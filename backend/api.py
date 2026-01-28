import os
import requests
from typing import Union, List, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import LangChain
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==========================================================
# 1. SETUP & CẤU HÌNH
# ==========================================================
load_dotenv()

# Điền Key Groq của bạn (nếu chưa có trong .env)
if not os.environ.get("GROQ_API_KEY"):
    os.environ["GROQ_API_KEY"] = "" 

HRM_API_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

app = FastAPI(title="ICS HRM SQL Chatbot API", version="3.0 - All in One")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    sql: str
    data: Union[List, Dict, Any]
    answer: str

# Khởi tạo LLM (Temperature = 0 để tuân thủ luật Logic)
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0, 
    api_key=os.environ.get("GROQ_API_KEY")
)

# ==========================================================
# 2. SCHEMA & LUẬT NGHIỆP VỤ (Nguồn: HRM_SCHEMA.docx)
# ==========================================================
HRM_SCHEMA_RAW = """
-- CHẤM CÔNG [Source: 7] --
BẢNG cham_cong: id, nhan_vien_id, ngay (date), check_in (time), check_out (time).

-- NHÂN SỰ [Source: 12] --
BẢNG nhanvien: id, ho_ten, email, so_dien_thoai, phong_ban_id, chuc_vu, vai_tro, luong_co_ban, trang_thai_lam_viec, ngay_vao_lam.
BẢNG phong_ban: id, ten_phong, truong_phong_id [Source: 13].

-- LƯƠNG & KPI [Source: 10, 11] --
BẢNG luong: id, nhan_vien_id, thang, nam, luong_co_ban, phu_cap, khoan_tru.
BẢNG luu_kpi: id, nhan_vien_id, thang, nam, diem_kpi, xep_loai.
BẢNG ngay_phep_nam: id, nhan_vien_id, nam, tong_ngay_phep, ngay_phep_con_lai.

-- DỰ ÁN & CÔNG VIỆC [Source: 7, 8, 9] --
BẢNG du_an: id, ten_du_an, lead_id (PM), phong_ban (varchar), trang_thai_duan, ngay_ket_thuc.
BẢNG cong_viec: id, ten_cong_viec, nguoi_giao_id, han_hoan_thanh, trang_thai, muc_do_uu_tien, du_an_id.
BẢNG cong_viec_nguoi_nhan: id, cong_viec_id, nhan_vien_id.
BẢNG cong_viec_tien_do: id, cong_viec_id, phan_tram.

-- TÀI LIỆU & HỆ THỐNG [Source: 14] --
BẢNG tai_lieu: id, ten_tai_lieu, mo_ta, link_tai_lieu, nguoi_tao_id.
BẢNG thong_bao: id, tieu_de, noi_dung, nguoi_nhan_id.

"""

