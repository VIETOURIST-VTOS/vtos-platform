"""Chia một khoản tiền vào cho nhiều booking — và giữ số dư chưa phân bổ luôn nói thật.

Xem app/models/phan_bo_tien.py để biết vì sao bảng này tồn tại. Tệp này giữ ba luật:

  1. Tổng phân bổ còn hiệu lực KHÔNG vượt số tiền của giao dịch. Vượt là tạo ra tiền không có thật.
  2. Mỗi dòng sinh đúng một phiếu thu; huỷ dòng thì huỷ luôn phiếu thu ấy. Không có đường nào để một
     dòng phân bổ sống mà phiếu thu của nó đã chết, hoặc ngược lại.
  3. Thu DƯ so với số còn phải thu của booking thì CẢNH BÁO chứ không chặn. Khách trả dư là chuyện
     có thật hằng ngày (làm tròn, chuyển nhầm, trả trước cho tour sau); chặn ở đây chỉ đẩy kế toán
     sang ghi chú tay, và lúc ấy hệ thống mất dấu vết thay vì có thêm.
"""
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.core import Booking, User
from app.models.payments import BankTransaction, Receipt
from app.models.phan_bo_tien import PhanBoTien
from app.models.nghia_vu import NghiaVuThanhToan, DotThanhToan, TRANG_THAI_DONG
from app.services import payments as PAY
from app.services import rules as R


def cac_dong(db: Session, txn_id: int, ca_da_huy: bool = False) -> list[PhanBoTien]:
    q = select(PhanBoTien).where(PhanBoTien.bank_txn_id == txn_id)
    if not ca_da_huy:
        q = q.where(PhanBoTien.huy == False)          # noqa: E712
    return list(db.execute(q.order_by(PhanBoTien.id)).scalars())


def da_phan_bo(db: Session, txn_id: int) -> float:
    """Tổng đã phân bổ còn hiệu lực. Đây là NGUỒN SỰ THẬT; cột `chua_phan_bo` chỉ là bản chép lại."""
    return float(db.execute(
        select(func.coalesce(func.sum(PhanBoTien.so_tien), 0))
        .where(PhanBoTien.bank_txn_id == txn_id, PhanBoTien.huy == False)).scalar() or 0)   # noqa: E712


def con_lai(db: Session, txn: BankTransaction) -> float:
    return round(float(txn.amount or 0) - da_phan_bo(db, txn.id), 2)


def _cap_nhat_giao_dich(db: Session, txn: BankTransaction) -> float:
    """Chép số dư vào cột lưu và đặt lại trạng thái khớp cho đúng với thực tế.

    Trạng thái phải đi theo số dư, không đi theo ý người bấm: còn dư thì giao dịch vẫn là việc đang
    dở, và màn hình phải tiếp tục hiện nó ra. Đánh dấu 'đã khớp' khi còn dư là cách một khoản tiền
    biến mất khỏi danh sách việc mà vẫn chưa xong.
    """
    du = con_lai(db, txn)
    txn.chua_phan_bo = du
    dong = cac_dong(db, txn.id)
    if not dong:
        # Quay về trạng thái chờ: mọi dòng đã huỷ nghĩa là chưa ai hiểu được khoản tiền này.
        txn.match_status = "cho_ke_toan"
        txn.booking_id = None
        txn.match_note = "Đã huỷ toàn bộ phân bổ – chờ Kế toán phân bổ lại"
    elif du > 0.5:
        txn.match_status = "cho_ke_toan"
        txn.booking_id = _booking_neu_duy_nhat(dong)
        txn.match_note = f"Phân bổ {len(dong)} dòng, còn {du:,.0f} đ chưa phân bổ"
    else:
        txn.match_status = "da_khop"
        txn.booking_id = _booking_neu_duy_nhat(dong)
        txn.match_note = f"Phân bổ đủ cho {len(dong)} dòng"
    return du


def _booking_neu_duy_nhat(dong: list[PhanBoTien]) -> int | None:
    """Gắn giao dịch về MỘT booking chỉ khi nó có đúng một dòng, và dòng ấy là nhánh booking.

    Đợt E5 13/10/2026: trước đợt này chỗ gọi viết thẳng `dong[0].booking_id`, mà từ nay một dòng
    có thể là nhánh NGHĨA VỤ với `booking_id` rỗng. Gán rỗng vào `txn.booking_id` thì không sai số
    liệu, nhưng gán NHẦM thì sai — nên hỏi đúng một câu: có đúng một dòng, và nó có booking không.
    """
    if len(dong) == 1 and dong[0].booking_id is not None:
        return dong[0].booking_id
    return None


