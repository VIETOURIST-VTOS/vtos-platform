"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { AnhNoiBo } from "@/components/nha-hang/AlbumNhaHang";
import DanhGiaKsNoiBo from "@/components/khach-san-vtd/DanhGiaKsNoiBo";

/** KS-13 · KHÁCH SẠN HỢP TÁC (CỔNG KHÁCH) — Chủ tịch duyệt bản demo 30/10/2026.
 *  NV / TP Điều hành nhập khách sạn, ảnh, loại phòng, gói giá và mùa giá (chỉ GIÁ BÁN, chưa thuế phí).
 *  TP Điều hành duyệt giá — người nhập không tự duyệt (trừ Chủ tịch, TGĐ). Sửa gói đã duyệt → về Nháp, thôi hiện.
 *  KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh — tải là hiện; người tải tự xóa, TP Điều hành xóa mọi ảnh.
 *  TP Điều hành bật «Hiện trên cổng» khi đủ điều kiện; người vừa sửa hồ sơ không tự bật.
 *  KS-14 (Chủ tịch duyệt bản xem thử 30/10/2026): khách trả ngay 100%. Điều hành sửa số phòng bán mỗi đêm (tab «Phòng trống»),
 *  chốt đơn đã trả với khách sạn hoặc báo hết phòng (tab «Đơn đặt phòng»); Sales xác nhận hoàn, Kế toán ghi sổ thu hộ,
 *  đối soát thẻ, hoàn tiền, chốt hoa hồng (tab «Tiền & hoàn»). */
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
  const [tab, setTab] = useState<"ds" | "cd" | "don" | "tien" | "dg">("ds");
  const [demDon, setDemDon] = useState<any>({});
  useEffect(() => { api<any>("/khach-san-vtd/don?loc=cho_chot").then((r) => setDemDon(r.dem || {})).catch(() => {}); }, [tab]);
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
      ảnh, giá và bật «Hiện trên cổng». Người nhập không tự duyệt / tự bật (trừ Chủ tịch, TGĐ). Gói đã duyệt: khách đặt và trả ngay 100% (QR / thẻ),
      Điều hành chốt với khách sạn ở tab «Đơn đặt phòng»; chưa có giá thì khách gửi yêu cầu vào màn «Đơn khách sạn OTA › Yêu cầu của khách».
      Tiền phòng là tiền thu hộ khách sạn; hoa hồng Kế toán chốt ở tab «Tiền &amp; hoàn».</p>
    <div style={{ display: "flex", gap: 6, margin: "10px 0" }}>
      <button className={`act ${tab === "ds" ? "teal" : "grey"}`} onClick={() => setTab("ds")}>Khách sạn ({x.khach_san.length})</button>
      <button className={`act ${tab === "cd" ? "teal" : "grey"}`} onClick={() => setTab("cd")}>Chờ duyệt ({x.cho_duyet.goi} gói giá)</button>
      <button className={`act ${tab === "don" ? "teal" : "grey"}`} onClick={() => setTab("don")}>Đơn đặt phòng{demDon.da_tra ? ` (${demDon.da_tra} chờ chốt)` : ""}</button>
      <button className={`act ${tab === "tien" ? "teal" : "grey"}`} onClick={() => setTab("tien")}>Tiền &amp; hoàn</button>
      <button className={`act ${tab === "dg" ? "teal" : "grey"}`} onClick={() => setTab("dg")}>Đánh giá</button></div>
    {tab === "cd" && <ChoDuyet toast={toast} onDoi={load} />}
    {tab === "don" && <DonDat toast={toast} />}
    {tab === "tien" && <TienHoan toast={toast} />}
    {tab === "dg" && <DanhGiaKsNoiBo toast={toast} />}
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
  const [t, setT] = useState<"tt" | "anh" | "phong" | "trong" | "hien">("tt");
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
      {([["tt", "Thông tin"], ["anh", `Album ảnh (${h?.anh.length ?? 0})`], ["phong", `Loại phòng & giá (${h?.loai_phong.length ?? 0})`], ["trong", "Phòng trống"], ["hien", "Hiện trên cổng"]] as const).map(([k2, t2]) =>
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
    {h && t === "trong" && <PhongTrong kid={h.khach_san.id} toast={toast} />}
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
    <p className="muted" style={{ margin: 0, fontSize: 12 }}>Ảnh tải lên là hiện ngay trên cổng (Chủ tịch bỏ khâu duyệt ảnh 31/10/2026). Ảnh sai: người tải tự xóa, TP Điều hành xóa được mọi ảnh.</p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 10 }}>{h.anh.map((a: any) =>
      <div key={a.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
        <AnhNoiBo src={a.nho} alt={a.chu_thich || a.nhom_ten} style={{ width: "100%", aspectRatio: "4 / 3", borderRadius: 6 }} />
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <Tag cls={TT[a.trang_thai]}>{a.trang_thai === "da_duyet" ? "Đang hiện" : a.trang_thai_ten}</Tag>{a.la_bia && <Tag cls="ok">Bìa</Tag>}<span className="muted" style={{ fontSize: 12 }}>{a.nhom_ten}{a.loai_phong_id ? ` · ${tenLp[a.loai_phong_id] || ""}` : ""}</span></div>
        {a.ly_do_tra_lai && <small style={{ color: "#d99a2b" }}>Trả lại: {a.ly_do_tra_lai}</small>}
        <small className="muted">tải: {a.tai_boi}{a.duyet_boi && a.duyet_boi !== "tu_dong" ? ` · duyệt: ${a.duyet_boi}` : ""}</small>
        {x.duoc_nhap && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {a.trang_thai === "da_duyet" && !a.la_bia && <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}`, { la_bia: true })}>Đặt bìa</button>}
          {a.trang_thai !== "an" ? <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: true })}>Ẩn</button>
            : <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: false })}>Bỏ ẩn</button>}
          {(a.tai_boi === x.toi || x.duoc_duyet) && <button className="act grey" disabled={busy} onClick={() => { if (window.confirm("Xóa ảnh này khỏi album?")) goi(`/khach-san-vtd/anh/${a.id}/xoa`, {}); }}>Xóa</button>}</div>}
      </div>)}
      {!h.anh.length && <p className="muted">Chưa có ảnh. Ảnh do khách sạn gửi hoặc VTD tự chụp; tải lên là hiện trên cổng.</p>}</div>
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

/* ── KS-14 · Phòng trống, Đơn đặt phòng, Tiền & hoàn ─────────────────────────────────────────────── */
const hom = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
const THU2 = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const dm = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().slice(0, 2).join("/") : "");
const gio = (s?: string | null) => (s ? `${s.slice(11, 16)} ${dm(s)}` : "");
const MAU_DON: Record<string, string> = { cho_tra: "warn", het_han: "", da_tra: "warn", da_xac_nhan: "ok", da_huy: "bad" };

function PhongTrong({ kid, toast }: { kid: number; toast: (m: string, l?: boolean) => void }) {
  const [tu, setTu] = useState(hom());
  const [b, setB] = useState<any>(null);
  const [sua, setSua] = useState<any>(null);   // {lid, ten, ngay:[...], so_ban, dong}
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>(`/khach-san-vtd/don/phong-trong/${kid}?tu=${tu}&so_ngay=14`).then(setB).catch((e) => toast(errMsg(e), true)); }, [kid, tu, toast]);
  useEffect(() => { load(); }, [load]);
  const luu = async (dong: boolean, veMacDinh = false) => {
    setBusy(true);
    try { const r = await api<any>(`/khach-san-vtd/don/phong-trong/${sua.lid}`, { method: "POST",
      json: { ngay: sua.ngay, so_ban: veMacDinh || sua.so_ban === "" ? null : Number(sua.so_ban), dong } }); toast(r.message); setSua(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!b) return <p className="muted">Đang tải…</p>;
  const chonO = (p: any, o: any) => {
    if (!b.duoc_sua) return;
    if (sua && sua.lid === p.id) { const ngay = sua.ngay.includes(o.ngay) ? sua.ngay.filter((x: string) => x !== o.ngay) : [...sua.ngay, o.ngay]; setSua(ngay.length ? { ...sua, ngay } : null); }
    else setSua({ lid: p.id, ten: p.ten, ngay: [o.ngay], so_ban: o.da_sua ? String(o.ban) : "", dong: o.dong });
  };
  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    <p className="muted" style={{ margin: 0 }}>Số phòng VTD được bán mỗi đêm. Mặc định = «số phòng / đêm» ở hồ sơ loại phòng; bấm ô để sửa hoặc đóng bán (chọn nhiều ô cùng loại phòng rồi lưu một lần).
      Ô ghi <b>còn / tổng</b>; «đã nhận» gồm đơn đang giữ 15 phút chờ trả tiền, đã trả và đã xác nhận.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <button className="act grey" onClick={() => { const d = new Date(tu + "T00:00:00"); d.setDate(d.getDate() - 14); const s2 = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); setTu(s2 < hom() ? hom() : s2); }}>← 14 ngày</button>
      <input type="date" value={tu} min={hom()} onChange={(e) => e.target.value && setTu(e.target.value)} aria-label="Từ ngày" style={{ maxWidth: 170 }} />
      <button className="act grey" onClick={() => { const d = new Date(tu + "T00:00:00"); d.setDate(d.getDate() + 14); setTu(new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)); }}>14 ngày →</button></div>
    <div style={{ overflowX: "auto" }}><table className="ksv-lich"><thead><tr><th style={{ textAlign: "left" }}>Loại phòng</th>
      {b.ngay.map((n: string) => { const d = new Date(n + "T00:00:00"); return <th key={n} style={{ textAlign: "center", whiteSpace: "nowrap" }}>{THU2[d.getDay()]}<br />{dm(n)}</th>; })}</tr></thead>
      <tbody>{b.phong.map((p: any) => <tr key={p.id}><td><b>{p.ten}</b><div className="muted">{p.so_phong} phòng / đêm{p.dang_ban ? "" : " · ngừng bán"}</div></td>
        {p.o.map((o: any) => { const on = sua && sua.lid === p.id && sua.ngay.includes(o.ngay);
          return <td key={o.ngay} style={{ padding: 3 }}><button type="button" disabled={!b.duoc_sua} onClick={() => chonO(p, o)} aria-pressed={!!on}
            aria-label={`${p.ten} đêm ${dm(o.ngay)}: ${o.dong ? "đóng bán" : `còn ${o.con} trên ${o.ban}`}`}
            className={`ksv-o ${o.dong ? "dong" : o.con === 0 ? "het" : ""} ${on ? "chon" : ""}`}>
            {o.dong ? "Đóng" : <>{o.con}<span className="muted">/{o.ban}</span></>}{o.da_sua && !o.dong ? <i>•</i> : null}</button></td>; })}</tr>)}
        {!b.phong.length && <tr><td colSpan={15} className="muted">Chưa có loại phòng.</td></tr>}</tbody></table></div>
    {sua && <div className="panel" style={{ margin: 0 }}><b>{sua.ten} · {sua.ngay.length} đêm: {[...sua.ngay].sort().map(dm).join(", ")}</b>
      <div className="grid"><label>Số phòng bán mỗi đêm (để trống = theo hồ sơ)<input inputMode="numeric" value={sua.so_ban} onChange={(e) => setSua({ ...sua, so_ban: e.target.value.replace(/\D/g, "") })} /></label></div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button className="act teal" disabled={busy} onClick={() => luu(false)}>Lưu số phòng</button>
        <button className="act grey" disabled={busy} onClick={() => luu(true)}>Đóng bán các đêm này</button>
        <button className="act grey" disabled={busy} onClick={() => luu(false, true)}>Về theo hồ sơ</button>
        <button className="act grey" onClick={() => setSua(null)}>Thôi</button></div></div>}
    <style>{`.ksv-lich td,.ksv-lich th{padding:6px}.ksv-o{min-width:46px;min-height:44px;border-radius:6px;border:1px solid transparent;background:#1c3d5e;color:inherit;font:inherit;cursor:pointer;position:relative}
      .ksv-o.het{background:#5a4614;color:#ffe08a}.ksv-o.dong{background:#4a2330;color:#ffb4bf;font-weight:700}.ksv-o.chon{border-color:#4cc38a;box-shadow:0 0 0 2px #4cc38a}
      .ksv-o i{position:absolute;top:2px;right:4px;font-style:normal;color:#7fc4ff}.ksv-o:disabled{cursor:default}`}</style>
  </div>;
}

function DongDon({ d }: { d: any }) {
  return <><td><b>{d.ma}</b><div className="muted">{d.ho_ten} · {d.lien_he}</div></td>
    <td>{d.khach_san?.ten}<div className="muted">{d.dong.map((x: any) => `${x.so} × ${x.loai_phong} · ${x.goi}`).join("; ")}</div></td>
    <td style={{ whiteSpace: "nowrap" }}>{dm(d.vao)} – {dm(d.ra)}<div className="muted">{d.dem} đêm · {d.nguoi_lon} NL{d.tre_em ? ` + ${d.tre_em} TE` : ""}</div></td>
    <td style={{ whiteSpace: "nowrap" }}>₫ {tien(d.tong)}<div className="muted">đã trả {tien(d.da_tra)}{d.thanh_toan?.length ? ` · ${d.thanh_toan.map((t: any) => t.kenh === "qr" ? "QR" : "thẻ").join(", ")}` : ""}</div>
      {d.giam_voucher > 0 && <div className="muted" style={{ color: "#ffcf7a" }}>voucher {d.voucher?.ma} −{tien(d.giam_voucher)}{d.voucher?.trang_thai === "da_hoan" ? " · đã trả điểm" : " · VTD chịu"}</div>}</td></>;
}

function DonDat({ toast }: { toast: (m: string, l?: boolean) => void }) {
  const [loc, setLoc] = useState("cho_chot");
  const [x, setX] = useState<any>(null);
  const [o, setO] = useState<Record<number, { ma: string; ly: string }>>({});
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>(`/khach-san-vtd/don?loc=${loc}`).then(setX).catch((e) => toast(errMsg(e), true)); }, [loc, toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { await api<any>(path, { method: "POST", json }); toast("Đã lưu"); load(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const v = (id: number) => o[id] || { ma: "", ly: "" };
  return <section className="panel">
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
      {([["cho_chot", `Chờ chốt với khách sạn (${x.dem.da_tra || 0})`], ["da_xac_nhan", `Đã xác nhận (${x.dem.da_xac_nhan || 0})`], ["cho_tra", `Chờ thanh toán (${x.dem.cho_tra || 0})`],
        ["da_huy", `Đã hủy (${x.dem.da_huy || 0})`], ["", "Tất cả"]] as const).map(([k, t]) =>
        <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{t}</button>)}</div>
    <p className="muted" style={{ margin: "0 0 8px" }}>Đơn khách đã trả 100%. Điều hành gọi khách sạn chốt phòng trong 2 giờ làm việc rồi nhập mã xác nhận của khách sạn — khách nhận phiếu ngay.
      Khách sạn không giữ được phòng → bấm «KS hết phòng»: đơn hủy, hoàn 100% qua Sales → Kế toán.</p>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn · phòng</th><th>Ngày ở</th><th>Tiền</th><th>Trạng thái</th><th>Việc</th></tr></thead>
      <tbody>{x.don.map((d: any) => <tr key={d.id}><DongDon d={d} />
        <td><Tag cls={MAU_DON[d.trang_thai]}>{d.trang_thai_ten}</Tag>
          {d.trang_thai === "da_tra" && <div style={{ color: d.qua_han_chot ? "#ff8a9a" : undefined, fontWeight: d.qua_han_chot ? 700 : 400 }}>{d.qua_han_chot ? "Quá hạn chốt" : "Hạn chốt"} {gio(d.han_chot)}</div>}
          {d.trang_thai === "da_xac_nhan" && <div className="muted">mã KS {d.ma_xac_nhan_ks} · {d.xac_nhan_boi}</div>}
          {d.trang_thai === "da_huy" && <div className="muted">{d.ly_do_huy}{d.so_hoan ? ` · hoàn ${tien(d.so_hoan)} (${d.hoan_tt_ten || "xong"})` : ""}</div>}
          {d.yeu_cau && <div className="muted">Yêu cầu: {d.yeu_cau}</div>}</td>
        <td style={{ minWidth: 230 }}>{x.vai.dh && ["da_tra"].includes(d.trang_thai) && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label>Mã xác nhận của khách sạn<input value={v(d.id).ma} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ma: e.target.value } })} /></label>
          <button className="act teal" disabled={busy || v(d.id).ma.trim().length < 3} onClick={() => goi(`/khach-san-vtd/don/${d.id}/xac-nhan`, { ma_ks: v(d.id).ma })}>Đã xác nhận → gửi phiếu</button></div>}
          {x.vai.dh && ["da_tra", "da_xac_nhan"].includes(d.trang_thai) && <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
            <label>Lý do (khi khách sạn hết phòng)<input value={v(d.id).ly} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ly: e.target.value } })} placeholder="KS báo hết Deluxe ngày 6/11" /></label>
            <button className="act grey" style={{ color: "#ffb4bf" }} disabled={busy || v(d.id).ly.trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/het-phong`, { ly_do: v(d.id).ly })}>KS hết phòng → hoàn 100%</button></div>}
          {x.vai.mien_phat && d.trang_thai === "da_huy" && d.giu_lai > 0 && d.hoa_hong === null && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label>Lý do miễn phạt<input value={v(d.id).ly} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ly: e.target.value } })} /></label>
            <button className="act grey" disabled={busy || v(d.id).ly.trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/mien-phat`, { ly_do: v(d.id).ly })}>Miễn phạt · hoàn đủ {tien(d.da_tra)}</button></div>}
        </td></tr>)}
        {!x.don.length && <tr><td colSpan={6} className="muted">Không có đơn.</td></tr>}</tbody></table></div>
  </section>;
}

