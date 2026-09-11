"""Lớp 3 quyết toán tour: hai hình thức, dòng khách, dòng doanh thu, phương tiện, HDV chi, dấu vết sửa.

HAI HÌNH THỨC, KHÔNG PHẢI BA – Chủ tịch chốt 11/9/2026

    trong_nuoc  : tour lẻ nội địa và tour đoàn nội địa
    nuoc_ngoai  : tour lẻ và tour đoàn outbound

Đo trên bốn mẫu quyết toán thật thì "đoàn" KHÔNG phải một hình thức riêng. Đoàn Phú Quốc là tour
trong nước đi MÁY BAY; tour lẻ Nha Trang là tour trong nước đi Ô TÔ. Cái khác giữa chúng là phương
tiện, không phải hình thức – nên phương tiện là một trục riêng (bảng TourPhuongTien), và dựng "đoàn"
thành hình thức thứ ba là nhầm hai trục làm một.

Cái thật sự chia đôi là biên giới: trong nước thì một đồng tiền, không visa, không vé quốc tế; nước
ngoài thì nhiều đồng tiền có tỷ giá, phí lãnh sự quán từng khách một giá, vé quốc tế từng khách một
giá, và khách của đại lý ngồi ghép.

BỐN MẪU ĐÃ ĐỌC, VÀ MỖI MẪU DẠY MỘT THỨ

    NHA TRANG 10.07.26        lẻ, trong nước, ô tô   -> doanh thu là 42 DÒNG KHÁCH có tên
    ĐOÀN ĐÀ LẠT 3N3D 04.06    đoàn, trong nước       -> doanh thu là 4 DÒNG HỢP ĐỒNG cho 37 người,
                                                        có VAT 8%, và có DÒNG ÂM từ biên bản thanh lý
    SM000.05260226 (SIN/MAL)  lẻ, nước ngoài         -> ngoại tệ, vé máy bay, khách của đại lý ghép
    QuyetToan_27052026_UK     lẻ, nước ngoài         -> ba đồng tiền, phí lãnh sự quán từng khách
                                                        một giá, hai pháp nhân cùng thu

HAI GRAIN DOANH THU, MỘT BẢNG

Tour lẻ ghi doanh thu theo từng khách có tên; tour đoàn ghi theo dòng hợp đồng ("NGƯỜI LỚN × 25").
Cùng một hình – đơn giá, số lượng, thuế suất – nên cùng một bảng TourDoanhThuDong. Dòng nào ứng với
một khách có tên thì nối vào khach_id, dòng hợp đồng đoàn thì để trống. Nhờ vậy báo cáo toàn công ty
cộng được cả hai mà không phải cộng từ hai nguồn.

BẢNG LỚP 2 VÀ BẢNG LỚP 3 KHÁC NHAU CHỖ NÀO

Lớp 2 (app/models/quyet_toan.py) là BẢN SAO Y TỆP: giữ nguyên những gì tệp Excel viết, kể cả khi tệp
viết sai, để còn đối chiếu được với bản gốc đã có chữ ký. Nó treo vào tour_settlements – tức treo vào
CỬA NẠP.

Lớp 3 ở đây là bảng VẬN HÀNH: treo vào tours, mang quy tắc của công ty, mang luồng duyệt. Hai lớp trả
lời hai câu khác nhau – "tệp viết gì" và "công ty quyết gì". Mẫu Nha Trang cho thấy vì sao không gộp
được: tệp viết HDV mua 44 suất Tháp Bà trong khi chiết tính tính 40. Bản sao y tệp phải giữ CẢ HAI
con số; bảng vận hành phải sinh ra một khoản chờ người duyệt.
"""
from datetime import date, datetime
from sqlalchemy import String, Integer, Float, Numeric, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN

HINH_THUC = {
    "trong_nuoc": "Tour trong nước",
    "nuoc_ngoai": "Tour nước ngoài",
}

