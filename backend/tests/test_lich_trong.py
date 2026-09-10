"""Lịch chạy bên trong VTOS – phép thử tập trung vào chỗ đếm phút làm SAI.

Bối cảnh 09/9/2026: mở n8n ra kiểm thì workspace TRỐNG, 0 lần chạy. Bốn việc lẽ ra chạy theo lịch
chưa bao giờ chạy. Chủ tịch quyết đưa vào trong VTOS.

Vòng lặp robot sẵn có đếm phút từ lúc máy chủ khởi động. Cách đó hỏng ở đúng hai chỗ, và cả hai chỗ
đều hỏng LẶNG LẼ – việc không chạy thì không sinh ra dòng nào để ai đó nhìn thấy:

  L1 khóa theo kỳ: cùng một kỳ gọi mười lần vẫn chỉ chạy một lần
  L2 ★ máy chủ tắt lúc tới giờ, lên lại muộn thì việc VẪN CHẠY BÙ – không bị bỏ luôn
  L3 mã kỳ mỗi 30 phút rơi đúng mốc tròn, không trôi theo lúc khởi động
  L4 chưa tới giờ thì không chạy sớm
  L5 báo cáo tuần không làm bù sang ngày khác (số liệu đã khác, người đọc hiểu nhầm kỳ)
  L6 một việc hỏng không làm chết việc còn lại, và hỏng thì ghi lần chạy thất bại
  L7 việc người đã TẮT thì khởi động lại không bật lại hộ
  L8 các việc trong lịch tự hiện trên màn hình V11
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_lt.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
os.environ["ROBOT_TOKEN"] = "thu-lt"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import datetime
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.services import lich_trong as LT
from app.models.tu_dong import TacVuTuDong, LanChayTacVu


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _dem(ma):
    with SessionLocal() as db:
        t = db.execute(select(TacVuTuDong).where(TacVuTuDong.ma == ma)).scalars().first()
        if t is None: return 0
        return len(db.execute(select(LanChayTacVu)
                              .where(LanChayTacVu.tac_vu_id == t.id)).scalars().all())


def _thay(ma, ham, **kw):
    """Thay hàm chạy của một việc trong bản khai, để phép thử không gọi ra ngoài internet."""
    d = LT.THEO_MA[ma]
    cu = d["chay"]; d["chay"] = ham
    d.update(kw)
    return cu


# ------------------------------------------------------------------ L1
def test_cung_mot_ky_goi_muoi_lan_van_chi_chay_mot_lan():
    chay = {"n": 0}
    def ham(db):
        chay["n"] += 1
        return chay["n"], "thử"
    cu = _thay("vtos_bao_cao_ngay", ham)
    try:
        toi = datetime(2026, 9, 9, 21, 0)
        for _ in range(10):
            with SessionLocal() as db:
                LT.den_luot(db, toi)
        assert chay["n"] == 1, f"chạy {chay['n']} lần trong cùng một kỳ"
        assert _dem("vtos_bao_cao_ngay") == 1
    finally:
        LT.THEO_MA["vtos_bao_cao_ngay"]["chay"] = cu


# ------------------------------------------------------------------ L2 ★
def test_may_chu_tat_luc_toi_gio_len_lai_muon_thi_VAN_CHAY_BU():
    """Phép thử quan trọng nhất.

    Đếm phút từ lúc khởi động: máy chủ lên lại lúc 21:10 thì bộ đếm về 0, mốc 20:30 hôm đó đã trôi
    qua và không bao giờ chạy – báo cáo ngày hôm ấy mất, không ai biết. Khóa theo mã kỳ thì mã của
    ngày hôm đó chưa dùng, nên việc được làm bù.
    """
    chay = {"n": 0}
    def ham(db):
        chay["n"] += 1
        return None, "bù"
    cu = _thay("vtos_bao_cao_tuan", ham)
    try:
        # Thứ Bảy 12/9/2026, lịch 17:00. Máy chủ vừa lên lúc 19:45 – đã trễ gần 3 tiếng.
        muon = datetime(2026, 9, 12, 19, 45)
        assert muon.weekday() == 5
        with SessionLocal() as db:
            LT.den_luot(db, muon)
        assert chay["n"] == 1, "việc bị lỡ đã bị bỏ luôn thay vì làm bù"
    finally:
        LT.THEO_MA["vtos_bao_cao_tuan"]["chay"] = cu


# ------------------------------------------------------------------ L3
def test_ma_ky_moi_30_phut_roi_dung_moc_tron():
    d = LT.THEO_MA["vtos_sepay_bu"]
    assert LT.ma_ky(d, datetime(2026, 9, 9, 14, 3)) == "vtos_sepay_bu:2026-09-09T14:00"
    assert LT.ma_ky(d, datetime(2026, 9, 9, 14, 29)) == "vtos_sepay_bu:2026-09-09T14:00"
    assert LT.ma_ky(d, datetime(2026, 9, 9, 14, 30)) == "vtos_sepay_bu:2026-09-09T14:30"
    assert LT.ma_ky(d, datetime(2026, 9, 9, 14, 59)) == "vtos_sepay_bu:2026-09-09T14:30"


# ------------------------------------------------------------------ L4
def test_chua_toi_gio_thi_khong_chay_som():
    d = LT.THEO_MA["vtos_bao_cao_ngay"]           # 20:30
    assert LT.ma_ky(d, datetime(2026, 9, 10, 20, 29)) is None
    assert LT.ma_ky(d, datetime(2026, 9, 10, 20, 30)) is not None


# ------------------------------------------------------------------ L5
def test_bao_cao_tuan_khong_lam_bu_sang_ngay_khac():
    """Một báo cáo tuần gửi vào Chủ nhật thì số liệu đã khác, và người nhận đọc nó như báo cáo của
    tuần mới. Làm bù trong NGÀY thì được, sang ngày khác thì không."""
    d = LT.THEO_MA["vtos_bao_cao_tuan"]
    assert LT.ma_ky(d, datetime(2026, 9, 12, 23, 59)) is not None    # thứ Bảy muộn – vẫn chạy
    assert LT.ma_ky(d, datetime(2026, 9, 13, 9, 0)) is None          # Chủ nhật – thôi


def test_bao_cao_thang_chi_chay_dung_ngay_10():
    d = LT.THEO_MA["vtos_bao_cao_thang"]
    assert LT.ma_ky(d, datetime(2026, 9, 10, 9, 0)) == "vtos_bao_cao_thang:2026-09"
    assert LT.ma_ky(d, datetime(2026, 9, 11, 9, 0)) is None


# ------------------------------------------------------------------ L6
def test_mot_viec_hong_khong_lam_chet_viec_con_lai_va_co_ghi_lai():
    def no(db):
        raise RuntimeError("giả vờ hỏng")
    lanh = {"n": 0}
    def ok(db):
        lanh["n"] += 1
        return 0, "ổn"
    cu1 = _thay("vtos_zalo_gui_cho", no)
    cu2 = _thay("vtos_quet_im_lang", ok)
    try:
        toi = datetime(2026, 9, 20, 8, 0)
        with SessionLocal() as db:
            LT.den_luot(db, toi)
        assert lanh["n"] == 1, "một việc hỏng đã làm chết việc sau nó"
        with SessionLocal() as db:
            t = db.execute(select(TacVuTuDong)
                           .where(TacVuTuDong.ma == "vtos_zalo_gui_cho")).scalars().first()
            l = db.execute(select(LanChayTacVu).where(LanChayTacVu.tac_vu_id == t.id)
                           .order_by(LanChayTacVu.id.desc())).scalars().first()
        assert l is not None and l.trang_thai == "that_bai"
        assert "giả vờ hỏng" in l.thong_bao
    finally:
        LT.THEO_MA["vtos_zalo_gui_cho"]["chay"] = cu1
        LT.THEO_MA["vtos_quet_im_lang"]["chay"] = cu2


# ------------------------------------------------------------------ L7
def test_viec_nguoi_da_TAT_thi_khoi_dong_lai_khong_bat_lai_ho():
    """Tắt một việc là quyết định của người. Mã nguồn khai lại mô tả thì được, bật lại thì không –
    nếu không thì mỗi lần deploy là một lần cãi lại quyết định của người dùng."""
    with SessionLocal() as db:
        t = db.execute(select(TacVuTuDong)
                       .where(TacVuTuDong.ma == "vtos_bao_cao_thang")).scalars().first()
        t.bat = False; t.ly_do_tat = "chưa dùng báo cáo tháng"; db.commit()
    with SessionLocal() as db:
        LT.dam_bao_khai_bao(db)
    with SessionLocal() as db:
        t = db.execute(select(TacVuTuDong)
                       .where(TacVuTuDong.ma == "vtos_bao_cao_thang")).scalars().first()
        assert t.bat is False, "khởi động lại đã bật lại việc người đã tắt"
        assert t.ly_do_tat == "chưa dùng báo cáo tháng"

    # và đã tắt thì không chạy nữa
    chay = {"n": 0}
    def ham(db):
        chay["n"] += 1
        return None, ""
    cu = _thay("vtos_bao_cao_thang", ham)
    try:
        with SessionLocal() as db:
            LT.den_luot(db, datetime(2026, 10, 10, 9, 0))
        assert chay["n"] == 0
    finally:
        LT.THEO_MA["vtos_bao_cao_thang"]["chay"] = cu


# ------------------------------------------------------------------ L8
def test_cac_viec_trong_lich_hien_tren_man_hinh_V11():
    """Việc chạy trong VTOS và việc chạy ở n8n phải nhìn thấy ở CÙNG MỘT CHỖ – một màn hình, một
    cách phát hiện im lặng. Hai chỗ nhìn thì luôn có một chỗ không ai mở."""
    with SessionLocal() as db:
        ds = {t.ma: t for t in db.execute(select(TacVuTuDong)).scalars()}
    for d in LT.LICH:
        assert d["ma"] in ds, f"việc {d['ma']} không có trong bảng tác vụ"
        assert ds[d["ma"]].he_thong == "vtos"
        assert ds[d["ma"]].lich_doc, "phải có lịch viết bằng chữ cho người đọc"
        # Mọi việc theo lịch đều phải canh im lặng: để 0 là mở lại đúng lỗ hổng vừa bịt.
        assert ds[d["ma"]].han_toi_da_phut > 0, f"{d['ma']} không canh im lặng"
