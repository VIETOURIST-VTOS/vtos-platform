import type { Metadata, Viewport } from "next";
import "./globals.css";
import CaiDatApp from "@/components/CaiDatApp";

export const metadata: Metadata = {
  title: "VTOS – Vietourist Operating System",
  description: "Hệ thống quản trị nội bộ Vietourist Holdings",
  manifest: "/manifest.json",
  applicationName: "VTOS",
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
  formatDetection: { telephone: false },
};
// Màu thanh trạng thái trình duyệt = navy thương hiệu, để thanh hệ thống của điện thoại liền màu
// với thanh ngang của trang.
export const viewport: Viewport = { themeColor: "#14538D", width: "device-width", initialScale: 1 };

/* MÀN HÌNH CHỜ CHO iPHONE/iPAD.
 * Android tự dựng màn hình chờ từ manifest (icon + background_color), không cần khai gì.
 * iOS thì không: thiếu apple-touch-startup-image là người dùng nhìn màn hình TRẮNG
 * suốt 2–3 giây mỗi lần mở app, tưởng máy treo. Phải khai từng khổ máy một.
 * Mỗi dòng: [rộng CSS, cao CSS, tỷ lệ điểm ảnh, tên tệp trong /public/splash].
 * Thêm máy mới thì thêm một dòng ở đây và sinh thêm một ảnh cùng khổ điểm ảnh.
 */
const MAN_HINH_CHO: [number, number, number, string][] = [
  [320, 568, 2, "splash-640x1136.png"],    // iPhone SE (đời 1)
  [375, 667, 2, "splash-750x1334.png"],    // iPhone 8, SE 2/3
  [414, 896, 2, "splash-828x1792.png"],    // iPhone XR, 11
  [414, 736, 3, "splash-1242x2208.png"],   // iPhone 8 Plus
  [375, 812, 3, "splash-1125x2436.png"],   // iPhone X, XS, 11 Pro
  [390, 844, 3, "splash-1170x2532.png"],   // iPhone 12, 13, 14
  [393, 852, 3, "splash-1179x2556.png"],   // iPhone 14 Pro, 15, 16
  [402, 874, 3, "splash-1206x2622.png"],   // iPhone 16 Pro
  [414, 896, 3, "splash-1242x2688.png"],   // iPhone XS Max, 11 Pro Max
  [428, 926, 3, "splash-1284x2778.png"],   // iPhone 12–14 Pro Max
  [430, 932, 3, "splash-1290x2796.png"],   // iPhone 14 Pro Max, 15/16 Plus
  [440, 956, 3, "splash-1320x2868.png"],   // iPhone 16 Pro Max
  [768, 1024, 2, "splash-1536x2048.png"],  // iPad 9.7"
  [810, 1080, 2, "splash-1620x2160.png"],  // iPad 10.2"
  [834, 1194, 2, "splash-1668x2388.png"],  // iPad Pro 11"
  [1024, 1366, 2, "splash-2048x2732.png"], // iPad Pro 12.9"
];

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

        {/* Tên hiện dưới icon trên iPhone khi cài vào màn hình chính */}
        <meta name="apple-mobile-web-app-title" content="VTOS" />
        <meta name="mobile-web-app-capable" content="yes" />

        {MAN_HINH_CHO.map(([rong, cao, ty_le, tep]) => (
          <link
            key={tep}
            rel="apple-touch-startup-image"
            href={`/splash/${tep}`}
            media={`(device-width: ${rong}px) and (device-height: ${cao}px) and (-webkit-device-pixel-ratio: ${ty_le}) and (orientation: portrait)`}
          />
        ))}
      </head>
      <body>
        {children}
        <CaiDatApp />
        <script dangerouslySetInnerHTML={{ __html: `if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))}` }} />
      </body>
    </html>
  );
}
