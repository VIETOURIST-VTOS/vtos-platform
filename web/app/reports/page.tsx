"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const MANAGERS = ["tp_dh", "gd_kd", "tp_kd", "tn_kd", "ptgd_doan", "ptgd_mkt", "tgd", "chutich", "hcns", "cntt", "bks"];
const today = () => new Date().toISOString().slice(0, 10);
const thisMonth = () => new Date().toISOString().slice(0, 7);

const EX: Record<string, Record<string, string>> = {};   // không dùng ví dụ mẫu – để trống để nhân viên tự nhập

function Countdown({ seconds }: { seconds: number }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => { setLeft(seconds); const t = setInterval(() => setLeft((x) => Math.max(0, x - 1)), 1000); return () => clearInterval(t); }, [seconds]);
  const h = Math.floor(left / 3600), m = Math.floor((left % 3600) / 60);
  return <div style={{ textAlign: "right" }}><b style={{ fontSize: 22, color: left > 0 ? "var(--orange)" : "var(--red)" }}>{left > 0 ? `${h} giờ ${m} phút` : "Đã quá 20 giờ"}</b><br /><span className="muted">{left > 0 ? "còn lại để gửi trước 20 giờ" : "báo cáo nộp lúc này tính là trễ"}</span></div>;
}

function DailyForm({ onDone, rows }: { onDone: () => void; rows: any[] }) {
  const { user, toast } = useShell();
  const [form, setForm] = useState<any>(null);
  const [dept, setDept] = useState("");
  const [f, setF] = useState<any>({ report_date: today(), part1_done: "", part3_issues: "", part4_plan: "" });
  const [p2, setP2] = useState<Record<string, string>>({});
  const [pv, setPv] = useState<{ subject: string; body: string; lines: number } | null>(null);
  const [sent, setSent] = useState<any>(null);
  useEffect(() => { api("/daily-reports/form").then((r) => { setForm(r); setDept(r.department); if (r.today) { setF({ report_date: r.today.report_date, part1_done: r.today.part1_done, part3_issues: r.today.part3_issues, part4_plan: r.today.part4_plan }); setP2(r.today.part2 || {}); } }).catch((e) => toast(errMsg(e), true)); }, [toast]);
  const fields: string[] = form?.forms?.[dept]?.fields || [];
  const payload = { ...f, department: dept, part2_numbers: Object.fromEntries(fields.map((k) => [k, p2[k] || ""])) };
  useEffect(() => { if (!form) return; const t = setTimeout(() => api("/daily-reports/preview", { method: "POST", json: payload }).then(setPv).catch(() => {}), 400); return () => clearTimeout(t); }, [JSON.stringify(payload), form]);   // eslint-disable-line react-hooks/exhaustive-deps
  const isMgr = MANAGERS.includes(user?.role || "");
  const submit = async () => { try { const r = await api("/daily-reports", { method: "POST", json: payload }); toast(r.message); setSent(r); onDone(); } catch (e) { toast(errMsg(e), true); } };
  const clear = () => { setF({ ...f, part1_done: "", part3_issues: "", part4_plan: "" }); setP2({}); };
  if (!form) return <p className="muted">Đang tải mẫu báo cáo…</p>;
  const ta = (k: string, rows = 4, ph = "") => <textarea rows={rows} value={f[k]} placeholder={ph} onChange={(e) => setF({ ...f, [k]: e.target.value })} style={{ width: "100%" }} />;
  return (<>
    <div className="panel" style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
      <div><h2 style={{ marginBottom: 2 }}>Báo cáo công việc hằng ngày</h2><span className="muted">Vietourist Holdings · gửi báo cáo trước <b>20 giờ</b> mỗi ngày làm việc · áp dụng từ 01/9/2026 (Điều 12)</span></div>
      <Countdown seconds={form.seconds_left} />
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
      {Object.entries(form.forms).map(([k, v]: any) => <button key={k} className={"act " + (dept === k ? "teal" : "grey")} style={{ margin: 0, borderRadius: 20 }} disabled={!isMgr && k !== form.department} onClick={() => { setDept(k); setP2({}); }}>{v.name}</button>)}
    </div>
    {form.today && !sent && <div className="gate pass">Hôm nay anh/chị đã nộp lúc {fmtDT(form.today.submitted_at)} (điểm nháp {form.today.robot_score}/10). Sửa và nộp lại được tới khi trưởng phòng chấm.</div>}
    <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1.4fr) minmax(280px, 1fr)" }}>
      <div className="panel">
        <div className="grid" style={{ gridTemplateColumns: "2fr 1fr 1fr" }}>
          <label>Họ và tên<input value={form.full_name} readOnly /></label>
          <label>Mã nhân viên<input value={form.staff_code || ""} readOnly placeholder="chưa có – HCNS cập nhật" /></label>
          <label>Ngày báo cáo<input type="date" value={f.report_date} max={today()} onChange={(e) => setF({ ...f, report_date: e.target.value })} /></label>
        </div>
        <h3><Tag cls="ok">Phần 1</Tag> Việc đã làm hôm nay</h3>
        <p className="muted" style={{ margin: "0 0 6px" }}>Mỗi việc một dòng. {form.forms[dept]?.hint}</p>
        {ta("part1_done", 6, "Ví dụ: Gọi lại 12 lead Facebook, chốt booking BK2609-0123 tour Đà Lạt 3N2Đ 4 khách 15.600.000 đ…")}
        <h3><Tag cls="ok">Phần 2</Tag> Số liệu trong ngày – {form.forms[dept]?.name}</h3>
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
          {fields.map((k) => <label key={k}>{k}<input value={p2[k] || ""} placeholder="không" onChange={(e) => setP2({ ...p2, [k]: e.target.value })} /></label>)}
        </div>
        <h3><Tag cls="ok">Phần 3</Tag> Việc ngày mai</h3>
        {ta("part4_plan", 3, "Việc dự kiến làm ngày mai, có mốc giờ / khách / mã tour nếu có")}
        <h3><Tag cls="ok">Phần 4</Tag> Vướng mắc – đề xuất</h3>
        {ta("part3_issues", 2, "Không có thì ghi: không")}
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>
          <button className="act teal" disabled={!f.part1_done.trim() || !f.part4_plan.trim()} onClick={submit}>Gửi báo cáo</button>
          <button className="act grey" onClick={clear}>Xoá hết</button>
          <span className="muted">Robot chấm nháp: Phần 1 (3đ) · Phần 2 đủ mục (3đ) · Việc ngày mai (2đ) · trước 20h (2đ). Trưởng phòng chấm chính thức.</span>
        </div>
      </div>
      <div className="panel" style={{ background: "var(--panel2)" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}><h3 style={{ margin: 0 }}>Nội dung thư</h3><span className="muted">{pv?.lines || 0} dòng</span></div>
        <p className="muted" style={{ margin: "8px 0 2px", fontSize: 11 }}>TIÊU ĐỀ THƯ</p>
        <div className="mono" style={{ fontSize: 12.5 }}>{pv?.subject}</div>
        <p className="muted" style={{ margin: "10px 0 2px", fontSize: 11 }}>NỘI DUNG</p>
        <pre className="mono" style={{ whiteSpace: "pre-wrap", fontSize: 12.5, margin: 0, maxHeight: 520, overflow: "auto" }}>{pv?.body}</pre>
        {sent && <div className="gate pass" style={{ marginTop: 10 }}>Đã gửi. Điểm nháp robot {sent.report.robot_score}/10 · {sent.report.robot_note}</div>}
      </div>
    </div>
    <div className="panel wrap"><h2>Báo cáo của tôi trong tháng</h2><table><thead><tr><th>Ngày</th><th>Nộp lúc</th><th>Đúng giờ</th><th>Điểm robot</th><th>Điểm TP</th><th>Nhận xét</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td>{fmtD(r.report_date)}</td><td>{fmtDT(r.submitted_at)}</td><td>{r.on_time ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">trễ</Tag>}</td><td>{r.robot_score}/10 <span className="muted">{r.robot_note}</span></td><td>{r.manager_score ?? "–"}</td><td className="muted">{r.manager_note}</td></tr>) : <tr><td colSpan={6} className="muted">Chưa có báo cáo trong tháng.</td></tr>}</tbody></table></div>
  </>);
}

function Reports() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const isMgr = MANAGERS.includes(role);
  const [tab, setTab] = useState(isMgr ? "all" : "mine");
  const [period, setPeriod] = useState(thisMonth());
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

    {tab === "mine" && <DailyForm onDone={load} rows={rows} />}

    {tab === "all" && <>
      {sum && <><h2>Xếp loại tháng {period} ({sum.work_days} ngày làm việc tính đến nay)</h2>
        <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th>Đã nộp</th><th>Đúng giờ</th><th>TP đã chấm</th><th>Thiếu</th><th>Điểm BQ</th><th>Xếp loại</th></tr></thead>
          <tbody>{sum.rows.map((r: any) => <tr key={r.code}><td className="mono">{r.code}</td><td><b>{r.name}</b></td><td>{r.department}</td><td>{r.submitted}/{r.work_days}</td><td>{r.on_time}</td><td>{r.reviewed}</td><td>{r.missing ? <Tag cls={r.missing >= 2 ? "red" : "warn"}>{r.missing}</Tag> : "0"}</td><td>{r.avg}</td><td><Tag cls={r.grade === "A" ? "ok" : r.grade === "B" ? "navy" : r.grade === "C" ? "warn" : "red"}>{r.grade}</Tag></td></tr>)}</tbody></table></div>
        {["cntt", "hcns", "tgd"].includes(role) && <button className="act orange" onClick={() => post("/daily-reports/check-missing")}>Robot rà thiếu báo cáo</button>}</>}
      <h2>Báo cáo chi tiết – bấm để xem và chấm</h2>
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Người</th><th>Phòng</th><th>Đúng giờ</th><th>Robot</th><th>TP</th><th></th></tr></thead>
        <tbody>{rows.map((r) => <>
          <tr key={r.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.id ? null : r.id)}><td>{fmtD(r.report_date)}</td><td><b>{r.user}</b> <span className="muted mono">{r.staff_code}</span></td><td>{r.department_name || r.department}</td><td>{r.on_time ? "✔" : <Tag cls="warn">trễ</Tag>}</td><td>{r.robot_score}</td><td>{r.manager_score ?? "–"}</td>
            <td onClick={(e) => e.stopPropagation()}>{!r.reviewed_by && <button className="act teal" style={{ margin: 0 }} onClick={() => { const s = prompt(`Điểm cho ${r.user} (0–10), gợi ý robot ${r.robot_score}:`, String(r.robot_score)); if (s !== null) { const n = prompt("Nhận xét:") || ""; post(`/daily-reports/${r.id}/review`, { score: Number(s), note: n }); } }}>Chấm</button>}</td></tr>
          {open === r.id && <tr key={r.id + "d"}><td colSpan={7}><div style={{ margin: "4px 0 8px 16px" }}><b>1. Đã làm:</b> <span style={{ whiteSpace: "pre-wrap" }}>{r.part1_done}</span><br /><b>2. Số liệu ({r.department_name}):</b> {Object.entries(r.part2 || {}).map(([k, v]: any) => <span key={k}> · {k}: <b>{v || "không"}</b></span>)}<br /><b>3. Ngày mai:</b> {r.part4_plan}<br /><b>4. Vướng mắc:</b> {r.part3_issues}<br /><span className="muted">Robot: {r.robot_note}{r.manager_note && ` · TP: ${r.manager_note}`}</span></div></td></tr>}
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
