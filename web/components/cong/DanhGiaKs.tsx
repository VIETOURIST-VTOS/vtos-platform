"use client";
/* KS-15 · Đánh giá khách sạn VTD (Chủ tịch duyệt bản xem thử 30/10/2026) — như đánh giá nhà hàng AT-3, thang 10 như Agoda.
   Chỉ khách đã đặt qua VTD và đã ở viết được (từ ngày trả phòng, 30 ngày); hiện ngay; tên khách đã che.
   Dùng trong KhachSanVtd (nằm trong khung .ksv, dùng chung CSS ở đó). */
import { useCallback, useEffect, useState } from "react";
import { goiCong, phienCong } from "@/lib/cong";

export const MUC_KS: [string, string][] = [["diem_sach", "Sạch sẽ"], ["diem_vi_tri", "Vị trí"], ["diem_phong", "Phòng"], ["diem_phuc_vu", "Phục vụ"], ["diem_gia", "Đáng giá tiền"]];
const DI_CUNG: [string, string][] = [["", "— không ghi —"], ["mot_minh", "Đi một mình"], ["cap_doi", "Cặp đôi"], ["gia_dinh_tre_nho", "Gia đình có trẻ nhỏ"],
  ["gia_dinh", "Gia đình"], ["nhom_ban", "Nhóm bạn"], ["cong_tac", "Công tác"]];
const so = (x?: number | null) => (x == null ? "" : String(x).replace(".", ","));
export const nhanDiem = (d?: number | null) => (d == null ? "" : d >= 9 ? "Xuất sắc" : d >= 8.5 ? "Tuyệt vời" : d >= 8 ? "Rất tốt" : d >= 7 ? "Tốt" : d >= 6 ? "Dễ chịu" : "Trung bình");

export function OD({ d, lon = false }: { d: number; lon?: boolean }) {
  return <span className={`ksv-od ${d < 7 ? "xam" : ""} ${lon ? "lon" : ""}`}>{so(d)}</span>;
}

/** Ô điểm cạnh tên khách sạn. dg = tom_tat từ máy chủ. */
export function TomTatDg({ dg, toi = "ksv-dg" }: { dg: any; toi?: string }) {
  const keo = (e: any) => { e.preventDefault(); document.getElementById(toi)?.scrollIntoView({ behavior: "smooth" }); };
  return <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
    {dg?.diem_tb != null ? <><OD d={dg.diem_tb} lon /><span style={{ display: "flex", flexDirection: "column" }}><b style={{ fontSize: 17 }}>{dg.nhan || nhanDiem(dg.diem_tb)}</b>
      <span className="ksv-muted" style={{ fontSize: 13 }}>{dg.so_bai} đánh giá của khách đã ở</span><a href={`#${toi}`} onClick={keo} className="ksv-link" style={{ fontSize: 13 }}>Xem đánh giá</a></span></>
      : <span style={{ display: "flex", flexDirection: "column", gap: 2 }}><b style={{ fontSize: 16 }}>Đánh giá của khách</b>
        <span className="ksv-muted" style={{ fontSize: 13 }}>{dg?.so_bai ? `Mới — chưa đủ đánh giá (${dg.so_bai} bài)` : "Chưa có đánh giá. Chỉ khách đặt qua Vietourist và đã ở mới viết được."}</span>
        {dg?.so_bai > 0 && <a href={`#${toi}`} onClick={keo} className="ksv-link" style={{ fontSize: 13 }}>Xem bài</a>}</span>}</div>;
}

