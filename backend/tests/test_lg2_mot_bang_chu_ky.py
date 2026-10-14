# -*- coding: utf-8 -*-
"""Đợt LG2 — MỘT BẢNG CHỮ KÝ, mọi cửa cùng đọc; và cửa ký thứ bảy không mọc lặng lẽ.

Trước đợt này "cần hai chữ ký" nằm rời ở sáu chỗ, mỗi chỗ viết lại cùng một luật ba lần
(`require_roles`, `kiem_tra_nguoi_ky`, `if signed_chutich and signed_tgd`). Đổi luật một cửa là
phải sửa đúng ba chỗ; sót một chỗ thì cửa vẫn chạy, chỉ là chạy sai — và không ai thấy.

Tệp này canh ba điều:
  A. Bảng `VAI_KY_CAN` nói ĐÚNG quyết định ngày 11/10/2026, và đếm được.
  B. Ba cửa đã chuyển sang một chữ ký thì CỬA và PHÉP KIỂM phải cùng đọc bảng ấy — không còn
     chỗ nào viết thẳng `("chutich", "tgd")` cho ba cửa đó.
  C. MỌI hàm có đặt chữ ký đều gọi `kiem_tra_nguoi_ky`, trừ những cửa KHAI CÓ TÊN.
"""
import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_lg2.db")

from app.services import chu_ky as CK  # noqa: E402

GOC_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")

# `dieu_khoan_thanh_toan` vào bảng ngày 12/10/2026 theo Đợt E4a, Chủ tịch chốt: điều khoản
# thanh toán đi MỘT chữ ký Chủ tịch, y như bảng tham số chính sách. Đợt E4a thêm dòng vào
# `VAI_KY_CAN` mà KHÔNG khai lại ở đây, nên phép thử này đỏ trên main từ 12/10 đến 13/10 —
# đúng việc nó sinh ra để làm ("có người thêm một cửa mà không ai ký lại bảng này"), chỉ là
# người thêm cửa đã không đọc chỗ đỏ. Đợt VA-WEB5 khai nốt, không nới phép thử.
# `mo_lai_ky` vào bảng ngày 13/10/2026 theo Đợt E6, Chủ tịch chốt: mở lại một kỳ kế toán đã khóa
# đi MỘT chữ ký Chủ tịch, và Kế toán trưởng là người trình. Khai nốt ở đây để sổ phép thử không
# lệch với bảng luật — đúng việc Đợt DỌN-1 phải đi dọn vì Đợt E4a quên.
# `bo_so_kiem_toan` vào bảng ngày 14/10/2026 theo Đợt E16, Chủ tịch chốt: bộ số BCTC đã kiểm
# toán do Kế toán tải lên và Chủ tịch ký — MỘT chữ ký, cùng hình dáng với `mo_lai_ky`. Khai nốt ở
# đây để sổ phép thử không lệch với bảng luật.
MOT_CHU_KY = ("tham_so", "don_gia_hdv", "gia_xe", "dieu_khoan_thanh_toan", "mo_lai_ky",
              "bo_so_kiem_toan")
HAI_CT_TGD = ("quy_tac_hach_toan", "che_tai_muc_3")
HAI_PTGD_TGD = ("du_toan_duoi_bien",)
HAI_CHU_KY = HAI_CT_TGD + HAI_PTGD_TGD


