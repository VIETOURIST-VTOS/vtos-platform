# -*- coding: utf-8 -*-
"""ĐỐI CHIẾU TIỀN — Đợt E15, 14/10/2026.

BA CON SỐ, VÀ MỖI CON SỐ LÀ MỘT NGƯỜI KHÁC NÓI

  · SỐ SỔ      — dư Nợ 112x (hoặc 111) trên sổ cái, chỉ tính bút toán ĐÃ GHI SỔ. Đây là con số đi
                 vào Bảng cân đối kế toán.
  · SỐ ĐÃ CHỐT — Kế toán ký "đến hết ngày này còn ngần này", sau khi soát với sao kê / sổ quỹ.
  · SỐ MÁY CỘNG — máy cộng từ giao dịch ngân hàng đẩy về, đã lưu sẵn ở `chot_so_du.so_may_cong`.

Ba con số ấy LẼ RA bằng nhau. Khi không bằng nhau thì mỗi cặp lệch kể một câu chuyện khác:

  sổ ≠ đã chốt    → hạch toán thiếu hoặc thừa. Đi thẳng vào báo cáo tài chính. ĐỢT NÀY ĐO CÁI NÀY.
  đã chốt ≠ máy   → sao kê về chậm, hoặc tài khoản chưa nối SePay. Đã có ô `ly_do_lech` riêng từ DT-2.

Gộp hai thứ ấy thành một con số thì lệch ở đâu cũng không biết đường nào mà tìm, nên màn hình bày
cả ba và nói rõ cột nào trừ cột nào.

RỖNG KHÁC KHÔNG, Ở ĐÂY QUAN TRỌNG HƠN MỌI CHỖ KHÁC

Chưa ai chốt ngày ấy thì `so_da_chot` là RỖNG, và chênh lệch cũng RỖNG — KHÔNG phải 0. Lấy 0 thay
cho "chưa ai chốt" là biến một việc chưa làm thành một việc đã làm và khớp. Màn hình hiện "—", và
một dòng "—" KHÔNG được tính là đã đối chiếu.

Cùng lẽ ấy: sổ chưa có bút toán nào chạm tài khoản ấy thì `so_so` RỖNG, không phải 0.

"CHƯA GIẢI THÍCH HẾT THÌ CHƯA PHẢI ĐÃ ĐỐI CHIẾU"

Đối chiếu không phải là NHÌN THẤY chênh lệch, mà là NÓI ĐƯỢC chênh lệch gồm những khoản nào. Nên
phép đo ở đây không hỏi "lệch có nhỏ không" mà hỏi "phần chưa giải thích có bằng không chưa".
Tổng các lời giải thích còn hiệu lực phải bằng đúng chênh lệch; còn một đồng chưa ai nói là chưa xong.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.banks import BankAccount
from app.models.doi_chieu_tien import GiaiThichLech
from app.models.dong_tien import ChotSoDu
from app.services import dong_tien as DT

# Tài khoản sổ cái của quỹ tiền mặt. Khai ra một chỗ, không rải chuỗi "111" khắp tệp.
TK_TIEN_MAT = "111"

# Ngưỡng coi là bằng nhau. MỘT ĐỒNG, không phải một phần trăm: sổ kế toán Việt Nam ghi tới đồng, và
# một ngưỡng phần trăm nghĩa là tài khoản càng to thì càng được phép lệch nhiều — đúng chiều ngược
# với cái người ta cần.
NGUONG = 1.0


class LoiDoiChieu(ValueError):
    """Lời giải thích khai sai, kèm câu nói ra vì sao."""


def _du_no(db: Session, company_id: int, ma_tk: str, den_ngay: date) -> float | None:
    """Dư NỢ của một tài khoản tới hết ngày. RỖNG khi sổ chưa có bút toán nào chạm tài khoản ấy.

    Dùng lại đúng truy vấn của `dong_tien._du_co` rồi đổi dấu, chứ không viết một truy vấn thứ hai:
    111 và 112 là tài khoản TÀI SẢN nên số đọc được là dư Nợ, còn phép đếm "có bút toán nào chưa"
    thì hai bên giống hệt. Hai truy vấn gần giống nhau là hai chỗ để lệch nhau về sau.
    """
    co = DT._du_co(db, company_id, ma_tk, den_ngay)
    return None if co is None else round(-co, 2)


def _tong_da_giai_thich(db: Session, company_id: int, nguon: str,
                        tai_khoan_id: int | None, den_ngay: date) -> float:
    """Tổng các lời giải thích CÒN HIỆU LỰC cho đúng một (pháp nhân, nguồn, tài khoản, ngày).

    Trả 0.0 khi chưa ai giải thích gì — và ở ĐÂY 0 là đúng nghĩa: "đã giải thích được không đồng
    nào". Khác hẳn `so_da_chot` rỗng, vốn nghĩa là "chưa ai chốt".
    """
    dong = db.execute(select(GiaiThichLech).where(
        GiaiThichLech.company_id == company_id,
        GiaiThichLech.nguon == nguon,
        GiaiThichLech.tai_khoan_id == tai_khoan_id,
        GiaiThichLech.den_ngay == den_ngay,
        GiaiThichLech.trang_thai == "hieu_luc")).scalars().all()
    # `so_tien` là cột NOT NULL — xem `models/doi_chieu_tien.py`: một lời giải thích không có số thì
    # không cộng được, mà cộng được chính là lý do bảng ấy tồn tại. Cửa ghi còn chặn thêm số tiền
    # dưới ngưỡng. Nên ở đây KHÔNG bọc `or 0`: bọc vào là nói rằng rỗng có thể xảy ra và khi xảy
    # ra thì coi như 0 — tức là một dòng hỏng sẽ lặng lẽ biến mất khỏi tổng, đúng kiểu sai mà cả đợt
    # này dựng ra để chặn.
    return round(sum(float(d.so_tien) for d in dong), 2)  # k2-doc-an-toan: so_tien la cot NOT NULL, rong khong xay ra duoc


def _mot_dong(db: Session, company_id: int, nguon: str, tai_khoan_id: int | None,
              ma_tk_so: str | None, ten: str, den_ngay: date) -> dict:
    """Một dòng của bảng đối chiếu. Mọi RỖNG ở đây đều mang một `vi_sao` đọc được."""
    b = DT.ban_chot_moi_nhat(db, company_id, nguon, tai_khoan_id, den_ngay)
    so_so = None if ma_tk_so is None else _du_no(db, company_id, ma_tk_so, den_ngay)

    vi_sao: list[str] = []
    if ma_tk_so is None:
        vi_sao.append("tài khoản ngân hàng này chưa khai tiểu khoản 112 nên không đọc được số sổ")
    elif so_so is None:
        vi_sao.append(f"sổ chưa có bút toán nào đã ghi sổ chạm TK {ma_tk_so} tính đến "
                      f"{den_ngay:%d/%m/%Y}")
    if b is None:
        vi_sao.append(f"chưa ai chốt số dư tính đến {den_ngay:%d/%m/%Y}")

    so_da_chot = None if b is None else float(b.so_du)
    lech = None if (so_so is None or so_da_chot is None) else round(so_so - so_da_chot, 2)
    # Ngày của BẢN CHỐT, không phải ngày người dùng hỏi. Lời giải thích gắn vào ngày này, vì chênh
    # lệch là chênh lệch CỦA bản chốt ấy.
    ngay_chot = None if b is None else b.den_ngay
    da_giai_thich = (0.0 if ngay_chot is None
                     else _tong_da_giai_thich(db, company_id, nguon, tai_khoan_id, ngay_chot))
    con_lai = None if lech is None else round(lech - da_giai_thich, 2)

    return {
        "nguon": nguon,
        "tai_khoan_id": tai_khoan_id,
        "ten": ten,
        "ma_tk_so": ma_tk_so,
        "so_so": so_so,
        "so_da_chot": so_da_chot,
        # Số máy cộng lấy THẲNG từ bản chốt — không cộng lại ở đây. Cộng lại là có hai con số cùng
        # tên mà khác giá trị, và không ai biết màn hình đang bày cái nào.
        "so_may_cong": None if (b is None or b.so_may_cong is None) else float(b.so_may_cong),
        "ngay_chot": ngay_chot,
        "chot_boi": None if b is None else b.boi,
        "lech": lech,
        "da_giai_thich": da_giai_thich,
        "con_lai_chua_giai_thich": con_lai,
        "xong": con_lai is not None and abs(con_lai) < NGUONG,
        "vi_sao": " · ".join(vi_sao),
    }


def bang(db: Session, company_id: int, den_ngay: date) -> dict:
    """Bảng đối chiếu tiền của MỘT pháp nhân tính đến hết một ngày.

    TẬP TÀI KHOẢN SUY TỪ SỔ CHỐT, không duyệt cả danh mục. `bank_accounts_cat` không có cột
    `company_id` (đo 11/9/2026, ghi trong `dong_tien.tien_kha_dung`), nên duyệt cả danh mục thì
    pháp nhân A hiện đầy tài khoản của pháp nhân B và bảng nào cũng đỏ. Dùng ĐÚNG quy tắc mà
    `tien_kha_dung` đang dùng — hai màn hình phải đồng ý với nhau về việc tài khoản nào của ai, và
    cách duy nhất chắc chắn là chúng đọc cùng một quy tắc.
    """
    rows = []
    tk_da_tung_chot = list(db.execute(
        select(ChotSoDu.tai_khoan_id).where(
            ChotSoDu.company_id == company_id, ChotSoDu.nguon == "ngan_hang",
            ChotSoDu.tai_khoan_id != None).distinct()).scalars())      # noqa: E711
    for tid in sorted(tk_da_tung_chot):
        t = db.get(BankAccount, tid)
        ten = f"{t.code} ({t.bank_name})" if t else f"tài khoản #{tid}"
        ma = (t.account_code or None) if t else None
        rows.append(_mot_dong(db, company_id, "ngan_hang", tid, ma, ten, den_ngay))

    # Quỹ tiền mặt luôn có một dòng, kể cả khi chưa ai chốt — thiếu dòng và dòng rỗng là hai nghĩa
    # khác nhau, và "quên mất quỹ tiền mặt" là cái thứ hai cần nhìn thấy.
    rows.append(_mot_dong(db, company_id, "tien_mat", None, TK_TIEN_MAT, "Quỹ tiền mặt", den_ngay))

    chua_xong = [r for r in rows if not r["xong"]]
    return {
        "company_id": company_id,
        "den_ngay": den_ngay,
        "rows": rows,
        "so_dong": len(rows),
        "so_dong_xong": len(rows) - len(chua_xong),
        # CỐ Ý KHÔNG có dòng tổng cộng các chênh lệch. Một tài khoản lệch +100 và một tài khoản lệch
        # −100 cộng lại bằng 0, và con số 0 ấy nói dối to hơn cả hai con số nó che đi.
        "xong": not chua_xong,
        "vi_sao_chua_xong": [
            (f"{r['ten']}: " + (r["vi_sao"] if r["vi_sao"]
                                else f"còn {r['con_lai_chua_giai_thich']:,.0f} đ chưa giải thích"))
            for r in chua_xong],
    }


def them_giai_thich(db: Session, boi: str, company_id: int, nguon: str,
                    tai_khoan_id: int | None, den_ngay: date, so_tien: float,
                    ly_do: str, ghi_chu: str = "") -> GiaiThichLech:
    """Ghi một khoản giải thích. KHÔNG tự chốt sổ, KHÔNG sinh bút toán nào.

    Giải thích chênh lệch và SỬA chênh lệch là hai việc khác nhau: cái sau là một bút toán điều
    chỉnh, đi cửa riêng của nó (Đợt E14), và có hai mốc thời gian của nó.
    """
    if not (ly_do or "").strip():
        raise LoiDoiChieu("Phải nói khoản này là khoản gì. Một con số không có lý do thì nó không "
                          "giải thích được gì cả.")
    if abs(float(so_tien)) < NGUONG:
        raise LoiDoiChieu("Khoản giải thích phải có số tiền khác 0. Muốn ghi một nhận xét không "
                          "kèm số thì ghi vào ô ghi chú của bản chốt.")
    if nguon not in ("ngan_hang", "tien_mat"):
        raise LoiDoiChieu(f"Nguồn tiền `{nguon}` không có thật.")
    if nguon == "tien_mat" and tai_khoan_id is not None:
        raise LoiDoiChieu("Quỹ tiền mặt không có số tài khoản ngân hàng.")
    if nguon == "ngan_hang" and tai_khoan_id is None:
        raise LoiDoiChieu("Phải nói khoản này thuộc tài khoản ngân hàng nào.")
    if DT.ban_chot_moi_nhat(db, company_id, nguon, tai_khoan_id, den_ngay) is None:
        raise LoiDoiChieu(f"Chưa ai chốt số dư tính đến {den_ngay:%d/%m/%Y} cho nguồn tiền này. "
                          "Giải thích một chênh lệch trước khi có chênh lệch là giải thích một "
                          "con số chưa tồn tại.")
    g = GiaiThichLech(company_id=company_id, nguon=nguon, tai_khoan_id=tai_khoan_id,
                      den_ngay=den_ngay, so_tien=round(float(so_tien), 2),
                      ly_do=ly_do.strip()[:300], boi=boi, ghi_chu=ghi_chu)
    db.add(g)
    db.flush()
    return g


def huy_giai_thich(db: Session, boi: str, gid: int, ly_do: str) -> GiaiThichLech:
    """Gỡ một lời giải thích. KHÔNG xoá dòng — ai giải thích sai và ai gỡ là câu kiểm toán sẽ hỏi."""
    from datetime import datetime
    g = db.get(GiaiThichLech, gid)
    if g is None:
        raise LoiDoiChieu("Không có lời giải thích này.")
    if g.trang_thai != "hieu_luc":
        raise LoiDoiChieu("Lời giải thích này đã được gỡ rồi.")
    if not (ly_do or "").strip():
        raise LoiDoiChieu("Phải nói vì sao gỡ. Gỡ không lý do thì lần sau không ai biết nó sai ở đâu.")
    g.trang_thai = "da_huy"
    g.huy_boi = boi
    g.huy_luc = datetime.now()
    g.huy_ly_do = ly_do.strip()[:300]
    db.flush()
    return g


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHÉP CHẶN KHÓA KỲ
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _cuoi_ky(period: str) -> date:
    """Ngày cuối cùng của kỳ 'YYYY-MM'."""
    import calendar
    nam, thang = int(period[:4]), int(period[5:7])
    return date(nam, thang, calendar.monthrange(nam, thang)[1])


def ly_do_chua_khoa_duoc(db: Session, period: str) -> list[str]:
    """Những chỗ chênh lệch tiền chưa giải thích hết trong kỳ — rỗng nghĩa là khóa được.

    CHỈ XÉT PHÁP NHÂN ĐÃ CHỐT TRONG CHÍNH KỲ ẤY, và đó là một GIỚI HẠN CÓ CHỦ Ý, nói ra ở đây chứ
    không giấu: pháp nhân nào cả tháng không chốt số dư lần nào thì phép chặn này KHÔNG kêu, vì
    chẳng có bản chốt nào để so. Lấy bản chốt của tháng trước ra so với sổ tháng này là dựng một
    chênh lệch không ai từng đo.

    Nghĩa là còn một lỗ: bỏ hẳn việc chốt thì khóa kỳ vẫn trôi. Bịt lỗ ấy là ĐÒI mỗi kỳ phải có
    chốt số dư — một quy định mới về nghĩa vụ hàng tháng, phải có người ký, nên không nằm trong đợt
    này. Ghi vào đây để lần sau ai đọc cũng thấy nó còn hở ở đâu.
    """
    cuoi = _cuoi_ky(period)
    dau = date(cuoi.year, cuoi.month, 1)
    cac_ct = list(db.execute(
        select(ChotSoDu.company_id).where(
            ChotSoDu.company_id != None,                               # noqa: E711
            ChotSoDu.trang_thai == "hieu_luc",
            ChotSoDu.den_ngay >= dau, ChotSoDu.den_ngay <= cuoi).distinct()).scalars())
    xau: list[str] = []
    for cid in sorted(cac_ct):
        b = bang(db, cid, cuoi)
        for r in b["rows"]:
            if r["ngay_chot"] is None or r["ngay_chot"] < dau:
                continue        # pháp nhân này không chốt nguồn tiền ấy trong kỳ — xem docstring
            if not r["xong"]:
                con = r["con_lai_chua_giai_thich"]
                xau.append(
                    f"pháp nhân #{cid} · {r['ten']}: "
                    + (r["vi_sao"] if con is None
                       else f"còn {con:,.0f} đ chênh lệch giữa sổ và số đã chốt chưa giải thích"))
    return xau
