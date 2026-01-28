HRM_SCHEMA = """
BẢNG cau_hinh_he_thong:
- id (int)
- ten_cau_hinh (varchar)
- gia_tri (text)
- mo_ta (varchar)
- ngay_tao (datetime)

BẢNG cham_cong:
- id (int)
- nhan_vien_id (int)
- ngay (date)
- check_in (time)
- check_out (time)
- ngay_tao (datetime)

BẢNG cong_viec:
- id (int)
- ten_cong_viec (varchar)
- mo_ta (text)
- du_an_id (int)
- phong_ban_id (int)
- nguoi_giao_id (int)
- ngay_bat_dau (date)
- han_hoan_thanh (date)
- ngay_hoan_thanh (date)
- trang_thai (varchar)
- trang_thai_duyet (varchar)
- muc_do_uu_tien (varchar)
- tai_lieu_cv (varchar)
- file_tai_lieu (varchar)
- nhac_viec (int)
- ngay_tao (datetime)

BẢNG cong_viec_danh_gia:
- id (int)
- cong_viec_id (int)
- nguoi_danh_gia_id (int)
- nhan_xet (text)
- thoi_gian (datetime)
- is_from_worker (boolean)

BẢNG cong_viec_lich_su:
- id (int)
- cong_viec_id (int)
- nguoi_thay_doi_id (int)
- mo_ta_thay_doi (varchar)
- thoi_gian (datetime)

BẢNG cong_viec_nguoi_nhan:
- id (int)
- cong_viec_id (int)
- nhan_vien_id (int)

BẢNG cong_viec_quy_trinh:
- id (int)
- cong_viec_id (int)
- ten_buoc (varchar)
- mo_ta (text)
- ngay_bat_dau (date)
- ngay_ket_thuc (date)
- trang_thai (varchar)
- ngay_tao (datetime)

BẢNG cong_viec_tien_do:
- id (int)
- cong_viec_id (int)
- phan_tram (int)
- thoi_gian_cap_nhat (datetime)

BẢNG don_nghi_phep:
- id (int)
- nhanvien_id (int)
- tu_ngay (date)
- den_ngay (date)
- ly_do (varchar)
- trang_thai (varchar)
- ngay_tao (datetime)

BẢNG du_an:
- id (int)
- ten_du_an (varchar)
- mo_ta (text)
- trang_thai_duan (varchar)
- muc_do_uu_tien (varchar)
- nhom_du_an (varchar)
- phong_ban (varchar)
- lead_id (int)
- ngay_bat_dau (date)
- ngay_ket_thuc (date)
- ngay_tao (datetime)

BẢNG file_dinh_kem:
- id (int)
- ten_file (varchar)
- duong_dan (varchar)
- loai_file (varchar)
- kich_thuoc (int)
- cong_viec_id (int)
- du_an_id (int)
- ngay_tao (datetime)
- nguoi_tai_len_id (int)

BẢNG lich_trinh:
- id (int)
- tieu_de (varchar)
- mo_ta (text)
- ngay_bat_dau (date)
- ngay_ket_thuc (date)
- ngay_tao (datetime)


BẢNG luong (nodata):
- id (int)
- nhan_vien_id (int)
- thang (int)
- nam (int)
- luong_co_ban (float)
- phu_cap (float)
- khoan_tru (float)
- thuc_linh (float)
- trang_thai_thanh_toan (varchar)
- ngay_tao (datetime)

BẢNG luong_cau_hinh (nodata):
- id (int)
- ten_cau_hinh (varchar)
- loai_cau_hinh (varchar)
- gia_tri (float)
- don_vi (varchar)
- mo_ta (text)
- ngay_tao (datetime)

BẢNG luu_kpi (nodata):
- id (int)
- nhan_vien_id (int)
- thang (int)
- nam (int)
- diem_kpi (float)
- xep_loai (varchar)
- ghi_chu (text)
- ngay_chot (datetime)

BẢNG ngay_phep_nam:
- id (int)
- nhan_vien_id (int)
- nam (int)
- tong_ngay_phep (float)
- ngay_phep_da_dung (float)
- ngay_phep_con_lai (float)
- ngay_cap_nhat (datetime)

BẢNG nhan_su_lich_su (nodata):
- id (int)
- nhan_vien_id (int)
- loai_thay_doi (varchar)
- noi_dung_cu (text)
- noi_dung_moi (text)
- nguoi_thuc_hien_id (int)
- thoi_gian (datetime)
- ghi_chu (text)




BẢNG nhanvien:
- id (int)
- ho_ten (varchar)
- so_dien_thoai (varchar)
- email (varchar)
- mat_khau (varchar)
- ngay_sinh (date)
- gioi_tinh (varchar)
- avatar_url (varchar)
- vai_tro (varchar)
- chuc_vu (varchar)
- phong_ban_id (int)
- luong_co_ban (float)
- ngay_vao_lam (date)
- trang_thai_lam_viec (varchar)
- ngay_tao (datetime)



BẢNG nhanvien_quyen:
- id (int)
- nhanvien_id (int)
- quyen_id (int)

BẢNG nhom_tai_lieu (*):
- id (int)
- ten_nhom (varchar)
- mo_ta (text)
- ngay_tao (datetime)
- nguoi_tao_id (int)

BẢNG phan_quyen_chuc_nang:
- id (int)
- quyen_id (int)
- ten_chuc_nang (varchar)
- mo_ta (varchar)
- co_quyen_xem (boolean)
- co_quyen_them (boolean)
- co_quyen_sua (boolean)
- co_quyen_xoa (boolean)
- ngay_tao (datetime)


BẢNG phong_ban:
- id (int)
- ten_phong (varchar)
- truong_phong_id (int)
- ngay_tao (datetime)

BẢNG quy_trinh_nguoi_nhan:
- id (int)
- step_id (int)
- nhan_id (int)

BẢNG quyen:
- id (int)
- ma_quyen (varchar)
- ten_quyen (varchar)
- nhom_quyen (varchar)

BẢNG tai_lieu:
- id (int)
- ten_tai_lieu (varchar)
- mo_ta (text)
- file_name (varchar)
- file_path (varchar)
- file_type (varchar)
- file_size (int)
- loai_tai_lieu (varchar)
- doi_tuong_xem (varchar)
- trang_thai (varchar)
- luot_xem (int)
- luot_tai (int)
- nguoi_tao_id (int)
- ngay_tao (datetime)
- ngay_cap_nhat (datetime)

BẢNG thong_bao:
- id (int)
- tieu_de (varchar)
- noi_dung (text)
- loai_thong_bao (varchar)
- duong_dan (varchar)
- nguoi_nhan_id (int)
- da_doc (boolean)
- ngay_tao (datetime)
- ngay_doc (datetime)

VIEW v_don_nghi_phep_chi_tiet:
- id (từ đơn nghỉ phép)
- nhan_vien_id
- ho_ten_nhan_vien (từ bảng nhan_vien)
- ten_phong_ban (từ bảng phong_ban)
- ngay_bat_dau
- ngay_ket_thuc
- ly_do
- trang_thai_duyet
- nguoi_duyet_id
- ho_ten_nguoi_duyet (từ bảng nhan_vien)
- ngay_duyet
- ngay_tao

"""
