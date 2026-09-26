# -*- coding: utf-8 -*-
"""PQ-1 · Bảng luồng công việc phải KHỚP với luật đang chạy trong mã.

Phép thử quan trọng nhất ở đây là test_bang_khop_voi_luat_dang_chay. Nó tồn tại vì bảng
LUONG_VIEC là một BẢN CHÉP, và một bản chép không có gì canh thì sớm muộn lệch khỏi bản gốc –
lệch lặng lẽ, vì cả hai bên vẫn chạy được. Khi ấy màn hình /access nói một đằng, máy chủ làm một
nẻo, và đó đúng là thứ tệ hơn không có bảng: người đọc tin vào một trang sai.

Quy ước khi phép thử này đỏ: MÃ ĐÚNG, BẢNG SAI. Sửa bảng cho khớp mã. Nếu thật sự muốn đổi luật
thì đó là việc riêng, có người ký, và sửa mã trước rồi mới sửa bảng – không bao giờ ngược lại.

Phép thử đọc MÃ chứ không chạy hàm, nên phải bỏ chú thích trước khi so khớp: ngày 09/9 hai đột
biến lọt qua vì phép thử đọc cả chú thích, mà chú thích lại nhắc đúng tên định danh vừa bị xoá.
"""
import re
from pathlib import Path

import pytest

from app.services import luong_viec as LV

GOC = Path(__file__).resolve().parents[1]
DV = GOC / "app" / "services"


def _than_ham(tep: str, ten_ham: str) -> str:
    """Thân một hàm, đã bỏ chú thích và chuỗi tài liệu."""
    p = DV / tep
    if not p.exists():
        pytest.skip(f"chưa có {tep} trong cây làm việc")
    s = p.read_text(encoding="utf-8", errors="replace")
    i = s.find(f"def {ten_ham}(")
    assert i >= 0, f"không thấy {tep}::{ten_ham} – bảng đang trỏ tới một hàm không tồn tại"
    j = s.find("\ndef ", i + 5)
    than = s[i: j if j > 0 else len(s)]
    than = re.sub(r'"""(?:.|\n)*?"""', " ", than)
    than = re.sub(r"^\s*#.*$", " ", than, flags=re.M)
    return than


def _vai_tro_trong(than: str) -> set[str]:
    """Mọi vai trò xuất hiện trong các dòng CHẶN của một hàm.

    Chỉ đọc dòng ĐIỀU KIỆN – bắt đầu bằng if/elif – hoặc dòng có raise. Bản đầu đọc mọi dòng có
    'u.role' và lập tức bắt nhầm một ca thật: trong nonpackage.create có dòng
    `t = Tour(..., tour_type="non_package", ..., operator_id=u.id if u.role in ("nv_dh","tp_dh")...)`
    – đó là mã NGHIỆP VỤ chứ không phải chặn quyền, và nó kéo theo cả chuỗi "non_package" vào danh
    sách vai trò. Một phép thử báo oan thì sau vài lần không ai đọc nó nữa.
    """
    ra: set[str] = set()
    for dong in than.splitlines():
        s = dong.strip()
        if "audit" in s or "EV(" in s:
            continue
        if not re.search(r"u\.role", s):
            continue
        if not (re.match(r"(if|elif)\b", s) or "raise" in s):
            continue
        ra |= set(re.findall(r'"([a-z_]{2,12})"', s))
    return ra


# Mỗi dòng: (nghiệp vụ, mã bước, tệp, hàm). Khai tay chứ không dò tự động, vì một hàm có thể
# chứa nhiều bước (tours.d7) và dò tự động sẽ gộp chúng lại thành một – che mất đúng chỗ cần canh.
NEO = [
    ("chuyen_tour", "tao",            "tours.py",      "create"),
    ("chuyen_tour", "trinh",          "tours.py",      "submit"),
    ("chuyen_tour", "xac_nhan",       "tours.py",      "confirm"),
    ("chuyen_tour", "kt_xac_nhan",    "tours.py",      "kt_confirm"),
    ("chuyen_tour", "cntt_doi_chieu", "tours.py",      "cntt_check"),
    ("chuyen_tour", "kt_tra_lai",     "settlement.py", "kt_return"),
    ("booking",     "tao",            "tours.py",      "create_booking"),
    ("booking",     "huy",            "bookings.py",   "cancel"),
    ("booking",     "mo_khoa",        "bookings.py",   "unlock"),
    ("bao_luu",     "tat_toan",       "bookings.py",   "apply_retention"),
    ("bao_luu",     "de_xuat_hoan",   "bookings.py",   "refund_retention"),
    ("bao_luu",     "huy",            "bookings.py",   "cancel_retention"),
    ("dich_vu_le",  "tao",            "nonpackage.py", "create"),
    ("dich_vu_le",  "chot_thang",     "nonpackage.py", "close_month"),
    ("dich_vu_le",  "mo_tour_tu_san_pham", "products.py", "open_tour"),
]


