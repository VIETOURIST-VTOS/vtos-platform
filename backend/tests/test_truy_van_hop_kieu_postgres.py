"""Chặn lớp lỗi CHỈ XUẤT HIỆN TRÊN POSTGRESQL mà kiểm thử chạy SQLite không thể bắt.

Ngày 07/9/2026 trang chủ của Chủ tịch đứng ở "Đang tải…" vĩnh viễn. Nguyên nhân:

    select(Tour).where(..., Tour.chairman_run_decision == False, ...)

`chairman_run_decision` là CHUỖI ghi nội dung quyết định ("Chủ tịch duyệt chạy 07/09/2026"),
không phải cờ đúng/sai. SQLite âm thầm ép kiểu nên toàn bộ 300+ phép thử vẫn xanh; PostgreSQL
từ chối thẳng:

    operator does not exist: character varying = boolean

Bảng điều khiển trả 500, giao diện nuốt lỗi (`.catch(() => {})`) nên người dùng chỉ thấy trang
đứng im. Lỗi nằm ở chỗ khó thấy nhất: đúng cú pháp, đúng kiểu tư duy Python, xanh hết kiểm thử.

Phép thử này không kiểm một dòng mã cụ thể mà quét TOÀN BỘ mã nguồn: hễ có `<Model>.<cột> == True/False`
mà cột đó không phải Boolean thì báo lỗi. Thêm cột chuỗi mới rồi vô tình so với False sẽ bị chặn ngay.
"""
import os, re, sys, pathlib
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_kieu.db"); os.environ.setdefault("ENV", "dev")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from sqlalchemy import Boolean
from app.db.session import Base
import app.models.core, app.models.hr, app.models.finance, app.models.fleet, app.models.ops        # noqa: F401
import app.models.accounting, app.models.assets, app.models.banks, app.models.crm, app.models.visa  # noqa: F401
import app.models.hrm, app.models.payments, app.models.vietrip, app.models.reports_auto             # noqa: F401

APP = pathlib.Path(__file__).resolve().parent.parent / "app"


def _kieu_cot() -> dict[str, dict[str, object]]:
    """{TênLớp: {tên_cột: kiểu}} lấy thẳng từ metadata của SQLAlchemy."""
    out = {}
    for lop in Base.registry.mappers:
        cls = lop.class_
        out[cls.__name__] = {c.key: c.type for c in lop.columns}
    return out


def test_khong_so_sanh_cot_khong_phai_boolean_voi_true_false():
    kieu = _kieu_cot()
    # cột nào là Boolean thì so với True/False là ĐÚNG; tên cột trùng nhau giữa các bảng thì chỉ cần
    # một bảng có cột Boolean cùng tên là bỏ qua – quét bằng chữ không biết biến thuộc lớp nào.
    bool_cot, moi_cot = set(), set()
    for cols in kieu.values():
        for ten, t in cols.items():
            moi_cot.add(ten)
            if isinstance(t, Boolean): bool_cot.add(ten)

    mau = re.compile(r"\b([A-Z]\w+)\.(\w+)\s*==\s*(True|False)\b")
    vi_pham = []
    for f in APP.rglob("*.py"):
        for i, dong in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if dong.lstrip().startswith("#"): continue
            for lop, cot, gt in mau.findall(dong):
                if cot not in moi_cot or cot in bool_cot: continue
                if lop in kieu and cot in kieu[lop] and isinstance(kieu[lop][cot], Boolean): continue
                vi_pham.append(f"{f.relative_to(APP.parent)}:{i}  {lop}.{cot} == {gt}  "
                               f"(cột {cot} không phải Boolean – PostgreSQL sẽ báo "
                               f"'operator does not exist: character varying = boolean')")
    assert not vi_pham, "So sánh cột không phải Boolean với True/False:\n  " + "\n  ".join(vi_pham)


def test_cot_chairman_run_decision_van_la_chuoi():
    """Chốt lại bản chất của cột gây ra sự cố: nó lưu NỘI DUNG quyết định, nên phép so đúng là so với chuỗi rỗng."""
    from app.models.core import Tour
    from sqlalchemy import String
    assert isinstance(Tour.__table__.c.chairman_run_decision.type, String)
