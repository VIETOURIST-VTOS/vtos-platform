"use client";
/* VB-1 · VÉ MÁY BAY QUA OTA — cổng Khách hàng và Cổ đông (Chủ tịch duyệt 28/10/2026: chỉ OTA, không hãng bay).
   Không hiện giá, lịch bay; không giữ chỗ, không thu tiền. Khách nhập hành trình để NHỚ khi sang OTA, đọc lời
   nhắc, rồi MÁY CHỦ ghi lượt chuyển và trả link. Câu «có thể nhận hoa hồng» chỉ hiện khi OTA dùng link hoa hồng. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";

const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const uuid = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID()
  : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => { const r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 3) | 8).toString(16); }));
const HANG: Record<string, string> = { pho_thong: "Phổ thông", pho_thong_dac_biet: "Phổ thông đặc biệt", thuong_gia: "Thương gia" };

export default function VeMayBayOta() {
  const [ds, setDs] = useState<any[] | null>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [khuHoi, setKhuHoi] = useState(true);
  const [f, setF] = useState({ diem_di: "", diem_den: "", ngay_di: "", ngay_ve: "", nguoi_lon: 1, tre_em: 0, em_be: 0, hang_ve: "pho_thong" });
  const [chon, setChon] = useState<any>(null);
  const [rid, setRid] = useState("");
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback(() => {
    goiCong("/khach-san/ota?san_pham=ve_may_bay").then((r) => setDs(r.ota)).catch((x) => { setDs([]); setLoi(x.message); });
    goiCong("/khach-san/lich-su?san_pham=ve_may_bay").then((r) => setLs(r.luot)).catch(() => null);
  }, []);
  useEffect(() => { tai(); }, [tai]);
  const tom = [[f.diem_di, f.diem_den].filter(Boolean).join(" → "),
    f.ngay_di && `${ngay(f.ngay_di)}${khuHoi && f.ngay_ve ? ` – ${ngay(f.ngay_ve)}` : " · một chiều"}`,
    `${f.nguoi_lon} người lớn${Number(f.tre_em) ? ` · ${f.tre_em} trẻ em` : ""}${Number(f.em_be) ? ` · ${f.em_be} em bé` : ""}`, HANG[f.hang_ve]].filter(Boolean).join(" · ");
  const moXacNhan = (o: any) => { setChon(o); setRid(uuid()); setLoi(""); };
  const di = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach-san/chuyen", { ota: chon.ma, request_id: rid, diem_di: f.diem_di, diem_den: f.diem_den,
        ngay_di: f.ngay_di || null, ngay_ve: khuHoi && f.ngay_ve ? f.ngay_ve : null, nguoi_lon: Number(f.nguoi_lon),
        tre_em: Number(f.tre_em), em_be: Number(f.em_be), hang_ve: f.hang_ve });
      window.location.assign(r.url);
    } catch (x: any) { setLoi(x.message); setBusy(false); }
  };
  const so = (k: "nguoi_lon" | "tre_em" | "em_be", nhan: string, min: number, max: number) =>
    <label className="v3-field">{nhan}<input type="number" min={min} max={max} value={f[k]} onChange={(e) => setF({ ...f, [k]: Number(e.target.value) })} /></label>;

  if (chon) return (<section className="v3-panel ks-xac-nhan">
    <h2>Bạn sắp chuyển sang {chon.ten}</h2>
    <p>Bạn xem giá, đặt vé và thanh toán trên {chon.ten}, theo điều kiện của {chon.ten}. Đổi, hoàn vé, hành lý làm với {chon.ten}.</p>
    <div className="v3-notice warn"><span>Trên {chon.ten}, hãy chọn lại: <b>{tom}</b>. Link hiện tại không mang được hành trình.</span></div>
    <p className="v3-small">{chon.co_hoa_hong ? "Vietourist có thể nhận hoa hồng từ đặt vé hợp lệ — giá bạn trả không đổi. " : ""}Vietourist không gửi số điện thoại, email của bạn cho {chon.ten}.</p>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    <div className="v3-actions">
      <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => setChon(null)}><span>Ở lại</span></button>
      <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={di}><span>{busy ? "Đang mở…" : `Mở ${chon.ten} ↗`}</span></button>
    </div></section>);

  return (<>
    <section className="v3-panel"><div className="v3-section-title"><h3>Bạn muốn bay đi đâu?</h3></div>
      <div className="v3-actions" role="radiogroup" aria-label="Loại hành trình">
        <button type="button" className={`v3-button ${khuHoi ? "v3-primary" : "v3-secondary"} cursor-interaction`} aria-pressed={khuHoi} onClick={() => setKhuHoi(true)}><span>Khứ hồi</span></button>
        <button type="button" className={`v3-button ${!khuHoi ? "v3-primary" : "v3-secondary"} cursor-interaction`} aria-pressed={!khuHoi} onClick={() => setKhuHoi(false)}><span>Một chiều</span></button>
      </div>
      <div className="v3-form-grid">
        <label className="v3-field">Điểm đi<input value={f.diem_di} placeholder="Hà Nội (HAN)" onChange={(e) => setF({ ...f, diem_di: e.target.value })} /></label>
        <label className="v3-field">Điểm đến<input value={f.diem_den} placeholder="Phú Quốc (PQC)" onChange={(e) => setF({ ...f, diem_den: e.target.value })} /></label>
        <label className="v3-field">Ngày đi<input type="date" value={f.ngay_di} onChange={(e) => setF({ ...f, ngay_di: e.target.value })} /></label>
        {khuHoi && <label className="v3-field">Ngày về<input type="date" value={f.ngay_ve} min={f.ngay_di || undefined} onChange={(e) => setF({ ...f, ngay_ve: e.target.value })} /></label>}
        {so("nguoi_lon", "Người lớn", 1, 9)}{so("tre_em", "Trẻ em (2–11)", 0, 8)}{so("em_be", "Em bé (dưới 2)", 0, 9)}
        <label className="v3-field">Hạng<select value={f.hang_ve} onChange={(e) => setF({ ...f, hang_ve: e.target.value })}>
          {Object.entries(HANG).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      <p className="v3-small">Lựa chọn này để bạn nhớ khi sang trang đặt vé — bạn chọn lại trên trang đó.</p></section>
    <section className="v3-panel"><div className="v3-section-title"><h3>Đặt vé qua đối tác của Vietourist</h3>
      <span className="v3-badge neutral">{ds ? `${ds.length} đối tác đang mở` : "Đang tải…"}</span></div>
      {ds && ds.length > 0 ? <div className="ks-ota">{ds.map((o) => <div key={o.ma} className="ks-the">
        <strong>{o.ten}</strong><small>So giá nhiều hãng, đặt và thanh toán trên {o.ten}</small>
        <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => moXacNhan(o)}><span>Tiếp tục trên {o.ten} ↗</span></button></div>)}</div>
        : ds && <p>Chưa có đối tác vé máy bay nào đang mở. Vui lòng quay lại sau hoặc liên hệ Vietourist.</p>}
      {loi && !chon && <div className="v3-notice warn"><span>{loi}</span></div>}
      <p className="v3-small">VTD chưa hiện giá và lịch bay — giá, chỗ và thanh toán xem trên trang đối tác.</p></section>
    {ls.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đã mở trang đặt vé</h3><span className="v3-badge neutral">không phải đặt vé</span></div>
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">Lúc</th><th scope="col">OTA</th><th scope="col">Bạn đã chọn</th></tr></thead>
        <tbody>{ls.map((l, i) => <tr key={i}><td>{ngay(l.luc)} {l.luc.slice(11, 16)}</td><th scope="row">{l.ota}</th><td>{l.da_chon}</td></tr>)}</tbody></table></div>
      <p className="v3-small">Mở trang OTA không chứng minh đã đặt hay đã trả tiền. Cần hỗ trợ một vé: vào Hỗ trợ, ghi mã đặt chỗ của OTA.</p></section>}
  </>);
}
