"""Chiến dịch marketing – trục nối tiền, khách và doanh thu (Đợt 1, đề xuất 07/9/2026 đã duyệt).

Nguyên tắc của tệp này: KHÔNG có ô nào cho người dùng gõ "đã chi bao nhiêu" hay "thu về bao nhiêu".
Chi phí đọc từ đề nghị chi đã duyệt, lead đọc từ bảng lead, doanh thu đọc từ booking đã chốt. Hai nơi
giữ hai con số của cùng một việc là hai con số sẽ lệch nhau, và không ai biết tin con số nào.
"""
from datetime import date, datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.core import User, Booking
from app.models.crm import Lead
from app.models.ops import PaymentRequest
from app.models.marketing import Campaign, CAMPAIGN_STATUS, MUC_TIEU, KENH
from app.services import rules as R
from app.api.deps import toan_quyen_ke_ca_tach_bach   # công tắc chu_tich_mo_het_cua

# Chuyển trạng thái hợp lệ. Không cho nhảy cóc: mỗi bước là một quyết định có người chịu trách nhiệm.
CHUYEN = {"nhap": ("cho_duyet",), "cho_duyet": ("dang_chay", "nhap"),
          "dang_chay": ("tam_dung", "ket_thuc"), "tam_dung": ("dang_chay", "ket_thuc"),
          "ket_thuc": ("da_danh_gia",), "da_danh_gia": ()}
DUYET = ("ptgd_mkt", "tgd", "chutich")      # ai được đưa chiến dịch vào chạy


def next_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(Campaign)).scalar() + 1
    return f"CD{date.today():%y%m}-{n:02d}"


def kiem_du_lieu(d: dict) -> None:
    if d.get("objective") not in MUC_TIEU: raise ValueError(f"Mục tiêu không hợp lệ. Chỉ nhận: {', '.join(MUC_TIEU)}")
    if d.get("mang") not in ("le", "doan"): raise ValueError("Mảng kinh doanh phải là 'le' hoặc 'doan'")
    kenh = d.get("channels") or []
    if not kenh: raise ValueError("Phải chọn ít nhất một kênh triển khai")
    la = [k for k in kenh if k not in KENH]
    if la: raise ValueError(f"Kênh không hợp lệ: {', '.join(la)}")
    if d.get("objective") == "ban_tour" and not d.get("product_id"):
        raise ValueError("Mục tiêu 'Bán tour cụ thể' phải chọn sản phẩm – không có sản phẩm thì không quy được doanh thu")
    if (d.get("budget") or 0) <= 0: raise ValueError("Ngân sách duyệt phải lớn hơn 0")
    if (d.get("target_leads") or 0) <= 0 and (d.get("target_bookings") or 0) <= 0:
        raise ValueError("Phải có chỉ tiêu lead hoặc chỉ tiêu booking – không có chỉ tiêu thì không đánh giá được")
    if d.get("to_date") and d.get("from_date") and d["to_date"] < d["from_date"]:
        raise ValueError("Đến ngày không được trước Từ ngày")


def tao(db: Session, u: User, data: dict) -> Campaign:
    """Lập chiến dịch. Bản do AI đề xuất LUÔN dừng ở nháp, dù người gọi có quyền duyệt.

    Cùng nguyên tắc đã áp cho AI trả lời khách ở hộp thư: AI đề xuất, người quyết. Một tờ trình chi tiền
    do máy tự lập rồi tự đưa vào chạy là bỏ mất đúng chỗ mà con người cần có mặt.
    """
    d = dict(data); nguon = (d.pop("nguon_tao", "") or "nguoi").lower()
    if nguon not in ("nguoi", "ai"): raise ValueError("Nguồn tạo chỉ nhận 'nguoi' hoặc 'ai'")
    kiem_du_lieu(d)
    if nguon == "ai" and not (d.get("ai_ghi_chu") or "").strip():
        raise ValueError("Đề xuất do AI lập phải ghi căn cứ – không có căn cứ thì người duyệt không kiểm được gì")
    c = Campaign(code=next_code(db), nguon_tao=nguon, status="nhap", created_by=u.username, **d)
    db.add(c); db.flush()
    R.audit(db, u.username, u.role, "tao_chien_dich", f"campaign:{c.code}",
            after={"ten": c.name, "ngan_sach": c.budget, "nguon": nguon})
    db.commit(); db.refresh(c)
    return c


