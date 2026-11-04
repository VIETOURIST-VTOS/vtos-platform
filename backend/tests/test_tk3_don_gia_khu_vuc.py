# -*- coding: utf-8 -*-
"""TK-3 · Đơn giá dịch vụ đoàn gắn khu vực (Chủ tịch 04/11/2026: giá châu Âu tạm nhập từ quyết toán T6 không được áp
cho tour Thái Lan, Hàn Quốc).

  1. Đơn giá nước ngoài gắn châu lục hoặc nước; rỗng = mọi nước. Tạm tính chọn dòng khớp nhất: nước > châu lục > mọi nước.
  2. Nước không có dòng khớp → «thiếu giá», Sales báo giá — không lấy giá châu lục khác.
  5. Visa không có đơn giá chung (mỗi nước một loại visa): luôn «Sales báo giá», Điều hành không nhập được.
  3. Khu vực ngoài danh mục, hoặc gắn cho đơn giá trong nước → chặn. Vé máy bay bỏ qua khu vực (đã theo chặng).
  4. Danh mục khu vực ở máy chủ khớp danh mục điểm đến nước ngoài của cổng khách.
"""
import json
import re
from pathlib import Path

import pytest

from tests.test_at1_am_thuc import _u, db  # noqa: F401
from tests.test_tk1_tu_thiet_ke_tour_doan import HOM_NAY, _dg, _thiet_ke, nen  # noqa: F401

GOC = Path(__file__).resolve().parents[2]


def _nn(nen, diem, dv=("visa", "bao_hiem", "hdv")):
    return _thiet_ke(nen, pham_vi="nn", diem=[{"ten": t, "dem": 2} for t in diem], ngay=[],
                     chang=[{"pt": "bay"}] + [{"pt": "xe"}] * (len(diem) - 1) + [{"pt": "bay"}], dich_vu=list(dv))


def test_tk3_1_chon_dong_khop_nhat(db, nen):
    from app.services import thiet_ke_doan as S
    _dg(db, loai="bao_hiem", ten="BH Hàn Quốc", gia=90_000, pham_vi="nn", khu_vuc="Hàn Quốc")
    _dg(db, loai="bao_hiem", ten="BH quốc tế chung", gia=100_000, pham_vi="nn")
    _dg(db, loai="bao_hiem", ten="BH Châu Âu", gia=183_300, pham_vi="nn", khu_vuc="Châu Âu")
    _dg(db, loai="truong_doan", ten="Trưởng đoàn Châu Âu", gia=3_427_000, pham_vi="nn", khu_vuc="Châu Âu")
    _dg(db, loai="xe", ten="Xe 45 chỗ Châu Âu", tu_cho=45, gia=26_688_000, pham_vi="nn", khu_vuc="Châu Âu")

    eu = S.du_toan(db, S.chuan_hoa(_nn(nen, ["Pháp", "Thụy Sĩ"]), HOM_NAY))
    ten = {x["ten"] for x in eu["dong"]}
    assert {"BH Châu Âu", "Trưởng đoàn Châu Âu", "Xe 45 chỗ Châu Âu"} <= ten
    assert "BH quốc tế chung" not in ten and "BH Hàn Quốc" not in ten
    assert any(x["ten"] == "Visa nhập cảnh" and "Sales" in x["ly_do"] for x in eu["thieu_gia"])

    han = S.du_toan(db, S.chuan_hoa(_nn(nen, ["Hàn Quốc"]), HOM_NAY))
    ten = {x["ten"] for x in han["dong"]}
    assert "BH Hàn Quốc" in ten and "BH quốc tế chung" not in ten
    assert not ten & {"BH Châu Âu", "Xe 45 chỗ Châu Âu", "Trưởng đoàn Châu Âu"}

    thai = S.du_toan(db, S.chuan_hoa(_nn(nen, ["Thái Lan"]), HOM_NAY))
    ten = {x["ten"] for x in thai["dong"]}
    assert "BH quốc tế chung" in ten and not ten & {"BH Hàn Quốc", "BH Châu Âu", "Xe 45 chỗ Châu Âu"}
    assert any(x["nhom"] == "Xe" for x in thai["thieu_gia"])


def test_tk3_2_nuoc_thang_chau_luc(db, nen):
    from app.services import thiet_ke_doan as S
    _dg(db, loai="bao_hiem", ten="BH Châu Âu", gia=183_300, pham_vi="nn", khu_vuc="Châu Âu")
    _dg(db, loai="bao_hiem", ten="BH Anh", gia=250_000, pham_vi="nn", khu_vuc="Anh")
    ten = {x["ten"] for x in S.du_toan(db, S.chuan_hoa(_nn(nen, ["Anh"], ("bao_hiem",)), HOM_NAY))["dong"]}
    assert "BH Anh" in ten and "BH Châu Âu" not in ten
    assert S.muc_khu_vuc("", ["Ý"]) == 0 and S.muc_khu_vuc("Châu Âu", ["Ý"]) == 1 and S.muc_khu_vuc("Ý", ["Ý"]) == 2
    assert S.muc_khu_vuc("Châu Á", ["Ý"]) is None


def test_tk3_3_chan_khu_vuc_sai(db, nen):
    from app.services import thiet_ke_doan as S
    with pytest.raises(S.LoiThietKe, match="danh mục"):
        _dg(db, loai="bao_hiem", ten="BH", gia=1, pham_vi="nn", khu_vuc="Sao Hỏa")
    with pytest.raises(S.LoiThietKe, match="loại dịch vụ"):
        _dg(db, loai="visa", ten="Visa Schengen", gia=3_887_000, pham_vi="nn")
    with pytest.raises(S.LoiThietKe, match="nước ngoài"):
        _dg(db, loai="bao_hiem", ten="BH", gia=1, pham_vi="dn", khu_vuc="Châu Âu")
    v = _dg(db, loai="ve_may_bay", ten="SGN-FRA", tu_diem="TP HCM", den_diem="Đức", gia=1, pham_vi="nn", khu_vuc="Châu Âu")
    assert v["khu_vuc"] == ""
    ds = S.ds_don_gia(db, _u(db, "tp"))
    assert "Châu Âu" in ds["khu_vuc"] and "Đức" in ds["khu_vuc"]["Châu Âu"]


def test_tk3_4_danh_muc_khop_cong_khach():
    from app.services import thiet_ke_doan as S
    s = (GOC / "web/components/cong/tuThietKeDuLieu.ts").read_text(encoding="utf-8")
    i = s.index('"nn": {')
    nn = json.loads("{" + s[i:s.index("}", i) + 1] + "}")["nn"]
    assert nn == S.NUOC_NGOAI


def test_tk3_5_man_vtos_co_o_khu_vuc():
    s = (GOC / "web/app/tour-doan/page.tsx").read_text(encoding="utf-8")
    assert "khu_vuc" in s and re.search(r"Khu vực", s)
