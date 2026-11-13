"use client";
/** TK-1 · TOUR ĐOÀN KHÁCH TỰ THIẾT KẾ (Chủ tịch 04/11/2026 — giai đoạn 1).
 *  Hai mục:
 *   · Thiết kế khách gửi: mỗi mã một dòng (phiên bản mới nhất), mở xem từng ngày, dòng tạm tính, mục «Sales báo giá».
 *     Sales thấy GIÁ BÁN; Điều hành / Kế toán / BKS / Chủ tịch / TGĐ thấy thêm GIÁ VỐN và biên (máy chủ lọc).
 *   · Đơn giá dịch vụ đoàn (giá vốn): xe theo số chỗ, HDV, trưởng đoàn, bảo hiểm, nước, hội nghị, team building,
 *     Vé máy bay theo chặng (nối API vé sau). Điều hành nhập → TP Điều hành duyệt (người nhập không tự duyệt; Chủ tịch / TGĐ tự duyệt
 *     được). Chỉ dòng «Hiệu lực» vào tạm tính. Sửa một dòng = về «Chờ duyệt».
 *  Khách sạn và nhà hàng KHÔNG nhập ở đây: lấy gói giá khách sạn VTD và thực đơn nhà hàng đã duyệt. */
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "—");
const MAU_BG: Record<string, string> = { nhap: "grey", cho_duyet: "warn", tra_lai: "red", da_gui: "navy", khach_chot: "ok", het_han: "grey", thay_the: "grey" };
const MAU: Record<string, string> = { cho_duyet: "warn", hieu_luc: "ok", tu_choi: "red", ngung: "grey" };
const TRONG = { loai: "xe", ten: "", pham_vi: "ca_hai", khu_vuc: "", gia: "", tu_cho: "", tu_diem: "", den_diem: "", hang_ve: "pho_thong", gia_tre_em: "", gia_em_be: "", tu_ngay: "", den_ngay: "", ghi_chu: "" };

