# Sổ giữ chỗ — làn Phân quyền · Đợt KS-MUC2

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **KS-MUC2 — CÂU CẢNH BÁO NÀO CŨNG CÓ MÀU** (Chủ tịch 08/11/2026: «kiểm tra thêm các bàn làm việc khác trong crm còn chỗ nào cảnh báo để sửa lại màu cho đúng»; duyệt «Sửa hết theo bản xem thử»). Rà sau #719: khoảng 20 câu cảnh báo trên Kết sổ, Lãi lỗ tour, Sổ con nợ, PTGĐ tour đoàn, Đội xe, Tỷ giá, Xác nhận công gắn lớp `warn` / `red` / `note` mà không có kiểu tô nào (lớp chỉ khai trong `<style jsx>` của thành phần khác, hoặc không khai) — hiện như chữ thường. Sửa: bộ kiểu dùng chung trong `globals.css` (`cb-do`, `cb-vang`, `so-do`, `so-vang`, `so-xanh-la`, chỉ dùng biến màu) và gắn đúng từng chỗ; phép thử canh không còn lớp cảnh báo nào thiếu kiểu. Không đổi chữ, không đổi số. | web/app/globals.css, web/app/so-con-no/page.tsx, web/app/ket-so/page.tsx, web/app/ty-gia/page.tsx, web/app/lai-lo-tour/page.tsx, web/app/doi-xe/page.tsx, web/app/ptgd-doan/page.tsx, web/components/XacNhanCong.tsx, backend/tests/test_ks_muc_ba_mau_muc_do.py, docs/dang-lam/phan-quyen/KS-MUC2.md | 08-11-2026 00:30 | xong |
