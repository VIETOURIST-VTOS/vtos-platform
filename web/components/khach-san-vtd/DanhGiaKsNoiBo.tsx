"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** KS-15 · ĐÁNH GIÁ KHÁCH SẠN VTD trong VTOS (Chủ tịch duyệt bản xem thử 30/10/2026) — như AT-3, thang 10.
 *  Hiện ngay khi khách gửi. Không ai ẩn được vì bài chê — chỉ NV / PTGĐ Marketing ẩn vì vi phạm (4 lý do, phải ghi);
 *  TP Điều hành xem lại mọi bài bị ẩn: giữ ẩn hoặc hiện lại. Khách sạn trả lời qua cổng NCC. */
type Toast = (m: string, loi?: boolean) => void;
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const LOC: [string, string][] = [["", "Tất cả"], ["thap", "Điểm thấp (≤ 5)"], ["anh", "Có ảnh"], ["chua_tra_loi", "Chưa trả lời"], ["da_an", "Đã ẩn"]];

export default function DanhGiaKsNoiBo({ toast, nid }: { toast: Toast; nid?: number }) {
  const [x, setX] = useState<any>(null);
  const [loc, setLoc] = useState("");
  const [an, setAn] = useState<any>(null);            // {id, phan, ly_do, ghi_chu}
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api(`/khach-san-vtd/danh-gia?loc=${loc}`).then(setX).catch((e) => toast(errMsg(e), true)); }, [loc, toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải đánh giá…</p>;
  const ds = x.bai.filter((b: any) => !nid || b.khach_san_id === nid);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setAn(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const the = (t: string, v: any, c?: string) => <div className="panel" style={{ margin: 0, display: "flex", flexDirection: "column", gap: 4 }}>
    <span className="muted" style={{ fontSize: 13 }}>{t}</span><b style={{ fontSize: 24, color: c }}>{v}</b></div>;
  const coAn = (b: any) => b.an || b.tra_loi_an || b.anh.some((a: any) => a.an);
  return <section className="panel" id="ksv-dg-vtos" style={nid ? { margin: 0 } : undefined}>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
      <div><h2 style={{ margin: 0 }}>Đánh giá của khách{nid ? " về khách sạn này" : ""}</h2>
        <div className="muted">Hiện ngay khi khách gửi. Không ai ẩn được vì bài chê — chỉ ẩn vi phạm, phải ghi lý do; TP Điều hành xem lại mọi bài bị ẩn.</div></div>
      </div>
    {!nid && <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 10, margin: "12px 0" }}>
      {the("Bài trong 30 ngày", x.dem.ba_muoi_ngay)}
      {the("Điểm thấp (≤ 5) chưa được trả lời", x.dem.thap_chua_tra_loi, "#b33a3a")}
      {the("Đã ẩn · chờ TP ĐH xem lại", x.dem.cho_xem_lai, "#b07a10")}
      {the("Đơn đã ở (30 ngày) chưa được chấm", x.dem.chua_cham)}</div>}
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>{LOC.map(([k, t]) =>
      <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{t}</button>)}</div>
    <div style={{ overflowX: "auto" }}><table><thead><tr>{!nid && <th>Khách sạn</th>}<th>Điểm</th><th>Nhận xét</th><th>Trả lời</th><th></th></tr></thead>
      <tbody>{ds.map((b: any) => <tr key={b.id} className="ksv-dg-dong" style={coAn(b) ? { background: "rgba(176,122,16,.08)" } : undefined}>
        {!nid && <td><b>{b.khach_san}</b><div className="muted">{b.ten} · {b.loai_phong} · ở {b.thang_o}</div></td>}
        <td><b style={{ color: b.diem <= 5 ? "#e07a7a" : "#7fc4ff" }}>{b.diem}/10</b>
          <div className="muted" style={{ fontSize: 12 }}>{Object.entries(x.muc_ten as Record<string, string>).filter(([k]) => b[k]).map(([k, t]) => `${t} ${b[k]}`).join(" · ")}</div></td>
        <td style={{ maxWidth: 420 }}>
          <div style={{ whiteSpace: "pre-line", textDecoration: b.an ? "line-through" : undefined, opacity: b.an ? .7 : 1 }}>{b.tieu_de && <b>{b.tieu_de}<br /></b>}{b.nhan_xet || <span className="muted">(không ghi nhận xét)</span>}</div>
          {b.anh.length > 0 && <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>{b.anh.map((a: any) =>
            <span key={a.i} style={{ display: "flex", flexDirection: "column", gap: 2, alignItems: "center" }}>
              <img src={a.nho} alt="Ảnh khách" style={{ width: 56, height: 56, objectFit: "cover", borderRadius: 6, opacity: a.an ? .3 : 1 }} />
              {a.an ? <span className="muted" style={{ fontSize: 11 }}>đã ẩn</span> : x.duoc_an && !b.an &&
                <button className="act grey" style={{ fontSize: 11, padding: "2px 6px" }} onClick={() => setAn({ id: b.id, phan: `anh:${a.i}`, ly_do: "anh_sai", ghi_chu: "" })}>Ẩn ảnh</button>}</span>)}</div>}
          {b.an && <div style={{ fontSize: 12, color: "#b07a10", marginTop: 4 }}><b>Đã ẩn</b> bởi {b.an_boi} {ngay(b.an_luc)} · {b.an_ly_do} · {b.an_ghi_chu}</div>}
          {!b.an && b.an_boi && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{b.an_boi} {ngay(b.an_luc)}: {b.an_ly_do} · {b.an_ghi_chu}</div>}
          {b.xem_lai && <div className="muted" style={{ fontSize: 12 }}>TP ĐH {b.xem_lai_boi}: {b.xem_lai === "giu" ? "giữ ẩn" : "hiện lại"}</div>}</td>
        <td style={{ maxWidth: 240 }}>{b.tra_loi ? <><span style={{ color: "#1f7a50" }}>✓</span> <span style={{ textDecoration: b.tra_loi_an ? "line-through" : undefined }}>{b.tra_loi}</span>
          {b.tra_loi_an && <div style={{ fontSize: 12, color: "#b07a10" }}>Đã ẩn · {b.tra_loi_an_ly_do}</div>}
          {x.duoc_an && !b.tra_loi_an && <div><button className="act grey" style={{ fontSize: 11, padding: "2px 6px" }} onClick={() => setAn({ id: b.id, phan: "tra_loi", ly_do: "chui_boi", ghi_chu: "" })}>Ẩn trả lời</button></div>}</>
          : <span className="muted">—</span>}</td>
        <td style={{ minWidth: 150 }}>
          {x.duoc_an && !b.an && <button className="act grey" onClick={() => setAn({ id: b.id, phan: "bai", ly_do: "", ghi_chu: "" })}>Ẩn vì vi phạm…</button>}
          {x.duoc_xem_lai && coAn(b) && !b.xem_lai && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/danh-gia/${b.id}/xem-lai`, { giu: true })}>Giữ ẩn</button>
            <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/danh-gia/${b.id}/xem-lai`, { giu: false })}>Hiện lại</button>
            <span className="muted" style={{ fontSize: 12, width: "100%" }}>TP Điều hành xem lại</span></div>}
          {!coAn(b) && b.diem <= 5 && <span className="muted" style={{ fontSize: 12 }}>Chê không phải vi phạm — không ẩn vì lý do «không đúng».</span>}</td></tr>)}
        {!ds.length && <tr><td colSpan={5} className="muted">{x.bai.length ? "Không có bài khớp bộ lọc." : "Chưa có đánh giá. Khách viết được từ ngày trả phòng của đơn đã xác nhận."}</td></tr>}</tbody></table></div>
    {an && <div className="panel" id="ksv-dg-an" style={{ marginTop: 10 }}>
      <b>Ẩn {an.phan === "bai" ? "bài" : an.phan === "tra_loi" ? "lời trả lời của khách sạn" : "ảnh"} vì vi phạm — chọn một lý do (bắt buộc ghi thêm)</b>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>{Object.entries(x.ly_do as Record<string, string>).map(([k, t]) =>
        <button key={k} className={`act ${an.ly_do === k ? "teal" : "grey"}`} onClick={() => setAn({ ...an, ly_do: k })}>{t}</button>)}</div>
      <label>Chỗ vi phạm (để TP Điều hành xem lại)<input value={an.ghi_chu} onChange={(e) => setAn({ ...an, ghi_chu: e.target.value })} placeholder="vd: có số điện thoại nhân viên" /></label>
      <p className="muted" style={{ fontSize: 13 }}>Ẩn một ảnh thì bài vẫn hiện. Mọi lần ẩn / hiện lại ghi nhật ký. Người viết, khách sạn, Sales không ẩn được.</p>
      <button className="act teal" disabled={busy || !an.ly_do || an.ghi_chu.trim().length < 5} onClick={() => goi(`/khach-san-vtd/danh-gia/${an.id}/an`, an)}>Ẩn</button>{" "}
      <button className="act grey" onClick={() => setAn(null)}>Thôi</button></div>}
  </section>;
}

