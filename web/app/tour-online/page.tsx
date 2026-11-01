"use client";
/** TR-1 · TOUR TRÊN CỔNG KHÁCH (Chủ tịch duyệt 01–02/11/2026).
 *  Ảnh, lịch trình, bảng giá, bao gồm / không bao gồm, quy định KHÔNG nhập ở đây: máy đọc thẳng từ trang tour trên
 *  vietourist.com.vn (chỉ đọc, không sửa web). Ở đây chỉ:
 *   · Ghép: tour trên web ↔ sản phẩm crm (máy gợi ý theo tên + số ngày, TP Điều hành / TP-GĐ Kinh doanh xác nhận).
 *   · Hồ sơ cổng: điểm đến, 3–5 điểm nổi bật, Wellness & retreat, phương tiện (Điều hành / Marketing).
 *   · Công tắc thanh toán: chung (Chủ tịch / TGĐ) + từng sản phẩm. Đóng → khách chỉ «Gửi yêu cầu giữ chỗ».
 *   · Đơn đặt online + yêu cầu hóa đơn GTGT công ty (Kế toán đánh dấu đã xuất).
 *  Ma trận quản lý do máy chủ trả về (ma_tran) — màn chỉ hiện, không tự quyết quyền. */
import { useEffect, useMemo, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const luc = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");
const VAI: Record<string, string> = { chutich: "Chủ tịch", tgd: "TGĐ", bks: "BKS", nv_dh: "NV Điều hành", tp_dh: "TP Điều hành", nv_kd: "NV KD",
  tn_kd: "TN KD", tp_kd: "TP KD", gd_kd: "GĐ KD", sales_admin: "Sales admin", nv_mkt: "NV Marketing", ptgd_mkt: "PTGĐ Marketing", ketoan: "Kế toán", robot_ks: "Robot Kiểm soát (chỉ đọc)" };

function Trang() {
  const { toast } = useShell();
  const [x, setX] = useState<any>(null);
  const [tab, setTab] = useState<"sp" | "web" | "don" | "mt">("sp");
  const [tim, setTim] = useState(""); const [loc, setLoc] = useState("");
  const [sua, setSua] = useState<any>(null);
  const [web, setWeb] = useState<any[] | null>(null);
  const [don, setDon] = useState<any[] | null>(null); const [chiVat, setChiVat] = useState(false);
  const [busy, setBusy] = useState(false);
  const tai = () => api("/tour-online").then(setX).catch((e) => toast(errMsg(e), true));
  useEffect(() => { tai(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (tab === "don" && x?.duoc?.don) api(`/tour-online/don?chi_vat=${chiVat}`).then((r) => setDon(r.don)).catch((e) => toast(errMsg(e), true)); }, [tab, chiVat]);  // eslint-disable-line react-hooks/exhaustive-deps
  const lam = async (f: () => Promise<any>) => { setBusy(true); try { const r = await f(); if (r?.message) toast(r.message); await tai(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } };
  const taiWeb = async () => { setBusy(true); setWeb(null); try { setWeb((await api("/tour-online/web")).web); } catch (e) { toast(errMsg(e), true); setWeb([]); } finally { setBusy(false); } };

  const sps: any[] = x?.san_pham || [];
  const ds = useMemo(() => {
    const k = tim.trim().toLowerCase();
    return sps.filter((p) => (!k || `${p.ma} ${p.ten} ${p.diem_den_suy}`.toLowerCase().includes(k))
      && (!loc || (loc === "chua_ghep" ? !p.link_web : loc === "loi" ? !!p.web.loi : loc === "mo_tt" ? p.mo_thanh_toan : loc === "co_chuyen" ? p.so_chuyen > 0 : true)));
  }, [sps, tim, loc]);
  if (!x) return <p>Đang tải…</p>;
  const duoc = x.duoc || {};

  return (<>
    <h1>Tour trên cổng khách</h1>
    <p className="muted">Ảnh, lịch trình, bảng giá, bao gồm / không bao gồm và quy định đọc thẳng từ trang tour trên vietourist.com.vn (chỉ đọc, không sửa web) — không nhập lại ở đây.
      Ở đây: ghép tour web ↔ sản phẩm, hồ sơ cổng, công tắc thanh toán, đơn đặt online. Khách đặt tại kh.vietourist.vn/tours.</p>
    <div className="panel" style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
      <b>Thanh toán trực tuyến tour (chung):</b>
      {x.tt_chung ? <Tag cls="ok">Đang mở</Tag> : <Tag cls="grey">Đang đóng — khách chỉ gửi yêu cầu giữ chỗ</Tag>}
      {duoc.tt_chung && <button className="act grey" disabled={busy} onClick={() => lam(() => api("/tour-online/thanh-toan-chung", { method: "POST", json: { bat: !x.tt_chung } }))}>
        {x.tt_chung ? "Đóng thanh toán chung" : "Mở thanh toán chung"}</button>}
      <span className="muted" style={{ fontSize: 13 }}>Khách đặt online được khi công tắc chung VÀ công tắc của sản phẩm cùng mở.</span>
    </div>
    <div style={{ display: "flex", gap: 6, margin: "8px 0", flexWrap: "wrap" }}>{([["sp", `Sản phẩm (${sps.length})`], ...(duoc.sua || duoc.ghep ? [["web", "Tour trên web · ghép"]] : []),
      ...(duoc.don ? [["don", "Đơn đặt online"]] : []), ["mt", "Ma trận quản lý"]] as [typeof tab, string][]).map(([k, t]) =>
      <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} aria-pressed={tab === k} onClick={() => setTab(k)}>{t}</button>)}</div>

    {tab === "sp" && <div className="panel">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <input placeholder="Mã, tên, điểm đến…" value={tim} onChange={(e) => setTim(e.target.value)} style={{ minWidth: 220 }} />
        <select value={loc} onChange={(e) => setLoc(e.target.value)}><option value="">Tất cả</option><option value="co_chuyen">Có chuyến mở bán</option>
          <option value="chua_ghep">Chưa ghép web</option><option value="loi">Đọc web lỗi</option><option value="mo_tt">Đang mở thanh toán</option></select>
        <span className="muted">{ds.length} sản phẩm</span></div>
      <div className="wrap"><table><thead><tr><th>Sản phẩm</th><th>Loại</th><th>Chuyến</th><th>Nội dung web</th><th>Hồ sơ cổng</th><th>Thanh toán</th><th /></tr></thead>
        <tbody>{ds.map((p) => <tr key={p.id}>
          <td><b>{p.ma}</b><br />{p.ten}</td>
          <td>{p.loai === "doan" ? "Đoàn riêng" : "Ghép"} · {p.nuoc_ngoai ? "Nước ngoài" : "Trong nước"}</td>
          <td>{p.so_chuyen}</td>
          <td style={{ maxWidth: 260 }}>{p.link_web ? <>
            <a href={p.link_web} target="_blank" rel="noopener noreferrer">{p.web.ten || "Trang tour"}</a><br />
            <small className="muted">{p.web.so_anh} ảnh · {p.web.so_ngay} ngày · {p.web.so_bao_gom} mục bao gồm · {luc(p.web.cap_nhat_luc)}</small>
            {p.web.loi && <><br /><Tag cls="red">Lỗi: {p.web.loi}</Tag></>}</> : <span className="muted">Chưa ghép</span>}</td>
          <td><small>{p.diem_den || <i className="muted">{p.diem_den_suy} (máy suy)</i>}{p.wellness ? " · Wellness" : ""}<br />
            {(p.phuong_tien_ds.length ? p.phuong_tien_ds : p.phuong_tien_suy).map((k: string) => x.phuong_tien[k]).join(", ")}
            {p.noi_bat.length ? ` · ${p.noi_bat.length} điểm nổi bật` : ""}</small></td>
          <td>{p.mo_thanh_toan ? <Tag cls="ok">Mở</Tag> : <Tag cls="grey">Đóng</Tag>}
            {duoc.ghep && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-online/${p.id}/thanh-toan`, { method: "POST", json: { bat: !p.mo_thanh_toan } }))}>{p.mo_thanh_toan ? "Đóng" : "Mở"}</button>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{duoc.sua && <button className="act grey" onClick={() => setSua({ id: p.id, ma: p.ma, diem_den: p.diem_den, noi_bat: p.noi_bat.join("\n"), wellness: p.wellness, phuong_tien_ds: p.phuong_tien_ds })}>Sửa hồ sơ</button>}
            {duoc.sua && p.link_web && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-online/${p.id}/doc-web`, { method: "POST" }))}>Đọc lại web</button>}
            {duoc.ghep && <button className="act grey" disabled={busy} onClick={() => { const u = window.prompt(`Link trang tour trên vietourist.com.vn cho ${p.ma} (để trống = bỏ ghép)`, p.link_web || ""); if (u !== null) lam(() => api(`/tour-online/${p.id}/ghep-web`, { method: "POST", json: { link_web: u.trim() } })); }}>Ghép link</button>}</td>
        </tr>)}</tbody></table></div>
    </div>}

    {sua && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
      <h3 style={{ marginTop: 0 }}>Hồ sơ cổng · {sua.ma}</h3>
      <label>Điểm đến (trống = máy suy từ tên)<input value={sua.diem_den} onChange={(e) => setSua({ ...sua, diem_den: e.target.value })} /></label>
      <label>Điểm nổi bật (3–5 dòng ngắn, mỗi dòng một ý)<textarea rows={5} value={sua.noi_bat} onChange={(e) => setSua({ ...sua, noi_bat: e.target.value })} /></label>
      <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={sua.wellness} onChange={(e) => setSua({ ...sua, wellness: e.target.checked })} />Wellness &amp; retreat</label>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>Phương tiện: {Object.entries(x.phuong_tien).map(([k, t]) =>
        <label key={k} style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={sua.phuong_tien_ds.includes(k)}
          onChange={(e) => setSua({ ...sua, phuong_tien_ds: e.target.checked ? [...sua.phuong_tien_ds, k] : sua.phuong_tien_ds.filter((y: string) => y !== k) })} />{t as string}</label>)}</div>
      <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
        <button className="act teal" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/${sua.id}/cong`, { method: "PUT", json: { diem_den: sua.diem_den,
          noi_bat: sua.noi_bat.split("\n").map((s: string) => s.trim()).filter(Boolean), wellness: sua.wellness, phuong_tien_ds: sua.phuong_tien_ds } }); setSua(null); return r; })}>Lưu</button>
        <button className="act grey" onClick={() => setSua(null)}>Hủy</button></div>
    </div>}

    {tab === "web" && <div className="panel">
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
        <button className="act teal" disabled={busy} onClick={taiWeb}>{busy && !web ? "Đang đọc vietourist.com.vn…" : "Đọc danh sách tour trên web"}</button>
        <span className="muted" style={{ fontSize: 13 }}>Chỉ đọc hai trang danh sách tour trong nước / nước ngoài. Máy gợi ý sản phẩm giống tên + cùng số ngày; người có quyền xác nhận mới ghép.</span></div>
      {web && <div className="wrap"><table><thead><tr><th>Tour trên web</th><th>Đã ghép</th><th>Gợi ý</th><th /></tr></thead>
        <tbody>{web.map((w) => <tr key={w.url}><td><a href={w.url} target="_blank" rel="noopener noreferrer">{w.ten}</a>{w.muc && <><br /><small className="muted">{w.muc}</small></>}
          {w.goi_y_wellness && <> <Tag cls="ok">Gợi ý Wellness — xác nhận ở «Sửa hồ sơ»</Tag></>}</td>
          <td>{w.da_ghep ? <><b>{w.da_ghep.ma}</b> {w.da_ghep.ten}</> : <span className="muted">—</span>}</td>
          <td>{w.goi_y ? <>{w.goi_y.ma} {w.goi_y.ten} <small className="muted">({Math.round(w.goi_y.diem * 100)}%)</small></> : <span className="muted">Không có gợi ý</span>}</td>
          <td>{duoc.ghep && !w.da_ghep && w.goi_y && <button className="act grey" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/${w.goi_y.pid}/ghep-web`, { method: "POST", json: { link_web: w.url } }); await taiWeb(); return r; })}>Xác nhận ghép {w.goi_y.ma}</button>}</td></tr>)}
          {!web.length && <tr><td colSpan={4} className="muted">Không đọc được tour nào.</td></tr>}</tbody></table></div>}
    </div>}

    {tab === "don" && <div className="panel">
      <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}><input type="checkbox" checked={chiVat} onChange={(e) => setChiVat(e.target.checked)} />Chỉ đơn cần hóa đơn GTGT công ty</label>
      {!don ? <p>Đang tải…</p> : <div className="wrap"><table><thead><tr><th>Mã</th><th>Tour</th><th>Khách</th><th>Tiền</th><th>Trạng thái</th><th>Email</th><th>Hóa đơn công ty</th></tr></thead>
        <tbody>{don.map((o) => <tr key={o.id}><td><b>{o.ma}</b><br /><small className="muted">{luc(o.tao_luc)}</small></td>
          <td>{o.ten}<br /><small className="muted">{o.ma_chuyen} · {o.khoi_hanh}</small></td>
          <td>{o.khach_hang}<br /><small className="muted">{o.dien_thoai} · {o.nguoi_lon} NL{o.tre_em ? ` ${o.tre_em} TE` : ""}{o.em_be ? ` ${o.em_be} EB` : ""} · Sales {o.sales}</small></td>
          <td>Tổng {d(o.tong)}<br />Đã trả {d(o.da_tra)}<br /><small className="muted">{o.cach_tra_ten}</small></td>
          <td><Tag cls={o.trang_thai.startsWith("Đã thanh toán") ? "ok" : o.trang_thai.startsWith("Đã đặt cọc") ? "navy" : o.trang_thai === "Chờ thanh toán" ? "warn" : "grey"}>{o.trang_thai}</Tag></td>
          <td>{o.email_gui_luc ? `Đã gửi ${luc(o.email_gui_luc)}` : "—"}{o.email_loi && <><br /><Tag cls="red">{o.email_loi}</Tag></>}</td>
          <td>{o.hoa_don_cong_ty ? <>{o.hoa_don_cong_ty.ten}<br /><small>MST {o.hoa_don_cong_ty.mst}</small><br />
            {o.hoa_don_da_xuat ? <Tag cls="ok">Đã xuất · {o.hoa_don_xuat_boi}</Tag>
              : duoc.vat ? <button className="act grey" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/don/${o.id}/da-xuat-vat`, { method: "POST" }); setDon((await api(`/tour-online/don?chi_vat=${chiVat}`)).don); return r; })}>Đánh dấu đã xuất</button>
              : <Tag cls="warn">Chờ Kế toán</Tag>}</> : <span className="muted">—</span>}</td></tr>)}
          {!don.length && <tr><td colSpan={7} className="muted">Chưa có đơn.</td></tr>}</tbody></table></div>}
    </div>}

    {tab === "mt" && <div className="panel"><h3 style={{ marginTop: 0 }}>Ma trận quản lý</h3>
      <div className="wrap"><table><thead><tr><th>Việc</th><th>Vai trò được làm</th></tr></thead>
        <tbody>{Object.entries(x.ma_tran || {}).map(([viec, vai]) => <tr key={viec}><td>{viec}</td><td>{(vai as string[]).map((v) => VAI[v] || v).join(", ")}</td></tr>)}</tbody></table></div>
      <p className="muted" style={{ fontSize: 13 }}>Máy chủ kiểm quyền ở từng cửa; bảng này đọc từ máy chủ. Không ai sửa nội dung trên vietourist.com.vn từ đây.</p></div>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
