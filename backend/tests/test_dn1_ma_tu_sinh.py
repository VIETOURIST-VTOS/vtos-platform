"""DN-1 · Mã hồ sơ tự sinh: lấy số lớn nhất của đúng tiền tố, không đếm cả bảng.

Mười chỗ trong `services/` từng viết cùng một dòng `count() + 1` rồi ghép tháng vào. Ba hỏng,
và cả ba đều có thật trong kho này — xem phần mở đầu `services/ma_tu_sinh.py`:

  1. Xoá một dòng là cấp lại một mã đang còn sống. Cột `code` UNIQUE → lỗi 500, và cửa
     `DELETE /import/vietrip/records/user/{id}` của CNTT là một đường xoá CÓ THẬT.
  2. Mã mang tháng mà số thứ tự không bao giờ về 1 khi sang tháng mới.
  3. Mã khác tiền tố trong cùng bảng (VT#### của robot Vietrip) làm nhảy dãy NS####.

Phép thử cuối là HÀNG RÀO QUÉT MÃ NGUỒN: nó không tin vào lần sửa hôm nay, nó canh để lối cũ
không quay lại ở bộ sinh mã thứ mười một.
"""
import ast
import pathlib
import re
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.core import User, Company  # noqa: F401 – bảng mà khoá ngoại của Employee trỏ tới
from app.models.hr import Employee
from app.services.ma_tu_sinh import tiep_theo

DV = pathlib.Path(__file__).resolve().parents[1] / "app" / "services"


@pytest.fixture()
def db():
    m = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool,
                         connect_args={"check_same_thread": False})
    Base.metadata.create_all(m)
    with Session(m) as s:
        yield s


def _ns(db, *ma):
    for i, c in enumerate(ma):
        db.add(Employee(code=c, full_name=f"Người {i}", department="hcns"))
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 1 · ĐẾM TIẾP TỪ SỐ LỚN NHẤT, KHÔNG ĐẾM SỐ DÒNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_bang_rong_thi_bat_dau_tu_mot(db):
    assert tiep_theo(db, Employee, "NS", 4) == "NS0001"


def test_cap_tiep_so_lon_nhat_cong_mot(db):
    _ns(db, "NS0001", "NS0002", "NS0003")
    assert tiep_theo(db, Employee, "NS", 4) == "NS0004"


def test_xoa_mot_dong_giua_chung_KHONG_cap_lai_ma_dang_con_song(db):
    """Đây là chỗ hỏng số một, và nó bật ra sau MỖI lần CNTT gỡ một hồ sơ nạp nhầm."""
    _ns(db, "NS0001", "NS0002", "NS0003")
    db.delete(db.query(Employee).filter_by(code="NS0002").one())
    db.flush()
    ma = tiep_theo(db, Employee, "NS", 4)
    assert ma == "NS0004", (
        f"Sau khi xoá một dòng giữa chừng, hàm cấp {ma!r}. Lối cũ (đếm cả bảng) cấp NS0003 — "
        "mã ấy đang còn sống, và cột `code` UNIQUE nên người dùng ăn nguyên một lỗi 500.")
    assert ma not in {e.code for e in db.query(Employee).all()}


def test_ma_khac_tien_to_trong_cung_bang_khong_lam_nhay_so(db):
    """Bảng `employees` chứa cả NS#### người lập lẫn VT#### robot Vietrip nạp."""
    _ns(db, "NS0001", "VT0137", "VT0138", "VT0139")
    assert tiep_theo(db, Employee, "NS", 4) == "NS0002", (
        "Robot Vietrip nạp ba người thì dãy NS phải đứng yên. Lối cũ đếm cả bảng nên nhảy sang "
        "NS0005, và sáu tháng sau không ai giải thích được quãng trống ấy.")
    assert tiep_theo(db, Employee, "VT", 4) == "VT0140"


def test_sang_thang_moi_thi_so_ve_mot(db):
    """Mã khiếu nại đọc như 'hồ sơ thứ N của tháng ấy' — nó phải nói đúng điều nó trông như nói.

    Hai mốc tháng dựng từ `date`, KHÔNG gõ cứng chuỗi mã: hàng rào `test_tc101` cấm mã chứng từ
    viết thẳng trong phép thử, vì một chuỗi như thế đỏ vào đầu tháng sau mà không ai đụng mã
    nguồn. Ở đây tháng còn là THỨ ĐANG ĐƯỢC THỬ, nên dựng nó ra cũng là cách nói rõ hơn.
    """
    thang_truoc, thang_nay = date(2026, 10, 1), date(2026, 11, 1)
    truoc, nay = f"KN{thang_truoc:%y%m}-", f"KN{thang_nay:%y%m}-"
    _ns(db, *(f"{truoc}{i:03d}" for i in (1, 2, 3)))
    assert tiep_theo(db, Employee, nay, 3) == f"{nay}001", (
        "Tiền tố mang tháng mới thì dãy số phải bắt đầu lại từ 001. Lối cũ đếm cả bảng nên hồ sơ "
        "đầu tiên của tháng 11 mang số 004.")
    assert tiep_theo(db, Employee, truoc, 3) == f"{truoc}004"


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 2 · DỮ LIỆU CŨ LẠ DẠNG KHÔNG ĐƯỢC CHẶN NGƯỜI ĐANG LẬP HỒ SƠ
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def test_duoi_khong_phai_so_thuan_thi_bo_qua_chu_khong_nem_loi(db):
    _ns(db, "NS0001", "NS0002_cu", "NSxxxx", "NS0003")
    assert tiep_theo(db, Employee, "NS", 4) == "NS0004"


