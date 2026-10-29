"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, getToken, taiTep } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** AT-2a · ALBUM ẢNH NHÀ HÀNG (Chủ tịch + Điều hành chốt 29/10/2026).
 *  Chỉ ảnh của chính nhà hàng · 10 MB/ảnh · 60 ảnh/nhà hàng · máy tạo ảnh nhẹ, giữ bản gốc · 5 nhóm ảnh.
 *  Nguồn / căn cứ quyền dùng chỉ là ghi chú NỘI BỘ (Chủ tịch bỏ chặn 29/10/2026): không chặn duyệt, không ra cổng khách.
 *  Ảnh mới «Nháp» → «Gửi duyệt» → TP Điều hành duyệt (người tải / sửa không tự duyệt). */

const MB = 1024 * 1024;
const DUOI = ["jpg", "jpeg", "png", "webp"];
const kb = (n: number) => (n >= MB ? `${(n / MB).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);
const MAU_TT: Record<string, string> = { nhap: "", cho_duyet: "warn", da_duyet: "ok", an: "red" };

/** Ảnh nội bộ cần mã đăng nhập → tải blob rồi hiện. */
export function AnhNoiBo({ src, alt, style }: { src: string; alt: string; style?: React.CSSProperties }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let u = "", huy = false;
    fetch(`/api/v1${src.replace(/^\/api\/v1/, "")}`, { headers: { Authorization: `Bearer ${getToken() || ""}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((b) => { if (!huy) { u = URL.createObjectURL(b); setUrl(u); } })
      .catch(() => {});
    return () => { huy = true; if (u) URL.revokeObjectURL(u); };
  }, [src]);
  return url ? <img src={url} alt={alt} style={{ objectFit: "cover", display: "block", ...style }} />
    : <div style={{ background: "var(--line, #2a3b4d)", ...style }} aria-label={alt} />;
}

type Dong = { k: string; file: File; tt: "cho" | "tai" | "xong" | "loi" | "bo"; pt: number; loi: string };

function guiMot(path: string, fd: FormData, tienDo: (p: number) => void): Promise<any> {
  return new Promise((ok, hong) => {
    const x = new XMLHttpRequest();
    x.open("POST", `/api/v1${path}`);
    const t = getToken(); if (t) x.setRequestHeader("Authorization", `Bearer ${t}`);
    x.upload.onprogress = (e) => { if (e.lengthComputable) tienDo(Math.round((e.loaded / e.total) * 100)); };
    x.onload = () => { let d: any = null; try { d = JSON.parse(x.responseText); } catch { /* */ }
      if (x.status >= 200 && x.status < 300) ok(d); else hong(new Error(typeof d?.detail === "string" ? d.detail : `Lỗi ${x.status}`)); };
    x.onerror = () => hong(new Error("Mất mạng"));
    x.send(fd);
  });
}