def chuyen_trang_thai(db: Session, u: User, c: Campaign, moi: str, danh_gia: str = "") -> Campaign:
    if moi not in CAMPAIGN_STATUS: raise ValueError("Trạng thái không hợp lệ")
    if moi not in CHUYEN.get(c.status, ()):
        raise ValueError(f"Không chuyển thẳng từ '{CAMPAIGN_STATUS[c.status]}' sang '{CAMPAIGN_STATUS[moi]}'")
    if moi == "dang_chay":
        if u.role not in DUYET: raise PermissionError("Chỉ PTGĐ Marketing, TGĐ hoặc Chủ tịch được đưa chiến dịch vào chạy")
        # Người trình không tự duyệt tờ trình của chính mình.
        if c.created_by == u.username:
            raise PermissionError("Người lập chiến dịch không được tự duyệt – phải người khác trong nhóm có thẩm quyền")
        c.approved_by = u.username; c.approved_at = datetime.now()
    if moi == "da_danh_gia":
        if not (danh_gia or c.evaluation or "").strip():
            raise ValueError("Phải ghi đánh giá kết thúc trước khi đóng chiến dịch – đây là chỗ tích luỹ kinh nghiệm cho kỳ sau")
        if danh_gia: c.evaluation = danh_gia
    truoc = c.status; c.status = moi
    R.audit(db, u.username, u.role, "chuyen_trang_thai_chien_dich", f"campaign:{c.code}",
            before={"trang_thai": truoc}, after={"trang_thai": moi})
    db.commit(); db.refresh(c)
    return c


def ket_qua(db: Session, c: Campaign) -> dict:
    """Kết quả chiến dịch – cộng bằng SQL, không nạp lead/booking vào bộ nhớ."""
    so_lead = db.execute(select(func.count()).select_from(Lead).where(Lead.campaign_id == c.id)).scalar() or 0
    chuyen_doi = db.execute(select(func.count()).select_from(Lead)
                            .where(Lead.campaign_id == c.id, Lead.booking_id.isnot(None))).scalar() or 0
    chi_phi = float(db.execute(select(func.coalesce(func.sum(PaymentRequest.amount), 0.0))
                               .where(PaymentRequest.campaign_id == c.id,
                                      PaymentRequest.status == "da_chi")).scalar() or 0)
    treo = float(db.execute(select(func.coalesce(func.sum(PaymentRequest.amount), 0.0))
                            .where(PaymentRequest.campaign_id == c.id,
                                   PaymentRequest.status.in_(["cho_tp", "cho_kt", "cho_duyet", "cho_chi"]))).scalar() or 0)
    doanh_thu = float(db.execute(
        select(func.coalesce(func.sum(func.coalesce(Booking.amount, 0) - func.coalesce(Booking.discount, 0)), 0.0))
        .join(Lead, Lead.booking_id == Booking.id)
        .where(Lead.campaign_id == c.id, Booking.cancelled == False)).scalar() or 0)
    return {"so_lead": int(so_lead), "chuyen_doi": int(chuyen_doi),
            "ty_le_chuyen_doi": (chuyen_doi / so_lead) if so_lead else 0,
            "chi_phi": chi_phi, "chi_phi_treo": treo, "con_lai_ngan_sach": (c.budget or 0) - chi_phi - treo,
            "chi_phi_moi_lead": (chi_phi / so_lead) if so_lead else 0,
            "chi_phi_moi_booking": (chi_phi / chuyen_doi) if chuyen_doi else 0,
            "doanh_thu": doanh_thu, "hieu_qua": (doanh_thu / chi_phi) if chi_phi else 0,
            "dat_chi_tieu_lead": (so_lead >= c.target_leads) if c.target_leads else None,
            "dat_chi_tieu_booking": (chuyen_doi >= c.target_bookings) if c.target_bookings else None,
            # Vượt ngân sách nói ra ngay, không đợi tới lúc quyết toán.
            "vuot_ngan_sach": (chi_phi + treo) > (c.budget or 0)}


def lead_chua_gan(db: Session, thang: str = "") -> dict:
    """Lead chưa gắn chiến dịch, gom theo ô chữ campaign cũ – để Marketing gán dần chứ không đoán hộ."""
    q = select(Lead.campaign, func.count()).where(Lead.campaign_id.is_(None))
    if thang: q = q.where(Lead.lead_month == thang)
    rows = db.execute(q.group_by(Lead.campaign).order_by(func.count().desc())).all()
    return {"tong": sum(int(n) for _, n in rows),
            "nhom": [{"campaign_cu": (t or "(không ghi)"), "so_lead": int(n)} for t, n in rows]}


