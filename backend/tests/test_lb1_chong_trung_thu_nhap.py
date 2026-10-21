"""Đợt B — chống trùng thu nhập liên phòng, liên kỳ.

  A. Mọi khoản thu nhập biến đổi đều khai LOẠI và CĂN CỨ máy đọc được – phép thử canh mã nguồn.
  B. Ký là ghi sổ, và sổ có khoá duy nhất (người, loại, căn cứ).
  C. Trùng căn cứ: cùng lý do trả hai kỳ → CHẶN.
  D. Trùng nguồn: cùng một chuyến nằm trong căn cứ của hai tháng → CHẶN, dù căn cứ khác tên.
  E. Một quỹ chia đủ cho nhiều người → CẢNH BÁO, có tên từng người và tổng chi.
  F. Ký lại cùng một kỳ KHÔNG tự chặn mình, và không sinh dòng trùng.
"""
import os
import re
import sys
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test_lb1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lb1.db"):
    os.remove("test_lb1.db")

import pytest
from tests.cong_da_duyet import duyet_cong
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
P = f"{date.today() - timedelta(days=14):%Y-%m}"


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


def _ky_xong(period=P):
    client.get(f"/api/v1/payroll-runs/{period}", params={"refresh": True}, headers=login("hcns"))
    duyet_cong(client, period, login)   # CN-1: công chưa duyệt thì kiểm cơ sở chặn
    client.post(f"/api/v1/payroll-runs/{period}/kiem-co-so", headers=login("hcns"))
    client.post(f"/api/v1/payroll-runs/{period}/advance", headers=login("hcns"))
    return client.post(f"/api/v1/payroll-runs/{period}/advance", headers=login("chutich"))


# ───────────────────── A · mọi khoản đều có căn cứ ─────────────────────
def test_a1_moi_loi_goi_add_deu_khai_loai_va_can_cu():
    """Đọc thẳng mã nguồn. Một nguồn thu nhập mới thêm vào mà quên khai căn cứ thì không ai chống
    trùng được cho nó — và chỗ quên ấy im lặng, nên phải có phép thử nói hộ."""
    import app.services.hr as H
    src = open(H.__file__, encoding="utf-8").read()
    than = src[src.index("def compute_draft"):src.index("def _dau_van_tay")]
    goi = [m for m in re.finditer(r"(?<![\w_])add\(e[,)]|(?<![\w_])add\(emps\[", than)]
    assert len(goi) >= 14, f"chỉ thấy {len(goi)} lời gọi add() – phép thử này đã lạc khỏi mã"
    # Mỗi lời gọi phải có loai= trong vòng 400 ký tự sau đó (lời gọi trải nhiều dòng).
    thieu = [than[m.start():m.start() + 60] for m in goi
             if 'loai="' not in than[m.start():m.start() + 400]]
    assert not thieu, "lời gọi add() không khai loại: " + " | ".join(thieu)


def test_a2_moi_loai_dung_trong_ma_deu_co_trong_bang_khai():
    import app.services.hr as H
    from app.services.thu_nhap_su_kien import LOAI_KHOAN
    src = open(H.__file__, encoding="utf-8").read()
    dung = set(re.findall(r'loai="([a-z0-9_]+)"', src))
    la = dung - set(LOAI_KHOAN)
    assert not la, f"loại khoản dùng trong mã mà chưa khai ở LOAI_KHOAN: {sorted(la)}"


def test_a3_ban_nhap_mang_theo_can_cu():
    r = client.get(f"/api/v1/payroll-runs/{P}", params={"refresh": True}, headers=login("hcns"))
    assert r.status_code == 200, r.text
    khoan = [k for row in r.json()["rows"] for k in (row.get("khoan") or [])]
    assert khoan, "kỳ mẫu không có khoản biến đổi nào – phép thử sau sẽ rỗng mà vẫn xanh"
    for k in khoan:
        assert k.get("loai") and k.get("can_cu"), f"khoản thiếu căn cứ: {k.get('ten')}"


# ───────────────────── B · ký là ghi sổ ─────────────────────
def test_b1_ky_xong_thi_so_co_dong():
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    r = _ky_xong()
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        so = TN.so_cua_ky(db, P)
    assert so, "ký rồi mà sổ rỗng – không có sổ thì không chống trùng được"
    for d in so:
        assert d["loai"] in TN.LOAI_KHOAN and d["can_cu"]


def test_b2_khoa_duy_nhat_chan_dong_thu_hai():
    """Hàng rào ở tầng cơ sở dữ liệu, không phải ở tầng mã. Phép kiểm vòng qua được; khoá thì không."""
    from sqlalchemy.exc import IntegrityError
    from app.db.session import SessionLocal
    from app.models.su_kien_thu_nhap import SuKienThuNhap
    with SessionLocal() as db:
        mau = db.query(SuKienThuNhap).first()
        assert mau is not None
        db.add(SuKienThuNhap(period="1900-01", ma_nv=mau.ma_nv, loai=mau.loai, can_cu=mau.can_cu,
                             so_tien=1))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


# ───────────────────── C · trùng căn cứ ─────────────────────
def test_c1_cung_can_cu_o_ky_khac_thi_chan():
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    with SessionLocal() as db:
        so = TN.so_cua_ky(db, P)
        mau = so[0]
        rows = [{"ma": mau["ma_nv"], "ten": "X", "khoan": [
            {"ten": "thử", "tien": 1, "loai": mau["loai"], "can_cu": mau["can_cu"], "nguon": []}]}]
        co = TN.kiem_trung(db, "1900-02", rows)
    trung = [c for c in co if c["ma"] == "TRUNG_CAN_CU"]
    assert len(trung) == 1, co
    assert trung[0]["muc"] == "chan"
    assert trung[0]["bang_chung"]["ky_da_tra"] == P, \
        "phải nói ra ĐÃ TRẢ Ở KỲ NÀO, không chỉ nói 'trùng'"


