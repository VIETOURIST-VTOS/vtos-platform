# -*- coding: utf-8 -*-
"""ĐỐI CHIẾU LÃI LỖ TOUR: SỔ ↔ BẢNG TÍNH — Đợt R5b-1, 02/11/2026.

Chủ tịch chốt 01/11/2026: *"số từ SỔ là số thật, bảng tính để cạnh để so, có cột lệch"*, và
*"ghép theo mã tour, và nói ra bên nào thiếu"*.

TỆP NÀY KHÔNG TÍNH MỘT CON SỐ LÃI LỖ NÀO — VÀ ĐÓ LÀ CẢ ĐIỂM CỦA NÓ

Ngày 09/9/2026 VTOS có BỐN công thức lãi lỗ tour chạy song song, cho bốn con số khác nhau cho
cùng một chuyến. Chủ tịch chốt lấy quyết toán chi tiết làm chuẩn, và `services/lai_lo_tour.py`
mở đầu bằng câu *"mọi màn hình phải gọi vào đây, không tự cộng lại"*.

Nên tệp này gọi ĐÚNG HAI nguồn đã có và chỉ làm một phép TRỪ:

    SỔ        `books.project_summary(db, tu, den)`     — gom `journal_lines` theo `project_code`
    BẢNG TÍNH `lai_lo_tour.so_theo_vietrip(db, tours)` — booking và dòng chi phí quyết toán

Viết lại một trong hai ở đây là dựng công thức thứ NĂM, và lần này còn khó thấy hơn vì nó nằm
trong một bảng mang tên "đối chiếu". Có một phép thử soi lại điều ấy.

ĐỢT NÀY KHÔNG ĐỔI CHUẨN 09/9 (Chủ tịch chốt 01/11/2026, phương án "thêm thẻ đối chiếu")

Bảng Lãi lỗ tour của Điều hành giữ nguyên chuẩn quyết toán chi tiết. Thẻ này là chỗ ĐỐI CHIẾU:
cột Sổ đứng trước, bảng tính để cạnh, cột lệch nói to. Không màn hình nào đang chạy bị đổi số.

BA ĐIỀU PHẢI LÀM ĐÚNG, mỗi điều chống một kiểu nói sai

  1. LỆCH CHỈ TÍNH KHI CÓ CẢ HAI BÊN. Thiếu một bên thì lệch RỖNG, không phải bằng chính bên
     còn lại. Quy tắc 4 của `services/nhap_lieu.py`. Một tour chưa ghi sổ mà báo "lệch 900
     triệu" là nói sổ sai, trong khi sự thật là sổ chưa có gì.
  2. HAI RỔ THIẾU PHẢI HIỆN RA, không bị bỏ im lặng. Mã có trong sổ mà không có tour, và tour
     có số mà mã chưa vào sổ — đó đúng là hai chỗ cần nhìn nhất, cùng hình với dòng thiếu mã
     của Đợt R6b.
  3. HAI CƠ SỞ NGÀY KHÁC NHAU, và tệp này NÓI RA chứ không gộp. Sổ lọc theo NGÀY HẠCH TOÁN của
     bút toán; bảng tính lấy chuyến theo NGÀY KHỞI HÀNH. Một chuyến đi tháng 12 mà hóa đơn về
     tháng 1 sẽ nằm ở hai khoảng khác nhau — lệch ấy là THẬT và là một việc phải xử, không phải
     một lỗi của phép đối chiếu. Giấu nó đi bằng cách gộp hai cơ sở ngày là xoá mất chính câu
     hỏi ấy.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.services import books as BK
from app.services import lai_lo_tour as LL

# Ngưỡng coi là khớp: 1 đồng. Giống mọi phép cân khác trong kho (`abs(td - tc) >= 1`), không
# khai một ngưỡng riêng cho bảng này — hai ngưỡng là hai định nghĩa "khớp".
NGUONG = 1.0

CO_SO_NGAY = {
    "so": "Sổ: lọc theo NGÀY HẠCH TOÁN của bút toán",
    "bang_tinh": "Bảng tính: lấy chuyến theo NGÀY KHỞI HÀNH, cộng mọi chuyến có mã trong sổ",
}

RO = {
    "chi_co_trong_so": "Có trong SỔ mà không có chuyến nào mang mã ấy",
    "chi_co_bang_tinh": "Chuyến CÓ số trên bảng tính mà mã chưa có dòng nào trong sổ",
}


def _lech(a: float | None, b: float | None) -> float | None:
    """Lệch = sổ − bảng tính, và RỖNG khi thiếu một bên.

    Quy tắc 4: thiếu một bên thì không có lệch nào cả. Trả `a or 0` − `b or 0` là biến "chưa
    ghi sổ" thành "sổ lệch đúng bằng bảng tính" — một con số to, trông như lỗi sổ, và sai.
    """
    if a is None or b is None:
        return None
    return round(a - b, 0)


def doi_chieu(db: Session, tu: date, den: date, gioi_han: int = 500) -> dict:
    """Bảng đối chiếu lãi lỗ tour: SỔ ↔ BẢNG TÍNH, ghép theo MÃ TOUR.

    `gioi_han` cắt DANH SÁCH dòng, không cắt phần TỔNG: tổng cộng trên toàn bộ tập ghép, nên
    nó vẫn đúng khi danh sách bị cắt — cùng luật mà `services/books.py` đã đặt cho mọi sổ.
    """
    so = BK.project_summary(db, tu, den)
    so_theo_ma = {(r["project_code"] or "").strip(): r for r in so["rows"] if (r["project_code"] or "").strip()}
    ma_so = set(so_theo_ma)

    # Chuyến của CẢ HAI nguồn: mã đã có trong sổ, CỘNG chuyến khởi hành trong khoảng. Lấy hợp
    # của hai tập chứ không lấy một tập rồi tra tập kia — lấy một tập là bỏ mất đúng một trong
    # hai rổ thiếu.
    dk = [and_(Tour.start_date >= tu, Tour.start_date <= den)]
    if ma_so:
        dk.append(Tour.code.in_(sorted(ma_so)))
    tours = list(db.execute(select(Tour).where(or_(*dk))).scalars())
    cap = LL.so_theo_vietrip(db, tours)
    bt_theo_ma: dict[str, dict] = {}
    for t in tours:
        ma = (t.code or "").strip()
        if not ma:
            continue
        dt, gv = cap.get(t.id, (None, None))
        bt_theo_ma[ma] = {
            "ten_tour": t.name, "tour_id": t.id, "ngay_khoi_hanh": t.start_date,
            "trang_thai": t.status, "doanh_thu": dt, "gia_von": gv,
            "loi_nhuan": None if (dt is None or gv is None) else round(dt - gv, 0),
        }

    dong = []
    for ma in sorted(set(so_theo_ma) | set(bt_theo_ma)):
        s = so_theo_ma.get(ma)
        b = bt_theo_ma.get(ma)
        # SỔ ĐỨNG TRƯỚC: `cost` của sổ là chi phí đã ghi sổ, `profit` là lãi trên sổ. Không
        # đổi tên sang "giá vốn" — hai chữ ấy là hai khái niệm, và bảng này đang so chúng.
        s_dt = s["revenue"] if s else None
        s_cp = s["cost"] if s else None
        s_ln = s["profit"] if s else None
        b_dt = b["doanh_thu"] if b else None
        b_cp = b["gia_von"] if b else None
        b_ln = b["loi_nhuan"] if b else None
        l_dt, l_cp, l_ln = _lech(s_dt, b_dt), _lech(s_cp, b_cp), _lech(s_ln, b_ln)
        dong.append({
            "ma": ma,
            "ten_tour": (b or {}).get("ten_tour") or "",
            "tour_id": (b or {}).get("tour_id"),
            "ngay_khoi_hanh": (b or {}).get("ngay_khoi_hanh"),
            "trang_thai": (b or {}).get("trang_thai") or "",
            "so_doanh_thu": s_dt, "so_chi_phi": s_cp, "so_loi_nhuan": s_ln,
            "bt_doanh_thu": b_dt, "bt_gia_von": b_cp, "bt_loi_nhuan": b_ln,
            "lech_doanh_thu": l_dt, "lech_chi_phi": l_cp, "lech_loi_nhuan": l_ln,
            "co_trong_so": s is not None,
            "co_trong_bang_tinh": b is not None and b_dt is not None,
            # KHỚP chỉ khi CÓ CẢ HAI BÊN và cả ba cột lệch đều dưới ngưỡng. Thiếu một bên thì
            # KHÔNG khớp và cũng KHÔNG lệch — nó là "chưa so được", một trạng thái thứ ba.
            "khop": (s is not None and b_ln is not None
                     and all(x is not None and abs(x) < NGUONG for x in (l_dt, l_cp, l_ln))),
            "chua_so_duoc": s is None or b_ln is None,
        })

    chi_so = [d for d in dong if d["co_trong_so"] and not d["co_trong_bang_tinh"]]
    chi_bt = [d for d in dong if d["co_trong_bang_tinh"] and not d["co_trong_so"]]
    so_duoc = [d for d in dong if not d["chua_so_duoc"]]
    lech = [d for d in so_duoc if not d["khop"]]

    # TỔNG chỉ cộng những dòng SO ĐƯỢC — cùng luật mà `lai_lo_tour._cong` đã đặt: cộng cả dòng
    # thiếu một bên vào là tạo ra một con số lệch giả, và giả theo hướng dễ chịu.
    cong = {
        "so_dong_so_duoc": len(so_duoc), "so_dong_chua_so_duoc": len(dong) - len(so_duoc),
        "so_doanh_thu": round(sum(d["so_doanh_thu"] or 0 for d in so_duoc), 0),
        "so_chi_phi": round(sum(d["so_chi_phi"] or 0 for d in so_duoc), 0),
        "so_loi_nhuan": round(sum(d["so_loi_nhuan"] or 0 for d in so_duoc), 0),
        "bt_doanh_thu": round(sum(d["bt_doanh_thu"] or 0 for d in so_duoc), 0),
        "bt_gia_von": round(sum(d["bt_gia_von"] or 0 for d in so_duoc), 0),
        "bt_loi_nhuan": round(sum(d["bt_loi_nhuan"] or 0 for d in so_duoc), 0),
    }
    cong["lech_doanh_thu"] = round(cong["so_doanh_thu"] - cong["bt_doanh_thu"], 0)
    cong["lech_chi_phi"] = round(cong["so_chi_phi"] - cong["bt_gia_von"], 0)
    cong["lech_loi_nhuan"] = round(cong["so_loi_nhuan"] - cong["bt_loi_nhuan"], 0)

    canh_bao = []
    if chi_so:
        canh_bao.append({
            "loai": "chi_co_trong_so", "muc": "do", "so_dong": len(chi_so), "ten": RO["chi_co_trong_so"],
            "chi_tiet": "Sổ có số mà không chuyến nào mang mã ấy. Hoặc mã công trình gõ sai khi "
                        "hạch toán, hoặc chuyến đã bị xoá khỏi danh mục. Không cộng vào tổng.",
            "ma": [d["ma"] for d in chi_so[:20]]})
    if chi_bt:
        canh_bao.append({
            "loai": "chi_co_bang_tinh", "muc": "do", "so_dong": len(chi_bt), "ten": RO["chi_co_bang_tinh"],
            "chi_tiet": "Chuyến có doanh thu trên bảng tính mà sổ chưa có dòng nào mang mã ấy — "
                        "nghĩa là doanh thu / chi phí của chuyến chưa vào sổ kế toán, hoặc vào "
                        "mà không gắn mã công trình. Không cộng vào tổng.",
            "ma": [d["ma"] for d in chi_bt[:20]]})
    if lech:
        canh_bao.append({
            "loai": "lech_so", "muc": "vang", "so_dong": len(lech),
            "ten": "So được cả hai bên mà vẫn lệch",
            "chi_tiet": "Đây là những dòng đáng đọc nhất: cả sổ và bảng tính đều có số, và hai "
                        "số khác nhau. Sổ là số thật; chênh là việc phải giải thích.",
            "ma": [d["ma"] for d in lech[:20]]})

    return {
        "tu": tu, "den": den,
        "dong": dong[:max(1, gioi_han)],
        "tong_dong": len(dong), "hien_dong": len(dong[:max(1, gioi_han)]),
        "cat_bot": len(dong) > gioi_han,
        "cong": cong,
        "chi_co_trong_so": [d["ma"] for d in chi_so],
        "chi_co_bang_tinh": [d["ma"] for d in chi_bt],
        "canh_bao": canh_bao,
        "khop": not lech and not chi_so and not chi_bt,
        "co_so_ngay": CO_SO_NGAY,
        "ghi_chu": "Cột SỔ là số thật (Chủ tịch chốt 01/11/2026). Bảng tính để cạnh để so, "
                   "không để thay. Tổng chỉ cộng dòng so được cả hai bên.",
    }
