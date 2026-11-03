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
from app.services import access as AC
from app.services import cong_chan as CC
from app.services import accounting as ACC
from app.services import chung_tu_loai as CTL   # Đợt E3 – ba bảng phân loại chứng từ
from app.services import rules as R

router = APIRouter(prefix="/api/v1/hach-toan", tags=["hach-toan"])

# tp_dh có mặt vì hàng đợi thiếu giá vốn đứng tên phòng Điều hành. Bảng quy ước cũng mở cho họ đọc:
# đây là chính sách nội bộ, không phải số tiền – và phòng phải nhập giá vốn thì nên biết dòng họ nhập
# sẽ chạy vào tài khoản nào. Ma trận quyền và tuple này phải khớp nhau, lệch một cái là menu mở mà API chặn.
XEM = ("chutich", "tgd", "bks", "ketoan", "ketoan_truong", "cntt", "tp_dh", "hcns")
TRINH = ("ketoan",)                 # Chủ tịch/TGĐ vẫn qua được (FULL_ACCESS trong deps)
KY = ("chutich", "tgd")
QUET = ("ketoan", "cntt", "bks")
GHI_SO = ("ketoan",)


@router.get("")
def bang(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    return HT.bang(db)


@router.get("/bang")
def danh_muc_httt(u: User = Depends(require_roles(*AC.PAYMENT_REQUEST_ROLES, "thu_quy",
                                                   # DOT DON-R4c3 04/11/2026 — them
                                                   # `ketoan_tt`: vai ay CO `/expenses`
                                                   # trong MAN_HINH_KETOAN_TT nhung CO Y
                                                   # khong ke thua `ketoan`, nen khong
                                                   # duong nao noi toi no va o hinh thuc
                                                   # thanh toan RONG voi dung vai xu
                                                   # chuyen khoan.
                                                   "ketoan_tt",
                                                   mo_ta="danh mục hình thức thanh toán cho nút ĐÃ CHI")),
                  db: Session = Depends(get_db)):
    """SUA-2 02/11/2026 — đường `/hach-toan/bang` mà màn /expenses gọi (Đợt P2-1 đã khai vào bản đồ màn hình)
    nhưng KHÔNG CÓ trên máy chủ: ô «Hình thức thanh toán» khi bấm ĐÃ CHI luôn rỗng. Cửa này trả ĐÚNG MỘT danh
    mục tĩnh `HINH_THUC_TT` — không quy tắc, không số liệu — cho mười vai lập đề nghị chi và thủ quỹ (người bấm
    ĐÃ CHI, `ops.VAI_GHI_DA_CHI`). Bảng quy ước đầy đủ vẫn chỉ ở `GET /hach-toan` với `XEM`."""
    from app.models.hach_toan import HINH_THUC_TT
    return {"hinh_thuc_tt": HINH_THUC_TT}


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
    # DOT R4c-1 02/11/2026 — HAI O NAY `HT.de_xuat()` DA DOC tu Dot R2 (15/10/2026) qua
    # `data.get(...)`, nhung mo hinh cua cua KHONG khai, nen qua API chung LUON rong/False.
    # Hau qua nang hon "thieu mot o": BA phep kiem hinh thuc thanh toan trong `de_xuat`
    # chi dung khi o ay khac rong, nen hai trong ba la MA CHET tren duong API — tu
    # 15/10/2026 chung chua chan duoc gi. Va khong trinh duoc mot quy tac tien mat nao,
    # nen sau dong tien mat cua Dot R2 chi them duoc bang cach sua ma.
    # Mac dinh GIU NGUYEN hanh vi cu (rong / False) nen khong quy tac nao dang chay doi.
    hinh_thuc_tt: str = ""
    can_khoan_muc: bool = False
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
    # Đợt R2 15/10/2026 — BẮT ValueError Ở ĐÂY. `dung_but_toan` nay ném khi quy tắc bắt buộc mã
    # khoản mục mà bối cảnh không có. Không bắt thì người dùng nhận một mã 500 trắng thay vì câu
    # "chọn một mã ở danh mục Khoản mục chi phí rồi ghi lại" — mà câu ấy mới là cả giá trị của
    # phép chặn. Cửa `/xem-truoc` ngay trên đã bắt từ trước; cửa này thì chưa, và đây là cửa GHI.
    try:
        bt = HT.xem_truoc(db, data.nguon, data.so_tien, data.boi_canh, data.ngay)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
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
                           tour_id=data.tour_id, nghiep_vu="theo_quy_tac")
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


