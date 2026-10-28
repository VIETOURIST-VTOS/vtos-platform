"""CD-1 · Cổng Cổ đông đợt 1 — phép tính và hàng rào (Chủ tịch duyệt bản xem thử 28/10/2026).

QUY TẮC (đúng bản xem thử Chủ tịch duyệt):
  1. Tài liệu lên cổng CHỈ từ bản ghi công bố ĐÃ CÔNG BỐ (`ban_ghi_cong_bo.da_cong_bo_luc` có giá trị).
     Không có cửa thứ hai. Tài liệu chưa công bố hiện cho cổ đông là tiết lộ chọn lọc.
  2. IR – Pháp chế đưa lên (kèm tệp PDF, nhóm, phạm vi). Chủ tịch, TGĐ, IR – Pháp chế gỡ ngay — gỡ
     phải có lý do và KHÔNG xoá dòng.
  3. Bản thay: đưa bản mới «thay cho» bản đang hiện; bản cũ đổi sang «đã có bản thay», cổng hiện lịch sử.
  4. Sự kiện do IR – Pháp chế tạo. Cổ đông chỉ «ghi nhận quan tâm» — không phải đăng ký tham dự,
     không phải ủy quyền, không biểu quyết.
  5. Câu hỏi IR có mã IR-xxxx. Gửi trả lời phải xác nhận «không chứa thông tin chưa công bố».
  6. Chỉ tài khoản cổ đông ĐÃ XÁC MINH (hoat_dong) vào được. Tài liệu «Công khai» xem được không cần
     đăng nhập — qua nhóm cửa công khai riêng, có phanh.
  7. Bốn bảng bắt đầu rỗng. Phần mềm không tự điền tài liệu, sự kiện hay số liệu nào.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attachments import Attachment
from app.models.cong_co_dong import (
    CHU_DE_IR,
    LOAI_SU_KIEN,
    NHOM_TAI_LIEU,
    PHAM_VI,
    TRANG_THAI_IR,
    TRANG_THAI_SU_KIEN,
    TRANG_THAI_TAI_LIEU,
    QuanTamSuKien,
    SuKienCoDong,
    TaiLieuCongCoDong,
    YeuCauIr,
)
from app.models.cong_ngoai import TaiKhoanNgoai
from app.models.core import User
from app.models.phap_che import BanGhiCongBo, NghiaVuCongBo
from app.services import attachments as AT
from app.services import rules as R

VAI_XEM = ("chutich", "tgd", "bks", "robot_ks", "ir_phapche")
VAI_GHI = ("ir_phapche",)                          # đưa tài liệu, tạo sự kiện, trả lời IR
VAI_GO = ("chutich", "tgd", "ir_phapche")          # gỡ tài liệu khỏi cổng ngay

TOI_DA_CHO_IR = 5          # câu hỏi đang chờ cùng lúc của một tài khoản
TOI_DA_IR_NGAY = 10        # câu hỏi gửi trong 24 giờ của một tài khoản
DAI_NOI_DUNG = 2000


class LoiCoDong(Exception):
    def __init__(self, msg: str, status: int = 422):
        super().__init__(msg)
        self.status = status


# ====================================================================== cửa vào cổng
def cua_co_dong(tk: TaiKhoanNgoai) -> TaiKhoanNgoai:
    if tk.loai != "co_dong":
        raise LoiCoDong("Mục này dành cho cổ đông", 403)
    if tk.trang_thai != "hoat_dong":
        raise LoiCoDong("Tài khoản cổ đông chưa được IR xác minh", 403)
    return tk


# ====================================================================== tài liệu
def _ra_tl(db: Session, t: TaiLieuCongCoDong, noi_bo: bool = False) -> dict:
    bg = db.get(BanGhiCongBo, t.ban_ghi_id)
    a = db.get(Attachment, t.attachment_id)
    d = {"id": t.id, "tieu_de": t.tieu_de, "nhom": t.nhom, "nhom_ten": NHOM_TAI_LIEU.get(t.nhom, t.nhom),
         "pham_vi": t.pham_vi, "pham_vi_ten": PHAM_VI.get(t.pham_vi, t.pham_vi),
         "da_cong_bo_luc": bg.da_cong_bo_luc if bg else None, "noi_cong_bo": bg.noi_cong_bo if bg else "",
         "nam": bg.da_cong_bo_luc.year if bg and bg.da_cong_bo_luc else None,
         "ten_tep": a.ten_tep if a else "", "kich_thuoc": a.kich_thuoc if a else 0,
         "thay_cho_id": t.thay_cho_id, "ly_do_thay": t.ly_do_thay,
         "trang_thai": t.trang_thai, "trang_thai_ten": TRANG_THAI_TAI_LIEU.get(t.trang_thai, t.trang_thai),
         "dang_luc": t.dang_luc}
    if noi_bo:
        d.update({"ban_ghi_id": t.ban_ghi_id, "dang_boi": t.dang_boi, "go_boi": t.go_boi,
                  "go_luc": t.go_luc, "ly_do_go": t.ly_do_go})
    return d


def _lich_su(db: Session, t: TaiLieuCongCoDong) -> list[dict]:
    """Chuỗi bản thay ngược về bản đầu. Chỉ những bản từng hiện (không tính bản đã gỡ)."""
    ra, seen, cur = [], {t.id}, t
    while cur.thay_cho_id and cur.thay_cho_id not in seen:
        cu = db.get(TaiLieuCongCoDong, cur.thay_cho_id)
        if cu is None:
            break
        seen.add(cu.id)
        bg = db.get(BanGhiCongBo, cu.ban_ghi_id)
        ra.append({"id": cu.id, "tieu_de": cu.tieu_de, "da_cong_bo_luc": bg.da_cong_bo_luc if bg else None,
                   "ly_do_thay_boi_ban_sau": cur.ly_do_thay})
        cur = cu
    return ra


def _duoc_xem(t: TaiLieuCongCoDong, co_dong: bool) -> bool:
    if t.trang_thai not in ("hien", "thay_the"):
        return False
    return t.pham_vi == "cong_khai" or co_dong


def ds_tai_lieu(db: Session, co_dong: bool, nhom: str = "", nam: int | None = None) -> list[dict]:
    """Chỉ bản đang hiện. Bản đã có bản thay đọc được qua lịch sử của bản mới."""
    q = select(TaiLieuCongCoDong).where(TaiLieuCongCoDong.trang_thai == "hien")
    if not co_dong:
        q = q.where(TaiLieuCongCoDong.pham_vi == "cong_khai")
    if nhom:
        q = q.where(TaiLieuCongCoDong.nhom == nhom)
    ds = [_ra_tl(db, t) for t in db.execute(q).scalars()]
    if nam:
        ds = [d for d in ds if d["nam"] == nam]
    ds.sort(key=lambda d: d["da_cong_bo_luc"] or datetime.min, reverse=True)
    return ds


def mot_tai_lieu(db: Session, tid: int, co_dong: bool) -> dict:
    t = db.get(TaiLieuCongCoDong, tid)
    if t is None or not _duoc_xem(t, co_dong):
        raise LoiCoDong("Không có tài liệu này", 404)
    d = _ra_tl(db, t)
    d["lich_su"] = _lich_su(db, t)
    if t.trang_thai == "thay_the":
        moi = db.execute(select(TaiLieuCongCoDong).where(TaiLieuCongCoDong.thay_cho_id == t.id,
                                                         TaiLieuCongCoDong.trang_thai == "hien")).scalars().first()
        d["ban_moi_id"] = moi.id if moi else None
    return d


def tep_tai_lieu(db: Session, tid: int, co_dong: bool) -> tuple[bytes, Attachment]:
    t = db.get(TaiLieuCongCoDong, tid)
    if t is None or not _duoc_xem(t, co_dong):
        raise LoiCoDong("Không có tài liệu này", 404)
    a = db.get(Attachment, t.attachment_id)
    if a is None or a.thu_hoi:
        raise LoiCoDong("Tệp của tài liệu này không còn", 404)
    try:
        return AT.doc(db, a), a
    except Exception as ex:   # lệch băm / kho lỗi: không trả nội dung sai
        raise LoiCoDong(str(ex), 503)


def _ra_bg_ngan(db: Session, bg: BanGhiCongBo) -> dict:
    nv = db.get(NghiaVuCongBo, bg.nghia_vu_id)
    return {"id": bg.id, "ky": bg.ky, "nghia_vu": nv.ten if nv else "", "nghia_vu_ma": nv.ma if nv else "",
            "da_cong_bo_luc": bg.da_cong_bo_luc, "noi_cong_bo": bg.noi_cong_bo}


def quan_tri_tai_lieu(db: Session) -> dict:
    tren_cong = list(db.execute(select(TaiLieuCongCoDong).order_by(TaiLieuCongCoDong.dang_luc.desc())).scalars())
    da_dua = {t.ban_ghi_id for t in tren_cong if t.trang_thai in ("hien", "thay_the")}
    cho = [_ra_bg_ngan(db, b) for b in db.execute(
        select(BanGhiCongBo).where(BanGhiCongBo.da_cong_bo_luc.is_not(None))
        .order_by(BanGhiCongBo.da_cong_bo_luc.desc())).scalars() if b.id not in da_dua]
    return {"cho_dua_len": cho,
            "dang_hien": [_ra_tl(db, t, True) for t in tren_cong if t.trang_thai == "hien"],
            "da_go_hoac_thay": [_ra_tl(db, t, True) for t in tren_cong if t.trang_thai != "hien"],
            "nhom": NHOM_TAI_LIEU, "pham_vi": PHAM_VI}


def dua_len(db: Session, u: User, ban_ghi_id: int, tieu_de: str, nhom: str, pham_vi: str,
            ten_tep: str, kieu: str, data: bytes, thay_cho_id: int | None = None, ly_do_thay: str = "") -> TaiLieuCongCoDong:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế đưa tài liệu lên cổng", 403)
    bg = db.get(BanGhiCongBo, ban_ghi_id)
    if bg is None:
        raise LoiCoDong("Không có bản ghi công bố này", 404)
    if bg.da_cong_bo_luc is None:
        raise LoiCoDong("Bản ghi này CHƯA công bố — ghi lần công bố ở màn IR – Pháp chế trước. "
                        "Tài liệu chưa công bố không được lên cổng cổ đông.")
    if nhom not in NHOM_TAI_LIEU:
        raise LoiCoDong("Nhóm tài liệu không hợp lệ")
    if pham_vi not in PHAM_VI:
        raise LoiCoDong("Phạm vi không hợp lệ")
    tieu_de = (tieu_de or "").strip()
    if not tieu_de:
        raise LoiCoDong("Thiếu tên tài liệu")
    if (ten_tep or "").rsplit(".", 1)[-1].lower() != "pdf":
        raise LoiCoDong("Tài liệu trên cổng phải là tệp PDF")
    dang = db.execute(select(TaiLieuCongCoDong).where(TaiLieuCongCoDong.ban_ghi_id == bg.id,
                                                      TaiLieuCongCoDong.trang_thai.in_(("hien", "thay_the")))).scalars().first()
    if dang is not None:
        raise LoiCoDong("Bản ghi công bố này đã có tài liệu trên cổng", 409)
    cu = None
    if thay_cho_id:
        cu = db.get(TaiLieuCongCoDong, thay_cho_id)
        if cu is None or cu.trang_thai != "hien":
            raise LoiCoDong("Tài liệu được thay không còn đang hiện", 409)
        if not (ly_do_thay or "").strip():
            raise LoiCoDong("Thay một tài liệu đang hiện phải ghi lý do — cổ đông đọc được lý do ấy")
    try:
        a, _moi = AT.dinh_kem(db, "van_ban", f"cong-co-dong-bg{bg.id}", ten_tep, data, kieu=kieu or "application/pdf",
                              loai="chung_tu", mo_ta=f"Cổng cổ đông · {tieu_de[:120]}", boi=u.username)
    except ValueError as ex:
        raise LoiCoDong(str(ex))
    t = TaiLieuCongCoDong(ban_ghi_id=bg.id, tieu_de=tieu_de[:300], nhom=nhom, pham_vi=pham_vi,
                          attachment_id=a.id, thay_cho_id=cu.id if cu else None,
                          ly_do_thay=(ly_do_thay or "").strip()[:2000] if cu else "",
                          trang_thai="hien", dang_boi=u.username, dang_luc=datetime.now())
    db.add(t)
    if cu is not None:
        cu.trang_thai = "thay_the"
    db.flush()
    R.audit(db, u.username, u.role, "cong_co_dong_dua_len", f"tai_lieu_cong_co_dong:{t.id}",
            after={"ban_ghi_id": bg.id, "pham_vi": pham_vi, "thay_cho": t.thay_cho_id, "checksum": a.checksum})
    return t


def go(db: Session, u: User, tid: int, ly_do: str) -> TaiLieuCongCoDong:
    if u.role not in VAI_GO:
        raise LoiCoDong("Không có quyền gỡ tài liệu khỏi cổng", 403)
    t = db.get(TaiLieuCongCoDong, tid)
    if t is None:
        raise LoiCoDong("Không có tài liệu này", 404)
    if t.trang_thai == "go":
        raise LoiCoDong("Tài liệu đã gỡ", 409)
    if not (ly_do or "").strip():
        raise LoiCoDong("Gỡ khỏi cổng phải ghi lý do")
    truoc = t.trang_thai
    t.trang_thai, t.go_boi, t.go_luc, t.ly_do_go = "go", u.username, datetime.now(), ly_do.strip()[:2000]
    # Gỡ bản mới thì bản nó thay quay lại hiện — cổ đông không mất tài liệu đã công bố chỉ vì bản thay bị gỡ.
    if truoc == "hien" and t.thay_cho_id:
        cu = db.get(TaiLieuCongCoDong, t.thay_cho_id)
        if cu is not None and cu.trang_thai == "thay_the":
            cu.trang_thai = "hien"
    db.flush()
    R.audit(db, u.username, u.role, "cong_co_dong_go", f"tai_lieu_cong_co_dong:{t.id}",
            before={"trang_thai": truoc}, after={"ly_do": t.ly_do_go})
    return t


# ====================================================================== sự kiện
def _ra_sk(db: Session, s: SuKienCoDong, tk: TaiKhoanNgoai | None = None, noi_bo: bool = False) -> dict:
    tl = []
    for i in (s.tai_lieu_ids or []):
        t = db.get(TaiLieuCongCoDong, int(i))
        if t is not None and t.trang_thai == "hien":
            tl.append({"id": t.id, "tieu_de": t.tieu_de})
    d = {"id": s.id, "ten": s.ten, "loai": s.loai, "loai_ten": LOAI_SU_KIEN.get(s.loai, s.loai),
         "bat_dau": s.bat_dau, "dia_diem": s.dia_diem, "ngay_chot_ds": s.ngay_chot_ds, "mo_ta": s.mo_ta,
         "tai_lieu": tl, "nhan_quan_tam": s.nhan_quan_tam, "trang_thai": s.trang_thai,
         "trang_thai_ten": TRANG_THAI_SU_KIEN.get(s.trang_thai, s.trang_thai), "ly_do_huy": s.ly_do_huy,
         "da_dien_ra": s.bat_dau < datetime.now()}
    if tk is not None:
        q = db.execute(select(QuanTamSuKien).where(QuanTamSuKien.su_kien_id == s.id,
                                                   QuanTamSuKien.tai_khoan_id == tk.id)).scalars().first()
        d["toi_quan_tam"] = bool(q and q.bo_luc is None)
        d["quan_tam_luc"] = q.luc if q and q.bo_luc is None else None
    if noi_bo:
        rows = list(db.execute(select(QuanTamSuKien).where(QuanTamSuKien.su_kien_id == s.id)).scalars())
        d["so_quan_tam"] = sum(1 for r in rows if r.bo_luc is None)
        d["so_da_rut"] = sum(1 for r in rows if r.bo_luc is not None)
        d["tai_lieu_ids"] = list(s.tai_lieu_ids or [])
        d.update({"tao_boi": s.tao_boi, "tao_luc": s.tao_luc, "sua_boi": s.sua_boi, "sua_luc": s.sua_luc})
    return d


def ds_su_kien_cong(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    """Sự kiện đã thông báo hoặc đã hủy (hủy vẫn hiện để cổ đông biết). Bản nháp không ra cổng.
    Sự kiện đã diễn ra quá 180 ngày thôi hiện."""
    moc = datetime.now() - timedelta(days=180)
    q = (select(SuKienCoDong).where(SuKienCoDong.trang_thai.in_(("cong_bo", "huy")), SuKienCoDong.bat_dau >= moc)
         .order_by(SuKienCoDong.bat_dau))
    ds = [_ra_sk(db, s, tk) for s in db.execute(q).scalars()]
    sap = [d for d in ds if not d["da_dien_ra"]]
    qua = [d for d in ds if d["da_dien_ra"]][::-1]
    return sap + qua


def _kiem_sk(data: dict) -> None:
    if not (data.get("ten") or "").strip():
        raise LoiCoDong("Thiếu tên sự kiện")
    if data.get("loai") not in LOAI_SU_KIEN:
        raise LoiCoDong("Loại sự kiện không hợp lệ")
    if not data.get("bat_dau"):
        raise LoiCoDong("Thiếu thời điểm bắt đầu")


def _tai_lieu_hop_le(db: Session, ids) -> list[int]:
    ra = []
    for i in ids or []:
        t = db.get(TaiLieuCongCoDong, int(i))
        if t is None or t.trang_thai != "hien":
            raise LoiCoDong(f"Tài liệu #{i} không đang hiện trên cổng — không gắn vào sự kiện được")
        ra.append(t.id)
    return ra


def tao_su_kien(db: Session, u: User, data: dict) -> SuKienCoDong:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế tạo sự kiện", 403)
    _kiem_sk(data)
    s = SuKienCoDong(ten=data["ten"].strip()[:200], loai=data["loai"], bat_dau=data["bat_dau"],
                     dia_diem=(data.get("dia_diem") or "").strip()[:200], ngay_chot_ds=data.get("ngay_chot_ds"),
                     mo_ta=(data.get("mo_ta") or "").strip()[:4000],
                     tai_lieu_ids=_tai_lieu_hop_le(db, data.get("tai_lieu_ids")),
                     nhan_quan_tam=bool(data.get("nhan_quan_tam", True)), trang_thai="nhap",
                     tao_boi=u.username, tao_luc=datetime.now())
    db.add(s)
    db.flush()
    R.audit(db, u.username, u.role, "su_kien_co_dong_tao", f"su_kien_co_dong:{s.id}", after={"ten": s.ten})
    return s


def sua_su_kien(db: Session, u: User, sid: int, data: dict) -> SuKienCoDong:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế sửa sự kiện", 403)
    s = db.get(SuKienCoDong, sid)
    if s is None:
        raise LoiCoDong("Không có sự kiện này", 404)
    if s.trang_thai == "huy":
        raise LoiCoDong("Sự kiện đã hủy — tạo sự kiện mới", 409)
    _kiem_sk(data)
    truoc = {"bat_dau": str(s.bat_dau), "dia_diem": s.dia_diem, "ngay_chot_ds": str(s.ngay_chot_ds)}
    s.ten, s.loai, s.bat_dau = data["ten"].strip()[:200], data["loai"], data["bat_dau"]
    s.dia_diem = (data.get("dia_diem") or "").strip()[:200]
    s.ngay_chot_ds = data.get("ngay_chot_ds")
    s.mo_ta = (data.get("mo_ta") or "").strip()[:4000]
    s.tai_lieu_ids = _tai_lieu_hop_le(db, data.get("tai_lieu_ids"))
    s.nhan_quan_tam = bool(data.get("nhan_quan_tam", True))
    s.sua_boi, s.sua_luc = u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, "su_kien_co_dong_sua", f"su_kien_co_dong:{s.id}", before=truoc,
            after={"bat_dau": str(s.bat_dau), "dia_diem": s.dia_diem, "ngay_chot_ds": str(s.ngay_chot_ds)})
    return s


def doi_trang_thai_su_kien(db: Session, u: User, sid: int, trang_thai: str, ly_do: str = "") -> SuKienCoDong:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế đổi trạng thái sự kiện", 403)
    s = db.get(SuKienCoDong, sid)
    if s is None:
        raise LoiCoDong("Không có sự kiện này", 404)
    if trang_thai == "cong_bo":
        if s.trang_thai != "nhap":
            raise LoiCoDong("Chỉ bản nháp mới thông báo được", 409)
    elif trang_thai == "huy":
        if s.trang_thai == "huy":
            raise LoiCoDong("Sự kiện đã hủy", 409)
        if not (ly_do or "").strip():
            raise LoiCoDong("Hủy sự kiện phải ghi lý do — cổ đông đọc được lý do ấy")
        s.ly_do_huy = ly_do.strip()[:2000]
    else:
        raise LoiCoDong("Trạng thái không hợp lệ")
    truoc = s.trang_thai
    s.trang_thai, s.sua_boi, s.sua_luc = trang_thai, u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, f"su_kien_co_dong_{trang_thai}", f"su_kien_co_dong:{s.id}",
            before={"trang_thai": truoc}, after={"ly_do": s.ly_do_huy})
    return s


def quan_tam(db: Session, tk: TaiKhoanNgoai, sid: int, bat: bool) -> dict:
    cua_co_dong(tk)
    s = db.get(SuKienCoDong, sid)
    if s is None or s.trang_thai != "cong_bo":
        raise LoiCoDong("Không có sự kiện này", 404)
    if not s.nhan_quan_tam:
        raise LoiCoDong("Sự kiện này không nhận ghi nhận quan tâm qua cổng", 409)
    if s.bat_dau < datetime.now():
        raise LoiCoDong("Sự kiện đã diễn ra", 409)
    q = db.execute(select(QuanTamSuKien).where(QuanTamSuKien.su_kien_id == s.id,
                                               QuanTamSuKien.tai_khoan_id == tk.id)).scalars().first()
    if bat:
        if q is None:
            db.add(QuanTamSuKien(su_kien_id=s.id, tai_khoan_id=tk.id, luc=datetime.now()))
        elif q.bo_luc is not None:
            q.bo_luc, q.luc = None, datetime.now()
    elif q is not None and q.bo_luc is None:
        q.bo_luc = datetime.now()
    db.flush()
    return _ra_sk(db, s, tk)


def ds_quan_tam(db: Session, sid: int) -> list[dict]:
    s = db.get(SuKienCoDong, sid)
    if s is None:
        raise LoiCoDong("Không có sự kiện này", 404)
    ra = []
    for q in db.execute(select(QuanTamSuKien).where(QuanTamSuKien.su_kien_id == sid)
                        .order_by(QuanTamSuKien.luc)).scalars():
        tk = db.get(TaiKhoanNgoai, q.tai_khoan_id)
        ra.append({"tai_khoan_id": q.tai_khoan_id, "ho_ten": tk.ho_ten if tk else "",
                   "lien_he": (tk.dien_thoai or tk.email) if tk else "", "luc": q.luc, "bo_luc": q.bo_luc})
    return ra


def quan_tri_su_kien(db: Session) -> dict:
    ds = [_ra_sk(db, s, noi_bo=True) for s in db.execute(select(SuKienCoDong).order_by(SuKienCoDong.bat_dau.desc())).scalars()]
    return {"su_kien": ds, "loai": LOAI_SU_KIEN, "trang_thai": TRANG_THAI_SU_KIEN}


# ====================================================================== yêu cầu IR
def _ra_ir(y: YeuCauIr, tk: TaiKhoanNgoai | None = None) -> dict:
    d = {"ma": y.ma, "chu_de": y.chu_de, "chu_de_ten": CHU_DE_IR.get(y.chu_de, y.chu_de), "noi_dung": y.noi_dung,
         "trang_thai": y.trang_thai, "trang_thai_ten": TRANG_THAI_IR.get(y.trang_thai, y.trang_thai),
         "tra_loi": y.tra_loi, "tra_loi_luc": y.tra_loi_luc, "ly_do_dong": y.ly_do_dong, "luc": y.luc}
    d["co_tep"] = y.attachment_id is not None
    if tk is not None:
        d.update({"id": y.id, "ho_ten": tk.ho_ten, "lien_he": tk.dien_thoai or tk.email,
                  "tra_loi_boi": y.tra_loi_boi})
    return d


def gui_ir(db: Session, tk: TaiKhoanNgoai, chu_de: str, noi_dung: str) -> YeuCauIr:
    cua_co_dong(tk)
    if chu_de not in CHU_DE_IR:
        raise LoiCoDong("Chủ đề không hợp lệ")
    noi_dung = (noi_dung or "").strip()
    if len(noi_dung) < 5:
        raise LoiCoDong("Nội dung câu hỏi quá ngắn")
    if len(noi_dung) > DAI_NOI_DUNG:
        raise LoiCoDong(f"Nội dung tối đa {DAI_NOI_DUNG} ký tự")
    cho = db.execute(select(func.count()).select_from(YeuCauIr).where(
        YeuCauIr.tai_khoan_id == tk.id, YeuCauIr.trang_thai == "cho")).scalar() or 0
    if cho >= TOI_DA_CHO_IR:
        raise LoiCoDong(f"Bạn đang có {cho} câu hỏi chờ IR trả lời — đợi trả lời rồi gửi tiếp", 429)
    ngay = db.execute(select(func.count()).select_from(YeuCauIr).where(
        YeuCauIr.tai_khoan_id == tk.id, YeuCauIr.luc >= datetime.now() - timedelta(days=1))).scalar() or 0
    if ngay >= TOI_DA_IR_NGAY:
        raise LoiCoDong("Đã gửi nhiều câu hỏi trong 24 giờ — thử lại sau", 429)
    so = (db.execute(select(func.max(YeuCauIr.id))).scalar() or 0) + 1
    y = YeuCauIr(ma=f"IR-{so:04d}", tai_khoan_id=tk.id, chu_de=chu_de, noi_dung=noi_dung,
                 trang_thai="cho", luc=datetime.now())
    db.add(y)
    db.flush()
    return y


def ir_cua_toi(db: Session, tk: TaiKhoanNgoai) -> list[dict]:
    cua_co_dong(tk)
    return [_ra_ir(y) for y in db.execute(select(YeuCauIr).where(YeuCauIr.tai_khoan_id == tk.id)
                                          .order_by(YeuCauIr.luc.desc())).scalars()]


def quan_tri_ir(db: Session) -> dict:
    ds = []
    for y in db.execute(select(YeuCauIr).order_by(YeuCauIr.luc.desc())).scalars():
        ds.append(_ra_ir(y, db.get(TaiKhoanNgoai, y.tai_khoan_id) or TaiKhoanNgoai()))
    return {"yeu_cau": ds, "so_cho": sum(1 for d in ds if d["trang_thai"] == "cho"), "chu_de": CHU_DE_IR}


def tra_loi_ir(db: Session, u: User, yid: int, tra_loi: str, xac_nhan: bool) -> YeuCauIr:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế trả lời", 403)
    y = db.get(YeuCauIr, yid)
    if y is None:
        raise LoiCoDong("Không có yêu cầu này", 404)
    if y.trang_thai != "cho":
        raise LoiCoDong("Yêu cầu này đã xử lý", 409)
    tra_loi = (tra_loi or "").strip()
    if len(tra_loi) < 5:
        raise LoiCoDong("Thiếu nội dung trả lời")
    if not xac_nhan:
        raise LoiCoDong("Phải xác nhận câu trả lời không chứa thông tin chưa công bố")
    y.tra_loi, y.xac_nhan_da_cong_bo = tra_loi[:DAI_NOI_DUNG * 2], True
    y.trang_thai, y.tra_loi_boi, y.tra_loi_luc = "da_tra_loi", u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, "yeu_cau_ir_tra_loi", f"yeu_cau_ir:{y.ma}",
            after={"xac_nhan_da_cong_bo": True, "do_dai": len(y.tra_loi)})
    return y


def dong_ir(db: Session, u: User, yid: int, ly_do: str) -> YeuCauIr:
    if u.role not in VAI_GHI:
        raise LoiCoDong("Chỉ IR – Pháp chế đóng yêu cầu", 403)
    y = db.get(YeuCauIr, yid)
    if y is None:
        raise LoiCoDong("Không có yêu cầu này", 404)
    if y.trang_thai != "cho":
        raise LoiCoDong("Yêu cầu này đã xử lý", 409)
    if not (ly_do or "").strip():
        raise LoiCoDong("Đóng không trả lời phải ghi lý do — cổ đông đọc được lý do ấy")
    y.trang_thai, y.ly_do_dong, y.tra_loi_boi, y.tra_loi_luc = "dong", ly_do.strip()[:2000], u.username, datetime.now()
    db.flush()
    R.audit(db, u.username, u.role, "yeu_cau_ir_dong", f"yeu_cau_ir:{y.ma}", after={"ly_do": y.ly_do_dong})
    return y


# ====================================================================== tổng quan CD01
def tong_quan(db: Session, tk: TaiKhoanNgoai) -> dict:
    cua_co_dong(tk)
    sk = [d for d in ds_su_kien_cong(db, tk) if not d["da_dien_ra"] and d["trang_thai"] == "cong_bo"]
    ir = ir_cua_toi(db, tk)
    return {"tai_lieu_moi": ds_tai_lieu(db, True)[:3], "su_kien_sap_toi": sk[0] if sk else None,
            "ir_cho": sum(1 for d in ir if d["trang_thai"] == "cho"), "ir_moi_nhat": ir[0] if ir else None,
            "nhom": NHOM_TAI_LIEU, "chu_de_ir": CHU_DE_IR}


def nam_co_tai_lieu(db: Session, co_dong: bool) -> list[int]:
    return sorted({d["nam"] for d in ds_tai_lieu(db, co_dong) if d["nam"]}, reverse=True)

