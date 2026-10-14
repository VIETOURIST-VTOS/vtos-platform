"""Bước duyệt cần đủ n chữ ký của các vai trò được chỉ định đích danh (Phụ lục đối chiếu 27/8/2026, mục 3.2).

Yêu cầu "đủ hai chữ ký Chủ tịch Hội đồng quản trị và Tổng giám đốc" lặp lại ở nhiều chỗ trong bộ chính
sách: sửa đổi mọi quy chế, duyệt chuyến chạy dưới biên 10%, chế tài sự vụ mức 3. Đối tượng duyệt trước đây
là chuỗi bước tuần tự MỘT người mỗi bước, nên hai điều sau không có chỗ nào chặn:

  1. Người TRÌNH hồ sơ tự ký duyệt hồ sơ của chính mình. Chữ ký thứ hai khi đó không còn là một lớp kiểm
     soát độc lập – nó chỉ là cùng một người ký hai lần dưới hai vai.
  2. Một người mang nhiều vai trò ký thay cả hai vai.

Gộp vào một chỗ để mọi phân hệ dùng chung, thay vì mỗi nơi tự viết một kiểu rồi sót một nơi.
"""
from fastapi import HTTPException
from app.models.core import User, ROLES


# ══════════════════════════════════════════════════════════════════════════════════════════════
# AI PHẢI KÝ — MỘT BẢNG CÓ TÊN, NHIỀU NƠI ĐỌC (Đợt LG2, 11/10/2026)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Trước đợt này, "cần hai chữ ký" nằm RỜI ở sáu chỗ: mỗi cửa tự viết `("chutich", "tgd")` vào
# `require_roles`, viết lại lần nữa vào `kiem_tra_nguoi_ky`, rồi tự kiểm `if signed_chutich and
# signed_tgd`. Ba lần viết cùng một luật ở cùng một cửa, nhân với sáu cửa. Đổi luật cho một cửa
# là phải sửa đúng ba chỗ và không sót — mà sót một chỗ thì cửa vẫn chạy, chỉ là chạy sai.
#
# CHỦ TỊCH CHỐT 11/10/2026, sau khi được liệt kê ĐỦ sáu cửa đang đòi hai chữ ký:
#
#   MỘT chữ ký, Chủ tịch     : tham số chính sách · đơn giá HDV theo tuyến · giá xe theo tuyến
#   HAI chữ ký, CT + TGĐ     : quy tắc hạch toán · chế tài sự vụ mức 3
#   HAI chữ ký, P.TGĐ + TGĐ  : dự toán chuyến dưới biên 10%
#   Bước bộ phận + cấp duyệt : chi ngoài dự toán (cổng 15)
#
# LUẬT "NGƯỜI TRÌNH KHÔNG TỰ KÝ" GIỮ NGUYÊN cho cả sáu — Chủ tịch chốt cùng ngày. Nên ba cửa một
# chữ ký VẪN LÀ HAI NGƯỜI: một người trình con số, Chủ tịch ký là hiệu lực ngay. Bỏ luật ấy đi
# thì ba cửa kia còn đúng một người làm trọn từ đầu đến cuối, và không còn lớp kiểm soát nào.
#
# HỆ QUẢ ĐÃ ĐO VÀ ĐÃ NÊU TRƯỚC KHI CHỐT: ô `nguong_chu_tich_duyet_chi` nằm trong nhóm một chữ ký,
# mà chính nó là con số định ra AI ĐƯỢC DUYỆT KHOẢN NÀO. Hạ nó về 0 thì mọi khoản thành Chủ tịch
# duyệt; nâng rất cao thì mọi khoản thành TGĐ duyệt. Chữ ký thứ hai ở đây từng là cái chặn không
# cho một người tự dời ranh giới ấy; từ nay cái chặn là "người trình phải là người khác".
#
# MỘT CÂU TRÍCH DẪN SAI, SỬA Ở ĐỢT NÀY: lời nhắn của màn hình Tham số ghi "(Điều 1 MHQT)". Đó là
# chỗ DUY NHẤT trong cả kho mã viện dẫn Điều 1 cho việc hai chữ ký, và Chủ tịch xác nhận 11/10/2026
# rằng Điều 1 không quy định việc này. Căn cứ thật là Phụ lục đối chiếu 27/8/2026 mục 3.2 — chính
# là câu đầu tệp này — và nó kể ba việc: sửa đổi mọi quy chế, duyệt chuyến dưới biên 10%, chế tài
# sự vụ mức 3. Trích dẫn sai còn tệ hơn không trích dẫn: nó gửi người đọc đi tìm nhầm điều khoản.
VAI_KY_CAN: dict[str, tuple[str, ...]] = {
    "tham_so":           ("chutich",),
    "don_gia_hdv":       ("chutich",),
    "gia_xe":            ("chutich",),
    "quy_tac_hach_toan": ("chutich", "tgd"),
    "che_tai_muc_3":     ("chutich", "tgd"),
    # CHUYẾN DƯỚI BIÊN 10% ĐỔI NGƯỜI KÝ, 11/10/2026: Chủ tịch RA KHỎI LUẬT, P.TGĐ tour đoàn VÀO.
    # Chủ tịch vẫn ĐI QUA ĐƯỢC bằng toàn quyền 06/9/2026 — đi qua được khác với có tên trong luật,
    # và bảng này khai LUẬT. Việc đổi người ký buộc phải thêm cột `signed_ptgd_doan` cho bảng
    # `tours`: nhét chữ ký P.TGĐ vào cột tên là `signed_chutich` là để sổ nói dối sau ba tháng.
    "du_toan_duoi_bien": ("ptgd_doan", "tgd"),
    # Dot E4a 12/10/2026 - DIEU KHOAN THANH TOAN. Chu tich chot: Chu tich ky mot minh,
    # y nhu bang tham so chinh sach. Khai O DAY chu khong o `dieu_khoan.py`: mot luat, mot cho.
    "dieu_khoan_thanh_toan": ("chutich",),
    # Đợt E6 13/10/2026 — MỞ LẠI KỲ KẾ TOÁN ĐÃ KHÓA. Chủ tịch chốt: Kế toán trưởng trình, Chủ
    # tịch ký. Khai ở ĐÂY chứ không ở `mo_lai_ky.py`: một luật, một chỗ — cùng lẽ với điều khoản
    # thanh toán ở dòng trên. Người TRÌNH không khai trong bảng này vì bảng này nói về MỘT bước
    # ký; ai được trình là việc của `require_roles` ở cửa trình.
    "mo_lai_ky":         ("chutich",),
    # Đợt E16 14/10/2026 — BỘ SỐ BCTC ĐÃ KIỂM TOÁN. Chủ tịch chốt: Kế toán tải lên, Chủ tịch ký.
    # Khai ở ĐÂY chứ không ở `bo_so_kiem_toan.py`: một luật, một chỗ — cùng lẽ với `mo_lai_ky` ở
    # dòng trên. Vì sao bộ số phải có chữ ký trong khi mọi bộ nạp MISA khác thì không: các bộ nạp
    # kia nạp SỐ PHÁT SINH, sai một dòng thì lệch một dòng và đối chiếu sẽ tìm ra. Bộ số này là
    # ĐÁP ÁN — `misa.import_audited_checkpoint` lấy nó làm chuẩn rồi kéo cả sổ về bằng chênh lệch,
    # nên một con số sai ở đây viết lại cả bảng cân đối của một công ty đại chúng.
    "bo_so_kiem_toan":   ("chutich",),
}

# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỔNG 15 — CHI NGOÀI DỰ TOÁN: HAI CHỮ KÝ Ở HAI BƯỚC KHÁC NHAU, nên KHÔNG ở bảng trên
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Chủ tịch chốt 11/10/2026: chi ngoài dự toán cần chữ ký TRƯỞNG PHÒNG và TGĐ. Và khi được hỏi
# chữ ký trưởng phòng là bước nào, Chủ tịch chọn: CHÍNH bước xác nhận bộ phận đã có (`cho_tp`,
# ghi tên vào ô `tp_by`) — không bắt ai bấm thêm một lần nữa.
#
# Nên cổng 15 KHÔNG nằm ở `VAI_KY_CAN`: hai chữ ký của nó không cùng một bước, và bảng trên nói
# về MỘT bước ký. Đặt nó vào đấy là nói sai cấu trúc của chính nó.
#
# ĐIỀU ĐỢT NÀY ĐỔI TRONG MÃ, đúng một vế: trước đây cờ `two_signatures` CỘNG THÊM chữ ký Chủ tịch
# cho mọi khoản ngoài dự toán, bất kể to nhỏ. Nay nó không cộng nữa; cấp duyệt thuần theo mốc F1.
#
# BẢNG SỰ THẬT SAU ĐỢT NÀY, và Chủ tịch đã xem đúng bảng này trước khi chốt:
#
#     trong dự toán, dưới mốc : TGĐ
#     trong dự toán, từ mốc   : Chủ tịch
#     NGOÀI dự toán, dưới mốc : trưởng phòng (bước `cho_tp`) + TGĐ
#     NGOÀI dự toán, TỪ MỐC   : trưởng phòng (bước `cho_tp`) + TGĐ + CHỦ TỊCH   ← ba chữ ký
#
# Dòng cuối là chỗ Chủ tịch chọn SIẾT chứ không nới: hỏi "khoản 300 triệu ngoài dự toán ai ký",
# ba lựa chọn đưa ra là (theo mốc → Chủ tịch) / (luôn là TGĐ) / (cả hai), và Chủ tịch chọn CẢ HAI.
# Nếu không có dòng ấy thì một khoản ngoài dự toán 300 triệu lại nhẹ hơn cùng khoản ấy TRONG dự
# toán — ngoại lệ dễ hơn lệ thường là chỗ người ta sẽ đi vòng qua.

