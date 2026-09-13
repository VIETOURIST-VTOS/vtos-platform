"use client";

/* Trang hiện ra khi mở VTOS lúc không có mạng.
 * Service worker (public/sw.js) đã lưu sẵn trang này lúc cài, nên nó bật lên được
 * ngay cả khi máy chủ không với tới. KHÔNG hiện số liệu ở đây: mất mạng nghĩa là
 * số trong máy đã cũ, hiện ra là gây hiểu nhầm.
 */

export default function TrangMatMang() {
  return (
    <main
      style={{
        minHeight: "100dvh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 18,
        padding: 24,
        textAlign: "center",
        background: "var(--vtos-navy, #14538D)",
        color: "#FFFFFF",
        fontFamily: "var(--vtos-font-text, 'Be Vietnam Pro', system-ui, sans-serif)",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/favicon/icon-192.png" alt="VTOS" width={72} height={72} style={{ borderRadius: 17 }} />

      <h1
        style={{
          margin: 0,
          fontSize: 22,
          fontWeight: 700,
          fontFamily: "var(--vtos-font-display, 'Space Grotesk', sans-serif)",
        }}
      >
        Máy đang không có mạng
      </h1>

      <p style={{ margin: 0, maxWidth: 380, lineHeight: 1.6, opacity: 0.9, fontSize: 15 }}>
        VTOS lấy số liệu trực tiếp từ máy chủ nên cần có mạng mới mở được. Anh/chị kiểm tra
        wifi hoặc 4G rồi bấm nút bên dưới.
      </p>

      <button
        onClick={() => window.location.reload()}
        style={{
          marginTop: 6,
          padding: "12px 26px",
          fontSize: 15,
          fontWeight: 600,
          color: "var(--vtos-navy, #14538D)",
          background: "#FFFFFF",
          border: "none",
          borderRadius: 9,
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        Thử lại
      </button>

      <p style={{ margin: 0, fontSize: 12.5, opacity: 0.65 }}>
        Nếu đã có mạng mà vẫn báo lỗi, báo phòng CNTT.
      </p>
    </main>
  );
}
