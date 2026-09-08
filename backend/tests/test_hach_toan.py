"""Bộ quy tắc hạch toán và cổng chặn giá vốn.

Bốn phép thử quan trọng nhất, vì bốn cái này hỏng thì sổ vẫn "chạy được" mà số sai:
  - test_khong_khop_thi_noi_khong_khop: máy không được đoán tài khoản. Đoán sai một lần là sai cả kỳ.
  - test_chan_don_thieu_gia_von: đơn thiếu giá vốn mà ghi doanh thu thì đơn đó lãi 100%.
  - test_bien_qua_cao_cung_bi_giu: giá vốn nhỏ bất thường cũng là thiếu dòng chi phí, không phải lãi.
  - test_but_toan_luon_can_va_khong_lech_dong_nao: tách thuế bằng phép chia luôn có rủi ro lệch 1đ.
"""
import os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:///./test_hach_toan.db"; os.environ["SEED_DEMO"] = "1"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_hach_toan.db", "test_hach_toan.db-journal"):
    if os.path.exists(_f): os.remove(_f)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.models.core import User, Tour
from app.models.accounting import Account
from app.models.hach_toan import QuyTacHachToan, ThieuGiaVon
from app.services import hach_toan as HT
from app.services import cong_chan as CC

client = TestClient(app)
MK = "hachtoan123456"


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client; client = c
        from app.db.session import SessionLocal
        from app.core.security import hash_password
        db = SessionLocal()
        for vai in ("chutich", "tgd", "ketoan", "cntt", "bks", "tp_dh"):
            un = f"ht_{vai}"
            if db.execute(select(User).where(User.username == un)).scalars().first() is None:
                db.add(User(username=un, full_name=f"Thử {vai}", role=vai, department="Kiểm thử",
                            password_hash=hash_password(MK), active=True))
        db.commit(); db.close()
        yield


def login(vai):
    r = client.post("/api/v1/auth/login", data={"username": f"ht_{vai}", "password": MK})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def db_():
    from app.db.session import SessionLocal
    return SessionLocal()


# ============================ BỘ QUY TẮC ============================
def test_nap_mac_dinh_du_va_chay_lai_khong_nhan_doi():
    db = db_()
    n1 = len(db.execute(select(QuyTacHachToan)).scalars().all())
    assert n1 == len(HT.MAC_DINH), f"khởi động phải nạp đủ {len(HT.MAC_DINH)} quy tắc, đang có {n1}"
    HT.nap_mac_dinh(db); HT.nap_mac_dinh(db)
    assert len(db.execute(select(QuyTacHachToan)).scalars().all()) == n1
    db.close()


def test_moi_quy_tac_tro_toi_tai_khoan_co_that():
    """Một quy tắc trỏ vào tài khoản không có trong danh mục thì nghiệp vụ đó chết lúc ghi sổ,
    và chết ở tận cuối tháng khi kế toán khóa kỳ."""
    db = db_()
    thieu = []
    for q in db.execute(select(QuyTacHachToan)).scalars():
        for tk in (q.tk_no, q.tk_co, q.tk_thue):
            if tk and db.get(Account, tk) is None:
                thieu.append((q.ma, tk))
    assert not thieu, f"quy tắc trỏ vào tài khoản không có trong danh mục: {thieu}"
    db.close()


def test_quy_tac_tach_thue_phai_khai_du_ba_o():
    """ty_le_thue mà thiếu tk_thue hoặc thiếu ben_thue thì thuế biến mất khỏi bút toán mà không báo lỗi."""
    db = db_()
    for q in db.execute(select(QuyTacHachToan)).scalars():
        if q.ty_le_thue:
            assert q.tk_thue and q.ben_thue in ("no", "co"), f"{q.ma} khai thuế thiếu ô"
        if q.tk_thue:
            assert q.ty_le_thue > 0, f"{q.ma} có tài khoản thuế mà tỷ lệ bằng 0"
    db.close()


def test_uu_tien_khong_trung_trong_cung_mot_nguon():
    """Hai quy tắc cùng nguồn cùng ưu tiên thì thứ tự xét phụ thuộc mã – tức là phụ thuộc may rủi."""
    db = db_()
    thay: dict[tuple, list] = {}
    for q in db.execute(select(QuyTacHachToan).where(QuyTacHachToan.status == "active")).scalars():
        thay.setdefault((q.nguon, q.uu_tien), []).append(q.ma)
    trung = {k: v for k, v in thay.items() if len(v) > 1}
    assert not trung, f"trùng ưu tiên trong cùng nguồn: {trung}"
    db.close()


