"use client";
/* KS-16f · VIDEO KHÁCH SẠN / NHÀ HÀNG phía VTOS (Chủ tịch duyệt bản xem thử 31/10/2026).
   · Mức chuẩn chỉ nhắc: KS tổng quan · phòng · trải nghiệm; NH không gian · món. Tối đa 5 video, ≤100 MB.
   · Tải theo từng phần 8 MB (mạng chập chờn: gửi lại đúng phần lỗi, tối đa 3 lần). Tải xong là hiện.
   · Ảnh đại diện: trình duyệt chụp khung hình giây thứ 2 (đổi được). Thời lượng đọc ngay trên máy người tải.
   · Video / ảnh đại diện xem bằng vé ký ngắn hạn (?t=) — thẻ <video> không gửi được phiên đăng nhập. */
import { useCallback, useEffect, useState } from "react";
import { api, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

type Gan = { id: number; ten: string };
const MB = 1024 * 1024;
const giay = (s: number) => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : "");

function docVideo(f: File): Promise<{ thoi_luong: number; phat_duoc: boolean; anh: Blob | null }> {
  return new Promise((ok) => {
    const url = URL.createObjectURL(f);
    const v = document.createElement("video");
    v.muted = true; v.preload = "metadata"; v.src = url;
    let xong = false;
    const ket = (r: { thoi_luong: number; phat_duoc: boolean; anh: Blob | null }) => { if (!xong) { xong = true; URL.revokeObjectURL(url); ok(r); } };
    v.onerror = () => ket({ thoi_luong: 0, phat_duoc: false, anh: null });
    v.onloadedmetadata = () => { v.currentTime = Math.min(2, (v.duration || 0) / 2); };
    v.onseeked = () => {
      try {
        const c = document.createElement("canvas");
        const r = Math.min(1, 1280 / (v.videoWidth || 1280));
        c.width = Math.round((v.videoWidth || 1280) * r); c.height = Math.round((v.videoHeight || 720) * r);
        c.getContext("2d")?.drawImage(v, 0, 0, c.width, c.height);
        c.toBlob((b) => ket({ thoi_luong: v.duration || 0, phat_duoc: !!v.videoWidth, anh: b }), "image/jpeg", 0.85);
      } catch { ket({ thoi_luong: v.duration || 0, phat_duoc: !!v.videoWidth, anh: null }); }
    };
    setTimeout(() => ket({ thoi_luong: v.duration || 0, phat_duoc: !!v.videoWidth, anh: null }), 15000);
  });
}

