# -*- coding: utf-8 -*-
"""NS-5 · Ba bảng HCNS trong một migration: 5.6 Đánh giá, 5.9.2 Đề nghị mua, 5.9.3 Cấp phát.

HÀNG RÀO ĐẮT NHẤT TỆP NÀY là `test_khong_mot_duong_nao_bien_diem_thanh_tien`. Chủ tịch chốt
09/10/2026 điểm CHỈ ĐỂ XÉT thưởng, TGĐ/Chủ tịch quyết mức tiền bằng tay. Một ngày nào đó sẽ có
người thấy việc ấy thủ công và viết "cho tiện" một công thức nhân điểm với hệ số — và từ hôm ấy
phần mềm trả thưởng sai mà không ai ký. Phép thử ấy canh đúng chỗ đó.

HAI Ô "CHƯA CÓ SỐ" VÀ "0 ĐIỂM" LÀ HAI THỨ KHÁC NHAU, và có hai phép thử giữ ranh giới ấy: một cho
phép tính (ô rỗng không kéo trung bình xuống) và một cho bộ đếm (chỗ thiếu nguồn phải ĐẾM ĐƯỢC).
Gộp chúng lại là biến một chỗ VTOS chưa đo được thành một điểm kém của người đi làm.
"""
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_ns5.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_ns5.db"):
    os.remove("test_ns5.db")

import pytest                                        # noqa: E402
from fastapi.testclient import TestClient            # noqa: E402
from sqlalchemy import select                        # noqa: E402

from app.main import app                             # noqa: E402
from app.db.session import SessionLocal, Base        # noqa: E402
from app.models.core import User                     # noqa: E402
from app.models.hr import Employee, Incident         # noqa: E402
from app.models.hrm import AttendanceDay             # noqa: E402
from app.models.nhan_su_danh_gia import (            # noqa: E402
    DanhGiaNhanSu, DeNghiMua, CapPhatTaiSan)
from app.services import danh_gia_ns as DG           # noqa: E402
from app.services import mua_sam_cap_phat as MS      # noqa: E402
from app.services import hrm as HRM                  # noqa: E402

GOC = Path(__file__).resolve().parents[2]
KY = "2027-03"          # kỳ riêng của tệp này, không đụng dữ liệu phép thử khác


@pytest.fixture(scope="module", autouse=True)
def _startup():
    with TestClient(app):
        yield


def _doc(*p) -> str:
    return (GOC.joinpath(*p)).read_text(encoding="utf-8")