# ══════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT E2a — TÁCH BẠCH TRÁCH NHIỆM THEO NGƯỜI
#
# Vào chung tiền tố `/api/v1/hach-toan` đã có sẵn trong MAN_HINH_API của màn hình /ket-so, nên
# PHAM_VI_DA_CHOT KHÔNG đổi một số. Không tự khai thêm một lát quyền nào.
# ══════════════════════════════════════════════════════════════════════════════════════════
from datetime import datetime as _dt                             # noqa: E402
from sqlalchemy import select as _select                         # noqa: E402
from app.models.muc_do_chan import MUC_DO as _MUC_DO             # noqa: E402
from app.models.muc_do_chan import MUC_DO_KHI_CHUA_KHAI as _MAC_DINH   # noqa: E402
from app.models.tach_nhiem import CapTachNhiem as _CTN           # noqa: E402
from app.services import ks_tach_nhiem as _KTN                   # noqa: E402


class CapIn(BaseModel):
    ma_cap: str
    buoc_a: str
    buoc_b: str
    ten: str = ""
    mo_ta: str = ""
    muc_do: str | None = None
    nguoi_ky: str = ""
    can_cu: str = ""
    dang_ap_dung: bool | None = None


@router.get("/cap-tach-nhiem")
def xem_cap_tach_nhiem(u: User = Depends(require_roles(*XEM, mo_ta="cặp tách bạch trách nhiệm")),
                       db: Session = Depends(get_db)):
    ds = db.execute(_select(_CTN).order_by(_CTN.ma_cap)).scalars().all()
    return {
        "cac_cap": [{
            "ma_cap": c.ma_cap, "buoc_a": c.buoc_a, "buoc_b": c.buoc_b, "ten": c.ten,
            "mo_ta": c.mo_ta, "muc_do_khai": c.muc_do or "", "muc_do_dang_ap": _KTN.muc_do(c),
            "nguoi_ky": c.nguoi_ky, "can_cu": c.can_cu, "dang_ap_dung": bool(c.dang_ap_dung),
            "ngay_hieu_luc": c.ngay_hieu_luc.isoformat() if c.ngay_hieu_luc else "",
        } for c in ds],
        "muc_do": _MUC_DO,
        "chua_dat_muc": _KTN.cap_chua_dat_muc(db),
        "mac_dinh_khi_chua_khai": _MAC_DINH,
    }


