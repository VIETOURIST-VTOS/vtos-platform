"""API đồng bộ Vietrip → VTOS: nạp thô theo entity, xem trạng thái, ánh xạ sang nghiệp vụ, dòng chi phí tour."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, Tour
from app.models.vietrip import VtRecord, TourCostLine
from app.models.hr import Employee
from app.services import vietrip as VT
from app.services import access as AC
from app.services import rules as R

router = APIRouter(prefix="/api/v1", tags=["vietrip"])
SYNC_ROLES = ("cntt", "ketoan", "tgd", "chutich")


@router.get("/import/vietrip/status")
def status(u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    return VT.status_counts(db)


@router.post("/import/vietrip/apply")
def apply(limit: int = 400, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    try:
        return {"applied": VT.apply_all(db, u.username, limit=max(1, min(limit, 2000))), "message": "Đã ánh xạ dữ liệu Vietrip vào VTOS"}
    except Exception as e:   # trả lỗi có nội dung để robot/CNTT chẩn đoán (không lộ dữ liệu nhạy cảm)
        db.rollback()
        raise HTTPException(500, f"Ánh xạ lỗi: {type(e).__name__}: {str(e)[:600]}")


@router.delete("/import/vietrip/records/{entity}/{vietrip_id}")
def delete_record(entity: str, vietrip_id: str, u: User = Depends(require_roles("cntt")), db: Session = Depends(get_db)):
    """CNTT gỡ bản ghi nạp thử/nhầm: xóa bản ghi thô; với user → xóa hồ sơ nhân sự VT#### và khóa tài khoản tạo từ Vietrip (không xóa dữ liệu nghiệp vụ khác)."""
    r = db.execute(select(VtRecord).where(VtRecord.entity == entity, VtRecord.vietrip_id == vietrip_id)).scalars().first()
    if not r: raise HTTPException(404, "Không có bản ghi")
    removed = {"vt_record": vietrip_id}
    if entity == "user" and vietrip_id.isdigit():
        e = db.execute(select(Employee).where(Employee.code == f"VT{int(vietrip_id):04d}")).scalars().first()
        if e:
            usr = db.execute(select(User).where(User.id == e.user_id)).scalars().first()
            db.delete(e); removed["employee"] = e.code
            if usr and usr.username not in ("chutich", "tgd", "cntt", "ketoan"):
                usr.active = False; removed["user_locked"] = usr.username
    db.delete(r)
    R.audit(db, u.username, u.role, "dong_bo_vietrip_xoa", entity, after=removed); db.commit()
    return removed


# ---------- robot đồng bộ phía máy chủ (không cần trình duyệt) ----------
class SyncIn(BaseModel):
    from_date: str | None = None   # mặc định 7 ngày gần nhất
    to_date: str | None = None
    products: bool = False         # kéo lại 354 sản phẩm (chậm ~10 phút) – bật khi cần
    settlements_days: int = 10     # quét bảng quyết toán tour kết thúc trong N ngày


# MỐC SỚM NHẤT ROBOT ĐƯỢC CHẠM TỚI — Chủ tịch chốt 26/9/2026.
#
# Tháng 1 đến tháng 7/2026 trên VTOS đã là số CHỐT: 604 tệp quyết toán gốc của Điều hành, nạp qua
# cửa có người ký, đóng số xong. Chính Chủ tịch đã ra lệnh xoá phần Vietrip của khoảng ấy ngày
# 12/9/2026 vì "số trên Vietrip từ T1 đến T6 không chính xác".
#
# Robot chạy hai lượt mỗi ngày. Chỉ cần MỘT lần ai đó gọi tay với `from_date` cũ — hoặc một lần
# sửa mã đặt nhầm cửa sổ mặc định — là hai tháng số chốt bị đè bằng đúng nguồn đã bị bác, và
# không có gì đỏ lên để báo. Nên mốc này không nằm ở lịch chạy mà nằm ở ĐÂY, chỗ mọi đường gọi
# đều phải đi qua: cửa robot, cửa bấm tay, và mọi lần gọi sau này.
#
# Muốn nạp lại T1–T7 thì sửa dòng này, và đó phải là một quyết định có người ký chứ không phải
# một tham số truyền vào lúc 11 giờ đêm.
MOC_SOM_NHAT = date(2026, 8, 1)


