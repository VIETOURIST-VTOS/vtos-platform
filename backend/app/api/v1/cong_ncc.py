"""NCC-1 · Cổng Nhà cung cấp — hai nhóm cửa:

  /api/v1/cong/ncc/*   — phía NGOÀI: phiên cổng của tài khoản NCC đã duyệt VÀ đã nối vào danh mục NCC.
  /api/v1/cong-ncc/*   — phía VTOS: nối tài khoản, duyệt đề xuất giá, lập bản kê, trả lời đề nghị, học liệu.
"""
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.api.v1.cong_ngoai import tai_khoan_ngoai
from app.db.session import get_db
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.suppliers import Supplier
from app.services import cong_ncc as S

router = APIRouter(prefix="/api/v1/cong/ncc", tags=["cong-ncc"])
router_vtos = APIRouter(prefix="/api/v1/cong-ncc", tags=["cong-ncc"])


def _goi(f, *a, **k):
    try:
        return f(*a, **k)
    except S.LoiNcc as ex:
        raise HTTPException(ex.status, str(ex))


def _ncc(tk: TaiKhoanNgoai = Depends(tai_khoan_ngoai), db: Session = Depends(get_db)) -> tuple[TaiKhoanNgoai, Supplier]:
    return tk, _goi(S.ncc_cua, db, tk)


def _tep(data: bytes, a) -> Response:
    return Response(content=data, media_type=a.kieu_noi_dung or "application/octet-stream",
                    headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(a.ten_tep or 'tep')}",
                             "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


# ---------------------------------------------------------------- phía NCC
@router.get("/ban-lam-viec")
def ban_lam_viec(x=Depends(_ncc), db: Session = Depends(get_db)):
    return S.ban_lam_viec(db, x[1])


@router.get("/don")
def don(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"don": S.ds_don(db, x[1])}


@router.get("/don/{did}")
def mot_don(did: int, x=Depends(_ncc), db: Session = Depends(get_db)):
    return _goi(S.mot_don, db, x[1], did)


@router.post("/don/{did}")
async def phan_hoi_don(did: int, hanh_dong: str = Form(...), ma: str = Form(""), ghi_chu: str = Form(""),
                       tep: UploadFile | None = File(None), x=Depends(_ncc), db: Session = Depends(get_db)):
    data = await tep.read() if tep is not None else None
    r = _goi(S.phan_hoi_don, db, x[0], x[1], did, hanh_dong, ma, ghi_chu,
             (tep.filename if tep else "") or "", (tep.content_type if tep else "") or "", data)
    db.commit()
    return {"message": {"xac_nhan": "Đã xác nhận đơn", "tu_choi": "Đã gửi lời từ chối — Điều hành xử lý",
                        "chung_tu": "Đã gửi chứng từ"}[hanh_dong], "don": r}


@router.get("/gia")
def gia(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"gia": S.gia_dang_ap_dung(db, x[1]), "thuc_don": S.thuc_don_cua(db, x[1]),
            "nha_hang": [{"id": n.id, "ten": n.ten} for n in S._nha_hang_cua(db, x[1])],
            "de_xuat": S.ds_de_xuat_cua(db, x[1]), "loai_ncc": x[1].loai}


class DeXuatIn(BaseModel):
    loai: str = "gia"
    gia_ncc_id: int | None = None
    thuc_don_id: int | None = None
    nha_hang_id: int | None = None
    dich_vu: str = ""
    don_vi: str = ""
    gia: float = 0
    gia_tre_em: float | None = None
    so_luong_mo: int | None = None
    tu_ngay: date | None = None
    den_ngay: date | None = None
    ngay_khong_phuc_vu: str = ""
    ghi_chu: str = ""


@router.post("/de-xuat")
def gui_de_xuat(data: DeXuatIn, x=Depends(_ncc), db: Session = Depends(get_db)):
    _goi(S.de_xuat, db, x[0], x[1], data.model_dump())
    db.commit()
    return {"message": "Đã gửi đề xuất — Điều hành duyệt mới áp dụng", **gia(x, db)}


@router.get("/cong-no")
def cong_no(x=Depends(_ncc), db: Session = Depends(get_db)):
    return S.cong_no(db, x[1])


@router.get("/ban-ke")
def ban_ke(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"ban_ke": S.ds_ban_ke_cua(db, x[1])}


class ChenhIn(BaseModel):
    dong_id: int
    gia_tri: float | None = None
    ghi_chu: str = ""


