"""V2 – màn hình đọc chứng từ ảnh ra số (cửa 3 của khuôn ba cửa).

Bốn đường: tải ảnh cho máy đọc, xem hàng chờ, xác nhận (ghi vào bảng đích qua cửa 1), bỏ.

KHÔNG có đường nào ghi thẳng vào bảng đích. Nếu sau này ai thêm một endpoint làm việc đó thì phép thử
test_doc_chung_tu.py::test_khong_co_duong_nao_ghi_thang sẽ đỏ – nó đếm số lần phân hệ này gọi hàm ghi.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import require_roles, current_user
from app.db.session import get_db
from app.models.core import User
from app.models.doc_chung_tu import BanDocChungTu
from app.services import doc_chung_tu as DCT

router = APIRouter(prefix="/api/v1/doc-chung-tu", tags=["doc-chung-tu"])

# Ai được MỞ màn hình. Ai được XÁC NHẬN thì hẹp hơn và do bộ nạp quyết (duoc_xac_nhan_anh), không do
# danh sách này – nên CNTT có tên ở đây (vận hành mô hình, xem hàng chờ) mà vẫn không bấm xác nhận được.
XEM = ("chutich", "tgd", "ketoan", "tp_dh", "nv_dh", "gd_doi_xe", "cntt", "bks", "ptgd_doan")


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return DCT.meta()


@router.post("/doc", status_code=201)
async def doc(loai: str = Form(...), tep: UploadFile = File(...), doi_tuong_id: str = Form(""),
              phap_nhan: str = Form(""), ky: str = Form(""),
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    data = await tep.read()
    try:
        b = DCT.doc(db, loai, tep.filename or "anh", data, tep.content_type or "", u.username,
                    u.role, doi_tuong_id=doi_tuong_id, phap_nhan=phap_nhan, ky=ky)
    except DCT.KhongDocDuoc as ex:
        raise HTTPException(400, str(ex))
    except ValueError as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return {**DCT.ra(b),
            "message": ("Máy đã đọc xong. Số này là NHÁP – nó chưa nằm ở bất kỳ báo cáo nào và chỉ "
                        "vào hệ thống khi bạn kiểm lại rồi bấm xác nhận.")}


@router.get("")
def danh_sach(loai: str = "", cua_toi: bool = False,
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    ds = DCT.hang_cho(db, loai, u.username if cua_toi else "")
    return {"rows": [DCT.ra(b) for b in ds], "so_dong": len(ds)}


@router.get("/chat-luong")
def chat_luong(loai: str = "", ngay: int = 30,
               u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return DCT.ty_le_sua(db, loai, ngay)


@router.get("/{bid}")
def mot(bid: int, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    b = db.get(BanDocChungTu, bid)
    if b is None: raise HTTPException(404, "Không có bản đọc này")
    return DCT.ra(b)


class XacNhan(BaseModel):
    so: dict


@router.post("/{bid}/xac-nhan")
def xac_nhan(bid: int, body: XacNhan, u: User = Depends(current_user),
             db: Session = Depends(get_db)):
    b = db.get(BanDocChungTu, bid)
    if b is None: raise HTTPException(404, "Không có bản đọc này")
    try:
        kq = DCT.xac_nhan(db, b, body.so, u.username, u.role)
    except DCT.KhongDocDuoc as ex:
        raise HTTPException(403 if "không được xác nhận" in str(ex) else 400, str(ex))
    if not kq.get("da_ghi"):
        db.rollback()
        raise HTTPException(400, kq.get("message") or "Chưa ghi được")
    db.commit()
    return kq


class Bo(BaseModel):
    ly_do: str


@router.post("/{bid}/bo")
def bo(bid: int, body: Bo, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    b = db.get(BanDocChungTu, bid)
    if b is None: raise HTTPException(404, "Không có bản đọc này")
    try:
        DCT.bo(db, b, body.ly_do, u.username)
    except DCT.KhongDocDuoc as ex:
        raise HTTPException(400, str(ex))
    db.commit()
    return DCT.ra(b)
