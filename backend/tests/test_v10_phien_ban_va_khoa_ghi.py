"""V10 – hai người cùng sửa một bản ghi, và bấm nạp hai lần.

Nghiệm thu V10 nói đúng hai câu, và bộ này canh đúng hai câu đó:

    "Hai phiên cùng sửa một bản ghi: phiên sau nhận lỗi kèm nội dung mới."
    "Gọi nạp cùng một lô hai lần: lần hai trả về kết quả lần đầu, không tạo bản ghi mới."

Có một cái bẫy phải tránh trong chính bộ test này: một hàm kiểm luôn trả "khớp" cũng làm mọi phép thử
xanh. Nên ở đây phép thử quan trọng nhất là phép thử NGƯỢC – dựng đúng tình huống va chạm và ĐÒI máy
chủ phải từ chối. Một cái khóa không khóa được cái gì thì việc nó im lặng chẳng chứng minh điều gì.

Và một điều nữa ghi thẳng ra để người sau không đọc nhầm thành "V10 đã xong": kiểm phiên bản mới nối
vào MỘT đường sửa (dự toán tour). Mười một bảng còn lại đã có cột nhưng đường sửa của chúng CHƯA gọi
hàm kiểm – có phép thử ghi rõ điều đó bằng số, để lần sau nối thêm là thấy số đổi.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v10.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str) -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    from sqlalchemy import select
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        assert u is not None, f"không có tài khoản vai trò {vai} trong dữ liệu mẫu"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ====================== 1. HAI CHỖ KHAI DANH SÁCH BẢNG PHẢI KHỚP NHAU ======================
def test_mo_hinh_va_ban_nang_cap_khai_cung_mot_danh_sach_bang():
    """Bản nâng cấp thêm cột cho một tập bảng, dịch vụ khai một tập khác – thì cơ sở dữ liệu thật
    không giống điều mã tin, và không ai biết cho tới lúc một lần sửa đè mất số."""
    import importlib.util, pathlib
    from app.services.ghi_mot_lan import BANG_CO_PHIEN_BAN
    p = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / \
        "v10a7f3c9e1b48_v10_phien_ban_va_khoa_ghi.py"
    spec = importlib.util.spec_from_file_location("v10mig", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert m.BANG == BANG_CO_PHIEN_BAN


def test_du_muoi_hai_bang_co_cot_phien_ban_trong_mo_hinh():
    from app.db.session import Base
    import app.models, app.models.fleet, app.models.vietrip, app.models.visa  # noqa
    from app.services.ghi_mot_lan import BANG_CO_PHIEN_BAN
    thieu = [b for b in BANG_CO_PHIEN_BAN
             if b not in Base.metadata.tables or "phien_ban" not in Base.metadata.tables[b].columns]
    assert not thieu, f"khai trong danh sách nhưng mô hình chưa có cột: {thieu}"


def test_cot_phien_ban_co_mac_dinh_o_PHIA_MAY_CHU():
    """Dòng đang có trong cơ sở dữ liệu không đi qua mã Python lúc nâng cấp. Thiếu server_default thì
    mọi dòng cũ mang giá trị rỗng, và cột kiểm phiên bản không kiểm gì đúng lúc nó cần nhất."""
    from app.db.session import Base
    from app.services.ghi_mot_lan import BANG_CO_PHIEN_BAN
    for b in BANG_CO_PHIEN_BAN:
        c = Base.metadata.tables[b].columns["phien_ban"]
        assert c.server_default is not None, f"{b}.phien_ban thiếu server_default"
        assert c.nullable is False, f"{b}.phien_ban cho phép rỗng – rỗng thì không so được"


# ====================== 2. KIỂM PHIÊN BẢN – PHÉP THỬ NGƯỢC ======================
def _tour_nhap(db):
    from sqlalchemy import select
    from app.models.core import Tour
    return db.execute(select(Tour).where(Tour.status == "nhap")).scalars().first()


def test_phien_ban_LECH_thi_TU_CHOI_va_tra_ve_noi_dung_moi():
    """Phép thử quan trọng nhất của tệp này. Không có nó thì mọi phép thử khác vẫn xanh với một hàm
    kiểm rỗng."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        t = _tour_nhap(db)
        if t is None: pytest.skip("dữ liệu mẫu không có tour trạng thái nháp")
        tid, ma = t.id, t.code
    h = login("tp_dh")
    xem = client.get(f"/api/v1/tours/{tid}", headers=h)
    assert xem.status_code == 200, xem.text
    pb = xem.json()["phien_ban"]

    than = {"price_per_pax": 5_000_000, "fixed_cost": 1_000_000, "var_cost_per_pax": 2_000_000,
            "planned_pax": 20, "rest_stops": "Trạm A, Trạm B", "justification": ""}
    # Người A lưu trước, cầm đúng phiên bản.
    a = client.put(f"/api/v1/tours/{tid}", json={**than, "phien_ban": pb}, headers=h)
    assert a.status_code == 200, a.text
    assert a.json()["phien_ban"] == pb + 1, "sửa xong mà phiên bản không tăng thì lần sau không phát hiện được gì"

    # Người B vẫn cầm phiên bản CŨ – đây đúng là tình huống mất số âm thầm.
    b = client.put(f"/api/v1/tours/{tid}",
                   json={**than, "price_per_pax": 9_999_999, "phien_ban": pb}, headers=h)
    assert b.status_code == 409, f"người sau ghi đè được lên người trước: {b.status_code} {b.text}"
    ct = b.json()["detail"]
    assert ct["gate"] == "LECH_PHIEN_BAN"
    assert ct["dang_co"] == pb + 1 and ct["gui_len"] == pb
    # Từ chối phải KÈM nội dung mới, nếu không thì người sửa vẫn phải đi tra tay.
    assert ct["noi_dung_moi"]["price"] == 5_000_000, ct["noi_dung_moi"]
    assert ct["noi_dung_moi"]["phien_ban"] == pb + 1

    # Và số cũ phải còn nguyên – từ chối mà vẫn ghi một phần là tệ hơn không từ chối.
    lai = client.get(f"/api/v1/tours/{tid}", headers=h).json()
    assert lai["price_per_pax"] == 5_000_000 and lai["phien_ban"] == pb + 1


