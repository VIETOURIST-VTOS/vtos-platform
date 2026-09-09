"""Suy pháp nhân cho tài khoản từ hồ sơ nhân sự.

Đo trên hệ thống thật ngày 08/9/2026: 109/110 nhân sự đang làm việc đã có pháp nhân, nhưng chỉ 1/116
tài khoản đang hoạt động có. Phạm vi pháp nhân theo phiên đăng nhập vì thế đang giới hạn đúng một
người. Chỗ trống ấy không phải chỗ trống của quyết định – người quản trị đã quyết ở hồ sơ nhân sự,
chỉ chưa chép sang tài khoản.

Bốn phép thử quan trọng nhất tệp này đều canh những chỗ KHÔNG được làm, vì suy tự động sai thì hậu
quả không nhìn thấy được: một người mang pháp nhân sai vẫn dùng hệ thống bình thường, chỉ có báo cáo
của hai công ty là lệch, và lệch âm thầm.
"""
import os, sys

os.environ["DATABASE_URL"] = "sqlite:///./test_suy_phapnhan.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_suy_phapnhan.db", "test_suy_phapnhan.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, Company
from app.models.hr import Employee
from app.services import suy_phap_nhan as SPN

client = TestClient(app)
MK = "suyphapnhan123"
ID = {}


def _db():
    from app.db.session import SessionLocal
    return SessionLocal()


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.core.security import hash_password
        db = _db()
        for ma, ten in (("SPN_A", "Công ty A"), ("SPN_B", "Công ty B"),
                        ("VTD", "Vietourist Holdings"), ("VTRIP-VT", "Công ty TNHH Vận tải Vietrip")):
            if db.execute(select(Company).where(Company.code == ma)).scalars().first() is None:
                db.add(Company(code=ma, name=ten, kind="con"))
        db.commit()
        ID["A"] = db.execute(select(Company).where(Company.code == "SPN_A")).scalars().first().id
        ID["B"] = db.execute(select(Company).where(Company.code == "SPN_B")).scalars().first().id

        def tk(un, vai="nv_dh", ma="", cid=None):
            u = db.execute(select(User).where(User.username == un)).scalars().first()
            if u is None:
                u = User(username=un, full_name=f"Thử {un}", role=vai, department="Kiểm thử",
                         staff_code=ma, password_hash=hash_password(MK), active=True, company_id=cid)
                db.add(u); db.commit(); db.refresh(u)
            ID[un] = u.id
            return u

        def hs(ma, u=None, cid=None, active=True):
            e = db.execute(select(Employee).where(Employee.code == ma)).scalars().first()
            if e is None:
                e = Employee(code=ma, full_name=f"HS {ma}", department="Kiểm thử")
                db.add(e)
            e.user_id = u.id if u else None
            e.company_id = cid
            e.active = active
            db.commit()
            return e

        # 1. nối bằng user_id, hồ sơ có pháp nhân → SUY ĐƯỢC
        hs("SPN01", tk("spn_uid"), ID["A"])
        # 2. nối bằng MÃ NHÂN VIÊN (hồ sơ chưa gắn user_id) → SUY ĐƯỢC
        tk("spn_ma", ma="SPN02"); hs("SPN02", None, ID["B"])
        # 3. hồ sơ chưa có pháp nhân → KHÔNG suy được, phải nói rõ vì sao
        hs("SPN03", tk("spn_hs_trong"), None)
        # 4. không có hồ sơ nào → KHÔNG suy được
        tk("spn_khong_ho_so")
        # 5. hồ sơ ĐÃ NGHỈ, có pháp nhân → KHÔNG suy: quan hệ đã chấm dứt
        hs("SPN05", tk("spn_ho_so_nghi"), ID["A"], active=False)
        # 6. tài khoản ĐÃ CÓ pháp nhân B, hồ sơ nói A → LỆCH, báo ra chứ không tự sửa
        hs("SPN06", tk("spn_lech", cid=ID["B"]), ID["A"])
        # 7. QUY TẮC 09/9: phòng Đội xe → VTRIP-VT, còn lại → VTD
        e = hs("SPN07", tk("spn_taixe", "xe_hdv"), None); e.department = "doi_xe"
        e = hs("SPN08", tk("spn_gd_doi_xe", "gd_doi_xe"), None); e.department = "doi_xe"
        e = hs("SPN09", tk("spn_hdv", "xe_hdv"), None); e.department = "huong_dan"
        e = hs("SPN10", tk("spn_vanphong", "nv_kd"), None); e.department = "kd_le"
        # hồ sơ ghi NGƯỢC quy tắc – phải nêu ra, không im lặng lấy bên nào
        e = hs("SPN11", tk("spn_lech_quy_tac"), ID["A"]); e.department = "doi_xe"
        db.commit()
        # 8. người bấm nút
        tk("spn_cntt", "cntt")
        tk("spn_bks", "bks")
        tk("spn_hcns", "hcns")
        db.close()
        yield


