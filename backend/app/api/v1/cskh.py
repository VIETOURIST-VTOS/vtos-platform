"""API Phản hồi & khiếu nại (Đợt 3) và Chăm sóc sau bán (Đợt 4).

Không có endpoint nào nhận "số tiền bồi thường", và không có endpoint nào tạo phiếu chăm sóc cho một
khách lẻ. Cả hai là cố ý, xem app/services/cskh.py.
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, Booking, Tour
from app.models.ops import PaymentRequest
from app.models.cskh import (Complaint, CareTicket, KN_NGUON, KN_NHOM, KN_MUC, KN_TRANG_THAI,
                             KN_NGUYEN_NHAN, KN_HUONG, CS_HINH_THUC, CS_DIEM, CS_TRANG_THAI)
from app.services import cskh as CS
from app.services import rules as R
from app.services import ai_log as AL

router = APIRouter(prefix="/api/v1", tags=["cskh"])
XEM = ("chutich", "tgd", "bks", "ptgd_mkt", "ptgd_doan", "nv_mkt", "gd_kd", "tp_kd", "tn_kd", "nv_kd",
       "tp_dh", "nv_dh", "ketoan", "cntt")
GHI = ("ptgd_mkt", "nv_mkt", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "tp_dh", "nv_dh", "ptgd_doan",
       "tgd", "chutich", "cntt")


# ---------------- Khiếu nại ----------------
def kn_out(db: Session, c: Complaint) -> dict:
    bk = db.get(Booking, c.booking_id) if c.booking_id else None
    t = db.get(Tour, c.tour_id) if c.tour_id else None
    pr = db.get(PaymentRequest, c.payment_request_id) if c.payment_request_id else None
    bay_gio = datetime.now()
    return {"id": c.id, "code": c.code, "source": c.source, "source_ten": KN_NGUON.get(c.source, c.source),
            "customer_name": c.customer_name, "customer_phone": c.customer_phone,
            "booking_id": c.booking_id, "booking_code": bk.code if bk else "",
            "tour_id": c.tour_id, "tour_code": t.code if t else "",
            "nhom": c.nhom, "nhom_ten": KN_NHOM.get(c.nhom, c.nhom),
            "level": c.level, "level_ten": KN_MUC.get(c.level, str(c.level)),
            "noi_dung": c.noi_dung, "de_nghi_khach": c.de_nghi_khach,
            "received_by": c.received_by, "received_at": c.received_at, "handler": c.handler,
            "han_phan_hoi": c.han_phan_hoi, "first_response_at": c.first_response_at,
            # Quá hạn là một SỰ KIỆN, không phải một cột lưu sẵn: lưu sẵn thì tới lúc quá hạn không ai
            # ghi lại và cờ mãi mãi là "chưa".
            # MỘT định nghĩa cho cả phép đếm lẫn dòng này — xem `services/cskh.qua_han_cua`.
            # Trước KN-1 chỗ này là một bản chép tay bằng Python của mệnh đề SQL trong `chi_so()`,
            # và hai bản ấy không có gì buộc phải giống nhau.
            "qua_han": CS.qua_han_cua(c, bay_gio),
            "tre_khi_phan_hoi": bool(c.first_response_at and c.han_phan_hoi and c.first_response_at > c.han_phan_hoi),
            "nguyen_nhan_nhom": c.nguyen_nhan_nhom,
            "nguyen_nhan_ten": KN_NGUYEN_NHAN.get(c.nguyen_nhan_nhom, ""),
            "nguyen_nhan": c.nguyen_nhan, "huong_xu_ly": c.huong_xu_ly or [],
            "huong_ten": [KN_HUONG.get(h, h) for h in (c.huong_xu_ly or [])],
            "payment_request_id": c.payment_request_id, "payment_request_code": pr.code if pr else "",
            "payment_request_amount": pr.amount if pr else 0,
            "payment_request_status": pr.status if pr else "",
            "khach_chap_nhan": c.khach_chap_nhan, "status": c.status,
            "status_ten": KN_TRANG_THAI.get(c.status, c.status),
            "incident_id": c.incident_id, "care_id": c.care_id,
            "nguon_tao": c.nguon_tao, "ai_ghi_chu": c.ai_ghi_chu,
            "closed_by": c.closed_by, "closed_at": c.closed_at, "reopen_reason": c.reopen_reason,
            "created_by": c.created_by, "created_at": c.created_at,
            "lan_khieu_nai_12_thang": CS.lan_khieu_nai_12_thang(db, c.customer_phone),
            "can_hai_chu_ky": c.level == 3,
            "chuyen_duoc": [s for s in CS.CHUYEN.get(c.status, ()) if s != "da_dong"]}


@router.get("/cskh/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return {"kn_nguon": KN_NGUON, "kn_nhom": KN_NHOM, "kn_muc": {str(k): v for k, v in KN_MUC.items()},
            "kn_trang_thai": KN_TRANG_THAI, "kn_nguyen_nhan": KN_NGUYEN_NHAN, "kn_huong": KN_HUONG,
            "kn_nhom_can_booking": list(CS.KN_NHOM_CAN_BOOKING),
            "cs_hinh_thuc": CS_HINH_THUC, "cs_diem": CS_DIEM, "cs_trang_thai": CS_TRANG_THAI}


@router.get("/khieu-nai/chi-so")
def kn_chi_so(ky: str = "", u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    try:
        return CS.chi_so(db, ky)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


@router.get("/khieu-nai")
def kn_ds(status: str = "", level: int = 0, qua_han: int = 0, ky: str = "", limit: int = 300,
          u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Danh sách hồ sơ khiếu nại — KN-1 09/10/2026: thêm bộ lọc KỲ và CẮT TRANG.

    BA CHỖ ĐỔI, và mỗi chỗ vá một lỗi khác nhau:

    MỘT · CẮT TRANG. Bản cũ trả về MỌI hồ sơ từng có, không một giới hạn nào. Hôm nay bảng còn
    nhỏ nên không ai thấy; nó hỏng vào đúng cái ngày không ai còn nhớ dòng này — và hỏng theo
    kiểu tệ nhất, là màn hình đứng chứ không phải báo lỗi.

    HAI · LỌC KỲ. Không có bộ lọc kỳ thì phòng CSKH không trả lời được câu hỏi đơn giản nhất của
    họ: tháng này khách kêu bao nhiêu lần, so với tháng trước thế nào.

    BA · `qua_han` LỌC TRONG SQL. Bản cũ dựng xong MỌI dòng rồi mới vứt bớt bằng Python, nên bộ
    lọc càng hẹp máy chủ càng không nhẹ đi chút nào. Nay nó là một mệnh đề, và là ĐÚNG mệnh đề
    mà bảng số dùng để đếm.

    Trả về một KHỐI CÓ `tong_khop` chứ không còn là mảng trần: đếm chạy trên câu hỏi TRƯỚC khi
    cắt, nên màn hình nói được "đang xem 300 trên 812" thay vì lặng lẽ giấu 512 hồ sơ.
    """
    q = select(Complaint).order_by(desc(Complaint.id))
    if status: q = q.where(Complaint.status == status)
    if level: q = q.where(Complaint.level == level)
    if qua_han: q = q.where(CS.dieu_kien_qua_han())
    try:
        dk = CS.dieu_kien_ky(ky)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if dk is not None: q = q.where(dk)
    tong = int(db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0)
    n = max(1, min(limit, 2000))
    rows = [kn_out(db, c) for c in db.execute(q.limit(n)).scalars()]
    return {"rows": rows, "tong_khop": tong, "limit": n, "cat_bot": tong > len(rows)}


