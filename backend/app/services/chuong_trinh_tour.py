"""4.4.2 · Chương trình của từng chuyến — chép một lần, đề xuất chứ không áp đặt.

BA LUẬT CỦA TỆP NÀY, và cả ba đều là lời từ chối làm hộ:

1. CHÉP MỘT LẦN, KHÔNG NỐI SỐNG. Mở lần đầu thì chụp lại bản sản phẩm và dựng đủ số ngày rỗng. Từ
   đó chương trình của chuyến sống độc lập. Đọc sống thì người sửa sản phẩm hôm nay lặng lẽ viết
   lại chương trình của một đoàn đã đi tuần trước, và bản khách cầm trong tay không còn khớp với
   bản trên hệ thống — đúng lúc có tranh chấp thì không ai chứng minh được gì.

2. KHÔNG TỰ TÁCH VĂN BẢN THÀNH TỪNG NGÀY. `de_xuat_tach()` chỉ tách khi văn bản có mốc "Ngày N"
   rõ ràng, và nó KHÔNG BAO GIỜ tự ghi — người điều hành đọc bản đề xuất cạnh bản gốc rồi bấm
   nhận. Đoán ranh giới ngày cho ra một lịch trình trông rất gọn mà có thể sai, và một lịch trình
   sai nhưng gọn thì không ai đọc lại lần thứ hai.

3. KHÔNG SỬA CHO KHỚP SỐ NGÀY. Khung ngày dựng theo độ dài chuyến; nếu sau đó chuyến đổi ngày về
   thì `lech_so_ngay()` NÓI RA chỗ lệch chứ không tự thêm hay xoá ngày. Tự xoá một ngày là xoá
   nội dung người ta đã soạn; tự thêm là in ra một ngày trống mà không ai biết nó từ đâu ra.

SỬA SAU KHI KHỞI HÀNH thì KHÔNG CẤM — đổi lịch vì thời tiết hay sự cố là việc có thật. Nhưng phải
ghi lý do và hệ thống đếm số lần. Cấm thì người ta sửa ở chỗ khác (Zalo, giấy) và hệ thống mất dấu
hoàn toàn, mà mất dấu thì tệ hơn một dòng lý do viết vội.
"""
from __future__ import annotations
import re
from datetime import datetime, date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import User, Tour, Product
from app.models.chuong_trinh import ChuongTrinhTour, ChuongTrinhNgay, CT_NGUON

# Mốc ngày mà bộ đề xuất CHẤP NHẬN. Cố ý hẹp: chỉ nhận "Ngày 1", "NGÀY 1", "Ngay 1", "Day 1" đứng
# đầu dòng. Nhận thêm mẫu lỏng hơn ("Sáng:", "Buổi 1") là bắt đầu đoán, và chỗ đoán nằm đúng trong
# thứ sẽ gửi cho khách.
MOC_NGAY = re.compile(r"^\s*(?:ngày|ngay|day)\s*(\d{1,2})\s*[:.\-–]?", re.IGNORECASE | re.MULTILINE)


def so_ngay_cua_chuyen(t: Tour) -> int:
    """Độ dài chuyến tính theo NGÀY DƯƠNG LỊCH, tối thiểu 1.

    Lấy từ start_date/end_date chứ không từ `tours.days`: cột ấy có thể rỗng với chuyến nạp từ kho
    cũ, và một khung 0 ngày thì màn hình không có gì để hiện.
    """
    if t.start_date and t.end_date and t.end_date >= t.start_date:
        return (t.end_date - t.start_date).days + 1
    return max(int(t.days or 0), 1)


def _dong_ngay(n: ChuongTrinhNgay) -> dict:
    return {"id": n.id, "ngay_thu": n.ngay_thu,
            "ngay": n.ngay.isoformat() if n.ngay else None,
            "tieu_de": n.tieu_de, "noi_dung": n.noi_dung,
            "bua_sang": n.bua_sang, "bua_trua": n.bua_trua, "bua_toi": n.bua_toi,
            "khach_san": n.khach_san, "phuong_tien": n.phuong_tien, "ghi_chu": n.ghi_chu,
            "lan_sua_sau_khoi_hanh": n.lan_sua_sau_khoi_hanh,
            "ly_do_sua_gan_nhat": n.ly_do_sua_gan_nhat,
            "sua_boi": n.sua_boi, "sua_luc": n.sua_luc.isoformat() if n.sua_luc else None,
            "trong": not (n.noi_dung or "").strip()}