def test_chon_dung_quy_tac_theo_boi_canh():
    db = db_()
    assert HT.chon(db, "tien_vao", {"khop_don": True}).ma == "THU_KHACH"
    assert HT.chon(db, "tien_vao", {"khop_don": False}).ma == "THU_CHUA_RO"
    assert HT.chon(db, "tien_vao", {"khop_don": False, "noi_dung": "bao luu khach huy"}).ma == "THU_BAO_LUU"
    assert HT.chon(db, "mua_vao", {"co_hoa_don": True}).ma == "MUA_CO_HD"
    assert HT.chon(db, "mua_vao", {"co_hoa_don": False}).ma == "MUA_KHONG_HD"
    assert HT.chon(db, "tien_ra", {"muc_chi": "cong_tac"}).ma == "CHI_PHI_CONG_TAC"
    db.close()


def test_khong_khop_thi_noi_khong_khop():
    """Bối cảnh thiếu dữ liệu thì KHÔNG được rơi vào một quy tắc gần đúng."""
    db = db_()
    assert HT.chon(db, "mua_vao", {}) is None
    ra = HT.xem_truoc(db, "mua_vao", 1_000_000, {})
    assert ra["khop"] is False and "Kế toán" in ra["ly_do"]
    assert "lines" not in ra
    db.close()


# ============================ DỰNG BÚT TOÁN ============================
def test_doanh_thu_tach_thue_dau_ra():
    db = db_()
    q = HT.chon(db, "quyet_toan", {"da_ket_thuc": True, "co_gia_von": True})
    assert q.ma == "DOANH_THU"
    bt = HT.dung_but_toan(q, 108_000_000, {"ma": "KLE010826", "khach": "Cty ABC", "ten": "Visa Hàn Quốc"})
    tk = {l["account"]: (l.get("debit", 0), l.get("credit", 0)) for l in bt["lines"]}
    assert tk["131"][0] == 108_000_000
    assert tk["5113"][1] == 100_000_000
    assert tk["3331"][1] == 8_000_000
    assert all(l["project_code"] == "KLE010826" for l in bt["lines"])
    db.close()


def test_mua_vao_tach_thue_dau_vao_ben_no():
    db = db_()
    q = HT.chon(db, "mua_vao", {"co_hoa_don": True})
    bt = HT.dung_but_toan(q, 54_000_000, {"ma": "KLE010826", "ncc": "Resort Vĩnh Hy"})
    tk = {l["account"]: (l.get("debit", 0), l.get("credit", 0)) for l in bt["lines"]}
    assert tk["154"][0] == 50_000_000 and tk["133"][0] == 4_000_000 and tk["331"][1] == 54_000_000
    db.close()


def test_but_toan_luon_can_va_khong_lech_dong_nao():
    """Tách thuế bằng phép chia: 1.000.001đ chia 1,08 không tròn. Bút toán vẫn phải cân tuyệt đối."""
    db = db_()
    q = HT.chon(db, "quyet_toan", {"da_ket_thuc": True, "co_gia_von": True})
    for so in (1, 999, 1_000_001, 7_777_777, 1_126_475_000, 2_654_940_111):
        bt = HT.dung_but_toan(q, so, {"ma": "T", "khach": "K"})
        no = sum(l.get("debit", 0) for l in bt["lines"])
        co = sum(l.get("credit", 0) for l in bt["lines"])
        assert no == co == so, f"lệch ở {so}: Nợ {no} ≠ Có {co}"
    db.close()


def test_so_tien_khong_duong_thi_tu_choi():
    db = db_()
    q = HT.chon(db, "tien_vao", {"khop_don": True})
    for so in (0, -1, -1_000_000):
        with pytest.raises(ValueError):
            HT.dung_but_toan(q, so, {})
    db.close()


def test_khong_tach_khach_cong_ty_va_khach_le():
    """Quyết định 08/9/2026: công ty là bên chính cho MỌI khách. Không được có quy tắc nào đưa
    khách cá nhân sang 338 thu hộ – đó là quy ước cũ đã bị bãi."""
    db = db_()
    for q in db.execute(select(QuyTacHachToan).where(QuyTacHachToan.status == "active")).scalars():
        dk = q.dieu_kien or {}
        assert "loai_khach" not in dk, f"{q.ma} còn phân loại theo loại khách"
        if q.nguon == "quyet_toan" and q.tk_co.startswith("338"):
            raise AssertionError(f"{q.ma} ghi doanh thu vào 338 – trái quyết định bên chính")
    db.close()


def test_tam_ung_di_vao_141_khong_phai_138():
    """Sửa quy ước cũ: tiền giao cho người của công ty là tạm ứng, không phải phải thu khác."""
    db = db_()
    q = HT.chon(db, "tien_ra", {"muc_chi": "tam_ung"})
    assert q.tk_no == "141" and q.tk_co == "1121"
    assert HT.chon(db, "quyet_toan", {"co_tam_ung": True}).tk_co == "141"
    db.close()


