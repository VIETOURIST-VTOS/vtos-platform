"""Nghiệp vụ tour: dự toán, cổng chặn, phê duyệt, quyết toán. Mọi hàm nhận user đã xác thực."""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import Tour, User, ServiceRequest, Booking, Alert, AuditLog, ROLES
from app.services import rules as R
from app.services import ghi_mot_lan as GML
from app.services import accounting as ACC
from app.services.products import event as EV
from app.api.deps import Gate, toan_quyen, toan_quyen_ke_ca_tach_bach
from fastapi import HTTPException


def snap(t: Tour) -> dict:
    return {"code": t.code, "status": t.status, "price": t.price_per_pax, "fixed": t.fixed_cost, "var": t.var_cost_per_pax,
            "pax": t.planned_pax, "below_margin": t.below_margin, "actual_revenue": t.actual_revenue,
            "actual_cost": t.actual_cost, "promo": t.promo_value,
            # Ô hoa hồng khách đi vào nhật ký kiểm: ai đổi câu trả lời, từ gì sang gì, lúc nào.
            # Một ô bắt buộc mà không để lại vết đổi thì đổi lúc nào cũng được, và cái nó chặn
            # chỉ còn là sự bất tiện.
            "hoa_hong_khach": getattr(t, "hoa_hong_khach", ""),
            "hoa_hong_khach_tien": getattr(t, "hoa_hong_khach_tien", 0)}


def tour_view(db: Session, t: Tour, user: User | None = None) -> dict:
    thr = R.get_param(db, "nguong_bien", t.start_date)
    c = R.calc_db(db, t, thr)
    s = R.settlement_summary(db, t) if t.status in ("da_dong_so", "kt_xac_nhan", "khoa") else None
    bk = R.booked_pax(t)
    days_left = (t.start_date - date.today()).days
    out = {
        "id": t.id, "code": t.code, "name": t.name, "tour_type": t.tour_type, "start_date": t.start_date, "end_date": t.end_date,
        "phien_ban": getattr(t, "phien_ban", 1),   # V10 – màn hình gửi lại số này khi lưu
        "operator_id": t.operator_id, "operator_name": t.operator.full_name if t.operator else "",
        "price_per_pax": t.price_per_pax, "fixed_cost": t.fixed_cost, "var_cost_per_pax": t.var_cost_per_pax, "planned_pax": t.planned_pax,
        "rest_stops": t.rest_stops, "strategic": t.strategic, "below_margin": t.below_margin, "justification": t.justification,
        "status": t.status, "confirmed_by": t.confirmed_by, "approved_by": t.approved_by,
        "signed_chutich": t.signed_chutich, "signed_tgd": t.signed_tgd, "chairman_run_decision": t.chairman_run_decision,
        "actual_revenue": t.actual_revenue, "actual_cost": t.actual_cost, "promo_value": t.promo_value,
        "closed_at": t.closed_at, "kt_confirmed_at": t.kt_confirmed_at, "cntt_checked_at": t.cntt_checked_at,
        "calc": c, "booked_pax": bk, "days_left": days_left, "settlement_deadline": R.settlement_deadline(db, t),
        "approver_role": R.approver_role(t), "settlement": s, "is_doan": R.is_doan(t),
        "hoa_hong_khach": getattr(t, "hoa_hong_khach", ""),
        "hoa_hong_khach_tien": getattr(t, "hoa_hong_khach_tien", 0),
        # Biên thứ hai đặt CẠNH biên đã nhập, không thay nó. Xem `rules.bien_neu_hoa_hong_chua_vao`.
        "hoa_hong_khach_bien": R.bien_neu_hoa_hong_chua_vao(t, c),
        "company_id": t.company_id, "chua_gan_phap_nhan": t.company_id is None,   # P6: chưa xác định pháp nhân là một trạng thái phải nhìn thấy, không gộp về công ty mẹ
        "imported": t.imported, "product_code": t.product_code, "product_id": t.product_id, "days": t.days, "transport": t.transport, "vehicle_type": t.vehicle_type, "departure_point": t.departure_point,
        "d7_flag": bool(c["breakeven_pax"] and bk < c["breakeven_pax"] and 0 <= days_left <= int(R.get_param(db, "moc_d7")) and t.status == "da_duyet"),
        "bookings": [{"id": b.id, "code": b.code, "sales_id": b.sales_id, "customer_name": b.customer_name, "customer_phone": b.customer_phone, "source": b.source,
                      "pax": b.pax, "amount": b.amount, "discount": b.discount, "promo_code": b.promo_code, "sales_name": b.sales.full_name if b.sales else "",
                      "sla_minutes": b.sla_minutes, "sla_ok": b.sla_ok, "counts_for_target": b.counts_for_target, "created_at": b.created_at} for b in t.bookings],
    }
    if user:
        out["actions"] = allowed_actions(db, t, user)
    return out