# ====================== ĐỢT 2: KẾ HOẠCH & NGÂN SÁCH ======================
from app.models.marketing import MarketingBudget, MarketingBudgetLine, HANG_MUC, BUDGET_STATUS


def ky_hop_le(period: str) -> bool:
    """2026-09 (tháng) hoặc 2026-Q4 (quý). Năm cả năm dùng 4 quý – không mở thêm dạng kỳ thứ ba."""
    p = (period or "").strip()
    if len(p) != 7 and len(p) != 7: return False
    if p[4] != "-": return False
    if p[5] == "Q": return p[6] in "1234" and p[:4].isdigit()
    return p[5:].isdigit() and 1 <= int(p[5:]) <= 12 and p[:4].isdigit()


def thang_cua_ky(period: str) -> list[str]:
    """Các tháng YYYY-MM thuộc kỳ. Kỳ quý trải ra ba tháng để cộng chi phí cho đúng."""
    if period[5] == "Q":
        q = int(period[6]); return [f"{period[:4]}-{m:02d}" for m in range((q - 1) * 3 + 1, q * 3 + 1)]
    return [period]


def tao_ngan_sach(db: Session, u: User, data: dict) -> MarketingBudget:
    period = (data.get("period") or "").strip()
    if not ky_hop_le(period): raise ValueError("Kỳ phải dạng 2026-09 (tháng) hoặc 2026-Q4 (quý)")
    dong = data.get("lines") or []
    if not dong: raise ValueError("Phải có ít nhất một hạng mục chi")
    for l in dong:
        if l.get("hang_muc") not in HANG_MUC: raise ValueError(f"Hạng mục không hợp lệ: {l.get('hang_muc')}")
        if (l.get("amount") or 0) <= 0: raise ValueError("Số tiền dự toán từng hạng mục phải lớn hơn 0")
    # TC-77 · 23/9/2026 – LUẬT CŨ ĐƯỢC NỚI, ghi lại cả hai vế.
    #
    # CŨ : mỗi hạng mục chỉ được MỘT dòng trong một kỳ.
    # MỚI: mỗi (hạng mục × chiến dịch) một dòng.
    #
    # Vì sao phải nới: từ vòng này dòng chi gắn được chiến dịch, mà tháng 9 chi Facebook Ads 100
    # triệu cho chiến dịch A và 50 triệu cho chiến dịch B là HAI dòng cùng hạng mục — luật cũ
    # chặn đúng việc mà cột mới sinh ra để làm.
    #
    # Phần luật cũ VẪN CÒN NGUYÊN cho dòng không gắn chiến dịch: hai dòng "Facebook Ads" cùng để
    # trống chiến dịch vẫn bị chặn, vì đó đúng là trường hợp luật cũ nói tới — cùng một khoản chi
    # bị gõ hai lần. Xem test_tc77_luat_cu_duoc_noi_va_ghi_ca_hai_ve.
    khoa = [(l["hang_muc"], l.get("campaign_id")) for l in dong]
    if len(set(khoa)) != len(khoa):
        raise ValueError("Mỗi hạng mục chỉ được một dòng cho mỗi chiến dịch "
                         "(dòng không gắn chiến dịch thì mỗi hạng mục một dòng)")
    for l in dong:
        if l.get("campaign_id") is not None and db.get(Campaign, l["campaign_id"]) is None:
            raise ValueError(f"Không có chiến dịch id {l['campaign_id']}")
    if (data.get("target_leads") or 0) <= 0:
        raise ValueError("Phải có mục tiêu lead – không có mục tiêu thì không so được chi phí/lead kế hoạch với thực tế")
    if not (data.get("rationale") or "").strip():
        raise ValueError("Phải ghi căn cứ lập ngân sách – kỳ sau còn đối chiếu lại được")
    nguon = (data.get("nguon_tao") or "nguoi").lower()
    if nguon == "ai" and not (data.get("ai_ghi_chu") or "").strip():
        raise ValueError("Bản do AI lập phải ghi căn cứ đề xuất")
    # Một kỳ × một pháp nhân chỉ có MỘT ngân sách còn hiệu lực. Hai bản cùng hiệu lực là hai hạn mức
    # khác nhau cho cùng một kỳ, và cổng vượt dự toán sẽ so với bản nào cũng đúng – tức là vô nghĩa.
    trung = db.execute(select(MarketingBudget).where(
        MarketingBudget.period == period, MarketingBudget.company_id == data.get("company_id"),
        MarketingBudget.status.in_(["cho_duyet", "hieu_luc"]))).scalars().first()
    if trung: raise ValueError(f"Kỳ {period} của pháp nhân này đã có ngân sách {BUDGET_STATUS[trung.status].lower()} (mã {trung.id})")
    b = MarketingBudget(period=period, company_id=data.get("company_id"), target_leads=data.get("target_leads") or 0,
                        target_revenue=data.get("target_revenue") or 0, rationale=data["rationale"],
                        nguon_tao=nguon, ai_ghi_chu=data.get("ai_ghi_chu", ""), status="nhap", created_by=u.username)
    db.add(b); db.flush()
    for l in dong:
        db.add(MarketingBudgetLine(budget_id=b.id, hang_muc=l["hang_muc"], amount=float(l["amount"]),
                                   note=l.get("note", ""), campaign_id=l.get("campaign_id")))
    R.audit(db, u.username, u.role, "lap_ngan_sach_marketing", f"mkt_budget:{b.id}",
            after={"ky": period, "so_hang_muc": len(dong), "tong": sum(float((l["amount"] or 0)) for l in dong), "nguon": nguon})
    db.commit(); db.refresh(b)
    return b


