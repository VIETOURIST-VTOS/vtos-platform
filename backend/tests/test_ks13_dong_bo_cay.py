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
        # HAI LẦN SỬA, cố ý (Đợt KS-19). `app/cu.py` phải THẬT SỰ là nội dung của một commit cũ
        # thì mới chứng minh được nó là bản cũ. Bản đầu của chỗ dựng này chỉ ghi một chuỗi bất kỳ
        # lên đĩa rồi gọi nó là "bản cũ" — và vì thế nó cũng nghiệm đúng cho một tệp ĐANG VIẾT DỞ.
        _ghi(d, "app/moi.py", "# tệp MỚI của làn khác\nx = 1\n")
        _ghi(d, "app/cu.py", "# bản CŨ trên đĩa\n")
        _ghi(d, "app/dang_viet.py", "# bản CŨ trên đĩa\n")
        _ghi(d, "docs/dang-lam/vong.md", SO)
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "ban cu")
        _ghi(d, "app/cu.py", "# bản MAIN\ny = 2\n")
        _ghi(d, "app/dang_viet.py", "# bản MAIN\nz = 3\n")
        _ghi(d, "app/dang_sua.py", "# bản MAIN\nw = 4\n")
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "nen")
        sha = _git(d, "rev-parse", "HEAD").strip()
        _git(d, "update-ref", "refs/remotes/origin/main", sha)

        os.remove(os.path.join(d, "app/moi.py"))                       # THIẾU
        _ghi(d, "app/cu.py", "# bản CŨ trên đĩa\n")                    # CŨ, không ai giữ
        _ghi(d, "app/dang_viet.py", "# ĐANG VIẾT DỞ, đừng đụng\n")     # CŨ nhưng ĐANG GIỮ
        _ghi(d, "app/chua_day.py", "# tệp làn khác vừa tạo, chưa đẩy\n")  # THỪA
        _ghi(d, "app/dang_sua.py", "# KHÁC main mà KHÔNG phải bản cũ nào\n")  # CHƯA RÕ
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


# ═════════════════════════════════════════════════════════════════════════════════════════════
# KS-14 · 21/10/2026 — MỘT QUYỂN SỔ CŨ BẢO VỆ ĐÚNG NHỮNG TỆP CŨ
#
# Lỗ của chính vòng KS-13, đo được ngay hôm sau khi dựng nó. `docs/dang-lam/vong.md` trên cây
# chung là bản cũ nguyên si của commit ngày 17/10; trong bản ấy dòng HD-Q2a còn `đang làm` nên
# nó GIỮ ba tệp cũng là bản cũ — `models/danh_gia.py`, `api/v1/danh_gia.py`, `api/v1/cskh.py`.
# Trên main dòng ấy đã `xong` từ lâu (vòng HD-Q2a gộp trong commit c16f5d9).
#
# Bộ đồng bộ đứng nhìn, vì nó tin quyển sổ trên đĩa. Và sổ cũ còn dựng ra một VA CHẠM GIẢ: sổ cũ
# của làn Vòng cùng sổ thật của làn Phân quyền cùng khai `ks_cua_nhap.py`, nên `test_giu_cho_lan`
# đỏ trên cây trong khi trên main thì không — hai làn đi tìm một cuộc va chạm không tồn tại.
#
# Cách chữa: KÉO SỔ VỀ TRƯỚC, và chỉ kéo quyển CHỨNG MINH ĐƯỢC là bản cũ (trùng khít một bản
# trong lịch sử của chính nó — cùng câu hỏi VG-1 hỏi). Quyển nào đã có dòng mới thì không trùng
# bản nào, nên không bao giờ bị đụng.
# ═════════════════════════════════════════════════════════════════════════════════════════════

SO_CU = """# Sổ giữ chỗ — làn Vòng

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Vòng | VD-9 — việc đã gộp từ lâu | app/da_gop.py | 15-10-2026 10:00 | đang làm |
"""
SO_MOI = SO_CU.replace("| đang làm |", "| xong |")


