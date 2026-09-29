"use client";
import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, pct, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg, MangTag } from "@/components/ui";

/** Số dòng chi tiết in ra màn hình. Máy chủ vẫn trả đủ, và Xuất Excel vẫn ra đủ — đây chỉ là mức
 *  mà TRÌNH DUYỆT chịu được. Ngày 29/9/2026 báo cáo "bán tour lẻ" kỳ 01–29/9 mảng Lẻ ra 6.682 dòng
 *  chi tiết; trang dựng hết ngần ấy thẻ <tr> thành ~900 KB văn bản trong một màn hình, máy cấu hình
 *  thấp ở chi nhánh mở là đứng. Mảng Đoàn chỉ 85 dòng nên suốt thời gian qua không ai gặp.
 *  Bảng tổng hợp KHÔNG cắt: nó xếp theo sale nên số dòng bằng số người, luôn đọc hết được. */
const CT_TOI_DA = 300;
const PCT_KEYS = new Set(["margin", "pct_moc", "rate"]);
const DATE_KEYS = new Set(["created_at", "cancelled_at", "deadline", "start_date", "end_date"]);
function cell(k: string, v: any) {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "✓" : "";
  if (PCT_KEYS.has(k)) return pct(v);
  if (DATE_KEYS.has(k)) return String(v).length > 10 ? fmtDT(v) : fmtD(v);
  if (k === "status") return <Tag cls={v === "PAID" ? "ok" : v === "DEPO" ? "warn" : v === "CANCEL" ? "" : "red"}>{v}</Tag>;
  if (typeof v === "number") return vnd(v);
  return String(v);
}

function SalesReports() {
  const { toast } = useShell();
  const [list, setList] = useState<any[]>([]); const [key, setKey] = useState("ban_tour_le");
  const today = new Date().toISOString().slice(0, 10);
  const [from, setFrom] = useState(today.slice(0, 8) + "01"); const [to, setTo] = useState(today); const [month, setMonth] = useState(today.slice(0, 7));
  const [rep, setRep] = useState<any>(null); const [busy, setBusy] = useState(false);
  // Mảng lấy từ đường dẫn (menu phòng Lẻ / phòng Đoàn trỏ vào ?mang=le / ?mang=doan). Next chỉ đổi query chứ
  // không dựng lại trang khi chuyển giữa hai menu, nên `mang` phải nằm trong phụ thuộc của useCallback.
  const mang = useSearchParams().get("mang") || "";
  useEffect(() => { api("/sales-reports").then(setList).catch(() => {}); }, []);
  const qs = `from=${from}&to=${to}&month=${month}&mang=${mang}`;
  const run = useCallback(async () => { setBusy(true); try { setRep(await api(`/sales-reports/${key}?${qs}`)); } catch (e) { setRep(null); toast(errMsg(e), true); } setBusy(false); }, [key, qs, toast]);
  useEffect(() => { run(); }, [run]);
  const xlsx = async () => { try { const r = await fetch(`/api/v1/sales-reports/${key}/xlsx?${qs}`, { headers: { Authorization: `Bearer ${getToken() || ""}` } }); if (!r.ok) throw new Error("Không xuất được"); const u = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = u; a.download = `VTOS_${key}_${mang || "toanhethong"}_${month}.xlsx`; a.click(); } catch (e: any) { toast(e.message, true); } };
  const meta = list.find((x) => x.key === key) || {}; const P: string[] = meta.params || [];
  const T = rep?.total || {};
  return (<>
    <h1>Báo cáo bán hàng{mang ? ` – ${mang === "doan" ? "Kinh doanh Đoàn (MICE)" : "Kinh doanh Lẻ"}` : ""}</h1>
    <p className="muted">Danh mục như Vietrip (Báo cáo › Tour lẻ / Điều hành): chọn báo cáo, kỳ, chạy và xuất Excel. Sale chỉ thấy số liệu của mình; Ban Giám đốc, Kế toán, BKS thấy toàn bộ.</p>
    <MangTag mang={mang} />
    <div className="grid">
      <div className="panel"><h2>Danh sách báo cáo</h2>
        <table><thead><tr><th>Tên báo cáo</th><th>Loại</th></tr></thead><tbody>{list.map((x) => <tr key={x.key} onClick={() => setKey(x.key)} style={{ cursor: "pointer", background: x.key === key ? "var(--panel2, rgba(255,255,255,.06))" : undefined }}><td><b>{x.name}</b><div className="muted">{x.desc}</div></td><td>{x.kind}</td></tr>)}</tbody></table></div>
      <div className="panel"><h2>Thông số báo cáo</h2>
        {P.includes("from") && <div className="grid"><div><label>Từ ngày</label><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></div><div><label>Đến ngày</label><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></div></div>}
        {P.includes("month") && <label>Tháng<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></label>}
        {P.length === 0 && <p className="muted">Báo cáo tính đến thời điểm hiện tại.</p>}
        <button className="act teal" onClick={run} disabled={busy}>{busy ? "Đang chạy…" : "Chạy báo cáo"}</button> <button className="act grey" onClick={xlsx}>Xuất Excel</button>
        {rep && <div className="kpis" style={{ marginTop: 8 }}>{Object.entries(T).map(([k, v]: any) => <div className="kpi" key={k}><b>{typeof v === "number" ? vnd(v) : String(v)}</b><span>{k}</span></div>)}</div>}
        {rep?.note && <p className="muted">{rep.note}</p>}
      </div>
    </div>
    {rep && <div className="panel wrap"><h2>{meta.name} – tổng hợp ({rep.summary.length})</h2>
      <table><thead><tr>{rep.columns.summary.map((c: any) => <th key={c[0]} className={["sale", "office", "f", "status", "tour_code", "name", "operator"].includes(c[0]) ? "" : "num"}>{c[1]}</th>)}</tr></thead>
        <tbody>{rep.summary.length ? rep.summary.map((r: any, i: number) => <tr key={i}>{rep.columns.summary.map((c: any) => <td key={c[0]} className={typeof r[c[0]] === "number" ? "num" : ""}>{cell(c[0], r[c[0]])}</td>)}</tr>) : <tr><td colSpan={rep.columns.summary.length} className="muted">Không có dữ liệu trong kỳ.</td></tr>}</tbody></table></div>}
    {rep && rep.detail?.length > 0 && <div className="panel wrap"><h2>Chi tiết ({rep.detail.length})</h2>
      {rep.detail.length > CT_TOI_DA && <p className="muted">Đang hiện {CT_TOI_DA} dòng đầu trong tổng số <b>{rep.detail.length}</b>. Thu hẹp khoảng ngày để xem phần còn lại, hoặc bấm <b>Xuất Excel</b> – tệp Excel lấy thẳng từ máy chủ nên vẫn đủ cả {rep.detail.length} dòng.</p>}
      <table><thead><tr>{rep.columns.detail.map((c: any) => <th key={c[0]}>{c[1]}</th>)}</tr></thead>
        <tbody>{rep.detail.slice(0, CT_TOI_DA).map((r: any, i: number) => <tr key={i} style={{ opacity: r.cancelled ? 0.55 : 1, color: r.overdue || r.late ? "var(--red)" : undefined }}>{rep.columns.detail.map((c: any) => <td key={c[0]} className={typeof r[c[0]] === "number" ? "num" : ""}>{cell(c[0], r[c[0]])}</td>)}</tr>)}</tbody></table></div>}
  </>);
}

export default function Page() { return <Shell><Suspense><SalesReports /></Suspense></Shell>; }
