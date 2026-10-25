# Cửa hẹp chạy trên máy — cho mọi làn

    scripts\!CUA-HEP.bat          (bấm rồi gõ tên nhánh)
    python scripts\cua-hep.py --nhanh <ten-nhanh>

## Nó làm gì

Chạy **đúng** những gì việc `hang-rao-gop` của `ci.yml` chạy: 17 tệp phép thử, cộng
`ruff check app --select E9,F63,F7,F82`. Danh sách 17 tệp chép nguyên từ `ci.yml`, không tự chọn.

Đo trên máy Chủ tịch 25/10/2026: **1 đến 1,5 phút** một lượt. Trên CI việc ấy mất 57 giây.

## Vì sao có nó

Ngân sách GitHub Actions chạm trần ngày 24/10 (lần thứ tư: 19/9 · 17/10 · 21/10 · 24/10) và bị
chặn tới 01/11. Mọi lượt CI trả về *"The job was not started because recent account payments have
failed or your spending limit needs to be increased"* sau 4 giây. Các làn vẫn đẩy mã lên, nhưng
không hàng rào nào canh.

Loại hỏng mà cửa hẹp bắt là loại không ai thấy bằng mắt — `ci.yml` ghi sẵn:

> Hai PR cùng xanh RIÊNG LẺ vẫn có thể hỏng khi GỘP LẠI: làn A thêm một bản di trú, làn B cũng
> thêm một bản — mỗi nhánh một đầu mạch nên cả hai đều xanh, gộp xong thành hai đầu và hộp chứa
> chết lúc khởi động.

## Nó KHÔNG làm gì

- **Không thay bộ đủ 251 tệp (~55 phút).** Xanh ở đây không có nghĩa là `backend` sẽ xanh.
- **Không ghi, không đẩy, không gộp.** Chỉ đọc.
- **Không chạy `web`.** Vòng nào đụng giao diện thì cửa hẹp không nói gì về phần ấy.

## Đọc màu cho đúng

| Nó nói | Nghĩa là |
|---|---|
| `✓ CỬA HẸP XANH` | 17 tệp qua hết |
| `⛔ CỬA HẸP ĐỎ` | có phép thử đỏ thật — đọc dòng `FAILED`/`ERROR` |
| `⛔ máy chưa cài pytest` | **chưa chạy được**, KHÔNG phải xanh. `python -m pip install -r backend\requirements-dev.txt` |
| `⛔ KHÔNG CÓ MỘT DÒNG NÀO` | có lượt cửa hẹp khác chạy đè — để mỗi lượt xong rồi hãy bấm lượt sau |

Nếu nhánh của bạn không đụng tệp sổ nào thì `test_gn2` sẽ đỏ. Đó không phải lỗi của cửa hẹp:
luật 4 trong [docs/dang-lam/README.md](../docs/dang-lam/README.md) đòi mỗi nhánh đẩy mã lên phải
kèm một dòng trong quyển sổ của làn mình.
