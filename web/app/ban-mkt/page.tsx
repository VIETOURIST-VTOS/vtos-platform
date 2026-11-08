"use client";
/** MKT-1 · BÀN LÀM VIỆC NHÂN VIÊN MARKETING — `/ban-mkt`, Chủ tịch duyệt 09/11/2026.
 *
 *  Thân bàn dùng chung với `/ptgd-mkt` ở `components/BanMkt.tsx` — xem chú thích bên ấy.
 *
 *  Ô "Lead nằm im quá hạn tôi giữ" cắt theo NGƯỜI ĐANG ĐĂNG NHẬP, và việc cắt ấy làm ở MÁY CHỦ.
 *  Trang này không truyền `nguoi_id` và cửa API cũng không nhận: nhận một tham số người là mở
 *  đường cho một nhân viên gõ thêm vào đường dẫn để đọc bàn của đồng nghiệp.
 *
 *  Phó TGĐ Marketing cũng mở được trang này — Chủ tịch chốt 09/11/2026: người quản thấy cả bàn
 *  của nhân viên. Lúc ông mở thì ô lead đếm lead của CHÍNH ÔNG, vì nó cắt theo người đăng nhập;
 *  muốn nhìn lead cả phòng thì mở `/marketing?tab=khach`, nơi quyền đã có chủ.
 */
import Shell from "@/components/Shell";
import BanMkt from "@/components/BanMkt";

export default function Page() {
  return <Shell><BanMkt duong="/marketing/ban-nhan-vien" /></Shell>;
}