@router.post("/cap-tach-nhiem")
def khai_cap_tach_nhiem(data: CapIn,
                        u: User = Depends(require_roles(*XEM, mo_ta="cặp tách bạch trách nhiệm")),
                        db: Session = Depends(get_db)):
    """THẮT thì Kế toán làm được, NỚI phải có chữ ký — cùng bất đối xứng của Đợt E1."""
    if data.buoc_a.strip() == data.buoc_b.strip() or not data.buoc_a.strip() or not data.buoc_b.strip():
        raise HTTPException(422, "Một cặp phải là HAI bước khác nhau, và cả hai đều phải có tên.")
    if data.muc_do is not None and data.muc_do != "" and data.muc_do not in _MUC_DO:
        raise HTTPException(422, f"Mức độ không hợp lệ. Nhận: {', '.join(_MUC_DO)}")

    la_ky = u.role in KY
    c = db.execute(_select(_CTN).where(_CTN.ma_cap == data.ma_cap)).scalars().first()
    noi = []
    if c is None:
        c = _CTN(ma_cap=data.ma_cap, buoc_a=data.buoc_a.strip(), buoc_b=data.buoc_b.strip())
        db.add(c)
    else:
        # HAI BƯỚC CỦA MỘT CẶP LÀ BẤT BIẾN. Trước bản vá này hai dòng ở cuối hàm ghi
        # `c.buoc_a, c.buoc_b = ...` vô điều kiện, nên giữ mã cặp mà đổi bước là gỡ được
        # kiểm soát trong khi mức vẫn đọc là "chặn" và người ký vẫn là Chủ tịch. Chữ ký nằm
        # trên CẶP BƯỚC, không nằm trên mã cặp — nên đây không phải một việc "nới có ký",
        # mà là một việc KHÔNG LÀM Ở ĐÂY. Canh cặp bước khác thì tạo cặp mới rồi tắt cặp cũ
        # (tắt đã là nới, đã phải ký và ghi căn cứ), và cả hai dòng ở lại bảng làm lịch sử.
        if {data.buoc_a.strip(), data.buoc_b.strip()} != {c.buoc_a, c.buoc_b}:
            raise HTTPException(422,
                f"Cặp `{c.ma_cap}` đang canh `{c.buoc_a}` ↔ `{c.buoc_b}`. Hai bước của một cặp "
                "KHÔNG đổi được sau khi tạo: chữ ký nằm trên chính cặp bước, nên đổi bước mà giữ "
                "mã là mang chữ ký của quyết định này sang một quyết định khác. Muốn canh cặp "
                "bước khác thì tạo cặp MỚI với mã mới, rồi tắt cặp này — tắt cặp cần chữ ký "
                "Chủ tịch hoặc TGĐ và một dòng căn cứ.")
        cu = _KTN.muc_do(c)
        if data.muc_do is not None and cu in ("canh_bao_va_chan",) and data.muc_do != cu:
            noi.append(f"hạ mức cặp {c.ma_cap}: {cu} → {data.muc_do}")
        if data.dang_ap_dung is False and c.dang_ap_dung:
            noi.append(f"tắt cặp {c.ma_cap}")
    if noi and not la_ky:
        raise HTTPException(403, "Nới hàng rào phải có chữ ký Chủ tịch hoặc TGĐ: " + "; ".join(noi))
    if noi and not (data.can_cu or "").strip():
        raise HTTPException(422, "Nới hàng rào phải ghi CĂN CỨ — một quyết định không giải trình "
                                 "được thì không ai dám xem lại.")

    c.buoc_a, c.buoc_b = data.buoc_a.strip(), data.buoc_b.strip()
    c.ten, c.mo_ta = data.ten or c.ten, data.mo_ta or c.mo_ta
    if data.muc_do is not None:
        c.muc_do = data.muc_do or None
    if data.dang_ap_dung is not None:
        c.dang_ap_dung = data.dang_ap_dung
    if data.nguoi_ky:
        c.nguoi_ky = data.nguoi_ky
    if data.can_cu:
        c.can_cu = data.can_cu
    if c.muc_do and not c.ngay_hieu_luc:
        c.ngay_hieu_luc = _dt.utcnow()
    c.boi, c.luc = u.username, _dt.utcnow()
    db.commit()
    return {"message": f"Đã khai cặp {c.ma_cap}", "muc_do_dang_ap": _KTN.muc_do(c),
            "chua_dat_muc": _KTN.cap_chua_dat_muc(db)}


@router.get("/dau-chan/{pham_vi}")
def xem_dau_chan(pham_vi: str,
                 u: User = Depends(require_roles(*XEM, mo_ta="dấu chân tách bạch trách nhiệm")),
                 db: Session = Depends(get_db)):
    """Ai đã làm bước gì trong phạm vi này (`dc:12`, `ky:2026-09`).

    Chỉ ĐỌC — dấu chân do hệ thống ghi đúng lúc một bước hoàn thành, không ai gõ tay vào được.
    """
    return {"pham_vi": pham_vi, "dau_chan": _KTN.dau_chan(db, pham_vi)}


