"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT, getToken } from "@/lib/api";
import { Tag, Gate, errMsg } from "@/components/ui";
import BaoCaoChuyenDoi from "@/components/BaoCaoChuyenDoi";

const ST_CLS: Record<string, string> = { moi: "navy", dang_cham_soc: "warn", chot: "ok", mat: "" };

// DẤU NGUỒN QUẢNG CÁO của một lead — Chủ tịch chốt 08/10/2026: hiện CẢ lần chạm đầu lẫn lần chạm
// cuối, hai cột riêng. Lần đầu là kênh MANG KHÁCH ĐẾN, lần cuối là kênh CHỐT ĐƯỢC; chênh lệch
// giữa hai cột chính là chỗ cho thấy kênh nào đang nuôi quỹ khách mà không được ghi công.
// Ô trống in "–": chưa có dấu nào KHÁC với có dấu mà nền tảng rỗng.
function DauO({ d, ten }: { d: any; ten: Record<string, string> }) {
  if (!d) return <span className="muted">–</span>;
  const phu = d.ten_chien_dich || d.ma_chien_dich || "";
  return (<>
    <b>{ten[d.nen_tang] || d.nen_tang}</b>
    {phu && <div className="muted">{phu}</div>}
    {/* Giờ chạm rỗng là CHƯA BIẾT, không phải 0. Không lấy giờ VTOS ghi lấp vào: lấp là bịa ra
        một mốc khách chưa từng chạm, và mốc bịa đi thẳng vào phép đếm 30 / 60 / 90 ngày. */}
    <div className="muted">{d.cham_luc ? fmtDT(d.cham_luc) : "giờ chạm: nền tảng không gửi"}</div>
  </>);
}

function Leads() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [meta, setMeta] = useState<any>({ channels: [], status: {}, zalo: {}, nen_tang: {}, nguon_ghi: {} });
  const month0 = new Date().toISOString().slice(0, 7);
  const [tab, setTab] = useState("leads");
  // mở đúng tab khi vào từ menu bên trái (?tab=...)
  useEffect(() => { const q = new URLSearchParams(window.location.search).get("tab"); if (q) setTab(q); }, []);
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
  // PHẢI KHỚP `EDIT_ROLES` ở backend/app/api/v1/crm.py. Trước 08/10/2026 màn hình HẸP HƠN máy
  // chủ: tn_kd, tp_kd và nv_mkt được phép sửa nhưng không thấy nút nào — nên họ đi nhờ người
  // khác sửa hộ, và nhật ký ghi sai tên người sửa. Rộng hơn máy chủ thì ngược lại: bấm vào ăn
  // 403. Hai danh sách này là một luật, phép thử test_tc110 canh cho chúng không lệch nhau.
  const canEdit = ["nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "cntt", "tgd"].includes(role);
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
      <table><thead><tr><th>SĐT</th><th>Khách</th><th>Kênh</th><th>Chạm đầu</th><th>Chạm cuối</th><th>Tháng</th><th>Tour quan tâm</th><th>Trạng thái</th><th>Booking</th><th>Sale</th><th>Zalo</th><th>Liên hệ cuối</th><th></th></tr></thead>
        <tbody>{data.rows.length ? data.rows.map((l: any) => <tr key={l.id}><td><b>{l.phone}</b>{l.phone.length < 10 && <div className="muted">thiếu số</div>}</td><td>{l.name}</td><td>{l.channel}</td><td><DauO d={l.dau_cham_dau} ten={meta.nen_tang || {}} /></td><td><DauO d={l.dau_cham_cuoi} ten={meta.nen_tang || {}} />{l.so_lan_cham > 1 && <div className="muted">{l.so_lan_cham} lần chạm</div>}</td><td>{l.lead_month}</td><td className="muted">{l.interest}</td><td><Tag cls={ST_CLS[l.status] || ""}>{l.status_name}</Tag></td><td>{l.booking_code}<div className="muted">{l.booking_tour}</div></td><td>{l.sales_name}</td><td>{l.zalo_uid ? <Tag cls="ok">OA</Tag> : "–"}</td><td>{fmtDT(l.last_contact_at)}</td>
          <td style={{ whiteSpace: "nowrap" }}>{canEdit && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setEdit(l)}>sửa</button>} <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setZsend(l)}>Zalo</button></td></tr>) : <tr><td colSpan={13} className="muted">Chưa có lead – bấm “Nhập Excel” để nạp file của Marketing.</td></tr>}</tbody></table>
    </div>}

    {tab === "report" && <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}><label>Tháng tour khởi hành<input type="month" value={repMonth} onChange={(e) => setRepMonth(e.target.value)} /></label><button className="act grey" style={{ margin: 0 }} onClick={xlsx}>Xuất Excel (mẫu Marketing)</button>{rep && <span className="muted">Đối chiếu lúc {fmtDT(rep.as_of)} · lead các tháng {rep.lead_months.join(", ")}</span>}</div>
      {/* BẢNG NÀY KHÔNG CÒN VIẾT TAY Ở ĐÂY (18/9/2026). Không gian Marketing cần đúng bảng ấy; chép
          sang là có hai đầu, và sửa một đầu thì đầu kia lặng lẽ hiện số theo quy tắc cũ. Cả hai màn
          hình nay gọi chung components/BaoCaoChuyenDoi.tsx. */}
      <BaoCaoChuyenDoi rep={rep} />
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
