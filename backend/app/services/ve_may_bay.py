# -*- coding: utf-8 -*-
"""Đ-8 · Vé máy bay theo mã đặt chỗ: dòng từng khách là số chốt, khối theo mã do máy cộng.

Xem chú thích dài ở `app/models/lop3_tour.py`, khối Đ-8, cho phần đo trên tệp thật. Tệp này chỉ nói
về PHÉP TÍNH và PHÉP SOÁT.

──────────────────────────────────────────────────────────────────────────────────────────────────
BA PHÉP SOÁT, VÀ CHỈ MỘT TRONG BA ĐƯỢC CHẶN
──────────────────────────────────────────────────────────────────────────────────────────────────

CHẶN  · một dòng vé không có tên khách; một dòng hoàn vé không có lý do; một dòng hoàn vé mang số
        tiền dương; một dòng vé mang số tiền âm. Bốn thứ ấy đều làm con số mất nghĩa ngay tại chỗ,
        không phải "sẽ xử lý sau".

CẢNH BÁO · số chỗ đã giữ ở hãng nhiều hơn số tên đã điền. Đó là việc phải làm, không phải lỗi: giữ
        32 chỗ rồi điền tên dần là cách đặt vé đoàn bình thường. Nhưng quá hạn xuất vé mà vẫn thiếu
        tên thì hãng huỷ chỗ, nên nó phải hiện ra.

CẢNH BÁO · tổng tiền vé lệch so với dòng chi phí vé trong chiết tính. Lệch là chuyện thường (giá
        đổi, hoàn vé, nâng hạng); im lặng mới là chuyện lạ.

KHÔNG PHẢI PHÉP SOÁT · "Σ tiền vé = Σ đã thanh toán". Xem chú thích lớp TourVeThanhToan: các đợt
        thanh toán chỉ TRỪ DẦN vào nợ, chúng không phải một cách ghi khác của tổng tiền vé. Ở đây
        chỉ có một SỐ DƯ, và số dư được BÁO chứ không bị chặn.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import LOAI_VE, TourVeKhach, TourVeMa, TourVeThanhToan
from app.models.vietrip import TourCostLine

# Loại dịch vụ trong bảng chiết tính được coi là "khoản vé máy bay". Dùng để so đối chiếu, KHÔNG
# dùng để tự động ghi gì – so xong thì báo, người quyết.
MA_DICH_VU_VE = ("AIR", "VE_MB", "FLIGHT", "VMB")

MUC = {"chan": "Chặn – con số mất nghĩa ngay tại chỗ",
       "canh_bao": "Cảnh báo – việc phải làm, không chặn đóng số"}


def thanh_tien_dong(d: TourVeKhach) -> float | None:
    """Cộng bốn ô tiền của một dòng vé. Trả None khi CẢ BỐN ô đều rỗng.

    Rỗng khác không: một dòng chưa nhập ô nào thì thành tiền là CHƯA CÓ, không phải 0 đồng. Trả 0 ở
    đây là biến một dòng chưa làm xong thành một dòng đã xong với giá 0.
    """
    o = [d.gia_ve, d.gia_ve_noi_dia, d.phi_khac, d.phi_nang_hang]
    if all(x is None for x in o):
        return None
    return round(sum(float(x) for x in o if x is not None), 2)


def _quy_vnd(so_tien: float | None, tien_te: str | None, ty_gia: float | None) -> float | None:
    """Quy một số về VND. Thiếu tỷ giá cho ngoại tệ thì trả None, KHÔNG trả số gốc.

    Trả số gốc khi thiếu tỷ giá là cách 450 USD lặng lẽ được cộng vào như 450 đồng.
    """
    if so_tien is None:
        return None
    if not tien_te or tien_te.upper() == "VND":
        return round(float(so_tien), 2)
    if not ty_gia:
        return None
    return round(float(so_tien) * float(ty_gia), 2)


def bang(db: Session, tour_id: int) -> dict:
    """Toàn bộ khối vé của một chuyến: dòng khách, khối theo mã (máy cộng), và số dư với đại lý."""
    ma_ds = list(db.scalars(select(TourVeMa).where(TourVeMa.tour_id == tour_id)
                            .order_by(TourVeMa.id)))
    kh_ds = list(db.scalars(select(TourVeKhach).where(TourVeKhach.tour_id == tour_id)
                            .order_by(TourVeKhach.id)))
    tt_ds = list(db.scalars(select(TourVeThanhToan).where(TourVeThanhToan.tour_id == tour_id)
                            .order_by(TourVeThanhToan.ngay, TourVeThanhToan.id)))

    dong = []
    for d in kh_ds:
        tt = thanh_tien_dong(d)
        dong.append({
            "id": d.id, "ve_ma_id": d.ve_ma_id, "khach_id": d.khach_id, "ho_ten_ve": d.ho_ten_ve,
            "loai": d.loai, "loai_ten": LOAI_VE.get(d.loai, d.loai),
            "gia_ve": d.gia_ve, "gia_ve_noi_dia": d.gia_ve_noi_dia,
            "phi_khac": d.phi_khac, "phi_nang_hang": d.phi_nang_hang,
            "thanh_tien": tt, "tien_te": d.tien_te, "ty_gia": d.ty_gia,
            "thanh_tien_vnd": _quy_vnd(tt, d.tien_te, d.ty_gia),
            "so_hoa_don": d.so_hoa_don, "ly_do": d.ly_do, "ghi_chu": d.ghi_chu,
        })

    # ---- Khối theo mã: MÁY CỘNG. Không có cửa nào cho người gõ tổng của một mã. ----
    theo_ma = []
    for m in ma_ds:
        cua_ma = [x for x in dong if x["ve_ma_id"] == m.id]
        co_so = [x["thanh_tien_vnd"] for x in cua_ma if x["thanh_tien_vnd"] is not None]
        so_ve = len([x for x in cua_ma if x["loai"] == "ve"])
        theo_ma.append({
            "id": m.id, "ma_dat_cho": m.ma_dat_cho, "hang_bay": m.hang_bay,
            "hanh_trinh": m.hanh_trinh, "so_cho_giu": m.so_cho_giu,
            "han_xuat_ve": m.han_xuat_ve, "trang_thai": m.trang_thai,
            "nha_cung_cap": m.nha_cung_cap,
            "so_dong": len(cua_ma), "so_ve": so_ve,
            # Thiếu tên bao nhiêu chỗ so với số đã giữ. None khi chưa khai số chỗ giữ – khác 0.
            "con_thieu_ten": (None if m.so_cho_giu is None else m.so_cho_giu - so_ve),
            "tong_vnd": (round(sum(co_so), 2) if co_so else None),
            "so_dong_chua_co_so": len([x for x in cua_ma if x["thanh_tien_vnd"] is None]),
        })

    khong_thuoc_ma = [x for x in dong if x["ve_ma_id"] is None]
    co_so_all = [x["thanh_tien_vnd"] for x in dong if x["thanh_tien_vnd"] is not None]
    tong_ve = round(sum(co_so_all), 2) if co_so_all else None

    da_tra = [_quy_vnd(t.so_tien, t.tien_te, t.ty_gia) for t in tt_ds]
    tong_tra = round(sum(x for x in da_tra if x is not None), 2) if any(
        x is not None for x in da_tra) else None

    return {
        "tour_id": tour_id,
        "dong": dong, "theo_ma": theo_ma,
        "so_dong_khong_thuoc_ma": len(khong_thuoc_ma),
        "tong_tien_ve_vnd": tong_ve,
        "so_dong_chua_quy_duoc_vnd": len([x for x in dong if x["thanh_tien_vnd"] is None
                                          and x["thanh_tien"] is not None]),
        "thanh_toan": [{"id": t.id, "ngay": t.ngay, "so_tien": t.so_tien, "tien_te": t.tien_te,
                        "ty_gia": t.ty_gia, "so_tien_vnd": _quy_vnd(t.so_tien, t.tien_te, t.ty_gia),
                        "hinh_thuc": t.hinh_thuc, "so_chung_tu": t.so_chung_tu,
                        "ghi_chu": t.ghi_chu} for t in tt_ds],
        "tong_da_thanh_toan_vnd": tong_tra,
        # Số dư, KHÔNG phải đẳng thức. Dương = còn nợ đại lý. Âm = đã trả thừa.
        "con_no_dai_ly": (None if tong_ve is None else round(tong_ve - (tong_tra or 0), 2)),
        "ghi_chu": ("Các đợt thanh toán chỉ TRỪ DẦN vào nợ – chúng không phải một cách ghi khác của "
                    "tổng tiền vé. Lệch giữa hai con số là SỐ DƯ, không phải sai sót."),
    }


def _chiet_tinh_ve(db: Session, tour_id: int) -> float | None:
    ds = list(db.scalars(select(TourCostLine).where(
        TourCostLine.tour_id == tour_id, TourCostLine.status == "hd")))
    co = [float(x.actual) for x in ds
          if x.actual is not None and (x.service_type or "").upper() in MA_DICH_VU_VE]
    return round(sum(co), 2) if co else None


def soat(db: Session, tour_id: int, hom_nay: date | None = None) -> dict:
    """Chấm khối vé trước khi đóng số."""
    hom_nay = hom_nay or date.today()
    b = bang(db, tour_id)
    chan, canh = [], []

    for d in b["dong"]:
        tt = d["thanh_tien"]
        if d["loai"] in ("ve", "hoan_ve") and not (d["ho_ten_ve"] or "").strip() and not d["khach_id"]:
            chan.append({"muc": "chan", "dong_id": d["id"],
                         "vi_sao": "Dòng vé không có TÊN KHÁCH – một cái vé không có người đi thì "
                                   "không phải một cái vé.",
                         "can_lam": "Điền họ tên trên vé, hoặc nối dòng này vào một khách của đoàn."})
        if d["loai"] == "hoan_ve":
            if not (d["ly_do"] or "").strip():
                chan.append({"muc": "chan", "dong_id": d["id"],
                             "vi_sao": "Dòng hoàn vé chưa có LÝ DO.",
                             "can_lam": "Ghi vì sao hoàn: khách huỷ, đổi chuyến, hãng huỷ chuyến…"})
            if tt is not None and tt > 0:
                chan.append({"muc": "chan", "dong_id": d["id"], "so_tien": tt,
                             "vi_sao": "Dòng hoàn vé mang số tiền DƯƠNG – hoàn vé là tiền chảy "
                                       "ngược về công ty nên phải âm.",
                             "can_lam": "Nhập số tiền hoàn với dấu trừ."})
        if d["loai"] == "ve" and tt is not None and tt < 0:
            chan.append({"muc": "chan", "dong_id": d["id"], "so_tien": tt,
                         "vi_sao": "Dòng vé mang số tiền ÂM. Nếu đây là khoản hoàn thì đổi loại "
                                   "dòng sang «Hoàn vé» để nó có lý do và đếm được.",
                         "can_lam": "Đổi loại dòng, hoặc sửa dấu."})
        if d["thanh_tien"] is not None and d["thanh_tien_vnd"] is None:
            canh.append({"muc": "canh_bao", "dong_id": d["id"], "tien_te": d["tien_te"],
                         "vi_sao": f"Dòng ghi bằng {d['tien_te']} nhưng chưa có TỶ GIÁ nên không quy "
                                   "được về đồng Việt Nam.",
                         "can_lam": "Nhập tỷ giá của dòng."})

    for m in b["theo_ma"]:
        thieu = m["con_thieu_ten"]
        if thieu:
            qua_han = bool(m["han_xuat_ve"] and m["han_xuat_ve"] < hom_nay)
            canh.append({
                "muc": "canh_bao", "ma_dat_cho": m["ma_dat_cho"], "con_thieu_ten": thieu,
                "han_xuat_ve": m["han_xuat_ve"], "qua_han": qua_han,
                "vi_sao": (f"Giữ {m['so_cho_giu']} chỗ, mới điền {m['so_ve']} tên"
                           + (f" – ĐÃ QUÁ HẠN XUẤT VÉ {m['han_xuat_ve']}." if qua_han
                              else f", hạn xuất vé {m['han_xuat_ve']}." if m["han_xuat_ve"]
                              else " và chưa đặt hạn xuất vé.")),
                "can_lam": ("Điền nốt tên, hoặc trả chỗ thừa về hãng. Quá hạn thì hãng huỷ chỗ và "
                            "mua lại theo giá hôm huỷ.")})

    ct = _chiet_tinh_ve(db, tour_id)
    tong = b["tong_tien_ve_vnd"]
    if ct is not None and tong is not None and round(abs(tong - ct), 2) >= 1.0:
        canh.append({"muc": "canh_bao", "tong_tien_ve": tong, "chiet_tinh_ve": ct,
                     "lech": round(tong - ct, 2),
                     "vi_sao": "Tổng khối vé lệch so với dòng vé trong bảng chiết tính.",
                     "can_lam": "Sửa một trong hai, hoặc ghi một dòng giải thích vì sao lệch."})

    return {**b, "chan": chan, "canh_bao": canh, "chiet_tinh_ve": ct,
            "duoc_dong_so": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}
