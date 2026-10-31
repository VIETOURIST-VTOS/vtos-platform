"""KS-16f · Video khách sạn VTD và nhà hàng (Chủ tịch duyệt bản xem thử 31/10/2026).

Đường tải: bắt đầu (máy kiểm số lượng / dung lượng / quyền dùng) → gửi từng phần 8 MB → xong (ghép trên kho) →
ảnh đại diện (trình duyệt chụp khung hình, máy làm nhẹ WEBP). Máy chủ chỉ giữ một phần trong bộ nhớ mỗi lần.

Đường xem: cổng khách chỉ xem video ĐANG HIỆN của cơ sở ĐANG HIỆN; VTOS xem mọi video qua đường có chữ ký ngắn hạn
(thẻ <video> không gửi được phiên đăng nhập). Kho R2: chuyển hướng sang đường tạm có chữ ký — trình duyệt tua thẳng
từ kho, máy chủ không gánh băng thông.
"""
import hashlib
import hmac
import time
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.core import User
from app.models.video_dich_vu import (CHUAN_KS, CHUAN_NH, GOI_Y_GIAY, LOAI_VIDEO_KS, LOAI_VIDEO_NH, TRANG_THAI_VIDEO,
                                      VideoDichVu)
from app.services import rules as R
from app.services.storage import StorageError, storage

TOI_DA = 5
TOI_DA_BYTE = 100 * 1024 * 1024
PHAN_BYTE = 8 * 1024 * 1024
DUOI = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm", "m4v": "video/mp4"}
HAN_LINK = 3600


class LoiVideo(ValueError):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _cfg(doi: str) -> dict:
    if doi == "khach_san_vtd":
        from app.services import khach_san_vtd as K
        return {"nhap": K.VAI_NHAP, "quan": K.VAI_DUYET, "xem": K.VAI_XEM, "loai": LOAI_VIDEO_KS, "chuan": CHUAN_KS,
                "ten": "khách sạn", "anh_doi": "khach_san_vtd", "anh_ma": "ks", "cong": "/api/v1/ks-vtd-anh/video",
                "noi": "/api/v1/khach-san-vtd/video"}
    if doi == "nha_hang":
        from app.services import nha_hang as N
        return {"nhap": N.VAI_ANH_NH, "quan": N.VAI_DUYET_ANH, "xem": N.VAI_XEM, "loai": LOAI_VIDEO_NH, "chuan": CHUAN_NH,
                "ten": "nhà hàng", "anh_doi": "am_thuc", "anh_ma": "nh", "cong": "/api/v1/am-thuc/video",
                "noi": "/api/v1/nha-hang/video"}
    raise LoiVideo("Không có loại cơ sở này", 404)


def _co(u: User | None, vai: tuple) -> bool:
    return u is not None and u.role in vai


def _quyen(u: User, vai: tuple, loi: str) -> None:
    if not _co(u, vai):
        raise LoiVideo(loi, 403)


def _co_so(db: Session, doi: str, oid: int):
    if doi == "khach_san_vtd":
        from app.models.khach_san_vtd import KhachSanVtd as M
    else:
        from app.models.nha_hang import NhaHang as M
    x = db.get(M, oid)
    if x is None:
        raise LoiVideo(f"Không có {_cfg(doi)['ten']} này", 404)
    return x


def _cua(db: Session, doi: str, oid: int, ca_dang_tai: bool = True) -> list[VideoDichVu]:
    tt = ("dang_tai", "hien", "an") if ca_dang_tai else ("hien", "an")
    return db.execute(select(VideoDichVu).where(VideoDichVu.doi_tuong == doi, VideoDichVu.doi_tuong_id == oid,
                                                VideoDichVu.trang_thai.in_(tt))
                      .order_by(VideoDichVu.la_gioi_thieu.desc(), VideoDichVu.thu_tu, VideoDichVu.id)).scalars().all()


def _lay(db: Session, vid: int) -> VideoDichVu:
    v = db.get(VideoDichVu, vid)
    if v is None or v.trang_thai == "xoa":
        raise LoiVideo("Không có video này", 404)
    return v


# ── đường xem có chữ ký ngắn hạn (VTOS) ─────────────────────────────────────────────────────────────
def _ky(vid: int, het: int) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"video:{vid}:{het}".encode(), hashlib.sha256).hexdigest()[:32]


