"""R5 · Cửa đọc của bàn làm việc Giám đốc Kinh doanh lẻ (/ban-kd-le) — Chủ tịch duyệt 13/11/2026.

MỘT TIỀN TỐ RIÊNG, cùng lập luận với `ban_tour_le.py`: gắn nhờ vào một nhóm API có sẵn là nới CẢ
nhóm ấy cho mọi vai mở được màn mới.

CHỈ ĐỌC. Bàn không có cửa ghi nào: mọi việc làm ở màn đang giữ nghiệp vụ, mở ngay trong bàn.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.core import User
from app.services import ban_kd_le as S
from app.services import nho_tam as NHO

# R5-24 · NHỚ 2 PHÚT (Chủ tịch 14/11/2026 «load rất chậm», chọn «1»: lưu sẵn 1–2 phút, chấp nhận số chậm cập
# nhật tối đa 2 phút). Đo trên crm: tổng quan bàn TP 5,4 giây khi gọi riêng, 25–42 giây khi cả bàn bắn bảy
# cửa cùng lúc vì máy chủ một tiến trình xếp hàng mọi lệnh. Nhớ lại thì lần mở thứ hai (F5, đổi tab về, người
# khác cùng vai) không tính lại. KHOÁ MANG VAI VÀ NGƯỜI (luật 1 · services/nho_tam.py): bàn TP / Trưởng nhóm /
# Chuyên viên cắt số theo chính người đăng nhập. `refresh=true` tính lại ngay (luật 2). Lỗi không được nhớ (luật 3).
KHO_BAN = NHO.Kho("ban_kd_le", 120)


def _nho(khoa: tuple, refresh: bool, tinh, db: Session):
    from datetime import date
    khoa = (*khoa, date.today().isoformat(), id(db.get_bind()))
    if not refresh:
        cu = KHO_BAN.lay(khoa)
        if cu is not None:
            return {**cu, "nho_tam": True}
    return KHO_BAN.dat(khoa, tinh())

# R5-5 (13/11/2026): bàn chạy ở /fit — màn của CẢ phòng Lẻ — nên phạm vi nhóm API rộng hơn bàn; hàng rào
# THẬT của bàn là danh sách này (TP, trưởng nhóm, NV mở /fit gặp trang hai tab, gọi cửa này thì 403).
# Gương: VAI_BAN_KD_LE ở web/components/Shell.tsx (phép thử so hai chỗ). Chủ tịch chốt 13/11/2026: Giám đốc KD làm việc
# trên bàn; Chủ tịch, TGĐ (và hai vai đọc nền bks, robot_ks) mở để xem. tp_kd, tn_kd chưa vào đợt này.
# R5-5: cntt rời danh sách — cntt không thuộc phòng Lẻ nên không mở được /fit, chỗ duy nhất còn bàn.
XEM = ("chutich", "tgd", "bks", "robot_ks", "gd_kd")

router = APIRouter(prefix="/api/v1/ban-kd-le", tags=["ban-kd-le"])


@router.get("/tong-quan")
def tong_quan(refresh: bool = False,
              u: User = Depends(require_roles(*XEM, mo_ta="bàn làm việc Giám đốc Kinh doanh lẻ")),
              db: Session = Depends(get_db)):
    # Bàn GĐ không cắt theo người (cả phòng) — khoá theo vai là đủ.
    return _nho(NHO.khoa_vai(u.role, "tong_quan"), refresh, lambda: S.tong_quan(db), db)


@router.get("/doanh-thu")
def doanh_thu(nam: int = 0, u: User = Depends(require_roles(*XEM, mo_ta="doanh thu – chỉ tiêu tour lẻ")),
              db: Session = Depends(get_db)):
    """Tách khỏi /tong-quan: 12 tháng doanh thu tốn vài giây, bàn hiện trước rồi biểu đồ hiện sau."""
    from datetime import date
    return S.doanh_thu_le(db, nam or date.today().year)


# ─────────────── R5-7 · ba bàn của phòng: Trưởng phòng, Trưởng nhóm, Chuyên viên ───────────────
# Chủ tịch duyệt bản xem trước 13/11/2026. Cùng tiền tố /api/v1/ban-kd-le — nhóm này đã tới được qua /fit
# (R5-5), nên ba bàn KHÔNG nới thêm quyền màn hình nào. Hàng rào thật là danh sách dưới đây, và phạm vi
# số (cả phòng / nhóm / chính mình) cắt ở `services/ban_kd_vai.py`, không ở trình duyệt.
from app.services import ban_kd_vai as VAI_S  # noqa: E402

VAI_PHONG = tuple(VAI_S.VAI_BAN)          # ("tp_kd", "tn_kd", "nv_kd")


@router.get("/vai/tong-quan")
def vai_tong_quan(refresh: bool = False,
                  u: User = Depends(require_roles(*VAI_PHONG, mo_ta="bàn làm việc của tôi ở Kinh doanh lẻ")),
                  db: Session = Depends(get_db)):
    """Không nhận user_id hay đơn vị — cố ý: bàn của ai là của người đăng nhập."""
    return _nho(NHO.khoa_vai(u.role, u.id, "vai_tong_quan"), refresh, lambda: VAI_S.tong_quan(db, u), db)


@router.get("/vai/doanh-thu")
def vai_doanh_thu(nam: int = 0,
                  u: User = Depends(require_roles(*VAI_PHONG, mo_ta="doanh thu – chỉ tiêu trên bàn của tôi")),
                  db: Session = Depends(get_db)):
    from datetime import date
    return VAI_S.doanh_thu_12(db, u, nam or date.today().year)


# ─────────────── R5-12 · một khối Doanh thu – Chỉ tiêu kiểu đường lũy kế ───────────────
@router.get("/nhip")
def nhip_phong(ky: str = "thang", refresh: bool = False,
               u: User = Depends(require_roles(*XEM, mo_ta="doanh thu – chỉ tiêu tour lẻ")),
               db: Session = Depends(get_db)):
    """Bàn GĐ KD: chỉ «Của phòng» (Chủ tịch chốt 14/11/2026)."""
    try:
        return _nho(NHO.khoa_vai(u.role, u.id, "nhip", "phong", ky), refresh, lambda: VAI_S.nhip(db, u, "phong", ky), db)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/vai/nhip")
def vai_nhip(pham_vi: str = "phong", ky: str = "thang", refresh: bool = False,
             u: User = Depends(require_roles(*VAI_PHONG, mo_ta="doanh thu – chỉ tiêu trên bàn của tôi")),
             db: Session = Depends(get_db)):
    """Bàn TP / Trưởng nhóm / Chuyên viên: «Của phòng» hoặc «Của tôi» (chỉ chính người đăng nhập)."""
    try:
        return _nho(NHO.khoa_vai(u.role, u.id, "nhip", pham_vi, ky), refresh, lambda: VAI_S.nhip(db, u, pham_vi, ky), db)
    except ValueError as e:
        raise HTTPException(400, str(e))
