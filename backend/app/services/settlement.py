"""Quyết toán tour soạn trên VTOS (theo bố cục bảng quyết toán Vietrip):
dòng chi phí theo NCC (mô tả, loại DV, NCC–MST, cách tính, đơn giá, SL, hệ số, dự toán, thực chi, đã thanh toán, chứng từ),
kiểm tra nhập theo dòng, phiên bản V.01/V.02, khớp 'đã thanh toán' với lệnh chi NCC / tạm ứng, so dự toán – thực chi, chấm thiếu chứng từ."""
from datetime import date, datetime
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Tour
from app.models.vietrip import TourCostLine
from app.models.ops import PaymentRequest
from app.services import rules as R
from app.services import chu_ho_so as CHS
from app.services import ngoai_te_chi as NT
from app.services.vietrip import _strip_accents
from app.api.deps import toan_quyen, toan_quyen_ke_ca_tach_bach   # Chủ tịch toàn quyền – MỘT luật, xem deps.toan_quyen


def _norm(s: str) -> str:
    return " ".join(_strip_accents((s or "").upper()).split())[:80]

SERVICE_TYPES = {"GUIDE": "Hướng dẫn viên", "HOTEL": "Khách sạn", "RESTAURANT": "Nhà hàng", "LAND": "Tham quan / landtour", "VEHICLE": "Xe", "FLIGHT": "Vé máy bay",
                 "INSURANCE": "Bảo hiểm", "TICKET": "Vé tàu / vé tham quan", "VISA": "Visa", "GIFT": "Quà tặng / nón / nước", "OTHER": "Khác"}
COST_KINDS = ("co_dinh", "theo_khach")
EDITABLE = ("da_duyet", "ket_thuc")          # Điều hành soạn quyết toán cho tới khi đóng số; Kế toán trả lại → quay về ket_thuc
MAX_DOC = 1_500_000 * 4 // 3                 # ~1,5 MB nhị phân dưới dạng data URL


class Gate(HTTPException):
    def __init__(self, code: str, msg: str): super().__init__(422, {"gate": code, "message": msg})


def calc_actual(kind: str, unit_price: float, qty: float, coef: float, ndigits: int | None = None) -> float:
    """Theo khách: đơn giá × số khách × hệ số. Cố định: đơn giá × hệ số (SL chỉ để ghi nhận số khách).

    `ndigits=None` (mặc định) làm tròn về ĐỒNG – đúng cho tiền Việt: đồng Việt Nam không có đơn vị
    nhỏ hơn đồng. Truyền `ndigits=2` khi `unit_price` là ĐƠN GIÁ NGOẠI TỆ: 29.770,62 GBP làm tròn
    về 29.771 là mất 0,62 GBP – một khoản tiền có thật, và nhân tỷ giá lên thành hơn hai chục nghìn
    đồng lệch trên mỗi dòng.

    Ô `ndigits` thêm vào 27/9/2026 chứ không dựng một hàm nhân thứ hai cho ngoại tệ: LUẬT PHÉP NHÂN
    (`theo_khach` nhân số khách, `co_dinh` không) phải nằm đúng MỘT chỗ. Hai bản chép của một phép
    tính thì sớm muộn lệch nhau – đã trả hơn một tỷ đồng để học điều đó ngày 27/9/2026.
    """
    tich = unit_price * qty * coef if kind == "theo_khach" else unit_price * coef
    return round(tich) if ndigits is None else round(tich, ndigits)


def tong_ngoai_te(l: TourCostLine) -> float:
    """Tổng nghĩa vụ của MỘT dòng giá vốn, tính bằng ĐỒNG GỐC (không quy đổi).

    Dùng để khớp lệnh chi ngoại tệ theo đồng gốc: nhà cung cấp hết nợ khi nhận đủ số ngoại tệ này,
    bất kể mình mua ngoại tệ ấy giá nào. Gọi CHÍNH `calc_actual` – xem lý do ở hàm trên.
    """
    return calc_actual(l.cost_kind or "co_dinh", float(l.so_tien_goc or 0),
                       float(l.qty or 0), float(l.coef or 1), 2)


def can_edit(db: Session, u: User, t: Tour) -> bool:
    return CHS.la_chu_ho_so(db, u, t) and t.status in EDITABLE


