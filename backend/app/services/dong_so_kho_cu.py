# -*- coding: utf-8 -*-
"""ĐÓNG SỐ BÙ cho kho quyết toán cũ T1–T6/2026 — Chủ tịch ký thay các phòng ban.

══════════════════════════════════════════════════════════════════════════════════════════════════
CHỦ TỊCH CHỐT 17/9/2026
══════════════════════════════════════════════════════════════════════════════════════════════════

    "Vì đây là nhập dữ liệu cũ lên hệ thống nên em để Chủ tịch ký thay toàn bộ các phòng ban luôn.
     Khi nào vào vận hành chính thức thì phòng nào ký phòng đó, đúng vai trò thiết lập."

Nên cửa này TỒN TẠI CHO ĐÚNG MỘT LÔ: chuyến do kho quyết toán cũ dựng ra. Nó không phải một lối
tắt của cửa đóng số thật (`services/tours.close`), và không được dùng cho chuyến vận hành.

══════════════════════════════════════════════════════════════════════════════════════════════════
VẤN ĐỀ ĐO ĐƯỢC NGÀY 17/9/2026
══════════════════════════════════════════════════════════════════════════════════════════════════

Màn hình Chủ tịch (khối Kết quả kinh doanh) hiện RỖNG năm tháng đầu năm:

    T1 · T2 · T3 · T4 · T5 = null        T6 = 8,85 tỷ    T7 = 19,25 tỷ    T8 = 13,81 tỷ

Nhưng tiền CÓ trong hệ. Đếm cùng ngày: 765 chuyến T1–T6/2026, trong đó **456 chuyến T1–T5 không có
`closed_at`** — và `ket_qua_that.thang()` lọc đúng theo cột ấy:

    select(Tour).where(Tour.status.in_(DA_DONG_SO), Tour.closed_at >= dau, Tour.closed_at < cuoi)

Cửa nạp kho cũ ghi `bookings` + `tour_cost_lines` nhưng CỐ Ý không ghi `tours.actual_revenue` /
`actual_cost` / `closed_at` — vì đóng số là hành vi của Điều hành, không phải hệ quả phụ của việc
đọc một tệp Excel. Ranh giới ấy đúng, và nó chỉ được gỡ bằng một chữ ký thật: chữ ký ở trên.

══════════════════════════════════════════════════════════════════════════════════════════════════
CÁI BẪY VỀ NGÀY — LÝ DO LỚN NHẤT KHIẾN TỆP NÀY KHÔNG PHẢI MỘT VÒNG LẶP BA DÒNG
══════════════════════════════════════════════════════════════════════════════════════════════════

`closed_at` là thứ QUYẾT ĐỊNH CHUYẾN THUỘC THÁNG NÀO trên màn hình Chủ tịch.

Cửa đóng số thật ghi `closed_at = datetime.now()` — đúng với nó, vì chuyến vừa kết thúc thì tháng
đóng số cũng là tháng ấy. Chép nguyên cách đó vào đây thì **toàn bộ ≈ 36 tỷ của T1–T5 nhảy vào
tháng chạy lệnh**: cột tháng 9 phình lên gấp mấy lần, năm tháng đầu năm VẪN rỗng.

Sai kiểu ấy tệ hơn rỗng. Rỗng thì người đọc biết là thiếu; còn một cột tháng 9 phình lên nhìn không
khác gì một tháng bán tốt, và không có gì kêu lên.

Nên ở đây `closed_at` = **cuối ngày KẾT THÚC của chính chuyến**. Tiền rơi đúng tháng nó phát sinh.

Hệ quả phải chịu, và phải nói ra: với lô này `closed_at` mang nghĩa **"kỳ của chuyến"**, không còn
là "lúc người ta bấm đóng số". Ngày bấm thật và người bấm nằm ở NHẬT KÝ và DÒNG SỰ KIỆN của chuyến,
không lẫn vào cột kỳ. Chuỗi tài liệu đầu `ket_qua_that.py` đã được sửa theo.

══════════════════════════════════════════════════════════════════════════════════════════════════
BA CHUYẾN KHÔNG ĐƯỢC ĐÓNG, VÀ VÌ SAO
══════════════════════════════════════════════════════════════════════════════════════════════════

1. **KHÔNG CÓ MỘT DÒNG CHI PHÍ NÀO.** Đóng là ghi `actual_cost = 0`, và chuyến ấy báo lãi bằng
   ĐÚNG TOÀN BỘ doanh thu, biên 100%. Bảng vẫn cân nên không ai nhìn ra. Đây đúng là điều
   `ket_qua_that.py` sinh ra để chặn ("rỗng ≠ 0"); cửa này không được phá nó từ đầu kia.

2. **DOANH THU BẰNG 0.** Một chuyến đã chạy mà không có đồng doanh thu nào gần như chắc chắn là
   dòng khách chưa vào, không phải một chuyến cho không. Đóng nó là ghi một khoản lỗ bằng đúng chi
   phí vào báo cáo Chủ tịch.

3. **CHƯA KẾT THÚC.** Giữ nguyên hàng rào của cửa đóng số thật: chuyến chưa chạy xong thì chưa có
   gì để quyết toán.

Cả ba nhóm KHÔNG biến mất — chúng ra số đếm riêng trong bản trả về, để "còn bao nhiêu chưa vào
được và vì sao" là câu tra được chứ không phải câu phải đoán.

══════════════════════════════════════════════════════════════════════════════════════════════════
KHÔNG TỰ CỘNG LẠI DOANH THU — DÙNG ĐÚNG PHÉP CỦA HỆ
══════════════════════════════════════════════════════════════════════════════════════════════════

`settlement.summary()` đã định nghĩa sẵn cả hai con số:

    revenue = sum((b.amount or 0) - (b.discount or 0) for b in t.bookings if not b.cancelled)
    actual  = sum((l.actual or 0) for l in lines_of(db, t, active_only=True))

Bản nháp đầu của tệp này định tự cộng `bookings.amount` — **thiếu mất phần trừ `discount`**, và
thiếu cả luật bỏ phiếu đã huỷ cùng dòng chi phí đã huỷ. Hai phép cộng cho cùng một câu hỏi là hai
con số sẽ lệch nhau vào ngày không ai để ý. Nên ở đây gọi thẳng `ST.summary`.
"""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.services.tao_chuyen_kho_cu import NGUON

