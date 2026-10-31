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
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default nextConfig;
