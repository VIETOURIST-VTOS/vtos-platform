"""Chủ tịch toàn quyền – MỘT luật, và phép kiểm giữ cho nó không bị bỏ sót lần nữa.

QUYẾT ĐỊNH 06/9/2026: Chủ tịch HĐQT có toàn quyền chức năng trên mọi phân hệ. Nó được cài vào
`deps.FULL_ACCESS`, kèm một dòng chú thích nói rằng đặt ở "đúng một chỗ" thì "về sau không có endpoint
nào bị bỏ sót".

NGÀY 13/9/2026 CÂU ẤY HOÁ RA SAI, và sai theo đúng kiểu mà một hằng số hay sai. `FULL_ACCESS` chỉ được
đọc bên trong `require_roles`. Còn 43 chỗ khác trong kho tự viết `if u.role not in X: raise 403` ngay
trong thân hàm – không chỗ nào nhìn thấy nó.

Chủ tịch phát hiện khi mở tab “Quyết toán chi tiết” của một chuyến: màn hình báo “Vai trò của anh/chị
không khai được hình thức”. Cửa ghi thật sự VẪN MỞ cho ông – `require_roles(*NHAP)` cho qua nhờ
FULL_ACCESS – nhưng cái CỜ mà màn hình đọc để quyết định vẽ nút hay vẽ câu từ chối lại tự kiểm
`u.role in NHAP` bằng tay, ngay dưới một dòng chú thích tên là “MỘT NGUỒN SỰ THẬT VỀ QUYỀN NHẬP”.
Cửa mở, biển đề đóng. Người dùng tin biển.

PHÉP KIỂM TRẢ LỜI ĐÚNG MỘT CÂU: còn chỗ từ chối nào theo vai trò mà Chủ tịch bị chặn, và chỗ ấy chưa
được khai là CỐ Ý không?

BA CÁCH MỘT CHỖ TỪ CHỐI ĐƯỢC CHO QUA

  1. Gọi `toan_quyen(u)` trong chính điều kiện – cách đúng, và là cách bộ kiểm đọc được chắc chắn nhất.
  2. Danh sách vai trò của nó ĐÃ CÓ "chutich" – tra sống bằng cách nạp module rồi đọc tên. Không chép
     lại thành danh sách thứ hai: hôm nào ai đó bỏ "chutich" khỏi danh sách ấy thì bộ kiểm đỏ ngay.
  3. Khai vào GIU_DONG KÈM LÝ DO – dành cho cửa cố ý đóng với MỌI người, kể cả Chủ tịch.

VÌ SAO PHẢI CÓ (3), VÀ VÌ SAO NÓ KHÔNG PHẢI LỖ HỔNG

“Toàn quyền” là chuyện PHÂN QUYỀN: ai được làm việc gì. Có một loại cửa khác hẳn, gọi là TÁCH BẠCH
TRÁCH NHIỆM: việc này và việc kia phải do HAI NGƯỜI làm, bất kể hai người ấy to đến đâu. Người ký lệnh
chi và người bấm nút đã-chi mà là một người thì công ty mất lớp kiểm soát chống gian lận cổ điển nhất
đang có, và Ban Kiểm soát mất chỗ dựa để đối chiếu. Nới cửa ấy cho Chủ tịch không làm ông mạnh thêm –
nó làm chữ ký của ông rẻ đi, vì không còn ai đứng ngoài xác nhận.

Nên (3) bắt buộc có LÝ DO viết ra, y như `ks_cua_nhap.MAY_SINH`: “khai để cho qua” là lối thoát dễ
nhất, nên phải viết được vì sao thì mới khai được.

CHỖ BỘ KIỂM NÀY KHÔNG NHÌN THẤY – nói ra để không ai đọc xong rồi yên tâm quá mức:

  * Nó đọc ĐIỀU KIỆN của lệnh từ chối, không chạy thử. Một hàm phụ trợ nhận `u.role` rồi tự chặn bên
    trong thì điều kiện ở đây chỉ là một lời gọi hàm – bộ kiểm không đi vào trong được, nên nó đòi
    những chỗ ấy phải KHAI (xem `intake`, `attachments` dưới đây). Khai chứ không lờ đi.
  * Danh sách vai trò dựng lúc chạy từ cơ sở dữ liệu (`nd_vai_tro_ky_2(db)`) thì không tra tĩnh được,
    nên cũng phải khai.
  * Nó không kiểm MÀN HÌNH. Màn hình tự suy quyền rồi ẩn nút thì đây không thấy – đó đúng là lỗi
    13/9 ở phía cờ `nhap_duoc`, và chỗ gác nó là phép thử của từng màn hình.
"""
import ast
import importlib
import os