async function guiTho(path: string, init: RequestInit) {
  const tok = getToken();
  const r = await fetch(`/api/v1${path}`, { ...init, headers: { ...(init.headers as any), ...(tok ? { Authorization: `Bearer ${tok}` } : {}) } });
  const t = await r.text(); let d: any = null; try { d = t ? JSON.parse(t) : null; } catch { d = t; }
  if (!r.ok) throw { status: r.status, message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}

export default function VideoNoiBo({ goc, oid, toast, loaiPhong = [], mon = [], thucDon = [], onDoi }:
  { goc: "/khach-san-vtd" | "/nha-hang"; oid: number; toast: (m: string, l?: boolean) => void; loaiPhong?: Gan[]; mon?: Gan[]; thucDon?: Gan[]; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [f, setF] = useState<File | null>(null);
  const [doc, setDoc] = useState<{ thoi_luong: number; phat_duoc: boolean; anh: Blob | null } | null>(null);
  const [o, setO] = useState<Record<string, any>>({ loai: "", tieu_de: "", nguon: "", xac_nhan_quyen: false, gan: "" });
  const [tien, setTien] = useState<{ da: number; tong: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [phat, setPhat] = useState<number | null>(null);
  const [lanTep, setLanTep] = useState(0);         // đổi key để làm trống ô chọn tệp sau khi tải xong
  const load = useCallback(() => { api<any>(`${goc}/${oid}/video`).then(setX).catch((e) => toast(errMsg(e), true)); }, [goc, oid, toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const ks = goc === "/khach-san-vtd";
  const ganDs: Gan[] = o.loai === "phong" ? loaiPhong : o.loai === "mon" ? mon : o.loai === "thuc_don" ? thucDon : [];
  const ganKhoa = o.loai === "phong" ? "loai_phong_id" : o.loai === "mon" ? "mon_id" : o.loai === "thuc_don" ? "thuc_don_id" : "";
  const day = x.video.length >= x.toi_da;

  const chon = async (tep: File | null) => {
    setF(tep); setDoc(null);
    if (!tep) return;
    if (tep.size > x.toi_da_mb * MB) { toast(`Video tối đa ${x.toi_da_mb} MB — tệp này ${(tep.size / MB).toFixed(0)} MB`, true); setF(null); return; }
    setDoc(await docVideo(tep));
  };
  const tai = async () => {
    if (!f) return;
    setBusy(true);
    try {
      const v = await api<any>(`${goc}/${oid}/video/bat-dau`, { method: "POST", json: {
        ten_tep: f.name, kich_thuoc: f.size, thoi_luong: doc?.thoi_luong || 0, loai: o.loai, tieu_de: o.tieu_de, nguon: o.nguon,
        xac_nhan_quyen: o.xac_nhan_quyen, ...(ganKhoa && o.gan ? { [ganKhoa]: Number(o.gan) } : {}) } });
      const n = v.so_phan, kc = v.phan_byte;
      for (let i = 0; i < n; i++) {
        const phan = f.slice(i * kc, Math.min(f.size, (i + 1) * kc));
        let lan = 0;
        for (;;) {
          try { await guiTho(`${goc}/video/${v.id}/phan/${i + 1}`, { method: "PUT", body: phan, headers: { "Content-Type": "application/octet-stream" } }); break; }
          catch (e) { if (++lan >= 3) throw e; await new Promise((r) => setTimeout(r, 1500 * lan)); }
        }
        setTien({ da: Math.min(f.size, (i + 1) * kc), tong: f.size });
      }
      await api(`${goc}/video/${v.id}/xong`, { method: "POST" });
      if (doc?.anh) { const fd = new FormData(); fd.append("tep", doc.anh, "anh.jpg"); await guiTho(`${goc}/video/${v.id}/anh-dai-dien`, { method: "POST", body: fd }).catch(() => {}); }
      toast("Đã tải video — đang hiện"); setF(null); setDoc(null); setLanTep((n) => n + 1); setO({ loai: "", tieu_de: "", nguon: o.nguon, xac_nhan_quyen: false, gan: "" });
      load(); onDoi?.();
    } catch (e) { toast(errMsg(e), true); load(); }
    finally { setBusy(false); setTien(null); }
  };
  const viec = async (id: number, v: string) => {
    if (v === "xoa" && !window.confirm("Xóa video này khỏi danh sách?")) return;
    setBusy(true);
    try { const r = await api<any>(`${goc}/video/${id}/${v}`, { method: "POST" }); toast(r.message); load(); onDoi?.(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const doiAnh = async (id: number, tep: File | undefined) => {
    if (!tep) return;
    try { const fd = new FormData(); fd.append("tep", tep); const r = await guiTho(`${goc}/video/${id}/anh-dai-dien`, { method: "POST", body: fd }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); }
  };
  const duoc = (v: any) => x.duoc_quan || (x.duoc_nhap && v.tai_boi === x.toi);

  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    <div className="panel" style={{ margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 13 }}><b>Mức chuẩn:</b> {x.chuan.map((c: any) => <span key={c.loai} style={{ marginRight: 10 }}>{c.co ? "✓" : "○"} {c.ten.split(" (")[0].split(" —")[0]}</span>)}
        {x.du_chuan ? <Tag cls="ok">Đủ chuẩn</Tag> : <span className="muted">— chỉ nhắc, 1 video thực tế là đủ để bắt đầu</span>}</div>
      {x.duoc_nhap && (day ? <p className="muted" style={{ margin: 0 }}>Đã đủ {x.toi_da} video — xóa video cũ trước khi tải thêm.</p> : <>
        <div className="grid">
          <label>Tệp video (MP4 khuyên dùng; MOV / WebM; ≤{x.toi_da_mb} MB)<input key={lanTep} type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm,.m4v" onChange={(e) => chon(e.target.files?.[0] || null)} disabled={busy} /></label>
          <label>Loại nội dung<select value={o.loai} onChange={(e) => setO({ ...o, loai: e.target.value, gan: "" })}><option value="">— chọn —</option>{Object.entries(x.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          {ganKhoa && <label>{o.loai === "phong" ? "Gắn loại phòng" : o.loai === "mon" ? "Gắn món" : "Gắn thực đơn"}<select value={o.gan} onChange={(e) => setO({ ...o, gan: e.target.value })}><option value="">— không gắn —</option>{ganDs.map((g) => <option key={g.id} value={g.id}>{g.ten}</option>)}</select></label>}
          <label>Tiêu đề<input value={o.tieu_de} maxLength={160} onChange={(e) => setO({ ...o, tieu_de: e.target.value })} placeholder={ks ? "Sảnh & lễ tân" : "Bếp hải sản buổi tối"} /></label>
          <label>Nguồn (bắt buộc)<input value={o.nguon} maxLength={200} onChange={(e) => setO({ ...o, nguon: e.target.value })} placeholder={ks ? "Khách sạn gửi / VTD quay" : "Nhà hàng gửi / VTD quay"} /></label>
        </div>
        {f && <div className="muted" style={{ fontSize: 12 }}>{f.name} · {(f.size / MB).toFixed(1)} MB{doc?.thoi_luong ? ` · ${giay(doc.thoi_luong)}` : ""}
          {doc && !doc.phat_duoc && <span style={{ color: "#d99a2b" }}> · Trình duyệt này không phát được tệp (thường là MOV quay iPhone dạng HEVC) — nên xuất lại MP4 trước khi tải.</span>}</div>}
        <label style={{ display: "flex", flexDirection: "row", gap: 8, alignItems: "center", justifyContent: "flex-start", fontSize: 13 }}><input type="checkbox" style={{ width: "auto", margin: 0 }} checked={o.xac_nhan_quyen} onChange={(e) => setO({ ...o, xac_nhan_quyen: e.target.checked })} /><span>Xác nhận Vietourist được phép dùng video này cho khách xem</span></label>
        <div><button className="act teal" disabled={busy || !f || !o.loai || !o.nguon.trim() || !o.xac_nhan_quyen} onClick={tai}>Tải video lên</button>
          {tien && <span className="muted" style={{ marginLeft: 8 }}>Đang tải {(tien.da / MB).toFixed(0)} / {(tien.tong / MB).toFixed(0)} MB</span>}</div>
        {tien && <div style={{ height: 8, background: "#dde3eb", borderRadius: 99, overflow: "hidden" }}><i style={{ display: "block", height: "100%", width: `${(100 * tien.da) / tien.tong}%`, background: "#0f7b74" }} /></div>}
      </>)}
    </div>
    <p className="muted" style={{ margin: 0, fontSize: 12 }}>Tải lên là hiện trên cổng (video «Giới thiệu» đứng đầu). Người tải tự xóa; TP Điều hành, Chủ tịch, TGĐ ẩn / xóa mọi video. Tối đa {x.toi_da} video.</p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(220px,1fr))", gap: 10 }}>{x.video.map((v: any) =>
      <div key={v.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
        {phat === v.id ? <video src={v.xem} poster={v.anh || undefined} controls autoPlay playsInline style={{ width: "100%", aspectRatio: "16 / 9", background: "#000", borderRadius: 6 }} />
          : <button type="button" onClick={() => v.trang_thai !== "dang_tai" && setPhat(v.id)} style={{ position: "relative", padding: 0, border: 0, width: "100%", aspectRatio: "16 / 9", borderRadius: 6, background: v.anh ? `#000 url(${v.anh}) center/cover` : "#16212c", cursor: "pointer" }} aria-label="Phát video">
            <b style={{ position: "absolute", inset: "50% auto auto 50%", transform: "translate(-50%,-50%)", width: 40, height: 40, borderRadius: "50%", background: "rgba(255,255,255,.85)", color: "#16212c", display: "flex", alignItems: "center", justifyContent: "center" }}>▶</b>
            {v.thoi_luong > 0 && <em style={{ position: "absolute", right: 6, bottom: 6, fontStyle: "normal", fontSize: 11, color: "#fff", background: "rgba(0,0,0,.6)", padding: "1px 6px", borderRadius: 4 }}>{giay(v.thoi_luong)}</em>}
            {v.la_gioi_thieu && <span style={{ position: "absolute", left: 6, top: 6, fontSize: 11, fontWeight: 700, background: "#e0b53a", color: "#16212c", padding: "1px 6px", borderRadius: 4 }}>GIỚI THIỆU</span>}
          </button>}
        <b style={{ fontSize: 13 }}>{v.tieu_de || v.ten_tep}</b>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <Tag cls={v.trang_thai === "hien" ? "ok" : "warn"}>{v.trang_thai_ten}</Tag>
          <span className="muted" style={{ fontSize: 12 }}>{v.loai_ten.split(" (")[0].split(" —")[0]}{v.loai_phong_id ? ` · ${loaiPhong.find((p) => p.id === v.loai_phong_id)?.ten || "loại phòng"}` : ""}{v.mon_id ? ` · ${mon.find((p) => p.id === v.mon_id)?.ten || "món"}` : ""}{v.thuc_don_id ? ` · ${thucDon.find((p) => p.id === v.thuc_don_id)?.ten || "thực đơn"}` : ""}</span>
        </div>
        <small className="muted">{(v.kich_thuoc / MB).toFixed(v.kich_thuoc < 10 * MB ? 1 : 0)} MB · nguồn: {v.nguon} · {v.tai_boi}{v.goi_y ? ` · ${v.goi_y}` : ""}</small>
        {duoc(v) && (v.trang_thai === "dang_tai" ? <div><span className="muted" style={{ fontSize: 12 }}>Tải dở ({v.so_phan} phần) — </span><button className="act grey" disabled={busy} onClick={() => viec(v.id, "huy")}>Hủy</button></div>
          : <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button className="act grey" disabled={busy} onClick={() => viec(v.id, "len")} title="Lên">↑</button>
            <button className="act grey" disabled={busy} onClick={() => viec(v.id, "xuong")} title="Xuống">↓</button>
            {v.trang_thai === "hien" && !v.la_gioi_thieu && <button className="act grey" disabled={busy} onClick={() => viec(v.id, "gioi-thieu")}>Đặt làm giới thiệu</button>}
            <button className="act grey" disabled={busy} onClick={() => document.getElementById(`vd-anh-${v.id}`)?.click()}>Đổi ảnh đại diện</button>
            <input id={`vd-anh-${v.id}`} type="file" accept="image/jpeg,image/png,image/webp" style={{ display: "none" }} onChange={(e) => doiAnh(v.id, e.target.files?.[0])} />
            <button className="act grey" disabled={busy} onClick={() => viec(v.id, v.trang_thai === "an" ? "hien" : "an")}>{v.trang_thai === "an" ? "Bỏ ẩn" : "Ẩn"}</button>
            <button className="act grey" disabled={busy} onClick={() => viec(v.id, "xoa")}>Xóa</button>
          </div>)}
      </div>)}
      {!x.video.length && <p className="muted">Chưa có video.</p>}</div>
  </div>;
}

/** Nhà hàng: lấy danh sách món để gắn video món; thực đơn đoàn / tiệc lấy từ gói đặt bàn của nhà hàng. */
export function VideoNhaHang({ nid, toast, thucDon, onDoi }: { nid: number; toast: (m: string, l?: boolean) => void; thucDon: Gan[]; onDoi?: () => void }) {
  const [mon, setMon] = useState<Gan[]>([]);
  useEffect(() => { api<any>(`/nha-hang/${nid}/mon`).then((r) => setMon((r.mon || []).map((m: any) => ({ id: m.id, ten: m.ten })))).catch(() => setMon([])); }, [nid]);
  return <VideoNoiBo goc="/nha-hang" oid={nid} toast={toast} mon={mon} thucDon={thucDon} onDoi={onDoi} />;
}
