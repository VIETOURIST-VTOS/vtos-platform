# -*- coding: utf-8 -*-
"""R5-19 · Rà bốn tab còn lại của bàn Phòng KD Lẻ (Chủ tịch 14/11/2026: «1 chung navy trắng sáng», «2 có»).

  A. Thẻ trùng / đặt sai chỗ: GĐ gom ba thẻ OTA về tab Bán hàng, thêm «Báo cáo công việc» ở Đội ngũ;
     Chuyên viên bỏ thẻ «Đề xuất gửi BLĐ» (trùng màn) và khối «Lương, đề xuất & báo cáo» ở Tổng quan;
     bốn bàn đổi tên thẻ «Doanh thu & chỉ tiêu».
  B. Khung bàn chung nền trắng sáng, điểm nhấn navy cho màn mở trong bàn; nhãn tiếng Việt ở ô tổng báo
     cáo bán hàng; cảnh báo cấu hình hộp thư chỉ cho CNTT.
  C. Trưởng nhóm ĐỌC báo cáo ngày của người trong nhóm mình (chỉ đọc; xem xét vẫn là việc Trưởng phòng).
"""
import re
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
WEB = GOC / "web"
doc = lambda p: (WEB / p).read_text(encoding="utf-8")  # noqa: E731


def _tab(src: str, ma: str) -> str:
    m = re.search(r'\{ ma: "' + ma + r'".*?\] \}', src, re.S)
    assert m, ma
    return m.group(0)


# ── A ─────────────────────────────────────────────────────────────────────────────────────────

def test_gd_gom_ota_ve_ban_hang_va_co_bao_cao_cong_viec():
    s = doc("components/BanGdKdLe.tsx")
    ban = _tab(s, "ban")
    for d in ("/khach-san-ota", "/don-khach-san-ota", "/doi-soat-ota"):
        assert d in ban and s.count(d) == 1, d
    assert "/reports" in _tab(s, "doi")


def test_nv_khong_lap_the_va_khoi():
    s = doc("components/BanNvKd.tsx")
    assert "Đề xuất gửi Ban lãnh đạo\"" not in s and "<h2>Lương, đề xuất" not in s
    assert s.count('toi: "/reports"') == 1
    assert "Việc hôm nay" in s and "g5-hai" not in s


def test_bon_ban_doi_ten_the_chi_tieu():
    for f in ("BanGdKdLe", "BanTpKd", "BanTnKd", "BanNvKd", "BanKdKhung"):
        s = doc(f"components/{f}.tsx")
        assert 'ten: "Doanh thu & chỉ tiêu' not in s and "Chỉ tiêu kinh doanh\"" not in s, f
    for f in ("BanGdKdLe", "BanTpKd", "BanTnKd"):
        assert "Chỉ tiêu theo người & nhóm" in doc(f"components/{f}.tsx"), f


# ── B ─────────────────────────────────────────────────────────────────────────────────────────

def test_khung_ban_chung_bat_o_hai_ban():
    k = doc("components/KhungNhung.tsx")
    assert "khungBan" in k and "vtos-khung-ban" in k and "data-nhan" in k
    for f in ("BanKdKhung", "BanGdKdLe"):
        assert "anDauBan khungBan" in doc(f"components/{f}.tsx"), f
    css = doc("app/globals.css")
    khoi = css[css.index("R5-19 · KHUNG BÀN CHUNG"):]
    # R5-25: luật đầu bảng dùng chung cho bàn PTGĐ Đoàn (.ban-navy)
    assert "html.vtos-khung-ban th,.ban-navy th{" in khoi and "var(--vtos-info-bg)" in khoi and "text-transform:none" in khoi
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", khoi), "màu phải dùng token"


def test_nhan_tieng_viet_o_tong_bao_cao_ban_hang():
    s = doc("app/sales-reports/page.tsx")
    for k, v in (("revenue", "Doanh thu"), ("paid", "Đã thu"), ("due", "Còn phải thu"), ("cancelled", "Đã huỷ")):
        assert f'{k}: "{v}"' in s
    assert "NHAN_TONG[k] || k" in s


def test_canh_bao_cau_hinh_hop_thu_chi_cho_cntt():
    s = doc("app/inbox/page.tsx")
    i = s.index('role === "cntt" ? <>')
    assert i < s.index("FB_PAGE_ACCESS_TOKEN") and i < s.index("Chưa có ANTHROPIC_API_KEY")
    assert "chưa nối — đang chờ CNTT" in s


# ── C ─────────────────────────────────────────────────────────────────────────────────────────

D = date(2026, 10, 27)
NOP = datetime(2026, 10, 27, 18, 0)
SAU = datetime(2026, 10, 28, 9, 0)
DAI = "Nội dung đủ dài trên hai mươi ký tự để tính điểm."


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def _nguoi(db, ten, vai, nhom):
    from app.models.core import User
    from app.models.hr import Employee
    u = User(username=ten, full_name=ten.upper(), role=vai, password_hash="x", active=True, sales_group=nhom)
    db.add(u); db.flush()
    db.add(Employee(code=f"NV-{ten}", full_name=ten.upper(), department="kd_le", position="nv", user_id=u.id, active=True))
    db.flush()
    return u


def test_truong_nhom_doc_bao_cao_cua_nhom_minh(db):
    from app.services import ops as O
    from app.services import bao_cao_ngay_xem as X
    tn = _nguoi(db, "tn.kd1", "tn_kd", "KD1")
    a = _nguoi(db, "nv.kd1", "nv_kd", "KD1")
    b = _nguoi(db, "nv.kd2", "nv_kd", "KD2")
    ra = O.submit_report(db, a, D, DAI, "{}", "", DAI, now=NOP)
    rb = O.submit_report(db, b, D, DAI, "{}", "", DAI, now=NOP)
    db.commit()
    th = X.tong_hop(db, tn, D, now=SAU)
    assert th["pham_vi"] == "nhom"
    ten = {d["ten"]: d for d in th["dong"]}
    assert "NV.KD1" in ten and "NV.KD2" not in ten
    assert ten["NV.KD1"]["doc_duoc"] and ten["NV.KD1"]["noi_dung"] is not None
    assert X.doc_duoc(db, tn, ra) and not X.doc_duoc(db, tn, rb)
    # R5-20: Trưởng nhóm nay xem xét được người trong nhóm (test_r5_20_gia_von_tn).


def test_vai_khac_khong_co_pham_vi_nhom_van_bi_chan(db):
    from app.services import bao_cao_ngay_xem as X
    nv = _nguoi(db, "nv.x", "nv_kd", "KD1")
    assert X.nhom_doc_duoc(db, nv) == set()
    with pytest.raises(PermissionError):
        X.tong_hop(db, nv, D, now=SAU)
