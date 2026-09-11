# -*- coding: utf-8 -*-
"""GD-1 · Trình bày cảnh báo – gom theo nguyên nhân, tách "đã tự xử lý", đếm "chưa có chủ".

Ba chỗ tệp này canh, và cả ba đều làm con số trên màn hình lãnh đạo nói sai:

  1. Trộn "đã tự xử lý" vào "chưa giải quyết" → con số đỏ TO HƠN sự thật. Người ta nhìn một con số
     to rồi hoặc hoảng, hoặc – nguy hơn – quen với nó.
  2. Gom theo MỨC thay vì theo NGUYÊN NHÂN → ra "23 việc đỏ", một câu không ai xử lý được.
  3. "Chưa có chủ" không được đếm → 1.557 dòng vô chủ biến mất khỏi mọi báo cáo, y như trước PQ-9.
"""
from datetime import datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Alert, User
from app.services import canh_bao_trinh_bay as CB


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:", poolclass=sa.pool.StaticPool,
                           connect_args={"check_same_thread": False})
    md.create_all(eng)
    with Session(eng) as s:
        s.add_all([
            User(id=41, username="a", full_name="Nguyễn Văn A", role="nv_kd", password_hash="x"),
            User(id=52, username="b", full_name="Trần Thị B", role="nv_kd", password_hash="x"),
        ])
        s.flush()
        yield s


def _cb(db, kind, level="red", resolved=False, chu=None, dong_boi=None, msg="x", ref="r"):
    a = Alert(kind=kind, level=level, ref=ref, message=msg, to_roles="nv_kd,gd_kd",
              resolved=resolved, nguoi_phu_trach=chu, dong_boi_id=dong_boi,
              created_at=datetime(2026, 9, 11, 8, 0))
    db.add(a)
    db.flush()
    return a


# =============================================================================================
# 1. Gom theo NGUYÊN NHÂN
# =============================================================================================

def test_gom_theo_nguyen_nhan_chu_khong_gom_theo_muc(db):
    """Gom theo mức cho ra '23 việc đỏ' – một con số không nói được phải làm gì."""
    for _ in range(3):
        _cb(db, "qua_deadline_thu", "red")
    _cb(db, "d7", "red")
    r = CB.trinh_bay(db)
    khoa = {o["khoa_gom"]: o["so_viec"] for o in r["chua_giai_quyet"]}
    assert khoa == {"qua_deadline_thu": 3, "d7": 1}


def test_nhan_da_la_tieng_viet_khong_phai_ma(db):
    _cb(db, "qua_deadline_thu")
    o = CB.trinh_bay(db)["chua_giai_quyet"][0]
    assert o["nhan"] == "Quá hạn thu tiền khách" and o["can_dat_ten"] is False


def test_muc_cua_nhom_lay_theo_dong_NANG_NHAT(db):
    """Một nhóm có ba việc vàng và một việc đỏ thì nhóm ấy là đỏ – lấy mức nhẹ nhất là hạ cấp một
    việc đỏ xuống bằng phép trung bình."""
    _cb(db, "d7", "info"); _cb(db, "d7", "warn"); _cb(db, "d7", "red")
    assert CB.trinh_bay(db)["chua_giai_quyet"][0]["muc"] == "do"


def test_do_xep_truoc_vang_truoc_xam(db):
    _cb(db, "d7", "info")
    for _ in range(9):
        _cb(db, "sla_booking", "warn")
    _cb(db, "qua_deadline_thu", "red")
    muc = [o["muc"] for o in CB.trinh_bay(db)["chua_giai_quyet"]]
    assert muc == ["do", "vang", "xam"], "nhóm đỏ một việc vẫn phải đứng trên nhóm vàng chín việc"


# =============================================================================================
# 2. "Đã tự xử lý" tách khỏi "chưa giải quyết"
# =============================================================================================

def test_da_tu_xu_ly_KHONG_lot_vao_nhom_chua_giai_quyet(db):
    """Trộn hai thứ làm con số đỏ trên màn hình lãnh đạo to hơn sự thật."""
    for _ in range(7):
        _cb(db, "het_han_giu_cho", resolved=True, dong_boi=None)
    _cb(db, "d7")
    r = CB.trinh_bay(db)
    assert [o["khoa_gom"] for o in r["chua_giai_quyet"]] == ["d7"]
    assert r["da_tu_xu_ly"] == [{"khoa_gom": "het_han_giu_cho",
                                 "nhan": "Hết hạn giữ chỗ – hệ thống đã trả chỗ về chuyến",
                                 "can_dat_ten": False, "so_viec": 7}]


def test_nguoi_dong_thi_KHONG_phai_tu_xu_ly_va_cung_khong_con_la_viec(db):
    """Ba trạng thái khác nhau, không được gộp: còn nợ · người đã xong · máy tự xong."""
    _cb(db, "d7", resolved=True, dong_boi=41)
    r = CB.trinh_bay(db)
    assert r["chua_giai_quyet"] == [] and r["da_tu_xu_ly"] == []


def test_can_cu_la_COT_dong_boi_chu_khong_phai_danh_sach_loai(db):
    """Một loại hôm nay robot tự xử được, mai người ta tắt robot ấy đi, thì danh sách loại nói sai
    còn cột dong_boi_id vẫn nói đúng."""
    _cb(db, "het_han_giu_cho", resolved=True, dong_boi=52)
    assert CB.trinh_bay(db)["da_tu_xu_ly"] == []
    _cb(db, "d7", resolved=True, dong_boi=None)
    assert [o["khoa_gom"] for o in CB.trinh_bay(db)["da_tu_xu_ly"]] == ["d7"]


