"""Màn hình nào cũng phải có cửa nhập, hoặc phải nói rõ nó là tấm gương soi cái gì.

Ranh giới Chủ tịch đặt 09/9/2026: phần mềm viết cấu trúc, phép tính và hệ điều hành; SỐ LIỆU do
nhân viên các bộ phận tự nhập – gõ biểu, tải tệp, tải ảnh. Hệ quả trực tiếp: mỗi con số trên màn
hình phải lần ngược được về MỘT CỬA có người đứng.

Bản rà 09/9 đi qua 83 mục menu và tìm được ba chỗ hỏng, cả ba cùng một dạng: cửa có tồn tại nhưng
người phải dùng nó không với tới, hoặc cửa chưa bao giờ được dựng dù máy chủ đã mở đường.

  · Lệnh điều xe – người duy nhất được chốt lệnh không thấy màn hình nào chứa mẫu.
  · Nạp dữ liệu – 26 bộ nạp chỉ có cửa tệp, dù máy chủ có sẵn đường gõ tay một dòng.
  · Đính kèm – bảy loại hồ sơ khai gắn được tệp mà không màn hình nào dựng ô gắn.

Rà tay chỉ đúng tại thời điểm rà. Màn hình thứ 84 thêm vào tuần sau sẽ không có ai rà lại, và nó
lặng lẽ nằm đó không cửa. Nên chuyển bản rà thành một phép kiểm chạy cùng bộ phép thử.

Phép thử này KHÔNG đòi mọi màn hình đều ghi được. Màn hình chỉ xem là chuyện bình thường và đúng –
báo cáo, nhật ký, bảng tổng hợp. Nó đòi một điều khác: màn hình chỉ xem phải NÓI RA nó soi cái gì,
và đường đọc ấy phải còn đó. Thêm một con số mới từ một nguồn khác vào một tấm gương là lúc phải
dừng lại hỏi con số ấy vào hệ thống bằng cửa nào – phép thử này là chỗ dừng ấy.
"""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
SHELL = WEB / "components" / "Shell.tsx"

# Lời gọi GHI. Bắt cả ba lối viết đang dùng: api(p,{method:"POST"}) · fetch(...,{method}) ·
# hàm bọc kiểu const post = async (path, json?, method = "POST") => api(path, {method, json}).
RE_API = re.compile(r'\bapi(?:<[^>]*>)?\(([^;]{0,300}?)\)\s*[;,.\)\}]', re.S)
RE_FETCH = re.compile(r'\bfetch\(([^;]{0,300}?)\)\s*[;,.\)\}]', re.S)

# Màn hình CHỈ XEM, kèm lý do và những đường nó đọc. Thêm tên vào đây phải kèm cả hai – lý do trống
# hoặc đường đọc trống thì phép thử không còn canh được gì.
CHI_XEM = {
    "/": ("Bảng tổng quan: gộp lại con số của các phân hệ khác, không sở hữu con số nào của riêng "
          "mình. Số vào hệ thống ở màn hình của từng phân hệ.", ("/dashboard",)),
    "/tai-xe": ("Hồ sơ tài xế: màn hình gom ba thứ đã có cửa ở nơi khác – hồ sơ người nạp ở Nhân "
                "sự, bằng lái nạp bằng bộ nạp tệp 'Bằng lái tài xế', xe gán tài xế ở màn hình Đội "
                "xe. Thêm cửa ghi thứ hai cho cùng dữ liệu là thêm một chỗ để hai bên ghi lệch "
                "nhau; mỗi dòng trên màn hình đã chỉ sẵn chỗ phải đi để sửa.", ("/tai-xe",)),
    "/sales-reports": ("Báo cáo bán hàng: tính từ booking và tour đã có. Cửa nhập nằm ở màn hình "
                       "Booking và Tour, không phải ở đây.", ("/sales-reports",)),
    "/cong-no": ("Công nợ: suy ra từ booking, phiếu thu và đề nghị chi. Sửa công nợ bằng cách sửa "
                 "chứng từ gốc, không phải bằng cách gõ đè lên bảng tổng hợp.", ("/cong-no",)),
    "/hieu-qua-doi-xe": ("Chi phí & hiệu quả đội xe: tính từ nhật trình chuyến, nhiên liệu, phí cầu "
                         "đường, bảo dưỡng – tất cả đều có bộ nạp riêng ở màn hình Nạp dữ liệu.",
                         ("/fleet/ban-tin-sang", "/fleet/hieu-qua")),
    "/phieu-luong": ("Phiếu lương của tôi: kỳ lương do HCNS chốt ở màn hình Lương, thưởng & hoa "
                     "hồng. Người xem phiếu không sửa được phiếu của chính mình.",
                     ("/phieu-luong/ky-cua-toi",)),
    # Thêm 09/9/2026 cùng đợt gộp nhánh Đợt 2. Ba màn hình bị bộ kiểm này bắt, và CHỈ MỘT trong ba là
    # chỉ-xem thật – hai cái kia là cửa còn thiếu và đã dựng cửa, không khai vòng cho qua.
    "/bao-cao": ("Báo cáo tự động theo phòng ban: mọi con số tính TẠI CHỖ từ dữ liệu của các phân hệ "
                 "khác, không sở hữu con số nào của riêng mình. Cửa nhập nằm ở màn hình của từng "
                 "phòng. Màn hình này mà ghi được thì nó thôi là báo cáo.", ("/bao-cao",)),
    # TC-71 · 19/9/2026 — Sổ chuyến còn nợ. Đây là chỉ-xem THẬT, không phải khai vòng cho qua:
    # màn hình không sở hữu con số nào của riêng nó, mà liệt kê chuyến chưa đóng sổ và đưa đường
    # dẫn sang đúng chuyến để người có quyền đóng ở CỬA THẬT (`services/tours.close`).
    #
    # VÀ VIỆC KHÔNG CÓ CỬA GHI Ở ĐÂY LÀ MỘT LỰA CHỌN, không phải chỗ còn thiếu. Em đã hỏi và anh
    # Tuấn chốt 18/9: "Danh sách + đường dẫn sang chuyến", không đóng sổ hàng loạt. Lý do: đóng sổ
    # là việc khó lùi — làm hàng loạt từ một màn hình tổng thì một cú bấm nhầm đi xa hơn nhiều so
    # với cái lợi về tốc độ, và ở màn hình tổng người bấm không nhìn thấy dòng quyết toán của
    # chuyến để mà biết mình đang chốt cái gì.
    "/so-con-no": ("Sổ chuyến còn nợ: liệt kê chuyến đã chạy mà chưa đóng sổ. Không sở hữu con số "
                   "nào của riêng mình — mọi số lấy từ sổ quyết toán của chính chuyến. Cửa đóng sổ "
                   "nằm ở từng chuyến (/tours/<id>), và anh Tuấn chốt 18/9/2026 là KHÔNG dựng cửa "
                   "đóng hàng loạt ở đây vì đóng sổ là việc khó lùi.",
                   ("/so-con-no",)),
    # XE-KD-1 · 11/11/2026 — chỗ trống CUỐI CÙNG của danh sách này, và nó được tiêu vào
    # đúng câu hỏi mà danh sách này sinh ra để hỏi: «con số ấy vào hệ thống bằng cửa nào».
    # Màn này trả lời được từng cửa một, nên nó thuộc đây chứ không cần một nhóm mới.
    "/lich-xe-trong": ("Lịch xe trống để bán: khoảng trống và công suất tuần của đội xe, cho "
                       "phòng Kinh doanh đẩy bán. Không sở hữu con số nào của riêng mình — "
                       "ngày có lệnh đọc từ lệnh điều xe (cửa: Lệnh điều xe → Lập lệnh), đề "
                       "nghị chờ từ đề nghị xe (cửa: Lệnh điều xe → Đề nghị xe), xe bị chặn "
                       "từ báo hỏng mức phải dừng xe (cửa: Đội xe → tab Báo hỏng), biển số và "
                       "số chỗ từ hồ sơ xe (cửa: Đội xe → Hồ sơ xe). Cả bốn cửa đều ở màn của "
                       "ĐỘI XE, và dựng thêm một cửa ở đây là để hai nơi lệch nhau.",
                       # VH-17: màn nay vẽ lịch 90 ngày đầy đủ (LichXe90) — đọc cửa lịch, vẫn chỉ xem.
                       ("/fleet/lich-xe-tuong-lai",)),
}

