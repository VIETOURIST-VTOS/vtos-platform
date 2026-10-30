"""Mỗi con số phải có một CỬA cho người nhập – phép kiểm giữ cho quy tắc ấy không mòn.

Ranh giới Chủ tịch đặt ngày 09/9/2026: phần mềm viết cấu trúc, phép tính và luồng quản trị; SỐ LIỆU do
nhân viên các phòng tự nhập – gõ vào biểu, tải tệp, hoặc tải ảnh. Hệ quả trực tiếp: mỗi con số hệ thống
cần phải có ít nhất một cửa để người dùng đưa nó vào. Bảng nào không có cửa nào thì đó là VIỆC CÒN
THIẾU, không phải việc để ai đó nhập hộ vào cơ sở dữ liệu.

Ngày 09/9/2026 đã rà tay toàn bộ 128 bảng và ra kết quả: 120 bảng đủ cửa, 8 bảng máy sinh (đúng ra là
không cần cửa). Tệp này giữ cho kết quả ấy không mòn đi. Rà tay một lần chỉ đúng tại thời điểm rà; bảng
thứ 129 thêm vào tuần sau sẽ không có ai rà lại, và nó sẽ lặng lẽ nằm đó không cửa.

PHÉP KIỂM TRẢ LỜI ĐÚNG MỘT CÂU: có bảng nào trong mô hình mà chưa ai khai cửa cho nó không?

Ba nguồn cửa, và mức tin cậy của chúng KHÁC NHAU – nói rõ ra đây để không ai đọc bảng này rồi yên tâm
quá mức:

  1. CỬA TẢI TỆP – đọc SỐNG từ intake.BO_NAP[*]["bang_dich"]. Bỏ một bộ nạp đi là phép kiểm biết ngay.
  2. CỬA NHẬP TAY – danh sách KHAI, chép từ bản rà 09/9. Phép kiểm biết bảng đã ĐƯỢC KHAI là có cửa;
     nó KHÔNG tự kiểm màn hình ấy còn sống hay không. Xoá một màn hình nhập tay thì phép kiểm này im.
     Chỗ đó do K12 (đối chiếu ma trận quyền với thư mục màn hình) gác.
  3. MÁY SINH – danh sách KHAI, mỗi dòng kèm LÝ DO. Bắt buộc có lý do: "máy sinh" là cách dễ nhất để
     một bảng thiếu cửa được cho qua, nên phải viết ra ai ghi vào bảng đó và vì sao người không cần
     chạm tới. Không viết được lý do nghĩa là chưa chắc nó máy sinh.

Bảng có trong danh sách khai nhưng không còn trong mô hình thì KHÔNG phải lỗi: các nhánh đang làm dở
có bảng chưa gộp về (chuỗi bán hàng V6), và bảng đã bỏ thì dòng khai thừa ra là chuyện dọn dần.
"""
from sqlalchemy.orm import Session

