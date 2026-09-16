# -*- coding: utf-8 -*-
"""TC-43 · MỘT LỊCH DUY NHẤT: hôm nay phải chụp những kỳ nào?

Anh Tuấn 16/9/2026 hỏi có dùng Google Calendar thay n8n được không, rồi chốt giữ n8n. Nhưng câu
hỏi ấy làm lộ ra một chỗ yếu thật sự của thiết kế cũ, và vòng này chữa chỗ ấy.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO BA LỊCH LÀ BA CHỖ CÓ THỂ GÕ SAI
═══════════════════════════════════════════════════════════════════════════════════════════════
Bản TC-39 để lịch tự truyền ngày vào, và chú thích của chính nó đã cảnh báo vì sao:

    "Chạy lúc 00:30 ngày 1 mà không truyền ngày thì `khoang('thang')` trả về THÁNG MỚI — tức là
     chụp một tháng mới đi được nửa tiếng, rồi ghi đè lên đúng ô đáng ra phải chứa tháng vừa đóng.
     Một dòng cấu hình lịch sai chỗ này là hỏng vĩnh viễn số liệu của kỳ ấy."

Cảnh báo ấy đúng, và đó chính là vấn đề: nó đặt phần DỄ SAI NHẤT vào một ô cấu hình ngoài kho mã —
nơi không có bộ kiểm nào canh, không có ai soát lại, và sai thì im lặng. Ba lịch là ba ô như thế,
mỗi ô mang một biểu thức ngày riêng.

Nên vòng này đảo lại: lịch chỉ còn phải biết MỘT việc — gọi mỗi ngày một lần. Việc "hôm nay là kỳ
gì, và mốc là ngày nào" chuyển vào đây, nơi nó kiểm được bằng máy.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA LUẬT, VÀ CẢ BA ĐỀU SINH RA TỪ MỘT CÂU: KỲ PHẢI ĐÃ ĐÓNG
═══════════════════════════════════════════════════════════════════════════════════════════════
1 · MỐC LUÔN LÀ HÔM QUA, không bao giờ là hôm nay. Chụp lúc 00:30 ngày 1/10 là chụp cho THÁNG 9,
    và ngày cuối tháng 9 là 30/9 — tức hôm qua. Lấy hôm nay là dán nhãn tháng 9 lên con số của
    tháng 10 khi nó mới đi được nửa tiếng.

2 · TUẦN CHỤP VÀO THỨ HAI, vì tuần vừa đóng kết thúc Chủ nhật — tức hôm qua.

3 · THÁNG CHỤP VÀO NGÀY 1, vì tháng vừa đóng kết thúc ngày cuối tháng trước — tức hôm qua.

Cả ba dùng CHUNG một mốc "hôm qua", nên không có chỗ nào để lệch nhau. Đó là điều bản ba lịch
không bảo đảm được: ba biểu thức ngày viết tay ở ba ô khác nhau.

═══════════════════════════════════════════════════════════════════════════════════════════════
NGÀY 1 RƠI ĐÚNG THỨ HAI THÌ CHỤP CẢ BA — KHÔNG PHẢI CHỌN MỘT
═══════════════════════════════════════════════════════════════════════════════════════════════
Ba kỳ là ba câu hỏi khác nhau về cùng một ngày cuối, không phải ba mức của một thang. Bỏ bớt kỳ
nào trong hôm ấy là mất kỳ ấy vĩnh viễn — chỉ tiêu tồn kho không tính lại được.
"""
from datetime import date, timedelta

# Khoá kỳ đúng như `bao_cao_phong.TEN_KY` dùng. Không khai lại tên tiếng Việt ở đây: một cái tên
# nằm hai chỗ là hai chỗ sớm muộn nói khác nhau.
KY_NGAY = "ngay"
KY_TUAN = "tuan"
KY_THANG = "thang"

THU_HAI = 0        # date.weekday(): thứ Hai = 0


def ky_den_han(hom_nay: date | None = None) -> list[tuple[str, date]]:
    """Hôm nay phải chụp những kỳ nào, và mốc của mỗi kỳ là ngày nào.

    Trả về danh sách (kind, moc) — `moc` là NGÀY CUỐI của kỳ cần chụp, luôn là hôm qua.
    Thứ tự: ngày → tuần → tháng, tức hẹp trước rộng sau. Thứ tự này không đổi kết quả nhưng làm
    nhật ký đọc được: một dòng "ngay, tuan, thang" nói ngay rằng hôm ấy là mùng 1 thứ Hai.
    """
    hom_nay = hom_nay or date.today()
    hom_qua = hom_nay - timedelta(days=1)

    ra: list[tuple[str, date]] = [(KY_NGAY, hom_qua)]
    if hom_nay.weekday() == THU_HAI:
        ra.append((KY_TUAN, hom_qua))
    if hom_nay.day == 1:
        ra.append((KY_THANG, hom_qua))
    return ra


def mo_ta(hom_nay: date | None = None) -> str:
    """Câu giải thích cho nhật ký và cho màn hình Tự động hoá — vì sao hôm nay chụp chừng ấy kỳ."""
    hom_nay = hom_nay or date.today()
    ds = ky_den_han(hom_nay)
    ly_do = ["kỳ ngày chụp mỗi ngày"]
    if hom_nay.weekday() == THU_HAI:
        ly_do.append("hôm nay là thứ Hai nên chụp thêm kỳ tuần")
    if hom_nay.day == 1:
        ly_do.append("hôm nay là ngày 1 nên chụp thêm kỳ tháng")
    return f"{len(ds)} kỳ đến hạn ({' · '.join(ly_do)}); mốc của cả {len(ds)} là hôm qua."
