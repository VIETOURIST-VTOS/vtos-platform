# -*- coding: utf-8 -*-
"""ĐỢT DỌN-6 — hàng rào cho việc tự đóng dòng sổ khi gộp.

Mỗi phép thử dưới đây canh MỘT câu có thể làm hỏng sổ, không canh cú pháp.

Thứ tự đọc: khớp đúng → KHÔNG khớp kiểu "chứa" → bốn chốt → đổi đúng một ô → không mở lại dòng cũ.

LUẬT LỚN NHẤT là phép thử số 2. Mã `R1` nằm trong chuỗi `r10`; nếu luật so kiểu "chứa" thì một
nhánh của R-10 sẽ lặng lẽ đóng dòng của R-1, và làn R-1 mất lớp bảo vệ mà không ai biết. Đỏ ở đó
nghĩa là ai đó vừa nới luật khớp — ĐỪNG sửa phép thử cho hết đỏ.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.dong_so import (  # noqa: E402
    DANG_LAM,
    chon,
    chuan,
    cua_so,
    doc_dong_dang_lam,
    dong_mot_dong,
    ma_cua_dong,
)

MA = ["backend/app/services/access.py"]  # một tệp mã bất kỳ, để qua chốt "nhánh dọn sổ"


def _dong(ma: str, tep: str = "backend/app/x.py", tt: str = "đang làm") -> str:
    return f"| Phân quyền | **{ma} — MÔ TẢ GÌ ĐÓ** | {tep}, docs/dang-lam/phan-quyen.md | 20-10-2026 01:00 | {tt} |"


# ── 1. khớp đúng ────────────────────────────────────────────────────────────────────────────
def test_ds1_1_khop_ma_binh_thuong():
    d = doc_dong_dang_lam(_dong("R3b"))
    ra, ly_do = chon(d, "pq-r3b-danh-muc-bo-phan-17-10", MA)
    assert [x["ma"] for x in ra] == ["R3b"], ly_do


def test_ds1_2_khop_ma_co_dau_va_gach():
    """`DỌN-5` trong sổ ↔ `don5` trong tên nhánh. Lệch dấu không được làm trượt."""
    d = doc_dong_dang_lam(_dong("DỌN-5"))
    ra, _ = chon(d, "pq-don5-ci-main-va-dong-so-16-10", MA)
    assert [x["ma"] for x in ra] == ["DỌN-5"]


def test_ds1_3_mot_nhanh_dong_duoc_nhieu_dot():
    """Đo được 19/10: `pq-e13-b03-tl1-tra-lai` mang hai đợt và đóng cả hai dòng."""
    s = _dong("E13-B03") + "\n" + _dong("TL-1", tep="backend/app/y.py")
    ra, _ = chon(doc_dong_dang_lam(s), "pq-e13-b03-tl1-tra-lai-19-10", MA)
    assert sorted(x["ma"] for x in ra) == ["E13-B03", "TL-1"]


# ── 2. LUẬT LỚN NHẤT: không khớp kiểu "chứa" ────────────────────────────────────────────────
def test_ds1_4_ma_ngan_KHONG_bi_nhanh_ma_dai_dong_nham():
    """`r1` nằm trong `r10`. So kiểu "chứa" thì R-10 đóng nhầm dòng R-1 — và không ai thấy."""
    d = doc_dong_dang_lam(_dong("R-1"))
    ra, ly_do = chon(d, "pq-r10-mot-viec-khac-20-10", MA)
    assert ra == [], f"R-10 vừa đóng nhầm dòng R-1: {[x['ma'] for x in ra]}"
    assert "không mã nào" in ly_do


def test_ds1_5_ma_dai_khong_khop_nhanh_ma_ngan():
    d = doc_dong_dang_lam(_dong("HD-Q2a"))
    ra, _ = chon(d, "vg-hd-q2ab-dem-luot-man-hinh-16-10d", MA)
    assert ra == [], "q2ab không phải q2a — phải trượt"


# ── 3. bốn chốt ─────────────────────────────────────────────────────────────────────────────
def test_ds1_6_chot_ma_trung_thi_khong_dong_gi():
    """Sổ CÓ mã trùng thật (`qt1`, `dl` — đo 20/10/2026), nên chốt này không phải phòng xa."""
    s = _dong("QT-1") + "\n" + _dong("QT-1", tep="backend/app/khac.py")
    ra, ly_do = chon(doc_dong_dang_lam(s), "pq-qt1-quyet-toan-chuyen-13-10", MA)
    assert ra == [], "hai dòng cùng mã mà vẫn đóng — một trong hai thuộc làn khác"
    assert "nhiều hơn một dòng" in ly_do


def test_ds1_7_chot_qua_ba_dong():
    s = "\n".join(_dong(m, tep=f"backend/app/{m}.py") for m in ["A1", "A2", "A3", "A4"])
    ra, ly_do = chon(doc_dong_dang_lam(s), "pq-a1-a2-a3-a4-gom-bon-20-10", MA)
    assert ra == [], "khớp bốn dòng mà vẫn đóng — luật khớp hỏng thì phải dừng"
    assert "quá 3" in ly_do


def test_ds1_8_chot_nhanh_chi_don_so():
    """Nhánh chỉ sửa sổ là nhánh dọn, không phải nhánh làm việc.

    Đo được 20/10: 8 trong 185 lần gộp là loại này, và chúng chính là chỗ bản đo đầu báo nhầm.
    """
    d = doc_dong_dang_lam(_dong("PD-1"))
    ra, ly_do = chon(d, "va-main7-dong-pd1-ve-xong-09-10", ["docs/dang-lam/vong.md"])
    assert ra == [], "nhánh chỉ dọn sổ mà vẫn đóng dòng"
    assert "nhánh dọn sổ" in ly_do


def test_ds1_9_khong_co_dong_dang_lam_nao_thi_im_lang():
    ra, ly_do = chon([], "pq-r3b-gi-do-17-10", MA)
    assert ra == [] and "không mã nào" in ly_do


# ── 4. đổi đúng một ô ───────────────────────────────────────────────────────────────────────
def test_ds1_10_chi_doi_o_trang_thai_moi_ky_tu_khac_giu_nguyen():
    cu = _dong("R3b")
    moi = dong_mot_dong(cu)
    assert moi.endswith("| xong |")
    assert moi[: -len("| xong |")] == cu.rstrip()[: -len(DANG_LAM)], "có ký tự khác bị đụng"
    # mô tả và danh sách tệp phải nguyên vẹn
    assert moi.split("|")[2] == cu.split("|")[2]
    assert moi.split("|")[3] == cu.split("|")[3]
    assert moi.split("|")[4] == cu.split("|")[4]


def test_ds1_11_khong_mo_lai_dong_da_xong():
    s = _dong("R3b", tt="xong")
    assert doc_dong_dang_lam(s) == [], "dòng `xong` lọt vào danh sách được xét"


def test_ds1_12_dong_khong_doc_duoc_ma_thi_khong_bao_gio_khop():
    s = "| Phân quyền | không có mã ở đầu | backend/app/x.py | 20-10 | đang làm |"
    assert doc_dong_dang_lam(s) == []


# ── 5. hàm nền ──────────────────────────────────────────────────────────────────────────────
def test_ds1_13_chuan_hoa_bo_dau_va_gach():
    assert chuan("DỌN-5") == "don5"
    assert chuan("HD-Q2a") == "hdq2a"
    assert chuan("E13-B03") == "e13b03"


def test_ds1_14_cua_so_ghep_toi_ba_doan():
    cs = cua_so("vg-hd-dg3-dong-y-cong-khai")
    assert "hddg3" in cs and "hd" in cs and "dg3" in cs
    assert "vghddg3" in cs
    assert "hddg3dongy" not in cs, "ghép quá ba đoạn thì cửa sổ nở ra vô tội vạ"


def test_ds1_15_ma_cua_dong_doc_dung_cot():
    assert ma_cua_dong(_dong("XN-1")) == "XN-1"
    assert ma_cua_dong("| Vòng | **R3b — ABC** | a.py | 1 | đang làm |") == "R3b"
