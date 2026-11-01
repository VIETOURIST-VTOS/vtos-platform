"""KS-14 · ĐẶT PHÒNG KHÁCH SẠN VTD CÓ THANH TOÁN (Chủ tịch duyệt bản xem thử 30/10/2026).

Khách trả NGAY 100% như Agoda: chọn phòng → máy giữ phòng 15 phút → trả QR (tài khoản Vietourist, máy tự khớp
nội dung + đúng số tiền) hoặc thẻ qua OnePay → «Đã thanh toán» → Điều hành chốt với khách sạn trong 2 giờ làm
việc (nhập mã xác nhận của khách sạn) hoặc báo «khách sạn hết phòng» → hoàn 100%.

  · Số phòng bán mỗi đêm: mặc định = «số phòng/đêm» của loại phòng; Điều hành sửa từng đêm hoặc đóng bán
    (bảng `phong_trong_vtd`). Phòng «đã nhận» gồm đơn đang giữ 15 phút, đã trả, đã xác nhận.
  · Hủy theo gói: trước hạn miễn phí hủy → hoàn phần của gói đó; sau hạn / gói không hoàn → 0.
    Khách sạn hết phòng → hoàn 100%. Hoàn hai người: Sales xác nhận → Kế toán chuyển và ghi sổ.
    TP / GĐ Kinh doanh miễn phạt (ghi lý do) → hoàn đủ số đã trả.
  · Hạch toán THU HỘ khách sạn (như đặt bàn DT-3): tiền vào Nợ 1121 / Có 3388; hoàn Nợ 3388 / Có 1121.
    Hoa hồng của Vietourist là số Kế toán gõ theo hợp đồng sau khi khách trả phòng; phải trả khách sạn
    = đã thu − đã hoàn − hoa hồng, chi qua đề nghị chi NCC như mọi khoản trả nhà cung cấp.
  · Không ô nào cho trình duyệt gửi số tiền: giá, tổng, số hoàn đều máy tính từ gói giá đã duyệt.

Ba bảng mới, bắt đầu RỖNG.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.kieu_tien import TIEN

TRANG_THAI_DON = {"cho_tra": "Chờ thanh toán", "het_han": "Hết giờ giữ phòng", "da_tra": "Đã thanh toán · chờ khách sạn xác nhận",
                  "da_xac_nhan": "Đã xác nhận", "da_huy": "Đã hủy"}
HOAN_TT_KS = {"": "", "cho_sales": "Chờ Sales xác nhận hoàn", "cho_chi": "Chờ Kế toán hoàn tiền", "da_hoan": "Đã hoàn"}
KENH_KS = {"qr": "QR chuyển khoản", "onepay": "Thẻ (OnePay)", "sepay": "Thẻ (cổng SePay)"}
TT_TT_KS = {"cho": "Đang thanh toán", "that_bai": "Không thành công", "tu_khop": "Máy tự khớp · chờ Kế toán ghi sổ",
            "thanh_cong": "Cổng thẻ báo thành công · chờ đối soát", "da_doi_soat": "Đã đối soát", "da_xac_nhan": "Kế toán đã xác nhận"}
TT_DA_TRA_KS = ("tu_khop", "thanh_cong", "da_doi_soat", "da_xac_nhan")


class PhongTrongVtd(Base):
    """Điều hành sửa số phòng bán của MỘT loại phòng trong MỘT đêm. Không có dòng = dùng «số phòng/đêm»."""
    __tablename__ = "phong_trong_vtd"
    __table_args__ = (UniqueConstraint("loai_phong_id", "ngay", name="uq_phong_trong_vtd"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    loai_phong_id: Mapped[int] = mapped_column(ForeignKey("loai_phong_vtd.id"), index=True)
    ngay: Mapped[date] = mapped_column(Date, index=True)                 # đêm bắt đầu ngày này
    so_ban: Mapped[int | None] = mapped_column(Integer, nullable=True)    # None = theo hồ sơ loại phòng
    dong: Mapped[bool] = mapped_column(Boolean, default=False)            # đóng bán đêm này
    sua_boi: Mapped[str] = mapped_column(String(50), default="")
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DonKsVtd(Base):
    __tablename__ = "don_ks_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    ma: Mapped[str] = mapped_column(String(16), unique=True)             # KS + yymm + 4 ký tự, ghi vào nội dung CK
    khach_san_id: Mapped[int] = mapped_column(ForeignKey("khach_san_vtd.id"), index=True)
    tai_khoan_ngoai_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    cong: Mapped[str] = mapped_column(String(12), default="")            # khach_hang | doi_tac | co_dong
    ho_ten: Mapped[str] = mapped_column(String(120), default="")
    lien_he: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(160), default="")
    yeu_cau: Mapped[str] = mapped_column(Text, default="")
    vao: Mapped[date] = mapped_column(Date, index=True)
    ra: Mapped[date] = mapped_column(Date)
    nguoi_lon: Mapped[int] = mapped_column(Integer, default=1)
    tre_em: Mapped[int] = mapped_column(Integer, default=0)
    # [{goi_id, loai_phong_id, loai_phong, goi, so, tien, thue, bua_sang, huy_han}] — chụp lúc đặt, không đổi theo giá sau
    dong: Mapped[list] = mapped_column(JSON, default=list)
    so_phong: Mapped[int] = mapped_column(Integer, default=1)
    tien_phong: Mapped[float] = mapped_column(TIEN, default=0)
    thue_phi: Mapped[float] = mapped_column(TIEN, default=0)
    tong: Mapped[float] = mapped_column(TIEN, default=0)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho_tra", index=True)
    giu_den: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tra_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    han_chot: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ma_xac_nhan_ks: Mapped[str] = mapped_column(String(60), default="")
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    huy_boi: Mapped[str] = mapped_column(String(60), default="")
    huy_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ly_do_huy: Mapped[str] = mapped_column(String(300), default="")
    so_hoan: Mapped[float] = mapped_column(TIEN, default=0)
    hoan_tt: Mapped[str] = mapped_column(String(10), default="", index=True)
    mien_phat_boi: Mapped[str] = mapped_column(String(50), default="")
    da_hoan_tien: Mapped[float] = mapped_column(TIEN, default=0)
    hoan_boi: Mapped[str] = mapped_column(String(50), default="")
    hoan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    hoan_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    hoa_hong: Mapped[float | None] = mapped_column(TIEN, nullable=True)  # Kế toán gõ theo hợp đồng, sau khi khách trả phòng
    phai_tra_ks: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    chot_boi: Mapped[str] = mapped_column(String(50), default="")
    chot_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # KS-16 (Chủ tịch duyệt 30/10/2026): khách tự nhập voucher VTD Rewards lúc đặt — tối đa 5% đơn, VTD chịu.
    # `tong` = số khách phải trả (đã trừ voucher); khách sạn vẫn nhận như không có voucher.
    voucher_id: Mapped[int | None] = mapped_column(Integer, nullable=True)   # voucher_rewards.id (khoá ngoại ở phía voucher)
    giam_voucher: Mapped[float] = mapped_column(TIEN, default=0)
    # KS-16p (Chủ tịch duyệt bản xem thử 01/11/2026): «Đặt giữ, trả sau» — chỉ gói miễn phí hủy. Đơn «cho_tra» giữ phòng tới
    # cuối ngày han_tra (giu_den); quá hạn chưa trả → het_han như đơn trả ngay, nhả phòng, không thu phí. VTD không lưu thẻ.
    cach_tra: Mapped[str] = mapped_column(String(6), default="ngay")       # ngay | sau
    han_tra: Mapped[date | None] = mapped_column(Date, nullable=True)
    nhac_luc: Mapped[list] = mapped_column(JSON, default=list)             # [số ngày còn lại đã nhắc] — 3, 1
    km_but_toan: Mapped[str] = mapped_column(String(30), default="")   # bút toán Nợ 641 / Có 3388 lúc chốt
    # KS-16d (Chủ tịch 31/10/2026): Kế toán chốt → máy lập ngay MỘT đề nghị chi trả khách sạn (loại tra_ncc_thu_ho)
    payment_request_id: Mapped[int | None] = mapped_column(ForeignKey("payment_requests.id"), nullable=True)
    # KS-16e: bút toán doanh thu hoa hồng Nợ 3388 / Có 511 (ghi khi đã chi trả khách sạn, hoặc lúc chốt nếu trả 0)
    dt_but_toan: Mapped[str] = mapped_column(String(30), default="")


class ThanhToanKsVtd(Base):
    __tablename__ = "thanh_toan_ks_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_ks_vtd.id"), index=True)
    kenh: Mapped[str] = mapped_column(String(8))                         # qr | onepay
    so_tien: Mapped[float] = mapped_column(TIEN)
    trang_thai: Mapped[str] = mapped_column(String(12), default="cho", index=True)
    bank_txn_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transactions.id"), nullable=True, unique=True)
    ma_gd: Mapped[str] = mapped_column(String(40), default="", index=True)
    so_gd_cong: Mapped[str] = mapped_column(String(40), default="")
    ket_qua: Mapped[str] = mapped_column(String(10), default="")
    luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    xac_nhan_boi: Mapped[str] = mapped_column(String(50), default="")
    xac_nhan_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ghi_chu: Mapped[str] = mapped_column(String(300), default="")
    goc: Mapped[str] = mapped_column(String(80), default="")
    phi_the: Mapped[float | None] = mapped_column(TIEN, nullable=True)
    but_toan: Mapped[str] = mapped_column(String(30), default="")


# ══ KS-15 · ĐÁNH GIÁ KHÁCH SẠN VTD (Chủ tịch duyệt bản xem thử 30/10/2026) ══════════════════════════════════════
# Luật như đánh giá nhà hàng AT-3, thang 10 như Agoda: chỉ người đặt của một đơn ĐÃ XÁC NHẬN, từ ngày trả phòng, trong
# 30 ngày; một bài / đơn; sửa trong 7 ngày. Hiện ngay; chỉ Marketing ẩn vì vi phạm; TP Điều hành xem lại. Khách sạn
# trả lời qua cổng NCC (khách sạn phải được gắn với một NCC). Dưới 3 bài đang hiện: «Mới — chưa đủ đánh giá».
LY_DO_AN_DG_KS = {"chui_boi": "Chửi bới, xúc phạm", "thong_tin_ca_nhan": "Lộ thông tin cá nhân",
                  "quang_cao": "Quảng cáo / spam", "anh_sai": "Ảnh không phải khách sạn / phòng"}
MUC_DG_KS = {"diem_sach": "Sạch sẽ", "diem_vi_tri": "Vị trí", "diem_phong": "Phòng", "diem_phuc_vu": "Phục vụ",
             "diem_gia": "Đáng giá tiền"}
DI_CUNG = {"mot_minh": "Đi một mình", "cap_doi": "Cặp đôi", "gia_dinh_tre_nho": "Gia đình có trẻ nhỏ",
           "gia_dinh": "Gia đình", "nhom_ban": "Nhóm bạn", "cong_tac": "Công tác"}


class DanhGiaKsVtd(Base):
    __tablename__ = "danh_gia_ks_vtd"
    id: Mapped[int] = mapped_column(primary_key=True)
    don_id: Mapped[int] = mapped_column(ForeignKey("don_ks_vtd.id"), unique=True)
    khach_san_id: Mapped[int] = mapped_column(ForeignKey("khach_san_vtd.id"), index=True)
    tai_khoan_id: Mapped[int] = mapped_column(ForeignKey("tai_khoan_ngoai.id"), index=True)
    ten_hien: Mapped[str] = mapped_column(String(40), default="")          # đã che, chụp lúc viết
    loai_phong: Mapped[str] = mapped_column(String(160), default="")
    so_dem: Mapped[int] = mapped_column(Integer, default=1)
    ngay_tra: Mapped[date] = mapped_column(Date)
    di_cung: Mapped[str] = mapped_column(String(20), default="")
    diem: Mapped[int] = mapped_column(Integer)                              # 1–10, bắt buộc
    # Năm mục phụ: RỖNG khác 0 — bỏ trống thì không tính vào điểm mục đó.
    diem_sach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_vi_tri: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_phong: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_phuc_vu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diem_gia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tieu_de: Mapped[str] = mapped_column(String(120), default="")
    nhan_xet: Mapped[str] = mapped_column(Text, default="")
    anh: Mapped[list] = mapped_column(JSON, default=list)                   # [{hien, nho, an, ly_do}]
    tao_luc: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    sua_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    an: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    an_ly_do: Mapped[str] = mapped_column(String(20), default="")
    an_ghi_chu: Mapped[str] = mapped_column(Text, default="")
    an_boi: Mapped[str] = mapped_column(String(50), default="")
    an_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    xem_lai: Mapped[str] = mapped_column(String(6), default="")            # "" chờ · "giu" · "hien"
    xem_lai_boi: Mapped[str] = mapped_column(String(50), default="")
    xem_lai_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tra_loi: Mapped[str] = mapped_column(Text, default="")
    tra_loi_boi: Mapped[str] = mapped_column(String(60), default="")
    tra_loi_luc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tra_loi_an: Mapped[bool] = mapped_column(Boolean, default=False)
    tra_loi_an_ly_do: Mapped[str] = mapped_column(String(20), default="")