function TienHoan({ toast }: { toast: (m: string, l?: boolean) => void }) {
  const [x, setX] = useState<any>(null);
  const [o, setO] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>("/khach-san-vtd/don/tien").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r?.message || "Đã lưu"); load(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const nhap = (k: string, ph = "", so = false) => <input value={o[k] || ""} placeholder={ph} inputMode={so ? "numeric" : undefined}
    onChange={(e) => setO({ ...o, [k]: so ? e.target.value.replace(/\D/g, "") : e.target.value })} style={{ minWidth: 150 }} />;
  const kt = x.vai.kt, sales = x.vai.sales;
  return <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
    <p className="muted" style={{ margin: 0 }}>Tiền phòng khách sạn VTD là tiền THU HỘ khách sạn (như đặt bàn DT-3): tiền vào Nợ 1121 / Có 3388, phí thẻ 6428, hoàn Nợ 3388 / Có 1121.
      Doanh thu Vietourist là hoa hồng Kế toán gõ theo hợp đồng sau khi khách trả phòng; phần còn lại trả khách sạn qua đề nghị chi NCC. Không ô nào gõ số tiền khách trả / số hoàn.</p>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>1 · Tiền vào chờ ghi sổ ({x.tien_cho.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Đơn</th><th>Cách trả</th><th>Số tiền</th><th>Trạng thái</th><th>Việc</th></tr></thead>
        <tbody>{x.tien_cho.map((t: any) => <tr key={t.id}><td><b>{t.ma}</b></td><td>{t.kenh_ten}{t.so_gd_cong ? ` · GD ${t.so_gd_cong}` : ""}</td><td>₫ {tien(t.so_tien)}</td><td>{t.trang_thai_ten}<div className="muted">{gio(t.luc)}</div></td>
          <td>{kt && (t.trang_thai === "tu_khop" ? <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/tt/${t.id}/xac-nhan`, {})}>Xác nhận · ghi sổ</button>
            : <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}><label>Phí thẻ theo sao kê{nhap(`phi${t.id}`, "0", true)}</label>
              <button className="act teal" disabled={busy || o[`phi${t.id}`] === undefined || o[`phi${t.id}`] === ""} onClick={() => goi(`/khach-san-vtd/don/tt/${t.id}/doi-soat`, { phi: Number(o[`phi${t.id}`]) })}>Đối soát</button></span>)}</td></tr>)}
          {!x.tien_cho.length && <tr><td colSpan={5} className="muted">Không có khoản chờ.</td></tr>}</tbody></table></div>
      {kt && <><h3>Giao dịch có mã đặt phòng chưa khớp ({x.giao_dich_cho.length})</h3>
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Lúc</th><th>Nội dung</th><th>Số tiền</th><th>Đơn</th><th>Việc</th></tr></thead>
          <tbody>{x.giao_dich_cho.map((g: any) => <tr key={g.txn_id}><td>{gio(g.luc)}</td><td>{g.noi_dung}<div className="muted">{g.ghi_chu}</div></td><td>₫ {tien(g.so_tien)}</td>
            <td><b>{g.ma}</b><div className="muted">{g.trang_thai_ten}{g.con_phai_tra != null ? ` · còn phải trả ${tien(g.con_phai_tra)}` : ""}</div></td>
            <td>{g.don_id && <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/${g.don_id}/gan-qr`, { txn_id: g.txn_id })}>Gán vào đơn · ghi sổ</button>}</td></tr>)}
            {!x.giao_dich_cho.length && <tr><td colSpan={5} className="muted">Không có giao dịch chờ.</td></tr>}</tbody></table></div></>}
      {x.thieu.length > 0 && <><h3>Đơn có tiền nhưng chưa đủ / đã hết giờ giữ ({x.thieu.length})</h3>
        <table><tbody>{x.thieu.map((d: any) => <tr key={d.id}><DongDon d={d} /><td>{kt && <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`cv${d.id}`, "Lý do")}
          <button className="act grey" disabled={busy || (o[`cv${d.id}`] || "").trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/chuyen-hoan`, { ly_do: o[`cv${d.id}`] })}>Hủy · hoàn đủ {tien(d.da_tra)}</button></span>}</td></tr>)}</tbody></table></>}
    </section>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>2 · Hoàn tiền — Sales xác nhận → Kế toán chuyển ({x.hoan.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn</th><th>Ngày ở</th><th>Tiền</th><th>Lý do · số hoàn</th><th>Việc</th></tr></thead>
        <tbody>{x.hoan.map((d: any) => <tr key={d.id}><DongDon d={d} /><td>{d.ly_do_huy}<div><b>Hoàn ₫ {tien(d.so_hoan - d.da_hoan_tien)}</b> · <Tag cls="warn">{d.hoan_tt_ten}</Tag></div>
          {d.hoan_ghi_chu && <div className="muted" style={{ whiteSpace: "pre-line" }}>{d.hoan_ghi_chu}</div>}</td>
          <td>{d.hoan_tt === "cho_sales" && (sales ? <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/${d.id}/sales-hoan`, {})}>Xác nhận số hoàn</button> : <span className="muted">chờ Sales</span>)}
            {d.hoan_tt === "cho_chi" && (kt ? <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`ct${d.id}`, "Số UNC / mã hoàn OnePay")}
              <button className="act teal" disabled={busy || (o[`ct${d.id}`] || "").trim().length < 3} onClick={() => goi(`/khach-san-vtd/don/${d.id}/da-hoan`, { ghi_chu: o[`ct${d.id}`] })}>Đã hoàn · ghi sổ</button></span> : <span className="muted">chờ Kế toán</span>)}</td></tr>)}
          {!x.hoan.length && <tr><td colSpan={6} className="muted">Không có khoản hoàn chờ.</td></tr>}</tbody></table></div></section>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>3 · Sau khi khách trả phòng — chốt hoa hồng ({x.cho_chot.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn</th><th>Ngày ở</th><th>Tiền</th><th>Giữ lại</th><th>Hoa hồng theo hợp đồng</th></tr></thead>
        <tbody>{x.cho_chot.map((d: any) => { const giu = d.da_tra - d.so_hoan + (d.khuyen_mai || 0); return <tr key={d.id}><DongDon d={d} /><td>₫ {tien(giu)}{d.khuyen_mai > 0 ? <div className="muted">gồm voucher VTD chịu {tien(d.khuyen_mai)} — chốt ghi Nợ 641 / Có 3388</div> : null}{d.trang_thai === "da_huy" ? <div className="muted">đơn hủy, giữ theo gói</div> : null}</td>
          <td>{kt ? <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`hh${d.id}`, "số tiền", true)}
            <button className="act teal" disabled={busy || !o[`hh${d.id}`]} onClick={() => goi(`/khach-san-vtd/don/${d.id}/chot`, { hoa_hong: Number(o[`hh${d.id}`]) })}>Chốt</button>
            {o[`hh${d.id}`] ? <span className="muted">→ trả khách sạn ₫ {tien(giu - Number(o[`hh${d.id}`]))}</span> : null}</span> : <span className="muted">Kế toán chốt</span>}</td></tr>; })}
          {!x.cho_chot.length && <tr><td colSpan={6} className="muted">Không có đơn chờ chốt.</td></tr>}</tbody></table></div>
      <h3>Phải trả từng khách sạn (đã chốt)</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Khách sạn</th><th>Số đơn</th><th>Tiền giữ lại</th><th>Voucher VTD chịu</th><th>Hoa hồng VTD</th><th>Phải trả khách sạn</th></tr></thead>
        <tbody>{x.phai_tra_ks.map((k: any) => <tr key={k.ma}><td><b>{k.khach_san}</b><div className="muted">{k.ma}</div></td><td>{k.so_don}</td><td>₫ {tien(k.giu_lai)}</td><td>₫ {tien(k.khuyen_mai || 0)}</td><td>₫ {tien(k.hoa_hong)}</td><td><b>₫ {tien(k.phai_tra)}</b></td></tr>)}
          {!x.phai_tra_ks.length && <tr><td colSpan={6} className="muted">Chưa có đơn đã chốt.</td></tr>}</tbody></table></div>
      <p className="muted" style={{ fontSize: 12 }}>Lập đề nghị chi NCC cho khoản «Phải trả khách sạn» ở màn Đề nghị chi như mọi khoản trả nhà cung cấp (Giám đốc duyệt chi).</p></section>
  </div>;
}
export default function Page() { return <Shell><Trang /></Shell>; }
