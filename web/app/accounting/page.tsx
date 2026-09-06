"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const SRC: Record<string, string> = { thu_tien: "Thu tiền (R1)", hoa_don: "Hóa đơn", quyet_toan: "Quyết toán tour", thu_cong: "Kế toán lập", dao: "Bút toán đảo", de_nghi_chi: "Đề nghị chi (R3)", lenh_chi: "Lệnh chi", luong: "Bảng lương (R6)", ket_chuyen: "Kết chuyển 911" };
const EST: Record<string, [string, string]> = { nhap: ["Nháp", "warn"], da_ghi_so: ["Đã ghi sổ", "ok"], huy: ["Hủy", "red"] };
const IST: Record<string, [string, string]> = { nhap: ["Nháp", "warn"], da_phat_hanh: ["Đã phát hành", "ok"], huy: ["Hủy", "red"] };
const thisPeriod = () => new Date().toISOString().slice(0, 7);
const TABS = [["journal", "Chứng từ ghi sổ"], ["ledger", "Sổ cái"], ["tb", "Cân đối phát sinh"], ["invoices", "Hóa đơn điện tử"], ["bctc", "BCTC TT99"], ["fs", "BCTC rút gọn"], ["tax", "Tờ khai thuế"], ["misa", "MISA ↔ VTOS"], ["periods", "Khóa kỳ"]];
const SRC2: Record<string, string> = { misa: "Sổ MISA", so_du_dau_ky: "Số dư đầu kỳ", kiem_toan: "Điều chỉnh kiểm toán" };
const dl = (path: string, name: string) => fetch(`/api/v1${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token")}` } }).then((r) => r.blob()).then((b) => { const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = name; a.click(); });

