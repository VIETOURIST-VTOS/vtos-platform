# -*- coding: utf-8 -*-
"""VH-1 · CHẠY THỬ TRỌN LUỒNG MỘT CHUYẾN XE — đúng vai, đúng cửa (Chủ tịch giao 10/11/2026, chuẩn bị vào vận hành).

Mỗi bước gọi CỬA HTTP thật bằng tài khoản của đúng vai, như người dùng bấm trên màn hình:

  1. Điều hành tour (nv_dh)   ĐỀ NGHỊ XE cho tour
  2. GĐ đội xe (gd_doi_xe)    LẬP LỆNH điều xe từ đề nghị ấy
  3. Tài xế (tai_xe)          NHẬN LỆNH trên màn /xe-hdv
  4. GĐ đội xe                NHẬP BÁO CÁO XE (cửa bốn bước: phiếu chuyến + chi phí), chưa vào lợi nhuận
  5. GĐ đội xe                GỬI tờ báo cáo xe
  6. Chủ tịch                 DUYỆT → chuyến vào lợi nhuận kỳ
  7. Kế toán                  CHI (ký bước cuối)
  8. GĐ đội xe                ĐỀ XUẤT CHI cho khoản gốc của chuyến → Chủ tịch duyệt → Kế toán chi có UNC
  9. Màn gọn /xe đọc đúng trạng thái ở từng bước.
"""
import os
import sys
import tempfile
from datetime import date, timedelta