def _tep_py():
    for g, _d, ts in os.walk(GOC_APP):
        for t in sorted(ts):
            if t.endswith(".py"):
                p = os.path.join(g, t)
                rel = os.path.relpath(p, GOC_APP).replace(os.sep, "/")
                yield rel, io.open(p, encoding="utf-8").read()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. Bảng nói đúng quyết định
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg2_1_bang_dung_nhu_chu_tich_chot():
    """Sáu cửa, không hơn không kém, và mỗi cửa đúng số chữ ký đã chốt.

    Đỏ ở đây nghĩa là có người thêm hoặc bớt một cửa chính sách mà không ai ký lại bảng này.
    """
    assert set(CK.VAI_KY_CAN) == set(MOT_CHU_KY) | set(HAI_CHU_KY), (
        "So cua chinh sach doi so voi ban da chot 11/10/2026: " + repr(sorted(CK.VAI_KY_CAN)))
    for loai in MOT_CHU_KY:
        assert CK.VAI_KY_CAN[loai] == ("chutich",), f"{loai} phai la MOT chu ky Chu tich"
    for loai in HAI_CT_TGD:
        assert CK.VAI_KY_CAN[loai] == ("chutich", "tgd"), f"{loai} phai GIU Chu tich + TGD"
    for loai in HAI_PTGD_TGD:
        assert CK.VAI_KY_CAN[loai] == ("ptgd_doan", "tgd"), (
            f"{loai} doi nguoi ky 11/10/2026: P.TGD tour doan + TGD, Chu tich RA KHOI LUAT")
    assert "chi_ngoai_du_toan" not in CK.VAI_KY_CAN, (
        "Cong 15 co hai chu ky o HAI BUOC khac nhau (buoc bo phan + buoc duyet), nen no khong "
        "thuoc bang nay - bang nay noi ve MOT buoc ky. Dat no vao day la noi sai cau truc.")


def test_lg2_2_bang_phai_ghi_can_cu():
    """Một quyết định nới lỏng kiểm soát mà không ghi ngày và người quyết là một quyết định
    không rà được. Ba tháng nữa người đọc phải biết ai bỏ chữ ký thứ hai, và bỏ hôm nào."""
    assert CK.CAN_CU_VAI_KY and "11/10/2026" in CK.CAN_CU_VAI_KY
    assert "Chủ tịch" in CK.CAN_CU_VAI_KY


def test_lg2_3_go_sai_ten_loai_la_vo_ngay():
    """`can_ky` không có giá trị mặc định. Trả mặc định `("chutich","tgd")` nghe an toàn hơn,
    nhưng nó biến một lỗi gõ phím thành một cửa chạy bằng luật không ai khai."""
    import pytest
    for loai in CK.VAI_KY_CAN:
        assert CK.can_ky(loai) == CK.VAI_KY_CAN[loai]
    with pytest.raises(KeyError):
        CK.can_ky("tham_so_go_nham")


def test_lg2_4_mot_chu_ky_van_la_hai_nguoi():
    """Ba cửa một chữ ký VẪN đi qua `kiem_tra_nguoi_ky`, nên người trình không tự ký được.

    Đây là điều giữ cho "một chữ ký" khác với "một người làm trọn". Chủ tịch chốt cùng ngày.
    """
    import pytest
    from fastapi import HTTPException

    class U:
        role = "chutich"
        username = "ong_tuan"

    # người khác trình -> ký được
    CK.kiem_tra_nguoi_ky(U(), CK.can_ky("tham_so"), nguoi_trinh="ke_toan_a", da_ky={})
    # chính mình trình -> KHÔNG ký được, dù chỉ cần một chữ ký
    with pytest.raises(HTTPException):
        CK.kiem_tra_nguoi_ky(U(), CK.can_ky("tham_so"), nguoi_trinh="ong_tuan", da_ky={})


def test_lg2_5_du_chu_ky_theo_bang():
    assert CK.du_chu_ky_cua("tham_so", {"chutich": "x"}) is True
    assert CK.du_chu_ky_cua("quy_tac_hach_toan", {"chutich": "x"}) is False
    assert CK.du_chu_ky_cua("quy_tac_hach_toan", {"chutich": "x", "tgd": "y"}) is True
    assert CK.con_thieu_cua("quy_tac_hach_toan", {"chutich": "x"}) == ["Tổng giám đốc"]
    assert CK.con_thieu_cua("tham_so", {"chutich": "x"}) == []


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. Ba cửa một chữ ký không còn chỗ nào viết thẳng hai vai
# ═════════════════════════════════════════════════════════════════════════════════════════════
CUA_MOT_CHU_KY_TRONG_MA = {
    "api/v1/routes.py": ("sign_param", "tham_so"),
    "api/v1/hr.py": ("guide_rate_sign", "don_gia_hdv"),
}
# `hr.py` có hai cửa một chữ ký; khai riêng để đếm được cả hai.
CUA_MOT_CHU_KY_THEM = {"api/v1/hr.py": ("rate_sign", "gia_xe")}