@router.post("/cap-tach-nhiem/nap-da-ky")
def nap_cap_da_ky(u: User = Depends(require_roles(*XEM, mo_ta="cặp tách bạch trách nhiệm")),
                  db: Session = Depends(get_db)):
    """Nạp các cặp đã có chữ ký ghi trong mã nguồn (`models/tach_nhiem.CAP_DA_KY`).

    CỬA CHỨ KHÔNG PHẢI MIGRATION, và đó là chủ ý: một lần nâng cấp cơ sở dữ liệu tự dựng
    quy chế kiểm soát nội bộ thì không ai bấm, không ai biết, và không ai nhớ. Một cửa có
    người bấm thì có tên người và có giờ trong nhật ký. Chạy lại được, không dựng trùng, và
    KHÔNG đụng tới mức của dòng đã có — ai đặt mức rồi thì lần nạp sau không đặt lại hộ.
    """
    them = _KTN.nap_cap_da_ky(db)
    return {"message": f"Đã nạp {len(them)} cặp đã ký" if them else "Không có cặp nào mới",
            "da_nap": them, "chua_dat_muc": _KTN.cap_chua_dat_muc(db)}


@router.get("/thieu-ma-nhan-vien")
def xem_thieu_ma_nhan_vien(
        u: User = Depends(require_roles(*XEM, mo_ta="tài khoản thiếu mã nhân viên")),
        db: Session = Depends(get_db)):
    """Tài khoản vai tiền chưa có mã nhân viên — lỗ CÒN LẠI sau khi so theo người.

    Không có mã thì hai tài khoản của cùng một người được coi là hai người, nên họ đi được
    cả hai bước mà không ai thấy. Lỗ này chỉ bịt được bằng dữ liệu HCNS, không bịt được bằng
    mã — nên việc của phần mềm là ĐẾM và GỌI TÊN, để có người đi điền.
    """
    ds = _KTN.tai_khoan_thieu_ma_nv(db)
    return {"so_tai_khoan": len(ds), "tai_khoan": ds,
            "dang_bat_buoc": _KTN.bat_buoc_ma_nv(db),
            "tham_so_bat": "tach_nhiem_bat_buoc_ma_nv_tu"}


@router.get("/hai-vai-trung-nguoi")
def xem_hai_vai_trung_nguoi(
        u: User = Depends(require_roles(*XEM, mo_ta="hai vai không được kiêm nhau")),
        db: Session = Depends(get_db)):
    """Ai đang giữ cả hai tài khoản của một cặp vai không được kiêm nhau.

    CHỈ ĐỌC, và cố ý chỉ đọc. Việc phải sửa là thu hồi một quyền — việc của HCNS và người phê
    duyệt quyền, không phải việc của sổ kế toán. Phần mềm làm cho nó đếm được và gọi được tên.

    `mu_khi_thieu_ma_nv` không phải một cờ trang trí: nó nói rằng con số 0 ở đây KHÔNG có nghĩa
    là sạch khi còn tài khoản chưa có mã nhân viên. Hai con số phải đọc cùng nhau.

    Nó đếm bằng `thieu_ma_lam_mu_phep_do`, KHÔNG bằng `tai_khoan_thieu_ma_nv` — hai danh sách
    vai khác nhau, và dùng lẫn là lỗi đã mắc một lần: `tai_khoan_thieu_ma_nv` chỉ xét `VAI_TIEN`,
    không có `hcns`, nên cờ mù báo "không mù" đúng lúc đang mù vì tài khoản HCNS thiếu mã.
    """
    ds = _KTN.hai_vai_trung_nguoi(db)
    mu = _KTN.thieu_ma_lam_mu_phep_do(db)
    return {"so_truong_hop": len(ds), "cac_truong_hop": ds,
            "cac_cap": [dict(c) for c in _KTN.CAP_VAI_KHONG_KIEM],
            "mu_khi_thieu_ma_nv": len(mu) > 0,
            "so_tai_khoan_thieu_ma_nv": len(mu),
            "vai_can_ma": list(_KTN.vai_can_ma_de_phep_do_thay()),
            "tai_khoan_lam_mu": mu}