_DB = os.path.join(tempfile.gettempdir(), "vtos_test_vh1.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB):
        os.remove(_DB)
except OSError:
    pass

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

PW = "Vtos@Demo#2026"
TOK: dict = {}
CTX: dict = {}
client: TestClient


def h(u: str) -> dict:
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": PW})
        assert r.status_code == 200, f"{u}: {r.text}"
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    global client
    with TestClient(app) as c:
        client = c
        from app.core.security import hash_password
        from app.models.core import Param, Tour, User
        from app.models.hr import Employee, Vehicle
        from app.services import ops as O
        from app.services import rules as R
        db = SessionLocal()
        gd = User(username="vh1.gdxe", full_name="GĐ đội xe VH1", role="gd_doi_xe", department="doi_xe",
                  staff_code="VH1GD", password_hash=hash_password(PW), active=True)
        tx = User(username="vh1.taixe", full_name="Lý Văn Sơn (tài xế)", role="tai_xe", department="doi_xe",
                  staff_code="VH1TX", password_hash=hash_password(PW), active=True)
        db.add_all([gd, tx]); db.flush()
        e = db.execute(select(Employee).where(Employee.full_name.like("Lý Văn Sơn%"))).scalars().first()
        e.user_id = tx.id
        v = db.execute(select(Vehicle).where(Vehicle.driver_id == e.id)).scalars().first()
        di = date.today() + timedelta(days=3)
        t = Tour(code="VH1-TOUR", name="Đà Lạt 3N2Đ (chạy thử VH1)", tour_type="doan_noi_dia", start_date=di, end_date=di + timedelta(days=2),
                 status="da_duyet", operator_id=db.execute(select(User).where(User.username == "dh.lan")).scalars().first().id)
        db.add(t)
        db.add(Param(key=O.NGUONG_CHU_TICH_KEY, value="100000000", label="Ngưỡng Chủ tịch duyệt chi", unit="đồng",
                     effective_from=date(2026, 9, 2), source="phép thử VH1", status="active",
                     signed_chutich=True, signed_tgd=True, proposed_by="phep_thu"))
        db.commit()
        CTX.update(tour=t.id, xe=v.id, bien_so=v.plate, tai_xe=e.id, di=di)
        db.close()
        R.clear_param_cache()
        yield


def test_1_dieu_hanh_de_nghi_xe():
    r = client.post("/api/v1/de-nghi-xe", headers=h("dh.lan"),
                    json={"tour_id": CTX["tour"], "so_khach": 30, "km_du_kien": 700, "yeu_cau": "Xe 45 chỗ"})
    assert r.status_code == 201, r.text
    CTX["de_nghi"] = r.json()["id"]


def test_2_gd_doi_xe_lap_lenh():
    r = client.post("/api/v1/dispatch", headers=h("vh1.gdxe"),
                    json={"tour_id": CTX["tour"], "vehicle_id": CTX["xe"], "date_from": str(CTX["di"]),
                          "date_to": str(CTX["di"] + timedelta(days=2)), "de_nghi_id": CTX["de_nghi"],
                          "so_khach": 30, "km_du_kien": 700,
                          "ly_do_khac_goi_y": "Chạy thử trọn luồng VH1 – chọn xe của tài xế đã cấp tài khoản"})
    assert r.status_code == 201, r.text
    CTX["lenh"] = r.json()["id"]


def test_3_tai_xe_thay_lenh_va_nhan():
    r = client.get("/api/v1/xe-hdv/cua-toi", headers=h("vh1.taixe"))
    assert r.status_code == 200, r.text
    assert CTX["lenh"] in [x.get("id") for x in (r.json().get("lenh") or r.json().get("lenh_dieu_xe") or [])], r.json().keys()
    r = client.post(f"/api/v1/nhan-lenh/{CTX['lenh']}/nhan", headers=h("vh1.taixe"))
    assert r.status_code == 200, r.text


def test_4a_tai_xe_ghi_chuyen_tren_dien_thoai():
    """Tài xế mở phiếu, ghi dầu kèm ảnh hoá đơn, qua trạm, rồi kết thúc gửi GĐ — không có ô doanh thu."""
    tx, did = h("vh1.taixe"), CTX["lenh"]
    anh = {"tep": ("hoadon.jpg", b"\xff\xd8\xff\xe0 anh hoa don dau", "image/jpeg")}
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx, data={"kind": "dau", "so_tien": 1000})
    assert r.status_code == 422 and "Bắt đầu chuyến" in r.text
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/bat-dau", headers=tx, data={"km_dau": 120000})
    assert r.status_code == 200, r.text
    assert "doanh_thu" not in r.text                                   # tài xế không thấy doanh thu
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx, data={"kind": "dau", "so_tien": 6_100_000})
    assert r.status_code == 422 and "số lít" in r.text
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx,
                    data={"kind": "dau", "so_tien": 6_100_000, "lit": 200}, files=anh)
    assert r.status_code == 200, r.text
    assert r.json()["chi_phi"][0]["co_anh"] is True
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx,
                    data={"kind": "cau_duong", "so_tien": 760_000, "so_hoa_don": "EPASS-VH1", "tra_bang": "tai_khoan_cong_ty"})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx, data={"kind": "cong_tac_phi", "so_tien": 600_000})
    assert r.status_code == 422                                        # CTP do đội xe tính theo lệnh
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/ket-thuc", headers=tx, data={"km_cuoi": 119000})
    assert r.status_code == 422 and "nhỏ hơn" in r.text
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/ket-thuc", headers=tx, data={"km_cuoi": 120690})
    assert r.status_code == 200, r.text
    assert r.json()["chuyen"]["da_gui"] and r.json()["chuyen"]["km_chay"] == 690
    r = client.post(f"/api/v1/nhan-lenh/{did}/chuyen/khoan", headers=tx, data={"kind": "giu_xe", "so_tien": 50_000})
    assert r.status_code == 422 and "không sửa được" in r.text          # gửi rồi thì khoá
    # tài xế khác không chạm được phiếu của lệnh này
    from app.core.security import hash_password
    from app.models.core import User
    db = SessionLocal()
    db.add(User(username="vh1.taixe2", full_name="Tài xế khác", role="tai_xe", department="doi_xe",
                staff_code="VH1TX2", password_hash=hash_password(PW), active=True)); db.commit(); db.close()
    assert client.get(f"/api/v1/nhan-lenh/{did}/chuyen", headers=h("vh1.taixe2")).status_code == 403