def duyet_ngan_sach(db: Session, u: User, b: MarketingBudget) -> MarketingBudget:
    if b.status == "hieu_luc": raise ValueError("Ngân sách đã hiệu lực")
    if b.created_by == u.username:
        raise PermissionError("Người lập ngân sách không được tự duyệt – phải người khác có thẩm quyền")
    if u.role not in ("tgd", "chutich"):
        raise PermissionError("Chỉ TGĐ hoặc Chủ tịch duyệt ngân sách marketing")
    b.status = "hieu_luc"; b.approved_by = u.username; b.approved_at = datetime.now()
    R.audit(db, u.username, u.role, "duyet_ngan_sach_marketing", f"mkt_budget:{b.id}", after={"ky": b.period})
    db.commit(); db.refresh(b)
    return b


def _khoang_ngay(period: str) -> tuple[datetime, datetime]:
    """Mốc đầu và mốc sau-cuối của kỳ. So bằng khoảng ngày chứ không cắt chuỗi ngày tháng:
    cắt chuỗi phụ thuộc cách từng cơ sở dữ liệu định dạng ngày, và sẽ im lặng trả về 0 khi khác định dạng."""
    y = int(period[:4])
    if period[5] == "Q":
        q = int(period[6]); m1 = (q - 1) * 3 + 1
        dau = datetime(y, m1, 1)
        sau = datetime(y + 1, 1, 1) if q == 4 else datetime(y, m1 + 3, 1)
    else:
        m = int(period[5:]); dau = datetime(y, m, 1)
        sau = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
    return dau, sau


def _chi_theo_muc(db: Session, period: str, company_id: int | None) -> dict:
    """Đã chi và đang treo của kỳ, tách theo hạng mục. Đọc từ đề nghị chi – không có đường nào khác."""
    dau, sau = _khoang_ngay(period)
    q = (select(PaymentRequest.marketing_muc, PaymentRequest.status,
                func.coalesce(func.sum(PaymentRequest.amount), 0.0))
         .where(PaymentRequest.category == "marketing",
                PaymentRequest.created_at >= dau, PaymentRequest.created_at < sau))
    if company_id: q = q.where(PaymentRequest.company_id == company_id)
    rows = db.execute(q.group_by(PaymentRequest.marketing_muc, PaymentRequest.status)).all()
    da_chi: dict[str, float] = {}; treo: dict[str, float] = {}
    for muc, tt, tien in rows:
        d = da_chi if tt == "da_chi" else (treo if tt in ("cho_tp", "cho_kt", "cho_duyet", "cho_chi") else None)
        if d is None: continue          # từ chối thì không tính vào đâu cả
        k = muc or "_chua_phan_muc"
        d[k] = d.get(k, 0.0) + float(tien)
    return {"da_chi": da_chi, "treo": treo}


