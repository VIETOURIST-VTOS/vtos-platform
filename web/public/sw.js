/* VTOS – service worker v2 (13/9/2026)
 *
 * Ba nguyên tắc, đọc kỹ trước khi sửa:
 *  1. KHÔNG BAO GIỜ lưu tạm phản hồi của /api/. Số liệu kế toán, dòng tiền, duyệt chi
 *     mà đọc từ bộ nhớ tạm thì người dùng nhìn thấy số cũ và tưởng là số thật. Mọi lệnh
 *     gọi API đều đi thẳng ra mạng, mất mạng thì báo lỗi – đó là hành vi đúng.
 *  2. Trang (điều hướng) lấy mạng trước, hỏng mới lấy bản đã lưu, không có nữa thì
 *     hiện trang /offline. Nhờ vậy mở app khi mất sóng vẫn ra màn hình có chữ,
 *     không phải khủng long trắng của trình duyệt.
 *  3. Tệp tĩnh của Next (/_next/static/...) có mã băm trong tên nên không bao giờ đổi
 *     nội dung – lấy bản đã lưu trước cho nhanh.
 *
 * Đổi PHIEN_BAN mỗi lần sửa tệp này: bản cũ sẽ bị xóa sạch khi bản mới kích hoạt.
 */
const PHIEN_BAN = "vtos-v2";
const KHO_VO = PHIEN_BAN + "-vo";       // trang, HTML
const KHO_TINH = PHIEN_BAN + "-tinh";   // js, css, ảnh, phông
const TRANG_MAT_MANG = "/offline";

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(KHO_VO).then((kho) => kho.addAll([TRANG_MAT_MANG])).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((ten) => Promise.all(
        ten.filter((t) => !t.startsWith(PHIEN_BAN)).map((t) => caches.delete(t))
      ))
      .then(() => self.clients.claim())
  );
});

// Cho phép trang yêu cầu bản mới kích hoạt ngay (nút "Tải lại bản mới").
self.addEventListener("message", (e) => {
  if (e.data === "BO_QUA_CHO") self.skipWaiting();
});

function laApi(url) {
  return url.pathname.startsWith("/api/")
    || url.pathname.startsWith("/robot/")
    || url.pathname.startsWith("/import/");
}

function laTepTinh(url) {
  return url.pathname.startsWith("/_next/static/")
    || /\.(js|css|png|jpg|jpeg|svg|ico|webp|woff2?)$/i.test(url.pathname);
}

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // phông Google, ảnh ngoài: để trình duyệt tự lo
  if (laApi(url)) return;                            // nguyên tắc 1
  if (url.pathname === "/sw.js" || url.pathname === "/manifest.json") return;

  // Nguyên tắc 2 – trang
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const ban_sao = res.clone();
          caches.open(KHO_VO).then((kho) => kho.put(req, ban_sao)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((cu) => cu || caches.match(TRANG_MAT_MANG)))
    );
    return;
  }

  // Nguyên tắc 3 – tệp tĩnh
  if (laTepTinh(url)) {
    e.respondWith(
      caches.match(req).then((cu) => {
        if (cu) return cu;
        return fetch(req).then((res) => {
          if (res && res.status === 200 && res.type === "basic") {
            const ban_sao = res.clone();
            caches.open(KHO_TINH).then((kho) => kho.put(req, ban_sao)).catch(() => {});
          }
          return res;
        });
      })
    );
    return;
  }

  // Còn lại: mạng trước, hỏng thì lấy bản đã lưu nếu có
  e.respondWith(fetch(req).catch(() => caches.match(req)));
});
