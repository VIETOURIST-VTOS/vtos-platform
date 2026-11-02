"""DH-1 · Hoa hồng đối tác bán hàng theo D06 — Chủ tịch chốt 26/10/2026, duyệt bản xem thử cùng ngày.

LUẬT (đúng lời chốt, không thêm):
  · Đại lý:  3% × 200 triệu đầu + 3,5% × phần trên 200 đến 500 triệu + 4% × phần trên 500 triệu.
  · CTV bán hàng: 2% × 50 triệu đầu + 2,5% × phần trên 50 đến 150 triệu + 3% × phần trên 150 triệu.
  · Lũy tiến TỪNG PHẦN; tính theo tháng dương lịch giờ Việt Nam; tháng mới bắt đầu lại từ 0; KHÔNG giới
    hạn tiền hoa hồng. Không áp tỷ lệ cao nhất cho toàn bộ doanh số.
  · Doanh số đủ điều kiện = giá trị booking SAU GIẢM GIÁ (amount − discount) của booking không hủy, gắn
    đối tác, khi tour đã kết thúc VÀ khách đã trả đủ; vào tháng của NGÀY MUỘN HƠN trong hai mốc ấy.
  · Đối tác hưởng theo hình thức đã chọn (đại lý D06 / CTV D06 / giá NET). CHƯA CHỌN = KHÔNG TÍNH.
  · Chương trình chỉ sinh tiền thật từ tham số `d06_hieu_luc_tu` (Chủ tịch ký). Rỗng = tính thử.

PHÉP TÍNH: số nguyên đồng, tỷ lệ basis point, cộng phân số chính xác rồi làm tròn HALF_UP MỘT lần trên
tổng kỳ. Cơ bản = làm tròn(D × tỷ lệ cơ bản); thưởng vượt bậc = tổng − cơ bản.

SỔ CHỈ GHI THÊM: tính lại ghi phần chênh so với đã ghi; chạy lại cùng nguồn không ghi thêm gì. Hoàn / hủy
sau khi chốt ghi dòng âm vào ĐÚNG KỲ GỐC (sau_chot=True). Quyền hưởng trừ đã trả âm thì hiện vượt chi —
không che bằng 0, không tự trừ tiền đối tác.
"""
import json
from datetime import date, datetime, timedelta
from fractions import Fraction

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour, User, Company
from app.models.payments import Receipt
from app.models.ops import PaymentRequest
from app.models.doi_tac_ban_hang import DoiTacBanHang
from app.models.hoa_hong_d06 import HinhThucHoaHong, KyHoaHong, SoHoaHong, ChiHoaHong, HINH_THUC
from app.services import rules as R

KHOA_HIEU_LUC = "d06_hieu_luc_tu"
# (từ, đến, bps) — `đến` None là không trần.
BAC = {
    "dai_ly_d06": {"co_ban": 300, "bac": ((0, 200_000_000, 300), (200_000_000, 500_000_000, 350), (500_000_000, None, 400))},
    "ctv_d06": {"co_ban": 200, "bac": ((0, 50_000_000, 200), (50_000_000, 150_000_000, 250), (150_000_000, None, 300))},
}
CHUONG_TRINH = tuple(BAC)
TOUR_CHUA_CHAY = ("nhap", "cho_xac_nhan", "cho_duyet", "huy")
VAI_XEM = ("chutich", "tgd", "bks", "robot_ks", "ketoan", "gd_kd")
VAI_KE_TOAN = ("ketoan",)                       # tính lại, chốt kỳ, lập đề nghị chi (Chủ tịch, TGĐ qua toàn quyền)
VAI_HINH_THUC = ("gd_kd", "ketoan", "chutich", "tgd")


class LoiD06(ValueError):
    pass


# ---------------------------------------------------------------- phép tính thuần

def _lam_tron(x: Fraction) -> int:
    """HALF_UP cho số không âm và âm (đối xứng quanh 0)."""
    s = -1 if x < 0 else 1
    x = abs(x)
    n = x.numerator // x.denominator
    return s * (n + (1 if (x - n) >= Fraction(1, 2) else 0))


