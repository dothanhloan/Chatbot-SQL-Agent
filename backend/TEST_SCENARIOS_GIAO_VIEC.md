# TEST SCENARIOS: PHÂN BIỆT NGƯỜI GIAO VIỆC vs NGƯỜI ĐƯỢC GIAO

## KHÁI NIỆM
- **Người giao việc (Assigner):** Được lưu ở `cong_viec.nguoi_giao_id` - người khởi tạo/giao công việc
- **Người được giao (Assignee):** Được lưu ở `cong_viec_nguoi_nhan.nhan_vien_id` - người nhận/thực hiện công việc
- **Bảng liên quan:** 
  - `cong_viec`: Chứa `nguoi_giao_id` (người giao)
  - `cong_viec_nguoi_nhan`: Chứa `nhan_vien_id` (người nhận)

---

## TEST CASES

### 1. NGƯỜI GIAO VIỆC
**SQL Logic:** `JOIN cong_viec cv JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id`

#### Test 1.1: Ai giao công việc?
```
Câu hỏi: "Ai giao công việc?"
SQL:     SELECT DISTINCT nv.ho_ten FROM cong_viec cv JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id
Kỳ vọng: Danh sách những người giao việc
VÍ DỤ KỲ VỌNG: 
- Nguyễn Văn A
- Trần Minh B
- Phạm Xuân C
```

#### Test 1.2: Ai giao công việc cho nhân viên X?
```
Câu hỏi: "Ai giao công việc cho Trần Minh?"
SQL:     SELECT DISTINCT nv.ho_ten, cv.ten_cong_viec 
         FROM cong_viec cv 
         JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id 
         JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id 
         JOIN nhanvien nvnhan ON cvnn.nhan_vien_id = nvnhan.id 
         WHERE nvnhan.ho_ten LIKE '%Trần Minh%'
Kỳ vọng: Người giao việc cho Trần Minh + tên công việc
VÍ DỤ KỲ VỌNG:
- Người giao: Nguyễn Văn A, Công việc: Làm báo cáo
- Người giao: Phạm Xuân C, Công việc: Review code
```

#### Test 1.3: Bao nhiêu công việc được giao bởi người X?
```
Câu hỏi: "Bao nhiêu công việc được giao bởi Nguyễn Văn A?"
SQL:     SELECT COUNT(cv.id) as so_cong_viec 
         FROM cong_viec cv 
         JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id 
         WHERE nv.ho_ten LIKE '%Nguyễn Văn A%'
Kỳ vọng: Con số (VÍ DỤ: 5)
```

#### Test 1.4: Chi tiết công việc giao bởi ai?
```
Câu hỏi: "Liệt kê công việc do Nguyễn Văn A giao"
SQL:     SELECT cv.ten_cong_viec, cv.han_hoan_thanh, cv.trang_thai, nv.ho_ten 
         FROM cong_viec cv 
         JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id 
         WHERE nv.ho_ten LIKE '%Nguyễn Văn A%' 
         ORDER BY cv.han_hoan_thanh
Kỳ vọng: Danh sách chi tiết công việc được giao bởi Nguyễn Văn A
VÍ DỤ KỲ VỌNG:
- Công việc: Làm báo cáo, Hạn: 2026-02-10, Trạng thái: Đang thực hiện, Người giao: Nguyễn Văn A
- Công việc: Review code, Hạn: 2026-02-15, Trạng thái: Đang thực hiện, Người giao: Nguyễn Văn A
- Công việc: Lên design, Hạn: 2026-02-20, Trạng thái: Chưa bắt đầu, Người giao: Nguyễn Văn A
```

---

### 2. NGƯỜI ĐƯỢC GIAO VIỆC
**SQL Logic:** `JOIN cong_viec cv JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id`

