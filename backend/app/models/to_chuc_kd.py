"""Cơ cấu tổ chức khối Kinh doanh — chi nhánh, phòng, team, và ai thuộc đơn vị nào TỪ NGÀY NÀO.

VẤN ĐỀ BẢNG NÀY SINH RA ĐỂ GIẢI

Trước vòng này, "đơn vị" của một người kinh doanh nằm trong BA CHUỖI CHỮ TỰ DO, không bảng nào cả:
`User.department`, `User.sales_group` ("KD1".."KD5", "VPCT"...) và `Employee.office` ("hcm",
"cantho"...). Gõ sai một chữ là người ấy rơi khỏi mọi báo cáo, mà không có gì báo lỗi. Ba chuỗi ấy
cũng không nói được quan hệ: không biết KD1 thuộc phòng nào, phòng nào thuộc chi nhánh nào. Bản bàn
giao Kinh doanh Lẻ V5.0 (19/9/2026) đòi xem xuống bốn cấp — chi nhánh → phòng → team → người — nên
không có cây thì không có màn hình.

Nặng hơn chuyện gõ sai: ba chuỗi ấy KHÔNG CÓ THỜI GIAN. Người chuyển team hôm nay thì doanh thu
tháng trước của họ lập tức chạy sang team mới, và báo cáo tháng trước in lại ra một con số khác con
số đã trình. Một bảng báo cáo đổi số sau lưng người đọc là bảng không dùng được để giao chỉ tiêu.

NĂM QUYẾT ĐỊNH ĐÁNG GHI LẠI

MỘT — CẤP PHẢI KHỚP VỚI CHA, MÁY CHỦ CHẶN. Team phải treo dưới phòng, phòng dưới chi nhánh, chi
nhánh không có cha. Không kiểm thì sáu tháng nữa sẽ có một "team" treo thẳng dưới chi nhánh vì hôm
ấy ai đó thấy tiện, và mọi phép cộng theo cấp sai từ đó. Đây là thứ rẻ nhất để chặn lúc ghi và đắt
nhất để dọn lúc đã có dữ liệu.

HAI — KHÔNG XOÁ ĐƠN VỊ, CHỈ ĐÓNG. Xoá một team là xoá luôn nghĩa của mọi dòng doanh thu từng gắn
vào nó. `hieu_luc_den` đóng đơn vị lại: từ ngày ấy không phân công mới được nữa, nhưng lịch sử vẫn
đọc được. Cùng một nếp với `Company` và với nhật ký giữ chỗ.

BA — PHÂN CÔNG LÀ MỘT KHOẢNG THỜI GIAN, KHÔNG PHẢI MỘT Ô. Đây là lý do cả bảng `phan_cong_kd` tồn
tại. Một người có nhiều dòng phân công nối tiếp nhau; báo cáo kỳ nào hỏi "ngày ấy người này thuộc
đơn vị nào" thì tra đúng dòng có hiệu lực NGÀY ẤY. Nhờ vậy chuyển team không làm đổi số kỳ cũ.
`den_ngay` để trống nghĩa là đang còn hiệu lực — RỖNG KHÁC KHÔNG, không lấy một ngày xa tít thay cho
trống.

BỐN — KHÔNG CHỒNG LẤN: một người, một mảng, một vai trò thì không được có hai dòng phủ cùng một
ngày. Chồng lấn là cách một người được đếm hai lần trong hai team, và tổng phòng lớn hơn tổng các
dòng con mà không ai tìm ra vì sao. Máy chủ chặn ngay lúc ghi, không để bộ đối soát phát hiện sau.

NĂM — ĐƠN VỊ CÓ MẢNG (`mang`), LẺ HAY ĐOÀN. Bản bàn giao V5.0 nói thẳng: Giám đốc Kinh doanh Lẻ
KHÔNG mặc định có quyền với Kinh doanh Đoàn. Nếu hai khối dùng chung một cây không nhãn thì cắt
quyền phải cắt bằng tên đơn vị — tức là quay lại đúng cái bệnh chuỗi chữ tự do mà bảng này sinh ra
để chữa.

BẢNG NÀY KHÔNG GIỮ SỐ TIỀN NÀO. Nó chỉ trả lời "ai ở đâu, từ bao giờ". Chỉ tiêu và phân bổ doanh thu
là hai bảng riêng ở vòng sau — gộp vào đây thì mỗi lần đổi chỉ tiêu lại đụng vào cơ cấu tổ chức.
"""
from datetime import date, datetime