def chi_thuc_te(db: Session, period: str, company_id: int | None = None) -> dict:
    """Tiền ĐÃ CHI và ĐANG TREO của kỳ, tách theo TỪNG CHIẾN DỊCH.

    VÌ SAO TỆP NÀY MỌC THÊM HÀM — MỘT LỖI SỐ TIỀN ĐÃ LÊN MÀN HÌNH CHỦ TỊCH

    TC-77 (23/9/2026) nối `campaign_id` vào `mkt_budget_lines` rồi lấy `amount` của dòng ấy làm
    "chi thực tế" của chiến dịch. `amount` là DỰ TOÁN — tiền ĐỊNH tiêu. Cột trên màn hình Đóng góp
    doanh thu ghi "Chi thực tế" và ô "Thu / chi" chia doanh thu cho con số ấy, nên chiến dịch tiêu
    ít hơn kế hoạch thì hiệu quả hiện THẤP hơn sự thật, tiêu vượt thì hiện CAO hơn.

    Anh Tuấn chốt ngày 23/9 là "nối chi vào chiến dịch". Chi là ĐỀ NGHỊ CHI. Cột `campaign_id` của
    `payment_requests` đã có sẵn từ trước — vòng ấy nối nhầm bảng chứ không thiếu cột.

    CÙNG MỘT NGUỒN VỚI `_chi_theo_muc` NGAY TRÊN, và cố ý: màn hình Ngân sách đã đọc đề nghị chi để
    ra "đã chi / đang treo" theo hạng mục. Nếu hàm này đi lối khác thì hai màn hình cùng nói về một
    khoản tiền mà ra hai con số — đúng cái bệnh nhóm 2.8 sinh ra để chữa.

    KỲ TÍNH THEO NGÀY LẬP ĐỀ NGHỊ, không theo ngày chi. Giống hệt `_chi_theo_muc`, và phải giống:
    hai cách chia kỳ khác nhau thì bảng ngân sách và bảng hiệu quả lệch nhau ở tháng giao mùa mà
    không ai biết vì sao. Ngày chi nằm ở `paid_at` cho ai cần soát riêng.

    TỪ CHỐI KHÔNG TÍNH VÀO ĐÂU CẢ — không vào đã chi, không vào treo.

    RỖNG `campaign_id` NGHĨA LÀ CHƯA GẮN, KHÔNG PHẢI "CHI CHUNG". Phần ấy trả riêng ở
    `da_chi_chua_gan`, KHÔNG chia đều cho các chiến dịch: chia đều là bịa số.
    """
    dau, sau = _khoang_ngay(period)
    q = (select(PaymentRequest.campaign_id, PaymentRequest.status,
                func.coalesce(func.sum(PaymentRequest.amount), 0.0),
                func.count(PaymentRequest.id))
         .where(PaymentRequest.category == "marketing",
                PaymentRequest.created_at >= dau, PaymentRequest.created_at < sau))
    if company_id:
        q = q.where(PaymentRequest.company_id == company_id)
    rows = db.execute(q.group_by(PaymentRequest.campaign_id, PaymentRequest.status)).all()

    da_chi_cd: dict[int, float] = {}
    treo_cd: dict[int, float] = {}
    da_chi_chua_gan = treo_chua_gan = 0.0
    so_dong = 0
    for cd, tt, tien, dem in rows:
        if tt == "da_chi":
            d, chua = da_chi_cd, "da_chi"
        elif tt in ("cho_tp", "cho_kt", "cho_duyet", "cho_chi"):
            d, chua = treo_cd, "treo"
        else:
            continue                      # từ chối
        so_dong += int(dem or 0)
        if cd:
            d[cd] = d.get(cd, 0.0) + float(tien)
        elif chua == "da_chi":
            da_chi_chua_gan += float(tien)
        else:
            treo_chua_gan += float(tien)

    return {
        "da_chi_theo_chien_dich": da_chi_cd,
        "treo_theo_chien_dich": treo_cd,
        "da_chi_chua_gan": da_chi_chua_gan,
        "treo_chua_gan": treo_chua_gan,
        "da_chi_tong": float(sum(da_chi_cd.values())) + da_chi_chua_gan,
        "treo_tong": float(sum(treo_cd.values())) + treo_chua_gan,
        "so_dong": so_dong,
    }