def _ham(nguon: str, ten: str):
    cay = ast.parse(nguon)
    for n in ast.walk(cay):
        if isinstance(n, ast.FunctionDef) and n.name == ten:
            return n
    return None


def test_lg2_6_ba_cua_doc_bang_khong_viet_thang():
    """Cửa nào đã chuyển sang một chữ ký thì không được còn chuỗi `"tgd"` viết thẳng trong thân
    hàm ký — còn một chuỗi ấy nghĩa là còn một nơi nói luật cũ, và nơi ấy sẽ thắng vào một ngày
    nào đó."""
    nguon = {t: s for t, s in _tep_py()}
    can_soi = [("api/v1/routes.py", "sign_param"), ("api/v1/hr.py", "guide_rate_sign"),
               ("api/v1/hr.py", "rate_sign")]
    loi = []
    for tep, ten in can_soi:
        h = _ham(nguon[tep], ten)
        assert h is not None, f"khong thay ham {ten} trong {tep}"
        than = ast.get_source_segment(nguon[tep], h) or ""
        ma = "\n".join(d for d in than.split("\n") if not d.lstrip().startswith("#"))
        if '"tgd"' in ma or "'tgd'" in ma:
            loi.append(f"{tep}::{ten} con viet thang 'tgd'")
        if "VAI_KY_CAN" not in ma and "can_ky(" not in ma:
            loi.append(f"{tep}::{ten} khong doc bang VAI_KY_CAN")
    assert not loi, "; ".join(loi)


def test_lg2_7_ba_cua_hai_chu_ky_van_con_nguyen():
    """Siết một bên mà nới nhầm bên kia là chuyện xảy ra khi sửa hàng loạt. Câu này canh ba cửa
    KHÔNG đổi vẫn đòi đủ hai chữ ký."""
    nguon = {t: s for t, s in _tep_py()}
    h = _ham(nguon["services/hach_toan.py"], "ky")
    assert h is not None
    ma = ast.get_source_segment(nguon["services/hach_toan.py"], h) or ""
    assert "quy_tac_hach_toan" in ma, "cua quy tac hach toan phai doc bang VAI_KY_CAN"
    assert CK.can_ky("quy_tac_hach_toan") == ("chutich", "tgd")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. Mọi hàm ĐẶT chữ ký đều gọi `kiem_tra_nguoi_ky`, trừ cửa khai có tên
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _dat_chu_ky(h: ast.FunctionDef) -> bool:
    for n in ast.walk(h):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Attribute) and t.attr in ("signed_chutich", "signed_tgd"):
                    return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "setattr":
            if len(n.args) >= 2:
                a = n.args[1]
                if isinstance(a, ast.JoinedStr) and any(
                        isinstance(v, ast.Constant) and "signed_" in str(v.value)
                        for v in a.values):
                    return True
    return False