def test_khong_gui_phien_ban_thi_van_luu_duoc():
    """Màn hình cũ chưa kịp sửa vẫn phải dùng được – bắt lỗi toàn bộ giao diện trong một lần nâng cấp
    là cách chắc chắn để có một buổi sáng không ai làm việc được. Đây là NỢ có chủ ý, ghi ra bằng
    phép thử để người sau siết lại thì biết mình đang đổi cái gì."""
    from app.db.session import SessionLocal
    with SessionLocal() as db:
        t = _tour_nhap(db)
        if t is None: pytest.skip("dữ liệu mẫu không có tour trạng thái nháp")
        tid = t.id
    h = login("tp_dh")
    r = client.put(f"/api/v1/tours/{tid}",
                   json={"price_per_pax": 6_000_000, "fixed_cost": 0, "var_cost_per_pax": 1_000_000,
                         "planned_pax": 10, "rest_stops": "Trạm C", "justification": ""}, headers=h)
    assert r.status_code == 200, r.text


def test_ham_kiem_phien_ban_khong_bao_oan_khi_bang_nhau():
    from app.services import ghi_mot_lan as GML

    class Gia:
        phien_ban = 7
    GML.kiem_phien_ban(Gia(), 7, "thử", {})          # bằng nhau: im lặng
    GML.kiem_phien_ban(Gia(), None, "thử", {})       # chưa gửi: im lặng
    GML.kiem_phien_ban(Gia(), "", "thử", {})
    with pytest.raises(GML.LechPhienBan):
        GML.kiem_phien_ban(Gia(), 6, "thử", {})