def login(un):
    r = client.post("/api/v1/auth/login", data={"username": un, "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def nhom(kq, ten):
    return {d["username"]: d for d in kq[ten]}


def go_phap_nhan(*usernames):
    """Gỡ pháp nhân của vài tài khoản rồi trả về bảng xem trước.

    Các phép thử trong tệp này chạy chung một cơ sở dữ liệu và vài phép trước đã BẤM NÚT GHI, nên tài
    khoản đã có pháp nhân sẽ rơi khỏi nhóm 'suy_duoc' sang 'da_co'. Phép thử về QUY TẮC phải nói về
    quy tắc, không nói về việc phép thử nào chạy trước – nên dọn trước khi hỏi."""
    db = _db()
    for un in usernames:
        u = db.execute(select(User).where(User.username == un)).scalars().first()
        if u: u.company_id = None
    db.commit(); db.close()
    return nhom(SPN.xem_truoc(_db()), "suy_duoc")


# ---------------- Suy đúng cái suy được ----------------
def test_noi_duoc_bang_user_id():
    d = go_phap_nhan("spn_uid")["spn_uid"]
    assert d["noi_bang"] == "user_id" and d["company"] == "VTD"


def test_noi_duoc_bang_ma_nhan_vien_khi_ho_so_chua_gan_user_id():
    """Hai đường nối lệch nhau ở vài tài khoản là chuyện có thật, nên phải nối được cả hai đường –
    và theo đúng thứ tự mà phần còn lại của hệ thống đang dùng: user_id trước, mã sau."""
    d = go_phap_nhan("spn_ma")["spn_ma"]
    assert d["noi_bang"] == "ma_nhan_vien" and d["company"] == "VTD"


# ---------------- Bốn chỗ KHÔNG được làm ----------------
def test_ho_so_chua_gan_phap_nhan_van_suy_duoc_theo_quy_tac():
    """Đổi hướng so với bản đầu (08/9). Bản ấy chỉ suy khi HỒ SƠ đã có pháp nhân, và từ chối mọi
    trường hợp khác vì "không đoán". Quyết định 09/9 của Chủ tịch làm cột company_id của hồ sơ không
    còn là nguồn duy nhất: đã có một QUY TẮC nói thẳng phòng nào thuộc pháp nhân nào, nên suy theo quy
    tắc không phải là đoán – đoán là khi không có quy tắc mà vẫn điền."""
    d = go_phap_nhan("spn_hs_trong")["spn_hs_trong"]
    assert d["company"] == "VTD", "hồ sơ chưa gán pháp nhân vẫn suy được theo phòng ban"


def test_van_khong_doan_khi_danh_muc_thieu_phap_nhan():
    """Ranh giới của "không đoán" nay nằm ở đây: quy tắc gọi tên một pháp nhân mà danh mục không có
    thì DỪNG, không tự tạo và không lấy tạm công ty mẹ."""
    goc = dict(SPN.PHONG_THEO_PHAP_NHAN)
    SPN.PHONG_THEO_PHAP_NHAN["huong_dan"] = "KHONG-CO-TRONG-DANH-MUC"
    try:
        kq = SPN.xem_truoc(_db())
        d = nhom(kq, "khong_suy_duoc")
        assert "spn_hdv" in d, "quy tắc trỏ tới pháp nhân không có mà vẫn gán bừa"
        assert "danh mục" in d["spn_hdv"]["ly_do"]
    finally:
        SPN.PHONG_THEO_PHAP_NHAN.clear(); SPN.PHONG_THEO_PHAP_NHAN.update(goc)


def test_khong_doan_khi_khong_co_ho_so():
    kq = SPN.xem_truoc(_db())
    d = nhom(kq, "khong_suy_duoc")["spn_khong_ho_so"]
    assert "không nối được" in d["ly_do"]


def test_khong_suy_tu_ho_so_da_nghi():
    """Hồ sơ đã nghỉ vẫn giữ pháp nhân cũ; suy từ nó là gán theo một quan hệ đã chấm dứt."""
    kq = SPN.xem_truoc(_db())
    assert "spn_ho_so_nghi" not in nhom(kq, "suy_duoc")
    assert "spn_ho_so_nghi" in nhom(kq, "khong_suy_duoc")


def test_lech_thi_bao_ra_chu_khong_tu_sua():
    """Gán tay là quyết định của con người; suy tự động là phỏng theo dữ liệu. Cái sau không được ghi
    đè cái trước – nhưng cũng không được im lặng bỏ qua."""
    kq = SPN.xem_truoc(_db())
    d = nhom(kq, "lech_voi_ho_so")["spn_lech"]
    assert d["company_id"] == ID["B"] and d["ho_so_company"] == "SPN_A"
    assert "spn_lech" not in nhom(kq, "suy_duoc")


def test_ghi_xong_khong_dung_toi_tai_khoan_da_co_phap_nhan():
    db = _db()
    truoc = db.get(User, ID["spn_lech"]).company_id
    db.close()
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_cntt"))
    db = _db(); sau = db.get(User, ID["spn_lech"]).company_id; db.close()
    assert sau == truoc == ID["B"], "suy tự động đã ghi đè một giá trị gán tay"


# ---------------- Xem trước rồi mới ghi ----------------
def test_xem_truoc_khong_ghi_gi():
    db = _db()
    truoc = {u.id: u.company_id for u in db.execute(select(User)).scalars()}
    db.close()
    client.get("/api/v1/access/phap-nhan/suy-tu-ho-so", headers=login("spn_bks"))
    db = _db()
    sau = {u.id: u.company_id for u in db.execute(select(User)).scalars()}
    db.close()
    assert truoc == sau, "bảng xem trước đã ghi vào cơ sở dữ liệu"


def test_chay_lai_lan_hai_khong_ghi_them_gi():
    """Bấm hai lần là chuyện sẽ xảy ra. Lần hai phải không còn gì để ghi, chứ không phải ghi lại."""
    h = login("spn_cntt")
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=h)
    r2 = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=h)
    assert r2.json()["da_ghi"] == 0


