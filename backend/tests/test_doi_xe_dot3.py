"""Đội xe Vietrip – Đợt 3: quyết toán chủ xe hợp tác, cấn trừ có kiểm soát, thế chấp, năm chặn cứng còn lại.

Đây là đợt mà mọi lỗi đều là lỗi TIỀN, nên bộ test nhắm thẳng vào những chỗ tiền đi lạc trong thực tế chứ
không kiểm "có chạy được không":

  1. Chia lịch cấn trừ sai một kỳ là thu thừa của đối tác đúng một khoản, mà bảng vẫn trông hợp lý.
  2. Dựng lại bảng quyết toán là việc người ta làm nhiều lần trong một kỳ – mỗi lần dựng lại mà trừ thêm một
     lần thì đối tác mất tiền và không ai thấy.
  3. Kỳ mà đối tác chịu nhiều hơn được hưởng KHÔNG được thành phiếu chi mang dấu trừ.
  4. Cấn trừ chéo pháp nhân là sai cả sổ lẫn thuế.
  5. Xe còn thế chấp mà sang tên được là mất tài sản bảo đảm của ngân hàng.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe3.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe3.db"): os.remove("test_doi_xe3.db")
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app


# ══════════════ DL-7 · 16/10/2026 — TỆP NÀY TẮT LUẬT «LỆNH PHẢI RA TỪ ĐỀ NGHỊ»
#
# Từ 16/10/2026 cửa lập lệnh từ chối lệnh không kèm đề nghị xe (tham số
# `xe_bat_buoc_qua_de_nghi`, bật sẵn). Các phép thử trong tệp này có trước luật ấy và đo một việc
# KHÁC — không đo chuỗi đề nghị → lệnh. Dựng một đề nghị hợp lệ cho mỗi phép thử ở đây đòi duyệt
# dự toán chuyến, tức kéo cả một phân hệ khác vào một tệp không nói về nó.
#
# Nên tệp này TẮT luật bằng tham số, và khai thẳng ra việc tắt. Hàng rào thật được đo riêng ở
# `test_dl7_lenh_phai_ra_tu_de_nghi.py` — chỗ duy nhất nói về chuỗi.
def _tat_luat_chuoi_de_nghi():
    from datetime import date as _date
    from app.db.session import SessionLocal as _S
    from app.models.core import Param as _Param
    from app.services import rules as _R
    # effective_from phải là HÔM NAY: `seed_params` đã nạp bản mặc định với ngày 01/9/2026, và
    # `_param_value` lấy bản có ngày hiệu lực MỚI NHẤT còn ≤ hôm nay. Đặt một ngày cũ hơn thì bản
    # của phép thử thua bản mặc định và luật vẫn bật — phép thử đỏ mà không hiểu vì sao.
    db = _S()
    try:
        db.add(_Param(key="xe_bat_buoc_qua_de_nghi", value="0", label="xe_bat_buoc_qua_de_nghi",
                      unit="", effective_from=_date.today(), source="test", status="active",
                      signed_chutich=True, signed_tgd=True, proposed_by="test"))
        db.commit()
    finally:
        db.close()
    _R.clear_param_cache()


client = TestClient(app); TOK = {}
HOM_NAY = date.today()
KY = f"{HOM_NAY:%Y-%m}"


def login(u):
    if u not in TOK:
        TOK[u] = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        _tat_luat_chuoi_de_nghi()     # DL-7: xem ghi chú ở đầu tệp
        yield


def xe(plate: str) -> dict:
    return next(x for x in client.get("/api/v1/fleet/xe", headers=login("cntt")).json() if x["plate"] == plate)


# ---------------------------------------------------------------- 1. Chia lịch cấn trừ
def test_chia_lich_ky_cuoi_om_phan_du_chu_khong_thu_thua_mot_ky():
    """Ví dụ trong tài liệu: 200.000.000 với mức 14.000.000/tháng ra 14 kỳ đủ mức và kỳ cuối 4.000.000 –
    KHÔNG phải 15 kỳ đủ 14 triệu. Sai chỗ này là thu thừa của đối tác đúng 10 triệu."""
    from app.services.fleet_settlement import dung_lich, chia_deu
    ks = dung_lich(200_000_000, 14_000_000)
    assert len(ks) == 15
    assert ks[:14] == [14_000_000] * 14
    assert ks[14] == 4_000_000
    assert sum(ks) == 200_000_000, "tổng lịch phải khớp tuyệt đối số nợ"

    # 400.000.000 chia 36 kỳ: 35 kỳ 11.111.111 và kỳ cuối 11.111.115
    ks2 = chia_deu(400_000_000, 36)
    assert len(ks2) == 36 and ks2[0] == 11_111_111 and ks2[-1] == 11_111_115
    assert sum(ks2) == 400_000_000


def test_lich_chua_co_ngay_bat_dau_thi_giu_nhap_va_khong_bao_qua_han():
    """Báo quá hạn cho một lịch chưa ai xác nhận là cách nhanh nhất làm người dùng bỏ qua mọi cảnh báo."""
    pid = client.post("/api/v1/fleet/chu-xe", headers=login("ketoan"),
                      json={"ho_ten": "Chủ xe kiểm thử A"}).json()["id"]
    r = client.post("/api/v1/fleet/lich-can-tru", headers=login("ketoan"),
                    json={"partner_id": pid, "ten": "Nợ mua xe", "principal": 200_000_000, "moi_ky": 14_000_000})
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "nhap_chua_xac_nhan"
    assert all(k["due_date"] is None for k in r.json()["cac_ky"])
    assert "chưa phát cảnh báo quá hạn" in r.json()["message"]


# ---------------------------------------------------------------- 2. Cấn trừ chỉ một lần
@pytest.fixture(scope="module")
def bo_du_lieu(_startup):
    """Một chủ xe, một xe của họ, một chuyến có doanh thu, và một lịch cấn trừ đang hiệu lực."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe hợp tác B"}).json()["id"]
    v = xe("50E-955.31")
    assert client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h,
                       json={"vehicle_id": v["id"], "partner_id": pid}).status_code == 200
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                          "km_dau": 10_000, "km_cuoi": 10_300, "doanh_thu": 100_000_000,
                          "ten_tour": "Chuyến kiểm thử quyết toán"}).json()
    client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=h,
                json={"kind": "dau", "amount": 8_000_000, "lit": 100, "chung_tu": "HD-D-1"})
    pl = client.post("/api/v1/fleet/lich-can-tru", headers=h,
                     json={"partner_id": pid, "ten": "Nợ mua xe 200tr", "principal": 200_000_000,
                           "moi_ky": 14_000_000, "bat_dau": str(HOM_NAY.replace(day=1))}).json()
    assert pl["status"] == "hieu_luc"
    return {"partner_id": pid, "vehicle_id": v["id"], "trip_id": t["id"], "plan_id": pl["id"]}


