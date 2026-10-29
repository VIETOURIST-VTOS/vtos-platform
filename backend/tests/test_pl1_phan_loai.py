# -*- coding: utf-8 -*-
"""PL-1 · Phân loại nhà hàng (Chủ tịch duyệt 30/10/2026).

  1. «Đặc sản địa phương»: máy tự gắn khi nguồn là TasteAtlas; đổi tay qua đề xuất → chốt; gỡ phải ghi lý do.
  2. Bậc: máy gợi ý (thực đơn đang bán → Michelin ₫ → sao Michelin → không gợi ý); NV ĐH đề xuất, TP ĐH chốt;
     người đề xuất không tự chốt; Chủ tịch chốt ngay.
  3. Cổng khách: chỉ bậc đã chốt; lọc theo loại / bậc; mục riêng «Đặc sản địa phương».
  4. Excel Michelin: tệp mẫu → điền → đọc thử không ghi → ghi; ô trống giữ nguyên; giá trị lạ báo lỗi.
"""
import pytest

from tests.test_at1_am_thuc import db, _u, HN  # noqa: F401
from tests.test_at2a_album import _nh


def _ct(s):
    from app.models.core import User
    x = User(username="ct", full_name="CT", role="chutich", password_hash="x"); s.add(x); s.commit()
    return x


def _nguon(s, nh, nguon):
    nh.nguon = nguon; s.commit()
    return nh


def test_dac_san_tu_dong_va_doi_tay(db):
    from app.services import phan_loai_nh as PL, nha_hang as N
    from app.models.core import AuditLog
    ta = _nguon(db, _nh(db, "1946 Cửa Bắc"), "TasteAtlas 28/10/2026")
    mi = _nguon(db, _nh(db, "Akuna"), "MICHELIN Guide 29/10/2026")
    assert PL.dac_san(ta) and not PL.dac_san(mi)
    # gỡ phải có lý do
    with pytest.raises(N.LoiNhaHang, match="lý do"):
        PL.de_xuat_dac_san(db, _u(db, "dh"), ta.id, "go", "")
    PL.de_xuat_dac_san(db, _u(db, "dh"), ta.id, "go", "Nhà hàng chuyển sang món Âu")
    assert PL.dac_san(ta)                          # đề xuất chưa có hiệu lực
    with pytest.raises(N.LoiNhaHang):
        PL.chot_dac_san(db, _u(db, "dh"), ta.id, True)          # NV không chốt
    PL.chot_dac_san(db, _u(db, "tp"), ta.id, True)
    assert not PL.dac_san(ta) and ta.dac_san_ly_do.startswith("Nhà hàng")
    # TP ĐH đề xuất → chính TP đó không tự chốt; TP khác chốt được
    PL.de_xuat_dac_san(db, _u(db, "tp"), mi.id, "gan", "")
    with pytest.raises(N.LoiNhaHang, match="không tự chốt"):
        PL.chot_dac_san(db, _u(db, "tp"), mi.id, True)
    PL.chot_dac_san(db, _u(db, "tp2"), mi.id, True)
    assert PL.dac_san(mi)
    # Chủ tịch: về theo máy, có hiệu lực ngay
    PL.de_xuat_dac_san(db, _ct(db), ta.id, "may")
    assert PL.dac_san(ta) and ta.dac_san_tay == ""
    assert db.query(AuditLog).filter(AuditLog.action.like("nha_hang_dac_san%")).count() >= 5


def test_goi_y_bac(db):
    from app.services import phan_loai_nh as PL, nha_hang as N
    nh = _nh(db)
    assert PL.goi_y(nh, [], HN) == ("", "Chưa đủ căn cứ")
    PL.ghi_michelin(db, _u(db, "dh"), nh.id, "sao1", 0)
    assert PL.goi_y(nh, [], HN)[0] == "cao_cap"
    PL.ghi_michelin(db, _u(db, "dh"), nh.id, "sao1", 4)
    assert PL.goi_y(nh, [], HN) == ("sang_trong", "Michelin ₫₫₫₫")
    with pytest.raises(N.LoiNhaHang):
        PL.ghi_michelin(db, _u(db, "dh"), nh.id, "sao9", 0)
    with pytest.raises(N.LoiNhaHang):
        PL.ghi_michelin(db, _u(db, "mkt"), nh.id, "bib", 1)       # Marketing không ghi
    # thực đơn đang bán thắng ký hiệu Michelin: trung vị 300k → Tầm trung
    for g in (200_000, 300_000, 900_000):
        N.luu_thuc_don(db, _u(db, "dh"), nh.id, {"ten": f"Set {g}", "loai": "set", "gia_nguoi_lon": g})
    from app.models.nha_hang import ThucDonNhaHang
    tds = db.query(ThucDonNhaHang).filter_by(nha_hang_id=nh.id).all()
    assert PL.goi_y(nh, tds, HN)[0] == "tam_trung"
    assert [PL.bac_theo_tien(x) for x in (249_999, 250_000, 600_000, 1_500_000, 1_500_001)] == \
        ["binh_dan", "tam_trung", "cao_cap", "cao_cap", "sang_trong"]


