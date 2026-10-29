"""KS-10 · Cửa máy chủ cho ĐƠN khách sạn — sáu bước Agoda, phía VTOS.

    /api/v1/don-khach-san-ota/*   — Điều hành thao tác, Chủ tịch / TGĐ / Ban Kiểm soát xem.

KHÔNG có nhóm cửa phía ngoài trong vòng này. Bảng đơn của KS-6 chưa có cột nào ghi NGƯỜI ĐẶT,
nên mở cửa cho khách lúc này là để ai biết thẻ tham chiếu cũng đọc được đơn người khác. Cửa cho
khách là một vòng riêng, sau khi có cột chủ đơn.

Mọi con số của nguồn vào bằng cửa nhập: ở «Chạy thật» Điều hành dán từ Agoda, ở «Thử» máy sinh.
Tệp này không gọi mạng và không nhận một ô số thẻ nào — Fulfill Assisted, Agoda thu tiền khách.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import dat_phong_ota as S
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.models.cong_ngoai import TaiKhoanNgoai

router_vtos = APIRouter(prefix="/api/v1/don-khach-san-ota", tags=["khach-san-ota"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiOta as ex:
        raise HTTPException(ex.status, str(ex))


def _ten(u: User) -> str:
    return (getattr(u, "ho_ten", "") or getattr(u, "email", "") or str(getattr(u, "id", "")))[:80]


# ---------------------------------------------------------------- xem

@router_vtos.get("")
def ds(trang_thai: str = "", moi_truong: str = "",
       u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return S.ds(db, trang_thai, moi_truong)


@router_vtos.get("/{don_id}")
def mot_don(don_id: int, u: User = Depends(require_roles(*S.VAI_XEM)),
            db: Session = Depends(get_db)):
    from app.services import don_khach_san_ota as D
    don = _goi(S.lay_don, db, don_id)
    return {"don": D.tom_tat(don), "nhat_ky": S.nhat_ky(db, don_id), **S.tham_so()}


# ---------------------------------------------------------------- bước 1 · Search

class HoiGiaIn(BaseModel):
    ota_id: int
    ngay_nhan: str | None = None
    ngay_tra: str | None = None
    so_phong: int = 1
    nguoi_lon: int = 2
    tre_em: int = 0
    tuoi_tre_em: str = ""
    nuoc_khach: str = "VN"
    ngon_ngu: str = "vi-vn"
    tien_te: str = "VND"
    ghi_chu: str = ""
    # Số của NGUỒN — Điều hành dán từ Agoda khi môi trường là «Chạy thật». Ở «Thử» bỏ trống,
    # máy sinh. Không có ô nào nhận số thẻ: Agoda thu tiền khách, Vietourist không chạm vào.
    ma_tim: int | None = None
    ma_khoi: str | None = None
    the_chao: str | None = None
    ma_khach_san: int | None = None
    ma_phong: int | None = None
    ma_goi_gia: int | None = None
    gia_gom_thue: float | None = None
    kieu_thanh_toan: str | None = None
    phu_thu: str | None = None


@router_vtos.post("/hoi-gia")
def hoi_gia(data: HoiGiaIn, u: User = Depends(require_roles(*S.VAI_LAM)),
            db: Session = Depends(get_db)):
    from datetime import date
    d = data.model_dump()
    for k in ("ngay_nhan", "ngay_tra"):
        if d.get(k):
            try:
                d[k] = date.fromisoformat(d[k])
            except ValueError:
                raise HTTPException(400, "Ngày không đọc được: " + k)
    don = _goi(S.hoi_gia, db, _ten(u), d)
    return {"message": "Đã dựng đơn " + don.the_tham_chieu, **S.ds(db)}


# ---------------------------------------------------------------- bước 2 · Precheck

class SoatTruocIn(BaseModel):
    ngay_nhan: str | None = None
    ngay_tra: str | None = None
    so_phong: int | None = None
    nguoi_lon: int | None = None
    tre_em: int | None = None
    tuoi_tre_em: str | None = None
    nuoc_khach: str | None = None
    ngon_ngu: str | None = None
    tien_te: str | None = None


@router_vtos.post("/{don_id}/soat-truoc")
def soat_truoc(don_id: int, data: SoatTruocIn, u: User = Depends(require_roles(*S.VAI_LAM)),
               db: Session = Depends(get_db)):
    gui = {k: v for k, v in data.model_dump().items() if v is not None}
    r = _goi(S.soat_truoc, db, _ten(u), don_id, gui)
    r["message"] = "Khớp cả ba bước" if not r["lech"] else "Lệch %d ô" % len(r["lech"])
    return r


# ---------------------------------------------------------------- bước 3 · Book

class TraLoiDat(BaseModel):
    id: int | None = None
    itineraryId: int | None = None
    processing: bool = False


class DatIn(BaseModel):
    qua_han: bool = False
    tra_loi: TraLoiDat | None = None


@router_vtos.post("/{don_id}/dat")
def dat(don_id: int, data: DatIn, u: User = Depends(require_roles(*S.VAI_LAM)),
        db: Session = Depends(get_db)):
    d = {"qua_han": data.qua_han,
         "tra_loi": data.tra_loi.model_dump() if data.tra_loi else {}}
    r = _goi(S.dat, db, _ten(u), don_id, d)
    r["message"] = ("Đã ghi QUÁ HẠN — phải tra Booking List bằng thẻ tham chiếu, "
                    "không gửi lại") if r["qua_han"] else "Đã đặt"
    return r


# ---------------------------------------------------------------- bước 4 · Booking Detail

class TrangThaiIn(BaseModel):
    trang_thai_nguon: str = ""
    so_xac_nhan_ks: str | None = None
    tham_chieu_nguon: str | None = None


@router_vtos.post("/{don_id}/trang-thai")
def trang_thai(don_id: int, data: TrangThaiIn, u: User = Depends(require_roles(*S.VAI_LAM)),
               db: Session = Depends(get_db)):
    d = {k: v for k, v in data.model_dump().items() if v is not None}
    r = _goi(S.nhan_trang_thai, db, _ten(u), don_id, d)
    r["message"] = "Đã ghi trạng thái nguồn"
    return r


# ---------------------------------------------------------------- bước 5 · Cancel preview

@router_vtos.post("/{don_id}/xem-huy")
def xem_huy(don_id: int, u: User = Depends(require_roles(*S.VAI_LAM)),
            db: Session = Depends(get_db)):
    r = _goi(S.xem_huy, db, _ten(u), don_id)
    r["message"] = "Huỷ được" if r["huy_duoc"] else "Chưa huỷ được"
    return r


# ---------------------------------------------------------------- bước 6 · Confirm cancel

class BaSoHuy(BaseModel):
    bookingId: int | None = None
    reference: int | None = None
    refundInclusive: float | None = None


class HuyIn(BaseModel):
    xem: BaSoHuy
    gui: BaSoHuy
    cancelReason: int = 0


@router_vtos.post("/{don_id}/huy")
def huy(don_id: int, data: HuyIn, u: User = Depends(require_roles(*S.VAI_LAM)),
        db: Session = Depends(get_db)):
    gui = data.gui.model_dump()
    gui["cancelReason"] = data.cancelReason
    r = _goi(S.huy, db, _ten(u), don_id, data.xem.model_dump(), gui)
    r["message"] = "Đã huỷ"
    return r
# ---------------------------------------------------------------- KS-11 · cửa cho khách
# Gắn vào ĐÚNG tiền tố `/api/v1/cong/khach-san` đã có từ KS-1, nên KHÔNG thêm nhóm API mới:
# bản đồ quyền và bảng phạm vi vai trò không đổi một con số nào.
#
# Mọi cửa dưới đây đi qua `tai_khoan_ngoai` — phiên cổng ngoài, KHÔNG phải phiên VTOS. Một tài
# khoản cổng ngoài không bao giờ là một `User`, nên không có đường nào từ đây vào màn nội bộ.
#
# KHÔNG CÓ Ô SỐ THẺ ở bất kỳ cửa nào: Fulfill Assisted — Agoda thu tiền thẳng của khách.

router_cong = APIRouter(prefix="/api/v1/cong/khach-san", tags=["khach-san-ota"])


class YeuCauIn(BaseModel):
    noi_den: str
    ngay_nhan: str | None = None
    ngay_tra: str | None = None
    so_phong: int = 1
    nguoi_lon: int = 2
    tre_em: int = 0
    nguoi_nhan_phong: str = ""
    lien_he: str = ""
    yeu_cau_them: str = ""


@router_cong.post("/yeu-cau")
def gui_yeu_cau(data: YeuCauIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai),
                db: Session = Depends(get_db)):
    don = _goi(S.gui_yeu_cau, db, tk, data.model_dump())
    return {"message": "Đã nhận yêu cầu. Vietourist sẽ báo giá cho bạn.",
            "don": S.tom_tat_khach(don), **S.tham_so_khach()}


@router_cong.get("/don-cua-toi")
def don_cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    return {"don": _goi(S.don_cua_toi, db, tk), **S.tham_so_khach()}


@router_cong.get("/don/{don_id}")
def mot_don(don_id: int, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai),
            db: Session = Depends(get_db)):
    return {"don": _goi(S.mot_don_cua_toi, db, tk, don_id), **S.tham_so_khach()}


# ------------------------------------------------- phía VTOS · nhận một yêu cầu của khách

class HoiGiaYeuCauIn(BaseModel):
    ota_id: int
    ma_tim: int | None = None
    ma_khoi: str | None = None
    the_chao: str | None = None
    ma_khach_san: int | None = None
    ma_phong: int | None = None
    ma_goi_gia: int | None = None
    gia_gom_thue: float | None = None
    kieu_thanh_toan: str | None = None
    phu_thu: str | None = None
    nuoc_khach: str | None = None
    ngon_ngu: str | None = None
    tien_te: str | None = None


@router_vtos.post("/{don_id}/hoi-gia-yeu-cau")
def hoi_gia_yeu_cau(don_id: int, data: HoiGiaYeuCauIn,
                    u: User = Depends(require_roles(*S.VAI_LAM)),
                    db: Session = Depends(get_db)):
    don = _goi(S.hoi_gia_yeu_cau, db, u.username, don_id, data.model_dump())
    return {"message": "Đã hỏi giá cho yêu cầu của khách", "don_id": don.id}
