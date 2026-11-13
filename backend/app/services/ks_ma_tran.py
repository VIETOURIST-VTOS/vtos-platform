"""K12 – đối chiếu ma trận phân quyền với thư mục trang giao diện.

Đọc THẲNG hai nguồn gốc: `access.MENU_ROLES` và thư mục `web/app/*/page.tsx`. Cố tình KHÔNG đi qua tệp
menu của giao diện: menu là bản sao thứ ba, và một màn hình bị bỏ quên thường bị bỏ quên ở cả menu lẫn
ma trận quyền – đối chiếu hai bản sao cùng thiếu thì lúc nào cũng khớp, lúc nào cũng xanh.

Hai chiều, hai loại sai khác hẳn nhau:

  1. Khai quyền cho màn hình KHÔNG tồn tại. Menu dẫn tới trang trắng; tệ hơn, nó làm bảng phân quyền
     trông đầy đủ hơn thực tế và không ai đi tìm màn hình còn thiếu.
  2. Có màn hình mà KHÔNG khai quyền. Quy ước của hệ thống là "trang không liệt kê thì ai đăng nhập
     cũng thấy" – nên một màn hình quên khai không bị khoá lại, nó MỞ TOANG. Đây chính là cách hồ sơ
     xe và bảng giá vốn đội xe từng mở cho nhân viên kinh doanh trước 07/9/2026.

Robot chỉ ĐO và MỞ VIỆC. Nó không tự thêm dòng vào ma trận quyền: quyết ai được xem màn hình nào là
việc của người, và một robot tự cấp quyền cho chính mình là thứ không được phép có trong hệ thống này.
"""
import pathlib
from sqlalchemy.orm import Session

from app.services import access as AC

# Màn hình KHÔNG cần khai quyền, kèm lý do. Danh sách này phải ngắn và mỗi dòng phải tự bảo vệ được.
NGOAI_LE = {
    "login": "Trang đăng nhập – bắt buộc mở cho người chưa có phiên.",
    # CG-1 26/10/2026 — không gian của khách hàng / đối tác / cổ đông sau khi đăng nhập ở cổng kết nối.
    "cong": "Trang của người ở cổng NGOÀI – không có tài khoản VTOS nên không có vai trò; dữ liệu đi qua phiên cổng ngoài (khoá ký riêng), không qua MENU_ROLES.",
    "doi-mat-khau": "Tự đổi mật khẩu của chính mình – mọi tài khoản đều phải vào được.",
    "payroll": "Chỉ chuyển hướng sang /hr, không hiển thị dữ liệu; quyền nằm ở /hr.",
    # R5-5 · 13/11/2026 — Chủ tịch «ok sửa»: một bàn, một đường dẫn. Người quyết: Chủ tịch.
    "ban-kd-le": "Chỉ chuyển hướng sang /fit, không hiển thị dữ liệu; bàn GĐ KD lẻ và quyền của nó nằm ở /fit.",
}


def thu_muc_web() -> pathlib.Path | None:
    """Thư mục trang giao diện, hoặc None khi mã nguồn giao diện không nằm cùng máy chủ.

    Ảnh Docker của máy chủ chỉ đóng gói thư mục backend. Không đo được thì trả None và bộ kiểm im lặng –
    im lặng vì KHÔNG ĐO ĐƯỢC khác hẳn im lặng vì KHÔNG CÓ LỖI, và đoán bừa ở đây là dựng cảnh báo giả.
    """
    p = pathlib.Path(__file__).resolve().parents[3] / "web" / "app"
    return p if p.is_dir() else None


def trang_giao_dien() -> set[str] | None:
    web = thu_muc_web()
    if web is None: return None
    return {x.parent.name for x in web.glob("*/page.tsx")}


def doi_chieu() -> dict:
    co = trang_giao_dien()
    if co is None:
        return {"doc_duoc": False, "khai_thieu_man_hinh": [], "man_hinh_thieu_quyen": [],
                "so_khai": len(AC.MENU_ROLES), "so_man_hinh": 0}
    khai = {k.lstrip("/") for k in AC.MENU_ROLES}
    return {"doc_duoc": True,
            "khai_thieu_man_hinh": sorted(khai - co),
            "man_hinh_thieu_quyen": sorted(co - khai - set(NGOAI_LE)),
            "so_khai": len(khai), "so_man_hinh": len(co)}


def _ma_tran_quyen(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot. Mở việc cho CNTT; ai được xem thì Chủ tịch quyết."""
    d = doi_chieu()
    if not d["doc_duoc"]: return []
    ra = []
    for ten in d["khai_thieu_man_hinh"]:
        ra.append({"ma": f"quyen_thua#{ten}", "loai": "quyen_thua_man_hinh", "muc": "vang",
                   "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt", "doi_tuong": f"/{ten}",
                   "tom_tat": f"Ma trận phân quyền khai màn hình /{ten} nhưng giao diện không có trang này",
                   "chi_tiet": {"vai_tro_dang_khai": list(AC.MENU_ROLES.get(f"/{ten}", ()))}})
    for ten in d["man_hinh_thieu_quyen"]:
        ra.append({"ma": f"man_hinh_ho_quyen#{ten}", "loai": "man_hinh_ho_quyen", "muc": "do",
                   "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt", "doi_tuong": f"/{ten}",
                   "tom_tat": f"Màn hình /{ten} không có trong ma trận phân quyền – theo quy ước hiện "
                              f"hành thì mọi tài khoản đăng nhập đều mở được",
                   "chi_tiet": {"quy_uoc": "trang không liệt kê trong MENU_ROLES = ai đăng nhập cũng thấy"}})
    return ra


def bang(db: Session) -> dict:
    d = doi_chieu()
    d["ngoai_le"] = NGOAI_LE
    return d