def test_lg2_8_moi_cua_ky_deu_goi_kiem_tra_nguoi_ky():
    """ĐÂY LÀ CÂU CHÍNH CỦA TỆP NÀY.

    `kiem_tra_nguoi_ky` sinh ra để chặn hai thứ: người trình tự ký, và MỘT NGƯỜI giữ nhiều tài
    khoản ký thay cả hai vai. Một cửa ký không gọi nó thì hai chữ ký của cửa ấy chưa chắc là hai
    người — tức là nó có hình thức của một lớp kiểm soát mà không có tác dụng của một lớp kiểm
    soát, và đó là loại hỏng tệ nhất vì nhìn vào thì thấy yên tâm.

    Đỏ ở đây nghĩa là vừa có một cửa ký mới mọc ra mà quên gọi. Cách xử: gọi hàm ấy, hoặc —
    nếu CÓ NGƯỜI QUYẾT là cố ý để mở — khai tên cửa vào `CK.KHONG_GOI_KIEM_TRA` kèm lý do.
    """
    thieu = []
    for tep, s in _tep_py():
        try:
            cay = ast.parse(s)
        except SyntaxError:          # pragma: no cover
            continue
        for n in ast.walk(cay):
            if not isinstance(n, ast.FunctionDef) or not _dat_chu_ky(n):
                continue
            than = ast.get_source_segment(s, n) or ""
            # Hai hàm đều là lớp kiểm soát hợp lệ. `kiem_tra_nguoi_ky` kiểm ba thứ; cửa nào có
            # danh sách vai tính theo từng hồ sơ thì dùng `kiem_tra_mot_nguoi_hai_vai` và tự giữ
            # phép chặn người-lập của riêng nó — xem `ops.step`.
            if "kiem_tra_nguoi_ky" in than or "kiem_tra_mot_nguoi_hai_vai" in than:
                continue
            khoa = f"{os.path.basename(tep)[:-3]}.{n.name}"
            if khoa in CK.KHONG_GOI_KIEM_TRA:
                continue
            thieu.append(f"{tep}::{n.name}")
    assert not thieu, ("CUA KY KHONG GOI kiem_tra_nguoi_ky va CHUA KHAI:\n"
                       + "\n".join(f"   . {x}" for x in thieu)
                       + "\n  Goi ham ay, hoac khai ten cua vao CK.KHONG_GOI_KIEM_TRA kem ly do.")


def test_lg2_9_cua_khai_mien_phai_co_ly_do_va_ngay():
    """Khai miễn mà không ghi vì sao là khai cho qua phép thử. Mỗi dòng miễn phải nêu được
    người quyết và ngày quyết, để lần rà sau đọc ra được ai chịu trách nhiệm."""
    assert CK.KHONG_GOI_KIEM_TRA, "danh sach mien khong duoc rong ma khong ai biet"
    for khoa, ly_do in CK.KHONG_GOI_KIEM_TRA.items():
        assert len(ly_do) > 80, f"{khoa}: ly do qua ngan de ai do doc lai hieu duoc"
        assert "11/10/2026" in ly_do or "/2026" in ly_do, f"{khoa}: thieu NGAY quyet"
        assert "Chủ tịch" in ly_do, f"{khoa}: thieu NGUOI quyet"


def test_lg2_10_cua_duoi_bien_van_dang_trong_danh_sach_mien():
    """Ghi thẳng ra để không ai đọc nhầm bảng `VAI_KY_CAN`: `du_toan_duoi_bien` ghi HAI chữ ký,
    nhưng chừng nào `tours.approve` còn trong danh sách miễn thì hai chữ ký ấy CHƯA CHẮC là hai
    người. Ngày bịt lỗ, xoá dòng này và xoá dòng trong `KHONG_GOI_KIEM_TRA` cùng lúc.

    CỔNG 15 THÌ ĐÃ BỊT ở chính đợt này (xem nhóm D dưới) — hai cửa tiền KHÔNG còn cùng trạng
    thái nữa, và chỗ khác nhau ấy là một quyết định chứ không phải một sự bỏ quên."""
    assert "tours.approve" in CK.KHONG_GOI_KIEM_TRA
    assert CK.can_ky("du_toan_duoi_bien") == ("ptgd_doan", "tgd")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. Cổng 15 — bảng sự thật, và một người không ký thay cả hai vai
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg2_11_ghi_va_doc_nguoi_da_ky_khop_nhau():
    """Một chỗ đọc, một chỗ ghi. Mỗi nơi tự tách chuỗi một kiểu là lại một chỗ lệch."""
    assert CK.doc_nguoi_da_ky("") == {}
    assert CK.doc_nguoi_da_ky("tgd:nv_b") == {"tgd": "nv_b"}
    assert CK.doc_nguoi_da_ky(" tgd:nv_b , chutich:ong_a ") == {"tgd": "nv_b", "chutich": "ong_a"}
    assert CK.doc_nguoi_da_ky("rac,,tgd:") == {}
    assert CK.ghi_nguoi_da_ky({"tgd": "nv_b", "chutich": "ong_a"}) == "chutich:ong_a,tgd:nv_b"
    assert CK.ghi_nguoi_da_ky({"tgd": ""}) == ""
    o = CK.ghi_nguoi_da_ky({"chutich": "x", "tgd": "y"})
    assert CK.doc_nguoi_da_ky(o) == {"chutich": "x", "tgd": "y"}


