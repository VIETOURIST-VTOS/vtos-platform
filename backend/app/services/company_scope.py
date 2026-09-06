"""Công ty chủ quản của hồ sơ nghiệp vụ (Ý kiến thẩm định 06/9/2026 – Đợt 2 mục 2).

Nguyên tắc bất di bất dịch của phần này: **rỗng là "chưa xác định", không phải "công ty mẹ"**.
Gán nhầm pháp nhân cho một tour làm sai đồng thời hai thứ: báo cáo riêng của từng đơn vị, và phần
loại trừ giao dịch nội bộ khi hợp nhất – mà cả hai đều không có cách nào phát hiện lại về sau.
Vì vậy ở đây chỉ có hai cách để một hồ sơ có pháp nhân:

1. **Suy từ hồ sơ cha đã được xác định** (booking ← tour, phiếu thu ← booking, đề nghị chi ← tour,
   chứng từ ghi sổ ← tour). Đây không phải phỏng đoán: booking của một tour thuộc pháp nhân nào thì
   doanh thu của nó thuộc pháp nhân đó.
2. **Người có thẩm quyền gán tay** cho từng hồ sơ hoặc theo lô, có ghi nhật ký.

Tour KHÔNG có hồ sơ cha nên không suy được – phải do Điều hành/Kế toán chỉ định. Toàn bộ tour nhập
từ Vietrip vì thế sẽ nằm trong danh sách đối chiếu cho tới khi lãnh đạo chốt, và đó là trạng thái
đúng: hệ thống nói thật rằng nó chưa biết, thay vì đoán.
"""
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from app.models.core import Tour, Booking, Company
from app.models.ops import PaymentRequest
from app.models.payments import Receipt
from app.models.accounting import JournalEntry
from app.services import rules as R

# key → (nhãn, model, cột mã để hiển thị, hồ sơ cha suy ra pháp nhân)
KINDS: dict[str, dict] = {
    "tour":     {"label": "Chuyến tour",      "model": Tour,           "code": "code", "parent": None},
    "booking":  {"label": "Booking",          "model": Booking,        "code": "code", "parent": ("tour_id", Tour)},
    "receipt":  {"label": "Phiếu thu",        "model": Receipt,        "code": "code", "parent": ("booking_id", Booking)},
    "chi":      {"label": "Đề nghị chi",      "model": PaymentRequest, "code": "code", "parent": ("tour_id", Tour)},
    "chung_tu": {"label": "Chứng từ ghi sổ",  "model": JournalEntry,   "code": "code", "parent": ("tour_id", Tour)},
}


def _dem(db: Session, m) -> tuple[int, int]:
    tong = db.execute(select(func.count()).select_from(m)).scalar() or 0
    da = db.execute(select(func.count()).select_from(m).where(m.company_id.is_not(None))).scalar() or 0
    return tong, da


def coverage(db: Session) -> dict:
    """Mỗi loại hồ sơ: tổng, đã có pháp nhân, còn phải đối chiếu, và có suy được từ hồ sơ cha không."""
    rows = []
    for key, cfg in KINDS.items():
        tong, da = _dem(db, cfg["model"])
        rows.append({"kind": key, "label": cfg["label"], "tong": tong, "da_gan": da, "chua_gan": tong - da,
                     "suy_duoc_tu": KINDS[key]["parent"][1].__name__ if cfg["parent"] else None,
                     "ty_le": round(da * 100 / tong, 1) if tong else 100.0})
    return {"rows": rows, "chua_gan_tong": sum(r["chua_gan"] for r in rows)}


def pending(db: Session, kind: str, limit: int = 100, offset: int = 0) -> dict:
    """Danh sách hồ sơ chưa xác định pháp nhân – để Điều hành/Kế toán gán, không có nút gán tất cả về mẹ."""
    cfg = KINDS[kind]
    m = cfg["model"]
    q = select(m).where(m.company_id.is_(None)).order_by(m.id.desc())
    tong = db.execute(select(func.count()).select_from(m).where(m.company_id.is_(None))).scalar() or 0
    rows = []
    for r in db.execute(q.limit(limit).offset(offset)).scalars():
        rows.append({"id": r.id, "code": getattr(r, cfg["code"], ""), "mo_ta": _mo_ta(kind, r),
                     "tour_id": getattr(r, "tour_id", None)})
    return {"kind": kind, "label": cfg["label"], "tong": tong, "rows": rows}


def _mo_ta(kind: str, r) -> str:
    if kind == "tour": return f"{r.name} · khởi hành {r.start_date}"
    if kind == "booking": return f"{r.customer_name} · {r.pax} khách"
    if kind == "receipt": return f"{r.payer or 'khách'} · {r.amount:,.0f}đ"
    if kind == "chi": return f"{r.supplier_name} · {r.amount:,.0f}đ"
    if kind == "chung_tu": return f"{r.description} · {r.entry_date}"
    return ""