@pytest.mark.parametrize("nv,ma,tep,ham", NEO)
def test_bang_khop_voi_luat_dang_chay(nv, ma, tep, ham):
    """Vai trò trong bảng phải đúng bằng vai trò hàm đang chặn. Không thừa, không thiếu."""
    b = LV.buoc(nv, ma)
    assert b is not None, f"bảng thiếu bước {nv}/{ma}"
    trong_ma = _vai_tro_trong(_than_ham(tep, ham))
    # Hằng số danh sách vai trò (CANCEL_ROLES, UNLOCK_ROLES, CREATE_ROLES) nằm ngoài thân hàm –
    # lấy thêm từ đầu tệp thì mới so được.
    if not trong_ma:
        s = (DV / tep).read_text(encoding="utf-8", errors="replace")
        for hang in re.findall(r'^[A-Z_]{3,}\s*=\s*\(([^)]*)\)', s, re.M):
            nhom = set(re.findall(r'"([a-z_]{2,12})"', hang))
            if nhom == set(b.vai_tro):
                trong_ma = nhom
                break
    assert trong_ma, f"không đọc được vai trò nào trong {tep}::{ham} – neo đã lỗi thời"
    assert trong_ma == set(b.vai_tro), (
        f"{nv}/{ma}: mã chặn {sorted(trong_ma)} nhưng bảng khai {sorted(b.vai_tro)}. "
        "MÃ ĐÚNG, BẢNG SAI – sửa bảng cho khớp mã.")


def test_cong_mot_chu_ho_so_van_la_MOT_nguoi_trong_ma():
    """Hai cổng quyết toán phải KHÔNG có đường thoát theo vai trò, và phải hỏi ĐÚNG MỘT người.

    Đóng sổ quyết toán và soạn dòng quyết toán là chỗ duy nhất trong hệ thống mà chức vụ không
    thay được trách nhiệm: Trưởng phòng cũng không nhập hộ. Thêm một vai trò vào đây là xoá dấu
    người chịu trách nhiệm về con số, và không ai nhận ra vì bảng vẫn cân.

    ĐỔI NGÀY 25/9/2026 (Chủ tịch, câu 4). Bản cũ canh bằng cách đòi chữ `operator_id` có mặt
    trong thân hai hàm. Nay người chịu trách nhiệm do `chu_ho_so.chu_ho_so()` chỉ ra, nên phép
    thử đòi đúng ba điều còn lại — và chúng mới là nội dung thật của luật:

      1. Hai hàm KHÔNG chặn theo vai trò. Đây là điều quan trọng nhất và nó KHÔNG đổi.
      2. Hai hàm hỏi `chu_ho_so` (qua `la_chu_ho_so`), không tự dựng luật riêng. Bản cũ từng để
         hai bản chép của cùng một luật lệch nhau một lần rồi.
      3. `chu_ho_so` bản thân nó trả về MỘT người: vẫn rơi về `operator_id`, và KHÔNG xét
         `u.role` ở bất cứ đâu. Nếu một ngày ai đó viết `if u.role == "tp_dh": return u.id` vào
         đó thì cổng một chủ hồ sơ đã bị nới — ở một tệp mà hai phép thử trên không nhìn tới.
    """
    for tep, ham in (("tours.py", "close"), ("settlement.py", "_assert_edit")):
        than = _than_ham(tep, ham)
        assert not _vai_tro_trong(than), (
            f"{tep}::{ham} nay có chặn theo vai trò – cổng một chủ hồ sơ đã bị nới, bảng phải khai lại")
        assert "la_chu_ho_so" in than, (
            f"{tep}::{ham} không còn hỏi chu_ho_so.la_chu_ho_so – luật đang được chép lại chỗ khác")

    than_chs = _than_ham("chu_ho_so.py", "chu_ho_so")
    assert "operator_id" in than_chs, "chu_ho_so() không còn rơi về người điều hành chuyến"
    assert "u.role" not in than_chs and "role" not in than_chs, (
        "chu_ho_so() nay xét vai trò – một chủ hồ sơ không còn là một người")

    for nv, ma in (("chuyen_tour", "dong_so"), ("quyet_toan", "soan_dong")):
        b = LV.buoc(nv, ma)
        assert b.cach_canh == LV.CHI_CHU_SO_HUU and not b.vai_tro
        assert b.chu_so_huu == LV.CHU_HO_SO


