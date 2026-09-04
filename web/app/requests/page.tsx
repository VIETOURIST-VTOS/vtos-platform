"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

function Requests() {
  const { user, toast } = useShell();
  const [reqs, setReqs] = useState<any[]>([]); const [tours, setTours] = useState<any[]>([]); const [bookings, setBookings] = useState<any[]>([]); const [sla, setSla] = useState(120);
  const load = useCallback(() => { api("/requests").then(setReqs); api("/tours?status=da_duyet").then(setTours); api("/bookings?limit=50").then(setBookings); api("/meta").then((m) => setSla(m.params.sla_booking_phut)); }, []);
  useEffect(() => { load(); }, [load]);
  const canReq = ["nv_kd", "gd_kd", "nv_dh", "tp_dh"].includes(user?.role || ""), canBook = ["nv_dh", "tp_dh"].includes(user?.role || "");
  async function send(e: React.FormEvent) {
    e.preventDefault(); const f = e.target as HTMLFormElement; const d: any = Object.fromEntries(new FormData(f).entries());
    d.tour_id = Number(d.tour_id); d.pax = Number(d.pax || 1); d.discount = Number(d.discount || 0);
    try { const r = await api("/requests", { method: "POST", json: d }); toast(r.message); f.reset(); load(); } catch (x) { toast(errMsg(x), true); }
  }
  async function book(id: number) { try { const r = await api(`/requests/${id}/booking`, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); } }
  const open = reqs.filter((r) => !r.booking_id);
  return (<>
    <h1>Yêu cầu đặt dịch vụ & booking</h1>
    <div className="grid">
      <div className="panel"><h2>Kinh doanh gửi yêu cầu – 4 trường bắt buộc (KD Lẻ Điều 2)</h2>
        {canReq ? <form onSubmit={send}>
          <label>Tour (chỉ tour đã duyệt dự toán)</label><select name="tour_id">{tours.map((t) => <option key={t.id} value={t.id}>{t.code} – {t.name} ({fmtD(t.start_date)})</option>)}</select>
          <div className="grid"><div><label>Tên khách</label><input name="customer_name" /></div><div><label>Số điện thoại *</label><input name="customer_phone" /></div></div>
          <div className="grid"><div><label>Nguồn khách *</label><select name="source" defaultValue=""><option value="">– chọn –</option>{["Fanpage", "Zalo", "Website", "Khách hàng cũ", "Giới thiệu", "Đối tác"].map((s) => <option key={s}>{s}</option>)}</select></div><div><label>Số khách</label><input type="number" name="pax" defaultValue={1} min={1} /></div></div>
          <label>Ghi chú chăm sóc *</label><input name="care_note" />
          <div className="grid"><div><label>Mã chiến dịch</label><input name="campaign_code" /></div><div><label>Mã khuyến mãi</label><input name="promo_code" /></div><div><label>Giảm giá (đ)</label><input type="number" name="discount" defaultValue={0} step="1000" /></div></div>
          <button className="act teal">Gửi Điều hành (không qua email)</button>
        </form> : <p className="muted">Vai trò này không gửi yêu cầu.</p>}
      </div>
      <div className="panel wrap"><h2>Hàng đợi Điều hành – tạo booking trong {sla} phút</h2>
        <table><thead><tr><th>#</th><th>Tour</th><th>Khách</th><th>Sale</th><th>Đã chờ</th><th></th></tr></thead>
          <tbody>{open.length ? open.map((r) => <tr key={r.id}><td>{r.id}</td><td>{r.tour_code}</td><td>{r.customer_name} · {r.pax} khách{r.discount > 0 && ` · giảm ${vnd(r.discount)}`}</td><td>{r.sales_name}</td><td>{r.waited_minutes} phút {r.waited_minutes > sla && <Tag cls="red">quá SLA</Tag>}</td>
            <td>{canBook && <button className="act teal" style={{ margin: 0 }} onClick={() => book(r.id)}>Tạo booking</button>}</td></tr>) : <tr><td colSpan={6} className="muted">Hàng đợi trống.</td></tr>}</tbody></table>
      </div>
    </div>
    <div className="panel wrap"><h2>Booking gần đây</h2>
      <table><thead><tr><th>Mã</th><th>Tour</th><th>Khách</th><th>Nguồn</th><th className="num">Khách</th><th className="num">Tiền</th><th>Mã KM</th><th>SLA</th><th>Chỉ tiêu</th><th>Lúc</th></tr></thead>
        <tbody>{bookings.map((b) => <tr key={b.id}><td>{b.code}</td><td>{b.tour_code}</td><td>{b.customer_name}</td><td>{b.source}</td><td className="num">{b.pax}</td><td className="num">{vnd(b.amount - b.discount)}</td><td>{b.promo_code}</td><td>{b.sla_minutes}′ {!b.sla_ok && <Tag cls="red">quá</Tag>}</td><td>{b.counts_for_target ? "có" : "không"}</td><td>{fmtDT(b.created_at)}</td></tr>)}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Requests /></Shell>; }