def ve(vid: int, giay: int = HAN_LINK, now: float | None = None) -> str:
    het = int((now or time.time()) + giay)
    return f"{het}.{_ky(vid, het)}"


def ve_hop_le(vid: int, t: str, now: float | None = None) -> bool:
    try:
        het, k = t.split(".", 1)
        return int(het) >= int(now or time.time()) and hmac.compare_digest(k, _ky(vid, int(het)))
    except Exception:
        return False


def _gan(db: Session, doi: str, oid: int, d: dict) -> dict:
    """Kiểm loại nội dung + đối tượng gắn (loại phòng / món / thực đơn thuộc đúng cơ sở)."""
    c = _cfg(doi)
    loai = str(d.get("loai") or "khac")
    if loai not in c["loai"]:
        raise LoiVideo("Chọn loại nội dung video")
    o = {"loai": loai, "loai_phong_id": None, "mon_id": None, "thuc_don_id": None}

    def _id(k):
        v = d.get(k)
        return int(v) if v not in (None, "", 0, "0") else None
    if doi == "khach_san_vtd" and loai == "phong" and _id("loai_phong_id"):
        from app.models.khach_san_vtd import LoaiPhongVtd
        lp = db.get(LoaiPhongVtd, _id("loai_phong_id"))
        if lp is None or lp.khach_san_id != oid:
            raise LoiVideo("Loại phòng không thuộc khách sạn này")
        o["loai_phong_id"] = lp.id
    if doi == "nha_hang" and loai == "mon" and _id("mon_id"):
        from app.models.nha_hang import MonNhaHang
        m = db.get(MonNhaHang, _id("mon_id"))
        if m is None or m.nha_hang_id != oid:
            raise LoiVideo("Món không thuộc nhà hàng này")
        o["mon_id"] = m.id
    if doi == "nha_hang" and loai == "thuc_don" and _id("thuc_don_id"):
        from app.models.nha_hang import ThucDonNhaHang
        t = db.get(ThucDonNhaHang, _id("thuc_don_id"))
        if t is None or t.nha_hang_id != oid:
            raise LoiVideo("Thực đơn không thuộc nhà hàng này")
        o["thuc_don_id"] = t.id
    return o


def _out(v: VideoDichVu, cong: bool = False) -> dict:
    c = _cfg(v.doi_tuong)
    if cong:
        goc, q = c["cong"], ""
    else:
        goc, q = c["cong"], f"?t={ve(v.id)}"
    o = {"id": v.id, "loai": v.loai, "loai_ten": c["loai"].get(v.loai, v.loai), "tieu_de": v.tieu_de,
         "thoi_luong": v.thoi_luong, "la_gioi_thieu": v.la_gioi_thieu, "loai_phong_id": v.loai_phong_id,
         "mon_id": v.mon_id, "thuc_don_id": v.thuc_don_id, "kieu": v.kieu,
         "xem": f"{goc}/{v.id}/xem{q}", "anh": (f"{goc}/{v.id}/anh{q}" if v.anh_id else None)}
    if not cong:
        lo = GOI_Y_GIAY.get(v.loai, (30, 90))
        o.update({"trang_thai": v.trang_thai, "trang_thai_ten": TRANG_THAI_VIDEO.get(v.trang_thai, v.trang_thai),
                  "nguon": v.nguon, "ten_tep": v.ten_tep, "kich_thuoc": v.kich_thuoc, "tai_boi": v.tai_boi,
                  "tai_luc": v.tai_luc.isoformat(timespec="minutes") if v.tai_luc else None, "thu_tu": v.thu_tu,
                  "so_phan": len(v.phan or []),
                  "goi_y": (f"Gợi ý {lo[0]}–{lo[1]} giây" if v.thoi_luong and not (lo[0] <= v.thoi_luong <= lo[1] + 15) else "")})
    return o


