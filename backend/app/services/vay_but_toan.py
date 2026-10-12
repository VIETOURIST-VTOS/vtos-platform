"""V12 – nối khế ước vay với sổ kế toán, và mã đáo hạn nối hai chân một lần đảo nợ.

Lệnh Đợt 2, việc V12. Hiện trạng trước đợt này: đã có bảng khế ước, đã có lịch trả nợ, đã có 13 quy
ước tài chính và cổng đáo hạn – nhưng KHÔNG NỐI. Đánh dấu một kỳ "đã trả" trên màn hình tài chính
không sinh bút toán nào, nên dư nợ vay trên sổ và lịch trả nợ là hai con số sống riêng.

Đo được ngày 08/9/2026: 59 khoản vay, dư nợ 68.561.868.945đ, VTOS mới theo dõi 9 khế ước (19,76 tỷ).
Hai con số sống riêng ở quy mô đó thì đối chiếu bằng tay là việc không ai làm nổi mỗi tháng.

────────────────────────────────────────────────────────────────────────────────
BA ĐIỀU KHÔNG ĐƯỢC LÀM KHÁC, VÌ CHỦ TỊCH ĐÃ QUYẾT
────────────────────────────────────────────────────────────────────────────────

1. LÃI VAY GHI KHI TRẢ, KHÔNG TRÍCH TRƯỚC (quyết định 08/9/2026, mục 5). Hệ quả phải nói ra chứ
   không được giấu: tháng nào trả lãi thì tháng đó gánh toàn bộ, tháng không trả thì lãi bằng 0 – nên
   lãi lỗ THEO THÁNG không dùng để so sánh giữa các tháng. Số theo năm và theo kỳ báo cáo vẫn đúng.
   Tệp này vì vậy KHÔNG có hàm trích trước lãi. Ai thêm vào sau phải hỏi lại Chủ tịch trước.

2. GỐC VÀ LÃI LÀ HAI BÚT TOÁN, không bù trừ thành một dòng. Bù trừ thì dư nợ vay trên sổ không bao
   giờ đứng ở đỉnh và dòng tiền mất một vòng.

3. ĐÁO HẠN CHỈ CANH HAI CHÂN NGÂN HÀNG (quyết định 08/9/2026, mục 7). Công ty không dùng tiền vay
   ngoài ngân hàng để chạy đáo hạn; nếu về sau có thì phải khai thành một khoản vay thật đứng tên
   người cho vay, chứ không nới cổng cho lọt.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO GHI SỔ ĐI QUA ĐÂY CHỨ KHÔNG GỌI THẲNG post_entry Ở MÀN HÌNH
────────────────────────────────────────────────────────────────────────────────

Ba quy ước VAY_NHAN, VAY_TRA_GOC, VAY_LAI đã có trong bảng quy ước hạch toán. Nếu màn hình tự dựng
lấy cặp tài khoản thì bảng quy ước thành bản trang trí: sửa quy ước một chỗ mà chỗ kia vẫn chạy số
cũ, và không ai biết cho tới lúc đối chiếu. Tệp này ĐỌC bảng quy ước ra rồi mới ghi.
"""
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.finance import FinContract, FinSchedule
from app.models.accounting import JournalEntry, JournalLine
from app.services import accounting as ACC

# Kỳ nào ghi bằng quy ước nào. Viết thẳng ra chứ không suy từ tên: suy thì một loại thêm sau sẽ tự
# rơi vào một quy ước mà không ai chọn cho nó.
QUY_UOC_THEO_KY = {
    "nhan_vay": "VAY_NHAN",
    "giai_ngan": "VAY_NHAN",
    "tra_goc": "VAY_TRA_GOC",
    "tra_lai": "VAY_LAI",
}
# Kỳ thu hồi (cho vay ra) không thuộc V12 – V12 nói về khoản đi vay.
KY_KHONG_GHI = ("thu_hoi",)


class CongVay(HTTPException):
    def __init__(self, ma: str, thong_diep: str, **them):
        super().__init__(422, {"gate": ma, "message": thong_diep, **them})


def _quy_uoc(db: Session, ma: str, ngay: date | None = None) -> dict:
    """Đọc cặp tài khoản từ BẢNG quy ước trong cơ sở dữ liệu, không từ hằng số trong mã.

    Kế toán sửa được quy ước trên màn hình, và bản sửa có ngày hiệu lực. Đọc từ hằng số MAC_DINH thì
    tệp này chạy số của ngày đầu tiên mãi mãi, còn màn hình hiển thị số mới – hai nơi nói hai điều và
    không ai biết cho tới lúc đối chiếu.
    """
    from app.models.hach_toan import QuyTacHachToan
    from sqlalchemy import desc
    on = ngay or date.today()
    q = db.execute(
        select(QuyTacHachToan)
        .where(QuyTacHachToan.ma == ma, QuyTacHachToan.status == "active",
               QuyTacHachToan.effective_from <= on)
        .order_by(desc(QuyTacHachToan.effective_from), desc(QuyTacHachToan.id))).scalars().first()
    if q is not None:
        return {"ma": q.ma, "ten": q.ten, "no": q.tk_no, "co": q.tk_co,
                "can_cu": q.can_cu, "hieu_luc_tu": str(q.effective_from)}
    raise CongVay("THIEU_QUY_UOC",
                  f"Không có quy ước hạch toán '{ma}' đang hiệu lực ngày {on}. Bảng quy ước là nguồn "
                  "duy nhất của cặp tài khoản – thiếu thì DỪNG, không tự dựng lấy.")


