"""Hồ sơ kiểm toán – V7 Đợt 3 (10/9/2026).

Đây là hồ sơ GIAO CHO KIỂM TOÁN VIÊN, khác hẳn nhật ký nghiệp vụ `audit_log`. Hai thứ hay bị gọi chung
một tên, nên phép thử đầu tiên canh đúng chỗ ấy.

  A1  ba bảng mới tách hẳn khỏi audit_log, và không bảng nào giữ một con số tiền
  A2  một pháp nhân – một kỳ – một loại thì chỉ MỘT hồ sơ
  A3  lập hồ sơ nạp sẵn danh mục mẫu; nạp lại lần hai không nhân đôi
  A4  còn mục chưa gửi thì KHÔNG phát hành được
  A5  "không áp dụng cho kỳ này" phải có lý do
  A6  ý kiến khác 'chấp nhận toàn phần' bắt buộc ghi cơ sở của ý kiến
  A7  điều chỉnh đánh dấu 'đã ghi sổ' phải kèm số hiệu bút toán CÓ THẬT
  A8  không đồng ý với điều chỉnh phải nêu lý do
  A9  còn điều chỉnh chưa quyết thì chưa đóng được hồ sơ
  A10 số tệp của một mục đếm SỐNG từ kho tệp chung, không lưu thành cột
  A11 màn hình nhật ký nghiệp vụ vẫn CHỈ ĐỌC – không có đường ghi nào ở /api/v1/audit
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_v7_kt.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_v7_kt.db", "test_v7_kt.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app); TOK = {}


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "123456"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c; yield


def lap(ky, loai="soat_xet", **kw):
    d = {"ky": ky, "loai": loai, "don_vi_kiem_toan": "Baker Tilly A&C",
         "han_hoan_thanh": str(date.today() + timedelta(days=20))}
    d.update(kw)
    r = client.post("/api/v1/kiem-toan", json=d, headers=login("cntt"))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def xong_het_muc(hid):
    """Đánh dấu mọi mục đã gửi, để tới được bước phát hành."""
    h = login("cntt")
    hs = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()
    for m in hs["muc"]:
        client.patch(f"/api/v1/kiem-toan/muc/{m['id']}", json={"trang_thai": "da_gui"}, headers=h)


# ------------------------------------------------------------------ A1
def test_a1_tach_han_khoi_nhat_ky_nghiep_vu_va_khong_co_cot_tien():
    from sqlalchemy import Numeric, Float
    from app.models.kiem_toan import HoSoKiemToan, HoSoKiemToanMuc, HoSoKiemToanDieuChinh
    from app.models.core import AuditLog
    assert AuditLog.__tablename__ == "audit_log"
    for bang in (HoSoKiemToan, HoSoKiemToanMuc, HoSoKiemToanDieuChinh):
        assert bang.__tablename__ != "audit_log"
        for c in bang.__table__.columns:
            assert not isinstance(c.type, (Numeric, Float)), (
                f"{bang.__tablename__}.{c.name} là cột số thực – bút toán điều chỉnh nằm ở sổ, bảng "
                "này chỉ giữ số hiệu")
            assert "so_tien" not in c.name and "amount" not in c.name, f"{bang.__tablename__}.{c.name}"
    # Chân nối sang sổ phải có, và phải rỗng được: chưa ghi sổ thì chưa có số hiệu.
    assert HoSoKiemToanDieuChinh.__table__.columns["journal_entry_id"].nullable


# ------------------------------------------------------------------ A2, A3
def test_a2_mot_phap_nhan_mot_ky_mot_loai_chi_mot_ho_so():
    lap("2030H1")
    r = client.post("/api/v1/kiem-toan",
                    json={"ky": "2030H1", "loai": "soat_xet", "don_vi_kiem_toan": "Đơn vị khác"},
                    headers=login("cntt"))
    assert r.status_code == 422 and "đã có hồ sơ" in r.text.lower()
    # Khác LOẠI thì là hồ sơ khác – soát xét bán niên và kiểm toán năm không phải một việc.
    r2 = client.post("/api/v1/kiem-toan",
                     json={"ky": "2030H1", "loai": "kiem_toan_nam", "don_vi_kiem_toan": "Baker Tilly A&C"},
                     headers=login("cntt"))
    assert r2.status_code == 200, r2.text


def test_a3_danh_muc_mau_nap_san_va_khong_nhan_doi_khi_nap_lai():
    from app.services.kiem_toan import MAU_DANH_MUC
    hid = lap("2030Q1")
    h = login("cntt")
    hs = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()
    assert hs["tong_muc"] == len(MAU_DANH_MUC)
    assert client.post(f"/api/v1/kiem-toan/{hid}/danh-muc-mau", headers=h).status_code == 200
    lai = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()
    assert lai["tong_muc"] == len(MAU_DANH_MUC), "nạp lại danh mục mẫu không được nhân đôi"
    # Mục thêm tay vẫn được – kiểm toán mỗi kỳ hỏi thêm những thứ khác nhau.
    assert client.post(f"/api/v1/kiem-toan/{hid}/muc",
                       json={"ten": "Bảng kê chi tiết doanh thu theo tuyến"},
                       headers=h).status_code == 200
    assert client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()["tong_muc"] == len(MAU_DANH_MUC) + 1


# ------------------------------------------------------------------ A4, A5, A6
def test_a4_con_muc_chua_gui_thi_khong_phat_hanh_duoc():
    hid = lap("2030Q2")
    h = login("cntt")
    for tt in ("dang_cung_cap", "dang_soat_xet", "co_y_kien"):
        assert client.post(f"/api/v1/kiem-toan/{hid}/chuyen", json={"trang_thai": tt},
                           headers=h).status_code == 200
    r = client.post(f"/api/v1/kiem-toan/{hid}/chuyen",
                    json={"trang_thai": "da_phat_hanh", "loai_y_kien": "chap_nhan_toan_phan",
                          "so_bao_cao": "4.0299/26/TC-AC"}, headers=h)
    assert r.status_code == 422 and "chưa cung cấp xong" in r.text
    xong_het_muc(hid)
    ok = client.post(f"/api/v1/kiem-toan/{hid}/chuyen",
                     json={"trang_thai": "da_phat_hanh", "loai_y_kien": "chap_nhan_toan_phan",
                           "so_bao_cao": "4.0299/26/TC-AC"}, headers=h)
    assert ok.status_code == 200, ok.text
    hs = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()
    assert hs["trang_thai"] == "da_phat_hanh" and hs["ngay_bao_cao"]


def test_a5_khong_ap_dung_cho_ky_nay_phai_co_ly_do():
    hid = lap("2030Q3")
    h = login("cntt")
    m = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()["muc"][0]
    r = client.patch(f"/api/v1/kiem-toan/muc/{m['id']}", json={"trang_thai": "khong_can"}, headers=h)
    assert r.status_code == 422, "đây là lối thoát dễ nhất cho một mục thiếu – phải tốn một câu giải thích"
    ok = client.patch(f"/api/v1/kiem-toan/muc/{m['id']}",
                      json={"trang_thai": "khong_can", "ghi_chu": "Kỳ này không phát sinh khoản mục này"},
                      headers=h)
    assert ok.status_code == 200
    # Mục đánh dấu không áp dụng thì không còn tính là "còn thiếu".
    hs = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()
    assert all(x["trang_thai"] != "khong_can" or not x["tre_han"] for x in hs["muc"])


def test_a6_y_kien_khac_chap_nhan_toan_phan_phai_ghi_co_so():
    hid = lap("2030Q4")
    h = login("cntt")
    for tt in ("dang_cung_cap", "dang_soat_xet", "co_y_kien"):
        client.post(f"/api/v1/kiem-toan/{hid}/chuyen", json={"trang_thai": tt}, headers=h)
    xong_het_muc(hid)
    thieu = client.post(f"/api/v1/kiem-toan/{hid}/chuyen",
                        json={"trang_thai": "da_phat_hanh", "loai_y_kien": "ngoai_tru",
                              "so_bao_cao": "4.0300/26/TC-AC"}, headers=h)
    assert thieu.status_code == 422, (
        "công ty đại chúng công bố ý kiến ngoại trừ mà không nói ngoại trừ cái gì là công bố thiếu")
    ok = client.post(f"/api/v1/kiem-toan/{hid}/chuyen",
                     json={"trang_thai": "da_phat_hanh", "loai_y_kien": "ngoai_tru",
                           "so_bao_cao": "4.0300/26/TC-AC",
                           "van_de_nhan_manh": "Chưa thu thập đủ bằng chứng về khoản phải thu quá hạn tại TK 131"},
                     headers=h)
    assert ok.status_code == 200, ok.text
    # Thiếu số báo cáo cũng không phát hành được.
    hid2 = lap("2031H1")
    for tt in ("dang_cung_cap", "dang_soat_xet", "co_y_kien"):
        client.post(f"/api/v1/kiem-toan/{hid2}/chuyen", json={"trang_thai": tt}, headers=h)
    xong_het_muc(hid2)
    assert client.post(f"/api/v1/kiem-toan/{hid2}/chuyen",
                       json={"trang_thai": "da_phat_hanh", "loai_y_kien": "chap_nhan_toan_phan",
                             "so_bao_cao": ""}, headers=h).status_code == 422


# ------------------------------------------------------------------ A7, A8, A9
def test_a7_a8_a9_dieu_chinh_phai_quyet_xong_moi_dong_duoc_ho_so():
    hid = lap("2031Q1")
    h = login("cntt")
    r = client.post(f"/api/v1/kiem-toan/{hid}/dieu-chinh",
                    json={"noi_dung": "Trích trước chi phí hướng dẫn viên tháng 6 chưa ghi nhận"},
                    headers=h)
    assert r.status_code == 200
    did = r.json()["id"]

    # A7 – 'đã ghi sổ' mà không có số hiệu bút toán thì chặn; số hiệu không có thật cũng chặn.
    assert client.post(f"/api/v1/kiem-toan/dieu-chinh/{did}/quyet",
                       json={"trang_thai": "da_ghi_so"}, headers=h).status_code == 422
    assert client.post(f"/api/v1/kiem-toan/dieu-chinh/{did}/quyet",
                       json={"trang_thai": "da_ghi_so", "journal_entry_id": 999_999},
                       headers=h).status_code == 422

    # A8 – không đồng ý thì phải nêu lý do.
    assert client.post(f"/api/v1/kiem-toan/dieu-chinh/{did}/quyet",
                       json={"trang_thai": "khong_dong_y", "ly_do": "không"},
                       headers=h).status_code == 422

    # A9 – còn điều chỉnh chưa quyết thì chưa đóng được hồ sơ.
    for tt in ("dang_cung_cap", "dang_soat_xet", "co_y_kien"):
        client.post(f"/api/v1/kiem-toan/{hid}/chuyen", json={"trang_thai": tt}, headers=h)
    xong_het_muc(hid)
    client.post(f"/api/v1/kiem-toan/{hid}/chuyen",
                json={"trang_thai": "da_phat_hanh", "loai_y_kien": "chap_nhan_toan_phan",
                      "so_bao_cao": "4.0301/26/TC-AC"}, headers=h)
    chua = client.post(f"/api/v1/kiem-toan/{hid}/chuyen", json={"trang_thai": "dong"}, headers=h)
    assert chua.status_code == 422 and "chưa quyết" in chua.text

    ok = client.post(f"/api/v1/kiem-toan/dieu-chinh/{did}/quyet",
                     json={"trang_thai": "khong_dong_y",
                           "ly_do": "Chi phí này đã nằm trong dự toán chuyến và ghi ở kỳ sau theo quy ước hạch toán"},
                     headers=h)
    assert ok.status_code == 200, ok.text
    assert client.post(f"/api/v1/kiem-toan/{hid}/chuyen", json={"trang_thai": "dong"},
                       headers=h).status_code == 200


def test_a7b_so_hieu_but_toan_co_that_thi_ghi_duoc():
    """Chiều ngược lại của A7: có bút toán thật thì đánh dấu 'đã ghi sổ' phải qua, và số hiệu nằm lại."""
    from app.db.session import SessionLocal
    from app.models.accounting import JournalEntry
    from sqlalchemy import select
    with SessionLocal() as db:
        je = db.execute(select(JournalEntry)).scalars().first()
        if je is None:
            # Dựng một chứng từ để phép thử không tự bỏ qua chính mình khi dữ liệu mẫu thiếu. Một
            # phép thử chỉ chạy lúc may mắn thì không canh được gì.
            je = JournalEntry(code="CTKT-9001", entry_date=date.today(),
                              period=f"{date.today():%Y-%m}",
                              description="Điều chỉnh sau soát xét (dựng cho phép thử)",
                              source_type="thu_cong", created_by="cntt")
            db.add(je); db.commit()
        je_id = je.id
    hid = lap("2031Q2")
    h = login("cntt")
    did = client.post(f"/api/v1/kiem-toan/{hid}/dieu-chinh",
                      json={"noi_dung": "Phân loại lại khoản trả trước người bán"}, headers=h).json()["id"]
    r = client.post(f"/api/v1/kiem-toan/dieu-chinh/{did}/quyet",
                    json={"trang_thai": "da_ghi_so", "journal_entry_id": je_id}, headers=h)
    assert r.status_code == 200, r.text
    dc = client.get(f"/api/v1/kiem-toan/{hid}", headers=h).json()["dieu_chinh"][0]
    assert dc["journal_entry_id"] == je_id and dc["trang_thai"] == "da_ghi_so"


# ------------------------------------------------------------------ A10
def test_a10_so_tep_dem_song_tu_kho_tep_chung():
    """Lưu thành cột thì mỗi lần ai đó gỡ một tệp là con số sai, và không ai nhớ chạy lại phép đếm."""
    from app.models.kiem_toan import HoSoKiemToanMuc
    from app.models.attachments import DOI_TUONG_DAY_DU
    assert "so_tep" not in HoSoKiemToanMuc.__table__.columns.keys()
    # Có cửa đính kèm thật, và nó rơi đúng nhóm hồ sơ 08_Kiem_toan.
    assert "ho_so_kiem_toan_muc" in DOI_TUONG_DAY_DU
    assert DOI_TUONG_DAY_DU["ho_so_kiem_toan_muc"][2] == "08_Kiem_toan"
    hid = lap("2031Q3")
    m = client.get(f"/api/v1/kiem-toan/{hid}", headers=login("cntt")).json()["muc"][0]
    assert m["so_tep"] == 0


# ------------------------------------------------------------------ A11
def test_a11_nhat_ky_nghiep_vu_van_chi_doc():
    """Nhật ký là tấm gương. Có đường ghi ở đó thì nhật ký thôi là nhật ký.

    Bộ lọc thêm cùng đợt này đều là GET; phép thử canh để không ai nhân tiện mở một đường ghi.
    """
    duong = [r for r in app.routes if getattr(r, "path", "").startswith("/api/v1/audit")]
    assert duong, "phải còn đường đọc nhật ký"
    for r in duong:
        assert set(r.methods) <= {"GET", "HEAD", "OPTIONS"}, f"{r.path} mở phương thức ghi: {r.methods}"
    h = login("cntt")
    d = client.get("/api/v1/audit?limit=5", headers=h).json()
    assert "danh_muc" in d and set(d["danh_muc"]) == {"actor", "action", "entity"}
    assert d["chain_ok"] is True, d["chain_message"]
    # Lọc chạy ở MÁY CHỦ: lọc theo một hành động không tồn tại phải trả về rỗng, không trả cả sổ.
    assert client.get("/api/v1/audit?action=khong_co_hanh_dong_nay", headers=h).json()["rows"] == []
    # Đối tượng lọc theo tiền tố: gõ phân hệ ra cả phân hệ.
    if d["danh_muc"]["entity"]:
        tt = d["danh_muc"]["entity"][0]
        assert all(x["entity"].startswith(tt)
                   for x in client.get(f"/api/v1/audit?entity={tt}&limit=50", headers=h).json()["rows"])
    # Mốc thời gian sai dạng thì báo rõ, không lặng lẽ bỏ qua bộ lọc.
    assert client.get("/api/v1/audit?tu=hom-qua", headers=h).status_code == 422