/** Mục «Đánh giá của khách» trên trang khách sạn. */
export function DanhGiaKsCong({ kid }: { kid: number }) {
  const [x, setX] = useState<any>(null);
  const [xep, setXep] = useState("moi");
  const [trang, setTrang] = useState(1);
  const tai = useCallback(() => {
    goiCong(`/ks-vtd/${kid}/danh-gia?xep=${xep}&trang=${trang}`).then(setX).catch(() => setX({ bai: [], tong: 0, tom_tat: {} }));
  }, [kid, xep, trang]);
  useEffect(() => { tai(); }, [tai]);
  if (!x) return null;
  const t = x.tom_tat || {};
  return <section className="ksv-panel" id="ksv-dg" style={{ padding: 20, gap: 14 }}>
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", alignItems: "baseline" }}><h2 style={{ margin: 0, fontSize: 20 }}>Đánh giá của khách</h2>
      <span className="ksv-muted" style={{ fontSize: 13 }}>Chỉ khách đặt qua Vietourist và đã ở mới viết được · không ai ẩn được bài vì chê</span></div>
    {t.diem_tb != null ? <div style={{ display: "flex", flexWrap: "wrap", gap: 20 }}>
      <div style={{ flex: "0 0 180px", display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-start" }}><OD d={t.diem_tb} lon /><b style={{ fontSize: 18 }}>{t.nhan}</b>
        <span className="ksv-muted" style={{ fontSize: 13 }}>Trung bình {t.so_bai} bài</span></div>
      <div style={{ flex: "1 1 320px", display: "flex", flexDirection: "column", gap: 10, fontSize: 14 }}>{MUC_KS.filter(([k]) => t.muc?.[k] != null).map(([k, ten]) =>
        <div key={k} style={{ display: "flex", gap: 10, alignItems: "center" }}><span style={{ flex: "0 0 120px" }}>{ten}</span>
          <span className="ksv-bar10" aria-hidden="true"><span style={{ width: `${t.muc[k] * 10}%` }} /></span><b style={{ flex: "0 0 34px", textAlign: "right" }}>{so(t.muc[k])}</b></div>)}</div></div>
      : <div className="ksv-moi">{x.tong ? `Mới — chưa đủ đánh giá: cần ít nhất ${x.toi_thieu || 3} bài để hiện điểm trung bình.` : "Chưa có bài đánh giá nào."}</div>}
    {x.tong > 0 && <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{[["moi", "Mới nhất"], ["cao", "Điểm cao nhất"], ["thap", "Điểm thấp nhất"], ["anh", "Có ảnh"]].map(([k, ten]) =>
      <button key={k} type="button" className={`ksv-chip ${xep === k ? "on" : ""}`} aria-pressed={xep === k} onClick={() => { setXep(k); setTrang(1); }}>{ten}</button>)}</div>}
    {x.bai.map((b: any) => <Bai key={b.id} b={b} />)}
    {x.tong > trang * 10 && <button type="button" className="ksv-btn line" style={{ alignSelf: "flex-start" }} onClick={() => setTrang(trang + 1)}>Xem thêm</button>}
  </section>;
}

function Bai({ b }: { b: any }) {
  return <article className="ksv-bai">
    <div className="ksv-bai-ai"><b>{b.ten}</b>{b.di_cung_ten && <span>{b.di_cung_ten}</span>}<span>{b.loai_phong} · {b.so_dem} đêm</span><span>Ở tháng {b.thang_o}</span></div>
    <div style={{ flex: "1 1 360px", minWidth: 0, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}><OD d={b.diem} /><b>{b.tieu_de || b.nhan}</b>{b.da_sua && <small className="ksv-muted">đã sửa</small>}</div>
      {b.nhan_xet && <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-line" }}>{b.nhan_xet}</p>}
      {b.anh?.length > 0 && <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{b.anh.map((a: any) =>
        <a key={a.i} href={a.hien} target="_blank" rel="noreferrer"><img src={a.nho} alt={`Ảnh khách chụp ${a.i + 1}`} loading="lazy" style={{ width: 84, height: 64, objectFit: "cover", borderRadius: 8 }} /></a>)}</div>}
      {b.tra_loi && <div className="ksv-tl-ks"><b>Phản hồi của khách sạn</b><br />{b.tra_loi}</div>}
    </div></article>;
}

async function guiForm(ma: string, fd: FormData) {
  const headers: Record<string, string> = {}; const p = phienCong();
  if (p) headers["Authorization"] = `Bearer ${p}`;
  const r = await fetch(`/api/v1/cong/ks-vtd/don/${encodeURIComponent(ma)}/danh-gia`, { method: "POST", headers, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw { message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}

/** Khách đã ở viết / sửa đánh giá cho một đơn. dg = d.danh_gia của đơn. */
export function VietDanhGiaKs({ d, onXong, onThoi }: { d: any; onXong: (r: any) => void; onThoi: () => void }) {
  const cu = d.danh_gia?.bai;
  const [f, setF] = useState<any>(() => ({ diem: cu?.diem || 0, ...Object.fromEntries(MUC_KS.map(([k]) => [k, cu?.[k] || 0])),
    di_cung: cu?.di_cung || "", tieu_de: cu?.tieu_de || "", nhan_xet: cu?.nhan_xet || "", dong_y: false }));
  const [giu, setGiu] = useState<number[]>(() => (cu?.anh || []).map((a: any) => a.i));
  const [tep, setTep] = useState<File[]>([]);
  const [loi, setLoi] = useState("");
  const [busy, setBusy] = useState(false);
  const gui = async () => {
    if (!f.diem) { setLoi("Chọn điểm chung từ 1 đến 10"); return; }
    if (!f.dong_y) { setLoi("Đánh dấu đồng ý cho Vietourist hiện bài công khai"); return; }
    if (giu.length + tep.length > 3) { setLoi("Tối đa 3 ảnh"); return; }
    setBusy(true); setLoi("");
    try {
      const fd = new FormData();
      for (const k of ["diem", ...MUC_KS.map(([k2]) => k2), "di_cung", "tieu_de", "nhan_xet"]) fd.append(k, String(f[k] ?? ""));
      fd.append("dong_y", "true"); fd.append("giu_anh", giu.join(","));
      for (const t of tep) fd.append("anh", t);
      onXong(await guiForm(d.ma, fd));
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  return <section className="ksv-panel" style={{ padding: 22, gap: 16 }} aria-label="Viết đánh giá">
    <h2 style={{ margin: 0, fontSize: 21 }}>{cu ? "Sửa đánh giá" : "Đánh giá kỳ ở"} tại {d.khach_san?.ten}</h2>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}><b>Điểm chung (bắt buộc)</b>
      <div role="radiogroup" aria-label="Điểm chung 1 đến 10" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{Array.from({ length: 10 }, (_, i) => i + 1).map((n) =>
        <button key={n} type="button" role="radio" aria-checked={f.diem === n} className={`ksv-so ${f.diem === n ? "on" : ""}`} onClick={() => setF({ ...f, diem: n })}>{n}</button>)}</div>
      {f.diem > 0 && <small className="ksv-muted">{f.diem} — {nhanDiem(f.diem)}</small>}</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}><b>Từng mục (không bắt buộc — bỏ trống khác với chấm thấp)</b>
      <div className="ksv-f2">{MUC_KS.map(([k, ten]) => <label key={k} className="ksv-fld">{ten}
        <select className="ksv-sel" value={f[k]} onChange={(e) => setF({ ...f, [k]: Number(e.target.value) })}><option value={0}>— bỏ trống —</option>
          {Array.from({ length: 10 }, (_, i) => 10 - i).map((n) => <option key={n} value={n}>{n}</option>)}</select></label>)}
        <label className="ksv-fld">Bạn đi cùng<select className="ksv-sel" value={f.di_cung} onChange={(e) => setF({ ...f, di_cung: e.target.value })}>
          {DI_CUNG.map(([k, ten]) => <option key={k} value={k}>{ten}</option>)}</select></label></div></div>
    <label className="ksv-fld">Tiêu đề<input value={f.tieu_de} maxLength={120} onChange={(e) => setF({ ...f, tieu_de: e.target.value })} /></label>
    <label className="ksv-fld">Nhận xét (tối đa 1.000 ký tự)<textarea value={f.nhan_xet} maxLength={1000} rows={4} onChange={(e) => setF({ ...f, nhan_xet: e.target.value })} /></label>
    {cu?.anh?.length > 0 && <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{cu.anh.map((a: any) =>
      <label key={a.i} className="ksv-chk" style={{ flexDirection: "column", alignItems: "flex-start" }}><img src={a.nho} alt="" style={{ width: 84, height: 64, objectFit: "cover", borderRadius: 8 }} />
        <span><input type="checkbox" checked={giu.includes(a.i)} onChange={(e) => setGiu(e.target.checked ? [...giu, a.i] : giu.filter((y) => y !== a.i))} /> Giữ ảnh</span></label>)}</div>}
    <label className="ksv-fld">Ảnh (tối đa 3 — máy làm nhẹ, bỏ vị trí GPS)<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => setTep(Array.from(e.target.files || []).slice(0, 3))} /></label>
    <label className="ksv-chk" style={{ alignItems: "flex-start" }}><input type="checkbox" checked={f.dong_y} onChange={(e) => setF({ ...f, dong_y: e.target.checked })} />
      <span style={{ fontSize: 13 }}>Tôi đồng ý cho Vietourist hiện bài này công khai, tên che còn chữ đầu, không kèm số điện thoại hay mã đơn.</span></label>
    {loi && <div className="ksv-loi">{loi}</div>}
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
      <button type="button" className="ksv-btn" disabled={busy} onClick={gui}>{cu ? "Lưu đánh giá" : "Gửi đánh giá"}</button>
      <button type="button" className="ksv-btn line" onClick={onThoi}>Thôi</button>
      <small className="ksv-muted">Hiện ngay trên trang khách sạn. Sửa được trong 7 ngày.</small></div>
  </section>;
}
