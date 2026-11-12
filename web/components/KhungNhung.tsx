"use client";
import { useState } from "react";

/** KHUNG NHÚNG MỘT MÀN ĐANG CHẠY vào một bàn làm việc riêng (VH-41 · 12/11/2026 — tách từ /xe để bàn
 *  Marketing & PR dùng chung). Không chép lại màn nào: mọi luật, mọi cửa nhập vẫn là của màn gốc.
 *  Cùng tên miền nên khung đọc được trang con: giấu thanh ngang và thanh dọc của nó (bàn đã có) và
 *  tự co chiều cao theo nội dung.
 *
 *  Liên kết bấm TRONG khung:
 *  · `ngoai(href)` trả true → bàn tự xử lý (vd. một ô trên bàn Phó TGĐ trỏ `/marketing?tab=…` thì bàn
 *    đổi nhóm tại chỗ, không mở bàn lồng trong bàn).
 *  · đường dẫn thuộc `cuaBan` → mở NGAY TRONG KHUNG.
 *  · còn lại (trang chủ, phân hệ khác của CRM) → không đi đâu cả; lối ra duy nhất là thanh đầu. */
export default function KhungNhung({ toi, ten, mo, cuaBan, ngoai, anDauBan }: {
  toi: string; ten: string; mo?: string; cuaBan: (href: string) => boolean; ngoai?: (href: string) => boolean;
  /** VH-43: giấu thanh đầu `.mh01-ban` của bàn nhúng — bàn ngoài đã có một thanh, hai thanh là lặp. */
  anDauBan?: boolean;
}) {
  const [cao, setCao] = useState(640);
  const src = toi + (mo ? (toi.includes("?") ? "&" : "?") + `mo=${mo}` : "");
  const doCao = (f: HTMLIFrameElement) => {
    try {
      const doc = f.contentDocument;
      const b = doc?.body;
      if (!doc || !b) return;
      if (!doc.getElementById("vtos-nhung")) {
        const st = doc.createElement("style");
        st.id = "vtos-nhung";
        st.textContent = ".top,aside.side{display:none!important}main{max-width:none!important;padding:0!important;margin:0!important}body{background:transparent!important}"
          // VH-6: vụn đường «VTOS · … » dẫn về trang chủ CRM — trong bàn thì giấu, cùng mũi tên «mở tab mới».
          + ".thanh-viec .tv-duong,.thanh-viec .tv-mui{display:none!important}"
          // VH-33: trong khung chỉ giữ việc CHÍNH của màn; «‹ Lên một cấp» và lối sang màn khác đã có trên
          // thanh nghiệp vụ của bàn — giữ lại là lặp nút trên một màn. Thanh trống thì giấu.
          + ".thanh-viec a.tv:not(.chinh),.thanh-viec .tv-nhan{display:none!important}.thanh-viec:not(:has(a.tv.chinh)){display:none!important}";
        if (anDauBan) st.textContent += ".mh01-ban{display:none!important}";
        doc.head.appendChild(st);
        doc.addEventListener("click", (e) => {
          const a = (e.target as HTMLElement | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
          if (!a) return;
          const h = a.getAttribute("href") || "";
          if (!h.startsWith("/")) return;
          e.preventDefault();
          if (ngoai && ngoai(h)) return;
          if (cuaBan(h)) f.contentWindow?.location.assign(h);
        }, true);
      }
      const dat = () => setCao(Math.max(400, b.scrollHeight + 24));
      dat();
      const ro = new ResizeObserver(dat);
      ro.observe(b);
    } catch { /* khác nguồn thì giữ chiều cao mặc định */ }
  };
  return <iframe key={src} src={src} title={ten} onLoad={(e) => doCao(e.currentTarget)}
    style={{ width: "100%", height: cao, border: 0, display: "block" }} />;
}
