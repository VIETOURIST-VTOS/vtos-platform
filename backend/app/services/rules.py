"""Rules engine, nhật ký hash-chain, tính toán dự toán, robot cảnh báo."""
import hashlib, json, math
from datetime import datetime, date, timedelta
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from app.models.core import Param, AuditLog, Tour, Booking, ServiceRequest, Alert, TOUR_TYPES, User

# ====================== THAM SỐ MẶC ĐỊNH (theo bộ chính sách 27/8/2026 + Văn bản đính chính) ======================
DEFAULT_PARAMS = [
    ("nguong_bien", "0.10", "Ngưỡng biên lợi nhuận kế hoạch (cổng chặn)", "tỷ lệ", "MHQT Điều 10"),
    ("han_qt_doan", "7", "Hạn quyết toán tour đoàn", "ngày", "MHQT Điều 10; ĐC Điều 1"),
    ("han_qt_le", "3", "Hạn quyết toán tour lẻ", "ngày", "MHQT Điều 10; ĐC Điều 1"),
    ("han_kt_xac_nhan", "3", "Kế toán xác nhận sau khi đóng số", "ngày làm việc", "KT-HCNS; ĐC Điều 1"),
    ("sla_booking_phut", "120", "Điều hành tạo booking sau khi nhận yêu cầu", "phút làm việc", "ĐH Điều 2"),
    ("moc_d7", "7", "Mốc D-n kiểm tra chuyến dưới hòa vốn", "ngày", "ĐH Điều 13"),
    # Đội xe Đợt 1: bật thành 1 khi hồ sơ giấy tờ 14 xe đã nhập đủ. Để 0 trong giai đoạn nhập liệu, vì chặn
    # theo giấy tờ khi chưa có giấy tờ nào trong hệ thống thì mọi lệnh điều xe đều dừng.
    ("xe_chan_khi_thieu_giay", "0", "Chặn phát lệnh khi thiếu dữ liệu giấy tờ xe/tài xế", "0 hoặc 1", "Đội xe Vietrip v1.3 §7"),
    ("han_muc_mkt", "5000000", "Hạn mức chi Marketing cần 2 chữ ký", "đồng", "MKT Điều 8"),
    # Giá theo tuổi – Chủ tịch chốt 10/9/2026, sửa tỷ lệ 11/9/2026. Bốn con số này KHÔNG viết cứng
    # trong mã vì chúng là chính sách giá, và chính sách giá thì đổi: đổi thì sửa tham số, ký duyệt
    # theo quy trình tham số đã có, không phải sửa phần mềm rồi triển khai lại.
    #
    # Quan trọng hơn: tham số ở đây có hiệu lực THEO NGÀY. Chuyến đã đi giữ nguyên tỷ lệ của ngày nó
    # khởi hành, nên đổi chính sách hôm nay không làm đổi lợi nhuận của những tờ quyết toán đã ký.
    #
    # Tỷ lệ 0,90 đến từ việc đo bốn mẫu quyết toán thật – con số 0,75 chốt hôm 10/9 không mẫu nào
    # đang theo:
    #     SIN/MAL   10.340.000 / 11.490.000 = 89,99%
    #     UK        46.905.000 / 52.900.000 = 88,67%
    #     Nha Trang  1.500.000 /  1.790.000 = 83,80%
    ("tuoi_em_be", "2", "Dưới tuổi này là em bé – tính theo tỷ lệ bậc em bé", "tuổi", "Chủ tịch chốt 10/9/2026"),
    ("tuoi_tre_em", "12", "Dưới tuổi này là trẻ em – tính theo tỷ lệ giá người lớn", "tuổi", "Chủ tịch chốt 10/9/2026"),
    # TỶ LỆ TÁCH THEO HÌNH THỨC TOUR – Chủ tịch chốt 11/9/2026.
    #
    # Một tỷ lệ chung cho cả hai loại là sai về nghiệp vụ, không chỉ sai về con số: tour nước ngoài
    # có vé máy bay quốc tế, visa và bảo hiểm mà trẻ nhỏ vẫn phải trả gần bằng người lớn, nên hạ sâu
    # là lỗ ngay. Tour trong nước thì phần lớn chi phí là ghế xe và suất ăn – hạ sâu vẫn còn biên.
    ("ty_le_tre_em_trong_nuoc", "0.80", "Giá trẻ em (dưới 12) bằng tỷ lệ này của giá người lớn – tour TRONG NƯỚC", "tỷ lệ", "Chủ tịch chốt 11/9/2026"),
    ("ty_le_tre_em_nuoc_ngoai", "0.90", "Giá trẻ em (dưới 12) bằng tỷ lệ này của giá người lớn – tour NƯỚC NGOÀI", "tỷ lệ", "Chủ tịch chốt 11/9/2026"),
    # Em bé (dưới 2 tuổi) KHÔNG còn miễn phí. Chủ tịch sửa 11/9/2026: 30% giá người lớn.
    #
    # Bản chốt 10/9 ghi "dưới 2 tuổi miễn phí", và mẫu quyết toán Nha Trang cũng làm đúng như vậy –
    # hai cháu miễn phí thu 0 đồng nhưng vẫn gánh 5.000 đ bảo hiểm mỗi cháu, tức mỗi cháu lỗ 5.000.
    # Với 30% thì chính hai cháu ấy thu 537.000 đ mỗi cháu.
    #
    # Để 0 ở tham số này là quay lại quy tắc miễn phí – đó là một lựa chọn chính sách hợp lệ, không
    # phải lỗi, nên mã KHÔNG chặn giá trị 0.
    ("ty_le_em_be_trong_nuoc", "0.10", "Giá em bé (dưới 2) bằng tỷ lệ này của giá người lớn – tour TRONG NƯỚC (0 = miễn phí)", "tỷ lệ", "Chủ tịch chốt 11/9/2026"),
    ("ty_le_em_be_nuoc_ngoai", "0.30", "Giá em bé (dưới 2) bằng tỷ lệ này của giá người lớn – tour NƯỚC NGOÀI (0 = miễn phí)", "tỷ lệ", "Chủ tịch chốt 11/9/2026"),
    # Marketing & CSKH Đợt 3–5. Bốn con số Ban TGĐ phải chốt (đề xuất 07/9/2026) nằm ở đây chứ KHÔNG viết
    # cứng trong mã: đổi chính sách thì sửa tham số, ký duyệt theo quy trình đã có, không phải sửa phần mềm
    # rồi triển khai lại. Giá trị dưới đây là ĐỀ XUẤT, còn hiệu lực cho tới khi Ban TGĐ ký con số khác.
    ("cham_soc_han_ngay", "3", "Hạn liên hệ chăm sóc khách sau khi tour kết thúc", "ngày", "MKT/CSKH đề xuất 07/9/2026 – chờ Ban TGĐ chốt"),
    ("cham_soc_hai_long_mo_kn", "3", "Điểm hài lòng DƯỚI mức này thì tự mở hồ sơ khiếu nại", "điểm (1–5)", "MKT/CSKH đề xuất 07/9/2026"),
    ("khao_sat_han_ngay", "14", "Mã khảo sát khách tự chấm sống bao nhiêu ngày. Đủ dài để khách đi công tác về vẫn chấm được, đủ ngắn để không thành một cửa mở mãi", "ngày", "Đề xuất tự động hoá CSKH 25/9/2026"),
    ("khao_sat_gio_gui", "9", "Giờ trong ngày gửi tin xin đánh giá. Tin chăm sóc đến lúc 2 giờ sáng làm hỏng đúng thiện chí mà nó đi xin", "giờ (0–23)", "Đề xuất tự động hoá CSKH 25/9/2026, bước 1"),
    ("khao_sat_nhac_gio", "48", "Không trả lời sau bao nhiêu giờ thì nhắc MỘT lần. Một lần, và không gọi điện — đề xuất 25/9/2026 bước 6", "giờ", "Đề xuất tự động hoá CSKH 25/9/2026, bước 6"),
    ("cham_soc_goi_lai_gio", "24", "Hạn gọi lại khách chấm điểm thấp, tính từ lúc khách chấm. Đây là hạn của MỘT VIỆC CÓ CHỦ (cảnh báo mang tên người), không phải hạn của một thông báo", "giờ", "Đề xuất tự động hoá CSKH 25/9/2026, bước 4"),
    ("cham_soc_lui_ngay", "30", "Chỉ sinh phiếu chăm sóc cho tour kết thúc trong khoảng lùi này (chặn việc mở phiếu cho toàn bộ lịch sử chuyến đã đóng)", "ngày", "MKT/CSKH Đợt 4"),
    # KS-4 (11/9/2026) – hai mốc của vòng đời cảnh báo. Chủ tịch chốt 30 ngày / 48 giờ.
    #
    # KHÔNG khai `ngay_van_hanh_that` ở đây. Tham số ấy đã có sẵn phía dưới, CỐ Ý để trống chờ hai
    # chữ ký; thêm một dòng thứ hai điền sẵn "2026-12-01" là ký thay Chủ tịch bằng một dòng mã, và
    # hai dòng cùng tên thì không ai biết dòng nào đang có hiệu lực. KS-4 ĐỌC mốc ấy qua
    # moi_truong_du_lieu.moc_van_hanh_that(); chưa ký thì đọc ra None và cảnh báo để nguồn TRỐNG.
    ("canh_bao_lui_ngay", "30", "Chỉ sinh cảnh báo cho sự kiện trong khoảng lùi này. Không có mốc này thì mỗi lượt quét là một lượt quét lại toàn bộ lịch sử – đúng cơ chế đã đẻ ra 851 dòng quá hạn quyết toán", "ngày", "Chủ tịch chốt 11/9/2026, bằng cham_soc_lui_ngay"),
    # GIỮ 48, KHÔNG đổi theo `han_giu_cho_gio`. Lời khai cũ nói "bằng han_giu_cho_gio" — từ
    # 25/9/2026 hai con số TÁCH NHAU, nên lời khai ấy sửa lại cho đúng. Hai thứ khác nhau: một
    # cái là hạn giữ một CHỖ NGỒI (ghế không bán cho người khác — càng ngắn càng tốt), cái kia
    # là hạn xử lý một CẢNH BÁO (người phải đọc và làm — 4 giờ thì mọi cảnh báo tạo sau giờ
    # chiều đều trễ ngay sáng hôm sau, và một bảng đỏ toàn bộ thì không còn chỉ được chỗ nào gấp).
    ("canh_bao_han_mac_dinh_gio", "48", "Hạn xử lý mặc định cho loại cảnh báo chưa khai hạn riêng. Không có hạn thì không có gì trễ", "giờ", "Chủ tịch chốt 11/9/2026; tách khỏi han_giu_cho_gio ngày 25/9/2026"),
    # Hạn RIÊNG của dòng tiền, cố ý ngắn hơn hạn mặc định 48 giờ ở trên: một dòng tiền thiếu nguồn
    # làm sai cả bảng bốn mốc, và bảng ấy là thứ Chủ tịch nhìn để quyết định chi tiền. Hạn đếm từ
    # lúc LƯỢT QUÉT phát hiện, không phải từ lúc mở trang – xem services/han_dong_tien.py điều 1.
    ("dong_tien_han_xu_ly_gio", "24", "Hạn xử lý cho dòng dòng tiền chưa đủ nguồn, tính từ lúc lượt quét phát hiện", "giờ", "Chủ tịch chốt 14/9/2026"),
    # HẠN XỬ LÝ MỘT LEAD — P.TGĐ Phan Ngọc Tuấn chốt 18/9/2026.
    #
    # Khai ở ĐÂY chứ không viết cứng số 24 trong services/leads.py, vì hai lẽ:
    #   · Bảng này là chỗ DUY NHẤT của kho ghi một con số luật kèm NGƯỜI KÝ và NGÀY KÝ (cột cuối).
    #     Một con số luật nằm trong mã thì sáu tháng nữa không ai biết ai đặt ra nó.
    #   · Bảng này đã có cửa nhập sẵn (màn hình Tham số), nên đổi hạn là một lần duyệt tham số, không
    #     phải một lần đẩy mã. Đúng ranh giới 09/9: mỗi con số phải có một cửa cho người dùng.
    #
    # ĐẾM TỪ `received_at` — lúc lead VÀO SỔ, không phải lúc ai đó mở màn hình. Cùng cách đếm với
    # dong_tien_han_xu_ly_gio ở trên (đếm từ lúc lượt quét phát hiện): mốc phải là một sự kiện có
    # thật trong sổ, không phải hành vi xem.
    #
    # KHÔNG trừ ngày nghỉ, không quy ra giờ hành chính. P.TGĐ nói 24 giờ thì là 24 giờ đồng hồ; bịa
    # thêm luật giờ làm việc là tự ký thay một điều không ai ký.
    # ---- Sổ hoạt động PR · Chủ tịch chốt 18/9/2026 ----
    #
    # HAI GIỜ, THEO ĐỒNG HỒ THẬT. Không trừ ngày nghỉ, không quy ra giờ hành chính: một việc ghi
    # vào sổ lúc 22h thứ Bảy thì 0h là quá hạn. Đó là bản chất của khủng hoảng truyền thông, và
    # cũng đúng cách hạn xử lý lead 24 giờ đang chạy. Bịa thêm một luật giờ làm việc ở đây là tự
    # ký thay một điều không ai ký.
    #
    # MỐC ĐẾM LÀ LÚC VÀO SỔ, không phải lúc việc xảy ra ngoài đời — xem services/pr_hoat_dong.
    ("pr_khung_hoang_gio", "2",
     "Hạn phản hồi chính thức cho một vụ khủng hoảng truyền thông, kể từ lúc việc được GHI VÀO SỔ",
     "giờ", "Chủ tịch chốt 18/9/2026"),
    # BẢN GHI CHỮ KÝ, không phải hàng rào. Hàng rào thật là `require_roles` ở đường phát ngôn —
    # bảng phân quyền toàn hệ chỉ đếm được quyền khai ở đó. Tham số này giữ thứ `require_roles`
    # không mang được: ai chốt, ngày nào. Một phép thử chốt hai chỗ không được lệch nhau.
    ("pr_vai_phat_ngon", "ptgd_mkt",
     "Vai trò được bấm PHÁT trên sổ hoạt động PR – người chịu trách nhiệm cho câu nói ra ngoài",
     "vai trò", "Chủ tịch chốt 18/9/2026"),
    # ---- Cửa lọc tin khủng hoảng · 19/9/2026 ----
    #
    # BỐN THAM SỐ NÀY ĐIỀU KHIỂN MỘT CÁI XẾP HÀNG, KHÔNG ĐIỀU KHIỂN MỘT QUYẾT ĐỊNH. Không tham số
    # nào trong đây đặt `la_khung_hoang` hay bấm đồng hồ hai giờ; cả bốn chỉ quyết tin nào được đọc
    # trước. Sửa sai một tham số ở đây làm người trực đọc thừa hoặc đọc muộn, không làm hệ thống tự
    # tuyên bố một vụ khủng hoảng — xem services/loc_khung_hoang.
    #
    # DANH SÁCH TỪ ĐỎ để ở tham số chứ không viết cứng, vì nó là thứ SẼ SAI và phải sửa được trong
    # ngày: mỗi vụ đi qua lại dạy cho công ty một từ mới. Viết trong mã thì sửa nó là một bản nâng
    # cấp; để ở đây thì Marketing tự sửa và người sửa có tên.
    # So khớp KHÔNG dấu và theo RANH GIỚI TỪ (loc_khung_hoang.tim_tu_do), nên viết có dấu hay không
    # đều được — "lừa đảo" và "lua dao" là một.
    ("pr_tu_do",
     "lua dao,lua gat,bip,to cao,khieu nai,kien,luat su,cong an,bao chi,nha bao,quyt,bung tien,"
     "doi tien,hoan tien,tra tien,ngo doc,tai nan,bo roi,mat do,to,phot,scandal,tay chay",
     "Những từ làm một tin được xếp lên đầu hàng đợi Marketing. Sửa được ở màn hình này, không "
     "phải bằng bản nâng cấp – mỗi vụ đi qua lại dạy thêm một từ",
     "từ, cách nhau bằng dấu phẩy", "Marketing đề xuất – Chủ tịch chốt 19/9/2026"),
    # NGƯỠNG 2 nghĩa là: một từ đỏ (+2) đủ vào hàng đợi, hoặc dốc (+1) cộng quá hạn trả lời (+1)
    # cũng đủ. Hạ xuống 1 thì mọi tin của một hội thoại đang dốc đều vào — dùng được khi muốn xem
    # lại, nhưng để thường trực thì hàng đợi dài đến mức không ai mở.
    ("pr_nguong_canh_bao", "2",
     "Điểm tối thiểu để một tin vào hàng đợi Marketing. Dưới ngưỡng là XẾP SAU, không phải bị bỏ – "
     "màn hình hạ ngưỡng xuống là xem lại được",
     "điểm", "Chủ tịch chốt 19/9/2026"),
    # DỐC: đếm theo HỘI THOẠI, không theo cả hộp thư. Cả hộp thư đông lên vào chủ nhật là chuyện
    # bình thường của một công ty lữ hành; một người nhắn sáu tin trong một giờ thì không.
    ("pr_cum_phut", "60",
     "Cửa sổ đếm 'dốc': bao nhiêu phút gần nhất được tính là một cụm tin trên cùng một hội thoại",
     "phút", "Chủ tịch chốt 19/9/2026"),
    ("pr_cum_so_tin", "5",
     "Bao nhiêu tin của khách trong cửa sổ ấy thì tính là một 'dốc' và cộng điểm",
     "tin", "Chủ tịch chốt 19/9/2026"),
    # ---- Báo động khủng hoảng: phút 0 và phút 15 · Chủ tịch chốt 19/9/2026 ----
    #
    # HAI NGƯỠNG chứ không một. Trên `pr_nguong_canh_bao` thì vào hàng chờ người đọc; trên ngưỡng
    # ĐỎ dưới đây, hoặc gặp DỐC, thì reo chuông NGAY kể cả 2 giờ sáng. Một ngưỡng thì phải chọn
    # giữa hai cái hỏng: reo cho mọi tin thì vài đêm sau người ta tắt chuông, còn chỉ reo khi có
    # người tích tay thì ban đêm chuông không bao giờ reo — mà ban đêm chính là lúc không có người
    # trực Marketing để tích.
    ("pr_nguong_bao_dong", "4",
     "Từ bao nhiêu điểm thì máy TỰ reo chuông cho lãnh đạo, không chờ ai đọc hàng đợi",
     "điểm", "Chủ tịch chốt 19/9/2026"),
    # Phút 0 báo Chủ tịch. Hết số phút này mà CHƯA AI bấm 'đã nhận' thì báo tiếp TGĐ và P.TGĐ
    # Marketing — không phải để chia quyền quyết, mà để một người trực có người đỡ phía sau.
    ("pr_phut_leo_thang", "15",
     "Chưa ai bấm 'đã nhận' sau bao nhiêu phút thì báo tiếp TGĐ và P.TGĐ Marketing",
     "phút", "Chủ tịch chốt 19/9/2026"),
    # Kênh là THAM SỐ chứ không viết cứng trong mã: bật thêm một kênh là một cái gạt, không phải
    # một vòng dựng lại. 'chuong' luôn nên có mặt (nó rẻ và là dấu vết trong VTOS); ba kênh còn
    # lại — zalo_oa, zns, email — là ba kênh làm ĐIỆN THOẠI kêu.
    ("pr_kenh_bao_dong", "chuong,zns,email",
     "Kênh gửi báo động, cách nhau bằng dấu phẩy: chuong, zalo_oa, zns, email",
     "kênh", "Chủ tịch chốt 19/9/2026"),
    # ---- Sổ tài sản thương hiệu · Chủ tịch chốt 18/9/2026 ----
    #
    # GIÁ TRỊ LÀ DANH SÁCH VAI TRÒ, không phải một con số, và cố ý để ở đây chứ không viết cứng
    # trong mã: "ai được ký một bộ nhận diện mới" là một quyết định quản trị, và ngày nó đổi thì
    # phải đổi bằng một dòng ở màn hình Tham số kèm tên người đổi — không phải bằng một bản nâng
    # cấp mà sáu tháng sau không ai tra được ai đã quyết.
    #
    # Mã đọc SỐNG từ đây (tai_san_thuong_hieu.VAI_KY đối chiếu với tham số này), nên thêm một vai
    # vào đây là thêm một ô chữ ký trên màn hình, không phải thêm một dòng mã.
    ("thuong_hieu_vai_ky", "chutich,ptgd_mkt",
     "Những vai trò phải ký thì một bộ nhận diện mới mới có hiệu lực. ĐỦ CẢ hai, không phải một trong hai",
     "danh sách vai trò", "Chủ tịch chốt 18/9/2026"),
    ("lead_han_xu_ly_gio", "24", "Hạn xử lý một lead kể từ khi vào sổ. Quá hạn mà chưa ai liên hệ và trạng thái vẫn là Mới thì lead bị đánh dấu quá hạn", "giờ", "P.TGĐ Phan Ngọc Tuấn chốt 18/9/2026"),
    ("kn_han_muc1_gio", "72", "Hạn phản hồi khách – khiếu nại mức 1 (góp ý)", "giờ", "MKT/CSKH đề xuất 07/9/2026 – chờ Ban TGĐ chốt"),
    ("kn_han_muc2_gio", "24", "Hạn phản hồi khách – khiếu nại mức 2 (có thiệt hại)", "giờ", "MKT/CSKH đề xuất 07/9/2026 – chờ Ban TGĐ chốt"),
    ("kn_han_muc3_gio", "4", "Hạn phản hồi khách – khiếu nại mức 3 (nghiêm trọng)", "giờ", "MKT/CSKH đề xuất 07/9/2026 – chờ Ban TGĐ chốt"),
    # Ngưỡng tiền bồi thường KHÔNG có tham số riêng: hoàn tiền đi qua Đề nghị chi nhóm "hoan_tien" và dùng
    # đúng ngưỡng hai chữ ký hiện hành. Đặt ngưỡng riêng ở đây là tạo đường tiền thứ hai.
    # V7 Đợt 3 – sự cố tour. Ba con số này đi NGƯỢC chiều với hạn khiếu nại ở trên: mức càng nặng hạn
    # càng NGẮN, vì khách đang đứng ngoài đường chứ không ngồi nhà chờ thư trả lời. Hạn tính từ LÚC XẢY
    # RA chứ không phải lúc ghi vào hệ thống – báo muộn ba tiếng không được tự dời hạn thêm ba tiếng.
    ("sc_han_muc1_gio", "24", "Hạn có người nhận xử lý – sự cố tour mức 1 (xử lý tại chỗ)", "giờ", "Điều hành/V7 đề xuất 10/9/2026 – chờ Ban TGĐ chốt"),
    ("sc_han_muc2_gio", "8", "Hạn có người nhận xử lý – sự cố tour mức 2 (đổi lịch trình hoặc phát sinh chi phí)", "giờ", "Điều hành/V7 đề xuất 10/9/2026 – chờ Ban TGĐ chốt"),
    ("sc_han_muc3_gio", "2", "Hạn có người nhận xử lý – sự cố tour mức 3 (mất chuyến, tai nạn, an ninh)", "giờ", "Điều hành/V7 đề xuất 10/9/2026 – chờ Ban TGĐ chốt"),
    # Lệnh Robot Kiểm soát 08/9/2026.
    ("ky_thuat_cham_ms", "5000", "Đường dẫn chạy quá số mili giây này thì ghi sự kiện “chậm bất thường”", "mili giây", "Lệnh Kiểm soát K6"),
    ("han_nhap_lieu_ngay", "5", "Ngày hàng tháng mà số liệu tháng trước coi như đã nhập đủ (mốc đo trễ để chấm điểm phòng ban)", "ngày trong tháng sau", "Chủ tịch chốt 08/9/2026"),
    # K3 – hậu kiểm số nhập tay. Bảy ngưỡng, tất cả ở đây chứ không viết cứng: đặt chặt quá thì mỗi
    # ngày hàng trăm dòng và không ai đọc, lỏng quá thì bỏ lọt. Dùng GET /kiem-soat/nhap-tay/do-nguong
    # để xem trước mỗi ngưỡng ra bao nhiêu dòng rồi hãy chốt.
    ("ks_lech_lan", "3", "Lệch quá bao nhiêu LẦN so với chính chỉ tiêu đó kỳ trước thì mở ngoại lệ", "lần", "Lệnh Kiểm soát K3 – đề xuất, chờ chốt sau một tháng chạy thật"),
    ("ks_lech_toi_thieu", "20000000", "Lệch nhiều lần nhưng số tiền chênh dưới mức này thì bỏ qua", "đồng", "Lệnh Kiểm soát K3"),
    ("ks_tron_tu", "10000000", "Số tròn triệu từ mức này trở lên mới coi là khoản lớn đáng ngờ", "đồng", "Lệnh Kiểm soát K3"),
    ("ks_tron_lap", "3", "Cùng một người nhập cùng một số tròn bao nhiêu lần thì mở ngoại lệ", "lần", "Lệnh Kiểm soát K3"),
    ("ks_gio_bat_dau", "7", "Giờ bắt đầu ngày làm việc – nhập trước giờ này là ngoài giờ", "giờ", "Lệnh Kiểm soát K3"),
    ("ks_gio_ket_thuc", "21", "Giờ kết thúc ngày làm việc – nhập từ giờ này trở đi là ngoài giờ", "giờ", "Lệnh Kiểm soát K3"),
    ("ks_don_dong", "10", "Bao nhiêu dòng trong 5 phút thì coi là nhập dồn", "dòng", "Lệnh Kiểm soát K3"),
    ("nd_vai_tro_ky_2", "tgd,chutich,hanh_chinh", "Vai trò được ký chữ ký thứ hai cho nội dung có cam kết với khách hoặc có số liệu tài chính (hanh_chinh gồm pháp chế)", "danh sách vai trò", "MKT Đợt 5 – chờ Ban TGĐ chốt"),
    ("coc_mac_dinh_pct", "30", "Tỷ lệ cọc mặc định khi sản phẩm không quy định", "%", "Vận hành Vietrip"),
    ("han_coc_gio", "24", "Hạn khách đặt cọc sau khi tạo booking (quá → cảnh báo sale/ĐH)", "giờ", "Vận hành Vietrip"),
    ("han_huy_cho_ngay", "3", "Deadline hủy chỗ / thu đủ trước khởi hành (đóng tour, khóa booking)", "ngày", "Vận hành Vietrip"),
    ("bao_luu_han_ngay", "90", "Hạn hiệu lực tiền bảo lưu (cảnh báo trước 7 ngày)", "ngày", "Vận hành Vietrip"),
    ("sla_tra_loi_chat_phut", "5", "Sale phải trả lời tin nhắn khách (Facebook/Zalo/web) trong giờ làm việc; quá → AI trả lời thay", "phút", "MKT/KD – hộp thư đa kênh"),
    ("sla_tra_loi_ngoai_gio_phut", "15", "Ngoài giờ làm việc (trước 8h, sau 21h): AI trả lời thay sau", "phút", "MKT/KD – hộp thư đa kênh"),
    ("ai_tra_loi_bat", "1", "Bật robot AI trả lời thay khi sale trễ (1 bật / 0 tắt)", "cờ", "MKT/KD – hộp thư đa kênh"),
    ("quy_dh_le_noi_dia", "0.02", "Quỹ thưởng Điều hành – tour lẻ nội địa", "tỷ lệ LN", "ĐH Điều 5"),
    ("quy_dh_le_nuoc_ngoai", "0.01", "Quỹ thưởng Điều hành – tour lẻ nước ngoài", "tỷ lệ LN", "ĐH Điều 5"),
    ("quy_dh_doan", "0.01", "Quỹ thưởng Điều hành – tour đoàn (không phụ thuộc biên)", "tỷ lệ LN", "ĐH Điều 5; ĐC Điều 7"),
    ("quy_dh_chia_nv", "0.70", "Phần nhân viên trong quỹ Điều hành (Trưởng phòng 30%)", "tỷ lệ", "ĐH Điều 6"),
    ("hh_doan_ty_le", "0.10", "Hoa hồng NV kinh doanh đoàn trên phần LN vượt mốc", "tỷ lệ", "Đoàn Điều 7"),
    ("hh_doan_moc", "20000000", "Mốc LN đoàn/tháng bắt đầu tính hoa hồng", "đồng", "Đoàn Điều 7"),
    ("ptgd_doan_ty_le", "0.05", "PTGĐ tour đoàn – tỷ lệ LN sau quyết toán", "tỷ lệ", "TP Đoàn"),
    ("sale_admin_ty_le", "0.02", "Sale Admin – tỷ lệ LN sau quyết toán", "tỷ lệ", "TP Đoàn"),
    ("visa_tu_xu_ly", "200000", "Đơn giá visa – hồ sơ tự xử lý", "đồng/hồ sơ", "ĐH Điều 7"),
    ("visa_gui_doi_tac", "50000", "Đơn giá visa – gửi đối tác", "đồng/hồ sơ", "ĐH Điều 7"),
    ("moc_chi_tieu_hcm", "200000000", "Mốc chỉ tiêu doanh thu NV kinh doanh lẻ HCM", "đồng/tháng", "KD Lẻ"),
    ("moc_chi_tieu_cantho", "120000000", "Mốc chỉ tiêu doanh thu NV Cần Thơ và văn phòng tỉnh (Bình Dương khách lẻ dùng mốc HCM)", "đồng/tháng", "KD Lẻ Phụ lục B.2"),
    ("thang_f_bang", "65:0,70:0,90:0,100:0,110:0.5,130:0.8,160:1.1,200:1.4,250:1.7,300:2,350:2.3,400:2.6,450:2.9,500:3.2,550:3.5,600:3.8,700:4.1,800:4.4,900:4.7,1000:5",
     "Bảng B.1 thang f: 'ngưỡng % mốc:hệ số %' từ f1 đến f19 và trần 1000%; f0 dưới ngưỡng đầu; ngưỡng tiền = % × mốc văn phòng", "bảng", "KD Lẻ Phụ lục A, B.1"),
    ("ca_truc_phut", "5", "Thời gian trả lời khách trong ca trực page", "phút", "KD Lẻ Điều 2a"),
    ("tai_xe_cong_tac_phi", "200000", "Công tác phí tài xế mỗi ngày tour", "đồng/ngày", "Đội xe"),
    # ---- Đội xe Vietrip Đợt 2. Đặc tả nói thẳng: "Toàn bộ số dưới đây phải nằm trong bảng cấu hình có giao
    # diện sửa, kèm lịch sử thay đổi. Lập trình viên không được viết thẳng vào mã." Dùng luôn bảng tham số
    # chính sách sẵn có thay vì dựng bảng cấu hình thứ hai: nó đã có hiệu lực theo ngày, có lịch sử và có
    # chữ ký duyệt – mà mấy con số này là tiền, nên đi qua cửa ký là đúng chứ không phải phiền.
    # Công tác phí tài xế dùng lại khóa tai_xe_cong_tac_phi ở trên (200.000 đ/ngày, khớp giá trị đã xác nhận).
    ("xe_chu_ky_bao_duong_km", "9000", "Chu kỳ bảo dưỡng xe (mốc chung; xe có mốc riêng thì ghi ở hồ sơ xe)", "km", "Đội xe v1.3 – A1, A5"),
    ("xe_bd_gap_km", "2000", "Còn dưới mốc này tới kỳ bảo dưỡng thì báo GẤP", "km", "Đội xe v1.3 – A5"),
    ("xe_bd_theo_doi_km", "5000", "Còn dưới mốc này thì đưa vào diện theo dõi bảo dưỡng", "km", "Đội xe v1.3 – A5"),
    ("xe_giay_to_vang_ngay", "30", "Giấy tờ xe/GPLX còn dưới số ngày này thì cảnh báo vàng", "ngày", "Đội xe v1.3 – A5"),
    ("xe_giay_to_do_ngay", "7", "Giấy tờ còn dưới số ngày này (hoặc đã quá hạn) thì cảnh báo đỏ", "ngày", "Đội xe v1.3 – A5"),
    ("xe_luong_khoan_hop_tac_thang", "7000000", "Lương khoán tài xế xe hợp tác", "đồng/xe/tháng", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_phi_bai_dau_thang", "2000000", "Phí bãi đậu xe (chưa VAT)", "đồng/xe/tháng", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_bai_dau_vat", "0.08", "Thuế suất VAT phí bãi đậu xe", "tỷ lệ", "Đội xe v1.3 – A6, chốt 07/9/2026"),
    ("xe_tieu_hao_min", "2.5", "Cận dưới dải tiêu hao nhiên liệu hợp lý", "km/lít", "Đội xe v1.3 – A2"),
    ("xe_tieu_hao_max", "4.5", "Cận trên dải tiêu hao nhiên liệu hợp lý", "km/lít", "Đội xe v1.3 – A2"),
    ("xe_lech_dau_vang", "0.10", "Định mức dầu đ/km lệch quá mức này so với trung bình 6 tháng của CHÍNH xe đó → vàng", "tỷ lệ", "Đội xe v1.3 – A3"),
    ("xe_lech_dau_do", "0.20", "Lệch quá mức này → đỏ", "tỷ lệ", "Đội xe v1.3 – A3"),
    ("xe_lech_km_gps", "0.05", "Km đọc từ ảnh lệch km GPS quá mức này → đỏ", "tỷ lệ", "Đội xe v1.3 – A2"),
    ("xe_lech_km_noi_chuyen", "50", "Km cuối chuyến trước lệch km đầu chuyến sau quá mức này → vàng (nghi có chuyến chưa khai)", "km", "Đội xe v1.3 – A2"),
    ("xe_vay_dao_han_ngay", "60", "Cảnh báo trước ngày đáo hạn khế ước", "ngày", "Đội xe v1.3 – A8"),
    ("xe_vay_tra_goc_ngay", "10", "Cảnh báo trước kỳ trả gốc", "ngày", "Đội xe v1.3 – A8"),
    ("xe_chung_tu_bat_buoc_tu", "10000000", "Khoản chi từ mức này bắt buộc có chứng từ gốc đính kèm", "đồng", "Đội xe v1.3 – B6"),
    ("xe_chenh_gia_ban_vang", "0.20", "Giá chào bán thấp hơn định giá nội bộ quá mức này → cờ vàng bắt buộc giải trình", "tỷ lệ", "Đội xe v1.3 – A9"),
    # Chỉ đạo Chủ tịch 07/9/2026: GĐ điều hành đội xe là người DUY NHẤT được tạo và chốt lệnh điều xe.
    # Ghi bằng tài khoản/mã nhân viên trong tham số chứ KHÔNG viết tên một người vào mã nguồn – thay người
    # phụ trách thì sửa tham số, không phải sửa phần mềm và triển khai lại. Nhận nhiều giá trị, ngăn bởi dấu
    # phẩy; để trống là giữ nguyên quy tắc theo vai trò như trước.
    ("xe_sua_chua_ben_chiu", "vietourist_tam_ung", "Sửa chữa/bảo dưỡng mặc định bên nào chịu",
     "vietourist_tam_ung hoặc chu_xe", "Chủ tịch chốt lại cuối ngày 07/9/2026 – giữ cách chi hộ đang làm"),
    ("xe_ky_quyet_toan_ap_dung_tu", "2026-09", "Kỳ đầu tiên áp dụng cách cắt kỳ theo tháng dương lịch; kỳ "
     "trước mốc này đã quyết toán xong theo cách cũ nên máy không dựng lại", "YYYY-MM", "Chủ tịch 07/9/2026"),
    ("xe_nguoi_lap_lenh", "53","Tài khoản (hoặc mã nhân viên) được tạo và chốt lệnh điều xe – để trống là theo vai trò", "danh sách", "Chủ tịch 07/9/2026"),

    # ── Chủ hồ sơ quyết toán mảng Đoàn · Chủ tịch quyết 25/9/2026, câu 4 ─────────────────────
    #
    # GIÁ TRỊ ĐỂ TRỐNG, VÀ ĐÓ LÀ MẶC ĐỊNH ĐÚNG. Trống = mọi chuyến vẫn theo luật cũ (người điều
    # hành chuyến soạn quyết toán). Phòng Đoàn khai tài khoản Sale Admin vào đây thì từ lúc ấy
    # mọi tour ĐOÀN chưa ai chạm vào sẽ thuộc về chị ấy.
    #
    # ĐÚNG MỘT TÀI KHOẢN. Khác `xe_nguoi_lap_lenh` ở trên — ô ấy nhận một danh sách, ô này thì
    # không: "một chủ hồ sơ" mà khai hai người là một câu hỏi cấu hình chưa trả lời xong, và
    # `chu_ho_so.nguoi_giu_ho_so_doan` từ chối đoán hộ thay vì lấy bừa người đầu danh sách.
    #
    # ĐỔI Ô NÀY LÀ CHUYỂN CHỦ HÀNG TRĂM CHUYẾN CÙNG LÚC — nhưng chỉ những chuyến CHƯA AI GHI dòng
    # quyết toán nào. Hồ sơ vừa có dòng đầu tiên là tên người ghi được đóng cứng vào
    # `tours.chu_ho_so_id`, và từ đó tham số này không với tới nữa.
    # ── Thang bậc đòi nợ khách · Chủ tịch quyết 25/9/2026, câu 5 ───────────────────────────────
    #
    # Chủ tịch chỉ định AI chịu ở từng bậc; hai con số NGÀY dưới đây là phần hệ thống phải có để
    # câu ấy chạy được, và chúng là ĐỀ XUẤT — 3 ngày lên cấp trên trực tiếp, 7 ngày lên lãnh đạo
    # khối. Cả hai sửa ở màn hình Chính sách, không phải sửa mã.
    #
    # ĐẾM TỪ HẠN HỦY CHỖ (`booking.cancel_deadline`), không phải từ ngày khởi hành: hạn hủy chỗ là
    # mốc đã ký với khách, còn ngày khởi hành thì tiền lẽ ra phải thu xong từ trước đó.
    ("no_khach_bac2_ngay", "3", "Quá hạn thu tiền bao nhiêu ngày thì chuyển cấp trên trực tiếp "
     "(Đoàn: Sale Admin · Lẻ: TP Kinh doanh)", "ngày", "Chủ tịch quyết 25/9/2026, câu 5"),
    ("no_khach_bac3_ngay", "7", "Quá hạn thu tiền bao nhiêu ngày thì chuyển lãnh đạo khối "
     "(Đoàn: Phó TGĐ Đoàn · Lẻ: Giám đốc Kinh doanh)", "ngày", "Chủ tịch quyết 25/9/2026, câu 5"),

    ("chu_ho_so_doan", "", "Tài khoản (hoặc mã nhân viên) giữ hồ sơ quyết toán của mọi tour mảng Đoàn – "
     "để trống là người điều hành chuyến soạn như cũ. Đúng MỘT người.", "tài khoản",
     "Chủ tịch quyết 25/9/2026, câu 4"),
    # Hạn TRẢ LỜI của lời chào chuyến, không phải hạn tuân thủ của hướng dẫn viên: hết hạn thì lời chào
    # hết hiệu lực và chuyến được chào cho người khác. Toàn bộ HDV là cộng tác viên (07/9/2026), nên một
    # mốc thời gian mang nghĩa "bắt buộc phải trả lời" là dấu hiệu quản lý, điều hành – thứ mà luật nhìn
    # vào để xác định lại quan hệ lao động bất kể hợp đồng mang tên gì.
    ("hdv_han_tra_loi_gio", "24", "Lời chào chuyến hết hiệu lực sau bao nhiêu giờ", "giờ",
     "Chính sách Phòng Hướng dẫn"),
    ("moc_luong_doan", "30000000", "Mốc bình quân LN quyết toán 3 tháng để hưởng đủ lương NV kinh doanh đoàn", "đồng", "Đoàn Điều 5"),
    ("phat_su_vu", "1000000", "Chế tài mỗi sự vụ từ mức 2 (chỉ trừ hoa hồng)", "đồng/vụ", "KD Lẻ"),
    # Khoản trừ của NGƯỜI LAO ĐỘNG, áp từ kỳ lương 01/9/2026 (Bộ tính lương Vietourist, sheet Tham số).
    # BHXH tính trên MỨC LƯƠNG HỢP ĐỒNG (tiền lương làm căn cứ đóng), không tính trên mức lương của kỳ:
    # mức của kỳ thay đổi theo doanh thu, lấy nó làm căn cứ đóng là sai bản chất và sai cả số phải nộp.
    ("bhxh_nld", "0.105", "Bảo hiểm xã hội phần người lao động", "tỷ lệ trên lương hợp đồng", "Bộ tính lương 01/9/2026"),
    ("doan_phi_ty_le", "0.005", "Đoàn phí công đoàn – tỷ lệ trên tiền lương làm căn cứ đóng BHXH",
     "tỷ lệ", "Thỏa thuận khấu trừ đoàn phí: mức theo quy định Tổng LĐLĐ, tính trên tiền lương đóng BHXH bắt buộc"),
    ("visa_lien_minh", "300000", "Đơn giá hồ sơ visa khách liên minh", "đồng/hồ sơ", "ĐH Điều 7"),
    ("hdv_tncn", "0.10", "Khấu trừ TNCN thù lao HDV cộng tác viên", "tỷ lệ", "Bảng thuê ngoài 04-LĐTL"),
    ("gd_kd_thuong_50", "3000000", "Thưởng GĐ KD khi 50–85% NV đạt chỉ tiêu", "đồng", "Chính sách GĐ KD"),
    ("gd_kd_thuong_85", "6000000", "Thưởng GĐ KD khi ≥ 85% NV đạt chỉ tiêu", "đồng", "Chính sách GĐ KD"),
    ("so_du_tien_toi_thieu", "500000000", "Ngưỡng số dư tiền tối thiểu – cảnh báo dự báo dòng tiền 13 tuần", "đồng", "Thiết kế 3.4"),
    ("thue_gtgt", "0.10", "Thuế suất GTGT dịch vụ lữ hành (Kế toán chỉnh theo mức giảm thuế hiện hành)", "tỷ lệ", "Luật Thuế GTGT"),
    ("giam_tru_ban_than", "11000000", "Giảm trừ gia cảnh cho bản thân người nộp thuế TNCN (Kế toán chỉnh khi Nhà nước nâng mức)", "đồng/tháng", "NQ 954/2020/UBTVQH14"),
    ("giam_tru_nguoi_phu_thuoc", "4400000", "Giảm trừ gia cảnh cho mỗi người phụ thuộc (Kế toán chỉnh khi Nhà nước nâng mức)", "đồng/tháng/người", "NQ 954/2020/UBTVQH14"),
    # 48 → 4 ngày 25/9/2026, Chủ tịch quyết. Bản đề xuất Phòng Điều hành viết 4 giờ; anh Tuấn chốt 4.
    #
    # HỆ QUẢ PHẢI NÓI RA, vì nó xảy ra ngay đêm đầu tiên: hạn tính bằng GIỜ ĐỒNG HỒ, không phải
    # giờ làm việc (`giu_cho.han_mac_dinh` cộng thẳng timedelta). Nên booking tạo 16h30 chiều hết
    # hạn 20h30 tối cùng ngày, và robot trả chỗ về tour ngay trong đêm — sáng hôm sau ngân hàng
    # báo có thì chỗ đã mất.
    #
    # Cái làm cho điều đó KHÔNG thành mất khách: robot chỉ đụng booking CHƯA THU ĐỒNG NÀO
    # (`giu_cho.het_han_giu_cho`, luật 1), và booking VẪN CÒN — chỉ là không còn chiếm ghế.
    # Khách trả tiền muộn thì Điều hành bấm khôi phục nếu tour còn chỗ.
    #
    # Muốn đổi sang "4 giờ LÀM VIỆC" thì sửa `giu_cho.han_mac_dinh` cộng theo giờ hành chính,
    # không phải sửa con số này.
    ("han_giu_cho_gio", "4", "Giữ chỗ cho booking CHƯA thu đồng nào; quá hạn thì trả chỗ về tour (booking vẫn còn)", "giờ", "VPM-7 11/9/2026; Chủ tịch đổi 48 → 4 ngày 25/9/2026"),

    # ── CSKH 27/9/2026 · Ba tham số cho đường Zalo OA, một cho Google, một cho ngưỡng chuông ──
    # ZNS giữ mẫu bên Zalo và phải chờ duyệt; OA thì mình tự soạn cả câu, KHÔNG cần duyệt — nên
    # đây là đường duy nhất chạy thử được trong lúc mẫu ZNS còn đang đăng ký. Để TRỐNG mẫu là tắt
    # đường OA, tin rơi về ZNS như cũ.
    #
    # Câu chữ gửi khách là việc của Marketing. Viết cứng trong mã thì mỗi lần sửa một dấu phẩy
    # phải đẩy một vòng mã — cách chắc chắn để không ai sửa nữa.
    ("khao_sat_mau_tin", "Vietourist cam on anh/chi {ten_khach} da dong hanh cung chuyen {ten_tour}. Anh/chi danh 1 phut cham diem chuyen di, huong dan vien va tai xe giup Vietourist phuc vu tot hon: {link} (duong dan chi dung mot lan).", "Nội dung tin OA mời chấm điểm sau tour. Chỗ điền: ten_khach, ten_tour, link", "mẫu chữ", "27/9/2026"),
    ("khao_sat_mau_nhac", "Vietourist gui lai duong dan danh gia chuyen {ten_tour} toi anh/chi {ten_khach}: {link}. Day la lan nhac duy nhat, neu khong tien thi anh/chi bo qua giup.", "Nội dung tin OA nhắc một lần khi khách chưa trả lời", "mẫu chữ", "27/9/2026"),
    ("khao_sat_link_goc", "https://vtos.infinitytours.org", "Gốc đường dẫn trang khảo sát; trang khách mở là <gốc>/y-kien/<mã>", "đường dẫn", "27/9/2026"),

    # Chỉ hiện cho khách đã chấm 4–5 sao, ngay trên trang khảo sát sau khi họ bấm gửi. Để TRỐNG
    # thì màn hình không mời ai cả — đó là cách tắt bước này mà không phải sửa mã.
    ("link_danh_gia_google", "https://www.google.com/maps/place/TOURISM+CORPORATION+VIETOURIST/data=!4m2!3m1!1s0x31752f6a4ac8537d:0x99072d754b108707", "Đường dẫn hồ sơ Google của công ty, mời khách 4-5 sao viết đánh giá công khai", "đường dẫn", "anh Tuấn gửi 27/9/2026"),

    # Đo 27/9/2026: 200 lời mời chấm điểm do robot CSKH xếp lúc 20:45 ngày 26/9 nằm im hai ngày ở
    # trạng thái "chờ cấu hình" — khách không nhận gì, không ai được báo, và robot vẫn báo "đã xếp
    # N tin" mỗi lượt. Ngưỡng này là chỗ biến một hàng đợi dài thành một tiếng chuông.
    ("zalo_hang_doi_nguong", "20", "Bao nhiêu tin Zalo kẹt ở 'chờ cấu hình' thì robot CSKH reo cảnh báo", "tin", "27/9/2026 – sau khi đo bản đang chạy"),

    # ── PQ-4 · Hai mốc chuyển VTOS từ chạy thử sang vận hành thật ────────────────────────────
    # Thêm 11/9/2026. Trước hôm nay hai khóa này KHÔNG TỒN TẠI, và hệ quả không nhìn thấy được từ
    # màn hình: propose_param chặn mọi khóa chưa có dòng nào trong bảng, còn ô chọn tham số trên
    # màn hình Chính sách chỉ liệt kê 81 khóa đang có. Chủ tịch quyết hai mốc ngày 10/9 và tưởng đã
    # ký xong; đo ngày 11/9 thì trong bảng không có dòng nào. Không phải người quên ký – KHÔNG CÓ
    # CỬA ĐỂ KÝ. Đây đúng là kiểu thiếu mà quy ước "mỗi con số phải có một cửa nhập" nói tới.
    #
    # GIÁ TRỊ ĐỂ TRỐNG, và phải để trống. seed_params tạo dòng mặc định ở trạng thái active kèm hai
    # chữ ký sẵn – tiện cho bộ chính sách nền, nhưng ở đây mà điền sẵn "01-12-2026" thì hệ thống sẽ
    # tự đóng dấu VẬN HÀNH THẬT bằng một chữ ký không ai ký. Để trống thì moi_truong_du_lieu đọc ra
    # None, nghĩa là CHƯA CHỐT, và ngày tháng thật đi vào qua đúng cửa đề xuất – ký hai chữ ký.
    ("ngay_van_hanh_that", "", "Mốc VTOS chuyển sang vận hành thật – số do người nhập trong VTOS",
     "ngày (DD-MM-YYYY)", "Chủ tịch quyết 10/9/2026 – đề xuất 01-12-2026, chờ ký"),
    ("ngay_du_lieu_that_vietrip", "", "Mốc dữ liệu Vietrip đổ về hàng ngày được coi là dữ liệu thật",
     "ngày (DD-MM-YYYY)", "Chủ tịch quyết 10/9/2026 – đề xuất 01-10-2026, chờ ký"),
    # ---- Đ-2 · Thuế GTGT ở mức chuyến. Chủ tịch chốt 12/9/2026 ----
    #
    # "VAT đầu vào tương ứng với đầu ra. Nếu đầu vào không đủ thì sẽ phải đóng 8% VAT chênh lệch.
    #  Nên trừ vào lợi nhuận của tour."
    #
    # Để ở tham số chứ không viết cứng 0.08 trong mã vì thuế suất là chính sách NHÀ NƯỚC – nó đã đổi
    # (10% → 8%) và sẽ còn đổi. Tham số có hiệu lực theo ngày nên chuyến đã đi giữ nguyên thuế suất
    # của ngày nó khởi hành: đổi thuế suất hôm nay KHÔNG làm đổi lợi nhuận những tờ quyết toán đã ký.
    ("thue_suat_dau_ra", "0.08", "Thuế suất GTGT đầu ra áp cho doanh thu tour", "tỷ lệ",
     "Chủ tịch chốt 12/9/2026"),
    # Dòng "dịch vụ tiêu dùng ngoài Việt Nam" của hoá đơn tour nước ngoài. Chủ tịch chốt 14/9/2026:
    # tour nước ngoài tính 0%. Nhưng 0% ấy là MỘT CHÍNH SÁCH, nên nó nằm ở đây chứ không nằm trong
    # mã: chính sách đổi thì Kế toán ký lại tham số, không ai phải sửa và triển khai lại phần mềm.
    ("thue_suat_ngoai_vn", "0", "Thuế suất GTGT cho phần dịch vụ tiêu dùng ngoài Việt Nam", "tỷ lệ",
     "Chủ tịch chốt 14/9/2026"),
    # Giá bán niêm yết ĐÃ GỒM thuế GTGT hay chưa. Đây là một QUY ƯỚC, không phải phép tính, và hai
    # quy ước lệch nhau đúng 8% của chính phần chịu thuế – ở mọi chuyến, và không bao giờ tự lộ ra.
    #
    # Để 1 (đã gồm) vì đó là quy ước đang dùng trong chính tệp quyết toán của phòng Điều hành: đoàn
    # Hồ Tràm tính 3.790.000 / 1,08 để ra giá trước thuế.
    #
    # CHỦ TỊCH XÁC NHẬN 13/9/2026: giá bán niêm yết ĐÃ GỒM thuế GTGT. Giá trị không đổi – vẫn là 1 –
    # nhưng NGUỒN của nó đổi, và đó mới là điều đáng ghi. Trước hôm nay, số 1 này là máy đọc ngược ra
    # từ một tệp Excel: thấy phép chia cho 1,08 nên đoán giá đã gồm thuế. Một quy ước thuế suy ra từ
    # một phép chia trong một tệp mẫu thì đúng cho tệp ấy, không đúng cho công ty – và nếu sai thì
    # mọi chuyến lệch nhau đúng 8% của phần chịu thuế mà không bao giờ tự lộ ra (xem đoạn trên).
    # Nay đã có người chịu trách nhiệm chốt, nên nó là quy ước của công ty.
    ("gia_ban_gom_thue_gtgt", "1", "Giá bán niêm yết đã gồm thuế GTGT (1) hay chưa gồm (0)", "cờ",
     "Chủ tịch xác nhận 13/9/2026: giá bán niêm yết ĐÃ GỒM thuế GTGT (trước đó chỉ là quy ước máy "
     "đọc ngược từ mẫu quyết toán Điều hành)"),
    # Đ-10 · Ngưỡng thực chi THẤP hơn dự toán. Khai riêng khỏi `nguong_bien` (chiều vượt) vì đây là
    # một câu hỏi khác: hụt vài phần trăm là chuyện thường của mọi chuyến (đổi nhà hàng, bớt một
    # suất), còn hụt sâu thì thường là chương trình đã đổi so với thứ đã bán cho khách.
    #
    # Đo trên đoàn Hồ Tràm: ăn tối −11%, vé tham quan −11%, banner −52%. Ngưỡng 15% để hai dòng đầu
    # đi qua và dòng thứ ba phải có một câu giải thích.
    ("nguong_hut_du_toan", "0.15", "Thực chi thấp hơn dự toán quá tỷ lệ này thì cần một dòng giải thích",
     "tỷ lệ", "Đ-10, đo trên mẫu quyết toán Hồ Tràm 12/9/2026"),
    # ---- CÔNG TẮC CHẠY THỬ: Chủ tịch đi qua được cả cửa TÁCH BẠCH TRÁCH NHIỆM ----
    #
    # Chủ tịch chốt 13/9/2026: mở hết cửa cho Chủ tịch ĐỂ CHẠY THỬ VÀ TRÌNH DIỄN. Sáu cửa được mở là
    # sáu cửa vốn đóng với mọi vai trò, không riêng Chủ tịch: Kế toán kiểm chứng từ, Kế toán bấm ĐÃ
    # CHI, Kế toán xác nhận và trả lại quyết toán, CNTT đối chiếu độc lập, CNTT thao tác tài khoản
    # lãnh đạo, và chữ ký thứ hai của nội dung marketing.
    #
    # ĐỂ Ở THAM SỐ chứ không viết cứng vào sáu tệp mã, vì hai lý do:
    #
    #   1. Đây là quyết định của GIAI ĐOẠN chạy thử. Đến ngày vận hành thật, đóng lại là đổi một dòng
    #      ở màn hình tham số — không phải sửa sáu tệp, chạy lại phép thử và đẩy một bản nâng cấp.
    #      Một việc phải làm mà tốn một bản nâng cấp là một việc sẽ bị hoãn.
    #   2. Tham số là con số ĐỌC ĐƯỢC. Robot Kiểm soát nêu nó thành phát hiện `tach_bach_dang_mo`,
    #      nên Ban Kiểm soát nhìn thấy hệ thống đang ở chế độ nào mà không phải đọc mã nguồn. Một
    #      lớp kiểm soát bị tắt mà không ai nhìn thấy nó đang tắt thì tệ hơn là chưa từng có.
    #
    # CÓ MỘT CỬA KHÔNG NẰM TRONG DANH SÁCH NÀY và tham số cũng không mở được: cửa chữ ký hai người
    # (chu_ky.kiem_tra_nguoi_ky). Ở đó Chủ tịch vốn đã nằm trong danh sách được ký — cửa ấy không
    # chặn ai vì vai trò. Thứ nó chặn là MỘT NGƯỜI KÝ THAY CẢ HAI VAI, mà mô hình dữ liệu chỉ có hai
    # ô `signed_chutich` / `signed_tgd`: mở ra thì sổ ghi một chữ ký TGĐ mà TGĐ chưa hề bấm. Đó không
    # phải nới quyền, đó là ghi sai sổ — và con số sai ấy không ai đọc lại mà biết được.
    ("chu_tich_mo_het_cua", "1",
     "Chủ tịch đi qua được cả cửa tách bạch trách nhiệm (1 = mở, dùng khi chạy thử; 0 = đóng)", "cờ",
     "Chủ tịch chốt 13/9/2026 để chạy thử và trình diễn. ĐẶT LẠI VỀ 0 vào ngày vận hành thật"),
    # ---- Đ-6 · Tiền tip. Chủ tịch chốt 12/9/2026: "tiền tip tour châu Âu chia 1 phần với công ty" ----
    #
    # GIÁ TRỊ ĐỂ TRỐNG, và phải để trống — giống hai mốc vận hành thật ở trên. Chủ tịch đã chốt
    # NGUYÊN TẮC (có chia) nhưng chưa cho TỶ LỆ. Điền sẵn một con số vào đây là tự đặt ra tỷ lệ chia
    # tiền giữa công ty và trưởng đoàn bằng một dòng mã, và về sau không ai trả lời được câu "ai đã
    # quyết 50/50, từ ngày nào".
    #
    # Chưa ký thì tip_tour.ty_le_cong_ty() đọc ra None và phép chia TỪ CHỐI chạy – khác hẳn chia 0%
    # (công ty không lấy gì) hay chia 100% (công ty lấy hết). Cả hai đều là chính sách hợp lệ, nên
    # mã không được đoán hộ bên nào.
    ("ty_le_tip_cong_ty", "", "Phần tiền tip thuộc về công ty (phần còn lại của trưởng đoàn)", "tỷ lệ",
     "Chủ tịch chốt nguyên tắc 12/9/2026 – TỶ LỆ CHƯA KÝ"),
]

