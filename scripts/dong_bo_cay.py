#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KS-13 — KÉO CÂY LÀM VIỆC VỀ ĐÚNG BẢN MAIN, TRỪ NHỮNG TỆP ĐANG CÓ LÀN GIỮ.

VÌ SAO CÓ TỆP NÀY

`VONG_DAY.bat` dựng commit bằng `read-tree` + `update-index --add` + `commit-tree`: nó KHÔNG
bao giờ checkout. Nghĩa là nó chỉ ghi lên đĩa những tệp của chính vòng đang đẩy, còn tệp MỚI do
vòng của làn khác tạo ra thì không bao giờ đi xuống cây làm việc chung. Mỗi lần một làn gộp một
vòng có tệp mới, cây chung thủng thêm một lỗ — và lỗ ấy im lặng cho tới khi nó nằm đúng trên
đường nạp mô-đun.

ĐO ĐƯỢC 21/10/2026 trên cây chung `Documents\\vtos-platform`, gốc `bf822b7`:

    thiếu hẳn trên đĩa                         24 tệp
    khác bản main mà KHÔNG làn nào giữ         28 tệp   (bản cũ)
    khác bản main và ĐANG có làn giữ           21 tệp   (việc đang làm)

Trong 28 tệp cũ ấy có `.github/workflows/ci.yml`, `backend/app/models/__init__.py`,
`backend/tests/test_man_hinh_co_cua_nhap.py` (một tệp của cửa hẹp) và `web/app/page.tsx`. Làn
nào lỡ đưa một trong số đó vào vòng của mình là đẩy bản bốn ngày trước đè lên main — đúng tai
nạn mà hàng rào VG-1 sinh ra để chặn, chỉ khác là lần này nó đi vào từ phía cây làm việc.

Hệ quả nặng nhất không phải mã sai, mà là SỐ ĐO SAI: mọi phép thử chạy trên cây ấy đều nói về
một bản không tồn tại ở đâu cả. Làn Kiểm soát đã trả giá hai lần — báo "3–4 đỏ sẵn có trên main"
hôm 17/10 (sai), và một lần nữa 21/10.

BA LUẬT

1. CHỈ KÉO VỀ, KHÔNG XOÁ GÌ. Tệp nằm trên đĩa mà main không có thì để nguyên — đó có thể là
   tệp một làn vừa tạo mà chưa đẩy.

2. KHÔNG ĐỤNG TỆP ĐANG CÓ LÀN GIỮ. Sổ giữ chỗ là lời khai duy nhất về "ai đang làm gì"; tệp
   nào đứng trong một dòng `đang làm` thì bản trên đĩa là việc đang viết dở, không phải bản cũ.
   Đây là phần quan trọng nhất của tệp này: một bộ đồng bộ không đọc sổ sẽ xoá sạch việc đang
   làm của người khác, và xoá lúc nửa đêm khi không ai nhìn.

3. CẤT BẢN CŨ TRƯỚC KHI GHI ĐÈ, vào `_cu-truoc-khi-dong-bo-<ngày>/`. Thư mục ấy không nằm
   trong git. Một bộ đồng bộ không giữ lại bản cũ là một bộ không ai dám bấm lần thứ hai.

CÁCH DÙNG
    python scripts/dong_bo_cay.py            # đồng bộ thật
    python scripts/dong_bo_cay.py --xem      # chỉ kê ra, không ghi gì

Gọi SAU `git fetch`. Không có `origin/main` mới thì nó kéo về bản cũ — vô hại nhưng vô ích.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import date

DANG_LAM = "đang làm"
SO_COT = 5


def _git(*ds: str, nhi_phan: bool = False):
    r = subprocess.run(["git", *ds], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(ds)} → {r.stderr.decode('utf-8', 'replace')[:200]}")
    return r.stdout if nhi_phan else r.stdout.decode("utf-8", "replace")


def goc_kho() -> str:
    return _git("rev-parse", "--show-toplevel").strip()


def tep_cua_main(ref: str = "origin/main") -> dict[str, str]:
    """{đường dẫn: mã băm blob} — một lượt hỏi git, không duyệt cây bằng tay."""
    ra = {}
    for d in _git("ls-tree", "-r", ref).splitlines():
        if not d.strip():
            continue
        meta, duong = d.split("\t", 1)
        ra[duong] = meta.split()[2]
    return ra


def tep_so(goc: str) -> list[str]:
    """Đường dẫn mọi tệp sổ giữ chỗ, tính từ gốc kho."""
    ra = ["docs/DANG-LAM.md"]
    tm = os.path.join(goc, "docs", "dang-lam")
    if os.path.isdir(tm):
        ra += [f"docs/dang-lam/{t}" for t in sorted(os.listdir(tm))
               if t.endswith(".md") and t != "README.md"]
    return [d for d in ra if os.path.exists(os.path.join(goc, d))]