# Trạng thái chuyến được phép đóng bù. Giống cửa đóng số thật.
# SỐ CHUYẾN MỖI LÔ. Vì sao phải chia lô, đo được 19/9/2026 trên hệ thật:
#
# Cả hai cửa dưới đây nuốt trọn 476 chuyến trong MỘT lần gọi. Cửa đóng số còn tệ hơn cửa gỡ: nó
# gọi `xem()` (một lần chiết tính mỗi chuyến), rồi trong vòng lặp gọi lại `_soat_mot` (lần hai)
# và `ST.summary` (lần ba) — 1.428 lần chiết tính cho 476 chuyến. Cổng cắt giữa chừng và trả về
# một trang HTML; phía trình duyệt chỉ thấy "Unexpected token '<'". Giao dịch bị huỷ trọn nên
# KHÔNG hỏng dữ liệu, nhưng cũng không ai bấm xong được nút.
#
# Chia lô sửa cả hai vế: mỗi lần gọi là một giao dịch nhỏ, xong thì commit và trả về `con_lai`.
# Người bấm (hoặc màn hình) gọi tiếp cho tới khi `con_lai` = 0. Dừng giữa chừng — mất mạng, đóng
# máy — thì phần đã làm vẫn sạch và gọi lại là chạy tiếp, không làm lại từ đầu.
#
# 50 là chỗ đứng giữa: đủ nhỏ để một lô chạy dưới vài giây, đủ lớn để 476 chuyến xong trong mươi
# lần gọi. Người gọi đổi được qua tham số; `gioi_han=0` nghĩa là không chia lô (giữ nết cũ).
MOI_LO = 50

