# VTOS – Giai đoạn 2.1: Phân hệ Thu tiền (robot R1 – SePay) – 05/9/2026

**Trạng thái:** đã code, test (14/14 pass), push GitHub (commit 2630a94, 879a634), Vercel + Render tự triển khai. Tab **Thu tiền** đang chạy tại https://vtos.infinitytours.org (= https://vtos-platform.vercel.app).

## Quy tắc robot R1 (theo mục 7.1 Thiết kế v1.7)
- Webhook SePay `POST /api/v1/sepay/webhook` (header `Authorization: Apikey <SEPAY_WEBHOOK_KEY>`), idempotent theo id giao dịch SePay.
- Giao dịch ngân hàng là **bản ghi bất biến** (bảng `bank_transactions`, không sửa/xóa).
- Tiền vào: tìm mã `BKxxxxxxxx` trong nội dung CK. Khớp **tuyệt đối** mã + số tiền còn phải thu → sinh phiếu thu tự động (`tu_dong`), booking.paid cập nhật. Không mã / mã sai / lệch tiền → `cho_ke_toan` kèm ghi chú lý do.
- Tiền ra → `bo_qua` (theo dõi ở phân hệ chi, giai đoạn sau).
- Kế toán: **Gán & lập phiếu thu** (thu một phần/thu dư/sai nội dung, ghi chú bắt buộc), **Bỏ qua** (có lý do), **Xác nhận** phiếu thu robot, **Lập phiếu thu tiền mặt**.
- Phiếu thu mã `PTyymm-nnnn` (mẫu 01-TT, TT99/2025). Mọi thao tác ghi audit hash-chain.
- Phân quyền: ketoan (mọi thao tác), cntt (gán/bỏ qua), các vai trò khác chỉ xem.

## Màn hình Thu tiền
4 KPI (còn phải thu, booking chưa thu đủ, giao dịch chờ KT, phiếu thu chờ xác nhận) → hàng chờ giao dịch SePay (lọc Chờ KT / Đã khớp / Bỏ qua / Tất cả) → danh sách phiếu thu → form thu tiền mặt (chỉ Kế toán) → công nợ phải thu theo booking.

## Việc anh Tuấn cần làm để chạy thật với SePay
1. Render → `vtos-api` → Environment → copy `SEPAY_WEBHOOK_KEY` (Blueprint tự sinh).
2. my.sepay.vn → Webhooks → thêm: URL `https://vtos-api.onrender.com/api/v1/sepay/webhook`, chứng thực API Key = `Apikey <key>`, sự kiện tiền vào.
3. Gửi thử từ SePay → tab Thu tiền hiện giao dịch.
(Chi tiết: `docs/trien-khai-infinitytours.md` trong repo.)

## Tiếp theo (giai đoạn 2.2+)
Kế toán TT99 + hóa đơn điện tử → thang lương f, visa, HDV, đội xe → báo cáo ngày, ca trực.

---
# Giai đoạn 2.2: Kế toán TT99/2025 + Hóa đơn điện tử (robot R2) – 05/9/2026

- Hệ thống tài khoản rút gọn cho lữ hành (111, 112, 131, 133, 154, 331, 3331, 335, 3387, 511, 632, 641, 642, 911…), bổ sung dần.
- Bút toán tự động: Kế toán xác nhận phiếu thu → Nợ 111/112 – Có 131; phát hành hóa đơn → Nợ 131 – Có 511 + 3331; Kế toán xác nhận quyết toán tour → Nợ 154 – Có 331, Nợ 632 – Có 154. Mã KM là dòng giá vốn quản trị nội bộ, không ghi sổ kế toán.
- Chứng từ ghi sổ bất biến: sai thì lập bút toán đảo (có lý do). Kế toán lập chứng từ tay → nháp → ghi sổ; cổng chặn không cân Nợ/Có.
- Sổ cái theo TK (S03b), Bảng cân đối số phát sinh (S06) theo kỳ; khóa kỳ (chặn khi còn nháp; kỳ khóa không ghi sổ).
- Hóa đơn GTGT từ booking: giá đã gồm thuế, tách thuế theo tham số `thue_gtgt` (mặc định 10%, Kế toán chỉnh theo mức giảm thuế hiện hành hoặc nhập riêng từng hóa đơn); ký hiệu 1C26TVT; hủy → bút toán đảo. Adapter `noi_bo` cấp số – khi ký nhà cung cấp HĐĐT thay adapter gọi API.
- Trang web tab **Kế toán** (5 mục). Test: 6 kịch bản; tổng 20 test pass. Migration 932fede91a23.

