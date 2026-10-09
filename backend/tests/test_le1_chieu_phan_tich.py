"""Đợt E1 — chiều phân tích khai trên tài khoản, và bảng mức độ chặn.

  A. Bảng mức độ chặn bắt đầu RỖNG, và phép kiểm chưa ai đặt mức thì chạy ở mức nhẹ nhất NHƯNG
     bị đếm lên. Im lặng mới là hỏng.
  B. BỐN LUẬT CỨNG không đặt mức được. Cửa phải từ chối, không phải phép thử nhắc suông.
  C. Đặt mức mà không nói ai xử lý thì không phải một kiểm soát.
  D. Chiều phân tích đọc từ chính tài khoản — một nơi khai, mọi nơi đọc. Đây là chỗ gỡ xung đột
     TK3388 của bản rà soát 09/10.
  E. `tinh_chat` TRỐNG = chưa ai khai, KHÔNG phải "dư Nợ" (K2). Chưa khai thì không báo bất thường.
  F. THẮT thì Kế toán làm được, NỚI phải có chữ ký.
  G. Chỉ khai cờ nào `journal_lines` có cột để kiểm — cờ không có cột là cờ không kiểm được gì.
"""
import os
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_le1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_le1.db", "test_le1.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.accounting import Account, JournalLine, Partner
from app.models.muc_do_chan import LUAT_CUNG, MUC_DO, MUC_DO_KHI_CHUA_KHAI, MucDoChan
from app.services import ke_toan_chieu as KTC

client = TestClient(app)
TOK = {}
P = "/api/v1/hach-toan"


def login(u):
    if u not in TOK:
        r = client.post("/api/v1/auth/login", data={"username": u, "password": "Vtos@Demo#2026"})
        assert r.status_code == 200, r.text
        TOK[u] = r.json()["access_token"]
    return {"Authorization": f"Bearer {TOK[u]}"}


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app) as c:
        global client
        client = c
        yield


def _tk(code, **kw):
    """Dựng một tài khoản thử trong sổ, trả về mã."""
    db = SessionLocal()
    try:
        t = db.get(Account, code)
        if t is None:
            t = Account(code=code, name=f"TK thử {code}", kind="TS")
            db.add(t)
        for k, v in kw.items():
            setattr(t, k, v)
        db.commit()
    finally:
        db.close()
    return code


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. Bảng bắt đầu rỗng; chưa đặt mức thì nhẹ nhất nhưng bị đếm
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_a1_bang_bat_dau_rong():
    db = SessionLocal()
    try:
        assert db.query(MucDoChan).count() == 0, (
            "Bảng mức độ chặn phải bắt đầu rỗng. Máy nạp sẵn một dòng là máy tự đặt mức hộ người.")
    finally:
        db.close()


def test_a2_chua_dat_muc_thi_nhe_nhat_nhung_bi_dem():
    db = SessionLocal()
    try:
        assert KTC.muc_do(db, KTC.PK_THIEU_CHIEU) == MUC_DO_KHI_CHUA_KHAI
        assert KTC.muc_do(db, KTC.PK_THIEU_CHIEU) != "canh_bao_va_chan"
        chua = KTC.phep_kiem_chua_dat_muc(db)
        assert KTC.PK_THIEU_CHIEU in chua, (
            "Phép kiểm chạy ở mức mặc định PHẢI bị đếm lên. Cho qua mà có người đếm thì được; "
            "cho qua trong im lặng thì không.")
    finally:
        db.close()


def test_a3_dat_muc_roi_thi_doc_dung_va_het_bi_dem():
    r = client.post(f"{P}/muc-do-chan", headers=login("chutich"), json={
        "ma_phep_kiem": KTC.PK_THIEU_CHIEU, "ten": "Dòng bút toán thiếu chiều phân tích",
        "muc_do": "canh_bao_va_chan", "nguoi_xu_ly": "ketoan", "han_xu_ly_ngay": 2,
        "nguoi_thay_the": "cntt", "can_cu": "Quyết định Chủ tịch 09/10/2026"})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        assert KTC.muc_do(db, KTC.PK_THIEU_CHIEU) == "canh_bao_va_chan"
        assert KTC.chan(db, KTC.PK_THIEU_CHIEU) is True
        assert KTC.PK_THIEU_CHIEU not in KTC.phep_kiem_chua_dat_muc(db)
    finally:
        db.close()


