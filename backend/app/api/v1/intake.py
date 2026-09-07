"""Nạp dữ liệu vào VTOS – một cửa cho người nhập, cho tệp tải lên, và cho AI.

Cả ba đường đi qua cùng bộ kiểm tra và cùng nhật ký. Nếu mỗi đường một kiểu kiểm tra thì cái chặt nhất
trở nên vô nghĩa: người ta chỉ cần đi đường lỏng nhất."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.intake import IntakeRun
from app.services import intake as IN, rules as R

router = APIRouter(prefix="/api/v1/nap-du-lieu", tags=["nap-du-lieu"])

# Mở màn hình rộng, chặn theo TỪNG BỘ NẠP (app/services/intake.VAI_TRO). Nếu chặn ở cửa màn hình thì
# hoặc phải mở cho mọi phòng – ai cũng nạp được mọi thứ – hoặc phải đóng bớt phòng, và phòng bị đóng sẽ
# nhờ người khác nạp hộ, tức là nhật ký ghi sai tên người chịu trách nhiệm.
READ = ("chutich", "tgd", "ptgd_doan", "ptgd_mkt", "tp_dh", "nv_dh", "ketoan", "bks", "cntt", "hcns",
        "gd_doi_xe", "gd_kd", "tp_kd", "tn_kd", "nv_kd", "nv_mkt")
WRITE = READ


@router.get("/bo-nap")
def bo_nap(u: User = Depends(require_roles(*READ))):
    """Khai báo cấu trúc từng loại dữ liệu: cột nào, bắt buộc không, ví dụ, khóa chống trùng.

    Đây cũng là thứ một tác vụ AI đọc để biết phải gửi lên những gì – không phải đoán từ màn hình."""
    return {"bo_nap": IN.danh_sach_bo_nap(), "nguon": IN.NGUON,
            "quy_tac": ["Kiểm tra trước, nạp sau: bước kiểm tra không ghi gì vào hệ thống.",
                        "Có dòng lỗi thì mặc định KHÔNG nạp gì cả; bỏ qua dòng lỗi phải là lựa chọn có ý thức.",
                        "Nạp lại cùng tệp không nhân đôi – mỗi bộ nạp có khóa chống trùng riêng.",
                        "Mỗi lần nạp đều ghi nhật ký: ai nạp, tệp nào, bao nhiêu dòng, mã băm nội dung."]}


@router.get("/mau/{loai}", response_class=PlainTextResponse)
def tep_mau(loai: str, u: User = Depends(require_roles(*READ))):
    """Tệp CSV mẫu: hàng 1 là tên cột, hàng 2 là một dòng ví dụ."""
    if loai not in IN.BO_NAP: raise HTTPException(404, f"Không có bộ nạp '{loai}'")
    return PlainTextResponse(IN.mau_csv(loai), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="mau_{loai}.csv"'})


class KiemTraIn(BaseModel):
    loai: str
    rows: list[dict]


@router.post("/kiem-tra")
def kiem_tra(data: KiemTraIn, u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Xem trước: trả về lỗi theo từng dòng. KHÔNG ghi gì vào hệ thống."""
    try:
        kq = IN.kiem_tra(db, data.loai, data.rows)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    db.rollback()          # chắc chắn không để lại thay đổi nào từ bước kiểm tra
    return kq


@router.post("/kiem-tra-tep")
async def kiem_tra_tep(loai: str = Form(...), tep: UploadFile = File(...),
                       u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    if loai not in IN.BO_NAP: raise HTTPException(422, f"Không có bộ nạp '{loai}'")
    noi_dung = await tep.read()
    try:
        rows = IN.doc_bang(noi_dung, tep.filename or "")
    except Exception as ex:
        raise HTTPException(422, f"Không đọc được tệp: {ex}. Hỗ trợ .csv và .xlsx, hàng đầu là tên cột.")
    if not rows: raise HTTPException(422, "Tệp không có dòng dữ liệu nào (hàng đầu phải là tên cột)")
    kq = IN.kiem_tra(db, loai, rows)
    db.rollback()
    return {**kq, "ten_tep": tep.filename, "rows": rows[:1000]}


class NapIn(BaseModel):
    loai: str
    rows: list[dict]
    bo_qua_dong_loi: bool = False
    ten_tep: str = ""
    nguon: str = "nguoi_nhap"       # nguoi_nhap / ai / he_thong
    tac_nhan: str = ""              # tên tác vụ AI, nếu nguồn là ai


@router.post("/nap", status_code=201)
def nap(data: NapIn, u: User = Depends(require_roles(*WRITE)), db: Session = Depends(get_db)):
    """Nạp thật. Luôn kiểm tra lại ở máy chủ trước khi ghi – không tin kết quả xem trước gửi kèm."""
    if not data.rows: raise HTTPException(422, "Không có dòng nào để nạp")
    if data.loai in IN.BO_NAP and not IN.duoc_nap(data.loai, u.role):
        raise HTTPException(403, f"Vai trò của anh/chị không nạp được '{IN.BO_NAP[data.loai]['ten']}'. "
                                 "Loại dữ liệu này thuộc phòng khác – nhờ họ nạp để nhật ký ghi đúng tên "
                                 "người chịu trách nhiệm.")
    try:
        kq = IN.nap(db, data.loai, data.rows, u.username, data.bo_qua_dong_loi,
                    data.ten_tep, data.nguon, data.tac_nhan)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    if kq["da_nap"] == 0 and kq.get("run_id") is None:
        db.rollback()
        return kq
    R.audit(db, u.username, u.role, "nap_du_lieu", f"bo_nap:{data.loai}",
            after={k: kq[k] for k in ("so_dong", "da_nap", "da_co", "dong_loi") if k in kq})
    db.commit()
    return kq


@router.get("/lich-su")
def lich_su(loai: str = "", u: User = Depends(require_roles(*READ)), db: Session = Depends(get_db)):
    """Nhật ký nạp: trả lời câu hỏi 'con số này ở đâu ra' vào đúng lúc khó nhất."""
    q = select(IntakeRun).order_by(IntakeRun.id.desc())
    if loai: q = q.where(IntakeRun.loai == loai)
    return [{"id": r.id, "loai": r.loai, "ten_bo_nap": IN.BO_NAP.get(r.loai, {}).get("ten", r.loai),
             "ten_tep": r.ten_tep, "nguon": r.nguon, "nguon_ten": IN.NGUON.get(r.nguon, r.nguon),
             "tac_nhan": r.tac_nhan, "so_dong": r.so_dong, "da_nap": r.da_nap,
             "bo_qua_da_co": r.bo_qua_da_co, "dong_loi": r.dong_loi,
             "bo_qua_dong_loi": r.bo_qua_dong_loi, "hash": r.dau_vao_hash[:12],
             "boi": r.boi, "luc": r.luc} for r in db.execute(q.limit(200)).scalars()]
