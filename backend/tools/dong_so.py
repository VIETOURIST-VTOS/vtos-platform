# -*- coding: utf-8 -*-
"""ĐỢT DỌN-6 — đóng dòng sổ giữ chỗ ngay khi lần gộp vào main hạ cánh.

VÌ SAO CÓ TỆP NÀY, ĐO ĐƯỢC CHỨ KHÔNG SUY

Đo trên main `06369d2` ngày 20/10/2026: sổ có 136 dòng, trong đó **6 trên 7** dòng `đang làm`
là dòng ĐÃ CHẾT — việc đã nằm trên main rồi, chỉ là chưa ai đóng dòng. Nghĩa là sổ nói sai sáu
lần trên bảy. Ai đọc nó để biết "có ai đang đụng tệp này không" thì phần lớn câu trả lời là tin cũ.

Giá đã trả, đếm trong 36 giờ ngày 16–17/10: Đợt DỌN-5 đóng hộ 20 dòng, TM-1 đóng hộ 4, R3b đóng
hộ 3 — 27 dòng chết phải nhờ làn đi sau dọn, mỗi lần là một bước vá, một phép chứng và một vòng CI.

GỐC CỦA NÓ: dòng sổ được GHI lúc làn bắt đầu, nhưng thời điểm duy nhất đúng để ĐÓNG nó là lúc PR
gộp — mà lúc ấy mọi script của làn đã chạy xong từ lâu, việc gộp diễn ra trên GitHub. Không có gì
trong hệ thống gắn vào sự kiện gộp. Trạng thái dòng là một bản sao chép tay của một sự thật nằm
chỗ khác, và bản sao chép tay thì trôi.

LUẬT KHỚP, VÀ VÌ SAO NÓ CHẶT

Tên nhánh cắt theo dấu gạch, bỏ dấu tiếng Việt, ghép các cửa sổ 1–2–3 đoạn liền nhau, rồi so
BẰNG ĐÚNG với mã dòng. KHÔNG so kiểu "chứa": mã `R1` nằm trong chuỗi `r10`, nên một nhánh của
R-10 sẽ đóng nhầm dòng của R-1.

Luật được viết để TRƯỢT AN TOÀN. Trượt thì dòng ở lại, người đọc thấy và đóng tay. Đóng nhầm thì
một làn đang sống mất lớp bảo vệ mà không ai biết. Nên mọi chỗ còn ngờ đều chọn trượt.

NĂM CHỐT
  1. Chỉ chạm `docs/dang-lam/*.md`, và chỉ đổi đúng ô trạng thái.
  2. Không đóng quá ba dòng một lần — nhiều hơn nghĩa là luật khớp đã hỏng.
  3. Mã phải là duy nhất trong các dòng `đang làm`. Sổ CÓ mã trùng (`qt1`, `dl` — đo 20/10), nên
     chốt này không phải phòng xa.
  4. Lần gộp không đụng tệp nào ngoài `docs/dang-lam/` thì bỏ qua: đó là nhánh dọn sổ, không phải
     nhánh làm việc. HẸP LẠI ở đợt KS-16 (21/10/2026): một dòng mà MỌI tệp khai đều nằm trong sổ
     thì việc của nó chính là quyển sổ, nên lần gộp ấy ĐƯỢC đóng đúng dòng ấy — và chỉ dòng ấy.
     Không có khe này thì mọi vòng dọn sổ đều tự để lại rác của chính mình (đo trên lần gộp #413).
  5. Bỏ qua commit của chính việc này (làm ở tầng workflow).

ĐÃ CHẠY THỬ trên 185 lần gộp thật của main: đóng đúng 94, trượt 88, ĐÓNG NHẦM 0.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
import unicodedata

DANG_LAM = "| đang làm |"
XONG = "| xong |"
THU_MUC_SO = "docs/dang-lam"
TOI_DA = 3


def chuan(s: str) -> str:
    """Bỏ dấu tiếng Việt, bỏ mọi ký tự không phải chữ-số, về chữ thường.

    `DỌN-5` → `don5`. Hai mã chỉ khác nhau ở dấu hoặc dấu gạch là MỘT mã trong mắt hàm này —
    đúng ý: tên nhánh viết không dấu, mã dòng viết có dấu.
    """
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def cua_so(nhanh: str) -> set[str]:
    """Các cửa sổ 1–2–3 đoạn liền nhau của tên nhánh, đã chuẩn hoá.

    `pq-hd-dg3-dong-y…` → {`pq`, `hd`, `dg3`, …, `pqhd`, `hddg3`, …, `pqhddg3`, …}
    Ba đoạn là đủ cho mọi mã đang có (dài nhất là `E13-B03` → hai đoạn trong tên nhánh).
    """
    doan = [x for x in (chuan(y) for y in nhanh.split("-")) if x]
    ra: set[str] = set()
    for n in (1, 2, 3):
        for i in range(len(doan) - n + 1):
            ra.add("".join(doan[i : i + n]))
    return ra


def ma_cua_dong(dong: str) -> str:
    """Mã đợt, lấy từ đầu cột mô tả. Không có mã đọc được thì trả rỗng → dòng ấy không bao giờ khớp.

    CẮT THEO DẤU GẠCH DÀI CÓ KHOẢNG TRẮNG HAI BÊN, không theo bảng chữ cái. Bản đầu dùng
    `[A-ZĐ][A-Za-zĐ0-9-]*` và vì thế ĐỌC TRƯỢT mọi mã có chữ tiếng Việt: `DỌN-5` có chữ `Ọ`
    không nằm trong bảng ấy. Trượt kiểu này im lặng — dòng chỉ đơn giản không bao giờ được xét,
    và cả phép đo lẫn phép thử đều không kêu. Phát hiện 20/10/2026 khi phép thử số 2 đỏ.

    Mã không bao giờ chứa khoảng trắng; mô tả thì luôn có. Đó là chỗ phân biệt.
    """
    o = dong.split("|")
    if len(o) < 6:
        return ""
    t = o[2].strip().lstrip("*").strip()
    dau = re.split(r"\s[—–-]\s", t, maxsplit=1)[0].strip()
    if not dau or " " in dau or len(dau) > 20 or not re.search(r"[A-Za-zĐ]", dau):
        return ""
    return dau


def tep_khai(dong: str) -> list[str]:
    """Các tệp dòng ấy khai ở cột `Tệp sẽ đụng`. Đọc không được thì trả rỗng.

    Rỗng nghĩa là dòng KHÔNG BAO GIỜ được đóng bởi nhánh chỉ dọn sổ — trượt an toàn.
    """
    o = dong.split("|")
    if len(o) < 6:
        return []
    return [t.strip() for t in o[3].split(",") if t.strip()]


def chi_khai_tep_trong_so(tep: list[str]) -> bool:
    """Dòng mà MỌI tệp khai đều nằm trong `docs/dang-lam/` — tức việc của nó CHÍNH LÀ quyển sổ."""
    return bool(tep) and all(t.startswith(THU_MUC_SO + "/") for t in tep)


def doc_dong_dang_lam(noi_dung: str) -> list[dict]:
    ra = []
    for i, l in enumerate(noi_dung.splitlines(), 1):
        if l.rstrip().endswith(DANG_LAM):
            ma = ma_cua_dong(l)
            if ma:
                ra.append({
                    "dong": i,
                    "ma": ma,
                    "ma_chuan": chuan(ma),
                    "tep": tep_khai(l),
                    "noi_dung": l,
                })
    return ra


def chon(dong_dang_lam: list[dict], nhanh: str, doi_tep: list[str]) -> tuple[list[dict], str]:
    """Trả về (các dòng được đóng, lý do nếu không đóng gì).

    Đây là toàn bộ phần quyết định. Nó KHÔNG đọc đĩa, KHÔNG gọi git — nên phép thử gọi thẳng được.
    """
    chi_don_so = not [t for t in doi_tep if not t.startswith(THU_MUC_SO + "/")]

    cs = cua_so(nhanh)
    khop = [d for d in dong_dang_lam if d["ma_chuan"] in cs]
    if not khop:
        return [], f"không mã nào của sổ khớp tên nhánh `{nhanh}`"

    if chi_don_so:
        # CHỐT 4 (hẹp lại ở đợt KS-16, 21/10/2026). Bản đầu BỎ QUA HẲN mọi lần gộp chỉ đụng sổ.
        # Đo được trên lần gộp thật #413 ngày 21/10: vòng KS-15 là một vòng DỌN SỔ, nên chính
        # dòng KS-15 không bao giờ được đóng — một vòng dọn sổ luôn tự để lại rác của mình.
        #
        # Chỗ chốt 4 bảo vệ là: nhánh chỉ sửa sổ thì KHÔNG được đóng dòng của việc THẬT, vì nó
        # chưa làm gì cho việc ấy. Chỗ ấy giữ nguyên. Chỉ nới đúng một khe: dòng mà MỌI tệp khai
        # đều nằm trong sổ thì việc của nó CHÍNH LÀ quyển sổ — lần gộp này đã làm xong việc ấy.
        # Thêm một điều kiện nữa để khỏi đóng vu vơ: lần gộp phải thật sự đụng một tệp nó khai.
        da_doi = set(doi_tep)
        khop = [
            d for d in khop
            if chi_khai_tep_trong_so(d["tep"]) and any(t in da_doi for t in d["tep"])
        ]
        if not khop:
            return [], (
                "lần gộp không đụng tệp nào ngoài sổ — nhánh dọn sổ, và không dòng nào vừa khớp "
                "tên nhánh vừa chỉ khai tệp trong sổ, bỏ qua"
            )

    dem: dict[str, int] = {}
    for d in dong_dang_lam:
        dem[d["ma_chuan"]] = dem.get(d["ma_chuan"], 0) + 1
    trung = sorted({d["ma"] for d in khop if dem[d["ma_chuan"]] > 1})
    if trung:
        return [], f"mã {trung} xuất hiện ở nhiều hơn một dòng `đang làm` — để người đi xem"

    if len(khop) > TOI_DA:
        return [], (f"khớp {len(khop)} dòng, quá {TOI_DA} — luật khớp đã hỏng, không đóng gì")

    return khop, ""


def dong_mot_dong(dong: str) -> str:
    """Đổi ĐÚNG ô trạng thái. Mọi ký tự khác giữ nguyên."""
    s = dong.rstrip()
    if not s.endswith(DANG_LAM):
        raise ValueError("dòng không ở trạng thái `đang làm`")
    return s[: -len(DANG_LAM)] + XONG


def chay(goc: pathlib.Path, nhanh: str, doi_tep: list[str], that: bool) -> int:
    thu_muc = goc / THU_MUC_SO
    tep_so = sorted(p for p in thu_muc.glob("*.md"))
    tat_ca: list[tuple[pathlib.Path, dict]] = []
    for p in tep_so:
        for d in doc_dong_dang_lam(p.read_text(encoding="utf-8")):
            tat_ca.append((p, d))

    chon_duoc, ly_do = chon([d for _, d in tat_ca], nhanh, doi_tep)
    if not chon_duoc:
        print(f"  không đóng dòng nào: {ly_do}")
        return 0

    xong_roi = 0
    for p in tep_so:
        s = p.read_text(encoding="utf-8")
        moi = s
        for d in chon_duoc:
            if d["noi_dung"] in moi:
                moi = moi.replace(d["noi_dung"], dong_mot_dong(d["noi_dung"]), 1)
                print(f"  đóng {d['ma']}  ({p.name}:{d['dong']})")
                xong_roi += 1
        if moi != s and that:
            p.write_text(moi, encoding="utf-8", newline="\n")
    if not that:
        print("  (chạy thử — không ghi)")
    return xong_roi


def main() -> int:
    b = argparse.ArgumentParser()
    b.add_argument("--goc", default=".")
    b.add_argument("--nhanh", required=True)
    b.add_argument("--doi-tep", default="", help="danh sách tệp lần gộp đã đổi, cách nhau bằng xuống dòng")
    b.add_argument("--that", action="store_true", help="ghi thật; không có cờ này thì chỉ in")
    a = b.parse_args()
    doi = [x.strip() for x in a.doi_tep.splitlines() if x.strip()]
    n = chay(pathlib.Path(a.goc).resolve(), a.nhanh, doi, a.that)
    print(f"ĐÓNG {n} DÒNG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