def _assert_edit(db: Session, u: User, t: Tour):
    """Cổng MỘT CHỦ HỒ SƠ (trước 25/9/2026 tên là "Một cửa", khoá cứng vào `operator_id`).

    Vẫn đúng MỘT người, và vẫn KHÔNG CÓ ĐƯỜNG THOÁT THEO VAI TRÒ: Trưởng phòng cũng không nhập hộ.
    Chỗ đổi là người ấy được xác định bằng `chu_ho_so.chu_ho_so()` thay vì bằng cột thưởng chuyến.
    Vì sao đổi: xem đầu tệp `services/chu_ho_so.py`.
    """
    if not CHS.la_chu_ho_so(db, u, t):
        raise Gate("CONG_6", f"Một chủ hồ sơ: chỉ {CHS.ten_chu_ho_so(db, t)} soạn quyết toán chuyến này")
    if t.status not in EDITABLE:
        raise Gate("TRANG_THAI", "Quyết toán đã đóng số / Kế toán đã xác nhận – chỉ sửa khi Kế toán trả lại" if t.status in ("da_dong_so", "kt_xac_nhan", "khoa") else "Tour chưa được duyệt")


def _ngoai_te(d: dict, out: dict) -> None:
    """Bốn ô ngoại tệ của dòng giá vốn — MỞ CỬA cho bốn cột ĐÃ CÓ, 25/9/2026.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    ĐÂY LÀ MỘT CỬA, KHÔNG PHẢI MỘT CỘT MỚI
    ═══════════════════════════════════════════════════════════════════════════════════════════
    `models/vietrip.py:89-92` đã có `tien_te`, `so_tien_goc`, `ty_gia`, `ngay_ty_gia` từ lâu. Chỗ
    thiếu là `validate()` dựng dữ liệu từ một danh sách trường cố định và bốn tên ấy không nằm
    trong danh sách — nên `add_line`/`update_line` không bao giờ ghi chúng.

    Hệ quả đo được trên dữ liệu: chuyến nước ngoài NẠP TỪ KHO CŨ có số gốc và tỷ giá (bộ nạp ghi
    thẳng vào bảng, không đi qua cửa này); chuyến nước ngoài SOẠN MỚI trên VTOS thì không. Hai
    loại chuyến nằm chung một sổ, một loại truy được về đồng gốc, loại kia không — và không có gì
    trên màn hình nói cho người đọc biết mình đang nhìn loại nào.

    Ranh giới Chủ tịch chốt 09/9/2026: mỗi con số cần một cửa nhập; không có cửa thì đó là việc
    còn thiếu, không phải việc để bộ nạp làm hộ.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    BỐN ĐIỀU CỐ Ý
    ═══════════════════════════════════════════════════════════════════════════════════════════
    1. RỖNG NGHĨA LÀ VND, VÀ KHÔNG ĐÒI GÌ THÊM. Tuyệt đại đa số dòng giá vốn là tiền đồng. Bắt cả
       chúng khai `tien_te = "VND"` là thêm một ô bắt buộc cho hàng nghìn dòng để phục vụ vài chục
       dòng — và ô bắt buộc mà ai cũng gõ cùng một giá trị thì chỉ còn là phiền.

    2. KHAI NGOẠI TỆ THÌ PHẢI ĐỦ BA Ô CÒN LẠI. Một số tiền USD không có tỷ giá là một con số không
       quy đổi được; một tỷ giá không có ngày là một con số không kiểm lại được. Thiếu ô nào thì
       từ chối ngay tại cửa, đừng để dòng ấy nằm trong sổ rồi ba tháng sau mới có người hỏi.

    3. `unit_price` (VND) là SỐ SUY RA, người không gõ. Gõ tay cả số gốc, tỷ giá lẫn số VND là mở
       đường cho ba con số không khớp nhau — chính câu `models/ty_gia.py` đã ghi. Máy nhân.

    4. KHÔNG TỰ TRA SỔ TỶ GIÁ. Sổ chỉ ĐIỀN SẴN vào form cho người nhập; máy không chọn hộ. Tỷ giá
       của một khoản là tỷ giá NGÀY CHI THẬT của khoản ấy — một sự thật đã xảy ra, không được sửa
       lùi khi sổ đổi. Luật ấy đã viết trong `models/ty_gia.py`, đây chỉ là chỗ không phá nó.
    """
    tt = (d.get("tien_te") or "").strip().upper()[:3]
    if tt in ("", "VND"):
        # Không ghi đè bằng None: dòng cũ đã có ngoại tệ mà màn hình cũ gửi lên thiếu ô thì sẽ bị
        # xoá trắng. Rỗng ở đây nghĩa là "không đụng tới", đúng cách `tours._dat_hoa_hong_khach`
        # xử lý chuỗi rỗng ngày 24/9.
        return
    goc = float(d.get("so_tien_goc") or 0)
    tg = float(d.get("ty_gia") or 0)
    ngay = d.get("ngay_ty_gia") or ""
    thieu = [ten for ten, ok in (("số tiền bằng đồng gốc", goc > 0),
                                 ("tỷ giá", tg > 0),
                                 ("ngày tỷ giá", bool(str(ngay).strip()))) if not ok]
    if thieu:
        raise Gate("QT_NHAP", f"Khai ngoại tệ {tt} thì phải có: {', '.join(thieu)}. "
                              "Một số tiền ngoại tệ thiếu tỷ giá là con số không quy đổi được; "
                              "một tỷ giá thiếu ngày là con số không kiểm lại được.")
    if isinstance(ngay, str):
        try:
            ngay = date.fromisoformat(ngay[:10])
        except ValueError:
            raise Gate("QT_NHAP", f"Ngày tỷ giá không đọc được: {ngay!r}. Dạng đúng là 2026-09-25.")
    out["tien_te"], out["so_tien_goc"], out["ty_gia"], out["ngay_ty_gia"] = tt, goc, tg, ngay
    out["unit_price"] = round(goc * tg, 2)      # ghi chú 3: máy nhân, người không gõ


