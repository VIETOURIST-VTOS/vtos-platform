"""API sản phẩm tour (tour cha), mở chuyến từ sản phẩm, và trang chi tiết tour tổng hợp theo tab."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, or_, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.api import schemas as S
from app.models.core import User, Tour, Product, TourEvent, Booking
from app.models.payments import Receipt
from app.models.ops import PaymentRequest
from app.models.hr import GuideAssignment, DispatchOrder, Employee, Vehicle
from app.models.vietrip import TourCostLine
from app.services import products as PS
from app.services import access as AC
from app.services import tours as T
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["san-pham"])


@router.get("/products")
def list_products(q: str = "", status: str = "", limit: int = 500, u: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = select(Product).order_by(Product.code)
    if q: qs = qs.where(or_(Product.code.ilike(f"%{q}%"), Product.name.ilike(f"%{q}%")))
    if status: qs = qs.where(Product.status == status)
    rows = db.execute(qs.limit(limit)).scalars().all()
    n_tours = dict(db.execute(select(Tour.product_code, func.count()).group_by(Tour.product_code)).all())
    return [AC.mask_product({**PS.product_out(p, db), "n_tours": n_tours.get(p.code, 0)}, u) for p in rows]


@router.get("/products/{pid}")
def get_product(pid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    out = AC.mask_product(PS.product_out(p, db), u)
    out["tours"] = [{"id": t.id, "code": t.code, "start_date": t.start_date, "end_date": t.end_date, "status": t.status, "seats_open": t.seats_open, "booked": R.booked_pax(t), "price": t.price_per_pax}
                    for t in db.execute(select(Tour).where(Tour.product_code == p.code).order_by(desc(Tour.start_date)).limit(60)).scalars()]
    return out


@router.post("/products", status_code=201)
def create_product(data: S.ProductIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    p = PS.upsert_product(db, data.model_dump(), u); db.commit()
    return PS.product_out(p, db)


@router.put("/products/{pid}")
def edit_product(pid: int, data: S.ProductIn, u: User = Depends(require_roles("nv_dh", "tp_dh", "cntt")), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    d = data.model_dump(); d["code"] = p.code
    from app.services import ghi_mot_lan as GML
    GML.kiem_phien_ban(p, d.get("phien_ban"), f"Sản phẩm {p.code}",
                       lambda: {**PS.product_out(p, db), "phien_ban": p.phien_ban})
    PS.upsert_product(db, d, u)
    GML.tang_phien_ban(p)
    db.commit()
    return PS.product_out(p, db)


@router.post("/products/{pid}/open-tour", status_code=201)
def open_tour(pid: int, data: S.OpenTourIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Không có sản phẩm")
    kw = dict(price_adl=data.price_adl, price_chd=data.price_chd, price_inf=data.price_inf, seats_promo=data.seats_promo, price_promo=data.price_promo, operator_id=data.operator_id, note=data.note)
    if data.date_to and data.weekdays:
        tours = PS.open_series(db, u, p, data.start_date, data.date_to, data.weekdays, data.seats, **kw)
    else:
        tours = [PS.open_tour(db, u, p, data.start_date, data.seats, **kw)]
    db.commit()
    return {"message": f"Đã mở {len(tours)} chuyến từ sản phẩm {p.code} (nháp – kiểm tra 3 con số rồi trình Trưởng phòng)", "tours": [{"id": t.id, "code": t.code, "start_date": t.start_date} for t in tours]}


# ---------- Chi tiết tour tổng hợp (tab) ----------
@router.get("/tours/{tid}/detail")
def tour_detail(tid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    v = T.tour_view(db, t, u)
    p = db.get(Product, t.product_id) if t.product_id else db.execute(select(Product).where(Product.code == t.product_code)).scalars().first() if t.product_code else None
    v["product"] = AC.mask_product(PS.product_out(p), u) if p else None
    v["seats"] = {"open": t.seats_open, "promo": (t.seats_promo or 0), "booked": R.booked_pax(t), "left": max(0, (t.seats_open or t.planned_pax) - R.booked_pax(t))}
    v["prices"] = {"adl": t.price_per_pax, "chd": t.price_chd, "inf": t.price_inf, "promo": t.price_promo}
    # booking + đã thu
    bks = t.bookings
    paid = dict(db.execute(select(Receipt.booking_id, func.coalesce(func.sum(Receipt.amount), 0)).where(Receipt.booking_id.in_([b.id for b in bks] or [0]), Receipt.status != "huy").group_by(Receipt.booking_id)).all())
    for b in v["bookings"]:
        bo = next((x for x in bks if x.id == b["id"]), None)
        b["paid"] = float(paid.get(b["id"], 0) or 0); b["due"] = max(0.0, (b["amount"] or 0) - (b["discount"] or 0) - (b["paid"] or 0))
        b["adl"], b["chd"], b["inf"], b["pmt_status"], b["cancelled"], b["cancel_deadline"] = (bo.adl, bo.chd, bo.inf, bo.pmt_status, bo.cancelled, bo.cancel_deadline) if bo else (0, 0, 0, "", False, None)
    v["receipts"] = [{"id": r.id, "code": r.code, "booking_code": next((b.code for b in bks if b.id == r.booking_id), ""), "amount": r.amount, "method": r.method, "payer": r.payer, "status": r.status, "created_at": r.created_at, "confirmed_by": r.confirmed_by}
                     for r in db.execute(select(Receipt).where(Receipt.booking_id.in_([b.id for b in bks] or [0])).order_by(desc(Receipt.created_at))).scalars()]
    v["payment_requests"] = [{"id": r.id, "code": r.code, "category": r.category, "supplier_name": r.supplier_name, "amount": r.amount, "status": r.status, "description": r.description, "created_at": r.created_at, "paid_at": r.paid_at}
                             for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id).order_by(desc(PaymentRequest.id))).scalars()]
    lines = db.execute(select(TourCostLine).where(TourCostLine.tour_id == t.id).order_by(TourCostLine.line_no)).scalars().all()
    v["cost_lines"] = [{"line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "supplier_name": l.supplier_name, "supplier_tax_code": l.supplier_tax_code,
                        "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "actual": l.actual, "paid": l.paid, "note": l.note} for l in lines]
    from app.services import settlement as ST
    lines = [l for l in lines if l.status == "hd"]
    v["cost_lines"] = [ST.line_out(l) for l in ST.lines_of(db, t)]
    v["cost_total"] = {"actual": sum((l.actual or 0) for l in lines), "paid": sum((l.paid or 0) for l in lines)}
    v["settlement_edit"] = {"can_edit": ST.can_edit(db, u, t), "version": t.settlement_version, "service_types": ST.SERVICE_TYPES, "summary": ST.summary(db, t), "checks": ST.checks(db, t)}
    emps = {e.id: e.full_name for e in db.execute(select(Employee)).scalars()}
    # Như trên: đơn giá hiển thị giữ nguyên rỗng, chỉ thù lao mới xử rỗng thành 0.
    v["guides"] = [{"id": a.id, "guide": emps.get(a.guide_id, ""), "days": a.days,
                    "rate_per_day": a.rate_per_day, "holiday": a.holiday, "status": a.status,
                    "amount": (a.rate_per_day or 0) * a.days * (2 if a.holiday else 1)}
                   for a in db.execute(select(GuideAssignment).where(GuideAssignment.tour_id == t.id)).scalars()]
    veh = {x.id: x.plate for x in db.execute(select(Vehicle)).scalars()}
    v["dispatch"] = [{"id": d.id, "plate": veh.get(d.vehicle_id, ""), "driver": emps.get(d.driver_id, ""), "date_from": d.date_from, "date_to": d.date_to, "internal_price": d.internal_price, "status": d.status}
                     for d in db.execute(select(DispatchOrder).where(DispatchOrder.tour_id == t.id)).scalars()]
    v["events"] = [{"id": e.id, "step": e.step, "title": e.title, "note": e.note, "actor": e.actor, "source": e.source, "at": e.at}
                   for e in db.execute(select(TourEvent).where(TourEvent.tour_id == t.id).order_by(desc(TourEvent.at), desc(TourEvent.id))).scalars()]
    # B3 – Ý kiến thẩm định 06/9/2026: chi phí trên đầu trang là chi phí ĐÃ GHI NHẬN, không phải giá vốn
    # đầy đủ của chuyến. Với tour đang bán chưa có dòng quyết toán, số này gần 0 nên "lợi nhuận" xấp xỉ
    # toàn bộ doanh thu – phải ghi rõ là TẠM TÍNH và cảnh báo ngay cạnh chỉ tiêu.
    v["summary"] = {"revenue_booking": sum((b["amount"] or 0) - (b["discount"] or 0) for b in v["bookings"] if not b["cancelled"]), "collected": sum((b["paid"] or 0) for b in v["bookings"]),
                    "cost_actual": v["cost_total"]["actual"] or (t.actual_cost or 0), "cost_paid": sum((r.amount or 0) for r in db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status == "da_chi")).scalars())}
    v["summary"]["profit"] = ((t.actual_revenue or 0) or v["summary"]["revenue_booking"]) - v["summary"]["cost_actual"]
    confirmed = t.status in ("kt_xac_nhan", "khoa")
    n_lines = len(lines)
    v["summary"]["cost_lines"] = n_lines
    v["summary"]["profit_state"] = "xac_nhan" if confirmed else "tam_tinh"
    v["summary"]["cost_basis"] = ("quyet_toan" if n_lines else ("tong_hop_vietrip" if t.actual_cost else "chua_co"))
    if confirmed:
        v["summary"]["warning"] = ""
    elif not n_lines and not t.actual_cost:
        v["summary"]["warning"] = "Chuyến chưa có dòng chi phí quyết toán – lợi nhuận chỉ là chênh lệch doanh thu trừ chi phí đã ghi nhận, KHÔNG phải lợi nhuận của chuyến"
    elif t.end_date >= date.today():
        v["summary"]["warning"] = "Chuyến chưa kết thúc – chi phí còn phát sinh, lợi nhuận là số tạm tính"
    else:
        v["summary"]["warning"] = "Quyết toán chưa được Kế toán xác nhận – lợi nhuận là số tạm tính"
    from app.models.core import AuditLog
    v["audit"] = [{"id": l.id, "ts": l.ts, "actor": l.actor, "role": l.role, "action": l.action, "before": l.before, "after": l.after}
                  for l in db.execute(select(AuditLog).where(AuditLog.entity == f"tour:{t.code}").order_by(desc(AuditLog.id)).limit(100)).scalars()]
    # Che ở BƯỚC CUỐI, không ở giữa hàm: `cost_lines`, `cost_total`, `settlement_edit`,
    # `payment_requests` và `audit` đều được gắn vào SAU khối che cũ, nên trước hôm nay chúng chưa
    # từng bị che — tab bị ẩn trên màn hình nhưng tên NCC và đơn giá mua vẫn nằm trong phản hồi.
    # Cùng một hàm với `GET /tours/{id}`: xem `AC.che_gia_von`.
    return AC.che_gia_von(v, u, t, db)


# ── TR-1 (Chủ tịch duyệt 01–02/11/2026) · màn «Tour trên cổng khách» (/tour-online) ──────────────────────────────
# Ma trận quản lý khai ở chữ ký từng cửa (require_roles), hằng số ở services/tour_online.py.
from pydantic import BaseModel as _BM          # noqa: E402
from app.services import tour_online as TRO     # noqa: E402


class _TrCongIn(_BM):
    diem_den: str | None = None
    noi_bat: list[str] | None = None
    wellness: bool | None = None
    phuong_tien_ds: list[str] | None = None


class _TrGhepIn(_BM):
    link_web: str = ""


class _TrBatIn(_BM):
    bat: bool


def _tro(f, *a, **k):
    try:
        return f(*a, **k)
    except TRO.LoiTour as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/tour-online")
def tro_ds(u: User = Depends(require_roles(*TRO.VAI_XEM, mo_ta="Tour trên cổng khách")), db: Session = Depends(get_db)):
    return _tro(TRO.ds_vtos, db, u)


@router.get("/tour-online/web")
def tro_web(u: User = Depends(require_roles(*(TRO.VAI_SUA_CONG + TRO.VAI_GHEP))), db: Session = Depends(get_db)):
    return {"web": _tro(TRO.ds_web, db, u)}


# TR-11 · CHIỀU NGƯỢC của cửa trên. Cửa `/web` đi từ tour web sang sản phẩm; cửa này đi từ SẢN
# PHẨM CHƯA GHÉP sang các trang web hợp nhất — thứ người đi ghép thật sự cần, vì việc của họ là
# «22 tour này thiếu ảnh, trang nào của nó?» chứ không phải «596 trang này thuộc về ai».
@router.get("/tour-online/goi-y-link")
def tro_goi_y(u: User = Depends(require_roles(*(TRO.VAI_SUA_CONG + TRO.VAI_GHEP))), db: Session = Depends(get_db)):
    return _tro(TRO.ds_goi_y_nguoc, db, u)


@router.put("/tour-online/{pid}/cong")
def tro_sua(pid: int, data: _TrCongIn, u: User = Depends(require_roles(*TRO.VAI_SUA_CONG)), db: Session = Depends(get_db)):
    p = _tro(TRO.sua_cong, db, u, pid, data.model_dump(exclude_none=True))
    return {"message": f"Đã lưu hồ sơ cổng của {p.code}"}


@router.post("/tour-online/{pid}/doc-web")
def tro_doc(pid: int, u: User = Depends(require_roles(*TRO.VAI_SUA_CONG)), db: Session = Depends(get_db)):
    nd = _tro(TRO.doc_lai, db, u, pid)
    return {"noi_dung": nd, "message": f"Lỗi đọc web: {nd['loi']} — cổng giữ bản cũ" if nd.get("loi") else
            f"Đã đọc lại: {len(nd.get('anh') or [])} ảnh · {len(nd.get('lich_trinh') or [])} ngày lịch trình"}


@router.post("/tour-online/{pid}/ghep-web")
def tro_ghep(pid: int, data: _TrGhepIn, u: User = Depends(require_roles(*TRO.VAI_GHEP)), db: Session = Depends(get_db)):
    p = _tro(TRO.ghep, db, u, pid, data.link_web)
    return {"message": f"Đã ghép {p.code} với tour trên web" if p.link_web else f"Đã bỏ ghép {p.code}"}


@router.post("/tour-online/{pid}/thanh-toan")
def tro_tt(pid: int, data: _TrBatIn, u: User = Depends(require_roles(*TRO.VAI_GHEP)), db: Session = Depends(get_db)):
    p = _tro(TRO.bat_tt_sp, db, u, pid, data.bat)
    return {"message": f"{'Đã mở' if p.mo_thanh_toan else 'Đã đóng'} thanh toán trực tuyến của {p.code}"}


@router.post("/tour-online/thanh-toan-chung")
def tro_tt_chung(data: _TrBatIn, u: User = Depends(require_roles(*TRO.VAI_TT_CHUNG)), db: Session = Depends(get_db)):
    b = _tro(TRO.bat_tt_chung, db, u, data.bat)
    return {"message": "Đã mở thanh toán trực tuyến tour (chung)" if b else "Đã đóng thanh toán trực tuyến tour (chung)"}


class _TrBatLoIn(_TrBatIn):
    loc: str = "co_chuyen"


@router.post("/tour-online/thanh-toan-hang-loat")
def tro_tt_lo(data: _TrBatLoIn, u: User = Depends(require_roles(*TRO.VAI_TT_CHUNG)), db: Session = Depends(get_db)):
    """Mở / đóng thanh toán cho NHIỀU sản phẩm trong MỘT lượt gọi, MỘT giao dịch.

    Bấm từng sản phẩm thì mỗi lượt là một yêu cầu HTTP + một commit + một dòng nhật ký. Đo được
    13/11/2026: vài trăm lượt như thế làm máy chủ 512MB trả 502 và VTOS mất API — hai lần, cả khi
    đi một luồng có giãn nhịp. Cửa này gộp chúng lại làm một.

    Quyền `VAI_TT_CHUNG` (Chủ tịch / TGĐ), CAO HƠN cửa một sản phẩm — lý do ở `tour_online.py`.
    """
    r = _tro(TRO.bat_tt_hang_loat, db, u, data.bat, data.loc)
    lam = "Đã mở" if r["bat"] else "Đã đóng"
    return {**r, "message": f"{lam} thanh toán trực tuyến cho {r['da_doi']}/{r['so_xet']} sản phẩm "
                            f"({r['bo_loc_ten'].lower()})"}


@router.get("/tour-online/suc-khoe-doc-web")
def tro_suc_khoe(u: User = Depends(require_roles(*TRO.VAI_GHEP)), db: Session = Depends(get_db)):
    """Đường đọc nội dung từ vietourist.com.vn còn sống không, và tour nào đang thiếu ảnh.

    CỬA ĐỌC, cùng vai với cửa ghép link — ai ghép link thì người ấy phải thấy link mình ghép còn
    đọc được không. Không gọi ra mạng, không sửa gì: nó chỉ đọc lại thứ `lam_moi()` đã ghi sẵn
    vào `noi_dung_web` sau mỗi lần thử.

    VÌ SAO CẦN. `lam_moi()` nuốt mọi lỗi để cổng khách vẫn chạy bằng bản cũ — đúng, nhưng nghĩa
    là ngày web cũ đổi bố cục HTML thì bộ bóc tách chết âm thầm: khách vẫn thấy trang, chỉ là bản
    chụp của nhiều tuần trước. Lỗi vẫn được ghi, chỉ là trước đợt này không màn hình nào đọc.
    """
    return TRO.suc_khoe_doc_web(db)


@router.get("/tour-online/don")
def tro_don(chi_vat: bool = False, u: User = Depends(require_roles(*TRO.VAI_XEM_DON)), db: Session = Depends(get_db)):
    return {"don": _tro(TRO.ds_don, db, u, chi_vat)}


@router.post("/tour-online/don/{did}/da-xuat-vat")
def tro_vat(did: int, u: User = Depends(require_roles(*TRO.VAI_VAT)), db: Session = Depends(get_db)):
    d = _tro(TRO.xuat_vat, db, u, did)
    return {"message": f"Đã đánh dấu xuất hóa đơn GTGT cho {d.ma}"}


# ══ TR-8 (13/11/2026) · ALBUM ẢNH TOUR ══════════════════════════════════════════════════════
# Cửa để phòng sản phẩm TỰ ĐƯA ẢNH LÊN. Đo 13/11: 13 trong 85 tour trên cổng không có một tấm
# ảnh nào, và 22 trong 33 tour đang có chuyến mở bán thiếu ảnh — vì nội dung đọc từ web cũ mà
# bên ấy trống. Chỗ này không sửa được bằng mã, chỉ sửa được bằng một cửa nhập (ranh giới Chủ
# tịch chốt 09/9/2026: Claude viết cửa, người của anh đưa dữ liệu vào).
#
# Gửi TỪNG TỆP một, không gửi cả lô: giao diện báo được tiến độ từng tấm và thử lại đúng tấm
# hỏng, thay vì cả lô 20 ảnh đổ vì một tệp lỗi. Mỗi tấm cũng là một lượt nhẹ cho máy 512MB.
from fastapi import File, Form, Response, UploadFile     # noqa: E402

from app.services import anh_tour as ANHT                # noqa: E402


def _anht(f, *a, **k):
    try:
        return f(*a, **k)
    except ANHT.LoiTour as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/tour-online/{pid}/album")
def tro_album(pid: int, u: User = Depends(require_roles(*ANHT.VAI_XEM)), db: Session = Depends(get_db)):
    return _anht(ANHT.album, db, u, pid)


@router.post("/tour-online/{pid}/anh", status_code=201)
async def tro_anh_tai(pid: int, tep: UploadFile = File(...), nhom: str = Form(...), can_cu: str = Form("chua_xac_minh"),
                      chu_thich: str = Form(""), mo_ta_thay_the: str = Form(""), credit: str = Form(""),
                      can_cu_ghi_chu: str = Form(""),
                      u: User = Depends(require_roles(*ANHT.VAI_ANH)), db: Session = Depends(get_db)):
    data = await tep.read()
    x, moi = _anht(ANHT.tai_anh, db, u, pid, tep.filename or "anh.jpg", data,
                   {"nhom": nhom, "can_cu": can_cu, "chu_thich": chu_thich,
                    "mo_ta_thay_the": mo_ta_thay_the, "credit": credit, "can_cu_ghi_chu": can_cu_ghi_chu})
    return {"id": x.id, "moi": moi,
            "message": "Đã tải ảnh lên" if moi else "Ảnh này đã có trong album — không tạo bản trùng"}


class _AnhSuaIn(_BM):
    nhom: str | None = None
    chu_thich: str | None = None
    mo_ta_thay_the: str | None = None
    credit: str | None = None
    can_cu: str | None = None
    can_cu_ghi_chu: str | None = None


@router.put("/tour-online/anh/{aid}")
def tro_anh_sua(aid: int, data: _AnhSuaIn, u: User = Depends(require_roles(*ANHT.VAI_ANH)),
                db: Session = Depends(get_db)):
    _anht(ANHT.sua, db, u, aid, data.model_dump())
    return {"message": "Đã lưu"}


class _AnhAnIn(_BM):
    an: bool = True


@router.post("/tour-online/anh/{aid}/an")
def tro_anh_an(aid: int, data: _AnhAnIn, u: User = Depends(require_roles(*ANHT.VAI_ANH)),
               db: Session = Depends(get_db)):
    x = _anht(ANHT.an, db, u, aid, data.an)
    return {"message": "Đã gỡ ảnh khỏi cổng khách" if x.trang_thai == "an" else "Đã cho ảnh hiện lại"}


@router.delete("/tour-online/anh/{aid}")
def tro_anh_xoa(aid: int, u: User = Depends(require_roles(*ANHT.VAI_ANH)), db: Session = Depends(get_db)):
    _anht(ANHT.xoa, db, u, aid)
    return {"message": "Đã xoá ảnh khỏi album"}


class _AnhXepIn(_BM):
    ids: list[int]


@router.post("/tour-online/{pid}/anh/xep")
def tro_anh_xep(pid: int, data: _AnhXepIn, u: User = Depends(require_roles(*ANHT.VAI_ANH)),
                db: Session = Depends(get_db)):
    _anht(ANHT.xep, db, u, pid, data.ids)
    return {"message": "Đã xếp lại thứ tự ảnh"}


@router.get("/tour-online/anh/{aid}/{co}")
def tro_anh_tep(aid: int, co: str, u: User = Depends(require_roles(*ANHT.VAI_XEM)),
                db: Session = Depends(get_db)):
    """Người trong nhà xem được cả ảnh đang ẩn (để còn bật lại) và bản gốc."""
    data, a = _anht(ANHT.tep, db, u, aid, co)
    return Response(content=data, media_type=a.kieu_noi_dung or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=600"})
