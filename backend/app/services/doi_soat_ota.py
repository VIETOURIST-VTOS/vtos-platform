"""KS-2 · Đối soát đặt phòng & hoa hồng OTA (Chủ tịch duyệt bản xem thử 28/10/2026).

LUỒNG
  1. Kế toán tải tệp báo cáo từ OTA (Expedia Creator Hub → Performance → Download; CJ cho Booking.com)
     rồi «đọc thử» trên VTOS: máy đọc, so với sổ hiện có, báo dòng mới / cập nhật / trùng / lỗi — CHƯA
     GHI GÌ. Gửi duyệt = tạo một LÔ chờ duyệt (lưu các dòng đã đọc và mã băm tệp).
  2. Chủ tịch duyệt (người nạp KHÔNG tự duyệt). Duyệt mới chạm sổ: đặt phòng mới / đổi trạng thái
     → phiên bản mới; sổ hoa hồng ghi PHẦN CHÊNH (chỉ ghi thêm). Từ chối phải có lý do.

BA ĐIỀU KHÔNG LỎNG
  · Tiền giữ nguyên USD, số nguyên cent. Không quy đổi, không cộng vào doanh thu Vietourist — hoa hồng
    thuộc pháp nhân hợp đồng (INFINIS). Hạch toán do Kế toán quyết theo chứng từ.
  · Không ĐOÁN chủ đặt phòng theo ngày / thành phố. Chỉ nối về lượt chuyển (→ khách / đại lý) khi báo
    cáo có đúng mã lượt (SubID) VTOS đã gắn. Expedia Creator Hub hiện không có cột ấy → số tổng.
  · Báo cáo không có mã đặt phòng thì khoá ghép = ngày đặt | ngày đến | ngày đi | thành phố | link |
    sản phẩm | giá trị. Hai dòng giống hệt trong một tệp → đánh #1, #2 và BÁO RA để Kế toán xem.
"""
import csv
import hashlib
import io
import re
import secrets
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import User
from app.models.khach_san_ota import (DoiTacOta, LuotChuyenOta, LoNapOta, DatPhongOta, SoHoaHongOta, TRANG_THAI_LO)
from app.services import rules as R

VAI_NAP = ("ketoan",)
VAI_DUYET = ("chutich",)
VAI_XEM = ("chutich", "tgd", "bks", "robot_ks", "ketoan")
TEP_TOI_DA = 5 * 1024 * 1024
DONG_TOI_DA = 5000

# Tên cột chuẩn → các tên cột OTA có thể dùng (so sau khi bỏ dấu, chữ thường, bỏ ký tự lạ).
COT = {
    "ma_dat_phong": ("booking id", "itinerary", "itinerary number", "order id", "action id", "reservation id", "confirmation number"),
    "ngay_dat": ("booked date", "booking date", "event date", "transaction date", "posting date", "order date"),
    "san_pham": ("booked product", "product", "trip element", "action type"),
    "thanh_pho": ("destination city", "city", "hotel city"),
    "quoc_gia": ("destination country", "country"),
    "link": ("affiliate link", "link name", "link id", "website"),
    "hoa_hong": ("estimated commission usd", "estimated commission", "commission usd", "publisher commission", "commission"),
    "gia_tri": ("transaction value usd", "transaction value", "sale amount usd", "sale amount", "order amount"),
    "trang_thai_chuyen": ("trip status", "status", "action status", "booking status"),
    "trang_thai_tt": ("payment status", "payout status", "locking status"),
    "ngay_den": ("start date", "check in", "checkin date", "check in date"),
    "ngay_di": ("end date", "check out", "checkout date", "check out date"),
    "so_khach": ("travelers", "travellers", "guests"),
    "subid": ("subid", "sub id", "sid", "shopper id", "clickref", "click ref", "tracking id"),
}
BAT_BUOC = ("ngay_dat", "hoa_hong")
HUY = ("cancel", "huy", "declined", "reversed", "corrected")
XONG = ("completed", "complete", "closed", "stayed", "hoan tat")
DA_TRA = ("paid",)


