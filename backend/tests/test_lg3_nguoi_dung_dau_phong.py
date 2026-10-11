# -*- coding: utf-8 -*-
"""Đợt LG3 — người đứng đầu phòng ký, và NƠI ĐỌC luật cũng phải đọc bảng luật.

Đợt LG2 dựng `test_lg2_8` quét mọi hàm ĐẶT chữ ký. Nó bắt được hai cửa đã kể thiếu — nhưng nó
chỉ nhìn MỘT CHIỀU, và chiều còn lại là chỗ LG2 để lại ba lỗi thật:

    dong_tien_ky.muc_du_phong            mức dự phòng mới KHÔNG BAO GIỜ có hiệu lực
    ptgd_doan.duoi_bien_cho_hai_chu_ky   báo thiếu chữ ký "Chủ tịch" — sai tên người ký
    ngoai_le._tat_chan_giay_xe           bỏ trống ô "người quyết"

Tệp này canh bốn điều:
  A. Bảng người đứng đầu phòng khớp với danh sách phòng đã có, không khai lại lần thứ ba.
  B. Chuyến dưới biên: ai ký tuỳ MẢNG, và chuyến không thuộc mảng nào thì CHẶN.
  C. Người xác nhận bộ phận không duyệt được chính hồ sơ ấy.
  D. Mọi nơi ĐỌC chữ ký đều hỏi bảng luật, trừ nơi chỉ hiển thị — khai có tên.
"""
import ast
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_lg3.db")

from app.services import bao_cao_phong as BCP  # noqa: E402
from app.services import chu_ky as CK  # noqa: E402

GOC_APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")


def _tep_py():
    for g, _d, ts in os.walk(GOC_APP):
        for t in sorted(ts):
            if t.endswith(".py"):
                p = os.path.join(g, t)
                rel = os.path.relpath(p, GOC_APP).replace(os.sep, "/")
                yield rel, io.open(p, encoding="utf-8").read()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. Bảng người đứng đầu khớp với danh sách phòng ĐÃ CÓ
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg3_1_moi_phong_deu_co_nguoi_dung_dau():
    """Thêm một phòng mà quên khai người đứng đầu là ĐỎ ở đây.

    Không khai lại danh sách phòng trong `chu_ky`: lấy thẳng từ `bao_cao_phong.PHONG`. Bộ phận
    trực thuộc (ô `thuoc`) thì dùng người đứng đầu của phòng mẹ, nên không cần dòng riêng.
    """
    thieu = []
    for ma, cfg in BCP.PHONG.items():
        if cfg.get("thuoc"):
            continue
        if ma not in CK.NGUOI_DUNG_DAU_PHONG:
            thieu.append(ma)
    assert not thieu, ("PHONG CHUA KHAI NGUOI DUNG DAU: " + ", ".join(thieu)
                       + ". Them dong vao chu_ky.NGUOI_DUNG_DAU_PHONG, co nguoi quyet.")


def test_lg3_2_khong_khai_thua_phong_khong_co_that():
    """Chiều ngược lại: một mã phòng không có trong sổ phòng là một dòng chết, và dòng chết thì
    không ai dọn — nó chỉ nằm đó làm người đọc tin là có thật."""
    that = set(BCP.PHONG)
    thua = [ma for ma in CK.NGUOI_DUNG_DAU_PHONG if ma not in that]
    assert not thua, f"Ma phong khong co trong bao_cao_phong.PHONG: {thua}"


def test_lg3_3_phong_me_chep_dung_quan_he_da_khai():
    """`PHONG_ME` chép lại ô `thuoc` của `bao_cao_phong`, không tự đặt. Lệch là ĐỎ."""
    assert CK.PHONG_ME == BCP.TRUC_THUOC, (
        f"PHONG_ME={CK.PHONG_ME} khac TRUC_THUOC={BCP.TRUC_THUOC}")
    for bo_phan, me in CK.PHONG_ME.items():
        assert CK.nguoi_dung_dau(bo_phan) == CK.nguoi_dung_dau(me)


