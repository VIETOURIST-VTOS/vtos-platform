# -*- coding: utf-8 -*-
"""KS-13 — bộ đồng bộ cây làm việc: kéo bản cũ về, và KHÔNG ĐỤNG việc đang làm.

Phép thử nặng nhất là `ks13_3`: nó dựng một tệp vừa KHÁC bản main vừa ĐANG đứng tên trong một
dòng `đang làm`, rồi đòi bộ đồng bộ để nguyên. Một bộ đồng bộ không đọc sổ giữ chỗ sẽ xoá sạch
việc người khác đang viết dở — và xoá đúng lúc nửa đêm, khi người ấy không ngồi trước máy.

`ks13_4` canh chiều ngược lại: tệp có trên đĩa mà main không có thì phải để nguyên. Đó thường là
tệp một làn vừa tạo mà chưa đẩy; một bộ đồng bộ "cho giống main" sẽ coi nó là rác.

Dựng kho git THẬT chứ không chắp vá bằng đồ giả: thứ đang thử là một kịch bản gọi `git ls-tree`
và `git show` thật, nên thay git bằng đồ giả là thử một thứ khác.
"""
import os
import subprocess
import sys
import tempfile

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, "scripts"))


def _git(cwd, *ds):
    r = subprocess.run(["git", *ds], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(ds)}: {r.stderr}"
    return r.stdout


def _ghi(goc, duong, noi_dung):
    that = os.path.join(goc, duong)
    os.makedirs(os.path.dirname(that), exist_ok=True)
    with open(that, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung)


SO = """# Sổ giữ chỗ — làn Vòng

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Vòng | VD-1 — việc đang viết dở | app/dang_viet.py | 21-10-2026 10:00 | đang làm |
| Vòng | VD-0 — việc đã xong | app/da_xong.py | 20-10-2026 10:00 | xong |
"""


@pytest.fixture()
def kho():
    """Kho giả: main có 4 tệp; trên đĩa thì một tệp mất, một cũ, một đang giữ, một thừa."""
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _git(d, "init", "-q", "-b", "main")
        _git(d, "config", "user.email", "ks@vtos.test")
        _git(d, "config", "user.name", "KS")
        _ghi(d, "app/moi.py", "# tệp MỚI của làn khác\nx = 1\n")
        _ghi(d, "app/cu.py", "# bản MAIN\ny = 2\n")
        _ghi(d, "app/dang_viet.py", "# bản MAIN\nz = 3\n")
        _ghi(d, "docs/dang-lam/vong.md", SO)
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "nen")
        sha = _git(d, "rev-parse", "HEAD").strip()
        _git(d, "update-ref", "refs/remotes/origin/main", sha)

        os.remove(os.path.join(d, "app/moi.py"))                       # THIẾU
        _ghi(d, "app/cu.py", "# bản CŨ trên đĩa\n")                    # CŨ, không ai giữ
        _ghi(d, "app/dang_viet.py", "# ĐANG VIẾT DỞ, đừng đụng\n")     # CŨ nhưng ĐANG GIỮ
        _ghi(d, "app/chua_day.py", "# tệp làn khác vừa tạo, chưa đẩy\n")  # THỪA
        yield d


def _chay(kho, chi_xem=False):
    import importlib
    m = importlib.import_module("dong_bo_cay")
    cwd = os.getcwd()
    os.chdir(kho)
    try:
        return m.dong_bo(kho, chi_xem=chi_xem)
    finally:
        os.chdir(cwd)


