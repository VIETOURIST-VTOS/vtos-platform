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
