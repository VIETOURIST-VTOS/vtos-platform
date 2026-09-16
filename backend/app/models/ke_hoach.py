"""KẾ HOẠCH THÁNG – cửa nhập mà màn hình Chủ tịch đã chờ từ vòng TC-21.

Anh Tuấn duyệt mở cửa này ngày 15/9/2026 ("Anh muốn em mở luôn cửa nhập kế hoạch tháng = có").

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO MỘT BẢNG RIÊNG, KHÔNG PHẢI MỘT CỘT THÊM VÀO ĐÂU ĐÓ
═══════════════════════════════════════════════════════════════════════════════════════════════
Từ bản V1.4 của bản vẽ, thẻ "Doanh thu tháng" phải có dòng phụ "so với kế hoạch và kỳ trước". Suốt
bốn vòng thẻ ấy in một câu thú nhận – "chưa có kế hoạch tháng để so sánh (Kế toán)" – vì trong toàn
hệ thống không có chỗ nào chứa con số kế hoạch, và cũng không có cửa nào để ai nhập nó vào.

Ranh giới Chủ tịch đặt 09/9/2026 nói thẳng chuyện này: phần mềm viết CẤU TRÚC và PHÉP TÍNH, còn SỐ
LIỆU thì người của các bộ phận tự nhập. Hệ quả là mỗi con số trên màn hình phải lần ngược được về
MỘT CỬA có người đứng. Kế hoạch tháng chưa có cửa, nên nó không phải "chưa có số" – nó là VIỆC CÒN
THIẾU. Bảng này là chỗ số ấy nằm.

═══════════════════════════════════════════════════════════════════════════════════════════════
MỘT DÒNG = MỘT CHỈ TIÊU CỦA MỘT PHÁP NHÂN TRONG MỘT THÁNG
═══════════════════════════════════════════════════════════════════════════════════════════════
Không gộp doanh thu và lợi nhuận thành hai cột của cùng một dòng, dù cách ấy ngắn hơn. Lý do là
chuyện xảy ra thật ở mọi bảng kế hoạch: Kế toán nhập xong doanh thu cả năm rồi mới ngồi tính lợi
nhuận. Nếu hai chỉ tiêu chung một dòng thì trạng thái "đã có doanh thu, chưa có lợi nhuận" phải
biểu diễn bằng một ô NULL nằm cạnh một ô có số – và một ô NULL trong bảng thì đọc lên rất dễ thành
số 0. Tách dòng thì chỉ tiêu chưa nhập KHÔNG CÓ DÒNG NÀO CẢ, và không có dòng thì không có gì để
đọc nhầm.

`chi_tieu` là mã trong một danh sách ĐÓNG (services/ke_hoach.CHI_TIEU). Để mở thì bảng này thành
ngăn kéo tạp: mỗi người nhập một mã, và ba tháng sau không ai trả lời được câu "kế hoạch tháng gồm
những chỉ tiêu nào".

═══════════════════════════════════════════════════════════════════════════════════════════════
`company_id` CHỨ KHÔNG PHẢI `phap_nhan_id` – VÀ ĐÓ LÀ MỘT LỰA CHỌN CÓ HẬU QUẢ
═══════════════════════════════════════════════════════════════════════════════════════════════
`pham_vi_phap_nhan.bang_co_cot_phap_nhan()` QUÉT mô hình tìm cột tên `company_id` để biết bảng nào
thuộc về pháp nhân nào, thay vì đọc một danh sách viết tay. Đặt tên khác đi thì bảng này lọt khỏi
phép đo độ phủ, khỏi bộ kiểm SEC-02, và khỏi hàm lọc phạm vi – im lặng, không lỗi nào.

Cột NOT NULL: một kế hoạch phải thuộc về một pháp nhân. Khác hẳn các bảng hồ sơ, nơi dòng chưa gán
pháp nhân là chuyện bình thường của dữ liệu cũ; ở đây dòng là do người gõ vào hôm nay, và người gõ
luôn biết mình đang lập kế hoạch cho công ty nào.

═══════════════════════════════════════════════════════════════════════════════════════════════
THÊM MỘT BẢNG LÀ KHAI Ở BỐN SỔ, KHÔNG PHẢI MỘT — DANH SÁCH ĐẦY ĐỦ, ĐỂ LẦN SAU KHỎI ĐI TÌM
═══════════════════════════════════════════════════════════════════════════════════════════════
Vòng đầu của TC-41 đỏ CI đúng vì thiếu bốn dòng khai này, và cả bốn đều do bộ kiểm của kho bắt
được — không phải do ai đọc ra. Ghi lại thành danh sách vì lần sau người thêm bảng sẽ không nhớ:

  1. `app/models/__init__.py` — một dòng `from app.models.ke_hoach import *`. Thiếu nó thì
     `import app.models` KHÔNG thấy bảng: create_all không tạo, mọi phép thử soi metadata mù đúng
     bảng ấy, và alembic autogenerate sẽ đòi XOÁ nó. (test_ks7 · C1, C1b)
  2. `services/ks_cua_nhap.CUA_TAY` — khai bảng này vào bằng CỬA NÀO. Ranh giới 09/9 nói mỗi con
     số phải lần ngược được về một cửa có người đứng; bảng không khai cửa là việc còn thiếu.
     (test_ks_cua_nhap · CN1)
  3. `services/pham_vi_phap_nhan.PHAI_LOC` — bảng có cột `company_id` thì phải nói rõ nó được lọc
     theo phiên hay cố ý không, kèm lý do. (test_pham_vi_theo_phien)
  4. `tests/test_p2_pham_vi_vai_tro.PHAM_VI_DA_CHOT` — màn hình mới làm phạm vi của vài vai trò
     rộng thêm, và bảng chốt phải đổi theo, kèm lý do. Đây là phép đếm chống NỚI QUYỀN NHẦM: nó
     đỏ với mọi thay đổi, để người sửa buộc phải nói ra mình nới cho ai và vì sao.

═══════════════════════════════════════════════════════════════════════════════════════════════
BA CỘT CUỐI LÀ CHỖ TRẢ LỜI CÂU "AI SỬA KẾ HOẠCH THÁNG TRƯỚC, VÀ VÌ SAO"
═══════════════════════════════════════════════════════════════════════════════════════════════
Kế hoạch là thước đo, và ai cũng hiểu vì sao một thước đo sửa được sau khi đã đo xong thì không còn
là thước. Nên tháng đã khép được sửa – có những lý do chính đáng, ví dụ Hội đồng quản trị điều
chỉnh chỉ tiêu – nhưng mỗi lần sửa phải để lại lý do và tên người, ngay trên dòng, chứ không chỉ
trong nhật ký chung. Nhật ký chung thì phải đi tìm; dòng này thì đọc bảng là thấy.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.models.kieu_tien import TIEN


class KeHoachThang(Base):
    __tablename__ = "ke_hoach_thang"
    __table_args__ = (UniqueConstraint("ky", "company_id", "chi_tieu",
                                       name="uq_ke_hoach_thang_o"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # "2026-09". Chuỗi chứ không phải ngày: kế hoạch thuộc về CẢ THÁNG, không thuộc về một ngày nào
    # trong tháng. Lưu bằng kiểu ngày thì buộc phải chọn ngày 1 hay ngày cuối, và sớm muộn có chỗ
    # so sánh lệch một ngày.
    ky: Mapped[str] = mapped_column(String(7), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    chi_tieu: Mapped[str] = mapped_column(String(30), index=True)
    gia_tri: Mapped[float] = mapped_column(TIEN)

    # Lý do của LẦN SỬA GẦN NHẤT sau khi tháng đã khép. Rỗng nghĩa là dòng chưa từng bị sửa muộn –
    # không phải nghĩa là "không có lý do".
    ly_do_sua: Mapped[str] = mapped_column(Text, default="")
    nguoi_nhap: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # Đếm số lần dòng này bị sửa SAU KHI tháng đã khép. Một dòng sửa bảy lần thì bản thân con số bảy
    # đã là điều đáng hỏi, trước cả khi đọc từng lý do.
    so_lan_sua_muon: Mapped[int] = mapped_column(Integer, default=0)
