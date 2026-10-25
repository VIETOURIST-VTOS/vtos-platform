# -*- coding: utf-8 -*-
"""BC-2 · Tổng hợp báo cáo ngày cho NGƯỜI XEM XÉT — Chủ tịch duyệt bản xem thử 26/10/2026.

Điều Chủ tịch chốt cùng bản xem thử, mỗi điều một nhóm phép thử:
  1. Chỉ thấy phòng thuộc phạm vi (bảng bao_cao_phong.PHONG); Chủ tịch/TGĐ/BKS cả công ty; HCNS thấy
     trạng thái cả công ty nhưng nội dung chỉ phòng mình — máy chủ không trả nội dung.
  2. Ba số xử lý: chờ xem, cần bổ sung, quá hạn chưa nộp; thanh năm trạng thái; «không có nghĩa vụ»
     không vào mẫu số.
  3. Trả bổ sung bắt buộc lý do; nộp lại về «chờ xem» mà vẫn giữ lần nộp đầu; «đã xem» thì khoá.
  4. Không xem xét báo cáo của chính mình; mở bản cũ trong khi nhân viên vừa nộp lại thì báo 409.
  5. Vướng mắc chuyển phòng có trạng thái riêng, không đóng theo việc báo cáo đã xem.
  6. Giao hỗ trợ cho một người trong phòng mình, người ấy thấy và cập nhật được.
"""
from datetime import date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
D = date(2026, 10, 27)                          # sau mốc 0 giờ → hạn 00:00 ngày 28/10
TRONG_HAN = datetime(2026, 10, 27, 18, 0)
MUON = datetime(2026, 10, 28, 0, 30)
SAU_HAN = datetime(2026, 10, 28, 9, 0)
DAI = "Nội dung đủ dài trên hai mươi ký tự để tính điểm."


@pytest.fixture()
def db():
    import app.models  # noqa: F401
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def _nguoi(db, username, phong, vai="nv_dh", vi_tri="nv"):
    from app.models.core import User
    from app.models.hr import Employee
    u = User(username=username, full_name=username.upper(), role=vai, password_hash="x", active=True)
    db.add(u); db.flush()
    db.add(Employee(code=f"NV-{username}", full_name=username.upper(), department=phong, position=vi_tri,
                    user_id=u.id, active=True))
    db.flush()
    return u


def _nop(db, u, now, vuong_mac="", cho="", han=None):
    from app.services import ops as O
    return O.submit_report(db, u, D, DAI, "{}", vuong_mac, DAI, vuong_mac_cho=cho, vuong_mac_han=han, now=now)


@pytest.fixture()
def cty(db):
    """Phòng Điều hành 3 người + Visa 1 + KD Lẻ 1 + Kế toán 1, cùng các người xem."""
    p = {
        "tp": _nguoi(db, "tp.dh", "dieu_hanh", "tp_dh", "tp"),
        "a": _nguoi(db, "dh.a", "dieu_hanh"), "b": _nguoi(db, "dh.b", "dieu_hanh"), "c": _nguoi(db, "dh.c", "dieu_hanh"),
        "visa": _nguoi(db, "visa.a", "visa", "visa"),
        "kd": _nguoi(db, "kd.a", "kd_le", "nv_kd"),
        "kt": _nguoi(db, "kt.a", "ketoan", "ketoan"),
        "hcns": _nguoi(db, "hcns.a", "hcns", "hcns"),
        "ct": _nguoi(db, "ct", "ban_tgd", "chutich"),
    }
    _nop(db, p["a"], TRONG_HAN)
    _nop(db, p["b"], MUON)
    _nop(db, p["visa"], TRONG_HAN)
    _nop(db, p["kd"], TRONG_HAN)
    db.commit()
    return p


# ── 1 · phạm vi ───────────────────────────────────────────────────────────────────────────────

def test_pham_vi_theo_bang_phong(db, cty):
    from app.services import bao_cao_ngay_xem as X
    assert X.pham_vi_noi_dung(db, cty["tp"]) == {"dieu_hanh", "visa"}
    assert X.pham_vi_noi_dung(db, cty["ct"]) is None
    assert X.pham_vi_trang_thai(db, cty["hcns"]) is None, "HCNS thấy trạng thái cả công ty"
    assert X.pham_vi_noi_dung(db, cty["hcns"]) == {"hcns"}, "nhưng nội dung chỉ phòng mình"
    assert X.pham_vi_noi_dung(db, cty["kd"]) == set()


