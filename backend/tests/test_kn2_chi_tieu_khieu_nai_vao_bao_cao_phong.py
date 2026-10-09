"""KN-2 · Sổ khiếu nại đi vào BÁO CÁO PHÒNG của CSKH.

Tới trước vòng này bảng của phòng CSKH chỉ nói về CHĂM SÓC SAU BÁN — lời mời chấm điểm, phiếu
chấm thấp, chuyến không ai chấm, tin Zalo kẹt. Sổ khiếu nại có màn hình riêng và có bảng số riêng
trên màn hình ấy, nhưng KHÔNG một con số nào của nó đi vào báo cáo phòng. Người đọc báo cáo —
trưởng bộ phận, Ban TGĐ, Chủ tịch — không thấy tháng này khách kêu bao nhiêu lần trừ khi tự mở
thêm một màn hình nữa. Một con số phải đi tìm mới thấy thì phần lớn thời gian không ai thấy.

BỐN ĐIỀU TỆP NÀY CANH:

  1. SÁU CHỈ TIÊU CÓ MẶT, và mỗi cái mang đủ cách tính + nguồn (luật B2 của test_bao_cao_phong).
  2. MỘT ĐỊNH NGHĨA 'QUÁ HẠN'. Báo cáo phòng phải gọi `cskh.dieu_kien_qua_han()`, KHÔNG được tự
     viết lại mệnh đề. Vòng KN-1 vừa gom hai bản SQL/Python về một chỗ; viết lại ở đây là dựng
     cái đầu THỨ BA, và ba đầu thì chắc chắn có hai cái lệch.
  3. CẮT KỲ ĐÚNG CHỖ. Hồ sơ đếm theo NGÀY NHẬN; riêng 'quá hạn' là TỒN ĐỌNG nên KHÔNG cắt kỳ —
     hồ sơ quá hạn từ tháng trước vẫn đang quá hạn hôm nay.
  4. RỖNG KHÁC KHÔNG. Chưa hồ sơ nào phản hồi thì ô 'trễ hạn' để rỗng, không ghi 0 — và ô rỗng
     thì không được tô màu cảnh báo.
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import User, Booking, Tour, Company  # noqa: F401
from app.models.ops import PaymentRequest                # noqa: F401
from app.models.cskh import Complaint
from app.services import bao_cao_phong as BP

GOC = Path(__file__).resolve().parents[1] / "app"
TU, DEN = date(2026, 10, 1), date(2026, 10, 31)
TRONG_KY = datetime(2026, 10, 15, 9, 0)


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


_dem = [0]


def _kn(db, **kw):
    _dem[0] += 1
    d = {"code": f"KN-K{_dem[0]:04d}", "source": "dien_thoai", "customer_name": "Khách thử",
         "nhom": "khac", "level": 1, "noi_dung": "x", "de_nghi_khach": "y",
         "received_at": TRONG_KY, "status": "moi",
         "han_phan_hoi": TRONG_KY + timedelta(days=30), "first_response_at": None}
    d.update(kw)
    c = Complaint(**d)
    db.add(c)
    db.flush()
    return c


def _bang(db) -> dict:
    return {x["ma"]: x for x in BP._cskh_dong(db, TU, DEN)}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · SÁU CHỈ TIÊU CÓ MẶT VÀ ĐỦ CẤU TRÚC
# ═══════════════════════════════════════════════════════════════════════════════════════════════

SAU_O = ("kn_moi", "kn_qua_han", "kn_muc3", "kn_tre_phan_hoi", "kn_tai_mo", "kn_nhom_dau")


def test_sau_chi_tieu_khieu_nai_co_mat_trong_bao_cao_phong_cskh(db):
    b = _bang(db)
    thieu = [m for m in SAU_O if m not in b]
    assert not thieu, (
        f"Báo cáo phòng CSKH thiếu chỉ tiêu khiếu nại: {thieu}. Sổ khiếu nại có màn hình riêng, "
        "nhưng con số của nó phải lên được bảng mà Ban TGĐ và Chủ tịch đọc hằng kỳ.")


def test_moi_chi_tieu_moi_deu_noi_duoc_cach_tinh_va_nguon(db):
    """Luật B2 của test_bao_cao_phong: một chỉ tiêu thiếu cách tính vẫn hiện ra bình thường, không
    lỗi, không đỏ — nó chỉ hỏng ở chỗ người đọc thôi tin bảng."""
    b = _bang(db)
    for m in SAU_O:
        assert (b[m].get("cong_thuc") or "").strip(), f"{m} không nói cách tính."
        assert (b[m].get("nguon") or "").strip(), f"{m} không nói nguồn số."
        assert (b[m].get("ten") or "").strip(), f"{m} không có tên đọc được."


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · MỘT ĐỊNH NGHĨA 'QUÁ HẠN' — KHÔNG DỰNG CÁI ĐẦU THỨ BA
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_bao_cao_phong_goi_ham_chung_chu_khong_viet_lai_menh_de_qua_han():
    than = (GOC / "services" / "bao_cao_phong.py").read_text(encoding="utf-8")
    assert "dieu_kien_qua_han()" in than, (
        "Báo cáo phòng phải gọi `cskh.dieu_kien_qua_han()`. Vòng KN-1 đã gom hai bản SQL/Python "
        "về một chỗ; viết lại mệnh đề ở đây là dựng cái đầu THỨ BA.")
    xau = re.findall(r"first_response_at\.is_\(None\)", than)
    assert not xau, (
        "Tệp này đang tự dựng lại mệnh đề 'chưa phản hồi'. Gọi `cskh.dieu_kien_qua_han()` thay vì "
        "chép — ba chỗ cùng trả lời một câu thì chắc chắn có hai chỗ lệch.")


def test_con_so_qua_han_khop_dung_menh_de_chung(db):
    from app.services import cskh as CS
    from sqlalchemy import select
    _kn(db, status="moi", han_phan_hoi=datetime(2026, 10, 2))                 # quá hạn
    _kn(db, status="dang_xu_ly", han_phan_hoi=datetime(2026, 10, 3))          # quá hạn
    _kn(db, status="da_dong", han_phan_hoi=datetime(2026, 10, 4))             # đã đóng
    _kn(db, status="moi", han_phan_hoi=datetime(2099, 1, 1))                  # còn hạn
    theo_menh_de = len(db.execute(select(Complaint).where(CS.dieu_kien_qua_han())).scalars().all())
    assert _bang(db)["kn_qua_han"]["gia_tri"] == theo_menh_de == 2


def test_qua_han_la_TON_DONG_nen_khong_cat_theo_ky(db):
    """Hồ sơ quá hạn từ tháng trước vẫn đang quá hạn hôm nay — cắt nó ra khỏi kỳ là giấu đúng cái
    cần thấy. Cùng lý do với dòng tin Zalo kẹt chờ cấu hình ở ngay trên."""
    _kn(db, received_at=datetime(2026, 8, 20, 9, 0), status="moi",
        han_phan_hoi=datetime(2026, 8, 21, 9, 0))
    b = _bang(db)
    assert b["kn_moi"]["gia_tri"] == 0, "Hồ sơ tháng 8 KHÔNG được tính vào số nhận trong kỳ tháng 10."
    assert b["kn_qua_han"]["gia_tri"] == 1, (
        "Nhưng nó VẪN phải hiện ở ô quá hạn: nó đang treo thật, và treo từ tháng trước thì còn "
        "đáng lo hơn.")
    assert b["kn_qua_han"]["muc"] == "do", "Có hồ sơ quá hạn mà không tô đỏ thì không ai thấy."


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · CẮT KỲ THEO NGÀY NHẬN
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_dem_theo_NGAY_NHAN_chu_khong_theo_ngay_dong(db):
    """Hồ sơ nhận tháng này đóng tháng sau vẫn là tiếng kêu của tháng này."""
    _kn(db, received_at=datetime(2026, 10, 28, 9, 0), status="da_dong",
        closed_at=datetime(2026, 11, 3, 9, 0))
    _kn(db, received_at=datetime(2026, 9, 28, 9, 0), status="da_dong",
        closed_at=datetime(2026, 10, 3, 9, 0))
    assert _bang(db)["kn_moi"]["gia_tri"] == 1


def test_muc3_va_tai_mo_dem_dung_va_co_tro_tay(db):
    _kn(db, level=3)
    _kn(db, level=1, reopen_reason="Khách gọi lại nói phương án không chạy được")
    b = _bang(db)
    assert b["kn_muc3"]["gia_tri"] == 1 and b["kn_muc3"]["muc"] == "vang"
    assert b["kn_tai_mo"]["gia_tri"] == 1 and b["kn_tai_mo"]["muc"] == "vang"
    for m in ("kn_muc3", "kn_tai_mo"):
        assert (b[m].get("viec") or "").strip(), (
            f"{m} tô màu cảnh báo mà không nói làm gì. Một con số đỏ không kèm việc thì chỉ tạo "
            "lo lắng, không tạo hành động.")


def test_nhom_bi_keu_nhieu_nhat_noi_duoc_LA_NHOM_NAO(db):
    """Một con số không nói được nhóm nào thì không dùng được."""
    for _ in range(3):
        _kn(db, nhom="dich_vu")
    _kn(db, nhom="khac")
    o = _bang(db)["kn_nhom_dau"]
    assert o["gia_tri"] == 3
    assert o["chi_tiet"] and len(o["chi_tiet"]) == 2, (
        f"Phần chi tiết phải liệt kê bảng xếp nhóm; đang có {o['chi_tiet']}")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · RỖNG KHÁC KHÔNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_chua_ho_so_nao_phan_hoi_thi_o_TRE_HAN_de_rong_chu_khong_ghi_khong(db):
    """'Chưa đo được' khác hẳn 'đo ra không có'. Ghi 0 vào đây là nói với người đọc rằng kỳ này
    không ai trả lời trễ, trong khi sự thật là chưa ai trả lời."""
    _kn(db)
    o = _bang(db)["kn_tre_phan_hoi"]
    assert o["gia_tri"] is None, f"Phải RỖNG khi chưa hồ sơ nào phản hồi; đang trả {o['gia_tri']!r}"
    assert o["muc"] == "", "Ô rỗng không được tô màu cảnh báo — một phòng chưa có số không phải một phòng có vấn đề."


def test_co_ho_so_phan_hoi_dung_han_thi_o_TRE_HAN_la_khong_chu_khong_rong(db):
    _kn(db, han_phan_hoi=datetime(2026, 10, 16, 9, 0),
        first_response_at=datetime(2026, 10, 15, 10, 0))
    o = _bang(db)["kn_tre_phan_hoi"]
    assert o["gia_tri"] == 0 and o["muc"] == ""


def test_phan_hoi_muon_hon_han_thi_dem_va_to_mau(db):
    _kn(db, han_phan_hoi=datetime(2026, 10, 15, 10, 0),
        first_response_at=datetime(2026, 10, 16, 9, 0))
    o = _bang(db)["kn_tre_phan_hoi"]
    assert o["gia_tri"] == 1 and o["muc"] == "vang"


def test_so_khieu_nai_rong_thi_nhom_dau_de_rong_va_khong_to_mau(db):
    o = _bang(db)["kn_nhom_dau"]
    assert o["gia_tri"] is None and o["muc"] == ""
