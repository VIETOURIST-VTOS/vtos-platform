"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getToken, taiTep } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KH-2 · NHÀ HÀNG (CỔNG KHÁCH) — Chủ tịch duyệt bản xem thử 26/10/2026.
 *  Điều hành nhập nhà hàng + thực đơn (chỉ GIÁ BÁN). TP Điều hành bật «Hiện trên cổng» (DT-2b, Chủ tịch 28/10/2026);
 *  người vừa nhập / sửa không tự bật.
 *  Sửa nội dung bán của nhà hàng đang hiện → máy chủ tự tắt và ghi lý do; TP Điều hành bật lại.
 *  AT-1 (Chủ tịch duyệt 28/10/2026): «Hiện trên cổng» = hiện GIỚI THIỆU trên web VTD. Mở đặt bàn do máy tính từ
 *  5 điều kiện (hợp đồng ký + tệp còn hiệu lực, gắn NCC, thực đơn đang bán, liên hệ xác minh, hoa hồng đã khai).
 *  Điều hành nhập danh sách từ tệp, xác minh, ghi nhận hợp đồng; Marketing viết giới thiệu, món ăn, điểm đến. */
const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const NH_TRONG = { ten: "", tinh_thanh: "", khu_vuc: "", am_thuc: "Việt Nam", gio_phuc_vu: "", tien_ich: "", mo_ta: "", ghi_chu_noi_bo: "" };
const HD_TRONG = { da_ky: false, so_hd: "", ngay_ky: "", tu_ngay: "", den_ngay: "", hoa_hong_pct: "", hoa_hong_co_dinh: "", co_so: "", ly_do: "" };
const ND_TRONG = { loai: "mon", ten: "", ten_khac: "", nhom: "", tinh_thanh: "", tom_tat: "", noi_dung: "", vung: "", nen_an: "", thanh_phan: "", cach_goi: "", nha_hang_ids: [] as number[], thu_tu: 0, hien: false };