# AI TRẢ TIỀN. Chủ tịch chốt 11/9/2026: ghi hết mọi người ngồi trên chuyến, tách bốn nhóm.
# Tách khỏi bậc tuổi vì đây là hai trục: một cột không nói được "trẻ em của đại lý".
NHOM_KHACH = {
    "tra_tien": "Khách trả tiền – doanh thu của Vietourist",
    "mien_phi": "Suất miễn phí – khách được tặng, hoặc miễn phí theo tuổi",
    "noi_bo": "Nhân viên công ty đi cùng, kể cả trưởng đoàn công ty cử",
    "dai_ly": "Khách của đại lý ngồi ghép – doanh thu không thuộc Vietourist",
}

# TÍNH GIÁ BAO NHIÊU. Ngưỡng tuổi và tỷ lệ là tham số có hiệu lực theo ngày (tuoi_em_be, tuoi_tre_em,
# ty_le_tre_em_* và ty_le_em_be_* trong rules.DEFAULT_PARAMS – TÁCH THEO HÌNH THỨC TOUR), không
# viết cứng ở đây: đổi chính sách thì đổi tham số,
# còn các chuyến cũ giữ nguyên tỷ lệ của ngày chúng khởi hành.
LOAI_TUOI = {
    "nguoi_lon": "Người lớn – giá đầy đủ",
    "tre_em": "Trẻ em – theo tỷ lệ phần trăm giá người lớn",
    "em_be": "Em bé – theo tỷ lệ riêng của bậc em bé (trong nước 10%, nước ngoài 30%)",
}

LOAI_PHUONG_TIEN = {
    "o_to": "Ô tô",
    "may_bay": "Máy bay",
    "tau_hoa": "Tàu hoả",
    "tau_thuy": "Tàu thuỷ / ca nô",
    "khac": "Khác",
}

LOAI_DOANH_THU = {
    "hop_dong": "Theo hợp đồng / giá bán",
    "thanh_ly": "Điều chỉnh theo biên bản thanh lý – thường là số ÂM",
    "phu_thu": "Phụ thu phát sinh",
    "charge_huy": "Tiền phạt huỷ giữ lại",
    "thu_khac": "Thu khác",
}

TRANG_THAI_DUYET = {
    "cho_duyet": "Chờ Trưởng phòng Điều hành duyệt",
    "da_duyet": "Đã duyệt – công ty chịu phần vượt",
    "tu_choi": "Không duyệt – hướng dẫn viên bù phần vượt",
}

TY_GIA = Numeric(18, 4)


