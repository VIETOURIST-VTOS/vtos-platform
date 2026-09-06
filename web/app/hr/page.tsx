"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const TABS = [["payroll", "Bảng lương"], ["employees", "Hồ sơ nhân sự"], ["visa", "Hồ sơ visa"], ["guides", "HDV & phân chuyến"], ["fleet", "Đội xe"], ["incidents", "Sự vụ"]];
const PST: Record<string, [string, string]> = { nhap: ["Robot nháp", "warn"], kt_xac_nhan: ["Kế toán đã xác nhận cơ sở", "navy"], hcns_lap: ["HCNS đã lập – chờ TGĐ", "warn"], tgd_ky: ["TGĐ đã ký lô", "ok"] };
const NEXT: Record<string, [string, string]> = { nhap: ["ketoan", "Kế toán xác nhận cơ sở"], kt_xac_nhan: ["hcns", "HCNS lập bảng lương"], hcns_lap: ["tgd", "TGĐ ký lô & ghi sổ"] };
const lastMonth = () => { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - 1); return d.toISOString().slice(0, 7); };

function HR() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState("payroll");
  const [period, setPeriod] = useState(lastMonth());
  const [meta, setMeta] = useState<any>({ departments: {}, positions: {}, offices: {} });
  const [run, setRun] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [emps, setEmps] = useState<any[]>([]);
  const [visa, setVisa] = useState<any[]>([]);
  const [asg, setAsg] = useState<any[]>([]);
  const [veh, setVeh] = useState<any[]>([]);
  const [disp, setDisp] = useState<any[]>([]);
  const [fleet, setFleet] = useState<any>(null);
  const [inc, setInc] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [fEmp, setFEmp] = useState<any>({ full_name: "", department: "kd_le", position: "nv", office: "hcm", contract_type: "hdld", base_salary: "" });
  const [fVisa, setFVisa] = useState<any>({ customer_name: "", market: "", method: "tu_xu_ly", handler_id: "", office: "hcm", alliance: false, revenue: "" });
  const [fAsg, setFAsg] = useState<any>({ tour_id: "", guide_id: "", days: "", rate_per_day: "", rate_id: "", holiday: false });
  const [grates, setGrates] = useState<any[]>([]);
  const [fGrate, setFGrate] = useState<any>({ route: "", days: "", rate_per_day: "", old_rate_per_day: "", effective_from: new Date().toISOString().slice(0, 10) });
  const [incMeta, setIncMeta] = useState<any>(null);
  const [fDisp, setFDisp] = useState<any>({ tour_id: "", vehicle_id: "", date_from: "", date_to: "", rate_id: "" });
  const [rates, setRates] = useState<any[]>([]);
  const [fRate, setFRate] = useState<any>({ route: "", days: "", internal_price: "", partner_price: "", effective_from: new Date().toISOString().slice(0, 10) });
  const [fInc, setFInc] = useState<any>({ employee_id: "", level: "2", description: "", occurred_on: new Date().toISOString().slice(0, 10) });
  const canHR = ["hcns", "cntt"].includes(role), canDH = ["nv_dh", "tp_dh", "hcns", "cntt"].includes(role);

  const load = useCallback(async () => {
    if (!Object.keys(meta.departments).length) api("/hr/meta").then(setMeta);
    if (!emps.length) api("/employees").then(setEmps).catch(() => {});
    if (!tours.length) api("/tours").then(setTours).catch(() => {});
    if (tab === "payroll") api(`/payroll-runs/${period}`).then(setRun).catch((e) => toast(errMsg(e), true));
    if (tab === "employees") api("/employees").then(setEmps);
    if (tab === "visa") api("/visa").then(setVisa);
    if (tab === "guides") { api("/guide-assignments").then(setAsg); api("/guide-rates").then(setGrates); }
    if (tab === "fleet") { api("/vehicles").then(setVeh); api("/dispatch").then(setDisp); api("/vehicle-rates").then(setRates); api(`/fleet/summary?period=${period}`).then(setFleet); }
    if (tab === "incidents") { api("/incidents").then(setInc); api("/incident-levels").then(setIncMeta); }
  }, [tab, period]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any, method = "POST") => { try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const guides = emps.filter((e) => e.department === "huong_dan");
  const empName = (id: number) => emps.find((e) => e.id === id)?.full_name || id;

  return (<>
    <h1>Nhân sự – Lương (robot R6)</h1>
    <p className="muted">Thưởng và hoa hồng tính theo <b>tháng quyết toán</b>, căn cứ duy nhất là số liệu Kế toán đã xác nhận; chế tài chỉ chạm thưởng/hoa hồng, không trừ lương cơ bản (Điều 127.2 BLLĐ). Luồng: robot nháp → Kế toán xác nhận cơ sở → HCNS lập → TGĐ ký lô → bút toán 642/334, 632/338, TNCN 10% CTV.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ lương <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "payroll" && run && <>
      <div className="kpis">
        <div className="kpi"><b>{run.totals.so_nguoi}</b><span>Người · {run.totals.so_chuyen} chuyến KT xác nhận</span></div>
        <div className="kpi"><b>{vnd(run.totals.luong_cb)}</b><span>Lương cơ bản (sau thang giảm)</span></div>
        <div className="kpi"><b>{vnd(run.totals.bien_doi)}</b><span>Thu nhập biến đổi</span></div>
        <div className="kpi"><b>{vnd(run.totals.thuc_nhan)}</b><span>Thực nhận (đã trừ TNCN CTV {vnd(run.totals.tncn)})</span></div>
      </div>
      <p><Tag cls={PST[run.status]?.[1]}>{PST[run.status]?.[0]}</Tag> {run.kt_confirmed_by && <span className="muted"> · KT {run.kt_confirmed_by} {fmtDT(run.kt_confirmed_at)}</span>}{run.hcns_by && <span className="muted"> · HCNS {run.hcns_by} {fmtDT(run.hcns_at)}</span>}{run.tgd_by && <span className="muted"> · TGĐ {run.tgd_by} {fmtDT(run.tgd_at)} · {run.entry_ids?.length} chứng từ</span>}
        {run.status === "nhap" && ["hcns", "ketoan", "cntt"].includes(role) && <button className="act grey" onClick={() => api(`/payroll-runs/${period}?refresh=true`).then(setRun).then(() => toast("Đã tính lại nháp")).catch((e) => toast(errMsg(e), true))}>Tính lại nháp</button>}
        {NEXT[run.status] && NEXT[run.status][0] === role && <button className="act teal" onClick={() => post(`/payroll-runs/${period}/advance`)}>{NEXT[run.status][1]}</button>}</p>
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Họ tên</th><th>Phòng</th><th>HĐ</th><th style={{ textAlign: "right" }}>Lương CB</th><th style={{ textAlign: "right" }}>Biến đổi</th><th style={{ textAlign: "right" }}>TNCN</th><th style={{ textAlign: "right" }}>Thực nhận</th><th>Ghi chú robot</th></tr></thead>
        <tbody>{run.rows.map((r: any) => <>
          <tr key={r.ma} style={{ cursor: "pointer" }} onClick={() => setOpen(open === r.ma ? null : r.ma)}><td className="mono">{r.ma}</td><td><b>{r.ten}</b></td><td>{meta.departments[r.phong] || r.phong}<div className="muted">{meta.positions[r.chuc_vu]}</div></td><td>{r.hop_dong === "hdld" ? "HĐLĐ" : "CTV"}</td>
            <td style={{ textAlign: "right" }}>{vnd(r.luong_cb)}</td><td style={{ textAlign: "right" }}>{vnd(r.bien_doi)}</td><td style={{ textAlign: "right" }}>{r.tncn ? vnd(r.tncn) : ""}</td><td style={{ textAlign: "right" }}><b>{vnd(r.thuc_nhan)}</b></td><td className="muted" style={{ maxWidth: 320 }}>{r.ghi_chu}</td></tr>
          {open === r.ma && r.khoan.length > 0 && <tr key={r.ma + "k"}><td colSpan={9}><table style={{ margin: "4px 0 8px 24px", width: "auto" }}><tbody>{r.khoan.map((k: any, i: number) => <tr key={i}><td>{k.ten}</td><td style={{ textAlign: "right" }}>{vnd(k.tien)}</td><td className="muted">{k.ghi_chu}</td></tr>)}</tbody></table></td></tr>}
        </>)}</tbody></table></div>
      <p className="muted">Thang f KD Lẻ: f0–f4 = 0%, f5 = 0,5% … f19 = 4,7%, ≥1000% mốc = 5%; ngưỡng bậc tạm theo % mốc – HCNS nạp Bảng B.1 chính thức trước kỳ lương đầu. Thang đoàn f9–f0 theo bình quân LN 3 tháng / 30 triệu.</p>
    </>}

    {tab === "employees" && <>
      {canHR && <div className="panel"><h2>Danh sách nhân viên chính thức (bảng lương HCNS)</h2><p className="muted">Nạp mã NV / phòng / nhóm kinh doanh / chức vụ từ bảng lương HCNS đã đưa vào hệ thống (tháng 9/2026); ghép tài khoản theo họ tên, tạo tài khoản mới cho khối phải báo cáo ngày (mật khẩu ban đầu = mã NV). Nhân sự không còn trên bảng lương → ngưng hoạt động (không xóa).</p>
        <button className="act orange" onClick={() => post("/employees/import-master").then(() => api("/employees").then(setEmps))}>Nạp / cập nhật danh sách nhân viên</button></div>}
      {canHR && <div className="panel"><h2>Thêm hồ sơ</h2><div className="grid">
        <label>Họ tên<input value={fEmp.full_name} onChange={(e) => setFEmp({ ...fEmp, full_name: e.target.value })} /></label>
        <label>Phòng<select value={fEmp.department} onChange={(e) => setFEmp({ ...fEmp, department: e.target.value })}>{Object.entries(meta.departments).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Chức danh<select value={fEmp.position} onChange={(e) => setFEmp({ ...fEmp, position: e.target.value })}>{Object.entries(meta.positions).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Văn phòng<select value={fEmp.office} onChange={(e) => setFEmp({ ...fEmp, office: e.target.value })}>{Object.entries(meta.offices).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Hợp đồng<select value={fEmp.contract_type} onChange={(e) => setFEmp({ ...fEmp, contract_type: e.target.value })}><option value="hdld">HĐLĐ</option><option value="ctv">Cộng tác viên</option><option value="doi_tac">Đối tác</option></select></label>
        <label>Lương công việc (đ)<input type="number" value={fEmp.base_salary} onChange={(e) => setFEmp({ ...fEmp, base_salary: e.target.value })} /></label>
      </div><button className="act" disabled={!fEmp.full_name} onClick={() => post("/employees", { ...fEmp, base_salary: Number(fEmp.base_salary) || 0 }).then((r) => r && setFEmp({ ...fEmp, full_name: "", base_salary: "" }))}>Tạo hồ sơ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Mã NV</th><th>Họ tên</th><th>Phòng</th><th>Nhóm</th><th>Chức vụ</th><th>VP</th><th>HĐ</th><th style={{ textAlign: "right" }}>Lương CV</th><th>Thẻ HDV</th><th>Trạng thái</th></tr></thead>
        <tbody>{emps.map((e) => <tr key={e.id} style={{ opacity: e.active ? 1 : 0.55 }}><td className="mono">{e.code}</td><td><b>{e.full_name}</b></td><td>{e.department_name}</td><td>{e.sales_group}</td><td>{e.title || e.position_name}</td><td>{e.office_name}</td><td>{e.contract_type === "hdld" ? "HĐLĐ" : e.contract_type === "ctv" ? "CTV" : "Đối tác"}</td><td style={{ textAlign: "right" }}>{e.base_salary ? vnd(e.base_salary) : ""}</td>
          <td>{e.department === "huong_dan" && <>{e.card_no} <span className="muted">hạn {fmtD(e.card_expiry)}</span> {e.guide_ok ? <Tag cls="ok">Đủ điều kiện</Tag> : <Tag cls="red">Cổng 13</Tag>}</>}</td><td>{e.probation && <Tag cls="warn">Thử việc 85%</Tag>}{e.active ? "" : <Tag cls="red">Nghỉ</Tag>}</td></tr>)}</tbody></table></div>
    </>}

    {tab === "visa" && <>
      {canDH && <div className="panel"><h2>Hồ sơ visa mới</h2><div className="grid">
        <label>Khách<input value={fVisa.customer_name} onChange={(e) => setFVisa({ ...fVisa, customer_name: e.target.value })} /></label>
        <label>Thị trường<input value={fVisa.market} onChange={(e) => setFVisa({ ...fVisa, market: e.target.value })} placeholder="Schengen, Anh, Úc…" /></label>
        <label>Cách xử lý<select value={fVisa.method} onChange={(e) => setFVisa({ ...fVisa, method: e.target.value })}><option value="tu_xu_ly">Tự xử lý (200.000)</option><option value="gui_doi_tac">Gửi đối tác (50.000)</option></select></label>
        <label>Người xử lý<select value={fVisa.handler_id} onChange={(e) => setFVisa({ ...fVisa, handler_id: e.target.value })}><option value="">–</option>{emps.filter((e) => e.department === "visa").map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}</select></label>
        <label>Địa bàn<select value={fVisa.office} onChange={(e) => setFVisa({ ...fVisa, office: e.target.value })}><option value="hcm">HCM (chia đều)</option><option value="hanoi">Hà Nội (riêng)</option></select></label>
        <label>Doanh thu visa (đ)<input type="number" value={fVisa.revenue} onChange={(e) => setFVisa({ ...fVisa, revenue: e.target.value })} /></label>
        <label><input type="checkbox" checked={fVisa.alliance} onChange={(e) => setFVisa({ ...fVisa, alliance: e.target.checked })} /> Khách liên minh (+300.000)</label>
      </div><button className="act" disabled={!fVisa.customer_name || !fVisa.handler_id} onClick={() => post("/visa", { ...fVisa, handler_id: Number(fVisa.handler_id), revenue: Number(fVisa.revenue) || 0 }).then((r) => r && setFVisa({ ...fVisa, customer_name: "", market: "", revenue: "" }))}>Tạo hồ sơ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Khách</th><th>Thị trường</th><th>Cách</th><th>Người xử lý</th><th>Địa bàn</th><th style={{ textAlign: "right" }}>DT visa</th><th>Trạng thái</th><th>Hoàn thành</th>{canDH && <th></th>}</tr></thead>
        <tbody>{visa.map((f) => <tr key={f.id}><td className="mono">{f.code}</td><td>{f.customer_name}{f.alliance && <Tag cls="navy">liên minh</Tag>}</td><td>{f.market}</td><td>{f.method === "tu_xu_ly" ? "Tự xử lý" : "Gửi đối tác"}</td><td>{f.handler}</td><td>{f.office === "hanoi" ? "Hà Nội" : "HCM"}</td><td style={{ textAlign: "right" }}>{vnd(f.revenue)}</td>
          <td>{f.status === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : <Tag cls="warn">Đang làm</Tag>}</td><td>{fmtD(f.completed_at)}</td>{canDH && <td>{f.status !== "hoan_thanh" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/visa/${f.id}/complete`)}>Hoàn thành</button>}</td>}</tr>)}</tbody></table></div>
    </>}

    {tab === "guides" && <>
      {canDH && <div className="panel"><h2>Văn bản phân công HDV (cổng 13 – kiểm tra thẻ, hội viên, hợp đồng CTV)</h2><div className="grid">
        <label>Tour<select value={fAsg.tour_id} onChange={(e) => setFAsg({ ...fAsg, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>HDV<select value={fAsg.guide_id} onChange={(e) => setFAsg({ ...fAsg, guide_id: e.target.value })}><option value="">–</option>{guides.map((g) => <option key={g.id} value={g.id}>{g.full_name} {g.guide_ok ? "" : "(không đủ điều kiện)"}</option>)}</select></label>
        <label>Tuyến (bảng giá HDV)<select value={fAsg.rate_id} onChange={(e) => { const r = grates.find((x) => String(x.id) === e.target.value); setFAsg({ ...fAsg, rate_id: e.target.value, rate_per_day: r ? String(r.rate_per_day) : fAsg.rate_per_day, days: r ? String(Math.round(r.days)) : fAsg.days }); }}><option value="">– ngoài bảng giá (nhập tay) –</option>{grates.filter((r) => r.status === "active").map((r) => <option key={r.id} value={r.id}>{r.route} · {vnd(r.rate_per_day)}/ngày · {r.days} ngày</option>)}</select></label>
        <label>Số ngày<input type="number" value={fAsg.days} onChange={(e) => setFAsg({ ...fAsg, days: e.target.value })} /></label>
        <label>Đơn giá/ngày<input type="number" value={fAsg.rate_per_day} disabled={!!fAsg.rate_id} onChange={(e) => setFAsg({ ...fAsg, rate_per_day: e.target.value })} /></label>
        <label><input type="checkbox" checked={fAsg.holiday} onChange={(e) => setFAsg({ ...fAsg, holiday: e.target.checked })} /> Lễ Tết ×2</label>
      </div><button className="act" disabled={!fAsg.tour_id || !fAsg.guide_id || (!fAsg.rate_id && !fAsg.rate_per_day)} onClick={() => post("/guide-assignments", { tour_id: Number(fAsg.tour_id), guide_id: Number(fAsg.guide_id), days: Number(fAsg.days) || 0, rate_per_day: Number(fAsg.rate_per_day) || 0, rate_id: fAsg.rate_id ? Number(fAsg.rate_id) : null, holiday: fAsg.holiday })}>Phân công</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tour</th><th>HDV</th><th>Ngày × đơn giá</th><th style={{ textAlign: "right" }}>Thù lao</th><th>Trạng thái</th><th>Báo cáo tour</th><th>Hoàn ứng</th><th>Phân công</th>{canDH && <th></th>}</tr></thead>
        <tbody>{asg.map((a) => <tr key={a.id}><td><b>{a.tour_code}</b><div className="muted">{a.tour_name}</div></td><td>{a.guide}</td><td>{a.days} × {vnd(a.rate_per_day)}{a.holiday && " ×2"}</td><td style={{ textAlign: "right" }}>{vnd(a.amount)}</td>
          <td>{a.status === "da_xac_nhan" ? <Tag cls="ok">HDV đã xác nhận</Tag> : a.status === "huy" ? <Tag cls="red">Hủy</Tag> : <Tag cls="warn">Chờ xác nhận 24h</Tag>}</td><td>{a.report_submitted ? "✔" : <Tag cls="warn">thiếu → treo</Tag>}</td><td>{a.advance_settled ? "✔" : <Tag cls="warn">chưa → treo</Tag>}</td><td className="muted">{a.assigned_by} {fmtDT(a.assigned_at)}</td>
          {canDH && <td>{a.status === "cho_xac_nhan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/guide-assignments/${a.id}/update`, { confirm: true })}>HDV xác nhận</button>}{!a.report_submitted && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={() => post(`/guide-assignments/${a.id}/update`, { report_submitted: true })}>Đã nộp báo cáo</button>}</td>}</tr>)}</tbody></table></div>
      <h2>Bảng giá thù lao HDV theo tuyến (đồng/ngày, lễ Tết ×2) – Chủ tịch + TGĐ ký, hiệu lực theo ngày</h2>
      {["hcns", "cntt", "tp_dh"].includes(role) && <div className="panel"><div className="grid">
        <label>Tuyến<input value={fGrate.route} onChange={(e) => setFGrate({ ...fGrate, route: e.target.value })} /></label>
        <label>Số ngày<input type="number" step="0.5" value={fGrate.days} onChange={(e) => setFGrate({ ...fGrate, days: e.target.value })} /></label>
        <label>Đơn giá mới/ngày<input type="number" value={fGrate.rate_per_day} onChange={(e) => setFGrate({ ...fGrate, rate_per_day: e.target.value })} /></label>
        <label>Đơn giá cũ (đối chiếu)<input type="number" value={fGrate.old_rate_per_day} onChange={(e) => setFGrate({ ...fGrate, old_rate_per_day: e.target.value })} /></label>
        <label>Hiệu lực từ<input type="date" value={fGrate.effective_from} onChange={(e) => setFGrate({ ...fGrate, effective_from: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fGrate.route || !fGrate.rate_per_day} onClick={() => post("/guide-rates", { ...fGrate, days: Number(fGrate.days) || 0, rate_per_day: Number(fGrate.rate_per_day), old_rate_per_day: Number(fGrate.old_rate_per_day) || 0 }).then((r) => r && setFGrate({ ...fGrate, route: "", days: "", rate_per_day: "", old_rate_per_day: "" }))}>Trình Chủ tịch + TGĐ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tuyến</th><th>Số ngày</th><th style={{ textAlign: "right" }}>Giá cũ</th><th style={{ textAlign: "right" }}>Giá mới/ngày</th><th style={{ textAlign: "right" }}>Chênh lệch</th><th>Hiệu lực</th><th>Trạng thái</th><th>Ghi chú</th>{["chutich", "tgd"].includes(role) && <th></th>}</tr></thead>
        <tbody>{grates.map((r) => <tr key={r.id} style={{ opacity: r.status === "rejected" ? 0.5 : 1 }}><td><b>{r.route}</b></td><td>{r.days}</td><td style={{ textAlign: "right" }}>{vnd(r.old_rate_per_day)}</td><td style={{ textAlign: "right" }}><b>{vnd(r.rate_per_day)}</b></td><td style={{ textAlign: "right" }}>{vnd(r.rate_per_day - r.old_rate_per_day)}</td><td>{fmtD(r.effective_from)}</td>
          <td>{r.status === "active" ? <Tag cls="ok">Hiệu lực</Tag> : r.status === "pending" ? <Tag cls="warn">{r.signed_chutich ? "CT ✔ " : ""}{r.signed_tgd ? "TGĐ ✔ " : ""}chờ ký</Tag> : <Tag>Hết hiệu lực</Tag>}</td><td className="muted">{r.note}</td>
          {["chutich", "tgd"].includes(role) && <td>{r.status === "pending" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/guide-rates/${r.id}/sign`)}>Ký</button>}</td>}</tr>)}</tbody></table></div>
    </>}

    {tab === "fleet" && <>
      {fleet && <div className="kpis"><div className="kpi"><b>{vnd(fleet.total_revenue)}</b><span>Doanh thu nội bộ Đội xe {period}</span></div>{fleet.rows.map((r: any) => <div className="kpi" key={r.vehicle}><b>{r.days} ngày</b><span>{r.vehicle} · {r.driver} · {r.trips} chuyến · CTP {vnd(r.driver_allowance)}</span></div>)}</div>}
      {["nv_dh", "tp_dh", "cntt"].includes(role) && <div className="panel"><h2>Lệnh điều xe (Đội xe xác nhận trong 4 giờ)</h2><div className="grid">
        <label>Tour<select value={fDisp.tour_id} onChange={(e) => setFDisp({ ...fDisp, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>Xe<select value={fDisp.vehicle_id} onChange={(e) => setFDisp({ ...fDisp, vehicle_id: e.target.value })}><option value="">–</option>{veh.map((v) => <option key={v.id} value={v.id}>{v.plate} · {v.kind === "hop_tac" ? "xe hợp tác" : v.driver}</option>)}</select></label>
        <label>Tuyến (bảng giá xe)<select value={fDisp.rate_id} onChange={(e) => setFDisp({ ...fDisp, rate_id: e.target.value })}><option value="">– theo ngày –</option>{rates.filter((r) => r.status === "active").map((r) => <option key={r.id} value={r.id}>{r.route}{r.days ? ` ${r.days}N` : ""} · {vnd(r.internal_price)} / HT {r.partner_price ? vnd(r.partner_price) : "–"}</option>)}</select></label>
        <label>Từ ngày<input type="date" value={fDisp.date_from} onChange={(e) => setFDisp({ ...fDisp, date_from: e.target.value })} /></label>
        <label>Đến ngày<input type="date" value={fDisp.date_to} onChange={(e) => setFDisp({ ...fDisp, date_to: e.target.value })} /></label>
      </div><button className="act" disabled={!fDisp.tour_id || !fDisp.vehicle_id || !fDisp.date_from || !fDisp.date_to} onClick={() => post("/dispatch", { tour_id: Number(fDisp.tour_id), vehicle_id: Number(fDisp.vehicle_id), date_from: fDisp.date_from, date_to: fDisp.date_to, rate_id: fDisp.rate_id ? Number(fDisp.rate_id) : null })}>Lập lệnh</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Tuyến</th><th>Thời gian</th><th style={{ textAlign: "right" }}>Giá nội bộ</th><th>Trạng thái</th><th>Sự cố</th>{["cntt", "tp_dh", "nv_dh", "hcns"].includes(role) && <th></th>}</tr></thead>
        <tbody>{disp.map((d) => <tr key={d.id}><td><b>{d.tour_code}</b></td><td>{d.vehicle}</td><td>{d.driver}</td><td className="muted">{d.route}</td><td>{fmtD(d.date_from)} → {fmtD(d.date_to)} ({d.days} ngày)</td><td style={{ textAlign: "right" }}>{vnd(d.internal_price)}</td>
          <td>{d.status === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : d.status === "da_xac_nhan" ? <Tag cls="navy">Đã xác nhận</Tag> : d.status === "huy" ? <Tag cls="red">Hủy</Tag> : <Tag cls="warn">Chờ xác nhận 4h</Tag>}</td><td className="muted">{d.incident_note}</td>
          {["cntt", "tp_dh", "nv_dh", "hcns"].includes(role) && <td>{d.status === "cho_xac_nhan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/dispatch/${d.id}/update`, { status: "da_xac_nhan" })}>Xác nhận</button>}{d.status === "da_xac_nhan" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/dispatch/${d.id}/update`, { status: "hoan_thanh" })}>Hoàn thành</button>}</td>}</tr>)}</tbody></table></div>
      <h2>Bảng giá xe nội bộ theo tuyến (Chủ tịch + TGĐ duyệt, hiệu lực theo ngày)</h2>
      {["cntt", "hcns", "tp_dh"].includes(role) && <div className="panel"><div className="grid">
        <label>Tuyến<input value={fRate.route} onChange={(e) => setFRate({ ...fRate, route: e.target.value })} /></label>
        <label>Số ngày<input type="number" value={fRate.days} onChange={(e) => setFRate({ ...fRate, days: e.target.value })} /></label>
        <label>Giá xe Vietrip – VTD<input type="number" value={fRate.internal_price} onChange={(e) => setFRate({ ...fRate, internal_price: e.target.value })} /></label>
        <label>Giá xe hợp tác<input type="number" value={fRate.partner_price} onChange={(e) => setFRate({ ...fRate, partner_price: e.target.value })} /></label>
        <label>Hiệu lực từ<input type="date" value={fRate.effective_from} onChange={(e) => setFRate({ ...fRate, effective_from: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fRate.route || !fRate.internal_price} onClick={() => post("/vehicle-rates", { ...fRate, days: Number(fRate.days) || 0, internal_price: Number(fRate.internal_price), partner_price: Number(fRate.partner_price) || 0 }).then((r) => r && setFRate({ ...fRate, route: "", days: "", internal_price: "", partner_price: "" }))}>Trình Chủ tịch + TGĐ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Tuyến</th><th>Ngày</th><th style={{ textAlign: "right" }}>Xe Vietrip – VTD</th><th style={{ textAlign: "right" }}>Xe hợp tác</th><th>Hiệu lực</th><th>Trạng thái</th><th>Chữ ký</th>{["chutich", "tgd"].includes(role) && <th></th>}</tr></thead>
        <tbody>{rates.map((r) => <tr key={r.id} style={{ opacity: r.status === "rejected" ? 0.5 : 1 }}><td><b>{r.route}</b></td><td>{r.days || "–"}</td><td style={{ textAlign: "right" }}>{vnd(r.internal_price)}</td><td style={{ textAlign: "right" }}>{r.partner_price ? vnd(r.partner_price) : "–"}</td><td>{fmtD(r.effective_from)}</td>
          <td><Tag cls={r.status === "active" ? "ok" : r.status === "pending" ? "warn" : ""}>{r.status === "active" ? "Hiệu lực" : r.status === "pending" ? "Chờ ký" : "Hết hiệu lực"}</Tag></td><td>CT {r.signed_chutich ? "✔" : "…"} · TGĐ {r.signed_tgd ? "✔" : "…"}</td>
          {["chutich", "tgd"].includes(role) && <td>{r.status === "pending" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/vehicle-rates/${r.id}/sign`)}>Ký</button>}</td>}</tr>)}</tbody></table></div>
      <p className="muted">Bảng giá 6/5/2026 (anh Tuấn cung cấp 05/9/2026); cột xe hợp tác áp dụng từ 5/8/2026 cho 50E-955.31, 50H-496.23. Đội xe Vietrip hạch toán riêng như trung tâm lợi nhuận; lệnh điều xe lấy giá theo tuyến và loại xe; tuyến không có trong bảng → giá theo ngày ở hồ sơ xe. Quyết toán tháng do CNTT/AI.</p>
    </>}

    {tab === "incidents" && <>
      {incMeta && <div className="panel"><h2>Bảng phân mức sự vụ (áp dụng từ 05/9/2026 – Chủ tịch + TGĐ ban hành)</h2>
        <table><thead><tr><th>Mức</th><th>Hành vi điển hình</th><th>Chế tài</th><th>Thẩm quyền duyệt</th></tr></thead><tbody>
          {Object.entries(incMeta.levels).map(([k, v]: any) => <tr key={k}><td><Tag cls={k === "3" ? "red" : k === "2" ? "warn" : ""}>{v.ten}</Tag></td><td>{v.mo_ta}</td><td>{v.che_tai}</td><td className="muted">{v.duyet.length ? v.duyet.join(", ") : "không cần duyệt"}</td></tr>)}</tbody></table>
        <p className="muted">{incMeta.quy_trinh}. Người bị lập biên bản được ghi ý kiến; khiếu nại trong 3 ngày làm việc → chế tài treo tới khi cấp trên một bậc kết luận.</p></div>}
      {["hcns", "tp_dh", "gd_kd", "ptgd_doan", "tgd", "cntt", "tp"].includes(role) && <div className="panel"><h2>Lập biên bản sự vụ</h2><div className="grid">
        <label>Nhân sự<select value={fInc.employee_id} onChange={(e) => setFInc({ ...fInc, employee_id: e.target.value })}><option value="">–</option>{emps.map((e) => <option key={e.id} value={e.id}>{e.code} · {e.full_name}</option>)}</select></label>
        <label>Mức<select value={fInc.level} onChange={(e) => setFInc({ ...fInc, level: e.target.value })}>{[1, 2, 3].map((l) => <option key={l} value={l}>Mức {l}{l === 2 ? " (−1 triệu hoa hồng)" : l === 3 ? " (mất hoa hồng booking, kỷ luật)" : " (nhắc nhở)"}</option>)}</select></label>
        <label>Tour liên quan<select value={fInc.tour_id || ""} onChange={(e) => setFInc({ ...fInc, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code}</option>)}</select></label>
        <label>Ngày<input type="date" value={fInc.occurred_on} onChange={(e) => setFInc({ ...fInc, occurred_on: e.target.value })} /></label>
        <label>Mô tả<input value={fInc.description} onChange={(e) => setFInc({ ...fInc, description: e.target.value })} /></label>
      </div><button className="act orange" disabled={!fInc.employee_id || !fInc.description} onClick={() => post("/incidents", { employee_id: Number(fInc.employee_id), level: Number(fInc.level), description: fInc.description, occurred_on: fInc.occurred_on, tour_id: fInc.tour_id ? Number(fInc.tour_id) : null }).then((r) => r && setFInc({ ...fInc, description: "" }))}>Lập biên bản</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Nhân sự</th><th>Mức</th><th>Mô tả</th><th>Lập / HCNS / duyệt</th><th>Trạng thái</th><th>Ý kiến – khiếu nại</th><th></th></tr></thead>
        <tbody>{inc.length ? inc.map((i) => <tr key={i.id}><td>{fmtD(i.occurred_on)}</td><td>{i.employee}</td><td><Tag cls={i.level >= 3 ? "red" : i.level === 2 ? "warn" : ""}>Mức {i.level}</Tag></td><td>{i.description}</td>
          <td className="muted">{i.created_by}{i.confirmed_by && ` / ${i.confirmed_by}`}{i.approved_by && ` / ${i.approved_by}`}</td>
          <td>{i.status === "hieu_luc" ? <Tag cls="ok">{i.status_name}</Tag> : i.status === "huy" ? <Tag>{i.status_name}</Tag> : i.status === "khieu_nai" ? <Tag cls="red">{i.status_name}</Tag> : <Tag cls="warn">{i.status_name}{i.status === "cho_khieu_nai" && i.appeal_deadline ? ` (đến ${fmtD(i.appeal_deadline)})` : ""}</Tag>}</td>
          <td className="muted">{i.employee_opinion && <div>Ý kiến: {i.employee_opinion}</div>}{i.appeal_note && <div>Khiếu nại: {i.appeal_note}</div>}{i.appeal_result && <div>Kết luận: {i.appeal_result}</div>}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            {role === "hcns" && i.status === "lap" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/incidents/${i.id}/confirm`)}>HCNS xác nhận</button>}
            {["gd_kd", "ptgd_doan", "tgd", "chutich"].includes(role) && i.status === "hcns_xac_nhan" && <button className="act" style={{ margin: 0 }} onClick={() => post(`/incidents/${i.id}/approve`)}>Duyệt</button>}
            {["gd_kd", "ptgd_doan", "tgd", "chutich"].includes(role) && ["khieu_nai", "cho_khieu_nai"].includes(i.status) && <><button className="act grey" style={{ margin: "0 4px 0 0" }} onClick={() => { const n = prompt("Kết luận (giữ nguyên chế tài):"); if (n !== null) post(`/incidents/${i.id}/resolve`, { accept: false, result: n }); }}>Giữ nguyên</button>{i.status === "khieu_nai" && <button className="act grey" style={{ margin: 0 }} onClick={() => { const n = prompt("Kết luận (chấp nhận khiếu nại, hủy chế tài):"); if (n !== null) post(`/incidents/${i.id}/resolve`, { accept: true, result: n }); }}>Chấp nhận KN</button>}</>}
            {i.is_mine && ["lap", "hcns_xac_nhan", "cho_khieu_nai"].includes(i.status) && <button className="act orange" style={{ margin: "0 0 0 4px" }} onClick={() => { const o = prompt("Ý kiến của anh/chị về biên bản:") || ""; const a = prompt("Khiếu nại (để trống nếu không):") || ""; if (o || a) post(`/incidents/${i.id}/opinion`, { opinion: o, appeal: a }); }}>Ghi ý kiến / khiếu nại</button>}
          </td></tr>) : <tr><td colSpan={8} className="muted">Chưa có sự vụ.</td></tr>}</tbody></table></div>
      {["hcns", "cntt"].includes(role) && <button className="act grey" onClick={() => post("/incidents/finalize-expired")}>Chốt hiệu lực sự vụ hết hạn khiếu nại</button>}
    </>}
  </>);
}
export default function Page() { return <Shell><HR /></Shell>; }
