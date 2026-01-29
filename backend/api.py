import os
import requests
from typing import Union, List, Dict, Any
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# LangChain - OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ==========================================================
# 1. SETUP & CẤU HÌNH
# ==========================================================
load_dotenv()

# BẮT BUỘC phải có OpenAI API Key
if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError("❌ Chưa cấu hình OPENAI_API_KEY")

HRM_API_URL = "https://hrm.icss.com.vn/ICSS/api/execute-sql"

app = FastAPI(title="ICS HRM SQL Chatbot API", version="3.0 - OpenAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# 2. SCHEMA REQUEST / RESPONSE
# ==========================================================
class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    sql: Union[str, None]
    data: Union[List, Dict, Any, None]
    answer: str


# ==========================================================
# 3. KHỞI TẠO LLM (OPENAI)
# ==========================================================
llm = ChatOpenAI(
    model="gpt-4o-mini",   # ✅ Nhanh – rẻ – ổn cho SQL + RAG
    temperature=0,
    max_tokens=600   # đủ cho SQL + trả lời
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

9. **LUẬT TIẾN ĐỘ & LỊCH SỬ (QUAN TRỌNG NHẤT):**
   - Bảng `cong_viec_tien_do` lưu lịch sử cập nhật (Log). Một việc có nhiều dòng dữ liệu.
   - **Tra cứu đơn lẻ (1 việc):** Dùng `ORDER BY thoi_gian_cap_nhat DESC LIMIT 1` để lấy % mới nhất.
   - **Thống kê/Đếm (Nhiều việc):** BẮT BUỘC dùng Sub-query để lọc ngày mới nhất: 
     `WHERE td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)`.
   - ⛔ **CẤM:** Tuyệt đối KHÔNG dùng `AVG()` hoặc `SUM()` trên cột `phan_tram`.

10. **LUẬT CHI TIẾT QUY TRÌNH (SUB-TASKS):**
   - Khi hỏi về "chi tiết", "các bước", "quy trình" của một việc -> Hãy query bảng `cong_viec_quy_trinh` (lấy cột `ten_buoc`, `trang_thai`).
   - Đừng chỉ lấy mỗi cột `mo_ta` trong bảng `cong_viec` vì nó không đủ chi tiết.
11. **LUẬT TÍNH TIẾN ĐỘ DỰ ÁN (PROJECT PROGRESS RULE):**
   - Bảng `du_an` KHÔNG có cột phần trăm hoàn thành.
   - **Định nghĩa:** Tiến độ dự án = Trung bình cộng (AVG) tiến độ hiện tại của tất cả các công việc (`cong_viec`) thuộc dự án đó.
   - **Công thức SQL bắt buộc:**
     1. Lấy tiến độ mới nhất của từng công việc (dùng Sub-query `MAX(thoi_gian_cap_nhat)`).
     2. Gom nhóm theo dự án (`GROUP BY du_an.id`).
     3. Tính `AVG(phan_tram)`.
     4. Nếu cần lọc (ví dụ > 80%), dùng `HAVING AVG(...) > 80`.
12. **MỐI QUAN HỆ DỰ ÁN - CÔNG VIỆC:**
   - Liên kết: `du_an.id` = `cong_viec.du_an_id`.
   - Tiến độ: `cong_viec.id` = `cong_viec_tien_do.cong_viec_id`
13. **LUẬT TRA CỨU TIẾN ĐỘ AN TOÀN (SAFE JOIN RULE):**
   - Khi tính toán tiến độ dự án hoặc công việc, hãy ưu tiên dùng **`LEFT JOIN cong_viec_tien_do`**.
   - Lý do: Có những dự án mới tạo chưa có log tiến độ. Nếu dùng `INNER JOIN` sẽ bị mất dữ liệu.
   - Xử lý NULL: Sử dụng `COALESCE(AVG(td.phan_tram), 0)` để mặc định là 0% nếu không tìm thấy log.
14. **LUẬT THỐNG KÊ TRẠNG THÁI DỰ ÁN (PROJECT STATUS STATS):**
   - Khi người dùng hỏi thống kê số lượng dự án theo "trạng thái" (VD: Đang thực hiện, Đã xong...):
   - **Không cần tính toán** phức tạp.
   - Truy vấn trực tiếp bảng `du_an`.
   - Sử dụng `GROUP BY trang_thai_duan` (Lưu ý: tên cột là `trang_thai_duan`, KHÔNG dùng `trang_thai` vì đó là cột của bảng công việc).

15. **LUẬT TRA CỨU TIẾN ĐỘ DỰ ÁN (PROJECT PROGRESS - ADVANCED):**
   - **Bối cảnh:** Bảng `du_an` KHÔNG có cột phần trăm.
   - **Logic:** Tiến độ Dự án = Trung bình cộng (AVG) tiến độ *mới nhất* của tất cả công việc (`cong_viec`) thuộc dự án đó.
   - **Công thức SQL BẮT BUỘC (Safe Mode):**
     1. Dùng **`LEFT JOIN`** bảng `cong_viec` và `cong_viec_tien_do` (để không bị mất dự án nếu chưa có log tiến độ).
     2. Xử lý NULL: Dùng `COALESCE(AVG(td.phan_tram), 0)` để mặc định là 0% nếu chưa có dữ liệu.
     3. Lọc mới nhất: `AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)`.
     4. Gom nhóm: `GROUP BY d.id, d.ten_du_an`.

16. **LUẬT DỰ ÁN TẠM NGƯNG (PAUSED PROJECTS):**
    - Khi truy vấn dự án (đặc biệt là dự án Tạm ngưng/Dừng), người dùng luôn muốn biết **Ai chịu trách nhiệm (Leader)**.
    - **Logic lấy tên Leader:** 
      - Bắt buộc JOIN bảng `nhanvien` (alias `nv`).
      - Điều kiện: `du_an.lead_id = nv.id`.
      - Lấy cột: `nv.ho_ten`.
    - **Logic lọc trạng thái:** Dùng `trang_thai LIKE '%Ngưng%'` hoặc `LIKE '%Dừng%'`.
    - **Logic tiến độ:** Vẫn giữ nguyên công thức tính AVG từ bảng `cong_viec` để biết dự án dừng ở mức nào.

13. **LUẬT HIỆU SUẤT NHÂN SỰ (PERFORMANCE):**
    - Đánh giá ai làm việc hiệu quả: Dựa trên số lượng công việc đã hoàn thành (`trang_thai` = 'Đã hoàn thành') và so sánh `ngay_hoan_thanh` <= `han_hoan_thanh` (xong trước hạn).
    - Đánh giá quá tải: Đếm số lượng công việc `trang_thai` = 'Đang thực hiện' của từng người.

14. **LUẬT TÊN CỘT TRẠNG THÁI (STATUS COLUMN NAMES):**
   - LƯU Ý RẤT QUAN TRỌNG VỀ SCHEMA:
     + Bảng `cong_viec` dùng cột: **`trang_thai`** [2].
     + Bảng `du_an` dùng cột: **`trang_thai_duan`** [1].
   - Tuyệt đối không dùng `du_an.trang_thai` (sẽ gây lỗi SQL).

11. **LUẬT DỰ ÁN TẠM NGƯNG:**
    - Khi lọc dự án tạm ngưng, dùng điều kiện: `d.trang_thai_du_an LIKE '%Ngưng%'`.
    - Vẫn tính toán tiến độ trung bình từ `cong_viec` để hiển thị mức độ dở dang.

12. **LUẬT XÁC ĐỊNH CÔNG VIỆC TRỄ HẠN (OVERDUE RULE):**
    - Một công việc bị coi là TRỄ HẠN khi thỏa mãn 2 điều kiện:
      1. `trang_thai` KHÁC 'Đã hoàn thành' (Ví dụ: 'Đang thực hiện', 'Mới tạo'...).
      2. `han_hoan_thanh` < `CURRENT_DATE` (Ngày hiện tại).
    - Câu lệnh SQL mẫu: `WHERE cv.trang_thai != 'Đã hoàn thành' AND cv.han_hoan_thanh < CURDATE()`.

13. **QUY TẮC ĐẾM SỐ LƯỢNG (COUNT RULE) – BẮT BUỘC:**
- KÍCH HOẠT KHI câu hỏi chứa các cụm:
  + "bao nhiêu"
  + "tổng số"
  + "có mấy"
  + "số lượng"
- MỤC TIÊU:
  → Trả lời bằng **SỐ LƯỢNG** (không liệt kê danh sách chi tiết).
- SQL LOGIC BẮT BUỘC:
  → PHẢI sử dụng hàm:
    `COUNT(*) AS total`
- MẪU SQL CHUẨN:
  ```sql
  SELECT COUNT(*) AS total
  FROM <table>;

14. **LUẬT TRA CỨU ĐƠN NGHỈ PHÉP (LEAVE REQUESTS - REAL DATA):**
    - **Cấu trúc bảng `don_nghi_phep` thực tế:**
      + Cột ngày: `ngay_bat_dau` và `ngay_ket_thuc` (KHÔNG dùng `tu_ngay`/`den_ngay`).
      + Khóa ngoại: `nhan_vien_id` (có gạch dưới `_`).
      + Trạng thái: Giá trị lưu là `'da_duyet'` (không dấu, viết thường).
    - **Logic tìm người đang nghỉ:**
      + `CURRENT_DATE` nằm trong khoảng `ngay_bat_dau` và `ngay_ket_thuc`.
      + Điều kiện: `trang_thai = 'da_duyet'`.

15. **LUẬT TRA CỨU QUỸ PHÉP (LEAVE BALANCE):**
    - **Cấu trúc bảng `ngay_phep_nam`:**
      + Khóa ngoại: `nhan_vien_id`.
      + Cột số liệu: `tong_ngay_phep`, `ngay_phep_da_dung`, `ngay_phep_con_lai`.
    - **Logic Join:** `ngay_phep_nam.nhan_vien_id = nhanvien.id`.

16. **LUẬT TÌM LÃNH ĐẠO / GIÁM ĐỐC (LEADERSHIP LOOKUP):**
    - Khi người dùng hỏi: "Giám đốc là ai?", "Ai là sếp?", "CEO của công ty", "Ban lãnh đạo".
    - **Logic:** Truy vấn bảng `nhanvien`.
    - **Điều kiện:** Tìm kiếm trong cột `chuc_vu` hoặc `vai_tro`.
    - **Từ khóa lọc:** Sử dụng `LIKE '%Giám đốc%'`, `LIKE '%CEO%'`, hoặc `LIKE '%Chủ tịch%'`.
    - **SQL mẫu:** `SELECT ho_ten, chuc_vu, email FROM nhanvien WHERE chuc_vu LIKE '%Giám đốc%' OR chuc_vu LIKE '%CEO%'`.
    
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
5. Ngoài lề:
- Chỉ trả về "NO_DATA" nếu:
  a) Câu hỏi hoàn toàn KHÔNG liên quan đến HRM / Dự án / Nhân sự
  b) Không ánh xạ được tới BẤT KỲ bảng nào trong schema
- Nếu câu hỏi còn mơ hồ nhưng có khả năng liên quan,hãy suy luận hợp lý nhất và sinh SQL an toàn.

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

- User: "Tiến độ hiện tại của công việc 'Lên phương án hợp tác với TPX' đến đâu rồi?"
  -> SQL: SELECT td.phan_tram, td.thoi_gian_cap_nhat FROM cong_viec_tien_do td JOIN cong_viec cv ON td.cong_viec_id = cv.id WHERE cv.ten_cong_viec LIKE '%Lên phương án hợp tác với TPX%' ORDER BY td.thoi_gian_cap_nhat DESC LIMIT 1

- User: "Cho tôi xem chi tiết các bước của việc 'Làm việc với a Bình BIDV'?"
  -> SQL: SELECT qt.ten_buoc, qt.trang_thai, qt.mo_ta, qt.ngay_ket_thuc FROM cong_viec_quy_trinh qt JOIN cong_viec cv ON qt.cong_viec_id = cv.id WHERE cv.ten_cong_viec LIKE '%Tuyển dụng nhân sự%' ORDER BY qt.ngay_bat_dau ASC

User: "Liệt kê các công việc đã hoàn thành trên 50%?"
  -> SQL: SELECT cv.ten_cong_viec, td.phan_tram, td.thoi_gian_cap_nhat FROM cong_viec cv JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id WHERE td.phan_tram > 50 AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)
                                              
- User: "Có bao nhiêu công việc đã hoàn thành trên 50%?"
  -> SQL: SELECT COUNT(cv.id) AS so_luong FROM cong_viec cv JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id WHERE td.phan_tram > 50 AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)                        

User: "Thống kê số lượng dự án theo từng trạng thái?"
  -> SQL: SELECT trang_thai_du_an, COUNT(id) FROM du_an GROUP BY trang_thai_du_an
                                              
User: "Liệt kê những dự án đã hoàn thành trên 80%?"
  -> SQL: SELECT d.ten_du_an, AVG(td.phan_tram) as tien_do_tb FROM du_an d JOIN cong_viec cv ON d.id = cv.du_an_id JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id WHERE td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id) GROUP BY d.id, d.ten_du_an HAVING AVG(td.phan_tram) > 80          

 User: "Có bao nhiêu dự án có tiến độ dưới 50%?"
  -> SQL: SELECT COUNT(*) as so_luong FROM (SELECT d.id FROM du_an d JOIN cong_viec cv ON d.id = cv.du_an_id JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id WHERE td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id) GROUP BY d.id HAVING AVG(td.phan_tram) < 50) as subquery

- User: "Liệt kê các dự án có tiến độ dưới 50%?"
  -> SQL: SELECT d.ten_du_an, AVG(td.phan_tram) as tien_do_trung_binh FROM du_an d JOIN cong_viec cv ON d.id = cv.du_an_id JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id WHERE td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id) GROUP BY d.id, d.ten_du_an HAVING AVG(td.phan_tram) < 50                                              
                                              
     

- User: "Tiến độ dự án 'Database Mobifone' hiện tại là bao nhiêu?"
  -> SQL: SELECT d.ten_du_an, COALESCE(AVG(td.phan_tram), 0) as phan_tram_hoan_thanh 
          FROM du_an d 
          LEFT JOIN cong_viec cv ON d.id = cv.du_an_id 
          LEFT JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id 
          AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)
          WHERE d.ten_du_an LIKE '%Database Mobifone%'
          GROUP BY d.id, d.ten_du_an                                            

- User: "Thống kê số lượng dự án theo từng trạng thái?"
  -> SQL: SELECT trang_thai_duan, COUNT(id) as so_luong FROM du_an GROUP BY trang_thai_duan

- User: "Có bao nhiêu dự án đang ở trạng thái 'Đang thực hiện'?"
  -> SQL: SELECT COUNT(id) as so_luong FROM du_an WHERE trang_thai_du_an LIKE '%Đang thực hiện%'                                                                                          

- User: "Những dự án nào đang bị tạm ngưng và ai là quản lý?"
  -> SQL: SELECT d.ten_du_an, d.trang_thai, COALESCE(AVG(td.phan_tram), 0) as tien_do_luc_dung, nv.ho_ten as quan_ly_du_an
          FROM du_an d 
          LEFT JOIN cong_viec cv ON d.id = cv.du_an_id 
          LEFT JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id 
          AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)
          LEFT JOIN nhanvien nv ON d.lead_id = nv.id
          WHERE d.trang_thai LIKE '%Ngưng%' OR d.trang_thai LIKE '%Dừng%'
          GROUP BY d.id, d.ten_du_an, d.trang_thai, nv.ho_ten

# --- Kịch bản: Hỏi thông tin Lead của một dự án cụ thể ---
- User: "Ai đang phụ trách dự án 'Oracle Cloud' và tiến độ thế nào?"
  -> SQL: SELECT d.ten_du_an, nv.ho_ten as lead_du_an, nv.email, COALESCE(AVG(td.phan_tram), 0) as tien_do
          FROM du_an d 
          LEFT JOIN nhanvien nv ON d.lead_id = nv.id
          LEFT JOIN cong_viec cv ON d.id = cv.du_an_id 
          LEFT JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id 
          AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)
          WHERE d.ten_du_an LIKE '%Oracle Cloud%'
          GROUP BY d.id, d.ten_du_an, nv.ho_ten, nv.email   

- User: "Top 5 nhân viên hoàn thành nhiều công việc nhất trong tháng này?"
  -> SQL: SELECT nv.ho_ten, COUNT(cv.id) as so_viec_hoan_thanh, pb.ten_phong
          FROM nhanvien nv 
          JOIN cong_viec_nguoi_nhan cvnn ON nv.id = cvnn.nhan_vien_id 
          JOIN cong_viec cv ON cvnn.cong_viec_id = cv.id 
          JOIN phong_ban pb ON nv.phong_ban_id = pb.id
          WHERE cv.trang_thai = 'Đã hoàn thành' AND MONTH(cv.ngay_hoan_thanh) = MONTH(CURRENT_DATE())
          GROUP BY nv.id, nv.ho_ten, pb.ten_phong
          ORDER BY so_viec_hoan_thanh DESC LIMIT 5

- User: "Thống kê khối lượng công việc đang chạy theo từng phòng ban?"
  -> SQL: SELECT pb.ten_phong, COUNT(cv.id) as so_luong_viec_dang_lam 
          FROM phong_ban pb 
          JOIN cong_viec cv ON pb.id = cv.phong_ban_id 
          WHERE cv.trang_thai = 'Đang thực hiện' 
          GROUP BY pb.ten_phong 
          ORDER BY so_luong_viec_dang_lam DESC

- User: "Những dự án nào đang bị tạm ngưng và ai là quản lý?"
  -> SQL: SELECT d.ten_du_an, d.trang_thai_duan, COALESCE(AVG(td.phan_tram), 0) as tien_do_luc_dung, nv.ho_ten as quan_ly_du_an
          FROM du_an d 
          LEFT JOIN cong_viec cv ON d.id = cv.du_an_id 
          LEFT JOIN cong_viec_tien_do td ON cv.id = td.cong_viec_id 
          AND td.thoi_gian_cap_nhat = (SELECT MAX(thoi_gian_cap_nhat) FROM cong_viec_tien_do WHERE cong_viec_id = cv.id)
          LEFT JOIN nhanvien nv ON d.lead_id = nv.id
          WHERE d.trang_thai_duan LIKE '%Ngưng%' OR d.trang_thai_duan LIKE '%Dừng%'
          GROUP BY d.id, d.ten_du_an, d.trang_thai_duan, nv.ho_ten

- User: "Thống kê số lượng dự án theo từng trạng thái?"
  -> SQL: SELECT trang_thai_duan, COUNT(id) as so_luong FROM du_an GROUP BY trang_thai_duan                                              

- User: "Kiểm tra xem Trần Đình Nam có công việc nào đang bị trễ hạn không?"
  -> SQL: SELECT cv.ten_cong_viec, cv.han_hoan_thanh, cv.trang_thai, nv.ho_ten
          FROM cong_viec cv
          JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
          JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id
          WHERE nv.ho_ten LIKE '%Trần Đình Nam%'
          AND cv.trang_thai != 'Đã hoàn thành' 
          AND cv.han_hoan_thanh < CURRENT_DATE


- User: "Liệt kê các công việc đã làm xong của nhân viên mã số 24?"
  -> SQL: SELECT cv.ten_cong_viec, cv.ngay_hoan_thanh, cv.muc_do_uu_tien
          FROM cong_viec cv
          JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
          WHERE cvnn.nhan_vien_id = 24
          AND cv.trang_thai = 'Đã hoàn thành'


- User: "Danh sách công việc và tình trạng hạn chót của dự án Web HRM?"
  -> SQL: SELECT cv.ten_cong_viec, nv.ho_ten as nguoi_lam, cv.han_hoan_thanh, cv.trang_thai,
                 CASE 
                    WHEN cv.trang_thai != 'Đã hoàn thành' AND cv.han_hoan_thanh < CURRENT_DATE THEN 'Trễ hạn'
                    ELSE 'Đúng hạn/Đang chạy'
                 END as tinh_trang_han
          FROM cong_viec cv
          JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
          JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id
          JOIN du_an d ON cv.du_an_id = d.id
          WHERE d.ten_du_an LIKE '%Web HRM%'         

- User: "Hôm nay ai đang nghỉ phép?" 
  -> SQL: SELECT nv.ho_ten, dnp.ly_do FROM don_nghi_phep dnp JOIN nhanvien nv ON dnp.nhan_vien_id = nv.id WHERE CURRENT_DATE BETWEEN dnp.ngay_bat_dau AND dnp.ngay_ket_thuc AND dnp.trang_thai = 'da_duyet'
- User: "Nguyễn Tấn Dũng còn bao nhiêu phép?"
  -> SQL: SELECT nv.ho_ten, np.ngay_phep_con_lai FROM ngay_phep_nam np JOIN nhanvien nv ON np.nhan_vien_id = nv.id WHERE nv.ho_ten LIKE '%Nguyễn Tấn Dũng%' AND np.nam = YEAR(CURRENT_DATE)
- User: "Giám đốc công ty là ai?" -> SQL: SELECT ho_ten, chuc_vu, email, so_dien_thoai FROM nhanvien WHERE chuc_vu LIKE '%Giám đốc%' OR chuc_vu LIKE '%CEO%' OR chuc_vu LIKE '%General Manager%'
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

1. Nếu dữ liệu KHÔNG rỗng:
   - Trả lời thẳng vào vấn đề
   - Liệt kê đầy đủ danh sách nếu có nhiều bản ghi

2. Nếu dữ liệu rỗng (Empty List hoặc Null):
   - Không nói "Không tìm thấy dữ liệu"
   - Được phép suy luận tích cực dựa trên logic nghiệp vụ thông thường
   - Áp dụng cho các câu hỏi kiểm tra trạng thái
     (ví dụ: đi muộn, nghỉ làm, trễ hạn, chưa hoàn thành)
   - Ví dụ:
     + "Ai đi muộn?" → "Tuyệt vời! Hôm nay không có nhân viên nào đi muộn."
     + "Ai nghỉ làm?" → "Hôm nay toàn bộ nhân viên đều đi làm đầy đủ."

3. Với dữ liệu thống kê (COUNT, SUM, AVG):
   - Nếu dữ liệu là một con số, đó chính là câu trả lời
   - Trả lời trực tiếp, không nói thiếu thông tin

4. Khi SQL đã có điều kiện lọc:
   - Mặc định TẤT CẢ bản ghi trả về đều thỏa mãn điều kiện
   - Không cần suy đoán thêm từ phía AI

5. TRUNG THỰC VỚI DỮ LIỆU (DATA FIDELITY – BẮT BUỘC):
   - Không được tự ý loại bỏ bất kỳ bản ghi nào
   - Không được bỏ qua các giá trị 0 (0% tiến độ là thông tin hợp lệ)
   - SQL trả về gì → câu trả lời phải phản ánh đúng như vậy

6. QUY TẮC ĐỊNH DẠNG (BẮT BUỘC):
  - TUYỆT ĐỐI KHÔNG dùng Markdown in đậm (**).
  - KHÔNG dùng **text** trong mọi trường hợp.
  - Chỉ trả lời bằng văn bản thường.
  - Nếu cần liệt kê → dùng dấu "-" ở đầu dòng.
GIỌNG ĐIỆU:
Tự nhiên, thân thiện, chuyên nghiệp, giống trợ lý nội bộ doanh nghiệp.

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
                "answer": "Xin lỗi. Tôi không có dữ liệu về vấn đề này!"
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