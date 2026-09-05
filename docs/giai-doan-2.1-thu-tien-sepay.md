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
