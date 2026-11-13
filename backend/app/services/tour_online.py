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
# TR-2 (03/11/2026): hai trang danh sách chỉ in vài tour mỗi miền rồi để nút «Xem thêm» → /vn/tour/area/?area=N, mỗi
# khu lại chia trang (&page=K). Chỉ đọc hai trang đầu thì màn ghép thấy 57/105 tour đang bán — phần còn lại không ai ghép.
WEB_KHU = "https://www.vietourist.com.vn/vn/tour/area/?area={khu}&page={trang}"
WEB_KHU_TOI_DA_TRANG = 40          # chặn vòng lặp nếu web trả mãi một trang
WEB_KHU_LUONG = 6                  # số khu đọc song song
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


# ── TR-6 (13/11/2026) · SỨC KHOẺ CỦA ĐƯỜNG ĐỌC WEB CŨ ─────────────────────────────────────────
# Chủ tịch chốt 12/11/2026: nội dung tour TIẾP TỤC đọc từ vietourist.com.vn. Quyết định ấy mang
# theo một rủi ro không tự lộ ra: `lam_moi()` nuốt mọi lỗi để cổng vẫn chạy bằng bản cũ —
#
#     except Exception as ex:   # web chính chậm / đổi cấu trúc: cổng vẫn chạy bằng bản cũ
#
# — đúng và nên thế, NHƯNG hệ quả là ngày web cũ đổi bố cục HTML, bộ bóc tách chết ÂM THẦM. Khách
# vẫn thấy trang, chỉ là thấy bản chụp của nhiều tuần trước, và không ai biết. Lỗi có được ghi
# vào `noi_dung_web["loi"]`, nhưng trước đợt này KHÔNG MÀN HÌNH NÀO ĐỌC CỘT ẤY.
#
# Hàm này là chỗ đọc. CHỈ ĐỌC, không gọi mạng, không sửa một dòng nào — nên gọi bao nhiêu lần
# cũng được và không bao giờ làm hỏng cái nó đang đo.
#
# KHÔNG TỰ ĐẶT NGƯỠNG «BAO LÂU LÀ CŨ». Nó lấy đúng `WEB_CU_GIO` mà `can_lam_moi()` đang dùng, rồi
# nhân đôi: quá HAI kỳ làm mới mà vẫn chưa đọc lại nghĩa là việc làm mới không chạy, chứ không
# phải mới tới hạn. Viết lại một con số thứ hai ở đây là tạo ra hai định nghĩa «cũ», và hai bản
# thì sớm muộn lệch — bài học KN-1 chép lại ở `ho_so_hdv.py`.

def suc_khoe_doc_web(db: Session, now: datetime | None = None) -> dict:
    """Đường đọc nội dung từ vietourist.com.vn còn sống không, và tour nào đang thiếu ảnh.

    Trả về SỐ ĐẾM và DANH SÁCH MÃ TOUR, không trả nội dung — đây là cửa cho người vận hành nhìn
    một cái biết đường đọc còn chạy không, không phải cửa đọc dữ liệu tour.
    """
    now = now or datetime.now()
    han_cu = timedelta(hours=WEB_CU_GIO * 2)

    sps = _sp_hien(db)
    chua_ghep, chua_doc, hong, qua_han, khong_anh = [], [], [], [], []
    cu_nhat: str | None = None

    for p in sps:
        nd = p.noi_dung_web or {}

        if not (p.link_web or "").strip():
            chua_ghep.append(p.code)
            continue                                  # chưa ghép link thì không có gì để đo tiếp

        if not nd:
            chua_doc.append(p.code)
            continue                                  # đã ghép nhưng chưa đọc lần nào

        if (nd.get("loi") or "").strip():
            hong.append({"ma": p.code, "ten": p.name, "loi": str(nd.get("loi"))[:200],
                         "thu_luc": nd.get("thu_luc") or None})

        moc = nd.get("cap_nhat_luc")
        if moc:
            if cu_nhat is None or moc < cu_nhat:
                cu_nhat = moc
            try:
                if now - datetime.fromisoformat(moc) > han_cu:
                    qua_han.append({"ma": p.code, "ten": p.name, "cap_nhat_luc": moc})
            except ValueError:
                # Mốc không đọc được là một kiểu hỏng riêng, KHÔNG phải «quá hạn». Gộp vào quá
                # hạn là nói sai nguyên nhân cho người đi sửa.
                hong.append({"ma": p.code, "ten": p.name, "loi": f"mốc thời gian không đọc được: {moc}",
                             "thu_luc": nd.get("thu_luc") or None})

        # THIẾU ẢNH đo ở đây, cùng một lượt duyệt. Trên trang bán tour, thẻ không ảnh gần như
        # không bán được — và nguồn ảnh là web cũ, nên nó thuộc đúng phép đo này.
        if not (nd.get("anh") or []):
            khong_anh.append({"ma": p.code, "ten": p.name})

    da_doc = len(sps) - len(chua_ghep) - len(chua_doc)
    return {
        "tong_san_pham": len(sps),
        "chua_ghep_link": {"so": len(chua_ghep), "ma": chua_ghep[:50]},
        "chua_doc_lan_nao": {"so": len(chua_doc), "ma": chua_doc[:50]},
        "da_doc": da_doc,
        "doc_hong": {"so": len(hong), "ds": hong[:50]},
        "qua_han_lam_moi": {"so": len(qua_han), "ds": qua_han[:50], "nguong_gio": WEB_CU_GIO * 2},
        "khong_co_anh": {"so": len(khong_anh), "ds": khong_anh[:50]},
        # RỖNG khác 0: chưa sản phẩm nào đọc được thì KHÔNG có bản cũ nhất, chứ không phải bản cũ
        # nhất là hôm nay. Màn hình đọc `null` phải in «chưa có», không in một ngày.
        "ban_cu_nhat": cu_nhat,
        "do_luc": now.isoformat(timespec="minutes"),
    }


