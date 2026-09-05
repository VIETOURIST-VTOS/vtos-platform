"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT } from "@/lib/api";
import { ROLES, TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, Gate, errMsg } from "@/components/ui";

const TABS: [string, string][] = [["info", "Thông tin & quy trình"], ["budget", "Dự toán 3 con số"], ["bookings", "Booking & thu tiền"], ["cost", "Chi NCC & quyết toán"], ["ops", "HDV & xe"], ["history", "Quy trình & lịch sử"]];
const PR_ST: Record<string, string> = { cho_tp: "Chờ TP", cho_kt: "Chờ Kế toán", cho_duyet: "Chờ duyệt", cho_chi: "Chờ chi", da_chi: "Đã chi", tu_choi: "Từ chối", huy: "Hủy" };

function TourDetail() {
  const { id } = useParams<{ id: string }>();
  const { user, toast } = useShell();
  const [t, setT] = useState<any>(null);
  const [tab, setTab] = useState("info");
  const [note, setNote] = useState("");
  const load = useCallback(() => api(`/tours/${id}/detail`).then(setT).catch((e) => toast(errMsg(e), true)), [id, toast]);
  useEffect(() => { load(); }, [load]);
  if (!t) return <p className="muted">Đang tải…</p>;
  const c = t.calc, s = t.settlement, act: string[] = t.actions || [], sm = t.summary || {};
  const can = (a: string) => act.includes(a);
  const run = async (path: string, json?: any) => { try { const r = await api(`/tours/${t.id}/${path}`, { method: "POST", json: { note, ...(json || {}) } }); toast(r.message); setNote(""); load(); } catch (e) { toast(errMsg(e), true); } };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    ["price_per_pax", "fixed_cost", "var_cost_per_pax", "planned_pax"].forEach((k) => (d[k] = Number(d[k] || 0)));
    try { await api(`/tours/${t.id}`, { method: "PUT", json: d }); toast("Đã lưu dự toán"); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const closeTour = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    run("close", { actual_revenue: Number(d.actual_revenue), actual_cost: Number(d.actual_cost), promo_value: Number(d.promo_value || 0) });
  };
  const bookedAmount = sm.revenue_booking || 0;
  const NoteBox = () => <label>Lời giải trình / ghi chú cho bước này (hiển thị ở Quy trình & lịch sử)<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="VD: khách ít nên biên thấp, nhờ anh duyệt…" /></label>;
  return (<>
    <p><Link href="/tours">← Danh sách tour</Link>{t.product && <> · Sản phẩm <Link href="/products">{t.product.code}</Link></>}</p>
    <h1>{t.code} · {t.name} <Tag cls="navy">{TOUR_TYPES[t.tour_type]}</Tag> {t.below_margin && <Tag cls="warn">dưới biên</Tag>} {t.imported && <Tag>Vietrip</Tag>}</h1>
    <p className="muted">{fmtD(t.start_date)} → {fmtD(t.end_date)} · {t.days || ""} ngày · {t.transport} {t.vehicle_type} · KH {t.departure_point} · Điều hành <b>{t.operator_name}</b> · Trạng thái <b>{TOUR_STATUS[t.status]}</b> · Hạn quyết toán <b>{fmtD(t.settlement_deadline)}</b></p>
    <div className="kpis">
      <div className="kpi"><b>{t.seats.booked}/{t.seats.open || t.planned_pax}</b><span>Đã bán / mở bán · còn {t.seats.left}</span></div>
      <div className="kpi"><b>{vnd(bookedAmount)}</b><span>Doanh thu booking</span></div>
      <div className="kpi"><b>{vnd(sm.collected)}</b><span>Đã thu</span></div>
      <div className="kpi"><b>{vnd(sm.cost_actual)}</b><span>Chi phí thực tế (quyết toán)</span></div>
      <div className="kpi"><b style={{ color: sm.profit < 0 ? "var(--red)" : undefined }}>{vnd(sm.profit)}</b><span>Lợi nhuận ước</span></div>
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "info" && <div className="grid">
      <div className="panel"><h2>Thông tin tour</h2>
        <table><tbody>
          <tr><td>Mã tour / sản phẩm</td><td><b>{t.code}</b> · {t.product_code || "–"}</td></tr>
          <tr><td>Khởi hành – kết thúc</td><td>{fmtD(t.start_date)} – {fmtD(t.end_date)}</td></tr>
          <tr><td>Số chỗ mở bán / khuyến mãi</td><td>{t.seats.open} / {t.seats.promo}</td></tr>
          <tr><td>Giá ADL / CHD / INF / KM</td><td>{vnd(t.prices.adl)} / {vnd(t.prices.chd)} / {vnd(t.prices.inf)} / {vnd(t.prices.promo)}</td></tr>
          <tr><td>Người điều hành duy nhất</td><td>{t.operator_name}</td></tr>
          <tr><td>Điểm dừng nghỉ</td><td>{t.rest_stops || "–"}</td></tr>
          <tr><td>Duyệt</td><td>{t.confirmed_by && `TP ĐH: ${t.confirmed_by}`} {t.approved_by && `· ${t.approved_by}`} {t.chairman_run_decision}</td></tr>
        </tbody></table>
        {t.product?.program && <details><summary>Chương trình tour (từ sản phẩm)</summary><pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{t.product.program}</pre></details>}
      </div>
      <div className="panel"><h2>Luồng phê duyệt</h2>
        {t.status === "nhap" && (can("edit") ? <p className="muted">Sửa dự toán ở tab <b>Dự toán 3 con số</b> rồi bấm Trình.</p> : <p className="muted">Chỉ người điều hành chuyến ({t.operator_name}) hoặc TP Điều hành sửa được dự toán.</p>)}
        {t.status === "nhap" && can("submit") && <><NoteBox /><button className="act teal" onClick={() => run("submit")}>Trình Trưởng phòng Điều hành</button></>}
        {t.status === "cho_xac_nhan" && <><p>Chờ Trưởng phòng Điều hành xác nhận.</p>{can("confirm") && <><NoteBox /><button className="act teal" onClick={() => run("confirm")}>Xác nhận dự toán</button></>}</>}
        {t.status === "cho_duyet" && (t.below_margin ? <>
          <p>Chuyến dưới biên – cần đủ 2 chữ ký: Chủ tịch {t.signed_chutich ? "✔" : "…"} · TGĐ {t.signed_tgd ? "✔" : "…"}</p>
          <div className="gate"><b>Giải trình:</b> {t.justification}</div>
          {can("sign") && <><NoteBox /><button className="act orange" onClick={() => run("approve")}>Ký duyệt ({user?.role_name})</button></>}
        </> : <><p>Chờ <b>{ROLES[t.approver_role]}</b> duyệt.</p>{can("approve") && <><NoteBox /><button className="act teal" onClick={() => run("approve")}>Duyệt dự toán</button></>}</>)}
        {t.status === "da_duyet" && <p>Đã duyệt. Kinh doanh gửi yêu cầu, Điều hành tạo booking tại <Link href="/requests">Yêu cầu & booking</Link>.</p>}
        {t.d7_flag && <>
          <Gate ok={false}>CỔNG 8 – Mốc D-7: {t.booked_pax}/{c.breakeven_pax} khách hòa vốn → ghép/dời/hủy; chạy tiếp cần Chủ tịch. {t.chairman_run_decision && <b>{t.chairman_run_decision}</b>}</Gate>
          {can("d7") && <><NoteBox /><button className="act grey" onClick={() => run("d7", { decision: "ghep" })}>Ghép</button><button className="act grey" onClick={() => run("d7", { decision: "doi" })}>Dời</button><button className="act red" onClick={() => run("d7", { decision: "huy" })}>Hủy</button>{user?.role === "chutich" && <button className="act orange" onClick={() => run("d7", { decision: "chay" })}>Chủ tịch duyệt chạy</button>}</>}
        </>}
        {t.status === "huy" && <p>{t.chairman_run_decision}</p>}
        {can("close") && <><h3>Đóng số quyết toán · một cửa · hạn {fmtD(t.settlement_deadline)} {new Date().toISOString().slice(0, 10) > t.settlement_deadline && <Tag cls="red">ĐÃ QUÁ HẠN</Tag>}</h3>
          <form onSubmit={closeTour}><div className="grid">
            <div><label>Doanh thu thực tế (đ)</label><input type="number" name="actual_revenue" step="1000" defaultValue={Math.round(t.actual_revenue || bookedAmount)} required /></div>
            <div><label>Giá vốn thực tế (đ)</label><input type="number" name="actual_cost" step="1000" defaultValue={Math.round(sm.cost_actual || t.fixed_cost + t.var_cost_per_pax * t.booked_pax)} required /></div>
            <div><label>Giảm giá / mã KM (đ)</label><input type="number" name="promo_value" step="1000" defaultValue={0} /></div>
          </div><NoteBox /><button className="act teal">Đóng số → Kế toán</button></form></>}
        {can("kt_confirm") && <><NoteBox /><button className="act teal" onClick={() => run("kt-confirm")}>Kế toán xác nhận (3 ngày làm việc)</button></>}
        {can("cntt_check") && <><NoteBox /><button className="act teal" onClick={() => run("cntt-check")}>CNTT đối chiếu độc lập & khóa</button></>}
        {s && <><h3>Quyết toán và quỹ thưởng</h3><table><tbody>
          <tr><td>Doanh thu thực tế</td><td className="num">{vnd(s.revenue)}</td><td>Đóng số</td><td>{fmtDT(t.closed_at)} · {s.on_time ? "đúng hạn" : <b>QUÁ HẠN</b>}</td></tr>
          <tr><td>Giá vốn thực tế</td><td className="num">{vnd(s.cost)}</td><td>Kế toán xác nhận</td><td>{fmtDT(t.kt_confirmed_at)}</td></tr>
          <tr><td>Lợi nhuận / biên</td><td className="num"><b>{vnd(s.profit)} · {pct(s.margin)}</b></td><td>CNTT khóa</td><td>{fmtDT(t.cntt_checked_at)}</td></tr>
          <tr><td>Quỹ thưởng Điều hành ({pct(s.rate)})</td><td className="num"><b>{vnd(s.fund)}</b></td><td>NV 70% / TP 30%</td><td className="num">{vnd(s.fund_nv)} / {vnd(s.fund_tp)}</td></tr>
        </tbody></table>{!s.eligible && <Gate ok={false}>Không phát sinh quỹ thưởng: {!s.on_time ? "quá hạn quyết toán" : t.below_margin ? "chuyến duyệt chạy dưới biên" : "biên thực tế dưới ngưỡng"}.</Gate>}</>}
      </div>
    </div>}

    {tab === "budget" && <div className="grid">
      <div className="panel"><h2>Ba con số dự toán (ĐH Điều 2, 11)</h2>
        <table><tbody>
          <tr><td>Số khách dự toán</td><td className="num"><b>{t.planned_pax}</b></td></tr>
          <tr><td>Số khách hòa vốn</td><td className="num"><b>{c.breakeven_pax ?? "–"}</b></td></tr>
          <tr><td>Số khách đạt biên {pct(c.threshold)}</td><td className="num"><b>{c.pax_for_margin ?? "–"}</b></td></tr>
          <tr><td>Doanh thu kế hoạch</td><td className="num">{vnd(c.revenue)}</td></tr>
          <tr><td>Giá vốn kế hoạch (cố định {vnd(t.fixed_cost)} + {vnd(t.var_cost_per_pax)}/khách)</td><td className="num">{vnd(c.cost)}</td></tr>
          <tr><td>Lợi nhuận / biên kế hoạch</td><td className="num">{vnd(c.profit)} · <b>{pct(c.margin)}</b></td></tr>
        </tbody></table>
        <Gate ok={c.pass_gate}>CỔNG 1 – Biên {pct(c.threshold)}: {c.pass_gate ? `ĐẠT → ${ROLES[t.approver_role]} duyệt` : "KHÔNG ĐẠT → giải trình + 2 chữ ký Chủ tịch và TGĐ"}</Gate>
        {t.product && <p className="muted">Cơ cấu chi phí sản phẩm {t.product.code}: cố định {vnd(t.product.fixed_cost)} · theo khách {vnd(t.product.var_cost_per_pax)} · giá tham khảo {vnd(t.product.reference_price)}</p>}
      </div>
      <div className="panel"><h2>Sửa dự toán</h2>
        {t.status === "nhap" && can("edit") ? <form onSubmit={saveEdit}>
          <div className="grid"><div><label>Giá bán/khách</label><input type="number" name="price_per_pax" defaultValue={t.price_per_pax} step="1000" /></div><div><label>Chi phí cố định</label><input type="number" name="fixed_cost" defaultValue={t.fixed_cost} step="1000" /></div>
            <div><label>Chi phí theo khách</label><input type="number" name="var_cost_per_pax" defaultValue={t.var_cost_per_pax} step="1000" /></div><div><label>Số khách dự toán</label><input type="number" name="planned_pax" defaultValue={t.planned_pax} /></div></div>
          <label>Điểm dừng nghỉ (bắt buộc)</label><input name="rest_stops" defaultValue={t.rest_stops} />
          <label>Giải trình chuyến dưới biên (4 mục) – bắt buộc khi biên &lt; {pct(c.threshold)}</label><textarea name="justification" defaultValue={t.justification} />
          <button className="act grey" type="submit">Lưu dự toán</button>
        </form> : <p className="muted">Dự toán đã trình – không sửa ({TOUR_STATUS[t.status]}).</p>}
      </div>
    </div>}

    {tab === "bookings" && <>
      <div className="panel wrap"><h2>Booking ({t.bookings.length}) · doanh thu {vnd(bookedAmount)} · đã thu {vnd(sm.collected)}</h2>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Nguồn</th><th className="num">ADL/CHD/INF</th><th className="num">Tiền</th><th className="num">Đã thu</th><th className="num">Còn lại</th><th>TT</th><th>Sale</th><th>Chỉ tiêu</th></tr></thead>
          <tbody>{t.bookings.length ? t.bookings.map((b: any) => <tr key={b.id} style={{ opacity: b.cancelled ? 0.5 : 1 }}><td>{b.code}{b.cancelled && <Tag cls="red">hủy</Tag>}</td><td>{b.customer_name} · {b.customer_phone}</td><td>{b.source}</td><td className="num">{b.adl}/{b.chd}/{b.inf}</td><td className="num">{vnd(b.amount - b.discount)}</td><td className="num">{vnd(b.paid)}</td><td className="num">{b.due > 0 ? <Tag cls="warn">{vnd(b.due)}</Tag> : <Tag cls="ok">Đủ</Tag>}</td><td>{b.pmt_status}</td><td>{b.sales_name}</td><td>{b.counts_for_target ? "có" : "không"}</td></tr>) : <tr><td colSpan={10} className="muted">Chưa có booking.</td></tr>}</tbody></table></div>
      <div className="panel wrap"><h2>Phiếu thu ({t.receipts.length})</h2>
        <table><thead><tr><th>Số PT</th><th>Booking</th><th className="num">Số tiền</th><th>Hình thức</th><th>Người nộp</th><th>Trạng thái</th><th>Lúc</th><th>Xác nhận</th></tr></thead>
          <tbody>{t.receipts.map((r: any) => <tr key={r.id}><td>{r.code}</td><td>{r.booking_code}</td><td className="num">{vnd(r.amount)}</td><td>{r.method === "tien_mat" ? "Tiền mặt" : "CK"}</td><td>{r.payer}</td><td>{r.status}</td><td>{fmtDT(r.created_at)}</td><td>{r.confirmed_by}</td></tr>)}</tbody></table></div>
    </>}

    {tab === "cost" && <>
      <div className="panel wrap"><h2>Đề nghị chi / lệnh chi NCC ({t.payment_requests.length}) · đã chi {vnd(sm.cost_paid)}</h2>
        <table><thead><tr><th>Mã</th><th>NCC</th><th>Nội dung</th><th className="num">Số tiền</th><th>Trạng thái</th><th>Lập</th><th>Chi</th></tr></thead>
          <tbody>{t.payment_requests.map((r: any) => <tr key={r.id}><td>{r.code}</td><td>{r.supplier_name}</td><td>{r.description}</td><td className="num">{vnd(r.amount)}</td><td><Tag cls={r.status === "da_chi" ? "ok" : "warn"}>{PR_ST[r.status] || r.status}</Tag></td><td>{fmtDT(r.created_at)}</td><td>{fmtDT(r.paid_at)}</td></tr>)}</tbody></table></div>
      <div className="panel wrap"><h2>Quyết toán chi phí thực tế theo NCC ({t.cost_lines.length} dòng) · thực chi {vnd(t.cost_total.actual)} · đã thanh toán {vnd(t.cost_total.paid)}</h2>
        <table><thead><tr><th>#</th><th>Mô tả</th><th>Loại DV</th><th>NCC (MST)</th><th className="num">Đơn giá</th><th className="num">SL</th><th className="num">HS</th><th className="num">Thực chi</th><th className="num">Đã TT</th><th>Ghi chú</th></tr></thead>
          <tbody>{t.cost_lines.length ? t.cost_lines.map((l: any) => <tr key={l.line_no}><td>{l.line_no}</td><td>{l.description} <Tag>{l.cost_kind === "theo_khach" ? "theo khách" : "cố định"}</Tag></td><td>{l.service_type}</td><td>{l.supplier_name}{l.supplier_tax_code && <span className="muted"> ({l.supplier_tax_code})</span>}</td><td className="num">{vnd(l.unit_price)}</td><td className="num">{l.qty}</td><td className="num">{l.coef}</td><td className="num">{vnd(l.actual)}</td><td className="num">{vnd(l.paid)}</td><td className="muted">{l.note}</td></tr>) : <tr><td colSpan={10} className="muted">Chưa có dòng quyết toán (đồng bộ từ Vietrip hoặc nhập khi đóng số).</td></tr>}</tbody></table></div>
    </>}

    {tab === "ops" && <div className="grid">
      <div className="panel wrap"><h2>Phân công HDV</h2><table><thead><tr><th>HDV</th><th>Ngày × đơn giá</th><th className="num">Thù lao</th><th>Trạng thái</th></tr></thead>
        <tbody>{t.guides.length ? t.guides.map((a: any) => <tr key={a.id}><td>{a.guide}</td><td>{a.days} × {vnd(a.rate_per_day)}{a.holiday && " ×2"}</td><td className="num">{vnd(a.amount)}</td><td>{a.status}</td></tr>) : <tr><td colSpan={4} className="muted">Chưa phân công – tab Nhân sự › HDV & phân chuyến.</td></tr>}</tbody></table></div>
      <div className="panel wrap"><h2>Lệnh điều xe</h2><table><thead><tr><th>Xe</th><th>Tài xế</th><th>Từ – đến</th><th className="num">Giá nội bộ</th><th>Trạng thái</th></tr></thead>
        <tbody>{t.dispatch.length ? t.dispatch.map((d: any) => <tr key={d.id}><td>{d.plate}</td><td>{d.driver}</td><td>{fmtD(d.date_from)} – {fmtD(d.date_to)}</td><td className="num">{vnd(d.internal_price)}</td><td>{d.status}</td></tr>) : <tr><td colSpan={5} className="muted">Chưa có lệnh điều xe – tab Nhân sự › Đội xe.</td></tr>}</tbody></table></div>
    </div>}

    {tab === "history" && <>
      <div className="panel"><h2>Quy trình & lịch sử</h2>
        {t.events.length ? t.events.map((e: any) => <div key={e.id} style={{ borderLeft: "3px solid " + (e.source === "vietrip" ? "#888" : "var(--teal)"), padding: "4px 10px", marginBottom: 8 }}>
          <b>{e.title}</b> {e.source === "vietrip" && <Tag>Vietrip</Tag>}<div className="muted">{fmtDT(e.at)} · {e.actor}</div>{e.note && <div style={{ background: "var(--panel2, #f4f6f8)", padding: 6, borderRadius: 6, marginTop: 4 }}>{e.note}</div>}
        </div>) : <p className="muted">Chưa có bước nào được ghi.</p>}
      </div>
      <div className="panel wrap"><h2>Nhật ký bất biến (hash-chain)</h2>
        <table><thead><tr><th>Lúc</th><th>Ai</th><th>Hành động</th><th>Trước → sau</th></tr></thead>
          <tbody>{(t.audit || []).map((l: any) => <tr key={l.id}><td>{fmtDT(l.ts)}</td><td>{l.actor}</td><td>{l.action}</td><td className="muted mono">{l.before ? JSON.stringify(l.before) + " → " : ""}{JSON.stringify(l.after || "")}</td></tr>)}</tbody></table></div>
    </>}
  </>);
}
export default function Page() { return <Shell><TourDetail /></Shell>; }
