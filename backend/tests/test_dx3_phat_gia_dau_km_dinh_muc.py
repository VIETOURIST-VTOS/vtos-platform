# -*- coding: utf-8 -*-
"""DX-3 · Phạt tài xế, giá dầu theo ngày, và km định mức của danh mục tour.

Ba việc cuối của danh sách BẢY việc lập trình đội xe (chốt 11/10/2026). Chủ tịch duyệt 16/10/2026.

LUẬT QUAN TRỌNG NHẤT, và là lý do tệp này tồn tại hơn là chỉ đo ba cái bảng:

  **PHẠT ĐI VÀO LƯƠNG, KHÔNG ĐI VÀO GIÁ VỐN XE.** Khoản phạt là tiền của NGƯỜI LÁI; chiếc xe
  không làm gì sai. Cộng vào chi phí xe thì lãi lỗ từng xe sai, và tệ hơn: công ty thu lại tiền
  phạt nhưng sổ vẫn ghi xe đã tiêu khoản ấy — tính hai lần theo hai chiều ngược nhau.

Hai luật còn lại:
  · GIÁ DẦU KHÔNG ĐOÁN. Thiếu giá đúng ngày thì nói ra, không lấy giá gần nhất — giá đổi mười
    ngày một lần, lấy giá cách ba tuần ra số lít sai mà trông vẫn hợp lý.
  · KM ĐỊNH MỨC RỖNG NGHĨA LÀ CHƯA AI KHAI, không phải 0 km.
"""
import os
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Product  # noqa: E402
from app.models.fleet import GiaDauNgay, PhatTaiXe  # noqa: E402
from app.models.hr import Employee  # noqa: E402
from app.services import phat_va_gia_dau as PG  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _tx(db, ten="Lý Văn Sơn", ma="TX1", phong="doi_xe"):
    e = Employee(code=ma, full_name=ten, department=phong)
    db.add(e); db.flush()
    return e


# ═══════════════ LUẬT LỚN · phạt vào lương, không vào giá vốn xe
def test_phat_KHONG_co_duong_nao_chay_vao_chi_phi_xe():
    """Đọc bằng CÂY CÚ PHÁP, không tìm chuỗi trong cả tệp.

    Tìm chuỗi thì chính đoạn chú thích giải thích «vì sao KHÔNG chạm hai bảng ấy» làm phép thử
    đỏ — và cách chữa dễ nhất lúc ấy là xoá lời giải thích đi, tức phép thử dạy người ta gỡ bỏ
    đúng thứ đáng giữ nhất. Cây cú pháp chỉ nhìn mã THẬT SỰ CHẠY.
    """
    import ast
    import inspect
    cay = ast.parse(inspect.getsource(PG))
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    ten |= {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}
    ten |= {a.name for n in ast.walk(cay) if isinstance(n, (ast.Import, ast.ImportFrom))
            for a in n.names}
    for bang in ("FleetPeriodCost", "TripCost", "Maintenance"):
        assert bang not in ten, f"dịch vụ phạt đang chạm {bang} – phạt sẽ lọt vào giá vốn xe"


def test_phat_co_cua_tra_ve_so_tru_LUONG_tung_nguoi(db):
    n1, n2 = _tx(db), _tx(db, "Nguyễn Văn Bền", "TX2")
    PG.ghi_phat(db, n1.id, "2026-10", date(2026, 10, 3), 500_000, "đi muộn", "gddx")
    PG.ghi_phat(db, n1.id, "2026-10", date(2026, 10, 9), 300_000, "không mặc đồng phục", "gddx")
    PG.ghi_phat(db, n2.id, "2026-10", date(2026, 10, 5), 200_000, "quên ký lệnh", "gddx")
    PG.ghi_phat(db, n1.id, "2026-11", date(2026, 11, 2), 999_000, "kỳ sau", "gddx")
    tru = PG.tru_luong_ky(db, "2026-10")
    assert tru == {n1.id: 800_000, n2.id: 200_000}, "kỳ sau không được lẫn vào kỳ này"


def test_so_phat_noi_ro_khoan_nay_khong_vao_chi_phi_xe(db):
    n = _tx(db)
    PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), 500_000, "đi muộn", "gddx")
    assert "Không cộng vào chi phí của chiếc xe" in PG.so_phat(db)["ghi_chu"]


# ═══════════════ Phạt · luật ghi
def test_ly_do_bat_buoc(db):
    n = _tx(db)
    with pytest.raises(PG.KhongGhiDuoc) as e:
        PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), 500_000, "   ", "gddx")
    assert "lý do" in str(e.value)