def test_lg3_4_phong_cua_mang_dung_nghich_dao():
    """Hai bộ mã (mảng / phòng) có sẵn từ trước; chỗ dịch giữa chúng chỉ được có MỘT."""
    nghich_dao = {v: k for k, v in BCP.MANG_CUA_PHONG.items()}
    assert CK.PHONG_CUA_MANG == nghich_dao, (
        f"PHONG_CUA_MANG={CK.PHONG_CUA_MANG} khong phai nghich dao cua {BCP.MANG_CUA_PHONG}")


def test_lg3_5_bang_phai_ghi_can_cu():
    assert "11/10/2026" in CK.CAN_CU_NGUOI_DUNG_DAU
    assert "Chủ tịch" in CK.CAN_CU_NGUOI_DUNG_DAU


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. Chuyến dưới biên: ai ký tuỳ MẢNG
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg3_6_duoi_bien_ky_theo_mang():
    """Chủ tịch chốt 11/10/2026: người đứng đầu PHÒNG BÁN nó + TGĐ."""
    assert CK.can_ky_duoi_bien("doan") == ("ptgd_doan", "tgd")
    assert CK.can_ky_duoi_bien("le") == ("gd_kd", "tgd")


def test_lg3_7_chuyen_khong_thuoc_mang_nao_thi_CHAN():
    """Dịch vụ lẻ không thuộc mảng nào. CHẶN và nói ra, không chọn bừa một phòng — hệ thống nói
    ra chỗ nó không biết là cách duy nhất để người ta đi sửa dữ liệu gốc."""
    for mang in ("", None, "khong_co"):
        with pytest.raises(ValueError):
            CK.can_ky_duoi_bien(mang)
    assert "không thuộc mảng" in CK.CHUYEN_KHONG_THUOC_MANG


def test_lg3_8_cua_duoi_bien_doc_bang_chu_khong_viet_thang():
    nguon = {t: s for t, s in _tep_py()}
    ma = nguon["services/tours.py"]
    than = "\n".join(d for d in ma.split("\n") if not d.lstrip().startswith("#"))
    assert "can_ky_duoi_bien" in than, "tours.py phai hoi bang luat theo MANG"
    assert '"ptgd_doan"' not in than, "tours.py con viet thang ten vai - luat phai o bang"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. Người xác nhận bộ phận không duyệt
# ═════════════════════════════════════════════════════════════════════════════════════════════
def test_lg3_9_nguoi_xac_nhan_bo_phan_khong_duyet():
    """Chủ tịch chốt 11/10/2026, cho MỌI hồ sơ chi.

    Không có câu này thì TGĐ — người xác nhận bộ phận được, và duyệt được — bấm hai bước là một
    mình ký cả hai vế. Phép chặn cũ chỉ so với NGƯỜI LẬP, nên nó không bắt được chuyện ấy.
    Không cần cột mới: hồ sơ đã ghi `tp_by`.
    """
    nguon = {t: s for t, s in _tep_py()}
    cay = ast.parse(nguon["services/ops.py"])
    h = next((n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef) and n.name == "step"), None)
    assert h is not None
    than = ast.get_source_segment(nguon["services/ops.py"], h) or ""
    ma = "\n".join(d for d in than.split("\n") if not d.lstrip().startswith("#"))
    assert "tp_by" in ma, "nhanh duyet phai so voi nguoi xac nhan bo phan (`tp_by`)"


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. Mọi nơi ĐỌC chữ ký đều hỏi bảng luật — đây là câu chính của tệp này
# ═════════════════════════════════════════════════════════════════════════════════════════════
# Những cái tên NÀY là "đã hỏi bảng luật". `cap_duyet` nằm trong danh sách vì nó CHÍNH LÀ bảng
# luật của cấp duyệt đề nghị chi — một phép suy có tên, bốn nơi cùng đọc, dựng ở Đợt F1.
HOI_BANG_LUAT = ("can_ky", "du_chu_ky", "da_ky_cua", "con_thieu", "VAI_KY_CAN",
                 "cap_duyet", "doc_nguoi_da_ky", "kiem_tra_mot_nguoi_hai_vai")