def validate(d: dict) -> dict:
    out = {"description": (d.get("description") or "").strip()[:200], "service_type": (d.get("service_type") or "OTHER").upper()[:30], "cost_kind": d.get("cost_kind") or "co_dinh",
           "supplier_name": (d.get("supplier_name") or "").strip()[:200], "supplier_tax_code": (d.get("supplier_tax_code") or "").strip()[:20],
           "unit_price": float(d.get("unit_price") or 0), "qty": float(d.get("qty") or 0), "coef": float(d.get("coef") or 1), "budget": float(d.get("budget") or 0),
           "note": (d.get("note") or "").strip()[:200]}
    _ngoai_te(d, out)     # đặt TRƯỚC các phép kiểm dưới: nó có thể thay `unit_price`
    if not out["description"]: raise Gate("QT_NHAP", "Vui lòng nhập Mô tả chi tiết")
    if out["service_type"] not in SERVICE_TYPES: raise Gate("QT_NHAP", "Loại dịch vụ không hợp lệ")
    if not out["supplier_name"]: raise Gate("QT_NHAP", "Vui lòng nhập Nhà cung cấp")
    if out["cost_kind"] not in COST_KINDS: raise Gate("QT_NHAP", "Vui lòng chọn Cách tính chi (cố định / theo khách)")
    if (out["unit_price"] or 0) < 0: raise Gate("QT_NHAP", "Đơn giá thực tế không được âm")
    if out["coef"] <= 0: raise Gate("QT_NHAP", "Hệ số phải lớn hơn 0")
    if out["cost_kind"] == "theo_khach" and out["qty"] <= 0: raise Gate("QT_NHAP", "Số khách (Pax) phải lớn hơn 0")
    out["actual"] = calc_actual(out["cost_kind"], out["unit_price"], out["qty"], out["coef"])
    if (out["actual"] or 0) < 0: raise Gate("QT_NHAP", "Tổng thực chi không được âm")
    if d.get("paid") is not None: out["paid"] = max(0.0, float(d.get("paid") or 0))
    return out


def lines_of(db: Session, t: Tour, active_only: bool = False) -> list[TourCostLine]:
    q = select(TourCostLine).where(TourCostLine.tour_id == t.id)
    if active_only: q = q.where(TourCostLine.status == "hd")
    return list(db.execute(q.order_by(TourCostLine.line_no, TourCostLine.id)).scalars())