def allowed_actions(db: Session, t: Tour, u: User) -> list[str]:
    a = []
    from app.services import access as AC
    # Bước Kinh doanh soạn (24/9/2026): khối Kinh doanh sửa, Sale Admin chuyển hoặc trả lại.
    if t.status == NHAP_KD:
        if u.role in AC.SALES or u.role == "sales_admin": a.append("edit")
        if u.role == "sales_admin": a += ["chuyen_dieu_hanh", "tra_lai_kinh_doanh"]
    if t.status == "nhap" and (u.id == t.operator_id or u.role == "tp_dh"): a += ["edit", "submit"]
    if t.status == "cho_xac_nhan" and u.role == "tp_dh": a.append("confirm")
    if t.status == "cho_duyet":
        if t.below_margin and u.role in ("chutich", "tgd") and not getattr(t, f"signed_{u.role}"): a.append("sign")
        if not t.below_margin and u.role == R.approver_role(t): a.append("approve")
    if t.status in ("ket_thuc", "da_duyet") and u.id == t.operator_id and date.today() >= t.end_date: a.append("close")
    if t.status == "da_dong_so" and u.role == "ketoan": a += ["kt_confirm", "kt_return"]
    if t.status in ("da_duyet", "ket_thuc") and u.id == t.operator_id: a.append("edit_settlement")
    if t.status == "kt_xac_nhan" and u.role == "cntt": a.append("cntt_check")
    if t.status == "da_duyet" and u.role in ("chutich", "tp_dh") and not t.chairman_run_decision: a.append("d7")
    return a


# ══════════════════════════════════════════════════════════════════════════════════════════════
# VÒNG ĐỜI DỰ TOÁN ĐOÀN — đổi ngày 24/9/2026 theo quyết định của Chủ tịch
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Trước bản này: "Chỉ Phòng Điều hành tạo tour và lập dự toán" (ĐH Điều 2), một chuỗi cho cả lẻ
# lẫn đoàn. Nay Kinh doanh Đoàn tự lập dự toán đoàn, và Sale Admin giữ cổng chuyển sang Điều hành
# (Phần V Bản mô tả công việc Sale Admin, hiệu lực 01/9/2026).
#
# HÌNH CỦA THAY ĐỔI — và đây là chỗ đáng đọc kỹ nhất:
#
#     nhap_kd ──(Sale Admin chuyển)──> nhap ──(Điều hành trình)──> cho_xac_nhan ──> cho_duyet ──> ...
#        ▲                               │
#        └──(Sale Admin trả lại)─────────┘
#
# Hai bước mới nằm TRƯỚC `nhap`, và bước chuyển đổ về ĐÚNG trạng thái `nhap` vốn đã có. Nghĩa là
# từ `nhap` trở đi KHÔNG một dòng nào phải sửa: cổng biên 10%, luật hai chữ ký cho chuyến dưới
# biên, hạn quyết toán, quỹ thưởng — tất cả giữ nguyên.
#
# Đó là lựa chọn có chủ ý. Cách khác là cho Kinh doanh trình thẳng vào `cho_xac_nhan`, ngắn hơn
# một bước; nhưng lúc ấy chuỗi cổng chặn có HAI lối vào thay vì một, và mọi phép thử đang canh
# chuỗi ấy phải viết lại. Một thay đổi vòng đời an toàn là thay đổi chỉ NỐI THÊM vào đầu chuỗi.
#
# TOUR LẺ KHÔNG ĐỔI GÌ: vẫn Điều hành tạo, vẫn vào thẳng `nhap`. ĐH Điều 2 còn nguyên cho mảng lẻ.
NHAP_KD = "nhap_kd"


def _la_doan(data_hoac_tour) -> bool:
    """Dữ liệu này là ĐOÀN không — hỏi lại `rules.is_doan`, không tự đọc `tour_type`.

    Lúc TẠO thì chưa có bản ghi Tour, nên dựng một bản tạm đủ để `is_doan` đọc. Vẫn là hỏi lại
    một luật đã có chủ, chứ không phải chép luật ấy ra đây lần thứ hai.
    """
    if isinstance(data_hoac_tour, Tour):
        return R.is_doan(data_hoac_tour)
    return R.is_doan(Tour(code=(getattr(data_hoac_tour, "code", "") or "").strip().upper(),
                          tour_type=getattr(data_hoac_tour, "tour_type", "")))


HOA_HONG_KHACH_HOP_LE = ("", "co", "khong")