def test_dung_quyet_toan_ra_dung_cong_thuc(bo_du_lieu):
    """Trước cấn trừ = đối tác được hưởng − đối tác phải chịu + điều chỉnh được duyệt."""
    r = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{bo_du_lieu['partner_id']}/dung", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["doanh_thu"] == 100_000_000
    assert d["doi_tac_chiu"] == 8_000_000, "nhiên liệu do Vietourist tạm ứng nên đối tác phải hoàn lại"
    assert d["truoc_can_tru"] == 92_000_000
    assert any(l["kind"] == "doanh_thu" for l in d["dong"]) and any(l["kind"] == "chi_ho" for l in d["dong"])


def test_dung_lai_ky_khong_can_tru_them_lan_nao(bo_du_lieu):
    """Người ta dựng lại bảng nhiều lần trong một kỳ. Mỗi lần dựng lại mà trừ thêm một lần thì đối tác mất
    tiền và bảng vẫn trông hợp lý – đây là lỗi khó phát hiện nhất của cả đợt."""
    h = login("ketoan"); pid = bo_du_lieu["partner_id"]
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()["id"]
    r = client.post(f"/api/v1/fleet/quyet-toan/{sid}/can-tru", headers=h,
                    json={"plan_id": bo_du_lieu["plan_id"], "so_tien": 14_000_000})
    assert r.status_code == 201, r.text
    assert r.json()["da_tru"] == 14_000_000 and r.json()["lap_lai"] is False
    sau_lan_1 = r.json()["quyet_toan"]["can_tru"]

    for _ in range(3):
        client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h)
    d = client.get(f"/api/v1/fleet/quyet-toan?ky={KY}&partner_id={pid}", headers=h).json()[0]
    assert d["can_tru"] == sau_lan_1 == 14_000_000, "dựng lại kỳ không được cấn trừ thêm"

    # Gọi lại đúng lần áp dụng đó cũng không trừ thêm
    r2 = client.post(f"/api/v1/fleet/quyet-toan/{sid}/can-tru", headers=h,
                     json={"plan_id": bo_du_lieu["plan_id"], "so_tien": 14_000_000})
    assert r2.json()["lap_lai"] is True
    assert r2.json()["quyet_toan"]["can_tru"] == 14_000_000