# CON TRỎ `bo_qua` — chỗ dễ làm sai nhất của việc chia lô, và là chỗ suýt sai ở bản đầu.
#
# Lô lấy theo điều kiện "chưa đóng số". Chuyến ĐÓNG ĐƯỢC thì sau khi đóng nó rời khỏi điều kiện,
# nên lần gọi sau không gặp lại. Nhưng chuyến KHÔNG đóng được (thiếu dòng chi, doanh thu 0) thì
# vẫn nằm nguyên trong điều kiện — và vì sắp theo `id`, nó luôn đứng ở ĐẦU hàng. Không có con trỏ,
# lần gọi sau lấy đúng những chuyến ấy, đóng được 0 chuyến, `con_lai` không giảm: màn hình quay
# vòng mãi mãi. Cửa gỡ y hệt, với những chuyến Điều hành đã đóng THẬT mà cửa này phải giữ nguyên —
# đo 17/9/2026 đã có 82 chuyến như thế, nhiều hơn một lô, nên vòng lặp sẽ kẹt ngay lô đầu.
#
# Vì vậy mỗi lần gọi trả về `bo_qua_tiep` = số dòng đã xét mà VẪN CÒN Ở LẠI trong điều kiện.
# Người gọi truyền lại con số ấy ở lần sau. `con_lai` cũng đếm theo con trỏ: còn bao nhiêu dòng
# CHƯA XÉT, chứ không phải còn bao nhiêu dòng khớp điều kiện.

CHO_DONG = ("ket_thuc", "da_duyet")

# Trạng thái sau khi đóng — cũng giống cửa thật, để mọi bước sau (Kế toán xác nhận, khoá) đi tiếp
# bình thường chứ không phải một nhánh riêng.
SAU_DONG = "da_dong_so"


def moc_ky(t: Tour) -> datetime:
    """`closed_at` của lô bù = CUỐI NGÀY KẾT THÚC CHUYẾN.

    Không phải `datetime.now()`. Xem "cái bẫy về ngày" ở đầu tệp — đây là dòng quan trọng nhất của
    cả tệp này, và cũng là dòng dễ bị "dọn cho gọn" nhất trong một lần sửa sau.
    """
    return datetime.combine(t.end_date, time(23, 59, 59))


def _cau_ung_vien(gioi_han: int | None = None, bo_qua: int = 0):
    """Câu hỏi CSDL cho "chuyến kho cũ chưa đóng số" — tách riêng để phép thử soi được thứ tự.

    `order_by(Tour.id)` KHÔNG phải để cho đẹp. Cả cơ chế chia lô dựa trên nó: `bo_qua` bỏ qua
    `n` dòng ĐẦU, mà "đầu" chỉ có nghĩa khi thứ tự cố định. Thiếu `order_by` thì thứ tự do cơ sở
    dữ liệu quyết (Postgres đổi thứ tự sau mỗi lần UPDATE), lô sau có thể lặp lại chuyến của lô
    trước hoặc nhảy cóc bỏ sót — cả hai đều lặng lẽ.
    """
    q = select(Tour).where(Tour.confirmed_by == NGUON, Tour.closed_at.is_(None)).order_by(Tour.id)
    if bo_qua:
        q = q.offset(bo_qua)
    if gioi_han:
        q = q.limit(gioi_han)
    return q


def _ung_vien(db: Session, gioi_han: int | None = None, bo_qua: int = 0) -> list[Tour]:
    """Chuyến do kho cũ dựng ra mà CHƯA đóng số.

    Nhận diện bằng `confirmed_by` — cửa tạo chuyến kho cũ ghi sẵn nguồn vào đấy
    (`intake_tao_chuyen.nap_lo`). Không cần thêm cột, không cần bản nâng cấp CSDL.

    `gioi_han` cắt bớt để làm THEO LÔ; `bo_qua` là CON TRỎ — xem chú thích ở `MOI_LO`.
    """
    return list(db.execute(_cau_ung_vien(gioi_han, bo_qua)).scalars())


