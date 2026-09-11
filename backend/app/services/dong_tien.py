"""Dòng tiền – DT-2 (cửa chốt số dư) và DT-1 (hàm tiền khả dụng).

RỖNG KHÔNG PHẢI LÀ SỐ KHÔNG
---------------------------
Đây là luật xuyên suốt tệp này, và nó có giá của nó. Một bảng dòng tiền trả về RỖNG trông như bảng
hỏng; một bảng trả về 0 trông như bảng chạy tốt và công ty hết tiền. Cái thứ hai nguy hiểm hơn nhiều:
người đọc tin nó.

Nên mọi hàm ở đây trả về `None` kèm một `vi_sao` đọc được bằng tiếng Việt, chứ không bao giờ lấy 0
thay cho "chưa ai chốt". Màn hình hiện "Chưa có nguồn – Kế toán chốt số dư ngày …", không hiện "0 đ".

KHÔNG BÙ TRỪ GIỮA HAI PHÁP NHÂN
-------------------------------
Vietourist Holdings có tám pháp nhân. Cộng tiền của pháp nhân A với pháp nhân B rồi bảo "tập đoàn còn
ngần này" là sai cả về kế toán lẫn về thực tế: tiền của A không trả được nợ của B nếu không có hợp
đồng vay nội bộ và một lệnh chuyển thật. Nên `tien_kha_dung` nhận ĐÚNG MỘT `company_id` và không có
chế độ "tất cả". Muốn xem toàn cảnh thì gọi `tien_kha_dung_nhieu_phap_nhan`, và hàm ấy trả về một
DANH SÁCH từng pháp nhân – cố ý không có dòng tổng.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.banks import BankAccount
from app.models.core import Company
from app.models.dong_tien import NGUON_TIEN, ChotSoDu
from app.models.finance import FinContract
from app.models.ops import PaymentRequest
from app.models.payments import BankTransaction

# CHIA TẦNG – chốt của Chủ tịch 11/9/2026.
#
# Ngày 11/9 có hai làn cùng viết DT-1 và DT-3. Không bỏ bên nào: tệp này giữ tầng CỬA (bảng
# `chot_so_du`, bước chuyển CSDL, đường POST cho kế toán chốt số, màn hình), còn tầng TÍNH lấy của
# làn Phân quyền ở `dong_tien_ky.py` và `lam_tron_tien.py`.
#
# Ranh giới: tệp này ĐI TÌM SỐ, tệp kia CỘNG TRỪ. Không chỗ nào trong tệp này được tự cộng lại bốn
# mốc hay tự quyết "thiếu thành phần thì tính sao" – hỏi lại `dong_tien_ky` là xong. Hai nơi cùng
# cộng một bảng là hai con số cho cùng một công ty, và lần sửa đầu tiên sẽ chỉ sửa một nơi.
#
# Đổi sang mốc của `dong_tien_ky` sửa luôn MỘT LỖI THẬT của bản cũ trong tệp này: mốc tháng bị lệch
# một ngày. Bản cũ lấy `cộng_tháng(d, n) − 1 ngày`, nên 31/01 + 1 tháng ra 27/02; v1.1 ghi thẳng
# 31/01 + 1 tháng = 28/02. Một ngày ấy đủ để một kỳ trả gốc rơi ra ngoài cột.
from app.services import dong_tien_ky as DTK
from app.services.lam_tron_tien import lam_tron

# Đề nghị chi đã qua đủ chữ ký nhưng tiền chưa rời tài khoản. Đây là tiền đã hứa, không còn khả dụng.
# Trạng thái sau 'cho_chi' là 'da_chi' – lúc ấy tiền đã ra và số dư ngân hàng đã phản ánh.
TRANG_THAI_DA_DUYET_CHUA_CHUYEN = ("cho_chi",)

# Khoản ký quỹ giấy phép lữ hành. Tiền nằm trong tài khoản phong toả của ngân hàng: nó CÓ trong số dư
# nhưng không tiêu được, nên phải trừ ra. Giữ riêng thành một dòng ghi nhớ trên bảng, không bù trừ
# với nghĩa vụ của công ty.
KY_QUY_GIAY_PHEP = "ky_quy"


# --------------------------------------------------------------------------------- DT-2 · cửa chốt

class LoiChot(ValueError):
    """Lỗi nghiệp vụ của cửa chốt số dư. Thông báo phải nói người dùng cần làm gì."""


def _kiem_dau_vao(db: Session, company_id: int | None, nguon: str,
                  tai_khoan_id: int | None, den_ngay: date, so_du: float) -> BankAccount | None:
    if not company_id:
        raise LoiChot("Phải chọn pháp nhân. Số dư không gắn pháp nhân thì không cộng vào tiền khả "
                      "dụng của bất kỳ pháp nhân nào – và cũng không được mặc định về công ty mẹ.")
    if db.get(Company, company_id) is None:
        raise LoiChot("Không có pháp nhân này")
    if nguon not in NGUON_TIEN:
        raise LoiChot(f"Nguồn tiền phải là một trong: {', '.join(NGUON_TIEN)}")

    tk = None
    if nguon == "ngan_hang":
        if not tai_khoan_id:
            raise LoiChot("Chốt số dư ngân hàng phải chọn TỪNG tài khoản. Gộp các tài khoản thành "
                          "một dòng thì lúc lệch không tìm ra lệch ở tài khoản nào.")
        tk = db.get(BankAccount, tai_khoan_id)
        if tk is None:
            raise LoiChot("Không có tài khoản ngân hàng này")
    elif tai_khoan_id:
        raise LoiChot("Quỹ tiền mặt không gắn với tài khoản ngân hàng")

    if den_ngay > date.today():
        raise LoiChot(f"Không chốt được cho ngày mai. Đối soát là việc đã làm xong, không phải việc "
                      f"dự kiến – hôm nay là {date.today():%d/%m/%Y}.")
    if so_du is None:
        raise LoiChot("Phải có số dư. Chốt mà không có số thì không phải một lần chốt.")
    return tk


def so_may_cong_duoc(db: Session, tk: BankAccount | None, den_ngay: date) -> float | None:
    """Số máy tự cộng tới hết ngày, để ĐỐI CHIẾU với số người ký – không phải để thay nó.

    Trả RỖNG khi máy không có cơ sở để cộng: quỹ tiền mặt (không có luồng giao dịch), hoặc tài khoản
    chưa nối SePay. Rỗng ở đây nghĩa là "không đối chiếu được", khác hẳn 0 là "cộng ra bằng không" –
    và phân biệt được hai chuyện ấy là điểm khác nhau giữa một cột lệch dùng được và một cột lệch
    lúc nào cũng kêu.
    """
    if tk is None or not tk.sepay_account_number:
        return None
    dau = float(tk.opening_balance) if tk.opening_balance is not None else None
    if dau is None:
        return None
    het_ngay = datetime.combine(den_ngay, datetime.max.time())
    vao = ra = 0.0
    for t in db.execute(select(BankTransaction).where(
            BankTransaction.account_number == tk.sepay_account_number,
            BankTransaction.transaction_date <= het_ngay)).scalars():
        if t.transfer_type == "in":
            vao += float(t.amount or 0)
        else:
            ra += float(t.amount or 0)
    return round(dau + vao - ra, 2)


def chot(db: Session, boi: str, company_id: int | None, nguon: str, tai_khoan_id: int | None,
         den_ngay: date, so_du: float, ly_do_lech: str = "", ghi_chu: str = "") -> ChotSoDu:
    """Ghi một bản chốt. Chốt lại cùng một ngày thì bản cũ bị THAY THẾ, không bị xoá."""
    tk = _kiem_dau_vao(db, company_id, nguon, tai_khoan_id, den_ngay, so_du)

    may = so_may_cong_duoc(db, tk, den_ngay)
    lech = None if may is None else round(float(so_du) - may, 2)
    if lech not in (None, 0) and not (ly_do_lech or "").strip():
        raise LoiChot(
            f"Số chốt lệch {lech:,.0f} đ so với số máy cộng từ sao kê ({may:,.0f} đ). Phải ghi lý do "
            f"– giao dịch SePay chưa đẩy về, phí ngân hàng chưa hạch toán, hay sổ ghi sai. Lệch mà "
            f"không ai giải thích thì lần sau không ai biết lệch ấy đã được xem chưa.")

    cu = db.execute(select(ChotSoDu).where(
        ChotSoDu.company_id == company_id, ChotSoDu.nguon == nguon,
        ChotSoDu.tai_khoan_id == tai_khoan_id, ChotSoDu.den_ngay == den_ngay,
        ChotSoDu.trang_thai == "hieu_luc")).scalars().first()
    if cu is not None:
        cu.trang_thai = "da_thay_the"
        db.flush()

    moi = ChotSoDu(
        company_id=company_id, nguon=nguon, tai_khoan_id=tai_khoan_id, den_ngay=den_ngay,
        so_du=float(so_du), so_may_cong=may, lech=lech,
        ly_do_lech=(ly_do_lech or "").strip()[:300],
        thay_the_id=cu.id if cu is not None else None,
        boi=boi, ghi_chu=(ghi_chu or "").strip())
    db.add(moi)
    db.flush()
    return moi


def ban_chot_moi_nhat(db: Session, company_id: int, nguon: str,
                      tai_khoan_id: int | None, den_ngay: date | None = None) -> ChotSoDu | None:
    """Bản chốt hiệu lực GẦN NHẤT không muộn hơn `den_ngay`. RỖNG nếu chưa ai chốt bao giờ.

    KHÔNG nội suy sang ngày chưa chốt: bản chốt ngày 08/9 trả lời cho ngày 08/9, và DT-1 nói thẳng
    mốc ấy ra. Lấy số ngày 08/9 rồi gọi nó là số dư ngày 11/9 là bịa ra một lần đối soát không ai làm.
    """
    q = select(ChotSoDu).where(
        ChotSoDu.company_id == company_id, ChotSoDu.nguon == nguon,
        ChotSoDu.tai_khoan_id == tai_khoan_id, ChotSoDu.trang_thai == "hieu_luc")
    if den_ngay is not None:
        q = q.where(ChotSoDu.den_ngay <= den_ngay)
    return db.execute(q.order_by(ChotSoDu.den_ngay.desc(), ChotSoDu.id.desc())).scalars().first()


# ----------------------------------------------------------------------- DT-1 · tiền khả dụng

# Tài khoản thu hộ khách. Tiền của khách nằm trong tài khoản công ty nhưng KHÔNG phải tiền công ty:
# tour gom khách lẻ, visa, vé máy bay – công ty thu hộ rồi chi hộ. Xem app/services/cong_chan.py.
TK_THU_HO_KHACH = "3388"


def _du_co(db: Session, company_id: int, ma_tk: str, den_ngay: date) -> float | None:
    """Dư CÓ của một tài khoản kế toán tới hết ngày, chỉ tính bút toán ĐÃ GHI SỔ.

    Trả RỖNG khi pháp nhân này chưa có bút toán nào đã ghi sổ chạm tài khoản ấy – nghĩa là sổ chưa
    nói gì về khoản này, chứ không phải khoản ấy bằng không.
    """
    from app.models.accounting import JournalEntry, JournalLine
    from sqlalchemy import func

    r = db.execute(
        select(func.count(JournalLine.id),
               func.coalesce(func.sum(JournalLine.credit), 0.0),
               func.coalesce(func.sum(JournalLine.debit), 0.0))
        .select_from(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalLine.account_code.like(f"{ma_tk}%"),
               JournalEntry.company_id == company_id,
               JournalEntry.status == "da_ghi_so",
               JournalEntry.entry_date <= den_ngay)).one()
    so_dong, co, no = int(r[0]), float(r[1] or 0), float(r[2] or 0)
    if so_dong == 0:
        return None
    return round(co - no, 2)


def _so_dong_da_ghi_so(db: Session, company_id: int, den_ngay: date) -> int:
    """Sổ của pháp nhân này có đang được ghi không – đếm dòng bút toán ĐÃ GHI SỔ ở MỌI tài khoản.

    Dùng để phân biệt "tài khoản này bằng không" với "sổ này chưa ai ghi". Hai chuyện nhìn giống hệt
    nhau khi chỉ soi một tài khoản, mà kết luận thì ngược nhau.
    """
    from app.models.accounting import JournalEntry, JournalLine
    from sqlalchemy import func
    return int(db.execute(
        select(func.count(JournalLine.id))
        .select_from(JournalLine).join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(JournalEntry.company_id == company_id,
               JournalEntry.status == "da_ghi_so",
               JournalEntry.entry_date <= den_ngay)).scalar() or 0)


def tien_kha_dung(db: Session, company_id: int, den_ngay: date | None = None) -> dict:
    """DT-1. Tiền MỘT pháp nhân thật sự tiêu được hôm nay, kèm mốc đối soát.

        số dư ngân hàng đã đối soát
      + quỹ tiền mặt đã kiểm kê
      − tiền thu hộ khách          (tiền trong tài khoản, không phải tiền của công ty)
      − ký quỹ giấy phép lữ hành   (bị phong toả, có mà không tiêu được)
      − lệnh chi đã duyệt chưa chuyển

    THIẾU MỘT ĐẦU VÀO THÌ TRẢ RỖNG, KHÔNG TRẢ 0. Một bảng trả 0 trông như bảng chạy tốt và công ty
    hết tiền – người đọc tin nó, và đó là kiểu sai đắt nhất trong cả phân hệ này. Trả rỗng thì người
    đọc đi hỏi, và câu `vi_sao` nói sẵn phải hỏi ai.

    KHÔNG nhận nhiều pháp nhân. Tiền của pháp nhân A không trả được nợ của B nếu không có hợp đồng
    vay nội bộ và một lệnh chuyển thật.
    """
    hom_nay = den_ngay or date.today()
    ct = db.get(Company, company_id)
    if ct is None:
        raise LoiChot("Không có pháp nhân này")

    thieu: list[str] = []
    moc: list[date] = []

    # --- 1. Ngân hàng: TỪNG tài khoản phải có bản chốt riêng. Thiếu một tài khoản là thiếu, không
    #        phải cộng những cái có rồi coi như xong – tổng thiếu một tài khoản trông y hệt tổng đủ.
    #
    # DANH MỤC TÀI KHOẢN KHÔNG BIẾT TÀI KHOẢN NÀO CỦA PHÁP NHÂN NÀO. `bank_accounts_cat` không có
    # cột company_id (đo 11/9/2026). Nên KHÔNG duyệt toàn bộ danh mục ở đây: làm thế thì pháp nhân A
    # bị tính là "thiếu chốt" cho cả những tài khoản của pháp nhân B, và mọi pháp nhân đều rỗng mãi.
    #
    # Tập tài khoản của một pháp nhân suy từ chính SỔ CHỐT: tài khoản nào pháp nhân này đã từng chốt
    # thì thuộc về nó, và từ đó trở đi ngày nào cũng phải có chốt. Cách này đúng ngay từ ngày đầu và
    # tự hết khi `bank_accounts_cat` có cột pháp nhân – lúc ấy đổi đúng truy vấn dưới đây.
    # Việc thêm cột company_id vào danh mục tài khoản: đã ghi vào bản bàn giao, thuộc làn Kế toán.
    tk_da_tung_chot = list(db.execute(
        select(ChotSoDu.tai_khoan_id).where(
            ChotSoDu.company_id == company_id, ChotSoDu.nguon == "ngan_hang",
            ChotSoDu.tai_khoan_id != None).distinct()).scalars())      # noqa: E711
    ngan_hang = 0.0
    chi_tiet_nh = []
    if not tk_da_tung_chot:
        thieu.append("chưa chốt số dư tài khoản ngân hàng nào cho pháp nhân này")
    for tid in tk_da_tung_chot:
        t = db.get(BankAccount, tid)
        ten = f"{t.code} ({t.bank_name})" if t else f"tài khoản #{tid}"
        b = ban_chot_moi_nhat(db, company_id, "ngan_hang", tid, hom_nay)
        if b is None:
            thieu.append(f"chưa chốt số dư tài khoản {ten} tính đến {hom_nay:%d/%m/%Y}")
            chi_tiet_nh.append({"tai_khoan": t.code if t else None, "so_du": None, "den_ngay": None})
            continue
        ngan_hang += float(b.so_du)
        moc.append(b.den_ngay)
        chi_tiet_nh.append({"tai_khoan": t.code if t else None,
                            "so_du": float(b.so_du), "den_ngay": b.den_ngay})

    # --- 2. Quỹ tiền mặt
    q = ban_chot_moi_nhat(db, company_id, "tien_mat", None, hom_nay)
    if q is None:
        thieu.append("chưa kiểm kê quỹ tiền mặt")
        tien_mat = None
    else:
        tien_mat = float(q.so_du)
        moc.append(q.den_ngay)

    # --- 3. Thu hộ khách (dư Có 3388).
    #
    # Một tài khoản không có bút toán nào là câu trả lời MẬP MỜ, và hai nghĩa của nó dẫn tới hai con
    # số rất khác nhau: hoặc pháp nhân này không thu hộ ai cả (đúng là 0), hoặc sổ của pháp nhân này
    # chưa được ghi (thì 0 là con số bịa, và nó bịa theo chiều NGUY HIỂM – khai khống tiền khả dụng).
    #
    # Phân biệt bằng một câu hỏi khác: SỔ CỦA PHÁP NHÂN NÀY CÓ ĐANG ĐƯỢC GHI KHÔNG. Có bút toán đã
    # ghi sổ ở bất kỳ tài khoản nào mà 3388 trống ⇒ sổ đang sống và nó nói không có khoản thu hộ nào:
    # 0 là số thật. Không có bút toán nào ⇒ sổ chưa nói gì: RỖNG, và bảng nói ra điều đó.
    thu_ho = _du_co(db, company_id, TK_THU_HO_KHACH, hom_nay)
    if thu_ho is None:
        if _so_dong_da_ghi_so(db, company_id, hom_nay) > 0:
            thu_ho = 0.0
        else:
            thieu.append(f"sổ kế toán của pháp nhân này chưa có bút toán nào đã ghi sổ tính đến "
                         f"{hom_nay:%d/%m/%Y}, nên chưa biết tiền thu hộ khách (TK "
                         f"{TK_THU_HO_KHACH}) là bao nhiêu")

    # --- 4. Ký quỹ giấy phép lữ hành
    ky_quy = 0.0
    co_ky_quy = False
    for hd in db.execute(select(FinContract).where(
            FinContract.kind == KY_QUY_GIAY_PHEP,
            FinContract.company_id == company_id)).scalars():
        con = hd.outstanding if hd.outstanding is not None else hd.principal
        if con is None:
            thieu.append(f"khế ước ký quỹ {hd.code} chưa có số dư")
            continue
        ky_quy += float(con)
        co_ky_quy = True
    if not co_ky_quy and ky_quy == 0:
        ky_quy = 0.0   # không có khế ước ký quỹ nào là một câu trả lời đúng: pháp nhân này không ký quỹ

    # --- 5. Lệnh chi đã duyệt chưa chuyển
    da_duyet_chua_chuyen = 0.0
    for pr in db.execute(select(PaymentRequest).where(
            PaymentRequest.status.in_(TRANG_THAI_DA_DUYET_CHUA_CHUYEN),
            PaymentRequest.company_id == company_id)).scalars():
        da_duyet_chua_chuyen += float(pr.amount or 0)

    # --- Kết luận: PHÉP TÍNH KHÔNG NẰM Ở ĐÂY.
    #
    # Năm thành phần trên là việc của tệp này – mỗi cái đi qua một cửa thật. Cộng trừ chúng lại, và
    # quyết định "thiếu một thành phần thì ra số hay không", là việc của `dong_tien_ky.tien_kha_dung`.
    # Luật của hàm ấy: THIẾU MỘT THÀNH PHẦN LÀ KHÔNG RA SỐ, vì thành phần dễ thiếu nhất – lệnh chi đã
    # duyệt chưa chuyển – là một số TRỪ, bỏ nó đi thì tiền khả dụng LUÔN CAO HƠN sự thật.
    #
    # Số dư ngân hàng vào là RỖNG khi còn tài khoản chưa chốt, không phải tổng của những tài khoản đã
    # chốt: một tổng thiếu một tài khoản trông y hệt một tổng đủ.
    con_thieu_tk = any("tài khoản" in c for c in thieu)
    gia_tri = {
        "so_du_ngan_hang": None if (con_thieu_tk or not tk_da_tung_chot) else ngan_hang,
        "tien_mat": tien_mat,
        "thu_ho_khach": thu_ho,
        "ky_quy_lu_hanh": ky_quy,
        "lenh_chi_chua_chuyen": da_duyet_chua_chuyen,
    }
    # Mốc đối soát là ngày CŨ NHẤT trong các bản chốt: số này chỉ đáng tin tới mốc yếu nhất của nó.
    # Lấy ngày mới nhất là nói quá mức tin cậy của chính mình.
    doi_soat = min(moc) if moc else None
    tinh = DTK.tien_kha_dung(gia_tri, doi_soat)
    du_dau_vao = tinh["du_du_lieu"] and not thieu
    so_tien = tinh.get("so") if du_dau_vao else None

    # Hai danh sách thiếu, và chúng KHÁC NHAU, nên giữ cả hai:
    #   · `thieu` của tệp này nói THIẾU Ở CỬA NÀO và phải đi hỏi ai  – "chưa chốt số dư tài khoản …".
    #   · `tinh["thieu"]` nói thiếu THÀNH PHẦN nào của công thức    – dùng để tô ô trống trên bảng.
    # Gộp hai cái làm một thì mất một trong hai câu, và câu bị mất luôn là câu chỉ ra người phải làm.
    return {
        "phap_nhan": {"id": ct.id, "ma": ct.code, "ten": ct.name},
        "tien_kha_dung": so_tien,
        "hien": tinh["hien"] if du_dau_vao else DTK.CHUA_XAC_MINH,
        "doi_soat_den_ngay": doi_soat if du_dau_vao else None,
        "vi_sao": "" if du_dau_vao else
                  "Chưa đủ đầu vào nên KHÔNG có số – ô này để trống chứ không phải bằng 0. Còn thiếu: "
                  + "; ".join(thieu or [tinh.get("cau_thieu", "")]),
        "con_thieu": thieu,
        "thieu_thanh_phan": tinh["thieu"],
        "chi_tiet_thanh_phan": tinh["chi_tiet"],
        "thanh_phan": {
            "ngan_hang_da_doi_soat": gia_tri["so_du_ngan_hang"],
            "quy_tien_mat_da_kiem_ke": tien_mat,
            "tru_thu_ho_khach": thu_ho,
            "tru_ky_quy_giay_phep": ky_quy,
            "tru_lenh_chi_da_duyet_chua_chuyen": da_duyet_chua_chuyen,
        },
        "chi_tiet_ngan_hang": chi_tiet_nh,
        # DT-8: hai dòng GHI NHỚ. Đã trừ khỏi tiền khả dụng ở trên, hiện riêng ở đây để người đọc
        # thấy tiền ấy tồn tại – và KHÔNG bù trừ với nghĩa vụ của công ty.
        "ghi_nho": {
            "tien_thu_ho_khach": thu_ho,
            "ky_quy_giay_phep_lu_hanh": ky_quy,
        },
    }


def tien_kha_dung_nhieu_phap_nhan(db: Session, company_ids: list[int],
                                  den_ngay: date | None = None) -> list[dict]:
    """Toàn cảnh = một DANH SÁCH từng pháp nhân. CỐ Ý không có dòng tổng.

    Một dòng tổng ở đây là một lời nói dối tiện tay: nó gợi rằng tám pháp nhân có chung một túi tiền.
    Ai cần con số hợp nhất thì đó là việc của báo cáo hợp nhất, nơi có bút toán loại trừ nội bộ.
    """
    return [tien_kha_dung(db, cid, den_ngay) for cid in company_ids]


# ============================================================================= DT-3 · bốn mốc lũy kế

# BỐN CỘT LŨY KẾ, CÙNG MỘT ĐIỂM BẮT ĐẦU.
#
# Cả bốn đều tính TỪ HÔM NAY, nên cột 14 ngày đã chứa trọn cột 7 ngày, cột 1 tháng chứa trọn cột 14
# ngày. Đó là lý do KHÔNG BAO GIỜ được cộng bốn cột lại: cộng ra một con số lớn gấp mấy lần thực tế
# và không có nghĩa gì cả. Hàm này cố ý không trả về ô tổng bốn cột.
#
# "Một tháng lịch" hiểu là MỘT THÁNG KỂ TỪ HÔM NAY (11/9 → hết 10/10), không phải "đến hết tháng 9".
# Hai cách hiểu cho hai con số khác nhau, nên mỗi cột trả kèm `tu_ngay` và `den_ngay` THẬT để người
# đọc thấy ngay mình đang nhìn khoảng nào – chứ không phải đoán từ cái tên cột.
# BỐN MỐC KHÔNG ĐỊNH NGHĨA Ở ĐÂY – xem `dong_tien_ky.MOC` và `dong_tien_ky.khoang`.
#
# Bản cũ của tệp này có bảng mốc riêng với mã `7_ngay / 14_ngay / 1_thang / 2_thang`. Bỏ ngày
# 11/9/2026 khi chia tầng. Hai chỗ cùng định nghĩa "một tháng lịch là gì" thì sớm muộn hai chỗ trả
# lời khác nhau – và hôm nay CHÚNG ĐÃ khác nhau thật: bản cũ ở đây cho 31/01 + 1 tháng = 27/02, còn
# v1.1 ghi 28/02. Lệch một ngày, đủ để một kỳ trả gốc rơi ra ngoài cột mà không ai thấy.
#
# Mã mốc từ nay là mã của `dong_tien_ky`: 7n · 14n · 1t · 2t. Màn hình đọc mã từ chính phản hồi API
# nên không cần sửa; phép thử thì có.
MOC = DTK.MOC
MA_MOC = DTK.MA_MOC


def khoang_cua_moc(hom_nay: date, ma: str) -> tuple[date, date]:
    """Ngày đầu và ngày cuối THẬT của một mốc – hỏi thẳng `dong_tien_ky`, không tự tính lại."""
    return DTK.khoang(hom_nay, ma)


# ----------------------------------------------------------------- sổ khai CÁC DÒNG của bảng

# MỖI DÒNG PHẢI KHAI NGUỒN CỦA MÌNH, HOẶC KHAI LÀ CHƯA CÓ NGUỒN KÈM BỘ PHẬN CHỊU TRÁCH NHIỆM.
#
# Đây là nguyên tắc B6 của lệnh giao việc dựng thành cấu trúc: "mỗi con số mới trên màn hình phải có
# một cửa nhập hoặc cửa tải. Chưa có cửa thì ghi 'Chưa có nguồn' kèm bộ phận chịu trách nhiệm –
# không hiện 0, không nhập hộ."
#
# Vì sao khai thành bảng chứ không viết thẳng vào hàm: một dòng thiếu nguồn mà cứ trả 0 thì nhìn y
# hệt một dòng thật sự bằng 0, và cả bảng sẽ trông đủ trong khi thiếu bốn khoản chi lớn nhất. Khai
# ra thì số dòng chưa có nguồn ĐẾM ĐƯỢC, và GD-2 (DT-7) là việc rút danh sách này về rỗng.
#
# `pham_vi_tgd` theo quyết định của Chủ tịch 11/9/2026 – xem `LOC_THEO_VAI_TRO` ở dưới.
DONG_BANG = (
    # (mã, tên hiển thị, chiều, nguồn, bộ phận chịu trách nhiệm nếu chưa có nguồn)
    ("thu_khach",      "Thu khách / booking / hợp đồng", "vao", "lich_thanh_toan_hd", ""),
    ("thu_cong_no",    "Thu công nợ khác",               "vao", None, "Kế toán"),
    ("giai_ngan_vay",  "Giải ngân vay đã ký khế ước",    "vao", "fin_schedule:giai_ngan,nhan_vay", ""),
    ("tra_ncc",        "Trả nhà cung cấp",               "ra",  "payment_request", ""),
    ("hoan_khach",     "Hoàn / trả khách hàng",          "ra",  None, "Kế toán"),
    ("hoa_hong",       "Hoa hồng đại lý và cộng tác viên", "ra", None, "Kinh doanh"),
    ("tra_goc_vay",    "Trả gốc vay ngân hàng",          "ra",  "fin_schedule:tra_goc", ""),
    ("lai_phi_vay",    "Lãi và phí ngân hàng",           "ra",  "fin_schedule:tra_lai", ""),
    ("luong_bhxh",     "Lương, bảo hiểm và liên quan",   "ra",  None, "Hành chính – Nhân sự"),
    ("thue",           "Thuế và nghĩa vụ khác",          "ra",  None, "Kế toán"),
    ("van_hanh",       "Vận hành và phải trả khác",      "ra",  "cash_plan_item", ""),
)

# Hai dòng GHI NHỚ. KHÔNG cộng vào dòng tiền thuần và không bù trừ với nghĩa vụ công ty (DT-8).
DONG_GHI_NHO = ("tien_thu_ho_khach", "ky_quy_giay_phep")


def _khoang(db: Session, company_id: int, ma: str, nguon: str | None,
            tu: date, den: date) -> float | None:
    """Số tiền của MỘT dòng trong MỘT khoảng, theo NGÀY CAM KẾT. RỖNG khi dòng chưa có nguồn."""
    if nguon is None:
        return None

    from sqlalchemy import func

    if nguon == "lich_thanh_toan_hd":
        from app.models.ban_hang import HopDongKhach, LichThanhToanHD
        return float(db.execute(
            select(func.coalesce(func.sum(LichThanhToanHD.so_tien), 0.0))
            .select_from(LichThanhToanHD)
            .join(HopDongKhach, HopDongKhach.id == LichThanhToanHD.hop_dong_id)
            .where(HopDongKhach.company_id == company_id,
                   HopDongKhach.trang_thai.notin_(["huy", "thanh_ly"]),
                   LichThanhToanHD.han != None,                       # noqa: E711
                   LichThanhToanHD.han >= tu, LichThanhToanHD.han <= den)).scalar() or 0)

    if nguon.startswith("fin_schedule:"):
        from app.models.finance import FinSchedule
        loai = nguon.split(":", 1)[1].split(",")
        return float(db.execute(
            select(func.coalesce(func.sum(FinSchedule.amount), 0.0))
            .select_from(FinSchedule)
            .join(FinContract, FinContract.id == FinSchedule.contract_id)
            .where(FinContract.company_id == company_id,
                   FinSchedule.kind.in_(loai),
                   FinSchedule.status != "da_thuc_hien",
                   FinSchedule.due_date >= tu, FinSchedule.due_date <= den)).scalar() or 0)

    if nguon == "payment_request":
        # Đề nghị chi đã duyệt chờ chuyển. KHÔNG có ngày đến hạn riêng, nên xếp vào khoảng đầu tiên:
        # tiền đã hứa thì phải chi ngay khi có tiền. Ngày cam kết thật là việc của DT-7.
        if tu > date.today():
            return 0.0
        return float(db.execute(
            select(func.coalesce(func.sum(PaymentRequest.amount), 0.0))
            .where(PaymentRequest.company_id == company_id,
                   PaymentRequest.status.in_(TRANG_THAI_DA_DUYET_CHUA_CHUYEN))).scalar() or 0)

    if nguon == "cash_plan_item":
        from app.models.finance import CashPlanItem
        return float(db.execute(
            select(func.coalesce(func.sum(CashPlanItem.amount), 0.0))
            .where(CashPlanItem.direction == "out",
                   CashPlanItem.due_date >= tu, CashPlanItem.due_date <= den)).scalar() or 0)

    raise ValueError(f"Dòng {ma} khai nguồn '{nguon}' mà không ai đọc được nguồn ấy")


def bang_bon_moc(db: Session, company_id: int, hom_nay: date | None = None) -> dict:
    """DT-3. Bảng dòng tiền bốn mốc lũy kế của MỘT pháp nhân.

    BỐN CỘT LŨY KẾ TỪ CÙNG MỘT ĐIỂM, nên chúng CHỒNG LÊN NHAU: cột 14 ngày đã chứa trọn cột 7 ngày.
    Vì thế bảng này KHÔNG có ô tổng bốn cột, và `cong_bon_cot_la_sai` nói thẳng điều đó ra cho bất kỳ
    ai định cộng.

    Tiền đầu kỳ là CÙNG MỘT MỐC cho cả bốn cột: đó là tiền khả dụng hôm nay (DT-1). Lấy bốn mốc khác
    nhau thì bốn cột không so được với nhau nữa.
    """
    hn = hom_nay or date.today()
    ct = db.get(Company, company_id)
    if ct is None:
        raise LoiChot("Không có pháp nhân này")

    kd = tien_kha_dung(db, company_id, hn)
    dau_ky = kd["tien_kha_dung"]

    # Bốn cột lấy thẳng từ `dong_tien_ky.cac_khoang` – kèm sẵn chuỗi ngày DD-MM-YYYY để màn hình
    # không phải tự định dạng. Mỗi nơi tự định dạng là một nơi có thể quên.
    cot = [{"ma": k["ma"], "ten": k["nhan"], "tu_ngay": k["tu"], "den_ngay": k["den"],
            "tu_hien": k["tu_hien"], "den_hien": k["den_hien"], "so_ngay": k["so_ngay"]}
           for k in DTK.cac_khoang(hn)]

    dong = []
    thieu_nguon = []
    for ma, ten, chieu, nguon, bo_phan in DONG_BANG:
        o = {}
        for c in cot:
            o[c["ma"]] = _khoang(db, company_id, ma, nguon, c["tu_ngay"], c["den_ngay"])
        d = {"ma": ma, "ten": ten, "chieu": chieu, "so": o}
        if nguon is None:
            d["chua_co_nguon"] = True
            d["bo_phan_chiu_trach_nhiem"] = bo_phan
            thieu_nguon.append(f"{ten} – {bo_phan}")
        dong.append(d)

    # Dòng tiền thuần và số dư cuối: CHỈ tính được khi KHÔNG dòng nào thiếu nguồn. Cộng mười dòng có
    # số rồi bỏ qua bốn dòng rỗng là ra một con số đẹp hơn thực tế – đúng kiểu sai mà Chủ tịch đã
    # chỉ đích danh: người đọc thấy "còn 5 tỷ" trong lúc công ty còn 400 triệu sau khi trả nợ.
    du_nguon = not thieu_nguon
    thuan, cuoi_ky = {}, {}
    for c in cot:
        if not du_nguon or dau_ky is None:
            thuan[c["ma"]] = None
            cuoi_ky[c["ma"]] = None
            continue
        # DÒNG TỔNG = TỔNG CÁC DÒNG ĐÃ LÀM TRÒN (chỉ đạo Chủ tịch 11/9/2026), không phải phần làm
        # tròn của một tổng chưa tròn. Hai cách lệch nhau vài đồng, và vài đồng trên bảng dòng tiền
        # là chỗ kế toán dò cả buổi chiều mà không tìm ra, vì không dòng nào sai cả.
        t = sum(lam_tron(d["so"][c["ma"]] or 0) * (1 if d["chieu"] == "vao" else -1) for d in dong)
        thuan[c["ma"]] = t
        cuoi_ky[c["ma"]] = lam_tron(dau_ky) + t

    return {
        "phap_nhan": kd["phap_nhan"],
        "hom_nay": hn,
        "cot": cot,
        "tien_kha_dung_dau_ky": dau_ky,
        "doi_soat_den_ngay": kd["doi_soat_den_ngay"],
        "dong": dong,
        "dong_tien_thuan": thuan,
        "so_du_du_kien_cuoi_khoang": cuoi_ky,
        "ghi_nho": kd["ghi_nho"],
        "chua_co_nguon": thieu_nguon,
        "vi_sao_khong_co_so_cuoi": "" if (du_nguon and dau_ky is not None) else (
            "Chưa đủ nguồn nên KHÔNG có dòng tiền thuần và số dư cuối – ô để trống chứ không phải "
            "bằng 0. " + ("Chưa có tiền khả dụng đầu kỳ. " if dau_ky is None else "")
            + ("Các dòng chưa có nguồn: " + "; ".join(thieu_nguon) if thieu_nguon else "")),
        "cong_bon_cot_la_sai": (
            "Bốn cột LŨY KẾ từ cùng một ngày nên chồng lên nhau – cột 14 ngày đã chứa trọn cột 7 "
            "ngày. Cộng bốn cột ra một con số lớn gấp mấy lần thực tế và không có nghĩa gì cả."),
    }


# ===================================================== DT-4 · số dư từng ngày và mức dự phòng

def khoa_muc_du_phong(company_id: int) -> str:
    """Khoá tham số mức dự phòng của MỘT pháp nhân – MỘT khoá duy nhất cho cả hệ thống.

    Chủ tịch chốt 11/9/2026: dùng khoá của làn Phân quyền, `muc_du_phong_toi_thieu:<id pháp nhân>`.
    Bản cũ ở đây dùng `muc_du_phong_<mã pháp nhân>`. Để cả hai thì Chủ tịch và Tổng giám đốc ký vào
    một khoá, còn màn hình đọc khoá kia rồi vẫn ghi "Chưa có ngưỡng" – hai chữ ký thật nằm đó mà hệ
    thống báo chưa ai ký. Hàm này chỉ còn là lối gọi cũ, trỏ về đúng một nơi.
    """
    return DTK._khoa_theo_phap_nhan(company_id)


def muc_du_phong(db: Session, company_id: int, on: date | None = None) -> tuple[float | None, str]:
    """Mức dự phòng tối thiểu đang CÓ HIỆU LỰC của một pháp nhân, và lý do nếu chưa có.

    PHÉP ĐỌC NẰM Ở `dong_tien_ky.muc_du_phong` – đây chỉ là lối gọi cũ giữ nguyên kiểu trả về
    `(số | None, lý do)` cho những chỗ đã viết theo nó. Hai nơi cùng quyết định "ngưỡng này đã có
    hiệu lực chưa" là hai câu trả lời cho cùng một câu hỏi tiền bạc.

    Luật vẫn thế và do hàm kia giữ: đủ HAI CHỮ KÝ Tổng giám đốc + Chủ tịch (Chủ tịch quyết 11/9/2026,
    không phải Kế toán trưởng), có ngày hiệu lực không vượt quá hôm nay, giá trị không rỗng. Chưa đủ
    thì RỖNG kèm câu "Chưa có ngưỡng" – không có con số mặc định nào, vì một ngưỡng ai đó đoán hộ sẽ
    kêu sai ở cả hai chiều.

    CÒN MỘT CÂU HỎI ĐÃ BÀN GIAO SANG LÀN PHÂN QUYỀN: bản cũ ở đây còn đòi `Param.status == "active"`,
    bản đang dùng thì không. Một ngưỡng đã bị rút mà vẫn còn đủ hai chữ ký sẽ được coi là còn hiệu
    lực. Chưa sửa ở đây vì sửa tệp của làn khác là đúng thứ đã gây ra hai lần đụng độ hôm nay.
    """
    ct = db.get(Company, company_id)
    if ct is None:
        raise LoiChot("Không có pháp nhân này")
    r = DTK.muc_du_phong(db, company_id, on or date.today())
    if not r.get("co_nguong"):
        return None, f"{DTK.CHUA_CO_NGUONG} – {r.get('cau', '')} (khoá {r.get('khoa', '')})"
    return float(r["so"]), ""


def so_du_tung_ngay(db: Session, company_id: int, hom_nay: date | None = None,
                    so_ngay: int | None = None) -> dict:
    """DT-4. Số dư dự kiến THEO TỪNG NGÀY, để bắt thiếu tiền GIỮA KỲ.

    Vì sao không đủ khi chỉ có bốn cột lũy kế: một kỳ hai tháng có thể kết thúc dương mà vẫn có ba
    ngày âm ở giữa – ngày trả gốc vay rơi trước ngày khách thanh toán đợt hai. Bảng bốn mốc nói "cuối
    kỳ còn tiền" và đúng; nhưng công ty vẫn mất khả năng chi trả trong ba ngày ấy.

    Thiếu tiền đầu kỳ hoặc thiếu nguồn của bất kỳ dòng nào thì KHÔNG dựng đường số dư: một đường vẽ
    từ sáu trong mười một dòng luôn nằm CAO HƠN thực tế, và nó nằm cao đúng ở chỗ người đọc cần nó
    chính xác nhất.
    """
    hn = hom_nay or date.today()
    b = bang_bon_moc(db, company_id, hn)
    den = DTK.khoang(hn, "2t")[1] if so_ngay is None else hn + timedelta(days=so_ngay - 1)

    nguong, vi_sao_nguong = muc_du_phong(db, company_id, hn)

    chung = {
        "phap_nhan": b["phap_nhan"], "tu_ngay": hn, "den_ngay": den,
        "muc_du_phong": nguong, "vi_sao_chua_co_nguong": vi_sao_nguong,
        "chua_co_nguon": b["chua_co_nguon"],
    }
    if b["tien_kha_dung_dau_ky"] is None or b["chua_co_nguon"]:
        return {**chung, "ngay": [], "ngay_dau_thieu_tien": None,
                "muc_thieu_lon_nhat": None,
                "vi_sao_khong_ve_duoc": b["vi_sao_khong_co_so_cuoi"] or
                "Chưa đủ đầu vào để dựng đường số dư từng ngày."}

    # Gom biến động theo NGÀY trong một lượt cho mỗi nguồn, không hỏi lại theo từng ngày: hỏi theo
    # từng ngày là 61 lượt truy vấn cho mỗi dòng, đúng kiểu N+1 mà bộ kiểm KS-5 canh.
    bien_dong: dict[date, float] = {}
    for ma, ten, chieu, nguon, _bp in DONG_BANG:
        for ngay, tien in _theo_ngay(db, company_id, nguon, hn, den):
            bien_dong[ngay] = bien_dong.get(ngay, 0.0) + tien * (1 if chieu == "vao" else -1)

    so_du = float(b["tien_kha_dung_dau_ky"])
    ngay_list, ngay_thieu, thieu_lon_nhat = [], None, None
    d = hn
    while d <= den:
        so_du = round(so_du + bien_dong.get(d, 0.0), 2)
        thieu = None if nguong is None else round(nguong - so_du, 2)
        if thieu is not None and thieu > 0:
            if ngay_thieu is None:
                ngay_thieu = d
            if thieu_lon_nhat is None or thieu > thieu_lon_nhat:
                thieu_lon_nhat = thieu
        ngay_list.append({"ngay": d, "bien_dong": round(bien_dong.get(d, 0.0), 2),
                          "so_du": so_du, "thieu_so_voi_du_phong": thieu})
        d += timedelta(days=1)

    return {**chung, "ngay": ngay_list, "ngay_dau_thieu_tien": ngay_thieu,
            "muc_thieu_lon_nhat": thieu_lon_nhat, "vi_sao_khong_ve_duoc": ""}


def _theo_ngay(db: Session, company_id: int, nguon: str | None,
               tu: date, den: date) -> list[tuple[date, float]]:
    """Biến động của MỘT dòng, gom theo ngày, MỘT lượt truy vấn cho cả khoảng."""
    if nguon is None:
        return []
    from sqlalchemy import func

    if nguon == "lich_thanh_toan_hd":
        from app.models.ban_hang import HopDongKhach, LichThanhToanHD
        r = db.execute(
            select(LichThanhToanHD.han, func.coalesce(func.sum(LichThanhToanHD.so_tien), 0.0))
            .select_from(LichThanhToanHD)
            .join(HopDongKhach, HopDongKhach.id == LichThanhToanHD.hop_dong_id)
            .where(HopDongKhach.company_id == company_id,
                   HopDongKhach.trang_thai.notin_(["huy", "thanh_ly"]),
                   LichThanhToanHD.han != None,                       # noqa: E711
                   LichThanhToanHD.han >= tu, LichThanhToanHD.han <= den)
            .group_by(LichThanhToanHD.han)).all()
        return [(x[0], float(x[1] or 0)) for x in r]

    if nguon.startswith("fin_schedule:"):
        from app.models.finance import FinSchedule
        loai = nguon.split(":", 1)[1].split(",")
        r = db.execute(
            select(FinSchedule.due_date, func.coalesce(func.sum(FinSchedule.amount), 0.0))
            .select_from(FinSchedule)
            .join(FinContract, FinContract.id == FinSchedule.contract_id)
            .where(FinContract.company_id == company_id, FinSchedule.kind.in_(loai),
                   FinSchedule.status != "da_thuc_hien",
                   FinSchedule.due_date >= tu, FinSchedule.due_date <= den)
            .group_by(FinSchedule.due_date)).all()
        return [(x[0], float(x[1] or 0)) for x in r]

    if nguon == "payment_request":
        t = _khoang(db, company_id, "tra_ncc", nguon, tu, den)
        return [(tu, float(t or 0))] if t else []

    if nguon == "cash_plan_item":
        from app.models.finance import CashPlanItem
        r = db.execute(
            select(CashPlanItem.due_date, func.coalesce(func.sum(CashPlanItem.amount), 0.0))
            .where(CashPlanItem.direction == "out",
                   CashPlanItem.due_date >= tu, CashPlanItem.due_date <= den)
            .group_by(CashPlanItem.due_date)).all()
        return [(x[0], float(x[1] or 0)) for x in r]

    raise ValueError(f"Nguồn '{nguon}' chưa có cách gom theo ngày")



# ============================================ DT-5 · hai cơ sở ngày · DT-6 · chống tính trùng
#
# KHÔNG CÓ MÃ Ở ĐÂY, VÀ ĐÓ LÀ CÓ Ý.
#
# Bản đầu của tệp này có một bảng `nghia_vu_tien` riêng cùng ba hàm phủ dòng nguồn thành nghĩa vụ.
# Ngày 11/9/2026, khi gộp, phát hiện lằn VPM-11 đã dựng đúng khái niệm ấy ở
# `app/models/nghia_vu.py` + `app/services/nghia_vu.py`, hoàn chỉnh hơn: mười ba nhóm khớp đúng
# mười ba dòng của bảng dòng tiền, có ngoại tệ và tỷ giá, có phép đồng bộ dựng lại từ sáu bảng
# chứng từ gốc, và – điểm quyết định – khi ngờ hai dòng là một thì nó ĐÁNH DẤU `nghi_trung_voi`
# cho người quyết, chứ KHÔNG tự gộp. Tự gộp là tự đặt ra một quy tắc kế toán chưa ai ký.
#
# Chủ tịch chốt bỏ bản của Robot A, giữ bản VPM-11. Hai sổ nghĩa vụ song song là hai con số nợ
# phải trả cho cùng một công ty, và không ai biết phải tin cái nào.
#
# Cần hai cơ sở ngày và số đã gỡ trùng thì gọi:
#     from app.services import nghia_vu as NV
#     NV.cong(db, tu, den, co_so_ngay="cam_ket" | "du_kien", company_id=...)   # cộng theo nhóm
#     NV.ba_ro(db, den, ...)          # quá hạn · thiếu ngày · nghi trùng – ba rổ không được bỏ im
#
# HAI VIỆC CÒN NỢ, đã bàn giao sang lằn VPM (chưa có trong bản VPM-11):
#   1. Dời `ngay_du_kien_tra` phải BẮT BUỘC ghi lý do. Một khoản lùi ngày mà không ai giải thích
#      thì sang tháng không ai biết nó đã được xem chưa. `ngay_cam_ket` thì không được dời ở màn
#      hình dòng tiền – dời cam kết là sửa hợp đồng, và sửa hợp đồng có cửa riêng với chữ ký riêng.
#   2. Khi cơ sở `du_kien` phải mượn `ngay_cam_ket` vì chưa ai đặt ngày dự kiến, nói điều đó ra
#      trên từng dòng. Im lặng thay thế là trộn hai cơ sở ngày mà người đọc không biết.
