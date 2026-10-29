"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { AnhNoiBo } from "@/components/nha-hang/AlbumNhaHang";

/** KS-13 · KHÁCH SẠN HỢP TÁC (CỔNG KHÁCH) — Chủ tịch duyệt bản demo 30/10/2026.
 *  NV / TP Điều hành nhập khách sạn, ảnh, loại phòng, gói giá và mùa giá (chỉ GIÁ BÁN, chưa thuế phí).
 *  TP Điều hành duyệt ảnh và giá — người nhập không tự duyệt (trừ Chủ tịch, TGĐ). Sửa gói đã duyệt → về Nháp, thôi hiện.
 *  TP Điều hành bật «Hiện trên cổng» khi đủ điều kiện; người vừa sửa hồ sơ không tự bật. */
const tien = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "");
const KS0 = { ten: "", tinh_thanh: "", khu_vuc: "", dia_chi: "", sao: 0, loai: "khach_san", km_trung_tam: "", gan: "", noi_bat: "", mo_ta: "",
  tien_ich: [] as string[], gio_nhan: "14:00", gio_tra: "12:00", cs_tre_em: "", cs_giuong_phu: "", cs_vat_nuoi: "", cs_khac: "", thue_phi_pt: 0,
  lien_he_noi_bo: "", ghi_chu_noi_bo: "" };
const LP0 = { ten: "", dien_tich: 0, giuong: "", mo_ta: "", toi_da_nguoi_lon: 2, toi_da_tre_em: 0, so_phong: 1, thu_tu: 0, dang_ban: true };
const MUA0 = { tu_ngay: "", den_ngay: "", gia_thuong: "", gia_cuoi_tuan: "", gia_niem_yet: "", ghi_chu: "" };
const TT: Record<string, string> = { nhap: "", cho_duyet: "warn", da_duyet: "ok", tra_lai: "bad", an: "" };