def la_ban_cu_nguyen_si(goc: str, duong: str, ref: str = "origin/main") -> bool:
    """Bản trên đĩa có TRÙNG TỪNG BYTE với một bản CŨ của chính đường dẫn ấy không?

    Cùng một câu hỏi `scripts/kiem-tep-cu.sh` (vòng VG-1) hỏi. Trùng khít một bản trong lịch sử
    thì gần như chắc chắn là tệp cũ chứ không phải trùng hợp — và quan trọng hơn: một tệp như thế
    KHÔNG chứa dòng nào mới, vì nó đúng là một commit cũ.
    """
    that = os.path.join(goc, duong)
    if not os.path.exists(that):
        return False
    with open(that, "rb") as f:
        d = f.read()
    import hashlib
    bam = hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()
    try:
        ds = _git("rev-list", ref, "--", duong).split()
    except RuntimeError:
        return False
    for c in ds[:60]:                       # 60 lần sửa gần nhất là quá đủ
        try:
            if _git("rev-parse", f"{c}:{duong}").strip() == bam:
                return True
        except RuntimeError:
            continue
    return False


def dong_bo_so(goc: str, ref: str = "origin/main") -> list[str]:
    """KÉO SỔ VỀ TRƯỚC, và chỉ những quyển CHỨNG MINH ĐƯỢC là bản cũ.

    VÌ SAO PHẢI LÀM TRƯỚC — đo được 21/10/2026, và đây là một lỗ của chính vòng KS-13:
    `docs/dang-lam/vong.md` trên đĩa là bản cũ nguyên si của commit ngày 17/10. Trong bản ấy
    dòng HD-Q2a còn `đang làm`, nên nó GIỮ `models/danh_gia.py`, `api/v1/danh_gia.py` và
    `api/v1/cskh.py` — ba tệp cũng là bản cũ. Trên main thì dòng HD-Q2a đã `xong` từ lâu.

    Tức là MỘT QUYỂN SỔ CŨ BẢO VỆ ĐÚNG NHỮNG TỆP CŨ, và bộ đồng bộ đứng nhìn. Nó còn dựng ra một
    va chạm giả: sổ cũ của làn Vòng và sổ thật của làn Phân quyền cùng khai `ks_cua_nhap.py`,
    `test_giu_cho_lan` đỏ trên cây mà trên main thì không.

    CHỈ kéo về quyển TRÙNG KHÍT một bản cũ. Quyển nào đã có dòng mới thì không trùng bản nào, và
    nó được giữ nguyên — dòng vừa khai của một làn không bao giờ bị bộ này xoá.
    """
    xong = []
    for duong in tep_so(goc):
        if la_ban_cu_nguyen_si(goc, duong, ref):
            that = os.path.join(goc, duong)
            with open(that, "wb") as f:
                f.write(_git("show", f"{ref}:{duong}", nhi_phan=True))
            xong.append(duong)
    return xong


def tep_dang_giu(goc: str) -> dict[str, str]:
    """{đường dẫn: "<làn> · <mã việc>"} đọc từ MỌI tệp sổ, chỉ lấy dòng `đang làm`.

    Đọc theo SỐ CỘT đúng như `test_giu_cho_lan`: bảng hướng dẫn hai cột ở đầu tệp phải bị bỏ
    qua, và một dòng sổ lỡ có ký tự ngăn cột trong phần mô tả sẽ ra sai số cột — dòng ấy coi như
    không giữ gì, y như hàng rào đang hiểu. Hai nơi hiểu sổ khác nhau thì sớm muộn cũng lệch.
    """
    ra: dict[str, str] = {}
    for duong in tep_so(goc):
        # HỢP của sổ TRÊN ĐĨA và sổ TRÊN MAIN. Lấy hợp chứ không lấy một bên: bên đĩa có thể
        # mang dòng một làn vừa khai mà chưa đẩy (bỏ qua là ghi đè lên việc họ đang viết), bên
        # main có thể mang dòng một làn đã đẩy mà đĩa chưa thấy (bỏ qua cũng vậy). Giữ chỗ là
        # thứ thà thừa còn hơn thiếu.
        van_ban = []
        that = os.path.join(goc, duong)
        if os.path.exists(that):
            with open(that, encoding="utf-8") as f:
                van_ban.append(f.read())
        try:
            van_ban.append(_git("show", f"origin/main:{duong}"))
        except RuntimeError:
            pass
        for noi_dung in van_ban:
            for raw in noi_dung.splitlines():
                dong = raw.strip()
                if not dong.startswith("|"):
                    continue
                o = [x.strip() for x in dong.strip("|").split("|")]
                if len(o) != SO_COT or o[4].lower() != DANG_LAM:
                    continue
                ten = f"{o[0]} · {' '.join(o[1].split())[:40]}"
                for t in (x.strip() for x in o[2].split(",")):
                    if t:
                        ra.setdefault(t, ten)
    return ra


def bam_tep(duong: str) -> str:
    import hashlib
    with open(duong, "rb") as f:
        d = f.read()
    return hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()


