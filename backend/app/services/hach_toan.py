"""Bộ quy tắc hạch toán – máy chạy quy ước, người sửa quy ước.

Trước đây quy ước nằm trong một tệp Excel và trong đầu người: mỗi tháng hơn bốn nghìn dòng
được phân loại thủ công. Ở đây quy ước là dữ liệu: mỗi dòng nói "gặp nghiệp vụ thế này thì
ghi Nợ tài khoản này – Có tài khoản kia", có ngày hiệu lực và hai chữ ký như tham số chính sách.

Bốn quyết định của Chủ tịch ngày 08/9/2026 mà bộ quy tắc này mã hóa:
  1. Công ty là BÊN CHÍNH cho mọi dịch vụ – tour, tour gom khách lẻ, visa, vé máy bay, land.
     Không có nghiệp vụ "đại lý ăn hoa hồng"; không dùng tiêu chí loại khách để chọn tài khoản.
  2. Mọi đơn đều có doanh thu VÀ giá vốn. "Giá vốn bằng 0" là THIẾU DỮ LIỆU, không phải bản
     chất khác – đơn đó bị cổng chặn giữ lại, không được ghi doanh thu (xem cong_chan.py).
  3. Mọi khách đều đi qua 131/511, kèm cờ theo dõi hóa đơn (đã xuất / khách không lấy / chờ xuất).
     "Có lấy hóa đơn hay không" là chuyện chứng từ, không phải chuyện bản chất.
  4. Số bảo hiểm xã hội lấy từ bảng lương, không tính lại theo tỷ lệ.

Ba quyết định bổ sung về nhóm tài chính (Chủ tịch, 08/9/2026):
  5. LÃI VAY GHI KHI TRẢ, không trích trước theo kỳ. Hệ quả phải biết và không được giấu: tháng nào trả
     lãi thì tháng đó gánh toàn bộ, tháng không trả thì lãi bằng 0 – nên lãi lỗ THEO THÁNG không dùng để
     so sánh giữa các tháng. Số theo năm và theo kỳ báo cáo vẫn đúng.
  6. Phí ngân hàng tách làm hai theo TT99: phí dịch vụ thông thường vào 6428; phí gắn với khoản vay vào
     635, vì TT99 nêu đích danh khoản này trong nội dung TK 635.
  7. Công ty KHÔNG dùng tiền vay ngoài ngân hàng để chạy đáo hạn. Cổng đáo hạn vì vậy chỉ canh hai chân
     ngân hàng; nếu về sau có phát sinh thì phải khai thành một khoản vay thật đứng tên người cho vay.

Căn cứ pháp lý: Thông tư 99/2025/TT-BTC (hiệu lực 01/01/2026) – bản chất quan trọng hơn hình thức;
TK 511 không bao gồm các khoản thu hộ bên thứ ba (Điều về TK 511); TK 338 gồm 7 tài khoản cấp 2.
"""
from datetime import date, datetime
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.hach_toan import (QuyTacHachToan, NGUON, DOI_TUONG, HINH_THUC_TT,
                                  HTTT_QUA_NGAN_HANG, HTTT_QUA_TIEN_MAT, TK_TIEN_MAT, TK_TIEN_GUI)
from app.models.core import User
from app.services import rules as R

CAN_CU_TT99 = "TT99/2025/TT-BTC"
CAN_CU_QD = "Quyết định Chủ tịch 08/9/2026 – Công ty là bên chính, mọi đơn có doanh thu và giá vốn"

VAT_DU_LICH = 0.08   # dịch vụ lữ hành nội địa – thuế suất ghi trên hóa đơn thực tế của Vietourist

