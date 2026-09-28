# -*- coding: utf-8 -*-
"""NẮN LẠI DÒNG NGOẠI TỆ THIẾU TỶ GIÁ — Chủ tịch quyết 27/9/2026, sau khi ĐÃ ĐO.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CỬA NÀY KHÔNG GIỐNG CÁI ĐÃ HÌNH DUNG HÔM QUA
═══════════════════════════════════════════════════════════════════════════════════════════════
Hôm 27/9 sáng, khi mới có `soat_ngoai_te` mà chưa chạy trên dữ liệu thật, cửa nắn được hình dung là
"sửa từng dòng đã ghi sai quy ước" — vì lúc ấy chỗ sai tưởng là *người nhập hiểu ô `so_tien_goc`
theo nghĩa nào*, và điều đó chỉ người nhập biết.

Đo thật thì KHÁC HẲN:

    sai_bo_nhan  = 0        ← KHÔNG dòng nào ghi sai quy ước. Cửa nắn kiểu cũ không cần.
    thieu_o      = 61       ← cả 61 dòng THIẾU TỶ GIÁ, nên `actual` = 0
    nguồn        = kho_cu_h1_2026, toàn bộ là phí visa (LSQ, TLS/VFS) của 10 chuyến dịch vụ lẻ
    chưa quy đổi = 3.345 CAD + 3.743 USD + 2.261,4 AUD

Việc thật không phải "sửa 61 con số", mà là "nhập 11 con số TỶ GIÁ rồi máy nhân lại". Đếm CẶP
(đồng tiền × ngày) chứ không đếm dòng là cách duy nhất nói đúng khối lượng việc.

═══════════════════════════════════════════════════════════════════════════════════════════════
BỐN ĐIỀU ĐƯỢC ÉP TRONG CẤU TRÚC, KHÔNG PHẢI TRONG LỜI DẶN
═══════════════════════════════════════════════════════════════════════════════════════════════

1. TỶ GIÁ LẤY TỪ SỔ TỶ GIÁ. Cửa này KHÔNG có ô gõ tỷ giá.
   Ranh giới 09/9/2026: Claude viết cấu trúc và phép tính, không nhập số liệu. Một cửa nắn cho gõ
   tỷ giá ngay tại chỗ là mở đường cho 61 dòng mang 61 tỷ giá không ai truy được — đúng cái bệnh
   `models/ty_gia.py` sinh ra để chữa. Chưa có tỷ giá trong sổ thì dòng ấy KHÔNG nắn được, và màn
   hình nói ra thiếu con số nào.

2. MỘT NGÀY, NHIỀU NGUỒN → NGƯỜI CHỌN, MÁY KHÔNG CHỌN.
   Sổ cho phép "Vietcombank bán ra" và "tỷ giá hợp đồng đối tác" cùng một ngày khác nhau, và phải
   khác nhau. Máy lấy bừa một dòng là tự đặt ra một sự thật.

3. CHUYẾN ĐÃ ĐÓNG SỐ THÌ KHÔNG NẮN LẶNG LẼ.
   Đo được 27/9: cả 61 dòng nằm trên chuyến `da_dong_so`. Cửa này KHÔNG tự mở khoá — nó dừng lại và
   nói "Kế toán trả lại trước". Sửa một chuyến đã chốt số mà không ai ký là xoá mất cái ranh giới
   giữa "số đang soạn" và "số đã chốt", thứ đắt nhất của cả phân hệ quyết toán.

4. KHÔNG CHẠM DÒNG ĐÃ CÓ SỐ.
   Chỉ nắn dòng `actual` rỗng hoặc 0. Một dòng đã có con số — dù từ đâu — là một con số ai đó đã
   nhìn; ghi đè nó là việc khác hẳn, và phải có cửa khác.

═══════════════════════════════════════════════════════════════════════════════════════════════
NGÀY TỶ GIÁ: "CUỐI THÁNG", KHÔNG PHẢI "NGÀY KHỞI HÀNH"
═══════════════════════════════════════════════════════════════════════════════════════════════
Chủ tịch chọn lấy NGÀY KHỞI HÀNH CHUYẾN làm ngày tỷ giá, vì kho cũ không mang ngày tỷ giá nào cả.

Nhưng đo ra thì 11 ngày ấy đều rơi vào 31/01, 28/02, 31/03, 30/04, 30/06 — tức CUỐI THÁNG, vì bộ
nạp kho cũ đặt ngày ấy khi tệp gốc chỉ có tháng. Đó KHÔNG phải ngày đi thật.

Chủ tịch được báo lại điều này và giữ nguyên lựa chọn (27/9/2026). Nên nhãn ghi vào từng dòng là
**"tỷ giá cuối tháng"**, không phải "tỷ giá ngày khởi hành": tỷ giá cuối tháng là một mốc kế toán
có thật và giải trình được với kiểm toán, còn "ngày khởi hành" ở đây là một ngày máy tự đặt. Viết
nhãn sai là để lại cho người ba tháng sau một câu trả lời sai cho câu hỏi "con số này ở đâu ra".
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour, User
from app.models.ty_gia import TyGia
from app.models.vietrip import TourCostLine
from app.services import chu_ho_so as CHS
from app.services import rules as R
from app.services.settlement import EDITABLE, Gate, calc_actual

# Nhãn ghi vào ghi chú của MỌI dòng được nắn. Người đọc dòng ba tháng sau phải biết con số ấy không
# do người nhập gõ, mà do máy nhân từ một tỷ giá trong sổ — và nhân theo mốc nào.
NHAN = "tỷ giá cuối tháng"


def _cuoi_thang(t: Tour) -> date | None:
    """Ngày tỷ giá dùng cho dòng kho cũ của chuyến này.

    Lấy `start_date` — nhưng KHÔNG gọi nó là "ngày khởi hành" ở bất cứ chỗ nào người dùng đọc: với
    dòng kho cũ, bộ nạp đặt ngày ấy bằng ngày cuối tháng của tệp gốc. Xem đầu tệp.
    """
    return t.start_date


def _can_nan(l: TourCostLine) -> bool:
    """Dòng này có nằm trong phạm vi cửa nắn không. Bốn điều kiện, không nới cái nào."""
    tt = (l.tien_te or "").strip().upper()
    return (bool(tt) and tt != "VND"                       # có khai ngoại tệ
            and bool(l.so_tien_goc)                        # có đơn giá đồng gốc
            and l.ty_gia is None                           # CHƯA có tỷ giá — đây là chỗ thiếu
            and not (l.actual or 0)                        # chưa có con số nào ai đã nhìn
            and l.status == "hd")                          # không phải dòng đã huỷ


def _nguon_ty_gia(db: Session, tt: str, ngay: date | None) -> list[dict]:
    if not ngay:
        return []
    rows = db.scalars(select(TyGia).where(TyGia.tien_te == tt, TyGia.ngay == ngay)
                      .order_by(TyGia.nguon)).all()
    return [{"id": r.id, "nguon": r.nguon, "loai_gia": r.loai_gia, "ty_gia": float(r.ty_gia or 0)}
            for r in rows if r.ty_gia]


def xem_truoc(db: Session, gioi_han: int = 300) -> dict:
    """Sổ CHỈ ĐỌC: dòng nào nắn được, dòng nào còn vướng, và vướng vì cái gì.

    Ba lý do vướng, và chúng KHÁC NHAU — gộp làm một là bắt người đọc đi tra mã nguồn:
      · `thieu_ty_gia`     sổ chưa có tỷ giá cho cặp (đồng tiền × ngày) ấy   → nhập sổ trước
      · `nhieu_nguon`      sổ có HAI nguồn trở lên cùng ngày                 → người phải chọn
      · `chuyen_da_dong`   chuyến đã đóng số / Kế toán đã xác nhận / khoá    → Kế toán trả lại trước
    """
    tours = {t.id: t for t in db.execute(select(Tour)).scalars()}

    nan_duoc, vuong = [], []
    can_ty_gia: dict[tuple[str, str], int] = {}
    tong_theo_dong: dict[str, float] = {}

    q = select(TourCostLine).where(TourCostLine.tien_te.is_not(None),
                                   TourCostLine.tien_te != "",
                                   TourCostLine.tien_te != "VND")
    for l in db.execute(q.order_by(TourCostLine.tour_id, TourCostLine.line_no)).scalars():
        if not _can_nan(l):
            continue
        t = tours.get(l.tour_id)
        if t is None:
            continue
        tt = (l.tien_te or "").upper()
        ngay = _cuoi_thang(t)
        nguon = _nguon_ty_gia(db, tt, ngay)
        goc_nhan = calc_actual(l.cost_kind or "co_dinh", float(l.so_tien_goc or 0),
                               float(l.qty or 0), float(l.coef or 1), 2)
        tong_theo_dong[tt] = round(tong_theo_dong.get(tt, 0.0) + goc_nhan, 2)

        chung = {"line_id": l.id, "tour_id": t.id, "tour": t.code, "dong": l.line_no,
                 "mo_ta": (l.description or "")[:80], "ncc": (l.supplier_name or "")[:60],
                 "tien_te": tt, "so_tien_goc": float(l.so_tien_goc or 0),
                 "so_luong": l.qty, "he_so": l.coef, "cach_tinh": l.cost_kind,
                 "tong_dong_goc": goc_nhan, "ngay_ty_gia": ngay, "nhan_ngay": NHAN,
                 "trang_thai_chuyen": t.status, "chu_ho_so": CHS.ten_chu_ho_so(db, t),
                 "nguon_ty_gia": nguon}

        if not nguon:
            if ngay:
                can_ty_gia[(tt, ngay.isoformat())] = can_ty_gia.get((tt, ngay.isoformat()), 0) + 1
            vuong.append({**chung, "vuong": "thieu_ty_gia",
                          "vuong_ten": f"Sổ tỷ giá chưa có {tt} ngày "
                                       f"{ngay:%d/%m/%Y}" if ngay else "Chuyến không có ngày"})
        elif t.status not in EDITABLE:
            vuong.append({**chung, "vuong": "chuyen_da_dong",
                          "vuong_ten": "Chuyến đã đóng số – Kế toán phải trả lại trước khi nắn"})
        elif len(nguon) > 1:
            vuong.append({**chung, "vuong": "nhieu_nguon",
                          "vuong_ten": f"Sổ có {len(nguon)} nguồn cho ngày này – người nắn phải chọn"})
        else:
            tg = nguon[0]["ty_gia"]
            goc = float(l.so_tien_goc or 0)
            nan_duoc.append({**chung, "ty_gia": tg, "nguon_chon": nguon[0]["nguon"],
                             "actual_se_thanh": calc_actual(l.cost_kind or "co_dinh",
                                                            round(goc * tg, 2),
                                                            float(l.qty or 0), float(l.coef or 1))})

    return {
        "nan_duoc": nan_duoc[:gioi_han], "vuong": vuong[:gioi_han],
        "dem": {"nan_duoc": len(nan_duoc), "vuong": len(vuong)},
        "dem_vuong": {k: sum(1 for v in vuong if v["vuong"] == k)
                      for k in ("thieu_ty_gia", "nhieu_nguon", "chuyen_da_dong")},
        "can_ty_gia": sorted([{"tien_te": a, "ngay": b, "so_dong": n}
                              for (a, b), n in can_ty_gia.items()],
                             key=lambda x: (x["tien_te"], x["ngay"])),
        "tong_dong_goc_chua_quy_doi": tong_theo_dong,
        "nhan_ngay": NHAN,
        "luu_y": ("Không có dòng nào trong phạm vi cửa nắn — chưa chắc đã sạch, hãy xem sổ soát "
                  "ngoại tệ." if not nan_duoc and not vuong else
                  f"Ngày tỷ giá lấy theo mốc CUỐI THÁNG của chuyến ({NHAN}), không phải ngày khởi "
                  "hành thật: kho quyết toán cũ không mang ngày tỷ giá nào, và bộ nạp đặt ngày cuối "
                  "tháng khi tệp gốc chỉ có tháng. Chủ tịch được báo điều này và giữ nguyên lựa "
                  "chọn (27/9/2026). Máy KHÔNG gõ hộ tỷ giá: con số lấy từ Sổ tỷ giá, ai nhập sổ "
                  "thì người ấy chịu trách nhiệm cho nó."),
    }


def nan_mot_dong(db: Session, u: User, l: TourCostLine, ty_gia_id: int, ly_do: str) -> dict:
    """Nắn MỘT dòng, có người bấm và ghi lý do. Trả về số trước và số sau.

    Mọi cổng đều nổ trước khi chạm vào con số — và không cổng nào có đường vòng:
      · dòng phải nằm trong phạm vi (`_can_nan`)
      · chuyến phải đang soạn được (`EDITABLE`) — cửa này KHÔNG tự mở khoá chuyến đã đóng số
      · người bấm phải là CHỦ HỒ SƠ của chuyến — đúng luật "một chủ hồ sơ" 26/9/2026, không thêm
        một ngoại lệ theo vai trò nào
      · tỷ giá phải là MỘT DÒNG CÓ THẬT trong sổ, đúng đồng tiền và đúng ngày của chuyến
      · phải có lý do bằng chữ
    """
    t = db.get(Tour, l.tour_id)
    if t is None:
        raise Gate("QT_NHAP", "Dòng không thuộc chuyến nào")
    if not _can_nan(l):
        raise Gate("QT_NHAP",
                   "Dòng này không nằm trong phạm vi nắn: chỉ nắn dòng khai ngoại tệ, có đơn giá "
                   "đồng gốc, CHƯA có tỷ giá và CHƯA có số thực chi. Dòng đã có số là số ai đó đã "
                   "nhìn — ghi đè nó là việc khác, phải có cửa khác.")
    if t.status not in EDITABLE:
        raise Gate("TRANG_THAI",
                   f"Chuyến {t.code} đã đóng số/xác nhận – Kế toán phải trả lại trước khi nắn. "
                   "Cửa này không tự mở khoá một chuyến đã chốt số.")
    if not CHS.la_chu_ho_so(db, u, t):
        raise Gate("CONG_6", f"Một chủ hồ sơ: chỉ {CHS.ten_chu_ho_so(db, t)} nắn được dòng của "
                             f"chuyến {t.code}")
    if not (ly_do or "").strip():
        raise Gate("QT_NHAP", "Nắn một con số tiền phải ghi lý do")

    tg = db.get(TyGia, ty_gia_id)
    tt = (l.tien_te or "").upper()
    ngay = _cuoi_thang(t)
    if tg is None or not tg.ty_gia:
        raise Gate("QT_NHAP", "Không có dòng tỷ giá ấy trong sổ")
    if tg.tien_te != tt or tg.ngay != ngay:
        raise Gate("QT_NHAP",
                   f"Dòng tỷ giá đã chọn là {tg.tien_te} ngày {tg.ngay:%d/%m/%Y}, nhưng dòng chi "
                   f"cần {tt} ngày {ngay:%d/%m/%Y}. Không lấy tỷ giá của một ngày khác thay vào.")

    truoc = {"ty_gia": l.ty_gia, "ngay_ty_gia": l.ngay_ty_gia,
             "unit_price": l.unit_price, "actual": l.actual}

    ty = float(tg.ty_gia)
    # `_can_nan` đã chặn dòng không có đơn giá đồng gốc, nhưng đọc cột tiền vẫn phải chịu được rỗng:
    # hàng rào K2 đọc CÚ PHÁP chứ không đọc luồng, và nó đúng khi khó tính — một câu chặn ở dòng
    # trên có thể bị người sau gỡ mà không ai để ý, còn `or 0` thì nằm ngay tại chỗ đọc.
    goc_nt = float(l.so_tien_goc or 0)
    don_gia_vnd = round(goc_nt * ty, 2)
    l.ty_gia, l.ngay_ty_gia = ty, ngay
    l.unit_price = don_gia_vnd
    l.actual = calc_actual(l.cost_kind or "co_dinh", don_gia_vnd,
                           float(l.qty or 0), float(l.coef or 1))
    dau = (f"[NẮN {datetime.now():%d/%m/%Y}] {NHAN} {tt} {ngay:%d/%m/%Y} = {ty:,.2f} "
           f"(nguồn: {tg.nguon or 'không ghi nguồn'}) – {ly_do.strip()}")
    l.note = (dau + " | " + (l.note or ""))[:200]
    l.updated_by = u.username

    sau = {"ty_gia": l.ty_gia, "ngay_ty_gia": l.ngay_ty_gia,
           "unit_price": l.unit_price, "actual": l.actual}
    # Nhật ký lưu dạng JSON — ngày phải thành chuỗi trước khi ghi, nếu không cả giao dịch nổ ở
    # đúng lúc ghi vết, tức là nắn xong mà không có dấu vết. Đổi ở đây chứ không ở `rules.audit`:
    # sửa hàm nhật ký dùng chung cho cả hệ vì một chỗ gọi là việc của một đợt khác.
    def _chu(d: dict) -> dict:
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in d.items()}

    R.audit(db, u.username, u.role, "nan_ngoai_te", f"tour:{t.code}",
            before=_chu({"dong": l.line_no, **truoc}),
            after=_chu({"dong": l.line_no, **sau, "ty_gia_id": tg.id, "nguon": tg.nguon,
                        "ly_do": ly_do.strip()[:120]}))
    db.commit()
    return {"line_id": l.id, "tour": t.code, "dong": l.line_no, "truoc": truoc, "sau": sau,
            "message": f"Đã nắn dòng {l.line_no} chuyến {t.code}: {l.actual:,.0f} đ "
                       f"({NHAN} {ty:,.2f})"}
