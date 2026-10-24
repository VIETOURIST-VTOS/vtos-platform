# -*- coding: utf-8 -*-
"""XS-1 · «XE ĐANG ĐI» ĐỌC TỪ SHEET QUYẾT TOÁN CỦA ĐỘI XE — Chủ tịch duyệt bản xem thử 25/10/2026.

VÌ SAO CÓ TỆP NÀY
-----------------
Ô «Xe đang đi» đếm LỆNH ĐIỀU XE (`xe_hom_nay.py`), mà đo hệ thật 24/10/2026 thì bảng lệnh còn
rỗng: Đội xe sẽ lập lệnh trên VTOS khi vào vận hành chính thức. Trong lúc chờ, sổ thật của Đội xe
là Google Sheet «Quyết Toán dữ liệu xe» của anh Huân — mỗi xe một khối, mỗi chuyến một dòng có
ngày đi / ngày về. Anh Tuấn chốt 25/10/2026:

  · robot đọc sheet qua LINK CSV «Công bố lên web» (anh chọn cách này, đã được nói rõ là ai có link
    cũng xem được doanh thu từng xe);
  · lỗi trong sheet: VTOS TỰ CỘNG LẠI và báo vàng từng dòng, không chặn;
  · khi Đội xe đã lập lệnh trên VTOS thì LỆNH THAY SHEET, sheet chỉ còn để đối chiếu.

RANH GIỚI 09/9 GIỮ NGUYÊN: tệp này chỉ ĐỌC. Không ghi gì vào sheet, không nạp chuyến nào vào bảng
`fleet_trips`. Cửa nhập của con số là chính cái sheet do Đội xe gõ, và cửa dán link là tham số
`xe_sheet_csv_url` ở màn Chính sách & định mức (đổi phải có chữ ký như mọi tham số).

ĐO TRƯỚC KHI VIẾT (bản tải về của sheet, 25/10/2026)
---------------------------------------------------
11 khối xe, 55 chuyến. Những thứ bộ đọc phải chịu được — mỗi thứ đều CÓ THẬT trong bản đo:

  1. Biển số chỉ ghi ở dòng đầu khối, và ghi lẫn kiểu: «50F01783», «49829», «04622», «50H 94458».
     → khớp xe VTOS theo NĂM SỐ CUỐI của biển.
  2. Số gõ lẫn kiểu: «  600.000 », «30000», «6.375.630», «(200.000)», «30,39772727», «#DIV/0!».
     → dấu chấm là phân cách nghìn, dấu phẩy là phần thập phân, ngoặc là số âm, lỗi công thức là rỗng.
  3. Ngày gõ lẫn kiểu: «4/10/2026», «04/10/2026», «29/9/2026».
  4. Ô TỔNG SAI: Xe 4 cột Lợi nhuận bằng đúng Doanh thu ở cả bốn chuyến; bốn chuyến chưa về có
     Tổng chi cộng nhầm cả doanh thu. → TIN DÒNG, KHÔNG TIN TỔNG (cùng luật `nap_mau_quyet_toan`).
  5. Mười dòng chỉ có CTP 200.000 mà không có tên tour. → không phải chuyến; liệt kê, không tính.
  6. Km nối không liền: Xe 8 chuyến 6/10 km đầu 81.592 trong khi chuyến trước về ở 81.952.

DÒ CỘT THEO NHÃN, KHÔNG THEO CHỮ CÁI: Đội xe thêm một cột ở giữa là mọi chữ cái dịch sang một ô,
số vẫn là số và không ai thấy. Thiếu cột bắt buộc thì nói ra, không đoán.
"""
from __future__ import annotations

import csv
import io
import re
import time
import unicodedata
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import rules as R

KHOA_LINK = "xe_sheet_csv_url"
# Robot đọc lại sau ngần này giây. Sheet do người gõ tay, đổi vài lần một ngày — 15 phút là đủ
# tươi cho câu «hôm nay xe nào đang đi» mà không gọi Google mỗi lần ai mở bảng điều hành.
CHU_KY_DOC = 15 * 60
CHO_GIAY = 8
TRAN_BYTE = 2_000_000
# Chỉ nhận link CSV công bố của Google Sheet. Máy chủ KHÔNG tải một địa chỉ tuỳ ý do người dán vào
# — tham số là chữ tự do, và một máy chủ tải mọi link được dán là một cửa cho người khác gọi vào
# mạng nội bộ của chính nó.
TIEN_TO_HOP_LE = "https://docs.google.com/spreadsheets/"

