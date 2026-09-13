# -*- coding: utf-8 -*-
"""Đ-7 · Thu hộ – chi hộ: tiền đi ngang qua công ty, KHÔNG phải doanh thu và KHÔNG phải giá vốn.

Đo trên tệp thật:

    QUYẾT TOÁN VISA LẺ CHÂU ÂU T5.2026 — có hẳn một cột "Thu hộ chi hộ": 821.500 đ và 1.200.000 đ,
    nằm ngoài cả cột Tổng thu lẫn cột Tổng chi.

    QuyetToan_27052026_UK, sheet CongNo_HDV — "TL thu của khách 126 GBP (mua dùm khách vé tham
    quan)". Trưởng đoàn cầm 126 £ của khách để đi mua vé hộ họ.

Hai khoản ấy không phải tiền của Vietourist ở bất kỳ thời điểm nào. Nếu chúng lọt vào doanh thu thì
lợi nhuận phồng lên bằng tiền của người khác; lọt vào giá vốn thì lợi nhuận teo đi cũng bằng tiền
của người khác. Cả hai đều sai, và sai theo cách bảng vẫn cân.

--------------------------------------------------------------------------------------------------
VÌ SAO KHÔNG CHẶN KHI THU HỘ ≠ CHI HỘ
--------------------------------------------------------------------------------------------------

Bản đề xuất đầu ngày 12/9 của Robot A viết: "Σ thu hộ = Σ chi hộ, chênh khác 0 là CHẶN".

Làn rà soát (Codex) bác đúng:

    "Cho phép số dư đang chờ trả hoặc chờ thu; theo dõi chủ tiền và hạn xử lý. Chặn sai đối chiếu,
     không chặn đơn thuần vì thu hộ chưa bằng chi hộ."

Thu hôm nay, mua vé ngày mai — đó là hoạt động bình thường, không phải lỗi. Chặn ở đó là chặn đúng
lúc mọi thứ đang chạy đúng, và người ta sẽ học cách không ghi khoản thu hộ nữa để khỏi bị chặn. Khi
ấy tiền của khách biến mất khỏi sổ hoàn toàn — tệ hơn hẳn tình trạng ban đầu.

Nên số dư khác 0 là MỘT VIỆC PHẢI LÀM, không phải một hàng rào:

    số dư = đã thu hộ − đã chi đúng chủ tiền − đã hoàn/nộp trả

Số dư ấy phải có **CHỦ** (trả lại cho ai) và có **HẠN** (bao giờ). Thiếu chủ hoặc quá hạn mới là
chuyện phải kêu — và kêu ở mức cảnh báo có tên người, không phải một dòng đỏ vô danh.

--------------------------------------------------------------------------------------------------
CHỖ DUY NHẤT ĐƯỢC PHÉP CHẶN
--------------------------------------------------------------------------------------------------

Một khoản thu hộ **không biết của ai**. Không có chủ thì không trả lại được cho ai, và một khoản
tiền của người khác nằm trong két công ty mà không ai biết của ai thì đó không còn là thu hộ nữa.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lop3_tour import TourDoanhThuDong, TourHdvChi

# Loại dòng doanh thu dùng cho tiền THU HỘ. Nó nằm trong sổ doanh thu vì đó là nơi ghi tiền vào,
# nhưng MỌI phép cộng doanh thu phải loại nó ra – xem `LOAI_KHONG_PHAI_DOANH_THU`.
LOAI_THU_HO = "thu_ho"

# Danh sách này là hàng rào thật của Đ-7: bất kỳ chỗ nào cộng doanh thu đều phải trừ các loại ở đây.
# Để một chỗ quên là lợi nhuận phồng lên bằng tiền của khách.
LOAI_KHONG_PHAI_DOANH_THU = (LOAI_THU_HO,)

MUC = {"chan": "Chặn – phải xác định chủ tiền",
       "canh_bao": "Cảnh báo – số dư còn treo, có chủ và có hạn"}


def la_doanh_thu(loai: str | None) -> bool:
    """Dòng này có được cộng vào doanh thu không.

    MỘT hàm duy nhất trả lời câu ấy, để không nơi nào tự viết lại điều kiện theo cách của mình.
    """
    return (loai or "") not in LOAI_KHONG_PHAI_DOANH_THU


def so_du(db: Session, tour_id: int, hom_nay: date | None = None) -> dict:
    """Số dư giữ hộ của một chuyến, tách theo CHỦ TIỀN.

    Vế thu: dòng doanh thu loại `thu_ho`.
    Vế chi: dòng chi HDV có cờ `thu_ho_khach` – tiền trưởng đoàn đã tiêu đúng vào việc khách nhờ.
    """
    hom_nay = hom_nay or date.today()

    thu = list(db.scalars(select(TourDoanhThuDong).where(
        TourDoanhThuDong.tour_id == tour_id, TourDoanhThuDong.loai == LOAI_THU_HO)))
    chi = list(db.scalars(select(TourHdvChi).where(
        TourHdvChi.tour_id == tour_id, TourHdvChi.thu_ho_khach == 1)))

    theo_chu: dict[str, dict] = {}

    def _o(ten: str | None) -> dict:
        k = (ten or "").strip()
        if k not in theo_chu:
            theo_chu[k] = {"chu_tien": k, "da_thu_ho": 0.0, "da_chi_ho": 0.0,
                           "han_xu_ly": None, "so_dong": 0}
        return theo_chu[k]

    for d in thu:
        o = _o(getattr(d, "chu_tien", None) or d.ghi_chu)
        o["da_thu_ho"] += float(d.thanh_tien or 0)
        o["so_dong"] += 1
    for d in chi:
        o = _o(getattr(d, "chu_tien", None))
        o["da_chi_ho"] += float(d.thanh_tien or 0)
        o["so_dong"] += 1
        h = getattr(d, "han_xu_ly", None)
        if h and (o["han_xu_ly"] is None or h < o["han_xu_ly"]):
            o["han_xu_ly"] = h
    for d in thu:
        h = getattr(d, "han_xu_ly", None)
        if h:
            o = _o(getattr(d, "chu_tien", None) or d.ghi_chu)
            if o["han_xu_ly"] is None or h < o["han_xu_ly"]:
                o["han_xu_ly"] = h

    dong = []
    for o in theo_chu.values():
        du = round(o["da_thu_ho"] - o["da_chi_ho"], 2)
        dong.append({**o, "so_du": du,
                     "qua_han": bool(o["han_xu_ly"] and du and o["han_xu_ly"] < hom_nay)})
    dong.sort(key=lambda x: (-abs(x["so_du"]), x["chu_tien"]))

    tong_thu = round(sum(x["da_thu_ho"] for x in dong), 2)
    tong_chi = round(sum(x["da_chi_ho"] for x in dong), 2)
    return {"tour_id": tour_id, "da_thu_ho": tong_thu, "da_chi_ho": tong_chi,
            "so_du": round(tong_thu - tong_chi, 2), "theo_chu_tien": dong,
            "ghi_chu": ("Khoản thu hộ – chi hộ KHÔNG vào doanh thu và KHÔNG vào giá vốn. "
                        "Số dư khác 0 là bình thường (thu hôm nay, trả ngày mai); nó chỉ phải có "
                        "chủ và có hạn.")}


def soat(db: Session, tour_id: int, hom_nay: date | None = None) -> dict:
    """Chấm phần thu hộ trước khi đóng số.

    CHẶN đúng một chuyện: khoản thu hộ không biết của ai. CẢNH BÁO cho số dư quá hạn và số dư chưa
    đặt hạn. Số dư còn treo trong hạn thì KHÔNG nói gì – đó là hoạt động bình thường.
    """
    sd = so_du(db, tour_id, hom_nay)
    chan, canh = [], []
    for x in sd["theo_chu_tien"]:
        if not x["so_du"]:
            continue
        if not x["chu_tien"]:
            chan.append({"muc": "chan", "so_tien": x["so_du"],
                         "vi_sao": "Khoản thu hộ chưa xác định CHỦ TIỀN – không biết trả lại cho ai.",
                         "can_lam": "Điền ô «Chủ tiền» trên các dòng thu hộ của chuyến."})
            continue
        if x["qua_han"]:
            canh.append({"muc": "canh_bao", "chu_tien": x["chu_tien"], "so_tien": x["so_du"],
                         "han_xu_ly": x["han_xu_ly"],
                         "vi_sao": f"Quá hạn xử lý ({x['han_xu_ly']}) mà số dư vẫn còn."})
        elif x["han_xu_ly"] is None:
            canh.append({"muc": "canh_bao", "chu_tien": x["chu_tien"], "so_tien": x["so_du"],
                         "han_xu_ly": None,
                         "vi_sao": "Số dư giữ hộ chưa đặt HẠN XỬ LÝ – không có hạn thì nó nằm đó mãi "
                                   "và không thành việc của ai."})
    return {**sd, "chan": chan, "canh_bao": canh,
            "duoc_dong_so": not chan, "so_chan": len(chan), "so_canh_bao": len(canh)}