def bang_ngan_sach(db: Session, b: MarketingBudget) -> dict:
    """Bảng theo dõi: dự toán – đã chi – đang treo – còn lại, theo từng hạng mục."""
    lines = list(db.execute(select(MarketingBudgetLine).where(MarketingBudgetLine.budget_id == b.id)).scalars())
    chi = _chi_theo_muc(db, b.period, b.company_id)
    rows = []
    for l in lines:
        dc = chi["da_chi"].get(l.hang_muc, 0.0); tr = chi["treo"].get(l.hang_muc, 0.0)
        rows.append({"hang_muc": l.hang_muc, "ten": HANG_MUC[l.hang_muc], "du_toan": l.amount,
                     "da_chi": dc, "dang_treo": tr, "con_lai": (l.amount or 0) - dc - tr,
                     "vuot": (dc + tr) > (l.amount or 0), "note": l.note})
    # Khoản chi marketing chưa ai gán hạng mục: nêu riêng, KHÔNG chia bừa vào các hạng mục đã có.
    chua = {"da_chi": chi["da_chi"].get("_chua_phan_muc", 0.0), "dang_treo": chi["treo"].get("_chua_phan_muc", 0.0)}
    # Hạng mục có chi nhưng không nằm trong ngân sách kỳ này – cũng phải nêu.
    ngoai = [{"hang_muc": k, "ten": HANG_MUC.get(k, k), "da_chi": chi["da_chi"].get(k, 0.0),
              "dang_treo": chi["treo"].get(k, 0.0)}
             for k in set(list(chi["da_chi"]) + list(chi["treo"]))
             if k != "_chua_phan_muc" and k not in {l.hang_muc for l in lines}]
    tong_du_toan = sum(r["du_toan"] for r in rows)
    tong_da_chi = sum(r["da_chi"] for r in rows) + chua["da_chi"] + sum(x["da_chi"] for x in ngoai)
    tong_treo = sum(r["dang_treo"] for r in rows) + chua["dang_treo"] + sum(x["dang_treo"] for x in ngoai)
    so_lead = _lead_trong_ky(db, b.period)
    return {"rows": rows, "chua_phan_muc": chua, "ngoai_ngan_sach": ngoai,
            "tong_du_toan": tong_du_toan, "tong_da_chi": tong_da_chi, "tong_treo": tong_treo,
            "tong_con_lai": tong_du_toan - tong_da_chi - tong_treo,
            "so_lead": so_lead,
            "chi_phi_lead_ke_hoach": (tong_du_toan / b.target_leads) if b.target_leads else 0,
            "chi_phi_lead_thuc_te": (tong_da_chi / so_lead) if so_lead else 0,
            "vuot_tong": (tong_da_chi + tong_treo) > tong_du_toan}


def _lead_trong_ky(db: Session, period: str) -> int:
    thang = thang_cua_ky(period)
    return int(db.execute(select(func.count()).select_from(Lead).where(Lead.lead_month.in_(thang))).scalar() or 0)


def con_lai_hang_muc(db: Session, muc: str, company_id: int | None, luc: date | None = None) -> tuple[float, str]:
    """Còn lại của một hạng mục ở kỳ đang hiệu lực – dùng cho cổng vượt dự toán khi lập đề nghị chi.

    Không có ngân sách hiệu lực thì trả về (0, lý do) và người gọi KHÔNG được coi đó là "còn nhiều".
    Chưa lập ngân sách không phải là ngân sách vô hạn.
    """
    hom_nay = luc or date.today()
    ung_vien = [f"{hom_nay:%Y-%m}", f"{hom_nay.year}-Q{(hom_nay.month - 1)//3 + 1}"]
    b = db.execute(select(MarketingBudget).where(MarketingBudget.period.in_(ung_vien),
                                                 MarketingBudget.status == "hieu_luc",
                                                 MarketingBudget.company_id == company_id)).scalars().first()
    if b is None:
        b = db.execute(select(MarketingBudget).where(MarketingBudget.period.in_(ung_vien),
                                                     MarketingBudget.status == "hieu_luc")).scalars().first()
    if b is None: return 0.0, "chưa có ngân sách marketing hiệu lực cho kỳ này"
    l = db.execute(select(MarketingBudgetLine).where(MarketingBudgetLine.budget_id == b.id,
                                                     MarketingBudgetLine.hang_muc == muc)).scalars().first()
    if l is None: return 0.0, f"ngân sách kỳ {b.period} không có hạng mục này"
    chi = _chi_theo_muc(db, b.period, b.company_id)
    con = (l.amount or 0) - chi["da_chi"].get(muc, 0.0) - chi["treo"].get(muc, 0.0)
    return con, f"ngân sách kỳ {b.period}"


