# -*- coding: utf-8 -*-
"""ĐẾM LƯỢT MỞ CỬA ĐỌC — Đợt HD-Q2a. Chủ tịch chốt 16/10/2026.

VÌ SAO CÓ TỆP NÀY. Chủ tịch yêu cầu: trước khi thu hẹp quyền đọc của Marketing và Điều hành, phải
dựng một cửa ĐẾM nói rõ ai sẽ mất cửa nào và mỗi ngày họ đang mở bao nhiêu phiếu. Đi đo thì thấy hệ
thống KHÔNG có nhật ký đọc: `audit_log` được gọi ở 432 chỗ nhưng toàn là thao tác GHI, và trong cả
nhóm đánh giá chỉ đúng một hành vi được ghi lại — `ghi_danh_gia_ho`. Nghĩa là câu hỏi ấy hôm nay
KHÔNG trả lời được bằng dữ liệu có sẵn. Đoán hộ một con số rồi gọi nó là phép đo thì đó là một con
số trả lời một câu hỏi khác. Nên vòng này không siết quyền của ai: nó bắt đầu ĐẾM, và Chủ tịch bấm
ngày siết sau khi nhìn số thật.

BỐN ĐIỀU TỆP NÀY CỐ Ý LÀM KHÁC, và lý do từng cái:

MỘT — ĐẾM BẰNG PHIÊN RIÊNG, KHÔNG DÙNG PHIÊN CỦA NGƯỜI ĐỌC. Một cái máy đếm làm hỏng việc nó đang
đếm là cái máy đếm tệ nhất. Nếu ghi chung phiên với cửa đọc thì một lỗi ghi, một ràng buộc trùng,
hay một lần `commit` sớm đều có thể làm hỏng chính yêu cầu đọc của người dùng — và hỏng theo kiểu
khó lần, vì không ai ngờ màn hình bảng điểm chết vì bộ đếm. Nên hàm `ghi` mở phiên của riêng nó,
`commit` của riêng nó, và nuốt MỌI lỗi của chính nó. Đếm hụt một lượt là chuyện nhỏ; chặn một
trưởng phòng đọc bảng điểm vì bộ đếm là chuyện lớn.

HAI — ĐẾM CẢ SỐ PHÚT KHÁC NHAU, KHÔNG CHỈ SỐ LƯỢT. Màn hình web tự nạp lại, người dùng bấm F5, bộ
lọc đổi một tham số — mỗi thứ đều là một lượt gọi. Đếm lượt thôi thì một người mở màn hình rồi bỏ
đó có thể ra con số to hơn một người thật sự ngồi làm. `so_phut` đếm số PHÚT KHÁC NHAU trong ngày
có ít nhất một lượt: một màn hình tự nạp 30 giây một lần cả giờ đồng hồ ra 60 phút, còn một người
mở ba lần trong cùng một phút ra 1. Hai con số cạnh nhau nói được thứ mà một con số không nói được.

BA — TÁCH NGƯỜI VỚI ROBOT. `robot_ks` gọi cửa đọc theo lịch. Gộp lượt của nó vào lượt người là biến
một con robot thành một phòng ban đang chăm chỉ. Cột `role` giữ nguyên để người đọc bảng tự thấy,
và hàm `bang` đánh dấu rõ dòng nào là robot.

BỐN — KHÔNG GHI MỘT CHỮ NÀO VỀ KHÁCH. Bảng này có tên người đăng nhập, vai trò, tên cửa và mấy con
số đếm. Không tên khách, không mã phiếu, không tham số lọc. Một bộ đếm dùng để quyết định phân
quyền mà lại tự nó trở thành một kho dữ liệu khách thì nó đã thành đúng cái vấn đề nó đi giải.

CÒN MỘT CHỖ HỤT, GHI RA CHỨ KHÔNG GIẤU: hai yêu cầu đến cùng một lúc trong cùng một ngày cho cùng
một cửa có thể cùng thấy "chưa có dòng" rồi cùng chèn, và ràng buộc duy nhất sẽ loại một cái. Lúc
ấy mất ĐÚNG MỘT lượt của lần đầu tiên trong ngày. Chấp nhận: đổi lại là không phải khoá bảng trên
mỗi lần đọc. Con số này dùng để so các phòng với nhau, không dùng để tính tiền.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.danh_gia import LuotDocCua

# Các cửa ĐỌC được đếm. Khai ở MỘT chỗ: cửa không có tên trong bảng này thì `ghi` từ chối đếm, nên
# không ai lỡ tay sinh ra một tên cửa mới chỉ bằng cách gõ sai chuỗi ở chỗ gọi.
CUA = {
    "bang_diem": "Bảng điểm đánh giá",
    "chi_so": "Chỉ số khảo sát",
    "chua_tra_loi": "Khách chưa chấm điểm",
    "cham_soc": "Danh sách phiếu chăm sóc",
    "cham_soc_chi_so": "Chỉ số chăm sóc",
}

VAI_ROBOT = ("robot_ks",)


def ghi(u, cua: str, so_dong: int = 0) -> bool:
    """Ghi một lượt mở cửa. Trả về True nếu đã ghi được.

    KHÔNG BAO GIỜ ném lỗi ra ngoài — xem điều MỘT ở đầu tệp.
    """
    if cua not in CUA:
        return False
    try:
        # `SessionLocal` tra ở cấp mô-đun chứ không nhập trong thân hàm: nhờ vậy phép thử thay được
        # RIÊNG phiên của bộ đếm để chứng minh bộ đếm hỏng thì cửa đọc vẫn chạy. Nhập trong thân hàm
        # thì thay nó là thay luôn phiên của cửa đọc — và ca thử ấy sẽ đỏ vì một lý do khác.
        s = SessionLocal()
        try:
            bay_gio = datetime.now()
            ngay, phut = bay_gio.date(), bay_gio.strftime("%H:%M")
            r = s.execute(
                select(LuotDocCua).where(
                    LuotDocCua.ngay == ngay,
                    LuotDocCua.username == u.username,
                    LuotDocCua.cua == cua,
                )
            ).scalars().first()
            if r is None:
                r = LuotDocCua(ngay=ngay, username=u.username, role=u.role, cua=cua,
                               so_luot=0, so_phut=0, phut_cuoi="", so_dong=0)
                s.add(r)
            r.role = u.role
            r.so_luot = (r.so_luot or 0) + 1
            r.so_dong = (r.so_dong or 0) + max(0, int(so_dong or 0))
            if r.phut_cuoi != phut:
                r.so_phut = (r.so_phut or 0) + 1
                r.phut_cuoi = phut
            s.commit()
            return True
        finally:
            s.close()
    except Exception:      # noqa: BLE001 - xem điều MỘT: bộ đếm không được làm hỏng cửa đọc
        return False


def bang(db: Session, tu: date, den: date) -> dict:
    """Bảng đếm cho Chủ tịch: mỗi người × mỗi cửa một dòng, kèm tổng theo vai.

    `so_ngay` là số NGÀY KHÁC NHAU có mở cửa — con số trả lời "họ có dùng hằng ngày không", khác hẳn
    `so_luot` vốn có thể dồn hết vào một buổi chiều.
    """
    rows = list(db.execute(
        select(LuotDocCua).where(LuotDocCua.ngay >= tu, LuotDocCua.ngay <= den)
        .order_by(LuotDocCua.role, LuotDocCua.username, LuotDocCua.cua)
    ).scalars())

    gop: dict[tuple[str, str, str], dict] = {}
    for r in rows:
        k = (r.role, r.username, r.cua)
        d = gop.setdefault(k, {"role": r.role, "username": r.username, "cua": r.cua,
                               "cua_ten": CUA.get(r.cua, r.cua), "so_luot": 0, "so_phut": 0,
                               "so_dong": 0, "so_ngay": 0,
                               "la_robot": r.role in VAI_ROBOT})
        d["so_luot"] += r.so_luot or 0
        d["so_phut"] += r.so_phut or 0
        d["so_dong"] += r.so_dong or 0
        d["so_ngay"] += 1

    ds = sorted(gop.values(), key=lambda x: (x["role"], x["username"], x["cua"]))
    so_ngay_ky = (den - tu).days + 1
    for d in ds:
        # Trung bình tính trên SỐ NGÀY CỦA KỲ, không trên số ngày có dùng. Chia cho số ngày có dùng
        # thì một người mở đúng một hôm rồi thôi vẫn ra "mỗi ngày một lượt" — đó là con số trả lời
        # một câu hỏi khác.
        d["luot_moi_ngay"] = round(d["so_luot"] / so_ngay_ky, 2) if so_ngay_ky > 0 else 0.0

    return {
        "tu": tu.isoformat(), "den": den.isoformat(), "so_ngay_ky": so_ngay_ky,
        "cua": CUA, "rows": ds,
        "luu_y": ("Bảng này chỉ đếm từ ngày Đợt HD-Q2a lên hệ thống thật; trước đó hệ thống không "
                  "ghi lượt đọc nên không có số. Vai robot được đánh dấu riêng."),
    }