def line_out(l: TourCostLine) -> dict:
    over = ((l.actual or 0) - (l.budget or 0)) / (l.budget or 0) if (l.budget or 0) else 0
    return {"id": l.id, "line_no": l.line_no, "description": l.description, "cost_kind": l.cost_kind, "service_type": l.service_type, "service_name": SERVICE_TYPES.get(l.service_type, l.service_type),
            "supplier_name": l.supplier_name, "supplier_tax_code": l.supplier_tax_code, "unit_price": l.unit_price, "qty": l.qty, "coef": l.coef, "budget": l.budget, "actual": l.actual, "paid": l.paid,
            "remaining": max(0.0, (l.actual or 0) - (l.paid or 0)), "over_pct": over, "note": l.note, "source": l.source, "status": l.status, "version": l.version, "has_doc": bool(l.doc_data), "doc_name": l.doc_name,
            "updated_by": l.updated_by, "updated_at": l.updated_at,
            # Bốn ô ngoại tệ. Trả về CẢ KHI RỖNG, để màn hình phân biệt được "dòng tiền đồng" với
            # "dòng ngoại tệ chưa ai khai" — hai thứ khác nhau, và gộp lại thì không nhìn ra dòng
            # nào là dòng cần đi hỏi.
            "tien_te": l.tien_te, "so_tien_goc": l.so_tien_goc,
            "ty_gia": float(l.ty_gia) if l.ty_gia is not None else None,
            "ngay_ty_gia": l.ngay_ty_gia}


def add_line(db: Session, u: User, t: Tour, d: dict) -> TourCostLine:
    _assert_edit(db, u, t); v = validate(d)
    # Đóng dấu chủ hồ sơ ở LẦN GHI ĐẦU: từ giây này hồ sơ có tên một người, và đổi tham số
    # `chu_ho_so_doan` không lấy đi được nữa. Xem `chu_ho_so.ghi_dau_chu`.
    CHS.ghi_dau_chu(db, t, u.id)
    n = (db.execute(select(func.max(TourCostLine.line_no)).where(TourCostLine.tour_id == t.id)).scalar() or 0) + 1
    l = TourCostLine(tour_id=t.id, line_no=n, source="vtos", version=t.settlement_version, updated_by=u.username, paid=v.pop("paid", 0.0), **v)
    db.add(l); db.flush()
    R.audit(db, u.username, u.role, "qt_them_dong", f"tour:{t.code}", after={"dong": n, "mo_ta": l.description, "ncc": l.supplier_name, "thuc_chi": l.actual, "v": t.settlement_version})
    db.commit(); db.refresh(l); return l


def update_line(db: Session, u: User, t: Tour, l: TourCostLine, d: dict) -> TourCostLine:
    _assert_edit(db, u, t)
    CHS.ghi_dau_chu(db, t, u.id)
    if l.status != "hd": raise Gate("QT_NHAP", "Dòng đã hủy – không sửa")
    from app.services import ghi_mot_lan as GML
    pb = d.pop("phien_ban", None)
    v = validate(d); before = {"thuc_chi": l.actual, "don_gia": l.unit_price, "sl": l.qty, "hs": l.coef, "da_tt": l.paid}
    GML.kiem_phien_ban(l, pb, f"Dòng giá vốn {l.line_no} của {t.code}",
                       lambda: {**before, "phien_ban": l.phien_ban})
    for k, x in v.items(): setattr(l, k, x)
    GML.tang_phien_ban(l)
    l.version, l.updated_by, l.source = t.settlement_version, u.username, "vtos" if l.source != "vietrip" else "vietrip+vtos"
    R.audit(db, u.username, u.role, "qt_sua_dong", f"tour:{t.code}", before=before, after={"dong": l.line_no, "thuc_chi": l.actual, "da_tt": l.paid, "v": t.settlement_version})
    db.commit(); db.refresh(l); return l


def cancel_line(db: Session, u: User, t: Tour, l: TourCostLine, reason: str) -> None:
    _assert_edit(db, u, t)
    CHS.ghi_dau_chu(db, t, u.id)
    if not (reason or "").strip(): raise Gate("QT_NHAP", "Hủy dòng phải có lý do")
    l.status, l.note, l.updated_by, l.version = "huy", (f"[HỦY] {reason.strip()} | " + l.note)[:200], u.username, t.settlement_version
    R.audit(db, u.username, u.role, "qt_huy_dong", f"tour:{t.code}", after={"dong": l.line_no, "mo_ta": l.description, "ly_do": reason.strip()[:120]})
    db.commit()