---
# Giai đoạn 2.3: Nhân sự – Lương (robot R6) – 05/9/2026

- Hồ sơ nhân sự (phòng, chức danh, văn phòng, HĐLĐ/CTV, lương công việc, thử việc 85%, thẻ HDV/hội viên/hợp đồng CTV), gắn tài khoản đăng nhập.
- Bảng lương tháng theo mục 6.4 Thiết kế v1.7, tính từ chuyến Kế toán đã xác nhận trong tháng (tháng quyết toán):
  - KD Lẻ: thang giảm Phụ lục C (mỗi 20 triệu/12 triệu dưới mốc −700k NV / −800k TL / −1 triệu TP, tới 0); hoa hồng thang f0–f19 × (DT tính chỉ tiêu − mốc), trần 5% từ 1000%; booking thiếu 4 trường không tính; chuyến duyệt chạy dưới biên → 10% LN booking; mã KM tính theo DT đã giảm; sự vụ ≥ mức 2 −1 triệu/vụ chỉ trừ hoa hồng; Cần Thơ +10% LN đoàn tự chốt; GĐ KD +3/+6 triệu theo % NV đạt chỉ tiêu (phần % LN Công ty nhập tay khi TGĐ duyệt).
  - KD Đoàn: hoa hồng 10% × (LN đoàn tháng − 20 triệu); thang lương f9–f0 theo bình quân LN 3 tháng / mốc 30 triệu; PTGĐ 5% (−0,5 điểm/tiêu chí sự vụ), Sale Admin 2%.
  - Điều hành: quỹ 2%/1%/1% chia 70/30. Ban Visa: quỹ 200k/50k (+300k liên minh) theo tháng hoàn thành, HCM chia đều, Hà Nội riêng.
  - HDV CTV: đơn giá tuyến × ngày (lễ ×2), TNCN 10%, treo khi thiếu báo cáo tour/chưa hoàn ứng; cổng 13 chặn phân chuyến khi thẻ hết hạn/không hội viên/chưa ký HĐ CTV.
  - Tài xế: công tác phí 200k × ngày tour từ lệnh điều xe (xác nhận 4 giờ); Đội xe = trung tâm lợi nhuận (doanh thu nội bộ theo bảng giá xe).
- Luồng: robot nháp → Kế toán xác nhận cơ sở → HCNS lập → TGĐ ký lô → bút toán Nợ 642/Có 334, Nợ 632/Có 338 (CTV), Nợ 338/Có 3335 (TNCN).
- **Chờ anh nạp tham số:** Bảng B.1 ngưỡng bậc f0–f19 (hiện tạm 100% + 45%×k mốc), đơn giá HDV 23 tuyến (nhập khi phân công), bảng giá xe nội bộ (nhập ở hồ sơ xe), bảng phân mức sự vụ chung.
- Trang web tab **Nhân sự – Lương** (6 mục). Test: 6 kịch bản; tổng 26 test pass. Migration 856b08720cb7.

---
# Giai đoạn 2.4: Báo cáo ngày (Điều 12) · Ca trực page (cổng 11) · Đề nghị chi – Lệnh chi (robot R3, cổng 14/15) – 05/9/2026