def test_gach_duoi_trong_tien_to_khong_vot_nham_ky_khac(db):
    """`_` trong LIKE khớp MỘT ký tự bất kỳ. Không thoát thì tiền tố này vợt luôn dãy kia."""
    _ns(db, "AB_C-001", "ABXC-009")
    assert tiep_theo(db, Employee, "AB_C-", 3) == "AB_C-002", (
        "Tiền tố chứa `_` phải được so đúng từng chữ. Trả về 010 nghĩa là câu hỏi đã vợt cả "
        "ABXC-009 của một dãy khác.")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# 3 · HÀNG RÀO: LỐI ĐẾM CŨ KHÔNG ĐƯỢC QUAY LẠI
# ═══════════════════════════════════════════════════════════════════════════════════════════════

# Một ngoại lệ, và nó có lý do bằng chữ. `nonpackage.next_code` KHÔNG đếm cả bảng — nó đọc các
# mã đã có cùng ngày rồi tìm chỗ trống, tức là đã đúng tinh thần, chỉ khác cách đánh số (hậu tố
# `_2` thay vì số thứ tự). Đừng nới danh sách này; thêm một tên vào đây là mở lại đúng cái cửa
# mà phép thử sinh ra để đóng.
MIEN = {("nonpackage.py", "next_code")}

DEM = "func.count()"
# `return f"...{n:03d}"` / `{n:0{width}d}` — một con số ĐẾM ĐƯỢC rồi đệm số 0, tức là một mã.
DEM_RA_MA = re.compile(r"return\s+f[\"'].*\{[^{}]*:\s*0(?:\d*d|\{)", re.S)


def _ham_sinh_ma():
    """Mọi hàm trong `services/` vừa đếm vừa trả về một chuỗi có số đệm 0 — tức là đang sinh mã."""
    ra = []
    for tep in sorted(DV.glob("*.py")):
        than = tep.read_text(encoding="utf-8")
        try:
            cay = ast.parse(than)
        except SyntaxError:                      # noqa: PERF203 – tệp hỏng thì phép thử khác lo
            continue
        for nut in ast.walk(cay):
            if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            than_ham = ast.get_source_segment(than, nut) or ""
            if DEM in than_ham and DEM_RA_MA.search(than_ham):
                ra.append((tep.name, nut.name, than_ham))
    return ra


def test_khong_con_cho_nao_sinh_ma_bang_cach_dem_ca_bang():
    xau = [(t, h) for t, h, _ in _ham_sinh_ma() if (t, h) not in MIEN]
    assert not xau, (
        "Có bộ sinh mã lấy số bằng cách đếm cả bảng rồi cộng một. Xoá một dòng là cấp lại một mã "
        "đang còn sống, và cột `code` UNIQUE nên người dùng ăn lỗi 500; mã mang tháng thì số "
        "cũng không bao giờ về 1. Dùng `services/ma_tu_sinh.tiep_theo(db, Model, tiền_tố, rộng)` "
        "— nó lấy số lớn nhất của đúng tiền tố ấy.\n"
        + "\n".join(f"  {t}:{h}()" for t, h in xau))


def test_bo_sinh_ma_that_cua_nhan_su_cung_chiu_duoc_mot_lan_xoa(db):
    """Đi qua HÀM THẬT mà cửa thêm nhân sự gọi, không chỉ qua hàm chung.

    Hàng rào quét mã nguồn ở trên canh LUẬT; phép thử này canh DÂY NỐI. Một bộ sinh mã có thể
    gọi đúng hàm chung mà truyền sai tiền tố, và lúc ấy máy quét vẫn xanh.

    Chọn đúng `hr.next_code` vì nó là chỗ có đường xoá thật: cửa
    `DELETE /import/vietrip/records/user/{id}` cho CNTT gỡ một hồ sơ nhân sự nạp nhầm, và lối cũ
    thì ngay lần thêm người kế tiếp là đụng mã.
    """
    from app.services import hr as H
    _ns(db, "NS0001", "NS0002", "NS0003")
    db.delete(db.query(Employee).filter_by(code="NS0002").one())
    db.flush()
    ma = H.next_code(db, Employee, "NS")
    dang_co = {e.code for e in db.query(Employee).all()}
    assert ma == "NS0004", f"hr.next_code cấp {ma!r} sau một lần xoá — lối cũ cấp NS0003."
    assert ma not in dang_co, f"{ma} đang có người giữ — thêm nhân sự sẽ ăn lỗi 500."
