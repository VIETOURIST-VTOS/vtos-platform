# -*- coding: utf-8 -*-
"""KS-10 — cổng chống đo trên một bản sao đã cũ.

VÌ SAO CÓ TỆP NÀY. Ngày 17/10/2026 tôi báo sai HAI LẦN trong một ngày, và cả hai lần đều vì đọc
`origin/main` trong bản sao trên máy mà không biết bản sao ấy đứng yên từ bao giờ: lần đầu là "bộ
hàng rào có 3–4 đỏ sẵn có trên main" (xuất sạch ra thì xanh hết), lần sau nặng hơn — "hệ thật đang
chạy mã CHƯA DUYỆT", trong khi nhánh ấy đã được gộp một giờ trước.

`scripts/so-voi-main.sh` là cổng. Tệp này canh cổng, và nó canh ĐÚNG BA CÁCH cổng có thể thủng —
cả ba đều đã xảy ra thật, không cái nào là giả định:

  1. bản sao cũ mà vẫn in số  → người đọc tưởng số ấy nói về main hôm nay;
  2. `git fetch` HỎNG vẫn cắt `FETCH_HEAD` về 0 byte và đặt lại giờ, nên bản sao TRÔNG NHƯ mới;
  3. `git diff <commit> -- <tệp>` bỏ qua tệp CHƯA ĐƯỢC THEO DÕI và báo nó như đã xoá sạch.

ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không đòi bit thực thi (`os.access(..., X_OK)`). Kho này nằm trên một
thư mục Windows gắn vào, nơi bit ấy không giữ được — vòng VG-1b đã viết đúng một dòng `assert`
như thế và nó KHÔNG BAO GIỜ xanh nổi, làm đỏ cả bộ 45 phút. Ở đây hỏi câu trả lời được: có dòng
shebang không, và `bash <tệp>` có chạy không.
"""
import os
import subprocess
import sys
import tempfile
import time

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KICH_BAN = os.path.join(GOC, "scripts", "so-voi-main.sh")


def _git(cwd, *ds):
    return subprocess.run(["git", *ds], cwd=cwd, capture_output=True, text=True)


def _kho_gia(thu_muc, tuoi_giay=0, fetch_head_rong=False):
    """Dựng một kho git nhỏ có `origin/main` thật và một `FETCH_HEAD` do mình đặt giờ.

    Dựng kho thật chứ không chắp vá bằng `monkeypatch` là có chủ ý: thứ đang được thử là hành vi
    của một kịch bản shell gọi git thật, nên thay git bằng đồ giả là thử một thứ khác.
    """
    _git(thu_muc, "init", "-q", "-b", "main")
    _git(thu_muc, "config", "user.email", "ks@vtos.test")
    _git(thu_muc, "config", "user.name", "KS")
    with open(os.path.join(thu_muc, "cu.txt"), "w", encoding="utf-8") as f:
        f.write("mot\nhai\nba\n")
    _git(thu_muc, "add", "-A")
    _git(thu_muc, "commit", "-qm", "nen")
    sha = _git(thu_muc, "rev-parse", "HEAD").stdout.strip()
    _git(thu_muc, "update-ref", "refs/remotes/origin/main", sha)

    fh = os.path.join(thu_muc, ".git", "FETCH_HEAD")
    with open(fh, "w", encoding="utf-8") as f:
        if not fetch_head_rong:
            f.write(f"{sha}\t\tbranch 'main' of https://github.com/x/y\n")
    luc = time.time() - tuoi_giay
    os.utime(fh, (luc, luc))
    return sha


def _chay(thu_muc, *tep):
    return subprocess.run(["bash", KICH_BAN, *tep], cwd=thu_muc, capture_output=True, text=True)


# ---------------------------------------------------------------------------------------------
def test_ks10_1_kich_ban_co_that_va_chay_duoc():
    """Thiếu tệp này thì mọi phép thử dưới đây đỏ vì lý do sai — nên hỏi thẳng, hỏi trước."""
    assert os.path.isfile(KICH_BAN), (
        f"Không thấy {KICH_BAN}. Đây là cổng duy nhất chặn việc đo trên một bản sao đã cũ; "
        f"xoá nó đi thì không còn gì kêu lên nữa.")
    dong_dau = open(KICH_BAN, encoding="utf-8").readline()
    assert dong_dau.startswith("#!") and "bash" in dong_dau, (
        f"Dòng đầu của {os.path.basename(KICH_BAN)} phải là shebang bash, đang là “{dong_dau!r}”.")


def test_ks10_2_ban_sao_moi_thi_qua_cong():
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=60)
        r = _chay(d)
        assert r.returncode == 0, f"Bản sao vừa lấy main 1 phút trước mà bị chặn.\n{r.stderr}"
        assert "ĐỘ MỚI CỦA BẢN SAO" in r.stdout, (
            "Qua cổng nhưng không nói bản sao mới bao lâu. Người đọc cần con số ấy đứng cạnh con "
            f"số đo, không thì vẫn phải tin suông.\n{r.stdout}")


