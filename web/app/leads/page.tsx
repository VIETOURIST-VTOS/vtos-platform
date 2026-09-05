"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, pct, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, Gate, errMsg } from "@/components/ui";

const ST_CLS: Record<string, string> = { moi: "navy", dang_cham_soc: "warn", chot: "ok", mat: "" };

function Leads() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [meta, setMeta] = useState<any>({ channels: [], status: {}, zalo: {} });
  const month0 = new Date().toISOString().slice(0, 7);
  const [tab, setTab] = useState("leads");
  const [month, setMonth] = useState(month0); const [channel, setChannel] = useState(""); const [status, setStatus] = useState(""); const [q, setQ] = useState("");
  const [data, setData] = useState<any>({ rows: [], counts: {} });
  const [rep, setRep] = useState<any>(null); const [repMonth, setRepMonth] = useState(month0);
  const [zalo, setZalo] = useState<any>({ messages: {} }); const [msgs, setMsgs] = useState<any[]>([]);
  const [edit, setEdit] = useState<any>(null); const [zsend, setZsend] = useState<any>(null); const [showNew, setShowNew] = useState(false);
  useEffect(() => { api("/leads/meta").then(setMeta).catch(() => {}); }, []);
  const load = useCallback(() => {
    if (tab === "leads") api(`/leads?month=${month}&channel=${encodeURIComponent(channel)}&status=${status}&q=${encodeURIComponent(q)}`).then(setData).catch((e) => toast(errMsg(e), true));
    if (tab === "report") api(`/leads/conversion?month=${repMonth}`).then(setRep).catch((e) => toast(errMsg(e), true));
    if (tab === "zalo") { api("/zalo/status").then(setZalo).catch(() => {}); api("/zalo/messages?limit=100").then(setMsgs).catch(() => {}); }
  }, [tab, month, channel, status, q, repMonth, toast]);
  useEffect(() => { load(); }, [load]);
  const canEdit = ["nv_kd", "gd_kd", "ptgd_mkt", "cntt", "tgd"].includes(role);
  const post = async (path: string, json?: any, ok?: string) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || ok || "Xong"); load(); return r; } catch (e) { toast(errMsg(e), true); } };
  const upload = () => { const inp = document.createElement("input"); inp.type = "file"; inp.accept = ".xlsx"; inp.onchange = async () => { const f = inp.files?.[0]; if (!f) return; const fd = new FormData(); fd.append("file", f);
    try { const r = await fetch(`/api/v1/leads/import?default_month=${month}`, { method: "POST", body: fd, headers: { Authorization: `Bearer ${getToken() || ""}` } }); const j = await r.json(); if (!r.ok) throw new Error(j.detail?.message || j.detail || "Lỗi"); toast(j.message); load(); } catch (e: any) { toast(e.message, true); } }; inp.click(); };
  const createLead = async (e: React.FormEvent) => { e.preventDefault(); const f = e.target as HTMLFormElement; const d: any = Object.fromEntries(new FormData(f).entries()); if (await post("/leads", { ...d, lead_month: d.lead_month || month })) { f.reset(); setShowNew(false); } };
  const saveEdit = async (e: React.FormEvent) => { e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries()); try { await api(`/leads/${edit.id}`, { method: "PUT", json: d }); toast("Đã cập nhật lead"); setEdit(null); load(); } catch (x) { toast(errMsg(x), true); } };
  const sendZalo = async (e: React.FormEvent) => { e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries()); const r = await post("/zalo/send", { lead_id: zsend.id, text: d.text, purpose: d.purpose }); if (r) setZsend(null); };
  const xlsx = async () => { try { const r = await fetch(`/api/v1/leads/conversion/xlsx?month=${repMonth}`, { headers: { Authorization: `Bearer ${getToken() || ""}` } }); const u = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = u; a.download = `VTOS_Lead_Chuyen_doi_${repMonth}.xlsx`; a.click(); } catch { toast("Không xuất được", true); } };
  const c = data.counts || {};
  return (<>
    <h1>CRM – Lead & Zalo</h1>
    <p className="muted">Lead theo kênh (Hotline, VCHAT, Web, Tiktok Ads, Livestream, Appier, Zalo OA…) ghi vào VTOS trong ngày; robot đối chiếu SĐT lead với booking để tính tỷ lệ chốt, khách mới / quay lại, doanh thu lũy kế (đúng mẫu Báo cáo Lead & Chuyển đổi của Marketing); nhắn Zalo OA/ZNS cho lead và khách.</p>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{[["leads", "Danh sách lead"], ["report", "Báo cáo lead & chuyển đổi"], ["zalo", "Kết nối Zalo"]].map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "leads" && <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
        <label>Tháng lead<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></label>
        <label>Kênh<select value={channel} onChange={(e) => setChannel(e.target.value)}><option value="">Tất cả</option>{meta.channels.map((x: string) => <option key={x} value={x}>{x}</option>)}</select></label>
        <label>Trạng thái<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">Tất cả</option>{Object.entries(meta.status).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label style={{ flex: 1, minWidth: 180 }}>Tìm<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="SĐT / tên / tour quan tâm" /></label>
        {canEdit && <><button className="act teal" style={{ margin: 0 }} onClick={() => setShowNew(!showNew)}>+ Lead</button><button className="act grey" style={{ margin: 0 }} onClick={upload}>Nhập Excel (file Marketing)</button><button className="act grey" style={{ margin: 0 }} onClick={() => post("/leads/match", {}, "Đã đối chiếu lead với booking")}>Đối chiếu booking</button></>}
      </div>
      <div className="kpis"><div className="kpi"><b>{Object.values(c).reduce((a: any, b: any) => a + b, 0) as any}</b><span>Lead tháng {month}</span></div><div className="kpi"><b>{c.chot || 0}</b><span>Đã chốt tour</span></div><div className="kpi"><b>{c.dang_cham_soc || 0}</b><span>Đang chăm sóc</span></div><div className="kpi"><b>{c.moi || 0}</b><span>Mới</span></div></div>
      {showNew && <form onSubmit={createLead} className="panel"><h2>Lead mới</h2><div className="grid"><div><label>SĐT *</label><input name="phone" required /></div><div><label>Tên khách</label><input name="name" /></div><div><label>Kênh</label><select name="channel">{meta.channels.map((x: string) => <option key={x}>{x}</option>)}</select></div><div><label>Tháng lead</label><input name="lead_month" type="month" defaultValue={month} /></div><div><label>Tour quan tâm</label><input name="interest" /></div><div><label>Chiến dịch</label><input name="campaign" /></div></div><label>Ghi chú</label><input name="note" /><button className="act teal">Lưu</button></form>}
      {edit && <form onSubmit={saveEdit} className="panel"><h2>Lead {edit.phone} – {edit.name}</h2><div className="grid"><div><label>Tên</label><input name="name" defaultValue={edit.name} /></div><div><label>Trạng thái</label><select name="status" defaultValue={edit.status}>{Object.entries(meta.status).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></div><div><label>Tour quan tâm</label><input name="interest" defaultValue={edit.interest} /></div></div><label>Ghi chú chăm sóc (nối tiếp)</label><textarea name="note" defaultValue={edit.note} /><button className="act teal">Lưu</button> <button type="button" className="act grey" onClick={() => setEdit(null)}>Đóng</button></form>}
      {zsend && <form onSubmit={sendZalo} className="panel"><h2>Nhắn Zalo – {zsend.name || zsend.phone} {zsend.zalo_uid ? <Tag cls="ok">đã quan tâm OA</Tag> : <Tag cls="warn">chưa có Zalo OA → gửi ZNS theo SĐT</Tag>}</h2>
        <div className="grid"><div><label>Mục đích</label><select name="purpose" defaultValue="cham_soc"><option value="cham_soc">Chăm sóc / tư vấn</option><option value="nhac_coc">Nhắc cọc</option><option value="xac_nhan_booking">Xác nhận booking</option><option value="khuyen_mai">Khuyến mãi</option><option value="cam_on">Cảm ơn sau tour</option></select></div></div>
        <label>Nội dung (OA) – với ZNS dùng mẫu đã duyệt theo mục đích</label><textarea name="text" defaultValue={`Vietourist chào ${zsend.name || "anh/chị"}, em là ${user?.full_name}. `} />
        <button className="act teal">Gửi</button> <button type="button" className="act grey" onClick={() => setZsend(null)}>Đóng</button></form>}
      <table><thead><tr><th>SĐT</th><th>Khách</th><th>Kênh</th><th>Tháng</th><th>Tour quan tâm</th><th>Trạng thái</th><th>Booking</th><th>Sale</th><th>Zalo</th><th>Liên hệ cuối</th><th></th></tr></thead>
        <tbody>{data.rows.length ? data.rows.map((l: any) => <tr key={l.id}><td><b>{l.phone}</b>{l.phone.length < 10 && <div className="muted">thiếu số</div>}</td><td>{l.name}</td><td>{l.channel}</td><td>{l.lead_month}</td><td className="muted">{l.interest}</td><td><Tag cls={ST_CLS[l.status] || ""}>{l.status_name}</Tag></td><td>{l.booking_code}<div className="muted">{l.booking_tour}</div></td><td>{l.sales_name}</td><td>{l.zalo_uid ? <Tag cls="ok">OA</Tag> : "–"}</td><td>{fmtDT(l.last_contact_at)}</td>
          <td style={{ whiteSpace: "nowrap" }}>{canEdit && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setEdit(l)}>sửa</button>} <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setZsend(l)}>Zalo</button></td></tr>) : <tr><td colSpan={11} className="muted">Chưa có lead – bấm “Nhập Excel” để nạp file của Marketing.</td></tr>}</tbody></table>
    </div>}

    {tab === "report" && <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}><label>Tháng tour khởi hành<input type="month" value={repMonth} onChange={(e) => setRepMonth(e.target.value)} /></label><button className="act grey" style={{ margin: 0 }} onClick={xlsx}>Xuất Excel (mẫu Marketing)</button>{rep && <span className="muted">Đối chiếu lúc {fmtDT(rep.as_of)} · lead các tháng {rep.lead_months.join(", ")}</span>}</div>
      {rep && <>
        <h2>1. Lead tháng {rep.target_month} → tour khởi hành tháng {rep.target_month} theo kênh</h2>
        <table><thead><tr><th>Kênh</th><th className="num">Số leads</th><th className="num">SĐT chốt tour</th><th className="num">Tỷ lệ chốt</th><th className="num">Khách mới</th><th className="num">Quay lại</th><th className="num">Doanh thu lũy kế</th><th className="num">Chi phí/lead</th></tr></thead>
          <tbody>{rep.by_channel_current.map((a: any) => <tr key={a.channel}><td>{a.channel}</td><td className="num">{a.leads}</td><td className="num">{a.converted}</td><td className="num"><b>{pct(a.rate)}</b></td><td className="num">{a.new}</td><td className="num">{a.returning}</td><td className="num">{vnd(a.revenue)}</td><td className="num">{a.cost_per_lead ? vnd(a.cost_per_lead) : "–"}</td></tr>)}
            <tr><td><b>TỔNG</b></td><td className="num"><b>{rep.total_current.leads}</b></td><td className="num"><b>{rep.total_current.converted}</b></td><td className="num"><b>{pct(rep.total_current.rate)}</b></td><td colSpan={4}></td></tr></tbody></table>
        <h2>2. Lead các tháng → tour tháng {rep.target_month}</h2>
        <table><thead><tr><th>Tháng lead</th><th className="num">Tổng leads</th><th className="num">SĐT có tour</th><th className="num">Tỷ lệ chốt</th><th className="num">Khách mới</th><th className="num">Quay lại</th><th className="num">Doanh thu lũy kế</th></tr></thead>
          <tbody>{rep.by_month.map((m: any) => <tr key={m.lead_month}><td>{m.lead_month}</td><td className="num">{m.leads}</td><td className="num">{m.converted}</td><td className="num"><b>{pct(m.rate)}</b></td><td className="num">{m.new}</td><td className="num">{m.returning}</td><td className="num">{vnd(m.revenue)}</td></tr>)}</tbody></table>
        <h2>3. Kênh × tháng lead</h2>
        <table><thead><tr><th>Kênh</th><th>Tháng lead</th><th className="num">Tổng leads</th><th className="num">SĐT có tour</th><th className="num">Tỷ lệ</th><th className="num">Mới</th><th className="num">Quay lại</th><th className="num">Doanh thu lũy kế</th></tr></thead>
          <tbody>{rep.by_channel_month.map((a: any, i: number) => <tr key={i}><td>{a.channel}</td><td>{a.lead_month}</td><td className="num">{a.leads}</td><td className="num">{a.converted}</td><td className="num">{pct(a.rate)}</td><td className="num">{a.new}</td><td className="num">{a.returning}</td><td className="num">{vnd(a.revenue)}</td></tr>)}</tbody></table>
        <h2>Chi tiết SĐT đã chốt ({rep.detail.length})</h2>
        <table><thead><tr><th>Kênh</th><th>Tháng lead</th><th>SĐT</th><th>Khách</th><th>Tour</th><th>KH</th><th>Phân loại</th><th className="num">Lần đi</th><th className="num">Khách</th><th className="num">DT lũy kế</th><th>Sale</th></tr></thead>
          <tbody>{rep.detail.map((d: any, i: number) => <tr key={i}><td>{d.channel}</td><td>{d.lead_month}</td><td>{d.phone}</td><td>{d.name}</td><td>{d.tour_code}<div className="muted">{d.tour}</div></td><td>{fmtD(d.start_date)}</td><td><Tag cls={d.kind === "Khách mới" ? "ok" : "navy"}>{d.kind}</Tag></td><td className="num">{d.trips}</td><td className="num">{d.pax}</td><td className="num">{vnd(d.revenue)}</td><td>{d.sales}</td></tr>)}</tbody></table>
      </>}
    </div>}

    {tab === "zalo" && <div className="panel wrap">
      <h2>Kết nối Zalo Official Account</h2>
      <Gate ok={!!zalo.oa}>{zalo.oa ? "Đã có access token Zalo OA – tin OA gửi trực tiếp; ZNS theo mẫu đã duyệt." : "Chưa cấu hình: CNTT dán ZALO_OA_ACCESS_TOKEN (+ ZALO_OA_REFRESH_TOKEN, ZALO_APP_ID, ZALO_APP_SECRET) vào Render → Environment. Tin gửi trong lúc chưa cấu hình được xếp hàng và tự gửi khi có token."}</Gate>
      <p className="muted">Webhook OA (Zalo for Developers → OA → Webhook): <code>https://vtos-api.onrender.com{zalo.webhook_url}</code> – sự kiện quan tâm / nhắn tin / chia sẻ SĐT tự tạo lead kênh “Zalo OA”. Mẫu ZNS: đặt ZALO_ZNS_TEMPLATES = “nhac_coc:&lt;id&gt;,xac_nhan_booking:&lt;id&gt;,cam_on:&lt;id&gt;” (mẫu phải được Zalo duyệt). Mẫu ZNS hiện có: {Object.keys(zalo.zns_templates || {}).join(", ") || "chưa có"}.</p>
      <div className="kpis">{Object.entries(zalo.messages || {}).map(([k, v]: any) => <div className="kpi" key={k}><b>{v}</b><span>{{ da_gui: "Đã gửi", loi: "Lỗi", cho_gui: "Chờ gửi", cho_cau_hinh: "Chờ cấu hình" }[k as string] || k}</span></div>)}</div>
      {["cntt", "ptgd_mkt", "gd_kd", "tgd"].includes(role) && <button className="act grey" onClick={() => post("/zalo/send-pending", {}, "Đã gửi tin chờ")}>Gửi tin đang chờ</button>}
      <table><thead><tr><th>Lúc</th><th>Kênh</th><th>SĐT / UID</th><th>Mục đích</th><th>Nội dung</th><th>Trạng thái</th><th>Người gửi</th><th>Phản hồi</th></tr></thead>
        <tbody>{msgs.length ? msgs.map((m) => <tr key={m.id}><td>{fmtDT(m.created_at)}</td><td>{m.kind.toUpperCase()}</td><td>{m.phone}{m.zalo_uid && <div className="muted">{m.zalo_uid}</div>}</td><td>{m.purpose}</td><td className="muted" style={{ maxWidth: 320 }}>{m.text || `mẫu ${m.template_id}`}</td><td><Tag cls={m.status === "da_gui" ? "ok" : m.status === "loi" ? "red" : "warn"}>{m.status}</Tag></td><td>{m.created_by}</td><td className="muted mono">{m.response}</td></tr>) : <tr><td colSpan={8} className="muted">Chưa có tin.</td></tr>}</tbody></table>
    </div>}
  </>);
}

export default function Page() { return <Shell><Leads /></Shell>; }
