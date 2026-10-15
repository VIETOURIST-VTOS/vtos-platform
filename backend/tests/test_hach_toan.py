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
    # Đợt R2 15/10/2026: bộ quy ước nay có HAI phần — `MAC_DINH` (Quyết định 08/9/2026) và
    # `MAC_DINH_TIEN_MAT` (sáu đường tiền mặt). Đếm cả hai chứ không đếm một: đếm một thì ngày ai
    # đó thêm một danh sách thứ ba, phép thử này vẫn xanh trong lúc bảng nạp thiếu.
    du = len(HT.MAC_DINH) + len(HT.MAC_DINH_TIEN_MAT)
    assert n1 == du, f"khởi động phải nạp đủ {du} quy tắc, đang có {n1}"
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
        # Đợt R2 15/10/2026 — khóa thêm HÌNH THỨC THANH TOÁN, và đây là một phép SIẾT chứ không
        # phải một chỗ nới. Lý do phép thử này tồn tại: hai quy tắc cùng nguồn cùng ưu tiên thì
        # thứ tự xét rơi xuống so mã, tức là may rủi. Từ đợt R2, `dang_hieu_luc` xếp theo
        # (có khai hình thức, ưu tiên, mã) — nên `THU_KHACH` (để trống) và `THU_KHACH_TM`
        # ("tien_mat") cùng ưu tiên 10 KHÔNG còn là may rủi: dòng khai đích danh luôn được xét
        # trước, theo một luật đọc được. Còn hai dòng CÙNG hình thức mà cùng ưu tiên thì vẫn đúng
        # là may rủi, và vẫn phải đỏ.
        thay.setdefault((q.nguon, q.hinh_thuc_tt, q.uu_tien), []).append(q.ma)
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
    # Đợt R2 15/10/2026: MUA_CO_HD nay bắt buộc mã khoản mục chi phí (đây là một trong bốn đường
    # tiền trở thành giá vốn của một chuyến). Thêm mã vào bối cảnh; chủ đề phép thử — tách thuế
    # đầu vào bên Nợ — không đổi.
    bt = HT.dung_but_toan(q, 54_000_000, {"ma": "KLE010826", "ncc": "Resort Vĩnh Hy",
                                          "khoan_muc": "KM_KS"})
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

# ============================ TÀI CHÍNH: VAY, NGÂN HÀNG, TRẢ NCC ============================
def test_co_quy_uoc_tra_tien_nha_cung_cap():
    """Thiếu quy ước này thì tiền ra khỏi tài khoản mà công nợ nhà cung cấp không bao giờ giảm –
    chạy một tháng là bảng công nợ sai toàn bộ. Đây là chỗ thiếu Chủ tịch chỉ ra ngày 08/9."""
    db = db_()
    q = HT.chon(db, "tien_ra", {"muc_chi": "tra_ncc"})
    assert q is not None and q.ma == "TRA_NCC"
    assert q.tk_no == "331" and q.tk_co == "1121"
    assert HT.chon(db, "tien_ra", {"muc_chi": "ung_ncc"}).ma == "TRA_NCC", "ứng trước cũng ghi 331"
    db.close()


def test_bo_quy_uoc_vay_du_ba_chan():
    """Nhận giải ngân, trả gốc, trả lãi – thiếu một chân là dư nợ vay trên sổ sai."""
    db = db_()
    assert HT.chon(db, "tien_vao", {"muc_thu": "giai_ngan_vay"}).tk_co == "3411"
    assert HT.chon(db, "tien_ra", {"muc_chi": "tra_goc_vay"}).tk_no == "3411"
    assert HT.chon(db, "tien_ra", {"muc_chi": "lai_vay"}).tk_no == "635"
    db.close()


def test_lai_vay_ghi_khi_tra_khong_trich_truoc():
    """Quyết định Chủ tịch 08/9: lãi vay ghi khi trả. Quy ước trích trước phải KHÔNG tồn tại –
    để nửa vời (có quy ước nhưng không ai bật) là chỗ sau này có người bật nhầm."""
    db = db_()
    assert HT.chon(db, "ket_chuyen", {"phan": "lai_vay_du_thu"}) is None
    assert not [q for q in db.execute(select(QuyTacHachToan)).scalars() if q.ma == "VAY_LAI_TRICH"]
    db.close()