def test_c2_cung_ky_thi_khong_tu_chan_minh():
    """Ký lại một kỳ thành bản 2 là việc hợp lệ. Sổ so với các kỳ KHÁC, không so với chính nó."""
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    with SessionLocal() as db:
        so = TN.so_cua_ky(db, P)
        mau = so[0]
        rows = [{"ma": mau["ma_nv"], "ten": "X", "khoan": [
            {"ten": "thử", "tien": 1, "loai": mau["loai"], "can_cu": mau["can_cu"], "nguon": []}]}]
        co = TN.kiem_trung(db, P, rows)
    assert not [c for c in co if c["ma"] == "TRUNG_CAN_CU"]


# ───────────────────── D · trùng nguồn ─────────────────────
def test_d1_cung_mot_chuyen_o_hai_thang_thi_chan_du_can_cu_khac_ten():
    """Đây là chỗ trùng nguy nhất: chuyến chốt lại sang tháng sau sinh một căn cứ MỚI, trông như
    một khoản mới, và đi lọt qua phép kiểm trùng căn cứ."""
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    with SessionLocal() as db:
        co_nguon = [d for d in TN.so_cua_ky(db, P) if d["nguon"]]
        assert co_nguon, "kỳ mẫu không có khoản nào ghi nguồn – phép thử này sẽ rỗng mà vẫn xanh"
        mau = co_nguon[0]
        rows = [{"ma": mau["ma_nv"], "ten": "X", "khoan": [
            {"ten": "thử", "tien": 1, "loai": mau["loai"],
             "can_cu": mau["can_cu"] + "-thang-sau", "nguon": [mau["nguon"][0]]}]}]
        co = TN.kiem_trung(db, "1900-03", rows)
    trung = [c for c in co if c["ma"] == "TRUNG_NGUON"]
    assert len(trung) == 1, co
    assert trung[0]["muc"] == "chan"
    assert trung[0]["bang_chung"]["nguon"] == mau["nguon"][0]


# ───────────────────── E · một quỹ chia nhiều người ─────────────────────
def test_e1_mot_quy_tra_du_cho_hai_nguoi_thi_canh_bao_co_ten_tung_nguoi():
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    assert "quy_dh_tp" in TN.DOC_CHIEM
    rows = [{"ma": "A1", "ten": "Người A", "khoan": [
                {"ten": "30% quỹ", "tien": 1000, "loai": "quy_dh_tp", "can_cu": "quy_dh:1900-04", "nguon": []}]},
            {"ma": "A2", "ten": "Người B", "khoan": [
                {"ten": "30% quỹ", "tien": 1000, "loai": "quy_dh_tp", "can_cu": "quy_dh:1900-04", "nguon": []}]}]
    with SessionLocal() as db:
        co = TN.kiem_trung(db, "1900-04", rows)
    c = [x for x in co if x["ma"] == "CAN_CU_CHIA_NHIEU_NGUOI"]
    assert len(c) == 1, co
    assert c[0]["muc"] == "canh_bao", \
        "chặn ở đây là tự đổi công thức chia tiền – việc ấy cần chữ ký, không thuộc làn viết phần mềm"
    assert c[0]["bang_chung"]["tong_chi"] == 2000
    assert {x["ma_nv"] for x in c[0]["bang_chung"]["nguoi"]} == {"A1", "A2"}


def test_e2_mot_nguoi_thi_khong_canh_bao():
    from app.db.session import SessionLocal
    from app.services import thu_nhap_su_kien as TN
    rows = [{"ma": "A1", "ten": "Người A", "khoan": [
        {"ten": "30% quỹ", "tien": 1000, "loai": "quy_dh_tp", "can_cu": "quy_dh:1900-05", "nguon": []}]}]
    with SessionLocal() as db:
        co = TN.kiem_trung(db, "1900-05", rows)
    assert not [x for x in co if x["ma"] == "CAN_CU_CHIA_NHIEU_NGUOI"]


# ───────────────────── F · ghi sổ lại không sinh dòng trùng ─────────────────────
def test_f1_ghi_so_lan_hai_cap_nhat_chu_khong_them_dong():
    from app.db.session import SessionLocal
    from app.models.su_kien_thu_nhap import SuKienThuNhap
    from app.services import thu_nhap_su_kien as TN
    with SessionLocal() as db:
        truoc = db.query(SuKienThuNhap).count()
        rows = [{"ma": d["ma_nv"], "khoan": [{"ten": d["dien_giai"], "tien": 999, "loai": d["loai"],
                                              "can_cu": d["can_cu"], "nguon": d["nguon"]}]}
                for d in TN.so_cua_ky(db, P)]
        TN.ghi_so(db, P, rows)
        sau = db.query(SuKienThuNhap).count()
        moi = db.query(SuKienThuNhap).filter(SuKienThuNhap.so_tien == 999).count()
        db.rollback()
    assert sau == truoc, "ghi lại cùng khoá phải CẬP NHẬT, không thêm dòng"
    assert moi > 0, "bản ký sau phải ghi đè số của bản trước – bản đang hiệu lực là bản cuối"


def test_f2_bang_khai_la_may_sinh_khong_co_cua_go_tay():
    from app.services.ks_cua_nhap import CUA_TAY, MAY_SINH
    assert "su_kien_thu_nhap" in MAY_SINH
    assert "su_kien_thu_nhap" not in CUA_TAY
    assert len(MAY_SINH["su_kien_thu_nhap"]) >= 60, \
        "khai máy sinh phải kèm lý do đủ dài – 'máy sinh' là cách dễ nhất để một bảng thiếu cửa được cho qua"
