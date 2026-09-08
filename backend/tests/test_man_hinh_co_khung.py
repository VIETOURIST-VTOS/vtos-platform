"""Mọi màn hình phải nằm trong khung Shell.

Ngày 08/9/2026 phát hiện sáu màn hình mới nhất (/access, /ai-roles, /ngoai-le, /kiem-soat,
/doi-mat-khau, /hach-toan) được viết thiếu lớp bọc <Shell>. Hậu quả không hiện ra thành lỗi:
trang vẫn tải, số vẫn đúng – chỉ mất thanh điều hướng, và useShell() trả user RỖNG nên mọi nút
gắn theo vai trò lặng lẽ biến mất. Người dùng thấy một màn hình thiếu nút và không có cách nào
biết là do quyền hay do lỗi.

Phép thử này đọc thẳng mã nguồn giao diện. Nó không cần trình duyệt, chạy trong một giây, và
canh đúng cái chỗ đã hỏng sáu lần liên tiếp.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web" / "app"

# Trang được phép đứng ngoài khung, kèm lý do. Thêm tên vào đây phải kèm lý do thật.
NGOAI_LE = {
    "payroll": "chỉ chuyển hướng sang /hr, không vẽ gì",
    "login": "màn hình đăng nhập – chưa có phiên thì chưa có khung",
}


def test_moi_man_hinh_deu_nam_trong_shell():
    if not WEB.exists():
        return          # chỉ chạy khi có mã giao diện cạnh mã máy chủ
    thieu = []
    for p in sorted(WEB.glob("*/page.tsx")):
        ten = p.parent.name
        if ten in NGOAI_LE:
            continue
        src = p.read_text(encoding="utf-8")
        if "<Shell>" not in src:
            thieu.append(ten)
    assert not thieu, (
        "Màn hình chạy ngoài khung Shell (mất thanh điều hướng, useShell() trả user rỗng nên nút "
        f"theo vai trò biến mất): {thieu}")


def test_trang_goc_van_trong_shell():
    """Trang chủ là mẫu để so – nó hỏng thì phép thử trên vô nghĩa."""
    p = WEB / "page.tsx"
    if not p.exists():
        return
    assert "<Shell>" in p.read_text(encoding="utf-8")
