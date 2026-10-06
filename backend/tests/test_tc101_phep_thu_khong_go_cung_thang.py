"""TC-101 · PHÉP THỬ KHÔNG ĐƯỢC GÕ CỨNG THÁNG VÀO MÃ CHỨNG TỪ — 06/10/2026.

Sáng 06/10/2026 ba tệp phép thử Kế toán đỏ cùng lúc: test_accounting, test_payments, test_reports.
Cả ba cùng một kiểu hỏng — `StopIteration` khi đi tìm một booking hoặc một phiếu thu. Mã nguồn
KHÔNG đổi giữa lần xanh cuối (29/9) và lần đỏ; thứ đổi là tờ lịch.

Nguyên nhân: `services/seed.py` dựng mã booking bằng `f"BK{today:%y%m}{n:04d}"` — mã mang THÁNG
HIỆN TẠI. Ba tệp ấy gõ cứng mã của tháng 9 ("BK26090001"). Sang tháng 10, bộ dữ liệu thử sinh ra
BK2610xxxx, phép thử vẫn đi tìm BK2609xxxx, không thấy, và nổ.

VÌ SAO ĐÁNG MỘT HÀNG RÀO RIÊNG, CHỨ KHÔNG CHỈ SỬA BA TỆP KIA:

  Chỗ nguy hiểm không phải là nó đỏ. Nó đỏ ĐỀU ĐẶN mỗi đầu tháng, không ai đụng vào mã nguồn, và
  lần nào cũng "sửa một tí là xanh". Một hàng rào tháng nào cũng đỏ là một hàng rào người ta thôi
  đọc — rồi đúng hôm nó đỏ vì chuyện thật thì không còn ai nhìn nữa. Lỗi kiểu này phải chặn ở chỗ
  nó sinh ra, không phải dọn lại mỗi tháng.

VÀ MỘT LỜI TỰ ĐÍNH CHÍNH, ghi lại để không ai đi lại đường ấy: khi mới thấy ba tệp đỏ, tôi đọc
thông điệp lỗi ("không tìm thấy phiếu thu trạng thái tu_dong") rồi kết luận robot đối chiếu SePay
đã thôi tự khớp, tức là tiền khách nộp thật cũng sắp không khớp. KẾT LUẬN ẤY SAI, và nó sai vì
tôi suy từ thông điệp lỗi mà chưa dựng lại hiện tượng. Dựng lại mất đúng một lượt chạy: in ra mã
booking mà bộ dữ liệu thử sinh được. Robot SePay không hỏng một chút nào.
"""
import ast
import os
import pathlib
import re

THU_MUC = pathlib.Path(__file__).resolve().parent

# Mã chứng từ nào mang %y%m thì tiền tố của nó nằm ở đây. Thêm tiền tố mới vào cùng lúc với việc
# thêm hàm sinh mã, nếu không hàng rào này canh hụt đúng cái vừa thêm.
#   BK  bookings.py / seed.py   ·  BL  giữ chỗ  ·  NV  nghĩa vụ  ·  KN  khiếu nại
#   DC  điều chuyển             ·  HD  hợp đồng ·  SC  sự cố     ·  CD/ND  marketing
TIEN_TO = ("BK", "BL", "NV", "KN", "DC", "HD", "SC", "CD", "ND")
# BK26090001 (8 chữ số liền) hoặc BL2609-0001 / NV2609-00001 (có gạch nối).
GO_CUNG = re.compile(r"\b(" + "|".join(TIEN_TO) + r")\d{4}-?\d{3,5}\b")


def _chuoi_that(ma_nguon: str):
    """Mọi chuỗi TRONG MÃ, bỏ chú thích và bỏ docstring.

    Bài học TC-93: một hàng rào cấm chuỗi rồi quét cả tệp sẽ bắt luôn đoạn giải thích vì sao chuỗi
    ấy bị cấm — kể cả đoạn ngay trên đầu tệp này.
    """
    cay = ast.parse(ma_nguon)
    la_docstring = set()
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            than = nut.body
            if (than and isinstance(than[0], ast.Expr)
                    and isinstance(than[0].value, ast.Constant)
                    and isinstance(than[0].value.value, str)):
                la_docstring.add(id(than[0].value))
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Constant) and isinstance(nut.value, str)
                and id(nut) not in la_docstring):
            yield getattr(nut, "lineno", 0), nut.value


