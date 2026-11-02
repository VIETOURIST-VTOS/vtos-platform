# -*- coding: utf-8 -*-
"""HAI BẢNG QUYỀN PHẢI KHỚP NHAU — hàng rào chung, Đợt LG1.

──────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO TỆP NÀY TỒN TẠI
──────────────────────────────────────────────────────────────────────────────────────────────

Hệ thống có HAI hàng rào quyền, và chúng rời nhau:

  · hàng rào NGOÀI — `MENU_ROLES` → `MAN_HINH_API`: ai MỞ được màn hình
  · hàng rào TRONG — `require_roles` trên từng cửa: ai GỌI được cửa

Lệch nhau thì ra "cửa mở, biển đề đóng": người mở được màn hình, bấm vào nhận 403, và không biết
mình thiếu quyền hay hệ thống hỏng. Hình ấy đã xảy ra BA LẦN và được ghi vào sổ mỗi lần:

  13/9/2026   Chủ tịch mở tab Quyết toán chi tiết: cửa ghi VẪN MỞ nhờ `FULL_ACCESS`, nhưng CỜ mà
              màn hình đọc để vẽ nút lại tự kiểm `u.role in NHAP` bằng tay.
  10/10/2026  Ba vai kế toán mới thấy `/ket-so` trong menu mà `XEM` của `hach_toan.py` không có.
  10/10/2026  Đợt E2b suy bảng MÀN HÌNH từ `ketoan` nhưng KHÔNG suy bảng CỬA — **29 cặp** mở menu
              mà bấm vào là 403, và chỉ **4 cặp** có hàng rào bắt được.

Lần thứ ba là nặng nhất vì nó im lặng: 25 cặp không phép thử nào nhìn thấy. Trước tệp này, chỗ
duy nhất trong kho so hai bảng là `test_tc100` — và nó chỉ so cho ĐÚNG MỘT màn hình, `/tai-xe`.

Tệp này hỏi câu ấy cho MỌI màn hình × MỌI vai, một lượt.

──────────────────────────────────────────────────────────────────────────────────────────────
PHẠM VI: ĐỎ với ba vai mới, ĐẾM phần còn lại — Chủ tịch chốt 11/10/2026
──────────────────────────────────────────────────────────────────────────────────────────────

Lượt đo đầu tiên ra 56 cặp lệch: 29 của Đợt E2b và 27 có sẵn từ trước, thuộc `robot_ks` (18),
`sales_admin` (8) và `tp_dh` (1). Bắt đỏ cả 56 thì làn Phân quyền phải đi sửa quyền của ba làn
khác, và mỗi vai là một quyết định nghiệp vụ nữa phải chờ ký.

Nên: 29 cặp của E2b phải BẰNG KHÔNG, còn 27 cặp kia khai thành `DA_BIET` — đếm được, có tên, và
**không được dài thêm**. `test_lg4` canh đúng điều đó. Danh sách này là một món NỢ có sổ, không
phải một ngoại lệ được tha.
"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_lg1.db"
os.environ["SEED_DEMO"] = "0"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
if os.path.exists("test_lg1.db"):
    os.remove("test_lg1.db")

import re  # noqa: E402

from app.main import app  # noqa: E402
from app.services import access as AC  # noqa: E402
from app.services import vai_ke_thua as VKT  # noqa: E402

# Vai mà Đợt E2b mở ra. Ba vai này phải KHÔNG có một cặp lệch nào.
VAI_E2B = ("ketoan_truong", "ketoan_tt", "thu_quy")

# Chủ tịch đi qua mọi cửa bằng `FULL_ACCESS` (luật 06/9/2026), nên cặp của ông không bao giờ lệch.
BO_QUA_VAI = ("chutich",)

# ─────────────────────────────────────────────────────────────────────────────────────────────
# MÓN NỢ CÓ SỔ — 27 cặp đã lệch TRƯỚC Đợt E2b, đo 11/10/2026
# ─────────────────────────────────────────────────────────────────────────────────────────────
#
# `robot_ks` (18) — robot Kiểm soát được khai vào menu của gần như mọi màn hình để "nhìn thấy
#   hết", nhưng nó đọc qua API riêng chứ không mở màn hình. Có thể đây là khai thừa chứ không
#   phải thiếu quyền; quyết định thuộc làn Kiểm soát.
# `sales_admin` (8) — vai Sale Admin mở thêm màn hình ngày 29/9 mà cửa chưa theo. Thuộc làn Bán hàng.
# `tp_dh` (1) — `/vietrip`: Trưởng phòng Điều hành thấy menu mà cửa nạp dữ liệu chỉ cho Kế toán.
#
# BA LÀN KHÁC, nên làn Phân quyền KHÔNG tự sửa. Việc của danh sách này là làm món nợ ĐẾM ĐƯỢC và
# không cho nó dài thêm — thêm một cặp mới là `test_lg4` đỏ, và người thêm phải nói vì sao.
DA_BIET = (
    ("/ai-roles", "robot_ks"),
    ("/bang-gia", "robot_ks"),
    ("/bao-gia", "robot_ks"),
    # ("/bao-gia", "sales_admin") và ("/hop-dong-khach", "sales_admin") — GẠCH 02/11/2026, TR-1d: Sale Admin
    #   được mở BA cửa đọc của `/api/v1/ban-hang` (danh sách hợp đồng, lịch thanh toán, link thanh toán) để tạo
    #   link theo đợt. `/bao-gia` gạch theo vì phép đo này xét theo TIỀN TỐ dùng chung — thực tế cửa đọc
    #   BÁO GIÁ (`XEM`) vẫn chưa có Sale Admin; màn hình /hop-dong-khach thì nay chạy thật.
    ("/cham-soc", "robot_ks"),
    ("/cong-no", "robot_ks"),
    ("/cong-no", "sales_admin"),
    ("/doi-xe", "robot_ks"),
    # ("/hach-toan", "robot_ks") và ("/ket-so", "robot_ks") — GẠCH 02/11/2026, SUA-2: cửa đọc mới
    #   `GET /api/v1/hach-toan/bang` (danh mục hình thức thanh toán) mở cho nhóm vai đề nghị chi, trong đó có
    #   robot_ks; phép đo xét theo TIỀN TỐ `/api/v1/hach-toan` nên hai cặp này hết lệch.
    ("/hieu-qua-doi-xe", "robot_ks"),
    ("/hop-dong-khach", "robot_ks"),
    ("/ir-phap-che", "robot_ks"),
    ("/lai-lo-doi-xe", "robot_ks"),
    ("/lai-lo-tour", "robot_ks"),
    ("/lai-lo-tour", "sales_admin"),
    # ("/lenh-dieu-xe", "robot_ks") — MÓN NỢ ĐÃ TRẢ ngày 11/10/2026, DL-1.
    #
    # Trả được KHÔNG phải vì làn Phân quyền đi sửa quyền của làn Kiểm soát, mà vì cửa đề nghị xe
    # mới suy `XEM` TỪ `MENU_ROLES["/lenh-dieu-xe"]` thay vì gõ lại danh sách — và `robot_ks` có
    # trong bảng menu nên nó vào thẳng nhóm xem. Một phép suy có tên trả luôn một cặp lệch.
    ("/nap-du-lieu", "robot_ks"),
    ("/nap-du-lieu", "sales_admin"),
    ("/nguoi-ban-hang", "sales_admin"),
    ("/robot-reports", "robot_ks"),
    ("/tep", "sales_admin"),
    ("/to-chuc-kd", "sales_admin"),
    ("/vietrip", "robot_ks"),
    ("/vietrip", "tp_dh"),
    ("/visa", "robot_ks"),
)

LUONG_RE = re.compile(r"payroll|luong|bhxh|thu-nhap|employee|hrm|cap-phat|chat-luong|dung-luong", re.I)


def _cua():
    """(đường dẫn, tập vai) của mọi cửa — đọc TỪ CHỮ KÝ qua `vai_tro_yeu_cau`, không phân tích mã.

    `None` nghĩa là cửa không khai vai: mọi người đã đăng nhập đều gọi được.
    """
    ra = []
    for r in app.routes:
        p = getattr(r, "path", "")
        if not p.startswith("/api/v1"):
            continue
        vai = None
        for d in (getattr(getattr(r, "dependant", None), "dependencies", None) or []):
            v = getattr(getattr(d, "call", None), "vai_tro_yeu_cau", None)
            if v:
                vai = set(v)
        ra.append((p, vai, sorted(getattr(r, "methods", {"?"}))[0]))
    return ra


def _lech():
    """Cặp (màn hình, vai): mở được màn hình mà KHÔNG gọi được một cửa nào của nó."""
    cua = _cua()
    ra = []
    for man, vais in AC.MENU_ROLES.items():
        tien_to = AC.MAN_HINH_API.get(man, ())
        if not tien_to:
            continue
        cua_man = [(p, v) for p, v, _ in cua if any(p.startswith(t) for t in tien_to)]
        if not cua_man:
            continue                      # màn hình chưa có cửa nào: việc khác, không phải việc này
        for vai in vais:
            if vai in BO_QUA_VAI:
                continue
            if not any(v is None or vai in v for _, v in cua_man):
                ra.append((man, vai))
    return ra


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Luật chính
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg1_ba_vai_cua_E2b_khong_con_mot_cap_lech_nao():
    """Đỏ ở đây nghĩa là một vai mở được màn hình mà bấm vào nhận 403.

    Cách xử KHÔNG phải sửa phép thử này. Hai chiều, và phải chọn một:
      · vai ấy ĐÚNG là nên xem màn hình → mở cửa cho nó (hoặc cho vai cha, nếu có kế thừa);
      · vai ấy KHÔNG nên thấy màn hình → bỏ khỏi `MENU_ROLES`, sửa XUỐNG.
    """
    xau = [x for x in _lech() if x[1] in VAI_E2B]
    assert not xau, (
        "Ba vai cua Dot E2b lai co cap lech - mot vai mo duoc man hinh ma bam vao la 403:\n"
        + "\n".join(f"   . {m} x {v}" for m, v in sorted(xau)))


def test_lg2_phep_suy_vai_ke_thua_duoc_CA_HAI_bang_doc():
    """Chỗ hỏng của E2b là suy MỘT BÊN. Phép thử này canh đúng chỗ ấy, không canh hậu quả.

    Với mọi màn hình mà vai CHA mở được, vai CON cũng phải mở được (bảng màn hình), VÀ phải gọi
    được ít nhất một cửa (bảng cửa). Thiếu một trong hai là hai bảng đã rời nhau trở lại.
    """
    cua = _cua()
    for con, cha in VKT.VAI_KE_THUA.items():
        thieu_menu = [m for m, v in AC.MENU_ROLES.items() if cha in v and con not in v]
        assert not thieu_menu, f"{con} khong ke thua man hinh cua {cha}: {sorted(thieu_menu)[:8]}"
        thieu_cua = [p for p, v, _ in cua if v and cha in v and con not in v]
        assert not thieu_cua, (
            f"{con} khong ke thua CUA cua {cha} o {len(thieu_cua)} cho, vi du: {sorted(thieu_cua)[:5]}")


def test_lg3_vai_HEP_khong_ke_thua():
    """`ketoan_tt` và `thu_quy` là vai HẸP — chuyển khoản và tiền mặt. Cho chúng kế thừa `ketoan`
    là xoá mất chính việc tách vai của Đợt E2b, và xoá bằng một dòng mà không ai thấy."""
    for v in ("ketoan_tt", "thu_quy"):
        assert v not in VKT.VAI_KE_THUA, (
            f"`{v}` vua duoc cho ke thua. Day la vai HEP - tach vai cua E2b se mat.")


def test_lg4_mon_no_khong_duoc_DAI_THEM():
    """27 cặp có sẵn của ba làn khác. Danh sách này là một món NỢ CÓ SỔ, không phải ngoại lệ được tha.

    Đỏ theo hai chiều, và cả hai đều đáng:
      · có cặp lệch MỚI không nằm trong sổ → ai đó vừa mở một menu mà quên mở cửa;
      · có dòng trong sổ mà thực tế KHÔNG còn lệch → ai đó đã sửa, hãy xoá dòng ấy đi.
    Chiều thứ hai giữ cho danh sách khỏi mục: một sổ nợ không ai gạch nợ thì ba tháng nữa không
    còn ai tin nó nói đúng.
    """
    thuc = set(_lech())
    so = set(DA_BIET)
    moi = sorted(thuc - so)
    assert not moi, ("CAP LECH MOI, khong nam trong so:\n"
                     + "\n".join(f"   . {m} x {v}" for m, v in moi)
                     + "\n  Mo duoc menu ma khong goi duoc cua nao. Xem test_lg1 de biet hai chieu sua.")
    cu = sorted(so - thuc)
    assert not cu, ("SO CON GHI NO DA TRA - xoa cac dong nay khoi DA_BIET:\n"
                    + "\n".join(f"   . {m} x {v}" for m, v in cu))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Mười bảy cửa lương — bản ghi quyết định, không phải một phép suy
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg5_cua_luong_dung_nhu_da_ky():
    """Chủ tịch chốt 11/10/2026: Kế toán trưởng được mở CẢ cửa lương, kể cả nút chi lương thật.

    Phép thử này KHÔNG phán quyết ấy đúng hay sai — nó giữ cho quyết định ấy ĐẾM ĐƯỢC. Bảng lương
    là dữ liệu cá nhân theo Luật 91/2025 và NĐ 356/2025, nên một quyền mở ra do HỆ QUẢ của một
    dòng suy là một quyền không ai rà được. Khai ra thì Pháp chế đọc được đúng danh sách ấy, từng dòng một.

    Đỏ ở đây nghĩa là có một cửa lương vừa mở cho Kế toán trưởng mà chưa ai ký — và lần
    chạy đầu tiên nó đỏ thật, vì lượt quét tay của em bỏ sót `GET /api/v1/cap-phat`. Cách xử: đưa nó
    vào `CUA_LUONG_DA_KY` SAU KHI có người quyết, hoặc đóng nó lại.
    """
    mo = {(m, p) for p, v, m in _cua() if v and "ketoan_truong" in v and LUONG_RE.search(p)}
    da_ky = set(VKT.CUA_LUONG_DA_KY)
    chua_ky = sorted(mo - da_ky)
    assert not chua_ky, ("CUA LUONG MO CHO KE TOAN TRUONG MA CHUA AI KY:\n"
                         + "\n".join(f"   . {m} {p}" for m, p in chua_ky)
                         + f"\n  Can cu dang co: {VKT.CAN_CU_CUA_LUONG}")
    assert VKT.CAN_CU_CUA_LUONG, "danh sach cua luong phai ghi CAN CU - ngay va nguoi quyet"


def test_lg6_nut_chi_luong_nam_trong_danh_sach_co_ten():
    """Nút CHI LƯƠNG THẬT, không phải xem. Nó phải nằm trong danh sách có tên chứ không lọt vào
    bằng một phép suy — để người đọc sổ ba tháng nữa biết nó được mở có chủ đích."""
    assert ("POST", "/api/v1/payroll-runs/{period}/chi") in VKT.CUA_LUONG_DA_KY


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Phép suy: hai chỗ dễ sai
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg7_danh_sach_RONG_van_rong():
    """`require_roles()` không tham số nghĩa là "mọi người đã đăng nhập". Nới một danh sách rỗng
    là biến nó thành danh sách CÓ HẠN — tức SIẾT chứ không nới, và siết lặng lẽ."""
    assert VKT.mo_rong(()) == ()
    assert VKT.mo_rong([]) == ()


def test_lg8_ke_thua_la_CONG_THEM_khong_phai_thay_the():
    """`vai_va_cha` trả cả vai con để một quyền cấp RIÊNG cho vai con vẫn còn tác dụng. Trả mỗi
    vai cha thì mọi thứ khai riêng cho Kế toán trưởng biến mất mà không ai thấy."""
    assert VKT.vai_va_cha("ketoan_truong") == ("ketoan_truong", "ketoan")
    assert VKT.vai_va_cha("ketoan") == ("ketoan",)
    assert VKT.vai_va_cha("hcns") == ("hcns",)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Nới MOI_NHAN_VIEN: nới đúng bốn cửa ĐƠN TỪ, không nới theo một cửa tiền nào
# ═════════════════════════════════════════════════════════════════════════════════════════════
DON_TU_CUA_NGUOI = ("/api/v1/leaves", "/api/v1/leave-balance",
                    "/api/v1/danh-gia-cua-toi", "/api/v1/de-nghi-mua")
VAI_HEP = ("ketoan_tt", "thu_quy")


def test_lg9_ba_vai_tien_vao_moi_nhan_vien_chi_mo_them_don_tu():
    """Chủ tịch chốt 11/10/2026: ba vai tiền là NGƯỜI ĐI LÀM, gửi được đơn nghỉ phép. Việc ấy làm
    bằng cách thêm ba vai vào `MOI_NHAN_VIEN` — một hằng số dùng cho NHIỀU màn hình, nên nó nới
    nhiều hơn một cửa và phải đếm được từng cửa.

    ĐO ĐƯỢC, KHÔNG ĐOÁN: phạm vi `ketoan_tt` 27 → 31 và `thu_quy` 23 → 27, thêm đúng bốn màn hình
    đơn từ dưới đây. `ketoan_truong` KHÔNG đổi (108 → 108) vì `ketoan` vốn đã ở trong nhóm ấy.

    VÀ ĐÂY LÀ CHỖ DỄ ĐỌC NHẦM NHẤT CỦA ĐỢT NÀY: hai con số 31 và 27 TỪNG là phạm vi của hai vai
    ấy trước lần siết 10/10/2026, lần ấy gỡ `/ket-so` vì nó mở menu rồi trả 403. Trùng số là
    trùng ngẫu nhiên. `test_lg10` canh `/ket-so` vẫn đóng, để không ai đọc lần nới này thành một
    lần đảo quyết định cũ.
    """
    for vai in VAI_HEP:
        pv = set(AC.pham_vi_day_du(vai))
        thieu = [m for m in DON_TU_CUA_NGUOI if m not in pv]
        assert not thieu, f"{vai} la nguoi di lam ma khong gui duoc don tu: {thieu}"
    # SUA-2 02/11/2026: +1 cho cả hai — Đợt P2-1 (#614) khai `/api/v1/hach-toan/bang` vào màn /expenses mà hai vai
    # này đều có; `test_p2.PHAM_VI_DA_CHOT` đã đổi 31→32 / 27→28 cùng đợt ấy, chỗ này quên theo nên đỏ trên main.
    assert len(AC.pham_vi_day_du("ketoan_tt")) == 32
    assert len(AC.pham_vi_day_du("thu_quy")) == 28
    # Kế toán trưởng KHÔNG hẹp hơn Kế toán. Từ 20/10/2026 rộng hơn đúng MỘT cửa (Chủ tịch chốt): tự
    # gửi yêu cầu Pháp chế — việc của trưởng phòng trở lên; kế toán viên nhờ Kế toán trưởng gửi.
    ktt, kt = set(AC.pham_vi_day_du("ketoan_truong")), set(AC.pham_vi_day_du("ketoan"))
    assert kt <= ktt and ktt - kt == {"/api/v1/gui-phap-che"}


def test_lg10_ket_so_van_dong_voi_hai_vai_hep():
    """Lần siết 10/10/2026 KHÔNG bị đảo. Sổ kết sổ là sổ KIỂM SOÁT: người bị kiểm soát không mở
    nó. Đỏ ở đây nghĩa là một lần nới nhóm vừa kéo theo một cửa kiểm soát mà không ai quyết."""
    for vai in VAI_HEP:
        assert "/api/v1/ket-so" not in set(AC.pham_vi_day_du(vai)), \
            f"{vai} vua mo lai /ket-so - lan siet 10/10/2026 bi dao ma khong ai ky"