CAN_CU_VAI_KY = ("Chủ tịch chốt 11/10/2026 – ba cửa chính sách (tham số, đơn giá HDV, giá xe) "
                 "đi MỘT chữ ký Chủ tịch; quy tắc hạch toán, chế tài mức 3 và dự toán dưới biên "
                 "giữ HAI chữ ký; luật người trình không tự ký giữ nguyên cho cả sáu")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGƯỜI ĐỨNG ĐẦU PHÒNG — Chủ tịch chốt 11/10/2026 (Đợt LG3)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Luật: chữ ký thứ nhất là NGƯỜI ĐỨNG ĐẦU PHÒNG CỦA HỒ SƠ, chữ ký thứ hai là TGĐ.
#
# BẢNG NÀY KHAI VAI, KHÔNG KHAI TÊN NGƯỜI. Ai đang giữ vai nào là dữ liệu nhân sự, nằm ở hồ sơ
# nhân viên, không nằm trong kho mã — cùng lẽ với mọi chỗ khác trong sổ này.
#
# DANH SÁCH PHÒNG KHÔNG KHAI LẠI Ở ĐÂY. Nó đã có ở `bao_cao_phong.PHONG` (9 phòng, kèm `thuoc`
# cho bộ phận trực thuộc) và `models/hr.DEPARTMENTS` (11 mã phòng của hồ sơ nhân sự). Khai lần
# thứ ba là dựng thêm một chỗ để ba bảng lệch nhau. `test_lg3` SO bảng này với `bao_cao_phong`
# và đỏ nếu có phòng chưa khai người đứng đầu — thêm một phòng mà quên là bắt được ngay.
#
# VÌ SAO KHÔNG `import bao_cao_phong` NGAY TẠI ĐÂY: `chu_ky` là mô-đun luật, nằm dưới cùng và
# không nhập gì ngoài `models.core`; kéo `bao_cao_phong` vào là mở đường cho một vòng nhập ngược.
# Phép SO để cho phép thử làm — phép thử chạy một lần, vòng nhập thì hỏng mãi mãi.
NGUOI_DUNG_DAU_PHONG: dict[str, str] = {
    "dieu_hanh": "tp_dh",
    "kd_le":     "gd_kd",
    "kd_doan":   "ptgd_doan",
    "marketing": "ptgd_mkt",
    "hcns":      "hcns",
    "doi_xe":    "gd_doi_xe",
    "huong_dan": "tp_hd",
    "ketoan":    "ketoan_truong",
}

CAN_CU_NGUOI_DUNG_DAU = ("Chủ tịch chốt 11/10/2026 – người đứng đầu phòng của hồ sơ ký vế thứ "
                         "nhất, TGĐ ký vế thứ hai")

# Bộ phận TRỰC THUỘC một phòng thì dùng người đứng đầu của phòng mẹ. `bao_cao_phong.PHONG` khai
# quan hệ ấy ở ô `thuoc` (hôm nay: Visa thuộc Điều hành, Chủ tịch chốt 10/9/2026); bảng dưới đây
# chép LẠI quan hệ ấy chứ không tự đặt, và `test_lg3` so hai bên.
PHONG_ME = {"visa": "dieu_hanh"}