# ============================ CỔNG CHẶN GIÁ VỐN ============================
def _tour(db, code, dt, gv, ten="Dịch vụ thử nghiệm trọn gói"):
    t = db.execute(select(Tour).where(Tour.code == code)).scalars().first()
    if t is None:
        op = db.execute(select(User).where(User.username == "ht_tp_dh")).scalars().first()
        t = Tour(code=code, name=ten, tour_type="non_package", start_date=date.today() - timedelta(days=20),
                 end_date=date.today() - timedelta(days=18), operator_id=op.id, status="ket_thuc")
        db.add(t)
    t.name, t.actual_revenue, t.actual_cost, t.status = ten, dt, gv, "ket_thuc"
    db.commit()
    return t


def test_chan_don_thieu_gia_von():
    db = db_()
    t = _tour(db, "HT-THIEU-01", 93_390_000, 0)
    assert CC.kiem_tra(t) == "thieu_gia_von"
    with pytest.raises(ValueError):
        CC.chan(t)
    db.close()


def test_don_du_ca_hai_thi_qua_cong():
    db = db_()
    t = _tour(db, "HT-DU-01", 100_000_000, 83_000_000)
    assert CC.kiem_tra(t) == ""
    CC.chan(t)          # không được ném
    db.close()


def test_bien_qua_cao_cung_bi_giu():
    """Biên 70% ở một đơn lữ hành gần như chắc chắn là thiếu dòng chi phí chứ không phải lãi thật."""
    db = db_()
    t = _tour(db, "HT-BIEN-01", 100_000_000, 30_000_000)
    assert CC.kiem_tra(t) == "lai_bat_thuong"
    db.close()


def test_gia_von_am_bi_giu():
    db = db_()
    t = _tour(db, "HT-AM-01", 100_000_000, -5_000_000)
    assert CC.kiem_tra(t) == "gia_von_am"
    db.close()


def test_chua_co_doanh_thu_thi_chua_den_luot_cong_nay():
    db = db_()
    t = _tour(db, "HT-CHUA-01", 0, 0)
    assert CC.kiem_tra(t) == ""
    db.close()


def test_quet_dua_vao_hang_doi_va_chay_lai_khong_nhan_doi():
    db = db_()
    _tour(db, "HT-THIEU-02", 9_688_677, 0)
    CC.quet(db); CC.quet(db)
    rows = db.execute(select(ThieuGiaVon).where(ThieuGiaVon.ma_don == "HT-THIEU-02")).scalars().all()
    assert len(rows) == 1 and rows[0].trang_thai == "cho"
    assert rows[0].nguoi_phu_trach, "phải đứng tên một người cụ thể, không để trống"
    db.close()


def test_bo_sung_gia_von_thi_dong_lai_chu_khong_xoa():
    db = db_()
    _tour(db, "HT-THIEU-03", 50_000_000, 0)
    CC.quet(db)
    _tour(db, "HT-THIEU-03", 50_000_000, 42_000_000)
    CC.quet(db)
    r = db.execute(select(ThieuGiaVon).where(ThieuGiaVon.ma_don == "HT-THIEU-03")).scalars().first()
    assert r is not None and r.trang_thai == "da_bo_sung", "giữ dấu vết là đơn này TỪNG thiếu"
    db.close()


def test_bo_qua_phai_co_giai_trinh():
    db = db_()
    _tour(db, "HT-THIEU-04", 6_233_434, 0)
    CC.quet(db)
    u = db.execute(select(User).where(User.username == "ht_ketoan")).scalars().first()
    with pytest.raises(ValueError):
        CC.bo_qua(db, u, "HT-THIEU-04", "ok")
    r = CC.bo_qua(db, u, "HT-THIEU-04", "Đây là ba dòng vé máy bay công tác của lãnh đạo, đã hạch toán 642")
    assert r.trang_thai == "bo_qua"
    from app.models.core import AuditLog
    assert db.execute(select(AuditLog).where(AuditLog.action == "bo_qua_cong_gia_von")).scalars().first() is not None
    db.close()


def test_hang_doi_hien_len_man_hinh_ngoai_le():
    """Không dựng hàng đợi thứ hai cho phòng ban: việc phải xuất hiện ở đúng cái cửa họ đã quen."""
    db = db_()
    _tour(db, "HT-THIEU-05", 77_000_000, 0)
    CC.quet(db)
    from app.services import ngoai_le as NL
    ma = {i["ma"] for i in NL.do_tim(db)}
    assert "thieu_gia_von#HT-THIEU-05" in ma
    db.close()


