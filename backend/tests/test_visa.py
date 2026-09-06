"""Phân hệ Visa – kiểm thử theo tiêu chí nghiệm thu mục 15 của đặc tả.

Mỗi hàm test ghi rõ nó chứng minh tiêu chí số mấy, để sau này ai sửa mã nguồn cũng biết mình đang phá cái gì.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_visa.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_visa.db"): os.remove("test_visa.db")
from datetime import date, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}
DEP = str(date.today() + timedelta(days=90))


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def uid(username):
    h = login("chutich")
    for u in client.get("/api/v1/users", headers=h).json():
        if u["username"] == username:
            return u["id"]
    raise AssertionError(f"không thấy người dùng {username}")


def new_case(name, dob=None, on_dup="block", **kw):
    h = login("tp.dieuhanh")
    body = {"applicant_name": name, "market_code": "UK", "departure_date": DEP,
            "visa_type": "UK_STANDARD_VISITOR", "on_duplicate": on_dup}
    if dob:
        body["applicant_dob"] = dob
    body.update(kw)
    r = client.post("/api/v1/visa/ho-so", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def to_stage_thu_thap(cid, owner="dh.lan"):
    """Đưa hồ sơ tới bước thu thập tài liệu: phân công → khai form → gửi → khách xác nhận."""
    h = login("tp.dieuhanh")
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=h, json={"visa_owner_user_id": uid(owner),
                                                                       "supervisor_user_id": uid("tp.dieuhanh")})
    fv = client.post(f"/api/v1/visa/ho-so/{cid}/form", headers=h,
                     json={"data": {"ho_ten": "X", "so_ho_chieu": "C1234567", "quoc_tich": "VN"}}).json()
    client.post(f"/api/v1/visa/ho-so/{cid}/form/{fv['id']}/gui-khach", headers=h)
    r = client.post(f"/api/v1/visa/ho-so/{cid}/xac-nhan-form", headers=h,
                    json={"form_version_id": fv["id"], "confirmed_by_name": "Khách"})
    assert r.status_code == 201, r.text
    return fv


def upload(cid, item_id, who="dh.lan", content=b"noi dung tai lieu"):
    r = client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu", headers=login(who),
                    files={"file": ("ho_chieu.pdf", content, "application/pdf")},
                    data={"checklist_item_id": str(item_id)})
    assert r.status_code == 201, r.text
    return r.json()


def detail(cid, who="tp.dieuhanh"):
    r = client.get(f"/api/v1/visa/ho-so/{cid}", headers=login(who))
    assert r.status_code == 200, r.text
    return r.json()


def items(cid):
    return {i["key"]: i for i in detail(cid)["checklist"]}


def satisfy_all(cid):
    """Chấp nhận mọi mục bắt buộc – dùng làm nền cho các test bước sau."""
    for key, it in items(cid).items():
        if not it["bat_buoc"]:
            continue
        doc = upload(cid, it["id"])
        r = client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{doc['id']}/kiem-tra",
                        headers=login("tp.dieuhanh"), json={"decision": "ACCEPTED"})
        assert r.status_code == 201, r.text


# ---------- Nền tảng ----------

def test_checklist_theo_dieu_kien_va_quy_trinh_thi_truong():
    """Checklist áp theo điều kiện tuổi; quy trình lấy theo cấu hình thị trường chứ không cứng theo UK."""
    nguoi_lon = new_case("Nguyen Van A", dob="1990-05-01")
    tre_em = new_case("Nguyen Van B", dob=str(date.today().replace(year=date.today().year - 10)))
    assert "giay_khai_sinh" not in items(nguoi_lon["case"]["id"])
    assert "giay_khai_sinh" in items(tre_em["case"]["id"])       # dưới 18 mới phải nộp khai sinh

    # Thị trường không lấy sinh trắc học ⇒ bước đó biến mất khỏi quy trình, không phải sửa mã nguồn
    h = login("chutich")
    r = client.post("/api/v1/visa/thi-truong", headers=h,
                    json={"code": "KR", "name": "Hàn Quốc", "requires_biometrics": False,
                          "requires_appointment": False, "sla_hours": {"kiem_tra": 24}})
    assert r.status_code == 201, r.text
    assert "sinh_trac_hoc" not in r.json()["stages"]
    assert "lich_hen" not in r.json()["stages"]


def test_nghiem_thu_9_khong_sinh_ho_so_trung():
    """Tiêu chí 9: tạo lại cùng một yêu cầu không âm thầm sinh hồ sơ trùng."""
    a = new_case("Tran Thi Trung", dob="1988-02-02")
    r = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                    json={"applicant_name": "Tran Thi Trung", "market_code": "UK", "departure_date": DEP})
    assert r.status_code == 422 and "trùng" in r.json()["detail"]
    # Chọn mở hồ sơ hiện có thì trả về đúng hồ sơ cũ, không tạo bản ghi mới
    r2 = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                     json={"applicant_name": "Tran Thi Trung", "market_code": "UK", "departure_date": DEP,
                           "on_duplicate": "open_existing"})
    assert r2.status_code == 201 and r2.json()["case"]["id"] == a["case"]["id"]
    # Nộp lại thì là hồ sơ MỚI nhưng có liên kết về hồ sơ cũ, không xóa hồ sơ cũ
    r3 = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                     json={"applicant_name": "Tran Thi Trung", "market_code": "UK", "departure_date": DEP,
                           "on_duplicate": "resubmit"})
    assert r3.status_code == 201 and r3.json()["case"]["id"] != a["case"]["id"]


def test_nghiem_thu_1_pham_vi_duoc_giao():
    """Tiêu chí 1: nhân viên chỉ xem được hồ sơ thuộc phạm vi được giao, kể cả gọi thẳng API."""
    c = new_case("Le Van Pham Vi", dob="1991-01-01")["case"]
    cid = c["id"]
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("dh.minh")).status_code == 403
    assert client.get("/api/v1/visa/ho-so", headers=login("dh.minh")).json()["total"] == 0
    client.post(f"/api/v1/visa/ho-so/{cid}/phan-cong", headers=login("tp.dieuhanh"),
                json={"visa_owner_user_id": uid("dh.minh")})
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("dh.minh")).status_code == 200

    # Tải tệp cũng phải qua kiểm quyền, không đi vòng bằng id tài liệu
    to_stage_thu_thap(cid, owner="dh.minh")
    doc = upload(cid, items(cid)["ho_chieu"]["id"], who="dh.minh")
    assert client.get(f"/api/v1/visa/tai-lieu/{doc['id']}/tep", headers=login("dh.minh")).status_code == 200
    assert client.get(f"/api/v1/visa/tai-lieu/{doc['id']}/tep", headers=login("dh.lan")).status_code == 403


# ---------- Tài liệu ----------

def test_nghiem_thu_3_va_4_nop_lai_va_khach_bao_khong_nop():
    """Tiêu chí 3: nộp lại sinh phiên bản mới và phải kiểm lại. Tiêu chí 4: không nộp KHÔNG tự vượt điều kiện."""
    cid = new_case("Pham Tai Lieu", dob="1985-03-03")["case"]["id"]
    to_stage_thu_thap(cid)
    it = items(cid)["ho_chieu"]
    d1 = upload(cid, it["id"])
    client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{d1['id']}/kiem-tra", headers=login("tp.dieuhanh"),
                json={"decision": "ACCEPTED"})
    assert items(cid)["ho_chieu"]["trang_thai"] == "ACCEPTED"

    d2 = upload(cid, it["id"], content=b"ban moi khac han")
    assert d2["version"] == 2 and d2["sha256"] != d1["sha256"]
    assert items(cid)["ho_chieu"]["trang_thai"] == "UPLOADED"      # tài liệu đã duyệt bị thay ⇒ quay lại kiểm tra
    assert client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{d1['id']}/kiem-tra", headers=login("tp.dieuhanh"),
                       json={"decision": "ACCEPTED"}).status_code == 422   # bản cũ đã bị thay, không kiểm nữa
    client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{d2['id']}/kiem-tra", headers=login("tp.dieuhanh"),
                json={"decision": "ACCEPTED"})

    # Khách báo không nộp chứng minh tài chính ⇒ chỉ là ĐỀ NGHỊ, mục vẫn chưa đạt
    tc = items(cid)["chung_minh_tai_chinh"]
    w = client.post(f"/api/v1/visa/ho-so/{cid}/ngoai-le", headers=login("dh.lan"),
                    json={"checklist_item_id": tc["id"], "reason": "Khách không có sổ tiết kiệm"})
    assert w.status_code == 201 and w.json()["quyet_dinh"] == "PENDING"
    assert items(cid)["chung_minh_tai_chinh"]["trang_thai"] == "WAIVER_REQUESTED"
    # Còn mục bắt buộc chưa nộp thì chưa gửi kiểm tra được (lý do là các mục MISSING, không phải đề nghị treo)
    assert client.post(f"/api/v1/visa/ho-so/{cid}/gui-kiem-tra", headers=login("dh.lan")).status_code == 422

    # Chuyên viên KHÔNG được tự duyệt ngoại lệ; phải người có thẩm quyền
    wid = w.json()["id"]
    assert client.post(f"/api/v1/visa/ho-so/{cid}/ngoai-le/{wid}/quyet-dinh", headers=login("dh.lan"),
                       json={"approve": True}).status_code == 422
    ok = client.post(f"/api/v1/visa/ho-so/{cid}/ngoai-le/{wid}/quyet-dinh", headers=login("tp.dieuhanh"),
                     json={"approve": True, "note": "Chấp nhận bảng lương thay thế"})
    assert ok.status_code == 200 and items(cid)["chung_minh_tai_chinh"]["trang_thai"] == "WAIVED"


def test_nghiem_thu_4_de_nghi_treo_khong_qua_duoc_cua_kiem_tra():
    """Tiêu chí 4, tách riêng: mọi mục khác đã ĐẠT, chỉ còn một mục đang đề nghị miễn nộp.

    Theo mục 5.1 của đặc tả, bước «Thu thập tài liệu» xong khi các mục đã nộp HOẶC có đề nghị ngoại lệ, nên
    gửi kiểm tra vẫn qua. Cửa chặn thật nằm ở «Kiểm tra trước khai/nộp»: chừng nào đề nghị chưa được người có
    thẩm quyền quyết định thì không ai qua được. Test trước đó chạm vào tình huống này nhưng lỗi 422 khi ấy đến
    từ các mục còn MISSING, nên không chứng minh được điều đang cần – đây mới là phép thử đúng.
    """
    cid = new_case("Ngoai Le Treo", dob="1984-04-04")["case"]["id"]
    to_stage_thu_thap(cid)
    it = items(cid)
    for key, i in it.items():
        if not i["bat_buoc"] or key == "chung_minh_tai_chinh":
            continue
        doc = upload(cid, i["id"])
        client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{doc['id']}/kiem-tra", headers=login("tp.dieuhanh"),
                    json={"decision": "ACCEPTED"})
    w = client.post(f"/api/v1/visa/ho-so/{cid}/ngoai-le", headers=login("dh.lan"),
                    json={"checklist_item_id": it["chung_minh_tai_chinh"]["id"],
                          "reason": "Khách không có sổ tiết kiệm"}).json()
    # Gửi kiểm tra: QUA – đúng theo điều kiện hoàn thành của bước thu thập tài liệu
    assert client.post(f"/api/v1/visa/ho-so/{cid}/gui-kiem-tra", headers=login("dh.lan")).status_code == 200
    # Kiểm tra đạt: CHẶN – đề nghị còn treo thì mục bắt buộc chưa coi là xong
    r = client.post(f"/api/v1/visa/ho-so/{cid}/kiem-tra-dat", headers=login("tp.dieuhanh"))
    assert r.status_code == 422 and "chung_minh_tai_chinh" in r.json()["detail"]
    # Từ chối miễn nộp thì mục quay về chưa nộp, vẫn không qua được
    client.post(f"/api/v1/visa/ho-so/{cid}/ngoai-le/{w['id']}/quyet-dinh", headers=login("tp.dieuhanh"),
                json={"approve": False, "note": "Bảng lương chưa đủ căn cứ"})
    assert items(cid)["chung_minh_tai_chinh"]["trang_thai"] == "MISSING"
    assert client.post(f"/api/v1/visa/ho-so/{cid}/kiem-tra-dat", headers=login("tp.dieuhanh")).status_code == 422
    # Nộp bổ sung và được chấp nhận thì mới qua
    doc = upload(cid, it["chung_minh_tai_chinh"]["id"])
    client.post(f"/api/v1/visa/ho-so/{cid}/tai-lieu/{doc['id']}/kiem-tra", headers=login("tp.dieuhanh"),
                json={"decision": "ACCEPTED"})
    assert client.post(f"/api/v1/visa/ho-so/{cid}/kiem-tra-dat", headers=login("tp.dieuhanh")).status_code == 200


def test_nghiem_thu_5_doi_thong_tin_quan_trong_phai_xac_nhan_lai():
    """Tiêu chí 5: đổi trường quan trọng làm phát sinh yêu cầu xác nhận lại ĐÚNG phiên bản mới."""
    cid = new_case("Vo Thi Form", dob="1992-04-04")["case"]["id"]
    fv1 = to_stage_thu_thap(cid)
    h = login("tp.dieuhanh")
    fv2 = client.post(f"/api/v1/visa/ho-so/{cid}/form", headers=h,
                      json={"data": {"ho_ten": "X", "so_ho_chieu": "C7654321", "quoc_tich": "VN"}}).json()
    assert fv2["can_xac_nhan_lai"] is True and "so_ho_chieu" in fv2["truong_doi"]
    assert detail(cid)["case"]["current_stage"] == "khach_xac_nhan"
    # Xác nhận lại phiên bản CŨ không có giá trị
    r = client.post(f"/api/v1/visa/ho-so/{cid}/xac-nhan-form", headers=h,
                    json={"form_version_id": fv1["id"], "confirmed_by_name": "Khách"})
    assert r.status_code == 422 and "phiên bản mới" in r.json()["detail"]
    client.post(f"/api/v1/visa/ho-so/{cid}/form/{fv2['id']}/gui-khach", headers=h)
    assert client.post(f"/api/v1/visa/ho-so/{cid}/xac-nhan-form", headers=h,
                       json={"form_version_id": fv2["id"], "confirmed_by_name": "Khách"}).status_code == 201


def test_dong_bo_checklist_giu_ket_qua_cu():
    """Mẫu đổi phiên bản: mục không đổi giữ nguyên kết quả, mục bị ảnh hưởng phải kiểm lại (mục 6.3)."""
    cid = new_case("Bui Van Mau", dob="1980-06-06")["case"]["id"]
    to_stage_thu_thap(cid)
    satisfy_all(cid)
    h = login("chutich")
    moi = [dict(i) for i in __import__("app.services.visa", fromlist=["x"]).UK_CHECKLIST]
    for i in moi:
        if i["key"] == "anh_the":
            i["ten"] = "Ảnh thẻ nền trắng 45x35mm, chụp trong 6 tháng gần nhất"
    client.post("/api/v1/visa/checklist-mau", headers=h, json={"market_code": "UK", "items": moi})
    r = client.post(f"/api/v1/visa/ho-so/{cid}/dong-bo-checklist", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["kiem_lai"] == ["anh_the"]
    it = items(cid)
    assert it["anh_the"]["can_kiem_lai"] is True                 # yêu cầu đổi ⇒ kết quả cũ phải kiểm lại
    assert it["ho_chieu"]["can_kiem_lai"] is False               # mục không đổi thì giữ nguyên
    # Còn mục phải kiểm lại thì chưa qua được bước kiểm tra
    client.post(f"/api/v1/visa/ho-so/{cid}/gui-kiem-tra", headers=login("dh.lan"))
    assert client.post(f"/api/v1/visa/ho-so/{cid}/kiem-tra-dat", headers=login("tp.dieuhanh")).status_code == 422


# ---------- Lịch hẹn, kết quả, gia đình ----------

def _den_buoc_lich_hen(ten):
    cid = new_case(ten, dob="1987-07-07")["case"]["id"]
    to_stage_thu_thap(cid)
    satisfy_all(cid)
    assert client.post(f"/api/v1/visa/ho-so/{cid}/gui-kiem-tra", headers=login("dh.lan")).status_code == 200
    assert client.post(f"/api/v1/visa/ho-so/{cid}/kiem-tra-dat", headers=login("tp.dieuhanh")).status_code == 200
    r = client.post(f"/api/v1/visa/ho-so/{cid}/khai-ho-so", headers=login("dh.lan"),
                    json={"reference_code": "GWF" + ten[:4], "portal": "VFS UK"})
    assert r.status_code == 201 and r.json()["giai_doan"] == "lich_hen"
    return cid


def test_nghiem_thu_6_va_7_doi_lich_va_lich_da_qua():
    """Tiêu chí 6: đổi lịch giữ lịch cũ, người đổi, lý do. Tiêu chí 7: lịch đã qua tạo cảnh báo, không tự kết luận."""
    cid = _den_buoc_lich_hen("Do Van Lich")
    h = login("dh.lan")
    ap = client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen", headers=h,
                     json={"starts_at": str(datetime.now() + timedelta(days=3)),
                           "location": "VFS TP.HCM"}).json()
    assert client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen/{ap['id']}/doi-lich", headers=h,
                       json={"starts_at": str(datetime.now() + timedelta(days=5)),
                             "reason": ""}).status_code == 422        # đổi lịch phải có lý do
    new = client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen/{ap['id']}/doi-lich", headers=h,
                      json={"starts_at": str(datetime.now() + timedelta(days=5)),
                            "reason": "Khách bận công tác"}).json()
    lich = detail(cid)["lich_hen"]
    cu = [x for x in lich if x["id"] == ap["id"]][0]
    assert cu["trang_thai"] == "RESCHEDULED"                          # lịch cũ vẫn còn nguyên
    assert new["thay_cho_id"] == ap["id"] and len(lich) == 2

    # Tiêu chí 7: lịch quá giờ chưa cập nhật ⇒ sinh công việc xác minh, KHÔNG tự ghi khách vắng mặt
    qua = client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen", headers=h,
                      json={"starts_at": str(datetime.now() - timedelta(hours=3)),
                            "location": "VFS TP.HCM"}).json()
    cb = client.get("/api/v1/visa/canh-bao", headers=login("tp.dieuhanh")).json()
    assert any(x["lich_hen_id"] == qua["id"] for x in cb["lich_hen_chua_xac_minh"])
    assert "cong_viec_qua_han" in cb and "nguy_co_tre_ngay_di" in cb   # hai loại cảnh báo tách bạch
    assert [x for x in detail(cid)["lich_hen"] if x["id"] == qua["id"]][0]["trang_thai"] == "SCHEDULED"
    assert any(t["loai"] == "xac_minh_lich_hen" for t in detail(cid)["cong_viec"])
    # Ghi khách không đến thì phải nêu căn cứ
    assert client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen/{qua['id']}/sinh-trac-hoc", headers=h,
                       json={"attended": False}).status_code == 422


def test_nghiem_thu_2_va_10_gia_dinh_hai_ket_qua_va_huy_mot_nguoi():
    """Tiêu chí 2: hai thành viên ở hai giai đoạn, hai kết quả. Tiêu chí 10: hủy một người không hủy người còn lại."""
    h = login("tp.dieuhanh")
    g = client.post("/api/v1/visa/nhom-gia-dinh", headers=h,
                    json={"name": "Gia đình Nguyễn", "contact_name": "Nguyễn Văn Cha"}).json()
    cha = _den_buoc_lich_hen("Nguyen Van Cha")
    con = new_case("Nguyen Thi Con", dob=str(date.today().replace(year=date.today().year - 12)))["case"]["id"]
    for cid, vai in ((cha, "duong_don_chinh"), (con, "con")):
        assert client.post(f"/api/v1/visa/nhom-gia-dinh/{g['id']}/thanh-vien", headers=h,
                           json={"case_id": cid, "family_role": vai,
                                 "main": vai == "duong_don_chinh"}).status_code == 200
    # Hai người ở hai giai đoạn khác nhau
    assert detail(cha)["case"]["current_stage"] == "lich_hen"
    assert detail(con)["case"]["current_stage"] == "phan_cong"

    # Cha được cấp, con bị từ chối – kết quả KHÔNG lây sang nhau
    ap = client.post(f"/api/v1/visa/ho-so/{cha}/lich-hen", headers=h,
                     json={"starts_at": str(datetime.now() + timedelta(days=2)), "location": "VFS"}).json()
    client.post(f"/api/v1/visa/ho-so/{cha}/lich-hen/{ap['id']}/sinh-trac-hoc", headers=h, json={"attended": True})
    assert client.post(f"/api/v1/visa/ho-so/{cha}/ket-qua", headers=h,
                       json={"outcome": "GRANTED", "received_on": str(date.today()),
                             "entries": "multiple"}).status_code == 201
    assert detail(cha)["case"]["result_status"] == "GRANTED"
    assert detail(con)["case"]["result_status"] == "NOT_AVAILABLE"

    # Hủy cả nhóm phải xem trước danh sách bị ảnh hưởng; hủy một người không đụng người kia
    xt = client.get(f"/api/v1/visa/nhom-gia-dinh/{g['id']}/xem-truoc-huy", headers=h).json()["thanh_vien"]
    assert len(xt) == 2
    assert client.post(f"/api/v1/visa/ho-so/{con}/huy", headers=h, json={"reason": ""}).status_code == 422
    assert client.post(f"/api/v1/visa/ho-so/{con}/huy", headers=h,
                       json={"reason": "Khách đổi kế hoạch"}).status_code == 200
    assert detail(con)["case"]["lifecycle_status"] == "CANCELLED"
    assert detail(cha)["case"]["lifecycle_status"] == "ACTIVE"        # người còn lại không bị ảnh hưởng


def test_nghiem_thu_11_lien_ket_het_han_va_thu_hoi():
    """Tiêu chí 11: liên kết hết hạn hoặc bị thu hồi thì không truy cập được; mã chỉ lưu dạng băm."""
    from app.db.session import SessionLocal
    from app.services import visa as VS
    cid = new_case("Ho Van Link", dob="1993-08-08")["case"]["id"]
    r = client.post(f"/api/v1/visa/ho-so/{cid}/lien-ket-khach", headers=login("tp.dieuhanh"),
                    json={"scopes": ["view", "upload"], "days": 7})
    assert r.status_code == 201
    raw, lid = r.json()["token"], r.json()["id"]
    db = SessionLocal()
    try:
        assert VS.use_link(db, raw, "upload").id == lid
        with pytest.raises(VS.VisaError):
            VS.use_link(db, raw, "confirm")                # ngoài phạm vi được cấp
        with pytest.raises(VS.VisaError):
            VS.use_link(db, "token-bia-dat", "view")
        from app.models.visa import VisaAccessLink
        assert db.get(VisaAccessLink, lid).token_hash != raw     # CSDL không giữ mã thô
        db.commit()
    finally:
        db.close()
    client.post(f"/api/v1/visa/ho-so/{cid}/lien-ket-khach/{lid}/thu-hoi", headers=login("tp.dieuhanh"))
    db = SessionLocal()
    try:
        with pytest.raises(VS.VisaError):
            VS.use_link(db, raw, "view")                   # đã thu hồi
    finally:
        db.close()


def test_nghiem_thu_12_ai_khong_vuot_quyen():
    """Tiêu chí 12: AI chỉ đề xuất, phải có nguồn, và không tự cập nhật dữ liệu nghiệp vụ."""
    cid = new_case("Ai Test", dob="1994-09-09")["case"]["id"]
    h = login("cntt")
    assert client.post(f"/api/v1/visa/ho-so/{cid}/ai/de-xuat", headers=h,
                       json={"agent": "ai_kiem_tra_tai_lieu", "payload": {"so_ho_chieu": "C1"},
                             "source_ref": ""}).status_code == 422          # thiếu tài liệu nguồn
    s = client.post(f"/api/v1/visa/ho-so/{cid}/ai/de-xuat", headers=h,
                    json={"agent": "ai_kiem_tra_tai_lieu", "target": "form.so_ho_chieu",
                          "payload": {"so_ho_chieu": "C1234567"},
                          "source_ref": "tai_lieu:12 trang 1 dòng 4"}).json()
    assert s["trang_thai"] == "NEW"
    ok = client.post(f"/api/v1/visa/ho-so/{cid}/ai/de-xuat/{s['id']}/quyet-dinh", headers=login("tp.dieuhanh"),
                     json={"accept": True})
    assert ok.status_code == 200 and ok.json()["trang_thai"] == "ACCEPTED"
    # Quyết định hai lần không được
    assert client.post(f"/api/v1/visa/ho-so/{cid}/ai/de-xuat/{s['id']}/quyet-dinh", headers=login("tp.dieuhanh"),
                       json={"accept": False}).status_code == 422


def test_nghiem_thu_13_chi_tieu_dashboard_phan_biet():
    """Tiêu chí 13: dashboard tách hồ sơ cá nhân, hồ sơ thuộc nhóm, và loại hẳn hủy + thử nghiệm."""
    new_case("Du Lieu Thu Nghiem", dob="1995-10-10", is_test=True)
    d = client.get("/api/v1/visa/tong-quan", headers=login("chutich")).json()
    assert "ho_so_ca_nhan_dang_xu_ly" in d and "ho_so_thuoc_nhom_dang_xu_ly" in d and "so_nhom_gia_dinh" in d
    d2 = client.get("/api/v1/visa/tong-quan?include_test=true", headers=login("chutich")).json()
    assert d2["ho_so_ca_nhan_dang_xu_ly"] > d["ho_so_ca_nhan_dang_xu_ly"]     # dữ liệu thử nghiệm bị loại mặc định
    ds = client.get("/api/v1/visa/ho-so", headers=login("chutich")).json()
    assert all(not r["is_test"] for r in ds["rows"])


def test_khong_dat_thang_giai_doan_va_chong_ghi_de():
    """Mục 5.2: không có đường nào nhận thẳng current_stage. Mục 12: xung đột phiên bản báo lỗi, không ghi đè âm thầm."""
    cid = new_case("Nguyen Van Version", dob="1996-11-11")["case"]["id"]
    h = login("tp.dieuhanh")
    c = detail(cid)["case"]
    # Gửi kèm current_stage cũng không đổi được bước
    client.patch(f"/api/v1/visa/ho-so/{cid}", headers=h,
                 json={"row_version": c["row_version"], "current_stage": "dong_ho_so", "visa_type": "X"})
    assert detail(cid)["case"]["current_stage"] == "phan_cong"
    # Sửa bằng phiên bản cũ ⇒ 409, người dùng phải tải lại
    r = client.patch(f"/api/v1/visa/ho-so/{cid}", headers=h,
                     json={"row_version": c["row_version"], "visa_type": "Y"})
    assert r.status_code == 409, r.text
    # Chưa kiểm tra xong thì không khai hồ sơ chính thức được
    assert client.post(f"/api/v1/visa/ho-so/{cid}/khai-ho-so", headers=h,
                       json={"reference_code": "GWF999"}).status_code == 422


def test_dong_ho_so_va_nhat_ky():
    """Đóng hồ sơ chỉ khi đủ kết quả và có xác nhận bàn giao; mọi thao tác đều có trong nhật ký bất biến."""
    cid = _den_buoc_lich_hen("Ket Thuc Ho So")
    h = login("tp.dieuhanh")
    ap = client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen", headers=h,
                     json={"starts_at": str(datetime.now() + timedelta(days=1)), "location": "VFS"}).json()
    client.post(f"/api/v1/visa/ho-so/{cid}/lich-hen/{ap['id']}/sinh-trac-hoc", headers=h, json={"attended": True})
    assert client.post(f"/api/v1/visa/ho-so/{cid}/dong-ho-so", headers=h).status_code == 422   # chưa có kết quả
    client.post(f"/api/v1/visa/ho-so/{cid}/ket-qua", headers=h,
                json={"outcome": "GRANTED", "received_on": str(date.today())})
    assert client.post(f"/api/v1/visa/ho-so/{cid}/dong-ho-so", headers=h).status_code == 422   # chưa trả giấy tờ
    client.post(f"/api/v1/visa/ho-so/{cid}/ban-giao", headers=h,
                json={"direction": "TRA_KHACH", "item_type": "ho_chieu", "to_party": "Khách", "confirmed": True})
    assert client.post(f"/api/v1/visa/ho-so/{cid}/dong-ho-so", headers=h).status_code == 200
    d = detail(cid)
    assert d["case"]["lifecycle_status"] == "CLOSED"
    assert all(t["trang_thai"] in ("done", "cancelled") for t in d["cong_viec"])
    nk = client.get(f"/api/v1/visa/ho-so/{cid}/nhat-ky", headers=h).json()
    acts = {x["action"] for x in nk}
    assert {"visa_tao_ho_so", "visa_ghi_ket_qua", "visa_dong_ho_so"} <= acts
    # Nhật ký kiểm toán toàn hệ thống vẫn liền chuỗi sau khi phân hệ Visa ghi vào
    assert client.get("/api/v1/audit?limit=5", headers=login("chutich")).json()["chain_ok"] is True
    # Hồ sơ đã đóng thì không thao tác nghiệp vụ được nữa
    assert client.post(f"/api/v1/visa/ho-so/{cid}/tam-dung", headers=h,
                       json={"reason": "thử"}).status_code == 422


def test_noi_voi_quy_visa_cua_nhan_su():
    """VTOS đã có bảng visa_files (quỹ visa – Nhân sự). Hồ sơ nghiệp vụ NỐI vào đó, không nhập liệu hai lần."""
    cid = new_case("Noi Quy Visa", dob="1990-01-02")["case"]["id"]
    h = login("tp.dieuhanh")
    hs = client.get("/api/v1/visa", headers=login("hcns")).json()
    assert hs, "seed phải có sẵn hồ sơ quỹ visa của Nhân sự"
    fid = hs[0]["id"]
    assert client.post(f"/api/v1/visa/ho-so/{cid}/noi-quy-visa", headers=h,
                       json={"hr_visa_file_id": fid}).status_code == 200
    assert detail(cid)["quy_visa_nhan_su"] == fid
    # Một bản ghi quỹ visa không nối được cho hai hồ sơ
    cid2 = new_case("Noi Quy Visa Hai", dob="1990-01-03")["case"]["id"]
    assert client.post(f"/api/v1/visa/ho-so/{cid2}/noi-quy-visa", headers=h,
                       json={"hr_visa_file_id": fid}).status_code == 422
    assert client.post(f"/api/v1/visa/ho-so/{cid}/noi-quy-visa", headers=h,
                       json={"hr_visa_file_id": 999999}).status_code == 422


def test_khong_dung_duong_dan_voi_quy_visa_nhan_su():
    """Hai phân hệ cùng dùng tiền tố /api/v1/visa – bảng định tuyến không được có đường nào đè lên nhau."""
    paths = app.openapi()["paths"]
    assert "/api/v1/visa" in paths and "get" in paths["/api/v1/visa"]          # quỹ visa của Nhân sự
    assert "/api/v1/visa/ho-so" in paths                                       # hồ sơ nghiệp vụ Visa
    assert "/api/v1/visa/{vid}/complete" in paths                              # của Nhân sự, 3 cấp – không đè
    # Không có đường nào của phân hệ Visa chỉ đúng hai cấp /api/v1/visa/{tham_so} để tránh nuốt đường của Nhân sự
    for p in paths:
        if p.startswith("/api/v1/visa/") and p.count("/") == 4:
            assert "{" not in p.split("/")[-1], f"đường {p} có thể đè lên /api/v1/visa/{{vid}} của Nhân sự"


def test_phap_nhan_chu_quan_lay_tu_danh_muc_cong_ty():
    """Hồ sơ ghi pháp nhân chủ quản bằng khóa ngoại sang danh mục companies sẵn có, mặc định là công ty mẹ."""
    from app.db.session import SessionLocal
    from app.models.core import Company
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        me = db.execute(sel(Company).where(Company.kind == "me")).scalars().first()
        vt = db.execute(sel(Company).where(Company.code == "VTRIP-VT")).scalars().first()
    finally:
        db.close()
    assert me and vt, "seed phải có danh mục pháp nhân"
    c1 = new_case("Phap Nhan Mac Dinh", dob="1986-01-01")["case"]
    assert c1["company_id"] == me.id                     # không khai thì thuộc công ty mẹ
    c2 = new_case("Phap Nhan Chi Dinh", dob="1986-01-02", company_id=vt.id)["case"]
    assert c2["company_id"] == vt.id
    r = client.post("/api/v1/visa/ho-so", headers=login("tp.dieuhanh"),
                    json={"applicant_name": "Phap Nhan Sai", "market_code": "UK", "company_id": 999999})
    assert r.status_code == 422 and "pháp nhân" in r.json()["detail"]


def test_ban_kiem_soat_chi_doc():
    """Ban Kiểm soát xem được nhưng mọi thao tác ghi bị chặn ở tầng chung của VTOS."""
    cid = new_case("Bks Xem", dob="1997-12-12")["case"]["id"]
    assert client.get(f"/api/v1/visa/ho-so/{cid}", headers=login("bks")).status_code == 200
    r = client.post(f"/api/v1/visa/ho-so/{cid}/tam-dung", headers=login("bks"), json={"reason": "thử"})
    assert r.status_code in (403, 422)