def _kiem_nhanh_ra(db: Session, txn: BankTransaction, d: dict, i: int) -> tuple:
    """Kiểm MỘT dòng phân bổ tiền ra. Trả về (nghĩa vụ, đợt, số tiền, ghi chú) hoặc ném lỗi.

    BỐN CHỖ CHẶN CỨNG, và chỉ bốn: sai pháp nhân · nghĩa vụ đã đóng · nghĩa vụ hướng THU · đợt
    không thuộc nghĩa vụ đã chọn. (Chỗ chặn thứ năm — vượt số dư chưa phân bổ — kiểm trên cả lô,
    không kiểm từng dòng được.) Trả dư thì CẢNH BÁO, xem `phan_bo_ra`.
    """
    try:
        tien = round(float(d.get("so_tien") or 0), 2)
    except (TypeError, ValueError):
        raise ValueError(f"Dòng {i}: số tiền không đọc được")
    if tien <= 0:
        raise ValueError(f"Dòng {i}: số tiền phải lớn hơn 0")

    nv = db.get(NghiaVuThanhToan, int(d.get("nghia_vu_id") or 0))
    if not nv:
        raise ValueError(f"Dòng {i}: không có nghĩa vụ")
    if nv.huong != "chi":
        raise ValueError(f"Dòng {i}: nghĩa vụ {nv.ma_goc} là nghĩa vụ THU, không trả tiền ra vào "
                         f"nó được. Tiền ra chỉ phân bổ cho nghĩa vụ hướng chi.")
    if nv.trang_thai in TRANG_THAI_DONG:
        raise ValueError(f"Dòng {i}: nghĩa vụ {nv.ma_goc} đã đóng ({nv.trang_thai})")
    # PHÁP NHÂN: tiền của pháp nhân này không mặc định dùng được cho pháp nhân khác. Nghĩa vụ CHƯA
    # XÁC ĐỊNH pháp nhân (rỗng) thì KHÔNG đoán — chặn và nói ra, đúng luật K2.
    cty_txn = getattr(txn, "company_id", None)
    if nv.company_id is None:
        raise ValueError(f"Dòng {i}: nghĩa vụ {nv.ma_goc} chưa xác định pháp nhân – gán pháp nhân "
                         f"cho nó trước, hệ thống không đoán thay.")
    if cty_txn is not None and nv.company_id != cty_txn:
        raise ValueError(f"Dòng {i}: nghĩa vụ {nv.ma_goc} thuộc pháp nhân khác với tài khoản ngân "
                         f"hàng của giao dịch. Tiền của pháp nhân này không trả hộ pháp nhân kia.")

    dot = None
    if d.get("dot_id"):
        dot = db.get(DotThanhToan, int(d["dot_id"]))
        if not dot:
            raise ValueError(f"Dòng {i}: không có đợt thanh toán")
        if dot.nghia_vu_id != nv.id:
            raise ValueError(f"Dòng {i}: đợt {dot.so_thu_tu} không thuộc nghĩa vụ {nv.ma_goc}")
    return nv, dot, tien, str(d.get("ghi_chu") or "")[:300]


