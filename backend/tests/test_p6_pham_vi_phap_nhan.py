"""P6 – phạm vi pháp nhân theo phiên đăng nhập.

Ba điều phải giữ, và chúng kéo ngược nhau nên phải viết ra thành phép thử chứ không giữ bằng trí nhớ:

1. Người của pháp nhân A KHÔNG thấy hồ sơ của pháp nhân B.
2. Hồ sơ CHƯA XÁC ĐỊNH pháp nhân vẫn thấy được, có nhãn – nhưng KHÔNG bao giờ được cộng vào con số
   của pháp nhân A. Đây là điều duy nhất trong P6 mà một lần làm sai thì không sửa lại được: khi một
   khoản đã trôi vào báo cáo của công ty khác thì không còn dấu vết nào nói rằng nó từng "chưa biết".
3. Tài khoản chưa được gán pháp nhân KHÔNG bị khoá ra khỏi hệ thống. Cột users.company_id mới thêm
   ngày 07/9/2026 và chưa có bước điền sẵn; bật lọc cứng là cả công ty đứng lại trong một buổi sáng.
   Nhưng nó cũng không được im lặng – /auth/me phải nói thẳng ra rằng phiên này chưa bị giới hạn.

Phép thử số 2 là phép thử quan trọng nhất tệp này. Nếu ai đó về sau thêm một khoá "tong" vào dem()
cho tiện giao diện, phép thử đó phải đỏ.
"""
import os, sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_p6_phapnhan.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p6_phapnhan.db", "test_p6_phapnhan.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, Company, Tour
from app.services import pham_vi_phap_nhan as PV

client = TestClient(app)
MK = "phapnhan123"
ID = {}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for ma, ten, loai in (("PN_A", "Công ty thử A", "me"), ("PN_B", "Công ty thử B", "con")):
            if db.execute(select(Company).where(Company.code == ma)).scalars().first() is None:
                db.add(Company(code=ma, name=ten, kind=loai))
        db.commit()
        a = db.execute(select(Company).where(Company.code == "PN_A")).scalars().first()
        b = db.execute(select(Company).where(Company.code == "PN_B")).scalars().first()
        ID["A"], ID["B"] = a.id, b.id

        # ba tài khoản: của A, của B, và một tài khoản chưa gán pháp nhân (trạng thái thật hôm nay)
        for un, vai, cid in (("pn_a", "nv_dh", a.id), ("pn_b", "nv_dh", b.id), ("pn_chua", "nv_dh", None),
                             ("pn_ketoan", "ketoan", None)):
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {un}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True, company_id=cid))
        db.commit()
        dh = db.execute(select(User).where(User.username == "pn_a")).scalars().first()

        # ba tour: một của A, một của B, một chưa xác định pháp nhân
        for ma, cid in (("PN_TOUR_A", a.id), ("PN_TOUR_B", b.id), ("PN_TOUR_X", None)):
            if db.execute(select(Tour).where(Tour.code == ma)).scalars().first() is None:
                db.add(Tour(code=ma, name=f"Chuyến {ma}", tour_type="package",
                            start_date=date(2026, 10, 1), end_date=date(2026, 10, 3),
                            operator_id=dh.id, price_per_pax=1_000_000, planned_pax=10,
                            status="da_duyet", company_id=cid))
        db.commit(); db.close()
        yield


def login(un):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def ma_tour(headers):
    r = client.get("/api/v1/tours?limit=1000", headers=headers)
    assert r.status_code == 200, r.text
    return {t["code"] for t in r.json()}


# ---------------- 1. Không thấy hồ sơ của pháp nhân khác ----------------
def test_nguoi_cua_A_khong_thay_tour_cua_B():
    co = ma_tour(login("pn_a"))
    assert "PN_TOUR_A" in co, "mất chính tour của pháp nhân mình"
    assert "PN_TOUR_B" not in co, "thấy tour của pháp nhân khác – phạm vi không có tác dụng"


def test_nguoi_cua_B_khong_thay_tour_cua_A():
    co = ma_tour(login("pn_b"))
    assert "PN_TOUR_B" in co
    assert "PN_TOUR_A" not in co


