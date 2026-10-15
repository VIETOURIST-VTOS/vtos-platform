# -*- coding: utf-8 -*-
"""DL-4 · Xoá một lệnh điều xe chưa từng chạy — và chỉ lệnh chưa từng chạy.

VÌ SAO CÓ CỬA NÀY. Lệnh điều xe là chứng từ điều hành: nó nói ai cho xe nào chạy tour nào, ngày
nào, giá bao nhiêu. Một lệnh đã chạy phải ở lại trong sổ, nên phân hệ điều hành có cửa HUỶ và
không có cửa xoá nào. Nguyên tắc ấy không phủ một trường hợp: một lệnh tạo nhầm, chưa từng thành
chuyến, chưa ai nhận. Đo trên hệ thật 14/10/2026: xe mẫu `51B-123.45` không xoá được vì vướng
đúng một lệnh — `DL-0825`, và đó là lệnh điều xe duy nhất trong toàn hệ thống.

LUẬT KHÓ NHẤT, và là lý do tệp này dài hơn vẻ ngoài:

  `status` KHÔNG phải bằng chứng. `DL-0825` mang chữ "hoan_thanh" mà không có lấy một chuyến nào.
  Chặn theo chữ thì cửa vô dụng đúng ở trường hợp duy nhất cần nó. Nên chỉ hai thứ chặn xoá:
  CÓ CHUYẾN móc vào, hoặc TÀI XẾ ĐÃ NHẬN — hai dấu vết của việc đã xảy ra ngoài đời.
"""
import json
import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

import pytest  # noqa: E402
from app.db.session import Base, engine, SessionLocal  # noqa: E402
from app.models.core import Tour  # noqa: E402
from app.models.hr import DispatchOrder, Employee, Vehicle  # noqa: E402
from app.models.fleet import Trip  # noqa: E402
from app.services import xoa_lenh as XL  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.create_all(engine)
    s = SessionLocal()
    yield s
    s.close()
    Base.metadata.drop_all(engine)


def _nen(db):
    v = Vehicle(plate="51B-123.45", code="XE0001", seats=45)
    nv = Employee(code="NV1", full_name="Điều hành viên", department="Điều hành")
    tx = Employee(code="TX1", full_name="Lý Văn Sơn", department="doi_xe")
    db.add_all([v, nv, tx]); db.flush()
    t = Tour(code="DL-0825", name="Đà Lạt", tour_type="doan_noi_dia", operator_id=nv.id,
             start_date=date(2026, 8, 16), end_date=date(2026, 8, 18))
    db.add(t); db.flush()
    return v, tx, t


def _lenh(db, trang_thai="hoan_thanh", nhan_luc=None):
    v, tx, t = _nen(db)
    d = DispatchOrder(tour_id=t.id, vehicle_id=v.id, driver_id=tx.id,
                      date_from=date(2026, 8, 16), date_to=date(2026, 8, 18),
                      internal_price=10_500_000, created_by="chutich",
                      status=trang_thai, nhan_luc=nhan_luc)
    db.add(d); db.flush()
    return d


# ═════════════════ 1 · XOÁ ĐƯỢC ═════════════════

def test_lenh_chua_tung_chay_thi_XOA_DUOC(db):
    d = _lenh(db, trang_thai="cho_xac_nhan")
    s = XL.soat(db, d)
    assert s["xoa_duoc"] is True
    assert s["vuong"] == []
    assert "xoá được" in s["noi"]


def test_status_HOAN_THANH_mot_minh_KHONG_phai_ly_do_tu_choi(db):
    """Đúng hình dáng của DL-0825: mang chữ "hoàn thành" nhưng không có chuyến, không ai nhận.

    Nếu phép thử này đỏ nghĩa là ai đó đã thêm `status` vào danh sách chặn — và làm thế thì cửa
    này vô dụng đúng ở trường hợp duy nhất cần nó.
    """
    d = _lenh(db, trang_thai="hoan_thanh")
    assert XL.soat(db, d)["xoa_duoc"] is True


# ═════════════════ 2 · KHÔNG XOÁ ĐƯỢC ═════════════════

def test_lenh_CO_CHUYEN_thi_khong_xoa(db):
    d = _lenh(db, trang_thai="cho_xac_nhan")
    db.add(Trip(vehicle_id=d.vehicle_id, dispatch_id=d.id,
                ngay_di=date(2026, 8, 16), ngay_ve=date(2026, 8, 18)))
    db.flush()
    s = XL.soat(db, d)
    assert s["xoa_duoc"] is False
    assert any(x["bang"] == "fleet_trips" for x in s["vuong"])
    assert "chuyến" in s["noi"]


def test_lenh_TAI_XE_DA_NHAN_thi_khong_xoa(db):
    """Dấu nhận là một CỘT trên chính lệnh, không phải một bảng — phép quét khoá ngoại không
    thấy nó. Bỏ phép kiểm riêng ấy đi thì một lệnh đã có người nhận vẫn lọt qua cửa."""
    d = _lenh(db, trang_thai="da_xac_nhan", nhan_luc=datetime(2026, 8, 15, 9, 0))
    s = XL.soat(db, d)
    assert s["xoa_duoc"] is False
    assert s["tai_xe_da_nhan"] is True
    assert "tài xế đã nhận" in s["noi"]


def test_BAT_BUOC_co_ly_do(db):
    d = _lenh(db, trang_thai="cho_xac_nhan")
    with pytest.raises(ValueError):
        XL.xoa(db, d, "   ")


def test_xoa_tra_ve_NGUYEN_noi_dung_de_dung_lai_duoc(db):
    d = _lenh(db, trang_thai="cho_xac_nhan")
    did = d.id
    kq = XL.xoa(db, d, "lệnh dữ liệu mẫu, chưa từng chạy")
    assert kq["da_xoa"]["id"] == did
    assert kq["da_xoa"]["internal_price"] == 10_500_000
    assert kq["ly_do"] == "lệnh dữ liệu mẫu, chưa từng chạy"
    assert db.get(DispatchOrder, did) is None