def test_tong_hop_khong_ro_phong_khac_va_hcns_khong_nhan_noi_dung(db, cty):
    from app.services import bao_cao_ngay_xem as X
    th = X.tong_hop(db, cty["tp"], D, now=SAU_HAN)
    ten = {d["ten"] for d in th["dong"]}
    assert "KD.A" not in ten and "KT.A" not in ten, "trưởng phòng ĐH không thấy phòng khác"
    assert {"DH.A", "DH.B", "DH.C", "VISA.A", "TP.DH"} <= ten
    h = X.tong_hop(db, cty["hcns"], D, now=SAU_HAN)
    assert h["chi_trang_thai"] is True
    kd = next(d for d in h["dong"] if d["ten"] == "KD.A")
    assert kd["noi_dung"] is None and kd["doc_duoc"] is False and kd["xem_xet_duoc"] is False
    assert kd["thoi_han"] == "dung_han", "trạng thái nộp vẫn có"
    with pytest.raises(PermissionError):
        X.tong_hop(db, cty["kd"], D, now=SAU_HAN)


# ── 2 · ba số xử lý và thanh trạng thái ───────────────────────────────────────────────────────

def test_ba_so_xu_ly_va_thanh_trang_thai(db, cty):
    from app.services import bao_cao_ngay_xem as X
    th = X.tong_hop(db, cty["tp"], D, now=SAU_HAN)
    # nộp: dh.a đúng hạn, dh.b muộn, visa.a đúng hạn; chưa nộp: dh.c và chính tp.dh
    assert th["dem"]["dung_han"] == 2 and th["dem"]["muon"] == 1 and th["dem"]["qua_han"] == 2
    assert th["xu_ly"] == {"cho_xem": 3, "can_bo_sung": 0, "qua_han": 2}
    assert th["phai_nop"] == 5 and th["da_nop"] == 3 and th["ty_le"] == 60
    truoc_han = X.tong_hop(db, cty["tp"], D, now=TRONG_HAN)
    assert truoc_han["dem"]["chua_den_han"] == 2 and truoc_han["xu_ly"]["qua_han"] == 0
    assert X.tong_hop(db, cty["tp"], D, phong="visa", now=SAU_HAN)["phai_nop"] == 1


# ── 3, 4 · xem xét ────────────────────────────────────────────────────────────────────────────

def _bc(db, u):
    from sqlalchemy import select
    from app.models.ops import DailyReport
    return db.execute(select(DailyReport).where(DailyReport.user_id == u.id, DailyReport.report_date == D)).scalars().one()


def test_tra_bo_sung_bat_buoc_ly_do_nop_lai_ve_cho_xem_giu_lan_dau(db, cty):
    from app.services import bao_cao_ngay_xem as X
    r = _bc(db, cty["b"])
    lan_dau, muon = r.first_submitted_at, r.on_time
    with pytest.raises(ValueError):
        X.xem_xet(db, cty["tp"], r, "bo_sung", ly_do="   ")
    X.xem_xet(db, cty["tp"], r, "bo_sung", ly_do="Thiếu số booking đã xác nhận", lan=1)
    assert X.trang_thai_xem(r) == "can_bo_sung"
    assert X.tong_hop(db, cty["tp"], D, now=SAU_HAN)["xu_ly"]["can_bo_sung"] == 1
    r = _nop(db, cty["b"], SAU_HAN)
    assert X.trang_thai_xem(r) == "cho_xem" and r.first_submitted_at == lan_dau and r.on_time == muon
    with pytest.raises(LookupError):
        X.xem_xet(db, cty["tp"], r, "da_xem", lan=1)    # đang mở bản lần 1, nhân viên đã nộp lần 2
    X.xem_xet(db, cty["tp"], r, "da_xem", lan=2)        # điểm không bắt buộc
    assert r.manager_score is None and X.trang_thai_xem(r) == "da_xem"
    with pytest.raises(ValueError):
        X.xem_xet(db, cty["tp"], r, "bo_sung", ly_do="muộn quá")
    with pytest.raises(ValueError):
        _nop(db, cty["b"], SAU_HAN)                     # đã xem thì khoá
    from sqlalchemy import select
    from app.models.ops import DailyReportReview
    assert [x.hanh_dong for x in db.execute(select(DailyReportReview).where(
        DailyReportReview.report_id == r.id)).scalars()] == ["bo_sung", "da_xem"]


def test_khong_tu_xem_minh_va_khong_xem_phong_khac(db, cty):
    from app.services import bao_cao_ngay_xem as X
    r_tp = _nop(db, cty["tp"], TRONG_HAN)
    with pytest.raises(PermissionError):
        X.xem_xet(db, cty["tp"], r_tp, "da_xem")
    assert next(d for d in X.tong_hop(db, cty["tp"], D, now=SAU_HAN)["dong"] if d["tu_minh"])["xem_xet_duoc"] is False
    X.xem_xet(db, cty["ct"], r_tp, "da_xem", diem=9)    # cấp trên xem được
    with pytest.raises(PermissionError):
        X.xem_xet(db, cty["tp"], _bc(db, cty["kd"]), "da_xem")
    with pytest.raises(ValueError):
        X.xem_xet(db, cty["ct"], _bc(db, cty["a"]), "da_xem", diem=11)


# ── 5 · vướng mắc chuyển phòng ────────────────────────────────────────────────────────────────

