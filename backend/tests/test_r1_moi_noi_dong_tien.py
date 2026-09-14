# -*- coding: utf-8 -*-
"""R1 · Mối nối giữa `dong_tien.py` và `dong_tien_ky.py`, và lỗi trừ hai lần.

Tệp này sinh ra từ một tai nạn có thật, đo được ngày 14/9/2026:

    services/dong_tien.py : 339   tinh = DTK.tien_kha_dung(gia_tri, doi_soat)
    services/dong_tien_ky.py      → KHÔNG còn tên `tien_kha_dung`

Ngày 13/9 làn Phân quyền tách `tien_kha_dung` thành hai chỉ tiêu theo chốt của Chủ tịch. Tám tên
khác mà `dong_tien.py` gọi đều còn; đúng một tên mất. Từ lúc ấy mọi lần gọi đều ném AttributeError
– cả màn hình dòng tiền lẫn `bang_bon_moc()` đều hỏng. Dấu thời gian nói rõ chuyện gì xảy ra:
`dong_tien.py` sửa lần cuối 01:16, `dong_tien_ky.py` 18:38 cùng ngày. Người đổi tên không quay lại
chỗ gọi, và không phép thử nào kêu.

Hai nhóm phép thử:

  1. MỐI NỐI – đọc cây cú pháp của `dong_tien.py`, liệt kê mọi tên `DTK.x` nó gọi, đòi từng tên
     tồn tại trong `dong_tien_ky.py`. Rẻ, chạy trong một phần nghìn giây, và bắt được đúng loại
     tai nạn này cho mọi lần sau. Đọc cây cú pháp chứ không dùng biểu thức chính quy: regex bắt
     nhầm tên nằm trong chú thích, và một hàm canh kêu oan là một hàm canh sắp bị gỡ.

  2. TRỪ HAI LẦN – dựng đúng ví dụ 100 → 80 → 60 mà Chủ tịch chỉ đích danh, bằng CHÍNH hai hàm
     thật của `dong_tien_ky.py`, không dựng bản giả.
"""
import ast
import os

import pytest

from app.services import dong_tien_ky as DTK

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONG_TIEN = os.path.join(GOC, "app", "services", "dong_tien.py")
DONG_TIEN_KY = os.path.join(GOC, "app", "services", "dong_tien_ky.py")


def _ten_goi_qua(bi_danh: str, duong_dan: str) -> set[str]:
    """Mọi `<bí_danh>.x` xuất hiện trong tệp, đọc từ cây cú pháp."""
    cay = ast.parse(open(duong_dan, encoding="utf-8").read())
    ra = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id == bi_danh:
            ra.add(n.attr)
    return ra


