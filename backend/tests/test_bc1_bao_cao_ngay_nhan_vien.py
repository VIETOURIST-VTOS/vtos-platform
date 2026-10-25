# -*- coding: utf-8 -*-
"""BC-1 · Báo cáo ngày phía NHÂN VIÊN — Chủ tịch duyệt bản xem thử 26/10/2026.

Năm điều Chủ tịch chốt và tài liệu bàn giao IT (25/10/2026) đòi, mỗi điều một nhóm phép thử:
  1. Hạn trước 0 giờ ngày kế tiếp, giờ Việt Nam; đúng 00:00 là muộn; ngày trước mốc giữ hạn 20 giờ.
  2. Đúng hạn tính theo LẦN NỘP ĐẦU; nộp lại thêm phiên bản, không đổi cờ đúng hạn.
  3. Mọi nhân viên văn phòng phải nộp, trừ HDV, tài xế và Ban TGĐ; TP Hướng dẫn, quản lý xe vẫn nộp.
  4. Nghỉ CẢ NGÀY đã duyệt không có nghĩa vụ; nửa ngày và công tác không miễn.
  5. Kiêm nhiệm do Chủ tịch giao; mẫu Ngân hàng đọc danh mục tài khoản, không viết cứng.
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker

GOC = Path(__file__).resolve().parents[2]
D = date(2026, 10, 27)          # sau mốc 26-10-2026 → luật 0 giờ


@pytest.fixture()
def db():
    import app.models  # noqa: F401 — nạp mọi mô hình để create_all giải được khoá ngoại
    from app.db.session import Base
    from app.services import rules as R
    e = create_engine("sqlite://")
    Base.metadata.create_all(e)
    s = sessionmaker(bind=e)()
    R.clear_param_cache()
    yield s
    s.close()


def _nguoi(db, username="an", phong="ketoan", vi_tri="nv"):
    from app.models.core import User
    from app.models.hr import Employee
    u = User(username=username, full_name=username.upper(), role="ketoan", password_hash="x", active=True)
    db.add(u); db.flush()
    e = Employee(code=f"NV-{username}", full_name=username.upper(), department=phong, position=vi_tri,
                 user_id=u.id, active=True)
    db.add(e); db.flush()
    return u, e


# ── 1 · hạn nộp ────────────────────────────────────────────────────────────────────────────────

def test_han_0_gio_ngay_ke_tiep_va_dung_00_00_la_muon(db):
    from app.services import ops as O
    assert O.han_nop(db, D) == datetime(2026, 10, 28, 0, 0)
    u, _ = _nguoi(db)
    r = O.submit_report(db, u, D, "x" * 30, "{}", "", "y" * 30, now=datetime(2026, 10, 27, 23, 59, 59))
    assert r.on_time is True
    u2, _ = _nguoi(db, "binh")
    r2 = O.submit_report(db, u2, D, "x" * 30, "{}", "", "y" * 30, now=datetime(2026, 10, 28, 0, 0, 0))
    assert r2.on_time is False, "đúng 00:00 là muộn cho ngày trước"


def test_ngay_truoc_moc_giu_han_20_gio(db):
    from app.services import ops as O
    cu = date(2026, 10, 20)
    assert O.han_chu(db, cu) == "20:00" and O.han_chu(db, D) == "0:00 ngày kế tiếp"
    u, _ = _nguoi(db)
    assert O.submit_report(db, u, cu, "x" * 30, "{}", "", "y" * 30, now=datetime(2026, 10, 20, 20, 0)).on_time
    u2, _ = _nguoi(db, "binh")
    assert not O.submit_report(db, u2, cu, "x" * 30, "{}", "", "y" * 30, now=datetime(2026, 10, 20, 20, 1)).on_time


def test_ngay_tuong_lai_theo_gio_viet_nam(db):
    from app.services import ops as O
    u, _ = _nguoi(db)
    with pytest.raises(ValueError):
        O.submit_report(db, u, D + timedelta(days=1), "x", "{}", "", "y", now=datetime(2026, 10, 27, 23, 0))


# ── 2 · lần nộp đầu + phiên bản ─────────────────────────────────────────────────────────────────

def test_nop_lai_giu_lan_dau_va_them_phien_ban(db):
    from app.models.ops import DailyReportVersion
    from app.services import ops as O
    u, _ = _nguoi(db)
    r = O.submit_report(db, u, D, "lần một " * 4, "{}", "", "y" * 30, now=datetime(2026, 10, 27, 21, 14))
    dau = r.first_submitted_at
    r = O.submit_report(db, u, D, "lần hai " * 4, '{"Hóa đơn đã xuất trong ngày": "3"}', "", "y" * 30,
                        now=datetime(2026, 10, 28, 8, 30))
    assert r.first_submitted_at == dau and r.on_time is True, "nộp lại sau hạn không biến báo cáo đúng hạn thành muộn"
    assert r.so_lan_nop == 2 and r.submitted_at == datetime(2026, 10, 28, 8, 30)
    v = db.query(DailyReportVersion).filter_by(report_id=r.id).order_by(DailyReportVersion.lan).all()
    assert [x.lan for x in v] == [1, 2] and "lần một" in v[0].du_lieu, "bản lần đầu phải còn nguyên"


def test_muon_roi_nop_lai_van_la_muon(db):
    from app.services import ops as O
    u, _ = _nguoi(db)
    O.submit_report(db, u, D, "x" * 30, "{}", "", "y" * 30, now=datetime(2026, 10, 28, 0, 12))
    r = O.submit_report(db, u, D, "x" * 31, "{}", "", "y" * 30, now=datetime(2026, 10, 28, 0, 20))
    assert r.on_time is False


def test_vuong_mac_co_phong_nhan_va_han(db):
    from app.services import ops as O
    u, _ = _nguoi(db)
    r = O.submit_report(db, u, D, "x" * 30, "{}", "giao dịch chưa rõ", "y" * 30, vuong_mac_cho="kd_le",
                        vuong_mac_han=date(2026, 10, 28), now=datetime(2026, 10, 27, 17, 0))
    assert (r.vuong_mac_cho, r.vuong_mac_han) == ("kd_le", date(2026, 10, 28))
    with pytest.raises(ValueError):
        O.submit_report(db, u, D, "x" * 30, "{}", "", "y" * 30, vuong_mac_cho="khong_co",
                        now=datetime(2026, 10, 27, 17, 5))


# ── 3 · ai phải nộp ─────────────────────────────────────────────────────────────────────────────

def test_ai_phai_nop(db):
    from app.services import ops as O
    can = {
        ("ketoan", "nv"): True, ("huong_dan", "tp"): True, ("huong_dan", "hdv"): False,
        ("doi_xe", "tp"): True, ("doi_xe", "tai_xe"): False, ("ban_tgd", "khac"): False,
        ("visa", "visa"): True, ("kd_le", "hdv"): False,
    }
    for i, ((phong, vt), mong) in enumerate(can.items()):
        _, e = _nguoi(db, f"u{i}", phong, vt)
        assert O.phai_nop(e) is mong, (phong, vt)
    assert len(O.nhan_vien_phai_nop(db)) == sum(can.values())


# ── 4 · nghỉ cả ngày ────────────────────────────────────────────────────────────────────────────

def test_nghi_ca_ngay_mien_nua_ngay_va_cong_tac_khong_mien(db):
    from app.models.hrm import LeaveRequest
    from app.services import ops as O
    _, e = _nguoi(db)
    db.add_all([
        LeaveRequest(employee_id=e.id, kind="phep_nam", date_from=D, date_to=D, days=1, status="duyet"),
        LeaveRequest(employee_id=e.id, kind="phep_nam", date_from=D + timedelta(days=1), date_to=D + timedelta(days=1), days=0.5, status="duyet"),
        LeaveRequest(employee_id=e.id, kind="cong_tac", date_from=D + timedelta(days=2), date_to=D + timedelta(days=2), days=1, status="duyet"),
        LeaveRequest(employee_id=e.id, kind="phep_nam", date_from=D + timedelta(days=3), date_to=D + timedelta(days=3), days=1, status="cho_duyet"),
    ]); db.commit()
    assert O.nghi_ca_ngay(db, e.id, D)
    for k in (1, 2, 3):
        assert O.nghi_ca_ngay(db, e.id, D + timedelta(days=k)) is None, k


def test_trang_thai_ngay(db):
    from app.services import ops as O
    u, e = _nguoi(db)
    chua = O.trang_thai_ngay(db, e, u.id, D, now=datetime(2026, 10, 27, 22, 0))
    qua = O.trang_thai_ngay(db, e, u.id, D, now=datetime(2026, 10, 28, 0, 0))
    assert (chua["ma"], qua["ma"]) == ("chua_den_han", "qua_han")
    assert O.trang_thai_ngay(db, e, u.id, date(2026, 10, 25), now=datetime(2026, 10, 27))["ma"] == "khong_nghia_vu"  # Chủ nhật


# ── 5 · mẫu, kiêm nhiệm, ngân hàng ──────────────────────────────────────────────────────────────

def test_kiem_nhiem_va_mau_ngan_hang_doc_danh_muc(db):
    from app.models.banks import BankAccount
    from app.models.ops import ReportExtraForm
    from app.services import ops as O
    u, e = _nguoi(db)
    assert O.mau_cua(db, u) == ["ketoan"]
    db.add(ReportExtraForm(employee_id=e.id, mau="ngan_hang", active=True, boi="chutich"))
    db.add_all([BankAccount(code="MB1", bank_name="MB", currency="VND", active=True),
                BankAccount(code="TPB1", bank_name="TPBank", currency="VND", active=True),
                BankAccount(code="CU", bank_name="Cũ", currency="VND", active=False)])
    db.commit()
    assert O.mau_cua(db, u) == ["ketoan", "ngan_hang"]
    o = O.truong_cua(db, "ngan_hang")
    assert sum("số dư cuối ngày" in x for x in o) == 2, "đúng số tài khoản đang dùng — không viết cứng"
    assert O.khoa_o("ngan_hang", "ketoan", o[0]).startswith("Ngân hàng · ")
    assert O.khoa_o("ketoan", "ketoan", "Hóa đơn đã xuất trong ngày") == "Hóa đơn đã xuất trong ngày"


def test_muoi_ba_mau_va_ba_mau_chi_mo_bang_kiem_nhiem():
    from app.models.hr import DEPARTMENTS
    from app.services import ops as O
    for m in ("visa", "huong_dan", "doi_xe", "ngan_hang", "cskh", "ir_phap_che"):
        assert m in O.DEPT_FORMS, m
    assert O.DEPT_FORMS["huong_dan"]["fields"] == ["Đoàn đang có HDV", "Đoàn chưa phân HDV", "HDV đang đi tour",
                                                   "Nhận xét / khiếu nại về HDV", "Hồ sơ HDV cần bổ sung"]
    assert not set(O.MAU_KIEM_NHIEM) & set(DEPARTMENTS), "mẫu kiêm nhiệm không phải tên phòng"


def test_khong_phat_sinh_khac_o_trong():
    from app.models.ops import DailyReport
    from app.services import ops as O
    import json
    r = DailyReport(part1_done="x" * 30, part4_plan="y" * 30, on_time=True,
                    part2_numbers=json.dumps({"a": O.KHONG_PHAT_SINH, "b": "", "c": "2"}))
    _, note = O.robot_score(r)
    assert "2/3" in note, "«Không phát sinh» là ô đã điền; ô trống là chưa nhập"
    _, body = O.mail_text(type("U", (), {"full_name": "A"})(), "ketoan", D, "p1", {"a": O.KHONG_PHAT_SINH, "b": ""}, "p3", "p4")
    assert "b: chưa nhập" in body and "a: Không phát sinh" in body


# ── nối hệ ──────────────────────────────────────────────────────────────────────────────────────

def test_cua_api_quyen_dung_cho():
    src = (GOC / "backend/app/api/v1/ops.py").read_text(encoding="utf-8")
    for duong in ('@router.get("/daily-reports/kiem-nhiem")', '@router.post("/daily-reports/kiem-nhiem")'):
        i = src.index(duong)
        assert 'require_roles("chutich")' in src[i:i + 300], f"{duong}: chỉ Chủ tịch giao kiêm nhiệm"
    i = src.index('@router.post("/daily-reports/{rid}/tep"')
    than = src[i:i + 1400]
    assert "r.user_id != u.id" in than and "GIOI_HAN_TEP_MB" in than, "chỉ tác giả gắn tệp, tối đa 8 MB"
    assert "GIOI_HAN_TEP_MB = 8" in src


def test_tep_bao_cao_la_ho_so_nhan_su_khong_lo_qua_cua_chung():
    from app.models.attachments import DOI_TUONG_DAY_DU, NHOM_NHAY_CAM
    assert DOI_TUONG_DAY_DU["bao_cao_ngay"][2] in NHOM_NHAY_CAM


def test_tham_so_moc_han_la_tham_so_ngay():
    from app.services import rules as R
    assert "bao_cao_ngay_han_0h_tu" in R.THAM_SO_NGAY
    assert [p for p in R.DEFAULT_PARAMS if p[0] == "bao_cao_ngay_han_0h_tu"][0][1] == "26-10-2026"


def test_man_hinh_nop_dung_cua_moi():
    trang = (GOC / "web/app/reports/page.tsx").read_text(encoding="utf-8")
    assert "Không phát sinh" in trang and "/tep" in trang and "vuong_mac_cho" in trang
    assert not re.search(r"trước <b>20 giờ</b>", trang), "câu hạn 20 giờ cũ còn trên màn nộp"