def _dem_ung_vien(db: Session) -> int:
    """Đếm, KHÔNG tải. `len(_ung_vien(db))` kéo cả 476 đối tượng Tour về chỉ để lấy một con số."""
    from sqlalchemy import func
    return db.scalar(select(func.count(Tour.id)).where(
        Tour.confirmed_by == NGUON, Tour.closed_at.is_(None))) or 0


def _soat_mot(db: Session, t: Tour, hom_nay: date) -> dict:
    """Một chuyến: đóng được hay không, và nếu không thì vì sao. KHÔNG ghi gì."""
    from app.services import settlement as ST

    sm = ST.summary(db, t)
    d = {"tour_id": t.id, "ma": t.code, "ten": t.name,
         "ngay_ket_thuc": t.end_date, "ky": f"{t.end_date:%Y-%m}" if t.end_date else "",
         "doanh_thu": float(sm["revenue"] or 0), "gia_von": float(sm["actual"] or 0),
         "so_dong_chi": sm["lines"], "dong_duoc": False, "vi_sao": "",
         # Giữ luôn kết quả `ST.summary` để cửa ghi khỏi tính lại. Trước đây `chay()` gọi
         # `xem()` (1 lần/chuyến) rồi trong vòng lặp gọi `_soat_mot` (lần 2) và `ST.summary`
         # (lần 3) — BA lần cho cùng một chuyến. Với 476 chuyến là 1.428 lần chiết tính, và
         # cổng cắt giữa chừng: đo 19/9/2026, cửa trả về trang HTML thay vì JSON.
         "_sm": sm}

    if t.status not in CHO_DONG:
        d["vi_sao"] = f"trạng thái {t.status!r} không ở bước quyết toán"
    elif not t.end_date or t.end_date > hom_nay:
        d["vi_sao"] = "chuyến chưa kết thúc"
    elif not sm["lines"]:
        d["vi_sao"] = ("không có dòng chi phí nào — đóng là ghi giá vốn 0 đồng, và chuyến báo lãi "
                       "bằng đúng toàn bộ doanh thu")
    elif float(sm["revenue"] or 0) <= 0:
        d["vi_sao"] = "doanh thu bằng 0 — dòng khách chưa vào, đóng là ghi một khoản lỗ không có thật"
    else:
        d["dong_duoc"] = True
    return d


def _gom(hang: list[dict]) -> dict:
    """Cộng theo tháng — để người duyệt thấy tiền sẽ rơi vào tháng nào TRƯỚC khi bấm."""
    theo_ky: dict[str, dict] = {}
    for h in hang:
        if not h["dong_duoc"]:
            continue
        k = theo_ky.setdefault(h["ky"], {"ky": h["ky"], "so_chuyen": 0, "doanh_thu": 0.0,
                                         "gia_von": 0.0})
        k["so_chuyen"] += 1
        k["doanh_thu"] += h["doanh_thu"]
        k["gia_von"] += h["gia_von"]
    for k in theo_ky.values():
        k["doanh_thu"] = round(k["doanh_thu"], 2)
        k["gia_von"] = round(k["gia_von"], 2)
        k["lai"] = round(k["doanh_thu"] - k["gia_von"], 2)
    return dict(sorted(theo_ky.items()))


def _sach(hang: list[dict]) -> list[dict]:
    """Bỏ `_sm` trước khi trả ra ngoài.

    `_sm` là kết quả chiết tính giữ lại cho `chay()` dùng — việc BÊN TRONG. Để nó lọt ra câu trả
    lời của cửa API thì mỗi chuyến gánh thêm một khối chiết tính, 50 chuyến một lô là một câu trả
    lời phình ra vô ích; và một trường bắt đầu bằng dấu gạch dưới lọt ra ngoài rồi thì sớm muộn sẽ
    có màn hình đọc nó, lúc ấy sửa bên trong hoá ra là phá cửa.
    """
    return [{k: v for k, v in h.items() if k != "_sm"} for h in hang]


