# -*- coding: utf-8 -*-
"""XE-1 · Xoá một dòng xe tạo nhầm — và chỉ dòng tạo nhầm.

VÌ SAO CÓ CỬA NÀY. Danh mục xe dựng trên nguyên tắc «mã xe theo chiếc xe suốt vòng đời»: xe bán đi
thì ghi vòng đời và ngày rời đội, KHÔNG xoá, vì lịch sử chuyến và chi phí phải ở lại. Nên tới
14/10/2026 phân hệ xe có cửa sửa, cửa đổi biển, và KHÔNG có cửa xoá nào.

Nguyên tắc ấy không phủ một trường hợp: một dòng tạo nhầm, chưa từng là xe thật. Đo trên hệ thật
14/10/2026: danh mục 16 xe, hai dòng là dữ liệu mẫu — không bán được (chưa từng mua), không ngừng
khai thác được (chưa từng khai thác), và nằm lại trong mẫu số của mọi phép tính đội hình.

LUẬT KHÓ NHẤT, và là lý do tệp này dài hơn vẻ ngoài của nó:

  HÀNG RÀO ĐỌC TỪ METADATA, KHÔNG GÕ TAY. Có 14 cột ở 14 bảng móc vào `vehicles.id`. Gõ tay 14 cái
  tên thì bảng thứ 15 thêm vào tháng sau lọt khỏi phép kiểm, và cửa xoá thành cửa tạo dòng mồ côi.
  Phép thử cuối tệp này canh đúng điều đó: nó KHÔNG đếm 14, nó đối chiếu với chính metadata.
"""
import os
import re
import tempfile
from datetime import date

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.hr import Vehicle, Employee, DispatchOrder  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.fleet import Trip, VehiclePlate, Maintenance  # noqa: E402
from app.services import xoa_xe as XX  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _xe(db, bien="51B-123.45", ma="XE0001"):
    v = Vehicle(plate=bien, code=ma, seats=45)
    db.add(v); db.flush()
    return v


def _tour(db, ma="T-001"):
    nv = Employee(code="NV1", full_name="Điều hành viên", department="Điều hành")
    db.add(nv); db.flush()
    t = Tour(code=ma, name="Đà Lạt", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 10, 1), end_date=date(2026, 10, 3))
    db.add(t); db.flush()
    return t


# ═════════════════ 1 · XOÁ ĐƯỢC ═════════════════

def test_xe_chua_tung_dung_thi_XOA_DUOC(db):
    v = _xe(db)
    s = XX.soat(db, v)
    assert s["xoa_duoc"] is True and s["vuong"] == []
    XX.xoa(db, v, "dòng dữ liệu mẫu, chưa từng là xe thật")
    assert db.get(Vehicle, v.id) is None


def test_lich_su_bien_DI_THEO_xe_chu_khong_phai_ly_do_tu_choi(db):
    """Một chiếc chưa từng dùng vẫn có dòng biển đầu tiên — đó không phải dấu vết hoạt động."""
    v = _xe(db)
    db.add(VehiclePlate(vehicle_id=v.id, plate=v.plate, from_date=date(2026, 1, 1)))
    db.flush()
    s = XX.soat(db, v)
    assert s["xoa_duoc"] is True
    assert [x["bang"] for x in s["se_xoa_theo"]] == ["vehicle_plates"]
    XX.xoa(db, v, "mẫu")
    assert db.query(VehiclePlate).count() == 0, "lịch sử biển phải xoá cùng, không để lại mồ côi"


def test_BAT_BUOC_co_ly_do(db):
    v = _xe(db)
    with pytest.raises(ValueError, match="lý do"):
        XX.xoa(db, v, "   ")
    assert db.get(Vehicle, v.id) is not None


# ═════════════════ 2 · KHÔNG XOÁ ĐƯỢC ═════════════════

def test_xe_DA_CO_CHUYEN_thi_khong_xoa(db):
    v = _xe(db, "50F-017.37", "XE0003")
    db.add(Trip(vehicle_id=v.id, ngay_di=date(2026, 1, 2), ngay_ve=date(2026, 1, 4),
                ten_tour="thử")); db.flush()
    s = XX.soat(db, v)
    assert s["xoa_duoc"] is False
    assert any(x["bang"] == "fleet_trips" for x in s["vuong"])
    assert "ngừng khai thác" in s["noi"].lower() or "NGỪNG KHAI THÁC" in s["noi"]
    with pytest.raises(ValueError):
        XX.xoa(db, v, "thử xoá")
    assert db.get(Vehicle, v.id) is not None, "có lịch sử mà vẫn xoá được là mất lịch sử"


def test_xe_co_LENH_DIEU_XE_thi_khong_xoa(db):
    v = _xe(db, "50F-022.59", "XE0005")
    t = _tour(db)
    tx = Employee(code="TX1", full_name="Tài xế", department="Đội xe"); db.add(tx); db.flush()
    db.add(DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=tx.id,
                         date_from=date(2026, 10, 1), date_to=date(2026, 10, 3))); db.flush()
    assert XX.soat(db, v)["xoa_duoc"] is False


def test_xe_co_PHIEU_BAO_DUONG_thi_khong_xoa(db):
    v = _xe(db, "50H-643.38", "XE0011")
    db.add(Maintenance(vehicle_id=v.id, kind="dinh_ky", ngay=date(2026, 5, 1))); db.flush()
    assert XX.soat(db, v)["xoa_duoc"] is False


