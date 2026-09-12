import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VTOS – Vietourist Operating System",
  description: "Hệ thống quản trị nội bộ Vietourist Holdings",
  manifest: "/manifest.json",
  // Bộ favicon của bộ nhận diện VTOS v1.0 (mục 2 của README-IT). Ô BO GÓC, không dùng ký hiệu trần.
  icons: {
    icon: [
      { url: "/favicon/favicon.ico", sizes: "any" },
      { url: "/favicon/app-icon.svg", type: "image/svg+xml" },
      { url: "/favicon/icon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: "/favicon/icon-180.png",
  },
  appleWebApp: { capable: true, title: "VTOS", statusBarStyle: "default" },
};
// Màu thanh trạng thái trình duyệt = navy thương hiệu, để thanh hệ thống của điện thoại liền màu
// với thanh ngang của trang.
export const viewport: Viewport = { themeColor: "#14538D", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        {/* Zalo Platform xác thực quyền sở hữu domain vtos.infinitytours.org (08/9/2026).
            Thẻ này phải nằm ở HEAD TRANG CHỦ và ở gần đầu trang – Zalo chỉ đọc 512KB đầu tiên.
            Gỡ thẻ ra là mất xác thực domain, kéo theo mất quyền gọi API Zalo OA của hộp thư đa kênh. */}
        <meta name="zalo-platform-site-verification" content="VyIH6BJWInypriytmjXq6m7usaBjZW0KE3Gs" />
        {/* BA PHÔNG của bộ nhận diện VTOS v1.0, đúng đường dẫn README-IT mục 3 đưa ra:
            Space Grotesk (tiêu đề) · Be Vietnam Pro (chữ thường) · JetBrains Mono (tiền và mã).
            preconnect để phông về sớm hơn – thiếu nó thì lần tải đầu chữ nhảy một nhịp. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Be+Vietnam+Pro:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" />
      </head>
      <body>
        {children}
        <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))}` }} />
      </body>
    </html>
  );
}
