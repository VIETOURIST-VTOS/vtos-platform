"""CRM nhẹ: lead theo kênh (Hotline, VCHAT, Web, Tiktok Ads, Livestream, Appier, Zalo OA…), thống kê lead theo kênh × tháng,
tin nhắn Zalo (OA / ZNS) gửi cho lead – khách; đối chiếu lead ↔ booking để tính tỷ lệ chốt, khách mới / quay lại."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON, UniqueConstraint  # noqa: F401
from sqlalchemy import Index as sa_Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

LEAD_CHANNELS = ["Hotline 1", "Hotline 2", "Đặt tour web", "VCHAT", "Tiktok Ads", "Livestream", "Appier", "Zalo OA", "Facebook", "Khách cũ", "Khác"]
LEAD_STATUS = {"moi": "Mới", "dang_cham_soc": "Đang chăm sóc", "chot": "Đã chốt tour", "mat": "Không chốt"}


class Lead(Base):
    __tablename__ = "leads"
    # V10 – kiểm phiên bản: tăng sau mỗi lần sửa, người gọi gửi kèm bản mình đang cầm.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    # ── SỬA CỦA LÀN PHÂN QUYỀN, 14/9/2026 – có động tới tệp của làn khác, nói rõ ở đây ─────
    # Ràng buộc cũ: UniqueConstraint("phone", "lead_month", "channel").
    # Nó BUỘC mỗi khách chỉ có MỘT dòng cho mỗi kỳ mỗi kênh. Hệ quả không nhìn thấy trên màn hình:
    # khách gọi hotline ngày 3 rồi gọi lại ngày 20 cùng tháng thì lần thứ hai KHÔNG lưu được – cơ
    # sở dữ liệu từ chối, và cửa nhập buộc phải ghi đè lên lần thứ nhất. Một lần liên hệ có thật
    # biến mất, không dòng nhật ký nào ghi lại.
    #
    # Đây không phải suy đoán. Phép thử `test_nguoi_XAC_NHAN_la_lan_lien_he_khac_thi_moi_ghi_them`
    # và `test_ma_lead_do_HE_THONG_cap_va_KHONG_trung_nhau` đều đỏ với chính lỗi
    # "UNIQUE constraint failed: leads.phone, leads.lead_month, leads.channel" trước khi sửa dòng
    # này. Góp ý độc lập ngày 13/9 mục 3 đòi "một khách có thể có nhiều nhu cầu" – đòi hỏi ấy
    # KHÔNG thực hiện được chừng nào ràng buộc này còn.
    #
    # Thay bằng: `ma_lead` duy nhất (mỗi LẦN phát sinh nhu cầu một mã) + chỉ mục thường trên bộ ba
    # cũ để các truy vấn đang chạy không chậm đi.
    #
    # CẦN MỘT BẢN NÂNG CẤP CƠ SỞ DỮ LIỆU để gỡ ràng buộc trên máy chủ thật – xem bản nháp
    # `NHAP_migration_marketing.py` trong gói bàn giao. Mạch nâng cấp đo ngày 14/9/2026 chỉ còn
    # MỘT đầu (a3d71e9c54b28) nên viết được ngay; nhưng CHỈ làn nhận việc này được commit nó,
    # hai làn cùng thêm một bản là hai đầu mạch và máy chủ không khởi động được.
    __table_args__ = (sa_Index("ix_lead_phone_month_channel", "phone", "lead_month", "channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)                 # chuẩn hóa 0xxxxxxxxx
    name: Mapped[str] = mapped_column(String(120), default="")
    channel: Mapped[str] = mapped_column(String(40), index=True)
    lead_month: Mapped[str] = mapped_column(String(7), index=True)             # YYYY-MM tháng phát sinh lead
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    campaign: Mapped[str] = mapped_column(String(80), default="")            # ô chữ cũ – giữ nguyên để không mất dữ liệu đã nhập
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    interest: Mapped[str] = mapped_column(String(200), default="")             # tour quan tâm
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="moi")
    note: Mapped[str] = mapped_column(Text, default="")
    zalo_uid: Mapped[str] = mapped_column(String(40), default="")               # user_id Zalo OA (khi khách quan tâm OA)
    zalo_follow: Mapped[bool] = mapped_column(Boolean, default=False)
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)       # booking chốt (đối chiếu theo SĐT)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


    # ── MKT-2 · năm cột của cửa nhập Marketing (13/9/2026) ────────────────────────────────
    # Tất cả NULLABLE và không có giá trị mặc định: dòng cũ chưa có dữ liệu này, và rỗng ở đây
    # nghĩa là CHƯA AI HỎI, không phải "không có". Đặt mặc định là biến một ô chưa hỏi thành một
    # câu trả lời, rồi báo cáo cộng nó vào như số thật.
    #
    # `channel` cũ GIỮ NGUYÊN, không bỏ: dữ liệu đã nhập nằm ở đó. Từ nay `diem_tiep_nhan` là ô
    # được hỏi, còn `channel` là bản sao để mã cũ đọc tiếp – bỏ cột cũ là làm hỏng mọi báo cáo
    # đang chạy trong cùng một lần sửa.
    nguon_thu_hut: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    diem_tiep_nhan: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    mang: Mapped[str | None] = mapped_column(String(6), nullable=True)          # le / mice
    giao_luc: Mapped[date | None] = mapped_column(Date, nullable=True)
    han_xu_ly: Mapped[date | None] = mapped_column(Date, nullable=True)
    ly_do_mat: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── MKT-3 · các cột thêm sau góp ý độc lập ngày 13/9/2026 ────────────────────────────
    # Góp ý mục 3 đòi "mã lần phát sinh nhu cầu", đòi giữ NGÀY GIỜ thật thay vì chỉ tháng, và đòi
    # nối chuyển đổi tới booking bằng MÃ chứ không bằng chữ tự do.
    #
    # VÌ SAO PHẢI CÓ MÃ CHO MỘT LẦN PHÁT SINH NHU CẦU
    # Một người có thể hỏi nhiều lần, và mỗi lần là một nghiệp vụ riêng. Không có mã thì mọi phép
    # đếm phải đoán từ số điện thoại, và đoán kiểu nào cũng sai một trong hai chiều: gộp thì mất
    # một lần liên hệ có thật, không gộp thì một chuyến đi bị đếm hai lần vì khách vào từ hai kênh.
    #
    # KHÔNG CÓ MÃ KHÁCH – chốt của Chủ tịch 14/9/2026
    # Hệ thống KHÔNG cấp mã khách. Người nhập chỉ nhập MÃ TOUR. Đơn vị "một người" khi báo cáo vì
    # thế lấy theo SỐ ĐIỆN THOẠI đã chuẩn hoá, và điều đó mang hai sai số phải nói ra chứ không
    # được giấu: hai người dùng chung một số thì đếm thành một; một người đổi số thì đếm thành hai.
    # Báo cáo gọi con số ấy là "số điện thoại khác nhau", KHÔNG gọi là "số khách đã xác minh".
    ma_lead: Mapped[str | None] = mapped_column(String(24), nullable=True, unique=True, index=True)
    # Mã tour do Điều hành/Kinh doanh cấp. Ô MÃ, người nhập chọn từ danh mục tour – không phải ô
    # chữ tự do. `interest` cũ giữ nguyên cho dữ liệu đã nhập, nhưng phép đếm dùng mã này: chữ tự
    # do thì "Nha Trang 3N" và "nha trang 3 ngày" thành hai tour khác nhau.
    ma_tour: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # Ngày GIỜ nhu cầu phát sinh ở nguồn, không phải lúc nhập tệp. Chỉ có tháng thì không tính
    # được mốc 30/60/90 ngày; lấy ngày nhập thay ngày phát sinh thì mọi lead nhập muộn trở thành
    # "chốt nhanh", và hiệu quả kênh nào nhập tệp trễ nhất trông đẹp nhất.
    phat_sinh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    # Mã booking do Kinh doanh/Vietrip cấp. Ô MÃ, không phải ô tiền: doanh thu đọc từ booking theo
    # mã này, Marketing không gõ lại số tiền. `booking_id` cũ giữ nguyên cho mã đang chạy.
    ma_booking: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    # Dấu của dòng nguồn đã nhập, để nhập lại cùng một tệp không sinh thêm lead. KHÔNG unique:
    # hai lần liên hệ thật có thể trùng dấu, và khi ấy hệ thống phải hỏi người chứ không chặn.
    dau_van_tay: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)


class LeadBanGiao(Base):
    """Lịch sử giao – nhận – giao lại – đổi hạn của một lead. Bảng riêng, không phải hai cột.

    Góp ý mục 3 đòi "ghi tự động thời điểm thao tác; hạn theo quy tắc có phiên bản". Hai cột
    `giao_luc` / `han_xu_ly` trên bảng lead không làm được việc ấy: chúng chỉ giữ được TRẠNG THÁI
    HIỆN TẠI. Lead giao cho người A, A không gọi, giao lại người B – sau khi ghi đè thì trên hệ
    thống không còn dấu vết nào cho thấy A từng cầm nó. Đến lúc hỏi "vì sao lead này mất", câu trả
    lời đã bị chính hệ thống xoá.

    `phien_ban_quy_tac` giữ tên bản quy tắc đã dùng để đặt hạn. Quy tắc hạn xử lý sẽ đổi – hôm nay
    2 ngày, sang năm 1 ngày. Không ghi lại bản đã dùng thì các lead cũ bị chấm theo thước mới, và
    người bị chấm có quyền không nhận kết quả ấy.
    """
    __tablename__ = "lead_ban_giao"
    VIEC = {
        "giao": "Giao cho Sales",
        "nhan": "Sales tiếp nhận",
        "giao_lai": "Giao lại người khác",
        "doi_han": "Đổi hạn xử lý",
        "tra_lai": "Sales trả lại",
    }
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    viec: Mapped[str] = mapped_column(String(10), index=True)
    tu_nguoi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    den_nguoi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    han_cu: Mapped[date | None] = mapped_column(Date, nullable=True)
    han_moi: Mapped[date | None] = mapped_column(Date, nullable=True)
    phien_ban_quy_tac: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ly_do: Mapped[str] = mapped_column(String(200), default="")
    # `luc` do hệ thống đặt lúc ghi, KHÔNG nhận từ người dùng. Cho người dùng sửa thời điểm thao
    # tác thì lịch sử này không còn là bằng chứng nữa.
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    boi: Mapped[str] = mapped_column(String(50), default="")


class LeadChannelStat(Base):
    """Tổng số lead theo kênh × tháng (khi không có danh sách thô – nhập từ báo cáo Marketing)."""
    __tablename__ = "lead_channel_stats"
    __table_args__ = (UniqueConstraint("lead_month", "channel", name="uq_lead_stat_month_channel"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_month: Mapped[str] = mapped_column(String(7), index=True)
    channel: Mapped[str] = mapped_column(String(40))
    leads: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float | None] = mapped_column(TIEN)                       # chi phí kênh (nếu có) → chi phí/lead, nullable=True
    updated_by: Mapped[str] = mapped_column(String(50), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class ZaloMessage(Base):
    """Nhật ký tin Zalo: OA (theo user_id, khách đã quan tâm OA) hoặc ZNS (theo SĐT, mẫu đã duyệt)."""
    __tablename__ = "zalo_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), default="oa")                 # oa / zns
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    zalo_uid: Mapped[str] = mapped_column(String(40), default="")
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    template_id: Mapped[str] = mapped_column(String(40), default="")
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    text: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(String(30), default="")                # nhac_coc / xac_nhan_booking / cham_soc / khuyen_mai / cam_on
    status: Mapped[str] = mapped_column(String(20), default="cho_gui")          # cho_gui / da_gui / loi / cho_cau_hinh
    response: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    """Hộp thư đa kênh: một hội thoại với khách trên Facebook Messenger / Zalo OA / web chat…; gắn lead, sale phụ trách, đồng hồ SLA trả lời."""
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("channel", "external_id", name="uq_conv_channel_ext"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)                # facebook / zalo / web / vchat
    external_id: Mapped[str] = mapped_column(String(80))                        # PSID (Messenger) / user_id (Zalo)
    page_id: Mapped[str] = mapped_column(String(40), default="")
    customer_name: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(20), default="", index=True)
    lead_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sales_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="mo")                # mo / cho_sale / ai_da_tra_loi / dong
    last_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # tin khách gần nhất
    last_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # tin công ty gần nhất
    sla_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)   # hạn sale phải trả lời
    unanswered: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_replies: Mapped[int] = mapped_column(Integer, default=0)
    ai_off: Mapped[bool] = mapped_column(Boolean, default=False)                 # sale tắt AI cho hội thoại này
    summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    direction: Mapped[str] = mapped_column(String(3))                            # in / out
    sender: Mapped[str] = mapped_column(String(20), default="khach")             # khach / sale / ai / he_thong
    sender_name: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    external_id: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="da_nhan")           # da_nhan / da_gui / loi
    response: Mapped[str] = mapped_column(Text, default="")
    ai_review: Mapped[dict] = mapped_column(JSON, default=dict)                  # AI chấm câu trả lời của sale
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class ZaloOaToken(Base):
    """Chỗ ở của token Zalo OA. MỘT dòng duy nhất, luôn đọc dòng mới nhất.

    Vì sao phải có bảng này thay vì để token trong biến môi trường: Zalo cấp access token sống 25 giờ, và
    refresh token ĐỔI MỚI sau mỗi lần dùng – dùng xong cái cũ chết. Máy chủ giữ token mới trong bộ nhớ thôi
    thì mỗi lần khởi động lại (gói Render miễn phí ngủ khi vắng khách) nó đọc lại refresh token CŨ từ biến
    môi trường, thứ mà Zalo đã vô hiệu hoá. Kết quả: chạy ngon đúng một ngày rồi Zalo OA lặng lẽ chết, không
    cảnh báo, và tin khách nhắn vào không ai thấy. Đó là loại lỗi tệ nhất – nó không kêu.
    """
    __tablename__ = "zalo_oa_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    oa_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    het_han_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)      # access token
    lan_lam_moi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    so_lan_lam_moi: Mapped[int] = mapped_column(Integer, default=0)
    # Chuỗi chống giả mạo của lần xin uỷ quyền đang mở. Không có nó thì bất kỳ ai gọi đúng đường dẫn trả về
    # cũng đặt được token cho hệ thống.
    ma_chong_gia: Mapped[str] = mapped_column(String(64), default="")
    loi_cuoi: Mapped[str] = mapped_column(Text, default="")
    cap_boi: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class TongDaiSuKien(Base):
    """Nhật ký NGUYÊN VĂN mọi thứ tổng đài gửi sang. Chưa diễn giải gì cả – và đó là chủ ý.

    Vì sao dựng cái này trước khi dựng phần khớp cuộc gọi vào lead: P.A Việt Nam công bố bốn API tổng đài
    (lịch sử cuộc gọi, file ghi âm, CallNow, webhook cuộc gọi đến) nhưng KHÔNG công bố đặc tả kỹ thuật. Bài
    hướng dẫn duy nhất có nội dung (28/08/2021) chỉ nêu bốn cái tên tham số – "số nội bộ, số gọi đi,
    uniqueid, notecall" – và một URL ví dụ `callback_url.php`. Không địa chỉ, không cách xác thực, không
    kiểu dữ liệu, không chữ ký.

    Dựng phần khớp lead trên bốn cái tên đó là đoán. Đoán sai thì hỏng LẶNG LẼ: webhook vẫn trả 200, tổng
    đài vẫn báo thành công, còn VTOS thì ghi rỗng – và không ai biết cho tới lúc cần tra một cuộc gọi mà
    không có.

    Nên bảng này KHÔNG có cột `so_dien_thoai`, `may_nhanh`, `uniqueid`. Nó chỉ giữ nguyên văn: phương thức,
    đường dẫn, chuỗi truy vấn, thân yêu cầu, đầu mục HTTP. Khi P.A trỏ webhook vào đây, mình ĐỌC ĐƯỢC dữ
    liệu thật rồi mới viết phần diễn giải – dựa trên bằng chứng, không dựa trên hình dung.

    `da_doc` đánh dấu dòng đã có người xem và rút ra kết luận; không phải trạng thái nghiệp vụ, vì chưa có
    nghiệp vụ nào.
    """
    __tablename__ = "tong_dai_su_kien"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Nguồn TỰ KHAI (pavietnam / vchat / khac). Không dùng để phân quyền – chỉ để lọc khi đọc.
    nguon: Mapped[str] = mapped_column(String(20), default="", index=True)
    phuong_thuc: Mapped[str] = mapped_column(String(10), default="")
    duong_dan: Mapped[str] = mapped_column(String(300), default="")
    chuoi_truy_van: Mapped[str] = mapped_column(Text, default="")
    than: Mapped[str] = mapped_column(Text, default="")
    dau_muc: Mapped[dict] = mapped_column(JSON, default=dict)
    ip_goi: Mapped[str] = mapped_column(String(60), default="", index=True)
    da_doc: Mapped[bool] = mapped_column(Boolean, default=False)
    nhan_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