# nhãn đã chuẩn hoá → tên trường. Vế trái là ĐẦU nhãn sau khi bỏ dấu, gộp khoảng trắng, chữ thường.
NHAN_COT = {
    "xe so": "khoi", "so": "bien", "lai xe": "lai_xe", "ten tour": "tour",
    "ngay di": "di", "ngay ve": "ve", "so ngay": "so_ngay", "ctp": "ctp",
    "gui xe": "gui_xe", "dau": "dau", "epass": "epass", "d. thu": "doanh_thu",
    "tong chi": "tong_chi", "loi nhuan": "loi_nhuan", "km dau": "km_dau", "km cuoi": "km_cuoi",
    "tong km": "tong_km", "sl lit": "lit", "note": "ghi_chu",
}
COT_BAT_BUOC = ("khoi", "tour", "di", "ve")
COT_CHI = ("ctp", "gui_xe", "dau", "epass")

_DEM: dict[str, tuple[float, str | None, str | None]] = {}


# ---------------------------------------------------------------------------------------------
# Đọc một ô
# ---------------------------------------------------------------------------------------------

def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", s).strip().lower()


def so(v) -> float | None:
    """Một ô số theo cách gõ Việt: «6.375.630» là sáu triệu, «30,39» là ba mươi phẩy ba chín.

    Rỗng, «-» và lỗi công thức («#DIV/0!») đều ra RỖNG — không suy thành 0 (quy ước K2): một chuyến
    chưa có số dầu là CHƯA BIẾT, không phải tốn 0 đồng dầu.
    """
    s = re.sub(r"\s+", "", str(v or ""))
    if s in ("", "-") or s.startswith("#"):
        return None
    am = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s.startswith("-"):
        am, s = True, s[1:]
    if re.fullmatch(r"\d+,\d+", s):
        s = s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s) or re.fullmatch(r"\d+", s):
        s = s.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+,\d+", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        return None
    x = float(s)
    return -x if am else x


def ngay(v) -> date | None:
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", str(v or "").strip())
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


def nam_so_cuoi(bien: str) -> str:
    """Khoá khớp biển số: năm chữ số cuối. «50H 94458», «94458», «50H-944.58» đều ra «94458»."""
    d = re.sub(r"\D", "", bien or "")
    return d[-5:] if len(d) >= 5 else ""


# ---------------------------------------------------------------------------------------------
# Đọc cả bảng
# ---------------------------------------------------------------------------------------------

def _tim_cot(rows: list[list[str]]) -> tuple[int, dict[str, int]]:
    """Dòng tiêu đề là dòng đầu tiên chứa đủ «Tên tour» và «Ngày đi»."""
    for i, r in enumerate(rows[:15]):
        nhan = [_khong_dau(c) for c in r]
        if "ten tour" in nhan and "ngay di" in nhan:
            cot: dict[str, int] = {}
            for j, n in enumerate(nhan):
                for dau_nhan, ten in NHAN_COT.items():
                    # «so» phải khớp TRỌN ô, không thì «so ngay» và «so lit» cũng thành cột biển số.
                    khop = n == dau_nhan if dau_nhan in ("so", "dau", "ctp", "note") else n.startswith(dau_nhan)
                    if khop and ten not in cot:
                        cot[ten] = j
            return i, cot
    return -1, {}


