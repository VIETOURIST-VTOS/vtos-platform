"""MKT · Mã lead, mã tour, thời điểm phát sinh/chốt, lịch sử giao–nhận Sales

Revision ID: mkt1a9c4e7b2d63
Revises: tg9c4e1a7b52d8  (nối lại 18/9/2026 – xem phần dưới)
Create Date: 2026-09-14

═══════════════════════════════════════════════════════════════════════════════════════════════
ĐÃ NHẬN VÀ ĐÃ ĐẨY – 18/9/2026
═══════════════════════════════════════════════════════════════════════════════════════════════
Bản này do làn R1 soạn sẵn ngày 14/9/2026 lúc bàn giao phần Marketing sang R3, và để ở dạng NHÁP
ngoài kho suốt bốn ngày vì chưa có làn nào nhận. Anh Tuấn giao lại cho R1 ngày 18/9/2026.

HAI VIỆC BẢN NHÁP DẶN PHẢI LÀM TRƯỚC KHI DÙNG, VÀ ĐÃ LÀM:

  1. `down_revision` đổi từ `a3d71e9c54b28` sang `tg9c4e1a7b52d8`.
     Đầu mạch đã chạy tiếp ba bản trong bốn ngày ấy. Đo lại ngày 18/9 bằng cách đọc cả 98 bản
     trong `alembic/versions/`: đúng MỘT gốc (`30644a36358d`), đúng MỘT đầu (`tg9c4e1a7b52d8`,
     sổ tỷ giá 17/9), không bản nào trỏ vào một mã không tồn tại.
  2. Đổi tên tệp và đặt vào `alembic/versions/`.

VÌ SAO CHUYỆN ĐẦU MẠCH QUAN TRỌNG ĐẾN THẾ: Dockerfile chạy `alembic upgrade head` lúc khởi động.
Nhiều hơn một đầu là container không lên được. Ngày 07/9/2026 việc ấy xảy ra BA lần trong một buổi.
`tests/test_mach_migration.py` canh đúng điều đó và chạy trong mỗi vòng CI.

MỘT PHẦN CỦA GÓI BÀN GIAO CỐ Ý KHÔNG ĐẨY: `mkt_chi_so.py` (và ba tệp phép thử của nó) cài lại quy
tắc `overview-v1` — cùng một luật Chủ tịch đã ký, nhưng ở một tệp thứ hai và ra con số khác với bản
đang chạy trong `services/leads.py`. Anh Tuấn chốt ngày 18/9: giữ MỘT bản cài, là bản trong
`leads.py`. Gói bàn giao gốc vẫn nằm nguyên ở thư mục `BAN-GIAO-R3-MARKETING` cho ai cần đọc lại.

═══════════════════════════════════════════════════════════════════════════════════════════════
NỘI DUNG
═══════════════════════════════════════════════════════════════════════════════════════════════
A · MƯỜI CỘT MỚI TRÊN `leads`, tất cả NULLABLE

Rỗng ở đây nghĩa là CHƯA AI HỎI, không phải "không có". Đặt giá trị mặc định là biến một ô chưa
hỏi thành một câu trả lời, rồi báo cáo cộng nó vào như số thật.

    nguon_thu_hut      khách biết tới mình từ đâu       (Facebook, Tiktok, khách cũ giới thiệu…)
    diem_tiep_nhan     cuộc liên hệ rơi vào đâu          (hotline, web, VCHAT, Zalo OA)
    mang               le / mice
    giao_luc           lúc lead sang tay Sales
    han_xu_ly          hẹn bao giờ phải liên hệ xong
    ly_do_mat          bắt buộc khi trạng thái là "không chốt"
    ma_lead            mã MỘT LẦN PHÁT SINH NHU CẦU – duy nhất
    ma_tour            mã tour khách hỏi – ô MÃ, chọn từ danh mục, không gõ tự do
    phat_sinh_luc      ngày GIỜ nhu cầu sinh ra ở nguồn, KHÔNG phải giờ nhập tệp
    ma_booking         mã booking khi chốt – ô MÃ, không phải ô tiền
    dau_van_tay        dấu dòng nguồn đã nhập, để nhập lại cùng một tệp không sinh thêm lead

KHÔNG CÓ CỘT MÃ KHÁCH – chốt của Chủ tịch 14/9/2026. Hệ thống không cấp mã khách; người nhập chỉ
nhập mã tour. Đơn vị "một người" khi báo cáo vì thế lấy theo SỐ ĐIỆN THOẠI đã chuẩn hoá, và báo
cáo phải gọi đúng tên nó là "số điện thoại khác nhau", không gọi là "số khách đã xác minh".

Cột `channel` CŨ GIỮ NGUYÊN, không bỏ: dữ liệu đã nhập nằm ở đó, và bỏ cột cũ trong cùng một lần
sửa là làm hỏng mọi báo cáo đang chạy.

B · GỠ RÀNG BUỘC DUY NHẤT `uq_lead_phone_month_channel`

Đây là phần quan trọng nhất và cũng là phần DỄ ĐỌC NHẦM LÀ NỚI LỎNG. Ràng buộc cũ trên
(phone, lead_month, channel) buộc mỗi khách chỉ có MỘT dòng cho mỗi kỳ mỗi kênh. Hệ quả không
nhìn thấy trên màn hình: khách gọi hotline ngày 3 rồi gọi lại ngày 20 cùng tháng thì lần thứ hai
KHÔNG lưu được – cơ sở dữ liệu từ chối, và cửa nhập buộc phải ghi đè lên lần thứ nhất. Một lần
liên hệ có thật biến mất, không dòng nhật ký nào ghi lại.

Không phải suy đoán: hai phép thử trong `test_mkt2_cua_nhap.py` đỏ với chính dòng lỗi
"UNIQUE constraint failed: leads.phone, leads.lead_month, leads.channel".

Thay bằng: `ma_lead` duy nhất + một chỉ mục THƯỜNG trên bộ ba cũ để các truy vấn đang chạy không
chậm đi. Tính duy nhất không mất – nó chuyển sang đúng chỗ của nó.

C · BẢNG MỚI `lead_ban_giao`

Hai cột `giao_luc` / `han_xu_ly` chỉ giữ được TRẠNG THÁI HIỆN TẠI. Lead giao người A, A không
gọi, giao lại người B – sau khi ghi đè thì không còn dấu vết nào cho thấy A từng cầm nó. Đến lúc
hỏi "vì sao lead này mất", câu trả lời đã bị chính hệ thống xoá.

`phien_ban_quy_tac` giữ tên bản quy tắc đã dùng để đặt hạn. Quy tắc hạn sẽ đổi; không ghi lại
bản đã dùng thì lead cũ bị chấm theo thước mới, và người bị chấm có quyền không nhận.

═══════════════════════════════════════════════════════════════════════════════════════════════
LÙI LẠI ĐƯỢC KHÔNG
═══════════════════════════════════════════════════════════════════════════════════════════════
`downgrade()` dựng LẠI ràng buộc duy nhất cũ. Nếu lúc ấy trong bảng đã có hai dòng cùng
(phone, lead_month, channel) – tức đúng những lần liên hệ mà ràng buộc cũ không cho lưu – thì
lệnh dựng lại SẼ HỎNG. Đó là hành vi đúng: lùi lại một bản đã ghi dữ liệu mới phải dừng và báo,
chứ không được tự xoá bớt dòng cho vừa ràng buộc.
"""
import sqlalchemy as sa
from alembic import op

