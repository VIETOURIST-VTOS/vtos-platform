"""Nền dữ liệu đội xe Vietrip – Đợt 1 (đặc tả v1.3, 06/9/2026).

Ba điều đợt này phải làm đúng, và cũng là ba điều bộ test dưới đây nhắm vào:

  1. Đổi biển số KHÔNG được đẻ ra chiếc xe thứ hai. Đây là lý do tồn tại của cả đợt: dữ liệu cũ lấy biển số
     làm danh tính, nên mỗi lần đổi biển là lịch sử chuyến của xe bị chẻ làm đôi.
  2. Thiếu dữ liệu KHÔNG được hiện màu xanh. Một xe chưa nhập đăng kiểm mà màn hình báo "đạt" thì người điều
     hành tin rằng đã kiểm tra rồi – tệ hơn hẳn việc không kiểm tra gì.
  3. Những điều kiện đúng bất kể hồ sơ đã nhập đủ hay chưa – hết quyền khai thác, xe đã bán, trùng lịch –
     phải CHẶN thật, ngay hôm nay.
"""
import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_doi_xe.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_doi_xe.db"): os.remove("test_doi_xe.db")
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

def _tour_o(d1, d2=None):
    """R5-28: ngày lệnh phải nằm trong ngày tour — phép thử lập lệnh ở một ngày xa thì dựng một tour đúng ngày ấy."""
    import uuid
    from datetime import date as _d
    from app.db.session import SessionLocal as _SL
    from app.models.core import Tour as _T, User as _U
    d1 = _d.fromisoformat(str(d1)); d2 = _d.fromisoformat(str(d2 or d1))
    db = _SL()
    try:
        op = db.query(_U).filter_by(username="dh.lan").first()
        t = _T(code="XE-" + uuid.uuid4().hex[:6].upper(), name="Tour thử lệnh xe", tour_type="le_noi_dia",
               start_date=d1, end_date=d2, operator_id=op.id, price_per_pax=1_000_000, fixed_cost=0,
               var_cost_per_pax=0, planned_pax=20, status="da_duyet")
        db.add(t); db.commit()
        return t.id
    finally:
        db.close()

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
    ds = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()
    return next(x for x in ds if x["plate"] == plate)


def ho_so(vid: int) -> dict:
    r = client.get(f"/api/v1/fleet/xe/{vid}", headers=login("cntt"))
    assert r.status_code == 200, r.text
    return r.json()


def kiem_tra(vid: int, d1: date, d2: date, who="tp.dieuhanh") -> dict:
    r = client.get(f"/api/v1/fleet/kiem-tra?vehicle_id={vid}&date_from={d1}&date_to={d2}", headers=login(who))
    assert r.status_code == 200, r.text
    return r.json()


def ma_loi(kq: dict) -> set:
    return {i["code"] for i in kq["items"]}


# ---------------------------------------------------------------- 1. Danh tính xe
def test_doi_bien_so_khong_de_ra_chiec_xe_thu_hai():
    """Cả Đợt 1 sinh ra vì lỗi này: trước đây đổi biển nghĩa là tạo bản ghi xe mới, và lịch sử chuyến, chi phí,
    khế ước của chiếc xe bị chẻ làm đôi mà không ai hay."""
    v = xe("50F-009.60"); vid = v["id"]; ma_cu = v["code"]
    n_truoc = len(client.get("/api/v1/fleet/xe", headers=login("cntt")).json())

    r = client.post(f"/api/v1/fleet/xe/{vid}/doi-bien", headers=login("cntt"),
                    json={"plate": "51B-123.45", "from_date": str(HOM_NAY), "source": "Giấy đăng ký mới"})
    assert r.status_code == 201, r.text

    ds = client.get("/api/v1/fleet/xe", headers=login("cntt")).json()
    assert len(ds) == n_truoc, "đổi biển không được làm tăng số xe trong danh mục"
    v2 = next(x for x in ds if x["id"] == vid)
    assert v2["plate"] == "51B-123.45"
    assert v2["code"] == ma_cu, "mã xe phải giữ nguyên suốt vòng đời"

    ls = ho_so(vid)["lich_su_bien"]
    assert [p["plate"] for p in ls] == ["50F-009.60", "51B-123.45"]
    assert ls[0]["to_date"] is not None, "biển cũ phải được đóng lại, không để hai biển cùng hiệu lực"
    assert ls[1]["to_date"] is None