# ── BÀN LÀM VIỆC THEO VAI — nhóm ĐẾM RIÊNG, mở ngày 24/9/2026 ───────────────────────────────────
#
# ĐÂY LÀ VIỆC CHÍNH PHÉP THỬ NÀY ĐÃ DẶN PHẢI LÀM. Dòng cảnh giác viết ngày 24/9/2026 ở
# `test_danh_sach_chi_xem_co_tran` nói rõ: ba vai của phòng Đoàn thì còn hai vai chưa dựng, và
# "nếu vòng sau lại nâng trần thêm hai lần với cùng một lý do, thì lý do ấy đã thành thói quen chứ
# không còn là lý do — lúc ấy việc phải làm là ĐỔI CÁCH ĐẾM (tách riêng nhóm bàn làm việc), không
# phải nâng tiếp."
#
# Vòng 3/3 tới đúng chỗ ấy. Nên nâng trần lên 10 là làm đúng cái đã tự dặn mình đừng làm; tách
# nhóm thì trần của CHI_XEM tụt về 8 (đúng con số ngày 19/9, trước khi bàn làm việc đầu tiên ra
# đời) và nhóm mới mang trần riêng cùng một câu hỏi riêng.
#
# CÂU HỎI CỦA NHÓM NÀY KHÁC câu hỏi của CHI_XEM. CHI_XEM hỏi "con số này vào hệ thống bằng cửa
# nào". Bàn làm việc hỏi thêm một câu nữa: "cửa GHI của chính vai này nằm ở đâu, và vì sao nó
# không nằm ở đây" — vì một bàn làm việc không có cửa ghi nào mà cũng không chỉ được cửa ghi của
# mình thì nó là một bảng tin, không phải một bàn làm việc.
BAN_LAM_VIEC = {
    "/ptgd-doan": ("Bàn làm việc Phó TGĐ tour đoàn: hàng đợi dự toán đoàn chờ ký, sổ quá hạn quyết "
                   "toán và bảng lãi lỗ đã chốt. Không sở hữu con số nào của riêng mình.",
                   ("/ptgd-doan/ban-lam-viec",),
                   # Cửa ghi của vai này, và vì sao nó không nằm trên màn hình:
                   # ký dự toán đã có cửa thật với cổng biên, luật hai chữ ký và nhật ký. Dựng cửa
                   # ký thứ hai ở đây là tạo bản sao thứ hai của một luật, và bản sao nào rồi cũng
                   # lệch. Ký hàng loạt thì người bấm không nhìn thấy dòng dự toán để biết mình vừa
                   # duyệt cái gì — duyệt là việc phải ĐỌC, không phải việc phải bấm.
                   "POST /api/v1/tours/{id}/approve"),
    "/sales-admin": ("Bàn làm việc Sale Admin phòng Đoàn: dự toán chờ chuyển, soát giá vốn và chứng "
                     "từ NCC, hồ sơ đoàn, tiến độ thu tiền, tiến độ quyết toán, dữ liệu khách. "
                     "Không sở hữu con số nào của riêng mình.",
                     ("/sales-admin/ban-lam-viec",),
                     # Hai cửa ghi của vai này nằm trên CHÍNH CHUYẾN, và cùng một lý do như trên:
                     # chuyển một dự toán là việc phải đọc dự toán ấy. Một nút "chuyển" cạnh một
                     # dòng tóm tắt là lời mời chuyển mà chưa mở ra xem — và cổng chặn duy nhất của
                     # vị trí này mất hết ý nghĩa đúng vào lúc nó trở nên tiện tay.
                     "POST /api/v1/tours/{id}/chuyen-dieu-hanh · .../tra-lai-kinh-doanh"),
    "/ban-tour-le": ("Bàn bán tour lẻ của Phòng Kinh doanh Lẻ: chuyến lẻ đang bán, mỗi dòng kèm "
                     "thông tin chuyến và ba con số dự toán cùng biên. Không sở hữu con số nào của "
                     "riêng mình — mọi số tính từ dự toán do Điều hành lập.",
                     ("/ban-tour-le/ban-lam-viec",),
                     # Cửa ghi của vai này là cửa BÁN, và nó đã có từ đầu. Vì sao không đặt ở đây:
                     # bán một chỗ là việc phải mở chuyến ra đọc trước — chương trình, điểm dừng
                     # nghỉ, hạn huỷ. Một nút "đặt" cạnh một dòng tóm tắt là lời mời đặt mà chưa
                     # xem, và người nhận hậu quả là khách. Thêm nữa, chỗ ngồi có hàng rào sức
                     # chứa (25/9/2026) nằm trong `tours.create_booking`; một cửa đặt thứ hai ở
                     # đây là một chỗ nữa phải nhớ gọi hàng rào ấy.
                     "POST /api/v1/requests"),
    # `/xe` ĐÃ RỜI NHÓM NÀY, cùng ngày nó vào — 09/11/2026. Sáng nay nó khai "chỉ đọc" và
    # lời khai ấy đúng với bản lúc ấy. Chiều, PR #753 (ks54) cho ngăn kéo chi phí kỳ LÀM
    # VIỆC THẬT: màn `/xe` nhập `components/doixe/ChiPhiKyPanel`, tệp có cả POST lẫn DELETE.
    # Nó có cửa ghi thật thì nó không còn thuộc nhóm ngoại lệ này — và hàng rào
    # `test_man_hinh_chi_xem_van_dung_la_chi_xem` reo đúng chỗ ấy. Thêm cửa nhập là việc
    # TỐT; việc phải làm khi nó xảy ra là bỏ lời khai cũ đi, không phải giữ nó nằm đó.
    #
    # ĐỢT MKT-1 (09/11/2026) -- hai ban cua phong Marketing. Chung hoi DUNG cau cua nhom nay
    # ("cua ghi cua vai nay nam o dau") va tra loi duoc tung cai mot, nen chung o day chu
    # khong o mot nhom moi. Xem tran o phep thu duoi.
    "/ptgd-mkt": ("Bàn làm việc Phó TGĐ Marketing: PR quá hạn phản hồi, nội dung chờ duyệt, chiến dịch chờ đưa vào chạy và kỳ chưa chốt số. Không sở hữu con số nào của riêng mình — bốn ô đều đếm trên bảng gốc mà màn Marketing đang dùng.",
                  ("/marketing/ban-ptgd",),
                  # Cửa ghi của vai này nằm trên bảy tab của màn `/marketing`, và bàn dẫn
                  # thẳng tới đúng tab thay vì dựng bản sao thứ hai. Cùng một lẽ với ba
                  # dòng trên: duyệt một nội dung hay phát một thông cáo là việc phải ĐỌC
                  # thứ mình đang duyệt, và một nút duyệt cạnh một dòng tóm tắt là lời mời
                  # duyệt mà chưa mở ra xem.
                  "POST qua /marketing: tab Nội dung · Ngân sách & chiến dịch · Khủng hoảng, PR & thương hiệu · Đối soát dữ liệu"),
    "/ban-mkt": ("Bàn làm việc nhân viên Marketing: lead nằm im quá hạn do CHÍNH NGƯỜI ẤY giữ, và lead chưa gắn chiến dịch của cả phòng. Không sở hữu con số nào của riêng mình.",
                 ("/marketing/ban-nhan-vien",),
                 # Cửa ghi: chăm lead ở tab Khách tiềm năng & Sales, gắn chiến dịch ở tab
                 # Đối soát dữ liệu. Không dựng ô ghi trên bàn — chăm một lead là việc
                 # phải mở lead ấy ra đọc, không phải việc gạch một dòng trong danh sách.
                 "POST qua /marketing: tab Khách tiềm năng & Sales · tab Đối soát dữ liệu"),
}

