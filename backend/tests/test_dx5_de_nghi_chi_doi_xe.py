# -*- coding: utf-8 -*-
"""ĐỘI XE v3.3 · đề xuất chi của Giám đốc đội xe đi VÀO Đề nghị chi 05-TT (Chủ tịch chốt 10/11/2026).

Tài liệu v3.3 mục 3: «IT ánh xạ vào các trạng thái đang dùng, không tạo thêm một luồng duyệt song song».
Bộ này canh:
  1. Phiếu là một đề nghị chi `chi_doi_xe` — mã DC…, sổ VTD, bắt đầu ở «Kế toán kiểm» (GĐ gửi = bộ phận
     đã xác nhận), mốc duyệt là mốc chung.
  2. Người lập không tự kiểm / tự ký; GĐ đội xe không nhập ngân hàng.
  3. Tài khoản theo nhóm khoản, khóa lúc lập; lúc chi ghi đúng tài khoản ấy.
  4. Bấm Gửi hai lần cùng chứng từ chỉ ra một phiếu; điều chuyển nội bộ không lập được.
  5. Danh sách của đội xe chỉ đọc ba loại chi của đội xe.
"""
import os
import sys
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///./test_dx5_dncx.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_dx5_dncx.db"):
    os.remove("test_dx5_dncx.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.core import Param  # noqa: E402
from app.models.ops import PaymentRequest  # noqa: E402
from app.services import ops as O  # noqa: E402
from app.services import misa as MS  # noqa: E402
from app.services import rules as R  # noqa: E402

client = TestClient(app)
TOK: dict = {}
CTX: dict = {}
GD = "gd.doixe.dx5"


def login(u: str) -> dict:
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
        from app.models.core import User
        from app.models.hr import Vehicle
        from app.core.security import hash_password
        db = SessionLocal()
        # Chạy chung với tệp khác thì cơ sở dữ liệu là của tệp nạp đầu tiên — dựng sẵn chỉ khi chưa có.
        if db.execute(select(User).where(User.username == GD)).scalars().first() is None:
            db.add(User(username=GD, full_name="GĐ đội xe thử DX5", role="gd_doi_xe", department="doi_xe",
                        staff_code="DX5GD", password_hash=hash_password("Vtos@Demo#2026"), active=True))
        v = db.execute(select(Vehicle)).scalars().first()
        if v is None:
            v = Vehicle(code="XE-DX5", plate="51B-555.55")
            db.add(v)
        for p in db.execute(select(Param).where(Param.key == O.NGUONG_CHU_TICH_KEY,
                                                Param.proposed_by == "phep_thu")).scalars().all():
            db.delete(p)
        db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value="100000000", label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                     effective_from=date(2026, 9, 2), source="phép thử DX5", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="phep_thu"))
        db.commit()
        CTX["bien_so"] = v.plate
        db.close()
        R.clear_param_cache()
        yield


def _lap(nguoi=GD, **kw):
    body = {"so_tien": 6_800_000, "noi_dung": "Thay lốp trước", "nguoi_thu_huong": "Garage Minh Phát",
            "ma_so_thue": "0312345678", "chung_tu": "HD-0001", "pham_vi": "xe", "bien_so": CTX["bien_so"],
            "loai": "thanh_toan", "nhom": "Sửa chữa – bảo dưỡng", "can_cu_so_tien": "Đã gồm thuế / phí theo chứng từ"}
    body.update(kw)
    return client.post("/api/v1/fleet/de-nghi-chi", json=body, headers=login(nguoi))


def _buoc(rid, hanh_dong, nguoi, **kw):
    return client.post(f"/api/v1/payment-requests/{rid}/step", json={"action": hanh_dong, **kw}, headers=login(nguoi))


def test_1_phieu_la_de_nghi_chi_so_vtd_vao_thang_ke_toan():
    r = _lap()
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["code"].startswith("DC") and j["status"] == "cho_duyet"      # Chủ tịch 10/11: lên thẳng Chủ tịch
    db = SessionLocal()
    p = db.get(PaymentRequest, j["id"])
    from app.services.ket_qua_that import cong_ty_me
    assert p.category == "chi_doi_xe" and p.company_id == cong_ty_me(db)
    assert p.doi_xe["tk"] == "627" and p.doi_xe["bien_so"] == CTX["bien_so"]
    assert O.cap_duyet(db, p)["ai"] == "Chủ tịch" and O.vai_ky_duoc(db, p) == ["chutich"]   # mọi mức tiền
    db.close()
    CTX["id"] = j["id"]


def test_2_gui_hai_lan_cung_chung_tu_chi_mot_phieu():
    r = _lap()
    assert r.status_code == 422 and "Đã có phiếu" in r.text
    assert _lap(cho_phep_trung=True).status_code == 201     # khoản khác thật thì vẫn gửi được, có chủ ý


def test_3_gd_doi_xe_khong_nhap_ngan_hang():
    r = _lap(chung_tu="HD-0002", so_tai_khoan="0123456789", ngan_hang="VCB")
    assert r.status_code == 422 and "Kế toán kiểm soát" in r.text