# Tham số mang giá trị NGÀY chứ không phải số. propose_param kiểm giá trị bằng float(), nên nếu
# không khai ở đây thì một ngày tháng bị trả về "Giá trị phải là số" và không đường nào nhập được.
#
# GHÉP LẠI 11/9/2026: khối này từng được commit rồi BIẾN MẤT – một phiên khác lưu đè tệp này bằng
# bản mở từ trước. Thiếu nó thì routes.py vẫn gọi getattr(R, "THAM_SO_NGAY", ()) và nhận về rỗng,
# nên cửa nhập ngày im lặng không bao giờ chạy: mã trông đủ, hàng rào thì không có.
THAM_SO_NGAY = ("ngay_van_hanh_that", "ngay_du_lieu_that_vietrip")


# Bộ nhớ đệm tham số. get_param bị gọi hàng nghìn lần trong một lần dựng bảng điều khiển –
# mỗi chuyến quyết toán gọi 4 lần, mỗi lần là một chuyến đi–về tới PostgreSQL ở Singapore. Tham số
# là master data đổi vài tháng một lần và mỗi lần đổi đều đi qua đúng một chỗ (ký duyệt tham số),
# nên đệm được an toàn miễn là chỗ đó xoá đệm. TTL 60 giây để bản ghi do phiên khác ghi cũng vào.
# Đệm theo KHÓA, không theo (khóa, ngày). Đổi ngày 10/9/2026, lý do:
#
# Bản cũ lấy (khóa, ngày hiệu lực) làm khóa đệm. Với `get_param(db, "han_qt_le")` – ngày mặc định là
# hôm nay – thì đệm ăn. Nhưng những chỗ tính theo TỪNG CHUYẾN đều truyền `on=tour.end_date`, mà mỗi
# chuyến một ngày kết thúc khác nhau, nên đệm trượt gần như mọi lần: duyệt 1.258 chuyến là 1.258 câu
# truy vấn cho đúng một tham số không đổi. Đó là phần lớn 55 giây của màn hình Khoản treo.
#
# Bản mới nạp TẤT CẢ bản ghi đang hiệu lực của một khóa trong một câu, rồi chọn bản ghi theo ngày
# ngay trong bộ nhớ. Phép chọn giữ nguyên thứ tự cũ (effective_from giảm dần, id giảm dần, lấy bản
# ghi đầu tiên có effective_from <= ngày hỏi) nên kết quả trùng khít bản cũ – chỉ khác số câu truy vấn.
_PARAM_CACHE: dict[str, tuple[list[tuple[date, int, str]], float]] = {}
PARAM_CACHE_TTL = 60.0


