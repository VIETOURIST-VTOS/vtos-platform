# -*- coding: utf-8 -*-
"""TK-2 · Báo giá chính thức tour đoàn khách tự thiết kế — giai đoạn 2 (Chủ tịch 04/11/2026: hạn 24 giờ; trẻ em 75%
tour xe / 80% có chặng bay; khách đồng ý → hợp đồng nháp; biên < 10% Chủ tịch / TGĐ duyệt).

  1. Lập từ thiết kế: chép dòng tạm tính kèm giá vốn + dòng thiếu giá; còn thiếu giá thì không gửi duyệt.
  2. Tiền: bán = vốn ÷ 0,9 lên nghìn; giá NL = tổng ÷ (NL + k·TE); TE = k·NL; hệ số 0,75 xe / 0,80 bay.
  3. Duyệt: biên ≥ 10% → TP ĐH khác người lập; < 10% → phải có lý do, chỉ Chủ tịch / TGĐ; trả lại cần lý do.
  4. Khách: thấy báo giá đã duyệt (không thấy giá vốn); đồng ý trong hạn → hợp đồng nháp + lead; quá 24 giờ → 410.
  5. Khách sửa thiết kế → báo giá cũ «thay_the»; Sales không thấy giá vốn.
  6. Giao diện: màn VTOS và cổng khách có đủ cửa.
"""
import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_tk1_tu_thiet_ke_tour_doan import HOM_NAY, NOW, _bang_gia, _thiet_ke, _tk, nen  # noqa: F401


def _gui(db, nen, **them):
    from app.services import thiet_ke_doan as S
    r = S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen, **them), "dien_thoai": "0901000001", "dong_y": True}, NOW)
    from app.models.thiet_ke_doan import ThietKeDoan
    return db.execute(select(ThietKeDoan).where(ThietKeDoan.ma == r["ma"]).order_by(ThietKeDoan.phien_ban.desc())).scalars().first()


def _du_von(db, bg, gia=1_000_000):
    from app.services import bao_gia_doan as B
    dong = [{**x, "von": x["von"] if x.get("von") is not None else gia} for x in bg["dong"]]
    return B.luu(db, _u(db, "dh"), bg["id"], {"dong": dong})


def test_tk2_1_lap_va_chan_thieu_gia(db, nen):
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = B.lap(db, _u(db, "dh"), tk.id, NOW)
    assert bg["trang_thai"] == "nhap" and bg["thieu_gia"] and bg["he_so_te"] == 0.8      # có chặng bay
    assert any(x["nguon"] == "tạm tính" and x["von"] for x in bg["dong"])
    assert B.lap(db, _u(db, "dh"), tk.id, NOW)["id"] == bg["id"]                           # lập lại → bản đang soạn
    with pytest.raises(B.LoiBaoGia, match="chưa có giá vốn"):
        B.gui_duyet(db, _u(db, "dh"), bg["id"])
    with pytest.raises(B.LoiBaoGia, match="Chỉ Điều hành"):
        B.lap(db, _u(db, "kd"), tk.id, NOW)


def test_tk2_2_tien_va_he_so_tre_em(db, nen):
    import math
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = _du_von(db, B.lap(db, _u(db, "dh"), tk.id, NOW))
    ban = sum(x["ban"] for x in bg["dong"])
    assert all(x["ban"] == math.ceil(x["von"] / 0.9 / 1000) * 1000 for x in bg["dong"])
    gnl = math.ceil(ban / (20 + 0.8 * 2) / 1000) * 1000
    assert bg["gia_nl"] == gnl and bg["gia_te"] == math.ceil(gnl * 0.8 / 1000) * 1000
    assert bg["tong_ban"] == gnl * 20 + bg["gia_te"] * 2 and bg["bien_thuc"] >= 0.0999
    # tour chỉ đi xe → 75%
    tk2 = _gui(db, nen, chang=[{"pt": "xe"}, {"pt": "xe"}], khach={"nl": 10, "te": 4}, phong={"p2": 7})
    assert B.lap(db, _u(db, "dh"), tk2.id, NOW)["he_so_te"] == 0.75


def test_tk2_3_cap_duyet_theo_bien(db, nen):
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = _du_von(db, B.lap(db, _u(db, "dh"), tk.id, NOW))
    with pytest.raises(B.LoiBaoGia, match="Chỉ Điều hành"):
        B.luu(db, _u(db, "kd"), bg["id"], {"bien_pt": 5})
    bg = B.luu(db, _u(db, "dh"), bg["id"], {"bien_pt": 5})
    with pytest.raises(B.LoiBaoGia, match="ghi lý do"):
        B.gui_duyet(db, _u(db, "dh"), bg["id"])
    bg = B.gui_duyet(db, _u(db, "dh"), bg["id"], "Khách quen, đoàn lớn")
    assert bg["cap_duyet"] == "ct_tgd"
    with pytest.raises(B.LoiBaoGia, match="Chủ tịch / TGĐ"):
        B.duyet(db, _u(db, "tp"), bg["id"], True)
    with pytest.raises(B.LoiBaoGia, match="lý do trả lại"):
        B.duyet(db, _u(db, "ct"), bg["id"], False)
    bg = B.duyet(db, _u(db, "ct"), bg["id"], False, "Biên thấp quá")
    assert bg["trang_thai"] == "tra_lai"
    bg = B.luu(db, _u(db, "dh"), bg["id"], {"bien_pt": 10})
    bg = B.gui_duyet(db, _u(db, "dh"), bg["id"])
    assert bg["cap_duyet"] == "tp_dh"
    with pytest.raises(B.LoiBaoGia, match="sửa"):
        B.luu(db, _u(db, "dh"), bg["id"], {"bien_pt": 12})
    bg = B.duyet(db, _u(db, "tp"), bg["id"], True, now=NOW)
    assert bg["trang_thai"] == "da_duyet" and bg["han_luc"] == (NOW + dt.timedelta(hours=24)).isoformat(timespec="minutes")


