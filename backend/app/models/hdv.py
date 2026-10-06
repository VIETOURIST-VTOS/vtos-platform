"""Phòng Hướng dẫn viên — bảng YÊU CẦU HDV (Đợt 1, Chủ tịch giao 06/10/2026).

VÌ SAO CẦN MỘT BẢNG RIÊNG CHO CÁI CHƯA XẾP ĐƯỢC

Hôm nay chuỗi của phòng HDV bắt đầu thẳng từ `guide_assignments` — tức là từ lúc ĐÃ chọn được người.
Thứ chưa chọn được thì không nằm ở đâu cả. Hệ quả không phải là thiếu một màn hình, mà là thiếu một
câu trả lời: "tuần sau có bao nhiêu chuyến chưa có hướng dẫn viên" hiện không hỏi được, vì cái thiếu
không tồn tại trong cơ sở dữ liệu. Một chuyến khởi hành thiếu người thì chỉ lộ ra khi có người nhớ ra.

Bảng này là chỗ Điều hành ĐẶT HÀNG phòng HDV, và là chỗ đếm được phần còn thiếu.

MỘT BẢNG RIÊNG CHO HDV, KHÔNG DÙNG CHUNG VỚI YÊU CẦU XE — Chủ tịch chốt 06/10/2026. Làn khác giữ
phần đội xe. Hai bảng thì phải có MỘT quy ước chung cho chữ "chuyến chưa đủ nguồn lực", nếu không
hai màn hình sẽ trả lời khác nhau về cùng một chuyến; quy ước ấy đặt ở `con_thieu()` dưới đây và
phần xe cần một hàm cùng nghĩa.

VÌ SAO CÓ `bat_dau`/`ket_thuc` CHỨ KHÔNG CHỈ CÓ NGÀY ĐI–VỀ CỦA TOUR

Chủ tịch chốt 06/10: một hướng dẫn viên KHÔNG được xếp hai chuyến chồng giờ. Muốn so hai khoảng thì
phải có hai đầu mốc, mà khoảng cần người KHÔNG bằng khoảng của tour: đón đoàn 5h sáng thì người phải
có mặt từ 4h, tiễn sân bay xong 23h đêm thì 23h mới là lúc hết việc. Lấy ngày đi–về của tour để so
thì hai chuyến "về 22h hôm nay, đi 5h sáng mai" sẽ bị báo là chồng nhau, còn hai chuyến thật sự chồng
vài giờ trong cùng một ngày thì không bị bắt.

RỖNG VẪN LÀ RỖNG. Hai mốc giờ ĐỂ TRỐNG ĐƯỢC: hàng trăm chuyến cũ không có giờ, và suy giờ từ ngày
khởi hành sẽ sinh ra một con số trông như thật. Yêu cầu chưa có giờ thì hiện ở danh sách việc còn
thiếu và KHÔNG tham gia phép chặn trùng — xem `app/services/hdv.py`.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

# Trạng thái của một yêu cầu. "da_du" KHÁC "da_phan_cong": phân công một người cho yêu cầu cần hai
# người thì yêu cầu vẫn còn thiếu một — và phần còn thiếu ấy chính là thứ bảng này sinh ra để đếm.
TRANG_THAI = {
    "moi": "Mới gửi, chưa phân công ai",
    "dang_xep": "Đã phân công một phần, còn thiếu người",
    "da_du": "Đã đủ số hướng dẫn viên yêu cầu",
    "huy": "Đã huỷ",
}
# Hai trạng thái dưới đây KHÔNG còn nằm trong danh sách việc phải xếp.
TRANG_THAI_DONG = ("da_du", "huy")


class YeuCauHdv(Base):
    """Điều hành xin hướng dẫn viên cho một chuyến. Một chuyến có thể có nhiều yêu cầu (ví dụ xin
    thêm người sau khi đoàn tăng khách), nên KHÔNG đặt khoá duy nhất theo tour."""

    __tablename__ = "yeu_cau_hdv"

    # V10 – người sau biết mình đang đè lên người trước. Yêu cầu là bản ghi mà Điều hành và phòng HDV
    # cùng chạm: một bên sửa số người, một bên sửa hạn phản hồi.
    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    # Pháp nhân suy từ chuyến lúc lập, và GIỮ LẠI chứ không tra lại mỗi lần đọc: chuyến có thể đổi
    # pháp nhân, còn yêu cầu đã gửi thì thuộc về pháp nhân lúc gửi.
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)

    so_hdv: Mapped[int] = mapped_column(Integer, default=1)
    # Khoảng CẦN NGƯỜI, tính cả chuẩn bị và di chuyển. Để trống được – xem chú thích đầu tệp.
    bat_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ket_thuc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    ngoai_ngu: Mapped[str] = mapped_column(String(60), default="")
    nang_luc: Mapped[str] = mapped_column(String(200), default="")
    diem_hen: Mapped[str] = mapped_column(String(200), default="")
    ghi_chu: Mapped[str] = mapped_column(Text, default="")
    # Hạn phòng HDV phải trả lời Điều hành. Khác `guide_assignments.han_tra_loi` là hạn HDV trả lời
    # phòng — hai hạn của hai chặng khác nhau, gộp một cột là mất một trong hai.
    han_phan_hoi: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(16), default="moi", index=True)
    ly_do_huy: Mapped[str] = mapped_column(String(200), default="")

    nguoi_lap: Mapped[str] = mapped_column(String(50), default="")
    lap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def thieu_gio(self) -> bool:
        """Yêu cầu chưa đủ hai mốc giờ. Không phải lỗi – là việc còn thiếu, phải hiện ra cho người
        nhập chứ không được lặng lẽ bỏ qua."""
        return self.bat_dau is None or self.ket_thuc is None


# Danh sách việc hay mở nhất là "yêu cầu chưa đủ người, sắp tới hạn", nên đánh chỉ mục theo đúng cặp
# ấy thay vì theo từng cột rời.
Index("ix_yeu_cau_hdv_trang_thai_bat_dau", YeuCauHdv.trang_thai, YeuCauHdv.bat_dau)


# ───────────────────────────── Đợt 2 · BÁO CÁO SAU TOUR (06/10/2026) ─────────────────────────────
#
# TRƯỚC ĐỢT NÀY, BÁO CÁO SAU TOUR LÀ MỘT Ô ĐÁNH DẤU. `guide_assignments.report_submitted` kiểu
# đúng/sai, và dòng chú thích cạnh nó ghi "báo cáo tour 4 phần" — tức ai đó đã định nghĩa nội dung từ
# lâu mà chưa dựng chỗ chứa. Một ô đánh dấu thì ai cũng tick được, tick rồi thì không ai đọc lại được
# gì, và cái cột ấy đang gánh hai quyết định thật: treo chào chuyến mới sau 3 ngày
# (app/api/v1/huong_dan.py) và treo thù lao (app/services/luong.py).
#
# NỘI DUNG LẤY TỪ ĐÂU: sáu phần dưới đây lấy đúng mục 05 "Form chuẩn — Báo cáo sau tour" của bản đặc
# tả phòng HDV v1.0 ngày 06/10/2026. KHÔNG lấy theo "4 phần" của báo cáo NGÀY (`daily_reports`) —
# bốn phần ấy là việc đã làm / số liệu ngày / khó khăn / kế hoạch mai, dựng cho chấm công hằng ngày,
# không phải cho một chuyến đã chạy xong.
#
# GỬI RỒI THÌ KHOÁ, SỬA LÀ BẢN MỚI. Báo cáo sau tour là căn cứ để quyết toán và để trả thù lao; sửa
# đè lên bản đã gửi thì người kiểm đã đọc một bản, hệ thống giữ một bản khác, và không ai biết. Bản
# mới trỏ về bản cũ bằng `thay_cho_id`, nên đọc ngược được cả chuỗi.
#
# `so_khach_thuc_te` ĐỂ TRỐNG ĐƯỢC và KHÔNG mặc định: "chưa đếm" khác "đi 0 khách". Mặc định 0 ở đây
# thì mọi báo cáo chưa điền đều thành một chuyến không có khách nào, và con số ấy đi thẳng vào đối
# chiếu với booking.
TRANG_THAI_BC = {
    "nhap": "Nháp, chưa gửi",
    "da_gui": "Đã gửi, chờ Trưởng phòng kiểm",
    "can_bo_sung": "Trưởng phòng trả lại, cần bổ sung",
    "da_xac_nhan": "Trưởng phòng đã xác nhận",
}
# Chỉ bản ĐÃ XÁC NHẬN mới gỡ được treo chào chuyến và treo thù lao. Gửi xong mà chưa ai kiểm thì vẫn
# là còn nợ báo cáo — nếu không, chỉ cần bấm Gửi một tờ trống là hết bị treo.
BC_DA_XONG = ("da_xac_nhan",)
# Bản đã bị thay bằng bản mới thì không còn là bản đang xét.
BC_CON_HIEU_LUC = ("nhap", "da_gui", "can_bo_sung", "da_xac_nhan")

# Hạn nộp: 3 ngày kể từ ngày tour kết thúc — Chủ tịch chốt 06/10/2026. Con số 3 ngày KHÔNG phải mới:
# app/api/v1/huong_dan.py đã treo chào chuyến mới khi quá 3 ngày chưa báo cáo. Đặt lại một hằng số ở
# đây và để hai chỗ tự đếm riêng là cách chắc chắn để mai kia một chỗ đổi thành 5 mà chỗ kia vẫn 3.
HAN_NOP_NGAY = 3


class BaoCaoSauTour(Base):
    """Một bản báo cáo của MỘT hướng dẫn viên cho MỘT phân công. Nhiều bản cho cùng một phân công là
    chuyện thường: gửi, bị trả lại, gửi bản mới."""

    __tablename__ = "bao_cao_sau_tour"

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("guide_assignments.id"), index=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)
    guide_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)

    # Sáu phần nội dung – đặc tả v1.0 §05.
    chuong_trinh_thuc_hien: Mapped[str] = mapped_column(Text, default="")
    so_khach_thuc_te: Mapped[int | None] = mapped_column(Integer, nullable=True)
    danh_gia_ncc: Mapped[str] = mapped_column(Text, default="")
    su_co: Mapped[str] = mapped_column(Text, default="")
    khoan_chi_thu_ho: Mapped[str] = mapped_column(Text, default="")
    viec_chua_xong: Mapped[str] = mapped_column(Text, default="")

    ban_so: Mapped[int] = mapped_column(Integer, default=1)
    thay_cho_id: Mapped[int | None] = mapped_column(ForeignKey("bao_cao_sau_tour.id"), nullable=True)
    bi_thay: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    trang_thai: Mapped[str] = mapped_column(String(16), default="nhap", index=True)
    han_nop: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    nguoi_nop: Mapped[str] = mapped_column(String(50), default="")
    nop_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nguoi_kiem: Mapped[str] = mapped_column(String(50), default="")
    kiem_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Trả lại mà không nói thiếu gì thì người nộp đoán, và thường đoán sai – nên ô này BẮT BUỘC ở cửa
    # trả bổ sung, không phải ô tuỳ chọn.
    y_kien_kiem: Mapped[str] = mapped_column(Text, default="")

    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def da_khoa(self) -> bool:
        """Đã gửi thì nội dung khoá. Nháp và bản bị trả lại thì còn sửa tại chỗ được."""
        return self.trang_thai in ("da_gui", "da_xac_nhan")

    def tre_han(self, hom_nay: date | None = None) -> bool:
        """Quá hạn mà CHƯA xác nhận. Thiếu hạn thì không kết luận trễ – chưa biết hạn khác hẳn đúng hạn."""
        if self.han_nop is None or self.trang_thai in BC_DA_XONG:
            return False
        return (hom_nay or date.today()) > self.han_nop


Index("ix_bao_cao_sau_tour_assignment_trang_thai", BaoCaoSauTour.assignment_id, BaoCaoSauTour.trang_thai)


# ═════════════════════ Đợt 3 · TIỀN CỦA HƯỚNG DẪN VIÊN (07/10/2026) ═════════════════════
#
# VÌ SAO PHẢI CÓ SỔ TẠM ỨNG THEO NGƯỜI
#
# Hôm nay tiền ứng cho hướng dẫn viên nằm ở `tour_guide_advances`, và bảng ấy gắn vào
# `settlement_id` — tức gắn vào TỜ QUYẾT TOÁN, không gắn vào CON NGƯỜI. Hệ quả: câu "hướng dẫn viên
# Thắng còn nợ ứng bao nhiêu" không hỏi được, vì không có chỗ nào cộng theo người. Mà đó lại là câu
# duy nhất cần trả lời trước khi đưa tiếp một khoản ứng mới.
#
# Bảng này KHÔNG thay `tour_guide_advances`. Bảng kia là dòng chi trên tờ quyết toán của một chuyến;
# bảng này là SỔ của một người. Hai cái trả lời hai câu khác nhau và cùng tồn tại.
#
# KHÔNG GỘP KHÁC CHỦ TIỀN, KHÁC LOẠI TIỀN
#
# Đặc tả v1.0 §06 nói thẳng: "không tự gộp khác pháp nhân/ngoại tệ". Một người có thể cầm 5 triệu
# đồng của Vietourist và 300 đô của một đối tác — cộng lại thành "số dư 5.3" là một con số không có
# thật và không ai trả được. Nên hàm tính số dư trả về NHIỀU TÚI, không trả một con số; xem
# `app/services/hdv.py`.
#
# SỐ ÂM KHÔNG PHẢI LỖI. Chi hộ vượt tiền ứng là chuyện thường: hướng dẫn viên bỏ tiền túi trả thêm
# cho đoàn. Số âm nghĩa là CÔNG TY NỢ LẠI, và nó phải hiện ra để có người xem xét trả — hệ thống
# KHÔNG tự trả.
#
# TIỀN THU HỘ KHÁCH THEO DÕI RIÊNG, không bù trừ tự động vào số dư ứng: tiền ấy là của khách, chỉ
# đang nằm trong túi hướng dẫn viên. Trộn vào số dư ứng là lấy tiền khách che một khoản công ty nợ.
CHU_TIEN = {
    "vietourist": "Tiền của Vietourist",
    "doi_tac": "Tiền của đối tác / nhà cung cấp",
    "khach": "Tiền thu hộ khách — KHÔNG bù trừ vào số dư ứng",
}
TRANG_THAI_UNG = {
    "de_nghi": "Đề nghị, chưa nhận tiền",
    "da_nhan": "Đã nhận tiền, đang mở",
    "tat_toan": "Đã tất toán",
    "huy": "Đã huỷ",
}
UNG_DANG_MO = ("de_nghi", "da_nhan")


class TamUngHdv(Base):
    """Một khoản ứng của MỘT hướng dẫn viên. Sổ theo người, không theo tờ quyết toán."""

    __tablename__ = "tam_ung_hdv"

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    guide_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("guide_assignments.id"), nullable=True, index=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)

    chu_tien: Mapped[str] = mapped_column(String(16), default="vietourist", index=True)
    loai_tien: Mapped[str] = mapped_column(String(3), default="VND", index=True)

    # BỐN CỘT TIỀN, TẤT CẢ ĐỂ TRỐNG ĐƯỢC VÀ KHÔNG MẶC ĐỊNH (luật K2). "Chưa nhận tiền" khác "nhận 0
    # đồng": khoản mới đề nghị chưa chi thì `da_nhan` phải TRỐNG, không phải 0 — nếu là 0 thì nó lẫn
    # vào những khoản đã chi xong và trả về đúng 0.
    de_nghi: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_nhan: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chi_ho_duyet: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_nop_lai: Mapped[float | None] = mapped_column(TIEN, nullable=True)

    muc_dich: Mapped[str] = mapped_column(String(200), default="")
    trang_thai: Mapped[str] = mapped_column(String(12), default="de_nghi", index=True)
    ngay_de_nghi: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_nhan: Mapped[date | None] = mapped_column(Date, nullable=True)
    ngay_tat_toan: Mapped[date | None] = mapped_column(Date, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(Text, default="")

    nguoi_lap: Mapped[str] = mapped_column(String(50), default="")
    lap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def so_du(self) -> float:
        """Thực nhận − chi hộ được duyệt − đã nộp lại.

        Dương: hướng dẫn viên còn giữ tiền công ty. Âm: công ty nợ lại người ấy — KHÔNG phải lỗi, và
        hệ thống không tự trả. Mọi cột đọc với `or 0` theo luật K2: rỗng là chưa có, và chưa có thì
        không đóng góp gì vào phép trừ.
        """
        return float(self.da_nhan or 0) - float(self.chi_ho_duyet or 0) - float(self.da_nop_lai or 0)

    def dang_mo(self) -> bool:
        return self.trang_thai in UNG_DANG_MO


Index("ix_tam_ung_hdv_guide_trang_thai", TamUngHdv.guide_id, TamUngHdv.trang_thai)
Index("ix_tam_ung_hdv_tui", TamUngHdv.guide_id, TamUngHdv.chu_tien, TamUngHdv.loai_tien)


# ══════════════ Đợt 4 · ĐỀ XUẤT CỦA PHÒNG HDV VÀ BƯỚC DUYỆT CÓ CẤP (07/10/2026) ══════════════
#
# Đặc tả v1.0 §10–§12. Đợt này dựng CÁI MÁY; các CON SỐ (loại hồ sơ nào, hạn mức bao nhiêu, ai duyệt)
# là chính sách và phải có người ký — xem `CauHinhDuyetHdv` dưới đây, bảng ấy sinh ra RỖNG.
#
# THIẾU CẤU HÌNH THÌ CHẶN TRÌNH, KHÔNG CHO BỎ CẤP. Đây là câu quan trọng nhất của cả đợt, và nó lấy
# nguyên từ §10 của đặc tả. Nếu thiếu cấu hình mà vẫn cho trình thì hệ thống phải tự chọn một đường
# đi — và đường nó chọn sẽ thành tiền lệ, không ai ký mà vẫn thành luật. Chặn thì có người đi hỏi,
# và câu trả lời được ghi lại thành cấu hình có chữ ký.
#
# KHÔNG GIẢ ĐỊNH TGĐ VÀ CHỦ TỊCH THAY NHAU. §10 nói rõ: "Không giả định hai người thay nhau hoặc hồ
# sơ nào cũng cần cả hai". Nên các cấp lưu thành MỘT DANH SÁCH CÓ THỨ TỰ, mỗi cấp một vai trò; muốn
# hai người cùng ký một cấp thì khai hai cấp. Không có đường tắt nào trong mã.
LOAI_DE_XUAT = {
    "thue_ctv": "Thuê hướng dẫn viên / cộng tác viên",
    "thu_lao": "Thù lao, phụ cấp, công tác phí",
    "tam_ung": "Tạm ứng / hoàn ứng",
    "phat_sinh_tour": "Phát sinh trong tour",
    "dao_tao": "Đào tạo, bổ sung nhân sự",
    "doi_soat_ky": "Đối soát thù lao kỳ",
}
TRANG_THAI_DX = {
    "nhap": "Nháp",
    "cho_duyet": "Đang chờ duyệt",
    "can_bo_sung": "Trả lại, cần bổ sung",
    "tu_choi": "Đã từ chối",
    "da_duyet": "Đã duyệt đủ cấp",
}
DX_DANG_CHAY = ("nhap", "cho_duyet", "can_bo_sung")
QUYET_DINH = ("dong_y", "tra_bo_sung", "tu_choi")


class CauHinhDuyetHdv(Base):
    """Một dòng = một khoảng tiền của một loại hồ sơ, và danh sách cấp duyệt cho khoảng ấy.

    BẢNG NÀY SINH RA RỖNG, CỐ Ý. Nội dung của nó là chính sách phê duyệt — ai duyệt tới mức tiền nào —
    và đó là thứ phải có chữ ký, không phải thứ robot tự đặt. Chừng nào chưa có dòng nào khớp thì cửa
    trình CHẶN, kèm câu nói rõ thiếu cấu hình nào.

    `den_so_tien` RỖNG nghĩa là KHÔNG CÓ TRẦN (khoảng cuối cùng). Không phải "chưa biết": một khoảng
    tiền thiếu trần sẽ để lọt mọi hồ sơ lớn hơn mức cao nhất đã khai, và đó là đúng những hồ sơ cần
    cấp cao nhất.

    `cac_cap` là chuỗi vai trò ngăn bằng dấu phẩy, THEO THỨ TỰ phải ký. Ví dụ "ptgd_doan,tgd,chutich".

    Trong MỘT cấp, nhiều vai trò ngăn bằng dấu `|` nghĩa là MỘT NGƯỜI BẤT KỲ trong số đó ký là xong cấp
    ấy — không phải tất cả. Ví dụ "chutich|tgd" là MỘT cấp, Chủ tịch hoặc Tổng giám đốc ký đều được
    (quyết định 06/10/2026). So với "chutich,tgd" là HAI cấp, phải đủ cả hai chữ ký. Phân biệt hai cái
    bằng dấu là cố ý: ghi nhầm dấu thì sai số lượng chữ ký, nên dấu phải khác nhau rõ, không suy diễn.
    """

    __tablename__ = "cau_hinh_duyet_hdv"

    id: Mapped[int] = mapped_column(primary_key=True)
    loai: Mapped[str] = mapped_column(String(20), index=True)
    tu_so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    den_so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    cac_cap: Mapped[str] = mapped_column(String(200), default="")
    hieu_luc_tu: Mapped[date | None] = mapped_column(Date, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho_ky", index=True)
    ky_boi: Mapped[str] = mapped_column(String(120), default="")
    ky_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(200), default="")
    lap_boi: Mapped[str] = mapped_column(String(50), default="")
    lap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def danh_sach_cap(self) -> list[str]:
        return [x.strip() for x in (self.cac_cap or "").split(",") if x.strip()]


class DeXuatHdv(Base):
    """Đề xuất của phòng Hướng dẫn trình lên cấp có thẩm quyền (đặc tả v1.0 §10)."""

    __tablename__ = "de_xuat_hdv"

    phien_ban: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    loai: Mapped[str] = mapped_column(String(20), index=True)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True, index=True)
    guide_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    ky: Mapped[str] = mapped_column(String(7), default="")

    noi_dung: Mapped[str] = mapped_column(Text, default="")
    ly_do: Mapped[str] = mapped_column(Text, default="")
    can_cu_tinh: Mapped[str] = mapped_column(Text, default="")
    # Rỗng được: có đề xuất không mang tiền (xin bổ sung nhân sự). Rỗng KHÁC 0, và phép chọn cấu hình
    # phân biệt hai cái: không có tiền thì rơi vào khoảng bắt đầu từ 0.
    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    loai_tien: Mapped[str] = mapped_column(String(3), default="VND")
    han_xu_ly: Mapped[date | None] = mapped_column(Date, nullable=True)

    trang_thai: Mapped[str] = mapped_column(String(14), default="nhap", index=True)
    cap_dang_cho: Mapped[int] = mapped_column(Integer, default=0)   # thứ tự bước đang chờ, 0 = chưa trình
    cau_hinh_id: Mapped[int | None] = mapped_column(ForeignKey("cau_hinh_duyet_hdv.id"), nullable=True)

    nguoi_lap: Mapped[str] = mapped_column(String(50), default="")
    lap_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    trinh_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    xong_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BuocDuyetHdv(Base):
    """Một bước duyệt của một đề xuất. Lập đủ các bước NGAY LÚC TRÌNH, không sinh dần từng bước.

    Lập sẵn thì người trình nhìn thấy cả đường đi trước khi gửi, và ai cũng đọc được hồ sơ này còn
    qua mấy cửa. Sinh dần thì mỗi lần chỉ biết cửa kế tiếp, và không ai trả lời được "bao giờ xong".
    """

    __tablename__ = "buoc_duyet_hdv"

    id: Mapped[int] = mapped_column(primary_key=True)
    de_xuat_id: Mapped[int] = mapped_column(ForeignKey("de_xuat_hdv.id", ondelete="CASCADE"), index=True)
    thu_tu: Mapped[int] = mapped_column(Integer, default=1)
    # Rộng hơn một tên vai trò vì một bước có thể nhận NHIỀU vai trò thay thế nhau, ngăn bằng `|`.
    vai_tro: Mapped[str] = mapped_column(String(60))
    trang_thai: Mapped[str] = mapped_column(String(14), default="cho", index=True)  # cho / dong_y / tra_bo_sung / tu_choi
    nguoi: Mapped[str] = mapped_column(String(50), default="")
    luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    y_kien: Mapped[str] = mapped_column(Text, default="")

    def cac_vai(self) -> list[str]:
        """Các vai trò ký được bước này. Một phần tử = một cấp một vai; nhiều phần tử = ai cũng được."""
        return [x.strip() for x in (self.vai_tro or "").split("|") if x.strip()]


Index("ix_buoc_duyet_hdv_de_xuat_thu_tu", BuocDuyetHdv.de_xuat_id, BuocDuyetHdv.thu_tu)