def clear_param_cache() -> None:
    """Gọi ngay sau khi ghi/duyệt/huỷ một tham số. Quên gọi là hệ thống chạy bằng giá trị cũ tới 60 giây."""
    _PARAM_CACHE.clear()


def _param_rows(db: Session, key: str) -> list[tuple[date, int, str]]:
    """Mọi bản ghi đang hiệu lực của một khóa, sắp sẵn theo thứ tự ưu tiên (mới nhất trước)."""
    import time
    hit = _PARAM_CACHE.get(key)
    if hit is not None and time.time() - hit[1] < PARAM_CACHE_TTL:
        return hit[0]
    rows = [(p.effective_from, p.id, p.value)
            for p in db.execute(select(Param).where(Param.key == key, Param.status == "active")
                                .order_by(desc(Param.effective_from), desc(Param.id))).scalars()]
    _PARAM_CACHE[key] = (rows, time.time())
    return rows


def _param_value(db: Session, key: str, on: date | None) -> str | None:
    on = on or date.today()
    for eff, _id, val in _param_rows(db, key):
        if eff <= on:
            return val
    return None


def get_param_chu(db: Session, key: str, on: date | None = None) -> str:
    """Đọc một tham số DẠNG CHỮ. `get_param` ở dưới ép về float và nổ với thứ không phải số.

    Thêm 18/9/2026 cho `thuong_hieu_vai_ky` – tham số đầu tiên của sổ mang giá trị là một DANH
    SÁCH VAI TRÒ chứ không phải một con số. Không nới `get_param` cho nhận cả hai kiểu: một hàm
    trả khi thì số khi thì chữ là hàm mà nơi gọi phải đoán, và chỗ đoán sai sẽ im lặng.
    """
    val = _param_value(db, key, on)
    if val is None:
        for k, v, *_ in DEFAULT_PARAMS:
            if k == key:
                return str(v)
        raise KeyError(key)
    return str(val)