class BookingKhach(Base):
    """Một người ngồi trên chuyến.

    VÌ SAO PHẢI CÓ BẢNG NÀY

    Bảng bookings đếm đầu người bằng ba cột adl/chd/inf. Nó biết CÓ BAO NHIÊU trẻ em; nó không biết
    trẻ nào, và tuyệt nhiên không biết tuổi. Quy tắc giá theo tuổi vì thế không kiểm được: nhìn vào
    tờ quyết toán đã có bốn chữ ký, không ai xác minh được cháu nào thật sự dưới 2 tuổi.

    Và nó không có chỗ nào cho người KHÔNG phải khách. Mẫu thật có đủ cả: đoàn Phú Quốc "46 NGƯỜI LỚN
    + 3 TRẺ EM + 1 FREE + 4 NỘI BỘ"; SIN/MAL có 30 khách cộng 22 người của hai đại lý SGS và VV ngồi
    cùng chuyến mà doanh thu không thuộc Vietourist. Những người ấy ăn suất ăn thật, ngồi ghế thật,
    chịu bảo hiểm thật. Không ghi họ thì số khách trên tờ quyết toán không bao giờ khớp số ghế.

    NGÀY SINH THU Ở KHÂU ĐĂNG KÝ, KHÔNG PHẢI Ở QUYẾT TOÁN

    Đến lúc quyết toán thì khách đã đi rồi; hỏi tuổi lúc ấy là hỏi để hợp thức hoá, không phải để tính
    giá. Nên bảng này treo vào bookings, không treo vào tour_settlements.
    """
    __tablename__ = "booking_khach"
    __table_args__ = (Index("ix_bk_booking", "booking_id"), Index("ix_bk_tour", "tour_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"))
    # Lặp lại tour_id để hỏi "42 khách của chuyến này" không phải nối qua bookings. Dịch vụ ghi cả
    # hai; lệch nhau là lỗi và có phép kiểm bắt.
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    stt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ho_ten: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nhom_khach: Mapped[str | None] = mapped_column(String(20), nullable=True)
    loai_tuoi: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # NULL = CHƯA HỎI ngày sinh. Cột quyết định của quy tắc giá theo tuổi, nên NULL phải kêu lên chứ
    # không lặng lẽ tính thành người lớn: tính nhầm em bé thành người lớn là thu thừa tiền của khách,
    # và bảng vẫn cân nên không ai phát hiện.
    ngay_sinh: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Hệ thống xếp loại tại NGÀY KHỞI HÀNH rồi GHI LẠI, không tính lại mỗi lần đọc. Đứa trẻ 11 tuổi
    # rưỡi lúc đi tour sẽ 12 tuổi khi kế toán mở lại tờ quyết toán ba tháng sau; tờ đã ký không được
    # đổi số.
    tuoi_luc_di: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Giá hệ thống tính từ quy tắc, và giá thực bán. Hai cột riêng, vì chênh nhau là DỮ LIỆU chứ không
    # phải lỗi – đó là tín hiệu bảng giá đang lệch quy tắc ở đâu.
    gia_chuan: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_ban: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ly_do_khac_chuan: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Tour nước ngoài. Mã đặt chỗ là khoá tra ngược duy nhất về hãng bay khi cần đối chiếu vé – mẫu
    # SIN/MAL ghi nó ngay trên dòng khách (KCLWRD/H7ZDSV).
    so_ho_chieu: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ma_dat_cho: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # ---- Bản nâng cấp y2d8e3f0a5b97 (11/9/2026) ----
    #
    # Bốn ô mẫu ĐANG THU mà trước đây không có chỗ chứa: nhân viên gõ xong thì bộ nạp đọc rồi bỏ.
    # CCCD tách riêng khỏi so_ho_chieu – mẫu trong nước thu CCCD, mẫu nước ngoài thu hộ chiếu, và
    # hai loại giấy tờ chung một ô thì không lọc được, cũng không kiểm được độ dài.
    #
    # KHÔNG có cột "sale" ở đây: sale thuộc về PHIẾU ĐẶT (bookings.sales_id). Từ bản nâng cấp này
    # dòng khách treo đúng phiếu đặt nên tra ra được. Chép sang đây là hai chỗ giữ cùng một sự thật.
    gioi_tinh: Mapped[str | None] = mapped_column(String(10), nullable=True)
    dien_thoai: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cccd: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nguoi_sua: Mapped[str | None] = mapped_column(String(60), nullable=True)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def lech_chuan(self) -> float | None:
        """Bán khác giá chuẩn bao nhiêu. None khi thiếu một trong hai số – rỗng không phải 0."""
        if self.gia_ban is None or self.gia_chuan is None:
            return None
        return self.gia_ban - self.gia_chuan

    def co_thu(self) -> bool:
        """Người này có mang doanh thu cho Vietourist không.

        Dùng làm mẫu số của quy tắc phân bổ 'chia đều khách có thu'. Khách đại lý và khách nội bộ
        KHÔNG mang doanh thu dù họ vẫn ngồi ghế và vẫn ăn suất ăn.
        """
        return self.nhom_khach == "tra_tien" and (self.gia_ban or 0) > 0