#### Test 2.1: Ai được giao công việc?
```
Câu hỏi: "Ai được giao công việc?"
SQL:     SELECT DISTINCT nv.ho_ten FROM cong_viec cv 
         JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id 
         JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id
Kỳ vọng: Danh sách những người nhận công việc
VÍ DỤ KỲ VỌNG:
- Lê Hoàng D
- Võ Thị E
- Đặng Văn F
```

#### Test 2.2: Công việc giao cho nhân viên X là gì?
```
Câu hỏi: "Công việc giao cho Lê Hoàng D là gì?"
SQL:     SELECT DISTINCT cv.ten_cong_viec FROM cong_viec cv 
         JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id 
         JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id 
         WHERE nv.ho_ten LIKE '%Lê Hoàng D%'
Kỳ vọng: Danh sách công việc của Lê Hoàng D
VÍ DỤ KỲ VỌNG:
- Hỗ trợ khách hàng
- Cập nhật tài liệu
- Kiểm tra dữ liệu
```

#### Test 2.3: Bao nhiêu công việc được giao cho nhân viên X?
```
Câu hỏi: "Bao nhiêu công việc được giao cho Lê Hoàng D?"
SQL:     SELECT COUNT(cv.id) as so_cong_viec FROM cong_viec cv 
         JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id 
         JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id 
         WHERE nv.ho_ten LIKE '%Lê Hoàng D%'
Kỳ vọng: Con số (VÍ DỤ: 8)
```

#### Test 2.4: Chi tiết công việc nhân viên X nhận?
```
Câu hỏi: "Liệt kê công việc được giao cho Lê Hoàng D"
SQL:     SELECT cv.ten_cong_viec, cv.han_hoan_thanh, cv.trang_thai, nv.ho_ten as nguoi_giao 
         FROM cong_viec cv 
         JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id 
         JOIN nhanvien nvnhan ON cvnn.nhan_vien_id = nvnhan.id 
         JOIN nhanvien nv ON cv.nguoi_giao_id = nv.id 
         WHERE nvnhan.ho_ten LIKE '%Lê Hoàng D%' 
         ORDER BY cv.han_hoan_thanh
Kỳ vọng: Danh sách chi tiết công việc của Lê Hoàng D (bao gồm cả người giao)
VÍ DỤ KỲ VỌNG:
- Công việc: Hỗ trợ khách hàng, Hạn: 2026-02-08, Trạng thái: Đang thực hiện, Người giao: Nguyễn Văn A
- Công việc: Cập nhật tài liệu, Hạn: 2026-02-12, Trạng thái: Chưa bắt đầu, Người giao: Trần Minh B
- Công việc: Kiểm tra dữ liệu, Hạn: 2026-02-18, Trạng thái: Đã hoàn thành, Người giao: Phạm Xuân C
```

---

### 3. SO SÁNH: NGƯỜI GIAO vs NGƯỜI NHẬN

#### Test 3.1: So sánh cùng 1 công việc
```
Câu hỏi: "Công việc 'Làm báo cáo' do ai giao, được giao cho ai?"
SQL:     SELECT cv.ten_cong_viec,
                 nv_giao.ho_ten as nguoi_giao,
                 nv_nhan.ho_ten as nguoi_nhan
         FROM cong_viec cv
         LEFT JOIN nhanvien nv_giao ON cv.nguoi_giao_id = nv_giao.id
         LEFT JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
         LEFT JOIN nhanvien nv_nhan ON cvnn.nhan_vien_id = nv_nhan.id
         WHERE cv.ten_cong_viec LIKE '%Làm báo cáo%'
Kỳ vọng: Công việc + người giao + người nhận
VÍ DỤ KỲ VỌNG:
- Công việc: Làm báo cáo
  Người giao: Nguyễn Văn A
  Người nhận: Lê Hoàng D, Võ Thị E
```