def test_so_tien_phai_lon_hon_khong(db):
    n = _tx(db)
    for xau in (0, -1):
        with pytest.raises(PG.KhongGhiDuoc):
            PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), xau, "đi muộn", "gddx")


def test_nguoi_ngoai_doi_xe_khong_bi_ghi_phat_o_day(db):
    ke_toan = _tx(db, "Kế toán viên", "KT1", "ke_toan")
    with pytest.raises(PG.KhongGhiDuoc) as e:
        PG.ghi_phat(db, ke_toan.id, "2026-10", date(2026, 10, 3), 500_000, "đi muộn", "gddx")
    assert "không thuộc đội xe" in str(e.value)


@pytest.mark.parametrize("ky", ["2026-13", "10-2026", "2026", "", "thang muoi"])
def test_ky_luong_sai_dang_bi_chan(db, ky):
    """`ky` KHÔNG suy từ `ngay`: một lỗi ngày 29 có thể chốt vào kỳ sau nếu kỳ này đã khoá, và
    suy hộ là trừ nhầm tháng của một con người."""
    n = _tx(db)
    with pytest.raises(PG.KhongGhiDuoc):
        PG.ghi_phat(db, n.id, ky, date(2026, 10, 29), 500_000, "đi muộn", "gddx")


def test_ky_khong_suy_tu_ngay(db):
    n = _tx(db)
    p = PG.ghi_phat(db, n.id, "2026-11", date(2026, 10, 29), 500_000, "kỳ này đã khoá", "gddx")
    assert p.ky == "2026-11" and p.ngay == date(2026, 10, 29)


def test_khong_bat_buoc_gan_chuyen(db):
    """Không phải lỗi nào cũng gắn vào một chuyến. Bắt gắn là bắt người ghi chọn đại một chuyến."""
    n = _tx(db)
    p = PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), 500_000, "không mặc đồng phục", "gddx")
    assert p.trip_id is None and p.vehicle_id is None


# ═══════════════ Phạt · HCNS đối chiếu
def test_doi_chieu_danh_dau_nguoi_thu_hai_da_nhin(db):
    n = _tx(db)
    p = PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), 500_000, "đi muộn", "gddx")
    assert PG.so_phat(db)["chua_doi_chieu"] == 1
    PG.hcns_doi_chieu(db, p, "hcns1")
    assert p.hcns_doi_chieu_boi == "hcns1" and p.hcns_doi_chieu_luc is not None
    assert PG.so_phat(db)["chua_doi_chieu"] == 0


def test_khong_doi_chieu_hai_lan(db):
    n = _tx(db)
    p = PG.ghi_phat(db, n.id, "2026-10", date(2026, 10, 3), 500_000, "đi muộn", "gddx")
    PG.hcns_doi_chieu(db, p, "hcns1")
    with pytest.raises(PG.KhongGhiDuoc):
        PG.hcns_doi_chieu(db, p, "hcns2")


def test_nguoi_GHI_va_nguoi_DOI_CHIEU_la_hai_vai_khac_nhau():
    """Cùng một người vừa ghi vừa đánh dấu đã đối chiếu thì dấu ấy không nói thêm được gì."""
    from app.api.v1 import fleet as F
    assert set(F.GHI_PHAT) & set(F.DOI_CHIEU_PHAT) == {"cntt"}, \
        "ngoài CNTT, hai vai phải rời nhau"
    assert "gd_doi_xe" in F.GHI_PHAT and "gd_doi_xe" not in F.DOI_CHIEU_PHAT
    assert "hcns" in F.DOI_CHIEU_PHAT and "hcns" not in F.GHI_PHAT


def test_vai_ghi_phat_HEP_hon_vai_ghi_chung_cua_doi_xe():
    """Để nguyên WRITE thì Điều hành cũng trừ được lương tài xế — quyền chưa ai trao."""
    from app.api.v1 import fleet as F
    assert set(F.GHI_PHAT) < set(F.WRITE) | {"cntt"}
    assert "nv_dh" not in F.GHI_PHAT and "tp_dh" not in F.GHI_PHAT


# ═══════════════ Giá dầu
def test_quy_tien_ra_lit(db):
    PG.ghi_gia(db, date(2026, 10, 3), "do", 20_000, "Petrolimex", "ketoan")
    ra = PG.lit_tu_tien(db, date(2026, 10, 3), 1_800_000)
    assert ra["lit"] == 90.0 and ra["gia_lit"] == 20_000 and not ra["vi_sao"]