# ma, ten, nguon, dieu_kien, tk_no, tk_co, tk_thue, ben_thue, ty_le, doi_tuong, cong_trinh, dien_giai, uu_tien, can_cu
MAC_DINH = [
    # ---- Chặng 1: tiền vào ----
    ("THU_KHACH", "Khách trả tiền – mọi khách, mọi loại dịch vụ", "tien_vao",
     {"khop_don": True}, "1121", "131", "", "", 0, "khach", True,
     "Thu tiền {ma} – {khach}", 10,
     CAN_CU_QD + ". Không tách khách công ty / khách lẻ: cùng là bên chính nên cùng ghi 131."),
    ("THU_CHUA_RO", "Tiền vào chưa nhận ra đơn nào", "tien_vao",
     {"khop_don": False}, "1121", "3388", "", "", 0, "", False,
     "Tiền vào chờ xác định – {noi_dung}", 90,
     CAN_CU_TT99 + " TK 338. Treo chờ xác định, KHÔNG ghi doanh thu khi chưa biết của đơn nào."),
    ("THU_BAO_LUU", "Khách hủy tour, giữ tiền bảo lưu", "tien_vao",
     {"chua": ["bảo lưu", "bao luu"]}, "1121", "3387", "", "", 0, "khach", False,
     "Bảo lưu {ma} – {khach}", 20,
     CAN_CU_TT99 + " TK 3387 doanh thu chưa thực hiện."),

    # ---- Chặng 2: chi phí mua vào ----
    ("MUA_CO_HD", "Mua dịch vụ đầu vào, nhà cung cấp có hóa đơn GTGT", "mua_vao",
     {"co_hoa_don": True}, "154", "331", "133", "no", VAT_DU_LICH, "ncc", True,
     "Chi phí {ma} – {ncc}", 10,
     CAN_CU_TT99 + " TK 154 tập hợp theo mã công trình = mã đơn."),
    ("MUA_KHONG_HD", "Mua dịch vụ đầu vào, nhà cung cấp không xuất hóa đơn", "mua_vao",
     {"co_hoa_don": False}, "154", "331", "", "", 0, "ncc", True,
     "Chi phí {ma} – {ncc} (chưa có hóa đơn)", 20,
     "Vẫn là chi phí của đơn. Thiếu hóa đơn là rủi ro thuế, ghi cờ theo dõi chứ không đổi tài khoản."),
    ("TRICH_TRUOC", "Chi phí đã phát sinh, chứng từ về sau", "mua_vao",
     {"trich_truoc": True}, "154", "335", "", "", 0, "ncc", True,
     "Trích trước chi phí {ma} – {ncc}", 30,
     CAN_CU_TT99 + " TK 335. Ghi đúng kỳ phát sinh, không đợi hóa đơn."),

    # ---- Chặng 3: tạm ứng cho hướng dẫn viên / nhân viên ----
    ("TAM_UNG", "Chi tạm ứng cho HDV / nhân viên đi đoàn", "tien_ra",
     {"muc_chi": ["tam_ung"]}, "141", "1121", "", "", 0, "nhan_vien", False,
     "Tạm ứng {ma} – {nhan_vien}", 10,
     "Sửa quy ước cũ: tiền giao cho người của công ty là TẠM ỨNG (141), không phải phải thu khác (138)."),
    ("HOAN_UNG", "Hoàn ứng theo quyết toán đoàn", "quyet_toan",
     {"co_tam_ung": True}, "154", "141", "", "", 0, "nhan_vien", True,
     "Hoàn ứng {ma} – {nhan_vien}", 20,
     "Tạm ứng đã tiêu trở thành chi phí của đơn."),
    ("CHI_PHI_CONG_TAC", "Vé máy bay / chi phí đi công tác của cán bộ công ty", "tien_ra",
     {"muc_chi": ["cong_tac"]}, "642", "1121", "", "", 0, "nhan_vien", False,
     "Công tác phí – {nhan_vien}", 15,
     "Quyết định 08/9/2026: ba dòng vé máy bay của lãnh đạo là CHI PHÍ CÔNG TÁC, không phải doanh thu."),

    # ---- Chặng 4: hoàn thành dịch vụ – doanh thu và giá vốn ----
    ("DOANH_THU", "Hoàn thành dịch vụ – ghi doanh thu", "quyet_toan",
     {"da_ket_thuc": True, "co_gia_von": True}, "131", "5113", "3331", "co", VAT_DU_LICH, "khach", True,
     "Doanh thu {ma} – {ten}", 10,
     CAN_CU_QD + ". Cổng chặn: chưa có giá vốn thì không chạy quy tắc này."),
    ("GIA_VON", "Hoàn thành dịch vụ – kết chuyển giá vốn", "quyet_toan",
     {"da_ket_thuc": True, "co_gia_von": True}, "632", "154", "", "", 0, "", True,
     "Giá vốn {ma} – {ten}", 11,
     CAN_CU_TT99 + " TK 632. Đi liền với DOANH_THU, cùng một mã công trình."),
    ("HOA_HONG", "Hoa hồng trả đại lý / cộng tác viên bán tour", "mua_vao",
     {"muc_chi": ["hoa_hong"]}, "641", "331", "", "", 0, "ncc", True,
     "Hoa hồng {ma} – {ncc}", 25,
     "Chi phí bán hàng, không trừ vào doanh thu."),

    # ---- Chặng 5: lương và bảo hiểm ----
    ("LUONG", "Lương phải trả người lao động", "luong",
     {"phan": "luong"}, "642", "334", "", "", 0, "nhan_vien", False,
     "Lương tháng {ky}", 10, "Số lấy từ bảng lương đã duyệt."),
    ("BHXH_CTY", "Bảo hiểm phần công ty đóng", "luong",
     {"phan": "bh_cong_ty"}, "642", "3383", "", "", 0, "", False,
     "BHXH-BHYT-BHTN phần công ty tháng {ky}", 20,
     "Quyết định 08/9/2026: lấy số từ BẢNG LƯƠNG, không tính lại theo tỷ lệ."),
    ("BHXH_NLD", "Bảo hiểm khấu trừ vào lương người lao động", "luong",
     {"phan": "bh_nguoi_lao_dong"}, "334", "3383", "", "", 0, "", False,
     "BHXH phần người lao động tháng {ky}", 21,
     "Quyết định 08/9/2026: lấy số từ bảng lương."),
    ("TNCN", "Thuế thu nhập cá nhân khấu trừ tại nguồn", "luong",
     {"phan": "tncn"}, "334", "3335", "", "", 0, "", False,
     "Thuế TNCN tháng {ky}", 22, CAN_CU_TT99 + " TK 3335."),
    ("TRA_LUONG", "Chi trả lương qua ngân hàng", "tien_ra",
     {"muc_chi": ["luong"]}, "334", "1121", "", "", 0, "", False,
     "Trả lương tháng {ky}", 30, ""),

    # ---- Chặng 6: khấu hao và chi phí quản lý ----
    ("KHAU_HAO", "Khấu hao tài sản cố định", "ket_chuyen",
     {"phan": "khau_hao"}, "642", "2141", "", "", 0, "", False,
     "Khấu hao TSCĐ tháng {ky}", 40,
     "Khấu hao là khoản chênh lớn nhất giữa lãi gộp theo đoàn và lãi gộp trên sổ (3,46 tỷ / 6T-2026)."),
    ("CHI_QLDN", "Chi phí quản lý doanh nghiệp trả bằng tiền", "tien_ra",
     {"muc_chi": ["quan_ly"]}, "642", "1121", "", "", 0, "ncc", False,
     "Chi phí quản lý – {noi_dung}", 40, ""),

    # ---- Chặng 6b: tài chính – vay, ngân hàng, trả nhà cung cấp ----
    # Bổ sung 08/9/2026 theo chỉ ra của Chủ tịch: bảng quy ước ban đầu KHÔNG có dòng nào về tài chính.
    # Nặng nhất là TRA_NCC: có quy ước ghi nợ phải trả lúc mua, nhưng không có quy ước ghi lúc trả tiền –
    # nghĩa là tiền ra khỏi tài khoản mà công nợ nhà cung cấp không bao giờ giảm.
    ("TRA_NCC", "Trả tiền / ứng trước cho nhà cung cấp", "tien_ra",
     {"muc_chi": ["tra_ncc", "ung_ncc"]}, "331", "1121", "", "", 0, "ncc", False,
     "Trả nhà cung cấp – {ncc}", 12,
     "Ứng trước cũng ghi 331 và thể hiện bằng số dư NỢ 331 – đúng chỉ tiêu 'Trả trước cho người bán' "
     "trên Báo cáo tình hình tài chính. Không tách sang tài khoản khác."),
    ("VAY_NHAN", "Nhận giải ngân khoản vay", "tien_vao",
     {"muc_thu": ["giai_ngan_vay"]}, "1121", "3411", "", "", 0, "ngan_hang", False,
     "Nhận giải ngân {ngan_hang}", 12,
     CAN_CU_TT99 + " TK 3411. Đối tượng là bên cho vay – ngân hàng hay cá nhân đều phải có tên."),
    ("VAY_TRA_GOC", "Trả gốc khoản vay", "tien_ra",
     {"muc_chi": ["tra_goc_vay"]}, "3411", "1121", "", "", 0, "ngan_hang", False,
     "Trả gốc vay {ngan_hang}", 13,
     "Đáo hạn KHÔNG bù trừ: trả khoản cũ và nhận khoản mới là hai bút toán, nối với nhau bằng mã đáo hạn. "
     "Bù trừ thành một dòng thì dư nợ vay trên sổ không bao giờ đứng ở đỉnh và dòng tiền mất một vòng."),
    ("VAY_LAI", "Trả lãi vay", "tien_ra",
     {"muc_chi": ["lai_vay"]}, "635", "1121", "", "", 0, "ngan_hang", False,
     "Lãi vay {ngan_hang}", 14, CAN_CU_TT99 + " TK 635."),
    ("KY_QUY_CHI", "Ký quỹ, thế chấp, đặt cọc dài hạn", "tien_ra",
     {"muc_chi": ["ky_quy"]}, "244", "1121", "", "", 0, "ncc", False,
     "Ký quỹ {ncc}", 17, CAN_CU_TT99 + " TK 244."),
    ("KY_QUY_HOAN", "Nhận lại tiền ký quỹ", "tien_vao",
     {"muc_thu": ["hoan_ky_quy"]}, "1121", "244", "", "", 0, "ncc", False,
     "Hoàn ký quỹ {ncc}", 16, CAN_CU_TT99 + " TK 244."),
    ("LAI_TIEN_GUI", "Lãi tiền gửi ngân hàng", "tien_vao",
     {"muc_thu": ["lai_tien_gui"]}, "1121", "515", "", "", 0, "ngan_hang", False,
     "Lãi tiền gửi {ngan_hang}", 14, CAN_CU_TT99 + " TK 515."),
    ("PHI_NGAN_HANG", "Phí dịch vụ ngân hàng thông thường (chuyển tiền, quản lý tài khoản)", "tien_ra",
     {"muc_chi": ["phi_ngan_hang"]}, "6428", "1121", "", "", 0, "ngan_hang", False,
     "Phí ngân hàng {ngan_hang}", 18,
     CAN_CU_TT99 + " TK 6428 'Chi phí bằng tiền khác' – phí dịch vụ ngân hàng không gắn với khoản vay "
     "thì là chi phí quản lý, không phải chi phí tài chính."),
    ("PHI_VAY", "Phí gắn với khoản vay (thẩm định hồ sơ, thu xếp, cam kết)", "tien_ra",
     {"muc_chi": ["phi_vay"]}, "635", "1121", "", "", 0, "ngan_hang", False,
     "Phí khoản vay {ngan_hang}", 16,
     CAN_CU_TT99 + " TK 635 nêu đích danh 'thẩm định hồ sơ vay vốn, chi phí thu xếp khoản vay'. Chỉ chạy "
     "cho phí không vốn hóa; phí lớn phải phân bổ dần thì ghi giảm 341 rồi phân bổ, Kế toán lập tay."),
    ("NOP_THUE_GTGT", "Nộp thuế giá trị gia tăng", "tien_ra",
     {"muc_chi": ["nop_thue_gtgt"]}, "3331", "1121", "", "", 0, "", False,
     "Nộp thuế GTGT kỳ {ky}", 19, CAN_CU_TT99 + " TK 3331."),
    ("NOP_THUE_TNDN", "Nộp thuế thu nhập doanh nghiệp", "tien_ra",
     {"muc_chi": ["nop_thue_tndn"]}, "3334", "1121", "", "", 0, "", False,
     "Nộp thuế TNDN kỳ {ky}", 20, CAN_CU_TT99 + " TK 3334."),
    ("NOP_THUE_TNCN", "Nộp thuế thu nhập cá nhân đã khấu trừ", "tien_ra",
     {"muc_chi": ["nop_thue_tncn"]}, "3335", "1121", "", "", 0, "", False,
     "Nộp thuế TNCN kỳ {ky}", 21, CAN_CU_TT99 + " TK 3335."),
    ("NOP_BHXH", "Nộp bảo hiểm cho cơ quan bảo hiểm", "tien_ra",
     {"muc_chi": ["nop_bhxh"]}, "3383", "1121", "", "", 0, "", False,
     "Nộp bảo hiểm kỳ {ky}", 22, CAN_CU_TT99 + " TK 338."),

    # ---- Chặng 7: kết chuyển xác định kết quả ----
    ("KC_DOANH_THU", "Kết chuyển doanh thu sang xác định kết quả", "ket_chuyen",
     {"phan": "ket_chuyen", "buoc": 1}, "5113", "911", "", "", 0, "", False,
     "Kết chuyển doanh thu kỳ {ky}", 50, CAN_CU_TT99 + " TK 911."),
    ("KC_GIA_VON", "Kết chuyển giá vốn sang xác định kết quả", "ket_chuyen",
     {"phan": "ket_chuyen", "buoc": 2}, "911", "632", "", "", 0, "", False,
     "Kết chuyển giá vốn kỳ {ky}", 51, CAN_CU_TT99 + " TK 911."),
    ("KC_CHI_PHI", "Kết chuyển chi phí bán hàng và quản lý", "ket_chuyen",
     {"phan": "ket_chuyen", "buoc": 3}, "911", "642", "", "", 0, "", False,
     "Kết chuyển chi phí quản lý kỳ {ky}", 52, CAN_CU_TT99 + " TK 911."),
    ("KC_LAI", "Kết chuyển lãi sau thuế", "ket_chuyen",
     {"phan": "ket_chuyen", "buoc": 4}, "911", "4212", "", "", 0, "", False,
     "Kết chuyển lãi kỳ {ky}", 53, CAN_CU_TT99 + " TK 421."),
]

# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỢT R2 15/10/2026 — SÁU ĐƯỜNG TIỀN MẶT, TRƯỚC ĐỢT NÀY KHÔNG CÓ ĐƯỜNG NÀO
#
# Đọc lại `MAC_DINH` ở trên: mọi quy tắc tiền vào và tiền ra đều gõ cứng `1121`. Không một dòng
# nào chạm 1111. Một phiếu thu tiền mặt tại quầy chạy qua bộ quy tắc sẽ ghi vào TÀI KHOẢN NGÂN
# HÀNG — sổ vẫn cân, tổng tiền vẫn đúng, chỉ có quỹ tiền mặt thiếu và số dư ngân hàng thừa đúng
# một khoản bằng nhau. Cái sai ấy chỉ lộ lúc đối chiếu sao kê, tức là muộn.
#
# VÌ SAO KHÔNG SỬA SÁU DÒNG CŨ MÀ THÊM SÁU DÒNG MỚI: dòng cũ để `hinh_thuc_tt = ""`, nghĩa là
# "không phụ thuộc hình thức thanh toán" và khớp với mọi bối cảnh — đúng y hành vi hôm nay, nên
# KHÔNG một đường gọi nào đang chạy bị đổi. Dòng mới khai đích danh `tien_mat`, và luật "cụ thể
# thắng chung chung" (xem `dang_hieu_luc`) làm nó thắng khi, và CHỈ khi, bối cảnh nói rõ đây là
# tiền mặt. Lỗ thủng bịt lại mà không ai phải đổi lời gọi.
#
# ma, ten, nguon, dieu_kien, tk_no, tk_co, tk_thue, ben_thue, ty_le, doi_tuong, cong_trinh,
# dien_giai, uu_tien, can_cu, HINH_THUC_TT
MAC_DINH_TIEN_MAT = [
    ("THU_KHACH_TM", "Khách trả tiền mặt tại quầy", "tien_vao",
     {"khop_don": True}, "1111", "131", "", "", 0, "khach", True,
     "Thu tiền mặt {ma} – {khach}", 10,
     "Đợt R2 15/10/2026. Cặp tiền mặt của THU_KHACH. MISA tách TTKHTM khỏi TTKHTG.", "tien_mat"),
    ("THU_CHUA_RO_TM", "Tiền mặt vào quỹ chưa nhận ra đơn nào", "tien_vao",
     {"khop_don": False}, "1111", "3388", "", "", 0, "", False,
     "Tiền mặt chờ xác định – {noi_dung}", 90,
     CAN_CU_TT99 + " TK 338. Cặp tiền mặt của THU_CHUA_RO.", "tien_mat"),
    ("TRA_NCC_TM", "Trả tiền mặt cho nhà cung cấp", "tien_ra",
     {"muc_chi": ["tra_ncc", "ung_ncc"]}, "331", "1111", "", "", 0, "ncc", False,
     "Trả tiền mặt nhà cung cấp – {ncc}", 12,
     "Đợt R2 15/10/2026. Cặp tiền mặt của TRA_NCC.", "tien_mat"),
    ("TAM_UNG_TM", "Chi tạm ứng tiền mặt cho HDV / nhân viên", "tien_ra",
     {"muc_chi": ["tam_ung"]}, "141", "1111", "", "", 0, "nhan_vien", False,
     "Tạm ứng tiền mặt {ma} – {nhan_vien}", 10,
     "Đợt R2 15/10/2026. Cặp tiền mặt của TAM_UNG – HDV đi đoàn phần lớn nhận tiền mặt.", "tien_mat"),
    ("TRA_LUONG_TM", "Chi trả lương bằng tiền mặt", "tien_ra",
     {"muc_chi": ["luong"]}, "334", "1111", "", "", 0, "", False,
     "Trả lương tiền mặt tháng {ky}", 30,
     "Đợt R2 15/10/2026. Cặp tiền mặt của TRA_LUONG.", "tien_mat"),
    ("CHI_QLDN_TM", "Chi phí quản lý trả bằng tiền mặt", "tien_ra",
     {"muc_chi": ["quan_ly"]}, "642", "1111", "", "", 0, "ncc", False,
     "Chi phí quản lý tiền mặt – {noi_dung}", 40,
     "Đợt R2 15/10/2026. Cặp tiền mặt của CHI_QLDN.", "tien_mat"),
]