- **Báo cáo ngày**: nộp 4 phần trên VTOS trước 20:00 (Thứ Hai–Thứ Bảy) cho khối KD Lẻ, Đoàn, Điều hành, Marketing, CNTT; robot chấm nháp 0–10 (mỗi phần ≥ 20 ký tự = 2 điểm, đúng giờ = 2); trưởng phòng chấm chính thức (không sửa sau khi chấm); tổng hợp tháng xếp loại A/B/C/D (≥8,5 / ≥7 / ≥5) làm cảnh báo sớm; robot rà thiếu: 1 ngày → nhắc nhở TP, 2 ngày liên tiếp → cảnh báo đỏ HCNS/TGĐ (chạy cùng nút "Chạy robot").
- **Ca trực page**: GĐ KD phân ca (sáng/chiều/tối); CNTT/robot quét số lượt sót > 5 phút; chế tài 1–3: −100k/lượt, 4–5: −200k/lượt, ≥6: loại ca tháng sau; NV phản hồi trong 3 ngày; tiền phạt tự trừ vào hoa hồng trên bảng lương (không trừ lương cơ bản).
- **Đề nghị chi (05-TT) & lệnh chi**: bắt buộc mã tour với chi tour/hoàn tiền (cổng 14), NCC có MST, chứng từ đính kèm (Kế toán chặn nếu thiếu). Robot R3 xếp cấp: vượt dự toán tour (cố định + biến đổi × max(khách dự toán, khách đã chốt)) hoặc Marketing ≥ hạn mức 5 triệu → 2 chữ ký Chủ tịch + TGĐ (cổng 15). Luồng: bộ phận (TP ĐH / PTGĐ MKT / HCNS) → Kế toán kiểm tra → TGĐ (+Chủ tịch) → lệnh chi chờ → Kế toán chi (nhập mã GD) hoặc SePay tiền ra có mã DC… + đúng số tiền tự khớp. Từ chối phải có lý do.
- **Bút toán**: duyệt → Nợ 154 (tour) / 641 (MKT) / 642 (HC) – Có 331 NCC (ghi chú "không hóa đơn – không trừ TNDN"); chi → Nợ 331 – Có 112/111; hoàn tiền khách → Nợ 131 – Có 112. Quyết toán tour nay chỉ trích trước **335** phần chi phí chưa qua đề nghị chi, rồi kết chuyển 632/154; chi phí quyết toán nhỏ hơn đề nghị chi đã duyệt → cảnh báo Kế toán rà soát.
- **Bảng dòng tiền tour** (mọi cấp duyệt xem): doanh thu booking, đã thu, đã chi, lệnh chi chờ, đang trình, tiền còn lại, dự toán, LN dự kiến; đỏ khi chi + lệnh chi vượt tiền đã thu.
- Trang web: tab **Chi tiền** (đề nghị chi, dòng tiền) và **Báo cáo ngày** (của tôi, tổng hợp phòng, ca trực). Test 4 kịch bản; tổng 30 test. Migration b3d8461c1b41.

---
# Bảng giá xe nội bộ – nạp 05/9/2026 (ảnh gốc: docs/bang-gia-xe-6-5-2026.jpg)
- 29 tuyến từ bảng giá 6/5/2026: cột **xe Vietrip – VTD** và cột **xe hợp tác hỗ trợ** (từ 5/8/2026, xe 50E-955.31, 50H-496.23). Đội xe nội bộ mẫu: 50F-009.60, 50E-957.34.
- Bảng giá là master data: đề xuất (CNTT/HCNS/TP ĐH) → Chủ tịch + TGĐ ký → hiệu lực theo ngày, thay giá cũ cùng tuyến. Lệnh điều xe chọn tuyến → giá theo loại xe (nội bộ / hợp tác); tuyến không có trong bảng → giá theo ngày ở hồ sơ xe. Xe hợp tác không tính công tác phí tài xế Vietrip.

---
# Giai đoạn 3: BCTC & thuế (a) · Ngân quỹ – tài chính (b) · Dashboard & robot báo cáo (c) – 05/9/2026

**(a) BCTC + tờ khai thuế (robot R5/R7)** – tab Kế toán › BCTC / Tờ khai thuế
- B02-DN (KQKD) theo kỳ, tách lãi vay & khấu hao → "LN sau lãi vay trước khấu hao" (căn cứ thưởng GĐ KD); B01-DN (BCĐKT) cuối kỳ, tự cân bằng cả lãi/lỗ chưa kết chuyển; B03-DN (LCTT trực tiếp) phân loại theo tài khoản đối ứng của 111/112, đối chiếu tiền đầu/cuối kỳ. Mẫu rút gọn theo TK cấp 1 – KTT đối chiếu mẫu đầy đủ TT99 trước khi phát hành.
- Robot lập chứng từ kết chuyển 911 (nháp) → KTT ghi sổ.
- 01/GTGT: đầu ra từ HĐĐT đã phát hành, đầu vào từ 133, khấu trừ chuyển kỳ; 05/KK-TNCN từ 3335. Xuất XML (mã chỉ tiêu → giá trị) để nạp HTKK/eTax; KTT ký số & nộp. Biến môi trường COMPANY_TAX_CODE.