def soat(goc: str, ref: str = "origin/main"):
    """Trả về (thiếu, cũ, đang_giữ) — ba danh sách rời nhau."""
    main = tep_cua_main(ref)
    giu = tep_dang_giu(goc)
    # SỔ GIỮ CHỖ KHÔNG BAO GIỜ ĐI QUA ĐƯỜNG CHUNG. Một quyển sổ thường không được dòng nào khai
    # (các làn khai sổ của chính mình, nhưng không phải lúc nào cũng nhớ), nên nó sẽ rơi vào
    # nhóm "cũ, không ai giữ" và bị ghi đè — cùng với nó là mọi dòng giữ chỗ một làn vừa khai mà
    # chưa đẩy. `test_ks13_11` bắt được đúng chỗ này khi vòng KS-14 mới viết xong.
    # Sổ chỉ đi qua `dong_bo_so`, nơi đòi CHỨNG MINH là bản cũ trước khi đụng. Sổ THIẾU HẲN thì
    # vẫn kéo về bình thường: không có gì để mất.
    la_so = set(tep_so(goc)) | {d for d in main if d.startswith("docs/dang-lam/") or d == "docs/DANG-LAM.md"}
    thieu, cu, dang_giu = [], [], []
    for duong, sha in main.items():
        that = os.path.join(goc, duong)
        if not os.path.exists(that):
            thieu.append(duong)
        elif bam_tep(that) != sha:
            if duong in la_so:
                continue                      # sổ: để `dong_bo_so` quyết, không đụng ở đây
            (dang_giu if duong in giu else cu).append(duong)
    return sorted(thieu), sorted(cu), sorted(dang_giu), giu


def dong_bo(goc: str, ref: str = "origin/main", chi_xem: bool = False) -> dict:
    so_da_keo = [] if chi_xem else dong_bo_so(goc, ref)   # SỔ TRƯỚC, rồi mới xét ai giữ gì
    thieu, cu, dang_giu, giu = soat(goc, ref)
    kho = os.path.join(goc, f"_cu-truoc-khi-dong-bo-{date.today():%Y-%m-%d}")

    if not chi_xem:
        for duong in thieu + cu:
            that = os.path.join(goc, duong)
            if os.path.exists(that):                       # chỉ bản CŨ mới cần cất
                luu = os.path.join(kho, duong)
                os.makedirs(os.path.dirname(luu), exist_ok=True)
                shutil.copy2(that, luu)
            os.makedirs(os.path.dirname(that), exist_ok=True)
            with open(that, "wb") as f:
                f.write(_git("show", f"{ref}:{duong}", nhi_phan=True))

    return {"thieu": thieu, "cu": cu, "dang_giu": dang_giu, "giu": giu, "so_da_keo": so_da_keo,
            "kho_cat": kho if (cu and not chi_xem) else None, "chi_xem": chi_xem}


def main(argv: list[str]) -> int:
    chi_xem = "--xem" in argv
    try:
        goc = goc_kho()
    except (RuntimeError, FileNotFoundError):
        # Chạy ngoài một kho git (ví dụ trên một bản xuất sạch) — nói ra, đừng đổ traceback:
        # tệp này được gọi từ một tệp .bat, và traceback trong cửa sổ đen thì không ai đọc.
        print("KHÔNG PHẢI KHO GIT: chạy lệnh này từ trong kho vtos-platform.")
        return 1
    os.chdir(goc)
    try:
        kq = dong_bo(goc, chi_xem=chi_xem)
    except RuntimeError as e:
        print(f"KHÔNG ĐỒNG BỘ ĐƯỢC: {e}")
        print("Thường là chưa có `origin/main` — chạy `git fetch origin` trước.")
        return 1

    lam = "SẼ KÉO VỀ" if chi_xem else "ĐÃ KÉO VỀ"
    print("=== ĐỒNG BỘ CÂY LÀM VIỆC VỚI origin/main ===")
    print(f"{lam:<12} thiếu hẳn : {len(kq['thieu'])} tệp")
    for d in kq["thieu"][:40]:
        print(f"               + {d}")
    if len(kq["thieu"]) > 40:
        print(f"               … và {len(kq['thieu']) - 40} tệp nữa")
    print(f"{lam:<12} bản cũ    : {len(kq['cu'])} tệp")
    for d in kq["cu"][:40]:
        print(f"               ~ {d}")
    if len(kq["cu"]) > 40:
        print(f"               … và {len(kq['cu']) - 40} tệp nữa")
    print(f"KHÔNG ĐỤNG   đang giữ  : {len(kq['dang_giu'])} tệp (việc đang làm của các làn)")
    for d in kq["dang_giu"]:
        print(f"               · {d}  ←  {kq['giu'].get(d, '?')}")
    if kq["kho_cat"]:
        print(f"\nBản cũ cất ở: {os.path.basename(kq['kho_cat'])}/  (không nằm trong git, không xoá gì)")
    if kq["dang_giu"]:
        print("\nTệp 'đang giữ' KHÔNG được kéo về — nếu một tệp trong số đó thật ra là bản cũ thì")
        print("làn giữ nó phải tự lấy bản main về rồi đặt lại phần sửa của mình lên trên.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