# ============================ API ============================
def test_api_ghi_so_tu_choi_don_thieu_gia_von():
    db = db_()
    t = _tour(db, "HT-THIEU-06", 120_000_000, 0)
    tid = t.id
    db.close()
    r = client.post("/api/v1/hach-toan/ghi-so", headers=login("ketoan"), json={
        "nguon": "quyet_toan", "so_tien": 120_000_000, "ngay": str(date.today()), "tour_id": tid,
        "boi_canh": {"da_ket_thuc": True, "co_gia_von": True, "ma": "HT-THIEU-06", "khach": "Khách thử"}})
    assert r.status_code == 422, r.text
    assert "giá vốn" in r.text


def test_api_xem_truoc_khong_ghi_gi_vao_so():
    from app.models.accounting import JournalEntry
    db = db_(); truoc = len(db.execute(select(JournalEntry)).scalars().all()); db.close()
    r = client.post("/api/v1/hach-toan/xem-truoc", headers=login("ketoan"), json={
        "nguon": "tien_vao", "so_tien": 50_000_000, "boi_canh": {"khop_don": True, "ma": "PT-DL-0912", "khach": "Khách A"}})
    assert r.status_code == 200 and r.json()["quy_tac"] == "THU_KHACH"
    db = db_(); assert len(db.execute(select(JournalEntry)).scalars().all()) == truoc; db.close()


def test_bks_doc_duoc_nhung_khong_ghi_duoc():
    h = login("bks")
    assert client.get("/api/v1/hach-toan", headers=h).status_code == 200
    assert client.get("/api/v1/hach-toan/thieu-gia-von", headers=h).status_code == 200
    r = client.post("/api/v1/hach-toan/ghi-so", headers=h, json={
        "nguon": "tien_vao", "so_tien": 1_000_000, "ngay": str(date.today()), "boi_canh": {"khop_don": True}})
    assert r.status_code == 403, r.text
    r = client.post("/api/v1/hach-toan/thieu-gia-von/bo-qua", headers=h,
                    json={"ma_don": "HT-THIEU-02", "giai_trinh": "x" * 30})
    assert r.status_code == 403, r.text


def test_bks_quet_duoc_vi_quet_khong_sua_so_cua_ai():
    r = client.post("/api/v1/hach-toan/thieu-gia-von/quet", headers=login("bks"))
    assert r.status_code == 200, r.text


def test_tp_dh_thay_viec_cua_phong_minh_nhung_khong_bo_qua_duoc():
    h = login("tp_dh")
    assert client.get("/api/v1/hach-toan/thieu-gia-von", headers=h).status_code == 200
    r = client.post("/api/v1/hach-toan/thieu-gia-von/bo-qua", headers=h,
                    json={"ma_don": "HT-THIEU-02", "giai_trinh": "x" * 30})
    assert r.status_code == 403


def test_quy_tac_moi_phai_du_hai_chu_ky_moi_chay():
    ngay = str(date.today())
    r = client.post("/api/v1/hach-toan/quy-tac", headers=login("ketoan"), json={
        "ma": "THU_LAI_NH", "ten": "Lãi tiền gửi ngân hàng", "nguon": "tien_vao",
        "dieu_kien": {"chua": ["lai tien gui"]}, "tk_no": "1121", "tk_co": "515",
        "doi_tuong": "ngan_hang", "dien_giai": "Lãi tiền gửi {ngan_hang}", "uu_tien": 15,
        "effective_from": ngay})
    assert r.status_code == 200, r.text
    qid = r.json()["id"]
    db = db_()
    assert HT.chon(db, "tien_vao", {"khop_don": False, "noi_dung": "lai tien gui thang 8"}).ma == "THU_CHUA_RO", \
        "quy tắc chưa ký mà đã chạy"
    db.close()
    assert client.post(f"/api/v1/hach-toan/quy-tac/{qid}/ky", headers=login("chutich")).status_code == 200
    db = db_()
    assert HT.chon(db, "tien_vao", {"khop_don": False, "noi_dung": "lai tien gui thang 8"}).ma == "THU_CHUA_RO", \
        "một chữ ký đã đủ hiệu lực – sai"
    db.close()
    assert client.post(f"/api/v1/hach-toan/quy-tac/{qid}/ky", headers=login("tgd")).status_code == 200
    db = db_()
    assert HT.chon(db, "tien_vao", {"khop_don": False, "noi_dung": "lai tien gui thang 8"}).ma == "THU_LAI_NH"
    db.close()


def test_quy_tac_tro_vao_tai_khoan_khong_co_thi_tu_choi_ngay_luc_trinh():
    r = client.post("/api/v1/hach-toan/quy-tac", headers=login("ketoan"), json={
        "ma": "BAY", "ten": "Tài khoản không tồn tại", "nguon": "tien_vao",
        "tk_no": "9999", "tk_co": "131", "effective_from": str(date.today())})
    assert r.status_code == 422 and "9999" in r.text