def set_doc(db: Session, u: User, t: Tour, l: TourCostLine, name: str, data: str) -> None:
    """Gắn chứng từ (ảnh/PDF data URL) cho dòng. Sau đóng số vẫn cho bổ sung chứng từ (không đổi số)."""
    if not CHS.la_chu_ho_so(db, u, t) and u.role not in ("ketoan", "cntt") and not toan_quyen(u): raise Gate("CONG_6", f"Chỉ chủ hồ sơ quyết toán ({CHS.ten_chu_ho_so(db, t)}) hoặc Kế toán gắn chứng từ")
    if t.status in ("kt_xac_nhan", "khoa"): raise Gate("TRANG_THAI", "Tour đã xác nhận/khóa – không thay chứng từ")
    if data and not data.startswith(("data:image/", "data:application/pdf")): raise Gate("QT_NHAP", "Chứng từ phải là ảnh hoặc PDF")
    if len(data) > MAX_DOC: raise Gate("QT_NHAP", "Tệp quá lớn (tối đa ~1,5 MB) – vui lòng nén ảnh")
    l.doc_name, l.doc_data, l.updated_by = (name or "")[:160], data, u.username
    R.audit(db, u.username, u.role, "qt_gan_chung_tu" if data else "qt_go_chung_tu", f"tour:{t.code}", after={"dong": l.line_no, "tep": l.doc_name}); db.commit()