function MisaPanel({ toast, isKT }: { toast: (m: string, e?: boolean) => void; isKT: boolean }) {
  const [stats, setStats] = useState<any>(null);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const [asOf, setAsOf] = useState("2026-06-30");
  const [col, setCol] = useState("close");
  const [replace, setReplace] = useState(false);
  const [range, setRange] = useState({ from: "2026-01-01", to: "2026-06-30" });
  const files = useState<Record<string, File | null>>({})[0];
  const reload = () => api("/partners/stats").then(setStats);
  useEffect(() => { reload(); }, []);
  const send = async (path: string, key: string, extra: Record<string, string> = {}, objKey?: string) => {
    const f = files[key]; if (!f) { toast("Chọn tệp Excel trước", true); return; }
    const fd = new FormData(); fd.append("file", f); if (objKey && files[objKey]) fd.append("objects", files[objKey]!);
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    setBusy(path);
    try { const r = await api(path, { method: "POST", body: fd }); setRes(r); toast(r.message || "Xong"); reload(); } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const pick = (key: string) => <input type="file" accept=".xlsx" onChange={(e) => { files[key] = e.target.files?.[0] || null; }} />;
  return <>
    <p className="muted">Một cấu trúc dữ liệu với MISA (định hướng 06/9/2026): cùng số hiệu tài khoản, mã đối tượng (MST/CCCD), mã công trình = mã tour. Nạp các tệp Excel xuất từ MISA AMIS – không cần API.</p>
    {stats && <div className="panel"><b>Hiện có:</b> {stats.partners} đối tượng ({stats.customers} khách, {stats.suppliers} NCC) · {stats.projects} công trình ({stats.projects_linked} đã gắn tour) · {stats.misa_entries} chứng từ nạp từ sổ MISA · số dư đầu kỳ: {stats.opening_entries.join(", ") || "chưa nhập"}</div>}
    <div className="grid">
      <div className="panel"><h3>1. Danh mục đối tượng</h3><p className="muted">“Danh sách khách hàng”, “Danh sách nhà cung cấp” (MISA) hoặc DataNCC của Điều hành.</p>{pick("p")}{isKT && <button className="act" disabled={!!busy} onClick={() => send("/misa/partners", "p")}>Nạp</button>}</div>
      <div className="panel"><h3>2. Danh mục công trình (tour)</h3><p className="muted">“Danh sách công trình” MISA. Mã trùng mã tour VTOS → tự gắn.</p>{pick("c")}{isKT && <button className="act" disabled={!!busy} onClick={() => send("/misa/projects", "c")}>Nạp</button>}</div>
      <div className="panel"><h3>3. Số dư đầu kỳ</h3><p className="muted">“Bảng cân đối tài khoản (mẫu quản trị)” + tùy chọn “Tổng hợp công nợ theo đối tượng” để tách 131/331/1388/141 theo từng khách/NCC. Chỉ ghi tài khoản chi tiết.</p>
        Bảng cân đối: {pick("tb")}<br />Công nợ theo đối tượng: {pick("ob")}<br />
        <label>Ngày số dư <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label> <label>Lấy cột <select value={col} onChange={(e) => setCol(e.target.value)}><option value="close">Cuối kỳ</option><option value="open">Đầu kỳ</option></select></label> <label><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> Thay thế số dư đã nhập</label><br />
        <button className="act grey" disabled={!!busy} onClick={() => send("/misa/trial-balance/preview", "tb")}>Xem trước</button> {isKT && <button className="act orange" disabled={!!busy} onClick={() => send("/misa/opening-balance", "tb", { as_of: asOf, column: col, replace: String(replace) }, "ob")}>Ghi số dư đầu kỳ</button>}</div>
      <div className="panel"><h3>4. Sổ nhật ký chung</h3><p className="muted">“Sổ nhật ký chung” MISA (có Mã đối tượng). Mỗi số chứng từ = một chứng từ VTOS nguồn “Sổ MISA”; đã nạp thì bỏ qua. Nên chạy “Đọc thử” trước.</p>{pick("j")}<br />
        <label>Từ <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label> <label>đến <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label><br />
        <button className="act grey" disabled={!!busy} onClick={() => send("/misa/journal", "j", { dry_run: "true", date_from: range.from, date_to: range.to })}>Đọc thử</button> {isKT && <button className="act orange" disabled={!!busy} onClick={() => send("/misa/journal", "j", { date_from: range.from, date_to: range.to })}>Nạp vào sổ</button>}</div>
      <div className="panel"><h3>5. Đối chiếu VTOS – MISA</h3><p className="muted">Nạp “Bảng cân đối tài khoản” MISA của kỳ cần so; liệt kê tài khoản lệch.</p>{pick("r")}<br /><button className="act" disabled={!!busy} onClick={() => send("/misa/reconcile", "r", { column: col })}>Đối chiếu</button></div>
      <div className="panel"><h3>6. Xuất ngược sang MISA (mẫu Import)</h3><p className="muted">Kế toán nhập vào MISA trong thời gian chạy song song.</p>
        <button className="act grey" onClick={() => dl(`/misa/export/purchases.xlsx?date_from=${range.from}&date_to=${range.to}`, "Import_MISA_MuaDichVu.xlsx")}>Mua dịch vụ (57 cột)</button>
        <button className="act grey" onClick={() => dl(`/misa/export/entries.xlsx?date_from=${range.from}&date_to=${range.to}`, "Import_MISA_ButToan.xlsx")}>Bút toán tổng hợp</button>
        <button className="act grey" onClick={() => dl(`/misa/export/projects.xlsx?date_from=${range.from}`, "Import_DanhMuc_CongTrinh.xlsx")}>Danh mục công trình</button></div>
      <div className="panel"><h3>7. Chốt sổ theo BCTC kiểm toán/soát xét</h3><p className="muted">Dùng khi số MISA thô chưa chuẩn (thiếu phân loại vay ngắn/dài hạn, thiếu trích trước…). Ghi đè mốc 30/06/2026 bằng đúng số trên BCTC riêng đã soát xét (Baker Tilly A&C). Nguồn “Điều chỉnh kiểm toán” trên Chứng từ ghi sổ.</p>
        <label><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> Thay thế nếu đã chốt</label><br />
        {isKT && <button className="act orange" disabled={!!busy} onClick={async () => { const fd = new FormData(); fd.append("column", col); fd.append("replace", String(replace)); setBusy("kt"); try { const r = await api("/misa/kiem-toan-checkpoint", { method: "POST", body: fd }); setRes(r); toast(r.message || "Xong"); reload(); } catch (x) { toast(errMsg(x), true); } setBusy(""); }}>Chốt sổ theo BCTC kiểm toán</button>}</div>
    </div>
    {busy && <p className="muted">Đang xử lý {busy}… (sổ nhật ký lớn có thể mất vài phút)</p>}
    {res && <div className="panel wrap"><h3>Kết quả</h3>
      {res.rows && res.diff_count !== undefined ? <><p>{res.period} · {res.accounts} tài khoản · <b>{res.diff_count} lệch</b> · tổng lệch {vnd(res.diff_total)}</p><table><thead><tr><th>TK</th><th>Tên</th><th>MISA</th><th>VTOS</th><th>Lệch</th></tr></thead><tbody>{res.rows.map((r: any) => <tr key={r.account}><td className="mono">{r.account}</td><td>{r.name}</td><td style={{ textAlign: "right" }}>{vnd(r.misa)}</td><td style={{ textAlign: "right" }}>{vnd(r.vtos)}</td><td style={{ textAlign: "right", color: "#b00" }}>{vnd(r.diff)}</td></tr>)}</tbody></table></>
        : res.rows ? <><p>{res.period} · {res.accounts} TK ({res.detail_accounts} chi tiết) · đầu kỳ Nợ {vnd(res.open_debit)} / Có {vnd(res.open_credit)} · cuối kỳ Nợ {vnd(res.close_debit)} / Có {vnd(res.close_credit)}</p><table><thead><tr><th>TK</th><th>Tên</th><th>ĐK Nợ</th><th>ĐK Có</th><th>CK Nợ</th><th>CK Có</th></tr></thead><tbody>{res.rows.map((r: any) => <tr key={r.code}><td className="mono">{r.code}</td><td>{r.name}</td><td style={{ textAlign: "right" }}>{vnd(r.open_d)}</td><td style={{ textAlign: "right" }}>{vnd(r.open_c)}</td><td style={{ textAlign: "right" }}>{vnd(r.close_d)}</td><td style={{ textAlign: "right" }}>{vnd(r.close_c)}</td></tr>)}</tbody></table></>
        : <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(res, null, 1)}</pre>}</div>}
  </>;
}