# Mảng kinh doanh → phòng bán. Nghịch đảo của `bao_cao_phong.MANG_CUA_PHONG`, và `test_lg3` canh
# đúng nghịch đảo. Hai bộ mã (mảng / phòng) có sẵn từ trước; chỗ này chỉ dịch giữa chúng.
PHONG_CUA_MANG = {"doan": "kd_doan", "le": "kd_le"}

CHUYEN_KHONG_THUOC_MANG = (
    "Chuyến này không thuộc mảng kinh doanh nào nên hệ thống KHÔNG BIẾT phòng nào bán nó, mà "
    "chuyến dưới biên 10% thì người đứng đầu phòng bán phải ký. Dịch vụ lẻ (non_package) là loại "
    "hàng riêng, cả hai phòng đều bán được. Cách xử: đặt đúng LOẠI CHUYẾN cho nó, hoặc đưa người "
    "quyết định lên một cấp. Hệ thống nói ra chỗ nó không biết thay vì đoán một phòng.")


def nguoi_dung_dau(phong: str) -> str:
    """Vai của người đứng đầu một phòng. Bộ phận trực thuộc thì lấy của phòng mẹ.

    Gõ sai mã phòng là KeyError — cùng lẽ với `can_ky`: một lỗi gõ phím không được biến thành một
    cửa chạy âm thầm bằng luật không ai khai.
    """
    ma = (phong or "").strip()
    ma = PHONG_ME.get(ma, ma)
    return NGUOI_DUNG_DAU_PHONG[ma]


def can_ky_duoi_bien(mang: str) -> tuple[str, ...]:
    """Ai ký một chuyến dưới biên 10%: người đứng đầu PHÒNG BÁN nó, rồi TGĐ.

    Chủ tịch chốt 11/10/2026 chọn "phòng BÁN nó" chứ không phải "phòng LÀM nó": dự toán do Điều
    hành lập, nhưng tiền và chỉ tiêu của chuyến thuộc về phòng bán, nên người chịu hậu quả của
    một chuyến chạy dưới biên là người ký.

    Mảng rỗng thì NÉM LỖI chứ không chọn bừa một phòng — xem `CHUYEN_KHONG_THUOC_MANG`.
    """
    phong = PHONG_CUA_MANG.get((mang or "").strip())
    if not phong:
        raise ValueError(CHUYEN_KHONG_THUOC_MANG)
    return (nguoi_dung_dau(phong), "tgd")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# NƠI CHỈ ĐỌC TRẠNG THÁI CHỮ KÝ, KHÔNG PHÁN QUYẾT — khai có tên (Đợt LG3)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Đợt LG2 dựng hàng rào `test_lg2_8` quét mọi hàm ĐẶT chữ ký. Nó bắt được hai cửa em kể thiếu —
