"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, fmtD } from "@/lib/api";
import { TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, errMsg } from "@/components/ui";

function Tours() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]); const [ops, setOps] = useState<any[]>([]); const [open, setOpen] = useState(false);
  const load = () => api("/tours").then(setRows).catch(() => {});
  useEffect(() => { load(); api("/users?role=nv_dh,tp_dh").then(setOps).catch(() => {}); }, []);
  const canCreate = ["nv_dh", "tp_dh"].includes(user?.role || "");
  async function create(e: React.FormEvent) {
    e.preventDefault(); const f = new FormData(e.target as HTMLFormElement); const d: any = Object.fromEntries(f.entries());
    ["price_per_pax", "fixed_cost", "var_cost_per_pax", "planned_pax", "operator_id"].forEach((k) => (d[k] = Number(d[k] || 0)));
    try { const t = await api("/tours", { method: "POST", json: d }); toast("Đã tạo tour – kiểm tra 3 con số rồi trình Trưởng phòng"); location.href = `/tours/${t.id}`; } catch (x) { toast(errMsg(x), true); }
  }
  const today = new Date().toISOString().slice(0, 10);
  return (<>
    <h1>Tour & dự toán</h1>
    {canCreate && <details className="panel" open={open} onToggle={(e) => setOpen((e.target as any).open)}>
      <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--navy)" }}>+ Tạo tour / dự toán (chỉ Điều hành)</summary>
      <form onSubmit={create}>
        <div className="grid"><div><label>Mã tour</label><input name="code" required placeholder="VD: PT-DL-1015" /></div>
          <div><label>Loại chuyến</label><select name="tour_type">{Object.entries(TOUR_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div></div>
        <label>Tên tour</label><input name="name" required />
        <div className="grid"><div><label>Khởi hành</label><input type="date" name="start_date" required /></div><div><label>Kết thúc</label><input type="date" name="end_date" required /></div>
          <div><label>Người điều hành duy nhất</label><select name="operator_id" defaultValue={user?.id}>{ops.map((o) => <option key={o.id} value={o.id}>{o.full_name}</option>)}</select></div></div>
        <h3>Dự toán – tách chi phí cố định / theo khách (ĐH Điều 11)</h3>
        <div className="grid"><div><label>Giá bán / khách (đ)</label><input type="number" name="price_per_pax" step="1000" /></div><div><label>Chi phí cố định</label><input type="number" name="fixed_cost" step="1000" /></div>
          <div><label>Chi phí theo khách</label><input type="number" name="var_cost_per_pax" step="1000" /></div><div><label>Số khách dự toán</label><input type="number" name="planned_pax" /></div></div>
        <label>Điểm dừng nghỉ (bắt buộc)</label><input name="rest_stops" />
        <button className="act teal">Lưu nháp</button>
      </form></details>}
    <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Khởi hành</th><th className="num">Biên KH</th><th className="num">Hòa vốn</th><th className="num">Đạt 10%</th><th className="num">Đã bán</th><th>Trạng thái</th><th>Hạn QT</th></tr></thead>
      <tbody>{rows.map((t) => { const c = t.calc; return <tr key={t.id}><td><Link href={`/tours/${t.id}`}>{t.code}</Link></td><td>{t.name}</td><td>{TOUR_TYPES[t.tour_type]}</td><td>{fmtD(t.start_date)}</td>
        <td className="num">{c.complete ? <Tag cls={c.pass_gate ? "ok" : "red"}>{pct(c.margin)}</Tag> : "–"}</td><td className="num">{c.breakeven_pax ?? "–"}</td><td className="num">{c.pax_for_margin ?? "–"}</td>
        <td className="num">{t.booked_pax} {t.d7_flag && <Tag cls="red">D-7</Tag>}</td><td>{TOUR_STATUS[t.status]} {t.below_margin && <Tag cls="warn">dưới biên</Tag>}</td>
        <td>{fmtD(t.settlement_deadline)} {t.status === "ket_thuc" && today > t.settlement_deadline && <Tag cls="red">quá hạn</Tag>}</td></tr>; })}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Tours /></Shell>; }
