"""Đợt E3 – LOẠI CHỨNG TỪ, LOẠI NGHIỆP VỤ, và KHOÁ SỰ KIỆN của một bút toán.

════════════════════════════════════════════════════════════════════════════════════════════════
VÌ SAO CÓ TỆP NÀY
════════════════════════════════════════════════════════════════════════════════════════════════

`journal_entries` trước đợt này chỉ phân loại bằng MỘT cột `source_type`. Chú thích cạnh cột ấy
khai năm giá trị (thu_tien / hoa_don / quyet_toan / thu_cong / dao); đo lại ngày 12/10/2026 bằng
cách đọc cây cú pháp của 32 chỗ gọi `post_entry` thì mã thật đang dùng **17 giá trị hằng cộng ba
chỗ truyền biến**. Một chú thích sai suốt nhiều tháng mà không hàng rào nào canh là chuyện phải
sửa cùng lúc với việc thêm cột, không phải sau.

Và `source_type` một mình không trả lời được câu hỏi của kế toán: *đây là loại CHỨNG TỪ gì (phiếu
thu, phiếu chi, phiếu kế toán…)* và *nó ghi cho NGHIỆP VỤ nào*. Hai câu khác nhau: một tour quyết
toán sinh ba bút toán – hoàn ứng, trích trước, kết chuyển giá vốn – cả ba cùng `source_type`
`quyet_toan`, cùng là phiếu kế toán, nhưng là **ba nghiệp vụ khác nhau**.

════════════════════════════════════════════════════════════════════════════════════════════════
KHOÁ SỰ KIỆN – CHỐNG GHI SỔ HAI LẦN (P0·04)
════════════════════════════════════════════════════════════════════════════════════════════════

Chủ tịch chốt 12/10/2026: một sự kiện được định danh bằng **nguồn + mã nguồn + loại nghiệp vụ**.

ĐÃ ĐO TRƯỚC KHI CHỐT, và đây là lý do khoá phải có vế thứ ba. Ba chỗ trong mã CỐ Ý sinh nhiều
chứng từ dưới cùng một cặp (nguồn, mã nguồn) – khoá hai vế sẽ chặn nhầm cả ba:

    luong      + payroll:2026-09:VTD  → 5 chứng từ (lương · thù lao CTV · TNCN · BHXH · đoàn phí)
    ket_chuyen + period:2026-09       → 3 chứng từ (doanh thu · chi phí · lãi lỗ)
    quyet_toan + tour:HT001           → 3 chứng từ (hoàn ứng · trích trước · giá vốn)

Cả ba hết va nhau khi thêm vế nghiệp vụ, vì năm bút toán lương ĐÚNG LÀ năm nghiệp vụ.

KHOÁ ĐƯỢC TÍNH MỘT CHỖ, KHÔNG PHẢI MỘT Ô NGƯỜI GỌI ĐIỀN. `post_entry` tự ghép ba vế rồi cất vào
cột `khoa_su_kien`. Để người gọi tự điền thì chỗ nào quên là hàng rào tắt âm thầm ở đúng chỗ ấy –
đúng kiểu hỏng mà Đợt LG3 vừa phải đi sửa ba lần. Cột lưu giá trị đã ghép chứ không phải chỉ mục
ba cột, vì RỖNG phải nghĩa là "không khoá", mà NULL thì không va nhau trong cả SQLite lẫn
PostgreSQL – còn chỉ mục ba cột thì mọi chứng từ lập tay sẽ va nhau ở bộ ba rỗng.
"""
from __future__ import annotations

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 1 · LOẠI CHỨNG TỪ – hình thức tờ giấy, theo TT99/2023 và thói quen của phòng Kế toán
# ════════════════════════════════════════════════════════════════════════════════════════════════
# KHAI TRONG MÃ, KHÔNG PHẢI MỘT BẢNG TRONG CSDL (Chủ tịch chọn 12/10/2026). Thêm một loại chứng từ
# là đổi KHOÁ của quy tắc hạch toán đang chạy; để bấm thêm trên màn hình thì một lần bấm nhầm làm
# lệch cả bảng quy tắc mà không có lịch sử nào nói ai đổi. Trong mã thì có git và có người ký.
LOAI_CHUNG_TU: dict[str, str] = {
    "PT":  "Phiếu thu",
    "PC":  "Phiếu chi",
    "BC":  "Giấy báo Có ngân hàng",
    "BN":  "Giấy báo Nợ ngân hàng",
    "HDB": "Hóa đơn bán ra",
    "HDM": "Hóa đơn mua vào",
    "PKT": "Phiếu kế toán (bút toán tổng hợp)",
}

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 2 · LOẠI NGHIỆP VỤ – việc gì đã xảy ra. Mỗi dòng kèm loại chứng từ của nó.
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Danh sách này dựng TỪ 32 CHỖ GỌI CÓ THẬT trong mã, không dựng từ một bản vẽ. Thêm một chỗ gọi
# mới mà không khai nghiệp vụ thì `test_e3_1` đỏ.
NGHIEP_VU: dict[str, tuple[str, str]] = {
    # mã                        (tên hiển thị,                                        loại chứng từ)
    "thu_tien_khach":           ("Thu tiền khách hàng",                                "PT"),
    "huy_bao_luu":              ("Hủy tiền bảo lưu, trả về doanh thu",                 "PKT"),
    "phat_hanh_hoa_don":        ("Phát hành hóa đơn bán ra",                           "HDB"),
    "de_nghi_chi":              ("Ghi nhận đề nghị chi đã duyệt",                      "PKT"),
    "chi_tien":                 ("Chi tiền theo lệnh chi",                             "PC"),
    "quyet_toan_hoan_ung":      ("Quyết toán tour – hoàn ứng",                         "PKT"),
    "quyet_toan_trich_truoc":   ("Quyết toán tour – trích trước chi phí chưa có hóa đơn", "PKT"),
    "quyet_toan_gia_von":       ("Quyết toán tour – kết chuyển giá vốn",               "PKT"),
    "luong_hdld":               ("Lương người lao động hợp đồng",                      "PKT"),
    "thu_lao_ctv":              ("Thù lao HDV / cộng tác viên",                        "PKT"),
    "khau_tru_tncn":            ("Khấu trừ thuế TNCN",                                 "PKT"),
    "bhxh_nld":                 ("BHXH phần người lao động",                           "PKT"),
    "doan_phi":                 ("Đoàn phí công đoàn",                                 "PKT"),
    "ket_chuyen_doanh_thu":     ("Kết chuyển doanh thu sang 911",                      "PKT"),
    "ket_chuyen_chi_phi":       ("Kết chuyển chi phí sang 911",                        "PKT"),
    "ket_chuyen_lai_lo":        ("Kết chuyển lãi/lỗ sang 421",                         "PKT"),
    "ket_chuyen_cuoi_ky":       ("Kết chuyển cuối kỳ theo bước kết sổ",                "PKT"),
    "ket_chuyen_chot_so":       ("Kết chuyển để chốt sổ theo bản kiểm toán",           "PKT"),
    "tach_ty_gia":              ("Tách chênh lệch tỷ giá ra 635/515",                  "PKT"),
    "but_toan_sao_ke":          ("Ghi sổ dòng sao kê ngân hàng đã nhận diện",          "BC"),
    "khau_hao_tscd":            ("Trích khấu hao tài sản cố định",                     "PKT"),
    "phan_bo_tra_truoc":        ("Phân bổ chi phí trả trước / công cụ dụng cụ",        "PKT"),
    "so_du_dau_ky":             ("Nhập số dư đầu kỳ từ MISA",                          "PKT"),
    "dieu_chinh_kiem_toan":     ("Điều chỉnh theo báo cáo kiểm toán / soát xét",       "PKT"),
    "chung_tu_misa":            ("Chứng từ nạp từ MISA",                               "PKT"),
    "but_toan_dao":             ("Bút toán đảo",                                       "PKT"),
    "but_toan_tay":             ("Bút toán Kế toán lập tay",                           "PKT"),
    "theo_quy_tac":             ("Ghi sổ theo quy tắc hạch toán",                      "PKT"),
    "khe_uoc_vay":              ("Khế ước vay – nhận vay / trả gốc / trả lãi",         "PKT"),
    # ĐÁO HẠN LÀ HAI BÚT TOÁN, nên nó là HAI nghiệp vụ — Đợt DỌN-1, 13/10/2026.
    #
    # Trả gốc khoản cũ và nhận giải ngân khoản mới cùng thuộc MỘT khế ước, cùng một mã nguồn, nên
    # dưới một tên nghiệp vụ chung thì khoá ba phần coi chân thứ hai là bản sao của chân thứ nhất
    # và chặn. Bù trừ hai chân thành một dòng thì dư nợ vay không bao giờ đứng ở đỉnh và dòng tiền
    # mất hẳn một vòng ra–vào — cả hai đều là số công bố của công ty đại chúng, nên gộp là sai sổ.
    #
    # Đặt tên riêng cho từng chân vừa cho khoá phân biệt được, vừa làm sổ đọc ra đúng việc đã làm.
    "tra_goc_vay":              ("Trả gốc khoản vay (chân trả của đáo hạn)",           "PKT"),
    "nhan_giai_ngan_vay":       ("Nhận giải ngân khoản vay (chân nhận của đáo hạn)",   "PKT"),
    "khe_uoc_tai_chinh":        ("Khế ước tài chính khác – đầu tư, ký quỹ, đặt cọc",   "PKT"),
}

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 3 · NGUỒN SINH CHỨNG TỪ – thay cho chú thích năm giá trị đã sai nhiều tháng
# ════════════════════════════════════════════════════════════════════════════════════════════════
NGUON: dict[str, str] = {
    "thu_cong":     "Kế toán lập tay trên màn hình chứng từ",
    "thu_tien":     "Phiếu thu tiền khách",
    "bao_luu":      "Hủy tiền bảo lưu",
    "hoa_don":      "Hóa đơn bán ra đã phát hành",
    "de_nghi_chi":  "Đề nghị chi đã duyệt",
    "lenh_chi":     "Lệnh chi đã thực hiện",
    "quyet_toan":   "Quyết toán tour được Kế toán xác nhận",
    "luong":        "Bảng lương đã chốt",
    "ket_chuyen":   "Kết chuyển cuối kỳ",
    "khau_hao":     "Bảng trích khấu hao TSCĐ",
    "phan_bo":      "Bảng phân bổ chi phí trả trước",
    "tai_chinh":    "Lịch khế ước tài chính (đầu tư, ký quỹ, đặt cọc…)",
    "khe_uoc_vay":  "Lịch khế ước vay",
    "so_du_dau_ky": "Số dư đầu kỳ nạp từ MISA",
    "kiem_toan":    "Điều chỉnh theo báo cáo kiểm toán",
    "misa":         "Chứng từ nạp thẳng từ MISA",
    "quy_tac":      "Ghi sổ qua màn hình quy tắc hạch toán",
    "dao":          "Bút toán đảo của một chứng từ đã ghi sổ",
}

