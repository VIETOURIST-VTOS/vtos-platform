# -*- coding: utf-8 -*-
"""PQ-4b · CỬA để ký hai mốc vận hành thật.

Ngày 10/9/2026 Chủ tịch quyết hai mốc và ngày 11/9 báo là "đã ký". Đo bản đang chạy: bảng tham số có
81 dòng, không dòng nào mang hai khóa ấy. Tìm tiếp thì ra lý do, và lý do không phải người quên ký:

  · màn hình Chính sách chỉ có ô CHỌN trong 81 khóa đang có, không có ô tạo khóa mới;
  · API propose_param chặn thẳng khóa chưa có dòng nào: Gate("THAM_SO", "Không có tham số này");
  · và ngay cả khi khóa tồn tại, nó kiểm giá trị bằng float() – một ngày tháng bị trả về
    "Giá trị phải là số".

Ba lớp chặn nối tiếp nhau, nên KHÔNG CÓ ĐƯỜNG NÀO nhập được hai mốc này. Đúng kiểu thiếu mà quy ước
"mỗi con số phải có một cửa nhập hoặc cửa tải" nói tới: không có cửa thì đó là việc còn thiếu.

Điều tệp này canh kỹ nhất không phải là cửa đã mở, mà là cửa mở ĐÚNG CÁCH: giá trị mặc định phải để
TRỐNG. seed_params tạo dòng mặc định kèm sẵn hai chữ ký – điền sẵn "01-12-2026" vào đó là hệ thống
tự đóng dấu VẬN HÀNH THẬT bằng một chữ ký không ai ký, và dấu ấy không gỡ được.

Định dạng ngày là DD-MM-YYYY (Chủ tịch chốt 11/9/2026) – kiểu người Việt gõ, không phải kiểu máy.
"""
from datetime import date

import pytest

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
import app.models.core  # noqa: F401
from app.models.core import Param
from app.services import rules as R
from app.services import moi_truong_du_lieu as MT


@pytest.fixture()
def db():
    md = Base.metadata
    can = {fk._table_key() for t in md.tables.values() for fk in t.foreign_keys}
    for ten in sorted(can - set(md.tables)):
        sa.Table(ten, md, sa.Column("id", sa.Integer, primary_key=True))
    eng = sa.create_engine("sqlite+pysqlite:///:memory:")
    md.create_all(eng)
    with Session(eng) as s:
        yield s


def _khoa(ten: str):
    return [d for d in R.DEFAULT_PARAMS if d[0] == ten]


# ---------------------------------------------------------------------------------------------
# 1. Khóa phải tồn tại – nếu không thì không đề xuất được
# ---------------------------------------------------------------------------------------------

def test_hai_moc_co_mat_trong_bo_tham_so():
    """propose_param đòi khóa đã có ít nhất một dòng. Khóa chưa khai ở đây là khóa không nhập được."""
    for ten in (MT.THAM_SO_MOC, MT.THAM_SO_MOC_NGUON["vietrip"]):
        assert _khoa(ten), f"không có cửa nào nhập được {ten}"


def test_hai_moc_deu_khai_la_tham_so_NGAY():
    """Không khai thì float('2026-12-01') ném lỗi và cửa vừa mở lại đóng ở lớp kiểm giá trị."""
    ngay = set(getattr(R, "THAM_SO_NGAY", ()))
    assert MT.THAM_SO_MOC in ngay
    assert MT.THAM_SO_MOC_NGUON["vietrip"] in ngay
    for ten in ngay:
        assert _khoa(ten), f"{ten} khai là tham số ngày nhưng không có trong bộ tham số"


def test_don_vi_noi_ro_dinh_dang_ngay():
    """Ô đơn vị là thứ người ký đọc trước khi gõ, nên nó phải nói ĐÚNG dạng mà cửa nhận.

    Chủ tịch chốt 11/9/2026: dạng là DD-MM-YYYY, kiểu người Việt gõ. Bản trước ghi YYYY-MM-DD –
    đúng với máy, sai với người ngồi ký.
    """
    for ten in getattr(R, "THAM_SO_NGAY", ()):
        đv = _khoa(ten)[0][3]
        assert MT.DINH_DANG_NGAY in đv, f"{ten}: đơn vị không nói định dạng người ký phải gõ"


def test_doc_ngay_nhan_dung_hai_dang_va_khong_doan_gi_them():
    """Hai dạng không thể lẫn nhau: nhóm bốn chữ số đứng đầu là năm, đứng cuối cũng là năm.

    Điều phép thử này canh là phần KHÔNG nhận: '05-06-2026' phải luôn là ngày 5 tháng 6. Một hàm
    đọc ngày biết đoán là một hàm sẽ đoán sai vào đúng hôm không ai kiểm lại.
    """
    from datetime import date as _d
    assert MT.doc_ngay("01-12-2026") == _d(2026, 12, 1)
    assert MT.doc_ngay("01/12/2026") == _d(2026, 12, 1), "người ta gõ dấu chéo nhiều hơn dấu gạch"
    assert MT.doc_ngay("2026-12-01") == _d(2026, 12, 1), "dạng cũ phải còn đọc được"
    assert MT.doc_ngay("05-06-2026") == _d(2026, 6, 5), "DD-MM chứ không phải MM-DD"
    for xau in ("01-13-2026", "31-02-2026", "hôm nay", "", "2026", "1/12/26"):
        assert MT.doc_ngay(xau) is None, f"đọc bừa được {xau!r}"