def quyen_huong(d: int, chuong_trinh: str) -> dict:
    """{tong, co_ban, thuong, bac: [(từ, đến, bps, phần doanh số, tiền)]} cho doanh số tháng d (đồng)."""
    cfg = BAC[chuong_trinh]
    tong = Fraction(0)
    bac = []
    for tu, den, bps in cfg["bac"]:
        phan = max(0, (d if den is None else min(d, den)) - tu)
        tien = Fraction(phan * bps, 10_000)
        tong += tien
        bac.append({"tu": tu, "den": den, "bps": bps, "doanh_so": phan, "tien": _lam_tron(tien)})
    t = _lam_tron(tong)
    cb = _lam_tron(Fraction(d * cfg["co_ban"], 10_000))
    return {"tong": t, "co_ban": cb, "thuong": t - cb, "bac": bac}


def _tien_chinh_xac(d: int, chuong_trinh: str) -> Fraction:
    return sum((Fraction(max(0, (d if den is None else min(d, den)) - tu) * bps, 10_000) for tu, den, bps in BAC[chuong_trinh]["bac"]),
               Fraction(0))


def phan_bo_don(nguon: list[dict], chuong_trinh: str) -> list[dict]:
    """KS-16h: phần hoa hồng của TỪNG ĐƠN trong bậc lũy tiến tháng — xếp theo ngày đủ điều kiện, mỗi đơn lấy phần
    tăng thêm của tổng khi cộng doanh số của mình. Tổng phần = tổng kỳ (phần dư làm tròn dồn vào đơn cuối)."""
    ra, luy, da = [], 0, 0
    tong = quyen_huong(sum(x["doanh_so"] for x in nguon), chuong_trinh)["tong"] if chuong_trinh in BAC else 0
    ds = sorted(nguon, key=lambda x: (x.get("thu_du") or "", x.get("ket_thuc") or "", x.get("booking") or ""))
    for i, x in enumerate(ds):
        truoc, sau = luy, luy + x["doanh_so"]
        if chuong_trinh in BAC:
            phan = tong - da if i == len(ds) - 1 else _lam_tron(_tien_chinh_xac(sau, chuong_trinh) - _tien_chinh_xac(truoc, chuong_trinh))
            bps = sorted({b for t, dn, b in BAC[chuong_trinh]["bac"] if (dn is None or truoc < dn) and sau > t})
        else:
            phan, bps = 0, []
        da += phan
        luy = sau
        ra.append(dict(x, hoa_hong=phan, bac_bps=bps))
    return ra


def bac_hien_tai(d: int, chuong_trinh: str) -> dict:
    for tu, den, bps in BAC[chuong_trinh]["bac"]:
        if den is None or d < den:
            return {"bps": bps, "toi_da": den is None, "con_toi_bac_sau": None if den is None else den - d}
    return {}


# ---------------------------------------------------------------- tham số, hình thức

def hieu_luc_tu(db: Session) -> date | None:
    from app.services import moi_truong_du_lieu as MT
    try:
        return MT.doc_ngay(str(R.get_param_chu(db, KHOA_HIEU_LUC)).strip())
    except (KeyError, ValueError):
        return None


def dau_thang(ky: str) -> date:
    y, m = map(int, ky.split("-"))
    return date(y, m, 1)


KHOA_V3 = "d06_v3_tu"


def v3_tu(db: Session) -> date | None:
    from app.services import moi_truong_du_lieu as MT
    try:
        return MT.doc_ngay(str(R.get_param_chu(db, KHOA_V3)).strip())
    except (KeyError, ValueError):
        return None


def la_v3(db: Session, ky: str) -> bool:
    """KS-16h: kỳ này tính D06 theo đề xuất v3 (loại VAT, chỉ tour có phụ lục, bỏ đặt bàn)?"""
    v = v3_tu(db)
    return v is not None and dau_thang(ky) >= date(v.year, v.month, 1)


def doanh_so_d06(net: int, tour: Tour | None) -> int:
    """Doanh số D06 theo v3: giá sau giảm ÷ (1 + %VAT của tour), số nguyên đồng làm tròn HALF_UP."""
    vat = Fraction(str(getattr(tour, "vat_pct", 0) or 0))
    return _lam_tron(Fraction(net) / (1 + vat / 100))


