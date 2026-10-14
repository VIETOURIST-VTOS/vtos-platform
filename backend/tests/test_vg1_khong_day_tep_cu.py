# -*- coding: utf-8 -*-
"""VG-1 · Hàng rào chặn đẩy một TỆP CŨ đè lên bản mới (làn Kiểm soát, 14/10/2026).

VÌ SAO SINH RA. Vòng đẩy của bốn làn commit NGUYÊN TỆP từ đĩa lên một gốc vừa fetch. Tệp trên đĩa
là bản cũ thì lần đẩy ấy XOÁ SẠCH phần làn khác vừa thêm — và git không báo một chữ xung đột nào,
vì đẩy nguyên tệp thì không có gì để xung đột. `VONG_DAY.bat` ghi lại chuyện ấy đã xảy ra
19/9 và 23/9/2026. Ngày 14/10 suýt lần thứ ba: cây làm việc chung đang ở HEAD ngày 16/9, chậm sau
`origin/main` 511 commit, nên `backend/tests/test_tc40_man_hinh_gon.py` trên đĩa là bản 18/9 —
vá lên bản ấy rồi đẩy là xoá luôn bản sửa E17 vừa merge.

HÀNG RÀO CŨ VÀ CHỖ NÓ HỞ. `VONG_DAY.bat` đã đếm dòng bị xoá và bắt khai trước trong `VONG_XOA.txt`.
Chú thích của chính nó gọi con số ấy là "một LỜI HỨA". Một làn tính VONG_XOA **từ chính tệp cũ** sẽ
khai đúng con số lớn ấy và đi thẳng qua cửa. Hàng rào này hỏi một câu không cần lời hứa: bản trên
đĩa có trùng NGUYÊN SI một bản cũ của chính đường dẫn ấy không.

VÌ SAO PHÉP THỬ NẰM Ở ĐÂY MÀ KHÔNG CANH THẲNG `VONG_DAY.bat`: tệp .bat ấy **không nằm trong kho**
(`git ls-files` không có nó), nên CI không bao giờ nhìn thấy. Thứ canh được là PHẦN LUẬT —
`scripts/kiem-tep-cu.sh` — và đó là thứ phép thử này canh. Phần gọi nằm trong tệp .bat vẫn là chỗ
hở có thật, ghi ra đây để không ai tưởng là đã kín.
"""
import os
import subprocess
import tempfile
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
KICH_BAN = GOC / "scripts" / "kiem-tep-cu.sh"


def test_vg1_0_kich_ban_con_do():
    assert KICH_BAN.exists(), (
        "Mất `scripts/kiem-tep-cu.sh`. Đây là phần LUẬT của hàng rào chặn đẩy tệp cũ; "
        "`VONG_DAY.bat` gọi vào nó. Mất tệp này là cửa mở lại.")
    # KHÔNG đòi bit thực thi, và lý do đáng ghi (sửa 14/10/2026, ngay sau khi chính dòng cũ
    # làm bộ 45 phút đỏ): bản cũ viết `assert os.access(KICH_BAN, os.X_OK)`. Nó xanh trên máy
    # Linux nhưng KHÔNG THỂ xanh trên CI, vì cây làm việc nằm trên ổ Windows — ổ ấy không giữ
    # bit thực thi, nên git ghi tệp ở mode 100644 và runner nhận một tệp không chạy trực tiếp
    # được. Một phép thử không bao giờ xanh nổi ở chỗ nó phải xanh là một phép thử hỏng.
    #
    # Và bit ấy KHÔNG CẦN: không chỗ nào gọi `./kiem-tep-cu.sh`. Cả sáu phép thử dưới đây lẫn
    # `VONG_DAY.bat` đều gọi `bash <đường dẫn>`, chạy được bất kể quyền. Nên nay đòi thứ thật
    # sự cần: tệp có nội dung và là một kịch bản shell.
    dau = KICH_BAN.read_text(encoding="utf-8")[:64]
    assert dau.startswith("#!"), (
        f"scripts/kiem-tep-cu.sh phải là kịch bản shell (dòng đầu là #!...), thấy: {dau[:40]!r}")
    assert "bash" in dau, "Dòng #! phải gọi bash – phần dưới dùng mapfile và process substitution."


