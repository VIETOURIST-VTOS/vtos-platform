"""API Sự cố tour – V7 Đợt 3.

Không có endpoint nào nhận "chi phí phát sinh". Cố ý; xem app/models/su_co_tour.py.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User, Tour, Booking
from app.models.ops import PaymentRequest
from app.models.cskh import Complaint
from app.models.suppliers import Supplier
from app.models.su_co_tour import (SuCoTour, SuCoTourXuLy, SC_NHOM, SC_MUC, SC_TRANG_THAI, SC_CHUYEN,
                                   SC_NGUYEN_NHAN)
from app.services import su_co_tour as SC
from app.services import vai_ke_thua as VKT   # phep suy vai ke thua, Dot LG1

router = APIRouter(prefix="/api/v1", tags=["su-co-tour"])

# XEM rộng hơn GHI: quyết toán chuyến và lãi lỗ chuyến đều phải đọc được sự cố của chuyến ấy, nếu không
# thì con số chi phí phát sinh hiện ra mà không ai giải thích được nó từ đâu.
# DH-1 · 08/10/2026 — thêm `sales_admin` và `ptgd_mkt` (Chủ tịch quyết), để tab "Phát sinh" gắn được
# vào trang chi tiết chuyến. Hai vai ấy mở được trang chuyến từ trước; không mở danh sách này thì tab
# mới sẽ là một cái tab bấm vào nhận 403, và `MAN_HINH_API` của /tours sẽ khai hai vai gọi được một
# cửa máy chủ từ chối — bảng phân quyền đầy đủ hơn thực tế.
#
# `sales_admin` KHÔNG phải một lần nới: nó đã nằm trong `MENU_ROLES["/su-co-tour"]` từ trước (qua nhóm
# SALES_ADMIN) mà KHÔNG có ở đây — tức Sale Admin mở được màn hình Sự cố tour và MỌI cửa trên đó trả
# 403. Một màn hình mở mà không cửa nào bấm được thì tệ hơn một màn hình bị khoá: người dùng không
# biết mình thiếu quyền hay hệ thống hỏng. Đây là sửa chỗ hai bảng nói ngược nhau, đo được chứ không
# suy đoán — và có phép thử canh đúng điều đó trong `test_dh1`.
XEM = ("chutich", "tgd", "bks", "robot_ks", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "gd_kd",
       "tp_kd", "tn_kd", "nv_kd", "tp_hd", "gd_doi_xe", "sales_admin", "ketoan", "cntt")
# Đợt LG1 — nới một lượt bằng phép suy vai kế thừa, KHÔNG gõ thêm tên vai vào bộ ở trên. `test_dh1`
# so THẲNG hằng số này với `MENU_ROLES["/su-co-tour"]`, nên nới ở `require_roles` thôi là chưa đủ:
# hằng số phải nói đúng cửa thật. Để thành một dòng RIÊNG thay vì gói cả bộ, để lần sau ai thêm một
# vai vào bộ trên vẫn thấy rõ phép suy đứng ở đâu.
XEM = VKT.mo_rong(XEM)

# Ai được đọc TÊN KHÁCH trong các ô chọn của màn hình này (10/9/2026, sau khi anh Tuấn chốt mở màn
# hình cho GĐ Đội xe và TP Hướng dẫn).
#
# Hai vai ấy vào được màn hình, ghi được sự cố, theo dõi được việc của mình – nhưng KHÔNG cầm danh
# sách khách. Đó là ranh giới cả ma trận phân quyền giữ từ đầu ("KHÔNG xem dữ liệu khách, booking"),
# và mở màn hình không phải là lý do để bỏ nó: một người sửa xe không cần biết ai ngồi trên xe, cần
# biết xe nào, chuyến nào, hỏng gì.
#
# Ô chọn booking với họ trả về MÃ booking chứ không trả tên khách. Mã đủ để chỉ đúng nhóm khách bị
# ảnh hưởng; tên thì không thêm được gì cho việc điều xe.
KHACH = ("chutich", "tgd", "bks", "robot_ks", "ptgd_doan", "tp_dh", "nv_dh", "gd_kd", "tp_kd",
         "tn_kd", "nv_kd", "ketoan", "cntt")


def _out(db: Session, sc: SuCoTour, kem_xu_ly: bool = False) -> dict:
    t = db.get(Tour, sc.tour_id)
    bk = db.get(Booking, sc.booking_id) if sc.booking_id else None
    ncc = db.get(Supplier, sc.supplier_id) if sc.supplier_id else None
    pr = db.get(PaymentRequest, sc.payment_request_id) if sc.payment_request_id else None
    kn = db.get(Complaint, sc.complaint_id) if sc.complaint_id else None
    d = {"id": sc.id, "code": sc.code,
         "tour_id": sc.tour_id, "tour_code": t.code if t else "", "tour_name": getattr(t, "name", "") if t else "",
         "booking_id": sc.booking_id, "booking_code": bk.code if bk else "",
         "nhom": sc.nhom, "nhom_ten": SC_NHOM.get(sc.nhom, sc.nhom),
         "muc": sc.muc, "muc_ten": SC_MUC.get(sc.muc, str(sc.muc)),
         "xay_ra_luc": sc.xay_ra_luc, "noi_xay_ra": sc.noi_xay_ra,
         "so_khach_anh_huong": sc.so_khach_anh_huong, "mo_ta": sc.mo_ta,
         "nguoi_bao": sc.nguoi_bao, "nguoi_bao_id": sc.nguoi_bao_id,
         "supplier_id": sc.supplier_id, "supplier_name": ncc.ten if ncc else "",
         "trang_thai": sc.trang_thai, "trang_thai_ten": SC_TRANG_THAI.get(sc.trang_thai, sc.trang_thai),
         "han_xu_ly": sc.han_xu_ly, "nhan_luc": sc.nhan_luc, "nguoi_xu_ly": sc.nguoi_xu_ly,
         # Quá hạn tính TẠI CHỖ, không lưu cột – xem su_co_tour.qua_han().
         "qua_han": SC.qua_han(sc),
         "huong_xu_ly": sc.huong_xu_ly, "ket_qua": sc.ket_qua,
         "nguyen_nhan_nhom": sc.nguyen_nhan_nhom,
         "nguyen_nhan_ten": SC_NGUYEN_NHAN.get(sc.nguyen_nhan_nhom, ""),
         "nguyen_nhan": sc.nguyen_nhan,
         # Số hiệu chứng từ, KHÔNG phải số tiền của riêng hồ sơ này: số tiền hiện ra là số của chính
         # đề nghị chi, đọc sang chứ không chép lại.
         "payment_request_id": sc.payment_request_id, "payment_request_code": pr.code if pr else "",
         "payment_request_amount": pr.amount if pr else 0,
         "payment_request_status": pr.status if pr else "",
         "complaint_id": sc.complaint_id, "complaint_code": kn.code if kn else "",
         "incident_id": sc.incident_id,
         "company_id": sc.company_id, "created_by": sc.created_by, "created_at": sc.created_at,
         "closed_by": sc.closed_by, "closed_at": sc.closed_at,
         "chuyen_duoc": list(SC_CHUYEN.get(sc.trang_thai, ()))}
    if kem_xu_ly:
        d["xu_ly"] = [{"id": x.id, "luc": x.luc, "nguoi": x.nguoi, "noi_dung": x.noi_dung}
                      for x in db.execute(select(SuCoTourXuLy)
                                          .where(SuCoTourXuLy.su_co_id == sc.id)
                                          .order_by(SuCoTourXuLy.luc, SuCoTourXuLy.id)).scalars()]
    return d


@router.get("/su-co-tour/meta")
def meta(u: User = Depends(require_roles(*XEM, mo_ta="sự cố tour")), db: Session = Depends(get_db)):
    """Danh mục của màn hình, KÈM danh sách nhà cung cấp rút gọn.

    Vì sao danh sách nhà cung cấp đi qua đây thay vì màn hình gọi thẳng /api/v1/suppliers: bản đầu
    10/9/2026 gọi thẳng, và bộ kiểm phạm vi P2 chỉ ra hậu quả – khối Kinh doanh mở được màn hình này,
    nên gọi thẳng là mở luôn cho họ cả nhóm API nhà cung cấp, thứ ma trận xưa nay giữ ngoài tầm họ
    ("Khối Kinh doanh không xem cơ cấu chi phí nhà cung cấp").

    Ở đây trả về ĐÚNG mã và tên. Không giá, không điều khoản, không tài khoản ngân hàng – vừa đủ để
    chỉ ra bên nào gây ra sự cố, không đủ để đọc cơ cấu giá vốn.
    """
    ncc = [{"id": s.id, "name": s.ten, "code": s.code}
           for s in db.execute(select(Supplier).where(Supplier.active == True)
                               .order_by(Supplier.ten)).scalars()]
    # Danh sách chuyến cũng đi qua đây, cùng lý lẽ với nhà cung cấp: gọi thẳng /api/v1/tours là buộc
    # mọi vai trò mở được màn hình này phải cầm luôn nhóm API chuyến tour. Chỉ mã, tên và ngày.
    tours = [{"id": t.id, "code": t.code, "name": t.name,
              "start_date": t.start_date, "end_date": t.end_date}
             for t in db.execute(select(Tour).order_by(desc(Tour.start_date)).limit(400)).scalars()]
    return {"nhom": SC_NHOM, "muc": {str(k): v for k, v in SC_MUC.items()},
            "trang_thai": SC_TRANG_THAI, "nguyen_nhan": SC_NGUYEN_NHAN,
            "nha_cung_cap": ncc, "tours": tours,
            "xem_duoc_ten_khach": u.role in KHACH or u.role == "chutich",
            "ghi_duoc": list(SC.GHI), "dong_duoc": list(SC.DONG)}


@router.get("/su-co-tour/chon/booking")
def chon_booking(tour_id: int, u: User = Depends(require_roles(*XEM, mo_ta="sự cố tour")),
                 db: Session = Depends(get_db)):
    """Booking CỦA MỘT CHUYẾN, để chọn nhóm khách bị ảnh hưởng.

    Lọc theo chuyến chứ không trả cả sổ booking: sự cố nào cũng thuộc một chuyến, nên danh sách đúng
    luôn là danh sách của chuyến ấy – vừa dễ chọn đúng, vừa không phải mở nhóm API booking cho mọi
    vai trò xem được màn hình này.

    Tên khách chỉ trả cho vai trò trong KHACH. Vai trò khác nhận mã booking – đủ để chỉ đúng nhóm
    khách, không đủ để dựng lại danh sách khách hàng.
    """
    co_ten = u.role in KHACH or u.role == "chutich"
    ra = []
    for b in db.execute(select(Booking).where(Booking.tour_id == tour_id)
                        .order_by(Booking.id)).scalars():
        d = {"id": b.id, "code": b.code}
        if co_ten:
            d["khach"] = b.customer_name
        ra.append(d)
    return {"co_ten_khach": co_ten, "rows": ra}


@router.get("/su-co-tour/chon/ket-luan")
def chon_ket_luan(u: User = Depends(require_roles(*SC.DONG, mo_ta="kết luận sự cố tour")),
                  db: Session = Depends(get_db)):
    """Hai danh sách chỉ dùng ở bước KẾT LUẬN: chứng từ chi phí và hồ sơ khiếu nại của khách.

    Đặt sau hàng rào SC.DONG chứ không để ở meta: chỉ bốn vai trò kết luận được hồ sơ mới cần hai
    danh sách này, mà cả hai đều là dữ liệu nhạy hơn hẳn phần còn lại của màn hình – một bên là
    đường tiền, một bên là tên và lời của khách.
    """
    chi = [{"id": p.id, "code": p.code, "amount": p.amount, "status": p.status,
            "description": p.description}
           for p in db.execute(select(PaymentRequest)
                               .where(PaymentRequest.category == "chi_tour")
                               .order_by(desc(PaymentRequest.id)).limit(300)).scalars()]
    kn = [{"id": c.id, "code": c.code, "khach": c.customer_name}
          for c in db.execute(select(Complaint).order_by(desc(Complaint.id)).limit(300)).scalars()]
    return {"chi_phi_tour": chi, "khieu_nai": kn}


@router.get("/su-co-tour/chi-so")
def chi_so(u: User = Depends(require_roles(*XEM, mo_ta="sự cố tour")), db: Session = Depends(get_db)):
    return SC.chi_so(db)


@router.get("/su-co-tour")
def danh_sach(trang_thai: str = "", muc: int = 0, tour_id: int = 0, qua_han: int = 0,
              u: User = Depends(require_roles(*XEM, mo_ta="sự cố tour")), db: Session = Depends(get_db)):
    q = select(SuCoTour).order_by(desc(SuCoTour.id))
    if trang_thai: q = q.where(SuCoTour.trang_thai == trang_thai)
    if muc: q = q.where(SuCoTour.muc == muc)
    if tour_id: q = q.where(SuCoTour.tour_id == tour_id)
    ra = [_out(db, sc) for sc in db.execute(q).scalars()]
    if qua_han: ra = [x for x in ra if x["qua_han"]]
    return ra


@router.get("/su-co-tour/{sid}")
def chi_tiet(sid: int, u: User = Depends(require_roles(*XEM, mo_ta="sự cố tour")),
             db: Session = Depends(get_db)):
    sc = db.get(SuCoTour, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ sự cố này")
    return _out(db, sc, kem_xu_ly=True)


class SuCoIn(BaseModel):
    tour_id: int
    booking_id: int | None = None
    nhom: str
    muc: int = 1
    xay_ra_luc: datetime | None = None
    noi_xay_ra: str = ""
    so_khach_anh_huong: int = 0
    mo_ta: str
    nguoi_bao: str = ""
    nguoi_bao_id: int | None = None
    supplier_id: int | None = None
    company_id: int | None = None


@router.post("/su-co-tour")
def tao(inp: SuCoIn, u: User = Depends(require_roles(*SC.GHI, mo_ta="ghi sự cố tour")),
        db: Session = Depends(get_db)):
    try:
        sc = SC.tao(db, u, inp.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": f"Đã ghi sự cố {sc.code}", "id": sc.id, "code": sc.code}


class XuLyIn(BaseModel):
    noi_dung: str
    luc: datetime | None = None


@router.post("/su-co-tour/{sid}/xu-ly")
def them_xu_ly(sid: int, inp: XuLyIn, u: User = Depends(require_roles(*SC.GHI, mo_ta="xử lý sự cố tour")),
               db: Session = Depends(get_db)):
    sc = db.get(SuCoTour, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ sự cố này")
    try:
        SC.them_xu_ly(db, u, sc, inp.noi_dung, inp.luc)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã ghi bước xử lý"}


class ChuyenIn(BaseModel):
    trang_thai: str


@router.post("/su-co-tour/{sid}/chuyen")
def chuyen(sid: int, inp: ChuyenIn, u: User = Depends(require_roles(*SC.GHI, mo_ta="sự cố tour")),
           db: Session = Depends(get_db)):
    sc = db.get(SuCoTour, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ sự cố này")
    try:
        SC.chuyen_trang_thai(db, u, sc, inp.trang_thai)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã chuyển trạng thái"}


class DongIn(BaseModel):
    nguyen_nhan_nhom: str
    nguyen_nhan: str
    ket_qua: str
    huong_xu_ly: str = ""
    payment_request_id: int | None = None
    complaint_id: int | None = None
    incident_id: int | None = None


@router.post("/su-co-tour/{sid}/dong")
def dong(sid: int, inp: DongIn, u: User = Depends(require_roles(*SC.DONG, mo_ta="kết luận sự cố tour")),
         db: Session = Depends(get_db)):
    sc = db.get(SuCoTour, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ sự cố này")
    try:
        SC.dong(db, u, sc, inp.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": f"Đã đóng hồ sơ {sc.code}"}


class MoLaiIn(BaseModel):
    ly_do: str


@router.post("/su-co-tour/{sid}/mo-lai")
def mo_lai(sid: int, inp: MoLaiIn, u: User = Depends(require_roles(*SC.DONG, mo_ta="mở lại sự cố tour")),
           db: Session = Depends(get_db)):
    sc = db.get(SuCoTour, sid)
    if not sc: raise HTTPException(404, "Không có hồ sơ sự cố này")
    try:
        SC.mo_lai(db, u, sc, inp.ly_do)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": f"Đã mở lại hồ sơ {sc.code}"}
