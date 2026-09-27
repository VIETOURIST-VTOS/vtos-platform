"""Robot đồng bộ Vietrip chạy phía máy chủ (không cần trình duyệt): đăng nhập app.vietrip.com.vn bằng tài khoản robot
(VIETRIP_PHONE / VIETRIP_PASSWORD trong biến môi trường), kéo dữ liệu theo khoảng ngày rồi nạp qua cùng bộ ánh xạ vietrip.upsert/apply_all.
Dùng cho lịch chạy hằng ngày (GitHub Actions / n8n gọi POST /api/v1/robot/vietrip/sync). Cùng logic với docs/vietrip-sync.js."""
import json, re, threading, time, urllib.request, urllib.parse, http.cookiejar
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import vietrip as VT

BASE = "https://app.vietrip.com.vn"
STATE: dict = {"running": False, "log": [], "started": None, "finished": None, "result": None, "error": ""}


class VietripError(Exception):
    pass


class Client:
    def __init__(self, phone: str, password: str):
        self.cj = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.op.addheaders = [("User-Agent", "Mozilla/5.0 VTOS-robot"), ("Accept", "*/*")]
        self.phone, self.password = phone, password

    def _req(self, path: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 90) -> tuple[int, str]:
        req = urllib.request.Request(BASE + path, data=data, headers=headers or {})
        try:
            with self.op.open(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "ignore")

    def get(self, path: str, timeout: int = 90) -> str:
        st, body = self._req(path, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=timeout)
        if st >= 400: raise VietripError(f"GET {path.split('?')[0]} → {st}")
        return body

    def post_json(self, path: str, payload: dict) -> dict:
        st, body = self._req(path, json.dumps(payload).encode(), {"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"})
        if st >= 400: raise VietripError(f"POST {path} → {st}")
        return json.loads(body)

    def post_form(self, path: str, form: dict) -> str:
        st, body = self._req(path, urllib.parse.urlencode(form).encode(), {"Content-Type": "application/x-www-form-urlencoded", "X-Requested-With": "XMLHttpRequest"})
        if st >= 400: raise VietripError(f"POST {path} → {st}")
        return body

    def login(self):
        st, html = self._req("/signin")
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html) or re.search(r'value="([^"]+)"[^>]*name="__RequestVerificationToken"', html)
        if not m: raise VietripError("Không lấy được token đăng nhập Vietrip")
        st, body = self._req("/signin", urllib.parse.urlencode({"Phone": self.phone, "Password": self.password, "RememberMe": "true", "__RequestVerificationToken": m.group(1), "ReturnUrl": "/"}).encode(),
                             {"Content-Type": "application/x-www-form-urlencoded"})
        # kiểm tra: gọi API cần đăng nhập
        st2, body2 = self._req("/api/users/all", headers={"X-Requested-With": "XMLHttpRequest"})
        if st2 != 200 or not body2.lstrip().startswith(("[", "{")): raise VietripError("Đăng nhập Vietrip thất bại – kiểm tra VIETRIP_PHONE / VIETRIP_PASSWORD")
        return json.loads(body2)


# ---------- phân tích HTML bảng quyết toán / sản phẩm bằng html.parser (không cần thư viện ngoài) ----------
class _Tables(HTMLParser):
    """Thu bảng (tbody tr td) và text thuần; đủ cho bảng quyết toán Vietrip."""
    def __init__(self):
        super().__init__(); self.rows = []; self._row = None; self._cell = None; self.text = []; self._skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self._skip += 1
        if tag == "tr": self._row = []
        if tag == "td" and self._row is not None: self._cell = []
        if tag == "br" and self._cell is not None: self._cell.append("\n")
    def handle_endtag(self, tag):
        if tag in ("script", "style"): self._skip = max(0, self._skip - 1)
        if tag == "td" and self._cell is not None and self._row is not None: self._row.append(" ".join(self._cell).strip()); self._cell = None
        if tag == "tr" and self._row is not None:
            if self._row: self.rows.append(self._row)
            self._row = None
        if tag in ("div", "p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"): self.text.append("\n")
    def handle_data(self, data):
        if self._skip: return
        d = data.strip()
        if not d: return
        if self._cell is not None: self._cell.append(d)
        self.text.append(d + " ")


