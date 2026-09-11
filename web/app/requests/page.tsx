"use client";
import { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT, soTien } from "@/lib/api";
import { Tag, errMsg, MangTag } from "@/components/ui";

/** Góc nhìn theo vai trò (Đề xuất 06/9 mục 4). Chỉ mở những góc nhìn mà quy trình hiện có trạng thái tương ứng:
 *  "Đang xử lý" và "Chờ bổ sung" cần bổ sung trạng thái vào quy trình yêu cầu – chờ chính sách duyệt. */
const VIEWS: [string, string][] = [
  ["cua_toi", "Của tôi"],
  ["cho_phan_cong", "Chờ phân công"],
  ["sap_qua_han", "Sắp quá hạn"],
  ["qua_han", "Quá hạn"],
  ["hoan_tat", "Hoàn tất"],
  ["", "Tất cả"],
];

const SLA_TAG: Record<string, [string, string]> = {
  cho_phan_cong: ["Còn hạn", "ok"],
  sap_qua_han: ["Sắp quá hạn", "warn"],
  qua_han: ["QUÁ HẠN", "red"],
  hoan_tat: ["Hoàn tất", ""],
};

function Requests() {
  const { user, toast } = useShell();
  const mang = useSearchParams().get("mang") || "";
  const [reqs, setReqs] = useState<any[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [bookings, setBookings] = useState<any[]>([]);
  const [sla, setSla] = useState(120);
  const [view, setView] = useState("cho_phan_cong");

  const load = useCallback(() => {
    api(`/requests?mang=${mang}`).then(setReqs).catch((e) => toast(errMsg(e), true));
    api(`/tours?status=da_duyet&mang=${mang}`).then((r) => setTours(r.rows || [])).catch(() => {});
    api(`/bookings?limit=50&mang=${mang}`).then(setBookings).catch(() => {});
    api("/meta").then((m) => setSla(m.params.sla_booking_phut)).catch(() => {});
  }, [mang, toast]);      // thiếu `mang` ở đây là đổi menu mà danh sách không tải lại
  useEffect(() => { load(); }, [load]);

  // Quyền lấy từ máy chủ (/auth/me) – không dựng lại danh sách vai trò ở giao diện để khỏi lệch với máy chủ.
  const canReq = !!user?.can_create_request, canBook = !!user?.can_create_booking;

  const counts = useMemo(() => {
    const c: Record<string, number> = { cua_toi: 0, cho_phan_cong: 0, sap_qua_han: 0, qua_han: 0, hoan_tat: 0, "": reqs.length };
    reqs.forEach((r) => {
      c[r.view] = (c[r.view] || 0) + 1;
      if (user && (r.sales_id === user.id || r.operator_id === user.id)) c.cua_toi++;
    });
    return c;
  }, [reqs, user]);

  const rows = useMemo(() => {
    if (!view) return reqs;
    if (view === "cua_toi") return reqs.filter((r) => user && (r.sales_id === user.id || r.operator_id === user.id));
    return reqs.filter((r) => r.view === view);
  }, [reqs, view, user]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    const d: any = Object.fromEntries(new FormData(f).entries());
    d.tour_id = Number(d.tour_id); d.pax = Number(d.pax || 1); d.discount = soTien(d.discount);
    try { const r = await api("/requests", { method: "POST", json: d }); toast(r.message); f.reset(); load(); } catch (x) { toast(errMsg(x), true); }
  }
  async function book(id: number) {
    try { const r = await api(`/requests/${id}/booking`, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); }
  }

  return (<>
    <h1>Yêu cầu đặt dịch vụ & booking</h1>
    <MangTag mang={mang} />
    <p className="muted">Mỗi yêu cầu hiển thị người chịu trách nhiệm nhận việc, hạn xử lý và bước tiếp theo – không chỉ thời gian chờ. Đồng hồ {sla} phút tính từ lúc Kinh doanh gửi yêu cầu (ĐH Điều 2).</p>

    {canReq && <div className="panel"><h2>Gửi yêu cầu đặt dịch vụ – 4 trường bắt buộc (KD Lẻ Điều 2)</h2>
      <form onSubmit={send}>
        <label>Tour (chỉ tour đã duyệt dự toán)</label>
        <select name="tour_id">{tours.map((t) => <option key={t.id} value={t.id}>{t.code} – {t.name} ({fmtD(t.start_date)})</option>)}</select>
        <div className="grid"><div><label>Tên người đặt</label><input name="customer_name" /></div><div><label>Số điện thoại *</label><input name="customer_phone" /></div></div>
        <div className="grid"><div><label>Nguồn khách *</label><select name="source" defaultValue=""><option value="">– chọn –</option>{["Fanpage", "Zalo", "Website", "Khách hàng cũ", "Giới thiệu", "Đối tác"].map((s) => <option key={s}>{s}</option>)}</select></div><div><label>Số khách</label><input type="number" name="pax" defaultValue={1} min={1} /></div></div>
        <label>Ghi chú chăm sóc *</label><input name="care_note" />
        <div className="grid"><div><label>Mã chiến dịch</label><input name="campaign_code" /></div><div><label>Mã khuyến mãi</label><input name="promo_code" /></div><div><label>Giảm giá (đ)</label><input type="number" name="discount" defaultValue={0} step="1000" /></div></div>
        <button className="act teal">Gửi Điều hành (không qua email)</button>
      </form>
    </div>}

    <div className="panel wrap">
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 8 }}>
        {VIEWS.map(([k, l]) => <button key={k} className={"act " + (view === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setView(k)}>{l} ({counts[k] || 0})</button>)}
      </div>
      <h2>{VIEWS.find(([k]) => k === view)?.[1]} – {rows.length} yêu cầu</h2>
      <table><thead><tr><th>Mã YC</th><th>Tour · khởi hành</th><th>Người đặt</th><th className="num">Số khách</th><th className="num">Giá trị booking</th><th>Người gửi</th><th>Người phụ trách</th><th>Thời điểm gửi</th><th>Hạn xử lý</th><th>Bước tiếp theo</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((r) => { const [sl, sc] = SLA_TAG[r.sla_state] || ["", ""]; return <tr key={r.id}>
          <td><b>YC-{r.id}</b></td>
          <td><Link href={`/tours/${r.tour_id}`}>{r.tour_code}</Link><div className="muted">{fmtD(r.tour_start)}</div></td>
          <td>{r.customer_name}<div className="muted">{r.customer_phone} · {r.source}</div></td>
          <td className="num">{r.pax}</td>
          <td className="num">{vnd(r.amount)}{r.discount > 0 && <div className="muted">giảm {vnd(r.discount)}</div>}</td>
          <td>{r.sales_name}</td>
          <td>{r.operator_name || <span className="muted">chưa xác định</span>}</td>
          <td>{fmtDT(r.created_at)}</td>
          <td>{r.booking_id ? <Tag>{sl}</Tag> : <>{fmtDT(r.deadline)} <Tag cls={sc}>{sl}</Tag><div className="muted">đã chờ {r.waited_minutes} phút</div></>}</td>
          <td className="muted">{r.next_step}</td>
          <td>{!r.booking_id && canBook && <button className="act teal" style={{ margin: 0 }} onClick={() => book(r.id)}>Tạo booking</button>}</td>
        </tr>; }) : <tr><td colSpan={11} className="muted">Không có yêu cầu trong góc nhìn này.</td></tr>}</tbody></table>
    </div>

    <div className="panel wrap"><h2>Booking gần đây</h2>
      <table><thead><tr><th>Mã booking</th><th>Tour</th><th>Người đặt</th><th>Nguồn</th><th className="num">Số khách</th><th className="num">Giá trị booking</th><th>Mã khuyến mãi</th><th>Thời gian tạo booking</th><th>Tính chỉ tiêu</th><th>Thời điểm tạo</th></tr></thead>
        <tbody>{bookings.map((b) => <tr key={b.id}>
          <td>{b.code}</td><td>{b.tour_code}</td><td>{b.customer_name}</td><td>{b.source}</td>
          <td className="num">{b.pax}</td><td className="num">{vnd(b.amount - b.discount)}</td><td>{b.promo_code}</td>
          <td>{b.sla_known === false ? <span className="muted">Chưa đủ dữ liệu</span> : <>{b.sla_minutes}′ {!b.sla_ok && <Tag cls="red">quá {sla}′</Tag>}</>}</td>
          <td>{b.counts_for_target ? "có" : "không"}</td><td>{fmtDT(b.created_at)}</td>
        </tr>)}</tbody></table>
      <p className="muted">Booking nhập từ hệ thống khác (Vietrip) không mang mốc tiếp nhận yêu cầu nên cột thời gian tạo booking ghi “Chưa đủ dữ liệu”, không tính là xử lý trong 0 phút.</p>
    </div>
  </>);
}
export default function Page() { return <Shell><Suspense><Requests /></Suspense></Shell>; }
