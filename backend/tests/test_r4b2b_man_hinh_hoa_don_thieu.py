# -*- coding: utf-8 -*-
"""Đợt R4b-2b (23/10/2026) — MÀN HÌNH "HÓA ĐƠN CÒN THIẾU".

Đợt R4b-2a thêm hai cột hóa đơn trên dòng bút toán và hai cửa API. Theo ranh giới 09/9/2026,
một con số không có cửa cho NGƯỜI nhập là việc còn thiếu — nên đợt này dựng màn hình.

BỐN LUẬT, và luật 2 là chỗ đáng đọc kỹ:

 1. Màn hình có thật, và nó có CỬA GHI (gọi POST) — `test_man_hinh_co_cua_nhap` đọc chính điều ấy.
 2. Danh sách vai của `/hoa-don-thieu` KHÔNG BAO GIỜ rộng hơn `/ket-so`. Đêm 22/10 Đợt R4b-2a tự
    mở cửa ghi cho `ketoan_tt` và `ketoan_truong`, và `test_le2b_ba_vai_ke_toan` đỏ ngay vì hai
    vai ấy có bảng ký đã chốt. Luật này giữ cho chuyện ấy không lặp lại ở tầng màn hình.
 3. Màn hình phải được KHAI trong MENU_ROLES. `ks_ma_tran` ghi rõ quy ước: "trang không liệt kê
    trong MENU_ROLES = ai đăng nhập cũng thấy" — nên quên khai không phải là an toàn.
 4. Mục menu có thật trong Shell, trỏ đúng đường dẫn.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(os.path.dirname(ROOT), "web")
DUONG = "/hoa-don-thieu"


def _doc(p: str) -> str:
    assert os.path.isfile(p), f"Thiếu {p}"
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_r4b2b_1_man_hinh_co_that_va_co_cua_ghi():
    p = os.path.join(WEB, "app", "hoa-don-thieu", "page.tsx")
    s = _doc(p)
    assert '"/books/hoa-don-thieu/ghi"' in s, (
        "Màn hình không gọi cửa ghi. Không có cửa ghi thì hai cột hóa đơn của Đợt R4b-2a vẫn là "
        "việc còn thiếu theo ranh giới 09/9/2026.")
    assert 'method: "POST"' in s, "Cửa ghi phải là POST."
    assert "/books/hoa-don-thieu?" in s, "Màn hình phải đọc danh sách từ cửa đọc của máy chủ."
    assert "133" not in s and "3331" not in s, (
        "Màn hình đang chép lại LUẬT ĐẾM (nhánh tài khoản thuế) của máy chủ. Hai nơi khai cùng "
        "một luật thì sớm muộn lệch, và lúc lệch không ai biết bên nào đúng — luật ấy chỉ nằm ở "
        "`services/books.py`.")


def test_r4b2b_2_vai_KHONG_BAO_GIO_rong_hon_ket_so():
    """Bài học đêm 22/10: Đợt R4b-2a tự mở cửa ghi cho hai vai có bảng ký đã chốt."""
    import sys
    sys.path.insert(0, ROOT)
    from app.services.access import MENU_ROLES
    assert DUONG in MENU_ROLES, "chưa khai — xem luật 3"
    cua_toi, cua_ket_so = set(MENU_ROLES[DUONG]), set(MENU_ROLES["/ket-so"])
    thua = cua_toi - cua_ket_so
    assert not thua, (
        f"Màn hình {DUONG} đang mở cho vai mà `/ket-so` không có: {sorted(thua)}. Hai màn hình "
        "cùng họ Sổ & kỳ kế toán, nên rộng hơn là một quyết định cấp quyền — phải sửa bảng ký "
        "trước, bằng một quyết định có chữ ký, không phải bằng một dòng thêm vào `access.py`.")


def test_r4b2b_5_khong_de_lai_mon_no_menu_khong_cua():
    """Vai nào mở được màn hình này thì phải gọi được cửa đọc của nó.

    `BASE_VIEW` có `robot_ks`, nhưng `books.READ` thì không — khai thẳng `BASE_VIEW` là đẻ ra
    một cặp "mở được menu mà không gọi được cửa nào", và `test_lg4_mon_no_khong_duoc_DAI_THEM`
    đỏ đúng chỗ ấy trên PR #442 ngày 23/10/2026.

    Luật này nằm ở đây để người sửa màn hình thấy ngay, thay vì gặp một phép thử ở tệp khác.
    """
    import sys
    sys.path.insert(0, ROOT)
    from app.api.v1.books import READ
    from app.services.access import MENU_ROLES
    thua = set(MENU_ROLES[DUONG]) - set(READ)
    assert not thua, (
        f"Vai {sorted(thua)} mở được {DUONG} nhưng không nằm trong `books.READ`, nên mở ra là "
        "một màn hình trắng. Sửa một trong hai chiều — và chiều TRỪ (bỏ khỏi menu) không cấp "
        "thêm quyền cho ai, nên nó là chiều mặc định.")


def test_r4b2b_3_phai_khai_trong_MENU_ROLES_va_MAN_HINH_API():
    import sys
    sys.path.insert(0, ROOT)
    from app.services.access import MAN_HINH_API, MENU_ROLES
    assert DUONG in MENU_ROLES, (
        "Chưa khai trong MENU_ROLES. `ks_ma_tran` ghi rõ: trang không liệt kê = AI ĐĂNG NHẬP "
        "CŨNG THẤY. Quên khai không phải là an toàn.")
    assert DUONG in MAN_HINH_API, "Chưa khai nhóm API màn hình được chạm."
    assert "/api/v1/books" in MAN_HINH_API[DUONG], "Màn hình gọi /api/v1/books — phải khai đúng."


def test_r4b2b_4_co_muc_menu_tro_dung_duong_dan():
    s = _doc(os.path.join(WEB, "components", "Shell.tsx"))
    assert re.search(r'\["Hóa đơn còn thiếu",\s*"/hoa-don-thieu"\]', s), (
        "Thiếu mục menu. Màn hình không có lối vào thì người phải dùng nó không với tới — đúng "
        "một trong ba chỗ hỏng mà bản rà 09/9/2026 tìm được.")
