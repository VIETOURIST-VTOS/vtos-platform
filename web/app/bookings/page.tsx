"use client";
import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import DinhKem from "@/components/DinhKem";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT, soTien } from "@/lib/api";
import { Tag, Gate, errMsg, MangTag } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

const PMT: Record<string, [string, string]> = { UNPAID: ["Chưa cọc", "red"], DEPO: ["Đã cọc", "warn"], PAID: ["Đủ tiền", "ok"], CANCEL: ["Đã hủy", ""] };
const RT_ST: Record<string, [string, string]> = { hieu_luc: ["Còn hiệu lực", "ok"], tat_toan: ["Đã tất toán", ""], huy: ["Đã hủy", "red"] };

function Bookings() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const role = user?.role || "";
  const mang = useSearchParams().get("mang") || "";
  const [rows, setRows] = useState<any[]>([]); const [q, setQ] = useState(""); const [st, setSt] = useState("due");
  const [cnt, setCnt] = useState<any>({ total: null, filtered: null }); const [page, setPage] = useState(0);
  const PAGE = 300;
  const [ret, setRet] = useState<any>({ summary: {}, rows: [] }); const [rst, setRst] = useState("hieu_luc");
  const [edit, setEdit] = useState<any>(null); const [cancel, setCancel] = useState<any>(null); const [apply, setApply] = useState<any>(null); const [cands, setCands] = useState<any[]>([]);
  const openApply = (r: any) => { setApply(r); api(`/bookings?status=due&limit=50&q=${encodeURIComponent(r.customer_phone || r.customer_name)}`).then((x) => setCands(x.filter((b: any) => b.id !== r.booking_id))).catch(() => setCands([])); };
  const load = useCallback(() => {
    api(`/bookings?limit=${PAGE}&offset=0&q=${encodeURIComponent(q)}&status=${st}&mang=${mang}`).then((x) => { setRows(x); setPage(0); }).catch((e) => toast(errMsg(e), true));
    api(`/bookings/count?q=${encodeURIComponent(q)}&status=${st}&mang=${mang}`).then(setCnt).catch(() => setCnt({ total: null, filtered: null }));
    api(`/retentions?status=${rst}`).then(setRet).catch(() => {});
  }, [q, st, rst, mang, toast]);      // thiếu `mang` ở đây là đổi menu mà danh sách không tải lại
  const more = async () => {
    try { const x = await api(`/bookings?limit=${PAGE}&offset=${(page + 1) * PAGE}&q=${encodeURIComponent(q)}&status=${st}&mang=${mang}`); setRows((r) => [...r, ...x]); setPage((p) => p + 1); } catch (e) { toast(errMsg(e), true); }
  };
  useEffect(() => { load(); }, [load]);
  const isDH = ["nv_dh", "tp_dh"].includes(role), canUnlock = ["tp_dh", "gd_kd", "cntt", "tgd"].includes(role), canRt = ["nv_dh", "tp_dh", "ketoan"].includes(role), canRtCancel = ["tp_dh", "gd_kd", "tgd", "ketoan"].includes(role);
  const canGiuCho = ["nv_dh", "tp_dh", "gd_kd", "tp_kd", "cntt", "tgd"].includes(role);
  const run = async (path: string, json: any, ok?: string) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || ok || "Xong"); load(); return true; } catch (e) { toast(errMsg(e), true); return false; } };
  // Gia hạn đòi HẠN MỚI và LÝ DO – máy chủ từ chối nếu thiếu một trong hai, vì một chỗ được giữ thêm
  // là một chỗ không bán cho khách khác. Hạn mới cũng không được muộn hơn deadline hủy chỗ của tour.
  const giaHan = async (b: any) => {
    const g = await nhap(`Gia hạn giữ chỗ ${b.code} (${b.pax} chỗ) đến lúc nào?\nNhập theo dạng 2026-09-20 17:00${b.cancel_deadline ? `\nKhông được muộn hơn deadline hủy chỗ ${fmtDT(b.cancel_deadline)}` : ""}`,
      (b.giu_cho_den || "").slice(0, 16).replace("T", " "));
    if (!g) return;
    const ly_do = (await nhap("Lý do gia hạn (bắt buộc – một chỗ giữ thêm là một chỗ không bán được):") || "").trim();
    if (!ly_do) { toast("Phải ghi lý do gia hạn.", true); return; }
    run(`/bookings/${b.id}/giu-cho/gia-han`, { den: g.trim().replace(" ", "T"), ly_do });
  };
  // Khôi phục = xin lại chỗ đã trả về tour. Máy chủ kiểm tour còn chỗ trước khi cho; hết chỗ thì báo
  // đỏ chứ không im lặng cho qua – cho qua ở đây là bán trùng ghế.
  const khoiPhuc = async (b: any) => {
    const note = (await nhap(`Khôi phục giữ chỗ ${b.code} – ${b.pax} chỗ. Lý do:`, "Khách báo đã chuyển tiền") || "").trim();
    if (!note) return;
    run(`/bookings/${b.id}/giu-cho/khoi-phuc`, { note });
  };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    ["adl", "chd", "inf"].forEach((k) => (d[k] = d[k] === "" ? null : Number(d[k])));
    try { await api(`/bookings/${edit.id}`, { method: "PUT", json: d }); toast("Đã cập nhật thông tin khách"); setEdit(null); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const doCancel = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    if (await run(`/bookings/${cancel.id}/cancel`, { reason: d.reason, charge: soTien(d.charge), retain: d.mode === "retain", expires_days: d.expires_days ? Number(d.expires_days) : null })) setCancel(null);
  };
  const doApply = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    if (await run(`/retentions/${apply.id}/apply`, { booking_id: Number(d.booking_id), amount: d.amount ? Number(d.amount) : null })) setApply(null);
  };
  const s = ret.summary || {};
  return (<>{hop}
    <h1>Booking & tiền bảo lưu</h1>
    <MangTag mang={mang} />
    <p className="muted">Theo vận hành Vietrip: % cọc theo sản phẩm → trạng thái Chưa cọc / Đã cọc / Đủ tiền; deadline hủy chỗ = khởi hành − số ngày đóng tour (17:00); robot R4 khóa booking khi đóng tour hoặc thu đủ, nhắc cọc quá hạn; Điều hành hủy booking (một cửa) → phí hủy giữ lại, phần còn lại bảo lưu hoặc hoàn tiền. <Link href="/requests">Tạo yêu cầu / booking mới →</Link></p>

    <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
        <label style={{ flex: 1, minWidth: 220 }}>Tìm (mã booking, khách, SĐT, mã tour)<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="BK2609… / 0903… / PT001" /></label>
        <label>Trạng thái<select value={st} onChange={(e) => setSt(e.target.value)}><option value="due">Còn phải thu</option><option value="unpaid">Chưa cọc</option><option value="depo">Đã cọc</option><option value="paid">Đủ tiền</option><option value="locked">Đã khóa</option><option value="cancelled">Đã hủy</option><option value="">Tất cả</option></select></label>
        {(isDH || ["gd_kd", "ketoan", "cntt", "tgd"].includes(role)) && <button className="act grey" style={{ margin: 0 }} onClick={() => run("/bookings/check", {}, "Đã chạy kiểm tra cọc – deadline – khóa")}>Chạy robot R4 ngay</button>}
      </div>
      <h2 style={{ marginTop: 10 }}>Booking – đang xem {rows.length}{cnt.filtered != null && <> / thỏa bộ lọc <b>{cnt.filtered.toLocaleString("vi-VN")}</b> / tổng toàn hệ thống <b>{cnt.total.toLocaleString("vi-VN")}</b></>}</h2>
      {cnt.filtered != null && rows.length < cnt.filtered && <p className="muted">Đang hiển thị {rows.length} dòng mới nhất – <b>không dùng số này làm tổng</b>. <button className="act grey" style={{ margin: 0 }} onClick={more}>Tải thêm {PAGE} dòng</button></p>}
      <table><thead><tr><th>Mã</th><th>Tour · KH</th><th>Khách</th><th className="num">Pax</th><th className="num">Tiền</th><th className="num">Cọc {""}</th><th className="num">Đã thu</th><th className="num">Còn lại</th><th>Trạng thái</th><th>Deadline hủy chỗ</th><th>Giữ chỗ</th><th>Khóa</th><th>Sale</th><th></th></tr></thead>
        <tbody>{rows.length ? rows.map((b) => { const [pl, pc] = PMT[b.pmt_status] || [b.pmt_status, ""]; return <tr key={b.id} style={{ opacity: b.cancelled ? 0.55 : 1 }}>
          <td><b>{b.code}</b><div className="muted">{fmtDT(b.created_at)}</div></td>
          <td><Link href={`/tours/${b.tour_id}`}>{b.tour_code}</Link><div className="muted">{fmtD(b.tour_start)}</div></td>
          <td>{b.customer_name}<div className="muted">{b.customer_phone} · {b.source}</div>{b.nguon_ctv && <div className="muted" title={`${b.nguon_ctv.loai} ${b.nguon_ctv.tu} · giữ nguồn tới ${b.nguon_ctv.den} · máy gắn lúc tạo booking, khóa — đổi nguồn qua khiếu nại`}><Tag cls="navy">Nguồn: CTV {b.nguon_ctv.doi_tac} ({b.nguon_ctv.ma_ctv})</Tag></div>}{b.cancelled && <div className="muted">Hủy: {b.cancel_reason}{b.cancel_charge > 0 && ` · phí ${vnd(b.cancel_charge)}`}</div>}</td>
          <td className="num">{b.pax}{(b.adl || b.chd || b.inf) ? <div className="muted">{b.adl}/{b.chd}/{b.inf}</div> : null}</td>
          <td className="num">{vnd(b.amount - b.discount)}</td><td className="num muted">{b.deposit_pct}% · {vnd(b.deposit_due)}</td><td className="num">{vnd(b.paid)}</td>
          <td className="num">{b.cancelled ? "–" : b.due > 0 ? <Tag cls="warn">{vnd(b.due)}</Tag> : <Tag cls="ok">Đủ</Tag>}</td>
          <td><Tag cls={pc}>{pl}</Tag></td>
          <td style={{ color: b.past_deadline && b.pmt_status !== "PAID" ? "var(--red)" : undefined }}>{fmtDT(b.cancel_deadline)}{b.past_deadline && <div className="muted">đã qua</div>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{b.cancelled ? <span className="muted">–</span>
            : b.giu_cho_het ? <><Tag cls="red">đã trả chỗ</Tag><div className="muted">{fmtDT(b.giu_cho_het_luc)}</div></>
            : b.qua_han_giu_cho ? <><Tag cls="warn">quá hạn</Tag><div className="muted">{fmtDT(b.giu_cho_den)}</div></>
            : b.giu_cho_den ? <span className="muted">đến {fmtDT(b.giu_cho_den)}</span>
            : <span className="muted">chưa đặt hạn</span>}</td>
          <td>{b.locked ? <Tag cls="navy" >🔒 {b.lock_reason}</Tag> : <span className="muted">mở</span>}</td>
          <td>{b.sales_name}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            {!b.cancelled && !b.locked && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setEdit(b)}>sửa khách</button>}{" "}
            {!b.cancelled && b.locked && canUnlock && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={async () => { const r = await nhap(`Lý do mở khóa ${b.code}?`); if (r) run(`/bookings/${b.id}/unlock`, { note: r }); }}>mở khóa</button>}{" "}
            {!b.cancelled && isDH && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setCancel(b)}>hủy</button>}{" "}
            {/* VPM-7 · cửa giữ chỗ. Trước 11/9/2026 phân hệ này có đủ robot, đủ nhật ký, đủ cửa ở máy chủ
                mà màn hình KHÔNG có nút nào – tức là luật chỉ sống trong mã, còn Điều hành thì không dùng
                được. Gia hạn khi chỗ còn đang giữ; khôi phục khi chỗ đã trả về tour (và chỉ được nếu tour
                còn chỗ – máy chủ kiểm, không phải màn hình). */}
            {!b.cancelled && canGiuCho && !b.giu_cho_het &&
              <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => giaHan(b)}>gia hạn giữ chỗ</button>}
            {!b.cancelled && canGiuCho && b.giu_cho_het &&
              <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => khoiPhuc(b)}>khôi phục giữ chỗ</button>}
          </td></tr>; }) : <tr><td colSpan={14} className="muted">Không có booking theo bộ lọc.</td></tr>}</tbody></table>
    </div>

    {edit && <form onSubmit={saveEdit} className="panel"><h2>Sửa thông tin khách – {edit.code} ({edit.tour_code})</h2>
      <div className="grid"><div><label>Tên khách</label><input name="customer_name" defaultValue={edit.customer_name} /></div><div><label>SĐT</label><input name="customer_phone" defaultValue={edit.customer_phone} /></div>
        <div><label>ADL</label><input name="adl" type="number" min={0} defaultValue={edit.adl} /></div><div><label>CHD</label><input name="chd" type="number" min={0} defaultValue={edit.chd} /></div><div><label>INF</label><input name="inf" type="number" min={0} defaultValue={edit.inf} /></div></div>
      <label>Ghi chú chăm sóc</label><input name="care_note" defaultValue={edit.care_note || ""} /><label>Dịch vụ lẻ</label><input name="services_note" defaultValue={edit.services_note || ""} />
      <p className="muted">Tiền booking không tự tính lại khi đổi cơ cấu khách (giữ giá đã chốt). Booking đã khóa (đóng tour / thu đủ) phải được TP Điều hành / GĐ KD mở khóa.</p>
      <button className="act teal" type="submit">Lưu</button> <button type="button" className="act grey" onClick={() => setEdit(null)}>Đóng</button></form>}
    {edit && <DinhKem doiTuong="booking" doiTuongId={edit.code} tieuDe={`Chứng từ của booking ${edit.code}`}
      goi={"Ảnh ủy nhiệm chi, biên lai thu tiền, hợp đồng ký với khách, hộ chiếu/giấy tờ tùy thân. " +
           "Chứng từ nằm cùng booking thì lúc đối chiếu tiền không phải đi hỏi từng người."} />}

    {cancel && <form onSubmit={doCancel} className="panel"><h2>Hủy booking {cancel.code} – {cancel.customer_name} · đã thu {vnd(cancel.paid)}</h2>
      {cancel.past_deadline && <Gate ok={false}>Đã qua deadline hủy chỗ {fmtDT(cancel.cancel_deadline)} – cân nhắc phí hủy theo điều kiện tour.</Gate>}
      <label>Lý do (bắt buộc – hiển thị ở danh sách bảo lưu)</label><input name="reason" required placeholder="VD: KHÁCH BỆNH HỦY TOUR – charge 700K, còn lại bảo lưu đến 30/10" />
      <div className="grid"><div><label>Phí hủy giữ lại (đ) – tối đa {vnd(cancel.paid)}</label><input name="charge" type="number" step={1000} min={0} max={cancel.paid} defaultValue={0} /></div>
        <div><label>Phần còn lại</label><select name="mode" defaultValue="retain"><option value="retain">Bảo lưu cho khách (dùng tour sau)</option><option value="refund">Lập đề nghị hoàn tiền</option></select></div>
        <div><label>Hạn bảo lưu (ngày, trống = theo tham số)</label><input name="expires_days" type="number" min={0} /></div></div>
      <button className="act teal" type="submit">Xác nhận hủy</button> <button type="button" className="act grey" onClick={() => setCancel(null)}>Đóng</button></form>}

    <div className="panel wrap">
      <h2>Tiền bảo lưu</h2>
      <div className="kpis">
        <div className="kpi"><b>{vnd(s.hieu_luc?.remaining)}</b><span>Tổng còn hiệu lực ({s.hieu_luc?.n || 0} khoản)</span></div>
        <div className="kpi"><b>{vnd(s.refunded)}</b><span>Đã hoàn tiền cho khách</span></div>
        <div className="kpi"><b>{vnd(s.tat_toan?.amount)}</b><span>Đã tất toán ({s.tat_toan?.n || 0})</span></div>
        <div className="kpi"><b>{vnd(s.huy?.amount)}</b><span>Đã hủy bảo lưu ({s.huy?.n || 0})</span></div>
      </div>
      <label>Trạng thái<select value={rst} onChange={(e) => setRst(e.target.value)}><option value="hieu_luc">Còn hiệu lực</option><option value="tat_toan">Đã tất toán</option><option value="huy">Đã hủy</option><option value="all">Tất cả</option></select></label>
      <table><thead><tr><th>Mã</th><th>Booking gốc · Tour</th><th>Khách</th><th className="num">Số tiền</th><th className="num">Còn lại</th><th>Ghi chú</th><th>Hạn</th><th>Trạng thái</th><th>Người tạo</th><th></th></tr></thead>
        <tbody>{ret.rows?.length ? ret.rows.map((r: any) => { const [l, c] = RT_ST[r.status] || [r.status, ""]; return <tr key={r.id}>
          <td><b>{r.code}</b><div className="muted">{fmtDT(r.created_at)}</div></td><td>{r.booking_code}<div className="muted">{r.tour_code} · KH {fmtD(r.start_date)}</div></td>
          <td>{r.customer_name}<div className="muted">{r.customer_phone}</div></td><td className="num">{vnd(r.amount)}</td><td className="num"><b>{vnd(r.remaining)}</b></td>
          <td className="muted" style={{ maxWidth: 260 }}>{r.note}{r.resolve_note && <div>→ {r.resolve_note}</div>}</td><td>{fmtD(r.expires_on)}</td><td><Tag cls={c}>{l}</Tag>{r.refund_request_id && r.status === "hieu_luc" && <div className="muted">đang hoàn</div>}</td><td>{r.created_by}</td>
          <td style={{ whiteSpace: "nowrap" }}>{r.status === "hieu_luc" && <>
            {canRt && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => openApply(r)}>dùng cho booking</button>}{" "}
            {!r.refund_request_id && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={async () => { const n = await nhap(`Đề xuất hoàn ${vnd(r.remaining)} đ cho ${r.customer_name} – ghi chú:`); if (n !== null) run(`/retentions/${r.id}/refund`, { note: n }); }}>đề xuất hoàn tiền</button>}{" "}
            {canRtCancel && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={async () => { const n = await nhap(`Lý do hủy bảo lưu ${r.code} (số còn lại ghi thu nhập khác)?`); if (n) run(`/retentions/${r.id}/cancel`, { note: n }); }}>hủy bảo lưu</button>}</>}</td>
        </tr>; }) : <tr><td colSpan={10} className="muted">Không có khoản bảo lưu.</td></tr>}</tbody></table>
    </div>

    {apply && <form onSubmit={doApply} className="panel"><h2>Dùng bảo lưu {apply.code} ({vnd(apply.remaining)} đ) cho booking mới</h2>
      <div className="grid"><div><label>Booking mới của khách (còn phải thu)</label>{cands.length ? <select name="booking_id" required>{cands.map((b) => <option key={b.id} value={b.id}>{b.code} · {b.tour_code} · còn {vnd(b.due)} đ</option>)}</select> : <input name="booking_id" type="number" required placeholder="Không tìm thấy theo SĐT – nhập ID booking" />}</div><div><label>Số tiền (trống = tối đa còn lại / còn phải thu)</label><input name="amount" type="number" step={1000} min={0} /></div></div>
      <p className="muted">Lập phiếu thu phương thức “bảo lưu” cho booking mới, bút toán Nợ 131 booking cũ – Có 131 booking mới; dùng hết → tất toán.</p>
      <button className="act teal" type="submit">Tất toán vào booking</button> <button type="button" className="act grey" onClick={() => setApply(null)}>Đóng</button></form>}
  </>);
}

export default function Page() { return <Shell><Suspense><Bookings /></Suspense></Shell>; }
