"use client";
/* KS-16q (Chủ tịch duyệt bản xem thử 01/11/2026) · ba ô đầu tab «Khám phá» của cổng khách: Tour du lịch, Khách sạn,
   Nhà hàng & ẩm thực. Bấm ô nào mở trang riêng kh.vietourist.vn/tours, /hotel, /restaurant ở tab mới. */
import { useEffect, useState } from "react";
import { duongRieng, type TrangRieng } from "@/lib/cong";

const O: [TrangRieng, string, string, string][] = [
  ["tours", "Tour du lịch", "Tour trong nước, nước ngoài, tour đoàn theo yêu cầu", "linear-gradient(135deg,#0e7c6b,#3fb59d)"],
  ["hotel", "Khách sạn", "Khách sạn hợp tác, giá hợp đồng Vietourist, đặt giữ trả sau", "linear-gradient(135deg,#1d3f9a,#4f86e8)"],
  ["restaurant", "Nhà hàng & ẩm thực", "Hương vị Việt Nam, thực đơn, đặt bàn có ưu đãi", "linear-gradient(135deg,#8f3420,#e0794f)"],
];

export default function KhamPhaBaMuc() {
  const [goc, setGoc] = useState<Record<string, string>>({ tours: "/kham-pha/tours", hotel: "/kham-pha/hotel", restaurant: "/kham-pha/restaurant" });
  useEffect(() => { setGoc({ tours: duongRieng("tours"), hotel: duongRieng("hotel"), restaurant: duongRieng("restaurant") }); }, []);
  return <nav className="kp3" aria-label="Khám phá dịch vụ">
    <style dangerouslySetInnerHTML={{ __html: CSS }} />
    {O.map(([k, t, m, nen]) => <a key={k} className="kp3-o" href={goc[k]} target="_blank" rel="noopener">
      <span className="kp3-pic" style={{ background: nen }}><b>{t}</b><small>Mở trang riêng ↗</small></span>
      <span className="kp3-bd"><span>{m}</span><em>kh.vietourist.vn/{k}</em></span></a>)}
  </nav>;
}

const CSS = `
#vtd-access .kp3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
#vtd-access .kp3-o{display:flex;flex-direction:column;border-radius:16px;overflow:hidden;border:1px solid var(--vtd-line,#dfe6ef);background:var(--vtd-surface,#fff);color:inherit;text-decoration:none;transition:transform .15s,box-shadow .15s}
#vtd-access .kp3-o:hover{transform:translateY(-2px);box-shadow:0 10px 24px rgba(16,40,65,.14)}
#vtd-access .kp3-o:focus-visible{outline:3px solid var(--vtd-blue,#225bd6);outline-offset:2px}
#vtd-access .kp3-pic{position:relative;min-height:128px;display:flex;align-items:flex-end;padding:14px;color:#fff}
#vtd-access .kp3 .kp3-pic b{color:#fff;font-size:20px;font-weight:800;line-height:1.2}
#vtd-access .kp3 .kp3-pic small{position:absolute;top:10px;right:10px;background:rgba(0,0,0,.32);padding:3px 9px;border-radius:99px;font-size:11.5px;font-weight:600;color:#fff;line-height:1.4}
#vtd-access .kp3-bd{display:flex;flex-direction:column;gap:4px;padding:11px 14px 13px;font-size:13px;color:var(--vtd-muted,#52677f)}
#vtd-access .kp3-bd em{font-style:normal;font-weight:700;color:var(--vtd-blue,#225bd6);font-size:12.5px}
@media (max-width:720px){#vtd-access .kp3{grid-template-columns:1fr}#vtd-access .kp3-pic{min-height:96px}}
@media (prefers-reduced-motion:reduce){#vtd-access .kp3-o{transition:none}}
`;