CUA_TAY = (
# KS-10 29/10/2026. Đơn phòng OTA: Điều hành dựng đơn ở màn /don-khach-san-ota. Môi trường
# «Chạy thật» thì Điều hành DÁN sáu con số tra từ Agoda; môi trường «Thử» máy sinh mã giả để
# chạy thử sáu bước. Không có đường nối tự động sang Agoda, nên đây là cửa tay thật.
"don_khach_san_ota",
    # CN-1 21/10/2026. Bang xac nhan cong thang: HCNS bam «Xac nhan cong», TGD bam «Duyet cong» o
    # the «Cham cong & nghi phep» man /hr. May chi chup so lieu luc nguoi bam, khong tu sinh dong nao.
    "xac_nhan_cong",
    # Dot E4a 12/10/2026. Ca hai bang nhap tay tren man hinh `/params`: nguoi dung khai
    # dieu khoan (ma, moc, cac dot), con cac dot THAT cua mot nghia vu do dieu khoan sinh ra
    # va Ke toan sua han duoc. KHONG khai la may sinh: may dung khuon, nguoi dat ra khuon ay.
    "dieu_khoan_thanh_toan",
    "dot_thanh_toan",
    "van_ban_phap_che",
    # Đợt E2a — cặp xung đột tách bạch trách nhiệm. Người dùng tự khai qua màn hình /ket-so;
    # hệ thống KHÔNG nạp sẵn dòng nào, vì mỗi dòng là một quy chế kiểm soát nội bộ có người ký.
    "cap_tach_nhiem",
    "nghia_vu_cong_bo",
    "ban_ghi_cong_bo",
    # Đợt D2 — bàn làm việc Pháp chế. Cả bốn bảng người dùng tự khai qua màn hình
    # /ir-phap-che; hệ thống không nạp sẵn dòng nào.
    "yeu_cau_phap_che",
    "ra_soat_hop_dong",
    "ban_ghi_chu_ky",
    "xac_nhan_chu_so_lieu",
    # Đợt D3 — quan hệ nhà đầu tư. Người dùng tự khai qua màn hình /ir-phap-che;
    # hệ thống không nạp sẵn dòng nào, và không chép số cổ phần sở hữu từ đâu cả.
    "lien_he_nha_dau_tu",
    "tuong_tac_nha_dau_tu",
    "quyen_truy_cap_ho_so",
    "lich_su_to_chuc",
    "chi_ky_luong",
    # Ba bảng HCNS mở 09/10/2026. Cả ba là CỬA TAY, và không bảng nào được khai MAY_SINH — kể cả
    # bảng đánh giá, nơi ba ô A do máy điền sẵn: ba ô ấy chỉ là GIÁ TRỊ máy tính ra, còn DÒNG thì
    # vẫn do trưởng phòng mở và ba ô B vẫn do người chấm. Khai nó là máy sinh thì ngày không ai
    # chấm, bảng rỗng mà không bộ đếm nào kêu.
    "danh_gia_nhan_su",      # /hr thẻ "Đánh giá & sự vụ" — trưởng phòng chấm
    "de_nghi_mua",           # /de-nghi-mua — mọi phòng gửi, TGĐ/Chủ tịch duyệt, Kế toán ghi đã chi
    "cap_phat_tai_san",      # /tai-san — HCNS lập biên bản cấp phát
    # Đợt E1 (09/10/2026). CỬA TAY trên màn hình /ket-so. Bảng bắt đầu rỗng và PHẢI rỗng: mỗi
    # dòng là một mức chặn có người ký, nên máy nạp sẵn một dòng là máy tự đặt mức hộ người.
    "muc_do_chan",
    # DL-1 (11/10/2026). CUA TAY tren man hinh Lenh dieu xe. Bang bat dau RONG va phai rong: mot
    # de nghi xe la mot cau cua nguoi Dieu hanh noi "chuyen nay can xe". May nap san mot dong la may
    # tu de nghi ho - va roi Giam doc doi xe lap lenh cho mot chuyen chua ai hoi.
    "fleet_vehicle_requests",
    # CT-1 (4.4.2, 11/10/2026). CUA TAY tren man hinh Tour > the "Chuong trinh". Bang bat dau RONG
    # va phai rong: chuong trinh cua mot chuyen chi sinh ra khi Dieu hanh bam "mo tu san pham". May
    # nap san mot dong la may tu viet chuong trinh ho nguoi ban cho khach.
    "chuong_trinh_tour", "chuong_trinh_ngay",
    # Đợt E6 13/10/2026. CỬA TAY trên màn hình /accounting, tab "Khóa kỳ": ô kỳ + ô lý do + nút
    # "Trình Chủ tịch HĐQT". Bảng bắt đầu RỖNG và phải rỗng — mỗi dòng là một câu NGƯỜI nói
    # ("xin mở lại kỳ 09, vì..."), nên máy nạp sẵn một dòng là máy tự xin hộ. KHÔNG khai MAY_SINH:
    # hai cột `khoa_lai_*` do máy điền lúc khóa lại, nhưng DÒNG thì luôn do người mở.
    # HD-DG3 · 16/10/2026 — ĐỒNG Ý CÔNG KHAI NHẬN XÉT. CỬA TAY, và cửa ấy là TRANG KHẢO SÁT:
    # dòng sinh ra khi KHÁCH trả lời câu «anh/chị có đồng ý đăng công khai nhận xét này trên hồ sơ
    # hướng dẫn viên tại VTOS, không kèm tên và thông tin liên hệ không».
    #
    # KHÔNG khai MAY_SINH, dù máy là thứ chèn dòng. Phân biệt của bảng này là AI QUYẾT con số, chứ
    # không phải tay ai gõ: người quyết ở đây là khách, và khách bấm trên một cái form. Khai máy
    # sinh thì ngày không ai trả lời, bảng rỗng mà không bộ đếm nào kêu — mà rỗng ở bảng này nghĩa
    # là không một nhận xét nào đăng được, và sẽ không ai biết vì sao.
    #
    # Cửa khách đi KHÔNG CẦN ĐĂNG NHẬP, nên nó còn được khai ở hai chỗ nữa, mỗi chỗ một việc:
    # `test_p2.CONG_KHAI` (nhóm API không có hàng rào quyền) và `tools/ks2_khai_quyen.CONG_KHAI`
    # (đường GHI không khai quyền theo vai). Ba chỗ khai ba câu hỏi khác nhau, không phải chép ba lần.
    "dong_y_cong_khai",
    "mo_lai_ky",
    # Đợt E15 14/10/2026. CỬA TAY trên màn hình /dong-tien, khung "Đối chiếu tiền" → nút "Giải
    # thích" của từng dòng: ô số tiền (có dấu) + ô "khoản này là khoản gì". Bảng bắt đầu RỖNG và
    # phải rỗng — mỗi dòng là một câu NGƯỜI nói, nên máy nạp sẵn một dòng là máy giải thích hộ
    # chính cái chênh lệch mà đợt này dựng ra để bắt người phải nói. KHÔNG khai MAY_SINH.
    "giai_thich_lech",
    # Đợt E16 14/10/2026. CỬA TAY trên màn hình /accounting, thẻ "Nạp từ MISA", khung 7: ô chọn
    # tệp Excel + bảy ô khai nguồn + nút "Tải lên". Bảng DÒNG cũng khai CỬA TAY chứ KHÔNG khai
    # MAY_SINH, dù máy là thứ dựng từng dòng: mỗi dòng là một con số NGƯỜI điền vào tệp Excel và
    # ký tên chịu trách nhiệm. Khai nó là máy sinh thì ngày không ai tải lên, bảng rỗng mà không
    # bộ đếm nào kêu — mà rỗng ở bảng này nghĩa là không chốt sổ kiểm toán được nữa.
    "bo_so_kiem_toan", "bo_so_kiem_toan_dong",
    # Đợt R1 15/10/2026. CỬA TAY trên màn hình /accounting, thẻ "BCTC TT99", khung "Bản báo cáo đã
    # lập": ô tên kỳ + ô người đại diện + nút "Lập bản". Bảng DÒNG cũng khai CỬA TAY chứ KHÔNG
    # khai MAY_SINH, dù máy là thứ tính ra từng con số: NGƯỜI quyết định lập bản ấy và NGƯỜI ký
    # chịu trách nhiệm về nó. Khai máy sinh thì ngày không ai lập, bảng rỗng mà không bộ đếm nào
    # kêu — mà rỗng ở bảng này nghĩa là mọi kỳ đều đang đọc số tính lại từ sổ, đúng cái bệnh đợt
    # này chữa.
    "bao_cao_da_lap", "bao_cao_da_lap_dong",
    # Đợt R2 15/10/2026. Danh mục khoản mục chi phí — CỬA TAY trên màn hình quy ước hạch toán.
    # Mười dòng `nap_mac_dinh` gieo là KHUÔN ngành tour, không phải số liệu: Kế toán sửa tên, thêm
    # dòng, hoặc ngừng dùng qua /api/v1/hach-toan/khoan-muc. Khai MAY_SINH thì ngày Kế toán cần một
    # khoản mục thứ mười một sẽ không có chỗ nào thêm, và họ sẽ dồn hết vào "Chi phí tour khác".
    "khoan_muc_chi_phi",
    # ĐỢT R3b 17/10/2026. Tám dòng `nap_mac_dinh` gieo là KHUÔN cơ cấu, không phải số
    # liệu: HCNS sửa tên, thêm, hoặc ngừng dùng qua /api/v1/hach-toan/bo-phan. Khai
    # MAY_SINH thì ngày tách một phòng mới sẽ không có chỗ nào thêm, và người ta quay lại
    # gõ chữ tự do — đúng cái mà đợt này đi chữa.
    "bo_phan",
    "accounts", "ai_pause", "ai_positions", "alerts", "attachments", "attendance_days", "audit_log",
    "auto_reports", "ban_doc_chung_tu", "bang_gia", "bang_gia_dong", "bank_accounts_cat",
    "bank_doc_map", "bank_transactions", "bao_gia", "bao_gia_ban", "bao_gia_dong", "bookings",
    "campaigns", "care_tickets", "cash_plan_items", "chot_so_du", "companies", "complaints",
    "content_items",
    "conversations", "daily_reports",
    # BC-1 26/10/2026. Kiêm nhiệm báo cáo ngày: Chủ tịch tick ở tab «Kiêm nhiệm» màn /reports
    # (POST /daily-reports/kiem-nhiem).
    "report_extra_forms",
    # BC-2 (26/10/2026): việc phát sinh từ báo cáo ngày — người xem xét giao hỗ trợ ở tab «Tổng hợp
    # phòng» (POST /daily-reports/{rid}/giao-ho-tro); vướng mắc Phần 4 sinh khi nhân viên nộp.
    "daily_report_follow_ups",
    # CG-1 (26/10/2026): tài khoản bên ngoài — người ngoài tự tạo ở cổng kết nối (/login, bước xác thực
    # mã) và tự khai hồ sơ; VTOS duyệt ở màn /tai-khoan-ngoai.
    "tai_khoan_ngoai",
    # DH-1 (26/10/2026): hình thức hưởng hoa hồng của đối tác — GĐ KD / Kế toán chọn ở màn /hoa-hong-d06.
    "hinh_thuc_hoa_hong",
    # KH-1 (26/10/2026): yêu cầu khách tự gửi ở cổng khách hàng (/cong) — tour có lịch hoặc tour đoàn; đi kèm một lead cho Sales.
    "yeu_cau_khach",
    # KH-2 (26/10/2026): danh mục nhà hàng + thực đơn cho cổng khách — Điều hành nhập ở màn /nha-hang.
    "nha_hang",
    "thuc_don_nha_hang",
    # KH-3 (26/10/2026): khách tự đổi điểm lấy voucher và tự lưu tour yêu thích ở cổng khách.
    "voucher_rewards",
    "yeu_thich_khach",
    # KH-4: khách gửi từ cổng (đánh giá, góp ý lãnh đạo, yêu cầu hỗ trợ) — cửa là chính form cổng khách
    "phieu_danh_gia_khach",
    "gop_y_lanh_dao",
    "ho_tro_khach",
    # KS-1 (28/10/2026): Chủ tịch nhập link / bật OTA ở màn /khach-san-ota; lượt chuyển do khách bấm ở cổng.
    "phap_nhan_hop_dong",
    "doi_tac_ota",
    "luot_chuyen_ota",
    # KS-2 (28/10/2026): Kế toán nạp tệp báo cáo OTA ở màn /doi-soat-ota; duyệt lô mới sinh đặt phòng + sổ.
    "lo_nap_ota",
    "dat_phong_ota",
    "so_hoa_hong_ota",
    # CD-1 (28/10/2026): IR – Pháp chế đưa tài liệu, tạo sự kiện, trả lời ở màn /ir-cong-co-dong;
    # cổ đông ghi nhận quan tâm và gửi câu hỏi qua cổng ir. (phiên cổng ngoài).
    "tai_lieu_cong_co_dong",
    "su_kien_co_dong",
    "quan_tam_su_kien",
    "yeu_cau_ir",
    # CD-2 (28/10/2026): IR – Pháp chế tải danh sách VSD ở màn /ir-cong-co-dong (Chủ tịch duyệt); IR nối tài khoản.
    "lo_so_co_dong",
    "dong_so_co_dong",
    "noi_so_co_dong",
    # NCC-1 (28/10/2026): NCC phản hồi đơn, đề xuất giá, xác nhận bản kê, gửi đề nghị qua cổng dt. (phiên cổng);
    # Điều hành duyệt giá, Kế toán lập bản kê / trả lời, Marketing đưa học liệu ở màn /cong-ncc.
    "phan_hoi_don_ncc",
    "gia_ncc",
    "de_xuat_gia_ncc",
    "ban_ke_ncc",
    "dong_ban_ke_ncc",
    "de_nghi_ncc",
    "hoc_lieu_doi_tac",
    # DT-2 (28/10/2026): người đặt gửi đơn đặt bàn trên cổng (phiên cổng); tiền thẻ do OnePay báo có chữ ký;
    # Kế toán xác nhận tiền QR / đối soát / chốt doanh số, Sales xác nhận hoàn ở màn /dat-ban-nha-hang.
    "don_dat_ban",
    "thanh_toan_dat_ban",
    # AT-1 (28/10/2026): Điều hành ghi nhận hợp đồng đã ký + tải tệp; Marketing viết món / điểm đến — màn /nha-hang.
    "hop_dong_nha_hang",
    "noi_dung_am_thuc",
    # AT-2a (29/10/2026): Điều hành / Marketing tải ảnh album, TP Điều hành duyệt — màn /nha-hang › Album ảnh.
    "anh_nha_hang",
    # AT-2b (29/10/2026): Điều hành / Marketing nhập món, tải thực đơn theo phiên bản — màn /nha-hang › Món ăn, Thực đơn.
    "mon_nha_hang", "thuc_don_ban", "thuc_don_trang",
    # AT-2c (29/10/2026): Chủ tịch giao người biên tập — màn /nha-hang › Hoàn thiện.
    "bien_tap_nha_hang",
    # AT-3 (29/10/2026): khách tự viết qua cổng (Đơn của tôi › Đánh giá); nhà hàng trả lời qua cổng NCC.
    "danh_gia_nha_hang",
    # KS-13 (30/10/2026): Điều hành nhập khách sạn, ảnh, loại phòng, gói và mùa giá ở màn /khach-san-vtd.
    "khach_san_vtd", "anh_khach_san_vtd", "loai_phong_vtd", "goi_gia_vtd", "mua_gia_vtd",
    # KS-14 (30/10/2026): khách đặt + trả trên cổng (phiên cổng, OnePay / QR khớp mã); Điều hành sửa số phòng bán,
    # chốt với khách sạn; Sales xác nhận hoàn; Kế toán ghi sổ / đối soát / hoàn / chốt hoa hồng — màn /khach-san-vtd.
    "phong_trong_vtd", "don_ks_vtd", "thanh_toan_ks_vtd",
    # KS-15 (30/10/2026): khách đã ở tự viết qua cổng (Phòng đã đặt › Viết đánh giá); khách sạn trả lời qua cổng NCC.
    "danh_gia_ks_vtd",
    # CSKH tự động 25/9/2026. Hai bảng này có cửa nhập THẬT, và cửa ấy khác mọi cửa còn lại của
    # kho: người nhập là KHÁCH HÀNG, qua trang công khai /y-kien/<mã> (API /api/v1/khao-sat).
    # Cửa thứ hai cho khách không dùng Zalo: nhân viên ghi hộ ở màn hình /danh-gia, và bản ghi
    # ấy mang nguon="nhan_vien" để bảng điểm tách được hai loại số.
    "danh_gia_sau_tour", "ma_khao_sat",
    "dependents", "dispatch_orders", "employee_profiles",
    "employees", "fin_contracts", "fin_schedules", "fleet_ai_runs", "fleet_collaterals",
    "fleet_debt_payments",
    # Báo hư hỏng xe, 06/10/2026. Cửa nhập tay là khung "Báo xe hỏng" trên màn hình /xe-hdv của
    # chính tài xế, và khung tương tự trên tab Báo hỏng của /doi-xe cho đội xe ghi hộ khi tài xế
    # gọi điện. CỐ Ý không có bộ nạp tệp: báo hỏng là việc xảy ra từng lần một, ngay lúc nó xảy ra.
    "fleet_faults",
    # HQ-2c (13/10/2026) · ĐỊNH MỨC TIÊU HAO DẦU theo số chỗ. Cửa: khối «Định mức tiêu hao dầu» trên
    # tab Hồ sơ xe của /doi-xe, ghi qua PUT /fleet/dinh-muc-dau (Đội xe · Trưởng phòng ĐH · CNTT).
    # CỐ Ý không có bộ nạp tệp và CỐ Ý không để máy tự sinh: Chủ tịch quyết 13/10/2026 rằng ngưỡng
    # do người khai. Phương án bị loại là lấy trung bình 6 tháng của chính chiếc xe làm mốc — một
    # chiếc hao nhiều SUỐT sáu tháng thì máy coi đó là bình thường, và chiếc hao nhất đội thành
    # chiếc không bao giờ bị cảnh báo. Ngưỡng tự sinh từ chính số liệu nó canh thì không canh gì.
    "fleet_fuel_norms",
    # DX-3 · 16/10/2026 — hai bảng mới.
    #
    # R1 · 17/10/2026 — SỬA LỜI KHAI Ở ĐÂY. Dòng cũ ghi "cả hai đều có màn hình nhập tay trên
    # /doi-xe". Khi viết thì câu ấy KHÔNG ĐÚNG: bảng và cửa API có, nhưng không màn nào gọi hai
    # cửa ghi, nên không ai nhập được. Và không phép thử nào bắt được — `test_man_hinh_co_cua_nhap`
    # đọc màn hình từ GROUPS trong Shell.tsx, nên một cửa ghi không có màn thì nó không thấy.
    # Nay hai màn đã có, và đường dẫn đúng là:
    #   fleet_driver_penalties → /doi-xe/phat-tai-xe  (+ /moi để ghi)
    #   fleet_fuel_prices      → /doi-xe/gia-dau      (+ /moi để ghi)
    #
    # `fleet_driver_penalties`: Giám đốc đội xe ghi (POST /fleet/phat-tai-xe), HCNS đánh dấu đã
    # đối chiếu khi chốt lương. CỐ Ý không có bộ nạp tệp: một khoản trừ vào lương của một con
    # người thì phải có người gõ và người ấy chịu trách nhiệm, chứ không nạp cả tệp một lần.
    #
    # `fleet_fuel_prices`: Kế toán khai giá dầu từng ngày (POST /fleet/gia-dau). Chưa có bộ nạp
    # tệp vì nguồn giá hiện là tra tay theo ngày; khi nào có sao kê giá dạng tệp thì chuyển sang
    # intake.BO_NAP và bỏ dòng này — ghi ra đây để người sau biết đó là việc còn nợ, không phải
    # một lựa chọn đã chốt.
    "fleet_driver_penalties", "fleet_fuel_prices",
    "fleet_maintenance", "fleet_offset_applications", "fleet_partners",
    "fleet_period_costs", "fleet_repayment_installments", "fleet_repayment_plans",
    "fleet_sale_cases", "fleet_settlement_lines", "fleet_settlements", "fleet_shared_invoice_lines",
    "fleet_shared_invoices", "fleet_trip_costs", "fleet_trips", "fleet_verifications",
    "guide_assignments", "guide_rates",
    # Phòng Hướng dẫn, 06-07/10/2026. Năm bảng, năm cửa nhập tay THẬT, không bảng nào máy sinh:
    #   yeu_cau_hdv      – khung "Yêu cầu HDV" trên /huong-dan (Điều hành ĐẶT HÀNG).
    #   bao_cao_sau_tour – khung "Báo cáo sau tour của tôi" trên /xe-hdv (chính HDV nộp), và vòng
    #                      kiểm của TP HD ở thẻ "Báo cáo sau tour" trên /huong-dan.
    #   tam_ung_hdv      – khung Tiền HDV trên /huong-dan; Kế toán ghi số tiền thực nhận/nộp lại.
    #   de_xuat_hdv      – thẻ "Đề xuất" trên /huong-dan.
    #   cau_hinh_duyet_hdv – cùng thẻ ấy: cửa trình cấu hình, và nút công bố của Chủ tịch/TGĐ.
    # CỐ Ý không có bộ nạp tệp cho bảng nào: cả năm là việc xảy ra từng lần một, ngay lúc nó xảy ra,
    # và mỗi dòng cần một người chịu trách nhiệm chứ không phải một tệp tải lên hàng loạt.
    # buoc_duyet_hdv: DÒNG do máy lập (đủ các bước ngay lúc trình), nhưng NỘI DUNG của mỗi dòng —
    # ai quyết, lúc nào, ý kiến gì — là người gõ vào, qua nút Duyệt / Trả bổ sung / Từ chối. Nên nó
    # là cửa nhập tay chứ không phải bảng máy sinh: khai "máy sinh" ở đây là nói sai về chỗ mà chữ ký
    # của Chủ tịch được ghi lại.
    "yeu_cau_hdv", "bao_cao_sau_tour", "tam_ung_hdv", "de_xuat_hdv", "cau_hinh_duyet_hdv",
    "buoc_duyet_hdv",
    "hop_dong_khach", "incidents", "intake_runs", "invoices",
    "journal_entries",
    # TC-73 – cơ cấu tổ chức khối Kinh doanh. Cửa nhập tay ở màn hình /to-chuc-kd: khung "Khai đơn
    # vị mới" và khung "Phân công người vào đơn vị". CỐ Ý KHÔNG có bộ nạp tệp, và cố ý không suy từ
    # `users.sales_group`: ba chuỗi chữ tự do cũ gõ tay suốt bốn năm là thứ hai bảng này sinh ra để
    # thay, chép sang là biến một đống không ai dám tin thành một bảng trông rất đáng tin.
    "don_vi_kd", "phan_cong_kd",
    # TC-81 - KOL / KOC. Cua nhap tay o man hinh /bao-chi-kol: khung "Them KOL" va khung "Ghi mot
    # lan hop tac". CO Y khong co bo nap tep: danh ba nay dung dan tung nguoi mot theo tung dot
    # thuong luong, khong ai co san mot bang Excel 200 KOL de tai len.
    "mkt_kol", "mkt_kol_hop_tac",
    # TC-74 - danh muc doi tac ban hang. Cua nhap tay o man hinh /nguoi-ban-hang.
    "doi_tac_ban_hang",
    # TC-76 - chi tieu doanh thu theo don vi hoac theo nguoi. Cua nhap tay o man hinh
    # /kinh-doanh-le, khung "Giao chi tieu". May KHONG suy duoc bang nay va cung khong duoc
    # phep: chi tieu la dieu nguoi ta QUYET DINH. Suy no tu thuc hien ky truoc la bien thuoc
    # do thanh cai bong cua chinh so bi do - cung ly le da ghi cho ke_hoach_thang ngay duoi.
    "chi_tieu_kd",
    # TC-41 – chỉ tiêu doanh thu và lợi nhuận trước thuế theo tháng × pháp nhân. Cửa nhập tay ở màn
    # hình /ke-hoach-thang. Máy KHÔNG sinh được bảng này và cũng không được phép: kế hoạch là điều
    # người ta QUYẾT ĐỊNH, không phải điều hệ thống đo được. Suy nó từ thực hiện kỳ trước là biến
    # thước đo thành cái bóng của chính số bị đo.
    "ke_hoach_thang",
    "journal_lines", "khoa_ghi", "labor_contracts", "lead_channel_stats",
    "leads",
    # Đơn từ nhân sự. 07/10/2026 — DÒNG NÀY TỪNG NÓI KHÔNG ĐÚNG, ghi lại để lần sau ai đọc cũng
    # thấy. Bảng được khai "có cửa nhập tay" từ bản rà 09/9, trong khi rà cả `web/app` thì KHÔNG
    # một tệp nào gọi `/leaves`: cửa có trên máy chủ, người phải dùng nó không với tới. Đúng loại
    # lệch mà docstring đầu tệp này nói trước là phép thử ở đây không bắt được — nó chỉ biết bảng
    # ĐÃ ĐƯỢC KHAI, không biết màn hình còn sống hay chưa bao giờ có.
    #
    # Cửa thật, từ 07/10/2026: khung "Đơn nghỉ phép / ốm / vắng việc" trên màn hình /xe-hdv, và
    # khung "Đơn chờ bạn ký" ngay dưới nó cho người ký. CỐ Ý không có bộ nạp tệp: đơn nghỉ là việc
    # của từng người một, gửi lúc cần, không ai nạp một tệp đơn nghỉ hàng loạt.
    #
    # CÒN THIẾU và nói ra ở đây: màn hình ấy mới mở cho phòng Đội xe và phòng Hướng dẫn. Người của
    # chín phòng còn lại vẫn chưa có chỗ bấm — cửa máy chủ nhận đơn của họ, nhưng chưa ai dựng ô
    # nhập. Đó là một vòng riêng, không phải thứ sửa kèm ở đây.
    "leave_requests",
    # VPM-9 – lịch thanh toán theo tiến độ của hợp đồng khách. Cửa nhập tay ở màn hình
    # /hop-dong-khach: người soạn chia hợp đồng thành các đợt, gõ số tiền và mốc hạn từng đợt.
    # Máy KHÔNG tự chia được: tiến độ trả tiền là điều hai bên thỏa thuận, không suy ra từ đâu.
    "lich_thanh_toan_hd",
    "messages", "mkt_budget_lines", "mkt_budgets", "page_shifts",
    "params", "partners", "payment_requests", "payroll_runs", "period_locks",
    # VPM-5 – kế toán tự tay chia một khoản tiền cho nhiều booking ở màn hình /collections. Đây đúng
    # là CỬA TAY chứ không phải bảng máy sinh: máy không biết khách định trả cho tour nào, chỉ người
    # đọc nội dung chuyển khoản và nói chuyện với khách mới biết.
    "phan_bo_tien",
    "products",
    "projects", "quy_tac_hach_toan", "receipts", "retentions", "service_orders", "service_requests",
    "supplier_bank_changes", "suppliers", "thieu_gia_von", "tour_cost_lines", "tour_events",
    "tac_vu_tu_dong",
    # Hai bảng dưới đây TỪNG khai nhầm là "máy sinh", và chính lời giải thích đi kèm đã tự nói ra
    # màn hình nào ghi vào chúng – nghĩa là chúng CÓ cửa, chỉ xếp nhầm ngăn. Bộ kiểm KS-7 bắt được
    # 11/9/2026. Xếp nhầm ngăn nguy hiểm hơn là để trống: "máy sinh" nghĩa là KHÔNG AI cần dựng cửa,
    # nên nó đóng luôn câu hỏi thay vì để ngỏ.
    #   prepaid_allocations – màn hình /tai-san, nút ghi sổ phân bổ chi phí trả trước
    #   nhat_ky_giu_cho     – màn hình /bookings, nút gia hạn và nút khôi phục giữ chỗ; ô lý do là
    #                         người gõ, và chính ô ấy làm nó thành dòng do người tạo ra
    "prepaid_allocations", "nhat_ky_giu_cho",
    # Cửa lọc tin khủng hoảng (19/9/2026). Cửa tay ở màn hình /marketing, tab "Thương hiệu & PR":
    # hai nút "Bỏ qua" (bắt buộc gõ lý do) và "Lập dòng PR" trên hàng đợi cảnh báo hộp thư.
    #
    # Xếp vào CỬA TAY chứ không phải MÁY SINH, và khác biệt ấy quan trọng: bảng này không ghi điểm
    # của bộ lọc — điểm chấm lại được bất cứ lúc nào từ tin gốc. Nó ghi KẾT LUẬN CỦA NGƯỜI, thứ
    # không suy ra được từ đâu cả. Gọi nó là "máy sinh" là nói rằng máy tự kết luận được một vụ
    # khủng hoảng, mà đó đúng là điều cả cửa lọc này được dựng ra để KHÔNG làm.
    "mkt_hop_thu_xu_ly",
    # Lớp 3 quyết toán tour (11/9/2026). Năm bảng, cửa API là /api/v1/quyet-toan-lop3
    # (app/api/v1/quyet_toan_lop3.py), gắn vào màn hình "Quyết toán tour" đã có:
    #   POST .../{tid}/khach            – dòng khách, có ngày sinh
    #   POST .../{tid}/khach-chi-phi    – chi phí đích danh của khách (vé, visa, quà)
    #   POST .../{tid}/doanh-thu        – dòng doanh thu, kể cả dòng âm theo biên bản thanh lý
    #   POST .../{tid}/phuong-tien      – từng chặng ô tô / máy bay / tàu
    #   POST .../{tid}/hdv-chi          – HDV chi trên đường
    #
    # Không cửa nào nhận ô "tổng": máy nhân đơn giá × số lượng rồi cộng thuế, và máy cộng các dòng.
    # Đó là cách chặn đúng lỗi 210.000 đ tìm thấy trên tệp mẫu Nha Trang.
    "booking_khach", "khach_chi_phi", "tour_doanh_thu_dong", "tour_phuong_tien", "tour_hdv_chi",
    # Đ-8 · Đ-9 (13/9/2026). Bốn bảng của khối vé và tờ công nợ trưởng đoàn, cả bốn đều có cửa
    # nhập tay trên chính biểu quyết toán (web/components/QuyetToanForm.tsx, khối 7a–7c và 8):
    #   POST .../{tid}/ve/ma           – mã đặt chỗ; KHÔNG có ô tiền nào ở đây
    #   POST .../{tid}/ve/khach        – vé của từng khách; máy cộng bốn ô tiền thành thành tiền
    #   POST .../{tid}/ve/thanh-toan   – các đợt trả tiền đại lý vé; chỉ trừ dần vào nợ
    #   POST .../{tid}/tl-cong-no      – từng dòng công nợ trưởng đoàn, mỗi dòng một đồng tiền
    #
    # KHÔNG bảng nào ở đây là "máy sinh". Đặc biệt tour_ve_ma: nghe như thứ máy có thể suy ra từ
    # cột ma_dat_cho của dòng khách, nhưng hạn xuất vé và số chỗ đã giữ thì không ở đâu suy ra
    # được – chúng là điều đại lý báo qua điện thoại.
    "tour_ve_ma", "tour_ve_khach", "tour_ve_thanh_toan", "tour_tl_cong_no",
    # Đ-4 · Đ-12 (13/9/2026). Bốn bảng, bốn cửa nhập tay:
    #   POST .../{tid}/ben-ban            – một bên bán ghép land; Vietourist cũng là một dòng
    #   POST .../{tid}/ben-ban/dong       – dòng phân bổ / hoàn tip / thanh toán của bên ấy
    #   POST .../lanh-su                  – mở tờ đề nghị chi phí lãnh sự
    #   POST .../lanh-su/{did}/dong       – một khách trên tờ đề nghị
    #
    # KHÔNG bảng nào ở đây là "máy sinh". Riêng `tour_ben_ban` nghe như thứ máy suy được từ cột
    # `nhom_khach = "dai_ly"` của dòng khách, nhưng nhãn ấy chỉ nói "khách này của một đại lý nào
    # đó" – nó KHÔNG nói của đại lý nào, và một chuyến ghép có tới ba bên.
    "tour_ben_ban", "tour_ben_ban_dong",
    "de_nghi_lanh_su", "de_nghi_lanh_su_dong",
    # V7 Đợt 3 (10/9/2026). Cả năm bảng đều có màn hình nhập tay:
    #   /su-co-tour        – ghi sự cố, ghi từng bước xử lý
    #   /ho-so-kiem-toan   – lập hồ sơ, thêm mục danh mục, ghi điều chỉnh kiểm toán đề nghị
    # KHÔNG khai bảng nào trong nhóm này là "máy sinh": sự cố là lời người ở hiện trường kể lại, và
    # danh mục kiểm toán là thứ kiểm toán viên hỏi – máy không biết trước cả hai.
    "su_co_tour", "su_co_tour_xu_ly", "ho_so_kiem_toan", "ho_so_kiem_toan_muc",
    "ho_so_kiem_toan_dieu_chinh",
    # Robot A · 16/9/2026. SỔ TỶ GIÁ. Cửa nhập tay ở màn hình /ty-gia, API /api/v1/ty-gia:
    #   POST /api/v1/ty-gia        – một đồng tiền, một ngày, một nguồn
    #   PUT  /api/v1/ty-gia/{id}   – sửa, bắt buộc có lý do, số cũ vào `lich_su`
    #
    # KHÔNG khai là "máy sinh", dù nghe như thứ máy lấy được từ trang ngân hàng. Chủ tịch chốt
    # 16/9/2026: *"tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên tự nhập tay
    # và tải tệp/ảnh."* Và có lý do thật: tỷ giá dùng cho một khoản là tỷ giá NGÀY CHI THẬT của
    # khoản ấy, có khi là giá niêm yết, có khi là giá thực tế đã chuyển khoản, có khi là giá ghi
    # trong hợp đồng với đối tác – ba con số khác nhau mà chỉ người lập chứng từ biết dùng cái nào.
    # Máy kéo về một con số rồi nhân vào tiền là chọn hộ cái không được chọn hộ.
    "ty_gia",
    "tours", "user_grants", "users", "vehicle_documents", "vehicle_plates", "vehicle_rates",
    "vehicles", "visa_access_links", "visa_ai_suggestions", "visa_applications",
    "visa_appointments", "visa_cases", "visa_checklist_items", "visa_checklist_templates",
    "visa_customer_confirmations", "visa_document_reviews", "visa_document_versions",
    "visa_family_groups", "visa_files", "visa_form_versions", "visa_handovers", "visa_markets",
    "visa_results", "visa_tasks", "visa_waiver_requests", "vt_records", "zalo_messages",
    "zalo_oa_tokens",
)


