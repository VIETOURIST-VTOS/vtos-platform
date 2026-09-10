"""API Hồ sơ kiểm toán – V7 Đợt 3.

Đây là hồ sơ GIAO CHO KIỂM TOÁN VIÊN, khác hẳn nhật ký nghiệp vụ `/api/v1/audit`. Xem ghi chú đầu
app/models/kiem_toan.py.

Không có endpoint nào nhận số tiền điều chỉnh: điều chỉnh sau soát xét là bút toán thật ở sổ, bảng này
chỉ giữ số hiệu.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User, Company
from app.models.accounting import JournalEntry
from app.models.attachments import NHOM_HO_SO
from app.models.kiem_toan import (HoSoKiemToan, HoSoKiemToanMuc, HoSoKiemToanDieuChinh, KT_LOAI,
                                  KT_TRANG_THAI, KT_CHUYEN, KT_Y_KIEN, MUC_TRANG_THAI, DC_TRANG_THAI)
from app.services import kiem_toan as KT

router = APIRouter(prefix="/api/v1", tags=["kiem-toan"])

# XEM: Ban lãnh đạo, Kế toán, Ban Kiểm soát (nghĩa vụ Luật Doanh nghiệp), CNTT. Cộng các phòng CÓ MỤC
# phải nộp – không mở được hồ sơ thì họ không biết mình đang nợ tài liệu gì, và Kế toán lại phải đi
# nhắc từng người bằng tin nhắn.
XEM = ("chutich", "tgd", "bks", "robot_ks", "ketoan", "cntt", "hcns", "tp_dh", "ptgd_doan",
       "gd_doi_xe", "hanh_chinh")


def _hs_out(db: Session, hs: HoSoKiemToan, kem_muc: bool = False) -> dict:
    ct = db.get(Company, hs.company_id) if hs.company_id else None
    d = {"id": hs.id, "code": hs.code, "company_id": hs.company_id,
         "company_name": ct.name if ct else "", "ky": hs.ky,
         "loai": hs.loai, "loai_ten": KT_LOAI.get(hs.loai, hs.loai),
         "don_vi_kiem_toan": hs.don_vi_kiem_toan, "so_hop_dong": hs.so_hop_dong,
         "nguoi_dau_moi": hs.nguoi_dau_moi, "ngay_bat_dau": hs.ngay_bat_dau,
         "han_hoan_thanh": hs.han_hoan_thanh,
         "trang_thai": hs.trang_thai, "trang_thai_ten": KT_TRANG_THAI.get(hs.trang_thai, hs.trang_thai),
         "loai_y_kien": hs.loai_y_kien, "loai_y_kien_ten": KT_Y_KIEN.get(hs.loai_y_kien, ""),
         "so_bao_cao": hs.so_bao_cao, "ngay_bao_cao": hs.ngay_bao_cao,
         "van_de_nhan_manh": hs.van_de_nhan_manh, "ghi_chu": hs.ghi_chu,
         "created_by": hs.created_by, "created_at": hs.created_at, "closed_at": hs.closed_at,
         "chuyen_duoc": list(KT_CHUYEN.get(hs.trang_thai, ())),
         **KT.chi_so(db, hs)}
    if kem_muc:
        d["muc"] = [_muc_out(db, m) for m in db.execute(
            select(HoSoKiemToanMuc).where(HoSoKiemToanMuc.ho_so_id == hs.id)
            .order_by(HoSoKiemToanMuc.stt)).scalars()]
        d["dieu_chinh"] = [_dc_out(db, x) for x in db.execute(
            select(HoSoKiemToanDieuChinh).where(HoSoKiemToanDieuChinh.ho_so_id == hs.id)
            .order_by(HoSoKiemToanDieuChinh.id)).scalars()]
    return d


def _muc_out(db: Session, m: HoSoKiemToanMuc) -> dict:
    return {"id": m.id, "ho_so_id": m.ho_so_id, "stt": m.stt, "ten": m.ten,
            "nhom_ho_so": m.nhom_ho_so, "nhom_ho_so_ten": (NHOM_HO_SO.get(m.nhom_ho_so) or ("", ""))[0],
            "phong_ban": m.phong_ban, "nguoi_phu_trach": m.nguoi_phu_trach, "han_nop": m.han_nop,
            "trang_thai": m.trang_thai, "trang_thai_ten": MUC_TRANG_THAI.get(m.trang_thai, m.trang_thai),
            "ngay_gui": m.ngay_gui, "cau_hoi": m.cau_hoi, "tra_loi": m.tra_loi, "ghi_chu": m.ghi_chu,
            # Đếm sống từ kho tệp chung, không lưu thành cột – gỡ một tệp là con số đổi theo ngay.
            "so_tep": KT.dem_tep(db, m.id),
            "tre_han": bool(m.han_nop and m.trang_thai in ("chua_gui", "hoi_them") and m.han_nop < date.today())}


def _dc_out(db: Session, dc: HoSoKiemToanDieuChinh) -> dict:
    je = db.get(JournalEntry, dc.journal_entry_id) if dc.journal_entry_id else None
    return {"id": dc.id, "ho_so_id": dc.ho_so_id, "noi_dung": dc.noi_dung,
            "journal_entry_id": dc.journal_entry_id,
            "journal_entry_ref": getattr(je, "source_ref", "") if je else "",
            "trang_thai": dc.trang_thai, "trang_thai_ten": DC_TRANG_THAI.get(dc.trang_thai, dc.trang_thai),
            "ly_do": dc.ly_do, "nguoi_quyet": dc.nguoi_quyet, "created_by": dc.created_by,
            "created_at": dc.created_at}


@router.get("/kiem-toan/meta")
def meta(u: User = Depends(require_roles(*XEM, mo_ta="hồ sơ kiểm toán"))):
    return {"loai": KT_LOAI, "trang_thai": KT_TRANG_THAI, "y_kien": KT_Y_KIEN,
            "muc_trang_thai": MUC_TRANG_THAI, "dc_trang_thai": DC_TRANG_THAI,
            "nhom_ho_so": {k: v[0] for k, v in NHOM_HO_SO.items()},
            "mau_danh_muc": [{"ten": t, "nhom_ho_so": n, "phong_ban": p} for t, n, p in KT.MAU_DANH_MUC]}


@router.get("/kiem-toan")
def danh_sach(trang_thai: str = "", ky: str = "",
              u: User = Depends(require_roles(*XEM, mo_ta="hồ sơ kiểm toán")),
              db: Session = Depends(get_db)):
    q = select(HoSoKiemToan).order_by(desc(HoSoKiemToan.id))
    if trang_thai: q = q.where(HoSoKiemToan.trang_thai == trang_thai)
    if ky: q = q.where(HoSoKiemToan.ky == ky.upper())
    return [_hs_out(db, hs) for hs in db.execute(q).scalars()]


@router.get("/kiem-toan/{hid}")
def chi_tiet(hid: int, u: User = Depends(require_roles(*XEM, mo_ta="hồ sơ kiểm toán")),
             db: Session = Depends(get_db)):
    hs = db.get(HoSoKiemToan, hid)
    if not hs: raise HTTPException(404, "Không có hồ sơ kiểm toán này")
    return _hs_out(db, hs, kem_muc=True)


class HoSoIn(BaseModel):
    ky: str
    loai: str = "soat_xet"
    company_id: int | None = None
    don_vi_kiem_toan: str
    so_hop_dong: str = ""
    nguoi_dau_moi: str = ""
    ngay_bat_dau: date | None = None
    han_hoan_thanh: date | None = None
    ghi_chu: str = ""
    dung_mau: bool = True


@router.post("/kiem-toan")
def tao(inp: HoSoIn, u: User = Depends(require_roles(*KT.GHI, mo_ta="lập hồ sơ kiểm toán")),
        db: Session = Depends(get_db)):
    d = inp.model_dump()
    mau = d.pop("dung_mau", True)
    try:
        hs = KT.tao(db, u, d, dung_mau=mau)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": f"Đã lập hồ sơ {hs.code}", "id": hs.id, "code": hs.code}


@router.post("/kiem-toan/{hid}/danh-muc-mau")
def nap_mau(hid: int, u: User = Depends(require_roles(*KT.GHI, mo_ta="danh mục hồ sơ kiểm toán")),
            db: Session = Depends(get_db)):
    hs = db.get(HoSoKiemToan, hid)
    if not hs: raise HTTPException(404, "Không có hồ sơ kiểm toán này")
    n = KT.them_muc_mau(db, hs)
    db.commit()
    return {"message": f"Đã bổ sung {n} mục từ danh mục mẫu" if n else "Danh mục mẫu đã có đủ trong hồ sơ"}


class MucIn(BaseModel):
    ten: str
    nhom_ho_so: str = "08_Kiem_toan"
    phong_ban: str = "ketoan"
    nguoi_phu_trach: str = ""
    han_nop: date | None = None
    ghi_chu: str = ""


@router.post("/kiem-toan/{hid}/muc")
def them_muc(hid: int, inp: MucIn, u: User = Depends(require_roles(*KT.GHI, mo_ta="danh mục hồ sơ kiểm toán")),
             db: Session = Depends(get_db)):
    hs = db.get(HoSoKiemToan, hid)
    if not hs: raise HTTPException(404, "Không có hồ sơ kiểm toán này")
    try:
        m = KT.them_muc(db, u, hs, inp.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": f"Đã thêm mục #{m.stt}", "id": m.id}


class MucSuaIn(BaseModel):
    trang_thai: str | None = None
    nguoi_phu_trach: str | None = None
    phong_ban: str | None = None
    han_nop: date | None = None
    ngay_gui: date | None = None
    cau_hoi: str | None = None
    tra_loi: str | None = None
    ghi_chu: str | None = None


@router.patch("/kiem-toan/muc/{mid}")
def sua_muc(mid: int, inp: MucSuaIn,
            u: User = Depends(require_roles(*KT.GHI_MUC, mo_ta="mục hồ sơ kiểm toán")),
            db: Session = Depends(get_db)):
    m = db.get(HoSoKiemToanMuc, mid)
    if not m: raise HTTPException(404, "Không có mục này")
    try:
        KT.sua_muc(db, u, m, inp.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã cập nhật mục"}


class DieuChinhIn(BaseModel):
    noi_dung: str


@router.post("/kiem-toan/{hid}/dieu-chinh")
def them_dieu_chinh(hid: int, inp: DieuChinhIn,
                    u: User = Depends(require_roles(*KT.GHI, mo_ta="điều chỉnh kiểm toán")),
                    db: Session = Depends(get_db)):
    hs = db.get(HoSoKiemToan, hid)
    if not hs: raise HTTPException(404, "Không có hồ sơ kiểm toán này")
    try:
        dc = KT.them_dieu_chinh(db, u, hs, inp.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã ghi nhận điều chỉnh kiểm toán đề nghị", "id": dc.id}


class QuyetIn(BaseModel):
    trang_thai: str
    journal_entry_id: int | None = None
    ly_do: str = ""


@router.post("/kiem-toan/dieu-chinh/{did}/quyet")
def quyet_dieu_chinh(did: int, inp: QuyetIn,
                     u: User = Depends(require_roles(*KT.GHI, mo_ta="điều chỉnh kiểm toán")),
                     db: Session = Depends(get_db)):
    dc = db.get(HoSoKiemToanDieuChinh, did)
    if not dc: raise HTTPException(404, "Không có điều chỉnh này")
    try:
        KT.quyet_dieu_chinh(db, u, dc, inp.model_dump())
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã ghi quyết định về điều chỉnh"}


class ChuyenIn(BaseModel):
    trang_thai: str
    loai_y_kien: str = ""
    so_bao_cao: str = ""
    ngay_bao_cao: date | None = None
    van_de_nhan_manh: str = ""


@router.post("/kiem-toan/{hid}/chuyen")
def chuyen(hid: int, inp: ChuyenIn, u: User = Depends(require_roles(*KT.GHI, mo_ta="hồ sơ kiểm toán")),
           db: Session = Depends(get_db)):
    hs = db.get(HoSoKiemToan, hid)
    if not hs: raise HTTPException(404, "Không có hồ sơ kiểm toán này")
    d = inp.model_dump()
    try:
        KT.chuyen_trang_thai(db, u, hs, d.pop("trang_thai"), d)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.commit()
    return {"message": "Đã chuyển trạng thái hồ sơ"}