def test_ghi_ra_man_hinh_cung_dang_voi_luc_nhap():
    """Nhập 01-12-2026 mà hiện lại 2026-12-01 thì người dùng tưởng hệ thống vừa sửa số của mình."""
    from datetime import date as _d
    assert MT.ghi_ngay(_d(2026, 12, 1)) == "01-12-2026"
    assert MT.ghi_ngay(None) == ""


# ---------------------------------------------------------------------------------------------
# 2. Và phải để TRỐNG – đây là phần quan trọng hơn
# ---------------------------------------------------------------------------------------------

def test_gia_tri_mac_dinh_cua_hai_moc_phai_de_TRONG():
    """seed_params tạo dòng mặc định ở trạng thái active kèm signed_chutich và signed_tgd.

    Điền sẵn ngày vào đó nghĩa là hệ thống tự chuyển sang VẬN HÀNH THẬT bằng hai chữ ký mà không ai
    ký. Ngày tháng thật phải đi qua cửa đề xuất và hai chữ ký thật, giống mọi tham số chính sách
    khác. Để trống thì hệ thống đọc ra 'chưa chốt' – trạng thái đúng cho tới lúc có chữ ký.
    """
    for ten in (MT.THAM_SO_MOC, MT.THAM_SO_MOC_NGUON["vietrip"]):
        gt = _khoa(ten)[0][1]
        assert gt == "", f"{ten}: điền sẵn '{gt}' là ký thay Chủ tịch"


def test_can_cu_van_ghi_lai_con_so_Chu_tich_da_quyet():
    """Để trống giá trị không có nghĩa là quên mất anh ấy quyết gì – số đề xuất nằm ở cột căn cứ."""
    assert "01-12-2026" in _khoa(MT.THAM_SO_MOC)[0][4]
    assert "01-10-2026" in _khoa(MT.THAM_SO_MOC_NGUON["vietrip"])[0][4]


def test_seed_xong_van_la_CHUA_CHOT(db):
    """Phép thử quan trọng nhất tệp này: nạp mặc định xong, hệ thống vẫn phải nói CHƯA CHỐT."""
    R.seed_params(db)
    assert MT.moc_van_hanh_that(db) is None, "seed xong đã thành vận hành thật – chữ ký ở đâu ra?"
    assert MT.moc_cua_nguon(db, "vietrip") is None
    assert MT.che_do(db, date(2027, 1, 1)) == MT.THU_NGHIEM, \
        "chưa chốt mốc mà đã coi là dữ liệu thật thì mốc chẳng để làm gì"


def test_ky_roi_thi_moc_co_hieu_luc(db):
    """Và khi có dòng đã ký thật thì mốc phải ăn ngay – cửa mở ra để dùng, không phải để trưng."""
    R.seed_params(db)
    db.add(Param(key=MT.THAM_SO_MOC, value="01-12-2026", label="Mốc vận hành thật",
                 unit="ngày (DD-MM-YYYY)", effective_from=date(2026, 9, 11), status="active",
                 signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
    db.flush(); R.clear_param_cache()
    assert MT.moc_van_hanh_that(db) == date(2026, 12, 1)
    assert MT.che_do(db, date(2026, 12, 5)) == MT.THAT
    assert MT.che_do(db, date(2026, 11, 30)) == MT.THU_NGHIEM


def test_go_sai_dinh_dang_thi_coi_nhu_chua_chot_chu_khong_doan_bua(db):
    """Hỏng thì đóng. Đoán bừa một ngày ở đây là đóng dấu 'thật' lên dữ liệu thử, và dấu ấy không gỡ được.

    Ví dụ sai đổi ngày 11/9: bản trước lấy '01/12/2026' làm ví dụ GÕ SAI, nhưng từ nay dấu chéo là
    dạng hợp lệ. Ví dụ phải là thứ thật sự không đọc được, nếu không phép thử chỉ còn canh chính nó.
    """
    R.seed_params(db)
    db.add(Param(key=MT.THAM_SO_MOC, value="ngày 1 tháng 12", label="x", effective_from=date(2026, 9, 11),
                 status="active", signed_chutich=True, signed_tgd=True, proposed_by="chutich"))
    db.flush(); R.clear_param_cache()
    assert MT.moc_van_hanh_that(db) is None


# ---------------------------------------------------------------------------------------------
# 3. Cửa API phải thật sự nhận ngày
# ---------------------------------------------------------------------------------------------

def test_cua_de_xuat_nhan_ngay_thay_vi_doi_so():
    """Đọc mã đường propose_param: khóa ngày phải rẽ nhánh trước khi gặp float()."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[2] / "backend" / "app" / "api" / "v1" / "routes.py"
    if not p.exists():
        pytest.skip("chưa có kho mã")
    src = p.read_text(encoding="utf-8")
    dau = src.find("def propose_param")
    assert dau > 0
    khoi = src[dau:src.find("\n@router", dau)]
    assert "THAM_SO_NGAY" in khoi, "cửa đề xuất chưa biết tới tham số dạng ngày"
    assert khoi.index("THAM_SO_NGAY") < khoi.index("float(data.value)"), \
        "gặp float() trước thì nhánh ngày không bao giờ chạy tới"
    # Phải dùng CHUNG hàm đọc với nơi đọc mốc ra. Cửa nhận rộng hơn chỗ đọc nghĩa là có giá trị ký
    # xong mà hệ thống vẫn bảo chưa chốt – và không ai tìm ra vì cả hai phía đều "chạy đúng".
    assert "doc_ngay" in khoi, "cửa tự kiểm theo cách riêng thay vì dùng chung hàm đọc ngày"
