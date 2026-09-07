"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, pct } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const RONG = { name: "", objective: "ra_lead", product_id: "", mang: "le", channels: [] as string[],
               from_date: today(), to_date: "", budget: "", target_leads: "", target_bookings: "",
               owner_id: "", note: "", nguon_tao: "nguoi", ai_ghi_chu: "" };

function Marketing() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const lapDuoc = ["ptgd_mkt", "nv_mkt", "cntt"].includes(role);
  const [meta, setMeta] = useState<any>({ muc_tieu: {}, kenh: {}, trang_thai: {}, mang: {} });
  const [ds, setDs] = useState<any[]>([]);
  const [sp, setSp] = useState<any[]>([]);
  const [nv, setNv] = useState<any[]>([]);
  const [chua, setChua] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [f, setF] = useState<any>({ ...RONG });
  const [hienForm, setHienForm] = useState(false);

  const load = useCallback(() => {
    api("/marketing/campaigns").then(setDs).catch((e) => toast(errMsg(e), true));
    api("/marketing/campaigns/lead-chua-gan").then(setChua).catch(() => {});
  }, []); // eslint-disable-line
  useEffect(() => {
    api("/marketing/meta").then(setMeta).catch(() => {});
    api("/products").then((r) => setSp(Array.isArray(r) ? r : r.rows || [])).catch(() => {});
    api("/users").then((r) => setNv(Array.isArray(r) ? r : [])).catch(() => {});
    load();
  }, [load]);

  const post = async (path: string, json?: any, method = "POST") => {
    try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiKenh = (k: string) => setF({ ...f, channels: f.channels.includes(k) ? f.channels.filter((x: string) => x !== k) : [...f.channels, k] });
  const luu = () => post("/marketing/campaigns", {
    ...f, product_id: f.product_id ? Number(f.product_id) : null, owner_id: f.owner_id ? Number(f.owner_id) : null,
    budget: Number(f.budget) || 0, target_leads: Number(f.target_leads) || 0,
    target_bookings: Number(f.target_bookings) || 0, to_date: f.to_date || null,
  }).then((r) => { if (r) { setF({ ...RONG }); setHienForm(false); } });

  const mau: Record<string, string> = { nhap: "grey", cho_duyet: "warn", dang_chay: "ok", tam_dung: "warn", ket_thuc: "grey", da_danh_gia: "ok" };

  return (<>
    <h1>Marketing · Chiến dịch</h1>
    <p className="muted">Chiến dịch là trục nối tiền – khách – doanh thu. Chi phí đọc từ đề nghị chi đã duyệt, lead đọc từ Nguồn khách, doanh thu đọc từ booking đã chốt — <b>không có ô nào để gõ tay ba con số đó</b>.</p>

    {lapDuoc && <button className="act" onClick={() => setHienForm(!hienForm)}>{hienForm ? "Đóng biểu mẫu" : "+ Lập chiến dịch mới"}</button>}

    {hienForm && <div className="panel">
      <h2>Biểu mẫu chiến dịch</h2>
      <div className="grid">
        <label>Tên chiến dịch *<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Tết 2026 – Miền Bắc" /></label>
        <label>Mục tiêu *<select value={f.objective} onChange={(e) => setF({ ...f, objective: e.target.value })}>
          {Object.entries(meta.muc_tieu).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Mảng kinh doanh *<select value={f.mang} onChange={(e) => setF({ ...f, mang: e.target.value })}>
          {Object.entries(meta.mang).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Sản phẩm / tuyến {f.objective === "ban_tour" && <b style={{ color: "var(--red)" }}>*</b>}
          <select value={f.product_id} onChange={(e) => setF({ ...f, product_id: e.target.value })}>
            <option value="">— không gắn sản phẩm —</option>
            {sp.map((p: any) => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>
        <label>Từ ngày *<input type="date" value={f.from_date} onChange={(e) => setF({ ...f, from_date: e.target.value })} /></label>
        <label>Đến ngày<input type="date" value={f.to_date} onChange={(e) => setF({ ...f, to_date: e.target.value })} /></label>
        <label>Ngân sách duyệt (đ) *<input type="number" value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} /></label>
        <label>Chỉ tiêu lead *<input type="number" value={f.target_leads} onChange={(e) => setF({ ...f, target_leads: e.target.value })} /></label>
        <label>Chỉ tiêu booking<input type="number" value={f.target_bookings} onChange={(e) => setF({ ...f, target_bookings: e.target.value })} /></label>
        <label>Người phụ trách<select value={f.owner_id} onChange={(e) => setF({ ...f, owner_id: e.target.value })}>
          <option value="">— chọn —</option>{nv.map((x: any) => <option key={x.id} value={x.id}>{x.full_name}</option>)}</select></label>
      </div>
      <div style={{ margin: "8px 0" }}><b>Kênh triển khai *</b>{" "}
        {Object.entries(meta.kenh).map(([k, v]: any) => <button key={k} className={"act " + (f.channels.includes(k) ? "" : "grey")}
          style={{ margin: "4px 6px 0 0", fontSize: 13 }} onClick={() => doiKenh(k)}>{v}</button>)}</div>
      <label>Ghi chú<textarea rows={2} style={{ width: "100%" }} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
      <div className="panel" style={{ background: "var(--bg2)" }}>
        <label><input type="checkbox" checked={f.nguon_tao === "ai"} onChange={(e) => setF({ ...f, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Đề xuất do trợ lý AI soạn</b></label>
        <p className="muted" style={{ margin: "4px 0" }}>Bản do AI soạn luôn dừng ở <b>Nháp</b> và phải người có thẩm quyền xem lại rồi duyệt — AI đề xuất, người quyết.</p>
        {f.nguon_tao === "ai" && <label>Căn cứ đề xuất (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={f.ai_ghi_chu}
          onChange={(e) => setF({ ...f, ai_ghi_chu: e.target.value })} placeholder="Dựa trên 3 kỳ gần nhất: chi phí/lead kênh Zalo thấp hơn Facebook 32%…" /></label>}
      </div>
      <button className="act" disabled={!f.name || !f.channels.length} onClick={luu}>Lưu ở trạng thái Nháp</button>
    </div>}

    {chua && chua.tong > 0 && <div className="panel" style={{ borderColor: "var(--orange)" }}>
      <b>{chua.tong} lead chưa gắn chiến dịch</b>
      <p className="muted">Gom theo ô chữ chiến dịch cũ. Hệ thống không tự đoán — chọn một chiến dịch bên dưới rồi bấm gán.</p>
      <div className="wrap"><table><thead><tr><th>Ô chữ cũ</th><th style={{ textAlign: "right" }}>Số lead</th><th>Gán vào</th></tr></thead><tbody>
        {chua.nhom.slice(0, 12).map((n: any) => <tr key={n.campaign_cu}>
          <td>{n.campaign_cu}</td><td style={{ textAlign: "right" }}>{n.so_lead}</td>
          <td>{lapDuoc && <select defaultValue="" onChange={(e) => { if (e.target.value) post(`/marketing/campaigns/${e.target.value}/gan-lead`, { campaign_cu: n.campaign_cu === "(không ghi)" ? "" : n.campaign_cu }); }}>
            <option value="">— chọn chiến dịch —</option>{ds.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select>}</td></tr>)}
      </tbody></table></div></div>}

    <h2>Danh sách chiến dịch</h2>
    <div className="panel wrap"><table><thead><tr>
      <th>Mã</th><th>Tên</th><th>Mục tiêu</th><th>Kênh</th><th>Thời gian</th>
      <th style={{ textAlign: "right" }}>Ngân sách</th><th style={{ textAlign: "right" }}>Đã chi</th>
      <th style={{ textAlign: "right" }}>Lead</th><th style={{ textAlign: "right" }}>Chốt</th>
      <th style={{ textAlign: "right" }}>CP/lead</th><th>Trạng thái</th><th></th></tr></thead><tbody>
      {ds.map((c) => { const k = c.ket_qua || {}; return [
        <tr key={c.id}>
          <td><b>{c.code}</b>{c.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</td>
          <td>{c.name}{c.san_pham && <div className="muted">{c.san_pham}</div>}</td>
          <td>{c.objective_ten}</td><td className="muted">{c.kenh_ten.join(" · ")}</td>
          <td>{fmtD(c.from_date)}{c.to_date ? ` → ${fmtD(c.to_date)}` : " → nay"}</td>
          <td style={{ textAlign: "right" }}>{vnd(c.budget)}</td>
          <td style={{ textAlign: "right", color: k.vuot_ngan_sach ? "var(--red)" : undefined }}>{vnd(k.chi_phi)}{k.chi_phi_treo > 0 && <div className="muted">treo {vnd(k.chi_phi_treo)}</div>}</td>
          <td style={{ textAlign: "right" }}>{k.so_lead}{c.target_leads > 0 && <div className="muted">/{c.target_leads}</div>}</td>
          <td style={{ textAlign: "right" }}>{k.chuyen_doi}{k.so_lead > 0 && <div className="muted">{pct(k.ty_le_chuyen_doi)}</div>}</td>
          <td style={{ textAlign: "right" }}>{k.chi_phi_moi_lead ? vnd(k.chi_phi_moi_lead) : "—"}</td>
          <td><Tag cls={mau[c.status] || "grey"}>{c.status_ten}</Tag></td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(mo === c.id ? null : c.id)}>{mo === c.id ? "Ẩn" : "Xem"}</button></td>
        </tr>,
        mo === c.id && <tr key={c.id + "d"}><td colSpan={12} style={{ background: "var(--bg2)" }}>
          <div className="kpis">
            <div className="kpi"><b>{vnd(k.doanh_thu)}</b><span>Doanh thu quy về</span></div>
            <div className="kpi"><b>{k.hieu_qua ? k.hieu_qua.toFixed(2) + "×" : "—"}</b><span>Doanh thu / chi phí</span></div>
            <div className="kpi"><b>{k.chi_phi_moi_booking ? vnd(k.chi_phi_moi_booking) : "—"}</b><span>Chi phí / booking</span></div>
            <div className="kpi"><b style={{ color: k.con_lai_ngan_sach < 0 ? "var(--red)" : undefined }}>{vnd(k.con_lai_ngan_sach)}</b><span>Còn lại ngân sách</span></div>
          </div>
          {c.nguon_tao === "ai" && c.ai_ghi_chu && <p><b>Căn cứ AI đề xuất:</b> {c.ai_ghi_chu}</p>}
          {c.evaluation && <p><b>Đánh giá kết thúc:</b> {c.evaluation}</p>}
          <p className="muted">Người lập {c.created_by}{c.approved_by && ` · Duyệt bởi ${c.approved_by}`}</p>
          {c.chuyen_duoc.map((s: string) => <button key={s} className="act" style={{ marginRight: 6 }} onClick={() => {
            if (s === "da_danh_gia") { const dg = prompt("Đánh giá kết thúc chiến dịch (bắt buộc):"); if (dg && dg.trim()) post(`/marketing/campaigns/${c.id}/chuyen-trang-thai`, { status: s, danh_gia: dg.trim() }); }
            else post(`/marketing/campaigns/${c.id}/chuyen-trang-thai`, { status: s });
          }}>→ {meta.trang_thai[s]}</button>)}
        </td></tr>,
      ]; })}
      {!ds.length && <tr><td colSpan={12} className="muted">Chưa có chiến dịch nào.</td></tr>}
    </tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Marketing /></Shell>; }