@router.get("/khieu-nai/{cid}")
def kn_chi_tiet(cid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    return kn_out(db, c)


class KNIn(BaseModel):
    source: str
    customer_name: str
    customer_phone: str = ""
    booking_id: int | None = None
    nhom: str
    level: int = 1
    noi_dung: str
    de_nghi_khach: str = ""      # NGUYÊN VĂN đề nghị của khách – không phải số tiền
    handler: str = ""
    company_id: int | None = None
    nguon_tao: str = "nguoi"
    ai_ghi_chu: str = ""


@router.post("/khieu-nai", status_code=201)
def kn_tao(data: KNIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    try:
        c = CS.tao(db, u, data.model_dump())
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))
    if c.nguon_tao == "ai":
        AL.ghi(db, tac_vu="vb_noi_bo", muc=2, nguon="tro_ly", vai_tro=u.role, nguoi=u.username,
               ref=f"complaint:{c.code}", ket_qua=f"Ghi nhận khiếu nại {c.code}", trang_thai="cho_hau_kiem")
    db.commit(); db.refresh(c)
    return {"complaint": kn_out(db, c),
            "message": f"Đã lập hồ sơ {c.code} – hạn phản hồi khách {c.han_phan_hoi:%d/%m %H:%M}"}


@router.post("/khieu-nai/{cid}/phan-hoi")
def kn_phan_hoi(cid: int, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    try:
        c = CS.ghi_phan_hoi_dau(db, u, c)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    tre = c.han_phan_hoi and c.first_response_at > c.han_phan_hoi
    return {"complaint": kn_out(db, c),
            "message": "Đã ghi nhận phản hồi khách" + (" – TRỄ HẠN" if tre else " trong hạn")}


class KNChuyenIn(BaseModel):
    status: str


@router.post("/khieu-nai/{cid}/chuyen-trang-thai")
def kn_chuyen(cid: int, data: KNChuyenIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    try:
        c = CS.chuyen_trang_thai(db, u, c, data.status)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"complaint": kn_out(db, c), "message": f"{c.code} → {KN_TRANG_THAI[c.status]}"}


class KNDongIn(BaseModel):
    nguyen_nhan_nhom: str = ""
    nguyen_nhan: str = ""
    huong_xu_ly: list[str] = []
    de_nghi_khach: str = ""
    khach_chap_nhan: str = ""
    payment_request_id: int | None = None


@router.post("/khieu-nai/{cid}/dong")
def kn_dong(cid: int, data: KNDongIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    d = data.model_dump(exclude_unset=True)
    try:
        c = CS.dong(db, u, c, d)
    except PermissionError as ex:
        db.rollback(); raise HTTPException(403, str(ex))
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))
    xong = c.status == "da_dong"
    return {"complaint": kn_out(db, c),
            "message": f"Đã đóng hồ sơ {c.code}" if xong else
                       f"Đã ghi chữ ký của bạn – hồ sơ mức 3 cần chữ ký thứ hai của người khác"}