def get_param(db: Session, key: str, on: date | None = None) -> float:
    val = _param_value(db, key, on)
    if val is None:
        for k, v, *_ in DEFAULT_PARAMS:
            if k == key:
                return float(v)
        raise KeyError(key)
    return float(val)


def get_param_text(db: Session, key: str, on: date | None = None) -> str:
    """Tham số dạng CHỮ – cố ý KHÔNG đệm, khác với `get_param` ở trên.

    Ngày 10/9/2026 đã thử cho hàm này dùng chung đệm với `get_param`, và một phép thử đội xe đỏ ngay:
    nó sửa thẳng bản ghi Param trong cơ sở dữ liệu (không qua cửa duyệt tham số nên không ai gọi
    `clear_param_cache`) rồi đọc lại ngay. Với `get_param` thì độ trễ tới 60 giây là điều đã chấp nhận từ
    trước cho các tham số SỐ – chúng đổi vài tháng một lần. Nhưng tham số chữ ở đây đang giữ những thứ như
    `xe_nguoi_lap_lenh` (ai được lập lệnh điều xe): sửa xong mà 60 giây sau mới có hiệu lực thì người vừa
    sửa tưởng mình gõ sai và sửa tiếp.

    Và đệm chỗ này chẳng được gì: mỗi lần tính bảng lương chỉ gọi tới nó một lần. Nên giữ nguyên một câu
    truy vấn thẳng – đừng "cho nhất quán" mà đệm lại.
    """
    on = on or date.today()
    row = db.execute(select(Param).where(Param.key == key, Param.status == "active", Param.effective_from <= on)
                     .order_by(desc(Param.effective_from), desc(Param.id))).scalars().first()
    if row is None:
        for k, v, *_ in DEFAULT_PARAMS:
            if k == key: return v
        raise KeyError(key)
    return row.value