# ── NHẬT KÝ MÁY GHI — nhóm ĐẾM RIÊNG, mở ngày 16/10/2026 ───────────────────────────────────────
#
# TÁCH NHÓM CHỨ KHÔNG NÂNG TRẦN, đúng điều tệp này đã tự dặn ở `test_danh_sach_chi_xem_co_tran`:
# "Tới dòng thứ MƯỜI thì dừng nâng và tách nhóm, đúng cách vòng 3/3 đã làm với bàn làm việc."
# Đợt HD-Q2mh tới đúng dòng thứ mười. Nâng trần lần thứ tư là làm đúng cái đã tự dặn đừng làm.
#
# VÀ CÂU HỎI CỦA NHÓM NÀY KHÁC HẲN CÂU HỎI CỦA CHI_XEM. CHI_XEM hỏi "con số này vào hệ thống bằng
# cửa nào", và mốc nó đặt ra cho lần sau là "chỉ RA ĐƯỢC từng cửa nhập thật của từng con số".
# Nhóm này KHÔNG trả lời được câu ấy, và đó không phải vì thiếu sót: số trong các bảng này do MÁY
# ghi, không người nào gõ, và VIỆC KHÔNG CÓ CỬA GHI LÀ MỘT TÍNH CHẤT AN TOÀN. Nhét chúng vào
# CHI_XEM là làm hỏng câu hỏi của CHI_XEM — một danh sách trả lời hai câu khác nhau thì không
# canh được câu nào.
#
# Câu nhóm này phải trả lời thay vào đó: VÌ SAO một cửa ghi ở đây sẽ phá đúng thứ bảng ấy sinh ra
# để giữ. Phần tử thứ ba của mỗi dòng là câu trả lời ấy, và có ca canh nó không được để trống.
NHAT_KY_MAY_GHI = {
    "/audit": ("Nhật ký nghiệp vụ: mọi thao tác ghi ở màn hình khác đều để lại một dòng ở đây. "
               "Không màn hình nào nhập vào bảng này — máy chủ tự ghi đúng lúc có thao tác.",
               ("/audit",),
               "Nhật ký này là chuỗi bất biến, mỗi bản ghi băm nối vào bản ghi trước. Gõ tay được "
               "vào đây thì dựng được một dòng cho việc chưa ai làm, hoặc sửa được một dòng đã có "
               "— mà chống đúng hai chuyện ấy là lý do nhật ký tồn tại."),
    "/dem-luot-doc": ("Đếm lượt mở cửa đọc: mỗi người × mỗi cửa × mỗi ngày một dòng, do bộ đếm ở "
                      "`services/dem_luot.py` tự ghi mỗi lần ai mở một cửa đọc đã khai. Màn hình "
                      "chỉ đọc lại con số máy chủ đã cộng, kể cả lượt trung bình mỗi ngày.",
                      ("/danh-gia/dem-luot",),
                      "Bảng này dùng để Chủ tịch quyết thu hẹp quyền đọc của một phòng. Gõ tay "
                      "được vào nó thì sửa được chính con số dùng để quyết — và người có động cơ "
                      "sửa đúng là người sắp bị siết. Không có cửa ghi là tính chất an toàn, "
                      "không phải cửa còn thiếu."),
}