# ====================== ĐỢT 5: NỘI DUNG & THƯƠNG HIỆU ======================
from app.models.marketing import ContentItem, ND_LOAI, ND_KENH, ND_TRANG_THAI

ND_SOAN = ("nv_mkt", "ptgd_mkt", "cntt")
ND_DUYET = ("ptgd_mkt", "tgd", "chutich", "hanh_chinh")     # hanh_chinh gồm pháp chế
# "cho_ky_2" phải quay về được "nhap": người ký thứ hai không đồng ý thì phải có đường rút bản thảo về sửa.
# Không có đường đó thì hồ sơ kẹt vĩnh viễn ở trạng thái chờ, và cách duy nhất để đăng là lập một hồ sơ mới
# — tức là người ta sẽ bỏ qua chốt chặn bằng cách lập hồ sơ mới, đúng thứ chốt chặn này sinh ra để ngăn.
ND_CHUYEN = {"nhap": ("cho_duyet",), "cho_duyet": ("nhap",), "cho_ky_2": ("nhap",),
             "da_duyet": ("da_dang", "go"), "da_dang": ("go",), "go": ()}


def nd_next_code(db: Session) -> str:
    n = db.execute(select(func.count()).select_from(ContentItem)).scalar() + 1
    return f"ND{date.today():%y%m}-{n:03d}"


def nd_can_ky_2(n: ContentItem) -> bool:
    """Nội dung có cam kết với khách hoặc có số liệu tài chính thì cần chữ ký thứ hai.

    Đây là LÝ DO TỒN TẠI của màn hình này. Vietourist là công ty đại chúng (VTD, UPCoM): một bài hứa
    'cam kết hoàn tiền 100%' hay một con số doanh thu đưa ra ngoài mà chưa ai duyệt là rủi ro pháp lý và
    rủi ro công bố thông tin. Bỏ chốt này thì đây chỉ còn là một danh sách bài đăng.
    """
    return bool(n.co_cam_ket or n.co_so_lieu_tc)


def nd_vai_tro_ky_2(db: Session) -> tuple:
    """Vai trò được ký chữ ký thứ hai – lấy từ tham số chính sách, không viết cứng tên người vào mã."""
    s = R.get_param_text(db, "nd_vai_tro_ky_2") or "tgd,chutich,hanh_chinh"
    return tuple(x.strip() for x in s.split(",") if x.strip())


def nd_kiem_du_lieu(d: dict) -> None:
    if not (d.get("title") or "").strip(): raise ValueError("Phải có tiêu đề nội dung")
    if d.get("loai") not in ND_LOAI: raise ValueError(f"Loại nội dung không hợp lệ. Chỉ nhận: {', '.join(ND_LOAI)}")
    kenh = d.get("kenh") or []
    if not kenh: raise ValueError("Phải chọn ít nhất một kênh đăng")
    la = [k for k in kenh if k not in ND_KENH]
    if la: raise ValueError(f"Kênh đăng không hợp lệ: {', '.join(la)}")
    if not d.get("ngay_du_kien"): raise ValueError("Phải có ngày dự kiến đăng – đây là thứ dựng nên lịch nội dung")
    if not (d.get("ban_thao") or "").strip():
        raise ValueError("Phải đính kèm hoặc dán đường dẫn bản thảo – bản thảo không xem được thì không duyệt được")


def nd_tao(db: Session, u: User, data: dict) -> ContentItem:
    d = dict(data); nguon = (d.pop("nguon_tao", "") or "nguoi").lower()
    if nguon not in ("nguoi", "ai"): raise ValueError("Nguồn tạo chỉ nhận 'nguoi' hoặc 'ai'")
    nd_kiem_du_lieu(d)
    if nguon == "ai" and not (d.get("ai_ghi_chu") or "").strip():
        raise ValueError("Nội dung do AI soạn phải ghi căn cứ – người duyệt cần biết máy dựa vào đâu")
    n = ContentItem(code=nd_next_code(db), title=d["title"], loai=d["loai"],
                    campaign_id=d.get("campaign_id"), kenh=d["kenh"], ngay_du_kien=d["ngay_du_kien"],
                    ban_thao=d["ban_thao"], co_cam_ket=bool(d.get("co_cam_ket")),
                    co_so_lieu_tc=bool(d.get("co_so_lieu_tc")), nguoi_soan=u.username,
                    note=d.get("note", ""), company_id=d.get("company_id"),
                    nguon_tao=nguon, ai_ghi_chu=d.get("ai_ghi_chu", ""), status="nhap")
    db.add(n); db.flush()
    R.audit(db, u.username, u.role, "lap_noi_dung", f"content:{n.code}",
            after={"tieu_de": n.title, "cam_ket": n.co_cam_ket, "so_lieu_tc": n.co_so_lieu_tc, "nguon": nguon})
    db.commit(); db.refresh(n)
    return n


