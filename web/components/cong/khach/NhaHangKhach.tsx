"use client";
/* KH-2 · Tab «Nhà hàng & ẩm thực» trên cổng khách (bộ giao diện v3.2, màn KH08–KH10), Chủ tịch duyệt
   26/10/2026. Gửi yêu cầu đặt bàn đi cùng đường với tour: lead cho Sales, chưa giữ bàn, chưa thu tiền.
   Tạm tính hiển thị để khách hình dung; máy chủ tự tính lại từ giá đã lưu, không nhận số từ trình duyệt. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "./icons";

const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const canh = (a: string) => (a === "Hải sản" ? ["dining-sea", "fish"] : a === "Chay" ? ["dining-garden", "utensils"] : ["dining", "utensils"]);
const mai = () => { const t = new Date(Date.now() + 7 * 3600e3 + 86400e3); return t.toISOString().slice(0, 10); };

export default function NhaHangKhach({ ten, lienHe, coSdt, sdtCho, daGui }: { ten: string; lienHe: string; coSdt: boolean; sdtCho: string; daGui: (msg: string) => void }) {
  const [ds, setDs] = useState<any>(null);
  const [loc, setLoc] = useState({ tinh: "", am_thuc: "", gia_toi_da: "" });
  const [mo, setMo] = useState<any>(null);
  const [f, setF] = useState<any>(null);
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback((l = loc) => {
    const q = new URLSearchParams(Object.entries(l).filter(([, v]) => v) as any).toString();
    goiCong(`/khach/nha-hang${q ? `?${q}` : ""}`).then(setDs).catch((x) => setLoi(x.message));
  }, [loc]);
  useEffect(() => { tai(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const goi = useMemo(() => mo && f ? mo.thuc_don.find((t: any) => t.id === Number(f.thuc_don_id)) : null, [mo, f]);
  const tam = goi ? goi.gia_nguoi_lon * Number(f.nguoi_lon || 0) + (goi.gia_tre_em || 0) * Number(f.tre_em || 0) : 0;
  const datBan = (n: any, tid?: number) => { setMo(n); setLoi(""); setF({ thuc_don_id: tid || n.thuc_don[0]?.id, ngay: mai(), gio: "18:30", nguoi_lon: 2, tre_em: 0, ghi_chu: "", dien_thoai: "", dong_y: false }); window.scrollTo(0, 0); };
  const gui = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach/yeu-cau", { loai: "nha_hang", ngay_mong_muon: f.ngay, dien_thoai: f.dien_thoai, ghi_chu: f.ghi_chu, dong_y: f.dong_y,
        nha_hang: { nha_hang_id: mo.id, thuc_don_id: Number(f.thuc_don_id), gio: f.gio, nguoi_lon: Number(f.nguoi_lon), tre_em: Number(f.tre_em || 0) } });
      setMo(null); setF(null); daGui(r.message);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  if (mo && f) return (<>
    <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => { setMo(null); setF(null); }}><I n="arrow-left" /><span>Quay lại nhà hàng</span></button>
    {loi && <div className="v3-notice warn"><I n="info" /><span>{loi}</span></div>}
    <section className="v3-panel"><div className="v3-section-title"><h2>{mo.ten}</h2><span className="v3-badge neutral">{mo.am_thuc}</span></div>
      <p>{[mo.tinh_thanh, mo.khu_vuc].filter(Boolean).join(" · ")}{mo.gio_phuc_vu ? ` · Giờ phục vụ ${mo.gio_phuc_vu}` : ""}</p>
      {mo.tien_ich && <p>{mo.tien_ich}</p>}{mo.mo_ta && <p>{mo.mo_ta}</p>}
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">Gói</th><th scope="col">Giá người lớn</th><th scope="col">Giá trẻ em</th><th scope="col">Điều kiện</th></tr></thead>
        <tbody>{mo.thuc_don.map((t: any) => <tr key={t.id}><th scope="row">{t.ten}<small>{t.loai_ten}{t.so_khach_toi_thieu > 1 ? ` · tối thiểu ${t.so_khach_toi_thieu} khách` : ""}{t.mo_ta ? ` · ${t.mo_ta}` : ""}</small></th>
          <td>{tien(t.gia_nguoi_lon)}</td><td>{t.gia_tre_em != null ? tien(t.gia_tre_em) : "—"}</td><td>{[t.dieu_kien, t.dieu_kien_huy].filter(Boolean).join(" · ") || "—"}</td></tr>)}</tbody></table></div>
    </section>
    <div className="v3-two">
      <section className="v3-panel"><h2>Gửi yêu cầu đặt bàn</h2>
        <label className="v3-field">Gói<select value={f.thuc_don_id} onChange={(e) => setF({ ...f, thuc_don_id: e.target.value })}>{mo.thuc_don.map((t: any) => <option key={t.id} value={t.id}>{t.ten} · {tien(t.gia_nguoi_lon)}</option>)}</select></label>
        <div className="v3-form-grid">
          <label className="v3-field">Ngày đến<input type="date" min={mai()} value={f.ngay} onChange={(e) => setF({ ...f, ngay: e.target.value })} /></label>
          <label className="v3-field">Giờ đến<input type="time" value={f.gio} onChange={(e) => setF({ ...f, gio: e.target.value })} /></label>
          <label className="v3-field">Người lớn<input type="number" min={1} value={f.nguoi_lon} onChange={(e) => setF({ ...f, nguoi_lon: e.target.value })} /></label>
          <label className="v3-field">Trẻ em<input type="number" min={0} value={f.tre_em} onChange={(e) => setF({ ...f, tre_em: e.target.value })} /></label>
        </div>
        <div className="v3-field">Người gửi<div className="v3-readonly">{ten || "Khách hàng"} · {lienHe}</div></div>
        <label className="v3-field">Số điện thoại Sales gọi lại{coSdt ? " (để trống = số đã xác thực)" : ""}<input inputMode="tel" value={f.dien_thoai} placeholder={coSdt ? sdtCho : "09xx xxx xxx"} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
        <label className="v3-field">Ghi chú<textarea rows={2} value={f.ghi_chu} placeholder="Ăn chay, ghế trẻ em, dịp đặc biệt…" onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
        <div className="v3-check"><input id="nh-dong-y" type="checkbox" checked={f.dong_y} onChange={(e) => setF({ ...f, dong_y: e.target.checked })} />
          <label htmlFor="nh-dong-y">Tôi hiểu gửi yêu cầu chưa giữ bàn và chưa thu tiền; Sales hỏi nhà hàng rồi xác nhận.</label></div>
      </section>
      <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Tạm tính</h3><span className="v3-badge demo">Chưa phải báo giá</span></div>
        {goi && <dl className="v3-stat-rows"><div><dt>{f.nguoi_lon} người lớn × {tien(goi.gia_nguoi_lon)}</dt><dd>{tien(goi.gia_nguoi_lon * Number(f.nguoi_lon || 0))}</dd></div>
          {Number(f.tre_em) > 0 && <div><dt>{f.tre_em} trẻ em × {tien(goi.gia_tre_em || 0)}</dt><dd>{tien((goi.gia_tre_em || 0) * Number(f.tre_em))}</dd></div>}</dl>}
        <div className="v3-total"><span>Tạm tính</span><strong>{tien(tam)}</strong></div>
        <p>Đồ uống, phụ thu và điều kiện hủy do Sales gửi kèm xác nhận.</p>
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !f.dong_y} onClick={gui}><I n="send" /><span>{busy ? "Đang gửi…" : "Gửi yêu cầu"}</span></button>
      </section>
    </div>
  </>);

  return (<>
    <section className="v3-panel"><div className="v3-form-grid">
      <label className="v3-field">Tỉnh / thành<select value={loc.tinh} onChange={(e) => { const l = { ...loc, tinh: e.target.value }; setLoc(l); tai(l); }}>
        <option value="">Tất cả</option>{(ds?.tinh_thanh || []).map((t: string) => <option key={t}>{t}</option>)}</select></label>
      <label className="v3-field">Ẩm thực<select value={loc.am_thuc} onChange={(e) => { const l = { ...loc, am_thuc: e.target.value }; setLoc(l); tai(l); }}>
        <option value="">Tất cả</option>{(ds?.am_thuc || []).map((t: string) => <option key={t}>{t}</option>)}</select></label>
      <label className="v3-field">Giá / người tới<select value={loc.gia_toi_da} onChange={(e) => { const l = { ...loc, gia_toi_da: e.target.value }; setLoc(l); tai(l); }}>
        <option value="">Tất cả</option><option value="300000">300.000 đ</option><option value="500000">500.000 đ</option><option value="1000000">1.000.000 đ</option></select></label>
    </div></section>
    {loi && <div className="v3-notice warn"><I n="info" /><span>{loi}</span></div>}
    <div className="v3-section-title"><h2>Thưởng thức một điểm đến</h2><span className="v3-badge neutral">{ds ? `${ds.nha_hang.length} nhà hàng` : "Đang tải…"}</span></div>
    <div className="v3-products v31-restaurants">{(ds?.nha_hang || []).map((n: any) => {
      const [c, ic] = canh(n.am_thuc); const g = n.thuc_don[0];
      return (<article key={n.id} className="v3-product">
        <div className={`v3-scene ${c}`}><span className="v3-scene-orb" /><span className="v3-scene-icon"><I n={ic} /></span><span className="v3-badge neutral">{n.am_thuc}</span><span className="v3-scene-title">{n.ten}</span></div>
        <div className="v3-product-body"><small><I n="map-pin" /> {[n.tinh_thanh, n.khu_vuc].filter(Boolean).join(" · ")}</small>
          <h3>{g?.ten}{n.thuc_don.length > 1 ? ` · +${n.thuc_don.length - 1} gói` : ""}</h3>{n.tien_ich && <p>{n.tien_ich}</p>}
          <div className="v3-price"><strong>từ {tien(n.gia_tu)}</strong><small>/người lớn</small></div>
          <span className="v3-badge neutral">Cần nhà hàng xác nhận bàn</span>
          <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => datBan(n)}><I n="arrow-up-right" /><span>Xem thực đơn & đặt bàn</span></button></div>
      </article>);
    })}</div>
    {ds && !ds.nha_hang.length && <section className="v3-panel"><p>Chưa có nhà hàng mở đặt bàn{loc.tinh || loc.am_thuc || loc.gia_toi_da ? " khớp bộ lọc" : ""}. Vietourist đang bổ sung danh mục.</p></section>}
  </>);
}
