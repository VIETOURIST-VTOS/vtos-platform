"use client";
/* KS-16s · «Xem trên bản đồ» kiểu Agoda (Chủ tịch duyệt bản xem thử 01/11/2026). Bản đồ nền OpenStreetMap (Leaflet,
   nạp động chỉ phía trình duyệt). Ghim hiện giá «từ»; bấm ghim chọn khách sạn; «Tìm khi di chuyển bản đồ» lọc danh sách
   theo vùng đang xem. Tọa độ do máy lấy từ địa chỉ (hoặc Điều hành dán link Google Maps) — chưa có thì không có ghim. */
import { useEffect, useRef } from "react";
import "leaflet/dist/leaflet.css";

export type Ghim = { id: number; vi_do: number; kinh_do: number; nhan: string };
type Khung = { s: number; w: number; n: number; e: number };

export const giaGon = (n?: number | null) =>
  n == null ? "Yêu cầu" : n >= 1e6 ? `₫ ${String(Math.round(n / 1e4) / 100).replace(".", ",")}tr` : `₫ ${Math.round(n / 1000)}k`;

export default function BanDoKs({ ghim, chon, onChon, onKhung, cao = 520, mot = false }: {
  ghim: Ghim[]; chon?: number | null; onChon?: (id: number) => void; onKhung?: (k: Khung) => void; cao?: number | string; mot?: boolean;
}) {
  const hop = useRef<HTMLDivElement>(null);
  const map = useRef<any>(null);
  const lop = useRef<any>(null);
  const L_ = useRef<any>(null);
  const goiKhung = useRef(onKhung);
  goiKhung.current = onKhung;

  useEffect(() => {
    let huy = false;
    import("leaflet").then((m) => {
      const L = (m as any).default || m;
      if (huy || !hop.current || map.current) return;
      L_.current = L;
      const bd = L.map(hop.current, { zoomControl: true, scrollWheelZoom: !mot, attributionControl: true }).setView([16.05, 108.2], 6);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(bd);
      bd.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
      lop.current = L.layerGroup().addTo(bd);
      bd.on("moveend", () => { const b = bd.getBounds(); goiKhung.current?.({ s: b.getSouth(), w: b.getWest(), n: b.getNorth(), e: b.getEast() }); });
      map.current = bd;
      ve(true);
      // khung bản đồ có thể chưa có kích thước lúc tạo (vừa bật, nằm trong khối dính) — đo lại rồi canh ghim
      setTimeout(() => { if (map.current) { map.current.invalidateSize(); ve(true); } }, 250);
    });
    return () => { huy = true; if (map.current) { map.current.remove(); map.current = null; } };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const ve = (canh = false) => {
    const L = L_.current, bd = map.current;
    if (!L || !bd) return;
    lop.current.clearLayers();
    for (const g of ghim) {
      const icon = L.divIcon({ className: "", html: `<span class="ksv-pin${g.id === chon ? " on" : ""}">${g.nhan}</span>`, iconSize: null, iconAnchor: [0, 0] });
      const mk = L.marker([g.vi_do, g.kinh_do], { icon, title: g.nhan, keyboard: true, zIndexOffset: g.id === chon ? 1000 : 0 });
      mk.on("click", () => onChon?.(g.id));
      lop.current.addLayer(mk);
    }
    if (canh && ghim.length) {
      if (ghim.length === 1) bd.setView([ghim[0].vi_do, ghim[0].kinh_do], mot ? 15 : 13);
      else bd.fitBounds(L.latLngBounds(ghim.map((g) => [g.vi_do, g.kinh_do])), { padding: [40, 40], maxZoom: 14 });
    }
  };
  const khoa = ghim.map((g) => `${g.id}:${g.nhan}`).join("|");
  useEffect(() => { ve(false); }, [khoa, chon]);  // eslint-disable-line react-hooks/exhaustive-deps
  const khoaVung = ghim.map((g) => g.id).sort().join(",");
  useEffect(() => { ve(true); }, [khoaVung]);  // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={hop} className="ksv-bando" style={{ height: cao }} role="region" aria-label="Bản đồ khách sạn" />;
}