def test_ks10_3_ban_sao_cu_thi_CHAN_VA_KHONG_IN_SO():
    """Chặn mà vẫn in số thì cổng này vô dụng: người ta sẽ đọc số rồi bỏ qua lời cảnh báo."""
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=3600)
        with open(os.path.join(d, "cu.txt"), "a", encoding="utf-8") as f:
            f.write("bon\n")
        r = _chay(d, "cu.txt")
        assert r.returncode == 2, f"Bản sao cũ một tiếng mà vẫn cho qua (mã {r.returncode})."
        assert "BẢN SAO ĐÃ CŨ" in r.stderr, r.stderr
        assert "thêm" not in r.stdout and "TỔNG DÒNG BỊ XOÁ" not in r.stdout, (
            "Đã chặn mà VẪN IN SỐ. Một con số in ra kèm lời cảnh báo thì người ta chỉ nhớ con "
            f"số.\n{r.stdout}")


def test_ks10_4_fetch_hong_khong_duoc_tinh_la_moi():
    """CHỖ NGUY HIỂM NHẤT, và là thứ đã xảy ra thật 17/10/2026.

    Gọi `git fetch` từ máy ảo cầu nối báo lỗi `could not read Username for 'https://github.com'`
    nhưng VẪN cắt `FETCH_HEAD` về 0 byte và đặt lại giờ sửa tệp. Một cổng chỉ xét GIỜ sẽ nói
    "bản sao vừa mới lấy main" đúng vào lúc bản sao không học được gì cả — tức là nó tự thủng ở
    đúng trường hợp tệ nhất, và thủng một cách im lặng.
    """
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=10, fetch_head_rong=True)
        r = _chay(d, "cu.txt")
        assert r.returncode == 2, (
            f"FETCH_HEAD rỗng (lần lấy main HỎNG) mà cổng vẫn cho qua vì giờ còn mới (mã "
            f"{r.returncode}). Phải xét CẢ kích thước, không chỉ giờ.")
        assert "THẤT BẠI" in r.stderr, r.stderr
        assert "TỔNG DÒNG BỊ XOÁ" not in r.stdout, r.stdout


def test_ks10_5_tep_chua_theo_doi_phai_dem_dung():
    """`git diff origin/main -- <tệp>` BỎ QUA tệp chưa theo dõi và báo nó như ĐÃ XOÁ SẠCH.

    Sáng 17/10/2026 nó báo sổ giữ chỗ là “0 thêm / 21 xoá” trong khi tệp nằm nguyên trên đĩa với
    23 dòng. Khai con số ấy vào `VONG_XOA.txt` là tự cho phép mình xoá 21 dòng mà không ai hỏi.
    """
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=60)
        # cùng đường dẫn đã có trên main, nhưng bản trên đĩa KHÔNG nằm trong index
        _git(d, "rm", "-q", "--cached", "cu.txt")
        with open(os.path.join(d, "cu.txt"), "w", encoding="utf-8") as f:
            f.write("mot\nhai\nba\nbon\n")
        r = _chay(d, "cu.txt")
        assert r.returncode == 0, r.stderr
        dong = [l for l in r.stdout.splitlines() if "cu.txt" in l]
        assert dong, r.stdout
        assert "thêm 1" in dong[0] and "xoá 0" in dong[0], (
            "Tệp CHƯA ĐƯỢC THEO DÕI bị đếm sai — phải là thêm 1 / xoá 0, đang là:\n"
            f"  {dong[0]}\nĐây đúng là cách `git diff <commit> -- <tệp>` nói dối: nó không thấy "
            "tệp chưa theo dõi nên báo như đã xoá sạch.")
        assert "TỔNG DÒNG BỊ XOÁ : 0" in r.stdout, r.stdout


def test_ks10_6_tep_moi_chua_tung_co_tren_main():
    """Tệp mới thì không có bản cũ để so — phải ra 'thêm N / xoá 0', không được vỡ."""
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=60)
        with open(os.path.join(d, "moi.txt"), "w", encoding="utf-8") as f:
            f.write("a\nb\n")
        with open(os.path.join(d, "cu.txt"), "w", encoding="utf-8") as f:
            f.write("mot\nHAI DOI\nba\n")        # 1 dòng bị thay = 1 thêm 1 xoá
        r = _chay(d, "moi.txt", "cu.txt")
        assert r.returncode == 0, r.stderr
        assert "thêm 2" in [l for l in r.stdout.splitlines() if "moi.txt" in l][0], r.stdout
        assert "TỔNG DÒNG BỊ XOÁ : 1" in r.stdout, (
            f"Tổng dòng bị xoá phải là 1 (một dòng của cu.txt bị thay).\n{r.stdout}")


def test_ks10_7_tep_thieu_tren_dia_phai_keu_chu_khong_am_tham_bo_qua():
    """Gõ nhầm một đường dẫn mà cổng lặng lẽ bỏ qua thì tổng dòng xoá thiếu đi một tệp, và con số
    khai vào `VONG_XOA.txt` nhỏ hơn thật — đúng chiều nguy hiểm."""
    with tempfile.TemporaryDirectory(dir=tempfile.gettempdir()) as d:
        _kho_gia(d, tuoi_giay=60)
        r = _chay(d, "khong-co-tep-nay.txt")
        assert "THIẾU TRÊN ĐĨA" in r.stderr, (
            f"Đường dẫn không tồn tại bị bỏ qua không một tiếng nào.\n{r.stdout}\n{r.stderr}")
