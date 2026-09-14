"""V12 – form khế ước vay: kế toán tải tệp lên, hệ thống sinh lịch trả nợ bằng công thức.

Bộ nạp này khác phần lớn bộ nạp khác ở một chỗ, và cả tệp phép thử này xoay quanh chỗ đó: nó không
chỉ ghi một bản ghi, nó SINH RA hàng chục dòng lịch. Một khế ước sai công thức đẻ ra hàng chục dòng
lịch sai, và mỗi dòng lịch sai về sau thành một bút toán sai.

Phép thử quan trọng nhất không phải "sinh ra đủ số kỳ" – đó là điều dễ đúng. Quan trọng nhất là:
TỔNG GỐC TRONG LỊCH PHẢI BẰNG ĐÚNG SỐ TIỀN VAY. Chia 1,2 tỷ cho 7 kỳ rồi làm tròn từng kỳ là chỗ
một vài đồng rơi mất, và một đồng rơi mất trong lịch trả nợ là một đồng lệch giữa sổ và ngân hàng ở
kỳ cuối – đúng lúc tất toán, đúng lúc khó giải thích nhất.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v12form.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _x in (_DB, _DB + "-journal"):
    try:
        if os.path.exists(_x): os.remove(_x)
    except OSError:
        pass
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.services.lich_tra_no import sinh_lich, them_thang, CONG_THUC

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def login(vai: str = "ketoan") -> dict:
    from app.db.session import SessionLocal
    from app.models.core import User
    with SessionLocal() as s:
        u = s.execute(select(User).where(User.role == vai, User.active == True)).scalars().first()
        assert u is not None, f"dữ liệu mẫu không có vai trò {vai}"
        ten = u.username
    r = client.post("/api/v1/auth/login", data={"username": ten, "password": ten})
    if r.status_code != 200:
        r = client.post("/api/v1/auth/login", data={"username": ten, "password": "Vtos@Demo#2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ====================== 1. CÔNG THỨC – KHÔNG ĐƯỢC RƠI MẤT MỘT ĐỒNG ======================
@pytest.mark.parametrize("ct", list(CONG_THUC))
@pytest.mark.parametrize("goc,ky", [(1_200_000_000, 12), (1_000_000_000, 7), (999_999_999, 13),
                                    (100_000_000, 1), (7_777_777, 3)])
def test_tong_goc_trong_lich_bang_DUNG_so_tien_vay(ct, goc, ky):
    """Chia rồi làm tròn từng kỳ là chỗ vài đồng rơi mất. Kỳ cuối phải gánh phần dư."""
    r = sinh_lich(goc, 9.5, ky, date(2026, 10, 15), ct)
    assert r["tong_goc"] == float(round(goc)), f"{ct}: lệch {r['tong_goc'] - goc}"
    assert not r["canh_bao"], r["canh_bao"]
    assert r["dong"][-1]["du_no_sau"] == 0, "sau kỳ cuối vẫn còn dư nợ"
    assert len(r["dong"]) == ky


def test_lai_suat_0_khong_lam_no_cong_thuc_nien_kim():
    """Niên kim chia cho (1 − (1+i)^−n); i = 0 thì mẫu số bằng 0. Đây là nhánh RIÊNG, không phải một
    trường hợp con – và vay không lãi là chuyện có thật với khoản vay nội bộ."""
    r = sinh_lich(120_000_000, 0, 12, date(2026, 10, 15), "nien_kim")
    assert r["tong_lai"] == 0 and r["tong_goc"] == 120_000_000
    assert all(d["goc"] == 10_000_000 for d in r["dong"])


def test_goc_deu_lai_GIAM_DAN_con_nien_kim_tong_moi_ky_BANG_NHAU():
    """Hai công thức khác nhau ở đúng chỗ này. Lẫn lộn thì lịch trong VTOS lệch lịch ngân hàng ngay
    từ kỳ đầu mà tổng vẫn khớp – kiểu sai khó thấy nhất."""
    a = sinh_lich(1_200_000_000, 9.0, 12, date(2026, 10, 15), "goc_deu")["dong"]
    b = sinh_lich(1_200_000_000, 9.0, 12, date(2026, 10, 15), "nien_kim")["dong"]
    assert all(a[i]["lai"] > a[i + 1]["lai"] for i in range(len(a) - 1)), "gốc đều: lãi phải giảm dần"
    assert all(a[i]["goc"] == a[0]["goc"] for i in range(len(a) - 1)), "gốc đều: gốc phải bằng nhau"
    giua = [d["tong"] for d in b[:-1]]
    assert max(giua) - min(giua) <= 1, "niên kim: tổng mỗi kỳ phải bằng nhau"
    assert all(b[i]["goc"] < b[i + 1]["goc"] for i in range(len(b) - 2)), "niên kim: gốc phải tăng dần"


def test_cuoi_ky_chi_tra_goc_o_ky_CUOI():
    r = sinh_lich(500_000_000, 8.0, 6, date(2026, 10, 15), "cuoi_ky")["dong"]
    assert all(d["goc"] == 0 for d in r[:-1]) and r[-1]["goc"] == 500_000_000
    assert all(d["lai"] > 0 for d in r), "kiểu cuối kỳ vẫn trả lãi định kỳ"


def test_ngay_den_han_cong_THANG_chu_khong_cong_30_NGAY():
    """Cộng 30 ngày thì kỳ trả nợ trôi dần khỏi ngày ký, và sau một năm lịch của ta lệch lịch ngân
    hàng khoảng nửa tháng."""
    r = sinh_lich(120_000_000, 9.0, 13, date(2026, 1, 31), "goc_deu")["dong"]
    assert r[0]["ngay"] == date(2026, 1, 31)
    assert r[1]["ngay"] == date(2026, 2, 28), "ngày 31 rơi vào tháng ngắn phải lùi về cuối tháng"
    assert r[12]["ngay"] == date(2027, 1, 31), "sau 12 kỳ phải đúng cùng ngày năm sau"
    assert them_thang(date(2026, 3, 31), 1) == date(2026, 4, 30)


def test_so_lieu_la_bi_tu_choi_ngay_o_cong_thuc():
    for goc, ls, ky in ((0, 9, 12), (-1, 9, 12), (1_000_000, -1, 12), (1_000_000, 9, 0)):
        with pytest.raises(ValueError):
            sinh_lich(goc, ls, ky, date(2026, 10, 15))
    with pytest.raises(ValueError):
        sinh_lich(1_000_000, 9, 12, date(2026, 10, 15), "cong_thuc_khong_co")


# ====================== 2. CỬA NẠP ======================
def _dong(**kw):
    d = {"Số khế ước": "KU-THU-001", "Ngân hàng / bên cho vay": "TPBank – CN Bến Thành",
         "Số tiền vay": "1200000000", "Lãi suất (%/năm)": "9", "Số kỳ trả": "12",
         "Ngày trả kỳ đầu": "15/10/2026", "Công thức lịch trả nợ": "goc_deu",
         "Ngày ký khế ước": "01/09/2026", "Nhóm khoản vay": "vay_xe_45cho",
         "Tài sản bảo đảm": "Xe 50F-009.60", "Mục đích vay": "Mua xe 45 chỗ"}
    d.update(kw)
    return d


def _kiem(rows, who="ketoan"):
    return client.post("/api/v1/nap-du-lieu/kiem-tra", headers=login(who),
                       json={"loai": "khe_uoc_vay", "rows": rows})


def _nap(rows, who="ketoan", khoa=None):
    h = login(who)
    if khoa: h = {**h, "X-Khoa-Ghi": khoa}
    return client.post("/api/v1/nap-du-lieu/nap", headers=h,
                       json={"loai": "khe_uoc_vay", "rows": rows, "ten_tep": "khe_uoc.csv"})


def test_bo_nap_co_mat_va_khai_du_cot():
    r = client.get("/api/v1/nap-du-lieu/bo-nap", headers=login()).json()
    b = [x for x in r["bo_nap"] if x["ma"] == "khe_uoc_vay"]
    assert b, "chưa khai bộ nạp khế ước vay"
    assert b[0]["khoa_chong_trung"] == "Số khế ước"


def test_xem_truoc_noi_ro_lich_SE_sinh_ra_bao_nhieu():
    """Xem trước phải nói ra số kỳ và tổng lãi. Nạp một khế ước là cam kết mấy chục dòng lịch – người
    bấm phải thấy con số trước khi bấm, không phải sau."""
    r = _kiem([_dong()])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["hop_le"] == 1 and d["dong_loi"] == 0, d
    cb = " ".join(d["dong"][0].get("canh_bao", []))
    assert "12 kỳ" in cb and "tổng lãi" in cb, cb


def test_nap_that_sinh_dung_lich_va_KHONG_sinh_dong_so_tien_0():
    """Dòng lịch số tiền 0 là dòng không ai ghi sổ được mà vẫn nằm chờ trong danh sách."""
    from app.db.session import SessionLocal
    from app.models.finance import FinContract, FinSchedule
    r = _nap([_dong(**{"Số khế ước": "KU-THU-CUOI", "Công thức lịch trả nợ": "cuoi_ky",
                       "Số kỳ trả": "6", "Số tiền vay": "500000000"})])
    assert r.status_code == 201 and r.json()["da_nap"] == 1, r.text
    with SessionLocal() as db:
        c = db.execute(select(FinContract).where(
            FinContract.contract_no == "KU-THU-CUOI")).scalars().first()
        assert c is not None and c.principal == 500_000_000
        ds = db.execute(select(FinSchedule).where(FinSchedule.contract_id == c.id)).scalars().all()
    assert all(s.amount > 0 for s in ds), "có dòng lịch số tiền 0"
    goc = [s for s in ds if s.kind == "tra_goc"]
    lai = [s for s in ds if s.kind == "tra_lai"]
    assert len(goc) == 1 and goc[0].amount == 500_000_000, "kiểu cuối kỳ chỉ có MỘT dòng gốc"
    assert len(lai) == 6, "kiểu cuối kỳ vẫn trả lãi cả sáu kỳ"
    assert {s.ky for s in lai} == {1, 2, 3, 4, 5, 6}, "kỳ phải được đánh số"


def test_goc_va_lai_la_HAI_dong_lich_rieng():
    """Gốc và lãi là hai bút toán (quyết định 08/9: không bù trừ), nên phải là hai dòng lịch."""
    from app.db.session import SessionLocal
    from app.models.finance import FinContract, FinSchedule
    assert _nap([_dong(**{"Số khế ước": "KU-THU-DEU"})]).status_code == 201
    with SessionLocal() as db:
        c = db.execute(select(FinContract).where(
            FinContract.contract_no == "KU-THU-DEU")).scalars().first()
        ds = db.execute(select(FinSchedule).where(FinSchedule.contract_id == c.id)).scalars().all()
    assert len([s for s in ds if s.kind == "tra_goc"]) == 12
    assert len([s for s in ds if s.kind == "tra_lai"]) == 12
    assert sum(s.amount for s in ds if s.kind == "tra_goc") == 1_200_000_000


def test_nap_lai_cung_so_khe_uoc_thi_BO_QUA_khong_sinh_lich_lan_hai():
    """Sinh lịch lần hai là nhân đôi toàn bộ nghĩa vụ trả nợ trên hệ thống."""
    from app.db.session import SessionLocal
    from app.models.finance import FinContract, FinSchedule
    _nap([_dong(**{"Số khế ước": "KU-THU-TRUNG"})], khoa="ku-lan-1")
    with SessionLocal() as db:
        c = db.execute(select(FinContract).where(
            FinContract.contract_no == "KU-THU-TRUNG")).scalars().first()
        so_dong = len(db.execute(select(FinSchedule).where(
            FinSchedule.contract_id == c.id)).scalars().all())
    r = _nap([_dong(**{"Số khế ước": "KU-THU-TRUNG"})], khoa="ku-lan-2")
    assert r.json()["da_nap"] == 0 and r.json()["da_co"] == 1, r.text
    with SessionLocal() as db:
        assert len(db.execute(select(FinSchedule).where(
            FinSchedule.contract_id == c.id)).scalars().all()) == so_dong


def test_dong_loi_thi_KHONG_ghi_gi_ca():
    from app.db.session import SessionLocal
    from app.models.finance import FinContract
    r = _nap([_dong(**{"Số khế ước": "KU-THU-LOI", "Số tiền vay": "0"})])
    assert r.json()["da_nap"] == 0
    with SessionLocal() as db:
        assert db.execute(select(FinContract).where(
            FinContract.contract_no == "KU-THU-LOI")).scalars().first() is None


def test_cong_thuc_la_bi_chan_o_cua_nap():
    d = _kiem([_dong(**{"Số khế ước": "KU-CT-LA", "Công thức lịch trả nợ": "kieu_gi_do"})]).json()
    assert d["dong_loi"] == 1
    assert any("không hợp lệ" in x or "không có" in x for x in d["dong"][0]["loi"]), \
        d["dong"][0]["loi"]


def test_lai_suat_thang_nhap_nham_thanh_nam_thi_CANH_BAO():
    """9%/tháng gõ vào ô %/năm ra 108%/năm. Không chặn – có thể là vay nóng thật – nhưng phải nói."""
    d = _kiem([_dong(**{"Số khế ước": "KU-LS-CAO", "Lãi suất (%/năm)": "108"})]).json()
    assert d["hop_le"] == 1
    assert any("lãi suất THÁNG" in x for x in d["dong"][0]["canh_bao"]), d["dong"][0]["canh_bao"]


def test_thieu_nhom_vay_thi_canh_bao_chu_khong_chan():
    d = _kiem([_dong(**{"Số khế ước": "KU-KHONG-NHOM", "Nhóm khoản vay": ""})]).json()
    assert d["hop_le"] == 1
    assert any("nhóm khoản vay" in x.lower() for x in d["dong"][0]["canh_bao"])


def test_chi_KE_TOAN_va_quan_tri_nap_duoc():
    assert _nap([_dong(**{"Số khế ước": "KU-QUYEN"})], who="hcns").status_code == 403


def test_khe_uoc_vay_nam_trong_nhom_CHAM_TIEN():
    """Một dòng khế ước sai đẻ ra hàng chục dòng lịch sai. Nhập tay từng cái thì còn nhìn thấy."""
    from app.services.intake_phong_ban_2 import CHAM_TIEN
    assert "khe_uoc_vay" in CHAM_TIEN
