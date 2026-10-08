"use client";
import Shell from "@/components/Shell";
import DonNghiPhep from "@/components/DonNghiPhep";

/** Đơn nghỉ phép của tôi — mục 5.4b cây phân hệ, dựng 08/10/2026.
 *
 *  VÌ SAO MÀN HÌNH NÀY TỒN TẠI: cửa `POST /leaves` nhận đơn của BẤT KỲ ai đăng nhập (`current_user`),
 *  nhưng ô bấm chỉ có trên /xe-hdv của tài xế và hướng dẫn viên. Chín phòng còn lại không có đường vào
 *  — việc còn nợ đã ghi ra từ 30/9/2026 và nay trả. Cửa mở mà người không với tới thì cửa ấy chưa tồn tại.
 *
 *  Màn hình MỎNG là có chủ ý. Khung gửi đơn là thành phần dùng chung `DonNghiPhep`, cùng một thành
 *  phần đứng trên /xe-hdv — một cửa, một bảng, không hai bản chép lệch nhau ở lần sửa thứ nhất. Còn
 *  LƯỚI chấm công tháng đứng ở màn hình Lương chứ không ở đây: ô ghi của lưới đòi `HR_ADMIN`, nên đặt
 *  nó ở một màn hình mở cho cả 22 vai sẽ buộc khai tiền tố `/api/v1/attendance` cho cả 22 vai — mười
 *  sáu vai mang trong phạm vi một cửa máy chủ từ chối họ. Trang nói ra lưới nằm ở đâu, không giấu.
 */
function ChamCong() {
  return (<>
    <h1>Đơn nghỉ phép của tôi</h1>
    <p className="muted">Đơn nghỉ gửi ở đây, và <b>mọi phòng đều gửi được</b> — không chỉ tài xế và
      hướng dẫn viên. Đơn đi thẳng tới người ký của phòng bạn; đơn đã duyệt tự ghi vào bảng chấm công
      tháng. <b>Bảng chấm công không phải căn cứ trả lương</b>: bảng lương lấy số công Nhân sự nhập ở
      màn hình <b>Lương, thưởng &amp; hoa hồng</b>, và chỗ hai số lệch nhau được đếm ra ở chính màn
      hình ấy. Lưới chấm công tháng nằm ở màn hình <b>Chấm công &amp; nghỉ phép</b> của Nhân sự, vì chỉ Nhân sự ghi được.</p>
    <DonNghiPhep />
  </>);
}

export default function Page() { return <Shell><ChamCong /></Shell>; }