def mo(db: Session, boi: User, tour_id: int) -> dict:
    """Mở chương trình của một chuyến. Lần đầu: chụp bản sản phẩm và dựng đủ số ngày RỖNG.

    Dựng ngày rỗng chứ KHÔNG đổ nội dung sản phẩm vào: xem luật 2 ở đầu tệp.
    """
    t = db.get(Tour, tour_id)
    if t is None:
        raise ValueError(f"Không có chuyến id={tour_id}.")
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    if dau is None:
        sp = db.get(Product, t.product_id) if t.product_id else None
        dau = ChuongTrinhTour(
            tour_id=tour_id, nguon="chua_soan",
            product_id_goc=t.product_id,
            ban_san_pham_goc=(sp.program if sp and sp.program else ""),
            chep_luc=datetime.now() if sp and sp.program else None,
            tao_boi=boi.username)
        db.add(dau)
        n = so_ngay_cua_chuyen(t)
        for i in range(1, n + 1):
            db.add(ChuongTrinhNgay(
                tour_id=tour_id, ngay_thu=i,
                ngay=(t.start_date + timedelta(days=i - 1)) if t.start_date else None))
        db.flush()
    return xem(db, tour_id)


def xem(db: Session, tour_id: int) -> dict:
    t = db.get(Tour, tour_id)
    if t is None:
        raise ValueError(f"Không có chuyến id={tour_id}.")
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    ngay = list(db.execute(select(ChuongTrinhNgay).where(
        ChuongTrinhNgay.tour_id == tour_id).order_by(ChuongTrinhNgay.ngay_thu)).scalars())
    sp = db.get(Product, dau.product_id_goc) if dau and dau.product_id_goc else None
    return {
        "tour_id": tour_id, "ma_chuyen": t.code, "ten_chuyen": t.name,
        "da_khoi_hanh": bool(t.start_date and t.start_date <= date.today()),
        "so_ngay_cua_chuyen": so_ngay_cua_chuyen(t),
        "nguon": dau.nguon if dau else "chua_soan",
        "nguon_ten": CT_NGUON.get(dau.nguon if dau else "chua_soan", ""),
        "ban_san_pham_goc": dau.ban_san_pham_goc if dau else "",
        "chep_luc": dau.chep_luc.isoformat() if dau and dau.chep_luc else None,
        "ban_san_pham_hien_tai": (sp.program if sp else ""),
        "lech_voi_san_pham": lech_voi_san_pham(db, tour_id),
        "lech_so_ngay": lech_so_ngay(db, tour_id),
        "ngay_trong": [n.ngay_thu for n in ngay if not (n.noi_dung or "").strip()],
        "rows": [_dong_ngay(n) for n in ngay],
    }


def lech_voi_san_pham(db: Session, tour_id: int) -> dict:
    """Sản phẩm đã đổi kể từ lúc chuyến này chép chưa?

    So bản sản phẩm HIỆN TẠI với ẢNH CHỤP lúc chép, KHÔNG so với chương trình chuyến: chương trình
    chuyến đã được sửa có chủ ý, so với nó thì lúc nào cũng lệch và dòng cảnh báo thành vô nghĩa.

    Và chỉ BÁO, không tự chép lại: tự đồng bộ là quay về đúng cái hỏng mà bảng này sinh ra để chữa.
    """
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    if dau is None or not dau.product_id_goc:
        return {"co_lech": False, "ly_do": "chuyến này không gắn sản phẩm nào"}
    sp = db.get(Product, dau.product_id_goc)
    hien = (sp.program if sp else "") or ""
    goc = dau.ban_san_pham_goc or ""
    if hien.strip() == goc.strip():
        return {"co_lech": False, "ly_do": "bản sản phẩm chưa đổi kể từ lúc chép"}
    return {"co_lech": True,
            "ly_do": "chương trình SẢN PHẨM đã đổi kể từ lúc chuyến này chép; chuyến KHÔNG tự đổi "
                     "theo — người điều hành quyết có chép lại hay không",
            "chep_luc": dau.chep_luc.isoformat() if dau.chep_luc else None}