async function guiTep(path: string, fd: FormData) {
  const headers: Record<string, string> = {}; const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const r = await fetch(`/api/v1${path}`, { method: "POST", headers, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw { status: r.status, message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}

function Trang() {
  const { toast } = useShell();
  const [x, setX] = useState<any>(null);
  const [tab, setTab] = useState<"ds" | "cd">("ds");
  const [mo, setMo] = useState<number | "moi" | null>(null);
  const [tim, setTim] = useState("");
  const load = useCallback(() => { api("/khach-san-vtd").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const k = (s: string) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();
  const ds = x.khach_san.filter((h: any) => !tim || k(`${h.ten} ${h.ma} ${h.tinh_thanh} ${h.khu_vuc}`).includes(k(tim)));
  return (<>
    <h1>Khách sạn (cổng khách)</h1>
    <p className="muted">Khách sạn VTD có hợp đồng trực tiếp. Điều hành nhập khách sạn, ảnh, loại phòng và GIÁ BÁN theo mùa (chưa thuế phí); TP Điều hành duyệt
      ảnh, giá và bật «Hiện trên cổng». Người nhập không tự duyệt / tự bật (trừ Chủ tịch, TGĐ). Khách xem như Agoda và gửi yêu cầu giữ phòng — yêu cầu vào màn
      «Đơn khách sạn OTA › Yêu cầu của khách». Giá vốn / hoa hồng theo hợp đồng NCC, không nhập ở đây.</p>
    <div style={{ display: "flex", gap: 6, margin: "10px 0" }}>
      <button className={`act ${tab === "ds" ? "teal" : "grey"}`} onClick={() => setTab("ds")}>Khách sạn ({x.khach_san.length})</button>
      <button className={`act ${tab === "cd" ? "teal" : "grey"}`} onClick={() => setTab("cd")}>Chờ duyệt ({x.cho_duyet.anh} ảnh · {x.cho_duyet.goi} gói giá)</button></div>
    {tab === "cd" && <ChoDuyet toast={toast} onDoi={load} />}
    {tab === "ds" && mo === null && <section className="panel">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm tên, mã, thành phố" aria-label="Tìm khách sạn" style={{ maxWidth: 260 }} />
        <span style={{ flex: 1 }} />{x.duoc_nhap && <button className="act teal" onClick={() => setMo("moi")}>+ Thêm khách sạn</button>}</div>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th></th><th>Khách sạn</th><th>Thành phố</th><th>Ảnh</th><th>Loại phòng</th><th>Gói giá</th><th>Cổng khách</th><th></th></tr></thead>
        <tbody>{ds.map((h: any) => <tr key={h.id} className="ksv-dong">
          <td style={{ width: 72 }}>{h.bia ? <AnhNoiBo src={h.bia} alt={h.ten} style={{ width: 64, height: 48, borderRadius: 6 }} /> : <span className="muted">—</span>}</td>
          <td><b>{h.ten}</b><div className="muted">{h.ma} · {"★".repeat(h.sao) || "chưa xếp sao"}</div></td>
          <td>{h.tinh_thanh}<div className="muted">{h.khu_vuc}</div></td>
          <td>{h.anh_duyet} duyệt{h.anh_cho ? <> · <Tag cls="warn">{h.anh_cho} chờ</Tag></> : null}<div className="muted">{h.so_anh} ảnh</div></td>
          <td>{h.so_loai_phong}</td>
          <td>{h.goi_duyet} duyệt{h.goi_cho ? <> · <Tag cls="warn">{h.goi_cho} chờ</Tag></> : null}</td>
          <td>{h.ngung ? <Tag cls="bad">Ngừng hợp tác</Tag> : h.hien_cong ? <Tag cls="ok">Đang hiện</Tag> : <Tag cls="warn">Chưa hiện</Tag>}</td>
          <td><button className="act grey" onClick={() => setMo(h.id)}>{x.duoc_nhap ? "Mở" : "Xem"}</button></td></tr>)}
          {!ds.length && <tr><td colSpan={8} className="muted">{x.khach_san.length ? "Không có khách sạn khớp." : "Chưa có khách sạn hợp tác. Bấm «+ Thêm khách sạn»."}</td></tr>}</tbody></table></div>
    </section>}
    {tab === "ds" && mo !== null && <HoSo x={x} kid={mo} toast={toast} onDong={() => { setMo(null); load(); }} onMoi={(id) => { setMo(id); load(); }} onDoi={load} />}
  </>);
}

function HoSo({ x, kid, toast, onDong, onMoi, onDoi }: { x: any; kid: number | "moi"; toast: (m: string, l?: boolean) => void; onDong: () => void; onMoi: (id: number) => void; onDoi: () => void }) {
  const [h, setH] = useState<any>(null);
  const [f, setF] = useState<any>(KS0);
  const [t, setT] = useState<"tt" | "anh" | "phong" | "hien">("tt");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    if (kid === "moi") { setH(null); setF(KS0); return; }
    api<any>(`/khach-san-vtd/${kid}`).then((r) => { setH(r); setF({ ...KS0, ...r.khach_san, km_trung_tam: r.khach_san.km_trung_tam ?? "" }); }).catch((e) => toast(errMsg(e), true));
  }, [kid, toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); load(); onDoi(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  const nhap = x.duoc_nhap;
  const o = (key: string, label: string, ph = "", type = "text") => <label>{label}<input type={type} value={f[key] ?? ""} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [key]: e.target.value })} /></label>;
  const ta = (key: string, label: string, rows = 3, ph = "") => <label>{label}<textarea rows={rows} value={f[key] ?? ""} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [key]: e.target.value })} /></label>;
  const luu = async () => {
    const body = { ...f, sao: Number(f.sao) || 0, km_trung_tam: f.km_trung_tam === "" ? null : Number(f.km_trung_tam), thue_phi_pt: Number(f.thue_phi_pt) || 0 };
    const r = await goi(kid === "moi" ? "/khach-san-vtd" : `/khach-san-vtd/${kid}`, body);
    if (r && kid === "moi") onMoi(r.id);
  };
  return <section className="panel" id="ksv-ho-so">
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <h2 style={{ margin: 0 }}>{kid === "moi" ? "Thêm khách sạn" : h ? `${h.khach_san.ten}` : "…"}</h2>
      {h && <span className="muted">{h.khach_san.ma}</span>}{h && (h.khach_san.hien_cong ? <Tag cls="ok">Đang hiện trên cổng</Tag> : <Tag cls="warn">Chưa hiện</Tag>)}
      <span style={{ flex: 1 }} /><button className="act grey" onClick={onDong}>Đóng</button></div>
    {kid !== "moi" && <div style={{ display: "flex", gap: 4, flexWrap: "wrap", borderBottom: "1px solid var(--line, #2a3b4d)", margin: "10px 0" }}>
      {([["tt", "Thông tin"], ["anh", `Album ảnh (${h?.anh.length ?? 0})`], ["phong", `Loại phòng & giá (${h?.loai_phong.length ?? 0})`], ["hien", "Hiện trên cổng"]] as const).map(([k2, t2]) =>
        <button key={k2} className={`act ${t === k2 ? "teal" : "grey"}`} onClick={() => setT(k2)}>{t2}</button>)}</div>}
    {(kid === "moi" || t === "tt") && <>
      <div className="grid">
        {o("ten", "Tên khách sạn")}
        <label>Thành phố<select value={f.tinh_thanh} disabled={!nhap} onChange={(e) => setF({ ...f, tinh_thanh: e.target.value })}><option value="">— chọn —</option>
          {x.thanh_pho.map((c: any) => <option key={c.ten} value={c.ten}>{c.ten} · {c.mien}</option>)}</select></label>
        {o("khu_vuc", "Khu vực", "Mỹ Khê, Hải Châu…")}{o("dia_chi", "Địa chỉ")}
        <label>Hạng sao<select value={f.sao} disabled={!nhap} onChange={(e) => setF({ ...f, sao: Number(e.target.value) })}>{[0, 1, 2, 3, 4, 5].map((s) => <option key={s} value={s}>{s ? `${s} sao` : "Chưa xếp hạng"}</option>)}</select></label>
        <label>Loại chỗ ở<select value={f.loai} disabled={!nhap} onChange={(e) => setF({ ...f, loai: e.target.value })}>{Object.entries(x.loai).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
        {o("km_trung_tam", "Cách trung tâm (km)", "2.5", "number")}{o("gan", "Gần đâu (hiện trên thẻ)", "120 m tới biển · 3 km tới cầu Rồng")}
        {o("noi_bat", "Một dòng nổi bật", "Hồ bơi tầng thượng nhìn biển, bữa sáng buffet")}
        {o("gio_nhan", "Giờ nhận phòng", "14:00")}{o("gio_tra", "Giờ trả phòng", "12:00")}
        {o("thue_phi_pt", "Thuế phí cộng thêm (%)", "15", "number")}</div>
      {ta("mo_ta", "Giới thiệu cho khách", 4)}
      <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10 }}><legend>Tiện nghi</legend>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 6 }}>{Object.entries(x.tien_ich).map(([k2, v]: any) =>
          <label key={k2} style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" disabled={!nhap} checked={f.tien_ich.includes(k2)}
            onChange={(e) => setF({ ...f, tien_ich: e.target.checked ? [...f.tien_ich, k2] : f.tien_ich.filter((y: string) => y !== k2) })} />{v}</label>)}</div></fieldset>
      <div className="grid">{o("cs_tre_em", "Chính sách trẻ em")}{o("cs_giuong_phu", "Giường phụ")}{o("cs_vat_nuoi", "Vật nuôi")}</div>
      {ta("cs_khac", "Chính sách khác", 2)}
      <div className="grid">{o("lien_he_noi_bo", "Liên hệ khách sạn (nội bộ, không lên cổng)")}</div>
      {ta("ghi_chu_noi_bo", "Ghi chú nội bộ (không lên cổng)", 2)}
      {nhap && <button className="act teal" disabled={busy} onClick={luu}>{kid === "moi" ? "Thêm khách sạn" : "Lưu hồ sơ"}</button>}
    </>}
    {h && t === "anh" && <Album h={h} x={x} toast={toast} onDoi={() => { load(); onDoi(); }} />}
    {h && t === "phong" && <Phong h={h} x={x} toast={toast} goi={goi} busy={busy} />}
    {h && t === "hien" && <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <b>Điều kiện bật «Hiện trên cổng»</b>
      {h.dieu_kien.map((c: any) => <span key={c.ma} style={{ color: c.ok ? "#2bb39a" : "#d99a2b" }}>{c.ok ? "✓" : "✗"} {c.ten}</span>)}
      <span className="muted">Gói giá chưa duyệt thì khách sạn vẫn hiện, nhưng phòng hiện «Giá đang cập nhật» và khách chỉ gửi yêu cầu.</span>
      {x.duoc_duyet && <div style={{ display: "flex", gap: 8 }}>
        {h.khach_san.hien_cong ? <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/${kid}/hien-cong`, { bat: false })}>Tắt hiện</button>
          : <button className="act teal" disabled={busy || h.khach_san.ngung} onClick={() => goi(`/khach-san-vtd/${kid}/hien-cong`, { bat: true })}>Bật hiện trên cổng</button>}
        <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/${kid}/ngung`, { bat: !h.khach_san.ngung })}>{h.khach_san.ngung ? "Hợp tác lại" : "Ngừng hợp tác"}</button></div>}
      {!x.duoc_duyet && <span className="muted">TP Điều hành bật hiện.</span>}
    </div>}
  </section>;
}

