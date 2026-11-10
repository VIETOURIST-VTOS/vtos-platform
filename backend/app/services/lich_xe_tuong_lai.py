"""VH-9 · LỊCH XE 90 NGÀY TỚI — công suất và khoảng trống để phòng Kinh doanh đẩy bán (Chủ tịch duyệt 11/11/2026).

Mọi con số đọc từ thứ ĐÃ CÓ trong hệ thống, không ai phải nhập thêm:
  · ngày có lệnh  = lệnh điều xe chưa huỷ phủ ngày ấy (DispatchOrder.date_from..date_to);
  · ngày theo sheet = chuyến đội xe đã ghi trước vào Google Sheet xe (VH-15, Chủ tịch 11/11/2026: đội xe
                    ghi trước chuyến sắp chạy; VTOS chưa có lệnh nào nên chỉ đọc lệnh thì cả đội «trống
                    100%»). Ngày có lệnh VTOS thì lệnh thắng; sheet chỉ lấp ngày chưa có lệnh;
  · xe bị chặn    = báo hỏng mức «phải dừng xe» chưa đóng — KHÔNG biết ngày xong, nên xe ấy KHÔNG được tính là
                    trống ngày nào cả (tính là trống thì Kinh doanh bán một chiếc xe đang nằm xưởng);
  · đề nghị chờ   = đề nghị xe chưa có lệnh. Đề nghị chưa gắn xe, nên nó là SỐ XE ĐANG ĐƯỢC HỎI theo ngày, không
                    tô lên hàng của một xe cụ thể nào.

Công suất = ngày-xe có lệnh / ngày-xe khả dụng (xe đang khai thác, không bị chặn). Không chia cho số ngày lịch
của cả đội: xe đang hỏng không bán được, đưa nó vào mẫu số là làm công suất trông thấp hơn sự thật.
"""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.de_nghi_xe import DeNghiXe
from app.models.fleet import Fault
from app.models.hr import DispatchOrder, Vehicle

SO_NGAY = 90
KHOANG_TOI_THIEU = 2          # khoảng trống từ 2 ngày liền trở lên mới đáng đem bán
NGUONG_THAP = 40              # % — tuần dưới mức này tô vàng: cần đẩy bán
NGUOI_NHAN_TUAN = ("chutich", "tgd", "tp_dh", "gd_kd", "tp_kd", "ptgd_mkt", "ptgd_doan")
HONG_CON_MO = ("moi", "da_tiep_nhan")


def _xe_khai_thac(db: Session) -> list[Vehicle]:
    return [v for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars()
            if getattr(v, "active", True) and (getattr(v, "lifecycle", "") or "dang_khai_thac") == "dang_khai_thac"]