# Những quy tắc BẮT BUỘC có mã khoản mục chi phí. Đây là bốn đường mà tiền thật sự trở thành giá
# vốn của một chuyến: thiếu khoản mục ở đây thì câu "tour này lỗ ở đâu" không bao giờ trả lời
# được, dù mã tour có đủ. Khai tại ĐÂY và chỉ tại đây — xem ghi chú ở cột `can_khoan_muc`.
CAN_KHOAN_MUC = {"MUA_CO_HD", "MUA_KHONG_HD", "TRICH_TRUOC", "HOAN_UNG"}


def nap_mac_dinh(db: Session) -> int:
    """Nạp bộ quy tắc mặc định. Chạy được nhiều lần – đã có mã nào thì bỏ qua mã đó,
    KHÔNG đè lên quy tắc đang hiệu lực (kế toán có thể đã sửa)."""
    co = {q.ma for q in db.execute(select(QuyTacHachToan)).scalars()}
    them = 0
    # Đợt R2: hai danh sách nối lại, dòng cũ mang `hinh_thuc_tt = ""`, sáu dòng tiền mặt mang
    # `"tien_mat"`. Nối ở đây chứ không gộp vào một hằng số, để đọc `MAC_DINH` vẫn thấy đúng bộ
    # quy ước của Quyết định 08/9/2026 và thấy rõ phần nào là của đợt sau.
    bo = ([r + ("",) for r in MAC_DINH] + list(MAC_DINH_TIEN_MAT))
    for (ma, ten, nguon, dk, no, co_tk, thue, ben, tyle, dt, ct, dg, ut, cc, httt) in bo:
        if ma in co:
            continue
        # Cắt theo đúng độ dài cột trước khi ghi. Không phải để làm đẹp: SQLite KHÔNG ép độ dài VARCHAR
        # còn PostgreSQL thì có, nên một chuỗi quá dài đi qua toàn bộ phép thử ở máy rồi làm hỏng lệnh
        # INSERT lúc khởi động trên máy chủ thật – và hàm này chạy trong lifespan, nên hỏng ở đây là
        # CẢ API không lên được. Chuyện này đã xảy ra ngày 08/9/2026 với can_cu của PHI_VAY (363 ký tự).
        # Phép thử test_moi_gia_tri_mac_dinh_vua_do_dai_cot canh để không bao giờ phải cắt thật.
        ten, dg, cc = ten[:200], dg[:200], cc[:200]
        db.add(QuyTacHachToan(
            ma=ma, ten=ten, nguon=nguon, dieu_kien=dk, tk_no=no, tk_co=co_tk, tk_thue=thue,
            ben_thue=ben, ty_le_thue=tyle, doi_tuong=dt, can_cong_trinh=ct, dien_giai=dg,
            uu_tien=ut, can_cu=cc, hinh_thuc_tt=httt, can_khoan_muc=(ma in CAN_KHOAN_MUC),
            effective_from=date(2026, 1, 1),
            status="active", signed_chutich=True, signed_tgd=True, proposed_by="quyet_dinh_08-9-2026"))
        them += 1
    if them:
        db.commit()
    return them