def match_paid(db: Session, t: Tour) -> dict:
    """Khớp cột 'Đã thanh toán' của dòng quyết toán với lệnh chi NCC / tạm ứng đã chi của chuyến.

    Ưu tiên trùng MST, sau đó trùng tên NCC (bỏ dấu); mỗi lệnh chi chỉ dùng một lần, phân bổ tuần
    tự theo thứ tự dòng.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    NGOẠI TỆ: KHỚP THEO ĐỒNG GỐC, CHÊNH TỶ GIÁ ĐỨNG RIÊNG — Chủ tịch chốt 27/9/2026
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Bản cũ so số VND của lệnh chi với số VND của dòng. Hai số ấy dùng HAI TỶ GIÁ khác nhau (tỷ giá
    ngày chuyển tiền ≠ tỷ giá lúc làm quyết toán), nên phần chênh tỷ giá chui vào cột "còn phải trả
    NCC" — hoặc hiện thành "trả thừa". Không ai đọc được chuyến còn nợ NCC thật hay chỉ lệch tỷ giá.

    Luật mới, khi dòng và lệnh chi CÙNG một đồng tiền và cả hai đều có tỷ giá:

        phân bổ theo SỐ NGOẠI TỆ (nhà cung cấp hết nợ khi nhận đủ số ngoại tệ)
        `paid` của dòng = số ngoại tệ đã trả × TỶ GIÁ CỦA DÒNG   → "còn phải trả" về 0 đúng lúc
        chênh tỷ giá   = số ngoại tệ đã trả × (tỷ giá lệnh chi − tỷ giá dòng)   → đứng RIÊNG

    Chênh ấy được ĐO và in ra, KHÔNG sinh bút toán 635/515 (Chủ tịch chọn đo trước, 27/9/2026).

    Khác đồng tiền, hoặc một bên không khai ngoại tệ → rơi về khớp theo VND như cũ VÀ hiện ra ở
    `canh_bao`. Im lặng quy đổi giữa hai đồng tiền khác nhau ở đây là bịa một tỷ giá không ai khai.
    """
    prs = list(db.execute(select(PaymentRequest).where(PaymentRequest.tour_id == t.id, PaymentRequest.status == "da_chi", PaymentRequest.category.in_(["chi_tour", "tam_ung"]))).scalars())
    pool = [{"id": p.id, "code": p.code, "mst": (p.supplier_tax_code or "").strip(), "name": _norm(p.supplier_name),
             "left": p.amount,                                   # còn lại tính bằng VND (đường cũ)
             "tien_te": NT.hoa(p.tien_te), "ty_gia": float(p.ty_gia) if p.ty_gia else None,
             "left_nt": float(p.so_tien_ngoai_te) if p.so_tien_ngoai_te else None,  # còn lại tính bằng ngoại tệ
             "pr": p} for p in prs]
    matched, unmatched = 0, 0
    tong_chenh = 0.0
    chenh_dong: list[dict] = []
    canh_bao: list[str] = []

    for l in lines_of(db, t, active_only=True):
        if l.source == "vietrip" and (l.paid or 0) > 0 and not prs: continue
        mst, name = (l.supplier_tax_code or "").strip(), _norm(l.supplier_name)
        # Tổng nghĩa vụ của dòng tính bằng ĐỒNG GỐC. Bằng 0 nghĩa là dòng khai `tien_te` mà THIẾU
        # `so_tien_goc` – hình của dòng kho cũ và dòng ghi thẳng vào bảng. KHÔNG được đi đường ngoại
        # tệ với dòng ấy: nghĩa vụ 0 thì mọi lần trả đều lấy được 0, và `paid` sẽ bị ghi thành 0 –
        # tức XOÁ con số đã trả đang nằm đó. Rơi về khớp theo VND và hiện ra ở `canh_bao`.
        nt_tong = tong_ngoai_te(l) if NT.la_ngoai_te(l) else 0.0

        def _theo_nt(p, l=l, nt_tong=nt_tong) -> bool:
            return (NT.cung_dong_tien(l, p["pr"]) and nt_tong > NT.DUNG_SAI_NT
                    and (p["left_nt"] or 0) > NT.DUNG_SAI_NT)

        cands = [p for p in pool if ((mst and p["mst"] == mst) or (name and p["name"] == name))
                 and (_theo_nt(p) or p["left"] > 0)]
        paid = 0.0            # nghĩa vụ đã dập, tính bằng VND theo tỷ giá CỦA DÒNG
        chenh_l = 0.0         # chênh tỷ giá của riêng dòng này (dương = lỗ)
        nt_da_tra = 0.0
        # Tỷ giá ĐÃ DÙNG để phân bổ — giữ lại để in ra. In con số đã dùng chứ không đọc lại cột:
        # đọc lại là mở đường cho bảng nói một tỷ giá khác với tỷ giá phép tính thật sự chạy.
        tg_da_dung = 0.0
        for p in cands:
            if _theo_nt(p):
                # ── Cùng đồng tiền: phân bổ theo NGOẠI TỆ ────────────────────────────────────
                tg_dong = float(l.ty_gia)
                con_no_nt = max(0.0, nt_tong - nt_da_tra)
                take_nt = min(p["left_nt"], con_no_nt)
                if take_nt <= NT.DUNG_SAI_NT: continue
                p["left_nt"] -= take_nt
                p["left"] = round(max(0.0, p["left"] - take_nt * float(p["ty_gia"])), 2)
                nt_da_tra += take_nt
                tg_da_dung = tg_dong
                paid += take_nt * tg_dong
                chenh_l += NT.chenh_mot_lan_tra(take_nt, tg_dong, float(p["ty_gia"]))
            else:
                # ── Đường cũ: phân bổ theo VND ───────────────────────────────────────────────
                if NT.la_ngoai_te(l) and NT.hoa(l.tien_te) == p["tien_te"] and nt_tong <= NT.DUNG_SAI_NT:
                    canh_bao.append(
                        f"Dòng {l.line_no} khai {NT.hoa(l.tien_te)} nhưng THIẾU đơn giá đồng gốc – "
                        f"khớp lệnh chi {p['code']} theo số VND; chênh lệch tỷ giá KHÔNG đo được. "
                        "Chủ hồ sơ quyết toán cần gõ lại bốn ô ngoại tệ của dòng này.")
                elif NT.la_ngoai_te(l) != NT.la_ngoai_te(p["pr"]) or (
                        NT.la_ngoai_te(l) and NT.hoa(l.tien_te) != p["tien_te"]):
                    canh_bao.append(
                        f"Dòng {l.line_no} ({NT.hoa(l.tien_te) or 'VND'}) khớp với lệnh chi {p['code']} "
                        f"({p['tien_te'] or 'VND'}) – khác đồng tiền nên khớp theo số VND; "
                        "chênh lệch tỷ giá của lần trả này KHÔNG đo được.")
                take = min(p["left"], max(0.0, (l.actual or 0) - paid))
                if take <= 0: break
                p["left"] -= take; paid += take
        if cands:
            l.paid = round(paid); matched += 1
            if abs(chenh_l) > NT.DUNG_SAI:
                tong_chenh += chenh_l
                chenh_dong.append({"dong": l.line_no, "mo_ta": (l.description or "")[:80],
                                   "ncc": (l.supplier_name or "")[:60], "tien_te": NT.hoa(l.tien_te),
                                   "so_ngoai_te_da_tra": round(nt_da_tra, 2),
                                   "ty_gia_quyet_toan": tg_da_dung, "nghia_vu_vnd": round(paid),
                                   "chenh": round(chenh_l)})
        else:
            unmatched += 1

    leftover = round(sum(p["left"] for p in pool))
    db.commit()
    tong_chenh = round(tong_chenh)
    return {"matched": matched, "unmatched": unmatched, "payments": len(prs), "leftover": leftover,
            # Chênh lệch tỷ giá: ĐO, chưa hạch toán. Dương = LỖ. Xem `services/ngoai_te_chi.py`.
            "chenh_ty_gia": tong_chenh, "chenh_ty_gia_nhan_xet": NT.nhan_xet_chenh(tong_chenh),
            "chenh_ty_gia_dong": chenh_dong, "canh_bao": canh_bao,
            "message": f"Đã khớp {matched} dòng với {len(prs)} lệnh chi/tạm ứng đã chi"
                       + (f"; {unmatched} dòng chưa có lệnh chi" if unmatched else "")
                       + (f"; còn {leftover:,.0f} đ lệnh chi chưa gắn dòng" if leftover > 0 else "")
                       + (f"; {NT.nhan_xet_chenh(tong_chenh)}" if abs(tong_chenh) > NT.DUNG_SAI else "")
                       + (f"; {len(canh_bao)} lần khớp khác đồng tiền" if canh_bao else "")}



