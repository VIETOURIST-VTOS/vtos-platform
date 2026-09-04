# VTOS Mobile (Capacitor)

Vỏ ứng dụng Android/iOS bọc bản web VTOS. Không cần viết lại giao diện: app mở `https://<domain>`; PWA đã hỗ trợ cài trực tiếp từ trình duyệt (Chrome → "Thêm vào màn hình chính"), Capacitor dùng khi cần phát hành lên Google Play / App Store hoặc thông báo đẩy.

```bash
cd mobile && npm install
VTOS_WEB_URL=https://vtos.<domain> npm run add:android   # cần Android Studio
npm run sync && npm run open:android                       # build APK trong Android Studio
```

iOS tương tự với `add:ios` (cần macOS + Xcode). Giai đoạn 2: thông báo đẩy (@capacitor/push-notifications) cho cảnh báo D-7, quá hạn quyết toán.