# Vai trò có toàn quyền. Đọc lại từ deps để không thành danh sách thứ hai.
from app.api.deps import FULL_ACCESS

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # …/app

# Lời từ chối. Chỉ những thứ này mới làm một khối `if` trở thành CỬA CHẶN.
LOI_TU_CHOI = ("HTTPException", "PermissionError", "Gate", "ValueError")


# ---------------------------------------------------------------------------------------------
# KHAI GIỮ ĐÓNG – cửa cố ý đóng với MỌI người, kể cả Chủ tịch.
#
# Khoá là (đường dẫn tệp từ app/, tên hàm) chứ KHÔNG phải số dòng: số dòng đổi mỗi lần ai đó thêm một
# dòng phía trên, và một danh sách tự sai sau mỗi lần sửa là danh sách không ai giữ.
# ---------------------------------------------------------------------------------------------
GIU_DONG: dict[tuple[str, str], str] = {

    # ---- TÁCH BẠCH TRÁCH NHIỆM: người ký và người chi phải là hai người ----
    ("services/ops.py", "step"):
        "Hai bước trong hàm này cố ý đóng với mọi vai trò: Kế toán KIỂM TRA chứng từ trước khi trình "
        "duyệt, và Kế toán bấm ĐÃ CHI sau khi có lệnh. Bước duyệt ngay giữa hai bước ấy chính là chữ "
        "ký của Chủ tịch. Một người vừa ký lệnh chi vừa xác nhận đã chi thì chữ ký đầu không còn ai "
        "đối chiếu – đây là lớp chống gian lận cổ điển nhất công ty đang có, và là chỗ dựa của Ban "
        "Kiểm soát. Nới cho Chủ tịch không làm ông mạnh thêm, nó làm chữ ký của ông rẻ đi.",

    ("services/tours.py", "kt_confirm"):
        "Kế toán xác nhận quyết toán – và chính con số được xác nhận ở bước này là căn cứ DUY NHẤT "
        "tính thưởng chuyến. Người duyệt chuyến mà tự xác nhận luôn số quyết toán của nó thì không "
        "còn ai đứng ngoài. Chủ tịch muốn số khác thì trả lại cho Điều hành soạn lại, không tự ký.",

    ("services/tours.py", "cntt_check"):
        "CNTT đối chiếu ĐỘC LẬP doanh thu booking với doanh thu quyết toán rồi khoá chuyến. Chữ "
        "“độc lập” là toàn bộ giá trị của bước này: nó có nghĩa là người đối chiếu không dính gì tới "
        "hai con số đang đối chiếu. Mở cho bất kỳ ai khác là xoá đúng cái chữ ấy.",

    ("services/settlement.py", "kt_return"):
        "Kế toán trả quyết toán về cho Điều hành soạn lại – mặt kia của kt_confirm. Giữ cùng lý do: "
        "nếu người duyệt vừa xác nhận được vừa trả lại được thì vòng quay quyết toán không còn một "
        "người thứ hai nào nhìn vào.",

    # ---- TÁCH BẠCH TRÁCH NHIỆM: một người không ký thay hai vai ----
    ("services/chu_ky.py", "kiem_tra_nguoi_ky"):
        "Bộ kiểm chữ ký nhiều vai dùng chung (Phụ lục 27/8/2026 mục 3.2). Cửa này sinh ra ĐÚNG ĐỂ "
        "chặn chuyện một người ký thay cả hai vai – ba dòng ngay dưới nó còn chặn cả người trình tự "
        "ký hồ sơ của mình. Cho toàn quyền đi vòng qua nó là phá đúng thứ nó được viết ra để giữ. "
        "Vai trò cần ký là tham số truyền vào nên cũng không tra tĩnh được.",

    ("services/marketing.py", "nd_duyet"):
        "Chữ ký THỨ HAI cho nội dung có cam kết với khách hoặc số liệu tài chính, và danh sách vai "
        "trò ký thứ hai dựng lúc chạy từ cơ sở dữ liệu nên không tra tĩnh được. Chữ ký thứ hai mà "
        "cùng một người ký thì không phải chữ ký thứ hai.",

    # ---- BẢO VỆ CHÍNH TÀI KHOẢN CHỦ TỊCH ----
    #
    # Ba cửa dưới đây trông như chúng chặn Chủ tịch, và đúng là chúng chặn. Nhưng thứ chúng chặn là
    # thao tác TRÊN TÀI KHOẢN LÃNH ĐẠO – đổi vai trò, đặt lại mật khẩu của chutich và tgd – và người
    # duy nhất làm được là CNTT. Mở ra cho Chủ tịch thì ai chiếm được phiên đăng nhập của ông cũng
    # tự đổi được mật khẩu lãnh đạo và giữ luôn quyền ấy. Cửa này bảo vệ ông, không hạn chế ông.
    ("api/v1/access.py", "role_change"):
        "Đổi vai trò của tài khoản lãnh đạo (chutich/tgd) – chỉ CNTT. Đây là chốt chống leo thang "
        "quyền: nếu chính tài khoản Chủ tịch tự đổi được vai trò lãnh đạo thì một phiên đăng nhập bị "
        "chiếm sẽ chiếm được luôn cả công ty. Giữ đóng là bảo vệ chủ tài khoản.",

    ("api/v1/hr.py", "update_user"):
        "Sửa hồ sơ tài khoản lãnh đạo – cùng lý do chống leo thang quyền như role_change.",

    ("api/v1/hr.py", "reset_password"):
        "Đặt lại mật khẩu tài khoản lãnh đạo – chỉ CNTT. Người tự đặt lại được mật khẩu của chính "
        "vai trò cao nhất thì không còn ai thu hồi được quyền ấy khi cần.",

    # ---- KHÔNG CHẶN CHỦ TỊCH, nhưng bộ kiểm không tự thấy được ----
    ("api/v1/intake.py", "nhap_mot_dong"):
        "Quyền nạp và quyền xác nhận số máy đọc từ ảnh nằm trong intake.duoc_nap() / "
        "duoc_xac_nhan_anh() – bộ kiểm không đi vào trong hàm phụ trợ được. Đã tra tay 13/9/2026: "
        "Chủ tịch nạp được cả 30/30 bộ nạp và xác nhận ảnh được, vì QUAN_TRI = (chutich, tgd, cntt) "
        "là giá trị mặc định của mọi bộ. (Chỉ CNTT bị loại khỏi cửa xác nhận ảnh, vì CNTT vận hành "
        "mô hình đọc ảnh thì không được tự xác nhận kết quả của nó – P5 08/9/2026.) Không chặn.",

    ("api/v1/intake.py", "nap"):
        "Cùng hai hàm phụ trợ duoc_nap() / duoc_nap_tep() như trên. Không chặn Chủ tịch.",

    ("api/v1/attachments.py", "tai_ve"):
        "Đọc tệp nhạy cảm, cùng danh sách AT.VAI_TRO_NHAY_CAM đã có “chutich”. Quyền nằm trong "
        "AT.duoc_doc() nên bộ kiểm không tra tĩnh được. Không chặn.",
}