# nhưng nó chỉ nhìn MỘT CHIỀU, và chiều còn lại mới là chỗ LG2 để lại ba lỗi:
#
#   `dong_tien_ky.muc_du_phong`      đòi ĐỦ HAI cột chữ ký của tham số, nên sau khi tham số
#                                    xuống một chữ ký thì mức dự phòng mới KHÔNG BAO GIỜ hiệu lực
#   `ptgd_doan.duoi_bien_cho_hai_chu_ky`  báo còn thiếu chữ ký "Chủ tịch" — sai tên người ký
#   `ngoai_le._tat_chan_giay_xe`     để TRỐNG ô "người quyết" khi tham số chỉ có một chữ ký
#
# Cả ba đều ĐỌC hai cột `signed_*` rồi tự suy ra luật. Nên hàng rào của LG3 quét cả nơi ĐỌC: hàm
# nào nhắc tới `signed_chutich`/`signed_tgd` thì phải HỎI bảng luật (`can_ky`, `du_chu_ky*`,
# `da_ky_cua`), hoặc có tên dưới đây vì nó chỉ HIỂN THỊ trạng thái chứ không quyết định gì.
CHI_DOC_TRANG_THAI = {
    "routes.param_out":        "Trả trạng thái hai ô chữ ký ra màn hình Tham số. Hiển thị sự "
                               "thật, không phán quyết.",
    "hr.grate_out":            "Trả trạng thái chữ ký của đơn giá HDV ra màn hình; hiển thị "
                               "sự thật, không phán quyết.",
    "hr.rate_out":             "Trả trạng thái chữ ký của giá xe ra màn hình; hiển thị sự "
                               "thật, không phán quyết.",
    "ops.pr_out":              "Trả trạng thái chữ ký của đề nghị chi ra màn hình; còn CẤP DUYỆT "
                               "thì nó hỏi `cap_duyet`, không tự suy.",
    "hach_toan.bang":          "Bảng quy tắc hạch toán; cột 'đã ký' là hiển thị trạng thái, "
                               "không quyết định gì.",
    "tours.tour_view":         "Màn hình chuyến; cột chữ ký là hiển thị trạng thái, còn ai "
                               "được ký thì `approve` hỏi bảng luật.",
    "luong_khoa.chup_tham_so": "CHỤP LẠI trạng thái chữ ký của tham số vào bản khóa lương. Ảnh "
                               "chụp một thời điểm, không phải một phép quyết — và nó chụp đúng "
                               "cả khi luật đổi, nên không nằm trong ba chỗ phải sửa.",
    "vietrip.apply_supplier_payments": "Cửa NẠP dữ liệu từ hệ Vietrip, không phải cửa ký; "
                                       "xem `KHONG_GOI_KIEM_TRA`.",
    "rules.seed_params":       "Gieo tham số mẫu lúc dựng kho dữ liệu trống, không phải cửa "
                               "chạy thật và không ai bấm được nó.",
    "seed.seed_guide_rates":   "Gieo đơn giá HDV mẫu lúc dựng kho dữ liệu trống; không phải "
                               "cửa chạy thật.",
    "seed.seed_vehicle_rates": "Gieo giá xe mẫu lúc dựng kho dữ liệu trống; không phải cửa "
                               "chạy thật.",
    "chu_ky.da_ky_cua":        "Chính là nơi ĐỌC trạng thái chữ ký cho cả hệ thống dùng chung "
                               "— gốc của phép suy, không phải một bản sao của nó.",
    "vietrip.apply_receipts":  "Cửa NẠP dữ liệu từ hệ Vietrip, không phải cửa ký; lý do đầy "
                               "đủ ở `KHONG_GOI_KIEM_TRA`.",
    "hach_toan.nap_mac_dinh":  "Gieo quy tắc hạch toán mặc định lúc dựng kho dữ liệu trống; "
                               "không phải cửa chạy thật.",
}


def can_ky(loai: str) -> tuple[str, ...]:
    """Vai trò phải ký loại hồ sơ này. Gõ sai tên loại là KeyError ngay — cố ý.

    Trả về mặc định (`.get(loai, ("chutich", "tgd"))`) nghe có vẻ an toàn hơn, nhưng nó biến một
    lỗi gõ phím thành một cửa chạy ÂM THẦM bằng luật không ai khai. Vỡ to còn hơn sai lặng.
    """
    return VAI_KY_CAN[loai]


# HAI CỘT CHỮ KÝ mà các bảng hồ sơ chính sách đang có. Đây là TRẠNG THÁI của hồ sơ, không phải
# LUẬT — `VAI_KY_CAN` ở trên mới là luật. Trộn hai thứ làm một chính là cách sáu cửa trước đợt
# này viết tay `("chutich", "tgd")` vào cả ba chỗ rồi không ai phân biệt được chỗ nào là luật.
VAI_CO_O_KY = ("chutich", "tgd", "ptgd_doan")


def da_ky_cua(ho_so) -> dict[str, str]:
    """Đọc trạng thái chữ ký từ một hồ sơ, không cần nơi gọi viết tay tên vai nào.

    Không phải bảng nào cũng có đủ ba cột: `tours` có thêm `signed_ptgd_doan` từ Đợt LG2, còn
    `params`, `guide_rates`, `vehicle_rates` thì không. `getattr(..., False)` đọc cột không có
    thành RỖNG, và rỗng là đúng: bảng ấy không có chữ ký loại đó thật.

    Trả ĐỦ mọi cột là nói đúng hiện trạng; còn CẦN mấy chữ ký là việc của `can_ky`.
    `kiem_tra_nguoi_ky` đọc các GIÁ TRỊ của bảng này để bắt một người ký thay hai vai, nên bỏ
    bớt cột là bỏ luôn phép bắt ấy.
    """
    return {v: ("x" if getattr(ho_so, f"signed_{v}", False) else "")
            for v in VAI_CO_O_KY}


