# Sổ giữ chỗ — mỗi làn một tệp

**Chủ tịch quyết 06/10/2026.** Trước ngày này cả sáu làn ghi chung vào `docs/DANG-LAM.md`.
Một tệp chung, bốn làn đẩy song song, và mỗi lần đẩy là một lần ghi thêm dòng vào CUỐI tệp —
nên git thấy hai nhánh cùng sửa đúng một chỗ và báo xung đột. Đo được: quyển sổ chung bị đè
hoặc gây xung đột **năm lần trong ba tuần** (19/9, 23/9, 30/9, và hai lần ngày 06/10), và nó là
**thứ duy nhất** gây xung đột trong những lần ấy — không một tệp mã nào.

Từ nay mỗi làn ghi vào tệp của chính mình. Hai làn đẩy cùng lúc thì sửa hai tệp khác nhau, và
git không có gì để xung đột.

| Làn | Tệp |
|---|---|
| Robot A | `docs/dang-lam/robot-a.md` |
| Phân quyền | `docs/dang-lam/phan-quyen.md` |
| Vòng | `docs/dang-lam/vong.md` |
| VPM | `docs/dang-lam/vpm.md` |
| Kiểm soát | `docs/dang-lam/kiem-soat.md` |
| Quyết toán | `docs/dang-lam/quyet-toan.md` |
| R2 | `docs/dang-lam/r2.md` |

## Luật

1. **Bảng vẫn y hệt cũ** — năm cột `Làn · Mã việc · Tệp sẽ đụng · Bắt đầu · Trạng thái`. Hai hàng
   rào `test_giu_cho_lan.py` và `test_giu_cho_nhanh.py` đọc TẤT CẢ các tệp ở đây **cộng với**
   `docs/DANG-LAM.md`, rồi xét trên tập gộp. Nên luật không đổi một chữ: hai dòng `đang làm` của
   hai làn cùng khai một tệp thì vẫn ĐỎ, dù hai dòng ấy nằm ở hai tệp khác nhau.

2. **Dòng trong tệp của làn nào thì cột `Làn` phải là làn ấy.** Không có luật này thì tách tệp
   chẳng mua được gì: một làn ghi dòng của mình vào tệp làn khác là xung đột quay lại nguyên vẹn.

3. **`docs/DANG-LAM.md` KHÔNG bị xoá.** Nó còn 77 dòng lịch sử và còn nhánh đang bay của làn khác
   trỏ vào nó. Xoá nó là làm gãy những nhánh ấy đúng lúc chúng sắp gộp. Nó được đọc tiếp như một
   tệp nguồn nữa; làn nào dời dòng của mình sang đây thì dời, không ai bị ép.

4. **Nhánh đụng tệp mã vẫn phải sửa sổ** (luật N2 cũ) — nay “sổ” nghĩa là `docs/DANG-LAM.md`
   **hoặc** một tệp bất kỳ trong thư mục này. Làn ghi tệp riêng của mình là đã thoả N2.

## Vì sao không bỏ hẳn bảng khai

Vì nó đã reo đúng. Ngày 06/10/2026 chính hàng rào này chỉ ra ba tệp mà hai làn cùng giữ —
`ks_robot.py`, `misa.py`, `staff.py` — trước khi ai mất gì. Thứ hỏng không phải cái bảng, mà là
chỗ cất nó.
