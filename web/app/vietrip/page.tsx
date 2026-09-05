"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const E: Record<string, string> = { tour: "Tour", booking: "Booking", receipt: "Phiếu thu khách", supplier_payment: "Chi NCC", settlement: "Quyết toán chi tiết tour", user: "Người dùng", vehicle: "Xe", proposal: "Đề xuất chi" };

function Vietrip() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [st, setSt] = useState<any>(null);
  const [ent, setEnt] = useState("booking");
  const [rows, setRows] = useState<any[]>([]);
  const [unapplied, setUnapplied] = useState(false);
  const load = useCallback(() => { api("/import/vietrip/status").then(setSt).catch((e) => toast(errMsg(e), true)); api(`/import/vietrip/records?entity=${ent}&limit=50&unapplied=${unapplied}`).then(setRows).catch(() => {}); }, [ent, unapplied]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const apply = async () => { try { const r = await api("/import/vietrip/apply", { method: "POST" }); toast(r.message + " – " + Object.entries(r.applied).map(([k, v]) => `${k}: ${v}`).join(", ")); load(); } catch (x) { toast(errMsg(x), true); } };
  return (<>
    <h1>Đồng bộ Vietrip → VTOS (chuyển đổi dữ liệu, mục 11.3)</h1>
    <p className="muted">Robot đồng bộ chạy trong trình duyệt đã đăng nhập Vietrip (CNTT), đọc API Vietrip và đẩy vào VTOS theo lô; VTOS giữ bản gốc (vt_records) rồi ánh xạ sang tour, booking, phiếu thu, chi NCC, dòng chi phí quyết toán, người dùng, xe. Mã Vietrip lưu trong trường tham chiếu (VT…, VTPT…, VTDC…). Dữ liệu nhập không sinh bút toán – số dư đầu kỳ lấy từ MISA/BCTC khi cắt chuyển.</p>
    {st && <div className="kpis">{Object.entries(st).map(([k, v]: any) => <div className="kpi" key={k}><b>{v.total}</b><span>{E[k] || k} · đã ánh xạ {v.applied}{v.from && ` · ${fmtD(v.from)} → ${fmtD(v.to)}`}</span></div>)}</div>}
    {["cntt", "ketoan"].includes(role) && <button className="act orange" onClick={apply}>Ánh xạ dữ liệu đã nạp vào VTOS</button>}
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>{Object.entries(E).map(([k, l]) => <button key={k} className={"act " + (ent === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setEnt(k)}>{l}</button>)}
      <label><input type="checkbox" checked={unapplied} onChange={(e) => setUnapplied(e.target.checked)} /> chỉ bản ghi chưa ánh xạ</label></div>
    <div className="panel wrap"><table><thead><tr><th>Vietrip ID</th><th>Tham chiếu</th><th>Ngày</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Ánh xạ</th><th>Ghi chú</th><th>Đồng bộ lúc</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td className="mono">{r.vietrip_id}</td><td>{r.ref}</td><td>{fmtD(r.on_date)}</td><td style={{ textAlign: "right" }}>{vnd(r.amount)}</td><td>{r.applied ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">chưa</Tag>}</td><td className="muted">{r.apply_note}</td><td className="muted">{fmtDT(r.synced_at)}</td></tr>) : <tr><td colSpan={7} className="muted">Chưa có dữ liệu.</td></tr>}</tbody></table></div>
    <p className="muted">Kịch bản đồng bộ: <code>docs/vietrip-sync.js</code> trong repo – CNTT mở trang Vietrip đã đăng nhập, dán vào Console cùng token VTOS, chọn khoảng ngày; chạy lại bất kỳ lúc nào (không nhân bản).</p>
  </>);
}
export default function Page() { return <Shell><Vietrip /></Shell>; }