# ════════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT E3 – BA BẢNG PHÂN LOẠI CHỨNG TỪ, CHỈ ĐỌC
# ════════════════════════════════════════════════════════════════════════════════════════════════
# KHÔNG NỚI MỘT QUYỀN NÀO, và đó là chủ ý: cửa này nằm dưới đúng tiền tố `/api/v1/hach-toan` mà
# màn hình `/ket-so` đã khai trong `MAN_HINH_API`, nên `PHAM_VI_DA_CHOT` không đổi một số nào.
# Dựng một tiền tố thứ hai cho cùng một tập người là hai hàng rào phải canh cho một cánh cửa.
#
# CHỈ ĐỌC: ba bảng này khai trong mã (Chủ tịch chọn 12/10/2026), nên không có cửa ghi. Thêm một
# loại chứng từ là một lần sửa mã có người ký và có lịch sử git.
@router.get("/danh-muc-chung-tu", tags=["hach-toan"])
def danh_muc_chung_tu(u: User = Depends(require_roles(*XEM))):
    return CTL.danh_muc()


# ════════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R2 15/10/2026 — DANH MỤC KHOẢN MỤC CHI PHÍ
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Cùng tiền tố `/api/v1/hach-toan` đã khai, nên KHÔNG nới một quyền nào và không đụng bảng phân
# quyền — cùng lẽ với ba cửa danh mục chứng từ ở trên.
#
# KHÁC ba cửa ấy ở một điểm có chủ ý: danh mục này CÓ CỬA GHI. Loại chứng từ là luật kế toán, đổi
# nó phải sửa mã có người ký; còn khoản mục chi phí là CHIỀU PHÂN TÍCH của chính Vietourist —
# ngày mở dòng sản phẩm mới, Kế toán phải thêm được một khoản mục mà không chờ một đợt phần mềm.
# Đúng ranh giới 09/9/2026: máy dựng khuôn và phép tính, người khai nội dung.
#
# Vai ghi là `TRINH` (Kế toán; Chủ tịch/TGĐ vẫn qua được qua FULL_ACCESS) — KHÔNG mở cho `tp_dh`,
# dù họ đọc được bảng quy ước: Điều hành nhập giá vốn theo khoản mục, nhưng DANH SÁCH khoản mục
# là bộ xương của báo cáo tài chính và thuộc về Kế toán.
@router.get("/khoan-muc")
def khoan_muc_danh_sach(ca_ngung: bool = False,
                        u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    from app.models.khoan_muc_chi_phi import NHOM_KHOAN_MUC
    from app.services import khoan_muc_chi_phi as KM
    return {"nhom": NHOM_KHOAN_MUC, "rows": KM.danh_sach(db, ca_ngung=ca_ngung)}


@router.post("/khoan-muc/nap-mac-dinh")
def khoan_muc_nap_mac_dinh(u: User = Depends(require_roles(*TRINH)), db: Session = Depends(get_db)):
    """Gieo mười dòng khuôn ngành tour. Mã nào đã có thì GIỮ NGUYÊN, không đè lên bản đã sửa."""
    from app.services import khoan_muc_chi_phi as KM
    n = KM.nap_mac_dinh(db)
    R.audit(db, u.username, u.role, "nap_khoan_muc_chi_phi", "khoan_muc:mac_dinh", after={"them": n})
    db.commit()
    return {"them": n, "message": f"Đã thêm {n} khoản mục" if n else "Danh mục đã đủ, không thêm gì"}


class KhoanMucIn(BaseModel):
    ma: str
    ten: str
    nhom: str = "gia_von"
    thu_tu: int = 100
    ghi_chu: str = ""


class KhoanMucSuaIn(BaseModel):
    ten: str | None = None
    nhom: str | None = None
    thu_tu: int | None = None
    ghi_chu: str | None = None
    dung: bool | None = None


@router.post("/khoan-muc")
def khoan_muc_them(data: KhoanMucIn,
                   u: User = Depends(require_roles(*TRINH)), db: Session = Depends(get_db)):
    from app.services import khoan_muc_chi_phi as KM
    try:
        k = KM.them(db, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "them_khoan_muc_chi_phi", f"khoan_muc:{k.ma}",
            after={"ten": k.ten, "nhom": k.nhom})
    db.commit()
    return {"id": k.id, "ma": k.ma, "message": f"Đã thêm khoản mục {k.ma}"}


@router.patch("/khoan-muc/{kid}")
def khoan_muc_sua(kid: int, data: KhoanMucSuaIn,
                  u: User = Depends(require_roles(*TRINH)), db: Session = Depends(get_db)):
    """Sửa tên / nhóm / thứ tự / ghi chú, và BẬT-TẮT dùng. MÃ KHÔNG ĐỔI ĐƯỢC — xem dịch vụ."""
    from app.services import khoan_muc_chi_phi as KM
    truyen = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        k = KM.sua(db, kid, truyen)
    except ValueError as ex:
        raise HTTPException(404 if "Không có" in str(ex) else 422, str(ex))
    R.audit(db, u.username, u.role, "sua_khoan_muc_chi_phi", f"khoan_muc:{k.ma}", after=truyen)
    db.commit()
    return {"id": k.id, "ma": k.ma, "dung": k.dung, "message": f"Đã cập nhật khoản mục {k.ma}"}


# ════════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R3b 17/10/2026 — DANH MỤC BỘ PHẬN
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Cùng tiền tố `/api/v1/hach-toan` đã khai nên KHÔNG nới một quyền nào ở ma trận. Đặt cạnh danh
# mục khoản mục là có chủ ý: hai danh mục này là hai CHIỀU PHÂN TÍCH của cùng một bộ sổ, và người
# mở màn hình để sửa một cái thường sửa luôn cái kia.
#
# VAI GHI LÀ `GHI_BO_PHAN`, KHÁC `TRINH` của khoản mục — và đây là chỗ dễ làm sai nhất.
# Khoản mục chi phí là bộ xương của báo cáo tài chính nên thuộc về Kế toán. Cơ cấu bộ phận thì
# KHÔNG: ai còn, ai tách, ai nhập vào đâu là việc của Hành chính – Nhân sự. Mở cho Kế toán sửa cơ
# cấu phòng ban là trao cho họ một quyền chẳng ai ký, và ngược lại bắt HCNS đi nhờ Kế toán mỗi lần
# lập một phòng mới là dựng một cửa không ai dùng.
GHI_BO_PHAN = ("hcns",)             # Chủ tịch/TGĐ vẫn qua được (FULL_ACCESS trong deps)


@router.get("/bo-phan")
def bo_phan_danh_sach(ca_ngung: bool = False,
                      u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    from app.services import bo_phan as BP
    return {"rows": BP.danh_sach(db, ca_ngung=ca_ngung)}


@router.post("/bo-phan/nap-mac-dinh")
def bo_phan_nap_mac_dinh(u: User = Depends(require_roles(*GHI_BO_PHAN)),
                         db: Session = Depends(get_db)):
    """Gieo tám dòng khuôn cơ cấu. Mã nào đã có thì GIỮ NGUYÊN, không đè lên bản đã sửa."""
    from app.services import bo_phan as BP
    n = BP.nap_mac_dinh(db)
    R.audit(db, u.username, u.role, "nap_bo_phan", "bo_phan:mac_dinh", after={"them": n})
    db.commit()
    return {"them": n, "message": f"Đã thêm {n} bộ phận" if n else "Danh mục đã đủ, không thêm gì"}


class BoPhanIn(BaseModel):
    ma: str
    ten: str
    thu_tu: int = 100
    ghi_chu: str = ""


class BoPhanSuaIn(BaseModel):
    ten: str | None = None
    thu_tu: int | None = None
    ghi_chu: str | None = None
    dung: bool | None = None


@router.post("/bo-phan")
def bo_phan_them(data: BoPhanIn,
                 u: User = Depends(require_roles(*GHI_BO_PHAN)), db: Session = Depends(get_db)):
    from app.services import bo_phan as BP
    try:
        b = BP.them(db, data.model_dump())
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "them_bo_phan", f"bo_phan:{b.ma}", after={"ten": b.ten})
    db.commit()
    return {"id": b.id, "ma": b.ma, "message": f"Đã thêm bộ phận {b.ma}"}


@router.patch("/bo-phan/{bid}")
def bo_phan_sua(bid: int, data: BoPhanSuaIn,
                u: User = Depends(require_roles(*GHI_BO_PHAN)), db: Session = Depends(get_db)):
    """Sửa tên / thứ tự / ghi chú, và BẬT-TẮT dùng. MÃ KHÔNG ĐỔI ĐƯỢC — xem dịch vụ."""
    from app.services import bo_phan as BP
    truyen = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        b = BP.sua(db, bid, truyen)
    except ValueError as ex:
        raise HTTPException(404 if "Không có" in str(ex) else 422, str(ex))
    R.audit(db, u.username, u.role, "sua_bo_phan", f"bo_phan:{b.ma}", after=truyen)
    db.commit()
    return {"id": b.id, "ma": b.ma, "dung": b.dung, "message": f"Đã cập nhật bộ phận {b.ma}"}


@router.get("/bo-phan/chua-gan")
def bo_phan_chua_gan(u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Những chữ đang nằm trong sổ mà chưa bộ phận nào nhận. Máy LIỆT KÊ, người CHỌN."""
    from app.services import bo_phan as BP
    return BP.chua_gan(db)


class GanIn(BaseModel):
    chu: str
    ma: str


@router.post("/bo-phan/gan")
def bo_phan_gan(data: GanIn,
                u: User = Depends(require_roles(*GHI_BO_PHAN)), db: Session = Depends(get_db)):
    """Nhận một chữ cũ về làm bút danh. KHÔNG sửa một dòng sổ nào — xem dịch vụ."""
    from app.services import bo_phan as BP
    try:
        ra = BP.gan(db, data.chu, data.ma)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    R.audit(db, u.username, u.role, "gan_but_danh_bo_phan", f"bo_phan:{ra['ma']}",
            after={"chu": data.chu})
    db.commit()
    return {**ra, "message": f"Đã nhận '{data.chu}' về {ra['ma']}"}


@router.delete("/bo-phan/{ma}/but-danh/{chu}")
def bo_phan_bo_but_danh(ma: str, chu: str,
                        u: User = Depends(require_roles(*GHI_BO_PHAN)),
                        db: Session = Depends(get_db)):
    """Gỡ một bút danh. Gán nhầm phải sửa được, nếu không người ta sẽ ngại gán."""
    from app.services import bo_phan as BP
    try:
        ra = BP.bo_but_danh(db, ma, chu)
    except ValueError as ex:
        raise HTTPException(404, str(ex))
    R.audit(db, u.username, u.role, "bo_but_danh_bo_phan", f"bo_phan:{ra['ma']}",
            after={"chu": chu})
    db.commit()
    return {**ra, "message": f"Đã gỡ bút danh '{chu}'"}


# ════════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R4a 15/10/2026 — MA TRẬN CẶP ĐỊNH KHOẢN
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Cùng tiền tố `/api/v1/hach-toan` đã khai, nên KHÔNG nới một quyền nào. Đặt ở đây chứ không ở
# `books.py` là có chủ ý: báo cáo này đọc sổ để ĐỐI CHIẾU VỚI BẢNG QUY ƯỚC, nên nó thuộc về màn
# hình quy ước — người mở nó đang hỏi "bảng quy ước của tôi có khớp với sổ không", không phải
# "cho tôi xem sổ".
#
# CHỈ ĐỌC, cả hai cửa. Không có cửa nào tự thêm một dòng quy ước cho khớp sổ: khớp bằng cách nới
# luật cho vừa thực tế là bỏ mất đúng thứ báo cáo này sinh ra để giữ.
@router.get("/cap-dinh-khoan")
def cap_dinh_khoan(den_ngay: date, tu_ngay: date | None = None,
                   u: User = Depends(require_roles(*XEM)), db: Session = Depends(get_db)):
    """Mọi cặp (Nợ X / Có Y) có thật trong sổ, kèm số tiền và số chứng từ."""
    from app.services import cap_dinh_khoan as CDK
    return CDK.ma_tran(db, den_ngay, tu_ngay)


@router.get("/cap-dinh-khoan/ngoai-luat")
def cap_dinh_khoan_ngoai_luat(den_ngay: date, tu_ngay: date | None = None,
                              u: User = Depends(require_roles(*XEM)),
                              db: Session = Depends(get_db)):
    """Cặp có trong SỔ mà KHÔNG có trong bảng quy ước — chỗ phải nhìn, không phải kết luận."""
    from app.services import cap_dinh_khoan as CDK
    return CDK.ngoai_luat(db, den_ngay, tu_ngay)
