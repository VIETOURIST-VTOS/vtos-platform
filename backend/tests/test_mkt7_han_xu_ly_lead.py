"""HẠN XỬ LÝ MỘT LEAD — P.TGĐ Phan Ngọc Tuấn chốt 24 giờ ngày 18/9/2026.

Câu hỏi này treo từ bản thiết kế Marketing 18/9: hạn xử lý một lead là bao lâu, và AI ký con số ấy.
Nay đã có chữ ký, nên con số vào bảng tham số (`rules.DEFAULT_PARAMS`) chứ không vào mã.

BỐN ĐIỀU TỆP NÀY CANH, và cả bốn đều là chỗ đã từng hỏng ở phân hệ khác của chính kho này:

  1. CON SỐ Ở BẢNG THAM SỐ, KHÔNG VIẾT CỨNG. Viết cứng là mất cả người ký lẫn cửa nhập trong một
     dòng — và sáu tháng nữa không ai biết ai đặt ra con số đó.
  2. ĐẾM TỪ LÚC LEAD VÀO SỔ, không phải từ lúc ai mở màn hình.
  3. ĐÃ XỬ LÝ LẤY HỢP HAI DẤU (có giờ liên hệ HOẶC trạng thái đã đổi). Soi một dấu là đếm nhầm.
  4. CHỖ ĐẾM VÀ CHỖ ĐÁNH DẤU TỪNG DÒNG DÙNG CHUNG MỘT ĐỊNH NGHĨA. Đếm bằng SQL còn đánh dấu bằng
     Python là hai đầu, và hai đầu thì sớm muộn lệch nhau.
"""
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import User  # noqa: F401  – bảng mà khoá ngoại của Lead trỏ tới
from app.models.crm import Lead
from app.services import leads as L
from app.services import rules as R

# MỐC GIỜ DỰNG TAY. Không dùng datetime.now(): một phép thử về HẠN mà lấy giờ thật thì nó đỏ hay
# xanh tuỳ lúc chạy, và "đỏ lúc 2 giờ sáng" là kiểu hỏng không ai truy được.
BAY_GIO = datetime(2026, 9, 18, 12, 0, 0)


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


_dem = [0]


def _lead(db, **kw):
    _dem[0] += 1
    d = {"phone": f"090000{_dem[0]:04d}", "channel": "Facebook", "lead_month": "2026-09",
         "received_at": BAY_GIO - timedelta(hours=1), "status": "moi", "last_contact_at": None}
    d.update(kw)
    l = Lead(**d); db.add(l); db.flush(); return l


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · CON SỐ LÀ MỘT CHỮ KÝ, KHÔNG PHẢI MỘT HẰNG SỐ TRONG MÃ
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_han_da_ky_la_24_gio_va_doc_tu_bang_tham_so():
    khoa = [p for p in R.DEFAULT_PARAMS if p[0] == "lead_han_xu_ly_gio"]
    assert khoa, ("Chưa khai `lead_han_xu_ly_gio` trong rules.DEFAULT_PARAMS. Hạn xử lý là một con "
                  "số LUẬT: nó phải nằm ở bảng có cột người ký và có cửa nhập, không nằm trong mã.")
    assert float(khoa[0][1]) == 24.0, f"P.TGĐ chốt 24 giờ; bảng tham số đang ghi {khoa[0][1]}"
    nguoi_ky = khoa[0][4]
    assert "Phan Ngọc Tuấn" in nguoi_ky and "18/9/2026" in nguoi_ky, (
        f"Cột cuối phải ghi AI ký và NGÀY nào. Đang ghi: {nguoi_ky!r}")


def test_khong_viet_cung_so_24_trong_ma_nghiep_vu():
    """Con số ở hai chỗ là hai chỗ phải nhớ sửa. Một trong hai sẽ bị quên."""
    from pathlib import Path
    src = Path(__file__).resolve().parents[1] / "app" / "services" / "leads.py"
    than = src.read_text(encoding="utf-8")
    than = "\n".join(d for d in than.splitlines() if not d.lstrip().startswith("#"))
    import re
    xau = re.findall(r"timedelta\(\s*hours\s*=\s*24\b", than)
    assert not xau, ("services/leads.py viết cứng 24 giờ. Hạn phải đọc qua gio_han(db) → tham số "
                     "`lead_han_xu_ly_gio`, để đổi hạn là một lần duyệt tham số chứ không phải một "
                     "lần đẩy mã.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · ĐẾM TỪ LÚC LEAD VÀO SỔ
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_han_dem_tu_luc_lead_VAO_SO(db):
    vao_so = datetime(2026, 9, 18, 8, 0, 0)
    l = _lead(db, received_at=vao_so)
    assert L.han_xu_ly(l, 24.0) == vao_so + timedelta(hours=24), (
        "Hạn phải đếm từ received_at. Đếm từ lúc mở màn hình thì mỗi lần xem là một hạn mới, và "
        "không lead nào quá hạn bao giờ.")


def test_chua_den_han_thi_chua_qua_han(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=23, minutes=59))
    assert L.qua_han(l, 24.0, BAY_GIO) is False


def test_qua_24_gio_ma_chua_ai_cham_thi_QUA_HAN(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=24, minutes=1))
    assert L.qua_han(l, 24.0, BAY_GIO) is True


