# -*- coding: utf-8 -*-
"""Quyết toán chuyến theo Mẫu 2 — hai tổng CỘNG RA, và chỗ tờ giấy tự mâu thuẫn.

Chủ tịch chọn Mẫu 2 ngày 13/10/2026 (mẫu có Tạm ứng / Hoàn trả / Chi thêm, tuyến ký
Tài xế → Điều hành → Kế toán → Tổng giám đốc).

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO TỆP NÀY TỒN TẠI
═══════════════════════════════════════════════════════════════════════════════════════════════

Hai bộ hồ sơ thật, đo ngày 13/10/2026, mỗi bộ 8 trang gồm tờ quyết toán có chữ ký + ảnh đồng hồ
đầu/cuối + hoá đơn dầu + biên lai ngân hàng + vé gửi xe. Cả hai bộ CỘNG ĐÚNG tổng cuối. Nhưng:

  · Bộ 50F-046.22 (Di sản miền Trung, 06–12/10): tờ giấy ghi SỐ KM ĐẦU 197.935. Ảnh đồng hồ đọc
    197.435, tin Zalo của tài xế cũng 197.435. Km cuối 199.768. Lấy 197.435 ra 2.333 km — đúng
    bằng "TỔNG KM TOUR 2.333" ghi trên CHÍNH TỜ GIẤY ẤY. Lấy 197.935 ra 1.833. Tờ giấy mâu thuẫn
    với chính nó, lệch 500 km, và 500 km ấy đi thẳng vào phép tính chi phí mỗi km.

  · Bộ 50F-034.71 (Đà Lạt–Nha Trang, 07–11/10): ô "TỔNG TÀI XẾ CHI" viết tay 1.360.000, trong khi
    công thức IN NGAY CẠNH NÓ là "phí gửi xe + phí khác" = 360.000. Người viết cộng nhầm cả công
    tác phí 1.000.000 — mà công tác phí đã nằm ở "TỔNG CÔNG TY CHI" bên dưới. Tổng cuối vẫn đúng,
    nên không ai thấy.

Hai lỗi khác loại nhau nhưng cùng một gốc: **một con số CỘNG RA ĐƯỢC mà vẫn để người gõ**. Nên
luật ở đây là: ô nào suy ra được thì máy suy, và máy ĐỐI CHIẾU với con số trên giấy chứ không im.

Máy KHÔNG tự sửa số của người. Nó nói ra chỗ lệch và để người chọn — chứng từ nào đứng sau con số
nào là việc của Kế toán, không phải của phép tính.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fleet import (Trip, TripCost, TRA_BANG, TRA_BANG_TAI_XE,
                              QT_BUOC, QT_TRANG_THAI, COST_KINDS)

# Bước nào do vai nào ký. Khai ở đây một lần; cửa API đọc vào chứ không khai lần thứ hai.
VAI_KY = {"dieu_hanh": ("tp_dh", "nv_dh", "gd_doi_xe"),
          "ke_toan": ("ketoan", "kt_truong"),
          "tgd": ("tgd", "chutich")}
# Trạng thái SAU khi bước ấy ký xong.
SAU_KHI_KY = {"dieu_hanh": "cho_ke_toan", "ke_toan": "cho_tgd", "tgd": "da_duyet"}
CHO_BUOC = {"cho_dieu_hanh": "dieu_hanh", "cho_ke_toan": "ke_toan", "cho_tgd": "tgd"}


def _s(x) -> float:
    return float(x or 0)


def tong(db: Session, t: Trip) -> dict:
    """Hai tổng của Mẫu 2 — CỘNG RA từ bảng khoản chi, không đọc ô người gõ.

    `tra_bang` rỗng nghĩa là chưa ai khai khoản ấy ai trả. KHÔNG đoán về bên nào: xếp riêng vào
    `chua_khai` và nói ra. Dồn nó vào "công ty chi" cho đẹp bảng là biến một ô còn thiếu thành một
    con số trông như đã xong.
    """
    cs = db.execute(select(TripCost).where(TripCost.trip_id == t.id)).scalars().all()
    tai_xe = cong_ty = chua_khai = 0.0
    for c in cs:
        v = _s(c.amount)
        if not (c.tra_bang or ""):
            chua_khai += v
        elif c.tra_bang in TRA_BANG_TAI_XE:
            tai_xe += v
        else:
            cong_ty += v
    return {
        "tai_xe_chi": tai_xe, "cong_ty_chi": cong_ty, "chua_khai_ai_tra": chua_khai,
        # Tổng chi phí tour = tất cả khoản chi, bất kể ai ứng ra. Tạm ứng / hoàn trả / chi thêm
        # KHÔNG nằm trong đây: đó là tiền đi qua tay tài xế, không phải chi phí của chuyến. Cộng
        # vào là đếm hai lần, và đếm hai lần vào đúng chỗ tính giá vốn.
        "tong_chi_phi_tour": tai_xe + cong_ty + chua_khai,
        # Tài xế còn được nhận (dương) hay còn nợ công ty (âm).
        #
        # ĐỢT DỌN-4 14/10/2026 — ba ô tiền này đều đi qua `_s()`, mà `_s(x)` chính là `float(x or 0)`,
        # nên dòng này ĐÃ chịu được giá trị rỗng. Máy quét K2 chỉ nhận ra chuỗi `or 0` viết ngay sau
        # chỗ đọc nên nó bắt nhầm — miễn Ở ĐÂY, một dòng một lý do, chứ không dạy máy quét một
        # danh sách "hàm này an toàn": làm thế thì ngày ai đó sửa thân `_s`, hàng rào tắt im lặng ở
        # MỌI chỗ gọi mà không đỏ một dòng nào.
        #
        # RỖNG Ở ĐÂY TÍNH BẮNG KHÔNG LÀ ĐÚNG, và đó là quyết định chứ không phải mặc định: chưa ai
        # nhập tạm ứng nghĩa là chưa ứng đồng nào, nên khoản tài xế còn nhận không bị trừ gì — khác
        # hẳn những chỗ mà rỗng nghĩa là "chưa biết số" và kết quả cũng phải rỗng theo.
        "tai_xe_con_nhan": tai_xe + _s(t.chi_them) - _s(t.tam_ung) - _s(t.hoan_tra),  # k2-doc-an-toan: ba o tien deu qua `_s()` = `float(x or 0)`
        "so_khoan": len(cs),
    }


def km_tour(t: Trip) -> int | None:
    if t.km_dau is None or t.km_cuoi is None:
        return None
    return t.km_cuoi - t.km_dau


def kiem(db: Session, t: Trip, km_tour_tren_giay: int | None = None) -> list[dict]:
    """Soát một tờ quyết toán. Trả danh sách điểm lệch, KHÔNG sửa gì.

    `muc`: "do" chặn ký, "vang" phải có người đọc rồi mới ký qua.
    """
    ra: list[dict] = []
    km = km_tour(t)

    if t.km_dau is None or t.km_cuoi is None:
        ra.append({"muc": "vang", "o": "km",
                   "noi": "Chưa có km đầu hoặc km cuối — để trống nghĩa là CHƯA ĐO, không phải 0."})
    elif km is not None and km <= 0:
        ra.append({"muc": "do", "o": "km",
                   "noi": f"Km cuối {t.km_cuoi:,} không lớn hơn km đầu {t.km_dau:,}."})

    # ĐÂY là phép bắt được lỗi 500 km của bộ 50F-046.22. Con số viết tay trên giấy là một NGUỒN
    # THỨ HAI, và hai nguồn lệch nhau thì phải có người nhìn — chứ không phải máy lặng lẽ chọn một.
    if km is not None and km_tour_tren_giay is not None and km != km_tour_tren_giay:
        ra.append({"muc": "do", "o": "km",
                   "noi": f"Km cuối − km đầu = {km:,} km, nhưng tờ giấy ghi tổng "
                          f"{km_tour_tren_giay:,} km. Lệch {abs(km - km_tour_tren_giay):,} km. "
                          f"Đối chiếu với ảnh đồng hồ đính kèm trước khi ký."})

    g = tong(db, t)
    if g["so_khoan"] == 0:
        ra.append({"muc": "do", "o": "chi_phi", "noi": "Chưa có khoản chi nào."})
    if g["chua_khai_ai_tra"] > 0:
        ra.append({"muc": "vang", "o": "tra_bang",
                   "noi": f"{g['chua_khai_ai_tra']:,.0f} đ chưa khai ai trả, nên chưa tách được "
                          f"'tài xế chi' với 'công ty chi'."})
    if t.ngay_ve and t.ngay_di and t.ngay_ve < t.ngay_di:
        ra.append({"muc": "do", "o": "ngay", "noi": "Ngày về trước ngày đi."})
    ra += kiem_tieu_hao(db, t)
    return ra


# ── QT-1b · TIÊU HAO L/100KM KHI QUYẾT TOÁN (Chủ tịch chốt 22/10/2026) ─────────────────────────
# QT-1 (13/10) để lại có chủ ý: chưa có phép kiểm tiêu hao, nên một chuyến khai dầu bất thường
# vẫn qua được quyết toán. Phép kiểm này CẢNH BÁO, KHÔNG CHẶN — mức "vang" chứ không phải "do":
# có chuyến đi đường xấu thật, chặn là chặn nhầm người làm đúng. Người ký đọc rồi tự quyết.
#
# KHÔNG DỰNG BẢNG ĐỊNH MỨC MỚI. `FuelNorm` (L/100km theo số chỗ) đã có cửa nhập ở màn Đội xe và
# đang được khối Hiệu quả đội xe đọc (HQ-2c). Hai bảng định mức là hai con số sẽ có ngày lệch nhau.
#
# BIÊN 15% — Chủ tịch chọn 22/10/2026. Vượt QUÁ biên mới cảnh báo; đúng bằng biên là chưa vượt.
# Biên đọc từ bảng tham số (`rules.DEFAULT_PARAMS` · `qt_tieu_hao_bien`), nên Kế toán chỉnh ở màn
# tham số mà không cần sửa mã. Bản đầu để hằng số vì `rules.py` khi ấy đang có làn khác giữ chỗ;
# SO-2 (#431) nhả chỗ ấy cùng ngày nên chuyển ngay. `BIEN_TIEU_HAO` chỉ còn là giá trị mặc định
# để phép thử đọc ra luật Chủ tịch chốt.
BIEN_TIEU_HAO = 0.15


def bien_tieu_hao(db: Session, ngay=None) -> float:
    from app.services import rules as R
    return float(R.get_param(db, "qt_tieu_hao_bien", ngay))


def tieu_hao(db: Session, t: Trip) -> dict | None:
    """Tiêu hao L/100km của MỘT chuyến, cùng chỗ thiếu nếu chưa đo được. Không có khoản dầu → None.

    SỐ LÍT (Chủ tịch chốt 22/10/2026): lít khai trên khoản dầu; khoản không ghi lít thì quy tiền ÷
    giá dầu ĐÚNG ngày đi (`phat_va_gia_dau.lit_tu_tien`, DX-3); không có giá ngày ấy thì nói ra là
    chưa đo được — KHÔNG đoán bằng giá gần nhất.
    """
    from app.models.fleet import FuelNorm
    from app.models.hr import Vehicle
    from app.services import phat_va_gia_dau as GD

    dau = [c for c in db.execute(select(TripCost).where(TripCost.trip_id == t.id,
                                                        TripCost.kind == "dau")).scalars()]
    if not dau:
        return None
    lit, thieu = 0.0, []
    for c in dau:
        if (c.lit or 0) > 0:
            lit += float(c.lit)
            continue
        q = GD.lit_tu_tien(db, t.ngay_di, _s(c.amount))
        if q["lit"] is None:
            thieu.append(q["vi_sao"])
        else:
            lit += q["lit"]
    km = km_tour(t)
    v = db.get(Vehicle, t.vehicle_id) if t.vehicle_id else None
    so_cho = v.seats if v else None
    dm = None
    if so_cho is not None:
        n = db.execute(select(FuelNorm).where(FuelNorm.seats == so_cho)).scalars().first()
        dm = float(n.l_100km) if n and n.l_100km else None
    return {"lit": round(lit, 2), "km": km, "so_cho": so_cho,
            "ghe_da_xac_nhan": bool(v and (v.seats_xac_nhan_boi or "").strip()),
            "l_100km": round(lit * 100 / km, 1) if (km and km > 0 and lit and not thieu) else None,
            "dinh_muc": dm, "thieu": thieu}


def kiem_tieu_hao(db: Session, t: Trip) -> list[dict]:
    th = tieu_hao(db, t)
    if th is None or not th["km"] or th["km"] <= 0:
        return []                       # không có dầu, hoặc km đã có dòng báo riêng ở trên
    if th["thieu"]:
        return [{"muc": "vang", "o": "tieu_hao",
                 "noi": "Chưa đo được tiêu hao: " + "; ".join(dict.fromkeys(th["thieu"])) + "."}]
    ghe = "" if th["ghe_da_xac_nhan"] else " (số ghế của xe chưa ai xác nhận)"
    if th["dinh_muc"] is None:
        return [{"muc": "vang", "o": "tieu_hao",
                 "noi": f"Chưa có định mức tiêu hao cho xe {th['so_cho']} chỗ{ghe} — Đội xe khai ở "
                        f"cửa định mức dầu thì phép kiểm này tự chạy."}]
    # Biên làm tròn tới 0,1 như chính con số L/100km: so hai số cùng độ chính xác, không để 20 × 1,15
    # = 22,999… của dấu phẩy động làm một chuyến đúng bằng biên bị báo vượt.
    tl = bien_tieu_hao(db, t.ngay_di)
    bien = round(th["dinh_muc"] * (1 + tl), 1)
    if th["l_100km"] > bien:
        vuot = (th["l_100km"] / th["dinh_muc"] - 1) * 100
        return [{"muc": "vang", "o": "tieu_hao",
                 "noi": f"Tiêu hao {th['l_100km']:.1f} L/100km ({th['lit']:,.1f} lít / {th['km']:,} km), "
                        f"vượt định mức {th['dinh_muc']:.1f} L/100km của xe {th['so_cho']} chỗ{ghe} "
                        f"{vuot:.0f}% (biên {tl * 100:.0f}%). Đối chiếu hoá đơn dầu và "
                        f"ảnh đồng hồ trước khi ký — không chặn: đường xấu có thể vượt thật."}]
    return []


def co_the_ky(t: Trip, buoc: str, vai: str) -> str:
    """Trả "" nếu ký được, hoặc câu nói vì sao không. Thứ tự là thứ tự, không nhảy cóc.

    Vì sao chặn nhảy cóc: tuyến ký của Mẫu 2 không phải bốn người cùng xác nhận một việc — mỗi
    bước kiểm một thứ khác nhau. Kế toán ký trước Điều hành nghĩa là Kế toán đã xác nhận một tờ
    chưa ai đối chiếu với lệnh điều xe.
    """
    if buoc not in QT_BUOC:
        return f"Không có bước ký '{buoc}'."
    if t.qt_trang_thai == "nhap":
        return "Tờ quyết toán chưa gửi đi — Đội xe còn đang nhập."
    if t.qt_trang_thai == "da_duyet":
        return "Tờ này đã đủ chữ ký."
    dang_cho = CHO_BUOC.get(t.qt_trang_thai or "")
    if dang_cho != buoc:
        ten = QT_TRANG_THAI.get(t.qt_trang_thai or "", t.qt_trang_thai or "")
        return f"Chưa tới lượt bước '{buoc}' — tờ này đang ở '{ten}'."
    if vai not in VAI_KY[buoc]:
        return f"Vai '{vai}' không ký được bước '{buoc}'."
    return ""


def ky(db: Session, t: Trip, buoc: str, nguoi: str, vai: str) -> dict:
    vi_sao = co_the_ky(t, buoc, vai)
    if vi_sao:
        raise ValueError(vi_sao)
    do = [x for x in kiem(db, t) if x["muc"] == "do"]
    if do:
        raise ValueError("Còn điểm chặn chưa xử: " + " · ".join(x["noi"] for x in do))
    setattr(t, f"qt_{buoc}", nguoi[:50])
    setattr(t, f"qt_{buoc}_luc", datetime.now())
    t.qt_trang_thai = SAU_KHI_KY[buoc]
    t.qt_tra_lai_ly_do = ""
    db.flush()
    return {"trang_thai": t.qt_trang_thai, "ten_trang_thai": QT_TRANG_THAI[t.qt_trang_thai]}


def tra_lai(db: Session, t: Trip, ly_do: str, boi: str) -> dict:
    """Trả tờ về cho Đội xe sửa. BẮT BUỘC có lý do, và XOÁ HẾT chữ ký đã có.

    Giữ lại chữ ký cũ thì tờ sửa xong vẫn mang chữ ký của người đã ký bản TRƯỚC khi sửa — tức là
    một chữ ký cho một nội dung người ấy chưa từng đọc. Cùng luật với `nhan_lenh.xoa_dau_nhan`.
    """
    if not (ly_do or "").strip():
        raise ValueError("Trả lại phải ghi lý do — người sửa cần biết sửa cái gì.")
    for b in QT_BUOC:
        setattr(t, f"qt_{b}", "")
        setattr(t, f"qt_{b}_luc", None)
    t.qt_trang_thai = "tra_lai"
    t.qt_tra_lai_ly_do = f"{ly_do.strip()[:280]} (bởi {boi})"[:300]
    db.flush()
    return {"trang_thai": t.qt_trang_thai, "ly_do": t.qt_tra_lai_ly_do}


def gui_di(db: Session, t: Trip, boi: str) -> dict:
    """Đội xe nhập xong, gửi vào tuyến ký."""
    if t.qt_trang_thai not in ("nhap", "tra_lai"):
        raise ValueError(f"Tờ này đang ở '{QT_TRANG_THAI.get(t.qt_trang_thai or '', '?')}'.")
    do = [x for x in kiem(db, t) if x["muc"] == "do"]
    if do:
        raise ValueError("Còn điểm chặn chưa xử: " + " · ".join(x["noi"] for x in do))
    t.qt_trang_thai = "cho_dieu_hanh"
    t.qt_nhap_boi = boi[:50]
    t.qt_nhap_luc = datetime.now()
    t.qt_tra_lai_ly_do = ""
    db.flush()
    return {"trang_thai": t.qt_trang_thai, "ten_trang_thai": QT_TRANG_THAI[t.qt_trang_thai]}


def xem(db: Session, t: Trip) -> dict:
    """Một tờ quyết toán, đúng thứ tự Mẫu 2 — để màn hình chỉ việc in ra."""
    from app.models.hr import Vehicle
    v = db.get(Vehicle, t.vehicle_id) if t.vehicle_id else None
    g = tong(db, t)
    return {
        "id": t.id, "ma_phieu": t.ma_phieu,
        "bien_so": v.plate if v else "", "ma_xe": v.code if v else "",
        "ten_tour": t.ten_tour, "hdv": t.hdv or "", "hanh_trinh": t.hanh_trinh or "",
        "ngay_di": t.ngay_di, "ngay_ve": t.ngay_ve,
        "so_ngay": ((t.ngay_ve - t.ngay_di).days + 1) if (t.ngay_di and t.ngay_ve) else None,
        "km_dau": t.km_dau, "km_cuoi": t.km_cuoi, "km_tour": km_tour(t),
        "tam_ung": t.tam_ung, "hoan_tra": t.hoan_tra, "chi_them": t.chi_them,
        "phu_thu": t.phu_thu, "bc_tinh_trang_xe": t.bc_tinh_trang_xe or "",
        "tong": g,
        "tra_bang_danh_muc": TRA_BANG,
        # Danh sach khoan chi KEM O KHAI `tra_bang`. Khong co o nay thi loi chan "chua khai ai tra"
        # la mot ngo cut: nguoi doc duoc bao phai khai, ma khong co cho nao de khai.
        "chi_phi": [{"id": c.id, "kind": c.kind, "kind_ten": COST_KINDS.get(c.kind, c.kind),
                     "amount": c.amount, "lit": c.lit, "chung_tu": c.chung_tu or "",
                     "tra_bang": c.tra_bang or "",
                     "tra_bang_ten": TRA_BANG.get(c.tra_bang or "", "")}
                    for c in db.execute(select(TripCost)
                                        .where(TripCost.trip_id == t.id)
                                        .order_by(TripCost.id)).scalars().all()],
        "qt_trang_thai": t.qt_trang_thai or "nhap",
        "qt_ten_trang_thai": QT_TRANG_THAI.get(t.qt_trang_thai or "nhap", ""),
        "qt_tra_lai_ly_do": t.qt_tra_lai_ly_do or "",
        "ky": [{"buoc": b, "nguoi": getattr(t, f"qt_{b}") or "",
                "luc": getattr(t, f"qt_{b}_luc")} for b in QT_BUOC],
        "diem_lech": kiem(db, t),
    }