def phan_bo_ra(db: Session, u: User, txn: BankTransaction, dong_moi: list[dict]) -> dict:
    """Phân bổ một khoản tiền RA cho một hoặc nhiều nghĩa vụ (và đợt của chúng).

    Đợt E5, 13/10/2026. Cùng khuôn với `phan_bo` của tiền vào: kiểm CẢ LÔ trước khi ghi dòng đầu,
    huỷ chứ không xoá, số dư tính lại từ các dòng. Khác đúng một điều và đó là điều cố ý:
    KHÔNG SINH PHIẾU THU. Phiếu thu là chứng từ của tiền vào; tiền ra đã có lệnh chi của nó, và
    dựng thêm một chứng từ cho cùng một khoản là tạo chứng từ ma.
    """
    if (txn.transfer_type or "") != "out":
        raise ValueError("Cửa này chỉ phân bổ tiền RA. Tiền vào phân bổ cho booking ở cửa kia.")
    if not dong_moi:
        raise ValueError("Chưa có dòng phân bổ nào")

    du = con_lai(db, txn)
    tong_moi, da_kiem, canh_bao = 0.0, [], []
    for i, d in enumerate(dong_moi, start=1):
        nv, dot, tien, ghi_chu = _kiem_nhanh_ra(db, txn, d, i)
        tong_moi += tien
        # TRẢ DƯ: CẢNH BÁO, KHÔNG CHẶN — y như luật 3 của tiền vào. Trả dư là chuyện có thật (làm
        # tròn, trả trước đợt sau); chặn ở đây chỉ đẩy Kế toán sang ghi chú tay, và lúc ấy hệ
        # thống mất dấu vết thay vì có thêm.
        con = dot.con_lai() if dot is not None else nv.con_lai()
        ten = f"{nv.ma_goc} đợt {dot.so_thu_tu}" if dot is not None else nv.ma_goc
        if tien > con + 0.5:
            canh_bao.append(f"{ten}: phân bổ {tien:,.0f} đ nhiều hơn số còn phải trả {con:,.0f} đ "
                            f"– phần dư thành trả trước")
        da_kiem.append((nv, dot, tien, ghi_chu))

    if round(tong_moi, 2) > round(du, 2) + 0.5:
        raise ValueError(f"Tổng phân bổ {tong_moi:,.0f} đ vượt số dư chưa phân bổ {du:,.0f} đ "
                         f"của giao dịch (số tiền {abs(float(txn.amount or 0)):,.0f} đ)")

    ket = []
    for nv, dot, tien, ghi_chu in da_kiem:
        pb = PhanBoTien(bank_txn_id=txn.id, nghia_vu_id=nv.id,
                        dot_id=dot.id if dot is not None else None,
                        so_tien=tien, ghi_chu=ghi_chu, boi=u.username)
        db.add(pb)
        _cong_da_tra(nv, dot, tien)
        db.flush()
        ket.append(pb)
        R.audit(db, u.username, u.role, "phan_bo_tien_ra", f"bank:{txn.sepay_id}",
                after={"nghia_vu": nv.ma_goc, "dot": dot.so_thu_tu if dot is not None else None,
                       "so_tien": tien, "ghi_chu": ghi_chu})

    du_moi = _cap_nhat_giao_dich(db, txn)
    db.commit()
    return {"da_them": len(ket), "chua_phan_bo": du_moi, "canh_bao": canh_bao,
            "message": (f"Đã phân bổ {len(ket)} dòng. "
                        + (f"Còn {du_moi:,.0f} đ chưa phân bổ." if du_moi > 0.5 else "Đã phân bổ hết."))}


def _cong_da_tra(nv: NghiaVuThanhToan, dot, tien: float) -> None:
    """Cộng tiền đã trả vào ĐỢT và vào NGHĨA VỤ. Dấu trừ để trả lại khi huỷ.

    Cộng cả hai chỗ, không chỉ cộng vào đợt rồi tính tổng khi cần: `NghiaVuThanhToan.da_tra` là
    cột mà bảng dòng tiền và sổ công nợ đang đọc từ trước Đợt E4, và một nghĩa vụ KHÔNG chia đợt
    thì không có đợt nào để cộng. Phép thử canh hai con số khớp nhau khi có đợt.
    """
    nv.da_tra = round(float(nv.da_tra or 0) + tien, 2)
    if dot is not None:
        dot.da_tra = round(float(dot.da_tra or 0) + tien, 2)