def _doc(kho, duong):
    with open(os.path.join(kho, duong), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------------------------
def test_ks13_1_tep_thieu_han_phai_duoc_keo_ve(kho):
    """Đây là lỗ gốc: `VONG_DAY.bat` không checkout, nên tệp MỚI của làn khác không bao giờ
    xuống cây chung. Đo được 24 tệp như thế ngày 21/10/2026."""
    kq = _chay(kho)
    assert "app/moi.py" in kq["thieu"], kq
    assert os.path.exists(os.path.join(kho, "app/moi.py")), "Tệp thiếu không được kéo về."
    assert "tệp MỚI" in _doc(kho, "app/moi.py")


def test_ks13_2_ban_cu_khong_ai_giu_thi_keo_ve_VA_cat_ban_cu_lai(kho):
    kq = _chay(kho)
    assert "app/cu.py" in kq["cu"], kq
    assert _doc(kho, "app/cu.py") == "# bản MAIN\ny = 2\n", "Bản cũ chưa được kéo về bản main."
    luu = os.path.join(kq["kho_cat"], "app/cu.py")
    assert os.path.exists(luu), (
        "Không cất bản cũ trước khi ghi đè. Một bộ đồng bộ không giữ lại bản cũ là một bộ không "
        "ai dám bấm lần thứ hai.")
    assert "bản CŨ trên đĩa" in open(luu, encoding="utf-8").read()


def test_ks13_3_TEP_DANG_CO_LAN_GIU_THI_KHONG_DUOC_DUNG(kho):
    """Phép thử trung tâm. Bỏ phần đọc sổ giữ chỗ thì đỏ ở đây."""
    kq = _chay(kho)
    assert "app/dang_viet.py" in kq["dang_giu"], kq
    assert "app/dang_viet.py" not in kq["cu"], (
        "Tệp đang có làn giữ bị xếp vào nhóm 'bản cũ' — nó sẽ bị ghi đè.")
    assert _doc(kho, "app/dang_viet.py") == "# ĐANG VIẾT DỞ, đừng đụng\n", (
        "VIỆC ĐANG LÀM CỦA LÀN KHÁC BỊ GHI ĐÈ. Sổ giữ chỗ là lời khai duy nhất về ai đang làm "
        "gì; bộ đồng bộ không đọc sổ sẽ xoá việc viết dở của người khác lúc không ai nhìn.")


def test_ks13_4_tep_tren_dia_ma_main_khong_co_thi_de_nguyen(kho):
    """Thường là tệp một làn vừa tạo mà chưa đẩy. 'Cho giống main' sẽ coi nó là rác."""
    _chay(kho)
    assert os.path.exists(os.path.join(kho, "app/chua_day.py")), (
        "Tệp chưa đẩy bị xoá. Bộ này CHỈ KÉO VỀ, không xoá gì.")
    assert "chưa đẩy" in _doc(kho, "app/chua_day.py")


def test_ks13_5_ban_xem_truoc_khong_ghi_gi(kho):
    kq = _chay(kho, chi_xem=True)
    assert kq["chi_xem"] is True
    assert set(kq["thieu"]) == {"app/moi.py"} and set(kq["cu"]) == {"app/cu.py"}
    assert not os.path.exists(os.path.join(kho, "app/moi.py")), "Bản xem trước đã GHI."
    assert _doc(kho, "app/cu.py") == "# bản CŨ trên đĩa\n", "Bản xem trước đã GHI."


def test_ks13_6_chay_lai_lan_hai_thi_khong_con_gi_de_lam(kho):
    """Một bộ đồng bộ mà lần hai vẫn báo 'có việc' là một bộ không ai tin được nữa."""
    _chay(kho)
    lai = _chay(kho)
    assert lai["thieu"] == [] and lai["cu"] == [], f"Lần hai vẫn còn việc: {lai}"
    assert lai["dang_giu"] == ["app/dang_viet.py"], "Tệp đang giữ phải vẫn khác main — và vẫn còn."


def test_ks13_7_doc_so_dung_nhu_hang_rao_giu_cho(kho):
    """Hai nơi hiểu sổ khác nhau thì sớm muộn cũng lệch, và lệch ở đây nghĩa là ghi đè nhầm.

    Dòng `xong` KHÔNG giữ chỗ — đúng như `test_giu_cho_lan` nói — nên tệp của nó phải được coi
    là bản cũ bình thường.
    """
    import importlib
    m = importlib.import_module("dong_bo_cay")
    giu = m.tep_dang_giu(kho)
    assert "app/dang_viet.py" in giu, giu
    assert "app/da_xong.py" not in giu, (
        "Dòng `xong` vẫn được coi là đang giữ chỗ — `xong` không giữ chỗ nữa.")
    assert giu["app/dang_viet.py"].startswith("Vòng · "), giu


def test_ks13_8_kich_ban_co_that_va_chay_duoc_tu_dong_lenh(kho):
    """Chạy THẬT qua dòng lệnh, trong một kho git thật — vì tệp .bat gọi nó đúng kiểu ấy.

    Chạy trong kho GIẢ chứ không trong kho thật là có chủ ý: bản xuất sạch dùng để đo không có
    thư mục `.git`, và một phép thử chỉ xanh khi đứng trong kho thật là phép thử không đo được ở
    chỗ cần đo nhất.

    Không đòi bit thực thi: kho nằm trên thư mục Windows gắn vào, bit ấy không giữ được, và vòng
    VG-1b đã viết đúng một dòng `assert os.access(..., X_OK)` rồi nó không bao giờ xanh nổi."""
    duong = os.path.join(GOC, "scripts", "dong_bo_cay.py")
    assert os.path.isfile(duong), f"Không thấy {duong}"
    moi_truong = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, duong, "--xem"], cwd=kho,
                       capture_output=True, text=True, env=moi_truong)
    assert r.returncode == 0, f"Chạy --xem mà lỗi:\n{r.stdout}\n{r.stderr}"
    assert "ĐỒNG BỘ CÂY LÀM VIỆC" in r.stdout, r.stdout
    assert "app/moi.py" in r.stdout, "Bản kê không nói ra tệp đang thiếu."


def test_ks13_9_chay_ngoai_kho_git_thi_noi_tu_te_chu_khong_do_traceback():
    """Tệp này được gọi từ một tệp .bat; traceback trong cửa sổ đen thì không ai đọc."""
    duong = os.path.join(GOC, "scripts", "dong_bo_cay.py")
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as ngoai:
        r = subprocess.run([sys.executable, duong, "--xem"], cwd=ngoai,
                           capture_output=True, text=True,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert "Traceback" not in (r.stdout + r.stderr), (
        f"Đổ traceback khi chạy ngoài kho git:\n{r.stdout}\n{r.stderr}")
    assert "KHÔNG PHẢI KHO GIT" in r.stdout, r.stdout
