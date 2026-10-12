# -*- coding: utf-8 -*-
"""Đợt E4a — điều khoản thanh toán và đợt thanh toán.

Sáu điều tệp này canh:

  A. Một điều khoản khai sai thì NÉM LỖI NÓI RÕ SAI Ở ĐÂU, không im lặng nhận.
  B. TỔNG CÁC ĐỢT LUÔN BẰNG TỔNG NGHĨA VỤ, đến từng đồng — kể cả khi chia ba phần bằng nhau.
  C. Mốc rỗng thì hạn rỗng; KHÔNG lấy hôm nay thay thế.
  D. Sửa điều khoản đang dùng: đợt đã trả và đợt đang quá hạn KHÔNG bị dời.
  E. Luật chữ ký đọc từ `chu_ky`, không khai lại.
  F. Hai bảng mới có thật trong `Base.metadata` — cái bẫy đã sập mười ba lần ở `models/__init__.py`.
"""
import io
import os
import sys
import tempfile

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_e4.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import chu_ky as CK  # noqa: E402
from app.services import dieu_khoan as DK  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HAI_DOT = [
    {"ty_le": 50, "lech_ngay": -30, "dien_giai": "Đặt cọc khi chốt đoàn"},
    {"ty_le": 50, "lech_ngay": -7, "dien_giai": "Thanh toán nốt trước khi đi"},
]
BA_DOT_DEU = [
    {"ty_le": 100 / 3, "lech_ngay": 0},
    {"ty_le": 100 / 3, "lech_ngay": 30},
    {"ty_le": 100 / 3, "lech_ngay": 60},
]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. KHAI SAI THÌ NÓI RA SAI Ở ĐÂU
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e4_1_tong_ty_le_khong_du_100_thi_chan_va_noi_ly_do():
    with pytest.raises(DK.SaiDieuKhoan) as ex:
        DK.kiem_dot([{"ty_le": 50, "lech_ngay": 0}, {"ty_le": 30, "lech_ngay": 30}])
    loi = str(ex.value)
    assert "80" in loi, "Lời chặn phải nói ra tổng ĐANG LÀ bao nhiêu, không chỉ nói 'sai'."
    assert "dòng tiền" in loi, "Phải nói hậu quả: phần thiếu không hiện ở tháng nào."


def test_e4_2_dot_thieu_so_lieu_thi_chan_va_chi_dung_dot_nao():
    with pytest.raises(DK.SaiDieuKhoan) as ex:
        DK.kiem_dot([{"ty_le": 100}])
    assert "Đợt 1" in str(ex.value)
    with pytest.raises(DK.SaiDieuKhoan) as ex:
        DK.kiem_dot([{"ty_le": 60, "lech_ngay": 0}, {"ty_le": -5, "lech_ngay": 10},
                     {"ty_le": 45, "lech_ngay": 20}])
    assert "Đợt 2" in str(ex.value)
    with pytest.raises(DK.SaiDieuKhoan):
        DK.kiem_dot([])


def test_e4_3_moc_khong_co_that_thi_chan_va_liet_ke_moc_co_that():
    with pytest.raises(DK.SaiDieuKhoan) as ex:
        DK.kiem_moc("ngay_toi_thich")
    assert "khoi_hanh" in str(ex.value)
    for m in DK.MOC:
        assert DK.kiem_moc(m) == m


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. TỔNG CÁC ĐỢT LUÔN BẰNG TỔNG — ĐẾN TỪNG ĐỒNG
# ═════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("tong", [100_000_000, 189_000_000, 1, 7, 999_999_999, 420_000_000])
@pytest.mark.parametrize("ten_dot,dot", [("hai", HAI_DOT), ("ba_deu", BA_DOT_DEU)])
def test_e4_4_tong_cac_dot_bang_tong_nghia_vu(tong, ten_dot, dot):
    """ĐÂY LÀ PHÉP THỬ QUAN TRỌNG NHẤT CỦA ĐỢT.

    Ba lần làm tròn 1/3 có thể lệch vài đồng, và vài đồng ấy làm màn hình bật cảnh báo đỏ "tổng
    các đợt khác tổng nghĩa vụ". Một cảnh báo đỏ sai vì làm tròn dạy người dùng bỏ qua nó — nguy
    hiểm hơn hẳn không có cảnh báo nào."""
    tien = DK.chia_tien(tong, dot)
    assert len(tien) == len(dot)
    assert sum(tien) == tong, f"{ten_dot}: tổng các đợt {sum(tien)} ≠ tổng nghĩa vụ {tong}"
    assert all(t >= 0 for t in tien)


