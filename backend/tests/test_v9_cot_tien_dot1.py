"""V9 đợt 1 – tám cột tiền chạm sổ kế toán đổi sang số thập phân.

Nghiệm thu V9 đòi hai điều, và bộ test này canh cả hai:

    "bộ kiểm K1 giảm ĐÚNG số cột đã sửa"           – không nhiều hơn, không ít hơn
    "tổng phát sinh mọi tài khoản trước–sau KHÔNG LỆCH MỘT ĐỒNG"

Điều thứ hai có một cái bẫy mà bộ test phải tránh: một hàm so sánh luôn trả về "khớp" cũng làm mọi
phép thử xanh. Nên ở đây có phép thử NGƯỢC – dựng một chênh lệch đúng một đồng và đòi bộ đối chiếu
phải kêu lên. Một bộ đối chiếu không phát hiện được cái sai thì việc nó nói "khớp" chẳng chứng minh
điều gì.

Và một điều nữa phải nói thẳng trong chính bộ test, vì nó dễ bị đọc nhầm thành "V9 đã xong": đợt này
đổi CỘT TRONG CƠ SỞ DỮ LIỆU, Python vẫn nhận float. Có phép thử ghi rõ điều đó để người sau không
tưởng số học phía Python đã thành số thập phân.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_v9.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, Float, Numeric
from app.main import app

# Tám cột của đợt 1, viết thẳng ra ở đây LẦN THỨ BA (mô hình, bản nâng cấp, bộ test). Cố ý lặp: ba
# chỗ cùng liệt kê thì lệch nhau là phép thử đỏ ngay, còn một chỗ khai chung thì cả ba cùng sai theo.
DOT1 = {
    ("journal_lines", "debit"), ("journal_lines", "credit"),
    ("invoices", "pre_tax"), ("invoices", "vat"), ("invoices", "total"),
    ("receipts", "amount"), ("bank_transactions", "amount"), ("payment_requests", "amount"),
}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


@pytest.fixture()
def db():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s
        s.rollback()


def _cot(bang: str, cot: str):
    from app.db.session import Base
    return Base.metadata.tables[bang].columns[cot]


# ====================== 1. ĐÚNG TÁM CỘT, KHÔNG THỪA KHÔNG THIẾU ======================
def test_dung_tam_cot_da_doi_sang_so_thap_phan():
    for bang, cot in DOT1:
        assert isinstance(_cot(bang, cot).type, Numeric), f"{bang}.{cot} chưa đổi"
        assert not isinstance(_cot(bang, cot).type, Float), f"{bang}.{cot} vẫn là số thực nhị phân"


def test_khong_doi_nham_cot_khong_phai_tien():
    """vat_rate là TỶ LỆ (0,08), không phải tiền. Đổi nhầm một cột không phải tiền cũng tốn đúng một
    lần nâng cấp cơ sở dữ liệu."""
    assert isinstance(_cot("invoices", "vat_rate").type, Float)


def test_moi_cot_tien_doi_dung_18_2():
    for bang, cot in DOT1:
        t = _cot(bang, cot).type
        assert (t.precision, t.scale) == (18, 2), f"{bang}.{cot} = {t.precision},{t.scale}"


def test_python_van_nhan_float_va_dieu_do_la_co_y():
    """Đợt này đổi chỗ SỐ NẰM, chưa đổi số học phía Python. Ghi thành phép thử để người sau không
    tưởng V9 đã xong – nửa thứ hai (bật Decimal theo từng phân hệ) CÒN NỢ."""
    from app.models.kieu_tien import TIEN
    assert TIEN.asdecimal is False
    for bang, cot in DOT1:
        assert _cot(bang, cot).type.asdecimal is False


def test_mo_hinh_va_ban_nang_cap_khong_duoc_lech_nhau():
    """Ba chỗ cùng liệt kê tám cột. Lệch nhau là bản nâng cấp đổi một tập, mô hình khai một tập khác –
    và cơ sở dữ liệu thật sẽ không giống mô hình mà không ai biết."""
    import importlib.util, pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions" / \
        "v9a1d6b4f8c02_v9_dot1_cot_tien_so_ke_toan.py"
    spec = importlib.util.spec_from_file_location("v9mig", p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert {(b, c) for b, c, _ in m.COT} == DOT1
    assert (m.TIEN.precision, m.TIEN.scale) == (18, 2)


# ====================== 2. BỘ KIỂM K1 GIẢM ĐÚNG TÁM ======================
def test_K1_giam_dung_so_cot_da_sua(db):
    from app.services import ks_cot_tien as CT
    CT.dong_bo(db); CT.nap_quyet_dinh(db); db.flush()
    rows = CT._hieu_luc(db)
    con_float = {(r.bang, r.cot) for r in rows if r.xep() == "tien" and r.kieu == "Float"}
    assert not (con_float & DOT1), f"còn sót trong danh sách đợt 1: {con_float & DOT1}"
    # Và tám cột đó phải có mặt trong sổ rà soát với kiểu MỚI – không phải biến mất khỏi sổ.
    da_doi = {(r.bang, r.cot) for r in rows if r.kieu == "Numeric"}
    assert DOT1 <= da_doi, f"thiếu khỏi sổ rà soát: {DOT1 - da_doi}"


# ====================== 3. TỔNG TRƯỚC – SAU ======================
def _but_toan(db, ngay, lines):
    from app.services import accounting as ACC
    from app.models.core import User
    u = db.execute(select(User).where(User.role == "ketoan")).scalars().first()
    for l in lines:
        l.setdefault("partner_code", "DT-V9"); l.setdefault("partner", "Đối tượng thử")
        l.setdefault("project_code", "TOUR-V9")
    return ACC.post_entry(db, u.username, u.role, date.fromisoformat(ngay), "thử V9", lines,
                          "thu_cong", f"v9:{ngay}:{lines[0]['account']}:{lines[0].get('debit', 0)}")


def test_tong_theo_tai_khoan_khop_tuyet_doi_qua_mot_vong_ghi_doc(db):
    """Ghi vào rồi đọc ra, tổng phải khớp tuyệt đối – kể cả với số lẻ hàng đồng."""
    from app.services import v9_doi_chieu as DC
    _but_toan(db, "2026-02-10", [{"account": "131", "debit": 12_345_678},
                                 {"account": "5113", "credit": 12_345_678}])
    _but_toan(db, "2026-02-11", [{"account": "632", "debit": 7_654_321},
                                 {"account": "331", "credit": 7_654_321}])
    db.flush()
    a = DC.chup(db)
    tk = a["theo_tai_khoan"]
    assert tk["131"]["no"] == 12_345_678, tk["131"]
    assert tk["632"]["no"] == 7_654_321, tk["632"]
    # Sổ phải cân: tổng Nợ = tổng Có trên toàn bộ tài khoản.
    assert round(sum(v["no"] for v in tk.values()) - sum(v["co"] for v in tk.values()), 2) == 0


def test_bo_doi_chieu_PHAT_HIEN_DUOC_lech_mot_dong(db):
    """Phép thử ngược, và là phép thử quan trọng nhất của tệp này.

    Một hàm so sánh luôn trả 'khớp' cũng làm mọi phép thử khác xanh. Nếu bộ đối chiếu không kêu lên
    được khi lệch đúng một đồng thì việc nó nói 'khớp' chẳng chứng minh điều gì."""
    from app.services import v9_doi_chieu as DC
    truoc = {"cot": {"journal_lines.debit": {"tong": 1_000_000.0, "so_dong": 10,
                                             "so_dong_co_le_duoi_dong": 0}},
             "theo_tai_khoan": {"131": {"no": 1_000_000.0, "co": 0.0, "so_dong": 10}}}
    sau = {"cot": {"journal_lines.debit": {"tong": 1_000_001.0, "so_dong": 10,
                                           "so_dong_co_le_duoi_dong": 0}},
           "theo_tai_khoan": {"131": {"no": 1_000_001.0, "co": 0.0, "so_dong": 10}}}
    kq = DC.so_sanh(truoc, sau)
    assert kq["khop"] is False
    assert kq["lech_theo_cot"][0]["lech"] == 1.0
    assert kq["lech_theo_tai_khoan"][0]["lech_no"] == 1.0
    assert "Không đóng đợt nâng cấp" in kq["ket_luan"]


def test_bo_doi_chieu_phat_hien_duoc_mat_dong(db):
    """Mất dòng mà tổng vẫn bằng nhau vẫn là mất dữ liệu – phải kêu lên."""
    from app.services import v9_doi_chieu as DC
    truoc = {"cot": {"receipts.amount": {"tong": 500.0, "so_dong": 5, "so_dong_co_le_duoi_dong": 0}},
             "theo_tai_khoan": {}}
    sau = {"cot": {"receipts.amount": {"tong": 500.0, "so_dong": 4, "so_dong_co_le_duoi_dong": 0}},
           "theo_tai_khoan": {}}
    assert DC.so_sanh(truoc, sau)["khop"] is False


def test_hai_anh_chup_giong_nhau_thi_khop(db):
    from app.services import v9_doi_chieu as DC
    a = DC.chup(db)
    assert DC.so_sanh(a, a)["khop"] is True


# ====================== 4. CẢNH BÁO LÀM TRÒN ======================
def test_canh_bao_lam_tron_keu_len_khi_co_le_duoi_dong():
    """Đổi sang numeric(18,2) là thay đổi KHÔNG QUAY LẠI ĐƯỢC với phần lẻ thứ ba trở đi. Phải đếm
    trước khi nâng cấp, không phải phát hiện sau."""
    from app.services import v9_doi_chieu as DC
    ds = DC.canh_bao_lam_tron({"cot": {
        "journal_lines.debit": {"tong": 1.0, "so_dong": 1, "so_dong_co_le_duoi_dong": 3},
        "receipts.amount": {"tong": 1.0, "so_dong": 1, "so_dong_co_le_duoi_dong": 0},
    }})
    assert len(ds) == 1 and "journal_lines.debit" in ds[0] and "LÀM TRÒN" in ds[0]


def test_khong_dem_duoc_thi_noi_KHONG_BIET_chu_khong_noi_khong():
    from app.services import v9_doi_chieu as DC
    ds = DC.canh_bao_lam_tron({"cot": {
        "invoices.total": {"tong": 0.0, "so_dong": 0, "so_dong_co_le_duoi_dong": None}}})
    assert len(ds) == 1 and "KHÔNG ĐẾM ĐƯỢC" in ds[0]


def test_chup_that_tren_csdl_dem_duoc_phan_le(db):
    """Trên cơ sở dữ liệu thật, phép đếm phần lẻ phải chạy được – trả None nghĩa là câu lệnh hỏng và
    người vận hành sẽ đi nâng cấp mà không biết mình mất gì."""
    from app.services import v9_doi_chieu as DC
    a = DC.chup(db)
    for k, v in a["cot"].items():
        assert "loi" not in v, f"{k}: {v.get('loi')}"
        assert v["so_dong_co_le_duoi_dong"] is not None, k