def xem_truoc(db: Session, s: FinSchedule) -> dict:
    """Bút toán SẼ ghi cho một kỳ. Chỉ đọc – dùng cho màn hình xem trước và cho phép thử."""
    c = db.get(FinContract, s.contract_id)
    if c is None:
        raise CongVay("KHONG_CO_KHE_UOC", f"Kỳ này trỏ tới khế ước {s.contract_id} không tồn tại")
    if s.kind in KY_KHONG_GHI:
        raise CongVay("KY_KHONG_GHI_SO",
                      f"Kỳ loại '{s.kind}' không thuộc phạm vi V12 (V12 nói về khoản ĐI VAY)")
    ma = QUY_UOC_THEO_KY.get(s.kind)
    if ma is None:
        raise CongVay("KY_LA", f"Không biết ghi sổ cho kỳ loại '{s.kind}'")
    q = _quy_uoc(db, ma, s.done_on or s.due_date)
    so_tien = float(s.amount or 0)
    if so_tien <= 0:
        raise CongVay("SO_TIEN_KHONG_HOP_LE", f"Kỳ có số tiền {so_tien} – không ghi sổ được")
    dien_giai = f"{q['ten']} – {c.partner} ({c.code}" + (f", kỳ {s.ky}" if s.ky else "") + ")"
    return {
        "quy_uoc": q["ma"], "quy_uoc_ten": q["ten"],
        "ngay": s.done_on or s.due_date, "dien_giai": dien_giai, "so_tien": so_tien,
        "dong": [{"account": q["no"], "debit": so_tien, "credit": 0,
                  "partner": c.partner, "partner_code": c.code},
                 {"account": q["co"], "debit": 0, "credit": so_tien,
                  "partner": c.partner, "partner_code": c.code}],
        # Mã đáo hạn đi vào source_ref để cổng đáo hạn nhìn thấy hai chân là một cặp.
        "source_ref": (f"dao_han:{s.ma_dao_han}" if s.ma_dao_han else f"khe_uoc:{c.code}:ky{s.id}"),
    }


def ghi_so(db: Session, s: FinSchedule, boi: str, vai: str, ngay: date | None = None) -> JournalEntry:
    """Ghi sổ MỘT kỳ và đánh dấu đã thực hiện. Ghi hai lần một kỳ là chuyện phải chặn tuyệt đối –
    dư nợ vay bị trừ hai lần thì báo cáo tài chính sai ở đúng chỗ kiểm toán mở ra đầu tiên."""
    if s.entry_id:
        raise CongVay("DA_GHI_SO",
                      f"Kỳ này đã ghi sổ (bút toán #{s.entry_id}). Ghi lại là trừ dư nợ hai lần.",
                      entry_id=s.entry_id)
    xt = xem_truoc(db, s)
    e = ACC.post_entry(db, boi, vai, ngay or xt["ngay"], xt["dien_giai"], xt["dong"],
                       source_type="khe_uoc_vay", source_ref=xt["source_ref"], nghiep_vu="khe_uoc_vay")
    s.entry_id = e.id
    s.status = "da_thuc_hien"
    s.done_on = s.done_on or (ngay or xt["ngay"])
    db.flush()
    return e


# ────────────────────────────── ĐÁO HẠN ──────────────────────────────
def dat_ma_dao_han(db: Session, tra_goc: FinSchedule, nhan_moi: FinSchedule, ma: str) -> None:
    """Nối hai chân một lần đảo nợ bằng một mã chung.

    Đảo nợ là: trả gốc khoản cũ và nhận giải ngân khoản mới trong cùng một ngày, tiền thực chất không
    ra khỏi ngân hàng. Ghi hai bút toán rời rạc thì sổ đúng nhưng KHÔNG ai đọc ra được đó là một lần
    đảo – và chỉ tiêu "tiền chi trả nợ gốc vay" trên báo cáo lưu chuyển tiền tệ bị thổi lên bằng
    đúng số tiền không hề chuyển đi đâu.
    """
    if tra_goc.kind != "tra_goc":
        raise CongVay("CHAN_SAI", f"Chân thứ nhất phải là kỳ trả gốc, đang là '{tra_goc.kind}'")
    if nhan_moi.kind not in ("nhan_vay", "giai_ngan"):
        raise CongVay("CHAN_SAI", f"Chân thứ hai phải là kỳ nhận vay, đang là '{nhan_moi.kind}'")
    if tra_goc.entry_id or nhan_moi.entry_id:
        raise CongVay("DA_GHI_SO", "Đặt mã đáo hạn phải làm TRƯỚC khi ghi sổ – bút toán đã ghi mang "
                                   "source_ref cũ, và cổng đáo hạn sẽ không nhìn thấy cặp này")
    tra_goc.ma_dao_han = ma
    nhan_moi.ma_dao_han = ma
    db.flush()