def test_4_dieu_chuyen_noi_bo_khong_lap_duoc():
    r = _lap(chung_tu="HD-0003", nhom="Điều chuyển tiền nội bộ (không phải chi phí)")
    assert r.status_code == 422 and "Điều chuyển" in r.text


def test_5_tai_khoan_theo_nhom():
    assert O.tk_doi_xe("Chi phí chung phân bổ", "thanh_toan") == "627"
    assert O.tk_doi_xe("Quyết toán chủ xe / đối tác", "thanh_toan") == "331"
    assert O.tk_doi_xe("Nạp quỹ / tạm ứng (không phải chi phí)", "thanh_toan") == "141"
    assert O.tk_doi_xe("Sửa chữa – bảo dưỡng", "tam_ung") == "141"          # tạm ứng luôn 141
    assert MS.CATEGORY_ACCOUNT["chi_doi_xe"] == "627" and "chi_doi_xe" not in MS.thieu_tai_khoan()


def test_6_chu_tich_duyet_tgd_khong_duyet_duoc():
    r = _buoc(CTX["id"], "approve", "tgd")
    assert r.status_code == 422 and "Chủ tịch" in r.text
    r = _buoc(CTX["id"], "approve", "chutich")
    assert r.status_code == 200, r.text
    assert r.json()["request"]["status"] == "cho_chi"


def test_7_ke_toan_kiem_chung_tu_luc_chi():
    r = _lap(chung_tu="", ma_so_thue="", so_tien=2_000_000, loai="tam_ung", nhom="Tài xế (công tác phí, lương)",
             nguoi_thu_huong="Tài xế Nguyễn Văn A", pham_vi="doi")
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert _buoc(rid, "approve", "chutich").status_code == 200
    # chưa có chứng từ → Kế toán chưa chi được (kiểm trước UNC)
    r = _buoc(rid, "pay", "ketoan", hinh_thuc_tt="chuyen_khoan")
    assert r.status_code == 422 and "chứng từ" in r.text, r.text
    db = SessionLocal()
    p = db.get(PaymentRequest, rid)
    p.has_document = True
    db.commit()
    assert p.doi_xe["tk"] == "141"
    O._kiem_chung_tu_mst(db, p)            # tạm ứng tài xế: không đòi mã số thuế
    db.close()


def test_8_danh_sach_doi_xe_chi_doc_loai_chi_doi_xe():
    r = client.get("/api/v1/fleet/de-nghi-chi", headers=login(GD))
    assert r.status_code == 200, r.text
    ds = r.json()["de_nghi"]
    assert ds and all(x["loai_chi"] in ("chi_doi_xe", "sua_chua_xe", "tam_ung_tai_xe") for x in ds)
    assert any(x["code"] and x["buoc"].startswith("Chờ") for x in ds)


def test_9_chi_ghi_dung_tai_khoan_da_khoa():
    db = SessionLocal()
    p = db.get(PaymentRequest, CTX["id"])
    p.paid_method = "chuyen_khoan"
    O._post_payment(db, p)
    db.commit()
    from app.models.accounting import JournalLine
    dong = db.execute(select(JournalLine).where(JournalLine.entry_id == p.entry_ids[-1])).scalars().all()
    tk = {d.account_code: (d.debit or 0, d.credit or 0) for d in dong}
    assert tk["627"][0] == p.amount and tk["1121"][1] == p.amount, tk
    db.close()


def test_10_man_bon_buoc_goi_cua_05tt():
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    s = open(os.path.join(goc, "web", "components", "doixe", "BonBuocDeXuatChi.tsx"), encoding="utf-8").read()
    assert '"/fleet/de-nghi-chi"' in s and '"/fleet/de-xuat-chi"' not in s


# ── phần 2: giao diện /xe theo demo v3.3 (Chủ tịch duyệt bản xem trước 10/11/2026) ─────────────────
def _web(*p):
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return open(os.path.join(goc, "web", *p), encoding="utf-8").read()


def test_11_noi_dung_doi_tai_cho_va_bo_muc_luc():
    s = _web("app", "xe", "page.tsx")
    assert "Đợt này nối lối đi, chưa dựng màn mới" not in s           # thẻ «Mở … →» đã thay bằng nội dung tại chỗ
    assert "<KhungNhung" in s and "<DeXuatChiTaiCho" in s
    assert "TrangPhanHe" not in s                                       # khối mục lục «04 Điều hành xe» đã gỡ
    assert "Quyền của tôi" in s and "Số tiền theo" in s
    # VH-7 (Chủ tịch duyệt 11/11/2026): /xe thu gọn tối đa 1180px canh giữa như màn Nhà hàng / Khách sạn.
    assert "main{max-width:1180px!important;margin:0 auto!important}" in s and "vtos-nhung" in s


def test_12_o_so_theo_v33():
    k = _web("components", "KhoiV14.tsx")
    assert "Chưa khớp" in k and '"Lợi nhuận tạm tính"' in k
    from app.services import hieu_qua_xe as HQ
    import inspect
    assert 'tong.get("ngay_khai_thac_ghi_nhan"' in inspect.getsource(HQ.chi_so)   # công suất: mọi chuyến ghi nhận