# ── TR-6 (13/11/2026) · ĐÁNH GIÁ HIỆN TRÊN TRANG BÁN TOUR ────────────────────────────────────
# Sổ đánh giá đã có từ đợt 25/9/2026 (`DanhGiaSauTour`), nhưng chưa bao giờ hiện ra cổng khách.
# Đây là cửa đọc ấy. BỐN LUẬT, không luật nào được bỏ:
#
#  (1) CHỈ ĐIỂM KHÁCH TỰ CHẤM. `nguon == "khach"`. Điểm nhân viên ghi hộ không lên trang bán
#      hàng — lý do đã viết trong `models/danh_gia.py`: người gọi lại khách chấm thấp chính là
#      người bị chấm.
#  (2) CHỈ NHẬN XÉT ĐƯỢC PHÉP ĐĂNG Ở ĐÚNG CHỖ NÀY. Hỏi `dong_y.cong_khai_duoc(r, "trang_tour")`,
#      không tự dựng lại mệnh đề. Đánh giá thu trước 13/11/2026 mang phạm vi cũ («hồ sơ hướng
#      dẫn viên tại VTOS») nên KHÔNG lọt qua — đúng như đã hứa với khách.
#  (3) KHÔNG KÈM TÊN VÀ THÔNG TIN LIÊN HỆ. Chính câu hỏi đã hứa thế. Hàm này không trả về tên,
#      điện thoại, email, mã đơn hay mã chuyến — không có gì lần ngược ra được một người.
#  (4) ĐIỂM TRUNG BÌNH CŨNG CHỈ CỘNG TỪ NHỮNG DÒNG ẤY. Cộng cả dòng chưa được phép đăng rồi bảo
#      «đây chỉ là con số, không phải lời khách» là lách; con số ấy vẫn sinh ra từ dòng khách
#      chưa cho phép dùng ở đây.
#
# RỖNG LÀ RỖNG, KHÔNG PHẢI 0 SAO. Chưa có đánh giá nào thì `diem_tb` là None và màn hình phải in
# «chưa có đánh giá», không in «0/5» — một tour mới mở mà hiện 0 sao thì thà đừng hiện gì.

def danh_gia_cong_khai(db: Session, pid: int, trang: int = 1, moi_trang: int = 10) -> dict:
    """Đánh giá của khách cho một tour, phần được phép hiện công khai trên trang bán tour."""
    from app.models.danh_gia import DanhGiaSauTour, DongYCongKhai
    from app.services import dong_y as DY

    p = db.get(Product, pid)
    if p is None or p.status != "active":
        raise LoiTour("Không tìm thấy tour")

    # MỌI chuyến của sản phẩm, kể cả đã đi xong — đánh giá chỉ sinh ra SAU chuyến đi, nên không
    # dùng được `_chuyen()` (hàm ấy chỉ lấy chuyến đang mở bán).
    dk = [Tour.product_id == p.id]
    if (p.code or "").strip():
        dk.append(Tour.product_code == p.code)
    tids = [t.id for t in db.execute(select(Tour).where(or_(*dk))).scalars()]
    if not tids:
        return {"diem_tb": None, "so_danh_gia": 0, "nhan_xet": [], "tong_nhan_xet": 0, "trang": 1}

    cap = db.execute(
        select(DanhGiaSauTour, DongYCongKhai)
        .join(DongYCongKhai, DongYCongKhai.danh_gia_id == DanhGiaSauTour.id)
        .where(DanhGiaSauTour.tour_id.in_(tids),
               DanhGiaSauTour.doi_tuong == "tour",
               DanhGiaSauTour.nguon == "khach")
        .order_by(DanhGiaSauTour.tao_luc.desc())).all()

    duoc = [(dg, r) for dg, r in cap if DY.cong_khai_duoc(r, "trang_tour")]

    diem = [dg.diem for dg, _ in duoc if dg.diem is not None]      # bỏ qua ô khách không chấm
    co_chu = [dg for dg, _ in duoc if (dg.nhan_xet or "").strip()]

    t = max(1, int(trang or 1))
    dau = (t - 1) * moi_trang
    return {
        "diem_tb": round(sum(diem) / len(diem), 1) if diem else None,
        "so_danh_gia": len(diem),
        "tong_nhan_xet": len(co_chu),
        "trang": t,
        "moi_trang": moi_trang,
        # Chỉ hai thứ: lời khách và tháng. Không tên, không liên hệ, không mã đơn, không mã chuyến.
        "nhan_xet": [{"diem": dg.diem, "noi_dung": dg.nhan_xet.strip(),
                      "thang": dg.tao_luc.strftime("%m/%Y") if dg.tao_luc else None}
                     for dg in co_chu[dau:dau + moi_trang]],
    }


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


def so_ngay_sp(p: Product) -> int | None:
    """Số ngày của một sản phẩm crm, đọc theo thứ tự tin cậy: cột `days` → tên → `length_text`.

    Đọc bằng `getattr` có mặc định, KHÔNG phải vì sản phẩm thật thiếu cột — mà vì hàm này được
    gọi từ `thieu_noi_dung`, nơi các vòng khác đã dựng sẵn phép thử bằng bản ghi RÚT GỌN chỉ mang
    đúng mấy trường chúng cần (`test_p1_01_5`). Thêm một trường bắt buộc vào đường ấy là bắt vòng
    khác sửa phép thử của họ cho vừa ý vòng này — và một phép thử bị sửa để hết đỏ là một phép
    thử yếu đi. Thiếu trường thì trả `None`, và `None` nghĩa là «không biết», tức không cảnh báo.
    """
    return (getattr(p, "days", None) or _so_ngay(getattr(p, "name", "") or "")
            or _so_ngay(getattr(p, "length_text", "") or ""))


def _hop_ngay(nw: int | None, np_: int | None) -> bool:
    """Hai bên có thể ghép với nhau về ĐỘ DÀI không? Chỉ bên nào ĐỌC ĐƯỢC mới bị xét."""
    return not (nw and np_) or nw == np_


