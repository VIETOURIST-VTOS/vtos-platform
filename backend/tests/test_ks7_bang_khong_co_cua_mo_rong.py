"""KS-7 · Mở rộng bộ kiểm "bảng không có cửa" — và bịt chỗ bộ kiểm ấy đang MÙ.

Bộ kiểm cũ (test_ks_cua_nhap.py) vẫn đúng và vẫn chạy. Tệp này thêm ba lớp mà bộ kiểm cũ không với
tới, và lớp đầu tiên là lớp quan trọng nhất:

  C1  MỌI bảng định nghĩa dưới app/models phải có mặt sau khi `import app.models`
  C2  MỌI bảng do migration tạo ra phải có mặt trong mô hình
  C3  bảng thuộc năm nhóm của lệnh KS-7 không được khai là "máy sinh"

Vì sao C1 quan trọng hơn vẻ ngoài của nó:

  `ks_cua_nhap._bang_mo_hinh()` nạp `app.main` chứ không nạp `app.models`, nên nó thấy đủ bảng NHỜ
  việc một router nào đó tình cờ nạp mô-đun mô hình. Đó là may, không phải thiết kế.

  Chuyện này đã xảy ra một lần và được ghi lại ngay trong app/models/__init__.py: Đội xe thiếu dòng
  import từ đầu, nên `Base.metadata` sau `import app.models` thiếu 20 bảng, và MỌI phép thử soi
  metadata đều mù đúng phần đội xe. Phát hiện 09/9/2026, khi phép thử canh cột tiền K2 chỉ nhìn thấy
  62 trong 83 cột — và vẫn báo XANH.

  Lần ấy chữa đúng một dòng (thêm import fleet) mà không đặt cái canh. Đo lại hôm nay 11/9/2026:
  `app/models/tu_dong.py` vẫn chưa có trong __init__, nên hai bảng của V11 — tác vụ tự động và lần
  chạy tác vụ — lại đang nằm ngoài tầm nhìn của mọi phép thử soi metadata. Cùng một lỗi, lần thứ hai,
  một tháng chưa qua. C1 là cái canh mà lần chữa trước đã thiếu.

  Một phép thử mù báo xanh nguy hiểm hơn một phép thử đỏ, vì màu xanh được đem đi báo cáo.
"""
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_ks7_cua.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_ks7_cua.db", "test_ks7_cua.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU_MUC_MO_HINH = os.path.join(GOC, "app", "models")
THU_MUC_VERSIONS = os.path.join(GOC, "alembic", "versions")

# Năm nhóm bảng lệnh KS-7 nêu tên. Khoá là nhóm, giá trị là các mảnh tên bảng nhận ra nhóm ấy.
NHOM_KS7 = {
    "hồ sơ khách hàng": ("khach_hang", "ho_so_khach", "customer_profile", "hop_dong_khach"),
    "định danh": ("dinh_danh", "identity", "cccd", "ho_chieu", "passport"),
    "phân bổ tiền": ("phan_bo", "allocation", "prepaid_alloc", "phan_chia_tien"),
    "giữ chỗ": ("giu_cho", "hold", "reservation", "bao_luu"),
    "chứng từ nội bộ": ("chung_tu_noi_bo", "doc_chung_tu", "ban_doc_chung_tu", "phieu_noi_bo"),
}


def _bang_theo_import_models() -> set[str]:
    import app.models  # noqa: F401
    from app.db.session import Base
    return {t for t in Base.metadata.tables} - {"alembic_version"}


def _bang_theo_import_main() -> set[str]:
    import app.main  # noqa: F401
    from app.db.session import Base
    return {t for t in Base.metadata.tables} - {"alembic_version"}


def _bang_khai_trong_tep_mo_hinh() -> dict[str, str]:
    """{tên bảng: tệp khai} — đọc thẳng __tablename__ trong mã, không phụ thuộc import nào cả."""
    ra = {}
    for t in sorted(os.listdir(THU_MUC_MO_HINH)):
        if not t.endswith(".py") or t == "__init__.py":
            continue
        src = open(os.path.join(THU_MUC_MO_HINH, t), encoding="utf-8").read()
        for m in re.finditer(r'__tablename__\s*=\s*["\']([^"\']+)["\']', src):
            ra[m.group(1)] = t
    return ra


