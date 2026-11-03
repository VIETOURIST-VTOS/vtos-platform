# -*- coding: utf-8 -*-
"""TK-1 · Khách tự thiết kế tour đoàn — giai đoạn 1 (Chủ tịch 04/11/2026: tạm tính nối khách sạn, nhà hàng, vé máy bay
có sẵn; xe và chi phí khác Điều hành nhập; biên tạm tính 10%; «làm luôn giai đoạn 1»).

  1. Đơn giá đoàn: Điều hành nhập → chờ duyệt; người nhập không tự duyệt; TP ĐH duyệt → hiệu lực; Sales không xem.
  2. Tạm tính: khách sạn từ gói VTD (× phòng × thuế phí), bữa từ thực đơn, xe chọn đủ chỗ, vé bay theo chặng,
     dịch vụ theo đơn vị; giá bán = vốn ÷ 0,9 làm tròn lên nghìn; thiếu giá ghi riêng, không tính 0.
  3. Tour xa (châu Âu / Mỹ / Canada / Anh): HDV → trưởng đoàn kiêm HDV; tips vào «không bao gồm».
  4. Bỏ qua tiền trình duyệt gửi; chặn ngày đã qua, không người lớn, quá số khách.
  5. Gửi: tạo yêu cầu tour đoàn cho Sales (tạm tính ghi vào yêu cầu), phiên bản 1; gửi lại cùng mã → phiên bản 2,
     bản cũ «thay_the»; khách khác không sửa được. Sales thấy giá bán, không thấy giá vốn; Điều hành thấy cả hai.
  6. Nguồn theo điểm: khách sạn, nhà hàng khớp tỉnh; giá hiện ra là giá bán.
  8. TK-1b (Chủ tịch 04/11/2026): xe trong nước lấy bảng giá xe theo tuyến có sẵn (xe 45 chỗ, cột xe nhà, trùng tuyến
     + số ngày, đi xe từ TP HCM); lệch tuyến → đơn giá ngày xe nhà × số ngày; HDV lấy bảng thù lao HDV theo tuyến.
  7. Giao diện: màn khách và màn VTOS có đủ cửa.
"""
import datetime as dt
import math
from pathlib import Path

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_ks13_khach_san_vtd import _ks, _mo_ban

HOM_NAY = dt.date(2026, 11, 4)
NOW = dt.datetime(2026, 11, 4, 9, 0)
DI = "2026-12-18"


@pytest.fixture()
def nen(db, monkeypatch):
    from app.models.cong_ngoai import TaiKhoanNgoai
    from app.models.core import User
    from app.models.nha_hang import NhaHang, ThucDonNhaHang
    from app.services import cong_khach as K
    from app.services import nha_hang as NH
    db.add_all([User(username=t, full_name=t, role=v, password_hash="x") for t, v in (("ct", "chutich"), ("sa", "sales_admin"))])
    db.add_all([TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000001", ho_ten="Lan", trang_thai="hoat_dong"),
                TaiKhoanNgoai(loai="khach_hang", dien_thoai="0901000002", ho_ten="Bình", trang_thai="hoat_dong")])
    db.commit()
    k = _ks(db)
    lp, g, _x = _mo_ban(db, k)
    n = NhaHang(ma="NH-01", ten="Bếp Hàn", tinh_thanh="Đà Nẵng", hien_cong=True)
    db.add(n); db.flush()
    td = ThucDonNhaHang(nha_hang_id=n.id, ten="Set 6 món", loai="set", gia_nguoi_lon=300_000, gia_tre_em=None, so_khach_toi_thieu=10)
    db.add(td); db.commit()
    monkeypatch.setattr(NH, "mo_dat", lambda *a, **kw: True)
    monkeypatch.setattr(K, "_hom_nay", lambda: HOM_NAY, raising=False)
    return {"k": k, "lp": lp, "g": g, "n": n, "td": td}


def _tk(s, i=1):
    from app.models.cong_ngoai import TaiKhoanNgoai
    return s.execute(select(TaiKhoanNgoai).where(TaiKhoanNgoai.dien_thoai == f"090100000{i}")).scalars().one()


def _dg(s, nguoi="dh", duyet="tp", **d):
    from app.services import thiet_ke_doan as S
    x = S.luu_don_gia(s, _u(s, nguoi), d, now=NOW)
    if duyet:
        x = S.duyet_don_gia(s, _u(s, duyet), x["id"], True, now=NOW)
    return x