def dang_hieu_luc(db: Session, nguon: str = "", on: date | None = None) -> list[QuyTacHachToan]:
    """Quy tắc đang hiệu lực tại một ngày. Cùng một mã có nhiều bản theo ngày – lấy bản mới nhất
    đã có hiệu lực, không lấy bản ký cho tương lai."""
    on = on or date.today()
    q = select(QuyTacHachToan).where(QuyTacHachToan.status == "active", QuyTacHachToan.effective_from <= on)
    if nguon:
        q = q.where(QuyTacHachToan.nguon == nguon)
    rows = db.execute(q.order_by(desc(QuyTacHachToan.effective_from), desc(QuyTacHachToan.id))).scalars().all()
    moi_nhat: dict[str, QuyTacHachToan] = {}
    for r in rows:
        moi_nhat.setdefault(r.ma, r)
    # ĐỢT R2 15/10/2026 — CỤ THỂ THẮNG CHUNG CHUNG, và đây là một LUẬT chứ không phải một mẹo sắp
    # xếp. Quy tắc khai đích danh một hình thức thanh toán nói nhiều hơn quy tắc để trống, nên nó
    # phải được XÉT TRƯỚC — nếu không thì sáu dòng tiền mặt của đợt này có nằm trong bảng cũng vô
    # dụng: `THU_KHACH` (ưu tiên 10, hình thức để trống, khớp mọi bối cảnh) sẽ ăn mất mọi phiếu
    # thu tiền mặt trước khi `THU_KHACH_TM` được hỏi tới.
    #
    # Xếp theo HÌNH THỨC chứ không hạ `uu_tien` của sáu dòng mới xuống số nhỏ hơn: `uu_tien` là
    # thứ Kế toán sửa được trên màn hình, mà một luật tồn tại nhờ hai con số tình cờ hơn kém nhau
    # thì nó sẽ hỏng vào ngày có người chỉnh thứ tự ưu tiên vì một lý do khác hẳn. `test_r2_3`
    # canh đúng điều này: hạ ưu tiên dòng tiền mặt xuống dưới dòng ngân hàng, luật vẫn phải đứng.
    return sorted(moi_nhat.values(), key=lambda r: (0 if r.hinh_thuc_tt else 1, r.uu_tien, r.ma))