def dang_bat(db: Session, ky: str) -> bool:
    h = hieu_luc_tu(db)
    return h is not None and dau_thang(ky) >= date(h.year, h.month, 1)


def hinh_thuc_cua(db: Session, doi_tac_id: int, ky: str) -> str:
    """Hình thức có hiệu lực cho tháng `ky` — dòng mới nhất có hiệu lực từ ≤ đầu tháng. Rỗng = chưa chọn."""
    r = db.execute(select(HinhThucHoaHong).where(HinhThucHoaHong.doi_tac_id == doi_tac_id,
                                                 HinhThucHoaHong.hieu_luc_tu <= dau_thang(ky))
                   .order_by(HinhThucHoaHong.hieu_luc_tu.desc(), HinhThucHoaHong.id.desc())).scalars().first()
    return r.hinh_thuc if r else ""


def dat_hinh_thuc(db: Session, u: User, doi_tac_id: int, hinh_thuc: str, hom_nay: date | None = None) -> HinhThucHoaHong:
    """Đổi hình thức CÓ HIỆU LỰC TỪ ĐẦU THÁNG KẾ TIẾP — không đổi kỳ đang mở. Lần chọn đầu tiên (chưa từng
    có dòng nào) có hiệu lực từ đầu THÁNG NÀY, để đối tác mới không mất một tháng doanh số."""
    if hinh_thuc not in HINH_THUC:
        raise LoiD06("Hình thức không hợp lệ")
    dt = db.get(DoiTacBanHang, doi_tac_id)
    if dt is None:
        raise LoiD06("Không có đối tác này")
    hn = hom_nay or _hom_nay()
    co = db.execute(select(HinhThucHoaHong.id).where(HinhThucHoaHong.doi_tac_id == doi_tac_id)).first()
    tu = date(hn.year, hn.month, 1) if co is None else (date(hn.year + (hn.month == 12), hn.month % 12 + 1, 1))
    r = HinhThucHoaHong(doi_tac_id=doi_tac_id, hinh_thuc=hinh_thuc, hieu_luc_tu=tu, boi=u.username, luc=datetime.now())
    db.add(r)
    R.audit(db, u.username, u.role, "d06_dat_hinh_thuc", f"doi_tac:{doi_tac_id}", after={"hinh_thuc": hinh_thuc, "tu": tu.isoformat()})
    db.commit(); db.refresh(r)
    return r


def _hom_nay() -> date:
    from app.services.ops import gio_vn
    return gio_vn().date()


# ---------------------------------------------------------------- nguồn doanh số

def _ngay_thu_du(db: Session, b: Booking, net: int) -> date | None:
    if net <= 0:
        return None
    luy = 0.0
    for r in db.execute(select(Receipt).where(Receipt.booking_id == b.id, Receipt.status != "huy")
                        .order_by(Receipt.created_at, Receipt.id)).scalars():
        luy += float(r.amount or 0)
        if luy + 0.5 >= net:
            return (r.confirmed_at or r.created_at).date()
    return None


def tinh_trang_booking(db: Session, b: Booking, tour: Tour | None, hom_nay: date) -> dict:
    net = int(round((b.amount or 0) - (b.discount or 0)))
    ket_thuc = tour.end_date if tour is not None else None
    if tour is None or tour.status in TOUR_CHUA_CHAY or ket_thuc is None or ket_thuc > hom_nay:
        return {"du": False, "ly_do": "tour chưa kết thúc", "net": net, "ket_thuc": ket_thuc, "thu_du": None}
    du = _ngay_thu_du(db, b, net)
    if du is None:
        return {"du": False, "ly_do": "khách chưa trả đủ", "net": net, "ket_thuc": ket_thuc, "thu_du": None}
    return {"du": True, "ngay": max(ket_thuc, du), "net": net, "ket_thuc": ket_thuc, "thu_du": du}