def test_a4_chua_toi_ngay_hieu_luc_thi_van_la_muc_mac_dinh():
    mai = (date.today() + timedelta(days=30)).isoformat()
    r = client.post(f"{P}/muc-do-chan", headers=login("chutich"), json={
        "ma_phep_kiem": KTC.PK_TK_NGUNG_SU_DUNG, "ten": "Ghi vào TK đã ngừng",
        "muc_do": "canh_bao_va_chan", "nguoi_xu_ly": "ketoan", "ngay_hieu_luc": mai})
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        assert KTC.muc_do(db, KTC.PK_TK_NGUNG_SU_DUNG) == MUC_DO_KHI_CHUA_KHAI, (
            "Đã khai nhưng chưa tới ngày hiệu lực thì chưa được chặn.")
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B & C. Luật cứng, và cảnh báo phải có người
# ══════════════════════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("ma", LUAT_CUNG)
def test_b1_luat_cung_khong_dat_muc_duoc(ma):
    r = client.post(f"{P}/muc-do-chan", headers=login("chutich"),
                    json={"ma_phep_kiem": ma, "ten": ma, "muc_do": "khong_canh_bao",
                          "nguoi_xu_ly": "ketoan"})
    assert r.status_code == 422, (
        f"'{ma}' là luật cứng — cửa phải từ chối, không để ai hạ nó xuống 'không cảnh báo'.")
    assert "LUẬT CỨNG" in r.json()["detail"]


def test_b2_khong_dong_luat_cung_nao_lot_vao_bang():
    db = SessionLocal()
    try:
        co = {r.ma_phep_kiem for r in db.query(MucDoChan).all()} & set(LUAT_CUNG)
        assert not co, f"Luật cứng lọt vào bảng mức độ chặn: {sorted(co)}"
    finally:
        db.close()


def test_c1_dat_muc_ma_khong_co_nguoi_xu_ly_thi_bi_tu_choi():
    r = client.post(f"{P}/muc-do-chan", headers=login("chutich"),
                    json={"ma_phep_kiem": "thu_mot_phep_kiem", "ten": "Thử",
                          "muc_do": "canh_bao_cho_qua"})
    assert r.status_code == 422
    assert "AI xử lý" in r.json()["detail"]


def test_c2_muc_khong_hop_le_bi_tu_choi():
    r = client.post(f"{P}/muc-do-chan", headers=login("chutich"),
                    json={"ma_phep_kiem": "thu_muc_sai", "ten": "Thử", "muc_do": "chan_het",
                          "nguoi_xu_ly": "ketoan"})
    assert r.status_code == 422


def test_c3_ke_toan_khong_tu_dat_muc_duoc():
    r = client.post(f"{P}/muc-do-chan", headers=login("ketoan"),
                    json={"ma_phep_kiem": "thu_ke_toan", "ten": "Thử",
                          "muc_do": "khong_canh_bao", "nguoi_xu_ly": "ketoan"})
    assert r.status_code == 403, "Hạ một mức chặn là nới một hàng rào — phải có chữ ký."


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. Chiều phân tích đọc từ chính tài khoản
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_d1_tai_khoan_khong_khai_thi_khong_thieu_gi():
    code = _tk("9901")
    db = SessionLocal()
    try:
        dong = JournalLine(account_code=code, partner_code="", project_code="", item_code="")
        assert KTC.thieu_chieu(db, dong) == []
    finally:
        db.close()


def test_d2_khai_cong_trinh_thi_thieu_ma_tour_la_thieu_chieu():
    code = _tk("9902", td_cong_trinh=True)
    db = SessionLocal()
    try:
        thieu = KTC.thieu_chieu(db, JournalLine(account_code=code, project_code=""))
        assert thieu and "công trình" in thieu[0]
        du = KTC.thieu_chieu(db, JournalLine(account_code=code, project_code="MICEUK10N9.10090926"))
        assert du == []
    finally:
        db.close()


