"""4.4.2 · Chương trình của TỪNG CHUYẾN — hai bảng, và lý do có bảng riêng thay vì đọc sống sản phẩm.

Trước bản này, tab Thông tin in nguyên văn `products.program` — chương trình của SẢN PHẨM. Đó là
bản mẫu dùng cho mọi chuyến cùng mã, nên:

  . sửa nó là sửa chương trình của MỌI chuyến, kể cả chuyến đã khởi hành và chuyến đã kết thúc;
  . không chuyến nào ghi được thay đổi của riêng nó (đổi khách sạn, đảo điểm vì thời tiết);
  . không ai biết khách của chuyến này đã nhận bản nào.

CHÉP MỘT LẦN, KHÔNG NỐI SỐNG — đây là quyết định quan trọng nhất của vòng này.
Mở tab Chương trình lần đầu thì hệ thống CHÉP bản sản phẩm vào `ban_san_pham_goc` và dựng đủ số
ngày RỖNG. Từ đó chương trình của chuyến sống độc lập. Nếu đọc sống thì người sửa sản phẩm hôm nay
lặng lẽ viết lại chương trình của một đoàn đã đi tuần trước — và bản khách cầm trong tay không còn
khớp với bản trên hệ thống, đúng lúc có tranh chấp thì không ai chứng minh được điều gì.

Mặt sau của quyết định ấy phải nói ra: sản phẩm đổi thì chuyến KHÔNG tự đổi theo. Nên có
`lech_voi_san_pham()` đếm chỗ ấy và màn hình in ra — người điều hành quyết có chép lại hay không.
Tự đồng bộ là quay về đúng cái hỏng vừa chữa.

KHÔNG TỰ TÁCH VĂN BẢN SẢN PHẨM THÀNH TỪNG NGÀY. `products.program` là văn bản tự do; đoán ranh giới
ngày cho ra một bản tách trông rất hợp lý mà có thể sai — và một lịch trình sai nhưng gọn gàng thì
không ai đọc lại. Hệ thống ĐỀ XUẤT một bản tách (chỉ khi văn bản có mốc "Ngày N" rõ ràng), in ra
cạnh bản gốc, và người điều hành bấm nhận. Đề xuất không bao giờ tự ghi.
"""
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Nguồn của chương trình chuyến. Ghi lại để màn hình nói đúng: "chép từ sản phẩm PT001 ngày…" khác
# hẳn "điều hành tự soạn", và hai thứ ấy có mức tin cậy khác nhau khi đối chiếu với bản khách cầm.
CT_NGUON = {
    "chua_soan": "Chưa soạn – mới dựng khung ngày rỗng",
    "chep_san_pham": "Chép từ chương trình sản phẩm",
    "tu_soan": "Điều hành tự soạn cho chuyến này",
}


class ChuongTrinhTour(Base):
    """Đầu chương trình của một chuyến (1–1 với tour)."""
    __tablename__ = "chuong_trinh_tour"
    __table_args__ = (UniqueConstraint("tour_id", name="uq_chuong_trinh_tour"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    nguon: Mapped[str] = mapped_column(String(20), default="chua_soan")
    product_id_goc: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    # ẢNH CHỤP bản sản phẩm lúc chép. Giữ nó là cách duy nhất trả lời được câu "sản phẩm đã đổi
    # chưa kể từ lúc chuyến này chép" — so bản hiện tại với ảnh này, không so với chương trình
    # chuyến (chương trình chuyến đã được sửa có chủ ý, so với nó thì lúc nào cũng lệch).
    ban_san_pham_goc: Mapped[str] = mapped_column(Text, default="")
    chep_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_cuoi_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_cuoi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ChuongTrinhNgay(Base):
    """Một dòng = một NGÀY của một chuyến."""
    __tablename__ = "chuong_trinh_ngay"
    __table_args__ = (UniqueConstraint("tour_id", "ngay_thu", name="uq_chuong_trinh_tour_ngay"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    ngay_thu: Mapped[int] = mapped_column(Integer)                       # 1, 2, 3…
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)       # ngày dương lịch, suy từ start_date
    tieu_de: Mapped[str] = mapped_column(String(200), default="")
    noi_dung: Mapped[str] = mapped_column(Text, default="")
    # Ba bữa khai RIÊNG chứ không nhét vào nội dung: đây là thứ nhà hàng và hướng dẫn viên đọc để
    # đặt bàn, và một câu văn "ăn trưa tại nhà hàng X" thì máy không đếm được bao nhiêu bữa.
    bua_sang: Mapped[bool] = mapped_column(Boolean, default=False)
    bua_trua: Mapped[bool] = mapped_column(Boolean, default=False)
    bua_toi: Mapped[bool] = mapped_column(Boolean, default=False)
    khach_san: Mapped[str] = mapped_column(String(200), default="")
    phuong_tien: Mapped[str] = mapped_column(String(120), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # SỬA SAU KHI CHUYẾN ĐÃ KHỞI HÀNH là việc CÓ THẬT (thời tiết, sự cố, khách đổi ý), nên KHÔNG
    # cấm. Nhưng nó phải để lại dấu: cấm thì người ta sửa ở chỗ khác và hệ thống mất dấu hoàn toàn.
    lan_sua_sau_khoi_hanh: Mapped[int] = mapped_column(Integer, default=0)
    ly_do_sua_gan_nhat: Mapped[str] = mapped_column(Text, default="")
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