def test_khong_tru_qua_so_du_con_lai_cua_lich():
    """Bộ tính luôn giới hạn tổng áp dụng bằng số dư đủ điều kiện – không trừ của đối tác nhiều hơn họ nợ."""
    from app.db.session import SessionLocal
    from app.services import fleet_settlement as QT
    from app.models.fleet import RepaymentPlan
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe C"}).json()["id"]
    pl = client.post("/api/v1/fleet/lich-can-tru", headers=h,
                     json={"partner_id": pid, "ten": "Nợ nhỏ", "principal": 5_000_000, "so_ky": 1,
                           "bat_dau": str(HOM_NAY)}).json()
    db = SessionLocal()
    try:
        plan = db.get(RepaymentPlan, pl["id"])
        kq = QT.ap_dung_can_tru(db, plan, 50_000_000, idem_key="kiem-thu-vuot", boi="kiem_thu")
        assert kq["da_tru"] == 5_000_000, "không được trừ nhiều hơn số nợ còn lại"
        assert "số dư còn lại" in kq["ghi_chu"]
        db.commit()
        assert db.get(RepaymentPlan, pl["id"]).status == "tat_toan"
    finally:
        db.close()


# ---------------------------------------------------------------- 3. Số âm không thành phiếu chi âm
def test_ky_am_ghi_phai_thu_chuyen_ky_sau_chu_khong_tao_phieu_chi_am():
    """Kỳ mà đối tác chịu nhiều hơn được hưởng là khoản PHẢI THU, không phải một phiếu chi mang dấu trừ đi
    qua bàn duyệt."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe D"}).json()["id"]
    v = xe("50H-496.23")
    client.post("/api/v1/fleet/chu-xe/gan-xe", headers=h, json={"vehicle_id": v["id"], "partner_id": pid})
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": v["id"], "ngay_di": str(HOM_NAY), "ngay_ve": str(HOM_NAY),
                          "km_dau": 1000, "km_cuoi": 1100, "doanh_thu": 3_000_000}).json()
    client.post(f"/api/v1/fleet/chuyen/{t['id']}/chi-phi", headers=h,
                json={"kind": "dau", "amount": 9_000_000, "lit": 120, "chung_tu": "HD-D-2"})
    d = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()
    assert d["truoc_can_tru"] == -6_000_000
    assert d["sau_can_tru"] == 0, "số phải trả không bao giờ âm"
    assert d["chuyen_ky_sau"] == 6_000_000, "phần âm ghi thành phải thu chuyển kỳ sau"


# ---------------------------------------------------------------- 4. Đúng đối tác, đúng pháp nhân
def test_khong_can_tru_no_cua_doi_tac_khac(bo_du_lieu):
    h = login("ketoan")
    khac = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe E"}).json()["id"]
    pl = client.post("/api/v1/fleet/lich-can-tru", headers=h,
                     json={"partner_id": khac, "ten": "Nợ người khác", "principal": 10_000_000,
                           "so_ky": 1, "bat_dau": str(HOM_NAY)}).json()
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{bo_du_lieu['partner_id']}/dung", headers=h).json()["id"]
    r = client.post(f"/api/v1/fleet/quyet-toan/{sid}/can-tru", headers=h, json={"plan_id": pl["id"]})
    assert r.status_code == 422 and "đối tác khác" in r.json()["detail"]


def test_khong_can_tru_cheo_phap_nhan():
    """Hai pháp nhân là hai túi tiền khác nhau – gộp lại là sai cả sổ lẫn thuế."""
    h = login("ketoan")
    cos = client.get("/api/v1/companies", headers=login("chutich")).json()
    cos = cos if isinstance(cos, list) else cos.get("rows", [])
    if len(cos) < 2: pytest.skip("bản nền chưa có hai pháp nhân để kiểm")
    a, b = cos[0]["id"], cos[1]["id"]
    pid = client.post("/api/v1/fleet/chu-xe", headers=h,
                      json={"ho_ten": "Chủ xe F", "company_id": a}).json()["id"]
    pl = client.post("/api/v1/fleet/lich-can-tru", headers=h,
                     json={"partner_id": pid, "ten": "Nợ pháp nhân B", "principal": 10_000_000, "so_ky": 1,
                           "bat_dau": str(HOM_NAY), "creditor_company_id": b}).json()
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()["id"]
    r = client.post(f"/api/v1/fleet/quyet-toan/{sid}/can-tru", headers=h, json={"plan_id": pl["id"]})
    assert r.status_code == 422 and "pháp nhân" in r.json()["detail"]


# ---------------------------------------------------------------- 5. Phân bổ hóa đơn dùng chung
def test_hoa_don_chung_chi_chia_cho_xe_co_ten_tren_phu_luc():
    """Quy tắc sinh ra từ lỗi phân bổ tiền nước tháng 8/2026. Đường API không nhận "số lượng xe" – có ô số
    lượng là có ngày ai đó gõ 11 và chi phí chạy sang cả xe không nằm trên hóa đơn."""
    h = login("ketoan")
    ds = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()
    v1, v2 = ds[0]["id"], ds[1]["id"]
    r = client.post("/api/v1/fleet/hoa-don-chung", headers=h,
                    json={"so_hoa_don": "HD-BAI-01", "ngay": str(HOM_NAY), "nha_cung_cap": "Bãi xe X",
                          "tong_tien": 4_000_000, "vat": 320_000,
                          "xe": [{"vehicle_id": v1}, {"vehicle_id": v2}]})
    assert r.status_code == 201, r.text
    pb = r.json()["phan_bo"]
    assert len(pb) == 2 and {p["vehicle_id"] for p in pb} == {v1, v2}
    assert sum(p["amount"] for p in pb) == 4_320_000, "tổng phân bổ phải bằng tổng hóa đơn, không hụt vì làm tròn"

    assert client.post("/api/v1/fleet/hoa-don-chung", headers=h,
                       json={"so_hoa_don": "HD-BAI-02", "ngay": str(HOM_NAY), "tong_tien": 1_000_000,
                             "xe": []}).status_code == 422


def test_hoa_don_chung_khong_chia_cheo_hai_phap_nhan():
    from app.db.session import SessionLocal
    from app.models.hr import Vehicle
    from app.models.core import Company
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        cos = db.execute(sel(Company)).scalars().all()
        xes = db.execute(sel(Vehicle).order_by(Vehicle.id)).scalars().all()
        if len(cos) < 2 or len(xes) < 2: pytest.skip("bản nền chưa đủ dữ liệu")
        xes[0].company_id, xes[1].company_id = cos[0].id, cos[1].id
        db.commit()
        ids = [xes[0].id, xes[1].id]
    finally:
        db.close()
    r = client.post("/api/v1/fleet/hoa-don-chung", headers=login("ketoan"),
                    json={"so_hoa_don": "HD-BAI-03", "ngay": str(HOM_NAY), "tong_tien": 2_000_000,
                          "xe": [{"vehicle_id": i} for i in ids]})
    assert r.status_code == 422 and "hai pháp nhân" in r.json()["detail"]


# ---------------------------------------------------------------- 6. Chặn cứng B4, B5, B7, B8, B9
def test_B4_chi_vuot_so_da_thu_cua_tour():
    r = client.post("/api/v1/fleet/kiem-chi", headers=login("ketoan"),
                    json={"tour_id": 1, "so_tien": 999_000_000_000, "chung_tu": "HD-1"}).json()
    assert r["muc"] == "BLOCK"
    assert "B4_CHI_VUOT_DA_THU" in {i["code"] for i in r["items"]}


def test_B5_chi_cho_ben_con_cong_no_ma_khong_co_dong_khau_tru(bo_du_lieu):
    h = login("ketoan")
    r = client.post("/api/v1/fleet/kiem-chi", headers=h,
                    json={"so_tien": 1_000_000, "partner_id": bo_du_lieu["partner_id"],
                          "co_dong_khau_tru": False}).json()
    assert "B5_CHUA_CAN_TRU" in {i["code"] for i in r["items"]} and r["muc"] == "BLOCK"
    r2 = client.post("/api/v1/fleet/kiem-chi", headers=h,
                     json={"so_tien": 1_000_000, "partner_id": bo_du_lieu["partner_id"],
                           "co_dong_khau_tru": True}).json()
    assert "B5_CHUA_CAN_TRU" not in {i["code"] for i in r2["items"]}


def test_B6_chi_lon_khong_chung_tu():
    r = client.post("/api/v1/fleet/kiem-chi", headers=login("ketoan"),
                    json={"so_tien": 20_000_000, "chung_tu": ""}).json()
    assert "B6_THIEU_CHUNG_TU" in {i["code"] for i in r["items"]}


def test_B7_khong_sang_ten_xe_con_the_chap():
    """Ca thật trong tài liệu: 50F-034.71 thế chấp chung với 034.37 đã bán; 50F-046.22 thế chấp chung với
    046.92 đã sang tên. Cả hai phải giữ cờ đỏ cho tới khi có văn bản ngân hàng."""
    from app.db.session import SessionLocal
    from app.models.finance import FinContract
    h = login("ketoan"); hc = login("chutich")
    v = xe("50E-957.34")
    db = SessionLocal()
    try:
        ct = FinContract(code="KU-TEST-1", kind="vay", partner="TPBank", contract_no="TP41M231090001",
                         principal=2_000_000_000, outstanding=1_767_406_654, status="hieu_luc")
        db.add(ct); db.commit(); cid = ct.id
    finally:
        db.close()
    assert client.post("/api/v1/fleet/the-chap", headers=hc,
                       json={"contract_id": cid, "vehicle_id": v["id"],
                             "nguon": "hồ sơ ngân hàng"}).status_code == 201
    sid = client.post("/api/v1/fleet/ban-xe", headers=h,
                      json={"vehicle_id": v["id"], "gia_ban": 1_800_000_000,
                            "nguon": "hợp đồng bán xe"}).json()["id"]
    r = client.post(f"/api/v1/fleet/ban-xe/{sid}/chuyen-buoc", headers=hc, json={"stage": "sang_ten"})
    assert r.status_code == 422
    assert "B7_SANG_TEN_CON_THE_CHAP" in {i["code"] for i in r.json()["detail"]["vi_pham"]}

    # Có văn bản giải chấp thì đi tiếp được
    r2 = client.post(f"/api/v1/fleet/ban-xe/{sid}/chuyen-buoc", headers=hc,
                     json={"stage": "sang_ten", "van_ban_giai_chap": "CV-GC-2026/115"})
    assert r2.status_code == 200, r2.text


def test_B8_goi_the_chap_nhieu_xe_can_phuong_an_rut_tai_san():
    from app.db.session import SessionLocal
    from app.models.finance import FinContract
    hc = login("chutich")
    ds = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()
    v1, v2 = ds[0], ds[1]
    db = SessionLocal()
    try:
        ct = FinContract(code="KU-TEST-2", kind="vay", partner="MB", contract_no="LD2607831521",
                         principal=1_700_000_000, outstanding=1_700_000_000, status="hieu_luc")
        db.add(ct); db.commit(); cid = ct.id
    finally:
        db.close()
    for v in (v1, v2):
        client.post("/api/v1/fleet/the-chap", headers=hc, json={"contract_id": cid, "vehicle_id": v["id"]})
    sid = client.post("/api/v1/fleet/ban-xe", headers=login("ketoan"),
                      json={"vehicle_id": v1["id"], "gia_ban": 1_000_000_000, "nguon": "hợp đồng"}).json()["id"]
    r = client.post(f"/api/v1/fleet/ban-xe/{sid}/chuyen-buoc", headers=hc,
                    json={"stage": "sang_ten", "van_ban_giai_chap": "CV-GC-X"})
    assert r.status_code == 422
    assert "B8_GOI_THE_CHAP_NHIEU_XE" in {i["code"] for i in r.json()["detail"]["vi_pham"]}


def test_giai_chap_bat_buoc_co_van_ban_ngan_hang():
    """Đặc tả: không tự coi tài sản không thấy trong danh sách ngân hàng là đã giải chấp."""
    sid = client.post("/api/v1/fleet/ban-xe", headers=login("ketoan"),
                      json={"vehicle_id": xe("50H-496.23")["id"], "gia_ban": 500_000_000}).json()["id"]
    r = client.post(f"/api/v1/fleet/ban-xe/{sid}/chuyen-buoc", headers=login("chutich"), json={"stage": "giai_chap"})
    assert r.status_code == 422 and "văn bản giải chấp" in r.json()["detail"]


def test_B9_khong_dong_ky_khi_con_co_do(bo_du_lieu):
    """Kỳ còn cờ đỏ chưa xử lý thì không đóng được – đóng kỳ là chốt một con số với đối tác."""
    h = login("ketoan"); pid = bo_du_lieu["partner_id"]
    t = client.post("/api/v1/fleet/chuyen", headers=h,
                    json={"vehicle_id": bo_du_lieu["vehicle_id"], "ngay_di": str(HOM_NAY),
                          "ngay_ve": str(HOM_NAY), "km_dau": 90_000, "km_cuoi": 91_000,
                          "km_gps": 300, "doanh_thu": 1_000_000}).json()
    assert t["co"] == "do"
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()["id"]
    r = client.post(f"/api/v1/fleet/quyet-toan/{sid}/dong-ky", headers=login("chutich"))
    assert r.status_code == 422
    assert "B9_CHUYEN_CO_DO" in {i["code"] for i in r.json()["detail"]["vi_pham"]}


def test_ky_da_dong_thi_khoa_khong_sua_nguoc():
    """Đóng rồi thì khóa: sửa phải tạo bút toán điều chỉnh ở kỳ sau, không sửa ngược vào con số đã chốt."""
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe G"}).json()["id"]
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()["id"]
    assert client.post(f"/api/v1/fleet/quyet-toan/{sid}/dong-ky", headers=login("chutich")).status_code == 200
    assert client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).status_code == 422
    assert client.post(f"/api/v1/fleet/quyet-toan/{sid}/dieu-chinh", headers=login("chutich"),
                       json={"mo_ta": "sửa sau khi đóng", "amount": 1}).status_code == 422


def test_dong_dieu_chinh_phai_co_nguoi_duyet_moi_dong_duoc_ky():
    h = login("ketoan")
    pid = client.post("/api/v1/fleet/chu-xe", headers=h, json={"ho_ten": "Chủ xe H"}).json()["id"]
    sid = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{pid}/dung", headers=h).json()["id"]
    r = client.post(f"/api/v1/fleet/quyet-toan/{sid}/dieu-chinh", headers=login("chutich"),
                    json={"mo_ta": "Bù chênh lệch đối chiếu tháng trước", "amount": 500_000})
    assert r.status_code == 201, r.text
    d = r.json()["quyet_toan"]
    assert d["dieu_chinh"] == 500_000 and d["truoc_can_tru"] == 500_000
    assert all(l["duyet_boi"] for l in d["dong"] if l["kind"] == "dieu_chinh")
    assert client.post(f"/api/v1/fleet/quyet-toan/{sid}/dong-ky", headers=login("chutich")).status_code == 200


# ---------------------------------------------------------------- 7. Người lập lệnh điều xe
def test_chi_dinh_nguoi_lap_lenh_bang_cau_hinh_khong_viet_ten_vao_ma():
    """Chỉ đạo Chủ tịch 07/9/2026: một người duy nhất tạo và chốt lệnh điều xe. Ghi bằng tài khoản trong tham
    số chứ không viết tên người vào mã – thay người phụ trách thì sửa một dòng cấu hình."""
    ps = {p["key"]: p for p in client.get("/api/v1/params", headers=login("chutich")).json()}
    assert "xe_nguoi_lap_lenh" in ps, "phải có tham số chỉ định người lập lệnh"

    from app.db.session import SessionLocal
    from app.models.core import Param
    from sqlalchemy import select as sel
    db = SessionLocal()
    try:
        p = db.execute(sel(Param).where(Param.key == "xe_nguoi_lap_lenh")).scalars().first()
        p.value = "dh.lan"; db.commit()
    finally:
        db.close()
    t = client.get("/api/v1/tours", headers=login("cntt")).json()["rows"][0]
    v = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()[0]
    body = {"tour_id": t["id"], "vehicle_id": v["id"], "date_from": str(HOM_NAY + timedelta(days=400)),
            "date_to": str(HOM_NAY + timedelta(days=401)), "internal_price": 1_000_000}
    r = client.post("/api/v1/dispatch", headers=login("cntt"), json=body)
    assert r.status_code == 403 and "được tạo lệnh điều xe" in r.json()["detail"]
    r2 = client.post("/api/v1/dispatch", headers=login("dh.lan"), json=body)
    assert r2.status_code == 201, r2.text

    db = SessionLocal()
    try:
        p = db.execute(sel(Param).where(Param.key == "xe_nguoi_lap_lenh")).scalars().first()
        p.value = "53"; db.commit()          # trả lại giá trị chỉ định GĐ điều hành đội xe
    finally:
        db.close()


def test_cau_hinh_tro_toi_tai_khoan_khong_ton_tai_thi_noi_ra_chu_khong_im_lang():
    """Im lặng bỏ qua thì chỉ đạo "chỉ một người" âm thầm hết hiệu lực mà không ai biết; còn chặn sạch thì cả
    đội xe đứng vì một ô cấu hình gõ sai. Nên: giữ quy tắc theo vai trò VÀ nói ra."""
    d = client.get("/api/v1/fleet/danh-muc-dot3", headers=login("chutich")).json()
    assert d["nguoi_lap_lenh"] == []
    assert "không khớp tài khoản đang hoạt động nào" in d["nguoi_lap_lenh_ghi_chu"]


# ------------------------------------------- Chốt lại cuối ngày 07/9/2026 (chỉ đạo Chủ tịch)
def test_khong_dung_lai_ky_truoc_moc_ap_dung(bo_du_lieu):
    """Tháng 7 và tháng 8/2026 đã quyết toán và trả tiền xong theo cách cắt kỳ cũ. Máy dựng lại các kỳ đó sẽ
    cắt theo tháng dương lịch, ra một con số KHÁC con số đã trả – và đó chính là lúc phát sinh trả bù lần
    hai. Cách cắt theo tháng dương lịch áp dụng từ 01/9/2026 trở đi."""
    r = client.post(f"/api/v1/fleet/quyet-toan/2026-08/{bo_du_lieu['partner_id']}/dung", headers=login("ketoan"))
    assert r.status_code == 422, r.text
    assert "trước mốc áp dụng" in r.json()["detail"]
    assert "dòng điều chỉnh ở kỳ hiện tại" in r.json()["detail"], "phải chỉ đường xử lý, không chỉ chặn"


def test_sua_chua_chi_ho_vao_dung_cot_doi_tac_phai_hoan(bo_du_lieu):
    """Chủ tịch chốt lại cuối ngày 07/9/2026: giữ cách chi hộ – Vietourist ứng tiền sửa chữa rồi cấn trừ vào
    công nợ chủ xe. Khoản chi hộ phải vào cột "đối tác phải hoàn lại"; rơi nhầm sang cột "chủ xe tự chịu" là
    công ty ứng tiền rồi không đòi lại được, mà bảng vẫn cân."""
    h = login("ketoan")
    truoc = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{bo_du_lieu['partner_id']}/dung",
                        headers=h).json()["doi_tac_chiu"]
    r = client.post("/api/v1/fleet/bao-duong", headers=h,
                    json={"vehicle_id": bo_du_lieu["vehicle_id"], "ngay": str(HOM_NAY), "kind": "sua_chua",
                          "so_tien": 5_000_000, "noi_dung": "Thay bố thắng", "chung_tu": "HD-SC-QT"})
    assert r.status_code == 201, r.text
    assert r.json()["ben_chiu"] == "vietourist_tam_ung"
    d = client.post(f"/api/v1/fleet/quyet-toan/{KY}/{bo_du_lieu['partner_id']}/dung", headers=h).json()
    assert d["doi_tac_chiu"] == truoc + 5_000_000
    assert any(l["kind"] == "chi_ho" and l["amount"] == 5_000_000 for l in d["dong"])
