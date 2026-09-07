"""Màn hình Tài khoản & phân quyền (đặc tả 07/9/2026, phần B).

Nguyên tắc của màn hình này: ma trận quyền VẪN nằm trong mã nguồn, ở đây chỉ CÔNG BỐ chứ không sửa.
Cho sửa ma trận trên giao diện thì mất hai thứ đang bảo vệ hệ thống – phép thử tự động và lịch sử thay
đổi trong git – và một lần bấm nhầm là mở cả sổ lương. Thứ sửa được ở đây chỉ có ba: ai ở vai trò nào,
tài khoản mở hay khóa, và ngoại lệ có thời hạn (API ngoại lệ nằm ở routes.py).
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.models.core import User, ROLES, Company
from app.services import access as AC
from app.services import access_admin as AA
from app.services import rules as R

router = APIRouter(prefix="/api/v1/access", tags=["phan-quyen"])
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

XEM = ("chutich", "tgd", "cntt", "hcns", "bks")     # mở được màn hình
THAO_TAC = ("cntt", "hcns")                          # đổi vai trò, khóa/mở, đặt lại mật khẩu
# Ba vai trò còn phạm vi rộng nhất sau khi siết ma trận: đổi AI SANG một trong ba vai trò này phải do
# Chủ tịch hoặc TGĐ làm. Quyền nhìn toàn bộ tiền và sổ sách tương đương quyền ký – một người ở HCNS
# hoặc CNTT không nên tự trao được cho ai.
VAI_TRO_NHAY_CAM = ("ketoan", "cntt", "bks")


@router.get("/matrix")
def matrix(u: User = Depends(require_roles(*XEM))):
    return AA.ma_tran()


@router.get("/matrix.xlsx")
def matrix_xlsx(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Bản Excel để TGĐ ký rà quyền hằng tháng."""
    noi_dung = AA.ma_tran_xlsx(db)
    R.audit(db, u.username, u.role, "xuat_ma_tran_quyen", "access"); db.commit()
    return Response(content=noi_dung, media_type=XLSX,
                    headers={"Content-Disposition": f'attachment; filename="MA_TRAN_PHAN_QUYEN_{datetime.now():%d%m%y}.xlsx"'})


@router.get("/accounts")
def accounts(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return {"rows": AA.danh_sach_tai_khoan(db), "roles": ROLES,
            "companies": [{"id": c.id, "code": c.code, "name": c.name}
                          for c in db.execute(select(Company).where(Company.active == True).order_by(Company.code)).scalars()],
            "vai_tro_nhay_cam": VAI_TRO_NHAY_CAM}


@router.get("/gaps")
def gaps(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return AA.chenh_lech(db)


@router.get("/audit")
def audit_log(limit: int = 200, ke_ca_dang_nhap: bool = False,
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return {"rows": AA.nhat_ky_quyen(db, limit, bo_dang_nhap=not ke_ca_dang_nhap)}


class DoiVaiTroIn(BaseModel):
    role: str
    reason: str


@router.post("/role-change/{uid}")
def role_change(uid: int, data: DoiVaiTroIn,
                u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Đổi vai trò kèm lý do bằng lời. Ba chốt chặn, mỗi cái vá một cách mất kiểm soát khác nhau."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if data.role not in ROLES: raise HTTPException(422, f"Vai trò không hợp lệ: {data.role}")
    if not (data.reason or "").strip(): raise HTTPException(422, "Phải ghi lý do đổi vai trò")
    if t.id == u.id: raise HTTPException(422, "Không tự đổi vai trò của chính mình")
    if t.role in ("chutich", "tgd") and u.role != "cntt":
        raise HTTPException(403, "Chỉ CNTT thao tác trên tài khoản lãnh đạo")
    if data.role in VAI_TRO_NHAY_CAM and u.role not in ("chutich", "tgd"):
        raise HTTPException(403, f"Đổi sang vai trò {ROLES[data.role]} phải do Chủ tịch hoặc Tổng giám đốc – "
                                 f"đây là vai trò nhìn được toàn bộ tiền và sổ sách")
    if data.role == t.role: raise HTTPException(422, "Vai trò không thay đổi")
    before = {"vai_tro": t.role}
    t.role, t.role_changed_at, t.role_changed_by = data.role, datetime.now(), u.username
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"vai_tro": t.role, "ly_do": data.reason.strip()[:300]})
    db.commit()
    return {"message": f"Đã đổi vai trò {t.full_name} thành {ROLES[t.role]}", "role": t.role}


class PhapNhanIn(BaseModel):
    company_id: int | None = None


@router.put("/users/{uid}/company")
def gan_phap_nhan(uid: int, data: PhapNhanIn,
                  u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Gán pháp nhân chủ quản cho tài khoản. Để trống là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ –
    giữ đúng quy ước đã dùng ở tour, booking, xe và hồ sơ nhân sự."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    if data.company_id is not None and not db.get(Company, data.company_id):
        raise HTTPException(422, "Pháp nhân không có trong danh mục")
    before = {"company_id": t.company_id}
    t.company_id = data.company_id
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"company_id": t.company_id})
    db.commit()
    return {"message": "Đã cập nhật pháp nhân chủ quản", "company_id": t.company_id}


class BienCheIn(BaseModel):
    ngoai_bien_che: bool


@router.put("/users/{uid}/bien-che")
def danh_dau_bien_che(uid: int, data: BienCheIn,
                      u: User = Depends(require_roles(*THAO_TAC, "chutich", "tgd")), db: Session = Depends(get_db)):
    """Đánh dấu tài khoản NGOÀI biên chế (kế toán trưởng thuê ngoài, kiểm toán, tư vấn): có tài khoản
    nhưng không có trong bảng lương. Không đánh dấu thì danh sách đối chiếu báo lệch mãi mãi, và rà
    quyền hằng tháng không nhìn ra ai là người ngoài."""
    t = db.get(User, uid)
    if not t: raise HTTPException(404, "Không có tài khoản")
    before = {"ngoai_bien_che": t.ngoai_bien_che}
    t.ngoai_bien_che = data.ngoai_bien_che
    R.audit(db, u.username, u.role, "sua_tai_khoan", f"user:{t.username}", before=before,
            after={"ngoai_bien_che": t.ngoai_bien_che})
    db.commit()
    return {"message": "Đã đánh dấu ngoài biên chế" if data.ngoai_bien_che else "Đã bỏ đánh dấu ngoài biên chế"}
