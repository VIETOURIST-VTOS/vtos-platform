"""Đợt E1 – kiểm dòng bút toán theo CHIỀU PHÂN TÍCH mà chính tài khoản của nó khai.

VẤN ĐỀ CŨ. `journal_lines` có sẵn ba cột chiều – `partner_code`, `project_code`, `item_code` –
nhưng không chỗ nào nói tài khoản NÀO bắt buộc chiều nào. Hệ quả đã thấy: bản rà soát giao diện
ngày 09/10 báo một xung đột ở P1·07 – quy ước THU_CHUA_RO cho phép để trống đối tượng, trong khi
bộ kiểm kết sổ lại đòi TK3388 phải có đối tượng. Hai chỗ nói hai điều về cùng một tài khoản, và
không chỗ nào sai hơn chỗ nào vì không có nơi nào là NGUỒN.

CÁCH MISA GIẢI, VÀ TA CHÉP. Trên form tài khoản của MISA có một khối "Theo dõi chi tiết theo" gồm
các ô tích; TK 131 bật "Đối tượng = Khách hàng". Bộ ghi sổ đọc chính khai báo ấy. Một nơi khai,
mọi nơi đọc – nên không còn hai chỗ để lệch nhau.

CHỈ BA CHIỀU, VÀ ĐÓ LÀ CHỦ Ý. MISA có mười một chiều. Ở đây khai ĐÚNG BA, vì `journal_lines` hiện
chỉ có ba cột để mà kiểm. Khai một cờ không có cột tương ứng thì cờ ấy bật được mà không kiểm
được gì – đúng cái bẫy "có màn hình không có nghĩa là đã vận hành". Bốn chiều còn lại (tài khoản
ngân hàng, mục thu/chi, mã thống kê, đơn vị) chờ Đợt E3 mở cột rồi mới khai cờ.

MỨC CHẶN KHÔNG NẰM Ở ĐÂY. Thiếu chiều thì chặn hay cho qua là việc của bảng `muc_do_chan`, do
Kế toán đặt. Tệp này chỉ trả lời "dòng này thiếu chiều nào".
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.accounting import Account
from app.models.muc_do_chan import MUC_DO_KHI_CHUA_KHAI, MucDoChan

# Mã phép kiểm của đợt này. Mỗi mã là một dòng người ta đặt mức được.
PK_THIEU_CHIEU = "thieu_chieu_phan_tich"
PK_SO_DU_BAT_THUONG = "so_du_bat_thuong"
PK_TK_NGUNG_SU_DUNG = "ghi_vao_tk_ngung_su_dung"

PHEP_KIEM_DOT_NAY = (PK_THIEU_CHIEU, PK_SO_DU_BAT_THUONG, PK_TK_NGUNG_SU_DUNG)

# cờ trên Account  →  (cột trên JournalLine, tên đọc được)
CHIEU = {
    "td_doi_tuong": ("partner_code", "đối tượng"),
    "td_cong_trinh": ("project_code", "công trình (mã tour)"),
    "td_khoan_muc": ("item_code", "khoản mục chi phí"),
}

# td_doi_tuong_loai → cờ phải bật trên Partner. "tat_ca" và rỗng thì không soi loại.
LOAI_DOI_TUONG = {"kh": "is_customer", "ncc": "is_supplier"}


def muc_do(db: Session, ma_phep_kiem: str) -> str:
    """Mức đang áp dụng cho một phép kiểm. Chưa ai đặt thì trả mức nhẹ nhất – và bị đếm."""
    d = (db.query(MucDoChan)
           .filter(MucDoChan.ma_phep_kiem == ma_phep_kiem, MucDoChan.dang_ap_dung.is_(True))
           .first())
    if d is None or not d.muc_do:
        return MUC_DO_KHI_CHUA_KHAI
    if d.ngay_hieu_luc and d.ngay_hieu_luc > date.today():
        return MUC_DO_KHI_CHUA_KHAI      # đã khai nhưng chưa tới ngày
    return d.muc_do


def chan(db: Session, ma_phep_kiem: str) -> bool:
    return muc_do(db, ma_phep_kiem) == "canh_bao_va_chan"


def phep_kiem_chua_dat_muc(db: Session, ma: Iterable[str] = PHEP_KIEM_DOT_NAY) -> list[str]:
    """Phép kiểm đang chạy ở mức mặc định vì chưa ai ký. Đếm lên để không im lặng."""
    chua = []
    for m in ma:
        d = (db.query(MucDoChan)
               .filter(MucDoChan.ma_phep_kiem == m, MucDoChan.dang_ap_dung.is_(True))
               .first())
        if d is None or not d.muc_do:
            chua.append(m)
    return chua


def chieu_bat_buoc(tk: Account) -> list[tuple[str, str]]:
    """Các chiều tài khoản này khai là bắt buộc: [(ten_cot, ten_doc_duoc), ...]."""
    return [CHIEU[co] for co in CHIEU if getattr(tk, co, False)]


def thieu_chieu(db: Session, dong: Any, tk: Account | None = None) -> list[str]:
    """Tên các chiều còn thiếu trên MỘT dòng bút toán. Rỗng là đủ."""
    if tk is None:
        tk = db.get(Account, getattr(dong, "account_code", "") or "")
    if tk is None:
        return []                                  # tài khoản lạ là việc của bộ kiểm khác
    thieu: list[str] = []
    for cot, ten in chieu_bat_buoc(tk):
        if not (getattr(dong, cot, "") or "").strip():
            thieu.append(ten)
    # Khai loại đối tượng thì mã đối tượng phải đúng loại ấy.
    loai = (getattr(tk, "td_doi_tuong_loai", "") or "").strip()
    ma_dt = (getattr(dong, "partner_code", "") or "").strip()
    co_phai_bat = LOAI_DOI_TUONG.get(loai)
    if getattr(tk, "td_doi_tuong", False) and co_phai_bat and ma_dt:
        from app.models.accounting import Partner
        p = db.query(Partner).filter(Partner.code == ma_dt).first()
        if p is not None and not getattr(p, co_phai_bat, False):
            thieu.append(f"đối tượng {ma_dt} không phải {loai}")
    return thieu


def kiem_chung_tu(db: Session, cac_dong: Iterable[Any]) -> dict:
    """Soi cả chứng từ. Trả về {chan, muc_do, thieu:[{dong, tai_khoan, thieu:[...]}]}."""
    thieu = []
    for i, d in enumerate(cac_dong, 1):
        t = thieu_chieu(db, d)
        if t:
            thieu.append({"dong": i, "tai_khoan": getattr(d, "account_code", ""), "thieu": t})
    md = muc_do(db, PK_THIEU_CHIEU)
    return {"chan": bool(thieu) and md == "canh_bao_va_chan", "muc_do": md, "thieu": thieu}


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Số dư bất thường – dùng `tinh_chat`, và CHỈ khi tài khoản đã khai tính chất.
#
# `tinh_chat` RỖNG nghĩa là CHƯA AI KHAI, không phải "dư Nợ". 273 tài khoản đang có đều rỗng cho
# tới khi Kế toán khai – và một tài khoản chưa khai thì không bị báo bất thường, vì báo trên một
# giả định tự đặt ra thì tệ hơn không báo. Nguyên tắc K2: trống khác không.
# ─────────────────────────────────────────────────────────────────────────────────────────────
def so_du_bat_thuong(tk: Account | None, du_no: float | None, du_co: float | None) -> str:
    """Trả lý do nếu số dư trái tính chất đã khai. Chuỗi rỗng là bình thường hoặc chưa khai."""
    if tk is None or not (tk.tinh_chat or "").strip():
        return ""
    if tk.tinh_chat == "luong_tinh":
        return ""                                   # 131, 138, 331… hai chiều đều đúng
    no, co = du_no or 0, du_co or 0
    if tk.tinh_chat == "du_no" and co > no:
        return f"TK {tk.code} khai dư Nợ nhưng đang dư Có"
    if tk.tinh_chat == "du_co" and no > co:
        return f"TK {tk.code} khai dư Có nhưng đang dư Nợ"
    return ""
