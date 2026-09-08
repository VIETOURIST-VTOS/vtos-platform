"""V2 – bản nháp do máy đọc từ ảnh chứng từ (lệnh giao việc 08/9/2026).

Cửa 3 của khuôn ba cửa. Điều làm nó khác hai cửa kia không phải là mô hình ngôn ngữ, mà là chỗ CON SỐ
DỪNG LẠI: máy đọc xong thì số nằm ở bảng này, không nằm ở bảng đích. Nó chỉ sang bảng đích khi một
người mở ra, sửa chỗ máy đọc sai, và bấm xác nhận – và lúc đó nó đi đúng cửa 1, qua đúng bộ kiểm của
cửa 1, không có đường riêng.

VÌ SAO PHẢI CÓ BẢNG NÀY THAY VÌ GHI THẲNG VỚI MỘT CỜ "chờ duyệt" TRÊN BẢNG ĐÍCH

Một cờ trên bảng đích là một lời hứa rằng mọi truy vấn về sau sẽ nhớ lọc nó ra. Báo cáo công nợ, sổ
cái, bảng lãi lỗ, tệp xuất cho kiểm toán – chỉ cần MỘT chỗ quên điều kiện lọc là số máy đọc chưa ai
nhìn đã nằm trong một con số công bố. Bảng riêng thì cái quên đó không xảy ra được: không báo cáo nào
đọc bảng này, vì không báo cáo nào biết nó tồn tại.

BA ĐIỀU BẢNG NÀY GHI MÀ NƠI KHÁC KHÔNG GHI ĐƯỢC

  1. MÁY ĐỌC RA GÌ, TRƯỚC KHI NGƯỜI SỬA. `so_may_doc` giữ nguyên văn kết quả của mô hình và không bao
     giờ bị ghi đè. Không có nó thì không đo được tỷ lệ trường phải sửa – mà đó chính là con số quyết
     định có hạ mức AI hay không (>20% theo quyết định 08/9), và là con số duy nhất nói được mô hình
     đang tốt lên hay xấu đi.
  2. NGƯỜI NÀO BẤM. Người xác nhận chịu trách nhiệm về con số y như người gõ tay. Ghi tên ở đây, và
     ghi cả ở nhật ký nạp của cửa 1 – hai chỗ, vì hai câu hỏi khác nhau: "ai chịu trách nhiệm dòng
     này" và "dòng này vào hệ thống bằng đường nào".
  3. ẢNH GỐC. `attachment_id` trỏ về kho tệp, không lưu lại ảnh lần thứ hai. Sau này có tranh chấp thì
     mở đúng tấm ảnh mà máy đã nhìn, không phải một bản sao nào đó.

MỘT ĐIỀU BẢNG NÀY CỐ Ý KHÔNG LÀM: không có trạng thái "máy tự xác nhận". Nhóm tác vụ doc_chung_tu
trong bảng quyền AI cao nhất là mức 2 – soạn nháp. Kể cả khi ai đó sửa bảng quyền lên mức 3, mã ở
app/services/doc_chung_tu.py vẫn không có nhánh nào ghi thẳng vào bảng đích.
"""
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Boolean, ForeignKey, Index, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


# Bốn loại chứng từ mở trước, theo lệnh 08/9: khối lượng lớn nhất và khuôn ổn định nhất. Mỗi loại trỏ
# về ĐÚNG MỘT bộ nạp đã có – cửa 3 không có bảng đích riêng, đó là cả điểm của khuôn ba cửa.
LOAI_CHUNG_TU = {
    "hoa_don_gtgt": {
        "ten": "Hóa đơn GTGT đầu vào",
        "bo_nap": "hoa_don_dau_vao",
        "doi_tuong_tep": "hoa_don",
        "truong": ("mst_nguoi_ban", "ten_nguoi_ban", "ky_hieu", "so_hoa_don", "ngay_hd",
                   "noi_dung", "tien_truoc_thue", "thue_suat", "tien_thue", "tong_tien"),
    },
    "sao_ke_anh": {
        "ten": "Sao kê ngân hàng dạng ảnh / PDF",
        "bo_nap": "sao_ke_ngan_hang",
        "doi_tuong_tep": "sao_ke",
        "truong": ("ma_gd", "ngan_hang", "so_tai_khoan", "thoi_diem", "loai", "so_tien",
                   "noi_dung", "ma_tham_chieu"),
    },
    "bang_ke_chuyen_xe": {
        "ten": "Bảng kê chi phí chuyến xe",
        "bo_nap": "chuyen_xe",
        "doi_tuong_tep": "chuyen_xe",
        "truong": ("ma_phieu", "bien_so", "ten_tour", "ngay_di", "ngay_ve", "km_dau", "km_cuoi",
                   "doanh_thu", "tien_dau", "so_lit", "cau_duong", "cong_tac_phi"),
    },
    "hoa_don_dau": {
        "ten": "Hóa đơn / phiếu đổ dầu",
        "bo_nap": "nhien_lieu",
        "doi_tuong_tep": "chuyen_xe",
        "truong": ("ma_gd", "thoi_diem", "bien_so", "the_4so", "so_tien", "lit", "mo_ta"),
    },
}

