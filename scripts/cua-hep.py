# -*- coding: utf-8 -*-
"""CỬA HẸP CHẠY TRÊN MÁY — thay cho cửa hẹp của CI trong lúc Actions bị chặn. CHỈ ĐỌC.

    cd <goc repo> && python scripts\\cua-hep.py --nhanh main
    cd <goc repo> && python scripts\\cua-hep.py --nhanh <ten-nhanh-cua-ban>

    hoặc bấm  scripts\\!CUA-HEP.bat  rồi gõ tên nhánh vào.

BẢN NÀY DÙNG CHUNG CHO MỌI LÀN. Nó CHỈ ĐỌC: dựng một `git worktree` riêng cho mỗi nhánh,
chạy xong thì dọn, và KHÔNG chạm vào cây làm việc chung. Hai làn chạy cùng lúc trên hai
nhánh khác nhau không đụng nhau.

Bản này KHÔNG tự ghi tệp kết quả — nút `.bat` đã hứng sẵn nhật ký của chính nó.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ TỆP NÀY
═══════════════════════════════════════════════════════════════════════════════════════════════

Ngân sách Actions chạm trần 24/10 nên **CI không chạy**. Hệ quả ít ai để ý: các làn vẫn đẩy mã
lên, nhưng **không hàng rào nào canh nữa**. Mà loại hỏng mà cửa hẹp bắt là loại không ai thấy
bằng mắt:

    Hai PR cùng xanh RIÊNG LẺ vẫn có thể hỏng khi GỘP LẠI: làn A thêm một bản di trú, làn B cũng
    thêm một bản — mỗi nhánh một đầu mạch nên cả hai đều xanh, gộp xong thành hai đầu và hộp
    chứa chết lúc khởi động.                                     (ghi trong chính `ci.yml`)

Máy Chủ tịch có python 3.12. Mười bảy phép thử ấy chạy được ở đó.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHẠY ĐÚNG NHỮNG GÌ CI CHẠY — CHÉP TỪ `ci.yml`, KHÔNG TỰ CHỌN
═══════════════════════════════════════════════════════════════════════════════════════════════

Danh sách 17 tệp dưới đây chép nguyên từ việc `hang-rao-gop`. Tự chọn lấy vài phép «cho nhanh»
là dựng một cửa kiểm chạy thiếu — mà `ci.yml` đã ghi: *«một cửa kiểm chạy thiếu mà vẫn xanh là
thứ nguy hiểm hơn không có cửa nào»*.

`VTOS_TEP_DOI` LÀ BẮT BUỘC. `test_giu_cho_nhanh` cần danh sách tệp nhánh này đổi; thiếu nó thì
phép thử đỏ **vì thiếu môi trường, không vì có lỗi thật** — đúng kiểu đỏ làm người ta tắt hàng
rào. Tệp này tự tính danh sách ấy bằng `git diff --name-only origin/main <nhánh>`.

Dùng `git worktree` riêng — KHÔNG `checkout` trong cây làm việc chung.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import time

for _luong in (sys.stdout, sys.stderr):
    try:
        _luong.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chép nguyên từ việc `hang-rao-gop` trong .github/workflows/ci.yml
PHEP_THU = [
    "tests/test_mach_migration.py",
    "tests/test_menu.py",
    "tests/test_p11_khai_quyen_phai_co_man_hinh.py",
    "tests/test_ks_ma_tran.py",
    "tests/test_p2_pham_vi_vai_tro.py",
    "tests/test_giu_cho_lan.py",
    "tests/test_giu_cho_nhanh.py",
    "tests/test_ks_do_dai.py",
    "tests/test_ks2_khai_quyen_may_doc_duoc.py",
    "tests/test_ks_cua_nhap.py",
    "tests/test_man_hinh_co_cua_nhap.py",
    "tests/test_lg1_hai_bang_quyen_khop_nhau.py",
    "tests/test_lg2_mot_bang_chu_ky.py",
    "tests/test_ks_toan_quyen.py",
    "tests/test_le2b_ba_vai_ke_toan.py",
    "tests/test_hach_toan.py",
    "tests/test_misa.py",
]

ra = []


def thieu_goi(ten, dau_ra):
    """Máy có cài gói `ten` không. Bắt ĐÚNG dòng python in ra khi thiếu gói, không tra lỏng.

    Tra lỏng kiểu `"No module named pytest" in dau_ra` thì **sai một ca có thật**: pytest ĐÃ cài
    mà một tệp phép thử lại `import pytest_asyncio` không có, câu báo là «No module named
    pytest_asyncio» — chuỗi trên nằm trong đó, nên cửa hẹp sẽ nói «máy chưa cài pytest» trong khi
    thật ra là một tệp phép thử hỏng. Báo sai nguyên nhân thì người đọc đi sửa nhầm chỗ.
    """
    return re.search(r"(?m)^.*: No module named " + re.escape(ten) + r"\s*$", dau_ra) is not None


def noi(s=""):
    print(s, flush=True)
    ra.append(s)


def git(*a, cwd=None, phut=8):
    r = subprocess.run(["git"] + list(a), cwd=cwd or GOC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=phut * 60)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def go_worktree(wt, tam):
    git("worktree", "remove", "--force", wt)
    if os.path.isdir(wt):
        shutil.rmtree(wt, ignore_errors=True)
    git("worktree", "prune")
    git("branch", "-D", tam)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nhanh", required=True, help="main, hoặc tên một nhánh trên origin")
    a = p.parse_args()
    if not os.path.isdir(os.path.join(GOC, ".git")):
        print("DỪNG — chạy ở GỐC repo.")
        sys.exit(1)

    noi(f"CỬA HẸP TRÊN MÁY — nhánh «{a.nhanh}»")
    noi("Lúc: " + time.strftime("%d-%m-%Y %H:%M:%S") + " · CHỈ ĐỌC")
    noi("=" * 84)
    _, nh, _ = git("rev-parse", "--abbrev-ref", "HEAD")
    noi(f"cây chung: nhánh {nh.strip()} — script KHÔNG chạm vào đây")
    git("fetch", "origin", "main", "--quiet")
    if a.nhanh == "main":
        rev = "origin/main"
    else:
        rc, _, err = git("fetch", "origin", f"{a.nhanh}:refs/remotes/origin/{a.nhanh}", "--force")
        if rc != 0:
            noi("DỪNG — không lấy được nhánh: " + err.strip().split("\n")[0][:160])
            xuat(a.nhanh); sys.exit(1)
        rev = f"refs/remotes/origin/{a.nhanh}"
    _, s, _ = git("log", "-1", "--format=%h · %cd · %s", "--date=format:%d-%m %H:%M", rev)
    noi("đang soi: " + s.strip()[:96])

    # MỖI NHÁNH MỘT CHỖ LÀM RIÊNG. Bản đầu dùng chung một tên `_wt-cua-hep` cho mọi nhánh, và
    # 25/10/2026 chuyện ấy hỏng thật: Chủ tịch bấm bốn nút trong 40 giây, lượt sau vừa khởi động
    # đã `git worktree remove --force` ngay thư mục mà pytest của lượt trước đang chạy trong đó —
    # nên lượt main trả về RỖNG, không một dòng nào. Nhật ký ghi «(không có đầu ra)», trông như
    # phép thử câm chứ không ai đoán ra là bị lượt sau xoá chân.
    ten_gon = "".join(c if c.isalnum() else "-" for c in a.nhanh)[:40]
    wt = os.path.join(GOC, "_wt-cua-hep-" + ten_gon)
    tam = "cua-hep-tam-" + ten_gon
    go_worktree(wt, tam)
    rc, _, err = git("worktree", "add", "-B", tam, wt, rev)
    if rc != 0:
        noi("DỪNG — không dựng được worktree: " + err.strip()[:180])
        xuat(a.nhanh); sys.exit(1)
    try:
        # danh sách tệp nhánh này đổi — `test_giu_cho_nhanh` BẮT BUỘC phải có
        tep_doi = os.path.join(wt, "_tep_doi.txt")
        if a.nhanh == "main":
            # CI chỉ dựng danh sách này `if: github.event_name == 'pull_request'`. Trên main nó
            # KHÔNG đặt biến. Ở đây làm y thế — đặt một tệp RỖNG là một đầu vào khác hẳn («nhánh
            # này không đổi tệp nào»), và cửa hẹp chạy sai đầu vào thì màu của nó không nói gì.
            tep_doi = None
            noi("")
            noi("danh sách tệp đổi: KHÔNG đặt — đang soi main, CI cũng không đặt trên main")
        else:
            _, nm, _ = git("diff", "--name-only", "origin/main", rev)
            ds = [l.strip() for l in nm.split("\n") if l.strip()]
            with open(tep_doi, "w", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(ds) + ("\n" if ds else ""))
            noi("")
            noi(f"danh sách tệp đổi: {len(ds)} tệp → _tep_doi.txt")

        moi = dict(os.environ, PYTHONIOENCODING="utf-8:replace", PYTHONDONTWRITEBYTECODE="1")
        if tep_doi:
            moi["VTOS_TEP_DOI"] = tep_doi
        else:
            moi.pop("VTOS_TEP_DOI", None)
        be = os.path.join(wt, "backend")

        noi("")
        noi("1 · RUFF (E9,F63,F7,F82)")
        r = subprocess.run([sys.executable, "-m", "ruff", "check", "app",
                            "--select", "E9,F63,F7,F82"],
                           cwd=be, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=moi, timeout=600)
        if thieu_goi("ruff", (r.stdout or "") + (r.stderr or "")):
            noi("    ⚠ máy CHƯA CÀI ruff — bước này KHÔNG soát được (không phải là sạch).")
            noi("       Cài một lần:  python -m pip install ruff")
        else:
            noi("    " + ("✓ sạch" if r.returncode == 0 else "⚠ CÓ LỖI:"))
            for l in (r.stdout + r.stderr).strip().split("\n")[:10]:
                if l.strip():
                    noi("        " + l[:100])

        noi("")
        noi(f"2 · {len(PHEP_THU)} TỆP PHÉP THỬ (chép nguyên từ ci.yml)")
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header",
                            "-p", "no:cacheprovider"] + PHEP_THU,
                           cwd=be, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=moi, timeout=1800)
        out = (r.stdout or "") + (r.stderr or "")
        dong = [l for l in out.split("\n") if l.strip()]
        if thieu_goi("pytest", out):
            noi("    ⛔ máy chưa cài pytest — CHƯA CHẠY ĐƯỢC cửa hẹp. Đây KHÔNG phải là xanh.")
            noi("       Cài một lần:  python -m pip install -r backend\\requirements-dev.txt")
            ma = 3
        else:
            for l in dong[:-1]:   # dòng cuối in riêng ở dưới, đừng in hai lần
                if l.startswith(("FAILED", "ERROR")) or " error" in l.lower():
                    noi("    " + l[:120])
            if not dong:
                # pytest KHÔNG bao giờ im lặng. Rỗng nghĩa là nó bị cắt chân giữa chừng.
                noi("    ⛔ KHÔNG CÓ MỘT DÒNG NÀO — pytest không bao giờ chạy mà câm.")
                noi("       Gần như chắc là có một lượt cửa hẹp KHÁC chạy đè lên. Để mỗi lượt")
                noi("       chạy xong (đóng cửa sổ đen) rồi hãy bấm nút kế tiếp.")
                ma = 4
            else:
                noi("    " + dong[-1][:110])
                noi("")
                noi("    " + ("✓ CỬA HẸP XANH" if r.returncode == 0
                              else "⛔ CỬA HẸP ĐỎ — đọc dòng FAILED/ERROR ở trên"))
                ma = r.returncode
    finally:
        go_worktree(wt, tam)

    noi("")
    noi("Cửa hẹp KHÔNG thay bộ đủ (251 tệp, ~55 phút). Nó chỉ soi chuyện hai làn đụng nhau —")
    noi("đúng loại hỏng mà xanh-riêng-lẻ không bắt được.")
    xuat(a.nhanh)
    sys.exit(ma)


def xuat(nhanh):
    """Bản dùng chung KHÔNG ghi tệp kết quả — nút `.bat` đã hứng nhật ký của chính nó.

    Bản riêng của làn Phân quyền ghi vào `0-BAM-R1/`. Giữ nguyên chỗ ấy ở bản dùng chung
    thì mười làn kia mỗi lượt chạy lại ghi một tệp vào thư mục RIÊNG của một làn.
    """
    del nhanh


if __name__ == "__main__":
    main()