def doc_bang(noi_dung: str, nguong_km_noi: float = 50) -> dict:
    """Văn bản CSV → các chuyến + các dòng cần sửa. Hàm thuần: không gọi mạng, không đọc CSDL.

    `nguong_km_noi`: tham số `xe_lech_km_noi_chuyen` (Đội xe v1.3 – A2) — cùng một ngưỡng với luật
    nối km của nhật trình VTOS, không đặt ngưỡng thứ hai cho cùng một câu hỏi."""
    rows = list(csv.reader(io.StringIO(noi_dung)))
    i_td, cot = _tim_cot(rows)
    thieu = [c for c in COT_BAT_BUOC if c not in cot]
    if i_td < 0 or thieu:
        return {"loi": "Không thấy dòng tiêu đề có đủ cột Xe số, Tên tour, Ngày đi, Ngày về"
                       + (f" (thiếu: {', '.join(thieu)})" if i_td >= 0 else ""),
                "chuyen": [], "can_sua": [], "khoi": []}

    def o(r, ten):
        j = cot.get(ten)
        return r[j].strip() if j is not None and j < len(r) else ""

    chuyen, can_sua, khoi = [], [], []
    hien = None
    for i in range(i_td + 1, len(rows)):
        r, dong = rows[i], i + 1
        ten_khoi = o(r, "khoi")
        if re.match(r"(?i)^xe\s*\d+", ten_khoi):
            hien = {"khoi": re.sub(r"\s+", " ", ten_khoi.upper()), "bien": o(r, "bien"),
                    "lai_xe": o(r, "lai_xe"), "so_chuyen": 0}
            khoi.append(hien)
            continue
        if hien is None:
            continue
        # Dòng khối thường ghi biển rút gọn («01783»), dòng chuyến đầu ghi đủ («50F01783»): giữ bản
        # có nhiều chữ số hơn — để hiện ra cho người đọc; phép khớp chỉ dùng năm số cuối.
        if len(re.sub(r"\D", "", o(r, "bien"))) > len(re.sub(r"\D", "", hien["bien"])):
            hien["bien"] = o(r, "bien")
        if o(r, "lai_xe") and not hien["lai_xe"]:
            hien["lai_xe"] = o(r, "lai_xe")
        tour = o(r, "tour")
        if not tour:
            if any(so(o(r, c)) for c in COT_CHI + ("doanh_thu",)):
                can_sua.append({"loai": "dong_khong_tour", "khoi": hien["khoi"], "dong": dong,
                                "noi_dung": "Có số tiền mà không có tên tour — VTOS bỏ qua dòng này."})
            continue
        t = {"khoi": hien["khoi"], "dong": dong, "tour": tour,
             "di": ngay(o(r, "di")), "ve": ngay(o(r, "ve")),
             "doanh_thu": so(o(r, "doanh_thu")), "ghi_chu": o(r, "ghi_chu")}
        for c in COT_CHI + ("tong_chi", "loi_nhuan", "km_dau", "km_cuoi", "tong_km", "lit"):
            t[c] = so(o(r, c))
        hien["so_chuyen"] += 1
        # TIN DÒNG, KHÔNG TIN TỔNG.
        t["chi"] = sum(t[c] or 0 for c in COT_CHI)
        t["lai"] = None if t["doanh_thu"] is None else t["doanh_thu"] - t["chi"]
        chuyen.append(t)
        _kiem_dong(t, can_sua)

    _kiem_noi_km(chuyen, can_sua, nguong_km_noi)
    _kiem_chong_ngay(chuyen, can_sua)
    for k in khoi:
        k["khoa"] = nam_so_cuoi(k["bien"])
    return {"loi": None, "chuyen": chuyen, "can_sua": can_sua, "khoi": khoi}