def _num(s) -> float:
    s = re.sub(r"[^\d.,\-]", "", str(s or ""))
    if not s: return 0.0
    s = s.replace(".", "").replace(",", "") if re.search(r"[.,]\d{3}(\D|$)", s) else s.replace(",", ".")
    try: return float(s)
    except ValueError: return 0.0


def parse_settlement(html: str, tour: dict) -> dict:
    p = _Tables(); p.feed(html); txt = "".join(p.text)
    tt = re.search(r"Tổng thu:\s*([\d.,]+)", txt); tc = re.search(r"Tổng chi:\s*([\d.,]+)", txt)
    lines = []
    for c in p.rows:
        if len(c) >= 10 and re.match(r"^\d+$", c[0] or ""):
            lines.append({"mo_ta": c[1], "loai": c[2], "ncc": c[3], "don_gia": _num(c[4]), "sl": _num(c[5]), "hs": _num(c[6]), "thuc_chi": _num(c[8]), "da_tt": _num(c[9]), "ghi_chu": c[10] if len(c) > 10 else ""})
    step = re.search(r"(Bước\s*\d+[^\n]{0,80})", txt)
    hist = []
    if "Lịch sử hoạt động" in txt:
        tl = [x.strip() for x in txt[txt.find("Lịch sử hoạt động") + len("Lịch sử hoạt động"):].split("\n") if x.strip()]
        DT = re.compile(r"^(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2})\s*-\s*(.+)$")
        idx = [i for i, l in enumerate(tl) if DT.match(l)]
        for k, i in enumerate(idx):
            if i == 0: continue
            m = DT.match(tl[i]); d, mo, y, hh, mi, actor = m.groups()
            nxt_title = idx[k + 1] - 1 if k + 1 < len(idx) else len(tl)
            note = " ".join(tl[i + 1:nxt_title])
            rec = {"title": tl[i - 1][:200], "at": f"{y}-{mo}-{d}T{hh}:{mi}:00", "actor": actor.strip()[:120], "note": note[:1000]}
            if not any(h["title"] == rec["title"] and h["at"] == rec["at"] for h in hist): hist.append(rec)
    return {"tourId": tour["recID"], "tourcode": tour["tourcode"], "tong_thu": _num(tt.group(1)) if tt else 0, "tong_chi": _num(tc.group(1)) if tc else 0,
            "lines": lines, "step": step.group(1).strip() if step else "", "history": hist[:60]}


def parse_product(html: str, pid: int, listing: dict) -> dict:
    f = {}
    for m in re.finditer(r'<(input|select|textarea)\b([^>]*)>', html, re.I):
        attrs = dict(re.findall(r'(\w[\w-]*)\s*=\s*"([^"]*)"', m.group(2)))
        n = attrs.get("name")
        if not n or n in f: continue
        if m.group(1).lower() == "select":
            seg = html[m.end(): m.end() + 20000]; opt = re.search(r'<option[^>]*selected[^>]*>([^<]*)</option>', seg[: seg.find("</select>")] if "</select>" in seg else seg)
            f[n] = opt.group(1).strip() if opt else ""
        elif m.group(1).lower() == "textarea":
            seg = html[m.end():]; f[n] = seg[: seg.find("</textarea>")] if "</textarea>" in seg else ""
        elif attrs.get("type") == "checkbox": f[n] = "checked" in m.group(2)
        else: f[n] = attrs.get("value", "")
    price = re.sub(r"<[^>]+>", "\n", f.get("PriceInfo", "") or ""); price = re.sub(r"\n{3,}", "\n\n", urllib.parse.unquote(price)).strip()[:20000]
    nv = re.search(r'name="NVDH"[\s\S]{0,4000}?<option[^>]*selected[^>]*>([^<]*)</option>', html)
    keep = ["ProductCode", "ProductName", "DeparturePoint", "TourType", "Region", "Country", "SalePoint", "Transportation", "VehicleType", "TourLength", "Duration", "ReferencePrice", "DepositPercentage", "DaysToCloseTour", "RequiresConfirmation",
            "Flight", "Land", "LSQFee", "Insurance", "Gift", "TLFee", "GroupMeeting", "Operating", "Translation", "TicketCommission", "CKFee", "OtherCost"]
    out = {k: f.get(k, "") for k in keep}
    out.update({"id": pid, "services": listing.get("services", ""), "status": listing.get("status", "Hoạt động"), "PriceInfoText": price, "NVDH_name": nv.group(1).strip() if nv else "", "cost_lines": []})
    return out


