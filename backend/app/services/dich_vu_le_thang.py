# -*- coding: utf-8 -*-
"""Đ-5 · Dịch vụ lẻ theo tháng — dựng lại đúng hình tờ Excel của Điều hành, KHÔNG bằng bảng mới.

──────────────────────────────────────────────────────────────────────────────────────────────────
BẢN ĐỀ XUẤT 12/9 CỦA ROBOT A SAI Ở ĐÂY, VÀ ĐÂY LÀ CHỖ SỬA
──────────────────────────────────────────────────────────────────────────────────────────────────

Bản ấy viết: dựng hai bảng `dich_vu_le_thang` / `dich_vu_le_dong` cho sổ visa lẻ theo tháng, lấy
hình từ tệp "QUYẾT TOÁN VISA LẺ CHÂU ÂU – THÁNG 06.2026".

Đo lại ngày 13/9 trước khi viết: VTOS ĐÃ CÓ ĐỦ.

    · `/non-package` đã là sổ dịch vụ lẻ THEO THÁNG. Mỗi dịch vụ là một chuyến loại `non_package`
      mã KLEddmmyy cộng một booking, có doanh thu, giá vốn, lãi, biên — và có cả CHỐT THÁNG sinh
      bút toán 154/335/632 (`nonpackage.close_month`).

    · Bốn cột chi của tệp đã có sẵn bốn mã khoản mục trong danh mục:
          Phí LSQ          -> vs_phi_lsq
          Phí dịch vụ visa -> vs_phi_dich_vu_visa
          Phí dịch thuật   -> vs_dich_thuat
          Phí điều hành    -> hd_phi_dieu_hanh

    · `tour_cost_lines` đã mang được ngoại tệ: `tien_te`, `so_tien_goc`, `ty_gia`, `ngay_ty_gia`.
      Phí lãnh sự thu bằng USD ghi được đúng tỷ giá NGÀY NỘP HỒ SƠ, không phải một tỷ giá chung
      của cả tháng.

Dựng thêm hai bảng nữa là tạo SỔ THỨ BA cho cùng một việc — đúng cái lỗi Đ-10 sinh ra để chặn. Và
lần này còn nặng hơn: sổ mới sẽ KHÔNG sinh bút toán, nên số của Kế toán tách làm hai nguồn.

──────────────────────────────────────────────────────────────────────────────────────────────────
VẬY CÒN THIẾU THẬT SỰ LÀ GÌ
──────────────────────────────────────────────────────────────────────────────────────────────────

1. TỜ EXCEL VẪN CÓ MỘT HÌNH MÀ HỆ THỐNG CHƯA DỰNG RA: bốn cột chi đứng cạnh nhau trên cùng một
   dòng khách. Trong VTOS, bốn khoản ấy là bốn DÒNG chi phí của chuyến KLE — đúng về cấu trúc,
   nhưng Điều hành đang phải đọc theo chiều dọc thứ mà họ quen đọc theo chiều ngang. Tệp này xoay
   lại: một dòng một khách, bốn cột chi, lấy từ chính dòng chi phí đang có.

2. MỘT DỊCH VỤ CÓ DOANH THU MÀ KHÔNG CÓ MỘT DÒNG GIÁ VỐN NÀO thì hiện không có gì kêu. Lãi của nó
   bằng đúng toàn bộ số thu, và con số ấy đi thẳng vào báo cáo tháng.

Cả hai việc đều là ĐỌC và SOÁT, không phải ghi. Nên tệp này không có một câu `db.add` nào.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.models.core import SERVICE_KINDS, Booking, Tour
from app.models.vietrip import TourCostLine

MUC = {"chan": "Chặn – không chốt tháng được",
       "canh_bao": "Cảnh báo – cần một lần nhìn lại trước khi lấy số đi báo cáo"}

# Bốn cột chi của tờ Excel, và mã khoản mục tương ứng đã có sẵn trong danh mục. Đây là chỗ DUY NHẤT
# ánh xạ hai thứ ấy – thêm một cột mới thì thêm một dòng ở đây, không sửa chỗ nào khác.
COT_CHI = [
    ("phi_lsq", "Phí LSQ", ("vs_phi_lsq",)),
    ("phi_dich_vu_visa", "Phí dịch vụ visa", ("vs_phi_dich_vu_visa", "vs_nhan_visa")),
    ("phi_dieu_hanh", "Phí điều hành", ("hd_phi_dieu_hanh",)),
    ("phi_dich_thuat", "Phí dịch thuật", ("vs_dich_thuat",)),
]
MA_DA_XEP = {m for _, _, ms in COT_CHI for m in ms}


def _thang(nam: int, thang: int) -> tuple[date, date]:
    dau = date(nam, thang, 1)
    cuoi = date(nam + (thang == 12), thang % 12 + 1, 1)
    return dau, cuoi


def bang(db: Session, nam: int, thang: int, mang: str | None = None) -> dict:
    """Tờ dịch vụ lẻ của một tháng, dựng từ booking + dòng chi phí đang có.

    KHÔNG ghi gì. Đây là một cách NHÌN dữ liệu đã có, không phải một sổ thứ hai.
    """
    q = (select(Booking).join(Tour, Tour.id == Booking.tour_id)
         .where(Tour.tour_type == "non_package",
                extract("year", Booking.created_at) == nam,
                extract("month", Booking.created_at) == thang))
    if mang:
        q = q.where(Booking.service_type == mang.upper())
    bs = list(db.scalars(q.order_by(Booking.created_at, Booking.id)))

    tour_ids = {b.tour_id for b in bs if b.tour_id}
    chi_theo_tour: dict[int, list[TourCostLine]] = {}
    ma_tour: dict[int, str] = {}
    if tour_ids:
        for l in db.scalars(select(TourCostLine).where(
                TourCostLine.tour_id.in_(tour_ids), TourCostLine.status == "hd")):
            chi_theo_tour.setdefault(l.tour_id, []).append(l)
        # Mã KLE là thứ Điều hành gọi tên dịch vụ, không phải mã booking. Lời chặn phải gọi đúng
        # cái tên người ta đang nhìn trên màn hình, nếu không họ không tìm ra dòng nào bị nhắc.
        ma_tour = {t.id: t.code for t in db.scalars(select(Tour).where(Tour.id.in_(tour_ids)))}

    dong = []
    for b in bs:
        ls = chi_theo_tour.get(b.tour_id, [])
        cot: dict[str, float | None] = {}
        for khoa, _, mas in COT_CHI:
            v = [float(x.actual) for x in ls
                 if x.actual is not None and (x.ma_khoan_muc or "") in mas]
            cot[khoa] = round(sum(v), 2) if v else None
        khac = [float(x.actual) for x in ls
                if x.actual is not None and (x.ma_khoan_muc or "") not in MA_DA_XEP]
        cot["phi_khac"] = round(sum(khac), 2) if khac else None

        # Giá vốn: ưu tiên DÒNG CHI PHÍ. Chỉ khi chưa có dòng nào mới dùng ô cost_amount của
        # booking – cùng thứ tự ưu tiên với nonpackage.close_month, để hai chỗ không ra hai số.
        tu_dong = [float(x.actual) for x in ls if x.actual is not None]
        tong_chi = (round(sum(tu_dong), 2) if tu_dong
                    else (round(float(b.cost_amount), 2) if b.cost_amount is not None else None))
        nguon_chi = "dong_chi_phi" if tu_dong else ("o_gop" if b.cost_amount is not None else None)

        # Doanh thu = giá bán − giảm giá. CHƯA khai giá bán thì tổng thu là CHƯA CÓ, không phải 0.
        #
        # Chỗ này CỐ Ý khác `nonpackage.summary()`, vốn viết `(b.amount or 0) - (b.discount or 0)`
        # và do đó đọc "chưa nhập giá bán" thành "doanh thu 0". Với một bảng tổng hợp thì đọc như
        # thế là chấp nhận được; với một bảng SOÁT thì không – nó làm biến mất đúng thứ cần soi.
        # Hai con số chỉ khác nhau ở những dòng chưa nhập giá bán, và bộ đếm
        # `so_dong_chua_tinh_duoc_lai` nói ra có bao nhiêu dòng như vậy.
        gia_ban = None if b.amount is None else float(b.amount)
        giam = 0.0 if b.discount is None else float(b.discount)
        tong_thu = None if gia_ban is None else round(gia_ban - giam, 2)

        dong.append({
            "booking_id": b.id, "tour_id": b.tour_id,
            "ma": ma_tour.get(b.tour_id) or b.code, "ma_booking": b.code,
            "thi_truong": b.service_type,
            "thi_truong_ten": SERVICE_KINDS.get(b.service_type or "", b.service_type),
            "ten_khach": b.customer_name,
            "sale": (b.sales.full_name if getattr(b, "sales", None) else ""),
            "ngay": b.created_at.date() if b.created_at else None,
            "gia_ban": b.amount, "giam_gia": b.discount, "tong_thu": tong_thu,
            "da_thu": b.paid, "huy": bool(b.cancelled),
            **cot,
            "tong_chi": tong_chi, "nguon_chi": nguon_chi, "so_dong_chi": len(ls),
            "lai": (round(tong_thu - tong_chi, 2)
                    if (tong_thu is not None and tong_chi is not None) else None),
            "ghi_chu": b.care_note or "",
        })

    song = [x for x in dong if not x["huy"]]

    def _c(k: str) -> float | None:
        v = [x[k] for x in song if x[k] is not None]
        return round(sum(v), 2) if v else None

    lai = [x["lai"] for x in song if x["lai"] is not None]
    return {
        "nam": nam, "thang": thang, "mang": mang,
        "cot_chi": [{"khoa": k, "nhan": n, "ma_khoan_muc": list(m)} for k, n, m in COT_CHI],
        "dong": dong, "so_dong": len(dong), "so_dong_huy": len(dong) - len(song),
        "tong_thu": _c("tong_thu"), "tong_chi": _c("tong_chi"),
        **{f"tong_{k}": _c(k) for k, _, _ in COT_CHI},
        "tong_phi_khac": _c("phi_khac"),
        "tong_lai": round(sum(lai), 2) if lai else None,
        "so_dong_chua_tinh_duoc_lai": len([x for x in song if x["lai"] is None]),
        "ghi_chu": ("Bảng này ĐỌC từ booking dịch vụ lẻ và dòng chi phí của chính chuyến ấy – không "
                    "có sổ thứ hai. Bốn cột chi lấy theo mã khoản mục; khoản không thuộc bốn mã ấy "
                    "gom vào cột «Phí khác» để không con số nào biến mất."),
    }


def soat(db: Session, nam: int, thang: int, mang: str | None = None) -> dict:
    """Chấm tháng trước khi Kế toán chốt."""
    b = bang(db, nam, thang, mang)
    chan, canh = [], []

    for d in b["dong"]:
        if d["huy"]:
            continue
        gc = (d["ghi_chu"] or "").strip()
        if d["tong_thu"] is not None and d["tong_chi"] is None:
            chan.append({
                "muc": "chan", "booking_id": d["booking_id"], "ma": d["ma"],
                "ten_khach": d["ten_khach"], "tong_thu": d["tong_thu"],
                "vi_sao": (f"«{d['ma']} – {d['ten_khach']}» có doanh thu {d['tong_thu']:,.0f} đ mà "
                           "KHÔNG có một dòng giá vốn nào. Lãi của nó đang bằng đúng toàn bộ số "
                           "thu, và con số ấy đi thẳng vào báo cáo tháng."),
                "can_lam": ("Nhập dòng chi phí ở màn hình quyết toán của chính dịch vụ này "
                            f"(/tours/{d['tour_id']}), hoặc ghi rõ đây là dịch vụ không có giá vốn.")})
        if d["lai"] is not None and d["lai"] < 0 and not gc:
            canh.append({
                "muc": "canh_bao", "booking_id": d["booking_id"], "ma": d["ma"],
                "ten_khach": d["ten_khach"], "lai": d["lai"],
                "vi_sao": f"Dịch vụ này lỗ {abs(d['lai']):,.0f} đ mà không có lời giải thích nào.",
                "can_lam": ("Một dòng chữ: giữ khách quen, hay lãnh sự tăng phí sau khi đã báo giá? "
                            "Một khoản lỗ không ai giải thích thì tháng sau không ai nhớ.")})
        if d["nguon_chi"] == "o_gop":
            canh.append({
                "muc": "canh_bao", "booking_id": d["booking_id"], "ma": d["ma"],
                "vi_sao": ("Giá vốn đang lấy từ ô GỘP của booking, không phải từ dòng chi phí – nên "
                           "bốn cột phí của tờ này rỗng và không đối chiếu được với hoá đơn đầu vào."),
                "can_lam": "Tách thành dòng chi phí theo khoản mục ở màn hình quyết toán."})

    if b["so_dong_chua_tinh_duoc_lai"]:
        canh.append({
            "muc": "canh_bao", "so_dong": b["so_dong_chua_tinh_duoc_lai"],
            "vi_sao": (f"{b['so_dong_chua_tinh_duoc_lai']} dịch vụ chưa tính được lãi, nên con số "
                       "lãi của tháng CHƯA PHỦ HẾT sổ."),
            "can_lam": "Nhập nốt phần còn thiếu trước khi lấy số này đi báo cáo."})

    return {**b, "chan": chan, "canh_bao": canh,
            "duoc_chot_thang": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}
