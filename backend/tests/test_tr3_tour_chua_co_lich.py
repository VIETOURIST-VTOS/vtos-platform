# -*- coding: utf-8 -*-
"""TR-3 · Tour ghép đã ghép web nhưng chưa có chuyến mở bán vẫn hiện khi tìm (Chủ tịch «Ok làm» 02/11/2026, đã duyệt
bản xem thử). Trước TR-3 chỉ tour có chuyến mới hiện → 82 tour mã W… và phần lớn tour web không ai thấy.

  1. Tìm: tour ghép có link web, chưa có chuyến → hiện, gắn «chua_co_lich», giá tham khảo lấy từ bảng giá web; tour
     ghép KHÔNG có link web và không chuyến → vẫn ẩn. Lọc theo khoảng ngày thì tour chưa có lịch không hiện.
  2. Chi tiết: mở được (không còn 404) khi đã ghép web; chưa ghép thì vẫn 404.
  3. Có chuyến mở bán thì về như cũ: không còn «chua_co_lich», giá thật.
  4. Giao diện: thẻ và trang tour có nhãn «Lịch khởi hành đang cập nhật» và nút «Gửi yêu cầu giữ chỗ».
"""
import datetime as dt
from pathlib import Path

import pytest

from tests.test_tr1_tour_agoda import NOW, _sp, _tour, db  # noqa: F401

LINK = "https://www.vietourist.com.vn/vn/tour/du-lich-binh-thuan/tour-binh-thuan-2n1d-804.html"


def _co_web(s, p, gia=1_890_000):
    p.link_web = LINK
    p.noi_dung_web = {"anh": ["https://www.vietourist.com.vn/a.jpg"], "lich_trinh": [], "gia_web": gia, "loi": ""}
    s.commit()
    return p


def test_tr3_1_tim_hien_tour_da_ghep_web_chua_co_chuyen(db):
    from app.services import tour_online as TR
    w = _co_web(db, _sp(db, "W804", "BÌNH THUẬN 2N1Đ"))
    _sp(db, "AN001", "TOUR CHƯA GHÉP WEB")                           # không link, không chuyến → ẩn
    r = TR.tim(db, hom_nay=NOW.date())
    ma = {x["ma"]: x for x in r["san_pham"]}
    assert "W804" in ma and "AN001" not in ma
    assert ma["W804"]["chua_co_lich"] is True and ma["W804"]["gia_tham_khao"] == 1_890_000 and ma["W804"]["gia_tu"] is None
    # lọc khoảng ngày: tour chưa có lịch không khớp ngày nào
    assert "W804" not in {x["ma"] for x in TR.tim(db, tu=dt.date(2026, 11, 20), den=dt.date(2026, 11, 30), hom_nay=NOW.date())["san_pham"]}
    assert w.id


def test_tr3_2_chi_tiet_mo_duoc_khi_da_ghep_web(db):
    from app.services import tour_online as TR
    w = _co_web(db, _sp(db, "W804", "BÌNH THUẬN 2N1Đ"))
    o = TR.chi_tiet(db, w.id, hom_nay=NOW.date())
    assert o["chua_co_lich"] is True and o["chuyen"] == [] and o["link_web"] == LINK
    k = _sp(db, "AN001", "TOUR CHƯA GHÉP WEB")
    with pytest.raises(TR.LoiTour):
        TR.chi_tiet(db, k.id, hom_nay=NOW.date())


def test_tr3_3_co_chuyen_thi_ve_nhu_cu(db):
    from app.services import tour_online as TR
    w = _co_web(db, _sp(db, "W804", "BÌNH THUẬN 2N1Đ"))
    _tour(db, w, dt.date(2026, 11, 14), gia=2_190_000)
    x = next(o for o in TR.tim(db, hom_nay=NOW.date())["san_pham"] if o["ma"] == "W804")
    assert x["chua_co_lich"] is False and x["gia_tham_khao"] is None and x["gia_tu"] == 2_190_000


def test_tr3_4_giao_dien_nhan_va_nut():
    s = (Path(__file__).resolve().parents[2] / "web" / "components" / "cong" / "ToursAgoda.tsx").read_text(encoding="utf-8")
    assert '{s.chua_co_lich && <span>Lịch khởi hành đang cập nhật</span>}' in s
    assert 'const doan = sp.loai === "doan" || !!sp.chua_co_lich;' in s
    assert '"Gửi yêu cầu giữ chỗ"' in s and 's.loai === "doan" || s.chua_co_lich ? "Xem & gửi yêu cầu"' in s