def test_lg2_12_bang_su_that_cong_15():
    """BỐN DÒNG CHỦ TỊCH ĐÃ XEM TRƯỚC KHI CHỐT, 11/10/2026:

        trong dự toán, dưới mốc : TGĐ
        trong dự toán, từ mốc   : Chủ tịch
        NGOÀI dự toán, dưới mốc : trưởng phòng (bước `cho_tp`) + TGĐ
        NGOÀI dự toán, TỪ MỐC   : trưởng phòng + TGĐ + Chủ tịch

    Dòng cuối là chỗ Chủ tịch chọn SIẾT: thiếu nó thì khoản ngoài dự toán 300 triệu lại nhẹ hơn
    cùng khoản ấy trong dự toán, và ngoại lệ dễ hơn lệ thường là chỗ người ta đi vòng qua.
    """
    from app.services import ops as OPS

    class R:
        nguong_duyet_ap_dung = 100_000_000.0
        amount = 0.0
        two_signatures = False

    def cap(tien, ngoai_du_toan):
        r = R(); r.amount = float(tien); r.two_signatures = bool(ngoai_du_toan)
        return OPS.cap_duyet(None, r)

    c = cap(50_000_000, False)
    assert (c["can_tgd"], c["can_chutich"]) == (True, False), "trong du toan, duoi moc: TGD"
    c = cap(300_000_000, False)
    assert (c["can_tgd"], c["can_chutich"]) == (False, True), "trong du toan, tu moc: Chu tich"
    c = cap(50_000_000, True)
    assert (c["can_tgd"], c["can_chutich"]) == (True, False), "NGOAI du toan, duoi moc: TGD"
    c = cap(300_000_000, True)
    assert (c["can_tgd"], c["can_chutich"]) == (True, True), (
        "NGOAI du toan, TU MOC: ca TGD va Chu tich - Chu tich chon SIET ngay 11/10/2026")


def test_lg2_13_cong_15_co_goi_phep_chan_mot_nguoi_hai_vai():
    """Cổng 15 ĐÃ BỊT ở đợt này. Câu này canh đúng hai thứ làm nên phép bịt ấy: hồ sơ có ô ghi
    TÊN người ký, và nhánh duyệt có so tên ấy với người đang bấm. Thiếu một trong hai thì phép
    chặn không có gì để so — đúng tình trạng trước 11/10/2026."""
    from app.models.ops import PaymentRequest
    assert hasattr(PaymentRequest, "nguoi_da_ky"), (
        "thieu o ghi TEN nguoi ky - co `signed_*` la co dung/sai, khong nho ai bam")
    nguon = {t: s for t, s in _tep_py()}
    h = _ham(nguon["services/ops.py"], "step")
    assert h is not None
    ma = ast.get_source_segment(nguon["services/ops.py"], h) or ""
    assert "doc_nguoi_da_ky" in ma and "ghi_nguoi_da_ky" in ma, (
        "nhanh duyet phai DOC nguoi da ky de so, va GHI ten nguoi vua ky")
    assert "kiem_tra_mot_nguoi_hai_vai" in ma, "nhanh duyet phai goi phep chan chung, khong tu viet"
