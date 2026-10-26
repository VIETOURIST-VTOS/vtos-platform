"""KH-1 · Cổng khách hàng VTD — mọi cửa đòi PHIÊN CỔNG NGOÀI (không phải phiên VTOS) và loại khách hàng."""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.services import cong_khach as K
from app.services import cong_ngoai as C

router = APIRouter(prefix="/api/v1/cong/khach", tags=["cong-khach-hang"])


def _khach(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai)) -> TaiKhoanNgoai:
    try:
        K.la_khach(tk)
    except K.LoiKhach as ex:
        raise HTTPException(403, str(ex))
    return tk


def _loi(ex: K.LoiKhach):
    raise HTTPException(400, str(ex))


@router.get("/trang-chu")
def trang_chu(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return K.trang_chu(db, tk)


@router.get("/tour")
def ds_tour(q: str = "", tu_ngay: date | None = None, noi: str = "", ngan_sach: int = 0, nhom: str = "",
            tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return {"tour": K.tours(db, q, tu_ngay, noi, ngan_sach, nhom), "noi_khoi_hanh": K.noi_khoi_hanh(db)}


@router.get("/tour/{tour_id}")
def mot_tour(tour_id: int, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    try:
        return K.tour(db, tour_id)
    except K.LoiKhach as ex:
        raise HTTPException(404, str(ex))


class NhaHangYcIn(BaseModel):
    nha_hang_id: int
    thuc_don_id: int
    gio: str = ""
    nguoi_lon: int = 0
    tre_em: int = 0


class YeuCauIn(BaseModel):
    loai: str = "tour"
    tour_id: int | None = None
    so_khach: int = 1
    dien_thoai: str = ""
    ngay_mong_muon: date | None = None
    ghi_chu: str = ""
    dong_y: bool = False
    nha_hang: NhaHangYcIn | None = None


@router.post("/yeu-cau")
def gui_yeu_cau(data: YeuCauIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    try:
        yc = K.gui_yeu_cau(db, tk, data.loai, data.tour_id, data.so_khach, data.dien_thoai, data.ngay_mong_muon,
                           data.ghi_chu, data.dong_y, nha_hang=data.nha_hang.model_dump() if data.nha_hang else None)
    except K.LoiKhach as ex:
        _loi(ex)
    return {"message": "Đã gửi yêu cầu. Sales Vietourist sẽ gọi lại cho bạn; yêu cầu chưa giữ chỗ và chưa thu tiền.",
            "id": yc.id}


@router.get("/don")
def don_cua_toi(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    return {"don": K.don_cua_toi(db, tk), "yeu_cau": K.yeu_cau_cua(db, tk)}


@router.get("/don/{ma}")
def mot_don(ma: str, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    try:
        return K.don(db, tk, ma)
    except K.LoiKhach as ex:
        raise HTTPException(404, str(ex))


class HoSoKhachIn(BaseModel):
    ho_ten: str | None = None
    so_thich: str | None = None
    nhan_tin_quang_cao: bool | None = None


@router.get("/ho-so")
def ho_so(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai)):
    _khach(tk)
    return {**C.toi_out(tk), "so_thich": tk.so_thich, "so_thich_chon": list(K.SO_THICH)}


@router.post("/ho-so")
def sua_ho_so(data: HoSoKhachIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    try:
        tk = K.cap_nhat_ho_so(db, tk, data.ho_ten, data.so_thich, data.nhan_tin_quang_cao)
    except K.LoiKhach as ex:
        _loi(ex)
    return {**C.toi_out(tk), "so_thich": tk.so_thich, "so_thich_chon": list(K.SO_THICH)}


# ── KH-2 ──────────────────────────────────────────────────────────────────────────────────────

@router.get("/nha-hang")
def ds_nha_hang(tinh: str = "", am_thuc: str = "", gia_toi_da: int = 0,
                tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import nha_hang as NH
    return NH.danh_sach_cong(db, tinh, am_thuc, gia_toi_da)


@router.get("/nha-hang/{nid}")
def mot_nha_hang(nid: int, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import nha_hang as NH
    try:
        return NH.mot_nha_hang_cong(db, nid)[1]
    except NH.LoiNhaHang as ex:
        raise HTTPException(404, str(ex))


@router.get("/don/{ma}/qr")
def qr(ma: str, muc: str = "", tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    try:
        return K.qr_don(db, tk, ma, muc)
    except K.LoiKhach as ex:
        _loi(ex)


# ── KH-3 · VTD Rewards & yêu thích ─────────────────────────────────────────────────────────────

@router.get("/diem")
def diem(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import rewards as RW
    return RW.tong_quan(db, RW.chu_cua_tai_khoan(tk))


class DoiIn(BaseModel):
    so_diem: int


@router.post("/diem/doi")
def doi_diem(data: DoiIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import rewards as RW
    chu = RW.chu_cua_tai_khoan(tk)
    if not chu:
        raise HTTPException(400, "Tài khoản chưa có liên hệ xác thực")
    try:
        v = RW.doi_voucher(db, chu[0], data.so_diem)
    except RW.LoiDiem as ex:
        raise HTTPException(400, str(ex))
    n = lambda x: f"{x:,}".replace(",", ".")  # noqa: E731
    return {"message": f"Đã đổi {n(v.so_diem)} điểm lấy voucher {v.ma} trị giá {n(v.gia_tri)} đ, dùng đến {v.han_dung:%d/%m/%Y}. Đọc mã cho Sales khi đặt dịch vụ.",
            "ma": v.ma}


@router.get("/yeu-thich")
def yeu_thich(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import rewards as RW
    return {"yeu_thich": RW.ds_yeu_thich(db, tk), "ids": RW.id_yeu_thich(db, tk)}


class YeuThichIn(BaseModel):
    tour_id: int
    luu: bool = True


@router.post("/yeu-thich")
def luu_yeu_thich(data: YeuThichIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import rewards as RW
    try:
        RW.luu_yeu_thich(db, tk, data.tour_id, data.luu)
    except RW.LoiDiem as ex:
        raise HTTPException(400, str(ex))
    return {"ids": RW.id_yeu_thich(db, tk)}


# ── KH-4 · Đánh giá · Góp ý riêng lãnh đạo · Hỗ trợ ────────────────────────────────────────────

@router.get("/danh-gia")
def danh_gia(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    return {"chuyen": CK.chuyen_danh_gia(db, tk), "mo_cham_ngay": CK.MO_CHAM_NGAY, "sua_ngay": CK.SUA_NGAY}


class DanhGiaIn(BaseModel):
    ma_don: str
    diem: list[dict]
    nhu_cau_tiep: str = ""
    cong_khai: str = ""
    gop_y: str = ""


@router.post("/danh-gia")
def gui_danh_gia(data: DanhGiaIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    try:
        return CK.gui_danh_gia(db, tk, data.ma_don, data.model_dump())
    except (CK.LoiCham, K.LoiKhach) as ex:
        raise HTTPException(400, str(ex))


@router.get("/gop-y")
def gop_y(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    return {"gop_y": CK.gop_y_cua(db, tk), "muc": CK.MUC_GOP_Y, "lien_he": CK.LIEN_HE_LAI}


class GopYKhachIn(BaseModel):
    tieu_de: str
    noi_dung: str
    muc: str = "thuong"
    lien_he_qua: str = "email"
    ma_don: str = ""


@router.post("/gop-y")
def gui_gop_y(data: GopYKhachIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    try:
        g = CK.gui_gop_y(db, tk, data.model_dump())
    except (CK.LoiCham, K.LoiKhach) as ex:
        raise HTTPException(400, str(ex))
    return {"ma": g.ma, "message": f"Đã gửi góp ý {g.ma}. Chỉ Chủ tịch HĐQT và Tổng Giám đốc đọc góp ý này."}


@router.get("/ho-tro")
def ho_tro(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    return {"yeu_cau": CK.ho_tro_cua(db, tk), "loai": CK.LOAI_HO_TRO}


class HoTroIn(BaseModel):
    loai: str
    ma_don: str = ""
    noi_dung: str = ""
    hoa_don: dict | None = None


@router.post("/ho-tro")
def gui_ho_tro(data: HoTroIn, tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)):
    _khach(tk)
    from app.services import cham_soc_khach as CK
    try:
        y = CK.gui_ho_tro(db, tk, data.model_dump())
    except (CK.LoiCham, K.LoiKhach) as ex:
        raise HTTPException(400, str(ex))
    return {"ma": y.ma, "bo_phan": CK.BO_PHAN[y.bo_phan], "loai": CK.LOAI_HO_TRO[y.loai],
            "message": f"Đã gửi yêu cầu {y.ma} tới {CK.BO_PHAN[y.bo_phan]}. Người phụ trách sẽ trả lời tại đây."}