def _bang_gia(s):
    _dg(s, loai="xe", ten="Xe 16 chỗ", tu_cho=15, gia=2_000_000, pham_vi="dn")
    _dg(s, loai="xe", ten="Xe 29 chỗ", tu_cho=28, gia=3_000_000, pham_vi="dn")
    _dg(s, loai="hdv", ten="HDV suốt tuyến", gia=800_000, pham_vi="ca_hai")
    _dg(s, loai="bao_hiem", ten="Bảo hiểm nội địa", gia=20_000, pham_vi="dn")
    _dg(s, loai="ve_may_bay", ten="SGN-DAD", tu_diem="TP HCM", den_diem="Đà Nẵng", hang_ve="pho_thong",
        gia=1_500_000, gia_tre_em=1_200_000, gia_em_be=200_000)


def _thiet_ke(nen, **them):
    d = {"pham_vi": "dn", "khoi_hanh": "TP HCM", "ngay_di": DI, "nhom": "cong_ty", "nhip": "can_bang",
         "khach": {"nl": 20, "te": 2, "eb": 1, "tuoi_tre": [8, 9]}, "phong": {"p2": 11, "p3": 0, "p1": 0},
         "diem": [{"ten": "Đà Nẵng", "dem": 2, "ks": {"khach_san_id": nen["k"].id, "goi_id": nen["g"].id}}],
         "ngay": [{"trua": {"thuc_don_id": nen["td"].id}, "toi": {"tu_tuc": True}, "tham_quan": ["Bà Nà"]},
                  {"trua": {}, "toi": {"khac": "Hải sản Bé Mặn"}}, {}],
         "chang": [{"pt": "bay", "hang_bay": "Vietjet Air", "hang_ve": "pho_thong"}, {"pt": "xe"}],
         "dich_vu": ["hdv", "bao_hiem", "nuoc"], "ngan_sach": 1_000_000,
         "tong_ban": 1, "dong": [{"ban": 1}]}           # tiền trình duyệt gửi lên — phải bị bỏ qua
    d.update(them)
    return d


def test_tk1_1_don_gia_nhap_duyet_va_quyen(db, nen):
    from app.services import thiet_ke_doan as S
    x = S.luu_don_gia(db, _u(db, "tp"), {"loai": "xe", "ten": "Xe 29 chỗ", "tu_cho": 28, "gia": 3_000_000}, now=NOW)
    assert x["trang_thai"] == "cho_duyet"
    with pytest.raises(S.LoiThietKe, match="không tự duyệt"):
        S.duyet_don_gia(db, _u(db, "tp"), x["id"], True)
    with pytest.raises(S.LoiThietKe, match="Chỉ TP Điều hành"):
        S.duyet_don_gia(db, _u(db, "dh"), x["id"], True)
    assert S.duyet_don_gia(db, _u(db, "tp2"), x["id"], True, now=NOW)["trang_thai"] == "hieu_luc"
    with pytest.raises(S.LoiThietKe, match="số chỗ"):
        S.luu_don_gia(db, _u(db, "dh"), {"loai": "xe", "ten": "Xe", "gia": 1})
    with pytest.raises(S.LoiThietKe, match="chặng bay"):
        S.luu_don_gia(db, _u(db, "dh"), {"loai": "ve_may_bay", "ten": "Vé", "gia": 1})
    with pytest.raises(S.LoiThietKe, match="giá vốn"):
        S.ds_don_gia(db, _u(db, "kd"))
    with pytest.raises(S.LoiThietKe, match="Chỉ Điều hành"):
        S.luu_don_gia(db, _u(db, "kd"), {"loai": "hdv", "ten": "HDV", "gia": 1})
    # sửa dòng đang hiệu lực → về chờ duyệt (chưa duyệt thì không vào tạm tính)
    y = S.luu_don_gia(db, _u(db, "dh"), {"loai": "xe", "ten": "Xe 29 chỗ", "tu_cho": 28, "gia": 3_200_000}, x["id"], now=NOW)
    assert y["trang_thai"] == "cho_duyet" and y["gia"] == 3_200_000