def _diem_khop(tw: set[str], tp: set[str]) -> float:
    """0..1. Trộn BAO PHỦ (bao nhiêu phần tên web nằm trong tên sản phẩm) với Jaccard.

    Chỉ Jaccard thì thiên vị hai tên dài bằng nhau; tên trên web luôn dài hơn vì mang thêm
    «Tour Du Lịch», mùa, năm. Bao phủ gỡ đúng chỗ đó, Jaccard giữ cho nó không nhận bừa một tên
    web quá ngắn. 0.6/0.4 là tỉ lệ đo trên 596 tour web × 380 sản phẩm ngày 13/11/2026.
    """
    if not tw or not tp:
        return 0.0
    g = len(tw & tp)
    return 0.6 * (g / len(tw)) + 0.4 * (g / len(tw | tp))


def goi_y_ghep(web: list[dict], sps: list[Product]) -> list[dict]:
    """Gợi ý sản phẩm crm cho từng tour web. Chỉ GỢI Ý — người xác nhận mới ghép.

    TR-11 (13/11/2026) · SỐ NGÀY NAY LÀ ĐIỀU KIỆN LOẠI, KHÔNG PHẢI CỘNG ĐIỂM — và đây là chỗ
    sửa quan trọng nhất của vòng này, vì bản cũ gợi ý SAI đúng vào ca điểm cao nhất.
    ĐO ĐƯỢC ngày 13/11/2026 trên dữ liệu thật: web cũ có **20 tour Singapore – Malaysia**. Với
    `SM001` («HÀ NỘI - SINGAPORE - MALAYSIA 5N4D»), bản cũ chấm **1.00 — điểm tuyệt đối** cho
    trang «Singapore - Malaysia 4 NGÀY 3 ĐÊM Khởi Hành Từ Hà Nội», trong khi bản đúng
    «5 Ngày 4 Đêm KH Từ Hà Nội» nằm ngay cạnh. Lý do: hai tên có cùng bộ từ (`_tu` đã lọc bỏ
    «5n4d»), nên khác biệt DUY NHẤT giữa đúng và sai là số ngày — mà số ngày chỉ được cộng 0.15.
    Một khoản thưởng nhỏ không bao giờ thắng nổi một tên khớp hơn nửa từ.
    Hậu quả nếu ghép theo gợi ý ấy KHÔNG phải là xấu mặt: khách đặt tour 5 ngày rồi đọc lịch
    trình, bảng giá và «bao gồm» của tour 4 ngày — một lời hứa sai với người đã trả tiền.
    Nên: đọc được số ngày ở CẢ HAI bên mà lệch nhau thì LOẠI HẲN, không chấm điểm.
    """
    ra = []
    for w in web:
        tw, nw = _tu(w["ten"]), _so_ngay(w["ten"])
        tot = None
        for p in sps:
            np_ = so_ngay_sp(p)
            if not _hop_ngay(nw, np_):
                continue                       # lệch độ dài: không phải ứng viên, dù tên giống hệt
            diem = _diem_khop(tw, _tu(p.name))
            if not diem:
                continue
            if nw and np_:
                diem += 0.15                   # cùng độ dài ĐỌC ĐƯỢC ở cả hai bên: chắc hơn hẳn
            if tot is None or diem > tot[0]:
                tot = (diem, p)
        g = {"pid": tot[1].id, "ma": tot[1].code, "ten": tot[1].name, "diem": round(tot[0], 2)} if tot and tot[0] >= 0.25 else None
        ra.append({**w, "goi_y": g})
    return ra


# Dưới ngưỡng này thì không đưa ra làm ứng viên — bày một gợi ý tồi tốn thì giờ người xem hơn là
# không bày gì. 0.45 là mức đo được: dưới nó, các cặp trên dữ liệu thật đều là trùng điểm đến chứ
# không phải trùng tour (ví dụ mọi tour Đà Lạt khớp nhau ở đúng chữ «đà lạt»).
NGUONG_UNG_VIEN = 0.45
SO_UNG_VIEN = 3


def goi_y_web(web: list[dict], sps: list[Product], da_ghep: set[str] | None = None,
              so: int = SO_UNG_VIEN) -> list[dict]:
    """CHIỀU NGƯỢC LẠI: mỗi SẢN PHẨM chưa ghép → vài trang web hợp nhất, để người ghép bấm chọn.

    VÌ SAO PHẢI CÓ CHIỀU NÀY. `goi_y_ghep` đi từ WEB sang SẢN PHẨM: với mỗi tour web nó chọn một
    sản phẩm khớp nhất. Một sản phẩm không phải «khớp nhất» của tour web nào thì không có gợi ý
    nào trỏ tới nó — người của Điều hành thấy nó nằm trong mục «Chưa ghép web» nhưng phải TỰ DÒ
    trong 596 trang để tìm trang của nó. Đo ngày 13/11/2026: **22 sản phẩm có chuyến đang mở bán
    mà chưa ghép link**, nên cổng khách hiện chúng KHÔNG CÓ MỘT TẤM ẢNH NÀO — không phải vì
    thiếu ảnh, mà vì chưa có chỗ nào để đọc ảnh về.

    Trả về mỗi sản phẩm kèm tối đa `so` ứng viên đã xếp hạng. KHÔNG tự ghép: ghép là việc của
    người, vì trên dữ liệu thật chỉ khoảng một phần tư số sản phẩm có ứng viên đủ chắc, phần còn
    lại tên trên crm và trên web đặt khác hẳn nhau («ĐÀ LẠT MỘNG MƠ» ↔ «Đà Lạt 3 Ngày 2 Đêm:
    Thành Phố Ngàn Hoa») và chỉ người làm tour mới biết trang nào là trang nào.
    """
    da = set(da_ghep or ())
    ra = []
    for p in sps:
        if (p.link_web or "").strip():
            continue
        tp, np_ = _tu(p.name or ""), so_ngay_sp(p)
        tp = tp | _tu(p.diem_den or "")        # tên crm hay ngắn; điểm đến bù đúng chỗ thiếu
        cand = []
        for w in web:
            if w["url"] in da:
                continue                       # trang đang thuộc về sản phẩm khác — không bày
            nw = _so_ngay(w["ten"])
            if not _hop_ngay(nw, np_):
                continue
            diem = _diem_khop(_tu(w["ten"]), tp)
            if nw and np_:
                diem += 0.15
            if diem >= NGUONG_UNG_VIEN:
                cand.append({"url": w["url"], "ten": w["ten"], "anh": w.get("anh") or "",
                             "so_ngay": nw, "diem": round(diem, 2)})
        cand.sort(key=lambda x: -x["diem"])
        ra.append({"pid": p.id, "ma": p.code, "ten": p.name, "so_ngay": np_,
                   "ung_vien": cand[:so],
                   # «chắc» = điểm cao VÀ bỏ xa ứng viên nhì. Một ứng viên 0.9 đứng cạnh một ứng
                   # viên 0.88 thì KHÔNG chắc — đó là hai biến thể của cùng một tuyến, và chọn
                   # bừa một trong hai là đúng cái sai mà vòng này sinh ra để chặn.
                   "chac": bool(cand) and cand[0]["diem"] >= 0.80
                           and (len(cand) == 1 or cand[0]["diem"] - cand[1]["diem"] >= 0.15)})
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