def _dates(data: SyncIn):
    from datetime import date as _d, timedelta
    t = _d.fromisoformat(data.to_date) if data.to_date else _d.today()
    f = _d.fromisoformat(data.from_date) if data.from_date else t - timedelta(days=7)
    if f < MOC_SOM_NHAT:
        f = MOC_SOM_NHAT
    if t < MOC_SOM_NHAT:
        # Cả khoảng nằm trước mốc: không có gì để kéo, và trả về một khoảng ngược đời còn tệ hơn.
        raise HTTPException(400, f"Robot Vietrip chỉ nạp từ {MOC_SOM_NHAT:%d/%m/%Y} trở đi – "
                                 f"tháng 1 đến tháng 7/2026 là số đã chốt trên VTOS, không nạp đè.")
    return f, t


@router.post("/import/vietrip/repair-budget")
def repair_budget(u: User = Depends(require_roles(*SYNC_ROLES)), db: Session = Depends(get_db)):
    """Chạy MỘT LẦN sau khi triển khai bản sửa B2: xóa dự toán được suy ngược từ dòng quyết toán
    ở các tour nhập từ Vietrip, để dự toán và thực chi là hai số độc lập."""
    return VT.repair_derived_budgets(db, u.username)


@router.post("/import/vietrip/repair-phap-nhan")
def repair_phap_nhan(u: User = Depends(require_roles(*SYNC_ROLES)), db: Session = Depends(get_db)):
    """Gắn pháp nhân MẸ cho MỌI chuyến còn để rỗng — anh Tuấn chốt 17/9/2026: "gán hết cho
    Vietourist Holdings".

    TC-51 chỉ gắn cho chuyến nhập từ Vietrip; TC-56 mở ra cho mọi nguồn, vì KHO CŨ rơi đúng vào
    khe giữa "nhập từ Vietrip" và "ai đó dựng tay" — 477/765 chuyến H1 không có pháp nhân nên bị
    lọc khỏi màn hình Chủ tịch mà không ai thấy.

    Không ghi đè pháp nhân ai đã gắn tay, và không bịa khi danh mục chưa có công ty mẹ. Bấm lại
    lần hai vô hại. Kết quả đếm riêng `tu_vietrip` / `nguon_khac` để còn thấy kho cũ đã vào.
    """
    return VT.gan_phap_nhan_con_rong(db, u.username)


@router.post("/import/vietrip/dong-so-theo-buoc")
def dong_so_theo_buoc(u: User = Depends(require_roles(*SYNC_ROLES)), db: Session = Depends(get_db)):
    """Đóng số cho chuyến có bảng quyết toán Vietrip đã tới Bước 5 trở lên (anh Tuấn chốt 17/9/2026).

    Chạy một lần sau khi triển khai TC-52: 837 bảng quyết toán đã nhập đều `applied = True` nên
    `apply_settlements` không đi qua chúng nữa. Bấm lại lần hai vô hại.
    """
    return VT.dong_so_theo_buoc_vietrip(db, u.username)


class NapBuIn(BaseModel):
    """Khoảng NGÀY KẾT THÚC của chuyến, không phải ngày khởi hành."""
    tu: str = "2026-01-01"
    den: str | None = None      # mặc định hôm nay
    gioi_han: int = 6           # số bảng quyết toán mỗi lô


def _khoang(data: "NapBuIn"):
    from datetime import date as _d
    t = _d.fromisoformat(data.den) if data.den else _d.today()
    return _d.fromisoformat(data.tu), t