def test_d3_khai_ba_chieu_thi_bao_du_ba():
    code = _tk("9903", td_doi_tuong=True, td_doi_tuong_loai="tat_ca",
               td_cong_trinh=True, td_khoan_muc=True)
    db = SessionLocal()
    try:
        thieu = KTC.thieu_chieu(db, JournalLine(account_code=code))
        assert len(thieu) == 3, f"Phải báo đủ ba chiều còn thiếu, nhận: {thieu}"
    finally:
        db.close()


def test_d4_khai_loai_doi_tuong_thi_sai_loai_bi_bat():
    code = _tk("9904", td_doi_tuong=True, td_doi_tuong_loai="ncc")
    db = SessionLocal()
    try:
        p = db.query(Partner).filter(Partner.code == "KH-THU-E1").first()
        if p is None:
            db.add(Partner(code="KH-THU-E1", name="Khách thử E1", kind="kh",
                           is_customer=True, is_supplier=False))
            db.commit()
        thieu = KTC.thieu_chieu(db, JournalLine(account_code=code, partner_code="KH-THU-E1"))
        assert any("không phải ncc" in t for t in thieu), (
            f"Tài khoản khai theo dõi NCC mà gán mã khách hàng thì phải bị bắt. Nhận: {thieu}")
    finally:
        db.close()


def test_d5_kiem_chung_tu_chan_theo_dung_muc_da_dat():
    code = _tk("9905", td_cong_trinh=True)
    db = SessionLocal()
    try:
        kq = KTC.kiem_chung_tu(db, [JournalLine(account_code=code, project_code="")])
        # test_a3 đã đặt PK_THIEU_CHIEU = canh_bao_va_chan
        assert kq["muc_do"] == "canh_bao_va_chan"
        assert kq["chan"] is True
        assert kq["thieu"][0]["tai_khoan"] == code
        kq2 = KTC.kiem_chung_tu(db, [JournalLine(account_code=code, project_code="T-001")])
        assert kq2["chan"] is False and kq2["thieu"] == []
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. tinh_chat trống = chưa khai, không phải "dư Nợ" (K2)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_e1_chua_khai_tinh_chat_thi_khong_bao_bat_thuong():
    db = SessionLocal()
    try:
        t = db.get(Account, _tk("9906"))
        assert (t.tinh_chat or "") == ""
        assert KTC.so_du_bat_thuong(t, du_no=0, du_co=5_000_000) == "", (
            "Chưa ai khai tính chất mà đã báo bất thường là báo trên một giả định tự đặt ra.")
    finally:
        db.close()


def test_e2_khai_du_no_ma_dang_du_co_thi_bao():
    db = SessionLocal()
    try:
        t = db.get(Account, _tk("9907", tinh_chat="du_no"))
        assert "dư Có" in KTC.so_du_bat_thuong(t, du_no=0, du_co=1_000)
        assert KTC.so_du_bat_thuong(t, du_no=1_000, du_co=0) == ""
    finally:
        db.close()


def test_e3_luong_tinh_khong_bao_gio_bat_thuong():
    db = SessionLocal()
    try:
        t = db.get(Account, _tk("9908", tinh_chat="luong_tinh"))
        assert KTC.so_du_bat_thuong(t, du_no=9, du_co=0) == ""
        assert KTC.so_du_bat_thuong(t, du_no=0, du_co=9) == ""
    finally:
        db.close()