export default function AlbumNhaHang({ nid, toast, onDoi }: { nid: number; toast: (m: string, loi?: boolean) => void; onDoi?: () => void }) {
  const [a, setA] = useState<any>(null);
  const [loNhom, setLoNhom] = useState("khong_gian");
  const [lo, setLo] = useState({ can_cu: "nha_hang", can_cu_ghi_chu: "", credit: "" });
  const [hang, setHang] = useState<Dong[]>([]);
  const [loc, setLoc] = useState("");
  const [chon, setChon] = useState<any>(null);
  const [thuTu, setThuTu] = useState<number[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [moTai, setMoTai] = useState(false);
  const keo = useRef<number | null>(null);
  const tepThay = useRef<HTMLInputElement>(null);
  const tepMoi = useRef<HTMLInputElement>(null);
  const load = useCallback(() => api(`/nha-hang/${nid}/album`).then((r: any) => { setA(r); setThuTu(null);
    setChon((c: any) => (c ? r.anh.find((x: any) => x.id === c.id) || null : null)); }).catch((e) => toast(errMsg(e), true)), [nid, toast]);
  useEffect(() => { load(); setHang([]); }, [load]);

  if (!a) return <p className="muted">Đang tải album…</p>;
  const ds: any[] = thuTu ? thuTu.map((i) => a.anh.find((x: any) => x.id === i)).filter(Boolean) : a.anh;
  const conLai = a.toi_da - a.tong;

  const them = (files: FileList | File[]) => {
    const moi: Dong[] = Array.from(files).map((f, i) => {
      const duoi = (f.name.split(".").pop() || "").toLowerCase();
      const loi = !DUOI.includes(duoi) ? "Chỉ JPG / PNG / WEBP" : f.size > a.toi_da_mb * MB ? `Quá ${a.toi_da_mb} MB` : "";
      return { k: `${Date.now()}-${i}-${f.name}`, file: f, tt: loi ? "loi" : "cho", pt: 0, loi };
    });
    setHang((h) => [...h, ...moi]);
  };
  const capNhat = (k: string, p: Partial<Dong>) => setHang((h) => h.map((d) => (d.k === k ? { ...d, ...p } : d)));
  const taiHet = async (chiK?: string) => {
    setBusy(true);
    let so = 0;
    for (const d of hang) {
      if (chiK ? d.k !== chiK : d.tt !== "cho") continue;
      capNhat(d.k, { tt: "tai", pt: 0, loi: "" });
      const fd = new FormData();
      fd.append("tep", d.file); fd.append("nhom", loNhom);
      Object.entries(lo).forEach(([k, v]) => fd.append(k, v));
      try { const r = await guiMot(`/nha-hang/${nid}/album`, fd, (pt) => capNhat(d.k, { pt }));
        capNhat(d.k, { tt: "xong", pt: 100, loi: r?.moi === false ? "Đã có trong album — không tạo bản trùng" : "" }); so++; }
      catch (e: any) { capNhat(d.k, { tt: "loi", loi: e.message || "Lỗi" }); }
    }
    setBusy(false);
    if (so) { toast(`Đã tải ${so} ảnh (Nháp) — bấm «Gửi duyệt» khi xong lô`); load(); onDoi?.(); }
  };
  const goi = async (path: string, json: any, sau?: () => void) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); sau?.(); await load(); onDoi?.(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  const thay = async (f: File) => {
    if (f.size > a.toi_da_mb * MB) { toast(`Ảnh ${kb(f.size)}, quá ${a.toi_da_mb} MB`, true); return; }
    setBusy(true);
    try { const fd = new FormData(); fd.append("tep", f);
      const r = await guiMot(`/nha-hang/album/${chon.id}/thay`, fd, () => {}); toast(r.message); await load(); onDoi?.(); }
    catch (e: any) { toast(e.message, true); } finally { setBusy(false); }
  };
  const nhap = a.anh.filter((x: any) => x.trang_thai === "nhap");
  const dem = (k: string) => a.anh.filter((x: any) => x.nhom === k).length;
  const hien = ds.filter((x: any) => !loc || (loc === "_" ? !x.nhom : x.nhom === loc));
  // Mũi tên ←/→ trên thẻ: đổi chỗ với ảnh liền trước / sau (trong cả album) và lưu ngay.
  const dichChuyen = (id: number, b: number) => {
    const ids = ds.map((y: any) => y.id); const i = ids.indexOf(id); const j = i + b;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    goi(`/nha-hang/${nid}/album/thu-tu`, { ids });
  };

  return (<div className="panel" style={{ marginTop: 14 }}>
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-start", justifyContent: "space-between" }}>
      <div><h3 style={{ margin: 0 }}>Không gian &amp; hương vị</h3>
        <div className="muted">Chọn ảnh bìa, sắp xếp và hoàn thiện từng ảnh. <b>{a.tong}</b> ảnh / {a.toi_da}</div></div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {a.duoc_tai && <button className="act grey" onClick={() => setMoTai(!moTai)}>{moTai ? "Đóng khung tải" : "⤒ Thêm ảnh"}</button>}
        {a.duoc_tai && <button className="act teal" disabled={busy || !nhap.length} onClick={() => goi(`/nha-hang/${nid}/album/gui-duyet`, { ids: [] })}>Gửi duyệt{nhap.length ? ` ${nhap.length} ảnh nháp` : ""}</button>}
      </div></div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "6px 0" }}>
      <Tag cls="ok">Đã duyệt {a.dem.da_duyet}</Tag><Tag cls="warn">Chờ duyệt {a.dem.cho_duyet}</Tag><Tag>Nháp {a.dem.nhap}</Tag><Tag cls="red">Ẩn {a.dem.an}</Tag></div>

    {a.duoc_tai && (moTai || hang.length > 0) && <div className="panel" onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files?.length) them(e.dataTransfer.files); }}
      style={{ borderStyle: "dashed" }}>
      <b>Kéo thả nhiều ảnh vào đây</b> hoặc <label style={{ display: "inline" }}><span className="act grey" style={{ cursor: "pointer" }}>Chọn ảnh</span>
        <input type="file" multiple accept=".jpg,.jpeg,.png,.webp" style={{ display: "none" }} onChange={(e) => { if (e.target.files) them(e.target.files); e.target.value = ""; }} /></label>
      <div className="muted">JPG · PNG · WEBP · tối đa {a.toi_da_mb} MB/ảnh · {a.toi_da} ảnh/nhà hàng (đang có {a.tong}, còn {conLai}). Máy tạo ảnh nhẹ để hiển thị, giữ bản gốc.
        Chỉ ảnh của chính nhà hàng.</div>
      <div className="grid" style={{ marginTop: 6 }}>
        <label>Nhóm ảnh cho lô này<select value={loNhom} onChange={(e) => setLoNhom(e.target.value)}>
          {Object.entries(a.nhom_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Nguồn / căn cứ (không bắt buộc · chỉ lưu nội bộ)<select value={lo.can_cu} onChange={(e) => setLo({ ...lo, can_cu: e.target.value })}>
          {Object.entries(a.can_cu_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Ghi chú căn cứ<input value={lo.can_cu_ghi_chu} placeholder="Email chị Lan, quản lý, 28/10/2026" onChange={(e) => setLo({ ...lo, can_cu_ghi_chu: e.target.value })} /></label>
        <label>Tác giả / credit (nếu nhà hàng yêu cầu)<input value={lo.credit} onChange={(e) => setLo({ ...lo, credit: e.target.value })} /></label></div>
      {hang.length > 0 && <div style={{ marginTop: 6 }}>{hang.filter((d) => d.tt !== "bo").map((d) => <div key={d.k} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", padding: "3px 0" }}>
        <span>{d.file.name} · {kb(d.file.size)}</span>
        {d.tt === "cho" && <Tag>Chờ tải</Tag>}
        {d.tt === "tai" && <Tag cls="warn">Đang tải {d.pt}%</Tag>}
        {d.tt === "xong" && <><Tag cls="ok">Xong</Tag>{d.loi && <span className="muted">{d.loi}</span>}</>}
        {d.tt === "loi" && <><Tag cls="red">{d.loi}</Tag>
          {!/^Quá|^Chỉ/.test(d.loi) && <button className="act grey" disabled={busy} onClick={() => taiHet(d.k)}>Thử lại</button>}
          <button className="act grey" onClick={() => capNhat(d.k, { tt: "bo" })}>Bỏ</button></>}
      </div>)}
        <button className="act teal" disabled={busy || !hang.some((d) => d.tt === "cho")} onClick={() => taiHet()}>Tải {hang.filter((d) => d.tt === "cho").length} ảnh lên</button>
        <button className="act grey" disabled={busy} onClick={() => setHang([])}>Xóa danh sách</button>
        <div className="muted">Tải lại đúng tệp đã có (cùng nội dung) không tạo bản trùng. Ảnh mới vào «Nháp»; bấm «Gửi duyệt» khi xong lô.</div></div>}
    </div>}

    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0", alignItems: "center" }}>
      <button className={`act ${!loc ? "teal" : "grey"}`} onClick={() => setLoc("")}>Tất cả {a.tong}</button>
      {Object.entries(a.nhom_anh).map(([k, v]: any) => <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{v} {dem(k)}</button>)}
      {a.anh.some((x: any) => !x.nhom) && <button className={`act ${loc === "_" ? "teal" : "grey"}`} onClick={() => setLoc("_")}>Chưa phân nhóm {dem("")}</button>}
      <span style={{ flex: 1 }} />
      {thuTu && <button className="act teal" disabled={busy} onClick={() => goi(`/nha-hang/${nid}/album/thu-tu`, { ids: thuTu })}>Lưu thứ tự</button>}
    </div>
    {a.duoc_tai && a.anh.length > 1 && <div className="muted">Đổi thứ tự: bấm ←/→ trên thẻ (lưu ngay), hoặc kéo thả rồi bấm «Lưu thứ tự». Bấm ảnh để sửa chi tiết.</div>}

    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 300px), 1fr))", gap: 14, marginTop: 8 }}>
      {hien.map((x: any) => <div key={x.id} draggable={a.duoc_tai} onDragStart={() => { keo.current = x.id; }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const tu = keo.current; keo.current = null; if (!tu || tu === x.id) return;
          const ids = ds.map((y: any) => y.id).filter((i: number) => i !== tu); ids.splice(ids.indexOf(x.id), 0, tu); setThuTu(ids); }}
        onClick={() => setChon(x)}
        style={{ cursor: "pointer", border: chon?.id === x.id ? "2px solid var(--teal, #2bb5a0)" : "1px solid var(--line, #2a3b4d)", borderRadius: 14, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ position: "relative" }}>
          <AnhNoiBo src={x.hien} alt={x.mo_ta_thay_the || x.chu_thich || x.nhom_ten} style={{ width: "100%", aspectRatio: "16 / 9" }} />
          {x.la_bia && <span style={{ position: "absolute", left: 12, top: 12, background: "rgba(0,0,0,.6)", color: "#fff", borderRadius: 6, padding: "3px 10px", fontSize: 13 }}>Ảnh bìa</span>}
        </div>
        <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
          <b style={{ fontSize: 16 }}>{x.chu_thich || <span className="muted">(chưa có chú thích)</span>}</b>
          <div className="muted">{x.nhom_ten}</div>
          <div><Tag cls={MAU_TT[x.trang_thai]}>{x.trang_thai_ten}</Tag></div>
          {x.ly_do_tra_lai && <div style={{ color: "var(--red, #e5484d)", fontSize: 13 }}>Trả lại: {x.ly_do_tra_lai}</div>}
          <div style={{ flex: 1 }} />
          {a.duoc_tai && <div style={{ borderTop: "1px solid var(--line, #2a3b4d)", paddingTop: 10, display: "flex", alignItems: "center", gap: 6 }} onClick={(e) => e.stopPropagation()}>
            {x.la_bia ? <span className="muted">Đang làm bìa</span>
              : x.trang_thai === "an" ? <span className="muted">Đang ẩn</span>
              : <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/album/${x.id}/bia`, {})}>Chọn làm bìa</button>}
            <span style={{ flex: 1 }} />
            <button className="act grey" aria-label={`Đưa ảnh ${x.id} lên trước`} disabled={busy || ds[0]?.id === x.id} onClick={() => dichChuyen(x.id, -1)}>←</button>
            <button className="act grey" aria-label={`Đưa ảnh ${x.id} ra sau`} disabled={busy || ds[ds.length - 1]?.id === x.id} onClick={() => dichChuyen(x.id, 1)}>→</button>
          </div>}
        </div></div>)}
      {!hien.length && !a.duoc_tai && <p className="muted">Chưa có ảnh{loc ? " trong nhóm này" : ""}.</p>}
      {a.duoc_tai && conLai > 0 && <button type="button" onClick={() => tepMoi.current?.click()}
        onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); if (e.dataTransfer.files?.length) { them(e.dataTransfer.files); setMoTai(true); } }}
        style={{ all: "unset", cursor: "pointer", minHeight: 220, border: "1px dashed var(--line, #2a3b4d)", borderRadius: 14, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 6, textAlign: "center", padding: 16 }}>
        <b style={{ fontSize: 16, color: "var(--teal, #2bb5a0)" }}>Thêm khoảnh khắc</b>
        <span className="muted">JPG, PNG, WebP · tối đa {a.toi_da_mb} MB/ảnh · còn {conLai} chỗ</span></button>}
      <input ref={tepMoi} type="file" multiple accept=".jpg,.jpeg,.png,.webp" style={{ display: "none" }}
        onChange={(e) => { if (e.target.files?.length) { them(e.target.files); setMoTai(true); } e.target.value = ""; }} />
    </div>
    <p className="muted" style={{ marginTop: 8 }}>Ảnh cũ giữ vị trí bìa; quyền dùng và phê duyệt kiểm tra riêng. Chỉ ảnh «Đã duyệt» ra cổng khách. Tải hoặc duyệt ảnh không mở đặt bàn.</p>

    {chon && <div className="panel" style={{ marginTop: 10 }}>
      <b>Ảnh #{chon.id} · chi tiết</b> <span className="muted">{chon.ten_tep} · gốc {kb(chon.kich_thuoc)}{chon.rong ? ` · ${chon.rong}×${chon.cao}` : ""} · tải bởi {chon.tai_boi}{chon.duyet_boi ? ` · duyệt bởi ${chon.duyet_boi}` : ""}</span>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 6 }}>
        <AnhNoiBo src={chon.hien} alt={chon.mo_ta_thay_the || chon.chu_thich} style={{ width: 320, maxWidth: "100%", aspectRatio: "4 / 3", borderRadius: 8 }} />
        <div style={{ flex: 1, minWidth: 240 }}>
          <div className="grid">
            <label>Chú thích (hiện cho khách)<input value={chon.chu_thich} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, chu_thich: e.target.value })} /></label>
            <label>Mô tả thay thế (cho người dùng đọc màn hình)<input value={chon.mo_ta_thay_the} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, mo_ta_thay_the: e.target.value })} /></label>
            <label>Nhóm<select value={chon.nhom} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, nhom: e.target.value })}>
              {!chon.nhom && <option value="">— chọn —</option>}
              {Object.entries(a.nhom_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Nguồn / căn cứ (nội bộ)<select value={chon.can_cu} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, can_cu: e.target.value })}>
              {Object.entries(a.can_cu_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Ghi chú căn cứ<input value={chon.can_cu_ghi_chu} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, can_cu_ghi_chu: e.target.value })} /></label>
            <label>Tác giả / credit<input value={chon.credit} disabled={!a.duoc_tai} onChange={(e) => setChon({ ...chon, credit: e.target.value })} /></label></div>
          {a.duoc_tai && <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button className="act teal" disabled={busy} onClick={() => goi(`/nha-hang/album/${chon.id}`, { nhom: chon.nhom, chu_thich: chon.chu_thich, mo_ta_thay_the: chon.mo_ta_thay_the, can_cu: chon.can_cu, can_cu_ghi_chu: chon.can_cu_ghi_chu, credit: chon.credit })}>Lưu</button>
            {!chon.la_bia && chon.trang_thai !== "an" && <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/album/${chon.id}/bia`, {})}>Đặt làm ảnh bìa</button>}
            <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/album/${chon.id}/an`, { an: chon.trang_thai !== "an" })}>{chon.trang_thai === "an" ? "Bỏ ẩn" : "Ẩn ảnh"}</button>
            <button className="act grey" disabled={busy} onClick={() => tepThay.current?.click()}>Thay ảnh</button>
            <input ref={tepThay} type="file" accept=".jpg,.jpeg,.png,.webp" style={{ display: "none" }} onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) thay(f); }} />
            <button className="act grey" onClick={() => taiTep(chon.goc.replace(/^\/api\/v1/, ""), chon.ten_tep || `anh_${chon.id}.jpg`).catch((e) => toast(errMsg(e), true))}>Tải bản gốc</button>
          </div>}
          <div className="muted">Sửa chữ / căn cứ của ảnh đã duyệt → ảnh về «Chờ duyệt», thôi hiện tới khi TP Điều hành duyệt lại. «Thay ảnh» chỉ thay đúng ảnh này; tệp cũ vẫn giữ trong kho.</div>
        </div></div></div>}
  </div>);
}

/** Màn «Ảnh chờ duyệt» — TP Điều hành duyệt / trả lại. */
export function AnhChoDuyet({ toast, onDoi }: { toast: (m: string, loi?: boolean) => void; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [chon, setChon] = useState<number[]>([]);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api("/nha-hang/album/cho-duyet").then((r: any) => { setX(r); setChon([]); }).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const duocChon = x.anh.filter((a: any) => !a.khong_duyet).map((a: any) => a.id);
  const lam = async (duyet: boolean) => {
    if (!duyet && lyDo.trim().length < 3) { toast("Trả lại phải ghi lý do", true); return; }
    setBusy(true);
    try { const r = await api<any>("/nha-hang/album/duyet", { method: "POST", json: { ids: chon, duyet, ly_do: lyDo } });
      toast(r.message + (r.bo_qua?.length ? ` — ${r.bo_qua[0].ly_do}` : "")); setLyDo(""); load(); onDoi?.(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  return (<section className="panel">
    <h2>Ảnh chờ duyệt <Tag cls="warn">{x.anh.length}</Tag></h2>
    {x.duoc_duyet && x.anh.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", margin: "6px 0" }}>
      <label style={{ display: "flex", flexDirection: "row", gap: 6, alignItems: "center" }}><input type="checkbox" aria-label="Chọn tất cả ảnh duyệt được"
        checked={duocChon.length > 0 && chon.length === duocChon.length} onChange={(e) => setChon(e.target.checked ? duocChon : [])} />Chọn tất cả</label>
      <button className="act teal" disabled={busy || !chon.length} onClick={() => lam(true)}>Duyệt {chon.length} ảnh đã chọn</button>
      <input placeholder="Lý do trả lại" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      <button className="act grey" disabled={busy || !chon.length} onClick={() => lam(false)}>Trả lại</button></div>}
    <div className="wrap"><table><thead><tr>{x.duoc_duyet && <th></th>}<th>Ảnh</th><th>Nhà hàng</th><th>Nhóm · chú thích</th><th>Căn cứ quyền dùng</th><th>Người tải</th></tr></thead>
      <tbody>{x.anh.map((a: any) => <tr key={a.id}>
        {x.duoc_duyet && <td><input type="checkbox" aria-label={`Chọn ảnh ${a.id}`} disabled={!!a.khong_duyet} checked={chon.includes(a.id)}
          onChange={(e) => setChon(e.target.checked ? [...chon, a.id] : chon.filter((i) => i !== a.id))} /></td>}
        <td><AnhNoiBo src={a.nho} alt={a.chu_thich || a.nhom_ten} style={{ width: 96, height: 72, borderRadius: 6 }} /></td>
        <td>{a.nha_hang_ten}{a.la_bia && <div><Tag cls="ok">Ảnh bìa</Tag></div>}</td>
        <td>{a.nhom_ten} · {a.chu_thich || <span className="muted">(thiếu chú thích)</span>}</td>
        <td>{a.can_cu_ten}{a.can_cu_ghi_chu && <div className="muted">{a.can_cu_ghi_chu}</div>}
          {a.khong_duyet && <div style={{ color: "var(--red, #e5484d)" }}>{a.khong_duyet}</div>}</td>
        <td className="muted">{a.tai_boi}</td></tr>)}
        {!x.anh.length && <tr><td colSpan={6} className="muted">Không có ảnh chờ duyệt.</td></tr>}</tbody></table></div>
    <p className="muted">Ảnh do chính TP ĐH tải / sửa thì TP ĐH khác hoặc Chủ tịch / TGĐ duyệt. Ảnh thiếu căn cứ quyền dùng không duyệt được. Chỉ ảnh «Đã duyệt» mới ra cổng khách.</p>
  </section>);
}