def bang(db: Session, tu: date | None = None, so_ngay: int = SO_NGAY, tai_sheet=None) -> dict:
    tu = tu or date.today()
    so_ngay = max(7, min(int(so_ngay or SO_NGAY), 180))
    ngay = [tu + timedelta(days=i) for i in range(so_ngay)]
    den = ngay[-1]
    xe = _xe_khai_thac(db)
    ids = {v.id for v in xe}

    chan: dict[int, str] = {}
    for f in db.execute(select(Fault).where(Fault.trang_thai.in_(HONG_CON_MO), Fault.muc_do == "phai_dung_xe")
                        .order_by(Fault.id.desc())).scalars():
        if f.vehicle_id in ids:
            chan.setdefault(f.vehicle_id, f.hien_tuong)

    lenh: dict[int, set[int]] = {v.id: set() for v in xe}
    for d in db.execute(select(DispatchOrder).where(DispatchOrder.status != "huy",
                                                    DispatchOrder.date_to >= tu,
                                                    DispatchOrder.date_from <= den)).scalars():
        if d.vehicle_id not in lenh or d.date_from is None or d.date_to is None:
            continue
        for i in range(max(0, (d.date_from - tu).days), min(so_ngay - 1, (d.date_to - tu).days) + 1):
            lenh[d.vehicle_id].add(i)

    # VH-15 · chuyến ghi trước trên Google Sheet xe — khớp xe theo NĂM SỐ CUỐI biển số (cách sheet ghi xe).
    from app.services import xe_theo_sheet as XS
    sh = XS.chuyen_trong_khoang(db, tu, den, **({"tai": tai_sheet} if tai_sheet else {}))
    theo_sheet: dict[int, dict[int, str]] = {v.id: {} for v in xe}
    khoa_xe = {XS.nam_so_cuoi(v.plate): v.id for v in xe if XS.nam_so_cuoi(v.plate)}
    for k, ds in sh["theo_khoa"].items():
        vid = khoa_xe.get(k)
        if vid is None:
            continue
        for di, ve, tour in ds:
            for i in range(max(0, (di - tu).days), min(so_ngay - 1, (ve - tu).days) + 1):
                if i not in lenh[vid]:
                    theo_sheet[vid][i] = tour

    hoi = [0] * so_ngay           # số xe đang được hỏi (đề nghị chờ lệnh) theo ngày
    so_de_nghi, ngay_xe_hoi = 0, 0
    for dn in db.execute(select(DeNghiXe).where(DeNghiXe.trang_thai == "cho_lap_lenh",
                                                DeNghiXe.ngay_ve >= tu, DeNghiXe.ngay_di <= den)).scalars():
        so_de_nghi += 1
        for i in range(max(0, (dn.ngay_di - tu).days), min(so_ngay - 1, (dn.ngay_ve - tu).days) + 1):
            hoi[i] += dn.so_xe_can or 1
            ngay_xe_hoi += dn.so_xe_can or 1

    hang, khoang = [], []
    for v in xe:
        bi_chan = v.id in chan
        o = ["chan" if bi_chan else ("lenh" if i in lenh[v.id] else ("sheet" if i in theo_sheet[v.id] else ""))
             for i in range(so_ngay)]
        dung = len(lenh[v.id]) + len(theo_sheet[v.id])
        hang.append({"id": v.id, "xe": v.plate, "ma": v.code or "", "so_cho": v.seats or 0, "o": o,
                     "tour_sheet": {str(i): t for i, t in theo_sheet[v.id].items()},
                     "bi_chan": chan.get(v.id, ""),
                     "cong_suat": None if bi_chan else round(dung * 100 / so_ngay)})
        if bi_chan:
            continue
        i = 0
        while i < so_ngay:
            if o[i]:
                i += 1
                continue
            j = i
            while j + 1 < so_ngay and not o[j + 1]:
                j += 1
            if j - i + 1 >= KHOANG_TOI_THIEU:
                khoang.append({"xe": v.plate, "so_cho": v.seats or 0, "tu": ngay[i], "den": ngay[j],
                               "so_ngay": j - i + 1,
                               "cuoi_tuan": any(ngay[k].weekday() >= 5 for k in range(i, j + 1))})
            i = j + 1
    khoang.sort(key=lambda k: (k["tu"], -k["so_ngay"]))

    kha_dung = [h for h in hang if not h["bi_chan"]]

    def cs(a: int, b: int) -> int | None:
        tong = len(kha_dung) * (b - a)
        if tong <= 0:
            return None
        return round(sum(1 for h in kha_dung for i in range(a, b) if h["o"][i] in ("lenh", "sheet")) * 100 / tong)

    tuan = []
    for a in range(0, so_ngay, 7):
        b = min(so_ngay, a + 7)
        tuan.append({"tu": ngay[a], "den": ngay[b - 1], "nhan": f"T{ngay[a].isocalendar()[1]}",
                     "cong_suat": cs(a, b)})
    trong = sum(1 for h in kha_dung for x in h["o"] if not x)
    trong_cuoi_tuan = sum(1 for h in kha_dung for i, x in enumerate(h["o"]) if not x and ngay[i].weekday() >= 5)
    return {
        "tu": tu, "den": den, "so_ngay": so_ngay, "ngay": ngay, "xe": hang, "hoi_theo_ngay": hoi,
        "cong_suat_30": cs(0, min(30, so_ngay)), "cong_suat_31_60": cs(30, min(60, so_ngay)) if so_ngay > 30 else None,
        "ngay_xe_trong": trong, "ngay_xe_trong_cuoi_tuan": trong_cuoi_tuan,
        "de_nghi_cho": so_de_nghi, "ngay_xe_de_nghi": ngay_xe_hoi,
        "tuan": tuan, "nguong_thap": NGUONG_THAP, "khoang_trong": khoang,
        "ghi_chu": "Xe đang có báo hỏng «phải dừng xe» không tính là trống ngày nào — chưa biết ngày sửa xong.",
        "sheet": {"co_link": sh["co_link"], "loi": sh["loi"], "doc_luc": sh["doc_luc"], "so_chuyen": sh["so_chuyen"]},
        "so_ngay_lenh": sum(1 for h in hang for x in h["o"] if x == "lenh"),
    }


def khoang_trong_cho_kinh_doanh(db: Session, tu: date | None = None) -> dict:
    """Phần phòng Kinh doanh được xem: khoảng trống và công suất theo tuần — không tên tour, không giá."""
    b = bang(db, tu)
    return {"tu": b["tu"], "den": b["den"], "khoang_trong": b["khoang_trong"], "tuan": b["tuan"],
            "nguong_thap": b["nguong_thap"], "cong_suat_30": b["cong_suat_30"], "sheet": b["sheet"]}


def chua_du_du_lieu(b: dict) -> str | None:
    """VH-15: lý do KHÔNG được báo «xe trống» — sheet đọc hỏng, hoặc chưa có link sheet mà cũng chưa có lệnh
    nào. Báo trống trong hai trường hợp ấy là bảo Kinh doanh bán những ngày xe đã có khách."""
    if b["sheet"]["loi"]:
        return f"Chưa đọc được Sheet xe: {b['sheet']['loi']}"
    if not b["sheet"]["co_link"] and not b["so_ngay_lenh"]:
        return "Chưa có lệnh điều xe nào trên VTOS và chưa dán link Sheet xe — chưa biết xe nào bận."
    return None


def tin_tuan(db: Session, tu: date | None = None) -> str:
    """Nội dung tin gửi sáng thứ Hai: khoảng trống 30 ngày tới, gọn trong một tin."""
    tu = tu or date.today()
    b = bang(db, tu, 30)
    ds = b["khoang_trong"][:12]
    dong = [f"• {k['tu']:%d/%m}–{k['den']:%d/%m} · {k['xe']} ({k['so_cho']} chỗ) · {k['so_ngay']} ngày"
            + (" · có cuối tuần" if k["cuoi_tuan"] else "") for k in ds]
    dau = (f"Xe còn trống 30 ngày tới (từ {tu:%d/%m}): công suất {b['cong_suat_30'] if b['cong_suat_30'] is not None else '—'}%, "
           f"{b['ngay_xe_trong']} ngày-xe trống. Đẩy bán tour để lấp các khoảng sau:")
    them = f"\n… và {len(b['khoang_trong']) - len(ds)} khoảng nữa — xem /xe › Điều xe › Lịch xe 90 ngày." \
        if len(b["khoang_trong"]) > len(ds) else ""
    return dau + "\n" + ("\n".join(dong) if dong else "• Không có khoảng trống từ 2 ngày trở lên.") + them