def test_khong_gan_bien_dang_dung_cua_xe_khac():
    """Nếu cho phép, hệ thống sẽ có hai xe cùng một biển đang chạy – và mọi đối soát dầu, cầu đường tra theo
    biển số sẽ gán chi phí vào nhầm xe."""
    vid = xe("50E-957.34")["id"]
    r = client.post(f"/api/v1/fleet/xe/{vid}/doi-bien", headers=login("cntt"),
                    json={"plate": "51B-123.45", "from_date": str(HOM_NAY)})
    assert r.status_code == 422
    assert "xe khác" in r.json()["detail"]


def test_lich_su_bien_giu_lai_ca_cac_chuyen_da_chay():
    """Đổi biển xong, lệnh điều xe cũ vẫn phải thuộc về đúng chiếc xe đó."""
    vid = xe("51B-123.45")["id"]
    ds = client.get("/api/v1/dispatch", headers=login("cntt")).json()
    assert any(d["vehicle"] == "51B-123.45" for d in ds), \
        "lệnh cũ phải theo xe sang biển mới, không mất vào một bản ghi xe cũ"


# ---------------------------------------------------------------- 2. Thiếu dữ liệu ≠ đạt
def test_thieu_giay_to_thi_bao_chua_du_du_lieu_chu_khong_bao_dat():
    v = xe("50E-957.34")
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=5), HOM_NAY + timedelta(days=7))
    assert kq["muc"] != "OK", "xe chưa có giấy tờ nào mà báo đạt là sai"
    assert kq["muc"] == "UNKNOWN"
    assert {"THIEU_DANG_KIEM", "THIEU_PHU_HIEU", "THIEU_BAO_HIEM"} <= ma_loi(kq)
    assert all(i["level"] == "UNKNOWN" for i in kq["items"] if i["code"].startswith("THIEU_"))


def test_giay_co_so_nhung_khong_co_ngay_het_han_van_la_chua_du_du_lieu():
    """Nhập số giấy mà bỏ trống ngày hết hạn là cách dễ nhất để 'làm cho đủ form'. Hệ thống không được coi
    dòng đó là bằng chứng còn hạn."""
    v = xe("50E-957.34")
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"),
                    json={"kind": "dang_kiem", "vehicle_id": v["id"], "number": "DK-2026-777"})
    assert r.status_code == 201, r.text
    assert "CHƯA có ngày hết hạn" in r.json()["message"]
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=5), HOM_NAY + timedelta(days=7))
    assert "THIEU_HAN_DANG_KIEM" in ma_loi(kq)
    assert kq["muc"] == "UNKNOWN"


def test_o_dem_xe_san_sang_khong_bang_tong_so_xe():
    """Đặc tả nói thẳng: số xe sẵn sàng không mặc định bằng tổng số xe. Đây là con số lãnh đạo nhìn đầu tiên."""
    d = client.get("/api/v1/fleet/tong-quan", headers=login("chutich")).json()
    assert d["tong_so_xe"] >= 4
    assert d["san_sang"] < d["tong_so_xe"], "chưa nhập hồ sơ mà báo toàn bộ xe sẵn sàng là sai"
    assert d["san_sang"] + d["chua_du_du_lieu"] + d["bi_chan"] <= d["tong_so_xe"]
    assert d["chan_khi_thieu_giay"] is False, "giai đoạn nhập liệu phải để chế độ không chặn"