def test_tk2_3b_nguoi_lap_khong_tu_duyet(db, nen):
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = _du_von(db, B.lap(db, _u(db, "tp"), tk.id, NOW))
    bg = B.gui_duyet(db, _u(db, "tp"), bg["id"])
    with pytest.raises(B.LoiBaoGia, match="không tự duyệt"):
        B.duyet(db, _u(db, "tp"), bg["id"], True)
    assert B.duyet(db, _u(db, "tp2"), bg["id"], True)["trang_thai"] == "da_duyet"


def _da_duyet(db, nen, **them):
    from app.services import bao_gia_doan as B
    tk = _gui(db, nen, **them)
    bg = _du_von(db, B.lap(db, _u(db, "dh"), tk.id, NOW))
    B.gui_duyet(db, _u(db, "dh"), bg["id"])
    B.duyet(db, _u(db, "tp"), bg["id"], True, now=NOW)
    return tk


def test_tk2_4_khach_dong_y_tao_hop_dong_nhap(db, nen):
    from app.models.ban_hang import HopDongKhach
    from app.services import bao_gia_doan as B
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    tk = _da_duyet(db, nen)
    mine = S.cua_toi(db, _tk(db), NOW)[0]["bao_gia"]
    assert mine["trang_thai"] == "da_duyet" and "tong_von" not in mine and all("von" not in x for x in mine["dong"])
    with pytest.raises(B.LoiBaoGia, match="Không tìm thấy"):
        B.khach_dong_y(db, _tk(db, 2), mine["id"], mine["ma_bam"], True, NOW)
    with pytest.raises(B.LoiBaoGia, match="đã thay đổi"):
        B.khach_dong_y(db, _tk(db), mine["id"], "sai", True, NOW)
    r = B.khach_dong_y(db, _tk(db), mine["id"], mine["ma_bam"], True, NOW + dt.timedelta(hours=2))
    hd = db.execute(select(HopDongKhach)).scalars().one()
    assert r["trang_thai"] == "khach_dong_y" and r["hop_dong"] == hd.so_hop_dong
    assert hd.trang_thai == "nhap" and hd.gia_tri == mine["tong_ban"] and tk.ma in hd.ghi_chu
    assert B.khach_dong_y(db, _tk(db), mine["id"], mine["ma_bam"], True, NOW)["message"].startswith("Bạn đã đồng ý")


def test_tk2_4b_qua_24_gio_het_han(db, nen):
    from app.services import bao_gia_doan as B
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    _da_duyet(db, nen)
    mine = S.cua_toi(db, _tk(db), NOW)[0]["bao_gia"]
    with pytest.raises(B.LoiBaoGia, match="hết hạn") as e:
        B.khach_dong_y(db, _tk(db), mine["id"], mine["ma_bam"], True, NOW + dt.timedelta(hours=25))
    assert e.value.status == 410


def test_tk2_5_khach_sua_thiet_ke_thi_bao_gia_cu_het_hieu_luc(db, nen):
    from app.models.thiet_ke_doan import BaoGiaDoan
    from app.services import bao_gia_doan as B
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    tk = _da_duyet(db, nen)
    S.gui(db, _tk(db), {"thiet_ke": _thiet_ke(nen, khach={"nl": 25}, phong={"p2": 13}), "ma": tk.ma}, NOW)
    assert db.execute(select(BaoGiaDoan)).scalars().one().trang_thai == "thay_the"
    with pytest.raises(B.LoiBaoGia, match="phiên bản mới"):
        B.lap(db, _u(db, "dh"), tk.id, NOW)
    sa = S.ds_vtos(db, _u(db, "sa"))
    assert sa["thiet_ke"][0]["bao_gia"] is None or "tong_von" not in sa["thiet_ke"][0]["bao_gia"]


def test_tk2_6_giao_dien():
    goc = Path(__file__).resolve().parents[2] / "web"
    v = (goc / "app" / "tour-doan" / "page.tsx").read_text(encoding="utf-8")
    for chu in ("Lập báo giá", "/bao-gia", "Gửi duyệt", "Trả lại", "Chủ tịch / TGĐ"):
        assert chu in v, chu
    c = (goc / "components" / "cong" / "TuThietKeTour.tsx").read_text(encoding="utf-8")
    for chu in ("/khach/tour-doan/cua-toi", "Đồng ý báo giá", "/dong-y", "Hiệu lực đến"):
        assert chu in c, chu