def _dat_hoa_hong_khach(t: Tour, data) -> None:
    """Ghi câu trả lời ô hoa hồng khách — dùng chung cho `create` và `edit`.

    RỖNG NGHĨA LÀ "KHÔNG ĐỤNG TỚI", KHÔNG PHẢI "XOÁ CÂU TRẢ LỜI". Màn hình cũ chưa có ô này vẫn
    gửi lên chuỗi rỗng ở mọi lần sửa; nếu rỗng mà ghi đè thì một người sửa điểm dừng nghỉ sẽ lặng
    lẽ xoá câu trả lời của người khác, và dự toán quay về trạng thái chưa khai mà không ai biết vì
    sao. Muốn đổi câu trả lời thì gửi "co" hoặc "khong" — một giá trị, không phải một khoảng trống.

    Giá trị lạ bị từ chối thẳng: một chuỗi không đọc được nằm trong cột này sẽ làm cổng chuyển đọc
    ra "chưa trả lời" mãi mãi, và người dùng thấy mình đã điền rồi mà máy vẫn chặn.
    """
    khai = (getattr(data, "hoa_hong_khach", "") or "").strip()
    if khai not in HOA_HONG_KHACH_HOP_LE:
        raise Gate("HOA_HONG_KHACH", "Ô hoa hồng khách chỉ nhận 'co' hoặc 'khong'")
    if not khai:
        return
    t.hoa_hong_khach = khai
    # "khong" thì số tiền về RỖNG, không về 0: không có khoản tiền nào cả. Để lại một con số dưới
    # một câu trả lời "không" là để lại một con số mồ côi mà màn hình sau sẽ đọc ra theo cách của
    # nó — và 0 đồng đọc như "đã khai là 0", khác hẳn "không áp dụng".
    t.hoa_hong_khach_tien = float(getattr(data, "hoa_hong_khach_tien", 0) or 0) if khai == "co" else None


def create(db: Session, u: User, data) -> Tour:
    from app.services import access as AC
    kd_lap_doan = u.role in AC.SALES and _la_doan(data)
    if u.role not in ("nv_dh", "tp_dh") and not kd_lap_doan and not toan_quyen(u):
        raise HTTPException(403,
            "Tour lẻ: chỉ Phòng Điều hành tạo và lập dự toán (ĐH Điều 2). "
            "Tour đoàn: Phòng Điều hành hoặc Kinh doanh Đoàn (Chủ tịch quyết 24/9/2026)")
    code = data.code.strip().upper()
    if db.execute(select(Tour).where(Tour.code == code)).scalars().first():
        raise Gate("MA_TOUR", "Mã tour đã tồn tại")
    t = Tour(code=code, name=data.name, tour_type=data.tour_type, start_date=data.start_date, end_date=data.end_date,
             operator_id=data.operator_id, price_per_pax=data.price_per_pax, fixed_cost=data.fixed_cost,
             var_cost_per_pax=data.var_cost_per_pax, planned_pax=data.planned_pax, rest_stops=data.rest_stops,
             company_id=getattr(data, "company_id", None))   # bỏ trống → tour vào danh sách đối chiếu pháp nhân
    _dat_hoa_hong_khach(t, data)
    # Kinh doanh Đoàn lập thì dự toán đứng ở `nhap_kd`, chưa phải `nhap`: nó còn phải qua cổng
    # chuyển của Sale Admin. Điều hành lập thì vào thẳng `nhap` y như trước.
    if kd_lap_doan:
        t.status = NHAP_KD
    db.add(t); db.flush()
    from app.services.misa import ensure_project_for_tour
    ensure_project_for_tour(db, t)   # mỗi tour = một công trình (mã công trình = mã tour)
    EV(db, t, "khoi_tao", u.username, getattr(data, "note", "") or "")
    R.audit(db, u.username, u.role, "tao_tour", f"tour:{t.code}", after=snap(t)); db.commit(); db.refresh(t)
    return t