# ---------------- 2. Chưa xác định: thấy được, có nhãn, không bị cộng vào ----------------
def test_ho_so_chua_gan_van_thay_duoc_va_co_nhan():
    """Giấu hồ sơ chưa gán đi nghe có vẻ an toàn, nhưng người duy nhất còn có thể gán nó thì không
    còn nhìn thấy nó để mà gán.

    Đo trên hệ thống thật ngày 08/9/2026: hiện KHÔNG còn hồ sơ nào chưa gán pháp nhân. Phép thử vẫn
    giữ – nó canh cho cái ngày có hồ sơ đầu tiên chưa gán, và ngày đó không báo trước."""
    r = client.get("/api/v1/tours?limit=1000", headers=login("pn_a"))
    theo_ma = {t["code"]: t for t in r.json()}
    assert "PN_TOUR_X" in theo_ma, "hồ sơ chưa xác định pháp nhân bị giấu khỏi mọi màn hình"
    assert theo_ma["PN_TOUR_X"]["chua_gan_phap_nhan"] is True
    assert theo_ma["PN_TOUR_A"]["chua_gan_phap_nhan"] is False


def test_chua_gan_khong_bao_gio_gop_vao_so_cua_phap_nhan():
    """Điều không sửa lại được nếu làm sai. Hai con số phải nằm ở hai khoá khác nhau."""
    r = client.get("/api/v1/pham-vi", headers=login("pn_a"))
    assert r.status_code == 200, r.text
    d = {x["kind"]: x for x in r.json()["dong"]}["tour"]
    assert d["cua_phap_nhan"] == 1, f"số của pháp nhân A phải là 1 tour, đang là {d['cua_phap_nhan']}"
    assert d["chua_gan"] >= 1, "không đếm được hồ sơ chưa xác định pháp nhân"
    assert d["cua_phap_nhan"] != d["cua_phap_nhan"] + d["chua_gan"], "hai số đã bị gộp"


def test_dem_khong_tra_ve_khoa_tong():
    """Cố tình không có 'tong'. Ai cần tổng thì phải tự gõ phép cộng, và lúc gõ thì buộc phải nhìn
    thấy mình đang cộng số của pháp nhân với số chưa biết thuộc về ai."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    u = db.execute(select(User).where(User.username == "pn_a")).scalars().first()
    d = PV.dem(db, Tour, u)
    db.close()
    assert "tong" not in d, "thêm khoá 'tong' là mở đường cho việc gộp im lặng trở lại"
    assert set(d) == {"cua_phap_nhan", "chua_gan", "co_cot_phap_nhan"}


def test_khong_co_duong_nao_gop_chua_gan_ve_cong_ty_me():
    """Quy ước 'rỗng là CHƯA XÁC ĐỊNH, không phải công ty mẹ' phải đúng cả khi người xem CHÍNH LÀ
    người của công ty mẹ – đó là lúc cám dỗ gộp lớn nhất."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    me = db.execute(select(User).where(User.username == "pn_a")).scalars().first()
    assert me.company_id == ID["A"]
    d = PV.dem(db, Tour, me)
    db.close()
    assert d["cua_phap_nhan"] == 1, "tour chưa xác định đã bị tính vào công ty mẹ"


# ---------------- 3. Chưa gán pháp nhân thì không bị khoá cửa ----------------
def test_tai_khoan_chua_gan_phap_nhan_khong_bi_khoa_ra_ngoai():
    """Cột users.company_id thêm 07/9/2026, nullable, không có bước điền sẵn. Bật lọc cứng ngay là
    mọi tài khoản chưa gán thấy màn hình trống trơn."""
    co = ma_tour(login("pn_chua"))
    assert {"PN_TOUR_A", "PN_TOUR_B", "PN_TOUR_X"} <= co, "tài khoản chưa gán pháp nhân bị khoá ra ngoài"


def test_chua_gan_thi_khong_duoc_im_lang():
    """Không bị khoá, nhưng phải nói ra – nếu không thì 'chưa làm xong' trông y hệt 'đã làm xong'."""
    r = client.get("/api/v1/auth/me", headers=login("pn_chua"))
    pv = r.json()["pham_vi"]
    assert pv["bi_gioi_han"] is False
    assert pv["ly_do_khong_gioi_han"] == "tai_khoan_chua_gan_phap_nhan"
    assert "chưa được gán pháp nhân" in pv["cau_hien_thi"]


def test_phan_biet_hai_kieu_khong_bi_gioi_han():
    """Kế toán không bị giới hạn vì ĐÚNG THIẾT KẾ (hợp nhất cần nhìn cả hai bên giao dịch nội bộ);
    tài khoản chưa gán không bị giới hạn vì CHƯA LÀM XONG. Trộn hai thứ này lại là mất luôn danh
    sách việc còn phải làm."""
    kt = client.get("/api/v1/auth/me", headers=login("pn_ketoan")).json()["pham_vi"]
    chua = client.get("/api/v1/auth/me", headers=login("pn_chua")).json()["pham_vi"]
    assert kt["bi_gioi_han"] is False and chua["bi_gioi_han"] is False
    assert kt["ly_do_khong_gioi_han"] == "vai_tro_toan_tap_doan"
    assert chua["ly_do_khong_gioi_han"] == "tai_khoan_chua_gan_phap_nhan"
    assert kt["ly_do_khong_gioi_han"] != chua["ly_do_khong_gioi_han"]