class LoiDoiSoat(ValueError):
    def __init__(self, thong_diep: str, status: int = 400):
        super().__init__(thong_diep)
        self.status = status


def _vai(u: User) -> tuple[str, ...]:
    from app.services.vai_ke_thua import vai_va_cha
    return vai_va_cha(u.role)


def _co(u: User, vai: tuple[str, ...]) -> bool:
    return any(v in vai for v in _vai(u))


def _chuan(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ---------------------------------------------------------------- đọc tệp

def _bang(ten_tep: str, du_lieu: bytes) -> list[list[str]]:
    if len(du_lieu) > TEP_TOI_DA:
        raise LoiDoiSoat("Tệp quá 5 MB")
    if ten_tep.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            wb = load_workbook(io.BytesIO(du_lieu), read_only=True, data_only=True)
        except Exception:
            raise LoiDoiSoat("Không mở được tệp Excel")
        ws = wb.worksheets[0]
        return [["" if c is None else (c.isoformat() if isinstance(c, (date, datetime)) else str(c)) for c in r]
                for r in ws.iter_rows(values_only=True)]
    for mh in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            txt = du_lieu.decode(mh)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise LoiDoiSoat("Không đọc được bảng mã của tệp")
    try:
        mau = csv.Sniffer().sniff(txt[:4096], delimiters=",;\t")
    except csv.Error:
        mau = csv.excel
    return [r for r in csv.reader(io.StringIO(txt), mau)]


def _so_cent(s) -> int | None:
    t = str(s or "").strip()
    if not t or t in ("-", "—"):
        return None
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".") if len(t.split(",")[-1]) <= 2 else t.replace(",", "")
    try:
        return int((Decimal(t) * 100).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        raise ValueError(f"số tiền «{s}» không đọc được")


def _ngay(s) -> date | None:
    t = str(s or "").strip()
    if not t:
        return None
    for f, n in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10), ("%m/%d/%Y", 10),
                 ("%m/%d/%y", 8), ("%d-%b-%Y", 11), ("%b %d, %Y", 12), ("%d %b %Y", 11)):
        try:
            return datetime.strptime(t[:n], f).date()
        except ValueError:
            continue
    raise ValueError(f"ngày «{s}» không đọc được")


