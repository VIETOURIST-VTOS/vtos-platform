# -*- coding: utf-8 -*-
"""ĐỢT DỌN-MISA 01/11/2026 — MỘT TỆP PHÉP THỬ, MỘT CƠ SỞ DỮ LIỆU: BA LUẬT CANH.

Ba phép thử `test_misa` đỏ suốt từ 23/10/2026, và cả ba đỏ vì TIỀN CỦA TỆP KHÁC chảy sang, không
vì một phép tính nào sai. Đã đo bằng bảy lượt chạy trong cùng một lần bấm (xem ghi chú commit của
đợt này): [0] trên main CHƯA VÁ và [6] trên main ĐÃ VÁ của Đợt R2-KC1 cho kết quả GIỐNG HỆT NHAU —
3 failed / 42 passed. Nên nó là nợ CÓ SẴN.

TỆP THẮNG CUỘC ĐUA KHÔNG BAO GIỜ ĐỎ — tệp đỏ là tệp thua. Đó là lý do lỗi này sống lâu: nó không
hiện ra ở chỗ gây ra nó.

MỘT BÀI HỌC KHÔNG THÀNH LUẬT THÌ CHỈ LÀ MỘT CÂU CHUYỆN. `test_e18` thậm chí đã GHI nguyên nhân
này trong mã của nó từ 15/10 — "SessionLocal lúc ấy trỏ vào CSDL của tệp nào nhập trước" — mà
chuyện vẫn tái diễn thêm hai tuần, vì nó chỉ là một dòng ghi chú chứ không phải một hàng rào.
"""
import os
import re
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
TESTS = GOC / "backend" / "tests"


def test_donmisa_1_tep_da_chuyen_thi_khong_con_tu_dat_database_url():
    """TỰ ĐỊNH NGHĨA: tệp nào ĐÃ dùng `dung_csdl_rieng` thì không được còn đặt `DATABASE_URL`.

    Không gõ tay một danh sách, và tự lớn lên mỗi khi có tệp được chuyển sang cách mới.

    BẢN ĐẦU của luật này đòi KHÔNG tệp nào trong `tests/` đặt biến ấy, và lần chạy 24/10/2026 đo ra
    283 TỆP đang đặt — tức đó là LỐI VIẾT CHUNG của cả kho, không phải vài tệp cá biệt. Một luật
    đòi sửa 283 tệp thì không phải một luật, nó là một dự án; và một luật không bao giờ xanh được
    thì chẳng mấy chốc có người tắt nó đi. Chủ tịch chốt 25/10/2026: canh phần ĐÃ chuyển, và ghi
    con số kia vào sổ làm một món nợ ĐÃ ĐO ĐƯỢC. Đo lại 01/11/2026: 286 tệp.
    """
    xau = []
    for p in sorted(TESTS.glob("test_*.py")):
        s = p.read_text(encoding="utf-8")
        if "dung_csdl_rieng" in s and re.search(r'os\.environ\[.DATABASE_URL.\]\s*=', s):
            xau.append(p.name)
    assert not xau, "tep da chuyen ma van tu dat DATABASE_URL: " + repr(xau)


def test_donmisa_2_main_nhap_mo_dun_khong_nhap_ten():
    """`main.py` phải NHẬP MÔ-ĐUN, không nhập TÊN.

    Nhập tên thì `SessionLocal` và `engine` bị buộc LÚC IMPORT, mà chính `main` mới là nơi tạo
    bảng và gieo dữ liệu — nên tệp nào import `app.main` trước thì `main` cầm engine của tệp ấy
    VĨNH VIỄN, và `dung_csdl_rieng` gắn lại cũng không tới được nó.

    Production chạy y hệt: chỉ có một cơ sở dữ liệu, nên trả lúc gọi hay trả lúc import đều ra
    cùng một vật. Khác biệt chỉ hiện ra khi có người ĐỔI nó — mà đổi thì chỉ phép thử mới làm.
    """
    s = (GOC / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.db.session import SessionLocal" not in s, "main.py nhap TEN tro lai"
    assert "from app.db import session as _db" in s, "main.py chua nhap mo-dun"
    assert "_db.SessionLocal()" in s and "_db.engine" in s, "main.py chua goi qua mo-dun"


def test_donmisa_3_do_that_hai_lan_goi_ra_hai_so_khac_nhau():
    """ĐO THẬT, không tin bản khai: gọi cửa ấy hai lần và so hai địa chỉ sổ."""
    from app.db import session as S
    from csdl_rieng import dung_csdl_rieng

    cu = (S.engine, S.SessionLocal)
    try:
        a = dung_csdl_rieng("phep_thu_a")
        e1 = S.engine
        b = dung_csdl_rieng("phep_thu_b")
        e2 = S.engine
        assert a != b, "hai lan goi ra cung mot duong dan"
        assert e1 is not e2, "engine khong doi — gan lai khong co tac dung"
        assert str(e2.url) == b, "engine khong tro vao so vua khai"
    finally:
        S.engine, S.SessionLocal = cu