def test_vai_tro_toan_tap_doan_thay_ca_hai_phap_nhan():
    co = ma_tour(login("pn_ketoan"))
    assert {"PN_TOUR_A", "PN_TOUR_B", "PN_TOUR_X"} <= co


def test_phien_bi_gioi_han_noi_ro_ten_phap_nhan():
    pv = client.get("/api/v1/auth/me", headers=login("pn_a")).json()["pham_vi"]
    assert pv["bi_gioi_han"] is True
    assert pv["company_id"] == ID["A"]
    assert "Công ty thử A" in pv["cau_hien_thi"]


# ---------------- Hàng rào cho bảng không thuộc pháp nhân nào ----------------
def test_bang_khong_co_cot_phap_nhan_thi_khong_bi_loc():
    """Danh mục dùng chung – ngân hàng, tài khoản kế toán, tham số – không thuộc pháp nhân nào. Ép
    chúng phải có pháp nhân là làm hỏng danh mục của cả tập đoàn."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    u = db.execute(select(User).where(User.username == "pn_a")).scalars().first()
    q = select(Company)
    assert PV.loc(q, Company, u) is q, "bảng không có cột company_id mà vẫn bị thêm điều kiện lọc"
    db.close()


# ---------------- Cột pháp nhân nào cũng phải được nhìn tới (09/9/2026) ----------------
def test_quet_du_moi_bang_co_cot_phap_nhan():
    """Bảng đối chiếu pháp nhân chỉ theo dõi NĂM loại hồ sơ; hệ thống có nhiều bảng mang cột ấy hơn.

    Đây là chỗ một câu báo cáo đúng mà gây hiểu sai: "không còn hồ sơ nào chưa gán pháp nhân" chỉ nói
    về năm bảng, trong khi phần còn lại không ai nhìn tới. Một cột pháp nhân không ai nhìn tới thì
    hoặc luôn rỗng, hoặc mang giá trị do mã tự đặt mà không ai kiểm – và cả hai đều dẫn tới cùng một
    chỗ: đến kỳ hợp nhất, phần dữ liệu ấy không thuộc công ty nào cả.

    Quét từ MÔ HÌNH chứ không từ danh sách viết tay, vì danh sách viết tay lạc hậu ngay lần thêm bảng
    sau – và lần ấy sẽ không ai nhớ quay lại sửa nó.
    """
    from app.services import company_scope as CS
    bang = {c.__tablename__ for c in PV.bang_co_cot_phap_nhan()}
    theo_doi = {CS.KINDS[k]["model"].__tablename__ for k in CS.KINDS}
    assert theo_doi <= bang, "bảng đối chiếu đang theo dõi một bảng không có cột pháp nhân"
    assert len(bang) > len(theo_doi), (
        "quét mô hình ra đúng bằng số bảng đang theo dõi – nhiều khả năng hàm quét đang hỏng, vì "
        "hệ thống có nhiều bảng mang cột company_id hơn năm loại hồ sơ chính")


def test_do_phu_kin_tach_ba_nhom_va_khong_gop_thanh_ty_le():
    """Ba nhóm là ba loại việc khác nhau: xong · còn người phải gán · bảng rỗng chưa kết luận được.

    Cố ý KHÔNG trả về một tỷ lệ phần trăm: một con số 95% làm người đọc yên tâm đúng vào lúc 5% còn
    lại là toàn bộ một phân hệ.
    """
    d = PV.do_phu_kin(_db())
    assert set(d) >= {"da_gan_het", "con_chua_gan", "rong", "dem"}
    assert not any("ty_le" in k or "phan_tram" in k for k in d["dem"]), \
        "gộp thành tỷ lệ là làm mất chỗ đang thiếu"
    tong = len(d["da_gan_het"]) + len(d["con_chua_gan"]) + len(d["rong"])
    assert tong == d["dem"]["so_bang"] == len(PV.bang_co_cot_phap_nhan())
    # mỗi dòng phải nói đủ để đi làm được việc
    for nhom in ("da_gan_het", "con_chua_gan", "rong"):
        for x in d[nhom]:
            assert x["bang"] and x["tong"] == x["da_gan"] + x["chua_gan"]


def test_bang_con_thieu_duoc_xep_len_truoc():
    """Người mở bảng ra là để biết đi làm gì trước. Bảng thiếu nhiều nhất phải nằm trên cùng."""
    d = PV.do_phu_kin(_db())
    con = [x["chua_gan"] for x in d["con_chua_gan"]]
    assert con == sorted(con, reverse=True)


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()