function Album({ h, x, toast, onDoi }: { h: any; x: any; toast: (m: string, l?: boolean) => void; onDoi: () => void }) {
  const [teps, setTeps] = useState<File[]>([]);
  const [nhom, setNhom] = useState("");
  const [lp, setLp] = useState("");
  const [nguon, setNguon] = useState("");
  const [tien, setTien] = useState("");
  const [chon, setChon] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const kid = h.khach_san.id;
  const tai = async () => {
    if (!teps.length || !nhom) { toast("Chọn tệp ảnh và nhóm ảnh", true); return; }
    setBusy(true); let ok = 0;
    for (let i = 0; i < teps.length; i++) {
      setTien(`Đang tải ${i + 1}/${teps.length}…`);
      try { const fd = new FormData(); fd.append("tep", teps[i]); fd.append("nhom", nhom); fd.append("loai_phong_id", lp); fd.append("nguon", nguon);
        await guiTep(`/khach-san-vtd/${kid}/anh`, fd); ok++; }
      catch (e) { toast(`${teps[i].name}: ${errMsg(e)}`, true); }
    }
    setBusy(false); setTien(""); setTeps([]); toast(`Đã tải ${ok}/${teps.length} ảnh`); onDoi();
  };
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setChon([]); onDoi(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const tenLp: Record<number, string> = Object.fromEntries(h.loai_phong.map((p: any) => [p.id, p.ten]));
  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    {x.duoc_nhap && <div className="panel" style={{ margin: 0 }}>
      <div className="grid">
        <label>Ảnh (JPG / PNG / WEBP, chọn nhiều)<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => setTeps(Array.from(e.target.files || []))} /></label>
        <label>Nhóm ảnh<select value={nhom} onChange={(e) => setNhom(e.target.value)}><option value="">— chọn —</option>{Object.entries(x.nhom_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Ảnh của loại phòng (nếu là ảnh phòng)<select value={lp} onChange={(e) => setLp(e.target.value)}><option value="">— không —</option>{h.loai_phong.map((p: any) => <option key={p.id} value={p.id}>{p.ten}</option>)}</select></label>
        <label>Nguồn ảnh (nội bộ)<input value={nguon} onChange={(e) => setNguon(e.target.value)} placeholder="Khách sạn gửi qua email 30/10 / VTD tự chụp" /></label></div>
      <button className="act teal" disabled={busy || !teps.length} onClick={tai}>Tải {teps.length || ""} ảnh lên</button> {tien && <span className="muted">{tien}</span>}</div>}
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      <span className="muted">Đã chọn {chon.length}</span>
      {x.duoc_nhap && <button className="act teal" disabled={busy || !chon.length} onClick={() => goi("/khach-san-vtd/anh/gui-duyet", { ids: chon })}>Gửi duyệt</button>}
      <button className="act grey" onClick={() => setChon(h.anh.filter((a: any) => ["nhap", "tra_lai"].includes(a.trang_thai)).map((a: any) => a.id))}>Chọn ảnh nháp</button></div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 10 }}>{h.anh.map((a: any) =>
      <div key={a.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
        <AnhNoiBo src={a.nho} alt={a.chu_thich || a.nhom_ten} style={{ width: "100%", aspectRatio: "4 / 3", borderRadius: 6 }} />
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}><input type="checkbox" aria-label="Chọn ảnh" checked={chon.includes(a.id)} onChange={(e) => setChon(e.target.checked ? [...chon, a.id] : chon.filter((y) => y !== a.id))} />
          <Tag cls={TT[a.trang_thai]}>{a.trang_thai_ten}</Tag>{a.la_bia && <Tag cls="ok">Bìa</Tag>}<span className="muted" style={{ fontSize: 12 }}>{a.nhom_ten}{a.loai_phong_id ? ` · ${tenLp[a.loai_phong_id] || ""}` : ""}</span></div>
        {a.ly_do_tra_lai && <small style={{ color: "#d99a2b" }}>Trả lại: {a.ly_do_tra_lai}</small>}
        <small className="muted">tải: {a.tai_boi}{a.duyet_boi ? ` · duyệt: ${a.duyet_boi}` : ""}</small>
        {x.duoc_nhap && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {a.trang_thai === "da_duyet" && !a.la_bia && <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}`, { la_bia: true })}>Đặt bìa</button>}
          {a.trang_thai !== "an" ? <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: true })}>Ẩn</button>
            : <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: false })}>Bỏ ẩn</button>}</div>}
      </div>)}
      {!h.anh.length && <p className="muted">Chưa có ảnh. Ảnh do khách sạn gửi hoặc VTD tự chụp; TP Điều hành duyệt rồi mới lên cổng.</p>}</div>
  </div>;
}

function Phong({ h, x, toast, goi, busy }: { h: any; x: any; toast: (m: string, l?: boolean) => void; goi: (p: string, j: any) => Promise<any>; busy: boolean }) {
  const [lp, setLp] = useState<any>(null);
  const [g, setG] = useState<any>(null);   // {lid, id?, ten, bua_sang, huy_truoc_ngay, dang_ban, mua:[]}
  const kid = h.khach_san.id;
  const luuLp = async () => { const r = await goi(lp.id ? `/khach-san-vtd/${kid}/loai-phong/${lp.id}` : `/khach-san-vtd/${kid}/loai-phong`,
    { ...lp, dien_tich: Number(lp.dien_tich) || 0, toi_da_nguoi_lon: Number(lp.toi_da_nguoi_lon) || 1, toi_da_tre_em: Number(lp.toi_da_tre_em) || 0, so_phong: Number(lp.so_phong) || 0, thu_tu: Number(lp.thu_tu) || 0 }); if (r) setLp(null); };
  const luuGoi = async () => {
    const mua = g.mua.filter((m: any) => m.tu_ngay || m.den_ngay || m.gia_thuong).map((m: any) => ({ ...m, gia_thuong: Number(String(m.gia_thuong).replace(/\D/g, "")) || 0,
      gia_cuoi_tuan: m.gia_cuoi_tuan ? Number(String(m.gia_cuoi_tuan).replace(/\D/g, "")) : null, gia_niem_yet: m.gia_niem_yet ? Number(String(m.gia_niem_yet).replace(/\D/g, "")) : null }));
    const r = await goi(g.id ? `/khach-san-vtd/loai-phong/${g.lid}/goi/${g.id}` : `/khach-san-vtd/loai-phong/${g.lid}/goi`,
      { ten: g.ten, bua_sang: g.bua_sang, huy_truoc_ngay: g.huy_truoc_ngay === "" || g.huy_truoc_ngay === null ? null : Number(g.huy_truoc_ngay), dang_ban: g.dang_ban, mua });
    if (r) setG(null);
  };
  const nhap = x.duoc_nhap;
  return <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
    <p className="muted" style={{ margin: 0 }}>Giá bán / phòng / đêm, CHƯA gồm thuế phí ({h.khach_san.thue_phi_pt || 0}% — sửa ở tab Thông tin). Đêm thứ Sáu, thứ Bảy dùng «giá cuối tuần» nếu có.
      Đêm nào không nằm trong mùa giá nào thì gói đó không bán cho kỳ ở ấy. Sửa gói đã duyệt → về Nháp, thôi hiện trên cổng tới khi duyệt lại.</p>
    {nhap && !lp && <button className="act teal" style={{ alignSelf: "flex-start" }} onClick={() => setLp({ ...LP0 })}>+ Thêm loại phòng</button>}
    {lp && <div className="panel" style={{ margin: 0 }}><b>{lp.id ? `Sửa ${lp.ten}` : "Loại phòng mới"}</b>
      <div className="grid">{([["ten", "Tên loại phòng", "Deluxe hướng biển"], ["dien_tich", "Diện tích (m²)", "32"], ["giuong", "Giường", "1 giường đôi lớn"], ["mo_ta", "Đặc điểm", "Ban công hướng biển · bồn tắm"],
        ["toi_da_nguoi_lon", "Tối đa người lớn", "2"], ["toi_da_tre_em", "Tối đa trẻ em", "1"], ["so_phong", "Số phòng VTD được bán mỗi đêm", "3"], ["thu_tu", "Thứ tự hiện", "0"]] as const).map(([k2, t2, ph]) =>
        <label key={k2}>{t2}<input value={lp[k2] ?? ""} placeholder={ph} onChange={(e) => setLp({ ...lp, [k2]: e.target.value })} /></label>)}
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={lp.dang_ban} onChange={(e) => setLp({ ...lp, dang_ban: e.target.checked })} />Đang bán</label></div>
      <button className="act teal" disabled={busy} onClick={luuLp}>Lưu loại phòng</button> <button className="act grey" onClick={() => setLp(null)}>Thôi</button></div>}
    {h.loai_phong.map((p: any) => <div key={p.id} className="panel" style={{ margin: 0 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}><b style={{ fontSize: 16 }}>{p.ten}</b>
        <span className="muted">{[p.dien_tich ? `${p.dien_tich} m²` : "", p.giuong, `tối đa ${p.toi_da_nguoi_lon} NL${p.toi_da_tre_em ? ` + ${p.toi_da_tre_em} TE` : ""}`, `${p.so_phong} phòng / đêm`].filter(Boolean).join(" · ")}</span>
        {!p.dang_ban && <Tag cls="warn">Ngừng bán</Tag>}<span style={{ flex: 1 }} />
        {nhap && <><button className="act grey" onClick={() => setLp({ ...p })}>Sửa phòng</button>
          <button className="act grey" onClick={() => setG({ lid: p.id, ten: "Chỉ phòng", bua_sang: false, huy_truoc_ngay: 2, dang_ban: true, mua: [{ ...MUA0 }] })}>+ Gói giá</button></>}</div>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Gói</th><th>Mùa giá (giá / đêm, chưa thuế phí)</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{p.goi.map((q: any) => <tr key={q.id} className="ksv-goi">
          <td><b>{q.ten}</b><div className="muted">{q.bua_sang ? "Có bữa sáng" : "Chỉ phòng"} · {q.huy_truoc_ngay === null ? "Không hoàn tiền" : `Miễn phí hủy trước ${q.huy_truoc_ngay} ngày`}{q.dang_ban ? "" : " · ngừng bán"}</div></td>
          <td>{q.mua.map((m: any) => <div key={m.id}>{m.tu_ngay.split("-").reverse().join("/")} – {m.den_ngay.split("-").reverse().join("/")}: <b>{tien(m.gia_thuong)}</b>{m.gia_cuoi_tuan ? ` · T6-T7 ${tien(m.gia_cuoi_tuan)}` : ""}{m.gia_niem_yet ? <span className="muted"> · niêm yết {tien(m.gia_niem_yet)}</span> : null}</div>)}</td>
          <td><Tag cls={TT[q.trang_thai]}>{q.trang_thai_ten}</Tag><div className="muted" style={{ fontSize: 12 }}>nhập: {q.sua_boi}{q.duyet_boi ? ` · duyệt: ${q.duyet_boi}` : ""}</div>
            {q.ly_do_tra_lai && <small style={{ color: "#d99a2b" }}>Trả lại: {q.ly_do_tra_lai}</small>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{nhap && <button className="act grey" onClick={() => setG({ lid: p.id, ...q, huy_truoc_ngay: q.huy_truoc_ngay ?? "", mua: q.mua.map((m: any) => ({ ...m, gia_cuoi_tuan: m.gia_cuoi_tuan ?? "", gia_niem_yet: m.gia_niem_yet ?? "" })) })}>Sửa</button>}
            {nhap && ["nhap", "tra_lai"].includes(q.trang_thai) && <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/goi/${q.id}/gui-duyet`, {})}>Gửi duyệt</button>}</td></tr>)}
          {!p.goi.length && <tr><td colSpan={4} className="muted">Chưa có gói giá — khách thấy «Giá đang cập nhật» và gửi yêu cầu.</td></tr>}</tbody></table></div>
      {g && g.lid === p.id && <div className="panel" style={{ margin: "8px 0 0" }}><b>{g.id ? `Sửa gói ${g.ten}` : "Gói giá mới"}</b>
        <div className="grid">
          <label>Tên gói<input value={g.ten} onChange={(e) => setG({ ...g, ten: e.target.value })} placeholder="Chỉ phòng / Có bữa sáng" /></label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={g.bua_sang} onChange={(e) => setG({ ...g, bua_sang: e.target.checked })} />Có bữa sáng</label>
          <label>Hủy phòng<select value={g.huy_truoc_ngay === "" || g.huy_truoc_ngay === null ? "khong" : String(g.huy_truoc_ngay)} onChange={(e) => setG({ ...g, huy_truoc_ngay: e.target.value === "khong" ? "" : Number(e.target.value) })}>
            <option value="khong">Không hoàn tiền</option>{[0, 1, 2, 3, 5, 7, 14, 30].map((n) => <option key={n} value={n}>Miễn phí hủy trước {n} ngày</option>)}</select></label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={g.dang_ban} onChange={(e) => setG({ ...g, dang_ban: e.target.checked })} />Đang bán</label></div>
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Từ ngày</th><th>Đến ngày (gồm)</th><th>Giá ngày thường</th><th>Giá T6–T7</th><th>Giá niêm yết KS</th><th>Ghi chú</th><th></th></tr></thead>
          <tbody>{g.mua.map((m: any, i: number) => { const s = (k2: string, v: any) => setG({ ...g, mua: g.mua.map((y: any, j: number) => j === i ? { ...y, [k2]: v } : y) });
            return <tr key={i}><td><input type="date" value={m.tu_ngay} onChange={(e) => s("tu_ngay", e.target.value)} aria-label="Từ ngày" /></td>
              <td><input type="date" value={m.den_ngay} onChange={(e) => s("den_ngay", e.target.value)} aria-label="Đến ngày" /></td>
              <td><input inputMode="numeric" value={m.gia_thuong} onChange={(e) => s("gia_thuong", e.target.value)} placeholder="1.790.000" aria-label="Giá ngày thường" /></td>
              <td><input inputMode="numeric" value={m.gia_cuoi_tuan} onChange={(e) => s("gia_cuoi_tuan", e.target.value)} placeholder="để trống = như ngày thường" aria-label="Giá cuối tuần" /></td>
              <td><input inputMode="numeric" value={m.gia_niem_yet} onChange={(e) => s("gia_niem_yet", e.target.value)} placeholder="không bắt buộc" aria-label="Giá niêm yết" /></td>
              <td><input value={m.ghi_chu} onChange={(e) => s("ghi_chu", e.target.value)} aria-label="Ghi chú" /></td>
              <td><button className="act grey" onClick={() => setG({ ...g, mua: g.mua.filter((_: any, j: number) => j !== i) })}>Bỏ</button></td></tr>; })}</tbody></table></div>
        <button className="act grey" onClick={() => setG({ ...g, mua: [...g.mua, { ...MUA0 }] })}>+ Thêm mùa</button>{" "}
        <button className="act teal" disabled={busy} onClick={luuGoi}>Lưu gói</button> <button className="act grey" onClick={() => setG(null)}>Thôi</button>
        <p className="muted" style={{ fontSize: 12 }}>Chỉ GIÁ BÁN cho khách. Lưu xong gói ở trạng thái «Nháp» — bấm «Gửi duyệt» để TP Điều hành duyệt; người nhập không tự duyệt.</p></div>}
    </div>)}
    {!h.loai_phong.length && <p className="muted">Chưa có loại phòng.</p>}
  </div>;
}