def _anh_tai(db: Session, pids: list[int]) -> dict[int, list[str]]:
    """TR-8: đường ảnh phòng sản phẩm đã tải lên, MỘT lượt truy vấn cho cả danh sách.
    Nhập trong hàm vì `anh_tour` nhập ngược lại tệp này (ma trận quyền dùng chung)."""
    try:
        from app.services import anh_tour as AT
        return AT.duong_cong(db, pids)
    except Exception:
        return {}                      # thiếu bảng (bản cũ chưa chuyển hệ) thì cổng vẫn chạy bằng ảnh web


def the_san_pham(p: Product, chuyen: list[tuple[Tour, int]], so_khach: int, hom_nay: date, chung: bool,
                 anh_tai: list[str] | None = None) -> dict:
    """TR-8 (13/11/2026): `anh_tai` là ảnh phòng sản phẩm TẢI LÊN VTOS. Chủ tịch chốt cùng ngày:
    ảnh tải lên ĐỨNG TRƯỚC, ảnh đọc từ vietourist.com.vn nối sau — không xoá ảnh web nào, nên vá
    được tour nào hay tour ấy mà không phải chờ đủ bộ. Tham số chứ không tự truy vấn: hàm này
    chạy trong vòng lặp 85 sản phẩm, để nó tự hỏi cơ sở dữ liệu là 85 lượt truy vấn."""
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
            "it_cho": any(c["it_cho"] for c in du), "anh": (list(anh_tai or []) + list(nd.get("anh") or []))[:8], "noi_bat": list(p.noi_bat or [])[:5],
            "mo_thanh_toan": mo_thanh_toan(None, p, chung), "co_noi_dung": bool(nd.get("lich_trinh") or p.program),
            # TR-3: tour ghép đã ghép web nhưng chưa có chuyến mở bán → vẫn hiện, khách gửi yêu cầu giữ chỗ
            "chua_co_lich": loai(p) == "ghep" and not ds,
            "gia_tham_khao": (nd.get("gia_web") or None) if loai(p) == "ghep" and not ds else None}


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
    anh_tai = _anh_tai(db, [p.id for p in sps])     # TR-8: MỘT lượt truy vấn cho cả danh sách
    k0 = _khong_dau(q.strip())
    the, noi_ds = [], set()
    for p in sps:
        ds = ch.get(p.id, [])
        if loai(p) == "ghep" and not ds and not p.link_web:
            continue                                     # tour ghép chưa có chuyến: chỉ hiện khi đã ghép web (TR-3)
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
        the.append(the_san_pham(p, ds, nl + te, hom_nay, chung, anh_tai.get(p.id)))
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


_MUC_BAO = re.compile(r"^(gia\s*(tour\s*)?)?bao\s*gom\b")
_MUC_KHONG = re.compile(r"^(gia\s*(tour\s*)?)?khong\s*bao\s*gom\b")
_MUC_QD = re.compile(r"^(quy\s*dinh|dieu\s*kien|chinh\s*sach|luu\s*y|ghi\s*chu|thanh\s*toan|huy\s*tour|dieu\s*khoan|phu\s*thu\s*(chung|khac)?\s*:?$|"
                     r"truong\s*hop\s*huy|hoan\s*huy)")
_MUC_CT = re.compile(r"^(chuong\s*trinh|lich\s*trinh|hanh\s*trinh)\b")


def tach_muc(van_ban: str) -> dict:
    """P1-01 (Chủ tịch chọn «Tự tách đúng mục», 09/11/2026): ô «Chương trình» của sản phẩm trên crm hay chứa lẫn
    «GIÁ TOUR BAO GỒM / KHÔNG BAO GỒM / quy định» và dòng lặp (tour 6591 Đà Lạt – Vĩnh Hy). Máy tách theo dòng tiêu đề
    mục — chỉ dòng NGẮN (< 80 ký tự) mới là tiêu đề — thành {chuong_trinh, bao_gom, khong_bao_gom, quy_dinh}; mỗi mục bỏ
    dòng lặp (so không dấu, không phân biệt hoa thường). Không sửa dữ liệu gốc; chỉ là cách HIỆN."""
    muc = {"ct": [], "bao": [], "khong": [], "qd": []}
    da: dict[str, set] = {k: set() for k in muc}
    o = "ct"
    for d in (van_ban or "").replace("\r", "").split("\n"):
        t = _sach(_KHONG_RONG.sub("", d))
        if not t:
            if o == "ct" and muc["ct"] and muc["ct"][-1] != "":
                muc["ct"].append("")
            continue
        kd = re.sub(r"^[^a-z0-9]+", "", _khong_dau(t))
        if len(t) < 80:
            if _MUC_KHONG.match(kd):
                o = "khong"; continue                                         # noqa: E702
            if _MUC_BAO.match(kd):
                o = "bao"; continue                                           # noqa: E702
            if _MUC_QD.match(kd) and (t.rstrip().endswith(":") or _la_tieu_de_hoa(t)):   # «Lưu ý: mang áo» trong ngày không phải tiêu đề
                o = "qd"
            elif _MUC_CT.match(kd) or (_NGAY_RE.match(t) and o != "ct"):
                o = "ct"
        dong = re.sub(r"^[-•·*✓✔+]\s*", "", t) if o in ("bao", "khong") else t
        khoa = re.sub(r"\s+", " ", _khong_dau(dong))
        if not dong or khoa in da[o]:
            continue
        da[o].add(khoa)
        muc[o].append(dong[:300] if o in ("bao", "khong") else dong)
    ct = "\n".join(muc["ct"]).strip()
    return {"chuong_trinh": ct, "bao_gom": muc["bao"][:40], "khong_bao_gom": muc["khong"][:40],
            "quy_dinh": "\n".join(muc["qd"]).strip()[:4000]}