def test_tk1_2_tam_tinh_tu_nguon_that(db, nen):
    from app.services import khach_san_vtd as KS
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    tk = S.chuan_hoa(_thiet_ke(nen), HOM_NAY)
    dt_ = S.du_toan(db, tk)
    d = {x["nhom"] + "|" + x["ten"]: x for x in dt_["dong"]}
    p = KS.gia_luu(nen["g"], KS._mua_cua(db, [nen["g"].id])[nen["g"].id], dt.date(2026, 12, 18), dt.date(2026, 12, 20))
    ks = next(x for x in dt_["dong"] if x["nhom"] == "Khách sạn")
    assert ks["von"] == round(p["tong"] * 11 * 1.15)
    an = next(x for x in dt_["dong"] if x["nhom"] == "Ăn uống")
    assert an["von"] == 300_000 * 22                                   # trẻ em chưa có giá → tính giá người lớn
    xe = next(x for x in dt_["dong"] if x["nhom"] == "Xe")
    assert xe["ten"] == "Xe 29 chỗ" and xe["von"] == 3_000_000 * 3     # 22 ghế → xe 29 chỗ, 3 ngày
    ve = next(x for x in dt_["dong"] if x["nhom"] == "Vé máy bay")
    assert ve["von"] == 1_500_000 * 20 + 1_200_000 * 2 + 200_000
    bh = next(x for x in dt_["dong"] if x["ten"] == "Bảo hiểm nội địa")
    assert bh["von"] == 20_000 * 23
    for x in dt_["dong"]:
        assert x["ban"] == math.ceil(x["von"] / 0.9 / 1000) * 1000
    assert dt_["tong_ban"] == sum(x["ban"] for x in dt_["dong"]) and dt_["tong_ban"] != 1
    thieu = {x["nhom"] for x in dt_["thieu_gia"]}
    assert {"Ăn uống", "Dịch vụ", "Vé tham quan"} <= thieu             # bữa tự ghi, nước chưa có giá, vé tham quan
    assert "Bữa tối tự túc" in dt_["khong_bao_gom"] and "Ăn sáng tại khách sạn" in dt_["bao_gom"]
    assert any("vượt ngân sách" in c for c in dt_["canh_bao"])
    assert dt_["so_ngay"] == 3 and dt_["bien"] >= 0.0999 and not dt_["can_chu_tich_duyet"]
    assert len(d) == len(dt_["dong"])


def test_tk1_2b_ve_chua_co_gia_va_xe_ghep(db, nen):
    from app.services import thiet_ke_doan as S
    _dg(db, loai="xe", ten="Xe 45 chỗ", tu_cho=45, gia=5_000_000)
    tk = S.chuan_hoa(_thiet_ke(nen, khach={"nl": 100, "te": 0, "eb": 0}, phong={"p2": 50}), HOM_NAY)
    dt_ = S.du_toan(db, tk)
    xe = next(x for x in dt_["dong"] if x["nhom"] == "Xe")
    assert xe["chi_tiet"].startswith("3 xe") and xe["von"] == 5_000_000 * 3 * 3
    assert any(x["nhom"] == "Vé máy bay" and "Sales báo giá" in x["ly_do"] for x in dt_["thieu_gia"])
    assert not any(x["nhom"] == "Vé máy bay" for x in dt_["dong"])
    assert len(S.NGUON_VE) >= 1                                          # chỗ nối API vé sau này


def test_tk1_3_tour_xa_truong_doan(db, nen):
    from app.services import thiet_ke_doan as S
    _dg(db, loai="truong_doan", ten="Trưởng đoàn kiêm HDV", gia=3_000_000, pham_vi="nn")
    d = _thiet_ke(nen, pham_vi="nn", diem=[{"ten": "Pháp", "dem": 3}, {"ten": "Thụy Sĩ", "dem": 2}],
                  ngay=[], chang=[{"pt": "bay"}, {"pt": "xe"}, {"pt": "bay"}], dich_vu=["hdv", "visa"])
    dt_ = S.du_toan(db, S.chuan_hoa(d, HOM_NAY))
    td = next(x for x in dt_["dong"] if x["ten"] == "Trưởng đoàn kiêm HDV")
    assert td["von"] == 3_000_000 * 6 and dt_["truong_doan"] is True
    assert any("Tips" in x for x in dt_["khong_bao_gom"])
    assert any(x["ten"].startswith("Visa") for x in dt_["thieu_gia"])