def test_tang_phien_ban_tu_ban_ghi_cu_khong_co_so():
    """Dòng cũ trước nâng cấp có thể mang giá trị rỗng – tăng phải ra 2, không được nổ."""
    from app.services import ghi_mot_lan as GML

    class Cu:
        phien_ban = None
    c = Cu(); assert GML.tang_phien_ban(c) == 2 and c.phien_ban == 2


# ====================== 3. KHÓA CHỐNG GHI TRÙNG ======================
def _lo_ncc(ten: str) -> list[dict]:
    return [{"ten": ten, "loai": "khach_san", "ma_so_thue": "0312345678"}]


def test_nap_hai_lan_cung_mot_lo_KHONG_tao_ban_ghi_moi():
    """Nghiệm thu: 'lần hai trả về kết quả lần đầu, không tạo bản ghi mới'."""
    from app.db.session import SessionLocal
    from app.models.intake import IntakeRun
    from sqlalchemy import select, func
    h = login("cntt")
    than = {"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – khóa suy"),
            "ten_tep": "v10.csv", "nguon": "nguoi_nhap"}

    with SessionLocal() as db:
        truoc = db.execute(select(func.count()).select_from(IntakeRun)).scalar()

    a = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h)
    assert a.status_code == 201, a.text
    assert a.json()["da_nap"] == 1 and not a.json().get("lap_lai")

    b = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h)
    assert b.status_code == 201, b.text
    assert b.json().get("lap_lai") is True, "gọi lại cùng một lô mà vẫn chạy tiếp"
    assert b.json()["da_nap"] == a.json()["da_nap"], "lần hai phải trả KẾT QUẢ LẦN ĐẦU"
    assert "đã nạp lúc" in b.json()["message"]

    with SessionLocal() as db:
        sau = db.execute(select(func.count()).select_from(IntakeRun)).scalar()
    assert sau == truoc + 1, f"nhật ký nạp thêm {sau - truoc} dòng, đáng lẽ đúng 1"


def test_khoa_do_nguoi_goi_gui_thi_chan_ngay_ca_khi_noi_dung_khac():
    """Khóa của người gọi mạnh hơn khóa suy: cùng một lần bấm nút thì dù nội dung có khác cũng không
    được ghi hai lần – ví dụ người dùng sửa một ô rồi bấm lại trong lúc lần đầu chưa trả về."""
    h = {**login("cntt"), "X-Khoa-Ghi": "thu-v10-mot-lan-bam"}
    a = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – khóa gửi A"),
                          "ten_tep": "a.csv"})
    assert a.status_code == 201 and not a.json().get("lap_lai"), a.text
    b = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – khóa gửi B"),
                          "ten_tep": "b.csv"})
    assert b.json().get("lap_lai") is True
    from app.db.session import SessionLocal
    from app.models.suppliers import Supplier
    from sqlalchemy import select
    with SessionLocal() as db:
        assert db.execute(select(Supplier).where(
            Supplier.ten == "NCC thử V10 – khóa gửi B")).scalars().first() is None, \
            "lô thứ hai đã ghi vào bảng dù mang cùng khóa"


def test_lo_KHAC_NHAU_thi_van_nap_binh_thuong():
    """Khóa chống trùng mà chặn cả lô khác nhau thì nó không phải khóa, nó là hỏng."""
    h = login("cntt")
    a = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – lô một")})
    c = client.post("/api/v1/nap-du-lieu/nap", headers=h,
                    json={"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – lô hai")})
    assert a.status_code == 201 and c.status_code == 201
    assert not a.json().get("lap_lai") and not c.json().get("lap_lai")
    assert c.json()["da_nap"] == 1