def _phan_nang_cap(src: str) -> str:
    """Chỉ thân hàm upgrade(): bảng do downgrade() dựng lại (để lùi bản) không phải bảng đang có trên cơ sở dữ liệu."""
    import ast
    try:
        cay = ast.parse(src)
    except SyntaxError:
        return src
    for n in cay.body:
        if isinstance(n, ast.FunctionDef) and n.name == "upgrade":
            return ast.get_source_segment(src, n) or src
    return src


def _bang_do_migration_tao() -> set[str]:
    # KS-19k (06/11/2026): bảng một bản nâng cấp SAU đã bỏ (op.drop_table trong upgrade) thì không còn trên cơ sở
    # dữ liệu — trừ ra. Ví dụ bao_gia_doan: TK-2 tạo, KS-19k gộp vào bao_gia rồi bỏ; downgrade của KS-19k dựng lại.
    ra, bo = set(), set()
    for f in sorted(os.listdir(THU_MUC_VERSIONS)):
        if not f.endswith(".py") or f.startswith("__"):
            continue
        src = _phan_nang_cap(open(os.path.join(THU_MUC_VERSIONS, f), encoding="utf-8").read())
        for m in re.finditer(r'op\.create_table\(\s*["\']([^"\']+)["\']', src):
            ra.add(m.group(1))
        for m in re.finditer(r'CREATE TABLE (?:IF NOT EXISTS )?["\']?(\w+)', src, re.I):
            ra.add(m.group(1))
        for m in re.finditer(r'op\.drop_table\(\s*["\']([^"\']+)["\']', src):
            bo.add(m.group(1))
    return ra - bo - {"alembic_version"}


# ------------------------------------------------------------------ C1

def test_c1_import_app_models_phai_thay_moi_bang_dinh_nghia_duoi_app_models():
    """Lỗi này đã xảy ra một lần với Đội xe (09/9), chữa một dòng mà không đặt cái canh. Đây là cái canh.

    Hệ quả khi thiếu: `Base.metadata` không có bảng ấy, nên mọi phép thử soi metadata — kể cả bộ kiểm
    'bảng không có cửa' — không nhìn thấy nó và vẫn báo xanh.
    """
    khai = _bang_khai_trong_tep_mo_hinh()
    thay = _bang_theo_import_models()
    thieu = {b: t for b, t in khai.items() if b not in thay}
    assert not thieu, (
        f"{len(thieu)} bảng khai trong app/models nhưng KHÔNG có trong Base.metadata sau "
        f"`import app.models`:\n"
        + "\n".join(f"  · {b}  (khai ở app/models/{t})" for b, t in sorted(thieu.items()))
        + "\n\n  Nguyên nhân: app/models/__init__.py thiếu dòng import cho những tệp ấy.\n"
          "  Hệ quả: mọi phép thử soi metadata đều MÙ đúng phần đó và vẫn báo xanh — "
          "đúng chuyện đã xảy ra với Đội xe ngày 09/9/2026 (62/83 cột, vẫn xanh).\n"
          "  Sửa: thêm dòng `from app.models.<tệp> import *  # noqa` vào app/models/__init__.py.")


def test_c1b_bo_kiem_cua_nhap_khong_duoc_phu_thuoc_vao_viec_nap_app_main():
    """Bộ kiểm cửa nhập hiện thấy đủ bảng NHỜ `import app.main`, tức là nhờ một router tình cờ nạp hộ.

    Đó là may chứ không phải thiết kế: bỏ một router đi là bộ kiểm mù thêm một mảng mà không ai biết.
    """
    a, b = _bang_theo_import_models(), _bang_theo_import_main()
    chi_co_qua_main = sorted(b - a)
    assert not chi_co_qua_main, (
        f"{len(chi_co_qua_main)} bảng chỉ xuất hiện khi nạp app.main, không xuất hiện khi nạp "
        f"app.models: {chi_co_qua_main}\n"
        "  Nghĩa là bộ kiểm cửa nhập đang thấy đủ bảng nhờ một router nạp hộ. Bỏ router ấy đi thì "
        "bộ kiểm mù thêm một mảng và vẫn báo xanh.")


# ------------------------------------------------------------------ C2