def test_tk1_4_chan_du_lieu_sai(db, nen):
    from app.services import thiet_ke_doan as S
    with pytest.raises(S.LoiThietKe, match="sau hôm nay"):
        S.chuan_hoa(_thiet_ke(nen, ngay_di="2026-11-01"), HOM_NAY)
    with pytest.raises(S.LoiThietKe, match="ít nhất 1 người lớn"):
        S.chuan_hoa(_thiet_ke(nen, khach={"nl": 0, "te": 3}), HOM_NAY)
    with pytest.raises(S.LoiThietKe, match="Tối đa"):
        S.chuan_hoa(_thiet_ke(nen, khach={"nl": 300, "te": 5}), HOM_NAY)
    with pytest.raises(S.LoiThietKe, match="điểm đến"):
        S.chuan_hoa(_thiet_ke(nen, diem=[]), HOM_NAY)
    tk = S.chuan_hoa(_thiet_ke(nen, phong={"p2": 5}), HOM_NAY)
    assert "tong_ban" not in tk and "dong" not in tk
    assert any("thêm phòng" in c for c in S.du_toan(db, tk)["canh_bao"])


def test_tk1_5_gui_phien_ban_va_quyen_xem(db, nen):
    from app.models.cong_khach import YeuCauKhach
    from app.models.thiet_ke_doan import ThietKeDoan
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    with pytest.raises(S.LoiThietKe, match="xác nhận"):
        S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen), "dien_thoai": "0901000001"}, NOW)
    r = S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen), "dien_thoai": "0901000001", "dong_y": True}, NOW)
    assert r["phien_ban"] == 1 and r["ma"].startswith("TK-") and "von" not in r["du_toan"]["dong"][0]
    yc = db.execute(select(YeuCauKhach)).scalars().one()
    assert yc.loai == "tour_doan" and yc.tam_tinh == r["du_toan"]["tong_ban"] and yc.so_khach == 23
    r2 = S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen, khach={"nl": 25}, phong={"p2": 13}), "ma": r["ma"]}, NOW)
    assert r2["phien_ban"] == 2 and db.execute(select(YeuCauKhach)).scalars().all() == [yc]
    rows = db.execute(select(ThietKeDoan).order_by(ThietKeDoan.phien_ban)).scalars().all()
    assert [x.trang_thai for x in rows] == ["thay_the", "da_gui"] and yc.so_khach == 25
    with pytest.raises(S.LoiThietKe, match="Không tìm thấy"):
        S.gui(db, _tk(db, 2), {"thiet_ke": _thiet_ke(nen), "ma": r["ma"]}, NOW)
    sales = S.ds_vtos(db, _u(db, "sa"))
    assert sales["duoc"]["gia_von"] is False and "tong_von" not in sales["thiet_ke"][0]
    assert "von" not in sales["thiet_ke"][0]["du_toan"]["dong"][0] and "bien" not in sales["thiet_ke"][0]["du_toan"]
    dh = S.ds_vtos(db, _u(db, "dh"))
    assert dh["duoc"]["gia_von"] is True and dh["thiet_ke"][0]["du_toan"]["dong"][0]["von"] > 0
    assert len(S.lich_su(db, _u(db, "sa"), r["ma"])) == 2
    assert [x["phien_ban"] for x in S.cua_toi(db, _tk(db))] == [2] and S.cua_toi(db, _tk(db, 2)) == []


def test_tk1_6_nguon_theo_diem(db, nen):
    from app.services import thiet_ke_doan as S
    assert S.khop_diem("Ninh Bình – Tràng An – Tam Cốc", "Ninh Bình") and S.khop_diem("Đà Nẵng", "Da Nang")
    assert not S.khop_diem("Đà Lạt", "Đà Nẵng")
    o = S.nguon(db, "Đà Nẵng", "2026-12-18", "2026-12-20", 2, 0, 1, HOM_NAY)
    assert [k["ten"] for k in o["khach_san"]] == [nen["k"].ten]
    g = o["khach_san"][0]["phong"][0]["goi"][0]
    assert g["gia_dem"] % 1000 == 0 and "von" not in g
    assert o["nha_hang"][0]["thuc_don"][0]["gia_nguoi_lon"] == S.ban(300_000)
    assert S.nguon(db, "Đà Lạt", "2026-12-18", "2026-12-20", 2, 0, 1, HOM_NAY) == {"diem": "Đà Lạt", "khach_san": [], "nha_hang": []}
    kc = S.khung_cong(db, HOM_NAY)
    assert "Đà Nẵng" in kc["ks_tinh"] and "Đà Nẵng" in kc["nh_tinh"]


