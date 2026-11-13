"""V6 – cửa của chuỗi bán hàng: bảng giá, báo giá, hợp đồng khách.

Ba nhóm đường dẫn nhưng MỘT tiền tố "/api/v1/ban-hang", vì hàng rào phạm vi chỉ phân biệt tới mức
tiền tố – ba tiền tố là ba dòng phải khai và ba chỗ để quên một dòng.
"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.ban_hang import (BangGia, BangGiaDong, BaoGia, BaoGiaDong, BaoGiaBan,
                                 HopDongKhach, LichThanhToanHD, MOC_HAN, MANG, TRANG_THAI_BAO_GIA)
from app.services import ban_hang as BH
from app.services import ghi_mot_lan as GML, rules as R

router = APIRouter(prefix="/api/v1/ban-hang", tags=["ban-hang"])

# Ai XEM được chuỗi bán hàng. Kế toán có mặt vì hợp đồng là căn cứ ghi nhận doanh thu.
XEM = ("chutich", "tgd", "bks", "cntt", "ptgd_mkt", "gd_kd", "tp_kd", "tn_kd", "nv_kd",
       "nv_mkt", "ketoan", "tp_dh", "nv_dh", "ptgd_doan")
# Ai SOẠN báo giá: khối kinh doanh. Cổng biên nằm ở bước GỬI, không ở đây.
SOAN = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "ptgd_mkt", "tgd", "chutich", "cntt")
# Ai đặt BẢNG GIÁ: chính sách bán không phải việc của từng sale.
DAT_GIA = ("gd_kd", "tp_kd", "ptgd_mkt", "tgd", "chutich", "cntt")
# TR-1d (Chủ tịch 02/11/2026): Sale Admin phòng Đoàn tạo link thanh toán theo đợt — nên ĐỌC được danh sách hợp
# đồng, lịch thanh toán và link của nó. Chỉ ba cửa đọc ấy; báo giá / bảng giá vẫn như cũ.
XEM_HD = XEM + ("sales_admin",)


class BangGiaIn(BaseModel):
    ten: str
    product_id: int | None = None
    mang: str = "kd_le"
    hieu_luc_tu: date
    hieu_luc_den: date | None = None
    ghi_chu: str = ""
    dong: list[dict] = []


class BaoGiaIn(BaseModel):
    khach_ten: str
    mang: str = "kd_le"
    khach_dien_thoai: str = ""
    khach_email: str = ""
    product_id: int | None = None
    bang_gia_id: int | None = None
    tour_id: int | None = None
    lead_id: int | None = None
    company_id: int | None = None
    ngay_khoi_hanh: date | None = None
    so_khach: int = 1
    han_hieu_luc: date | None = None
    dong: list[dict] = []
    phien_ban: int | None = None


class GuiIn(BaseModel):
    giai_trinh: str = ""


class HopDongIn(BaseModel):
    so_hop_dong: str = ""
    khach_ten: str = ""
    khach_dai_dien: str = ""
    khach_ma_so_thue: str = ""
    khach_dia_chi: str = ""
    ngay_ky: date | None = None
    dat_coc: float = 0
    han_thanh_toan: date | None = None
    ghi_chu: str = ""


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return {"mang": list(MANG), "trang_thai": TRANG_THAI_BAO_GIA,
            "nguong_bien": R.get_param(db, "nguong_bien"),
            "hang_khach": ["nguoi_lon", "tre_em", "em_be", "phu_thu_phong_don"],
            "dai_giai_trinh": BH.DAI_GIAI_TRINH}


# ────────────────────────────── BẢNG GIÁ ──────────────────────────────
@router.get("/bang-gia")
def ds_bang_gia(mang: str = "", product_id: int | None = None,
                u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(BangGia).order_by(BangGia.hieu_luc_tu.desc(), BangGia.id.desc())
    if mang: q = q.where(BangGia.mang == mang)
    if product_id: q = q.where(BangGia.product_id == product_id)
    ra = []
    for b in db.execute(q).scalars():
        dong = db.execute(select(BangGiaDong).where(BangGiaDong.bang_gia_id == b.id)
                          .order_by(BangGiaDong.thu_tu, BangGiaDong.id)).scalars().all()
        ra.append({"id": b.id, "ma": b.ma, "ten": b.ten, "mang": b.mang,
                   "product_id": b.product_id, "hieu_luc_tu": b.hieu_luc_tu,
                   "hieu_luc_den": b.hieu_luc_den, "trang_thai": b.trang_thai,
                   "phien_ban": b.phien_ban, "ghi_chu": b.ghi_chu,
                   "con_hieu_luc": b.hieu_luc_den is None,
                   "dong": [{"id": d.id, "hang_khach": d.hang_khach, "mo_ta": d.mo_ta,
                             "gia_ban": float(d.gia_ban or 0),
                             "gia_von": None if d.gia_von is None else float(d.gia_von),
                             "chiet_khau_toi_da": d.chiet_khau_toi_da} for d in dong]})
    return ra


@router.post("/bang-gia", status_code=201)
def tao_bang_gia(data: BangGiaIn, u: User = Depends(require_roles(*DAT_GIA)),
                 db: Session = Depends(get_db)):
    if data.mang not in MANG:
        raise HTTPException(422, f"Mảng phải là một trong {MANG}")
    if data.hieu_luc_den and data.hieu_luc_den < data.hieu_luc_tu:
        raise HTTPException(422, "Hiệu lực đến trước hiệu lực từ")
    b = BangGia(ma=BH.sinh_ma(db, BangGia, BangGia.ma, "BG"), ten=data.ten,
                product_id=data.product_id, mang=data.mang, hieu_luc_tu=data.hieu_luc_tu,
                hieu_luc_den=data.hieu_luc_den, ghi_chu=data.ghi_chu, tao_boi=u.username)
    db.add(b); db.flush()
    for i, d in enumerate(data.dong):
        db.add(BangGiaDong(bang_gia_id=b.id, hang_khach=d.get("hang_khach", "nguoi_lon"),
                           mo_ta=d.get("mo_ta", ""), gia_ban=None if d.get("gia_ban") in (None, "") else float(d["gia_ban"]),
                           gia_von=None if d.get("gia_von") in (None, "") else float(d["gia_von"]),
                           chiet_khau_toi_da=float(d.get("chiet_khau_toi_da") or 0), thu_tu=i))
    db.commit()
    return {"id": b.id, "ma": b.ma, "message": f"Đã tạo bảng giá {b.ma}"}


# ────────────────────────────── BÁO GIÁ ──────────────────────────────
def _bg_ra(db: Session, bg: BaoGia) -> dict:
    dong = db.execute(select(BaoGiaDong).where(BaoGiaDong.bao_gia_id == bg.id)
                      .order_by(BaoGiaDong.thu_tu, BaoGiaDong.id)).scalars().all()
    ban = db.execute(select(BaoGiaBan).where(BaoGiaBan.bao_gia_id == bg.id)
                     .order_by(BaoGiaBan.lan.desc())).scalars().all()
    return {"id": bg.id, "ma": bg.ma, "mang": bg.mang, "khach_ten": bg.khach_ten,
            "khach_dien_thoai": bg.khach_dien_thoai, "khach_email": bg.khach_email,
            "product_id": bg.product_id, "bang_gia_id": bg.bang_gia_id, "tour_id": bg.tour_id,
            "lead_id": bg.lead_id, "company_id": bg.company_id,
            "so_khach": bg.so_khach, "ngay_khoi_hanh": bg.ngay_khoi_hanh,
            "han_hieu_luc": bg.han_hieu_luc, "trang_thai": bg.trang_thai,
            "trang_thai_ten": TRANG_THAI_BAO_GIA.get(bg.trang_thai, bg.trang_thai),
            "duoi_bien": bg.duoi_bien, "giai_trinh": bg.giai_trinh,
            "bien_luc_gui": bg.bien_luc_gui, "nguong_luc_gui": bg.nguong_luc_gui,
            "phien_ban": bg.phien_ban, "tao_boi": bg.tao_boi, "tao_luc": bg.tao_luc,
            "dong": [{"id": d.id, "hang_khach": d.hang_khach, "mo_ta": d.mo_ta,
                      "so_luong": d.so_luong, "don_gia": float(d.don_gia or 0),
                      "gia_von_don_vi": None if d.gia_von_don_vi is None else float(d.gia_von_don_vi),
                      "chiet_khau": float(d.chiet_khau or 0)} for d in dong],
            "ban_da_gui": [{"id": b.id, "lan": b.lan, "tong_ban": float(b.tong_ban or 0),
                            "tong_von": None if b.tong_von is None else float(b.tong_von),
                            "bien": b.bien, "nguong": b.nguong, "du_co_so": b.du_co_so,
                            "gui_boi": b.gui_boi, "gui_luc": b.gui_luc} for b in ban],
            "cong_bien": BH.xem_bien(db, bg), "nguon": bg.nguon, **_tu_thiet_ke(db, bg)}


def _tu_thiet_ke(db: Session, bg: BaoGia) -> dict:
    """KS-19k: báo giá đoàn lập từ thiết kế — kèm mã thiết kế và GIÁ BÁN (không giá vốn) để màn Bán hàng xem được."""
    if bg.nguon != "thiet_ke":
        return {}
    from app.models.thiet_ke_doan import BaoGiaDoan
    p = db.get(BaoGiaDoan, bg.id)
    if p is None:
        return {}
    return {"thiet_ke": {"ma": p.thiet_ke_ma, "so_nl": p.so_nl, "so_te": p.so_te, "so_eb": p.so_eb,
                         "gia_nl": p.gia_nl, "gia_te": p.gia_te, "tong_ban": p.tong_ban,
                         "han_luc": p.han_luc.isoformat(timespec="minutes") if p.han_luc else None}}


@router.get("/tour-de-chon")
def tour_de_chon(u: User = Depends(require_roles(*SOAN)), db: Session = Depends(get_db)):
    """Danh sách tour để gắn báo giá. CHỈ mã, tên, ngày đi – không kèm con số tiền nào.

    Người soạn báo giá không nằm trong COST_ROLES; mở cơ cấu chi phí tour cho họ là một quyết định về
    quyền, không phải một tiện ích để lén thêm vào đây."""
    from app.models.core import Tour
    q = (select(Tour).where(Tour.status.notin_(["huy"]))
         .order_by(Tour.start_date.desc()).limit(300))
    return [{"id": t.id, "code": t.code, "name": t.name, "start_date": t.start_date}
            for t in db.execute(q).scalars()]


@router.get("/tour/{tour_id}/gia-von")
def gia_von_tour(tour_id: int, so_khach: int = 1, u: User = Depends(require_roles(*SOAN)),
                 db: Session = Depends(get_db)):
    """Giá vốn MỘT KHÁCH suy từ dự toán tour – một con số tổng, không có dòng chi tiết.

    Trả về gia_von_moi_khach = null khi tour chưa có dự toán. Rỗng chứ không phải 0: hai cái đó khác
    nhau, và chỗ khác nhau đó là chỗ cổng biên báo ĐẠT trên một tour chưa ai tính giá vốn."""
    return BH.gia_von_tu_du_toan(db, tour_id, so_khach)


@router.get("/bao-gia")
def ds_bao_gia(mang: str = "", trang_thai: str = "", limit: int = 200,
               u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(BaoGia).order_by(BaoGia.id.desc()).limit(min(limit, 500))
    if mang: q = q.where(BaoGia.mang == mang)
    if trang_thai: q = q.where(BaoGia.trang_thai == trang_thai)
    return [_bg_ra(db, b) for b in db.execute(q).scalars()]


@router.get("/bao-gia/{bid}")
def mot_bao_gia(bid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    bg = db.get(BaoGia, bid)
    if bg is None: raise HTTPException(404, "Không có báo giá")
    return _bg_ra(db, bg)


@router.post("/bao-gia", status_code=201)
def tao_bao_gia(data: BaoGiaIn, u: User = Depends(require_roles(*SOAN)),
                db: Session = Depends(get_db)):
    if data.mang not in MANG:
        raise HTTPException(422, f"Mảng phải là một trong {MANG}")
    bg = BaoGia(ma=BH.sinh_ma(db, BaoGia, BaoGia.ma, "BQ"), mang=data.mang,
                khach_ten=data.khach_ten, khach_dien_thoai=data.khach_dien_thoai,
                khach_email=data.khach_email, product_id=data.product_id,
                bang_gia_id=data.bang_gia_id, tour_id=data.tour_id, lead_id=data.lead_id,
                company_id=data.company_id, ngay_khoi_hanh=data.ngay_khoi_hanh,
                so_khach=data.so_khach, han_hieu_luc=data.han_hieu_luc,
                sales_id=u.id, tao_boi=u.username)
    db.add(bg); db.flush()
    _ghi_dong(db, bg, data.dong)
    db.commit()
    return {"id": bg.id, "ma": bg.ma, "message": f"Đã tạo báo giá {bg.ma}"}


def _ghi_dong(db: Session, bg: BaoGia, dong: list[dict]) -> None:
    for d in db.execute(select(BaoGiaDong).where(BaoGiaDong.bao_gia_id == bg.id)).scalars().all():
        db.delete(d)
    db.flush()
    for i, d in enumerate(dong):
        gv = d.get("gia_von_don_vi")
        db.add(BaoGiaDong(bao_gia_id=bg.id, hang_khach=d.get("hang_khach", "nguoi_lon"),
                          mo_ta=d.get("mo_ta", ""), so_luong=int(d.get("so_luong") or 1),
                          don_gia=float(d.get("don_gia") or 0),
                          gia_von_don_vi=None if gv in (None, "") else float(gv),
                          chiet_khau=float(d.get("chiet_khau") or 0), thu_tu=i))
    db.flush()


@router.put("/bao-gia/{bid}")
def sua_bao_gia(bid: int, data: BaoGiaIn, u: User = Depends(require_roles(*SOAN)),
                db: Session = Depends(get_db)):
    bg = db.get(BaoGia, bid)
    if bg is None: raise HTTPException(404, "Không có báo giá")
    BH.chi_xem_neu_tu_thiet_ke(bg)
    if bg.trang_thai in ("khach_chot", "huy"):
        raise HTTPException(422, f"Báo giá đang ở '{bg.trang_thai}', không sửa được")
    GML.kiem_phien_ban(bg, data.phien_ban, f"Báo giá {bg.ma}", lambda: _bg_ra(db, bg))
    # Chỉ ghi đè những trường người gọi THẬT SỰ gửi lên. Trước đây vòng lặp gán cả những trường có
    # giá trị mặc định None, nên một màn hình chỉ sửa tên khách cũng xóa mất lead_id và company_id –
    # mất lặng lẽ, và chỉ lộ ra lúc đi tìm báo giá này thuộc nguồn khách nào.
    da_gui = data.model_fields_set
    for k in ("khach_ten", "khach_dien_thoai", "khach_email", "product_id", "bang_gia_id",
              "tour_id", "lead_id", "company_id", "ngay_khoi_hanh", "so_khach", "han_hieu_luc"):
        if k in da_gui:
            setattr(bg, k, getattr(data, k))
    _ghi_dong(db, bg, data.dong)
    GML.tang_phien_ban(bg)
    db.commit()
    return _bg_ra(db, bg)


@router.post("/bao-gia/{bid}/gui")
def gui_bao_gia(bid: int, data: GuiIn, x_khoa_ghi: str | None = Header(default=None),
                u: User = Depends(require_roles(*SOAN)), db: Session = Depends(get_db)):
    """Cổng biên đứng ở đây – xem app/services/ban_hang.gui_khach."""
    bg = db.get(BaoGia, bid)
    if bg is None: raise HTTPException(404, "Không có báo giá")
    khoa = x_khoa_ghi or GML.suy_khoa(f"/ban-hang/bao-gia/{bid}/gui", u.username,
                                      {"giai_trinh": data.giai_trinh, "pb": bg.phien_ban})
    cu = GML.da_ghi_roi(db, khoa, tu_suy=not x_khoa_ghi)
    if cu is not None:
        return cu
    ban = BH.gui_khach(db, bg, u.username, data.giai_trinh)
    ra = {"ban_id": ban.id, "lan": ban.lan, "tong_ban": float(ban.tong_ban or 0),
          "bien": ban.bien, "du_co_so": ban.du_co_so, "duoi_bien": bg.duoi_bien,
          "message": f"Đã gửi khách – bản lần {ban.lan}"}
    GML.nho_ket_qua(db, khoa, f"/ban-hang/bao-gia/{bid}/gui", u.username, ra)
    db.commit()
    return ra


@router.post("/bao-gia/{bid}/khach-chot")
def chot(bid: int, u: User = Depends(require_roles(*SOAN)), db: Session = Depends(get_db)):
    bg = db.get(BaoGia, bid)
    if bg is None: raise HTTPException(404, "Không có báo giá")
    BH.khach_chot(db, bg, u.username); db.commit()
    return {"message": f"Báo giá {bg.ma}: khách đã chốt"}


# ────────────────────────────── HỢP ĐỒNG ──────────────────────────────
def _hd_ra(hd: HopDongKhach) -> dict:
    return {"id": hd.id, "so_hop_dong": hd.so_hop_dong, "bao_gia_id": hd.bao_gia_id,
            "booking_id": hd.booking_id, "khach_ten": hd.khach_ten,
            "khach_dai_dien": hd.khach_dai_dien, "khach_ma_so_thue": hd.khach_ma_so_thue,
            "ngay_ky": hd.ngay_ky, "gia_tri": float(hd.gia_tri or 0),
            "dat_coc": float(hd.dat_coc or 0), "han_thanh_toan": hd.han_thanh_toan,
            "trang_thai": hd.trang_thai, "phien_ban": hd.phien_ban}


@router.get("/hop-dong")
def ds_hop_dong(trang_thai: str = "", u: User = Depends(require_roles(*XEM_HD)),
                db: Session = Depends(get_db)):
    q = select(HopDongKhach).order_by(HopDongKhach.id.desc())
    if trang_thai: q = q.where(HopDongKhach.trang_thai == trang_thai)
    return [_hd_ra(h) for h in db.execute(q).scalars()]


@router.post("/bao-gia/{bid}/hop-dong", status_code=201)
def lap_hop_dong(bid: int, data: HopDongIn, u: User = Depends(require_roles(*SOAN)),
                 db: Session = Depends(get_db)):
    bg = db.get(BaoGia, bid)
    if bg is None: raise HTTPException(404, "Không có báo giá")
    hd = BH.lap_hop_dong(db, bg, u.username, **data.model_dump())
    db.commit()
    return {**_hd_ra(hd), "message": f"Đã lập hợp đồng {hd.so_hop_dong}"}


@router.post("/hop-dong/{hid}/booking/{booking_id}")
def noi_booking(hid: int, booking_id: int, u: User = Depends(require_roles(*SOAN)),
                db: Session = Depends(get_db)):
    hd = db.get(HopDongKhach, hid)
    if hd is None: raise HTTPException(404, "Không có hợp đồng")
    BH.noi_booking(db, hd, booking_id); db.commit()
    return {**_hd_ra(hd), "message": "Đã nối hợp đồng với booking"}


# ───────────────── VPM-9: lịch thanh toán theo tiến độ ─────────────────
# Đặt dưới tiền tố "/api/v1/ban-hang" đã được cấp quyền sẵn – không mở tiền tố API mới.
class DotLichIn(BaseModel):
    ten: str = ""
    so_tien: float
    ty_le: float | None = None
    moc: str = "co_dinh"          # ngay_ky / truoc_khoi_hanh / sau_khoi_hanh / co_dinh
    moc_so_ngay: int | None = None
    han: date | None = None       # chỉ dùng khi moc = "co_dinh"
    ghi_chu: str = ""


class LichIn(BaseModel):
    # VPM-8 – đặt lại lịch là sửa hợp đồng (nó ghi vào `han_thanh_toan`), nên đi qua khoá phiên bản.
    phien_ban: int | None = None
    dot: list[DotLichIn]


class DoiHanIn(BaseModel):
    han: date
    ly_do: str


def _hd(db: Session, hid: int) -> HopDongKhach:
    hd = db.get(HopDongKhach, hid)
    if hd is None: raise HTTPException(404, "Không có hợp đồng")
    return hd


@router.get("/hop-dong/{hid}/lich-thanh-toan")
def xem_lich(hid: int, u: User = Depends(require_roles(*XEM_HD)), db: Session = Depends(get_db)):
    from app.services import lich_thanh_toan as LTT
    hd = _hd(db, hid)
    b = LTT.bang(db, hd)
    b["canh_bao"] = LTT.canh_bao_doi_ngay_khoi_hanh(db, hd)
    b["moc_han"] = MOC_HAN
    return b


@router.post("/hop-dong/{hid}/lich-thanh-toan")
def dat_lich(hid: int, data: LichIn, u: User = Depends(require_roles(*SOAN, "ketoan")),
             db: Session = Depends(get_db)):
    from app.services import lich_thanh_toan as LTT
    hd = _hd(db, hid)
    GML.kiem_phien_ban(hd, data.phien_ban, f"Hợp đồng {hd.so_hop_dong}",
                       lambda: {**_hd_ra(hd), "lich": LTT.bang(db, hd)})
    try:
        kq = LTT.dat_lich(db, u, hd, [d.model_dump() for d in data.dot])
    except ValueError as e:
        raise HTTPException(422, str(e))
    GML.tang_phien_ban(hd); db.commit()
    return kq


@router.post("/hop-dong/lich-thanh-toan/{did}/doi-han")
def doi_han(did: int, data: DoiHanIn, u: User = Depends(require_roles(*SOAN, "ketoan")),
            db: Session = Depends(get_db)):
    from app.services import lich_thanh_toan as LTT
    d = db.get(LichThanhToanHD, did)
    if d is None: raise HTTPException(404, "Không có đợt thanh toán")
    try:
        return LTT.doi_han(db, u, d, data.han, data.ly_do)
    except ValueError as e:
        raise HTTPException(422, str(e))


# ── TR-1d · link thanh toán tour đoàn riêng (Chủ tịch duyệt 02/11/2026) ─────────────────────────────────────────
class LinkTTIn(BaseModel):
    lich_id: int
    email: str = ""
    dien_thoai: str = ""
    gui_email: bool = True


class HuyLinkIn(BaseModel):
    ly_do: str


def _ttd(f, *a, **k):
    from app.services import thanh_toan_doan as TTD
    try:
        return f(*a, **k)
    except TTD.LoiTTD as e:
        raise HTTPException(e.status, str(e))


@router.get("/hop-dong/{hid}/link-thanh-toan")
def ds_link_tt(hid: int, u: User = Depends(require_roles(*XEM_HD)), db: Session = Depends(get_db)):
    from app.services import thanh_toan_doan as TTD
    _hd(db, hid)
    return TTD.ds_theo_hop_dong(db, hid)


@router.post("/link-thanh-toan")
def tao_link_tt(data: LinkTTIn, u: User = Depends(require_roles("sales_admin", mo_ta="tạo link thanh toán tour đoàn")),
                db: Session = Depends(get_db)):
    from app.services import thanh_toan_doan as TTD
    return _ttd(TTD.tao, db, u, data.lich_id, data.email, data.dien_thoai, data.gui_email)


@router.post("/link-thanh-toan/{ma}/huy")
def huy_link_tt(ma: str, data: HuyLinkIn, u: User = Depends(require_roles("sales_admin", mo_ta="hủy link thanh toán tour đoàn")),
                db: Session = Depends(get_db)):
    from app.services import thanh_toan_doan as TTD
    return _ttd(TTD.huy, db, u, ma, data.ly_do)


@router.post("/link-thanh-toan/{ma}/gui-lai")
def gui_lai_link_tt(ma: str, u: User = Depends(require_roles("sales_admin", mo_ta="gửi lại email link thanh toán tour đoàn")),
                    db: Session = Depends(get_db)):
    from app.services import thanh_toan_doan as TTD
    return _ttd(TTD.gui_lai, db, u, ma)


@router.get("/hop-dong-qua-han")
def hop_dong_qua_han(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Mọi đợt đã đến hạn mà chưa thu đủ – danh sách làm việc của người đòi công nợ."""
    from app.services import lich_thanh_toan as LTT
    ds = LTT.qua_han(db)
    return {"so_dot": len(ds), "tong_con_thieu": round(sum(x["con_thieu"] for x in ds), 2), "dong": ds}