@router.post("/ban-ke/{bid}/xac-nhan")
def xac_nhan_bk(bid: int, x=Depends(_ncc), db: Session = Depends(get_db)):
    _goi(S.xac_nhan_ban_ke, db, x[0], x[1], bid)
    db.commit()
    return {"message": "Đã xác nhận bản kê — bản kê đã khóa", "ban_ke": S.ds_ban_ke_cua(db, x[1])}


@router.post("/ban-ke/{bid}/chenh-lech")
def chenh_lech(bid: int, data: ChenhIn, x=Depends(_ncc), db: Session = Depends(get_db)):
    _goi(S.bao_chenh_lech, db, x[0], x[1], bid, data.dong_id, data.gia_tri, data.ghi_chu)
    db.commit()
    return {"message": "Đã gửi chênh lệch — Kế toán trả lời", "ban_ke": S.ds_ban_ke_cua(db, x[1])}


@router.get("/de-nghi")
def de_nghi(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"de_nghi": S.ds_de_nghi_cua(db, x[1]), "loai": S.LOAI_DE_NGHI}


@router.post("/de-nghi")
async def gui_de_nghi(loai: str = Form(...), noi_dung: str = Form(...), so_tien: str = Form(""),
                      tep: UploadFile | None = File(None), x=Depends(_ncc), db: Session = Depends(get_db)):
    data = await tep.read() if tep is not None else None
    dn = _goi(S.gui_de_nghi, db, x[0], x[1], loai, so_tien or None, noi_dung,
              (tep.filename if tep else "") or "", (tep.content_type if tep else "") or "", data)
    db.commit()
    return {"message": f"Đã gửi {dn.ma}", "de_nghi": S.ds_de_nghi_cua(db, x[1])}


@router.get("/ho-so")
def ho_so(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"ncc": S._ho_so(x[1]), "tep": S.ho_so_tep(db, x[1]), "ngan_hang": S.ngan_hang(db, x[1]),
            "thanh_vien": S.thanh_vien(db, x[1])}


@router.post("/ho-so")
async def gui_ho_so(mo_ta: str = Form(""), tep: UploadFile = File(...), x=Depends(_ncc), db: Session = Depends(get_db)):
    _goi(S.gui_ho_so, db, x[0], x[1], tep.filename or "", tep.content_type or "", await tep.read(), mo_ta)
    db.commit()
    return {"message": "Đã gửi hồ sơ", **ho_so(x, db)}


@router.post("/doi-tai-khoan")
async def doi_tk(so_tk: str = Form(...), ngan_hang: str = Form(""), chu_tk: str = Form(""), ly_do: str = Form(""),
                 tep: UploadFile | None = File(None), x=Depends(_ncc), db: Session = Depends(get_db)):
    data = await tep.read() if tep is not None else None
    _goi(S.doi_tai_khoan, db, x[0], x[1], so_tk, ngan_hang, chu_tk, ly_do,
         (tep.filename if tep else "") or "", (tep.content_type if tep else "") or "", data)
    db.commit()
    return {"message": "Đã gửi đề nghị đổi tài khoản — chờ Kế toán và người thứ hai xác nhận; chưa dùng để chi",
            **ho_so(x, db)}


@router.get("/hoc-lieu")
def hoc_lieu(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"hoc_lieu": S.hoc_lieu_cho(db, "ncc")}


@router.get("/hoc-lieu/{hid}/tep")
def hoc_lieu_tep(hid: int, x=Depends(_ncc), db: Session = Depends(get_db)):
    data, a = _goi(S.tep_hoc_lieu, db, hid, "ncc")
    return _tep(data, a)


@router.get("/dat-ban")
def dat_ban(x=Depends(_ncc), db: Session = Depends(get_db)):
    return {"dat_ban": S.don_dat_ban(db, x[1])}


class DatBanIn(BaseModel):
    nhan: bool
    ghi_chu: str = ""


@router.post("/dat-ban/{yid}")
def xu_ly_dat_ban(yid: int, data: DatBanIn, x=Depends(_ncc), db: Session = Depends(get_db)):
    _goi(S.xu_ly_dat_ban, db, x[0], x[1], yid, data.nhan, data.ghi_chu)
    db.commit()
    return {"message": "Đã nhận bàn" if data.nhan else "Đã từ chối — Vietourist báo khách", "dat_ban": S.don_dat_ban(db, x[1])}