function Trang() {
  const { xacNhan, nhap, hop } = useHoi();
  const { toast } = useShell();
  const [tab, setTab] = useState<"tk" | "dg" | "le">("tk");
  const [le, setLe] = useState<any>(null); const [fLe, setFLe] = useState({ ngay: "", ten: "" });
  const [x, setX] = useState<any>(null);
  const [dg, setDg] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [f, setF] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const tai = () => api("/tour-doan").then(setX).catch((e) => toast(errMsg(e), true));
  const taiDg = () => api("/tour-doan/don-gia").then(setDg).catch((e) => toast(errMsg(e), true));
  useEffect(() => { tai(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (tab === "dg" && !dg) taiDg(); }, [tab]);  // eslint-disable-line react-hooks/exhaustive-deps
  const taiLe = () => api("/tour-doan/ngay-le").then(setLe).catch((e) => toast(errMsg(e), true));
  useEffect(() => { if (tab === "le" && !le) taiLe(); }, [tab]);  // eslint-disable-line react-hooks/exhaustive-deps
  const lam = async (g: () => Promise<any>) => { setBusy(true); try { await g(); await taiDg(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } };
  if (!x) return <p>Đang tải…</p>;
  const duoc = x.duoc || {};
  const so = (v: any) => (v === "" || v === null || v === undefined ? null : Number(v));

  const luu = () => lam(async () => {
    const body = { ...f, gia: so(f.gia), tu_cho: so(f.tu_cho), gia_tre_em: so(f.gia_tre_em), gia_em_be: so(f.gia_em_be), tu_ngay: f.tu_ngay || null, den_ngay: f.den_ngay || null };
    await api(f.id ? `/tour-doan/don-gia/${f.id}` : "/tour-doan/don-gia", { method: "POST", json: body });
    toast("Đã lưu — chờ TP Điều hành duyệt"); setF(null);
  });

  return (<>{hop}
    <h1>Tour đoàn khách tự thiết kế</h1>
    <p className="muted">Khách thiết kế tại kh.vietourist.vn/tours → «Tự thiết kế tour đoàn». Tạm tính = giá vốn ÷ (1 − {Math.round((x.bien_tam_tinh || 0.1) * 100)}%).
      Khách sạn, nhà hàng lấy từ gói giá / thực đơn đã duyệt; xe trong nước lấy bảng giá xe theo tuyến (xe 45 chỗ, cột xe nhà), lệch tuyến thì đơn giá ngày xe nhà × số ngày; HDV trong nước lấy bảng thù lao HDV theo tuyến (ngày lễ Tết ×2 theo thẻ «Ngày lễ Tết»). Dịch vụ khác, xe / HDV nước ngoài và vé máy bay lấy từ đơn giá đoàn dưới đây. Mục chưa có giá = Sales báo giá.
      Báo giá chính thức: Điều hành lập từ thiết kế, biên từ {Math.round((x.nguong_duyet || 0.1) * 100)}% TP Điều hành duyệt, dưới mức đó Chủ tịch / TGĐ duyệt; khách có 24 giờ để đồng ý, đồng ý xong máy tạo hợp đồng nháp.</p>
    {duoc.gia_von && Object.keys(x.hdv_vung || {}).length > 0 && <p className="muted" style={{ fontSize: 13 }}>
      Tuyến chưa có trong bảng thù lao HDV thì máy lấy tuyến có chung địa danh, không có nữa thì theo vùng (trung vị bảng giá mới):{" "}
      {Object.entries(x.hdv_vung).map(([v, g]: any) => `${v} ${d(g)}/ngày`).join(" · ")}. Phòng Hướng dẫn thêm tuyến vào bảng thì giá tuyến được dùng trước.</p>}
    <div style={{ display: "flex", gap: 6, margin: "8px 0", flexWrap: "wrap" }}>
      <button className={`act ${tab === "tk" ? "teal" : "grey"}`} aria-pressed={tab === "tk"} onClick={() => setTab("tk")}>Thiết kế khách gửi ({x.thiet_ke.length})</button>
      {duoc.gia_von && <button className={`act ${tab === "dg" ? "teal" : "grey"}`} aria-pressed={tab === "dg"} onClick={() => setTab("dg")}>Đơn giá dịch vụ đoàn (giá vốn)</button>}
      <button className={`act ${tab === "le" ? "teal" : "grey"}`} aria-pressed={tab === "le"} onClick={() => setTab("le")}>Ngày lễ Tết</button></div>

    {/* TK-1e · lịch ngày lễ Tết: chuyến đi trùng ngày ở đây thì thù lao HDV ngày ấy ×2 trong tạm tính (Chủ tịch 04/11/2026). */}
    {tab === "le" && le && <div className="panel">
      <p className="muted">Ngày đi tour trùng ngày lễ Tết thì thù lao HDV ngày ấy nhân đôi trong tạm tính. Máy tự tính lịch theo luật mỗi năm
        (Tết Dương lịch, Tết Nguyên đán mùng 1–4, Giỗ Tổ 10/3 âm lịch, 30/4, 1/5, Quốc khánh 1/9 và 2/9, Ngày Văn hóa Việt Nam 24/11).
        Điều hành chỉ thêm ngày Nhà nước hoán đổi trong năm.</p>
      <div className="wrap"><table><thead><tr><th>Ngày (máy tính theo luật)</th><th>Dịp</th></tr></thead>
        <tbody>{(le.theo_luat || []).map((n: any) => <tr key={n.ngay}><td>{ngay(n.ngay)}</td><td>{n.ten}</td></tr>)}</tbody></table></div>
      <h3 style={{ margin: "8px 0 0" }}>Ngày Điều hành thêm</h3>
      {le.duoc.nhap && <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Ngày<input type="date" value={fLe.ngay} onChange={(e) => setFLe({ ...fLe, ngay: e.target.value })} /></label>
        <label>Tên ngày lễ<input value={fLe.ten} placeholder="Tết Nguyên đán, 30/4, 2/9…" onChange={(e) => setFLe({ ...fLe, ten: e.target.value })} /></label>
        <button className="act teal" disabled={busy || !fLe.ngay || !fLe.ten} onClick={async () => { setBusy(true); try { await api("/tour-doan/ngay-le", { method: "POST", json: fLe }); setFLe({ ngay: "", ten: "" }); await taiLe(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } }}>Thêm ngày</button></div>}
      <div className="wrap"><table><thead><tr><th>Ngày</th><th>Tên</th><th>Người nhập</th><th /></tr></thead>
        <tbody>{le.ngay_le.map((n: any) => <tr key={n.id}><td>{ngay(n.ngay)}</td><td>{n.ten}</td><td><small>{n.tao_boi}</small></td>
          <td>{le.duoc.nhap && <button className="act grey" disabled={busy} onClick={async () => { setBusy(true); try { await api(`/tour-doan/ngay-le/${n.id}/xoa`, { method: "POST" }); await taiLe(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } }}>Bỏ</button>}</td></tr>)}
          {!le.ngay_le.length && <tr><td colSpan={4} className="muted">Chưa có ngày nào — thù lao HDV chưa nhân đôi ngày lễ.</td></tr>}</tbody></table></div>
    </div>}

    {tab === "tk" && <div className="panel"><div className="wrap"><table><thead><tr><th>Mã</th><th>Thiết kế</th><th>Ngày đi</th><th>Khách</th><th>Tạm tính</th>
      {duoc.gia_von && <th>Giá vốn · biên</th>}<th>Sales báo giá</th><th>Báo giá</th><th>Gửi lúc</th><th /></tr></thead>
      <tbody>{x.thiet_ke.map((t: any) => <tr key={t.id}>
        <td><b>{t.ma}</b><br /><small className="muted">phiên bản {t.phien_ban}</small></td>
        <td style={{ maxWidth: 360 }}><small>{t.tom_tat}</small></td><td>{ngay(t.ngay_di)}</td><td>{t.so_khach}</td><td>{d(t.tong_ban)}</td>
        {duoc.gia_von && <td>{d(t.tong_von)}<br /><small className="muted">{t.du_toan.bien != null ? `${(t.du_toan.bien * 100).toFixed(1)}%` : "—"}</small></td>}
        <td>{t.du_toan.thieu_gia?.length ? <Tag cls="warn">{t.du_toan.thieu_gia.length} mục</Tag> : <Tag cls="ok">Đủ giá</Tag>}</td>
        <td>{t.bao_gia ? <><Tag cls={MAU_BG[t.bao_gia.trang_thai] || "grey"}>{t.bao_gia.trang_thai_ten}</Tag><br /><small className="muted">{t.bao_gia.ma}</small></> : <span className="muted">—</span>}</td>
        <td>{t.gui_luc.replace("T", " ")}</td>
        <td><button className="act grey" onClick={() => setMo(mo?.id === t.id ? null : t)}>{mo?.id === t.id ? "Đóng" : "Xem"}</button></td></tr>)}
        {!x.thiet_ke.length && <tr><td colSpan={10} className="muted">Chưa có thiết kế nào.</td></tr>}</tbody></table></div>
      {mo && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
        <h3 style={{ marginTop: 0 }}>{mo.ma} · phiên bản {mo.phien_ban}</h3>
        <BaoGia key={mo.id} tk={mo} duoc={duoc} xong={async () => { const r: any = await api("/tour-doan"); setX(r); setMo(r.thiet_ke.find((y: any) => y.id === mo.id) || null); }} />
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
          <label>Phạm vi<select value={f.pham_vi} onChange={(e) => setF({ ...f, pham_vi: e.target.value, khu_vuc: e.target.value === "nn" ? f.khu_vuc : "" })}>{Object.entries(dg.pham_vi).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          {f.pham_vi === "nn" && f.loai !== "ve_may_bay" && <label>Khu vực áp dụng<select value={f.khu_vuc || ""} onChange={(e) => setF({ ...f, khu_vuc: e.target.value })}>
            <option value="">Mọi nước</option>
            {Object.entries(dg.khu_vuc || {}).map(([c, ds]: any) => <optgroup key={c} label={c}><option value={c}>Cả {c}</option>
              {ds.map((n: string) => <option key={n} value={n}>{n}</option>)}</optgroup>)}</select></label>}
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
          <td>{dg.pham_vi[r.pham_vi]}{r.pham_vi === "nn" && r.loai !== "ve_may_bay" && <><br /><small className="muted">Khu vực: {r.khu_vuc || "Mọi nước"}</small></>}</td>
          <td>{d(r.gia)} / {r.don_vi}{r.loai === "ve_may_bay" && <><br /><small className="muted">TE {d(r.gia_tre_em)} · EB {d(r.gia_em_be)}</small></>}</td>
          <td>{ngay(r.tu_ngay)} – {r.den_ngay ? ngay(r.den_ngay) : "…"}</td>
          <td><Tag cls={MAU[r.trang_thai] || "grey"}>{r.trang_thai_ten}</Tag>{r.ly_do && <><br /><small className="muted">{r.ly_do}</small></>}</td>
          <td><small>{r.tao_boi}{r.duyet_boi ? ` · ${r.duyet_boi}` : ""}</small></td>
          <td style={{ whiteSpace: "nowrap" }}>
            {dg.duoc.nhap && <button className="act grey" onClick={() => setF({ ...TRONG, ...r, khu_vuc: r.khu_vuc || "", gia: String(r.gia ?? ""), tu_cho: r.tu_cho ?? "", gia_tre_em: r.gia_tre_em ?? "", gia_em_be: r.gia_em_be ?? "" })}>Sửa</button>}
            {dg.duoc.duyet && r.trang_thai === "cho_duyet" && <>
              <button className="act teal" disabled={busy} onClick={() => lam(() => api(`/tour-doan/don-gia/${r.id}/duyet`, { method: "POST", json: { dong_y: true } }))}>Duyệt</button>
              <button className="act grey" disabled={busy} onClick={async () => { const l = await nhap("Lý do từ chối"); if (l) lam(() => api(`/tour-doan/don-gia/${r.id}/duyet`, { method: "POST", json: { dong_y: false, ly_do: l } })); }}>Từ chối</button></>}
            {dg.duoc.duyet && r.trang_thai === "hieu_luc" && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-doan/don-gia/${r.id}/ngung`, { method: "POST" }))}>Ngừng</button>}
          </td></tr>)}
          {!dg.don_gia.length && <tr><td colSpan={8} className="muted">Chưa có đơn giá — mọi dịch vụ ngoài khách sạn / nhà hàng sẽ hiện «Sales báo giá».</td></tr>}</tbody></table></div>
    </div>}
  </>);
}

/* TK-2 · BÁO GIÁ CHÍNH THỨC (Chủ tịch 04/11/2026). Điều hành lập từ thiết kế khách gửi, sửa giá vốn theo xác nhận NCC,
   điền dòng thiếu giá → gửi duyệt. Biên ≥ 10%: TP Điều hành duyệt (khác người lập); < 10%: Chủ tịch / TGĐ, có lý do.
   Duyệt xong khóa, hiện cho khách 24 giờ. Mọi con số tiền do máy chủ tính; ô nhập chỉ là giá vốn từng dòng. */
function BaoGia({ tk, duoc, xong }: { tk: any; duoc: any; xong: () => Promise<void> }) {
  const { toast } = useShell();
  const [bg, setBg] = useState<any>(tk.bao_gia);
  const [sua, setSua] = useState<any>(null);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const lam = async (f: () => Promise<any>, msg = "") => {
    setBusy(true);
    try { const r = await f(); if (r) setBg(r); if (msg) toast(msg); setSua(null); await xong(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const moSua = () => setSua({ dong: bg.dong.map((r: any) => ({ ...r, von: r.von ?? "" })), bien_pt: bg.bien_pt, ghi_chu: bg.ghi_chu || "",
    bao_gom: (bg.bao_gom || []).join("\n"), khong_bao_gom: (bg.khong_bao_gom || []).join("\n") });
  const luu = () => lam(() => api(`/tour-doan/bao-gia/${bg.id}`, { method: "POST", json: {
    dong: sua.dong.map((r: any) => ({ ...r, von: r.von === "" ? null : Number(String(r.von).replace(/\D/g, "")) })),
    bien_pt: Number(sua.bien_pt), ghi_chu: sua.ghi_chu,
    bao_gom: sua.bao_gom.split("\n").map((t: string) => t.trim()).filter(Boolean),
    khong_bao_gom: sua.khong_bao_gom.split("\n").map((t: string) => t.trim()).filter(Boolean) } }), "Đã lưu báo giá");
  const coSua = bg && ["nhap", "tra_lai"].includes(bg.trang_thai) && duoc.lap_bao_gia;
  const coDuyet = bg && bg.trang_thai === "cho_duyet" && (bg.cap_duyet === "ct_tgd" ? duoc.toan_quyen : duoc.duyet_bao_gia)
    && (duoc.toan_quyen || bg.tao_boi !== duoc.ten);

  if (!bg) return <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
    <b>Báo giá chính thức:</b><span className="muted">chưa lập.</span>
    {duoc.lap_bao_gia && <button className="act teal" disabled={busy} onClick={() => lam(() => api(`/tour-doan/${tk.id}/bao-gia`, { method: "POST" }), "Đã lập báo giá nháp")}>Lập báo giá</button>}</div>;

  return <div className="panel" style={{ background: "var(--panel2, transparent)" }}>
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <b>Báo giá {bg.ma}</b><Tag cls={MAU_BG[bg.trang_thai] || "grey"}>{bg.trang_thai_ten}</Tag>
      <small className="muted">lập: {bg.tao_boi}{bg.duyet_boi ? ` · duyệt: ${bg.duyet_boi}` : ""}{bg.han_luc ? ` · hiệu lực đến ${bg.han_luc.replace("T", " ")}` : ""}
        {bg.hop_dong_id ? " · đã có hợp đồng nháp (xem /hop-dong-khach)" : ""}</small></div>
    {bg.ly_do_tra && <p className="muted">Trả lại: {bg.ly_do_tra}</p>}
    {bg.ly_do_bien && <p className="muted">Lý do biên thấp: {bg.ly_do_bien}</p>}
    {!sua ? <>
      <div className="wrap"><table><thead><tr><th>Nhóm</th><th>Hạng mục</th><th>Tính theo</th>{duoc.gia_von && <th>Giá vốn</th>}<th>Giá bán</th></tr></thead>
        <tbody>{bg.dong.map((r: any, i: number) => <tr key={i} style={r.von === null && duoc.gia_von ? { background: "var(--red-soft, rgba(200,40,40,.08))" } : undefined}>
          <td>{r.nhom}</td><td>{r.ten}</td><td><small>{r.chi_tiet}</small></td>{duoc.gia_von && <td>{r.von === null ? <Tag cls="red">thiếu</Tag> : d(r.von)}</td>}<td>{d(r.ban)}</td></tr>)}</tbody></table></div>
      <p><b>Khách trả:</b> {d(bg.tong_ban)} = {bg.so_nl} NL × {d(bg.gia_nl)} + {bg.so_te} TE × {d(bg.gia_te)} (trẻ em {Math.round(bg.he_so_te * 100)}%){bg.so_eb ? ` · ${bg.so_eb} em bé không tính` : ""}
        {duoc.gia_von && <> · <b>Giá vốn</b> {d(bg.tong_von)} · <b>biên thực</b> {bg.bien_thuc != null ? `${(bg.bien_thuc * 100).toFixed(1)}%` : "—"} (đặt {bg.bien_pt}%)
          · cấp duyệt: {bg.cap_duyet === "ct_tgd" ? "Chủ tịch / TGĐ" : "TP Điều hành"}</>}</p>
      {bg.thieu_gia?.length > 0 && <p className="muted">Còn {bg.thieu_gia.length} dòng thiếu giá vốn — chưa gửi duyệt được.</p>}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        {coSua && <button className="act grey" onClick={moSua}>Sửa báo giá</button>}
        {coSua && <><input style={{ minWidth: 240 }} value={lyDo} placeholder="Lý do nếu biên dưới 10%" onChange={(e) => setLyDo(e.target.value)} />
          <button className="act teal" disabled={busy || bg.thieu_gia?.length > 0} onClick={() => lam(() => api(`/tour-doan/bao-gia/${bg.id}/gui-duyet`, { method: "POST", json: { ly_do: lyDo } }), "Đã gửi duyệt")}>Gửi duyệt</button></>}
        {coDuyet && <><button className="act teal" disabled={busy} onClick={() => lam(() => api(`/tour-doan/bao-gia/${bg.id}/duyet`, { method: "POST", json: { dong_y: true } }), "Đã duyệt — báo giá hiện cho khách 24 giờ")}>Duyệt &amp; gửi khách</button>
          <input style={{ minWidth: 200 }} value={lyDo} placeholder="Lý do trả lại" onChange={(e) => setLyDo(e.target.value)} />
          <button className="act grey" disabled={busy || !lyDo.trim()} onClick={() => lam(() => api(`/tour-doan/bao-gia/${bg.id}/duyet`, { method: "POST", json: { dong_y: false, ly_do: lyDo } }), "Đã trả lại")}>Trả lại</button></>}
        {bg.trang_thai === "cho_duyet" && !coDuyet && <span className="muted">Chờ {bg.cap_duyet === "ct_tgd" ? "Chủ tịch / TGĐ" : "TP Điều hành (khác người lập)"} duyệt.</span>}
      </div></> : <>
      <div className="wrap"><table><thead><tr><th>Nhóm</th><th>Hạng mục</th><th>Tính theo</th><th>Giá vốn (đ)</th><th /></tr></thead>
        <tbody>{sua.dong.map((r: any, i: number) => <tr key={i}>
          <td><input value={r.nhom} style={{ width: 90 }} onChange={(e) => setSua({ ...sua, dong: sua.dong.map((y: any, j: number) => j === i ? { ...y, nhom: e.target.value } : y) })} /></td>
          <td><input value={r.ten} style={{ minWidth: 220 }} onChange={(e) => setSua({ ...sua, dong: sua.dong.map((y: any, j: number) => j === i ? { ...y, ten: e.target.value } : y) })} /></td>
          <td><input value={r.chi_tiet} style={{ minWidth: 140 }} onChange={(e) => setSua({ ...sua, dong: sua.dong.map((y: any, j: number) => j === i ? { ...y, chi_tiet: e.target.value } : y) })} /></td>
          <td><input inputMode="numeric" value={r.von} placeholder="chưa có" style={{ width: 130 }} onChange={(e) => setSua({ ...sua, dong: sua.dong.map((y: any, j: number) => j === i ? { ...y, von: e.target.value.replace(/\D/g, "") } : y) })} /></td>
          <td><button className="act grey" onClick={() => setSua({ ...sua, dong: sua.dong.filter((_: any, j: number) => j !== i) })}>Bỏ</button></td></tr>)}</tbody></table></div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
        <button className="act grey" onClick={() => setSua({ ...sua, dong: [...sua.dong, { nhom: "Khác", ten: "", chi_tiet: "", von: "", nguon: "Điều hành nhập" }] })}>+ Thêm dòng</button>
        <label>Biên (%)<input type="number" value={sua.bien_pt} style={{ width: 80 }} onChange={(e) => setSua({ ...sua, bien_pt: e.target.value })} /></label>
        <label>Ghi chú<input value={sua.ghi_chu} style={{ minWidth: 220 }} onChange={(e) => setSua({ ...sua, ghi_chu: e.target.value })} /></label></div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 10 }}>
        <label>Bao gồm (mỗi dòng một ý)<textarea rows={4} value={sua.bao_gom} onChange={(e) => setSua({ ...sua, bao_gom: e.target.value })} /></label>
        <label>Không bao gồm<textarea rows={4} value={sua.khong_bao_gom} onChange={(e) => setSua({ ...sua, khong_bao_gom: e.target.value })} /></label></div>
      <div style={{ display: "flex", gap: 10 }}><button className="act teal" disabled={busy} onClick={luu}>Lưu · máy tính lại giá bán</button>
        <button className="act grey" onClick={() => setSua(null)}>Hủy</button></div></>}
  </div>;
}

export default function Page() { return <Shell><Trang /></Shell>; }