def test_giay_het_han_thi_chan_that():
    """Khác với thiếu dữ liệu: ở đây hệ thống BIẾT giấy đã hết hạn, nên phải chặn chứ không chỉ nhắc."""
    v = xe("50E-957.34")
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"),
                    json={"kind": "dang_kiem", "vehicle_id": v["id"], "number": "DK-2025-001",
                          "expires_on": str(HOM_NAY - timedelta(days=1)), "verify": "da_xac_minh"})
    assert r.status_code == 201, r.text
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=5), HOM_NAY + timedelta(days=7))
    assert kq["muc"] == "BLOCK"
    assert "HET_HAN_DANG_KIEM" in ma_loi(kq)


def test_giay_moi_thay_giay_cu_chu_khong_xoa():
    """Lịch sử gia hạn là bằng chứng khi có tranh chấp – giấy cũ phải còn trong hồ sơ, chỉ hết hiệu lực."""
    v = xe("50E-957.34")
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"),
                    json={"kind": "dang_kiem", "vehicle_id": v["id"], "number": "DK-2027-002",
                          "expires_on": str(HOM_NAY + timedelta(days=365)), "verify": "da_xac_minh"})
    assert r.status_code == 201
    dk = [g for g in ho_so(v["id"])["giay_to"] if g["kind"] == "dang_kiem"]
    assert len(dk) == 1, "chỉ đúng một đăng kiểm còn hiệu lực"
    assert dk[0]["number"] == "DK-2027-002"
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=5), HOM_NAY + timedelta(days=7))
    assert "HET_HAN_DANG_KIEM" not in ma_loi(kq), "giấy đã gia hạn thì không được báo hết hạn nữa"


def test_giay_cua_xe_va_giay_cua_nguoi_khong_lan_nhau():
    """Gán nhầm giấy phép lái xe vào hồ sơ xe thì cả hai phía đều sai: xe thừa một giấy vô nghĩa, còn tài xế
    vẫn bị coi là chưa có bằng."""
    v = xe("50E-957.34")
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"), json={"kind": "gplx", "vehicle_id": v["id"]})
    assert r.status_code == 422 and "không phải của xe" in r.json()["detail"]
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"), json={"kind": "dang_kiem", "employee_id": 1})
    assert r.status_code == 422 and "không phải của người" in r.json()["detail"]
    r = client.post("/api/v1/fleet/giay-to", headers=login("cntt"),
                    json={"kind": "dang_kiem", "vehicle_id": v["id"], "employee_id": 1})
    assert r.status_code == 422 and "ĐÚNG một chủ thể" in r.json()["detail"]


# ---------------------------------------------------------------- 3. Điều kiện chặn thật
def test_xe_da_ban_khong_tu_dong_tro_lai_san_sang():
    """Đặc tả nêu đích danh: xe đã bán không tự đổi thành sẵn sàng. Chiếc xe vẫn nằm trong lịch sử, nhưng
    không được điều đi khi công ty không còn quyền khai thác."""
    v = xe("50E-955.31")
    r = client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"),
                   json={"lifecycle": "da_ban", "op_right": "khong"})
    assert r.status_code == 200, r.text
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=3), HOM_NAY + timedelta(days=4))
    assert kq["muc"] == "BLOCK"
    assert {"KHONG_QUYEN_KHAI_THAC", "XE_DA_BAN"} <= ma_loi(kq)


def test_xe_da_ban_nhung_co_hop_dong_hop_tac_thi_van_dieu_duoc():
    """Sở hữu và khai thác là hai việc khác nhau – xe bán rồi vẫn có thể chạy tiếp theo hợp đồng."""
    v = xe("50E-955.31")
    r = client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"),
                   json={"op_right": "hop_tac", "contract_ref": "HĐ-HT-2026/01",
                         "contract_from": str(HOM_NAY - timedelta(days=30)),
                         "contract_to": str(HOM_NAY + timedelta(days=300))})
    assert r.status_code == 200, r.text
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=3), HOM_NAY + timedelta(days=4))
    assert "XE_DA_BAN" not in ma_loi(kq)
    assert "KHONG_QUYEN_KHAI_THAC" not in ma_loi(kq)