def test_e4_273_tai_khoan_that_van_de_trong_tinh_chat():
    """Migration KHÔNG được bịa tính chất cho các tài khoản đang có."""
    r = client.get(f"{P}/tai-khoan-chieu", headers=login("ketoan"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["chua_khai_tinh_chat"] > 0, (
        "Mọi tài khoản đều đã có tính chất nghĩa là migration đã khai hộ — đó là bịa dữ liệu.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# F. Thắt thì Kế toán làm được, nới phải có chữ ký
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_f1_ke_toan_bat_co_duoc_vi_do_la_that():
    _tk("9910")
    r = client.post(f"{P}/tai-khoan-chieu", headers=login("ketoan"),
                    json={"code": "9910", "td_cong_trinh": True})
    assert r.status_code == 200, r.text
    assert "công trình" in " ".join(r.json()["chieu_bat_buoc"])


def test_f2_ke_toan_tat_co_dang_bat_thi_bi_chan():
    _tk("9911", td_cong_trinh=True)
    r = client.post(f"{P}/tai-khoan-chieu", headers=login("ketoan"),
                    json={"code": "9911", "td_cong_trinh": False})
    assert r.status_code == 403
    assert "chữ ký" in r.json()["detail"]


def test_f3_chu_tich_tat_co_duoc():
    _tk("9912", td_cong_trinh=True)
    r = client.post(f"{P}/tai-khoan-chieu", headers=login("chutich"),
                    json={"code": "9912", "td_cong_trinh": False})
    assert r.status_code == 200, r.text


def test_f4_doi_tinh_chat_da_khai_phai_co_chu_ky():
    _tk("9913", tinh_chat="du_no")
    r = client.post(f"{P}/tai-khoan-chieu", headers=login("ketoan"),
                    json={"code": "9913", "tinh_chat": "du_co"})
    assert r.status_code == 403, "Đổi tính chất đã khai là đổi nghĩa của phép kiểm số dư."
    r2 = client.post(f"{P}/tai-khoan-chieu", headers=login("chutich"),
                     json={"code": "9913", "tinh_chat": "du_co"})
    assert r2.status_code == 200, r2.text


def test_f5_khai_tinh_chat_lan_dau_thi_ke_toan_lam_duoc():
    _tk("9914")
    r = client.post(f"{P}/tai-khoan-chieu", headers=login("ketoan"),
                    json={"code": "9914", "tinh_chat": "du_co"})
    assert r.status_code == 200, r.text


def test_f6_bat_td_doi_tuong_ma_khong_noi_loai_thi_mac_dinh_tat_ca():
    _tk("9915")
    client.post(f"{P}/tai-khoan-chieu", headers=login("ketoan"),
                json={"code": "9915", "td_doi_tuong": True})
    db = SessionLocal()
    try:
        assert db.get(Account, "9915").td_doi_tuong_loai == "tat_ca"
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# G. Chỉ khai cờ nào có cột để kiểm
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_g1_moi_chieu_khai_deu_co_cot_that_tren_journal_lines():
    cot = set(JournalLine.__table__.columns.keys())
    for co, (ten_cot, _doc) in KTC.CHIEU.items():
        assert ten_cot in cot, (
            f"Cờ {co} trỏ tới cột '{ten_cot}' không có trên journal_lines. Một cờ không có cột "
            "là một cờ bật được mà không kiểm được gì.")
        assert hasattr(Account, co), f"Cờ {co} chưa có trên Account"


def test_g2_khong_khai_thua_co_cho_bay_chieu_chua_co_cot():
    """Bảy chiều còn lại của MISA chờ Đợt E3 — chưa có cột thì chưa được khai cờ."""
    chua_den_luot = ("td_tk_ngan_hang", "td_muc_thu_chi", "td_ma_thong_ke", "td_don_vi",
                     "td_don_dat_hang", "td_hop_dong_ban", "td_hop_dong_mua")
    co_som = [c for c in chua_den_luot if hasattr(Account, c)]
    assert not co_som, (
        f"Khai sớm cờ chưa có cột để kiểm: {co_som}. Mở cột trên journal_lines trước.")


def test_g3_bang_chieu_doc_duoc_bang_vai_xem():
    r = client.get(f"{P}/tai-khoan-chieu?chi_da_khai=true", headers=login("bks"))
    assert r.status_code == 200, r.text
    assert "tinh_chat" in r.json()


def test_g4_muc_do_chan_co_cua_nhap_khai_trong_ks_cua_nhap():
    from app.services.ks_cua_nhap import CUA_TAY
    assert "muc_do_chan" in CUA_TAY, (
        "Mỗi bảng phải có một cửa. Không có cửa thì đó là việc còn thiếu.")
