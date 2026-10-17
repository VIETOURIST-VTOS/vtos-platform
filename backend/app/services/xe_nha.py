# -*- coding: utf-8 -*-
"""XE NHÀ trên tờ quyết toán — một luật, ba chỗ dùng (Chủ tịch chốt 17/10/2026).

Bốn điều Chủ tịch chốt cho ô chọn xe ở mục «Phương tiện»:
  1. Xe thuê ngoài KHÔNG nằm trong danh sách chọn. Khi nào thuê thì người nhập tự gõ biển số.
  2. Đã chọn một xe nhà thì biển số, số chỗ và dấu «xe nhà» KHOÁ theo hồ sơ xe — máy chủ ghi đè,
     không tin con số màn hình gửi lên.
  3. Xe ngừng khai thác, đã bán: ẩn luôn, không hiện trên màn hình.
  4. Có cửa GẮN TAY cho chặng đã nhập (nạp từ mẫu, hoặc gõ biển trước khi có ô chọn) mà biển trùng
     một xe nhà nhưng chưa nối vào hồ sơ xe.

Hai câu hỏi khác nhau nên tách hai hàm:
  - `la_xe_nha(v)`  — chiếc xe này có phải của nhà không. Dùng để ĐỐI CHIẾU chặng cũ (DX-2 nhóm B),
    nên KHÔNG xét vòng đời: một chuyến tháng trước chạy bằng chiếc xe nay đã bán vẫn là xe nhà.
  - `chon_duoc(v)`  — hôm nay có được chọn chiếc xe này vào một chặng không. Thêm điều kiện còn
    khai thác. Đây là danh sách hiện trên màn hình.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import Vehicle

# Quyền khai thác không làm một chiếc xe thành «xe nhà»: xe thuê là thuê ngoài (điều 1), xe không
# có quyền khai thác thì không điều đi được.
QUYEN_KHONG_PHAI_XE_NHA = ("thue", "khong")


def la_xe_nha(v: Vehicle) -> bool:
    """Xe của nhà: thuộc đội nội bộ (không phải xe hợp tác hỗ trợ) và không phải xe thuê."""
    return (v.kind or "noi_bo") == "noi_bo" and (v.op_right or "so_huu") not in QUYEN_KHONG_PHAI_XE_NHA


def chon_duoc(v: Vehicle) -> bool:
    """Được hiện trong ô chọn: xe nhà, còn hoạt động, đang khai thác (điều 3)."""
    return la_xe_nha(v) and bool(v.active) and (v.lifecycle or "dang_khai_thac") == "dang_khai_thac"


def ds_chon_duoc(db: Session) -> list[Vehicle]:
    return [v for v in db.execute(select(Vehicle).order_by(Vehicle.plate)).scalars() if chon_duoc(v)]


def bien_chuan(s: str | None) -> str:
    """«51B-456.78», «51b 45678» và «51B45678» là một biển."""
    return "".join(ch for ch in (s or "") if ch.isalnum()).upper()


def xe_nha_theo_bien(db: Session) -> dict:
    """Biển chuẩn → xe nhà. Mọi vòng đời: dùng để đối chiếu chặng ĐÃ chạy, không phải để chọn mới."""
    ra = {}
    for v in db.execute(select(Vehicle).order_by(Vehicle.id)).scalars():
        b = bien_chuan(v.plate)
        if b and la_xe_nha(v):
            ra[b] = v
    return ra


def lech_khai_thue_ngoai(db: Session, t) -> dict:
    """Đối chiếu HAI LỜI KHAI về cùng một chuyện (Chủ tịch chốt 17/10/2026: giữ cả hai).

      - Cờ «thuê xe ngoài» trên CHUYẾN BÁN (`tours.thue_xe_ngoai` + lý do) — khai cả chuyến.
      - Các chặng ô tô trên tờ quyết toán — chặng nào nối hồ sơ xe nhà là xe nhà, còn lại thuê ngoài.

    Hai tầng khác nhau nên không gộp được: chặng không có LÝ DO, cờ không có CHẶNG. Nhưng hai lời
    khai nói ngược nhau thì ít nhất một lời sai, và máy phải nói ra chứ không chọn hộ bên nào.
    CHỈ ĐỌC — không sửa cờ, không sửa chặng.
    """
    from app.models.lop3_tour import TourPhuongTien
    from app.services.doi_chieu_xe_ngoai import LOAI_XE, _thue_ngoai

    chang = list(db.execute(select(TourPhuongTien).where(
        TourPhuongTien.tour_id == t.id, TourPhuongTien.loai == LOAI_XE)).scalars())
    ngoai = [x for x in chang if _thue_ngoai(x)]
    co = bool(t.thue_xe_ngoai)
    ra = {"thue_xe_ngoai": co, "ly_do_thue_ngoai": t.ly_do_thue_ngoai or "",
          "so_chang_o_to": len(chang), "so_chang_thue_ngoai": len(ngoai), "lech": None}
    if not co and ngoai:
        ra["lech"] = (f"Chuyến khai KHÔNG thuê xe ngoài, nhưng tờ quyết toán có {len(ngoai)} chặng ô tô "
                      "thuê ngoài. Hoặc khai lại cờ ở chuyến, hoặc gắn các chặng ấy vào xe nhà.")
    elif co and chang and not ngoai:
        ra["lech"] = ("Chuyến khai CÓ thuê xe ngoài, nhưng mọi chặng ô tô trên tờ quyết toán đều là "
                      "xe nhà. Một trong hai lời khai sai.")
    elif co and not (t.ly_do_thue_ngoai or ""):
        ra["lech"] = "Chuyến khai có thuê xe ngoài nhưng chưa chọn lý do."
    return ra