def test_e4_5_tong_rong_thi_moi_dot_bang_khong_chu_khong_no_loi():
    """K2: rỗng ≠ 0. Tổng chưa ai nhập thì các đợt chưa có tiền, nhưng cấu trúc đợt vẫn dựng được
    để người dùng thấy lịch trả trước khi biết số tiền."""
    assert DK.chia_tien(None, HAI_DOT) == [0.0, 0.0]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. MỐC RỖNG THÌ HẠN RỖNG
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e4_6_moc_rong_thi_han_rong_khong_lay_hom_nay_thay_the():
    """Lấy hôm nay làm mốc thay cho một ngày chưa biết là bịa ra một hạn, và một hạn bịa trông y
    hệt một hạn thật trên màn hình."""
    assert DK.suy_han(None, -7) is None
    assert DK.suy_han(date(2026, 8, 20), -7) == date(2026, 8, 13)
    assert DK.suy_han(date(2026, 8, 20), 30) == date(2026, 9, 19)
    assert DK.suy_han(date(2026, 8, 20), 0) == date(2026, 8, 20)


def test_e4_7_can_cu_han_doc_duoc_va_phan_biet_truoc_sau():
    truoc = DK.can_cu_han("khoi_hanh", -7)
    sau = DK.can_cu_han("nhan_hoa_don", 30)
    assert "khởi hành" in truoc.lower() and "7" in truoc
    assert "hóa đơn" in sau.lower() and "30" in sau
    assert truoc != sau
    assert "−" in truoc and "+" in sau


def test_e4_8_dung_dot_ra_du_so_dot_dung_thu_tu_va_dung_han():
    ra = DK.dung_dot(189_000_000, HAI_DOT, "khoi_hanh", date(2026, 8, 20))
    assert [d["so_thu_tu"] for d in ra] == [1, 2]
    assert [d["ngay_han"] for d in ra] == [date(2026, 7, 21), date(2026, 8, 13)]
    assert sum(d["so_tien"] for d in ra) == 189_000_000
    assert all(d["can_cu_han"] for d in ra)
    assert ra[0]["dien_giai"] == "Đặt cọc khi chốt đoàn"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. SỬA ĐIỀU KHOẢN ĐANG DÙNG — HAI LOẠI ĐỢT KHÔNG BỊ DỜI
# ═════════════════════════════════════════════════════════════════════════════════════════════
HOM_NAY = date(2026, 10, 12)


def test_e4_9_dot_da_tra_khong_bi_doi_han():
    """Dời hạn của một khoản đã xong là viết lại lịch sử."""
    assert DK.duoc_tinh_lai(date(2027, 1, 1), 94_500_000, 94_500_000, HOM_NAY) is False
    assert "đã trả" in DK.vi_sao_khong_tinh_lai(date(2027, 1, 1), 94_500_000, 94_500_000, HOM_NAY)
    # trả MỘT PHẦN cũng không dời: một khoản đã động tới tiền thì hạn của nó đã có hệ quả thật.
    assert DK.duoc_tinh_lai(date(2027, 1, 1), 94_500_000, 10_000_000, HOM_NAY) is False


