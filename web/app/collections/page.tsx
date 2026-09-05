"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const ST: Record<string, [string, string]> = {
  da_khop: ["Đã khớp", "ok"], cho_ke_toan: ["Chờ Kế toán", "warn"], chua_khop: ["Chưa khớp", ""], bo_qua: ["Bỏ qua", ""],
  tu_dong: ["Robot tự động", "warn"], ke_toan_xac_nhan: ["KT xác nhận", "ok"], huy: ["Hủy", "red"],
};
const S = (s: string) => <Tag cls={ST[s]?.[1] || ""}>{ST[s]?.[0] || s}</Tag>;

function Collections() {
  const { user, toast } = useShell();
  const isKT = ["ketoan", "cntt"].includes(user?.role || "");
  const [sum, setSum] = useState<any>(null);
  const [txns, setTxns] = useState<any[]>([]);
  const [rcs, setRcs] = useState<any[]>([]);
  const [filter, setFilter] = useState("cho_ke_toan");
  const [assign, setAssign] = useState<Record<number, { booking_id: string; note: string }>>({});
  const [cash, setCash] = useState({ booking_id: "", amount: "", payer: "", note: "" });
  const [sp, setSp] = useState<any>(null);
  const [pull, setPull] = useState({ from_date: new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10), to_date: new Date().toISOString().slice(0, 10) });
  const [pulling, setPulling] = useState(false);
  const loadSp = useCallback(() => { if (["ketoan", "cntt", "tgd", "chutich", "bks"].includes(user?.role || "")) api("/sepay/status").then(setSp).catch(() => setSp(null)); }, [user]);
  useEffect(() => { loadSp(); }, [loadSp]);
  const load = useCallback(() => Promise.all([api("/collections/summary").then(setSum), api(`/bank-transactions${filter ? `?status=${filter}` : ""}`).then(setTxns), api("/receipts").then(setRcs)]), [filter]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); } catch (x) { toast(errMsg(x), true); } };
  const dueRows = (sum?.bookings || []).filter((b: any) => b.due > 0);
  return (<>
    <h1>Thu tiền – robot R1 (SePay) &amp; phiếu thu</h1>
    <p className="muted">Robot chỉ tự sinh phiếu thu khi khớp <b>tuyệt đối</b> mã booking + số tiền còn phải thu. Mọi trường hợp khác treo chờ Kế toán quyết định. Giao dịch ngân hàng là bản ghi bất biến.</p>
    <div className="kpis">
      <div className="kpi"><b>{sum ? vnd(dueRows.reduce((a: number, b: any) => a + b.due, 0)) : "…"}</b><span>Còn phải thu (đ)</span></div>
      <div className="kpi"><b>{dueRows.length}</b><span>Booking chưa thu đủ</span></div>
      <div className="kpi"><b style={{ color: sum?.pending_txns ? "var(--orange)" : undefined }}>{sum?.pending_txns ?? "…"}</b><span>Giao dịch chờ Kế toán</span></div>
      <div className="kpi"><b>{sum?.pending_receipts ?? "…"}</b><span>Phiếu thu robot chờ xác nhận</span></div>
    </div>

    {sp && <><h2>Kết nối SePay</h2>
      <div className="panel"><div className="grid">
        <div><b>Webhook (SePay đẩy về)</b><div>{sp.webhook_key_set ? <Tag cls="ok">Đã đặt khóa</Tag> : <Tag cls="red">Chưa đặt SEPAY_WEBHOOK_KEY</Tag>}</div><div className="muted">URL: https://vtos-api.onrender.com{sp.webhook_url} · Xác thực: Api Key</div></div>
        <div><b>User API (VTOS kéo về)</b><div>{sp.api_token_set ? (sp.error ? <Tag cls="red">Lỗi: {sp.error}</Tag> : <Tag cls="ok">Đã kết nối</Tag>) : <Tag cls="warn">Chưa đặt SEPAY_API_TOKEN</Tag>}</div>
          <div className="muted">{sp.accounts?.length ? sp.accounts.map((a: any) => `${a.bank} ${a.account_number} (${a.holder})`).join(" · ") : "my.sepay.vn → Cấu hình → API Access → tạo token → Render → Environment"}</div></div>
        <div><b>Giao dịch đã nhận</b><div>{sp.transactions}</div><div className="muted">{sp.last_transaction ? `Gần nhất ${fmtDT(sp.last_transaction.date)} · ${vnd(sp.last_transaction.amount)} · ${sp.last_transaction.content}` : "Chưa có giao dịch"}</div></div>
      </div>
      {isKT && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <label>Từ <input type="date" value={pull.from_date} onChange={(e) => setPull({ ...pull, from_date: e.target.value })} /></label>
        <label>Đến <input type="date" value={pull.to_date} onChange={(e) => setPull({ ...pull, to_date: e.target.value })} /></label>
        <button className="act" style={{ margin: 0 }} disabled={pulling || !sp.api_token_set} onClick={async () => { setPulling(true); try { const r = await api("/sepay/pull", { method: "POST", json: pull }); toast(r.message); load(); loadSp(); } catch (x) { toast(errMsg(x), true); } setPulling(false); }}>{pulling ? "Đang kéo…" : "Kéo giao dịch từ SePay"}</button>
        <span className="muted">Kéo lại lịch sử khi mới kết nối hoặc webhook lỗi – không nhân bản giao dịch.</span></div>}
      </div></>}

    <h2>Giao dịch ngân hàng (SePay)</h2>
    <div>{[["cho_ke_toan", "Chờ Kế toán"], ["da_khop", "Đã khớp"], ["bo_qua", "Bỏ qua"], ["", "Tất cả"]].map(([v, l]) => <button key={v} className={"act " + (filter === v ? "" : "grey")} onClick={() => setFilter(v)}>{l}</button>)}</div>
    <div className="panel wrap"><table><thead><tr><th>Ngày</th><th>Ngân hàng</th><th>Loại</th><th>Số tiền</th><th>Nội dung CK</th><th>Kết quả robot</th><th>Ghi chú</th>{isKT && <th>Kế toán xử lý</th>}</tr></thead>
      <tbody>{txns.length ? txns.map((t) => <tr key={t.id}><td>{fmtDT(t.transaction_date)}</td><td>{t.gateway}</td><td>{t.transfer_type === "in" ? "Vào" : "Ra"}</td><td style={{ textAlign: "right" }}>{vnd(t.amount)}</td><td>{t.content}</td><td>{S(t.match_status)}{t.booking_code && <> <b>{t.booking_code}</b></>}</td><td className="muted">{t.match_note}</td>
        {isKT && <td>{t.match_status === "cho_ke_toan" && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          <select value={assign[t.id]?.booking_id ?? (t.booking_id || "")} onChange={(e) => setAssign({ ...assign, [t.id]: { booking_id: e.target.value, note: assign[t.id]?.note || "" } })}>
            <option value="">– chọn booking –</option>{(sum?.bookings || []).map((b: any) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · còn {vnd(b.due)}</option>)}</select>
          <input placeholder="Ghi chú (cọc đợt 1…)" value={assign[t.id]?.note || ""} onChange={(e) => setAssign({ ...assign, [t.id]: { booking_id: assign[t.id]?.booking_id ?? (t.booking_id || ""), note: e.target.value } })} />
          <button className="act teal" style={{ margin: 0 }} disabled={!(assign[t.id]?.booking_id ?? t.booking_id)} onClick={() => post(`/bank-transactions/${t.id}/assign`, { booking_id: Number(assign[t.id]?.booking_id ?? t.booking_id), note: assign[t.id]?.note || "" })}>Gán &amp; lập phiếu thu</button>
          <button className="act grey" style={{ margin: 0 }} onClick={() => { const n = prompt("Lý do bỏ qua giao dịch này?"); if (n !== null) post(`/bank-transactions/${t.id}/ignore`, { note: n }); }}>Bỏ qua</button>
        </div>}</td>}</tr>) : <tr><td colSpan={8} className="muted">Không có giao dịch.</td></tr>}</tbody></table></div>

    <h2>Phiếu thu (mẫu 01-TT)</h2>
    <div className="panel wrap"><table><thead><tr><th>Số PT</th><th>Booking</th><th>Tour</th><th>Người nộp</th><th>Số tiền</th><th>Hình thức</th><th>Trạng thái</th><th>Lập bởi</th><th>Lúc</th>{isKT && <th></th>}</tr></thead>
      <tbody>{rcs.length ? rcs.map((r) => <tr key={r.id}><td><b>{r.code}</b></td><td>{r.booking_code}<div className="muted">{r.customer_name}</div></td><td>{r.tour_code}</td><td>{r.payer}</td><td style={{ textAlign: "right" }}>{vnd(r.amount)}</td><td>{r.method === "tien_mat" ? "Tiền mặt" : "Chuyển khoản"}</td><td>{S(r.status)}</td><td className="muted">{r.created_by}{r.confirmed_by && ` → ${r.confirmed_by}`}</td><td>{fmtDT(r.created_at)}</td>
        {isKT && <td>{r.status === "tu_dong" && user?.role === "ketoan" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/receipts/${r.id}/confirm`)}>Xác nhận</button>}</td>}</tr>) : <tr><td colSpan={10} className="muted">Chưa có phiếu thu.</td></tr>}</tbody></table></div>

    {user?.role === "ketoan" && <><h2>Lập phiếu thu tiền mặt</h2>
      <div className="panel"><div className="grid">
        <label>Booking<select value={cash.booking_id} onChange={(e) => setCash({ ...cash, booking_id: e.target.value })}><option value="">– chọn –</option>{dueRows.map((b: any) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · còn {vnd(b.due)}</option>)}</select></label>
        <label>Số tiền (đ)<input type="number" value={cash.amount} onChange={(e) => setCash({ ...cash, amount: e.target.value })} /></label>
        <label>Người nộp<input value={cash.payer} onChange={(e) => setCash({ ...cash, payer: e.target.value })} /></label>
        <label>Ghi chú<input value={cash.note} onChange={(e) => setCash({ ...cash, note: e.target.value })} /></label>
      </div><button className="act" disabled={!cash.booking_id || !cash.amount} onClick={() => post("/receipts/cash", { booking_id: Number(cash.booking_id), amount: Number(cash.amount), payer: cash.payer, note: cash.note }).then(() => setCash({ booking_id: "", amount: "", payer: "", note: "" }))}>Lập phiếu thu</button></div></>}

    <h2>Công nợ phải thu theo booking</h2>
    <div className="panel wrap"><table><thead><tr><th>Booking</th><th>Tour</th><th>Khách</th><th>Phải thu</th><th>Đã thu</th><th>Còn lại</th></tr></thead>
      <tbody>{(sum?.bookings || []).map((b: any) => <tr key={b.booking_id} style={{ opacity: b.due > 0 ? 1 : 0.55 }}><td><b>{b.code}</b></td><td>{b.tour_code}</td><td>{b.customer_name}</td><td style={{ textAlign: "right" }}>{vnd(b.total)}</td><td style={{ textAlign: "right" }}>{vnd(b.paid)}</td><td style={{ textAlign: "right" }}>{b.due > 0 ? <Tag cls="warn">{vnd(b.due)}</Tag> : <Tag cls="ok">Đủ</Tag>}</td></tr>)}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Collections /></Shell>; }