# CẤM ĐỌC BẰNG MÁY, và cấm ở tầng mã chứ không ở tầng cấu hình.
#
# Lệnh giao việc 08/9 xếp bảng lương và bảng bảo hiểm vào nhóm bốn loại chứng từ mở trước. Chủ tịch
# quyết ngược lại ngay trong ngày: "được, nhưng LOẠI TRỪ BẢNG LƯƠNG". Lý do đứng vững hơn cả sự tiện
# lợi: bảng lương và bảng bảo hiểm là thu nhập của từng người – dữ liệu cá nhân theo Nghị định
# 13/2023 – và đưa chúng qua một mô hình ngôn ngữ là một lần chuyển dữ liệu cá nhân ra ngoài mà không
# ai trong danh sách đó đồng ý.
#
# Ghi thành hằng số ở đây, và có phép thử canh, để lần triển khai nào cũng có mặt. Người vào sau muốn
# bỏ nó thì phải sửa mã và phải giải thích trong một lần xem lại mã – không bỏ được bằng cách gạt một
# công tắc trên màn hình lúc 11 giờ đêm.
CAM_DOC_BANG_MAY = {
    "bang_luong": "Bảng lương – thu nhập của từng người, dữ liệu cá nhân theo Nghị định 13/2023",
    "bang_bao_hiem": "Bảng bảo hiểm – mức đóng gắn với thu nhập của từng người, dữ liệu cá nhân theo Nghị định 13/2023",
}

TRANG_THAI = {
    "nhap": "Máy đã đọc – CHỜ NGƯỜI XÁC NHẬN",
    "da_xac_nhan": "Người đã xác nhận và ghi vào hệ thống",
    "bo": "Người xem rồi bỏ – máy đọc sai hoặc chứng từ không dùng",
}


class BanDocChungTu(Base):
    """Một lần máy đọc một tấm ảnh chứng từ. Một ảnh đọc lại nhiều lần thì mỗi lần một dòng."""
    __tablename__ = "ban_doc_chung_tu"
    __table_args__ = (
        # Cùng một ảnh, cùng một loại chứng từ, chỉ còn MỘT bản nháp đang chờ. Người dùng tải lại ảnh
        # vì tưởng lần trước hỏng là chuyện thường ngày; không có chỉ mục này thì hàng chờ đầy bản
        # trùng và người xác nhận sẽ ghi hai lần cùng một hóa đơn.
        Index("ux_ban_doc_dang_cho", "loai", "checksum_anh", "dang_cho", unique=True),
        Index("ix_ban_doc_trang_thai", "trang_thai", "loai"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(30), index=True)              # LOAI_CHUNG_TU
    bo_nap: Mapped[str] = mapped_column(String(30))                        # bộ nạp đích của cửa 1
    attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id"), nullable=True)
    checksum_anh: Mapped[str] = mapped_column(String(64), index=True)
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id"), nullable=True)
    mo_hinh: Mapped[str] = mapped_column(String(60), default="")
    # Nguyên văn máy đọc ra. KHÔNG BAO GIỜ ghi đè – đây là mẫu đối chứng để đo tỷ lệ phải sửa.
    so_may_doc: Mapped[dict] = mapped_column(JSON, default=dict)
    # Máy tự nói chỗ nào nó không chắc. Trường nào không đọc được thì để RỖNG trong so_may_doc và có
    # tên ở đây – không đoán, và tuyệt đối không điền 0 (quy tắc 4 của lệnh).
    truong_khong_doc_duoc: Mapped[list] = mapped_column(JSON, default=list)
    ghi_chu_may: Mapped[str] = mapped_column(Text, default="")             # máy giải thích chỗ nó ngờ
    trang_thai: Mapped[str] = mapped_column(String(16), default="nhap", index=True)
    # Cột phụ trợ cho chỉ mục duy nhất ở trên: bằng checksum khi còn chờ, bằng NULL khi đã xử lý.
    # NULL không đụng chỉ mục duy nhất ở cả SQLite lẫn PostgreSQL, nên một ảnh xử lý xong vẫn đọc lại
    # được nếu người dùng thật sự cần đọc lại.
    dang_cho: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Người bấm xác nhận, và số họ đã sửa.
    so_da_sua: Mapped[dict] = mapped_column(JSON, default=dict)
    truong_da_sua: Mapped[list] = mapped_column(JSON, default=list)
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ket_qua_ghi: Mapped[str] = mapped_column(String(300), default="")      # mô tả dòng đã ghi ở bảng đích
    intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ly_do_bo: Mapped[str] = mapped_column(String(300), default="")
    boi: Mapped[str] = mapped_column(String(50), default="")               # người tải ảnh lên
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
