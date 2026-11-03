"""Đợt E2b-0 — ba vai kế toán mở ở phạm vi hẹp nhất, và hai cửa tiền.

  A. Ba vai có mặt, và `ketoan` KHÔNG mất gì — vai nền ở lại nguyên vẹn.
  B. Kế toán trưởng nhìn ĐÚNG tập màn hình Kế toán nhìn. Đây là bất biến quan trọng nhất của
     đợt: nó được SUY RA, nên không lệch được khi có người thêm `ketoan` vào màn hình mới.
  C. Thủ quỹ vào được đúng ba màn hình đã khai, không hơn.
  D. Hai cửa tiền rời nhau, và giao của chúng đúng bằng vai nền.
  E. Phạm vi đo được: Kế toán trưởng bằng Kế toán; hai vai kia hẹp hơn hẳn.
  F. ĐỢT NÀY CHƯA QUÉT 69 CỬA — kiểm được bằng máy, không nói miệng.
"""
import io
import os
import re
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_le2b.db"
os.environ["SEED_DEMO"] = "1"
os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_le2b.db", "test_le2b.db-journal"):
    if os.path.exists(_f):
        os.remove(_f)

from app.models.core import ROLES
from app.services import access as AC
from app.services import ops as O

BA_VAI = ("ketoan_truong", "ketoan_tt", "thu_quy")

