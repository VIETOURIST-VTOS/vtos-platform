"use client";
/** TK-1 · TOUR ĐOÀN KHÁCH TỰ THIẾT KẾ (Chủ tịch 04/11/2026 — giai đoạn 1).
 *  Hai mục:
 *   · Thiết kế khách gửi: mỗi mã một dòng (phiên bản mới nhất), mở xem từng ngày, dòng tạm tính, mục «Sales báo giá».
 *     Sales thấy GIÁ BÁN; Điều hành / Kế toán / BKS / Chủ tịch / TGĐ thấy thêm GIÁ VỐN và biên (máy chủ lọc).
 *   · Đơn giá dịch vụ đoàn (giá vốn): xe theo số chỗ, HDV, trưởng đoàn, bảo hiểm, nước, visa, hội nghị, team building,
 *     Vé máy bay theo chặng (nối API vé sau). Điều hành nhập → TP Điều hành duyệt (người nhập không tự duyệt; Chủ tịch / TGĐ tự duyệt
 *     được). Chỉ dòng «Hiệu lực» vào tạm tính. Sửa một dòng = về «Chờ duyệt».
 *  Khách sạn và nhà hàng KHÔNG nhập ở đây: lấy gói giá khách sạn VTD và thực đơn nhà hàng đã duyệt. */
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "—");
const MAU: Record<string, string> = { cho_duyet: "warn", hieu_luc: "ok", tu_choi: "red", ngung: "grey" };
const TRONG = { loai: "xe", ten: "", pham_vi: "ca_hai", gia: "", tu_cho: "", tu_diem: "", den_diem: "", hang_ve: "pho_thong", gia_tre_em: "", gia_em_be: "", tu_ngay: "", den_ngay: "", ghi_chu: "" };

