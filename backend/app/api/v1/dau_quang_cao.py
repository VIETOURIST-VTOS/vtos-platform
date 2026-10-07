"""Cửa nhận dấu nguồn quảng cáo.

CỬA NHẬN ĐỨNG SAU KHOÁ MÁY CHỦ (`robot_auth`), KHÔNG phải cửa công khai. Toàn kho hiện có đúng
MỘT cửa không cần đăng nhập – trang khách tự chấm điểm sau tour – và tệp ấy ghi rõ không mở thêm
cửa ra đường mà không có người quyết. Cửa này không cần mở: website, webhook Facebook và tổng đài
đều gọi được từ phần MÁY CHỦ của chúng.

KHOÁ KHÔNG BAO GIỜ ĐƯỢC DÁN VÀO JAVASCRIPT CHẠY TRÊN TRÌNH DUYỆT. Ai bấm xem mã nguồn trang cũng
đọc được, và từ đó bơm dấu giả vào VTOS tuỳ ý – mà dấu giả thì sẽ được đẩy ngược lên Google và
Facebook như chuyển đổi thật, tức là mình tự dạy nền tảng tối ưu sai rồi trả tiền cho nó. Form
web phải gửi từ phía máy chủ. Website không có phần máy chủ thì dừng lại và bàn lại cách khác,
đừng dán khoá.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles, robot_auth
from app.db.session import get_db
from app.models.core import User
from app.models.quang_cao import DauQuangCao, NEN_TANG_QUEN, LOAI_MA_QUEN, NGUON_GHI
from app.services import access as AC
from app.services import chuyen_doi_di as CD
from app.services import dau_quang_cao as DQ
from app.services import rules as R

router = APIRouter(prefix="/api/v1/dau-quang-cao", tags=["dau-quang-cao"])

# Ai ĐỌC được. Dấu nguồn không phải số tiền, nhưng nó mang số điện thoại khách – đúng loại dữ
# liệu của màn hình lead – nên nó lấy ĐÚNG danh sách vai của màn hình ấy, và lấy bằng cách SUY TỪ
# nhóm vai chứ không chép tay ra đây. Chép tay thì ngày nào đó hai chỗ lệch nhau, và lúc lệch thì
# một người mở được màn hình nhưng gọi cửa bị 403 – lỗi khó lần nhất trong loại này.
#
# `ptgd_doan` KHÔNG có mặt, vì màn hình /leads hôm nay không có ông. Nới quyền cho P.TGĐ tour đoàn
# là một quyết định riêng, và nó phải được quyết ở dòng menu của /leads chứ không lẻn vào đây.
XEM = AC.BASE_VIEW + AC.SALES + AC.OPERATIONS + AC.MARKETING + ("ptgd_mkt", "cntt")


class DauVao(BaseModel):
    nen_tang: str
    loai_ma: str = "khac"
    ma: str = ""
    ma_chien_dich: str = ""
    ma_nhom_qc: str = ""
    ma_mau_qc: str = ""
    ten_chien_dich: str = ""
    sdt: str = ""
    zalo_uid: str = ""
    utm: dict = {}
    trang_dich: str = ""
    trang_gioi_thieu: str = ""
    cham_luc: str = ""
    nguon_ghi: str = "khac"
    than_nguyen_van: str = ""
    ghi_chu: str = ""


class GoiNhan(BaseModel):
    # Nhận MỘT GÓI NHIỀU DÒNG. Webhook gửi từng cái một, nhưng tệp nạp và lượt quét lại thì gửi
    # hàng loạt, và mở hai cửa cho cùng một việc là hai chỗ phải sửa mỗi lần đổi.
    dau: list[DauVao]


def ra(r: DauQuangCao) -> dict:
    return {"id": r.id, "nen_tang": r.nen_tang,
            "nen_tang_ten": NEN_TANG_QUEN.get(r.nen_tang, r.nen_tang),
            "loai_ma": r.loai_ma, "loai_ma_ten": LOAI_MA_QUEN.get(r.loai_ma, r.loai_ma),
            "ma": r.ma, "ma_chien_dich": r.ma_chien_dich, "ma_nhom_qc": r.ma_nhom_qc,
            "ma_mau_qc": r.ma_mau_qc, "ten_chien_dich": r.ten_chien_dich,
            "sdt": r.sdt, "zalo_uid": r.zalo_uid, "lead_id": r.lead_id,
            "utm": r.utm or {}, "trang_dich": r.trang_dich,
            "trang_gioi_thieu": r.trang_gioi_thieu,
            "cham_luc": r.cham_luc, "nhan_luc": r.nhan_luc,
            "nguon_ghi": r.nguon_ghi, "nguon_ghi_ten": NGUON_GHI.get(r.nguon_ghi, r.nguon_ghi),
            "ghi_chu": r.ghi_chu, "boi": r.boi}


@router.post("/nhan", status_code=201, dependencies=[Depends(robot_auth)])
def nhan(goi: GoiNhan, db: Session = Depends(get_db)):
    """Nhận dấu từ website, webhook hoặc tổng đài.

    MỘT DÒNG HỎNG KHÔNG LÀM HỎNG CẢ GÓI. Khác hẳn cửa nạp tệp, nơi mặc định là có lỗi thì không
    nạp gì cả: ở đó người nhập đang ngồi trước màn hình và sửa được: ở đây đầu kia là một máy chủ
    đang gửi sự kiện thời gian thực, và từ chối cả gói vì một dòng sai múi giờ là vứt đi những
    dấu đúng mà không bao giờ lấy lại được. Dòng hỏng trả về kèm lý do để bên gửi gửi lại.
    """
    if not goi.dau:
        raise HTTPException(422, "Gói rỗng – không có dấu nào để ghi")
    if len(goi.dau) > 500:
        raise HTTPException(422, "Tối đa 500 dấu một lượt – chia nhỏ gói")
    moi = cu = 0
    loi: list[dict] = []
    for i, d in enumerate(goi.dau):
        try:
            _, la_moi = DQ.ghi(db, d.model_dump(), boi="cua-nhan")
            moi += la_moi
            cu += (not la_moi)
        except ValueError as ex:
            loi.append({"dong": i, "ly_do": str(ex)})
        except Exception as ex:                      # noqa: BLE001 – xem docstring
            db.rollback()
            loi.append({"dong": i, "ly_do": f"{type(ex).__name__}: {str(ex)[:160]}"})
    db.commit()
    return {"nhan": len(goi.dau), "moi": moi, "da_co": cu, "loi": loi,
            "message": f"Ghi {moi} dấu mới, {cu} dấu đã có" + (f", {len(loi)} dòng hỏng" if loi else "")}


@router.post("/ghep-lead", dependencies=[Depends(robot_auth)])
def ghep(db: Session = Depends(get_db)):
    """Quét lại những dấu chưa khớp lead. Lead thường tới SAU cái chạm."""
    n = DQ.ghep_lead_con_thieu(db)
    return {"da_ghep": n, "message": f"Ghép thêm {n} dấu vào lead"}


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return {"nen_tang": NEN_TANG_QUEN, "loai_ma": LOAI_MA_QUEN, "nguon_ghi": NGUON_GHI}


@router.get("/bang-do")
def bang_do(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return DQ.bang_do(db)


@router.get("")
def danh_sach(nen_tang: str = "", chua_ghep: int = 0, sdt: str = "", limit: int = 200,
              u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(DauQuangCao).order_by(desc(DauQuangCao.id))
    if nen_tang:
        q = q.where(DauQuangCao.nen_tang == nen_tang.strip().lower())
    if chua_ghep:
        q = q.where(DauQuangCao.lead_id.is_(None))
    if sdt.strip():
        from app.services.zalo import norm_phone
        q = q.where(DauQuangCao.sdt == norm_phone(sdt))
    return [ra(r) for r in db.execute(q.limit(min(max(limit, 1), 2000))).scalars()]


class GanIn(BaseModel):
    lead_id: int


@router.post("/{did}/gan-lead")
def gan_lead(did: int, data: GanIn,
             u: User = Depends(require_roles("ptgd_mkt", "nv_mkt", "gd_kd", "tp_kd", "cntt", "tgd")),
             db: Session = Depends(get_db)):
    """Gắn tay một dấu vào lead – khi máy không khớp được, ví dụ khách gọi bằng số khác."""
    from app.models.crm import Lead
    r = db.get(DauQuangCao, did)
    if not r:
        raise HTTPException(404, "Không có dấu này")
    l = db.get(Lead, data.lead_id)
    if not l:
        raise HTTPException(404, "Không có lead này")
    cu = r.lead_id
    r.lead_id = l.id
    R.audit(db, u.username, u.role, "gan_dau_quang_cao", f"dau_quang_cao:{r.id}",
            before={"lead_id": cu}, after={"lead_id": l.id})
    db.commit()
    return {**ra(r), "message": f"Đã gắn dấu {r.nen_tang} vào lead {l.phone}"}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HÀNG ĐỢI CHUYỂN ĐỔI GỬI NGƯỢC
# ══════════════════════════════════════════════════════════════════════════════════════════════
class KetQuaIn(BaseModel):
    xong: bool
    tra_loi: str = ""
    loi: str = ""


def cd_ra(c) -> dict:
    from app.models.quang_cao import CD_TRANG_THAI
    return {"id": c.id, "dau_id": c.dau_id, "lead_id": c.lead_id, "nen_tang": c.nen_tang,
            "nen_tang_ten": NEN_TANG_QUEN.get(c.nen_tang, c.nen_tang),
            "loai_ma": c.loai_ma, "ma": c.ma, "ma_booking": c.ma_booking,
            "doanh_thu": c.doanh_thu, "tien_te": c.tien_te, "chot_luc": c.chot_luc,
            "trang_thai": c.trang_thai,
            "trang_thai_ten": CD_TRANG_THAI.get(c.trang_thai, c.trang_thai),
            "lan_thu": c.lan_thu, "loi_cuoi": c.loi_cuoi, "gui_luc": c.gui_luc,
            "tao_luc": c.tao_luc}


@router.post("/chuyen-doi/sinh", dependencies=[Depends(robot_auth)])
def cd_sinh(db: Session = Depends(get_db)):
    """Xếp việc cho bộ gửi: lead đã chốt tour thì mỗi nền tảng có dấu được một dòng."""
    return {**CD.sinh(db), "message": "Đã quét và xếp hàng đợi chuyển đổi"}


@router.get("/chuyen-doi/cho-gui", dependencies=[Depends(robot_auth)])
def cd_cho_gui(gioi_han: int = 100, db: Session = Depends(get_db)):
    """Bộ gửi lấy việc. Chỉ trả dòng CÓ doanh thu – gửi 0 đồng là dạy nền tảng sai."""
    return [cd_ra(c) for c in CD.cho_gui(db, gioi_han)]


@router.post("/chuyen-doi/{cid}/ket-qua", dependencies=[Depends(robot_auth)])
def cd_ket_qua(cid: int, data: KetQuaIn, db: Session = Depends(get_db)):
    """Bộ gửi báo lại. Lỗi không xoá dòng – giữ để đếm được và để gửi lại."""
    from app.models.quang_cao import ChuyenDoiGuiDi
    c = db.get(ChuyenDoiGuiDi, cid)
    if not c:
        raise HTTPException(404, "Không có dòng chuyển đổi này")
    return cd_ra(CD.ghi_ket_qua(db, c, data.xong, data.tra_loi, data.loi))


@router.get("/chuyen-doi/bang-do")
def cd_bang_do(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return CD.bang_do(db)


@router.get("/chuyen-doi")
def cd_danh_sach(trang_thai: str = "", nen_tang: str = "", limit: int = 200,
                 u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    from sqlalchemy import select as _sel
    from app.models.quang_cao import ChuyenDoiGuiDi
    q = _sel(ChuyenDoiGuiDi).order_by(desc(ChuyenDoiGuiDi.id))
    if trang_thai:
        q = q.where(ChuyenDoiGuiDi.trang_thai == trang_thai.strip())
    if nen_tang:
        q = q.where(ChuyenDoiGuiDi.nen_tang == nen_tang.strip().lower())
    return [cd_ra(c) for c in db.execute(q.limit(min(max(limit, 1), 2000))).scalars()]