def run_sync(db: Session, from_date: date, to_date: date, products: bool = True, settlements_days: int = 10, log=None) -> dict:
    """Kéo toàn bộ dữ liệu trong khoảng [from, to] rồi ánh xạ. Trả về số lượng từng loại."""
    log = log or (lambda m: None)
    if not settings.VIETRIP_PHONE or not settings.VIETRIP_PASSWORD: raise VietripError("Chưa cấu hình VIETRIP_PHONE / VIETRIP_PASSWORD (Render → Environment) cho tài khoản robot")
    c = Client(settings.VIETRIP_PHONE, settings.VIETRIP_PASSWORD)
    users = c.login(); users = users.get("data", users) if isinstance(users, dict) else users
    VT.upsert(db, "user", users); log(f"user {len(users)}")
    veh = json.loads(c.get("/api/vehicles/filter?page=1&pageSize=200")); veh = veh.get("data", veh) if isinstance(veh, dict) else veh
    VT.upsert(db, "vehicle", veh); log(f"vehicle {len(veh)}")
    tours, page = [], 1
    while True:
        j = c.post_json("/operations/OperationsTour/GetToursData", {"tourType": "All", "fromDate": str(from_date), "searchKeyword": "", "selectedServices": [], "page": page, "pageSize": 500})
        tours += j.get("data") or []
        if not j.get("data") or len(j["data"]) < 500 or page >= (j.get("totalPages") or 1): break
        page += 1
    VT.upsert(db, "tour", tours); log(f"tour {len(tours)}")
    counts = {"users": len(users), "vehicles": len(veh), "tours": len(tours), "products": 0, "bookings": 0, "receipts": 0, "supplier_payments": 0, "settlements": 0}
    if products:
        html = c.get("/Product/Search?search=&page=1&pageSize=1000")
        items = [(int(m.group(1)), m.start()) for m in re.finditer(r'/product/edit/(\d+)', html)]
        seen = set(); prods = []
        for pid, pos in items:
            if pid in seen: continue
            seen.add(pid)
            row = html[max(0, pos - 2500):pos]; cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
            cells = [re.sub(r"<[^>]+>", " ", x).strip() for x in cells][-7:]
            try: prods.append(parse_product(c.get(f"/product/edit/{pid}"), pid, {"services": cells[2] if len(cells) > 2 else "", "status": cells[-1] if cells else ""}))
            except Exception as e: log(f"lỗi sản phẩm {pid}: {e}")
        VT.upsert(db, "product", prods); counts["products"] = len(prods); log(f"product {len(prods)}")
    # bookings theo ngày đặt
    d2 = lambda d: f"{d:%d}%2F{d:%m}%2F{d:%Y}"
    bks, start = [], 0
    while True:
        j = json.loads(c.get(f"/api/booking/search?draw=1&start={start}&length=1000&showAll=true&bookingDateFrom={d2(from_date)}&bookingDateTo={d2(to_date)}&order[0][column]=0&order[0][dir]=asc"))
        bks += j.get("data") or []; start += 1000
        if not j.get("data") or len(j["data"]) < 1000: break
    VT.upsert(db, "booking", bks); counts["bookings"] = len(bks); log(f"booking {len(bks)}")
    # phiếu thu/chi: danh sách (≤ ~3.000 dòng mới nhất) + quét theo booking trong kỳ
    seen_rec = set(); recs = []
    for pt in ("PhieuThu", "PhieuChi"):
        for stt in ("DaXacNhan", "ChoXacNhan"):
            for st, ln in ((0, 1200), (1100, 2000)):
                try:
                    j = json.loads(c.post_form("/Accounting/PaymentConfirmation/GetPaymentData", {"draw": "1", "start": str(st), "length": str(ln), "order[0][column]": "9", "order[0][dir]": "desc", "paymentType": pt, "status": stt, "fromDate": str(from_date)}))
                except Exception as e:
                    log(f"phiếu {pt}/{stt} {st}: {e}"); continue
                for x in j.get("data") or []:
                    if str(x.get("RecID")) in seen_rec: continue
                    seen_rec.add(str(x.get("RecID"))); x["LoaiPhieu"] = pt
                    if (x.get("FstUpdate") or "")[:10] <= str(to_date): recs.append(x)
                if len(seen_rec) >= (j.get("recordsFiltered") or 0): break
    for b in bks:
        try: j = json.loads(c.get(f"/api/bookings/{b['recID']}/payments", timeout=30))
        except Exception: continue
        for pm in j.get("data") or []:
            if str(pm.get("id")) in seen_rec: continue
            seen_rec.add(str(pm.get("id")))
            recs.append({"RecID": str(pm.get("id")), "Tourcode": b.get("tourcode"), "TenNguoiBook": b.get("tenNguoiBook"), "BookingID": str(b["recID"]), "SoTien": pm.get("soTien"), "NguoiThanhToan": pm.get("nguoiThanhToan"),
                         "HinhThuc": pm.get("hinhThuc"), "TaiKhoanCongTy": pm.get("taiKhoanCongTy"), "GhiChu": pm.get("ghiChu") or "", "FstUser": "", "FstUpdate": pm.get("fstUpdate"), "Status": pm.get("status"),
                         "LoaiPhieu": "PhieuChi" if (pm.get("soTien") or 0) < 0 else "PhieuThu"})
    VT.upsert(db, "receipt", recs); counts["receipts"] = len(recs); log(f"receipt {len(recs)}")
    # chi NCC
    sp, skip = [], 0
    while True:
        j = json.loads(c.get(f"/accounting/supplier-payment-confirmation/GetPaymentData?skip={skip}&take=1000&requireTotalCount=true"))
        sp += j.get("data") or []; skip += 1000
        if not j.get("data") or len(j["data"]) < 1000: break
    sp = [x for x in sp if str(from_date) <= (x.get("FstUpdateString") or "") <= str(to_date)]
    VT.upsert(db, "supplier_payment", sp); counts["supplier_payments"] = len(sp); log(f"supplier_payment {len(sp)}")
    try:
        pr = json.loads(c.get("/expense-proposals/approvals/data?start=0&length=1000&draw=1")); VT.upsert(db, "proposal", pr.get("items") or pr.get("data") or [])
    except Exception as e: log(f"proposal: {e}")
    # quyết toán: tour kết thúc trong `settlements_days` ngày gần nhất (mỗi trang ~10 giây)
    today = date.today(); lo = today - timedelta(days=settlements_days)
    done = [t for t in tours if str(lo) <= (t.get("ngayKetThuc") or "")[:10] <= str(today)]
    sets = []
    for t in done:
        try: sets.append(parse_settlement(c.get(f"/tour-settlement/spreadsheet/{t['recID']}", timeout=60), t))
        except Exception as e: log(f"lỗi quyết toán {t.get('tourcode')}: {e}")
        if len(sets) >= 50: VT.upsert(db, "settlement", sets); counts["settlements"] += len(sets); sets = []
    if sets: VT.upsert(db, "settlement", sets); counts["settlements"] += len(sets)
    log(f"settlement {counts['settlements']}/{len(done)}")
    # ánh xạ
    total = {}; guard = 0
    while guard < 300:
        ap = VT.apply_all(db, "robot-vietrip", limit=400); guard += 1
        for k, v in ap.items():
            if k not in ("remaining", "blocked"): total[k] = total.get(k, 0) + v
        if (ap["remaining"] or 0) <= 0: break
    counts["applied"] = total; counts["blocked"] = ap.get("blocked", 0)
    return counts


