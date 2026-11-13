# -*- coding: utf-8 -*-
"""TR-8 (13/11/2026) · ALBUM ẢNH TOUR — nghiệp vụ.

VÌ SAO CÓ VÒNG NÀY. Đo trên `kh.vietourist.vn/tours` ngày 13/11/2026: **13 trong 85 tour không
có một tấm ảnh nào**, và trong 33 tour đang có chuyến mở bán thì 22 tour thiếu ảnh. Nội dung
đọc từ `vietourist.com.vn` (Chủ tịch chốt mục 12 của KS-71), nên chất lượng ảnh bị chặn trần
bởi web cũ và KHÔNG sửa được bằng mã — chỉ sửa được bằng một cửa để người của anh tải ảnh lên.
Theo ranh giới Chủ tịch chốt 09/9/2026: Claude viết CỬA, người của anh đưa ẢNH vào.

BỐN QUYẾT ĐỊNH CỦA CHỦ TỊCH, 13/11/2026 — ghi ra để sau này không ai đoán lại:
 (1) ẢNH TẢI LÊN ĐỨNG TRƯỚC, ẢNH WEB NỐI SAU. Không xoá ảnh web nào. Phòng sản phẩm vá được
     tour nào hay tour ấy, không phải chờ đủ bộ mới dùng được, và không mất gì nếu dừng giữa chừng.
 (2) KHÔNG CÓ BƯỚC DUYỆT — tải là hiện, đúng bằng luật KS-16c đã chốt cho cổng nhà hàng
     31/10/2026. `trang_thai` vẫn còn, nhưng chỉ để GỠ NHANH một tấm ảnh sai sang «an».
 (3) BA PHÒNG TẢI ĐƯỢC: Marketing, Điều hành, Kinh doanh.
 (4) Lõi xử lý ảnh DÙNG CHUNG với cổng nhà hàng (`anh_chung.py`), không chép lại.

ĐIỀU KHÔNG PHẢI DO AI YÊU CẦU MÀ VẪN PHẢI CÓ: cột `can_cu` — ảnh này ở đâu ra, ai cho phép
dùng. Đăng một tấm ảnh không rõ nguồn lên internet thay mặt một công ty niêm yết là rủi ro
thật. Hệ nhà hàng đã có cột ấy từ 29/10; cổng tour không được kém hơn.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anh_tour import (ANH_TOI_DA_SO, CAN_CU_ANH_TOUR, NHOM_ANH_TOUR, TRANG_THAI_ANH_TOUR,
                                 AnhTour)
from app.models.core import Product, User
from app.services import anh_chung as AC
from app.services import rules as R
from app.services.tour_online import TOAN_QUYEN, VAI_SUA_CONG, VAI_XEM, LoiTour

VAI_ANH = tuple(dict.fromkeys(VAI_SUA_CONG + ("tp_kd", "gd_kd")))   # Marketing · Điều hành · Kinh doanh
VAI_GO = TOAN_QUYEN + ("ptgd_mkt", "tp_dh")                          # gỡ / xoá ảnh của NGƯỜI KHÁC

MA_TRAN_ANH = {
    "Xem album ảnh tour": VAI_XEM,
    "Tải ảnh tour · sửa chú thích · xếp thứ tự": VAI_ANH,
    "Ẩn hoặc xoá ảnh của người khác": VAI_GO,
}


def _co(u: User, vai: tuple) -> bool:
    return bool(u is not None and u.role in vai)


def _quyen(u: User, vai: tuple, msg: str) -> None:
    if not _co(u, vai):
        raise LoiTour(msg, 403)


def _sp(db: Session, pid: int) -> Product:
    p = db.get(Product, pid)
    if p is None:
        raise LoiTour("Không có sản phẩm này", 404)
    return p


def _lay(db: Session, aid: int) -> AnhTour:
    x = db.get(AnhTour, aid)
    if x is None:
        raise LoiTour("Không có ảnh này", 404)
    return x


def _cua(db: Session, pid: int) -> list[AnhTour]:
    return db.execute(select(AnhTour).where(AnhTour.product_id == pid)
                      .order_by(AnhTour.thu_tu, AnhTour.id)).scalars().all()


def _kiem_can_cu(can_cu: str, nhom: str) -> None:
    if can_cu not in CAN_CU_ANH_TOUR:
        raise LoiTour("Chọn căn cứ quyền dùng ảnh: " + " / ".join(CAN_CU_ANH_TOUR.values()))
    if nhom and nhom not in NHOM_ANH_TOUR:
        raise LoiTour("Nhóm ảnh không hợp lệ")


def duong(x: AnhTour) -> dict:
    """Ba đường đọc CHO NGƯỜI TRONG NHÀ (đòi đăng nhập). Màn quản lý phải xem được cả ảnh đang
    ẩn để còn bật lại, nên nó dùng bộ này chứ không dùng đường công khai."""
    # Bộ định tuyến sản phẩm gắn ở `/api/v1`, KHÔNG phải `/api/v1/products` — viết nhầm tiền tố
    # này một lần rồi (12/11/2026, cửa trả 422 mà không ai hiểu vì sao). Đường dưới đây đã đối
    # chiếu với bảng đường thật của ứng dụng, không viết theo trí nhớ.
    return {"nho": f"/api/v1/tour-online/anh/{x.id}/nho",
            "hien": f"/api/v1/tour-online/anh/{x.id}/hien",
            "goc": f"/api/v1/tour-online/anh/{x.id}/goc"}


def duong_khach(x: AnhTour) -> str:
    """Đường ảnh CHO CỔNG KHÁCH — cửa công khai, và chỉ bản hiển thị.

    Hai đường tách hẳn nhau là có chủ ý: cửa công khai tự kiểm `trang_thai` và không bao giờ
    trả bản gốc, nên một tấm ảnh bị gỡ là biến mất khỏi cổng ngay, không cần đổi gì ở màn khách.
    """
    return f"/api/v1/cong/mo/tour-online/anh/{x.id}/hien"


def _ra(x: AnhTour, goc=None) -> dict:
    return {"id": x.id, "product_id": x.product_id, "nhom": x.nhom,
            "nhom_ten": NHOM_ANH_TOUR.get(x.nhom, "Chưa phân nhóm"),
            "chu_thich": x.chu_thich, "mo_ta_thay_the": x.mo_ta_thay_the, "thu_tu": x.thu_tu,
            "la_bia": x.la_bia, "can_cu": x.can_cu, "can_cu_ten": CAN_CU_ANH_TOUR.get(x.can_cu, x.can_cu),
            "can_cu_ghi_chu": x.can_cu_ghi_chu, "credit": x.credit,
            "trang_thai": x.trang_thai, "trang_thai_ten": TRANG_THAI_ANH_TOUR.get(x.trang_thai, x.trang_thai),
            "tai_boi": x.tai_boi, "tai_luc": x.tai_luc.isoformat(timespec="minutes") if x.tai_luc else None,
            "rong": x.rong, "cao": x.cao,
            "ten_tep": getattr(goc, "ten_tep", "") or "", "kich_thuoc": getattr(goc, "kich_thuoc", 0) or 0,
            **duong(x)}


# ── ĐỌC ──────────────────────────────────────────────────────────────────────────────────────

def album(db: Session, u: User, pid: int) -> dict:
    from app.models.attachments import Attachment
    _quyen(u, VAI_XEM, "Không có quyền xem album ảnh tour")
    p = _sp(db, pid)
    ds = _cua(db, pid)
    goc = {a.id: a for a in db.execute(select(Attachment).where(
        Attachment.id.in_([x.attachment_id for x in ds]))).scalars()} if ds else {}
    nd = p.noi_dung_web or {}
    return {"san_pham": {"id": p.id, "ma": p.code, "ten": p.name},
            "anh": [_ra(x, goc.get(x.attachment_id)) for x in ds],
            "tong": len(ds), "toi_da": ANH_TOI_DA_SO, "toi_da_mb": AC.TOI_DA_MB,
            "so_anh_web": len(nd.get("anh") or []),
            "nhom_anh": NHOM_ANH_TOUR, "can_cu_anh": CAN_CU_ANH_TOUR,
            "duoc_tai": _co(u, VAI_ANH), "duoc_go": _co(u, VAI_GO), "toi": u.username}


def album_cong(db: Session, pids: list[int]) -> dict[int, list[AnhTour]]:
    """Ảnh ĐANG HIỆN của nhiều sản phẩm, cho cổng khách. Ảnh «an» và ảnh nháp không ra ngoài."""
    if not pids:
        return {}
    ds = db.execute(select(AnhTour).where(AnhTour.product_id.in_(pids), AnhTour.trang_thai == "da_duyet")
                    .order_by(AnhTour.thu_tu, AnhTour.id)).scalars().all()
    ra: dict[int, list[AnhTour]] = {}
    for x in ds:
        ra.setdefault(x.product_id, []).append(x)
    return ra


def duong_cong(db: Session, pids: list[int]) -> dict[int, list[str]]:
    """Đường ảnh cho cổng khách — BẢN HIỂN THỊ, không bao giờ bản gốc."""
    return {pid: [duong_khach(x) for x in ds] for pid, ds in album_cong(db, pids).items()}


def tep(db: Session, u: User | None, aid: int, co: str):
    """Một tệp ảnh. u=None nghĩa là cổng công khai: chỉ ảnh đang hiện, và KHÔNG BAO GIỜ bản gốc.

    Bản gốc mang kích thước thật và tên tệp người tải đặt; nó là tài sản nội bộ, không phải thứ
    đem ra cổng. Bản hiển thị đã bị xoá EXIF nên không rò toạ độ GPS của người chụp.
    """
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    if co not in ("nho", "hien", "goc"):
        raise LoiTour("Không có ảnh này", 404)
    x = _lay(db, aid)
    if u is None:
        if co == "goc" or x.trang_thai != "da_duyet":
            raise LoiTour("Không có ảnh này", 404)
    else:
        _quyen(u, VAI_XEM, "Không có quyền")
    aid2 = {"nho": x.nho_id or x.hien_id or x.attachment_id,
            "hien": x.hien_id or x.attachment_id, "goc": x.attachment_id}[co]
    a = db.get(Attachment, aid2)
    if a is None:
        raise LoiTour("Không có ảnh này", 404)
    return AT.doc(db, a), a


# ── GHI ──────────────────────────────────────────────────────────────────────────────────────

def _trung(db: Session, ds: list[AnhTour], data: bytes):
    """Cùng nội dung đã có trong album → trả đúng ảnh ấy. Tải lại hai lần không sinh bản trùng."""
    from app.models.attachments import Attachment
    from app.services import attachments as AT
    cs = AT._sha(data)
    for x in ds:
        a = db.get(Attachment, x.attachment_id)
        if a is not None and a.checksum == cs:
            return x
    return None


def tai_anh(db: Session, u: User, pid: int, ten_tep: str, data: bytes, d: dict,
            now: datetime | None = None) -> tuple[AnhTour, bool]:
    """Tải MỘT ảnh (giao diện gửi từng tệp để báo tiến độ và thử lại riêng từng tấm)."""
    from app.services import attachments as AT
    _quyen(u, VAI_ANH, "Chỉ Marketing, Điều hành hoặc Kinh doanh tải ảnh tour")
    now = now or datetime.now()
    p = _sp(db, pid)
    loi = AC.loi_kiem_tep(ten_tep, data)
    if loi:
        raise LoiTour(loi)
    nhom = (d.get("nhom") or "").strip()
    can_cu = (d.get("can_cu") or "").strip() or "chua_xac_minh"
    if not nhom:
        raise LoiTour("Chọn nhóm ảnh cho lô này")
    _kiem_can_cu(can_cu, nhom)

    ds = _cua(db, pid)
    cu = _trung(db, ds, data)
    if cu is not None:
        return cu, False
    if len(ds) >= ANH_TOI_DA_SO:
        raise LoiTour(f"Album đã đủ {ANH_TOI_DA_SO} ảnh — ẩn hoặc xoá ảnh cũ thay vì tải thêm")

    hien, nho, rong, cao = AC.lam_nhe(data)
    if hien is None and AC.co_pil():
        raise LoiTour("Tệp không mở được như một ảnh — kiểm tra lại tệp")
    duoi = AC.duoi_anh(ten_tep)
    ma = f"sp{p.id}"
    try:
        a, _ = AT.dinh_kem(db, "anh_tour", ma, ten_tep, data, kieu=AC.KIEU_ANH[duoi], loai="hinh_anh",
                           mo_ta=f"Album tour {p.code} · căn cứ: {CAN_CU_ANH_TOUR.get(can_cu, can_cu)}",
                           boi=u.username)
        ah = AT.dinh_kem(db, "anh_tour", ma, f"{ten_tep}.hien.webp", hien, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Bản hiển thị · album tour {p.code}", boi=u.username, nguon="he_thong")[0] if hien else a
        an = AT.dinh_kem(db, "anh_tour", ma, f"{ten_tep}.nho.webp", nho, kieu="image/webp", loai="hinh_anh",
                         mo_ta=f"Ảnh nhỏ · album tour {p.code}", boi=u.username, nguon="he_thong")[0] if nho else ah
    except ValueError as ex:
        raise LoiTour(str(ex))

    x = AnhTour(product_id=pid, attachment_id=a.id, hien_id=ah.id, nho_id=an.id, rong=rong, cao=cao,
                nhom=nhom, chu_thich=(d.get("chu_thich") or "").strip()[:200],
                mo_ta_thay_the=(d.get("mo_ta_thay_the") or "").strip()[:200],
                thu_tu=max([y.thu_tu for y in ds], default=0) + 1, la_bia=not ds,
                can_cu=can_cu, can_cu_ghi_chu=(d.get("can_cu_ghi_chu") or "").strip()[:300],
                credit=(d.get("credit") or "").strip()[:160],
                trang_thai="da_duyet",          # KS-16c, nhắc lại cho tour 13/11/2026: tải là hiện
                tai_boi=u.username, tai_luc=now)
    db.add(x)
    R.audit(db, u.username, u.role, "anh_tour_tai", f"product:{p.code}",
            after={"nhom": nhom, "can_cu": can_cu, "ten_tep": ten_tep, "byte": len(data)})
    db.commit(); db.refresh(x)
    return x, True


def sua(db: Session, u: User, aid: int, d: dict, now: datetime | None = None) -> AnhTour:
    _quyen(u, VAI_ANH, "Chỉ Marketing, Điều hành hoặc Kinh doanh sửa ảnh tour")
    x = _lay(db, aid)
    moi = {k: ((d.get(k) if d.get(k) is not None else getattr(x, k)) or "").strip()[:n]
           for k, n in (("nhom", 20), ("chu_thich", 200), ("mo_ta_thay_the", 200),
                        ("credit", 160), ("can_cu", 20), ("can_cu_ghi_chu", 300))}
    _kiem_can_cu(moi["can_cu"], moi["nhom"])
    if not moi["nhom"]:
        raise LoiTour("Chọn nhóm ảnh")
    for k, v in moi.items():
        setattr(x, k, v)
    x.sua_boi, x.sua_luc = u.username, now or datetime.now()
    db.commit(); db.refresh(x)
    return x


def an(db: Session, u: User, aid: int, an_di: bool) -> AnhTour:
    """Gỡ nhanh một tấm ảnh sai khỏi cổng mà không xoá hẳn. Ảnh của mình thì ai tải người ấy gỡ."""
    x = _lay(db, aid)
    if not (_co(u, VAI_GO) or (_co(u, VAI_ANH) and x.tai_boi == u.username)):
        raise LoiTour("Ảnh này do người khác tải — chỉ PTGĐ Marketing, TP Điều hành, Chủ tịch hoặc TGĐ gỡ được", 403)
    x.trang_thai = "an" if an_di else "da_duyet"
    R.audit(db, u.username, u.role, "anh_tour_an" if an_di else "anh_tour_hien", f"anh_tour:{x.id}")
    db.commit(); db.refresh(x)
    return x


def xoa(db: Session, u: User, aid: int) -> int:
    """Xoá hẳn khỏi album. Tệp trong kho giữ nguyên — kho hồ sơ không xoá theo, để còn truy lại."""
    x = _lay(db, aid)
    if not (_co(u, VAI_GO) or (_co(u, VAI_ANH) and x.tai_boi == u.username)):
        raise LoiTour("Ảnh này do người khác tải — chỉ PTGĐ Marketing, TP Điều hành, Chủ tịch hoặc TGĐ xoá được", 403)
    pid = x.product_id
    R.audit(db, u.username, u.role, "anh_tour_xoa", f"anh_tour:{x.id}",
            before={"product_id": pid, "tai_boi": x.tai_boi, "nhom": x.nhom})
    db.delete(x)
    db.commit()
    return pid


def xep(db: Session, u: User, pid: int, ids: list[int]) -> None:
    """Thứ tự ảnh = thứ tự khách nhìn thấy. Ảnh đầu là ảnh bìa, và ba ảnh đầu quyết định lượt bấm."""
    _quyen(u, VAI_ANH, "Chỉ Marketing, Điều hành hoặc Kinh doanh xếp ảnh tour")
    ds = {x.id: x for x in _cua(db, pid)}
    la = [i for i in ids if i not in ds]
    if la:
        raise LoiTour("Danh sách có ảnh không thuộc sản phẩm này")
    for i, aid in enumerate(ids, start=1):
        ds[aid].thu_tu = i
        ds[aid].la_bia = (i == 1)
    for x in ds.values():                                   # ảnh không có trong danh sách xuống cuối
        if x.id not in ids:
            x.thu_tu = len(ids) + x.id
            x.la_bia = False
    db.commit()