# ĐÚNG MỘT CỬA đợt này mở, và nó được khai ra chứ không lặng lẽ. `test_tc100` buộc danh sách vai
# trên router /tai-xe phải TRÙNG dòng trong MENU_ROLES; phép suy "Kế toán trưởng nhìn đúng những
# gì Kế toán nhìn" thêm vai ấy vào dòng ma trận, nên router phải theo. Không nới cho một con
# người nào: ai là Kế toán trưởng hôm nay cũng đang là `ketoan`, và `ketoan` đã có ở dòng ấy.
# BA VAI MỚI ĐƯỢC PHÉP XUẤT HIỆN Ở ĐÚNG NHỮNG CHỖ NÀY, ngoài hai tệp định nghĩa chúng
# (`models/core.py` khai tên vai, `services/access.py` suy ra bảng màn hình).
#
# `services/ops.py` — hai cửa tiền, chính là việc của đợt này.
# `api/v1/tai_xe.py` — `test_tc100` buộc danh sách vai trên router phải TRÙNG dòng MENU_ROLES;
#   phép suy thêm Kế toán trưởng vào dòng ma trận nên router phải theo. Không nới cho một con
#   người nào: ai là Kế toán trưởng hôm nay cũng đang là `ketoan`, đã có sẵn ở dòng ấy.
# `models/tach_nhiem.py` — `VAI_TIEN` đã liệt sẵn ba tên từ Đợt E2a, CỐ Ý: để ngày mở ba vai
#   không ai phải nhớ quay lại sửa tệp ấy. Nay ngày ấy đã tới và nó đúng sẵn.
# `services/ks_tach_nhiem.py` — Đợt E2b-1, cặp vai KHÔNG ĐƯỢC KIÊM NHAU (`CAP_VAI_KHONG_KIEM`).
#   Chủ tịch chốt 10/10/2026: HCNS riêng, thủ quỹ riêng. Tên vai phải viết ra ở đây vì phép đo so
#   `User.role` với đúng hai chuỗi ấy. Đây là chỗ THỨ HAI trong `services/` được phép nhắc
#   `thu_quy`, và nó được KHAI RA chứ không lặng lẽ — chính phép thử f1 bắt nếu ai thêm chỗ thứ ba.
CHO_DA_KHAI_BA_VAI = [
    "models/tach_nhiem.py: ketoan_truong",
    "models/tach_nhiem.py: ketoan_tt",
    "models/tach_nhiem.py: thu_quy",
    "services/ks_tach_nhiem.py: thu_quy",
    # `api/v1/hach_toan.py` — Đợt E2b sau rà soát 10/10/2026: Kế toán trưởng vào `XEM` để ĐỌC
    #   được những gì Kế toán đọc. Bản đầu chỉ mở bảng màn hình và quên danh sách vai đọc của
    #   router, nên ba vai thấy menu rồi nhận 403. Chính phép thử f1 dưới đây bắt dòng này khi
    #   em thêm nó mà chưa khai — đúng việc nó sinh ra để làm.
    "api/v1/hach_toan.py: ketoan_truong",
    "services/ops.py: ketoan_truong",
    "services/ops.py: ketoan_tt",
    "services/ops.py: thu_quy",
    # ── Đợt P2-2, 02/11/2026 ──────────────────────────────────────────────────────────────
    # `api/v1/payments.py` — cửa PHIẾU THU TIỀN MẶT (`cash_receipt`) nay là
    #   `require_roles("ketoan", "thu_quy")`. Dòng này đến cùng PR #613 (TR-1d) và lên main
    #   mà chưa khai, nên f1 đỏ trên main — lại đúng việc phép thử này sinh ra để làm.
    #
    #   KHAI LÀ GHI NHẬN, KHÔNG PHẢI MỞ. Vòng P2-2 không chạm `payments.py`: quyền ấy đã nằm
    #   trên main rồi. Khai ở đây để lần sau còn ĐẾM ĐƯỢC. Ai thấy việc mở quyền ấy là sai
    #   thì sửa ở `payments.py`, chứ đừng xoá dòng này — xoá dòng này chỉ làm hàng rào mù.
    "api/v1/payments.py: thu_quy",
    # ── SUA-2, 02/11/2026 ─────────────────────────────────────────────────────────────────
    # `api/v1/hach_toan.py` — cửa ĐỌC `GET /hach-toan/bang`: chỉ danh mục hình thức thanh toán cho nút ĐÃ CHI ở
    #   /expenses; thủ quỹ là người bấm ĐÃ CHI. Không mở bảng quy ước (`XEM` không đổi).
    "api/v1/hach_toan.py: thu_quy",
    "api/v1/tai_xe.py: ketoan_truong",
    # `api/v1/routes.py` — Đợt E4a 12/10/2026: Kế toán trưởng nằm trong hai bộ vai XEM và TRÌNH
    #   của cửa điều khoản thanh toán, cùng bộ vai với Kế toán. Đợt E4a thêm mà quên khai, nên
    #   phép thử f1 đỏ trên main từ 12/10 — lại đúng việc nó sinh ra để làm. Khai nốt ở Đợt DỌN-1.
    "api/v1/routes.py: ketoan_truong",
    # ── Đợt LG1, 11/10/2026 ───────────────────────────────────────────────────────────────
    # Hai cửa ĐỌC công nợ mở cho Kế toán thanh toán. Đây là cặp lệch thứ 29 của Đợt E2b:
    # `/cong-no` mở trên bảng MÀN HÌNH mà `debts.READ` và `cong_no_vietrip.XEM` không có
    # `ketoan_tt`, nên thấy menu rồi nhận 403. Hai hằng số ấy vốn đã ghi "khớp nhau".
    #
    # `ketoan_tt` KHÔNG kế thừa `ketoan` — nó là vai HẸP (chuyển khoản), cho kế thừa là xoá
    # mất chính việc tách vai của E2b. Nên cặp này chữa bằng cách mở ĐÚNG hai cửa đọc, và
    # hai dòng ấy phải khai ở đây để lần sau còn đếm được.
    "api/v1/debts.py: ketoan_tt",
    "api/v1/cong_no_vietrip.py: ketoan_tt",
    # ── Đợt LG3, 11/10/2026 ───────────────────────────────────────────────────────────────
    # `chu_ky.NGUOI_DUNG_DAU_PHONG` khai người đứng đầu phòng Kế toán là Kế toán trưởng (Chủ
    # tịch chốt 11/10/2026). Dòng ấy KHÔNG mở thêm một cửa nào: nó nói ai KÝ vế thứ nhất cho
    # hồ sơ của phòng Kế toán. Phép thử này soi theo TÊN VAI chứ không theo loại việc — đúng
    # như nó được thiết kế, vì soi theo cú pháp thì luôn có một cách viết khác lọt qua — nên
    # một dòng khai NGƯỜI KÝ cũng hiện ra ở đây và phải khai.
    "services/chu_ky.py: ketoan_truong",
    # ── Đợt E6, 13/10/2026 ────────────────────────────────────────────────────────────────
    # Cửa TRÌNH đề nghị mở lại một kỳ kế toán đã khóa: `POST /periods/{period}/mo-lai`, vai
    # `ketoan_truong` + `cntt`. Đây là MỘT cửa mới, và nó mở cho Kế toán trưởng chứ không cho
    # `ketoan`: người trình phải là người đứng đầu phòng, vì hồ sơ này đi lên Chủ tịch ký.
    # Cửa KÝ (`chutich`) không hiện ở đây vì phép thử chỉ soi ba vai mới của Đợt E2b.
    "api/v1/accounting.py: ketoan_truong",
    # `api/v1/books.py` — Đợt R4b-2b 23/10/2026, Chủ tịch ký: Kế toán trưởng ĐỌC được Sổ kế
    # toán (nhật ký chung, sổ cái, sổ chi tiết, bảng cân đối, hóa đơn còn thiếu). Không phải
    # quyền mới: phép suy `ketoan` → `ketoan_truong` của Đợt LG1 đã cho vai ấy thấy menu, cửa
    # này viết trước LG1 nên chặn — món nợ chỉ lộ khi `/api/v1/books` lần đầu gắn vào màn hình.
    # CỬA ĐỌC, không có cửa ghi nào mở thêm: `GHI_HOA_DON` vẫn chỉ `ketoan`.
    "api/v1/books.py: ketoan_truong",
    # ── Vòng HS-1, 15/10/2026 (làn Kiểm soát) ─────────────────────────────────────────────
    # `services/ho_so_nhan_vien.py: CAP_BAC` xếp THỨ BẬC cho cả 29 vai trong `ROLES`, nên ba
    # tên này hiện ra ở đó. Nó KHÔNG mở một cửa nào: cấp bậc chỉ quyết định dòng nào đứng trên
    # dòng nào trong bảng 121 tài khoản. Cùng loại với `services/chu_ky.py` khai NGƯỜI KÝ ở
    # trên — phép thử soi theo TÊN VAI chứ không theo loại việc, và đó là chủ ý của nó.
    #
    # CHỖ PHÉP THỬ NÀY MẤT KHI KHAI THÊM MỘT TỆP, nói ra để không ai yên tâm nhầm: danh sách
    # ghi MỘT dòng cho mỗi cặp (tệp, vai), nên từ nay nếu ai đó thật sự MỞ QUYỀN cho ba vai ấy
    # trong chính `ho_so_nhan_vien.py` thì f1 sẽ im. Phần canh ấy đã dựng lại ở nơi hẹp hơn:
    # `test_hs1_phan_quyen_ho_so.py::test_hs1_12_ba_vai_ke_toan_khong_nam_trong_bang_quyen`
    # đòi ba vai này không được xuất hiện trong bất kỳ bảng `quyen` nào của 17 nhóm trường.
    "services/ho_so_nhan_vien.py: ketoan_truong",
    # ĐỢT R4b-2c — CHỦ TỊCH KÝ 23/10/2026: thẻ “Hóa đơn còn thiếu” hiện trên bàn làm việc của
    # Kế toán trưởng. KHÔNG phải một cửa mới — `dashboard.py` không mở cửa nào, nó chỉ chọn dòng
    # nào bày ra. Vai ấy đã có `books.READ` (ký 23/10) và đã thấy màn hình qua phép suy LG1.
    # `test_r4b2c_5` đi từng đường dẫn trong khối ấy và đòi vai ấy vốn đã mở được màn hình đó —
    # nên dòng này mở ra một CHỖ ĐỌC con số, không mở ra quyền.
    "services/dashboard.py: ketoan_truong",
    "services/ho_so_nhan_vien.py: ketoan_tt",
    "services/ho_so_nhan_vien.py: thu_quy",
    # ── Đợt E12, 13/10/2026 ───────────────────────────────────────────────────────────────
    # `services/bang_ky_cua.py` KHÔNG mở một cửa nào — nó ĐẾM. Tên vai xuất hiện ở đây vì nó là
    # vai mà quyết định 11/10/2026 nói tới, và bảng ký phải gọi đúng tên quyết định ấy. Phép thử
    # này soi theo TÊN VAI chứ không theo loại việc, đúng như nó được thiết kế, nên một dòng chỉ
    # ĐỌC cũng hiện ra và cũng phải khai.
    "services/bang_ky_cua.py: ketoan_truong",
    # ── DOT DON-R4c3, 04/11/2026 ──────────────────────────────────────────────────────────
    # CHU TICH CHOT QUA TIN NHAN 04/11/2026: Ke toan thanh toan doc duoc danh muc hinh thuc
    # thanh toan. KHONG phai quyen moi tren du lieu — cua `GET /api/v1/hach-toan/bang` tra
    # DUNG bay nhan tinh `HINH_THUC_TT`, khong quy uoc, khong so lieu, khong cham co so du
    # lieu (than ham chi co mot dong `return`).
    #
    # Vi sao can mot dong o day: `ketoan_tt` DA co `/expenses` trong `MAN_HINH_KETOAN_TT`,
    # nhung no CO Y khong ke thua `ketoan` (Dot E2b tach vai: ke toan thanh toan xu chuyen
    # khoan, thu quy xu tien mat), nen `VKT.mo_rong` khong voi toi, va o «hinh thuc thanh
    # toan» RONG voi dung vai xu chuyen khoan. Cung le voi viec Dot SUA-2 khai `thu_quy`
    # vao chinh cua ay.
    #
    # Luat 3 cua `test_donr4c3_cua_hep_hinh_thuc_tt.py` canh chieu nguoc: vai nao vao duoc
    # `/expenses` ma khong doc duoc cua nay thi DO — nen cho hong tren khong quay lai im lang.
    "api/v1/hach_toan.py: ketoan_tt",
]
GOC_APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app")


