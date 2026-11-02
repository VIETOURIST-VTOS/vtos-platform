"""TR-1 · Tour kiểu Agoda/Klook trên kh.vietourist.vn/tours + nối nội dung web + đặt tour online + email invoice.

Chủ tịch duyệt bản xem thử 01/11/2026 (v4: tab Trong nước | Nước ngoài · loại Ghép / Đoàn riêng · chủ đề Wellness ·
phương tiện xe / máy bay / tàu hỏa / du thuyền · giữ chỗ cọc HOẶC trả toàn bộ online · email xác nhận + invoice PDF)
và 02/11/2026: nút «Đặt tour» CHỈ nằm trên kh.vietourist.vn/tours; ảnh / chương trình / bảng giá đọc thẳng từ trang
tour trên vietourist.com.vn — không ai gõ lại.

THUẬT TOÁN (mỗi mục một hàm, phép thử gọi thẳng):
  · Gộp chuyến theo SẢN PHẨM (`the_san_pham`): một thẻ = một sản phẩm; «giá từ» = giá hiệu lực thấp nhất trong các
    chuyến còn đủ chỗ cho số khách đang tìm; giá hiệu lực = giá KM khi 0 < KM < giá thường.
  · Lịch trình (`lich_trinh`): chương trình CỦA CHUYẾN (từng ngày) → lịch trình đọc từ web → chương trình sản phẩm
    có mốc «Ngày 1..N» LIÊN TIẾP → nguyên văn. Không đoán ranh giới ngày khi không có mốc rõ ràng.
  · Tiền (`tinh`): NL × giá hiệu lực + TE × giá trẻ em (trống = giá NL) + em bé × giá em bé (trống = 0). Cọc =
    tổng × % cọc của sản phẩm, làm tròn LÊN tới 1.000 đ. Hạn trả phần còn lại = ngày khởi hành − «đóng sổ trước»
    ngày, 17:00 (đúng như hạn hủy chỗ của booking). Hạn ấy đã qua thì chỉ cho trả toàn bộ.
  · Mở thanh toán = công tắc chung (Chủ tịch / TGĐ) VÀ công tắc của sản phẩm (TP Điều hành / TP-GĐ KD). Chưa mở thì
    khách vẫn xem, chọn, điền — nút cuối thành «Gửi yêu cầu giữ chỗ» (luồng yêu cầu sẵn có), máy chủ chặn 409.
  · Đọc web (`doc_tour_web`): CHỈ https://(www.)vietourist.com.vn/, không theo chuyển hướng ra ngoài, ≤ 2 MB, 15 giây.
    Đọc hỏng thì GIỮ bản cũ và ghi lỗi — cổng không bao giờ trắng trang vì web chính chậm.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.core import Alert, Booking, Product, ServiceRequest, Tour, User
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.tour_online import CACH_TRA_TOUR, PHUONG_TIEN_TOUR, DonTourOnline, ThanhToanTourOnline
from app.services import rules as R

# ── Ma trận quản lý (khai ở chữ ký API bằng require_roles; hằng số dùng chung ở đây) ──────────────────────────
TOAN_QUYEN = ("chutich", "tgd")
VAI_XEM = TOAN_QUYEN + ("bks", "robot_ks", "nv_dh", "tp_dh", "nv_kd", "tn_kd", "tp_kd", "gd_kd", "sales_admin", "nv_mkt", "ptgd_mkt", "ketoan")
VAI_SUA_CONG = TOAN_QUYEN + ("nv_mkt", "ptgd_mkt", "nv_dh", "tp_dh")        # hồ sơ cổng, đọc lại từ web
VAI_GHEP = TOAN_QUYEN + ("tp_dh", "tp_kd", "gd_kd")                          # xác nhận link web, mở thanh toán sản phẩm
VAI_TT_CHUNG = TOAN_QUYEN                                                    # công tắc chung
VAI_XEM_DON = TOAN_QUYEN + ("bks", "robot_ks", "nv_kd", "tn_kd", "tp_kd", "gd_kd", "sales_admin", "ketoan", "nv_dh", "tp_dh")
VAI_VAT = TOAN_QUYEN + ("ketoan",)                                           # yêu cầu hóa đơn công ty
MA_TRAN = {
    "Xem màn «Tour trên cổng khách»": VAI_XEM,
    "Sửa hồ sơ cổng (điểm đến, nổi bật, wellness, phương tiện) · đọc lại từ web": VAI_SUA_CONG,
    "Xác nhận ghép link web ↔ sản phẩm · mở / đóng thanh toán của sản phẩm": VAI_GHEP,
    "Mở / đóng thanh toán trực tuyến chung": VAI_TT_CHUNG,
    "Xem đơn đặt tour online": VAI_XEM_DON,
    "Đánh dấu đã xuất hóa đơn GTGT công ty": VAI_VAT,
}

KHOA_TT = "mo_thanh_toan_tour"
GIU_PHUT = 15
DON_CHO_TOI_DA_NGAY = 3
WEB_HOST = ("vietourist.com.vn", "www.vietourist.com.vn")
WEB_DS = ("https://www.vietourist.com.vn/vn/tour/tour-trong-nuoc", "https://www.vietourist.com.vn/vn/tour/tour-nuoc-ngoai")
WEB_TOI_DA_BYTE = 2 * 1024 * 1024
WEB_HAN_GIAY = 15
WEB_CU_GIO = 24
LOAI_TOUR = {"ghep": "Tour ghép", "doan": "Tour đoàn riêng"}


class LoiTour(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _co(u: User, vai: tuple) -> bool:
    return u.role in vai


def _quyen(u: User, vai: tuple, msg: str = "Không có quyền") -> None:
    if not _co(u, vai):
        raise LoiTour(msg, 403)


def _khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _vnd(x) -> str:
    return f"{int(round(float(x or 0))):,}".replace(",", ".")


def _hom_nay() -> date:
    from app.services import cong_khach as K
    return K._hom_nay()


# ══ 1 · ĐỌC NỘI DUNG WEB vietourist.com.vn ═══════════════════════════════════════════════════════════════════════

def kiem_link(url: str) -> str:
    """Chỉ nhận trang của chính Vietourist, qua https. Chặn mọi host khác (kể cả IP, cổng lạ, @, tên miền giả)."""
    u = (url or "").strip()
    try:
        p = urlparse(u)
    except ValueError:
        raise LoiTour("Link không hợp lệ")
    if p.scheme != "https" or (p.hostname or "").lower() not in WEB_HOST or p.port not in (None, 443) or p.username or p.password:
        raise LoiTour("Chỉ nhận link https://www.vietourist.com.vn/…")
    return u


def ma_hoa_link(url: str) -> str:
    """TR-1c: đường dẫn web có dấu cách / chữ có dấu («tour- bao-loc-963.html», «…-2N1Đ-952.html») → mã hóa %XX như trình
    duyệt; phần đã mã hóa sẵn (%20, %C4%90) giữ nguyên."""
    from urllib.parse import quote, urlsplit, urlunsplit
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, quote(p.path, safe="/%:@-._~!$&'()*+,;="),
                       quote(p.query, safe="=&%:@-._~!$'()*+,;/?"), p.fragment))


def _tai_that(url: str) -> bytes:
    import urllib.request

    class _KhongRaNgoai(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):   # noqa: D401
            kiem_link(urljoin(req.full_url, newurl))                       # chuyển hướng ra ngoài → LoiTour
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    op = urllib.request.build_opener(_KhongRaNgoai())
    req = urllib.request.Request(ma_hoa_link(kiem_link(url)), headers={"User-Agent": "VTOS/1.0 (+https://kh.vietourist.vn)", "Accept-Language": "vi"})
    with op.open(req, timeout=WEB_HAN_GIAY) as r:
        kiem_link(r.geturl())
        data = r.read(WEB_TOI_DA_BYTE + 1)
    if len(data) > WEB_TOI_DA_BYTE:
        raise LoiTour("Trang web quá lớn (> 2 MB) — không đọc")
    return data


FETCH = _tai_that      # phép thử thay bằng hàm trả HTML mẫu


class _Nut:
    __slots__ = ("tag", "attrs", "con", "cha", "chu")

    def __init__(self, tag: str, attrs: dict, cha: "_Nut | None"):
        self.tag, self.attrs, self.con, self.cha, self.chu = tag, attrs, [], cha, []


_RONG = {"br", "img", "hr", "meta", "link", "input", "source", "wbr", "area", "base", "col", "embed", "param", "track"}
_KHOI = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "div", "td", "th", "section", "article", "dt", "dd", "blockquote"}


class _Cay(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.goc = _Nut("#goc", {}, None)
        self.cur = self.goc

    def handle_starttag(self, tag, attrs):
        n = _Nut(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.con.append(n)
        if tag not in _RONG:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.con.append(_Nut(tag, {k: (v or "") for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.cha
        if n is not None and n.cha is not None:
            self.cur = n.cha

    def handle_data(self, data):
        if self.cur.tag in ("script", "style"):
            return
        self.cur.con.append(data)


def _chu(n) -> str:
    if isinstance(n, str):
        return n
    if n.tag in ("script", "style"):
        return ""
    if n.tag == "br":
        return "\n"
    s = "".join(_chu(c) for c in n.con)
    return ("\n" + s + "\n") if n.tag in _KHOI else s


_KHONG_RONG = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")   # TR-1c: web chèn ký tự rộng 0 trước «NGÀY 1:»


def _sach(s: str) -> str:
    return re.sub(r"[ \t\u00a0]+", " ", _KHONG_RONG.sub("", s or "")).strip()


def _duyet(n):
    if isinstance(n, str):
        return
    yield n
    for c in n.con:
        yield from _duyet(c)


def _lop(n, ten: str) -> bool:
    return not isinstance(n, str) and ten in (n.attrs.get("class") or "").split()


def _trong(n: _Nut, dk) -> bool:
    """n hoặc một tổ tiên của n thỏa dk."""
    c = n
    while c is not None:
        if dk(c):
            return True
        c = c.cha
    return False


def _tim(nut: list, dk):
    return next((n for n in nut if dk(n)), None)


def _anh(n: _Nut, url: str) -> str:
    src = n.attrs.get("data-src") or n.attrs.get("data-original") or n.attrs.get("src") or ""
    if not src or src.startswith("data:"):
        return ""
    a = urljoin(url, src.strip())
    p = urlparse(a)
    if p.scheme != "https" or (p.hostname or "") not in WEB_HOST:
        return ""
    return a


def _anh_tour_khac(n: _Nut) -> bool:
    """Ảnh KHÔNG thuộc tour này: băng chuyền tour liên quan (.owl-item / .item-product), tiện ích chấm sao (.kksr-*)."""
    if any(k.startswith("kksr") for k in (n.attrs.get("class") or "").split()) or "kksr" in (n.attrs.get("src") or ""):
        return True
    return _trong(n, lambda c: _lop(c, "owl-item") or _lop(c, "item-product")
                  or any(k.startswith("kksr") for k in (c.attrs.get("class") or "").split()))


def _so_tien(s: str) -> int | None:
    m = re.search(r"(\d{1,3}(?:[.,]\d{3})+|\d{4,})", s or "")
    if not m:
        return None
    return int(re.sub(r"[.,]", "", m.group(1)))


_NGAY_RE = re.compile(r"^\s*[-•·*]?\s*NG[ÀAÁẢÃẠ]Y\s*0?(\d{1,2})\b\s*[:.\-–—]?\s*(.*)$", re.IGNORECASE)
_PT_WEB = (("may bay", "may_bay"), ("du thuyen", "du_thuyen"), ("tau", "tau_hoa"), ("o to", "xe"), ("xe", "xe"))


def ma_phuong_tien(chu: str) -> list[str]:
    """«Ô tô» → xe, «Máy bay» → may_bay, «Tàu» → tau_hoa, «Du thuyền» → du_thuyen (theo bảng info-product)."""
    kd, ra = _khong_dau(chu), []
    for k, ma in _PT_WEB:
        if re.search(rf"\b{k}\b", kd) and ma not in ra:
            ra.append(ma)
            kd = re.sub(rf"\b{k}\b", " ", kd)
    return ra


def _khoi(goc: _Nut, url: str) -> list[tuple[str, list[str]]]:
    """Các khối chữ lá theo thứ tự (p, li, td…), mỗi khối kèm ảnh nằm trong nó."""
    ra: list[tuple[str, list[str]]] = []

    def _gom(n):
        if isinstance(n, str) or n.tag in ("script", "style"):
            return
        co_khoi_con = any(not isinstance(c, str) and c.tag in _KHOI for c in n.con)
        if n.tag in _KHOI and not co_khoi_con:
            t = _sach(_chu(n).replace("\n", " "))
            imgs = [a for a in (_anh(x, url) for x in _duyet(n) if x.tag == "img" and not _anh_tour_khac(x)) if a]
            if t or imgs:
                ra.append((t, imgs))
            return
        for c in n.con:
            if isinstance(c, str):
                t = _sach(c)
                if t and n.tag not in ("a", "span", "strong", "b", "em", "i", "u"):
                    ra.append((t, []))
            else:
                _gom(c)

    _gom(goc)
    return ra


def _la_tieu_de_hoa(t: str) -> bool:
    chu = re.sub(r"[^A-Za-zÀ-ỹ]", "", t)
    return 3 <= len(chu) and t == t.upper() and len(t) < 100


def phan_tich(html: str, url: str) -> dict:
    """HTML trang tour vietourist.com.vn → nội dung cho cổng (khớp cấu trúc trang thật, Điều phối đo DOM 02/11/2026):
      · ảnh       : .album-gallery (ảnh chính + .thumb-tour; ảnh /thumbnail/ đổi sang đường dẫn đầy đủ, trùng tên tệp thì
                    giữ một). BỎ băng chuyền tour liên quan (.owl-item .item-product .image img) và ảnh chấm sao (.kksr-*).
      · thông tin : table.info-product «Khởi hành : …», «Thời gian : …», «Phương tiện : …», «Giá : …» (bỏ dòng «Đặt tour»).
      · #tabs-detail «Chương trình tour»: đoạn bắt đầu «NGÀY 1:» / «NGÀY 01:» là mốc ngày; nội dung + ảnh kceditor tới mốc sau.
      · #tabs-more «Quy định»: «GIÁ TOUR BAO GỒM:» / «GIÁ TOUR KHÔNG BAO GỒM:» + các đoạn mục; phần còn lại = quy định.
      · #tabs-adv «Bảng giá chi tiết»: Độ tuổi | Khách sạn | Giá tiền | Phụ thu phòng đơn; «Đang cập nhật» → giá rỗng.
    Chỉ giữ chữ thuần và link ảnh tuyệt đối trên vietourist.com.vn."""
    cay = _Cay()
    cay.feed(html or "")
    nut = list(_duyet(cay.goc))
    meta = {(n.attrs.get("property") or n.attrs.get("name") or "").lower(): n.attrs.get("content", "") for n in nut if n.tag == "meta"}
    h1 = next((_sach(_chu(n)) for n in nut if n.tag == "h1" and _sach(_chu(n))), "")
    ten = h1 or _sach(meta.get("og:title", ""))
    # ẢNH album
    anh: list[str] = []
    ten_tep: dict[str, int] = {}
    for n in nut:
        if n.tag != "img" or _anh_tour_khac(n) or not _trong(n, lambda c: _lop(c, "album-gallery")):
            continue
        a = _anh(n, url)
        if not a:
            continue
        day_du = a.replace("/thumbnail/", "/")
        tep = day_du.rsplit("/", 1)[-1].lower()
        if tep not in ten_tep:
            ten_tep[tep] = len(anh)
            anh.append(day_du)
    if not anh and meta.get("og:image"):
        a = urljoin(url, meta["og:image"]).replace("/thumbnail/", "/")
        if urlparse(a).scheme == "https" and (urlparse(a).hostname or "") in WEB_HOST:
            anh.append(a)
    # THÔNG TIN
    khoi_hanh = thoi_luong = phuong_tien = ""
    gia_web = None
    bang = _tim(nut, lambda n: n.tag == "table" and _lop(n, "info-product"))
    if bang is not None:
        for tr in (x for x in _duyet(bang) if x.tag == "tr"):
            t = _sach(_chu(tr).replace("\n", " "))
            if ":" not in t:
                continue
            nhan, gt = (_sach(x) for x in t.split(":", 1))
            k = _khong_dau(nhan)
            if k.startswith("khoi hanh"):
                khoi_hanh = gt[:160]
            elif k.startswith("thoi gian"):
                thoi_luong = gt[:60]
            elif k.startswith("phuong tien"):
                phuong_tien = gt[:60]
            elif k == "gia":
                gia_web = _so_tien(gt)
    tab = {k: _tim(nut, lambda n, k=k: n.attrs.get("id") == k) for k in ("tabs-detail", "tabs-more", "tabs-adv")}
    # LỊCH TRÌNH
    lich: list[dict] = []
    gioi_thieu = ""
    if tab["tabs-detail"] is not None:
        for t, imgs in _khoi(tab["tabs-detail"], url):
            m = _NGAY_RE.match(t)
            if m and len(t) < 300:
                lich.append({"ngay": int(m.group(1)), "tieu_de": _sach(m.group(2))[:200], "noi_dung": "", "anh": list(imgs)})
            elif lich:
                if t:
                    lich[-1]["noi_dung"] = (lich[-1]["noi_dung"] + ("\n" if lich[-1]["noi_dung"] else "") + t)[:4000]
                lich[-1]["anh"] += [a for a in imgs if a not in lich[-1]["anh"]]
        so = [x["ngay"] for x in lich]
        if so != list(range(1, len(so) + 1)):
            lich = []                     # mốc ngày không liên tiếp → không tin cách tách
        # TR-1c: ảnh chèn trong «Chương trình tour» (kceditor) cũng là ảnh của tour → thêm vào album (trùng tên tệp bỏ)
        for _t, imgs in _khoi(tab["tabs-detail"], url):
            for a in imgs:
                day_du = a.replace("/thumbnail/", "/")
                tep = day_du.rsplit("/", 1)[-1].lower()
                if tep not in ten_tep:
                    ten_tep[tep] = len(anh)
                    anh.append(day_du)
        # TR-1c: trang chỉ có bài giới thiệu (tour Du lịch Xanh…) → giữ chữ làm «Giới thiệu», không bịa mốc ngày
        if not lich:
            gioi_thieu = "\n".join(t for t, _ in _khoi(tab["tabs-detail"], url) if t).strip()[:6000]
    # BAO GỒM / KHÔNG BAO GỒM / QUY ĐỊNH
    bao: list[str] = []
    khong: list[str] = []
    qd: list[str] = []
    if tab["tabs-more"] is not None:
        muc = "qd"
        for t, _ in _khoi(tab["tabs-more"], url):
            if not t:
                continue
            kd = _khong_dau(t)
            if re.match(r"^(gia\s*(tour\s*)?)?khong\s*bao\s*gom\b", kd) and len(t) < 80:
                muc = "khong"
                continue
            if re.match(r"^(gia\s*(tour\s*)?)?bao\s*gom\b", kd) and len(t) < 80:
                muc = "bao"
                continue
            if muc in ("bao", "khong") and _la_tieu_de_hoa(t):
                muc = "qd"
            dong = re.sub(r"^[-•·*✓✔+]\s*", "", t)
            if muc == "bao" and dong:
                bao.append(dong[:300])
            elif muc == "khong" and dong:
                khong.append(dong[:300])
            else:
                qd.append(t)
    quy_dinh = "\n".join(qd).strip()[:4000]
    # BẢNG GIÁ CHI TIẾT
    bang_gia = []
    if tab["tabs-adv"] is not None:
        cot_gia = cot_pt = cot_ks = None
        for tr in (x for x in _duyet(tab["tabs-adv"]) if x.tag == "tr"):
            o = [_sach(_chu(c).replace("\n", " ")) for c in tr.con if not isinstance(c, str) and c.tag in ("td", "th")]
            if not o:
                continue
            kd = [_khong_dau(x) for x in o]
            if kd[0].startswith("do tuoi"):
                cot_gia = next((i for i, x in enumerate(kd) if x.startswith("gia")), None)
                cot_pt = next((i for i, x in enumerate(kd) if x.startswith("phu thu")), None)
                cot_ks = next((i for i, x in enumerate(kd) if x.startswith("khach san")), None)
                continue
            if not re.search(r"nguoi\s*lon|tre\s*em|em\s*be|phu\s*thu|tuoi", kd[0]):
                continue
            o_gia = o[cot_gia] if cot_gia is not None and cot_gia < len(o) else ""
            gia = _so_tien(o_gia) or next((x for x in (_so_tien(c) for c in o[1:]) if x), None)
            pt = _so_tien(o[cot_pt]) if cot_pt is not None and cot_pt < len(o) else None
            ghi = "" if gia else next((c for c in ([o_gia] + o[1:]) if c and not re.fullmatch(r"(?i)không", c)), "")
            bang_gia.append({"doi_tuong": o[0][:80], "gia": gia, "ghi": ghi[:60],
                             "khach_san": (o[cot_ks] if cot_ks is not None and cot_ks < len(o) else "")[:80], "phu_thu_don": pt})
    return {"ten": ten[:200], "anh": anh[:40], "lich_trinh": lich, "bang_gia": bang_gia[:12], "bao_gom": bao[:40],
            "khong_bao_gom": khong[:40], "quy_dinh": quy_dinh, "khoi_hanh_text": khoi_hanh, "thoi_luong": thoi_luong,
            "phuong_tien": phuong_tien, "phuong_tien_ma": ma_phuong_tien(phuong_tien), "gia_web": gia_web, "link": url,
            "gioi_thieu": gioi_thieu}


def doc_tour_web(url: str) -> dict:
    url = kiem_link(url)
    data = FETCH(url)
    if len(data) > WEB_TOI_DA_BYTE:
        raise LoiTour("Trang web quá lớn (> 2 MB) — không đọc")
    return phan_tich(data.decode("utf-8", "replace"), url)


def lam_moi(db: Session, p: Product, now: datetime | None = None) -> dict:
    """Đọc lại trang web của sản phẩm. Hỏng thì GIỮ bản cũ, chỉ ghi lỗi + giờ thử."""
    now = now or datetime.now()
    cu = dict(p.noi_dung_web or {})
    if not p.link_web:
        raise LoiTour("Sản phẩm chưa ghép link tour trên web")
    try:
        moi = doc_tour_web(p.link_web)
        moi.update({"cap_nhat_luc": now.isoformat(timespec="minutes"), "loi": "", "thu_luc": now.isoformat(timespec="minutes")})
        p.noi_dung_web = moi
    except Exception as ex:   # noqa: BLE001 — web chính chậm / đổi cấu trúc: cổng vẫn chạy bằng bản cũ
        cu.update({"loi": str(ex)[:200] or ex.__class__.__name__, "thu_luc": now.isoformat(timespec="minutes")})
        p.noi_dung_web = cu
    return p.noi_dung_web


def can_lam_moi(p: Product, now: datetime | None = None) -> bool:
    """Cache cũ hơn 24 giờ (tính theo lần THỬ gần nhất, để web hỏng không bị gọi liên tục)."""
    if not p.link_web:
        return False
    nd = p.noi_dung_web or {}
    moc = nd.get("thu_luc") or nd.get("cap_nhat_luc")
    if not moc:
        return True
    try:
        return (now or datetime.now()) - datetime.fromisoformat(moc) > timedelta(hours=WEB_CU_GIO)
    except ValueError:
        return True


_XANH = ("du lich xanh", "chua lanh", "retreat", "wellness", "yoga")      # + «thiền» (có dấu — «thiên» không tính)


def phan_tich_ds(html: str, url: str) -> list[dict]:
    """Trang danh sách tour (/vn/tour/tour-trong-nuoc, /tour-nuoc-ngoai) → [{url, ten, anh, muc, goi_y_wellness}].
    Mỗi tour là một .item-product: tên + link ở .caption-product .caption-title a, ảnh ở .image. «muc» = tiêu đề mục gần
    nhất phía trên (Miền Nam / Miền Trung / Miền Bắc / Du Lịch Xanh). Mục «Du Lịch Xanh» hoặc tên có «Chữa Lành» / «Thiền»
    → goi_y_wellness = True (CHỈ GỢI Ý — Điều hành xác nhận nhãn Wellness ở hồ sơ cổng)."""
    cay = _Cay()
    cay.feed(html or "")
    ra: dict[str, dict] = {}
    muc = ""
    for n in _duyet(cay.goc):
        if n.tag in ("h1", "h2", "h3", "h4") or _lop(n, "title-category") or _lop(n, "title-section"):
            if not _trong(n, lambda c: _lop(c, "item-product")):
                t = _sach(_chu(n).replace("\n", " "))
                if t:
                    muc = t[:80]
            continue
        if not _lop(n, "item-product"):
            continue
        a = next((x for x in _duyet(n) if x.tag == "a" and _trong(x, lambda c: _lop(c, "caption-title"))), None)
        if a is None:
            continue
        h = urljoin(url, a.attrs.get("href", "")).split("#")[0]
        p = urlparse(h)
        if p.scheme != "https" or (p.hostname or "") not in WEB_HOST or not re.match(r"^/vn/tour/[^/]+/[^/]+\.html$", p.path):
            continue
        ten = _sach(_chu(a).replace("\n", " ")) or a.attrs.get("title", "")
        if not ten:
            continue
        img = next((x for x in _duyet(n) if x.tag == "img" and _trong(x, lambda c: _lop(c, "image"))), None)
        o = ra.setdefault(h, {"url": h, "ten": ten[:200], "anh": "", "muc": muc, "goi_y_wellness": False})
        if img is not None and not o["anh"]:
            o["anh"] = _anh(img, url).replace("/thumbnail/", "/")
        kd = _khong_dau(f"{muc} {ten}")
        o["goi_y_wellness"] = o["goi_y_wellness"] or any(k in kd for k in _XANH) or "thiền" in f"{muc} {ten}".lower()
    return list(ra.values())


_BO_TU = {"tour", "du", "lich", "ngay", "dem", "va", "kham", "pha", "hanh", "trinh", "tu", "di", "le", "tet", "khoi", "hanh"}


def _tu(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", _khong_dau(s)) if len(w) > 1 and w not in _BO_TU and not re.fullmatch(r"\d+[nd]\d*[nd]?", w)}


def _so_ngay(s: str) -> int | None:
    m = re.search(r"(\d{1,2})\s*n\s*\d{1,2}\s*[dđ]|(\d{1,2})\s*ngay", _khong_dau(s))
    return int(m.group(1) or m.group(2)) if m else None


def goi_y_ghep(web: list[dict], sps: list[Product]) -> list[dict]:
    """Gợi ý sản phẩm crm cho từng tour web (giống tên + cùng số ngày). Chỉ GỢI Ý — người xác nhận mới ghép."""
    ra = []
    for w in web:
        tw, nw = _tu(w["ten"]), _so_ngay(w["ten"])
        tot = None
        for p in sps:
            tp = _tu(p.name)
            if not tw or not tp:
                continue
            diem = len(tw & tp) / len(tw | tp)
            np_ = p.days or _so_ngay(p.name or "") or _so_ngay(p.length_text or "")
            if nw and np_ and nw == np_:
                diem += 0.15
            if tot is None or diem > tot[0]:
                tot = (diem, p)
        g = {"pid": tot[1].id, "ma": tot[1].code, "ten": tot[1].name, "diem": round(tot[0], 2)} if tot and tot[0] >= 0.25 else None
        ra.append({**w, "goi_y": g})
    return ra


# ══ 2 · SẢN PHẨM, CHUYẾN, THẺ ════════════════════════════════════════════════════════════════════════════════════

def tt_chung(db: Session) -> bool:
    from app.models.khach_san_vtd import CaiDatKsVtd
    r = db.get(CaiDatKsVtd, KHOA_TT)
    return bool(r and r.gia_tri == "1")


def mo_thanh_toan(db: Session, p: Product | None, chung: bool | None = None) -> bool:
    return bool(p is not None and p.mo_thanh_toan) and (tt_chung(db) if chung is None else chung)


def la_nuoc_ngoai(p: Product) -> bool:
    if (p.tour_type or "").endswith("nuoc_ngoai"):
        return True
    c = _khong_dau(p.country or "").strip()
    return bool(c) and c not in ("vn", "viet nam", "vietnam")


def loai(p: Product) -> str:
    return "doan" if (p.tour_type or "").startswith("doan") else "ghep"


def phuong_tien(p: Product) -> list[str]:
    if p.phuong_tien_ds:
        return [x for x in p.phuong_tien_ds if x in PHUONG_TIEN_TOUR]
    web = [x for x in ((p.noi_dung_web or {}).get("phuong_tien_ma") or []) if x in PHUONG_TIEN_TOUR]
    if web:
        return web                     # bảng info-product trên trang tour («Ô tô» / «Máy bay» …)
    t = _khong_dau(p.transport or "")
    ra = []
    for k, tu in (("may_bay", ("may bay", "bay")), ("tau_hoa", ("tau hoa", "tau lua")), ("du_thuyen", ("du thuyen", "cruise")), ("xe", ("xe", "o to", "bus"))):
        if any(x in t for x in tu):
            ra.append(k)
    return ra or (["xe"] if t else [])


def diem_den(p: Product) -> str:
    if p.diem_den:
        return p.diem_den
    ten = re.sub(r"(?i)^\s*(tour|chương trình)\s*(du lịch)?\s*", "", p.name or "")
    ten = re.sub(r"\s*\d+\s*N\s*\d+\s*[ĐD]\b.*$", "", ten, flags=re.I)
    return _sach(ten.split(":")[-1])[:120]


def gia_hieu_luc(t: Tour) -> tuple[int, int | None]:
    gia = int(t.price_per_pax or 0)
    km = int(t.price_promo or 0)
    return (km, gia) if 0 < km < gia else (gia, None)


def _chuyen(db: Session, sps: list[Product], hom_nay: date) -> dict[int, list[tuple[Tour, int]]]:
    """Chuyến đang bán của các sản phẩm (đã duyệt, chưa khởi hành, có giá, còn chỗ) — cùng luật cổng khách."""
    from app.services import cong_khach as K
    if not sps:
        return {}
    ids = [p.id for p in sps]
    ma = {p.code: p.id for p in sps}
    q = (select(Tour).where(Tour.status == "da_duyet", Tour.start_date > hom_nay, Tour.price_per_pax.is_not(None),
                            Tour.price_per_pax > 0, Tour.tour_type.not_in(K.KHONG_BAN),
                            or_(Tour.product_id.in_(ids), Tour.product_code.in_(list(ma))))
         .order_by(Tour.start_date, Tour.id))
    ts = db.execute(q).scalars().all()
    ban = K._da_ban(db, [t.id for t in ts])
    ra: dict[int, list] = {}
    for t in ts:
        con = K._con_cho(t, ban.get(t.id, 0))
        if con <= 0:
            continue
        pid = t.product_id if t.product_id in ids else ma.get(t.product_code)
        if pid:
            ra.setdefault(pid, []).append((t, con))
    return ra


def _chuyen_out(t: Tour, con: int, so_khach: int, hom_nay: date) -> dict:
    gia, goc = gia_hieu_luc(t)
    from app.services import cong_khach as K
    return {"tour_id": t.id, "ma": t.code, "khoi_hanh": t.start_date.isoformat(), "ket_thuc": t.end_date.isoformat(),
            "thu": t.start_date.weekday(), "gia": gia, "gia_goc": goc,
            "gia_tre_em": int(t.price_chd) if t.price_chd else gia, "gia_em_be": int(t.price_inf) if t.price_inf else 0,
            "con": con, "it_cho": 0 < con <= 5, "du_cho": con >= max(1, so_khach),
            "gio_chot": (t.start_date - hom_nay).days <= K.GIO_CHOT_NGAY}


def the_san_pham(p: Product, chuyen: list[tuple[Tour, int]], so_khach: int, hom_nay: date, chung: bool) -> dict:
    ds = [_chuyen_out(t, con, so_khach, hom_nay) for t, con in chuyen]
    du = [c for c in ds if c["du_cho"]]
    re_nhat = min(du, key=lambda c: c["gia"]) if du else None
    nd = p.noi_dung_web or {}
    ngay = p.days or (ds[0] and (date.fromisoformat(ds[0]["ket_thuc"]) - date.fromisoformat(ds[0]["khoi_hanh"])).days + 1 if ds else 0) or 1
    return {"id": p.id, "ma": p.code, "ten": p.name, "diem_den": diem_den(p), "nuoc_ngoai": la_nuoc_ngoai(p), "loai": loai(p),
            "loai_ten": LOAI_TOUR[loai(p)], "wellness": bool(p.wellness), "ngay": ngay, "dem": max(ngay - 1, 0),
            "thoi_luong": p.length_text or (f"{ngay}N{max(ngay - 1, 0)}Đ" if ngay > 1 else "1 ngày"),
            "noi_khoi_hanh": p.departure_point or "", "phuong_tien": phuong_tien(p),
            "gia_tu": re_nhat["gia"] if re_nhat else None, "gia_goc": re_nhat["gia_goc"] if re_nhat else None,
            "gia_tre_em": re_nhat["gia_tre_em"] if re_nhat else None,
            "so_chuyen": len(ds), "khoi_hanh_gan": [c["khoi_hanh"] for c in du[:4]],
            "khuyen_mai": any(c["gia_goc"] for c in du), "gio_chot": any(c["gio_chot"] for c in du),
            "it_cho": any(c["it_cho"] for c in du), "anh": list(nd.get("anh") or [])[:8], "noi_bat": list(p.noi_bat or [])[:5],
            "mo_thanh_toan": mo_thanh_toan(None, p, chung), "co_noi_dung": bool(nd.get("lich_trinh") or p.program)}


def _sp_hien(db: Session) -> list[Product]:
    return db.execute(select(Product).where(Product.status == "active").order_by(Product.code)).scalars().all()


def tim(db: Session, tab: str = "", q: str = "", noi: str = "", tu: date | None = None, den: date | None = None,
        nguoi_lon: int = 2, tre_em: int = 0, loai_: str = "", hom_nay: date | None = None) -> dict:
    """Thanh tìm: tab trong / ngoài nước, điểm đến (không dấu), nơi khởi hành, khoảng ngày đi, số khách, loại.
    Lọc mặt (thời lượng, giá, ưu đãi, phương tiện, wellness) làm trên trình duyệt từ thẻ trả về — số đếm thật."""
    hom_nay = hom_nay or _hom_nay()
    nl, te = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0))
    if nl + te > 60:
        raise LoiTour("Tối đa 60 khách một lần đặt — đoàn đông hơn gửi yêu cầu thiết kế tour")
    if tu and den and den < tu:
        raise LoiTour("Khoảng ngày đi chưa đúng")
    sps = _sp_hien(db)
    ch = _chuyen(db, sps, hom_nay)
    chung = tt_chung(db)
    k0 = _khong_dau(q.strip())
    the, noi_ds = [], set()
    for p in sps:
        ds = ch.get(p.id, [])
        if loai(p) == "ghep" and not ds:
            continue                                     # tour ghép phải có chuyến đang bán
        if loai(p) == "doan" and not ds and not (p.link_web or (p.program or "").strip()):
            continue                                     # tour đoàn: có chương trình mới hiện để khách xem
        if p.departure_point:
            noi_ds.add(p.departure_point)
        if tab == "trong_nuoc" and la_nuoc_ngoai(p) or tab == "nuoc_ngoai" and not la_nuoc_ngoai(p):
            continue
        if loai_ in LOAI_TOUR and loai(p) != loai_:
            continue
        if k0 and k0 not in _khong_dau(f"{p.name} {p.diem_den} {p.country} {p.region} {p.code}"):
            continue
        if noi and p.departure_point != noi:
            continue
        if tu or den:
            ds = [(t, c) for t, c in ds if (not tu or t.start_date >= tu) and (not den or t.start_date <= den)]
            if loai(p) == "ghep" and not ds:
                continue
        the.append(the_san_pham(p, ds, nl + te, hom_nay, chung))
    the.sort(key=lambda o: (o["gia_tu"] is None, min(o["khoi_hanh_gan"] or ["9999"]), o["ten"]))
    return {"san_pham": the, "tong": len(the), "noi_khoi_hanh": sorted(noi_ds), "nguoi_lon": nl, "tre_em": te,
            "phuong_tien": PHUONG_TIEN_TOUR, "loai": LOAI_TOUR, "co_wellness": any(o["wellness"] for o in the),
            "mo_thanh_toan_chung": chung}


def tach_ngay(van_ban: str) -> list[dict]:
    """Chương trình sản phẩm (văn bản tự do) → từng ngày, CHỈ khi có mốc «Ngày 1..N» liên tiếp."""
    dong = (van_ban or "").replace("\r", "").split("\n")
    ra: list[dict] = []
    for d in dong:
        m = _NGAY_RE.match(_KHONG_RONG.sub("", d))
        if m and len(d) < 300:
            ra.append({"ngay": int(m.group(1)), "tieu_de": _sach(m.group(2))[:200], "noi_dung": "", "anh": []})
        elif ra:
            ra[-1]["noi_dung"] = (ra[-1]["noi_dung"] + ("\n" if ra[-1]["noi_dung"] else "") + d.strip()).strip()[:4000]
    if not ra or [x["ngay"] for x in ra] != list(range(1, len(ra) + 1)):
        return []
    return ra


def lich_trinh(db: Session, p: Product, tour_id: int | None = None) -> dict:
    """Ưu tiên: chương trình của chuyến → lịch trình đọc từ web → chương trình sản phẩm có mốc ngày → nguyên văn."""
    from app.models.chuong_trinh import ChuongTrinhNgay
    if tour_id:
        ngay = db.execute(select(ChuongTrinhNgay).where(ChuongTrinhNgay.tour_id == tour_id)
                          .order_by(ChuongTrinhNgay.ngay_thu)).scalars().all()
        if any((n.tieu_de or n.noi_dung or "").strip() for n in ngay):
            return {"nguon": "chuyen", "ngay": [{"ngay": n.ngay_thu, "tieu_de": n.tieu_de, "noi_dung": n.noi_dung,
                                                "bua": [b for b, co in (("sáng", n.bua_sang), ("trưa", n.bua_trua), ("tối", n.bua_toi)) if co],
                                                "khach_san": n.khach_san, "anh": []} for n in ngay], "van_ban": ""}
    web = (p.noi_dung_web or {}).get("lich_trinh") or []
    if web:
        return {"nguon": "web", "ngay": [{**x, "bua": [], "khach_san": ""} for x in web], "van_ban": ""}
    tn = tach_ngay(p.program or "")
    if tn:
        return {"nguon": "san_pham", "ngay": [{**x, "bua": [], "khach_san": ""} for x in tn], "van_ban": ""}
    gt = ((p.noi_dung_web or {}).get("gioi_thieu") or "").strip()   # TR-1c: bài giới thiệu trên web trước văn bản sản phẩm
    if gt:
        return {"nguon": "web_gioi_thieu", "ngay": [], "van_ban": gt[:8000]}
    return {"nguon": "van_ban", "ngay": [], "van_ban": (p.program or "").strip()[:8000]}


def chi_tiet(db: Session, pid: int, nguoi_lon: int = 2, tre_em: int = 0, hom_nay: date | None = None) -> dict:
    hom_nay = hom_nay or _hom_nay()
    p = db.get(Product, pid)
    if p is None or p.status != "active":
        raise LoiTour("Tour này không còn trên cổng", 404)
    nl, te = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0))
    ds = _chuyen(db, [p], hom_nay).get(p.id, [])
    if loai(p) == "ghep" and not ds:
        raise LoiTour("Tour này hiện chưa có ngày khởi hành mở bán — xem tour khác hoặc gửi yêu cầu", 404)
    chung = tt_chung(db)
    the = the_san_pham(p, ds, nl + te, hom_nay, chung)
    nd = p.noi_dung_web or {}
    chuyen = [_chuyen_out(t, con, nl + te, hom_nay) for t, con in ds]
    return {**the, "chuyen": chuyen, "lich_trinh": lich_trinh(db, p, chuyen[0]["tour_id"] if chuyen else None),
            "anh": list(nd.get("anh") or []), "bao_gom": list(nd.get("bao_gom") or []), "khong_bao_gom": list(nd.get("khong_bao_gom") or []),
            "quy_dinh": nd.get("quy_dinh") or "", "bang_gia_web": list(nd.get("bang_gia") or []),
            "khoi_hanh_text": nd.get("khoi_hanh_text") or "", "link_web": p.link_web or "",
            "web_cap_nhat": nd.get("cap_nhat_luc"), "dich_vu": p.services or "",
            "coc_pt": float(p.deposit_pct or R.get_param(db, "coc_mac_dinh_pct")), "dong_so_truoc": int(p.days_to_close or 0),
            "the_bat": _the_bat()}


def lich_trinh_chuyen(db: Session, pid: int, tour_id: int) -> dict:
    p = db.get(Product, pid)
    t = db.get(Tour, tour_id)
    if p is None or t is None or (t.product_id != p.id and t.product_code != p.code):
        raise LoiTour("Không có chuyến này", 404)
    return lich_trinh(db, p, t.id)


def _the_bat() -> bool:
    try:
        from app.services import sepay_pg as SP
        return bool(SP.cong_the_bat())
    except Exception:   # noqa: BLE001
        return False


# ══ 3 · TIỀN ══════════════════════════════════════════════════════════════════════════════════════════════════════

def _sp_cua(db: Session, t: Tour) -> Product | None:
    if t.product_id:
        return db.get(Product, t.product_id)
    return db.execute(select(Product).where(Product.code == t.product_code)).scalars().first() if t.product_code else None


def tinh(db: Session, tour_id: int, nguoi_lon: int, tre_em: int = 0, em_be: int = 0, cach_tra: str = "coc",
         now: datetime | None = None) -> dict:
    from app.services import cong_khach as K
    now = now or datetime.now()
    nl, te, eb = int(nguoi_lon or 0), int(tre_em or 0), int(em_be or 0)
    if nl < 1 or te < 0 or eb < 0 or nl + te > 60 or eb > nl:
        raise LoiTour("Ít nhất 1 người lớn; tối đa 60 khách; mỗi em bé đi cùng một người lớn")
    try:
        o = K.tour(db, int(tour_id or 0))
    except K.LoiKhach as ex:
        raise LoiTour(str(ex))
    t = db.get(Tour, o["id"])
    con = K._con_cho(t, K._da_ban(db, [t.id]).get(t.id, 0))
    if nl + te > con:
        raise LoiTour(f"Chuyến này còn {con} chỗ — giảm số khách hoặc chọn ngày khác", 409)
    p = _sp_cua(db, t)
    gia, goc = gia_hieu_luc(t)
    g_te = int(t.price_chd) if t.price_chd else gia
    g_eb = int(t.price_inf) if t.price_inf else 0
    dong = [{"nhan": f"Người lớn × {nl}", "don_gia": gia, "so": nl, "tien": gia * nl}]
    if te:
        dong.append({"nhan": f"Trẻ em × {te}", "don_gia": g_te, "so": te, "tien": g_te * te})
    if eb:
        dong.append({"nhan": f"Em bé × {eb}", "don_gia": g_eb, "so": eb, "tien": g_eb * eb})
    tong = sum(d["tien"] for d in dong)
    pct = float(p.deposit_pct) if p and p.deposit_pct else float(R.get_param(db, "coc_mac_dinh_pct"))
    coc = min(tong, int(math.ceil(tong * pct / 100 / 1000) * 1000))
    ngay_dong = int(p.days_to_close) if p and p.days_to_close is not None else int(R.get_param(db, "han_huy_cho_ngay"))
    han = datetime.combine(t.start_date - timedelta(days=ngay_dong), time(17, 0))
    cho_coc = han > now and 0 < coc < tong
    cach = cach_tra if cach_tra in CACH_TRA_TOUR else "coc"
    if cach == "coc" and not cho_coc:
        cach = "du"
    return {"tour_id": t.id, "ma_chuyen": t.code, "ten": p.name if p else t.name, "product_id": p.id if p else None,
            "khoi_hanh": t.start_date.isoformat(), "ket_thuc": t.end_date.isoformat(), "dong": dong, "tong": tong,
            "goc_moi_nguoi": goc, "coc_pt": pct, "coc": coc, "cho_coc": cho_coc, "cach_tra": cach,
            "phai_tra": coc if cach == "coc" else tong, "han_tra_con_lai": han.isoformat(timespec="minutes"),
            "nuoc_ngoai": bool(p and la_nuoc_ngoai(p)), "mo_thanh_toan": mo_thanh_toan(db, p), "con": con}


def _kiem_mo_tt(db: Session, p: Product | None) -> None:
    if not mo_thanh_toan(db, p):
        raise LoiTour("Thanh toán trực tuyến chưa mở cho tour này — bấm «Gửi yêu cầu giữ chỗ», Sales liên hệ bạn", 409)


def _kiem_khach(ds: list, nl: int, te: int, eb: int, nuoc_ngoai: bool, ngay_di: date) -> list[dict]:
    if len(ds or []) != nl + te + eb:
        raise LoiTour(f"Ghi đủ thông tin {nl + te + eb} khách")
    ra = []
    for i, k in enumerate(ds):
        ten = _sach(str(k.get("ho_ten") or ""))
        if len(ten.split()) < 2:
            raise LoiTour(f"Khách {i + 1}: ghi đủ họ và tên")
        try:
            ns = date.fromisoformat(str(k.get("ngay_sinh") or "")[:10])
        except ValueError:
            raise LoiTour(f"Khách {i + 1}: ngày sinh chưa đúng")
        if ns >= ngay_di or ns.year < 1900:
            raise LoiTour(f"Khách {i + 1}: ngày sinh chưa đúng")
        gt = str(k.get("gioi_tinh") or "")
        gt = gt if gt in ("nam", "nu") else ""
        gtt = _sach(str(k.get("giay_to") or ""))[:40]
        if nuoc_ngoai and len(gtt) < 6:
            raise LoiTour(f"Khách {i + 1}: tour nước ngoài cần số hộ chiếu")
        loai_k = "nguoi_lon" if i < nl else ("tre_em" if i < nl + te else "em_be")
        ra.append({"ho_ten": ten[:120], "ngay_sinh": ns.isoformat(), "gioi_tinh": gt, "giay_to": gtt, "loai": loai_k})
    return ra


def dat(db: Session, tk: TaiKhoanNgoai, d: dict, now: datetime | None = None) -> DonTourOnline:
    """Khách bấm «Thanh toán»: máy tính lại tiền, qua ĐỦ cổng chiếm chỗ như Điều hành tạo booking, giữ chỗ 15 phút
    (VPM-7), tạo booking + phần cổng. Trình duyệt không gửi số tiền nào lên."""
    from fastapi import HTTPException
    from app.services import bookings as BK
    from app.services import cong_khach as K
    from app.services import doi_tac_cong as DT
    from app.services import tours as TS
    from app.services.zalo import norm_phone
    now = now or datetime.now()
    try:
        K.la_khach_hoac_co_dong(tk)
    except K.LoiKhach as ex:
        raise LoiTour(str(ex), 403)
    nl, te, eb = int(d.get("nguoi_lon") or 0), int(d.get("tre_em") or 0), int(d.get("em_be") or 0)
    tinh_ = tinh(db, int(d.get("tour_id") or 0), nl, te, eb, str(d.get("cach_tra") or "coc"), now)
    t = db.get(Tour, tinh_["tour_id"])
    p = _sp_cua(db, t)
    _kiem_mo_tt(db, p)
    if not d.get("dong_y"):
        raise LoiTour("Đánh dấu đồng ý điều khoản và chính sách hủy của tour")
    ho_ten = _sach(str(d.get("ho_ten") or tk.ho_ten or ""))
    if len(ho_ten.split()) < 2:
        raise LoiTour("Ghi đủ họ và tên người liên hệ")
    sdt = norm_phone(str(d.get("dien_thoai") or "")) or tk.dien_thoai or ""
    if len(sdt) != 10 or not sdt.startswith("0"):
        raise LoiTour("Ghi số điện thoại liên hệ (10 số)")
    email = str(d.get("email") or tk.email or "").strip()[:160]
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise LoiTour("Ghi email để nhận xác nhận thanh toán và invoice")
    khach = _kiem_khach(d.get("khach") or [], nl, te, eb, tinh_["nuoc_ngoai"], t.start_date)
    hd = d.get("hoa_don_cong_ty") or None
    if hd:
        mst = re.sub(r"\D", "", str(hd.get("mst") or ""))
        if len(mst) not in (10, 13) or not str(hd.get("ten") or "").strip():
            raise LoiTour("Hóa đơn công ty: ghi mã số thuế (10 hoặc 13 số) và tên công ty")
        hd = {"mst": mst, "ten": str(hd["ten"]).strip()[:200], "dia_chi": str(hd.get("dia_chi") or "").strip()[:300],
              "email": str(hd.get("email") or email).strip()[:160]}
    cho = db.execute(select(func.count(DonTourOnline.id)).join(Booking, Booking.id == DonTourOnline.booking_id).where(
        DonTourOnline.tai_khoan_ngoai_id == tk.id, DonTourOnline.tao_luc >= now - timedelta(days=1),
        Booking.cancelled.is_(False), or_(Booking.paid.is_(None), Booking.paid <= 0))).scalar_one()
    if cho >= DON_CHO_TOI_DA_NGAY:
        raise LoiTour("Bạn đang có nhiều đơn chưa thanh toán — thanh toán hoặc chờ đơn cũ hết hạn giữ chỗ", 429)
    try:
        TS.cong_tao_booking(db, t, nl + te, 0)
    except HTTPException as ex:
        db.rollback()
        dt_ = ex.detail
        raise LoiTour(dt_.get("message") if isinstance(dt_, dict) else str(dt_), 422)
    sa = DT.sale_admin_le(db)
    if sa is None:
        raise LoiTour("Vietourist chưa có bàn Sales Admin lẻ tiếp nhận đơn online — vui lòng gửi yêu cầu giữ chỗ", 409)
    nguon = "Cổng khách · đặt tour online"
    yc = _sach(str(d.get("yeu_cau") or ""))[:800]
    note = f"[Đặt online {now:%d/%m %H:%M}] tài khoản cổng #{tk.id} · {CACH_TRA_TOUR[tinh_['cach_tra']]}" + (f" · {yc}" if yc else "")
    r = ServiceRequest(tour_id=t.id, sales_id=sa.id, customer_name=ho_ten[:120], customer_phone=sdt, source=nguon,
                       care_note=note, pax=nl + te, created_at=now)
    db.add(r); db.flush()
    n = db.execute(select(func.count()).select_from(Booking)).scalar() + 1
    b = Booking(code=f"BK{now:%y%m}{n:04d}", tour_id=t.id, request_id=r.id, sales_id=sa.id, created_by=sa.id,
                customer_name=ho_ten[:120], customer_phone=sdt, customer_email=email[:120], source=nguon, care_note=note,
                pax=nl + te, adl=nl, chd=te, inf=eb, amount=tinh_["tong"], discount=0, counts_for_target=False,
                sla_minutes=0, sla_ok=True, company_id=t.company_id, created_at=now)
    while db.execute(select(Booking.id).where(Booking.code == b.code)).first():
        n += 1
        b.code = f"BK{now:%y%m}{n:04d}"
    db.add(b); db.flush(); r.booking_id = b.id
    BK.init_terms(db, b, t)
    b.giu_cho_den = min(b.giu_cho_den or now + timedelta(minutes=GIU_PHUT), now + timedelta(minutes=GIU_PHUT))
    don = DonTourOnline(booking_id=b.id, ma=b.code, tour_id=t.id, product_id=p.id if p else None, tai_khoan_ngoai_id=tk.id,
                        nguoi_lon=nl, tre_em=te, em_be=eb, khach=khach, email=email, cach_tra=tinh_["cach_tra"],
                        tong=tinh_["tong"], phai_tra=tinh_["phai_tra"],
                        han_tra_con_lai=datetime.fromisoformat(tinh_["han_tra_con_lai"]) if tinh_["cach_tra"] == "coc" else None,
                        hoa_don_cong_ty=hd, yeu_cau=yc, tao_luc=now)
    db.add(don)
    if not db.execute(select(Alert).where(Alert.kind == "tour_online_dat", Alert.ref == b.code[:60],
                                          Alert.resolved == False)).scalars().first():   # noqa: E712 — khuôn dò dòng đang mở
        db.add(Alert(kind="tour_online_dat", level="info", ref=b.code[:60],
                     message=f"Khách đặt online {nl + te} chỗ {t.code} ({b.code}) — {CACH_TRA_TOUR[tinh_['cach_tra']]} {_vnd(tinh_['phai_tra'])} đ, "
                             f"giữ chỗ tới {b.giu_cho_den:%H:%M %d/%m} · tiếp nhận: {sa.full_name}",
                     to_roles="sales_admin,tp_kd,gd_kd,nv_dh"))
    R.audit(db, f"cong:{tk.id}", tk.loai, "tour_online_dat", f"booking:{b.code}",
            after={"tour": t.code, "nl": nl, "te": te, "eb": eb, "tong": tinh_["tong"], "cach_tra": tinh_["cach_tra"],
                   "phai_tra": tinh_["phai_tra"], "hoa_don_cong_ty": bool(hd)})
    db.commit(); db.refresh(don)
    return don


def _don_cua(db: Session, tk: TaiKhoanNgoai, ma: str) -> DonTourOnline:
    d = db.execute(select(DonTourOnline).where(DonTourOnline.ma == ma, DonTourOnline.tai_khoan_ngoai_id == tk.id)).scalars().first()
    if d is None:
        raise LoiTour("Không tìm thấy đơn này trong tài khoản của bạn", 404)
    return d


def da_tra(db: Session, b: Booking) -> int:
    from app.services.payments import paid_amount
    return int(round(float(paid_amount(db, b.id))))


def ra_khach(db: Session, d: DonTourOnline, now: datetime | None = None) -> dict:
    now = now or datetime.now()
    b = db.get(Booking, d.booking_id)
    t = db.get(Tour, d.tour_id)
    p = db.get(Product, d.product_id) if d.product_id else None
    tra = da_tra(db, b)
    con_ngay = max(int(d.phai_tra) - tra, 0)
    het_giu = bool(b.giu_cho_het or (b.giu_cho_den and b.giu_cho_den < now and tra <= 0))
    tt = ("Đã hủy" if b.cancelled else "Hết giờ giữ chỗ" if het_giu else "Đã thanh toán đủ" if tra >= int(d.tong or 0)
          else "Đã đặt cọc — giữ chỗ" if tra >= int(d.phai_tra) else "Chờ thanh toán")
    return {"ma": d.ma, "ten": p.name if p else t.name, "ma_chuyen": t.code, "khoi_hanh": t.start_date.isoformat(),
            "ket_thuc": t.end_date.isoformat(), "noi_khoi_hanh": t.departure_point or (p.departure_point if p else ""),
            "nguoi_lon": d.nguoi_lon, "tre_em": d.tre_em, "em_be": d.em_be, "khach": d.khach or [], "email": d.email,
            "cach_tra": d.cach_tra, "cach_tra_ten": CACH_TRA_TOUR.get(d.cach_tra, d.cach_tra), "tong": int(d.tong),
            "phai_tra": int(d.phai_tra), "da_tra": tra, "con_phai_tra_ngay": con_ngay, "con_lai": max(int(d.tong or 0) - tra, 0),
            "han_tra_con_lai": d.han_tra_con_lai.isoformat(timespec="minutes") if d.han_tra_con_lai else None,
            "giu_den": b.giu_cho_den.isoformat(timespec="seconds") if b.giu_cho_den else None,
            "giay_con": max(0, int((b.giu_cho_den - now).total_seconds())) if b.giu_cho_den and tra <= 0 and not het_giu else 0,
            "trang_thai": tt, "co_the_tra": not b.cancelled and not het_giu and tra < int(d.tong or 0),
            "mo_thanh_toan": mo_thanh_toan(db, p), "the_bat": _the_bat(), "co_hoa_don": tra > 0,
            "hoa_don_cong_ty": d.hoa_don_cong_ty, "email_gui_luc": d.email_gui_luc.isoformat(timespec="minutes") if d.email_gui_luc else None,
            "tao_luc": d.tao_luc.isoformat(timespec="minutes")}


def don_khach(db: Session, tk: TaiKhoanNgoai, ma: str) -> dict:
    return ra_khach(db, _don_cua(db, tk, ma))


def qr(db: Session, tk: TaiKhoanNgoai, ma: str, muc: str = "") -> dict:
    from app.services import cong_khach as K
    d = _don_cua(db, tk, ma)
    _kiem_mo_tt(db, db.get(Product, d.product_id) if d.product_id else None)
    o = ra_khach(db, d)
    if not o["co_the_tra"]:
        raise LoiTour(f"Đơn đang «{o['trang_thai']}» — không thanh toán", 409)
    try:
        r = K.qr_don(db, tk, ma, muc)
    except K.LoiKhach as ex:
        raise LoiTour(str(ex))
    r["tu_khop"] = True          # TR-1: đơn online — máy khớp cả số cọc lẫn số còn lại (tu_khop bên dưới)
    return r


def goc_tra_ve(origin: str) -> str:
    """Địa chỉ cổng thẻ trả khách về. Chỉ tên miền Vietourist (không để «Origin» lạ biến trang trả về thành trang ngoài);
    trên tên miền cổng dùng /tours/don/…, nơi khác (crm, bản thử) dùng /kham-pha/tours/don/…"""
    # TM-1 (02/11/2026): vietourist.com.vn song song — chỉ bốn tên cổng (gốc/www .com.vn là web cũ, không nhận).
    m = re.fullmatch(r"https://(([a-z0-9-]+\.)?vietourist\.vn|(crm|kh|dt|ir)\.vietourist\.com\.vn)", (origin or "").strip().lower().rstrip("/"))
    if not m:
        return "https://kh.vietourist.vn/tours"
    o = origin.strip().lower().rstrip("/")
    return o + ("/tours" if re.match(r"https://(kh|dt|ir)\.", o) else "/kham-pha/tours")


def the_bat_dau(db: Session, tk: TaiKhoanNgoai, ma: str, goc: str, muc: str = "", now: datetime | None = None) -> dict:
    """Thẻ Visa / Master / JCB / ATM qua cổng SePay. Số tiền do máy tính (cọc còn thiếu hoặc toàn bộ còn lại)."""
    from app.services import sepay_pg as SP
    now = now or datetime.now()
    d = _don_cua(db, tk, ma)
    _kiem_mo_tt(db, db.get(Product, d.product_id) if d.product_id else None)
    if not SP.bat():
        raise LoiTour("Thanh toán thẻ chưa mở — dùng QR chuyển khoản", 409)
    o = ra_khach(db, d, now)
    if not o["co_the_tra"]:
        raise LoiTour(f"Đơn đang «{o['trang_thai']}» — không thanh toán", 409)
    muc = muc if muc in ("coc", "du") else ("coc" if o["con_phai_tra_ngay"] and o["con_phai_tra_ngay"] < o["con_lai"] else "du")
    so = o["con_phai_tra_ngay"] if muc == "coc" and o["con_phai_tra_ngay"] > 0 else o["con_lai"]
    t = ThanhToanTourOnline(don_id=d.id, kenh="sepay", so_tien=so, trang_thai="cho", luc=now)
    db.add(t); db.flush()
    t.ma_gd = f"TR{d.id}T{t.id}"
    ve = f"{goc}/don/{d.ma}?the="
    f = SP.bieu_mau(t.ma_gd, so, f"Dat tour {d.ma}", ve + "cho", ve + "loi", ve + "huy")
    db.commit()
    return {"form": f}


def sepay_ket_qua(db: Session, kq: dict, now: datetime | None = None):
    """IPN SePay (mã giao dịch TR…): thành công + đúng số → phiếu thu chờ Kế toán xác nhận + email + invoice."""
    from app.services import payments as P
    now = now or datetime.now()
    t = db.execute(select(ThanhToanTourOnline).where(ThanhToanTourOnline.ma_gd == kq["ma_gd"])).scalars().first()
    if t is None:
        return None
    d = db.get(DonTourOnline, t.don_id)
    b = db.get(Booking, d.booking_id)
    if kq.get("loai") == "TRANSACTION_VOID":
        t.ghi_chu = f"SePay báo hủy giao dịch {kq.get('so_gd', '')} — Kế toán kiểm tra"[:300]
        R.audit(db, "sepay", "sepay", "tour_online_the_huy_gd", f"booking:{b.code}", after={"so_gd": kq.get("so_gd")})
        db.commit()
        return d, t
    if t.trang_thai in ("cho", "that_bai"):
        t.ket_qua, t.so_gd_cong = kq.get("ma_kq", ""), kq.get("so_gd", "")
        if kq.get("thanh_cong") and int(kq.get("so_tien") or 0) == int(t.so_tien):
            r = P._make_receipt(db, b, None, float(t.so_tien), "sepay", "tu_dong", note=f"Thẻ qua cổng SePay {t.so_gd_cong}")
            r.method = "the"
            t.trang_thai, t.receipt_id = "thanh_cong", r.id
            t.ghi_chu = " · ".join(x for x in (kq.get("cach", ""), kq.get("the", "")) if x)[:300]
            R.audit(db, "sepay", "sepay", "tour_online_the_thanh_cong", f"booking:{b.code}", after={"so_tien": int(t.so_tien), "receipt": r.code})
            db.flush()
            sau_khi_tra(db, d, now)
        else:
            t.trang_thai = "that_bai"
            t.ghi_chu = "Số tiền không khớp" if kq.get("thanh_cong") else f"SePay: {kq.get('loai')} {kq.get('ma_kq')}"[:300]
        db.commit()
    return d, t


BK_RE = re.compile(r"BK(\d{8})")


def tu_khop(db: Session, txn) -> bool:
    """Gọi từ khớp giao dịch ngân hàng, TRƯỚC đường booking chung: nội dung có mã của một ĐƠN ONLINE và số tiền
    đúng bằng cọc còn thiếu HOẶC toàn bộ còn lại → phiếu thu tự động (chờ Kế toán xác nhận) + email. Lệch số thì
    trả False để đường chung ghi «chờ Kế toán» như mọi booking."""
    from app.services import payments as P
    m = BK_RE.search((txn.content or "").upper().replace(" ", ""))
    if not m:
        return False
    d = db.execute(select(DonTourOnline).where(DonTourOnline.ma == "BK" + m.group(1))).scalars().first()
    if d is None:
        return False
    b = db.get(Booking, d.booking_id)
    if b is None or b.cancelled:
        return False
    tra = da_tra(db, b)
    so = int(round(float(txn.amount or 0)))
    coc_thieu = int(d.phai_tra) - tra
    con = int(d.tong or 0) - tra
    if so <= 0 or so not in {x for x in (coc_thieu, con) if x > 0}:
        return False
    r = P._make_receipt(db, b, txn, float(so), "robot", "tu_dong", note="Đơn tour online — khớp mã + đúng số")
    txn.match_status, txn.booking_id, txn.match_note = "da_khop", b.id, f"Tự động (tour online): {r.code}"
    R.audit(db, "robot", "robot", "tour_online_qr_tu_khop", f"receipt:{r.code}", after={"booking": b.code, "so_tien": so})
    db.flush()
    sau_khi_tra(db, d)
    return True


# ══ 4 · EMAIL XÁC NHẬN + INVOICE PDF ═════════════════════════════════════════════════════════════════════════════

def _gui_email_that(to: str, tieu_de: str, noi_dung: str, dinh_kem: list[tuple[str, bytes, str]]) -> None:
    """Cùng hộp thư / cấu hình SMTP đang gửi mã OTP đăng nhập cổng khách (cong_ngoai._gui_email)."""
    import smtplib
    from email.message import EmailMessage
    from app.core.config import settings
    if not (settings.SMTP_HOST and settings.SMTP_FROM):
        raise RuntimeError("Máy chủ chưa cấu hình SMTP")
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = tieu_de, settings.SMTP_FROM, to
    m.set_content(noi_dung)
    for ten, data, mime in dinh_kem:
        chinh, phu = mime.split("/", 1)
        m.add_attachment(data, maintype=chinh, subtype=phu, filename=ten)
    cls = smtplib.SMTP_SSL if settings.SMTP_SSL else smtplib.SMTP
    with cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as s:
        if not settings.SMTP_SSL:
            s.starttls()
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.send_message(m)


GUI_EMAIL = _gui_email_that      # phép thử thay bằng hàm ghi lại

PHONG = ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf")
PHONG_DAM = ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
             "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf")


def _phong(co: int, dam: bool = False):
    import os
    from PIL import ImageFont
    for f in (PHONG_DAM if dam else PHONG):
        if os.path.exists(f):
            return ImageFont.truetype(f, co)
    return ImageFont.load_default(co)


def co_phong_viet() -> bool:
    import os
    return any(os.path.exists(f) for f in PHONG)


def _bo_dau(s: str) -> str:
    """Phông dự phòng của Pillow không có dấu tiếng Việt → in KHÔNG DẤU (giữ hoa / thường) thay vì ô vuông."""
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def hoa_don_pdf(db: Session, d: DonTourOnline, now: datetime | None = None) -> bytes:
    """Invoice / phiếu xác nhận thanh toán của Vietourist (KHÔNG phải hóa đơn GTGT điện tử — Kế toán xuất riêng)."""
    import io
    from PIL import Image, ImageDraw
    from app.core.config import settings
    from app.models.payments import Receipt
    now = now or datetime.now()
    o = ra_khach(db, d, now)
    b = db.get(Booking, d.booking_id)
    W, H, L = 1240, 1754, 90
    im = Image.new("RGB", (W, H), "white")
    g = ImageDraw.Draw(im)
    if not co_phong_viet():          # máy chủ thiếu gói phông (fonts-dejavu-core): chữ không dấu, vẫn đọc được
        _ve = g.text
        g.text = lambda xy, chu, **k: _ve(xy, _bo_dau(str(chu)), **k)      # type: ignore[method-assign]
    f_to, f_dam, f_th, f_nho = _phong(40, True), _phong(24, True), _phong(24), _phong(20)
    y = 80
    g.text((L, y), settings.COMPANY_NAME, font=f_dam, fill="#0f2f6b"); y += 40
    g.text((L, y), "Vietourist · www.vietourist.com.vn · kh.vietourist.vn", font=f_nho, fill="#555"); y += 70
    g.text((L, y), "INVOICE · XÁC NHẬN THANH TOÁN TOUR", font=f_to, fill="#111"); y += 70
    for k, v in (("Mã đơn", d.ma), ("Ngày lập", f"{now:%d/%m/%Y %H:%M}"), ("Khách hàng", b.customer_name),
                 ("Điện thoại / Email", f"{b.customer_phone} · {d.email}"), ("Tour", o["ten"]),
                 ("Mã chuyến · khởi hành", f"{o['ma_chuyen']} · {date.fromisoformat(o['khoi_hanh']):%d/%m/%Y} – {date.fromisoformat(o['ket_thuc']):%d/%m/%Y}"),
                 ("Số khách", f"{d.nguoi_lon} người lớn" + (f" · {d.tre_em} trẻ em" if d.tre_em else "") + (f" · {d.em_be} em bé" if d.em_be else ""))):
        g.text((L, y), k, font=f_nho, fill="#666"); g.text((L + 330, y), str(v)[:70], font=f_th, fill="#111"); y += 42
    y += 20
    g.line((L, y, W - L, y), fill="#999", width=2); y += 20
    t = db.get(Tour, d.tour_id)
    gia, _goc = gia_hieu_luc(t)
    dong = [(f"Người lớn × {d.nguoi_lon}", gia * d.nguoi_lon)]
    if d.tre_em:
        g_te = int(t.price_chd) if t.price_chd else gia
        dong.append((f"Trẻ em × {d.tre_em}", g_te * d.tre_em))
    if d.em_be:
        dong.append((f"Em bé × {d.em_be}", (int(t.price_inf or 0) if (t.price_inf or 0) else 0) * d.em_be))
    for k, v in dong:
        g.text((L, y), k, font=f_th, fill="#111"); g.text((W - L - 260, y), f"{_vnd(v)} đ", font=f_th, fill="#111"); y += 40
    g.line((L, y, W - L, y), fill="#ddd", width=1); y += 16
    for k, v, dam in (("Tổng giá trị tour", o["tong"], True), ("Đã thanh toán", o["da_tra"], True), ("Còn lại", o["con_lai"], False)):
        g.text((L, y), k, font=f_dam if dam else f_th, fill="#111"); g.text((W - L - 260, y), f"{_vnd(v)} đ", font=f_dam if dam else f_th, fill="#111"); y += 44
    if o["con_lai"] > 0 and o["han_tra_con_lai"]:
        g.text((L, y), f"Hạn thanh toán phần còn lại: {datetime.fromisoformat(o['han_tra_con_lai']):%H:%M %d/%m/%Y}", font=f_th, fill="#b45309"); y += 44
    y += 20
    g.text((L, y), "Các lần thanh toán", font=f_dam, fill="#111"); y += 40
    for r in db.execute(select(Receipt).where(Receipt.booking_id == b.id, Receipt.status != "huy").order_by(Receipt.id)).scalars():
        cach = "Thẻ" if r.method == "the" else ("Tiền mặt" if r.method == "tien_mat" else "Chuyển khoản / QR")
        g.text((L, y), f"{r.code} · {r.created_at:%d/%m/%Y %H:%M} · {cach}", font=f_nho, fill="#333")
        g.text((W - L - 260, y), f"{_vnd(r.amount or 0)} đ", font=f_nho, fill="#333"); y += 34
    y += 30
    if d.hoa_don_cong_ty:
        h = d.hoa_don_cong_ty
        g.text((L, y), f"Yêu cầu hóa đơn GTGT: {h.get('ten', '')} · MST {h.get('mst', '')}", font=f_nho, fill="#333"); y += 32
        g.text((L, y), "Kế toán Vietourist sẽ xuất hóa đơn điện tử và gửi riêng.", font=f_nho, fill="#333"); y += 40
    g.text((L, H - 120), "Chứng từ xác nhận thanh toán do hệ thống Vietourist lập tự động — không thay hóa đơn GTGT.", font=f_nho, fill="#777")
    buf = io.BytesIO()
    im.save(buf, "PDF", resolution=150.0)
    return buf.getvalue()


def sau_khi_tra(db: Session, d: DonTourOnline, now: datetime | None = None) -> bool:
    """Có tiền mới (lớn hơn lần báo trước) → email «Xác nhận đã thanh toán» kèm invoice PDF. Lỗi gửi chỉ GHI LẠI,
    không làm hỏng việc nhận tiền."""
    now = now or datetime.now()
    b = db.get(Booking, d.booking_id)
    tra = da_tra(db, b)
    if tra <= int(d.email_moc or 0) or not d.email:
        return False
    o = ra_khach(db, d, now)
    try:
        pdf = hoa_don_pdf(db, d, now)
        noi = (f"Chào {b.customer_name},\n\nVietourist đã nhận {_vnd(tra)} đ cho đơn {d.ma} — {o['ten']}, khởi hành "
               f"{date.fromisoformat(o['khoi_hanh']):%d/%m/%Y}.\nTổng giá trị {_vnd(o['tong'])} đ · còn lại {_vnd(o['con_lai'])} đ"
               + (f" (hạn {datetime.fromisoformat(o['han_tra_con_lai']):%d/%m/%Y})" if o['con_lai'] > 0 and o['han_tra_con_lai'] else "")
               + ".\nInvoice đính kèm. Xem đơn tại kh.vietourist.vn → Đơn của tôi.\n\nVietourist")
        GUI_EMAIL(d.email, f"Xác nhận đã thanh toán · {d.ma} · {o['ten']}", noi, [(f"Invoice-{d.ma}.pdf", pdf, "application/pdf")])
        d.email_moc, d.email_gui_luc, d.email_loi = tra, now, ""
        R.audit(db, "he_thong", "he_thong", "tour_online_email", f"booking:{d.ma}", after={"da_tra": tra})
        return True
    except Exception as ex:   # noqa: BLE001
        d.email_loi = f"{now:%d/%m %H:%M} {ex}"[:300]
        return False


def tai_hoa_don(db: Session, tk: TaiKhoanNgoai, ma: str) -> bytes:
    d = _don_cua(db, tk, ma)
    if da_tra(db, db.get(Booking, d.booking_id)) <= 0:
        raise LoiTour("Đơn chưa có khoản thanh toán nào — chưa có invoice", 409)
    return hoa_don_pdf(db, d)


def gui_yeu_cau_doan(db: Session, tk: TaiKhoanNgoai, d: dict, now: datetime | None = None):
    """Tour đoàn riêng: «Gửi yêu cầu thiết kế tour» → luồng yêu cầu tour đoàn sẵn có (Sales báo giá)."""
    from app.services import cong_khach as K
    p = db.get(Product, int(d.get("product_id") or 0)) if d.get("product_id") else None
    them = [x for x in (
        f"Tour mẫu: {p.code} · {p.name}" if p else "",
        f"Ngày đi {d.get('tu_ngay')}" + (f"–{d.get('den_ngay')}" if d.get("den_ngay") else "") if d.get("tu_ngay") else "",
        f"Khởi hành từ {d.get('noi_khoi_hanh')}" if d.get("noi_khoi_hanh") else "",
        f"Ngân sách {_vnd(d.get('ngan_sach'))} đ/khách" if d.get("ngan_sach") else "",
        f"Khách sạn {d.get('hang_ks')}" if d.get("hang_ks") else "",
        f"Đơn vị: {d.get('cong_ty')}" if d.get("cong_ty") else "",
        "Cần hóa đơn công ty" if d.get("hoa_don") else "",
        _sach(str(d.get("ghi_chu") or "")),
    ) if x]
    ngay = None
    if d.get("tu_ngay"):
        try:
            ngay = date.fromisoformat(str(d["tu_ngay"])[:10])
        except ValueError:
            raise LoiTour("Ngày đi chưa đúng")
    try:
        return K.gui_yeu_cau(db, tk, "tour_doan", None, int(d.get("so_khach") or 0), str(d.get("dien_thoai") or ""), ngay,
                             " · ".join(them)[:1000], bool(d.get("dong_y")), now)
    except K.LoiKhach as ex:
        raise LoiTour(str(ex))


# ══ 5 · VTOS — màn «Tour trên cổng khách» ═════════════════════════════════════════════════════════════════════════

def _sp_vtos(db: Session, p: Product, so_chuyen: int) -> dict:
    nd = p.noi_dung_web or {}
    return {"id": p.id, "ma": p.code, "ten": p.name, "tour_type": p.tour_type, "loai": loai(p), "nuoc_ngoai": la_nuoc_ngoai(p),
            "diem_den": p.diem_den or "", "diem_den_suy": diem_den(p), "noi_bat": p.noi_bat or [], "wellness": bool(p.wellness),
            "phuong_tien_ds": p.phuong_tien_ds or [], "phuong_tien_suy": phuong_tien(p), "transport": p.transport or "",
            "mo_thanh_toan": bool(p.mo_thanh_toan), "link_web": p.link_web or "", "so_chuyen": so_chuyen,
            "web": {"cap_nhat_luc": nd.get("cap_nhat_luc"), "loi": nd.get("loi") or "", "so_anh": len(nd.get("anh") or []),
                    "so_ngay": len(nd.get("lich_trinh") or []), "so_bao_gom": len(nd.get("bao_gom") or []), "ten": nd.get("ten") or "",
                    "anh_dau": (nd.get("anh") or [None])[0]},
            "co_chuong_trinh": bool((p.program or "").strip())}


def ds_vtos(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM)
    sps = _sp_hien(db)
    ch = _chuyen(db, sps, _hom_nay())
    return {"san_pham": [_sp_vtos(db, p, len(ch.get(p.id, []))) for p in sps], "tt_chung": tt_chung(db),
            "phuong_tien": PHUONG_TIEN_TOUR, "ma_tran": {k: list(v) for k, v in MA_TRAN.items()},
            "duoc": {"sua": _co(u, VAI_SUA_CONG), "ghep": _co(u, VAI_GHEP), "tt_chung": _co(u, VAI_TT_CHUNG),
                     "don": _co(u, VAI_XEM_DON), "vat": _co(u, VAI_VAT)}}


def sua_cong(db: Session, u: User, pid: int, d: dict) -> Product:
    _quyen(u, VAI_SUA_CONG, "Chỉ Marketing / Điều hành sửa hồ sơ tour trên cổng")
    p = db.get(Product, pid)
    if p is None:
        raise LoiTour("Không có sản phẩm này", 404)
    truoc = {"diem_den": p.diem_den, "noi_bat": p.noi_bat, "wellness": p.wellness, "phuong_tien_ds": p.phuong_tien_ds}
    if "diem_den" in d:
        p.diem_den = _sach(str(d.get("diem_den") or ""))[:120]
    if "noi_bat" in d:
        nb = [_sach(str(x))[:120] for x in (d.get("noi_bat") or []) if _sach(str(x))]
        if len(nb) > 5:
            raise LoiTour("Tối đa 5 dòng nổi bật")
        p.noi_bat = nb
    if "wellness" in d:
        p.wellness = bool(d.get("wellness"))
    if "phuong_tien_ds" in d:
        ds = [x for x in (d.get("phuong_tien_ds") or []) if x in PHUONG_TIEN_TOUR]
        p.phuong_tien_ds = list(dict.fromkeys(ds))
    R.audit(db, u.username, u.role, "tour_cong_sua", f"product:{p.code}", before=truoc,
            after={"diem_den": p.diem_den, "noi_bat": p.noi_bat, "wellness": p.wellness, "phuong_tien_ds": p.phuong_tien_ds})
    db.commit(); db.refresh(p)
    return p


def doc_lai(db: Session, u: User, pid: int) -> dict:
    _quyen(u, VAI_SUA_CONG, "Chỉ Marketing / Điều hành đọc lại nội dung web")
    p = db.get(Product, pid)
    if p is None:
        raise LoiTour("Không có sản phẩm này", 404)
    nd = lam_moi(db, p)
    R.audit(db, u.username, u.role, "tour_cong_doc_web", f"product:{p.code}", after={"loi": nd.get("loi") or "", "so_anh": len(nd.get("anh") or [])})
    db.commit()
    return nd


def ds_web(db: Session, u: User) -> list[dict]:
    """Tour đang có trên vietourist.com.vn (2 trang danh sách) + gợi ý sản phẩm crm để Điều hành xác nhận ghép."""
    _quyen(u, VAI_SUA_CONG + VAI_GHEP)
    web: dict[str, dict] = {}
    loi = []
    for url in WEB_DS:
        try:
            for o in phan_tich_ds(FETCH(url).decode("utf-8", "replace"), url):
                web.setdefault(o["url"], o)
        except Exception as ex:   # noqa: BLE001
            loi.append(f"{url}: {ex}"[:200])
    sps = _sp_hien(db)
    da = {p.link_web: p for p in sps if p.link_web}
    ra = goi_y_ghep(list(web.values()), sps)
    for o in ra:
        g = da.get(o["url"])
        o["da_ghep"] = {"pid": g.id, "ma": g.code, "ten": g.name} if g else None
    if loi and not ra:
        raise LoiTour("Không đọc được danh sách tour trên web: " + "; ".join(loi), 502)
    return ra


def ghep(db: Session, u: User, pid: int, url: str) -> Product:
    _quyen(u, VAI_GHEP, "Chỉ TP Điều hành / TP-GĐ Kinh doanh xác nhận ghép tour web với sản phẩm")
    p = db.get(Product, pid)
    if p is None:
        raise LoiTour("Không có sản phẩm này", 404)
    url = (url or "").strip()
    if url:
        kiem_link(url)
        khac = db.execute(select(Product).where(Product.link_web == url, Product.id != p.id)).scalars().first()
        if khac is not None:
            raise LoiTour(f"Link này đang ghép với {khac.code} — bỏ ghép ở đó trước", 409)
    truoc = p.link_web
    p.link_web = url
    if url != truoc:
        p.noi_dung_web = None
    R.audit(db, u.username, u.role, "tour_cong_ghep_web", f"product:{p.code}", before={"link_web": truoc}, after={"link_web": url})
    if url:
        lam_moi(db, p)
    db.commit(); db.refresh(p)
    return p


def bat_tt_sp(db: Session, u: User, pid: int, bat: bool) -> Product:
    _quyen(u, VAI_GHEP, "Chỉ TP Điều hành / TP-GĐ Kinh doanh mở / đóng thanh toán của sản phẩm")
    p = db.get(Product, pid)
    if p is None:
        raise LoiTour("Không có sản phẩm này", 404)
    p.mo_thanh_toan = bool(bat)
    R.audit(db, u.username, u.role, "tour_tt_mo" if bat else "tour_tt_dong", f"product:{p.code}")
    db.commit(); db.refresh(p)
    return p


def bat_tt_chung(db: Session, u: User, bat: bool, now: datetime | None = None) -> bool:
    from app.models.khach_san_vtd import CaiDatKsVtd
    _quyen(u, VAI_TT_CHUNG, "Chỉ Chủ tịch / TGĐ mở / đóng thanh toán trực tuyến tour")
    r = db.get(CaiDatKsVtd, KHOA_TT)
    if r is None:
        r = CaiDatKsVtd(khoa=KHOA_TT)
        db.add(r)
    r.gia_tri, r.sua_boi, r.sua_luc = ("1" if bat else "0"), u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "tour_tt_chung_mo" if bat else "tour_tt_chung_dong", "tour:chung")
    db.commit()
    return bool(bat)


def ds_don(db: Session, u: User, chi_vat: bool = False) -> list[dict]:
    _quyen(u, VAI_XEM_DON)
    q = select(DonTourOnline).order_by(DonTourOnline.tao_luc.desc()).limit(300)
    ra = []
    for d in db.execute(q).scalars():
        if chi_vat and not d.hoa_don_cong_ty:
            continue
        o = ra_khach(db, d)
        b = db.get(Booking, d.booking_id)
        sa = db.get(User, b.sales_id) if b else None
        ra.append({**o, "id": d.id, "khach_hang": b.customer_name if b else "", "dien_thoai": b.customer_phone if b else "",
                   "sales": sa.full_name if sa else "", "email_loi": d.email_loi, "hoa_don_da_xuat": d.hoa_don_da_xuat,
                   "hoa_don_xuat_boi": d.hoa_don_xuat_boi})
    return ra


def xuat_vat(db: Session, u: User, don_id: int, now: datetime | None = None) -> DonTourOnline:
    _quyen(u, VAI_VAT, "Chỉ Kế toán đánh dấu đã xuất hóa đơn GTGT")
    d = db.get(DonTourOnline, don_id)
    if d is None or not d.hoa_don_cong_ty:
        raise LoiTour("Đơn này không có yêu cầu hóa đơn công ty", 404)
    d.hoa_don_da_xuat, d.hoa_don_xuat_boi, d.hoa_don_xuat_luc = True, u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "tour_online_xuat_vat", f"booking:{d.ma}", after=d.hoa_don_cong_ty)
    db.commit(); db.refresh(d)
    return d
