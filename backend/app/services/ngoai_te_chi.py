# -*- coding: utf-8 -*-
"""NGOẠI TỆ TRÊN ĐỀ NGHỊ CHI — chỗ tiền THẬT rời ngân hàng. Chủ tịch chốt 27/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA QUY ƯỚC, VIẾT MỘT CHỖ
═══════════════════════════════════════════════════════════════════════════════════════════════

1. MÁY NHÂN, NGƯỜI KHÔNG GÕ SỐ VND.
   Người khai `tien_te`, `so_tien_ngoai_te`, `ty_gia`, `ngay_ty_gia`. `amount` = máy nhân. Cùng
   một luật với `quyet_toan_lop3.don_gia_vnd` và cùng lý do đã ghi ở `models/ty_gia.py`: gõ tay cả
   ba là mở đường cho ba con số không khớp nhau, và con số không khớp thì sẽ có người đi sửa
   con số SAI.

2. KHAI NGOẠI TỆ THÌ PHẢI KHAI ĐỦ BỐN Ô.
   Thiếu tỷ giá thì không nhân được; thiếu ngày tỷ giá thì không ai kiểm được tỷ giá ấy đúng hay
   sai; thiếu số gốc thì không đối chiếu được sao kê ngoại tệ. Chặn ngay ở cửa nhập, vì một khoản
   chi khai nửa vời sẽ nằm trong sổ mãi mãi.

3. SỔ TỶ GIÁ LÀ BẢN THAM CHIẾU, KHÔNG PHẢI QUAN TOÀ.
   Sổ lệch với số người khai thì NÓI RA, không sửa và không chặn. Tỷ giá của một khoản là tỷ giá
   NGÀY CHUYỂN TIỀN THẬT của khoản ấy — một sự thật đã xảy ra. Nguyên văn quy ước ở
   `models/ty_gia.py`: *"Máy không chọn hộ."*

═══════════════════════════════════════════════════════════════════════════════════════════════
CHÊNH LỆCH TỶ GIÁ: CHỦ TỊCH CHỐT 27/9/2026 — "ĐÃ TRẢ" TÍNH THEO TỶ GIÁ QUYẾT TOÁN
═══════════════════════════════════════════════════════════════════════════════════════════════

Trả NCC 29.770,62 GBP. Quyết toán tính tỷ giá 36.000 → nghĩa vụ 1.071.742.320đ. Ngày chuyển tiền
tỷ giá 36.200 → ngân hàng trừ 1.077.696.444đ.

    cột "đã thanh toán" của dòng  =  1.071.742.320   (tỷ giá CỦA DÒNG)
    chênh lệch tỷ giá             =      5.954.124   (đứng riêng, không lẫn vào công nợ)

Vì sao thế mới đúng: nhà cung cấp HẾT NỢ khi nhận đủ 29.770,62 GBP. Mua ngoại tệ giá nào là việc
của mình với ngân hàng, không phải việc của nhà cung cấp. Ghi 1.077.696.444 vào cột đã trả thì
"còn phải trả NCC" hiện −5.954.124đ — một khoản trả thừa không có thật, đúng cái bệnh hôm nay.

ĐỢT NÀY CHỈ ĐO, CHƯA HẠCH TOÁN (Chủ tịch chọn 27/9/2026). Con số chênh được tính, được cộng, được
in ra theo từng dòng và từng chuyến — nhưng KHÔNG sinh bút toán 635/515. Xem số thật trước rồi mới
quyết định định khoản; một bút toán sai thì phải đảo, mà chưa ai đo số thật.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ty_gia import DONG_TIEN_HAY_GAP, TyGia

# Sai số cho phép khi so hai con số tiền VND. Một đồng — cùng ngưỡng với `soat_ngoai_te.DUNG_SAI`,
# và cùng lý do: hai bên đều `round(..., 2)` nên chênh dưới một đồng là chênh làm tròn.
DUNG_SAI = 1.0

# Sai số cho phép khi so hai số NGOẠI TỆ. Ngoại tệ có phần lẻ thật (692,34 GBP), nên ngưỡng phải
# nhỏ hơn hẳn một đồng VND: một xu ngoại tệ là một khoản tiền có thật.
DUNG_SAI_NT = 0.01


def hoa(tien_te: str | None) -> str:
    """Mã đồng tiền viết HOA, bỏ trắng. Rỗng và "VND" là một: khoản đồng Việt Nam."""
    tt = (tien_te or "").strip().upper()
    return "" if tt == "VND" else tt


def la_ngoai_te(x) -> bool:
    """Bản ghi này có khai ngoại tệ hay không. Dùng cho cả `PaymentRequest` và `TourCostLine`."""
    return bool(hoa(getattr(x, "tien_te", "")))


def ten_dong_tien(tt: str) -> str:
    return DONG_TIEN_HAY_GAP.get(hoa(tt), hoa(tt))


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA NHẬP: kiểm đủ bốn ô, rồi MÁY NHÂN
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def chuan_hoa(data: dict) -> dict:
    """Đọc bốn ô ngoại tệ của một đề nghị chi và trả về số VND máy tự nhân.

    Trả về `{"tien_te", "so_tien_ngoai_te", "ty_gia", "ngay_ty_gia", "amount", "loi_nhan"}`.
    Khoản đồng Việt Nam: bốn ô rỗng, `amount` giữ đúng số người gõ.

    Ném `ValueError` — cửa `POST /payment-requests` đã dịch `ValueError` thành 422 cho màn hình.
    """
    tt = hoa(data.get("tien_te"))
    if not tt:
        return {"tien_te": "", "so_tien_ngoai_te": None, "ty_gia": None, "ngay_ty_gia": None,
                "amount": float(data.get("amount") or 0), "loi_nhan": ""}

    if len(tt) != 3 or not tt.isalpha():
        raise ValueError(f"Mã đồng tiền '{tt}' không đúng dạng – phải là ba chữ cái, ví dụ USD, GBP")

    goc = data.get("so_tien_ngoai_te")
    tg = data.get("ty_gia")
    ngay = data.get("ngay_ty_gia")
    thieu = []
    if not goc or float(goc) <= 0: thieu.append("số tiền ngoại tệ")
    if not tg or float(tg) <= 0: thieu.append("tỷ giá")
    if not ngay: thieu.append("ngày tỷ giá")
    if thieu:
        raise ValueError(
            f"Khoản chi bằng {ten_dong_tien(tt)} phải khai đủ bốn ô – còn thiếu: {', '.join(thieu)}. "
            "Thiếu một ô thì không đối chiếu được sao kê ngoại tệ và không dựng được chênh lệch tỷ giá.")

    goc, tg = float(goc), float(tg)
    vnd = round(goc * tg, 2)
    if vnd <= 0:
        raise ValueError("Số tiền quy đổi phải > 0")

    # Người gõ số VND KHÁC số máy nhân → nói ra, đừng im lặng lấy số của máy. Im lặng ghi đè là chỗ
    # người dùng tưởng hệ đã nhận con số của mình.
    da_go = float(data.get("amount") or 0)
    loi = ""
    if da_go > 0 and abs(da_go - vnd) > DUNG_SAI:
        raise ValueError(
            f"Số VND đã gõ ({da_go:,.0f}đ) khác số máy nhân ({goc:,.2f} × {tg:,.2f} = {vnd:,.0f}đ). "
            "Khoản ngoại tệ thì máy nhân, người không gõ số VND – bỏ trống ô VND hoặc sửa lại "
            "số gốc/tỷ giá.")

    return {"tien_te": tt, "so_tien_ngoai_te": goc, "ty_gia": tg, "ngay_ty_gia": ngay,
            "amount": vnd, "loi_nhan": f"{goc:,.2f} {tt} × {tg:,.2f} = {vnd:,.0f}đ"}


def doi_chieu_so_ty_gia(db: Session, tt: str, ngay: date | None, ty_gia: float | None) -> dict:
    """So tỷ giá người khai với SỔ TỶ GIÁ cùng đồng tiền cùng ngày. CHỈ ĐỌC, KHÔNG CHẶN.

    Trả `{"co_so", "khop", "cac_nguon", "loi_nhan"}`. `khop = None` nghĩa là sổ chưa có ngày ấy —
    khác hẳn `False` (sổ có, và lệch).
    """
    tt = hoa(tt)
    if not tt or not ngay or not ty_gia:
        return {"co_so": False, "khop": None, "cac_nguon": [], "loi_nhan": ""}

    # Chỉ lấy dòng THỰC SỰ có tỷ giá. Một dòng sổ trống tỷ giá là "chưa ai điền", không phải
    # "tỷ giá bằng 0" — coi nó là 0 rồi đem so là biến chỗ trống thành một con số.
    rows = [r for r in db.scalars(select(TyGia).where(TyGia.tien_te == tt, TyGia.ngay == ngay)
                                  .order_by(TyGia.nguon)).all() if r.ty_gia]
    if not rows:
        return {"co_so": False, "khop": None, "cac_nguon": [],
                "loi_nhan": f"Sổ tỷ giá chưa có {tt} ngày {ngay:%d/%m/%Y} – "
                            "nên nhập vào sổ kèm chứng từ để lần sau đối chiếu được."}

    nguon = [{"nguon": r.nguon, "loai_gia": r.loai_gia, "ty_gia": float(r.ty_gia or 0)} for r in rows]
    khop = any(abs(n["ty_gia"] - float(ty_gia)) <= 0.000001 for n in nguon)
    if khop:
        return {"co_so": True, "khop": True, "cac_nguon": nguon, "loi_nhan": ""}
    ds = "; ".join(f"{n['nguon'] or 'không ghi nguồn'} {n['ty_gia']:,.2f}" for n in nguon)
    return {"co_so": True, "khop": False, "cac_nguon": nguon,
            "loi_nhan": f"Tỷ giá khai ({float(ty_gia):,.2f}) khác mọi dòng trong sổ tỷ giá {tt} "
                        f"ngày {ngay:%d/%m/%Y} ({ds}). Không chặn – tỷ giá của khoản này là tỷ giá "
                        "ngày chuyển tiền thật, nhưng người duyệt nên biết."}


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# KHỚP LỆNH CHI VỚI DÒNG QUYẾT TOÁN: chênh tỷ giá ĐỨNG RIÊNG
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def cung_dong_tien(a, b) -> bool:
    """Dòng quyết toán và lệnh chi có cùng một đồng tiền ngoại tệ khai đủ tỷ giá hay không.

    Chỉ khi ĐÚNG thế mới khớp được theo ngoại tệ. Khác đồng tiền (mua USD trả cho một dòng ghi
    GBP) thì không có phép quy đổi nào ở đây là đúng — rơi về khớp theo VND và phải hiện ra.
    """
    ta, tb = hoa(getattr(a, "tien_te", "")), hoa(getattr(b, "tien_te", ""))
    return bool(ta) and ta == tb and bool(getattr(a, "ty_gia", None)) and bool(getattr(b, "ty_gia", None))


def chenh_mot_lan_tra(so_ngoai_te: float, ty_gia_dong: float, ty_gia_chi: float) -> float:
    """Chênh lệch tỷ giá của một lần trả. DƯƠNG = LỖ (chi nhiều VND hơn nghĩa vụ).

    Không làm tròn về đồng ở đây: người gọi cộng nhiều lần trả rồi mới làm tròn một lần, vì làm
    tròn từng lần rồi cộng là cách tự tạo ra một khoản lệch không ai giải thích được.
    """
    return float(so_ngoai_te) * (float(ty_gia_chi) - float(ty_gia_dong))


def nhan_xet_chenh(tong: float) -> str:
    if abs(tong) <= DUNG_SAI:
        return "Không có chênh lệch tỷ giá."
    if tong > 0:
        return (f"LỖ tỷ giá {tong:,.0f}đ – tiền rời ngân hàng nhiều hơn nghĩa vụ tính theo tỷ giá "
                "quyết toán. Số này CHƯA hạch toán (Chủ tịch chốt 27/9/2026: đo trước).")
    return (f"LÃI tỷ giá {-tong:,.0f}đ – tiền rời ngân hàng ít hơn nghĩa vụ tính theo tỷ giá quyết "
            "toán. Số này CHƯA hạch toán (Chủ tịch chốt 27/9/2026: đo trước).")


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# SỔ SOÁT ĐỀ NGHỊ CHI NGOẠI TỆ — CHỈ ĐỌC, KHÔNG SỬA MỘT DÒNG NÀO
# ═══════════════════════════════════════════════════════════════════════════════════════════════

def bang(db: Session, gioi_han: int = 300) -> dict:
    """Mọi đề nghị chi khai ngoại tệ: phép nhân có khớp không, tỷ giá có khớp sổ không.

    Vì sao cần sổ này bên cạnh `soat_ngoai_te` (sổ của dòng giá vốn): đây là chỗ tiền THẬT rời ngân
    hàng. Một dòng giá vốn ghi sai làm lệch báo cáo; một lệnh chi ghi sai làm chuyển sai số tiền.

    CHỈ ĐỌC. Không `commit`, không gán thuộc tính nào.
    """
    from app.models.core import Tour
    from app.models.ops import PaymentRequest

    ma_tour = {t.id: t.code for t in db.execute(select(Tour)).scalars()}
    q = select(PaymentRequest).where(PaymentRequest.tien_te.is_not(None),
                                     PaymentRequest.tien_te != "",
                                     PaymentRequest.tien_te != "VND")
    dem = {"dung": 0, "thieu_o": 0, "phep_nhan_lech": 0}
    dem_so = {"khop": 0, "lech": 0, "chua_co_trong_so": 0}
    rows: list[dict] = []
    tong = 0

    for r in db.execute(q.order_by(PaymentRequest.id.desc())).scalars():
        tong += 1
        goc = float(r.so_tien_ngoai_te) if r.so_tien_ngoai_te else None
        tg = float(r.ty_gia) if r.ty_gia else None
        vnd = float(r.amount or 0)

        if not goc or not tg:
            nhom = "thieu_o"
        elif abs(round(goc * tg, 2) - vnd) > DUNG_SAI:
            nhom = "phep_nhan_lech"
        else:
            nhom = "dung"
        dem[nhom] += 1

        so = doi_chieu_so_ty_gia(db, r.tien_te, r.ngay_ty_gia, tg)
        dem_so["chua_co_trong_so" if so["khop"] is None else ("khop" if so["khop"] else "lech")] += 1

        # In ra mọi dòng cần người nhìn. Dòng `dung` mà tỷ giá KHỚP SỔ thì không cần ai nhìn.
        if (nhom != "dung" or so["khop"] is False) and len(rows) < gioi_han:
            rows.append({
                "id": r.id, "ma": r.code, "tour": ma_tour.get(r.tour_id, ""),
                "ncc": (r.supplier_name or "")[:60], "trang_thai": r.status,
                "tien_te": r.tien_te, "so_tien_ngoai_te": goc, "ty_gia": tg,
                "ngay_ty_gia": r.ngay_ty_gia, "amount": vnd,
                "phep_nhan_dung": round(goc * tg, 2) if (goc and tg) else None,
                "nhom": nhom, "nhom_ten": NHOM_CHI[nhom],
                "so_ty_gia": so, "boi": r.created_by,
            })

    return {
        "tong_de_nghi_chi_ngoai_te": tong,
        "dem": dem, "nhom_ten": NHOM_CHI,
        "doi_chieu_so_ty_gia": dem_so,
        "rows": rows, "cham_tran": len(rows) >= gioi_han,
        "luu_y": ("Chưa có đề nghị chi nào khai ngoại tệ – chưa ai nhập, KHÔNG phải đã sạch. "
                  "Bốn ô ngoại tệ mở ngày 27/9/2026; khoản chi ngoại tệ lập trước ngày đó nằm ở "
                  "`amount` đồng Việt Nam mà không có số gốc, không truy lại được."
                  if tong == 0 else
                  "`phep_nhan_lech` là dòng có số VND không bằng số gốc × tỷ giá – chỉ xảy ra với "
                  "dòng ghi thẳng vào bảng, không đi qua cửa nhập. `so_ty_gia.khop = false` là "
                  "tỷ giá khai khác mọi nguồn trong sổ cùng ngày: KHÔNG phải lỗi, nhưng cần hỏi."),
    }


NHOM_CHI = {
    "dung": "Số VND đúng bằng số gốc × tỷ giá",
    "thieu_o": "Khai ngoại tệ mà thiếu số gốc hoặc tỷ giá",
    "phep_nhan_lech": "Số VND KHÔNG bằng số gốc × tỷ giá",
}