NGOAI_LE_KTT = {"/gui-phap-che"}


def man_hinh(vai: str) -> set:
    return {m for m, v in AC.MENU_ROLES.items() if vai in v}


# ─────────────────────────── A ───────────────────────────
def test_a1_ba_vai_co_mat_va_co_ten_tieng_viet():
    for v in BA_VAI:
        assert v in ROLES, f"Vai `{v}` chưa có trong ROLES"
        assert ROLES[v].strip(), f"Vai `{v}` không có tên hiển thị"


def test_a2_vai_nen_ketoan_o_lai_nguyen_ven():
    """Tách KHÔNG phải thay thế. Ai đang làm được gì hôm nay thì mai vẫn thế."""
    assert "ketoan" in ROLES
    assert len(man_hinh("ketoan")) > 0


# ─────────────────────────── B ───────────────────────────
def test_b1_ke_toan_truong_nhin_dung_bang_ke_toan():
    """Bất biến quan trọng nhất của đợt.

    Nếu một ngày ai đó thêm `ketoan` vào một màn hình mới mà quên Kế toán trưởng thì cấp dưới
    xem được màn hình còn cấp trên thì không — và không ai phát hiện ra, vì cả hai dòng đều
    trông đúng. Phép thử này làm chuyện ấy không xảy ra được.
    """
    thieu = man_hinh("ketoan") - man_hinh("ketoan_truong")
    # NGOẠI LỆ DUY NHẤT, Chủ tịch chốt 20/10/2026: Kế toán trưởng tự gửi yêu cầu Pháp chế (việc của
    # trưởng phòng trở lên), kế toán viên thì không. Thêm màn thứ hai vào đây phải có chữ ký riêng.
    thua = man_hinh("ketoan_truong") - man_hinh("ketoan") - NGOAI_LE_KTT
    assert not thieu, f"Kế toán xem được mà Kế toán trưởng thì không: {sorted(thieu)}"
    assert not thua, f"Kế toán trưởng xem được mà Kế toán thì không: {sorted(thua)}"


