# ĐANG LÀM — bảng giữ chỗ của các làn

Bảng này tồn tại vì **ngày 11/9/2026 có hai lần đụng độ trong một buổi chiều**: VPM-11 và Robot A
cùng viết sổ nghĩa vụ thanh toán; làn Phân quyền và Robot A cùng viết DT-1/DT-3. Không làn nào chép
của làn nào — cả hai lần đều là bốn làn cùng đọc một tài liệu rồi viết ra hai bản gần trùng khít.

Mỗi làn ghi **một dòng vào bảng dưới TRƯỚC KHI viết dòng mã đầu tiên**. Làn sau đọc bảng trước khi
viết. Rẻ hơn gỡ một lần đụng độ, và rẻ hơn rất nhiều so với một mạch nâng cấp hai đầu phát hiện sau
khi đã đẩy lên.

## Cách ghi

| Cột | Ghi gì |
|---|---|
| **Làn** | tên làn: `Robot A`, `Phân quyền`, `Vòng`, `VPM`, `Kiểm soát`, `Quyết toán` |
| **Mã việc** | mã trong lệnh giao việc: `DT-2`, `PQ-10`, `TC-4`, `VPM-17`… |
| **Tệp sẽ đụng** | đường dẫn từ gốc kho, phân cách bằng dấu phẩy. Kể cả tệp SẼ TẠO MỚI. |
| **Bắt đầu** | `DD-MM-YYYY HH:MM` |
| **Trạng thái** | `đang làm` · `xong` · `bỏ` |

Chỉ dòng **`đang làm`** mới giữ chỗ. Xong việc thì đổi sang `xong` — **đừng xoá dòng**, vì dòng cũ
là chỗ tra "ai đã đụng tệp này lần trước".

## Phép thử canh bảng này

`backend/tests/test_giu_cho_lan.py` đọc chính tệp này và **ĐỎ** khi hai dòng `đang làm` cùng khai
một đường dẫn. Không có phép thử canh thì một bảng khai đúng ba ngày là không ai điền nữa.

Phép thử **cố ý KHÔNG** đỏ theo thời gian — không có luật "quá N ngày thì đỏ". Một phép thử tự đỏ
mà không ai sửa mã là thứ làm người ta thôi nhìn CI, và chính lệnh giao việc đã cảnh báo điều đó.

Bảng này KHÔNG thay cho việc đọc kho mã trước khi viết. Nó chỉ bắt được chuyện hai làn khai cùng một
tệp; hai làn viết cùng một KHÁI NIỆM vào hai tệp khác tên thì bảng không thấy — đó vẫn là việc phải
đọc lệnh giao việc của làn khác.

---

## Bảng

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Robot A | GD-1 khối Dòng tiền DT-1…DT-4 | backend/app/models/dong_tien.py, backend/app/services/dong_tien.py, backend/app/api/v1/dong_tien.py, web/app/dong-tien/page.tsx | 11-09-2026 13:40 | xong |
| VPM | VPM-11 sổ nghĩa vụ thanh toán | backend/app/models/nghia_vu.py, backend/app/services/nghia_vu.py | 11-09-2026 14:30 | xong |
| VPM | VPM-17 cửa nhập ngày đến hạn | backend/app/api/v1/ops.py, backend/app/api/v1/suppliers.py, backend/app/services/ops.py, backend/app/services/suppliers.py | 11-09-2026 16:00 | xong |
| Phân quyền | PQ-10 · SEC-02 · CF-07 · DT-1 · DT-3 · GD-1 | backend/app/services/pham_vi_dang_xem.py, backend/app/services/lam_tron_tien.py, backend/app/services/dong_tien_ky.py, backend/app/services/dong_tien_pham_vi.py, backend/app/services/canh_bao_trinh_bay.py | 11-09-2026 15:30 | xong |
| Vòng | TC-2 · TC-1 · TC-1b · TC-4 | web/components/Shell.tsx, web/components/ChonDonVi.tsx, web/components/dienthoai.tsx, web/lib/phamvi.ts, web/app/globals.css | 11-09-2026 15:00 | xong |
| Kiểm soát | hàng rào phạm vi · visa sales | backend/app/services/access.py | 11-09-2026 09:00 | xong |
| Robot A | Ba cửa kho quyết toán cũ T1–T6/2026 | backend/app/services/intake_kho_cu.py, backend/app/services/intake.py, backend/tests/test_kho_cu_ba_cua.py | 12-09-2026 01:30 | xong |
| Robot A | Đ-2 thuế GTGT ở mức chuyến | backend/app/services/thue_gtgt_chuyen.py, backend/app/services/lai_lo_tour.py, backend/tests/test_thue_gtgt_chuyen.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-3 ba phép kiểm hai tổng phải bằng nhau | backend/app/services/soat_can_doi_quyet_toan.py, backend/tests/test_soat_can_doi_quyet_toan.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-6 tiền tip hai chiều + tham số tỷ lệ chia | backend/app/services/tip_tour.py, backend/app/models/lop3_tour.py, backend/app/services/rules.py, backend/tests/test_tip_tour.py | 12-09-2026 19:30 | xong |
| Robot A | Đ-1 mở cửa quyết toán lớp 3 | web/app/tours/[id]/page.tsx, backend/tests/test_cua_quyet_toan_lop3.py | 12-09-2026 21:00 | xong |
| Robot A | Đ-2b thuế tour nước ngoài hai dòng hoá đơn | backend/app/services/thue_gtgt_chuyen.py, backend/app/services/lai_lo_tour.py, backend/app/services/rules.py | 12-09-2026 22:30 | xong |
| Robot A | Đ-6b ô % chia tip cho Điều hành nhập | backend/app/services/tip_tour.py, backend/app/api/v1/quyet_toan_lop3.py, web/components/QuyetToanForm.tsx | 12-09-2026 22:30 | xong |
