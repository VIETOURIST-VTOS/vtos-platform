# -*- coding: utf-8 -*-
"""MỞ LẠI KỲ KẾ TOÁN ĐÃ KHÓA — Đợt E6, 13/10/2026. Chủ tịch chốt: Kế toán trưởng trình, Chủ tịch ký.

VÌ SAO CÓ TỆP NÀY

Trước đợt này khóa kỳ là MỘT CHIỀU. `accounting.lock_period` ghi một dòng `period_locks`, và
không có hàm nào, không có cửa nào gỡ nó ra — kể cả cho Chủ tịch. Khóa nhầm một kỳ là kẹt thật:
mọi bút toán vào kỳ ấy bị `post_entry` chặn, và cách duy nhất còn lại là sửa thẳng cơ sở dữ liệu,
tức là đi vòng qua chính lớp kiểm soát vừa dựng.

VÌ SAO KHÔNG MỞ BẰNG MỘT NÚT

Mở lại một kỳ đã khóa là mở đường sửa số đã chốt. Nó phải đắt hơn một lần bấm:

  1. HAI NGƯỜI. Kế toán trưởng trình, Chủ tịch ký — giữ đúng luật "người trình không tự ký" đang
     chạy ở ba cửa chính sách. Chủ tịch là người ký DUY NHẤT nên ông không tự trình được, y như
     `propose_param` và `trinh_dieu_khoan`.
  2. LÝ DO BẮT BUỘC, tối thiểu 30 ký tự, và nó hiện cho người ký đọc trước khi ký. Một kỳ mở lại
     không có lý do thì sáu tháng sau không ai dựng lại được câu chuyện.
  3. KHÔNG MỞ KỲ ĐÃ CHỐT THEO BẢN KIỂM TOÁN. Sửa số đã được kiểm toán xác nhận là việc khác hẳn,
     đi đường điều chỉnh kỳ sau — không đi cửa này.
  4. NHÌN THẤY ĐƯỢC cho tới khi khóa lại. Một kỳ mở mà ai cũng quên là chỗ số liệu lặng lẽ đổi
     sau lưng, nên `dang_mo_lai` đứng trên bàn làm việc cho tới khi có người khóa lại.

ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không tự khóa lại sau N ngày. Một cái khóa tự đóng sẽ đóng đúng lúc
Kế toán đang ghi dở, và lúc ấy họ mất việc đang làm mà không hiểu vì sao.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting import JournalEntry, PeriodLock
from app.models.core import ROLES, User
from app.models.mo_lai_ky import MoLaiKy
from app.services import chu_ky as _CK
from app.services import rules as R

LOAI_CHU_KY = "mo_lai_ky"
TOI_THIEU_LY_DO = 30

# Nguồn của bút toán chốt sổ theo bản kiểm toán. Kỳ nào đã có bút toán nguồn này thì số của nó đã
# được kiểm toán xác nhận — xem `misa.import_audited_checkpoint`.
NGUON_KIEM_TOAN = ("kiem_toan", "ket_chuyen")
REF_KIEM_TOAN = ("kt:", "kt-close:")


class SaiMoLaiKy(ValueError):
    """Không mở lại kỳ được, kèm câu nói ra vì sao."""


def _da_chot_kiem_toan(db: Session, period: str) -> str:
    """Kỳ này đã chốt theo bản kiểm toán chưa — trả về mã chứng từ làm bằng chứng, hoặc rỗng.

    Hỏi theo DẤU VẾT trong sổ chứ không theo một cột cờ: cột cờ phải có người bấm, mà người quên
    bấm thì kỳ đã kiểm toán vẫn mở ra được. Bút toán chốt sổ kiểm toán thì không ai quên ghi —
    nó chính là việc đang làm.
    """
    for e in db.execute(select(JournalEntry).where(JournalEntry.period == period,
                                                   JournalEntry.status == "da_ghi_so")).scalars():
        ref = e.source_ref or ""
        if (e.source_type or "") in NGUON_KIEM_TOAN and any(ref.startswith(x) for x in REF_KIEM_TOAN):
            return e.code
    return ""


def dang_cho_ky(db: Session, period: str | None = None) -> list[MoLaiKy]:
    q = select(MoLaiKy).where(MoLaiKy.trang_thai == "cho_ky")
    if period:
        q = q.where(MoLaiKy.period == period)
    return list(db.execute(q.order_by(MoLaiKy.id)).scalars())


def dang_mo_lai(db: Session) -> list[MoLaiKy]:
    """Kỳ đã mở lại mà chưa khóa lại. Đây là thứ phải nhìn thấy được trên bàn làm việc."""
    return list(db.execute(select(MoLaiKy).where(MoLaiKy.trang_thai == "da_ky")
                           .order_by(MoLaiKy.period)).scalars())


def de_nghi(db: Session, u: User, period: str, ly_do: str) -> MoLaiKy:
    """Kế toán trưởng trình một đề nghị mở lại kỳ. KHÔNG mở gì cả — chỉ lập hồ sơ."""
    ly_do = (ly_do or "").strip()
    if len(ly_do) < TOI_THIEU_LY_DO:
        raise SaiMoLaiKy(f"Lý do phải dài ít nhất {TOI_THIEU_LY_DO} ký tự. Người ký đọc đúng dòng "
                         f"này trước khi quyết, và sáu tháng sau nó là thứ duy nhất còn lại để "
                         f"giải thích vì sao kỳ đã khóa lại được mở ra.")
    if not db.get(PeriodLock, period):
        raise SaiMoLaiKy(f"Kỳ {period} đang MỞ, không có gì để mở lại.")
    if dang_cho_ky(db, period):
        raise SaiMoLaiKy(f"Kỳ {period} đã có một đề nghị mở lại đang chờ Chủ tịch ký.")
    ma = _da_chot_kiem_toan(db, period)
    if ma:
        raise SaiMoLaiKy(
            f"Kỳ {period} đã chốt theo bản kiểm toán (chứng từ {ma}). Số của kỳ này đã được kiểm "
            f"toán xác nhận, nên sửa nó là việc khác hẳn — đi đường bút toán điều chỉnh ghi vào "
            f"kỳ sau, không mở lại kỳ cũ.")
    # NGƯỜI TRÌNH KHÔNG TỰ KÝ. Cùng một phép chặn, cùng một câu, với `propose_param` (Đợt LG2) và
    # `trinh_dieu_khoan` (Đợt E4a): Chủ tịch là người ký duy nhất nên ông tự trình là một hồ sơ
    # KHÔNG AI KÝ ĐƯỢC. Nói ngay ở cửa trình thay vì để nó nằm chờ.
    can = _CK.can_ky(LOAI_CHU_KY)
    if u.role in can and len(can) == 1:
        raise SaiMoLaiKy(
            f"{ROLES.get(u.role, u.role)} là người ký DUY NHẤT của việc mở lại kỳ, nên không tự "
            f"trình được đề nghị của chính mình — chữ ký ấy khi đó không còn là một lớp kiểm "
            f"soát. Nhờ Kế toán trưởng trình, rồi ký.")

    d = MoLaiKy(period=period, ly_do=ly_do[:500], trinh_boi=u.username, trinh_vai=u.role,
                trinh_luc=datetime.now(), trang_thai="cho_ky")
    db.add(d)
    R.audit(db, u.username, u.role, "de_nghi_mo_lai_ky", f"period:{period}",
            after={"ly_do": d.ly_do})
    db.commit()
    return d


def ky(db: Session, u: User, d: MoLaiKy) -> dict:
    """Chủ tịch ký — và ĐÚNG LÚC NÀY kỳ mới thật sự mở ra."""
    if d.trang_thai != "cho_ky":
        raise SaiMoLaiKy(f"Đề nghị này không còn chờ ký (trạng thái {d.trang_thai}).")
    can = _CK.can_ky(LOAI_CHU_KY)
    if u.role not in can:
        raise SaiMoLaiKy("Chỉ " + " và ".join(ROLES.get(v, v) for v in can) + " ký mở lại kỳ được.")
    if u.username == d.trinh_boi:
        raise SaiMoLaiKy("Người trình không tự ký. Việc trình và việc ký phải là hai người, "
                         "bất kể hai người ấy to đến đâu.")
    khoa = db.get(PeriodLock, d.period)
    if not khoa:
        raise SaiMoLaiKy(f"Kỳ {d.period} đang mở sẵn rồi — không cần ký.")

    # GỠ KHÓA. Xoá dòng `period_locks` chứ không thêm một cột cờ thứ hai: `accounting.is_locked`
    # đọc đúng bảng này, và dựng một đường thứ hai để nói "đã khóa nhưng đang mở" là tạo hai câu
    # trả lời cho một câu hỏi. Dấu vết của lần khóa cũ không mất — nó nằm ở chính dòng này.
    d.khoa_cu_boi, d.khoa_cu_luc, d.khoa_cu_ghi_chu = khoa.locked_by, khoa.locked_at, khoa.note
    db.delete(khoa)
    d.ky_boi, d.ky_vai, d.ky_luc, d.trang_thai = u.username, u.role, datetime.now(), "da_ky"
    R.audit(db, u.username, u.role, "ky_mo_lai_ky", f"period:{d.period}",
            before={"khoa_boi": d.khoa_cu_boi}, after={"ly_do": d.ly_do})
    db.commit()
    return {"message": f"Đã mở lại kỳ {d.period}. Ghi xong thì KHÓA LẠI — kỳ đang mở còn hiện "
                       f"trên bàn làm việc cho tới lúc ấy."}


def tu_choi(db: Session, u: User, d: MoLaiKy, ly_do: str) -> dict:
    """Từ chối cũng phải có lý do: người trình cần biết sửa gì để trình lại."""
    if d.trang_thai != "cho_ky":
        raise SaiMoLaiKy(f"Đề nghị này không còn chờ ký (trạng thái {d.trang_thai}).")
    if u.role not in _CK.can_ky(LOAI_CHU_KY):
        raise SaiMoLaiKy("Chỉ người ký của việc mở lại kỳ mới từ chối được.")
    if not (ly_do or "").strip():
        raise SaiMoLaiKy("Phải ghi lý do từ chối — người trình cần biết sửa gì để trình lại.")
    d.trang_thai, d.ky_boi, d.ky_vai, d.ky_luc = "tu_choi", u.username, u.role, datetime.now()
    d.tu_choi_ly_do = ly_do.strip()[:500]
    R.audit(db, u.username, u.role, "tu_choi_mo_lai_ky", f"period:{d.period}",
            after={"ly_do": d.tu_choi_ly_do})
    db.commit()
    return {"message": f"Đã từ chối mở lại kỳ {d.period}."}


def danh_dau_da_khoa_lai(db: Session, period: str, boi: str) -> None:
    """Gọi từ cửa khóa kỳ: đóng vòng cho mọi đề nghị đang mở của kỳ ấy.

    Đặt ở đây chứ không ở `accounting.lock_period`: hàm kia là phép khóa kỳ chung, nó không phải
    biết gì về việc mở lại. Cửa khóa kỳ gọi hàm này sau khi khóa xong.
    """
    for d in db.execute(select(MoLaiKy).where(MoLaiKy.period == period,
                                              MoLaiKy.trang_thai == "da_ky")).scalars():
        d.trang_thai, d.khoa_lai_boi, d.khoa_lai_luc = "da_khoa_lai", boi, datetime.now()


def dong(d: MoLaiKy) -> dict:
    """Một dòng cho màn hình. Gửi cả tên vai đọc được, không bắt màn hình tự dịch mã vai."""
    return {"id": d.id, "period": d.period, "ly_do": d.ly_do, "trang_thai": d.trang_thai,
            "trinh_boi": d.trinh_boi, "trinh_vai": ROLES.get(d.trinh_vai, d.trinh_vai),
            "trinh_luc": d.trinh_luc,
            "ky_boi": d.ky_boi, "ky_vai": ROLES.get(d.ky_vai, d.ky_vai), "ky_luc": d.ky_luc,
            "tu_choi_ly_do": d.tu_choi_ly_do,
            "khoa_lai_boi": d.khoa_lai_boi, "khoa_lai_luc": d.khoa_lai_luc,
            "khoa_cu_boi": d.khoa_cu_boi, "khoa_cu_luc": d.khoa_cu_luc}