# ---------------------------------------------------------------------------------------------
# Bộ đọc
# ---------------------------------------------------------------------------------------------
def _ten_module(duong_dan: str) -> str:
    return "app." + os.path.relpath(duong_dan, GOC)[:-3].replace(os.sep, ".")


def _tra(ten: ast.expr, mod) -> tuple[bool, object]:
    """Tra một tên (NHAP, AC.REQUEST_CREATE_ROLES) ra giá trị thật. (tra_được, giá_trị)."""
    if isinstance(ten, (ast.Tuple, ast.List, ast.Set)):
        try:
            return True, ast.literal_eval(ten)
        except (ValueError, TypeError, SyntaxError):
            return False, None
    if isinstance(ten, ast.Constant):
        return True, ten.value
    if isinstance(ten, ast.Name):
        return (True, getattr(mod, ten.id)) if hasattr(mod, ten.id) else (False, None)
    if isinstance(ten, ast.Attribute):
        goc, duoi = ten.value, ten.attr
        if isinstance(goc, ast.Name) and hasattr(mod, goc.id):
            o = getattr(mod, goc.id)
            return (True, getattr(o, duoi)) if hasattr(o, duoi) else (False, None)
    return False, None


def _la_u_role(n: ast.expr) -> bool:
    return isinstance(n, ast.Attribute) and n.attr == "role" and isinstance(n.value, ast.Name)


def _phep_so_vai_tro(dieu_kien: ast.expr) -> list[ast.Compare]:
    """Mọi phép so sánh có vế là <ai đó>.role."""
    ra = []
    for n in ast.walk(dieu_kien):
        if isinstance(n, ast.Compare) and (_la_u_role(n.left)
                                           or any(_la_u_role(c) for c in n.comparators)):
            ra.append(n)
    return ra


