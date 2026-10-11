"""Bàn làm việc của Phó Tổng giám đốc tour đoàn — 24/9/2026.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO MÀN HÌNH NÀY MỞ RA LÀ HÀNG ĐỢI KÝ, KHÔNG PHẢI BẢNG DOANH THU
═══════════════════════════════════════════════════════════════════════════════════════════════
Theo Điều 4 Văn bản đính chính, `rules.approver_role()` định tuyến MỌI tour đoàn về `ptgd_doan`.
Quyền ấy đã chạy trong mã từ lâu, nhưng chưa có một màn hình nào dựng quanh nó: người ký phải tự
đi tìm từng chuyến trong danh sách tour chung, lọc bằng mắt.

Một cổng chặn mà người giữ cổng phải tự đi tìm việc là một cổng sẽ được ký muộn — và ký muộn một
dự toán thì chuyến vẫn chạy, chỉ là chạy trước khi có ai duyệt. Hàng đợi này không thêm quyền nào,
nó chỉ làm cho quyền đã có nhìn thấy được.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA CHỖ CỐ Ý LÀM KHÁC, MỖI CHỖ MỘT LÝ DO
═══════════════════════════════════════════════════════════════════════════════════════════════
1. KHỐI "DƯỚI BIÊN" TÁCH RIÊNG VÀ KHÔNG CÓ ĐƯỜNG KÝ.
   Chuyến dưới ngưỡng biên phải đủ chữ ký Chủ tịch VÀ Tổng giám đốc (`tours.approve`), P.TGĐ không
   ký được. Trộn chúng vào hàng đợi chính là vẽ ra một nút mà bấm vào sẽ nhận 403; bỏ hẳn chúng đi
   thì người phụ trách mảng đoàn không biết chuyến của mình đang nằm chờ ai. Nên: hiện ra, đếm
   riêng, và cửa này KHÔNG trả về bất kỳ đường ký nào cho chúng.

2. `thieu` TÍNH LẠI TỪ CHÍNH LUẬT CỦA BƯỚC TRÌNH, KHÔNG CHÉP TAY.
   Cùng ba điều kiện mà `tours.submit` dùng — đủ cơ sở tính, có điểm dừng nghỉ, giải trình đủ dài
   khi dưới biên. Chép tay danh sách ấy sang đây là tạo ra bản sao thứ hai của một luật: ngày
   `submit` siết thêm một điều kiện, màn hình này vẫn báo "đủ trường" cho một hồ sơ mà bước trình
   sẽ từ chối, và người ký sẽ tin màn hình.

3. QUÁ HẠN QUYẾT TOÁN ĐẾM CẢ CHUYẾN CHƯA ĐÓNG SỔ LẪN CHUYẾN ĐÓNG MUỘN.
   Chỉ đếm chuyến chưa đóng thì con số tự đẹp lên mỗi lần có người đóng muộn một chuyến — thước đo
   tự lành, và cái nó đo được thì biến mất. Hai nhóm đếm riêng, không cộng chung.

═══════════════════════════════════════════════════════════════════════════════════════════════
KHÔNG NHỚ TẠM
═══════════════════════════════════════════════════════════════════════════════════════════════
Đây là danh sách việc phải làm. Người vừa ký xong một dự toán bấm lại mà nó vẫn nằm đó thì họ
tưởng bấm hụt, và sẽ ký lần nữa.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Tour
from app.services import rules as R

# Độ dài tối thiểu của giải trình 4 mục, lấy đúng con số bước TRÌNH đang dùng (tours.submit).
# Khai ở đây một lần để phép thử soi được, thay vì rải số 30 ở hai nơi.
GIAI_TRINH_TOI_THIEU = 30


def _thieu(db: Session, t: Tour) -> list[str]:
    """Những trường còn thiếu khiến dự toán chưa đủ tư cách trình — CÙNG LUẬT với `tours.submit`.

    Trả danh sách rỗng nghĩa là đủ. Không trả True/False: người ký cần biết THIẾU GÌ, và "chưa đủ"
    mà không nói thiếu gì thì người nhận lại hồ sơ phải đoán.
    """
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
    thieu: list[str] = []
    if not c["complete"]:
        for ten, ok in (("giá bán mỗi khách", (t.price_per_pax or 0) > 0),
                        ("số khách dự toán", t.planned_pax > 0),
                        ("chi phí cố định hoặc chi phí theo khách", c["has_cost"]),
                        ("giá bán phải lớn hơn chi phí theo khách", c["breakeven_pax"] is not None)):
            if not ok:
                thieu.append(ten)
    if not (t.rest_stops or "").strip():
        thieu.append("điểm dừng nghỉ")
    if not c["pass_gate"] and len((t.justification or "").strip()) < GIAI_TRINH_TOI_THIEU:
        thieu.append("giải trình 4 mục cho chuyến dưới biên")
    return thieu


def _dong_tour(db: Session, t: Tour) -> dict:
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
    hom_nay = date.today()
    return {
        "tour_id": t.id, "ma": t.code, "ten": t.name,
        "khoi_hanh": t.start_date.isoformat() if t.start_date else None,
        "ket_thuc": t.end_date.isoformat() if t.end_date else None,
        "con_bao_nhieu_ngay": (t.start_date - hom_nay).days if t.start_date else None,
        "so_khach_du_toan": t.planned_pax,
        "doanh_thu_du_kien": c["revenue"],
        "gia_von_du_kien": c["cost"],
        "bien_ke_hoach": c["margin"],
        "nguong_bien": c["threshold"],
        "duoi_bien": bool(t.below_margin),
        "thieu": _thieu(db, t),
        "tp_dh_xac_nhan_boi": t.confirmed_by or "",
    }


def cho_toi_duyet(db: Session) -> list[dict]:
    """Dự toán đoàn đang chờ ĐÚNG chữ ký của Phó TGĐ tour đoàn.

    Lọc bằng `R.approver_role(t) == "ptgd_doan"` chứ không bằng `tour_type`: định tuyến duyệt là
    một luật đã có chủ, và hỏi lại chính nó thì màn hình không bao giờ lệch với cửa ký. Viết
    `tour_type in DOAN_TYPES` ở đây là dựng định nghĩa "đoàn" thứ hai — đúng thứ `rules.is_doan`
    đã ghi rõ là phải tránh.
    """
    ds = db.execute(select(Tour).where(Tour.status == "cho_duyet")).scalars().all()
    ra = [_dong_tour(db, t) for t in ds
          if R.approver_role(t) == "ptgd_doan" and not t.below_margin]
    ra.sort(key=lambda d: (d["con_bao_nhieu_ngay"] is None, d["con_bao_nhieu_ngay"]))
    return ra


def duoi_bien_cho_hai_chu_ky(db: Session) -> list[dict]:
    """Đoàn dưới biên: hiện ra để biết, KHÔNG kèm đường ký.

    Mỗi dòng nói rõ còn thiếu chữ ký nào. Không suy ra "sắp xong" hay "gần đủ" — hai chữ ký thì
    một chữ ký là chưa có gì.
    """
    ds = db.execute(select(Tour).where(Tour.status == "cho_duyet")).scalars().all()
    ra = []
    for t in ds:
        if not (R.approver_role(t) == "ptgd_doan" and t.below_margin):
            continue
        d = _dong_tour(db, t)
        # TÊN NGƯỜI CÒN THIẾU PHẢI ĐỌC TỪ BẢNG LUẬT — sửa ở Đợt LG3, và đây là một lỗi thật mà
        # Đợt LG2 để lại: bảng này viết thẳng "Chủ tịch" và "Tổng giám đốc", nhưng từ 11/10/2026
        # chuyến dưới biên do NGƯỜI ĐỨNG ĐẦU PHÒNG BÁN ký, không còn Chủ tịch. Một bảng công
        # việc nói sai tên người cần ký là một bảng đẩy người đọc đi gõ nhầm cửa.
        from app.models.core import ROLES as _ROLES
        from app.services import chu_ky as _CK
        from app.services import segments as _SEG
        try:
            _can = _CK.can_ky_duoi_bien(_SEG.mang_of(t))
        except ValueError:
            _can = ()
            d["chu_ky_con_thieu_ghi_chu"] = _CK.CHUYEN_KHONG_THUOC_MANG
        _da = _CK.doc_nguoi_da_ky(getattr(t, "nguoi_da_ky", "") or "")
        con_thieu = [_ROLES.get(v, v) for v in _can
                     if not (bool(getattr(t, f"signed_{v}", False)) or v in _da)]
        d["chu_ky_con_thieu"] = con_thieu
        d["toi_khong_ky_duoc"] = True     # nói thẳng trên dữ liệu, không để màn hình tự đoán
        ra.append(d)
    ra.sort(key=lambda d: (d["con_bao_nhieu_ngay"] is None, d["con_bao_nhieu_ngay"]))
    return ra


def qua_han_quyet_toan(db: Session) -> dict:
    """Đoàn quá hạn chốt sổ. Hai nhóm ĐẾM RIÊNG, xem ghi chú 3 ở đầu tệp."""
    hom_nay = date.today()
    chua_dong: list[dict] = []
    dong_muon: list[dict] = []
    ds = db.execute(select(Tour).where(Tour.end_date.isnot(None))).scalars().all()
    for t in ds:
        if not R.is_doan(t):
            continue
        han = R.settlement_deadline(db, t)
        dong = t.closed_at.date() if getattr(t, "closed_at", None) else None
        if dong is None:
            if t.end_date <= hom_nay and han < hom_nay:
                chua_dong.append({"tour_id": t.id, "ma": t.code, "ten": t.name,
                                  "ket_thuc": t.end_date.isoformat(), "han_chot_so": han.isoformat(),
                                  "qua_han_ngay": (hom_nay - han).days,
                                  "dieu_hanh_id": t.operator_id})
        elif dong > han:
            dong_muon.append({"tour_id": t.id, "ma": t.code, "ten": t.name,
                              "ket_thuc": t.end_date.isoformat(), "han_chot_so": han.isoformat(),
                              "dong_luc": dong.isoformat(), "muon_ngay": (dong - han).days,
                              "dieu_hanh_id": t.operator_id})
    chua_dong.sort(key=lambda d: -d["qua_han_ngay"])
    dong_muon.sort(key=lambda d: -d["muon_ngay"])
    return {"chua_dong_so": chua_dong, "dong_muon": dong_muon,
            "han_theo_tham_so_ngay": int(R.get_param(db, "han_qt_doan", hom_nay))}


def lai_lo_da_quyet_toan(db: Session, ky: str) -> dict:
    """Đoàn đã quyết toán trong kỳ, kèm BIÊN KẾ HOẠCH đặt cạnh BIÊN THỰC TẾ.

    Cột lệch giữa hai biên là chỗ đo lại chính chữ ký của người duyệt. Một bảng chỉ có biên thực tế
    trả lời được "chuyến này lãi bao nhiêu" nhưng không trả lời được "lúc tôi ký thì tôi đã được cho
    xem con số nào" — mà câu thứ hai mới là câu nói lên dự toán có đáng tin hay không.

    Kỳ dạng "2026-09". Kỳ đọc không ra thì ném ValueError để cửa API trả 422 — đoán một kỳ mặc định
    là in ra một bảng số thật dưới một cái tên sai.
    """
    dau, cuoi = _bien_ky(ky)
    ds = db.execute(select(Tour).where(Tour.end_date >= dau, Tour.end_date <= cuoi)).scalars().all()
    dong: list[dict] = []
    tong_dt = tong_gv = 0.0
    for t in ds:
        if not R.is_doan(t) or not getattr(t, "closed_at", None):
            continue
        s = R.settlement_summary(db, t)
        ke_hoach = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))["margin"]
        dong.append({"tour_id": t.id, "ma": t.code, "ten": t.name,
                     "ket_thuc": t.end_date.isoformat(),
                     "doanh_thu": s["revenue"], "gia_von": s["cost"], "loi_nhuan": s["profit"],
                     "bien_ke_hoach": ke_hoach, "bien_thuc_te": s["margin"],
                     "lech_bien": s["margin"] - ke_hoach})
        tong_dt += s["revenue"] or 0
        tong_gv += s["cost"] or 0
    dong.sort(key=lambda d: d["lech_bien"])          # xấu nhất lên đầu, không phải to nhất lên đầu
    return {"ky": ky, "so_chuyen": len(dong), "rows": dong,
            "tong_doanh_thu": tong_dt, "tong_gia_von": tong_gv,
            "bien_binh_quan": (tong_dt - tong_gv) / tong_dt if tong_dt else None}


def _bien_ky(ky: str) -> tuple[date, date]:
    from calendar import monthrange
    nam, thg = int(ky[:4]), int(ky[5:7])
    return date(nam, thg, 1), date(nam, thg, monthrange(nam, thg)[1])


def ban_lam_viec(db: Session, ky: str) -> dict:
    cho = cho_toi_duyet(db)
    duoi = duoi_bien_cho_hai_chu_ky(db)
    qh = qua_han_quyet_toan(db)
    return {
        "cho_toi_duyet": cho,
        "duoi_bien_hai_chu_ky": duoi,
        "qua_han_quyet_toan": qh,
        "lai_lo": lai_lo_da_quyet_toan(db, ky),
        "dem": {
            "cho_toi_duyet": len(cho),
            # Đếm riêng chuyến sắp chạy: một hàng đợi 7 dòng mà 2 dòng khởi hành tuần này thì con số
            # 7 không nói lên điều gì — cái gấp nằm ở 2 dòng ấy.
            "cho_toi_duyet_khoi_hanh_duoi_7_ngay": len(
                [d for d in cho if d["con_bao_nhieu_ngay"] is not None and d["con_bao_nhieu_ngay"] <= 7]),
            "cho_toi_duyet_du_truong": len([d for d in cho if not d["thieu"]]),
            "duoi_bien_hai_chu_ky": len(duoi),
            "qua_han_chua_dong_so": len(qh["chua_dong_so"]),
            "dong_so_muon": len(qh["dong_muon"]),
        },
    }