# ══════════════════════════════════════════════════════════════════════════════════════════════
# NHÓM THỨ TƯ — HỒ SƠ MỘT CON NGƯỜI (CUA-1, Chủ tịch chốt 22/10/2026)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÌ SAO TÁCH NHÓM, KHÔNG NÂNG TRẦN `CHI_XEM`. `CHI_XEM` còn đúng một chỗ trống, và dùng chỗ ấy
# thì rẻ hôm nay. Nhưng `CHI_XEM` hỏi «con số này vào hệ thống bằng cửa nào», còn hai màn dưới
# đây trả lời một câu khác: «số trên hồ sơ CỦA MỘT CON NGƯỜI vào hệ thống qua cửa nào của HCNS».
# Ghi chú của nhóm `NHAT_KY_MAY_GHI` ngay trên đã nói ra cái giá: một danh sách trả lời hai câu
# khác nhau thì không canh được câu nào.
#
# Và đây đúng khuôn hai nhóm trước: cả `BAN_LAM_VIEC` lẫn `NHAT_KY_MAY_GHI` đều ra đời bằng TÁCH
# NHÓM khi `CHI_XEM` chật, không bằng nâng trần.
#
# TRẦN 2, VÀ CHỈ 2. Đợt này có đúng hai màn hồ sơ người. Màn thứ ba muốn vào đây thì phải trả lời
# được câu hỏi của nhóm, và phải có một quyết định mới — không phải một dòng sửa trần.
#
# PHẦN TỬ THỨ BA của mỗi dòng là CỬA NHẬP THẬT: người dùng đi đâu để sửa con số ấy. Có một ca canh
# nó không được để trống, vì một nhóm «chỉ xem» mà không chỉ được chỗ sửa thì nó chỉ là một lời
# khai, không phải một câu trả lời.
HO_SO_NGUOI = {
    "/nhan-vien-phong-toi": (
        "Nhân viên phòng tôi: lối vào hồ sơ cho người đứng đầu một phòng. Cửa đọc đã có từ đợt "
        "HS-4 nhưng nút bấm duy nhất lại nằm trên màn quản trị Tài khoản mà trưởng phòng không "
        "mở được — quyền có, lối vào không. Màn này KHÔNG có bảng cột riêng: cột dựng từ chính "
        "những khoá máy chủ trả về sau khi cắt qua `cat_ho_so_theo_vai`.",
        ("/employees/phong-toi",),
        "Mọi trường nhập ở Nhân sự → Hồ sơ nhân viên; phòng ban và cấp trên gắn ở Tổ chức Kinh "
        "doanh. Thêm cửa ghi ở đây là thêm một chỗ để hai bên ghi lệch nhau."),
    "/ho-so-hdv/[id]": (
        "Hồ sơ một hướng dẫn viên: thẻ hành nghề, điểm sau tour, nhận xét đã duyệt công khai. "
        "Phần máy chủ xong từ đợt HD-14; đợt CUA-1 chỉ thêm màn hình.",
        ("/huong-dan/ho-so",),
        "Họ tên, mã, phòng ban và thẻ hành nghề nhập ở Nhân sự → Hồ sơ nhân viên. Điểm và nhận "
        "xét KHÔNG ai gõ tay được: khách gửi sau tour, Phòng Hướng dẫn duyệt ở Duyệt công bố, và "
        "điểm là số máy tính từ các lượt đã duyệt."),
}

# ==============================================================================================
# NHOM THU NAM -- TRANG PHONG (Dot PH-1, Chu tich chot 08/11/2026)
# ==============================================================================================
#
# VI SAO TACH NHOM, KHONG MUON HAI CHO TRONG CUA `CHI_XEM`. `CHI_XEM` con dung hai cho ma dot nay
# can nam, nen cau "muon hay tach" tu no da co loi dap. Nhung ke ca con du cho thi van phai tach,
# vi CAU HOI KHAC NHAU. `CHI_XEM` hoi <<con so nay vao he thong bang cua nao>>. Nam trang duoi day
# khong co con so nao cua rieng chung de hoi cau ay: chung KHONG doc mot bang nghiep vu nao, chung
# gom lai nhung con so man hinh khac da tinh va ve them muc luc chuc nang. Cau dung cho nhom nay
# la <<trang nay gom so cua phong nao, va so ay sinh ra o dau>>.
#
# Day la lan thu tu kho nay tach nhom thay vi nang tran -- sau `BAN_LAM_VIEC`, `NHAT_KY_MAY_GHI`
# va `HO_SO_NGUOI`. Nang tran thi re mot lan roi mat luon cau hoi; tach nhom thi moi danh sach
# van tra loi dung mot cau.
#
# TRAN 4, VA CHI 4. VTOS co tam phong ban. Ba phong -- Marketing, HC-NS, Tai chinh - Ke toan --
# DUNG DUNG MAN HINH LAM VIEC DANG CO (`/marketing`, `/hr`, `/finance`) va nhung man ay co cua ghi
# that, nen chung khong bao gio thuoc nhom nay.
#
# PHONG THU TAM -- DIEU HANH XE -- CUNG KHONG THUOC NHOM NAY, va day la chuyen moi. Dot PH-1 ban
# dau khai `/xe` o nhom nay. Nhung PR #744 (KS-46, 08/11/2026) da dung `/xe` thanh BAN LAM VIEC
# cua Giam doc doi xe: mot man that, co hang doi viec, co ngan keo dan tay sang cua nhap, va da
# tu khai quyen trong `access.py`. Nghia la `/xe` KHONG con la mot trang chi-xem, va dua no vao
# day la khai sai mot man hinh dang lam viec. Bon la con so dong, khong phai con so tam.
#
# DUONG DOC KHAI LA `/bao-cao`, VA BAN DAU DA KHAI SAI. Em viet `("/bao-cao/pham-vi",
# "/bao-cao/chi-tieu")` -- chuoi thu hai KHONG TON TAI trong kho, em bia ra ma khong mo ma xem.
# `test_duong_doc_da_khai_van_con_tren_man_hinh` do dung vao do. Khai `/bao-cao` la dung va du: no
# la nhom cua that, `TrangPhanHe` co chuoi ay ngay trong than (`an.includes("/bao-cao")`), va no
# khop dung cach man `/bao-cao` tu khai o `CHI_XEM` phia tren.
#
# PHAN TU THU BA la CUA NHAP THAT -- nguoi dung di dau de sua con so ay. Voi nhom nay cau tra loi
# luon la "o man hinh nghiep vu cua phong", va viet ra de khong ai tuong trang phong la noi nhap.
TRANG_PHONG = {
    "/fit": (
        "Trang phòng Kinh doanh lẻ: bảng chỉ tiêu của phòng cộng mục lục chức năng. Không đọc "
        "bảng nghiệp vụ nào — số lấy từ `/api/v1/bao-cao` đã tính sẵn ở `bao_cao_phong`.",
        ("/bao-cao",),
        "Số bán hàng nhập ở Booking, Yêu cầu và Báo giá; chỉ tiêu tháng nhập ở /ke-hoach-thang."),
    "/mice": (
        "Trang phòng Kinh doanh đoàn: bảng chỉ tiêu của phòng cộng mục lục chức năng. Cùng "
        "khuôn với /fit, khác phạm vi báo cáo — số lấy từ `/api/v1/bao-cao` đã tính sẵn.",
        ("/bao-cao",),
        "Số đoàn nhập ở Booking đoàn, Hợp đồng và Báo giá đoàn; chỉ tiêu ở /ke-hoach-thang."),
    "/op": (
        "Trang phòng Điều hành tour: bảng chỉ tiêu của phòng cộng mục lục chức năng, phạm vi "
        "`dieu_hanh`. Không đọc bảng nghiệp vụ nào của riêng nó.",
        ("/bao-cao",),
        "Số điều hành nhập ở Sản phẩm, Chuyến & quyết toán, Sự cố tour và Nhà cung cấp & đặt "
        "dịch vụ."),
    "/guide": (
        "Trang phòng Hướng dẫn: bảng chỉ tiêu của phòng cộng mục lục chức năng, phạm vi "
        "`huong_dan`. Hồ sơ và phân chuyến hướng dẫn viên vẫn ở màn hình của chúng.",
        ("/bao-cao",),
        "Số hướng dẫn nhập ở Phòng Hướng dẫn và Việc của tài xế & HDV; đơn giá và phân chuyến "
        "nhập ở chính màn hình Phòng Hướng dẫn."),
}

