import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VTOS – Vietourist Operating System",
  description: "Hệ thống quản trị nội bộ Vietourist Holdings",
  manifest: "/manifest.json",
  icons: { icon: "/icon-192.png", apple: "/icon-192.png" },
  appleWebApp: { capable: true, title: "VTOS", statusBarStyle: "default" },
};
export const viewport: Viewport = { themeColor: "#1F3A5F", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        {/* Zalo Platform xác thực quyền sở hữu domain vtos.infinitytours.org (08/9/2026).
            Thẻ này phải nằm ở HEAD TRANG CHỦ và ở gần đầu trang – Zalo chỉ đọc 512KB đầu tiên.
            Gỡ thẻ ra là mất xác thực domain, kéo theo mất quyền gọi API Zalo OA của hộp thư đa kênh. */}
        <meta name="zalo-platform-site-verification" content="VyIH6BJWInypriytmjXq6m7usaBjZW0KE3Gs" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" />
      </head>
      <body>
        {children}
        <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))}` }} />
      </body>
    </html>
  );
}
