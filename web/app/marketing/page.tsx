"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, pct, soTien } from "@/lib/api";
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
  const [tab, setTab] = useState("chiendich");
  const [ns, setNs] = useState<any[]>([]);
  const [hm, setHm] = useState<any>({});
  const [moNs, setMoNs] = useState<number | null>(null);
  const [fn, setFn] = useState<any>({ period: new Date().toISOString().slice(0, 7), target_leads: "", target_revenue: "", rationale: "", lines: {} as Record<string, string>, nguon_tao: "nguoi", ai_ghi_chu: "" });
  const [hienNs, setHienNs] = useState(false);

  const load = useCallback(() => {
    api("/marketing/campaigns").then(setDs).catch((e) => toast(errMsg(e), true));
    api("/marketing/campaigns/lead-chua-gan").then(setChua).catch(() => {});
    api("/marketing/budgets").then(setNs).catch(() => {});
  }, []); // eslint-disable-line
  useEffect(() => {
    api("/marketing/meta").then(setMeta).catch(() => {});
    api("/products").then((r) => setSp(Array.isArray(r) ? r : r.rows || [])).catch(() => {});
    api("/users").then((r) => setNv(Array.isArray(r) ? r : [])).catch(() => {});
    api("/marketing/budgets/hang-muc").then(setHm).catch(() => {});
    const q = new URLSearchParams(window.location.search).get("tab"); if (q) setTab(q);
    load();
  }, [load]);

  const post = async (path: string, json?: any, method = "POST") => {
    try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiKenh = (k: string) => setF({ ...f, channels: f.channels.includes(k) ? f.channels.filter((x: string) => x !== k) : [...f.channels, k] });
  const luu = () => post("/marketing/campaigns", {
    ...f, product_id: f.product_id ? Number(f.product_id) : null, owner_id: f.owner_id ? Number(f.owner_id) : null,
    budget: soTien(f.budget), target_leads: Number(f.target_leads) || 0,
    target_bookings: Number(f.target_bookings) || 0, to_date: f.to_date || null,
  }).then((r) => { if (r) { setF({ ...RONG }); setHienForm(false); } });

  const mau: Record<string, string> = { nhap: "grey", cho_duyet: "warn", dang_chay: "ok", tam_dung: "warn", ket_thuc: "grey", da_danh_gia: "ok" };

  const luuNs = () => {
    const lines = Object.entries(fn.lines).filter(([, v]) => Number(v) > 0)
      .map(([hang_muc, v]) => ({ hang_muc, amount: Number(v) }));
    post("/marketing/budgets", { period: fn.period, target_leads: Number(fn.target_leads) || 0,
      target_revenue: soTien(fn.target_revenue), rationale: fn.rationale, lines,
      nguon_tao: fn.nguon_tao, ai_ghi_chu: fn.ai_ghi_chu })
      .then((r) => { if (r) { setFn({ ...fn, rationale: "", lines: {} }); setHienNs(false); } });
  };

  return (<>
    <h1>Marketing</h1>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
      {[["chiendich", "Chiến dịch"], ["ngansach", "Kế hoạch & ngân sách"]].map(([k, l]) =>
        <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
    </div>

    {tab === "ngansach" && <>
      <p className="muted">Màn hình này chỉ giữ phần <b>dự toán</b>. Số <b>đã chi</b> đọc từ đề nghị chi đã duyệt — không có ô nào để gõ tay. Chi vượt phần còn lại của hạng mục sẽ tự bật cờ ngoài dự toán và cần hai chữ ký; hệ thống không chặn cứng việc chi, nhưng không cho chi âm thầm.</p>
      {lapDuoc && <button className="act" onClick={() => setHienNs(!hienNs)}>{hienNs ? "Đóng biểu mẫu" : "+ Lập ngân sách kỳ"}</button>}
      {hienNs && <div className="panel"><h2>Biểu mẫu ngân sách kỳ</h2>
        <div className="grid">
          <label>Kỳ *<input value={fn.period} onChange={(e) => setFn({ ...fn, period: e.target.value })} placeholder="2026-09 hoặc 2026-Q4" /></label>
          <label>Mục tiêu lead *<input type="number" value={fn.target_leads} onChange={(e) => setFn({ ...fn, target_leads: e.target.value })} /></label>
          <label>Mục tiêu doanh thu quy đổi<input type="number" value={fn.target_revenue} onChange={(e) => setFn({ ...fn, target_revenue: e.target.value })} /></label>
        </div>
        <b>Dự toán theo hạng mục *</b>
        <div className="grid">{Object.entries(hm).map(([k, v]: any) =>
          <label key={k}>{v}<input type="number" value={fn.lines[k] || ""} onChange={(e) => setFn({ ...fn, lines: { ...fn.lines, [k]: e.target.value } })} /></label>)}</div>
        <p className="muted">Tổng dự toán: <b>{vnd(Object.values(fn.lines).reduce((s: number, v: any) => s + (Number(v) || 0), 0))}</b> — tổng tự cộng, không có ô gõ tay.</p>
        <label>Căn cứ lập ngân sách *<textarea rows={2} style={{ width: "100%" }} value={fn.rationale}
          onChange={(e) => setFn({ ...fn, rationale: e.target.value })} placeholder="Vì sao con số này – kỳ sau còn đối chiếu lại được" /></label>
        <div className="panel" style={{ background: "var(--bg2)" }}>
          <label><input type="checkbox" checked={fn.nguon_tao === "ai"} onChange={(e) => setFn({ ...fn, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Đề xuất do trợ lý AI soạn</b></label>
          {fn.nguon_tao === "ai" && <label>Căn cứ đề xuất (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={fn.ai_ghi_chu} onChange={(e) => setFn({ ...fn, ai_ghi_chu: e.target.value })} /></label>}
        </div>
        <button className="act" disabled={!fn.rationale} onClick={luuNs}>Lưu ở trạng thái Nháp</button>
      </div>}

      {ns.map((b) => { const g = b.bang || {}; return <div className="panel" key={b.id}>
        <h2>Kỳ {b.period} · <Tag cls={b.status === "hieu_luc" ? "ok" : b.status === "cho_duyet" ? "warn" : "grey"}>{b.status_ten}</Tag>
          {b.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</h2>
        <div className="kpis">
          <div className="kpi"><b>{vnd(g.tong_du_toan)}</b><span>Dự toán</span></div>
          <div className="kpi"><b>{vnd(g.tong_da_chi)}</b><span>Đã chi</span></div>
          <div className="kpi"><b>{vnd(g.tong_treo)}</b><span>Đang treo (đã cam kết)</span></div>
          <div className="kpi"><b style={{ color: g.tong_con_lai < 0 ? "var(--red)" : undefined }}>{vnd(g.tong_con_lai)}</b><span>Còn lại</span></div>
        </div>
        <div className="wrap"><table><thead><tr><th>Hạng mục</th><th style={{ textAlign: "right" }}>Dự toán</th>
          <th style={{ textAlign: "right" }}>Đã chi</th><th style={{ textAlign: "right" }}>Đang treo</th>
          <th style={{ textAlign: "right" }}>Còn lại</th></tr></thead><tbody>
          {(g.rows || []).map((r: any) => <tr key={r.hang_muc}>
            <td>{r.ten}</td><td style={{ textAlign: "right" }}>{vnd(r.du_toan)}</td>
            <td style={{ textAlign: "right" }}>{vnd(r.da_chi)}</td><td style={{ textAlign: "right" }}>{vnd(r.dang_treo)}</td>
            <td style={{ textAlign: "right", color: r.vuot ? "var(--red)" : undefined }}><b>{vnd(r.con_lai)}</b>{r.vuot && <Tag cls="red">vượt</Tag>}</td></tr>)}
          {g.chua_phan_muc && (g.chua_phan_muc.da_chi > 0 || g.chua_phan_muc.dang_treo > 0) && <tr>
            <td><i>Chi marketing chưa gán hạng mục</i></td><td style={{ textAlign: "right" }}>—</td>
            <td style={{ textAlign: "right" }}>{vnd(g.chua_phan_muc.da_chi)}</td>
            <td style={{ textAlign: "right" }}>{vnd(g.chua_phan_muc.dang_treo)}</td>
            <td style={{ textAlign: "right" }}><Tag cls="warn">cần gán</Tag></td></tr>}
          {(g.ngoai_ngan_sach || []).map((x: any) => <tr key={x.hang_muc}>
            <td><i>{x.ten} — ngoài ngân sách kỳ</i></td><td style={{ textAlign: "right" }}>—</td>
            <td style={{ textAlign: "right" }}>{vnd(x.da_chi)}</td><td style={{ textAlign: "right" }}>{vnd(x.dang_treo)}</td>
            <td style={{ textAlign: "right" }}><Tag cls="warn">ngoài</Tag></td></tr>)}
        </tbody></table></div>
        <p className="muted">Chi phí/lead kế hoạch <b>{vnd(g.chi_phi_lead_ke_hoach)}</b> · thực tế <b>{vnd(g.chi_phi_lead_thuc_te)}</b> ({g.so_lead} lead trong kỳ) · Mục tiêu {b.target_leads} lead</p>
        <p className="muted"><b>Căn cứ:</b> {b.rationale}</p>
        {b.ai_ghi_chu && <p className="muted"><b>Căn cứ AI:</b> {b.ai_ghi_chu}</p>}
        <p className="muted">Người lập {b.created_by}{b.approved_by && ` · Duyệt bởi ${b.approved_by}`}</p>
        {b.status === "nhap" && lapDuoc && <button className="act" onClick={() => post(`/marketing/budgets/${b.id}/trinh`)}>Trình duyệt</button>}
        {b.status === "cho_duyet" && ["tgd", "chutich"].includes(role) && <button className="act" onClick={() => post(`/marketing/budgets/${b.id}/duyet`)}>Duyệt ngân sách</button>}
      </div>; })}
      {!ns.length && <p className="muted">Chưa có ngân sách kỳ nào.</p>}
    </>}

    {tab === "chiendich" && <>
    <h2>Chiến dịch</h2>
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
    </>}
  </>);
}
export default function Page() { return <Shell><Marketing /></Shell>; }