def phan_bo(db: Session, u: User, txn: BankTransaction, dong_moi: list[dict]) -> dict:
    """Phân bổ thêm một hoặc nhiều dòng cho giao dịch. KHÔNG ghi gì nếu có bất kỳ dòng nào sai.

    Kiểm cả lô trước khi ghi dòng đầu tiên: ghi được ba dòng rồi hỏng ở dòng thứ tư để lại một trạng
    thái không ai đọc được – tiền đã vào sổ một nửa, và người dùng không biết nên bấm lại hay không.
    """
    if (txn.transfer_type or "") != "in":
        raise ValueError("Chỉ phân bổ được tiền VÀO. Tiền ra khớp với lệnh chi, không phải booking.")
    if not dong_moi:
        raise ValueError("Chưa có dòng phân bổ nào")

    du = con_lai(db, txn)
    tong_moi = 0.0
    da_kiem = []
    canh_bao = []
    for i, d in enumerate(dong_moi, start=1):
        try:
            tien = round(float(d.get("so_tien") or 0), 2)
        except (TypeError, ValueError):
            raise ValueError(f"Dòng {i}: số tiền không đọc được")
        if tien <= 0:
            raise ValueError(f"Dòng {i}: số tiền phải lớn hơn 0")
        b = db.get(Booking, int(d.get("booking_id") or 0))
        if not b:
            raise ValueError(f"Dòng {i}: không có booking")
        if getattr(b, "cancelled", False):
            raise ValueError(f"Dòng {i}: booking {b.code} đã huỷ – không nhận tiền vào booking đã huỷ")
        tong_moi += tien
        # Cảnh báo thu dư – KHÔNG chặn. Xem luật 3 ở đầu tệp.
        con_phai_thu = round(float(b.amount or 0) - float(b.discount or 0) - PAY.paid_amount(db, b.id), 2)
        if tien > con_phai_thu + 0.5:
            canh_bao.append(f"{b.code}: phân bổ {tien:,.0f} đ nhiều hơn số còn phải thu "
                            f"{con_phai_thu:,.0f} đ – phần dư sẽ thành tiền trả trước")
        da_kiem.append((b, tien, str(d.get("ghi_chu") or "")[:300]))

    if round(tong_moi, 2) > round(du, 2) + 0.5:
        raise ValueError(f"Tổng phân bổ {tong_moi:,.0f} đ vượt số dư chưa phân bổ {du:,.0f} đ "
                         f"của giao dịch (số tiền {float(txn.amount or 0):,.0f} đ)")

    ket = []
    for b, tien, ghi_chu in da_kiem:
        rc = PAY._make_receipt(db, b, txn, tien, u.username, "ke_toan_xac_nhan",
                               note=ghi_chu or f"Phân bổ từ giao dịch {txn.sepay_id}")
        rc.confirmed_by, rc.confirmed_at = u.username, datetime.now()
        pb = PhanBoTien(bank_txn_id=txn.id, booking_id=b.id, receipt_id=rc.id,
                        so_tien=tien, ghi_chu=ghi_chu, boi=u.username)
        db.add(pb); db.flush()
        ket.append(pb)
        R.audit(db, u.username, u.role, "phan_bo_tien_vao", f"bank:{txn.sepay_id}",
                after={"booking": b.code, "so_tien": tien, "phieu_thu": rc.code, "ghi_chu": ghi_chu})

    du_moi = _cap_nhat_giao_dich(db, txn)
    db.commit()
    return {"da_them": len(ket), "chua_phan_bo": du_moi, "canh_bao": canh_bao,
            "message": (f"Đã phân bổ {len(ket)} dòng. "
                        + (f"Còn {du_moi:,.0f} đ chưa phân bổ." if du_moi > 0.5 else "Đã phân bổ hết."))}