def test_hop_dong_het_han_giua_chuyen_cung_la_het_quyen():
    """Hợp đồng còn hiệu lực ngày đi nhưng hết trước ngày về thì nửa sau hành trình xe chạy không có căn cứ."""
    v = xe("50E-955.31")
    client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"),
               json={"contract_to": str(HOM_NAY + timedelta(days=3))})
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=2), HOM_NAY + timedelta(days=6))
    assert "HOP_DONG_HET_HAN" in ma_loi(kq) and kq["muc"] == "BLOCK"
    client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"),
               json={"contract_to": str(HOM_NAY + timedelta(days=300))})


def test_trung_lich_bi_chan_ngay_ca_khi_ho_so_chua_day_du():
    """Trùng lịch đúng bất kể hồ sơ đã nhập đủ hay chưa, nên đây là điều được chặn ngay từ hôm nay."""
    from app.db.session import SessionLocal
    from app.models.hr import DispatchOrder, Vehicle, Employee
    from sqlalchemy import select as sel
    v = xe("51B-123.45")
    db = SessionLocal()
    try:
        drv = db.execute(sel(Employee).where(Employee.department == "doi_xe")).scalars().first()
        db.add(DispatchOrder(tour_id=1, vehicle_id=v["id"], driver_id=drv.id,
                             date_from=HOM_NAY + timedelta(days=10), date_to=HOM_NAY + timedelta(days=12),
                             created_by="kiem_thu", status="da_xac_nhan"))
        db.commit()
    finally:
        db.close()
    # Chồng đúng một ngày ở mép cũng là chồng – đây là chỗ hay sót khi viết điều kiện ngày.
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=12), HOM_NAY + timedelta(days=14))
    assert "TRUNG_LICH" in ma_loi(kq) and kq["muc"] == "BLOCK"
    kq2 = kiem_tra(v["id"], HOM_NAY + timedelta(days=13), HOM_NAY + timedelta(days=14))
    assert "TRUNG_LICH" not in ma_loi(kq2), "không chồng ngày thì không được báo trùng"


def test_lap_lenh_dieu_xe_bi_chan_khi_khong_du_dieu_kien():
    """Kiểm tra phải nằm ở đường LẬP LỆNH, không chỉ ở màn hình xem trước – nếu chỉ ở màn hình thì gọi thẳng
    API vẫn phát được lệnh."""
    v = xe("51B-123.45")
    r = client.post("/api/v1/dispatch", headers=login("gd.doixe"),
                    json={"tour_id": _tour_o(HOM_NAY + timedelta(days=11)), "vehicle_id": v["id"], "date_from": str(HOM_NAY + timedelta(days=11)),
                          "date_to": str(HOM_NAY + timedelta(days=11)), "internal_price": 1_000_000})
    assert r.status_code == 422, r.text
    d = r.json()["detail"]
    assert d["message"].startswith("Không đủ điều kiện")
    assert any(i["code"] == "TRUNG_LICH" for i in d["vi_pham"])