def test_e4_10_dot_dang_qua_han_khong_bi_doi_sang_tuong_lai():
    """Luật sổ nghĩa vụ 11/9/2026: 'Thay lịch trả không tự xoá quá hạn theo cam kết'.

    Đây là chỗ câu chốt của Chủ tịch ngày 12/10 ('tính lại cả hợp đồng đang gắn') gặp một luật đã
    có chữ ký, và phạm vi tính lại hẹp lại đúng ở đây."""
    assert DK.duoc_tinh_lai(date(2026, 8, 13), 94_500_000, None, HOM_NAY) is False
    ly_do = DK.vi_sao_khong_tinh_lai(date(2026, 8, 13), 94_500_000, None, HOM_NAY)
    assert "quá hạn" in ly_do and "11/9/2026" in ly_do


def test_e4_11_dot_chua_tra_con_o_tuong_lai_thi_duoc_tinh_lai():
    assert DK.duoc_tinh_lai(date(2026, 11, 19), 168_000_000, None, HOM_NAY) is True
    assert DK.vi_sao_khong_tinh_lai(date(2026, 11, 19), 168_000_000, None, HOM_NAY) == ""
    # Đúng ngày hôm nay vẫn còn kịp – chưa quá hạn.
    assert DK.duoc_tinh_lai(HOM_NAY, 1000, None, HOM_NAY) is True
    # Chưa có hạn thì không có gì để quá – vẫn tính lại được.
    assert DK.duoc_tinh_lai(None, 1000, None, HOM_NAY) is True


# ═════════════════════════════════════════════════════════════════════════════════════════════
# E. LUẬT CHỮ KÝ ĐỌC TỪ BẢNG LUẬT, KHÔNG KHAI LẠI
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e4_12_dieu_khoan_do_chu_tich_ky_va_luat_nam_o_chu_ky():
    assert DK.LOAI_CHU_KY in CK.VAI_KY_CAN, (
        "Luật ký của điều khoản phải nằm trong `chu_ky.VAI_KY_CAN`, không khai riêng ở "
        "`dieu_khoan.py` — một luật, một chỗ (bài học LG1, LG2, LG3).")
    assert CK.can_ky(DK.LOAI_CHU_KY) == ("chutich",), "Chủ tịch chốt 12/10/2026: Chủ tịch ký."


def test_e4_13_dieu_khoan_py_khong_khai_lai_ten_vai_nao():
    """Khai tay tên vai ở đây là một ngày nào đó bảng luật đổi mà chỗ này còn nói luật cũ — đúng
    ba chỗ mà Đợt LG3 đã phải đi sửa."""
    s = io.open(os.path.join(GOC, "app", "services", "dieu_khoan.py"), encoding="utf-8").read()
    than = "\n".join(d for d in s.split("\n") if not d.lstrip().startswith("#"))
    for vai in ("chutich", "tgd", "ketoan_truong"):
        assert f'"{vai}"' not in than, f"`dieu_khoan.py` khai cứng vai `{vai}` — phải hỏi bảng luật."


# ═════════════════════════════════════════════════════════════════════════════════════════════
# F. HAI BẢNG CÓ THẬT, VÀ BẢN DI TRÚ KHAI ĐÚNG CHÚNG
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_e4_14_hai_bang_moi_nam_trong_metadata():
    """Cái bẫy đã sập mười ba lần: một bảng khai dưới `app/models` mà thiếu dòng nhập ở
    `models/__init__.py` thì nó không vào `Base.metadata` — create_all không tạo, mọi phép thử soi
    metadata mù đúng bảng ấy mà vẫn xanh, và alembic autogenerate đòi XOÁ bảng."""
    import app.models  # noqa: F401
    from app.db.session import Base
    for bang in ("dieu_khoan_thanh_toan", "dot_thanh_toan"):
        assert bang in Base.metadata.tables, f"Bảng {bang} không có trong Base.metadata"
    assert "dieu_khoan_id" in Base.metadata.tables["nghia_vu_thanh_toan"].columns


