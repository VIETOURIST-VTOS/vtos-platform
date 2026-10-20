# -*- coding: utf-8 -*-
"""PC-1 · Trưởng phòng tự gửi yêu cầu Pháp chế (Chủ tịch duyệt bản xem thử 19/10/2026).

Trước hôm nay chỉ Pháp chế, TGĐ, Chủ tịch ghi được yêu cầu (`/api/v1/ir-phap-che`), nên một trưởng
phòng muốn hỏi Pháp chế thì Pháp chế ghi hộ. Cửa này mở cho `access.GUI_PHAP_CHE_ROLES` — trưởng
phòng trở lên, cộng HCNS và CNTT — trên TIỀN TỐ RIÊNG. Không nới `/api/v1/ir-phap-che`: tiền tố ấy
chứa sổ công bố thông tin, sổ chữ ký và cả bàn làm việc Pháp chế.

BỐN LUẬT, mỗi luật vá một cách hỏng:
  1. Phòng gửi, người gửi LẤY TỪ TÀI KHOẢN, không nhận từ màn hình — không ai gửi thay tên người khác.
  2. Cửa đọc CHỈ trả yêu cầu do chính người đang đăng nhập gửi (`boi`). Không đọc được việc phòng khác.
  3. Người gửi chỉ BỔ SUNG khi Pháp chế đã chuyển «chờ bổ sung»; không tự đóng, không tự đổi trạng thái.
  4. Gửi xong có một chuông cho Pháp chế; chuông tự tắt khi Pháp chế nhận việc hoặc đóng yêu cầu.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.attachments import Attachment
from app.models.core import ROLES, User
from app.models.phap_che_viec import LOAI_YEU_CAU, MUC_DO, TRANG_THAI_YC, YeuCauPhapChe
from app.services import access as AC
from app.services import attachments as AT
from app.services import phap_che_viec as PV
from app.services import rules as R
from app.services.storage import StorageError

router = APIRouter(prefix="/api/v1/gui-phap-che", tags=["gui-phap-che"])

GUI = AC.GUI_PHAP_CHE_ROLES
DOI_TUONG = "yeu_cau_phap_che"
# Loại chỉ dành cho Pháp chế tự mở (hồ sơ công bố là việc của chính Pháp chế, không phải yêu cầu phòng ban).
LOAI_PHONG_GUI = tuple(k for k in LOAI_YEU_CAU if k != "ho_so_cong_bo")


class GuiIn(BaseModel):
    loai: str = "y_kien_phap_ly"
    tieu_de: str
    noi_dung: str = ""
    muc_do: str = "thuong"
    han_mong_muon: date | None = None


class BoSungIn(BaseModel):
    noi_dung_bo_sung: str


def _cua_toi(db: Session, u: User, yid: int) -> YeuCauPhapChe:
    yc = db.get(YeuCauPhapChe, yid)
    if yc is None or yc.boi != u.username:
        # 404 chứ không 403: không cho đoán một mã yêu cầu của phòng khác có tồn tại hay không.
        raise HTTPException(404, "Không có yêu cầu này trong danh sách bạn đã gửi")
    return yc


def _ra(db: Session, yc: YeuCauPhapChe) -> dict:
    v = PV.ra_yc(db, yc)
    v["co_the_bo_sung"] = yc.trang_thai == "cho_bo_sung"
    return v


@router.get("")
def cua_toi(u: User = Depends(require_roles(*GUI, *AC.READ_ALL, mo_ta="yêu cầu Pháp chế đã gửi")),
            db: Session = Depends(get_db)):
    ds = db.execute(select(YeuCauPhapChe).where(YeuCauPhapChe.boi == u.username)
                    .order_by(YeuCauPhapChe.luc.desc())).scalars().all()
    return {"rows": [_ra(db, x) for x in ds],
            "loai": {k: LOAI_YEU_CAU[k] for k in LOAI_PHONG_GUI}, "muc_do": MUC_DO,
            "trang_thai": TRANG_THAI_YC,
            "phong_gui": u.department or ROLES.get(u.role, u.role), "nguoi_gui": u.full_name}


@router.post("", status_code=201)
def gui(body: GuiIn, u: User = Depends(require_roles(*GUI, mo_ta="gửi yêu cầu Pháp chế")),
        db: Session = Depends(get_db)):
    if body.loai not in LOAI_PHONG_GUI:
        raise HTTPException(422, f"Loại yêu cầu không hợp lệ: {body.loai}")
    if body.muc_do not in MUC_DO:
        raise HTTPException(422, f"Mức độ không hợp lệ: {body.muc_do}")
    if not (body.tieu_de or "").strip():
        raise HTTPException(422, "Phải ghi tiêu đề")
    data = body.model_dump()
    data["tieu_de"] = data["tieu_de"].strip()[:300]
    data["phong_gui"] = (u.department or ROLES.get(u.role, u.role))[:80]
    data["nguoi_gui"] = (u.full_name or u.username)[:80]
    yc = PV.tao_yeu_cau(db, data, u.username)
    PV.bao_chuong_yc_moi(db, yc)
    R.audit(db, u.username, u.role, "gui_yeu_cau_phap_che", f"yeu_cau:{yc.id}",
            after={"loai": yc.loai, "tieu_de": yc.tieu_de, "muc_do": yc.muc_do})
    db.commit()
    return {"message": f"Đã gửi Pháp chế yêu cầu #{yc.id}", "yeu_cau": _ra(db, yc)}


@router.post("/{yid}/bo-sung")
def bo_sung(yid: int, body: BoSungIn, u: User = Depends(require_roles(*GUI, mo_ta="bổ sung yêu cầu Pháp chế")),
            db: Session = Depends(get_db)):
    yc = _cua_toi(db, u, yid)
    if yc.trang_thai != "cho_bo_sung":
        raise HTTPException(422, "Chỉ bổ sung được khi Pháp chế đang chờ bạn bổ sung")
    them = (body.noi_dung_bo_sung or "").strip()
    if not them:
        raise HTTPException(422, "Phải ghi nội dung bổ sung")
    yc.noi_dung = (yc.noi_dung or "") + f"\n\n[Bổ sung {datetime.now():%d/%m/%Y %H:%M}] {them}"
    # Trả việc về tay Pháp chế: đã có người nhận thì về «đang xử lý», chưa thì về «mới».
    yc.trang_thai = "dang_xu_ly" if yc.nguoi_nhan else "moi"
    R.audit(db, u.username, u.role, "bo_sung_yeu_cau_phap_che", f"yeu_cau:{yc.id}",
            after={"bo_sung": them[:200]})
    db.commit()
    return {"message": f"Đã bổ sung yêu cầu #{yc.id}", "yeu_cau": _ra(db, yc)}


@router.post("/{yid}/tep", status_code=201)
async def gan_tep(yid: int, tep: UploadFile = File(...),
                  u: User = Depends(require_roles(*GUI, mo_ta="gắn tệp vào yêu cầu Pháp chế")),
                  db: Session = Depends(get_db)):
    yc = _cua_toi(db, u, yid)
    if yc.trang_thai in PV.DA_DONG:
        raise HTTPException(422, "Yêu cầu đã đóng – gửi yêu cầu mới")
    data = await tep.read()
    try:
        a, _moi = AT.dinh_kem(db, DOI_TUONG, str(yc.id), tep.filename or "tep", data,
                              tep.content_type or "", "hop_dong", f"Yêu cầu Pháp chế #{yc.id}", u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    yc.attachment_id = a.id
    R.audit(db, u.username, u.role, "gan_tep_yeu_cau_phap_che", f"yeu_cau:{yc.id}",
            after={"tep": a.id, "ten": a.ten_tep})
    db.commit()
    return {"message": f"Đã gắn tệp {a.ten_tep}", "yeu_cau": _ra(db, yc)}


@router.get("/{yid}/tep")
def tai_tep(yid: int, u: User = Depends(require_roles(*GUI, mo_ta="tệp kèm yêu cầu Pháp chế")),
            db: Session = Depends(get_db)):
    """Người gửi mở lại tệp của CHÍNH MÌNH. Pháp chế mở ở `/api/v1/ir-phap-che/yeu-cau/{id}/tep`."""
    yc = _cua_toi(db, u, yid)
    a = db.get(Attachment, yc.attachment_id) if yc.attachment_id else None
    if a is None:
        raise HTTPException(404, "Yêu cầu này chưa có tệp đính kèm")
    try:
        data = AT.doc(db, a)
    except StorageError as ex:
        raise HTTPException(503, str(ex))
    return Response(content=data, media_type=a.kieu_noi_dung or "application/octet-stream",
                    headers={"Content-Disposition": f'inline; filename="{a.id}-{a.ten_tep}"'})
