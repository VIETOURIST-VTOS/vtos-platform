"""Bảng quy ước hạch toán, cổng chặn giá vốn, và xem trước bút toán.

Ba việc, một màn hình: quy ước là dữ liệu ai cũng đọc được; đơn thiếu giá vốn nằm chờ chứ không
lặng lẽ thành 100% lãi; và mọi bút toán máy định khoản đều XEM TRƯỚC rồi mới ghi sổ.

Ai sửa quy ước: Kế toán trình, Chủ tịch và TGĐ ký – y hệt tham số chính sách. Không ai một mình
đổi được một dòng định khoản, kể cả Kế toán trưởng.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_roles
from app.models.core import User
from app.services import hach_toan as HT
from app.services import cong_chan as CC
from app.services import accounting as ACC
from app.services import rules as R

router = APIRouter(prefix="/api/v1/hach-toan", tags=["hach-toan"])

# tp_dh có mặt vì hàng đợi thiếu giá vốn đứng tên phòng Điều hành. Bảng quy ước cũng mở cho họ đọc:
# đây là chính sách nội bộ, không phải số tiền – và phòng phải nhập giá vốn thì nên biết dòng họ nhập
# sẽ chạy vào tài khoản nào. Ma trận quyền và tuple này phải khớp nhau, lệch một cái là menu mở mà API chặn.
XEM = ("chutich", "tgd", "bks", "ketoan", "cntt", "tp_dh")
TRINH = ("ketoan",)                 # Chủ tịch/TGĐ vẫn qua được (FULL_ACCESS trong deps)
KY = ("chutich", "tgd")
QUET = ("ketoan", "cntt", "bks")
GHI_SO = ("ketoan",)


@router.get("")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return HT.bang(db)


@router.post("/nap-mac-dinh")
def nap_mac_dinh(u: User = Depends(require_roles("cntt")), db: Session = Depends(get_db)):
    """Nạp bộ quy ước theo bốn quyết định ngày 08/9/2026. Đã có mã nào thì giữ nguyên mã đó."""
    n = HT.nap_mac_dinh(db)
    R.audit(db, u.username, u.role, "nap_quy_tac_hach_toan", "quy_tac:mac_dinh", after={"them": n})
    db.commit()
    return {"them": n, "message": f"Đã nạp {n} quy tắc mới" if n else "Bộ quy tắc đã đủ, không thêm gì"}


class QuyTacIn(BaseModel):
    ma: str
    ten: str
    nguon: str
    dieu_kien: dict = {}
    tk_no: str
    tk_co: str
    tk_thue: str = ""
    ben_thue: str = ""
    ty_le_thue: float = 0
    doi_tuong: str = ""
    can_cong_trinh: bool = False
    dien_giai: str = ""
    uu_tien: int = 100
    can_cu: str = ""
    ghi_chu: str = ""
    effective_from: date


@router.post("/quy-tac")
def de_xuat(data: QuyTacIn, u: User = Depends(require_roles(*TRINH)), db: Session = Depends(get_db)):
    try:
        q = HT.de_xuat(db, u, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"id": q.id, "message": "Đã trình – chờ Chủ tịch và TGĐ ký, quy tắc chưa có hiệu lực"}


@router.post("/quy-tac/{qid}/ky")
def ky(qid: int, u: User = Depends(require_roles(*KY)), db: Session = Depends(get_db)):
    try:
        q = HT.ky(db, u, qid)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"status": q.status,
            "message": "Đã ký – quy tắc có hiệu lực từ ngày đã ghi" if q.status == "active" else "Đã ký, chờ chữ ký còn lại"}


class XemTruocIn(BaseModel):
    nguon: str
    so_tien: float
    boi_canh: dict = {}
    ngay: date | None = None


@router.post("/xem-truoc")
def xem_truoc(data: XemTruocIn, u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Định khoản thử. KHÔNG ghi sổ, không đụng dữ liệu – dùng để đối chiếu quy ước trước khi chạy hàng loạt."""
    try:
        return HT.xem_truoc(db, data.nguon, data.so_tien, data.boi_canh, data.ngay)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class GhiSoIn(BaseModel):
    nguon: str
    so_tien: float
    boi_canh: dict = {}
    ngay: date
    nguon_chung_tu: str = ""      # receipt:PT… / tour:… – chống ghi trùng
    tour_id: int | None = None


@router.post("/ghi-so")
def ghi_so(data: GhiSoIn, u: User = Depends(require_roles(*GHI_SO)), db: Session = Depends(get_db)):
    """Ghi sổ đúng bút toán vừa xem trước. Máy định khoản, người bấm nút – và người bấm nút đứng tên."""
    bt = HT.xem_truoc(db, data.nguon, data.so_tien, data.boi_canh, data.ngay)
    if not bt.get("khop"):
        raise HTTPException(422, bt.get("ly_do") or "Không có quy tắc khớp")
    # Cổng chặn giá vốn: quy tắc doanh thu không được chạy cho đơn chưa có giá vốn.
    if bt["quy_tac"] == "DOANH_THU" and data.tour_id:
        from app.models.core import Tour
        t = db.get(Tour, data.tour_id)
        if t is not None:
            try:
                CC.chan(t)
            except ValueError as ex:
                raise HTTPException(422, str(ex))
    try:
        e = ACC.post_entry(db, u.username, u.role, data.ngay, bt["dien_giai"], bt["lines"],
                           source_type="quy_tac", source_ref=data.nguon_chung_tu or f"quy_tac:{bt['quy_tac']}",
                           tour_id=data.tour_id)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.commit()
    return {"code": e.code, "quy_tac": bt["quy_tac"], "message": f"Đã ghi sổ chứng từ {e.code}"}


# ---------------- Cổng chặn giá vốn ----------------
@router.get("/thieu-gia-von")
def thieu_gia_von(trang_thai: str = "cho", ky: str = "", ly_do: str = "",
                  u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return CC.danh_sach(db, trang_thai, ky, ly_do)


@router.post("/thieu-gia-von/quet")
def quet(ky: str = "", u: User = Depends(require_roles(*QUET)), db: Session = Depends(get_db)):
    ra = CC.quet(db, ky)
    R.audit(db, u.username, u.role, "quet_cong_gia_von", "thieu_gia_von", after=ra)
    db.commit()
    return ra


class BoQuaIn(BaseModel):
    ma_don: str
    giai_trinh: str


@router.post("/thieu-gia-von/bo-qua")
def bo_qua(data: BoQuaIn, u: User = Depends(require_roles(*GHI_SO)), db: Session = Depends(get_db)):
    try:
        r = CC.bo_qua(db, u, data.ma_don, data.giai_trinh)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"ma_don": r.ma_don, "message": "Đã ghi lý do cho qua – việc này nằm trong nhật ký bất biến"}
