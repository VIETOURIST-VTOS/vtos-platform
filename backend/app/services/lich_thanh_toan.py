"""VPM-9 — lịch thanh toán theo tiến độ của hợp đồng khách.

Xem app/models/ban_hang.py (lớp `LichThanhToanHD`) để biết vì sao phân hệ này tồn tại và ba quyết
định đã chốt. Tệp này giữ các luật ấy:

  1. TỔNG CÁC ĐỢT PHẢI BẰNG GIÁ TRỊ HỢP ĐỒNG. Lệch thì từ chối cả lô. Một lịch mà tổng không khớp
     thì không phải lịch – nó chỉ là vài dòng ghi chú, và người thu công nợ vẫn phải tự cộng lại.
  2. Hạn tính MỘT LẦN từ mốc rồi lưu thành ngày thật. Dời hạn là hành động có người và có lý do.
  3. Không lưu "đã thu" theo đợt. Tiền đã thu được RẢI vào các đợt theo thứ tự hạn khi đọc.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ban_hang import HopDongKhach, LichThanhToanHD, MOC_HAN
from app.models.core import Booking, Tour, User
from app.services import payments as PAY
from app.services import rules as R

SOAN_LICH = ("nv_kd", "tn_kd", "tp_kd", "gd_kd", "ketoan", "cntt", "tgd", "chutich")

# Sai số cho phép khi so tổng các đợt với giá trị hợp đồng. Một đồng là tiền; nửa đồng là làm tròn.
SAI_SO = 0.5


def _ngay_khoi_hanh(db: Session, hd: HopDongKhach) -> date | None:
    if not hd.booking_id:
        return None
    b = db.get(Booking, hd.booking_id)
    t = db.get(Tour, b.tour_id) if b else None
    return t.start_date if t else None


def tinh_han(db: Session, hd: HopDongKhach, moc: str, so_ngay: int | None,
             han_co_dinh: date | None = None) -> date | None:
    """Ra NGÀY THẬT từ mốc. Trả về None khi chưa đủ căn cứ – và None ở đây nghĩa là CHƯA CÓ HẠN."""
    if moc == "co_dinh":
        return han_co_dinh
    n = int(so_ngay or 0)
    if moc == "ngay_ky":
        return (hd.ngay_ky + timedelta(days=n)) if hd.ngay_ky else None
    kh = _ngay_khoi_hanh(db, hd)
    if kh is None:
        return None
    if moc == "truoc_khoi_hanh":
        return kh - timedelta(days=n)
    if moc == "sau_khoi_hanh":
        return kh + timedelta(days=n)
    raise ValueError(f"Mốc không hợp lệ: {moc}. Chọn một trong {', '.join(MOC_HAN)}")


def cac_dot(db: Session, hd: HopDongKhach) -> list[LichThanhToanHD]:
    return list(db.execute(
        select(LichThanhToanHD).where(LichThanhToanHD.hop_dong_id == hd.id)
        .order_by(LichThanhToanHD.dot)).scalars())


def da_thu(db: Session, hd: HopDongKhach) -> float:
    """Tổng đã thu của hợp đồng — lấy từ phiếu thu của booking, KHÔNG có sổ tiền thứ hai."""
    if not hd.booking_id:
        return 0.0
    return float(PAY.paid_amount(db, hd.booking_id) or 0)


def dat_lich(db: Session, u: User, hd: HopDongKhach, dong: list[dict]) -> dict:
    """Đặt (hoặc đặt lại) toàn bộ lịch cho hợp đồng. Kiểm CẢ LÔ trước khi ghi dòng đầu tiên.

    Đặt lại thì thay trọn lịch cũ: một lịch nửa cũ nửa mới là thứ không ai đọc được, và cũng không
    ai nói được tổng của nó có còn bằng giá trị hợp đồng hay không.
    """
    if u.role not in SOAN_LICH:
        raise ValueError("Vai trò này không đặt được lịch thanh toán hợp đồng")
    if hd.trang_thai in ("huy", "thanh_ly"):
        raise ValueError(f"Hợp đồng đang ở trạng thái '{hd.trang_thai}' – không đặt lịch nữa")
    if not dong:
        raise ValueError("Chưa có đợt nào")

    gia_tri = float(hd.gia_tri or 0)
    if gia_tri <= 0:
        raise ValueError("Hợp đồng chưa có giá trị – nhập giá trị hợp đồng trước khi chia đợt")

    da_kiem, tong = [], 0.0
    for i, d in enumerate(dong, start=1):
        moc = str(d.get("moc") or "co_dinh")
        if moc not in MOC_HAN:
            raise ValueError(f"Đợt {i}: mốc '{moc}' không hợp lệ")
        try:
            tien = round(float(d.get("so_tien") or 0), 2)
        except (TypeError, ValueError):
            raise ValueError(f"Đợt {i}: số tiền không đọc được")
        if tien <= 0:
            raise ValueError(f"Đợt {i}: số tiền phải lớn hơn 0")

        han_cd = d.get("han")
        if isinstance(han_cd, str) and han_cd:
            han_cd = date.fromisoformat(han_cd[:10])
        han = tinh_han(db, hd, moc, d.get("moc_so_ngay"), han_cd if isinstance(han_cd, date) else None)
        if moc == "co_dinh" and han is None:
            raise ValueError(f"Đợt {i}: mốc là ngày cố định thì phải nhập ngày")

        ty_le = d.get("ty_le")
        tong += tien
        da_kiem.append({"dot": i, "ten": str(d.get("ten") or f"Đợt {i}")[:120], "so_tien": tien,
                        "ty_le": float(ty_le) if ty_le not in (None, "") else None,
                        "moc": moc, "moc_so_ngay": d.get("moc_so_ngay"), "han": han,
                        "ghi_chu": str(d.get("ghi_chu") or "")[:300]})

    # LUẬT 1 – không khớp thì không ghi gì.
    if abs(round(tong, 2) - round(gia_tri, 2)) > SAI_SO:
        thieu = round(gia_tri - tong, 2)
        raise ValueError(
            f"Tổng các đợt {tong:,.0f} đ không bằng giá trị hợp đồng {gia_tri:,.0f} đ "
            f"({'thiếu' if thieu > 0 else 'thừa'} {abs(thieu):,.0f} đ). "
            f"Lịch mà tổng không khớp thì người thu công nợ vẫn phải tự cộng lại.")

    cu = cac_dot(db, hd)
    for x in cu:
        db.delete(x)
    db.flush()

    for r in da_kiem:
        db.add(LichThanhToanHD(hop_dong_id=hd.id, dot=r["dot"], ten=r["ten"], ty_le=r["ty_le"],
                               so_tien=r["so_tien"], moc=r["moc"], moc_so_ngay=r["moc_so_ngay"],
                               han=r["han"], han_goc=r["han"], ghi_chu=r["ghi_chu"], boi=u.username))
    # Giữ `han_thanh_toan` của hợp đồng khớp với đợt CUỐI: trước VPM-9 nó là hạn duy nhất và nhiều
    # chỗ trong hệ thống vẫn đọc nó. Để nó nói một chuyện khác với lịch là mở đường cho hai câu trả lời.
    hans = [r["han"] for r in da_kiem if r["han"]]
    if hans:
        hd.han_thanh_toan = max(hans)

    R.audit(db, u.username, u.role, "dat_lich_thanh_toan", f"hopdong:{hd.so_hop_dong}",
            before={"so_dot_cu": len(cu)},
            after={"so_dot": len(da_kiem), "tong": tong, "gia_tri": gia_tri})
    db.commit()
    return {"so_dot": len(da_kiem), "tong": tong,
            "message": f"Đã đặt lịch {len(da_kiem)} đợt, tổng {tong:,.0f} đ – khớp giá trị hợp đồng."}


def doi_han(db: Session, u: User, dot: LichThanhToanHD, han_moi: date, ly_do: str) -> dict:
    """Dời hạn MỘT đợt. Bắt buộc có lý do – hạn đã báo cho khách, đổi nó là đổi một lời hứa."""
    if u.role not in SOAN_LICH:
        raise ValueError("Vai trò này không dời được hạn thanh toán")
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do dời hạn – hạn này đã nằm trong hợp đồng khách đang cầm")
    cu = dot.han
    dot.han = han_moi
    if dot.han_goc is None:
        dot.han_goc = cu
    dot.moc, dot.moc_so_ngay = "co_dinh", None      # đã dời tay thì thôi bám mốc
    dot.ghi_chu = (f"{dot.ghi_chu} · Dời hạn {cu:%d/%m/%Y} → {han_moi:%d/%m/%Y}: {ly_do.strip()}"
                   if cu else f"{dot.ghi_chu} · Đặt hạn {han_moi:%d/%m/%Y}: {ly_do.strip()}")[:300]
    hd = db.get(HopDongKhach, dot.hop_dong_id)
    R.audit(db, u.username, u.role, "doi_han_thanh_toan",
            f"hopdong:{hd.so_hop_dong if hd else dot.hop_dong_id}",
            before={"dot": dot.dot, "han": cu.isoformat() if cu else None},
            after={"han": han_moi.isoformat(), "ly_do": ly_do.strip()})
    db.commit()
    return {"message": f"Đã dời hạn đợt {dot.dot} sang {han_moi:%d/%m/%Y}"}


def bang(db: Session, hd: HopDongKhach, den_ngay: date | None = None) -> dict:
    """Toàn cảnh một hợp đồng: từng đợt, đã rải bao nhiêu, và ĐẾN HÔM NAY khách phải trả bao nhiêu.

    Việc rải tiền là một PHÉP CHIA ĐỂ ĐỌC, không phải một khẳng định rằng khoản tiền ấy trả cho đợt
    ấy. Tiền vào không mang nhãn; màn hình phải nói rõ điều đó thay vì để người đọc tưởng hệ thống
    biết nhiều hơn nó biết.
    """
    hom_nay = den_ngay or date.today()
    tong_thu = da_thu(db, hd)
    con_lai = tong_thu
    ds, den_han, da_du = [], 0.0, 0.0

    for x in cac_dot(db, hd):
        tien = float(x.so_tien or 0)
        rai = min(con_lai, tien)
        con_lai = round(con_lai - rai, 2)
        thieu = round(tien - rai, 2)
        qua_han = bool(x.han and x.han < hom_nay and thieu > SAI_SO)
        if x.han and x.han <= hom_nay:
            den_han += tien
        if thieu <= SAI_SO:
            da_du += tien
        ds.append({
            "id": x.id, "dot": x.dot, "ten": x.ten, "ty_le": x.ty_le, "so_tien": tien,
            "moc": x.moc, "moc_mo_ta": MOC_HAN.get(x.moc, x.moc), "moc_so_ngay": x.moc_so_ngay,
            "han": x.han, "han_goc": x.han_goc, "da_doi_han": bool(x.han_goc and x.han != x.han_goc),
            "da_rai": round(rai, 2), "con_thieu": thieu,
            "trang_thai": ("da_du" if thieu <= SAI_SO else "qua_han" if qua_han else "cho_den_han"),
            "qua_han": qua_han, "ghi_chu": x.ghi_chu, "boi": x.boi, "luc": x.luc,
        })

    tong_dot = round(sum(d["so_tien"] for d in ds), 2)
    return {
        "hop_dong_id": hd.id, "so_hop_dong": hd.so_hop_dong, "khach_ten": hd.khach_ten,
        "gia_tri": float(hd.gia_tri or 0), "tong_cac_dot": tong_dot,
        "khop_gia_tri": abs(tong_dot - float(hd.gia_tri or 0)) <= SAI_SO if ds else None,
        "da_thu": tong_thu, "chua_gan_dot": round(con_lai, 2),
        "den_han_hom_nay": round(den_han, 2),
        "phai_tra_den_hom_nay": round(max(0.0, den_han - tong_thu), 2),
        "ngay_khoi_hanh": _ngay_khoi_hanh(db, hd),
        "dot": ds,
        "ghi_chu_man_hinh": ("Số 'đã rải' là phép chia để đọc – tiền vào không mang nhãn ghi nó trả cho "
                             "đợt nào. Tổng đã thu lấy từ phiếu thu của booking, không có sổ thứ hai."),
    }


def qua_han(db: Session, den_ngay: date | None = None) -> list[dict]:
    """Mọi đợt đã đến hạn mà hợp đồng chưa thu đủ tới đợt ấy – danh sách cho người đòi công nợ."""
    hom_nay = den_ngay or date.today()
    ra = []
    for hd in db.execute(select(HopDongKhach).where(
            HopDongKhach.trang_thai.notin_(["huy", "thanh_ly"]))).scalars():
        b = bang(db, hd, hom_nay)
        for d in b["dot"]:
            if d["qua_han"]:
                ra.append({"hop_dong_id": hd.id, "so_hop_dong": hd.so_hop_dong,
                           "khach_ten": hd.khach_ten, "dot": d["dot"], "ten": d["ten"],
                           "han": d["han"], "so_tien": d["so_tien"], "con_thieu": d["con_thieu"],
                           "tre_ngay": (hom_nay - d["han"]).days if d["han"] else None})
    ra.sort(key=lambda x: (x["han"] or date.max))
    return ra


def canh_bao_doi_ngay_khoi_hanh(db: Session, hd: HopDongKhach) -> list[str]:
    """Ngày khởi hành đổi thì các đợt bám mốc khởi hành KHÔNG tự dời – hàm này nói ra chỗ lệch.

    Không tự sửa: hạn đã nằm trong hợp đồng khách đang cầm. Việc của hệ thống là làm cho chỗ lệch
    nhìn thấy được, rồi để người có thẩm quyền dời từng đợt kèm lý do.
    """
    ra = []
    for x in cac_dot(db, hd):
        if x.moc not in ("truoc_khoi_hanh", "sau_khoi_hanh"):
            continue
        nen = tinh_han(db, hd, x.moc, x.moc_so_ngay)
        if nen and x.han and nen != x.han:
            ra.append(f"Đợt {x.dot} ({x.ten}): hạn đang là {x.han:%d/%m/%Y}, nhưng theo mốc "
                      f"'{MOC_HAN[x.moc]} {x.moc_so_ngay} ngày' thì phải là {nen:%d/%m/%Y}. "
                      f"Ngày khởi hành đã đổi – dời hạn hay giữ nguyên là quyết định của người, "
                      f"hệ thống không tự đổi lời hứa với khách.")
    return ra
