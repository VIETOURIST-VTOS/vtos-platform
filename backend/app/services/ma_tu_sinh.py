"""Sinh mã hồ sơ: lấy SỐ LỚN NHẤT đã cấp cho đúng tiền tố ấy, cộng một.

VÌ SAO CÓ TỆP NÀY — ba chỗ hỏng của lối cũ, và cả ba đều có thật trong kho này.

Mười chỗ trong `services/` từng viết cùng một dòng:

    n = db.execute(select(func.count()).select_from(Model)).scalar() + 1
    return f"KN{date.today():%y%m}-{n:03d}"

MỘT · XOÁ MỘT DÒNG LÀ CẤP LẠI MỘT MÃ ĐÃ DÙNG. Đếm cả bảng thì xoá một dòng là số đếm lùi
một bước, và mã kế tiếp trùng với mã đang còn sống. Mọi cột `code` ở đây đều UNIQUE, nên kết
quả là IntegrityError — người dùng thấy màn hình lỗi 500 mà không biết vì sao, và nếu đang nạp
một tệp nhiều dòng thì cả lượt nạp đổ. Đường xoá ấy KHÔNG phải giả định: cửa
`DELETE /import/vietrip/records/user/{id}` cho CNTT gỡ một hồ sơ nhân sự nạp nhầm, và ngay sau
đó mọi lần thêm nhân sự đều đụng mã cho tới khi số đếm đuổi kịp.

HAI · MÃ MANG THÁNG NHƯNG SỐ KHÔNG BAO GIỜ VỀ MỘT. `KN2611-058` đọc như "hồ sơ thứ 58 của
tháng 11", trong khi tháng 11 mới có đúng một hồ sơ — 57 cái kia là của các tháng trước. Con số
ấy in trên giấy gửi khách và trên biên bản, nên nó phải nói đúng điều nó trông như đang nói.

BA · MÃ KHÁC TIỀN TỐ TRONG CÙNG BẢNG LÀM NHẢY SỐ. Bảng `employees` chứa cả `NS0001` do người
lập lẫn `VT0137` do robot Vietrip nạp. Đếm cả bảng thì mỗi lần robot nạp một người là dãy NS
nhảy một quãng, và quãng ấy không ai giải thích được về sau.

CÁCH LÀM Ở ĐÂY. Đọc những mã ĐÃ CÓ mang đúng tiền tố ấy, lấy số lớn nhất, cộng một. Xoá một
dòng không làm lùi số lớn nhất (trừ khi xoá đúng dòng cuối — và khi đó cấp lại số ấy là đúng,
vì không còn ai giữ). Tiền tố chứa tháng thì sang tháng mới là một dãy mới, tự về 001. Tiền tố
khác trong cùng bảng không chạm vào nhau.

CHỖ CÒN HỞ, nói thẳng ra chứ không giấu: hai người bấm tạo trong cùng một khoảnh khắc vẫn có
thể đọc ra cùng một số lớn nhất rồi cùng xin một mã. Cột UNIQUE chặn cái thứ hai lại — vẫn là
một lỗi 500, nhưng là lỗi của một va chạm thật hiếm, không phải lỗi bật ra sau mỗi lần xoá.
Bịt hẳn thì cần một bảng cấp số có khoá dòng, hoặc bắt IntegrityError rồi xin lại mã; cả hai
đều là việc riêng, không gộp vào vòng dọn này.
"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session


def _loc_like(s: str) -> str:
    """Thoát ba ký tự có nghĩa riêng trong LIKE, để tiền tố được so đúng từng chữ.

    `_` trong LIKE khớp MỘT ký tự bất kỳ. Không thoát thì tiền tố `KT2026H1-` cũng vợt luôn mã
    của một kỳ khác chỉ khác đúng một chữ — và hàm trả về một số lớn hơn thật.
    """
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def tiep_theo(db: Session, model, tien_to: str, rong: int, cot: str = "code") -> str:
    """Mã kế tiếp mang `tien_to`, phần số có `rong` chữ số.

    Chỉ đọc những dòng có mã BẮT ĐẦU bằng tiền tố ấy, nên câu hỏi hẹp chứ không quét cả bảng.
    Mã cũ mang tiền tố đúng mà phần đuôi không phải số thuần (`KLE081026_2` chẳng hạn) thì bỏ
    qua — không ném lỗi: một dòng dữ liệu cũ lạ dạng không được quyền chặn người đang lập hồ sơ.
    """
    c = getattr(model, cot)
    mau = re.compile(r"^" + re.escape(tien_to) + r"(\d+)$")
    lon_nhat = 0
    for (ma,) in db.execute(select(c).where(c.like(_loc_like(tien_to) + "%", escape="\\"))).all():
        m = mau.match(str(ma or ""))
        if m:
            lon_nhat = max(lon_nhat, int(m.group(1)))
    return f"{tien_to}{lon_nhat + 1:0{rong}d}"