def seed_params(db: Session):
    """Nạp tham số mặc định; CSDL đã có thì chỉ bổ sung khóa mới xuất hiện trong bộ chính sách (không đè giá trị đang hiệu lực)."""
    have = {p.key for p in db.execute(select(Param)).scalars()}
    for k, v, label, unit, src in DEFAULT_PARAMS:
        if k in have: continue
        db.add(Param(key=k, value=v, label=label, unit=unit, effective_from=date(2026, 9, 1),
                     source=src, status="active", signed_chutich=True, signed_tgd=True, proposed_by="seed"))
    db.commit()
    clear_param_cache()


# ====================== NHẬT KÝ BẤT BIẾN ======================
def _canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def audit(db: Session, actor: str, role: str, action: str, entity: str, before=None, after=None):
    db.flush()  # để bản ghi audit chưa commit trong cùng giao dịch được nhìn thấy khi lấy hash cuối
    last = db.execute(select(AuditLog).order_by(desc(AuditLog.id))).scalars().first()
    prev = last.hash if last else "0" * 64
    ts = datetime.now()
    payload = _canon({"ts": ts.isoformat(), "actor": actor, "role": role, "action": action,
                      "entity": entity, "before": before, "after": after})
    h = hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
    db.add(AuditLog(ts=ts, actor=actor, role=role, action=action, entity=entity,
                    before=before, after=after, prev_hash=prev, hash=h))