def test_ban_ghi_DA_XOA_phai_ghi_duoc_vao_NHAT_KY(db):
    """CHỖ HỎNG THẬT, 15/10/2026, lần bấm đầu tiên của Chủ tịch trên bản chạy thật: cửa xoá trả
    về 500. Nguyên nhân là `da_xoa` mang các ô `date`/`datetime` thô, mà nhật ký kiểm toán băm
    nội dung qua JSON — gặp kiểu ngày là nổ.

    Phép thử cũ 11/11 xanh mà cửa vẫn hỏng, vì nó chỉ đo lớp dịch vụ chứ không đo thứ chỗ gọi
    sẽ làm với kết quả ấy. Nên phép thử này chạy ĐÚNG phép biến đổi mà nhật ký chạy.
    """
    d = _lenh(db, trang_thai="hoan_thanh")
    kq = XL.xoa(db, d, "lệnh dữ liệu mẫu")
    json.dumps(kq["da_xoa"])          # nổ ở đây là cửa xoá sẽ trả về 500
    from app.services.rules import _canon
    _canon({"before": kq["da_xoa"], "after": {"ly_do": kq["ly_do"]}})
    assert kq["da_xoa"]["date_from"] == "2026-08-16"


# ═════════════════ 3 · CỬA SOÁT PHẢI IN RA ĐỦ ĐỂ NGƯỜI BẤM NHÌN TẬN MẮT ═════════════════

def test_soat_IN_RA_noi_dung_lenh_chu_khong_chi_mot_cau_ket_luan(db):
    """Người sắp làm mất hẳn một chứng từ phải thấy nó là chứng từ gì. In mỗi câu «xoá được»
    thì người bấm đang tin một câu, không phải nhìn một dòng dữ liệu."""
    d = _lenh(db, trang_thai="hoan_thanh")
    l = XL.soat(db, d)["lenh"]
    assert l["tour"] == "DL-0825"
    assert l["xe"] == "51B-123.45"
    assert l["tai_xe"] == "Lý Văn Sơn"
    assert l["gia_noi_bo"] == 10_500_000
    assert l["trang_thai"] == "hoan_thanh"
    assert l["tu_ngay"] == date(2026, 8, 16) and l["den_ngay"] == date(2026, 8, 18)


# ═════════════════ 4 · HÀNG RÀO ĐỌC TỪ METADATA ═════════════════

def test_hang_rao_SOAT_DU_moi_bang_moc_vao_lenh_khong_bo_sot_bang_nao():
    """KHÔNG đếm con số 1. Đối chiếu với chính `Base.metadata`, nên bảng thứ hai thêm vào tháng
    sau tự được canh — gõ tay một danh sách là tháng sau có một đường vòng không ai biết."""
    from app.db.session import Base as B
    that = {(t.name, c.name) for t in B.metadata.sorted_tables for c in t.columns
            for fk in c.foreign_keys if fk.column.table.name == "dispatch_orders"}
    quet = {(t.name, c.name) for t, c in XL._cot_moc_vao_lenh()}
    assert quet == that, f"hang rao bo sot: {that - quet}"


# ═════════════════ 5 · MÀN HÌNH VÀ MÁY CHỦ PHẢI NÓI CÙNG MỘT ĐIỀU ═════════════════

def _tsx_lenh() -> str:
    p = Path(__file__).resolve().parents[2] / "web" / "app" / "lenh-dieu-xe" / "page.tsx"
    assert p.exists(), f"khong thay man hinh lenh dieu xe tai {p}"
    return p.read_text(encoding="utf-8")


def test_vai_duoc_XOA_LENH_tren_man_hinh_va_may_chu_PHAI_KHOP():
    from app.api.v1.hr import XOA_LENH
    m = re.search(r"const\s+XOA_LENH_VAI\s*=\s*\[([^\]]*)\]", _tsx_lenh())
    assert m, "web/app/lenh-dieu-xe/page.tsx khong con khai `const XOA_LENH_VAI = [...]`"
    vai = set(re.findall(r'"([a-z_]+)"', m.group(1)))
    assert vai == set(XOA_LENH), (
        f"man hinh cho vai {sorted(vai)}, may chu chi nhan {sorted(set(XOA_LENH))}")


def test_vai_xoa_LENH_phai_KHOP_vai_xoa_XE():
    """Hai cửa cùng làm mất hẳn một dòng. Một bên rộng hơn bên kia thì hàng rào chặt đang nằm
    cạnh một đường vòng — và người ta sẽ đi đường vòng."""
    from app.api.v1.fleet import XOA_XE
    from app.api.v1.hr import XOA_LENH
    assert set(XOA_LENH) == set(XOA_XE), (
        f"xoa lenh: {sorted(set(XOA_LENH))} — xoa xe: {sorted(set(XOA_XE))}")


def test_khoi_XOA_tren_man_hinh_dat_lai_khi_doi_lenh():
    """Đã xảy ra thật ở cửa xoá xe 14/10/2026: soát dòng A rồi bấm sang dòng B thì khối vẫn in
    câu trả lời của A. React giữ nguyên trạng thái khi chỉ đổi prop."""
    m = re.search(r"<XoaLenh\b([^>]*)>", _tsx_lenh())
    assert m, "khong con cho gan <XoaLenh> tren man hinh lenh dieu xe"
    assert re.search(r"key=\{\s*d\.id\s*\}", m.group(1)), (
        "<XoaLenh> thieu `key={d.id}` — doi lenh se khong dat lai ket qua soat")