revision = "mkt1a9c4e7b2d63"
down_revision = "tg9c4e1a7b52d8"
branch_labels = None
depends_on = None


COT_MOI = [
    ("nguon_thu_hut", sa.String(24), True),
    ("diem_tiep_nhan", sa.String(24), True),
    ("mang", sa.String(6), False),
    ("giao_luc", sa.Date(), False),
    ("han_xu_ly", sa.Date(), False),
    ("ly_do_mat", sa.String(20), False),
    ("ma_tour", sa.String(40), True),
    ("phat_sinh_luc", sa.DateTime(), True),
    ("ma_booking", sa.String(40), True),
    ("dau_van_tay", sa.String(16), True),
]


def upgrade():
    for ten, kieu, co_chi_muc in COT_MOI:
        op.add_column("leads", sa.Column(ten, kieu, nullable=True))
        if co_chi_muc:
            op.create_index(f"ix_leads_{ten}", "leads", [ten])

    # ma_lead tách riêng vì nó DUY NHẤT – và duy nhất trên cột rỗng thì mọi dòng cũ vẫn hợp lệ
    # (NULL không đụng ràng buộc duy nhất ở PostgreSQL).
    op.add_column("leads", sa.Column("ma_lead", sa.String(24), nullable=True))
    op.create_index("ix_leads_ma_lead", "leads", ["ma_lead"], unique=True)

    # Gỡ ràng buộc cũ, thay bằng chỉ mục thường. Xem phần B của chú thích đầu tệp.
    op.drop_constraint("uq_lead_phone_month_channel", "leads", type_="unique")
    op.create_index("ix_lead_phone_month_channel", "leads",
                    ["phone", "lead_month", "channel"])

    op.create_table(
        "lead_ban_giao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=False),
        sa.Column("viec", sa.String(10), nullable=False),
        sa.Column("tu_nguoi", sa.String(50), nullable=True),
        sa.Column("den_nguoi", sa.String(50), nullable=True),
        sa.Column("han_cu", sa.Date(), nullable=True),
        sa.Column("han_moi", sa.Date(), nullable=True),
        sa.Column("phien_ban_quy_tac", sa.String(20), nullable=True),
        sa.Column("ly_do", sa.String(200), server_default="", nullable=False),
        sa.Column("luc", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("boi", sa.String(50), server_default="", nullable=False),
    )
    op.create_index("ix_lead_ban_giao_lead_id", "lead_ban_giao", ["lead_id"])
    op.create_index("ix_lead_ban_giao_viec", "lead_ban_giao", ["viec"])
    op.create_index("ix_lead_ban_giao_luc", "lead_ban_giao", ["luc"])


def downgrade():
    op.drop_index("ix_lead_ban_giao_luc", table_name="lead_ban_giao")
    op.drop_index("ix_lead_ban_giao_viec", table_name="lead_ban_giao")
    op.drop_index("ix_lead_ban_giao_lead_id", table_name="lead_ban_giao")
    op.drop_table("lead_ban_giao")

    op.drop_index("ix_lead_phone_month_channel", table_name="leads")
    # DỰNG LẠI ràng buộc cũ. Nếu đã có hai lần liên hệ cùng (phone, lead_month, channel) thì lệnh
    # này HỎNG – và hỏng là đúng. Xem phần cuối chú thích đầu tệp.
    op.create_unique_constraint("uq_lead_phone_month_channel", "leads",
                                ["phone", "lead_month", "channel"])

    op.drop_index("ix_leads_ma_lead", table_name="leads")
    op.drop_column("leads", "ma_lead")
    for ten, _kieu, co_chi_muc in reversed(COT_MOI):
        if co_chi_muc:
            op.drop_index(f"ix_leads_{ten}", table_name="leads")
        op.drop_column("leads", ten)
