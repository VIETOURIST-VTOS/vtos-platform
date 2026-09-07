"""Tệp & hình ảnh đính kèm – một cửa cho mọi phòng ban.

Cùng triết lý với bộ nạp dữ liệu: một đường vào, một bộ quy tắc, một nhật ký. Nếu mỗi phân hệ tự làm một
kiểu tải ảnh thì quy tắc chặt nhất thành vô nghĩa – người ta đi đường lỏng nhất."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.attachments import Attachment, DOI_TUONG, LOAI_TEP
from app.services import attachments as AT, rules as R
from app.services.storage import StorageError, storage

router = APIRouter(prefix="/api/v1/tep", tags=["tep-dinh-kem"])

# Đính kèm chứng từ là việc của gần như mọi vai trò – chỗ chặn nằm ở chỗ khác: xem được hồ sơ nào thì
# gắn được tệp vào hồ sơ đó. Riêng THU HỒI hẹp hơn: gỡ chứng từ khỏi hồ sơ không phải việc ai cũng làm.
READ = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns",
        "gd_doi_xe", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "nv_visa", "hanh_chinh")
WRITE = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "ketoan", "cntt", "hcns",
         "gd_doi_xe", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "nv_visa", "hanh_chinh")
GO = ("chutich", "tgd", "cntt", "ketoan", "hcns", "tp_dh", "gd_doi_xe")


@router.get("/cau-hinh")
def cau_hinh(u: User = Depends(require_roles(*READ))):
    """Đối tượng nào gắn được tệp, loại tệp nào nhận, nặng tối đa bao nhiêu.

    Đây cũng là thứ một tác vụ AI đọc trước khi gửi tệp lên – để nó biết giới hạn thay vì thử rồi lỗi."""
    kho = storage().describe()
    return {"doi_tuong": [{"ma": k, "ten": v[0], "phong_ban": v[1]} for k, v in DOI_TUONG.items()],
            "loai": LOAI_TEP, "gioi_han_mb": AT.GIOI_HAN_MB,
            "duoi_nhan": sorted(AT.DUOI_CHO_PHEP), "duoi_tu_choi": sorted(AT.DUOI_CAM),
            "kho_luu": kho,
            "quy_tac": ["Cùng một tệp gắn vào cùng một bản ghi chỉ một lần – tải lại không tạo bản thứ hai.",
                        "Tên tệp gốc chỉ để hiển thị; chỗ lưu do hệ thống sinh từ mã băm nội dung.",
                        "Đọc ra luôn đối chiếu lại mã băm – lệch thì báo lỗi, không trả nội dung sai.",
                        "Gỡ tệp là THU HỒI có ghi lý do, không xóa cứng."]}


@router.get("")
def danh_sach(doi_tuong: str = "", doi_tuong_id: str = "", phong_ban: str = "",
              ke_ca_thu_hoi: bool = False, u: User = Depends(require_roles(*READ)),
              db: Session = Depends(get_db)):
    return AT.danh_sach(db, doi_tuong, doi_tuong_id, phong_ban, ke_ca_thu_hoi)


@router.post("", status_code=201)
async def tai_len(doi_tuong: str = Form(...), doi_tuong_id: str = Form(...), tep: UploadFile = File(...),
                  loai: str = Form("chung_tu"), mo_ta: str = Form(""), nguon: str = Form("nguoi_nhap"),
                  tac_nhan: str = Form(""), u: User = Depends(require_roles(*WRITE)),
                  db: Session = Depends(get_db)):
    data = await tep.read()
    try:
        a, moi = AT.dinh_kem(db, doi_tuong, doi_tuong_id, tep.filename or "tep", data,
                             tep.content_type or "", loai, mo_ta, u.username, nguon, tac_nhan)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    if moi:
        R.audit(db, u.username, u.role, "dinh_kem_tep", f"{doi_tuong}:{doi_tuong_id}",
                after={"ten_tep": a.ten_tep, "hash": a.checksum[:12], "kich_thuoc": a.kich_thuoc})
    db.commit()
    return {**AT.ra(a), "moi": moi,
            "message": "Đã lưu tệp" if moi else "Tệp này đã có trong hồ sơ – không tạo bản thứ hai"}


@router.get("/{aid}/tai")
def tai_ve(aid: int, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    a = db.get(Attachment, aid)
    if a is None: raise HTTPException(404, "Không có tệp này")
    try:
        data = AT.doc(db, a)
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{a.id}-{a.ten_tep}"'})


class GoIn(BaseModel):
    ly_do: str


@router.post("/{aid}/thu-hoi")
def go(aid: int, data: GoIn, u: User = Depends(require_roles(*GO)), db: Session = Depends(get_db)):
    a = db.get(Attachment, aid)
    if a is None: raise HTTPException(404, "Không có tệp này")
    try:
        AT.thu_hoi(db, a, u.username, data.ly_do)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "thu_hoi_tep", f"{a.doi_tuong}:{a.doi_tuong_id}",
            after={"tep_id": a.id, "ly_do": a.ly_do_thu_hoi})
    db.commit()
    return {**AT.ra(a), "message": "Đã thu hồi tệp khỏi hồ sơ. Bản ghi vẫn còn để đối chiếu."}