**(b) Ngân quỹ – tài chính (mục 3.4, 3.9)** – tab Tài chính
- Hồ sơ hợp đồng tài chính: khế ước vay (tự sinh lịch trả gốc đều + lãi dư nợ giảm dần; nhập đè lịch ngân hàng), đầu tư liên kết, hợp tác KD, ký quỹ, cọc, cho vay, phải thu bán cổ phần, vốn phát hành – bắt buộc nghị quyết HĐQT (trừ vay), cờ bên liên quan (GDLK).
- Thực hiện lịch (đối chiếu GD ngân hàng) → bút toán 341/635/112, 222/138/244/128 – 112; cập nhật dư nợ; quá hạn tự đánh dấu.
- Dự báo dòng tiền 13 tuần: booking còn phải thu (D-7), đề nghị chi + dự toán tour sắp chạy, lịch vay/đầu tư, bảng lương gần nhất, khoản kế hoạch Kế toán nhập (lặp tháng); cảnh báo âm / dưới ngưỡng `so_du_tien_toi_thieu` (500 triệu, tham số 2 chữ ký).
- Báo cáo tài chính tuần (mục 6.6): tiền, vay, hạn 4 tuần, 10 khoản phải thu lớn nhất, danh mục đầu tư cho HĐQT, 154/335 tồn đọng, quá hạn.

**(c) Dashboard theo cấp + robot R7** – Bảng điều khiển, tab Robot báo cáo
- Dashboard: "Việc chờ tôi xử lý" gom mọi phân hệ theo vai trò (tham số, giá xe, đề nghị chi, dự toán, bảng lương, SePay, phiếu thu, chứng từ nháp, quyết toán, báo cáo ngày…); KPI HĐQT/BĐH (tiền, vay, phải thu, cảnh báo 13 tuần, LN kế toán) + KPI vận hành; khối theo phòng (KD Lẻ theo mốc, ĐH chuyến 21 ngày tới & quá hạn quyết toán, HCNS tỷ lệ báo cáo ngày).
- Robot R7: báo cáo ngày / tuần / tháng (markdown + số liệu + nhận xét; Claude API nếu đặt ANTHROPIC_API_KEY, không thì nhận xét theo quy tắc). API cho n8n: `POST /api/v1/robot/report/{ngay|tuan|thang}` (X-Robot-Token) → gửi Zalo/Email. Lịch đề xuất: 20:30 hằng ngày, Thứ Bảy, ngày 10.
- Test: 36 kịch bản. Migration 720517874278.

---
# Đồng bộ Vietrip → VTOS (05/9/2026)

**Cấu trúc Vietrip (app.vietrip.com.vn) đã phân tích** – 154 người dùng, 10 xe, ~10.060 tour, ~70.000 phiếu thu khách, ~6.000 lệnh chi NCC:
- Quản lý User (`/api/users/all`: họ tên, chức vụ, phòng ban Kế toán/Điều hành/Tour/Tour MICE/Hướng dẫn/CSKH/IT/Marketing/Giám đốc), Quản lý Xe (`/api/vehicles/filter`: biển số, đời xe, tài xế, tổng km).
- Quản lý Tour: Sản phẩm (mã, loại tour, phương tiện, số ngày), Đặt tour, Booking (`/api/booking/search`: bookingID, tourcode, người book, SĐT, ADL/CHD/INF, tổng tiền, tình trạng TT UNPAID/DEPO/PAID, deadline hủy chỗ, người tạo, trạng thái OK/hủy), Non-package, Mở khóa booking.
- Điều hành: Thông tin tour (`/operations/OperationsTour/GetToursData`: tourcode = mã SP.số thứ tự+ngày, khởi hành/kết thúc/đóng tour, loại tour TOURLE/NonPackage/MICE, số chỗ mở bán & KM, giá ADL/CHD/INF & KM, vé MB, land, LSQ, bảo hiểm, quà tặng, tổng CP, doanh thu, LN, cờ quyết toán/duyệt chi), Tiền bảo lưu, Đề xuất chi NCC; Quyết toán chi tiết tour (`/tour-settlement/spreadsheet/{id}`: dòng chi phí mô tả, cố định/theo khách, loại DV GUIDE/HOTEL/LAND…, NCC kèm MST, đơn giá, SL, hệ số, thực chi, đã thanh toán; luồng trình – duyệt – từ chối).
- Kế toán: Xác nhận thu chi khách (`GetPaymentData`: phiếu thu/phiếu chi, chờ/đã xác nhận, hình thức CK/tiền mặt, TK công ty TPBank/MB, file UNC), Xác nhận chi NCC (DevExpress: OrgID, FOP BTF/DBT/CSH, TK NCC, trạng thái KC/QQ/XX/GD), Thông tin booking, Duyệt đề xuất chi (loại VEHICLE/…, GĐ và Kế toán duyệt).
- Marketing/CSKH: phân loại khách, hồ sơ khách, khách đã đi tour, chiến dịch, khuyến mãi, Zalo; Báo cáo tour lẻ / điều hành / marketing.