# Kết hợp Schema thô với Luật nghiệp vụ (Enhanced Schema)
HRM_SCHEMA_ENHANCED = f"""
DANH SÁCH BẢNG VÀ LUẬT NGHIỆP VỤ BẮT BUỘC (DATA TRUTH):

1. **QUY TẮC ĐI MUỘN (08:06 RULE) - BẮT BUỘC:**
   - Định nghĩa: Nhân viên CÓ đi làm (check_in NOT NULL) nhưng giờ vào **từ 08:06:00 trở đi**.
   - SQL Logic: `check_in >= '08:06:00'`.
   - LƯU Ý: Tuyệt đối CẤM dùng `> 08:05`.
   - Phân biệt: Nếu không có dữ liệu chấm công -> Là Vắng mặt (Absent), dùng `NOT IN`.

2. **BẢNG `phong_ban` & `du_an`:**
   - Tìm tên phòng ban: BẮT BUỘC dùng `LIKE` (VD: `LIKE '%Marketing%'`). **CẤM** dùng `=`.
   - Dự án của phòng: Cột `phong_ban` trong bảng `du_an` là text (varchar). Tìm dự án theo phòng phải query trên bảng `du_an` (dùng LIKE).

3. **BẢNG `cong_viec` (Task):**
   - Muốn biết ai thực hiện công việc -> Phải JOIN bảng `cong_viec_nguoi_nhan`.
   - Trễ hạn: `han_hoan_thanh < CURRENT_DATE` AND `trang_thai != 'Hoàn thành'`.

4. **LUẬT TRA CỨU LƯƠNG (QUAN TRỌNG - SỬA ĐỔI):**
   - Bảng `luong` hiện tại KHÔNG có dữ liệu.
   - Khi người dùng hỏi về Lương (cơ bản, thu nhập...), **HÃY TRUY VẤN TỪ BẢNG `nhanvien`**.
   - Cột cần lấy: `nhanvien.luong_co_ban`.
   - Tuyệt đối không JOIN bảng `luong`.

5. **LUẬT DỰ ÁN & CÔNG VIỆC (QUAN TRỌNG):**
   - **Tìm Dự án theo phòng:** Cột `du_an.phong_ban` là text -> Dùng `LIKE`, CẤM JOIN bảng `phong_ban`.
   - **Tìm Quản lý (PM/Lead):** 
     + Cột `lead_id` trong `du_an` chỉ là số.
     + BẮT BUỘC JOIN bảng `nhanvien`: `ON du_an.lead_id = nhanvien.id`.
     + SELECT `nhanvien.ho_ten`.
   - **Người thực hiện task:** JOIN `cong_viec` -> `cong_viec_nguoi_nhan` -> `nhanvien`.

6. **LUẬT GIAO VIỆC (QUAN TRỌNG - MANY-TO-MANY):**
   - Bảng `cong_viec` KHÔNG lưu trực tiếp người thực hiện (chỉ lưu `nguoi_giao_id`).
   - Để tìm **"Ai làm việc gì"** hoặc **"Việc này ai làm"**:
     => BẮT BUỘC JOIN qua bảng trung gian: `cong_viec_nguoi_nhan`.
   - Lộ trình JOIN chuẩn: `cong_viec` <-> `cong_viec_nguoi_nhan` <-> `nhanvien`.

7.  **LUẬT CHUẨN HÓA DỮ LIỆU (QUAN TRỌNG - MỚI):**
   - **Trạng thái công việc:** Trong DB lưu chính xác là `'Đã hoàn thành'` (Tuyệt đối không dùng 'Hoàn thành' hay 'Done').
   - **Logic chưa xong:** `trang_thai != 'Đã hoàn thành'`.
   - **Logic trễ hạn:** `han_hoan_thanh < CURRENT_DATE` AND `trang_thai != 'Đã hoàn thành'`.

8. **LUẬT TRỄ HẠN (DEADLINE LOGIC):**
   - **Định nghĩa:** Một dự án hoặc công việc bị coi là trễ hạn (Overdue) khi:
     `ngay_ket_thuc < CURRENT_DATE` (hoặc `han_hoan_thanh < CURRENT_DATE`)
     AND `trang_thai != 'Đã hoàn thành'`.
   - **Lưu ý:** Luôn phải kiểm tra trạng thái. Nếu đã xong (`'Đã hoàn thành'`) thì dù quá ngày cũng không tính là trễ (có thể là xong muộn, nhưng hiện tại không còn treo).
SCHEMA CHI TIẾT:
{HRM_SCHEMA_RAW}
"""

# ==========================================================
# 3. PROMPTS (Kỹ thuật Prompt Engineering)
# ==========================================================

# --- PROMPT 1: SINH SQL (Kèm Few-Shot Learning) ---
SQL_PROMPT = ChatPromptTemplate.from_template("""
Bạn là SQL Generation Engine. Nhiệm vụ: Chuyển câu hỏi thành SQL Server/MySQL query tối ưu.

⛔ BỘ LUẬT CẤM (CRITICAL RULES):
1. **Output:** Chỉ trả về code SQL trần (Raw text). KHÔNG Markdown, KHÔNG giải thích.
2. **Luật Đi Muộn:** Bắt buộc `check_in >= '08:06:00'`.
3. **Luật Vắng Mặt:** Dùng `NOT IN (SELECT...)`.
4. **An toàn:** Chỉ dùng bảng/cột có trong SCHEMA.
5. **Ngoài lề:** Nếu câu hỏi không liên quan đến Nhân sự/Dự án (VD: thời tiết, bóng đá...), hãy trả về duy nhất chuỗi: "NO_DATA".

HỌC TỪ VÍ DỤ (FEW-SHOT):
- User: "Hôm nay ai đi muộn?" 
  -> SQL: SELECT n.ho_ten, c.check_in FROM cham_cong c JOIN nhanvien n ON c.nhan_vien_id = n.id WHERE c.ngay = CURRENT_DATE AND c.check_in >= '08:06:00'

- User: "Ai vắng mặt hôm nay?"
  -> SQL: SELECT ho_ten FROM nhanvien WHERE id NOT IN (SELECT nhan_vien_id FROM cham_cong WHERE ngay = CURRENT_DATE)

User: "Lương cơ bản của Nam là bao nhiêu?"
  -> SQL: SELECT ho_ten, luong_co_ban FROM nhanvien WHERE ho_ten LIKE '%Nam%'
                                              
- User: "Có dự án nào đang bị trễ hạn không?"
  -> SQL: SELECT ten_du_an, ngay_ket_thuc FROM du_an WHERE ngay_ket_thuc < CURRENT_DATE AND trang_thai_duan != 'Đã hoàn thành'

- User: "Liệt kê các dự án quá hạn và tên người quản lý?"
  -> SQL: SELECT d.ten_du_an, n.ho_ten, d.ngay_ket_thuc FROM du_an d JOIN nhanvien n ON d.lead_id = n.id WHERE d.ngay_ket_thuc < CURRENT_DATE AND d.trang_thai_du_an != 'Đã hoàn thành'

SCHEMA:
{schema}

CÂU HỎI:
{question}

SQL OUTPUT (Only SQL):
""")

