"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Bảng sẵn sàng vận hành đội xe (Chủ tịch duyệt bản xem trước 10/11/2026).
 *
 *  Máy đếm còn thiếu gì để đội xe chạy thật trên VTOS; mỗi dòng mở đúng cửa nhập. Đủ hết thì thu
 *  thành một dòng. Màn hình chỉ in lại điều máy chủ trả (`/fleet/san-sang-van-hanh`) — không tự suy. */
export default function SanSangVanHanh({ ky, mo }: { ky: string; mo: (trang: string) => void }) {
  const [d, setD] = useState<any>(null);
  const [gon, setGon] = useState(false);
  useEffect(() => { api(`/fleet/san-sang-van-hanh?ky=${ky}`).then(setD).catch(() => setD(null)); }, [ky]);
  if (!d) return null;
  if (d.du) return <p className="tag ok" style={{ display: "inline-block", marginBottom: 12 }}>Đội xe đủ điều kiện vận hành · {d.tong}/{d.tong} mục</p>;
  const mau: Record<string, string> = { ok: "ok", warn: "warn", bad: "red" };
  return <section className="panel" aria-label="Sẵn sàng vận hành" style={{ marginBottom: 14 }}>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ flex: "1 1 260px", minWidth: 0 }}>
        <strong>Sẵn sàng vận hành {d.dat} / {d.tong} mục</strong>
        <div style={{ height: 8, borderRadius: 999, background: "#dce3ec", overflow: "hidden", marginTop: 4 }}>
          <div style={{ height: "100%", width: `${Math.round((d.dat / d.tong) * 100)}%`, background: "#1d5bbf" }} /></div>
      </div>
      <button type="button" onClick={() => setGon(!gon)} aria-expanded={!gon}>{gon ? "Mở rộng" : "Thu gọn"}</button>
    </div>
    {!gon && <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12, marginTop: 10 }}>
      {Object.entries(d.nhom).map(([ma, ten]: any) => <div key={ma} style={{ border: "1px solid #dce3ec", borderRadius: 8, padding: "8px 12px", minWidth: 0 }}>
        <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{ten}</h3>
        {d.dong.filter((x: any) => x.nhom === ma).map((x: any) =>
          <div key={x.ma} style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px dashed #e6eaf0" }}>
            <span style={{ minWidth: 0 }}>{x.ten}{x.ghi && <div className="muted" style={{ fontSize: 12.5 }}>{x.ghi}</div>}</span>
            <span style={{ display: "flex", gap: 6, alignItems: "center", whiteSpace: "nowrap" }}>
              <span className={`tag ${mau[x.muc]}`}>{x.so == null ? (x.dat ? "Đủ" : "Chưa") : x.so}</span>
              {!x.dat && x.mo && <button type="button" onClick={() => mo(x.mo)}>{x.nut}</button>}
            </span>
          </div>)}
      </div>)}
    </div>}
  </section>;
}