def da_ky_mot_vai(ho_so, vai: str) -> bool:
    """Vai này đã ký hồ sơ ấy chưa — MỘT chỗ đọc cho cả hệ thống (Đợt VA-WEB5, 13/10/2026).

    Phải đọc HAI nguồn, và đó là cả lý do hàm này tồn tại:

        cột `signed_<vai>`   sự thật của các bản trước Đợt LG3, và là nơi DUY NHẤT có chữ ký của
                             ba vai `chutich`, `tgd`, `ptgd_doan` trên những hồ sơ cũ
        ô `nguoi_da_ky`      sự thật từ Đợt LG3 trở đi, và là nơi DUY NHẤT có chữ ký của những
                             vai KHÔNG có cột riêng — `gd_kd` chẳng hạn: bảng `tours` không có
                             cột `signed_gd_kd` và sẽ không bao giờ có, vì LG3 cố ý không dựng
                             thêm cột cho mỗi vai mới

    Bỏ nguồn thứ hai là xoá chữ ký của mọi vai không có cột — đúng lỗi màn hình chi tiết chuyến
    mắc ngày 13/10/2026: Giám đốc Kinh doanh ký rồi mà màn hình vẫn hiện "…". `tours.approve`
    đọc đủ hai nguồn từ LG3; chỗ HIỆN thì chỉ đọc một. Nay cả hai gọi chung hàm này.
    """
    if bool(getattr(ho_so, f"signed_{vai}", False)):
        return True
    return vai in doc_nguoi_da_ky(getattr(ho_so, "nguoi_da_ky", "") or "")


def _ghep_chu_ky(vai: tuple[str, ...], ho_so) -> list[dict]:
    """Ghép LUẬT (danh sách vai) với TRẠNG THÁI. Chỗ dựng dòng chữ ký duy nhất của hệ thống."""
    return [{"vai": v, "ten": ROLES.get(v, v), "da_ky": da_ky_mot_vai(ho_so, v)} for v in vai]


def chu_ky_duoi_bien_de_hien(mang: str, ho_so) -> list[dict]:
    """Chữ ký của một chuyến dưới biên — luật THEO MẢNG, không phải bảng tĩnh.

    `VAI_KY_CAN["du_toan_duoi_bien"]` ghi (ptgd_doan, tgd) và dòng ấy ĐÚNG cho mảng Đoàn, SAI
    cho mảng Lẻ: Đợt LG3 đã thay nó bằng `can_ky_duoi_bien(mang)` ở cửa ký, nhưng Đợt VA-WEB4
    lại cho màn hình đọc bảng tĩnh — nên một chuyến LẺ dưới biên hiện ra "Phó TGĐ tour đoàn"
    trong khi người phải ký là Giám đốc Kinh doanh. Đo được trên TL-BKK-1005 ngày 13/10/2026.

    Mảng rỗng thì NÉM `ValueError` y như `can_ky_duoi_bien` — nơi gọi phải nói ra chỗ hệ thống
    không biết, không được hiện một phòng đoán bừa.
    """
    return _ghep_chu_ky(can_ky_duoi_bien(mang), ho_so)


def chu_ky_de_hien(loai: str, ho_so) -> list[dict]:
    """MỘT CHỖ cho mọi màn hình ĐỌC chữ ký — Đợt VA-WEB4, 12/10/2026.

    Trước đợt này bốn màn hình gõ tay tên vai vào mã web: `"CT … · TGĐ …"`. Đợt LG2 đổi ba cửa
    chính sách sang MỘT chữ ký Chủ tịch và đổi `VAI_KY_CAN` theo, nhưng chữ trên màn hình thì
    không đổi — nên dòng `nguong_chu_tich_duyet_chi` = 100.000.000, ĐÃ đủ ký và ĐANG có hiệu
    lực, vẫn hiện ra là "TGĐ …", tức là còn thiếu. Đo được trên production ngày 12/10/2026.

    Màn hình nói sai về chữ ký nặng hơn sai chính tả: người đọc sẽ đi tìm một chữ ký không ai
    cần, hoặc tưởng hồ sơ chưa xong và không dám tiêu tiền theo nó.

    Hàm này ghép LUẬT (`can_ky`) với TRẠNG THÁI (`da_ky_cua`) và CHỈ trả về những vai mà luật
    đòi cho loại hồ sơ ấy. Vai không có trong luật thì không xuất hiện — nên không còn dấu "…"
    nào là giả. Thiếu vế nào cũng không dùng được: `can_ky` một mình không biết ai đã ký,
    `da_ky_cua` một mình trả đủ ba cột kể cả cột luật không đòi, và chính nó là chỗ sinh ra
    "TGĐ …" của hôm nay.
    """
    return _ghep_chu_ky(can_ky(loai), ho_so)