def test_c2_bang_do_migration_tao_phai_co_trong_mo_hinh():
    """Bảng chỉ có trong migration mà không có mô hình thì nằm NGOÀI mọi bộ kiểm, kể cả bộ kiểm cửa.

    Không phải chuyện lý thuyết: cơ sở dữ liệu thật có bảng ấy, người vẫn ghi vào được qua SQL, mà
    không phép thử nào của kho nhìn thấy nó.
    """
    mo = _bang_theo_import_models()
    thieu = sorted(_bang_do_migration_tao() - mo)
    assert not thieu, (
        f"{len(thieu)} bảng do migration tạo nhưng không có trong mô hình: {thieu}\n"
        "  Chúng nằm ngoài tầm nhìn của bộ kiểm cửa nhập, bộ kiểm cột tiền và mọi phép thử soi "
        "metadata. Hoặc thêm mô hình, hoặc bỏ bảng đi.")


# ------------------------------------------------------------------ C3

def test_c3_nam_nhom_bang_cua_lenh_ks7_khong_duoc_khai_la_may_sinh():
    """Năm nhóm lệnh KS-7 nêu tên: hồ sơ khách hàng, định danh, phân bổ tiền, giữ chỗ, chứng từ nội bộ.

    "Máy sinh" là lối thoát dễ nhất cho một bảng thiếu cửa, và năm nhóm này là nơi lối thoát ấy sai
    nhất: hồ sơ khách và định danh là số NGƯỜI khai; phân bổ tiền, giữ chỗ và chứng từ nội bộ là chỗ
    tiền đi qua. Chỗ tiền đi qua mà không có cửa nhập thì không có ai chịu trách nhiệm cho con số.
    """
    from app.services import ks_cua_nhap as CN
    mo = _bang_theo_import_models()
    sai = []
    for nhom, manh in NHOM_KS7.items():
        for b in sorted(mo):
            if any(m in b for m in manh) and b in CN.MAY_SINH:
                sai.append(f"{b} (nhóm {nhom})\n      khai máy sinh vì: {CN.MAY_SINH[b]}")
    assert not sai, (
        "bảng thuộc năm nhóm KS-7 mà khai là máy sinh:\n" + "\n".join("  · " + s for s in sai)
        + "\n\n  Đây là số của người, hoặc là chỗ tiền đi qua — phải có cửa nhập tay hoặc cửa tải tệp.\n"
          "  Lưu ý khi đọc lý do ở trên: nếu chính lý do đã nói ra MÀN HÌNH nào ghi vào bảng này thì\n"
          "  bảng ấy CÓ cửa, chỉ là đang xếp nhầm ngăn. Sửa bằng cách chuyển dòng khai từ MAY_SINH\n"
          "  sang CUA_TAY kèm đúng màn hình đó — không phải bằng cách nới phép thử này.\n"
          "  Chủ: lane Viết phần mềm (chủ tệp app/services/ks_cua_nhap.py).")


def test_c3b_nam_nhom_bang_cua_lenh_ks7_deu_phai_co_cua():
    """Đếm riêng năm nhóm ấy, để báo cáo có số chứ không chỉ có kết luận."""
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    khong = set(b["khong_cua"])
    thieu = []
    for nhom, manh in NHOM_KS7.items():
        for t in sorted(khong):
            if any(m in t for m in manh):
                thieu.append(f"{t} (nhóm {nhom})")
    assert not thieu, (
        "bảng thuộc năm nhóm KS-7 không có cửa nào: " + ", ".join(thieu)
        + "\n  Chọn một trong ba: bộ nạp tệp (intake.BO_NAP kèm bang_dich), màn hình nhập tay khai "
          "vào CUA_TAY, hoặc MAY_SINH kèm lý do — nhưng C3 đã chặn MAY_SINH cho năm nhóm này.")


def test_c4_in_so_lieu_de_cham_diem():
    """Không khẳng định gì — in số để báo cáo, chạy với -s để xem."""
    from app.services import ks_cua_nhap as CN
    b = CN.bang()
    khai = _bang_khai_trong_tep_mo_hinh()
    print(f"\nKS-7 · {b['so_bang']} bảng trong mô hình · {len(khai)} bảng khai trong app/models "
          f"· {len(_bang_do_migration_tao())} bảng do migration tạo")
    print(f"    cửa tải tệp {len(b['co_cua_tep'])} · cửa nhập tay {len(b['co_cua_tay'])} "
          f"· máy sinh {len(b['may_sinh'])} · KHÔNG CỬA {len(b['khong_cua'])}")
    if b["khong_cua"]:
        print(f"    không cửa: {b['khong_cua']}")
    assert True
