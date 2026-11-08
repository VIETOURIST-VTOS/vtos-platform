"use client";
/* KS-KS2 · 08/11/2026 — TẢI KHI CUỘN TỚI (Chủ tịch chọn «Cuộn tới mới tải»).
 *
 * Trang Kết sổ vừa mở đã gửi 10 yêu cầu của riêng nó cùng một lúc; máy chủ xử lý ít yêu cầu một
 * lúc nên ba khung trên cùng (Tình trạng kỳ, Tách tỷ giá, Bù trừ GTGT) phải xếp hàng sau bốn khung
 * dưới mà người đọc còn chưa cuộn tới. Đo trên crm thật: gọi riêng thì mỗi bản xem trước khoảng 2
 * giây, mở cả trang thì 5–6 giây.
 *
 * Khung bọc trong đây chỉ được DỰNG (và vì thế mới gọi máy chủ) khi nó cách màn hình 300px. Trước
 * đó chỉ hiện tiêu đề của khung và «Đang tải…», nên bố cục trang không đổi. Dựng rồi thì giữ luôn,
 * cuộn đi cuộn lại không tải lại. Trình duyệt không có IntersectionObserver thì dựng ngay như cũ.
 */
import { useEffect, useRef, useState, type ReactNode } from "react";

export default function TaiKhiThay({ ten, san = true, children }: { ten: string; san?: boolean; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [thay, setThay] = useState(false);
  useEffect(() => {
    if (thay || !san) return;    // `san`: chỗ gọi báo phần trên đã dựng xong — trước đó chưa canh
    if (typeof IntersectionObserver === "undefined" || !ref.current) { setThay(true); return; }
    const io = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) { setThay(true); io.disconnect(); }
    }, { rootMargin: "300px" });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [thay, san]);
  if (thay) return <>{children}</>;
  return (
    <div ref={ref} className="tai-khi-thay">
      <h2 style={{ marginTop: 28 }}>{ten}</h2>
      <p className="muted">Đang tải…</p>
    </div>
  );
}
