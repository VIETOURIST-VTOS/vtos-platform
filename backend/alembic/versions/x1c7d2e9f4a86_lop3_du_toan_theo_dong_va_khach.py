"""Lớp 3: hai hình thức tour, dòng khách, phương tiện, HDV chi có duyệt, dấu vết sửa sau ký.

HAI HÌNH THỨC, KHÔNG PHẢI BA – Chủ tịch chốt 11/9/2026

    trong_nuoc  : tour nội địa và tour đoàn nội địa
    nuoc_ngoai  : tour lẻ và tour đoàn outbound

Ban đầu định dựng ba (nội địa / lẻ outbound / đoàn), nhưng đo trên ba mẫu thật thì "đoàn" không phải
một hình thức riêng: đoàn Phú Quốc (MICEPQ3N2D.03.200226) là tour TRONG NƯỚC đi MÁY BAY, còn tour lẻ
Nha Trang là tour trong nước đi Ô TÔ. Cái khác nhau giữa chúng là PHƯƠNG TIỆN, không phải hình thức.
Dựng "đoàn" thành hình thức thứ ba là nhầm hai trục làm một.

Cái thật sự chia đôi là biên giới:

    trong nước  -> một đồng tiền, không visa, không vé quốc tế
    nước ngoài  -> nhiều đồng tiền có tỷ giá, phí lãnh sự quán từng khách một giá, vé quốc tế từng
                   khách một giá, và khách của đại lý ngồi ghép

PHƯƠNG TIỆN LÀ MỘT BẢNG, KHÔNG PHẢI MỘT CỘT

Bảng tours đã có cột `transport` dạng chữ. Một cột không đủ: đoàn Phú Quốc đi máy bay SGN–PQC rồi
dùng HAI xe 29 chỗ tại đảo; tour UK có vé quốc tế cộng xe tại Anh. Mỗi chặng có nhà cung cấp riêng,
giá riêng, số chỗ riêng, và chứng từ riêng. Nên mỗi chặng là một dòng ở tour_phuong_tien, nối thẳng
vào dòng chi phí của chính nó.

BỐN NHÓM KHÁCH TÁCH RIÊNG KHỎI BA BẬC TUỔI

Chủ tịch chốt 11/9/2026: ghi hết mọi người ngồi trên chuyến, tách bốn nhóm. Bốn nhóm ấy là chuyện
AI TRẢ TIỀN, còn ba bậc tuổi là chuyện TÍNH GIÁ BAO NHIÊU – hai trục khác nhau, nên hai cột:

    nhom_khach : tra_tien / mien_phi / noi_bo / dai_ly
    loai_tuoi  : nguoi_lon / tre_em / em_be

Một cột không nói được "trẻ em của đại lý". Đo trên mẫu thật: đoàn Phú Quốc có "46 NGƯỜI LỚN + 3 TRẺ
EM + 1 FREE + 4 NỘI BỘ"; SIN/MAL có 30A + 01 CHD + 01 TL cộng thêm 22 khách của hai đại lý SGS và VV
ngồi cùng chuyến mà doanh thu không thuộc Vietourist.

CHI PHÍ RIÊNG CỦA TỪNG KHÁCH – bảng khach_chi_phi

Tour trong nước chia chi phí chung cho từng khách bằng phép chia. Tour nước ngoài thì không chia được:
trong tệp UK, cùng một chuyến mà vé máy bay của khách này 22.435.959 đ còn khách kia 21.903.700 đ, phí
lãnh sự quán chạy từ 7.875.750 đến 8.290.750, và bốn khách không mua visa vì đã có sẵn. Đó là chi phí
ĐÍCH DANH, không phải chi phí chung – ép vào phép chia là làm hỏng cả hai đầu.

QUY ƯỚC TIỀN

Mọi cột tiền là Numeric(18,2) theo chuẩn V9 và để NULL được, theo quy ước K2: rỗng nghĩa là CHƯA CÓ
SỐ, khác hẳn 0 đồng.

Revision ID: x1c7d2e9f4a86
Revises: v14b6e9c2a7d31
"""
from alembic import op
import sqlalchemy as sa