# ─────────────────────────── C ───────────────────────────
# ĐỢT LG1, 11/10/2026: ba vai tiền vào `MOI_NHAN_VIEN` (Chủ tịch chốt: "họ là người làm việc"),
# nên MENU của hai vai hẹp thêm ĐÚNG hai màn hình ĐƠN TỪ dưới đây. Không phải quyền tiền.
#
# Vẫn so BẰNG chứ không đổi sang "chứa": nới câu hỏi thành "chứa" là bỏ mất chính điều hai phép
# thử này canh — rằng hai vai ấy HẸP ĐÚNG NHƯ ĐÃ KHAI và không ai nới thêm được mà không ai thấy.
MAN_HINH_DON_TU = {"/cham-cong", "/de-nghi-mua"}


def test_c1_thu_quy_dung_ba_man_hinh_da_khai():
    assert man_hinh("thu_quy") == set(AC.MAN_HINH_THU_QUY) | MAN_HINH_DON_TU


def test_c2_hai_man_hinh_ay_la_cho_nam_bon_cua_cua_thu_quy():
    """Cấp cửa mà khoá màn hình là dựng một vai không dùng được — chính là dòng CHẶN NL-1.

    `/ket-so` KHÔNG thuộc thủ quỹ, và bản đầu của đợt này đã khai sai. Rà soát 10/10/2026:
    mở `/ket-so` cho thủ quỹ làm họ THẤY MENU rồi nhận 403, vì `hach_toan.py` khai danh sách
    vai đọc của riêng nó. Chữa theo hướng ĐI XUỐNG, không nới `XEM`: sổ tách bạch trách
    nhiệm là sổ KIỂM SOÁT, người bị kiểm soát không cần mở nó.
    """
    mh = man_hinh("thu_quy")
    assert "/expenses" in mh, "Cửa bấm ĐÃ CHI nằm sau màn hình /expenses"
    assert "/collections" in mh, "Xác nhận phiếu thu và phiếu thu tiền mặt nằm sau /collections"
    assert "/ket-so" not in mh, (
        "Thủ quỹ KHÔNG có /ket-so: màn hình ấy đọc /api/v1/hach-toan, mà thủ quỹ không nằm "
        "trong danh sách vai đọc của router ấy — cấp menu mà không cấp quyền đọc là dựng lại "
        "đúng cái bẫy 13/9/2026")


