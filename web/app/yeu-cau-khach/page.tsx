"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KH-4 · YÊU CẦU KHÁCH TỪ CỔNG — Chủ tịch duyệt bản xem thử 27/10/2026.
 *  Đổi / hủy → Sales phụ trách booking · Hóa đơn → Kế toán · Khác → Sale Admin. Màn này KHÔNG hủy
 *  booking, KHÔNG xuất hóa đơn, KHÔNG chi tiền: làm việc ấy ở màn của nó rồi trả lời khách tại đây.
 *  Máy chủ lọc: Sales chỉ thấy việc giao cho mình. */
const gio = (s?: string | null) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)} ${s.slice(11, 16)}` : "");
const MAU: Record<string, string> = { moi: "warn", dang_xu_ly: "", da_tra_loi: "ok", dong: "" };

function Trang() {
  const { toast } = useShell();
  const [loc, setLoc] = useState("mo");
  const [x, setX] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [tl, setTl] = useState(""); const [bp, setBp] = useState("");
  const tai = useCallback(() => api<any>(`/yeu-cau-khach?trang_thai=${loc}`).then(setX).catch((e) => toast(errMsg(e), true)), [loc, toast]);
  useEffect(() => { tai(); }, [tai]);
  const lam = async (hanh_dong: string) => {
    try {
      const r = await api<any>(`/yeu-cau-khach/${mo.id}`, { method: "POST", json: { hanh_dong, tra_loi: tl, bo_phan: bp } });
      setMo(r); setTl(r.tra_loi || ""); toast("Đã lưu"); tai();
    } catch (e) { toast(errMsg(e), true); }
  };
  return (<>
    <h1>Yêu cầu khách (cổng)</h1>
    <p className="muted">Khách gửi từ kh.vietourist.vn. Trả lời ở đây thì khách thấy trên cổng. Đổi / hủy / hóa đơn thật làm ở màn Booking, Hóa đơn, Đề nghị chi như hiện nay.</p>
    <div className="row">{[["mo", "Đang mở"], ["moi", "Mới"], ["da_tra_loi", "Đã trả lời"], ["dong", "Đã đóng"], ["", "Tất cả"]].map(([k, t]) =>
      <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{t}</button>)}</div>
    <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Loại</th><th>Đơn</th><th>Khách</th><th>Gửi lúc</th><th>Giao cho</th><th>Trạng thái</th></tr></thead>
      <tbody>{!x ? <tr><td colSpan={7}>Đang tải…</td></tr> : x.dong.length ? x.dong.map((y: any) =>
        <tr key={y.id} onClick={() => { setMo(y); setTl(y.tra_loi || ""); setBp(""); }} style={{ cursor: "pointer" }}>
          <td className="mono">{y.ma}</td><td>{y.loai_ten}</td><td className="mono">{y.don || "—"}</td><td>{y.khach} · {y.lien_he}</td>
          <td>{gio(y.gui_luc)}</td><td>{y.giao_cho || y.bo_phan_ten}</td><td><Tag cls={MAU[y.trang_thai]}>{y.trang_thai_ten}</Tag></td></tr>)
        : <tr><td colSpan={7}>Không có yêu cầu nào.</td></tr>}</tbody></table></div>
    {mo && <section className="panel">
      <h2>{mo.ma} · {mo.loai_ten} {mo.don ? `· ${mo.don}` : ""}</h2>
      {mo.noi_dung && <p>{mo.noi_dung}</p>}
      {mo.hoa_don && <p>Hóa đơn: <b>{mo.hoa_don.ten_don_vi}</b> · MST {mo.hoa_don.mst} · {mo.hoa_don.dia_chi}{mo.hoa_don.email ? ` · gửi ${mo.hoa_don.email}` : ""}</p>}
      <p className="muted">Bộ phận: {mo.bo_phan_ten}{mo.giao_cho ? ` · ${mo.giao_cho}` : ""}{mo.nhan_boi ? ` · nhận bởi ${mo.nhan_boi}` : ""}</p>
      <label>Trả lời khách (khách thấy trên cổng)<textarea rows={3} value={tl} onChange={(e) => setTl(e.target.value)} /></label>
      <div className="row">
        {mo.trang_thai === "moi" && <button className="act grey" onClick={() => lam("nhan")}>Nhận việc</button>}
        <button className="act teal" disabled={tl.trim().length < 3} onClick={() => lam("tra_loi")}>Gửi trả lời</button>
        <button className="act grey" disabled={!mo.tra_loi} onClick={() => lam("dong")}>Đóng</button>
        <select value={bp} onChange={(e) => setBp(e.target.value)}><option value="">Chuyển bộ phận…</option>
          {Object.entries(x?.bo_phan || {}).filter(([k]) => k !== mo.bo_phan).map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}</select>
        {bp && <button className="act grey" onClick={() => lam("chuyen")}>Chuyển</button>}
      </div>
    </section>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
