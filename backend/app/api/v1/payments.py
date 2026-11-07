"""API thu tiền: webhook SePay + màn hình Kế toán."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.models.core import Booking, Tour, User
from app.models.payments import BankTransaction, Receipt
from app.services import payments as P
from app.services import access as AC
from app.services import pham_vi_phap_nhan as PV
from app.services import sepay as SP

router = APIRouter(prefix="/api/v1", tags=["thu-tien"])


def txn_out(t: BankTransaction, db: Session, ma_bk: dict | None = None, dem_pb: dict | None = None) -> dict:
    # KS-TC · `ma_bk` / `dem_pb` là hai bảng tra NẠP SẴN cho cả danh sách (xem `list_txns`). Không
    # truyền thì tự hỏi từng dòng như cũ — chỗ gọi lẻ một giao dịch vẫn đúng.
    if ma_bk is not None:
        b_code = ma_bk.get(t.booking_id, "") if t.booking_id else ""
    else:
        b = db.get(Booking, t.booking_id) if t.booking_id else None
        b_code = b.code if b else ""
    return {"id": t.id, "sepay_id": t.sepay_id, "gateway": t.gateway, "account_number": t.account_number, "transaction_date": t.transaction_date,
            "transfer_type": t.transfer_type, "amount": t.amount, "content": t.content, "reference_code": t.reference_code,
            "match_status": t.match_status, "match_note": t.match_note, "booking_id": t.booking_id, "booking_code": b_code,
            "received_at": t.received_at,
            # VPM-5: số dư chưa phân bổ đi kèm ngay trong danh sách, không bắt màn hình tự trừ.
            # RỖNG = chưa từng phân bổ dòng nào (giao dịch cũ), khác hẳn 0 = đã phân bổ hết.
            "chua_phan_bo": t.chua_phan_bo,
            "so_dong_phan_bo": dem_pb.get(t.id, 0) if dem_pb is not None else _dem_phan_bo(db, t.id)}


def _dem_phan_bo(db: Session, tid: int) -> int:
    from app.models.phan_bo_tien import PhanBoTien
    from sqlalchemy import func as _f
    return int(db.execute(select(_f.count()).select_from(PhanBoTien)
                          .where(PhanBoTien.bank_txn_id == tid, PhanBoTien.huy == False)).scalar() or 0)   # noqa: E712


def receipt_out(r: Receipt, db: Session) -> dict:
    b = db.get(Booking, r.booking_id)
    return {"id": r.id, "code": r.code, "booking_id": r.booking_id, "booking_code": b.code if b else "", "customer_name": b.customer_name if b else "",
            "tour_code": b.tour.code if b and b.tour else "", "amount": r.amount, "method": r.method, "payer": r.payer, "note": r.note,
            "status": r.status, "created_by": r.created_by, "confirmed_by": r.confirmed_by, "created_at": r.created_at, "confirmed_at": r.confirmed_at}


# ---------- Webhook SePay ----------
@router.post("/sepay/webhook", status_code=201)
async def sepay_webhook(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """SePay gọi POST kèm header `Authorization: Apikey <SEPAY_WEBHOOK_KEY>`."""
    expected = f"Apikey {settings.SEPAY_WEBHOOK_KEY}"
    if not settings.SEPAY_WEBHOOK_KEY or authorization != expected:
        raise HTTPException(401, "Sai khóa webhook SePay")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(422, "Body không phải JSON")
    if not isinstance(payload, dict) or not (payload.get("id") or payload.get("sepay_id")):
        # SePay "Gửi thử" / ping không có id giao dịch → xác nhận kết nối, không ghi
        return {"success": True, "test": True, "note": "Kết nối OK – gói tin không có id giao dịch nên không ghi nhận"}
    try:
        txn, created = P.ingest_sepay(db, payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"success": True, "new": created, "match_status": txn.match_status, "note": txn.match_note}


# ---------- Kết nối API SePay (kéo) ----------
@router.get("/sepay/status")
def sepay_status(u: User = Depends(require_roles("ketoan", "cntt", "tgd", "chutich", "bks")), db: Session = Depends(get_db)):
    return SP.status(db)


class PullIn(BaseModel):
    from_date: str | None = None   # YYYY-MM-DD
    to_date: str | None = None
    account_number: str = ""


@router.post("/sepay/pull")
def sepay_pull(data: PullIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    """Kéo giao dịch từ SePay User API vào VTOS (idempotent). Robot R1 đối chiếu như webhook."""
    from datetime import date as _d
    try:
        f = _d.fromisoformat(data.from_date) if data.from_date else None
        t = _d.fromisoformat(data.to_date) if data.to_date else None
        res = SP.pull(db, f, t, data.account_number or settings.SEPAY_ACCOUNT_NUMBER)
    except ValueError as e:
        raise HTTPException(422, f"Ngày không hợp lệ: {e}")
    except SP.SePayError as e:
        raise HTTPException(502, str(e))
    from app.services import rules as R
    R.audit(db, u.username, u.role, "sepay_keo_giao_dich", "sepay", after=res); db.commit()
    res["message"] = f"Đã kéo {res['fetched']} giao dịch, mới {res['new']} (khớp {res['matched']}, chờ Kế toán {res['pending']})"
    return res


@router.post("/robot/sepay/pull")
def robot_sepay_pull(data: PullIn, x_robot_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    """n8n gọi định kỳ (X-Robot-Token) để đối chiếu bù khi webhook lỗi."""
    if not settings.ROBOT_TOKEN or x_robot_token != settings.ROBOT_TOKEN: raise HTTPException(401, "Sai robot token")
    from datetime import date as _d, timedelta
    f = _d.fromisoformat(data.from_date) if data.from_date else _d.today() - timedelta(days=3)
    t = _d.fromisoformat(data.to_date) if data.to_date else _d.today()
    try:
        return SP.pull(db, f, t, data.account_number or settings.SEPAY_ACCOUNT_NUMBER)
    except SP.SePayError as e:
        raise HTTPException(502, str(e))


# ---------- Kế toán ----------
@router.get("/bank-transactions")
def list_txns(status: str | None = None, limit: int = 200, u: User = Depends(require_roles(*AC.FINANCE_ROLES, mo_ta="giao dịch ngân hàng")), db: Session = Depends(get_db)):
    from sqlalchemy.orm import defer
    # Gói tin gốc SePay (`raw`) không ra màn hình danh sách — có đường riêng /raw — nên không kéo về.
    q = select(BankTransaction).options(defer(BankTransaction.raw)).order_by(desc(BankTransaction.transaction_date))
    if status: q = q.where(BankTransaction.match_status.in_(status.split(",")))
    # KS-TC · 08/11/2026 — BA CÂU HỎI CHO CẢ DANH SÁCH, KHÔNG PHẢI 1 + 2×200. Đo trên crm thật:
    # trang Tài chính chờ 6–7,6 giây chỉ riêng danh sách này, vì mỗi dòng hỏi riêng mã booking và
    # riêng số dòng phân bổ — 400 chuyến đi–về tới cơ sở dữ liệu cho 200 dòng. Nay nạp hai bảng tra
    # một lần. Cùng số, cùng thứ tự, cùng khuôn trả về.
    from app.models.phan_bo_tien import PhanBoTien
    ds = list(db.execute(q.limit(limit)).scalars())
    bk_ids = {t.booking_id for t in ds if t.booking_id}
    ma_bk = dict(db.execute(select(Booking.id, Booking.code).where(Booking.id.in_(bk_ids))).all()) if bk_ids else {}
    t_ids = [t.id for t in ds]
    dem_pb = dict(db.execute(select(PhanBoTien.bank_txn_id, func.count())
                             .where(PhanBoTien.bank_txn_id.in_(t_ids), PhanBoTien.huy == False)   # noqa: E712
                             .group_by(PhanBoTien.bank_txn_id)).all()) if t_ids else {}
    return [txn_out(t, db, ma_bk, {k: int(v) for k, v in dem_pb.items()}) for t in ds]


@router.post("/bank-transactions/rematch")
def rematch(u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    """Chạy lại robot R1 cho các giao dịch tiền vào đang chờ (sau khi nạp booking mới / cải tiến quy tắc khớp)."""
    n = m = 0
    for t in db.execute(select(BankTransaction).where(BankTransaction.transfer_type == "in", BankTransaction.match_status.in_(["cho_ke_toan", "chua_khop"]))).scalars():
        P.match_transaction(db, t); n += 1
        if t.match_status == "da_khop": m += 1
    from app.services import rules as R
    R.audit(db, u.username, u.role, "chay_lai_khop_giao_dich", "sepay", after={"xet": n, "khop": m}); db.commit()
    return {"checked": n, "matched": m, "message": f"Đã xét lại {n} giao dịch, khớp thêm {m}"}


@router.get("/bank-transactions/{tid}/raw")
def txn_raw(tid: int, u: User = Depends(require_roles("ketoan", "cntt", "bks")), db: Session = Depends(get_db)):
    """Gói tin gốc SePay của giao dịch (đối chiếu/kiểm toán)."""
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    return {"id": t.id, "sepay_id": t.sepay_id, "raw": t.raw}


class AssignIn(BaseModel):
    booking_id: int
    note: str = ""


@router.post("/bank-transactions/{tid}/assign")
def assign_txn(tid: int, data: AssignIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    t = db.get(BankTransaction, tid); b = db.get(Booking, data.booking_id)
    if not t or not b: raise HTTPException(404, "Không có giao dịch/booking")
    try:
        r = P.accountant_assign(db, u, t, b, data.note)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"receipt": receipt_out(r, db), "message": f"Đã lập {r.code} cho {b.code}"}


class IgnoreIn(BaseModel):
    note: str = ""


@router.post("/bank-transactions/{tid}/ignore")
def ignore_txn(tid: int, data: IgnoreIn, u: User = Depends(require_roles("ketoan", "cntt")), db: Session = Depends(get_db)):
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    P.ignore_transaction(db, u, t, data.note)
    return {"message": "Đã bỏ qua giao dịch"}


@router.get("/receipts")
def list_receipts(limit: int = 200, u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="phiếu thu")), db: Session = Depends(get_db)):
    q = select(Receipt).order_by(desc(Receipt.created_at))
    q = PV.loc(q, Receipt, u)                # P6: phạm vi pháp nhân của phiên đăng nhập
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: q = q.join(Booking, Booking.id == Receipt.booking_id).where(Booking.sales_id.in_(vis))   # sale/nhóm chỉ thấy phiếu thu của khách mình
    return [receipt_out(r, db) for r in db.execute(q.limit(limit)).scalars()]


@router.post("/receipts/{rid}/confirm")
def confirm_receipt(rid: int, u: User = Depends(require_roles("ketoan",)), db: Session = Depends(get_db)):
    r = db.get(Receipt, rid)
    if not r: raise HTTPException(404, "Không có phiếu thu")
    try:
        P.accountant_confirm(db, u, r)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return {"message": f"Kế toán đã xác nhận {r.code}"}


@router.get("/receipts/quy/so-du")
# ĐỢT QUY-3 05/11/2026 — SỐ DƯ QUỸ TIỀN MẶT.
#
# Nằm dưới nhóm `/api/v1/receipts` ĐÃ KHAI, không mở nhóm mới — cùng lý do với ba cửa của Đợt
# QUY-1: mở một nhóm mới làm `PHAM_VI_DA_CHOT` lệch mười sáu dòng vai và hai con số ghim trong
# `test_lg9`, hai bảng CÓ CHỮ KÝ, trong khi KHÔNG vai nào bấm được thêm một cửa nào.
#
# Hai vai đúng bằng hai vai cửa lập phiếu. Thủ quỹ phải thấy tồn quỹ: đó là con số họ cần nhất
# lúc cầm tờ phiếu chi trên tay.
def so_du_quy(den_ngay: str = "", tu_ngay: str = "",
              u: User = Depends(require_roles("ketoan", "thu_quy",
                                              mo_ta="xem số dư quỹ tiền mặt")),
              db: Session = Depends(get_db)):
    """Tồn quỹ tính đến một ngày, cộng bằng ĐÚNG cái máy của sổ cái (`books.so_du_tien`)."""
    from datetime import date as _date
    from app.services import books as B
    try:
        dn = _date.fromisoformat(den_ngay) if den_ngay else _date.today()
        tn = _date.fromisoformat(tu_ngay) if tu_ngay else None
    except ValueError:
        raise HTTPException(422, "Ngày phải dạng yyyy-mm-dd")
    try:
        return B.so_du_tien(db, dn, tu_ngay=tn)
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class PhieuQuyIn(BaseModel):
    """Thân yêu cầu lập phiếu quỹ. Đợt QUY-1 04/11/2026.

    `ngay` là CHUỖI yyyy-mm-dd chứ không phải `date`: tệp này chỉ nhập `datetime`, và nối thêm
    một tên vào dòng nhập ấy là dựng lại cái bẫy "neo quá dài" — main thêm tên vào cuối dòng nhập
    là bản vá sau không còn khớp. Đổi ở trong thân hàm thì không neo vào dòng nhập nào.
    """
    chieu: str
    so_tien: float
    ly_do: str
    ngay: str = ""
    noi_dung: str = ""
    ten_doi_tuong: str = ""
    ma_doi_tuong: str = ""
    booking_id: int | None = None
    khoan_muc: str = ""


@router.post("/receipts/quy/phieu", status_code=201)
# ĐỢT QUY-1 04/11/2026 — CỬA LẬP PHIẾU QUỸ TIỀN MẶT.
#
# HAI VAI, KHÔNG THÊM BƯỚC XÁC NHẬN (Chủ tịch chốt 04/11/2026). `access.MAN_HINH_THU_QUY` đã cấp
# màn hình /collections cho `thu_quy` từ Đợt E2b-0, nên đây KHÔNG phải nới một quyền mới.
#
# `confirm_receipt` ngay trên KHÔNG bị đụng: mở cả lập lẫn xác nhận cho một vai là bỏ tách bạch
# trách nhiệm, và đó là một quyết định phải có chữ ký riêng. Luật 7 đo cả hai chiều.
def lap_phieu_quy(data: PhieuQuyIn,
                  u: User = Depends(require_roles("ketoan", "thu_quy",
                                                  mo_ta="lập phiếu quỹ tiền mặt")),
                  db: Session = Depends(get_db)):
    from datetime import date as _date
    from app.services import phieu_quy as PQ
    try:
        ngay = _date.fromisoformat(data.ngay) if data.ngay else _date.today()
    except ValueError:
        raise HTTPException(422, "Ngày phải dạng yyyy-mm-dd")
    try:
        p, bt = PQ.lap(db, u, chieu=data.chieu, ngay=ngay, so_tien=data.so_tien,
                       ly_do=data.ly_do, noi_dung=data.noi_dung,
                       ten_doi_tuong=data.ten_doi_tuong, ma_doi_tuong=data.ma_doi_tuong,
                       booking_id=data.booking_id, khoan_muc=data.khoan_muc)
    except ValueError as ex:
        raise HTTPException(422, str(ex))
    return {"phieu": PQ.ra(p), "but_toan": bt,
            "message": f"Đã lập và ghi sổ {p.code} theo quy tắc {p.quy_tac}"}


@router.get("/receipts/quy/phieu")
def danh_sach_phieu_quy(tu_ngay: str = "", den_ngay: str = "", chieu: str = "",
                        u: User = Depends(require_roles("ketoan", "thu_quy",
                                                        mo_ta="đọc sổ quỹ tiền mặt")),
                        db: Session = Depends(get_db)):
    from datetime import date as _date
    from app.services import phieu_quy as PQ
    try:
        tn = _date.fromisoformat(tu_ngay) if tu_ngay else None
        dn = _date.fromisoformat(den_ngay) if den_ngay else None
    except ValueError:
        raise HTTPException(422, "Ngày phải dạng yyyy-mm-dd")
    return {"phieu": [PQ.ra(p) for p in PQ.danh_sach(db, tn, dn, chieu)]}


@router.get("/receipts/quy/ly-do")
def ly_do_phieu_quy(chieu: str = "thu",
                    u: User = Depends(require_roles("ketoan", "thu_quy",
                                                    mo_ta="danh mục lý do phiếu quỹ")),
                    db: Session = Depends(get_db)):
    """Những lý do bảng quy ước ĐANG nhận. Đọc sống từ bảng quy tắc — thêm một quy tắc là một lý
    do mới tự hiện ra ở ô chọn, không ai phải sửa hai chỗ."""
    from app.services import phieu_quy as PQ
    try:
        return {"ly_do": PQ.ly_do_nhan_duoc(db, chieu)}
    except ValueError as ex:
        raise HTTPException(422, str(ex))


class CashIn(BaseModel):
    booking_id: int
    amount: float
    payer: str = ""
    note: str = ""


@router.post("/receipts/cash", status_code=201)
# ĐỢT R4c-4 02/11/2026 — CỬA NÓI ĐÚNG NHƯ MENU ĐÃ NÓI.
#
# `access.MAN_HINH_THU_QUY` mở `/collections` cho `thu_quy` kèm lời chú thích ghi rõ bốn cửa của
# thủ quỹ nằm sau nó, trong đó có **"phiếu thu tiền mặt"**. Nhưng cửa này gác bằng
# `require_roles("ketoan",)`, và màn hình cũng chỉ hiện khối lập phiếu cho `ketoan`. Menu nói thủ
# quỹ có, cửa nói chỉ kế toán — thủ quỹ bấm vào thì nhận 403 trên một màn hình menu vừa mời họ vào.
#
# ĐÂY KHÔNG PHẢI NỚI QUYỀN MỚI: bảng menu đã ký cấp màn hình này cho thủ quỹ từ Đợt E2b-0. Đợt này
# chỉ làm cửa khớp với bảng ấy. Chủ tịch chốt 02/11/2026 ("cả hai vai đều lập được", không thêm
# bước xác nhận).
#
# CÒN MỘT CỬA NỮA cùng lời chú thích ấy nhắc tới — `confirm_receipt` ("xác nhận phiếu thu"). Đợt
# này KHÔNG đụng: mở cả lập lẫn xác nhận cho một vai là bỏ tách nhiệm, và đó là một quyết định
# phải có chữ ký riêng chứ không phải hệ quả của câu trả lời hôm nay.
def cash_receipt(data: CashIn, u: User = Depends(require_roles("ketoan", "thu_quy")), db: Session = Depends(get_db)):
    b = db.get(Booking, data.booking_id)
    if not b: raise HTTPException(404, "Không có booking")
    if (data.amount or 0) <= 0: raise HTTPException(422, "Số tiền phải > 0")
    r = P.cash_receipt(db, u, b, data.amount, data.payer, data.note)
    return {"receipt": receipt_out(r, db), "message": f"Đã lập phiếu thu tiền mặt {r.code}"}


@router.get("/collections/summary")
def collections_summary(chi_con_no: bool = False,
                        u: User = Depends(require_roles(*AC.BOOKING_ROLES, mo_ta="tổng quan thu tiền")), db: Session = Depends(get_db)):
    """Tổng quan thu tiền: booking còn phải thu, giao dịch chờ Kế toán, phiếu thu chờ xác nhận.

    Vì sao viết lại ngày 10/9/2026 (đo trên Render: 106.832 ms):

    Bản cũ nạp TOÀN BỘ booking rồi với mỗi booking gọi thêm hai câu truy vấn – một để cộng phiếu thu
    (`paid_amount`) và một để lấy mã tour (`b.tour` nạp muộn). Trên 10.074 booking là hơn hai mươi nghìn
    câu, mỗi câu một vòng đi–về tới Postgres. Máy không chậm, cái chậm là số vòng.

    Bản mới gộp phiếu thu thành MỘT câu cộng theo booking và nối bảng tours để lấy mã, nên tổng cộng chỉ
    còn vài câu bất kể bao nhiêu booking. Từng con số giữ nguyên công thức cũ:
    `còn phải thu = (amount − discount) − tổng phiếu thu chưa hủy`.

    Hai chỗ khác cố ý sửa hành vi, và lý do:

      * THÊM hàng rào phạm vi pháp nhân `PV.loc`. Mọi đường khác đọc booking đều có nó (xem
        `_bookings_query` trong routes.py); riêng đường này thiếu từ đầu, nên một Kế toán chỉ được xem
        một pháp nhân vẫn nhìn thấy công nợ của pháp nhân khác qua màn hình Thu tiền. Đây là lỗ hở
        quyền, không phải là tính năng – vá lại thì danh sách của một số người sẽ NGẮN ĐI, và ngắn đi
        mới là đúng.
      * Cộng sẵn `tong_con_phai_thu` và `so_booking_con_no` ở máy chủ. Giao diện đang tự cộng trên toàn
        bộ mảng; máy chủ cộng thì con số vẫn thế mà giao diện không phải giữ cả vạn dòng để cộng.

    `chi_con_no=1` chỉ trả những booking còn nợ – dùng cho màn hình công nợ. Mặc định vẫn trả đủ để
    không làm hỏng ô chọn booking đang có sẵn.
    """
    tra = P.paid_amount_map(db)          # {booking_id: đã thu} – một câu cộng cho tất cả
    qb = (select(Booking, Tour.code).outerjoin(Tour, Tour.id == Booking.tour_id)
          .order_by(desc(Booking.created_at)))
    qb = PV.loc(qb, Booking, u)          # P6: phạm vi pháp nhân – thiếu ở đây từ đầu, xem giải thích trên
    vis = AC.sales_ids_visible(db, u)
    if vis is not None: qb = qb.where(Booking.sales_id.in_(vis))
    rows = []
    tong_no = 0.0
    so_no = 0
    for b, ma_tour in db.execute(qb):
        tong = (b.amount or 0) - (b.discount or 0)
        due = tong - tra.get(b.id, 0.0)
        if due > 0:
            tong_no += due; so_no += 1
        elif chi_con_no:
            continue
        rows.append({"booking_id": b.id, "code": b.code, "tour_code": ma_tour or "", "customer_name": b.customer_name,
                     "total": tong, "paid": (b.paid or 0), "due": due})
    return {"bookings": rows,
            "tong_con_phai_thu": tong_no, "so_booking_con_no": so_no,
            "pending_txns": db.execute(select(func.count()).select_from(BankTransaction)
                                       .where(BankTransaction.match_status == "cho_ke_toan")).scalar() or 0,
            "pending_receipts": db.execute(select(func.count()).select_from(Receipt)
                                           .where(Receipt.status == "tu_dong")).scalar() or 0}


# ---------- VPM-5: phân bổ một khoản tiền cho nhiều booking ----------
class DongPhanBoIn(BaseModel):
    booking_id: int
    so_tien: float
    ghi_chu: str = ""


class PhanBoIn(BaseModel):
    dong: list[DongPhanBoIn]


@router.get("/bank-transactions/{tid}/phan-bo")
def xem_phan_bo(tid: int, u: User = Depends(require_roles(*AC.FINANCE_ROLES, mo_ta="phân bổ tiền vào")),
                db: Session = Depends(get_db)):
    """Một khoản tiền đã chia cho ai, còn lại bao nhiêu, và những dòng đã huỷ kèm lý do."""
    from app.services import phan_bo_tien as PB
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    return PB.bang(db, t)


@router.post("/bank-transactions/{tid}/phan-bo")
def them_phan_bo(tid: int, data: PhanBoIn, u: User = Depends(require_roles("ketoan", "cntt")),
                 db: Session = Depends(get_db)):
    """Chia khoản tiền cho nhiều booking. Cả lô được kiểm TRƯỚC khi ghi dòng đầu tiên."""
    from app.services import phan_bo_tien as PB
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    try:
        return PB.phan_bo(db, u, t, [d.model_dump() for d in data.dong])
    except ValueError as e:
        raise HTTPException(422, str(e))


class DongPhanBoRaIn(BaseModel):
    nghia_vu_id: int
    dot_id: int | None = None
    so_tien: float
    ghi_chu: str = ""


class PhanBoRaIn(BaseModel):
    dong: list[DongPhanBoRaIn]


# ĐỢT E5 13/10/2026 — cửa phân bổ tiền RA. Nằm DƯỚI tiền tố `/bank-transactions` y như cửa tiền
# vào, và vì đúng lý do đã ghi ở cửa huỷ bên dưới: mở một tiền tố mới là xin thêm một nhóm API
# cho mọi vai đang xem màn hình này — nới quyền chỉ vì đặt tên đường dẫn cho gọn. Danh sách vai
# cũng chép đúng cửa tiền vào, không rộng hơn một vai nào.
@router.post("/bank-transactions/{tid}/phan-bo-ra")
def them_phan_bo_ra(tid: int, data: PhanBoRaIn, u: User = Depends(require_roles("ketoan", "cntt")),
                    db: Session = Depends(get_db)):
    """Chia một khoản tiền RA cho nhiều nghĩa vụ. Cả lô được kiểm TRƯỚC khi ghi dòng đầu tiên."""
    from app.services import phan_bo_tien as PB
    t = db.get(BankTransaction, tid)
    if not t: raise HTTPException(404, "Không có giao dịch")
    try:
        return PB.phan_bo_ra(db, u, t, [d.model_dump() for d in data.dong])
    except ValueError as e:
        raise HTTPException(422, str(e))


class HuyPhanBoIn(BaseModel):
    ly_do: str = ""


# Cửa huỷ nằm DƯỚI tiền tố /bank-transactions chứ không ở một tiền tố mới: màn hình Thu tiền đã
# được cấp tiền tố ấy rồi. Mở "/api/v1/phan-bo-tien" là xin thêm một nhóm API cho mọi vai trò đang
# xem màn hình này – nới quyền chỉ vì đặt tên đường dẫn cho gọn.
@router.post("/bank-transactions/phan-bo/{pid}/huy")
def huy_phan_bo(pid: int, data: HuyPhanBoIn, u: User = Depends(require_roles("ketoan", "cntt")),
                db: Session = Depends(get_db)):
    """Huỷ một dòng phân bổ (kèm phiếu thu của nó). Huỷ chứ không xoá, và bắt buộc có lý do."""
    from app.services import phan_bo_tien as PB
    from app.models.phan_bo_tien import PhanBoTien
    pb = db.get(PhanBoTien, pid)
    if not pb: raise HTTPException(404, "Không có dòng phân bổ")
    try:
        return PB.huy_dong(db, u, pb, data.ly_do)
    except ValueError as e:
        raise HTTPException(422, str(e))