def dao_han_thieu_chan_tren_lich(db: Session) -> list[dict]:
    """Mã đáo hạn chỉ có MỘT chân trong lịch trả nợ.

    Khác với cong_chan.dao_han_thieu_chan – hàm ấy soi SỔ, hàm này soi LỊCH. Soi sổ chỉ thấy sau khi
    đã ghi; soi lịch thấy TRƯỚC, tức là còn kịp sửa mà không phải điều chỉnh bút toán.
    """
    ra = []
    q = (select(FinSchedule.ma_dao_han,
                func.count().label("so_chan"),
                func.count(func.distinct(FinSchedule.kind)).label("so_loai"))
         .where(FinSchedule.ma_dao_han != "")
         .group_by(FinSchedule.ma_dao_han))
    for ma, so_chan, so_loai in db.execute(q).all():
        if so_chan < 2 or so_loai < 2:
            ra.append({"ma_dao_han": ma, "so_chan": int(so_chan),
                       "vi_sao": ("chỉ có một chân" if so_chan < 2
                                  else "hai chân cùng loại – phải là một trả gốc và một nhận vay")})
    return ra


# ────────────────────────────── ĐỐI CHIẾU ──────────────────────────────
TK_VAY = "3411"


def du_no_tren_so(db: Session, company_id: int | None = None) -> float:
    """Dư nợ vay theo SỔ: số dư Có của 3411 (Có trừ Nợ)."""
    q = (select(func.coalesce(func.sum(JournalLine.credit), 0) -
                func.coalesce(func.sum(JournalLine.debit), 0))
         .where(JournalLine.account_code.like(TK_VAY + "%")))
    return float(db.execute(q).scalar() or 0)


def du_no_theo_lich(db: Session) -> float:
    """Dư nợ theo LỊCH TRẢ NỢ: tổng nhận vay đã thực hiện trừ tổng trả gốc đã thực hiện.

    Chỉ tính kỳ ĐÃ THỰC HIỆN. Tính cả kỳ kế hoạch thì con số này nói về tương lai, còn sổ nói về quá
    khứ – hai thứ không so được với nhau, và một phép so sai còn tệ hơn không so.
    """
    nhan = db.execute(select(func.coalesce(func.sum(FinSchedule.amount), 0))
                      .where(FinSchedule.kind.in_(("nhan_vay", "giai_ngan")),
                             FinSchedule.status == "da_thuc_hien")).scalar() or 0
    tra = db.execute(select(func.coalesce(func.sum(FinSchedule.amount), 0))
                     .where(FinSchedule.kind == "tra_goc",
                            FinSchedule.status == "da_thuc_hien")).scalar() or 0
    return float(nhan) - float(tra)


def doi_chieu(db: Session) -> dict:
    """Câu nghiệm thu của V12: dư nợ vay TRÊN SỔ khớp LỊCH TRẢ NỢ.

    Lệch một đồng cũng phải hiện ra, và phải nói được lệch vì đâu – kỳ đã đánh dấu thực hiện mà chưa
    ghi sổ là nguyên nhân thường gặp nhất, nên đếm riêng.
    """
    so = du_no_tren_so(db)
    lich = du_no_theo_lich(db)
    lech = round(so - lich, 2)
    chua_ghi = db.execute(
        select(FinSchedule).where(FinSchedule.status == "da_thuc_hien",
                                  FinSchedule.entry_id.is_(None),
                                  FinSchedule.kind.in_(tuple(QUY_UOC_THEO_KY)))).scalars().all()
    return {
        "du_no_tren_so": so, "du_no_theo_lich": lich, "lech": lech, "khop": abs(lech) < 0.005,
        "ky_da_thuc_hien_ma_chua_ghi_so": [
            {"id": k.id, "contract_id": k.contract_id, "ky": k.ky, "kind": k.kind,
             "amount": float(k.amount or 0), "due_date": k.due_date} for k in chua_ghi],
        "dao_han_thieu_chan": dao_han_thieu_chan_tren_lich(db),
        "ket_luan": ("Dư nợ vay trên sổ khớp lịch trả nợ." if abs(lech) < 0.005 else
                     f"LỆCH {lech:,.0f}đ giữa sổ và lịch trả nợ. "
                     + (f"Có {len(chua_ghi)} kỳ đã đánh dấu thực hiện mà chưa ghi sổ – nhiều khả năng "
                        "là nguyên nhân." if chua_ghi else
                        "Không có kỳ nào chưa ghi sổ, nên chênh lệch đến từ bút toán ghi tay ngoài "
                        "khế ước – phải tìm ra từng dòng.")),
    }
