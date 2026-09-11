# -*- coding: utf-8 -*-
"""PQ-3b · Cửa thứ hai của cổng quyền AI: xét NỘI DUNG, không chỉ xét vai trò.

Ca thật, đo trên bản đang chạy sáng 11/9/2026: sáu tin gửi khách ở mức 3, cả sáu mang
nguon="quy_tac", trong khi 120/121 lượt chạy ghi lỗi "chưa cấu hình ANTHROPIC_API_KEY". Lời gọi mô
hình hỏng, mã rơi về một câu dựng sẵn, rồi vẫn gửi đi.

Chỗ hỏng không nằm ở bảng quyền – bảng trả lời đúng câu nó được hỏi. Chỗ hỏng là câu ấy được hỏi
lúc BẮT ĐẦU, trước khi biết ai thật sự viết ra nội dung sắp ra khỏi công ty.

Hệ quả nguy hiểm nhất là hệ quả ngược đời: một lần gọi mô hình HỎNG lại biến thành một tin ĐÃ GỬI,
nên hệ thống càng hỏng thì càng gửi – và nhật ký vẫn trông lành vì có ghi lỗi tử tế ở cột bên cạnh.
"""
import re
from pathlib import Path

import pytest

from app.services import ai_quyen as AQ

GOC = Path(__file__).resolve().parents[2]
INBOX = GOC / "backend" / "app" / "services" / "inbox.py"


# ---------------------------------------------------------------------------------------------
# 1. Bản thân cái cửa
# ---------------------------------------------------------------------------------------------

def test_noi_dung_quy_tac_khong_duoc_tu_gui_o_nhom_viec_cua_mo_hinh():
    duoc, vi_sao = AQ.noi_dung_duoc_tu_gui("tin_khach", "quy_tac")
    assert duoc is False
    assert len(vi_sao) >= 40, "chặn mà không nói vì sao thì người đọc mã sau sẽ gỡ nó ra"
    assert "loai_noi_dung" in vi_sao, "phải chỉ đúng ràng buộc mà câu dựng sẵn không đi qua"


def test_noi_dung_mo_hinh_viet_thi_duoc_tu_gui():
    assert AQ.noi_dung_duoc_tu_gui("tin_khach", "claude") == (True, "")


def test_nhom_viec_ma_xac_dinh_thi_nguoc_lai():
    """canh_bao là mức 4 vì nó do MÃ làm. Mô hình viết cảnh báo thì mất đúng cái tính xác định ấy."""
    assert AQ.noi_dung_duoc_tu_gui("canh_bao", "quy_tac")[0] is True
    duoc, vi_sao = AQ.noi_dung_duoc_tu_gui("canh_bao", "claude")
    assert duoc is False and "quy tắc xác định" in vi_sao


def test_nguon_la_gi_khong_ro_thi_coi_nhu_khong_duoc():
    """Hỏng thì đóng. Một nguồn chưa từng khai không được hưởng quyền của nguồn đã khai."""
    for la in ("", "khong_biet", "cache", "mau_san"):
        assert AQ.noi_dung_duoc_tu_gui("tin_khach", la)[0] is False, la


def test_moi_nhom_viec_deu_thuoc_dung_mot_ho():
    """Nhóm việc rơi ra ngoài cả hai họ sẽ đi vào nhánh mặc định mà không ai nhận ra."""
    assert set(AQ.TAC_VU_MO_HINH) | set(AQ.TAC_VU_MA_XAC_DINH) == set(AQ.COT)
    assert not (set(AQ.TAC_VU_MO_HINH) & set(AQ.TAC_VU_MA_XAC_DINH))


# ---------------------------------------------------------------------------------------------
# 2. Quyết định của Chủ tịch ngày 11/9/2026
# ---------------------------------------------------------------------------------------------

def test_khong_vai_tro_nao_con_mac_dinh_muc_3_o_tin_khach():
    """Chủ tịch hạ hai ô Marketing xuống mức 2 ngày 11/9. Mức 2 không có đường nào tự gửi ra ngoài.

    Phép thử canh cả bảng chứ không canh riêng hai vai trò: thêm một vai trò mới ở mức 3 cũng là
    mở lại đúng cái cửa vừa đóng, và mở bằng một dòng trông rất giống các dòng chung quanh.
    """
    i = AQ.COT.index("tin_khach")
    cao = {v: m[i] for v, m in AQ.MAC_DINH.items() if m[i] >= 3}
    assert not cao, f"vai trò đặt mức tự động ở tin_khach: {cao}"


