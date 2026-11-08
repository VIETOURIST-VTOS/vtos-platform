"use client";
/** ĐỢT PH-1 — Kinh doanh lẻ, đường dẫn riêng `/fit`. Chủ tịch chốt 08/11/2026.
 *
 *  TRANG NÀY KHÔNG CÓ THÂN RIÊNG. Nó gọi `components/TrangPhanHe` với khoá `kdle` — đúng thân
 *  đang chạy ở `/phan-he/[khoa]` từ 11/10/2026. Chép thân ra đây là tạo bản thứ hai của cùng một
 *  trang, và hai bản thì sớm muộn lệch nhau; lúc ấy không ai biết bản nào đúng.
 *
 *  CHỖ Ở CŨ `/phan-he/kdle` ĐÃ BỎ, chỉ còn lối chỉ sang đây — xem `app/phan-he/[khoa]/page.tsx`.
 *
 *  BỌC `Suspense` — BẮT BUỘC, và vì một lý do KHÁC với `/phan-he/[khoa]`. Đường dẫn kia là đường
 *  ĐỘNG nên Next không dựng sẵn và không đòi ranh giới nào. `/fit` là đường TĨNH: Next dựng
 *  sẵn, mà `TrangPhanHe` gọi `useSearchParams` để đọc `?xem=muc-luc`. Thiếu lớp này thì
 *  `npm run build` CHẾT ở đúng trang này — luật 11/10/2026, canh ở
 *  tests/test_web_suspense_cho_search_params.py.
 */
import { Suspense } from "react";
import Shell from "@/components/Shell";
import TrangPhanHe from "@/components/TrangPhanHe";

export default function Page() {
  return <Shell><Suspense fallback={<div className="panel muted">Đang tải…</div>}>
    <TrangPhanHe khoa="kdle" />
  </Suspense></Shell>;
}
