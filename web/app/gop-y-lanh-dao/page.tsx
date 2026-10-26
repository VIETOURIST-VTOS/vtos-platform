"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KH-4 · GÓP Ý RIÊNG LÃNH ĐẠO — Chủ tịch duyệt 27/10/2026.
 *  Chỉ Chủ tịch HĐQT và Tổng Giám đốc trả lời. Ban Kiểm soát đọc theo luật chung (không trả lời).
 *  Không vai nào khác thấy màn này — kể cả người bị khách nhắc tên. */
const gio = (s?: string | null) => (s ? `${s.slice(8, 10)}/${s.slice(5, 7)} ${s.slice(11, 16)}` : "");
const MAU: Record<string, string> = { moi: "warn", dang_xu_ly: "", da_tra_loi: "ok", dong: "" };

function Trang() {
  const { toast } = useShell();
  const [x, setX] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [tl, setTl] = useState(""); const [gc, setGc] = useState(""); const [tt, setTt] = useState("");
  const tai = useCallback(() => api<any>("/gop-y-lanh-dao").then(setX).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { tai(); }, [tai]);
  const chon = (g: any) => { setMo(g); setTl(g.tra_loi || ""); setGc(g.ghi_chu_noi_bo || ""); setTt(g.trang_thai); };
  const luu = async () => {
    try {
      const r = await api<any>(`/gop-y-lanh-dao/${mo.id}`, { method: "POST", json: { trang_thai: tt, tra_loi: tl, ghi_chu_noi_bo: gc } });
      chon(r); toast("Đã lưu"); tai();
    } catch (e) { toast(errMsg(e), true); }
  };
  return (<>
    <h1>Góp ý riêng lãnh đạo</h1>
    <div className="gate">Chỉ Chủ tịch HĐQT và Tổng Giám đốc trả lời. Ban Kiểm soát đọc theo quy định chung. Không vai nào khác thấy màn này.</div>
    <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Tiêu đề</th><th>Đơn</th><th>Mức</th><th>Gửi lúc</th><th>Trạng thái</th></tr></thead>
      <tbody>{!x ? <tr><td colSpan={6}>Đang tải…</td></tr> : x.dong.length ? x.dong.map((g: any) =>
        <tr key={g.id} onClick={() => chon(g)} style={{ cursor: "pointer" }}>
          <td className="mono">{g.ma}</td><td>{g.tieu_de}</td><td className="mono">{g.don || "—"}</td>
          <td><Tag cls={g.muc === "khan" ? "warn" : ""}>{g.muc_ten}</Tag></td><td>{gio(g.gui_luc)}</td>
          <td><Tag cls={MAU[g.trang_thai]}>{g.trang_thai_ten}</Tag></td></tr>)
        : <tr><td colSpan={6}>Chưa có góp ý nào.</td></tr>}</tbody></table></div>
    {mo && <section className="panel">
      <h2>{mo.ma} · {mo.tieu_de}</h2>
      <p style={{ whiteSpace: "pre-wrap" }}>{mo.noi_dung}</p>
      <p className="muted">Khách: {mo.khach} · {mo.lien_he} · muốn liên hệ lại qua: {mo.lien_he_qua}</p>
      {x?.tra_loi_duoc ? <>
        <label>Trả lời khách (khách thấy trên cổng)<textarea rows={3} value={tl} onChange={(e) => setTl(e.target.value)} /></label>
        <label>Ghi chú nội bộ (khách không thấy)<textarea rows={2} value={gc} onChange={(e) => setGc(e.target.value)} /></label>
        <div className="row"><select value={tt} onChange={(e) => setTt(e.target.value)}>
          {Object.entries(x.trang_thai).map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}</select>
          <button className="act teal" onClick={luu}>Lưu</button></div>
        {mo.tra_loi_boi && <p className="muted">Trả lời bởi {mo.tra_loi_boi} · {gio(mo.tra_loi_luc)}</p>}
      </> : <>{mo.tra_loi && <p><b>Đã trả lời:</b> {mo.tra_loi}</p>}<p className="muted">Bạn chỉ có quyền đọc.</p></>}
    </section>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