def test_khoa_suy_HET_HAN_ngoai_cua_so_thi_nap_lai_duoc():
    """Suy khóa từ nội dung mà không giới hạn thời gian là sai: nạp lại đúng cùng một tệp hai tháng
    sau có thể là việc thật. Cửa sổ ngắn bắt đúng cái nó nhắm tới và không cản việc thật."""
    from datetime import datetime, timedelta
    from app.db.session import SessionLocal
    from app.models.ghi_mot_lan import KhoaGhi
    from app.services import ghi_mot_lan as GML
    with SessionLocal() as db:
        db.add(KhoaGhi(khoa="suy:thu-het-han", duong_dan="/x", boi="ai_do",
                       tra_ve='{"da_nap": 3}',
                       luc=datetime.now() - GML.CUA_SO_SUY_KHOA - timedelta(minutes=1)))
        db.commit()
        assert GML.da_ghi_roi(db, "suy:thu-het-han", tu_suy=True) is None, "ngoài cửa sổ vẫn chặn"
        # Khóa do NGƯỜI GỌI gửi thì không có cửa sổ – nó nói về một lần bấm nút cụ thể.
        assert GML.da_ghi_roi(db, "suy:thu-het-han", tu_suy=False) is not None


def test_ket_qua_nho_lai_du_de_man_hinh_ve_duoc():
    """Chỉ nhớ dấu 'đã chạy rồi' thì lần hai biết là trùng nhưng không nói được kết quả – người dùng
    vẫn phải đi tra tay, tức là chưa giải quyết gì."""
    h = login("cntt")
    than = {"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử V10 – nhớ kết quả")}
    a = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h).json()
    b = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h).json()
    for k in ("da_nap", "so_dong"):
        assert b.get(k) == a.get(k), f"thiếu '{k}' trong kết quả nhớ lại"
    assert b["lan_dau_luc"]


# ====================== 4. NÓI THẲNG PHẦN CÒN NỢ ======================
def test_ghi_ro_moi_noi_duoc_MOT_duong_sua_va_con_muoi_mot_bang_chua_noi():
    """Bản gốc (08/9/2026) chốt cứng HAI tệp – dự toán tour và báo giá – kèm câu dặn: "nếu đúng ý thì
    sửa phép thử này và ghi vì sao". VPM-8 (11/9/2026) chính là lần ấy.

    VÌ SAO ĐỔI: chốt cứng một danh sách tên tệp thì mỗi lần nối thêm một cửa sửa lại phải sửa tay
    phép thử, và người sửa tay dễ nhất là người đang muốn nó xanh. Nay phép thử đối chiếu với BẢN
    KHAI `CUA_SUA_CO_KHOA` trong ghi_mot_lan.py: nối thêm cửa mà quên khai thì đỏ, khai mà không nối
    thì test_vpm8 đỏ. Hai đầu canh nhau, không còn một con số để ai đó chỉnh cho vừa.
    """
    import pathlib, re
    from app.services.ghi_mot_lan import CUA_SUA_CO_KHOA
    goc = pathlib.Path(__file__).resolve().parents[1] / "app"
    noi = set()
    for f in goc.rglob("*.py"):
        if re.search(r"GML\.kiem_phien_ban|kiem_phien_ban\(", f.read_text(encoding="utf-8")) \
                and "ghi_mot_lan" not in f.name:
            noi.add(f.name)
    da_khai = {tep.rsplit("/", 1)[-1] for tep, _ in CUA_SUA_CO_KHOA.values()}
    assert noi == da_khai, (
        f"Tệp CÓ gọi kiểm phiên bản: {sorted(noi)}\n"
        f"Tệp ĐƯỢC KHAI trong CUA_SUA_CO_KHOA: {sorted(da_khai)}\n"
        "Lệch nghĩa là có cửa sửa gắn khoá mà quên khai (hoặc ngược lại). Khai vào "
        "app/services/ghi_mot_lan.py::CUA_SUA_CO_KHOA.")