def nguon_thang(db: Session, ky: str, hom_nay: date | None = None) -> dict:
    """{(doi_tac_id, company_key): [nguồn]} của tháng ky, cùng danh sách chưa đủ điều kiện."""
    hn = hom_nay or _hom_nay()
    d0 = dau_thang(ky)
    d1 = date(d0.year + (d0.month == 12), d0.month % 12 + 1, 1)
    nhom, chua = {}, []
    tours = {}
    v3 = la_v3(db, ky)
    for b in db.execute(select(Booking).where(Booking.doi_tac_id != None, Booking.cancelled == False)).scalars():  # noqa: E711,E712
        t = tours.get(b.tour_id) or db.get(Tour, b.tour_id)
        tours[b.tour_id] = t
        tt = tinh_trang_booking(db, b, t, hn)
        if tt["du"] and v3 and d0 <= tt["ngay"] < d1 and not getattr(t, "d06_phu_luc", False):
            chua.append({"booking": b.code, "doi_tac_id": b.doi_tac_id, "ly_do": "tour chưa có phụ lục hoa hồng", "net": tt["net"],
                         "con_thieu": None})
            continue
        if not tt["du"]:
            # Chỉ báo những booking sắp rơi vào tháng đang xem: tour kết thúc trong tháng hoặc trước đó.
            if tt["ket_thuc"] is None or tt["ket_thuc"] < d1:
                chua.append({"booking": b.code, "doi_tac_id": b.doi_tac_id, "ly_do": tt["ly_do"], "net": tt["net"],
                             "con_thieu": max(0, tt["net"] - int(round(b.paid or 0))) if tt["ly_do"] == "khách chưa trả đủ" else None})
            continue
        if not (d0 <= tt["ngay"] < d1):
            continue
        nhom.setdefault((b.doi_tac_id, b.company_id or 0), []).append({
            "booking_id": b.id, "booking": b.code, "tour": t.code if t else "", "ten_tour": t.name if t else "",
            "ket_thuc": tt["ket_thuc"].isoformat(), "thu_du": tt["thu_du"].isoformat(),
            "doanh_so": doanh_so_d06(tt["net"], t) if v3 else tt["net"], "gia_sau_giam": tt["net"],
            "vat_pct": float(getattr(t, "vat_pct", 0) or 0) if v3 else None})
    # DT-2 (Chủ tịch 28/10/2026): đơn đặt bàn qua đối tác cộng vào doanh số D06 khi nhà hàng báo khách đã
    # dùng VÀ Kế toán đã chốt doanh số — cùng bậc lũy tiến với tour.
    # KS-16h (Chủ tịch 31/10/2026, theo v3): từ kỳ áp v3, đặt bàn KHÔNG vào bậc D06 (hoa hồng đặt bàn theo phụ lục riêng).
    if not v3:
        from app.services import dat_ban as DB
        for k, v in DB.nguon_d06(db, d0, d1).items():
            nhom.setdefault(k, []).extend(v)
    return {"nhom": nhom, "chua_du": chua}


# ---------------------------------------------------------------- sổ

def _da_ghi(db: Session, ky: KyHoaHong) -> dict:
    rows = db.execute(select(SoHoaHong.thanh_phan, func.coalesce(func.sum(SoHoaHong.so_tien), 0))
                      .where(SoHoaHong.ky_id == ky.id).group_by(SoHoaHong.thanh_phan)).all()
    d = {"BASE": 0, "BONUS": 0}
    for k, v in rows:
        d[k] = int(v)
    return d


def _chi(db: Session, ky: KyHoaHong) -> dict:
    da_tra = dang = 0
    for c, pr in db.execute(select(ChiHoaHong, PaymentRequest).join(PaymentRequest, PaymentRequest.id == ChiHoaHong.payment_request_id)
                            .where(ChiHoaHong.ky_id == ky.id)).all():
        if pr.status == "da_chi":
            da_tra += (c.so_tien or 0)
        elif pr.status != "tu_choi":
            dang += (c.so_tien or 0)
    return {"da_tra": da_tra, "dang_de_nghi": dang}