# ══ VTOS ══════════════════════════════════════════════════════════════════════════════════════
def ds(db: Session, u: User, doi: str, oid: int) -> dict:
    c = _cfg(doi)
    _quyen(u, c["xem"], "Không có quyền xem video")
    _co_so(db, doi, oid)
    vs = _cua(db, doi, oid)
    hien = [v for v in vs if v.trang_thai == "hien"]
    co = {v.loai for v in hien}
    return {"video": [_out(v) for v in vs], "toi_da": TOI_DA, "toi_da_mb": TOI_DA_BYTE // (1024 * 1024),
            "phan_mb": PHAN_BYTE // (1024 * 1024), "duoi": sorted(DUOI), "loai": c["loai"],
            "chuan": [{"loai": k, "ten": c["loai"][k], "co": k in co} for k in c["chuan"]],
            "du_chuan": all(k in co for k in c["chuan"]), "duoc_nhap": _co(u, c["nhap"]), "duoc_quan": _co(u, c["quan"]),
            "toi": u.username}


def bat_dau(db: Session, u: User, doi: str, oid: int, d: dict, now: datetime | None = None) -> VideoDichVu:
    c = _cfg(doi)
    _quyen(u, c["nhap"], f"Không có quyền tải video {c['ten']}")
    _co_so(db, doi, oid)
    ten = str(d.get("ten_tep") or "").strip()[:200]
    duoi = ten.rsplit(".", 1)[-1].lower() if "." in ten else ""
    if duoi not in DUOI:
        raise LoiVideo("Chỉ nhận video MP4, MOV hoặc WebM")
    kt = int(d.get("kich_thuoc") or 0)
    if kt <= 0 or kt > TOI_DA_BYTE:
        raise LoiVideo(f"Video tối đa {TOI_DA_BYTE // (1024 * 1024)} MB — tệp này {kt / 1048576:.0f} MB")
    if len(_cua(db, doi, oid)) >= TOI_DA:
        raise LoiVideo(f"Đã đủ {TOI_DA} video — xóa video cũ trước khi tải thêm")
    nguon = str(d.get("nguon") or "").strip()[:200]
    if not nguon:
        raise LoiVideo("Ghi nguồn video (khách sạn / nhà hàng gửi, VTD quay…)")
    if not d.get("xac_nhan_quyen"):
        raise LoiVideo("Xác nhận Vietourist được phép dùng video này cho khách xem")
    g = _gan(db, doi, oid, d)
    key = f"video/{doi}/{oid}/{uuid.uuid4().hex}.{duoi}"
    try:
        ma = storage().mp_bat_dau(key, DUOI[duoi])
    except StorageError as ex:
        raise LoiVideo(str(ex), 503)
    v = VideoDichVu(doi_tuong=doi, doi_tuong_id=oid, **g, tieu_de=str(d.get("tieu_de") or "").strip()[:160], nguon=nguon,
                    xac_nhan_quyen=True, ten_tep=ten, kieu=DUOI[duoi], kich_thuoc=kt,
                    thoi_luong=max(0, int(float(d.get("thoi_luong") or 0))), khoa_luu=key, ma_tai=ma, phan=[],
                    trang_thai="dang_tai", tai_boi=u.username, tai_luc=now or datetime.now())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _cua_minh(u: User, v: VideoDichVu) -> None:
    c = _cfg(v.doi_tuong)
    if not (v.tai_boi == u.username and _co(u, c["nhap"])) and not _co(u, c["quan"]):
        raise LoiVideo("Chỉ người tải hoặc TP Điều hành / Chủ tịch / TGĐ được làm việc này", 403)