def test_ghi_duoc_cho_rieng_may_tai_khoan_da_chon():
    """Người quản trị bỏ tick vài dòng ở bảng xem trước thì chỉ những dòng còn lại được ghi."""
    db = _db()
    u = db.get(User, ID["spn_uid"]); u.company_id = None
    v = db.get(User, ID["spn_ma"]); v.company_id = None
    db.commit(); db.close()
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so",
                    json={"user_ids": [ID["spn_uid"]]}, headers=login("spn_cntt"))
    assert r.json()["da_ghi"] == 1
    db = _db()
    vtd = db.execute(select(Company).where(Company.code == "VTD")).scalars().first()
    assert db.get(User, ID["spn_uid"]).company_id == vtd.id
    assert db.get(User, ID["spn_ma"]).company_id is None, "ghi cả dòng không được chọn"
    db.close()


# ---------------- Ai được xem, ai được ghi ----------------
def test_xem_duoc_ma_khong_can_quyen_ghi():
    """Ban Kiểm soát phải đối chiếu được bảng này mà không cần quyền ghi vào bảng tài khoản."""
    r = client.get("/api/v1/access/phap-nhan/suy-tu-ho-so", headers=login("spn_bks"))
    assert r.status_code == 200, r.text


def test_khong_phai_ai_cung_ghi_duoc():
    """Cùng bộ vai trò với gán lẻ. Rộng hơn thì hàng loạt thành đường vòng của lẻ."""
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_uid"))
    assert r.status_code == 403


def test_ban_kiem_soat_khong_ghi_duoc():
    r = client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_bks"))
    assert r.status_code == 403, "vai trò chỉ đọc ghi được vào bảng tài khoản"


# ---------------- Có dấu vết ----------------
def test_moi_lan_ghi_deu_de_lai_nhat_ky():
    db = _db()
    for un in ("spn_uid", "spn_ma"):
        x = db.get(User, ID[un]); x.company_id = None
    db.commit(); db.close()
    client.post("/api/v1/access/phap-nhan/suy-tu-ho-so", json={}, headers=login("spn_cntt"))
    r = client.get("/api/v1/access/audit?limit=50", headers=login("spn_cntt"))
    assert r.status_code == 200, r.text
    rows = r.json()["rows"] if isinstance(r.json(), dict) else r.json()
    assert any("suy_phap_nhan_tai_khoan_tu_ho_so" in str(x) for x in rows), \
        "gán pháp nhân hàng loạt mà không có dòng nhật ký nào"


# ---------------- Quy tắc pháp nhân 09/9/2026 ----------------
def test_phong_doi_xe_thuoc_cong_ty_van_tai():
    """Chủ tịch chốt 09/9: tài xế và Giám đốc điều hành đội xe thuộc Công ty TNHH Vận tải Vietrip."""
    d = go_phap_nhan("spn_taixe", "spn_gd_doi_xe")
    for un in ("spn_taixe", "spn_gd_doi_xe"):
        assert d[un]["company"] == "VTRIP-VT", f"{un} → {d[un]['company']}, phải là VTRIP-VT"