# ── TR-7b (13/11/2026) · SỐ GIỮ CHỖ KHÔNG ĐƯỢC LỌT RA MÀN KHÁCH ─────────────────────────────
# KS-71 mục G4 đo được trên bản chạy thật: trang chi tiết in «Chi phí phụ thu phòng đơn:
# 00.000 VNĐ/khách». Đó là số giữ chỗ của người soạn bài trên vietourist.com.vn, chưa ai điền.
#
# VÌ SAO PHẢI CHẶN Ở ĐÂY CHỨ KHÔNG ĐỢI SỬA BÊN WEB CŨ. Nội dung đọc về từ web cũ (Chủ tịch
# chốt mục 12 của KS-71), nên mọi lỗi soạn bài bên ấy chảy thẳng ra màn khách. Một con số giả
# nằm cạnh giá thật làm hỏng lòng tin vào CẢ trang — khách không biết số nào mới là thật.
#
# LUẬT: dòng nào mang số tiền toàn số 0 («00.000», «000.000») hoặc còn chỗ trống chưa điền
# («X.XXX», «____») thì KHÔNG hiện cho khách, VÀ sản phẩm bị đánh dấu thiếu nội dung để phòng
# sản phẩm thấy mà đi sửa bên web cũ. Giấu đi mà không ai biết thì sáu tháng sau vẫn còn đó.
#
# KHÔNG tự đoán số đúng và KHÔNG tự điền — ranh giới Chủ tịch chốt 09/9/2026: Claude viết cấu
# trúc, người của anh nhập số.
# CÁCH VIẾT ĐẦU TIÊN CỦA EM SAI, VÀ SAI KIỂU NGUY HIỂM — ghi lại để không ai viết lại như thế.
# Em bắt thẳng mẫu «0{1,3}.000». Nó khớp luôn phần đuôi của «1.000.000», tức một tour giá đúng
# một triệu sẽ bị GIẤU khỏi màn khách. Bộ lọc dựng để chống số giả mà lại xoá số thật thì tệ
# hơn là không lọc. Phép thử bắt được trước khi đẩy.
#
# Cách đúng: tách từng SỐ TIỀN trọn vẹn rồi hỏi «mọi chữ số của nó có phải đều là 0 không».
_TIEN = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3})+(?![\d.,])")
_CHO_TRONG = re.compile(r"(?<![0-9A-Za-zÀ-ỹ])[Xx]{1,3}[.,][Xx]{3}(?![0-9A-Za-zÀ-ỹ])|_{3,}")


def co_so_ao(s: str) -> bool:
    """Dòng này có số tiền giữ chỗ chưa ai điền không?"""
    s = s or ""
    if _CHO_TRONG.search(s):
        return True
    return any(set(m.group().replace(".", "").replace(",", "")) == {"0"} for m in _TIEN.finditer(s))


def _loc_so_ao(dong: list[str]) -> tuple[list[str], int]:
    """Trả (các dòng SẠCH, số dòng đã bỏ). Giữ nguyên thứ tự."""
    sach = [d for d in dong if not co_so_ao(d)]
    return sach, len(dong) - len(sach)


def _quy_dinh_sach(s: str) -> tuple[str, int]:
    sach, bo = _loc_so_ao((s or "").split("\n"))
    return "\n".join(sach).strip(), bo


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
    ct = tach_muc(p.program or "")["chuong_trinh"]                     # P1-01: bỏ phần bao gồm / quy định lẫn vào
    tn = tach_ngay(ct)
    if tn:
        return {"nguon": "san_pham", "ngay": [{**x, "bua": [], "khach_san": ""} for x in tn], "van_ban": ""}
    gt = ((p.noi_dung_web or {}).get("gioi_thieu") or "").strip()   # TR-1c: bài giới thiệu trên web trước văn bản sản phẩm
    if gt:
        return {"nguon": "web_gioi_thieu", "ngay": [], "van_ban": gt[:8000]}
    return {"nguon": "van_ban", "ngay": [], "van_ban": ct[:8000]}