def _khop(dk: dict | None, boi_canh: dict) -> bool:
    """Điều kiện rỗng là khớp mọi thứ. Mỗi khóa trong điều kiện phải khớp; thiếu khóa trong
    bối cảnh coi như KHÔNG khớp – không đoán.

    Cách so THEO KIỂU của giá trị điều kiện, và đây là chỗ đã sai một lần ngày 08/9: điều kiện
    đúng/sai so theo đúng/sai, danh sách so theo phần tử, còn lại so bằng nhau. Trước bản sửa,
    mọi giá trị không nằm trong hai khóa được liệt kê sẵn đều rơi xuống phép so đúng/sai – nên
    "muc_thu: hoan_ky_quy" khớp nhầm quy tắc giải ngân vay, và "phan: lai_vay_du_thu" khớp nhầm
    quy tắc khấu hao, chỉ vì cả hai vế đều khác rỗng. Sai kiểu này không báo lỗi bao giờ; nó chỉ
    lặng lẽ chọn nhầm tài khoản."""
    if not dk:
        return True
    noi_dung = str(boi_canh.get("noi_dung") or "").lower()
    for k, v in dk.items():
        if k == "chua":
            if not any(str(x).lower() in noi_dung for x in v): return False
        elif k == "khong_chua":
            if any(str(x).lower() in noi_dung for x in v): return False
        elif k == "ma_bat_dau":
            ma = str(boi_canh.get("ma") or "").upper()
            if not any(ma.startswith(str(x).upper()) for x in v): return False
        elif isinstance(v, bool):
            # Chỉ điều kiện kiểu ĐÚNG/SAI mới so theo đúng/sai.
            if k not in boi_canh or bool(boi_canh.get(k)) != v: return False
        elif isinstance(v, (list, tuple, set)):
            if boi_canh.get(k) not in v: return False
        else:
            if boi_canh.get(k) != v: return False
    return True


def _khop_hinh_thuc(q: QuyTacHachToan, boi_canh: dict) -> bool:
    """ĐỢT R2 — hình thức thanh toán là một phần của KHÓA, xét riêng khỏi `dieu_kien`.

    Xét riêng chứ không nhét vào `dieu_kien` là có chủ ý: `dieu_kien` là JSON Kế toán sửa tự do,
    còn đây là một cột có danh sách giá trị đóng (`HINH_THUC_TT`) mà phép thử canh được. Nhét vào
    JSON thì một lỗi gõ (`"tien_mat "` thừa dấu cách) im lặng biến quy tắc thành không bao giờ
    khớp, và không gì kêu lên.

    Quy tắc để TRỐNG khớp mọi bối cảnh — đó là hành vi của toàn bộ bảng trước đợt này, giữ nguyên
    để không đường gọi nào đang chạy bị đổi.
    """
    if not q.hinh_thuc_tt:
        return True
    return str(boi_canh.get("hinh_thuc_tt") or "") == q.hinh_thuc_tt


def chon(db: Session, nguon: str, boi_canh: dict, on: date | None = None) -> QuyTacHachToan | None:
    """Chọn quy tắc đầu tiên khớp bối cảnh, theo thứ tự ưu tiên. Không khớp thì trả None –
    gọi bên ngoài phải đưa nghiệp vụ vào hàng chờ kế toán, tuyệt đối không đoán tài khoản."""
    for q in dang_hieu_luc(db, nguon, on):
        if _khop_hinh_thuc(q, boi_canh) and _khop(q.dieu_kien, boi_canh):
            return q
    return None


def _dien_giai(mau: str, boi_canh: dict) -> str:
    out = mau or ""
    for k, v in boi_canh.items():
        out = out.replace("{" + k + "}", str(v or ""))
    while "{" in out and "}" in out:      # khóa còn lại không có trong bối cảnh – bỏ đi
        i, j = out.index("{"), out.index("}")
        if j < i: break
        out = out[:i] + out[j + 1:]
    return " ".join(out.split())[:300]