revision = "x1c7d2e9f4a86"
# SỬA 11/9/2026 (làn Phân quyền, Chủ tịch giao): bản đầu nối vào "v14b6e9c2a7d31" – migration của
# V7 (sự cố tour, hồ sơ kiểm toán). Tệp ấy KHÔNG có trong thư mục alembic/versions vì V7 còn nằm ở
# nhánh chưa nhập. Container khởi động chạy `alembic upgrade head` và dừng ở KeyError trước khi API
# lên được – đúng lỗi đã giết lần triển khai ngày 10/9.
#
# Nối lại vào đầu mạch đang có. Kiểm ba điều trước khi đổi, vì đổi thứ tự migration của người khác
# chỉ an toàn khi liên kết cũ là THỨ TỰ chứ không phải PHỤ THUỘC:
#   · bản này không nhắc tới bảng nào của V7 (su_co_tour, ho_so_kiem_toan): 0 lần
#   · sáu bảng nó tạo không trùng bảng nào của Lớp 2, VPM-5, VPM-7
#   · nó thêm cột vào tour_settlements, mà Lớp 2 không thêm cột nào vào bảng ấy – không đụng cột
#
# Khi V7 được nhập về sau: v14b6e9c2a7d31 phải nối vào ĐẦU MẠCH LÚC ẤY, không nối lại vào
# v11d8e4b6a2f79 như hiện nay – nối vào v11 là lập tức có hai đầu.
down_revision = "y2c6e0f4b8d3"
branch_labels = None
depends_on = None

TIEN = sa.Numeric(18, 2)


def _co(ten: str) -> bool:
    return ten in set(sa.inspect(op.get_bind()).get_table_names())


def _co_cot(bang: str, cot: str) -> bool:
    if not _co(bang):
        return False
    return cot in {c["name"] for c in sa.inspect(op.get_bind()).get_columns(bang)}


def _them(bang: str, ten: str, kieu) -> None:
    if not _co_cot(bang, ten):
        op.add_column(bang, sa.Column(ten, kieu, nullable=True))


