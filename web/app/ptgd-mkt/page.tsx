"use client";
/** MKT-1 · BÀN LÀM VIỆC PHÓ TGĐ MARKETING — `/ptgd-mkt`, Chủ tịch duyệt 09/11/2026.
 *
 *  Trang mỏng có chủ ý: thân bàn nằm ở `components/BanMkt.tsx`, dùng chung với `/ban-mkt`. Hai
 *  bàn khác nhau ở DANH SÁCH Ô, mà danh sách ô do máy chủ dựng — phần vẽ thì giống hệt nhau.
 *
 *  CÓ THANH DỌC, khác `/xe`. Bàn đội xe là màn RIÊNG của một pháp nhân khác nên nó ẩn thanh dọc;
 *  hai bàn Marketing thì nằm trong cùng bộ màn hình với `/marketing`, và mọi ô trên bàn đều dẫn
 *  sang một tab của màn ấy. Ẩn thanh dọc ở đây là bắt người ta bấm Quay lại để đi tiếp.
 *
 *  KHÔNG GỌI `useSearchParams`, nên không cần ranh giới `Suspense` — xem luật ở
 *  `backend/tests/test_web_suspense_cho_search_params.py`. Bàn này không nhận tham số nào: ô lead
 *  cắt theo người đang đăng nhập ở máy chủ, không nhận `nguoi_id` từ đường dẫn.
 */
import Shell from "@/components/Shell";
import BanMkt from "@/components/BanMkt";

export default function Page() {
  return <Shell><BanMkt duong="/marketing/ban-ptgd" /></Shell>;
}