# Năm nhóm gộp lại mới là toàn bộ màn hình không có cửa ghi. Khoá tên riêng để không nhóm nào lặng
# lẽ nuốt nhóm kia.
KHONG_CUA_GHI = {**{k: v[:2] for k, v in BAN_LAM_VIEC.items()},
                 **{k: v[:2] for k, v in NHAT_KY_MAY_GHI.items()},
                 **{k: v[:2] for k, v in HO_SO_NGUOI.items()},
                 **{k: v[:2] for k, v in TRANG_PHONG.items()}, **CHI_XEM}
assert len(KHONG_CUA_GHI) == (len(CHI_XEM) + len(BAN_LAM_VIEC) + len(NHAT_KY_MAY_GHI)
                              + len(HO_SO_NGUOI) + len(TRANG_PHONG)), \
    "năm nhóm không được trùng tên màn hình"


def _ma(src: str) -> str:
    """Bỏ chú thích, chỉ giữ mã chạy – chú thích nhắc tên một đường không tính là màn hình gọi nó."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"^\s*//.*$", " ", src, flags=re.M)
    return src


def _man_hinh() -> list:
    """Đường dẫn màn hình lấy từ menu thật (GROUPS trong Shell.tsx), không chép tay danh sách."""
    if not SHELL.exists():
        return []
    blk = _ma(SHELL.read_text(encoding="utf-8"))
    i = blk.index("export const GROUPS")
    # Mốc kết thúc là MÃ THẬT (`export const CA_NHAN`), không phải chú thích: hàm _ma() ở trên
    # xoá sạch chú thích trước khi tìm mốc. Trước 11/9/2026 mốc là tên hằng ROADMAP_ROLES; TC-2
    # bỏ hằng ấy đi và phép thử này vỡ bằng ValueError không nói gì về nguyên nhân.
    blk = blk[i: blk.index("export const CA_NHAN")]
    ra = []
    for _, href in re.findall(r'\["([^"]*)",\s*"([^"]*)"\]', blk):
        if href:
            ra.append("/" + href.split("?")[0].strip("/"))
    return sorted(set(ra))


def _ma_cua_man_hinh(duong: str) -> list[str] | None:
    """Mã CHẠY của một màn hình: tệp trang, CỘNG mã các thành phần dùng chung mà nó nhập.

    Trả về None khi không có tệp trang.

    VÌ SAO PHẢI TÍNH CẢ THÀNH PHẦN. Một màn hình không nhất thiết gọi máy chủ ngay trong
    `page.tsx`: mã có thể nằm ở `components/<Tên>.tsx` mà trang nhập vào. Đọc mỗi tệp trang thì
    một màn hình dọn mã sang thành phần sẽ TRÔNG NHƯ không đọc, không ghi gì cả — và cả hai phép
    thử dưới đây đều hoá vô hại mà vẫn xanh.

    GOM VỀ MỘT CHỖ — 11/10/2026. Trước hôm nay chỉ `_so_cua_ghi` biết đi theo thành phần, còn
    `test_duong_doc_da_khai_van_con_tren_man_hinh` thì chỉ đọc tệp trang. Hai phép thử trong cùng
    một tệp, cùng hỏi "màn hình này có mã gì", mà trả lời theo hai cách khác nhau. Chuyện lộ ra
    khi `/bao-cao` dọn bảng chỉ tiêu sang `components/BangChiTieuPhong.tsx`: phần đếm cửa ghi vẫn
    đúng, phần soát đường đọc thì đỏ và báo "/bao-cao không còn đọc /bao-cao" — trong khi màn
    hình vẫn đọc đúng cửa ấy. Lỗi của phép thử, không phải của mã, nên sửa phép thử mới đúng.

    Chỉ đi MỘT TẦNG, cố ý: thành phần của thành phần chưa có trong kho, và một phép thử đi sâu
    hơn thứ nó cần là một phép thử khó đọc mà không canh thêm được gì. Ngày nào có tầng thứ hai
    thật thì mở rộng ở đúng đây, một chỗ.

    THƯ MỤC CON — 09/11/2026. Vẫn MỘT tầng, nhưng đường dẫn nhập có thể có thư mục con:
    `@/components/doixe/ChiPhiKyPanel`. Bản cũ chỉ khớp chữ, số và gạch dưới — không nhận
    dấu gạch chéo — nên những thành phần ấy bị bỏ qua IM LẶNG. Chuyện lộ ra khi PR #753 dọn
    ô nhập chi phí kỳ của `/lai-lo-doi-xe` sang đúng một tệp như thế: cửa ghi vẫn còn, có
    cả POST lẫn DELETE, nhưng hàng rào không đọc tới và báo màn hình «không có lời gọi ghi
    nào». Lỗi của phép thử, không phải của mã — y như lần `BangChiTieuPhong` ngày
    11/10/2026, và cách sửa cũng y như thế. Phép thử ngay dưới canh đúng điều này, để nó là
    thứ đo được chứ không phải một câu hứa.
    """
    p = WEB / "app" / duong.strip("/") / "page.tsx" if duong != "/" else WEB / "app" / "page.tsx"
    if not p.exists():
        return None
    src = _ma(p.read_text(encoding="utf-8"))
    tep = [src]
    for m in re.findall(r'from "@/components/([\w/]+)"', src):
        if m == "Shell":
            continue
        q = WEB / "components" / (m + ".tsx")
        if q.exists():
            tep.append(_ma(q.read_text(encoding="utf-8")))
    return tep


def _so_cua_ghi(duong: str) -> int:
    """Đếm lời gọi ghi của một màn hình, tính cả mã của thành phần dùng chung mà nó nhập."""
    tep = _ma_cua_man_hinh(duong)
    if tep is None:
        return -1
    n = 0
    for t in tep:
        for rx in (RE_API, RE_FETCH):
            for m in rx.finditer(t):
                if re.search(r"\bmethod\b|\bjson\s*[:,}]|\bbody\b", m.group(1)):
                    n += 1
        ten = set(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*method\s*=\s*"(?:POST|PUT|PATCH|DELETE)"', t))
        ten |= set(re.findall(r'const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]{0,200}?\)\s*=>\s*\{?[^;]{0,250}?method:\s*"(?:POST|PUT|PATCH|DELETE)"', t))
        for x in ten:
            n += max(len(re.findall(r"(?<![\w.])" + re.escape(x) + r"\(", t)) - 1, 0)
    return n


def test_doc_duoc_menu_that_chu_khong_pass_suong():
    """Phép thử đọc menu bằng biểu thức chính quy; biểu thức hỏng thì nó tìm ra 0 màn hình và xanh
    suốt. Chốt một sàn để chỗ ấy không im lặng."""
    if not SHELL.exists():
        return
    mh = _man_hinh()
    assert len(mh) >= 40, f"Chỉ đọc được {len(mh)} màn hình từ GROUPS – nhiều khả năng cách đọc đã hỏng"


def test_moi_man_hinh_hoac_co_cua_ghi_hoac_khai_la_chi_xem():
    if not SHELL.exists():
        return
    thieu = []
    for d in _man_hinh():
        n = _so_cua_ghi(d)
        if n <= 0 and d not in KHONG_CUA_GHI:
            thieu.append((d, "không có tệp màn hình" if n < 0 else "không có lời gọi ghi nào"))
    assert not thieu, (
        "Màn hình không có cửa nhập nào và cũng không khai là chỉ xem: "
        + "; ".join(f"{d} ({vi})" for d, vi in thieu) +
        ". Ranh giới 09/9/2026: mỗi con số phải có một cửa cho người dùng. Dựng cửa, hoặc thêm vào "
        "CHI_XEM kèm lý do và những đường màn hình ấy đọc.")


def test_man_hinh_chi_xem_van_dung_la_chi_xem():
    """Chiều ngược lại: một màn hình đã khai chỉ xem mà nay ghi được thì lời khai thành sai.

    Không phải để cấm – thêm cửa nhập là việc tốt. Nhưng lời khai ở trên nói "số vào hệ thống ở chỗ
    khác", và câu ấy không còn đúng nữa thì phải sửa lời khai, không để nó nằm đó dẫn người đọc sai.
    """
    if not SHELL.exists():
        return
    sai = [d for d in KHONG_CUA_GHI if _so_cua_ghi(d) > 0]
    assert not sai, (
        f"Màn hình khai là chỉ xem nhưng đã có cửa ghi: {sai}. Bỏ khỏi CHI_XEM.")


def test_duong_doc_da_khai_van_con_tren_man_hinh():
    """Đường đọc đã khai phải còn đó.

    Đây là chỗ phép thử thật sự làm việc. Một tấm gương chỉ vô hại khi biết nó soi cái gì. Thêm một
    con số mới từ một nguồn khác vào màn hình chỉ xem là lúc phải dừng lại hỏi: con số ấy vào hệ
    thống bằng cửa nào, ai gõ nó. Không có chỗ dừng thì màn hình báo cáo lớn dần lên bằng những con
    số không ai nhập – và đó đúng là hình dạng của một hệ thống trông như đang chạy.
    """
    if not SHELL.exists():
        return
    hong = []
    for d, (ly_do, duong) in KHONG_CUA_GHI.items():
        assert len(ly_do) > 60, f"Lý do chỉ xem của {d} quá ngắn để là một lý do thật"
        assert duong, f"{d} khai là chỉ xem mà không nói đọc từ đâu"
        tep = _ma_cua_man_hinh(d)
        if tep is None:
            hong.append((d, "mất tệp màn hình")); continue
        src = "\n".join(tep)
        mat = [x for x in duong if x not in src]
        if mat:
            hong.append((d, f"không còn đọc {mat}"))
    assert not hong, (
        "Lời khai của màn hình chỉ xem không còn khớp với mã: "
        + "; ".join(f"{d} – {vi}" for d, vi in hong) +
        ". Nếu màn hình đổi nguồn số liệu thì sửa lời khai, và nhân thể trả lời câu: con số mới ấy "
        "vào hệ thống bằng cửa nào?")


def test_danh_sach_chi_xem_co_tran():
    """Danh sách ngoại lệ không trần là cách một phép thử tự tắt mình.

    6 (09/9/2026) → 8 (19/9/2026) → 9 (24/9/2026, bàn làm việc P.TGĐ tour đoàn) → 8 (24/9/2026,
    vòng 3/3: bàn làm việc tách sang nhóm riêng).

    LẦN NÀY TRẦN ĐI XUỐNG, và đó là chuyện đáng ghi. Dòng cảnh giác viết cùng ngày ở bản trước đã
    dặn: nếu lại nâng trần với cùng một lý do thì lý do ấy đã thành thói quen, và việc phải làm là
    ĐỔI CÁCH ĐẾM chứ không phải nâng tiếp. Vòng 3/3 tới đúng chỗ ấy nên đã tách `BAN_LAM_VIEC`
    thành nhóm riêng, có trần riêng và có thêm một câu hỏi riêng phải trả lời.

    CHI_XEM trở lại đúng con số ngày 19/9/2026 — trước khi bàn làm việc đầu tiên ra đời.

    → 9 (05/10/2026, /tai-xe). Nâng trần, nên phải trả lời đúng câu dòng trên đặt ra: lý do lần
    này CÓ PHẢI cùng một lý do đã thành thói quen không?

    KHÔNG. Lý do bị bác hồi 24/9 là "bàn làm việc theo vai" — và nó bị bác vì cách sửa đúng là
    tách nhóm, việc đã làm. /tai-xe thuộc đúng loại đã nằm sẵn trong danh sách này từ 09/9: màn
    hình GOM LẠI dữ liệu mà cửa nhập nằm ở chỗ khác — y như /sales-reports gom từ booking, hay
    /cong-no gom từ chứng từ gốc. Ba cửa của nó đều có thật và đều ở nơi khác: hồ sơ người ở Nhân
    sự, bằng lái ở bộ nạp tệp, gán xe ở màn hình Đội xe.

    MỐC CHO LẦN SAU, để câu trả lời này không tự nó thành thói quen mới: một màn hình chỉ được
    vào đây khi chỉ RA ĐƯỢC từng cửa nhập thật của từng con số nó hiện. Chỉ không ra thì đó là
    cửa còn thiếu, và việc phải làm là dựng cửa. Tới dòng thứ MƯỜI thì dừng nâng và tách nhóm,
    đúng cách vòng 3/3 đã làm với bàn làm việc.
    """
    assert len(CHI_XEM) <= 9, (
        f"Đang khai {len(CHI_XEM)} màn hình chỉ xem. Ngày 09/9/2026 là 6, ngày 19/9 là 8, ngày "
        "05/10/2026 là 9. Con số này to lên nghĩa là mỗi lần đỏ lại thêm một dòng thay vì hỏi con "
        "số kia vào hệ thống bằng cửa nào. Bàn làm việc theo vai KHÔNG khai ở đây – nhóm ấy là "
        "BAN_LAM_VIEC.")


def test_ban_lam_viec_co_tran_rieng_va_chi_duoc_cua_ghi_cua_minh():
    """Nhóm bàn làm việc có trần RIÊNG và phải trả lời thêm MỘT CÂU nữa.

    Câu ấy là: cửa GHI của chính vai này nằm ở đâu. Một bàn làm việc không có cửa ghi nào mà cũng
    không chỉ ra được cửa ghi của mình thì nó là một bảng tin, không phải một bàn làm việc — và
    người mở nó hằng ngày sẽ dần đọc nó như đọc báo.

    Trần 3: phòng Kinh doanh Đoàn có ba vai (P.TGĐ, Sale Admin, NV Sales đoàn). Vai thứ ba lập dự
    toán nên màn hình của họ CÓ cửa ghi thật và sẽ không vào nhóm này — nhưng để trần ở 3 thì dòng
    thứ tư phải dừng lại giải thích vì sao lại có thêm một vai chỉ đọc nữa, thay vì trôi qua.

    → 4 (09/11/2026, `/xe` — bàn làm việc Giám đốc đội xe, PR #744). ĐÂY LÀ CHỖ DỪNG LẠI ẤY, nên
    trả lời cho đủ.

    Lý do cũ của trần 3 là ĐẾM VAI CỦA MỘT PHÒNG: ba vai của phòng Kinh doanh Đoàn. `/xe` không
    thuộc phòng ấy — nó là vai đầu của một phòng khác, nên cách đếm cũ không với tới nó, và nâng
    trần ở đây KHÔNG phải là kéo dài một lý do đã thành thói quen.

    VÌ SAO KHÔNG TÁCH NHÓM MỚI, dù kho này quen tách hơn quen nâng: tách nhóm chỉ đúng khi nhóm
    mới hỏi một CÂU KHÁC — `BAN_LAM_VIEC` tách khỏi `CHI_XEM` vì nó hỏi thêm "cửa ghi của vai này
    ở đâu", `TRANG_PHONG` tách ra vì nó hỏi "trang gom số của phòng nào". Tách một nhóm chỉ để
    khỏi chạm vào con số trần là tách giả, và nó làm hỏng chính cái mà thói quen tách sinh ra
    để giữ.

    → 5 (09/11/2026, CÙNG NGÀY, và con số đi theo hai hướng ngược nhau trong một buổi chiều):
    `/xe` RA, hai bàn phòng Marketing VÀO.

    `/xe` ra vì nó đã có CỬA GHI THẬT. Sáng nay nó không có, và lời khai lúc ấy đúng. Chiều,
    PR #753 cho ngăn kéo chi phí kỳ làm việc thật: màn ấy nhập `components/doixe/ChiPhiKyPanel`,
    tệp có cả POST lẫn DELETE. Ngoại lệ sinh ra vì thiếu cửa, nên cửa dựng xong thì ngoại lệ
    phải đi — giữ nó nằm lại là để một lời khai sai nằm trong tệp canh lời khai.

    Hai dòng Marketing VÀO thì trả lời đúng mốc trên: Marketing là một phòng nữa, và cửa ghi
    của hai vai ấy chỉ ra được từng cái một — bảy tab của màn `/marketing`, viết rõ trong hai
    dòng khai. Vì sao HAI dòng chứ không một: phòng này có hai vai làm hai việc ngược chiều
    nhau, một người duyệt và phát ngôn, một người chạy nội dung và giữ lead. Gộp lại thì mỗi
    người phải bỏ qua nửa số ô, và một bàn mà người ngồi phải bỏ qua nửa số ô thì nó đã thôi
    là bàn làm việc.

    MỐC MỚI: dòng thứ SÁU. Nếu nó lại là một vai nữa của một phòng ĐÃ CÓ bàn ở đây thì câu hỏi
    phải đổi — không phải «vai này có cửa ghi ở đâu» nữa, mà «vì sao phòng ấy cần thêm một bàn
    thứ ba» — và lúc ấy việc phải làm là xem lại cách chia bàn, không phải nâng tiếp con số này.
    """
    assert len(BAN_LAM_VIEC) <= 5, (
        f"Đang khai {len(BAN_LAM_VIEC)} bàn làm việc chỉ đọc. Mỗi dòng thêm vào đây là một vai được "
        "cho một màn hình mà không có việc nào bấm được trên đó – hỏi lại xem vai ấy làm gì.")
    thieu = [d for d, x in BAN_LAM_VIEC.items() if len(x) < 3 or not str(x[2]).strip()]
    assert not thieu, (
        f"Bàn làm việc khai thiếu CỬA GHI của vai: {thieu}. Phải ghi rõ cửa ghi nằm ở đâu, và chú "
        "thích ngay trên dòng ấy phải nói vì sao nó không nằm trên màn hình này.")


def test_nhat_ky_may_ghi_co_tran_rieng_va_phai_noi_vi_sao_khong_co_cua_ghi():
    """Nhóm nhật ký máy ghi có trần RIÊNG và phải trả lời thêm MỘT CÂU nữa.

    Câu ấy KHÔNG phải câu của CHI_XEM. CHI_XEM hỏi "con số này vào hệ thống bằng cửa nào"; nhóm này
    không có cửa nào để chỉ, nên nó phải trả lời: vì sao một cửa ghi ở đây sẽ phá đúng thứ bảng ấy
    sinh ra để giữ. Thiếu câu đó thì nhóm này thành chỗ trốn: bất kỳ màn hình nào thiếu cửa cũng
    tự gọi mình là «nhật ký máy ghi» rồi đi qua.

    Trần 2: hôm nay đúng hai sổ máy tự ghi có màn hình — nhật ký nghiệp vụ (ghi thao tác GHI) và
    đếm lượt mở cửa (ghi thao tác ĐỌC). Dòng thứ ba phải dừng lại giải thích, thay vì trôi qua.
    """
    assert len(NHAT_KY_MAY_GHI) <= 2, (
        f"Đang khai {len(NHAT_KY_MAY_GHI)} màn hình nhật ký máy ghi. Mỗi dòng thêm vào đây là một "
        "bảng nữa không ai nhập được — hỏi lại xem con số ấy có thật do máy sinh không, hay đó là "
        "một cửa nhập còn thiếu đang mượn tên nhật ký.")
    thieu = [d for d, x in NHAT_KY_MAY_GHI.items() if len(x) < 3 or len(str(x[2]).strip()) < 60]
    assert not thieu, (
        f"Nhật ký máy ghi khai thiếu LÝ DO AN TOÀN: {thieu}. Phải nói rõ một cửa ghi ở đây sẽ phá "
        "cái gì — không nói được thì đây là cửa còn thiếu, không phải nhật ký.")


def test_ho_so_nguoi_co_tran_rieng():
    """Nhóm thứ tư có trần RIÊNG, và trần ấy là 2 (CUA-1, Chủ tịch chốt 22/10/2026).

    Danh sách ngoại lệ không trần là cách một phép thử tự tắt mình — cùng lẽ với ba trần đã có.

    Trần này đi XUỐNG từ con số của `CHI_XEM` chứ không thêm vào: đợt CUA-1 có đúng hai màn hồ sơ
    người, và chỗ trống của `CHI_XEM` được giữ nguyên chứ không tiêu. Màn thứ ba muốn vào đây thì
    phải có một QUYẾT ĐỊNH MỚI, không phải một dòng sửa số 2 thành 3 — đúng điều mà lời nhắn của
    `test_danh_sach_chi_xem_co_tran` đã dặn và hai nhóm trước đã làm theo.
    """
    assert len(HO_SO_NGUOI) <= 2, (
        f"Đang khai {len(HO_SO_NGUOI)} màn hồ sơ người. Trần là 2 (22/10/2026). Muốn thêm thì "
        "trả lời trước: màn mới có thật trả lời câu «số trên hồ sơ này vào hệ thống qua cửa nào "
        "của HCNS» không, và vì sao nó không thuộc một nhóm đã có?")


def test_ho_so_nguoi_phai_chi_ra_cua_nhap_that():
    """Phần tử thứ ba KHÔNG được để trống — đó là cả lý do nhóm này tồn tại.

    Một màn khai «chỉ xem» mà không chỉ được chỗ sửa thì nó là một lời khai, không phải một câu
    trả lời: người đọc thấy một con số sai vẫn không biết đi đâu. Cùng hình với ca canh phần tử
    thứ ba của `NHAT_KY_MAY_GHI`.
    """
    thieu = [d for d, v in HO_SO_NGUOI.items() if len(v) < 3 or not (v[2] or "").strip()]
    assert not thieu, (
        f"Màn khai trong HO_SO_NGUOI mà không nói cửa nhập thật nằm ở đâu: {thieu}. "
        "Viết ra chỗ người dùng phải đi để sửa con số ấy.")


def test_bo_doc_thay_duoc_thanh_phan_trong_thu_muc_con():
    """Tự kiểm bộ đọc thành phần: nó phải thấy cả tệp nằm trong thư mục con.

    Không có dòng này thì bản sửa 09/11/2026 có thể bị thu lại về bản chỉ khớp chữ và số mà
    mọi phép thử vẫn xanh — một hàng rào quét THIẾU tệp thì nó canh được ít hơn, chứ không đỏ.
    """
    co = sorted(p.relative_to(WEB / "components").as_posix()
                for p in (WEB / "components").glob("*/*.tsx"))
    assert co, ("kho không còn thành phần nào nằm trong thư mục con — nếu đúng thế thật thì "
                "bỏ phép thử này đi, đừng để nó xanh vì không có gì để kiểm")
    nhap = set()
    for p in WEB.glob("app/**/page.tsx"):
        nhap |= set(re.findall(r'from "@/components/([\w/]+)"',
                               _ma(p.read_text(encoding="utf-8"))))
    sau = sorted(x for x in nhap if "/" in x)
    assert sau, (
        f"Không trang nào nhập thành phần trong thư mục con, dù kho có {len(co)} tệp như thế: "
        + ", ".join(co[:5]) +
        ". Nghi là cách đọc dòng `import` đã bị thu lại và bộ đọc thành phần đang mù với cả "
        "một thư mục.")


def test_tran_cua_nhom_trang_phong():
    """TRẦN 4. Mỗi dòng thêm vào đây là một màn hình nữa KHÔNG có cửa nhập mà vẫn được cho qua.

    VTOS có tám phòng. Bốn phòng còn lại có màn hình làm việc đã có cửa ghi thật — Marketing,
    HC–NS, Tài chính – Kế toán, và Điều hành xe (`/xe`, bàn làm việc Giám đốc đội xe, PR #744) —
    nên chúng không thuộc nhóm này. Bốn là con số đóng.
    """
    assert len(TRANG_PHONG) <= 4, (
        f"Đang khai {len(TRANG_PHONG)} trang phòng. VTOS có bốn phòng dùng trang chỉ tiêu riêng; "
        "bốn phòng kia dùng màn hình làm việc đã có cửa ghi. Thêm dòng ở đây là nới một ngoại lệ.")
    thieu = [d for d, x in TRANG_PHONG.items() if len(x) < 3 or not str(x[2]).strip()]
    assert not thieu, (
        f"Trang phòng thiếu lời khai CỬA NHẬP THẬT: {thieu}. Một nhóm «chỉ xem» mà không chỉ "
        "được chỗ sửa thì nó chỉ là một lời khai, không phải một câu trả lời.")