def test_ban_giao_ho_so_khong_dong_thoi_chuyen_thuong_chuyen():
    """Bàn giao hồ sơ quyết toán KHÔNG được chạm vào `operator_id`.

    `operator_id` là căn cứ duy nhất tính thưởng chuyến. Một cú bấm mang tên "bàn giao hồ sơ" mà
    ghi đè cột ấy là chuyển tiền thưởng của điều hành sang người gõ quyết toán, và không màn hình
    nào nói ra điều đó. Phép thử này tồn tại vì "cho gọn, dùng luôn operator_id" là đúng cái cách
    sửa mà ba tháng nữa trông rất hợp lý.
    """
    than = _than_ham("chu_ho_so.py", "giao_ho_so")
    assert "t.chu_ho_so_id = nguoi_moi.id" in than, "bàn giao không ghi vào cột chủ hồ sơ"
    assert "t.operator_id =" not in than, "bàn giao đang ghi đè người điều hành – thưởng chuyến đi theo"


def test_duyet_du_toan_lay_vai_tro_dong_khong_viet_cung():
    """Duyệt dự toán: tour LẺ do TGĐ, tour ĐOÀN do Phó TGĐ đoàn – vai trò tính lúc chạy.

    Viết cứng một trong hai vào bảng là khai sai một nửa số chuyến, và khai sai kiểu không ai
    thấy: mỗi loại tour nhìn riêng đều đúng.
    """
    b = LV.buoc("chuyen_tour", "duyet")
    assert b.vai_tro_dong == "rules.approver_role" and not b.vai_tro
    than = _than_ham("rules.py", "approver_role")
    assert "ptgd_doan" in than and "tgd" in than

    ok, ly_do = LV.duoc_day(b, "tgd")
    assert not ok and "chưa tính" in ly_do, "thiếu vai trò tính lúc chạy thì phải NÓI RA, không cho qua"
    assert LV.duoc_day(b, "tgd", vai_tro_dong="tgd")[0]
    assert not LV.duoc_day(b, "tgd", vai_tro_dong="ptgd_doan")[0]


def test_hai_chu_ky_chi_o_dung_hai_cho():
    """Hai chữ ký là ngoại lệ, không phải mặc định. Khai thừa một chỗ là làm chậm cả luồng."""
    hai = {(b.nghiep_vu, b.ma) for b in LV.LUONG_VIEC if b.chu_ky == 2}
    assert hai == {("chuyen_tour", "duyet_duoi_bien"), ("de_nghi_chi", "duyet_hai_chu_ky")}
    than = _than_ham("tours.py", "approve")
    assert "below_margin" in than, "mã không còn phân biệt chuyến dưới biên"
    assert "signed_" in _than_ham("ops.py", "step")


def test_moi_buoc_deu_noi_duoc_luat_nam_o_dau_va_vi_sao():
    """Bước không ghi nguồn thì không ai kiểm lại được; không ghi vì sao thì lần sau bị sửa bừa."""
    for b in LV.LUONG_VIEC:
        assert b.nguon and "::" in b.nguon, f"{b.nghiep_vu}/{b.ma} chưa ghi luật nằm ở đâu"
        assert len(b.vi_sao) >= 30, f"{b.nghiep_vu}/{b.ma} chưa ghi vì sao bước này chặn như vậy"
        assert b.cach_canh in (LV.CHI_VAI_TRO, LV.CHI_CHU_SO_HUU, LV.HOAC, LV.VA)
        if b.cach_canh in (LV.CHI_CHU_SO_HUU, LV.HOAC, LV.VA):
            assert b.chu_so_huu, f"{b.nghiep_vu}/{b.ma} khai canh theo chủ sở hữu mà không nói là ai"


