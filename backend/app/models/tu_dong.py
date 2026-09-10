"""V11 – Lịch tự động hóa: mở VTOS ra là biết cái gì đang tự chạy, lúc nào, và lần gần nhất ra sao.

Hiện trạng trước hôm nay: lịch chạy tự động nằm ở n8n NGOÀI VTOS. Ai không mở n8n thì không biết hệ
thống đang tự làm những gì – kể cả Chủ tịch. Lệnh V11 nói rõ: không cần chuyển n8n vào trong, nhưng
n8n phải BÁO VỀ mỗi lần chạy.

────────────────────────────────────────────────────────────────────────────────
VÌ SAO PHẢI CÓ BẢNG KHAI BÁO TÁC VỤ, KHÔNG CHỈ CÓ SỔ LẦN CHẠY
────────────────────────────────────────────────────────────────────────────────

Đây là điểm quan trọng nhất của V11, và cũng là chỗ dễ làm hỏng nhất.

Nếu chỉ ghi lần chạy, ta thấy được mọi lần CHẠY HỎNG. Nhưng cách một tác vụ tự động hỏng tệ nhất
không phải là chạy rồi báo lỗi – mà là NGỪNG CHẠY. Luồng n8n bị tắt, bị đổi tên, hết hạn thẻ đăng
nhập, hoặc ai đó sửa lịch: từ lúc đó nó không sinh ra lần chạy nào, nên cũng không sinh ra một dòng
lỗi nào. Màn hình toàn màu xanh, và tuần sau kế toán mới phát hiện sao kê ba ngày chưa về.

    Im lặng là một trạng thái hỏng. Sổ lần chạy KHÔNG bao giờ ghi được nó, vì nó là sự VẮNG MẶT của
    một dòng chứ không phải sự có mặt của một dòng.

Nên phải khai trước: tác vụ này lẽ ra chạy mỗi bao lâu (`han_toi_da_phut`). Có con số đó thì hệ thống
so được "lần chạy thành công gần nhất" với "bây giờ" và tự nói ra tác vụ nào đã im. Không có nó thì
không ai trả lời được câu "cái gì lẽ ra phải chạy mà chưa chạy".

Và tác vụ do NGƯỜI khai, không phải máy tự sinh khi thấy lần chạy đầu tiên. Máy tự sinh thì một luồng
n8n bị xóa sẽ lặng lẽ biến mất khỏi màn hình cùng với lịch sử của nó – tức là đúng lúc cần biết nhất
thì không còn gì để nhìn. Người khai thì tác vụ ở lại và chuyển sang trạng thái quá hạn.

────────────────────────────────────────────────────────────────────────────────
HAI BẢNG
────────────────────────────────────────────────────────────────────────────────
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

# Hệ thống nào chạy tác vụ. Ghi ra để lúc một tác vụ im thì biết đi mở cái gì lên xem.
HE_THONG = {"n8n": "n8n (ngoài VTOS)", "vtos": "Bên trong VTOS", "khac": "Hệ thống khác"}

TRANG_THAI_LAN_CHAY = {
    "dang_chay": "Đang chạy",
    "thanh_cong": "Thành công",
    "that_bai": "Thất bại",
    # Chạy xong nhưng không làm được trọn việc – ví dụ đọc được 40/45 dòng sao kê. Tách riêng khỏi
    # "thất bại" vì hai cái này xử lý khác nhau: một cái phải chạy lại, một cái phải đi xem 5 dòng kia.
    "mot_phan": "Xong một phần",
}


class TacVuTuDong(Base):
    """Một tác vụ tự động được KHAI BÁO – tồn tại độc lập với việc nó có chạy hay không."""
    __tablename__ = "tac_vu_tu_dong"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Mã do người khai đặt và n8n gửi kèm mỗi lần báo về. Đây là chỗ nối duy nhất giữa hai hệ thống,
    # nên nó phải do người đặt và viết ra giấy, không phải một id sinh tự động ở một bên.
    ma: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    ten: Mapped[str] = mapped_column(String(200))
    mo_ta: Mapped[str] = mapped_column(Text, default="")
    he_thong: Mapped[str] = mapped_column(String(10), default="n8n")
    lich_doc: Mapped[str] = mapped_column(String(120), default="")   # "mỗi ngày 06:00" – cho người đọc
    lich_cron: Mapped[str] = mapped_column(String(80), default="")   # bản máy đọc, nếu có
    phong_ban: Mapped[str] = mapped_column(String(20), default="")
    nguoi_phu_trach: Mapped[str] = mapped_column(String(80), default="")
    # Lẽ ra chạy lại trong vòng bao nhiêu phút. 0 = không canh im lặng (tác vụ chạy theo sự kiện, không
    # theo lịch). Để 0 là một lựa chọn có ý thức, không phải mặc định tiện tay – nên màn hình nói ra.
    han_toi_da_phut: Mapped[int] = mapped_column(Integer, default=0)
    # Tác vụ quan trọng: im lặng hoặc thất bại thì sinh sự kiện kỹ thuật mức ĐỎ cho robot Kiểm soát.
    quan_trong: Mapped[bool] = mapped_column(Boolean, default=False)
    bat: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tắt có chủ ý phải ghi LÝ DO. Không có ô này thì một tác vụ bị tắt và một tác vụ bị quên trông
    # giống hệt nhau trên màn hình, mà hai cái đó cần hai cách xử lý ngược nhau.
    ly_do_tat: Mapped[str] = mapped_column(String(300), default="")
    tao_boi: Mapped[str] = mapped_column(String(50), default="")
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class LanChayTacVu(Base):
    """Một lần chạy. n8n gửi về; VTOS không tự sinh dòng nào ở đây."""
    __tablename__ = "lan_chay_tac_vu"
    __table_args__ = (
        Index("ix_lan_chay_tac_vu_luc", "tac_vu_id", "bat_dau"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    tac_vu_id: Mapped[int] = mapped_column(ForeignKey("tac_vu_tu_dong.id"), index=True)
    # Mã lần chạy bên hệ thống gọi (execution id của n8n). DUY NHẤT: n8n thử lại khi mạng chập, và
    # không có ràng buộc này thì một lần chạy thành hai dòng – rồi số lần thất bại đếm ra gấp đôi và
    # không ai còn tin bảng này nữa.
    ma_lan: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="dang_chay", index=True)
    bat_dau: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    giay: Mapped[float] = mapped_column(default=0)
    # Số bản ghi tác vụ xử lý được. RỖNG khi tác vụ không đếm được gì – không phải 0: 0 nghĩa là
    # "chạy xong, không có gì để làm", rỗng nghĩa là "không biết", và hai cái đó khác nhau.
    so_ban_ghi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thong_bao: Mapped[str] = mapped_column(Text, default="")
    chi_tiet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    boi: Mapped[str] = mapped_column(String(50), default="")