def test_ngoai_cua_so_thi_NAP_LAI_THAT_chu_khong_phai_500():
    """CÁNH CỬA 10 PHÚT MỞ RA MỘT BỨC TƯỜNG — đo trên bản chạy thật 16/9/2026.

    Nạp lại 67 tệp kho cũ T1 (đã nạp buổi sáng) thì bước kiểm tra trả 200 bình thường, còn bước
    ghi trả **500 Internal Server Error**. Lần theo thì ra ba mảnh khớp nhau:

        suy_khoa()    băm THUẦN của (đường dẫn | người | nội dung) – cùng tệp, cùng người,
                      cùng cờ thì ra CÙNG MỘT KHÓA, mãi mãi
        da_ghi_roi()  ngoài cửa sổ 10 phút thì cố ý trả None – "coi như lần ghi mới"
        nho_ket_qua() rồi THÊM lại đúng khóa ấy, mà `khoa_ghi.khoa` là cột unique
                      -> IntegrityError -> 500

    Tức là chính trường hợp mà cửa sổ 10 phút sinh ra để CHO PHÉP — chú thích đầu tệp viết rõ
    "đủ ngắn để không cản việc nạp lại thật sự vào hôm sau" — lại là trường hợp làm nổ.

    VÌ SAO BỘ TEST NÀY TỪNG BỎ LỌT. `test_khoa_suy_HET_HAN_ngoai_cua_so_thi_nap_lai_duoc` dừng
    đúng ở ngưỡng cửa: nó chứng minh `da_ghi_roi` trả None, rồi thôi. Không ai bước qua cửa ấy để
    xem bên kia có sàn không. Phép thử này đi hết đường: gọi THẬT lần thứ hai qua cửa HTTP.

    Và lỗi này KHÔNG RIÊNG kho cũ: mọi bộ nạp, hễ nạp lại đúng một nội dung sau 10 phút, đều nổ.
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.ghi_mot_lan import KhoaGhi

    h = login("cntt")
    than = {"loai": "nha_cung_cap", "rows": _lo_ncc("NCC thử – nạp lại hôm sau"),
            "ten_tep": "hom-sau.csv", "nguon": "nguoi_nhap"}

    a = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h)
    assert a.status_code == 201, a.text
    assert not a.json().get("lap_lai")

    # Đẩy mốc thời gian lùi ra NGOÀI cửa sổ – đúng cảnh "nạp lại vào hôm sau".
    with SessionLocal() as db:
        r = db.execute(select(KhoaGhi).order_by(KhoaGhi.id.desc())).scalars().first()
        r.luc = datetime.now() - GML_CUA_SO() - timedelta(minutes=1)
        db.commit()

    b = client.post("/api/v1/nap-du-lieu/nap", json=than, headers=h)
    assert b.status_code != 500, (
        "nạp lại sau cửa sổ 10 phút trả 500 – khóa chống ghi trùng tự đâm vào cột unique "
        "của chính nó. Đây là 67 tệp kho cũ T1 không nạp lại được trên bản chạy thật 16/9/2026.")
    assert b.status_code == 201, b.text
    assert not b.json().get("lap_lai"), "ngoài cửa sổ thì phải nạp THẬT, không trả kết quả cũ"

    # Và chỉ còn ĐÚNG MỘT dòng khóa cho nội dung ấy – ghi đè, không đẻ dòng thứ hai.
    with SessionLocal() as db:
        from app.services import ghi_mot_lan as GML
        khoa = GML.suy_khoa("/nap-du-lieu/nap", _ten_dang_nhap("cntt"),
                            {"loai": than["loai"], "rows": than["rows"],
                             "bo_qua_dong_loi": False})
        so = len(db.execute(select(KhoaGhi).where(KhoaGhi.khoa == khoa)).scalars().all())
    assert so == 1, f"có {so} dòng khóa cho cùng một nội dung – phải ghi đè, không thêm dòng"


def GML_CUA_SO():
    from app.services import ghi_mot_lan as GML
    return GML.CUA_SO_SUY_KHOA


def _ten_dang_nhap(vai: str) -> str:
    from sqlalchemy import select
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        return u.username
