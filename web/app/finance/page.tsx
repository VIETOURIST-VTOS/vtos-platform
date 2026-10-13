"use client";
import DinhKem from "@/components/DinhKem";
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
  // mở đúng tab khi vào từ menu bên trái (?tab=...)
  useEffect(() => { const q = new URLSearchParams(window.location.search).get("tab"); if (q) setTab(q); }, []);
  const [fc, setFc] = useState<any>(null);
  const [wk, setWk] = useState<any>(null);
  const [cs, setCs] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>({ kinds: {} });
  const [plan, setPlan] = useState<any[]>([]);
  const [vx, setVx] = useState<any>(null);
  const [dc, setDc] = useState<any>(null);
  const [sk, setSk] = useState<any>({ ngan_hang: "TPBank", den_ngay: today(), text: "" });
  const [open, setOpen] = useState<number | null>(null);
  const [f, setF] = useState<any>({ kind: "vay", entity: "Công ty mẹ", partner: "", contract_no: "", principal: "", interest_rate: "", maturity: "", collateral: "", purpose: "", owner: "", approval_ref: "", related_party: false, months: "", first_due: "" });
  const [fp, setFp] = useState<any>({ due_date: today(), direction: "out", category: "luong", description: "", amount: "", recurring_monthly: true });
  const load = useCallback(() => {
    if (!Object.keys(meta.kinds).length) api("/fin/meta").then(setMeta);
    if (tab === "forecast") { api("/fin/forecast").then(setFc).catch((e) => toast(errMsg(e), true)); api("/fin/plan").then(setPlan); }
    if (tab === "contracts") api("/fin/contracts").then(setCs);
    if (tab === "weekly") api("/fin/weekly").then(setWk);
    if (tab === "vayxe") api("/fin/vay-xe").then(setVx).catch((e) => toast(errMsg(e), true));
  }, [tab]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any, method = "POST") => { try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const keysIn = fc ? Array.from(new Set(fc.weeks.flatMap((w: any) => Object.keys(w.in)))) as string[] : [];
  const keysOut = fc ? Array.from(new Set(fc.weeks.flatMap((w: any) => Object.keys(w.out)))) as string[] : [];

  return (<>
    <h1>Ngân quỹ – Tài chính: dự báo 13 tuần, vay, đầu tư &amp; hợp tác (mục 3.9)</h1>
    <p className="muted">Dự báo dòng tiền lấy tự động từ: booking còn phải thu (dự kiến thu trước khởi hành 7 ngày), đề nghị chi & dự toán tour sắp chạy, lịch trả gốc/lãi từng khế ước, lịch thu hồi hợp tác/ký quỹ/cọc/cho vay, bảng lương gần nhất và các khoản Kế toán nhập (thuế, thuê văn phòng…). Cảnh báo khi số dư dự kiến âm hoặc dưới ngưỡng tối thiểu.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["forecast", "Dự báo 13 tuần"], ["contracts", "Hợp đồng vay & đầu tư"], ["weekly", "Báo cáo tài chính tuần"], ["vayxe", "Vay & thế chấp xe"], ["doichieu", "Đối chiếu sao kê vay"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

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
            {isKT && <button className="act grey" onClick={() => { const d = prompt("Ngày (YYYY-MM-DD):", today()); const k = prompt("Loại: tra_goc / tra_lai / thu_hoi / giai_ngan / nhan_vay:", c.kind === "vay" ? "tra_goc" : "thu_hoi"); const a = prompt("Số tiền:"); if (d && k && a) post(`/fin/contracts/${c.id}/schedule`, { due_date: d, kind: k, amount: Number(a) }); }}>+ dòng lịch</button>}
            <DinhKem doiTuong="khe_uoc_vay" doiTuongId={c.code} loai="hop_dong"
              tieuDe={`Bản gốc khế ước ${c.contract_no || c.code} – ${c.partner}`}
              goi={"Bản scan khế ước / hợp đồng, phụ lục gia hạn, thông báo lãi suất, giấy nhận nợ từng lần " +
                   "giải ngân, biên bản đối chiếu dư nợ. Bộ nạp Excel chỉ mang được các con số; lúc đối " +
                   "chiếu với ngân hàng thì thứ phải mở ra là bản gốc."} />
            </div></td></tr>}
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

    {tab === "vayxe" && vx && <>
      <div className="kpis">
        <div className="kpi"><b>{vnd(vx.tong_du_no)}</b><span>Tổng dư nợ vay có tài sản là xe</span></div>
        <div className="kpi"><b>{vnd(vx.tong_lai_thang)}</b><span>Lãi phải trả mỗi tháng</span></div>
        <div className="kpi"><b style={{ color: vx.canh_bao.filter((c: any) => c.muc === "gap" || c.muc === "qua_han").length ? "var(--red)" : undefined }}>{vx.canh_bao.filter((c: any) => c.muc === "gap" || c.muc === "qua_han").length}</b><span>Việc gấp</span></div>
        <div className="kpi"><b style={{ color: vx.thieu_ho_so.length ? "var(--orange)" : undefined }}>{vx.thieu_ho_so.length}</b><span>Xe chưa rõ thuộc khế ước nào</span></div>
      </div>
      {vx.canh_bao.length > 0 && <div className="panel wrap"><h2>Việc phải xử lý</h2><table><thead><tr><th>Mức</th><th>Nội dung</th><th>Việc phải làm</th></tr></thead><tbody>
        {vx.canh_bao.map((c: any, i: number) => <tr key={i}>
          <td><Tag cls={c.muc === "gap" || c.muc === "qua_han" ? "red" : c.muc === "thieu_du_lieu" ? "warn" : "warn"}>{c.muc === "gap" ? "GẤP" : c.muc === "qua_han" ? "QUÁ HẠN" : c.muc === "thieu_du_lieu" ? "THIẾU DỮ LIỆU" : "SỚM"}</Tag></td>
          <td>{c.noi_dung}</td><td className="muted">{c.viec}
            {c.loai === "xe_da_ra_khoi_doi_van_the_chap" && c.collateral_id && isKT && <div style={{ marginTop: 6 }}>
              <button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => {
                const so = prompt(`Số văn bản giải chấp của ngân hàng cho xe ${c.xe}:`);
                if (so && so.trim()) post(`/fleet/the-chap/${c.collateral_id}/giai-chap`, { van_ban: so.trim() }).then(() => api("/fin/vay-xe").then(setVx));
              }}>Ghi giải chấp (có văn bản)</button>
              <button className="act grey" style={{ margin: "0 0 0 6px", fontSize: 12 }} onClick={() => {
                const ly = prompt(`Gỡ ${c.xe} khỏi theo dõi thế chấp — ĐÂY KHÔNG PHẢI GIẢI CHẤP. Lý do:`);
                if (ly && ly.trim()) post(`/fleet/the-chap/${c.collateral_id}/go-khoi-theo-doi`, { ly_do: ly.trim() }).then(() => api("/fin/vay-xe").then(setVx));
              }}>Gỡ khỏi theo dõi</button>
            </div>}
          </td></tr>)}
      </tbody></table></div>}
      <h2>Khế ước – số liệu không trùng, dùng bảng này để cộng tổng</h2>
      <div className="panel wrap"><table><thead><tr><th>Mã / Hợp đồng</th><th>Ngân hàng</th><th>Pháp nhân</th><th style={{ textAlign: "right" }}>Dư nợ</th><th style={{ textAlign: "right" }}>Lãi/năm</th><th style={{ textAlign: "right" }}>Lãi/tháng</th><th>Đáo hạn</th><th>Xe thế chấp</th></tr></thead><tbody>
        {vx.ke_uoc.map((k: any) => <tr key={k.id}>
          <td>{k.contract_no || k.code}<div className="muted">{k.code}</div></td><td>{k.partner}</td><td>{k.company || k.entity}</td>
          <td style={{ textAlign: "right" }}>{vnd(k.du_no)}</td><td style={{ textAlign: "right" }}>{k.lai_suat}%</td><td style={{ textAlign: "right" }}>{vnd(k.lai_thang)}</td>
          <td>{k.maturity ? <>{fmtD(k.maturity)}{k.con_ngay !== null && <div className={k.con_ngay <= 30 ? "" : "muted"} style={{ color: k.con_ngay <= 30 ? "var(--red)" : undefined }}>{k.con_ngay < 0 ? `quá ${-k.con_ngay} ngày` : `còn ${k.con_ngay} ngày`}</div>}</> : <Tag cls="warn">chưa có ngày</Tag>}</td>
          <td>{k.xe_the_chap.join(" · ") || <span className="muted">chưa gắn xe</span>}{k.xe_da_giai_chap.length > 0 && <div className="muted">đã giải chấp: {k.xe_da_giai_chap.join(" · ")}</div>}</td></tr>)}
        <tr><td colSpan={3}><b>TỔNG</b></td><td style={{ textAlign: "right" }}><b>{vnd(vx.tong_du_no)}</b></td><td></td><td style={{ textAlign: "right" }}><b>{vnd(vx.tong_lai_thang)}</b></td><td colSpan={2}></td></tr>
      </tbody></table></div>
      {vx.ke_uoc_xe_ngoai_doi && vx.ke_uoc_xe_ngoai_doi.length > 0 && <>
        <h2>Xe ngoài đội 45 chỗ — {vx.ke_uoc_xe_ngoai_doi.length} khế ước, dư nợ {vnd(vx.tong_du_no_xe_ngoai_doi)}, lãi {vnd(vx.tong_lai_thang_xe_ngoai_doi)}/tháng</h2>
        <p className="muted">Vay có tài sản là xe nhưng không thuộc 12 xe khách 45 chỗ. Để riêng nên KHÔNG cộng vào các con số ở đầu màn hình.</p>
        <div className="panel wrap"><table><thead><tr><th>Mã / Hợp đồng</th><th>Ngân hàng</th><th style={{ textAlign: "right" }}>Dư nợ</th><th style={{ textAlign: "right" }}>Lãi/tháng</th><th>Đáo hạn</th><th>Tài sản thế chấp</th></tr></thead><tbody>
          {vx.ke_uoc_xe_ngoai_doi.map((k: any) => <tr key={k.id}><td>{k.contract_no || k.code}</td><td>{k.partner}</td><td style={{ textAlign: "right" }}>{vnd(k.du_no)}</td><td style={{ textAlign: "right" }}>{vnd(k.lai_thang)}</td><td>{k.maturity ? fmtD(k.maturity) : <Tag cls="warn">chưa có ngày</Tag>}</td><td className="muted">{k.collateral}</td></tr>)}
        </tbody></table></div></>}
      <h2>Tách theo pháp nhân</h2>
      <div className="panel wrap"><table><thead><tr><th>Pháp nhân</th><th style={{ textAlign: "right" }}>Số khế ước</th><th style={{ textAlign: "right" }}>Dư nợ</th><th style={{ textAlign: "right" }}>Lãi/tháng</th></tr></thead><tbody>
        {Object.entries(vx.theo_phap_nhan).map(([ten, t]: any) => <tr key={ten}><td>{ten}</td><td style={{ textAlign: "right" }}>{t.so_khe_uoc}</td><td style={{ textAlign: "right" }}>{vnd(t.du_no)}</td><td style={{ textAlign: "right" }}>{vnd(t.lai_thang)}</td></tr>)}
      </tbody></table></div>
      <h2>Từng xe gắn với khế ước nào</h2>
      <div className="panel wrap"><table><thead><tr><th>Biển số</th><th>Pháp nhân</th><th>Vòng đời</th><th>Khế ước</th><th style={{ textAlign: "right" }}>Dư nợ phân bổ/xe (tham khảo)</th></tr></thead><tbody>
        {vx.xe.filter((x: any) => x.active || x.khe_uoc.length).map((x: any) => <tr key={x.id}>
          <td>{x.plate}</td><td>{x.phap_nhan || <span className="muted">—</span>}</td>
          <td>{x.lifecycle !== "dang_khai_thac" ? <Tag cls="warn">{x.lifecycle}</Tag> : <span className="muted">đang khai thác</span>}</td>
          <td>{x.khe_uoc.length ? x.khe_uoc.map((k: any) => <div key={k.collateral_id}>{k.contract_no || k.code} · {k.partner} <span className="muted">(gói {k.so_xe_trong_goi} xe)</span></div>) : <Tag cls="warn">chưa xác định</Tag>}</td>
          <td style={{ textAlign: "right" }}>{x.khe_uoc.length ? vnd(x.khe_uoc.reduce((s: number, k: any) => s + k.du_no_phan_bo, 0)) : ""}</td></tr>)}
      </tbody></table></div>
      <p className="muted">Cột &quot;dư nợ phân bổ/xe&quot; chỉ để tham khảo – chia đều dư nợ khế ước cho số xe trong gói. Đây KHÔNG phải nghĩa vụ riêng của từng xe: ngân hàng nắm cả gói, giải chấp một xe phải thoả thuận riêng với ngân hàng. Xe không xuất hiện trong tài sản bảo đảm của khế ước nào KHÔNG có nghĩa là đã được giải chấp – phải có văn bản của ngân hàng mới ghi nhận giải chấp.</p>
    </>}

    {tab === "doichieu" && <>
      <div className="panel"><h2>Dán sao kê khoản vay của ngân hàng</h2>
        <p className="muted">Mỗi dòng một khế ước, ngăn bằng dấu chấm phẩy hoặc tab: <b>mã khế ước ; dư nợ ; lãi suất %/năm ; ngày đáo hạn (yyyy-mm-dd) ; nhóm</b>. Chỉ ba cột đầu là bắt buộc. Cột <b>nhóm</b> ghi <code>von_luu_dong</code>, <code>bds</code> hoặc <code>khac</code> cho khoản vay không thuộc đội xe — những dòng đó sẽ được xếp là &quot;ngoài phạm vi&quot; thay vì báo là thiếu sót. Đối chiếu chỉ ĐỌC và so sánh — muốn ghi đè dư nợ phải bấm nút cập nhật riêng bên dưới.</p>
        <div className="grid">
          <label>Ngân hàng<input value={sk.ngan_hang} onChange={(e) => setSk({ ...sk, ngan_hang: e.target.value })} /></label>
          <label>Sao kê đến ngày<input type="date" value={sk.den_ngay} onChange={(e) => setSk({ ...sk, den_ngay: e.target.value })} /></label>
        </div>
        <textarea rows={8} style={{ width: "100%", fontFamily: "monospace" }} placeholder={"125/2025/GNN/Q4 ; 8711111104 ; 13.7 ; 2031-05-09\n125/2025/GNN/Q4/02 ; 2247887320 ; 13.5 ; 2031-05-09"} value={sk.text} onChange={(e) => setSk({ ...sk, text: e.target.value })} />
        <button className="act" disabled={!sk.text.trim()} onClick={() => {
          const dong = sk.text.split("\n").map((l: string) => l.split(/[;\t]/).map((x: string) => x.trim())).filter((c: string[]) => c[0])
            .map((c: string[]) => ({ ke_uoc: c[0], du_no: Number((c[1] || "0").replace(/[^0-9.]/g, "")) || 0, lai_suat: c[2] ? Number(c[2].replace(/[^0-9.]/g, "")) : null, dao_han: c[3] || null, nhom: c[4] || "", muc_dich: c[5] || "" }));
          post("/fin/doi-chieu-sao-ke", { ngan_hang: sk.ngan_hang, den_ngay: sk.den_ngay, dong }).then((r) => r && setDc({ ...r, _dong: dong }));
        }}>Đối chiếu</button>
      </div>
      {dc && <>
        <div className="kpis">
          <div className="kpi"><b>{dc.khop.length}</b><span>Khớp</span></div>
          <div className="kpi"><b style={{ color: dc.lech.length ? "var(--orange)" : undefined }}>{dc.lech.length}</b><span>Lệch số</span></div>
          <div className="kpi"><b style={{ color: dc.khong_thay_tren_sao_ke.length ? "var(--red)" : undefined }}>{dc.khong_thay_tren_sao_ke.length}</b><span>Hệ thống có, sao kê không</span></div>
          <div className="kpi"><b style={{ color: dc.chua_theo_doi.length ? "var(--orange)" : undefined }}>{dc.chua_theo_doi.length}</b><span>Ngân hàng có, hệ thống chưa theo dõi</span></div>
        </div>
        {dc.lech.length > 0 && <><h2>Lệch số — hồ sơ nội bộ trễ so với ngân hàng</h2>
          <div className="panel wrap"><table><thead><tr><th>Khế ước</th><th>Đối tác</th><th>Sai lệch</th></tr></thead><tbody>
            {dc.lech.map((l: any) => <tr key={l.ke_uoc}><td>{l.ke_uoc}</td><td>{l.partner}</td>
              <td>{l.sai_lech.map((s: any, i: number) => <div key={i}>{s.truong === "du_no" ? <>Dư nợ: hệ thống {vnd(s.he_thong)} → sao kê {vnd(s.sao_ke)} <b style={{ color: s.chenh < 0 ? "var(--teal)" : "var(--red)" }}>({s.chenh > 0 ? "+" : ""}{vnd(s.chenh)})</b></> : s.truong === "lai_suat" ? <>Lãi suất: {s.he_thong}% → <b>{s.sao_ke}%</b></> : <>Đáo hạn: {s.he_thong} → <b>{s.sao_ke}</b></>}</div>)}</td></tr>)}
          </tbody></table></div>
          {isKT && <button className="act" onClick={() => { if (confirm(`Ghi dư nợ, lãi suất và ngày đáo hạn theo sao kê ${sk.ngan_hang} cho ${dc.lech.length} khế ước?`)) post("/fin/cap-nhat-theo-sao-ke", { ngan_hang: sk.ngan_hang, den_ngay: sk.den_ngay, dong: dc._dong }).then((r) => { if (r) { toast(r.message); setDc(null); } }); }}>Cập nhật hệ thống theo sao kê</button>}
        </>}
        {dc.khong_thay_tren_sao_ke.length > 0 && <><h2>Hệ thống đang theo dõi nhưng không có trên sao kê</h2>
          <div className="panel" style={{ borderColor: "var(--red)" }}>{dc.khong_thay_tren_sao_ke.map((k: any) => <div key={k.ke_uoc} style={{ marginBottom: 8 }}>
            <Tag cls="red">!</Tag> <b>{k.ke_uoc}</b> · {k.partner} · dư nợ hệ thống {vnd(k.du_no_he_thong)}{k.the_chap && <> · TSTC: {k.the_chap}</>}
            <div className="muted">{k.y_nghia}</div></div>)}</div></>}
        {dc.ngoai_pham_vi && dc.ngoai_pham_vi.length > 0 && <><h2>Ngoài phạm vi theo dõi vay xe — {dc.ngoai_pham_vi.length} khoản, cộng {vnd(dc.tong_ngoai_pham_vi)}</h2>
          <p className="muted">Vay bất động sản và vay vốn lưu động. Nêu ra để thấy đủ bức tranh nợ ngân hàng, KHÔNG phải việc phải nạp vào phân hệ vay xe.</p>
          <div className="panel wrap"><table><thead><tr><th>Khế ước</th><th style={{ textAlign: "right" }}>Dư nợ</th><th>Lãi suất</th><th>Đáo hạn</th></tr></thead><tbody>
            {dc.ngoai_pham_vi.map((k: any) => <tr key={k.ke_uoc}><td>{k.ke_uoc}</td><td style={{ textAlign: "right" }}>{vnd(k.du_no)}</td><td>{k.lai_suat ? k.lai_suat + "%" : ""}</td><td>{k.dao_han ? fmtD(k.dao_han) : ""}</td></tr>)}
          </tbody></table></div></>}
        {dc.chua_theo_doi.length > 0 && <><h2>Ngân hàng đang cho vay nhưng hệ thống chưa theo dõi — cộng {vnd(dc.tong_chua_theo_doi)}</h2>
          <div className="panel wrap"><table><thead><tr><th>Khế ước</th><th style={{ textAlign: "right" }}>Dư nợ</th><th>Lãi suất</th><th>Đáo hạn</th><th>Mục đích</th></tr></thead><tbody>
            {dc.chua_theo_doi.map((k: any) => <tr key={k.ke_uoc}><td>{k.ke_uoc}</td><td style={{ textAlign: "right" }}>{vnd(k.du_no)}</td><td>{k.lai_suat ? k.lai_suat + "%" : ""}</td><td>{k.dao_han ? fmtD(k.dao_han) : ""}</td><td className="muted">{k.muc_dich}</td></tr>)}
          </tbody></table></div>
          <p className="muted">Dự báo dòng tiền 13 tuần chỉ tính được lịch trả gốc/lãi của khế ước đã có trong hệ thống. Khoản vay nào chưa nạp thì chưa xuất hiện trong dự báo.</p></>}
        {dc.khop.length > 0 && <><h2>Khớp</h2><div className="panel">{dc.khop.map((k: any) => <div key={k.ke_uoc}><Tag cls="ok">✓</Tag> {k.ke_uoc} · {k.partner} · {vnd(k.du_no_sao_ke)}</div>)}</div></>}
      </>}
    </>}
  </>);
}
/** PHÂN BỔ TIỀN RA — Đợt E5, 13/10/2026. Chủ tịch duyệt hình dáng qua bản dựng thử.
 *
 *  Màn hình này là CỬA của một con số: từ đợt này `nghia_vu.da_tra` tăng lên nhờ người bấm ở đây,
 *  không nhờ ai nhập tay vào cơ sở dữ liệu. Không có cửa thì con số ấy là việc còn thiếu.
 *
 *  Ô "đợt" để TRỐNG là hợp lệ, không phải là chưa điền xong: một nghĩa vụ không chia đợt vẫn trả
 *  được. Nói ra ngay dưới ô, vì một ô trống không giải thích thì người dùng tưởng mình làm thiếu.
 */