def _lay_ky(db: Session, doi_tac_id: int, company_key: int, ky: str, ct: str, tao: bool) -> KyHoaHong | None:
    k = db.execute(select(KyHoaHong).where(KyHoaHong.doi_tac_id == doi_tac_id, KyHoaHong.company_key == company_key,
                                           KyHoaHong.ky == ky, KyHoaHong.chuong_trinh == ct)).scalars().first()
    if k is None and tao:
        k = KyHoaHong(doi_tac_id=doi_tac_id, company_key=company_key, company_id=company_key or None, ky=ky, chuong_trinh=ct)
        db.add(k); db.flush()
    return k


def tinh_lai(db: Session, u: User, ky: str, hom_nay: date | None = None) -> dict:
    """Tính lại MỌI kỳ của tháng `ky` và ghi phần chênh vào sổ. Chạy lại cùng nguồn: không ghi thêm."""
    if not dang_bat(db, ky):
        raise LoiD06("D06 chưa có hiệu lực cho tháng này (tham số «d06_hieu_luc_tu» trống hoặc sau tháng này) — chỉ xem tính thử")
    ng = nguon_thang(db, ky, hom_nay)
    khoa = set(ng["nhom"])
    for k in db.execute(select(KyHoaHong).where(KyHoaHong.ky == ky)).scalars():
        khoa.add((k.doi_tac_id, k.company_key))
    ghi = 0
    for dt_id, ck in sorted(khoa):
        ct = hinh_thuc_cua(db, dt_id, ky)
        cu = [k for k in db.execute(select(KyHoaHong).where(KyHoaHong.doi_tac_id == dt_id, KyHoaHong.company_key == ck,
                                                          KyHoaHong.ky == ky)).scalars()]
        cac_ct = set(k.chuong_trinh for k in cu) | ({ct} if ct in CHUONG_TRINH else set())
        for c in sorted(cac_ct):
            nguon = ng["nhom"].get((dt_id, ck), []) if c == ct else []   # đổi hình thức giữa chừng: kỳ cũ về 0
            d = sum(x["doanh_so"] for x in nguon)
            q = quyen_huong(d, c)
            k = _lay_ky(db, dt_id, ck, ky, c, tao=True)
            da = _da_ghi(db, k)
            chenh = {"BASE": q["co_ban"] - da["BASE"], "BONUS": q["thuong"] - da["BONUS"]}
            if any(chenh.values()):
                k.revision += 1
                for tp, v in chenh.items():
                    if v:
                        db.add(SoHoaHong(ky_id=k.id, revision=k.revision, thanh_phan=tp, so_tien=v, doanh_so=d,
                                         sau_chot=k.trang_thai == "da_chot", boi=u.username, luc=datetime.now(),
                                         nguon=json.dumps(nguon, ensure_ascii=False),
                                         ly_do="điều chỉnh sau chốt — tính lại kỳ gốc" if k.trang_thai == "da_chot" else "tính kỳ"))
                        ghi += 1
            k.doanh_so, k.co_ban, k.thuong, k.thu, k.tinh_luc = d, q["co_ban"], q["thuong"], False, datetime.now()
    R.audit(db, u.username, u.role, "d06_tinh_lai", f"ky:{ky}", after={"dong_so_ghi": ghi})
    db.commit()
    return {"message": f"Đã tính lại kỳ {ky}: {ghi} dòng sổ mới" if ghi else f"Kỳ {ky}: không có gì thay đổi"}


def chot(db: Session, u: User, ky_id: int) -> KyHoaHong:
    k = db.get(KyHoaHong, ky_id)
    if k is None:
        raise LoiD06("Không có kỳ này")
    if not dang_bat(db, k.ky):
        raise LoiD06("D06 chưa có hiệu lực cho tháng này — không chốt được kỳ tính thử")
    if k.trang_thai == "da_chot":
        raise LoiD06("Kỳ đã chốt")
    d0 = dau_thang(k.ky)
    if _hom_nay() < date(d0.year + (d0.month == 12), d0.month % 12 + 1, 1):
        raise LoiD06("Tháng chưa kết thúc — chưa chốt được")
    k.trang_thai, k.chot_boi, k.chot_luc = "da_chot", u.username, datetime.now()
    R.audit(db, u.username, u.role, "d06_chot_ky", f"ky_hoa_hong:{k.id}", after={"ky": k.ky, "tong": k.co_ban + k.thuong})
    db.commit(); db.refresh(k)
    return k


