# Sổ giữ chỗ — làn Phân quyền · Đợt TM-1

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **TM-1 — NỐI vietourist.com.vn SONG SONG VỚI vietourist.vn** (Chủ tịch chốt 02/11/2026: crm/kh/dt/ir.vietourist.com.vn; ba trang tour, khách sạn, nhà hàng theo đường dẫn kh.vietourist.com.vn/tours… như .vn; hai họ tên miền chạy song song, email/link gửi khách vẫn ghi .vn). Mã: bảng tên miền → cổng ở trang đăng nhập, danh sách khóa cứng CG-3, luật viết lại ba trang riêng, và hai chỗ nhận tên miền trả về của cổng thẻ (`tour_online.goc_tra_ve`, `dat_ban._goc`) — chỉ nhận ĐÚNG bốn tên .com.vn; tên gốc/www vietourist.com.vn vẫn là web cũ 103.216.118.43 nên KHÔNG nhận. Không đổi quyền, không thêm API. Ngoài mã (Claude làm trên Chrome của Chủ tịch): thêm 4 tên vào dự án Vercel và 4 bản ghi CNAME ở DNS PA Vietnam; KHÔNG đụng @, www, MX. Năm luật ở `test_tm1_ten_mien_com_vn.py`. | web/next.config.mjs, web/app/login/page.tsx, web/lib/cong.ts, backend/app/api/v1/dat_ban.py, backend/app/services/tour_online.py, backend/tests/test_cg2_ten_mien.py, backend/tests/test_tm1_ten_mien_com_vn.py, docs/dang-lam/phan-quyen/TM-1.md | 02-11-2026 06:10 | đang làm |
