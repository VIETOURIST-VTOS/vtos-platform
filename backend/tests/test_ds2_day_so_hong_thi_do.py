# -*- coding: utf-8 -*-
"""ĐẨY SỔ HỎNG THÌ PHẢI ĐỎ — Đợt DỌN-7, 21/10/2026.

VÌ SAO CÓ TỆP NÀY. Lần chạy đầu tiên của `Đóng sổ khi gộp` (21/10/2026, sau khi PR #405 gộp) làm
ĐÚNG mọi thứ:

    nhanh: pq-don6-dong-so-khi-gop-21-10
      đóng DỌN-6  (phan-quyen.md:95)
    ĐÓNG 1 DÒNG
    [main 541d21d] Đóng sổ: ... đã gộp [skip ci]

rồi đẩy lên và bị từ chối:

    remote: error: GH006: Protected branch update failed for refs/heads/main.
    remote: - Required status check "hang-rao-gop" is expected.

Sổ KHÔNG đổi một chữ. Nhưng việc CI báo **Success**, vì dòng cuối của bước đẩy là

    git push || { git pull --rebase origin main && git push; } || echo "day khong duoc — ..."

tức là nuốt mã lỗi. Một việc không làm được gì mà vẫn xanh thì tệ hơn một việc đỏ: nó dạy người
đọc rằng sổ đã được đóng, trong khi sổ vẫn nguyên.

ĐIỀU TỆP NÀY CANH: bước đẩy không được kết thúc bằng một lệnh nuốt lỗi, và phải nói ra khi bị rào
bảo vệ chặn. Nó KHÔNG canh việc đẩy có thành công hay không — chuyện ấy phụ thuộc cài đặt kho,
nằm ngoài kho mã.

BA ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM
  1. Không đọc cài đặt bảo vệ nhánh: phép thử không gọi mạng.
  2. Không cấm `git pull --rebase` rồi thử lại — thử lại một lần là đúng, nuốt lỗi mới là sai.
  3. Không đòi `[skip ci]` bị bỏ đi. Ngược lại: `[skip ci]` PHẢI còn, vì từ 16/10 `backend` chạy
     cả trên push, nên một commit ghi sổ không mang `[skip ci]` sẽ kéo theo ~55 phút máy MỖI LẦN
     GỘP. Phép thử số 4 ghim đúng điều ấy.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEP = os.path.join(ROOT, ".github", "workflows", "dong-so.yml")


@pytest.fixture(scope="module")
def noi_dung() -> str:
    assert os.path.isfile(TEP), f"Thiếu {TEP} — Đợt DỌN-6 là nơi tạo ra nó."
    with open(TEP, encoding="utf-8") as f:
        return f.read()


def _buoc_ghi_so(s: str) -> str:
    """Cắt riêng phần thân của bước `Ghi lại sổ`."""
    i = s.find("name: Ghi lại sổ")
    assert i > 0, "Không tìm thấy bước `Ghi lại sổ` trong dong-so.yml."
    return s[i:]


def test_ds2_1_khong_nuot_loi_khi_day(noi_dung):
    """LUẬT CHÍNH. Không được có `|| echo` hay `|| true` đứng sau một lệnh `git push`.

    Đây đúng là dòng đã làm việc CI xanh trong khi sổ không đổi, ngày 21/10/2026.
    """
    than = _buoc_ghi_so(noi_dung)
    xau = [
        d.strip()
        for d in than.splitlines()
        if "push" in d and re.search(r"\|\|\s*(echo|true|:)\b", d)
    ]
    assert not xau, (
        "Bước `Ghi lại sổ` đang NUỐT lỗi của `git push`:\n  "
        + "\n  ".join(xau)
        + "\n\nĐẩy hỏng mà việc CI vẫn xanh thì người đọc tin là sổ đã đóng, trong khi sổ còn "
          "nguyên. Đúng chuyện đã xảy ra sau khi PR #405 gộp. Để nó ĐỎ."
    )


def test_ds2_2_khong_nuot_loi_bang_dau_tru_hay_set_cong(noi_dung):
    """Nuốt lỗi còn hai hình nữa: `set +e` và dấu `-` đầu lệnh của YAML."""
    than = _buoc_ghi_so(noi_dung)
    assert "set +e" not in than, "`set +e` trong bước ghi sổ là mở đường cho lỗi đi lọt."
    assert "continue-on-error" not in than, (
        "`continue-on-error` ở bước ghi sổ biến một lần đẩy hỏng thành một việc xanh."
    )


def test_ds2_3_noi_ro_khi_bi_rao_bao_ve_chan(noi_dung):
    """Đỏ thôi chưa đủ — phải nói ĐÚNG phải làm gì.

    Lỗi GH006 không phải lỗi mã: nó có nghĩa là `main` đang chặn đẩy thẳng và chủ kho phải cho
    `github-actions[bot]` vào danh sách vượt rào. Người đọc nhật ký lúc 2 giờ sáng cần đọc ra
    điều ấy mà không phải đi tra.
    """
    than = _buoc_ghi_so(noi_dung)
    assert "GH006" in than, (
        "Bước ghi sổ không hề nhắc GH006. Khi `main` chặn, nhật ký phải nói rõ là bị rào bảo vệ "
        "chặn, không phải lỗi mã."
    )
    assert "bypass" in than or "vuot rao" in than or "vượt rào" in than, (
        "Thông điệp lỗi phải nói ra cách sửa: cho github-actions[bot] vào danh sách vượt rào của "
        "nhánh main."
    )


def test_ds2_4_van_giu_skip_ci_tren_commit_ghi_so(noi_dung):
    """`[skip ci]` PHẢI còn — bỏ nó đi là tự tốn ~55 phút máy mỗi lần gộp.

    Từ 16/10/2026 việc `backend` chạy cả trên push lên main. Một commit ghi sổ không mang
    `[skip ci]` sẽ kéo nguyên bộ đủ chạy lại chỉ vì một ô chữ đổi.
    """
    assert "[skip ci]" in _buoc_ghi_so(noi_dung), (
        "Commit ghi sổ mất `[skip ci]`. Mỗi lần gộp sẽ kéo thêm một vòng `backend` ~55 phút cho "
        "một thay đổi đúng một ô chữ."
    )


def test_ds2_5_van_dung_han_khi_co_tep_doi_ngoai_so(noi_dung):
    """CHỐT 1 của DỌN-6 không được rụng khi sửa bước này."""
    than = _buoc_ghi_so(noi_dung)
    assert "docs/dang-lam/" in than and "exit 1" in than, (
        "Mất chốt “một tệp đổi ngoài sổ thì dừng hẳn”. Đó là thứ giữ cho việc này không bao giờ "
        "chạm được vào mã."
    )
