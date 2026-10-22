# -*- coding: utf-8 -*-
"""Đợt DỌN-8 (22/10/2026) — ĐÓNG SỔ ĐI QUA PR, và cái lỗ duy nhất được nới trong `ci.yml`.

VÌ SAO CÓ TỆP NÀY

Hai lần chạy đầu của `Đóng sổ khi gộp` đều làm ĐÚNG — đọc tên nhánh, khớp mã, đóng đúng một dòng,
commit đúng một ô — rồi bị `main` từ chối đẩy: GH006 lần đầu, **GH013 (Ruleset)** lần sau. Đường
cho `github-actions[bot]` vượt rào đã THỬ và KHÔNG CÓ: Rulesets không liệt kê bot ấy.

Nên robot nay **mở PR** thay vì đẩy thẳng. Việc ấy kéo theo một cái giá và một cái lỗ, và tệp này
canh đúng hai thứ đó:

  · GIÁ: PR đóng sổ sẽ kéo `backend` ~55 phút cho một ô chữ.
  · LỖ : `backend` được bỏ qua khi diff chỉ chạm `docs/dang-lam/`.

ĐIỀU TỆP NÀY CANH — bốn chuyện, tất cả đọc từ hai tệp YAML, không gọi mạng:

 1. Việc `loc` còn đó, và trên `push` nó TRẢ 0 VÔ ĐIỀU KIỆN. Mất dòng ấy là quyết định 16/10
    (bộ đủ chạy cả trên main) bị tắt lặng lẽ.
 2. Mọi chỗ còn ngờ đều trượt về phía CHẠY ĐỦ, không về phía bỏ qua.
 3. `dong-so.yml` KHÔNG còn đẩy thẳng vào `main`.
 4. Nó có gọi `workflow_dispatch` — thiếu dòng ấy thì PR của robot không bao giờ có vòng CI, và
    tự gộp chờ mãi mà không ai biết vì sao.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CI = os.path.join(ROOT, ".github", "workflows", "ci.yml")
DS = os.path.join(ROOT, ".github", "workflows", "dong-so.yml")


def _doc(p: str) -> str:
    assert os.path.isfile(p), f"Thiếu {p}"
    with open(p, encoding="utf-8") as f:
        return f.read()


def _viec_loc() -> str:
    s = _doc(CI)
    i = s.find("\n  loc:\n")
    assert i > 0, "Không tìm thấy việc `loc` trong ci.yml — Đợt DỌN-8 là nơi tạo ra nó."
    j = re.search(r"\n  [a-z][a-z0-9-]*:\n", s[i + 8:])
    return s[i:i + 8 + (j.start() if j else len(s))]


def test_ds3_1_tren_push_KHONG_BAO_GIO_bo_qua():
    """LUẬT CHÍNH. Mất dòng này là tắt lặng lẽ quyết định 16/10.

    Quyết định ấy: bộ đủ phải chạy cả trên main, vì hai PR cùng xanh riêng lẻ gộp lần lượt thì
    cái thứ hai có thể làm đỏ — và không chạy trên main thì KHÔNG AI THẤY. Đã xảy ra thật
    ngày 16/10/2026 với PR #370 và #367.
    """
    than = _viec_loc()
    assert 'github.event_name }}" = "push"' in than, (
        "Việc `loc` không còn chặn riêng trường hợp `push`. Thiếu nó thì một lần gộp chỉ-chạm-sổ "
        "trên main cũng bỏ qua bộ đủ — tức quyết định 16/10 bị tắt mà không ai quyết.")
    i = than.find('= "push"')
    assert "chi_so=0" in than[i:i + 220], (
        "Nhánh `push` phải trả `chi_so=0` (chạy đủ bộ). Trả 1 ở đó là bỏ qua bộ đủ trên main.")


def test_ds3_2_moi_cho_con_ngo_deu_truot_ve_phia_CHAY_DU():
    """Bỏ qua nhầm thì mất một lớp canh mà không ai biết; chạy thừa thì chỉ tốn máy."""
    than = _viec_loc()
    assert than.count("chi_so=0") >= 3, (
        "Phải còn đủ các nhánh trả 0: chạy trên push, không đọc được danh sách tệp, và có tệp "
        f"ngoài sổ. Đang thấy {than.count('chi_so=0')} chỗ.")
    assert than.count("chi_so=1") == 1, (
        "Chỉ được MỘT chỗ trả 1, và đúng chỗ 'không có tệp nào ngoài docs/dang-lam/'.")


def test_ds3_3_chi_bo_qua_khi_khong_co_tep_nao_ngoai_so():
    than = _viec_loc()
    assert "grep -v '^docs/dang-lam/'" in than, (
        "Phép đo phải hỏi 'có tệp nào NGOÀI docs/dang-lam/ không', không phải 'có tệp nào TRONG "
        "đó không'. Hai câu khác nhau: một PR vừa sửa sổ vừa sửa mã thì câu sau trả lời sai.")


def test_ds3_4_backend_nhan_dung_mot_dieu_kien():
    s = _doc(CI)
    assert "    if: needs.loc.outputs.chi_so != '1'\n" in s, (
        "Việc `backend` phải nhận đúng điều kiện này. `test_ci4` ghim cùng một chuỗi — hai nơi "
        "lệch nhau thì một trong hai đang nói dối.")


def test_ds3_5_dong_so_KHONG_con_day_thang_vao_main():
    """Đẩy thẳng đã thử hai lần và bị chặn hai lần. Để lại dòng ấy là để lại một đường chết."""
    s = _doc(DS)
    i = s.find("name: Ghi lại sổ")
    than = s[i:]
    xau = [d.strip() for d in than.splitlines()
           if re.search(r"^\s*git push\s*$", d) or re.search(r"git push origin main", d)]
    assert not xau, f"Bước ghi sổ còn đẩy thẳng: {xau}"
    assert "git push origin \"$nh\"" in than, "Phải đẩy lên NHÁNH riêng rồi mở PR."


def test_ds3_6_KHONG_con_trong_cho_workflow_dispatch():
    """ĐỔI Ở ĐỢT DỌN-9 22/10/2026 — và chỗ đổi này đáng đọc kỹ.

    Luật cũ ở đây BẮT BUỘC phải có `gh workflow run ci.yml`, với lý do: PR do GITHUB_TOKEN mở
    ra thì GitHub không sinh vòng CI, nên phải gọi tay một lượt. Lý do ấy đúng. Cách gỡ thì SAI.

    Đo được, lượt #1023 ngày 22/10/2026 trên nhánh `so/dong-bbece3d`: vòng ấy CHẠY và XANH —
    loc 5s, backend bỏ qua, hang-rao-gop xanh 1m11s, tổng 1m21s. Mà PR #426 vẫn đứng với
    "hang-rao-gop: Expected — Waiting for status to be reported", và tab Checks của PR chỉ thấy
    Vercel. Vì lượt `workflow_dispatch` gắn vào NHÁNH, không gắn vào PR.

    Nên luật này nay lật ngược: KHÔNG được dựa vào workflow_dispatch nữa. Chỗ canh thật nằm ở
    `test_ds4`, nơi bắt robot tự chạy hai phép thử sổ trước khi gộp.
    """
    than = _doc(DS)
    assert "gh workflow run ci.yml" not in than, (
        "Còn `gh workflow run ci.yml` trong dong-so.yml. Nó tạo một vòng CI xanh KHÔNG gắn vào "
        "PR — tức một màu xanh không ai dùng được, và tệ hơn: nó làm người đọc tưởng PR đã được "
        "kiểm. Chỗ kiểm thật là hai phép thử sổ chạy ngay trong việc đóng sổ (test_ds4).")


def test_ds3_7_van_giu_chot_khong_cham_tep_ngoai_so():
    than = _doc(DS)
    i = than.find("name: Ghi lại sổ")
    assert "grep -v '^docs/dang-lam/'" in than[i:] and "exit 1" in than[i:], (
        "Mất chốt “một tệp đổi ngoài sổ thì dừng hẳn”. Đó là thứ giữ cho việc này không bao giờ "
        "chạm được vào mã, và nay càng quan trọng vì nó đang mở PR chứ không chỉ đẩy.")


def test_ds3_8_van_giu_skip_ci_tren_commit_dong_so():
    than = _doc(DS)
    assert "[skip ci]" in than[than.find("name: Ghi lại sổ"):], (
        "Commit đóng sổ mất `[skip ci]`. Lần gộp của chính PR đóng sổ sẽ kéo thêm một vòng nữa.")


def test_ds3_9_khai_du_quyen_mo_PR():
    s = _doc(DS)
    assert "pull-requests: write" in s, (
        "Thiếu quyền `pull-requests: write` thì `gh pr create` hỏng — và hỏng ở bước cuối, sau "
        "khi đã commit, là chỗ khó đọc nhất.")
