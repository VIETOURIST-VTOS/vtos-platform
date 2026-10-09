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


# ═════════════════════════════════════════════════════════════════════════════════════════════
# Đợt E1 (09/10/2026) · MỨC ĐỘ CHẶN và CHIỀU PHÂN TÍCH
#
# Hai cửa, một quy tắc chung về ai được bấm: THẮT CHẶT thì Kế toán làm được, NỚI LỎNG phải có
# chữ ký. Bật một cờ chiều là thêm điều kiện cho dòng bút toán — thắt. Tắt nó đi là bỏ điều kiện
# — nới. Đặt một phép kiểm xuống "không cảnh báo" cũng là nới. Bất đối xứng này cố ý, và nó là
# cùng một nguyên tắc đã dùng cho bảng quy ước hạch toán ngay trên tệp này.
# ═════════════════════════════════════════════════════════════════════════════════════════════
from app.models.accounting import Account as _TK
from app.models.muc_do_chan import MUC_DO as _MUC_DO, LUAT_CUNG as _LUAT_CUNG, MucDoChan as _MDC
from app.services import ke_toan_chieu as KTC

TINH_CHAT = {"du_no": "Dư Nợ", "du_co": "Dư Có", "luong_tinh": "Lưỡng tính"}


class MucDoIn(BaseModel):
    ma_phep_kiem: str
    ten: str = ""
    mo_ta: str = ""
    muc_do: str = ""          # rỗng = để trống, chưa đặt mức
    nguoi_xu_ly: str = ""
    han_xu_ly_ngay: int | None = None
    nguoi_thay_the: str = ""
    ngay_hieu_luc: date | None = None
    can_cu: str = ""


class ChieuIn(BaseModel):
    code: str
    tinh_chat: str | None = None
    co_ngoai_te: bool | None = None
    ngung_su_dung: bool | None = None
    td_doi_tuong: bool | None = None
    td_doi_tuong_loai: str | None = None
    td_cong_trinh: bool | None = None
    td_khoan_muc: bool | None = None