def edit(db: Session, u: User, t: Tour, data) -> Tour:
    from app.services import access as AC
    if t.status not in ("nhap", NHAP_KD):
        raise Gate("KHOA_DU_TOAN", "Dự toán đã trình, không sửa được (muốn sửa phải rút về nháp, có ghi nhật ký)")
    if t.status == NHAP_KD:
        # Giai đoạn Kinh doanh soạn. Mở cho CẢ KHỐI Kinh doanh chứ không riêng người tạo, và đây
        # là một lựa chọn có lý do: Trưởng phòng và Giám đốc Kinh doanh phải rà được dự toán của
        # nhân viên TRƯỚC khi Sale Admin chuyển đi — khoá theo người tạo là khoá luôn người rà.
        # Phạm vi vẫn hẹp: đúng một mảng (đoàn), đúng một trạng thái (nháp của Kinh doanh), và mọi
        # lần sửa đều để lại một dòng nhật ký mang tên người sửa.
        if not (u.role in AC.SALES or u.role == "sales_admin" or toan_quyen(u)):
            raise HTTPException(403, "Dự toán đoàn đang ở bước Kinh doanh soạn – chỉ khối Kinh doanh sửa")
        # Sale Admin sửa được Ở ĐÂY mà vẫn KHÔNG bán hàng và KHÔNG duyệt: Phần V cấm ba việc khác
        # hẳn — nhận khách, chốt đoàn, duyệt dự toán. Vá một trường còn thiếu trong bản nháp là
        # đúng việc mục 4.2 giao cho chị ấy.
    elif not (u.id == t.operator_id or u.role == "tp_dh" or toan_quyen(u)):
        raise HTTPException(403, "Chỉ người điều hành chuyến hoặc TP Điều hành sửa dự toán")
    before = snap(t)
    # V10 – hai người cùng sửa một dự toán thì người sau phải biết. Kiểm TRƯỚC khi gán, và từ chối
    # kèm nội dung mới để người sửa đối chiếu được thay vì phải đi tra tay.
    GML.kiem_phien_ban(t, getattr(data, "phien_ban", None), f"Dự toán tour {t.code}",
                       lambda: {**snap(t), "phien_ban": getattr(t, "phien_ban", 1),
                                "rest_stops": t.rest_stops, "justification": t.justification})
    t.price_per_pax, t.fixed_cost, t.var_cost_per_pax, t.planned_pax = data.price_per_pax, data.fixed_cost, data.var_cost_per_pax, data.planned_pax
    t.rest_stops, t.justification = data.rest_stops, data.justification
    _dat_hoa_hong_khach(t, data)
    GML.tang_phien_ban(t)
    EV(db, t, "sua_du_toan", u.username, "")
    R.audit(db, u.username, u.role, "sua_du_toan", f"tour:{t.code}", before=before, after=snap(t)); db.commit()
    return t


# ─────────────────── CỔNG CỦA SALE ADMIN: chuyển, hoặc trả lại ───────────────────
# Phần V Bản mô tả công việc: "Từ chối chuyển sang Phòng Điều hành những dự toán chưa đủ trường
# bắt buộc". Đây là quyền CHẶN duy nhất của vị trí ấy, và nó phải là một cổng thật trong mã —
# một lời nhắc trên màn hình thì không chặn được gì.
TOI_THIEU_LY_DO = 20     # độ dài tối thiểu của lý do trả lại, xem chú thích ở `tra_lai_kinh_doanh`


def _thieu_truong_de_chuyen(db: Session, t: Tour) -> list[str]:
    """Những trường còn thiếu khiến dự toán chưa đủ tư cách chuyển sang Điều hành.

    DÙNG LẠI ĐÚNG `R.calc` mà cổng biên dùng, không dựng phép kiểm thứ hai. Nếu chép tay danh
    sách này thì ngày bước trình siết thêm một điều kiện, cổng của Sale Admin vẫn cho qua một hồ
    sơ mà bước sau sẽ từ chối — và người bị trả lại hai lần sẽ thôi tin cả hai cổng.

    CỐ Ý KHÔNG ĐÒI ĐIỂM DỪNG NGHỈ: đó là việc của Điều hành (ĐH Điều 11), và họ điền nó ở bước
    sau. Bắt Kinh doanh khai hộ là bắt người không biết phải đoán.
    """
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))
    thieu = []
    if not (t.name or "").strip():
        thieu.append("tên đoàn / khách")
    if not t.start_date or not t.end_date:
        thieu.append("ngày khởi hành và kết thúc")
    if not c["complete"]:
        for ten, ok in (("giá bán mỗi khách", (t.price_per_pax or 0) > 0),
                        ("số khách dự toán", t.planned_pax > 0),
                        ("giá vốn: chi phí cố định hoặc chi phí theo khách", c["has_cost"]),
                        ("giá bán phải lớn hơn chi phí theo khách", c["breakeven_pax"] is not None)):
            if not ok:
                thieu.append(ten)
    if not t.operator_id:
        thieu.append("người điều hành phụ trách")
    # Ô bắt buộc hoa hồng khách — Chủ tịch quyết 24/9/2026, mục 4.2 bản mô tả Sale Admin.
    #
    # CHỈ ĐÒI Ở CHUYẾN ĐOÀN. Cổng này là cổng của phòng Đoàn; tour lẻ đi đường cũ của Điều hành và
    # không có ai ở bước này để trả lời, nên đòi ở đó là chặn một dây chuyền vì một câu hỏi không
    # dành cho nó.
    #
    # "khong" LÀ MỘT CÂU TRẢ LỜI HỢP LỆ và cổng cho qua. Cổng này không phán đoàn có hoa hồng hay
    # không — nó chỉ buộc phải có người trả lời. Chỗ trống và "không có" trông giống hệt nhau cho
    # tới lúc có ô này; sau khi có, ai ghi "không" trong khi đã hứa 5% cho khách thì đó là một câu
    # nói dối mang tên người và dấu thời gian, không còn là một ô bỏ quên.
    if R.is_doan(t):
        khai = (getattr(t, "hoa_hong_khach", "") or "").strip()
        if khai not in ("co", "khong"):
            thieu.append("trả lời ô hoa hồng dành cho khách: có hay không")
        elif khai == "co" and float(getattr(t, "hoa_hong_khach_tien", 0) or 0) <= 0:
            thieu.append("số tiền hoa hồng dành cho khách (đã khai là CÓ)")
    return thieu