def lech_so_ngay(db: Session, tour_id: int) -> dict:
    """Khung ngày có còn khớp độ dài chuyến không. NÓI RA, không tự sửa."""
    t = db.get(Tour, tour_id)
    co = db.execute(select(ChuongTrinhNgay).where(ChuongTrinhNgay.tour_id == tour_id)).scalars().all()
    can = so_ngay_cua_chuyen(t)
    if len(co) == can:
        return {"co_lech": False, "khung": len(co), "chuyen": can}
    return {"co_lech": True, "khung": len(co), "chuyen": can,
            "ly_do": f"khung chương trình có {len(co)} ngày mà chuyến dài {can} ngày. Hệ thống KHÔNG "
                     "tự thêm hay xoá: tự xoá là xoá nội dung đã soạn, tự thêm là in ra một ngày "
                     "trống không ai biết từ đâu. Người điều hành thêm hoặc xoá ngày bằng tay."}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỀ XUẤT TÁCH — ĐỀ XUẤT, KHÔNG ÁP ĐẶT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def de_xuat_tach(van_ban: str) -> dict:
    """Tách văn bản sản phẩm thành từng ngày, CHỈ khi có mốc "Ngày N" rõ ràng.

    Không có mốc thì trả về RỖNG kèm lý do, chứ không tách đều theo đoạn hay theo số dòng: tách đều
    cho ra một bản trông gọn mà sai, và cái sai ấy nằm đúng trong thứ sẽ gửi cho khách.
    """
    van_ban = van_ban or ""
    moc = list(MOC_NGAY.finditer(van_ban))
    if not moc:
        return {"tach_duoc": False,
                "ly_do": "văn bản không có mốc \"Ngày N\" nào ở đầu dòng, nên không tách được mà "
                         "không phải đoán. Người điều hành tự soạn từng ngày, bản gốc in ngay cạnh.",
                "rows": []}
    rows = []
    for i, m in enumerate(moc):
        dau = m.end()
        cuoi = moc[i + 1].start() if i + 1 < len(moc) else len(van_ban)
        than = van_ban[dau:cuoi].strip()
        dong_dau = than.split("\n", 1)
        rows.append({"ngay_thu": int(m.group(1)),
                     "tieu_de": dong_dau[0].strip()[:200],
                     "noi_dung": than})
    return {"tach_duoc": True, "so_ngay": len(rows), "rows": rows,
            "ly_do": f"tìm thấy {len(rows)} mốc ngày. ĐÂY LÀ ĐỀ XUẤT — chưa ghi gì; đọc lại rồi bấm nhận."}


def nhan_de_xuat(db: Session, boi: User, tour_id: int) -> dict:
    """Người điều hành bấm nhận bản đề xuất. CHỈ ghi vào ngày đang RỖNG.

    Không đè lên ngày đã có nội dung: người ta soạn tay rồi bấm nhầm nút thì mất công cả buổi, và
    bản đè lên lại trông hợp lý nên không ai phát hiện ngay.
    """
    xem_truoc = xem(db, tour_id)
    dx = de_xuat_tach(xem_truoc["ban_san_pham_goc"])
    if not dx["tach_duoc"]:
        raise ValueError(dx["ly_do"])
    theo_ngay = {r["ngay_thu"]: r for r in dx["rows"]}
    da_ghi, bo_qua = [], []
    for n in db.execute(select(ChuongTrinhNgay).where(
            ChuongTrinhNgay.tour_id == tour_id).order_by(ChuongTrinhNgay.ngay_thu)).scalars():
        r = theo_ngay.get(n.ngay_thu)
        if r is None:
            continue
        if (n.noi_dung or "").strip():
            bo_qua.append(n.ngay_thu)
            continue
        n.tieu_de, n.noi_dung = r["tieu_de"], r["noi_dung"]
        n.sua_boi, n.sua_luc = boi.username, datetime.now()
        da_ghi.append(n.ngay_thu)
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    if dau:
        dau.nguon = "chep_san_pham"
        dau.sua_cuoi_boi, dau.sua_cuoi_luc = boi.username, datetime.now()
    db.flush()
    return {"da_ghi": da_ghi, "bo_qua_vi_da_co_noi_dung": bo_qua,
            "thua_trong_de_xuat": sorted(set(theo_ngay) - set(da_ghi) - set(bo_qua))}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỬA
# ══════════════════════════════════════════════════════════════════════════════════════════════
O_SUA = ("tieu_de", "noi_dung", "bua_sang", "bua_trua", "bua_toi", "khach_san",
         "phuong_tien", "ghi_chu")