def de_nghi_chi(db: Session, u: User, ky_id: int) -> PaymentRequest:
    from app.services import ops as O
    k = db.get(KyHoaHong, ky_id)
    if k is None:
        raise LoiD06("Không có kỳ này")
    if k.trang_thai != "da_chot":
        raise LoiD06("Chốt kỳ trước rồi mới lập đề nghị chi")
    if not dang_bat(db, k.ky):
        raise LoiD06("D06 chưa có hiệu lực cho tháng này")
    da = _da_ghi(db, k)
    c = _chi(db, k)
    con = da["BASE"] + da["BONUS"] - c["da_tra"] - c["dang_de_nghi"]
    # KS-16h: kỳ theo v3 phải qua đối soát với đối tác; chỉ chi phần đã thống nhất (đơn khiếu nại tách riêng).
    from app.services import doi_soat_doi_tac as DS
    try:
        duoc = DS.so_duoc_chi(db, k)
    except DS.LoiDoiSoat as ex:
        raise LoiD06(str(ex))
    if duoc is not None:
        con = min(con, duoc - c["da_tra"] - c["dang_de_nghi"])
    if con <= 0:
        raise LoiD06("Không còn số nào để đề nghị chi" + (" — kỳ đang VƯỢT CHI, lập hồ sơ thu hồi" if con < 0 else ""))
    dt = db.get(DoiTacBanHang, k.doi_tac_id)
    r = O.create_request(db, u, {"category": "hoa_hong", "supplier_name": dt.ten, "supplier_tax_code": dt.ma_so_thue or "",
                                 "amount": con, "description": f"Hoa hồng D06 kỳ {k.ky} — {dt.ten} ({HINH_THUC[k.chuong_trinh]})"})
    r.company_id = k.company_id
    db.add(ChiHoaHong(ky_id=k.id, payment_request_id=r.id, so_tien=con, boi=u.username, luc=datetime.now()))
    R.audit(db, u.username, u.role, "d06_de_nghi_chi", f"ky_hoa_hong:{k.id}", after={"de_nghi": r.code, "so_tien": con})
    db.commit(); db.refresh(r)
    return r


# ---------------------------------------------------------------- màn hình

