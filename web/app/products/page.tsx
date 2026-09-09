"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, soTien } from "@/lib/api";
import { TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, errMsg } from "@/components/ui";

const WD = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
const EMPTY = { code: "", name: "", tour_type: "le_noi_dia", departure_point: "TP HCM", region: "", country: "", sale_point: "TP HCM", transport: "Xe", vehicle_type: "45", length_text: "", days: "3", reference_price: "", deposit_pct: "30", days_to_close: "3", requires_confirmation: false, program: "", services: "", status: "active", cost_structure: {} as Record<string, any>, cost_lines: [] as any[] };

function Products() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const canEdit = ["nv_dh", "tp_dh", "cntt"].includes(role);
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<any>(null);
  const [f, setF] = useState<any>(EMPTY);
  const [editing, setEditing] = useState(false);
  const [open, setOpen] = useState<any>({ start_date: "", date_to: "", weekdays: [] as number[], seats: "40", price_adl: "", price_chd: "", price_inf: "", note: "" });
  const load = useCallback(() => api(`/products?q=${encodeURIComponent(q)}`).then(setRows).catch((e) => toast(errMsg(e), true)), [q, toast]);
  useEffect(() => { load(); }, [load]);
  const view = async (id: number) => { try { const p = await api(`/products/${id}`); setSel(p); setEditing(false); if (!open.price_adl) setOpen({ ...open, price_adl: String(p.reference_price || "") }); } catch (e) { toast(errMsg(e), true); } };
  const startEdit = (p?: any) => { setEditing(true); setF(p ? { ...p, days: String(p.days), reference_price: String(p.reference_price), deposit_pct: String(p.deposit_pct), days_to_close: String(p.days_to_close) } : EMPTY); };
  const save = async () => {
    const d = { ...f, days: Number(f.days) || 1, reference_price: soTien(f.reference_price), deposit_pct: Number(f.deposit_pct) || 0, days_to_close: Number(f.days_to_close) || 0,
      cost_structure: Object.fromEntries(Object.entries(f.cost_structure || {}).map(([k, v]) => [k, Number(v) || 0])),
      cost_lines: (f.cost_lines || []).filter((l: any) => l.mo_ta || l.don_gia).map((l: any) => ({ ...l, don_gia: soTien(l.don_gia), sl: Number(l.sl) || 1, so_tien: Number(l.so_tien) || 0 })) };
    try { const p = f.id ? await api(`/products/${f.id}`, { method: "PUT", json: d }) : await api("/products", { method: "POST", json: d }); toast("Đã lưu sản phẩm " + p.code); setEditing(false); load(); view(p.id); } catch (e) { toast(errMsg(e), true); }
  };
  const openTour = async () => {
    if (!sel) return;
    const j: any = { start_date: open.start_date, seats: Number(open.seats) || 0, price_adl: open.price_adl ? Number(open.price_adl) : null, price_chd: Number(open.price_chd) || 0, price_inf: Number(open.price_inf) || 0, note: open.note };
    if (open.date_to && open.weekdays.length) { j.date_to = open.date_to; j.weekdays = open.weekdays; }
    try { const r = await api(`/products/${sel.id}/open-tour`, { method: "POST", json: j }); toast(r.message); view(sel.id); load(); if (r.tours.length === 1) location.href = `/tours/${r.tours[0].id}`; } catch (e) { toast(errMsg(e), true); }
  };
  const items: [string, string][] = sel?.cost_items || f.cost_items || [["ve_may_bay", "Vé máy bay"], ["land", "Land"], ["phi_lsq", "Phí LSQ"], ["bao_hiem", "Bảo hiểm"], ["qua_tang", "Quà tặng"], ["phi_tl", "Phí TL"], ["hop_doan", "Họp đoàn"], ["dieu_hanh", "Điều hành"], ["dich_thuat", "Dịch thuật"], ["hoa_hong_ve", "Hoa hồng vé"], ["phi_ck", "Phí CK"], ["khac", "Khác"]];
  return (<>
    <h1>Sản phẩm tour (tour cha)</h1>
    <p className="muted">Sản phẩm giữ cơ cấu chi phí chuẩn (cố định / theo khách) và chương trình. <b>Mở chuyến</b> từ sản phẩm → mã tour theo quy ước Vietrip (MÃSP.NNddmmyy), dự toán 3 con số tự sinh, qua cổng biên 10% và luồng duyệt của VTOS. Đồng bộ từ Vietrip: {rows.filter((r) => r.source === "vietrip").length} sản phẩm.</p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
      <input placeholder="Tìm mã / tên sản phẩm…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 320 }} />
      {canEdit && <button className="act" style={{ margin: 0 }} onClick={() => { setSel(null); startEdit(); }}>+ Tạo sản phẩm</button>}
    </div>
    <div className="grid" style={{ alignItems: "start" }}>
      <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>PT</th><th className="num">Ngày</th><th className="num">Giá TK</th><th className="num">CP cố định</th><th className="num">CP/khách</th><th className="num">Chuyến</th><th></th></tr></thead>
        <tbody>{rows.map((p) => <tr key={p.id} style={{ opacity: p.status === "active" ? 1 : 0.5 }}><td><b>{p.code}</b></td><td>{p.name}</td><td>{TOUR_TYPES[p.tour_type]}</td><td>{p.transport}{p.vehicle_type && ` ${p.vehicle_type}`}</td><td className="num">{p.days}</td><td className="num">{vnd(p.reference_price)}</td><td className="num">{vnd(p.fixed_cost)}</td><td className="num">{vnd(p.var_cost_per_pax)}</td><td className="num">{p.n_tours}</td>
          <td><button className="act grey" style={{ margin: 0 }} onClick={() => view(p.id)}>Xem</button></td></tr>)}</tbody></table></div>
      {(sel || editing) && <div className="panel">
        {editing ? <>
          <h2>{f.id ? `Sửa sản phẩm ${f.code}` : "Tạo sản phẩm"}</h2>
          <div className="grid">
            <label>Mã sản phẩm<input value={f.code} disabled={!!f.id} onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} placeholder="PT001" /></label>
            <label>Tên<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></label>
            <label>Loại<select value={f.tour_type} onChange={(e) => setF({ ...f, tour_type: e.target.value })}>{Object.entries(TOUR_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Điểm khởi hành<input value={f.departure_point} onChange={(e) => setF({ ...f, departure_point: e.target.value })} /></label>
            <label>Vùng / Quốc gia<input value={f.region} onChange={(e) => setF({ ...f, region: e.target.value })} placeholder="Vùng" /><input value={f.country} onChange={(e) => setF({ ...f, country: e.target.value })} placeholder="Quốc gia" /></label>
            <label>Phương tiện / Loại xe<input value={f.transport} onChange={(e) => setF({ ...f, transport: e.target.value })} /><input value={f.vehicle_type} onChange={(e) => setF({ ...f, vehicle_type: e.target.value })} placeholder="45 / 29 / 16" /></label>
            <label>Độ dài (3N2Đ) / Số ngày<input value={f.length_text} onChange={(e) => setF({ ...f, length_text: e.target.value })} /><input type="number" value={f.days} onChange={(e) => setF({ ...f, days: e.target.value })} /></label>
            <label>Giá tham khảo (đ/khách)<input type="number" value={f.reference_price} onChange={(e) => setF({ ...f, reference_price: e.target.value })} /></label>
            <label>% cọc / Số ngày đóng tour<input type="number" value={f.deposit_pct} onChange={(e) => setF({ ...f, deposit_pct: e.target.value })} /><input type="number" value={f.days_to_close} onChange={(e) => setF({ ...f, days_to_close: e.target.value })} /></label>
            <label><input type="checkbox" checked={!!f.requires_confirmation} onChange={(e) => setF({ ...f, requires_confirmation: e.target.checked })} /> Cần xác nhận khi đặt</label>
            <label>Trạng thái<select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="active">Hoạt động</option><option value="inactive">Ngừng</option></select></label>
          </div>
          <h3>Cơ cấu chi phí tham khảo (đ/khách – 11 khoản theo Vietrip)</h3>
          <div className="grid">{items.map(([k, l]) => <label key={k}>{l}<input type="number" value={f.cost_structure?.[k] ?? ""} onChange={(e) => setF({ ...f, cost_structure: { ...f.cost_structure, [k]: e.target.value } })} /></label>)}</div>
          <h3>Dòng chi phí theo NCC (cố định = cả chuyến; theo khách = đ/khách) – dự toán 3 con số lấy từ đây</h3>
          <div className="wrap"><table><thead><tr><th>Loại DV</th><th>NCC (MST)</th><th>Cố định / theo khách</th><th>Mô tả</th><th>Đơn giá</th><th>SL</th><th>Thành tiền (cố định)</th><th></th></tr></thead>
            <tbody>{(f.cost_lines || []).map((l: any, i: number) => <tr key={i}>
              <td><input value={l.loai || ""} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, loai: e.target.value }; setF({ ...f, cost_lines: c }); }} placeholder="GUIDE/HOTEL/BUS…" style={{ width: 90 }} /></td>
              <td><input value={l.ncc || ""} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, ncc: e.target.value }; setF({ ...f, cost_lines: c }); }} /></td>
              <td><select value={l.kind || "co_dinh"} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, kind: e.target.value }; setF({ ...f, cost_lines: c }); }}><option value="co_dinh">Cố định</option><option value="theo_khach">Theo khách</option></select></td>
              <td><input value={l.mo_ta || ""} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, mo_ta: e.target.value }; setF({ ...f, cost_lines: c }); }} /></td>
              <td><input type="number" value={l.don_gia ?? ""} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, don_gia: e.target.value }; setF({ ...f, cost_lines: c }); }} style={{ width: 110 }} /></td>
              <td><input type="number" value={l.sl ?? 1} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, sl: e.target.value }; setF({ ...f, cost_lines: c }); }} style={{ width: 60 }} /></td>
              <td><input type="number" value={l.so_tien ?? ""} onChange={(e) => { const c = [...f.cost_lines]; c[i] = { ...l, so_tien: e.target.value }; setF({ ...f, cost_lines: c }); }} style={{ width: 120 }} /></td>
              <td><button className="act grey" style={{ margin: 0 }} onClick={() => setF({ ...f, cost_lines: f.cost_lines.filter((_: any, j: number) => j !== i) })}>×</button></td></tr>)}</tbody></table></div>
          <button className="act grey" onClick={() => setF({ ...f, cost_lines: [...(f.cost_lines || []), { loai: "", ncc: "", kind: "co_dinh", mo_ta: "", don_gia: "", sl: 1, so_tien: "" }] })}>+ Dòng chi phí</button>
          <label>Chương trình / thông tin giá<textarea rows={6} value={f.program} onChange={(e) => setF({ ...f, program: e.target.value })} /></label>
          <button className="act" onClick={save}>Lưu sản phẩm</button> <button className="act grey" onClick={() => setEditing(false)}>Hủy</button>
        </> : sel && <>
          <h2>{sel.code} · {sel.name} <Tag cls={sel.status === "active" ? "ok" : ""}>{sel.status === "active" ? "Hoạt động" : "Ngừng"}</Tag> {sel.source === "vietrip" && <Tag cls="navy">Vietrip</Tag>}</h2>
          <p className="muted">{TOUR_TYPES[sel.tour_type]} · KH {sel.departure_point} · {sel.transport} {sel.vehicle_type} · {sel.length_text || `${sel.days} ngày`} · Giá TK <b>{vnd(sel.reference_price)}</b> · cọc {sel.deposit_pct}% · đóng tour trước {sel.days_to_close} ngày{sel.operator_name && ` · ĐH phụ trách ${sel.operator_name}`}</p>
          <div className="kpis"><div className="kpi"><b>{vnd(sel.fixed_cost)}</b><span>Chi phí cố định/chuyến</span></div><div className="kpi"><b>{vnd(sel.var_cost_per_pax)}</b><span>Chi phí/khách</span></div><div className="kpi"><b>{sel.tours?.length || 0}</b><span>Chuyến gần đây</span></div></div>
          {canEdit && <button className="act grey" onClick={() => startEdit(sel)}>Sửa sản phẩm</button>}
          <details><summary><b>Cơ cấu chi phí & dòng NCC</b></summary>
            <table><tbody>{items.filter(([k]) => Number(sel.cost_structure?.[k])).map(([k, l]) => <tr key={k}><td>{l}</td><td className="num">{vnd(sel.cost_structure[k])}</td></tr>)}</tbody></table>
            {sel.cost_lines?.length > 0 && <div className="wrap"><table><thead><tr><th>Loại</th><th>NCC</th><th>Kiểu</th><th>Mô tả</th><th className="num">Đơn giá</th><th className="num">SL</th><th className="num">Thành tiền</th></tr></thead>
              <tbody>{sel.cost_lines.map((l: any, i: number) => <tr key={i}><td>{l.loai}</td><td>{l.ncc}</td><td>{l.kind === "theo_khach" ? "Theo khách" : "Cố định"}</td><td>{l.mo_ta}</td><td className="num">{vnd(l.don_gia)}</td><td className="num">{l.sl}</td><td className="num">{vnd(l.so_tien || l.don_gia * l.sl)}</td></tr>)}</tbody></table></div>}
          </details>
          {sel.program && <details><summary><b>Chương trình / thông tin giá</b></summary><pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{sel.program}</pre></details>}
          {canEdit && <><h3>Mở chuyến từ sản phẩm</h3><div className="grid">
            <label>Ngày khởi hành<input type="date" value={open.start_date} onChange={(e) => setOpen({ ...open, start_date: e.target.value })} /></label>
            <label>Số chỗ mở bán<input type="number" value={open.seats} onChange={(e) => setOpen({ ...open, seats: e.target.value })} /></label>
            <label>Giá ADL / CHD / INF<input type="number" value={open.price_adl} onChange={(e) => setOpen({ ...open, price_adl: e.target.value })} placeholder={String(sel.reference_price)} /><input type="number" value={open.price_chd} onChange={(e) => setOpen({ ...open, price_chd: e.target.value })} placeholder="CHD" /><input type="number" value={open.price_inf} onChange={(e) => setOpen({ ...open, price_inf: e.target.value })} placeholder="INF" /></label>
            <label>Lịch lặp đến ngày (tùy chọn)<input type="date" value={open.date_to} onChange={(e) => setOpen({ ...open, date_to: e.target.value })} /></label>
            <div><label>Thứ khởi hành (lịch lặp)</label>{WD.map((w, i) => <label key={w} style={{ display: "inline-block", marginRight: 8 }}><input type="checkbox" checked={open.weekdays.includes(i)} onChange={(e) => setOpen({ ...open, weekdays: e.target.checked ? [...open.weekdays, i] : open.weekdays.filter((x: number) => x !== i) })} /> {w}</label>)}</div>
            <label>Ghi chú (lời giải trình bước khởi tạo)<input value={open.note} onChange={(e) => setOpen({ ...open, note: e.target.value })} /></label>
          </div><button className="act" disabled={!open.start_date} onClick={openTour}>Mở chuyến (nháp → trình TP Điều hành)</button></>}
          <h3>Chuyến gần đây</h3>
          <div className="wrap"><table><thead><tr><th>Mã</th><th>KH – KT</th><th>Trạng thái</th><th className="num">Chỗ</th><th className="num">Đã bán</th><th className="num">Giá</th></tr></thead>
            <tbody>{(sel.tours || []).map((t: any) => <tr key={t.id}><td><Link href={`/tours/${t.id}`}>{t.code}</Link></td><td>{fmtD(t.start_date)} – {fmtD(t.end_date)}</td><td>{TOUR_STATUS[t.status] || t.status}</td><td className="num">{t.seats_open}</td><td className="num">{t.booked}</td><td className="num">{vnd(t.price)}</td></tr>)}</tbody></table></div>
        </>}
      </div>}
    </div>
  </>);
}
export default function Page() { return <Shell><Products /></Shell>; }
