# Sổ giữ chỗ — làn Phân quyền · Đợt XE-V33

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `Phân quyền`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| Phân quyền | **XE-V33 — ĐỘI XE THEO DEMO v3.3: ĐỀ XUẤT CHI ĐI VÀO ĐỀ NGHỊ CHI 05-TT + MÀN /xe** (Chủ tịch chốt 10/11/2026, duyệt bản xem trước). (1) Phiếu GĐ đội xe lập là đề nghị chi loại `chi_doi_xe`: sổ VTD, bắt đầu ở Kế toán kiểm (GĐ gửi = bộ phận xác nhận), mốc duyệt chung, tài khoản theo nhóm (627 / 141 / 331), chống gửi hai lần, GĐ không nhập ngân hàng, điều chuyển nội bộ không lập ở đây — thay luồng riêng của nhánh KS-63 (KHÔNG gộp nhánh ấy). (2) /xe: nội dung đổi tại chỗ (nhúng màn gốc, không sửa Shell — làn R2 giữ), hai cửa nhập mở tại chỗ, bỏ khối mục lục phân hệ, trải hết bề ngang, «Xe đang đi» Chưa khớp, «Lợi nhuận tạm tính», công suất đếm mọi chuyến ghi nhận, ô «Số tiền theo», «Quyền của tôi». | backend/app/models/ops.py, backend/alembic/versions/dx5c2a8e4f1b7d93_de_nghi_chi_doi_xe.py, backend/app/services/luong_viec.py, backend/app/services/misa.py, backend/app/api/v1/fleet.py, backend/app/services/fleet_lai_lo.py, backend/app/services/hieu_qua_xe.py, backend/tests/test_dx5_de_nghi_chi_doi_xe.py, web/app/xe/page.tsx, web/app/expenses/page.tsx, web/components/KhoiV14.tsx, web/components/doixe/BonBuocDeXuatChi.tsx, web/components/doixe/DeXuatChiTaiCho.tsx, backend/app/services/dat_ban.py, backend/tests/test_man_hinh_co_khung.py, docs/dang-lam/phan-quyen/XE-V33.md | 10-11-2026 00:40 | xong |

`backend/app/services/ops.py` khai ở sổ làn TC-KT ([../tc-kt/XE-V33.md](../tc-kt/XE-V33.md)) — tệp ấy chỉ làn TC-KT
được giữ (đợt dọn hai dòng ôi của TC-KT); Chủ tịch cho phép khai ở đó ngày 10/11/2026.

Sửa thêm khi CI đỏ: `fleet.py` đọc `so_tien` chịu rỗng (K2); `dat_ban.py` bỏ dấu gạch trong ghi chú làm phép thử K2
tưởng là phép trừ (đỏ trên main từ #765); `test_man_hinh_co_khung` nhận `<Shell khongThanhBen>` là có bọc Shell
(đỏ trên main với /xe và /marketing).