# Máy sinh – bảng KHÔNG cần cửa nhập, kèm lý do. Xem ghi chú đầu tệp: không viết được lý do nghĩa là
# chưa chắc nó máy sinh.
MAY_SINH = {
"buoc_don_ota": "Nhật ký từng bước của đơn phòng OTA (KS-10) – hệ thống ghi một dòng mỗi lần Điều hành gọi một bước, kể cả lần quá hạn. KHÔNG có cửa nhập tay là TÍNH CHẤT AN TOÀN: gõ tay được vào sổ này thì dựng được một lần gọi chưa ai làm, mà đó đúng là thứ nó sinh ra để chống — câu «Agoda đã nhận đơn chưa» chỉ có sổ này trả lời.",
    # BC-1 26/10/2026. Bản chụp mỗi lần nộp báo cáo ngày — hệ thống tự ghi đúng lúc người nộp bấm
    # «Nộp». Không có cửa sửa là TÍNH CHẤT AN TOÀN: sửa được bản lần đầu thì đổi được câu trả lời cho
    # «lần đầu nộp đã ghi gì, lúc nào».
    "so_diem_rewards": "Sổ điểm VTD Rewards (KH-3) – chỉ ghi thêm; máy đối chiếu booking đủ điều kiện và ghi phần chênh, voucher giữ / trả điểm; không có cửa sửa số dư.",
    "ky_hoa_hong": "Kỳ hoa hồng D06 (DH-1) – máy dựng khi Kế toán bấm Tính lại, từ booking đủ điều kiện; số trên kỳ là bản đọc nhanh của sổ, không có cửa gõ số.",
    "so_hoa_hong": "Sổ hoa hồng D06 (DH-1) – chỉ ghi thêm phần chênh mỗi lần tính lại; không có cửa sửa hay xoá để quyền hưởng đã ghi không bị viết lại.",
    "chi_hoa_hong": "Liên kết kỳ hoa hồng với đề nghị chi (DH-1) – hệ thống ghi khi Kế toán bấm Lập đề nghị chi; số tiền do máy tính từ sổ.",
    "ma_xac_thuc_ngoai": "Mã một lần của cổng kết nối (CG-1) – hệ thống sinh khi người dùng bấm Nhận mã; lưu dạng băm, không ai nhập tay.",
    "daily_report_reviews": "Sổ xem xét báo cáo ngày (BC-2) – hệ thống ghi một dòng mỗi lần người xem bấm «Đã xem» hoặc «Yêu cầu bổ sung»; không có cửa sửa để dấu trả bổ sung không bị xoá.",
    "daily_report_versions": "Bản chụp mỗi lần nộp báo cáo ngày (BC-1) – hệ thống ghi lúc người nộp bấm Nộp; không có cửa sửa để lần nộp đầu không bị viết lại.",
    # CN-2 (21/10/2026) · BẢNG LƯƠNG BỔ SUNG. Máy lập từ đúng bộ tính lương (`hr.compute_draft`) cho
    # những người bị giữ lúc ký bảng chính; HCNS chỉ bấm «Lập», rồi kiểm và trình như bảng chính.
    # KHÔNG có cửa gõ dòng lương là TÍNH CHẤT AN TOÀN: gõ tay được vào bảng này thì trả được một
    # khoản lương không qua bộ tính nào, mà bảng chính cũng không có cửa ấy.
    "bang_luong_bo_sung": "Bảng lương bổ sung do máy lập từ bộ tính lương cho người bị giữ lương (CN-2) – HCNS bấm lập, kiểm, trình; không có cửa gõ dòng lương, cùng luật với bảng chính.",
    "su_kien_thu_nhap": "Sổ ghi khoản thu nhập đã KÝ, do services/luong_khoa.khoa ghi đúng lúc có chữ ký. Không có cửa là TÍNH CHẤT AN TOÀN, không phải việc còn thiếu: gõ tay được vào sổ này thì xoá được dấu vết một lần đã trả, mà đó đúng là thứ nó sinh ra để giữ.",
    "buoc_da_lam": "Dấu chân tách bạch trách nhiệm — hệ thống tự ghi đúng lúc một bước nghiệp vụ hoàn thành. KHÔNG có cửa nhập tay là TÍNH CHẤT AN TOÀN, không phải việc còn thiếu: gõ tay được vào sổ này thì dựng được một dấu chân cho một bước chưa ai làm, mà đó đúng là thứ nó sinh ra để chống.",
    "ai_runs": "Nhật ký robot chạy – hệ thống tự ghi, không ai nhập tay.",
    # DL-2 (13/10/2026) · SỔ GHI TỪNG LẦN SỐ KHÁCH ĐỔI. Hệ thống tự ghi một dòng mỗi lần ai đó sửa
    # qua cửa thật (PUT /de-nghi-xe/{id}/so-khach, màn hình Lệnh điều xe). KHÔNG có cửa nhập tay là
    # TÍNH CHẤT AN TOÀN, không phải việc còn thiếu: gõ tay được vào sổ này thì dựng được một lịch
    # sử nói rằng số khách đã đổi từ lâu — mà câu hỏi sổ này sinh ra để trả lời là "lúc lập lệnh
    # thì đề nghị ghi bao nhiêu khách", và một câu trả lời sửa được thì không trả lời gì cả.
    "fleet_vehicle_request_pax_log": "Sổ ghi từng lần số khách của đề nghị xe đổi – hệ thống tự ghi "
                                     "khi người dùng sửa qua cửa, không gõ tay được. Xem DL-2.",
    # Đợt E7 13/10/2026. KHÔNG CÓ CỬA NHẬP TAY LÀ MỘT TÍNH CHẤT AN TOÀN, không phải việc còn
    # thiếu — đúng hình với `bang_luong_khoa` ở dưới. Gõ tay được số cuối của một ký hiệu thì lùi
    # được bộ cấp số, và lùi bộ cấp số là cấp lại một số đã in ra giấy, tức làm ra hai tờ hóa đơn
    # mang một số. Đó đúng là thứ bảng này sinh ra để chống.
    "so_nhay_hoa_don": "Số cuối đã CẤP của từng ký hiệu hóa đơn, do services/hoa_don_so.cap_so "
                       "tăng đúng lúc cấp số. Gõ tay được vào đây là lùi được bộ cấp số, tức cấp "
                       "lại một số đã in ra giấy — hai tờ hóa đơn mang một số.",
    "ks_bao_cao": "Báo cáo robot Kiểm soát tự lập.",
    "ks_cot_tien": "Cột tiền robot Kiểm soát tự dựng từ sổ.",
    "ks_diem": "Điểm chấm tự tính, không nhập tay.",
    "ks_phat_hien": "Phát hiện của robot – tự ghi.",
    "ngoai_le_xu_ly": "Ngoại lệ do bộ nạp tự đẩy ra.",
    "su_kien_ky_thuat": "Sự kiện kỹ thuật – hệ thống tự ghi.",
    # V11 – lịch tự động hóa. Sổ lần chạy do hệ thống chạy tác vụ BÁO VỀ (n8n hoặc chính vòng lặp
    # trong VTOS), qua POST /tu-dong/bao-cao. Người không gõ tay dòng nào ở đây, và KHÔNG NÊN gõ: một
    # dòng "đã chạy thành công" nhập tay là bằng chứng giả về một việc có thể chưa hề chạy.
    #
    # Ngược lại, bảng KHAI BÁO tác vụ (tac_vu_tu_dong) thì phải do người khai – nằm ở CUA_TAY, màn
    # hình /tu-dong-hoa. Hai bảng đi cùng nhau nhưng khác hẳn về cửa, và đó chính là thiết kế của
    # V11: máy tự khai tác vụ thì mất khả năng phát hiện tác vụ đã ngừng chạy.
    "lan_chay_tac_vu": "Lần chạy do hệ thống chạy tác vụ báo về qua /tu-dong/bao-cao – nhập tay một "
                       "dòng 'đã chạy thành công' là tạo bằng chứng giả về việc có thể chưa hề chạy.",
    # Đợt A1 bảng lương, 07/10/2026. Bản chụp kỳ lương lúc có chữ ký. KHÔNG CÓ CỬA LÀ MỘT TÍNH CHẤT
    # AN TOÀN, không phải việc còn thiếu: nếu người gõ tay được vào đây thì bản chụp giả được, mà bản
    # chụp giả được thì nó không chứng minh nổi điều duy nhất nó sinh ra để chứng minh — rằng đây đúng
    # là con số người ký đã nhìn. Người không nhập bản chụp; người bấm "ký", và máy ghi lại thứ họ ký.
    "bang_luong_khoa": "Bản chụp kỳ lương do máy ghi đúng lúc có chữ ký (services/luong_khoa.khoa). "
                       "Gõ tay được vào đây là làm giả được bằng chứng của một chữ ký.",
    "tong_dai_su_kien": "Nhật ký nguyên văn webhook tổng đài – tổng đài ghi vào, không ai nhập tay.",
    # 08/10/2026 · Hai bảng của TC-103 và TC-105. Không có cửa nhập tay là CHỦ Ý, và lý do nằm ở
    # chỗ: số ở đây không phải số của Vietourist, nó là số của Google / Meta / TikTok / Zalo.
    # Gõ tay một dòng dấu quảng cáo là bịa ra một lần khách chạm chưa từng xảy ra; mà dấu ấy sau
    # đó được đẩy NGƯỢC lên nền tảng như một chuyển đổi thật, tức là tự dạy nền tảng tối ưu sai
    # rồi trả tiền thật cho nó. Đây đúng loại "nhập hộ vào cơ sở dữ liệu" mà ranh giới 09/9/2026
    # cấm, chứ không phải một cửa còn thiếu.
    "dau_quang_cao": "Lần chạm giữa khách và một kênh quảng cáo. Nền tảng ghi vào qua webhook "
                     "hoặc qua cửa máy chủ POST /dau-quang-cao/nhan; người KHÔNG tạo được dòng "
                     "mới. Người chỉ gắn lại một dấu đã có vào đúng lead khi máy khớp sai "
                     "(POST /dau-quang-cao/{did}/gan-lead) – sửa liên kết, không nhập số liệu.",
    "chuyen_doi_gui_di": "Hàng đợi báo ngược doanh thu về nền tảng, do services/chuyen_doi_di.sinh "
                         "dựng từ dấu đã khớp lead và booking đã chốt. Gõ tay một dòng ở đây là "
                         "báo cho Meta hoặc TikTok một đơn hàng không có thật.",
    # 28/9/2026. Ảnh chụp công nợ khách theo Vietrip. Số là của VIETRIP, do lịch chạy 8h sáng đọc từ
    # Vietrip rồi đẩy vào qua POST /cong-no-vietrip/nap. Gõ tay một dòng ở đây là bịa ra một con số
    # Vietrip chưa từng nói – muốn sửa số thì sửa ở Vietrip, sáng hôm sau ảnh mới tự thay.
    "cong_no_vietrip_anh": "Ảnh chụp công nợ do lịch chạy 8h sáng nạp từ Vietrip qua /cong-no-vietrip/nap "
                           "– số của Vietrip, không nhập tay.",
    "cong_no_vietrip_dong": "Dòng của ảnh chụp công nợ Vietrip – nạp cùng ảnh, không nhập tay.",
    # 07/10/2026. Cặp bảng SONG SINH với hai dòng ngay trên, và khai muộn hơn đúng một tuần – nên bộ
    # soát `test_cn1` đỏ trên main suốt từ đó: hai bảng có người ghi mà chưa ai KHAI là ai ghi.
    #
    # Khai MÁY SINH ở đây là nói đúng sự thật, không phải để cho phép thử xanh. Số là của VIETRIP,
    # đọc từ trang Quyết toán tour (khối "Thống kê thu chi": Tổng chi dự toán · Thực tế đã chi · Còn
    # phải chi) rồi đẩy vào qua POST /api/v1/cong-no-vietrip/nap-phai-tra – đúng một đường, đúng một
    # hình với /cong-no-vietrip/nap của cặp công nợ khách. `con_phai_chi` do MÁY CHỦ tính
    # (tong_chi − da_chi) và tour hết nợ thì bỏ, nên không có chỗ nào cho một con số gõ tay chen vào
    # mà vẫn nhất quán.
    #
    # Vì sao KHÔNG mở cửa nhập tay: đây là ảnh chụp số của một hệ thống khác vào một ngày. Gõ tay một
    # dòng là bịa ra một con số Vietrip chưa từng nói, và cái ảnh ấy mất hẳn công dụng duy nhất của
    # nó – làm chứng cứ để SO. Muốn sửa số thì sửa trên Vietrip, sáng hôm sau ảnh tự thay.
    "phai_tra_vietrip_anh": "Ảnh chụp phải trả NCC theo dự toán tour, nạp từ Vietrip qua "
                            "/cong-no-vietrip/nap-phai-tra – số của Vietrip, không nhập tay.",
    "phai_tra_vietrip_dong": "Dòng của ảnh chụp phải trả Vietrip – nạp cùng ảnh; con_phai_chi do máy "
                             "chủ tính, không nhận từ bên gửi.",
    # Nối tài khoản Zalo (19/9/2026). Hai bảng, và CẢ HAI đều máy sinh — nhưng vì hai lý do khác
    # nhau, nên chép ra đây cả hai chứ không gộp một dòng:
    #
    #   · zalo_ma_noi         – mã do máy sinh ngẫu nhiên khi người dùng bấm "xin mã" ở màn hình
    #                           /doi-mat-khau. Người KHÔNG được gõ mã vào: một mã nhập tay là một
    #                           mã có người thứ hai biết, và cả tính an toàn của việc nối nằm ở chỗ
    #                           chỉ chính chủ nhìn thấy nó.
    #   · zalo_noi_tai_khoan  – UID do ZALO nói ra qua webhook khi chính người ấy nhắn mã vào OA.
    #                           Mở cửa nhập tay ở đây là mở lại đúng cái lỗ mà thiết kế này sinh ra
    #                           để bịt: một người gõ nhầm UID thì cảnh báo của Chủ tịch đi tới máy
    #                           người khác, và không ai biết.
    # Sổ gửi báo động (19/9/2026). MÁY SINH, và phải là máy sinh: mỗi hàng là dấu vết của một
    # lần gửi thật — ai, kênh nào, thành công hay không, vì sao không. Mở cửa nhập tay ở đây là
    # cho phép sửa nhật ký, mà nhật ký sửa được thì phép đo cuối tháng không còn là phép đo.
    "canh_bao_gui": "Nhật ký gửi thật; nhập tay được nghĩa là sửa được dấu vết, và phép đo mất nghĩa.",
    "zalo_ma_noi": "Mã nối do máy sinh ngẫu nhiên; nhập tay là để lộ mã cho người thứ hai.",
    "zalo_noi_tai_khoan": "UID do Zalo nói ra qua webhook khi chính chủ nhắn mã; gõ tay UID là mở "
                          "đường cho cảnh báo đi nhầm người.",
    # Bình luận công khai Fanpage (19/9/2026). Facebook đẩy sang qua webhook trường `feed`; người
    # KHÔNG gõ tay dòng nào, và không nên: một bình luận nhập tay là lời của một người có thật bị
    # người khác viết hộ, và sáu tháng sau không ai phân biệt nổi dòng nào là thật.
    #
    # Dòng vào bảng này rồi thì việc của NGƯỜI bắt đầu ở hàng đợi cảnh báo (bảng mkt_hop_thu_xu_ly,
    # nằm ở CỬA TAY) – chỗ người đọc và kết luận. Hai bảng đi cùng nhau, khác hẳn về cửa.
    "mkt_fb_binh_luan": "Bình luận dưới bài đăng Fanpage – Facebook đẩy sang qua webhook trường "
                        "feed. Nhập tay một bình luận là viết hộ lời của một người có thật.",
    # Lớp 3 quyết toán tour (11/9/2026). Sổ dấu vết sửa sau khi ký: hệ thống ghi khi người bấm sửa
    # một tờ đã ký, và KHÔNG được có cửa nhập tay. Một sổ dấu vết mà người ta gõ thẳng vào được thì
    # không còn là dấu vết – ai cũng viết được rằng mình đã sửa vì lý do gì, kể cả khi không sửa.
    #
    # Cùng lý lẽ ấy nên cũng không có cửa XOÁ: sửa sai thì sửa tiếp và ghi tiếp.
    "sua_sau_ky": "Sổ dấu vết sửa tờ quyết toán sau khi ký – hệ thống ghi khi người bấm sửa; có cửa "
                  "nhập tay thì không còn là dấu vết.",
    # Cùng lý lẽ với lan_chay_tac_vu, và ở đây còn gắt hơn: bao_cao_luu là ẢNH CHỤP số liệu tại một
    # thời điểm đã qua. Cho người nhập tay vào đây là cho phép viết lại quá khứ – đúng thứ mà một bản
    # chụp sinh ra để chống. Bản chụp chỉ do lịch tự động sinh, từ chính hàm mà màn hình đang gọi.
    # VPM-7 – nhật ký giữ chỗ. Mỗi dòng do MỘT hành động sinh ra: robot trả chỗ về, hoặc người bấm gia
    # hạn / khôi phục ở màn hình /bookings (ở đó lý do là ô người gõ, và đó mới là cửa nhập thật). Cho
    # nhập tay thẳng vào bảng này là cho phép bịa ra một lần gia hạn chưa từng có ai ký.
    # VPM-11 – sổ nghĩa vụ thanh toán. Đây là LỚP ĐỌC dựng lại từ sáu bảng chứng từ gốc, mỗi bảng đều
    # đã có cửa nhập riêng ở trên (payment_requests, service_orders, fin_schedules,
    # lich_thanh_toan_hd, bookings, cash_plan_items). Người nhập ở chứng từ gốc, không nhập ở đây –
    # và KHÔNG ĐƯỢC nhập ở đây: một dòng nghĩa vụ gõ tay là một khoản nợ không có chứng từ nào đứng
    # sau, đúng thứ mà việc chống đếm trùng sinh ra để loại.
    "nghia_vu_thanh_toan": "Sổ nghĩa vụ do phép đồng bộ dựng lại từ sáu bảng chứng từ gốc, mỗi bảng "
                           "đã có cửa nhập riêng – nhập tay vào đây là tạo một khoản nợ không có "
                           "chứng từ nào đứng sau.",
    "bao_cao_luu": "Ảnh chụp bảng chỉ tiêu do lịch tự động lưu mỗi kỳ, sinh từ chính hàm màn hình "
                   "gọi – nhập tay vào đây là viết lại quá khứ, đúng thứ bản chụp sinh ra để chống.",
    # TC-83 (24/9/2026) – bia mộ tài khoản đã xoá. Hệ thống ghi đúng MỘT dòng ở đây mỗi lần có người
    # bấm xoá một tài khoản, ngay trước khi hàng ở `users` biến mất. Không có cửa nhập tay, và cũng
    # KHÔNG CÓ CỬA XOÁ: nhật ký nghiệp vụ ghi người làm bằng tên đăng nhập dạng chữ, nên bảng này là
    # thứ duy nhất tra ngược được `nv.thao` trong một dòng nhật ký ba tháng trước ra người nào. Mở
    # cửa nhập tay ở đây là cho phép khai một lần xoá chưa từng xảy ra; mở cửa xoá là bịt lại đúng
    # cái lỗ mà bảng này sinh ra để vá.
    "tai_khoan_da_xoa": "Bia mộ do chính thao tác xoá tài khoản ghi ra, ngay trước khi hàng ở users "
                        "biến mất – nhập tay là khai một lần xoá chưa từng xảy ra.",
    # HD-Q2a · 16/10/2026 — SỔ ĐẾM LƯỢT MỞ CỬA ĐỌC. `services/dem_luot.ghi` viết một dòng mỗi khi
    # có người mở một trong năm cửa đọc của phân hệ Đánh giá và Chăm sóc khách. KHÔNG CÓ CỬA NHẬP
    # TAY LÀ MỘT TÍNH CHẤT AN TOÀN, không phải việc còn thiếu: bảng này sinh ra để trả lời đúng
    # một câu — AI THẬT SỰ ĐANG ĐỌC — và Chủ tịch sẽ dựa vào chính con số ấy để thu hẹp quyền đọc
    # của Marketing và Điều hành (Đợt HD-Q2b). Gõ tay được vào đây thì một phòng sắp bị siết quyền
    # tự ghi thêm lượt đọc cho mình, và phép đếm mất đúng công dụng duy nhất của nó.
    #
    # Cùng lý lẽ ấy nên cũng KHÔNG có cửa XOÁ. Bảng không ghi một chữ nào về khách — chỉ tên đăng
    # nhập, vai trò, tên cửa và số đếm; xem đầu tệp `services/dem_luot.py`.
    "luot_doc_cua": "Sổ đếm lượt mở cửa đọc do services/dem_luot.ghi viết khi người dùng mở cửa — "
                    "nhập tay được là tự ghi thêm lượt đọc cho chính mình, đúng lúc trước khi con "
                    "số ấy được dùng để quyết phạm vi quyền đọc.",
}