def test_nguoi_hau_kiem_khong_duoc_la_chinh_nguoi_lam():
    """Ô hậu kiểm ghi đúng tên người làm thì nó chỉ là một chỗ trống đã điền.

    Bản cũ để nguoi_hau_kiem="ptgd_mkt" cho chính hạn mức của ptgd_mkt. Chủ tịch đổi sang chutich
    ngày 11/9 trong giai đoạn chạy demo.
    """
    hk = AQ.HAN_MUC_MAC_DINH["nguoi_hau_kiem"]
    assert hk == "chutich"
    assert hk != "ptgd_mkt", "người hậu kiểm phải ngồi ngoài nhóm việc mình kiểm"
    assert AQ.HAN_MUC_KIEM_SOAT["nguoi_hau_kiem"] != "bks", "vị trí Kiểm soát cũng không tự hậu kiểm"


def test_han_muc_van_khai_du_du_da_ha_xuong_muc_2():
    """Hạ mức không phải lý do để bỏ trống bản khai – đây là thứ người ta đọc khi cân nhắc nâng lại."""
    from app.models.core import AI_HAN_MUC_BAT_BUOC
    for k in AI_HAN_MUC_BAT_BUOC:
        assert str(AQ.HAN_MUC_MAC_DINH.get(k) or "").strip(), f"hạn mức thiếu {k}"


# ---------------------------------------------------------------------------------------------
# 3. Cửa phải được GỌI ở đúng chỗ, không chỉ tồn tại
# ---------------------------------------------------------------------------------------------

def _ma(src: str) -> str:
    src = re.sub(r'""".*?"""', " ", src, flags=re.S)
    src = re.sub(r"^\s*#.*$", " ", src, flags=re.M)
    return src


@pytest.mark.skipif(not INBOX.exists(), reason="chưa có kho mã")
def test_duong_tu_gui_goi_cua_thu_hai_truoc_khi_gui():
    """Ngày 09/9 đã có ca thật: mã đủ mọi thứ, chỉ sai chỗ đặt. Đây canh chỗ đặt.

    Đòi hai điều trong cùng một khối: có gọi noi_dung_duoc_tu_gui, và lời gọi _send phải nằm SAU
    lời gọi ấy. Một hàm canh cửa được định nghĩa xong rồi không ai gọi thì bằng không có cửa.
    """
    src = _ma(INBOX.read_text(encoding="utf-8"))
    dau = src.find("def robot_check")
    assert dau > 0
    khoi = src[dau:src.find("\ndef ", dau + 10)]
    assert "noi_dung_duoc_tu_gui" in khoi, "đường tự gửi không hỏi cửa thứ hai"
    assert khoi.index("noi_dung_duoc_tu_gui") < khoi.index("_send("), \
        "gửi trước rồi mới hỏi – thứ tự ấy làm cái cửa thành lời bình luận"


@pytest.mark.skipif(not INBOX.exists(), reason="chưa có kho mã")
def test_nhat_ky_ghi_lai_vai_tro_da_dung_quyen():
    """120/121 lượt chạy trên bản đang chạy để trống phuc_vu_vai_tro.

    Nhật ký nói được "AI đã gửi" mà không nói được "nhân danh quyền của ai". Câu thứ hai mới là
    câu người hậu kiểm và kiểm toán viên cần, và nó chỉ thiếu đúng một tham số khi gọi AL.ghi.
    """
    src = _ma(INBOX.read_text(encoding="utf-8"))
    dau = src.find("def draft_reply")
    khoi = src[dau:src.find("\ndef ", dau + 10)]
    assert "AL.ghi(" in khoi
    assert "vai_tro=" in khoi, "ghi nhật ký mà không ghi vai trò đã dùng quyền"
    assert "CHU_QUAN_HOP_THU" in khoi, "vai trò phải lấy từ hằng số, không gõ tay lại chuỗi"


@pytest.mark.skipif(not INBOX.exists(), reason="chưa có kho mã")
def test_khong_con_duong_nao_gui_thang_sau_khi_soan_tu_dong():
    """Chặn kiểu hỏng cũ quay lại: draft_reply(tu_dong=True) rồi _send ngay dòng kế tiếp."""
    src = _ma(INBOX.read_text(encoding="utf-8"))
    xau = re.search(r"draft_reply\([^)]*tu_dong=True[^)]*\)\s*\n\s*_send\(", src)
    assert xau is None, "soạn tự động xong gửi thẳng, không qua cửa nội dung"