#### Test 3.2: Ai vừa giao việc vừa nhận việc?
```
Câu hỏi: "Ai vừa giao công việc vừa được giao công việc?"
SQL:     SELECT DISTINCT 
                 CASE WHEN nv_giao.id = nv_nhan.id THEN nv_giao.ho_ten ELSE NULL END as nguoi_vua_giao_vua_nhan
         FROM cong_viec cv
         JOIN nhanvien nv_giao ON cv.nguoi_giao_id = nv_giao.id
         LEFT JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
         LEFT JOIN nhanvien nv_nhan ON cvnn.nhan_vien_id = nv_nhan.id
         WHERE nv_giao.id = nv_nhan.id
Kỳ vọng: Danh sách người vừa giao vừa nhận
VÍ DỤ KỲ VỌNG:
- Nguyễn Văn A
- Trần Minh B
```

---

### 4. EDGE CASE - PHÂN BIỆT KỸ LỰC

#### Test 4.1: Công việc do ai giao? (KHÔNG phải công việc được giao cho ai)
```
✅ ĐÚNG: "Công việc do Nguyễn Văn A giao" → người_giao_id
❌ SAI: "Công việc do Nguyễn Văn A giao" → cong_viec_nguoi_nhan (đây là người nhận, không phải người giao)
```

#### Test 4.2: Công việc được giao cho ai? (KHÔNG phải công việc do ai giao)
```
✅ ĐÚNG: "Công việc được giao cho Lê Hoàng D" → cong_viec_nguoi_nhan.nhan_vien_id
❌ SAI: "Công việc được giao cho Lê Hoàng D" → cong_viec.nguoi_giao_id (đây là người giao, không phải người nhận)
```

#### Test 4.3: Danh sách công việc của nhân viên X (mơ hồ)
```
Câu hỏi: "Công việc của nhân viên X"
Phân tích:
- Nếu bối cảnh là X **ĐƯỢC GIAO** công việc → dùng `cong_viec_nguoi_nhan.nhan_vien_id`
- Nếu bối cảnh là X **GIAO** công việc cho người khác → dùng `cong_viec.nguoi_giao_id`
- MẶC ĐỊNH: Thường hỏi về công việc người đó phải thực hiện (NGƯỜI NHẬN) → dùng `cong_viec_nguoi_nhan`

SQL (an toàn):
SELECT cv.ten_cong_viec FROM cong_viec cv
JOIN cong_viec_nguoi_nhan cvnn ON cv.id = cvnn.cong_viec_id
JOIN nhanvien nv ON cvnn.nhan_vien_id = nv.id
WHERE nv.ho_ten LIKE '%X%'
```

---

## SCHEMA RECAP

### Bảng cong_viec
```
id, ten_cong_viec, nguoi_giao_id, han_hoan_thanh, trang_thai, muc_do_uu_tien, du_an_id
         ↑
   NGƯỜI GIAO VIỆC
```

### Bảng cong_viec_nguoi_nhan
```
id, cong_viec_id, nhan_vien_id
                  ↑
         NGƯỜI ĐƯỢC GIAO / NGƯỜI NHẬN VIỆC
```

---

## LỖI PHỔ BIẾN CẦN TRÁNH

❌ **LỖI 1:** Nhầm lẫn `nguoi_giao_id` với người nhận
```
Câu hỏi: "Công việc được giao cho ai?"
Sai: SELECT * FROM cong_viec (chỉ có nguoi_giao_id, không có người nhận!)
Đúng: SELECT * FROM cong_viec_nguoi_nhan (bảng này mới có người nhận)
```

❌ **LỖI 2:** Quên JOIN `cong_viec_nguoi_nhan`
```
Câu hỏi: "Ai nhận công việc X?"
Sai: SELECT * FROM cong_viec WHERE ten_cong_viec LIKE '%X%' (không biết ai nhận)
Đúng: Phải JOIN với cong_viec_nguoi_nhan để lấy danh sách người nhận
```

❌ **LỖI 3:** Nhầm giữa 2 khái niệm
```
Câu hỏi: "Công việc do ai giao?" vs "Công việc giao cho ai?"
Giao bởi = nguoi_giao_id (Người giao)
Giao cho = cong_viec_nguoi_nhan (Người nhận)
```