def chi_tiet(db: Session, pid: int, nguoi_lon: int = 2, tre_em: int = 0, hom_nay: date | None = None) -> dict:
    hom_nay = hom_nay or _hom_nay()
    p = db.get(Product, pid)
    if p is None or p.status != "active":
        raise LoiTour("Tour này không còn trên cổng", 404)
    nl, te = max(1, int(nguoi_lon or 1)), max(0, int(tre_em or 0))
    ds = _chuyen(db, [p], hom_nay).get(p.id, [])
    if loai(p) == "ghep" and not ds and not p.link_web:
        raise LoiTour("Tour này hiện chưa có ngày khởi hành mở bán — xem tour khác hoặc gửi yêu cầu", 404)
    chung = tt_chung(db)
    anh_tai = _anh_tai(db, [p.id]).get(p.id) or []
    the = the_san_pham(p, ds, nl + te, hom_nay, chung, anh_tai)
    nd = p.noi_dung_web or {}
    tm = tach_muc(p.program or "")                                      # P1-01: web trống thì lấy mục tách từ chương trình
    chuyen = [_chuyen_out(t, con, nl + te, hom_nay) for t, con in ds]
    # TR-7b: lọc số giữ chỗ TRƯỚC khi trả cho khách. `bo_so_ao` đếm số dòng đã bỏ — cửa
    # `/tour-online` của nhân viên đọc con số ấy để biết sản phẩm nào còn số giả trên web cũ.
    bao, bo1 = _loc_so_ao(list(nd.get("bao_gom") or tm["bao_gom"]))
    khong, bo2 = _loc_so_ao(list(nd.get("khong_bao_gom") or tm["khong_bao_gom"]))
    qd, bo3 = _quy_dinh_sach(nd.get("quy_dinh") or tm["quy_dinh"])
    return {**the, "chuyen": chuyen, "lich_trinh": lich_trinh(db, p, chuyen[0]["tour_id"] if chuyen else None),
            "anh": anh_tai + list(nd.get("anh") or []), "bao_gom": bao,
            "khong_bao_gom": khong, "bo_so_ao": bo1 + bo2 + bo3,
            "quy_dinh": qd, "bang_gia_web": list(nd.get("bang_gia") or []),
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
        "Tour ghép chưa có lịch — khách xin giữ chỗ" if p and loai(p) == "ghep" else "",           # TR-3
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

THIEU_ND = {"anh": "Thiếu ảnh", "lich": "Chưa có lịch theo ngày", "bao_gom": "Thiếu giá bao gồm", "tre_em": "Thiếu giá trẻ em",
            "gia_ao": "Còn số tiền chưa điền trên web",
            "lech_ngay": "Lịch trên web LỆCH số ngày với tour"}


def thieu_noi_dung(p: Product, chuyen: list[tuple[Tour, int]], co_ct_chuyen: bool = False,
                   co_anh_tai: bool = False) -> list[str]:
    """P1-01 (Chủ tịch duyệt 09/11/2026): khách đang thấy gì trên kh.vietourist.vn cho sản phẩm này — thiếu mục nào.
    Cùng nguồn với chi_tiet(): ảnh web; lịch theo ngày (chương trình chuyến → web → chương trình sản phẩm đã tách mục);
    bao gồm (web → mục tách từ chương trình → «dịch vụ»); giá trẻ em ở MỌI chuyến đang mở bán. Chỉ báo, không chặn."""
    nd = p.noi_dung_web or {}
    tm = tach_muc(p.program or "")
    ra = []
    # TR-8: tour đã có ảnh phòng sản phẩm tải lên thì KHÔNG còn thiếu ảnh, dù web cũ vẫn trống.
    if not (nd.get("anh") or co_anh_tai):
        ra.append("anh")
    if not (co_ct_chuyen or nd.get("lich_trinh") or tach_ngay(tm["chuong_trinh"])):
        ra.append("lich")
    if not (nd.get("bao_gom") or tm["bao_gom"] or (p.services or "").strip()):
        ra.append("bao_gom")
    if any(not t.price_chd for t, _con in chuyen):
        ra.append("tre_em")
    # TR-7b: màn khách đã LỌC các dòng mang số giữ chỗ; chỗ này là để người của anh biết mà đi
    # sửa bên vietourist.com.vn. Lọc mà không báo thì lỗi nằm im mãi.
    if any(co_so_ao(d) for d in list(nd.get("bao_gom") or tm["bao_gom"])
           + list(nd.get("khong_bao_gom") or tm["khong_bao_gom"])
           + (nd.get("quy_dinh") or tm["quy_dinh"] or "").split("\n")):
        ra.append("gia_ao")
    # TR-11 (13/11/2026) · GHÉP NHẦM ĐỘ DÀI — chỗ hỏng mà màn hình CŨ KHÔNG THỂ THẤY.
    #
    # Tất cả các phép kiểm trên đây hỏi «có hay không có». Không phép nào hỏi «có ĐÚNG không».
    # Nên một sản phẩm ghép vào trang web của một tour KHÁC ĐỘ DÀI vẫn được chấm «Đủ nội dung»,
    # và không ai biết, kể cả người đang nhìn thẳng vào dòng ấy.
    #
    # ĐO NGÀY 13/11/2026, trên 120 sản phẩm đã ghép link (88 sản phẩm đọc được số ngày cả hai
    # bên): **7 sản phẩm lệch**. Hai trong số đó ĐANG MỞ BÁN, nên khách đang đọc nhầm ngay lúc đo:
    #   · TL001 — cổng ghi «2 NGÀY 1 ĐÊM», 2 chuyến mở, nội dung đọc từ trang La Ngâu **3N2Đ**.
    #     (Web cũ chỉ có đúng một trang La Ngâu và nó là 3N2Đ — tour này không có trang đúng để
    #     ghép, nên lối ra là gỡ link rồi tải ảnh thẳng vào album.)
    #   · JP0013 — cổng ghi 6N5Đ, 3 chuyến mở, trang đã ghép có ĐÚNG 5 ngày lịch trình.
    #     Màn hình hôm ấy ghi dòng JP0013 là «Đủ nội dung».
    #
    # Chỉ báo khi ĐỌC ĐƯỢC số ngày ở cả hai bên — suy đoán thêm ở đây là đẻ ra báo động giả, mà
    # một hàng rào kêu oan vài lần là một hàng rào người ta thôi đọc.
    # Chỉ hỏi số ngày của sản phẩm KHI web đã đọc được lịch — không có lịch thì cảnh báo «lich»
    # ở trên đã lo, và tính thêm ở đây là làm việc thừa trên mỗi dòng của 380 sản phẩm.
    nw = len(nd.get("lich_trinh") or [])
    if nw and (np_ := so_ngay_sp(p)) and nw != np_:
        ra.append("lech_ngay")
    return ra


def _sp_vtos(db: Session, p: Product, so_chuyen: int, thieu: list[str] | None = None, so_anh_tai: int = 0) -> dict:
    nd = p.noi_dung_web or {}
    return {"id": p.id, "ma": p.code, "ten": p.name, "tour_type": p.tour_type, "loai": loai(p), "nuoc_ngoai": la_nuoc_ngoai(p),
            "diem_den": p.diem_den or "", "diem_den_suy": diem_den(p), "noi_bat": p.noi_bat or [], "wellness": bool(p.wellness),
            "phuong_tien_ds": p.phuong_tien_ds or [], "phuong_tien_suy": phuong_tien(p), "transport": p.transport or "",
            "mo_thanh_toan": bool(p.mo_thanh_toan), "link_web": p.link_web or "", "so_chuyen": so_chuyen,
            # TR-11: để màn hình nói ĐƯỢC «6 ngày ↔ web 5 ngày» chứ không chỉ gắn một cái nhãn đỏ.
            # Một cảnh báo không kèm hai con số thì người đọc phải tự đi tìm, và phần lớn sẽ không đi.
            "so_ngay": so_ngay_sp(p),
            "web": {"cap_nhat_luc": nd.get("cap_nhat_luc"), "loi": nd.get("loi") or "", "so_anh": len(nd.get("anh") or []),
                    "so_ngay": len(nd.get("lich_trinh") or []), "so_bao_gom": len(nd.get("bao_gom") or []), "ten": nd.get("ten") or "",
                    "anh_dau": (nd.get("anh") or [None])[0]},
            "so_anh_tai": so_anh_tai,                                 # TR-8: ảnh phòng sản phẩm đã tải lên VTOS
            "co_chuong_trinh": bool((p.program or "").strip()), "thieu": thieu or []}


def ds_vtos(db: Session, u: User) -> dict:
    _quyen(u, VAI_XEM)
    sps = _sp_hien(db)
    ch = _chuyen(db, sps, _hom_nay())
    from app.models.chuong_trinh import ChuongTrinhNgay                  # P1-01: chuyến nào đã có chương trình riêng
    tids = [t.id for v in ch.values() for t, _ in v]
    co_ct = set(db.execute(select(ChuongTrinhNgay.tour_id).where(ChuongTrinhNgay.tour_id.in_(tids or [0]))).scalars()) if tids else set()
    anh_sp = _anh_tai(db, [p.id for p in sps])                           # TR-8: ảnh phòng sản phẩm đã tải
    return {"san_pham": [_sp_vtos(db, p, len(ch.get(p.id, [])),
                                  thieu_noi_dung(p, ch.get(p.id, []), any(t.id in co_ct for t, _ in ch.get(p.id, [])),
                                                   bool(anh_sp.get(p.id))), len(anh_sp.get(p.id) or [])) for p in sps],
            "thieu_nd": THIEU_ND, "tt_chung": tt_chung(db),
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


def phan_tich_khu(html: str) -> list[int]:
    """TR-2: số khu ở các nút «Xem thêm» (/vn/tour/area/?area=N) trên trang danh sách — chỉ nhận số, tự dựng lại link
    trên tên miền Vietourist (không đi theo href thô)."""
    ra: list[int] = []
    for m in re.finditer(r"/vn/tour/area/?\?area=(\d{1,4})(?![\d&])", html or ""):
        k = int(m.group(1))
        if k not in ra:
            ra.append(k)
    return ra


def _doc_khu(khu: int, da: set[str]) -> tuple[list[dict], str]:
    """Đọc lần lượt các trang của MỘT khu tới khi trang không còn tour mới (hoặc chạm trần)."""
    ra: list[dict] = []
    thay = set(da)
    for trang in range(1, WEB_KHU_TOI_DA_TRANG + 1):
        url = WEB_KHU.format(khu=khu, trang=trang)
        try:
            ds = phan_tich_ds(FETCH(url).decode("utf-8", "replace"), url)
        except Exception as ex:   # noqa: BLE001
            return ra, f"khu {khu} trang {trang}: {ex}"[:200]
        moi = [o for o in ds if o["url"] not in thay]
        if not moi:
            break
        for o in moi:
            thay.add(o["url"])
            ra.append(o)
    return ra, ""


def doc_ds_web() -> tuple[list[dict], list[str]]:
    """Mọi tour đang có trên web: hai trang danh sách + mọi khu «Xem thêm» kèm phân trang (TR-2)."""
    from concurrent.futures import ThreadPoolExecutor
    web: dict[str, dict] = {}
    loi: list[str] = []
    khu: list[int] = []
    for url in WEB_DS:
        try:
            html = FETCH(url).decode("utf-8", "replace")
        except Exception as ex:   # noqa: BLE001
            loi.append(f"{url}: {ex}"[:200])
            continue
        for o in phan_tich_ds(html, url):
            web.setdefault(o["url"], o)
        khu += [k for k in phan_tich_khu(html) if k not in khu]
    if khu:
        da = set(web)
        with ThreadPoolExecutor(max_workers=WEB_KHU_LUONG) as ex:
            for ds, l in ex.map(lambda k: _doc_khu(k, da), khu):
                for o in ds:
                    web.setdefault(o["url"], o)
                if l:
                    loi.append(l)
    return list(web.values()), loi


def ds_web(db: Session, u: User) -> list[dict]:
    """Tour đang có trên vietourist.com.vn (hai trang danh sách + các khu «Xem thêm», TR-2) + gợi ý sản phẩm crm để
    Điều hành xác nhận ghép."""
    _quyen(u, VAI_SUA_CONG + VAI_GHEP)
    web, loi = doc_ds_web()
    sps = _sp_hien(db)
    da = {p.link_web: p for p in sps if p.link_web}
    ra = goi_y_ghep(web, sps)
    for o in ra:
        g = da.get(o["url"])
        o["da_ghep"] = {"pid": g.id, "ma": g.code, "ten": g.name} if g else None
    if loi and not ra:
        raise LoiTour("Không đọc được danh sách tour trên web: " + "; ".join(loi), 502)
    return ra


def ds_goi_y_nguoc(db: Session, u: User) -> dict:
    """TR-11 · Danh sách việc cho người ghép: mỗi sản phẩm CHƯA GHÉP kèm vài trang web hợp nhất.

    Xếp sản phẩm ĐANG MỞ BÁN lên trước, vì đó là những tour khách đang nhìn thấy trống ảnh ngay
    lúc này — 22 sản phẩm như thế, đo ngày 13/11/2026.
    Lỗi đọc web KHÔNG làm cửa này hỏng: trả kèm `loi` để màn hình nói ra, còn phần đọc được vẫn
    dùng được. Đọc được một nửa mà biết mình đọc một nửa thì vẫn hơn hẳn không có gì.
    """
    _quyen(u, VAI_SUA_CONG + VAI_GHEP)
    web, loi = doc_ds_web()
    sps = _sp_hien(db)
    da = {p.link_web for p in sps if p.link_web}
    ra = goi_y_web(web, sps, da)
    ch = _chuyen(db, sps, _hom_nay())
    for o in ra:
        o["so_chuyen"] = len(ch.get(o["pid"], []))
    ra.sort(key=lambda o: (-o["so_chuyen"], not o["chac"], o["ma"]))
    return {"san_pham": ra, "so_web": len(web), "loi": loi,
            "nguong": NGUONG_UNG_VIEN, "so_chua_ghep": len(ra),
            "so_chua_ghep_dang_ban": sum(1 for o in ra if o["so_chuyen"])}


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


# ── TR-6b (13/11/2026) · BẬT / ĐÓNG HÀNG LOẠT ────────────────────────────────────────────────
# VÌ SAO CÓ HÀM NÀY — ghi ra vì nó là bài học đắt, không phải một tiện ích cho tiện tay.
#
# 13/11/2026, Chủ tịch yêu cầu mở thanh toán cho cả 380 sản phẩm. Không có cửa hàng loạt, nên
# cách duy nhất là gọi `bat_tt_sp` 380 lần. ĐO ĐƯỢC, hai lần, trên máy chủ thật:
#
#   · 5 luồng song song  → máy chủ 502 sau ~30 giây, VTOS mất API ~5 phút (02:11–02:16).
#   · 1 luồng, nghỉ 400ms → máy chủ VẪN 502 sau ~90 giây, mất API lần nữa (02:21–02:25).
#
# Tức đây KHÔNG phải chuyện đi nhanh hay đi chậm. Mỗi lượt `bat_tt_sp` là một yêu cầu HTTP, một
# `db.commit()` và một dòng nhật ký kiểm toán; máy Render 512MB không nuốt nổi vài trăm lượt như
# thế liên tiếp, dù giãn cỡ nào. Hơn trăm người dùng VTOS bị văng cả hai lần.
#
# Hàm này đổi vài trăm lượt ấy thành MỘT: một truy vấn, một vòng gán, MỘT `commit`, MỘT dòng nhật
# ký mang theo số lượng và bộ lọc.
#
# BA ĐIỀU ÉP:
#  (1) QUYỀN CAO HƠN CỬA MỘT SẢN PHẨM. `bat_tt_sp` cho `VAI_GHEP` (TP Điều hành, TP/GĐ Kinh
#      doanh) — mở một tour là việc thường ngày của họ. Mở CẢ KHO một phát thì khác hẳn về mức:
#      nó là quyết định kinh doanh, nên đòi `VAI_TT_CHUNG` (Chủ tịch / TGĐ), đúng bằng công tắc
#      chung. Dùng lại `VAI_GHEP` ở đây là lặng lẽ nâng quyền của ba vai kia.
#  (2) MỘT DÒNG NHẬT KÝ, CÓ SỐ VÀ CÓ BỘ LỌC. Một thao tác đổi 300 dòng mà không nói nó đổi những
#      gì thì sáu tháng sau không ai dựng lại được chuyện đã xảy ra.
#  (3) TRẢ VỀ SỐ ĐO ĐƯỢC, KHÔNG TRẢ «đã xong». `da_doi` đếm đúng số dòng THỰC SỰ đổi trạng thái —
#      sản phẩm vốn đã mở thì không tính. Gọi lại lần hai phải ra `da_doi = 0`, và đó là cách
#      người bấm biết lần đầu đã ăn.

LOC_HANG_LOAT = {
    "tat_ca": "Tất cả sản phẩm đang hoạt động",
    "co_chuyen": "Chỉ sản phẩm có chuyến đang mở bán",
}


def bat_tt_hang_loat(db: Session, u: User, bat: bool, loc: str = "co_chuyen",
                     hom_nay: date | None = None) -> dict:
    """Mở / đóng thanh toán trực tuyến cho NHIỀU sản phẩm trong MỘT giao dịch."""
    _quyen(u, VAI_TT_CHUNG, "Chỉ Chủ tịch / TGĐ mở / đóng thanh toán hàng loạt")
    if loc not in LOC_HANG_LOAT:
        raise LoiTour(f"Bộ lọc không hợp lệ — chỉ nhận: {', '.join(LOC_HANG_LOAT)}")

    hom_nay = hom_nay or _hom_nay()
    sps = _sp_hien(db)
    if loc == "co_chuyen":
        ch = _chuyen(db, sps, hom_nay)
        sps = [p for p in sps if ch.get(p.id)]

    bat = bool(bat)
    doi = [p for p in sps if bool(p.mo_thanh_toan) is not bat]
    for p in doi:
        p.mo_thanh_toan = bat

    R.audit(db, u.username, u.role,
            "tour_tt_hang_loat_mo" if bat else "tour_tt_hang_loat_dong",
            f"tour-online:{loc}",
            after={"bo_loc": loc, "so_xet": len(sps), "so_doi": len(doi),
                   "ma": [p.code for p in doi][:200]})
    db.commit()                                   # MỘT lần, cho cả lô
    return {"bo_loc": loc, "bo_loc_ten": LOC_HANG_LOAT[loc], "bat": bat,
            "so_xet": len(sps), "da_doi": len(doi)}


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