**Bổ sung vào VTOS:** tour thêm mã sản phẩm, loại xe, điểm KH, phương tiện, số ngày, chỗ mở bán/KM, giá CHD/INF/KM, nước, cờ quyết toán Vietrip; booking thêm ADL/CHD/INF, tình trạng TT, deadline hủy chỗ, cờ hủy, dịch vụ lẻ; bảng **dòng chi phí tour** (tour_cost_lines) theo mẫu quyết toán Vietrip; bảng trung gian vt_records giữ bản gốc; API `/import/vietrip/*`; trang **Đồng bộ Vietrip**; kịch bản `docs/vietrip-sync.js` chạy trong trình duyệt đã đăng nhập Vietrip (không lưu mật khẩu).

**Ánh xạ:** user → tài khoản + hồ sơ nhân sự (mật khẩu ngẫu nhiên, HCNS cấp lại); xe → đội xe + tài xế; tour → tours (trạng thái: duyệt chi → khóa; quyết toán → KT xác nhận; đã kết thúc → chờ quyết toán; chưa → đang bán); quyết toán chi tiết → dòng chi phí + chi phí cố định/theo khách; booking → bookings (mã VT<id>, hủy = 0 đ); phiếu thu KC → phiếu thu KT xác nhận (VTPT<id>), phiếu chi khách → hoàn tiền đã chi (VTPC<id>); chi NCC KC → đề nghị chi đã chi (VTDC<id>), GD → lệnh chi chờ, QQ → chờ duyệt. Không sinh bút toán cho dữ liệu nhập.

**Kết quả nạp dữ liệu 6–9/2026 (chạy 05/9/2026, trước 7h30):**
- Đã nạp & ánh xạ: 154 user (+2 test), 10 xe, 1.244 tour (1.006 khởi hành 6–9/2026: T6 311, T7 292, T8 223, T9 180; 238 tour khởi hành sau 30/9 nạp để booking có tham chiếu), 10.295 booking đặt 1/6–5/9, 837 bảng quyết toán tour đã kết thúc (6.439 dòng chi phí; tổng thu 74,1 tỷ), 5.946 phiếu thu/chi khách (5.776 phiếu thu KC ≈ 69,5 tỷ: T6 21,5 · T7 25,4 · T8 20,9 · T9 1,7 tỷ; 162 phiếu chi hoàn khách), 4.807 lệnh chi NCC (4.508 KC ≈ 31,9 tỷ; T6 chỉ từ 24/6 vì API Vietrip chỉ trả ~6.000 lệnh gần nhất).
- Còn lại: 205 phiếu thu "chưa có booking" (booking đặt trước 1/6 hoặc phát sinh sau lúc quét; sẽ tự ánh xạ ở lần đồng bộ sau), 2 đề xuất chi (chưa ánh xạ). 245 booking của tour đã hủy/gộp: 235 booking hủy bỏ qua, 10 booking còn hiệu lực tạo tour tạm từ mã.
- Hạn chế API Vietrip đã ghi vào kịch bản: danh sách phiếu thu chỉ lọc từ ngày, `start` bị giới hạn ~1.100 và `length` lớn hơn ~3.000 bị lỗi → bổ sung quét theo từng booking (`/api/bookings/{id}/payments`); danh sách tour không trả doanh thu/cờ quyết toán (lấy từ bảng quyết toán); bảng quyết toán ~10 giây/tour → quét 6 luồng.
- Việc CNTT: xóa 2 user test (recID 99991–99998, họ tên "Test…") trong vt_records/users; đặt lịch chạy lại kịch bản hằng ngày (idempotent) tới ngày cắt chuyển.