def test_KHONG_BIET_LEAD_VAO_SO_LUC_NAO_THI_KHONG_KET_LUAN_QUA_HAN(db):
    """Không có mốc thì không có hạn, và không có hạn thì không kết luận. Cùng một lẽ với 'chưa đối
    chiếu thì tỷ lệ chốt là CHƯA XÁC ĐỊNH, không phải 0%' — mặc định thành 'quá hạn' là vu cho
    người ta một lần chậm trễ mà sổ không chứng minh được."""
    l = _lead(db)
    l.received_at = None
    assert L.han_xu_ly(l, 24.0) is None
    assert L.qua_han(l, 24.0, BAY_GIO) is False


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · ĐÃ XỬ LÝ = HỢP CỦA HAI DẤU
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_da_ghi_gio_lien_he_thi_khong_con_qua_han_du_trang_thai_van_la_moi(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=48),
              last_contact_at=BAY_GIO - timedelta(hours=40), status="moi")
    assert L.da_xu_ly(l) is True
    assert L.qua_han(l, 24.0, BAY_GIO) is False


def test_da_doi_trang_thai_thi_khong_con_qua_han_du_quen_ghi_gio_lien_he(db):
    """Sale chuyển lead sang 'đang chăm sóc' mà quên ghi giờ liên hệ vẫn là ĐÃ xử lý. Soi mỗi
    last_contact_at là đếm nhầm người ta thành chậm trễ."""
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=48), last_contact_at=None,
              status="dang_cham_soc")
    assert L.da_xu_ly(l) is True
    assert L.qua_han(l, 24.0, BAY_GIO) is False


def test_lead_da_chot_khong_bao_gio_bi_tinh_qua_han(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(days=30), last_contact_at=None, status="chot")
    assert L.qua_han(l, 24.0, BAY_GIO) is False


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · MỘT ĐỊNH NGHĨA CHO CẢ CHỖ ĐẾM LẪN CHỖ ĐÁNH DẤU
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_SQL_dem_ra_dung_bang_so_dong_Python_danh_dau(db):
    """Đây là phép thử quan trọng nhất của tệp. Chỗ đếm chạy bằng SQL, chỗ đánh dấu từng dòng chạy
    bằng Python. Hai đầu lệch nhau thì màn hình hiện 'có 5 lead quá hạn' mà mở ra chỉ thấy 3 dòng
    đỏ — và người dùng mất niềm tin vào cả hai con số."""
    _lead(db, received_at=BAY_GIO - timedelta(hours=30))                                  # quá hạn
    _lead(db, received_at=BAY_GIO - timedelta(hours=30))                                  # quá hạn
    _lead(db, received_at=BAY_GIO - timedelta(hours=30), last_contact_at=BAY_GIO)          # đã liên hệ
    _lead(db, received_at=BAY_GIO - timedelta(hours=30), status="dang_cham_soc")           # đã đổi trạng thái
    _lead(db, received_at=BAY_GIO - timedelta(hours=1))                                    # chưa tới hạn

    rows = list(db.execute(select(Lead)).scalars())
    theo_python = sum(1 for l in rows if L.qua_han(l, 24.0, BAY_GIO))
    theo_sql = L.dem_qua_han(db, select(Lead), 24.0, BAY_GIO)

    assert theo_python == 2, f"Python đánh dấu {theo_python} dòng, đáng ra 2"
    assert theo_sql == theo_python, (
        f"SQL đếm {theo_sql} nhưng Python đánh dấu {theo_python}. Hai đầu đã lệch — cả hai phải đi "
        f"qua cùng một định nghĩa trong services/leads.py.")


def test_dem_chay_tren_bo_loc_dang_xem_chu_khong_tren_trang_da_cat(db):
    """Danh sách cắt ở 300 dòng. Đếm trên trang đã cắt thì con số quá hạn nhỏ hơn sự thật, và nhỏ
    một cách im lặng — kiểu sai tệ nhất."""
    for _ in range(5):
        _lead(db, received_at=BAY_GIO - timedelta(hours=30))
    qs = select(Lead).order_by(Lead.id)
    assert L.dem_qua_han(db, qs, 24.0, BAY_GIO) == 5
    # Cắt hai dòng đầu rồi đếm lại: hàm đếm KHÔNG được nhìn vào giới hạn của trang.
    assert L.dem_qua_han(db, qs.limit(2), 24.0, BAY_GIO) == 5, (
        "dem_qua_han() đang đếm trên trang đã cắt. Phải đếm trên bộ lọc TRƯỚC khi cắt.")


def test_lead_out_mang_theo_han_va_co_qua_han(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=30))
    ra = L.lead_out(l, db)
    assert "han_xu_ly" in ra and "qua_han" in ra, (
        "Màn hình không tự tính lại hạn được — sổ phải trả kèm, nếu không mỗi màn hình lại dựng một "
        "bản định nghĩa riêng.")
    assert ra["han_xu_ly"] == l.received_at + timedelta(hours=24)
    assert ra["qua_han"] is True


def test_goi_lead_out_khong_kem_db_thi_KHONG_DOAN_bang_mot_so_viet_cung(db):
    l = _lead(db, received_at=BAY_GIO - timedelta(hours=30))
    ra = L.lead_out(l)
    assert ra["han_xu_ly"] is None and ra["qua_han"] is None, (
        "Không đọc được tham số đã ký thì trả None, không được lấy 24 làm mặc định trong mã.")
