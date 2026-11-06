# -*- coding: utf-8 -*-
"""KS-19k · Gộp báo giá đoàn (TK-2) vào bảng báo giá CHUNG (Chủ tịch chọn 06/11/2026: «đầu chung + bảng phụ»,
«quy về tên trạng thái chung», «màn Bán hàng hiện, chỉ xem»).

  1. Lập từ thiết kế → một dòng ĐẦU ở bao_gia (mang kd_doan, nguon thiet_ke, mã BGD-…) + phần riêng cùng id.
  2. Duyệt → da_gui (không còn da_duyet); khách đồng ý → khach_chot; hợp đồng nháp nối bao_gia_id về dòng đầu.
  3. Màn Bán hàng: thấy trong danh sách mảng đoàn, có giá bán, KHÔNG có giá vốn; sửa / gửi / chốt / lập HĐ bị chặn.
  4. Không còn bảng bao_gia_doan; migration chuyển dữ liệu cũ có mặt và nối đúng đầu chuỗi.
"""
from pathlib import Path

import pytest
from sqlalchemy import select

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_tk1_tu_thiet_ke_tour_doan import NOW, _bang_gia, _tk, nen  # noqa: F401
from tests.test_tk2_bao_gia_doan import _da_duyet, _du_von, _gui


def test_ks19k_1_lap_sinh_dong_dau_o_bang_chung(db, nen):
    from app.models.ban_hang import BaoGia
    from app.models.thiet_ke_doan import BaoGiaDoan
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = B.lap(db, _u(db, "dh"), tk.id, NOW)
    dau = db.get(BaoGia, bg["id"])
    assert dau is not None and dau.mang == "kd_doan" and dau.nguon == "thiet_ke" and dau.ma.startswith("BGD-")
    assert dau.trang_thai == "nhap" and dau.tao_boi and dau.so_khach == bg["so_nl"] + bg["so_te"] + bg["so_eb"]
    assert db.get(BaoGiaDoan, bg["id"]).dau is dau


def test_ks19k_2_trang_thai_chung_va_hop_dong_noi_dau(db, nen):
    from app.models.ban_hang import BaoGia, HopDongKhach
    from app.services import bao_gia_doan as B
    from app.services import thiet_ke_doan as S
    _bang_gia(db)
    _da_duyet(db, nen)
    mine = S.cua_toi(db, _tk(db), NOW)[0]["bao_gia"]
    dau = db.get(BaoGia, mine["id"])
    assert dau.trang_thai == "da_gui" and dau.duyet_boi and dau.han_hieu_luc and dau.bien_luc_gui is not None
    B.khach_dong_y(db, _tk(db), mine["id"], mine["ma_bam"], True, NOW)
    hd = db.execute(select(HopDongKhach)).scalars().one()
    assert db.get(BaoGia, mine["id"]).trang_thai == "khach_chot" and hd.bao_gia_id == mine["id"]


def test_ks19k_3_ban_hang_chi_xem(db, nen):
    from app.models.ban_hang import BaoGia
    from app.services import ban_hang as BH
    from app.services import bao_gia_doan as B
    _bang_gia(db)
    tk = _gui(db, nen)
    bg = _du_von(db, B.lap(db, _u(db, "dh"), tk.id, NOW))
    dau = db.get(BaoGia, bg["id"])
    for lam in (lambda: BH.gui_khach(db, dau, "kd"), lambda: BH.khach_chot(db, dau, "kd"),
                lambda: BH.lap_hop_dong(db, dau, "kd")):
        with pytest.raises(BH.CongBaoGia) as e:
            lam()
        assert e.value.detail["gate"] == "NGUON_THIET_KE"
    from app.api.v1.ban_hang import _bg_ra
    o = _bg_ra(db, dau)
    assert o["mang"] == "kd_doan" and o["nguon"] == "thiet_ke" and o["thiet_ke"]["ma"] == tk.ma
    assert o["thiet_ke"]["tong_ban"] == bg["tong_ban"] and "tong_von" not in o["thiet_ke"]


def test_ks19k_4_khong_con_bang_tach_doi_va_co_migration():
    from app.db.session import Base
    assert "bao_gia_doan" not in Base.metadata.tables and "bao_gia_thiet_ke" in Base.metadata.tables
    goc = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    m = (goc / "ks19k4d6f8a0c2e135_gop_bao_gia_doan.py").read_text(encoding="utf-8")
    for chu in ('op.drop_table("bao_gia_doan")', 'nguon="thiet_ke"', "bao_gia_id=bid", '"da_duyet": "da_gui"',
                '"khach_dong_y": "khach_chot"'):
        assert chu in m, chu


def test_ks19k_5_giao_dien_theo_ten_chung():
    goc = Path(__file__).resolve().parents[2] / "web"
    c = (goc / "components" / "cong" / "TuThietKeTour.tsx").read_text(encoding="utf-8")
    assert '"da_duyet"' not in c and '"khach_dong_y"' not in c
    v = (goc / "app" / "bao-gia" / "page.tsx").read_text(encoding="utf-8")
    assert 'b.nguon === "thiet_ke"' in v and "!tuTK" in v
