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
        if ap["remaining"] <= 0: break
    counts["applied"] = total; counts["blocked"] = ap.get("blocked", 0)
    return counts


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
