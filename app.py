import os
import re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate

# ==========================================================
# CONFIG
# ==========================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HRM_API_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

if not GROQ_API_KEY:
    raise RuntimeError("❌ Chưa cấu hình GROQ_API_KEY trong .env")

app = FastAPI(
    title="ICS HRM SQL Chatbot API",
    description="Chatbot AI truy vấn CSDL HRM thông qua SQL Agent + Schema",
    version="1.0"
)

# ==========================================================
# SCHEMA INPUT / OUTPUT
# ==========================================================
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    sql: str
    data: list | dict | None
    answer: str

# ==========================================================
# HRM DATABASE SCHEMA (ÉP AI KHÔNG ĐOÁN MÒ)
# ==========================================================
HRM_SCHEMA = """
BẢNG du_an:
- id (int)
- ten_du_an (varchar)
- trang_thai (varchar)
- ngay_bat_dau (date)
- ngay_ket_thuc (date)

BẢNG nhanvien:
- id (int)
- ho_ten (varchar)
- phong_ban_id (int)
- chuc_vu (varchar)

BẢNG luong:
- nhanvien_id (int)
- luong_co_ban (int)
- thang (int)
- nam (int)

BẢNG cham_cong:
- nhanvien_id (int)
- ngay (date)
- gio_vao (time)
- gio_ra (time)

BẢNG cong_viec:
- id (int)
- ten_cong_viec (varchar)
- nguoi_thuc_hien (int)
- tien_do (int)
"""

# ==========================================================
# LLM
# ==========================================================
from core.llm import get_llm
llm = get_llm()

# ==========================================================
# PROMPT ÉP AI VIẾT SQL
# ==========================================================
SQL_PROMPT = ChatPromptTemplate.from_template("""
Bạn là AI chuyên truy vấn CSDL HRM nội bộ.

QUY TẮC BẮT BUỘC:
- Chỉ dùng bảng & cột có trong SCHEMA
- Chỉ sinh câu lệnh SQL SELECT
- Không INSERT / UPDATE / DELETE
- Không suy đoán bảng hoặc cột không tồn tại
- Không giải thích, không markdown

SCHEMA:
{schema}

CÂU HỎI:
{question}

SQL:
""")

# ==========================================================
# UTILS
# ==========================================================
def validate_sql(sql: str) -> str:
    sql = sql.strip()

    if not sql.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="❌ Chỉ cho phép SELECT")

    if re.search(r"\b(insert|update|delete|drop|alter|truncate)\b", sql, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="❌ SQL nguy hiểm bị chặn")

    return sql


def execute_sql(sql: str):
    payload = {"command": sql}
    headers = {"Content-Type": "application/json"}

    try:
        res = requests.post(
            HRM_API_URL,
            json=payload,
            headers=headers,
            timeout=20
        )
        if res.status_code != 200:
            raise HTTPException(status_code=500, detail=res.text)

        return res.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================
# API ENDPOINT
# ==========================================================
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. Sinh SQL từ AI
    sql_chain = SQL_PROMPT | llm
    sql = sql_chain.invoke({
        "schema": HRM_SCHEMA,
        "question": request.question
    }).content.strip()

    # 2. Validate SQL
    sql = validate_sql(sql)

    # 3. Gọi HRM API thực thi SQL
    data = execute_sql(sql)

    # 4. AI tóm tắt kết quả (KHÔNG sinh SQL nữa)
    summary_prompt = f"""
Bạn là trợ lý HRM.

Dữ liệu truy vấn:
{data}

Câu hỏi ban đầu:
{request.question}

Hãy trả lời NGẮN GỌN, DỄ HIỂU, theo ngôn ngữ người dùng.
"""

    answer = llm.invoke(summary_prompt).content.strip()

    return ChatResponse(
        sql=sql,
        data=data,
        answer=answer
    )