def xem(db: Session, gioi_han: int | None = MOI_LO, bo_qua: int = 0,
        _giu_sm: bool = False) -> dict:
    """XEM TRƯỚC — không ghi một dòng nào.

    Nói ra đúng ba thứ người ký cần biết trước khi ký: sẽ đóng bao nhiêu chuyến, tiền rơi vào
    THÁNG NÀO, và những chuyến không đóng được thì vì sao.
    """
    hang = [_soat_mot(db, t, date.today()) for t in _ung_vien(db, gioi_han, bo_qua)]
    # `xem` không ghi gì nên KHÔNG chuyến nào rời khỏi điều kiện: con trỏ tiến đủ cả lô.
    bo_qua_tiep = bo_qua + len(hang)
    con_lai = _dem_ung_vien(db) - bo_qua_tiep
    dong = [h for h in hang if h["dong_duoc"]]
    bo = [h for h in hang if not h["dong_duoc"]]

    vi_sao: dict[str, int] = {}
    for h in bo:
        vi_sao[h["vi_sao"]] = vi_sao.get(h["vi_sao"], 0) + 1

    theo_ky = _gom(hang)
    return {
        "nguon": NGUON,
        "ung_vien": len(hang),
        # Bao nhiêu chuyến CHƯA được xét trong lần gọi này. Màn hình đọc con số này để biết còn
        # phải gọi tiếp hay không — và người bấm biết mình đang xem một PHẦN chứ không phải tất cả.
        "con_lai": con_lai,
        "moi_lo": gioi_han or 0,
        "bo_qua": bo_qua,
        "bo_qua_tiep": bo_qua_tiep,
        "se_dong": len(dong),
        "khong_dong_duoc": len(bo),
        "vi_sao_khong_dong": vi_sao,
        "theo_ky": list(theo_ky.values()),
        "tong_doanh_thu": round(sum(h["doanh_thu"] for h in dong), 2),
        "tong_gia_von": round(sum(h["gia_von"] for h in dong), 2),
        "chi_tiet": hang if _giu_sm else _sach(hang),
        "ghi_chu": (
            f"XEM TRƯỚC – chưa ghi gì. Sẽ đóng số {len(dong)} chuyến của kho quyết toán cũ, "
            f"Chủ tịch ký thay các phòng ban. Mốc kỳ (`closed_at`) lấy theo NGÀY KẾT THÚC CỦA "
            f"CHÍNH CHUYẾN, nên tiền rơi vào tháng nó phát sinh chứ không dồn vào tháng bấm nút. "
            f"{len(bo)} chuyến KHÔNG đóng được – xem `vi_sao_khong_dong`."),
    }


