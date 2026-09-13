# -*- coding: utf-8 -*-
"""Đ-4 · Nhiều bên bán trên một chuyến (ghép land) — và Đ-6b hoàn tiền tip về bên bán.

Phần đo trên tệp thật nằm ở `app/models/lop3_tour.py`, khối Đ-4. Tệp này là phép tính và phép soát.

──────────────────────────────────────────────────────────────────────────────────────────────────
MỘT ĐIỀU HỆ THỐNG CỐ Ý KHÔNG LÀM: TỰ ĐIỀN SỐ LƯỢNG
──────────────────────────────────────────────────────────────────────────────────────────────────

Trực giác nói: bên có 3 khách thì mọi dòng nhân 3. Tệp thật nói khác — tờ J TRAVEL có 3 khách mà
dòng "VISA người lớn 4 pax" ghi số lượng 4, tờ VTOURIST có 5 khách mà dòng VISA ghi 6. Có khách đã
sẵn visa, có người mua visa mà không đi.

Nên số lượng là ô người nhập, và hệ thống chỉ CẢNH BÁO khi nó khác số khách của bên. Tự điền là
biến một sự thật nghiệp vụ thành một lỗi lặng lẽ; chặn lại còn tệ hơn, vì khi ấy tờ đúng không nhập
được.

──────────────────────────────────────────────────────────────────────────────────────────────────
CHỖ DUY NHẤT ĐƯỢC PHÉP CHẶN
──────────────────────────────────────────────────────────────────────────────────────────────────

Tổng khách của các bên KHÁC số khách đã ghi trên chuyến. Đó không phải một khoản lệch để giải
trình — nó nghĩa là có người ngồi trên xe mà không thuộc bên nào, hoặc một bên khai thừa. Cả hai đều
làm mọi phép chia theo đầu khách bên dưới sai theo, và sai theo cách tổng vẫn cân.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import (BookingKhach, CACH_CHIA, LOAI_DONG_BEN_BAN, TourBenBan,
                                  TourBenBanDong)
from app.services import tip_tour as TIP

MUC = {"chan": "Chặn – số khách không khớp thì mọi phép chia bên dưới sai theo",
       "canh_bao": "Cảnh báo – cần một dòng chữ hoặc một lần nhìn lại"}

# Loại dòng làm TĂNG nợ của bên bán. Các loại còn lại làm giảm.
LOAI_TANG_NO = ("phan_bo",)


def thanh_tien_dong(don_gia: float | None, so_luong: float | None) -> float | None:
    """Đơn giá × số lượng. Rỗng ở BẤT KỲ vế nào thì thành tiền là CHƯA CÓ, không phải 0."""
    if don_gia is None or so_luong is None:
        return None
    return round(float(don_gia) * float(so_luong), 2)


def _so_khach(b: TourBenBan) -> int | None:
    """Số khách của một bên. None khi CHƯA khai ô nào – khác hẳn 0 khách."""
    o = [b.so_khach_nguoi_lon, b.so_khach_tre_em, b.so_khach_em_be]
    if all(x is None for x in o):
        return None
    return sum(int(x) for x in o if x is not None)


def bang(db: Session, tour_id: int) -> dict:
    """Tờ quyết toán của TỪNG bên bán, và số dư của từng bên."""
    bens = list(db.scalars(select(TourBenBan).where(TourBenBan.tour_id == tour_id)
                           .order_by(TourBenBan.id)))
    dongs = list(db.scalars(select(TourBenBanDong).where(TourBenBanDong.tour_id == tour_id)
                            .order_by(TourBenBanDong.stt, TourBenBanDong.id)))

    ra = []
    for b in bens:
        cua = [d for d in dongs if d.ben_ban_id == b.id]
        no = tra = 0.0
        co_no = co_tra = False
        ds = []
        for d in cua:
            tt = d.thanh_tien if d.thanh_tien is not None else thanh_tien_dong(d.don_gia, d.so_luong)
            if tt is not None:
                if d.loai in LOAI_TANG_NO:
                    no += tt
                    co_no = True
                elif d.loai == "thanh_toan":
                    tra += tt
                    co_tra = True
                else:
                    # hoan_tip / giam_tru: tệp thật đã ghi sẵn số ÂM, nên CỘNG vào vế nợ chứ không
                    # trừ hai lần. Bộ soát bên dưới bắt khi dấu đi ngược điều này.
                    no += tt
                    co_no = True
            ds.append({
                "id": d.id, "stt": d.stt, "noi_dung": d.noi_dung, "loai": d.loai,
                "loai_ten": LOAI_DONG_BEN_BAN.get(d.loai, d.loai),
                "cach_chia": d.cach_chia, "cach_chia_ten": CACH_CHIA.get(d.cach_chia or ""),
                "don_gia": d.don_gia, "so_luong": d.so_luong, "thanh_tien": tt,
                "ngay": d.ngay, "so_chung_tu": d.so_chung_tu, "ghi_chu": d.ghi_chu,
            })
        sk = _so_khach(b)
        ra.append({
            "id": b.id, "ten_ben": b.ten_ben, "la_vietourist": bool(b.la_vietourist),
            "mst": b.mst, "so_khach": sk,
            "so_khach_nguoi_lon": b.so_khach_nguoi_lon, "so_khach_tre_em": b.so_khach_tre_em,
            "so_khach_em_be": b.so_khach_em_be,
            "dong": ds, "so_dong": len(ds),
            "tong_phai_thu": round(no, 2) if co_no else None,
            "da_thanh_toan": round(tra, 2) if co_tra else None,
            "con_phai_thu": (round(no - tra, 2) if (co_no or co_tra) else None),
            "ghi_chu": b.ghi_chu,
        })

    sk_ben = [x["so_khach"] for x in ra if x["so_khach"] is not None]
    return {
        "tour_id": tour_id, "ben": ra, "so_ben": len(ra),
        "tong_khach_cac_ben": (sum(sk_ben) if sk_ben else None),
        "so_ben_chua_khai_khach": len([x for x in ra if x["so_khach"] is None]),
        "ghi_chu": ("Vietourist cũng là MỘT dòng bên bán, không phải phần còn lại sau khi trừ các "
                    "đại lý – để nó là phần còn lại thì lúc số khách lệch, phần thiếu tự chảy vào "
                    "Vietourist mà không ai thấy."),
    }


def _khach_tren_chuyen(db: Session, tour_id: int) -> int | None:
    n = len(list(db.scalars(select(BookingKhach).where(BookingKhach.tour_id == tour_id))))
    return n or None


def soat(db: Session, tour_id: int) -> dict:
    """Chấm phần nhiều bên bán trước khi đóng số."""
    b = bang(db, tour_id)
    chan, canh = [], []

    tong_ben = b["tong_khach_cac_ben"]
    tren_chuyen = _khach_tren_chuyen(db, tour_id)
    if tong_ben is not None and tren_chuyen is not None and tong_ben != tren_chuyen:
        chan.append({
            "muc": "chan", "tong_khach_cac_ben": tong_ben, "khach_tren_chuyen": tren_chuyen,
            "lech": tong_ben - tren_chuyen,
            "vi_sao": (f"Các bên bán cộng lại {tong_ben} khách, nhưng danh sách khách của chuyến có "
                       f"{tren_chuyen} người. Nghĩa là có người ngồi trên xe mà không thuộc bên nào, "
                       "hoặc một bên khai thừa."),
            "can_lam": "Sửa số khách của bên, hoặc bổ sung dòng khách còn thiếu."})

    if b["so_ben_chua_khai_khach"]:
        canh.append({"muc": "canh_bao", "so_ben": b["so_ben_chua_khai_khach"],
                     "vi_sao": f"{b['so_ben_chua_khai_khach']} bên chưa khai số khách – chưa so được "
                               "với danh sách khách của chuyến.",
                     "can_lam": "Điền số khách của từng bên."})

    if b["so_ben"] > 1 and not any(x["la_vietourist"] for x in b["ben"]):
        canh.append({"muc": "canh_bao",
                     "vi_sao": "Chuyến có nhiều bên bán nhưng chưa bên nào được đánh dấu là "
                               "VIETOURIST – phần khách của chính công ty đang không có tờ nào.",
                     "can_lam": "Đánh dấu bên của Vietourist, hoặc thêm nó vào danh sách."})

    for x in b["ben"]:
        for d in x["dong"]:
            tt = d["thanh_tien"]
            if tt is None:
                continue
            # Dấu phải đi đúng chiều với loại dòng. Đây là cùng một cái lưới đã dùng ở Đ-9: một dòng
            # hoàn tip ghi số dương làm nợ của đại lý PHỒNG LÊN thay vì giảm đi.
            if d["loai"] in ("hoan_tip", "giam_tru") and tt > 0:
                chan.append({
                    "muc": "chan", "ben": x["ten_ben"], "dong_id": d["id"], "so_tien": tt,
                    "vi_sao": (f"«{d['loai_ten']}» đang ghi số DƯƠNG – khoản giảm trừ mà mang dấu "
                               "dương thì nợ của bên bán phồng lên thay vì giảm đi."),
                    "can_lam": "Nhập số tiền với dấu trừ."})
            if d["loai"] == "phan_bo" and tt < 0:
                canh.append({
                    "muc": "canh_bao", "ben": x["ten_ben"], "dong_id": d["id"], "so_tien": tt,
                    "vi_sao": "Dòng phân bổ mang số ÂM. Nếu đây là khoản hoàn hoặc giảm trừ thì đổi "
                              "loại dòng để nó đếm được riêng.",
                    "can_lam": "Đổi loại dòng, hoặc sửa dấu."})
            # Điều 1 ở đầu tệp: KHÔNG tự điền, chỉ nói ra.
            if (d["loai"] == "phan_bo" and d["cach_chia"] == "moi_khach"
                    and d["so_luong"] is not None and x["so_khach"] is not None
                    and float(d["so_luong"]) != float(x["so_khach"])):
                canh.append({
                    "muc": "canh_bao", "ben": x["ten_ben"], "dong_id": d["id"],
                    "so_luong": d["so_luong"], "so_khach": x["so_khach"],
                    "vi_sao": (f"Dòng «{d['noi_dung']}» tính cho {d['so_luong']} suất trong khi bên "
                               f"này có {x['so_khach']} khách."),
                    "can_lam": ("Chuyện này có thật – khách đã sẵn visa, hoặc người mua visa mà "
                                "không đi. Ghi một dòng chú thích để người đọc sau không phải đoán.")})

    return {**b, "khach_tren_chuyen": tren_chuyen, "chan": chan, "canh_bao": canh,
            "duoc_dong_so": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Đ-6b · HOÀN TIỀN TIP VỀ BÊN BÁN
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# `tip_tour.hoan_cho_ben_ban()` đã viết xong từ 12/9 và cố ý nhận sẵn `{tên bên: số khách}` thay vì
# tự đi tìm — vì lúc ấy bảng bên bán chưa có. Giờ nó có, nên chỗ này chỉ là cái cầu, không phải một
# phép chia thứ hai.
#
# Đo chéo trên hai tệp khác nhau: tệp châu Âu ghi tip 3 €/khách/ngày × 9 ngày = 27 €/khách cả
# chuyến; tệp AU ghi "TIP HDV hoàn cho JTR −837.000/pax". Và 27 × 31.000 = 837.000. Cùng một khoản
# tiền, hai tờ giấy, khớp đến từng đồng.


def xem_truoc_hoan_tip(db: Session, tour_id: int, *, don_gia: float | None, don_vi: str | None,
                       so_ngay: int | None = None, ty_gia: float | None = None) -> dict:
    """Tính thử tiền tip phải hoàn về từng bên bán KHÔNG PHẢI Vietourist.

    KHÔNG ghi gì vào cơ sở dữ liệu. Người nhập nhìn con số rồi mới bấm ghi — cùng cách làm với ô
    tiền tip ở Đ-6, và vì cùng một lý do: đơn vị tip nhập sai là ra gấp chín lần.

    Bên của Vietourist bị loại ra: công ty không hoàn tiền cho chính mình.
    """
    b = bang(db, tour_id)
    ngoai = {x["ten_ben"]: x["so_khach"] for x in b["ben"]
             if not x["la_vietourist"] and x["so_khach"]}
    tien = TIP.hoan_cho_ben_ban(don_gia, don_vi, so_ngay, ngoai, ty_gia)
    canh = TIP.canh_bao_phan_tram(don_gia) if don_gia is not None else ""
    return {
        "tour_id": tour_id, "don_vi": don_vi, "don_vi_ten": TIP.DON_VI_TIP.get(don_vi or ""),
        "so_ngay": so_ngay, "ty_gia": ty_gia,
        "theo_ben": [{"ten_ben": k, "so_khach": ngoai[k], "so_tien_hoan": v}
                     for k, v in tien.items()],
        "tong_hoan": round(sum(tien.values()), 2) if tien else None,
        "so_ben_bo_qua_vi_la_vietourist": len([x for x in b["ben"] if x["la_vietourist"]]),
        "canh_bao": canh,
        "ghi_chu": ("Ghi vào tờ của bên bán là một dòng loại «hoan_tip» mang số ÂM – nó làm GIẢM nợ "
                    "của đại lý. Đây là tính thử, chưa ghi gì."),
    }
