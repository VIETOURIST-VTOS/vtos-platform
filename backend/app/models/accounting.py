"""Kế toán theo Thông tư 99/2025/TT-BTC: hệ thống tài khoản, chứng từ ghi sổ, hóa đơn điện tử, khóa kỳ."""
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, DateTime, Date, Boolean, Text, ForeignKey, JSON, Index, event, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from app.models.kieu_tien import TIEN


class Account(Base):
    """Danh mục tài khoản (Phụ lục hệ thống TK theo TT99)."""
    __tablename__ = "accounts"
    code: Mapped[str] = mapped_column(String(10), primary_key=True)      # 111, 1121, 131…
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))                        # TS (tài sản) / NV (nguồn vốn) / DT / CP / XD
    parent: Mapped[str] = mapped_column(String(10), default="")
    # Cấu trúc MISA + ánh xạ Báo cáo tình hình tài chính / KQKD theo TT99 (mẫu nộp UBCK)
    level: Mapped[int] = mapped_column(Integer, default=1)                # bậc 1–5 (số chữ số − 2)
    is_detail: Mapped[bool] = mapped_column(Boolean, default=True)        # TK chi tiết (không có TK con) – chỉ TK chi tiết được ghi sổ
    bs_debit: Mapped[str] = mapped_column(String(6), default="")          # mã chỉ tiêu THTC khi dư Nợ (vd 131, 132, 135…)
    bs_credit: Mapped[str] = mapped_column(String(6), default="")         # mã chỉ tiêu THTC khi dư Có (vd 311, 312, 320…)
    pl_code: Mapped[str] = mapped_column(String(6), default="")           # mã chỉ tiêu KQKD (01, 11, 22, 23, 25, 26, 31, 32, 51)
    misa: Mapped[bool] = mapped_column(Boolean, default=False)            # có trên sổ MISA của Vietourist

    # ───── Đợt E1 (09/10/2026) · CHIỀU PHÂN TÍCH KHAI NGAY TRÊN TÀI KHOẢN ─────
    # Học từ MISA: form tài khoản của họ có khối "Theo dõi chi tiết theo" gồm các ô tích, và bộ
    # ghi sổ đọc chính khai báo ấy. Một nơi khai, mọi nơi đọc.
    #
    # Trước bản này `journal_lines` đã có ba cột chiều (partner_code, project_code, item_code)
    # nhưng KHÔNG nơi nào nói tài khoản nào bắt buộc chiều nào — nên quy ước và bộ kiểm kết sổ
    # nói hai điều khác nhau về TK3388 mà không chỗ nào là nguồn (P1·07, rà soát 09/10/2026).
    #
    # CHỈ BA CỜ, vì journal_lines chỉ có ba cột để kiểm. Bảy chiều còn lại của MISA chờ Đợt E3
    # mở cột rồi mới khai cờ — một cờ không có cột là một cờ bật được mà không kiểm được gì.
    #
    # tinh_chat ĐỂ TRỐNG cho 273 tài khoản đang có: trống = CHƯA AI KHAI, không phải "dư Nợ".
    # Khác hẳn cột `kind` ở trên — kind là phân loại báo cáo (TS/NV/DT/CP/XD), tinh_chat là
    # chiều số dư, dùng cho phép kiểm số dư bất thường.
    tinh_chat: Mapped[str | None] = mapped_column(String(12), nullable=True)   # du_no / du_co / luong_tinh
    co_ngoai_te: Mapped[bool] = mapped_column(Boolean, default=False)
    ngung_su_dung: Mapped[bool] = mapped_column(Boolean, default=False)
    td_doi_tuong: Mapped[bool] = mapped_column(Boolean, default=False)
    td_doi_tuong_loai: Mapped[str] = mapped_column(String(10), default="")     # kh / ncc / nv / tat_ca
    td_cong_trinh: Mapped[bool] = mapped_column(Boolean, default=False)        # mã công trình = mã tour
    td_khoan_muc: Mapped[bool] = mapped_column(Boolean, default=False)