# DT-2 · sau bữa ăn: nhà hàng báo khách đã dùng (bill thực tế, số thu tại bàn, ảnh bill) hoặc khách không đến.
def _goi_db(f, *a, **k):
    from app.services import dat_ban as DB
    try:
        return f(*a, **k)
    except DB.LoiDatBan as ex:
        raise HTTPException(ex.status, str(ex))


@router.post("/dat-ban/{yid}/da-dung")
async def dat_ban_da_dung(yid: int, bill: int = Form(...), thu_tai_ban: int = Form(...), ghi_chu: str = Form(""),
                          tep: UploadFile | None = File(None), x=Depends(_ncc), db: Session = Depends(get_db)):
    from app.services import dat_ban as DB
    data = await tep.read() if tep else None
    _goi_db(DB.ncc_da_dung, db, x[0], x[1], yid, bill, thu_tai_ban, ghi_chu,
            (tep.filename or "") if tep else "", (tep.content_type or "") if tep else "", data)
    db.commit()
    return {"message": "Đã báo khách đã dùng", "dat_ban": S.don_dat_ban(db, x[1])}


class ThayDoiNhIn(BaseModel):
    nhan: bool
    ghi_chu: str = ""


@router.post("/dat-ban/{yid}/thay-doi")
def dat_ban_thay_doi(yid: int, data: ThayDoiNhIn, x=Depends(_ncc), db: Session = Depends(get_db)):
    from app.services import dat_ban as DB
    _goi_db(DB.ncc_thay_doi, db, x[0], x[1], yid, data.nhan, data.ghi_chu)
    db.commit()
    return {"message": "Đã nhận thay đổi" if data.nhan else "Đã từ chối thay đổi — khách giữ lịch cũ", "dat_ban": S.don_dat_ban(db, x[1])}


class TraLoiIn(BaseModel):
    noi_dung: str = ""


@router.get("/danh-gia")
def danh_gia(x=Depends(_ncc), db: Session = Depends(get_db)):
    """AT-3: đánh giá đang hiện về các nhà hàng của NCC này (tên khách đã che)."""
    from app.services import danh_gia_nh as DG
    return DG.ds_ncc(db, x[1])


@router.post("/danh-gia/{gid}/tra-loi")
def tra_loi_danh_gia(gid: int, data: TraLoiIn, x=Depends(_ncc), db: Session = Depends(get_db)):
    from app.services import danh_gia_nh as DG
    try:
        DG.tra_loi(db, x[0], x[1], gid, data.noi_dung)
    except DG.LoiDanhGia as ex:
        raise HTTPException(ex.status, str(ex))
    return {"message": "Đã đăng trả lời", **DG.ds_ncc(db, x[1])}


@router.post("/dat-ban/{yid}/khong-den")
def dat_ban_khong_den(yid: int, x=Depends(_ncc), db: Session = Depends(get_db)):
    from app.services import dat_ban as DB
    _goi_db(DB.ncc_khong_den, db, x[0], x[1], yid)
    db.commit()
    return {"message": "Đã báo khách không đến — Vietourist xử lý tiền theo chính sách", "dat_ban": S.don_dat_ban(db, x[1])}