def ten_vai_ky(loai: str) -> list[str]:
    """Tên các vai phải ký, cho tiêu đề và nút Trình — cũng đọc từ bảng luật, không gõ tay.

    Trả TÊN (`Chủ tịch HĐQT`) chứ không trả MÃ (`chutich`): nút bấm là chỗ người đọc, và `ROLES`
    đã là nơi duy nhất khai tên vai từ trước. Dựng thêm một bảng tên nữa trong mã web là dựng
    thêm một chỗ để hai bảng lệch nhau.
    """
    return [ROLES.get(v, v) for v in can_ky(loai)]


def kiem_tra_mot_nguoi_hai_vai(u, da_ky: dict[str, str]) -> None:
    """CHỈ phép chặn "một người không ký thay cả hai vai" — không kiểm vai, không kiểm người trình.

    VÌ SAO TÁCH RA KHỎI `kiem_tra_nguoi_ky`. Hàm kia kiểm BA thứ cùng lúc, trong đó có "vai này
    có nằm trong danh sách được ký không". Cửa duyệt đề nghị chi không dùng được vế ấy: vai được
    ký của nó tính theo TỪNG HỒ SƠ (mốc tiền, ngoài dự toán hay không — xem `ops.cap_duyet`), và
    Chủ tịch đi qua bằng toàn quyền 06/9/2026 để ký thay cấp TGĐ, lúc ấy vai ông không nằm trong
    danh sách mà vẫn đúng luật. Gọi hàm kia ở đó là chặn nhầm ông.

    Nên cửa chi gọi hàm này, và vẫn tự giữ phép chặn người-lập-không-tự-ký của riêng nó với lời
    nhắn nói rõ ai đã lập. Tách một phép kiểm ra khỏi ba phép kiểm thì mỗi chỗ dùng đúng phần nó
    cần, còn hơn nới lỏng hàm chung cho vừa một chỗ.
    """
    ten = getattr(u, "username", "")
    if ten and ten in da_ky.values():
        vai_cu = next(v for v, n in da_ky.items() if n == ten)
        raise HTTPException(422, f"{ten} đã ký hồ sơ này ở vai {ROLES.get(vai_cu, vai_cu)} – "
                                 "một người không ký thay cả hai vai")


def doc_nguoi_da_ky(o: str) -> dict[str, str]:
    """Đọc ô `nguoi_da_ky` dạng "vai:tên,vai:tên" thành bảng {vai: tên}.

    Một chỗ đọc, một chỗ ghi, để không nơi nào tự tách chuỗi theo kiểu của riêng nó. Ô rỗng —
    mọi hồ sơ lập trước Đợt LG2 — trả về bảng rỗng, và bảng rỗng nghĩa là KHÔNG BIẾT ai đã ký,
    chứ không phải chưa ai ký. Phép chặn một-người-hai-vai vì thế không bắt được hồ sơ cũ; nó
    chỉ bảo vệ từ nay. Nói ra để không ai tưởng hồ sơ cũ cũng đã được soi.
    """
    ra: dict[str, str] = {}
    for phan in (o or "").split(","):
        phan = phan.strip()
        if not phan or ":" not in phan:
            continue
        vai, ten = phan.split(":", 1)
        if vai.strip() and ten.strip():
            ra[vai.strip()] = ten.strip()
    return ra


def ghi_nguoi_da_ky(da_ky: dict[str, str]) -> str:
    """Ngược của `doc_nguoi_da_ky`. Bỏ ô trống, sắp theo vai để chuỗi ổn định giữa hai lần ghi."""
    return ",".join(f"{v}:{da_ky[v]}" for v in sorted(da_ky) if da_ky.get(v))


