/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // KS-16h: link riêng của CTV — kh.vietourist.vn/CTV-0012 → cổng khách ghi nguồn 30 ngày (app/cong/page.tsx).
  async redirects() {
    return [
      { source: "/:ma(CTV-\\d{4,})", destination: "/cong?ctv=:ma", permanent: false },
      { source: "/:ma(ctv-\\d{4,})", destination: "/cong?ctv=:ma", permanent: false },
    ];
  },
  async rewrites() {
    // Chuyển /api/* sang backend (dev: localhost:8000; Vercel: đặt API_INTERNAL_URL = địa chỉ Render)
    const api = process.env.API_INTERNAL_URL || "http://localhost:8000";
    // KS-16q: ba trang riêng trên tên miền cổng — kh.vietourist.vn/hotel → /kham-pha/hotel (… /restaurant, /tours).
    // Phải chạy TRƯỚC hệ tệp (beforeFiles) vì /tours đã là màn VTOS; chỉ áp cho tên miền cổng ngoài.
    // TM-1 (Chủ tịch 02/11/2026): vietourist.com.vn chạy song song với vietourist.vn — kh./dt./ir. của cả hai.
    const cong = [{ type: "host", value: "(kh|dt|ir)\\.vietourist\\.(vn|com\\.vn)" }];
    const rieng = ["hotel", "restaurant", "tours"].flatMap((k) => [
      { source: `/${k}`, has: cong, destination: `/kham-pha/${k}` },
      { source: `/${k}/:id(\\d+)`, has: cong, destination: `/kham-pha/${k}/:id` },
    ]).concat([{ source: "/tours/don/:ma", has: cong, destination: "/kham-pha/tours/don/:ma" },   // TR-1: cổng thẻ trả về đơn
             { source: "/thanh-toan/:ma", has: cong, destination: "/kham-pha/thanh-toan/:ma" }]); // TR-1d: link thanh toán tour đoàn
    return { beforeFiles: rieng, afterFiles: [{ source: "/api/:path*", destination: `${api}/api/:path*` }], fallback: [] };
  },
};
export default nextConfig;
