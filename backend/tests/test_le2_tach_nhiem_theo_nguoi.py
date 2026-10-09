"""Đợt E2a — tách bạch trách nhiệm theo NGƯỜI, không theo vai.

  A. Hai bảng bắt đầu RỖNG. Không có cặp nào thì không chặn ai — và không im lặng chặn.
  B. Chưa ai đặt mức thì chạy mức nhẹ nhất NHƯNG bị đếm lên (`cap_chua_dat_muc`).
  C. ĐỊNH DANH NGƯỜI. Hai tài khoản cùng mã nhân viên là MỘT người; hai tài khoản cùng RỖNG mã
     là HAI người (K2: rỗng khác bằng nhau). Đây là chỗ dễ sai nhất của cả đợt.
  D. Bắt đúng chuyện đã đo được 19/9/2026: một người hai tài khoản đi hết cả hai bước.
  E. Vai KHÁC nhau mà cùng một NGƯỜI vẫn bị bắt — đây là thứ lớp cũ không làm được.
     Hai NGƯỜI khác nhau thì không bị bắt, kể cả cùng vai.
  F. Dấu chân GHI THÊM, không ghi đè: làm lại một bước để lại dòng thứ hai.
  G. THẮT thì Kế toán làm được, NỚI phải có chữ ký.
  H. Hai bảng mới phải có cửa nhập (ks_cua_nhap), và phải khai phạm vi pháp nhân.
"""
import os
import sys
from datetime import datetime, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_le2.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_le2.db", "test_le2.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.muc_do_chan import MUC_DO, MUC_DO_KHI_CHUA_KHAI
from app.models.tach_nhiem import BuocDaLam, CapTachNhiem, ma_nguoi
from app.services import ks_tach_nhiem as KTN

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


class Gia:
    """Một tài khoản giả — đủ các trường mà bộ kiểm đọc, không hơn."""
    def __init__(self, id, staff_code="", username="", role="ketoan", full_name=""):
        self.id, self.staff_code, self.username = id, staff_code, username
        self.role, self.full_name = role, full_name or username


def _db():
    return SessionLocal()


def _dọn(db):
    db.query(BuocDaLam).delete()
    db.query(CapTachNhiem).delete()
    db.commit()


def _cap(db, ma, a, b, muc=None, ngay=None, ap_dung=True):
    c = CapTachNhiem(ma_cap=ma, buoc_a=a, buoc_b=b, ten=ma, muc_do=muc,
                     ngay_hieu_luc=ngay, dang_ap_dung=ap_dung)
    db.add(c)
    db.commit()
    return c


# ─────────────────────────── A. Bắt đầu rỗng ───────────────────────────
def test_a1_hai_bang_bat_dau_rong():
    db = _db()
    try:
        assert db.query(CapTachNhiem).count() == 0, (
            "Bảng cặp xung đột phải RỖNG khi dựng. Migration KHÔNG nạp hộ: hai cặp Chủ tịch ký "
            "09/10/2026 đi vào qua một CỬA có người bấm, không qua một lần nâng cấp lặng lẽ.")
        assert db.query(BuocDaLam).count() == 0
    finally:
        db.close()


def test_a2_nap_cap_da_ky_dung_hai_dong_va_chay_lai_duoc():
    from app.models.tach_nhiem import CAP_DA_KY
    db = _db()
    try:
        _dọn(db)
        them = KTN.nap_cap_da_ky(db)
        assert sorted(them) == sorted(d["ma_cap"] for d in CAP_DA_KY)
        assert db.query(CapTachNhiem).count() == len(CAP_DA_KY) == 2
        assert KTN.nap_cap_da_ky(db) == [], "Nạp lần hai không được dựng thêm dòng nào."
        assert db.query(CapTachNhiem).count() == 2
    finally:
        db.close()


