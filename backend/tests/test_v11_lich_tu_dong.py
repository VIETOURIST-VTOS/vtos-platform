"""V11 – Lịch tự động hóa. Phép thử quan trọng nhất ở đây là phép thử về CÁI KHÔNG XẢY RA.

Nghiệm thu V11 nói: "màn hình hiện đủ các tác vụ đang chạy và lần chạy gần nhất; tác vụ thất bại
sinh sự kiện kỹ thuật cho robot Kiểm soát đọc". Làm đúng từng chữ đó thì vẫn còn một lỗ hổng lớn:

    Một tác vụ NGỪNG CHẠY không sinh ra lần chạy nào, nên không sinh ra dòng thất bại nào, nên màn
    hình toàn xanh. Luồng n8n bị tắt, hết hạn thẻ đăng nhập, hay ai đó sửa lịch – ba ngày sau kế
    toán mới phát hiện sao kê chưa về. Im lặng là một trạng thái hỏng, và nó là sự VẮNG MẶT của
    một dòng chứ không phải sự có mặt của một dòng.

Nên bộ kiểm này canh cả hai chiều:

  T1 khai tác vụ rồi n8n báo về – đường thông
  T2 cùng mã lần gửi hai lần KHÔNG thành hai dòng (n8n thử lại khi mạng chập)
  T3 báo về cho tác vụ CHƯA KHAI thì bị từ chối, không tự tạo tác vụ lạ
  T4 thất bại sinh sự kiện kỹ thuật cho robot Kiểm soát (K6)
  T5 ★ TÁC VỤ IM LẶNG bị phát hiện – dù không có một dòng lỗi nào
  T6 tác vụ đã TẮT thì im lặng là đúng, không kêu
  T7 để hạn = 0 thì không canh im lặng – và màn hình phải nói ra điều đó
  T8 số bản ghi RỖNG khác số bản ghi 0
  T9 thất bại rồi im luôn thì hiện IM LẶNG, không hiện 'lần gần nhất thất bại'
  T10 tắt mà không ghi lý do thì bị chặn
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v11.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
os.environ["ROBOT_TOKEN"] = "thu-robot-v11"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

client = TestClient(app)
ROBOT = {"X-Robot-Token": "thu-robot-v11"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        assert u is not None, f"dữ liệu mẫu không có vai trò {vai}"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def khai(ma, **kw):
    than = {"ma": ma, "ten": kw.pop("ten", f"Tác vụ {ma}"), **kw}
    return client.post("/api/v1/tu-dong/tac-vu", headers=login("cntt"), json=than)


def bao(ma_tac_vu, ma_lan, trang_thai, **kw):
    return client.post("/api/v1/tu-dong/bao-cao", headers=ROBOT,
                       json={"ma_tac_vu": ma_tac_vu, "ma_lan": ma_lan,
                             "trang_thai": trang_thai, **kw})


def mot(ma):
    d = client.get("/api/v1/tu-dong", headers=login("ketoan")).json()
    return next(t for t in d["tac_vu"] if t["ma"] == ma)


# ------------------------------------------------------------------ T1
def test_khai_roi_bao_ve_thi_man_hinh_thay_lan_chay():
    assert khai("t1_sao_ke", han_toi_da_phut=1440, lich_doc="mỗi ngày 06:00").status_code == 201
    t = mot("t1_sao_ke")
    assert t["trang_thai"]["ma"] == "chua_chay"

    bd = datetime.now() - timedelta(minutes=3)
    r = bao("t1_sao_ke", "exec-1", "thanh_cong", bat_dau=bd.isoformat(),
            ket_thuc=datetime.now().isoformat(), so_ban_ghi=45)
    assert r.status_code == 201, r.text
    assert r.json()["moi"] is True

    t = mot("t1_sao_ke")
    assert t["trang_thai"]["ma"] == "binh_thuong"
    assert t["trang_thai"]["lan_cuoi"]["so_ban_ghi"] == 45
    assert t["trang_thai"]["lan_cuoi"]["giay"] > 100      # ~180 giây


# ------------------------------------------------------------------ T2
def test_cung_ma_lan_gui_hai_lan_khong_thanh_hai_dong():
    """n8n thử lại khi mạng chập. Một lần chạy đếm thành hai làm hỏng đúng con số mà màn hình này
    sinh ra để cho người ta tin."""
    khai("t2_lap", han_toi_da_phut=0)
    bao("t2_lap", "exec-lap", "dang_chay")
    r = bao("t2_lap", "exec-lap", "thanh_cong", ket_thuc=datetime.now().isoformat(), so_ban_ghi=7)
    assert r.status_code == 201 and r.json()["moi"] is False

    tid = mot("t2_lap")["id"]
    lc = client.get(f"/api/v1/tu-dong/tac-vu/{tid}/lan-chay", headers=login("cntt")).json()["lan_chay"]
    assert len(lc) == 1, f"một lần chạy thành {len(lc)} dòng"
    assert lc[0]["trang_thai"] == "thanh_cong" and lc[0]["so_ban_ghi"] == 7


# ------------------------------------------------------------------ T3
def test_bao_ve_cho_tac_vu_chua_khai_thi_bi_tu_choi():
    """KHÔNG tự tạo tác vụ. Máy tự tạo thì bảng khai báo thành bản sao của sổ lần chạy, và mất luôn
    khả năng phát hiện im lặng – vì một luồng bị xóa sẽ biến mất khỏi màn hình cùng lịch sử của nó."""
    r = bao("t3_khong_co_that", "exec-x", "thanh_cong")
    assert r.status_code == 422
    assert "Chưa khai báo" in str(r.json())
    d = client.get("/api/v1/tu-dong", headers=login("ketoan")).json()
    assert not any(t["ma"] == "t3_khong_co_that" for t in d["tac_vu"])


# ------------------------------------------------------------------ T4
def test_that_bai_sinh_su_kien_ky_thuat_cho_robot_kiem_soat():
    from app.db.session import SessionLocal
    from app.models.ky_thuat import SuKienKyThuat
    khai("t4_hong", han_toi_da_phut=0, quan_trong=True)
    assert bao("t4_hong", "exec-hong", "that_bai",
               thong_bao="Ngân hàng từ chối đăng nhập").status_code == 201
    with SessionLocal() as db:
        ds = db.execute(select(SuKienKyThuat)
                        .where(SuKienKyThuat.duong_dan == "tac-vu/t4_hong")).scalars().all()
    assert ds, "thất bại không sinh sự kiện kỹ thuật – robot Kiểm soát sẽ không thấy gì"
    assert ds[0].loai == "tac_vu_nen"
    assert ds[0].muc == "do", "tác vụ quan trọng thất bại phải là mức ĐỎ"


# ------------------------------------------------------------------ T5 ★
def test_TAC_VU_IM_LANG_bi_phat_hien_du_khong_co_mot_dong_loi_nao():
    """Phép thử quan trọng nhất của V11.

    Tác vụ chạy thành công hai ngày trước rồi thôi. Không có lần chạy thất bại, không có sự kiện lỗi,
    sổ lần chạy sạch bong. Nếu màn hình chỉ đọc dòng cuối thì nó báo 'bình thường' – và đó chính là
    cái bẫy: hệ thống nói ổn trong khi sao kê đã hai ngày không về.
    """
    khai("t5_im", han_toi_da_phut=1440, ten="Tác vụ đã ngừng chạy")   # lẽ ra chạy mỗi ngày
    hai_ngay_truoc = datetime.now() - timedelta(days=2)
    assert bao("t5_im", "exec-cu", "thanh_cong",
               bat_dau=hai_ngay_truoc.isoformat(),
               ket_thuc=(hai_ngay_truoc + timedelta(minutes=2)).isoformat(),
               so_ban_ghi=30).status_code == 201

    t = mot("t5_im")
    assert t["trang_thai"]["lan_cuoi"]["trang_thai"] == "thanh_cong", "lần chạy cuối vẫn là thành công"
    assert t["trang_thai"]["ma"] == "im_lang", \
        f"tác vụ ngừng chạy hai ngày mà màn hình báo '{t['trang_thai']['ten']}'"
    assert "quá hạn" in t["trang_thai"]["vi_sao"]

    im = client.get("/api/v1/tu-dong/im-lang", headers=login("ketoan")).json()["tac_vu"]
    assert any(x["ma"] == "t5_im" for x in im)


def test_quet_im_lang_day_len_su_kien_ky_thuat():
    from app.db.session import SessionLocal
    from app.models.ky_thuat import SuKienKyThuat
    r = client.post("/api/v1/tu-dong/quet-im-lang", headers=ROBOT)
    assert r.status_code == 200 and r.json()["so_tac_vu_im"] >= 1
    with SessionLocal() as db:
        ds = db.execute(select(SuKienKyThuat)
                        .where(SuKienKyThuat.duong_dan == "tac-vu/t5_im")).scalars().all()
    assert ds, "quét xong mà robot Kiểm soát vẫn không thấy tác vụ im lặng"


def test_quet_im_lang_khong_chay_khi_chi_MO_man_hinh():
    """Hàm đọc mà lại ghi thì mở màn hình mười lần đếm thành mười sự kiện."""
    from app.db.session import SessionLocal
    from app.models.ky_thuat import SuKienKyThuat
    with SessionLocal() as db:
        truoc = db.execute(select(SuKienKyThuat)
                           .where(SuKienKyThuat.duong_dan == "tac-vu/t5_im")).scalars().first().so_lan
    for _ in range(3):
        client.get("/api/v1/tu-dong", headers=login("ketoan"))
    with SessionLocal() as db:
        sau = db.execute(select(SuKienKyThuat)
                         .where(SuKienKyThuat.duong_dan == "tac-vu/t5_im")).scalars().first().so_lan
    assert sau == truoc, "mở màn hình đã ghi thêm sự kiện – hàm đọc đang ghi"


# ------------------------------------------------------------------ T6
def test_tac_vu_da_tat_thi_im_lang_la_dung_khong_keu():
    khai("t6_tat", han_toi_da_phut=60)
    tid = mot("t6_tat")["id"]
    r = client.put(f"/api/v1/tu-dong/tac-vu/{tid}", headers=login("cntt"), json={
        "ma": "t6_tat", "ten": "Tác vụ tắt có chủ ý", "han_toi_da_phut": 60,
        "bat": False, "ly_do_tat": "Ngưng đối chiếu kênh này từ tháng 9, chờ hợp đồng mới"})
    assert r.status_code == 200, r.text
    t = mot("t6_tat")
    assert t["trang_thai"]["ma"] == "tat"
    im = client.get("/api/v1/tu-dong/im-lang", headers=login("ketoan")).json()["tac_vu"]
    assert not any(x["ma"] == "t6_tat" for x in im), "tác vụ tắt có chủ ý không được kêu quá hạn"


# ------------------------------------------------------------------ T10
def test_tat_ma_khong_ghi_ly_do_thi_bi_chan():
    """Tác vụ bị tắt và tác vụ bị quên trông giống hệt nhau nếu không có lý do – mà hai cái đó cần
    hai cách xử lý ngược nhau."""
    khai("t10_tat_kho", han_toi_da_phut=60)
    tid = mot("t10_tat_kho")["id"]
    r = client.put(f"/api/v1/tu-dong/tac-vu/{tid}", headers=login("cntt"), json={
        "ma": "t10_tat_kho", "ten": "x", "han_toi_da_phut": 60, "bat": False, "ly_do_tat": "  "})
    assert r.status_code == 422 and "lý do" in str(r.json())


# ------------------------------------------------------------------ T7
def test_han_bang_0_thi_khong_canh_im_lang_va_man_hinh_noi_ra():
    khai("t7_theo_su_kien", han_toi_da_phut=0)
    bao("t7_theo_su_kien", "exec-cu-lam", "thanh_cong",
        bat_dau=(datetime.now() - timedelta(days=30)).isoformat(),
        ket_thuc=(datetime.now() - timedelta(days=30)).isoformat())
    t = mot("t7_theo_su_kien")
    assert t["trang_thai"]["ma"] == "binh_thuong"
    assert t["trang_thai"]["canh_im_lang"] is False, "màn hình phải nói ra là tác vụ này KHÔNG được canh"


# ------------------------------------------------------------------ T8
def test_so_ban_ghi_RONG_khac_so_ban_ghi_0():
    """Rỗng = 'không đếm được'. 0 = 'chạy xong, không có gì để làm'. Gộp hai cái làm một là mất đúng
    thông tin cần để biết tác vụ có thật sự làm việc hay không."""
    khai("t8_dem", han_toi_da_phut=0)
    bao("t8_dem", "exec-khong-dem", "thanh_cong")                    # không gửi so_ban_ghi
    bao("t8_dem", "exec-khong-co-gi", "thanh_cong", so_ban_ghi=0)
    tid = mot("t8_dem")["id"]
    lc = {l["ma_lan"]: l["so_ban_ghi"]
          for l in client.get(f"/api/v1/tu-dong/tac-vu/{tid}/lan-chay",
                              headers=login("cntt")).json()["lan_chay"]}
    assert lc["exec-khong-dem"] is None
    assert lc["exec-khong-co-gi"] == 0


# ------------------------------------------------------------------ T9
def test_that_bai_roi_im_luon_thi_hien_IM_LANG_chu_khong_hien_that_bai():
    """Thứ tự xét quan trọng: một tác vụ thất bại lúc 6h sáng rồi im ba ngày sẽ mãi hiện 'lần gần
    nhất thất bại' – đúng chữ nhưng che mất chuyện lớn hơn nhiều là nó đã ngừng chạy."""
    khai("t9_hong_roi_im", han_toi_da_phut=60)
    ba_ngay = datetime.now() - timedelta(days=3)
    bao("t9_hong_roi_im", "exec-hong-cu", "that_bai", bat_dau=ba_ngay.isoformat(),
        thong_bao="lỗi đăng nhập")
    t = mot("t9_hong_roi_im")
    assert t["trang_thai"]["ma"] == "im_lang", \
        f"đang hiện '{t['trang_thai']['ten']}' – che mất chuyện nó đã ngừng chạy"


# ------------------------------------------------------------------ Quyền
def test_bao_cao_khong_co_token_robot_thi_bi_chan():
    r = client.post("/api/v1/tu-dong/bao-cao",
                    json={"ma_tac_vu": "t1_sao_ke", "ma_lan": "exec-lau", "trang_thai": "thanh_cong"})
    assert r.status_code == 401


def test_nhan_vien_nghiep_vu_xem_duoc_nhung_khong_khai_duoc():
    assert client.get("/api/v1/tu-dong", headers=login("ketoan")).status_code == 200
    r = client.post("/api/v1/tu-dong/tac-vu", headers=login("ketoan"),
                    json={"ma": "ke_toan_tu_khai", "ten": "x"})
    assert r.status_code == 403