def _vnd(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def _kiem_dong(t: dict, can_sua: list) -> None:
    def ghi(loai, noi_dung):
        can_sua.append({"loai": loai, "khoi": t["khoi"], "dong": t["dong"], "tour": t["tour"],
                        "di": t["di"].isoformat() if t["di"] else None, "noi_dung": noi_dung})
    if t["di"] is None or t["ve"] is None:
        ghi("thieu_ngay", "Thiếu hoặc gõ sai ngày đi / ngày về — chuyến này không đếm được vào «đang đi».")
    elif t["ve"] < t["di"]:
        ghi("ve_truoc_di", "Ngày về trước ngày đi.")
    if t["tong_chi"] is not None and abs(t["tong_chi"] - t["chi"]) > 1:
        ghi("tong_chi", f"Ô Tổng chi ghi {_vnd(t['tong_chi'])}, cộng CTP + gửi xe + dầu + epass ra "
                        f"{_vnd(t['chi'])}.")
    if t["loi_nhuan"] is not None and t["lai"] is not None and abs(t["loi_nhuan"] - t["lai"]) > 1:
        ghi("loi_nhuan", f"Ô Lợi nhuận ghi {_vnd(t['loi_nhuan'])}, doanh thu trừ chi ra {_vnd(t['lai'])}.")
    if t["km_dau"] is not None and t["km_cuoi"] is not None and t["tong_km"] is not None \
            and abs(t["km_cuoi"] - t["km_dau"] - t["tong_km"]) > 0.5:
        ghi("tong_km", f"Ô Tổng km ghi {_vnd(t['tong_km'])}, km cuối trừ km đầu ra "
                       f"{_vnd(t['km_cuoi'] - t['km_dau'])}.")


def _kiem_noi_km(chuyen: list, can_sua: list, nguong: float) -> None:
    """Km đầu của một chuyến phải bằng km cuối của chuyến liền trước CÙNG XE (theo thứ tự dòng)."""
    truoc: dict[str, float] = {}
    for t in chuyen:
        k = t["khoi"]
        if t["km_dau"] is not None and k in truoc and abs(truoc[k] - t["km_dau"]) > nguong:
            can_sua.append({"loai": "km_noi", "khoi": k, "dong": t["dong"], "tour": t["tour"],
                            "di": t["di"].isoformat() if t["di"] else None,
                            "noi_dung": f"Km đầu {_vnd(t['km_dau'])}, nhưng chuyến trước về ở "
                                        f"{_vnd(truoc[k])}."})
        if t["km_cuoi"] is not None:
            truoc[k] = t["km_cuoi"]


def _kiem_chong_ngay(chuyen: list, can_sua: list) -> None:
    """Một xe hai chuyến chồng ngày (nối đuôi cùng ngày thì không tính là chồng)."""
    theo_xe: dict[str, list] = {}
    for t in chuyen:
        if t["di"] and t["ve"] and t["ve"] >= t["di"]:
            theo_xe.setdefault(t["khoi"], []).append(t)
    for k, ds in theo_xe.items():
        ds = sorted(ds, key=lambda x: x["di"])
        for a, b in zip(ds, ds[1:]):
            if b["di"] < a["ve"]:
                can_sua.append({"loai": "chong_ngay", "khoi": k, "dong": b["dong"], "tour": b["tour"],
                                "di": b["di"].isoformat(),
                                "noi_dung": f"Chồng ngày với chuyến «{a['tour']}» "
                                            f"{a['di']:%d/%m}–{a['ve']:%d/%m}."})


# ---------------------------------------------------------------------------------------------
# Hôm nay
# ---------------------------------------------------------------------------------------------

def _trang_thai(t: dict, hom_nay: date) -> str:
    if t["di"] == hom_nay and t["ve"] == hom_nay:
        return "Đi trong ngày"
    if t["di"] == hom_nay:
        return "Khởi hành hôm nay"
    if t["ve"] == hom_nay:
        return "Về hôm nay"
    return "Đang trên đường"


def hom_nay(bang: dict, hom_nay: date, xe_vtos: dict[str, str]) -> dict:
    """Xe đang đi ĐÚNG ngày ấy: ngày đi ≤ hôm nay ≤ ngày về. Đếm XE, không đếm chuyến.

    `xe_vtos`: năm số cuối → biển số đầy đủ của các xe ĐIỀU ĐƯỢC trong VTOS. Khối nào của sheet không
    khớp xe điều được thì vẫn hiện trong danh sách nhưng có cờ, và được đếm riêng ở `khong_khop` —
    mẫu số «trên N xe điều được» là của VTOS, không phải của sheet.
    """
    khoi = {k["khoi"]: k for k in bang["khoi"]}
    ds, xe_di = [], {}
    for t in bang["chuyen"]:
        if t["di"] and t["ve"] and t["di"] <= hom_nay <= t["ve"]:
            k = khoi.get(t["khoi"], {})
            bien = xe_vtos.get(k.get("khoa", ""))
            ds.append({"khoi": t["khoi"], "bien": bien or k.get("bien", ""), "khop_vtos": bool(bien),
                       "lai_xe": k.get("lai_xe", ""), "tour": t["tour"],
                       "di": t["di"].isoformat(), "ve": t["ve"].isoformat(),
                       "trang_thai": _trang_thai(t, hom_nay)})
            xe_di[t["khoi"]] = bool(bien)
    dang_di = sum(1 for v in xe_di.values() if v)
    nam_bai = [{"khoi": k["khoi"], "bien": xe_vtos.get(k["khoa"]) or k["bien"]}
               for k in bang["khoi"] if k["khoi"] not in xe_di and k["so_chuyen"]]
    return {"dang_di": dang_di, "khong_khop": sum(1 for v in xe_di.values() if not v),
            "danh_sach": ds, "nam_bai": nam_bai}


# ---------------------------------------------------------------------------------------------
# Mạng + CSDL
# ---------------------------------------------------------------------------------------------

def link(db: Session) -> str:
    try:
        return (R.get_param_text(db, KHOA_LINK) or "").strip()
    except KeyError:
        return ""


def link_hop_le(url: str) -> bool:
    return url.startswith(TIEN_TO_HOP_LE) and "output=csv" in url


def _tai(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "VTOS-robot-doi-xe"})
    with urllib.request.urlopen(req, timeout=CHO_GIAY) as r:  # noqa: S310 — đã chặn tiền tố ở trên
        b = r.read(TRAN_BYTE + 1)
    if len(b) > TRAN_BYTE:
        raise ValueError("Tệp CSV lớn quá 2 MB — không phải sheet quyết toán xe.")
    return b.decode("utf-8-sig")