def sua_ngay(db: Session, boi: User, tour_id: int, ngay_thu: int, o: dict,
             ly_do: str = "") -> dict:
    """Sửa một ngày. Sau khi chuyến ĐÃ KHỞI HÀNH thì BẮT BUỘC ghi lý do."""
    t = db.get(Tour, tour_id)
    if t is None:
        raise ValueError(f"Không có chuyến id={tour_id}.")
    n = db.execute(select(ChuongTrinhNgay).where(
        ChuongTrinhNgay.tour_id == tour_id,
        ChuongTrinhNgay.ngay_thu == ngay_thu)).scalars().first()
    if n is None:
        raise ValueError(f"Chuyến này chưa có ngày thứ {ngay_thu} trong khung chương trình.")
    da_khoi_hanh = bool(t.start_date and t.start_date <= date.today())
    if da_khoi_hanh and not (ly_do or "").strip():
        raise ValueError(
            "Chuyến đã khởi hành — sửa chương trình thì phải ghi lý do. Việc này KHÔNG bị cấm "
            "(đổi lịch vì thời tiết hay sự cố là chuyện có thật), nhưng phải để lại dấu: cấm thì "
            "người ta sửa ở chỗ khác và hệ thống mất dấu hoàn toàn.")
    for k in O_SUA:
        if k in o:
            v = o[k]
            if k in ("bua_sang", "bua_trua", "bua_toi"):
                setattr(n, k, bool(v))
            elif k == "tieu_de":
                setattr(n, k, (v or "").strip()[:200])
            elif k in ("khach_san",):
                setattr(n, k, (v or "").strip()[:200])
            elif k in ("phuong_tien",):
                setattr(n, k, (v or "").strip()[:120])
            else:
                setattr(n, k, (v or "").strip())
    if da_khoi_hanh:
        n.lan_sua_sau_khoi_hanh += 1
        n.ly_do_sua_gan_nhat = ly_do.strip()
    n.sua_boi, n.sua_luc = boi.username, datetime.now()
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    if dau:
        if dau.nguon == "chua_soan":
            dau.nguon = "tu_soan"
        dau.sua_cuoi_boi, dau.sua_cuoi_luc = boi.username, datetime.now()
    db.flush()
    return _dong_ngay(n)


def them_ngay(db: Session, boi: User, tour_id: int) -> dict:
    """Thêm một ngày vào cuối khung — người điều hành bấm, hệ thống không tự thêm."""
    t = db.get(Tour, tour_id)
    if t is None:
        raise ValueError(f"Không có chuyến id={tour_id}.")
    co = db.execute(select(ChuongTrinhNgay).where(
        ChuongTrinhNgay.tour_id == tour_id)).scalars().all()
    moi = max((n.ngay_thu for n in co), default=0) + 1
    n = ChuongTrinhNgay(tour_id=tour_id, ngay_thu=moi,
                        ngay=(t.start_date + timedelta(days=moi - 1)) if t.start_date else None)
    db.add(n)
    db.flush()
    return _dong_ngay(n)


def xoa_ngay(db: Session, boi: User, tour_id: int, ngay_thu: int, ly_do: str) -> dict:
    """Xoá một ngày. BẮT BUỘC ghi lý do, và chỉ xoá được ngày CUỐI khung.

    Xoá giữa khung thì mọi ngày sau phải đánh số lại, và đánh số lại là viết đè nội dung của một
    loạt ngày khác — một thao tác trông như xoá một dòng mà thật ra sửa cả lịch trình.
    """
    if not (ly_do or "").strip():
        raise ValueError("Xoá một ngày khỏi chương trình thì phải ghi lý do.")
    co = list(db.execute(select(ChuongTrinhNgay).where(
        ChuongTrinhNgay.tour_id == tour_id).order_by(ChuongTrinhNgay.ngay_thu)).scalars())
    if not co:
        raise ValueError("Chuyến này chưa có khung chương trình.")
    cuoi = co[-1]
    if cuoi.ngay_thu != ngay_thu:
        raise ValueError(
            f"Chỉ xoá được ngày CUỐI của khung (đang là ngày {cuoi.ngay_thu}). Xoá giữa khung thì "
            "mọi ngày sau phải đánh số lại, tức là viết đè nội dung của một loạt ngày khác.")
    db.delete(cuoi)
    dau = db.execute(select(ChuongTrinhTour).where(
        ChuongTrinhTour.tour_id == tour_id)).scalars().first()
    if dau:
        dau.ghi_chu = (f"[{date.today():%d/%m/%Y} {boi.username} xoá ngày {ngay_thu}] "
                       f"{ly_do.strip()}\n{dau.ghi_chu or ''}")[:2000]
        dau.sua_cuoi_boi, dau.sua_cuoi_luc = boi.username, datetime.now()
    db.flush()
    return {"da_xoa": ngay_thu}


def meta() -> dict:
    return {"nguon": CT_NGUON, "o_sua": list(O_SUA)}
