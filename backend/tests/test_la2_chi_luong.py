"""Đợt A2 — Kế toán CHI, Ủy nhiệm chi, đối chiếu, ghi nhận ĐÃ TRẢ (Chủ tịch chốt 07/10/2026).

  A. Thứ tự: chưa ký thì không chi được; chi gắn vào BẢN KHÓA chứ không vào kỳ.
  B. Lệnh cấm 08/9 còn nguyên, ngoại lệ 07/10 hẹp đúng hai trường và có chữ ký.
  C. Đối chiếu ra đủ / một phần / lỗi bằng quy tắc xác định, chạy lại ra cùng kết luận.
  D. K2 — máy không đọc được số tiền thì ô RỖNG, không phải 0, và chưa kết luận được.
  E. Chuẩn hoá tên: phụ lục ngân hàng in tên không dấu, hồ sơ nhân sự lưu tên có dấu.
  F. Trạng thái trả tiền của cả kỳ cộng từ các lần chi, không ai gõ tay vào được.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_la2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_la2.db"):
    os.remove("test_la2.db")

import pytest
from tests.cong_da_duyet import duyet_cong
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
P = f"{date.today() - timedelta(days=14):%Y-%m}"


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _ky_xong():
    """Đưa kỳ P qua hết chuỗi A1 để có một bản khóa thật mà đối chiếu."""
    client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns"))
    duyet_cong(client, P, login)   # CN-1: công chưa duyệt thì kiểm cơ sở chặn
    client.post(f"/api/v1/payroll-runs/{P}/kiem-co-so", headers=login("hcns"))
    client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("hcns"))
    client.post(f"/api/v1/payroll-runs/{P}/advance", headers=login("chutich"))


def _ban():
    from app.db.session import SessionLocal
    from app.services import luong_khoa as LK
    with SessionLocal() as db:
        b = LK.ban_dang_hieu_luc(db, P)
        return {"rows": (b.noi_dung or {}).get("rows") or [],
                "tong": float(((b.noi_dung or {}).get("totals") or {}).get("thuc_nhan") or 0)}


def _dat(lan: int, so_tien, dong=None, ngay=None):
    """Đặt thẳng số liệu của một lần chi như thể người đã sửa xong chỗ máy đọc sai.

    Không gọi cửa tải tệp vì ở đây không có khoá mô hình, và vì phép thử này kiểm PHÉP ĐỐI CHIẾU
    chứ không kiểm chất lượng máy đọc — hai việc hỏng vì hai lý do khác nhau thì phải đỏ riêng.
    """
    body = {"so_tien_unc": so_tien, "ngay_chuyen": str(ngay or date.today())}
    if dong is not None:
        body["dong_phu_luc"] = dong
    r = client.put(f"/api/v1/payroll-runs/{P}/chi/{lan}", json=body, headers=login("ketoan"))
    assert r.status_code == 200, r.text
    return r.json()["chi"]


def _mo_lan():
    r = client.post(f"/api/v1/payroll-runs/{P}/chi", headers=login("ketoan"))
    assert r.status_code == 201, r.text
    return r.json()["chi"]["lan"]


def _doi_chieu(lan):
    return client.post(f"/api/v1/payroll-runs/{P}/chi/{lan}/doi-chieu", headers=login("ketoan"))


# ───────────────────── A · thứ tự ─────────────────────
def test_a1_chua_ky_thi_khong_chi_duoc():
    ky_sau = f"{date.today() + timedelta(days=40):%Y-%m}"
    client.get(f"/api/v1/payroll-runs/{ky_sau}", headers=login("hcns"))
    r = client.post(f"/api/v1/payroll-runs/{ky_sau}/chi", headers=login("ketoan"))
    assert r.status_code == 422
    assert "chưa được ký" in r.json()["detail"], \
        "phải nói ra là THIẾU CHỮ KÝ, không chỉ nói sai trạng thái"


def test_a2_hcns_khong_mo_duoc_lan_chi():
    _ky_xong()
    r = client.post(f"/api/v1/payroll-runs/{P}/chi", headers=login("hcns"))
    assert r.status_code == 403, "chi tiền là việc của kế toán, không phải của người lập bảng"


def test_a3_lan_chi_gan_vao_ban_khoa_khong_gan_vao_ky():
    from app.db.session import SessionLocal
    from app.services import luong_khoa as LK
    lan = _mo_lan()
    with SessionLocal() as db:
        from app.models.chi_luong import ChiKyLuong
        from sqlalchemy import select
        c = db.execute(select(ChiKyLuong).where(ChiKyLuong.period == P,
                                                ChiKyLuong.lan == lan)).scalars().first()
        b = LK.ban_dang_hieu_luc(db, P)
        assert c.ban_khoa_id == b.id, \
            "gắn vào kỳ thì kết luận 'đã trả đủ' hôm nay tự đổi khi kỳ được tính lại"


# ───────────────────── B · lệnh cấm và ngoại lệ ─────────────────────
def test_b1_lenh_cam_08_9_con_nguyen():
    from app.models.doc_chung_tu import CAM_DOC_BANG_MAY, LOAI_CHUNG_TU
    assert set(CAM_DOC_BANG_MAY) == {"bang_luong", "bang_bao_hiem"}, \
        "ngoại lệ 07/10 chỉ mở cho PHỤ LỤC UNC – không được nới lệnh cấm gốc"
    assert not (set(CAM_DOC_BANG_MAY) & set(LOAI_CHUNG_TU))


def test_b2_moi_ngoai_le_phai_co_chu_ky_va_pham_vi_hep():
    from app.models.doc_chung_tu import MO_DOC_CO_CHU_KY
    assert MO_DOC_CO_CHU_KY, "mở ngoại lệ mà không khai ở đây là mở bằng một công tắc"
    for ma, n in MO_DOC_CO_CHU_KY.items():
        assert n.get("nguoi_ky"), f"{ma}: ngoại lệ không có tên người ký là ngoại lệ không ai nhận"
        assert n.get("ngay_ky"), f"{ma}: thiếu ngày ký"
        assert len(n.get("ly_do", "")) >= 80, \
            f"{ma}: lý do quá ngắn – ngoại lệ về dữ liệu cá nhân phải giải thích được bằng văn"
        assert n.get("truong"), f"{ma}: không khai trường nào được đọc"
        assert not (set(n["truong"]) & set(n.get("cam_truong", ()))), \
            f"{ma}: một trường vừa được đọc vừa bị cấm – bảng khai tự mâu thuẫn"


def test_b3_phu_luc_chi_duoc_doc_ho_ten_va_so_tien():
    from app.models.doc_chung_tu import MO_DOC_CO_CHU_KY
    n = MO_DOC_CO_CHU_KY["phu_luc_unc_luong"]
    assert tuple(n["truong"]) == ("ho_ten", "so_tien")
    for x in ("so_tai_khoan", "luong_cb", "bhxh", "tncn", "cccd", "ngay_sinh"):
        assert x in n["cam_truong"], f"'{x}' phải nằm trong danh sách cấm"


def test_b4_mo_hinh_tra_ve_so_tai_khoan_thi_bi_bo():
    from app.services.chi_luong import _loc_phu_luc
    dong, da_bo = _loc_phu_luc({"dong": [
        {"ho_ten": "Nguyen Van A", "so_tien": "5000000", "so_tai_khoan": "0123456789",
         "cccd": "079...", "bhxh": "400000"}]})
    assert dong == [{"ho_ten": "Nguyen Van A", "so_tien": 5000000.0}]
    assert "so_tai_khoan" in da_bo and "cccd" in da_bo, \
        "bỏ cái gì thì phải nói ra – im lặng bỏ là không kiểm được rằng đã bỏ"


def test_b5_cua_sua_tay_cung_loc_dung_hai_truong():
    lan = _mo_lan()
    r = client.put(f"/api/v1/payroll-runs/{P}/chi/{lan}",
                   json={"dong_phu_luc": [{"ho_ten": "X", "so_tien": 1, "so_tai_khoan": "999"}]},
                   headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()["chi"]["dong_phu_luc"][0]
    assert set(d) == {"ho_ten", "so_tien"}, \
        "cửa nhập tay rộng hơn cửa máy đọc thì lệnh cấm chỉ còn cấm được cái máy"


# ───────────────────── C · đối chiếu ─────────────────────
def test_c1_tong_khop_va_tung_nguoi_khop_thi_da_tra_du():
    b = _ban()
    lan = _mo_lan()
    _dat(lan, b["tong"], [{"ho_ten": r["ten"], "so_tien": r["thuc_nhan"]} for r in b["rows"]])
    d = _doi_chieu(lan).json()
    assert d["ket_luan"] == "du", d["ket_qua"]["ly_do"]
    assert d["tra_trang_thai"] == "da_tra_du"


def test_c2_chay_lai_ra_cung_ket_luan():
    """Cùng dữ liệu phải ra cùng kết luận. Không có điều này thì không ai dám dùng nó để trả tiền."""
    from app.db.session import SessionLocal
    from app.models.chi_luong import ChiKyLuong
    from app.models.luong_khoa import BangLuongKhoa
    from app.services import chi_luong as CL
    from sqlalchemy import select
    with SessionLocal() as db:
        c = db.execute(select(ChiKyLuong).where(ChiKyLuong.period == P)
                       .order_by(ChiKyLuong.lan)).scalars().first()
        ban = db.get(BangLuongKhoa, c.ban_khoa_id)
        a = CL.doi_chieu(db, c, ban)
        bb = CL.doi_chieu(db, c, ban)
    assert a["ket_luan"] == bb["ket_luan"] and a["ly_do"] == bb["ly_do"]


def test_c3_thieu_mot_nguoi_thi_la_mot_phan():
    b = _ban()
    assert len(b["rows"]) >= 2
    bo = b["rows"][0]
    con = b["rows"][1:]
    lan = _mo_lan()
    _dat(lan, b["tong"] - float(bo["thuc_nhan"] or 0),
         [{"ho_ten": r["ten"], "so_tien": r["thuc_nhan"]} for r in con])
    d = _doi_chieu(lan).json()
    assert d["ket_luan"] == "mot_phan", d["ket_qua"]["ly_do"]
    thieu = d["ket_qua"]["tung_nguoi"]["thieu"]
    assert [x["ma_nv"] for x in thieu] == [bo["ma"]], \
        "phải chỉ đích danh ai chưa nhận, không chỉ nói 'còn thiếu'"


def test_c4_phu_luc_co_nguoi_la_thi_la_loi():
    b = _ban()
    lan = _mo_lan()
    _dat(lan, b["tong"] + 1000,
         [{"ho_ten": r["ten"], "so_tien": r["thuc_nhan"]} for r in b["rows"]]
         + [{"ho_ten": "Nguoi La Khong Co Trong Bang", "so_tien": 1000}])
    d = _doi_chieu(lan).json()
    assert d["ket_luan"] == "loi", d["ket_qua"]["ly_do"]


def test_c5_chuyen_thua_thi_la_loi_khong_phai_mot_phan():
    b = _ban()
    lan = _mo_lan()
    _dat(lan, b["tong"] + 5_000_000)
    d = _doi_chieu(lan).json()
    assert d["ket_luan"] == "loi", \
        "trả thừa gọi là 'một phần' thì nó nằm chung hàng chờ với việc bình thường"


def test_c6_khong_co_phu_luc_thi_ket_luan_phai_noi_ro_chi_o_muc_tong():
    b = _ban()
    lan = _mo_lan()
    _dat(lan, b["tong"])
    d = _doi_chieu(lan).json()
    assert d["ket_luan"] == "du"
    assert "phụ lục" in d["ket_qua"]["ly_do"], \
        "tổng khớp vẫn có thể một người thừa một người thiếu – câu ấy phải nằm trong kết luận"


def test_c7_trung_ten_thi_khong_doan():
    from app.services.chi_luong import chuan_ten
    from app.db.session import SessionLocal
    from app.models.chi_luong import ChiKyLuong
    from app.models.luong_khoa import BangLuongKhoa
    from app.services import chi_luong as CL
    from sqlalchemy import select
    b = _ban()
    ten = b["rows"][0]["ten"]
    with SessionLocal() as db:
        ban = BangLuongKhoa(period="1900-01", ban_so=1, dau_van_tay="x",
                            noi_dung={"rows": [{"ma": "A1", "ten": ten, "thuc_nhan": 100},
                                               {"ma": "A2", "ten": ten, "thuc_nhan": 100}],
                                      "totals": {"thuc_nhan": 200}}, quy_tac={})
        db.add(ban); db.flush()
        c = ChiKyLuong(period="1900-01", ban_khoa_id=ban.id, lan=1, so_tien_unc=200,
                       dong_phu_luc=[{"ho_ten": chuan_ten(ten), "so_tien": 100}])
        db.add(c); db.flush()
        kq = CL.doi_chieu(db, c, ban)
        db.rollback()
    assert kq["ket_luan"] == "loi"
    assert kq["tung_nguoi"]["nhap_nhang"], \
        "đoán sai ở đây là báo 'đã trả' cho người chưa nhận tiền, và họ không có cách nào biết"


# ───────────────────── D · K2 rỗng ≠ 0 ─────────────────────
def test_d1_may_khong_doc_duoc_so_tien_thi_chua_ket_luan_duoc():
    from app.services.chi_luong import _so
    assert _so("") is None and _so(None) is None, "rỗng phải là rỗng, không phải 0"
    assert _so("0") == 0.0, "0 người gõ vào vẫn là 0 – chỉ chỗ KHÔNG ĐỌC ĐƯỢC mới là rỗng"
    lan = _mo_lan()
    r = _doi_chieu(lan)
    assert r.status_code == 422
    assert "Ủy nhiệm chi" in r.json()["detail"]


def test_d2_khong_co_cua_nao_cho_nguoi_go_ket_luan():
    lan_moi = _mo_lan()
    r = client.put(f"/api/v1/payroll-runs/{P}/chi/{lan_moi}",
                   json={"ket_luan": "du", "so_tien_unc": 1},
                   headers=login("ketoan"))
    assert r.status_code == 200, r.text
    assert r.json()["chi"]["ket_luan"] == "", \
        "một ô cho người gõ 'đã trả đủ' biến cả chuỗi này thành một lời khai"


# ───────────────────── E · chuẩn hoá tên ─────────────────────
def test_e1_ten_khong_dau_cua_ngan_hang_van_khop_ho_so():
    from app.services.chi_luong import chuan_ten
    assert chuan_ten("Nguyễn Tất Thắng") == chuan_ten("NGUYEN  TAT THANG ")
    assert chuan_ten("Đặng Thị Đào") == "DANG THI DAO"


# ───────────────────── F · trạng thái cả kỳ ─────────────────────
def test_f1_trang_thai_ky_cong_tu_cac_lan_chi_khong_ai_go_tay():
    from app.services.ks_cua_nhap import CUA_TAY, MAY_SINH
    assert "chi_ky_luong" in CUA_TAY, "bảng không có cửa là việc còn thiếu"
    assert "chi_ky_luong" not in MAY_SINH
    d = client.get(f"/api/v1/payroll-runs/{P}/chi", headers=login("ketoan")).json()
    assert d["tra_trang_thai"] in ("dang_chi", "da_tra_du", "loi_chi")
    assert len(d["lan_chi"]) >= 3
