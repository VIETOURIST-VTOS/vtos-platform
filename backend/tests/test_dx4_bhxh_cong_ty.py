# -*- coding: utf-8 -*-
"""DX-4 · BHXH phần công ty đóng — máy tính để ĐỐI CHIẾU, không để ghi hộ.

MỘT ĐIỀU PHẢI NÓI TRƯỚC, vì nó đổi hẳn phạm vi việc này. Bản rà 11/10 ghi «rules.py chỉ có
bhxh_nld». Đúng — nhưng đo lại 16/10 thì phía ĐỘI XE đã có cửa nhập: `NHOM_CHI_PHI_KY` có sẵn
nhóm `bhxh`. Cái thiếu không phải một cửa nhập, mà là một PHÉP ĐỐI CHIẾU: con số nhập tay không
có gì soi lại, gõ nhầm một chữ số thì giá vốn đội xe lệch mà không ai biết.

BA LUẬT:
  1. RỖNG THÌ NÓI CHƯA CHỐT, KHÔNG COI LÀ 0 — coi rỗng là 0 thì màn hình hiện một khoảng lệch
     do chính hệ thống bịa ra, và người đọc đi tìm lỗi ở chỗ không có lỗi.
  2. MÁY KHÔNG TỰ GHI VÀO SỔ — ranh giới Chủ tịch đặt 09/9/2026.
  3. CĂN CỨ LÀ MỨC ĐÓNG BHXH, KHÔNG PHẢI LƯƠNG HỢP ĐỒNG — bảng tháng 8/2026 ghi mức tham gia
     5.310.000 trong khi lương hợp đồng nhiều người 15–20 triệu.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Param  # noqa: E402
from app.models.fleet import FleetPeriodCost  # noqa: E402
from app.models.hr import PayrollRun  # noqa: E402
from app.services import bhxh_cong_ty as BH  # noqa: E402
from app.services import rules as R  # noqa: E402

KY = "2026-08"


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)
    R.clear_param_cache()


def _ty_le(db, gia_tri):
    db.add(Param(key="bhxh_cty", value=gia_tri, label="bhxh_cty", unit="",
                 effective_from=date.today(), source="test", status="active",
                 signed_chutich=True, signed_tgd=True, proposed_by="test"))
    db.commit()
    R.clear_param_cache()


def _bang_luong(db, dong, trang_thai="tgd_duyet"):
    db.add(PayrollRun(period=KY, status=trang_thai, rows=dong))
    db.flush()


def _ba_tai_xe():
    return [
        {"ma": "TX1", "ten": "Lý Văn Sơn", "phong": "doi_xe", "bhxh_base": 5_310_000},
        {"ma": "TX2", "ten": "Nguyễn Văn Bền", "phong": "doi_xe", "bhxh_base": 5_310_000},
        {"ma": "KD1", "ten": "Nhân viên KD", "phong": "kinh_doanh", "bhxh_base": 9_000_000},
    ]


# ═══════════════ LUẬT 1 · rỗng là CHƯA CHỐT, không phải 0
def test_tham_so_khai_RONG_trong_bo_mac_dinh():
    """Điền sẵn một tỷ lệ vào bộ mặc định là ký thay Chủ tịch bằng một dòng mã."""
    import re
    src = open(R.__file__, encoding="utf-8").read()
    m = re.search(r'\("bhxh_cty",\s*"([^"]*)"', src)
    assert m, "chưa khai tham số bhxh_cty"
    assert m.group(1) == "", "tham số này PHẢI để trống tới khi có chữ ký"


def test_chua_ky_thi_ty_le_la_None_chu_khong_phai_0(db):
    assert BH.ty_le(db) is None


def test_chua_ky_thi_KHONG_tinh_va_noi_ro_phai_ky_o_dau(db):
    _bang_luong(db, _ba_tai_xe())
    ra = BH.may_tinh(db, KY)
    assert ra["tinh_duoc"] is False and ra["so_tien"] is None
    assert "Chưa chốt tỷ lệ" in ra["vi_sao"] and "bhxh_cty" in ra["vi_sao"]


def test_chua_ky_thi_KHONG_bia_ra_mot_khoang_lech(db):
    """Coi rỗng là 0 thì màn hình hiện «máy 0 đ, sổ 180 triệu, lệch 180 triệu» — một khoảng lệch
    do chính hệ thống bịa ra, và người đọc đi tìm lỗi ở chỗ không có lỗi."""
    _bang_luong(db, _ba_tai_xe())
    db.add(FleetPeriodCost(ky=KY, pham_vi="doi", nhom="bhxh", mo_ta="BHXH T8", so_tien=2_283_300))
    db.flush()
    ra = BH.doi_chieu(db, KY)
    assert ra["lech"] is None and ra["khop"] is None
    assert ra["da_nhap_tay"]["so_tien"] == 2_283_300


def test_ty_le_so_am_hoac_khong_phai_so_cung_coi_la_chua_chot(db):
    for xau in ("0", "-0.2", "hai muoi mot phay nam", "  "):
        db.query(Param).delete(); db.commit()
        _ty_le(db, xau)
        assert BH.ty_le(db) is None, f"giá trị {xau!r} phải bị coi là chưa chốt"


# ═══════════════ LUẬT 3 · căn cứ là MỨC ĐÓNG, không phải lương hợp đồng
def test_tinh_tren_muc_dong_cua_RIENG_doi_xe(db):
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    ra = BH.may_tinh(db, KY)
    assert ra["tinh_duoc"] is True
    assert ra["so_nguoi"] == 2, "nhân viên kinh doanh không thuộc đội xe"
    assert ra["nen_dong"] == 10_620_000
    assert ra["so_tien"] == round(10_620_000 * 0.215)


def test_nguoi_chua_co_muc_dong_duoc_dem_RIENG_chu_khong_bo_im(db):
    """Thiếu dữ liệu không phải là dữ liệu bằng 0 — cùng câu đã viết ở bộ tính lương."""
    _ty_le(db, "0.215")
    dong = _ba_tai_xe()
    dong.append({"ma": "TX3", "ten": "Phạm Văn Tới", "phong": "doi_xe", "bhxh_base": 0})
    _bang_luong(db, dong)
    ra = BH.may_tinh(db, KY)
    assert ra["so_nguoi"] == 2 and ra["so_nguoi_chua_co_muc_dong"] == 1


def test_chua_co_bang_luong_thi_noi_ro(db):
    _ty_le(db, "0.215")
    ra = BH.may_tinh(db, "2026-09")
    assert ra["tinh_duoc"] is False and "Chưa có bảng lương" in ra["vi_sao"]


# ═══════════════ Đối chiếu
def test_hai_so_khop_thi_bao_khop(db):
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    db.add(FleetPeriodCost(ky=KY, pham_vi="doi", nhom="bhxh", mo_ta="BHXH T8",
                           so_tien=round(10_620_000 * 0.215)))
    db.flush()
    ra = BH.doi_chieu(db, KY)
    assert ra["lech"] == 0 and ra["khop"] is True


def test_lech_thi_noi_ra_bao_nhieu(db):
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    db.add(FleetPeriodCost(ky=KY, pham_vi="doi", nhom="bhxh", mo_ta="BHXH T8", so_tien=2_000_000))
    db.flush()
    ra = BH.doi_chieu(db, KY)
    assert ra["khop"] is False
    assert ra["lech"] == round(10_620_000 * 0.215) - 2_000_000


def test_nhieu_dong_bhxh_trong_mot_ky_thi_CONG_lai(db):
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    for t in (1_000_000, 1_283_300):
        db.add(FleetPeriodCost(ky=KY, pham_vi="doi", nhom="bhxh", mo_ta="BHXH T8", so_tien=t))
    db.flush()
    assert BH.da_nhap_tay(db, KY) == {"so_tien": 2_283_300, "so_dong": 2}


def test_nhom_chi_phi_khac_khong_bi_dem_nham(db):
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    db.add(FleetPeriodCost(ky=KY, pham_vi="doi", nhom="bai_xe", mo_ta="Phí bãi", so_tien=9_000_000))
    db.flush()
    assert BH.da_nhap_tay(db, KY)["so_tien"] == 0


# ═══════════════ LUẬT 2 · máy không tự ghi vào sổ
def test_doi_chieu_KHONG_ghi_them_dong_nao(db):
    """Ranh giới Chủ tịch đặt 09/9/2026: hệ thống viết phép tính, người nhập số liệu."""
    from sqlalchemy import func, select
    _ty_le(db, "0.215")
    _bang_luong(db, _ba_tai_xe())
    truoc = db.execute(select(func.count()).select_from(FleetPeriodCost)).scalar()
    BH.doi_chieu(db, KY)
    assert db.execute(select(func.count()).select_from(FleetPeriodCost)).scalar() == truoc


def test_dich_vu_KHONG_co_duong_nao_GHI_vao_chi_phi_ky():
    """Đọc bằng cây cú pháp: không một lời gọi `db.add` hay `FleetPeriodCost(` nào."""
    import ast
    import inspect
    cay = ast.parse(inspect.getsource(BH))
    goi = {n.func.attr for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert "add" not in goi and "commit" not in goi, "dịch vụ đối chiếu đang ghi vào cơ sở dữ liệu"
    tao = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "FleetPeriodCost" not in tao


def test_cua_doc_bat_buoc_chon_ky():
    import inspect
    from app.api.v1 import fleet as F
    src = inspect.getsource(F.bhxh_doi_xe)
    assert "422" in src and "YYYY-MM" in src
