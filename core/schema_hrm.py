HRM_SCHEMA = """
BẢNG du_an:
- id (INT)
- ten_du_an (TEXT)
- ngay_bat_dau (DATE)
- ngay_ket_thuc (DATE)


BẢNG nhan_vien:
- id (INT)
- ho_ten (TEXT)
- phong_ban (TEXT)
- chuc_vu (TEXT)

BẢNG cham_cong:
- nhan_vien_id (INT)
- ngay (DATE)
- gio_vao (TIME)
- gio_ra (TIME)

BẢNG luong:
- nhan_vien_id (INT)
- thang (INT)
- nam (INT)
- luong_co_ban (FLOAT)
"""
