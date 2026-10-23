# -*- coding: utf-8 -*-
"""SỐ DƯ ĐẦU KỲ — Đợt R6b-1, 23/10/2026. Một cửa chốt và bảy sổ phụ.

VÌ SAO TÁM BẢNG CHỨ KHÔNG MỘT BẢNG

Số dư đầu kỳ của một tài khoản là MỘT con số, nhưng nó phải trả lời được HAI câu hỏi khác nhau:

  · "TK 131 đầu kỳ dư bao nhiêu?"              → một dòng, cửa chốt
  · "Trong đó khách nào nợ bao nhiêu?"         → nhiều dòng, sổ phụ

Nhập một chỗ rồi suy ra chỗ kia thì mất một trong hai. Nhập hai chỗ rồi không đối chiếu thì
có hai sự thật. Nên: nhập CẢ HAI, và phép đối chiếu nằm ngay trong cách chia bảng — tổng sổ
phụ của một tài khoản phải bằng đúng dòng cửa chốt của tài khoản ấy. Lệch là một câu hỏi về
số liệu, và người trả lời là Kế toán, không phải phần mềm.

MÃ ĐỐI TƯỢNG LÀ BẮT BUỘC, GIỐNG MISA (Chủ tịch chốt 23/10/2026)

Mỗi dòng sổ phụ phải mang mã đối tượng. Một dòng "khách hàng nợ 200 triệu" không có mã thì
sang kỳ sau không ai đối chiếu được với ai, và nó cũng không cộng được vào bất kỳ báo cáo
công nợ nào — vì báo cáo công nợ gom theo mã.

NHƯNG CỘT `ma_doi_tuong` CHO RỖNG, và đó là chủ ý. Hai luật khác nhau:

  · dòng thiếu mã KHÔNG được cộng vào tổng đối chiếu — nếu cộng thì cửa chốt trông như khớp
    trong khi một phần tiền chưa biết thuộc về ai;
  · dòng thiếu mã KHÔNG bị xoá đi — nó là số liệu có thật mà người nhập vừa đưa vào, và xoá
    đi là làm mất tiền khỏi sổ để bảng trông sạch. Nó nằm đó, hiện màu khác, chờ gán mã.

Đặt `nullable=False, default=""` chứ không `nullable=True`: ô rỗng là MỘT TRẠNG THÁI có nghĩa
("chưa gán mã"), không phải "chưa khai cột". Hai thứ ấy đọc ra khác nhau ở mọi phép gom.

CỘT `ky` LÀ KỲ GỐC, KHÔNG PHẢI KỲ BẤT KỲ

Dạng "YYYY-MM", cùng khuôn với `period_locks.period`. Số dư đầu kỳ chỉ nhập MỘT LẦN cho kỳ
gốc của hệ (01/2026 với Vietourist); các kỳ sau do bộ kết sổ sinh ra. Giữ cột `ky` thay vì
viết cứng kỳ gốc vì một pháp nhân mới nhập hệ sau sẽ có kỳ gốc khác, và một con số viết cứng
là một con số không ai sửa được khi điều đó xảy ra.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN


# QUY TAC 4 cua services/nhap_lieu.py: "o trong la CHUA CO SO. Khong thay bang 0 o bat ky cua nao."
#
# Moi cot tien duoi day vi vay deu CHO RONG va KHONG co gia tri mac dinh. Mot cot tien vua co
# mac dinh 0 vua khong cho rong thi "chua nhap" va "bang 0" la MOT, khong phan biet duoc — dung
# cho mu ma Dot K2 sinh ra de xoa, va `test_kt12` bat duoc dung hai cot cua ban dau tep nay.
#
# Khac biet nay co that, khong phai hinh thuc: khau hao luy ke TRONG la chua ai khai, con 0 la
# tai san moi mua chua trich dong nao; chi phi do dang TRONG la chua nhap, con 0 la cong trinh
# da het do dang. Ghi ca hai thanh 0 la xoa mat mot cau tra loi.


class SoDuDauKy(Base):
    """CỬA CHỐT — số dư đầu kỳ của từng tài khoản. Bảy sổ phụ phải cộng về đúng đây.

    Hai cột `du_no` / `du_co` chứ không một cột có dấu: một tài khoản lưỡng tính (3388, 1388)
    có thể vừa dư Nợ ở đối tượng này vừa dư Có ở đối tượng kia, và cộng dồn thành một con số
    có dấu là xoá mất chính cái bất thường mà phép kiểm số dư ngược chiều đi tìm.
    """

    __tablename__ = "so_du_dau_ky"

    ky: Mapped[str] = mapped_column(String(7), primary_key=True)
    tk: Mapped[str] = mapped_column(ForeignKey("accounts.code"), primary_key=True)
    du_no: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du_co: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")   # nhap_tay / nap_tep
    ghi_boi: Mapped[str] = mapped_column(String(50), default="")
    ghi_luc: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class _SoPhu(Base):
    """Phần chung của bảy sổ phụ. Không phải bảng — lớp trừu tượng.

    KHÔNG có ràng buộc DUY NHẤT trên (ky, tk, ma_doi_tuong), và lý do là luật ở đầu tệp: dòng
    thiếu mã được giữ lại. Ba dòng chưa gán mã trên cùng một tài khoản là ba dòng hợp lệ, mà
    một ràng buộc duy nhất sẽ chặn đúng dòng thứ hai — tức là người nhập mất số liệu ở chỗ
    đáng ra chỉ cần một cảnh báo.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    ky: Mapped[str] = mapped_column(String(7), index=True)
    tk: Mapped[str] = mapped_column(ForeignKey("accounts.code"), index=True)
    # Rỗng = CHƯA GÁN MÃ. Không cộng vào tổng, và không bị xoá. Xem đầu tệp.
    ma_doi_tuong: Mapped[str] = mapped_column(String(60), default="", index=True)
    ten: Mapped[str] = mapped_column(String(300), default="")
    nguon: Mapped[str] = mapped_column(String(20), default="nhap_tay")
    ghi_boi: Mapped[str] = mapped_column(String(50), default="")
    ghi_luc: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now)