# --- PROMPT 2: ĐỌC BÁO CÁO (Humanize Answer) ---
ANSWER_PROMPT = ChatPromptTemplate.from_template("""
Bạn là trợ lý HRM thông minh.
Nhiệm vụ: Đọc dữ liệu JSON và trả lời câu hỏi của người dùng.

THÔNG TIN:
- Câu hỏi: "{question}"
- Dữ liệu nhận được: {data}

YÊU CẦU TRẢ LỜI:
1. Nếu có dữ liệu: Trả lời thẳng vào vấn đề. Liệt kê danh sách nếu cần.
2. **QUAN TRỌNG - NẾU DỮ LIỆU RỖNG (Empty List/Null):**
   - Đừng nói "Không tìm thấy dữ liệu".
   - Hãy trả lời dựa trên ngữ cảnh câu hỏi.
   - Ví dụ: Hỏi "Ai đi muộn?", Data=[], Trả lời: "Tuyệt vời! Hôm nay không có nhân viên nào đi làm muộn."
   - Ví dụ: Hỏi "Ai nghỉ làm?", Data=[], Trả lời: "Hôm nay toàn bộ nhân viên đều đi làm đầy đủ."

GIỌNG ĐIỆU: Tự nhiên, thân thiện nhưng chuyên nghiệp.
TRẢ LỜI:
""")
# ==========================================================
# 4. HELPER FUNCTIONS (Xử lý & Gọi API)
# ==========================================================
def validate_sql(sql: str) -> str:
    """Làm sạch và kiểm tra an toàn SQL"""
    # Xóa markdown nếu có
    sql_clean = sql.replace("```sql", "").replace("```", "").strip()
    
    # Chặn các lệnh nguy hiểm (Chỉ cho phép SELECT)
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "grant"]
    if any(cmd in sql_clean.lower() for cmd in forbidden):
        print(f"⚠️ Blocked dangerous SQL: {sql_clean}")
        return ""
    
    return sql_clean

def execute_sql_api(sql: str) -> Any:
    """Gọi API HRM để lấy dữ liệu"""
    if not sql: return None

    # Log query ra terminal để debug
    print(f"\n[DEBUG SQL]: {sql}")

    try:
        payload = {"command": sql}
        res = requests.post(HRM_API_URL, json=payload, timeout=15)
        
        if res.status_code == 200:
            try:
                # Ưu tiên trả về JSON object
                return res.json()
            except:
                return res.text
        else:
            print(f"❌ API Error {res.status_code}: {res.text}")
            return f"Lỗi từ hệ thống dữ liệu: {res.text}"
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return "Lỗi kết nối đến máy chủ dữ liệu."

# ==========================================================
# 5. MAIN ENDPOINT (Luồng xử lý chính)
# ==========================================================
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        # BƯỚC 1: SINH SQL
        sql_chain = SQL_PROMPT | llm | StrOutputParser()
        raw_sql = sql_chain.invoke({
            "schema": HRM_SCHEMA_ENHANCED,
            "question": req.question
        })
        sql = validate_sql(raw_sql)

        # Nếu AI phát hiện câu hỏi ngoài lề (thời tiết, bóng đá...)
        if "NO_DATA" in sql:
            return {
                "sql": None,
                "data": None,
                "answer": "Xin lỗi. Tôi không có dữ liệu về vấn đề này! 😅"
            }

        # BƯỚC 2: CHẠY SQL
        if not sql:
            data_result = None
            final_answer = "Xin lỗi, tôi không thể hiểu yêu cầu này."
        else:
            data_result = execute_sql_api(sql)

        # BƯỚC 3: SINH CÂU TRẢ LỜI (SỬA ĐOẠN NÀY)
        # Bỏ đoạn 'if not data...' cứng nhắc. Luôn gửi cho AI xử lý ngữ cảnh.
        
        # Kiểm tra nếu lỗi API trả về String thì báo lỗi
        if isinstance(data_result, str) and "Lỗi" in data_result:
             final_answer = f"⚠️ {data_result}"
        else:
            # Gửi cả Data rỗng cho AI để nó "chém gió" dựa trên Prompt mới
            ans_chain = ANSWER_PROMPT | llm | StrOutputParser()
            final_answer = ans_chain.invoke({
                "question": req.question,
                "data": str(data_result) 
            })

        return ChatResponse(
            sql=sql,
            data=data_result,
            answer=final_answer
        )

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))