def chay(db: Session, boi: str, xac_nhan: bool = False,
         gioi_han: int | None = MOI_LO, bo_qua: int = 0) -> dict:
    """ĐÓNG SỐ THẬT. `xac_nhan` mặc định False nên gọi nhầm KHÔNG ghi gì.

    Không commit — người gọi (cửa API) commit sau khi đã ghi nhật ký kiểm toán, để nhật ký và dữ
    liệu cùng nằm trong MỘT giao dịch.
    """
    from app.services import settlement as ST
    from app.services.products import event as EV

    kq = xem(db, gioi_han, bo_qua, _giu_sm=True)
    if not xac_nhan:
        return {**kq, "chi_tiet": _sach(kq["chi_tiet"]), "da_dong": 0,
                "message": "XEM TRƯỚC – chưa ghi gì. Gọi lại với xac_nhan = true để đóng thật."}

    luc = datetime.now()
    da = []
    # DÙNG LẠI kết quả của `xem` ở trên, KHÔNG soát lại và KHÔNG chiết tính lại. Bản trước gọi
    # `_soat_mot` và `ST.summary` thêm hai lần nữa cho mỗi chuyến — cùng một con số, tính ba lần.
    bang = {d["tour_id"]: d for d in kq["chi_tiet"]}
    for t in _ung_vien(db, gioi_han, bo_qua):
        d = bang.get(t.id)
        if d is None or not d["dong_duoc"]:
            continue
        sm = d["_sm"]
        t.actual_revenue = float(sm["revenue"] or 0)
        t.actual_cost = float(sm["actual"] or 0)
        t.closed_at = moc_ky(t)          # KỲ CỦA CHUYẾN – xem moc_ky()
        t.status = SAU_DONG
        EV(db, t, "dong_so", boi,
           f"Đóng số BÙ cho kho quyết toán cũ – Chủ tịch ký thay các phòng ban. "
           f"Doanh thu {t.actual_revenue:,.0f} đ, giá vốn {t.actual_cost:,.0f} đ trên "
           f"{sm['lines']} dòng chi. Mốc kỳ lấy theo ngày kết thúc chuyến "
           f"({t.end_date:%d/%m/%Y}); bấm lúc {luc:%d/%m/%Y %H:%M} bởi {boi}.")
        da.append(d)
    db.flush()

    theo_ky = _gom(da)
    # Chuyến vừa đóng đã rời khỏi điều kiện; chuyến KHÔNG đóng được thì ở lại và luôn đứng đầu
    # hàng, nên con trỏ phải tiến qua đúng số ấy — nếu không, lô sau lấy lại chính chúng và màn
    # hình quay vòng mãi. Xem chú thích ở `MOI_LO`.
    bo_qua_tiep = bo_qua + (len(kq["chi_tiet"]) - len(da))
    return {
        **kq,
        "chi_tiet": _sach(kq["chi_tiet"]),
        "da_dong": len(da),
        "bo_qua_tiep": bo_qua_tiep,
        # Còn bao nhiêu chuyến CHƯA XÉT. Màn hình gọi tiếp khi con số này > 0.
        # Sau `db.flush()` ở trên, `_dem_ung_vien` ĐÃ phản ánh trạng thái mới — những chuyến vừa
        # đóng không còn đếm vào nữa. Trừ thêm `len(da)` là trừ hai lần.
        "con_lai": _dem_ung_vien(db) - bo_qua_tiep,
        "theo_ky_da_dong": list(theo_ky.values()),
        "luc": luc,
        "boi": boi,
        "message": (
            f"Đã đóng số {len(da)} chuyến kho cũ, Chủ tịch ký thay. Tiền rơi theo NGÀY KẾT THÚC "
            f"của từng chuyến: " + " · ".join(f"{k['ky']} {k['doanh_thu']:,.0f} đ"
                                              for k in theo_ky.values())
            + f". {kq['khong_dong_duoc']} chuyến không đóng được, xem `vi_sao_khong_dong`."),
    }


def _dem_da_dong(db: Session) -> int:
    """Đếm chuyến kho cũ đang ở trạng thái đã đóng số. Đếm ở CSDL, không tải đối tượng về."""
    from sqlalchemy import func
    return db.scalar(select(func.count(Tour.id)).where(
        Tour.confirmed_by == NGUON, Tour.status == SAU_DONG,
        Tour.closed_at.is_not(None))) or 0


def _do_cua_nay(t: Tour) -> bool:
    """Chuyến này có phải do CỬA BÙ đóng không — hay do Điều hành đóng thật?

    Hai cửa cùng ghi vào một cột `closed_at`, nên nút gỡ phải phân biệt được, nếu không nó sẽ gỡ
    luôn công việc thật của Điều hành. Đo 17/9/2026: trong kho cũ đã có 82 chuyến T6 mang
    `closed_at` — tức là chuyện này KHÔNG phải giả định, nó đang có thật trong cơ sở dữ liệu.

    Dấu nhận: cửa bù ghi đúng `moc_ky(t)` = 23:59:59 của ngày kết thúc, phần micro-giây bằng 0. Cửa
    thật ghi `datetime.now()`, luôn có micro-giây và gần như không bao giờ rơi trúng giây ấy.

    Không phải một cột riêng, nên yếu hơn một cột riêng. Nhưng nó sai về phía AN TOÀN: nhầm thì cửa
    gỡ BỎ SÓT một chuyến của chính nó (người bấm thấy số còn lại, gỡ tay được), chứ không xoá nhầm
    một chuyến Điều hành đã đóng.
    """
    return bool(t.end_date) and t.closed_at == moc_ky(t)