def test_tk1_7_giao_dien():
    goc = Path(__file__).resolve().parents[2] / "web"
    c = (goc / "components" / "cong" / "TuThietKeTour.tsx").read_text(encoding="utf-8")
    for chu in ("/khach/tour-doan/tinh", "/khach/tour-doan/gui", "/khach/tour-doan/nguon", "Tạm tính", "Sales báo giá",
                "Khác…", "Phòng 3", "Hãng nào cũng được", "Gửi thiết kế"):
        assert chu in c, chu
    a = (goc / "components" / "cong" / "ToursAgoda.tsx").read_text(encoding="utf-8")
    assert "TuThietKeTour" in a
    v = (goc / "app" / "tour-doan" / "page.tsx").read_text(encoding="utf-8")
    for chu in ("/tour-doan/don-gia", "Duyệt", "Giá vốn", "Vé máy bay theo chặng"):
        assert chu in v, chu


def test_tk1_8_bang_gia_xe_va_hdv_co_san(db, nen):
    from app.models.hr import GuideRate, Vehicle, VehicleRate
    from app.services import thiet_ke_doan as S
    db.add_all([VehicleRate(route="Đà Lạt", days=4, internal_price=13_000_000, partner_price=16_000_000,
                            effective_from=dt.date(2026, 5, 6), status="active"),
                VehicleRate(route="Đà Lạt 4 ngày", days=4, internal_price=16_000_000, partner_price=18_000_000,
                            effective_from=dt.date(2026, 4, 1), status="active"),
                GuideRate(route="Đà Lạt 4N3Đ", days=4, rate_per_day=600_000, effective_from=dt.date(2026, 9, 1), status="active"),
                Vehicle(plate="51B-00001", seats=29, internal_rate_per_day=2_500_000),
                Vehicle(plate="51B-00002", seats=45, internal_rate_per_day=3_500_000)])
    db.commit()
    _dg(db, loai="xe", ten="Xe 29 chỗ (Điều hành nhập)", tu_cho=28, gia=9_000_000, pham_vi="dn")
    base = dict(diem=[{"ten": "Đà Lạt", "dem": 3}], ngay=[], dich_vu=["hdv"], chang=[{"pt": "xe"}, {"pt": "xe"}])
    # trùng tuyến «Đà Lạt» 4 ngày, đi xe từ TP HCM → giá trọn chuyến cột xe nhà, bản hiệu lực mới nhất; 50 ghế → 2 xe 45 chỗ
    dt_ = S.du_toan(db, S.chuan_hoa(_thiet_ke(nen, khach={"nl": 50}, phong={"p2": 25}, **base), HOM_NAY))
    xe = next(x for x in dt_["dong"] if x["nhom"] == "Xe")
    assert "bảng giá xe" in xe["ten"] and xe["von"] == 13_000_000 * 2          # bản hiệu lực mới nhất
    hdv = next(x for x in dt_["dong"] if "bảng thù lao HDV" in x["ten"])
    assert hdv["von"] == 600_000 * 4
    # có chặng bay → không dùng giá tuyến từ TP HCM; đơn giá ngày xe nhà: 22 ghế → xe 29 chỗ × 4 ngày
    d2 = dict(base, chang=[{"pt": "bay"}, {"pt": "bay"}])
    dt2 = S.du_toan(db, S.chuan_hoa(_thiet_ke(nen, **d2), HOM_NAY))
    xe2 = next(x for x in dt2["dong"] if x["nhom"] == "Xe")
    assert xe2["ten"].startswith("Xe 29 chỗ (đơn giá ngày") and xe2["von"] == 2_500_000 * 4
    # nước ngoài: không dùng bảng xe trong nước
    assert S.gia_xe_bang is not None and not S.khop_tuyen("Đà Lạt", ["Đà Lạt", "Nha Trang"])
    assert S._manh_tuyen("Tà Đùng – Đà Lạt – Phan Thiết") == ["Tà Đùng", "Đà Lạt", "Phan Thiết"]
