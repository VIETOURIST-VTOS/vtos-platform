# -*- coding: utf-8 -*-
"""Đợt DỌN-9 (22/10/2026) — ROBOT TỰ GỘP PR ĐÓNG SỔ, VÀ CHỖ BỊ VƯỢT PHẢI ĐƯỢC CANH LẠI.

VÌ SAO CÓ TỆP NÀY

`gh pr merge --admin` đi vòng qua yêu cầu "phải có hang-rao-gop xanh" của `main`. Đó là một
quyết định có người chịu trách nhiệm (Chủ tịch, 22/10/2026), không phải một dòng lọt vào.
Nhưng vượt rào trần trụi thì commit đóng sổ KHÔNG còn phép thử nào soi cả — mà một thay đổi
chỉ-chạm-sổ vẫn hỏng được đúng hai kiểu:

  · hai làn cùng giữ một tệp          → `test_giu_cho_lan` bắt
  · ô bảng vỡ (dấu gạch đứng trong mô tả) → cũng `test_giu_cho_lan` bắt

Nên luật ở đây không phải "cấm --admin". Luật là: **ĐƯỢC vượt rào, với điều kiện chính hai
phép thử ấy đã chạy ngay trước đó và xanh.** Đổi một hàng rào lấy một hàng rào, không đổi
một hàng rào lấy sự tiện.

BỐN CHUYỆN TỆP NÀY CANH, đọc từ `dong-so.yml`, không gọi mạng:

 1. Có gọi hai phép thử sổ.
 2. Lời gọi ấy ĐỨNG TRƯỚC lệnh gộp — chạy sau thì vô nghĩa.
 3. Không ai nuốt mã lỗi của nó (`|| true`, `continue-on-error`, `set +e`). Đây đúng là cái
    tật đã làm hỏng Đợt DỌN-6: một việc không làm được gì mà vẫn báo Success.
 4. Chốt "một tệp đổi ngoài sổ thì dừng hẳn" vẫn còn — nay nó là thứ duy nhất giữ cho đường
    `--admin` này không bao giờ chạm tới mã.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DS = os.path.join(ROOT, ".github", "workflows", "dong-so.yml")
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")

GOI_THU = "python -m pytest -q tests/test_giu_cho_lan.py tests/test_giu_cho_nhanh.py"


def _doc(p: str) -> str:
    assert os.path.isfile(p), f"Thiếu {p}"
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_ds4_1_co_chay_hai_phep_thu_so_truoc_khi_gop():
    s = _doc(DS)
    assert GOI_THU in s, (
        "Không thấy lời gọi hai phép thử sổ trong dong-so.yml. Thiếu nó thì `--admin` là vượt "
        "rào trần trụi: commit đóng sổ vào main mà không có phép thử nào soi.\n"
        f"Chờ nguyên văn: {GOI_THU}")


def test_ds4_2_phep_thu_phai_chay_TRUOC_lenh_gop():
    """Chạy sau khi gộp thì nó chỉ báo, không chặn — đúng cái tật của Đợt DỌN-7."""
    s = _doc(DS)
    i_thu = s.find(GOI_THU)
    i_gop = s.find("gh pr merge")
    assert i_thu > 0 and i_gop > 0, "Thiếu một trong hai: lời gọi phép thử, hoặc lệnh gộp."
    assert i_thu < i_gop, (
        "Hai phép thử sổ đang chạy SAU lệnh gộp. Như thế chúng chỉ BÁO chứ không CHẶN — mã đã "
        "vào main rồi. Phải đặt trước `gh pr merge`.")


def test_ds4_3_khong_ai_nuot_ma_loi_cua_phep_thu():
    """Đúng cái tật đã làm hỏng Đợt DỌN-6: việc không làm được gì mà vẫn báo Success."""
    s = _doc(DS)
    i = s.find("name: Ghi lại sổ")
    than = s[i:]
    xau = [d.strip() for d in than.splitlines()
           if "pytest" in d and re.search(r"\|\|\s*(true|:|echo)", d)]
    assert not xau, f"Mã lỗi của phép thử đang bị nuốt: {xau}"
    assert "continue-on-error" not in than, (
        "`continue-on-error` trong bước ghi sổ nuốt mọi thất bại, kể cả phép thử sổ đỏ.")
    assert not re.search(r"^\s*set \+e\s*$", than, re.M), "`set +e` tắt việc dừng khi lỗi."


def test_ds4_4_van_giu_chot_khong_cham_tep_ngoai_so():
    """Nay quan trọng hơn hẳn: đây là thứ DUY NHẤT giữ cho --admin không chạm tới mã."""
    s = _doc(DS)
    i = s.find("name: Ghi lại sổ")
    assert "grep -v '^docs/dang-lam/'" in s[i:] and "exit 1" in s[i:], (
        "Mất chốt “một tệp đổi ngoài sổ thì dừng hẳn”. Với --admin trong tay, mất chốt này "
        "nghĩa là một lỗi của dong_so.py có thể đẩy MÃ vào main mà không qua hàng rào nào.")


def test_ds4_5_ci_yml_khong_co_dau_huyen_trong_echo_cua_loc():
    """Lượt #1023 in ra `hang-rao-gop: command not found` — dấu huyền trong ngoặc kép.

    Vô hại (echo vẫn trả 0) nhưng nó làm log nói dối: tên việc biến mất khỏi câu thông báo, và
    một dòng `command not found` giữa log xanh là thứ khiến người đọc ngờ sai chỗ.
    """
    s = _doc(CI)
    i = s.find("\n  loc:\n")
    j = s.find("\n  backend:\n")
    than = s[i:j]
    xau = [d.strip() for d in than.splitlines() if d.strip().startswith("echo") and "`" in d]
    assert not xau, f"Còn dấu huyền trong lệnh echo của việc `loc` (shell hiểu là lệnh): {xau}"