def _ten_cong_khai(duong_dan: str) -> set[str]:
    """Tên mà một mô-đun cung cấp ra ngoài: hàm, lớp, và hằng gán ở mức mô-đun."""
    cay = ast.parse(open(duong_dan, encoding="utf-8").read())
    ra = set()
    for n in cay.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ra.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    ra.add(t.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            ra.add(n.target.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                ra.add(a.asname or a.name.split(".")[0])
    return ra


# =============================================================================================
# 1. Mối nối
# =============================================================================================

def test_moi_ten_dong_tien_goi_tu_DTK_deu_PHAI_ton_tai():
    """Phép thử canh chính. Đỏ nghĩa là có người vừa đổi tên mà quên một đầu."""
    goi = _ten_goi_qua("DTK", DONG_TIEN)
    co = _ten_cong_khai(DONG_TIEN_KY)
    thieu = sorted(g for g in goi if g not in co)
    assert not thieu, (
        f"dong_tien.py gọi {thieu} từ dong_tien_ky.py nhưng dong_tien_ky.py không có tên ấy. "
        f"Đây là AttributeError lúc chạy, không phải lỗi kiểu – nó chỉ hiện ra khi người dùng bấm "
        f"vào màn hình. Ai đổi tên thì sửa cả hai đầu.")


def test_phep_thu_nay_CO_KEU_khi_dang_keu(tmp_path):
    """Một hàm canh không bao giờ kêu thì không ai biết nó còn sống hay đã mục.

    Dựng một tệp giả gọi một tên không có thật, xác nhận phép so ở trên bắt được.
    """
    gia = tmp_path / "gia.py"
    gia.write_text("from app.services import dong_tien_ky as DTK\n"
                   "x = DTK.mot_ten_khong_he_ton_tai(1)\n", encoding="utf-8")
    goi = _ten_goi_qua("DTK", str(gia))
    co = _ten_cong_khai(DONG_TIEN_KY)
    assert "mot_ten_khong_he_ton_tai" in goi
    assert [g for g in goi if g not in co] == ["mot_ten_khong_he_ton_tai"]


def test_ten_cu_tien_kha_dung_DA_BI_XOA_khoi_dong_tien_ky():
    """Ghim lại sự thật đo được, để không ai vô tình dựng lại tên cũ với nghĩa cũ.

    Dựng lại `tien_kha_dung` trong dong_tien_ky.py là dựng lại đúng lỗi trừ hai lần: cái tên ấy
    mang nghĩa "đã trừ lệnh chi", mà số đầu kỳ thì không được trừ.
    """
    assert "tien_kha_dung" not in _ten_cong_khai(DONG_TIEN_KY)
    assert "tien_duoc_phep_su_dung" in _ten_cong_khai(DONG_TIEN_KY)
    assert "tien_con_bo_tri_moi" in _ten_cong_khai(DONG_TIEN_KY)


def test_dong_tien_KHONG_con_goi_ten_cu():
    assert "tien_kha_dung" not in _ten_goi_qua("DTK", DONG_TIEN)


# =============================================================================================
# 2. Lỗi trừ hai lần – ví dụ 100 → 80 → 60 của Chủ tịch
# =============================================================================================

CO = 100_000_000          # số dư ngân hàng đã đối soát
LENH_CHI = 20_000_000     # một lệnh chi đã duyệt, chưa chuyển
TRONG_SO_DU = {"thu_ho_khach": True, "ky_quy_lu_hanh": True}


def _a():
    return DTK.tien_duoc_phep_su_dung(
        {"so_du_ngan_hang": CO, "tien_mat": 0, "thu_ho_khach": 0, "ky_quy_lu_hanh": 0},
        TRONG_SO_DU, doi_soat_den=None)


def test_A_KHONG_tru_lenh_chi():
    a = _a()
    assert a["du_du_lieu"] is True
    assert a["so"] == CO, "A là số đầu kỳ – nó KHÔNG được trừ lệnh chi đã duyệt chưa chuyển"


def test_B_co_tru_lenh_chi_va_TU_KHAI_khong_dung_lam_dau_ky():
    b = DTK.tien_con_bo_tri_moi(_a(), LENH_CHI)
    assert b["so"] == CO - LENH_CHI
    assert b["dung_lam_dau_ky"] is False, \
        "B phải tự khai là không dùng làm đầu kỳ – đây là hàng rào cuối chặn lỗi trừ hai lần"


def test_lay_B_lam_dau_ky_thi_RA_DUNG_LOI_100_80_60():
    """Phép thử này CỐ TÌNH làm sai, để chứng minh con số sai là bao nhiêu và sai ở đâu.

    Nó không canh mã – nó ghi lại bài toán. Bỏ nó đi thì ba tháng sau không ai còn nhớ vì sao
    `dung_lam_dau_ky=False` lại quan trọng đến thế.
    """
    b = DTK.tien_con_bo_tri_moi(_a(), LENH_CHI)
    dau_ky_sai = b["so"]                      # 80 – đây là cách bản cũ làm
    cuoi_ky_sai = dau_ky_sai - LENH_CHI       # dòng tra_ncc trừ lần nữa → 60
    assert (dau_ky_sai, cuoi_ky_sai) == (80_000_000, 60_000_000)

    dau_ky_dung = _a()["so"]                  # 100
    cuoi_ky_dung = dau_ky_dung - LENH_CHI     # 80
    assert (dau_ky_dung, cuoi_ky_dung) == (100_000_000, 80_000_000)
    assert cuoi_ky_dung - cuoi_ky_sai == LENH_CHI, \
        "chênh lệch giữa hai cách đúng bằng số lệnh chi – đó là dấu của việc trừ hai lần"


def test_dong_tien_lay_A_lam_dau_ky_chu_khong_lay_B():
    """Đọc thẳng mã: `bang_bon_moc` phải gán dau_ky từ khoá của chỉ tiêu A.

    Canh bằng cây cú pháp chứ không bằng chuỗi, để không bắt nhầm chữ trong chú thích.
    """
    cay = ast.parse(open(DONG_TIEN, encoding="utf-8").read())
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "bang_bon_moc")
    gan = [n for n in ast.walk(ham)
           if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "dau_ky" for t in n.targets)]
    assert gan, "bang_bon_moc không còn gán dau_ky – cấu trúc đổi thì phép thử này phải đổi theo"
    khoa = [n.slice.value for n in ast.walk(gan[0])
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)]
    assert "tien_duoc_phep_su_dung" in khoa, \
        f"dau_ky đang lấy từ khoá {khoa} – phải lấy chỉ tiêu A, không lấy tien_kha_dung (chỉ tiêu B)"
    assert "tien_kha_dung" not in khoa


