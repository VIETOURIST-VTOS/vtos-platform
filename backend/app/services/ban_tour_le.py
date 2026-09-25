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
    }


def ban_lam_viec(db: Session) -> dict:
    """Danh sách chuyến LẺ đang bán, sắp theo ngày khởi hành gần nhất.

    KHÔNG cắt theo người phụ trách. Tour lẻ do Điều hành mở lịch và cả phòng cùng bán một kho chỗ —
    cắt theo sale thì mỗi người thấy một mẩu của cùng một chuyến, và chuyến nào không ai nhận sẽ
    không nằm trên bảng của ai. Cắt theo người là luật của BOOKING, không phải của chỗ ngồi.
    """
    hom_nay = date.today()
    # Lọc HAI BƯỚC, cố ý. Câu truy vấn thu hẹp theo loại chuyến; `segments.mang_of` mới là thứ
    # quyết định chuyến ấy thuộc mảng nào — nó là định nghĩa DUY NHẤT của "đoàn hay lẻ" trong kho
    # (hợp của loại chuyến và quy ước mã MICE). Một tour `le_noi_dia` mang mã MICE là tour ĐOÀN, và
    # nó không được nằm trên bàn của phòng Lẻ chỉ vì câu SQL không biết chuyện ấy.
    ts = [t for t in db.execute(
        select(Tour).where(Tour.tour_type.in_(SEG.LE_TYPES), Tour.status.in_(DANG_BAN),
                           Tour.start_date >= hom_nay).order_by(Tour.start_date)).scalars()
          if SEG.mang_of(t) == "le"]
    rows, nho = [], {}
    for t in ts:
        nguong = nho.get(t.start_date)
        if nguong is None:
            nguong = nho[t.start_date] = R.get_param(db, "nguong_bien", t.start_date)
        rows.append(_dong(db, t, nguong))

    sap_di = [r for r in rows if r["days_left"] <= 7]
    return {
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
