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
        select(func.coalesce(func.sum(Booking.amount - Booking.discount), 0.0))
        .join(Lead, Lead.booking_id == Booking.id)
        .where(Lead.campaign_id == c.id, Booking.cancelled == False)).scalar() or 0)
    return {"so_lead": int(so_lead), "chuyen_doi": int(chuyen_doi),
            "ty_le_chuyen_doi": (chuyen_doi / so_lead) if so_lead else 0,
            "chi_phi": chi_phi, "chi_phi_treo": treo, "con_lai_ngan_sach": c.budget - chi_phi - treo,
            "chi_phi_moi_lead": (chi_phi / so_lead) if so_lead else 0,
            "chi_phi_moi_booking": (chi_phi / chuyen_doi) if chuyen_doi else 0,
            "doanh_thu": doanh_thu, "hieu_qua": (doanh_thu / chi_phi) if chi_phi else 0,
            "dat_chi_tieu_lead": (so_lead >= c.target_leads) if c.target_leads else None,
            "dat_chi_tieu_booking": (chuyen_doi >= c.target_bookings) if c.target_bookings else None,
            # Vượt ngân sách nói ra ngay, không đợi tới lúc quyết toán.
            "vuot_ngan_sach": (chi_phi + treo) > c.budget}


def lead_chua_gan(db: Session, thang: str = "") -> dict:
    """Lead chưa gắn chiến dịch, gom theo ô chữ campaign cũ – để Marketing gán dần chứ không đoán hộ."""
    q = select(Lead.campaign, func.count()).where(Lead.campaign_id.is_(None))
    if thang: q = q.where(Lead.lead_month == thang)
    rows = db.execute(q.group_by(Lead.campaign).order_by(func.count().desc())).all()
    return {"tong": sum(int(n) for _, n in rows),
            "nhom": [{"campaign_cu": (t or "(không ghi)"), "so_lead": int(n)} for t, n in rows]}