def dung_but_toan(q: QuyTacHachToan, so_tien: float, boi_canh: dict) -> dict:
    """Dựng các dòng bút toán từ một quy tắc. so_tien là số tiền TỔNG (đã gồm thuế nếu quy tắc tách thuế).

    Trả về {"dien_giai", "lines"} theo đúng dạng post_entry nhận – chưa ghi sổ.
    """
    so_tien = round(float(so_tien or 0), 0)
    if so_tien <= 0:
        raise ValueError("Số tiền phải lớn hơn 0")
    truoc_thue, thue = so_tien, 0.0
    if q.ty_le_thue and q.tk_thue:
        truoc_thue = round(so_tien / (1 + q.ty_le_thue), 0)
        thue = round(so_tien - truoc_thue, 0)
    dt = {"khach": (boi_canh.get("khach"), boi_canh.get("ma_khach")),
          "ncc": (boi_canh.get("ncc"), boi_canh.get("ma_ncc")),
          "nhan_vien": (boi_canh.get("nhan_vien"), boi_canh.get("ma_nhan_vien")),
          "ngan_hang": (boi_canh.get("ngan_hang"), boi_canh.get("ma_ngan_hang"))}.get(q.doi_tuong, ("", ""))
    # ĐỢT R2 15/10/2026 — CHIỀU KHOẢN MỤC CHI PHÍ.
    #
    # Chặn ở ĐÂY, chỗ dựng bút toán, chứ không ở màn hình: màn hình là một trong nhiều đường vào
    # (robot sao kê, lệnh hàng loạt, lời gọi API thẳng đều đi qua hàm này và đều KHÔNG đi qua màn
    # hình). Một hàng rào chỉ ở màn hình là không có hàng rào nào.
    #
    # Và chặn chứ không điền mặc định "KM_KHAC": điền hộ thì mọi chi phí thiếu khai lặng lẽ dồn
    # vào ô "khác", bảng phân tích vẫn ra đủ dòng, và không ai biết nó rỗng nghĩa. Thà dừng lại
    # và hỏi — đúng ranh giới 09/9/2026: máy không đoán hộ người.
    khoan_muc = str(boi_canh.get("khoan_muc") or "").strip().upper()
    if q.can_khoan_muc and not khoan_muc:
        raise ValueError(
            f"Quy tắc {q.ma} bắt buộc có mã khoản mục chi phí. Đây là đường tiền trở thành giá vốn "
            "của một chuyến; thiếu khoản mục thì câu 'tour này lỗ ở landtour hay ở vé máy bay' "
            "không bao giờ trả lời được. Chọn một mã ở danh mục Khoản mục chi phí rồi ghi lại.")
    chung = {"partner": dt[0] or "", "partner_code": dt[1] or "", "item_code": khoan_muc,
             "project_code": (boi_canh.get("ma") or "") if q.can_cong_trinh else "",
             "booking_id": boi_canh.get("booking_id"), "tour_id": boi_canh.get("tour_id"),
             "doc_no": boi_canh.get("so_chung_tu") or "", "note": f"quy tắc {q.ma}"}
    if q.ben_thue == "co":          # thuế đầu ra: Nợ tổng – Có doanh thu + Có thuế
        lines = [dict(chung, account=q.tk_no, debit=so_tien),
                 dict(chung, account=q.tk_co, credit=truoc_thue)]
        if thue: lines.append(dict(chung, account=q.tk_thue, credit=thue))
    elif q.ben_thue == "no":        # thuế đầu vào: Nợ chi phí + Nợ thuế – Có tổng
        lines = [dict(chung, account=q.tk_no, debit=truoc_thue)]
        if thue: lines.append(dict(chung, account=q.tk_thue, debit=thue))
        lines.append(dict(chung, account=q.tk_co, credit=so_tien))
    else:
        lines = [dict(chung, account=q.tk_no, debit=so_tien),
                 dict(chung, account=q.tk_co, credit=so_tien)]
    return {"quy_tac": q.ma, "dien_giai": _dien_giai(q.dien_giai, boi_canh), "lines": lines,
            "truoc_thue": truoc_thue, "thue": thue, "tong": so_tien}


def xem_truoc(db: Session, nguon: str, so_tien: float, boi_canh: dict, on: date | None = None) -> dict:
    """Xem trước bút toán mà không ghi sổ. Không có quy tắc khớp thì nói thẳng là không có."""
    q = chon(db, nguon, boi_canh, on)
    if q is None:
        return {"khop": False, "ly_do": "Không có quy tắc nào khớp – nghiệp vụ này phải do Kế toán định khoản tay",
                "nguon": nguon, "boi_canh": boi_canh}
    bt = dung_but_toan(q, so_tien, boi_canh)
    bt.update({"khop": True, "ten_quy_tac": q.ten, "can_cu": q.can_cu, "hieu_luc_tu": str(q.effective_from)})
    return bt


