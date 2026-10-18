# -*- coding: utf-8 -*-
"""HS-8 — hai lớp đã viết mà KHÔNG AI GỌI, và một hộp mở ngoài tầm nhìn.

Chủ tịch mở màn hình Tài khoản ngày 17/10 và báo hai chuyện: «click nút Sửa không ăn» và «chưa
sắp xếp theo thứ tự». Soát ra cả hai đều là cùng một kiểu lỗi, và nó không phải lỗi phép tính:

  · `ho_so_nhan_vien.xep_bang_tai_khoan` — gom theo phòng, xếp theo cấp bậc — viết ngày 15/10
    đúng như bản vẽ Chủ tịch duyệt, có phép thử riêng, XANH HẾT. Và không một chỗ nào gọi nó.
    Bảng 121 dòng vẫn xếp theo `username`.
  · Hộp Sửa mở RA THẬT, nhưng nó nằm sau `</table>` của bảng 121 dòng. Người bấm nút ở dòng đầu
    không thấy gì và kết luận nút hỏng.

BÀI HỌC CHUNG, và lý do tệp này tồn tại: **một lớp tính không có ai gọi thì chưa phải việc đã
xong**, và **một ô mở ra ngoài tầm nhìn thì về mặt người dùng là không mở**. Phép thử của vòng cũ
xanh vì nó thử đúng cái hàm ấy — không thử xem màn hình có dùng hàm ấy không. Hai phép thử dưới
đây canh đúng mối nối ấy.
"""
import os, re, sys, tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_hs8.db")
for _f in (_DB, _DB + "-journal"):
    if os.path.exists(_f):
        try: os.remove(_f)
        except OSError: pass
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEP_MAN = os.path.join(GOC, "web", "app", "access", "page.tsx")


def test_hs8_1_bang_tai_khoan_xep_theo_so_do_to_chuc_chu_khong_theo_ten():
    """Thứ tự Chủ tịch chốt 15/10: phòng theo sơ đồ tổ chức → trong phòng theo cấp bậc → cùng cấp
    thì theo họ tên. KHÔNG theo bảng chữ cái của tên đăng nhập.

    Phép thử so cửa thật với chính hàm xếp, nên nó đỏ ngay ngày ai đó bỏ lời gọi ấy đi — đúng
    tình trạng đã tồn tại hai ngày mà không phép thử nào thấy.
    """
    from fastapi.testclient import TestClient
    from app.db.session import SessionLocal
    from app.main import app
    from app.services import ho_so_nhan_vien as HSNV
    from app.services.access_admin import danh_sach_tai_khoan

    with TestClient(app):
        db = SessionLocal()
        try:
            rows = danh_sach_tai_khoan(db)
            assert len(rows) > 1, "Dữ liệu thử chỉ có một tài khoản — không kết luận được thứ tự."

            mong = [ng for n in HSNV.xep_bang_tai_khoan([dict(r) for r in rows])["nhom"]
                    for ng in n["nguoi"]]
            assert [r["id"] for r in rows] == [r["id"] for r in mong], (
                "Bảng tài khoản không xếp theo `xep_bang_tai_khoan`. Hàm ấy viết 15/10 đúng bản vẽ "
                "Chủ tịch duyệt và nằm đó không ai gọi suốt hai ngày — phép thử của nó vẫn xanh, "
                "vì nó thử hàm chứ không thử mối nối.")

            # Và thứ tự ấy phải KHÁC thứ tự theo tên đăng nhập — nếu trùng thì phép thử trên
            # không chứng minh được gì.
            theo_ten = sorted(rows, key=lambda r: r["username"])
            if [r["id"] for r in rows] == [r["id"] for r in theo_ten]:
                pytest.skip("Dữ liệu thử tình cờ cho hai thứ tự trùng nhau.")

            # Mỗi dòng mang sẵn cấp bậc để màn hình khỏi tự tính lại — tính lại là bản sao thứ hai.
            assert all("cap_bac" in r for r in rows), "Thiếu `cap_bac` trên dòng tài khoản."
        finally:
            db.close()


def test_hs8_2_hop_sua_va_hop_ho_so_mo_o_TREN_bang():
    """Một ô mở ra ngoài tầm nhìn thì về mặt người dùng là KHÔNG MỞ.

    Bảng tài khoản có 121 dòng. Hộp đặt sau `</table>` thì cách chỗ bấm vài nghìn điểm ảnh, và
    Chủ tịch đã báo đúng chuyện ấy ngày 17/10 bằng câu «click không ăn».

    Phép thử so VỊ TRÍ trong mã nguồn, vì đây là thứ trôi rất dễ: lần sau ai thêm một khối vào
    giữa là hộp lại tụt xuống dưới bảng, và không có gì báo.
    """
    assert os.path.exists(TEP_MAN), f"Thiếu {TEP_MAN}"
    src = open(TEP_MAN, encoding="utf-8").read()

    vi_tri = {}
    for ten, mau in (("hop_ho_so", r"\{hsUid !== null && <HoSoNhanVien"),
                     ("hop_sua", r"\{suaUid !== null && acc && <SuaTaiKhoan"),
                     ("than_bang", r"<tbody>\{rows\.map")):
        m = re.search(mau, src)
        assert m, f"Không tìm thấy `{ten}` trong màn hình Tài khoản."
        vi_tri[ten] = m.start()

    for ten in ("hop_ho_so", "hop_sua"):
        assert vi_tri[ten] < vi_tri["than_bang"], (
            f"`{ten}` nằm SAU thân bảng 121 dòng. Bấm nút ở dòng đầu thì hộp mở cách đó vài nghìn "
            "điểm ảnh, người dùng không thấy gì và kết luận nút hỏng — đúng điều Chủ tịch báo "
            "ngày 17/10.")