def test_THIEU_gia_dung_ngay_thi_NOI_RA_chu_khong_lay_gia_gan_nhat(db):
    """Giá đổi mười ngày một lần. Lấy giá cách ba tuần ra số lít sai mà trông vẫn hợp lý — và một
    con số sai trông hợp lý thì không ai đi kiểm lại."""
    PG.ghi_gia(db, date(2026, 9, 10), "do", 20_000, "Petrolimex", "ketoan")
    ra = PG.lit_tu_tien(db, date(2026, 10, 3), 1_800_000)
    assert ra["lit"] is None
    assert "Chưa khai giá" in ra["vi_sao"] and "2026-10-03" in ra["vi_sao"]


def test_dau_va_xang_la_hai_gia_khac_nhau(db):
    PG.ghi_gia(db, date(2026, 10, 3), "do", 20_000, "", "ketoan")
    PG.ghi_gia(db, date(2026, 10, 3), "xang", 24_000, "", "ketoan")
    assert PG.gia_ngay(db, date(2026, 10, 3), "do") == 20_000
    assert PG.gia_ngay(db, date(2026, 10, 3), "xang") == 24_000


def test_khai_lai_cung_ngay_thi_DE_chu_khong_them_dong_thu_hai(db):
    """Hai dòng cùng ngày cùng loại thì phép quy lít ra hai kết quả tuỳ dòng nào đọc trước."""
    from sqlalchemy import func, select
    PG.ghi_gia(db, date(2026, 10, 3), "do", 20_000, "ước", "ketoan")
    PG.ghi_gia(db, date(2026, 10, 3), "do", 21_500, "hoá đơn", "ketoan")
    assert db.execute(select(func.count()).select_from(GiaDauNgay)).scalar() == 1
    assert PG.gia_ngay(db, date(2026, 10, 3)) == 21_500


def test_loai_nhien_lieu_ngoai_danh_muc_bi_chan(db):
    with pytest.raises(PG.KhongGhiDuoc):
        PG.ghi_gia(db, date(2026, 10, 3), "dau_hoa", 20_000, "", "ketoan")


def test_gia_phai_lon_hon_khong(db):
    with pytest.raises(PG.KhongGhiDuoc):
        PG.ghi_gia(db, date(2026, 10, 3), "do", 0, "", "ketoan")


def test_dong_chua_co_tien_thi_khong_quy_duoc_va_noi_ro(db):
    PG.ghi_gia(db, date(2026, 10, 3), "do", 20_000, "", "ketoan")
    assert PG.lit_tu_tien(db, date(2026, 10, 3), 0)["lit"] is None


def test_dem_duoc_nhung_ngay_con_thieu_gia(db):
    """Đếm được thì mới sửa được."""
    PG.ghi_gia(db, date(2026, 10, 3), "do", 20_000, "", "ketoan")
    thieu = PG.ngay_thieu_gia(db, [date(2026, 10, 3), date(2026, 10, 4), date(2026, 10, 5)])
    assert thieu == ["2026-10-04", "2026-10-05"]


# ═══════════════ Km định mức
def test_km_dinh_muc_nam_tren_DANH_MUC_TOUR(db):
    """Một tuyến có quãng đường cố định. Khai theo từng chuyến là bắt người điều hành gõ lại cùng
    một con số mỗi lần mở tour — và gõ lại thì lệch."""
    p = Product(code="DL3N2D", name="Đà Lạt 3N2Đ", km_dinh_muc=640)
    db.add(p); db.flush()
    assert db.get(Product, p.id).km_dinh_muc == 640


def test_km_dinh_muc_RONG_nghia_la_chua_ai_khai_khong_phai_0(db):
    """Đặt 0 thì mọi chuyến của tuyến ấy đều «vượt định mức», và một cảnh báo luôn bật là một
    cảnh báo không ai đọc."""
    p = Product(code="PT2N1D", name="Phan Thiết 2N1Đ")
    db.add(p); db.flush()
    assert db.get(Product, p.id).km_dinh_muc is None


def test_mach_migration_van_chi_co_MOT_dau():
    import pathlib
    import re
    goc = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    rev, cha = {}, set()
    for f in goc.glob("*.py"):
        s = f.read_text(encoding="utf-8", errors="replace")
        r = re.search(r'^revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        d = re.search(r'^down_revision\s*(?::.*?)?=\s*["\']([^"\']+)', s, re.M)
        if r:
            rev[r.group(1)] = f.name
        if d:
            cha.add(d.group(1))
    dau = [k for k in rev if k not in cha]
    assert len(dau) == 1, f"alembic phải có ĐÚNG MỘT đầu: {[rev[k] for k in dau]}"