function Trang() {
  const { toast } = useShell();
  const [tab, setTab] = useState<"tk" | "dg">("tk");
  const [x, setX] = useState<any>(null);
  const [dg, setDg] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [f, setF] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const tai = () => api("/tour-doan").then(setX).catch((e) => toast(errMsg(e), true));
  const taiDg = () => api("/tour-doan/don-gia").then(setDg).catch((e) => toast(errMsg(e), true));
  useEffect(() => { tai(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (tab === "dg" && !dg) taiDg(); }, [tab]);  // eslint-disable-line react-hooks/exhaustive-deps
  const lam = async (g: () => Promise<any>) => { setBusy(true); try { await g(); await taiDg(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } };
  if (!x) return <p>Đang tải…</p>;
  const duoc = x.duoc || {};
  const so = (v: any) => (v === "" || v === null || v === undefined ? null : Number(v));

  const luu = () => lam(async () => {
    const body = { ...f, gia: so(f.gia), tu_cho: so(f.tu_cho), gia_tre_em: so(f.gia_tre_em), gia_em_be: so(f.gia_em_be), tu_ngay: f.tu_ngay || null, den_ngay: f.den_ngay || null };
    await api(f.id ? `/tour-doan/don-gia/${f.id}` : "/tour-doan/don-gia", { method: "POST", json: body });
    toast("Đã lưu — chờ TP Điều hành duyệt"); setF(null);
  });

  return (<>
    <h1>Tour đoàn khách tự thiết kế</h1>
    <p className="muted">Khách thiết kế tại kh.vietourist.vn/tours → «Tự thiết kế tour đoàn». Tạm tính = giá vốn ÷ (1 − {Math.round((x.bien_tam_tinh || 0.1) * 100)}%).
      Khách sạn, nhà hàng lấy từ gói giá / thực đơn đã duyệt; xe trong nước lấy bảng giá xe theo tuyến (xe 45 chỗ, cột xe nhà), lệch tuyến thì đơn giá ngày xe nhà × số ngày; HDV trong nước lấy bảng thù lao HDV theo tuyến (chưa tính lễ Tết ×2). Dịch vụ khác, xe / HDV nước ngoài và vé máy bay lấy từ đơn giá đoàn dưới đây. Mục chưa có giá = Sales báo giá.
      Biên dưới {Math.round((x.nguong_duyet || 0.1) * 100)}% phải Chủ tịch / TGĐ duyệt (áp ở bước duyệt báo giá).</p>
    {duoc.gia_von && Object.keys(x.hdv_vung || {}).length > 0 && <p className="muted" style={{ fontSize: 13 }}>
      Tuyến chưa có trong bảng thù lao HDV thì máy lấy tuyến có chung địa danh, không có nữa thì theo vùng (trung vị bảng giá mới):{" "}
      {Object.entries(x.hdv_vung).map(([v, g]: any) => `${v} ${d(g)}/ngày`).join(" · ")}. Phòng Hướng dẫn thêm tuyến vào bảng thì giá tuyến được dùng trước.</p>}
    <div style={{ display: "flex", gap: 6, margin: "8px 0", flexWrap: "wrap" }}>
      <button className={`act ${tab === "tk" ? "teal" : "grey"}`} aria-pressed={tab === "tk"} onClick={() => setTab("tk")}>Thiết kế khách gửi ({x.thiet_ke.length})</button>
      {duoc.gia_von && <button className={`act ${tab === "dg" ? "teal" : "grey"}`} aria-pressed={tab === "dg"} onClick={() => setTab("dg")}>Đơn giá dịch vụ đoàn (giá vốn)</button>}</div>

    {tab === "tk" && <div className="panel"><div className="wrap"><table><thead><tr><th>Mã</th><th>Thiết kế</th><th>Ngày đi</th><th>Khách</th><th>Tạm tính</th>
      {duoc.gia_von && <th>Giá vốn · biên</th>}<th>Sales báo giá</th><th>Gửi lúc</th><th /></tr></thead>
      <tbody>{x.thiet_ke.map((t: any) => <tr key={t.id}>
        <td><b>{t.ma}</b><br /><small className="muted">phiên bản {t.phien_ban}</small></td>
        <td style={{ maxWidth: 360 }}><small>{t.tom_tat}</small></td><td>{ngay(t.ngay_di)}</td><td>{t.so_khach}</td><td>{d(t.tong_ban)}</td>
        {duoc.gia_von && <td>{d(t.tong_von)}<br /><small className="muted">{t.du_toan.bien != null ? `${(t.du_toan.bien * 100).toFixed(1)}%` : "—"}</small></td>}
        <td>{t.du_toan.thieu_gia?.length ? <Tag cls="warn">{t.du_toan.thieu_gia.length} mục</Tag> : <Tag cls="ok">Đủ giá</Tag>}</td>
        <td>{t.gui_luc.replace("T", " ")}</td>
        <td><button className="act grey" onClick={() => setMo(mo?.id === t.id ? null : t)}>{mo?.id === t.id ? "Đóng" : "Xem"}</button></td></tr>)}
        {!x.thiet_ke.length && <tr><td colSpan={9} className="muted">Chưa có thiết kế nào.</td></tr>}</tbody></table></div>
      {mo && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
        <h3 style={{ marginTop: 0 }}>{mo.ma} · phiên bản {mo.phien_ban}</h3>
        <p className="muted">{mo.thiet_ke.khoi_hanh} · {mo.thiet_ke.pham_vi === "nn" ? "Nước ngoài" : "Trong nước"} · {mo.thiet_ke.khach.nl} NL, {mo.thiet_ke.khach.te} trẻ em, {mo.thiet_ke.khach.eb} em bé
          · phòng {mo.thiet_ke.phong.p2} đôi / {mo.thiet_ke.phong.p3} phòng 3 / {mo.thiet_ke.phong.p1} đơn{mo.thiet_ke.ngan_sach ? ` · ngân sách ${d(mo.thiet_ke.ngan_sach)}/khách` : ""}
          {mo.thiet_ke.uu_tien ? ` · ${mo.thiet_ke.uu_tien}` : ""}{mo.thiet_ke.ghi_chu ? ` · Ghi chú: ${mo.thiet_ke.ghi_chu}` : ""}</p>
        <div className="wrap"><table><thead><tr><th>Ngày</th><th>Điểm</th><th>Trưa</th><th>Tối</th><th>Tham quan</th></tr></thead>
          <tbody>{mo.du_toan.khung?.map((k: any) => { const n = mo.thiet_ke.ngay[k.i] || {}; const b = (v: any) => v?.tu_tuc ? "Tự túc" : v?.thuc_don_id ? `Thực đơn #${v.thuc_don_id}` : v?.khac ? `Khách ghi: ${v.khac}` : "—";
            return <tr key={k.i}><td>{k.i + 1} · {ngay(k.ngay)}</td><td>{k.tu ? `${k.tu} → ${k.den} (${mo.thiet_ke.chang[k.chang_i]?.pt})` : k.o}</td><td>{b(n.trua)}</td><td>{b(n.toi)}</td><td>{(n.tham_quan || []).join(", ")}</td></tr>; })}</tbody></table></div>
        <div className="wrap"><table><thead><tr><th>Nhóm</th><th>Hạng mục</th><th>Tính theo</th>{duoc.gia_von && <th>Giá vốn</th>}<th>Tạm tính (bán)</th></tr></thead>
          <tbody>{mo.du_toan.dong.map((r: any, i: number) => <tr key={i}><td>{r.nhom}</td><td>{r.ten}</td><td>{r.chi_tiet}</td>{duoc.gia_von && <td>{d(r.von)}</td>}<td>{d(r.ban)}</td></tr>)}</tbody></table></div>
        {mo.du_toan.thieu_gia?.length > 0 && <><b>Sales báo giá</b><ul>{mo.du_toan.thieu_gia.map((r: any, i: number) => <li key={i}>{r.nhom}: {r.ten} — {r.ly_do}</li>)}</ul></>}
        {mo.du_toan.canh_bao?.length > 0 && <><b>Cảnh báo</b><ul>{mo.du_toan.canh_bao.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></>}
      </div>}
    </div>}

    {tab === "dg" && dg && <div className="panel">
      {dg.duoc.nhap && !f && <button className="act teal" onClick={() => setF({ ...TRONG })}>+ Thêm đơn giá</button>}
      {f && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
        <h3 style={{ marginTop: 0 }}>{f.id ? "Sửa đơn giá" : "Thêm đơn giá"}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 10 }}>
          <label>Loại<select value={f.loai} onChange={(e) => setF({ ...f, loai: e.target.value })}>{Object.entries(dg.loai).map(([k, v]: any) => <option key={k} value={k}>{v.ten} ({v.don_vi})</option>)}</select></label>
          <label>Tên hiển thị<input value={f.ten} placeholder={f.loai === "xe" ? "Xe 29 chỗ" : f.loai === "ve_may_bay" ? "SGN → DAD phổ thông" : ""} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
          <label>Phạm vi<select value={f.pham_vi} onChange={(e) => setF({ ...f, pham_vi: e.target.value })}>{Object.entries(dg.pham_vi).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          {f.loai === "xe" && <label>Số chỗ khách<input inputMode="numeric" value={f.tu_cho} onChange={(e) => setF({ ...f, tu_cho: e.target.value.replace(/\D/g, "") })} /></label>}
          {f.loai === "ve_may_bay" && <>
            <label>Điểm đi<input value={f.tu_diem} placeholder="TP HCM" onChange={(e) => setF({ ...f, tu_diem: e.target.value })} /></label>
            <label>Điểm đến<input value={f.den_diem} placeholder="Đà Nẵng" onChange={(e) => setF({ ...f, den_diem: e.target.value })} /></label>
            <label>Hạng vé<select value={f.hang_ve} onChange={(e) => setF({ ...f, hang_ve: e.target.value })}>{Object.entries(dg.hang_ve).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label></>}
          <label>{f.loai === "ve_may_bay" ? "Giá vốn người lớn (đ)" : `Giá vốn (đ / ${dg.loai[f.loai]?.don_vi})`}<input inputMode="numeric" value={f.gia} onChange={(e) => setF({ ...f, gia: e.target.value.replace(/\D/g, "") })} /></label>
          {f.loai === "ve_may_bay" && <>
            <label>Giá trẻ em (trống = chưa có)<input inputMode="numeric" value={f.gia_tre_em ?? ""} onChange={(e) => setF({ ...f, gia_tre_em: e.target.value.replace(/\D/g, "") })} /></label>
            <label>Giá em bé (trống = chưa có)<input inputMode="numeric" value={f.gia_em_be ?? ""} onChange={(e) => setF({ ...f, gia_em_be: e.target.value.replace(/\D/g, "") })} /></label></>}
          <label>Hiệu lực từ<input type="date" value={f.tu_ngay || ""} onChange={(e) => setF({ ...f, tu_ngay: e.target.value })} /></label>
          <label>Đến (trống = còn hiệu lực)<input type="date" value={f.den_ngay || ""} onChange={(e) => setF({ ...f, den_ngay: e.target.value })} /></label>
          <label>Ghi chú<input value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label></div>
        <div style={{ display: "flex", gap: 10, marginTop: 10 }}><button className="act teal" disabled={busy} onClick={luu}>Lưu · gửi duyệt</button>
          <button className="act grey" onClick={() => setF(null)}>Hủy</button></div></div>}
      <div className="wrap"><table><thead><tr><th>Loại</th><th>Tên</th><th>Phạm vi</th><th>Giá vốn</th><th>Hiệu lực</th><th>Trạng thái</th><th>Người nhập · duyệt</th><th /></tr></thead>
        <tbody>{dg.don_gia.map((r: any) => <tr key={r.id}>
          <td>{r.loai_ten}</td>
          <td>{r.ten}{r.loai === "xe" && <><br /><small className="muted">{r.tu_cho} chỗ</small></>}
            {r.loai === "ve_may_bay" && <><br /><small className="muted">{r.tu_diem} → {r.den_diem} · {dg.hang_ve[r.hang_ve] || ""}</small></>}</td>
          <td>{dg.pham_vi[r.pham_vi]}</td>
          <td>{d(r.gia)} / {r.don_vi}{r.loai === "ve_may_bay" && <><br /><small className="muted">TE {d(r.gia_tre_em)} · EB {d(r.gia_em_be)}</small></>}</td>
          <td>{ngay(r.tu_ngay)} – {r.den_ngay ? ngay(r.den_ngay) : "…"}</td>
          <td><Tag cls={MAU[r.trang_thai] || "grey"}>{r.trang_thai_ten}</Tag>{r.ly_do && <><br /><small className="muted">{r.ly_do}</small></>}</td>
          <td><small>{r.tao_boi}{r.duyet_boi ? ` · ${r.duyet_boi}` : ""}</small></td>
          <td style={{ whiteSpace: "nowrap" }}>
            {dg.duoc.nhap && <button className="act grey" onClick={() => setF({ ...TRONG, ...r, gia: String(r.gia ?? ""), tu_cho: r.tu_cho ?? "", gia_tre_em: r.gia_tre_em ?? "", gia_em_be: r.gia_em_be ?? "" })}>Sửa</button>}
            {dg.duoc.duyet && r.trang_thai === "cho_duyet" && <>
              <button className="act teal" disabled={busy} onClick={() => lam(() => api(`/tour-doan/don-gia/${r.id}/duyet`, { method: "POST", json: { dong_y: true } }))}>Duyệt</button>
              <button className="act grey" disabled={busy} onClick={() => { const l = window.prompt("Lý do từ chối"); if (l) lam(() => api(`/tour-doan/don-gia/${r.id}/duyet`, { method: "POST", json: { dong_y: false, ly_do: l } })); }}>Từ chối</button></>}
            {dg.duoc.duyet && r.trang_thai === "hieu_luc" && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-doan/don-gia/${r.id}/ngung`, { method: "POST" }))}>Ngừng</button>}
          </td></tr>)}
          {!dg.don_gia.length && <tr><td colSpan={8} className="muted">Chưa có đơn giá — mọi dịch vụ ngoài khách sạn / nhà hàng sẽ hiện «Sales báo giá».</td></tr>}</tbody></table></div>
    </div>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
