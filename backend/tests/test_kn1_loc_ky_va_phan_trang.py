"""KN-1 · Màn hình Khiếu nại: lọc theo KỲ, cắt trang, và MỘT định nghĩa cho 'quá hạn'.

Ba món nợ cũ, ghi từ đợt rà giao diện và tới nay mới trả:

  1. Cửa `GET /khieu-nai` trả về MỌI hồ sơ từng có, không một giới hạn nào. Hôm nay bảng còn nhỏ
     nên không ai thấy; nó hỏng vào đúng cái ngày không ai còn nhớ dòng ấy — và hỏng theo kiểu tệ
     nhất, là màn hình đứng chứ không phải báo lỗi.
  2. Không có bộ lọc kỳ, nên phòng CSKH không trả lời được câu hỏi đơn giản nhất của họ: tháng này
     khách kêu bao nhiêu lần, hơn hay kém tháng trước.
  3. `qua_han` lọc bằng Python SAU khi đã dựng xong mọi dòng, nên bộ lọc càng hẹp máy chủ càng
     không nhẹ đi chút nào. Và nó là một BẢN CHÉP TAY của mệnh đề SQL mà bảng số dùng để đếm —
     hai đầu, hai thứ tiếng, không gì buộc chúng giống nhau.

Phép thử nặng nhất của tệp này là cái thứ ba: nó không kiểm một con số nào, nó kiểm rằng hai bản
SQL và Python chọn ra CÙNG MỘT TẬP hồ sơ. Làn Marketing đã học đúng bài ấy ở hạn xử lý lead
(`test_mkt7`, điều 4); ghi lại đây để phân hệ này không phải học lại bằng một lần lệch số.
"""
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import User, Booking, Tour  # noqa: F401 – bảng mà khoá ngoại của Complaint trỏ tới
from app.models.ops import PaymentRequest        # noqa: F401
from app.models.cskh import Complaint
from app.services import cskh as CS

GOC = Path(__file__).resolve().parents[1] / "app"

# MỐC GIỜ DỰNG TAY. Một phép thử về HẠN mà lấy giờ thật thì nó đỏ hay xanh tuỳ lúc chạy, và
# "đỏ lúc 2 giờ sáng" là kiểu hỏng không ai truy được.
BAY_GIO = datetime(2026, 10, 9, 12, 0, 0)


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
    d = {"code": f"KN-T{_dem[0]:04d}", "source": "dien_thoai", "customer_name": "Khách thử",
         "customer_phone": "0900000000", "nhom": "khac", "level": 1,
         "noi_dung": "x", "de_nghi_khach": "y", "received_by": "cntt",
         "received_at": BAY_GIO - timedelta(days=1), "status": "moi",
         "han_phan_hoi": BAY_GIO + timedelta(hours=1), "first_response_at": None}
    d.update(kw)
    c = Complaint(**d)
    db.add(c)
    db.flush()
    return c


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · LỌC KỲ: MỐC LÀ LÚC NHẬN, VÀ CHẶN TRÊN LÀ ĐẦU THÁNG SAU
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def _loc(db, ky):
    dk = CS.dieu_kien_ky(ky)
    q = select(Complaint)
    return list(db.execute(q.where(dk) if dk is not None else q).scalars())


def test_ho_so_nhan_luc_23h_ngay_cuoi_thang_van_thuoc_thang_ay(db):
    """`received_at` là một MỐC GIỜ, không phải một ngày.

    Viết chặn trên là `<= 31/10` thì mọi hồ sơ nhận trong ngày 31 sau 00:00 rơi ra ngoài — mất
    gần trọn một ngày của kỳ, và mất một cách lặng lẽ.
    """
    cuoi = _kn(db, received_at=datetime(2026, 10, 31, 23, 30))
    dau_sau = _kn(db, received_at=datetime(2026, 11, 1, 0, 5))
    t10 = {c.id for c in _loc(db, "2026-10")}
    assert cuoi.id in t10, "Hồ sơ nhận 23:30 ngày 31/10 phải thuộc kỳ 2026-10."
    assert dau_sau.id not in t10, "Hồ sơ nhận 00:05 ngày 1/11 KHÔNG thuộc kỳ 2026-10."
    assert {c.id for c in _loc(db, "2026-11")} == {dau_sau.id}