def summary(db: Session, t: Tour) -> dict:
    ls = lines_of(db, t, active_only=True)
    actual = sum((l.actual or 0) for l in ls); paid = sum((l.paid or 0) for l in ls)
    budget_lines = sum((l.budget or 0) for l in ls)
    f, v, src = R.budget_of(db, t)          # dự toán tách hẳn khỏi thực chi (B2), có ghi nguồn
    budget_tour = f + v * R.booked_pax(t)
    budget = budget_lines or budget_tour
    b_src = "dong" if budget_lines else src
    rev = sum((b.amount or 0) - (b.discount or 0) for b in t.bookings if not b.cancelled)
    profit = rev - actual - (t.promo_value or 0)
    return {"lines": len(ls), "cancelled": sum(1 for l in lines_of(db, t) if l.status != "hd"), "actual": actual, "paid": paid, "remaining": max(0.0, actual - paid),
            "budget": budget, "budget_source": b_src, "budget_source_label": {"dong": "tổng dự toán theo dòng"}.get(b_src, R.BUDGET_SOURCES.get(b_src, b_src)),
            "has_budget": budget > 0 and b_src in ("dong", "du_toan_tour"), "variance": actual - budget, "variance_pct": (actual - budget) / budget if budget else 0,
            "revenue": rev, "profit": profit, "margin": profit / rev if rev else 0, "version": t.settlement_version, "with_doc": sum(1 for l in ls if l.doc_data)}


