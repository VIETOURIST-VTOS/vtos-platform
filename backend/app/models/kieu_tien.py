"""V9 – kiểu cột dùng cho MỌI cột tiền, khai một chỗ.

Lệnh Đợt 2, việc V9. 117 cột tiền đang khai kiểu số thực nhị phân (Float). Cộng dồn nhiều dòng thì
lệch, và lệch ở chỗ không ai nhìn – đây là chỗ kiểm toán đối chiếu đầu tiên.

VÌ SAO KHAI Ở MỘT TỆP RIÊNG thay vì gõ Numeric(18, 2) ở 117 chỗ: đổi 117 chỗ bằng tay thì sớm muộn
có chỗ gõ Numeric(18, 4), có chỗ quên, và ba tháng sau không ai trả lời được câu "cột tiền của hệ
này khai thế nào". Một cái tên thì đọc là biết, và sửa quy ước sau này là sửa một dòng.

────────────────────────────────────────────────────────────────────────────────
MỘT ĐIỀU PHẢI NÓI THẲNG: `asdecimal=False`, VÀ VÌ SAO
────────────────────────────────────────────────────────────────────────────────

Kiểu này đổi CỘT TRONG CƠ SỞ DỮ LIỆU sang số thập phân chính xác, nhưng Python vẫn nhận về `float`.
Đó là một lựa chọn có ý thức, không phải bỏ sót, và nó chỉ giải một nửa vấn đề:

    ĐÃ GIẢI – phần lưu trữ và phần cộng dồn phía cơ sở dữ liệu. Giá trị nằm trên đĩa là số thập phân
    đúng, không còn xấp xỉ nhị phân; và SUM() của PostgreSQL trên numeric là phép cộng chính xác.
    Đây chính là chỗ kiểm toán đối chiếu, và là chỗ lệch tích lũy sinh ra.

    CHƯA GIẢI – số học phía Python. Cộng trừ trong mã vẫn là float.

Vì sao không bật `asdecimal=True` ngay ở đợt này: đổi kiểu trả về thành Decimal làm MỌI phép tính
trộn với float trong mã ném TypeError ngay lúc chạy – `so_tien * 0.1` là hỏng. Số chỗ như vậy nằm
rải khắp phân hệ kế toán, đội xe, lương, và không có cách nào biết hết bằng cách đọc. Bật cả cụm
trong một lần nâng cấp trên hệ thống đang chạy của một công ty đại chúng là đánh cược, không phải kỹ
thuật.

Nên tách làm hai: đợt này sửa chỗ SỐ NẰM (làm được ngay, không rủi ro), đợt sau bật Decimal theo
từng phân hệ kèm rà soát số học của phân hệ đó. Ai đọc tệp này sau cũng phải thấy rằng nửa thứ hai
CÒN NỢ, chứ không tưởng V9 đã xong.

────────────────────────────────────────────────────────────────────────────────

18 chữ số, 2 chữ số thập phân: đủ cho 9.999 tỷ tỷ đồng – doanh thu 48 tỷ hai tháng của công ty còn
xa mới chạm. Hai chữ số thập phân giữ được phần lẻ sinh ra từ phép chia (phân bổ, khấu hao, cấn trừ)
mà không giữ thừa: đồng Việt Nam không có đơn vị nhỏ hơn đồng, nên mọi chữ số thứ ba trở đi là sản
phẩm của phép chia chứ không phải của một khoản tiền có thật.
"""
from sqlalchemy import Numeric

# Dùng cho cột TIỀN. Không dùng cho tỷ lệ (thuế suất, tỷ lệ hoa hồng), hệ số, số lượng, hay số đo –
# K1 đã tách riêng những cột đó và đổi nhầm chúng cũng tốn đúng một lần nâng cấp cơ sở dữ liệu.
TIEN = Numeric(18, 2, asdecimal=False)

# Số chữ số dùng lại ở bản nâng cấp, để mô hình và bản nâng cấp không bao giờ lệch nhau.
TIEN_PRECISION = 18
TIEN_SCALE = 2
