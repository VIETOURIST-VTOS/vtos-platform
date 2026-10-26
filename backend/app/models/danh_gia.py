"""Đánh giá sau tour — khách tự chấm, và mã khảo sát dùng một lần.

Đề xuất tự động hoá CSKH ngày 25/9/2026, bước 2: "Khách chấm 1–5 sao cho tour, HDV, tài xế và ghi
góp ý." Trước hôm nay VTOS chỉ có MỘT ô điểm (`care_tickets.hai_long`) và ô ấy do NHÂN VIÊN gõ hộ.

═══════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO LÀ MỘT BẢNG RIÊNG, KHÔNG PHẢI BA CỘT THÊM VÀO `care_tickets`
═══════════════════════════════════════════════════════════════════════════════════════════════
Ba cột `diem_tour`, `diem_hdv`, `diem_tai_xe` nhìn thì gọn, nhưng một chuyến có thể có HAI hướng
dẫn viên và HAI tài xế. Khách chấm người thứ hai vào đâu? Và ngày thêm "khách sạn" thì lại thêm
một cột nữa, trong khi bảng điểm vẫn không cộng được theo từng người.

Một dòng một đối tượng thì cộng được theo người, theo chuyến, theo tháng, và thêm loại đối tượng
mới không phải đổi bảng.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

# Đối tượng được chấm. Khoá `doi_tuong_id` trỏ vào đâu là tuỳ loại — ghi rõ ở đây để không ai phải
# đoán: "hdv" và "tai_xe" trỏ vào `employees.id`, "ncc" trỏ vào `suppliers.id`, "tour" không có
# khoá (chấm cả chuyến).
DG_DOI_TUONG = {
    "tour": "Chuyến đi",
    "hdv": "Hướng dẫn viên",
    "tai_xe": "Tài xế",
    "khach_san": "Khách sạn",
    "an_uong": "Ăn uống",
    # KH-4 (Chủ tịch duyệt 27/10/2026): khách chấm trên cổng thêm bốn mảng. Không có khoá người —
    # chấm theo mảng như khách sạn / ăn uống; tên chụp lại lúc chấm (tên Sales với «tu_van»).
    "hanh_trinh": "Hành trình / lịch trình",
    "xe": "Chất lượng xe",
    "tham_quan": "Điểm tham quan",
    "tu_van": "Tư vấn & đặt chỗ",
}
DG_CO_KHOA = ("hdv", "tai_xe")          # hai loại này BẮT BUỘC có doi_tuong_id (employees.id)

# Ai gõ con số. Đây là cột quan trọng nhất của bảng — xem chú thích ở lớp dưới.
DG_NGUON = {"khach": "Khách tự chấm", "nhan_vien": "Nhân viên ghi hộ"}


class DanhGiaSauTour(Base):
    """Một dòng = một điểm khách chấm cho một đối tượng của một chuyến."""
    __tablename__ = "danh_gia_sau_tour"

    id: Mapped[int] = mapped_column(primary_key=True)
    care_id: Mapped[int] = mapped_column(ForeignKey("care_tickets.id"), index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    tour_id: Mapped[int] = mapped_column(ForeignKey("tours.id"), index=True)

    doi_tuong: Mapped[str] = mapped_column(String(12), index=True)          # xem DG_DOI_TUONG
    doi_tuong_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    doi_tuong_ten: Mapped[str] = mapped_column(String(120), default="")
    # Tên chép lại lúc chấm, CỐ Ý. Hướng dẫn viên nghỉ việc và hồ sơ bị xoá thì điểm cũ vẫn phải
    # đọc được là chấm cho ai — bài học của bia mộ tài khoản (TC-83, 24/9/2026).

    # RỖNG khác 0. Khách bỏ qua mục "tài xế" vì chuyến đi bộ không có xe; ghi 0 thì điểm trung bình
    # của tài xế tụt vì một chuyến không có tài xế nào. Đây đúng là "thiếu chi phí không phải là
    # chi phí bằng 0" của Ý kiến thẩm định 06/9/2026, lặp lại trên một cột khác.
    diem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nhan_xet: Mapped[str] = mapped_column(Text, default="")                # nguyên văn lời khách

    # ── CỘT QUAN TRỌNG NHẤT CỦA BẢNG ─────────────────────────────────────────────────────────
    # Nó phân biệt điểm khách TỰ bấm với điểm nhân viên gõ hộ. Báo cáo gửi Ban lãnh đạo chỉ nên
    # cộng phần `nguon = "khach"`: khi không còn bộ phận chăm sóc riêng, người gọi lại khách chấm
    # thấp chính là người bị chấm, và một con số do người bị đo nhập vào thì không đo được ai.
    # Không có cột này thì hai loại số trộn vào nhau và không ai tách ra được nữa.
    nguon: Mapped[str] = mapped_column(String(10), default="khach", index=True)
    nguoi_ghi: Mapped[str] = mapped_column(String(50), default="")         # rỗng khi khách tự chấm
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class MaKhaoSat(Base):
    """Mã dùng một lần để khách mở trang tự chấm — KHÔNG cần đăng nhập.

    ═══════════════════════════════════════════════════════════════════════════════════════════
    ĐÂY LÀ CỬA CÔNG KHAI ĐẦU TIÊN CỦA VTOS
    ═══════════════════════════════════════════════════════════════════════════════════════════
    Mọi cửa khác đều đứng sau `Depends(current_user)`. Cửa này thì không, vì khách không có tài
    khoản. Nên nó phải được viết như một cửa ra đường, không như một cửa trong nhà:

        · `ma` sinh bằng `secrets.token_urlsafe` — KHÔNG suy được từ `booking_id`. Mã chạy theo số
          thứ tự thì ai cũng đọc được đánh giá của người khác bằng cách cộng một.
        · Một mã, MỘT lần ghi. Ghi xong `dung_luc` đóng lại.
        · Có hạn. Mã sống mãi là một cửa mở mãi.
        · `so_lan_mo` đếm số lần mở — đây chính là thước đo "khách có đọc tin không" mà mốc nghiệm
          thu 31/10 của đề xuất cần, và hôm nay hệ thống chưa có.
    """
    __tablename__ = "ma_khao_sat"

    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    care_id: Mapped[int] = mapped_column(ForeignKey("care_tickets.id"), unique=True, index=True)
    het_han: Mapped[datetime] = mapped_column(DateTime, index=True)
    dung_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    so_lan_mo: Mapped[int] = mapped_column(Integer, default=0)
    mo_lan_dau: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ---------- Đếm lượt mở cửa đọc (Đợt HD-Q2a, 16/10/2026) ----------
class LuotDocCua(Base):
    """Mỗi người × mỗi cửa đọc × mỗi ngày một dòng. KHÔNG ghi gì về khách.

    Dựng ra vì trước đợt này hệ thống không có nhật ký đọc: `audit_log` chỉ ghi thao tác GHI, nên
    câu hỏi «mỗi ngày mỗi vai mở bao nhiêu phiếu» — câu Chủ tịch cần để bấm ngày siết quyền — không
    có dữ liệu nào trả lời được. Xem `services/dem_luot.py` để biết vì sao có cột `so_phut` bên
    cạnh `so_luot`.

    ĐỂ Ở TỆP NÀY CHỨ KHÔNG Ở `models/core.py`, và đó là một lựa chọn chứ không phải chỗ tiện tay.
    Hai lẽ. Một: bảng này đếm lượt mở các cửa của chính phân hệ đánh giá và chăm sóc, nên nó thuộc
    về đây. Hai: `core.py` hôm nay đang được làn Phân quyền sửa cho Đợt DX-3, và vòng này commit
    NGUYÊN TỆP — đặt bảng vào `core.py` là hai làn cùng ghi một tệp, đúng thứ hàng rào giữ chỗ dựng
    ra để chặn. Tệp này đã có sẵn dòng nhập trong `models/__init__.py`, nên không phải chạm tới tệp
    ấy — mà tệp ấy cũng đang bị bốn dòng khác giữ.
    """

    __tablename__ = "luot_doc_cua"
    __table_args__ = (UniqueConstraint("ngay", "username", "cua", name="uq_luot_doc_cua"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ngay: Mapped[date] = mapped_column(Date, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(30), index=True)
    cua: Mapped[str] = mapped_column(String(40), index=True)
    so_luot: Mapped[int] = mapped_column(Integer, default=0)
    # Số PHÚT KHÁC NHAU trong ngày có ít nhất một lượt — chống màn hình tự nạp lại làm phồng số lượt.
    so_phut: Mapped[int] = mapped_column(Integer, default=0)
    phut_cuoi: Mapped[str] = mapped_column(String(5), default="")
    so_dong: Mapped[int] = mapped_column(Integer, default=0)


# ---------- Đồng ý công khai nhận xét (Đợt HD-DG3, 16/10/2026) ----------
class DongYCongKhai(Base):
    """Một nhận xét = một bản ghi. Hai việc KHÁC NHAU nằm chung một dòng, cố ý — đọc chú thích.

    VIỆC THỨ NHẤT, CỦA KHÁCH: đồng ý hay không, và rút lúc nào. Cột `cau_hoi` chép NGUYÊN VĂN câu
    đã hỏi, không trỏ sang một hằng số — ngày câu hỏi đổi thì các bản ghi cũ vẫn giữ câu đã hỏi
    lúc ấy. Một bản ghi đồng ý mà không nói được «đồng ý với điều gì» thì nó không chứng minh
    được gì cả.

    VIỆC THỨ HAI, CỦA CÔNG TY: ai duyệt, lúc nào, bằng quyền nào, và ai gỡ. `duyet_bang_quyen`
    ghi "vai" hay "cap_dich_danh" — vì quyền duyệt của anh Nguyễn Tất Thắng là ngoại lệ có hạn
    cấp qua `user_grants`, và sáu tháng sau câu «ai quyết cái này, bằng quyền gì» phải trả lời
    được mà không phải đi tra chéo hai bảng.

    HAI VIỆC CHUNG MỘT DÒNG vì chúng 1:1 với một nhận xét và luôn được đọc cùng nhau: câu hỏi duy
    nhất mọi cửa công khai đặt ra là «nhận xét này hiện được không», và câu ấy cần cả hai vế.
    Tách đôi bảng thì mỗi lần hỏi phải nối hai bảng, và ngày ai đó quên nối là một lời khách đã
    rút vẫn nằm trên mạng.

    KHÔNG CÓ CỬA XOÁ, và không có cửa nhập tay. Rút là NGỪNG CÔNG KHAI, không phải xoá: lời nhận
    xét vẫn ở sổ nội bộ theo thời hạn lưu nhóm «11 · Phản hồi khách hàng». Cùng một lẽ với luật
    giữ chỗ Chủ tịch chốt 11/9/2026 — hết hạn không phải là huỷ.
    """

    __tablename__ = "dong_y_cong_khai"
    __table_args__ = (UniqueConstraint("danh_gia_id", name="uq_dong_y_cong_khai_danh_gia"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    danh_gia_id: Mapped[int] = mapped_column(ForeignKey("danh_gia_sau_tour.id"), index=True)
    care_id: Mapped[int] = mapped_column(Integer, index=True)
    tour_id: Mapped[int] = mapped_column(Integer, index=True)

    # ── Việc của khách ────────────────────────────────────────────────────────────────────────
    pham_vi: Mapped[str] = mapped_column(String(32), default="ho_so_hdv_cong_khai", index=True)
    cau_hoi: Mapped[str] = mapped_column(Text, default="")       # nguyên văn, xem docstring
    tra_loi: Mapped[str] = mapped_column(String(6), index=True)  # "co" | "khong" — không có mặc định
    hoi_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    nguon: Mapped[str] = mapped_column(String(12), default="khao_sat")

    # Mã rút dùng MỘT lần. Rỗng nghĩa là không còn rút được bằng đường dẫn: hoặc khách trả lời
    # "khong" (không có gì để rút), hoặc đã rút rồi.
    ma_rut: Mapped[str] = mapped_column(String(64), default="", index=True)
    ma_rut_het_han: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rut_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    rut_ly_do: Mapped[str] = mapped_column(String(500), default="")

    # ── Việc của công ty ──────────────────────────────────────────────────────────────────────
    duyet_boi: Mapped[str] = mapped_column(String(50), default="")
    duyet_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    duyet_bang_quyen: Mapped[str] = mapped_column(String(16), default="")   # vai | cap_dich_danh
    duyet_ket_qua: Mapped[str] = mapped_column(String(12), default="", index=True)  # dang | khong_dang
    duyet_ly_do: Mapped[str] = mapped_column(String(1000), default="")

    go_boi: Mapped[str] = mapped_column(String(50), default="")
    go_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    go_ly_do: Mapped[str] = mapped_column(String(1000), default="")