def test_thang_muoi_hai_sang_nam_sau_khong_vo(db):
    """Tháng 12 + 1 phải ra tháng 1 NĂM SAU. Đây là chỗ cộng tay hay vỡ nhất."""
    trong = _kn(db, received_at=datetime(2026, 12, 20, 9, 0))
    ngoai = _kn(db, received_at=datetime(2027, 1, 3, 9, 0))
    t12 = {c.id for c in _loc(db, "2026-12")}
    assert t12 == {trong.id}, f"Kỳ 2026-12 phải chỉ có hồ sơ tháng 12; đang trả {t12}"
    assert ngoai.id not in t12


def test_ky_rong_la_toan_bo_lich_su(db):
    a = _kn(db, received_at=datetime(2026, 3, 1))
    b = _kn(db, received_at=datetime(2026, 10, 1))
    assert {c.id for c in _loc(db, "")} == {a.id, b.id}
    assert CS.dieu_kien_ky("") is None


def test_ky_sai_dang_thi_bao_loi_chu_khong_am_tham_tra_het(db):
    """Nuốt một kỳ sai rồi trả về toàn bộ lịch sử là nói dối người đọc bằng một bảng số."""
    for xau in ("thang 10", "2026/10", "20-2026", "2026-13", "2026-1", "2026-10-09", "202610"):
        with pytest.raises(ValueError):
            CS.dieu_kien_ky(xau)


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · MỘT ĐỊNH NGHĨA 'QUÁ HẠN' — PHÉP THỬ NẶNG NHẤT CỦA TỆP NÀY
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_ban_SQL_va_ban_Python_cua_qua_han_chon_cung_mot_tap(db):
    """Không kiểm một con số nào — kiểm rằng hai đầu KHÔNG LỆCH NHAU.

    Bảng số đếm bằng SQL, từng dòng tô đỏ bằng Python. Hai bản lệch nhau thì bảng nói 7 hồ sơ quá
    hạn còn danh sách tô đỏ 6 dòng, và không ai biết bên nào đúng. Mớ dữ liệu dưới đây cố tình
    chạm vào mọi mép: hạn rỗng, hạn đúng bằng mốc giờ, đã phản hồi, và từng trạng thái một.
    """
    _kn(db, status="moi", han_phan_hoi=BAY_GIO - timedelta(hours=1))                      # quá hạn
    _kn(db, status="dang_xu_ly", han_phan_hoi=BAY_GIO - timedelta(days=3))                # quá hạn
    _kn(db, status="cho_khach", han_phan_hoi=BAY_GIO - timedelta(minutes=1))              # quá hạn
    _kn(db, status="tai_mo", han_phan_hoi=BAY_GIO - timedelta(seconds=1))                 # quá hạn
    _kn(db, status="da_dong", han_phan_hoi=BAY_GIO - timedelta(days=9))                   # đã đóng
    _kn(db, status="moi", han_phan_hoi=BAY_GIO + timedelta(hours=2))                      # chưa tới hạn
    _kn(db, status="moi", han_phan_hoi=BAY_GIO)                                           # ĐÚNG mốc
    _kn(db, status="moi", han_phan_hoi=None)                                              # chưa đặt hạn
    _kn(db, status="dang_xu_ly", han_phan_hoi=BAY_GIO - timedelta(days=2),
        first_response_at=BAY_GIO - timedelta(days=1))                                    # đã phản hồi

    theo_sql = {c.id for c in db.execute(
        select(Complaint).where(CS.dieu_kien_qua_han(BAY_GIO))).scalars()}
    theo_python = {c.id for c in db.execute(select(Complaint)).scalars()
                   if CS.qua_han_cua(c, BAY_GIO)}
    assert theo_sql == theo_python, (
        f"Hai định nghĩa 'quá hạn' lệch nhau. SQL chọn {sorted(theo_sql)}, Python chọn "
        f"{sorted(theo_python)}. Lệch ở: {sorted(theo_sql ^ theo_python)}")
    assert len(theo_sql) == 4, f"Mớ dữ liệu này có đúng 4 hồ sơ quá hạn; đang đếm {len(theo_sql)}"


