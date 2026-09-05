"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const KIN: Record<string, string> = { thu_booking: "Thu booking (D-7)", thu_hoi_dau_tu: "Thu hồi đầu tư/hợp tác", nhan_vay: "Nhận giải ngân vay" };
const KOUT: Record<string, string> = { chi_ncc: "Đề nghị chi NCC", chi_tour_du_toan: "Chi tour theo dự toán", tra_goc_vay: "Trả gốc vay", lai_vay: "Lãi vay", giai_ngan_dau_tu: "Giải ngân đầu tư", luong: "Lương", thue: "Thuế", thue_van_phong: "Thuê văn phòng", khac: "Khác" };
const SK: Record<string, string> = { tra_goc: "Trả gốc", tra_lai: "Trả lãi", thu_hoi: "Thu hồi", giai_ngan: "Giải ngân", nhan_vay: "Nhận vay" };
const today = () => new Date().toISOString().slice(0, 10);

function Finance() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const isKT = role === "ketoan";
  const [tab, setTab] = useState("forecast");
  const [fc, setFc] = useState<any>(null);
  const [wk, setWk] = useState<any>(null);
  const [cs, setCs] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>({ kinds: {} });
  const [plan, setPlan] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [f, setF] = useState<any>({ kind: "vay", entity: "Công ty mẹ", partner: "", contract_no: "", principal: "", interest_rate: "", maturity: "", collateral: "", purpose: "", owner: "", approval_ref: "", related_party: false, months: "", first_due: "" });
  const [fp, setFp] = useState<any>({ due_date: today(), direction: "out", category: "luong", description: "", amount: "", recurring_monthly: true });
  const load = useCallback(() => {
    if (!Object.keys(meta.kinds).length) api("/fin/meta").then(setMeta);
    if (tab === "forecast") { api("/fin/forecast").then(setFc).catch((e) => toast(errMsg(e), true)); api("/fin/plan").then(setPlan); }
    if (tab === "contracts") api("/fin/contracts").then(setCs);
    if (tab === "weekly") api("/fin/weekly").then(setWk);
  }, [tab]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any, method = "POST") => { try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const keysIn = fc ? Array.from(new Set(fc.weeks.flatMap((w: any) => Object.keys(w.in)))) as string[] : [];
  const keysOut = fc ? Array.from(new Set(fc.weeks.flatMap((w: any) => Object.keys(w.out)))) as string[] : [];

  return (<>
    <h1>Ngân quỹ – Tài chính: dự báo 13 tuần, vay, đầu tư &amp; hợp tác (mục 3.9)</h1>
    <p className="muted">Dự báo dòng tiền lấy tự động từ: booking còn phải thu (dự kiến thu trước khởi hành 7 ngày), đề nghị chi & dự toán tour sắp chạy, lịch trả gốc/lãi từng khế ước, lịch thu hồi hợp tác/ký quỹ/cọc/cho vay, bảng lương gần nhất và các khoản Kế toán nhập (thuế, thuê văn phòng…). Cảnh báo khi số dư dự kiến âm hoặc dưới ngưỡng tối thiểu.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["forecast", "Dự báo 13 tuần"], ["contracts", "Hợp đồng vay & đầu tư"], ["weekly", "Báo cáo tài chính tuần"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "forecast" && fc && <>
      <div className="kpis"><div className="kpi"><b>{vnd(fc.opening)}</b><span>Tiền hiện có (111+112)</span></div><div className="kpi"><b style={{ color: fc.closing < 0 ? "var(--red)" : undefined }}>{vnd(fc.closing)}</b><span>Số dư dự kiến cuối tuần 13</span></div><div className="kpi"><b>{vnd(fc.min_cash)}</b><span>Ngưỡng tối thiểu (tham số)</span></div><div className="kpi"><b style={{ color: fc.alerts.length ? "var(--red)" : undefined }}>{fc.alerts.length}</b><span>Tuần cảnh báo</span></div></div>
      {fc.alerts.length > 0 && <div className="panel" style={{ borderColor: "var(--red)" }}>{fc.alerts.map((a: string, i: number) => <div key={i}><Tag cls="red">!</Tag> {a}</div>)}</div>}
      <div className="panel wrap"><table><thead><tr><th>Khoản</th>{fc.weeks.map((w: any) => <th key={w.week} style={{ textAlign: "right", whiteSpace: "nowrap" }}>T{w.week}<div className="muted">{fmtD(w.from).slice(0, 5)}</div></th>)}</tr></thead>
        <tbody>
          {keysIn.map((k) => <tr key={k}><td style={{ color: "var(--teal)" }}>+ {KIN[k] || k}</td>{fc.weeks.map((w: any) => <td key={w.week} style={{ textAlign: "right" }}>{w.in[k] ? vnd(w.in[k]) : ""}</td>)}</tr>)}
          {keysOut.map((k) => <tr key={k}><td style={{ color: "var(--red)" }}>− {KOUT[k] || k}</td>{fc.weeks.map((w: any) => <td key={w.week} style={{ textAlign: "right" }}>{w.out[k] ? vnd(w.out[k]) : ""}</td>)}</tr>)}
          <tr><td><b>Thuần trong tuần</b></td>{fc.weeks.map((w: any) => <td key={w.week} style={{ textAlign: "right" }}><b>{vnd(w.net)}</b></td>)}</tr>
          <tr><td><b>Số dư cuối tuần</b></td>{fc.weeks.map((w: any) => <td key={w.week} style={{ textAlign: "right", color: w.closing < 0 ? "var(--red)" : w.closing < fc.min_cash ? "var(--orange)" : undefined }}><b>{vnd(w.closing)}</b></td>)}</tr>
        </tbody></table></div>
      {isKT && <div className="panel"><h2>Khoản thu/chi kế hoạch khác (Kế toán nhập)</h2><div className="grid">
        <label>Ngày<input type="date" value={fp.due_date} onChange={(e) => setFp({ ...fp, due_date: e.target.value })} /></label>
        <label>Chiều<select value={fp.direction} onChange={(e) => setFp({ ...fp, direction: e.target.value })}><option value="out">Chi</option><option value="in">Thu</option></select></label>
        <label>Loại<select value={fp.category} onChange={(e) => setFp({ ...fp, category: e.target.value })}>{["luong", "thue", "thue_van_phong", "khac"].map((c) => <option key={c} value={c}>{KOUT[c]}</option>)}</select></label>
        <label>Diễn giải<input value={fp.description} onChange={(e) => setFp({ ...fp, description: e.target.value })} /></label>
        <label>Số tiền<input type="number" value={fp.amount} onChange={(e) => setFp({ ...fp, amount: e.target.value })} /></label>
        <label><input type="checkbox" checked={fp.recurring_monthly} onChange={(e) => setFp({ ...fp, recurring_monthly: e.target.checked })} /> Lặp hằng tháng</label>
      </div><button className="act" disabled={!fp.description || !fp.amount} onClick={() => post("/fin/plan", { ...fp, amount: Number(fp.amount) }).then((r) => r && setFp({ ...fp, description: "", amount: "" }))}>Thêm</button>
        <table><tbody>{plan.map((p) => <tr key={p.id}><td>{fmtD(p.due_date)}</td><td>{p.direction === "in" ? "Thu" : "Chi"}</td><td>{KOUT[p.category] || p.category}</td><td>{p.description}</td><td style={{ textAlign: "right" }}>{vnd(p.amount)}</td><td>{p.recurring_monthly && <Tag>hằng tháng</Tag>}</td><td><button className="act grey" style={{ margin: 0 }} onClick={() => post(`/fin/plan/${p.id}`, undefined, "DELETE")}>×</button></td></tr>)}</tbody></table></div>}
    </>}

    {tab === "contracts" && <>
      {isKT && <div className="panel"><h2>Hồ sơ hợp đồng tài chính mới</h2><div className="grid">
        <label>Loại<select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{Object.entries(meta.kinds).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Pháp nhân<select value={f.entity} onChange={(e) => setF({ ...f, entity: e.target.value })}><option>Công ty mẹ</option><option>Công ty TNHH Vận tải Vietrip</option></select></label>
        <label>Đối tác / ngân hàng<input value={f.partner} onChange={(e) => setF({ ...f, partner: e.target.value })} /></label>
        <label>Số hợp đồng / khế ước<input value={f.contract_no} onChange={(e) => setF({ ...f, contract_no: e.target.value })} /></label>
        <label>Giá trị (đ)<input type="number" value={f.principal} onChange={(e) => setF({ ...f, principal: e.target.value })} /></label>
        <label>Lãi suất %/năm<input type="number" value={f.interest_rate} onChange={(e) => setF({ ...f, interest_rate: e.target.value })} /></label>
        <label>Đáo hạn / hạn thu hồi<input type="date" value={f.maturity} onChange={(e) => setF({ ...f, maturity: e.target.value })} /></label>
        <label>Tài sản đảm bảo<input value={f.collateral} onChange={(e) => setF({ ...f, collateral: e.target.value })} /></label>
        <label>Mục đích<input value={f.purpose} onChange={(e) => setF({ ...f, purpose: e.target.value })} /></label>
        <label>Người phụ trách<input value={f.owner} onChange={(e) => setF({ ...f, owner: e.target.value })} /></label>
        <label>Nghị quyết HĐQT (bắt buộc với đầu tư/hợp tác/cho vay/cọc)<input value={f.approval_ref} onChange={(e) => setF({ ...f, approval_ref: e.target.value })} /></label>
        {f.kind === "vay" && <><label>Số tháng trả góp<input type="number" value={f.months} onChange={(e) => setF({ ...f, months: e.target.value })} /></label><label>Kỳ trả đầu<input type="date" value={f.first_due} onChange={(e) => setF({ ...f, first_due: e.target.value })} /></label></>}
        <label><input type="checkbox" checked={f.related_party} onChange={(e) => setF({ ...f, related_party: e.target.checked })} /> Bên liên quan (sổ GDLK, NĐ 132)</label>
      </div><button className="act" disabled={!f.partner || !f.principal} onClick={() => post("/fin/contracts", { ...f, principal: Number(f.principal), interest_rate: Number(f.interest_rate) || 0, months: Number(f.months) || 0, maturity: f.maturity || null, first_due: f.first_due || null }).then((r) => r && setF({ ...f, partner: "", contract_no: "", principal: "", approval_ref: "" }))}>Lập hồ sơ</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Loại</th><th>Đối tác</th><th>Pháp nhân</th><th style={{ textAlign: "right" }}>Giá trị</th><th style={{ textAlign: "right" }}>Dư nợ / còn thu</th><th>Lãi</th><th>Đáo hạn</th><th>Phê duyệt</th><th>Trạng thái</th></tr></thead>
        <tbody>{cs.map((c) => <>
          <tr key={c.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === c.id ? null : c.id)}><td><b>{c.code}</b><div className="muted">{c.contract_no}</div></td><td>{c.kind_name}{c.related_party && <Tag cls="warn">GDLK</Tag>}</td><td>{c.partner}<div className="muted">{c.owner}</div></td><td className="muted">{c.entity}</td><td style={{ textAlign: "right" }}>{vnd(c.principal)}</td><td style={{ textAlign: "right" }}><b>{vnd(c.outstanding)}</b></td><td>{c.interest_rate ? c.interest_rate + "%" : ""}</td><td>{fmtD(c.maturity)}</td><td className="muted">{c.approval_ref}</td>
            <td><Tag cls={c.status === "qua_han" ? "red" : c.status === "tat_toan" ? "" : "ok"}>{c.status === "qua_han" ? "Quá hạn" : c.status === "tat_toan" ? "Tất toán" : "Hiệu lực"}</Tag></td></tr>
          {open === c.id && <tr key={c.id + "s"}><td colSpan={10}><div style={{ margin: "4px 0 8px 16px" }}><div className="muted">{c.purpose} · TSĐB: {c.collateral}</div>
            <table style={{ width: "auto" }}><thead><tr><th>Ngày</th><th>Loại</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Trạng thái</th><th>GD ngân hàng</th>{isKT && <th></th>}</tr></thead><tbody>
              {c.schedule.map((s: any) => <tr key={s.id}><td>{fmtD(s.due_date)}</td><td>{SK[s.kind]}</td><td style={{ textAlign: "right" }}>{vnd(s.amount)}</td><td><Tag cls={s.status === "da_thuc_hien" ? "ok" : s.status === "qua_han" ? "red" : "warn"}>{s.status === "da_thuc_hien" ? "Đã thực hiện" : s.status === "qua_han" ? "Quá hạn" : "Kế hoạch"}</Tag></td><td className="muted">{s.bank_ref}{s.done_on && ` · ${fmtD(s.done_on)}`}</td>
                {isKT && <td>{s.status !== "da_thuc_hien" && <button className="act teal" style={{ margin: 0 }} onClick={() => { const ref = prompt("Mã giao dịch ngân hàng:") || ""; post(`/fin/schedule/${s.id}/settle`, { done_on: today(), bank_ref: ref }); }}>Đã thực hiện</button>}</td>}</tr>)}</tbody></table>
            {isKT && <button className="act grey" onClick={() => { const d = prompt("Ngày (YYYY-MM-DD):", today()); const k = prompt("Loại: tra_goc / tra_lai / thu_hoi / giai_ngan / nhan_vay:", c.kind === "vay" ? "tra_goc" : "thu_hoi"); const a = prompt("Số tiền:"); if (d && k && a) post(`/fin/contracts/${c.id}/schedule`, { due_date: d, kind: k, amount: Number(a) }); }}>+ dòng lịch</button>}</div></td></tr>}
        </>)}</tbody></table></div>
      <p className="muted">Thực hiện lịch → bút toán tự động: trả gốc Nợ 341/Có 112; lãi Nợ 635/Có 112; nhận vay Nợ 112/Có 341; giải ngân đầu tư Nợ 222/138/244/128/331 – Có 112; thu hồi ngược lại. Khoản quá hạn thu hồi lên báo cáo HĐQT hằng tháng.</p>
    </>}

    {tab === "weekly" && wk && <>
      <div className="kpis"><div className="kpi"><b>{vnd(wk.cash)}</b><span>Số dư tiền</span></div><div className="kpi"><b>{vnd(wk.total_loans)}</b><span>Dư nợ vay</span></div><div className="kpi"><b>{vnd(wk.investments_total)}</b><span>Đầu tư, hợp tác, ký quỹ, cọc, cho vay</span></div><div className="kpi"><b>{vnd(wk.receivables_total)}</b><span>Phải thu khách (booking chưa thu đủ)</span></div><div className="kpi"><b>{vnd(wk.wip_154)}</b><span>154 tồn đọng</span></div><div className="kpi"><b>{vnd(wk.accrued_335)}</b><span>335 chưa hóa đơn</span></div></div>
      {wk.overdue.length > 0 && <div className="panel" style={{ borderColor: "var(--red)" }}><b>Quá hạn:</b> {wk.overdue.map((o: any, i: number) => <div key={i}><Tag cls="red">{SK[o.kind]}</Tag> {o.contract} {o.partner} · {fmtD(o.date)} · {vnd(o.amount)}</div>)}</div>}
      <h2>Hạn trả gốc / lãi / thu hồi 4 tuần tới</h2>
      <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Hợp đồng</th><th>Đối tác</th><th>Loại</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Trạng thái</th></tr></thead><tbody>{wk.due_4w.length ? wk.due_4w.map((d: any, i: number) => <tr key={i}><td>{fmtD(d.date)}</td><td>{d.contract}</td><td>{d.partner}</td><td>{SK[d.kind]}</td><td style={{ textAlign: "right" }}>{vnd(d.amount)}</td><td>{d.status === "qua_han" ? <Tag cls="red">Quá hạn</Tag> : <Tag cls="warn">Kế hoạch</Tag>}</td></tr>) : <tr><td colSpan={6} className="muted">Không có.</td></tr>}</tbody></table></div>
      <h2>10 khoản phải thu lớn nhất</h2>
      <div className="panel wrap"><table><thead><tr><th>Booking</th><th>Khách</th><th>Tour</th><th style={{ textAlign: "right" }}>Còn phải thu</th><th>Tuổi nợ (ngày sau tour)</th></tr></thead><tbody>{wk.receivables_top10.map((r: any) => <tr key={r.booking}><td>{r.booking}</td><td>{r.customer}</td><td>{r.tour}</td><td style={{ textAlign: "right" }}>{vnd(r.due)}</td><td>{r.age_days > 20 ? <Tag cls="red">{r.age_days}</Tag> : r.age_days}</td></tr>)}</tbody></table></div>
      <h2>Danh mục đầu tư – hợp tác (báo cáo HĐQT)</h2>
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Loại</th><th>Đối tác</th><th style={{ textAlign: "right" }}>Giá trị</th><th style={{ textAlign: "right" }}>Còn lại</th><th>Hạn thu hồi</th><th>NQ HĐQT</th><th>Phụ trách</th><th>Trạng thái</th></tr></thead><tbody>{wk.investments.map((c: any) => <tr key={c.code}><td>{c.code}</td><td>{c.kind}{c.related_party && <Tag cls="warn">GDLK</Tag>}</td><td>{c.partner}</td><td style={{ textAlign: "right" }}>{vnd(c.principal)}</td><td style={{ textAlign: "right" }}>{vnd(c.outstanding)}</td><td>{fmtD(c.maturity)}</td><td className="muted">{c.approval_ref}</td><td>{c.owner}</td><td><Tag cls={c.status === "qua_han" ? "red" : "ok"}>{c.status}</Tag></td></tr>)}</tbody></table></div>
      <p className="muted">Nội dung báo cáo tài chính hằng tuần cho Chủ tịch, TGĐ, KTT, BKS theo mục 6.6 Thiết kế v1.7 (số dư, vay, hạn 4 tuần, tuổi nợ, tiến độ thu hồi, 335/154 tồn đọng). Số dư đầu kỳ các khoản đầu tư nhập từ BCTC kiểm toán 2025 khi cắt chuyển.</p>
    </>}
  </>);
}
export default function Page() { return <Shell><Finance /></Shell>; }