function PhanBoRa() {
  const { toast } = useShell();
  const [gd, setGd] = useState<any[]>([]);
  const [nv, setNv] = useState<any[]>([]);
  const [chon, setChon] = useState<number | null>(null);
  const [bang, setBang] = useState<any>(null);
  const [dot, setDot] = useState<any[]>([]);
  const [f, setF] = useState<any>({ nghia_vu_id: "", dot_id: "", so_tien: "", ghi_chu: "" });
  const nap = useCallback(() => {
    api("/bank-transactions?limit=200").then((ds: any[]) =>
      setGd(ds.filter((t) => t.transfer_type === "out")));
    api("/fin/nghia-vu/chi-tiet").then((r: any) =>
      setNv((r.chi_tiet || []).filter((x: any) => x.huong === "chi")));
  }, []);
  useEffect(() => { nap(); }, [nap]);
  useEffect(() => { if (chon) api(`/bank-transactions/${chon}/phan-bo`).then(setBang); }, [chon]);
  useEffect(() => {
    if (f.nghia_vu_id) api(`/fin/nghia-vu/${f.nghia_vu_id}/dot`).then(setDot); else setDot([]);
  }, [f.nghia_vu_id]);

  async function ghi() {
    try {
      const r = await api(`/bank-transactions/${chon}/phan-bo-ra`, {
        method: "POST",
        json: { dong: [{ nghia_vu_id: Number(f.nghia_vu_id), dot_id: f.dot_id ? Number(f.dot_id) : null,
                         so_tien: Number(String(f.so_tien).replace(/[^\d.-]/g, "")), ghi_chu: f.ghi_chu }] },
      });
      toast(r.message);
      (r.canh_bao || []).forEach((c: string) => toast(c, true));
      setF({ nghia_vu_id: "", dot_id: "", so_tien: "", ghi_chu: "" });
      api(`/bank-transactions/${chon}/phan-bo`).then(setBang); nap();
    } catch (x) { toast(errMsg(x), true); }
  }

  return (<>
    <h1>Phân bổ tiền ra — khoản chi này trả cho nghĩa vụ nào</h1>
    <p className="muted">Một khoản chi chia được cho nhiều nghĩa vụ, và một đợt trả được bằng nhiều
      khoản. Trả dư thì màn hình <b>cảnh báo</b> chứ không chặn — phần dư thành trả trước.</p>
    <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Nội dung</th><th className="num">Số tiền</th><th className="num">Chưa phân bổ</th><th></th></tr></thead>
      <tbody>{gd.map((t) => <tr key={t.id}><td>{fmtD(t.transaction_date)}</td><td>{t.content}</td>
        <td className="num">{vnd(Math.abs(Number(t.amount || 0)))}</td>
        <td className="num">{t.chua_phan_bo === null || t.chua_phan_bo === undefined
          ? <span className="muted">—</span> : <b>{vnd(t.chua_phan_bo)}</b>}</td>
        <td><button className="act" style={{ margin: 0 }} onClick={() => setChon(t.id)}>Phân bổ</button></td></tr>)}
      </tbody></table></div>

    {bang && <div className="panel">
      <h2>Giao dịch {bang.sepay_id} · {vnd(Math.abs(bang.so_tien))} · chưa phân bổ <b>{vnd(bang.chua_phan_bo)}</b></h2>
      <table><thead><tr><th>Nghĩa vụ</th><th>Đối tượng</th><th>Đợt</th><th className="num">Số tiền</th><th>Ghi chú</th><th>Trạng thái</th></tr></thead>
        <tbody>{(bang.dong || []).map((d: any) => <tr key={d.id} style={{ opacity: d.huy ? 0.5 : 1 }}>
          <td className="mono">{d.nghia_vu_ma || d.booking_code}</td><td>{d.doi_tuong || d.khach}</td>
          <td>{d.dot_stt ?? <span className="muted">—</span>}</td>
          <td className="num">{vnd(d.so_tien)}</td><td className="muted">{d.ghi_chu}</td>
          <td>{d.huy ? <Tag cls="warn">huỷ: {d.huy_ly_do}</Tag> : <Tag cls="ok">đã ghi</Tag>}</td></tr>)}
        </tbody></table>
      <div className="grid" style={{ marginTop: 10 }}>
        <div><label>Nghĩa vụ</label><select value={f.nghia_vu_id}
          onChange={(e) => setF({ ...f, nghia_vu_id: e.target.value, dot_id: "" })}>
          <option value="">— chọn —</option>
          {nv.map((x: any) => <option key={x.id} value={x.id}>{x.ma_goc} · {x.doi_tuong} · còn {vnd(x.con_lai)}</option>)}
        </select></div>
        <div><label>Đợt (để trống nếu nghĩa vụ không chia đợt)</label>
          <select value={f.dot_id} onChange={(e) => setF({ ...f, dot_id: e.target.value })}>
            <option value="">— không chia đợt —</option>
            {dot.filter((d: any) => !d.da_tra_du).map((d: any) =>
              <option key={d.id} value={d.id}>Đợt {d.so_thu_tu} · hạn {fmtD(d.ngay_han)} · còn {vnd(d.con_lai)}</option>)}
          </select></div>
        <div><label>Số tiền</label><input value={f.so_tien} onChange={(e) => setF({ ...f, so_tien: e.target.value })} /></div>
        <div><label>Ghi chú</label><input value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></div>
      </div>
      <button className="act orange" disabled={!f.nghia_vu_id || !f.so_tien} onClick={ghi}>Ghi phân bổ</button>
    </div>}
  </>);
}

export default function Page() { return <Shell><Finance /><PhanBoRa /></Shell>; }