"""TC-53 · NẠP BÙ THEO LÔ — hai cửa nhỏ thay cho một lần chạy dài không bao giờ xong.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO KHÔNG DÙNG `run_sync` ĐỂ NẠP BÙ TỪ THÁNG 1
═══════════════════════════════════════════════════════════════════════════════════════════════
Đếm ngày 17/9/2026: VTOS không có chuyến nào KẾT THÚC trước tháng 6 — T6 297, T7 289, T8 220,
T9 119, còn T1–T5 trống trơn. Không phải mất dữ liệu: lần đồng bộ đầu (05/9) đặt mốc từ 01/6 nên
Vietrip chỉ trả về tour từ tháng 6. Anh Tuấn yêu cầu 17/9: cập nhật từ tháng 1.

Gọi `run_sync(from_date=2026-01-01)` KHÔNG làm được việc ấy, vì hai chỗ:
  · Nó quét TỪNG BOOKING một để lấy phiếu thu (`/api/bookings/{id}/payments`). Từ tháng 1 là hơn
    12.000 lượt gọi — đây mới là chỗ giết job, không phải bảng quyết toán.
  · Nó chọn bảng quyết toán theo `settlements_days` đếm lùi từ HÔM NAY, nên muốn với tới tháng 1
    phải đặt ~260 ngày, kéo về hơn nghìn trang, mỗi trang ~10 giây — hơn ba tiếng.
Mà Render gói miễn phí ngủ sau 15 phút không có ai gọi, và robot chạy nền nằm trong chính tiến
trình ấy. Job dài hơn 15 phút chết giữa đường — đã xảy ra đúng như vậy sáng 17/9.

Nên hai cửa dưới đây CHẠY ĐỒNG BỘ VÀ CÓ ĐÁY: mỗi lần gọi làm một lô nhỏ rồi trả về `con_lai`.
Ngủ giữa chừng thì gọi tiếp — không mất gì, không nạp trùng (khoá theo `vietrip_id`). Cả hai
KHÔNG đụng tới booking và phiếu thu.
"""