def test_khong_tep_phep_thu_nao_go_cung_thang_vao_ma_chung_tu():
    vi_pham = []
    for tep in sorted(THU_MUC.glob("test_*.py")):
        if tep.name == os.path.basename(__file__):
            continue
        for dong, chuoi in _chuoi_that(tep.read_text(encoding="utf-8")):
            for m in GO_CUNG.finditer(chuoi):
                vi_pham.append(f"{tep.name}:{dong} → {m.group(0)}")
    assert not vi_pham, (
        "Mã chứng từ gõ cứng tháng trong phép thử. Mã sinh theo THÁNG HIỆN TẠI, nên dòng này sẽ đỏ "
        "vào đầu tháng sau mà không ai đụng vào mã nguồn. Suy mã từ date.today() bằng đúng công "
        "thức của hàm sinh mã (xem services/seed.py). Các chỗ đang vi phạm: " + "; ".join(vi_pham))


def test_hang_rao_bat_duoc_ban_cu():
    """Tự kiểm: đưa đúng những dòng của bản trước 06/10 vào thì hàng rào trên PHẢI bắt."""
    cu = '''
b = booking("BK26090001")
p = {"content": "NGUYEN VAN A CK BK26090001 tour phan thiet"}
'''
    bat = [m.group(0) for _, s in _chuoi_that(cu) for m in GO_CUNG.finditer(s)]
    assert bat == ["BK26090001", "BK26090001"], f"hàng rào không bắt được bản cũ, chỉ thấy {bat}"


def test_hang_rao_khong_bat_nham_docstring_va_chu_thich():
    """Tự kiểm chiều ngược: lời khai được nhắc tới mã cũ mà không bị coi là vi phạm."""
    lanh = '''
"""Tệp này từng gõ cứng BK26090001 và đã bỏ."""
# Trước đây là BK26090002.
ma = f"BK{nam_thang}{n:04d}"
'''
    assert not [m.group(0) for _, s in _chuoi_that(lanh) for m in GO_CUNG.finditer(s)]


def test_ba_tep_ke_toan_suy_ma_bang_DUNG_cong_thuc_cua_seed():
    """Suy mã là chưa đủ — phải suy bằng ĐÚNG công thức seed dùng, không phải một công thức na ná.

    So thẳng với chuỗi định dạng trong services/seed.py. Mai kia seed đổi cách dựng mã thì hàng rào
    này đỏ, và đỏ đúng chỗ: ba tệp kia đang đoán mã của người khác sinh ra.
    """
    goc = THU_MUC.parent.parent
    seed = (goc / "backend" / "app" / "services" / "seed.py").read_text(encoding="utf-8")
    cong_thuc = re.search(r'f"BK\{today:%y%m\}\{[^}]+\}"', seed)
    assert cong_thuc, "không còn tìm thấy công thức dựng mã booking trong services/seed.py"

    for ten in ("test_payments.py", "test_accounting.py", "test_reports.py"):
        ma_nguon = (THU_MUC / ten).read_text(encoding="utf-8")
        assert "def ma_bk(" in ma_nguon, f"{ten} chưa có hàm suy mã booking"
        assert 'return f"BK{date.today():%y%m}{n:04d}"' in ma_nguon, (
            f"{ten}: công thức suy mã lệch với services/seed.py "
            f"(seed đang dùng {cong_thuc.group(0)})")


def test_ba_tep_ke_toan_khong_con_go_cung_ma_nao():
    """Canh riêng ba tệp đã vá, để nếu ai đó thêm lại một dòng gõ cứng thì thấy ngay tên tệp."""
    for ten in ("test_payments.py", "test_accounting.py", "test_reports.py"):
        sai = [f"dòng {d}: {m.group(0)}"
               for d, c in _chuoi_that((THU_MUC / ten).read_text(encoding="utf-8"))
               for m in GO_CUNG.finditer(c)]
        assert not sai, f"{ten} gõ cứng mã lại: {'; '.join(sai)}"