# =============================================================================================
# 3. "Chưa có chủ" là một dòng ĐƯỢC ĐẾM
# =============================================================================================

def test_chua_co_chu_duoc_dem_trong_tung_nhom_va_o_tong(db):
    """PQ-9 đo: 1.557 trên 1.703 cảnh báo vô chủ, vì gửi cho bốn vai trò là gửi cho không ai."""
    _cb(db, "d7", chu=41)
    _cb(db, "d7", chu=None)
    _cb(db, "qua_deadline_thu", chu=None)
    r = CB.trinh_bay(db)
    theo = {o["khoa_gom"]: o["chua_co_chu"] for o in r["chua_giai_quyet"]}
    assert theo == {"d7": 1, "qua_deadline_thu": 1}
    assert r["tong_chua_co_chu"] == 2


def test_nguoi_phu_trach_kem_ten_that_va_xep_theo_so_viec(db):
    for _ in range(15):
        _cb(db, "qua_deadline_thu", chu=41)
    for _ in range(8):
        _cb(db, "qua_deadline_thu", chu=52)
    ds = CB.trinh_bay(db)["chua_giai_quyet"][0]["nguoi_phu_trach"]
    assert ds == [{"id": 41, "ten": "Nguyễn Văn A", "so": 15},
                  {"id": 52, "ten": "Trần Thị B", "so": 8}]


def test_to_roles_KHONG_duoc_dung_lam_nguoi_phu_trach(db):
    """to_roles trả lời 'ai được báo tin', không trả lời 'ai phải làm'. Gộp lại là mất đúng cái
    khác biệt mà PQ-9 vừa làm ra."""
    _cb(db, "d7", chu=None)
    o = CB.trinh_bay(db)["chua_giai_quyet"][0]
    assert o["nguoi_phu_trach"] == [] and o["chua_co_chu"] == 1


# =============================================================================================
# 4. Mã loại chưa có nhãn – không giấu, không đặt tên bừa
# =============================================================================================

def test_ma_chua_khai_hien_NGUYEN_MA_kem_co_can_dat_ten(db):
    """Đặt tên bừa nguy hơn để nguyên mã: một nhãn tiếng Việt trông như đã có người xét, nên sẽ
    không ai đi xét nữa."""
    _cb(db, "loai_moi_chua_ai_dat_ten")
    o = CB.trinh_bay(db)["chua_giai_quyet"][0]
    assert o["nhan"] == "loai_moi_chua_ai_dat_ten" and o["can_dat_ten"] is True


def test_ma_chua_khai_VAN_duoc_dem_chu_khong_bi_bo_qua(db):
    _cb(db, "loai_la"); _cb(db, "loai_la"); _cb(db, "d7")
    r = CB.trinh_bay(db)
    assert sum(o["so_viec"] for o in r["chua_giai_quyet"]) == 3


def test_do_duoc_con_bao_nhieu_ma_chua_co_nhan(db):
    """Danh sách VIỆC, đo trên dữ liệu thật – bộ mã là bộ mở, có chỗ truyền kind bằng biến nên
    không đọc tĩnh ra hết được."""
    _cb(db, "loai_la"); _cb(db, "loai_la"); _cb(db, "khac"); _cb(db, "d7")
    assert CB.trinh_bay(db)["loai_chua_co_nhan"] == [{"ma": "loai_la", "so": 2},
                                                     {"ma": "khac", "so": 1}]


def test_moi_nhan_da_khai_deu_dan_duoc_nguon_doc_ra(db):
    """Khai một nhãn mà không nói đọc được ở đâu thì rất có thể nó là một cái tên đoán."""
    for ma, lo in CB.NHAN.items():
        assert len(lo.nhan) >= 10, ma
        assert len(lo.nguon_khai) >= 20, f"{ma}: khai nhãn mà không dẫn được chỗ đọc ra"


# =============================================================================================
# 5. Nói thật về chuyện chưa lọc theo phạm vi
# =============================================================================================

def test_noi_thang_la_CHUA_loc_theo_don_vi(db):
    """Cảnh báo chưa có cột pháp nhân. Một bảng tưởng đã lọc mà chưa lọc còn tệ hơn một bảng nói rõ
    là chưa – vì người xem sẽ đinh ninh con số ấy là của đơn vị mình."""
    _cb(db, "d7")
    r = CB.trinh_bay(db)
    assert r["co_loc_pham_vi"] is False
    assert "CHƯA lọc" in r["ghi_chu"]
    assert not hasattr(Alert, "company_id"), (
        "cảnh báo vừa có cột pháp nhân – phải bật lọc phạm vi và sửa lại ghi chú này")


def test_vi_du_gioi_han_so_dong_va_do_dai(db):
    for i in range(5):
        _cb(db, "d7", msg="Booking 115069 – quá hạn 6 ngày " + "x" * 200, ref=f"r{i}")
    o = CB.trinh_bay(db)["chua_giai_quyet"][0]
    assert len(o["vi_du"]) == 2 and all(len(v) <= 120 for v in o["vi_du"])
    assert o["vi_du"][0].startswith("Booking 115069")