def _dang_nhap() -> "Client":
    if not settings.VIETRIP_PHONE or not settings.VIETRIP_PASSWORD:
        raise VietripError("Chưa cấu hình VIETRIP_PHONE / VIETRIP_PASSWORD (Render → Environment) cho tài khoản robot")
    c = Client(settings.VIETRIP_PHONE, settings.VIETRIP_PASSWORD)
    c.login()
    return c


def _ngay(s) -> str:
    return (s or "")[:10]


def nap_tour_theo_khoang(db: Session, tu: date, den: date) -> dict:
    """Kéo DANH SÁCH TOUR kết thúc trong [tu, den] rồi ánh xạ. Không đụng booking/phiếu thu.

    Vietrip chỉ nhận `fromDate` (mốc khởi hành) chứ không nhận mốc kết thúc, nên lấy rộng rồi lọc
    tại chỗ theo `ngayKetThuc`. Lọc ở đây chứ không ở Vietrip là chủ ý: một chuyến khởi hành cuối
    tháng 12/2025 mà kết thúc đầu tháng 1/2026 vẫn phải vào kỳ tháng 1.
    """
    c = _dang_nhap()
    tours, page = [], 1
    lay_tu = tu - timedelta(days=60)   # chuyến dài ngày khởi hành trước mốc vẫn kết thúc trong kỳ
    while True:
        j = c.post_json("/operations/OperationsTour/GetToursData",
                        {"tourType": "All", "fromDate": str(lay_tu), "searchKeyword": "",
                         "selectedServices": [], "page": page, "pageSize": 500})
        lo = j.get("data") or []
        tours += lo
        if not lo or len(lo) < 500 or page >= (j.get("totalPages") or 1): break
        page += 1
    trong_ky = [t for t in tours if str(tu) <= _ngay(t.get("ngayKetThuc")) <= str(den)]
    VT.upsert(db, "tour", trong_ky)
    da_anh_xa, vong = 0, 0
    while vong < 40:                       # 40 × 400 = 16.000 chuyến, thừa sức cho một năm
        n = VT.apply_tours(db, limit=400)
        da_anh_xa += n; vong += 1
        if n == 0: break
    return {"tu": str(tu), "den": str(den), "vietrip_tra_ve": len(tours),
            "trong_ky": len(trong_ky), "da_anh_xa": da_anh_xa}