def test_c3_ke_toan_thanh_toan_dung_tap_da_khai():
    assert man_hinh("ketoan_tt") == set(AC.MAN_HINH_KETOAN_TT) | MAN_HINH_DON_TU


# ─────────────────────────── D ───────────────────────────
def test_d1_hai_cua_tien_roi_nhau_tru_vai_nen():
    """Giao của hai cửa đúng bằng `ketoan`, và đó là điều phải ghi ra chứ không để ngầm.

    Vai nền còn ở cả hai vì hôm nay chỉ có họ làm cả hai việc. Khi đã có người cho từng vai
    mới thì `ketoan` ra khỏi một trong hai — và lúc ấy lớp chống gian lận mới đứng được bằng
    chính bảng phân quyền. Cho tới lúc ấy, thứ giữ nó là ks_tach_nhiem so theo NGƯỜI.
    """
    assert set(O.VAI_KIEM_CHUNG_TU) & set(O.VAI_GHI_DA_CHI) == {"ketoan"}


def test_d2_thu_quy_khong_kiem_chung_tu_ke_toan_truong_khong_bam_da_chi():
    assert "thu_quy" not in O.VAI_KIEM_CHUNG_TU, "Thủ quỹ cầm tiền, không kiểm chứng từ"
    assert "ketoan_truong" not in O.VAI_GHI_DA_CHI, (
        "Kế toán trưởng KÝ, thủ quỹ CẦM TIỀN — gộp vào một vai là mất lớp kiểm soát")
    assert "ketoan_tt" not in O.VAI_GHI_DA_CHI, (
        "Người lập chứng từ thanh toán không được tự bấm ĐÃ CHI")


