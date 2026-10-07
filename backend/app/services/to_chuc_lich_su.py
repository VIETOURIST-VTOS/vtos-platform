"""Đợt C – ghi và đọc lịch sử tổ chức.

MỘT ĐIỀU TỆP NÀY CỐ Ý KHÔNG LÀM: không đổi cách bất kỳ báo cáo nào đang tính.

Lịch sử tổ chức tồn tại để báo cáo quá khứ đọc được tổ chức TẠI THỜI ĐIỂM PHÁT SINH thay vì đọc
phòng hiện tại. Nhưng chuyển một báo cáo sang đọc lịch sử là ĐỔI CON SỐ ĐÃ CÔNG BỐ — chi phí lương
theo phòng của sáu tháng trước sẽ khác đi. Việc ấy cần người ký, không thuộc lần viết này.

Nên đợt này làm đúng hai việc: (1) từ nay mọi lần điều chuyển đều được ghi lại kèm ngày, và (2) có
hàm `tai_ngay` sẵn cho báo cáo nào được chọn để chuyển. Chuyển báo cáo nào, khi nào — chữ ký.

VÌ SAO KHÔNG CÓ CỬA RIÊNG ĐỂ GHI ĐIỀU CHUYỂN

Điều chuyển đã có một cửa: màn hình sửa hồ sơ nhân sự. Dựng thêm một cửa thứ hai nghĩa là có hai
đường đổi phòng, và đường nào quên ghi lịch sử thì lịch sử thủng đúng ở đó. Một cửa, và cửa ấy ghi.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr import Employee
from app.models.lich_su_to_chuc import LichSuToChuc

# Các trường tạo nên "một chặng tổ chức". Đổi bất kỳ trường nào trong đây là một lần điều chuyển;
# đổi lương hay số điện thoại thì không. Khai một chỗ để cửa sửa hồ sơ và phép thử đọc cùng một
# danh sách – hai bản danh sách sẽ lệch nhau ở lần sửa thứ nhất.
TRUONG_TO_CHUC = ("department", "position", "office", "company_id")
_SANG_COT = {"department": "phong", "position": "chuc_vu", "office": "van_phong",
             "company_id": "company_id"}


def _chang_cua(e: Employee) -> dict:
    return {"phong": e.department, "chuc_vu": e.position, "van_phong": e.office or "",
            "company_id": e.company_id}


def lich_su(db: Session, ma_nv: str) -> list[LichSuToChuc]:
    return list(db.execute(select(LichSuToChuc).where(LichSuToChuc.ma_nv == ma_nv)
                           .order_by(LichSuToChuc.tu_ngay, LichSuToChuc.id)).scalars())


def dang_mo(db: Session, ma_nv: str) -> LichSuToChuc | None:
    for c in reversed(lich_su(db, ma_nv)):
        if c.den_ngay is None:
            return c
    return None


def tai_ngay(db: Session, ma_nv: str, ngay: date) -> LichSuToChuc | None:
    """Người này ở đâu vào NGÀY ấy. Trả None khi chưa có chặng nào phủ ngày đó.

    None là một câu trả lời thật: trước lần điều chuyển đầu tiên thì hệ thống KHÔNG BIẾT, và người
    gọi phải tự quyết định dùng phòng hiện tại hay bỏ qua. Trả về phòng hiện tại ở đây là lặng lẽ
    biến "không biết" thành "biết", đúng cái lỗi mà cả bảng này sinh ra để chữa.
    """
    for c in lich_su(db, ma_nv):
        if c.dang_hieu_luc(ngay):
            return c
    return None


def anh_chup(e: Employee) -> dict:
    """Ảnh chụp các trường tổ chức, lấy TRƯỚC khi gán giá trị mới."""
    return {k: getattr(e, k) for k in TRUONG_TO_CHUC}


def can_dieu_chuyen(e: Employee, truoc: dict) -> bool:
    """Có trường tổ chức nào đổi không. `truoc` là ảnh chụp trước khi gán giá trị mới."""
    return any(truoc.get(k) != getattr(e, k, None) for k in TRUONG_TO_CHUC)


def ghi_dieu_chuyen(db: Session, e: Employee, truoc: dict, tu_ngay: date | None, ly_do: str,
                    boi: str) -> LichSuToChuc:
    """Đóng chặng đang mở và mở chặng mới. Gọi SAU khi hồ sơ đã mang giá trị mới.

    `truoc` là ảnh chụp các trường tổ chức TRƯỚC khi đổi — cần nó để dựng được chặng cũ cho người
    chưa từng có lịch sử. Không có `truoc` thì chặng cũ sẽ mang giá trị MỚI, tức là lịch sử ghi
    rằng người ấy vốn đã ở phòng mới từ ngày vào làm. Sai kiểu đó im lặng và không bao giờ tự lộ.

    Chặng cũ kết thúc vào NGÀY TRƯỚC ngày bắt đầu chặng mới, không kết thúc cùng ngày: hai chặng
    cùng phủ một ngày thì câu "ngày ấy người này ở đâu" có hai câu trả lời.
    """
    tu = tu_ngay or date.today()
    cu = dang_mo(db, e.code)
    if cu is not None and tu <= cu.tu_ngay:
        # Ngày hiệu lực sớm hơn (hoặc bằng) ngày bắt đầu chặng đang mở. Đóng chặng ấy vào "hôm
        # trước" sẽ cho một chặng có ngày kết thúc TRƯỚC ngày bắt đầu — một khoảng thời gian không
        # tồn tại. Từ chối thay vì tự chữa: sửa lịch sử đã ghi là việc phải làm có chủ ý, không
        # phải hệ quả phụ của một lần bấm Lưu.
        raise ValueError(
            f"Ngày hiệu lực {tu:%d/%m/%Y} sớm hơn ngày bắt đầu chặng đang mở "
            f"({cu.tu_ngay:%d/%m/%Y}). Muốn sửa lịch sử đã ghi thì phải sửa chặng ấy trước – "
            "hệ thống không tự ghi đè một chặng đã có.")
    if cu is None and not lich_su(db, e.code):
        # Chưa từng có lịch sử: dựng chặng cũ từ thứ hệ thống đang biết, đánh dấu SUY RA.
        bat_dau = e.start_date or tu
        if bat_dau > tu:
            bat_dau = tu
        cu = LichSuToChuc(
            ma_nv=e.code, phong=truoc.get("department") or "", chuc_vu=truoc.get("position") or "nv",
            van_phong=truoc.get("office") or "", company_id=truoc.get("company_id"),
            tu_ngay=bat_dau, den_ngay=None, suy_ra=True,
            ly_do="Chặng dựng lại từ hồ sơ đang có tại lần điều chuyển đầu tiên – không phải bản "
                  "ghi lập lúc ấy. Ngày bắt đầu lấy theo ngày vào làm.",
            boi=boi, luc=datetime.now())
        db.add(cu)
        db.flush()
    if cu is not None:
        cu.den_ngay = tu - timedelta(days=1)
    moi = LichSuToChuc(ma_nv=e.code, **_chang_cua(e), tu_ngay=tu, den_ngay=None,
                       ly_do=ly_do or "", boi=boi, luc=datetime.now())
    db.add(moi)
    db.flush()
    return moi


def ra(c: LichSuToChuc) -> dict:
    return {"id": c.id, "ma_nv": c.ma_nv, "phong": c.phong, "chuc_vu": c.chuc_vu,
            "van_phong": c.van_phong, "company_id": c.company_id, "tu_ngay": c.tu_ngay,
            "den_ngay": c.den_ngay, "ly_do": c.ly_do, "suy_ra": c.suy_ra, "boi": c.boi,
            "luc": c.luc}
