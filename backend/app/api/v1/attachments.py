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
from app.models.attachments import Attachment, DOI_TUONG_DAY_DU, LOAI_TEP, NHOM_HO_SO
from app.models.attachments import NHOM_NHAY_CAM
from app.services import attachments as AT, rules as R
from app.services.storage import StorageError, storage

router = APIRouter(prefix="/api/v1/tep", tags=["tep-dinh-kem"])

# Đính kèm chứng từ là việc của gần như mọi vai trò – chỗ chặn nằm ở chỗ khác: xem được hồ sơ nào thì
# gắn được tệp vào hồ sơ đó. Riêng THU HỒI hẹp hơn: gỡ chứng từ khỏi hồ sơ không phải việc ai cũng làm.
# "robot_ks" thêm 09/9/2026. Chủ tịch chốt vai trò này là "đọc toàn bộ như BKS, chỉ đọc", và danh sách
# màn hình của nó đã đúng thế – 46 màn hình, y hệt BKS, trong đó có /tep. Nhưng danh sách vai trò ở đây
# thì quên, nên mọi lần đọc tệp trả 403: robot đứng trước đúng màn hình nó phải kiểm và không thấy một
# chứng từ nào. Hàng rào hai lớp là để lớp ngoài rộng, lớp trong hẹp – không phải để hai lớp nói hai điều
# khác nhau về cùng một vai trò.
#
# CỐ Ý KHÔNG thêm vào VAI_TRO_NHAY_CAM (hồ sơ nhóm 06_Nhan_su). BKS là người, có tên, ký vào biên bản
# kiểm tra; một tác vụ máy đọc hồ sơ nhân sự là việc khác về bản chất, và Nghị định 13/2023 nói về dữ
# liệu cá nhân chứ không nói về mức tin cậy của người đọc. Chủ tịch mở thêm được – nhưng phải là một
# câu nói ra, không phải một hệ quả kèm theo của câu "đọc toàn bộ như BKS".
READ = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns",
        "gd_doi_xe", "tp_hd", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "nv_visa", "hanh_chinh",
        "robot_ks")
WRITE = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "ketoan", "cntt", "hcns",
         "gd_doi_xe", "tp_hd", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt", "nv_visa", "hanh_chinh")
GO = ("chutich", "tgd", "cntt", "ketoan", "hcns", "tp_dh", "gd_doi_xe")


@router.get("/cau-hinh")
def cau_hinh(u: User = Depends(require_roles(*READ))):
    """Đối tượng nào gắn được tệp, loại tệp nào nhận, nặng tối đa bao nhiêu.

    Đây cũng là thứ một tác vụ AI đọc trước khi gửi tệp lên – để nó biết giới hạn thay vì thử rồi lỗi."""
    kho = storage().describe()
    return {"doi_tuong": [{"ma": k, "ten": v[0], "phong_ban": v[1], "nhom_ho_so": v[2],
                          "luu_theo": "đối tượng" if v[3] else "tháng",
                          "nhay_cam": v[2] in NHOM_NHAY_CAM} for k, v in DOI_TUONG_DAY_DU.items()],
            "nhom_ho_so": [{"ma": k, "ten": v[0], "thoi_han_luu": v[1]} for k, v in NHOM_HO_SO.items()],
            "cau_truc_kho": "Pháp nhân / Năm / Nhóm hồ sơ / Tháng hoặc Mã đối tượng / Tệp "
                            "(Mô hình quản trị số hóa mục 7.2)",
            "loai": LOAI_TEP, "gioi_han_mb": AT.GIOI_HAN_MB,
            "duoi_nhan": sorted(AT.DUOI_CHO_PHEP), "duoi_tu_choi": sorted(AT.DUOI_CAM),
            "kho_luu": kho,
            "quy_tac": ["Cùng một tệp gắn vào cùng một bản ghi chỉ một lần – tải lại không tạo bản thứ hai.",
                        "Tên tệp gốc chỉ để hiển thị; chỗ lưu do hệ thống sinh từ mã băm nội dung.",
                        "Đọc ra luôn đối chiếu lại mã băm – lệch thì báo lỗi, không trả nội dung sai.",
                        "Gỡ tệp là THU HỒI có ghi lý do, không xóa cứng.",
                        "Hồ sơ nhóm 06_Nhan_su là dữ liệu cá nhân: phân quyền riêng theo Nghị định "
                        "13/2023 – chỉ HCNS, Ban TGĐ, Chủ tịch và Ban Kiểm soát đọc được."]}


@router.get("")
def danh_sach(doi_tuong: str = "", doi_tuong_id: str = "", phong_ban: str = "", nhom_ho_so: str = "",
              phap_nhan: str = "", ke_ca_thu_hoi: bool = False,
              u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Danh sách LỌC theo quyền: hồ sơ nhân sự chỉ hiện với vai trò được đọc dữ liệu cá nhân."""
    return AT.danh_sach(db, doi_tuong, doi_tuong_id, phong_ban, ke_ca_thu_hoi, vai_tro=u.role,
                        nhom_ho_so=nhom_ho_so, phap_nhan=phap_nhan)


@router.post("", status_code=201)
async def tai_len(doi_tuong: str = Form(...), doi_tuong_id: str = Form(...), tep: UploadFile = File(...),
                  loai: str = Form("chung_tu"), mo_ta: str = Form(""), nguon: str = Form("nguoi_nhap"),
                  tac_nhan: str = Form(""), phap_nhan: str = Form(""), nam: int = Form(0),
                  ky: str = Form(""), u: User = Depends(require_roles(*WRITE)),
                  db: Session = Depends(get_db)):
    if doi_tuong in DOI_TUONG_DAY_DU and DOI_TUONG_DAY_DU[doi_tuong][2] in NHOM_NHAY_CAM \
            and u.role not in AT.VAI_TRO_NHAY_CAM:
        raise HTTPException(403, "Hồ sơ nhân sự là dữ liệu cá nhân – chỉ HCNS, Ban TGĐ, Chủ tịch và Ban "
                                 "Kiểm soát gắn và đọc được (Nghị định 13/2023).")
    data = await tep.read()
    try:
        a, moi = AT.dinh_kem(db, doi_tuong, doi_tuong_id, tep.filename or "tep", data,
                             tep.content_type or "", loai, mo_ta, u.username, nguon, tac_nhan,
                             phap_nhan, nam, ky)
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
    if not AT.duoc_doc(a, u.role):
        raise HTTPException(403, "Tệp thuộc hồ sơ nhân sự – dữ liệu cá nhân, phân quyền riêng theo "
                                 "Nghị định 13/2023.")
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