@pytest.fixture()
def kho_so_cu():
    """Sổ trên đĩa là BẢN CŨ NGUYÊN SI, và dòng `đang làm` của nó giữ một tệp cũng cũ."""
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _git(d, "init", "-q", "-b", "main")
        _git(d, "config", "user.email", "ks@vtos.test")
        _git(d, "config", "user.name", "KS")
        _ghi(d, "docs/dang-lam/vong.md", SO_CU)
        _ghi(d, "app/da_gop.py", "# bản CŨ\n")
        _git(d, "add", "-A"); _git(d, "commit", "-qm", "cu")

        _ghi(d, "docs/dang-lam/vong.md", SO_MOI)        # việc đã xong
        _ghi(d, "app/da_gop.py", "# bản MAIN\nmoi = True\n")
        _git(d, "add", "-A"); _git(d, "commit", "-qm", "moi")
        _git(d, "update-ref", "refs/remotes/origin/main", _git(d, "rev-parse", "HEAD").strip())

        _ghi(d, "docs/dang-lam/vong.md", SO_CU)         # đĩa quay về bản cũ nguyên si
        _ghi(d, "app/da_gop.py", "# bản CŨ\n")
        yield d


def test_ks13_10_so_CU_phai_duoc_keo_ve_TRUOC_roi_moi_xet_ai_giu_gi(kho_so_cu):
    """Phép thử trung tâm của KS-14."""
    kq = _chay(kho_so_cu)
    assert "docs/dang-lam/vong.md" in kq.get("so_da_keo", []), (
        "Sổ cũ không được kéo về. Một quyển sổ cũ sẽ bảo vệ đúng những tệp cũ, và bộ đồng bộ "
        f"đứng nhìn.\n{kq}")
    assert _doc(kho_so_cu, "docs/dang-lam/vong.md") == SO_MOI, "Sổ chưa về đúng bản main."
    assert "app/da_gop.py" in kq["cu"], (
        f"Tệp cũ vẫn bị coi là 'đang giữ' vì đọc dòng của quyển sổ cũ.\n{kq}")
    assert _doc(kho_so_cu, "app/da_gop.py") == "# bản MAIN\nmoi = True\n"


def test_ks13_11_so_da_co_DONG_MOI_thi_khong_dung_va_dong_ay_van_giu_cho(kho_so_cu):
    """Sổ có dòng một làn vừa khai mà chưa đẩy thì không trùng bản cũ nào — phải giữ nguyên.

    Thiếu luật này thì bộ đồng bộ xoá đúng dòng giữ chỗ người ta vừa viết, rồi ghi đè luôn tệp
    mà dòng ấy đang bảo vệ — hai cái sai cộng lại trong một lượt chạy.
    """
    so_them = SO_CU + "| Vòng | VD-10 — việc VỪA khai, chưa đẩy | app/da_gop.py | 21-10-2026 09:00 | đang làm |\n"
    _ghi(kho_so_cu, "docs/dang-lam/vong.md", so_them)
    kq = _chay(kho_so_cu)
    assert kq.get("so_da_keo", []) == [], (
        f"Sổ đã có dòng mới mà vẫn bị kéo về — dòng vừa khai bị xoá.\n{kq}")
    assert _doc(kho_so_cu, "docs/dang-lam/vong.md") == so_them, "Sổ bị đụng."
    assert "app/da_gop.py" in kq["dang_giu"], "Dòng vừa khai không còn giữ được chỗ."
    assert _doc(kho_so_cu, "app/da_gop.py") == "# bản CŨ\n", "Tệp đang được giữ bị ghi đè."