def derive(db: Session, u=None) -> dict:
    """Suy pháp nhân từ hồ sơ cha đã xác định. Chạy lại nhiều lần vẫn cho cùng kết quả, và
    KHÔNG bao giờ ghi đè pháp nhân đã có – hồ sơ đã được người gán tay là quyết định cuối cùng.

    Viết bằng một câu lệnh cập nhật cho mỗi loại hồ sơ thay vì duyệt từng bản ghi: khối dữ liệu đã nạp
    có hơn 25.000 chứng từ ghi sổ, nạp ngần ấy đối tượng vào bộ nhớ đủ làm sập máy chủ 512 MB.
    """
    ket_qua = {}
    for key in ("booking", "receipt", "chi", "chung_tu"):
        cfg = KINDS[key]
        m, (fk, pm) = cfg["model"], cfg["parent"]
        col = getattr(m, fk)
        cha_da_xac_dinh = select(pm.id).where(pm.id == col, pm.company_id.is_not(None))
        r = db.execute(
            update(m)
            .where(m.company_id.is_(None), col.is_not(None), cha_da_xac_dinh.exists())
            .values(company_id=select(pm.company_id).where(pm.id == col).scalar_subquery())
            .execution_options(synchronize_session=False)
        )
        ket_qua[key] = r.rowcount or 0
    if u is not None and sum(ket_qua.values()):
        R.audit(db, u.username, u.role, "suy_phap_nhan_tu_ho_so_cha", "company_scope", after=ket_qua)
    db.commit()
    return {"da_suy": ket_qua, "tong": sum(ket_qua.values()),
            "ghi_chu": "Chỉ suy từ hồ sơ cha đã xác định; tour không có hồ sơ cha nên phải chỉ định tay."}


def assign(db: Session, kind: str, ids: list[int], company_id: int | None, u) -> dict:
    """Gán pháp nhân cho một lô hồ sơ. company_id = None là gỡ về 'chưa xác định' (khi gán nhầm)."""
    if kind not in KINDS: raise ValueError(f"Loại hồ sơ không hợp lệ: {kind}")
    if company_id is not None and db.get(Company, company_id) is None:
        raise ValueError("Không có pháp nhân này trong danh mục")
    m = KINDS[kind]["model"]
    rows = list(db.execute(select(m).where(m.id.in_(ids))).scalars()) if ids else []
    truoc = {r.id: r.company_id for r in rows}
    for r in rows: r.company_id = company_id
    R.audit(db, u.username, u.role, "gan_phap_nhan_ho_so", f"{kind}:{len(rows)}",
            before=truoc, after={"company_id": company_id, "so_ho_so": len(rows)})
    db.commit()
    khong_thay = sorted(set(ids) - set(truoc))
    return {"da_gan": len(rows), "khong_tim_thay": khong_thay,
            "message": f"Đã gán pháp nhân cho {len(rows)} {KINDS[kind]['label'].lower()}" if company_id
                       else f"Đã gỡ pháp nhân của {len(rows)} {KINDS[kind]['label'].lower()} về 'chưa xác định'"}


def assign_tours_by_filter(db: Session, company_id: int, u, nguon: str = "", tu_ngay=None, den_ngay=None,
                           loai: str = "", chi_chua_gan: bool = True) -> dict:
    """Gán pháp nhân cho một LÔ TOUR theo tiêu chí, thay cho việc bấm từng dòng trong hơn một nghìn tour.

    Đây vẫn là quyết định của con người: người gán phải nêu rõ tiêu chí (nguồn dữ liệu, khoảng khởi
    hành, loại tour) và toàn bộ tiêu chí đó được ghi vào nhật ký cùng số hồ sơ bị ảnh hưởng, để sau này
    truy lại được vì sao một tour thuộc pháp nhân này chứ không phải pháp nhân kia.
    """
    if db.get(Company, company_id) is None: raise ValueError("Không có pháp nhân này trong danh mục")
    dk = []
    if chi_chua_gan: dk.append(Tour.company_id.is_(None))
    if nguon == "vietrip": dk.append(Tour.vietrip_id.is_not(None))
    elif nguon == "vtos": dk.append(Tour.vietrip_id.is_(None))
    if tu_ngay: dk.append(Tour.start_date >= tu_ngay)
    if den_ngay: dk.append(Tour.start_date <= den_ngay)
    if loai: dk.append(Tour.tour_type == loai)
    n = db.execute(update(Tour).where(*dk).values(company_id=company_id)
                   .execution_options(synchronize_session=False)).rowcount or 0
    tieu_chi = {"nguon": nguon or "tất cả", "tu_ngay": str(tu_ngay or ""), "den_ngay": str(den_ngay or ""),
                "loai": loai or "tất cả", "chi_chua_gan": chi_chua_gan}
    R.audit(db, u.username, u.role, "gan_phap_nhan_lo_tour", f"company:{company_id}",
            before=tieu_chi, after={"so_tour": n})
    db.commit()
    return {"da_gan": n, "tieu_chi": tieu_chi,
            "message": f"Đã gán pháp nhân cho {n} chuyến tour theo tiêu chí đã nêu"}