def nhan_phan(db: Session, u: User, vid: int, so: int, data: bytes) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai != "dang_tai":
        raise LoiVideo("Video đã tải xong", 409)
    toi_da_phan = -(-v.kich_thuoc // PHAN_BYTE)
    if not (1 <= so <= toi_da_phan):
        raise LoiVideo("Số phần không hợp lệ")
    if not data or len(data) > PHAN_BYTE:
        raise LoiVideo(f"Mỗi phần tối đa {PHAN_BYTE // 1048576} MB")
    try:
        et = storage().mp_phan(v.khoa_luu, v.ma_tai, so, data)
    except StorageError as ex:
        raise LoiVideo(str(ex), 503)
    v.phan = [p for p in (v.phan or []) if p[0] != so] + [[so, et]]       # gửi lại một phần = thay phần cũ
    db.commit()
    return v


def xong(db: Session, u: User, vid: int, now: datetime | None = None) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai != "dang_tai":
        raise LoiVideo("Video đã tải xong", 409)
    can = -(-v.kich_thuoc // PHAN_BYTE)
    co = sorted(p[0] for p in (v.phan or []))
    if co != list(range(1, can + 1)):
        thieu = sorted(set(range(1, can + 1)) - set(co))
        raise LoiVideo(f"Còn thiếu phần {', '.join(map(str, thieu[:5]))} — gửi tiếp rồi bấm xong", 409)
    try:
        kt = storage().mp_xong(v.khoa_luu, v.ma_tai, [tuple(p) for p in v.phan])
    except StorageError as ex:
        raise LoiVideo(str(ex), 503)
    if kt > TOI_DA_BYTE:
        storage().xoa(v.khoa_luu)
        v.trang_thai = "xoa"
        db.commit()
        raise LoiVideo("Video vượt 100 MB — đã hủy")
    ds_ = [x for x in _cua(db, v.doi_tuong, v.doi_tuong_id, ca_dang_tai=False)]
    v.kich_thuoc, v.trang_thai, v.xong_luc = kt, "hien", now or datetime.now()
    v.thu_tu = max([x.thu_tu for x in ds_], default=0) + 1
    v.la_gioi_thieu = not any(x.la_gioi_thieu and x.trang_thai == "hien" for x in ds_)   # video đầu tiên = giới thiệu
    v.ma_tai, v.phan = "", []
    R.audit(db, u.username, u.role, "video_tai_len", f"video:{v.id}",
            after={"doi_tuong": v.doi_tuong, "id": v.doi_tuong_id, "loai": v.loai, "mb": round(kt / 1048576, 1), "nguon": v.nguon})
    db.commit()
    db.refresh(v)
    return v


def huy(db: Session, u: User, vid: int) -> None:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai != "dang_tai":
        raise LoiVideo("Chỉ hủy video đang tải dở — video đã xong thì bấm Xóa", 409)
    storage().mp_huy(v.khoa_luu, v.ma_tai)
    v.trang_thai = "xoa"
    db.commit()


def anh_dai_dien(db: Session, u: User, vid: int, ten_tep: str, data: bytes) -> VideoDichVu:
    from app.services import attachments as AT
    from app.services.nha_hang import _lam_nhe
    v = _lay(db, vid)
    _cua_minh(u, v)
    if not data or len(data) > 8 * 1024 * 1024:
        raise LoiVideo("Ảnh đại diện tối đa 8 MB")
    hien, _nho, _r, _c = _lam_nhe(data)
    if hien is None:
        raise LoiVideo("Tệp không mở được như một ảnh")
    c = _cfg(v.doi_tuong)
    try:
        a, _ = AT.dinh_kem(db, c["anh_doi"], f"{c['anh_ma']}{v.doi_tuong_id}", f"video{v.id}.anh.webp", hien,
                           kieu="image/webp", loai="hinh_anh", mo_ta=f"Ảnh đại diện video {v.id}", boi=u.username,
                           nguon="he_thong")
    except ValueError as ex:
        raise LoiVideo(str(ex))
    v.anh_id = a.id
    db.commit()
    return v


def sua(db: Session, u: User, vid: int, d: dict) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if "loai" in d:
        for k, x in _gan(db, v.doi_tuong, v.doi_tuong_id, d).items():
            setattr(v, k, x)
    if "tieu_de" in d:
        v.tieu_de = str(d.get("tieu_de") or "").strip()[:160]
    if "nguon" in d:
        n = str(d.get("nguon") or "").strip()[:200]
        if not n:
            raise LoiVideo("Nguồn video không được để trống")
        v.nguon = n
    db.commit()
    return v


def an(db: Session, u: User, vid: int, an_: bool) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai == "dang_tai":
        raise LoiVideo("Video chưa tải xong", 409)
    v.trang_thai, v.an_boi = ("an", u.username) if an_ else ("hien", "")
    if an_ and v.la_gioi_thieu:
        v.la_gioi_thieu = False
        khac = next((x for x in _cua(db, v.doi_tuong, v.doi_tuong_id, False) if x.id != v.id and x.trang_thai == "hien"), None)
        if khac:
            khac.la_gioi_thieu = True
    R.audit(db, u.username, u.role, "video_an" if an_ else "video_hien", f"video:{v.id}")
    db.commit()
    return v


def xoa(db: Session, u: User, vid: int) -> int:
    """Xóa khỏi danh sách (người tải hoặc TP ĐH / CT / TGĐ). Tệp vẫn giữ trong kho để đối chiếu, như ảnh album."""
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai == "dang_tai":
        huy(db, u, vid)
        return v.doi_tuong_id
    gt = v.la_gioi_thieu
    v.trang_thai, v.la_gioi_thieu, v.an_boi = "xoa", False, u.username
    if gt:
        khac = next((x for x in _cua(db, v.doi_tuong, v.doi_tuong_id, False) if x.trang_thai == "hien"), None)
        if khac:
            khac.la_gioi_thieu = True
    R.audit(db, u.username, u.role, "video_xoa", f"video:{v.id}", after={"tai_boi": v.tai_boi})
    db.commit()
    return v.doi_tuong_id


def dat_gioi_thieu(db: Session, u: User, vid: int) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    if v.trang_thai != "hien":
        raise LoiVideo("Chỉ video đang hiện mới làm video giới thiệu", 409)
    for x in _cua(db, v.doi_tuong, v.doi_tuong_id, False):
        x.la_gioi_thieu = x.id == v.id
    db.commit()
    return v


def doi_thu_tu(db: Session, u: User, vid: int, len_: bool) -> VideoDichVu:
    v = _lay(db, vid)
    _cua_minh(u, v)
    ds_ = [x for x in _cua(db, v.doi_tuong, v.doi_tuong_id, False)]
    ds_.sort(key=lambda x: (x.thu_tu, x.id))
    i = ds_.index(v)
    j = i - 1 if len_ else i + 1
    if 0 <= j < len(ds_):
        ds_[i], ds_[j] = ds_[j], ds_[i]
        for k, x in enumerate(ds_):
            x.thu_tu = k + 1
    db.commit()
    return v


# ══ XEM (cổng + VTOS có vé) ═════════════════════════════════════════════════════════════════════
def _xem_duoc(db: Session, v: VideoDichVu, t: str = "") -> None:
    if t and ve_hop_le(v.id, t):
        return
    o = _co_so(db, v.doi_tuong, v.doi_tuong_id)
    if v.trang_thai != "hien" or not getattr(o, "hien_cong", False) or getattr(o, "ngung", False):
        raise LoiVideo("Không có video này", 404)


def tep_xem(db: Session, vid: int, doi: str, t: str = "") -> dict:
    """→ {"url": đường tạm có chữ ký trên kho} hoặc {"duong": tệp trên đĩa, "kieu": …} (kho cục bộ — có hỗ trợ tua)."""
    v = _lay(db, vid)
    if v.doi_tuong != doi or v.trang_thai == "dang_tai":
        raise LoiVideo("Không có video này", 404)
    _xem_duoc(db, v, t)
    st = storage()
    try:
        url = st.link_tam(v.khoa_luu, HAN_LINK, v.kieu)
    except StorageError as ex:
        raise LoiVideo(str(ex), 503)
    if url:
        return {"url": url}
    return {"duong": st.duong_tep(v.khoa_luu), "kieu": v.kieu}


def tep_anh(db: Session, vid: int, doi: str, t: str = ""):
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    v = _lay(db, vid)
    if v.doi_tuong != doi or not v.anh_id:
        raise LoiVideo("Không có ảnh này", 404)
    _xem_duoc(db, v, t)
    a = db.get(Attachment, v.anh_id)
    return AT.doc(db, a), a


def video_cong(db: Session, doi: str, ids: list[int]) -> dict[int, list[dict]]:
    """Video ĐANG HIỆN theo cơ sở (giới thiệu trước). Cơ sở có đang hiện hay không do nơi gọi đã lọc."""
    if not ids:
        return {}
    ra: dict[int, list[dict]] = {}
    for v in db.execute(select(VideoDichVu).where(VideoDichVu.doi_tuong == doi, VideoDichVu.doi_tuong_id.in_(ids),
                                                  VideoDichVu.trang_thai == "hien")
                        .order_by(VideoDichVu.la_gioi_thieu.desc(), VideoDichVu.thu_tu, VideoDichVu.id)).scalars():
        ra.setdefault(v.doi_tuong_id, []).append(_out(v, cong=True))
    return ra