def test_phi_vay_vao_635_phi_dich_vu_vao_6428():
    """TT99 nêu đích danh 'chi phí liên quan trực tiếp đến khoản vay… thẩm định hồ sơ vay vốn, chi phí
    thu xếp khoản vay' trong nội dung TK 635. Phí chuyển tiền thường thì không – nó là chi phí quản lý."""
    db = db_()
    assert HT.chon(db, "tien_ra", {"muc_chi": "phi_vay"}).tk_no == "635"
    assert HT.chon(db, "tien_ra", {"muc_chi": "phi_ngan_hang"}).tk_no == "6428"
    db.close()


def test_goc_va_lai_vay_khong_dung_chung_tai_khoan():
    """Ghi lãi vào 341 thì dư nợ gốc phình lên; ghi gốc vào 635 thì lỗ giả."""
    db = db_()
    goc = HT.chon(db, "tien_ra", {"muc_chi": "tra_goc_vay"})
    lai = HT.chon(db, "tien_ra", {"muc_chi": "lai_vay"})
    assert goc.tk_no != lai.tk_no
    db.close()


def test_ky_quy_va_lai_tien_gui_va_nop_thue():
    db = db_()
    assert HT.chon(db, "tien_ra", {"muc_chi": "ky_quy"}).tk_no == "244"
    assert HT.chon(db, "tien_vao", {"muc_thu": "hoan_ky_quy"}).tk_co == "244"
    assert HT.chon(db, "tien_vao", {"muc_thu": "lai_tien_gui"}).tk_co == "515"
    for muc, tk in (("nop_thue_gtgt", "3331"), ("nop_thue_tndn", "3334"),
                    ("nop_thue_tncn", "3335"), ("nop_bhxh", "3383")):
        assert HT.chon(db, "tien_ra", {"muc_chi": muc}).tk_no == tk, muc
    db.close()


def test_dao_han_ghi_mot_chan_thi_mo_ngoai_le():
    """Đáo hạn là HAI bút toán. Bù trừ thành một dòng thì dư nợ vay không bao giờ đứng ở đỉnh và
    dòng tiền mất hẳn một vòng ra–vào – cả hai đều là con số công bố của công ty đại chúng."""
    from app.services import accounting as ACC
    from app.services import cong_chan as CC
    db = db_()
    u = db.execute(select(User).where(User.username == "ht_ketoan")).scalars().first()
    # chỉ ghi chân trả gốc
    # Hai chân đáo hạn khai HAI nghiệp vụ khác nhau (Đợt DỌN-1, 13/10/2026). Cùng một mã nguồn
    # mà cùng một tên nghiệp vụ thì khoá chống ghi sổ hai lần của Đợt E3 coi chân sau là bản sao
    # của chân trước — đúng, vì nó không có cách nào biết đấy là hai việc.
    ACC.post_entry(db, u.username, u.role, date.today(), "Trả gốc đáo hạn",
                   [{"account": "3411", "debit": 5_000_000_000, "partner": "TPBank", "partner_code": "TPB"},
                    {"account": "1121", "credit": 5_000_000_000}],
                   source_type="quy_tac", source_ref="dao_han:DH0826", nghiep_vu="tra_goc_vay")
    db.commit()
    ra = {x["ma"] for x in CC.dao_han_thieu_chan(db)}
    assert "dao_han_thieu_chan#DH0826" in ra
    # ghi nốt chân nhận giải ngân
    ACC.post_entry(db, u.username, u.role, date.today(), "Nhận giải ngân khoản mới",
                   [{"account": "1121", "debit": 5_000_000_000},
                    {"account": "3411", "credit": 5_000_000_000, "partner": "TPBank", "partner_code": "TPB"}],
                   source_type="quy_tac", source_ref="dao_han:DH0826", nghiep_vu="nhan_giai_ngan_vay")
    db.commit()
    assert "dao_han_thieu_chan#DH0826" not in {x["ma"] for x in CC.dao_han_thieu_chan(db)}
    db.close()


