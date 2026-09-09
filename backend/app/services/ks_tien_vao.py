"""Hai đường tiền vào phải cùng sống – phép kiểm sinh ra từ một chỗ hỏng có thật (09/9/2026).

Tiền khách nộp vào VTOS theo HAI đường:

  1. WEBHOOK (đẩy)  – SePay gọi sang VTOS ngay khi có giao dịch. Đường chính.
  2. KÉO BÙ (pull)  – VTOS chủ động hỏi lại SePay theo chu kỳ. Đường này tồn tại ĐỂ BẮT giao dịch mà
                      webhook bỏ sót: mạng chập, VTOS đang khởi động lại, SePay gọi trượt.

Chuyện đã xảy ra: token của đường kéo bù được tạo sẵn bên SePay, tác vụ định kỳ n8n gọi 7 phút một
lần cũng dựng xong – nhưng biến SEPAY_API_TOKEN chưa bao giờ được khai trên máy chủ. Nên đường kéo bù
CHƯA TỪNG chạy, và suốt thời gian đó dưới webhook không có lưới đỡ nào.

Không ai thấy gì, vì webhook vẫn chạy tốt. Đó là tính chất của một lớp đỡ: nó vô hình cho tới ngày cần
tới, và ngày cần tới thì đã muộn. Ngày 09/9 việc này lộ ra nhờ bộ đếm lỗi 5xx – tức là lộ ra vì n8n
kêu hộ, không phải vì có ai kiểm "hai đường tiền vào còn đủ cả hai không".

Nên có tệp này. Nguyên tắc nó cài đặt: MỘT LỚP ĐỠ CHƯA CẤU HÌNH LÀ MỘT CHỐT CHẶN ĐANG THIẾU, không
phải một tính năng chưa làm – và vì vậy nó là mức ĐỎ, dù hôm nay chẳng có gì hỏng cả.

Phép kiểm này CỐ TÌNH không gọi ra SePay. Vòng quét robot chạy mỗi phút; gọi ra ngoài mỗi phút là tự
tạo một nguồn hỏng mới và tự làm chậm chính vòng quét. Nó chỉ đọc cấu hình và độ tươi của dữ liệu –
đủ để bắt đúng ca đã xảy ra. Việc gọi thật để thử đường truyền nằm ở màn hình /sepay/status, nơi có
người bấm và có người đọc kết quả.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

# Bao lâu không có đồng nào vào thì đáng hỏi. Công ty lữ hành có tiền vào gần như mọi ngày làm việc;
# hai ngày im lặng là bất thường, nhưng chưa chắc là hỏng (nghỉ lễ), nên VÀNG chứ không ĐỎ.
GIO_IM_LANG = 48


def _cau_hinh():
    from app.core.config import settings
    return {"webhook": bool(getattr(settings, "SEPAY_WEBHOOK_KEY", "")),
            "keo_bu": bool(getattr(settings, "SEPAY_API_TOKEN", ""))}


def bang(db: Session) -> dict:
    from app.models.payments import BankTransaction
    ch = _cau_hinh()
    tong = int(db.execute(select(func.count()).select_from(BankTransaction.__table__)).scalar() or 0)
    moi = db.execute(select(BankTransaction).order_by(desc(BankTransaction.transaction_date)).limit(1)).scalars().first()
    gio_im = None
    if moi is not None and moi.transaction_date:
        gio_im = round((datetime.now() - moi.transaction_date).total_seconds() / 3600, 1)
    return {"duong_webhook_da_khai": ch["webhook"], "duong_keo_bu_da_khai": ch["keo_bu"],
            "so_giao_dich": tong, "gio_ke_tu_giao_dich_gan_nhat": gio_im,
            "nguong_im_lang_gio": GIO_IM_LANG}


def quet(db: Session) -> list[dict]:
    b = bang(db)
    ra = []
    if not b["duong_webhook_da_khai"]:
        ra.append({"ma": "tien_vao#webhook_chua_khai", "loai": "tien_vao_thieu_duong", "muc": "do",
                   "phong_ban": "Kế toán", "vai_tro": "ketoan", "doi_tuong": "sepay_webhook",
                   "tom_tat": "Đường webhook nhận tiền vào CHƯA khai khoá (SEPAY_WEBHOOK_KEY). Đây là "
                              "đường chính – không có nó thì giao dịch khách nộp không tự vào sổ",
                   "chi_tiet": b})
    if not b["duong_keo_bu_da_khai"]:
        ra.append({"ma": "tien_vao#keo_bu_chua_khai", "loai": "tien_vao_thieu_duong", "muc": "do",
                   "phong_ban": "Kế toán", "vai_tro": "ketoan", "doi_tuong": "sepay_keo_bu",
                   "tom_tat": "Đường KÉO BÙ chưa khai khoá (SEPAY_API_TOKEN). Webhook có thể vẫn chạy "
                              "tốt, nhưng dưới nó KHÔNG CÓ LƯỚI ĐỠ: giao dịch nào webhook bỏ sót thì "
                              "không có gì bắt lại. Một lớp đỡ chưa cấu hình là một chốt chặn đang "
                              "thiếu, không phải một tính năng chưa làm",
                   "chi_tiet": b})
    g = b["gio_ke_tu_giao_dich_gan_nhat"]
    if b["so_giao_dich"] and g is not None and g > GIO_IM_LANG:
        ra.append({"ma": "tien_vao#im_lang", "loai": "tien_vao_im_lang", "muc": "vang",
                   "phong_ban": "Kế toán", "vai_tro": "ketoan", "doi_tuong": "sepay",
                   "tom_tat": f"Đã {g:.0f} giờ không có giao dịch tiền vào nào. Có thể là kỳ nghỉ, "
                              f"cũng có thể là đường nhận tiền đã đứt mà không ai báo",
                   "chi_tiet": b})
    return ra


def _hai_duong_tien_vao(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot."""
    return quet(db)
