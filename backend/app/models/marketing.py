"""Marketing – Đợt 1: CHIẾN DỊCH.

Vì sao chiến dịch phải là một BẢN GHI CÓ MÃ chứ không phải một ô chữ tự do như trường `campaign` cũ trên
lead: hai người gõ "Tết 2026" và "tet2026" là hai chiến dịch khác nhau trong mắt máy, nên không bao giờ
cộng được chi phí trên mỗi lead. Có mã rồi thì lead, đề nghị chi, nội dung và khiếu nại mới trỏ về cùng
một chỗ, và câu hỏi "bỏ ra bao nhiêu, thu về bao nhiêu" mới trả lời được.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

CAMPAIGN_STATUS = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "dang_chay": "Đang chạy",
                   "tam_dung": "Tạm dừng", "ket_thuc": "Kết thúc", "da_danh_gia": "Đã đánh giá"}
MUC_TIEU = {"ra_lead": "Ra lead", "nhan_dien": "Nhận diện thương hiệu",
            "ban_tour": "Bán tour cụ thể", "cham_khach_cu": "Chăm sóc khách cũ"}
KENH = ("facebook", "zalo", "google", "tiktok", "email", "su_kien", "doi_tac", "khac")
KENH_TEN = {"facebook": "Facebook", "zalo": "Zalo OA", "google": "Google", "tiktok": "TikTok",
            "email": "Email", "su_kien": "Sự kiện", "doi_tac": "Đối tác", "khac": "Khác"}


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)              # CD2609-01
    name: Mapped[str] = mapped_column(String(160))
    objective: Mapped[str] = mapped_column(String(20))                      # MUC_TIEU
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    mang: Mapped[str] = mapped_column(String(6), default="le")              # le / doan
    channels: Mapped[list] = mapped_column(JSON, default=list)
    from_date: Mapped[date] = mapped_column(Date)
    to_date: Mapped[date | None] = mapped_column(Date, nullable=True)       # rỗng = đang chạy
    budget: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    target_leads: Mapped[int] = mapped_column(Integer, default=0)
    target_bookings: Mapped[int] = mapped_column(Integer, default=0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="nhap")
    evaluation: Mapped[str] = mapped_column(Text, default="")               # bắt buộc khi chuyển sang da_danh_gia
    note: Mapped[str] = mapped_column(Text, default="")
    # Ai điền tờ trình này. AI được phép ĐỀ XUẤT nhưng bản do AI lập luôn dừng ở nháp và phải người
    # có thẩm quyền duyệt – cùng nguyên tắc đã áp cho AI trả lời khách ở hộp thư.
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")      # nguoi / ai
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")               # AI giải thích căn cứ đề xuất
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_by: Mapped[str] = mapped_column(String(50), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------- Đợt 2: KẾ HOẠCH & NGÂN SÁCH ----------
HANG_MUC = {"quang_cao": "Quảng cáo trả phí", "noi_dung": "Nội dung – sản xuất", "su_kien": "Sự kiện",
            "an_pham": "Ấn phẩm – quà tặng", "nghien_cuu": "Nghiên cứu thị trường", "khac": "Khác"}
BUDGET_STATUS = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "hieu_luc": "Đang hiệu lực", "dong": "Đã đóng kỳ"}


class MarketingBudget(Base):
    """Ngân sách marketing một kỳ, một pháp nhân.

    Bảng này chỉ giữ phần DỰ TOÁN. Số ĐÃ CHI không nằm ở đây mà đọc từ đề nghị chi đã duyệt – hai nơi
    giữ hai con số chi phí của cùng một kỳ là hai con số sẽ lệch nhau, và không ai biết tin con số nào.
    """
    __tablename__ = "mkt_budgets"
    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(8), index=True)              # 2026-09 hoặc 2026-Q4
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    target_leads: Mapped[int] = mapped_column(Integer, default=0)
    target_revenue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    rationale: Mapped[str] = mapped_column(Text, default="")               # căn cứ – bắt buộc
    status: Mapped[str] = mapped_column(String(10), default="nhap")
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_by: Mapped[str] = mapped_column(String(50), default="")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MarketingBudgetLine(Base):
    """Một hạng mục của ngân sách kỳ. Tổng không lưu thành cột riêng – tổng luôn cộng từ các dòng này."""
    __tablename__ = "mkt_budget_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    budget_id: Mapped[int] = mapped_column(ForeignKey("mkt_budgets.id"), index=True)
    hang_muc: Mapped[str] = mapped_column(String(20))
    amount: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")


# ---------- Đợt 5: NỘI DUNG & THƯƠNG HIỆU ----------
# Vietourist là công ty đại chúng (mã VTD, sàn UPCoM). Một bài đăng hứa "cam kết hoàn tiền 100%" hay một
# con số tài chính đưa ra ngoài mà chưa ai duyệt là rủi ro pháp lý và rủi ro công bố thông tin, không phải
# chuyện nội bộ Marketing. Vì vậy bảng này là SỔ DUYỆT, không phải thư viện ảnh.
ND_LOAI = {"bai_dang": "Bài đăng", "video": "Video", "an_pham": "Ấn phẩm in", "email": "Email",
           "kich_ban": "Kịch bản tư vấn", "thong_cao": "Thông cáo báo chí"}
ND_KENH = {"website": "Website", "facebook": "Facebook", "zalo": "Zalo OA", "tiktok": "TikTok",
           "youtube": "YouTube", "in_an": "In ấn", "bao_chi": "Báo chí"}
ND_TRANG_THAI = {"nhap": "Nháp", "cho_duyet": "Chờ duyệt", "cho_ky_2": "Chờ chữ ký thứ hai",
                 "da_duyet": "Đã duyệt", "da_dang": "Đã đăng", "go": "Đã gỡ / hết hiệu lực"}


class ContentItem(Base):
    __tablename__ = "content_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)              # ND2609-014
    title: Mapped[str] = mapped_column(String(200))
    loai: Mapped[str] = mapped_column(String(12))
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    kenh: Mapped[list] = mapped_column(JSON, default=list)
    ngay_du_kien: Mapped[date] = mapped_column(Date)
    ban_thao: Mapped[str] = mapped_column(String(400), default="")          # đường dẫn bản thảo – bắt buộc
    # Hai ô quyết định có cần chữ ký thứ hai hay không. Trả lời "Có" ở một trong hai thì bản thảo phải qua
    # người ký thứ hai (Ban TGĐ hoặc Pháp chế) trước khi được duyệt.
    co_cam_ket: Mapped[bool] = mapped_column(Boolean, default=False)
    co_so_lieu_tc: Mapped[bool] = mapped_column(Boolean, default=False)
    nguoi_soan: Mapped[str] = mapped_column(String(50), default="")
    nguoi_duyet: Mapped[str] = mapped_column(String(160), default="")       # nhiều chữ ký: ngăn bởi dấu phẩy
    status: Mapped[str] = mapped_column(String(12), default="nhap")
    link_dang: Mapped[str] = mapped_column(String(400), default="")
    ly_do_go: Mapped[str] = mapped_column(String(300), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    nguon_tao: Mapped[str] = mapped_column(String(6), default="nguoi")
    ai_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỔ HOẠT ĐỘNG PR — Chủ tịch chốt 18/9/2026
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# BẢNG MỚI, và lần này bảng mới là đúng — khác hẳn sổ tài sản thương hiệu cùng ngày, chỗ ấy dùng
# chung bảng TSCĐ vì một bộ nhận diện mua ngoài vốn LÀ một thẻ tài sản. Ở đây không có bảng nào
# đang giữ "một việc truyền thông đã xảy ra": `content_items` là BẢN THẢO trước khi đăng (có ô
# bản thảo, ô người duyệt, ô ngày dự kiến), còn sổ này ghi VIỆC ĐÃ RA NGOÀI và ai chịu trách
# nhiệm cho nó. Nhét vào `content_items` thì một bảng phải trả lời hai câu hỏi ngược chiều nhau.
#
# HAI CHỮ KÝ CỦA CHỦ TỊCH NẰM Ở ĐÂY:
#
#   · NGƯỜI PHÁT NGÔN LÀ P.TGĐ MARKETING. `nguoi_phat_ngon` KHÔNG phải ô gõ tên tự do — nó lưu
#     tên tài khoản của người đã bấm nút phát, và hàng rào ở đường API chỉ mở cho đúng vai ấy.
#     Ô gõ tự do thì ba tháng sau không ai tra được ai đã nói câu đó.
#
#   · KHỦNG HOẢNG TRUYỀN THÔNG: 2 GIỜ kể từ lúc việc được GHI VÀO SỔ. Mốc chạy theo đồng hồ
#     thật, không trừ ngày nghỉ và không quy ra giờ hành chính — một việc ghi lúc 22h thứ Bảy thì
#     0h là quá hạn. Đó là bản chất của khủng hoảng truyền thông, và cũng đúng cách VTOS đã làm
#     với hạn xử lý lead (24 giờ, P.TGĐ chốt cùng ngày).
PR_LOAI = {
    "bai_bao": "Bài báo / phỏng vấn", "thong_cao": "Thông cáo báo chí",
    "su_kien": "Sự kiện", "phat_ngon": "Phát ngôn chính thức",
    "mang_xa_hoi": "Bài đăng mạng xã hội", "khung_hoang": "Xử lý khủng hoảng",
}
# `nhap` → đang soạn. `cho_phat` → đã soạn xong, chờ người phát ngôn bấm. `da_phat` → đã ra ngoài.
# `khong_phat` → quyết định KHÔNG phát, và phải ghi lý do: một việc bị bỏ mà không ai ghi vì sao
# thì lần sau có người lại đề xuất đúng việc ấy.
PR_TRANG_THAI = {"nhap": "Nháp", "cho_phat": "Chờ người phát ngôn",
                 "da_phat": "Đã phát", "khong_phat": "Quyết định không phát"}


class PrHoatDong(Base):
    """Một việc truyền thông: bài báo, thông cáo, sự kiện, phát ngôn, hoặc một vụ khủng hoảng."""
    __tablename__ = "mkt_pr_hoat_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(20), unique=True, index=True)     # PR-2026-09-0001
    loai: Mapped[str] = mapped_column(String(16))
    tieu_de: Mapped[str] = mapped_column(String(300))
    tom_tat: Mapped[str] = mapped_column(Text, default="")
    noi_dang: Mapped[str] = mapped_column(String(200), default="")           # báo nào, trang nào, ở đâu
    link: Mapped[str] = mapped_column(String(400), default="")
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="nhap")
    # ---- Người phát ngôn ----
    # Ô này CHỈ hệ thống ghi, lúc người có vai phát ngôn bấm nút. Xem ghi chú ở trên.
    nguoi_phat_ngon: Mapped[str] = mapped_column(String(50), default="")
    phat_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_khong_phat: Mapped[str] = mapped_column(String(300), default="")
    # ---- Khủng hoảng truyền thông ----
    # `ghi_nhan_luc` là MỐC BẮT ĐẦU ĐẾM, và nó do cơ sở dữ liệu đặt lúc dòng vào sổ. Cho người
    # dùng sửa mốc ấy thì "quá hạn" không còn nghĩa gì: ai sắp quá hạn chỉ cần lùi mốc lại.
    la_khung_hoang: Mapped[bool] = mapped_column(Boolean, default=False)
    ghi_nhan_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    phan_hoi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    phan_hoi_boi: Mapped[str] = mapped_column(String(50), default="")
    muc_do: Mapped[str] = mapped_column(String(12), default="")              # nhe / vua / nghiem_trong
    nguoi_tao: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Tin trong hộp thư đa kênh đã sinh ra dòng này, nếu có (19/9/2026 – cửa lọc tin khủng hoảng).
    # Không có cột này thì KHÔNG đo được "bộ lọc bỏ sót bao nhiêu vụ": không còn đường nào đi
    # ngược từ một vụ đã xảy ra về cái tin lẽ ra phải báo động. Rỗng là bình thường — một vụ nổ
    # trên báo thì không có tin nào trong hộp thư, và `loc_khung_hoang.do_bo_loc()` đếm riêng
    # phần ấy thay vì để nó rơi khỏi mẫu số.
    nguon_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Cùng vai trò, cho bình luận công khai (19/9/2026).
    nguon_binh_luan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


# ---------- Đợt 6b: CỬA LỌC TIN KHỦNG HOẢNG (19/9/2026) ----------
# Kết luận của NGƯỜI về một dòng trong hàng đợi. Bảng này không chứa điểm "hiện tại" của bộ lọc —
# điểm hiện tại chấm lại bất cứ lúc nào từ tin gốc. Nó chứa đúng hai thứ máy không tự biết:
# NGƯỜI ĐÃ KẾT LUẬN GÌ, và ĐIỂM BỘ LỌC NÓI RA LÚC ẤY. Cặp ấy là toàn bộ nguyên liệu của phép đo
# "bắt đúng / báo nhầm / bỏ sót".
KET_LUAN = {"bo_qua": "Bỏ qua – không phải việc của Marketing",
            "lap_pr": "Đã lập dòng vào sổ hoạt động PR"}


class HopThuXuLy(Base):
    """Một tin trong hộp thư đã được người của Marketing xem và kết luận.

    Chỉ dòng ĐÃ XỬ LÝ mới nằm ở đây. Ghi mọi tin vào bảng này là nhân đôi bảng `messages` (hơn
    một trăm nghìn dòng) để lưu một chữ "chưa xem" — hàng đợi suy ra được bằng phép trừ, còn
    kết luận của người thì không suy ra được từ đâu cả.
    """
    __tablename__ = "mkt_hop_thu_xu_ly"
    id: Mapped[int] = mapped_column(primary_key=True)
    # HAI NGUỒN, HAI CỘT KHOÁ NGOẠI RIÊNG – cố ý không dùng một cặp (loại, mã) chung.
    #
    # Cặp chung nghe gọn hơn, nhưng nó vứt bỏ ràng buộc khoá ngoại: một mã trỏ vào hư không thì cơ
    # sở dữ liệu không kêu, và ba tháng sau hàng đợi có những dòng không mở ra được. Hai cột, mỗi
    # cột một khoá ngoại thật, ĐÚNG MỘT cột có giá trị – `nguon` nói cột nào.
    nguon: Mapped[str] = mapped_column(String(10), default="tin")        # tin / binh_luan
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), unique=True,
                                                  index=True, nullable=True)
    binh_luan_id: Mapped[int | None] = mapped_column(ForeignKey("mkt_fb_binh_luan.id"), unique=True,
                                                    index=True, nullable=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"),
                                                        index=True, nullable=True)
    diem_luc_do: Mapped[int] = mapped_column(Integer, default=0)
    ly_do_luc_do: Mapped[str] = mapped_column(Text, default="")
    co_tu_do: Mapped[bool] = mapped_column(Boolean, default=False)
    ket_luan: Mapped[str] = mapped_column(String(10))                        # KET_LUAN
    pr_id: Mapped[int | None] = mapped_column(ForeignKey("mkt_pr_hoat_dong.id"), nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")            # lý do bỏ qua – bắt buộc
    nguoi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------- Đợt 6c: BÌNH LUẬN CÔNG KHAI FANPAGE (19/9/2026) ----------
#
# VÌ SAO BẢNG RIÊNG, KHÔNG ĐỔ VÀO `messages` CỦA HỘP THƯ
#
# Đổ vào hộp thư là cách viết ít dòng nhất, và nó hỏng ba chỗ cùng lúc:
#
#   1. SINH LEAD GIẢ. `inbox.get_or_create` tạo một Lead cho mỗi hội thoại mới. Mỗi người bình luận
#      "đẹp quá" hay "giá bao nhiêu ạ" sẽ thành một lead, và TỶ LỆ CHỐT LEAD – con số Sales đang
#      được đo bằng – bị pha loãng bằng thứ không phải lead. Một chỉ tiêu bị pha loãng thì không ai
#      phát hiện ra, người ta chỉ thấy "dạo này chốt kém".
#   2. ĐỒNG HỒ SLA CỦA SALES CHẠY NHẦM VIỆC. Hộp thư đặt hạn trả lời cho Sales. Bình luận dưới bài
#      đăng là việc của Marketing.
#   3. MẤT ĐÚNG CÁI KHÁC BIỆT QUAN TRỌNG NHẤT. Một bình luận thì CÔNG KHAI – người ngoài đọc được
#      ngay. Một tin nhắn riêng thì chưa. Gộp hai thứ vào một bảng là xoá mất cái làm nên mức độ
#      khẩn, đúng lúc cần nó nhất.
#
# BÌNH LUẬN BỊ XOÁ THÌ GIỮ LẠI DÒNG, chỉ đánh dấu `da_xoa`. Một bình luận bị xoá là bằng chứng nó đã
# TỪNG có, và nó thường bị xoá đúng vào lúc đáng giữ nhất.
BL_ITEM = ("comment",)


class FbBinhLuan(Base):
    """Một bình luận công khai dưới bài đăng Fanpage."""
    __tablename__ = "mkt_fb_binh_luan"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Khoá chống trùng là mã của Facebook. Webhook có thể gửi lại cùng một sự kiện; không có khoá này
    # thì một bình luận thành ba dòng và con số "bao nhiêu bình luận đáng đọc" sai ngay.
    comment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    post_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    parent_id: Mapped[str] = mapped_column(String(64), default="")     # bình luận trả lời bình luận
    page_id: Mapped[str] = mapped_column(String(40), default="")
    tac_gia_id: Mapped[str] = mapped_column(String(64), default="")
    tac_gia_ten: Mapped[str] = mapped_column(String(120), default="")
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(400), default="")
    # Page tự trả lời dưới bài của mình. KHÔNG chấm điểm: câu trả lời của mình mà bị bộ lọc nêu lên
    # thì hàng đợi tự nuôi chính nó.
    la_cua_page: Mapped[bool] = mapped_column(Boolean, default=False)
    da_sua: Mapped[bool] = mapped_column(Boolean, default=False)
    da_xoa: Mapped[bool] = mapped_column(Boolean, default=False)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    nhan_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