def test_dung_moc_gio_thi_chua_qua_han(db):
    """`<` chứ không phải `<=`: đúng giây hết hạn vẫn còn trong hạn."""
    c = _kn(db, han_phan_hoi=BAY_GIO)
    assert CS.qua_han_cua(c, BAY_GIO) is False


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · BẢNG SỐ ĐI THEO KỲ
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_bang_so_di_theo_ky_cua_danh_sach(db):
    _kn(db, received_at=datetime(2026, 9, 5), status="moi")
    _kn(db, received_at=datetime(2026, 9, 7), status="da_dong")
    _kn(db, received_at=datetime(2026, 10, 2), status="moi")
    assert CS.chi_so(db)["tong"] == 3
    t9, t10 = CS.chi_so(db, "2026-09"), CS.chi_so(db, "2026-10")
    assert (t9["tong"], t9["dang_mo"]) == (2, 1)
    assert (t10["tong"], t10["dang_mo"]) == (1, 1)
    assert t10["ky"] == "2026-10", "Bảng số phải nói ra nó đang tính cho kỳ nào."


def test_bang_so_dem_qua_han_bang_dung_menh_de_dung_chung(db):
    _kn(db, received_at=datetime(2026, 10, 2), status="moi",
        han_phan_hoi=datetime(2026, 10, 3))                       # quá hạn (hạn đã ở quá khứ)
    _kn(db, received_at=datetime(2026, 10, 4), status="moi",
        han_phan_hoi=datetime(2099, 1, 1))                        # còn hạn
    assert CS.chi_so(db, "2026-10")["qua_han_chua_phan_hoi"] == 1


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 4 · HÀNG RÀO: MỘT LUẬT, MỘT CHỖ KHAI
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_danh_sach_trang_thai_mo_chi_khai_dung_mot_cho():
    """Trước KN-1 bộ trạng thái 'đang mở' được gõ lại BA lần trong hai tệp."""
    xau = []
    for tep in sorted(GOC.rglob("*.py")):
        if tep.name == "ma_tu_sinh.py":
            continue
        than = tep.read_text(encoding="utf-8")
        for so, dong in enumerate(than.split("\n"), 1):
            if "DANG_MO" in dong or dong.lstrip().startswith("#"):
                continue
            if re.search(r'"moi"\s*,\s*"dang_xu_ly"\s*,\s*"cho_khach"\s*,\s*"tai_mo"', dong):
                xau.append(f"{tep.relative_to(GOC.parent)}:{so}")
    assert not xau, (
        "Bộ trạng thái 'đang mở' được gõ lại thay vì dùng `services/cskh.DANG_MO`. Thêm một "
        "trạng thái mới là phải nhớ sửa từng chỗ, và chỗ bị quên thì đếm thiếu mà không kêu:\n  "
        + "\n  ".join(xau))


def test_cua_danh_sach_cat_trang_va_loc_qua_han_trong_sql():
    """Đọc mã cửa: hai điều này mất đi thì không phép thử dữ liệu nào ở trên bắt được."""
    than = (GOC / "api" / "v1" / "cskh.py").read_text(encoding="utf-8")
    i = than.index("def kn_ds(")
    doan = than[i:than.index("@router.get(\"/khieu-nai/{cid}\")", i)]
    assert "limit" in doan and ".limit(" in doan, (
        "Cửa GET /khieu-nai không cắt trang — nó trả về mọi hồ sơ từng có.")
    assert "dieu_kien_qua_han()" in doan, (
        "Bộ lọc `qua_han` phải là MỆNH ĐỀ SQL dùng chung với bảng số, không phải một vòng lặp "
        "Python chạy sau khi đã dựng xong mọi dòng.")
    assert "tong_khop" in doan, (
        "Cửa phải trả `tong_khop` đếm TRƯỚC khi cắt — không thì màn hình lặng lẽ giấu phần dư.")