def upgrade() -> None:
    # --------------------------------------------- 0. hai cột danh mục dùng cho cả phân hệ
    # Tên pháp nhân của nhà cung cấp: tên trên HOÁ ĐƠN, khác tên giao dịch. Đo trên danh mục thật của
    # công ty (280 nhà cung cấp): "RESORT VĨNH HY" xuất hoá đơn dưới tên "CTY TNHH PHÁT HOÀNG LONG".
    # Gộp hai tên vào một cột thì hoặc mất tên để tra, hoặc mất tên để kê khai thuế.
    _them("suppliers", "ten_phap_nhan", sa.String(300))

    # Mã khoản mục chi phí – xem danh mục ở app/services/khoan_muc_chi.py.
    #
    # Trước cột này, "nội dung" của dòng chi là ô CHỮ TỰ DO, và trên tám tệp quyết toán thật thì cùng
    # một khoản có nhiều tên: LAND / LAND MCB / Landtour ADL / Giá land. Chữ tự do thì không cộng được
    # theo khoản mục, nên câu "cả năm công ty chi bao nhiêu tiền khách sạn" không có câu trả lời.
    _them("tour_cost_lines", "ma_khoan_muc", sa.String(40))
    _them("khach_chi_phi", "ma_khoan_muc", sa.String(40))

    # ------------------------------------------------------------- A. hình thức tour
    # KHÁC HẲN cột tour_type sẵn có: tour_type phân biệt tour trọn gói với dịch vụ lẻ (package /
    # non_package). Cột này phân biệt trong nước với nước ngoài – hai trục khác nhau, và một chuyến
    # có cả hai giá trị cùng lúc.
    _them("tours", "hinh_thuc", sa.String(20))

    # -------------------------------------------- B. cửa nạp nối vào chuyến thật bằng khoá
    # Trước bản này tour_settlements khớp với tours bằng CHUỖI mã tour. Chuỗi thì sai chính tả được,
    # thừa dấu cách được, và không có gì bắt lỗi. NULL nghĩa là chưa tra ra chuyến – khác hẳn
    # "không có chuyến".
    if not _co_cot("tour_settlements", "tour_id"):
        op.add_column("tour_settlements",
                      sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True))
        op.create_index("ix_tour_settlements_tour", "tour_settlements", ["tour_id"])

    # ------------------------------------ C. dự toán và chiết tính cùng một hình dạng, có ngoại tệ
    # Cột budget đã có sẵn từ 7f1a2b3c4d5e nên dự toán và thực chi nằm CÙNG MỘT DÒNG: so được từng
    # khoản, không phải so hai bảng. Bốn cột đầu là thứ mẫu Điều hành có mà VTOS chưa có; bốn cột
    # sau là cho tour nước ngoài.
    for ten, kieu in [
        # Giữ ngày ở dạng CHỮ đúng như tệp gốc ("10/07", "Ngày 1", "10-12/07"). Ép về kiểu ngày là
        # ép người nhập chuẩn hoá ngay tại chỗ, và họ sẽ bỏ trống cho nhanh.
        ("ngay", sa.String(60)),
        # Nhóm khoản mục của sheet CTT: "A. LAND TOUR", "B. TRẺ EM", "C. CHI PHÍ KHÁC". Chính chỗ
        # cộng nhóm B là nơi tệp Nha Trang bỏ sót 210.000 đ mà mọi tầng phía sau vẫn cân.
        ("nhom", sa.String(80)),
        # nguoi_lon / tre_em / em_be / chung. KHÁC cost_kind: cost_kind nói chi phí này có chia theo
        # đầu khách không, doi_tuong nói chia cho AI.
        ("doi_tuong", sa.String(20)),
        # Quy tắc phân bổ phải KHAI ra, không giấu trong công thức Excel. Xem BANG_PHAN_BO trong
        # app/services/gia_khach.py. Rỗng nghĩa là chưa ai chọn – máy không đoán hộ.
        ("quy_tac_phan_bo", sa.String(30)),
        # --- ngoại tệ ---
        # Số tiền GỐC bằng đồng tiền gốc, giữ nguyên không quy đổi. Cột actual/budget vẫn là VND.
        ("tien_te", sa.String(3)),
        ("so_tien_goc", TIEN),
        ("ty_gia", sa.Numeric(18, 4)),
        # Tỷ giá lấy tại NGÀY CHI THẬT – Chủ tịch chốt 11/9/2026. Ghi lại ngày ấy để tra ngược được
        # về sao kê ngân hàng. Tệp UK có HAI tỷ giá GBP khác nhau trong cùng một tệp (36.000 ở sheet
        # chiết tính, 35.944 ở sheet quyết toán); riêng trên giá land 692,34 GBP × 43 khách, 56 đồng
        # chênh ấy là 1.667.155 đ. Không ghi ngày thì không bao giờ phân xử được số nào đúng.
        ("ngay_ty_gia", sa.Date()),
        # --- thuế GTGT đầu vào ---
        # Cột vat_hoa_don (tiền thuế) đã có từ 8de308e27b31, nhưng THIẾU thuế suất. Mẫu đoàn Đà Lạt
        # có cả ba mức trên cùng một chuyến: 8% cho nhà hàng và lưu trú, 0% cho banner và ăn nội bộ.
        # Không lưu thuế suất thì không dựng lại được bảng kê thuế GTGT đầu vào từ dữ liệu.
        ("thue_suat", sa.Float()),
        # Số tiền của khoản này KHÔNG có hoá đơn. Khác NULL ở so_hoa_don: NULL là chưa ai nhập, cột
        # này là đã xác nhận KHÔNG CÓ. Mẫu Đà Lạt có hẳn một cột như vậy, và đó chính là con số
        # Chủ tịch cần thấy – phần giá vốn không khấu trừ được thuế.
        ("khong_hoa_don", TIEN),
    ]:
        _them("tour_cost_lines", ten, kieu)

    # --------------------------------------------------------- C2. dòng doanh thu của chuyến
    # VÌ SAO DOANH THU CŨNG PHẢI THÀNH DÒNG
    #
    # Tour lẻ bán cho khách lẻ: doanh thu là 42 dòng khách có tên (mẫu Nha Trang).
    # Tour đoàn bán cho doanh nghiệp: doanh thu là 4 DÒNG HỢP ĐỒNG cho 37 người (mẫu Đà Lạt) –
    #     "NGƯỜI LỚN × 25", "TRẺ EM × 10", rồi hai dòng ÂM từ biên bản thanh lý.
    #
    # Hai cách ghi khác nhau, nhưng cùng một hình: mỗi dòng có đơn giá, số lượng, thuế suất. Dòng
    # nào ứng với một khách có tên thì nối vào khach_id; dòng hợp đồng đoàn thì để trống. Nhờ vậy
    # một bảng đỡ được cả hai, và báo cáo toàn công ty cộng được cả hai.
    #
    # THU ÂM LÀ CHUYỆN BÌNH THƯỜNG, KHÔNG PHẢI LỖI NHẬP
    #
    # Mẫu Đà Lạt có "HOÀN SUẤT ĂN NGÀY CUỐI -899.999" và "HOÀN VÉ THAM QUAN -539.999", cả hai đến từ
    # biên bản thanh lý hợp đồng đã ký. Chặn số âm ở đây là buộc Điều hành phải trừ lén vào dòng
    # dương – và thế là mất dấu vết của việc thanh lý.
    if not _co("tour_doanh_thu_dong"):
        op.create_table(
            "tour_doanh_thu_dong",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
            sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=True),
            # Có tên người thì nối; dòng hợp đồng đoàn thì để trống.
            sa.Column("khach_id", sa.Integer(),
                      sa.ForeignKey("booking_khach.id"), nullable=True),
            # hop_dong / thanh_ly / phu_thu / charge_huy / thu_khac
            sa.Column("loai", sa.String(20), nullable=True),
            sa.Column("noi_dung", sa.String(200), nullable=True),
            sa.Column("doi_tuong", sa.String(20), nullable=True),
            sa.Column("don_gia_truoc_thue", TIEN, nullable=True),
            sa.Column("so_luong", sa.Float(), nullable=True),
            sa.Column("thanh_tien_truoc_thue", TIEN, nullable=True),
            sa.Column("thue_suat", sa.Float(), nullable=True),
            sa.Column("tien_thue", TIEN, nullable=True),
            sa.Column("thanh_tien", TIEN, nullable=True),
            # Số hiệu biên bản thanh lý / phụ lục hợp đồng làm căn cứ cho dòng âm.
            sa.Column("chung_tu", sa.String(120), nullable=True),
            sa.Column("tien_te", sa.String(3), nullable=True),
            sa.Column("so_tien_goc", TIEN, nullable=True),
            sa.Column("ty_gia", sa.Numeric(18, 4), nullable=True),
            sa.Column("ngay_ty_gia", sa.Date(), nullable=True),
            sa.Column("ghi_chu", sa.String(300), nullable=True),
            sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_tdd_tour", "tour_doanh_thu_dong", ["tour_id"])
        op.create_index("ix_tdd_khach", "tour_doanh_thu_dong", ["khach_id"])

    # ------------------------------------------------------------------- D. dòng khách của booking
    if not _co("booking_khach"):
        op.create_table(
            "booking_khach",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("booking_id", sa.Integer(),
                      sa.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False),
            # Lặp lại tour_id để hỏi "42 khách của chuyến này" không phải nối qua bookings.
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
            sa.Column("stt", sa.Integer(), nullable=True),
            sa.Column("ho_ten", sa.String(200), nullable=True),
            # AI TRẢ TIỀN: tra_tien / mien_phi / noi_bo / dai_ly
            sa.Column("nhom_khach", sa.String(20), nullable=True),
            # TÍNH GIÁ BAO NHIÊU: nguoi_lon / tre_em / em_be
            sa.Column("loai_tuoi", sa.String(20), nullable=True),
            # NULL = CHƯA HỎI ngày sinh. Cột quyết định của quy tắc giá theo tuổi, nên NULL phải kêu
            # lên chứ không lặng lẽ tính thành người lớn: tính nhầm em bé thành người lớn là thu
            # thừa tiền của khách, và bảng vẫn cân nên không ai phát hiện.
            sa.Column("ngay_sinh", sa.Date(), nullable=True),
            sa.Column("tuoi_luc_di", sa.Integer(), nullable=True),
            sa.Column("gia_chuan", TIEN, nullable=True),
            sa.Column("gia_ban", TIEN, nullable=True),
            sa.Column("ly_do_khac_chuan", sa.String(200), nullable=True),
            # Tour nước ngoài: hộ chiếu và mã đặt chỗ hàng không. Mã đặt chỗ là khoá tra ngược duy
            # nhất về hãng bay khi cần đối chiếu vé.
            sa.Column("so_ho_chieu", sa.String(30), nullable=True),
            sa.Column("ma_dat_cho", sa.String(30), nullable=True),
            sa.Column("nguoi_sua", sa.String(60), nullable=True),
            sa.Column("sua_luc", sa.DateTime(), nullable=True),
            sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_bk_booking", "booking_khach", ["booking_id"])
        op.create_index("ix_bk_tour", "booking_khach", ["tour_id"])

    # ------------------------------------------------------ E. chi phí ĐÍCH DANH của từng khách
    if not _co("khach_chi_phi"):
        op.create_table(
            "khach_chi_phi",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("khach_id", sa.Integer(),
                      sa.ForeignKey("booking_khach.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=True),
            # ve_may_bay / visa / dich_thuat / qua_tang / bao_hiem / khac
            sa.Column("loai", sa.String(30), nullable=True),
            sa.Column("noi_dung", sa.String(200), nullable=True),
            sa.Column("so_tien", TIEN, nullable=True),
            sa.Column("tien_te", sa.String(3), nullable=True),
            sa.Column("so_tien_goc", TIEN, nullable=True),
            sa.Column("ty_gia", sa.Numeric(18, 4), nullable=True),
            sa.Column("ngay_ty_gia", sa.Date(), nullable=True),
            sa.Column("nha_cung_cap", sa.String(200), nullable=True),
            sa.Column("mst_ncc", sa.String(20), nullable=True),
            sa.Column("so_hoa_don", sa.String(30), nullable=True),
            sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_kcp_khach", "khach_chi_phi", ["khach_id"])
        op.create_index("ix_kcp_tour", "khach_chi_phi", ["tour_id"])

    # --------------------------------------------------------------- F. phương tiện từng chặng
    if not _co("tour_phuong_tien"):
        op.create_table(
            "tour_phuong_tien",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
            # o_to / may_bay / tau_hoa / tau_thuy / khac
            sa.Column("loai", sa.String(20), nullable=False),
            sa.Column("chang", sa.String(120), nullable=True),      # "SGN-PQC", "HCM - Nha Trang"
            sa.Column("ngay", sa.Date(), nullable=True),
            sa.Column("gio_di", sa.String(10), nullable=True),
            sa.Column("gio_den", sa.String(10), nullable=True),
            # Xe: biển số. Máy bay: số hiệu chuyến. Tàu: số hiệu tàu/toa.
            sa.Column("so_hieu", sa.String(40), nullable=True),
            sa.Column("ma_dat_cho", sa.String(30), nullable=True),
            sa.Column("nha_cung_cap", sa.String(200), nullable=True),
            sa.Column("mst_ncc", sa.String(20), nullable=True),
            # Xe nhà (đội xe Vietourist) hay thuê ngoài. Xe nhà thì giá vốn đi qua phân hệ đội xe,
            # không phải một khoản chi trả cho bên thứ ba – hai đường hạch toán khác nhau.
            sa.Column("xe_nha", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=True),
            sa.Column("so_cho", sa.Integer(), nullable=True),
            sa.Column("so_khach_su_dung", sa.Integer(), nullable=True),
            sa.Column("don_gia", TIEN, nullable=True),
            sa.Column("so_luong", sa.Float(), nullable=True),
            sa.Column("thanh_tien", TIEN, nullable=True),
            sa.Column("tien_te", sa.String(3), nullable=True),
            sa.Column("so_tien_goc", TIEN, nullable=True),
            sa.Column("ty_gia", sa.Numeric(18, 4), nullable=True),
            sa.Column("ngay_ty_gia", sa.Date(), nullable=True),
            # Nối vào dòng chi phí của chính chặng này. Chặng không có dòng chi là chặng chưa vào
            # giá vốn – phép kiểm bắt được.
            sa.Column("dong_chi_phi_id", sa.Integer(),
                      sa.ForeignKey("tour_cost_lines.id"), nullable=True),
            sa.Column("ghi_chu", sa.String(300), nullable=True),
            sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_tpt_tour", "tour_phuong_tien", ["tour_id"])
        op.create_index("ix_tpt_loai", "tour_phuong_tien", ["loai"])

    # ----------------------------------------------------------------- G. HDV chi trên đường
    if not _co("tour_hdv_chi"):
        op.create_table(
            "tour_hdv_chi",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
            sa.Column("phan_cong_id", sa.Integer(),
                      sa.ForeignKey("guide_assignments.id"), nullable=True),
            sa.Column("noi_dung", sa.String(200), nullable=True),
            sa.Column("don_gia", TIEN, nullable=True),
            sa.Column("so_luong", sa.Float(), nullable=True),
            sa.Column("thanh_tien", TIEN, nullable=True),
            sa.Column("tien_ung", TIEN, nullable=True),
            # Tour nước ngoài: HDV ứng và chi bằng ngoại tệ. Tệp UK ghi công nợ TL bằng cả GBP lẫn
            # USD trong cùng một bảng, và có cả khoản "TL thu của khách 126 GBP (mua dùm khách vé
            # tham quan)" – tiền của khách chứ không phải của công ty.
            sa.Column("tien_te", sa.String(3), nullable=True),
            sa.Column("so_tien_goc", TIEN, nullable=True),
            sa.Column("ty_gia", sa.Numeric(18, 4), nullable=True),
            sa.Column("ngay_ty_gia", sa.Date(), nullable=True),
            sa.Column("thu_ho_khach", sa.Integer(), nullable=True, server_default="0"),
            # Dòng chiết tính tương ứng. NULL nghĩa là HDV chi một khoản KHÔNG CÓ trong chiết tính –
            # nặng hơn chi vượt, vì không có gì để so.
            sa.Column("dong_chiet_tinh_id", sa.Integer(),
                      sa.ForeignKey("tour_cost_lines.id"), nullable=True),
            sa.Column("thanh_tien_chiet_tinh", TIEN, nullable=True),
            # HAI PHÉP SO KHÁC NHAU, ĐỪNG LẪN:
            #
            #   vuot     = thực chi - chiết tính   -> vượt DỰ TOÁN. Đây là cái Chủ tịch chốt: vượt
            #              mà không được duyệt thì HDV bù tiền vào.
            #   con_lai  = tiền ứng - thực chi     -> tiền THỪA/THIẾU so với khoản đã ứng. Âm nghĩa
            #              là HDV đã bỏ tiền túi ra trước và CÔNG TY nợ lại HDV.
            #
            # Hai chiều ngược nhau và cùng xảy ra thật. Mẫu Nha Trang: HDV chi vượt chiết tính
            # 120.000 nhưng ứng vừa đủ nên "Dư 0". Mẫu đoàn Đà Lạt: công ty ứng 3.300.000, HDV chi
            # 3.696.000, còn lại -396.000 – công ty nợ HDV. Gộp hai cột làm một là lúc thì đòi tiền
            # người đang được công ty nợ.
            sa.Column("vuot", TIEN, nullable=True),
            sa.Column("con_lai", TIEN, nullable=True),
            # Loại chứng từ của khoản chi: phieu_thu / hoa_don / khong_co. Mẫu Đà Lạt ghi rõ từng
            # dòng, và đó là căn cứ để kế toán hoàn ứng.
            sa.Column("loai_chung_tu", sa.String(20), nullable=True),
            # Im lặng KHÔNG được tính là đồng ý: mặc định cho_duyet, và tờ quyết toán không đóng
            # được khi còn dòng chờ duyệt.
            sa.Column("trang_thai_duyet", sa.String(20), nullable=False, server_default="cho_duyet"),
            sa.Column("nguoi_duyet", sa.String(60), nullable=True),
            sa.Column("duyet_luc", sa.DateTime(), nullable=True),
            sa.Column("ly_do_duyet", sa.String(300), nullable=True),
            # Từ chối thì sinh khoản phải thu mang tên HDV. KHÔNG tự trừ lương: phần mềm tính đúng
            # và lưu dấu vết, kế toán mới là người trừ, và phải có quy chế HDV thì mới cưỡng chế được.
            sa.Column("phai_thu_hdv", TIEN, nullable=True),
            sa.Column("nguoi_nhap", sa.String(60), nullable=True),
            sa.Column("nhap_luc", sa.DateTime(), nullable=True),
            sa.Column("phien_ban", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_thc_tour", "tour_hdv_chi", ["tour_id"])
        op.create_index("ix_thc_duyet", "tour_hdv_chi", ["trang_thai_duyet"])

    # --------------------------------------------------------------- H. dấu vết sửa sau khi ký
    if not _co("sua_sau_ky"):
        op.create_table(
            "sua_sau_ky",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
            sa.Column("bang", sa.String(60), nullable=False),
            sa.Column("ban_ghi_id", sa.Integer(), nullable=True),
            sa.Column("truong", sa.String(60), nullable=True),
            # Text chứ không phải TIEN: bảng này ghi được cả sửa số lẫn sửa chữ. Tờ Nha Trang sai cả
            # ngày đi (07/07 trong khi ba nguồn khác nói 10/07) lẫn số khách (ghi 44, đếm được 42),
            # không chỉ sai tiền.
            sa.Column("gia_tri_cu", sa.Text(), nullable=True),
            sa.Column("gia_tri_moi", sa.Text(), nullable=True),
            # Bắt buộc, và dịch vụ từ chối lý do dưới 10 ký tự. "sửa" không phải một lý do.
            sa.Column("ly_do", sa.String(300), nullable=False),
            sa.Column("nguoi_sua", sa.String(60), nullable=False),
            sa.Column("vai_tro", sa.String(30), nullable=True),
            sa.Column("sua_luc", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_ssk_tour", "sua_sau_ky", ["tour_id"])
        op.create_index("ix_ssk_bang", "sua_sau_ky", ["bang", "ban_ghi_id"])


def downgrade() -> None:
    for t in ("sua_sau_ky", "tour_hdv_chi", "tour_phuong_tien", "khach_chi_phi", "booking_khach"):
        if _co(t):
            op.drop_table(t)
    for c in ("ngay_ty_gia", "ty_gia", "so_tien_goc", "tien_te",
              "quy_tac_phan_bo", "doi_tuong", "nhom", "ngay"):
        if _co_cot("tour_cost_lines", c):
            op.drop_column("tour_cost_lines", c)
    if _co_cot("tour_settlements", "tour_id"):
        op.drop_index("ix_tour_settlements_tour", table_name="tour_settlements")
        op.drop_column("tour_settlements", "tour_id")
    if _co_cot("tours", "hinh_thuc"):
        op.drop_column("tours", "hinh_thuc")