def tong_hop(db: Session, ky: str, hom_nay: date | None = None) -> dict:
    bat = dang_bat(db, ky)
    ng = nguon_thang(db, ky, hom_nay)
    dts = {d.id: d for d in db.execute(select(DoiTacBanHang)).scalars()}
    cty = {c.id: c.code for c in db.execute(select(Company)).scalars()}
    dong, chua_chon, net = [], {}, {}
    khoa = set(ng["nhom"]) | {(k.doi_tac_id, k.company_key) for k in db.execute(select(KyHoaHong).where(KyHoaHong.ky == ky)).scalars()}
    for dt_id, ck in sorted(khoa):
        ct = hinh_thuc_cua(db, dt_id, ky)
        nguon = ng["nhom"].get((dt_id, ck), [])
        d_song = sum(x["doanh_so"] for x in nguon)
        if ct not in CHUONG_TRINH and nguon:
            (net if ct == "gia_net" else chua_chon).setdefault(dt_id, {"doi_tac_id": dt_id, "ten": dts[dt_id].ten if dt_id in dts else dt_id,
                                                                       "loai": dts[dt_id].loai if dt_id in dts else "", "so_booking": 0, "doanh_so": 0})
            m = (net if ct == "gia_net" else chua_chon)[dt_id]
            m["so_booking"] += len(nguon); m["doanh_so"] += d_song
        ky_rows = db.execute(select(KyHoaHong).where(KyHoaHong.doi_tac_id == dt_id, KyHoaHong.company_key == ck, KyHoaHong.ky == ky)).scalars().all()
        cac = {k.chuong_trinh: k for k in ky_rows}
        for c in sorted(set(cac) | ({ct} if ct in CHUONG_TRINH else set())):
            k = cac.get(c)
            d = d_song if c == ct else 0
            q = quyen_huong(d, c)           # số sống — dùng khi chưa ghi sổ (tính thử) và để báo "chưa tính lại"
            da = _da_ghi(db, k) if k else {"BASE": 0, "BONUS": 0}
            ch = _chi(db, k) if k else {"da_tra": 0, "dang_de_nghi": 0}
            dieu_chinh = int(db.execute(select(func.coalesce(func.sum(SoHoaHong.so_tien), 0)).where(
                SoHoaHong.ky_id == k.id, SoHoaHong.sau_chot == True)).scalar() or 0) if k else 0   # noqa: E712
            ghi = bool(k and k.revision)
            tong = (da["BASE"] + da["BONUS"]) if ghi else q["tong"]
            dong.append({
                "ky_id": k.id if k else None, "doi_tac_id": dt_id, "ten": dts[dt_id].ten if dt_id in dts else str(dt_id),
                "company_key": ck, "phap_nhan": cty.get(ck, "Chưa gán pháp nhân"), "chuong_trinh": c, "hinh_thuc_ten": HINH_THUC[c],
                "doanh_so": (k.doanh_so if ghi else d), "co_ban": da["BASE"] if ghi else q["co_ban"], "thuong": da["BONUS"] if ghi else q["thuong"],
                "tong": tong, "dieu_chinh": dieu_chinh, "da_tra": ch["da_tra"], "dang_de_nghi": ch["dang_de_nghi"],
                "con_phai_tra": tong - ch["da_tra"], "co_the_de_nghi": tong - ch["da_tra"] - ch["dang_de_nghi"],
                "trang_thai": k.trang_thai if k else "mo", "da_ghi_so": ghi,
                "can_tinh_lai": bool(ghi and (q["co_ban"] != da["BASE"] or q["thuong"] != da["BONUS"])),
                "bac": q["bac"], "bac_hien_tai": bac_hien_tai(d, c), "nguon": phan_bo_don(nguon, c) if c == ct else [],
                "so": [{"revision": s.revision, "thanh_phan": s.thanh_phan, "so_tien": s.so_tien, "sau_chot": s.sau_chot,
                        "ly_do": s.ly_do, "boi": s.boi, "luc": s.luc.isoformat() if s.luc else None}
                       for s in db.execute(select(SoHoaHong).where(SoHoaHong.ky_id == k.id).order_by(SoHoaHong.id)).scalars()] if k else [],
            })
    dong.sort(key=lambda x: (-x["doanh_so"], x["ten"]))
    return {"ky": ky, "dang_bat": bat, "hieu_luc_tu": (hieu_luc_tu(db).isoformat() if hieu_luc_tu(db) else None),
            "v3": la_v3(db, ky), "v3_tu": (v3_tu(db).isoformat() if v3_tu(db) else None),
            "bac": {c: {"co_ban": v["co_ban"], "bac": [list(b) for b in v["bac"]]} for c, v in BAC.items()},
            "dong": dong, "chua_chon": list(chua_chon.values()), "gia_net": list(net.values()),
            "chua_du": [dict(x, ten=dts[x["doi_tac_id"]].ten if x["doi_tac_id"] in dts else "") for x in ng["chua_du"]],
            "tong": {"doanh_so": sum(x["doanh_so"] for x in dong), "quyen_huong": sum(x["tong"] for x in dong),
                     "da_tra": sum(x["da_tra"] for x in dong), "con_phai_tra": sum(x["con_phai_tra"] for x in dong)},
            "hinh_thuc_chon": HINH_THUC,
            "doi_tac": [{"id": d.id, "ten": d.ten, "loai": d.loai, "hinh_thuc": hinh_thuc_cua(db, d.id, ky),
                         "hinh_thuc_thang_sau": hinh_thuc_cua(db, d.id, (dau_thang(ky) + timedelta(days=32)).strftime("%Y-%m"))}
                        for d in dts.values() if d.dang_hieu_luc(dau_thang(ky)) or d.hieu_luc_den is None]}