def test_a3_khong_dong_nao_duoc_thieu_chu_ky():
    """Bất biến thật của bảng này: không phải 'rỗng mãi', mà là 'không dòng nào vô chủ'."""
    db = _db()
    try:
        _dọn(db)
        KTN.nap_cap_da_ky(db)
        for c in db.query(CapTachNhiem).all():
            assert (c.nguoi_ky or "").strip(), f"Cặp {c.ma_cap} không có người ký."
            assert (c.can_cu or "").strip(), f"Cặp {c.ma_cap} không có căn cứ."
    finally:
        db.close()


def test_a4_hai_cap_da_ky_de_TRONG_muc_do():
    """Chủ tịch ký SỰ TỒN TẠI của cặp, chưa ký MỨC. Tự đặt 'chặn' hộ là đúng lỗi đã phải sửa."""
    db = _db()
    try:
        _dọn(db)
        KTN.nap_cap_da_ky(db)
        for c in db.query(CapTachNhiem).all():
            assert c.muc_do is None, (
                f"Cặp {c.ma_cap} bị đặt sẵn mức `{c.muc_do}` — không ai ký mức ấy.")
            assert KTN.muc_do(c) == MUC_DO_KHI_CHUA_KHAI
        assert len(KTN.cap_chua_dat_muc(db)) == 2, "Chưa đặt mức thì phải bị đếm lên."
    finally:
        db.close()


def test_a5_hai_cap_da_ky_tro_dung_ma_buoc_co_that():
    from app.models.tach_nhiem import BUOC, CAP_DA_KY
    for d in CAP_DA_KY:
        for k in ("buoc_a", "buoc_b"):
            assert d[k] in BUOC, (
                f"Cặp {d['ma_cap']} trỏ tới bước `{d[k]}` không có trong BUOC — một cặp trỏ "
                f"vào bước không tồn tại là một cặp không bao giờ khớp, tức là một hàng rào tắt.")


def test_a6_khong_co_cap_thi_khong_chan_ai():
    db = _db()
    try:
        _dọn(db)
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:7", "ky_lenh_chi", u)
        db.commit()
        kq = KTN.kiem(db, "dc:7", "da_chi", u)
        assert kq["chan"] is False and kq["vi_pham"] == []
    finally:
        db.close()


# ─────────────────── B. Chưa đặt mức: nhẹ nhất, nhưng bị đếm ───────────────────
def test_b1_chua_dat_muc_thi_canh_bao_cho_qua():
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc=None)
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:1", "ky_lenh_chi", u)
        db.commit()
        kq = KTN.kiem(db, "dc:1", "da_chi", u)
        assert kq["muc_do"] == MUC_DO_KHI_CHUA_KHAI == "canh_bao_cho_qua"
        assert kq["chan"] is False, "Chưa ai đặt mức thì KHÔNG tự chặn — đó là tự đặt quy chế hộ."
        assert len(kq["vi_pham"]) == 1, "Cho qua thì được, im lặng thì không."
    finally:
        db.close()


def test_b2_cap_chua_dat_muc_bi_dem_len():
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc=None)
        _cap(db, "ghi-vs-khoa", "ghi_so", "khoa_so", muc="canh_bao_va_chan")
        assert KTN.cap_chua_dat_muc(db) == ["lap-vs-chi"]
    finally:
        db.close()


def test_b3_muc_viet_sai_chinh_ta_cung_la_chua_dat():
    db = _db()
    try:
        _dọn(db)
        c = _cap(db, "x", "a", "b", muc="chan_cung")      # không có trong MUC_DO
        assert "chan_cung" not in MUC_DO
        assert KTN.muc_do(c) == MUC_DO_KHI_CHUA_KHAI
        assert KTN.cap_chua_dat_muc(db) == ["x"]
    finally:
        db.close()


