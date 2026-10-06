"""Phòng HDV Đợt 3 — tiền của hướng dẫn viên: sổ ứng theo NGƯỜI, đơn giá theo LOẠI TOUR.

  A. Sổ ứng theo người trả lời được câu "người này còn giữ bao nhiêu tiền công ty".
  B. KHÔNG gộp khác chủ tiền, khác loại tiền. Tiền thu hộ khách là túi riêng.
  C. Số âm nghĩa là công ty nợ lại — không phải lỗi, và hệ thống không tự trả.
  D. Rỗng vẫn là rỗng: chưa nhận tiền khác nhận 0 đồng.
  E. Đơn giá tra theo tuyến VÀ loại tour; bản riêng thắng bản chung; bản mới chỉ hạ bản cùng loại.
  F. Bảng đối soát thù lao là bảng ĐỌC; thiếu bảng giá thì để trống, không tính 0.
  G. Tiền thì Kế toán ghi; tất toán một khoản chưa về 0 thì bị chặn.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_hdv3.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_hdv3.db"):
    os.remove("test_hdv3.db")

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
TOK = {}
ID = {}
AI = "cntt"
KT = "ketoan"


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
        from sqlalchemy import select

        from app.db.session import SessionLocal
        from app.models.core import Tour, User
        from app.models.hr import Employee, GuideAssignment, GuideRate

        db = SessionLocal()
        op_id = db.execute(select(User)).scalars().first().id
        e = Employee(code="TU001", full_name="Vũ Văn E", department="huong_dan", position="hdv",
                     start_date=date(2024, 1, 1), card_no="TU001", card_expiry=date(2030, 1, 1),
                     member_org=True, contract_type="ctv", ctv_contract=True)
        t = Tour(code="TU-T1", name="Huế đoàn nước ngoài", tour_type="doan_nuoc_ngoai",
                 operator_id=op_id, start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        t2 = Tour(code="TU-T2", name="Huế khách lẻ", tour_type="le_noi_dia",
                  operator_id=op_id, start_date=date(2026, 11, 20), end_date=date(2026, 11, 23))
        db.add_all([e, t, t2])
        db.commit()
        # Hai bản giá cùng tuyến: một bản CHUNG và một bản riêng cho đoàn nước ngoài.
        chung = GuideRate(route="Huế 4N", loai_tour="", rate_per_day=500_000, days=4,
                          effective_from=date(2026, 1, 1), status="active")
        rieng = GuideRate(route="Huế 4N", loai_tour="doan_nuoc_ngoai", rate_per_day=900_000, days=4,
                          effective_from=date(2026, 1, 1), status="active")
        db.add_all([chung, rieng])
        db.commit()
        a = GuideAssignment(tour_id=t.id, guide_id=e.id, days=4, rate_per_day=900_000,
                            status="da_xac_nhan", bat_dau=datetime(2026, 11, 20, 6),
                            ket_thuc=datetime(2026, 11, 23, 20))
        db.add(a)
        db.commit()
        ID.update(e=e.id, t=t.id, t2=t2.id, a=a.id, chung=chung.id, rieng=rieng.id)
        db.close()
        yield


def _lap_ung(**kw):
    than = {"guide_id": ID["e"], "tour_id": ID["t"], "de_nghi": 5_000_000,
            "muc_dich": "Chi đoàn Huế"}
    than.update(kw)
    return client.post("/api/v1/guide-assignments/tam-ung", json=than, headers=login(AI))


def _so(guide_id=None):
    return client.get("/api/v1/guide-assignments/tam-ung/so-theo-nguoi",
                      params={"guide_id": guide_id or ID["e"]}, headers=login(AI)).json()


# ───────────────────────────── A · sổ theo người ─────────────────────────────
def test_a1_lap_duoc_khoan_ung_va_doc_duoc_so_theo_nguoi():
    r = _lap_ung()
    assert r.status_code == 201, r.text
    ID["u1"] = r.json()["id"]
    d = _so()
    assert d["hdv"] == "Vũ Văn E" and len(d["cac_khoan"]) == 1


def test_a2_ghi_tien_thi_so_du_doi_theo():
    r = client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u1']}/tien",
                    json={"da_nhan": 5_000_000}, headers=login(KT))
    assert r.status_code == 200, r.text
    assert r.json()["so_du"] == 5_000_000
    tui = _so()["cac_tui"]
    assert len(tui) == 1 and tui[0]["so_du"] == 5_000_000 and tui[0]["so_khoan_dang_mo"] == 1


def test_a3_chi_ho_va_nop_lai_tru_dung():
    client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u1']}/tien",
                json={"chi_ho_duyet": 3_000_000, "da_nop_lai": 1_000_000}, headers=login(KT))
    assert _so()["cac_tui"][0]["so_du"] == 1_000_000


def test_a4_ghi_cot_nay_khong_xoa_cot_kia():
    """Gửi rỗng một cột = KHÔNG đổi cột ấy. Không phân biệt thì mỗi lần ghi chi hộ sẽ vô tình xoá
    số đã nhận, và số dư nhảy lên bằng cả khoản ứng."""
    client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u1']}/tien",
                json={"da_nop_lai": 1_000_000}, headers=login(KT))
    k = _so()["cac_khoan"][0]
    assert k["da_nhan"] == 5_000_000 and k["chi_ho_duyet"] == 3_000_000


# ───────────────────────────── B · không gộp khác túi ─────────────────────────────
def test_b1_khac_loai_tien_thi_de_rieng_tui():
    r = _lap_ung(loai_tien="USD", de_nghi=300)
    assert r.status_code == 201
    client.post(f"/api/v1/guide-assignments/tam-ung/{r.json()['id']}/tien",
                json={"da_nhan": 300}, headers=login(KT))
    tui = _so()["cac_tui"]
    assert len(tui) == 2, "5 triệu đồng và 300 đô cộng lại thành 5.3 là một con số không ai trả được"
    assert {t["loai_tien"] for t in tui} == {"VND", "USD"}


def test_b2_tien_thu_ho_khach_la_tui_rieng_va_khong_bu_tru():
    r = _lap_ung(chu_tien="khach", de_nghi=2_000_000)
    client.post(f"/api/v1/guide-assignments/tam-ung/{r.json()['id']}/tien",
                json={"da_nhan": 2_000_000}, headers=login(KT))
    tui = _so()["cac_tui"]
    khach = [t for t in tui if t["chu_tien"] == "khach"][0]
    vnd_cty = [t for t in tui if t["chu_tien"] == "vietourist" and t["loai_tien"] == "VND"][0]
    assert khach["khong_bu_tru"] is True
    assert vnd_cty["so_du"] == 1_000_000, \
        "tiền khách không được trộn vào túi công ty – trộn là lấy tiền khách che khoản công ty nợ"


def test_b3_chu_tien_la_khong_hop_le_thi_tu_choi():
    assert _lap_ung(chu_tien="ai_do").status_code == 422


# ───────────────────────────── C · số âm ─────────────────────────────
def test_c1_chi_ho_vuot_ung_thi_so_du_am_va_noi_ro_cong_ty_no_lai():
    r = _lap_ung(de_nghi=1_000_000)
    uid = r.json()["id"]
    client.post(f"/api/v1/guide-assignments/tam-ung/{uid}/tien",
                json={"da_nhan": 1_000_000, "chi_ho_duyet": 1_500_000}, headers=login(KT))
    kq = client.post(f"/api/v1/guide-assignments/tam-ung/{uid}/tien",
                     json={}, headers=login(KT)).json()
    assert kq["so_du"] == -500_000
    assert "không tự trả" in kq["message"]
    ID["u_am"] = uid


def test_c2_cot_tien_am_thi_tu_choi():
    assert client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u1']}/tien",
                       json={"da_nhan": -1}, headers=login(KT)).status_code == 422


# ───────────────────────────── D · rỗng vẫn là rỗng ─────────────────────────────
def test_d1_bon_cot_tien_de_trong_duoc_va_khong_co_mac_dinh():
    from app.models.hdv import TamUngHdv
    for ten in ("de_nghi", "da_nhan", "chi_ho_duyet", "da_nop_lai"):
        c = TamUngHdv.__table__.columns[ten]
        assert c.nullable is True and c.default is None and c.server_default is None, \
            f"{ten}: 'chưa nhận tiền' khác 'nhận 0 đồng'"


def test_d2_khoan_moi_lap_thi_da_nhan_con_trong_chu_khong_phai_0():
    r = _lap_ung(de_nghi=777_000)
    k = [x for x in _so()["cac_khoan"] if x["id"] == r.json()["id"]][0]
    assert k["da_nhan"] is None and k["so_du"] == 0


# ───────────────────────────── E · đơn giá theo loại tour ─────────────────────────────
def test_e1_ban_rieng_thang_ban_chung():
    from app.db.session import SessionLocal
    from app.services.hdv import tra_don_gia
    db = SessionLocal()
    r = tra_don_gia(db, "Huế 4N", "doan_nuoc_ngoai", date(2026, 11, 23))
    assert r is not None and r.rate_per_day == 900_000, \
        "bản chung mới ký mà che mất bản riêng thì không ai thấy, vì cả hai đều đang hiệu lực"
    db.close()


def test_e2_loai_tour_khong_co_ban_rieng_thi_roi_ve_ban_chung():
    from app.db.session import SessionLocal
    from app.services.hdv import tra_don_gia
    db = SessionLocal()
    r = tra_don_gia(db, "Huế 4N", "le_noi_dia", date(2026, 11, 23))
    assert r is not None and r.rate_per_day == 500_000
    db.close()


def test_e3_ban_moi_chi_ha_ban_CUNG_LOAI_TOUR():
    """Thiếu vế loại tour thì một bản giá mới cho đoàn nước ngoài sẽ hạ luôn bản giá khách lẻ cùng
    tuyến — hai con số khác nhau bị coi là một."""
    r = client.post("/api/v1/guide-rates",
                    json={"route": "Huế 4N", "loai_tour": "doan_nuoc_ngoai", "days": 4,
                          "rate_per_day": 1_000_000, "effective_from": "2026-12-01"},
                    headers=login("hcns"))
    assert r.status_code == 201
    rid = [x for x in client.get("/api/v1/guide-rates", headers=login(AI)).json()
           if x["status"] == "pending"][-1]["id"]
    for vai in ("chutich", "tgd"):
        client.post(f"/api/v1/guide-rates/{rid}/sign", headers=login(vai))
    ds = {x["id"]: x for x in client.get("/api/v1/guide-rates", headers=login(AI)).json()}
    assert ds[ID["chung"]]["status"] == "active", "bản CHUNG phải còn nguyên hiệu lực"
    assert ds[ID["rieng"]]["status"] == "rejected", "chỉ bản cùng loại tour mới bị hạ"


def test_e4_thieu_don_gia_thi_tra_rong_chu_khong_tra_0():
    from app.services.hdv import thu_lao
    assert thu_lao(4, None) is None, "một bảng thù lao toàn số 0 trông như đã tính xong và trả đủ"
    assert thu_lao(4, 500_000) == 2_000_000
    assert thu_lao(4, 500_000, le_tet=True) == 4_000_000
    assert thu_lao(None, 500_000) == 0, "0 ngày là một con số có thật"


# ───────────────────────────── F · bảng đối soát là bảng đọc ─────────────────────────────
def test_f1_doi_soat_tinh_dung_va_khong_ghi_gi_xuong_csdl():
    r = client.get("/api/v1/guide-assignments/thu-lao/doi-soat",
                   params={"tu_ngay": "2026-11-01", "den_ngay": "2026-11-30"}, headers=login(AI))
    assert r.status_code == 200, r.text
    d = r.json()
    dong = [x for x in d["dong"] if x["assignment_id"] == ID["a"]]
    assert dong and dong[0]["thu_lao"] == 4 * 900_000
    assert dong[0]["loai_tour"] == "doan_nuoc_ngoai"


def test_f2_treo_thu_lao_chi_hien_thi_lai_luat_da_co():
    d = client.get("/api/v1/guide-assignments/thu-lao/doi-soat",
                   params={"tu_ngay": "2026-11-01", "den_ngay": "2026-11-30"}, headers=login(AI)).json()
    dong = [x for x in d["dong"] if x["assignment_id"] == ID["a"]][0]
    assert dong["treo_thu_lao"] is True, "chưa nộp báo cáo thì treo – luật đã có ở services/luong.py"


def test_f3_khong_co_bang_thu_lao_ky_ghi_tien():
    """Chủ tịch chốt 06/10: quyết toán tour là sổ gốc, bảng kỳ chỉ ĐỌC. Không được có bảng nào tên
    kiểu remuneration_statement ghi tiền xuống cơ sở dữ liệu."""
    import app.models as M
    from app.db.session import Base
    ten = set(Base.metadata.tables)
    assert not {t for t in ten if "remuneration" in t or "thu_lao_ky" in t}, \
        "hai sổ cùng một khoản tiền thì sổ nào cũng đúng mà tổng thì sai"


# ───────────────────────────── G · ai ghi tiền, tất toán ─────────────────────────────
def test_g1_phong_hdv_khong_tu_ghi_duoc_tien():
    r = client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u1']}/tien",
                    json={"da_nhan": 9_000_000}, headers=login("tp.dieuhanh"))
    assert r.status_code == 403, "để phòng tự ghi 'đã nhận' thì con số ấy chỉ là lời khai"


def test_g2_tat_toan_khi_so_du_chua_ve_khong_thi_bi_chan():
    r = client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u_am']}/tat-toan",
                    json={}, headers=login(KT))
    assert r.status_code == 422 and r.json()["detail"]["gate"] == "UNG_CHUA_VE_KHONG"


def test_g3_ve_khong_roi_thi_tat_toan_duoc_va_khoa_lai():
    client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u_am']}/tien",
                json={"chi_ho_duyet": 1_000_000}, headers=login(KT))
    assert client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u_am']}/tat-toan",
                       json={}, headers=login(KT)).status_code == 200
    r = client.post(f"/api/v1/guide-assignments/tam-ung/{ID['u_am']}/tien",
                    json={"da_nhan": 1}, headers=login(KT))
    assert r.status_code == 422, "ghi thêm tiền vào khoản đã đóng là làm sai lại một việc đã xong"