def test_tu_choi_luon_kem_ly_do_du_ba_dieu():
    """403 phải nói: vai trò đang dùng thiếu gì, và bước ấy dành cho ai.

    Một câu 'không có quyền' trơ trọi thì người dùng đọc là phần mềm hỏng chứ không đọc là mình
    không được phép – và mỗi lần như thế là một lần niềm tin vào hệ thống bị trừ đi.
    """
    ok, ly_do = LV.duoc_day(LV.buoc("chuyen_tour", "xac_nhan"), "nv_dh")
    assert not ok and "tp_dh" in ly_do and "xác nhận" in ly_do.lower()

    ok, ly_do = LV.duoc_day(LV.buoc("chuyen_tour", "dong_so"), "tp_dh", la_chu_so_huu=False)
    assert not ok and "một cửa" in ly_do
    assert LV.duoc_day(LV.buoc("chuyen_tour", "dong_so"), "nv_dh", la_chu_so_huu=True)[0]

    b = LV.buoc("booking", "sua_thong_tin_khach")
    assert LV.duoc_day(b, "nv_kd", la_chu_so_huu=True)[0], "sale phụ trách phải sửa được"
    assert LV.duoc_day(b, "tp_dh", la_chu_so_huu=False)[0], "Điều hành phải sửa được"
    assert not LV.duoc_day(b, "nv_mkt", la_chu_so_huu=False)[0]


def test_bang_phu_du_sau_nghiep_vu_va_khong_trung_ma():
    """Thiếu một nghiệp vụ là mất hẳn một chuỗi bàn giao khỏi tầm nhìn của lãnh đạo."""
    assert set(LV.NGHIEP_VU) == {b.nghiep_vu for b in LV.LUONG_VIEC}
    khoa = [(b.nghiep_vu, b.ma) for b in LV.LUONG_VIEC]
    assert len(khoa) == len(set(khoa)), "có hai bước trùng mã – tra cứu sẽ trả về nhầm bước"
    assert len(LV.LUONG_VIEC) >= 25


def test_nguoi_xac_nhan_de_nghi_chi_doi_theo_loai_chi():
    """Không gộp năm loại chi thành một danh sách phẳng: gộp là mở quyền cho bốn loại còn lại."""
    assert LV.NGUOI_XAC_NHAN_THEO_LOAI["marketing"] == ("ptgd_mkt",)
    assert LV.NGUOI_XAC_NHAN_THEO_LOAI["hanh_chinh"] == ("hcns",)
    than = _than_ham("ops.py", "step")
    assert "CATEGORY_CONFIRMER" in than
    s = (DV / "ops.py").read_text(encoding="utf-8", errors="replace")
    trong_ma = dict(re.findall(r'"(\w+)":\s*\(([^)]*)\)', s[s.find("CATEGORY_CONFIRMER"):][:400]))
    for loai, vt in LV.NGUOI_XAC_NHAN_THEO_LOAI.items():
        assert loai in trong_ma, f"loại chi '{loai}' có trong bảng mà không có trong mã"
        assert set(re.findall(r'"([a-z_]+)"', trong_ma[loai])) == set(vt), (
            f"loại chi '{loai}': mã và bảng khai khác nhau")


def test_tra_cuu_nguoc_theo_vai_tro():
    """Màn hình /access cần trả lời: người này đẩy được những bước nào."""
    assert {b.ma for b in LV.buoc_cua_vai_tro("ketoan")} >= {"kt_xac_nhan", "kt_tra_lai", "ghi_da_chi"}
    assert not any(b.nghiep_vu == "chuyen_tour" and b.ma == "duyet"
                   for b in LV.buoc_cua_vai_tro("nv_kd")), "Kinh doanh không duyệt dự toán"
    d = {r["ma"]: r for r in LV.bang()}
    assert d["dong_so"]["ai_duoc"] == "chỉ chủ hồ sơ quyết toán"