def du_chu_ky_cua(loai: str, da_ky: dict[str, str]) -> bool:
    return du_chu_ky(da_ky, can_ky(loai))


def con_thieu_cua(loai: str, da_ky: dict[str, str]) -> list[str]:
    return con_thieu(da_ky, can_ky(loai))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CỬA KÝ KHÔNG GỌI `kiem_tra_nguoi_ky` — KHAI CÓ TÊN, CÓ NGÀY, CÓ NGƯỜI QUYẾT
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Phép thử `test_lg2` quét mọi hàm có ĐẶT chữ ký (`signed_chutich` / `signed_tgd`) và đòi hàm ấy
# gọi `kiem_tra_nguoi_ky`. Cửa nào cố ý không gọi thì phải có tên ở đây — không có tên là ĐỎ.
# Nhờ vậy cửa ký thứ bảy mai sau không lặng lẽ mọc ra thiếu lớp kiểm soát.
KHONG_GOI_KIEM_TRA = {
    "tours.approve": (
        "CHUYẾN DƯỚI BIÊN 10%. Chủ tịch quyết 11/10/2026: BIẾT VÀ CHẤP NHẬN, không bịt ở đợt này. "
        "Lỗ đo được: cửa này chỉ chặn 'vai này đã ký rồi', nên một người giữ CẢ hai tài khoản "
        "`chutich` và `tgd` ký được cả hai chữ ký cho cùng một chuyến, và người lập dự toán ký "
        "được chuyến của chính mình. Đo 19/9/2026: 220 tài khoản, SÁU người giữ từ hai tài khoản "
        "trở lên — nên đây không phải lỗ lý thuyết. Hệ quả: `du_toan_duoi_bien` ở bảng trên ghi "
        "HAI chữ ký, nhưng hai chữ ký ấy hôm nay chưa chắc là hai NGƯỜI. Bịt lại mất đúng một "
        "dòng gọi `kiem_tra_nguoi_ky`; để mở là một lựa chọn, không phải một chỗ bỏ sót."),
    "vietrip.apply_receipts": (
        "KHÔNG PHẢI CỬA KÝ — là cửa NẠP dữ liệu từ hệ Vietrip, Chủ tịch được nêu 11/10/2026. Nó "
        "đặt `signed_tgd = True` cho hồ sơ nhập về cùng với `approved_by = \"vietrip\"`, nghĩa là "
        "chữ ký ấy KHÔNG do ai trong hệ này bấm, và ô `approved_by` nói đúng điều đó cho người "
        "đọc sổ. Khai ở đây vì phép quét soi theo HÀNH VI — có đặt chữ ký hay không — chứ không "
        "soi theo ý định; soi theo hành vi là đúng, vì ý định thì không đo được."),
}


def kiem_tra_nguoi_ky(u: User, vai_tro_can: tuple[str, ...], nguoi_trinh: str = "", da_ky: dict[str, str] | None = None) -> None:
    """Ném HTTPException nếu người này không được ký bước hiện tại."""
    da_ky = da_ky or {}
    if u.role not in vai_tro_can:
        raise HTTPException(403, "Bước này cần chữ ký của " + " và ".join(ROLES.get(r, r) for r in vai_tro_can))
    if nguoi_trinh and u.username == nguoi_trinh:
        raise HTTPException(422, "Người trình hồ sơ không được ký duyệt chính hồ sơ mình trình – "
                                 "chữ ký thứ hai phải là một người khác thì mới là một lớp kiểm soát")
    if da_ky.get(u.role):
        raise HTTPException(422, f"Vai trò {ROLES.get(u.role, u.role)} đã ký hồ sơ này rồi")
    if u.username in da_ky.values():
        raise HTTPException(422, f"{u.username} đã ký hồ sơ này ở vai trò khác – một người không ký thay cả hai vai")


def du_chu_ky(da_ky: dict[str, str], vai_tro_can: tuple[str, ...]) -> bool:
    return all(da_ky.get(r) for r in vai_tro_can)


def con_thieu(da_ky: dict[str, str], vai_tro_can: tuple[str, ...]) -> list[str]:
    return [ROLES.get(r, r) for r in vai_tro_can if not da_ky.get(r)]