def doc_tep(ten_tep: str, du_lieu: bytes) -> dict:
    """Đọc tệp → {dong: [dòng chuẩn hoá], loi: [...], trung_trong_tep: n}. Không đụng cơ sở dữ liệu."""
    bang = [r for r in _bang(ten_tep, du_lieu) if any(str(c).strip() for c in r)]
    if not bang:
        raise LoiDoiSoat("Tệp rỗng")
    # Dòng tiêu đề = dòng đầu tiên chứa đủ các cột bắt buộc (một số báo cáo có vài dòng giới thiệu ở trên).
    vi_tri = None
    for i, r in enumerate(bang[:15]):
        tieu = [_chuan(c) for c in r]
        cot = {}
        for k, ten in COT.items():
            for j, t in enumerate(tieu):
                if t in ten and k not in cot:
                    cot[k] = j
        if all(k in cot for k in BAT_BUOC):
            vi_tri = (i, cot)
            break
    if vi_tri is None:
        raise LoiDoiSoat("Không thấy dòng tiêu đề có cột ngày đặt và hoa hồng — tệp có đúng là báo cáo đặt phòng của OTA không?")
    i0, cot = vi_tri
    dong, loi = [], []
    for so, r in enumerate(bang[i0 + 1:], start=i0 + 2):
        if len(dong) >= DONG_TOI_DA:
            loi.append({"dong": so, "loi": f"quá {DONG_TOI_DA} dòng — tách tệp"}); break
        g = lambda k: (r[cot[k]] if k in cot and cot[k] < len(r) else "")
        if _chuan(g("ngay_dat")) in ("total", "tong", "tong cong", "grand total", "sum"):
            continue              # dòng tổng cuối bảng
        try:
            hh = _so_cent(g("hoa_hong"))
            nd = _ngay(g("ngay_dat"))
            if nd is None and hh is None:
                continue          # dòng tổng cộng / ghi chú cuối bảng
            if nd is None:
                raise ValueError("thiếu ngày đặt")
            sk = str(g("so_khach")).strip()
            dong.append({
                "ma_dat_phong": str(g("ma_dat_phong")).strip()[:120], "ngay_dat": nd.isoformat(),
                "san_pham": str(g("san_pham")).strip()[:80], "thanh_pho": str(g("thanh_pho")).strip()[:120],
                "quoc_gia": str(g("quoc_gia")).strip()[:80], "link": str(g("link")).strip()[:300],
                "hoa_hong_cent": hh or 0, "gia_tri_cent": _so_cent(g("gia_tri")) or 0,
                "trang_thai_chuyen": str(g("trang_thai_chuyen")).strip()[:40], "trang_thai_tt": str(g("trang_thai_tt")).strip()[:40],
                "ngay_den": (_ngay(g("ngay_den")) or "") and _ngay(g("ngay_den")).isoformat(),
                "ngay_di": (_ngay(g("ngay_di")) or "") and _ngay(g("ngay_di")).isoformat(),
                "so_khach": int(float(sk)) if re.fullmatch(r"\d+(\.0+)?", sk) else None,
                "subid": re.sub(r"[^A-Za-z0-9_\-]", "", str(g("subid")))[:40],
            })
        except ValueError as ex:
            loi.append({"dong": so, "loi": str(ex)})
    # Khoá: mã đặt phòng nếu có; không thì khoá ghép, đánh #n cho dòng giống hệt.
    dem, trung = {}, 0
    for d in dong:
        if d["ma_dat_phong"]:
            d["khoa"], d["co_ma_rieng"] = "ID:" + d["ma_dat_phong"], True
            continue
        g = "|".join(str(d[k]) for k in ("ngay_dat", "ngay_den", "ngay_di", "thanh_pho", "link", "san_pham", "gia_tri_cent"))
        dem[g] = dem.get(g, 0) + 1
        if dem[g] == 2:
            trung += 1
        d["khoa"], d["co_ma_rieng"] = f"G:{g}#{dem[g]}", False
    return {"dong": dong, "loi": loi, "trung_trong_tep": trung, "cot_doc_duoc": sorted(cot)}


TRUONG_SO = ("ngay_dat", "san_pham", "thanh_pho", "quoc_gia", "link", "ngay_den", "ngay_di", "so_khach",
             "gia_tri_cent", "hoa_hong_cent", "trang_thai_chuyen", "trang_thai_tt", "subid")


def _gia_tri_hien(dp: DatPhongOta) -> dict:
    return {"ngay_dat": dp.ngay_dat.isoformat() if dp.ngay_dat else "", "san_pham": dp.san_pham, "thanh_pho": dp.thanh_pho,
            "quoc_gia": dp.quoc_gia, "link": dp.link, "ngay_den": dp.ngay_den.isoformat() if dp.ngay_den else "",
            "ngay_di": dp.ngay_di.isoformat() if dp.ngay_di else "", "so_khach": dp.so_khach, "gia_tri_cent": dp.gia_tri_cent,
            "hoa_hong_cent": dp.hoa_hong_cent, "trang_thai_chuyen": dp.trang_thai_chuyen, "trang_thai_tt": dp.trang_thai_tt,
            "subid": dp.ma_luot}