def test_4b_gd_mo_dung_phieu_tai_xe_them_doanh_thu():
    ds = client.get(f"/api/v1/fleet/lenh-cho-bao-cao?xe_id={CTX['xe']}", headers=h("vh1.gdxe")).json()["rows"]
    l = next(x for x in ds if x["id"] == CTX["lenh"])
    p = l["phieu"]
    assert p and p["tai_xe_da_gui"] and p["km_cuoi"] == 120690 and len(p["khoan"]) == 2
    CTX["chuyen"] = p["id"]
    # Lập phiếu thứ hai cho cùng lệnh bị chặn
    r = client.post("/api/v1/fleet/chuyen", headers=h("vh1.gdxe"),
                    json={"vehicle_id": CTX["xe"], "dispatch_id": CTX["lenh"], "ten_tour": "x",
                          "ngay_di": str(CTX["di"]), "ngay_ve": str(CTX["di"]), "quyet_toan": False})
    assert r.status_code == 422 and f"#{p['id']}" in r.text
    r = client.put(f"/api/v1/fleet/chuyen/{p['id']}", headers=h("vh1.gdxe"),
                   json={"phien_ban": p["phien_ban"], "doanh_thu": 15_000_000, "km_nguon": "anh_dong_ho"})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/fleet/chuyen/{p['id']}/chi-phi", headers=h("vh1.gdxe"),
                    json={"kind": "cong_tac_phi", "amount": 600_000})
    assert r.status_code in (200, 201), r.text
    ky = CTX["di"].strftime("%Y-%m")
    t = client.get(f"/api/v1/fleet/lai-lo?ky={ky}", headers=h("chutich")).json()["tong"]
    assert t["so_chuyen_chua_quyet_toan"] >= 1, t


def test_5_gd_gui_to_bao_cao():
    tid = CTX["chuyen"]
    r = client.get(f"/api/v1/fleet/quyet-toan-chuyen/{tid}", headers=h("vh1.gdxe"))
    assert r.status_code == 200, r.text
    CTX["kiem"] = r.json().get("kiem")
    r = client.post(f"/api/v1/fleet/quyet-toan-chuyen/{tid}/gui", headers=h("vh1.gdxe"))
    assert r.status_code == 200, f"{r.text} | kiểm: {CTX['kiem']}"
    ds = client.get("/api/v1/fleet/chuyen", headers=h("vh1.gdxe")).json()
    x = next(c for c in ds if c["id"] == tid)
    assert x["qt_trang_thai"] == "cho_tgd" and x["qt_ten_trang_thai"] == "Chờ Chủ tịch duyệt"


def test_6_chu_tich_duyet_chuyen_vao_loi_nhuan():
    tid = CTX["chuyen"]
    assert client.post(f"/api/v1/fleet/quyet-toan-chuyen/{tid}/ky", headers=h("vh1.gdxe"),
                       json={"buoc": "tgd"}).status_code in (403, 422)     # GĐ không tự duyệt tờ mình gửi
    r = client.post(f"/api/v1/fleet/quyet-toan-chuyen/{tid}/ky", headers=h("chutich"), json={"buoc": "tgd"})
    assert r.status_code == 200, r.text
    ds = client.get("/api/v1/fleet/chuyen", headers=h("chutich")).json()
    x = next(c for c in ds if c["id"] == tid)
    assert x["quyet_toan"] is True and x["qt_trang_thai"] == "cho_ke_toan"


def test_7_ke_toan_ky_buoc_cuoi():
    r = client.post(f"/api/v1/fleet/quyet-toan-chuyen/{CTX['chuyen']}/ky", headers=h("ketoan"),
                    json={"buoc": "ke_toan"})
    assert r.status_code == 200, r.text
    assert r.json().get("trang_thai") == "da_duyet" or "da_duyet" in r.text


def test_8_de_xuat_chi_cho_khoan_goc_cua_chuyen():
    kg = client.get(f"/api/v1/fleet/khoan-goc?xe_id={CTX['xe']}", headers=h("vh1.gdxe")).json()["rows"]
    dau = next(k for k in kg if k["ma"].startswith("tc:") and k["so_tien"] == 6_100_000)
    r = client.post("/api/v1/fleet/de-nghi-chi", headers=h("vh1.gdxe"),
                    json={"so_tien": 6_100_000, "noi_dung": "Hoàn tiền dầu chuyến Đà Lạt", "nguoi_thu_huong": "Lý Văn Sơn",
                          "ma_so_thue": "", "chung_tu": "HD-DAU-VH1", "pham_vi": "xe", "bien_so": CTX["bien_so"],
                          "loai": "hoan_ung", "nhom": "Chi phí riêng của xe", "can_cu_so_tien": "Theo chứng từ",
                          "ma_khoan_goc": dau["ma"]})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["status"] == "cho_duyet"
    r = client.post(f"/api/v1/payment-requests/{rid}/step", headers=h("chutich"), json={"action": "approve"})
    assert r.status_code == 200, r.text
    from app.models.attachments import Attachment
    from app.models.ops import PaymentRequest
    db = SessionLocal()
    p = db.get(PaymentRequest, rid)
    db.add(Attachment(doi_tuong="de_nghi_chi", doi_tuong_id=p.code, loai="unc", ten_tep="unc.pdf",
                      checksum="vh1-unc", khoa_luu="unc/vh1"))
    db.commit(); db.close()
    r = client.post(f"/api/v1/payment-requests/{rid}/step", headers=h("ketoan"),
                    json={"action": "pay", "hinh_thuc_tt": "chuyen_khoan", "reason": "GD-VH1"})
    assert r.status_code == 200, r.text
    ch = client.get(f"/api/v1/fleet/chuyen?vehicle_id={CTX['xe']}", headers=h("vh1.gdxe")).json()
    x = next(c for c in ch if c["id"] == CTX["chuyen"])
    assert any(c["de_nghi_chi"] for c in x["chi_phi"] if c["kind"] == "dau")


