"use client";

import { useEffect, useState } from "react";

/* Khung nhắc cài VTOS vào màn hình chính.
 *
 * Vì sao cần: 103 nhân viên sẽ không tự biết ba bước cài của iPhone. Không có khung này
 * thì "app" vẫn chỉ là một cái tab trình duyệt và không ai dùng.
 *
 * Hai đường khác nhau, không gộp được:
 *  - Android/Chrome: trình duyệt bắn sự kiện beforeinstallprompt → bắt lấy, hiện NÚT CÀI thật.
 *  - iPhone/Safari: Apple không cho gọi hộp cài, chỉ còn cách CHỈ ba bước bằng chữ.
 *
 * Tự ẩn khi: đã chạy ở chế độ app (standalone), hoặc người dùng bấm "Để sau"
 * (nhớ 30 ngày trong localStorage của chính máy đó).
 */

const KHOA_TAT = "vtos_an_nhac_cai_dat";
const SO_NGAY_NHO = 30;

type SuKienCai = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

function dangChayNhuApp() {
  if (typeof window === "undefined") return true;
  const w = window as unknown as { navigator: { standalone?: boolean } };
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.matchMedia("(display-mode: minimal-ui)").matches ||
    w.navigator.standalone === true
  );
}

function laIphone() {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  const iOS = /iPad|iPhone|iPod/.test(ua) || (ua.includes("Mac") && "ontouchend" in document);
  const safari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
  return iOS && safari;
}

function daTat() {
  try {
    const moc = Number(localStorage.getItem(KHOA_TAT) || 0);
    return moc > Date.now();
  } catch {
    return false;
  }
}

export default function CaiDatApp() {
  const [hien, datHien] = useState(false);
  const [ios, datIos] = useState(false);
  const [suKien, datSuKien] = useState<SuKienCai | null>(null);

  useEffect(() => {
    if (dangChayNhuApp() || daTat()) return;

    // Android: chờ trình duyệt cho phép cài
    const bat = (e: Event) => {
      e.preventDefault();
      datSuKien(e as SuKienCai);
      datHien(true);
    };
    window.addEventListener("beforeinstallprompt", bat);

    // iPhone: không có sự kiện nào để chờ, hiện hướng dẫn sau 3 giây cho đỡ giật màn hình
    if (laIphone()) {
      const h = setTimeout(() => {
        datIos(true);
        datHien(true);
      }, 3000);
      return () => {
        clearTimeout(h);
        window.removeEventListener("beforeinstallprompt", bat);
      };
    }

    const xong = () => datHien(false);
    window.addEventListener("appinstalled", xong);
    return () => {
      window.removeEventListener("beforeinstallprompt", bat);
      window.removeEventListener("appinstalled", xong);
    };
  }, []);

  if (!hien) return null;

  const deSau = () => {
    try {
      localStorage.setItem(KHOA_TAT, String(Date.now() + SO_NGAY_NHO * 86400000));
    } catch {
      /* chế độ riêng tư chặn localStorage – chấp nhận, lần sau hiện lại */
    }
    datHien(false);
  };

  const caiNgay = async () => {
    if (!suKien) return;
    await suKien.prompt();
    try {
      await suKien.userChoice;
    } catch {
      /* người dùng đóng hộp thoại */
    }
    datHien(false);
  };

  return (
    <div
      role="dialog"
      aria-label="Cài VTOS vào màn hình chính"
      style={{
        position: "fixed",
        left: 12,
        right: 12,
        bottom: "max(12px, env(safe-area-inset-bottom))",
        zIndex: 9999,
        margin: "0 auto",
        maxWidth: 520,
        /* Nền tối 13/9: thẻ mời cài app trước đây tô trắng cứng, nên nó là ô giấy duy nhất nổi
           trên cả nền tối. Lấy nền thẻ của bộ nhận diện. */
        background: "var(--vtos-card, #122C45)",
        color: "var(--vtos-text, #E8F1F8)",
        border: "1px solid var(--vtos-line, #E3E9EF)",
        borderRadius: "var(--vtos-radius-lg, 16px)",
        boxShadow: "0 12px 32px rgba(11,37,69,.20)",
        padding: 14,
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        fontFamily: "var(--vtos-font-text, 'Be Vietnam Pro', system-ui, sans-serif)",
        fontSize: 14,
        lineHeight: 1.5,
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/favicon/icon-192.png" alt="" width={44} height={44} style={{ borderRadius: 11, flexShrink: 0 }} />

      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontWeight: 700,
            fontSize: 15,
            fontFamily: "var(--vtos-font-display, 'Space Grotesk', sans-serif)",
          }}
        >
          Cài VTOS vào màn hình chính
        </div>

        {ios ? (
          <div style={{ marginTop: 6, color: "var(--vtos-text-mute, #64798C)" }}>
            Bấm nút <strong style={{ color: "inherit" }}>Chia sẻ</strong> ở thanh dưới của Safari →
            kéo xuống chọn <strong>Thêm vào MH chính</strong> → bấm <strong>Thêm</strong>.
          </div>
        ) : (
          <div style={{ marginTop: 6, color: "var(--vtos-text-mute, #64798C)" }}>
            Mở nhanh như một ứng dụng, không phải gõ địa chỉ mỗi lần.
          </div>
        )}

        <div style={{ marginTop: 10, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!ios && (
            <button
              onClick={caiNgay}
              style={{
                padding: "9px 18px",
                fontSize: 14,
                fontWeight: 600,
                /* --vtos-navy nay là màu CHỮ (#6FA8F0), không còn là màu nền như bản sáng: chữ
                   trắng trên nó chỉ đạt 2,0 lần. Nền nút là --vtos-sky, chữ trắng đạt 5,72. */
                color: "var(--vtos-text-on-navy, #FFFFFF)",
                background: "var(--vtos-sky, #1E63C8)",
                border: "none",
                borderRadius: "var(--vtos-radius-md, 9px)",
                cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              Cài ngay
            </button>
          )}
          <button
            onClick={deSau}
            style={{
              padding: "9px 16px",
              fontSize: 14,
              fontWeight: 500,
              color: "var(--vtos-text-mute, #64798C)",
              background: "transparent",
              border: "1px solid var(--vtos-line, #E3E9EF)",
              borderRadius: "var(--vtos-radius-md, 9px)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Để sau
          </button>
        </div>
      </div>
    </div>
  );
}