@router.post("/import/vietrip/nap-bu/tour")
def nap_bu_tour(data: NapBuIn, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    """Kéo DANH SÁCH TOUR kết thúc trong khoảng ngày (TC-53). Không đụng booking/phiếu thu.

    Dùng để nạp bù giai đoạn chưa bao giờ kéo về: lần đồng bộ đầu 05/9/2026 đặt mốc từ 01/6 nên
    VTOS không có chuyến nào kết thúc trước tháng 6.
    """
    from app.services import vietrip_client as VC
    f, t = _khoang(data)
    ra = VC.nap_tour_theo_khoang(db, f, t)
    R.audit(db, u.username, u.role, "nap_bu_tour_vietrip", "vietrip", after=ra); db.commit()
    return ra


@router.post("/import/vietrip/nap-bu/booking-cho-phieu-thu")
def nap_bu_booking_cho_phieu_thu(gioi_han: int = 500,
                                 u: User = Depends(require_roles(*SYNC_ROLES)),
                                 db: Session = Depends(get_db)):
    """Gỡ chỗ phiếu thu treo vì "chưa có booking": đi tìm đúng những booking ấy rồi ánh xạ lại.

    ĐO ĐƯỢC 26/9/2026: 227 phiếu thu/chi treo, tổng 1.519.979.111 đ, tất cả cùng một lý do. Cả 227
    phiếu đều MANG mã booking Vietrip — 183 booking khác nhau — chỉ là VTOS chưa có chúng, vì robot
    kéo booking theo NGÀY ĐẶT với cửa sổ 7 ngày, còn khách thì đặt tháng 3 trả tiền tháng 9.

    Cửa này KHÔNG truyền khoảng ngày nào, nên không chạm vào `MOC_SOM_NHAT`. Nó lần theo id của
    những booking mà phiếu thu ĐANG CÓ trỏ tới. Lấy một booking tháng 3 để gắn khoản tiền khách
    trả tháng 9 không phải là nạp lại tháng 3 — Chủ tịch chốt 26/9/2026 (phương án A).

    Ba bước, và bước nào cũng đếm được để đối chiếu:
        1. đọc id còn thiếu từ chính bản ghi thô đã kéo về
        2. tìm những booking ấy trên Vietrip rồi nạp thô
        3. ánh xạ booking, rồi ánh xạ lại phiếu thu
    """
    from app.services import vietrip_client as VC
    ids = VT.id_booking_con_thieu(db, gioi_han)
    if not ids:
        return {"can_tim": 0, "message": "Không còn phiếu thu nào treo vì thiếu booking."}
    ket = VC.nap_booking_theo_id(db, ids)
    da_booking, da_phieu, vong = 0, 0, 0
    while vong < 20:
        n = VT.apply_bookings(db, limit=400)
        da_booking += n; vong += 1
        if n == 0: break
    vong = 0
    while vong < 20:
        n = VT.apply_receipts(db, limit=400)
        da_phieu += n; vong += 1
        if n == 0: break
    con = db.execute(select(func.count()).select_from(VtRecord).where(
        VtRecord.entity == "receipt", VtRecord.applied == False)).scalar()
    R.audit(db, u.username, u.role, "nap_bu_booking_cho_phieu_thu", "vietrip",
            after={"can_tim": ket["can_tim"], "tim_thay": ket["tim_thay"],
                   "booking_da_anh_xa": da_booking, "phieu_thu_da_anh_xa": da_phieu,
                   "phieu_thu_con_treo": con})
    db.commit()
    return {**ket, "booking_da_anh_xa": da_booking, "phieu_thu_da_anh_xa": da_phieu,
            "phieu_thu_con_treo": con,
            "message": (f"Tìm {ket['can_tim']} booking, thấy {ket['tim_thay']} qua {ket['so_trang']} "
                        f"trang. Ánh xạ {da_booking} booking và {da_phieu} phiếu thu. "
                        f"Còn treo {con} phiếu.")}


@router.post("/import/vietrip/nap-bu/quyet-toan")
def nap_bu_quyet_toan(data: NapBuIn, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    """Tải bảng quyết toán CÒN THIẾU — MỖI LẦN MỘT LÔ NHỎ, gọi lặp tới khi `con_lai` = 0 (TC-53).

    Mỗi trang quyết toán mất ~10 giây và Render gói miễn phí ngủ sau 15 phút, nên một lần chạy dài
    không bao giờ xong. Lô nhỏ có đáy thì ngủ giữa chừng cũng chỉ mất đúng lô đang dở.
    """
    from app.services import vietrip_client as VC
    f, t = _khoang(data)
    return VC.nap_quyet_toan_thieu(db, f, t, data.gioi_han)


@router.post("/import/vietrip/sync")
def vietrip_sync(data: SyncIn, u: User = Depends(require_roles("cntt", "ketoan")), db: Session = Depends(get_db)):
    from app.services import vietrip_client as VC
    f, t = _dates(data)
    if not VC.start_background(f, t, data.products, data.settlements_days): raise HTTPException(409, "Robot đang chạy – xem trạng thái")
    R.audit(db, u.username, u.role, "chay_robot_vietrip", "vietrip", after={"tu": str(f), "den": str(t)}); db.commit()
    return {"message": f"Robot đồng bộ Vietrip đã chạy nền ({f} → {t}) – theo dõi ở Trạng thái robot"}


@router.post("/robot/vietrip/sync")
def robot_vietrip_sync(data: SyncIn, x_robot_token: str | None = Header(default=None)):
    """GitHub Actions / n8n gọi hằng ngày (X-Robot-Token)."""
    from app.core.config import settings
    from app.services import vietrip_client as VC
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    f, t = _dates(data)
    return {"started": VC.start_background(f, t, data.products, data.settlements_days), "from": str(f), "to": str(t)}


@router.get("/import/vietrip/robot-status")
def robot_status(u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    from app.services import vietrip_client as VC
    from app.core.config import settings
    return {**{k: v for k, v in VC.STATE.items() if k != "log"}, "log": VC.STATE["log"][-40:], "credentials_set": bool(settings.VIETRIP_PHONE and settings.VIETRIP_PASSWORD)}


@router.get("/import/vietrip/records")
def records(entity: str, limit: int = 50, unapplied: bool = False, u: User = Depends(require_roles(*SYNC_ROLES, "bks")), db: Session = Depends(get_db)):
    q = select(VtRecord).where(VtRecord.entity == entity).order_by(desc(VtRecord.on_date), desc(VtRecord.id))
    if unapplied: q = q.where(VtRecord.applied == False)
    return [{"id": r.id, "vietrip_id": r.vietrip_id, "ref": r.ref, "on_date": r.on_date, "amount": r.amount, "applied": r.applied, "apply_note": r.apply_note, "synced_at": r.synced_at, "raw": r.raw}
            for r in db.execute(q.limit(limit)).scalars()]


@router.get("/tours/{tid}/cost-lines")
def cost_lines(tid: int, u: User = Depends(require_roles(*AC.COST_ROLES, mo_ta="cơ cấu chi phí tour")), db: Session = Depends(get_db)):
    t = db.get(Tour, tid)
    if not t: raise HTTPException(404, "Không có tour")
    rows = db.execute(select(TourCostLine).where(TourCostLine.tour_id == tid).order_by(TourCostLine.line_no)).scalars().all()
    return {"tour": t.code, "rows": [{"id": l.id, "line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "supplier_name": l.supplier_name,
                                      "supplier_tax_code": l.supplier_tax_code, "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "actual": l.actual, "paid": l.paid, "note": l.note, "source": l.source} for l in rows],
            "total_actual": sum((l.actual or 0) for l in rows), "total_paid": sum((l.paid or 0) for l in rows)}


# đặt sau cùng để không nuốt /apply, /status, /records
class Batch(BaseModel):
    rows: list[dict]


@router.post("/import/vietrip/{entity}")
def ingest(entity: str, data: Batch, u: User = Depends(require_roles(*SYNC_ROLES)), db: Session = Depends(get_db)):
    try:
        new, upd = VT.upsert(db, entity, data.rows)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"entity": entity, "received": len(data.rows), "new": new, "updated": upd}


