# -*- coding: utf-8 -*-
"""KS-20e · Email + PDF sau thanh toán đặt phòng VTD (Chủ tịch duyệt bản xem thử 07/11/2026, theo mẫu Agoda).

  1. Đơn đã xác nhận → tải được phiếu xác nhận và hóa đơn đặt phòng (PDF), chữ tiếng Việt đủ dấu, có từng phòng P1/P2.
  2. Chưa thanh toán → không có hóa đơn; chưa xác nhận → không có phiếu.
  3. Email xác nhận song ngữ, đính kèm đúng hai PDF; người phát hành lấy từ hồ sơ pháp nhân công ty mẹ.
  4. Màn «Pháp nhân» sửa được địa chỉ + hotline; bản nâng cấp ghi đúng giá trị Chủ tịch đưa cho mã VTD.
  5. Giao diện: «Tải phiếu xác nhận» / «Tải hóa đơn» trong trang đơn.
"""
import datetime as dt
from pathlib import Path

import pytest

from tests.test_at1_am_thuc import db  # noqa: F401
from tests.test_ks13_khach_san_vtd import RA, VAO
from tests.test_ks14_dat_phong_vtd import NAY, _tk, k3  # noqa: F401
from tests.test_ks20b_chia_phong import hai  # noqa: F401

GOC = Path(__file__).resolve().parents[2]


def _don_tra(db, hai, tra=True):
    from app.models.don_ks_vtd import ThanhToanKsVtd
    from app.services import don_ks_vtd as KV
    k, g, fg = hai
    d = KV.dat(db, _tk(db), k.id, {"vao": VAO, "ra": RA, "chon": [{"goi_id": g.id, "so": 1}, {"goi_id": fg.id, "so": 1}],
                                    "chia": [{"nl": 2}, {"nl": 1, "te": 1, "tuoi": [7]}], "ho_ten": "Nguyễn Thị Lan",
                                    "lien_he": "0901 000 001", "email": "lan@example.com", "dong_y": True}, NAY)
    if tra:
        db.add(ThanhToanKsVtd(don_id=d.id, kenh="qr", so_tien=int(d.tong), trang_thai="tu_khop", luc=NAY))
        db.flush()
        KV._sau_khi_tra(db, d, NAY)
    db.commit()
    return d


def _chu(pdf: bytes) -> str:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf)
    return " ".join(" ".join(doc[i].get_textpage().get_text_bounded().split()) for i in range(len(doc)))


def _can_phong():
    from app.services import phieu_ks_vtd as PK
    if PK.phong_chu() is None:
        pytest.skip("máy thử không có phông DejaVu / Arial — ảnh máy chủ cài fonts-dejavu-core")


def test_ks20e_1_pdf_phieu_va_hoa_don(db, hai, monkeypatch):
    from app.services import don_ks_vtd as KV
    from app.services import phieu_ks_vtd as PK
    _can_phong()
    monkeypatch.setattr(KV, "GUI_XAC_NHAN", lambda *a: True)
    d = _don_tra(db, hai)
    assert d.trang_thai == "da_xac_nhan"
    p = _chu(PK.pdf_phieu(db, d))
    for t in ("Booking", "Confirmation", "Phiếu xác nhận đặt phòng", d.ma, "Nguyễn Thị Lan", "Family Suite", "P1", "P2",
              "Xác nhận điện tử", "Rooming list"):
        assert t in p, t
    h = _chu(PK.pdf_hoa_don(db, d))
    for t in ("Hóa đơn đặt phòng khách sạn", "Hotel Booking Invoice", "NGUYỄN THỊ LAN", f"HD-{d.ma}", "TỔNG CỘNG TIỀN THANH TOÁN",
              "Trong đó thuế GTGT 8%", "không thay thế hóa đơn GTGT", "QR chuyển khoản"):
        assert t in h, t
    assert f"{int(d.tong):,}".replace(",", ".") in h


def test_ks20e_2_chua_tra_thi_khong_co(db, hai):
    from app.services import phieu_ks_vtd as PK
    d = _don_tra(db, hai, tra=False)
    with pytest.raises(PK.LoiPhieu, match="đã thanh toán"):
        PK.kiem(d, "hoa_don")
    with pytest.raises(PK.LoiPhieu, match="đã được xác nhận"):
        PK.kiem(d, "phieu")


def test_ks20e_3_email_dinh_kem_hai_pdf(db, hai, monkeypatch):
    from app.models.core import Company
    from app.services import don_ks_vtd as KV
    _can_phong()
    monkeypatch.setattr(KV, "GUI_XAC_NHAN", lambda *a: True)
    c = db.query(Company).filter(Company.code == "VTD").one()
    c.address, c.phone = "242 Trần Hưng Đạo, TP. Hồ Chí Minh", "028 6261 6365"
    db.commit()
    d = _don_tra(db, hai)
    m = KV.thu_xac_nhan(d, "Khách sạn Biển Xanh")
    assert m["Subject"] == f"Xác nhận đặt phòng với Vietourist – Mã đặt phòng: {d.ma}"
    ten = sorted(p.get_filename() for p in m.iter_attachments())
    assert ten == [f"Hoa-don-{d.ma}.pdf", f"Phieu-xac-nhan-{d.ma}.pdf"]
    html = m.get_body(("html",)).get_content()
    for t in ("Đơn đặt phòng của quý khách đã được xác nhận!", "Your booking is confirmed", "242 Trần Hưng Đạo", "028 6261 6365",
              "Chính sách hủy · Cancellation policy", "Family Suite"):
        assert t in html, t


def test_ks20e_4_phap_nhan_dia_chi_hotline():
    m = (GOC / "backend/alembic/versions/ks20e1a3c5e7b9d135_dia_chi_hotline_phap_nhan.py").read_text(encoding="utf-8")
    assert 'DIA_CHI = "242 Trần Hưng Đạo, TP. Hồ Chí Minh"' in m and 'HOTLINE = "028 6261 6365"' in m
    assert "WHERE code = 'VTD' AND address = ''" in m                  # không đè giá trị Kế toán đã sửa
    api = (GOC / "backend/app/api/v1/companies.py").read_text(encoding="utf-8")
    assert '@router.post("/companies/{cid}/lien-he")' in api
    w = (GOC / "web/app/companies/page.tsx").read_text(encoding="utf-8")
    assert "Địa chỉ &amp; hotline in trên phiếu" in w and "/lien-he" in w


def test_ks20e_5_giao_dien_tai_pdf():
    c = (GOC / "web/components/cong/KhachSanVtd.tsx").read_text(encoding="utf-8")
    assert "Tải phiếu xác nhận (PDF)" in c and "Tải hóa đơn (PDF)" in c and "/pdf/${loai}" in c
    assert (GOC / "backend/app/static/logo/khoachu-holdings-ngang.svg").exists()
