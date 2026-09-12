# -*- coding: utf-8 -*-
"""Đ-1 · Canh CỬA của phân hệ quyết toán lớp 3.

Ngày 12/9/2026 bản rà tìm ra một chỗ hỏng không phép thử nào bắt được: máy chủ có 22 đường
`/api/v1/quyet-toan-lop3`, thành phần `web/components/QuyetToanForm.tsx` viết xong đủ sáu khối nhập
(dòng khách có mã đặt chỗ · doanh thu · chiết tính theo dòng có dự chi/thực chi/ngoại tệ/thuế suất ·
chi theo từng khách · phương tiện · chi HDV) — nhưng **không trang nào trong `web/app` import nó**.

Người dùng không có đường vào. Theo đúng ranh giới Chủ tịch chốt 09/9/2026 — *"mỗi con số cần một
cửa nhập hoặc cửa tải; không có cửa thì đó là việc còn thiếu"* — đó là việc còn thiếu, và nó tồn tại
được vì mọi phép thử đều xanh: phép thử máy chủ chạy đủ, phép thử giao diện không có, `tsc` không
kêu vì một thành phần không ai dùng vẫn hợp lệ, `next build` cũng không kêu.

Phép thử này canh đúng một điều: **cửa còn mở**. Nó đọc mã nguồn giao diện như văn bản, không dựng
trình duyệt — rẻ, chạy trong CI sẵn có, và đủ để bắt lại đúng lỗi đã xảy ra.

BA ĐIỀU PHÉP THỬ NÀY CỐ Ý KHÔNG LÀM:

  1. Không kiểm thành phần hiển thị ra gì. Đó là việc của phép thử giao diện thật, và một phép thử
     đọc chuỗi mà cố đoán kết quả hiển thị là phép thử đỏ mỗi lần ai đó đổi một chữ trong nhãn.
  2. Không bắt cửa phải nằm ở MỘT trang cụ thể. Hôm nay nó ở tab của `/tours` theo đúng quyết định
     11/9 (không dựng lối vào thứ hai); mai có thể chuyển chỗ. Điều phải giữ là CÓ lối vào.
  3. Không đòi mọi thành phần trong `web/components` đều được dùng. Nhiều thành phần là mảnh dùng
     chung, và một luật chung như thế sẽ đỏ vì những lý do chẳng liên quan gì tới cửa nhập liệu.
"""
import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[2]
WEB_APP = GOC / "web" / "app"
THANH_PHAN = GOC / "web" / "components" / "QuyetToanForm.tsx"

# Sáu khối mà biểu nhập phải còn đủ. Mất một khối là mất cửa của cả một mặt nghiệp vụ, và mất lặng
# lẽ — vì năm khối còn lại vẫn chạy.
SAU_KHOI = ["khach", "doanh-thu", "chi", "khach-chi-phi", "phuong-tien", "hdv-chi"]


def _co_web() -> bool:
    return WEB_APP.is_dir() and THANH_PHAN.is_file()


pytestmark = pytest.mark.skipif(not _co_web(), reason="Không có thư mục web trong bản này")


def _cac_tep_app() -> list[Path]:
    return [p for p in WEB_APP.rglob("*.tsx")]


def test_QuyetToanForm_PHAI_duoc_mot_trang_nao_do_import():
    """Đây là phép thử chính. Đỏ ở đây nghĩa là cửa đã đóng lại.

    ĐỪNG sửa phép thử này cho hết đỏ — hãy gắn lại thành phần vào một trang.
    """
    dung = [p for p in _cac_tep_app()
            if re.search(r'import\s+QuyetToanForm\s+from\s+["\']@/components/QuyetToanForm["\']',
                         p.read_text(encoding="utf-8"))]
    assert dung, (
        "KHÔNG TRANG NÀO trong web/app import QuyetToanForm.\n"
        "  22 đường /api/v1/quyet-toan-lop3 của máy chủ lại không có cửa cho người dùng.\n"
        "  Đây đúng là lỗi đã xảy ra ngày 12/9/2026 và không phép thử nào bắt được.\n"
        "  Cách sửa: gắn <QuyetToanForm tourId={...} toast={...} /> vào một trang, ĐỪNG sửa phép thử.")


def test_trang_gan_cua_PHAI_duoc_khai_tien_to_api_lop3():
    """Gắn thành phần vào một trang chưa khai `/api/v1/quyet-toan-lop3` thì người dùng bấm vào sẽ bị
    hàng rào vai trò chặn, và họ chỉ thấy một màn hình báo lỗi quyền — trông y hệt như hỏng."""
    from app.services.access import MAN_HINH_API

    dung = [p for p in _cac_tep_app()
            if "QuyetToanForm" in p.read_text(encoding="utf-8") and "import" in p.read_text(encoding="utf-8")]
    assert dung
    # Đường dẫn màn hình suy từ vị trí tệp: web/app/tours/[id]/page.tsx -> /tours
    man_hinh = set()
    for p in dung:
        phan = p.relative_to(WEB_APP).parts
        man_hinh.add("/" + (phan[0] if phan and phan[0] != "page.tsx" else ""))
    khai = {m for m in man_hinh
            if any("/api/v1/quyet-toan-lop3" in x for x in MAN_HINH_API.get(m, ()))}
    assert khai, (
        f"Màn hình {sorted(man_hinh)} có gắn biểu nhập lớp 3 nhưng chưa màn hình nào được khai tiền "
        f"tố /api/v1/quyet-toan-lop3 trong access.MAN_HINH_API.\n"
        f"  Người dùng sẽ bấm vào một tab rồi nhận lỗi quyền – trông y hệt như hỏng.")


def test_bieu_nhap_con_du_sau_khoi():
    """Mất một khối là mất cửa của cả một mặt nghiệp vụ, và mất lặng lẽ."""
    src = THANH_PHAN.read_text(encoding="utf-8")
    thieu = [k for k in SAU_KHOI if k not in src]
    assert not thieu, (
        f"Biểu nhập quyết toán thiếu cửa cho: {thieu}.\n"
        f"  Sáu mặt của lớp 3 phải có đủ sáu cửa; năm cửa còn lại vẫn chạy nên mất một cửa không ai kêu.")


def test_bieu_nhap_KHONG_co_o_nao_cho_go_tong():
    """Nguyên tắc 1 của chính biểu này: máy cộng, người không gõ tổng.

    Đo trên tệp thật: ô tổng một nhóm chi ghi 3.990.000 trong khi năm dòng của chính nhóm ấy cộng
    lại được 4.200.000. Hễ còn một ô cho gõ tổng thì lỗi ấy còn đường quay lại.
    """
    src = THANH_PHAN.read_text(encoding="utf-8")
    xau = re.findall(r'khoa:\s*"(tong[_a-z]*)"', src)
    assert not xau, f"Biểu nhập có ô cho gõ tổng: {xau}. Tổng phải do máy chủ cộng từ các dòng."