def de_xuat(db: Session, u: User, data: dict) -> QuyTacHachToan:
    """Đề xuất một quy tắc mới hoặc bản sửa của quy tắc cũ – chờ đủ hai chữ ký mới có hiệu lực."""
    q = QuyTacHachToan(
        ma=data["ma"].strip().upper()[:40], ten=data["ten"][:200], nguon=data["nguon"],
        dieu_kien=data.get("dieu_kien") or {}, tk_no=str(data["tk_no"]), tk_co=str(data["tk_co"]),
        tk_thue=str(data.get("tk_thue") or ""), ben_thue=data.get("ben_thue") or "",
        ty_le_thue=float(data.get("ty_le_thue") or 0), doi_tuong=data.get("doi_tuong") or "",
        can_cong_trinh=bool(data.get("can_cong_trinh")), dien_giai=(data.get("dien_giai") or "")[:200],
        hinh_thuc_tt=str(data.get("hinh_thuc_tt") or ""), can_khoan_muc=bool(data.get("can_khoan_muc")),
        uu_tien=int(data.get("uu_tien") or 100), can_cu=(data.get("can_cu") or "")[:200],
        ghi_chu=data.get("ghi_chu") or "", effective_from=data["effective_from"],
        status="pending", proposed_by=u.username)
    if q.nguon not in NGUON:
        raise ValueError(f"Nguồn nghiệp vụ không hợp lệ: {q.nguon}")
    if q.doi_tuong not in DOI_TUONG:
        raise ValueError(f"Cách lấy đối tượng không hợp lệ: {q.doi_tuong}")
    # ĐỢT R2 — ba phép kiểm của hình thức thanh toán, chạy LÚC ĐỀ XUẤT chứ không lúc ghi sổ: một
    # quy tắc sai khai mà lọt vào bảng thì nó định khoản sai cho tới khi có người phát hiện, còn
    # chặn ở đây thì người đề xuất đọc được ngay câu giải thích.
    if q.hinh_thuc_tt not in HINH_THUC_TT:
        raise ValueError(f"Hình thức thanh toán không hợp lệ: {q.hinh_thuc_tt}")
    cham = (q.tk_no, q.tk_co)
    if q.hinh_thuc_tt in HTTT_QUA_TIEN_MAT and any(t.startswith(TK_TIEN_GUI) for t in cham):
        raise ValueError(
            f"Quy tắc {q.ma} khai hình thức TIỀN MẶT mà lại ghi vào tài khoản tiền gửi "
            f"({[t for t in cham if t.startswith(TK_TIEN_GUI)][0]}). Đây đúng loại sai làm quỹ "
            "tiền mặt và số dư ngân hàng cùng lệch một khoản bằng nhau, và chỉ lộ ra lúc đối "
            "chiếu sao kê.")
    if q.hinh_thuc_tt in HTTT_QUA_NGAN_HANG and any(t.startswith(TK_TIEN_MAT) for t in cham):
        raise ValueError(
            f"Quy tắc {q.ma} khai hình thức {HINH_THUC_TT[q.hinh_thuc_tt]} — chạy trên tài khoản "
            f"ngân hàng — mà lại ghi vào tài khoản tiền mặt "
            f"({[t for t in cham if t.startswith(TK_TIEN_MAT)][0]}). Kể cả 'Séc tiền mặt': séc "
            "lĩnh tiền mặt vẫn rút trên tài khoản ngân hàng, nên vế tiền của nó là 112x.")
    from app.models.accounting import Account
    for tk in (q.tk_no, q.tk_co, q.tk_thue):
        if tk and not db.get(Account, tk):
            raise ValueError(f"Tài khoản {tk} không có trong danh mục")
    db.add(q); db.flush()
    R.audit(db, u.username, u.role, "de_xuat_quy_tac_hach_toan", f"quy_tac:{q.ma}",
            after={"no": q.tk_no, "co": q.tk_co, "hieu_luc": str(q.effective_from)})
    db.commit()
    return q


def ky(db: Session, u: User, qid: int) -> QuyTacHachToan:
    from app.services import chu_ky as CK
    q = db.get(QuyTacHachToan, qid)
    if not q or q.status != "pending":
        raise ValueError("Quy tắc không ở trạng thái chờ ký")
    # GIỮ NGUYÊN HAI CHỮ KÝ — Chủ tịch chốt 11/10/2026: ba cửa chính sách xuống một chữ ký,
    # cửa này KHÔNG. Đọc từ bảng chứ không viết tay, để lần sau đổi ý thì đổi đúng một dòng.
    can = CK.can_ky("quy_tac_hach_toan")
    da_ky = CK.da_ky_cua(q)
    CK.kiem_tra_nguoi_ky(u, can, nguoi_trinh=q.proposed_by, da_ky=da_ky)
    setattr(q, f"signed_{u.role}", True)
    da_ky[u.role] = "x"
    R.audit(db, u.username, u.role, "ky_quy_tac_hach_toan", f"quy_tac:{q.ma}", after={"id": q.id})
    if CK.du_chu_ky(da_ky, can):
        q.status = "active"
        R.audit(db, u.username, u.role, "quy_tac_hach_toan_hieu_luc", f"quy_tac:{q.ma}",
                after={"no": q.tk_no, "co": q.tk_co, "hieu_luc": str(q.effective_from)})
    db.commit()
    return q


def bang(db: Session, on: date | None = None) -> dict:
    """Bảng quy ước để đọc trên màn hình và để đối chiếu với kiểm toán."""
    hl = {q.id for q in dang_hieu_luc(db, "", on)}
    rows = db.execute(select(QuyTacHachToan).order_by(QuyTacHachToan.nguon, QuyTacHachToan.uu_tien, QuyTacHachToan.ma)).scalars().all()
    return {
        "nguon": NGUON, "doi_tuong": DOI_TUONG, "hinh_thuc_tt": HINH_THUC_TT,
        "quy_tac": [{
            "id": q.id, "ma": q.ma, "ten": q.ten, "nguon": q.nguon, "nguon_ten": NGUON.get(q.nguon, q.nguon),
            "dieu_kien": q.dieu_kien or {}, "tk_no": q.tk_no, "tk_co": q.tk_co, "tk_thue": q.tk_thue,
            "ben_thue": q.ben_thue, "ty_le_thue": q.ty_le_thue, "doi_tuong": q.doi_tuong,
            "can_cong_trinh": q.can_cong_trinh, "hinh_thuc_tt": q.hinh_thuc_tt,
            "hinh_thuc_tt_ten": HINH_THUC_TT.get(q.hinh_thuc_tt, q.hinh_thuc_tt),
            "can_khoan_muc": q.can_khoan_muc, "dien_giai": q.dien_giai, "uu_tien": q.uu_tien,
            "can_cu": q.can_cu, "ghi_chu": q.ghi_chu, "effective_from": str(q.effective_from),
            "status": q.status, "signed_chutich": q.signed_chutich, "signed_tgd": q.signed_tgd,
            "proposed_by": q.proposed_by, "dang_dung": q.id in hl,
        } for q in rows],
    }