def test_lg3_10_moi_noi_doc_chu_ky_deu_hoi_bang_luat():
    """ĐỢT LG2 ĐỂ LẠI BA LỖI Ở ĐÂY, và hàng rào của LG2 không thấy vì nó chỉ quét nơi ĐẶT.

    Một hàm tự đọc `signed_chutich and signed_tgd` là một hàm khai lại luật. Ngày luật đổi — và
    ngày 11/10/2026 nó đã đổi — hàm ấy vẫn chạy bằng luật cũ, im lặng, và người đọc màn hình tin
    vào con số sai. Đỏ ở đây nghĩa là vừa có thêm một chỗ như thế.

    Cách xử: hỏi `chu_ky.can_ky(...)` / `du_chu_ky_cua(...)` / `da_ky_cua(...)`; hoặc nếu nó chỉ
    HIỂN THỊ trạng thái chứ không quyết định gì thì khai tên vào `CK.CHI_DOC_TRANG_THAI` kèm lý do.
    """
    xau = []
    for tep, s in _tep_py():
        if tep == "services/chu_ky.py":
            continue
        try:
            cay = ast.parse(s)
        except SyntaxError:          # pragma: no cover
            continue
        for n in ast.walk(cay):
            if not isinstance(n, ast.FunctionDef):
                continue
            than = ast.get_source_segment(s, n) or ""
            ma = "\n".join(d for d in than.split("\n") if not d.lstrip().startswith("#"))
            if "signed_chutich" not in ma and "signed_tgd" not in ma:
                continue
            if any(k in ma for k in HOI_BANG_LUAT):
                continue
            khoa = f"{os.path.basename(tep)[:-3]}.{n.name}"
            if khoa in CK.CHI_DOC_TRANG_THAI:
                continue
            xau.append(f"{tep}::{n.name}")
    assert not xau, ("NOI DOC CHU KY MA KHONG HOI BANG LUAT:\n"
                     + "\n".join(f"   . {x}" for x in xau)
                     + "\n  Hoi chu_ky.can_ky/du_chu_ky_cua/da_ky_cua, hoac khai ten vao "
                       "CK.CHI_DOC_TRANG_THAI kem ly do.")


def test_lg3_11_khong_con_hang_so_hai_cot_chu_ky_viet_thang():
    """`HAI_CHU_KY = ("signed_tgd", "signed_chutich")` ở `dong_tien_ky` chính là luật viết thẳng
    ở MỨC MÔ-ĐUN, ngoài mọi hàm — nên câu trên không thấy. Câu này canh riêng kiểu ấy."""
    xau = []
    for tep, s in _tep_py():
        if tep == "services/chu_ky.py":
            continue
        for i, l in enumerate(s.split("\n"), 1):
            if l.startswith((" ", "\t")) or l.lstrip().startswith("#"):
                continue
            if "signed_chutich" in l or "signed_tgd" in l:
                xau.append(f"{tep}:{i}  {l.strip()[:70]}")
    assert not xau, ("HANG SO MUC MO-DUN KHAI LAI LUAT CHU KY:\n"
                     + "\n".join(f"   . {x}" for x in xau))


def test_lg3_12_khai_mien_phai_co_ly_do():
    """Khai miễn mà không ghi vì sao là khai cho qua phép thử."""
    assert CK.CHI_DOC_TRANG_THAI
    for khoa, ly_do in CK.CHI_DOC_TRANG_THAI.items():
        assert len(ly_do) > 30, f"{khoa}: ly do qua ngan"