def test_moi_quy_uoc_tai_chinh_deu_co_doi_tuong_khi_can():
    """131, 331, 341, 244 là tài khoản công nợ – ghi mà không có đối tượng thì không đối chiếu được."""
    db = db_()
    CAN = ("131", "331", "341", "3411", "244")
    for q in db.execute(select(QuyTacHachToan).where(QuyTacHachToan.status == "active")).scalars():
        if q.tk_no.startswith(CAN) or q.tk_co.startswith(CAN):
            assert q.doi_tuong, f"{q.ma} đụng tài khoản công nợ mà không khai cách lấy đối tượng"
    db.close()


def test_dieu_kien_danh_sach_phai_khop_theo_phan_tu():
    """Lỗi thật ngày 08/9: mọi khóa điều kiện dạng danh sách trừ hai khóa được liệt kê sẵn đều rơi
    xuống phép so đúng/sai, nên 'muc_thu: hoan_ky_quy' khớp nhầm vào quy tắc giải ngân vay. Sai kiểu
    này không báo lỗi – nó chỉ lặng lẽ chọn nhầm tài khoản."""
    db = db_()
    assert HT._khop({"muc_thu": ["giai_ngan_vay"]}, {"muc_thu": "hoan_ky_quy"}) is False
    assert HT._khop({"muc_thu": ["giai_ngan_vay"]}, {"muc_thu": "giai_ngan_vay"}) is True
    assert HT._khop({"khoa_moi_chua_tung_co": ["x"]}, {"khoa_moi_chua_tung_co": "y"}) is False
    # điều kiện là một CHUỖI thì so bằng nhau, không so khác-rỗng
    assert HT._khop({"phan": "khau_hao"}, {"phan": "lai_vay_du_thu"}) is False
    assert HT._khop({"phan": "khau_hao"}, {"phan": "khau_hao"}) is True
    # điều kiện ĐÚNG/SAI vẫn so theo đúng/sai
    assert HT._khop({"khop_don": True}, {"khop_don": True}) is True
    assert HT._khop({"khop_don": False}, {"khop_don": True}) is False
    db.close()


def test_moi_gia_tri_mac_dinh_vua_do_dai_cot():
    """Mọi giá trị trong bộ quy ước mặc định phải vừa độ dài cột đã khai.

    Vì sao cần phép thử này, và vì sao nó đọc độ dài từ chính mô hình chứ không chép số vào đây:
    SQLite KHÔNG ép độ dài VARCHAR, PostgreSQL thì CÓ. Một chuỗi quá dài vì thế đi qua sạch sẽ toàn
    bộ phép thử ở máy rồi làm hỏng lệnh INSERT lúc khởi động trên máy chủ thật. Mà nap_mac_dinh chạy
    trong lifespan, nên hỏng ở đó là cả API không lên được – Render dừng ở "Exited with status 3" và
    giữ nguyên bản cũ.

    Đã xảy ra thật ngày 08/9/2026: can_cu của PHI_VAY dài 363 ký tự trên cột String(200). 37 phép
    thử đều xanh, deploy vẫn hỏng.
    """
    from sqlalchemy import String
    cot = {c.name: c.type.length for c in QuyTacHachToan.__table__.columns
           if isinstance(c.type, String) and c.type.length}
    ten_truong = ("ma", "ten", "nguon", "dieu_kien", "tk_no", "tk_co", "tk_thue", "ben_thue",
                  "ty_le_thue", "doi_tuong", "can_cong_trinh", "dien_giai", "uu_tien", "can_cu")
    qua_dai = []
    for hang in HT.MAC_DINH:
        d = dict(zip(ten_truong, hang))
        for ten, gioi_han in cot.items():
            v = d.get(ten)
            if isinstance(v, str) and len(v) > gioi_han:
                qua_dai.append(f"{d['ma']}.{ten}: {len(v)} ký tự > {gioi_han}")
    assert not qua_dai, ("Giá trị dài quá cột – ở máy thì SQLite bỏ qua, lên PostgreSQL thì INSERT "
                         f"hỏng và API không khởi động được: {qua_dai}")
