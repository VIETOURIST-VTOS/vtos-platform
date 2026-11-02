# -*- coding: utf-8 -*-
"""DK-4 · Màn sáu trạng thái hồ sơ cho đối tác / cổ đông — phép thử ĐỌC THẲNG TỆP GIAO DIỆN.

  1. Màn có đủ SÁU trạng thái, mỗi trạng thái đúng tên máy chủ dùng (TRANG_THAI_NGOAI).
  2. Trang /cong dùng màn này cho đối tác / cổ đông — khách hàng vẫn giữ dòng cũ.
  3. Tên người duyệt trên màn khớp NGUOI_DUYET của máy chủ — màn nói «GĐ KD đang duyệt» mà máy chủ
     giao TP ĐH thì người gửi hồ sơ đi hỏi nhầm người.
  4. Màn chỉ ĐỌC: không gọi cửa nào.
"""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
MAN = GOC / "web" / "components" / "cong" / "TrangThaiHoSo.tsx"
TRANG = GOC / "web" / "app" / "cong" / "page.tsx"


def _man() -> str:
    assert MAN.is_file(), f"không có {MAN}"
    return MAN.read_text(encoding="utf-8")


def test_dk4_1_du_sau_trang_thai_dung_ten_may_chu():
    from app.models.cong_ngoai import TRANG_THAI_NGOAI
    s = _man()
    assert len(TRANG_THAI_NGOAI) == 6
    for ma, ten in TRANG_THAI_NGOAI.items():
        assert f'{ma}: "{ten}"' in s, f"màn thiếu hoặc đặt tên khác cho trạng thái {ma} («{ten}»)"


def test_dk4_2_trang_cong_dung_man_cho_doi_tac_co_dong():
    t = TRANG.read_text(encoding="utf-8")
    assert 'import TrangThaiHoSo from "@/components/cong/TrangThaiHoSo"' in t
    assert 'toi.loai !== "khach_hang" ? <TrangThaiHoSo toi={toi} />' in t
    assert "Trạng thái tài khoản:" in t, "khách hàng vẫn giữ dòng trạng thái cũ"


def test_dk4_3_nguoi_duyet_khop_may_chu():
    from app.services import cong_ngoai as C
    s = _man()
    ten = {"tp_dh": "Phòng Điều hành", "gd_kd": "Giám đốc Kinh doanh", "ir_phapche": "IR – Pháp chế"}
    assert C.NGUOI_DUYET[("co_dong", "")] == ("ir_phapche",) and '"IR – Pháp chế"' in s
    for ldt in ("dai_ly", "ctv_ban_hang"):
        assert C.NGUOI_DUYET[("doi_tac", ldt)] == ("gd_kd",), ldt
        assert f'toi.loai_doi_tac === "{ldt}"' in s, f"màn không rẽ riêng {ldt} sang GĐ KD"
    for ldt in ("ncc", ""):
        assert set(C.NGUOI_DUYET[("doi_tac", ldt)]) == {"tp_dh", "gd_kd"}, ldt
    assert '"Phòng Điều hành / Giám đốc Kinh doanh"' in s
    assert all(v in s for v in ten.values())


def test_dk4_4_man_chi_doc():
    s = _man()
    assert not re.search(r"\bgoiCong\(|\bfetch\(|\bapi\(", s), "màn trạng thái không được tự gọi cửa nào"
