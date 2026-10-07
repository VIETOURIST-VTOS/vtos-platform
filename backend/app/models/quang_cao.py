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
from app.models.kieu_tien import TIEN

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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HÀNG ĐỢI ĐẨY CHUYỂN ĐỔI NGƯỢC VỀ NỀN TẢNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Bắt được cái chạm mới là nửa việc. Nửa còn lại: khi khách ấy CHỐT TOUR, phải nói ngược lại cho
# nền tảng biết, kèm DOANH THU THẬT. Không nói thì Google và Facebook chỉ học được "có người điền
# form" và sẽ rất giỏi trong việc mua thêm người điền form — đúng loại khách rẻ nhất và không chốt.
#
# VÌ SAO LÀ HÀNG ĐỢI, KHÔNG PHẢI GỌI THẲNG LÚC CHỐT. Ba lý do, lý do thứ ba là lý do thật:
#   1. Nền tảng có lúc lỗi, có hạn số lần gọi, và có cửa sổ thời gian nhận chuyển đổi.
#   2. Gọi mạng ngay trong luồng chốt tour là cho một dịch vụ bên ngoài quyền làm chậm việc bán hàng.
#   3. HÔM NAY CHƯA CÓ TOKEN của nền tảng nào. Không có hàng đợi thì mọi chuyển đổi phát sinh từ
#      giờ tới lúc CNTT dán token đều mất trắng — đúng cái sai mà cả hai vòng này sinh ra để chặn.

CD_TRANG_THAI = {
    "cho_gui": "Chờ gửi",
    "da_gui": "Đã gửi",
    "loi": "Gửi lỗi",
    "thieu_doanh_thu": "Thiếu doanh thu – chưa gửi",
    "bo_qua": "Bỏ qua",
    # Meta chi nhan event_time trong 7 ngay ke tu luc chot. Qua han thi gui di cung bi tu
    # choi, nen danh dau va DUNG - gui de bi tu choi chi to lam ban bang loi va che mat loi
    # that. Dem duoc so dong o day la dem duoc so tien da mat co hoi quy cong tu dong.
    "qua_han": "Quá hạn nền tảng – không gửi được nữa",
}


class ChuyenDoiGuiDi(Base):
    """Một chuyển đổi cần báo cho MỘT nền tảng.

    MỘT LẦN CHỐT SINH NHIỀU DÒNG, MỖI NỀN TẢNG MỘT DÒNG, VÀ MỖI DÒNG MANG DOANH THU ĐẦY ĐỦ —
    không chia. Điều này trông như đếm trùng, nên phải nói cho rõ vì sao nó đúng:

    Mỗi nền tảng tự quy kết theo mô hình của riêng nó, trên dữ liệu của riêng nó. Gửi cho Google
    một phần ba doanh thu vì khách còn chạm Facebook và hotline thì Google sẽ tối ưu theo một con
    số không phải giá trị thật của khách ấy, và nó sẽ ra giá thầu thấp hơn giá trị thật. Cách các
    nền tảng được thiết kế là mỗi bên nhận giá trị ĐẦY ĐỦ của chuyển đổi mà nó dự phần.

    HỆ QUẢ PHẢI IN RA MÀN HÌNH, KHÔNG ĐƯỢC ĐỂ AI TỰ PHÁT HIỆN: tổng doanh thu báo lên ba nền tảng
    CÓ THỂ LỚN HƠN doanh thu thật của công ty, và điều đó không phải lỗi. Ba con số ấy KHÔNG ĐƯỢC
    CỘNG LẠI. Câu "tháng này kênh nào mang về bao nhiêu tiền" là câu hỏi QUY KẾT — nó có luật
    riêng, có số phiên bản, và thuộc một bảng khác chưa dựng. Báo cáo tháng 9/2026 đang trả lời
    câu ấy bằng tay, với mười một dòng "đã loại trùng" và một quy tắc không ghi ở đâu cả.

    DOANH THU ĐỌC TỪ BOOKING, KHÔNG AI GÕ. Và `amount` rỗng thì dòng nằm ở "thiếu doanh thu" chứ
    KHÔNG gửi đi với số 0: gửi 0 là dạy nền tảng rằng khách ấy vô giá trị, tệ hơn hẳn việc im lặng.
    """
    __tablename__ = "chuyen_doi_gui_di"
    id: Mapped[int] = mapped_column(primary_key=True)
    dau_id: Mapped[int] = mapped_column(ForeignKey("dau_quang_cao.id"), index=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True, index=True)
    # Chép từ dấu để truy vấn và lọc không phải nối bảng. Nguồn thật vẫn là `dau_id`.
    nen_tang: Mapped[str] = mapped_column(String(24), index=True)
    loai_ma: Mapped[str] = mapped_column(String(24))
    ma: Mapped[str] = mapped_column(String(200), default="")

    ma_booking: Mapped[str] = mapped_column(String(40), index=True)
    # RỖNG = chưa đọc được từ booking, KHÁC HẲN 0 đồng. Xem docstring.
    doanh_thu: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str] = mapped_column(String(3), default="VND")
    chot_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    trang_thai: Mapped[str] = mapped_column(String(20), default="cho_gui", index=True)
    lan_thu: Mapped[int] = mapped_column(Integer, default=0)
    loi_cuoi: Mapped[str] = mapped_column(Text, default="")
    gui_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Nền tảng trả về gì thì giữ nguyên văn – cùng lập luận với `than_nguyen_van` ở bảng dấu.
    tra_loi: Mapped[str] = mapped_column(Text, default="")

    # Khoá = nền tảng + booking + dấu. Chạy lại lượt sinh không nhân đôi; một booking chạm hai mẫu
    # quảng cáo CÙNG nền tảng thì vẫn là hai dòng, vì hai mẫu ấy cần hai lời báo riêng.
    khoa_chong_trung: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
