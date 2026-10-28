"use client";
/* KS-1 · KHÁCH SẠN QUA OTA — dùng chung cho cổng Khách hàng, Đối tác, Cổ đông (Chủ tịch duyệt 28/10/2026).
   Không hiện giá, không hiện phòng trống: VTD chưa có nguồn giá được cấp. Khách bấm «Tiếp tục trên …»,
   đọc lời nhắc, rồi MÁY CHỦ ghi lượt chuyển và trả link — trang chỉ gửi mã OTA + request_id + lựa chọn để
   nhắc khách, không gửi link hay thông tin khách. Mở CÙNG THẺ để trình duyệt không chặn cửa sổ bật. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";

const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const uuid = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID()
  : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => { const r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 3) | 8).toString(16); }));

export default function KhachSanOta({ ghiChu }: { ghiChu?: string }) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [dp, setDp] = useState<any[]>([]);
  const [f, setF] = useState({ diem_den: "", nhan_phong: "", tra_phong: "", so_phong: 1, nguoi_lon: 2, tre_em: 0 });
  const [chon, setChon] = useState<any>(null);
  const [rid, setRid] = useState("");
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback(() => {
    goiCong("/khach-san/ota").then((r) => setDs(r.ota)).catch((x) => { setDs([]); setLoi(x.message); });
    goiCong("/khach-san/lich-su").then((r) => { setLs(r.luot); setDp(r.dat_phong || []); }).catch(() => null);
  }, []);
  useEffect(() => { tai(); }, [tai]);
  const tom = [f.diem_den, f.nhan_phong && `${ngay(f.nhan_phong)}${f.tra_phong ? ` – ${ngay(f.tra_phong)}` : ""}`,
    `${f.so_phong} phòng · ${f.nguoi_lon} người lớn${Number(f.tre_em) ? ` · ${f.tre_em} trẻ em` : ""}`].filter(Boolean).join(" · ");
  const moXacNhan = (o: any) => { setChon(o); setRid(uuid()); setLoi(""); };
  const di = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach-san/chuyen", { ota: chon.ma, request_id: rid, ...f, nhan_phong: f.nhan_phong || null, tra_phong: f.tra_phong || null,
        so_phong: Number(f.so_phong), nguoi_lon: Number(f.nguoi_lon), tre_em: Number(f.tre_em) });
      window.location.assign(r.url);
    } catch (x: any) { setLoi(x.message); setBusy(false); }
  };

  if (chon) return (<section className="v3-panel ks-xac-nhan">
    <h2>Bạn sắp chuyển sang {chon.ten}</h2>
    <p>Bạn xem giá, đặt phòng và thanh toán trên {chon.ten}, theo điều kiện của {chon.ten}. Đổi, hủy, hoàn tiền làm với {chon.ten}.</p>
    <div className="v3-notice warn"><span>Trên {chon.ten}, hãy chọn lại: <b>{tom}</b>. Link hiện tại không mang được ngày và điểm đến.</span></div>
    <p className="v3-small">Vietourist có thể nhận hoa hồng từ đặt phòng hợp lệ — giá bạn trả không đổi. Vietourist không gửi số điện thoại, email của bạn cho {chon.ten}.</p>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    <div className="v3-actions">
      <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => setChon(null)}><span>Ở lại</span></button>
      <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={di}><span>{busy ? "Đang mở…" : `Mở ${chon.ten} ↗`}</span></button>
    </div></section>);

  return (<>
    <section className="v3-panel"><div className="v3-section-title"><h3>Bạn muốn ở đâu?</h3></div>
      <div className="v3-form-grid">
        <label className="v3-field">Điểm đến<input value={f.diem_den} placeholder="Đà Nẵng, Phú Quốc…" onChange={(e) => setF({ ...f, diem_den: e.target.value })} /></label>
        <label className="v3-field">Nhận phòng<input type="date" value={f.nhan_phong} onChange={(e) => setF({ ...f, nhan_phong: e.target.value })} /></label>
        <label className="v3-field">Trả phòng<input type="date" value={f.tra_phong} onChange={(e) => setF({ ...f, tra_phong: e.target.value })} /></label>
        <label className="v3-field">Số phòng<input type="number" min={1} max={9} value={f.so_phong} onChange={(e) => setF({ ...f, so_phong: Number(e.target.value) })} /></label>
        <label className="v3-field">Người lớn<input type="number" min={1} max={30} value={f.nguoi_lon} onChange={(e) => setF({ ...f, nguoi_lon: Number(e.target.value) })} /></label>
        <label className="v3-field">Trẻ em<input type="number" min={0} max={20} value={f.tre_em} onChange={(e) => setF({ ...f, tre_em: Number(e.target.value) })} /></label>
      </div>
      <p className="v3-small">Lựa chọn này để bạn nhớ khi sang OTA — bạn chọn lại trên trang OTA.</p></section>
    <section className="v3-panel"><div className="v3-section-title"><h3>Đặt phòng qua đối tác của Vietourist</h3>
      <span className="v3-badge neutral">{ds ? `${ds.length} đối tác đang mở` : "Đang tải…"}</span></div>
      {ds && ds.length > 0 ? <div className="ks-ota">{ds.map((o) => <div key={o.ma} className="ks-the">
        <strong>{o.ten}</strong><small>Xem giá, đặt và thanh toán trên {o.ten}</small>
        <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => moXacNhan(o)}><span>Tiếp tục trên {o.ten} ↗</span></button></div>)}</div>
        : ds && <p>Chưa có đối tác khách sạn nào đang mở. Vui lòng quay lại sau hoặc liên hệ Vietourist.</p>}
      {loi && !chon && <div className="v3-notice warn"><span>{loi}</span></div>}
      <p className="v3-small">VTD chưa hiện giá và phòng trống — giá, phòng và thanh toán xem trên trang đối tác.</p>
      {ghiChu && <div className="v3-notice warn"><span>{ghiChu}</span></div>}</section>
    {dp.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đặt phòng OTA đã xác minh</h3><span className="v3-badge good">{dp.length}</span></div>
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">OTA</th><th scope="col">Thành phố</th><th scope="col">Ngày ở</th><th scope="col">Trạng thái</th></tr></thead>
        <tbody>{dp.map((d, i) => <tr key={i}><th scope="row">{d.ota}</th><td>{d.thanh_pho || "—"}</td><td>{ngay(d.ngay_den)}{d.ngay_di ? ` – ${ngay(d.ngay_di)}` : ""}</td><td>{d.trang_thai}</td></tr>)}</tbody></table></div>
      <p className="v3-small">Đặt phòng do OTA báo về, nối được với lượt bạn mở từ VTD. Đổi, hủy, hoàn tiền làm với OTA.</p></section>}
    {ls.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đã mở OTA</h3><span className="v3-badge neutral">không phải đặt phòng</span></div>
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">Lúc</th><th scope="col">OTA</th><th scope="col">Bạn đã chọn</th></tr></thead>
        <tbody>{ls.map((l, i) => <tr key={i}><td>{ngay(l.luc)} {l.luc.slice(11, 16)}</td><th scope="row">{l.ota}</th><td>{l.da_chon}</td></tr>)}</tbody></table></div>
      <p className="v3-small">Mở trang OTA không chứng minh đã đặt hay đã trả tiền. Cần hỗ trợ một đặt phòng: vào Hỗ trợ, ghi mã đặt phòng OTA.</p></section>}
  </>);
}