# ════════════════════════════════════════════════════════════════════════════════════════════════
# 4 · HAI CHỖ KHÔNG KHOÁ ĐƯỢC – khai ra kèm lý do, không im lặng bỏ qua
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Khuôn này mượn của `chu_ky.KHONG_GOI_KIEM_TRA` và `chu_ky.CHI_DOC_TRANG_THAI`: một ngoại lệ có
# TÊN và có LÝ DO thì người sau đọc được vì sao; một ngoại lệ nằm trong một câu `if` thì nó biến
# mất khỏi tầm mắt ngay khi người viết nó đi khỏi.
#
# `test_e3_8` đếm đúng hai mục này và đỏ khi có mục thứ ba – thêm ngoại lệ phải có người biết.
KHONG_KHOA_SU_KIEN: dict[str, str] = {
    "": "Chứng từ Kế toán lập tay không gắn với sự kiện ngoài nào – hai phiếu kế toán giống hệt "
        "nhau trong một ngày là chuyện có thật và đúng, nên khoá ở đây là chặn nhầm nghiệp vụ.",
    "quy_tac:": "Màn hình quy tắc hạch toán cho phép bỏ trống số chứng từ; khi bỏ trống, mã nguồn "
                "lùi về mã QUY TẮC, mà một quy tắc dùng cho nhiều lần mua khác nhau. Mã ấy không "
                "định danh sự kiện nào cả nên không khoá được. Gõ số chứng từ vào thì khoá chạy.",
}