def test_moi_phong_con_lai_thuoc_cong_ty_me():
    d = go_phap_nhan("spn_vanphong")
    assert d["spn_vanphong"]["company"] == "VTD"


def test_huong_dan_vien_KHONG_bi_keo_sang_cong_ty_van_tai():
    """Chỗ dễ sai nhất của quy tắc này. Vai trò xe_hdv gộp CẢ tài xế lẫn hướng dẫn viên vào một tên,
    nên chốt theo vai trò là kéo toàn bộ HDV sang công ty vận tải – điều Chủ tịch không nói, và là
    điều sai: HDV nay là cộng tác viên của phòng Hướng dẫn, không phải người của đội xe."""
    d = go_phap_nhan("spn_hdv")
    assert d["spn_hdv"]["company"] == "VTD", \
        "hướng dẫn viên bị kéo sang công ty vận tải – quy tắc đang đọc theo vai trò thay vì phòng ban"
    assert d["spn_hdv"]["phong"] == "huong_dan"


def test_ho_so_ghi_khac_quy_tac_thi_neu_ra_chu_khong_im_lang():
    """Hai nguồn nói khác nhau thì phải nói ra. Im lặng lấy một bên là chỗ một người mang pháp nhân sai
    mà không ai biết – và pháp nhân sai thì bút toán lương chia sai, âm thầm."""
    # Tình huống: TÀI KHOẢN chưa có pháp nhân, nhưng HỒ SƠ của người ấy ghi một pháp nhân khác với
    # quy tắc. Quy tắc thắng, và chỗ lệch phải được nêu ra.
    d = go_phap_nhan("spn_lech_quy_tac")
    x = d["spn_lech_quy_tac"]
    assert x["company"] == "VTRIP-VT", "quy tắc phải thắng số liệu hồ sơ cũ"
    assert x.get("ho_so_company") == "SPN_A"
    assert "quy tắc" in x.get("ly_do_quy_tac", ""), "không nêu được vì sao hai bên lệch"


def test_quy_tac_duoc_cong_bo_ra_giao_dien():
    """Người bấm nút phải đọc được quy tắc ngay tại chỗ bấm, không phải đi tra mã nguồn."""
    kq = SPN.xem_truoc(_db())
    assert kq["quy_tac"]["theo_phong"]["doi_xe"] == "VTRIP-VT"
    assert kq["quy_tac"]["mac_dinh"] == "VTD"
    assert "09/9/2026" in kq["quy_tac"]["cau"]


# ---------------- Tài khoản cho vai trò máy ----------------
def test_tao_tai_khoan_robot_mat_khau_ngau_nhien_va_khong_bat_doi():
    r = client.post("/api/v1/access/accounts/robot", json={"role": "robot_ks"},
                    headers=login("spn_cntt"))
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["username"] == "robot_ks"
    assert len(d["mat_khau"]) >= 20, "mật khẩu robot phải dài và ngẫu nhiên, không phải mã nhân viên"
    db = _db()
    t = db.execute(select(User).where(User.username == "robot_ks")).scalars().first()
    db.close()
    assert t.must_change_password is False, \
        "bắt robot đổi mật khẩu lần đầu là khoá cửa từ bên trong – không có ai ngồi bấm"
    assert t.ngoai_bien_che is True, "robot không có trong bảng lương"
    # và mật khẩu ấy đăng nhập được thật
    assert client.post("/api/v1/auth/login",
                       data={"username": "robot_ks", "password": d["mat_khau"]}).status_code == 200


def test_khong_tao_hai_tai_khoan_cho_cung_mot_robot():
    """Hai tài khoản cùng một vai trò máy thì không truy được lần chạy nào của bên nào."""
    r = client.post("/api/v1/access/accounts/robot", json={"role": "robot_ks"},
                    headers=login("spn_cntt"))
    assert r.status_code == 409, r.text


def test_khong_tao_duoc_tai_khoan_may_cho_vai_tro_nguoi():
    """Cửa này sinh ra cho vai trò máy. Cho phép nó tạo tài khoản người là một đường tạo tài khoản
    KHÔNG đi qua kiểm tra nào của cửa tạo tài khoản thường."""
    r = client.post("/api/v1/access/accounts/robot", json={"role": "ketoan"},
                    headers=login("spn_cntt"))
    assert r.status_code == 422, r.text