function BctcPanel({ toast }: { toast: (m: string, e?: boolean) => void }) {
  const [upto, setUpto] = useState("2026-06-30");
  const [since, setSince] = useState("2026-01-01");
  const [rep, setRep] = useState<any>(null);
  const load = () => api(`/reports/bctc?upto=${upto}&since=${since}`).then(setRep).catch((x) => toast(errMsg(x), true));
  useEffect(() => { load(); }, []);
  const row = (r: any) => <tr key={r.code + r.name} style={{ fontWeight: r.group ? 700 : 400 }}><td>{r.name}</td><td className="mono">{r.code}</td><td className="muted">{r.note}</td><td style={{ textAlign: "right" }}>{r.now === null ? "" : vnd(r.now)}</td><td style={{ textAlign: "right" }}>{r.prev === null ? "" : vnd(r.prev)}</td></tr>;
  return <>
    <p className="muted">Mẫu Thông tư 99/2025 đúng cấu trúc bộ đã nộp UBCK: mỗi tài khoản chi tiết ánh xạ mã chỉ tiêu (dư Nợ / dư Có); 131, 331, 1388, 3388, 141 xét theo từng đối tượng; lãi/lỗ chưa kết chuyển cộng vào 420.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}><label>Từ <input type="date" value={since} onChange={(e) => setSince(e.target.value)} /></label><label>đến <input type="date" value={upto} onChange={(e) => setUpto(e.target.value)} /></label><button className="act" onClick={load}>Lập báo cáo</button><button className="act grey" onClick={() => dl(`/reports/bctc.xlsx?upto=${upto}&since=${since}`, `BCTC_TT99_${upto}.xlsx`)}>Xuất Excel (bố cục UBCK)</button>{rep && (rep.balanced ? <Tag cls="ok">Cân: 280 = 440</Tag> : <Tag cls="red">LỆCH 280 ≠ 440</Tag>)}</div>
    {rep && <>
      <h2>Báo cáo tình hình tài chính – tại {fmtD(rep.upto)} (so với {fmtD(rep.compare_upto)})</h2>
      <div className="panel wrap"><table><thead><tr><th>Chỉ tiêu</th><th>Mã</th><th>TM</th><th>Số cuối kỳ</th><th>Số đầu năm</th></tr></thead><tbody>{rep.thtc.map(row)}</tbody></table></div>
      <h2>Báo cáo kết quả hoạt động kinh doanh – từ {fmtD(rep.since)} đến {fmtD(rep.upto)}</h2>
      <div className="panel wrap"><table><thead><tr><th>Chỉ tiêu</th><th>Mã</th><th>TM</th><th>Kỳ này</th><th>Cùng kỳ năm trước</th></tr></thead><tbody>{rep.kqkd.map(row)}</tbody></table></div>
      <p className="muted">Lãi/lỗ chưa kết chuyển tính vào 420: {vnd(rep.unposted_pl)}. Lưu chuyển tiền tệ gián tiếp và thuyết minh B09 làm ở bước tiếp theo.</p>
    </>}
  </>;
}

