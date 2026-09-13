# -*- coding: utf-8 -*-
"""Đ-12 · Đề nghị chi phí lãnh sự: mỗi khách một dòng, và một người không được đứng hai lần.

Phần đo trên tệp thật nằm ở `app/models/lop3_tour.py`, khối Đ-12. Tệp này là phép tính và phép soát.

──────────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO KHÔNG CÀI MỐC TUỔI NÀO
──────────────────────────────────────────────────────────────────────────────────────────────────

Trên tệp AU, một khách sinh 30.10.2015 trả 1.403.500 – đúng một nửa. Một khách khác sinh 23.09.2013
trả nguyên giá 2.807.000. Mốc nằm đâu đó giữa 11 và 13 tuổi, và nó là quy định của LÃNH SỰ QUÁN,
khác nhau theo thị trường và đổi theo thời kỳ.

Đoán một con số rồi áp cho mọi thị trường là cách chắc chắn để sai ở thị trường thứ hai mà không ai
kiểm ra. Nên biểu phí sống ở `bang_gia` / `bang_gia_dong` – bảng đã có sẵn, có khoảng hiệu lực và có
hạng khách – và do NHÂN VIÊN TEAM VISA khai. Ở đây chỉ có ô nhập và phép cộng.

──────────────────────────────────────────────────────────────────────────────────────────────────
CHỖ HỆ THỐNG SOI ĐƯỢC, VÀ NÓ ĐÁNG GIÁ HƠN MỐC TUỔI
──────────────────────────────────────────────────────────────────────────────────────────────────

MỘT NGƯỜI XUẤT HIỆN HAI LẦN trong cùng một đề nghị. Nộp trùng thì chi trùng, và ở mức 2,8 triệu một
suất thì một dòng lặp là tiền thật đi ra khỏi công ty. Máy đối chiếu họ tên + ngày sinh – hai thứ
người nhập gõ sẵn, không phải bắt họ khai thêm gì.

Đối chiếu theo HỌ TÊN ĐÃ CHUẨN HOÁ (bỏ dấu cách thừa, không phân biệt hoa thường) vì tệp thật gõ tên
theo hộ chiếu, không dấu, và khoảng trắng thừa là chuyện thường.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import DeNghiLanhSu, DeNghiLanhSuDong

MUC = {"chan": "Chặn – dòng không có nghĩa, hoặc tiền có thể đi trùng",
       "canh_bao": "Cảnh báo – cần một lần nhìn lại"}

O_PHI = ("phi_tls_cao_cap", "phi_tls_co_ban", "phi_lsq")


def thanh_tien_dong(d: DeNghiLanhSuDong) -> float | None:
    """Cộng ba ô phí. Trả None khi CẢ BA đều rỗng – dòng chưa nhập, không phải dòng 0 đồng."""
    o = [d.phi_tls_cao_cap, d.phi_tls_co_ban, d.phi_lsq]
    if all(x is None for x in o):
        return None
    return round(sum(float(x) for x in o if x is not None), 2)


def _khoa_nguoi(ho_ten: str | None, ngay_sinh) -> str | None:
    """Khoá nhận dạng một người: họ tên chuẩn hoá + ngày sinh.

    Thiếu MỘT trong hai thì không nhận dạng được, và KHÔNG được đoán – hai người trùng tên là
    chuyện bình thường, gộp nhầm họ còn tệ hơn bỏ sót.
    """
    ten = re.sub(r"\s+", " ", (ho_ten or "")).strip().upper()
    if not ten or ngay_sinh is None:
        return None
    return f"{ten}|{ngay_sinh}"


def bang(db: Session, de_nghi_id: int) -> dict:
    t = db.get(DeNghiLanhSu, de_nghi_id)
    if t is None:
        return {"de_nghi_id": de_nghi_id, "co": False, "dong": []}
    ds = list(db.scalars(select(DeNghiLanhSuDong)
                         .where(DeNghiLanhSuDong.de_nghi_id == de_nghi_id)
                         .order_by(DeNghiLanhSuDong.stt, DeNghiLanhSuDong.id)))
    dong, co_so = [], []
    for d in ds:
        tt = d.thanh_tien if d.thanh_tien is not None else thanh_tien_dong(d)
        if tt is not None:
            co_so.append(tt)
        dong.append({
            "id": d.id, "stt": d.stt, "ho_ten": d.ho_ten, "gioi_tinh": d.gioi_tinh,
            "ngay_sinh": d.ngay_sinh, "sale": d.sale, "ben_ban_id": d.ben_ban_id,
            "khach_id": d.khach_id, "mst": d.mst,
            "phi_tls_cao_cap": d.phi_tls_cao_cap, "phi_tls_co_ban": d.phi_tls_co_ban,
            "phi_lsq": d.phi_lsq, "thanh_tien": tt, "ghi_chu": d.ghi_chu,
        })

    def _cot(ten: str) -> float | None:
        v = [float(getattr(x, ten)) for x in ds if getattr(x, ten) is not None]
        return round(sum(v), 2) if v else None

    return {
        "de_nghi_id": de_nghi_id, "co": True, "ma": t.ma, "tour_id": t.tour_id,
        "thi_truong": t.thi_truong, "ngay": t.ngay, "trang_thai": t.trang_thai,
        "don_vi_thu": t.don_vi_thu, "mst_don_vi_thu": t.mst_don_vi_thu,
        "dong": dong, "so_dong": len(ds),
        "so_dong_chua_co_so": len([x for x in dong if x["thanh_tien"] is None]),
        # Tổng theo TỪNG CỘT, đúng như tệp thật – Kế toán đối chiếu theo cột, không theo dòng.
        "tong_phi_tls_cao_cap": _cot("phi_tls_cao_cap"),
        "tong_phi_tls_co_ban": _cot("phi_tls_co_ban"),
        "tong_phi_lsq": _cot("phi_lsq"),
        "tong_thanh_toan": round(sum(co_so), 2) if co_so else None,
        "ghi_chu": ("Biểu phí không nằm trong mã nguồn: nó ở bang_gia / bang_gia_dong và do nhân "
                    "viên team Visa khai, vì mốc tuổi giảm phí là quy định của từng lãnh sự quán."),
    }


def soat(db: Session, de_nghi_id: int) -> dict:
    """Chấm tờ đề nghị trước khi trình duyệt."""
    b = bang(db, de_nghi_id)
    if not b.get("co"):
        return {**b, "chan": [], "canh_bao": [], "duoc_trinh": False,
                "so_chan": 0, "so_canh_bao": 0}
    chan, canh = [], []

    dem: dict[str, list] = {}
    for d in b["dong"]:
        if not (d["ho_ten"] or "").strip():
            chan.append({"muc": "chan", "dong_id": d["id"], "stt": d["stt"],
                         "vi_sao": "Dòng không có HỌ TÊN – không biết đề nghị chi cho ai.",
                         "can_lam": "Điền họ tên theo hộ chiếu."})
            continue
        if d["thanh_tien"] is None:
            chan.append({"muc": "chan", "dong_id": d["id"], "ho_ten": d["ho_ten"],
                         "vi_sao": "Cả ba ô phí đều để trống – dòng này không đề nghị chi gì cả.",
                         "can_lam": "Nhập ít nhất một khoản phí, hoặc xoá dòng."})
        if d["thanh_tien"] is not None and d["thanh_tien"] < 0:
            chan.append({"muc": "chan", "dong_id": d["id"], "ho_ten": d["ho_ten"],
                         "so_tien": d["thanh_tien"],
                         "vi_sao": "Đề nghị chi mang số ÂM.",
                         "can_lam": "Khoản hoàn phí không đi qua tờ đề nghị chi – ghi ở sổ thu."})
        if d["ngay_sinh"] is None:
            canh.append({"muc": "canh_bao", "dong_id": d["id"], "ho_ten": d["ho_ten"],
                         "vi_sao": "Chưa có NGÀY SINH – không đối chiếu trùng được, và mức phí "
                                   "giảm cho trẻ em cũng không kiểm được.",
                         "can_lam": "Điền ngày sinh theo hộ chiếu."})
        k = _khoa_nguoi(d["ho_ten"], d["ngay_sinh"])
        if k:
            dem.setdefault(k, []).append(d)

    for k, ds in dem.items():
        if len(ds) > 1:
            tong = round(sum(x["thanh_tien"] or 0 for x in ds), 2)
            chan.append({
                "muc": "chan", "ho_ten": ds[0]["ho_ten"], "ngay_sinh": ds[0]["ngay_sinh"],
                "so_lan": len(ds), "dong_id": [x["id"] for x in ds], "tong_tien": tong,
                "vi_sao": (f"«{ds[0]['ho_ten']}» đứng {len(ds)} lần trên cùng một tờ đề nghị, cộng "
                           f"lại {tong:,.0f} đ. Nộp trùng thì chi trùng."),
                "can_lam": ("Xoá dòng thừa. Nếu đúng là hai người trùng tên và trùng cả ngày sinh "
                            "thì ghi số hộ chiếu vào ô ghi chú của từng dòng.")})

    # Cột SALE của tệp thật có cả tên đại lý. Khoản phí của khách đại lý phải chảy về tờ công nợ
    # của họ (Đ-4), không tính vào giá vốn của Vietourist.
    chua_noi = [d for d in b["dong"]
                if (d["sale"] or "").strip() and d["ben_ban_id"] is None
                and (d["sale"] or "").strip().upper() == (d["sale"] or "").strip()
                and " " not in (d["sale"] or "").strip()]
    if chua_noi and b.get("tour_id"):
        canh.append({
            "muc": "canh_bao", "so_dong": len(chua_noi),
            "sale": sorted({(d["sale"] or "").strip() for d in chua_noi}),
            "vi_sao": ("Ô SALE ghi một tên viết liền kiểu tên đại lý nhưng dòng chưa nối vào bên "
                       "bán nào. Nếu đúng là khách của đại lý thì khoản phí này phải chảy về tờ "
                       "công nợ của họ, không vào giá vốn của Vietourist."),
            "can_lam": "Chọn bên bán cho những dòng ấy, hoặc bỏ qua nếu SALE là nhân viên."})

    return {**b, "chan": chan, "canh_bao": canh,
            "duoc_trinh": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}
