"""KS-16q (Chủ tịch duyệt bản xem thử 01/11/2026) · ba trang riêng kh.vietourist.vn/hotel, /restaurant, /tours.

Khách CHƯA đăng nhập được XEM (danh sách, chi tiết, đánh giá). Mọi việc ĐẶT, gửi yêu cầu, tính giá đặt, thanh
toán, đơn của tôi vẫn ở các cửa cũ đòi phiên cổng ngoài (tai_khoan_ngoai). Router này CHỈ có GET, không đọc
và không trả gì gắn với một tài khoản (điểm VTD Rewards luôn «chưa bật» ở đây)."""
import time
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import khach_san_vtd as S

# Phanh chống cào dữ liệu: mỗi địa chỉ tối đa 240 lượt / 10 phút cho cả router (khách xem bình thường dư sức).
CUA_SO_GIAY, TOI_DA_TRONG_CUA_SO = 600, 240
_LUOT: dict = defaultdict(list)


def _phanh(req: Request) -> None:
    ip = (req.headers.get("x-forwarded-for", "").split(",")[0].strip() or (req.client.host if req.client else "")) or "?"
    bay_gio = time.time()
    v = [t for t in _LUOT[ip] if bay_gio - t < CUA_SO_GIAY]
    if len(v) >= TOI_DA_TRONG_CUA_SO:
        _LUOT[ip] = v
        raise HTTPException(429, "Quá nhiều lượt xem từ địa chỉ này — đợi ít phút rồi thử lại")
    v.append(bay_gio)
    _LUOT[ip] = v


router = APIRouter(prefix="/api/v1/cong/mo", tags=["cong-mo"], dependencies=[Depends(_phanh)])

KHONG_DIEM = {"dang_bat": False, "hang": None, "he_so": 0}


def _ks(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiKhachSan as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/ks-vtd/tim")
def ks_tim(tinh: str = "", vao: str = "", ra: str = "", nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1, tuoi: str = "",
           db: Session = Depends(get_db)):
    return {**_ks(S.tim, db, tinh, vao, ra, nguoi_lon, tre_em, so_phong, None, tuoi), "diem": KHONG_DIEM}


@router.get("/ks-vtd/{kid:int}")
def ks_mot(kid: int, vao: str = "", ra: str = "", nguoi_lon: int = 2, tre_em: int = 0, so_phong: int = 1, tuoi: str = "",
           db: Session = Depends(get_db)):
    return {**_ks(S.chi_tiet_cong, db, kid, vao, ra, nguoi_lon, tre_em, so_phong, None, tuoi), "diem": KHONG_DIEM}


@router.get("/ks-vtd/{kid:int}/danh-gia")
def ks_danh_gia(kid: int, trang: int = 1, xep: str = "moi", db: Session = Depends(get_db)):
    from app.services import danh_gia_ks as DGK
    try:
        return DGK.cong(db, kid, trang, 10, xep)
    except DGK.LoiDanhGiaKs as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/tour")
def tour_ds(q: str = "", tu_ngay: date | None = None, noi: str = "", ngan_sach: int = 0, nhom: str = "", db: Session = Depends(get_db)):
    from app.services import cong_khach as K
    return {"tour": K.tours(db, q, tu_ngay, noi, ngan_sach, nhom), "noi_khoi_hanh": K.noi_khoi_hanh(db)}


@router.get("/tour/{tour_id:int}")
def tour_mot(tour_id: int, db: Session = Depends(get_db)):
    from app.services import cong_khach as K
    try:
        return K.tour(db, tour_id)
    except K.LoiKhach as ex:
        raise HTTPException(404, str(ex))


@router.get("/nha-hang")
def nh_ds(tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0, q: str = "", chi_dat: bool = False, trang: int = 1, loai: str = "",
          bac: str = "", db: Session = Depends(get_db)):
    from app.services import nha_hang as NH
    return NH.danh_sach_cong(db, tinh, am_thuc, gia_toi_da, q, chi_dat, trang, loai=loai, bac=bac)


@router.get("/nha-hang/{nid:int}")
def nh_mot(nid: int, db: Session = Depends(get_db)):
    from app.services import nha_hang as NH
    try:
        return NH.mot_nha_hang_cong(db, nid)[1]
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))


