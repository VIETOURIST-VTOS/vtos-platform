"""Phản hồi & khiếu nại (Đợt 3) và Chăm sóc sau bán (Đợt 4).

Ba chốt chặn của tệp này, viết ra để lần sau không ai gỡ nhầm:

1. Không có ô số tiền bồi thường. Hồ sơ chỉ ghi ĐỀ NGHỊ CỦA KHÁCH bằng nguyên văn; hướng xử lý có hoàn
   tiền thì phải gắn số hiệu Đề nghị chi nhóm "hoan_tien" mới đóng được hồ sơ.
2. Hạn phản hồi lấy từ THAM SỐ CHÍNH SÁCH theo mức độ, không viết cứng. Quá hạn thì robot cảnh báo lên
   trưởng bộ phận rồi lên Ban TGĐ – không im lặng.
3. Phiếu chăm sóc TỰ SINH từ tour đã kết thúc. Không có nút thêm phiếu nhập tay: danh sách nhập tay sẽ
   đầy đủ hai tuần đầu rồi thưa dần và bỏ hẳn.
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.core import User, Booking, Tour, Alert
from app.models.crm import Lead
from app.models.ops import PaymentRequest
from app.models.cskh import (Complaint, CareTicket, KN_NGUON, KN_NHOM, KN_NHOM_CAN_BOOKING, KN_MUC,
                             KN_TRANG_THAI, KN_NGUYEN_NHAN, KN_HUONG, KN_HUONG_CO_TIEN, KN_HAN_THAM_SO,
                             CS_HINH_THUC, CS_DIEM)
from app.services import rules as R

XU_LY = ("nv_mkt", "ptgd_mkt", "gd_kd", "tp_kd", "nv_kd", "tn_kd", "tp_dh", "nv_dh", "ptgd_doan")
DONG_MUC3 = ("ptgd_mkt", "ptgd_doan", "tgd", "chutich")     # mức 3 phải có Ban TGĐ trong danh sách xử lý
CHUYEN = {"moi": ("dang_xu_ly",), "dang_xu_ly": ("cho_khach", "da_dong"),
          "cho_khach": ("dang_xu_ly", "da_dong"), "da_dong": ("tai_mo",), "tai_mo": ("dang_xu_ly",)}


# ====================== ĐỢT 3: PHẢN HỒI & KHIẾU NẠI ======================
def next_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(Complaint)).scalar() + 1
    return f"KN{date.today():%y%m}-{n:03d}"


def han_theo_muc(db: Session, level: int, tu: datetime | None = None) -> datetime:
    """Hạn phản hồi khách. Số giờ nằm ở bảng tham số chính sách để Ban TGĐ đổi được mà không sửa phần mềm."""
    gio = R.get_param(db, KN_HAN_THAM_SO.get(level, "kn_han_muc1_gio"))
    return (tu or datetime.now()) + timedelta(hours=float(gio or 72))


def lan_khieu_nai_12_thang(db: Session, phone: str, tru_id: int | None = None) -> int:
    """Số hồ sơ của cùng số điện thoại trong 12 tháng gần nhất.

    Khách khiếu nại lần thứ hai trở lên là dấu hiệu vấn đề hệ thống chứ không phải khách khó tính, và là
    thông tin Ban TGĐ cần thấy ngay trên hồ sơ chứ không phải đi tra sổ mới ra.
    """
    if not (phone or "").strip(): return 0
    moc = datetime.now() - timedelta(days=365)
    q = select(func.count()).select_from(Complaint).where(Complaint.customer_phone == phone,
                                                          Complaint.received_at >= moc)
    if tru_id: q = q.where(Complaint.id != tru_id)
    return int(db.execute(q).scalar() or 0)


def kiem_du_lieu(db: Session, d: dict) -> None:
    if d.get("source") not in KN_NGUON: raise ValueError(f"Nguồn tiếp nhận không hợp lệ. Chỉ nhận: {', '.join(KN_NGUON)}")
    if d.get("nhom") not in KN_NHOM: raise ValueError(f"Nhóm vấn đề không hợp lệ. Chỉ nhận: {', '.join(KN_NHOM)}")
    if int(d.get("level") or 0) not in KN_MUC: raise ValueError("Mức độ phải là 1, 2 hoặc 3")
    if not (d.get("customer_name") or "").strip(): raise ValueError("Phải ghi tên khách hàng")
    if not (d.get("noi_dung") or "").strip():
        raise ValueError("Phải ghi nguyên văn nội dung khách phản ánh – tóm tắt lại theo ý mình là mất chứng cứ")
    if d.get("nhom") in KN_NHOM_CAN_BOOKING and not d.get("booking_id"):
        raise ValueError("Khiếu nại chất lượng dịch vụ phải chọn chuyến/booking liên quan – không có chuyến thì "
                         "không quy được trách nhiệm về hướng dẫn viên, xe hay nhà cung cấp nào")
    if d.get("booking_id") and not db.get(Booking, d["booking_id"]):
        raise ValueError("Không có booking này")


def giao_viec(db: Session, kind: str, ref: str, msg: str, *, nguoi_id: int | None,
              han_gio: float | None, roles: str, level: str = "warn") -> Alert | None:
    """Sinh MỘT cảnh báo CÓ CHỦ và CÓ HẠN. Trả None nếu đã có cảnh báo cùng loại chưa đóng.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    VÌ SAO CẦN HÀM NÀY, TRONG KHI `Alert(...)` GỌI THẲNG CŨNG CHẠY
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Bảng `alerts` có sẵn `nguoi_phu_trach` và `han_xu_ly` từ PQ-9 và KS-4, kèm một chú thích dài
    trong `models/core.py` giải thích vì sao: đo bản đang chạy cho thấy 1.557 trên 1.703 cảnh báo
    chưa ai xử lý, và lý do là chúng gửi cho `to_roles` — bốn vai trò, tức không ai.

    `rules.run_robots` điền hai cột ấy. `robot_cskh` thì KHÔNG — nó gọi `Alert(kind=..., level=...,
    ref=..., message=..., to_roles=...)` và bỏ trống phần còn lại. Đó là chỗ sót, không phải quyết
    định: cùng một kho, cùng một bảng, hai lối dùng khác nhau.

    Hàm này đóng chỗ sót ấy, và đóng bằng cách làm cho việc điền dễ hơn việc bỏ trống.

    `nguoi_id` để trống là HỢP LỆ và phải đếm được — có loại việc thật sự không suy ra được chủ
    (một chuyến đông khách có nhiều sale). Chỗ nguy hiểm không phải ô trống, mà là ô trống không
    ai biết là trống.
    """
    co = db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref,
                                        Alert.resolved == False)).scalars().first()
    if co: return None
    a = Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles,
              nguoi_phu_trach=nguoi_id,
              giao_luc=datetime.now() if nguoi_id else None,
              han_xu_ly=(datetime.now() + timedelta(hours=han_gio)) if han_gio else None,
              gom_khoa=f"{kind}:{ref}", nguon="phat_sinh")
    db.add(a)
    return a


def tao(db: Session, u: User, data: dict, tu_dong: bool = False) -> Complaint:
    """Lập hồ sơ khiếu nại.

    `tu_dong` dành cho hồ sơ do phiếu chăm sóc sau bán tự mở (điểm hài lòng thấp). Bản tự mở KHÔNG có
    "đề nghị của khách", vì lúc đó chưa ai hỏi khách câu ấy – và bịa ra một đề nghị để cho đủ ô là tệ hơn
    nhiều so với để trống. Chốt chặn nằm ở chỗ khác: không có đề nghị của khách thì không đóng hồ sơ được.
    """
    d = dict(data); nguon_tao = (d.pop("nguon_tao", "") or "nguoi").lower()
    if nguon_tao not in ("nguoi", "ai"): raise ValueError("Nguồn tạo chỉ nhận 'nguoi' hoặc 'ai'")
    kiem_du_lieu(db, d)
    if not tu_dong and not (d.get("de_nghi_khach") or "").strip():
        raise ValueError("Phải ghi ĐỀ NGHỊ CỦA KHÁCH bằng nguyên văn (xin lỗi, đổi lịch, hoàn tiền…). "
                         "Màn hình này không có ô số tiền – số tiền nằm ở Đề nghị chi nhóm hoàn tiền")
    if nguon_tao == "ai" and not (d.get("ai_ghi_chu") or "").strip():
        raise ValueError("Hồ sơ do AI lập phải ghi căn cứ – không có căn cứ thì người xử lý không kiểm được gì")
    lv = int(d.get("level") or 1)
    bk = db.get(Booking, d["booking_id"]) if d.get("booking_id") else None
    c = Complaint(code=next_code(db), source=d["source"], customer_name=d["customer_name"],
                  customer_phone=(d.get("customer_phone") or (bk.customer_phone if bk else "")),
                  booking_id=d.get("booking_id"), tour_id=(bk.tour_id if bk else None), nhom=d["nhom"],
                  level=lv, noi_dung=d["noi_dung"], de_nghi_khach=d.get("de_nghi_khach", ""),
                  received_by=u.username, received_at=datetime.now(),
                  handler=d.get("handler") or "", han_phan_hoi=han_theo_muc(db, lv),
                  company_id=(bk.company_id if bk else d.get("company_id")),
                  care_id=d.get("care_id"), nguon_tao=nguon_tao, ai_ghi_chu=d.get("ai_ghi_chu", ""),
                  status="moi", created_by=u.username)
    db.add(c); db.flush()
    R.audit(db, u.username, u.role, "lap_khieu_nai", f"complaint:{c.code}",
            after={"muc": lv, "nhom": c.nhom, "khach": c.customer_name, "tu_dong": tu_dong})
    return c


def ghi_phan_hoi_dau(db: Session, u: User, c: Complaint) -> Complaint:
    """Đánh dấu đã phản hồi khách lần đầu – mốc để đo có kịp hạn hay không."""
    if c.first_response_at: raise ValueError("Hồ sơ đã ghi nhận phản hồi đầu tiên")
    c.first_response_at = datetime.now()
    if c.status == "moi": c.status = "dang_xu_ly"
    if not c.handler: c.handler = u.username
    R.audit(db, u.username, u.role, "phan_hoi_khieu_nai", f"complaint:{c.code}",
            after={"tre_han": bool(c.han_phan_hoi and c.first_response_at > c.han_phan_hoi)})
    db.commit(); db.refresh(c)
    return c


def _kiem_chung_tu_hoan_tien(db: Session, c: Complaint, huong: list, pr_id: int | None) -> None:
    if not any(h in KN_HUONG_CO_TIEN for h in huong): return
    if not pr_id:
        raise ValueError("Hướng xử lý có hoàn tiền thì phải gắn số Đề nghị chi – màn hình này không có ô "
                         "nhập số tiền, số tiền nằm ở chứng từ chi và đi đúng cấp duyệt theo ngưỡng hiện hành")
    pr = db.get(PaymentRequest, pr_id)
    if not pr: raise ValueError("Không có đề nghị chi này")
    if pr.category != "hoan_tien":
        raise ValueError(f"Đề nghị chi {pr.code} thuộc nhóm '{pr.category}', không phải nhóm hoàn tiền")
    if pr.status == "tu_choi":
        raise ValueError(f"Đề nghị chi {pr.code} đã bị từ chối – không dùng làm căn cứ đóng hồ sơ được")


def dong(db: Session, u: User, c: Complaint, data: dict) -> Complaint:
    """Đóng hồ sơ. Mức 3 cần hai chữ ký và người xử lý không được tự đóng hồ sơ của mình."""
    if c.status == "da_dong": raise ValueError("Hồ sơ đã đóng")
    huong = data.get("huong_xu_ly") or c.huong_xu_ly or []
    la = [h for h in huong if h not in KN_HUONG]
    if la: raise ValueError(f"Hướng xử lý không hợp lệ: {', '.join(la)}")
    if not huong: raise ValueError("Phải chọn hướng xử lý trước khi đóng hồ sơ")
    nn_nhom = data.get("nguyen_nhan_nhom") or c.nguyen_nhan_nhom
    if nn_nhom not in KN_NGUYEN_NHAN: raise ValueError("Phải xác định nguyên nhân: do ta / do NCC / do khách / bất khả kháng")
    if not (data.get("nguyen_nhan") or c.nguyen_nhan or "").strip():
        raise ValueError("Phải ghi giải trình nguyên nhân")
    de_nghi = (data.get("de_nghi_khach") or c.de_nghi_khach or "").strip()
    if not de_nghi:
        raise ValueError("Chưa ghi ĐỀ NGHỊ CỦA KHÁCH – hồ sơ tự mở từ phiếu chăm sóc phải liên hệ khách "
                         "và ghi nguyên văn khách yêu cầu gì trước khi đóng")
    if (data.get("khach_chap_nhan") or c.khach_chap_nhan) != "co":
        raise ValueError("Khách chưa chấp nhận phương án thì hồ sơ chưa được đóng")
    pr_id = data.get("payment_request_id", c.payment_request_id)
    _kiem_chung_tu_hoan_tien(db, c, huong, pr_id)
    if c.level == 3:
        if u.role not in DONG_MUC3:
            raise PermissionError("Hồ sơ mức 3 chỉ Ban TGĐ hoặc Phó TGĐ phụ trách được ký đóng")
        if u.username == c.handler:
            raise PermissionError("Hồ sơ mức 3 không cho một người vừa xử lý vừa đóng – phải người khác ký")
    ky = [x for x in (c.closed_by or "").split(",") if x]
    if u.username in ky: raise ValueError("Bạn đã ký hồ sơ này rồi – cần chữ ký của người thứ hai")
    ky.append(u.username)
    c.huong_xu_ly = huong; c.nguyen_nhan_nhom = nn_nhom
    c.nguyen_nhan = data.get("nguyen_nhan") or c.nguyen_nhan
    c.de_nghi_khach = de_nghi; c.khach_chap_nhan = "co"
    c.payment_request_id = pr_id; c.closed_by = ",".join(ky)
    can = 2 if c.level == 3 else 1
    if len(ky) >= can:
        c.status = "da_dong"; c.closed_at = datetime.now()
    R.audit(db, u.username, u.role, "dong_khieu_nai" if len(ky) >= can else "ky_dong_khieu_nai",
            f"complaint:{c.code}", after={"huong": huong, "nguyen_nhan": nn_nhom, "du_chu_ky": len(ky) >= can})
    db.commit(); db.refresh(c)
    return c


def tai_mo(db: Session, u: User, c: Complaint, ly_do: str) -> Complaint:
    if c.status != "da_dong": raise ValueError("Chỉ tái mở được hồ sơ đã đóng")
    if not (ly_do or "").strip(): raise ValueError("Phải ghi lý do tái mở")
    c.status = "tai_mo"; c.reopen_reason = ly_do.strip()[:300]; c.closed_at = None; c.closed_by = ""
    c.khach_chap_nhan = ""
    R.audit(db, u.username, u.role, "tai_mo_khieu_nai", f"complaint:{c.code}", after={"ly_do": c.reopen_reason})
    db.commit(); db.refresh(c)
    return c


def chuyen_trang_thai(db: Session, u: User, c: Complaint, moi: str) -> Complaint:
    if moi not in KN_TRANG_THAI: raise ValueError("Trạng thái không hợp lệ")
    if moi == "da_dong": raise ValueError("Đóng hồ sơ phải qua biểu mẫu đóng – có nguyên nhân, hướng xử lý và xác nhận của khách")
    if moi not in CHUYEN.get(c.status, ()):
        raise ValueError(f"Không chuyển thẳng từ '{KN_TRANG_THAI[c.status]}' sang '{KN_TRANG_THAI[moi]}'")
    truoc = c.status; c.status = moi
    if moi == "dang_xu_ly" and not c.handler: c.handler = u.username
    R.audit(db, u.username, u.role, "chuyen_trang_thai_khieu_nai", f"complaint:{c.code}",
            before={"trang_thai": truoc}, after={"trang_thai": moi})
    db.commit(); db.refresh(c)
    return c


def chi_so(db: Session) -> dict:
    """Bảng số của màn hình. Cộng bằng SQL – không nạp cả bảng hồ sơ vào bộ nhớ."""
    dang_mo = ["moi", "dang_xu_ly", "cho_khach", "tai_mo"]
    tong = int(db.execute(select(func.count()).select_from(Complaint)).scalar() or 0)
    mo = int(db.execute(select(func.count()).select_from(Complaint).where(Complaint.status.in_(dang_mo))).scalar() or 0)
    qua_han = int(db.execute(select(func.count()).select_from(Complaint).where(
        Complaint.status.in_(dang_mo), Complaint.first_response_at.is_(None),
        Complaint.han_phan_hoi < datetime.now())).scalar() or 0)
    theo_muc = {int(k): int(n) for k, n in db.execute(
        select(Complaint.level, func.count()).where(Complaint.status.in_(dang_mo)).group_by(Complaint.level)).all()}
    theo_nhom = [{"nhom": k, "ten": KN_NHOM.get(k, k), "so": int(n)} for k, n in db.execute(
        select(Complaint.nhom, func.count()).group_by(Complaint.nhom).order_by(desc(func.count()))).all()]
    return {"tong": tong, "dang_mo": mo, "qua_han_chua_phan_hoi": qua_han,
            "theo_muc": theo_muc, "theo_nhom": theo_nhom}


# ====================== ĐỢT 4: CHĂM SÓC SAU BÁN ======================
def sinh_phieu(db: Session, tour_id: int | None = None) -> int:
    """Sinh phiếu chăm sóc cho mọi booking chưa huỷ của các tour vừa kết thúc.

    Chạy được nhiều lần: mỗi booking chỉ một phiếu (cột booking_id là duy nhất), nên gọi lại không sinh
    trùng. Đây là hàm robot gọi, không phải nút người bấm.

    CHỈ lấy tour kết thúc trong khoảng lùi gần đây (tham số `cham_soc_lui_ngay`). Không có giới hạn này
    thì lần chạy đầu tiên sẽ mở phiếu cho TOÀN BỘ lịch sử chuyến đã đóng – hàng nghìn việc, tất cả đều
    đã quá hạn liên hệ ngay từ lúc sinh ra. Một danh sách như thế không ai làm, và nó phá luôn chính con
    số "bao nhiêu phiếu chưa ai đụng tới" mà màn hình này dùng để đo việc chăm sóc có làm thật hay không.
    Gọi kèm `tour_id` thì bỏ qua giới hạn – đó là lúc có người chủ động xin bù phiếu cho một chuyến cũ.

    Hạn liên hệ đếm từ NGÀY MUỘN HƠN giữa ngày kết thúc chuyến và hôm nay. Đếm từ ngày kết thúc chuyến
    thôi thì phiếu của chuyến đóng cách đây 20 ngày sinh ra đã trễ 17 ngày – không ai liên hệ được với
    khách trước khi phiếu tồn tại, nên đó là món nợ hệ thống tự bịa ra rồi tự đi đòi.
    """
    han_ngay = int(R.get_param(db, "cham_soc_han_ngay") or 3)
    q = select(Tour).where(Tour.status == "ket_thuc")
    if tour_id:
        q = q.where(Tour.id == tour_id)
    else:
        lui = int(R.get_param(db, "cham_soc_lui_ngay") or 30)
        q = q.where(Tour.end_date >= date.today() - timedelta(days=lui))
    tours = {t.id: t for t in db.execute(q).scalars()}
    if not tours: return 0
    da_co = {x for x in db.execute(select(CareTicket.booking_id).where(
        CareTicket.tour_id.in_(list(tours)))).scalars()}
    n = 0
    for b in db.execute(select(Booking).where(Booking.tour_id.in_(list(tours)),
                                              Booking.cancelled == False)).scalars():
        if b.id in da_co: continue
        t = tours[b.tour_id]
        db.add(CareTicket(booking_id=b.id, tour_id=b.tour_id, customer_name=b.customer_name,
                          customer_phone=b.customer_phone, owner_id=b.sales_id,
                          han_lien_he=max(t.end_date or date.today(), date.today()) + timedelta(days=han_ngay),
                          company_id=b.company_id, status="moi"))
        n += 1
    if n: db.commit()
    return n


def va_han_lien_he(db: Session) -> int:
    """Đẩy lại hạn cho những phiếu chăm sóc sinh ra đã quá hạn.

    Chỉ chạm phiếu còn nguyên trạng "moi" và có hạn sớm hơn chính ngày phiếu được tạo. Không ai liên hệ
    được với khách trước khi phiếu tồn tại, nên một hạn như vậy là lỗi của hệ thống chứ không phải việc
    trễ của người – và mọi cảnh báo dựng trên nó đều là báo động giả. Phiếu ai đó đã đụng vào thì để
    nguyên: hạn của nó là việc thật, sửa đi là xoá dấu vết trễ có thật.
    """
    han_ngay = int(R.get_param(db, "cham_soc_han_ngay") or 3)
    n = 0
    for t in db.execute(select(CareTicket).where(CareTicket.status == "moi")).scalars():
        sinh = (t.created_at or datetime.now()).date()
        if t.han_lien_he and t.han_lien_he >= sinh: continue
        t.han_lien_he = sinh + timedelta(days=han_ngay)
        n += 1
    if n: db.commit()
    return n


def ghi_ket_qua(db: Session, u: User, t: CareTicket, data: dict) -> tuple[CareTicket, list[str]]:
    """Nhân viên chỉ ghi KẾT QUẢ. Trả về (phiếu, danh sách việc hệ thống tự sinh kèm theo)."""
    lh = data.get("lien_he_duoc") or ""
    if lh not in ("co", "khong", "hen_lai"): raise ValueError("Phải trả lời đã liên hệ được hay chưa")
    ht = data.get("hinh_thuc") or ""
    if ht not in CS_HINH_THUC: raise ValueError(f"Hình thức liên hệ không hợp lệ. Chỉ nhận: {', '.join(CS_HINH_THUC)}")
    diem = data.get("diem_chua_hai_long") or []
    la = [x for x in diem if x not in CS_DIEM]
    if la: raise ValueError(f"Điểm chưa hài lòng không hợp lệ: {', '.join(la)}")
    sinh: list[str] = []
    if lh == "khong":
        if not (data.get("ly_do_khong") or "").strip():
            raise ValueError("Không liên hệ được thì phải ghi lý do – đánh dấu cho xong là làm hỏng chính con số này")
        t.ly_do_khong = data["ly_do_khong"].strip()[:300]; t.status = "khong_lien_he_duoc"
    elif lh == "hen_lai":
        t.status = "hen_lai"
    else:
        hl = int(data.get("hai_long") or 0)
        if hl < 1 or hl > 5: raise ValueError("Liên hệ được thì phải chấm mức hài lòng từ 1 đến 5")
        if data.get("nhu_cau_tiep") not in ("co", "khong"):
            raise ValueError("Phải trả lời khách có nhu cầu đi tiếp hay không")
        if data.get("dong_y_dung_danh_gia") not in ("co", "khong"):
            raise ValueError("Phải hỏi khách có đồng ý cho dùng đánh giá hay không – chưa đồng ý thì tuyệt đối "
                             "không đưa lời khách lên kênh truyền thông")
        t.hai_long = hl; t.nhu_cau_tiep = data["nhu_cau_tiep"]
        t.dong_y_dung_danh_gia = data["dong_y_dung_danh_gia"]; t.status = "xong"
    t.hinh_thuc = ht; t.lien_he_duoc = lh; t.diem_chua_hai_long = diem
    t.ghi_chu = data.get("ghi_chu", t.ghi_chu); t.contacted_at = datetime.now(); t.updated_by = u.username
    db.flush()

    # Điểm thấp thì tự mở hồ sơ khiếu nại: khách đã nói không hài lòng mà không ai lập hồ sơ thì lời đó
    # chết ngay tại phiếu này. Ngưỡng nằm ở tham số chính sách.
    nguong = int(R.get_param(db, "cham_soc_hai_long_mo_kn") or 3)
    if t.lien_he_duoc == "co" and 0 < t.hai_long < nguong and not t.complaint_id:
        ten = ", ".join(CS_DIEM[x] for x in diem) or "không nêu cụ thể"
        # NGƯỜI XỬ LÝ là SALE ĐÃ BÁN, không phải người đang gõ. Trước hôm nay `handler` nhận
        # `u.username` — đúng khi người gõ là nhân viên chăm sóc gọi điện hộ, nhưng sai ngay khi
        # khách TỰ chấm điểm qua Zalo: lúc ấy `u` là tài khoản máy, và hồ sơ sẽ mang tên robot.
        ban = db.get(User, t.owner_id) if t.owner_id else None
        c = tao(db, u, {"source": "cham_soc", "customer_name": t.customer_name,
                        "customer_phone": t.customer_phone, "booking_id": t.booking_id,
                        "nhom": _nhom_tu_diem(diem), "level": 2,
                        "noi_dung": (f"Hồ sơ tự mở từ phiếu chăm sóc sau bán: khách chấm {t.hai_long}/5 điểm. "
                                     f"Điểm chưa hài lòng: {ten}." + (f" Ghi chú của nhân viên: {t.ghi_chu}" if t.ghi_chu else "")),
                        "handler": (ban.username if ban else u.username), "care_id": t.id}, tu_dong=True)
        t.complaint_id = c.id
        sinh.append(f"Đã mở hồ sơ khiếu nại {c.code} (khách chấm {t.hai_long}/5) – cần liên hệ khách ghi lại đề nghị của họ")
        # …và một VIỆC CÓ CHỦ, CÓ HẠN đi kèm. Hồ sơ khiếu nại là nơi GHI; cảnh báo có chủ là thứ
        # làm cho ai đó thật sự cầm lấy nó. Thiếu cái thứ hai thì hồ sơ nằm trong một danh sách
        # mà không ai coi là việc của mình.
        gio = float(R.get_param(db, "cham_soc_goi_lai_gio") or 24)
        if giao_viec(db, "cham_soc_diem_thap", c.code,
                     f"Khách {t.customer_name} chấm {t.hai_long}/5 cho chuyến – gọi lại trong {gio:.0f} giờ "
                     f"và ghi lại đề nghị của khách vào hồ sơ {c.code}",
                     nguoi_id=(ban.id if ban else None), han_gio=gio,
                     roles="tp_kd,gd_kd,ptgd_mkt", level="red" if t.hai_long <= 2 else "warn"):
            sinh.append(f"Đã giao việc gọi lại trong {gio:.0f} giờ cho "
                        + (ban.full_name if ban else "Trưởng phòng Kinh doanh (phiếu chưa có người phụ trách)"))

    # Khách còn nhu cầu thì tự tạo lead khách cũ, gắn đúng nhân viên đã bán.
    if t.lien_he_duoc == "co" and t.nhu_cau_tiep == "co" and not t.lead_id and (t.customer_phone or "").strip():
        l = Lead(phone=t.customer_phone, name=t.customer_name, channel="khach_cu",
                 lead_month=f"{date.today():%Y-%m}", sales_id=t.owner_id, status="moi",
                 interest=(t.ghi_chu or "")[:200], note=f"Sinh từ phiếu chăm sóc sau bán #{t.id}",
                 created_by=u.username)
        db.add(l); db.flush(); t.lead_id = l.id
        sinh.append(f"Đã tạo lead khách cũ #{l.id} cho {t.customer_name}")

    R.audit(db, u.username, u.role, "ghi_phieu_cham_soc", f"care:{t.id}",
            after={"lien_he": lh, "hai_long": t.hai_long, "sinh_them": sinh})
    db.commit(); db.refresh(t)
    return t, sinh


def _nhom_tu_diem(diem: list) -> str:
    """Điểm chưa hài lòng → nhóm vấn đề của hồ sơ khiếu nại. Chỉ ánh xạ những cặp một-một rõ ràng;
    còn lại để 'chất lượng dịch vụ' cho người xử lý phân loại lại, chứ không đoán hộ."""
    anh_xa = {"hdv": "hdv", "xe": "xe", "khach_san": "luu_tru", "an_uong": "an_uong", "gia": "tien"}
    for d in diem:
        if d in anh_xa: return anh_xa[d]
    return "chat_luong"


def chi_so_cham_soc(db: Session) -> dict:
    tong = int(db.execute(select(func.count()).select_from(CareTicket)).scalar() or 0)
    da_ghi = int(db.execute(select(func.count()).select_from(CareTicket)
                            .where(CareTicket.status.in_(["xong", "khong_lien_he_duoc"]))).scalar() or 0)
    lien_he_duoc = int(db.execute(select(func.count()).select_from(CareTicket)
                                  .where(CareTicket.lien_he_duoc == "co")).scalar() or 0)
    qua_han = int(db.execute(select(func.count()).select_from(CareTicket)
                             .where(CareTicket.status.in_(["moi", "hen_lai"]),
                                    CareTicket.han_lien_he < date.today())).scalar() or 0)
    tb = db.execute(select(func.avg(CareTicket.hai_long)).where(CareTicket.hai_long > 0)).scalar()
    lead_moi = int(db.execute(select(func.count()).select_from(CareTicket)
                              .where(CareTicket.lead_id.isnot(None))).scalar() or 0)
    kn_moi = int(db.execute(select(func.count()).select_from(CareTicket)
                            .where(CareTicket.complaint_id.isnot(None))).scalar() or 0)
    theo_diem = [{"diem": k, "ten": CS_DIEM.get(k, k)} for k in CS_DIEM]
    return {"tong_phieu": tong, "da_ghi": da_ghi, "chua_ghi": tong - da_ghi,
            "lien_he_duoc": lien_he_duoc, "ty_le_lien_he": (lien_he_duoc / da_ghi) if da_ghi else 0,
            "qua_han": qua_han, "hai_long_tb": round(float(tb), 2) if tb else 0,
            "lead_khach_cu": lead_moi, "khieu_nai_tu_mo": kn_moi, "danh_muc_diem": theo_diem}


# ====================== ROBOT ======================
def robot_cskh(db: Session) -> dict:
    """Sinh phiếu chăm sóc cho tour vừa kết thúc và cảnh báo khiếu nại quá hạn phản hồi.

    Leo thang theo mức độ: mức 1–2 lên trưởng bộ phận, mức 3 lên thẳng Ban TGĐ. Quá hạn mà im lặng là
    cách một khiếu nại mức 3 trở thành một bài báo.
    """
    n_phieu = sinh_phieu(db)
    n_va = va_han_lien_he(db)
    n_moi_cham, n_nhac = gui_loi_moi_cham_diem(db), nhac_chua_tra_loi(db)
    them = 0

    def add(kind, level, ref, msg, roles, nguoi_id=None, han_gio=None):
        nonlocal them
        if giao_viec(db, kind, ref, msg, nguoi_id=nguoi_id, han_gio=han_gio,
                     roles=roles, level=level) is not None:
            them += 1

    bay_gio = datetime.now()
    for c in db.execute(select(Complaint).where(Complaint.status.in_(["moi", "dang_xu_ly", "cho_khach", "tai_mo"]),
                                                Complaint.first_response_at.is_(None))).scalars():
        if not c.han_phan_hoi or c.han_phan_hoi >= bay_gio: continue
        tre = int((bay_gio - c.han_phan_hoi).total_seconds() // 3600)
        vai = "ptgd_mkt,gd_kd,tp_dh" if c.level < 3 else "ptgd_mkt,tgd,chutich"
        # Chủ của việc này là NGƯỜI ĐANG GIỮ HỒ SƠ. `handler` là tên đăng nhập dạng chữ chứ không
        # phải khoá ngoại, nên phải tra ra; tra không thấy thì để trống — và ô trống ấy đếm được.
        nguoi = db.execute(select(User).where(User.username == c.handler)).scalars().first() if c.handler else None
        add("kn_qua_han", "red" if c.level >= 2 else "warn", c.code,
            f"Khiếu nại {c.code} ({KN_MUC[c.level]}) của khách {c.customer_name} đã quá hạn phản hồi {tre} giờ – chưa ai trả lời khách",
            vai, nguoi_id=(nguoi.id if nguoi else None), han_gio=None)
    # Phiếu chăm sóc quá hạn liên hệ: nhắc chính nhân viên đã bán, gom một cảnh báo cho mỗi tour để
    # không dội hàng trăm dòng cho một chuyến đông khách.
    con_qua_han = set()
    for tid, so in db.execute(select(CareTicket.tour_id, func.count()).where(
            CareTicket.status.in_(["moi", "hen_lai"]), CareTicket.han_lien_he < date.today())
            .group_by(CareTicket.tour_id)).all():
        con_qua_han.add(f"cs:{tid}")
        t = db.get(Tour, tid)
        add("cham_soc_qua_han", "warn", f"cs:{tid}",
            f"{so} phiếu chăm sóc sau bán của chuyến {t.code if t else tid} đã quá hạn liên hệ", "gd_kd,tp_kd,ptgd_mkt")
    # Chuyến đã liên hệ xong – hoặc phiếu vừa được vá lại hạn – thì gỡ cảnh báo cũ xuống. Cảnh báo chỉ
    # thêm mà không bao giờ tự rút thì bảng cảnh báo dài mãi, và người ta thôi đọc nó.
    go = 0
    for a in db.execute(select(Alert).where(Alert.kind == "cham_soc_qua_han",
                                            Alert.resolved == False)).scalars():
        if a.ref not in con_qua_han:
            a.resolved = True; go += 1
    if them or go: db.commit()
    return {"phieu_moi": n_phieu, "phieu_va_han": n_va, "canh_bao_moi": them, "canh_bao_go": go,
            "moi_cham_diem": n_moi_cham, "nhac_lai": n_nhac}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# GỬI LỜI MỜI CHẤM ĐIỂM — đề xuất tự động hoá CSKH 25/9/2026, bước 1 và bước 6
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _gio_gui_toi(db: Session) -> datetime:
    """Lần tới giờ gửi. Hôm nay chưa qua giờ ấy thì hôm nay, qua rồi thì sáng mai.

    KHÔNG gửi ngay lúc phiếu sinh ra: phiếu sinh lúc nào là tuỳ vòng quét, và một tin chăm sóc
    đến lúc 2 giờ sáng làm hỏng đúng thiện chí mà nó đi xin.
    """
    gio = int(R.get_param(db, "khao_sat_gio_gui") or 9)
    bay_gio = datetime.now()
    hom_nay = bay_gio.replace(hour=max(0, min(23, gio)), minute=0, second=0, microsecond=0)
    return hom_nay if hom_nay > bay_gio else hom_nay + timedelta(days=1)


def gui_loi_moi_cham_diem(db: Session, limit: int = 200) -> int:
    """Phiếu chăm sóc chưa có mã khảo sát → sinh mã và XẾP HÀNG một tin ZNS.

    Không gọi Zalo trực tiếp: chỉ xếp vào hàng đợi đã có (`zalo.queue`), để mọi luật gửi, làm mới
    token, ghi sổ lỗi và gửi lại đều dùng chung một đường. Một chỗ gửi thứ hai là một chỗ nữa phải
    nhớ xử lý token chết.

    Phiếu KHÔNG có số điện thoại thì bỏ qua và KHÔNG sinh mã — sinh mã cho một phiếu không gửi
    được là tạo ra một con số "đã mời" không có thật, và tỷ lệ trả lời sẽ bị chia cho nó.
    """
    from app.models.danh_gia import MaKhaoSat
    from app.services import danh_gia as DG
    from app.services import zalo as Z

    da_co = {x for x in db.execute(select(MaKhaoSat.care_id)).scalars()}
    hen = _gio_gui_toi(db)
    n = 0
    for t in db.execute(select(CareTicket).where(
            CareTicket.status == "moi").order_by(CareTicket.id).limit(limit)).scalars():
        if t.id in da_co: continue
        if not (t.customer_phone or "").strip(): continue
        m = DG.sinh_ma(db, t)
        tour = db.get(Tour, t.tour_id)
        Z.queue(db, "robot_cskh", phone=t.customer_phone, purpose="cham_soc",
                params={"ten_khach": t.customer_name, "ten_tour": (tour.name if tour else ""),
                        "ma_khao_sat": m.ma},
                booking_id=t.booking_id, gui_tu_luc=hen)
        n += 1
    if n: db.commit()
    return n


def nhac_chua_tra_loi(db: Session, limit: int = 200) -> int:
    """Bước 6: không trả lời sau hạn thì nhắc MỘT lần. Một lần, và không gọi điện.

    "Một lần" là luật, không phải lời khuyên — nên nó được đo bằng chính sổ tin: đã có tin nhắc
    cho phiếu này thì thôi. Không dựng thêm cột "đã nhắc" trên phiếu: một sự thật hai nơi giữ thì
    rồi sẽ lệch, và nơi đúng để hỏi "đã gửi gì cho khách này" là sổ tin.
    """
    from app.models.crm import ZaloMessage
    from app.models.danh_gia import MaKhaoSat
    from app.services import zalo as Z

    gio = float(R.get_param(db, "khao_sat_nhac_gio") or 48)
    moc = datetime.now() - timedelta(hours=gio)
    n = 0
    for m in db.execute(select(MaKhaoSat).where(
            MaKhaoSat.dung_luc.is_(None), MaKhaoSat.het_han > datetime.now(),
            MaKhaoSat.tao_luc <= moc).order_by(MaKhaoSat.id).limit(limit)).scalars():
        t = db.get(CareTicket, m.care_id)
        if not t or not (t.customer_phone or "").strip(): continue
        da_nhac = db.execute(select(func.count()).select_from(ZaloMessage).where(
            ZaloMessage.booking_id == t.booking_id,
            ZaloMessage.purpose == "cham_soc_nhac")).scalar() or 0
        if da_nhac: continue
        tour = db.get(Tour, t.tour_id)
        Z.queue(db, "robot_cskh", phone=t.customer_phone, purpose="cham_soc_nhac",
                params={"ten_khach": t.customer_name, "ten_tour": (tour.name if tour else ""),
                        "ma_khao_sat": m.ma},
                booking_id=t.booking_id, gui_tu_luc=_gio_gui_toi(db))
        n += 1
    if n: db.commit()
    return n
