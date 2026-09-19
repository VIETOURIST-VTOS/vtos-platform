"""Cửa ĐẶT MÃ TOUR cho tệp quyết toán cũ không khai mã.

19 tệp trong kho không khai ô 'Mã tour' — 29,85 tỷ đồng, 82% của phần chưa ghép được với chuyến
nào. Cửa tạo chuyến đặt cho chúng mã tạm KHOCU-… và bày ra ở bảng xem trước, nhưng không nhận
lại gì: có chỗ đọc mà không có chỗ ghi.

PHÉP THỬ QUAN TRỌNG NHẤT Ở ĐÂY là `test_chan_ma_trung_chuyen_dang_co`. Đặt trùng mã một chuyến
đã có thì cửa tạo chuyến bỏ qua (không tạo), rồi cửa nạp quyết toán treo toàn bộ dòng chi của tệp
này lên CHUYẾN CỦA NGƯỜI KHÁC — giá vốn chuyến ấy gấp đôi, lợi nhuận âm, mà mọi bảng vẫn cân vì
tổng nào cũng cộng từ dòng. Đúng kiểu hỏng đã đo được ngày 18/9/2026: 57 chuyến ghi dư 2,63 tỷ
suốt hai tuần không ai thấy.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_dat_ma.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dat_ma.db"):
    os.remove("test_dat_ma.db")

import pytest                                                    # noqa: E402
from app.db.session import SessionLocal, Base, engine            # noqa: E402
import app.models                                                # noqa: E402,F401
from app.models.core import Tour, User                           # noqa: E402
from app.models.kho_cu import KhoCuTepChuyen                     # noqa: E402
from app.services import dat_ma_kho_cu as DM                     # noqa: E402
from app.services import tao_chuyen_kho_cu as TC                 # noqa: E402

Base.metadata.create_all(engine)

TEP_EU = "QUYẾT TOÁN CHÂU ÂU 6 NƯỚC 22.07.2026 - 30.07.2026.xlsx"
MA_EU = "EU220726"


@pytest.fixture()
def db():
    s = SessionLocal()
    s.query(KhoCuTepChuyen).delete()
    s.query(Tour).delete()
    s.commit()
    yield s
    s.rollback()
    s.close()


def _chuyen(db, ma: str) -> Tour:
    u = db.query(User).first()
    if u is None:
        u = User(username="dh_dat_ma", full_name="ĐH", role="nv_dh", password_hash="x")
        db.add(u); db.flush()
    t = Tour(code=ma, name="CHUYẾN CŨ", tour_type="package", operator_id=u.id,
             start_date=date(2026, 7, 22), end_date=date(2026, 7, 30), planned_pax=45)
    db.add(t); db.commit()
    return t


def _cap(ten=TEP_EU, ma=MA_EU):
    return [{"ten_tep": ten, "ma_tour": ma}]


# ------------------------------------------------------------------ soát

def test_dat_duoc_ma_hop_le(db):
    k = DM.soat(db, _cap())
    assert k["dat_duoc"] == 1 and k["bi_chan"] == 0
    assert k["hang"][0]["chan"] == []


def test_chan_ma_trung_chuyen_dang_co(db):
    """Phép thử chính: mã trùng chuyến đã có phải bị CHẶN, không phải cảnh báo."""
    _chuyen(db, MA_EU)
    k = DM.soat(db, _cap())
    assert k["bi_chan"] == 1
    assert "CHUYẾN CỦA NGƯỜI KHÁC" in " ".join(k["hang"][0]["chan"])


def test_chan_ten_khach_gõ_vao_o_ma(db):
    """Kho cũ đã có 19 tệp gõ TÊN KHÁCH vào ô mã. Không nhận thêm cái nào."""
    k = DM.soat(db, _cap(ma="CÔNG TY DƯỢC"))
    assert k["bi_chan"] == 1


@pytest.mark.parametrize("ma", ["", "   ", "EU22", "A" * 40])
def test_chan_ma_khong_dung_dang(db, ma):
    assert DM.soat(db, _cap(ma=ma))["bi_chan"] == 1


def test_hai_tep_cung_ma_thi_phai_xac_nhan_chu_khong_chan(db):
    """Hai tệp cùng chuyến có thật (bảng chính + bảng land). Hỏi, không chặn."""
    k = DM.soat(db, [{"ten_tep": "A 01.01.2026.xlsx", "ma_tour": MA_EU},
                     {"ten_tep": "B 01.01.2026.xlsx", "ma_tour": MA_EU}])
    assert k["bi_chan"] == 0
    assert k["phai_xac_nhan"] == 2


# ------------------------------------------------------------------ ghi

def test_khong_xac_nhan_thi_khong_ghi_gi(db):
    DM.dat(db, _cap(), boi="chutich", xac_nhan=False)
    db.commit()
    assert db.query(KhoCuTepChuyen).count() == 0


def test_xac_nhan_thi_ghi_mot_dong(db):
    kq = DM.dat(db, _cap(), boi="chutich", xac_nhan=True)
    db.commit()
    assert kq["da_ghi"] == 1
    r = db.query(KhoCuTepChuyen).one()
    assert r.ma_tour == MA_EU and r.tour_id is None


def test_dat_lai_la_THAY_khong_de_dong_thu_hai(db):
    DM.dat(db, _cap(), boi="chutich", xac_nhan=True); db.commit()
    DM.dat(db, _cap(ma="EU230726"), boi="chutich", xac_nhan=True,
           ke_ca_phai_hoi=True); db.commit()
    assert db.query(KhoCuTepChuyen).count() == 1
    assert db.query(KhoCuTepChuyen).one().ma_tour == "EU230726"


def test_tep_da_sinh_ra_chuyen_thi_khong_doi_ma_o_day(db):
    t = _chuyen(db, "DA-CO-0726")
    db.add(KhoCuTepChuyen(khoa_tep=TC.khoa_tep(TEP_EU), ten_tep=TEP_EU,
                          ma_tour="DA-CO-0726", tour_id=t.id))
    db.commit()
    k = DM.soat(db, _cap())
    assert k["bi_chan"] == 1
    assert "đã sinh ra chuyến" in " ".join(k["hang"][0]["chan"])


def test_hai_tep_cung_ma_khong_ghi_neu_chua_xac_nhan_rieng(db):
    kq = DM.dat(db, [{"ten_tep": "A 01.01.2026.xlsx", "ma_tour": MA_EU},
                     {"ten_tep": "B 01.01.2026.xlsx", "ma_tour": MA_EU}],
                boi="chutich", xac_nhan=True)
    db.commit()
    assert kq["da_ghi"] == 0 and len(kq["bo"]) == 2


# ------------------------------------------------------------------ nối vào cửa tạo chuyến

def test_ma_nguoi_dat_chi_tra_tep_chua_sinh_chuyen(db):
    DM.dat(db, _cap(), boi="chutich", xac_nhan=True); db.commit()
    assert DM.ma_nguoi_dat(db) == {TC.khoa_tep(TEP_EU): MA_EU}
    db.query(KhoCuTepChuyen).one().tour_id = 999
    db.commit()
    assert DM.ma_nguoi_dat(db) == {}


def test_ma_nguoi_dat_thang_ma_tam_cua_may():
    d = {"ten_tep": TEP_EU, "ma_tour": "", "ngay_di": None}
    khong = TC.de_xuat(d, set())
    assert khong["ma_la_may_dat"] and khong["ma"].startswith(TC.TIEN_TO_TAM)
    co = TC.de_xuat(d, set(), None, {TC.khoa_tep(TEP_EU): MA_EU})
    assert co["ma"] == MA_EU and co["ma_la_nguoi_dat"] and not co["ma_la_may_dat"]


def test_ma_nguoi_dat_thang_ca_ma_ghi_trong_tep():
    """Người đặt đã qua bốn phép soát; mã trong tệp thì chưa. Để tệp thắng là làm cửa kia vô nghĩa."""
    d = {"ten_tep": TEP_EU, "ma_tour": "PT14012022", "ngay_di": None}
    co = TC.de_xuat(d, set(), None, {TC.khoa_tep(TEP_EU): MA_EU})
    assert co["ma"] == MA_EU


def test_ma_nguoi_dat_thang_ke_ca_khi_ma_trong_tep_khop_mot_chuyen_khac():
    """Đột phá hoại sống sót lần đầu vì phép thử trên truyền `ma_da_co` rỗng.

    Tệp khai 'PT14012022' — mã của bản mẫu Phan Thiết 2022, và VTOS CÓ chuyến mang mã ấy. Nếu
    nhánh 'đã có' chạy trước nhánh mã người đặt thì tệp này bị xếp 'da_co' và gắn vào đúng chuyến
    2022 — tức là 2,4 tỷ tour Châu Âu treo lên một chuyến Phan Thiết bốn năm trước.
    """
    d = {"ten_tep": TEP_EU, "ma_tour": "PT14012022", "ngay_di": None}
    co = TC.de_xuat(d, {"PT14012022"}, None, {TC.khoa_tep(TEP_EU): MA_EU})
    assert co["viec"] == "tao_moi" and co["ma"] == MA_EU


def test_dong_bi_chan_khong_duoc_ghi(db):
    """Đột phá hoại sống sót lần đầu: không phép thử nào canh việc dòng bị chặn vẫn bị ghi."""
    _chuyen(db, MA_EU)                      # làm cho mã bị chặn vì trùng chuyến đang có
    kq = DM.dat(db, _cap(), boi="chutich", xac_nhan=True, ke_ca_phai_hoi=True)
    db.commit()
    assert kq["da_ghi"] == 0
    assert db.query(KhoCuTepChuyen).count() == 0
