"""API IR & Pháp chế (Đợt D1) – văn bản có phiên bản, nghĩa vụ công bố, bản ghi công bố.

VAI `ir_phapche` KHAI THEO CHỈ ĐẠO CHỦ TỊCH 08/10/2026: một người kiêm cả IR và Pháp chế, phạm vi
TOÀN TẬP ĐOÀN (không cắt theo pháp nhân). Lần viết phần mềm không tự khai quyền; lần này có chỉ đạo
trực tiếp, và nó được ghi ra đây để một lần xem lại mã sau này biết quyền ấy từ đâu mà có.

KHÔNG CÓ Ô NÀO CHO NGƯỜI GÕ TRẠNG THÁI CÔNG BỐ. Người ghi THỜI ĐIỂM công bố, NƠI công bố và VĂN BẢN
đã công bố; trạng thái (quá hạn / đúng hạn / trễ) do quy tắc xác định tính ra. Một ô "đã công bố"
gõ được là một lời khai, mà lời khai thì không cần tới phần mềm nào.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.models.phap_che import (BanGhiCongBo, CHU_KY_CONG_BO, LOAI_VAN_BAN, NghiaVuCongBo,
                                 TRANG_THAI_VB, VanBanPhapChe)
from app.services import phap_che as PC
from app.services import rules as R

router = APIRouter(prefix="/api/v1/ir-phap-che", tags=["ir-phap-che"])

# Ai MỞ được màn hình. Hẹp hơn hẳn các màn hình nghiệp vụ: hồ sơ công bố và văn bản HĐQT là chuyện
# của Ban Tổng giám đốc, Pháp chế và Kiểm soát – không phải của phòng ban.
XEM = ("chutich", "tgd", "ir_phapche", "bks", "cntt")
# Ai GHI được. Ban Kiểm soát đọc mà không ghi: kiểm soát mà sửa được thứ mình kiểm thì không còn là
# kiểm soát. CNTT cũng chỉ đọc – vận hành hệ thống không phải là ra văn bản.
GHI = ("chutich", "tgd", "ir_phapche")


# ====================== VĂN BẢN ======================
class VanBanIn(BaseModel):
    loai: str = "quy_dinh"
    so_hieu: str = ""
    tieu_de: str
    tom_tat: str = ""
    hieu_luc_tu: date | None = None
    hieu_luc_den: date | None = None
    nguoi_ky: str = ""
    ngay_ky: date | None = None
    ly_do_sua: str = ""


@router.get("/meta")
def meta(u: User = Depends(require_roles(*XEM))):
    return {"loai_van_ban": LOAI_VAN_BAN, "trang_thai_van_ban": TRANG_THAI_VB,
            "chu_ky_cong_bo": CHU_KY_CONG_BO, "trang_thai_ban_ghi": PC.TRANG_THAI_BG,
            "ngay_bao_som": PC.NGAY_BAO_SOM, "ghi_duoc": GHI}


@router.get("/van-ban")
def van_ban_ds(loai: str = "", chi_hieu_luc: bool = False,
               u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    q = select(VanBanPhapChe).order_by(VanBanPhapChe.goc_id, VanBanPhapChe.so_ban)
    ds = list(db.execute(q).scalars())
    if loai:
        ds = [v for v in ds if v.loai == loai]
    if chi_hieu_luc:
        ds = [v for v in ds if v.trang_thai == "hieu_luc"]
    return {"so": len(ds), "rows": [PC.ra_vb(v) for v in ds]}


@router.get("/van-ban/{goc_id}/phien-ban")
def van_ban_phien_ban(goc_id: int, u: User = Depends(require_roles(*XEM)),
                      db: Session = Depends(get_db)):
    """Mọi phiên bản của một văn bản, theo thứ tự. Đây là chỗ trả lời 'bản trước nó nói gì'."""
    ds = PC.cac_phien_ban(db, goc_id)
    if not ds:
        raise HTTPException(404, "Không có văn bản này")
    return {"goc_id": goc_id, "so_phien_ban": len(ds), "rows": [PC.ra_vb(v) for v in ds]}


@router.post("/van-ban", status_code=201)
def van_ban_tao(body: VanBanIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    if body.loai not in LOAI_VAN_BAN:
        raise HTTPException(422, f"Loại văn bản không hợp lệ: {body.loai}")
    d = body.model_dump()
    d.pop("ly_do_sua", None)
    v = PC.tao_moi(db, d, u.username)
    R.audit(db, u.username, u.role, "tao_van_ban_phap_che", f"van_ban:{v.id}",
            after={"tieu_de": v.tieu_de, "loai": v.loai})
    db.commit()
    return {"message": f"Đã tạo bản nháp phiên bản 1 – {v.tieu_de}", "van_ban": PC.ra_vb(v)}


@router.put("/van-ban/{vid}")
def van_ban_sua(vid: int, body: VanBanIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    """Bản nháp sửa tại chỗ; bản ĐÃ CÓ HIỆU LỰC sinh phiên bản mới. Xem services/phap_che.py."""
    v = db.get(VanBanPhapChe, vid)
    if v is None:
        raise HTTPException(404, "Không có văn bản này")
    d = body.model_dump(exclude_unset=True)
    ly_do = d.pop("ly_do_sua", "")
    truoc = v.so_ban
    try:
        ra = PC.sua(db, v, d, ly_do, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "sua_van_ban_phap_che", f"van_ban:{ra.id}",
            before={"phien_ban": truoc}, after={"phien_ban": ra.so_ban})
    db.commit()
    moi = ra.so_ban != truoc
    return {"message": (f"Bản đã có hiệu lực không sửa tại chỗ – đã sinh phiên bản {ra.so_ban}"
                        if moi else "Đã lưu bản nháp"),
            "sinh_phien_ban_moi": moi, "van_ban": PC.ra_vb(ra)}


@router.post("/van-ban/{vid}/ban-hanh")
def van_ban_ban_hanh(vid: int, hieu_luc_tu: date | None = None,
                     u: User = Depends(require_roles(*GHI)), db: Session = Depends(get_db)):
    v = db.get(VanBanPhapChe, vid)
    if v is None:
        raise HTTPException(404, "Không có văn bản này")
    try:
        PC.ban_hanh(db, v, hieu_luc_tu, u.username)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "ban_hanh_van_ban_phap_che", f"van_ban:{v.id}",
            after={"phien_ban": v.so_ban, "hieu_luc_tu": str(v.hieu_luc_tu)})
    db.commit()
    return {"message": f"Phiên bản {v.so_ban} có hiệu lực từ {v.hieu_luc_tu:%d/%m/%Y}",
            "van_ban": PC.ra_vb(v)}


# ====================== NGHĨA VỤ CÔNG BỐ ======================
class NghiaVuIn(BaseModel):
    ma: str
    ten: str
    can_cu: str = ""
    chu_ky: str = "su_kien"
    han_sau_ngay: int | None = None
    mo_ta_han: str = ""
    dang_ap_dung: bool = True


@router.get("/nghia-vu")
def nghia_vu_ds(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    ds = list(db.execute(select(NghiaVuCongBo).order_by(NghiaVuCongBo.ma)).scalars())
    return {"so": len(ds),
            "rows": [{"id": n.id, "ma": n.ma, "ten": n.ten, "can_cu": n.can_cu,
                      "chu_ky": n.chu_ky, "han_sau_ngay": n.han_sau_ngay,
                      "mo_ta_han": n.mo_ta_han, "dang_ap_dung": n.dang_ap_dung,
                      "khai_boi": n.khai_boi, "khai_luc": n.khai_luc} for n in ds],
            "ghi_chu": ("Hệ thống KHÔNG nạp sẵn nghĩa vụ nào. Danh mục và thời hạn là quy định pháp "
                        "luật; điền chúng từ trí nhớ của phần mềm thì một hạn sai không hiện ra như "
                        "lỗi phần mềm mà hiện ra như một lần chậm công bố.")}


@router.post("/nghia-vu", status_code=201)
def nghia_vu_tao(body: NghiaVuIn, u: User = Depends(require_roles(*GHI)),
                 db: Session = Depends(get_db)):
    if body.chu_ky not in CHU_KY_CONG_BO:
        raise HTTPException(422, f"Chu kỳ không hợp lệ: {body.chu_ky}")
    if db.execute(select(NghiaVuCongBo).where(NghiaVuCongBo.ma == body.ma)).scalars().first():
        raise HTTPException(422, f"Mã nghĩa vụ '{body.ma}' đã có")
    if not (body.can_cu or "").strip():
        raise HTTPException(422, "Phải ghi CĂN CỨ – một nghĩa vụ không ai nhớ vì sao có là nghĩa "
                                 "vụ sẽ bị bỏ khi bận")
    n = NghiaVuCongBo(khai_boi=u.username, khai_luc=datetime.now(), **body.model_dump())
    db.add(n)
    R.audit(db, u.username, u.role, "khai_nghia_vu_cong_bo", f"nghia_vu:{body.ma}",
            after={"ten": body.ten, "chu_ky": body.chu_ky})
    db.commit()
    return {"message": f"Đã khai nghĩa vụ {n.ma}", "id": n.id}


# ====================== BẢN GHI CÔNG BỐ ======================
class BanGhiIn(BaseModel):
    nghia_vu_id: int
    ky: str
    moc_phat_sinh: date | None = None
    han_chot: date | None = None
    ghi_chu: str = ""


class DaCongBoIn(BaseModel):
    da_cong_bo_luc: datetime | None = None
    noi_cong_bo: str
    van_ban_id: int | None = None
    ghi_chu: str = ""


@router.get("/bang-dieu-khien")
def bang_dieu_khien(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return PC.bang_dieu_khien(db)


@router.post("/ban-ghi", status_code=201)
def ban_ghi_tao(body: BanGhiIn, u: User = Depends(require_roles(*GHI)),
                db: Session = Depends(get_db)):
    nv = db.get(NghiaVuCongBo, body.nghia_vu_id)
    if nv is None:
        raise HTTPException(404, "Không có nghĩa vụ này")
    if db.execute(select(BanGhiCongBo).where(BanGhiCongBo.nghia_vu_id == nv.id,
                                             BanGhiCongBo.ky == body.ky)).scalars().first():
        raise HTTPException(422, f"Kỳ '{body.ky}' của nghĩa vụ {nv.ma} đã có bản ghi")
    han = body.han_chot or PC.han_tu_moc(nv, body.moc_phat_sinh)
    bg = BanGhiCongBo(nghia_vu_id=nv.id, ky=body.ky, moc_phat_sinh=body.moc_phat_sinh,
                      han_chot=han, ghi_chu=body.ghi_chu, boi=u.username, luc=datetime.now())
    db.add(bg)
    db.flush()
    R.audit(db, u.username, u.role, "mo_ban_ghi_cong_bo", f"cong_bo:{nv.ma}:{body.ky}",
            after={"han_chot": str(han)})
    db.commit()
    return {"message": ("Đã mở bản ghi" if han else
                        "Đã mở bản ghi – CHƯA xác định được hạn: nghĩa vụ này không khai hạn bằng "
                        "số ngày, mời điền hạn chốt tay"),
            "ban_ghi": PC.ra_bg(db, bg)}


@router.post("/ban-ghi/{bid}/da-cong-bo")
def ban_ghi_da_cong_bo(bid: int, body: DaCongBoIn, u: User = Depends(require_roles(*GHI)),
                       db: Session = Depends(get_db)):
    """Ghi lần công bố. Người ghi THỜI ĐIỂM, NƠI và VĂN BẢN – trạng thái do quy tắc tính ra."""
    bg = db.get(BanGhiCongBo, bid)
    if bg is None:
        raise HTTPException(404, "Không có bản ghi này")
    if bg.da_cong_bo_luc is not None:
        raise HTTPException(422, "Bản ghi này đã có lần công bố – mở bản ghi mới nếu công bố bổ sung")
    if not (body.noi_cong_bo or "").strip():
        raise HTTPException(422, "Phải ghi NƠI công bố – 'đã công bố' mà không nói ở đâu thì không "
                                 "chứng minh được bằng gì")
    if body.van_ban_id is not None and db.get(VanBanPhapChe, body.van_ban_id) is None:
        raise HTTPException(422, "Không có văn bản được trỏ tới")
    # Đợt D2: chủ số liệu đã được hỏi mà chưa trả lời — hoặc đã từ chối — thì cửa này không
    # mở. Pháp chế không phải người biết doanh thu quý đúng hay sai; người biết là chủ con số.
    from app.services import phap_che_viec as PV
    vuong = PV.chan_cong_bo(db, bg.id)
    if vuong:
        raise HTTPException(422, vuong)
    bg.da_cong_bo_luc = body.da_cong_bo_luc or datetime.now()
    bg.noi_cong_bo = body.noi_cong_bo.strip()[:160]
    bg.van_ban_id = body.van_ban_id
    if body.ghi_chu:
        bg.ghi_chu = body.ghi_chu
    d = PC.ra_bg(db, bg)
    R.audit(db, u.username, u.role, f"cong_bo_{d['trang_thai']}", f"cong_bo:{bg.id}",
            after={"noi": bg.noi_cong_bo, "luc": str(bg.da_cong_bo_luc)})
    db.commit()
    return {"message": d["trang_thai_ten"], "ban_ghi": d}
