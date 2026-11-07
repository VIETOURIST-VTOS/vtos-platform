# -*- coding: utf-8 -*-
"""Đợt TKC-3 07/11/2026 — MỘT BẢNG KHAI «đường ghi → tài khoản chi tiết», Kế toán trưởng ký một lần.

VÌ SAO CÓ TỆP NÀY
Nhịp 1 (Đợt TKC-2) đo trên sổ thật của công ty: 187 dòng đã ghi vào 13 tài khoản CHA. Nhưng
bảng «Theo đường ghi» chỉ thấy MỘT đường (`de_nghi_chi`) — vì 13 đường còn lại chưa phát sinh,
chứ không phải vì chúng đã đúng. Đọc mã ngày 07/11/2026 đếm được **14 chỗ** gõ cứng một tài
khoản cha vào bút toán.

CHỦ TỊCH CHỐT 07/11/2026: không sửa số cứng rải rác ở 14 tệp. Một bảng khai chung, Kế toán
trưởng ký một lần, mã đọc bảng ấy. Đổi tài khoản con về sau là đổi một dòng tham số đã có cửa
nhập và có chữ ký — không phải mở một đợt mã mới.

MỘT NGUỒN, KHÔNG HAI
`KHOA` dưới đây là nguồn duy nhất. `rules.DEFAULT_PARAMS` SINH RA từ nó (không chép tay), nên
mặc định của tham số và mặc định của mã không thể lệch nhau. Đây đúng chỗ hệ thống đang hỏng:
`ops.CATEGORY_ACCOUNT` (cấp cha: 154 / 641 / 642) và `misa.CATEGORY_ACCOUNT` (cấp con: 1541 /
6417 / 6428) là HAI bảng cùng nói một luật và ĐÃ LỆCH — cùng một khoản chi nằm ở 154 trong sổ
VTOS và ở 1541 trong bảng kê xuất sang MISA. Luật 3 của đợt này buộc hai bảng khớp nhau.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session


def KEY(khoa: str) -> str:
    """Tên khóa tham số của một đường ghi. Một chỗ sinh ra tên, không gõ chuỗi ở nơi khác."""
    return "tk_" + khoa


# khóa → (tài khoản chi tiết mặc định, mô tả cho màn Tham số)
#
# MẶC ĐỊNH LẤY TỪ ĐÂU: những dòng `dn_chi_*` lấy đúng giá trị `misa.CATEGORY_ACCOUNT` đang chạy —
# tức là các con số Chủ tịch đã chốt 08/10, 26/10 và 31/10/2026 cho bảng kê MISA. Đợt này KHÔNG
# tự nghĩ ra một tài khoản nào mới cho chúng; nó chỉ bắt sổ VTOS ghi đúng thứ bảng kê đã ghi.
KHOA: dict[str, tuple[str, str]] = {
    # ── Đề nghị chi đã duyệt → ghi công nợ (`ops._post_liability`) ─────────────────────────
    "dn_chi_chi_tour":        ("1541", "Đề nghị chi – chi phí tour (Nợ … / Có 331)"),
    "dn_chi_marketing":       ("6417", "Đề nghị chi – marketing"),
    "dn_chi_hanh_chinh":      ("6428", "Đề nghị chi – hành chính"),
    "dn_chi_hoa_hong":        ("6417", "Đề nghị chi – hoa hồng đại lý / CTV"),
    "dn_chi_tra_ncc_thu_ho":  ("3388", "Đề nghị chi – trả khách sạn / nhà hàng tiền thu hộ"),
    # ── Quyết toán tour (`accounting.post_tour_settlement`) ────────────────────────────────
    "qt_do_dang":             ("1541", "Quyết toán tour – chi phí dở dang (hoàn ứng, trích trước)"),
    # `335` (trích trước chi phí NCC chưa có hóa đơn) CỐ Ý CHƯA NẮN TRONG ĐỢT NÀY.
    # Con của nó trên sổ thật là `3351` / `3352`, nhưng danh mục mẫu đi kèm mã
    # (`app/data/misa_tai_khoan.json`, 134 tài khoản) CHƯA CÓ hai mã ấy — chúng vào sổ thật qua
    # đường nạp danh mục. Khai mặc định trỏ vào một tài khoản không có trong danh mục mẫu là
    # dựng một đợt chỉ chạy được trên đúng một cơ sở dữ liệu. Để `335` lại cho Đợt TKC-4, sau
    # khi danh mục thật được nạp — và nói ra ở đây chứ không im lặng bỏ qua.
    "qt_gia_von_noi_dia":     ("6321", "Quyết toán tour – giá vốn tour NỘI ĐỊA"),
    "qt_gia_von_nuoc_ngoai":  ("6328", "Quyết toán tour – giá vốn tour NƯỚC NGOÀI"),
    "qt_gia_von_thue_xe":     ("6323", "Quyết toán – giá vốn dịch vụ cho thuê xe"),
    # ── Kết chuyển lãi/lỗ (`reports.ket_chuyen`, `misa.chot_so_kiem_toan`) ─────────────────
    "kc_lai_lo":              ("4212", "Kết chuyển lãi/lỗ về lợi nhuận sau thuế chưa phân phối"),
}

# Giá vốn quyết toán chọn theo LOẠI TOUR, không phải một hằng số.
#
# `632` có bảy con trong danh mục thật, và chúng không thay nhau được: một chuyến nước ngoài ghi
# vào 6321 (nội địa) thì báo cáo doanh thu/giá vốn theo dòng sản phẩm sai ngay từ dòng đầu. Loại
# tour đã có sẵn trên bản ghi `Tour`, nên chỗ này không phải hỏi ai — chỉ phải ĐỌC.
GIA_VON_THEO_LOAI = {
    "le_noi_dia":      "qt_gia_von_noi_dia",
    "doan_noi_dia":    "qt_gia_von_noi_dia",
    "non_package":     "qt_gia_von_noi_dia",
    "le_nuoc_ngoai":   "qt_gia_von_nuoc_ngoai",
    "doan_nuoc_ngoai": "qt_gia_von_nuoc_ngoai",
    "thue_xe":         "qt_gia_von_thue_xe",
}


def tham_so_mac_dinh() -> list[tuple[str, str, str, str, str]]:
    """Các dòng của `rules.DEFAULT_PARAMS` SINH RA từ `KHOA` — không chép tay dòng nào.

    Chép tay là dựng nguồn thứ hai, và nguồn thứ hai bao giờ cũng lệch. Đây đúng bài học của
    `ops.CATEGORY_ACCOUNT` / `misa.CATEGORY_ACCOUNT` nói ở đầu tệp.
    """
    return [(KEY(k), mac_dinh, "Tài khoản chi tiết – " + mo_ta, "số hiệu tài khoản",
             "Chủ tịch chốt 07/11/2026 (Đợt TKC-3) – Kế toán trưởng đổi được trên màn Tham số")
            for k, (mac_dinh, mo_ta) in KHOA.items()]


def la_tai_khoan_cha(db: Session, tk: str) -> bool:
    """Có tài khoản nào khai `parent` là nó không. Hỏi DANH MỤC THẬT, không đoán theo độ dài mã."""
    from app.models.accounting import Account
    return db.execute(select(Account.code).where(Account.parent == tk)).first() is not None


def kiem(db: Session, tk: str) -> str:
    """"" nếu dùng được; ngược lại là câu nói rõ SAI GÌ.

    Ba cảnh, ba câu khác nhau. Một câu chung chung («tài khoản không hợp lệ») buộc người sửa
    tham số phải đoán, và họ sẽ đoán nhầm cảnh.
    """
    from app.models.accounting import Account
    tk = (tk or "").strip()
    if not tk:
        return "Chưa khai tài khoản chi tiết"
    if db.execute(select(Account.code).where(Account.code == tk)).first() is None:
        return "Tài khoản " + tk + " không có trong danh mục"
    if la_tai_khoan_cha(db, tk):
        return ("Tài khoản " + tk + " là tài khoản tổng hợp (có tài khoản con) — bút toán phải "
                "ghi vào tài khoản chi tiết, đúng việc đợt này đang nắn")
    return ""


def chon(db: Session, khoa: str) -> str:
    """Tài khoản chi tiết của một đường ghi: tham số đã ký, không có thì mặc định của `KHOA`.

    TỪ CHỐI trả về một tài khoản cha, KỂ CẢ khi ai đó vừa ký một tham số sai. Nếu chỉ đọc rồi
    trả về thì cửa Tham số trở thành một đường vòng đi quanh chính luật đợt này đặt ra — ký một
    dòng `tk_qt_gia_von_noi_dia = 632` là bút toán lại ghi vào cha, im lặng như cũ.
    """
    assert khoa in KHOA, "khóa `" + khoa + "` chưa khai trong tk_chi_tiet.KHOA"
    from app.services import rules as R
    tk = (R.get_param_text(db, KEY(khoa)) or "").strip() or KHOA[khoa][0]
    loi = kiem(db, tk)
    if loi:
        raise ValueError("Tham số `" + KEY(khoa) + "`: " + loi)
    return tk


def gia_von_tour(db: Session, tour_type: str) -> str:
    """Tài khoản giá vốn của một chuyến, theo loại tour. Loại lạ → về nội địa và KHÔNG im lặng."""
    return chon(db, GIA_VON_THEO_LOAI.get((tour_type or "").strip(), "qt_gia_von_noi_dia"))