def test_khong_phai_ai_cung_tao_duoc_tai_khoan_robot():
    r = client.post("/api/v1/access/accounts/robot", json={"role": "robot_vpm"},
                    headers=login("spn_bks"))
    assert r.status_code == 403, r.text


# ---------------- Số lượt đọc, không phải thời gian ----------------
def test_xem_truoc_doc_danh_muc_phap_nhan_dung_MOT_lan():
    """Đếm số lượt đọc thật, không đo thời gian: thời gian trên máy chạy thử không nói được gì về máy
    chủ 0,5 CPU, còn số lượt đọc thì nói.

    Bản đầu tra danh mục pháp nhân một lần cho MỖI nhân sự – 110 lượt đọc để lấy đúng hai con số, và
    xem_truoc() bị gọi hai lần trong một lần bấm nút. Không sai kết quả, chỉ trả giá nhiều lần cho
    cùng một câu trả lời – đúng loại việc đã làm cổng trả 502 hôm 08/9 và làm máy chủ vượt bộ nhớ
    hôm 09/9. Bảng này chỉ có mười dòng nên hôm nay chưa đau; phép thử đứng đây cho ngày tập đoàn có
    thêm pháp nhân và số nhân sự tăng gấp mấy lần.
    """
    from sqlalchemy import event
    from app.db.session import SessionLocal
    db = SessionLocal()
    dem = {"companies": 0, "tong": 0}

    def theo_doi(conn, cur, stm, params, ctx, many):
        dem["tong"] += 1
        if "companies" in stm.lower():
            dem["companies"] += 1

    event.listen(db.get_bind(), "before_cursor_execute", theo_doi)
    try:
        SPN.xem_truoc(db)
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", theo_doi)
        db.close()

    assert dem["companies"] <= 2, (
        f"đọc bảng pháp nhân {dem['companies']} lần cho một bảng xem trước – phải đọc một lần rồi "
        f"dùng lại")
    assert dem["tong"] <= 10, (
        f"{dem['tong']} lượt đọc cho một bảng xem trước. Con số này phải KHÔNG tăng theo số nhân sự; "
        f"tăng theo nghĩa là có một truy vấn nằm trong vòng lặp")


# ---------------- Mỗi con số phải có một cửa cho NGƯỜI nhập ----------------
def test_hcns_tu_gan_duoc_phap_nhan_cho_ho_so_nhan_su():
    """Ranh giới công việc do Chủ tịch đặt 09/9/2026: hệ thống viết cấu trúc và phép tính, còn SỐ LIỆU
    thì nhân viên các bộ phận tự nhập.

    Phép thử này canh vế thứ hai. Trước 09/9 ô chọn pháp nhân chỉ có ở bảng hướng dẫn viên và bảng xe,
    nên pháp nhân của một TÀI XẾ không có cửa nào để HCNS tự sửa – muốn đổi thì phải nhờ người gọi
    thẳng vào máy chủ. Và đó đúng là chuyện đã xảy ra: mười hồ sơ tài xế được sửa bằng tay từ bên
    ngoài màn hình, vì màn hình không có chỗ để sửa.

    Một con số mà người phụ trách không tự nhập được là một con số sẽ sai và ở yên đó, vì người duy
    nhất phát hiện ra nó sai lại là người không sửa được.
    """
    from app.models.hr import Employee
    db = _db()
    e = db.execute(select(Employee).where(Employee.code == "SPN07")).scalars().first()
    eid, truoc = e.id, e.company_id
    db.close()

    r = client.put(f"/api/v1/employees/{eid}/company", json={"company_id": ID["B"]},
                   headers=login("spn_hcns"))
    assert r.status_code == 200, f"HCNS không tự gán được pháp nhân cho hồ sơ nhân sự: {r.text}"
    db = _db()
    assert db.get(Employee, eid).company_id == ID["B"]
    # trả lại như cũ để các phép thử khác không bị ảnh hưởng
    db.get(Employee, eid).company_id = truoc; db.commit(); db.close()


def test_nguoi_khong_phu_trach_thi_khong_gan_duoc():
    """Cửa mở cho người phụ trách, không mở cho mọi người – pháp nhân quyết định bút toán lương thuộc
    công ty nào khi hợp nhất."""
    from app.models.hr import Employee
    db = _db()
    eid = db.execute(select(Employee).where(Employee.code == "SPN07")).scalars().first().id
    db.close()
    r = client.put(f"/api/v1/employees/{eid}/company", json={"company_id": ID["A"]},
                   headers=login("spn_uid"))
    assert r.status_code == 403, f"nhân viên thường gán được pháp nhân: {r.status_code}"
