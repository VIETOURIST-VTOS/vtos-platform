"""Màn hình Vị trí AI & quyền hạn (đặc tả 07/9/2026, phần C)."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User, AiPosition, AiPause, AI_GROUPS, AI_LEVELS, AI_CAM
from app.services import ai_quyen as AQ
from app.services import ai_log as AL
from app.services import rules as R

router = APIRouter(prefix="/api/v1/ai", tags=["quyen-ai"])

XEM = ("chutich", "tgd", "ptgd_mkt", "cntt", "bks", "robot_pq")
SUA = ("chutich", "tgd", "cntt")            # đặt mức và hạn mức
TAT_KHAN = ("chutich", "tgd", "cntt")


@router.get("/positions")
def positions(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    them = AQ.nap_mac_dinh(db)
    if them: db.commit()
    return {**AQ.bang(db), "viec_ai_khong_duoc_lam": list(AI_CAM), "vua_nap_mac_dinh": them}


class OIn(BaseModel):
    vai_tro: str
    tac_vu: str
    muc: int
    han_muc: dict | None = None


@router.put("/positions")
def dat_muc(data: OIn, u: User = Depends(require_roles(*SUA)), db: Session = Depends(get_db)):
    """Đặt mức cho một ô. Mức 3 không khai đủ hạn mức thì KHÔNG lưu – mức 3 không hạn mức chính là tình
    trạng trước ngày 07/9: AI gửi tin cho khách thật, không giới hạn, không ai hậu kiểm."""
    if data.tac_vu not in AI_GROUPS: raise HTTPException(422, f"Nhóm việc không hợp lệ: {data.tac_vu}")
    if data.muc not in (0, 1, 2, 3, 4): raise HTTPException(422, "Mức phải từ 0 đến 4")
    from app.models.core import ROLES
    if data.vai_tro not in ROLES: raise HTTPException(422, f"Vai trò không hợp lệ: {data.vai_tro}")
    thieu = AQ.thieu_han_muc(data.muc, data.han_muc)
    if thieu:
        raise HTTPException(422, {"gate": "THIEU_HAN_MUC",
                                  "message": "Mức 3 phải khai đủ hạn mức, còn thiếu: " + ", ".join(thieu),
                                  "thieu": thieu})
    p = db.execute(select(AiPosition).where(AiPosition.vai_tro == data.vai_tro,
                                            AiPosition.tac_vu == data.tac_vu)).scalars().first()
    truoc = {"muc": p.muc, "han_muc": p.han_muc} if p else None
    if p is None:
        p = AiPosition(vai_tro=data.vai_tro, tac_vu=data.tac_vu); db.add(p)
    p.muc, p.han_muc = data.muc, (data.han_muc or {})
    p.updated_at, p.updated_by = datetime.now(), u.username
    R.audit(db, u.username, u.role, "dat_quyen_ai", f"ai:{data.vai_tro}:{data.tac_vu}",
            before=truoc, after={"muc": p.muc, "han_muc": p.han_muc})
    db.commit()
    return {"message": f"Đã đặt {AI_GROUPS[data.tac_vu]} của {ROLES[data.vai_tro]} ở mức {data.muc} – {AI_LEVELS.get(data.muc, '')}"}


class PauseIn(BaseModel):
    tam_dung: bool
    ly_do: str = ""


@router.post("/pause")
def tat_khan(data: PauseIn, u: User = Depends(require_roles(*TAT_KHAN)), db: Session = Depends(get_db)):
    """Tạm dừng toàn bộ AI đối ngoại: hạ mọi ô mức 3 xuống mức 2 ngay, không cần phát hành lại phần mềm."""
    if data.tam_dung and not (data.ly_do or "").strip():
        raise HTTPException(422, "Phải ghi lý do tạm dừng")
    p = db.get(AiPause, 1)
    if p is None:
        p = AiPause(id=1); db.add(p)
    truoc = {"tam_dung": p.tam_dung, "ly_do": p.ly_do}
    p.tam_dung, p.ly_do = data.tam_dung, data.ly_do.strip()[:300]
    p.boi, p.luc = u.username, datetime.now()
    R.audit(db, u.username, u.role, "tat_khan_ai", "ai:doi_ngoai", before=truoc,
            after={"tam_dung": p.tam_dung, "ly_do": p.ly_do})
    db.commit()
    return {"message": "Đã tạm dừng AI đối ngoại – mọi ô mức 3 hạ xuống mức 2" if data.tam_dung
                       else "Đã mở lại AI đối ngoại", "tam_dung": p.tam_dung}


@router.get("/report")
def bao_cao(so_ngay: int = 7, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Ba báo cáo của đặc tả mục C5: AI làm gì, tỷ lệ bị người sửa, việc bị thu hồi."""
    tu = datetime.now() - timedelta(days=max(1, min(so_ngay, 90)))
    th = AL.tong_hop(db, tu)
    cho = AL.cho_hau_kiem(db)
    return {
        "tu_ngay": tu, "so_ngay": so_ngay, **th,
        "ten_tac_vu": AI_GROUPS,
        "cho_hau_kiem_chi_tiet": [{"id": r.id, "ts": r.ts, "tac_vu": r.tac_vu, "ref": r.ref,
                                   "ket_qua": (r.ket_qua or "")[:300], "nguon": r.nguon} for r in cho[:50]],
        "ghi_chu_ty_le": ("Tỷ lệ bị sửa tính trên phần ĐÃ hậu kiểm. Chưa hậu kiểm cái nào thì không có tỷ lệ – "
                          "0% đọc ra là 'chưa sai lần nào', đúng theo tốc độ người ta quên hậu kiểm."),
    }
