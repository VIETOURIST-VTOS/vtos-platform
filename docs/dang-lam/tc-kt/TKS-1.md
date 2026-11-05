# Sổ giữ chỗ — làn TC-KT · Đợt TKS-1

Một đợt một tệp (Đợt SO-DOT 02/11/2026). Luật: [../README.md](../README.md).
Mọi dòng trong tệp này PHẢI có cột `Làn` là `TC-KT`.

| Làn | Mã việc | Tệp sẽ đụng | Bắt đầu | Trạng thái |
|---|---|---|---|---|
| TC-KT | **TKS-1 — KHOÁ CHỐNG TRÙNG CỦA `test_ket_so.py` DỰA VÀO ĐỒNG HỒ, NÊN NÓ ĐỎ KHI MÁY CHẠY NHANH**. Đo trên main 06/11/2026: hàm `but_toan()` của tệp ấy lấy `f"test:{datetime.now().timestamp()}"` làm **mã nguồn** truyền cho `post_entry`. `datetime.now()` trên Windows nhảy từng ~15,6 ms, nên hai bút toán gọi liền nhau trong cùng một nhịp nhận CÙNG MỘT mã — và khoá chống ghi sổ hai lần của Đợt E3 (nguồn + mã nguồn + loại nghiệp vụ) chặn cái thứ hai, đúng việc nó sinh ra để làm. Lỗi nằm ở PHÉP THỬ, không ở sản phẩm: `post_entry` cư xử đúng. Hai vòng bấm Đợt DS-3 ngày 06/11 đỏ vì chỗ này — vòng đầu một phép thử, vòng sau hai — trong khi ba vòng hôm 05/11 đều xanh; đó là dấu của một phép thử phụ thuộc tốc độ máy chứ không phụ thuộc mã. Sửa: mã nguồn ghép thêm một BỘ ĐẾM TĂNG DẦN, nên nó duy nhất **do cách dựng** chứ không nhờ đồng hồ chạy đủ chậm. KHÔNG nới khoá chống trùng của `post_entry` — khoá ấy đang đúng, và nới nó để một phép thử hết đỏ là mở lại đúng chỗ hở nó bịt. Hai luật ở `test_tks1_khoa_chong_trung_phep_thu.py`: luật 1 đóng băng đồng hồ rồi đòi một nghìn lần gọi ra một nghìn mã khác nhau; luật 2 soi `test_ket_so.py` không còn lấy MỖI đồng hồ làm khoá. | backend/tests/test_ket_so.py, backend/tests/test_tks1_khoa_chong_trung_phep_thu.py, docs/dang-lam/tc-kt/TKS-1.md | 06-11-2026 03:30 | xong |