def chuyen_dieu_hanh(db: Session, u: User, t: Tour, note: str = "") -> str:
    """Sale Admin chuyển dự toán đoàn sang Phòng Điều hành. `nhap_kd` → `nhap`."""
    if u.role != "sales_admin" and not toan_quyen(u):
        raise HTTPException(403, "Chỉ Sale Admin phòng Đoàn chuyển dự toán sang Điều hành")
    if t.status != NHAP_KD:
        raise Gate("TRANG_THAI", "Chỉ dự toán đang ở bước Kinh doanh soạn mới chuyển được")
    thieu = _thieu_truong_de_chuyen(db, t)
    if thieu:
        raise Gate("THIEU_TRUONG",
                   "Chưa chuyển được, còn thiếu: " + "; ".join(thieu) +
                   ". Trả lại nhân viên phụ trách kèm ghi rõ thiếu gì (Phần V bản mô tả).")
    t.status = "nhap"
    EV(db, t, "chuyen_dieu_hanh", u.username, note)
    R.audit(db, u.username, u.role, "chuyen_du_toan_sang_dieu_hanh", f"tour:{t.code}", after=snap(t))
    db.commit()
    return "Đã chuyển Phòng Điều hành – chờ điền điểm dừng nghỉ, rà giá vốn rồi trình"


def tra_lai_kinh_doanh(db: Session, u: User, t: Tour, ly_do: str = "") -> str:
    """Sale Admin trả dự toán về cho nhân viên phụ trách. Trạng thái GIỮ NGUYÊN `nhap_kd`.

    BẮT BUỘC CÓ LÝ DO, và đây là cùng một luật đã đặt cho nút đóng cảnh báo ngày 11/9/2026:
    "đóng mà không phải nói dựa vào đâu thì nút đóng là nút giấu việc". Trả lại mà không nói
    thiếu gì thì người nhận lại chỉ biết là mình bị trả, không biết phải sửa gì — và bản sau sẽ
    bị trả lần nữa. Bản mô tả cũng viết đúng thế: "trả lại ... KÈM GHI RÕ TRƯỜNG CÒN THIẾU".

    Danh sách máy đo được đính kèm tự động, nhưng KHÔNG thay cho lý do người viết: máy chỉ thấy
    trường trống, còn "giá bán thấp hơn bảng giá đã duyệt" thì chỉ người đọc mới thấy.
    """
    if u.role != "sales_admin" and not toan_quyen(u):
        raise HTTPException(403, "Chỉ Sale Admin phòng Đoàn trả lại dự toán")
    if t.status != NHAP_KD:
        raise Gate("TRANG_THAI", "Dự toán không còn ở bước Kinh doanh soạn")
    if len((ly_do or "").strip()) < TOI_THIEU_LY_DO:
        raise Gate("THIEU_LY_DO",
                   f"Phải ghi rõ vì sao trả lại (tối thiểu {TOI_THIEU_LY_DO} ký tự). "
                   "Trả lại mà không nói thiếu gì thì bản sau sẽ bị trả lần nữa.")
    may_do = _thieu_truong_de_chuyen(db, t)
    ghi = ly_do.strip() + (" · Máy đo thấy thiếu: " + "; ".join(may_do) if may_do else "")
    EV(db, t, "tra_lai_kinh_doanh", u.username, ghi)
    R.audit(db, u.username, u.role, "tra_lai_du_toan_kinh_doanh", f"tour:{t.code}", after=snap(t))
    db.commit()
    return "Đã trả lại nhân viên phụ trách kèm lý do"