def so_sanh(db: Session, ota_id: int, dong: list[dict]) -> list[dict]:
    """Gắn mỗi dòng nhãn moi / cap_nhat / trung so với sổ HIỆN TẠI."""
    cu = {d.khoa: d for d in db.execute(select(DatPhongOta).where(DatPhongOta.doi_tac_ota_id == ota_id,
                                                                  DatPhongOta.khoa.in_([x["khoa"] for x in dong]))).scalars()} if dong else {}
    ra = []
    for x in dong:
        d = cu.get(x["khoa"])
        if d is None:
            nhan, doi = "moi", []
        else:
            h = _gia_tri_hien(d)
            doi = [k for k in TRUONG_SO if str(h.get(k) or "") != str(x.get(k) or "")]
            nhan = "cap_nhat" if doi else "trung"
        ra.append(dict(x, thay_doi=nhan, truong_doi=doi,
                       hoa_hong_truoc=(d.hoa_hong_cent if d else 0)))
    return ra


def _tom(ds: list[dict]) -> dict:
    return {"moi": sum(1 for x in ds if x["thay_doi"] == "moi"), "cap_nhat": sum(1 for x in ds if x["thay_doi"] == "cap_nhat"),
            "trung": sum(1 for x in ds if x["thay_doi"] == "trung"),
            "chenh_hoa_hong_cent": sum(x["hoa_hong_cent"] - x["hoa_hong_truoc"] for x in ds if x["thay_doi"] != "trung")}


def _ota(db: Session, ota_id: int) -> DoiTacOta:
    o = db.get(DoiTacOta, int(ota_id or 0))
    if o is None:
        raise LoiDoiSoat("Không có OTA này", 404)
    if getattr(o, "san_pham", "khach_san") != "khach_san":
        raise LoiDoiSoat("Đối soát OTA hiện chỉ cho khách sạn — vé máy bay chưa có hoa hồng", 422)
    return o


def doc_thu(db: Session, u: User, ota_id: int, ten_tep: str, du_lieu: bytes) -> dict:
    if not _co(u, VAI_NAP):
        raise LoiDoiSoat("Chỉ Kế toán nạp báo cáo OTA", 403)
    o = _ota(db, ota_id)
    r = doc_tep(ten_tep or "", du_lieu)
    ds = so_sanh(db, o.id, r["dong"])
    bam = hashlib.sha256(du_lieu).hexdigest()
    da_nap = db.execute(select(LoNapOta).where(LoNapOta.doi_tac_ota_id == o.id, LoNapOta.bam_tep == bam,
                                               LoNapOta.trang_thai != "tu_choi")).scalars().first()
    return {"ota": o.ten, "so_dong": len(ds), "loi": r["loi"], "trung_trong_tep": r["trung_trong_tep"],
            "cot_doc_duoc": r["cot_doc_duoc"], "tom": _tom(ds), "dong": ds[:300],
            "da_nap": {"ma": da_nap.ma, "trang_thai": TRANG_THAI_LO[da_nap.trang_thai]} if da_nap else None}


def gui_duyet(db: Session, u: User, ota_id: int, ky: str, ten_tep: str, du_lieu: bytes, now: datetime | None = None) -> LoNapOta:
    if not _co(u, VAI_NAP):
        raise LoiDoiSoat("Chỉ Kế toán nạp báo cáo OTA", 403)
    o = _ota(db, ota_id)
    if not re.fullmatch(r"\d{4}-\d{2}", ky or ""):
        raise LoiDoiSoat("Ghi kỳ báo cáo dạng YYYY-MM")
    r = doc_tep(ten_tep or "", du_lieu)
    if not r["dong"]:
        raise LoiDoiSoat("Tệp không có dòng đặt phòng nào đọc được")
    bam = hashlib.sha256(du_lieu).hexdigest()
    if db.execute(select(LoNapOta).where(LoNapOta.doi_tac_ota_id == o.id, LoNapOta.bam_tep == bam,
                                         LoNapOta.trang_thai != "tu_choi")).scalars().first():
        raise LoiDoiSoat("Tệp này đã nạp rồi — không nạp lại")
    if db.execute(select(LoNapOta).where(LoNapOta.doi_tac_ota_id == o.id, LoNapOta.trang_thai == "cho_duyet")).scalars().first():
        raise LoiDoiSoat(f"{o.ten} còn một lô chờ Chủ tịch duyệt — duyệt hoặc từ chối lô ấy trước")
    now = now or datetime.now()
    n = db.execute(select(func.count(LoNapOta.id))).scalar_one() + 1
    lo = LoNapOta(ma=f"{o.ma[:3].upper()}-{ky}-{n:03d}", doi_tac_ota_id=o.id, ky=ky, ten_tep=(ten_tep or "")[:200], bam_tep=bam,
                  dong=r["dong"], so_dong=len(r["dong"]), so_loi=len(r["loi"]), loi=r["loi"][:200],
                  nap_boi=u.username, nap_luc=now, ket_qua={"trung_trong_tep": r["trung_trong_tep"]})
    db.add(lo); db.flush()
    R.audit(db, u.username, u.role, "nap_bao_cao_ota", f"lo_nap_ota:{lo.ma}", after={"ota": o.ma, "ky": ky, "so_dong": lo.so_dong, "bam": bam})
    db.commit(); db.refresh(lo)
    return lo