def test_lenh_hop_le_van_lap_duoc_va_kem_canh_bao_chua_du_du_lieu():
    """Chốt an toàn quan trọng nhất của đợt này: bật kiểm tra KHÔNG được làm đứng việc điều xe hằng ngày khi
    hồ sơ giấy tờ chưa nhập. Thiếu giấy là cảnh báo hiện rõ, không phải rào chặn."""
    v = xe("51B-123.45")
    # ly_do_khac_goi_y: xe này đã có lệnh trước đó nên bộ gợi ý Đợt 4 xếp nó dưới nhóm đề xuất theo tiêu chí
    # cân bằng ngày công tài xế. Một câu lý do là qua – đúng ý đồ "ghi vết", không phải rào chặn.
    r = client.post("/api/v1/dispatch", headers=login("gd.doixe"),
                    json={"tour_id": _tour_o(HOM_NAY + timedelta(days=40), HOM_NAY + timedelta(days=41)), "vehicle_id": v["id"], "date_from": str(HOM_NAY + timedelta(days=40)),
                          "date_to": str(HOM_NAY + timedelta(days=41)), "internal_price": 1_000_000,
                          "ly_do_khac_goi_y": "Kiểm thử: chọn đúng xe này"})
    assert r.status_code == 201, r.text
    kt = r.json()["kiem_tra"]
    assert kt["muc"] in ("UNKNOWN", "REVIEW")
    assert any("Chưa có dữ liệu" in c for c in kt["canh_bao"]), "phải nói rõ đang thiếu gì, không im lặng cho qua"


# ---------------------------------------------------------------- Hàng đợi xác minh
def test_hang_doi_xac_minh_khong_cho_dong_ma_khong_ghi_ket_luan():
    """Đóng việc mà không ghi lý do thì lần sau không ai biết chuyện đã xử lý thế nào, và việc lại được mở ra."""
    ds = client.get("/api/v1/fleet/xac-minh", headers=login("tp.dieuhanh")).json()
    assert ds, "bản nền phải có sẵn việc xác minh của các xe hợp tác"
    xid = ds[0]["id"]
    r = client.post(f"/api/v1/fleet/xac-minh/{xid}/ket-luan", headers=login("cntt"),
                    json={"status": "xong", "resolution": "   "})
    assert r.status_code == 422 and "kết luận" in r.json()["detail"]
    r = client.post(f"/api/v1/fleet/xac-minh/{xid}/ket-luan", headers=login("cntt"),
                    json={"status": "xong", "resolution": "Đã đối chiếu hợp đồng gốc ngày 07/9/2026"})
    assert r.status_code == 200, r.text
    sau = next(x for x in client.get("/api/v1/fleet/xac-minh", headers=login("tp.dieuhanh")).json() if x["id"] == xid)
    assert sau["status"] == "xong" and sau["resolved_by"] == "cntt"


def test_viec_xac_minh_dang_treo_hien_ra_khi_kiem_tra_dieu_xe():
    """Người điều hành phải thấy việc xác minh còn treo của chính chiếc xe mình đang định điều, chứ không phải
    tự đi mở màn hình khác."""
    v = xe("50H-496.23")
    kq = kiem_tra(v["id"], HOM_NAY + timedelta(days=3), HOM_NAY + timedelta(days=4))
    assert "CON_VIEC_XAC_MINH" in ma_loi(kq)


def test_ma_xe_khong_duoc_trung():
    v1 = xe("50E-957.34"); v2 = xe("50H-496.23")
    r = client.put(f"/api/v1/fleet/xe/{v2['id']}", headers=login("cntt"), json={"code": v1["code"]})
    assert r.status_code == 422 and "đã dùng" in r.json()["detail"]


def test_vong_doi_va_quyen_khai_thac_sai_thi_bao_loi():
    v = xe("50H-496.23")
    assert client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"), json={"lifecycle": "ban_roi"}).status_code == 422
    assert client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("cntt"), json={"op_right": "muon"}).status_code == 422


def test_ban_kiem_soat_chi_doc_khong_sua_ho_so_xe():
    v = xe("50H-496.23")
    assert client.get("/api/v1/fleet/tong-quan", headers=login("bks")).status_code == 200
    assert client.put(f"/api/v1/fleet/xe/{v['id']}", headers=login("bks"), json={"vin": "X"}).status_code in (403, 405)
    assert client.post(f"/api/v1/fleet/xe/{v['id']}/doi-bien", headers=login("bks"),
                       json={"plate": "51C-000.11", "from_date": str(HOM_NAY)}).status_code in (403, 405)
