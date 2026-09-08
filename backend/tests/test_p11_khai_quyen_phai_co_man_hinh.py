"""P11 – khai quyền cho một màn hình thì màn hình đó phải tồn tại.

Vì sao việc này đáng một tệp riêng, và vì sao chốt chặn cũ chưa đủ:

Ngày 08/9/2026 một mục màn hình được khai quyền đầy đủ – có dòng trong ma trận, có bản đồ sang nhóm
API, có cả đường dẫn API chạy được và 19 phép thử xanh – nhưng KHÔNG có trang giao diện. Chức năng ấy
tồn tại trên máy chủ mà người dùng không có đường vào, và một thông điệp ghi mã còn mô tả màn hình đó
như đã dựng.

Chốt chặn duy nhất lúc ấy là tệp kiểm thử menu, đi VÒNG qua tệp menu của giao diện: nó bắt được, nhưng
bắt được một cách gián tiếp và chỉ vì tình cờ mục ấy cũng chưa vào menu. Phép thử bản đồ màn hình → API
thì im lặng đi qua, vì nó chỉ duyệt các trang ĐANG TỒN TẠI.

Đây là chốt chặn TRỰC TIẾP: đọc thẳng ma trận quyền, đối chiếu với thư mục trang. Khai quyền cho cái
chưa có thì đỏ ngay, kèm tên mục.

Chiều ngược lại cũng canh: một trang có thật mà không ai khai quyền thì theo quy ước cũ của kho là
"ai đăng nhập cũng thấy" – đúng cái mà hàng rào P2 vừa dựng lên để chấm dứt.
"""
import os, sys, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test_p11.db"; os.environ["SEED_DEMO"] = "0"; os.environ["ENV"] = "dev"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
for _f in ("test_p11.db", "test_p11.db-journal"):
    if os.path.exists(_f): os.remove(_f)
from app.services import access as AC

WEB_APP = pathlib.Path(__file__).resolve().parents[2] / "web" / "app"

# Mục được phép khai quyền mà CHƯA có trang, kèm lý do và ngày dự kiến. Không có ngày thì không được
# vào danh sách này – một dòng ngoại lệ không hạn là một dòng ở lại vĩnh viễn.
CHUA_CO_TRANG: dict[str, str] = {
    # "/vi-du": "lý do · dự kiến 15/9/2026",
}

# Trang có thật nhưng cố ý không khai quyền, kèm lý do.
KHONG_KHAI_QUYEN = {
    "login": "màn hình đăng nhập – chưa có phiên thì chưa có quyền",
    "payroll": "chỉ chuyển hướng sang /hr, không vẽ gì",
    "doi-mat-khau": "ai cũng vào được, kể cả tài khoản còn mật khẩu tạm",
    "alerts": "cảnh báo nghiệp vụ – mở cho mọi vai trò",
    "reports": "báo cáo công việc – mở cho mọi vai trò",
    "robot-reports": "báo cáo quản trị – khai quyền trong MENU_ROLES ở tên khác",
    "tours": "khai quyền ở /tours trong MENU_ROLES",
}


def _co_trang(muc: str) -> bool:
    if muc == "/":
        return (WEB_APP / "page.tsx").exists()
    return (WEB_APP / muc.strip("/") / "page.tsx").exists()


def test_moi_muc_khai_quyen_deu_co_trang():
    if not WEB_APP.exists():
        return                      # chỉ chạy khi có mã giao diện cạnh mã máy chủ
    thieu = []
    for muc in AC.MENU_ROLES:
        if muc in CHUA_CO_TRANG or _co_trang(muc):
            continue
        thieu.append(muc)
    assert not thieu, (
        "Khai quyền cho màn hình chưa dựng – chức năng tồn tại trên máy chủ mà người dùng không có "
        f"đường vào: {thieu}. Dựng trang, hoặc ghi vào CHUA_CO_TRANG kèm lý do VÀ ngày dự kiến.")


def test_muc_hoan_trang_deu_co_ly_do_va_ngay_du_kien():
    """Danh sách hoãn phải có hạn. Một dòng ngoại lệ không hạn là một dòng ở lại vĩnh viễn."""
    for muc, ly_do in CHUA_CO_TRANG.items():
        assert "dự kiến" in ly_do, f"{muc}: thiếu ngày dự kiến"
        assert muc in AC.MENU_ROLES, f"{muc}: hoãn một mục không có trong ma trận"


def test_moi_muc_khai_quyen_deu_co_ban_do_sang_nhom_api():
    """Khai quyền mà không khai gọi API nào thì hàng rào phạm vi không mở gì cho vai trò đó – màn hình
    mở ra và mọi nút bấm đều bị chặn."""
    thieu = [m for m in AC.MENU_ROLES if not AC.MAN_HINH_API.get(m)]
    assert not thieu, f"Mục khai quyền nhưng chưa khai gọi nhóm API nào: {thieu}"


def test_trang_co_that_ma_khong_ai_khai_quyen():
    """Chiều ngược lại: theo quy ước cũ, trang không khai quyền là 'ai đăng nhập cũng thấy'."""
    if not WEB_APP.exists():
        return
    # MENU_ROLES là một trong HAI chỗ khai quyền màn hình. Chỗ thứ hai là MAN_HINH_MOI_NGUOI –
    # màn hình mở cho mọi vai trò, khai ở đó chứ không liệt kê 20 vai trò trong MENU_ROLES.
    # Phép thử này trước chỉ đọc một chỗ, nên trang /phieu-luong đã khai đàng hoàng vẫn bị báo là
    # chưa khai. Đọc thiếu nguồn quyền rồi kết luận là "chưa khai" thì đúng cái nó sinh ra để chặn.
    khai = {m.strip("/") for m in AC.MENU_ROLES} | {m.strip("/") for m in AC.MAN_HINH_MOI_NGUOI}
    la = []
    for p in sorted(WEB_APP.glob("*/page.tsx")):
        ten = p.parent.name
        if ten in khai or ten in KHONG_KHAI_QUYEN:
            continue
        la.append(ten)
    assert not la, ("Trang có thật mà không khai quyền – theo quy ước cũ là ai đăng nhập cũng thấy: "
                    f"{la}. Khai vào MENU_ROLES, hoặc ghi vào KHONG_KHAI_QUYEN kèm lý do.")