def test_thieu_mot_thanh_phan_thi_KHONG_RA_SO_chu_khong_ra_0():
    a = DTK.tien_duoc_phep_su_dung(
        {"so_du_ngan_hang": None, "tien_mat": 0, "thu_ho_khach": 0, "ky_quy_lu_hanh": 0},
        TRONG_SO_DU)
    assert a["du_du_lieu"] is False
    assert "so" not in a, "thiếu đầu vào mà vẫn trả khoá 'so' thì nơi nhận sẽ viết `so or 0`"
    assert DTK.tien_con_bo_tri_moi(a, LENH_CHI)["tinh_duoc"] is False


def test_chua_biet_khoan_han_che_nam_o_dau_thi_KHONG_DOAN():
    """Tiền đề của `dong_tien.py` là cả hai khoản nằm trong số dư. Nếu một ngày không còn chắc,
    để None – và hàm phải trả 'chưa xác minh' chứ không tự chọn một phía."""
    a = DTK.tien_duoc_phep_su_dung(
        {"so_du_ngan_hang": CO, "tien_mat": 0, "thu_ho_khach": 5_000_000, "ky_quy_lu_hanh": 0},
        {"thu_ho_khach": None, "ky_quy_lu_hanh": True})
    assert a["du_du_lieu"] is False
    assert "so" not in a
    assert "thu_ho_khach" in a["chua_ro_vi_tri"]


@pytest.mark.parametrize("trong,mong", [(True, CO - 5_000_000), (False, CO)])
def test_khoan_han_che_chi_bi_tru_khi_nam_TRONG_so_du(trong, mong):
    a = DTK.tien_duoc_phep_su_dung(
        {"so_du_ngan_hang": CO, "tien_mat": 0, "thu_ho_khach": 5_000_000, "ky_quy_lu_hanh": 0},
        {"thu_ho_khach": trong, "ky_quy_lu_hanh": True})
    assert a["so"] == mong


