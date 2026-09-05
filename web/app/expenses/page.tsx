"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const CAT: Record<string, string> = { chi_tour: "Chi phí tour", marketing: "Marketing", hanh_chinh: "Hành chính", hoan_tien: "Hoàn tiền khách", tam_ung: "Tạm ứng HDV/NCC trước tour" };
const ST: Record<string, [string, string]> = { cho_tp: ["Chờ bộ phận", "warn"], cho_kt: ["Chờ Kế toán", "warn"], cho_duyet: ["Chờ duyệt", "warn"], cho_chi: ["Lệnh chi chờ", "navy"], da_chi: ["Đã chi", "ok"], tu_choi: ["Từ chối", "red"] };
const CONFIRMER: Record<string, string[]> = { chi_tour: ["tp_dh", "tgd"], marketing: ["ptgd_mkt", "tgd"], hanh_chinh: ["hcns", "tgd"], hoan_tien: ["gd_kd", "tp_dh", "tgd"], tam_ung: ["tp_dh", "tgd"] };

function Expenses() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [tab, setTab] = useState("requests");
  const [filter, setFilter] = useState("cho_tp,cho_kt,cho_duyet,cho_chi");
  const [rows, setRows] = useState<any[]>([]);
  const [cf, setCf] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [f, setF] = useState<any>({ category: "chi_tour", tour_id: "", supplier_name: "", supplier_tax_code: "", supplier_bank: "", amount: "", description: "", has_document: false, document_ref: "", has_invoice: false });
  const load = useCallback(() => {
    if (!tours.length) api("/tours").then(setTours).catch(() => {});
    if (tab === "requests") api(`/payment-requests${filter ? `?status=${filter}` : ""}`).then(setRows);
    if (tab === "cashflow") api("/cashflow").then(setCf).catch((e) => toast(errMsg(e), true));
  }, [tab, filter]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const step = (r: any, action: string, reason = "") => post(`/payment-requests/${r.id}/step`, { action, reason });
  const canCreate = ["nv_dh", "tp_dh", "ptgd_mkt", "hcns", "cntt", "gd_kd", "nv_kd"].includes(role);
  const actions = (r: any) => {
    const out: any[] = [];
    if (r.status === "cho_tp" && CONFIRMER[r.category]?.includes(role)) out.push(["Xác nhận", "confirm", "teal"]);
    if (r.status === "cho_kt" && role === "ketoan") out.push(["Kế toán kiểm tra", "check", "teal"]);
    if (r.status === "cho_duyet" && (role === "tgd" || (role === "chutich" && r.two_signatures))) out.push([role === "tgd" ? "TGĐ duyệt" : "Chủ tịch ký", "approve", ""]);
    if (r.status === "cho_chi" && role === "ketoan") out.push(["Đã chi (nhập mã GD)", "pay", "orange"]);
    if (!["da_chi", "tu_choi"].includes(r.status) && ["tgd", "chutich", "ketoan", "tp_dh", "ptgd_mkt"].includes(role)) out.push(["Từ chối", "reject", "grey"]);
    return out;
  };

  return (<>
    <h1>Đề nghị chi – Lệnh chi (robot R3) &amp; dòng tiền tour</h1>
    <p className="muted">Đề nghị chi bắt buộc mã tour (chi phí tour), NCC có MST, chứng từ đính kèm. Robot xếp cấp duyệt: chi ngoài dự toán tour hoặc Marketing ≥ hạn mức → <b>Chủ tịch + TGĐ</b> (cổng 15). Luồng: bộ phận xác nhận → Kế toán kiểm tra → TGĐ duyệt → lệnh chi chờ → Kế toán chi trên ngân hàng (SePay tiền ra có mã DC… tự khớp). Duyệt → Nợ 154/641/642 – Có 331; chi → Nợ 331 – Có 112.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["requests", "Đề nghị chi"], ["cashflow", "Dòng tiền tour"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "requests" && <>
      {canCreate && <div className="panel"><h2>Lập đề nghị chi (mẫu 05-TT)</h2><div className="grid">
        <label>Loại<select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>{Object.entries(CAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Tour (bắt buộc với chi tour/hoàn tiền)<select value={f.tour_id} onChange={(e) => setF({ ...f, tour_id: e.target.value })}><option value="">–</option>{tours.map((t) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>NCC / người thụ hưởng<input value={f.supplier_name} onChange={(e) => setF({ ...f, supplier_name: e.target.value })} /></label>
        <label>MST NCC<input value={f.supplier_tax_code} onChange={(e) => setF({ ...f, supplier_tax_code: e.target.value })} /></label>
        <label>Tài khoản thụ hưởng<input value={f.supplier_bank} onChange={(e) => setF({ ...f, supplier_bank: e.target.value })} placeholder="số TK – ngân hàng" /></label>
        <label>Số tiền (đ)<input type="number" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} /></label>
        <label>Nội dung<input value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
        <label>Chứng từ đính kèm (số HĐ/HĐơn/báo giá)<input value={f.document_ref} onChange={(e) => setF({ ...f, document_ref: e.target.value, has_document: !!e.target.value })} /></label>
        <label><input type="checkbox" checked={f.has_invoice} onChange={(e) => setF({ ...f, has_invoice: e.target.checked })} /> Có hóa đơn GTGT (không có → không được trừ TNDN)</label>
      </div><button className="act" disabled={!f.supplier_name || !f.amount || !f.description} onClick={() => post("/payment-requests", { ...f, tour_id: f.tour_id ? Number(f.tour_id) : null, amount: Number(f.amount) }).then((r) => r && setF({ ...f, supplier_name: "", amount: "", description: "", document_ref: "", has_document: false }))}>Lập đề nghị</button></div>}
      <div>{[["cho_tp,cho_kt,cho_duyet,cho_chi", "Đang xử lý"], ["cho_chi", "Lệnh chi chờ"], ["da_chi", "Đã chi"], ["tu_choi", "Từ chối"], ["", "Tất cả"]].map(([v, l]) => <button key={v} className={"act " + (filter === v ? "" : "grey")} onClick={() => setFilter(v)}>{l}</button>)}</div>
      <div className="panel wrap"><table><thead><tr><th>Số ĐN</th><th>Loại / Tour</th><th>NCC</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Nội dung</th><th>Cờ R3</th><th>Trạng thái → bước tiếp</th><th>Người</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td><b>{r.code}</b><div className="muted">{fmtDT(r.created_at)}</div></td><td>{CAT[r.category]}<div className="muted">{r.tour_code}</div></td><td>{r.supplier_name}<div className="muted">{r.supplier_tax_code || <Tag cls="warn">chưa MST</Tag>}</div></td><td style={{ textAlign: "right" }}><b>{vnd(r.amount)}</b></td><td>{r.description}<div className="muted">{r.document_ref || <Tag cls="warn">thiếu chứng từ</Tag>}{!r.has_invoice && !["hoan_tien", "tam_ung"].includes(r.category) && <Tag cls="warn">không HĐ</Tag>}</div></td>
          <td>{r.over_budget && <Tag cls="red">Ngoài dự toán</Tag>}{r.two_signatures && <Tag cls="navy">2 chữ ký</Tag>}</td><td><Tag cls={ST[r.status]?.[1]}>{ST[r.status]?.[0]}</Tag><div className="muted">{r.next}{r.two_signatures && r.status === "cho_duyet" && ` (CT ${r.signed_chutich ? "✔" : "…"} · TGĐ ${r.signed_tgd ? "✔" : "…"})`}{r.reject_reason && ` – ${r.reject_reason}`}{r.paid_ref && ` – ${r.paid_ref}`}</div></td>
          <td className="muted">{r.created_by}{r.tp_by && ` → ${r.tp_by}`}{r.kt_by && ` → ${r.kt_by}`}{r.approved_by && ` → ${r.approved_by}`}</td>
          <td>{actions(r).map(([l, a, c]) => <button key={a} className={"act " + c} style={{ margin: "0 4px 4px 0" }} onClick={() => { let reason = ""; if (a === "reject") { reason = prompt("Lý do từ chối (bắt buộc):") || ""; if (!reason) return; } if (a === "pay") { reason = prompt("Mã giao dịch ngân hàng (hoặc 'TM' nếu tiền mặt):") || ""; } step(r, a, reason); }}>{l}</button>)}</td></tr>) : <tr><td colSpan={9} className="muted">Không có đề nghị chi.</td></tr>}</tbody></table></div>
    </>}

    {tab === "cashflow" && <div className="panel wrap"><table><thead><tr><th>Tour</th><th>Trạng thái</th><th style={{ textAlign: "right" }}>Doanh thu booking</th><th style={{ textAlign: "right" }}>Đã thu</th><th style={{ textAlign: "right" }}>Đã chi</th><th style={{ textAlign: "right" }}>Lệnh chi chờ</th><th style={{ textAlign: "right" }}>Đang trình</th><th style={{ textAlign: "right" }}>Tiền còn lại</th><th style={{ textAlign: "right" }}>Dự toán chi</th><th style={{ textAlign: "right" }}>LN dự kiến</th><th>Cảnh báo</th></tr></thead>
      <tbody>{cf.map((c) => <tr key={c.tour_id}><td><b>{c.code}</b><div className="muted">{c.name}</div></td><td className="muted">{c.status}</td><td style={{ textAlign: "right" }}>{vnd(c.revenue)}</td><td style={{ textAlign: "right" }}>{vnd(c.collected)}</td><td style={{ textAlign: "right" }}>{vnd(c.paid)}</td><td style={{ textAlign: "right" }}>{vnd(c.committed)}</td><td style={{ textAlign: "right" }}>{vnd(c.pending)}</td><td style={{ textAlign: "right" }}><b style={{ color: c.cash_left < 0 ? "var(--red)" : undefined }}>{vnd(c.cash_left)}</b></td><td style={{ textAlign: "right" }}>{vnd(c.budget)}</td><td style={{ textAlign: "right" }}>{vnd(c.expected_profit)}</td>
        <td>{c.red && <Tag cls="red">Chi vượt thu</Tag>}{c.over_budget && <Tag cls="warn">Vượt dự toán</Tag>}</td></tr>)}</tbody></table>
      <p className="muted">Bảng dòng tiền tour tự động (R3): cảnh báo đỏ khi chi + lệnh chi chờ vượt tiền đã thu. Mọi cấp duyệt xem bảng này trước khi duyệt đề nghị chi.</p></div>}
  </>);
}
export default function Page() { return <Shell><Expenses /></Shell>; }