def _ngay_d(s: str) -> date | None:
    return date.fromisoformat(s) if s else None


def duyet(db: Session, u: User, lo_id: int, now: datetime | None = None) -> LoNapOta:
    if not _co(u, VAI_DUYET):
        raise LoiDoiSoat("Chỉ Chủ tịch duyệt lô đối soát OTA", 403)
    lo = db.get(LoNapOta, lo_id)
    if lo is None:
        raise LoiDoiSoat("Không có lô này", 404)
    if lo.trang_thai != "cho_duyet":
        raise LoiDoiSoat(f"Lô đang «{TRANG_THAI_LO[lo.trang_thai]}»")
    if lo.nap_boi == u.username:
        raise LoiDoiSoat("Người nạp không tự duyệt lô của mình", 403)
    now = now or datetime.now()
    o = db.get(DoiTacOta, lo.doi_tac_ota_id)
    ds = so_sanh(db, lo.doi_tac_ota_id, lo.dong)          # so lại lúc duyệt: sổ có thể đã đổi từ lúc nạp
    for x in ds:
        if x["thay_doi"] == "trung":
            continue
        dp = db.execute(select(DatPhongOta).where(DatPhongOta.doi_tac_ota_id == lo.doi_tac_ota_id,
                                                  DatPhongOta.khoa == x["khoa"])).scalars().first()
        if dp is None:
            dp = DatPhongOta(doi_tac_ota_id=lo.doi_tac_ota_id, khoa=x["khoa"], co_ma_rieng=x["co_ma_rieng"], phien_ban=1, lo_id=lo.id)
            db.add(dp)
            truoc = 0
        else:
            truoc = dp.hoa_hong_cent
            dp.phien_ban += 1
            dp.lo_id = lo.id
        nd = _ngay_d(x["ngay_dat"])
        dp.ngay_dat, dp.ky = nd, (nd.strftime("%Y-%m") if nd else lo.ky)
        dp.san_pham, dp.thanh_pho, dp.quoc_gia, dp.link = x["san_pham"], x["thanh_pho"], x["quoc_gia"], x["link"]
        dp.ngay_den, dp.ngay_di, dp.so_khach = _ngay_d(x["ngay_den"]), _ngay_d(x["ngay_di"]), x["so_khach"]
        dp.gia_tri_cent, dp.hoa_hong_cent = x["gia_tri_cent"], x["hoa_hong_cent"]
        dp.trang_thai_chuyen, dp.trang_thai_tt, dp.ma_luot = x["trang_thai_chuyen"], x["trang_thai_tt"], x["subid"]
        dp.cap_nhat_luc = now
        # Nối về lượt chuyển CHỈ bằng đúng mã lượt VTOS đã gắn, và chỉ khi OTA bật SubID. Không đoán.
        dp.luot_id = None
        if x["subid"] and o is not None and o.subid_cho_phep:
            l = db.execute(select(LuotChuyenOta).where(LuotChuyenOta.ma_luot == x["subid"],
                                                       LuotChuyenOta.doi_tac_ota_id == o.id)).scalars().first()
            dp.luot_id = l.id if l else None
        db.flush()
        chenh = x["hoa_hong_cent"] - truoc
        if chenh:
            db.add(SoHoaHongOta(dat_phong_id=dp.id, lo_id=lo.id, phien_ban=dp.phien_ban, tien_te="USD", chenh_cent=chenh,
                                ly_do="mới" if x["thay_doi"] == "moi" else "OTA báo thay đổi: " + ", ".join(x["truong_doi"])[:100], luc=now))
    tom = _tom(ds)
    lo.trang_thai, lo.duyet_boi, lo.duyet_luc = "da_duyet", u.username, now
    lo.ket_qua = dict(lo.ket_qua or {}, **tom)
    R.audit(db, u.username, u.role, "duyet_lo_doi_soat_ota", f"lo_nap_ota:{lo.ma}", after=tom)
    db.commit(); db.refresh(lo)
    return lo


