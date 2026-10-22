# -*- coding: utf-8 -*-
"""Đợt DỌN-10 (22/10/2026) — MỞ PR BẰNG TOKEN RIÊNG, VÀ BỎ HẲN ĐƯỜNG VƯỢT RÀO.

MỘT GỐC, BA LẦN CHỆCH

GitHub không sinh vòng CI cho việc gì do `GITHUB_TOKEN` làm — PR hay push đều vậy. Ba đợt
liên tiếp đều chệch quanh gốc ấy mà không chạm vào nó:

  · DỌN-7: đẩy thẳng vào main → GH006, rồi GH013.
  · DỌN-8: gọi `workflow_dispatch` → vòng CI XANH THẬT (lượt #1023) nhưng gắn vào NHÁNH, nên
    PR #426 vẫn đứng với "hang-rao-gop: Expected" và tab Checks chỉ thấy Vercel.
  · DỌN-9: `gh pr merge --admin` → "Required status check hang-rao-gop is expected
    (mergePullRequest)". Vì `--admin` KHÔNG phải quyền vượt rào; nó chỉ là một lời gọi gộp, và
    Rulesets vẫn chặn trừ khi NGƯỜI GỌI có quyền ấy.

Đợt này chạm vào gốc: PR mở bằng một token riêng của người, nên nó là PR của NGƯỜI, nên CI
chạy. Không vượt rào ở đâu cả.

NĂM LUẬT, đọc từ `dong-so.yml`, không gọi mạng:

 1. `GH_TOKEN` lấy từ `secrets.TOKEN_DONG_SO`, KHÔNG phải `github.token`.
 2. Commit của NHÁNH sổ KHÔNG mang `[skip ci]` — mang là vòng CI của PR bị bỏ qua, và ta quay
    lại đúng chỗ đứng của DỌN-8.
 3. Dòng `--subject` của lệnh gộp VẪN mang `[skip ci]` — bỏ là mỗi lần gộp kéo ~55 phút
    `backend` trên main cho một ô chữ.
 4. Lệnh gộp dùng `--auto` và KHÔNG dùng `--admin`.
 5. Hai phép thử sổ vẫn được gọi — nay là tín hiệu SỚM, không còn là thứ thay cho hàng rào.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DS = os.path.join(ROOT, ".github", "workflows", "dong-so.yml")


def _doc() -> str:
    assert os.path.isfile(DS), f"Thiếu {DS}"
    with open(DS, encoding="utf-8") as f:
        return f.read()


def _than_ghi_so() -> str:
    s = _doc()
    i = s.find("name: Ghi lại sổ")
    assert i > 0, "Không tìm thấy bước `Ghi lại sổ`."
    return s[i:]


def _lenh() -> str:
    """CHỈ các dòng LỆNH, bỏ hết dòng chú thích.

    Vì sao cần: khối chú thích của chính Đợt DỌN-10 có nhắc `--admin` và `--subject` để giải
    thích vì sao chúng đổi. Đếm thô trên cả tệp thì một lời giải thích bị tính là một lệnh —
    đã xảy ra thật khi chạy thử bản vá này lúc 08:40 ngày 22/10/2026, và đó đúng là kiểu phép
    thử đỏ vì đọc sai chứ không vì có lỗi.
    """
    return "\n".join(d for d in _than_ghi_so().splitlines() if not d.strip().startswith("#"))


def test_ds5_1_mo_PR_bang_token_rieng():
    s = _doc()
    assert "GH_TOKEN: ${{ secrets.TOKEN_DONG_SO }}" in s, (
        "Bước ghi sổ không dùng token riêng. Với `github.token`, GitHub KHÔNG sinh vòng CI cho "
        "PR robot mở ra — `hang-rao-gop` đứng ở trạng thái Expected và tự gộp chờ mãi.")
    assert "GH_TOKEN: ${{ github.token }}" not in s, (
        "Vẫn còn `GH_TOKEN: ${{ github.token }}`. Hai dòng cùng tồn tại thì dòng sau thắng, và "
        "không ai đọc YAML mà đoán ra được dòng nào đang chạy.")


def test_ds5_2_commit_nhanh_so_KHONG_mang_skip_ci():
    """Mang `[skip ci]` ở đây là vòng CI của PR bị bỏ qua — đúng chỗ đứng của DỌN-8."""
    dong = [d for d in _lenh().splitlines() if "git commit -m" in d]
    assert len(dong) == 1, f"Chờ đúng một dòng `git commit -m`, thấy {len(dong)}."
    assert "[skip ci]" not in dong[0], (
        "Commit của nhánh sổ lại mang `[skip ci]`. Vòng CI của PR sẽ bị bỏ qua, nên "
        "`hang-rao-gop` không bao giờ báo lên PR và `--auto` chờ mãi.\n"
        f"Dòng đang có: {dong[0].strip()}")


def test_ds5_3_commit_GOP_VAN_mang_skip_ci():
    """Bỏ ở đây là mỗi lần gộp kéo ~55 phút `backend` trên main cho một ô chữ."""
    dong = [d for d in _lenh().splitlines() if "--subject" in d]
    assert len(dong) == 1, f"Chờ đúng một dòng `--subject`, thấy {len(dong)}."
    assert "[skip ci]" in dong[0], (
        "Dòng `--subject` mất `[skip ci]`. Trên push lên main thì `loc` trả 0 vô điều kiện "
        "(quyết định 16/10), nên thiếu nó là ~55 phút máy cho MỖI lần gộp.")


def test_ds5_4_khong_con_duong_vuot_rao():
    than = _lenh()
    assert "--admin" not in than, (
        "Còn `--admin`. Nó KHÔNG phải quyền vượt rào — lần chạy #9 ngày 22/10/2026 trả về "
        "\"Required status check hang-rao-gop is expected (mergePullRequest)\". Để lại là để "
        "lại một đường chết, và tệ hơn: một đường chết TRÔNG NHƯ đang làm việc gì đó.")
    assert "--auto" in than, (
        "Thiếu `--auto`. Không có nó thì `gh pr merge` gộp ngay mà không chờ cửa hẹp xanh.")


def test_ds5_5_van_goi_hai_phep_thu_so():
    """Nối với `test_ds4`: nay là tín hiệu SỚM, không còn là thứ thay cho hàng rào."""
    than = _lenh()
    assert "tests/test_giu_cho_lan.py" in than and "tests/test_giu_cho_nhanh.py" in than, (
        "Mất lời gọi hai phép thử sổ. Hàng rào thật vẫn canh được, nhưng mất tín hiệu sớm: "
        "thay vì đỏ trong 15 giây ngay tại việc này, PR sẽ treo cho tới khi có người đọc.")
    i_thu = than.find("python -m pytest")
    i_gop = than.find("gh pr merge")
    assert 0 < i_thu < i_gop, "Phép thử phải chạy TRƯỚC lệnh gộp."
