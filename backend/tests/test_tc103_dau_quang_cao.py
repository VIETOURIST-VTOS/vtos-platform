"""TC-103 · Dấu nguồn quảng cáo – bắt được cái chạm trước khi nó mất.

VÌ SAO CÓ TỆP NÀY. Báo cáo Marketing tháng 9/2026 đo được 719/931 booking; 212 booking và
5.484.557.709 đ – 39,5% doanh thu tháng – không gắn được kênh nào. Mã click của nền tảng chỉ
tồn tại đúng giây khách bấm quảng cáo, nên chỗ mù ấy không vá được bằng cách đọc lại sổ cũ: phải
bắt lấy từ bây giờ. Những phép thử dưới đây giữ cho cái cửa bắt ấy không hỏng lặng lẽ.

  Q1  một lần chạm ghi được, và KHÔNG tự đẻ ra lead
  Q2  webhook gửi lại cùng một sự kiện thì không nhân đôi, và không làm nghèo bản ghi cũ
  Q3  hai cuộc gọi KHÔNG MÃ của cùng một số, khác phút, là HAI dòng
  Q4  dấu ghi trước – lead lập sau – lượt quét lại ghép được
  Q5  cửa nhận đứng sau khoá máy chủ, không phải cửa công khai
  Q6  một dòng hỏng không làm hỏng cả gói
  Q7  thời điểm chạm ở tương lai bị từ chối
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_tc103.db"; os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"; os.environ["ROBOT_TOKEN"] = "robot-tc103"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for f in ("test_tc103.db", "test_tc103.db-journal"):
    if os.path.exists(f): os.remove(f)

from datetime import datetime, timedelta           # noqa: E402
import pytest                                      # noqa: E402
from fastapi.testclient import TestClient          # noqa: E402
from app.main import app                           # noqa: E402

client = TestClient(app)
KHOA = {"X-Robot-Token": "robot-tc103"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


def _lead(phone: str, uid: str = ""):
    from app.models.crm import Lead
    db = _db()
    try:
        l = Lead(phone=phone, name="Khach thu", channel="Hotline 1",
                 lead_month=f"{datetime.now():%Y-%m}", zalo_uid=uid, created_by="phepthu")
        db.add(l); db.commit(); db.refresh(l)
        return l.id
    finally:
        db.close()


def _nhan(dau: list[dict]):
    return client.post("/api/v1/dau-quang-cao/nhan", json={"dau": dau}, headers=KHOA)


def test_q1_ghi_duoc_mot_lan_cham_va_khong_tu_de_ra_lead():
    """Dấu quảng cáo là bằng chứng ai đó bấm một mẫu quảng cáo – chưa đủ để nói đã có khách.

    Cho cửa này tạo lead là mở đường thứ năm vào bảng `leads`, bên cạnh cửa nạp, nút nhập Excel
    cũ, nút nhập tay và webhook Zalo – và đường thứ năm ấy không đi qua bộ kiểm nào.
    """
    from app.models.crm import Lead
    db = _db()
    try:
        truoc = db.query(Lead).count()
    finally:
        db.close()
    r = _nhan([{"nen_tang": "google", "loai_ma": "gclid", "ma": "Cj0KCQtc103",
                "sdt": "0901234567", "nguon_ghi": "web",
                "utm": {"utm_source": "google", "utm_campaign": "dalat-t10"},
                "trang_dich": "https://vietourist.com.vn/tour/da-lat",
                "cham_luc": "2026-10-06 09:20:00"}])
    assert r.status_code == 201, r.text
    assert r.json()["moi"] == 1 and not r.json()["loi"]
    db = _db()
    try:
        assert db.query(Lead).count() == truoc, (
            "Cửa dấu quảng cáo KHÔNG được tạo lead. Dấu chưa khớp được lead thì nằm chờ, và số "
            "dòng chờ chính là con số đo được việc ghép có chạy hay không.")
    finally:
        db.close()


def test_q2_gui_lai_cung_su_kien_thi_khong_nhan_doi_va_khong_lam_ngheo_ban_ghi():
    """Webhook gửi lại thường mang ÍT thông tin hơn lần đầu. Ghi đè là tự làm nghèo sổ của mình."""
    d = {"nen_tang": "facebook", "loai_ma": "leadgen_id", "ma": "lg-tc103-777",
         "ma_mau_qc": "ad-888", "ten_chien_dich": "Deal Hot T10", "sdt": "0912345678",
         "cham_luc": "2026-10-06 10:00:00", "nguon_ghi": "webhook_fb"}
    assert _nhan([d]).json()["moi"] == 1
    lai = _nhan([{"nen_tang": "facebook", "loai_ma": "leadgen_id", "ma": "lg-tc103-777"}]).json()
    assert lai["moi"] == 0 and lai["da_co"] == 1, "gửi lại cùng mã phải không sinh dòng mới"
    ds = client.get("/api/v1/dau-quang-cao?nen_tang=facebook",
                    headers=_dn("ptgd_mkt")).json()
    hang = [x for x in ds if x["ma"] == "lg-tc103-777"]
    assert len(hang) == 1
    assert hang[0]["ma_mau_qc"] == "ad-888" and hang[0]["ten_chien_dich"] == "Deal Hot T10", (
        "lần gửi lại nghèo thông tin hơn đã xoá mất nội dung của lần đầu")


def test_q3_hai_cuoc_goi_khong_ma_khac_phut_la_hai_dong():
    """Hotline là kênh doanh thu lớn thứ hai (tháng 9: 51 booking, 1,826 tỷ) và cuộc gọi thường
    KHÔNG có mã nào. Một ràng buộc duy nhất trên (nền tảng, loại mã, mã) sẽ cho đúng một dòng
    không mã cho mỗi nền tảng, tức là chặn chính cuộc gọi thứ hai."""
    g = {"nen_tang": "tong_dai", "loai_ma": "so_chuyen_tiep", "sdt": "0987654321",
         "nguon_ghi": "tong_dai"}
    a = _nhan([{**g, "cham_luc": "2026-10-06 08:15:00"}]).json()
    b = _nhan([{**g, "cham_luc": "2026-10-06 14:40:00"}]).json()
    lai = _nhan([{**g, "cham_luc": "2026-10-06 08:15:30"}]).json()
    assert a["moi"] == 1 and b["moi"] == 1, "hai cuộc gọi khác phút phải là hai dòng"
    assert lai["moi"] == 0, "cùng một cuộc gọi lệch vài giây phải gộp, không đếm thành cuộc thứ ba"


def test_q4_dau_ghi_truoc_lead_lap_sau_thi_luot_quet_lai_ghep_duoc():
    """Khách bấm quảng cáo lúc 9 giờ, 11 giờ mới gọi và Sales mới lập lead. Lúc ghi dấu chưa có
    gì để khớp – nên phải có một lượt quét lại, nếu không dấu nằm mồ côi mãi."""
    sdt = "0933777111"
    assert _nhan([{"nen_tang": "tiktok", "loai_ma": "ttclid", "ma": "tt-tc103-1",
                   "sdt": sdt, "cham_luc": "2026-10-06 09:00:00"}]).json()["moi"] == 1
    chua = client.get("/api/v1/dau-quang-cao?chua_ghep=1", headers=_dn("ptgd_mkt")).json()
    assert any(x["ma"] == "tt-tc103-1" for x in chua), "dấu chưa có lead phải nằm trong danh sách chờ"
    lid = _lead(sdt)
    assert client.post("/api/v1/dau-quang-cao/ghep-lead", headers=KHOA).json()["da_ghep"] >= 1
    ds = client.get(f"/api/v1/dau-quang-cao?sdt={sdt}", headers=_dn("ptgd_mkt")).json()
    assert ds and ds[0]["lead_id"] == lid


def test_q5_cua_nhan_dung_sau_khoa_may_chu_khong_phai_cua_cong_khai():
    """Toàn kho có ĐÚNG MỘT cửa không cần đăng nhập – trang khách chấm điểm sau tour. Cửa này
    không được là cái thứ hai: dấu giả bơm vào sẽ được đẩy ngược lên Google và Facebook như
    chuyển đổi thật, tức là tự dạy nền tảng tối ưu sai rồi trả tiền cho nó."""
    r = client.post("/api/v1/dau-quang-cao/nhan",
                    json={"dau": [{"nen_tang": "google", "loai_ma": "gclid", "ma": "gia-mao"}]})
    assert r.status_code == 401, "cửa nhận phải đòi khoá máy chủ"
    assert client.post("/api/v1/dau-quang-cao/ghep-lead").status_code == 401


def test_q6_mot_dong_hong_khong_lam_hong_ca_goi():
    """Khác cửa nạp tệp, nơi người nhập ngồi trước màn hình và sửa được. Ở đây đầu kia là một máy
    chủ đang gửi sự kiện thời gian thực: từ chối cả gói vì một dòng sai múi giờ là vứt đi những
    dấu đúng mà không bao giờ lấy lại được."""
    mai = datetime.now() + timedelta(days=1)
    r = _nhan([{"nen_tang": "zalo", "loai_ma": "zalo_uid", "ma": "uid-tc103-ok"},
               {"nen_tang": "zalo", "loai_ma": "zalo_uid", "ma": "uid-tc103-xau",
                "cham_luc": f"{mai:%Y-%m-%d %H:%M:%S}"},
               {"nen_tang": "zalo", "loai_ma": "zalo_uid", "ma": "uid-tc103-ok2"}]).json()
    assert r["moi"] == 2, "hai dòng đúng phải vào được"
    assert len(r["loi"]) == 1 and r["loi"][0]["dong"] == 1, "dòng hỏng phải trả về kèm chỉ số"


def test_q7_thoi_diem_cham_o_tuong_lai_bi_tu_choi():
    """Giờ ở tương lai là dấu hiệu đồng hồ nguồn sai hoặc múi giờ chưa quy đổi. Nhận vào thì mọi
    phép đếm theo kỳ lệch, và Google từ chối chuyển đổi có giờ sau giờ gửi."""
    from app.services import dau_quang_cao as DQ
    db = _db()
    try:
        with pytest.raises(ValueError, match="tương lai"):
            DQ.ghi(db, {"nen_tang": "google", "loai_ma": "gclid", "ma": "mai-moi-co",
                        "cham_luc": datetime.now() + timedelta(hours=5)})
    finally:
        db.rollback(); db.close()


def test_q8_bang_do_de_rong_khi_chua_co_gi_thay_vi_ghi_khong():
    """Bất biến của kho: RỖNG KHÁC KHÔNG. Tỷ lệ ghép 0% đọc là 'ghép mà không ra', còn chưa có
    dấu nào đọc là 'chưa đo'. Hai câu khác hẳn nhau."""
    from app.services import dau_quang_cao as DQ
    db = _db()
    try:
        b = DQ.bang_do(db)
    finally:
        db.close()
    assert set(b) >= {"tong", "da_ghep_lead", "chua_ghep", "ty_le_ghep", "theo_nen_tang"}
    assert b["tong"] == b["da_ghep_lead"] + b["chua_ghep"]
    if b["tong"] == 0:
        assert b["ty_le_ghep"] is None


_TOK: dict = {}


def _dn(u: str):
    """Đăng nhập. Bộ dữ liệu thử của tệp này tắt seed nên tạo thẳng một tài khoản."""
    if u not in _TOK:
        from app.models.core import User
        from app.core.security import hash_password
        db = _db()
        try:
            if not db.query(User).filter(User.username == u).first():
                db.add(User(username=u, full_name=u, role=u,
                            password_hash=hash_password("Vtos@Demo#2026"), active=True))
                db.commit()
        finally:
            db.close()
        _TOK[u] = client.post("/api/v1/auth/login",
                              data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {_TOK[u]}"}