def tu_choi(db: Session, u: User, lo_id: int, ly_do: str, now: datetime | None = None) -> LoNapOta:
    if not _co(u, VAI_DUYET):
        raise LoiDoiSoat("Chỉ Chủ tịch duyệt lô đối soát OTA", 403)
    lo = db.get(LoNapOta, lo_id)
    if lo is None:
        raise LoiDoiSoat("Không có lô này", 404)
    if lo.trang_thai != "cho_duyet":
        raise LoiDoiSoat(f"Lô đang «{TRANG_THAI_LO[lo.trang_thai]}»")
    ly_do = (ly_do or "").strip()[:300]
    if not ly_do:
        raise LoiDoiSoat("Ghi lý do từ chối để Kế toán biết cần làm gì")
    lo.trang_thai, lo.ly_do, lo.duyet_boi, lo.duyet_luc = "tu_choi", ly_do, u.username, now or datetime.now()
    R.audit(db, u.username, u.role, "tu_choi_lo_doi_soat_ota", f"lo_nap_ota:{lo.ma}", after={"ly_do": ly_do})
    db.commit(); db.refresh(lo)
    return lo


# ---------------------------------------------------------------- xem

def _co_tu(s: str, tu: tuple[str, ...]) -> bool:
    t = _chuan(s)
    return any(x in t for x in tu)


def la_huy(dp: DatPhongOta) -> bool:
    return _co_tu(dp.trang_thai_chuyen, HUY)


def lo_out(db: Session, lo: LoNapOta, u: User, chi_tiet: bool = False) -> dict:
    o = db.get(DoiTacOta, lo.doi_tac_ota_id)
    d = {"id": lo.id, "ma": lo.ma, "ota": o.ten if o else "", "ky": lo.ky, "ten_tep": lo.ten_tep, "trang_thai": lo.trang_thai,
         "trang_thai_ten": TRANG_THAI_LO[lo.trang_thai], "so_dong": lo.so_dong, "so_loi": lo.so_loi, "nap_boi": lo.nap_boi,
         "nap_luc": lo.nap_luc.isoformat(timespec="minutes"), "duyet_boi": lo.duyet_boi,
         "duyet_luc": lo.duyet_luc.isoformat(timespec="minutes") if lo.duyet_luc else None, "ly_do": lo.ly_do,
         "ket_qua": lo.ket_qua or {},
         "duyet_duoc": lo.trang_thai == "cho_duyet" and _co(u, VAI_DUYET) and lo.nap_boi != u.username}
    if chi_tiet:
        ds = so_sanh(db, lo.doi_tac_ota_id, lo.dong) if lo.trang_thai == "cho_duyet" else [dict(x, thay_doi="", truong_doi=[], hoa_hong_truoc=0) for x in lo.dong]
        d.update(tom=_tom(ds) if lo.trang_thai == "cho_duyet" else lo.ket_qua, dong=ds[:300], loi=lo.loi)
    return d


