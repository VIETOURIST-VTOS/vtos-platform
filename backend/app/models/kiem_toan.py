"""Hồ sơ kiểm toán – V7 Đợt 3 (10/9/2026).

PHÂN BIỆT VỚI `audit_log`, VÌ HAI THỨ NÀY HAY BỊ GỌI CHUNG MỘT TÊN
------------------------------------------------------------------
`audit_log` là NHẬT KÝ NGHIỆP VỤ: mỗi thao tác ghi để lại một dòng, nối chuỗi bằng mã băm, bất biến, máy
tự ghi. Nó trả lời "ai đã sửa cái gì lúc nào".

Bảng ở tệp này là HỒ SƠ GIAO CHO KIỂM TOÁN VIÊN: một kỳ soát xét hoặc kiểm toán, đơn vị nào làm, họ yêu
cầu những tài liệu gì, ai bên mình phụ trách từng mục, hạn nộp, đã nộp chưa, họ hỏi thêm gì, và cuối
cùng ý kiến kiểm toán là gì. Nó trả lời "kỳ này ta đã đưa cho họ những gì, còn thiếu gì".

Hai thứ khác nhau tới mức không có cột nào dùng chung. Trước bản này VTOS chỉ có cái thứ nhất, nên mỗi
kỳ soát xét lại quản bằng một tệp Excel gửi qua lại – và câu "hôm nay còn thiếu mục nào" chỉ trả lời
được bằng cách mở tệp mới nhất của người gửi cuối cùng.

BA BẢNG
-------
  ho_so_kiem_toan            : một kỳ kiểm toán / soát xét của MỘT pháp nhân
  ho_so_kiem_toan_muc        : từng mục tài liệu kiểm toán yêu cầu
  ho_so_kiem_toan_dieu_chinh : bút toán điều chỉnh kiểm toán đề nghị sau soát xét

BẢNG ĐIỀU CHỈNH CỐ TÌNH KHÔNG CÓ Ô SỐ TIỀN
------------------------------------------
Điều chỉnh sau soát xét là bút toán thật, phải nằm ở SỔ (journal_entries) và đi qua đúng quy ước hạch
toán. Bảng này chỉ giữ SỐ HIỆU bút toán đã ghi. Có một ô "số tiền điều chỉnh" ở đây thì sẽ có ngày sổ
ghi một đằng, hồ sơ kiểm toán ghi một nẻo, và bản giải trình cho kiểm toán viên lấy số từ bảng sai.
Cùng lý lẽ với ô bồi thường của khiếu nại khách và ô chi phí phát sinh của sự cố tour.

Tệp đính kèm không nằm ở đây: chúng đi qua `attachments` với đối tượng "ho_so_kiem_toan" (nhóm hồ sơ
08_Kiem_toan, đã có sẵn trong danh mục từ trước). Một kho tệp thứ hai là một kho tệp không ai dọn.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

KT_LOAI = {
    "soat_xet": "Soát xét bán niên",
    "kiem_toan_nam": "Kiểm toán báo cáo tài chính năm",
    "kiem_tra_thue": "Thanh tra / kiểm tra thuế",
    "kiem_toan_noi_bo": "Kiểm toán nội bộ / Ban Kiểm soát",
}

KT_TRANG_THAI = {
    "chuan_bi": "Chuẩn bị – đang lập danh mục",
    "dang_cung_cap": "Đang cung cấp hồ sơ",
    "dang_soat_xet": "Kiểm toán đang làm việc",
    "co_y_kien": "Đã có dự thảo ý kiến",
    "da_phat_hanh": "Đã phát hành báo cáo",
    "dong": "Đã đóng hồ sơ",
}
KT_CHUYEN = {"chuan_bi": ("dang_cung_cap",), "dang_cung_cap": ("dang_soat_xet",),
             "dang_soat_xet": ("co_y_kien", "dang_cung_cap"), "co_y_kien": ("da_phat_hanh",),
             "da_phat_hanh": ("dong",), "dong": ()}

# Bốn loại ý kiến theo chuẩn mực kiểm toán Việt Nam. Ghi thành danh sách chọn chứ không để gõ tự do:
# Vietourist là công ty đại chúng, loại ý kiến là thông tin phải công bố, và một ô văn bản tự do sẽ cho
# ra bốn cách viết khác nhau cho cùng một loại ý kiến qua bốn kỳ.
KT_Y_KIEN = {
    "chap_nhan_toan_phan": "Chấp nhận toàn phần",
    "ngoai_tru": "Ngoại trừ",
    "trai_nguoc": "Trái ngược",
    "tu_choi": "Từ chối đưa ra ý kiến",
}

MUC_TRANG_THAI = {
    "chua_gui": "Chưa gửi",
    "da_gui": "Đã gửi",
    "hoi_them": "Kiểm toán hỏi thêm",
    "chap_nhan": "Kiểm toán đã chấp nhận",
    "khong_can": "Không áp dụng cho kỳ này",
}

DC_TRANG_THAI = {
    "de_xuat": "Kiểm toán đề nghị",
    "da_ghi_so": "Đã ghi sổ",
    "khong_dong_y": "Công ty không đồng ý",
}


class HoSoKiemToan(Base):
    __tablename__ = "ho_so_kiem_toan"
    __table_args__ = (Index("ux_ho_so_kiem_toan_ky", "company_id", "ky", "loai", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)          # KT2026H1-001
    # Pháp nhân được kiểm toán. Rỗng = CHƯA XÁC ĐỊNH, KHÔNG mặc định về công ty mẹ – cùng quy ước với
    # đề nghị chi và hồ sơ khiếu nại. Hợp nhất và riêng lẻ là hai hồ sơ khác nhau của hai kỳ khác nhau.
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    ky: Mapped[str] = mapped_column(String(12), index=True)             # 2026H1 · 2026 · 2026Q3
    loai: Mapped[str] = mapped_column(String(20), default="soat_xet")
    don_vi_kiem_toan: Mapped[str] = mapped_column(String(160), default="")
    so_hop_dong: Mapped[str] = mapped_column(String(60), default="")
    nguoi_dau_moi: Mapped[str] = mapped_column(String(50), default="")  # người của mình, đầu mối làm việc
    ngay_bat_dau: Mapped[date | None] = mapped_column(Date, nullable=True)
    han_hoan_thanh: Mapped[date | None] = mapped_column(Date, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(16), default="chuan_bi", index=True)
    # Ba ô dưới chỉ có nghĩa khi đã phát hành. Điền trước là đoán trước kết quả kiểm toán.
    loai_y_kien: Mapped[str] = mapped_column(String(24), default="")
    so_bao_cao: Mapped[str] = mapped_column(String(60), default="")
    ngay_bao_cao: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Vấn đề nhấn mạnh / cơ sở của ý kiến ngoại trừ. Nguyên văn của kiểm toán, không tóm tắt.
    van_de_nhan_manh: Mapped[str] = mapped_column(Text, default="")

    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class HoSoKiemToanMuc(Base):
    """Một mục trong danh mục tài liệu kiểm toán yêu cầu."""
    __tablename__ = "ho_so_kiem_toan_muc"
    __table_args__ = (Index("ix_ho_so_kiem_toan_muc_ho_so", "ho_so_id", "trang_thai"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ho_so_id: Mapped[int] = mapped_column(ForeignKey("ho_so_kiem_toan.id"), index=True)
    stt: Mapped[int] = mapped_column(Integer, default=0)
    ten: Mapped[str] = mapped_column(String(300))                       # "Sổ chi tiết TK 131 kèm đối chiếu công nợ"
    # Nhóm hồ sơ theo Mô hình quản trị số hóa mục 7 (01_Phap_ly … 10_Marketing). Có nhóm thì tệp đính
    # kèm rơi đúng thư mục, và kiểm toán năm sau tìm được ở chỗ cũ.
    nhom_ho_so: Mapped[str] = mapped_column(String(20), default="08_Kiem_toan")
    # Phòng ban CHỊU TRÁCH NHIỆM cung cấp. Không có cột này thì mọi mục đều rơi về Kế toán, kể cả hợp
    # đồng lao động và hồ sơ xe – và người đi đòi từng phòng vẫn là Kế toán.
    phong_ban: Mapped[str] = mapped_column(String(20), default="ketoan")
    nguoi_phu_trach: Mapped[str] = mapped_column(String(50), default="")
    han_nop: Mapped[date | None] = mapped_column(Date, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(16), default="chua_gui", index=True)
    ngay_gui: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Câu hỏi thêm của kiểm toán và câu trả lời của mình. Đây là phần hay thất lạc nhất trong cách quản
    # bằng thư điện tử: hỏi ở một luồng thư, trả lời ở luồng khác, và tới lúc lập bản giải trình thì
    # phải đi tìm lại.
    cau_hoi: Mapped[str] = mapped_column(Text, default="")
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class HoSoKiemToanDieuChinh(Base):
    """Bút toán điều chỉnh kiểm toán đề nghị. KHÔNG giữ số tiền – xem ghi chú đầu tệp."""
    __tablename__ = "ho_so_kiem_toan_dieu_chinh"

    id: Mapped[int] = mapped_column(primary_key=True)
    ho_so_id: Mapped[int] = mapped_column(ForeignKey("ho_so_kiem_toan.id"), index=True)
    noi_dung: Mapped[str] = mapped_column(Text)                         # kiểm toán đề nghị điều chỉnh gì
    # Số hiệu bút toán đã ghi sổ. Rỗng khi công ty chưa ghi hoặc không đồng ý – và trạng thái nói rõ
    # đang ở đâu, thay vì để một ô rỗng tự nó nghĩa là gì cũng được.
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(16), default="de_xuat")
    ly_do: Mapped[str] = mapped_column(Text, default="")                # nếu không đồng ý thì vì sao
    nguoi_quyet: Mapped[str] = mapped_column(String(50), default="")
    created_by: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