class KNTaiMoIn(BaseModel):
    ly_do: str


@router.post("/khieu-nai/{cid}/tai-mo")
def kn_tai_mo(cid: int, data: KNTaiMoIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    try:
        c = CS.tai_mo(db, u, c, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"complaint": kn_out(db, c), "message": f"Đã tái mở hồ sơ {c.code}"}


class LapSuVuIn(BaseModel):
    employee_id: int
    description: str
    level: int = 1


@router.post("/khieu-nai/{cid}/lap-su-vu")
def kn_lap_su_vu(cid: int, data: LapSuVuIn, u: User = Depends(require_roles("hcns", "tgd", "chutich", "ptgd_mkt", "ptgd_doan", "cntt")),
                 db: Session = Depends(get_db)):
    """Nối hồ sơ khiếu nại của KHÁCH sang hồ sơ kỷ luật NỘI BỘ khi xác định được lỗi thuộc về một người.

    Hai bảng vẫn tách rời – ở đây chỉ ghi số hiệu sự vụ lên hồ sơ khiếu nại. Sự vụ đi tiếp theo đúng
    quy trình nội quy lao động đã có (ý kiến người bị lập biên bản, cấp duyệt, thời hiệu).
    """
    from app.models.hr import Incident, Employee
    c = db.get(Complaint, cid)
    if not c: raise HTTPException(404, "Không có hồ sơ")
    if c.incident_id: raise HTTPException(422, "Hồ sơ này đã gắn một sự vụ")
    if not db.get(Employee, data.employee_id): raise HTTPException(404, "Không có nhân sự này")
    if not data.description.strip(): raise HTTPException(422, "Phải mô tả sự việc")
    sv = Incident(employee_id=data.employee_id, tour_id=c.tour_id, level=data.level,
                  description=f"[Từ khiếu nại {c.code}] {data.description}"[:300],
                  occurred_on=date.today(), created_by=u.username, status="lap")
    db.add(sv); db.flush(); c.incident_id = sv.id
    R.audit(db, u.username, u.role, "lap_su_vu_tu_khieu_nai", f"complaint:{c.code}",
            after={"incident": sv.id, "employee_id": data.employee_id})
    db.commit()
    return {"complaint": kn_out(db, c), "incident_id": sv.id,
            "message": f"Đã lập sự vụ #{sv.id} từ hồ sơ {c.code} – sự vụ đi tiếp theo quy trình nội quy lao động"}


# ---------------- Chăm sóc sau bán ----------------
def cs_ctx(db: Session, rows: list[CareTicket]) -> dict:
    """Nạp sẵn tour, booking, người phụ trách và hồ sơ khiếu nại cho CẢ danh sách — mỗi bảng một lượt.

    Trước 29/9/2026 `cs_out` gọi `db.get` bốn lần cho MỖI phiếu. Với 1.267 phiếu đang tồn của
    Vietourist, cửa `/cham-soc` mất 12 giây mới trả lời. Mười hai giây ấy không chỉ là chậm: màn
    hình đứng trong trạng thái chưa có dữ liệu suốt thời gian đó, và số phiếu thì chỉ có tăng chứ
    không giảm. Nên chỗ phải sửa là số lượt hỏi cơ sở dữ liệu, không phải chỗ chờ máy chủ khoẻ lên.

    Trả về `{}` cho danh sách rỗng cũng được: `cs_out` tra `.get(...)` nên không có khoá thì ra None,
    đúng như `db.get` trả về None cho một id không tồn tại.
    """
    def _bang(model, ids) -> dict:
        can = {i for i in ids if i}
        if not can:
            return {}
        return {x.id: x for x in db.execute(select(model).where(model.id.in_(can))).scalars()}
    return {"tour": _bang(Tour, [t.tour_id for t in rows]),
            "booking": _bang(Booking, [t.booking_id for t in rows]),
            "nguoi": _bang(User, [t.owner_id for t in rows]),
            "khieu_nai": _bang(Complaint, [t.complaint_id for t in rows])}


def cs_out(db: Session, t: CareTicket, ctx: dict | None = None) -> dict:
    """`ctx` là bảng đã nạp sẵn của `cs_ctx`. Không truyền thì hàm tự hỏi từng dòng như cũ — các
    tuyến trả về MỘT phiếu (PUT, đổi người phụ trách) vẫn gọi thẳng, không cần dựng bảng."""
    def _lay(khoa: str, model, i):
        if not i:
            return None
        return ctx[khoa].get(i) if ctx else db.get(model, i)
    tour = _lay("tour", Tour, t.tour_id)
    bk = _lay("booking", Booking, t.booking_id)
    nv = _lay("nguoi", User, t.owner_id)
    c = _lay("khieu_nai", Complaint, t.complaint_id)
    return {"id": t.id, "booking_id": t.booking_id, "booking_code": bk.code if bk else "",
            "tour_id": t.tour_id, "tour_code": tour.code if tour else "",
            "tour_name": tour.name if tour else "", "ket_thuc": tour.end_date if tour else None,
            "customer_name": t.customer_name, "customer_phone": t.customer_phone,
            "owner_id": t.owner_id, "phu_trach": nv.full_name if nv else "",
            "han_lien_he": t.han_lien_he,
            "qua_han": bool(t.status in ("moi", "hen_lai") and t.han_lien_he < date.today()),
            "hinh_thuc": t.hinh_thuc, "hinh_thuc_ten": CS_HINH_THUC.get(t.hinh_thuc, ""),
            "lien_he_duoc": t.lien_he_duoc, "ly_do_khong": t.ly_do_khong, "hai_long": t.hai_long,
            "diem_chua_hai_long": t.diem_chua_hai_long or [],
            "diem_ten": [CS_DIEM.get(x, x) for x in (t.diem_chua_hai_long or [])],
            "nhu_cau_tiep": t.nhu_cau_tiep, "lead_id": t.lead_id,
            "complaint_id": t.complaint_id, "complaint_code": c.code if c else "",
            "dong_y_dung_danh_gia": t.dong_y_dung_danh_gia, "ghi_chu": t.ghi_chu,
            "status": t.status, "status_ten": CS_TRANG_THAI.get(t.status, t.status),
            "contacted_at": t.contacted_at, "updated_by": t.updated_by}


@router.get("/cham-soc/chi-so")
def cs_chi_so(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return CS.chi_so_cham_soc(db)


@router.get("/cham-soc")
def cs_ds(status: str = "", cua_toi: int = 0, qua_han: int = 0,
          u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    from app.services import access as AC
    q = select(CareTicket).order_by(CareTicket.han_lien_he, desc(CareTicket.id))
    if status: q = q.where(CareTicket.status == status)
    # Nhân viên kinh doanh chỉ thấy phiếu của khách mình bán – cùng quy tắc đã áp cho booking.
    ids = AC.sales_ids_visible(db, u)
    if ids is not None: q = q.where(CareTicket.owner_id.in_(ids))
    elif cua_toi: q = q.where(CareTicket.owner_id == u.id)
    phieu = list(db.execute(q).scalars())
    ctx = cs_ctx(db, phieu)
    ra = [cs_out(db, t, ctx) for t in phieu]
    if qua_han: ra = [x for x in ra if x["qua_han"]]
    return ra


@router.post("/cham-soc/sinh-phieu")
def cs_sinh(tour_id: int = 0, u: User = Depends(require_roles("ptgd_mkt", "nv_mkt", "gd_kd", "tp_dh", "tgd", "chutich", "cntt")),
            db: Session = Depends(get_db)):
    """Chạy lại việc sinh phiếu ngay, thay vì đợi robot. Không tạo phiếu cho một khách lẻ – chỉ quét
    các tour đã kết thúc và bù những booking chưa có phiếu."""
    n = CS.sinh_phieu(db, tour_id or None)
    return {"da_sinh": n, "message": f"Đã sinh {n} phiếu chăm sóc mới" if n else "Không có booking nào thiếu phiếu"}


class CSGhiIn(BaseModel):
    hinh_thuc: str
    lien_he_duoc: str
    ly_do_khong: str = ""
    hai_long: int = 0
    diem_chua_hai_long: list[str] = []
    nhu_cau_tiep: str = ""
    dong_y_dung_danh_gia: str = ""
    ghi_chu: str = ""


@router.put("/cham-soc/{tid}")
def cs_ghi(tid: int, data: CSGhiIn, u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    t = db.get(CareTicket, tid)
    if not t: raise HTTPException(404, "Không có phiếu")
    try:
        t, sinh = CS.ghi_ket_qua(db, u, t, data.model_dump())
    except ValueError as ex:
        db.rollback(); raise HTTPException(422, str(ex))
    return {"ticket": cs_out(db, t), "sinh_them": sinh,
            "message": "Đã ghi kết quả chăm sóc" + (" · " + " · ".join(sinh) if sinh else "")}


class DoiPhuTrachIn(BaseModel):
    owner_id: int


@router.put("/cham-soc/{tid}/phu-trach")
def cs_doi_phu_trach(tid: int, data: DoiPhuTrachIn,
                     u: User = Depends(require_roles("gd_kd", "tp_kd", "ptgd_mkt", "tgd", "chutich", "cntt")),
                     db: Session = Depends(get_db)):
    t = db.get(CareTicket, tid)
    if not t: raise HTTPException(404, "Không có phiếu")
    if not db.get(User, data.owner_id): raise HTTPException(404, "Không có người dùng này")
    truoc = t.owner_id; t.owner_id = data.owner_id
    R.audit(db, u.username, u.role, "doi_phu_trach_cham_soc", f"care:{t.id}",
            before={"owner_id": truoc}, after={"owner_id": data.owner_id})
    db.commit()
    return {"ticket": cs_out(db, t), "message": "Đã đổi người phụ trách"}