function Accounting() {
  const { user, toast } = useShell();
  const isKT = user?.role === "ketoan";
  const [tab, setTab] = useState("journal");
  const [period, setPeriod] = useState(thisPeriod());
  const [accounts, setAccounts] = useState<any[]>([]);
  const [entries, setEntries] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [acc, setAcc] = useState("131");
  const [ledger, setLedger] = useState<any>(null);
  const [tb, setTb] = useState<any>(null);
  const [invs, setInvs] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [fs, setFs] = useState<any>({});
  const [tax, setTax] = useState<any>({});
  const [bookings, setBookings] = useState<any[]>([]);
  const [lines, setLines] = useState([{ account: "642", debit: "", credit: "" }, { account: "111", debit: "", credit: "" }]);
  const [desc, setDesc] = useState("");
  const [inv, setInv] = useState({ booking_id: "", customer_tax_code: "", customer_address: "", vat_rate: "" });

  const load = useCallback(async () => {
    if (!accounts.length) api("/accounts").then(setAccounts);
    if (tab === "journal") api(`/journal?period=${period}`).then(setEntries);
    if (tab === "ledger") api(`/ledger?account=${acc}&period=${period}`).then(setLedger).catch(() => setLedger(null));
    if (tab === "tb") api(`/trial-balance?period=${period}`).then(setTb);
    if (tab === "invoices") { api("/invoices").then(setInvs); api("/collections/summary").then((s) => setBookings(s.bookings)); }
    if (tab === "periods") api("/periods").then(setPeriods);
    if (tab === "fs") Promise.all([api(`/reports/balance-sheet?period=${period}`), api(`/reports/income-statement?period=${period}`), api(`/reports/cash-flow?period=${period}`)]).then(([bs, pl, cf]) => setFs({ bs, pl, cf }));
    if (tab === "tax") Promise.all([api(`/tax/vat?period=${period}`), api(`/tax/pit?period=${period}`)]).then(([vat, pit]) => setTax({ vat, pit }));
  }, [tab, period, acc, accounts.length]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const num = (v: string) => Number(String(v).replace(/[^\d.-]/g, "")) || 0;
  const td = lines.reduce((a, l) => a + num(l.debit), 0), tc = lines.reduce((a, l) => a + num(l.credit), 0);

  return (<>
    <h1>Kế toán TT99/2025 – robot R2 ghi sổ tự động</h1>
    <p className="muted">Bút toán sinh tự động khi Kế toán xác nhận phiếu thu (Nợ 111/112 – Có 131), phát hành hóa đơn (Nợ 131 – Có 511, 3331), xác nhận quyết toán tour (Nợ 154 – Có 331; Nợ 632 – Có 154). Chứng từ đã ghi sổ không sửa – chỉ lập bút toán đảo. Kỳ đã khóa không ghi sổ.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "journal" && <>
      {isKT && <div className="panel"><h2>Lập chứng từ tay</h2>
        <label>Diễn giải<input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="VD: Chi tiền điện tháng 9" /></label>
        <table><thead><tr><th>Tài khoản</th><th>Nợ</th><th>Có</th><th></th></tr></thead><tbody>
          {lines.map((l, i) => <tr key={i}>
            <td><select value={l.account} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, account: e.target.value } : x))}>{accounts.map((a) => <option key={a.code} value={a.code}>{a.code} – {a.name}</option>)}</select></td>
            <td><input value={l.debit} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, debit: e.target.value } : x))} /></td>
            <td><input value={l.credit} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, credit: e.target.value } : x))} /></td>
            <td>{lines.length > 2 && <button className="act grey" style={{ margin: 0 }} onClick={() => setLines(lines.filter((_, j) => j !== i))}>×</button>}</td></tr>)}
          <tr><td><b>Tổng</b></td><td><b>{vnd(td)}</b></td><td><b>{vnd(tc)}</b></td><td>{Math.abs(td - tc) >= 1 && <Tag cls="red">Chưa cân</Tag>}</td></tr>
        </tbody></table>
        <button className="act grey" onClick={() => setLines([...lines, { account: "111", debit: "", credit: "" }])}>+ dòng</button>
        <button className="act" disabled={!desc || td <= 0 || Math.abs(td - tc) >= 1} onClick={() => post("/journal", { entry_date: new Date().toISOString().slice(0, 10), description: desc, post: false, lines: lines.map((l) => ({ account: l.account, debit: num(l.debit), credit: num(l.credit) })) }).then((r) => { if (r) { setDesc(""); setLines([{ account: "642", debit: "", credit: "" }, { account: "111", debit: "", credit: "" }]); } })}>Lưu nháp</button>
      </div>}
      <div className="panel wrap"><table><thead><tr><th>Số CT</th><th>Ngày</th><th>Diễn giải</th><th>Nguồn</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Trạng thái</th><th>Người ghi</th><th></th></tr></thead>
        <tbody>{entries.length ? entries.map((e) => <>
          <tr key={e.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === e.id ? null : e.id)}><td><b>{e.code}</b></td><td>{fmtD(e.entry_date)}</td><td>{e.description}</td><td className="muted">{SRC[e.source_type] || SRC2[e.source_type] || e.source_type}<div>{e.source_ref}</div></td><td style={{ textAlign: "right" }}>{vnd(e.amount)}</td>
            <td><Tag cls={EST[e.status]?.[1]}>{EST[e.status]?.[0]}</Tag>{e.reversed_by_id && <Tag cls="red">đã đảo</Tag>}</td><td className="muted">{e.posted_by || e.created_by}</td>
            <td onClick={(ev) => ev.stopPropagation()}>{isKT && e.status === "nhap" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/journal/${e.id}/post`)}>Ghi sổ</button>}
              {isKT && e.status === "da_ghi_so" && !e.reversed_by_id && <button className="act grey" style={{ margin: 0 }} onClick={() => { const r = prompt("Lý do đảo bút toán?"); if (r) post(`/journal/${e.id}/reverse`, { reason: r }); }}>Đảo</button>}</td></tr>
          {open === e.id && <tr key={e.id + "l"}><td colSpan={8}><table style={{ margin: "4px 0 8px 24px", width: "auto" }}><tbody>{e.lines.map((l: any) => <tr key={l.id}><td className="mono">{l.account}</td><td>{accounts.find((a) => a.code === l.account)?.name}</td><td style={{ textAlign: "right" }}>{l.debit ? "Nợ " + vnd(l.debit) : ""}</td><td style={{ textAlign: "right" }}>{l.credit ? "Có " + vnd(l.credit) : ""}</td><td className="muted">{l.partner_code && <code>{l.partner_code}</code>} {l.partner} {l.project_code && <Tag cls="grey">{l.project_code}</Tag>} {l.note}</td></tr>)}</tbody></table></td></tr>}
        </>) : <tr><td colSpan={8} className="muted">Chưa có chứng từ trong kỳ.</td></tr>}</tbody></table></div>
    </>}

    {tab === "ledger" && <>
      <div><label>Tài khoản <select value={acc} onChange={(e) => setAcc(e.target.value)}>{accounts.map((a) => <option key={a.code} value={a.code}>{a.code} – {a.name}</option>)}</select></label></div>
      {ledger && <><div className="kpis"><div className="kpi"><b>{vnd(ledger.opening)}</b><span>Dư đầu kỳ</span></div><div className="kpi"><b>{vnd(ledger.total_debit)}</b><span>Phát sinh Nợ</span></div><div className="kpi"><b>{vnd(ledger.total_credit)}</b><span>Phát sinh Có</span></div><div className="kpi"><b>{vnd(ledger.closing)}</b><span>Dư cuối kỳ</span></div></div>
        <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Số CT</th><th>Diễn giải</th><th>Đối tượng</th><th style={{ textAlign: "right" }}>Nợ</th><th style={{ textAlign: "right" }}>Có</th><th style={{ textAlign: "right" }}>Số dư</th></tr></thead>
          <tbody>{ledger.rows.length ? ledger.rows.map((r: any, i: number) => <tr key={i}><td>{fmtD(r.date)}</td><td>{r.code}</td><td>{r.description}</td><td className="muted">{r.partner}</td><td style={{ textAlign: "right" }}>{r.debit ? vnd(r.debit) : ""}</td><td style={{ textAlign: "right" }}>{r.credit ? vnd(r.credit) : ""}</td><td style={{ textAlign: "right" }}>{vnd(r.balance)}</td></tr>) : <tr><td colSpan={7} className="muted">Không phát sinh.</td></tr>}</tbody></table></div></>}
    </>}

    {tab === "tb" && tb && <>
      <p>{tb.balanced ? <Tag cls="ok">Cân đối Nợ = Có</Tag> : <Tag cls="red">LỆCH – kiểm tra ngay</Tag>}</p>
      <div className="panel wrap"><table><thead><tr><th>TK</th><th>Tên tài khoản</th><th style={{ textAlign: "right" }}>Dư đầu Nợ</th><th style={{ textAlign: "right" }}>Dư đầu Có</th><th style={{ textAlign: "right" }}>PS Nợ</th><th style={{ textAlign: "right" }}>PS Có</th><th style={{ textAlign: "right" }}>Dư cuối Nợ</th><th style={{ textAlign: "right" }}>Dư cuối Có</th></tr></thead>
        <tbody>{tb.rows.map((r: any) => <tr key={r.account}><td className="mono"><b>{r.account}</b></td><td>{r.name}</td>{["open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit"].map((k) => <td key={k} style={{ textAlign: "right" }}>{r[k] ? vnd(r[k]) : ""}</td>)}</tr>)}
          <tr><td></td><td><b>Cộng</b></td>{["open_debit", "open_credit", "debit", "credit", "close_debit", "close_credit"].map((k) => <td key={k} style={{ textAlign: "right" }}><b>{vnd(tb.total[k])}</b></td>)}</tr></tbody></table></div>
    </>}

    {tab === "invoices" && <>
      {isKT && <div className="panel"><h2>Lập hóa đơn GTGT từ booking</h2><div className="grid">
        <label>Booking<select value={inv.booking_id} onChange={(e) => setInv({ ...inv, booking_id: e.target.value })}><option value="">– chọn –</option>{bookings.map((b) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · {vnd(b.total)}</option>)}</select></label>
        <label>Mã số thuế người mua<input value={inv.customer_tax_code} onChange={(e) => setInv({ ...inv, customer_tax_code: e.target.value })} /></label>
        <label>Địa chỉ<input value={inv.customer_address} onChange={(e) => setInv({ ...inv, customer_address: e.target.value })} /></label>
        <label>Thuế suất (trống = tham số)<input placeholder="0.10 hoặc 0.08" value={inv.vat_rate} onChange={(e) => setInv({ ...inv, vat_rate: e.target.value })} /></label>
      </div><button className="act" disabled={!inv.booking_id} onClick={() => post("/invoices", { booking_id: Number(inv.booking_id), customer_tax_code: inv.customer_tax_code, customer_address: inv.customer_address, vat_rate: inv.vat_rate ? Number(inv.vat_rate) : null }).then((r) => r && setInv({ booking_id: "", customer_tax_code: "", customer_address: "", vat_rate: "" }))}>Lập hóa đơn nháp</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Số HĐ</th><th>Ngày</th><th>Booking</th><th>Người mua</th><th style={{ textAlign: "right" }}>Chưa thuế</th><th style={{ textAlign: "right" }}>GTGT</th><th style={{ textAlign: "right" }}>Tổng</th><th>Trạng thái</th><th>Mã tra cứu</th>{isKT && <th></th>}</tr></thead>
        <tbody>{invs.length ? invs.map((i) => <tr key={i.id}><td><b>{i.no || "(nháp)"}</b></td><td>{fmtD(i.issue_date)}</td><td>{i.booking_code}<div className="muted">{i.tour_code}</div></td><td>{i.customer_name}<div className="muted">{i.customer_tax_code}</div></td><td style={{ textAlign: "right" }}>{vnd(i.pre_tax)}</td><td style={{ textAlign: "right" }}>{vnd(i.vat)} <span className="muted">({Math.round(i.vat_rate * 100)}%)</span></td><td style={{ textAlign: "right" }}><b>{vnd(i.total)}</b></td>
          <td><Tag cls={IST[i.status]?.[1]}>{IST[i.status]?.[0]}</Tag></td><td className="mono muted">{i.provider_ref}</td>
          {isKT && <td>{i.status === "nhap" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/invoices/${i.id}/issue`)}>Phát hành</button>}{i.status !== "huy" && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={() => { const r = prompt("Lý do hủy hóa đơn?"); if (r) post(`/invoices/${i.id}/cancel`, { reason: r }); }}>Hủy</button>}</td>}</tr>) : <tr><td colSpan={10} className="muted">Chưa có hóa đơn.</td></tr>}</tbody></table></div>
      <p className="muted">Bản pilot cấp số nội bộ (adapter <code>noi_bo</code>). Khi ký hợp đồng nhà cung cấp HĐĐT (Viettel / VNPT / MISA meInvoice…) thay adapter gọi API, số hóa đơn và mã CQT lấy từ nhà cung cấp.</p>
    </>}

    {tab === "fs" && fs.bs && <>
      <h2>Báo cáo kết quả kinh doanh (B02-DN) – kỳ {period}</h2>
      <div className="panel wrap"><table><tbody>{fs.pl.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["20", "30", "50", "60"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table>
        <p className="muted">Quản trị: lãi vay {vnd(fs.pl.management.interest)} · khấu hao {vnd(fs.pl.management.depreciation)} · LN sau lãi vay trước khấu hao <b>{vnd(fs.pl.management.profit_after_interest_before_dep)}</b> (căn cứ thưởng GĐ KD).</p></div>
      <h2>Bảng cân đối kế toán (B01-DN) – cuối kỳ {period} {fs.bs.balanced ? <Tag cls="ok">Cân</Tag> : <Tag cls="red">LỆCH</Tag>}</h2>
      <div className="grid">
        <div className="panel wrap"><b>TÀI SẢN</b><table><tbody>{fs.bs.assets.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}<tr><td><b>Tổng tài sản</b></td><td style={{ textAlign: "right" }}><b>{vnd(fs.bs.total_assets)}</b></td></tr></tbody></table></div>
        <div className="panel wrap"><b>NGUỒN VỐN</b><table><tbody>{fs.bs.liabilities.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}{fs.bs.equity.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}<tr><td><b>Tổng nguồn vốn</b></td><td style={{ textAlign: "right" }}><b>{vnd(fs.bs.total_liabilities + fs.bs.total_equity)}</b></td></tr></tbody></table></div>
      </div>
      <h2>Lưu chuyển tiền tệ trực tiếp (B03-DN) {fs.cf.reconciled ? <Tag cls="ok">Khớp tiền đầu/cuối kỳ</Tag> : <Tag cls="red">Chưa khớp</Tag>}</h2>
      <div className="panel wrap"><table><tbody>{fs.cf.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["20", "30", "40", "50", "70"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table></div>
      {isKT && <button className="act orange" onClick={() => post(`/reports/closing-entries/${period}`)}>Robot lập chứng từ kết chuyển 911 (nháp)</button>}
      <p className="muted">Mẫu rút gọn theo nhóm tài khoản cấp 1 từ chứng từ đã ghi sổ; số dư đầu kỳ chuyển từ MISA/BCTC kiểm toán nhập khi cắt chuyển. Kế toán trưởng đối chiếu mẫu đầy đủ TT99/2025 trước khi phát hành; hợp nhất 2 pháp nhân và công ty liên kết làm ở giai đoạn 4.</p>
    </>}

    {tab === "tax" && tax.vat && <>
      <h2>Tờ khai GTGT (01/GTGT) – kỳ {period} · {tax.vat.invoices} hóa đơn đầu ra</h2>
      <div className="panel wrap"><table><tbody>{tax.vat.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["[40]", "[43]"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table><p className="muted">{tax.vat.note}</p>
        {isKT && <a className="act" style={{ display: "inline-block", textDecoration: "none" }} href={`/api/v1/tax/vat/xml?period=${period}`} onClick={(e) => { e.preventDefault(); fetch(`/api/v1/tax/vat/xml?period=${period}`, { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token")}` } }).then((r) => r.blob()).then((b) => { const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = `01GTGT_${period}.xml`; a.click(); }); }}>Xuất XML nạp HTKK/eTax</a>}</div>
      <h2>Tờ khai TNCN (05/KK-TNCN)</h2>
      <div className="panel wrap"><table><tbody>{tax.pit.rows.map((r: any) => <tr key={r[0]}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table><p className="muted">{tax.pit.note}</p></div>
      <p className="muted">Robot R5 chỉ lập tờ khai từ sổ và xuất XML; Kế toán trưởng kiểm tra, ký số bằng token công ty và nộp trên eTax; lưu biên nhận vào kho chứng từ. Cấu trúc XML cần đối chiếu với phiên bản HTKK hiện hành trước lần nộp đầu.</p>
    </>}

    {tab === "misa" && <MisaPanel toast={toast} isKT={isKT || user?.role === "cntt"} />}
    {tab === "bctc" && <BctcPanel toast={toast} />}

    {tab === "periods" && <div className="panel wrap"><table><thead><tr><th>Kỳ</th><th>Trạng thái</th><th>Khóa bởi</th><th>Lúc</th><th>Ghi chú</th>{isKT && <th></th>}</tr></thead>
      <tbody>{periods.map((p) => <tr key={p.period}><td><b>{p.period}</b></td><td>{p.locked ? <Tag cls="navy">Đã khóa</Tag> : <Tag cls="ok">Mở</Tag>}</td><td>{p.locked_by}</td><td>{fmtDT(p.locked_at)}</td><td className="muted">{p.note}</td>
        {isKT && <td>{!p.locked && <button className="act orange" style={{ margin: 0 }} onClick={() => { const n = prompt(`Khóa kỳ ${p.period}? Ghi chú:`); if (n !== null) post(`/periods/${p.period}/lock`, { note: n }); }}>Khóa kỳ</button>}</td>}</tr>)}</tbody></table></div>}
  </>);
}
export default function Page() { return <Shell><Accounting /></Shell>; }