def submit(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role not in ("nv_dh", "tp_dh") and not toan_quyen(u): raise HTTPException(403, "Chỉ Điều hành trình dự toán")
    if t.status != "nhap": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    c = R.calc(t, R.get_param(db, "nguong_bien", t.start_date))   # bước trình: dùng đúng số Điều hành nhập, không mượn dự toán sản phẩm
    if not c["complete"]:
        thieu = [n for n, ok in (("giá bán/khách", (t.price_per_pax or 0) > 0), ("số khách dự toán", t.planned_pax > 0),
                                 ("chi phí cố định hoặc chi phí theo khách", c["has_cost"]),
                                 ("giá bán phải lớn hơn chi phí theo khách", c["breakeven_pax"] is not None)) if not ok]
        raise Gate("CONG_5", "Dự toán chưa đủ cơ sở tính, thiếu: " + "; ".join(thieu) + ". Không có giá vốn thì không tính được biên – cổng biên không thể ĐẠT")
    if not t.rest_stops.strip():
        raise Gate("CONG_5", "Dự toán phải ghi điểm dừng nghỉ (ĐH Điều 11)")
    if not c["pass_gate"] and len(t.justification.strip()) < 30:
        raise Gate("CONG_1_2", f"Biên kế hoạch {c['margin']*100:.1f}% dưới {c['threshold']*100:.0f}%: phải có giải trình 4 mục (lý do · khoản làm mỏng biên · phương án bù · lỗ tối đa) mới trình được")
    t.below_margin = not c["pass_gate"]; t.status = "cho_xac_nhan"
    EV(db, t, "trinh_du_toan", u.username, note or (t.justification if not c["pass_gate"] else ""))
    R.audit(db, u.username, u.role, "trinh_du_toan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã trình Trưởng phòng Điều hành xác nhận"


def confirm(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "tp_dh" and not toan_quyen(u): raise HTTPException(403, "Chỉ Trưởng phòng Điều hành xác nhận dự toán")
    if t.status != "cho_xac_nhan": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    t.status, t.confirmed_by = "cho_duyet", u.username
    EV(db, t, "tp_xac_nhan", u.username, note)
    R.audit(db, u.username, u.role, "tp_xac_nhan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã xác nhận, chuyển " + ("Chủ tịch + TGĐ (2 chữ ký)" if t.below_margin else ROLES[R.approver_role(t)]) + " duyệt"


def approve(db: Session, u: User, t: Tour, note: str = "") -> str:
    if t.status != "cho_duyet": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    if t.below_margin:
        if u.role not in ("chutich", "tgd"):
            raise Gate("CONG_1", "Chuyến dưới biên 10% chỉ Chủ tịch và Tổng giám đốc được ký")
        if getattr(t, f"signed_{u.role}"): raise Gate("DA_KY", "Đã ký rồi")
        setattr(t, f"signed_{u.role}", True)
        EV(db, t, "ky", u.username, note, title=f"Ký duyệt chuyến dưới biên ({ROLES[u.role]})")
        R.audit(db, u.username, u.role, "ky_duyet_duoi_bien", f"tour:{t.code}", after=snap(t))
        if t.signed_chutich and t.signed_tgd:
            t.status, t.approved_by = "da_duyet", "chutich+tgd"
            R.audit(db, u.username, u.role, "duyet_du_toan_2_chu_ky", f"tour:{t.code}", after=snap(t)); db.commit()
            return "Đủ 2 chữ ký – chuyến được duyệt với cờ 'dưới biên' (không thưởng lẻ, không tính chỉ tiêu)"
        db.commit(); return f"Đã ký ({ROLES[u.role]}). Chờ chữ ký còn lại"
    need = R.approver_role(t)
    if u.role != need and not toan_quyen(u): raise Gate("PHAN_QUYEN", f"Dự toán này do {ROLES[need]} duyệt (Văn bản đính chính Điều 4)")
    t.status, t.approved_by = "da_duyet", u.username
    EV(db, t, "duyet", u.username, note)
    R.audit(db, u.username, u.role, "duyet_du_toan", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã duyệt – Kinh doanh có thể chốt khách; 3 con số công bố trên lịch khởi hành"


def d7(db: Session, u: User, t: Tour, decision: str, note: str = "") -> str:
    if u.role not in ("chutich", "tp_dh"): raise HTTPException(403, "Chỉ TP Điều hành (ghép/dời/hủy) hoặc Chủ tịch")
    if decision == "chay":
        if u.role != "chutich": raise Gate("CONG_8", "Chuyến dưới hòa vốn muốn chạy tiếp phải do Chủ tịch duyệt")
        t.chairman_run_decision = f"Chủ tịch duyệt chạy {date.today():%d/%m/%Y}"
    elif decision in ("ghep", "doi", "huy"):
        t.status, t.chairman_run_decision = "huy", f"{decision} bởi {u.username} {date.today():%d/%m/%Y}"
    else:
        raise Gate("D7", "Quyết định không hợp lệ")
    for a in db.execute(select(Alert).where(Alert.kind == "d7", Alert.ref == t.code)).scalars(): a.resolved = True
    EV(db, t, "d7", u.username, note, title=f"Quyết định mốc D-7: {decision}")
    R.audit(db, u.username, u.role, f"d7_{decision}", f"tour:{t.code}", after=snap(t)); db.commit()
    return "Đã ghi quyết định D-7"


def close(db: Session, u: User, t: Tour, data, note: str = "") -> str:
    if t.status not in ("ket_thuc", "da_duyet"): raise Gate("TRANG_THAI", "Chưa đến bước quyết toán")
    if u.id != t.operator_id: raise Gate("CONG_6", f"Một cửa: chỉ người điều hành chuyến ({t.operator.full_name}) mới được nhập quyết toán")
    if date.today() < t.end_date: raise Gate("CONG_6", "Chuyến chưa kết thúc")
    from app.services import settlement as ST
    blocks = [c["msg"] for c in ST.checks(db, t) if c["level"] == "block"]
    if blocks: raise Gate("QT_NHAP", blocks[0])
    before = snap(t)
    sm = ST.summary(db, t)
    t.actual_revenue, t.promo_value = data.actual_revenue, data.promo_value
    t.actual_cost = sm["actual"] if sm["lines"] else data.actual_cost   # có bảng dòng NCC → tổng dòng là giá vốn thực tế (không nhập tay)
    t.closed_at, t.status = datetime.now(), "da_dong_so"
    tag = f"Quyết toán V.{t.settlement_version:02d}: {sm['lines']} dòng NCC, thực chi {(t.actual_cost or 0):,.0f} đ, đã trả {(sm['paid'] or 0):,.0f} đ, dự toán {(sm['budget'] or 0):,.0f} đ ({sm['variance_pct'] * 100:+.0f}%), {sm['with_doc']}/{sm['lines']} dòng có chứng từ"
    EV(db, t, "dong_so", u.username, (note + " | " if note else "") + tag)
    R.audit(db, u.username, u.role, "dong_so_quyet_toan", f"tour:{t.code}", before=before, after=snap(t)); db.commit()
    late = date.today() > R.settlement_deadline(db, t)
    return "Đã đóng số, chuyển Kế toán xác nhận" + (" – QUÁ HẠN quyết toán, mất thưởng chuyến" if late else "")


def kt_confirm(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "ketoan" and not toan_quyen_ke_ca_tach_bach(u, db): raise HTTPException(403, "Chỉ Kế toán xác nhận quyết toán")
    if t.status != "da_dong_so": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    t.status, t.kt_confirmed_at = "kt_xac_nhan", datetime.now()
    EV(db, t, "kt_xac_nhan", u.username, note)
    R.audit(db, u.username, u.role, "ke_toan_xac_nhan", f"tour:{t.code}", after=snap(t))
    ACC.on_settlement_confirmed(db, t, u.username, u.role); db.commit()
    return "Kế toán đã xác nhận – số liệu này là căn cứ duy nhất tính thưởng"


def cntt_check(db: Session, u: User, t: Tour, note: str = "") -> str:
    if u.role != "cntt" and not toan_quyen_ke_ca_tach_bach(u, db): raise HTTPException(403, "Chỉ CNTT đối chiếu độc lập")
    if t.status != "kt_xac_nhan": raise Gate("TRANG_THAI", "Trạng thái không phù hợp")
    bk = sum((b.amount or 0) - (b.discount or 0) for b in t.bookings)
    chk = {"doanh_thu_booking": bk, "doanh_thu_quyet_toan": (t.actual_revenue or 0), "lech": round((t.actual_revenue or 0) - bk)}
    t.status, t.cntt_checked_at = "khoa", datetime.now()
    EV(db, t, "cntt_khoa", u.username, (note + " | " if note else "") + f"Lệch doanh thu booking/quyết toán: {chk['lech']:,.0f} đ")
    R.audit(db, u.username, u.role, "cntt_doi_chieu_khoa", f"tour:{t.code}", after=chk); db.commit()
    return f"Đã đối chiếu và khóa. Lệch doanh thu booking/quyết toán: {chk['lech']:,.0f} đ" + (" → đã ghi nhật ký trình TGĐ" if abs(chk["lech"]) > 1000 else "")


# ---------- yêu cầu & booking ----------
def create_request(db: Session, u: User, data) -> ServiceRequest:
    from app.services import access as AC
    if u.role not in AC.REQUEST_CREATE_ROLES and not toan_quyen(u): raise HTTPException(403, "Vai trò này không gửi yêu cầu đặt dịch vụ")
    missing = [n for n, v in (("số điện thoại khách", data.customer_phone), ("nguồn khách", data.source), ("ghi chú chăm sóc", data.care_note)) if not v.strip()]
    if missing:
        raise Gate("CONG_4", "Thiếu trường bắt buộc: " + ", ".join(missing) + " (booking sẽ không tính chỉ tiêu, không hoa hồng)")
    t = db.get(Tour, data.tour_id)
    if not t: raise Gate("TOUR", "Không có tour")
    r = ServiceRequest(tour_id=t.id, sales_id=u.id, customer_name=data.customer_name, customer_phone=data.customer_phone,
                       source=data.source, care_note=data.care_note, pax=data.pax, campaign_code=data.campaign_code,
                       promo_code=data.promo_code, discount=data.discount)
    db.add(r); db.flush()
    R.audit(db, u.username, u.role, "gui_yeu_cau_dat_dich_vu", f"yeucau:{r.id}", after={"tour": t.code, "pax": r.pax, "khach": r.customer_name}); db.commit(); db.refresh(r)
    return r


def create_booking(db: Session, u: User, r: ServiceRequest) -> tuple[Booking, str]:
    if u.role not in ("nv_dh", "tp_dh") and not toan_quyen(u): raise Gate("CONG_12", "Chỉ Phòng Điều hành tạo booking")
    if r.booking_id: raise Gate("TRANG_THAI", "Yêu cầu đã có booking")
    t = db.get(Tour, r.tour_id)
    if t.status != "da_duyet": raise Gate("CONG_1", "Tour chưa được duyệt dự toán, không thể tạo booking")
    thr = R.get_param(db, "nguong_bien", t.start_date)
    cb = R.calc_db(db, t, thr)
    if not cb["complete"]:
        # Chuyến do VTOS lập phải có dự toán mới được bán; chuyến nhập từ Vietrip đang bán thì ghi cảnh báo
        # (chặn cứng sẽ đóng băng hơn 1.200 tour đang chạy – việc bổ sung dự toán thuộc Đợt 1 kế hoạch điều chỉnh).
        if not t.imported:
            raise Gate("CONG_1", "Chuyến chưa có dự toán đủ cơ sở tính (thiếu giá vốn) – không mở bán được")
        if not db.execute(select(Alert).where(Alert.kind == "thieu_du_toan", Alert.ref == t.code, Alert.resolved == False)).scalars().first():
            db.add(Alert(kind="thieu_du_toan", level="warn", ref=t.code,
                         message=f"{t.code} đang bán nhưng chưa có dự toán ({R.BUDGET_SOURCES['chua_co']}) – không đánh giá được biên, cần Điều hành bổ sung",
                         to_roles="tp_dh,nv_dh,gd_kd,tgd"))
    if (r.discount or 0) > 0:
        c = cb
        nr = (c["revenue"] or 0) - (r.discount or 0)
        nm = (nr - (c["cost"] or 0)) / nr if nr > 0 else 0
        if nm < thr:
            raise Gate("CONG_3", f"Mã KM/giảm giá {(r.discount or 0):,.0f} đ làm biên chuyến tụt còn {nm*100:.1f}% (< {thr*100:.0f}%): treo, cần TGĐ duyệt")
    mins = int((datetime.now() - r.created_at).total_seconds() / 60)
    sla = int(R.get_param(db, "sla_booking_phut"))
    n = db.execute(select(func.count()).select_from(Booking)).scalar() + 1
    b = Booking(code=f"BK{date.today():%y%m}{n:04d}", tour_id=t.id, request_id=r.id, sales_id=r.sales_id, created_by=u.id,
                customer_name=r.customer_name, customer_phone=r.customer_phone, source=r.source, care_note=r.care_note,
                pax=r.pax, amount=(t.price_per_pax or 0) * r.pax, discount=(r.discount or 0), promo_code=r.promo_code, campaign_code=r.campaign_code,
                counts_for_target=not t.below_margin, sla_minutes=mins, sla_ok=mins <= sla,
                company_id=t.company_id)      # doanh thu booking thuộc pháp nhân của chuyến
    db.add(b); db.flush(); r.booking_id = b.id
    from app.services import bookings as BK
    BK.init_terms(db, b, t)
    for a in db.execute(select(Alert).where(Alert.kind == "sla_booking", Alert.ref == f"YC-{r.id}")).scalars(): a.resolved = True
    R.audit(db, u.username, u.role, "tao_booking", f"booking:{b.code}", after={"tour": t.code, "pax": b.pax, "amount": b.amount, "sla_phut": mins, "sla_ok": b.sla_ok, "tinh_chi_tieu": b.counts_for_target}); db.commit(); db.refresh(b)
    return b, f"Đã tạo {b.code} sau {mins} phút" + ("" if b.sla_ok else " – QUÁ 2 GIỜ, ghi vào tiêu chí đánh giá")