def _bang_mo_hinh() -> set[str]:
    import app.main  # noqa: F401 – nạp trọn mô hình, nếu không thì chỉ thấy vài bảng tình cờ nạp trước
    from app.db.session import Base
    return {t for t in Base.metadata.tables} - {"alembic_version"}


def cua_tai_tep() -> dict[str, list[str]]:
    """{bảng đích: [mã bộ nạp]} – đọc SỐNG từ sổ bộ nạp, không chép lại."""
    from app.services.intake import BO_NAP
    ra: dict[str, list[str]] = {}
    for ma, bo in BO_NAP.items():
        b = bo.get("bang_dich")
        if b: ra.setdefault(b, []).append(ma)
        # Một bộ nạp có thể đổ vào nhiều bảng: tệp quyết toán chi tiết của Điều hành ghi vào năm
        # bảng từ bốn sheet. bang_dich giữ bảng chính, bang_phu giữ phần còn lại – đọc cả hai, nếu
        # không thì bốn bảng kia bị báo là không có cửa trong khi chúng đi qua đúng bộ nạp này.
        for p in (bo.get("bang_phu") or ()):
            ra.setdefault(p, []).append(ma)
    return ra


def bang(db: Session | None = None) -> dict:
    mo = _bang_mo_hinh()
    tep = cua_tai_tep()
    khong_cua = sorted(b for b in mo if b not in tep and b not in CUA_TAY and b not in MAY_SINH)
    return {
        "so_bang": len(mo),
        "co_cua_tep": sorted(b for b in mo if b in tep),
        "co_cua_tay": sorted(b for b in mo if b in CUA_TAY),
        "may_sinh": sorted(b for b in mo if b in MAY_SINH),
        "khong_cua": khong_cua,
        # Dòng khai cho bảng không còn trong mô hình. Không phải lỗi – nhánh chưa gộp thì bảng chưa có.
        "khai_thua": sorted((set(CUA_TAY) | set(MAY_SINH)) - mo),
    }


def quet(db: Session) -> list[dict]:
    b = bang(db)
    return [{"ma": f"bang_khong_cua_nhap#{t}", "loai": "bang_khong_cua_nhap", "muc": "vang",
             "phong_ban": "Công nghệ thông tin", "vai_tro": "cntt", "doi_tuong": t,
             "tom_tat": f"Bảng “{t}” không có cửa nào để người dùng đưa số liệu vào – không bộ nạp tệp, "
                        f"không màn hình nhập tay, và cũng chưa khai là bảng máy sinh. Theo ranh giới "
                        f"09/9/2026 thì đây là việc CÒN THIẾU, không phải chỗ để nhập hộ vào cơ sở dữ liệu",
             "chi_tiet": {"bang": t}}
            for t in b["khong_cua"]]


def _cua_nhap_du_lieu(db: Session) -> list[dict]:
    """Cửa vào cho BO_KIEM của robot."""
    return quet(db)