def _nguoi(db, phong="dieu_hanh"):
    """Một hồ sơ nhân sự của phòng, và một tài khoản giữ vai ký của phòng ấy.

    KHÔNG lấy hồ sơ của chính người ký: trưởng phòng cũng là một nhân viên của phòng mình, và
    `cham()` cấm tự chấm — lấy nhầm thì phép thử đỏ vì một hàng rào KHÁC, và người đọc sẽ đi sửa
    nhầm chỗ. (Chính chuyện này đã xảy ra lần chạy đầu khi viết tệp này.)
    """
    vai = HRM.nguoi_ky_don(phong)[0]
    sep = db.execute(select(User).where(User.role == vai, User.active.is_(True))).scalars().first()
    nv = db.execute(select(Employee).where(
        Employee.department == phong, Employee.active.is_(True),
        (Employee.user_id.is_(None)) | (Employee.user_id != (sep.id if sep else -1))
    )).scalars().first()
    return nv, sep


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CẤU TRÚC
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_ba_bang_co_that_va_mot_dau_alembic():
    """Ba bảng vào Base.metadata, và cả ba nằm trong CÙNG MỘT migration.

    Vế sau không phải chuyện gọn gàng: bốn làn đang cùng đẩy lên một nhánh chính, hai đầu migration
    mở song song thì alembic có hai head và container KHÔNG khởi động được — đã xảy ra 14/9/2026.
    """
    for t in ("danh_gia_nhan_su", "de_nghi_mua", "cap_phat_tai_san"):
        assert t in Base.metadata.tables, (
            f"bảng {t} không vào Base.metadata — thiếu dòng nhập ở app/models/__init__.py thì "
            "create_all không tạo, và alembic autogenerate sẽ đòi XOÁ nó")
    thu_muc = GOC / "backend" / "alembic" / "versions"
    mang = [p for p in thu_muc.glob("*.py")
            if all(t in p.read_text(encoding="utf-8")
                   for t in ("danh_gia_nhan_su", "de_nghi_mua", "cap_phat_tai_san"))]
    assert len(mang) == 1, f"ba bảng phải nằm trong ĐÚNG MỘT migration, đang thấy: {mang}"

    rev, down = {}, {}
    for p in thu_muc.glob("*.py"):
        s = p.read_text(encoding="utf-8")
        r = re.search(r'^revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        if r:
            rev[r.group(1)] = p.name
            down[r.group(1)] = d.group(1) if d else None
    con = set(down.values())
    dau = [k for k in rev if k not in con]
    assert len(dau) == 1, f"alembic phải có ĐÚNG MỘT đầu, đang có {len(dau)}: {[rev[k] for k in dau]}"


def test_bang_danh_gia_KHONG_co_mot_cot_tien_nao():
    """Chủ tịch chốt điểm chỉ để XÉT. Một cột tiền trong bảng này là chỗ cho công thức mọc ra sau."""
    cot = set(Base.metadata.tables["danh_gia_nhan_su"].columns.keys())
    cam = {c for c in cot if any(t in c for t in ("tien", "thuong", "muc_thuong", "he_so", "luong"))}
    assert not cam, (
        f"bảng đánh giá mọc cột tiền: {sorted(cam)}. Chủ tịch chốt 09/10/2026 điểm CHỈ ĐỂ XÉT, "
        "mức thưởng do TGĐ/Chủ tịch quyết bằng tay. Thêm cột tiền ở đây là một quyết định MỚI, "
        "phải có chữ ký — không phải một lần thêm cột cho tiện.")


def test_khong_mot_duong_nao_bien_diem_thanh_tien():
    """Hàng rào đắt nhất tệp: không mã nguồn nào đọc điểm đánh giá rồi tính ra tiền.

    Không hỏi "hôm nay có công thức không" — hỏi CÁI ĐƯỜNG: tệp nào đụng tiền (lương, thưởng, hoa
    hồng, quyết toán) mà nạp mô-đun đánh giá thì đỏ. Người nối hai thứ ấy phải biết mình đang làm
    điều gì, và phải đi xin một quyết định thứ hai.
    """
    tien = ("hr.py", "rules.py", "settlement.py", "chi_luong.py", "luong_khoa.py", "finance.py")
    dv = GOC / "backend" / "app" / "services"
    pham = []
    for ten in tien:
        p = dv / ten
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        if "danh_gia_ns" in s or "DanhGiaNhanSu" in s:
            pham.append(ten)
    assert not pham, (
        f"tệp đụng tiền đang nạp mô-đun đánh giá: {pham}. Điểm CHỈ ĐỂ XÉT (Chủ tịch 09/10/2026) — "
        "nối nó vào tiền là một quyết định THỨ HAI của Chủ tịch, không phải một lần sửa mã.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.6 — PHÉP TÍNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_ky_sai_dang_bi_chan_ca_ba_loai():
    DG.kiem_ky("thang", "2026-10"); DG.kiem_ky("quy", "2026-Q4"); DG.kiem_ky("nam", "2026")
    for loai, xau in (("thang", "2026-13"), ("thang", "2026"), ("quy", "2026-Q5"),
                      ("quy", "2026-10"), ("nam", "2026-01"), ("thang", "thang 10")):
        with pytest.raises(ValueError):
            DG.kiem_ky(loai, xau)
    with pytest.raises(ValueError):
        DG.kiem_ky("tuan", "2026-W1")


def test_o_chua_co_so_KHONG_keo_diem_xuong():
    """"Chưa có số" khác hẳn 0 điểm — đây là ranh giới của cả bộ tiêu chí.

    Cùng một người, cùng năm ô có điểm; ô thứ sáu để trống thì trung bình phải tính trên NĂM ô.
    Coi ô trống là 0 thì một phòng VTOS chưa đo được sẽ kéo điểm mọi người phòng ấy xuống.
    """
    nam_o = {"a1_diem": None, "a2_diem": 5, "a3_diem": 5, "b1_diem": 4, "b2_diem": 4, "b3_diem": 4}
    diem, hang = DG.tinh_diem_tong(nam_o)
    assert diem == round((5 + 5 + 4 + 4 + 4) / 5, 2) == 4.4, diem
    assert hang == "tot"
    nhu_la_0 = dict(nam_o, a1_diem=0)
    assert DG.tinh_diem_tong(nhu_la_0)[0] < diem, (
        "coi ô trống như 0 thì điểm phải thấp hơn — nếu hai cái bằng nhau thì phép tính đang gộp "
        "hai thứ khác nhau làm một")
    assert DG.tinh_diem_tong({f"{k}_diem": None for k in DG.MOI_O}) == (None, "")


def test_xep_hang_dung_nam_khoang_va_hai_muc_duoi_bat_buoc_ghi_viec():
    moc = {5.0: "xuat_sac", 4.5: "xuat_sac", 4.49: "tot", 3.5: "tot", 3.49: "dat", 2.5: "dat",
           2.49: "can_cai_thien", 1.5: "can_cai_thien", 1.49: "khong_dat", 1.0: "khong_dat"}
    for d, mong in moc.items():
        o = {f"{k}_diem": None for k in DG.MOI_O}
        o["b1_diem"] = d
        assert DG.tinh_diem_tong(o)[1] == mong, f"điểm {d} phải xếp {mong}"
    # Hai mức dưới bắt buộc ghi việc phải sửa
    o = {f"{k}_diem": None for k in DG.MOI_O}
    o.update({"b1_diem": 2, "b2_diem": 2, "b3_diem": 2, "b1_ly_do": "x", "b2_ly_do": "x",
              "b3_ly_do": "x", "viec_phai_sua": ""})
    assert any("việc cụ thể phải sửa" in t for t in DG.thieu_chu(o)), DG.thieu_chu(o)
    o["viec_phai_sua"] = "Giao lại ba hồ sơ visa đúng hạn trong tháng tới"
    assert not DG.thieu_chu(o)


def test_ly_do_bat_buoc_o_hai_dau_thang_diem():
    """Điểm 5 và điểm 1–2 phải có lý do; điểm 3–4 thì không bắt buộc.

    Một bảng toàn điểm 4 không có chữ nào là một bảng không ai đọc lần thứ hai — mà chính những
    bảng ấy mới là bảng đem đi xét thưởng.
    """
    for d, phai_doi in ((5, True), (4, False), (3, False), (2, True), (1, True)):
        o = {f"{k}_diem": None for k in DG.MOI_O}
        o.update({f"{k}_ly_do": "" for k in DG.O_NGUOI})
        o["b1_diem"] = d
        o["viec_phai_sua"] = "có ghi"
        thieu = [t for t in DG.thieu_chu(o) if t.startswith("b1")]
        assert bool(thieu) == phai_doi, f"điểm {d}: {'phải' if phai_doi else 'không được'} đòi lý do"


def test_tuyen_cham_DUNG_LAI_tuyen_ky_don_khong_dung_tuyen_thu_hai():
    """Hỏi CÁI NGUỒN, không hỏi danh sách hôm nay.

    Một phép thử liệt kê mười một cặp phòng–vai thì ngày Chủ tịch đổi người ký, hai bảng lệch nhau
    mà cả hai vẫn xanh. Phép thử này hỏi: với MỌI phòng, tuyến chấm có bằng đúng tuyến ký không.
    """
    for phong in HRM.TUYEN_KY_DON:
        assert DG.vai_duoc_cham(phong) == HRM.nguoi_ky_don(phong), (
            f"phòng {phong}: tuyến chấm lệch tuyến ký. Hai tuyến sẽ lệch nhau ở lần đổi người thứ "
            "nhất, và lúc ấy không ai biết tuyến nào mới là tuyến Chủ tịch ký.")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.6 — CỬA GHI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_ba_o_may_dien_KHONG_nhan_ghi_tu_nguoi_cham():
    """Gửi thẳng a1/a2/a3 lên cửa chấm và đòi chúng KHÔNG đổi.

    Trưởng phòng sửa được ô máy thì cái neo đo độ lệch "điểm người − điểm máy" mất hết nghĩa — và
    cái neo ấy là thứ duy nhất nhìn thấy điểm trôi khi điểm bắt đầu dùng để xét thưởng.
    """
    with SessionLocal() as db:
        nv, sep = _nguoi(db)
        assert nv and sep
        truoc = DG.mo_bang(db, nv.id, "thang", KY)
        DG.cham(db, sep, nv.id, "thang", KY,
                {"b1_diem": 4, "b2_diem": 4, "b3_diem": 4,
                 "a1_diem": 5, "a2_diem": 5, "a3_diem": 5})
        r = db.execute(select(DanhGiaNhanSu).where(
            DanhGiaNhanSu.employee_id == nv.id, DanhGiaNhanSu.ky == KY)).scalars().first()
        for k in DG.O_MAY:
            assert getattr(r, f"{k}_diem") == truoc[f"{k}_diem"], (
                f"ô {k} đổi được từ cửa chấm — ba ô máy điền phải KHÔNG có cửa ghi")
        db.rollback()


def test_cham_sai_vai_bi_tu_choi_va_khong_tu_cham_ban_cua_minh():
    with SessionLocal() as db:
        nv, sep = _nguoi(db)
        sai = db.execute(select(User).where(User.role == "nv_kd",
                                            User.active.is_(True))).scalars().first()
        assert sai, "bản demo không có tài khoản nv_kd để dựng cảnh"
        with pytest.raises(PermissionError):
            DG.cham(db, sai, nv.id, "thang", KY, {"b1_diem": 4})
        # Người chấm tự chấm bản của chính mình
        nv_cua_sep = db.execute(select(Employee).where(Employee.user_id == sep.id)).scalars().first()
        if nv_cua_sep is not None:
            with pytest.raises(PermissionError):
                DG.cham(db, sep, nv_cua_sep.id, "thang", KY, {"b1_diem": 5})
        db.rollback()


def test_khong_gui_duoc_khi_con_thieu_chu_hoac_thieu_diem():
    with SessionLocal() as db:
        nv, sep = _nguoi(db)
        DG.cham(db, sep, nv.id, "thang", KY, {"b1_diem": 5, "b1_ly_do": ""})
        r = db.execute(select(DanhGiaNhanSu).where(
            DanhGiaNhanSu.employee_id == nv.id, DanhGiaNhanSu.ky == KY)).scalars().first()
        with pytest.raises(ValueError) as e:
            DG.gui(db, sep, r.id)
        assert "thiếu" in str(e.value).lower()
        # Ghi lý do nhưng còn trống hai ô điểm
        DG.cham(db, sep, nv.id, "thang", KY, {"b1_diem": 5, "b1_ly_do": "vượt mong đợi ba việc"})
        with pytest.raises(ValueError):
            DG.gui(db, sep, r.id)
        DG.cham(db, sep, nv.id, "thang", KY, {"b2_diem": 4, "b3_diem": 4})
        DG.gui(db, sep, r.id)
        assert r.trang_thai == "da_gui" and r.gui_luc is not None
        with pytest.raises(ValueError):
            DG.cham(db, sep, nv.id, "thang", KY, {"b1_diem": 3})
        db.rollback()


def test_quy_tong_hop_tu_thang_va_NOI_RA_thieu_thang_nao():
    """Thiếu kỳ con thì nói ra kỳ nào — không lấy hai tháng chia ba rồi im lặng.

    Một trung bình thiếu nguồn trông y hệt một trung bình đủ nguồn khi đã nằm trong cột, và nó sẽ
    được đem đi xét thưởng như nhau.
    """
    with SessionLocal() as db:
        nv, sep = _nguoi(db)
        for thang, diem in (("2027-01", 4), ("2027-02", 2)):
            DG.cham(db, sep, nv.id, "thang", thang,
                    {"b1_diem": diem, "b2_diem": diem, "b3_diem": diem,
                     "b1_ly_do": "lý do", "b2_ly_do": "lý do", "b3_ly_do": "lý do",
                     "viec_phai_sua": "việc phải sửa"})
        q = DG.mo_bang(db, nv.id, "quy", "2027-Q1")
        assert "2027-03" in (q["thieu_ky_con"] or ""), (
            f"quý thiếu tháng 3 mà không nói ra: {q['thieu_ky_con']!r}")
        assert "2027-01" not in (q["thieu_ky_con"] or "")
        assert q["b1_diem"] == 3, f"trung bình 4 và 2 phải ra 3, nhận {q['b1_diem']}"
        db.rollback()


def test_do_lech_nguoi_may_nhin_thay_nguoi_cham_cao_hon_so_may():
    """Dựng một cảnh có thật rồi hỏi BỘ ĐO, không hỏi con số hôm nay."""
    with SessionLocal() as db:
        nv, sep = _nguoi(db)
        r = db.execute(select(DanhGiaNhanSu).where(
            DanhGiaNhanSu.employee_id == nv.id, DanhGiaNhanSu.ky == KY)).scalars().first()
        if r is None:
            DG.mo_bang(db, nv.id, "thang", KY)
            r = db.execute(select(DanhGiaNhanSu).where(
                DanhGiaNhanSu.employee_id == nv.id, DanhGiaNhanSu.ky == KY)).scalars().first()
        r.a1_diem, r.a2_diem, r.a3_diem = 2, 2, 2
        r.b1_diem = r.b2_diem = r.b3_diem = 5
        r.nguoi_cham, r.vai_nguoi_cham = "nguoi_cham_thu", sep.role
        db.flush()
        bao = DG.do_lech_nguoi_may(db, "thang", KY)
        g = bao["theo_nguoi_cham"]["nguoi_cham_thu"]
        assert g["lech_tb"] == 3.0, f"chấm tay 5 trên số máy 2 phải ra lệch +3, nhận {g['lech_tb']}"
        r.b1_diem = r.b2_diem = r.b3_diem = 2
        db.flush()
        assert DG.do_lech_nguoi_may(db, "thang", KY)["theo_nguoi_cham"]["nguoi_cham_thu"]["lech_tb"] == 0.0
        db.rollback()


def test_bo_dem_thieu_nguon_that_su_nhin_thay_cho_ho():
    """Hỏi bộ đếm, không hỏi con số: thêm một phòng chưa có nguồn A1 thì nó phải đếm thêm."""
    with SessionLocal() as db:
        bao = DG.thieu_nguon(db, KY)
        assert bao["so_nguoi"] > 0
        assert bao["tong_thieu"]["a1"] > 0, (
            "bản demo có phòng chưa khai nguồn chỉ tiêu mà bộ đếm báo 0 — bộ đếm đang mù")
        ly_do = " ".join(bao["theo_o"]["a1"].keys())
        assert "chưa có số" in ly_do, "mỗi chỗ thiếu phải nói RA LÝ DO, không chỉ đếm số"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.9.2 — HAI CHỮ KÝ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _vai(db, ten):
    return db.execute(select(User).where(User.role == ten,
                                         User.active.is_(True))).scalars().first()


def test_ke_toan_KHONG_ghi_chi_duoc_khi_chua_ai_duyet():
    """Hai chữ ký của hai người. Chi trước khi có người duyệt là đúng cái vòng này sinh ra để chặn."""
    with SessionLocal() as db:
        ai_cung_duoc = _vai(db, "nv_dh") or _vai(db, "hcns")
        tgd, ketoan = _vai(db, "tgd"), _vai(db, "ketoan")
        assert ai_cung_duoc and tgd and ketoan
        r = MS.tao_de_nghi(db, ai_cung_duoc, "Máy in phòng Điều hành", 1, "cái", 4_500_000,
                           "máy cũ hỏng trống giấy")
        with pytest.raises(ValueError) as e:
            MS.ghi_da_chi(db, ketoan, r["id"], 4_500_000)
        assert "ĐÃ DUYỆT" in str(e.value)
        with pytest.raises(PermissionError):
            MS.duyet(db, ketoan, r["id"], True)          # Kế toán không duyệt thay TGĐ
        MS.duyet(db, tgd, r["id"], True)
        with pytest.raises(PermissionError):
            MS.ghi_da_chi(db, tgd, r["id"], 4_500_000)   # TGĐ không ghi chi thay Kế toán
        sau = MS.ghi_da_chi(db, ketoan, r["id"], 4_900_000, "PC2026-0012")
        assert sau["trang_thai"] == "da_chi"
        assert sau["uoc_tinh"] == 4_500_000 and sau["so_tien_chi"] == 4_900_000, (
            "hai cột tiền phải giữ CẢ HAI số — gộp một cột thì lần chi đầu tiên xoá mất con số "
            "đã được duyệt, và không ai đối chiếu được duyệt bao nhiêu / chi bao nhiêu")
        assert sau["lech_chi_so_voi_uoc"] == 400_000
        db.rollback()


def test_khong_duyet_thi_bat_buoc_ghi_ly_do():
    with SessionLocal() as db:
        ai = _vai(db, "nv_dh") or _vai(db, "hcns")
        tgd = _vai(db, "tgd")
        r = MS.tao_de_nghi(db, ai, "Ghế xoay", 2, "cái", 1_200_000)
        with pytest.raises(ValueError) as e:
            MS.duyet(db, tgd, r["id"], False, "")
        assert "lý do" in str(e.value)
        sau = MS.duyet(db, tgd, r["id"], False, "Quý này không mua đồ nội thất")
        assert sau["trang_thai"] == "tu_choi" and sau["duyet_ghi_chu"]
        db.rollback()


def test_gia_uoc_tinh_de_trong_duoc():
    """Chưa hỏi giá thì cứ gửi. Bắt điền thì người ta bịa, và con số bịa đi thẳng vào bảng chi phí."""
    with SessionLocal() as db:
        ai = _vai(db, "nv_dh") or _vai(db, "hcns")
        r = MS.tao_de_nghi(db, ai, "Một bộ đàm cho đội xe", uoc_tinh=None)
        assert r["uoc_tinh"] is None and r["trang_thai"] == "cho_duyet"
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5.9.3 — CẤP PHÁT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_chi_hcns_cap_phat_va_mon_phai_co_ten_khi_khong_co_the_tscd():
    with SessionLocal() as db:
        hcns, tgd = _vai(db, "hcns"), _vai(db, "tgd")
        nv = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().first()
        assert hcns and tgd and nv
        with pytest.raises(PermissionError):
            MS.cap_phat(db, tgd, nv.id, date(2026, 10, 9), "Điện thoại")
        with pytest.raises(ValueError) as e:
            MS.cap_phat(db, hcns, nv.id, date(2026, 10, 9), "")
        assert "tên món" in str(e.value)
        r = MS.cap_phat(db, hcns, nv.id, date(2026, 10, 9), "SIM data 4G", so_luong=1,
                        muc_dich="đi tour miền Trung", tinh_trang_khi_cap="mới")
        assert r["trang_thai"] == "dang_giu" and r["asset_id"] is None, (
            "món không đủ nguyên giá để thành thẻ TSCĐ vẫn phải ghi được — bắt có thẻ trước thì "
            "HCNS ghi ra giấy và sổ máy rỗng trong khi đồ vẫn đi")
        dang = MS.dang_giu_cua_nguoi(db, nv.id)
        assert any(x["id"] == r["id"] for x in dang)
        with pytest.raises(ValueError) as e:
            MS.ghi_tra(db, hcns, r["id"], date(2026, 11, 1), "")
        assert "tình trạng" in str(e.value)
        MS.ghi_tra(db, hcns, r["id"], date(2026, 11, 1), "còn dùng được")
        assert not [x for x in MS.dang_giu_cua_nguoi(db, nv.id) if x["id"] == r["id"]], (
            "ghi trả rồi mà vẫn nằm trong danh sách đang giữ")
        db.rollback()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# MÀN HÌNH — CỬA MỞ MÀ NGƯỜI KHÔNG VỚI TỚI THÌ CỬA ẤY CHƯA TỒN TẠI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def test_ba_muc_tren_cay_khong_con_khai_la_CHUA_CO():
    cay = _doc("web", "lib", "cay_phan_he.ts")
    for ma in ('"5.6"', '"5.9.2"', '"5.9.3"'):
        dong = next(d for d in cay.splitlines() if d.strip().startswith(f"{{ ma: {ma}"))
        assert "chưa" not in dong, f"mục {ma} đã dựng thật mà cây vẫn khai là chưa có: {dong.strip()}"


def test_ma_tren_cay_khong_trung_nhau():
    """Hai mục cùng một mã thì mọi thứ tra theo mã chỉ thấy một trong hai, và không ai biết nó bỏ
    qua cái nào. Mục 5.9.2 từng trùng giữa IR – Pháp chế và Mua sắm; sửa 09/10/2026."""
    cay = _doc("web", "lib", "cay_phan_he.ts")
    # Đếm TRONG TỪNG PHÂN HỆ, không đếm cả tệp. Một nhánh CỐ Ý hiện ở nhiều phân hệ — mục 3.5 Chăm
    # sóc khách hàng đứng ở cả Marketing (cờ `chuyen`) lẫn Kinh doanh — và đó là thiết kế, không
    # phải lỗi. Lỗi là HAI MỤC KHÁC NHAU mang CÙNG một mã trong CÙNG một phân hệ: lúc ấy mọi thứ
    # tra theo mã chỉ thấy một trong hai và không ai biết nó bỏ qua cái nào.
    khoi = re.split(r'\{\s*khoa:\s*"', cay)[1:]
    loi = {}
    for k in khoi:
        ten = k.split('"', 1)[0]
        ma = re.findall(r'\{\s*ma:\s*"([0-9.]+)"', k)
        trung = sorted({m for m in ma if ma.count(m) > 1})
        if trung:
            loi[ten] = trung
    assert not loi, f"mã trùng trong cùng một phân hệ: {loi}"


def test_moi_cua_moi_deu_co_man_hinh_that_va_duong_vao_menu():
    assert (GOC / "web" / "app" / "de-nghi-mua" / "page.tsx").exists(), \
        "cây trỏ tới /de-nghi-mua mà không có trang"
    shell = _doc("web", "components", "Shell.tsx")
    assert '"/de-nghi-mua"' in shell, "màn hình mới không có lối vào menu"
    # Hỏi CHỖ DỰNG, không hỏi cái tên. Bản đầu của phép thử này chỉ hỏi `"DanhGiaCuaToi" in cc`,
    # và kiểm ngược bắt được: xoá dòng dựng mà GIỮ dòng nhập thì nó vẫn xanh — màn hình không có
    # khối nào mà hàng rào vẫn bảo có. Một hàng rào đọc tên mô-đun chỉ chứng minh người ta đã gõ
    # tên ấy một lần.
    cc = _doc("web", "app", "cham-cong", "page.tsx")
    assert "<DanhGiaCuaToi />" in cc, (
        "Chủ tịch chốt 08/10 nhân viên được thấy bản của mình; khối ấy phải DỰNG ở màn hình đã mở "
        "cho mọi người, không phải ở /hr vốn chỉ mở cho sáu vai")
    hr = _doc("web", "components", "HrScreens.tsx")
    assert "<BangChamDiem />" in hr, "thẻ Đánh giá & sự vụ chưa dựng bảng chấm"
    ts = _doc("web", "app", "tai-san", "page.tsx")
    assert "<CapPhatTaiSan />" in ts, "màn hình Tài sản chưa dựng khối cấp phát"