def test_e4_15_chi_muc_duy_nhat_tren_nghia_vu_va_so_thu_tu():
    """Không có ràng buộc này thì một lần dựng lại đợt mà quên xoá đợt cũ sẽ nhân đôi tiền của cả
    nghĩa vụ, và tổng vẫn trông hợp lý."""
    from app.db.session import Base
    t = Base.metadata.tables["dot_thanh_toan"]
    duy_nhat = [i for i in t.indexes if i.unique]
    cot = {tuple(c.name for c in i.columns) for i in duy_nhat}
    assert ("nghia_vu_id", "so_thu_tu") in cot, f"Chỉ mục duy nhất đang có: {cot}"


def test_e4_16_ban_di_tru_khai_hai_bang_cot_tien_dung_so_thap_phan():
    d = os.path.join(GOC, "alembic", "versions")
    tep = [t for t in os.listdir(d) if t.startswith("e4a1b2c3d4e5")]
    assert len(tep) == 1, f"Không thấy bản di trú E4a trong {d}"
    s = io.open(os.path.join(d, tep[0]), encoding="utf-8").read()
    for x in ("dieu_khoan_thanh_toan", "dot_thanh_toan", "dieu_khoan_id",
              "ux_dot_nghia_vu_stt", "unique=True"):
        assert x in s, f"Bản di trú thiếu {x}"
    assert "sa.Float" not in s, (
        "Cột tiền phải dùng Numeric như `TIEN`, không phải Float — V9 đã đổi tám cột tiền sang số "
        "thập phân ngày 08/9/2026, khai Float ở đây là dựng lại đúng cái đã sửa.")
    assert "Numeric" in s


# ═════════════════════════════════════════════════════════════════════════════════════════════
# G. CHẠY THẬT TRÊN CƠ SỞ DỮ LIỆU
# ═════════════════════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _nghia_vu(db, tong=189_000_000.0):
    from app.models.nghia_vu import NghiaVuThanhToan
    nv = NghiaVuThanhToan(ma_goc=f"NV-E4-{int(tong)}", huong="chi", nhom="tra_ncc",
                          doi_tuong="Khách sạn E4", tong_nghia_vu=tong,
                          nguon_bang="test_e4", nguon_id=int(tong) % 100000)
    db.add(nv)
    db.flush()
    return nv


def test_e4_17_ghi_hai_dot_va_tong_khop_tong_nghia_vu(db):
    from app.models.nghia_vu import DotThanhToan
    nv = _nghia_vu(db)
    for d in DK.dung_dot(nv.tong_nghia_vu, HAI_DOT, "khoi_hanh", date(2026, 8, 20)):
        db.add(DotThanhToan(nghia_vu_id=nv.id, ngay_han_suy=d["ngay_han"], **d))
    db.flush()
    dot = db.query(DotThanhToan).filter_by(nghia_vu_id=nv.id).all()
    assert len(dot) == 2
    assert sum(float(x.so_tien) for x in dot) == float(nv.tong_nghia_vu)
    assert dot[0].con_lai() == float(dot[0].so_tien) and not dot[0].da_tra_du()
    db.rollback()


def test_e4_18_hai_dot_cung_so_thu_tu_thi_co_so_du_lieu_chan(db):
    from sqlalchemy.exc import IntegrityError
    from app.models.nghia_vu import DotThanhToan
    nv = _nghia_vu(db, 50_000_000.0)
    db.add(DotThanhToan(nghia_vu_id=nv.id, so_thu_tu=1, so_tien=50_000_000))
    db.flush()
    db.add(DotThanhToan(nghia_vu_id=nv.id, so_thu_tu=1, so_tien=50_000_000))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_e4_19_nghia_vu_khong_co_dot_nao_van_doc_duoc_y_nhu_truoc(db):
    """Sổ cũ không có đợt nào, và bản di trú CỐ Ý không nạp lại. Nghĩa vụ phải đọc được y như
    trước đợt này — `con_lai()` không đổi một đồng."""
    nv = _nghia_vu(db, 62_400_000.0)
    nv.da_tra = 12_400_000.0
    db.flush()
    assert nv.con_lai() == 50_000_000.0
    assert nv.dieu_khoan_id is None
    db.rollback()