def test_vuong_mac_chuyen_phong_co_trang_thai_rieng(db, cty):
    from app.services import bao_cao_ngay_xem as X
    from app.models.ops import DailyReportFollowUp
    r = _nop(db, cty["c"], TRONG_HAN, vuong_mac="Thiếu hoá đơn khách sạn đoàn tháng 10", cho="ketoan", han=date(2026, 10, 29))
    db.commit()
    viec_kt = X.viec_cua(db, cty["kt"])["den_phong"]
    assert len(viec_kt) == 1 and viec_kt[0]["den_phong"] == "ketoan" and viec_kt[0]["tu_phong"] == "dieu_hanh"
    assert X.viec_cua(db, cty["kd"])["den_phong"] == [], "phòng khác không thấy"
    X.xem_xet(db, cty["tp"], r, "da_xem")
    f = db.get(DailyReportFollowUp, viec_kt[0]["id"])
    assert f.trang_thai == "mo", "báo cáo đã xem không đóng vướng mắc"
    with pytest.raises(PermissionError):
        X.cap_nhat_viec(db, cty["kd"], f, "da_xong")
    X.cap_nhat_viec(db, cty["kt"], f, "dang_xu_ly")
    X.cap_nhat_viec(db, cty["kt"], f, "da_xong", "Đã nhận đủ hoá đơn")
    with pytest.raises(ValueError):
        X.cap_nhat_viec(db, cty["kt"], f, "dang_xu_ly")


def test_bo_vuong_mac_o_lan_nop_lai_thi_rut(db, cty):
    from sqlalchemy import select
    from app.models.ops import DailyReportFollowUp
    _nop(db, cty["c"], TRONG_HAN, vuong_mac="Chờ tạm ứng", cho="ketoan")
    _nop(db, cty["c"], TRONG_HAN)
    f = db.execute(select(DailyReportFollowUp)).scalars().one()
    assert f.trang_thai == "rut"
    _nop(db, cty["c"], TRONG_HAN, vuong_mac="Chờ tạm ứng lần nữa", cho="ketoan")
    assert f.trang_thai == "mo" and "lần nữa" in f.noi_dung
    assert len(list(db.execute(select(DailyReportFollowUp)).scalars())) == 1, "một báo cáo một vướng mắc"


# ── 6 · giao hỗ trợ ───────────────────────────────────────────────────────────────────────────

def test_giao_ho_tro_trong_phong(db, cty):
    from app.services import bao_cao_ngay_xem as X
    r = _bc(db, cty["b"])
    with pytest.raises(ValueError):
        X.giao_ho_tro(db, cty["tp"], r, cty["kd"].id, "Hỗ trợ đặt xe", None)   # người phòng khác
    with pytest.raises(ValueError):
        X.giao_ho_tro(db, cty["tp"], r, cty["a"].id, "  ", None)
    with pytest.raises(PermissionError):
        X.giao_ho_tro(db, cty["kd"], r, cty["a"].id, "x", None)
    f = X.giao_ho_tro(db, cty["tp"], r, cty["a"].id, "Hỗ trợ DH.B đặt xe đoàn 28/10", date(2026, 10, 28))
    toi = X.viec_cua(db, cty["a"])["cua_toi"]
    assert len(toi) == 1 and toi[0]["loai"] == "ho_tro" and toi[0]["nguoi_nhan"] == "DH.A"
    X.cap_nhat_viec(db, cty["a"], f, "da_xong")
    nguoi = {x["ten"] for x in X.tong_hop(db, cty["tp"], D, now=SAU_HAN)["nguoi_giao_duoc"]}
    assert "DH.A" in nguoi and "KD.A" not in nguoi and "TP.DH" not in nguoi


# ── cửa API và màn hình ───────────────────────────────────────────────────────────────────────

def test_cua_api_khai_quyen_va_cua_cu_di_qua_hang_rao_moi():
    src = (GOC / "backend/app/api/v1/ops.py").read_text(encoding="utf-8")
    from app.api.v1 import ops as A
    for v in ("tp_hd", "gd_doi_xe", "ketoan", "tp_dh", "chutich"):
        assert v in A.VAI_XEM_XET
    review = src.split("def review(")[1].split("\n@router")[0]
    assert "XEM.xem_xet" in review, "cửa chấm cũ phải qua cùng hàng rào phạm vi"
    assert "XEM.co_quyen_noi_dung" in src.split("def _bao_cao_duoc_xem(")[1].split("\n@router")[0]


def test_man_hinh_dung_cua_moi():
    src = (GOC / "web/app/reports/page.tsx").read_text(encoding="utf-8")
    for s in ("/daily-reports/tong-hop", "/daily-reports/viec", "/giao-ho-tro", "Yêu cầu bổ sung",
              "Chờ xem", "Cần bổ sung", "Quá hạn chưa nộp", "Không có nghĩa vụ", "Đã xem"):
        assert s in src, s