def test_d3_hai_cua_tien_la_hang_so_co_ten_de_may_doc_duoc():
    """Trước bản này hai cửa viết cứng trong thân hàm nên bộ kiểm quyền không đọc được.

    Cùng bài học 13/9/2026 đã khiến `toan_quyen()` phải là một HÀM chứ không phải một hằng số
    nhập tay: một hằng số thì người ta quên nhập, một cái tên thì phép thử canh được.
    """
    nguon = io.open(os.path.join(GOC_APP, "services/ops.py"), encoding="utf-8").read()
    # BỎ DÒNG CHÚ THÍCH TRƯỚC KHI TÌM. Chính chú thích giải thích lỗi cũ có chứa đúng chuỗi ấy,
    # nên bản đầu của phép thử này đỏ vì lời giải thích chứ không vì mã — bắt được ngay lần chạy
    # đầu, và ghi lại vì đó là cái bẫy chung của mọi phép thử đọc mã nguồn bằng chuỗi.
    ma = "\n".join(d for d in nguon.split("\n") if not d.lstrip().startswith("#"))
    assert 'u.role != "ketoan"' not in ma, (
        "Còn một cửa tiền viết cứng `u.role != \"ketoan\"` trong thân hàm")


# ─────────────────────────── E ───────────────────────────
def test_e1_pham_vi_do_duoc():
    pv = {v: len(AC.pham_vi_day_du(v)) for v in ("ketoan",) + BA_VAI}
    assert pv["ketoan_truong"] == pv["ketoan"] + len(NGOAI_LE_KTT), \
        "Kế toán trưởng phải bằng Kế toán, cộng đúng các ngoại lệ đã ký (NGOAI_LE_KTT)"
    assert pv["ketoan_tt"] < pv["ketoan"], "Kế toán thanh toán phải hẹp hơn vai nền"
    assert pv["thu_quy"] < pv["ketoan_tt"], "Thủ quỹ phải là vai hẹp nhất trong ba"
    assert pv["thu_quy"] < pv["chutich"] if "chutich" in pv else True


def test_e2_khong_vai_nao_rong_bang_chu_tich():
    rong_nhat = len(AC.pham_vi_day_du("chutich"))
    for v in BA_VAI:
        assert len(AC.pham_vi_day_du(v)) < rong_nhat, f"`{v}` rộng bằng Chủ tịch"


# ─────────────────────────── F ───────────────────────────
def test_f1_dot_nay_chi_mo_dung_nhung_cho_da_khai():
    """Lời hứa "đợt này mở ba vai ở phạm vi hẹp nhất" phải ĐO ĐƯỢC, không nói miệng.

    Quét MỌI dòng mã (bỏ chú thích) dưới `app/` tìm ba tên vai mới, trừ hai tệp nơi chúng
    được ĐỊNH NGHĨA và SUY RA. Những gì còn lại phải khớp đúng danh sách khai sẵn dưới đây.

    Bản đầu của phép thử này chỉ soi bên trong `require_roles(...)` và đã BỎ SÓT `tai_xe.py`,
    vì tệp ấy khai một tuple `READ` rồi mới trải vào. Soi theo cú pháp thì luôn có một cách
    viết khác lọt qua; soi theo TÊN VAI thì không.
    """
    # `services/vai_ke_thua.py` vào đây ở Đợt LG1 vì nó ĐÚNG LÀ nơi định nghĩa: `VAI_KE_THUA`
    # là một dòng khai phép suy, không phải một lần mở quyền. Khai nó như một "chỗ mở quyền"
    # thì danh sách trên kia nói sai về chính nó.
    NOI_DINH_NGHIA = {"models/core.py", "services/access.py", "services/vai_ke_thua.py"}
    co = []
    for goc, _d, tep in os.walk(GOC_APP):
        for t_ in tep:
            if not t_.endswith(".py"):
                continue
            p_ = os.path.join(goc, t_)
            rel = os.path.relpath(p_, GOC_APP).replace(os.sep, "/")
            if rel in NOI_DINH_NGHIA:
                continue
            s = io.open(p_, encoding="utf-8").read()
            ma = "\n".join(d for d in s.split("\n") if not d.lstrip().startswith("#"))
            for v in BA_VAI:
                if f'"{v}"' in ma:
                    co.append(f"{rel}: {v}")
    assert sorted(co) == sorted(CHO_DA_KHAI_BA_VAI), (
        "Ba vai mới chỉ được xuất hiện ở những chỗ đã khai. "
        f"Thừa: {sorted(set(co) - set(CHO_DA_KHAI_BA_VAI))} · "
        f"Thiếu: {sorted(set(CHO_DA_KHAI_BA_VAI) - set(co))}. "
        "Nếu đây là lần quét 71 cửa có chữ ký thì sửa luôn danh sách này.")
