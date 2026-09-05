"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const E: Record<string, string> = { product: "Sản phẩm", tour: "Tour", booking: "Booking", receipt: "Phiếu thu khách", supplier_payment: "Chi NCC", settlement: "Quyết toán chi tiết tour", user: "Người dùng", vehicle: "Xe", proposal: "Đề xuất chi" };

function Vietrip() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [st, setSt] = useState<any>(null);
  const [ent, setEnt] = useState("booking");
  const [rows, setRows] = useState<any[]>([]);
  const [unapplied, setUnapplied] = useState(false);
  const [rb, setRb] = useState<any>(null);
  const [rf, setRf] = useState({ from_date: new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10), to_date: new Date().toISOString().slice(0, 10), products: false, settlements_days: "10" });
  const loadRb = useCallback(() => api("/import/vietrip/robot-status").then(setRb).catch(() => {}), []);
  useEffect(() => { loadRb(); const t = setInterval(loadRb, 15000); return () => clearInterval(t); }, [loadRb]);
  const runRobot = async () => { try { const r = await api("/import/vietrip/sync", { method: "POST", json: { ...rf, settlements_days: Number(rf.settlements_days) || 10 } }); toast(r.message); loadRb(); } catch (x) { toast(errMsg(x), true); } };
  const load = useCallback(() => { api("/import/vietrip/status").then(setSt).catch((e) => toast(errMsg(e), true)); api(`/import/vietrip/records?entity=${ent}&limit=50&unapplied=${unapplied}`).then(setRows).catch(() => {}); }, [ent, unapplied]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const apply = async () => { try { const r = await api("/import/vietrip/apply", { method: "POST" }); toast(r.message + " – " + Object.entries(r.applied).map(([k, v]) => `${k}: ${v}`).join(", ")); load(); } catch (x) { toast(errMsg(x), true); } };
  return (<>
    <h1>Đồng bộ Vietrip → VTOS (chuyển đổi dữ liệu, mục 11.3)</h1>
    <p className="muted">Robot đồng bộ chạy trong trình duyệt đã đăng nhập Vietrip (CNTT), đọc API Vietrip và đẩy vào VTOS theo lô; VTOS giữ bản gốc (vt_records) rồi ánh xạ sang tour, booking, phiếu thu, chi NCC, dòng chi phí quyết toán, người dùng, xe. Mã Vietrip lưu trong trường tham chiếu (VT…, VTPT…, VTDC…). Dữ liệu nhập không sinh bút toán – số dư đầu kỳ lấy từ MISA/BCTC khi cắt chuyển.</p>
    {st && <div className="kpis">{Object.entries(st).map(([k, v]: any) => <div className="kpi" key={k}><b>{v.total}</b><span>{E[k] || k} · đã ánh xạ {v.applied}{v.from && ` · ${fmtD(v.from)} → ${fmtD(v.to)}`}</span></div>)}</div>}
    {rb && <div className="panel"><h2>Robot đồng bộ tự động (phía máy chủ – không cần mở Chrome)</h2>
      <div className="grid">
        <div><b>Tài khoản robot Vietrip</b><div>{rb.credentials_set ? <Tag cls="ok">Đã cấu hình</Tag> : <Tag cls="red">Chưa đặt VIETRIP_PHONE / VIETRIP_PASSWORD trên Render</Tag>}</div><div className="muted">Nên tạo riêng 1 tài khoản Vietrip quyền Kế toán/Giám đốc chỉ để robot đọc.</div></div>
        <div><b>Trạng thái</b><div>{rb.running ? <Tag cls="warn">Đang chạy từ {fmtDT(rb.started)}</Tag> : rb.error ? <Tag cls="red">Lỗi: {rb.error}</Tag> : rb.finished ? <Tag cls="ok">Xong {fmtDT(rb.finished)}</Tag> : <Tag>Chưa chạy</Tag>}</div>
          {rb.result && <div className="muted">{Object.entries(rb.result).filter(([k]) => k !== "applied").map(([k, v]: any) => `${k}: ${v}`).join(" · ")}{rb.result.applied && ` · ánh xạ: ${Object.entries(rb.result.applied).map(([k, v]) => `${k} ${v}`).join(", ")}`}</div>}</div>
        <div><b>Lịch tự động (GitHub Actions)</b><div className="muted">03:00 hằng ngày: đồng bộ 7 ngày gần nhất + quyết toán tour kết thúc 10 ngày · SePay 30 phút/lần · báo cáo ngày 20:30 · tuần T7 · tháng ngày 10. Cần đặt secret ROBOT_TOKEN trên GitHub.</div></div>
      </div>
      {["cntt", "ketoan"].includes(role) && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <label>Từ <input type="date" value={rf.from_date} onChange={(e) => setRf({ ...rf, from_date: e.target.value })} /></label>
        <label>Đến <input type="date" value={rf.to_date} onChange={(e) => setRf({ ...rf, to_date: e.target.value })} /></label>
        <label>Quyết toán tour kết thúc trong (ngày) <input type="number" value={rf.settlements_days} onChange={(e) => setRf({ ...rf, settlements_days: e.target.value })} style={{ width: 70 }} /></label>
        <label><input type="checkbox" checked={rf.products} onChange={(e) => setRf({ ...rf, products: e.target.checked })} /> kéo lại 354 sản phẩm (~10 phút)</label>
        <button className="act" style={{ margin: 0 }} disabled={rb.running || !rb.credentials_set} onClick={runRobot}>Chạy robot ngay</button>
      </div>}
      {rb.log?.length > 0 && <details><summary className="muted">Nhật ký chạy ({rb.log.length})</summary><pre style={{ fontSize: 12, maxHeight: 220, overflow: "auto" }}>{rb.log.join("\n")}</pre></details>}
    </div>}
    {["cntt", "ketoan"].includes(role) && <button className="act orange" onClick={apply}>Ánh xạ dữ liệu đã nạp vào VTOS</button>}
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>{Object.entries(E).map(([k, l]) => <button key={k} className={"act " + (ent === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setEnt(k)}>{l}</button>)}
      <label><input type="checkbox" checked={unapplied} onChange={(e) => setUnapplied(e.target.checked)} /> chỉ bản ghi chưa ánh xạ</label></div>
    <div className="panel wrap"><table><thead><tr><th>Vietrip ID</th><th>Tham chiếu</th><th>Ngày</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Ánh xạ</th><th>Ghi chú</th><th>Đồng bộ lúc</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td className="mono">{r.vietrip_id}</td><td>{r.ref}</td><td>{fmtD(r.on_date)}</td><td style={{ textAlign: "right" }}>{vnd(r.amount)}</td><td>{r.applied ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">chưa</Tag>}</td><td className="muted">{r.apply_note}</td><td className="muted">{fmtDT(r.synced_at)}</td></tr>) : <tr><td colSpan={7} className="muted">Chưa có dữ liệu.</td></tr>}</tbody></table></div>
    <p className="muted">Cách 2 (thủ công): kịch bản <code>docs/vietrip-sync.js</code> trong repo – CNTT mở trang Vietrip đã đăng nhập, dán vào Console cùng token VTOS, chọn khoảng ngày; chạy lại bất kỳ lúc nào (không nhân bản).</p>
  </>);
}
export default function Page() { return <Shell><Vietrip /></Shell>; }