class SoDuDauKyNganHang(_SoPhu):
    """Sổ phụ TK ngân hàng. Mã đối tượng = mã ngân hàng/tài khoản trong danh mục `partners`.

    Ba cột ngoại tệ có mặt vì một tài khoản USD có HAI con số đầu kỳ — số nguyên tệ và số đã
    quy đổi — và chỉ giữ số quy đổi thì phép đánh giá lại cuối kỳ không có gốc để đánh giá.
    Để trống nghĩa là tài khoản VND, không phải "tỷ giá 0".
    """

    __tablename__ = "so_du_dau_ky_ngan_hang"

    so_tai_khoan: Mapped[str] = mapped_column(String(40), default="")
    ngan_hang: Mapped[str] = mapped_column(String(200), default="")
    du_no: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du_co: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    loai_tien: Mapped[str] = mapped_column(String(3), default="VND")
    so_nguyen_te: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    ty_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)


class SoDuDauKyKhachHang(_SoPhu):
    """Sổ phụ công nợ khách hàng. Mã đối tượng = mã khách trong `partners` (MST / CCCD)."""

    __tablename__ = "so_du_dau_ky_khach_hang"

    du_no: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du_co: Mapped[float | None] = mapped_column(TIEN, nullable=True)


class SoDuDauKyNhaCungCap(_SoPhu):
    """Sổ phụ công nợ nhà cung cấp. Mã đối tượng = mã NCC trong `partners`."""

    __tablename__ = "so_du_dau_ky_nha_cung_cap"

    du_no: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du_co: Mapped[float | None] = mapped_column(TIEN, nullable=True)


class SoDuDauKyNhanVien(_SoPhu):
    """Sổ phụ công nợ nhân viên (tạm ứng 141, phải trả 334). Mã đối tượng = mã nhân viên."""

    __tablename__ = "so_du_dau_ky_nhan_vien"

    du_no: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    du_co: Mapped[float | None] = mapped_column(TIEN, nullable=True)


class SoDuDauKyTaiSan(_SoPhu):
    """Sổ phụ tài sản cố định & công cụ dụng cụ. Mã đối tượng = mã tài sản.

    BA CỘT, KHÔNG MỘT CỘT. Cửa chốt của TK 211 chỉ cần nguyên giá, nhưng một thẻ tài sản mở
    giữa đời nó cần cả khấu hao đã trích và số kỳ còn lại — thiếu hai cột ấy thì bộ khấu hao
    kỳ đầu tiên sẽ trích lại từ đầu trên một tài sản đã dùng ba năm.
    """

    __tablename__ = "so_du_dau_ky_tai_san"

    nguyen_gia: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    khau_hao_luy_ke: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    gia_tri_con_lai: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_ky_con: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bo_phan: Mapped[str] = mapped_column(String(20), default="")


class SoDuDauKyTraTruoc(_SoPhu):
    """Sổ phụ chi phí trả trước (242). Mã đối tượng = mã khoản trả trước."""

    __tablename__ = "so_du_dau_ky_tra_truoc"

    gia_tri_ban_dau: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    da_phan_bo: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    con_lai: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    so_ky_con: Mapped[int | None] = mapped_column(Integer, nullable=True)
    khoan_muc: Mapped[str] = mapped_column(String(40), default="")


class SoDuDauKyDoDang(_SoPhu):
    """Sổ phụ chi phí dở dang (154). Mã đối tượng = MÃ CÔNG TRÌNH, tức mã tour.

    Đây là sổ phụ duy nhất mà mã đối tượng không trỏ vào `partners` mà vào `projects`. Giữ
    cùng tên cột `ma_doi_tuong` là chủ ý: luật "thiếu mã thì không vào tổng, nhưng không bị
    xoá" phải viết MỘT LẦN cho bảy bảng, và nó chỉ viết một lần được nếu cột cùng tên.

    Phép kiểm 154 không công trình của Đợt R2-KC đọc đúng chỗ này cho kỳ gốc.
    """

    __tablename__ = "so_du_dau_ky_do_dang"

    so_tien: Mapped[float | None] = mapped_column(TIEN, nullable=True)