def test_ks13_12_dong_giu_cho_chi_co_TREN_MAIN_cung_phai_duoc_ton_trong(kho_so_cu):
    """Giữ chỗ đọc theo HỢP của sổ trên đĩa và sổ trên main.

    Một làn đã đẩy dòng giữ chỗ của mình nhưng cây này chưa thấy — lấy mỗi bên đĩa là ghi đè lên
    việc họ đang làm. Giữ chỗ là thứ thà thừa còn hơn thiếu.
    """
    import importlib
    m = importlib.import_module("dong_bo_cay")
    # main có dòng `xong`; thêm một dòng `đang làm` CHỈ trên main
    so_main = SO_MOI + "| Vòng | VD-11 — đã đẩy, cây chưa thấy | app/da_gop.py | 21-10-2026 08:00 | đang làm |\n"
    _ghi(kho_so_cu, "docs/dang-lam/vong.md", so_main)
    _git(kho_so_cu, "add", "-A"); _git(kho_so_cu, "commit", "-qm", "them dong tren main")
    _git(kho_so_cu, "update-ref", "refs/remotes/origin/main",
         _git(kho_so_cu, "rev-parse", "HEAD").strip())
    # Đĩa: KHÔNG có dòng giữ chỗ nào, và KHÔNG trùng bản cũ nào (thêm một dòng chú thích) — nên
    # nó không bị kéo về, và lời giữ chỗ DUY NHẤT là của sổ trên main. Bản đầu của phép thử này
    # để đĩa là `SO_CU` (vốn đã có dòng `đang làm`), nên nó xanh cả khi bỏ hẳn phần đọc sổ main —
    # phép thử ngược cho thấy đúng chỗ ấy, và đây là bản đã siết.
    _ghi(kho_so_cu, "docs/dang-lam/vong.md", SO_MOI + "\n<!-- ghi chú của làn, chưa đẩy -->\n")

    cwd = os.getcwd(); os.chdir(kho_so_cu)
    try:
        giu = m.tep_dang_giu(kho_so_cu)
    finally:
        os.chdir(cwd)
    assert "app/da_gop.py" in giu, (
        f"Dòng giữ chỗ chỉ có trên main bị bỏ qua — việc của làn ấy sẽ bị ghi đè.\n{giu}")
# ── KS-19: "khác main" KHÔNG đủ để ghi đè ───────────────────────────────────────────────────
def test_ks13_13_khac_main_ma_KHONG_phai_ban_cu_thi_de_nguyen(kho):
    """Lỗ của chính tệp này, đo được bằng cách nó ăn mất việc của người viết ra nó.

    Chiều 21/10/2026: `backend/Dockerfile` và `backend/app/api/v1/routes.py` vừa sửa xong cho đợt
    KS-18, chưa kịp khai vào sổ. Một lần bấm lấy main là cả hai bị ghi đè về bản main — vì luật
    cũ chỉ hỏi "khác main không?". "Khác main" có HAI nghĩa trái ngược: bản cũ chưa cập nhật, và
    việc đang làm dở chưa đẩy. Hỏi thêm một câu nữa mới phân biệt được: có trùng từng byte với
    một bản cũ của chính nó không.
    """
    kq = _chay(kho)
    assert "app/dang_sua.py" in kq["chua_ro"], kq
    assert "app/dang_sua.py" not in kq["cu"], "việc đang làm bị xếp nhầm vào nhóm bản cũ"
    assert _doc(kho, "app/dang_sua.py") == "# KHÁC main mà KHÔNG phải bản cũ nào\n", \
        "việc đang làm dở bị ghi đè"


def test_ks13_14_ban_cu_CHUNG_MINH_DUOC_thi_van_keo_ve_binh_thuong(kho):
    """Siết chặt không được làm công cụ ngừng hoạt động: bản cũ thật vẫn phải về."""
    kq = _chay(kho)
    assert "app/cu.py" in kq["cu"], kq
    assert _doc(kho, "app/cu.py") == "# bản MAIN\ny = 2\n"


def test_ks13_15_tep_chua_ro_duoc_BAO_RA_chu_khong_im_lang(kho):
    """Im lặng là chỗ nguy nhất: tệp lùi về mà không ai biết, rồi mọi phép đo chạy trên bản lùi."""
    import importlib
    m = importlib.import_module("dong_bo_cay")
    assert "chua_ro" in m.dong_bo(kho, chi_xem=True)
    ma = __import__("inspect").getsource(m)
    assert "chưa rõ" in ma, "kết quả không in nhóm `chưa rõ` ra cho người đọc"
