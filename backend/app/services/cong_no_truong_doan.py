# -*- coding: utf-8 -*-
"""Đ-9 · Công nợ trưởng đoàn: mỗi đồng tiền một số dư, quy về VND ở bước cuối cùng.

QUY ƯỚC DẤU – Chủ tịch chốt 12/9/2026, và hệ thống chỉ có MỘT quy ước:

        DƯƠNG  =  CÔNG TY CÒN PHẢI TRẢ TRƯỞNG ĐOÀN
        ÂM     =  TRƯỞNG ĐOÀN CÒN PHẢI NỘP LẠI CHO CÔNG TY

Phần đo trên hai tệp mẫu – và chỗ tệp châu Âu ghi ngược dấu so với chính nhãn của nó – nằm ở
`app/models/lop3_tour.py`, khối Đ-9. Tệp này là phép tính.

──────────────────────────────────────────────────────────────────────────────────────────────────
VÌ SAO KHÔNG CỘNG GỘP CÁC ĐỒNG TIỀN SỚM
──────────────────────────────────────────────────────────────────────────────────────────────────

Người ta trả cho trưởng đoàn bằng từng đồng tiền một: 450 USD tiền mặt ở sân bay, 95,21 GBP nộp lại
bằng chuyển khoản. Cộng gộp thành "8.497.440 đ" rồi mới đi trả là làm mất chính thông tin cần để
trả – và trên tờ UK, con số gộp ấy còn ngược chiều với một trong hai vế (công ty trả USD, nhưng thu
lại GBP).

Nên `so_du()` trả về:
    · một số dư cho MỖI đồng tiền  – đây là số dùng để đi trả tiền;
    · một con số VND gộp lại       – chỉ để đưa vào giá vốn và báo cáo.

Con số gộp là None khi có bất kỳ đồng tiền nào chưa có tỷ giá. KHÔNG lấy 0 thay cho tỷ giá thiếu:
450 USD nhân 0 bằng 0 và tờ quyết toán vẫn cân, đúng kiểu sai mà không ai nhìn thấy.

──────────────────────────────────────────────────────────────────────────────────────────────────
CÁI LƯỚI BẮT LỖI ĐỔI DẤU
──────────────────────────────────────────────────────────────────────────────────────────────────

Mỗi dòng khai `loai`, và mỗi loại có một CHIỀU đáng lẽ phải có (LOAI_CONG_NO_TL trong models). Công
tác phí thì công ty nợ trưởng đoàn – dấu dương. Tiền tip nộp về công ty thì ngược lại – dấu âm.

Khi dấu của số tiền mâu thuẫn với chiều của loại, bộ soát CHẶN. Đó chính là lúc người nhập vừa chép
tờ châu Âu vào mà quên đổi dấu, và là lỗi duy nhất ở đây có thể làm cả tờ quyết toán ra kết quả
ngược mà mọi tổng vẫn cân.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import LOAI_CONG_NO_TL, TourTlCongNo

VND = "VND"

MUC = {"chan": "Chặn – dấu mâu thuẫn với loại khoản, kết quả sẽ ngược chiều",
       "canh_bao": "Cảnh báo – chưa quy đổi được về đồng Việt Nam"}

# Câu chữ in ngay cạnh ô nhập trên biểu. Để ở đây chứ không gõ lại trong tệp giao diện: một quy ước
# dấu viết ở hai chỗ là một quy ước sẽ có ngày lệch nhau.
CAU_QUY_UOC = ("DƯƠNG = công ty còn phải TRẢ trưởng đoàn · ÂM = trưởng đoàn còn phải NỘP LẠI. "
               "Tờ quyết toán châu Âu ghi ngược quy ước này ở dòng cuối – khi chép vào phải đổi dấu.")


def chieu_cua_loai(loai: str | None) -> int | None:
    """+1 nếu loại khoản này đáng lẽ dương, −1 nếu đáng lẽ âm, None nếu loại không khai."""
    x = LOAI_CONG_NO_TL.get(loai or "")
    return x[0] if x else None


def _chuan(x: str | None) -> str:
    return (x or VND).strip().upper() or VND


def so_du(db: Session, tour_id: int, phan_cong_id: int | None = None) -> dict:
    """Số dư công nợ trưởng đoàn: theo từng đồng tiền, rồi mới gộp về VND.

    Lọc theo `phan_cong_id` khi một chuyến có hơn một trưởng đoàn – hai người thì hai tờ, và cộng
    chung hai người lại là mất đúng thông tin "ai nợ ai".
    """
    q = select(TourTlCongNo).where(TourTlCongNo.tour_id == tour_id)
    if phan_cong_id is not None:
        q = q.where(TourTlCongNo.phan_cong_id == phan_cong_id)
    ds = list(db.scalars(q.order_by(TourTlCongNo.stt, TourTlCongNo.id)))

    theo_tien: dict[str, dict] = {}
    dong = []
    for d in ds:
        tt = _chuan(d.tien_te)
        st = None if d.so_tien is None else float(d.so_tien)
        o = theo_tien.setdefault(tt, {"tien_te": tt, "so_du": 0.0, "so_dong": 0,
                                      "ty_gia": None, "so_dong_chua_co_so": 0})
        o["so_dong"] += 1
        if st is None:
            o["so_dong_chua_co_so"] += 1
        else:
            o["so_du"] += st
        # Tỷ giá của đồng tiền lấy từ dòng ĐẦU TIÊN khai nó. Nếu hai dòng cùng đồng tiền khai hai
        # tỷ giá khác nhau thì đó là chuyện phải kêu, không phải chuyện để trung bình cộng.
        if d.ty_gia is not None and float(d.ty_gia):
            tg = float(d.ty_gia)
            cu = o["ty_gia"]
            if cu is None:
                o["ty_gia"] = tg
            elif abs(cu - tg) > 1e-9:
                o["ty_gia_lech"] = True
        dong.append({
            "id": d.id, "stt": d.stt, "noi_dung": d.noi_dung, "loai": d.loai,
            "loai_ten": (LOAI_CONG_NO_TL.get(d.loai or "") or (None, d.loai))[1],
            "chieu_dung": chieu_cua_loai(d.loai),
            "so_tien": st, "tien_te": tt, "ty_gia": d.ty_gia,
            "ten_truong_doan": d.ten_truong_doan, "phan_cong_id": d.phan_cong_id,
            "hdv_chi_id": d.hdv_chi_id, "da_thanh_toan": bool(d.da_thanh_toan),
            "ghi_chu": d.ghi_chu,
        })

    ds_tien = []
    quy_duoc = True
    tong_vnd = 0.0
    for o in theo_tien.values():
        o["so_du"] = round(o["so_du"], 2)
        if o["tien_te"] == VND:
            o["so_du_vnd"] = o["so_du"]
        elif o["ty_gia"]:
            o["so_du_vnd"] = round(o["so_du"] * o["ty_gia"], 2)
        else:
            o["so_du_vnd"] = None
        if o["so_du_vnd"] is None:
            quy_duoc = False
        else:
            tong_vnd += o["so_du_vnd"]
        o["ai_no_ai"] = ("Công ty còn phải trả trưởng đoàn" if o["so_du"] > 0 else
                         "Trưởng đoàn còn phải nộp lại" if o["so_du"] < 0 else "Đã cân")
        ds_tien.append(o)
    ds_tien.sort(key=lambda x: x["tien_te"])

    tong = round(tong_vnd, 2) if (ds_tien and quy_duoc) else None
    return {
        "tour_id": tour_id, "phan_cong_id": phan_cong_id,
        "quy_uoc_dau": CAU_QUY_UOC,
        "dong": dong, "theo_tien_te": ds_tien,
        "so_du_vnd": tong,
        "ai_no_ai": (None if tong is None else
                     "Công ty còn phải trả trưởng đoàn" if tong > 0 else
                     "Trưởng đoàn còn phải nộp lại" if tong < 0 else "Đã cân"),
        "ghi_chu": ("Mỗi đồng tiền một số dư riêng – đó là số dùng để đi trả tiền. Con số VND gộp "
                    "chỉ để đưa vào giá vốn và báo cáo, và nó KHÔNG có khi còn đồng tiền thiếu tỷ giá."),
    }


def soat(db: Session, tour_id: int, phan_cong_id: int | None = None) -> dict:
    """Chấm tờ công nợ trưởng đoàn trước khi đóng số."""
    sd = so_du(db, tour_id, phan_cong_id)
    chan, canh = [], []

    for d in sd["dong"]:
        if d["chieu_dung"] is None:
            chan.append({"muc": "chan", "dong_id": d["id"], "loai": d["loai"],
                         "vi_sao": f"Loại khoản «{d['loai']}» không có trong danh mục – không biết "
                                   "khoản này làm công ty nợ trưởng đoàn hay ngược lại.",
                         "can_lam": "Chọn lại loại khoản từ danh sách."})
            continue
        st = d["so_tien"]
        if st is None or st == 0:
            continue
        if (st > 0) != (d["chieu_dung"] > 0):
            dung = "DƯƠNG" if d["chieu_dung"] > 0 else "ÂM"
            chan.append({
                "muc": "chan", "dong_id": d["id"], "stt": d["stt"], "noi_dung": d["noi_dung"],
                "loai": d["loai"], "so_tien": st, "tien_te": d["tien_te"],
                "vi_sao": (f"«{d['loai_ten']}» đáng lẽ phải mang dấu {dung}, nhưng đang ghi "
                           f"{st:+,.2f}. Sai dấu ở đây làm cả tờ ra kết quả NGƯỢC CHIỀU mà mọi tổng "
                           "vẫn cân."),
                "can_lam": ("Đổi dấu số tiền, hoặc chọn lại loại khoản. " + CAU_QUY_UOC)})

    for o in sd["theo_tien_te"]:
        if o.get("ty_gia_lech"):
            chan.append({"muc": "chan", "tien_te": o["tien_te"],
                         "vi_sao": f"Cùng đồng {o['tien_te']} nhưng các dòng khai HAI tỷ giá khác "
                                   "nhau – không có cách nào chọn hộ một cái đúng.",
                         "can_lam": "Thống nhất một tỷ giá cho đồng tiền này trong tờ quyết toán."})
        if o["so_du_vnd"] is None and o["so_du"]:
            canh.append({"muc": "canh_bao", "tien_te": o["tien_te"], "so_du": o["so_du"],
                         "vi_sao": f"Số dư {o['so_du']:+,.2f} {o['tien_te']} chưa có TỶ GIÁ nên "
                                   "không quy được về đồng Việt Nam.",
                         "can_lam": "Nhập tỷ giá đã dùng khi thanh toán cho đồng tiền này."})
        if o["so_dong_chua_co_so"]:
            canh.append({"muc": "canh_bao", "tien_te": o["tien_te"],
                         "so_dong": o["so_dong_chua_co_so"],
                         "vi_sao": f"{o['so_dong_chua_co_so']} dòng {o['tien_te']} chưa nhập số tiền.",
                         "can_lam": "Nhập nốt, hoặc xoá dòng trống."})

    return {**sd, "chan": chan, "canh_bao": canh,
            "duoc_dong_so": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}