async function guiTep(path: string, fd: FormData) {
  const headers: Record<string, string> = {}; const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const r = await fetch(`/api/v1${path}`, { method: "POST", headers, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw { status: r.status, message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}
const TD_TRONG = { ten: "", loai: "set", gia_nguoi_lon: "", gia_tre_em: "", so_khach_toi_thieu: 1, mo_ta: "", dieu_kien: "", dieu_kien_huy: "", tu_ngay: "", den_ngay: "", dang_ban: true };

function Trang() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const nhap = ["tp_dh", "nv_dh", "chutich", "tgd"].includes(role);
  const bat = ["tp_dh", "chutich", "tgd"].includes(role);
  const mkt = ["nv_mkt", "ptgd_mkt", "chutich", "tgd"].includes(role);
  const xemHd = nhap || ["ketoan", "bks"].includes(role);
  const [tab, setTab] = useState<"nh" | "nd">(["nv_mkt", "ptgd_mkt"].includes(role) ? "nd" : "nh");
  const [tim, setTim] = useState(""); const [locTinh, setLocTinh] = useState("");
  const [chon, setChon] = useState<number[]>([]);
  const [tep, setTep] = useState<File | null>(null); const [nguon, setNguon] = useState(""); const [thu, setThu] = useState<any>(null);
  const [hd, setHd] = useState<any>(HD_TRONG); const [tepHd, setTepHd] = useState<File | null>(null);
  const [gt, setGt] = useState<any>(null);
  const [nd, setNd] = useState<any>(null);
  const [anh, setAnh] = useState<{ tep: File | null; nguon: string }>({ tep: null, nguon: "" });
  const [timNh, setTimNh] = useState("");
  const [x, setX] = useState<any>(null);
  const [sua, setSua] = useState<any>(null);       // nhà hàng đang sửa (id hoặc "moi")
  const [f, setF] = useState<any>(NH_TRONG);
  const [td, setTd] = useState<any>(null);         // {id?, ...} gói đang sửa
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/nha-hang").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); load(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  const docTep = async (that: boolean) => {
    if (!tep) { toast("Chọn tệp CSV / Excel / JSON", true); return; }
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("tep", tep); fd.append("nguon", nguon); fd.append("thu", that ? "false" : "true");
      const r = await guiTep("/nha-hang/nhap-tep", fd); setThu(r);
      if (that) { toast(`Đã nhập ${r.moi} hồ sơ · bỏ qua ${r.trung} trùng`); setThu(null); setTep(null); load(); }
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const luuHd = async (nid: number) => {
    if (!tepHd) { toast("Tải tệp hợp đồng đã ký (PDF / ảnh)", true); return; }
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("tep", tepHd);
      Object.entries(hd).forEach(([k, v]) => fd.append(k, String(v ?? "")));
      const r = await guiTep(`/nha-hang/${nid}/hop-dong`, fd); toast(r.message); setHd(HD_TRONG); setTepHd(null); load();
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const taiAnh = async (doi: "nha_hang" | "noi_dung", id: number) => {
    if (!anh.tep) { toast("Chọn tệp ảnh", true); return; }
    setBusy(true);
    try {
      const fd = new FormData(); fd.append("tep", anh.tep); fd.append("nguon", anh.nguon);
      const r = await guiTep(`/nha-hang/anh/${doi}/${id}`, fd); toast(r.message); setAnh({ tep: null, nguon: "" }); load();
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const xemAnh = (aid: number) => taiTep(`/nha-hang/anh/${aid}`, `anh_${aid}.jpg`).catch((e) => toast(errMsg(e), true));
  const oAnh = (doi: "nha_hang" | "noi_dung", id: number, co: boolean, nguonCu: string, aid?: number) => <div className="panel" style={{ marginTop: 8 }}>
    <b>Ảnh trên web VTD</b> {co ? <><Tag cls="ok">Có ảnh</Tag><span className="muted"> nguồn: {nguonCu}</span>{aid && <button className="act grey" onClick={() => xemAnh(aid)}>Tải ảnh</button>}</> : <Tag cls="warn">Chưa có ảnh</Tag>}
    <div className="grid">
      <label>Tệp ảnh (JPG / PNG / WEBP)<input type="file" accept="image/*" onChange={(e) => setAnh({ ...anh, tep: e.target.files?.[0] || null })} /></label>
      <label>Nguồn ảnh (bắt buộc)<input value={anh.nguon} placeholder="VTD chụp / nhà hàng cấp quyền / Unsplash – tên tác giả" onChange={(e) => setAnh({ ...anh, nguon: e.target.value })} /></label></div>
    <button className="act teal" disabled={busy} onClick={() => taiAnh(doi, id)}>{co ? "Thay ảnh" : "Tải ảnh lên"}</button>
  </div>;
  if (!x) return <p className="muted">Đang tải…</p>;
  const k = (s: string) => (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/gi, "d").toLowerCase();
  const loc = x.nha_hang.filter((n: any) => (!locTinh || n.tinh_thanh === locTinh) && (!tim || k(`${n.ten} ${n.tinh_thanh} ${n.dia_danh_nguon} ${n.mon_noi_bat} ${n.ma}`).includes(k(tim))));
  const cacTinh = Array.from(new Set(x.nha_hang.map((n: any) => n.tinh_thanh).filter(Boolean))).sort() as string[];
  const dang = sua && sua !== "moi" ? x.nha_hang.find((n: any) => n.id === sua) : null;
  const o = (k: string, nhan: string, ph = "") => <label>{nhan}<input value={f[k]} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  const t = (k: string, nhan: string, type = "text") => <label>{nhan}<input type={type} value={td[k] ?? ""} onChange={(e) => setTd({ ...td, [k]: e.target.value })} /></label>;
  const luuTd = async () => {
    const body = { ...td, gia_nguoi_lon: td.gia_nguoi_lon === "" ? null : Number(td.gia_nguoi_lon), gia_tre_em: td.gia_tre_em === "" || td.gia_tre_em == null ? null : Number(td.gia_tre_em),
      so_khach_toi_thieu: Number(td.so_khach_toi_thieu || 1), tu_ngay: td.tu_ngay || null, den_ngay: td.den_ngay || null };
    const r = await goi(`/nha-hang/${dang.id}/thuc-don${td.id ? `/${td.id}` : ""}`, body);
    if (r) setTd(null);
  };
  return (<>
    <h1>Nhà hàng (cổng khách)</h1>
    <p className="muted">Điều hành nhập và sửa. Chỉ TP Điều hành bật «Hiện trên cổng»; người vừa nhập / sửa không tự bật. Sửa giá hoặc thực đơn của nhà hàng đang hiện → tự tắt, chờ TP Điều hành bật lại.
      Chỉ nhập <b>giá bán cho khách</b>; giá vốn / phí NCC theo hợp đồng nhà cung cấp, không nhập ở đây.</p>
    <div style={{ display: "flex", gap: 6, margin: "8px 0" }}>
      <button className={`act ${tab === "nh" ? "teal" : "grey"}`} onClick={() => setTab("nh")}>Nhà hàng</button>
      <button className={`act ${tab === "nd" ? "teal" : "grey"}`} onClick={() => setTab("nd")}>Nội dung ẩm thực (Marketing)</button></div>

    {tab === "nd" && <section className="panel">
      <h2>Nội dung trang «Hương vị Việt Nam»</h2>
      <p className="muted">Marketing viết bằng lời Vietourist — không chép chữ, ảnh, điểm hay nhận xét của trang ngoài. Ảnh phải ghi nguồn. Chỉ mục bật «Hiện» mới lên web VTD.
        Loại «Giới thiệu thành phố» gắn với một trong {x.thanh_pho.length} thành phố ẩm thực; «Ảnh bìa trang» là ảnh lớn đầu trang (chỉ cần một mục).</p>
      <div className="wrap"><table><thead><tr><th>Loại</th><th>Tên</th><th>Nhóm · thành phố</th><th>Ảnh</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{x.noi_dung.map((c: any) => <tr key={c.id}><td>{c.loai_ten}</td><td><b>{c.ten}</b>{c.ten_khac && <div className="muted">{c.ten_khac}</div>}<div className="muted">{c.tom_tat}</div></td>
          <td>{[c.nhom, c.tinh_thanh].filter(Boolean).join(" · ")}{c.nha_hang_ids.length > 0 && <div className="muted">{c.nha_hang_ids.length} nhà hàng «ăn ở đâu»</div>}</td>
          <td>{c.co_anh ? <Tag cls="ok">Có</Tag> : <Tag cls="warn">Chưa</Tag>}</td>
          <td>{c.hien ? <Tag cls="ok">Đang hiện</Tag> : <Tag>Nháp</Tag>}<div className="muted">{c.sua_boi}</div></td>
          <td>{mkt && <button className="act grey" onClick={() => { setNd({ ...ND_TRONG, ...c }); setAnh({ tep: null, nguon: "" }); }}>Sửa</button>}</td></tr>)}
          {!x.noi_dung.length && <tr><td colSpan={6} className="muted">Chưa có nội dung. Marketing bấm «Thêm».</td></tr>}</tbody></table></div>
      {mkt && !nd && <button className="act teal" onClick={() => setNd({ ...ND_TRONG })}>+ Thêm nội dung</button>}
      {nd && <div className="panel" style={{ marginTop: 10 }}><div className="grid">
        <label>Loại<select value={nd.loai} onChange={(e) => setNd({ ...nd, loai: e.target.value })}>{Object.entries(x.loai_nd).map(([a, b]: any) => <option key={a} value={a}>{b}</option>)}</select></label>
        {nd.loai === "thanh_pho" ? <label>Thành phố<select value={nd.ten} onChange={(e) => setNd({ ...nd, ten: e.target.value })}><option value="">— chọn —</option>
          {x.thanh_pho.map((t: any) => <option key={t.ten} value={t.ten}>{t.ten} · {t.mien}</option>)}</select></label>
          : <label>Tên<input value={nd.ten} placeholder={nd.loai === "bia" ? "Hương vị Việt Nam" : ""} onChange={(e) => setNd({ ...nd, ten: e.target.value })} /></label>}
        {["mon", "dac_san"].includes(nd.loai) && <label>Tên khác / tiếng Anh<input value={nd.ten_khac} placeholder="Beef pho" onChange={(e) => setNd({ ...nd, ten_khac: e.target.value })} /></label>}
        {nd.loai === "mon" && <label>Nhóm món<select value={nd.nhom} onChange={(e) => setNd({ ...nd, nhom: e.target.value })}><option value="">— chọn —</option>{x.nhom_mon.map((g: string) => <option key={g}>{g}</option>)}</select></label>}
        {nd.loai === "dac_san" && <label>Loại đặc sản<input value={nd.nhom} placeholder="Nước mắm, cà phê, bánh…" onChange={(e) => setNd({ ...nd, nhom: e.target.value })} /></label>}
        {["mon", "dac_san", "danh_sach"].includes(nd.loai) && <label>Thành phố<select value={nd.tinh_thanh} onChange={(e) => setNd({ ...nd, tinh_thanh: e.target.value })}><option value="">— không —</option>
          {x.thanh_pho.map((t: any) => <option key={t.ten} value={t.ten}>{t.ten}</option>)}</select></label>}
        <label>{nd.loai === "thanh_pho" ? "Món đặc trưng (hiện dưới tên)" : nd.loai === "bia" ? "Lời dẫn đầu trang" : "Tóm tắt (1 câu)"}<input value={nd.tom_tat} onChange={(e) => setNd({ ...nd, tom_tat: e.target.value })} /></label>
        <label>Thứ tự hiện<input type="number" value={nd.thu_tu} onChange={(e) => setNd({ ...nd, thu_tu: Number(e.target.value) })} /></label>
        {nd.loai === "mon" && <>
          <label>Vùng<input value={nd.vung} placeholder="Hà Nội, Nam Định" onChange={(e) => setNd({ ...nd, vung: e.target.value })} /></label>
          <label>Nên ăn<input value={nd.nen_an} placeholder="Sáng sớm, 6–9 giờ" onChange={(e) => setNd({ ...nd, nen_an: e.target.value })} /></label>
          <label>Thành phần chính<input value={nd.thanh_phan} onChange={(e) => setNd({ ...nd, thanh_phan: e.target.value })} /></label>
          <label>Cách gọi<input value={nd.cach_goi} placeholder="Tái, chín, nạm…" onChange={(e) => setNd({ ...nd, cach_goi: e.target.value })} /></label></>}
      </div>
        {nd.loai !== "bia" && <label>Bài giới thiệu<textarea rows={5} value={nd.noi_dung} onChange={(e) => setNd({ ...nd, noi_dung: e.target.value })} /></label>}
        {["mon", "dac_san", "danh_sach"].includes(nd.loai) && <div className="panel">
          <b>Ăn ở đâu / nhà hàng liên quan</b> <span className="muted">({nd.nha_hang_ids.length} đã chọn — chỉ nơi đang hiện mới lên web)</span>
          <div><input placeholder="Tìm nhà hàng…" value={timNh} onChange={(e) => setTimNh(e.target.value)} /></div>
          <div style={{ maxHeight: 180, overflow: "auto" }}>{x.nha_hang.filter((n: any) => nd.nha_hang_ids.includes(n.id) || (timNh && `${n.ten} ${n.tinh_thanh}`.toLowerCase().includes(timNh.toLowerCase()))).slice(0, 40).map((n: any) =>
            <label key={n.id} style={{ display: "flex", flexDirection: "row", justifyContent: "flex-start", gap: 6, alignItems: "center" }}><input type="checkbox" checked={nd.nha_hang_ids.includes(n.id)}
              onChange={(e) => setNd({ ...nd, nha_hang_ids: e.target.checked ? [...nd.nha_hang_ids, n.id] : nd.nha_hang_ids.filter((i: number) => i !== n.id) })} />
              {n.ten} <span className="muted">· {n.tinh_thanh}{n.mo_dat ? " · đặt được qua Vietourist" : ""}</span></label>)}</div></div>}
        <label style={{ display: "flex", flexDirection: "row", justifyContent: "flex-start", gap: 6, alignItems: "center" }}><input type="checkbox" checked={!!nd.hien} onChange={(e) => setNd({ ...nd, hien: e.target.checked })} />Hiện trên web VTD</label>
        <button className="act teal" disabled={busy} onClick={async () => { const r = await goi(nd.id ? `/nha-hang/noi-dung/${nd.id}` : "/nha-hang/noi-dung", nd); if (r) setNd({ ...nd, id: r.id }); }}>Lưu</button>
        <button className="act grey" onClick={() => setNd(null)}>Đóng</button>
        {nd.id ? oAnh("noi_dung", nd.id, !!x.noi_dung.find((c: any) => c.id === nd.id)?.co_anh, x.noi_dung.find((c: any) => c.id === nd.id)?.anh_nguon || "", undefined)
          : <div className="muted">Lưu trước rồi tải ảnh.</div>}
      </div>}
    </section>}

    {tab === "nh" && <>
    {nhap && <section className="panel">
      <h2>A. Nhập danh sách nhà hàng từ tệp</h2>
      <p className="muted">CSV / Excel / JSON có cột tên (source_name / Tên) và địa danh (source_city / Địa danh); món nổi bật, thứ tự, đường dẫn nếu có. Đọc thử không ghi gì.
        Trùng đúng tên + địa danh thì bỏ qua, không tự gộp. Hồ sơ mới: chưa hiện, chưa ghi nhận hợp đồng.</p>
      <div className="grid">
        <label>Tệp<input type="file" accept=".csv,.xlsx,.xls,.json" onChange={(e) => { setTep(e.target.files?.[0] || null); setThu(null); }} /></label>
        <label>Nguồn danh sách<input value={nguon} placeholder="Danh mục TasteAtlas 28/10/2026" onChange={(e) => setNguon(e.target.value)} /></label></div>
      <button className="act grey" disabled={busy} onClick={() => docTep(false)}>Đọc thử</button>
      {thu && <div className="panel" style={{ marginTop: 8 }}>
        <p>Hồ sơ mới <b>{thu.moi}</b> · trùng tên + địa danh đã có <b>{thu.trung}</b> (không tự gộp) · thiếu tên / địa danh <b>{thu.loi.length}</b></p>
        <div className="muted">Cột đọc được: {Object.entries(thu.cot).map(([a, b]: any) => `${a} ← ${b}`).join(" · ")}</div>
        {thu.mau.length > 0 && <div className="wrap"><table><thead><tr><th>Tên</th><th>Địa danh (nguồn)</th><th>Tỉnh / thành</th><th>Món nổi bật</th></tr></thead>
          <tbody>{thu.mau.map((m: any, i: number) => <tr key={i}><td>{m.ten}</td><td>{m.dia_danh}</td><td>{m.tinh}</td><td className="muted">{m.mon}</td></tr>)}</tbody></table></div>}
        {thu.chua_khop_tp?.length > 0 && <div className="muted">Chưa khớp thành phố ({thu.chua_khop_tp.length}) — nhập xong chọn tay ở cột Thành phố: {thu.chua_khop_tp.map((x: any) => `${x.ten} (${x.dia_danh})`).join("; ")}</div>}
        {thu.loi.length > 0 && <div className="muted">Dòng lỗi: {thu.loi.map((l: any) => `${l.dong} (${l.loi})`).join(", ")}</div>}
        {thu.moi > 0 && <button className="act teal" disabled={busy} onClick={() => docTep(true)}>Nhập {thu.moi} hồ sơ</button>}
      </div>}
    </section>}

    {nhap && <button className="act teal" onClick={() => { setSua("moi"); setF(NH_TRONG); setTd(null); }}>+ Thêm nhà hàng</button>}
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "8px 0" }}>
      <input placeholder="Tìm tên, món, địa danh…" value={tim} onChange={(e) => setTim(e.target.value)} />
      <select value={locTinh} onChange={(e) => setLocTinh(e.target.value)}><option value="">Mọi tỉnh ({x.nha_hang.length})</option>
        {cacTinh.map((t) => <option key={t} value={t}>{t} ({x.nha_hang.filter((n: any) => n.tinh_thanh === t).length})</option>)}</select>
      {bat && chon.length > 0 && <>
        <button className="act teal" disabled={busy} onClick={async () => { const r = await goi("/nha-hang/hien-hang-loat", { ids: chon, bat: true }); if (r) setChon([]); }}>Bật hiện {chon.length} nơi</button>
        <button className="act grey" disabled={busy} onClick={async () => { const r = await goi("/nha-hang/hien-hang-loat", { ids: chon, bat: false }); if (r) setChon([]); }}>Tắt {chon.length} nơi</button></>}
    </div>

    <div className="panel wrap"><table><thead><tr>{bat && <th><input type="checkbox" aria-label="Chọn tất cả" checked={loc.length > 0 && chon.length === loc.length} onChange={(e) => setChon(e.target.checked ? loc.map((n: any) => n.id) : [])} /></th>}
        <th>Nhà hàng</th><th>Địa điểm</th><th>Ẩm thực</th><th>Thực đơn đang bán</th><th>Trên web VTD</th><th>Đặt bàn qua VTD</th><th></th></tr></thead>
      <tbody>{loc.map((n: any) => <tr key={n.id}>
        {bat && <td><input type="checkbox" aria-label={`Chọn ${n.ten}`} checked={chon.includes(n.id)} onChange={(e) => setChon(e.target.checked ? [...chon, n.id] : chon.filter((i) => i !== n.id))} /></td>}
        <td><b>{n.ten}</b><div className="muted">{n.ma} · nhập bởi {n.tao_boi}{n.nguon ? ` · ${n.nguon}` : ""}</div></td>
        <td>{[n.tinh_thanh, n.khu_vuc].filter(Boolean).join(" · ")}{n.dia_danh_nguon && n.dia_danh_nguon !== n.tinh_thanh && <div className="muted">nguồn: {n.dia_danh_nguon}</div>}</td><td>{n.am_thuc}</td>
        <td>{n.so_dang_ban}{n.so_dang_ban ? ` (từ ${d(Math.min(...n.thuc_don.filter((t: any) => t.dang_ban).map((t: any) => t.gia_nguoi_lon)))})` : ""}</td>
        <td>{n.ngung ? <Tag cls="red">Ngừng hợp tác</Tag> : n.hien_cong ? <><Tag cls="ok">Đang hiện</Tag><div className="muted">{n.hien_boi}</div></>
          : <><Tag cls="warn">Chưa hiện</Tag>{n.tat_ly_do && <div className="muted">{n.tat_ly_do}</div>}</>}</td>
        <td>{n.mo_dat ? <Tag cls="ok">Đang mở</Tag> : <><Tag>Chưa mở</Tag><div className="muted">{n.dieu_kien.filter((c: any) => c.ok).length}/5 điều kiện</div></>}</td>
        <td style={{ whiteSpace: "nowrap" }}>
          <button className="act grey" onClick={() => { setSua(n.id); setF({ ...NH_TRONG, ...n }); setTd(null); setHd(HD_TRONG); setTepHd(null); setGt({ mo_ta: n.mo_ta || "", mon_noi_bat: n.mon_noi_bat || "" }); }}>{nhap ? "Sửa" : "Xem"}</button>
          {bat && !n.ngung && <button className="act teal" disabled={busy} onClick={() => goi(`/nha-hang/${n.id}/hien-cong`, { bat: !n.hien_cong })}>{n.hien_cong ? "Tắt khỏi cổng" : "Bật hiện cổng"}</button>}
        </td></tr>)}
        {!loc.length && <tr><td colSpan={8} className="muted">{x.nha_hang.length ? "Không có nhà hàng khớp bộ lọc." : "Chưa có nhà hàng nào. Điều hành nhập tệp hoặc bấm «Thêm nhà hàng»."}</td></tr>}</tbody></table></div>

    {sua && <section className="panel" style={{ marginTop: 14 }}>
      <h2>{sua === "moi" ? "Thêm nhà hàng" : `${dang?.ma} · ${dang?.ten}`}</h2>
      <div className="grid">
        {o("ten", "Tên nhà hàng")}<label>Thành phố<select value={f.tinh_thanh} disabled={!nhap} onChange={(e) => setF({ ...f, tinh_thanh: e.target.value })}>
          <option value="">— chọn —</option>{f.tinh_thanh && !x.thanh_pho.some((t: any) => t.ten === f.tinh_thanh) && <option value={f.tinh_thanh}>{f.tinh_thanh} (chưa khớp danh sách)</option>}
          {x.thanh_pho.map((t: any) => <option key={t.ten} value={t.ten}>{t.ten} · {t.mien}</option>)}</select></label>{o("khu_vuc", "Khu vực / địa chỉ hiển thị", "Q1 · ven sông")}
        <label>Ẩm thực<select value={f.am_thuc} disabled={!nhap} onChange={(e) => setF({ ...f, am_thuc: e.target.value })}>{x.am_thuc.map((a: string) => <option key={a}>{a}</option>)}</select></label>
        {o("gio_phuc_vu", "Giờ phục vụ", "10:00–14:00 · 17:00–22:00")}{o("tien_ich", "Tiện ích", "Phòng riêng · Chỗ đỗ xe")}
      </div>
      <label>Giới thiệu cho khách<textarea rows={2} value={f.mo_ta} disabled={!nhap} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
      <label>Ghi chú nội bộ (không lên cổng)<textarea rows={2} value={f.ghi_chu_noi_bo} disabled={!nhap} onChange={(e) => setF({ ...f, ghi_chu_noi_bo: e.target.value })} /></label>
      {nhap && <button className="act teal" disabled={busy} onClick={async () => { const r = await goi(sua === "moi" ? "/nha-hang" : `/nha-hang/${sua}`, f); if (r && sua === "moi") setSua(r.id); }}>Lưu nhà hàng</button>}
      <button className="act grey" onClick={() => setSua(null)}>Đóng</button>

      {dang && <>
        <h3 style={{ marginTop: 14 }}>Thực đơn / gói</h3>
        <div className="panel wrap"><table><thead><tr><th>Gói</th><th>Loại</th><th>Giá người lớn</th><th>Giá trẻ em</th><th>Áp dụng</th><th>Điều kiện / hủy</th><th>Đang bán</th><th></th></tr></thead>
          <tbody>{dang.thuc_don.map((g: any) => <tr key={g.id}><td><b>{g.ten}</b>{g.so_khach_toi_thieu > 1 && <div className="muted">tối thiểu {g.so_khach_toi_thieu} khách</div>}</td>
            <td>{g.loai_ten}</td><td>{d(g.gia_nguoi_lon)}</td><td>{d(g.gia_tre_em)}</td>
            <td>{g.tu_ngay || g.den_ngay ? `${g.tu_ngay || "…"} → ${g.den_ngay || "…"}` : "Quanh năm"}</td>
            <td className="muted">{[g.dieu_kien, g.dieu_kien_huy].filter(Boolean).join(" · ")}</td>
            <td>{g.dang_ban ? <Tag cls="ok">Có</Tag> : <Tag>Không</Tag>}</td>
            <td>{nhap && <button className="act grey" onClick={() => setTd({ ...TD_TRONG, ...g, gia_tre_em: g.gia_tre_em ?? "", tu_ngay: g.tu_ngay || "", den_ngay: g.den_ngay || "" })}>Sửa</button>}</td></tr>)}
            {!dang.thuc_don.length && <tr><td colSpan={8} className="muted">Chưa có gói. Cần ít nhất một gói đang bán thì mới mở đặt bàn được.</td></tr>}</tbody></table></div>
        {nhap && !td && <button className="act teal" onClick={() => setTd({ ...TD_TRONG })}>+ Thêm gói</button>}
        {td && <div className="panel" style={{ marginTop: 10 }}>
          <div className="grid">
            {t("ten", "Tên gói")}
            <label>Loại<select value={td.loai} onChange={(e) => setTd({ ...td, loai: e.target.value })}>{Object.entries(x.loai_goi).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            {t("so_khach_toi_thieu", "Khách tối thiểu", "number")}
            {t("gia_nguoi_lon", "Giá bán người lớn (đ)", "number")}{t("gia_tre_em", "Giá bán trẻ em (đ, để trống nếu không bán)", "number")}
            {t("tu_ngay", "Áp dụng từ", "date")}{t("den_ngay", "Áp dụng đến", "date")}
            {t("dieu_kien", "Điều kiện (đồ uống, phụ thu…)")}{t("dieu_kien_huy", "Điều kiện hủy")}
          </div>
          <label>Món trong gói<textarea rows={2} value={td.mo_ta} onChange={(e) => setTd({ ...td, mo_ta: e.target.value })} /></label>
          <label style={{ display: "flex", flexDirection: "row", justifyContent: "flex-start", gap: 6, alignItems: "center" }}><input type="checkbox" checked={!!td.dang_ban} onChange={(e) => setTd({ ...td, dang_ban: e.target.checked })} />Đang bán</label>
          <button className="act teal" disabled={busy} onClick={luuTd}>Lưu gói</button><button className="act grey" onClick={() => setTd(null)}>Bỏ</button>
        </div>}

        {(nhap || mkt) && oAnh("nha_hang", dang.id, !!dang.anh_id, dang.anh_nguon, dang.anh_id)}
        {mkt && gt && <div className="panel" style={{ marginTop: 14 }}>
          <h3>Giới thiệu trên web VTD (Marketing)</h3>
          <label>Món nổi bật<input value={gt.mon_noi_bat} onChange={(e) => setGt({ ...gt, mon_noi_bat: e.target.value })} /></label>
          <label>Giới thiệu do VTD viết<textarea rows={3} value={gt.mo_ta} onChange={(e) => setGt({ ...gt, mo_ta: e.target.value })} /></label>
          <button className="act teal" disabled={busy} onClick={() => goi(`/nha-hang/${dang.id}/gioi-thieu`, gt)}>Lưu giới thiệu</button></div>}

        <h3 style={{ marginTop: 14 }}>B. Điều kiện mở đặt bàn qua VTD</h3>
        <ul>{dang.dieu_kien.map((c: any) => <li key={c.ma}>{c.ok ? "✅" : "⬜"} {c.ten}</li>)}</ul>
        <p className="muted">Đủ 5 điều kiện và đang hiện trên web thì máy tự mở «Đặt bàn qua VTD»; hết hạn hợp đồng thì tự đóng nhận đặt mới, đơn cũ giữ nguyên.
          {!dang.supplier_id && " Gắn nhà cung cấp ở màn «Cổng nhà cung cấp»."}</p>
        <p>Liên hệ (địa chỉ, giờ mở cửa, điện thoại): {dang.lien_he_xac_minh ? <Tag cls="ok">Đã xác minh · {dang.xac_minh_boi}</Tag> : <Tag cls="warn">Chưa xác minh</Tag>}
          {nhap && <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/${dang.id}/xac-minh`, { ok: !dang.lien_he_xac_minh })}>{dang.lien_he_xac_minh ? "Bỏ xác minh" : "Đánh dấu đã xác minh"}</button>}</p>

        {xemHd && <>
          <h3 style={{ marginTop: 14 }}>C. Hợp đồng nhà hàng</h3>
          <div className="wrap"><table><thead><tr><th>Bản</th><th>Số HĐ</th><th>Ngày ký</th><th>Hiệu lực</th><th>Hoa hồng</th><th>Ghi bởi</th><th></th></tr></thead>
            <tbody>{dang.hop_dong.map((h: any) => <tr key={h.id}><td>{h.phien_ban}{h.con_dung ? <Tag cls="ok">Đang dùng</Tag> : <Tag>Đã thay</Tag>}</td><td>{h.so_hd}{h.ly_do && <div className="muted">{h.ly_do}</div>}</td>
              <td>{h.ngay_ky}</td><td>{h.tu_ngay} → {h.den_ngay || "không thời hạn"}</td><td>{h.hoa_hong || "Chưa khai"}{h.co_so && <div className="muted">{h.co_so}</div>}</td>
              <td className="muted">{h.ghi_boi} · {h.ghi_luc}</td>
              <td><button className="act grey" onClick={() => taiTep(`/nha-hang/hop-dong/${h.id}/tep`, `hop_dong_${h.so_hd}.pdf`).catch((e) => toast(errMsg(e), true))}>Mở tệp</button></td></tr>)}
              {!dang.hop_dong.length && <tr><td colSpan={7} className="muted">Chưa ghi nhận hợp đồng.</td></tr>}</tbody></table></div>
          {nhap && <div className="panel" style={{ marginTop: 10 }}>
            <label style={{ display: "flex", flexDirection: "row", justifyContent: "flex-start", gap: 6, alignItems: "center" }}><input type="checkbox" checked={hd.da_ky} onChange={(e) => setHd({ ...hd, da_ky: e.target.checked })} />Đã ký hợp đồng</label>
            <div className="grid">
              <label>Tệp hợp đồng đã ký (PDF / ảnh)<input type="file" accept=".pdf,image/*" onChange={(e) => setTepHd(e.target.files?.[0] || null)} /></label>
              <label>Số hợp đồng<input value={hd.so_hd} onChange={(e) => setHd({ ...hd, so_hd: e.target.value })} /></label>
              <label>Ngày ký<input type="date" value={hd.ngay_ky} onChange={(e) => setHd({ ...hd, ngay_ky: e.target.value })} /></label>
              <label>Hiệu lực từ<input type="date" value={hd.tu_ngay} onChange={(e) => setHd({ ...hd, tu_ngay: e.target.value })} /></label>
              <label>Hiệu lực đến (trống = không thời hạn)<input type="date" value={hd.den_ngay} onChange={(e) => setHd({ ...hd, den_ngay: e.target.value })} /></label>
              <label>Hoa hồng nhà hàng trả VTD (%)<input inputMode="decimal" value={hd.hoa_hong_pct} placeholder="10" onChange={(e) => setHd({ ...hd, hoa_hong_pct: e.target.value })} /></label>
              <label>hoặc cố định (đ / đơn)<input type="number" value={hd.hoa_hong_co_dinh} onChange={(e) => setHd({ ...hd, hoa_hong_co_dinh: e.target.value })} /></label>
              <label>Cơ sở tính hoa hồng<input value={hd.co_so} placeholder="tiền món, chưa VAT" onChange={(e) => setHd({ ...hd, co_so: e.target.value })} /></label>
              {dang.hop_dong.length > 0 && <label>Lý do thay bản cũ<input value={hd.ly_do} placeholder="Gia hạn / phụ lục / sửa sai" onChange={(e) => setHd({ ...hd, ly_do: e.target.value })} /></label>}
            </div>
            <button className="act teal" disabled={busy} onClick={() => luuHd(dang.id)}>Lưu ghi nhận hợp đồng</button>
            <div className="muted">Tệp lưu vào hồ sơ nhà cung cấp, chỉ Điều hành / Kế toán / BKS / lãnh đạo mở. Sửa hợp đồng = thêm bản mới kèm lý do, không xóa bản cũ.</div>
          </div>}
        </>}
      </>}
    </section>}
    </>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