def test_bang_bon_moc_NOI_RO_dau_ky_la_chi_tieu_nao():
    """Khoá `tien_kha_dung_dau_ky` nay chứa chỉ tiêu A, nhưng tên nó vẫn mang chữ "khả dụng".

    Tên ấy là MÃ DÒNG dùng chung với `dong_tien_pham_vi` và `khung_dong_tien` nên chưa đổi được
    ngay. Trong lúc chờ, bảng phải tự khai con số đầu kỳ là chỉ tiêu nào – nếu không thì ba tháng
    sau có người đọc tên khoá rồi kết luận nó đã trừ lệnh chi, và trừ thêm một lần nữa.
    """
    cay = ast.parse(open(DONG_TIEN, encoding="utf-8").read())
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "bang_bon_moc")
    khoa = {n.value for n in ast.walk(ham)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "chi_tieu_dau_ky" in khoa
    assert "tien_duoc_phep_su_dung" in khoa


# =============================================================================================
# CẦU SANG MÀN HÌNH 01 – canh TỪ PHÍA NÀY
# =============================================================================================
# `khung_dong_tien.py` (làn TC-8) đã có một phép thử canh cây cầu này, và nó ĐÃ BẮT ĐƯỢC lỗi ngày
# 14/9/2026. Phép thử dưới đây làm CÙNG một việc nhưng đứng ở đầu bên này, và đó là chủ ý:
#
#   · tệp kia thuộc làn khác. Nó có thể bị xoá, đổi tên, hoặc tạm tắt mà làn này không hay.
#   · khi nó đỏ, nó đỏ ở tệp của TC-8 – người sửa sẽ đi tìm lỗi trong tệp của TC-8. Ngày 14/9 mất
#     hai mươi hai phút CI và một lời báo cáo sai cho Chủ tịch đúng vì chỗ đứng ấy.
#
# Hàng rào hai đầu là cố ý trùng. Chi phí là một phép thử; giá của việc thiếu nó đã trả rồi.

def test_moi_dong_lay_so_tu_so_deu_BAC_DUOC_CAU_sang_man_hinh_01():
    """Mọi mã dòng của bảng phải có mặt ở cây cầu bên `khung_dong_tien.py`.

    Thiếu một mã = một dòng TRỐNG trên màn hình 01 của Chủ tịch. Không lỗi, không cảnh báo: ô
    trống trông y như "chưa có số", nên không ai đi hỏi.
    """
    from app.services import dong_tien_pham_vi as PV
    from app.services import khung_dong_tien as K

    cau = set(K.MA_SEC_SANG_DT) | set(K.GHI_NHO_SANG_DT)
    thieu = sorted(d.ma for d in PV.CAC_DONG if d.tu_so_nghia_vu and d.ma not in cau)
    assert thieu == [], (
        f"đổi mã dòng mà quên đầu kia: {thieu}. Mã dòng là tên ĐỐI NGOẠI – đổi nó là việc HAI "
        f"ĐẦU. Sửa MA_SEC_SANG_DT trong khung_dong_tien.py cùng lần đẩy, hoặc đừng đổi mã.")


def test_mo_ta_nhom_cua_moi_dong_deu_tro_toi_mot_nhom_CO_THAT_trong_so():
    """`nhom` sai chính tả thì dòng ấy cộng ra 0 – và 0 ở dòng chi đọc là "kỳ này không phải trả"."""
    from app.models.nghia_vu import NHOM
    from app.services import dong_tien_pham_vi as PV

    for d in PV.CAC_DONG:
        if d.tu_so_nghia_vu:
            assert d.nhom in NHOM, f"{d.ma}: khai nhóm '{d.nhom}' không có trong sổ nghĩa vụ"
        else:
            assert d.nhom is None, f"{d.ma}: dòng riêng của bảng mà lại khai nhóm"


def test_khong_dong_nao_hai_dong_cung_tro_ve_MOT_nhom_cua_so():
    """Hai dòng cùng nhận một nhóm thì `NHOM_SANG_MA` chỉ giữ được một, và dòng kia lặng lẽ rỗng."""
    from app.services import dong_tien_pham_vi as PV

    nhom = [d.nhom for d in PV.CAC_DONG if d.nhom]
    assert len(nhom) == len(set(nhom)), "hai dòng cùng khai một nhóm của sổ"
    assert len(PV.NHOM_SANG_MA) == len(nhom)


# =============================================================================================
# ĐỘT BIẾN TƯƠNG ĐƯƠNG – đo được, ghi lại thay vì giấu
# =============================================================================================
# Thử bảy phép đột biến trên hai tệp; SÁU bị bắt. Con thứ bảy THOÁT:
#
#     đổi  `if han_che_nam_trong.get(ma)`
#     thành `if han_che_nam_trong.get(ma) is not False`
#
# Đo lại thì đây là đột biến TƯƠNG ĐƯƠNG, không phải lỗ hổng của bộ phép thử: `chua_ro_vi_tri`
# đã chặn mọi giá trị None và trả về sớm TRƯỚC khi tới phép cộng, nên tới chỗ ấy mỗi khoản hạn
# chế chỉ còn hai giá trị True hoặc False – và với hai giá trị ấy thì hai cách viết cho kết quả
# y hệt nhau.
#
# Tương đương ấy ĐỨNG ĐƯỢC NHỜ hàng rào phía trên. Ngày nào ai đó nới `chua_ro_vi_tri` ra thì nó
# hết tương đương ngay, và lúc ấy `is not False` sẽ lặng lẽ đoán "có nằm trong số dư" cho một
# khoản chưa ai xác định. Phép thử dưới đây ghim chính hàng rào ấy.

def test_hang_rao_chan_None_TRUOC_phep_cong_van_con_song():
    """Ghim điều kiện làm cho đột biến R7 là tương đương. Đỏ = phải xem lại R7."""
    a = DTK.tien_duoc_phep_su_dung(
        {"so_du_ngan_hang": CO, "tien_mat": 0, "thu_ho_khach": 1, "ky_quy_lu_hanh": 1},
        {"thu_ho_khach": None, "ky_quy_lu_hanh": None})
    assert sorted(a["chua_ro_vi_tri"]) == ["ky_quy_lu_hanh", "thu_ho_khach"]
    assert "so" not in a, ("hàng rào đã nới: giá trị None nay đi tới được phép cộng, và cách viết "
                           "điều kiện trừ khoản hạn chế không còn tương đương nữa")
