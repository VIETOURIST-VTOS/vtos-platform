"use client";
/** TRANG PHÂN HỆ — đường dẫn ĐỘNG, còn phục vụ những phân hệ chưa dời.
 *
 *  Thân trang đã chuyển sang `components/TrangPhanHe.tsx` ngày 08/11/2026 (Đợt PH-1), vì năm
 *  phòng được tách ra đường dẫn riêng và sáu lối vào phải dùng CHUNG một thân — chép ra sáu bản
 *  thì sớm muộn chúng lệch nhau. Mọi luật của trang nằm trong tệp ấy, đọc ở đó.
 *
 *  ───────────────────────────────────────────────────────────────────────────────────────────
 *  LỐI CHUYỂN TIẾP CHO NĂM ĐƯỜNG DẪN CŨ
 *  ───────────────────────────────────────────────────────────────────────────────────────────
 *
 *  `/phan-he/kdle` và bốn bạn của nó KHÔNG còn là chỗ ở của năm phòng ấy nữa — Chủ tịch chốt
 *  08/11/2026 là bỏ, thay bằng `/fit`, `/mice`, `/op`, `/xe`, `/guide`.
 *
 *  "Bỏ" ở đây là bỏ CHỖ Ở, không phải đập cửa. Đường cũ giữ lại đúng một việc: chỉ sang chỗ mới.
 *  Lý do không đập thẳng: năm đường ấy đã sống hơn một tháng, nằm trong dấu trang của người dùng
 *  và trong các tin nhắn đã gửi nhau. Đập thẳng thì sáng hôm sau có người báo hỏng, mà cái hỏng
 *  ấy không nói cho họ biết phải đi đâu.
 *
 *  Dùng `replace` chứ không `push`: người bấm Quay lại phải về chỗ họ vừa rời, không phải rơi
 *  ngược vào đường cũ rồi bị đẩy sang lần nữa — một vòng lặp mà người dùng không thoát được bằng
 *  nút Quay lại.
 *
 *  Giữ nguyên phần sau dấu hỏi: `?xem=muc-luc` là một lối vào thật, mất nó thì người theo dấu
 *  trang cũ tới mục lục sẽ rơi vào bảng chỉ tiêu và tưởng mục lục đã bị bỏ.
 */
import { useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import TrangPhanHe from "@/components/TrangPhanHe";
import { DUONG_PHONG } from "@/lib/duong_phong";

function ChiSangChoMoi({ duong }: { duong: string }) {
  const r = useRouter();
  const sp = useSearchParams();
  const q = sp?.toString();
  useEffect(() => { r.replace(q ? `${duong}?${q}` : duong); }, [r, duong, q]);
  return <p className="muted">Phòng này đã chuyển sang <b>{duong}</b> — đang mở…</p>;
}

/** KHÔNG bọc `Suspense`, và đó là kết quả của một phép đo chứ không phải quên.
 *
 *  Next đòi ranh giới `Suspense` quanh `useSearchParams` khi trang bị DỰNG SẴN. Sáu màn hình
 *  dùng `useSearchParams` trong kho đều bọc — và cả sáu đều là đường dẫn TĨNH. Màn hình thứ bảy,
 *  `app/tours/[id]/page.tsx`, là đường dẫn ĐỘNG và KHÔNG bọc; nó nằm trên main và nhịp `web`
 *  vẫn xanh. Kho không có một `generateStaticParams` nào, nên đường dẫn động không bị dựng sẵn.
 *
 *  `/phan-he/[khoa]` là đường dẫn động, nên theo đúng tiền lệ ấy. Ngày nào ai thêm
 *  `generateStaticParams` cho nhánh này thì luật đổi — và `test_web_suspense_cho_search_params`
 *  đỏ đúng ngày đó, nên không phải nhớ.
 *
 *  NĂM TRANG MỚI THÌ NGƯỢC LẠI: `/fit` và bốn bạn của nó là đường dẫn TĨNH, nên mỗi trang ấy tự
 *  bọc một lớp `Suspense`. Cùng một thân trang, hai luật khác nhau, vì hai loại đường dẫn khác
 *  nhau — không phải vì ai đó quên.
 *
 *  Lấy khoá bằng useParams chứ không nhận qua tham số `params`: Next 15 đổi `params` thành
 *  Promise còn Next 14 thì không, và trang này là client component nên useParams chạy đúng ở cả
 *  hai. */
export default function Page() {
  const p = useParams<{ khoa: string }>();
  const khoa = String(p?.khoa || "");
  const moi = DUONG_PHONG[khoa];
  return <Shell>{moi ? <ChiSangChoMoi duong={moi} /> : <TrangPhanHe khoa={khoa} />}</Shell>;
}
