"""V8 – hai chặng cuối của luồng từ chứng từ đến báo cáo tài chính.

Bộ test này canh bốn cách một kỳ sổ có thể trông đã xong mà thật ra chưa:

  1. GHI SỔ HÀNG LOẠT MÀ ĐOÁN TÀI KHOẢN. Dòng sao kê không quy ước nào nhận phải nằm lại hàng chờ
     Kế toán, không được rơi vào một tài khoản "gần đúng". Một sổ trông đầy đủ mà sai thì tệ hơn
     một sổ còn thiếu và biết mình thiếu.
  2. BẤM GHI LÔ HAI LẦN THÀNH HAI BỘ BÚT TOÁN. Khóa là mã dòng sao kê, đặt ở chứng từ.
  3. KẾT CHUYỂN THEO ĐÚNG CHỮ CỦA QUY ƯỚC RỒI BỎ RƠI DOANH THU. Quy ước khai 5113; doanh thu thật
     nằm ở 5111, 5112 nữa. Chạy đúng chữ thì phần đó ở lại sổ và không có gì báo.
  4. SỐ BẢO HIỂM GHI SỔ ĐƯỢC TÍNH LẠI THEO TỶ LỆ thay vì lấy từ bảng lương. Hai con số chỉ khác nhau
     khi bảng lương có ngoại lệ – và đúng lúc đó thì không ai phát hiện, vì cả hai đều "đúng công
     thức". Lệnh giao việc 08/9 nêu đích danh điều này.
"""
import os, sys, tempfile
_DB = os.path.join(tempfile.gettempdir(), "vtos_test_ketso.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    if os.path.exists(_DB): os.remove(_DB)
except OSError:
    pass
from datetime import datetime, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app

KY = "2026-04"        # kỳ riêng của bộ test, để không đụng dữ liệu mẫu


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


@pytest.fixture()
def ke_toan(db):
    from app.models.core import User
    return db.execute(select(User).where(User.role == "ketoan")).scalars().first()


def txn(db, chieu, so_tien, noi_dung, ngay=f"{KY}-15", ma=""):
    from app.models.payments import BankTransaction
    t = BankTransaction(sepay_id=f"T{datetime.now().timestamp()}{so_tien}{noi_dung[:4]}",
                        gateway="TPBank", account_number="01811267101",
                        transaction_date=datetime.fromisoformat(f"{ngay}T10:00:00"),
                        transfer_type=chieu, amount=so_tien, content=noi_dung,
                        reference_code=ma or f"REF{int(so_tien)}")
    db.add(t); db.flush()
    return t


def but_toan(db, ngay, lines, mo_ta="thử"):
    from app.services import accounting as ACC
    from app.models.core import User
    u = db.execute(select(User).where(User.role == "ketoan")).scalars().first()
    for l in lines:                      # 131/331 bắt buộc có mã đối tượng – đúng luật của sổ
        l.setdefault("partner_code", "KH-THU"); l.setdefault("partner", "Khách thử")
        l.setdefault("project_code", "TOUR-THU")
    return ACC.post_entry(db, u.username, u.role, date.fromisoformat(ngay), mo_ta, lines,
                          "thu_cong", f"test:{datetime.now().timestamp()}")


# ====================== SAO KÊ VÀO SỔ HÀNG LOẠT ======================
def test_dong_khong_quy_uoc_nao_nhan_thi_cho_ke_toan_chu_khong_bi_doan(db):
    from app.services import ket_so as KS
    txn(db, "out", 3_500_000, "ND KHONG GIONG BAT KY QUY UOC NAO XYZQ")
    xt = KS.xem_truoc_sao_ke(db, KY)
    ids_chua = {x["id"] for x in xt["chua_nhan_dien"]}
    ids_khop = {x["id"] for x in xt["khop"]}
    assert ids_chua and not (ids_chua & ids_khop)
    assert all(x.get("ly_do") for x in xt["chua_nhan_dien"])
    assert "định khoản tay" in xt["ghi_chu"]


def test_dong_so_tien_khong_duong_khong_bao_gio_vao_ro_khop(db):
    from app.services import ket_so as KS
    t = txn(db, "in", 0, "Giao dich 0 dong")
    xt = KS.xem_truoc_sao_ke(db, KY)
    assert t.id in {x["id"] for x in xt["chua_nhan_dien"]}
    assert t.id not in {x["id"] for x in xt["khop"]}


def test_xem_truoc_khong_ghi_gi(db):
    from app.services import ket_so as KS
    from app.models.accounting import JournalEntry
    txn(db, "in", 12_000_000, "Thanh toan tour")
    truoc = db.execute(select(JournalEntry)).scalars().all()
    KS.xem_truoc_sao_ke(db, KY)
    assert len(db.execute(select(JournalEntry)).scalars().all()) == len(truoc)


def test_tien_vao_chua_khop_don_nhan_dung_quy_uoc_treo_cho_xac_dinh(db):
    """Quy ước THU_CHUA_RO: tiền vào chưa biết của đơn nào thì treo 3388, KHÔNG ghi doanh thu.
    Khóa `khop_don` máy tự suy ra từ dữ liệu – đây là chỗ bản đầu quên truyền, và hậu quả không phải
    là báo lỗi mà là mọi dòng đều rơi vào rổ 'chưa nhận diện'."""
    from app.services import ket_so as KS
    t = txn(db, "in", 7_000_000, "Khach thanh toan tour PT")
    xt = KS.xem_truoc_sao_ke(db, KY)
    x = next(x for x in xt["chua_nhan_dien"] if x["id"] == t.id)
    # Nhận ra quy ước rồi, nhưng chưa ghi được vì 3388 bắt buộc có mã đối tượng.
    assert x["quy_tac"] == "THU_CHUA_RO" and x["can_bo_sung"] and "3388" in x["ly_do"]
    # Kế toán chỉ ra người chuyển tiền là ai → ghi được.
    pl = {t.id: {"ma_doi_tuong": "KH-CHUA-RO", "doi_tuong": "Nguyễn Văn A"}}
    x2 = next(x for x in KS.xem_truoc_sao_ke(db, KY, pl)["khop"] if x["id"] == t.id)
    assert {l["account"] for l in x2["lines"]} == {"1121", "3388"}


def test_chi_ra_quy_uoc_khong_bao_gio_ghi_duoc_o_cap_QUY_UOC(db):
    """Nguyên tắc của phân hệ là 'người sửa quy tắc chứ không sửa từng bút toán', nên một quy ước
    hỏng phải được chỉ ra ở cấp quy ước – không để người dùng đi sửa từng dòng dữ liệu của mình."""
    from app.services import ket_so as KS
    ds = KS.quy_uoc_khong_bao_gio_ghi_duoc(db)
    ma = {x["quy_tac"] for x in ds}
    assert "THU_CHUA_RO" in ma, "quy ước ghi vào 3388 mà khai 'không cần đối tượng' phải bị chỉ ra"
    assert all("hai chữ ký" in x["ly_do"] for x in ds), "không được tự sửa quy ước"


def test_ghi_lo_hai_lan_khong_thanh_hai_bo_but_toan(db, ke_toan):
    from app.services import ket_so as KS
    t = txn(db, "in", 7_100_000, "Khach thanh toan tour PT")
    pl = {t.id: {"ma_doi_tuong": "KH-01", "doi_tuong": "Khách 01"}}
    lan1 = KS.ghi_so_sao_ke(db, ke_toan, KY, phan_loai=pl)
    assert len(lan1["da_ghi"]) >= 1 and not lan1["hong"]
    lan2 = KS.ghi_so_sao_ke(db, ke_toan, KY, phan_loai=pl)
    assert lan2["da_ghi"] == [], "bấm lần thứ hai không được sinh bút toán thứ hai"


def test_ghi_lo_chi_ghi_dong_duoc_chi_dinh(db, ke_toan):
    from app.services import ket_so as KS
    a = txn(db, "in", 5_100_000, "Khach A thanh toan")
    b = txn(db, "in", 5_200_000, "Khach B thanh toan")
    pl = {a.id: {"ma_doi_tuong": "KH-A"}, b.id: {"ma_doi_tuong": "KH-B"}}
    kq = KS.ghi_so_sao_ke(db, ke_toan, KY, chi_dinh=[a.id], phan_loai=pl)
    assert [x["id"] for x in kq["da_ghi"]] == [a.id]


def test_tien_ra_khong_doan_muc_chi_nhung_noi_ro_phan_loai_nao_se_khop(db, ke_toan):
    """Sao kê KHÔNG nói một dòng tiền ra 50 triệu là trả nhà cung cấp hay tạm ứng hay trả gốc vay.
    Máy không đoán hộ – nhưng nó phải nói được rằng phân loại NÀO sẽ khớp, nếu không thì người dùng
    chọn bừa, và một dòng phân loại bừa nguy hiểm hơn một dòng để trống."""
    from app.services import ket_so as KS
    t = txn(db, "out", 50_000_000, "CK cho doi tac")
    xt = KS.xem_truoc_sao_ke(db, KY)
    x = next(x for x in xt["chua_nhan_dien"] if x["id"] == t.id)
    goi_y = {g["gia_tri"] for g in x["phan_loai_giup_khop"]}
    assert "tra_ncc" in goi_y and "tam_ung" in goi_y

    # Kế toán chọn phân loại → cùng dòng đó nhận diện được và ghi sổ được.
    pl = {t.id: {"muc_chi": "tra_ncc", "ma_ncc": "NCC-001", "ncc": "Đối tác thử"}}
    xt2 = KS.xem_truoc_sao_ke(db, KY, pl)
    x2 = next(x for x in xt2["khop"] if x["id"] == t.id)
    assert x2["quy_tac"] == "TRA_NCC" and {l["account"] for l in x2["lines"]} == {"331", "1121"}
    kq = KS.ghi_so_sao_ke(db, ke_toan, KY, chi_dinh=[t.id], phan_loai=pl)
    assert len(kq["da_ghi"]) == 1


def test_ky_da_khoa_thi_khong_ghi_lo_duoc(db, ke_toan):
    from app.services import ket_so as KS
    from app.models.accounting import PeriodLock
    db.add(PeriodLock(period="2026-03", locked_by="ketoan")); db.flush()
    with pytest.raises(KS.KhongGhiDuoc) as ex:
        KS.ghi_so_sao_ke(db, ke_toan, "2026-03")
    assert "đã khóa" in str(ex.value)


# ====================== KẾT CHUYỂN ======================
def test_ket_chuyen_lay_tai_khoan_tu_so_chu_khong_tu_chu_cua_quy_uoc(db):
    """Quy ước khai đích danh 5113. Doanh thu thật của công ty nằm ở nhiều tài khoản 511 – chạy đúng
    chữ thì phần đó ở lại sổ sau kết chuyển và không có gì báo."""
    from app.services import ket_so as KS
    from app.models.accounting import Account
    co = {a.code for a in db.execute(select(Account)).scalars()}
    tk_dt = [c for c in ("5111", "5112", "5113") if c in co]
    if len(tk_dt) < 2:
        pytest.skip("danh mục mẫu chỉ có một tài khoản doanh thu")
    for i, tk in enumerate(tk_dt):
        but_toan(db, f"{KY}-10", [{"account": "131", "debit": 1_000_000 * (i + 1)},
                                  {"account": tk, "credit": 1_000_000 * (i + 1)}])
    xt = KS.xem_truoc_ket_chuyen(db, KY)
    b1 = next(b for b in xt["buoc"] if b["buoc"] == 1)
    assert {d["tk"] for d in b1["dong"]} >= set(tk_dt), "phải kết chuyển MỌI tài khoản doanh thu có số dư"


def test_tai_khoan_kqkd_khong_thuoc_buoc_nao_thi_bao_len_chu_khong_bo_im(db):
    from app.services import ket_so as KS
    assert "tai_khoan_khong_thuoc_buoc_nao" in KS.xem_truoc_ket_chuyen(db, KY)
    # Nhóm của ba bước cộng lại phải phủ hết tiền tố kết quả kinh doanh thường gặp; cái nào lọt ra
    # ngoài thì đã có rổ riêng ở trên, không có đường nào rơi im lặng.
    phu = set()
    for d in KS.BUOC_KET_CHUYEN.values(): phu |= set(d["tien_to"])
    assert {"511", "632", "642", "641", "635", "515", "711", "811", "821"} <= phu


def test_ket_chuyen_bon_buoc_ghi_duoc_va_khong_ghi_lai_lan_hai(db, ke_toan):
    from app.services import ket_so as KS
    but_toan(db, f"{KY}-11", [{"account": "131", "debit": 20_000_000},
                              {"account": "5113", "credit": 20_000_000}])
    but_toan(db, f"{KY}-12", [{"account": "632", "debit": 12_000_000},
                              {"account": "331", "credit": 12_000_000}])
    but_toan(db, f"{KY}-13", [{"account": "642", "debit": 3_000_000},
                              {"account": "331", "credit": 3_000_000}])
    kq = KS.ket_chuyen(db, ke_toan, KY)
    assert {x["buoc"] for x in kq["da_ghi"]} == {1, 2, 3, 4}
    lai = KS.xem_truoc_ket_chuyen(db, KY)
    assert all(b["da_ghi"] for b in lai["buoc"])
    lan2 = KS.ket_chuyen(db, ke_toan, KY)
    assert lan2["da_ghi"] == [] and len(lan2["bo_qua"]) == 4


def test_sau_ket_chuyen_tai_khoan_kqkd_ve_khong(db, ke_toan):
    """Phép thử thật sự của kết chuyển: sổ sau khi chạy phải sạch, không còn số dư nào ở nhóm 5–8."""
    from app.services import ket_so as KS
    but_toan(db, f"{KY}-14", [{"account": "131", "debit": 9_000_000},
                              {"account": "5113", "credit": 9_000_000}])
    but_toan(db, f"{KY}-15", [{"account": "642", "debit": 4_000_000},
                              {"account": "331", "credit": 4_000_000}])
    KS.ket_chuyen(db, ke_toan, KY)
    con = {k: v for k, v in KS._du_trong_ky(db, KY).items() if not k.startswith("911")}
    assert not con, f"còn số dư chưa kết chuyển: {con}"


def test_lai_va_lo_ghi_nguoc_chieu_nhau(db, ke_toan):
    from app.services import ket_so as KS
    from app.models.accounting import JournalEntry, JournalLine
    ky = "2026-05"
    # Lỗ: chi phí lớn hơn doanh thu.
    but_toan(db, f"{ky}-10", [{"account": "131", "debit": 2_000_000},
                              {"account": "5113", "credit": 2_000_000}])
    but_toan(db, f"{ky}-11", [{"account": "642", "debit": 6_000_000},
                              {"account": "331", "credit": 6_000_000}])
    xt = KS.xem_truoc_ket_chuyen(db, ky)
    assert xt["lai_truoc_buoc_4"] < 0
    KS.ket_chuyen(db, ke_toan, ky)
    e = db.execute(select(JournalEntry).where(
        JournalEntry.source_ref == f"kc:{ky}:4")).scalars().first()
    no_4212 = sum(l.debit for l in e.lines if l.account_code == KS.TK_LAI_LO)
    assert no_4212 > 0, "lỗ phải ghi Nợ 4212 – Có 911, ngược chiều với lãi"


def test_ket_chuyen_khong_chay_tren_ky_da_khoa(db, ke_toan):
    from app.services import ket_so as KS
    from app.models.accounting import PeriodLock
    db.add(PeriodLock(period="2026-02", locked_by="ketoan")); db.flush()
    with pytest.raises(KS.KhongGhiDuoc):
        KS.ket_chuyen(db, ke_toan, "2026-02")


# ====================== BÚT TOÁN LƯƠNG – ĐIỀU LỆNH NÊU ĐÍCH DANH ======================
def test_so_bao_hiem_ghi_so_lay_tu_bang_luong_khong_tinh_lai_theo_ty_le(db):
    """Lệnh giao việc 08/9: 'số bảo hiểm LẤY TỪ BẢNG LƯƠNG, không tính lại theo tỷ lệ'.

    Cách canh: dựng một bảng lương có số bảo hiểm CỐ Ý lệch khỏi mọi tỷ lệ chuẩn, rồi đòi bút toán
    ghi ra đúng con số lệch đó. Nếu người sau thay bằng một phép nhân tỷ lệ, phép thử này đỏ.
    """
    from app.models.hr import PayrollRun, Employee
    from app.models.accounting import JournalEntry, JournalLine
    from app.services import hr as HR
    e = db.execute(select(Employee).where(Employee.contract_type == "hdld")).scalars().first()
    ky = "2026-01"
    LECH = 1_234_567       # không bằng bất kỳ tỷ lệ nào nhân với lương
    run = PayrollRun(period=ky, status="hcns_lap", totals={"thuc_nhan": 0}, inputs={},
                     rows=[{"ma": e.code, "ho_ten": e.full_name, "hop_dong": "hdld",
                            "luong_cb": 10_000_000, "bien_doi": 0, "tncn": 0,
                            "bhxh": LECH, "doan_phi": 0}])
    db.add(run); db.flush()
    ids = HR.post_payroll_entries(db, run)
    assert ids
    tong_3383 = 0.0
    for i in ids:
        for l in db.get(JournalEntry, i).lines:
            if l.account_code == "3383":
                tong_3383 += l.credit
    assert tong_3383 == LECH, "số bảo hiểm ghi sổ phải bằng đúng số trên bảng lương"


# ====================== TRẠNG THÁI CẢ KỲ ======================
def test_tinh_trang_ky_noi_ro_con_thieu_chang_nao(db):
    from app.services import ket_so as KS
    txn(db, "out", 4_000_000, "ND KHONG AI NHAN QQQQ")
    tt = KS.tinh_trang_ky(db, KY)
    assert tt["chua_xong"] and tt["san_sang_len_bao_cao"] is False
    assert any("chưa định khoản" in x for x in tt["chua_xong"])
    # Nói thẳng rằng "sẵn sàng" không có nghĩa là "đúng".
    assert "KHÔNG có nghĩa là" in tt["ghi_chu"]


def test_chi_ke_toan_moi_ghi_so_duoc():
    """Chủ tịch và TGĐ XEM được cả kỳ nhưng không ghi thay – chặn ở API, không ở menu."""
    from app.api.v1.ket_so import XEM, GHI
    assert GHI == ("ketoan",)
    assert "chutich" in XEM and "chutich" not in GHI and "tgd" not in GHI


def test_menu_va_pham_vi_api_khop_nhau():
    from app.services.access import MENU_ROLES, pham_vi_api
    for vt in MENU_ROLES["/ket-so"]:
        assert "/api/v1/ket-so" in pham_vi_api(vt), f"{vt} thấy màn hình mà không chạm được API"