def tong_quan(db: Session, u: User) -> dict:
    otas = db.execute(select(DoiTacOta).where(DoiTacOta.san_pham == "khach_san")
                      .order_by(DoiTacOta.thu_tu, DoiTacOta.id)).scalars().all()
    ten = {o.id: o.ten for o in otas}
    so = {}
    for dp in db.execute(select(DatPhongOta)).scalars():
        k = (dp.ky, dp.doi_tac_ota_id)
        m = so.setdefault(k, {"ky": dp.ky, "ota": ten.get(dp.doi_tac_ota_id, ""), "dat_phong": 0, "huy": 0, "gia_tri_cent": 0,
                              "uoc_tinh_cent": 0, "hoan_tat_cent": 0, "da_tra_cent": 0, "noi_duoc": 0})
        if la_huy(dp):
            m["huy"] += 1
            continue
        m["dat_phong"] += 1
        m["gia_tri_cent"] += dp.gia_tri_cent
        m["uoc_tinh_cent"] += dp.hoa_hong_cent
        if _co_tu(dp.trang_thai_chuyen, XONG):
            m["hoan_tat_cent"] += dp.hoa_hong_cent
        if _co_tu(dp.trang_thai_tt, DA_TRA) and not _co_tu(dp.trang_thai_tt, ("unpaid", "not paid")):
            m["da_tra_cent"] += dp.hoa_hong_cent
        if dp.luot_id:
            m["noi_duoc"] += 1
    so_cai = int(db.execute(select(func.coalesce(func.sum(SoHoaHongOta.chenh_cent), 0))).scalar() or 0)
    los = db.execute(select(LoNapOta).order_by(LoNapOta.id.desc()).limit(50)).scalars().all()
    chua_noi = db.execute(select(func.count(DatPhongOta.id)).where(DatPhongOta.luot_id.is_(None))).scalar_one()
    return {"ota": [{"id": o.id, "ten": o.ten, "subid_cho_phep": o.subid_cho_phep, "subid_tham_so": o.subid_tham_so} for o in otas],
            "so": sorted(so.values(), key=lambda m: (m["ky"], m["ota"]), reverse=True),
            "tong_so_cai_cent": so_cai, "chua_noi": int(chua_noi), "lo": [lo_out(db, x, u) for x in los],
            "nap_duoc": _co(u, VAI_NAP), "duyet_duoc": _co(u, VAI_DUYET), "tien_te": "USD"}


def dat_phong_cua(db: Session, luot_ids: list[int]) -> list[dict]:
    """Đặt phòng đã xác minh nối được về các lượt chuyển của một tài khoản — KHÔNG có hoa hồng."""
    if not luot_ids:
        return []
    otas = {o.id: o.ten for o in db.execute(select(DoiTacOta)).scalars()}
    ra = []
    for dp in db.execute(select(DatPhongOta).where(DatPhongOta.luot_id.in_(luot_ids)).order_by(DatPhongOta.ngay_dat.desc())).scalars():
        tt = "Đã hủy" if la_huy(dp) else ("Đã hoàn tất" if _co_tu(dp.trang_thai_chuyen, XONG) else "Đã đặt")
        ra.append({"ota": otas.get(dp.doi_tac_ota_id, ""), "thanh_pho": dp.thanh_pho,
                   "ngay_den": dp.ngay_den.isoformat() if dp.ngay_den else None,
                   "ngay_di": dp.ngay_di.isoformat() if dp.ngay_di else None, "trang_thai": tt})
    return ra


def ma_luot_moi(db: Session) -> str:
    while True:
        m = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")[:8]
        if not db.execute(select(LuotChuyenOta.id).where(LuotChuyenOta.ma_luot == m)).first():
            return m