def nd_duyet(db: Session, u: User, n: ContentItem) -> tuple[ContentItem, str]:
    if n.status not in ("cho_duyet", "cho_ky_2"):
        raise ValueError(f"Chỉ duyệt được bản đang chờ duyệt, bản này đang ở '{ND_TRANG_THAI.get(n.status, n.status)}'")
    if u.role not in ND_DUYET: raise PermissionError("Vai trò của bạn không được duyệt nội dung")
    if u.username == n.nguoi_soan: raise PermissionError("Người soạn không được tự duyệt nội dung của mình")
    ky = [x for x in (n.nguoi_duyet or "").split(",") if x]
    if u.username in ky: raise ValueError("Bạn đã ký bản này rồi – cần chữ ký của người thứ hai")
    if n.status == "cho_ky_2" and u.role not in nd_vai_tro_ky_2(db) and not toan_quyen_ke_ca_tach_bach(u, db):
        raise PermissionError("Chữ ký thứ hai cho nội dung có cam kết hoặc số liệu tài chính phải là "
                              f"Ban TGĐ hoặc Pháp chế ({', '.join(nd_vai_tro_ky_2(db))})")
    ky.append(u.username); n.nguoi_duyet = ",".join(ky)
    if nd_can_ky_2(n) and len(ky) < 2:
        n.status = "cho_ky_2"
        tin = (f"Đã ghi chữ ký thứ nhất. Nội dung này có "
               + " và ".join([x for x in ["cam kết với khách" if n.co_cam_ket else "",
                                          "số liệu tài chính" if n.co_so_lieu_tc else ""] if x])
               + " nên cần thêm chữ ký của Ban TGĐ hoặc Pháp chế.")
    else:
        n.status = "da_duyet"; n.approved_at = datetime.now()
        tin = f"Nội dung {n.code} đã được duyệt"
    R.audit(db, u.username, u.role, "duyet_noi_dung", f"content:{n.code}",
            after={"trang_thai": n.status, "chu_ky": n.nguoi_duyet})
    db.commit(); db.refresh(n)
    return n, tin


def nd_chuyen(db: Session, u: User, n: ContentItem, moi: str, link: str = "", ly_do: str = "") -> ContentItem:
    if moi not in ND_TRANG_THAI: raise ValueError("Trạng thái không hợp lệ")
    if moi in ("da_duyet", "cho_ky_2"): raise ValueError("Duyệt nội dung phải qua nút Duyệt – ở đó mới đếm chữ ký")
    if moi not in ND_CHUYEN.get(n.status, ()):
        raise ValueError(f"Không chuyển thẳng từ '{ND_TRANG_THAI[n.status]}' sang '{ND_TRANG_THAI[moi]}'")
    if moi == "da_dang":
        if not (link or n.link_dang or "").strip():
            raise ValueError("Phải dán đường dẫn bài đã đăng – không có link thì sau này không ai kiểm được "
                             "nội dung thực tế trên kênh có đúng bản đã duyệt hay không")
        n.link_dang = (link or n.link_dang).strip()[:400]; n.posted_at = datetime.now()
    if moi == "go":
        if not (ly_do or "").strip(): raise ValueError("Phải ghi lý do gỡ nội dung")
        n.ly_do_go = ly_do.strip()[:300]
    # Rút bản thảo về Nháp thì mọi chữ ký cũ mất hiệu lực: chúng nói về bản thảo trước khi sửa.
    if moi == "nhap": n.nguoi_duyet = ""
    truoc = n.status; n.status = moi
    R.audit(db, u.username, u.role, "chuyen_trang_thai_noi_dung", f"content:{n.code}",
            before={"trang_thai": truoc}, after={"trang_thai": moi, "link": n.link_dang})
    db.commit(); db.refresh(n)
    return n
