"use client";
import { useState } from "react";
import { getToken } from "@/lib/api";

/** VH-13 · NÚT «XUẤT EXCEL» của đội xe (Chủ tịch duyệt bản xem trước 11/11/2026): viền xanh lá, một nút một
 *  bảng. Tải tệp từ cửa `.xlsx` của máy chủ — cửa ấy đọc đúng hàm của màn hình nên tệp và màn ra cùng số.
 *  `duong` là đường sau /api/v1 (vd. `/fleet/hieu-qua.xlsx?ky=2026-11`). */
export default function NutExcel({ duong, ten }: { duong: string; ten: string }) {
  const [dang, setDang] = useState(false);
  const [loi, setLoi] = useState("");
  const tai = async () => {
    setDang(true); setLoi("");
    try {
      const res = await fetch(`/api/v1${duong}`, { headers: { Authorization: `Bearer ${getToken() || ""}` } });
      if (!res.ok) throw new Error(res.status === 403 ? "Vai trò của bạn không được xuất bảng này" : `Máy chủ trả ${res.status}`);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = ten;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
    } catch (e: any) { setLoi(e?.message || "Không tải được"); }
    setDang(false);
  };
  return <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
    <style>{CSS}</style>
    <button type="button" className="nut-excel" onClick={tai} disabled={dang} aria-busy={dang}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
        <path d="M14 3v6h6M9 13l6 6M15 13l-6 6" /></svg>
      {dang ? "Đang xuất…" : "Xuất Excel"}
    </button>
    {loi && <small style={{ color: "var(--red, #b72f45)" }}>{loi}</small>}
  </span>;
}

const CSS = `
.nut-excel{display:inline-flex;align-items:center;gap:8px;border:1px solid #1f7a4d;background:#fff;color:#1f7a4d;
  font:inherit;font-weight:700;border-radius:10px;padding:8px 14px;cursor:pointer;margin:0;transition:background .15s,color .15s}
.nut-excel svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.nut-excel:hover:not(:disabled){background:#1f7a4d;color:#fff}
.nut-excel:disabled{opacity:.6;cursor:progress}
.nut-excel:focus-visible{outline:3px solid #7cc6a0;outline-offset:2px}
`;