def test_loi_NOI_RO_vuong_bao_nhieu_dong_cua_cai_gi(db):
    """Câu 'không xoá được' một mình thì người đọc phải đi dò từng màn hình."""
    v = _xe(db, "50F-034.71", "XE0007")
    for i in range(3):
        db.add(Trip(vehicle_id=v.id, ngay_di=date(2026, 1, 2), ngay_ve=date(2026, 1, 3),
                    ten_tour=f"t{i}"))
    db.flush()
    s = XX.soat(db, v)
    assert "3 chuyến xe" in s["noi"], s["noi"]


# ═════════════════ 3 · HÀNG RÀO ĐỌC TỪ METADATA ═════════════════

def test_hang_rao_SOAT_DU_moi_bang_moc_vao_xe_khong_bo_sot_bang_nao():
    """Phép thử QUAN TRỌNG NHẤT tệp này — và nó cố ý KHÔNG đếm một con số cứng.

    Đếm "phải có 14 bảng" thì tháng sau thêm bảng thứ 15, phép thử đỏ, ai đó sửa số 14 thành 15 rồi
    đi tiếp — mà cửa xoá vẫn chưa canh bảng mới. Nên ở đây đối chiếu với CHÍNH metadata: tập bảng
    hàm soát duyệt qua phải BẰNG tập bảng có khoá ngoại tới `vehicles.id`.
    """
    from app.db.session import Base as B
    that = {t.name for t in B.metadata.sorted_tables
            for c in t.columns for fk in c.foreign_keys
            if fk.column.table.name == "vehicles"}
    soat = {t.name for t, _ in XX._cot_moc_vao_xe()}
    assert soat == that, f"bảng hàm soát bỏ sót: {that - soat}"
    assert len(that) >= 10, "nghi ngờ metadata chưa nạp đủ model"


def test_bang_DI_THEO_XE_phai_la_tap_con_cua_cac_bang_that(db):
    """Gõ nhầm tên một bảng vào DI_THEO_XE thì bảng ấy lặng lẽ không bao giờ được xét."""
    that = {t.name for t, _ in XX._cot_moc_vao_xe()}
    assert XX.DI_THEO_XE <= that, f"tên không có thật trong DI_THEO_XE: {XX.DI_THEO_XE - that}"


# ═════════════════ 10 · MÀN HÌNH VÀ MÁY CHỦ PHẢI NÓI CÙNG MỘT ĐIỀU ═════════════════

def _tsx_doi_xe() -> str:
    """Đọc chính tệp màn hình, không gõ lại tên vai vào đây."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "web" / "app" / "doi-xe" / "page.tsx"
    assert p.exists(), f"khong thay man hinh doi xe tai {p}"
    return p.read_text(encoding="utf-8")


def test_vai_duoc_XOA_tren_man_hinh_va_may_chu_PHAI_KHOP():
    """Màn hình ẩn nút theo một danh sách vai, máy chủ từ chối theo một danh sách khác. Hai danh
    sách lệch nhau thì hoặc nút hiện ra rồi bấm vào báo 403, hoặc có vai bấm được mà màn hình
    không cho thấy nút — và cả hai đều là người dùng đứng trước một màn hình nói dối.

    Đã xảy ra thật 14/10/2026: Chủ tịch mở màn hình và KHÔNG THẤY nút xoá, vì em dựng ban đầu
    chỉ cho vai cntt mà không nói ra. Phép thử này đọc CẢ HAI chỗ khai và đối chiếu, nên lần
    sau ai nới một bên mà quên bên kia thì đỏ ngay.
    """
    from app.api.v1.fleet import XOA_XE
    m = re.search(r"const\s+XOA_XE_VAI\s*=\s*\[([^\]]*)\]", _tsx_doi_xe())
    assert m, ("web/app/doi-xe/page.tsx khong con khai `const XOA_XE_VAI = [...]` — "
               "mat cho doi chieu giua man hinh va may chu")
    vai_man_hinh = set(re.findall(r'"([a-z_]+)"', m.group(1)))
    assert vai_man_hinh == set(XOA_XE), (
        f"man hinh cho vai {sorted(vai_man_hinh)} thay nut xoa, "
        f"may chu chi nhan {sorted(set(XOA_XE))} — sua cho lech truoc khi di tiep")


def test_khoi_SOAT_phai_DAT_LAI_khi_doi_sang_xe_khac():
    """Đo 14/10/2026 trên bản chạy thật: soát `51B-123.45` (vướng 1 lệnh điều xe) rồi bấm sang
    `51B-678.90` (xoá được) thì khối VẪN in câu trả lời của chiếc trước — chính em đã tin nhầm
    một lần trước khi mở lại trang và soát riêng từng chiếc.

    React giữ nguyên trạng thái của khối khi chỉ đổi prop, nên chỗ gắn phải mang `key` theo id
    xe để khối dựng lại từ đầu. Đây là khối quyết định có làm mất hẳn một dòng hay không, nên
    một câu trả lời của xe khác nằm lại trên màn hình là lỗi nặng chứ không phải chuyện thẩm mỹ.
    """
    m = re.search(r"<XoaXe\b([^>]*)>", _tsx_doi_xe())
    assert m, "khong con cho gan <XoaXe> tren man hinh doi xe"
    assert re.search(r"key=\{\s*chon\.id\s*\}", m.group(1)), (
        "<XoaXe> thieu `key={chon.id}` — doi xe se khong dat lai ket qua soat")
