# -*- coding: utf-8 -*-
"""Đợt QUY-2b 05/11/2026 — KHỐI «SỔ QUỸ TIỀN MẶT» TRÊN MÀN `/collections`.

Chủ tịch chốt 02/11/2026: tiền mặt vào sổ bằng CẢ HAI CỬA. Đợt QUY-1 làm cửa máy chủ, Đợt QUY-2a
làm cửa tải lô, và đợt này làm chỗ NGƯỜI THỦ QUỸ thật sự ngồi: khối nhập tay trên màn hình.

MÀN HÌNH KHÔNG CHỌN MỘT CẶP TÀI KHOẢN NÀO, và luật 4 canh đúng điều đó. Nó gửi lý do người lập
chọn; bảng quy ước trên máy chủ quyết định ghi Nợ/Có vào đâu. Một màn hình tự biết «nộp quỹ thì
1121/1111» là chỗ thứ hai giữ quy ước kế toán — và chỗ thứ hai thì sớm muộn cũng lệch với chỗ
thứ nhất, lặng lẽ, cho tới ngày có người đối chiếu.

Ô «Lý do» ĐỌC SỐNG từ cửa `/receipts/quy/ly-do`: thêm một quy tắc hạch toán là một lý do mới tự
hiện ra ở ô chọn, không ai phải sửa màn hình. Đó là lý do đợt này không chép một danh sách lý do
nào vào `page.tsx`.

LUẬT 2 LÀ LUẬT ĐẮT NHẤT, và nó là bài học R4c-4 viết lại cho đợt này: màn hình và cửa máy chủ
phải nói CÙNG MỘT CÂU về việc ai được bấm. Gõ rời hai chỗ thì sửa một bên quên bên kia — và lúc
ấy nút hiện ra để bấm vào nhận 403, hoặc biến mất với người vẫn còn quyền. Luật này đọc CẢ HAI
chỗ rồi so, chứ không tin một lời hứa trong ghi chú.
"""
import ast
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_quy2b.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _f in ("test_quy2b.db", "test_quy2b.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(GOC, "web", "app", "collections", "page.tsx")
API_PQ = os.path.join(GOC, "backend", "app", "api", "v1", "payments.py")


def _man() -> str:
    assert os.path.exists(MAN), "khong thay web/app/collections/page.tsx"
    return open(MAN, encoding="utf-8").read()


def _khong_ghi_chu(s: str) -> str:
    """Bỏ ghi chú `//` và `/* */` — những đoạn giải thích CÓ nhắc 1111/1121 để nói với người đọc."""
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return "\n".join(d for d in s.split("\n") if not d.strip().startswith("//"))


def _vai_cua_may_chu(ten_ham: str) -> list[str]:
    """Bộ vai cửa máy chủ nhận, đọc bằng CÂY CÚ PHÁP chứ không bằng soi chuỗi.

    Soi chuỗi thì một cách viết khác — xuống dòng, đổi thứ tự, gọi qua một biến — là lọt. Đọc cây
    thì chỉ lọt khi người ta thật sự khai bằng một đường khác, và lúc ấy đỏ là đúng.
    """
    cay = ast.parse(open(API_PQ, encoding="utf-8").read())
    for n in ast.walk(cay):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name != ten_ham:
            continue
        # `require_roles(...)` nằm trong giá trị mặc định `Depends(require_roles(...))`, tức là
        # trong `n.args` — đi hết cây con ấy là thấy, dù người viết xuống dòng kiểu nào.
        for m in ast.walk(n.args):
            if (isinstance(m, ast.Call) and isinstance(m.func, ast.Name)
                    and m.func.id == "require_roles"):
                return [c.value for c in m.args if isinstance(c, ast.Constant)]
    raise AssertionError(f"khong tim thay `require_roles` cua ham `{ten_ham}` trong payments.py")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 1
def test_quy2b_1_khoi_so_quy_co_tren_man_hinh():
    """Ranh giới Chủ tịch ký 09/9/2026: mỗi con số phải có một cửa cho NGƯỜI DÙNG.

    Đợt QUY-1 mở cửa máy chủ, nhưng thủ quỹ không gọi HTTP — họ ngồi trước màn hình. Không có khối
    này thì cửa kia vẫn là việc còn thiếu.
    """
    s = _man()
    assert "Sổ quỹ tiền mặt" in s, "màn /collections chưa có khối «Sổ quỹ tiền mặt»"
    for can in ("lapPhieuQuy", "VAI_SO_QUY", "quyLyDo"):
        assert can in s, f"khối Sổ quỹ thiếu `{can}`"
    assert s.count("const VAI_SO_QUY") == 1, "bộ vai khối Sổ quỹ khai nhiều hơn một chỗ"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 2
def test_quy2b_2_man_hinh_va_may_chu_noi_CUNG_MOT_CAU_ve_ai_duoc_bam():
    """LUẬT ĐẮT NHẤT CỦA ĐỢT — bài học Đợt R4c-4 viết lại.

    Đọc bộ vai ở `page.tsx` và bộ vai `require_roles` của `lap_phieu_quy` trong `payments.py`, rồi
    so. Lệch một vai là một trong hai chuyện: nút hiện ra để bấm vào nhận 403, hoặc nút biến mất
    với người vẫn còn quyền. Cả hai đều chỉ lộ ra khi có người thật đi làm thật.
    """
    s = _man()
    m = re.search(r"const VAI_SO_QUY\s*=\s*\[([^\]]*)\]", s)
    assert m, "không đọc được hằng số VAI_SO_QUY trong page.tsx"
    man = sorted(re.findall(r'"([^"]+)"', m.group(1)))
    may_chu = sorted(_vai_cua_may_chu("lap_phieu_quy"))
    assert man == may_chu, (
        f"màn hình gác {man} còn cửa máy chủ nhận {may_chu} — hai chỗ đang nói hai câu khác nhau")
    assert man, "bộ vai rỗng: khối Sổ quỹ hiện ra với tất cả mọi người"


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 3
def test_quy2b_3_moi_duong_khoi_nay_goi_deu_CO_THAT_tren_may_chu():
    """Đường gọi sai không đỏ ở đâu cả — nó chỉ im lặng trả 404 lúc người dùng bấm.

    Đo đúng những đường của đợt này (`/receipts/quy/...`): lấy từ `page.tsx` rồi đối chiếu với
    bảng đường THẬT của FastAPI, không phải với một danh sách chép tay.

    Chính cái bẫy này làm hỏng Đợt R4c-3: màn hình gọi `api("/hach-toan/bang")` — một đường không
    có trên máy chủ — và không gì kêu lên cho tới khi ô «hình thức thanh toán» rỗng trên bản chạy.
    """
    from app.main import app
    co_that = {getattr(r, "path", "") for r in app.routes}
    goi = set(re.findall(r'api\(\s*[`"\']((?:/receipts/quy)[^`"\'?]*)', _man()))
    assert goi, "khối Sổ quỹ không gọi một đường `/receipts/quy/...` nào — nó đang lấy số ở đâu?"
    thieu = sorted(d for d in goi if f"/api/v1{d}" not in co_that)
    assert not thieu, (
        f"màn hình gọi những đường KHÔNG CÓ trên máy chủ: {thieu}. "
        "Người dùng sẽ bấm và nhận 404, mà không phép thử nào khác kêu lên.")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 4
def test_quy2b_4_man_hinh_KHONG_chon_mot_cap_tai_khoan_nao():
    """Cả chuỗi QUY không gõ cứng tài khoản — màn hình cũng vậy, và ở đây nó dễ sai nhất.

    Một màn hình tự biết «nộp quỹ thì 1121/1111» là chỗ THỨ HAI giữ quy ước kế toán. Chỗ thứ hai
    sớm muộn cũng lệch với chỗ thứ nhất, lặng lẽ, cho tới ngày có người đối chiếu.

    Bỏ ghi chú trước khi tìm: những đoạn giải thích CÓ nhắc số hiệu tài khoản để nói với người đọc,
    và một phép đo đếm cả ghi chú thì buộc người viết phải giải thích ít đi.
    """
    ma = _khong_ghi_chu(_man())
    thay = re.findall(r'"1(?:11|12)\d?"|\b1111\b|\b1121\b', ma)
    assert not thay, (
        f"màn hình gõ cứng tài khoản tiền {sorted(set(thay))} — nó phải gửi LÝ DO và để bảng quy "
        "ước chọn cặp tài khoản")
    assert "quyLyDo" in ma and "/receipts/quy/ly-do" in ma, (
        "ô «Lý do» không đọc sống từ cửa `/receipts/quy/ly-do` — nếu nó chép một danh sách cứng "
        "thì thêm một quy tắc hạch toán sẽ phải sửa màn hình, và sớm muộn hai chỗ lệch nhau")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 5
def test_quy2b_5_co_loi_sang_cua_TAI_LO():
    """Hai cửa phải nhìn thấy nhau. Thủ quỹ cầm cả quyển sổ giấy mà chỉ thấy ô gõ từng dòng thì
    họ gõ tay hai trăm dòng — rồi đến dòng thứ năm mươi là bắt đầu sai."""
    s = _man()
    assert "/nap-du-lieu" in s, "khối Sổ quỹ không có lối sang trang Nạp dữ liệu (cửa tải lô)"
    assert os.path.isdir(os.path.join(GOC, "web", "app", "nap-du-lieu")), (
        "đường /nap-du-lieu không có màn hình nào — lối dẫn sang một trang không tồn tại")


# ───────────────────────────────────────────────────────────────────────────────────────── LUẬT 6
def test_quy2b_6_thu_quy_mo_duoc_man_hinh_nay():
    """Khối gác đúng vai mà màn hình lại không cấp cho vai ấy thì họ không vào nổi để thấy khối.

    `access.MAN_HINH_THU_QUY` cấp `/collections` cho `thu_quy` từ Đợt E2b-0; luật này chỉ đo lại,
    vì đợt này dựa vào điều đó và KHÔNG nới thêm một quyền nào.
    """
    from app.services import access as AC
    m = re.search(r"const VAI_SO_QUY\s*=\s*\[([^\]]*)\]", _man())
    vai = re.findall(r'"([^"]+)"', m.group(1))
    mr = getattr(AC, "MENU_ROLES", None)
    assert mr, "access.py khong con MENU_ROLES — bang cap man hinh da doi, do lai"
    # Tra theo khoa CHUA chu "collections" chu khong go cung mot dang khoa: bang nay doi dang
    # khoa thi mot phep do go cung se do oan, va do oan thi nguoi doc mat long tin vao ca tep.
    cap = next((v for k, v in mr.items() if "collections" in str(k)), None)
    assert cap is not None, "MENU_ROLES khong co dong nao cho man /collections — do lai"
    for v in vai:
        assert v in cap, (
            f"vai `{v}` KHÔNG được cấp màn /collections trong MENU_ROLES — họ gác được khối "
            "nhưng không vào nổi trang để thấy nó")