from sqlalchemy import String, Date, DateTime, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Ba cấp, theo đúng thứ tự từ trên xuống. Thứ tự trong tuple LÀ thứ bậc — `CAP.index()` dùng để so
# sánh cấp, nên đừng sắp lại cho đẹp mắt.
CAP = ("chi_nhanh", "phong", "team")

# Cha hợp lệ của từng cấp. Cấp không có mặt ở đây (chi_nhanh) là cấp gốc, bắt buộc không có cha.
CHA_HOP_LE = {"phong": "chi_nhanh", "team": "phong"}

# Mảng kinh doanh. "le" = Kinh doanh Lẻ, "doan" = Kinh doanh Đoàn. Một đơn vị thuộc đúng một mảng;
# cây của hai mảng không dính nhau.
MANG = ("le", "doan")

# Vai trò trong đơn vị. Đây là vai trò TRONG CƠ CẤU, khác `User.role` (vai trò đăng nhập, quyết định
# mở được màn hình nào). Một người có `User.role = "nv_kd"` vẫn có thể là `leader` của một team —
# hai trục khác nhau, cố ý không trộn.
VAI_DON_VI = ("nhan_vien", "leader", "truong_phong", "giam_doc")


class DonViKD(Base):
    """Một chi nhánh, một phòng hoặc một team của khối Kinh doanh."""
    __tablename__ = "don_vi_kd"

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(160))
    cap: Mapped[str] = mapped_column(String(16))                 # CAP
    mang: Mapped[str] = mapped_column(String(8), default="le")   # MANG
    cha_id: Mapped[int | None] = mapped_column(ForeignKey("don_vi_kd.id"), nullable=True, index=True)

    # Pháp nhân chủ quản. RỖNG NGHĨA LÀ CHƯA XÁC ĐỊNH, không phải công ty mẹ — cùng luật với mọi
    # bảng khác mang `company_id` (xem services/pham_vi_phap_nhan.py).
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True)

    hieu_luc_tu: Mapped[date] = mapped_column(Date)
    hieu_luc_den: Mapped[date | None] = mapped_column(Date, nullable=True)

    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(64), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def dang_hieu_luc(self, ngay: date) -> bool:
        """Đơn vị này có hiệu lực vào `ngay` không. `hieu_luc_den` rỗng = còn hiệu lực."""
        if ngay < self.hieu_luc_tu:
            return False
        return self.hieu_luc_den is None or ngay <= self.hieu_luc_den


class PhanCongKD(Base):
    """Một người thuộc một đơn vị, TỪ ngày nào ĐẾN ngày nào, với vai trò gì trong đơn vị ấy."""
    __tablename__ = "phan_cong_kd"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    don_vi_id: Mapped[int] = mapped_column(ForeignKey("don_vi_kd.id"), index=True)
    vai: Mapped[str] = mapped_column(String(16), default="nhan_vien")   # VAI_DON_VI

    tu_ngay: Mapped[date] = mapped_column(Date)
    den_ngay: Mapped[date | None] = mapped_column(Date, nullable=True)

    ly_do: Mapped[str] = mapped_column(Text, default="")
    boi: Mapped[str] = mapped_column(String(64), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def dang_hieu_luc(self, ngay: date) -> bool:
        if ngay < self.tu_ngay:
            return False
        return self.den_ngay is None or ngay <= self.den_ngay


# Tra "ngày ấy người này ở đâu" là truy vấn chạy nhiều nhất của bảng, nên có chỉ mục riêng.
Index("ix_phan_cong_kd_nguoi_ngay", PhanCongKD.user_id, PhanCongKD.tu_ngay, PhanCongKD.den_ngay)
Index("ix_don_vi_kd_mang_cap", DonViKD.mang, DonViKD.cap)
