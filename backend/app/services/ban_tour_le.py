"""Bàn bán tour lẻ — Phòng Kinh doanh Lẻ. Chủ tịch quyết 25/9/2026.

    "Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc bán."
    "Sales lẻ chỉ nhìn thấy dự toán 3 con số như trong file quyết toán tour của Điều hành."
    "Trên quyết toán tour đã có thông tin tour, dự toán 3 con số — nối cái này về cho PKDL."

Màn hình này là cái "nối về" ấy: mỗi chuyến lẻ đang bán một dòng, kèm đúng phần đầu của bảng quyết
toán — thông tin chuyến và ba con số dự toán — chứ không phải cả bảng.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO LÀ MỘT DANH SÁCH, KHÔNG PHẢI MỘT NÚT TRÊN TỪNG CHUYẾN
═══════════════════════════════════════════════════════════════════════════════════════════════
Người bán không mở từng chuyến để tra. Họ đang nói chuyện với khách, khách xin giảm giá, và câu
hỏi trong đầu họ là "chuyến này còn lời bao nhiêu, giảm được không". Bắt họ mở mười chuyến để trả
lời một câu ấy thì họ sẽ không tra — họ sẽ đoán, và đoán về phía dễ bán.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA CON SỐ LÀ DỰ TOÁN, KHÔNG PHẢI GIÁ VỐN THẬT — VÀ MÀN HÌNH PHẢI NÓI RA
═══════════════════════════════════════════════════════════════════════════════════════════════
Mọi con số ở đây tính TỪ ba con số dự toán (`rules.calc`), không đọc một dòng chi phí nhà cung cấp
nào. Đó đúng là ranh giới Chủ tịch vạch: "không liên quan giá vốn". Hệ quả phải nói ra trên màn
hình, không giấu trong mã: chuyến đã chạy xong và đã có quyết toán thì lợi nhuận THẬT có thể khác
con số ở đây, và người bán không được lấy dòng này làm bằng chứng lãi lỗ.

`chua_du_co_so` KHÔNG phải "biên bằng 0". Chuyến chưa có dự toán riêng thì `complete=False`, và
dòng ấy hiện chữ chứ không hiện số — thiếu giá vốn mà in ra "biên 100%" là đúng cái bệnh Ý kiến
thẩm định 06/9/2026 đã bắt.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.services import rules as R
from app.services import segments as SEG

# Trạng thái ĐANG BÁN. `da_duyet` là chuyến đã qua cổng biên và đang mở bán; các trạng thái trước
# đó là việc của Điều hành, còn sau đó là việc của quyết toán — cả hai đều không phải việc của
# người bán, và bày ra chỉ làm dài danh sách.
DANG_BAN = ("da_duyet",)


# R5-4 · Chủ tịch 13/11/2026: «đạt mục tiêu tối đa 45 khách/tour thì lời được bao nhiêu %, hiện rõ trên
# từng tour cho sales thấy để làm động lực bán». Chuyến mở ÍT chỗ hơn thì tính ở số chỗ mở — không bán
# được khách thứ 46 trên một chuyến 30 chỗ.
KHACH_TOI_DA_TOUR = 45


def _khach_cho_bien(p: float, f: float, v: float, bien: float) -> int | None:
    """Số khách nhỏ nhất để lãi ÷ doanh thu ≥ `bien` (bien = 0 → hòa vốn).

    lãi(n) = (p − v)·n − f ;  lãi(n) ≥ bien·p·n  ⇔  n ≥ f ÷ ((1 − bien)·p − v).
    Mẫu ≤ 0 nghĩa là bán bao nhiêu khách cũng không tới mức ấy → None, không bịa một con số."""
    mau = (1 - bien) * p - v
    if mau <= 0:
        return None
    from math import ceil
    return max(0, ceil(f / mau - 1e-9))


def _dong(db: Session, t: Tour, nguong: float) -> dict:
    c = R.calc_db(db, t, nguong)
    ban = R.booked_pax(t)
    tran = int(t.seats_open or 0) or int(t.planned_pax or 0)
    hv = c["breakeven_pax"]
    # Lợi nhuận TẠI SỐ KHÁCH ĐANG BÁN, tính bằng chính ba con số — đây là con số người bán cần khi
    # khách xin giảm giá, và nó khác "lợi nhuận kế hoạch" (tính ở số khách dự toán) bất cứ khi nào
    # chuyến chưa bán đủ. In một số mà gọi tên số kia là cách nhanh nhất để mất lòng tin vào bảng.
    p, f, v = (t.price_per_pax or 0), (c["fixed_cost"] or 0), (c["var_cost_per_pax"] or 0)
    loi_dang_ban = (p - v) * ban - f if c["complete"] else None
    return {
        "id": t.id, "code": t.code, "name": t.name, "tour_type": t.tour_type,
        "start_date": t.start_date, "end_date": t.end_date, "days": t.days,
        "departure_point": t.departure_point, "transport": t.transport,
        "operator_name": t.operator.full_name if t.operator else "",
        "days_left": (t.start_date - date.today()).days,
        # ── chỗ ─────────────────────────────────────────────────────────────────────────
        "cho_mo_ban": tran, "cho_da_ban": ban, "cho_con": max(0, tran - ban),
        # ── ba con số dự toán ───────────────────────────────────────────────────────────
        "gia_ban": t.price_per_pax, "chi_phi_co_dinh": c["fixed_cost"],
        "chi_phi_theo_khach": c["var_cost_per_pax"], "so_khach_du_toan": t.planned_pax,
        # ── số máy tính ra từ ba con số ấy ──────────────────────────────────────────────
        "hoa_von_khach": hv,
        "con_thieu_de_hoa_von": max(0, hv - ban) if hv else None,
        "loi_nhuan_ke_hoach": c["profit"] if c["complete"] else None,
        "bien_ke_hoach": c["margin"] if c["complete"] else None,
        "loi_nhuan_tai_so_dang_ban": loi_dang_ban,
        "nguong_bien": c["threshold"], "trang_thai_cong": c["gate_state"],
        "nguon_du_toan": c["budget_source_label"], "chi_tham_chieu": c["reference_only"],
        "duoi_bien": bool(t.below_margin),
        # ── R5-4: ba con số động lực cho người bán — chỉ khi đủ ba con số dự toán ──────────
        **_dong_luc(c["complete"], p, f, v, ban, tran, nguong),
    }


def _dong_luc(du: bool, p: float, f: float, v: float, ban: int, tran: int, nguong: float) -> dict:
    """Khách cần để hòa vốn · để đạt ngưỡng biên (tham số `nguong_bien`, hiện 10%) · lãi % khi bán đủ
    khách tối đa. Thiếu dự toán thì cả ba là None — màn hình in «chưa có dự toán», không in 0."""
    if not du or not p:
        return {"khach_hoa_von": None, "khach_dat_bien": None, "bien_muc_tieu": nguong,
                "khach_toi_da": None, "bien_khi_day": None, "lai_khi_day": None}
    n_max = min(KHACH_TOI_DA_TOUR, tran) if tran else KHACH_TOI_DA_TOUR
    lai = (p - v) * n_max - f
    return {"khach_hoa_von": _khach_cho_bien(p, f, v, 0.0),
            "khach_dat_bien": _khach_cho_bien(p, f, v, nguong or 0.0), "bien_muc_tieu": nguong,
            "khach_toi_da": n_max, "lai_khi_day": lai, "bien_khi_day": (lai / (p * n_max)) if n_max else None}


# R5-16 · Chủ tịch 14/11/2026: bỏ thẻ «Lịch khởi hành» khỏi bàn Lẻ, GỘP vào bàn này — thêm hai phạm vi CHỈ XEM.
#   sap_mo_ban = chuyến tương lai Điều hành đã tạo nhưng chưa duyệt (nháp / chờ xác nhận / chờ duyệt) — chưa bán được;
#   da_di      = chuyến đã khởi hành (mọi trạng thái trừ huỷ), mới nhất trước.
# Không có cửa tạo tour: đó là việc của Điều hành / Đoàn ở màn /tours.
CHUA_DUYET = ("nhap", "cho_xac_nhan", "cho_duyet")
PHAM_VI = ("dang_ban", "sap_mo_ban", "da_di")
TOI_DA_XEM = 300


def dong_sap_di(db: Session, so_ngay: int = 7) -> list[dict]:
    """R5-23 · Dòng bàn bán của chuyến ĐANG BÁN khởi hành trong `so_ngay` ngày tới — cho khối «Chuyến cần
    thúc bán» trên bốn bàn KD (Chủ tịch 14/11/2026 «load rất chậm»). Cùng luật chọn và cùng `_dong` với
    `ban_lam_viec(pham_vi="dang_ban")`, chỉ không dựng dòng cho mọi chuyến đang bán rồi bỏ đi gần hết:
    đo trên crm `ban_lam_viec` mất ≈ 3,8 giây, khối này chỉ cần vài chuyến."""
    from datetime import timedelta
    hom_nay = date.today()
    ts = [t for t in db.execute(select(Tour).where(
              Tour.tour_type.in_(SEG.LE_TYPES), Tour.status.in_(DANG_BAN),
              Tour.start_date >= hom_nay, Tour.start_date <= hom_nay + timedelta(days=so_ngay))).scalars()
          if SEG.mang_of(t) == "le"]
    rows, nho = [], {}
    for t in sorted(ts, key=lambda t: t.start_date):
        nguong = nho.get(t.start_date)
        if nguong is None:
            nguong = nho[t.start_date] = R.get_param(db, "nguong_bien", t.start_date)
        rows.append(_dong(db, t, nguong))
    return rows


def ban_lam_viec(db: Session, pham_vi: str = "dang_ban") -> dict:
    """Danh sách chuyến LẺ đang bán, sắp theo ngày khởi hành gần nhất.

    KHÔNG cắt theo người phụ trách. Tour lẻ do Điều hành mở lịch và cả phòng cùng bán một kho chỗ —
    cắt theo sale thì mỗi người thấy một mẩu của cùng một chuyến, và chuyến nào không ai nhận sẽ
    không nằm trên bảng của ai. Cắt theo người là luật của BOOKING, không phải của chỗ ngồi.
    """
    if pham_vi not in PHAM_VI:
        pham_vi = "dang_ban"
    hom_nay = date.today()
    tat = [t for t in db.execute(select(Tour).where(Tour.tour_type.in_(SEG.LE_TYPES), Tour.status != "huy")).scalars()
           if SEG.mang_of(t) == "le"]
    nhom = {"dang_ban": [t for t in tat if t.status in DANG_BAN and t.start_date >= hom_nay],
            "sap_mo_ban": [t for t in tat if t.status in CHUA_DUYET and t.start_date >= hom_nay],
            "da_di": [t for t in tat if t.start_date < hom_nay]}
    dem = {k: len(v) for k, v in nhom.items()}
    # Lọc HAI BƯỚC, cố ý. Câu truy vấn thu hẹp theo loại chuyến; `segments.mang_of` mới là thứ
    # quyết định chuyến ấy thuộc mảng nào — nó là định nghĩa DUY NHẤT của "đoàn hay lẻ" trong kho
    # (hợp của loại chuyến và quy ước mã MICE). Một tour `le_noi_dia` mang mã MICE là tour ĐOÀN, và
    # nó không được nằm trên bàn của phòng Lẻ chỉ vì câu SQL không biết chuyện ấy.
    ts = sorted(nhom[pham_vi], key=lambda t: t.start_date, reverse=(pham_vi == "da_di"))[:TOI_DA_XEM if pham_vi != "dang_ban" else None]
    rows, nho = [], {}
    for t in ts:
        nguong = nho.get(t.start_date)
        if nguong is None:
            nguong = nho[t.start_date] = R.get_param(db, "nguong_bien", t.start_date)
        rows.append(_dong(db, t, nguong))

    sap_di = [r for r in rows if r["days_left"] <= 7]
    return {
        "pham_vi": pham_vi, "dem_pham_vi": dem, "cat_bot": max(0, dem[pham_vi] - len(rows)),
        "rows": rows,
        "tong": {
            "chuyen": len(rows),
            "cho_con": sum(r["cho_con"] for r in rows),
            "sap_khoi_hanh": len(sap_di),
            "chua_hoa_von": sum(1 for r in rows
                                if r["hoa_von_khach"] and r["cho_da_ban"] < r["hoa_von_khach"]),
            "chua_du_co_so": sum(1 for r in rows if r["trang_thai_cong"] == "chua_du_co_so"),
        },
        # Lời cảnh báo đi CÙNG dữ liệu, không nằm trong mã màn hình: màn hình có thể được viết lại,
        # còn câu này là một phần của con số.
        "luu_y": "Mọi con số ở đây tính từ BA CON SỐ DỰ TOÁN của chuyến, không đọc dòng chi phí nhà "
                 "cung cấp. Lợi nhuận thật của chuyến chỉ có sau khi Điều hành quyết toán và Kế "
                 "toán xác nhận — dòng này không phải bằng chứng lãi lỗ.",
    }
