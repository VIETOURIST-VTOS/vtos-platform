# -*- coding: utf-8 -*-
"""TX-2 · Cửa đề nghị của tài xế — Chủ tịch quyết 05/10/2026.

> "Liên quan đến sửa chữa, hư hỏng, tiền bạc là do TGĐ / CT duyệt và thấy."

Luật ấy KHÔNG đổi người ký: TGĐ vẫn ký, Chủ tịch vẫn ký khi cần hai chữ ký. Nó đổi người XÁC NHẬN
NGHIỆP VỤ ở bước đầu — Giám đốc đội xe. Bộ hàng rào này canh ba điều, và mỗi điều là một cách hỏng
đã thấy ở nơi khác trong chính kho mã này:

  1. BẢNG LOẠI CHI NẰM Ở BỐN CHỖ và phải khớp nhau. Hai bảng khai tay thì sớm muộn cũng lệch, và
     lúc lệch thì màn hình nói sai tên người phụ trách mà không ai báo lỗi.
  2. MỞ CỬA CHO TÀI XẾ KHÔNG ĐƯỢC THÀNH MỞ SỔ CHI TOÀN CÔNG TY. Ba lớp chặn, và phép thử đòi đủ ba.
  3. TÀI XẾ KHÔNG LẬP ĐƯỢC ĐỀ NGHỊ SỬA CHỮA. Lúc xe vừa hỏng thì chưa có số tiền và chưa có garage;
     bắt họ lập đề nghị chi là bắt họ bịa hai con số — đúng thứ ranh giới 09/9/2026 cấm.
"""
import os
import sys
import io
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from app.services import ops as O            # noqa: E402
from app.services import luong_viec as LV    # noqa: E402
from app.services import misa as MS          # noqa: E402
from app.services import access as AC        # noqa: E402

HAI_LOAI = ("sua_chua_xe", "tam_ung_tai_xe")


def _doc(*phan) -> str:
    return io.open(os.path.join(GOC, *phan), encoding="utf-8").read()


def test_tx2_1_hai_loai_chi_co_mat_va_nguoi_xac_nhan_la_giam_doc_doi_xe():
    for loai in HAI_LOAI:
        assert O.CATEGORY_CONFIRMER.get(loai) == ("gd_doi_xe",), (
            f"{loai}: người xác nhận phải là Giám đốc đội xe, đang là {O.CATEGORY_CONFIRMER.get(loai)}")


def test_tx2_2_bon_bang_loai_chi_phai_khop_nhau():
    """`ops.CATEGORY_CONFIRMER` là bảng luật đang chạy. Ba bảng còn lại CHÉP lại nó.

    Lệch một dòng thì hoặc màn hình `/expenses` hiện sai tên người phụ trách, hoặc bảng luồng công
    việc (thứ đem đi ký và đem cho kiểm toán đọc) mô tả một chuỗi chỉ huy không có thật.
    """
    luat = set(O.CATEGORY_CONFIRMER)

    assert set(LV.NGUOI_XAC_NHAN_THEO_LOAI) == luat, (
        "bảng luồng công việc lệch với luật đang chạy: "
        f"thiếu {sorted(luat - set(LV.NGUOI_XAC_NHAN_THEO_LOAI))}, "
        f"thừa {sorted(set(LV.NGUOI_XAC_NHAN_THEO_LOAI) - luat)}")
    for loai, vai in O.CATEGORY_CONFIRMER.items():
        assert LV.NGUOI_XAC_NHAN_THEO_LOAI[loai] == vai, f"{loai}: hai bảng khai hai người xác nhận khác nhau"

    man_hinh = _doc("..", "web", "app", "expenses", "page.tsx")
    for loai in luat:
        assert f"{loai}:" in man_hinh, f"màn hình /expenses chưa biết loại chi “{loai}” – ô loại sẽ hiện trống"


def test_tx2_3_moi_loai_chi_deu_phai_khai_tai_khoan():
    """Chi được mà không lên bảng kê MISA là tiền ra khỏi quỹ mà sổ không có dòng nào.

    BẢN CŨ CHO PHÉP ĐÚNG MỘT Ô TRỐNG, và nó đã làm đúng việc của nó: `sua_chua_xe` cố ý chưa khai
    vì chọn 154 / 642 / 1541 là ba con số lãi lỗ khác nhau, tức là một chữ ký chứ không phải một
    dòng mã. Phép thử giữ cho câu hỏi ấy đếm được, kèm lời dặn "nếu đã chọn thì sửa phép thử này
    kèm lý do".

    Chủ tịch đã chọn 08/10/2026: **627 – Chi phí sản xuất chung**, và **"chi phí sửa xe tháng nào
    tính tháng đó"**. Nên ô trống ấy không còn lý do tồn tại, và phép thử nay đòi KHÔNG CÒN Ô NÀO
    TRỐNG. Để lại ngoại lệ sau khi câu hỏi đã có câu trả lời thì lần tới một loại chi mới quên khai
    sẽ trượt qua đúng cái khe này.
    """
    thieu = MS.thieu_tai_khoan()
    assert MS.CATEGORY_ACCOUNT.get("tam_ung_tai_xe") == "141", (
        "tạm ứng tài xế là tiền giao cho người của công ty – 141, đúng quy ước đã chốt cho tam_ung")
    assert MS.CATEGORY_ACCOUNT.get("sua_chua_xe") == "627", (
        "Chủ tịch quyết 08/10/2026: sửa chữa xe hạch toán 627 – Chi phí sản xuất chung, cuối kỳ kết "
        "chuyển 154. Đổi khỏi 627 thì phải có quyết định mới và sửa phép thử này kèm ngày, người quyết")
    assert thieu == [], f"loại chi chạy được mà chưa khai tài khoản – tiền ra mà sổ không có dòng: {thieu}"


