"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const MANAGERS = ["tp_dh", "gd_kd", "ptgd_doan", "ptgd_mkt", "tgd", "chutich", "hcns", "cntt", "bks"];
const today = () => new Date().toISOString().slice(0, 10);
const thisMonth = () => new Date().toISOString().slice(0, 7);

function Reports() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const isMgr = MANAGERS.includes(role);
  const [tab, setTab] = useState(isMgr ? "all" : "mine");
  const [period, setPeriod] = useState(thisMonth());
  const [f, setF] = useState({ report_date: today(), part1_done: "", part2_numbers: "", part3_issues: "", part4_plan: "" });
  const [rows, setRows] = useState<any[]>([]);
  const [sum, setSum] = useState<any>(null);
  const [shifts, setShifts] = useState<any[]>([]);
  const [emps, setEmps] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [fs, setFs] = useState({ shift_date: today(), slot: "toi", employee_id: "" });
  const load = useCallback(() => {
    if (tab === "mine") api(`/daily-reports?mine=1&period=${period}`).then(setRows);
    if (tab === "all") { api(`/daily-reports?period=${period}`).then(setRows); api(`/daily-reports/summary?period=${period}`).then(setSum).catch(() => {}); }
    if (tab === "shifts") { api(`/page-shifts?period=${period}`).then(setShifts); if (isMgr) api("/employees?department=kd_le").then(setEmps).catch(() => {}); }
  }, [tab, period, isMgr]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const score = (r: any) => r.manager_score ?? r.robot_score;

  return (<>
    <h1>Báo cáo ngày (Điều 12) &amp; ca trực page</h1>
    <p className="muted">Khối Kinh doanh, Đoàn, Điều hành, Marketing, CNTT: nộp báo cáo 4 phần <b>trước 20:00</b> mỗi ngày làm việc (Thứ Hai – Thứ Bảy) thay chấm công. Robot chấm điểm nháp, trưởng phòng chấm chính thức; thiếu 1 ngày → nhắc nhở, 2 ngày liên tiếp → chuyển HCNS. Xếp loại tháng A/B/C/D là cảnh báo sớm, căn cứ đánh giá 3 tháng.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {[["mine", "Báo cáo của tôi"], ...(isMgr ? [["all", "Tổng hợp phòng"]] : []), ["shifts", "Ca trực page"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Tháng <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "mine" && <>
      <div className="panel"><h2>Nộp báo cáo ngày</h2>
        <label>Ngày<input type="date" value={f.report_date} max={today()} onChange={(e) => setF({ ...f, report_date: e.target.value })} /></label>
        <label>1. Việc đã làm hôm nay &amp; kết quả<textarea rows={3} value={f.part1_done} onChange={(e) => setF({ ...f, part1_done: e.target.value })} /></label>
        <label>2. Số liệu ngày (lead, booking, doanh thu, chuyến, hồ sơ… theo mẫu phòng)<textarea rows={2} value={f.part2_numbers} onChange={(e) => setF({ ...f, part2_numbers: e.target.value })} /></label>
        <label>3. Khó khăn – đề xuất<textarea rows={2} value={f.part3_issues} onChange={(e) => setF({ ...f, part3_issues: e.target.value })} /></label>
        <label>4. Kế hoạch ngày mai<textarea rows={2} value={f.part4_plan} onChange={(e) => setF({ ...f, part4_plan: e.target.value })} /></label>
        <button className="act" disabled={!f.part1_done || !f.part4_plan} onClick={() => post("/daily-reports", f).then((r) => r && setF({ ...f, part1_done: "", part2_numbers: "", part3_issues: "", part4_plan: "" }))}>Nộp báo cáo</button>
        <span className="muted"> Mỗi phần ≥ 20 ký tự = 2 điểm, đúng giờ = 2 điểm (nháp robot).</span></div>
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Nộp lúc</th><th>Đúng giờ</th><th>Điểm robot</th><th>Điểm TP</th><th>Nhận xét</th></tr></thead>
        <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td>{fmtD(r.report_date)}</td><td>{fmtDT(r.submitted_at)}</td><td>{r.on_time ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">trễ</Tag>}</td><td>{r.robot_score}/10 <span className="muted">{r.robot_note}</span></td><td>{r.manager_score ?? "–"}</td><td className="muted">{r.manager_note}</td></tr>) : <tr><td colSpan={6} className="muted">Chưa có báo cáo trong tháng.</td></tr>}</tbody></table></div>
    </>}

    {tab === "all" && <>
      {sum && <><h2>Xếp loại tháng {period} ({sum.work_days} ngày làm việc tính đến nay)</h2>
        <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th>Đã nộp</th><th>Đúng giờ</th><th>TP đã chấm</th><th>Thiếu</th><th>Điểm BQ</th><th>Xếp loại</th></tr></thead>
          <tbody>{sum.rows.map((r: any) => <tr key={r.code}><td className="mono">{r.code}</td><td><b>{r.name}</b></td><td>{r.department}</td><td>{r.submitted}/{r.work_days}</td><td>{r.on_time}</td><td>{r.reviewed}</td><td>{r.missing ? <Tag cls={r.missing >= 2 ? "red" : "warn"}>{r.missing}</Tag> : "0"}</td><td>{r.avg}</td><td><Tag cls={r.grade === "A" ? "ok" : r.grade === "B" ? "navy" : r.grade === "C" ? "warn" : "red"}>{r.grade}</Tag></td></tr>)}</tbody></table></div>
        {["cntt", "hcns", "tgd"].includes(role) && <button className="act orange" onClick={() => post("/daily-reports/check-missing")}>Robot rà thiếu báo cáo</button>}</>}
      <h2>Báo cáo chi tiết – bấm để xem và chấm</h2>
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Người</th><th>Phòng</th><th>Đúng giờ</th><th>Robot</th><th>TP</th><th></th></tr></thead>
        <tbody>{rows.map((r) => <>
          <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.id ? null : r.id)}><td>{fmtD(r.report_date)}</td><td><b>{r.user}</b></td><td>{r.department}</td><td>{r.on_time ? "✔" : <Tag cls="warn">trễ</Tag>}</td><td>{r.robot_score}</td><td>{r.manager_score ?? "–"}</td>
            <td onClick={(e) => e.stopPropagation()}>{!r.reviewed_by && <button className="act teal" style={{ margin: 0 }} onClick={() => { const s = prompt(`Điểm cho ${r.user} (0–10), gợi ý robot ${r.robot_score}:`, String(r.robot_score)); if (s !== null) { const n = prompt("Nhận xét:") || ""; post(`/daily-reports/${r.id}/review`, { score: Number(s), note: n }); } }}>Chấm</button>}</td></tr>
          {open === r.id && <tr key={r.id + "d"}><td colSpan={7}><div style={{ margin: "4px 0 8px 16px" }}><b>1. Đã làm:</b> {r.part1_done}<br /><b>2. Số liệu:</b> {r.part2_numbers}<br /><b>3. Khó khăn:</b> {r.part3_issues}<br /><b>4. Kế hoạch:</b> {r.part4_plan}<br /><span className="muted">Robot: {r.robot_note}{r.manager_note && ` · TP: ${r.manager_note}`}</span></div></td></tr>}
        </>)}</tbody></table></div>
    </>}

    {tab === "shifts" && <>
      {["gd_kd", "cntt"].includes(role) && <div className="panel"><h2>Phân ca trực page (GĐ KD)</h2><div className="grid">
        <label>Ngày<input type="date" value={fs.shift_date} onChange={(e) => setFs({ ...fs, shift_date: e.target.value })} /></label>
        <label>Ca<select value={fs.slot} onChange={(e) => setFs({ ...fs, slot: e.target.value })}><option value="sang">Sáng</option><option value="chieu">Chiều</option><option value="toi">Tối</option></select></label>
        <label>Nhân viên<select value={fs.employee_id} onChange={(e) => setFs({ ...fs, employee_id: e.target.value })}><option value="">–</option>{emps.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}</select></label>
      </div><button className="act" disabled={!fs.employee_id} onClick={() => post("/page-shifts", { ...fs, employee_id: Number(fs.employee_id) })}>Phân ca</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Ca</th><th>Nhân viên</th><th>Lượt sót &gt;5 phút</th><th>Chế tài</th><th>Ghi chú robot</th><th>NV phản hồi</th><th></th></tr></thead>
        <tbody>{shifts.length ? shifts.map((s) => <tr key={s.id}><td>{fmtD(s.shift_date)}</td><td>{s.slot}</td><td>{s.employee}</td><td>{s.scanned_at ? s.missed : <span className="muted">chưa quét</span>}</td><td>{s.penalty ? <Tag cls="red">−{vnd(s.penalty)}</Tag> : s.scanned_at ? <Tag cls="ok">0</Tag> : ""}{s.kicked && <Tag cls="red">loại ca</Tag>}</td><td className="muted">{s.missed_note}</td><td className="muted">{s.responded}</td>
          <td>{["cntt", "gd_kd"].includes(role) && <button className="act grey" style={{ margin: 0 }} onClick={() => { const n = prompt("Số lượt sót > 5 phút:", String(s.missed)); if (n !== null) post(`/page-shifts/${s.id}/scan`, { missed: Number(n), note: prompt("Ghi chú:") || "" }); }}>Quét</button>}{s.employee_id && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={() => { const t = prompt("Phản hồi (trong 3 ngày):"); if (t) post(`/page-shifts/${s.id}/respond`, { text: t }); }}>Phản hồi</button>}</td></tr>) : <tr><td colSpan={8} className="muted">Chưa có ca trong tháng.</td></tr>}</tbody></table></div>
      <p className="muted">Cổng 11: 1–3 lượt −100.000/lượt; 4–5 lượt −200.000/lượt; ≥6 lượt loại khỏi ca tháng sau và điều chỉnh chỉ tiêu. Chỉ trừ vào hoa hồng (đã nối vào bảng lương).</p>
    </>}
  </>);
}
export default function Page() { return <Shell><Reports /></Shell>; }