@router.get("/hop-dong/{hid}/chuoi")
def chuoi(hid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Trọn đường của một khách: bảng giá → báo giá → bản đã gửi → hợp đồng → booking."""
    hd = db.get(HopDongKhach, hid)
    if hd is None: raise HTTPException(404, "Không có hợp đồng")
    return BH.chuoi_ban_hang(db, hd)


# ── R5-16 · Chính sách bán (Chủ tịch duyệt 14/11/2026) ─────────────────────────────────────────────
from app.services import chinh_sach_ban as CSB  # noqa: E402


@router.get("/chinh-sach")
def chinh_sach(mang: str = "kd_le", u: User = Depends(require_roles(*CSB.VAI_XEM, mo_ta="chính sách bán")),
               db: Session = Depends(get_db)):
    """Bản đang hiệu lực + các bản cũ + hai chính sách đã có (D06, VTD Rewards) đọc thẳng."""
    return CSB.tong_hop(db, u, mang)


@router.post("/chinh-sach")
def ban_hanh_chinh_sach(d: dict, mang: str = "kd_le",
                        u: User = Depends(require_roles(*CSB.VAI_BAN_HANH, mo_ta="ban hành chính sách bán")),
                        db: Session = Depends(get_db)):
    return CSB.ban_hanh(db, u, d, mang)