def nap_quyet_toan_thieu(db: Session, tu: date, den: date, gioi_han: int = 6) -> dict:
    """Tải bảng quyết toán CÒN THIẾU cho chuyến kết thúc trong [tu, den] — mỗi lần một lô nhỏ.

    Danh sách chuyến đọc từ `vt_records` đã nạp, KHÔNG gọi lại Vietrip: danh sách tour vừa nặng
    vừa không đổi giữa hai lô, và mỗi lần gọi lại là một lần nữa có thể hỏng giữa chừng.

    Trả về `con_lai` để nơi gọi lặp tới khi bằng 0. `gioi_han` mặc định nhỏ vì mỗi trang quyết toán
    mất khoảng 10 giây: một lô phải xong gọn trong thời gian một lượt gọi HTTP, thà gọi nhiều lần
    còn hơn một lần gọi chết giữa đường và không biết đã làm tới đâu.
    """
    from sqlalchemy import select
    from app.models.vietrip import VtRecord

    da_co = {r.raw.get("tourcode") for r in db.execute(
        select(VtRecord).where(VtRecord.entity == "settlement")).scalars() if r.raw}
    thieu = []
    for r in db.execute(select(VtRecord).where(VtRecord.entity == "tour")).scalars():
        w = r.raw or {}
        if not (str(tu) <= _ngay(w.get("ngayKetThuc")) <= str(den)): continue
        if w.get("tourcode") in da_co: continue
        if not w.get("recID"): continue
        thieu.append(w)
    thieu.sort(key=lambda w: _ngay(w.get("ngayKetThuc")))

    lo = thieu[:max(1, min(gioi_han, 20))]
    if not lo:
        return {"da_nap": 0, "con_lai": 0, "loi": [], "message": "Không còn bảng quyết toán nào thiếu"}

    c = _dang_nhap()
    duoc, loi = [], []
    for w in lo:
        try:
            duoc.append(parse_settlement(c.get(f"/tour-settlement/spreadsheet/{w['recID']}", timeout=60), w))
        except Exception as e:                      # một trang hỏng KHÔNG được làm chết cả lô
            loi.append(f"{w.get('tourcode')}: {type(e).__name__}")
    if duoc:
        VT.upsert(db, "settlement", duoc)
        VT.apply_settlements(db, limit=400)
    return {"da_nap": len(duoc), "con_lai": len(thieu) - len(lo), "loi": loi,
            "message": f"Đã nạp {len(duoc)} bảng, còn {len(thieu) - len(lo)}"}


def start_background(from_date: date, to_date: date, products: bool, settlements_days: int) -> bool:
    if STATE["running"]: return False
    STATE.update({"running": True, "log": [], "started": datetime.now(), "finished": None, "result": None, "error": ""})

    def _job():
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            res = run_sync(db, from_date, to_date, products, settlements_days, log=lambda m: STATE["log"].append(f"{datetime.now():%H:%M:%S} {m}"))
            STATE["result"] = res
            from app.services import rules as R
            R.audit(db, "robot-vietrip", "robot", "dong_bo_vietrip_tu_dong", "vietrip", after={"tu": str(from_date), "den": str(to_date), **{k: v for k, v in res.items() if k != "applied"}}); db.commit()
        except Exception as e:
            STATE["error"] = f"{type(e).__name__}: {str(e)[:500]}"; STATE["log"].append("LỖI " + STATE["error"])
        finally:
            db.close(); STATE["running"] = False; STATE["finished"] = datetime.now()
    threading.Thread(target=_job, daemon=True).start()
    return True