# ---------------------------------------------------------------- phía VTOS
@router_vtos.get("")
def vt_tong(u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {"tai_khoan": S.ds_tai_khoan(db), "de_xuat": S.ds_de_xuat_cho(db), "ban_ke": S.ds_ban_ke(db),
            "de_nghi": S.ds_de_nghi(db), "hoc_lieu": S.ds_hoc_lieu(db), "tu_choi": S.don_bi_tu_choi(db),
            "nha_hang": [{"id": n.id, "ma": n.ma, "ten": n.ten, "supplier_id": n.supplier_id}
                         for n in db.query(S.NhaHang).order_by(S.NhaHang.ten).all()],
            "quyen": {"noi": u.role in S.VAI_NOI, "duyet_gia": u.role in S.VAI_DUYET_GIA, "ke_toan": u.role in S.VAI_KE_TOAN,
                      "dieu_hanh": u.role in S.VAI_DIEU_HANH, "hoc_lieu": u.role in S.VAI_HOC_LIEU},
            "loai_de_nghi": S.LOAI_DE_NGHI, "nhom_hoc_lieu": S.NHOM_HOC_LIEU, "danh_cho": S.DANH_CHO}


@router_vtos.get("/tim-ncc")
def vt_tim(q: str = "", u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    return {"ncc": S.tim_ncc(db, q)}


class NoiIn(BaseModel):
    ncc_id: int | None = None


@router_vtos.post("/noi/{tk_id}")
def vt_noi(tk_id: int, data: NoiIn, u: User = Depends(require_roles(*S.VAI_NOI)), db: Session = Depends(get_db)):
    _goi(S.noi, db, u, tk_id, data.ncc_id)
    db.commit()
    return {"message": "Đã nối" if data.ncc_id else "Đã gỡ nối", **vt_tong(u, db)}


@router_vtos.post("/nha-hang/{nid}")
def vt_gan_nh(nid: int, data: NoiIn, u: User = Depends(require_roles(*S.VAI_NOI)), db: Session = Depends(get_db)):
    _goi(S.gan_nha_hang, db, u, nid, data.ncc_id)
    db.commit()
    return {"message": "Đã gắn nhà hàng với NCC", **vt_tong(u, db)}


class XuLyIn(BaseModel):
    duyet: bool = True
    ly_do: str = ""


@router_vtos.post("/de-xuat/{xid}")
def vt_de_xuat(xid: int, data: XuLyIn, u: User = Depends(require_roles(*S.VAI_DUYET_GIA)), db: Session = Depends(get_db)):
    x = _goi(S.xu_ly_de_xuat, db, u, xid, data.duyet, data.ly_do)
    db.commit()
    return {"message": "Đã duyệt — giá áp dụng" if x.trang_thai == "duyet" else "Đã từ chối", **vt_tong(u, db)}


@router_vtos.post("/tu-choi/{pid}")
def vt_tu_choi(pid: int, u: User = Depends(require_roles(*S.VAI_DIEU_HANH)), db: Session = Depends(get_db)):
    _goi(S.xu_ly_tu_choi, db, u, pid)
    db.commit()
    return {"message": "Đã đánh dấu đã xử lý", **vt_tong(u, db)}


class BanKeIn(BaseModel):
    ncc_id: int
    ky: str


@router_vtos.post("/ban-ke")
def vt_lap_bk(data: BanKeIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    b = _goi(S.lap_ban_ke, db, u, data.ncc_id, data.ky)
    db.commit()
    return {"message": f"Đã lập {b.ma} — đã gửi NCC", **vt_tong(u, db)}


class TraLoiIn(BaseModel):
    tra_loi: str = ""
    trang_thai: str = "xong"


@router_vtos.post("/ban-ke/dong/{dong_id}")
def vt_tra_loi_bk(dong_id: int, data: TraLoiIn, u: User = Depends(require_roles(*S.VAI_KE_TOAN)), db: Session = Depends(get_db)):
    _goi(S.tra_loi_chenh_lech, db, u, dong_id, data.tra_loi)
    db.commit()
    return {"message": "Đã trả lời", **vt_tong(u, db)}


@router_vtos.post("/de-nghi/{did}")
def vt_de_nghi(did: int, data: TraLoiIn, u: User = Depends(require_roles(*(S.VAI_KE_TOAN + S.VAI_DIEU_HANH))),
               db: Session = Depends(get_db)):
    _goi(S.xu_ly_de_nghi, db, u, did, data.trang_thai, data.tra_loi)
    db.commit()
    return {"message": "Đã trả lời đề nghị", **vt_tong(u, db)}


@router_vtos.post("/hoc-lieu")
async def vt_hoc_lieu(tieu_de: str = Form(...), nhom: str = Form(...), danh_cho: str = Form(...), tep: UploadFile = File(...),
                      u: User = Depends(require_roles(*S.VAI_HOC_LIEU)), db: Session = Depends(get_db)):
    _goi(S.dang_hoc_lieu, db, u, tieu_de, nhom, [x.strip() for x in danh_cho.split(",")], tep.filename or "",
         tep.content_type or "", await tep.read())
    db.commit()
    return {"message": "Đã đưa học liệu lên", **vt_tong(u, db)}


@router_vtos.post("/hoc-lieu/{hid}/go")
def vt_go_hl(hid: int, u: User = Depends(require_roles(*S.VAI_HOC_LIEU)), db: Session = Depends(get_db)):
    _goi(S.go_hoc_lieu, db, u, hid)
    db.commit()
    return {"message": "Đã gỡ học liệu", **vt_tong(u, db)}


@router_vtos.get("/hoc-lieu/{hid}/tep")
def vt_hl_tep(hid: int, u: User = Depends(require_roles(*S.VAI_XEM)), db: Session = Depends(get_db)):
    data, a = _goi(S.tep_hoc_lieu, db, hid, None)
    return _tep(data, a)
