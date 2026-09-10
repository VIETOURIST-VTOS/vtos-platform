"""Lãi lỗ theo tour và theo khách. Chuẩn phép tính chốt ngày 09/9/2026.

Vì sao có tệp này, và vì sao nó phải là chỗ DUY NHẤT tính lãi lỗ tour:

Khảo sát 09/9/2026 tìm ra VTOS đang có BỐN công thức lãi lỗ tour, nằm ở bốn tệp khác nhau, đều đang
chạy, đều có màn hình gọi tới, và không cho cùng một con số:

  A  rules.calc               - kế hoạch: giá bán x số khách - (chi phí cố định + chi phí theo khách x số khách)
  B  rules.settlement_summary - quyết toán tổng: tours.actual_revenue - (actual_cost + promo_value)
  C  settlement.summary       - quyết toán chi tiết: tổng booking - tổng dòng chi phí - promo_value
  D  books.project_summary    - sổ cái theo mã công trình

Chúng tồn tại song song vì chưa ai chốt định nghĩa. Hậu quả: hai người mở hai màn hình đọc ra hai con
số lợi nhuận cho cùng một tour, và cả hai đều "đúng" theo công thức của mình. Đó là kiểu sai không sửa
được bằng cách kiểm tra số liệu, vì bản thân số liệu không sai - định nghĩa mới sai.

Chủ tịch chốt 09/9/2026: lấy C làm chuẩn. Đo trên hệ thống thật cho thấy đó cũng là nguồn giàu nhất -
dòng chi phí quyết toán đã có số thực chi ở 92%, trong khi giá vốn tổng của tour rỗng 55,5% và giá vốn
theo booking rỗng 100%.

CHUẨN PHÉP TÍNH (mọi màn hình phải gọi vào đây, không tự cộng lại):

    doanh thu  = tổng (booking.amount - booking.discount) của booking CHƯA HUỶ
                 + tổng booking.cancel_charge của booking ĐÃ HUỶ      (phí huỷ giữ lại là doanh thu)
    giá vốn    = tổng tour_cost_lines.actual (dòng còn hiệu lực) + tours.promo_value
    lợi nhuận  = doanh thu - giá vốn
    số khách   = tổng booking.pax của booking chưa huỷ                (khách ĐÃ ĐẶT, không phải dự toán)
    biên       = lợi nhuận / doanh thu; doanh thu bằng 0 thì RỖNG, không phải 0%

Ba quy tắc đi kèm, mỗi quy tắc chống một kiểu sai đã gặp thật:

  * Giá trị khuyến mãi là GIÁ VỐN, không phải giảm trừ doanh thu (ĐC Điều 3). Bỏ sót là thổi lợi nhuận
    lên. Đây là lỗi dễ mắc nhất vì cột ấy rỗng ở 99,9% tour nên không ai để ý.
  * Booking đã huỷ không tính doanh thu, nhưng phí huỷ giữ lại thì CÓ. Bỏ cả hai là mất doanh thu thật.
  * Thiếu số thì để RỖNG, không thay bằng 0. Một tour chưa quyết toán phải hiện ô trống ở cột giá vốn,
    không được hiện "0" rồi báo lợi nhuận bằng đúng doanh thu.

VÀ MỘT ĐIỀU KHÔNG ĐƯỢC QUÊN: tổng ở chân bảng chỉ cộng những dòng ĐÃ CÓ GIÁ VỐN. Cộng cả dòng chưa có
giá vốn vào là tạo ra một con số lãi giả - đúng kiểu sai mà cả làn Kiểm soát sinh ra để chặn.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.core import Booking, Tour
from app.models.suppliers import Supplier
from app.models.vietrip import TourCostLine

# Nhãn nguồn số của từng dòng. Bảng không được trình bày như thể mọi dòng đều tin được như nhau.
NGUON = {
    "quyet_toan_chi_tiet": "Quyết toán chi tiết – có dòng chi phí, tin được",
    "quyet_toan_tong": "Quyết toán tổng – chỉ có giá vốn tổng, không soi được từng khoản",
    "thieu_gia_von": "Có doanh thu, CHƯA có giá vốn – không cộng vào tổng",
    "chua_co_so": "Chưa có cả doanh thu lẫn giá vốn",
}

RONG = {"doanh_thu_bk": 0.0, "da_thu": 0.0, "khach": 0, "so_booking": 0, "phi_huy": 0.0, "so_huy": 0}
RONG_CP = {"gia_von_dong": 0.0, "da_tra": 0.0, "so_dong_cp": 0, "thieu_hoa_don": 0}


def _khung(tu: date | None, den: date | None, loai: str, trang_thai: str):
    """Khung lọc dùng chung cho mọi truy vấn, để các con số luôn nói về cùng một tập tour."""
    q = select(Tour.id)
    if tu:
        q = q.where(Tour.start_date >= tu)
    if den:
        q = q.where(Tour.start_date <= den)
    if loai == "le":
        q = q.where(Tour.tour_type == "non_package")
    elif loai == "ghep":
        q = q.where(Tour.tour_type != "non_package")
    if trang_thai:
        q = q.where(Tour.status.in_([x for x in trang_thai.split(",") if x]))
    return q


def _gom_booking(db: Session, ids):
    """Doanh thu và số khách của từng tour - MỘT truy vấn gộp cho toàn bộ danh sách.

    Không dùng vòng lặp gọi từng tour: cửa danh sách tour hiện tại dựng lại toàn bộ khối tính toán cho
    TỪNG tour, và đo thật thì 1.000 dòng mất hơn một phút trên máy chủ 0,5 CPU. Một báo cáo mà người
    dùng phải chờ một phút là một báo cáo không ai mở.
    """
    chua_huy = select(
        Booking.tour_id.label("tid"),
        func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)), 0).label("dt"),
        func.coalesce(func.sum(func.coalesce(Booking.paid, 0)), 0).label("da_thu"),
        func.coalesce(func.sum(Booking.pax), 0).label("khach"),
        func.count(Booking.id).label("so_bk"),
    ).where(Booking.cancelled == False, Booking.tour_id.in_(ids)).group_by(Booking.tour_id)  # noqa: E712

    # Phí huỷ giữ lại LÀ doanh thu. Đếm riêng vì nó nằm ở nhóm booking đã huỷ - gộp chung điều kiện là
    # hoặc mất khoản này, hoặc vô tình cộng cả tiền booking của khách đã huỷ.
    da_huy = select(
        Booking.tour_id.label("tid"),
        func.coalesce(func.sum(func.coalesce(Booking.cancel_charge, 0)), 0).label("phi_huy"),
        func.count(Booking.id).label("so_huy"),
    ).where(Booking.cancelled == True, Booking.tour_id.in_(ids)).group_by(Booking.tour_id)  # noqa: E712

    ra = {}
    for r in db.execute(chua_huy).all():
        ra[r.tid] = {"doanh_thu_bk": float(r.dt or 0), "da_thu": float(r.da_thu or 0),
                     "khach": int(r.khach or 0), "so_booking": int(r.so_bk or 0),
                     "phi_huy": 0.0, "so_huy": 0}
    for r in db.execute(da_huy).all():
        d = ra.setdefault(r.tid, dict(RONG))
        d["phi_huy"] = float(r.phi_huy or 0)
        d["so_huy"] = int(r.so_huy or 0)
    return ra


def _gom_chi_phi(db: Session, ids):
    """Giá vốn và đã trả nhà cung cấp của từng tour - một truy vấn gộp, chỉ lấy dòng còn hiệu lực."""
    q = select(
        TourCostLine.tour_id.label("tid"),
        func.coalesce(func.sum(func.coalesce(TourCostLine.actual, 0)), 0).label("gv"),
        func.coalesce(func.sum(func.coalesce(TourCostLine.paid, 0)), 0).label("da_tra"),
        func.count(TourCostLine.id).label("so_dong"),
        func.coalesce(func.sum(case((TourCostLine.so_hoa_don.is_(None), 1), else_=0)), 0).label("thieu_hd"),
    ).where(TourCostLine.status == "hd", TourCostLine.tour_id.in_(ids)).group_by(TourCostLine.tour_id)
    return {r.tid: {"gia_von_dong": float(r.gv or 0), "da_tra": float(r.da_tra or 0),
                    "so_dong_cp": int(r.so_dong or 0), "thieu_hoa_don": int(r.thieu_hd or 0)}
            for r in db.execute(q).all()}


def _mot_dong(t: Tour, bk: dict, cp: dict) -> dict:
    """Ráp một dòng báo cáo theo đúng chuẩn phép tính. Không phép tính nào khác được phép ở nơi khác."""
    doanh_thu = bk["doanh_thu_bk"] + bk["phi_huy"]
    co_dong_cp = cp["so_dong_cp"] > 0
    khuyen_mai = float(t.promo_value or 0)

    # Giá vốn: ưu tiên dòng chi phí (nguồn giàu nhất), lùi về giá vốn tổng nếu chưa có dòng nào.
    # KHÔNG lùi về 0 - rỗng và 0 là hai chuyện khác nhau, và đó là toàn bộ điều đợt K2 dựng ra để giữ.
    if co_dong_cp:
        gia_von = cp["gia_von_dong"] + khuyen_mai
        nguon = "quyet_toan_chi_tiet"
    elif t.actual_cost is not None and float(t.actual_cost) != 0:
        gia_von = float(t.actual_cost) + khuyen_mai  # k2-doc-an-toan: dong tren da chan actual_cost is None
        nguon = "quyet_toan_tong"
    else:
        gia_von = None
        nguon = "thieu_gia_von" if doanh_thu else "chua_co_so"

    loi_nhuan = None if gia_von is None else doanh_thu - gia_von
    co_bk = bool(bk["so_booking"] or bk["so_huy"])
    return {
        "tour_id": t.id, "ma_tour": t.code, "ten_tour": t.name,
        # Giá bán NIÊM YẾT của chương trình, không phải doanh thu chia đầu khách. Hai số này khác
        # nhau và khác một cách có ý nghĩa: chênh giữa chúng là phụ thu, khuyến mãi và charge huỷ.
        # Rỗng khi tour chưa khai giá – không thay bằng doanh thu/số khách, vì đó là một con số
        # không có trong bảng giá nào và không ai đối chiếu được.
        "gia_ban": (float(t.price_per_pax) if getattr(t, "price_per_pax", None) is not None
                    else None),
        "ngay_khoi_hanh": t.start_date, "ngay_ket_thuc": t.end_date,
        "loai": "dich_vu_le" if t.tour_type == "non_package" else "tour_ghep",
        "trang_thai": t.status,
        "so_khach": bk["khach"], "so_booking": bk["so_booking"], "so_booking_huy": bk["so_huy"],
        "doanh_thu": doanh_thu if co_bk else None,
        "gia_von": gia_von, "khuyen_mai": khuyen_mai or None,
        "loi_nhuan": loi_nhuan,
        # Biên rỗng khi doanh thu bằng 0. Hiện "0%" ở đó là nói dối: không có doanh thu thì không có
        # biên nào cả, chứ không phải biên bằng không.
        "bien": (loi_nhuan / doanh_thu) if (loi_nhuan is not None and doanh_thu) else None,
        "da_thu": bk["da_thu"] if co_bk else None,
        "con_phai_thu": max(0.0, doanh_thu - bk["da_thu"]) if doanh_thu else None,
        "da_tra_ncc": cp["da_tra"] if co_dong_cp else None,
        "con_phai_tra": max(0.0, cp["gia_von_dong"] - cp["da_tra"]) if co_dong_cp else None,
        "so_dong_chi_phi": cp["so_dong_cp"],
        "thieu_hoa_don": cp["thieu_hoa_don"] if co_dong_cp else None,
        "nguon_so": nguon, "nguon_so_ten": NGUON[nguon],
    }


def bang(db: Session, u=None, tu: date | None = None, den: date | None = None,
         loai: str = "ghep", trang_thai: str = "", gioi_han: int = 200, bo_qua: int = 0) -> dict:
    """Lớp 1 - bảng lãi lỗ theo tour, có phân trang THẬT.

    Cửa danh sách tour hiện tại chặn cứng ở 1.000 bản ghi mà không nói gì, trong khi cơ sở dữ liệu có
    1.258 tour - báo cáo dựng trên đó bị cụt mà không báo lỗi. Ở đây trả về `tong` thật và `con_nua`
    để màn hình biết mình đang xem một phần.
    """
    from app.services import pham_vi_phap_nhan as PV

    khung = _khung(tu, den, loai, trang_thai)
    if u is not None:
        khung = PV.loc(khung, Tour, u)
    tong = db.execute(select(func.count()).select_from(khung.subquery())).scalar_one()

    q = select(Tour).where(Tour.id.in_(khung)).order_by(Tour.start_date.desc(), Tour.id.desc())
    tours = list(db.execute(q.offset(bo_qua).limit(min(gioi_han, 1000))).scalars())
    ids = [t.id for t in tours]
    if not ids:
        return {"rows": [], "tong": tong, "con_nua": False, "cong": _cong([]), "canh_bao": []}

    bk, cp = _gom_booking(db, ids), _gom_chi_phi(db, ids)
    rows = [_mot_dong(t, bk.get(t.id, dict(RONG)), cp.get(t.id, dict(RONG_CP))) for t in tours]
    # Số thứ tự tính TỪ ĐẦU BẢNG chứ không từ đầu trang: trang 3 phải bắt đầu ở 401, không phải ở 1.
    # Để màn hình tự đánh số thì mỗi trang lại đánh lại từ 1, và người đọc tưởng bảng chỉ có 200 dòng.
    for i, r in enumerate(rows, start=bo_qua + 1):
        r["stt"] = i
    return {"rows": rows, "tong": tong, "con_nua": bo_qua + len(rows) < tong,
            "cong": _cong(rows), "canh_bao": _canh_bao(rows)}


def _cong(rows: list) -> dict:
    """Cộng CHỈ những dòng đã có giá vốn.

    Cộng cả dòng chưa có giá vốn vào là báo lãi bằng đúng doanh thu của những tour ấy - một con số lãi
    giả, và giả theo hướng dễ chịu, nên càng ít người đi kiểm. `so_dong_bo_qua` để người đọc biết ngay
    tổng này bỏ ra bao nhiêu dòng, thay vì phải tự trừ.
    """
    du = [r for r in rows if r["loi_nhuan"] is not None]
    dt = sum(r["doanh_thu"] or 0 for r in du)
    gv = sum(r["gia_von"] or 0 for r in du)
    return {"so_dong_tinh": len(du), "so_dong_bo_qua": len(rows) - len(du),
            "doanh_thu": dt, "gia_von": gv, "loi_nhuan": dt - gv,
            "bien": (dt - gv) / dt if dt else None,
            "ghi_chu": "Tổng chỉ cộng những tour đã có giá vốn. Tour chưa quyết toán không được tính "
                       "vào, vì cộng vào là báo lãi bằng đúng doanh thu."}


def _canh_bao(rows: list) -> list:
    """Ba dòng chất lượng, đặt ở ĐẦU bảng chứ không giấu ở cuối.

    Chủ tịch đã nói rõ số liệu hiện chưa đủ và chưa chính xác. Một bảng không nói ra điều đó sẽ được
    đọc như thể mọi dòng đều tin được như nhau - và người đọc sẽ ra quyết định trên phần không tin được.
    """
    ra = []
    thieu_gv = [r for r in rows if r["nguon_so"] == "thieu_gia_von"]
    if thieu_gv:
        ra.append({"loai": "thieu_gia_von", "muc": "do", "so_dong": len(thieu_gv),
                   "tom_tat": f"{len(thieu_gv)} tour có doanh thu nhưng chưa có giá vốn",
                   "chi_tiet": "Không được cộng vào tổng lợi nhuận. Hàng đợi xử lý nằm ở phân hệ Kiểm "
                               "soát, mục 'Có doanh thu, chưa có giá vốn'.",
                   "ma_tour": [r["ma_tour"] for r in thieu_gv[:20]]})
    ket_thuc_0 = [r for r in rows if r["trang_thai"] == "ket_thuc" and not r["so_khach"]]
    if ket_thuc_0:
        ra.append({"loai": "ket_thuc_khong_khach", "muc": "vang", "so_dong": len(ket_thuc_0),
                   "tom_tat": f"{len(ket_thuc_0)} tour đã kết thúc mà số khách bằng 0",
                   "chi_tiet": "Hoặc chưa nhập booking, hoặc tour không chạy. Hai chuyện này khác nhau "
                               "và cần người xác nhận, máy không suy ra được.",
                   "ma_tour": [r["ma_tour"] for r in ket_thuc_0[:20]]})
    thieu_hd = [r for r in rows if r["thieu_hoa_don"]]
    if thieu_hd:
        ra.append({"loai": "thieu_hoa_don", "muc": "vang", "so_dong": len(thieu_hd),
                   "tom_tat": f"{len(thieu_hd)} tour có dòng chi phí chưa nhập số hoá đơn",
                   "chi_tiet": "Không có số hoá đơn thì không đối chiếu được với tờ khai thuế, và khoản "
                               "chi ấy chưa chứng minh được là có chứng từ hợp lệ.",
                   "ma_tour": [r["ma_tour"] for r in thieu_hd[:20]]})
    return ra


def chi_tiet(db: Session, t: Tour) -> dict:
    """Lớp 2 - mở một tour ra: danh sách KHÁCH và danh sách CHI PHÍ theo nhà cung cấp.

    Chủ tịch chốt 09/9/2026: lớp 2 phải có cả hai phía. Phía khách để biết tiền vào từ ai; phía nhà
    cung cấp để biết tiền ra đi đâu, kèm mã số thuế, địa chỉ và SỐ HOÁ ĐƠN - ba thứ cần khi đối chiếu
    thuế, mà bảng quyết toán cũ không có chỗ ghi.

    Cột giá vốn theo TỪNG KHÁCH cố ý KHÔNG có với tour ghép: chi phí xe, khách sạn, hướng dẫn viên ghi
    ở mức chuyến, không ai ghi "khách A tốn bao nhiêu". Chia đều ra rồi gọi là giá vốn của khách là
    biến một phép phân bổ thành một sự thật - và nếu một khách được giảm giá sâu thì phép chia ấy sẽ
    báo khách đó "lỗ" trong khi chuyến vẫn lãi. Dịch vụ lẻ thì khác: một booking là một dịch vụ có nhà
    cung cấp riêng, nên ở đó giá vốn theo khách là số thật.
    """
    le = t.tour_type == "non_package"
    khach = []
    for b in sorted(t.bookings, key=lambda x: (x.cancelled, x.code or "")):
        dt = (float(b.amount or 0) - float(b.discount or 0)) if not b.cancelled else float(b.cancel_charge or 0)
        khach.append({
            "booking_id": b.id, "ma_booking": b.code,
            "ten_khach": b.customer_name, "dien_thoai": b.customer_phone, "email": b.customer_email or None,
            "so_khach": b.pax, "nguoi_lon": b.adl, "tre_em": b.chd, "em_be": b.inf,
            "doanh_thu": dt if (b.amount is not None or b.cancelled) else None,
            "giam_gia": float(b.discount) if b.discount is not None else None,
            "da_thu": float(b.paid) if b.paid is not None else None,
            "con_phai_thu": max(0.0, dt - float(b.paid or 0)) if b.amount is not None else None,
            "trang_thai_thu": b.pmt_status or None,
            "da_huy": b.cancelled, "phi_huy_giu_lai": float(b.cancel_charge) if (b.cancelled and b.cancel_charge is not None) else None,
            "sale_id": b.sales_id,
            # Chỉ dịch vụ lẻ mới có giá vốn theo khách, và chỉ khi có người nhập.
            "gia_von_khach": (float(b.cost_amount) if (le and b.cost_amount is not None) else None),
            "ncc_khach": (b.supplier_name or None) if le else None,
        })

    q = select(TourCostLine).where(TourCostLine.tour_id == t.id).order_by(TourCostLine.line_no, TourCostLine.id)
    dong = list(db.execute(q).scalars())
    ncc_id = {l.supplier_id for l in dong if l.supplier_id}
    ho_so = {}
    if ncc_id:
        ho_so = {s.id: s for s in db.execute(select(Supplier).where(Supplier.id.in_(ncc_id))).scalars()}

    chi_phi = []
    for l in dong:
        s = ho_so.get(l.supplier_id)
        chi_phi.append({
            "line_id": l.id, "dong_so": l.line_no, "mo_ta": l.description,
            "loai_dich_vu": l.service_type or None, "loai_chi_phi": l.cost_kind,
            "ncc": l.supplier_name or (s.ten if s else None) or None,
            "ma_so_thue": l.supplier_tax_code or (s.ma_so_thue if s else None) or None,
            "dia_chi": (s.dia_chi or None) if s else None,
            "so_hoa_don": l.so_hoa_don,
            "ngay_hoa_don": l.ngay_hoa_don,
            "vat_hoa_don": float(l.vat_hoa_don) if l.vat_hoa_don is not None else None,
            "don_gia": float(l.unit_price) if l.unit_price is not None else None,
            "so_luong": l.qty, "he_so": l.coef,
            "thuc_chi": float(l.actual) if l.actual is not None else None,
            "da_tra": float(l.paid) if l.paid is not None else None,
            "con_phai_tra": (max(0.0, float(l.actual or 0) - float(l.paid or 0)) if l.actual is not None else None),
            "co_chung_tu": bool(l.doc_name), "trang_thai": l.status, "ghi_chu": l.note or None,
        })

    bk = _gom_booking(db, [t.id]).get(t.id, dict(RONG))
    cp = _gom_chi_phi(db, [t.id]).get(t.id, dict(RONG_CP))
    return {"tong_hop": _mot_dong(t, bk, cp), "khach": khach, "chi_phi": chi_phi,
            "quyet_toan_dieu_hanh": _ban_quyet_toan(db, t),
            "co_gia_von_theo_khach": le,
            "vi_sao_khong_co_gia_von_theo_khach": None if le else
                "Chi phí của tour ghép ghi ở mức chuyến (xe, khách sạn, hướng dẫn viên), không tách "
                "được theo từng khách. Chia đều ra là phép phân bổ, không phải số thật."}


# ---------------------------------------------------------------------------------------------
# Lớp 2, phần đến từ TỆP QUYẾT TOÁN của Điều hành
# ---------------------------------------------------------------------------------------------

def _ban_quyet_toan(db: Session, t) -> dict | None:
    """Bốn mặt của bản quyết toán Điều hành, nếu chuyến này đã nạp tệp chi tiết.

    Vì sao gắn vào ĐÂY chứ không dựng màn hình quyết toán riêng: tệp lai_lo_tour.py này sinh ra ngày
    09/9 vì VTOS lúc ấy có BỐN công thức lãi lỗ tour chạy song song cho ra bốn con số. Dựng thêm một
    màn hình quyết toán hai lớp nữa là tạo công thức thứ năm, và lần này còn khó thấy hơn vì hai màn
    hình sẽ trông giống hệt nhau.

    Nên bốn mặt ấy là DỮ LIỆU BỔ SUNG của lớp 2 sẵn có, không phải một lối tính khác. Số tổng của
    chuyến vẫn do chuẩn phép tính ở đầu tệp này quyết; bản quyết toán chỉ nói thêm "số ấy đến từ đâu"
    và "chỗ nào trong tệp gốc không khớp nhau".

    Trả None khi chưa nạp tệp – rỗng nghĩa là CHƯA CÓ, khác hẳn với đã nạp mà không có dòng nào.
    """
    from app.models.quyet_toan import (TourSettlement, TourSettlementLine, TourSettlementCost,
                                       TourSettlementCostLine, TourGuideAdvance,
                                       TourSettlementBooking, TEN_KHOAN)
    s = db.execute(select(TourSettlement).where(TourSettlement.ma_tour == t.code)).scalars().first()
    if s is None or s.nguon != "nap_tep_chi_tiet":
        return None

    dong = db.execute(select(TourSettlementLine)
                      .where(TourSettlementLine.settlement_id == s.id)
                      .order_by(TourSettlementLine.stt)).scalars().all()
    khoan = {}
    if dong:
        for k in db.execute(select(TourSettlementCost).where(
                TourSettlementCost.line_id.in_([x.id for x in dong]))).scalars():
            khoan.setdefault(k.line_id, []).append(
                {"ma_khoan": k.ma_khoan, "ten_khoan": TEN_KHOAN.get(k.ma_khoan, k.ma_khoan),
                 "nhan": k.nhan, "so_tien": float(k.so_tien) if k.so_tien is not None else None})
    ct = db.execute(select(TourSettlementCostLine)
                    .where(TourSettlementCostLine.settlement_id == s.id)
                    .order_by(TourSettlementCostLine.id)).scalars().all()
    hdv = db.execute(select(TourGuideAdvance)
                     .where(TourGuideAdvance.settlement_id == s.id)).scalars().all()
    bkg = db.execute(select(TourSettlementBooking)
                     .where(TourSettlementBooking.settlement_id == s.id)).scalars().all()
    f = lambda v: (float(v) if v is not None else None)
    return {
        "ma_tour": s.ma_tour, "ten_chuong_trinh": s.ten_chuong_trinh,
        "so_khach_tep_ghi": s.so_khach, "so_dong_khach": len(dong),
        "hdv": s.hdv, "bien_so_xe": s.bien_so_xe,
        "gia_ban": f(s.gia_ban), "nhieu_muc_gia": bool(s.nhieu_muc_gia),
        # Chênh giữa lớp 1 và tổng lớp 2. Ghi 0 khi đã đối chiếu và khớp – "đã đối chiếu, khớp" khác
        # với "chưa đối chiếu bao giờ", và một ô rỗng không phân biệt được hai chuyện đó.
        "chenh_thu": f(s.chenh_thu), "chenh_chi": f(s.chenh_chi),
        "ten_tep": s.ten_tep, "nap_boi": s.boi, "nap_luc": s.luc,
        "phat_hien": [x for x in (s.ghi_chu or "").split(" | ") if x],
        "khach": [{"stt": x.stt, "sales": x.sales, "ten_khach": x.ten_khach,
                   "gia_ban": f(x.gia_ban), "thu_khac": f(x.thu_khac), "tong_thu": f(x.tong_thu),
                   "tong_chi": f(x.tong_chi), "loi_nhuan": f(x.loi_nhuan_tep),
                   "khoan_chi": khoan.get(x.id, []), "co_lech": x.co_lech or None}
                  for x in dong],
        "chiet_tinh": [{"ve": x.ve, "nhom": x.nhom, "noi_dung": x.noi_dung, "doi_tac": x.doi_tac,
                        "don_gia": f(x.don_gia), "so_luong": x.so_luong, "he_so": x.he_so,
                        "thanh_tien": f(x.thanh_tien), "so_chung_tu": x.so_chung_tu or None,
                        "mst_ncc": x.mst_ncc or None, "co_lech": x.co_lech or None}
                       for x in ct],
        "hdv_chi": [{"noi_dung": x.noi_dung, "don_gia": f(x.don_gia), "so_luong": x.so_luong,
                     "tong_chi": f(x.tong_chi), "ghi_chu": x.ghi_chu or None,
                     "tien_ung": f(x.tien_ung), "du": f(x.du), "ctp": f(x.ctp),
                     "la_dong_tong": bool(x.la_dong_tong)} for x in hdv],
        "booking": [{"ma_booking_nguon": x.ma_booking_nguon, "booking_id": x.booking_id,
                     "ten_nguoi_book": x.ten_nguoi_book, "dien_thoai": x.dien_thoai,
                     "so_khach": x.so_khach, "tong_thu": f(x.tong_thu), "da_dong": f(x.da_dong),
                     "con_phai_thu": f(x.con_phai_thu()), "nguoi_ban": x.nguoi_ban}
                    for x in bkg],
        # Đếm sẵn để màn hình không phải tự cộng – mọi chỗ tự cộng lại là một công thức song song nữa.
        "so_chung_tu_co_mst": sum(1 for x in ct if x.mst_ncc),
        "so_dong_chi_co_chung_tu": sum(1 for x in ct if x.ve == "chi" and x.so_chung_tu),
        "so_dong_chi": sum(1 for x in ct if x.ve == "chi"),
    }
