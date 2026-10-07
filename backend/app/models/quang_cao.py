"""DẤU NGUỒN QUẢNG CÁO – một bảng cho mọi kênh.

VÌ SAO BẢNG NÀY RA ĐỜI
══════════════════════════════════════════════════════════════════════════════════════════════
Báo cáo Marketing tháng 9/2026 (Ngọc Tuấn, 06/10) đo được 719 trên 931 booking. Phần còn lại –
212 booking, 5.484.557.709 đ, 39,5% doanh thu tháng – không gắn được kênh nào. Riêng Google Ads
báo cáo tự khai "chỉ đo được ~50%: khách qua các kênh CRM hoặc gọi hotline nên không đo lường
được". Hotline là kênh doanh thu lớn thứ hai toàn công ty (51 booking, 1,826 tỷ) và là kênh
KHÔNG có một dấu vết tự động nào.

Nguyên nhân kỹ thuật, đã quét cả kho ngày 07/10/2026: VTOS không lưu `gclid`, `fbclid`,
`ttclid`, `leadgen_id` hay một cột `utm_` nào – không ở `leads`, không ở đâu khác. Bảng `leads`
có `campaign` (ô chữ tự do) và `campaign_id` (trỏ chiến dịch nội bộ); cả hai do NGƯỜI gõ, không
phải do nền tảng quảng cáo gắn vào.

Mã click của Google chỉ tồn tại đúng giây khách bấm quảng cáo. Không ai bắt lấy nó lúc ấy thì
nó mất vĩnh viễn – không truy hồi được bằng bất cứ cách nào. Mỗi ngày chậm là một ngày dữ liệu
không lấy lại được, và đó là lý do bảng này đi trước mọi màn hình báo cáo.

BỐN CHỐT CỦA BẢNG NÀY
══════════════════════════════════════════════════════════════════════════════════════════════
1. GHI SỰ THẬT, KHÔNG QUY KẾT. Bảng này chỉ ghi "lúc X, qua nền tảng Y, có một lần chạm mang mã
   Z". Câu "booking này tính doanh thu cho kênh nào" là DIỄN GIẢI, có luật riêng và luật ấy sẽ
   đổi – để nó ở vòng sau, trong một bảng khác có số phiên bản. Trộn hai thứ vào đây thì mỗi lần
   đổi luật quy kết là một lần phải sửa dữ liệu gốc, và sau ba lần sửa không ai còn biết sự thật
   ban đầu là gì.

2. NHIỀU DÒNG CHO MỘT KHÁCH, KHÔNG PHẢI MỘT CỘT. Báo cáo tháng 9 ghi thẳng: "Khách cũng qua:
   vChat 11 · Appier 11 · Hotline 3 · Web 2". Một khách chạm nhiều điểm trước khi đặt tour. Một
   cột trên bảng lead chỉ giữ được một điểm, và giữ cái nào thì cũng là đã quy kết mất rồi –
   xem chốt 1.

3. DANH SÁCH NỀN TẢNG LÀ GỢI Ý, KHÔNG PHẢI HÀNG RÀO. Báo cáo tháng 9 có Appier, GetResponse,
   vChat, Zalo Mini App, Livestream và một sự kiện khuyến mãi – sáu nguồn không ai liệt kê
   trước được. Khoá cứng danh sách là buộc người nhập chọn "khác" cho một nửa dữ liệu, và cột
   "khác" thì không báo cáo được gì.

4. GIỮ NGUYÊN VĂN GÓI TIN. Cùng lập luận đã ghi ở `TongDaiSuKien`: chưa ai nhìn thấy gói tin
   thật mà Facebook, Google hay tổng đài gửi cho Vietourist. Diễn giải trước khi nhìn là đoán,
   và đoán sai thì hỏng LẶNG LẼ – cửa vẫn trả 200, nền tảng vẫn báo thành công, VTOS ghi rỗng.
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Gợi ý, không phải hàng rào – xem chốt 3 ở đầu tệp. Cửa nhận KHÔNG từ chối giá trị lạ; nó chỉ
# cắt độ dài và ghi thường hoá.
NEN_TANG_QUEN = {
    "google": "Google", "facebook": "Facebook", "tiktok": "TikTok", "zalo": "Zalo",
    "web": "Website Vietourist", "tong_dai": "Tổng đài", "appier": "Appier",
    "getresponse": "GetResponse", "vchat": "vChat", "su_kien": "Sự kiện / khuyến mãi",
    "khac": "Khác",
}

# Loại mã quyết định ghép ngược bằng đường nào khi đẩy chuyển đổi về nền tảng:
#   gclid        – mã click Google, đi trên đường dẫn khi khách bấm quảng cáo vào web
#   so_chuyen_tiep – cuộc gọi qua số chuyển tiếp của Google; ghép bằng số khách + giờ gọi, và
#                  CHỈ ghép được nếu tài khoản quảng cáo đã bật số chuyển tiếp từ trước
#   leadgen_id   – mã lead của biểu mẫu Facebook / TikTok, chính xác tới từng mẫu quảng cáo
#   ad_referral  – khách bấm quảng cáo click-to-Messenger; webhook mang `ref` và `ad_id`
#   ttclid       – mã click TikTok
#   zalo_uid     – khách quan tâm hoặc nhắn tin Zalo OA
#   ma_khuyen_mai – mã giảm giá. Tháng 9 có 56 mã DHT9 khớp đúng danh sách booking: đây là cách
#                  đo kênh KHÔNG cần công nghệ gì, và nó đã chạy thật rồi
#   khac         – còn lại
LOAI_MA_QUEN = {
    "gclid": "Mã click Google", "so_chuyen_tiep": "Cuộc gọi qua số chuyển tiếp Google",
    "leadgen_id": "Mã lead biểu mẫu", "ad_referral": "Khách bấm quảng cáo nhắn tin",
    "ttclid": "Mã click TikTok", "zalo_uid": "Tài khoản Zalo", "ma_khuyen_mai": "Mã khuyến mãi",
    "khac": "Khác",
}

NGUON_GHI = {
    "web": "Phần máy chủ của website", "webhook_fb": "Webhook Facebook",
    "webhook_zalo": "Webhook Zalo OA", "tong_dai": "Tổng đài", "nap_tep": "Nạp tệp",
    "nhap_tay": "Nhập tay", "khac": "Khác",
}


class DauQuangCao(Base):
    """Một LẦN CHẠM giữa khách và một kênh quảng cáo."""
    __tablename__ = "dau_quang_cao"
    id: Mapped[int] = mapped_column(primary_key=True)

    nen_tang: Mapped[str] = mapped_column(String(24), index=True)
    loai_ma: Mapped[str] = mapped_column(String(24), index=True)
    # Giá trị mã do nền tảng cấp. RỖNG được: một cuộc gọi vào hotline thường không có mã nào cả,
    # và từ chối ghi nó là quay lại đúng chỗ mù mà bảng này sinh ra để vá.
    ma: Mapped[str] = mapped_column(String(200), default="", index=True)

    # Khoá chống trùng, do `services/dau_quang_cao.khoa()` tính – KHÔNG nhận từ người gọi.
    #
    # Vì sao không đặt ràng buộc duy nhất thẳng lên (nen_tang, loai_ma, ma): `ma` rỗng là hợp lệ
    # (xem ngay trên), và một ràng buộc như thế sẽ cho phép ĐÚNG MỘT dòng không mã cho mỗi nền
    # tảng – tức là cuộc gọi thứ hai vào hotline bị cơ sở dữ liệu từ chối. Có mã thì khoá là mã;
    # không mã thì khoá ghép từ số điện thoại và PHÚT chạm, nên hai cuộc gọi khác phút là hai
    # dòng, còn webhook gửi lại cùng một cuộc thì không nhân đôi.
    khoa_chong_trung: Mapped[str] = mapped_column(String(160), unique=True, index=True)

    # Mã chiến dịch / nhóm quảng cáo / mẫu quảng cáo CỦA NỀN TẢNG – không phải mã chiến dịch nội
    # bộ ở bảng `campaigns`. Hai thứ khác nhau và sẽ còn khác nhau: một chiến dịch nội bộ có thể
    # chạy bằng nhiều mẫu trên nhiều nền tảng.
    ma_chien_dich: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ma_nhom_qc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ma_mau_qc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ten_chien_dich: Mapped[str] = mapped_column(String(200), default="")

    sdt: Mapped[str] = mapped_column(String(20), default="", index=True)
    zalo_uid: Mapped[str] = mapped_column(String(40), default="", index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)

    # Năm tham số utm của đường dẫn web, giữ nguyên tên gốc trong một ô JSON thay vì năm cột:
    # utm là chuẩn mở, ai cũng thêm được tham số thứ sáu, và năm cột thì cái thứ sáu rơi mất.
    utm: Mapped[dict] = mapped_column(JSON, default=dict)
    trang_dich: Mapped[str] = mapped_column(String(500), default="")
    trang_gioi_thieu: Mapped[str] = mapped_column(String(500), default="")

    # `cham_luc` là lúc khách chạm, theo nền tảng báo. `nhan_luc` là lúc VTOS ghi. Hai thời điểm
    # này lệch nhau – webhook chậm, tệp nạp muộn – và gộp làm một thì mọi phép tính theo mốc 30 /
    # 60 / 90 ngày đều lệch theo. Google đòi đúng `call_start_date_time` khi đẩy chuyển đổi cuộc
    # gọi, nên đây là cột bắt buộc có thật, không phải cột cho đẹp.
    cham_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    nhan_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    nguon_ghi: Mapped[str] = mapped_column(String(24), default="khac", index=True)
    than_nguyen_van: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")