@router.get("/muc-do-chan")
def bang_muc_do(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    rows = db.query(_MDC).order_by(_MDC.ma_phep_kiem).all()
    return {
        "muc_do": _MUC_DO,
        "luat_cung": list(_LUAT_CUNG),
        "chua_dat_muc": KTC.phep_kiem_chua_dat_muc(db),
        "dong": [{
            "id": r.id, "ma_phep_kiem": r.ma_phep_kiem, "ten": r.ten, "mo_ta": r.mo_ta,
            "muc_do": r.muc_do, "nguoi_xu_ly": r.nguoi_xu_ly, "han_xu_ly_ngay": r.han_xu_ly_ngay,
            "nguoi_thay_the": r.nguoi_thay_the,
            "ngay_hieu_luc": r.ngay_hieu_luc.isoformat() if r.ngay_hieu_luc else None,
            "nguoi_ky": r.nguoi_ky, "can_cu": r.can_cu, "dang_ap_dung": r.dang_ap_dung,
        } for r in rows],
    }


@router.post("/muc-do-chan")
def dat_muc_do(data: MucDoIn, u: User = Depends(require_roles(*KY)), db: Session = Depends(get_db)):
    """Đặt mức cho một phép kiểm. Chỉ Chủ tịch / TGĐ — vì hạ một mức chặn là nới một hàng rào."""
    ma = (data.ma_phep_kiem or "").strip()
    if not ma:
        raise HTTPException(422, "Thiếu mã phép kiểm")
    if ma in _LUAT_CUNG:
        raise HTTPException(422, f"'{ma}' là LUẬT CỨNG – luôn chặn, không đặt mức được. "
                                 "Bốn luật cứng: " + ", ".join(_LUAT_CUNG))
    if data.muc_do and data.muc_do not in _MUC_DO:
        raise HTTPException(422, f"Mức không hợp lệ. Nhận: {', '.join(_MUC_DO)}")
    if data.muc_do and not (data.nguoi_xu_ly or "").strip():
        raise HTTPException(422, "Đặt mức thì phải nói AI xử lý khi phép kiểm kêu. "
                                 "Một cảnh báo không có người là một dòng chữ.")
    r = db.query(_MDC).filter(_MDC.ma_phep_kiem == ma).first()
    if r is None:
        r = _MDC(ma_phep_kiem=ma, ten=data.ten or ma)
        db.add(r)
    r.ten = data.ten or r.ten or ma
    r.mo_ta = data.mo_ta
    r.muc_do = data.muc_do or None
    r.nguoi_xu_ly = data.nguoi_xu_ly
    r.han_xu_ly_ngay = data.han_xu_ly_ngay
    r.nguoi_thay_the = data.nguoi_thay_the
    r.ngay_hieu_luc = data.ngay_hieu_luc
    r.can_cu = data.can_cu
    r.nguoi_ky = u.username
    r.boi = u.username
    db.commit()
    return {"message": f"Đã đặt mức cho '{ma}'", "ma_phep_kiem": ma, "muc_do": r.muc_do}


@router.get("/tai-khoan-chieu")
def bang_chieu(chi_da_khai: bool = False, u: User = Depends(require_roles(*XEM)),
               db: Session = Depends(get_db)):
    q = db.query(_TK).order_by(_TK.code)
    rows = q.all()
    dong = [{
        "code": t.code, "name": t.name, "kind": t.kind, "tinh_chat": t.tinh_chat,
        "co_ngoai_te": bool(t.co_ngoai_te), "ngung_su_dung": bool(t.ngung_su_dung),
        "td_doi_tuong": bool(t.td_doi_tuong), "td_doi_tuong_loai": t.td_doi_tuong_loai or "",
        "td_cong_trinh": bool(t.td_cong_trinh), "td_khoan_muc": bool(t.td_khoan_muc),
    } for t in rows]
    if chi_da_khai:
        dong = [d for d in dong if d["tinh_chat"] or d["td_doi_tuong"] or d["td_cong_trinh"]
                or d["td_khoan_muc"]]
    return {"tinh_chat": TINH_CHAT, "tong": len(rows),
            "chua_khai_tinh_chat": sum(1 for t in rows if not (t.tinh_chat or "").strip()),
            "dong": dong}


@router.post("/tai-khoan-chieu")
def khai_chieu(data: ChieuIn, u: User = Depends(require_roles(*XEM)),
               db: Session = Depends(get_db)):
    """Khai chiều cho một tài khoản.

    THẮT thì Kế toán làm được; NỚI phải có chữ ký Chủ tịch / TGĐ. Cụ thể:
      · bật một cờ `td_*`            → thắt  (thêm điều kiện cho dòng bút toán)
      · tắt một cờ đang bật          → nới
      · khai `tinh_chat` lần đầu     → được
      · đổi `tinh_chat` đã khai      → nới (đổi nghĩa của phép kiểm số dư bất thường)
      · bật `ngung_su_dung`          → thắt
    """
    t = db.get(_TK, (data.code or "").strip())
    if t is None:
        raise HTTPException(404, f"Không có tài khoản {data.code}")
    la_ky = u.role in KY
    noi: list[str] = []

    for co in ("td_doi_tuong", "td_cong_trinh", "td_khoan_muc"):
        v = getattr(data, co)
        if v is None:
            continue
        if getattr(t, co) and not v:
            noi.append(f"tắt cờ {co}")
    if data.tinh_chat is not None:
        cu = (t.tinh_chat or "").strip()
        if cu and data.tinh_chat != cu:
            noi.append(f"đổi tính chất {cu} → {data.tinh_chat}")
        if data.tinh_chat and data.tinh_chat not in TINH_CHAT:
            raise HTTPException(422, f"Tính chất không hợp lệ. Nhận: {', '.join(TINH_CHAT)}")
    if data.ngung_su_dung is not None and t.ngung_su_dung and not data.ngung_su_dung:
        noi.append("mở lại tài khoản đã ngừng")
    if noi and not la_ky:
        raise HTTPException(403, "Nới hàng rào phải có chữ ký Chủ tịch hoặc TGĐ: " + "; ".join(noi))

    for k in ("tinh_chat", "co_ngoai_te", "ngung_su_dung", "td_doi_tuong", "td_doi_tuong_loai",
              "td_cong_trinh", "td_khoan_muc"):
        v = getattr(data, k)
        if v is not None:
            setattr(t, k, v)
    if t.td_doi_tuong and not (t.td_doi_tuong_loai or "").strip():
        t.td_doi_tuong_loai = "tat_ca"
    db.commit()
    return {"message": f"Đã khai chiều cho TK {t.code}", "code": t.code,
            "chieu_bat_buoc": [ten for _c, ten in KTC.chieu_bat_buoc(t)]}
