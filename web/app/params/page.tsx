"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

function Params() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]);
  const load = useCallback(() => api("/params").then(setRows), []);
  useEffect(() => { load(); }, [load]);
  const active = rows.filter((p) => p.status === "active"); const keys = Array.from(new Set(active.map((p) => p.key)));
  async function propose(e: React.FormEvent) {
    e.preventDefault(); const f = e.target as HTMLFormElement; const d: any = Object.fromEntries(new FormData(f).entries());
    try { const r = await api("/params", { method: "POST", json: d }); toast(r.message); f.reset(); load(); } catch (x) { toast(errMsg(x), true); }
  }
  async function sign(id: number) { try { const r = await api(`/params/${id}/sign`, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); } }
  const canSign = ["chutich", "tgd"].includes(user?.role || "");
  return (<>
    <h1>Tham số chính sách – hiệu lực theo ngày, đổi phải đủ 2 chữ ký</h1>
    <div className="panel"><h2>Đề xuất thay đổi</h2>
      <form onSubmit={propose}><div className="grid">
        <div><label>Tham số</label><select name="key">{keys.map((k) => <option key={k} value={k}>{k} – {active.find((p) => p.key === k)?.label}</option>)}</select></div>
        <div><label>Giá trị mới</label><input name="value" required /></div>
        <div><label>Hiệu lực từ</label><input type="date" name="effective_from" required defaultValue={new Date().toISOString().slice(0, 10)} /></div>
        <div><label>Căn cứ</label><input name="source" /></div>
      </div><button className="act orange">Trình Chủ tịch + TGĐ</button></form></div>
    <div className="panel wrap"><table><thead><tr><th>Khóa</th><th>Tên</th><th className="num">Giá trị</th><th>Đơn vị</th><th>Hiệu lực</th><th>Căn cứ</th><th>Trạng thái</th><th>Chữ ký</th><th></th></tr></thead>
      <tbody>{rows.map((p) => <tr key={p.id}><td className="mono">{p.key}</td><td>{p.label}</td><td className="num">{p.key === "thang_f_bang" ? <FTable v={p.value} /> : <b>{Number(p.value) >= 1000 ? vnd(Number(p.value)) : p.value}</b>}</td><td>{p.unit}</td><td>{fmtD(p.effective_from)}</td><td className="muted">{p.source}</td>
        <td><Tag cls={p.status === "active" ? "ok" : "warn"}>{p.status}</Tag></td><td>CT {p.signed_chutich ? "✔" : "…"} · TGĐ {p.signed_tgd ? "✔" : "…"}</td>
        <td>{p.status === "pending" && canSign && <button className="act" style={{ margin: 0 }} onClick={() => sign(p.id)}>Ký</button>}</td></tr>)}</tbody></table></div>
  </>);
}
function FTable({ v }: { v: string }) {
  const rows = v.split(",").map((x) => x.split(":")).filter((x) => x.length === 2);
  return (<details><summary><b>Bảng B.1 – {rows.length} bậc (bấm xem)</b></summary>
    <table style={{ fontSize: 12, marginTop: 4 }}><thead><tr><th>Bậc</th><th>Từ % mốc</th><th>HCM (mốc 200tr)</th><th>Tỉnh (mốc 120tr)</th><th>Hệ số</th></tr></thead>
      <tbody><tr><td>f0</td><td>dưới {rows[0]?.[0]}%</td><td>dưới {vnd(Number(rows[0]?.[0]) / 100 * 200e6)}</td><td>dưới {vnd(Number(rows[0]?.[0]) / 100 * 120e6)}</td><td>0%</td></tr>
        {rows.map(([t, r], i) => <tr key={t}><td>{i === rows.length - 1 ? "trần" : `f${i + 1}`}</td><td>{t}%</td><td>{vnd(Number(t) / 100 * 200e6)}</td><td>{vnd(Number(t) / 100 * 120e6)}</td><td>{r}%</td></tr>)}</tbody></table>
    <div className="muted">Hoa hồng = hệ số bậc sàn × (doanh thu tính chỉ tiêu − mốc), không nội suy; chỉ booking đủ 4 trường bắt buộc.</div></details>);
}
export default function Page() { return <Shell><Params /></Shell>; }