def _kho(tmp: Path):
    """Dựng một kho git bé: v1 rồi v2 của cùng một tệp, có nhánh 'main'."""
    def g(*a, **kw):
        return subprocess.run(["git", *a], cwd=tmp, check=True,
                              capture_output=True, text=True, **kw)
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t.t"); g("config", "user.name", "t")
    f = tmp / "a.txt"
    f.write_text("dong 1\ndong 2\n", encoding="utf-8")
    g("add", "."); g("commit", "-qm", "v1")
    f.write_text("dong 1\ndong 2\ndong 3 cua lan khac\n", encoding="utf-8")
    g("add", "."); g("commit", "-qm", "v2")
    return f


def _chay(tmp: Path, *tep, moi_truong=None):
    mt = {**os.environ, **(moi_truong or {})}
    return subprocess.run(["bash", str(KICH_BAN), "main", *tep],
                          cwd=tmp, capture_output=True, text=True, env=mt)


def test_vg1_1_tep_cu_thi_DUNG_LAI():
    """Đĩa mang bản v1 trong khi main đã ở v2 — phải chặn."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); f = _kho(tmp)
        f.write_text("dong 1\ndong 2\n", encoding="utf-8")        # quay về v1
        r = _chay(tmp, "a.txt")
        assert r.returncode == 1, f"Phải chặn mà không chặn.\n{r.stdout}\n{r.stderr}"
        assert "BẢN CŨ NGUYÊN SI" in r.stdout
        assert "a.txt" in r.stdout


def test_vg1_2_tep_dung_ban_moi_thi_cho_qua():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); _kho(tmp)
        r = _chay(tmp, "a.txt")
        assert r.returncode == 0, f"Bản đúng mà bị chặn.\n{r.stdout}\n{r.stderr}"


def test_vg1_3_sua_that_tren_nen_moi_thi_cho_qua():
    """Đây là chỗ dễ làm hàng rào thành vô dụng: chặn cả sửa thật thì người ta tắt nó."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); f = _kho(tmp)
        f.write_text("dong 1\ndong 2\ndong 3 cua lan khac\ndong 4 cua minh\n", encoding="utf-8")
        r = _chay(tmp, "a.txt")
        assert r.returncode == 0, f"Sửa thật trên nền mới mà bị chặn.\n{r.stdout}\n{r.stderr}"


def test_vg1_4_tep_moi_hoan_toan_thi_cho_qua():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); _kho(tmp)
        (tmp / "b.txt").write_text("tep moi\n", encoding="utf-8")
        r = _chay(tmp, "b.txt")
        assert r.returncode == 0, f"Tệp mới mà bị chặn.\n{r.stdout}\n{r.stderr}"


def test_vg1_5_co_y_quay_ve_ban_cu_phai_khai_ro():
    """Có đường đi tiếp, nhưng phải khai — không có đường thì người ta sẽ gỡ hẳn hàng rào."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); f = _kho(tmp)
        f.write_text("dong 1\ndong 2\n", encoding="utf-8")
        assert _chay(tmp, "a.txt").returncode == 1
        r = _chay(tmp, "a.txt", moi_truong={"VG1_CO_Y": "1"})
        assert r.returncode == 0, f"Khai cố ý rồi mà vẫn chặn.\n{r.stdout}\n{r.stderr}"


def test_vg1_6_doc_duoc_VONG_TEP_txt():
    """Vòng đẩy đọc danh sách từ VONG_TEP.txt; hàng rào phải đọc đúng danh sách ấy."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d); f = _kho(tmp)
        f.write_text("dong 1\ndong 2\n", encoding="utf-8")
        (tmp / "VONG_TEP.txt").write_text("# ghi chu\n\na.txt\n", encoding="utf-8")
        r = subprocess.run(["bash", str(KICH_BAN), "main"], cwd=tmp,
                           capture_output=True, text=True)
        assert r.returncode == 1, f"Đọc VONG_TEP.txt không ra.\n{r.stdout}\n{r.stderr}"
        assert "a.txt" in r.stdout