def test_b4_chua_toi_ngay_hieu_luc_thi_chua_ap():
    db = _db()
    try:
        _dọn(db)
        mai = datetime.utcnow() + timedelta(days=1)
        c = _cap(db, "y", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan", ngay=mai)
        assert KTN.muc_do(c) == MUC_DO_KHI_CHUA_KHAI
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:2", "ky_lenh_chi", u)
        db.commit()
        assert KTN.kiem(db, "dc:2", "da_chi", u)["chan"] is False
    finally:
        db.close()


# ─────────────────────── C. Ai là một người ───────────────────────
def test_c1_cung_ma_nhan_vien_la_mot_nguoi():
    a = Gia(91, "269", "van.anh")
    b = Gia(251, "269", "vananh2")
    assert ma_nguoi(a) == ma_nguoi(b) == "269"


def test_c2_hai_tai_khoan_cung_RONG_ma_la_HAI_nguoi():
    """K2: RỖNG khác BẰNG NHAU.

    Gộp mọi tài khoản chưa khai mã nhân viên thành "một người" là chặn oan hàng loạt ngay ngày
    đầu — đúng kiểu hỏng mà nguyên tắc K2 sinh ra để ngăn.
    """
    a, b = Gia(251, "", "moi1"), Gia(252, "", "moi2")
    assert ma_nguoi(a) != ma_nguoi(b)
    assert ma_nguoi(a) == "u:251" and ma_nguoi(b) == "u:252"


def test_c3_ma_co_khoang_trang_van_la_cung_mot_nguoi():
    assert ma_nguoi(Gia(1, " 114 ")) == ma_nguoi(Gia(2, "114")) == "114"


# ───────────── D & E. Bắt đúng chuyện đã đo được, và chỉ bắt đúng nó ─────────────
def test_d1_mot_nguoi_hai_tai_khoan_di_ca_hai_buoc_thi_bi_bat():
    """Dựng lại đúng cặp đo được 19/9/2026: id 91 và id 251 cùng mã nhân viên."""
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan")
        tk1 = Gia(91, "269", "van.anh")
        tk2 = Gia(251, "269", "vananh2")
        KTN.ghi_buoc(db, "dc:10", "ky_lenh_chi", tk1)
        db.commit()
        kq = KTN.kiem(db, "dc:10", "da_chi", tk2)
        assert kq["chan"] is True, (
            "Hai TÀI KHOẢN khác nhau nhưng cùng MỘT NGƯỜI — đây chính là lối đi vòng đã đếm "
            "được trên máy thật ngày 19/9/2026.")
        assert kq["vi_pham"][0]["ma_cap"] == "lap-vs-chi"
    finally:
        db.close()


def test_e1_vai_khac_nhau_ma_cung_mot_nguoi_van_bi_bat():
    """Thứ lớp cũ KHÔNG làm được: nó chỉ so vai, mà hai vai này khác nhau."""
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan")
        kt = Gia(91, "269", "van.anh", role="ketoan_tt")
        tq = Gia(251, "269", "vananh2", role="thu_quy")
        assert kt.role != tq.role
        KTN.ghi_buoc(db, "dc:11", "ky_lenh_chi", kt)
        db.commit()
        assert KTN.kiem(db, "dc:11", "da_chi", tq)["chan"] is True
    finally:
        db.close()


def test_e2_hai_nguoi_khac_nhau_thi_khong_bi_bat_ke_ca_cung_vai():
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan")
        a = Gia(1, "114", "a.nguyen", role="ketoan")
        b = Gia(2, "115", "b.tran", role="ketoan")
        KTN.ghi_buoc(db, "dc:12", "ky_lenh_chi", a)
        db.commit()
        assert KTN.kiem(db, "dc:12", "da_chi", b)["chan"] is False
    finally:
        db.close()


def test_e3_chung_tu_khac_thi_khong_dinh_nhau():
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan")
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:20", "ky_lenh_chi", u)
        db.commit()
        assert KTN.kiem(db, "dc:21", "da_chi", u)["chan"] is False
    finally:
        db.close()


def test_e4_cap_doc_duoc_ca_hai_chieu():
    """Khai cặp (A,B) thì làm B trước rồi A cũng phải bắt — không chỉ một chiều."""
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan")
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:30", "da_chi", u)
        db.commit()
        assert KTN.kiem(db, "dc:30", "ky_lenh_chi", u)["chan"] is True
    finally:
        db.close()


def test_e5_tat_dang_ap_dung_thi_khong_con_chan():
    db = _db()
    try:
        _dọn(db)
        _cap(db, "lap-vs-chi", "ky_lenh_chi", "da_chi", muc="canh_bao_va_chan", ap_dung=False)
        u = Gia(1, "114", "a.nguyen")
        KTN.ghi_buoc(db, "dc:31", "ky_lenh_chi", u)
        db.commit()
        assert KTN.kiem(db, "dc:31", "da_chi", u)["chan"] is False
        assert KTN.cap_chua_dat_muc(db) == [], "Cặp đã tắt thì không đếm vào việc phải xử lý."
    finally:
        db.close()


# ─────────────────────── F. Dấu chân ghi thêm ───────────────────────
def test_f1_lam_lai_mot_buoc_de_lai_dong_thu_hai():
    db = _db()
    try:
        _dọn(db)
        a, b = Gia(1, "114", "a.nguyen"), Gia(2, "115", "b.tran")
        KTN.ghi_buoc(db, "dc:40", "ky_lenh_chi", a)
        KTN.ghi_buoc(db, "dc:40", "ky_lenh_chi", b)
        db.commit()
        dc = KTN.dau_chan(db, "dc:40")
        assert len(dc) == 2, (
            "Làm lại một bước phải để lại dòng thứ hai. Ghi đè thì mất đúng cái cần nhìn: "
            "bước này đã bị làm lại, và ai làm.")
        assert [x["username"] for x in dc] == ["a.nguyen", "b.tran"], "Cũ trước, mới sau."
    finally:
        db.close()


def test_f2_dau_chan_giu_ca_vai_luc_lam():
    db = _db()
    try:
        _dọn(db)
        KTN.ghi_buoc(db, "dc:41", "ky_lenh_chi", Gia(1, "114", "a.nguyen", role="ketoan_tt"))
        db.commit()
        d = KTN.dau_chan(db, "dc:41")[0]
        assert d["vai"] == "ketoan_tt" and d["ma_nguoi"] == "114" and d["luc"]
    finally:
        db.close()


# ─────────────────────── G. Thắt / nới ───────────────────────
def test_g1_that_va_noi_phan_biet_ro():
    assert "canh_bao_va_chan" in KTN.THAT
    assert "khong_canh_bao" in KTN.NOI
    assert set(KTN.THAT) & set(KTN.NOI) == set(), "Một mức không thể vừa thắt vừa nới."
    assert set(KTN.THAT) | set(KTN.NOI) | {MUC_DO_KHI_CHUA_KHAI} == set(MUC_DO), (
        "Mỗi mức phải nằm đúng một phía, hoặc là mức mặc định — không có mức nào không phân loại.")


def test_e6_cap_ghi_so_vs_khoa_so_dung_chung_PHAM_VI_la_KY():
    """Ca kiểm chứng minh vì sao dấu chân khóa theo PHẠM VI chứ không theo id bản ghi.

    "Ghi sổ" xảy ra trên một BÚT TOÁN, "khóa sổ" xảy ra trên một KỲ — hai bản ghi khác nhau.
    Khóa theo id bút toán thì cặp này KHÔNG BAO GIỜ khớp: một hàng rào trông như đang chạy mà
    thật ra tắt. Thứ chung của hai bước là cái kỳ, nên phạm vi là `ky:<kỳ>`.
    """
    db = _db()
    try:
        _dọn(db)
        KTN.nap_cap_da_ky(db)
        c = db.query(CapTachNhiem).filter_by(ma_cap="ghi-so-vs-khoa-so").one()
        c.muc_do = "canh_bao_va_chan"
        db.commit()
        u = Gia(1, "114", "ketoan1")
        KTN.ghi_buoc(db, "ky:2026-09", "ghi_so", u)          # ghi sổ bút toán A
        KTN.ghi_buoc(db, "ky:2026-09", "ghi_so", u)          # và bút toán B
        db.commit()
        assert KTN.kiem(db, "ky:2026-09", "khoa_so_ky", u)["chan"] is True
        assert KTN.kiem(db, "ky:2026-10", "khoa_so_ky", u)["chan"] is False, (
            "Kỳ khác thì không dính nhau.")
        assert KTN.kiem(db, "ky:2026-09", "khoa_so_ky", Gia(2, "115", "ketoan2"))["chan"] is False
    finally:
        db.close()


# ──────────────── I. Mã nhân viên — lỗ còn lại, và cách nó được xử ────────────────
def test_i1_vai_tien_khong_co_ma_nv_bi_danh_dau():
    db = _db()
    try:
        _dọn(db)
        assert KTN.thieu_ma_nhan_vien(Gia(1, "", "ketoan1", role="ketoan")) is True
        assert KTN.thieu_ma_nhan_vien(Gia(2, "114", "ketoan2", role="ketoan")) is False
        assert KTN.thieu_ma_nhan_vien(Gia(3, "", "hdv1", role="hdv")) is False, (
            "Luật này chỉ áp cho VAI TIỀN. HDV cộng tác viên chưa có mã là chuyện bình thường, "
            "khóa họ lại là khóa oan.")
        kq = KTN.kiem(db, "dc:1", "da_chi", Gia(1, "", "ketoan1"))
        assert kq["thieu_ma_nhan_vien"] is True and kq["thong_diep_thieu_ma"]
    finally:
        db.close()


def test_i2_chua_toi_ngay_hieu_luc_thi_dem_chu_khong_chan():
    """Đo được: bộ dữ liệu mẫu KHÔNG tài khoản nào có mã nhân viên.

    Bật thẳng hôm nay là khóa cả Chủ tịch ra ngoài đúng cửa ĐÃ CHI. Nên luật đi kèm một ngày
    hiệu lực do Chủ tịch đặt sau khi HCNS điền xong mã — cùng lối đã dùng cho `muc_do_chan`.
    """
    db = _db()
    try:
        _dọn(db)
        assert KTN.bat_buoc_ma_nv(db) is False, "Chưa đặt tham số thì chưa chặn ai."
        kq = KTN.kiem(db, "dc:2", "da_chi", Gia(1, "", "ketoan1"))
        assert kq["thieu_ma_nhan_vien"] is True
        assert kq["chan_vi_thieu_ma_nhan_vien"] is False
        assert kq["chan"] is False
    finally:
        db.close()


def test_i3_co_danh_sach_tai_khoan_thieu_ma_de_HCNS_di_dien():
    db = _db()
    try:
        ds = KTN.tai_khoan_thieu_ma_nv(db)
        assert isinstance(ds, list)
        for d in ds:
            assert d["username"] and d["vai"], "Một con số thì không ai biết phải đi tìm ai."
    finally:
        db.close()


# ─────────────────────── H. Cửa nhập và phạm vi ───────────────────────
def test_h1_hai_bang_moi_co_cua_nhap():
    from app.services import ks_cua_nhap as KCN
    for b in ("cap_tach_nhiem", "buoc_da_lam"):
        assert b in KCN.CUA_TAY or b in getattr(KCN, "MAY_SINH", {}), (
            f"Bảng `{b}` chưa khai cửa nhập. Mỗi con số hệ thống cần cần một cửa nhập hoặc một "
            f"cửa sinh tự động; không có cửa thì đó là việc còn thiếu.")


def test_h2_hai_bang_moi_khai_pham_vi_phap_nhan():
    from app.services import pham_vi_phap_nhan as PV
    for b in ("CapTachNhiem", "BuocDaLam"):
        assert b in PV.PHAI_LOC or b in PV.CO_Y_KHONG_LOC, (
            f"`{b}` chưa khai phạm vi pháp nhân.")


def test_h3_lich_su_to_chuc_da_khai_pham_vi():
    """Nợ cũ của Đợt C, Chủ tịch quyết 09/10/2026: toàn tập đoàn, cố ý không lọc."""
    from app.services import pham_vi_phap_nhan as PV
    assert "LichSuToChuc" in PV.CO_Y_KHONG_LOC, (
        "Lịch sử tổ chức là chuyện của cả tập đoàn — cắt theo pháp nhân thì không ai đọc được "
        "bức tranh đầy đủ. Chủ tịch quyết 09/10/2026, cùng lối nghĩ đã dùng cho IR–Pháp chế.")
