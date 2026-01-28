import os
import sys
import requests

# =========================
# 1. CONFIG
# =========================
KEY_GROQ_CUA_BAN = "" # Điền Key Groq của bạn vào đây

GROQ_API_KEY = KEY_GROQ_CUA_BAN
API_DB_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

# =========================
# 2. IMPORT
# =========================
from langchain_groq import ChatGroq
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# =========================
# 3. SCHEMA (Dựa trên Source [1], [2], [3])
# =========================
DB_SCHEMA = """
-- CHẤM CÔNG (Source: HRM_SCHEMA) --
BẢNG cham_cong:
- id (int), nhan_vien_id (int)
- ngay (date) -> Dùng lọc ngày/tháng/năm
- check_in (time) -> Dùng tính đi muộn. QUY TẮC: Muộn là >= '08:06:00'
- check_out (time)

-- NHÂN SỰ (Source: HRM_SCHEMA) --
BẢNG nhanvien:
- id (int), ho_ten (varchar), email (varchar)
- phong_ban_id (int), chuc_vu (varchar), luong_co_ban (float)
- trang_thai_lam_viec (varchar) -> 'Đang làm việc', 'Nghỉ việc'

-- LƯƠNG (Source: HRM_SCHEMA) --
BẢNG luong (nodata): id, nhan_vien_id, thang, nam, thuc_linh.

-- TỔ CHỨC --
BẢNG phong_ban: id, ten_phong.
BẢNG du_an: id, ten_du_an, trang_thai_duan.
"""

# =========================
# 4. KỊCH BẢN MẪU (FEW-SHOT LEARNING) - ĐÃ ĐIỀU CHỈNH LOGIC
# =========================
FEW_SHOT_EXAMPLES = """
TRƯỜNG HỢP 1: ĐI MUỘN (LATE)
User: "Hôm nay ai đi làm muộn?"
AI Thought: 
  - "Đi muộn" nghĩa là ĐÃ check-in nhưng trễ giờ.
  - Điều kiện: check_in >= '08:06:00'.
  - KHÔNG dùng NOT IN (đó là nghỉ làm).
SQL: SELECT n.ho_ten, c.check_in FROM cham_cong c JOIN nhanvien n ON c.nhan_vien_id = n.id WHERE c.ngay = CURRENT_DATE AND c.check_in >= '08:06:00'

TRƯỜNG HỢP 2: KHÔNG ĐI LÀM (ABSENT)
User: "Hôm nay ai chưa đến?" hoặc "Ai nghỉ làm hôm nay?"
AI Thought: Chưa đến nghĩa là không có dữ liệu trong bảng chấm công.
SQL: SELECT ho_ten FROM nhanvien WHERE id NOT IN (SELECT nhan_vien_id FROM cham_cong WHERE ngay = CURRENT_DATE)

TRƯỜNG HỢP 3: CÂU HỎI KẾT HỢP
User: "Tháng này Lan đi trễ mấy lần?"
AI Thought: Đi trễ là check_in >= '08:06:00'.
SQL: SELECT COUNT(*) FROM cham_cong c JOIN nhanvien n ON c.nhan_vien_id = n.id WHERE n.ho_ten LIKE '%Lan%' AND MONTH(c.ngay) = MONTH(CURRENT_DATE) AND c.check_in >= '08:06:00'
"""

# =========================
# 5. CẬP NHẬT PROMPT HỆ THỐNG
# =========================
# ... (Phần Tool giữ nguyên) ...

def main():
    # ... (Phần khởi tạo LLM giữ nguyên) ...

    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
Bạn là chuyên gia SQL HRM.

SCHEMA DỮ LIỆU (Nguồn: HRM_SCHEMA):
{DB_SCHEMA}

PHÂN BIỆT KHÁI NIỆM QUAN TRỌNG:
1. **ĐI MUỘN (Late)**:
   - Là nhân viên CÓ đi làm, nhưng `check_in` trễ.
   - Bắt buộc dùng toán tử: `check_in >= '08:06:00'`.
   - Ví dụ: check-in lúc 08:07, 09:00...

2. **VẮNG MẶT / CHƯA ĐẾN (Absent)**:
   - Là nhân viên KHÔNG có dữ liệu chấm công ngày hôm đó.
   - Dùng cấu trúc: `id NOT IN (SELECT nhan_vien_id ...)`

⛔ LUẬT CẤM:
- Khi hỏi "đi muộn", TUYỆT ĐỐI KHÔNG viết query tìm người vắng mặt (NOT IN).
- Chỉ tìm những dòng có `check_in` tồn tại và lớn hơn 08:06:00.

HỌC TỪ VÍ DỤ SAU:
{FEW_SHOT_EXAMPLES}
"""),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}")
    ])
    
    # ... (Phần còn lại giữ nguyên) ...