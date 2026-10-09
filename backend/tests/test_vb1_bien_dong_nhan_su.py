# -*- coding: utf-8 -*-
"""VB-1 · 5.8 Báo cáo biến động nhân sự: một phép tính, và nó phải CÂN.

    đầu kỳ + tăng trong kỳ − giảm trong kỳ = cuối kỳ

HÀNG RÀO ĐẮT NHẤT TỆP NÀY là `test_dang_thuc_can_o_moi_phong_va_moi_ky`. Nó không kiểm một con số
nào cả — nó kiểm CÁI CÂN. Thêm một đường vào hoặc ra mà quên nối vào bộ đếm thì nó đỏ ngay, kể cả
khi mọi con số in ra trông vẫn hợp lý. Một bảng biến động lệch một người vẫn đẹp trên màn hình.

HÀNG RÀO THỨ HAI, và nó canh một thứ tinh vi hơn: người đã nghỉ mà CHƯA có ngày nghỉ không nằm
trong bất kỳ kỳ nào, nên MỌI kỳ đều cân — và cái cân ấy là cân giả. `chua_biet_ngay_nghi()` phải
đếm được họ; không có bộ đếm thì nhóm ấy chìm đi mà bảng vẫn báo cân.
"""
import os
import re
import sys
from datetime import date
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_vb1.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_vb1.db"):
    os.remove("test_vb1.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal, Base        # noqa: E402
from app.models.core import User                     # noqa: E402
from app.models.hr import Employee                   # noqa: E402
from app.services import bien_dong_ns as BD          # noqa: E402

GOC = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _doc(*p) -> str:
    return (GOC.joinpath(*p)).read_text(encoding="utf-8")


def _vai(db, ten):
    return db.execute(select(User).where(User.role == ten,
                                         User.active.is_(True))).scalars().first()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CẤU TRÚC
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_ba_cot_ngay_nghi_co_that_va_mot_dau_alembic():
    cot = Base.metadata.tables["employees"].columns.keys()
    for c in ("ended_on", "end_kind", "end_reason"):
        assert c in cot, f"thiếu cột {c} trên employees — không có ngày nghỉ thì vế 'giảm trong kỳ' không tính được"
    thu_muc = GOC / "backend" / "alembic" / "versions"
    # MÔ HÌNH CÓ CỘT KHÔNG ĐỦ — PHẢI CÓ MIGRATION TẠO RA CỘT ẤY.
    #
    # Bắt được bằng kiểm ngược: xoá hẳn tệp migration thì bản đầu của phép thử này VẪN XANH, vì
    # `Base.metadata` đọc từ mã Python chứ không đọc cơ sở dữ liệu. Trên máy phép thử (sqlite dựng
    # bằng create_all) mọi thứ chạy; trên Render, nơi alembic upgrade head mới là thứ tạo bảng,
    # cột không tồn tại và mọi truy vấn chạm `employees` đổ ngay khi khởi động.
    co_migration = [p.name for p in thu_muc.glob("*.py")
                    if all(c in p.read_text(encoding="utf-8")
                           for c in ("ended_on", "end_kind", "end_reason"))]
    assert co_migration, (
        "ba cột có trong mô hình mà KHÔNG migration nào tạo ra chúng. Máy phép thử dựng bảng bằng "
        "create_all nên vẫn xanh; bản chạy thật dựng bằng alembic nên sẽ thiếu cột.")
    rev, down = {}, {}
    for p in thu_muc.glob("*.py"):
        s = p.read_text(encoding="utf-8")
        r = re.search(r'^revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        if r:
            rev[r.group(1)] = p.name
            down[r.group(1)] = d.group(1) if d else None
    dau = [k for k in rev if k not in set(down.values())]
    assert len(dau) == 1, f"alembic phải có ĐÚNG MỘT đầu, đang có: {[rev[k] for k in dau]}"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHÉP TÍNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_dang_thuc_can_o_moi_phong_va_moi_ky():
    """Không kiểm một con số nào — kiểm CÁI CÂN.

    Dựng một cảnh có thật: một người vào trong kỳ, một người nghỉ trong kỳ. Rồi đòi
    đầu kỳ + tăng − giảm = cuối kỳ ở TỪNG phòng và ở tổng, qua cả ba loại kỳ.
    """
    with SessionLocal() as db:
        nv = list(db.execute(select(Employee)).scalars())[:3]
        assert len(nv) == 3, "bản demo cần ít nhất ba hồ sơ nhân sự"
        nv[0].start_date = date(2027, 5, 10)        # vào giữa kỳ
        nv[1].start_date = date(2024, 1, 1)
        nv[1].ended_on, nv[1].end_kind, nv[1].active = date(2027, 5, 20), "tu_xin", False
        # NGƯỜI THỨ BA LÀ CÁI BẪY, và cảnh phải có nó. Đã nghỉ (`active = False`) mà CHƯA ai điền
        # ngày — nhóm có sẵn trong VTOS từ trước VB-1. Nhét họ vào "giảm kỳ này" thì tháng đầu tiên
        # chạy báo cáo có một cú giảm giả bằng cả lịch sử công ty, và đẳng thức lệch ngay.
        # Không dựng người này thì bản phá ấy vẫn xanh — đã thử, và nó xanh thật.
        nv[2].start_date = date(2024, 1, 1)
        nv[2].ended_on, nv[2].end_kind, nv[2].active = None, "", False
        db.flush()
        for ky_loai, ky in (("thang", "2027-05"), ("quy", "2027-Q2"), ("nam", "2027")):
            bc = BD.bao_cao(db, ky_loai, ky)
            for ten, p in bc["theo_phong"].items():
                assert p["lech"] == 0, (
                    f"{ky_loai} {ky}, phòng {ten}: đầu kỳ {p['dau_ky']} + tăng {p['tang']} − giảm "
                    f"{p['giam']} ≠ cuối kỳ {p['cuoi_ky']}. Lệch nghĩa là có một đường vào hoặc ra "
                    "mà bộ đếm không thấy.")
            assert bc["tong"]["lech"] == 0
            assert bc["tong"]["tang"] >= 1 and bc["tong"]["giam"] >= 1, (
                "cảnh dựng có một người vào và một người nghỉ trong kỳ mà bộ đếm không thấy")
        db.rollback()


def test_nguoi_nghi_truoc_ky_KHONG_bi_dem_lai_vao_ky_dang_xem():
    """Nghỉ tháng 3 thì tháng 5 không được đếm là giảm — và cũng không được có mặt ở đầu kỳ."""
    with SessionLocal() as db:
        e = db.execute(select(Employee)).scalars().first()
        e.start_date = date(2024, 1, 1)
        e.ended_on, e.end_kind, e.active = date(2027, 3, 15), "tu_xin", False
        db.flush()
        bc = BD.bao_cao(db, "thang", "2027-05")
        p = bc["theo_phong"][e.department or "(chưa khai phòng)"]
        truoc = BD.bao_cao(db, "thang", "2027-03")["theo_phong"][e.department or "(chưa khai phòng)"]
        assert truoc["giam"] >= 1, "nghỉ tháng 3 mà tháng 3 không đếm là giảm"
        assert p["lech"] == 0
        db.rollback()


def test_chuyen_phap_nhan_KHONG_vao_ty_le_nghi_viec():
    """Chuyển sang pháp nhân khác trong tập đoàn thì người ấy CHƯA rời Vietourist.

    Gộp chung thì tỷ lệ nghỉ việc báo cáo lên HĐQT bị thổi lên đúng bằng số người chuyển nội bộ.
    """
    with SessionLocal() as db:
        nv = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())[:2]
        assert len(nv) == 2
        for e in nv:
            e.start_date, e.department = date(2024, 1, 1), "zz_thu"
        nv[0].ended_on, nv[0].end_kind, nv[0].active = date(2027, 7, 10), "tu_xin", False
        nv[1].ended_on, nv[1].end_kind, nv[1].active = date(2027, 7, 11), "chuyen_cong_ty", False
        db.flush()
        p = BD.bao_cao(db, "thang", "2027-07")["theo_phong"]["zz_thu"]
        assert p["giam"] == 2, "cả hai đều là giảm đầu người của phòng"
        assert p["giam_nghi_viec"] == 1 and p["giam_chuyen_cong_ty"] == 1
        assert p["lech"] == 0
        db.rollback()


def test_ty_le_nghi_viec_tinh_tren_BINH_QUAN_khong_tren_dau_ky():
    """Phòng 2 người mất 1: chia đầu kỳ ra 50%, chia bình quân ra 67%. 67% mới mô tả đúng kỳ ấy."""
    with SessionLocal() as db:
        nv = list(db.execute(select(Employee).where(Employee.active.is_(True))).scalars())[:2]
        for e in nv:
            e.start_date, e.department, e.ended_on, e.end_kind = date(2024, 1, 1), "zz_bq", None, ""
        nv[0].ended_on, nv[0].end_kind, nv[0].active = date(2027, 8, 10), "tu_xin", False
        db.flush()
        p = BD.bao_cao(db, "thang", "2027-08")["theo_phong"]["zz_bq"]
        assert p["dau_ky"] == 2 and p["cuoi_ky"] == 1 and p["binh_quan"] == 1.5
        assert p["ty_le_nghi_viec"] == 66.7, (
            f"chia bình quân 1,5 phải ra 66,7%, nhận {p['ty_le_nghi_viec']} — chia đầu kỳ ra 50%")
        db.rollback()


def test_bo_dem_nguoi_da_nghi_ma_chua_co_ngay_that_su_nhin_thay():
    """Nhóm này không nằm trong kỳ nào, nên MỌI kỳ đều cân — và cái cân ấy là cân giả.

    Hỏi BỘ ĐẾM: dựng thêm một người `active = False` không ngày thì con số phải tăng.
    """
    with SessionLocal() as db:
        truoc = BD.chua_biet_ngay_nghi(db)["so_nguoi"]
        e = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().first()
        e.active, e.ended_on = False, None
        db.flush()
        sau = BD.chua_biet_ngay_nghi(db)
        assert sau["so_nguoi"] == truoc + 1, (
            "thêm một người đã nghỉ không ngày mà bộ đếm không thấy — nhóm ấy sẽ chìm đi và mọi kỳ "
            "vẫn báo cân")
        assert any(r["employee_id"] == e.id for r in sau["rows"])
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA NHẬP
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_cua_ghi_ngay_nghi_chan_dung_bon_cho():
    with SessionLocal() as db:
        hcns = _vai(db, "hcns")
        e = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().first()
        e.start_date = date(2026, 1, 1)
        db.flush()
        with pytest.raises(ValueError):                       # lý do lạ
            BD.ghi_nghi_viec(db, hcns, e.id, date(2026, 6, 1), "nghi_choi")
        with pytest.raises(ValueError):                       # trước ngày vào
            BD.ghi_nghi_viec(db, hcns, e.id, date(2025, 6, 1), "tu_xin")
        with pytest.raises(ValueError):                       # tương lai
            BD.ghi_nghi_viec(db, hcns, e.id, date(2099, 1, 1), "tu_xin")
        with pytest.raises(ValueError):                       # không có hồ sơ
            BD.ghi_nghi_viec(db, hcns, 999999, date(2026, 6, 1), "tu_xin")
        r = BD.ghi_nghi_viec(db, hcns, e.id, date(2026, 6, 1), "tu_xin", "chuyển chỗ ở")
        assert r["active"] is False and r["ended_on"] == "2026-06-01"
        db.rollback()


def test_go_ngay_nghi_bat_buoc_ghi_ly_do_va_tra_nguoi_ve_dang_lam():
    with SessionLocal() as db:
        hcns = _vai(db, "hcns")
        e = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().first()
        e.start_date = date(2026, 1, 1)
        db.flush()
        BD.ghi_nghi_viec(db, hcns, e.id, date(2026, 6, 1), "tu_xin")
        with pytest.raises(ValueError):
            BD.huy_nghi_viec(db, hcns, e.id, "")
        r = BD.huy_nghi_viec(db, hcns, e.id, "ghi nhầm người")
        assert r["ended_on"] is None and r["active"] is True
        assert "ghi nhầm người" in r["end_reason"] and "gỡ" in r["end_reason"], (
            "gỡ xong phải để lại dấu vết — không có dấu vết thì lần bấm nhầm được chữa trong im lặng")
        with pytest.raises(ValueError):
            BD.huy_nghi_viec(db, hcns, e.id, "gỡ lần hai")
        db.rollback()


def test_ghi_ngay_nghi_KHONG_tu_dong_cham_dut_hop_dong():
    """Hai việc, hai chứng từ, hai ngày có thể khác nhau (bàn giao xong mới ký thanh lý).

    Nối tự động thì một lần bấm ở đây lặng lẽ đóng một hợp đồng lao động mà không ai ký.
    """
    from app.models.hrm import LaborContract
    with SessionLocal() as db:
        hcns = _vai(db, "hcns")
        e = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().first()
        e.start_date = date(2026, 1, 1)
        hd = LaborContract(employee_id=e.id, code="HD-VB1-TEST", kind="xac_dinh_12",
                           effective_from=date(2026, 1, 1), status="hieu_luc")
        db.add(hd)
        db.flush()
        BD.ghi_nghi_viec(db, hcns, e.id, date(2026, 6, 1), "tu_xin")
        db.refresh(hd)
        assert hd.status == "hieu_luc" and hd.terminated_on is None, (
            "ghi ngày nghỉ đã tự chấm dứt hợp đồng — đó là một chứng từ thứ hai, phải có người ký")
        db.rollback()


def test_cua_ghi_hep_hon_cua_xem():
    """XEM rộng bằng thẻ Tổng quan; GHI chỉ HR_ADMIN. Ghi ngày nghỉ là đóng một người khỏi bảng lương."""
    from app.api.v1 import bien_dong_ns as API
    assert set(API.GHI) == {"hcns", "cntt", "tgd", "chutich"}
    assert set(API.GHI) < set(API.XEM), "nhóm ghi phải HẸP HƠN THẬT SỰ nhóm xem"
    for vai in ("ketoan", "bks", "gd_kd", "ptgd_doan", "tp_dh"):
        assert vai not in API.GHI, f"{vai} không được ghi ngày nghỉ việc"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MÀN HÌNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_muc_5_8_tren_cay_khong_con_khai_la_chua_co_va_tro_dung_cho():
    cay = _doc("web", "lib", "cay_phan_he.ts")
    dong = next(d for d in cay.splitlines() if d.strip().startswith('{ ma: "5.8"'))
    assert "chưa" not in dong, f"5.8 đã dựng thật mà cây vẫn khai là chưa có: {dong.strip()}"
    assert "/hr?tab=tong_quan" in dong, (
        "5.8 phải trỏ về nơi báo cáo thật sự đứng. Trỏ về /reports là trỏ sang ba thẻ báo cáo DO "
        "NHÂN VIÊN VIẾT — không đầu người, không tăng giảm, không cơ cấu.")


def test_khoi_bien_dong_duoc_DUNG_that_tren_the_tong_quan():
    hr = _doc("web", "components", "HrScreens.tsx")
    assert "<BienDongNhanSu />" in hr, (
        "thẻ Tổng quan HCNS chưa DỰNG khối biến động. Hỏi chỗ dựng chứ không hỏi tên mô-đun: một "
        "hàng rào đọc tên chỉ chứng minh người ta đã gõ tên ấy một lần.")
    tp = _doc("web", "components", "BienDongNhanSu.tsx")
    assert "/bien-dong-ns" in tp, "khối không gọi cửa nào"
    # CỘT LỆCH PHẢI IN RA, KHÔNG GIẤU: một bảng tự nhận là cân mà không cho nhìn chỗ cân thì không
    # ai kiểm được nó. Hỏi CẢ tiêu đề cột LẪN ô dữ liệu — bản đầu chỉ hỏi chữ "Lệch" có mặt trong
    # tệp, và kiểm ngược bắt được: xoá `<th>Lệch</th>` mà giữ đoạn văn giải thích thì nó vẫn xanh,
    # tức bảng không còn cột ấy mà hàng rào vẫn bảo có.
    assert "<th>Lệch</th>" in tp, "bảng không còn tiêu đề cột Lệch"
    # Hỏi Ô IN RA, không hỏi chuỗi "v.lech" có mặt: chuỗi ấy còn nằm trong `className` tô màu cảnh
    # báo, nên thay giá trị ô bằng số 0 cứng vẫn qua được bản trước. Kiểm ngược bắt đúng chỗ đó.
    assert "{v.lech}</td>" in tp, "ô Lệch của từng phòng không in giá trị thật"
    assert "{t.lech}</th>" in tp, "ô Lệch của dòng tổng không in giá trị thật"
    assert "chua_biet_ngay_nghi" in tp, "màn hình không in nhóm đã nghỉ mà chưa có ngày"