@router.get("/nha-hang/tat-ca")
def nh_tat_ca(db: Session = Depends(get_db)):
    """AT-2: mọi nhà hàng đang hiện trong một lần — trang riêng /restaurant lọc, đếm, vẽ bản đồ trên trình duyệt."""
    from app.services import dat_ban as DB
    from app.services import nha_hang as NH
    return {**NH.tat_ca_cong(db), "tham_so": DB.tham_so(db), "the_bat": DB.SP.cong_the_bat()}


# ── TR-1 (Chủ tịch duyệt 01–02/11/2026) · tour kiểu Agoda trên kh.vietourist.vn/tours — XEM không cần đăng nhập ──
def _tr(f, *a, **k):
    from app.services import tour_online as TR
    try:
        return f(*a, **k)
    except TR.LoiTour as ex:
        raise HTTPException(ex.status, str(ex))


def _lam_moi_nen(pid: int) -> None:
    """Cache web cũ hơn 24 giờ → đọc lại SAU khi đã trả trang cho khách (phiên DB riêng). Hỏng thì giữ bản cũ."""
    from app.db.session import SessionLocal
    from app.models.core import Product
    from app.services import tour_online as TR
    db = SessionLocal()
    try:
        p = db.get(Product, pid)
        if p is not None and TR.can_lam_moi(p):
            TR.lam_moi(db, p)
            db.commit()
    finally:
        db.close()


@router.get("/tour-online/tim")
def tr_tim(tab: str = "", q: str = "", noi: str = "", tu: date | None = None, den: date | None = None, nguoi_lon: int = 2,
           tre_em: int = 0, loai: str = "", db: Session = Depends(get_db)):
    from app.services import tour_online as TR
    return _tr(TR.tim, db, tab, q, noi, tu, den, nguoi_lon, tre_em, loai)


@router.get("/tour-online/san-pham/{pid:int}")
def tr_mot(pid: int, background: BackgroundTasks, nguoi_lon: int = 2, tre_em: int = 0, db: Session = Depends(get_db)):
    from app.models.core import Product
    from app.services import tour_online as TR
    p = db.get(Product, pid)
    if p is not None and p.link_web and not p.noi_dung_web:
        TR.lam_moi(db, p)                       # chưa có bản nào: đọc ngay (hỏng thì vẫn trả trang, chỉ thiếu ảnh)
        db.commit()
    elif p is not None and TR.can_lam_moi(p):
        background.add_task(_lam_moi_nen, p.id)
    return _tr(TR.chi_tiet, db, pid, nguoi_lon, tre_em)


@router.get("/tour-online/san-pham/{pid:int}/lich-trinh/{tour_id:int}")
def tr_lich(pid: int, tour_id: int, db: Session = Depends(get_db)):
    from app.services import tour_online as TR
    return _tr(TR.lich_trinh_chuyen, db, pid, tour_id)


@router.get("/tour-online/tinh")
def tr_tinh(tour_id: int, nguoi_lon: int = 1, tre_em: int = 0, em_be: int = 0, cach_tra: str = "coc", db: Session = Depends(get_db)):
    from app.services import tour_online as TR
    return _tr(TR.tinh, db, tour_id, nguoi_lon, tre_em, em_be, cach_tra)


# ── TR-1d (Chủ tịch duyệt 02/11/2026) · link thanh toán tour đoàn riêng kh.vietourist.vn/thanh-toan/TD… ─────────
# Khách mở link KHÔNG cần đăng nhập: mã link là thứ Sale Admin gửi riêng cho khách. Chỉ GET; tiền vào đi qua
# khớp giao dịch ngân hàng (robot + Kế toán), không có cửa ghi nào ở đây. Phanh chung của router chặn dò mã.
def _ttd(f, *a, **k):
    from app.services import thanh_toan_doan as TTD
    try:
        return f(*a, **k)
    except TTD.LoiTTD as ex:
        raise HTTPException(ex.status, str(ex))


@router.get("/tt-doan/{ma}")
def ttd_xem(ma: str, db: Session = Depends(get_db)):
    from app.services import thanh_toan_doan as TTD
    return _ttd(TTD.xem_cong, db, ma)


@router.get("/tt-doan/{ma}/hoa-don")
def ttd_hoa_don(ma: str, db: Session = Depends(get_db)):
    from fastapi.responses import Response
    from app.services import thanh_toan_doan as TTD
    pdf = _ttd(TTD.tai_hoa_don, db, ma)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="HoaDon-{ma.upper()}.pdf"'})
