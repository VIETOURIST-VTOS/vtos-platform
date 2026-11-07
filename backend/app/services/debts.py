"""Sổ công nợ toàn hệ thống: phải thu của khách và phải trả nhà cung cấp.

Ba quy tắc dưới đây quyết định con số này có dùng được hay không, và cả ba đều là chỗ một bảng công nợ
làm ẩu sẽ nói sai:

  1. PHẢI THU VÀ PHẢI TRẢ KHÔNG BÙ TRỪ CHO NHAU. Khách nợ công ty và công ty nợ nhà cung cấp là hai quan hệ
     với hai đối tượng khác nhau. Trừ vào nhau ra "công nợ ròng" là con số không đòi được của ai và cũng
     không trả cho ai. Ở đây hai vế nằm hai mục, và không có trường nào là hiệu của hai vế.

  2. ĐỀ NGHỊ CHI CHƯA DUYỆT KHÔNG PHẢI LÀ NỢ. Một đề nghị đang chờ Trưởng phòng xem có thể bị từ chối.
     Gộp nó vào "phải trả" là thổi phồng nghĩa vụ và làm hỏng dự báo dòng tiền. Nghĩa vụ chỉ tính từ khi
     khoản chi đã được duyệt và đang chờ chi; phần chờ duyệt để riêng, gọi đúng tên là "đang chờ duyệt".

  3. THU THỪA KHÔNG ĐƯỢC LÀM PHẢI THU ÂM. Khách chuyển dư, hoặc booking giảm giá sau khi đã thu, là khoản
     công ty PHẢI TRẢ LẠI khách. Để nó thành số âm trong cột phải thu là vừa giấu một khoản phải trả, vừa
     làm tổng phải thu của cả công ty nhỏ hơn sự thật.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Booking, Tour, User
from app.models.ops import PaymentRequest

# Trạng thái đề nghị chi: đã qua duyệt và đang chờ chi = NGHĨA VỤ đã xác lập.
DA_DUYET_CHO_CHI = ("cho_chi",)
# Còn đang đi qua các cấp xem xét – chưa phải nghĩa vụ.
DANG_CHO_DUYET = ("cho_tp", "cho_kt", "cho_duyet")
DA_CHI = ("da_chi",)


def _q(x) -> float:
    return float(round(x or 0))


def phai_thu_khach(db: Session, den_ngay: date | None = None) -> dict:
    """Còn phải thu của khách, theo từng booking chưa hủy.

    Quá hạn tính theo NGÀY KHỞI HÀNH: tiền tour phải thu đủ trước khi khách lên xe, nên một booking đã khởi
    hành mà còn dư nợ là khoản đã đi khỏi tầm kiểm soát, không phải khoản "sắp thu"."""
    hom_nay = den_ngay or date.today()
    # KS-CN · 08/11/2026 — CHỈ KÉO VỀ NHỮNG BOOKING CÒN CHÊNH, VÀ CHỈ NHỮNG CỘT CẦN. Đo trên crm
    # thật: trang Công nợ chờ 4–5,7 giây, phần lớn là nạp nguyên vẹn hơn mười nghìn booking và mọi
    # tour thành đối tượng đầy đủ để rồi bỏ đi gần hết. Lọc `phải thu − đã thu ≠ 0` ngay trong SQL
    # là AN TOÀN với cách làm tròn bên dưới: chênh đúng bằng 0 thì hai vế làm tròn cũng bằng nhau,
    # nên dòng ấy vốn không vào rổ nào. Chênh khác 0 (kể cả 0,4 đồng) vẫn kéo về và để `_q` quyết
    # như cũ — không đổi một con số nào.
    chenh = (func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)
             - func.coalesce(Booking.paid, 0))
    bks = db.execute(select(Booking.id, Booking.code, Booking.customer_name, Booking.tour_id,
                            Booking.sales_id, Booking.amount, Booking.discount, Booking.paid)
                     .where(Booking.cancelled == False, chenh != 0).order_by(Booking.id)).all()   # noqa: E712
    t_ids = {b.tour_id for b in bks if b.tour_id}
    tours = {r.id: r for r in db.execute(select(Tour.id, Tour.code, Tour.name, Tour.start_date)
                                         .where(Tour.id.in_(t_ids))).all()} if t_ids else {}
    s_ids = {b.sales_id for b in bks if b.sales_id}
    sales = dict(db.execute(select(User.id, User.full_name).where(User.id.in_(s_ids))).all()) if s_ids else {}
    con_thu, tra_lai, qua_han = [], [], 0.0
    for b in bks:
        phai = _q((b.amount or 0) - (b.discount or 0))
        da = _q(b.paid or 0)
        t = tours.get(b.tour_id)
        dong = {"booking_id": b.id, "code": b.code, "khach": b.customer_name,
                "tour": t.code if t else "", "ten_tour": t.name if t else "",
                "khoi_hanh": t.start_date.isoformat() if t and t.start_date else None,
                "sales": sales.get(b.sales_id, ""), "phai_thu": phai, "da_thu": da}
        con = _q(phai - da)
        if con > 0:
            dong["con_lai"] = con
            dong["qua_han"] = bool(t and t.start_date and t.start_date < hom_nay)
            if dong["qua_han"]: qua_han += con
            con_thu.append(dong)
        elif con < 0:
            # Thu thừa: đây là khoản PHẢI TRẢ LẠI khách, không phải phải thu âm.
            dong["phai_tra_lai"] = _q(-con)
            tra_lai.append(dong)
    con_thu.sort(key=lambda x: -x["con_lai"]); tra_lai.sort(key=lambda x: -x["phai_tra_lai"])
    return {"tong_con_phai_thu": _q(sum(x["con_lai"] for x in con_thu)),
            "trong_do_qua_han": _q(qua_han),
            "so_booking": len(con_thu),
            "tong_thu_thua_phai_tra_lai": _q(sum(x["phai_tra_lai"] for x in tra_lai)),
            "chi_tiet": con_thu[:300], "thu_thua": tra_lai[:100]}


def phai_tra_ncc(db: Session) -> dict:
    """Phải trả nhà cung cấp, tách nghĩa vụ đã xác lập khỏi phần còn đang chờ duyệt."""
    tours = dict(db.execute(select(Tour.id, Tour.code)).all())   # KS-CN: hai cột, không nạp cả tour

    def gom(trang_thai):
        rows = list(db.execute(select(PaymentRequest)
                               .where(PaymentRequest.status.in_(trang_thai))
                               .order_by(PaymentRequest.amount.desc())).scalars())
        return rows

    def ra(rows):
        return [{"id": p.id, "code": p.code, "ncc": p.supplier_name, "tour": tours.get(p.tour_id, ""),
                 "so_tien": _q(p.amount), "noi_dung": p.description[:160], "loai": p.category,
                 "co_chung_tu": p.has_document, "co_hoa_don": p.has_invoice,
                 "status": p.status} for p in rows]

    no = gom(DA_DUYET_CHO_CHI)
    cho = gom(DANG_CHO_DUYET)
    theo_ncc: dict[str, float] = {}
    for p in no:
        theo_ncc[p.supplier_name or "(không ghi tên)"] = theo_ncc.get(p.supplier_name or "(không ghi tên)", 0) + (p.amount or 0)
    thieu_hd = [p for p in no if not p.has_invoice]
    return {"tong_phai_tra": _q(sum((p.amount or 0) for p in no)), "so_phieu": len(no),
            "dang_cho_duyet": _q(sum((p.amount or 0) for p in cho)), "so_phieu_cho_duyet": len(cho),
            "thieu_hoa_don_gtgt": _q(sum((p.amount or 0) for p in thieu_hd)),
            "theo_nha_cung_cap": [{"ncc": k, "so_tien": _q(v)}
                                  for k, v in sorted(theo_ncc.items(), key=lambda x: -x[1])[:50]],
            "chi_tiet": ra(no)[:300], "cho_duyet": ra(cho)[:100]}


def so_cong_no_toan_he_thong(db: Session) -> dict:
    from app.services import fleet_debt as CN
    thu = phai_thu_khach(db)
    tra = phai_tra_ncc(db)
    xe = CN.so_cong_no(db)
    return {
        "phai_thu_khach": thu,
        "phai_tra_ncc": tra,
        "doi_xe": {"cong_ty_phai_tra_chu_xe": xe["voi_chu_xe"]["cong_ty_phai_tra"],
                   "chu_xe_phai_tra_cong_ty": xe["voi_chu_xe"]["chu_xe_phai_tra_cong_ty"],
                   "con_phai_thu_ban_xe": xe["ban_xe"]["con_phai_thu"],
                   "du_no_vay_the_chap_xe": xe["vay_the_chap_xe"]["du_no_theo_khe_uoc"]},
        "giai_thich": [
            "Phải thu của khách và phải trả nhà cung cấp KHÔNG bù trừ cho nhau: hai quan hệ với hai đối "
            "tượng khác nhau, trừ vào nhau ra một con số không đòi được của ai và cũng không trả cho ai.",
            "Đề nghị chi đang chờ duyệt KHÔNG tính là nợ phải trả – nó có thể bị từ chối. Phần đó để riêng.",
            "Khách chuyển thừa là khoản PHẢI TRẢ LẠI khách, không phải phải thu âm; nếu để âm thì vừa giấu "
            "một khoản phải trả, vừa làm tổng phải thu nhỏ hơn sự thật.",
            "Phải thu quá hạn tính theo NGÀY KHỞI HÀNH: khách đã đi mà còn nợ là khoản đã ra khỏi tầm "
            "kiểm soát, không phải khoản sắp thu.",
        ],
        "tinh_den": datetime.now().isoformat(timespec="seconds"),
    }