def verify_chain(db: Session) -> tuple[bool, int, str]:
    prev = "0" * 64
    n = 0
    for row in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        payload = _canon({"ts": row.ts.isoformat(), "actor": row.actor, "role": row.role, "action": row.action,
                          "entity": row.entity, "before": row.before, "after": row.after})
        h = hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()
        if row.prev_hash != prev or row.hash != h:
            return False, n, f"Chuỗi bị phá tại bản ghi #{row.id}"
        prev = h
        n += 1
    return True, n, "Chuỗi nhật ký toàn vẹn"


# ====================== DỰ TOÁN 3 CON SỐ & CỔNG BIÊN ======================
def is_doan(tour: Tour) -> bool:
    """Tour có thuộc mảng Đoàn không – dùng cho định tuyến duyệt, hạn quyết toán, và cách tính hoa hồng.

    Trước 07/9/2026 hàm này chỉ nhìn loại chuyến. Từ khi Kinh doanh tách hai phòng, "thuộc mảng nào" được
    định nghĩa một chỗ duy nhất ở app/services/segments.py (hợp của loại chuyến đoàn VÀ quy ước mã MICE).
    Nếu để hai định nghĩa song song thì sẽ có ngày một tour nằm ở màn hình phòng Đoàn nhưng lại được trả
    hoa hồng theo bậc thang của phòng Lẻ – lệch tiền chứ không chỉ lệch màn hình.

    Trên dữ liệu thật ngày 07/9/2026 hai định nghĩa cho kết quả GIỐNG HỆT nhau (115/115 tour mã MICE đều là
    doan_noi_dia), nên thay đổi này không dịch một đồng nào của kỳ lương nào; nó chỉ chặn trường hợp nhập lệch
    về sau. Muốn quay lại quy tắc cũ thì sửa đúng segments.py, không sửa riêng chỗ này."""
    from app.services import segments as SEG
    return SEG.mang_of(tour) == "doan"