def test_9a_bang_san_sang_van_hanh():
    r = client.get("/api/v1/fleet/san-sang-van-hanh", headers=h("vh1.gdxe"))
    assert r.status_code == 200, r.text
    j = r.json()
    ma = {x["ma"]: x for x in j["dong"]}
    assert set(j["nhom"]) == {"xe", "nguoi", "tham_so", "ky", "treo"} and j["tong"] == len(j["dong"])
    assert ma["co_gd_doi_xe"]["dat"] and ma["moc_duyet_chi"]["dat"]
    assert ma["tai_xe_chua_tai_khoan"]["so"] >= 1 and ma["tai_xe_chua_tai_khoan"]["muc"] == "bad"   # Bình chưa có tài khoản
    assert "Lý Văn Sơn" not in ma["tai_xe_chua_tai_khoan"]["ghi"]
    assert all(x["mo"] in ("", "ho-so-xe", "tai-xe", "bao-duong", "dau", "cong-no", "quyet-toan", "lich", "bao-cao-xe")
               for x in j["dong"])
    assert client.get("/api/v1/fleet/san-sang-van-hanh?ky=2026/11", headers=h("vh1.gdxe")).status_code == 422


def test_9_man_gon_va_lai_lo_doc_dung():
    ky = CTX["di"].strftime("%Y-%m")
    t = client.get(f"/api/v1/fleet/lai-lo?ky={ky}", headers=h("vh1.gdxe"))
    assert t.status_code == 200, t.text
    xe = [x for x in t.json()["xe"] if x["vehicle_id"] == CTX["xe"]]
    assert xe and xe[0]["doanh_thu"] >= 15_000_000
    for duong in ("/api/v1/fleet/lenh-dieu-xe", "/api/v1/fleet/xe?kem_kiem_tra=true", "/api/v1/fleet/cong-no",
                  "/api/v1/fleet/bao-duong/theo-xe", "/api/v1/fleet/bao-hong", "/api/v1/fleet/gia-dau",
                  "/api/v1/fleet/dinh-muc-dau", "/api/v1/fleet/de-nghi-chi"):
        assert client.get(duong, headers=h("vh1.gdxe")).status_code == 200, duong


def _web(*p):
    goc = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return open(os.path.join(goc, "web", *p), encoding="utf-8").read()


def test_10_man_hinh_ba_phan_da_noi():
    bc = _web("components", "doixe", "BonBuocBaoCaoXe.tsx")
    assert "/fleet/lenh-cho-bao-cao?xe_id=" in bc and "dispatch_id: Number(d.dispatch_id)" in bc
    assert "d.phieu?.tai_xe_da_gui" in bc and "if (daTX[k]) continue;" in bc      # không ghi lại khoản tài xế đã ghi
    tx = _web("app", "xe-hdv", "page.tsx")
    assert "<TaiXeGhiChuyen" in tx and "Xe &amp; lệnh của tôi" in tx
    for hdv in ("Thẻ hướng dẫn viên", "Chuyến được chào cho tôi", "Báo cáo sau tour của tôi", "Tiền tôi đang giữ"):
        assert hdv not in tx, hdv                                                # HDV đã tách (Chủ tịch 10/11/2026)
    g = _web("components", "doixe", "TaiXeGhiChuyen.tsx")
    assert "doanh_thu" not in g and 'capture="environment"' in g
    assert "<SanSangVanHanh" in _web("app", "xe", "page.tsx")