def checks(db: Session, t: Tour) -> list[dict]:
    """Chấm quyết toán trước khi đóng số: block = chặn đóng số; warn = cảnh báo (Kế toán xem)."""
    ls = lines_of(db, t, active_only=True); out = []
    thr = R.get_param(db, "nguong_bien", t.end_date) or 0.1
    for l in ls:
        if (l.budget or 0) and (l.actual or 0) > (l.budget or 0) * (1 + thr) and not l.note.strip():
            out.append({"level": "block", "line": l.line_no, "msg": f"Dòng {l.line_no} {l.description}: thực chi vượt dự toán {(((l.actual or 0) - (l.budget or 0)) / (l.budget or 0)) * 100:.0f}% – phải ghi lời giải trình ở Ghi chú"})
        if not l.supplier_tax_code and l.service_type in ("HOTEL", "RESTAURANT", "VEHICLE", "FLIGHT", "LAND", "INSURANCE") and (l.actual or 0) >= 5_000_000:
            out.append({"level": "warn", "line": l.line_no, "msg": f"Dòng {l.line_no}: NCC {l.supplier_name} chưa có MST (chi ≥ 5 triệu cần hóa đơn)"})
        # NHẮC, KHÔNG CHẶN — Chủ tịch chốt 27/9/2026.
        #
        # Đo trên dữ liệu thật hôm ấy: 13 dòng của tour ĐANG CHẠY (nguồn `vietrip`) viết phép tính
        # ngoại tệ bằng tay vào ô MÔ TẢ rồi gõ số VND vào, bốn ô ngoại tệ bỏ trống:
        #     "Tổng chi phí (bao gồm phụ thu): 4,341 USD x 26,500 + BANK FEE 2tr"
        #     "(13GBP*10days*9pax+13GBP*8days*2pax)*35,724 + 100$*11 days *26,5"
        # Mỗi dòng như thế là một tỷ giá không ai truy được, và không đối chiếu được với sao kê.
        #
        # Cửa nhập bốn ô đã có từ 25/9 — đây KHÔNG phải lỗi mã, mà là người dùng chưa dùng cửa ấy.
        # Chủ tịch chọn NHẮC chứ không CHẶN: chặn thì Điều hành kẹt ngay hôm sau với những dòng mô
        # tả chỉ vô tình có ba chữ cái trùng mã đồng tiền. Mức `warn` để nó hiện trên màn hình chủ
        # hồ sơ trước khi đóng số, và đi vào sổ soát — nhưng không chặn ai.
        #
        # Nhập tại chỗ, KHÔNG nhập ở đầu tệp: `soat_ngoai_te` nhập `calc_actual` từ chính tệp này,
        # nên nhập ngược ở đầu tệp là vòng tròn và cả máy chủ không khởi động được.
        from app.services.soat_ngoai_te import dong_tien_trong_chu
        doan = dong_tien_trong_chu(l)
        if doan and not (l.tien_te or "").strip():
            out.append({"level": "warn", "line": l.line_no,
                        "msg": f"Dòng {l.line_no}: mô tả có \"{doan}\" nhưng bốn ô ngoại tệ bỏ trống "
                               f"– hãy khai Tiền tệ / Số tiền gốc / Tỷ giá / Ngày tỷ giá để máy nhân, "
                               f"thay vì tự nhân ngoài hệ rồi gõ số VND (tỷ giá gõ tay không đối "
                               f"chiếu được với sao kê)"})
        if (l.paid or 0) > (l.actual or 0) + 1:
            out.append({"level": "warn", "line": l.line_no, "msg": f"Dòng {l.line_no}: đã thanh toán {l.paid:,.0f} lớn hơn thực chi {l.actual:,.0f}"})
    nodoc = [l.line_no for l in ls if not l.doc_data and (l.actual or 0) > 0]
    if nodoc:
        out.append({"level": "warn", "line": 0, "msg": f"{len(nodoc)}/{len(ls)} dòng chưa gắn chứng từ (dòng {', '.join(map(str, nodoc[:12]))}{'…' if len(nodoc) > 12 else ''})"})
    s = summary(db, t)
    if not s["has_budget"]:
        out.append({"level": "warn", "line": 0, "msg": "Chuyến chưa có dự toán để so sánh – không đánh giá được mức vượt chi (không coi dự toán thiếu là 0)"})
    elif s["variance_pct"] > thr:
        out.append({"level": "warn", "line": 0, "msg": f"Tổng thực chi vượt dự toán {s['variance_pct'] * 100:.0f}% (> {thr * 100:.0f}%, {s['budget_source_label']}) – TGĐ xem khi Kế toán xác nhận"})
    if (s["remaining"] or 0) > 0:
        out.append({"level": "info", "line": 0, "msg": f"Còn lại cần thanh toán NCC: {s['remaining']:,.0f} đ"})
    return out


def kt_return(db: Session, u: User, t: Tour, note: str) -> str:
    """Kế toán trả lại quyết toán để Điều hành sửa: trạng thái về ket_thuc, tăng phiên bản, ghi lịch sử."""
    from app.services.products import event as EV
    if u.role != "ketoan" and not toan_quyen_ke_ca_tach_bach(u, db): raise HTTPException(403, "Chỉ Kế toán trả lại quyết toán")
    if t.status != "da_dong_so": raise Gate("TRANG_THAI", "Chỉ trả lại quyết toán đang chờ Kế toán xác nhận")
    if not (note or "").strip(): raise Gate("QT_NHAP", "Trả lại phải ghi rõ lý do")
    t.status, t.closed_at, t.settlement_version = "ket_thuc", None, t.settlement_version + 1
    EV(db, t, "kt_tra_lai", u.username, note, title=f"Kế toán trả lại quyết toán → soạn lại V.{t.settlement_version:02d}")
    R.audit(db, u.username, u.role, "ke_toan_tra_lai_quyet_toan", f"tour:{t.code}", after={"v": t.settlement_version, "ly_do": note[:200]}); db.commit()
    return f"Đã trả lại – Điều hành soạn lại quyết toán V.{t.settlement_version:02d}"