class KhachChiPhi(Base):
    """Chi phí ĐÍCH DANH của một khách – không chia, không phân bổ.

    Tour trong nước chia chi phí chung cho từng khách bằng phép chia. Tour nước ngoài thì không chia
    được. Đo trên tệp UK: cùng một chuyến mà vé máy bay của khách này 22.435.959 đ còn khách kia
    21.903.700 đ; phí lãnh sự quán chạy từ 7.875.750 đến 8.290.750; và bốn khách không mua visa vì
    đã có sẵn.

    Ép những khoản ấy vào phép chia là làm hỏng cả hai đầu: khách đã có visa phải gánh tiền visa của
    người khác, còn người mua visa đắt thì được gánh hộ. Nên chúng là chi phí đích danh, nằm ở đây.
    """
    __tablename__ = "khach_chi_phi"
    __table_args__ = (Index("ix_kcp_khach", "khach_id"), Index("ix_kcp_tour", "tour_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    khach_id: Mapped[int] = mapped_column(ForeignKey("booking_khach.id", ondelete="CASCADE"))
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    # Mã khoản mục chi phí – cùng danh mục với dòng chi chung, xem app/services/khoan_muc_chi.py.
    # Những mã có dich_danh=True (vé máy bay, phí lãnh sự quán, dịch thuật) thuộc về bảng này.
    ma_khoan_muc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # ve_may_bay / visa / dich_thuat / qua_tang / bao_hiem / khac
    loai: Mapped[str | None] = mapped_column(String(30), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mst_ncc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    so_hoa_don: Mapped[str | None] = mapped_column(String(30), nullable=True)


class TourDoanhThuDong(Base):
    """Một dòng doanh thu của chuyến.

    HAI CÁCH GHI, MỘT HÌNH DẠNG

        Tour lẻ  : mỗi khách một dòng, có tên  (Nha Trang: 42 dòng cho 42 người)
        Tour đoàn: mỗi khoản hợp đồng một dòng (Đà Lạt: 4 dòng cho 37 người)

    Cả hai đều có đơn giá, số lượng, thuế suất – nên cùng một bảng. Dòng ứng với một khách có tên thì
    nối khach_id; dòng hợp đồng đoàn để trống.

    THU ÂM LÀ CHUYỆN BÌNH THƯỜNG, KHÔNG PHẢI LỖI NHẬP

    Mẫu Đà Lạt có "HOÀN SUẤT ĂN NGÀY CUỐI −899.999" và "HOÀN VÉ THAM QUAN −539.999", cả hai đến từ
    biên bản thanh lý hợp đồng đã ký. Chặn số âm ở đây là buộc Điều hành phải trừ lén vào dòng dương,
    và thế là mất dấu vết của việc thanh lý. Số âm được phép; cái BẮT BUỘC là cột chung_tu.

    VAT NẰM TRÊN DÒNG, KHÔNG PHẢI Ở CUỐI BẢNG

    Đoàn bán cho doanh nghiệp thì có hoá đơn GTGT: mẫu Đà Lạt ghi 100.592.592,59 trước thuế + 8% =
    108.640.000. Tour lẻ bán cho khách lẻ thì không. Cùng một hệ thống phải đỡ được cả hai, nên thuế
    suất là một cột của dòng và để rỗng được.
    """
    __tablename__ = "tour_doanh_thu_dong"
    __table_args__ = (Index("ix_tdd_tour", "tour_id"), Index("ix_tdd_khach", "khach_id"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    khach_id: Mapped[int | None] = mapped_column(ForeignKey("booking_khach.id"), nullable=True)
    loai: Mapped[str | None] = mapped_column(String(20), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    doi_tuong: Mapped[str | None] = mapped_column(String(20), nullable=True)
    don_gia_truoc_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien_truoc_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thue_suat: Mapped[float | None] = mapped_column(Float, nullable=True)
    tien_thue: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # Số hiệu biên bản thanh lý / phụ lục hợp đồng làm căn cứ. Dòng âm mà không có căn cứ thì phép
    # kiểm chặn – xem app/services/quyet_toan_lop3.py.
    chung_tu: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TourPhuongTien(Base):
    """Một chặng phương tiện của chuyến.

    VÌ SAO LÀ BẢNG CHỨ KHÔNG PHẢI MỘT CỘT

    Bảng tours đã có cột `transport` dạng chữ. Một cột không đủ: đoàn Phú Quốc đi máy bay SGN–PQC rồi
    dùng HAI xe 29 chỗ tại đảo (biển 68H04420 và 68F00897, hai tài xế khác nhau); tour UK có vé quốc
    tế cộng xe tại Anh. Mỗi chặng có nhà cung cấp riêng, giá riêng, số chỗ riêng và chứng từ riêng.

    XE NHÀ KHÁC XE THUÊ NGOÀI

    Mẫu đoàn Đà Lạt có dòng "VIETRIP 45s – 3N3D  18.000.000  CÔNG NỢ VIETRIP" nằm hẳn một sheet
    riêng. Đó là xe của đội xe trong nhóm, nên khoản ấy là công nợ nội bộ chứ không phải tiền trả cho
    bên thứ ba – hai đường hạch toán khác nhau, và khi hợp nhất báo cáo thì nó phải loại trừ. Cột
    xe_nha + vehicle_id giữ đúng chỗ đó.
    """
    __tablename__ = "tour_phuong_tien"
    __table_args__ = (Index("ix_tpt_tour", "tour_id"), Index("ix_tpt_loai", "loai"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    loai: Mapped[str] = mapped_column(String(20))
    chang: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ngay: Mapped[date | None] = mapped_column(Date, nullable=True)
    gio_di: Mapped[str | None] = mapped_column(String(10), nullable=True)
    gio_den: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Xe: biển số. Máy bay: số hiệu chuyến (9G1951). Tàu: số hiệu tàu/toa.
    so_hieu: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ma_dat_cho: Mapped[str | None] = mapped_column(String(30), nullable=True)
    nha_cung_cap: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mst_ncc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    xe_nha: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    so_cho: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_khach_su_dung: Mapped[int | None] = mapped_column(Integer, nullable=True)
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Chặng không có dòng chi là chặng chưa vào giá vốn – phép kiểm bắt được.
    dong_chi_phi_id: Mapped[int | None] = mapped_column(ForeignKey("tour_cost_lines.id"), nullable=True)
    ghi_chu: Mapped[str | None] = mapped_column(String(300), nullable=True)


class TourHdvChi(Base):
    """Một khoản hướng dẫn viên chi trên đường, và hai phép so của khoản ấy.

    Chủ tịch chốt 10/9/2026: HDV chi vượt so với dự toán của Điều hành mà KHÔNG ĐƯỢC DUYỆT thì HDV bù
    tiền vào.

    HAI PHÉP SO KHÁC NHAU, ĐỪNG LẪN

        vuot    = thực chi − chiết tính   -> vượt DỰ TOÁN. Đây là cái Chủ tịch chốt.
        con_lai = tiền ứng − thực chi     -> thừa/thiếu so với khoản đã ứng. Âm nghĩa là HDV bỏ tiền
                  túi ra trước và CÔNG TY nợ lại HDV.

    Hai chiều ngược nhau và cùng xảy ra thật. Nha Trang: HDV chi vượt chiết tính 120.000 nhưng ứng vừa
    đủ nên "Dư 0". Đoàn Đà Lạt: công ty ứng 3.300.000, HDV chi 3.696.000, còn lại −396.000 – công ty
    nợ HDV. Gộp hai cột làm một là có lúc đi đòi tiền người đang được công ty nợ.

    IM LẶNG KHÔNG ĐƯỢC TÍNH LÀ ĐỒNG Ý

    Mặc định trang_thai_duyet là "cho_duyet", và tờ quyết toán không đóng được khi còn dòng chờ duyệt.
    Nếu im lặng mặc nhiên thành đã duyệt thì quy định chỉ có hiệu lực với những người có ai đó chịu
    bấm nút – tức là không có hiệu lực.

    PHẦN MỀM KHÔNG TỰ TRỪ LƯƠNG

    Từ chối thì sinh phai_thu_hdv – một con số chờ, mang tên người. Kế toán mới là người trừ, và phải
    có điều khoản trong quy chế hướng dẫn viên thì mới cưỡng chế được.
    """
    __tablename__ = "tour_hdv_chi"
    __table_args__ = (Index("ix_thc_tour", "tour_id"), Index("ix_thc_duyet", "trang_thai_duyet"))

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    phan_cong_id: Mapped[int | None] = mapped_column(ForeignKey("guide_assignments.id"), nullable=True)
    noi_dung: Mapped[str | None] = mapped_column(String(200), nullable=True)
    don_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_luong: Mapped[float | None] = mapped_column(Float, nullable=True)
    thanh_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_ung: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    tien_te: Mapped[str | None] = mapped_column(String(3), nullable=True)
    so_tien_goc: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TY_GIA, nullable=True)
    ngay_ty_gia: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Tiền của KHÁCH, không phải của công ty. Mẫu UK: "TL thu của khách 126 GBP (mua dùm khách vé
    # tham quan)". Khoản ấy không được vào giá vốn, và cũng không được vào doanh thu.
    thu_ho_khach: Mapped[int | None] = mapped_column(Integer, nullable=True, server_default="0")
    # NULL nghĩa là HDV chi một khoản KHÔNG CÓ trong chiết tính – nặng hơn chi vượt, vì không có gì
    # để so. Trường hợp ấy phải duyệt toàn bộ số tiền, không phải phần chênh.
    dong_chiet_tinh_id: Mapped[int | None] = mapped_column(ForeignKey("tour_cost_lines.id"), nullable=True)
    thanh_tien_chiet_tinh: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    vuot: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    con_lai: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # phieu_thu / hoa_don / khong_co. Mẫu Đà Lạt ghi rõ từng dòng, và đó là căn cứ để kế toán hoàn ứng.
    loai_chung_tu: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trang_thai_duyet: Mapped[str] = mapped_column(String(20), default="cho_duyet",
                                                  server_default="cho_duyet", nullable=False)
    nguoi_duyet: Mapped[str | None] = mapped_column(String(60), nullable=True)
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_duyet: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phai_thu_hdv: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguoi_nhap: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nhap_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SuaSauKy(Base):
    """Một lần sửa tờ quyết toán sau khi tờ ấy đã có chữ ký.

    Chủ tịch chốt 10/9/2026: chỉ Trưởng phòng Điều hành (tp_dh) và Phó Tổng Giám đốc đoàn (ptgd_doan)
    sửa được, và phải để lại dấu vết cùng lý do.

    MỖI LẦN MỘT DÒNG, KHÔNG GHI ĐÈ, KHÔNG XOÁ

    Kể cả Chủ tịch cũng không xoá dòng ở bảng này. Sửa sai thì sửa tiếp và ghi tiếp. Một sổ dấu vết mà
    người có quyền cao nhất xoá được thì không phải sổ dấu vết.

    VÌ SAO gia_tri_cu / gia_tri_moi LÀ Text CHỨ KHÔNG PHẢI TIEN

    Bảng này ghi được cả sửa số lẫn sửa chữ, và sửa chữ mới là phần hay sai. Đo trên hai mẫu: tờ Nha
    Trang sai ngày đi (07/07 trong khi ba nguồn khác nói 10/07) và sai số khách (ghi 44, đếm được 42).
    Tờ đoàn Đà Lạt mang HAI mã tour khác nhau trong cùng một tệp (MICEDL3N2D.03300526 ở đầu bảng,
    MICEDL3N3D.04040626 ở sheet chi phí) và các dòng chi ghi ngày 30/05–01/06 trong khi đầu bảng ghi
    khởi hành 04/06 – dấu vết của một tệp chép lại từ chuyến trước mà chưa sửa hết.

    Ép kiểu tiền là tự loại bỏ đúng những lỗi đã tìm thấy trên mẫu thật.
    """
    __tablename__ = "sua_sau_ky"
    __table_args__ = (Index("ix_ssk_tour", "tour_id"), Index("ix_ssk_bang", "bang", "ban_ghi_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"))
    bang: Mapped[str] = mapped_column(String(60))
    ban_ghi_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    truong: Mapped[str | None] = mapped_column(String(60), nullable=True)
    gia_tri_cu: Mapped[str | None] = mapped_column(Text, nullable=True)
    gia_tri_moi: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Bắt buộc, và dịch vụ từ chối lý do dưới 10 ký tự: "sửa" không phải một lý do, "sửa lại" cũng
    # không. Ô lý do nhận được một chữ thì sổ dấu vết đầy những chữ vô nghĩa, và người đọc thôi mở.
    ly_do: Mapped[str] = mapped_column(String(300))
    nguoi_sua: Mapped[str] = mapped_column(String(60))
    vai_tro: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sua_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