class SaiLoai(ValueError):
    """Khai một loại nghiệp vụ hoặc một nguồn không có trong ba bảng trên."""


def nghiep_vu_hop_le(ma: str) -> str:
    """Trả về chính mã nếu nó có trong bảng; ném lỗi NÓI RA mã sai nếu không.

    CỐ Ý ném thay vì trả rỗng: một mã gõ sai mà lặng lẽ thành rỗng là một chứng từ không khoá
    được, và nó trông y hệt một chứng từ được miễn khoá có lý do."""
    if ma not in NGHIEP_VU:
        raise SaiLoai(f"Loại nghiệp vụ `{ma}` chưa khai trong `chung_tu_loai.NGHIEP_VU`. "
                      f"Khai nó ở đó kèm loại chứng từ, đừng truyền một chuỗi tự nghĩ ra.")
    return ma


def chung_tu_cua(nghiep_vu: str) -> str:
    """Loại chứng từ suy từ nghiệp vụ – người gọi chỉ khai MỘT thứ, không khai hai thứ lệch nhau."""
    return NGHIEP_VU[nghiep_vu_hop_le(nghiep_vu)][1]


def ten_nghiep_vu(ma: str) -> str:
    return NGHIEP_VU[ma][0] if ma in NGHIEP_VU else ma