def _gio_vn(ts: float) -> str:
    return datetime.fromtimestamp(ts, ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%H:%M %d/%m/%Y")


def doc(url: str, doc_lai: bool = False, tai=_tai) -> dict:
    """Văn bản CSV, có đệm `CHU_KY_DOC` giây. Tải hỏng thì GIỮ bản cũ và nói ra là bản cũ."""
    now = time.time()
    hit = _DEM.get(url)
    if hit and not doc_lai and now - hit[0] < CHU_KY_DOC and hit[1] is not None:
        return {"noi_dung": hit[1], "doc_luc": _gio_vn(hit[0]), "loi_tai": None, "ban_cu": False}
    try:
        nd = tai(url)
        _DEM[url] = (now, nd, None)
        return {"noi_dung": nd, "doc_luc": _gio_vn(now), "loi_tai": None, "ban_cu": False}
    except Exception as ex:  # mạng, 404, link đã ngừng công bố…
        loi = f"Không tải được sheet: {str(ex)[:160]}"
        if hit and hit[1] is not None:
            return {"noi_dung": hit[1], "doc_luc": _gio_vn(hit[0]), "loi_tai": loi, "ban_cu": True}
        return {"noi_dung": None, "doc_luc": None, "loi_tai": loi, "ban_cu": False}


def _xe_dieu_duoc(db: Session) -> dict[str, str]:
    """Năm số cuối → biển số, của xe điều được. Cùng điều kiện với `xe_hom_nay._xe_dieu_duoc`."""
    from app.models.hr import Vehicle
    from app.services import xe_hom_nay as XE
    q = select(Vehicle.plate).where(Vehicle.active.is_(True),
                                    Vehicle.lifecycle.in_(XE.VONG_DOI_DIEU_DUOC),
                                    Vehicle.op_right.not_in(XE.QUYEN_KHONG_DIEU_DUOC))
    return {nam_so_cuoi(p): p for p in db.execute(q).scalars() if nam_so_cuoi(p)}


def bao_cao(db: Session, hom_nay_: date, doc_lai: bool = False, tai=_tai) -> dict:
    """Toàn bộ cho màn chi tiết: link có chưa, đọc lúc nào, xe hôm nay, dòng cần sửa."""
    url = link(db)
    if not url:
        return {"co_link": False, "ghi_chu": "Chưa dán link CSV của sheet Đội xe "
                f"(tham số «{KHOA_LINK}» ở màn Chính sách & định mức)."}
    if not link_hop_le(url):
        return {"co_link": True, "loi": "Link không phải link CSV «Công bố lên web» của Google Sheet "
                "(phải bắt đầu bằng https://docs.google.com/spreadsheets/ và có output=csv)."}
    d = doc(url, doc_lai=doc_lai, tai=tai)
    if d["noi_dung"] is None:
        return {"co_link": True, "loi": d["loi_tai"]}
    try:
        nguong = R.get_param(db, "xe_lech_km_noi_chuyen")
    except KeyError:
        nguong = 50
    bang = doc_bang(d["noi_dung"], nguong)
    if bang["loi"]:
        return {"co_link": True, "loi": bang["loi"], "doc_luc": d["doc_luc"]}
    xe = _xe_dieu_duoc(db)
    hn = hom_nay(bang, hom_nay_, xe)
    return {"co_link": True, "loi": None, "doc_luc": d["doc_luc"], "loi_tai": d["loi_tai"],
            "ban_cu": d["ban_cu"], "ngay": hom_nay_.isoformat(), "dieu_duoc": len(xe),
            "so_xe_sheet": len(bang["khoi"]), "so_chuyen": len(bang["chuyen"]),
            "dang_di": hn["dang_di"], "khong_khop": hn["khong_khop"],
            "o_bai": max(0, len(xe) - hn["dang_di"]),
            "danh_sach": hn["danh_sach"], "nam_bai": hn["nam_bai"], "can_sua": bang["can_sua"]}


def tom_tat(db: Session, hom_nay_: date) -> dict | None:
    """Cho bảng điều hành: chỉ các con số, không kèm danh sách. Chưa có link thì None."""
    b = bao_cao(db, hom_nay_)
    if not b.get("co_link"):
        return None
    if b.get("loi"):
        return {"loi": b["loi"], "doc_luc": b.get("doc_luc")}
    return {k: b[k] for k in ("doc_luc", "ban_cu", "dieu_duoc", "dang_di", "khong_khop", "o_bai")} | {
        "so_can_sua": len(b["can_sua"]), "loi": None}
