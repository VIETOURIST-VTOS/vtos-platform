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
    const cong = [{ type: "host", value: "(kh|dt|ir)\\.vietourist\\.vn" }];
    const rieng = ["hotel", "restaurant", "tours"].flatMap((k) => [
      { source: `/${k}`, has: cong, destination: `/kham-pha/${k}` },
      { source: `/${k}/:id(\\d+)`, has: cong, destination: `/kham-pha/${k}/:id` },
    ]);
    return { beforeFiles: rieng, afterFiles: [{ source: "/api/:path*", destination: `${api}/api/:path*` }], fallback: [] };
  },
};
export default nextConfig;