BUDGET_SOURCES = {"du_toan_tour": "dự toán của chuyến", "san_pham": "cơ cấu chi phí sản phẩm (tham chiếu)", "chua_co": "chưa có dự toán"}


def calc(tour: Tour, threshold: float, fixed: float | None = None, var: float | None = None, source: str | None = None) -> dict:
    """Ba con số dự toán và cổng biên.

    THIẾU CHI PHÍ KHÔNG PHẢI LÀ CHI PHÍ BẰNG 0 (Ý kiến thẩm định 06/9/2026, B1): giá vốn 0 từng cho
    biên 100% nên cổng biên luôn báo "ĐẠT" – vô hiệu hóa cổng chặn số 1. Nay dự toán thiếu giá vốn
    có complete=False và gate_state="chua_du_co_so"; pass_gate chỉ đúng khi dự toán đủ cơ sở tính.
    """
    # Gia cố tại chỗ GÁN, không phải chỗ dùng: từ đây trở xuống p/f/v đi vào một chục phép tính, và
    # máy quét chữ của K2 không lần được qua một biến cục bộ. Rỗng ở đây nghĩa là chưa lập dự toán –
    # xử như 0 thì `source` ra "chua_co", đúng ý.
    p, n = tour.price_per_pax or 0, tour.planned_pax
    f = (tour.fixed_cost if fixed is None else fixed) or 0
    v = (tour.var_cost_per_pax if var is None else var) or 0
    if source is None:
        source = "du_toan_tour" if (f > 0 or v > 0) else "chua_co"
    revenue = p * n
    cost = f + v * n
    has_cost = f > 0 or v > 0
    margin = (revenue - cost) / revenue if revenue else 0.0
    unit = p - v
    breakeven = math.ceil(f / unit) if unit > 0 else None
    unit10 = p * (1 - threshold) - v
    pax_margin = math.ceil(f / unit10) if unit10 > 0 else None
    # Dự toán tham chiếu lấy từ cơ cấu chi phí sản phẩm KHÔNG đủ tư cách cho cổng biên: dữ liệu sản phẩm
    # hiện chỉ 21/313 mã có cơ cấu chi phí và phần lớn sai (có mã ghi 11 đ/khách → biên 99,99%). Dùng nó
    # để mở cổng thì cổng lại bị vô hiệu hóa lần nữa – chỉ hiển thị tham chiếu, cổng vẫn "chưa đủ cơ sở".
    own = source == "du_toan_tour"
    complete = all([p > 0, n > 0, has_cost, own]) and breakeven is not None
    passed = complete and margin >= threshold
    return {"revenue": revenue, "cost": cost, "profit": revenue - cost, "margin": margin,
            "breakeven_pax": breakeven, "pax_for_margin": pax_margin, "threshold": threshold,
            "fixed_cost": f, "var_cost_per_pax": v, "has_cost": has_cost,
            "budget_source": source, "budget_source_label": BUDGET_SOURCES.get(source, source),
            "reference_only": source == "san_pham",
            "pass_gate": passed, "complete": complete,
            "gate_state": "dat" if passed else ("chua_du_co_so" if not complete else "khong_dat")}


def bien_neu_hoa_hong_chua_vao(tour: Tour, c: dict) -> dict:
    """Biên thứ hai đặt cạnh biên đã nhập: biên NẾU hoa hồng khách chưa nằm trong giá vốn.

    ĐÂY LÀ CHỖ CÁI Ô BẮT BUỘC CÓ RĂNG (Chủ tịch quyết 24/9/2026).

    `calc()` đọc giá vốn từ đúng hai con số người lập dự toán gõ: `fixed_cost` và
    `var_cost_per_pax`. Nó KHÔNG đọc các dòng chi phí chi tiết. Nghĩa là một ô "hoa hồng khách"
    nằm riêng, tự nó, không chạm được vào cổng biên 10% — người bán vẫn khai "có, 124 triệu" rồi
    vẫn gõ một giá vốn không chứa 124 triệu ấy, và cổng vẫn đo trên con số cũ. Một cái ô trang trí.

    Hàm này không sửa điều đó bằng cách CỘNG thêm — cộng sau lưng người lập dự toán thì hai màn
    hình sẽ in hai giá vốn khác nhau cho cùng một chuyến, và không ai biết con số nào là con số họ
    đã gõ. Nó làm việc khác: tính một biên thứ hai với giả định khoản ấy CHƯA nằm trong giá vốn,
    rồi đưa cả hai cho người ký. Con số thứ hai là một CẬN DƯỚI, không phải một khẳng định.

    Trả về `{"co": bool, "tien": float, "bien_neu_chua_vao": float|None, "lech": float|None}`.
    `bien_neu_chua_vao` là None khi không khai "có" hoặc khi doanh thu bằng 0 — không trả về 0,
    vì 0 đọc như một biên bằng không, còn None đọc đúng là "không có câu trả lời".
    """
    khai = (getattr(tour, "hoa_hong_khach", "") or "").strip()
    tien = float(getattr(tour, "hoa_hong_khach_tien", 0) or 0)
    if khai != "co" or tien <= 0:
        return {"co": khai == "co", "tien": tien, "bien_neu_chua_vao": None, "lech": None}
    rev = c.get("revenue") or 0
    if not rev:
        return {"co": True, "tien": tien, "bien_neu_chua_vao": None, "lech": None}
    bien2 = (rev - (c.get("cost") or 0) - tien) / rev
    return {"co": True, "tien": tien, "bien_neu_chua_vao": bien2,
            "lech": (c.get("margin") or 0.0) - bien2}


def budget_of(db: Session, t: Tour) -> tuple[float, float, str]:
    """Dự toán của chuyến và NGUỒN của nó – tách hẳn khỏi chi phí thực chi (B2).

    Trước đây dự toán của tour nhập từ Vietrip được suy ngược từ dòng quyết toán, nên biên kế hoạch
    luôn bằng biên thực tế và cảnh báo vượt dự toán không bao giờ kích hoạt. Nay: dự toán do Điều hành
    lập; nếu chuyến chưa có thì lấy cơ cấu chi phí sản phẩm làm dự toán THAM CHIẾU (ghi rõ nguồn);
    không có nữa thì trả về "chưa có dự toán", không suy ra số 0.
    """
    if (t.fixed_cost or 0) > 0 or (t.var_cost_per_pax or 0) > 0:
        return t.fixed_cost, t.var_cost_per_pax, "du_toan_tour"
    from app.models.core import Product
    p = None
    if t.product_id: p = db.get(Product, t.product_id)
    if p is None and t.product_code:
        p = db.execute(select(Product).where(Product.code == t.product_code)).scalars().first()
    if p is not None:
        f, v = p.fixed_cost(), p.var_cost_per_pax()
        if f > 0 or v > 0:
            return f, v, "san_pham"
    return 0.0, 0.0, "chua_co"


def calc_db(db: Session, t: Tour, threshold: float) -> dict:
    """calc() có tra cứu dự toán tham chiếu từ sản phẩm – dùng cho hiển thị, báo cáo và robot.
    Riêng bước TRÌNH dự toán vẫn dùng calc() thuần: Điều hành phải tự nhập đủ ba con số."""
    f, v, src = budget_of(db, t)
    return calc(t, threshold, f, v, src)


def booked_pax(tour: Tour) -> int:
    """Số chỗ ĐANG BỊ GIỮ trên chuyến – không phải số booking đang tồn tại.

    NỬA CÒN THIẾU CỦA VPM-7 (bù ngày 11/9/2026). Phân hệ giữ chỗ đã dựng xong cả robot hết hạn, cửa
    gia hạn, cửa khôi phục và nhật ký; giu_cho.con_trong() cũng đã ghi thẳng trong chú thích rằng
    "booking đã hết hạn giữ chỗ không nằm trong booked_pax nữa". Nhưng hàm này thì vẫn cộng mọi
    booking chưa huỷ, nên câu ấy KHÔNG đúng: robot tuyên hết hạn, ghi nhật ký, bắn cảnh báo – mà số
    chỗ còn trống của tour không nhúc nhích một đơn vị. Toàn bộ lý do VPM-7 tồn tại nằm ở một phép
    cộng thiếu một điều kiện.

    `giu_cho_het = True` nghĩa là: quá hạn giữ mà CHƯA THU ĐỒNG NÀO (luật 1 của giu_cho.py – có tiền
    vào thì robot không đụng tới), nên chỗ đã trả về tour. Booking VẪN CÒN – luật 2, robot không xoá
    cam kết với khách – nó chỉ không còn chiếm ghế. Đó cũng là cách đọc đúng ở mọi chỗ gọi hàm này:
    chỗ còn lại để bán, số khách so với điểm hoà vốn D-7, dự toán theo đầu khách. Một người chưa trả
    đồng nào và đã mất chỗ thì không phải một khách đang ngồi trên chuyến.

    Khách trả tiền muộn: Điều hành bấm khôi phục, giu_cho.gia_han() kiểm tour còn chỗ rồi đặt
    giu_cho_het = False, và ghế được tính lại ngay tại đây.
    """
    return sum(b.pax for b in tour.bookings if not b.cancelled and not b.giu_cho_het)


