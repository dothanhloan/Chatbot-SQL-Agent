import os
import sys
import requests

# =========================
# CONFIG
# =========================
KEY_GOOGLE_MOI = ""
KEY_GROQ_CUA_BAN = ""

os.environ["GOOGLE_API_KEY"] = KEY_GOOGLE_MOI
GROQ_API_KEY = KEY_GROQ_CUA_BAN

API_DB_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

# =========================
# IMPORT
# =========================
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPromptTemplate

# =========================
# SCHEMA HRM (GROUND TRUTH)
# =========================
DB_SCHEMA = """
du_an(id, ten_du_an, trang_thai, ngay_bat_dau, ngay_ket_thuc)
nhanvien(id, ho_ten, phong_ban_id, chuc_vu)
luong(nhanvien_id, luong_co_ban, thang, nam)
cham_cong(nhanvien_id, ngay, gio_vao, gio_ra)
cong_viec(id, ten_cong_viec, nguoi_thuc_hien, tien_do)
"""

# =========================
# TOOL GỌI API HRM
# =========================
@tool
def execute_sql_query(sql: str) -> str:
    """
    Thực thi SQL SELECT thông qua HRM API.
    """
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate"]
    if any(x in sql.lower() for x in forbidden):
        return "❌ Chỉ cho phép SELECT."

    payload = {"command": sql}
    try:
        res = requests.post(API_DB_URL, json=payload, timeout=15)
        return res.text if res.status_code == 200 else res.text
    except Exception as e:
        return f"Lỗi API HRM: {e}"

# =========================
# MAIN
# =========================
def main():
    # -------- RAG SETUP --------
    loader = Docx2txtLoader("data/input.docx")
    docs = loader.load()
    splits = CharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200
    ).split_documents(docs)

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    # -------- LLM --------
    llm = ChatGroq(
        model_name="llama-3.3-70b-versatile",
        temperature=0,
        api_key=GROQ_API_KEY
    )

    # -------- PROMPT --------
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
Bạn là AI Agent HRM.

NẾU câu hỏi là kiến thức chung → trả lời từ CONTEXT.
NẾU câu hỏi là số liệu / báo cáo → dùng SCHEMA, sinh SQL SELECT và gọi tool.

QUY TẮC:
- Chỉ dùng bảng & cột trong schema.
- Không đoán.
- Không SQL ghi dữ liệu.

SCHEMA:
{DB_SCHEMA}
"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])

    agent = create_tool_calling_agent(
        llm=llm,
        tools=[execute_sql_query],
        prompt=prompt
    )

    agent_executor = AgentExecutor(
        agent=agent,
        tools=[execute_sql_query],
        verbose=True
    )

    print("\n🚀 HRM AI CHATBOT READY (Schema + API)\n")

    while True:
        q = input("👤 Bạn: ")
        if q.lower() in ["exit", "thoát"]:
            break

        # Lấy context RAG
        docs = retriever.invoke(q)
        context = "\n".join(d.page_content for d in docs)

        try:
            res = agent_executor.invoke({
                "input": f"CÂU HỎI: {q}\n\nCONTEXT:\n{context}"
            })
            print("\n🤖 Bot:", res["output"])
        except Exception as e:
            print("❌ Lỗi:", e)


if __name__ == "__main__":
    main()