# ==============================================================================================
# KÉO BOOKING CÒN THIẾU THEO ID — gỡ chỗ 227 phiếu thu treo vì "chưa có booking"
# ==============================================================================================
#
# ĐO ĐƯỢC 26/9/2026 TRÊN HỆ THẬT
#
# 227 phiếu thu/chi Vietrip nằm treo, tổng 1.519.979.111 đ, tất cả cùng một lý do: "chưa có
# booking". Không phải phiếu mồ côi — CẢ 227 phiếu đều mang mã booking của Vietrip, trỏ tới 183
# booking khác nhau, id từ 95241 đến 127507. Chỉ là 183 booking ấy chưa có trên VTOS.
#
# Vì sao chưa có: `run_sync` kéo booking theo NGÀY ĐẶT, cửa sổ 7 ngày. Khách đặt tour từ tháng 3,
# trả tiền tháng 9 — phiếu thu tháng 9 lọt vào lưới, booking tháng 3 thì không. Càng chạy càng
# tích lại, và không có gì đỏ lên vì bộ ánh xạ xếp chúng vào rổ "blocked" chứ không phải "lỗi".
#
# VÌ SAO PHẢI LẦN THEO ID CHỨ KHÔNG LỌC Ở VIETRIP
#
# Đo ngày 26/9/2026: cửa `/api/booking/search` KHÔNG nhận bộ lọc nào ngoài khoảng ngày đặt. Thử
# `bookingID=`, `recID=`, `tourcode=`, `search[value]=` — cả bốn đều trả nguyên 122.783 dòng, tức
# tham số bị bỏ qua chứ không phải lọc ra 0. Và không có cửa `/api/bookings/{id}` (404).
#
# Nên cách duy nhất là lật trang danh sách. Danh sách trả về theo recID GIẢM DẦN, nên lật từ đầu
# là đi từ id mới nhất về id cũ, và DỪNG ĐƯỢC ngay khi trang hiện tại đã lùi qua id nhỏ nhất cần
# tìm. Với khoảng 95241–127507 trên tổng 122.783 dòng thì tệ nhất khoảng 33 trang, thực tế ít hơn.
#
# CHỖ NÀY KHÔNG ĐỤNG MỐC 01/08/2026
#
# `MOC_SOM_NHAT` chặn theo KHOẢNG NGÀY, để không nạp đè số quyết toán T1–T7 đã chốt. Hàm này không
# truyền khoảng ngày nào cả — nó đi tìm đúng những booking mà một phiếu thu ĐANG CÓ trỏ tới. Lấy
# một booking tháng 3 để gắn khoản tiền khách trả tháng 9 không phải là nạp lại tháng 3.
#
# Chủ tịch chốt 26/9/2026 (phương án A): cho phép lần theo id bất kể ngày đặt; mốc vẫn chặn tour
# và quyết toán như cũ.

MOI_TRANG_BOOKING = 1000
TRAN_TRANG_BOOKING = 60        # phanh: 60 × 1.000 = 60.000 dòng, quá thừa cho khoảng id thực tế


def nap_booking_theo_id(db: Session, ids: list[int], log=None) -> dict:
    """Tìm và nạp đúng những booking mang `recID` trong `ids`. Chỉ ĐỌC ở phía Vietrip."""
    log = log or (lambda m: None)
    con_tim = {int(i) for i in ids if i}
    if not con_tim:
        return {"can_tim": 0, "tim_thay": 0, "so_trang": 0, "con_thieu": []}

    nho_nhat = min(con_tim)
    c = _dang_nhap()
    thay, trang, start = [], 0, 0
    while trang < TRAN_TRANG_BOOKING and con_tim:
        j = json.loads(c.get(f"/api/booking/search?draw=1&start={start}&length={MOI_TRANG_BOOKING}"
                             f"&showAll=true&order[0][column]=0&order[0][dir]=desc"))
        lo = j.get("data") or []
        trang += 1
        if not lo:
            break
        for b in lo:
            rid = int(b.get("recID") or 0)
            if rid in con_tim:
                thay.append(b)
                con_tim.discard(rid)
        start += len(lo)
        nho_nhat_trang = min((int(b.get("recID") or 0) for b in lo), default=0)
        log(f"trang {trang}: {len(lo)} dòng, tới id {nho_nhat_trang}, còn tìm {len(con_tim)}")
        # Danh sách giảm dần: lùi qua id nhỏ nhất cần tìm thì những id còn lại không thể ở phía sau.
        if nho_nhat_trang and nho_nhat_trang < nho_nhat:
            break
        if len(lo) < MOI_TRANG_BOOKING:
            break

    if thay:
        VT.upsert(db, "booking", thay)
    return {"can_tim": len(ids), "tim_thay": len(thay), "so_trang": trang,
            "con_thieu": sorted(con_tim)[:50]}
