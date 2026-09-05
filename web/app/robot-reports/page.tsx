"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const K: Record<string, string> = { ngay: "Ngày", tuan: "Tuần", thang: "Tháng" };
function md(s: string) {
  return s.split("\n").map((l, i) => l.startsWith("# ") ? <h1 key={i}>{l.slice(2)}</h1> : l.startsWith("## ") ? <h2 key={i}>{l.slice(3)}</h2> : l.startsWith("  - ") ? <div key={i} style={{ marginLeft: 24 }}>• {l.slice(4)}</div> : l.startsWith("- ") ? <div key={i}>• {l.slice(2).split("**").map((x, j) => j % 2 ? <b key={j}>{x}</b> : x)}</div> : <div key={i}>{l}</div>);
}

function Robot() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [rows, setRows] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const load = useCallback(() => api("/auto-reports").then(setRows).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  const run = async (kind: string) => { try { const r = await api(`/auto-reports/${kind}`, { method: "POST" }); toast(r.message); load(); setOpen(r.report.id); } catch (x) { toast(errMsg(x), true); } };
  return (<>
    <h1>Robot R7 – báo cáo quản trị tự động</h1>
    <p className="muted">Robot gom số liệu từ hệ thống (không sửa dữ liệu) và viết nhận xét ngắn (Claude API khi có khóa, không thì theo quy tắc). Lịch đề xuất qua n8n: báo cáo ngày 20:30, tuần Thứ Bảy, tháng ngày 10 – gọi <code>POST /api/v1/robot/report/&#123;ngay|tuan|thang&#125;</code> với X-Robot-Token, rồi gửi Zalo/Email cho Chủ tịch, TGĐ, Kế toán.</p>
    {["cntt", "tgd", "chutich", "ketoan"].includes(role) && <div>{Object.entries(K).map(([k, l]) => <button key={k} className="act" onClick={() => run(k)}>Lập báo cáo {l.toLowerCase()} ngay</button>)}</div>}
    <div className="panel wrap"><table><thead><tr><th>Loại</th><th>Kỳ</th><th>Lập lúc</th><th>Nhận xét</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <>
        <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.id ? null : r.id)}><td><Tag cls="navy">{K[r.kind]}</Tag></td><td><b>{r.period}</b></td><td>{fmtDT(r.created_at)} · {r.created_by}</td><td className="muted">{r.comment.slice(0, 160)}{r.comment.length > 160 ? "…" : ""}</td></tr>
        {open === r.id && <tr key={r.id + "c"}><td colSpan={4}><div className="panel" style={{ margin: 8 }}>{md(r.content)}</div></td></tr>}
      </>) : <tr><td colSpan={4} className="muted">Chưa có báo cáo – bấm lập ngay.</td></tr>}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Robot /></Shell>; }