def duoc_mien_khoa(source_ref: str) -> str:
    """Trả về LÝ DO miễn khoá, hoặc chuỗi rỗng nếu mã nguồn này khoá được."""
    r = (source_ref or "").strip()
    if not r:
        return KHONG_KHOA_SU_KIEN[""]
    for tien_to, ly_do in KHONG_KHOA_SU_KIEN.items():
        if tien_to and r.startswith(tien_to):
            return ly_do
    return ""


def khoa(source_type: str, source_ref: str, nghiep_vu: str) -> str | None:
    """Khoá sự kiện của một bút toán, hoặc None khi sự kiện không định danh được.

    None chứ không phải chuỗi rỗng: cột `khoa_su_kien` có chỉ mục DUY NHẤT, và NULL không va nhau
    trong cả SQLite lẫn PostgreSQL còn chuỗi rỗng thì va."""
    if duoc_mien_khoa(source_ref):
        return None
    return f"{source_type}|{(source_ref or '').strip()}|{nghiep_vu_hop_le(nghiep_vu)}"


def danh_muc() -> dict:
    """Ba bảng trên, cho màn hình đọc. CHỈ ĐỌC – không có cửa ghi, vì chúng khai trong mã."""
    return {
        "loai_chung_tu": [{"ma": k, "ten": v} for k, v in LOAI_CHUNG_TU.items()],
        "nghiep_vu": [{"ma": k, "ten": v[0], "loai_chung_tu": v[1],
                       "ten_loai_chung_tu": LOAI_CHUNG_TU[v[1]]} for k, v in NGHIEP_VU.items()],
        "nguon": [{"ma": k, "ten": v} for k, v in NGUON.items()],
        "khong_khoa_su_kien": [{"mau_ma_nguon": k or "(rỗng)", "ly_do": v}
                               for k, v in KHONG_KHOA_SU_KIEN.items()],
    }