def _role_di_vao_loi_goi(dieu_kien: ast.expr) -> bool:
    """u.role bị truyền vào một hàm khác – quyền nằm trong hàm ấy, đọc từ đây không thấy."""
    for n in ast.walk(dieu_kien):
        if isinstance(n, ast.Call) and any(_la_u_role(a) for a in n.args):
            return True
    return False


def _chan_chu_tich(so: ast.Compare, mod) -> bool | None:
    """Phép so sánh này, với role = "chutich", có cho ra KẾT QUẢ TỪ CHỐI không?

    None = không tra được danh sách, phải khai.
    """
    if len(so.ops) != 1 or len(so.comparators) != 1:
        return None
    op, ve_kia = so.ops[0], so.comparators[0]
    if not _la_u_role(so.left):                 # dạng "chutich" == u.role – hiếm, đảo lại
        if _la_u_role(ve_kia):
            ve_kia = so.left
        else:
            return None
    duoc, gia_tri = _tra(ve_kia, mod)
    if not duoc:
        return None
    cho_moi = FULL_ACCESS[0]
    try:
        if isinstance(op, ast.NotIn):
            return cho_moi not in gia_tri       # not in ⇒ True nghĩa là bị từ chối
        if isinstance(op, ast.In):
            return cho_moi in gia_tri
        if isinstance(op, ast.NotEq):
            return cho_moi != gia_tri
        if isinstance(op, ast.Eq):
            return cho_moi == gia_tri
    except TypeError:
        return None
    return None


def _ham_bao(cay: ast.Module, dong: int) -> str:
    """Tên hàm chứa dòng này – khoá của GIU_DONG, bền hơn số dòng."""
    ten = ""
    for n in ast.walk(cay):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= dong <= (n.end_lineno or n.lineno):
                ten = n.name
    return ten


def _co_loi_tu_choi(than: list[ast.stmt]) -> bool:
    for n in ast.walk(ast.Module(body=than, type_ignores=[])):
        if isinstance(n, ast.Raise) and n.exc is not None:
            e = n.exc
            f = e.func if isinstance(e, ast.Call) else e
            ten = getattr(f, "id", None) or getattr(f, "attr", None)
            if ten not in LOI_TU_CHOI:
                continue
            if ten == "HTTPException" and isinstance(e, ast.Call) and e.args:
                a = e.args[0]
                if isinstance(a, ast.Constant) and a.value != 403:
                    continue
                if isinstance(a, ast.Attribute) and "403" not in ast.unparse(a):
                    continue
            return True
    return False


def bang() -> dict:
    """{'chan': [...], 'khai_thua': [...], 'so_cua': n} – 'chan' rỗng là điều phải giữ."""
    chan, thay = [], set()
    for thu_muc, _, tep in os.walk(GOC):
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            p = os.path.join(thu_muc, t)
            rel = os.path.relpath(p, GOC).replace(os.sep, "/")
            try:
                cay = ast.parse(open(p, encoding="utf-8").read())
            except SyntaxError:
                continue
            mod = None
            for n in ast.walk(cay):
                if not isinstance(n, ast.If) or not _co_loi_tu_choi(n.body):
                    continue
                dk = n.test
                chu = ast.unparse(dk)
                if "toan_quyen" in chu or "FULL_ACCESS" in chu:
                    continue                                   # cách (1)
                so = _phep_so_vai_tro(dk)
                qua_loi_goi = _role_di_vao_loi_goi(dk)
                if not so and not qua_loi_goi:
                    continue                                   # không phải cửa theo vai trò
                if mod is None:
                    try:
                        mod = importlib.import_module(_ten_module(p))
                    except Exception:                          # noqa – tệp không nạp được thì tra tay
                        mod = object()
                ket = [_chan_chu_tich(s, mod) for s in so]
                if not qua_loi_goi and ket and all(k is False for k in ket):
                    continue                                   # cách (2): danh sách đã có Chủ tịch
                ham = _ham_bao(cay, n.lineno)
                khoa = (rel, ham)
                thay.add(khoa)
                if khoa in GIU_DONG:
                    continue                                   # cách (3)
                chan.append({"tep": rel, "ham": ham, "dong": n.lineno, "dieu_kien": chu[:160]})
    return {"chan": chan, "so_cua": len(thay),
            "khai_thua": sorted(f"{a}::{b}" for a, b in set(GIU_DONG) - thay)}