class JournalEntry(Base):
    """Chứng từ ghi sổ. Sinh tự động từ nghiệp vụ (robot R2) hoặc Kế toán lập tay. Đã ghi sổ thì không sửa – chỉ lập bút toán đảo."""
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)            # CT2609-0001
    entry_date: Mapped[date] = mapped_column(Date)   # CỐ Ý không đánh chỉ mục – xem migration d0e1f2a3b4c5
    period: Mapped[str] = mapped_column(String(7), index=True)            # 2026-09
    description: Mapped[str] = mapped_column(String(300))
    # Đợt E3 12/10/2026 – chú thích cũ khai NĂM giá trị; đo bằng cây cú pháp của 32 chỗ gọi
    # `post_entry` thì mã thật dùng 17 giá trị hằng. Danh sách thật nay ở `chung_tu_loai.NGUON`,
    # và `test_e3_4` đỏ nếu mã dùng một giá trị chưa khai ở đó. Không chép danh sách vào đây:
    # một danh sách chép hai chỗ là hai chỗ để lệch nhau.
    source_type: Mapped[str] = mapped_column(String(30), default="thu_cong")
    source_ref: Mapped[str] = mapped_column(String(60), default="")       # receipt:PT…, invoice:…, tour:…
    # ĐỢT E3 – BA CỘT PHÂN LOẠI VÀ MỘT KHOÁ CHỐNG GHI SỔ HAI LẦN.
    #
    # `ngay_chung_tu` tách khỏi `entry_date`: trước đợt này MỘT ngày gánh hai việc – ngày trên tờ
    # chứng từ và ngày ghi vào sổ. Hóa đơn đề ngày 28/9 mà Kế toán nhận ngày 3/10 thì hai ngày ấy
    # khác nhau thật, và báo cáo thuế đọc ngày chứng từ còn sổ cái đọc ngày ghi sổ.
    #
    # `khoa_su_kien` do `services/accounting.py::post_entry` GHÉP, không phải ô người gọi điền:
    # nguồn, mã nguồn và loại nghiệp vụ nối lại. NULL nghĩa là sự kiện không định danh được – hai
    # trường hợp ấy khai ở `chung_tu_loai.KHONG_KHOA_SU_KIEN` kèm lý do. NULL không va nhau trong
    # chỉ mục duy nhất, nên chứng từ lập tay vẫn lập được nhiều tờ giống nhau trong một ngày.
    ngay_chung_tu: Mapped[date] = mapped_column(Date)
    # ĐỢT E14 13/10/2026 — HAI MỐC CỦA BÚT TOÁN ĐIỀU CHỈNH, và cả hai CỐ Ý để rỗng được.
    #
    # Rỗng ở đây đọc đúng là "không phải bút toán điều chỉnh" — khác hẳn 0 hay một ngày mặc định.
    # Hai mốc này chỉ có nghĩa với bút toán sửa sai sót kỳ trước, và `services/dieu_chinh.kiem`
    # chặn CẢ HAI CHIỀU: điều chỉnh mà thiếu thì không ghi được, nghiệp vụ thường mà điền vào
    # cũng không ghi được — điền hai mốc cho một bút toán bình thường là khai nó thành bút toán
    # sửa sai, tức một lời nói dối nhỏ nằm ngay trong sổ.
    #
    # `ky_goc` KHÔNG MỞ ĐƯỢC KỲ ĐÃ KHÓA. Nó là một NHÃN nói bút toán thuộc câu chuyện của kỳ nào;
    # bút toán vẫn ghi vào kỳ đang mở theo `entry_date`. Muốn ghi THẲNG vào kỳ cũ thì đi cửa mở
    # lại kỳ của Đợt E6 — hai người ký. Nếu `ky_goc` tự ghi vào kỳ cũ thì nó là đường vòng qua
    # chính cửa ấy, và cửa ấy mất nghĩa ngay ngày có đường vòng.
    ky_goc: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
    ngay_phat_hien: Mapped[date | None] = mapped_column(Date, nullable=True)
    loai_chung_tu: Mapped[str] = mapped_column(String(10), default="")    # xem chung_tu_loai.LOAI_CHUNG_TU
    loai_nghiep_vu: Mapped[str] = mapped_column(String(40), default="")   # xem chung_tu_loai.NGHIEP_VU
    khoa_su_kien: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True, index=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="nhap")       # nhap / da_ghi_so / huy
    created_by: Mapped[str] = mapped_column(String(50), default="robot")
    posted_by: Mapped[str] = mapped_column(String(50), default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # id chứng từ đảo
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # pháp nhân chủ quản – rỗng là CHƯA XÁC ĐỊNH, không mặc định về công ty mẹ
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    lines: Mapped[list["JournalLine"]] = relationship(back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.id")


# ĐỢT E3 – "NGÀY CHỨNG TỪ RỖNG THÌ BẰNG NGÀY GHI SỔ" LÀ LUẬT CỦA BẢNG, KHÔNG PHẢI CỦA MỘT HÀM.
#
# Đặt mặc định trong `post_entry` thôi là chưa đủ: bốn tệp phép thử và bất cứ mã nào về sau cũng
# có thể dựng `JournalEntry(...)` thẳng, và lúc ấy cột NOT NULL ném lỗi ở tầng cơ sở dữ liệu —
# một lời báo không nói được gì về nghiệp vụ. Đo 12/10/2026: `test_ks_hau_kiem_nhap_tay` đỏ đúng
# vì thế, 17 lỗi, và nó đỏ vì CÁCH KHAI của em chứ không vì bài toán nó đang canh.
#
# Móc `before_insert` đặt luật ở chỗ KHÔNG ai đi vòng được. Cột vẫn NOT NULL – ngày chứng từ rỗng
# là một chứng từ không báo cáo thuế được, nên nó phải là lỗi chứ không phải một ô trống.
@event.listens_for(JournalEntry, "before_insert")
def _ngay_chung_tu_mac_dinh(_mapper, _ket_noi, e: JournalEntry) -> None:
    if e.ngay_chung_tu is None:
        e.ngay_chung_tu = e.entry_date


class JournalLine(Base):
    __tablename__ = "journal_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_code: Mapped[str] = mapped_column(ForeignKey("accounts.code"), index=True)
    # V9 đợt 1 – hai cột này là chỗ kiểm toán đối chiếu đầu tiên, nên đổi trước mọi cột khác.
    debit: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    credit: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    partner: Mapped[str] = mapped_column(String(160), default="")         # tên đối tượng: khách / NCC
    partner_code: Mapped[str] = mapped_column(String(60), default="", index=True)   # mã đối tượng MISA (MST/CCCD/mã NV/mã ngân hàng)
    project_code: Mapped[str] = mapped_column(String(40), default="", index=True)   # mã công trình MISA = mã tour
    # ĐỢT R3a 16/10/2026 — `index=True` KHÔNG phải tối ưu, nó là điều kiện để chiều khoản mục
    # có báo cáo được: hai chiều kia (partner_code, project_code) đều có chỉ mục và đều đã có
    # báo cáo; chiều này không có chỉ mục nên mọi phép gom theo nó quét toàn bảng. Trên SQLite
    # của phép thử không ai thấy; trên Postgres với sổ thật thì thấy.
    item_code: Mapped[str] = mapped_column(String(40), default="", index=True)   # mã khoản mục chi phí (KM_*)
    # ĐỢT R3a — TÁCH BỘ PHẬN RA KHỎI `item_code`. Trước bản này `assets.py` ghi mã BỘ PHẬN vào
    # `item_code` cho khấu hao TSCĐ và phân bổ chi phí trả trước, nên một cột chở HAI nghĩa.
    # Báo cáo "chi phí theo khoản mục" dựng trên cột ấy sẽ có vài dòng mang tên bộ phận, mà
    # TỔNG VẪN ĐÚNG — không phép thử số học nào bắt được, chỉ người đọc báo cáo mới thấy lạ.
    bo_phan: Mapped[str] = mapped_column(String(20), default="", index=True)     # mã bộ phận sử dụng
    # ĐỢT R4b-2a 22/10/2026 — SỬA CHÚ THÍCH SAI CỦA CHÍNH CỘT NÀY.
    #
    # Chú thích cũ ghi "số hóa đơn / số chứng từ gốc" — MỘT cột hai nghĩa. Đo trên main hôm nay:
    # chỗ DUY NHẤT ghi vào nó trong bộ quy tắc là `services/hach_toan.py` dòng 399, và nó ghi
    # `boi_canh["so_chung_tu"]`, tức SỐ CHỨNG TỪ. Sáu chỗ trong `services/books.py` chỉ ĐỌC để in
    # ra cột "Số CT gốc". Giao diện web không dùng. Phép thử: KHÔNG CÓ CHỖ NÀO — nghĩa của cột này
    # chưa từng được ghim.
    #
    # Nên dùng lại nó làm số hóa đơn là để bộ quy tắc đè mất số hóa đơn mỗi lần tự ghi sổ: sổ vẫn
    # cân, báo cáo vẫn ra số, không phép thử nào đỏ. Đúng hình dạng lỗi `item_code` chở hai nghĩa
    # mà Đợt R3a phải đi gỡ. Nên: cột này giữ NGUYÊN nghĩa số chứng từ, hóa đơn đi cột riêng.
    doc_no: Mapped[str] = mapped_column(String(40), default="")           # số chứng từ gốc — KHÔNG phải hóa đơn (xem Đợt R4b-2a)
    # ĐỢT R4b-2a — HAI CỘT HÓA ĐƠN, GẮN TRÊN TỪNG DÒNG chứ không trên chứng từ.
    #
    # Chủ tịch chốt 22/10/2026. Lý do: một ủy nhiệm chi trả gộp ba hóa đơn của cùng một nhà cung
    # cấp là chuyện thường; đặt trên chứng từ thì chỉ ghi được một số, hai hóa đơn kia biến mất
    # khỏi sổ — mà đó đúng là thứ đối chiếu thuế sẽ hỏi tới. MISA cũng đặt trên dòng sổ chi tiết.
    #
    # `ngay_hoa_don` KHÔNG đổi `entry_date` và KHÔNG đổi kỳ của bút toán. Nó là mốc thứ ba, đứng
    # cạnh `ngay_chung_tu` của Đợt E3 — ba câu hỏi khác nhau, ba cột khác nhau.
    ngay_hoa_don: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_hoa_don: Mapped[str] = mapped_column(String(40), default="")
    # BA TRẠNG THÁI, và ô rỗng là một trong ba chứ không phải "chưa khai":
    #   ""                 chưa nhận được  (mặc định — dòng nằm trong danh sách việc cần làm)
    #   "da_nhap"          đã nhập         (có ngày và số)
    #   "khong_phat_sinh"  không phát sinh hóa đơn (bắt buộc có lý do)
    hoa_don_trang_thai: Mapped[str] = mapped_column(String(20), default="", index=True)
    hoa_don_ly_do: Mapped[str] = mapped_column(String(200), default="")
    # Không cần ai duyệt (Chủ tịch chốt), nhưng VẪN ghi ai và lúc nào: một khoản được miễn hóa đơn
    # là một quyết định thuế, và quyết định thì phải có tên người.
    hoa_don_nguoi_ghi: Mapped[str] = mapped_column(String(50), default="")
    hoa_don_ghi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")


class Invoice(Base):
    """Hóa đơn điện tử GTGT (mẫu 01/GTGT). Phát hành qua nhà cung cấp HĐĐT – bản pilot dùng adapter nội bộ."""
    __tablename__ = "invoices"
    # ĐỢT E7 13/10/2026 — HAI CHỈ MỤC DUY NHẤT, và chúng là HÀNG RÀO THỨ HAI của việc chống phát
    # hành hai lần. Hàng rào thứ nhất là mã việc do màn hình sinh; nhưng một hàng rào chỉ ở màn
    # hình là không có hàng rào nào — robot gọi thẳng API, một bản vá sau này viết sai, hay hai
    # người cùng phát hành hai hóa đơn khác nhau trong một giây đều không đi qua nó. Hai dòng dưới
    # đây đổ ở tầng thấp nhất, chỗ không đường nào lách được.
    #
    # ĐIỀU KIỆN `number > 0` LÀ BẮT BUỘC, không phải tối ưu: mọi hóa đơn NHÁP mang `number = 0`
    # theo giá trị mặc định của cột, nên một chỉ mục duy nhất KHÔNG điều kiện sẽ đổ ngay ở tờ nháp
    # thứ hai. Khai cả hai phương ngữ vì máy chủ chạy Postgres còn phép thử chạy SQLite, và một
    # hàng rào chỉ có ở một trong hai nơi là hàng rào không ai đo được.
    __table_args__ = (
        Index("ux_invoices_issue_request_id", "issue_request_id", unique=True),
        Index("ux_invoices_series_number", "series", "number", unique=True,
              postgresql_where=text("number > 0"), sqlite_where=text("number > 0")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    series: Mapped[str] = mapped_column(String(20), default="1C26TVT")    # ký hiệu
    number: Mapped[int] = mapped_column(Integer, default=0)                # số hóa đơn (cấp khi phát hành)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(160))
    customer_tax_code: Mapped[str] = mapped_column(String(20), default="")
    customer_address: Mapped[str] = mapped_column(String(300), default="")
    description: Mapped[str] = mapped_column(String(300), default="")
    pre_tax: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    vat_rate: Mapped[float] = mapped_column(Float, default=0.1)
    vat: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    total: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    # ĐỢT E7 13/10/2026 — TRẠNG THÁI THỨ TƯ `dang_phat_hanh`, nằm GIỮA nháp và đã phát hành.
    # Nó là trạng thái "KHÔNG BIẾT", không phải "thất bại": hệ thống biết mình đã gửi và không
    # biết bên kia đã nhận. Coi cái thứ nhất là cái thứ hai rồi phát hành lại chính là cách làm
    # ra hóa đơn trùng, nên tờ ở trạng thái này chỉ ra khỏi đó qua cửa DÒ LẠI.
    status: Mapped[str] = mapped_column(String(20), default="nhap")       # nhap / dang_phat_hanh / da_phat_hanh / huy
    # Mã việc của MỘT lần bấm, do màn hình sinh. Chỉ mục duy nhất ở trên là thứ làm nó có tác dụng.
    issue_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issue_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider: Mapped[str] = mapped_column(String(30), default="noi_bo")   # noi_bo / viettel / vnpt / misa…
    provider_ref: Mapped[str] = mapped_column(String(80), default="")     # mã tra cứu / mã CQT
    entry_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="")
    issued_by: Mapped[str] = mapped_column(String(50), default="")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PeriodLock(Base):
    """Khóa kỳ kế toán: sau khi khóa không ghi sổ vào kỳ đó."""
    __tablename__ = "period_locks"
    period: Mapped[str] = mapped_column(String(7), primary_key=True)
    locked_by: Mapped[str] = mapped_column(String(50))
    locked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    note: Mapped[str] = mapped_column(String(200), default="")


class Partner(Base):
    """Đối tượng kế toán (danh mục khách hàng / nhà cung cấp / nhân viên / ngân hàng) – cùng mã với MISA (MST, CCCD…)."""
    __tablename__ = "partners"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    kind: Mapped[str] = mapped_column(String(10), default="kh")          # kh / ncc / nv / nh / khac
    is_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_supplier: Mapped[bool] = mapped_column(Boolean, default=False)
    tax_code: Mapped[str] = mapped_column(String(20), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    trade_name: Mapped[str] = mapped_column(String(200), default="")     # tên thương mại (DataNCC: "RESORT VĨNH HY")
    internal: Mapped[bool] = mapped_column(Boolean, default=False)       # đối tượng nội bộ / bên liên quan
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(20), default="misa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Project(Base):
    """Công trình MISA = tour/đoàn (chiều tập hợp chi phí – doanh thu). Mã chuẩn SP.NHÓM.DDMMYY; mã cũ giữ để đọc lịch sử."""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="dang_thuc_hien")
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    technical: Mapped[bool] = mapped_column(Boolean, default=False)      # mã kỹ thuật (0000, CHUA RO, CPXD…) – không phải tour
    source: Mapped[str] = mapped_column(String(20), default="misa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