def settlement_deadline(db: Session, tour: Tour) -> date:
    days = get_param(db, "han_qt_doan" if is_doan(tour) else "han_qt_le", tour.end_date)
    return tour.end_date + timedelta(days=int(days))


def approver_role(tour: Tour) -> str:
    """Điều 4 Văn bản đính chính: lẻ → TGĐ; đoàn → PTGĐ tour đoàn."""
    return "ptgd_doan" if is_doan(tour) else "tgd"


def settlement_summary(db: Session, tour: Tour) -> dict:
    """Số liệu quyết toán và quỹ thưởng theo mục 6.4 (chỉ tính khi đã Kế toán xác nhận)."""
    rev = tour.actual_revenue or 0
    cost = (tour.actual_cost or 0) + (tour.promo_value or 0)  # ĐC Điều 3: giá trị mã KM là một dòng giá vốn nội bộ
    profit = rev - cost
    margin = profit / rev if rev else 0
    thr = get_param(db, "nguong_bien", tour.end_date)
    deadline = settlement_deadline(db, tour)
    on_time = tour.closed_at is not None and tour.closed_at.date() <= deadline
    key = {"le_noi_dia": "quy_dh_le_noi_dia", "le_nuoc_ngoai": "quy_dh_le_nuoc_ngoai", "non_package": "quy_dh_le_noi_dia"}.get(tour.tour_type, "quy_dh_doan")
    rate = get_param(db, key, tour.end_date)
    # ĐC Điều 7: tour lẻ < ngưỡng hoặc duyệt dưới biên → không quỹ; đoàn không phụ thuộc biên. Quá hạn → mất thưởng chuyến.
    eligible = on_time and (is_doan(tour) or (margin >= thr and not tour.below_margin))
    fund = profit * rate if (eligible and profit > 0) else 0
    share_nv = get_param(db, "quy_dh_chia_nv", tour.end_date)
    return {"revenue": rev, "cost": cost, "profit": profit, "margin": margin, "deadline": deadline,
            "on_time": on_time, "eligible": eligible, "fund": fund, "fund_nv": fund * share_nv,
            "fund_tp": fund * (1 - share_nv), "rate": rate}


# ====================== ROBOT CẢNH BÁO (R3/R7 thu gọn) ======================
def run_robots(db: Session) -> int:
    """Sinh cảnh báo D-7, quá hạn quyết toán, SLA booking. Chạy định kỳ; không sửa dữ liệu nghiệp vụ."""
    today = date.today()
    created = 0

    # KS-4 – mốc thời gian của lượt quét. Đọc một lần ở đây, không đọc lại trong vòng lặp.
    lui = int(get_param(db, "canh_bao_lui_ngay") or 30)
    moc_lui = today - timedelta(days=lui)
    han_gio = float(get_param(db, "canh_bao_han_mac_dinh_gio") or 48)
    # Mốc vận hành thật đọc qua đúng một chỗ. None nghĩa là CHƯA AI KÝ – và lúc ấy không đoán:
    # nguồn để TRỐNG chứ không đóng dấu 'phat_sinh' cho mọi thứ. Một ô trống đếm được, còn một ô
    # điền bừa thì đọc như sự thật.
    from app.services import moi_truong_du_lieu as MT
    vhs = MT.moc_van_hanh_that(db)

    def add(kind, level, ref, msg, roles, moc: date | None = None):
        """Thêm một cảnh báo nếu chưa có dòng CÙNG (kind, ref) đang mở.

        KS-4 gắn luôn ba thứ mà trước đây không ai gắn:
          · gom_khoa  – khoá gom trùng, để lượt quét sau cộng dồn chứ không đẻ dòng mới
          · han_xu_ly – không có hạn thì không có gì trễ, và 1.310 dòng đỏ đứng ngang nhau
          · nguon     – 'lich_su' hay 'phat_sinh'. Sự kiện TRƯỚC ngày vận hành thật là việc dọn dữ
                        liệu, sau ngày ấy là việc kỷ luật. Trộn hai thứ là cách chắc chắn nhất để
                        không xử lý được thứ nào. Mốc CHƯA KÝ thì để trống – không đoán.
        `moc` là ngày SỰ KIỆN xảy ra (không phải hôm nay) – dùng để xếp nguồn.
        """
        nonlocal created
        exists = db.execute(select(Alert).where(Alert.kind == kind, Alert.ref == ref, Alert.resolved == False)).scalars().first()
        if not exists:
            ngay = moc or today
            db.add(Alert(kind=kind, level=level, ref=ref, message=msg, to_roles=roles,
                         gom_khoa=f"{kind}:{ref}",
                         han_xu_ly=datetime.now() + timedelta(hours=han_gio),
                         nguon="" if vhs is None else ("lich_su" if ngay < vhs else "phat_sinh")))
            created += 1

    d7 = int(get_param(db, "moc_d7"))
    for t in db.execute(select(Tour).where(Tour.status == "da_duyet")).scalars():
        if t.tour_type == "non_package":
            if t.end_date < today: t.status = "ket_thuc"
            continue
        thr = get_param(db, "nguong_bien", t.start_date)
        c = calc_db(db, t, thr)
        days_left = (t.start_date - today).days
        if 0 <= days_left <= d7 and c["breakeven_pax"] and booked_pax(t) < c["breakeven_pax"] and not t.chairman_run_decision:
            level = "red" if days_left <= d7 - 1 else "warn"
            add("d7", level, t.code,
                f"{t.code} khởi hành {t.start_date:%d/%m}: {booked_pax(t)}/{c['breakeven_pax']} khách hòa vốn – cần ghép/dời/hủy hoặc Chủ tịch duyệt chạy",
                "tp_dh,gd_kd,tgd,chutich")
        if t.end_date < today:
            t.status = "ket_thuc"
    # KS-4 – CHỈ quét chuyến kết thúc trong khoảng lùi. Trước bản này vòng lặp duyệt MỌI chuyến
    # trạng thái "ket_thuc" từ đầu lịch sử; với dữ liệu đổ từ Vietrip sang nó đẻ ra 851 dòng đỏ
    # trong một lượt, và 851 dòng đỏ thì không ai đọc dòng nào. Chuyến cũ hơn mốc lùi vẫn quá hạn
    # thật, nhưng đó là việc DỌN DỮ LIỆU một lần, không phải việc nhắc mỗi lượt quét.
    for t in db.execute(select(Tour).where(Tour.status == "ket_thuc", Tour.tour_type != "non_package",
                                           Tour.end_date >= moc_lui)).scalars():
        dl = settlement_deadline(db, t)
        if today > dl:
            add("qua_han_qt", "red", t.code,
                f"{t.code} quá hạn quyết toán (hạn {dl:%d/%m}): xếp nhóm dưới 10% / hoãn thưởng tới khi chốt; người điều hành mất thưởng chuyến",
                "tp_dh,ketoan,tgd", moc=t.end_date)
    for t in db.execute(select(Tour).where(Tour.status == "da_dong_so")).scalars():
        if t.closed_at and (today - t.closed_at.date()).days > int(get_param(db, "han_kt_xac_nhan")):
            add("kt_cham", "warn", t.code, f"{t.code}: Kế toán chưa xác nhận sau {get_param(db,'han_kt_xac_nhan'):.0f} ngày làm việc", "ketoan,tgd")
    try:
        from app.services import bookings as BK
        created += BK.robot_check(db)["new_alerts"]
        from app.services import sales_reports as SR
        created += SR.r9_run(db)["new_alerts"]
    except Exception as ex:   # không để lỗi R4 chặn các cảnh báo khác
        audit(db, "robot", "robot", "robot_r4_loi", "robot", after={"ly_do": str(ex)[:200]})
    # Hạn xử lý dòng tiền (Chủ tịch chốt 14/9/2026 – 24 giờ). Đặt trong try riêng: dòng tiền dựa
    # trên bảng bốn mốc, pháp nhân nào chưa có nền dữ liệu thì ném lỗi, và một pháp nhân hỏng không
    # được phép nuốt mất mọi cảnh báo còn lại của lượt quét.
    try:
        from app.services import han_dong_tien as HDT
        created += HDT.quet(db)
    except Exception as ex:
        audit(db, "robot", "robot", "robot_han_dong_tien_loi", "robot", after={"ly_do": str(ex)[:200]})
    sla = int(get_param(db, "sla_booking_phut"))
    for r in db.execute(select(ServiceRequest).where(ServiceRequest.booking_id == None)).scalars():
        mins = (datetime.now() - r.created_at).total_seconds() / 60
        if mins > sla:
            add("sla_booking", "warn", f"YC-{r.id}", f"Yêu cầu #{r.id} ({r.customer_name}) chưa được tạo booking sau {mins/60:.1f} giờ", "tp_dh,nv_dh")
    db.commit()
    return created


# ====================== TÍNH THU NHẬP THÁNG (bản nháp cho Robot Lương) ======================
def monthly_payroll_draft(db: Session, year: int, month: int) -> list[dict]:
    """Bản nháp: quỹ thưởng Điều hành theo chuyến đã Kế toán xác nhận trong tháng; hoa hồng đoàn theo người chốt."""
    rows = []
    tours = [t for t in db.execute(select(Tour).where(Tour.status.in_(["kt_xac_nhan", "khoa"]))).scalars()
             if t.kt_confirmed_at and t.kt_confirmed_at.year == year and t.kt_confirmed_at.month == month]
    by_op: dict[int, dict] = {}
    doan_profit_by_sales: dict[int, float] = {}
    for t in tours:
        s = settlement_summary(db, t)
        o = by_op.setdefault(t.operator_id, {"name": t.operator.full_name, "role": "nv_dh", "chuyen": 0, "fund_nv": 0.0, "fund_tp": 0.0})
        o["chuyen"] += 1
        o["fund_nv"] += s["fund_nv"]
        o["fund_tp"] += s["fund_tp"]
        if is_doan(t):
            for b in t.bookings:
                doan_profit_by_sales[b.sales_id] = doan_profit_by_sales.get(b.sales_id, 0) + s["profit"] * ((b.amount or 0) / (s["revenue"] or 0) if (s["revenue"] or 0) else 0)
    for uid, o in by_op.items():
        rows.append({"nguoi": o["name"], "khoan": "Thưởng chuyến Điều hành (70%)", "so_chuyen": o["chuyen"], "tien": round(o["fund_nv"])})
    tp_total = sum(o["fund_tp"] for o in by_op.values())
    if tp_total:
        rows.append({"nguoi": "Trưởng phòng Điều hành", "khoan": "30% quỹ toàn phòng", "so_chuyen": len(tours), "tien": round(tp_total)})
    moc = get_param(db, "hh_doan_moc"); rate = get_param(db, "hh_doan_ty_le")
    for uid, pr in doan_profit_by_sales.items():
        u = db.get(User, uid)
        rows.append({"nguoi": u.full_name if u else uid, "khoan": f"Hoa hồng đoàn 10% × (LN − {moc:,.0f})", "so_chuyen": "", "tien": round(max(0, pr - moc) * rate)})
    return rows