def test_de_xuat_chot_bac_va_cong(db):
    from app.services import phan_loai_nh as PL, nha_hang as N
    a = _nguon(db, _nh(db, "Akuna"), "MICHELIN Guide 29/10/2026")
    b = _nguon(db, _nh(db, "1946 Cửa Bắc"), "TasteAtlas 28/10/2026")
    PL.de_xuat_bac(db, _u(db, "dh"), a.id, "sang_trong")
    assert a.bac == "" and a.bac_de_xuat == "sang_trong"
    o = {x["id"]: x for x in N.danh_sach_cong(db)["nha_hang"]}
    assert o[a.id]["bac"] == "" and o[a.id]["bac_ten"] == ""         # chưa chốt → cổng không hiện
    with pytest.raises(N.LoiNhaHang):
        PL.chot_bac(db, _u(db, "dh"), a.id, True)
    PL.chot_bac(db, _u(db, "tp"), a.id, True)
    assert a.bac == "sang_trong" and a.bac_de_xuat == "" and a.bac_chot_boi == "tp"
    # trả lại: giữ bậc cũ
    PL.de_xuat_bac(db, _u(db, "dh"), a.id, "cao_cap")
    PL.chot_bac(db, _u(db, "tp"), a.id, False)
    assert a.bac == "sang_trong"
    with pytest.raises(N.LoiNhaHang, match="không có đề xuất"):
        PL.chot_bac(db, _u(db, "tp"), a.id, True)
    # Chủ tịch chốt ngay
    PL.de_xuat_bac(db, _ct(db), b.id, "binh_dan")
    assert b.bac == "binh_dan"
    PL.ghi_michelin(db, _u(db, "dh"), a.id, "sao1", 4)
    c = N.danh_sach_cong(db)
    o = {x["id"]: x for x in c["nha_hang"]}
    assert o[a.id]["bac_ten"] == "Sang trọng" and o[a.id]["michelin"] == "Michelin 1 sao" and o[a.id]["la_michelin"]
    assert o[b.id]["dac_san"] and not o[a.id]["dac_san"]
    assert c["so_dac_san"] == 1 and [x["id"] for x in c["dac_san_noi_bat"]] == [b.id] and c["so_michelin"] == 1
    assert [x["id"] for x in N.danh_sach_cong(db, loai="dac_san")["nha_hang"]] == [b.id]
    assert [x["id"] for x in N.danh_sach_cong(db, loai="michelin")["nha_hang"]] == [a.id]
    assert [x["id"] for x in N.danh_sach_cong(db, bac="sang_trong")["nha_hang"]] == [a.id]
    assert N.danh_sach_cong(db, bac="tam_trung")["nha_hang"] == []
    # màn nội bộ
    d = PL.ds(db, _u(db, "tp"))
    assert d["dem"]["dac_san"] == 1 and d["dem"]["da_chot"] == 2 and d["duoc_chot"] and not PL.ds(db, _u(db, "mkt"))["duoc_de_xuat"]


def test_excel_michelin(db):
    from io import BytesIO
    from openpyxl import load_workbook, Workbook
    from app.services import phan_loai_nh as PL, nha_hang as N
    a = _nguon(db, _nh(db, "Akuna"), "MICHELIN Guide 29/10/2026")
    a.nguon_ref = "MICHELIN Guide 2026 · 38 · https://guide.michelin.com/vn/en/x/akuna"
    b = _nguon(db, _nh(db, "Ăn Thôi"), "MICHELIN Guide 29/10/2026")
    _nguon(db, _nh(db, "1946 Cửa Bắc"), "TasteAtlas 28/10/2026")
    db.commit()
    ws = load_workbook(BytesIO(PL.mau_xlsx(db)))["Michelin"]
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == PL.COT_MAU and len(rows) == 3          # chỉ nhà hàng Michelin
    assert rows[1][3].startswith("https://guide.michelin.com")
    wb = Workbook(); w = wb.active
    w.append(PL.COT_MAU)
    w.append([a.ma, "Akuna", "", "", "1 sao", "₫₫₫₫"])
    w.append([b.ma, "Ăn Thôi", "", "", "Bib Gourmand", 1])
    w.append(["NH-XXX", "?", "", "", "1 sao", "₫"])
    w.append([a.ma, "Akuna", "", "", "hạng lạ", ""])
    o = BytesIO(); wb.save(o)
    r = PL.nhap_xlsx(db, _u(db, "dh"), "m.xlsx", o.getvalue(), thu=True)
    assert len(r["doi"]) == 2 and len(r["loi"]) == 2 and not r["da_ghi"]
    assert a.michelin_hang == ""                                   # đọc thử không ghi
    with pytest.raises(N.LoiNhaHang):
        PL.nhap_xlsx(db, _u(db, "mkt"), "m.xlsx", o.getvalue(), thu=False)
    PL.nhap_xlsx(db, _u(db, "dh"), "m.xlsx", o.getvalue(), thu=False)
    assert (a.michelin_hang, a.michelin_gia, b.michelin_hang, b.michelin_gia) == ("sao1", 4, "bib", 1)
    # ô trống giữ nguyên
    wb = Workbook(); w = wb.active; w.append(PL.COT_MAU); w.append([a.ma, "", "", "", "", ""])
    o = BytesIO(); wb.save(o)
    r = PL.nhap_xlsx(db, _u(db, "dh"), "m.xlsx", o.getvalue(), thu=False)
    assert r["doi"] == [] and r["giu_nguyen"] == 1 and a.michelin_gia == 4