def test_tx2_4_tai_xe_chi_lap_duoc_dung_mot_loai():
    assert O.LOAI_CHI_TAI_XE_TU_LAP == ("tam_ung_tai_xe",)
    assert "sua_chua_xe" not in O.LOAI_CHI_TAI_XE_TU_LAP, (
        "tài xế lập được đề nghị sửa chữa nghĩa là lúc xe vừa hỏng họ phải gõ số tiền và tên garage "
        "mà họ chưa thể biết – đó là bịa số, không phải nhập liệu")
    # Chặn nằm trong HÀM, không chỉ ở cửa API: cửa API nói ai gõ được, hàm nói gõ được cái gì, và
    # chỉ cái sau còn đúng khi mai kia có thêm một cửa khác gọi vào cùng hàm này.
    dv = _doc("app", "services", "ops.py")
    than = dv[dv.index("def create_request("):]
    than = than[:than.index("\ndef ", 1)]
    assert "LOAI_CHI_TAI_XE_TU_LAP" in than, "create_request chưa canh loại chi của tài xế"


def test_tx2_5_mo_cua_cho_tai_xe_khong_duoc_thanh_mo_so_chi_toan_cong_ty():
    """Ba lớp, và phép thử đòi đủ ba. Bỏ lớp nào thì một tài xế đọc được hoặc lập được thứ không phải
    của mình — và không có lớp nào trong ba lớp này tự báo khi nó biến mất."""
    # Lớp 1 – tiền tố API được khai, nên bộ tra cứu ngược đọc được phạm vi của vai này.
    assert "/api/v1/payment-requests" in AC.RESTRICTED_API_PREFIXES["tai_xe"]
    # Lớp 2 – cửa ĐỌC lọc theo người lập.
    cua = _doc("app", "api", "v1", "ops.py")
    than = cua[cua.index('@router.get("/payment-requests")'):]
    than = than[:than.index("\nclass ")]
    assert re.search(r'u\.role in \([^)]*"tai_xe"[^)]*\).*created_by == u\.username', than, re.S), (
        "cửa đọc đề nghị chi chưa lọc theo người lập cho vai tai_xe – một tài xế đăng nhập sẽ đọc "
        "được mọi khoản chi của mọi phòng")
    # Lớp 3 – vai này KHÔNG được thêm màn hình nào. Mở tiền tố API không phải mở menu.
    assert AC.RESTRICTED_ROLE_MENUS["tai_xe"] == ("/xe-hdv", "/doi-mat-khau")
    assert "tai_xe" not in AC.PAYMENT_REQUEST_ROLES, "tai_xe lọt vào nhóm mở màn hình /expenses"


def test_tx2_6_man_hinh_hien_truong_goi_dung_cua_va_khong_tu_dat_luat():
    mh = _doc("..", "web", "app", "xe-hdv", "page.tsx")
    assert '"/payment-requests"' in mh, "màn hình chưa gọi cửa đề nghị chi"
    assert '"tam_ung_tai_xe"' in mh and '"sua_chua_xe"' not in mh, (
        "màn hình của tài xế chỉ được lập tạm ứng; nếu có sua_chua_xe ở đây thì luật ở hai nơi")
    # Màn hình KHÔNG tự tính tuyến ký: không có bảng người duyệt nào viết cứng trong tsx.
    assert "const CONFIRMER" not in mh and "const CAT" not in mh, (
        "màn hình của tài xế tự khai bảng người xác nhận – luật phải nằm ở máy chủ, một chỗ")
    # 06/10/2026 — dòng canh cũ ở đây đòi màn hình NÓI RA rằng chưa có cửa báo hư hỏng. Cửa ấy nay
    # đã có (TX-3), nên lời nhắn kia thành SAI. Đổi thành hai điều còn đúng mãi: cửa phải có mặt, và
    # lời nhắn "chưa có" phải BIẾN MẤT. Một màn hình nói mình thiếu thứ nó đang có là một lời nói dối
    # khó phát hiện hơn im lặng, vì người đọc tin nó.
    assert '"/fleet/bao-hong"' in mh, "màn hình tài xế mất cửa báo hư hỏng"
    assert "chưa có cửa báo hư hỏng" not in mh, (
        "màn hình vẫn nói là chưa có cửa báo hư hỏng, trong khi cửa ấy đã có – lời nhắn cũ phải gỡ "
        "cùng lúc với việc lấp chỗ thiếu")
