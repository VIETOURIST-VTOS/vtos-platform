"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT } from "@/lib/api";
import { ROLES, TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, Gate, errMsg } from "@/components/ui";

function TourDetail() {
  const { id } = useParams<{ id: string }>();
  const { user, toast } = useShell();
  const [t, setT] = useState<any>(null);
  const load = useCallback(() => api(`/tours/${id}`).then(setT).catch((e) => toast(errMsg(e), true)), [id, toast]);
  useEffect(() => { load(); }, [load]);
  if (!t) return <p className="muted">Đang tải…</p>;
  const c = t.calc, s = t.settlement, act: string[] = t.actions || [];
  const can = (a: string) => act.includes(a);
  const run = async (path: string, json?: any) => { try { const r = await api(`/tours/${t.id}/${path}`, { method: "POST", json }); toast(r.message); load(); } catch (e) { toast(errMsg(e), true); } };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    ["price_per_pax", "fixed_cost", "var_cost_per_pax", "planned_pax"].forEach((k) => (d[k] = Number(d[k] || 0)));
    try { await api(`/tours/${t.id}`, { method: "PUT", json: d }); toast("Đã lưu dự toán"); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const closeTour = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    run("close", { actual_revenue: Number(d.actual_revenue), actual_cost: Number(d.actual_cost), promo_value: Number(d.promo_value || 0) });
  };
  const bookedAmount = t.bookings.reduce((a: number, b: any) => a + b.amount - b.discount, 0);
  return (<>
    <p><Link href="/tours">← Danh sách tour</Link></p>
    <h1>{t.code} · {t.name} <Tag cls="navy">{TOUR_TYPES[t.tour_type]}</Tag> {t.below_margin && <Tag cls="warn">dưới biên</Tag>}</h1>
    <p className="muted">{fmtD(t.start_date)} → {fmtD(t.end_date)} · Người điều hành <b>{t.operator_name}</b> · Trạng thái <b>{TOUR_STATUS[t.status]}</b> · Hạn quyết toán <b>{fmtD(t.settlement_deadline)}</b>{t.confirmed_by && ` · TP ĐH xác nhận: ${t.confirmed_by}`}{t.approved_by && ` · Duyệt: ${t.approved_by}`}</p>
    <div className="grid">
      <div className="panel"><h2>Ba con số dự toán (ĐH Điều 2, 11)</h2>
        <table><tbody>
          <tr><td>Số khách dự toán</td><td className="num"><b>{t.planned_pax}</b></td></tr>
          <tr><td>Số khách hòa vốn</td><td className="num"><b>{c.breakeven_pax ?? "–"}</b></td></tr>
          <tr><td>Số khách đạt biên {pct(c.threshold)}</td><td className="num"><b>{c.pax_for_margin ?? "–"}</b></td></tr>
          <tr><td>Doanh thu kế hoạch</td><td className="num">{vnd(c.revenue)}</td></tr>
          <tr><td>Giá vốn kế hoạch (cố định {vnd(t.fixed_cost)} + {vnd(t.var_cost_per_pax)}/khách)</td><td className="num">{vnd(c.cost)}</td></tr>
          <tr><td>Lợi nhuận / biên kế hoạch</td><td className="num">{vnd(c.profit)} · <b>{pct(c.margin)}</b></td></tr>
          <tr><td>Đã bán</td><td className="num"><b>{t.booked_pax}</b> khách{t.days_left >= 0 && ` · còn ${t.days_left} ngày`}</td></tr>
        </tbody></table>
        <Gate ok={c.pass_gate}>CỔNG 1 – Biên {pct(c.threshold)}: {c.pass_gate ? `ĐẠT → ${ROLES[t.approver_role]} duyệt` : "KHÔNG ĐẠT → giải trình + 2 chữ ký Chủ tịch và TGĐ; gắn cờ 'dưới biên'"}</Gate>
        {t.d7_flag && <>
          <Gate ok={false}>CỔNG 8 – Mốc D-7: {t.booked_pax}/{c.breakeven_pax} khách hòa vốn → ghép/dời/hủy; chạy tiếp cần Chủ tịch. {t.chairman_run_decision && <b>{t.chairman_run_decision}</b>}</Gate>
          {can("d7") && <>
            <button className="act grey" onClick={() => run("d7", { decision: "ghep" })}>Ghép</button><button className="act grey" onClick={() => run("d7", { decision: "doi" })}>Dời</button>
            <button className="act red" onClick={() => run("d7", { decision: "huy" })}>Hủy</button>
            {user?.role === "chutich" && <button className="act orange" onClick={() => run("d7", { decision: "chay" })}>Chủ tịch duyệt chạy</button>}
          </>}
        </>}
      </div>
      <div className="panel"><h2>Luồng phê duyệt</h2>
        {t.status === "nhap" && (can("edit") ? <form onSubmit={saveEdit}>
          <div className="grid"><div><label>Giá bán/khách</label><input type="number" name="price_per_pax" defaultValue={t.price_per_pax} step="1000" /></div><div><label>Chi phí cố định</label><input type="number" name="fixed_cost" defaultValue={t.fixed_cost} step="1000" /></div>
            <div><label>Chi phí theo khách</label><input type="number" name="var_cost_per_pax" defaultValue={t.var_cost_per_pax} step="1000" /></div><div><label>Số khách dự toán</label><input type="number" name="planned_pax" defaultValue={t.planned_pax} /></div></div>
          <label>Điểm dừng nghỉ</label><input name="rest_stops" defaultValue={t.rest_stops} />
          <label>Giải trình chuyến dưới biên (4 mục: lý do · khoản làm mỏng biên · phương án bù · lỗ tối đa) – bắt buộc khi biên &lt; {pct(c.threshold)}</label><textarea name="justification" defaultValue={t.justification} />
          <button className="act grey" type="submit">Lưu dự toán</button><button className="act teal" type="button" onClick={() => run("submit")}>Trình Trưởng phòng Điều hành</button>
        </form> : <p className="muted">Chỉ người điều hành chuyến ({t.operator_name}) hoặc TP Điều hành sửa được dự toán.</p>)}
        {t.status === "cho_xac_nhan" && <><p>Chờ Trưởng phòng Điều hành xác nhận.</p>{can("confirm") && <button className="act teal" onClick={() => run("confirm")}>Xác nhận dự toán</button>}</>}
        {t.status === "cho_duyet" && (t.below_margin ? <>
          <p>Chuyến dưới biên – cần đủ 2 chữ ký: Chủ tịch {t.signed_chutich ? "✔" : "…"} · TGĐ {t.signed_tgd ? "✔" : "…"}</p>
          <div className="gate"><b>Giải trình:</b> {t.justification}</div>
          {can("sign") && <button className="act orange" onClick={() => run("approve")}>Ký duyệt ({user?.role_name})</button>}
        </> : <><p>Chờ <b>{ROLES[t.approver_role]}</b> duyệt (Văn bản đính chính Điều 4).</p>{can("approve") && <button className="act teal" onClick={() => run("approve")}>Duyệt dự toán</button>}</>)}
        {t.status === "da_duyet" && <p>Đã duyệt. Kinh doanh gửi yêu cầu, Điều hành tạo booking tại trang <Link href="/requests">Yêu cầu & booking</Link>.</p>}
        {t.status === "huy" && <p>{t.chairman_run_decision}</p>}
        {can("close") && <><h3>Đóng số quyết toán · một cửa · hạn {fmtD(t.settlement_deadline)} {new Date().toISOString().slice(0, 10) > t.settlement_deadline && <Tag cls="red">ĐÃ QUÁ HẠN</Tag>}</h3>
          <form onSubmit={closeTour}><div className="grid">
            <div><label>Doanh thu thực tế (đ)</label><input type="number" name="actual_revenue" step="1000" defaultValue={Math.round(bookedAmount)} required /></div>
            <div><label>Giá vốn thực tế (đ)</label><input type="number" name="actual_cost" step="1000" defaultValue={Math.round(t.fixed_cost + t.var_cost_per_pax * t.booked_pax)} required /></div>
            <div><label>Giảm giá / mã KM (đ) – dòng giá vốn nội bộ (ĐC Điều 3)</label><input type="number" name="promo_value" step="1000" defaultValue={0} /></div>
          </div><button className="act teal">Đóng số → Kế toán</button></form></>}
        {can("kt_confirm") && <button className="act teal" onClick={() => run("kt-confirm")}>Kế toán xác nhận (trong 3 ngày làm việc)</button>}
        {can("cntt_check") && <button className="act teal" onClick={() => run("cntt-check")}>CNTT đối chiếu độc lập & khóa</button>}
      </div>
    </div>
    {s && <div className="panel"><h2>Quyết toán và quỹ thưởng (mục 6.4 VTOS)</h2>
      <table><tbody>
        <tr><td>Doanh thu thực tế</td><td className="num">{vnd(s.revenue)}</td><td>Đóng số</td><td>{fmtDT(t.closed_at)} · {s.on_time ? "đúng hạn" : <b>QUÁ HẠN – mất thưởng chuyến</b>}</td></tr>
        <tr><td>Giá vốn thực tế (gồm mã KM {vnd(t.promo_value)})</td><td className="num">{vnd(s.cost)}</td><td>Kế toán xác nhận</td><td>{fmtDT(t.kt_confirmed_at)}</td></tr>
        <tr><td>Lợi nhuận / biên thực tế</td><td className="num"><b>{vnd(s.profit)} · {pct(s.margin)}</b></td><td>CNTT khóa</td><td>{fmtDT(t.cntt_checked_at)}</td></tr>
        <tr><td>Quỹ thưởng Điều hành ({pct(s.rate)} LN{t.is_doan && ", đoàn không phụ thuộc biên"})</td><td className="num"><b>{vnd(s.fund)}</b></td><td>NV 70% / TP 30%</td><td className="num">{vnd(s.fund_nv)} / {vnd(s.fund_tp)}</td></tr>
      </tbody></table>
      {!s.eligible && <Gate ok={false}>Không phát sinh quỹ thưởng: {!s.on_time ? "quá hạn quyết toán" : t.below_margin ? "chuyến duyệt chạy dưới biên" : "biên thực tế dưới ngưỡng"}.</Gate>}
    </div>}
    <div className="panel wrap"><h2>Booking ({t.bookings.length})</h2>
      <table><thead><tr><th>Mã</th><th>Khách</th><th>Nguồn</th><th className="num">Khách</th><th className="num">Tiền</th><th>Sale</th><th>SLA 2h</th><th>Chỉ tiêu</th></tr></thead>
        <tbody>{t.bookings.length ? t.bookings.map((b: any) => <tr key={b.id}><td>{b.code}</td><td>{b.customer_name} · {b.customer_phone}</td><td>{b.source}</td><td className="num">{b.pax}</td><td className="num">{vnd(b.amount - b.discount)}</td><td>{b.sales_name}</td><td>{b.sla_minutes} phút {!b.sla_ok && <Tag cls="red">quá</Tag>}</td><td>{b.counts_for_target ? "có" : "không"}</td></tr>) : <tr><td colSpan={8} className="muted">Chưa có booking.</td></tr>}</tbody></table></div>
    <div className="panel wrap"><h2>Nhật ký của tour (bất biến, hash-chain)</h2>
      <table><thead><tr><th>Lúc</th><th>Ai</th><th>Hành động</th><th>Trước → sau</th></tr></thead>
        <tbody>{(t.audit || []).map((l: any) => <tr key={l.id}><td>{fmtDT(l.ts)}</td><td>{l.actor}</td><td>{l.action}</td><td className="muted mono">{l.before ? JSON.stringify(l.before) + " → " : ""}{JSON.stringify(l.after || "")}</td></tr>)}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><TourDetail /></Shell>; }