def huy_dong(db: Session, u: User, pb: PhanBoTien, ly_do: str) -> dict:
    """Huỷ một dòng phân bổ – và huỷ luôn phiếu thu của nó. Bắt buộc có lý do bằng lời.

    Bắt buộc lý do vì dòng bị huỷ vẫn nằm lại trong sổ: người đọc về sau sẽ thấy nó và hỏi tại sao.
    Một dòng huỷ không lý do thì lần sau người ta chỉ còn cách đoán.
    """
    if pb.huy:
        raise ValueError("Dòng này đã huỷ rồi")
    if not (ly_do or "").strip():
        raise ValueError("Phải ghi lý do huỷ – dòng đã huỷ vẫn nằm lại trong sổ để tra cứu")

    txn = db.get(BankTransaction, pb.bank_txn_id)
    # Đợt E5: dòng nhánh NGHĨA VỤ không có phiếu thu, và trả tiền lại cho đợt / nghĩa vụ thay vì
    # cho booking. Đặt TRƯỚC phần phiếu thu để không ai đọc nhầm là hai việc nối nhau.
    if pb.nhanh() == "nghia_vu":
        _nv = db.get(NghiaVuThanhToan, pb.nghia_vu_id)
        _dot = db.get(DotThanhToan, pb.dot_id) if pb.dot_id else None
        if _nv is not None:
            _cong_da_tra(_nv, _dot, -round(float(pb.so_tien or 0), 2))
    rc = db.get(Receipt, pb.receipt_id) if pb.receipt_id else None
    pb.huy, pb.huy_boi, pb.huy_luc, pb.huy_ly_do = True, u.username, datetime.now(), ly_do.strip()[:300]
    if rc is not None:
        rc.status = "huy"
        rc.note = (rc.note + f" · HUỶ: {ly_do.strip()}")[:200]
        # PHẢI đẩy xuống trước khi đếm lại: phiên làm việc của VTOS mở với autoflush=False, nên câu
        # truy vấn tổng phiếu thu ngay sau đây KHÔNG nhìn thấy trạng thái vừa đổi nếu chưa flush.
        # Thiếu một dòng này thì booking.paid giữ nguyên số cũ sau khi huỷ – tiền đã trả về số dư của
        # giao dịch mà booking vẫn tưởng mình đã thu.
        db.flush()
        b = db.get(Booking, rc.booking_id)
        if b is not None:
            b.paid = PAY.paid_amount(db, b.id)
            from app.services.bookings import refresh_status
            refresh_status(b)
    R.audit(db, u.username, u.role, "huy_phan_bo_tien", f"bank:{txn.sepay_id if txn else pb.bank_txn_id}",
            before={"booking_id": pb.booking_id, "so_tien": float(pb.so_tien or 0),
                    "phieu_thu": rc.code if rc else ""},
            after={"ly_do": pb.huy_ly_do})
    du = _cap_nhat_giao_dich(db, txn) if txn else 0.0
    db.commit()
    return {"chua_phan_bo": du, "message": f"Đã huỷ dòng phân bổ. Còn {du:,.0f} đ chưa phân bổ."}


def bang(db: Session, txn: BankTransaction) -> dict:
    """Toàn cảnh một khoản tiền: đã chia cho ai, còn lại bao nhiêu, và những dòng đã huỷ."""
    ds = []
    for pb in cac_dong(db, txn.id, ca_da_huy=True):
        b = db.get(Booking, pb.booking_id) if pb.booking_id else None
        rc = db.get(Receipt, pb.receipt_id) if pb.receipt_id else None
        _nv = db.get(NghiaVuThanhToan, pb.nghia_vu_id) if pb.nghia_vu_id else None
        _dot = db.get(DotThanhToan, pb.dot_id) if pb.dot_id else None
        ds.append({"nhanh": pb.nhanh(),
                   "nghia_vu_id": pb.nghia_vu_id, "nghia_vu_ma": _nv.ma_goc if _nv else "",
                   "doi_tuong": _nv.doi_tuong if _nv else "",
                   "dot_id": pb.dot_id, "dot_stt": _dot.so_thu_tu if _dot else None,
                   "id": pb.id, "booking_id": pb.booking_id, "booking_code": b.code if b else "",
                   "khach": b.customer_name if b else "", "tour_code": b.tour.code if b and b.tour else "",
                   "so_tien": float(pb.so_tien or 0), "ghi_chu": pb.ghi_chu,
                   "phieu_thu": rc.code if rc else "", "boi": pb.boi, "luc": pb.luc,
                   "huy": pb.huy, "huy_boi": pb.huy_boi, "huy_luc": pb.huy_luc, "huy_ly_do": pb.huy_ly_do})
    du = con_lai(db, txn)
    return {"bank_txn_id": txn.id, "sepay_id": txn.sepay_id, "so_tien": float(txn.amount or 0),
            "noi_dung": txn.content, "ngay": txn.transaction_date,
            "da_phan_bo": round(float(txn.amount or 0) - du, 2), "chua_phan_bo": du,
            "match_status": txn.match_status, "dong": ds,
            "ghi_chu_man_hinh": ("Số dư chưa phân bổ hiện thẳng ở đây, không phải tự trừ nhẩm. "
                                 "Dòng đã huỷ vẫn giữ lại kèm lý do – đó là dấu vết của một lần hiểu sai.")}
