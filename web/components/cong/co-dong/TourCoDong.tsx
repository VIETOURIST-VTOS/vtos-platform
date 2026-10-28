"use client";
/* CD-2 · ƯU ĐÃI CỔ ĐÔNG — TOUR DU LỊCH. Cổ đông đã xác minh xem tour đang mở bán và gửi yêu cầu theo ĐÚNG luồng
   của khách hàng (lead cho Sales, ghi nguồn «Cổng cổ đông»). Gửi yêu cầu chưa giữ chỗ, chưa thu tiền.
   Mức ưu đãi riêng cho cổ đông: chưa hiện số đến khi Chủ tịch chốt chính sách. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";

const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");

export default function TourCoDong({ toi, daGui }: { toi: any; daGui: (m: string) => void }) {
  const [q, setQ] = useState("");
  const [ds, setDs] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [loai, setLoai] = useState<"tour" | "tour_doan" | null>(null);
  const [f, setF] = useState({ so_khach: 2, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false });
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tim = useCallback((x = q) => goiCong(`/khach/tour${x ? `?q=${encodeURIComponent(x)}` : ""}`).then(setDs).catch((e) => setLoi(e.message)), [q]);
  useEffect(() => { tim(""); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const gui = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach/yeu-cau", { loai, tour_id: loai === "tour" ? mo?.id : null, so_khach: Number(f.so_khach), dien_thoai: f.dien_thoai,
        ngay_mong_muon: loai === "tour_doan" && f.ngay_mong_muon ? f.ngay_mong_muon : null, ghi_chu: f.ghi_chu, dong_y: f.dong_y });
      daGui(r.message); setLoai(null); setMo(null); setF({ so_khach: 2, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false });
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  if (loai) return (<section className="v3-panel">
    <div className="v3-section-title"><h3>{loai === "tour" ? mo?.ten : "Tour đoàn theo yêu cầu"}</h3><span className="v3-badge demo">Ưu đãi cổ đông</span></div>
    {loai === "tour" && <p>{mo?.ma} · khởi hành {ngay(mo?.khoi_hanh)} · {tien(mo?.gia)} / khách</p>}
    <label className="v3-field">Số khách<input type="number" min={1} max={200} value={f.so_khach} onChange={(e) => setF({ ...f, so_khach: Number(e.target.value) })} /></label>
    <label className="v3-field">Số điện thoại Sales gọi lại{toi.dien_thoai ? " (để trống = số đã xác thực)" : ""}
      <input inputMode="tel" value={f.dien_thoai} placeholder={toi.dien_thoai || "09xx xxx xxx"} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
    {loai === "tour_doan" && <label className="v3-field">Ngày mong muốn<input type="date" value={f.ngay_mong_muon} onChange={(e) => setF({ ...f, ngay_mong_muon: e.target.value })} /></label>}
    <label className="v3-field">Ghi chú cho Sales<textarea rows={3} value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
    <div className="v3-check"><input id="cd-dong-y" type="checkbox" checked={f.dong_y} onChange={(e) => setF({ ...f, dong_y: e.target.checked })} />
      <label htmlFor="cd-dong-y">Tôi hiểu gửi yêu cầu chưa giữ chỗ và chưa thu tiền; giá cuối, chương trình và điều kiện hủy do Sales gửi.</label></div>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    <div className="v3-actions">
      <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => setLoai(null)}><span>Quay lại</span></button>
      <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !f.dong_y} onClick={gui}><span>{busy ? "Đang gửi…" : "Gửi yêu cầu"}</span></button></div>
  </section>);

  return (<>
    <section className="v3-panel"><div className="v3-search"><label className="v3-field">Điểm đến hoặc tên tour<input type="search" value={q} placeholder="Phú Quốc, Đà Nẵng, Huế…"
      onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && tim()} /></label>
      <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => tim()}><span>Tìm tour</span></button></div></section>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    <section className="v3-panel"><div className="v3-section-title"><h3>Tour đang mở bán</h3><span className="v3-badge neutral">{ds ? `${ds.tour.length} tour` : "Đang tải…"}</span></div>
      {ds && ds.tour.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Tour</th><th scope="col">Khởi hành</th><th scope="col">Giá / khách</th><th scope="col"></th></tr></thead>
        <tbody>{ds.tour.map((t: any) => <tr key={t.id}><th scope="row">{t.ten}<small>{t.ma} · {t.thoi_gian}{t.it_cho ? " · còn ít chỗ" : ""}</small></th>
          <td>{ngay(t.khoi_hanh)}</td><td>{tien(t.gia)}</td>
          <td><button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => { setMo(t); setLoai("tour"); }}><span>Gửi yêu cầu</span></button></td></tr>)}</tbody></table></div>
        : ds && <p>Không có tour khớp tìm kiếm.</p>}
      <div className="v3-actions"><button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => { setMo(null); setLoai("tour_doan"); }}><span>Gửi yêu cầu tour đoàn / gia đình</span></button></div>
      <small>Giá công bố. Mức ưu đãi riêng cho cổ đông Vietourist công bố sau.</small></section>
  </>);
}
