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
| TC-KT | `docs/dang-lam/tc-kt.md` |

**Bổ sung 02/11/2026 — làn TC-KT.** Việc tách ngày 06/10 chạy đúng: ngày 02/11 làn
`at2-nha-hang-agoda` gộp vào main mà không đụng `phan-quyen.md`. Nhưng bốn nhánh R4c liên
tiếp không gộp được, vì cả bốn khai làn «Phân quyền» rồi cùng nối vào cuối một tệp. Đo
được hôm ấy: `phan-quyen.md` **444 KB · 187 dòng · 16 dòng «đang làm»**, trong khi
`vpm.md` là 334 byte. Cùng một hỏng hóc, ở một tầng sâu hơn — không phải giữa các làn nữa,
mà trong một làn đã phình thành sáu làn đội lốt một. Phân hệ Tài chính – Kế toán từ nay
ghi vào tệp của chính nó.

**Dòng cũ KHÔNG bị dời.** `phan-quyen.md` còn dòng của làn khác và của nhánh đang bay;
dời chúng là sửa sổ người khác không ai nhờ, và làm gãy đúng những nhánh ấy — cùng lẽ với
luật 3 ở dưới. Làn nào muốn dời thì tự dời.

**Bổ sung 02/11/2026 (lần hai) — mỗi ĐỢT một tệp.** Tách làn chữa xung đột *giữa* các làn.
Nó không chữa được hai đợt của *cùng* một làn: cả hai vẫn nối vào cuối một tệp. Từ Đợt
SO-DOT, một làn ghi theo **một trong hai cách, hoặc cả hai**:

  · `docs/dang-lam/<làn>.md` — tệp phẳng, cách cũ, không ai bị ép dời;
  · `docs/dang-lam/<làn>/<mã đợt>.md` — **một tệp cho một đợt**. Đợt tạo tệp mới, nên git
    không có gì để hoà.

Chỉ SÂU MỘT BẬC. Bộ đọc đi đúng một bậc; một bậc nữa thì những dòng ấy rơi khỏi tập gộp,
nên `test_giu_cho_lan` chặn thư mục con và nói ra lý do.

**Chỗ chặn thư mục lạ đã chuyển.** `la_tep_so` của N2 nay nhận một bậc, nên nó không còn là
thứ chặn một thư mục lạ kiểu `docs/dang-lam/cu/`. Thứ chặn bây giờ là phép thử một-đổi-một
trong `test_giu_cho_lan`: mọi chỗ chứa trong thư mục này phải khớp `LAN_TEP`. Phép thử
`test_gn11b` đo lại đúng điều ấy, để nó là thứ đo được chứ không phải một câu hứa.

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

## Soi nhánh trước khi đẩy, khi CI không chạy

Ngân sách Actions chạm trần ngày 24/10/2026 (lần thứ tư) và bị chặn tới 01/11. Trong lúc ấy mọi
lượt CI đỏ sau 4 giây vì *không khởi động được*, nên **PR không có màu nào để đọc**.

Chạy hàng rào ngay trên máy, một đến hai phút:

    scripts\!CUA-HEP.bat          (bấm rồi gõ tên nhánh)

Nó chạy ĐÚNG 17 tệp phép thử của việc `hang-rao-gop` — trong đó có `test_giu_cho_lan` và
`test_giu_cho_nhanh`, tức đúng hai hàng rào canh quyển sổ này. Chi tiết và những chỗ nó KHÔNG
thay được: [scripts/README-cua-hep.md](../../scripts/README-cua-hep.md).
