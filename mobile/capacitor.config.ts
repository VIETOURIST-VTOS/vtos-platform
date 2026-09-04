import type { CapacitorConfig } from "@capacitor/cli";

/**
 * App di động VTOS = vỏ native (Capacitor) mở thẳng bản web.
 * Khi anh có tên miền: đổi server.url thành https://<domain>, build Android (APK/AAB) và iOS.
 * Ưu điểm: một mã nguồn web, cập nhật tính năng không cần phát hành lại app.
 */
const config: CapacitorConfig = {
  appId: "vn.com.vietourist.vtos",
  appName: "VTOS",
  webDir: "www",
  server: {
    url: process.env.VTOS_WEB_URL || "https://vtos.example.com",
    cleartext: false,
  },
  android: { allowMixedContent: false },
  ios: { contentInset: "automatic" },
};
export default config;
