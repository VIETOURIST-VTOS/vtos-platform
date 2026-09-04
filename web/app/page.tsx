"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, pct } from "@/lib/api";
import { ACTION_LABEL } from "@/lib/meta";
import { Tag } from "@/components/ui";

function Dash() {
  const { user } = useShell();
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/dashboard").then(setD).catch(() => {}); }, []);
  if (!d) return <p className="muted">Đang tải…</p>;
  const c = d.counts || {};
  return (<>
    <h1>Bảng điều khiển · {user?.role_name}</h1>
    <div className="kpis">
      <div className="kpi"><b>{d.n_tours}</b><span>tour trên hệ thống</span></div>
      <div className="kpi"><b>{c.da_duyet || 0}</b><span>đang bán (đã duyệt)</span></div>
      <div className="kpi"><b>{(c.ket_thuc || 0) + (c.da_dong_so || 0)}</b><span>chờ quyết toán / Kế toán</span></div>
      <div className="kpi"><b>{d.pending_requests}</b><span>yêu cầu chưa tạo booking</span></div>
      <div className="kpi"><b style={{ color: "var(--red)" }}>{d.alerts.length}</b><span>cảnh báo mở cho vai trò này</span></div>
    </div>
    <div className="grid" style={{ marginTop: 14 }}>
      <div className="panel"><h2>Việc cần xử lý</h2>
        {d.todo.length ? <ul>{d.todo.map((t: any, i: number) => <li key={i}><Link href={`/tours/${t.tour_id}`}>{t.code}</Link> – {t.name}: <b>{ACTION_LABEL[t.action] || t.action}</b></li>)}</ul> : <p className="muted">Không có việc chờ ở vai trò này.</p>}
        {d.pending_params > 0 && ["chutich", "tgd"].includes(user?.role || "") && <p><Link href="/params">{d.pending_params} tham số chính sách chờ ký</Link></p>}
      </div>
      <div className="panel"><h2>Cảnh báo từ robot</h2>
        {d.alerts.length ? <table><tbody>{d.alerts.map((a: any) => <tr key={a.id}><td><Tag cls={a.level}>{a.kind}</Tag></td><td>{a.message}</td></tr>)}</tbody></table> : <p className="muted">Không có cảnh báo.</p>}
      </div>
    </div>
    <p className="muted">Ngưỡng biên đang áp dụng {pct(d.threshold)} · Robot chạy mỗi 10 phút; CNTT có thể chạy tay ở trang Cảnh báo.</p>
  </>);
}
export default function Page() { return <Shell><Dash /></Shell>; }
