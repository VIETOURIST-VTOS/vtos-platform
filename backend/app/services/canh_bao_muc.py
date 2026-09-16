# -*- coding: utf-8 -*-
"""TC-42 · TỒN ĐỌNG CẦN XỬ LÝ, TÁCH THEO BA MỨC ĐỘ.

Anh Tuấn 16/9/2026 chốt ô "Tồn đọng cần xử lý" thành một trong sáu ô lớn, và chọn chiều vẽ là
MỨC ĐỘ: nghiêm trọng · cảnh báo · theo dõi.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO MỘT CON SỐ KHÔNG THÀNH BIỂU ĐỒ ĐƯỢC — VÀ VÌ SAO ĐIỀU ĐÓ QUAN TRỌNG
═══════════════════════════════════════════════════════════════════════════════════════════════
Trước vòng này màn hình có đúng một con số: `canh_bao_do` — số cảnh báo mức đỏ chưa xử lý. Trên
bản chạy thật nó là 1483, và 1483 nằm một mình thì không nói được điều gì để hành động: không biết
nó đang tăng hay giảm, không biết bao nhiêu phần là việc phải làm ngay.

Tách theo mức độ trả lời được vế thứ hai ngay hôm nay, KHÔNG cần chờ bản lưu kỳ nào tích luỹ —
`Alert.level` đã có sẵn trong sổ từ đầu. Đó là lý do chọn chiều này trước chiều thời gian.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA MỨC LÀ MỘT DANH SÁCH ĐÓNG, VÀ MỨC LẠ KHÔNG ĐƯỢC ÂM THẦM BIẾN MẤT
═══════════════════════════════════════════════════════════════════════════════════════════════
`Alert.level` là cột chuỗi, nên một robot mới viết sai chính tả mức là sinh ra một mức thứ tư mà
không có gì kêu lên. Nếu hàm này chỉ đếm ba mức đã biết thì những dòng ấy rơi khỏi cả biểu đồ lẫn
tổng — và tổng trên màn hình sẽ NHỎ HƠN số việc thật, đúng kiểu sai không ai nhìn ra.

Nên: mức lạ được gom vào một nhóm "chưa phân loại" hiện NGAY trên màn hình. Một nhóm chưa phân
loại có người nhìn thấy thì trong tuần sẽ có người đi sửa; một nhóm bị bỏ qua thì không.

═══════════════════════════════════════════════════════════════════════════════════════════════
CHỈ ĐẾM VIỆC CHƯA XỬ LÝ
═══════════════════════════════════════════════════════════════════════════════════════════════
`resolved == False`. Đếm cả việc đã xử lý là biến ô "cần xử lý" thành ô "đã từng có", và con số ấy
chỉ tăng chứ không bao giờ giảm — nhìn vào không ai biết hôm nay còn nợ bao nhiêu.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.core import Alert

# Thứ tự ở đây là thứ tự hiện trên biểu đồ: nặng nhất đứng trước. Đổi thứ tự là đổi điều người đọc
# nhìn thấy trước tiên, nên nó là một quyết định chứ không phải một chi tiết.
MUC = (
    ("red", "Nghiêm trọng"),
    ("warn", "Cảnh báo"),
    ("info", "Theo dõi"),
)
MA_MUC = tuple(m for m, _ in MUC)

CHUA_PHAN_LOAI = "chua_phan_loai"
TEN_CHUA_PHAN_LOAI = "Chưa phân loại"


def theo_muc(db: Session) -> dict:
    """Số việc CHƯA XỬ LÝ theo từng mức độ, cộng nhóm mức lạ nếu có.

    Trả về:
        {"tong": int,
         "phan": [{"ma", "ten", "so", "trang_thai"}],   # đúng thứ tự MUC, mức lạ đứng cuối
         "co_muc_la": bool}

    `trang_thai=True` đánh dấu nhóm mang màu cảnh báo trên biểu đồ — chỉ mức đỏ, vì nó là TRẠNG
    THÁI (việc đã thành vấn đề) chứ không phải một nấc của thang mức độ. Cùng quy ước với nhóm
    "Quá hạn" trong biểu đồ phải thu (TC-38).
    """
    rows = db.execute(
        select(Alert.level, func.count()).where(Alert.resolved == False)  # noqa: E712
        .group_by(Alert.level)
    ).all()
    dem = {str(r[0] or ""): int(r[1]) for r in rows}

    phan = [{"ma": ma, "ten": ten, "so": dem.get(ma, 0), "trang_thai": ma == "red"}
            for ma, ten in MUC]
    la = sum(v for k, v in dem.items() if k not in MA_MUC)
    if la:
        phan.append({"ma": CHUA_PHAN_LOAI, "ten": TEN_CHUA_PHAN_LOAI, "so": la,
                     "trang_thai": False})
    return {"tong": sum(v for v in dem.values()),
            "phan": phan,
            "co_muc_la": bool(la)}