def _cau_da_dong(gioi_han: int | None = None, bo_qua: int = 0):
    """Câu hỏi CSDL cho "chuyến kho cũ đang ở trạng thái đã đóng số". Xem `_cau_ung_vien` về
    `order_by` — cùng một lý do, và ở cửa gỡ nó còn quan trọng hơn vì số chuyến ở lại nhiều hơn."""
    q = (select(Tour).where(Tour.confirmed_by == NGUON, Tour.status == SAU_DONG,
                            Tour.closed_at.is_not(None)).order_by(Tour.id))
    if bo_qua:
        q = q.offset(bo_qua)
    if gioi_han:
        q = q.limit(gioi_han)
    return q


def go(db: Session, boi: str, xac_nhan: bool = False,
       gioi_han: int | None = MOI_LO, bo_qua: int = 0) -> dict:
    """GỠ lại phần cửa này đã đóng — bắt buộc phải có, vì không có nút gỡ là nút không ai dám bấm.

    CHỈ đụng chuyến còn ở `da_dong_so` VÀ mang dấu của cửa này (xem `_do_cua_nay`). Chuyến đã đi
    tiếp (Kế toán xác nhận, đã khoá) thì để yên: gỡ ngược một chuyến Kế toán đã xác nhận là kéo con
    số của họ về mà họ không biết.
    """
    # Lấy theo LÔ, và lọc `_do_cua_nay` SAU khi lấy — nên một lô có thể ra ít hơn `gioi_han`
    # chuyến gỡ được. Đó là chủ ý: lọc trong câu truy vấn thì phải so `closed_at` với một biểu
    # thức tính từ `end_date` của từng dòng, và mỗi cơ sở dữ liệu viết một kiểu.
    tat_ca = list(db.execute(_cau_da_dong(gioi_han, bo_qua)).scalars())
    ds = [t for t in tat_ca if _do_cua_nay(t)]
    giu = len(tat_ca) - len(ds)
    # Chuyến GIỮ LẠI vẫn ở trạng thái đã đóng nên lô sau gặp lại đúng chúng — con trỏ phải tiến
    # qua. Đo 17/9/2026: 82 chuyến kho cũ đã đóng THẬT, nhiều hơn một lô, nên không có con trỏ là
    # vòng lặp kẹt ngay ở lô đầu và không bao giờ tới chuyến cần gỡ.
    bo_qua_tiep = bo_qua + giu
    if not xac_nhan:
        return {"se_go": len(ds), "da_go": 0, "giu_lai_do_dong_that": giu,
                # Xem trước không ghi gì, nên cả lô còn ở lại: con trỏ tiến đủ `len(tat_ca)`.
                "bo_qua": bo_qua, "bo_qua_tiep": bo_qua + len(tat_ca),
                "con_lai": _dem_da_dong(db) - bo_qua - len(tat_ca),
                "moi_lo": gioi_han or 0,
                "ma": [t.code for t in ds[:50]],
                "message": (f"XEM TRƯỚC – chưa gỡ gì. Sẽ gỡ {len(ds)} chuyến về lại 'kết thúc' và "
                            f"xoá doanh thu / giá vốn / mốc kỳ do cửa này ghi. Giữ nguyên {giu} "
                            f"chuyến kho cũ đã được đóng số THẬT – cửa này không đụng vào.")}
    for t in ds:
        t.actual_revenue = None
        t.actual_cost = None
        t.closed_at = None
        t.status = "ket_thuc"
    db.flush()
    return {"se_go": len(ds), "da_go": len(ds), "giu_lai_do_dong_that": giu,
            "moi_lo": gioi_han or 0, "bo_qua": bo_qua, "bo_qua_tiep": bo_qua_tiep,
            # Như trên: sau flush, chuyến vừa gỡ không còn ở trạng thái đã đóng nên không đếm vào.
            # Trừ con trỏ ra để còn lại đúng số CHƯA XÉT.
            "con_lai": _dem_da_dong(db) - bo_qua_tiep,
            "ma": [t.code for t in ds[:50]],
            "message": (f"Đã gỡ {len(ds)} chuyến về lại 'kết thúc'. Giữ nguyên {giu} chuyến đã đóng "
                        f"số thật. Chạy lại cửa đóng bù được.")}