function ChoDuyet({ toast, onDoi }: { toast: (m: string, l?: boolean) => void; onDoi: () => void }) {
  const [x, setX] = useState<any>(null);
  const [chon, setChon] = useState<number[]>([]);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/khach-san-vtd/cho-duyet").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setChon([]); load(); onDoi(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  return <section className="panel" id="ksv-cho-duyet">
    <h2 style={{ marginTop: 0 }}>Chờ duyệt</h2>
    {!x.duoc_duyet && <p className="muted">TP Điều hành duyệt. Bạn chỉ xem.</p>}
    <label>Lý do trả lại (bắt buộc khi trả lại)<input value={lyDo} onChange={(e) => setLyDo(e.target.value)} placeholder="vd: ảnh mờ, giá cuối tuần thấp hơn ngày thường" /></label>
    <h3>Ảnh ({x.anh.length})</h3>
    {x.duoc_duyet && x.anh.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
      <button className="act grey" onClick={() => setChon(x.anh.filter((a: any) => a.tai_boi !== x.toi || x.toan_quyen).map((a: any) => a.id))}>Chọn tất cả ({x.anh.length})</button>
      <button className="act teal" disabled={busy || !chon.length} onClick={() => goi("/khach-san-vtd/anh/duyet", { ids: chon, dong_y: true })}>Duyệt {chon.length} ảnh</button>
      <button className="act grey" disabled={busy || !chon.length || lyDo.trim().length < 5} onClick={() => goi("/khach-san-vtd/anh/duyet", { ids: chon, dong_y: false, ly_do: lyDo })}>Trả lại</button></div>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 10 }}>{x.anh.slice(0, 120).map((a: any) =>
      <label key={a.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 4, cursor: "pointer" }}>
        <AnhNoiBo src={a.nho} alt={a.chu_thich || a.nhom_ten} style={{ width: "100%", aspectRatio: "4 / 3", borderRadius: 6 }} />
        <span style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" disabled={!x.duoc_duyet || (a.tai_boi === x.toi && !x.toan_quyen)} checked={chon.includes(a.id)} onChange={(e) => setChon(e.target.checked ? [...chon, a.id] : chon.filter((y) => y !== a.id))} />
          <b style={{ fontSize: 13 }}>{a.khach_san}</b></span>
        <small className="muted">{a.nhom_ten} · tải: {a.tai_boi}{a.tai_boi === x.toi && !x.toan_quyen ? " (bạn tải — không tự duyệt)" : ""}</small></label>)}</div>
    {x.anh.length > 120 && <p className="muted">Hiện 120 / {x.anh.length} ảnh — duyệt xong lô này để xem tiếp.</p>}
    <h3>Gói giá ({x.goi.length})</h3>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Khách sạn · phòng · gói</th><th>Mùa giá</th><th>Nhập</th><th></th></tr></thead>
      <tbody>{x.goi.map((g: any) => <tr key={g.id}>
        <td><b>{g.khach_san}</b><div>{g.loai_phong} · {g.ten}</div><div className="muted">{g.bua_sang ? "Có bữa sáng" : "Chỉ phòng"} · {g.huy_truoc_ngay === null ? "Không hoàn tiền" : `Miễn phí hủy trước ${g.huy_truoc_ngay} ngày`}</div></td>
        <td>{g.mua.map((m: any) => <div key={m.id}>{m.tu_ngay.split("-").reverse().join("/")} – {m.den_ngay.split("-").reverse().join("/")}: <b>{tien(m.gia_thuong)}</b>{m.gia_cuoi_tuan ? ` · T6-T7 ${tien(m.gia_cuoi_tuan)}` : ""}{m.gia_niem_yet ? ` · niêm yết ${tien(m.gia_niem_yet)}` : ""}</div>)}</td>
        <td>{g.sua_boi}</td>
        <td style={{ whiteSpace: "nowrap" }}>{x.duoc_duyet && (g.sua_boi !== x.toi || x.toan_quyen) ? <>
          <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/goi/${g.id}/duyet`, { dong_y: true })}>Duyệt</button>{" "}
          <button className="act grey" disabled={busy || lyDo.trim().length < 5} onClick={() => goi(`/khach-san-vtd/goi/${g.id}/duyet`, { dong_y: false, ly_do: lyDo })}>Trả lại</button></>
          : <span className="muted">{g.sua_boi === x.toi ? "Bạn nhập — không tự duyệt" : "Chờ TP Điều hành"}</span>}</td></tr>)}
        {!x.goi.length && <tr><td colSpan={4} className="muted">Không có gói chờ duyệt.</td></tr>}</tbody></table></div>
  </section>;
}

export default function Page() { return <Shell><Trang /></Shell>; }
