"use client";
/* KH-2 · Tab «Nhà hàng & ẩm thực» trên cổng khách (bộ giao diện v3.2, màn KH08–KH10), Chủ tịch duyệt
   26/10/2026. DT-2 (28/10/2026): đặt bàn CÓ THANH TOÁN, dùng chung cho khách, cổ đông, đại lý, CTV —
   chọn cọc hoặc trả đủ; nhà hàng nhận bàn rồi mới hiện QR / thẻ. Tạm tính và số phải trả hiển thị để người
   đặt hình dung; máy chủ tự tính lại từ giá đã lưu và tham số, không nhận số tiền từ trình duyệt.
   AT-1 (28/10/2026): «Khám phá ẩm thực» — mọi nhà hàng đang hiện giới thiệu; chỉ nơi đã ký hợp đồng (máy tính đủ
   5 điều kiện) mới có thực đơn, giá và nút đặt bàn (giao diện ở KhamPhaAmThuc). Khách xem sau khi nhận OTP qua
   Zalo / email, không tạo tài khoản, không mật khẩu (Chủ tịch chốt 28/10/2026). */
import { useEffect, useMemo, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "./icons";
import KhamPhaAmThuc, { OTrongNh, NhanPl } from "./KhamPhaAmThuc";
import AlbumKhach from "./AlbumKhach";

const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const mai = () => { const t = new Date(Date.now() + 7 * 3600e3 + 86400e3); return t.toISOString().slice(0, 10); };

const nghin = (x: number) => Math.ceil(Math.round(x) / 1000) * 1000;

export default function NhaHangKhach({ ten, lienHe, coSdt, sdtCho, daGui, doiTac = false }: { ten: string; lienHe: string; coSdt: boolean; sdtCho: string; daGui: (msg: string) => void; doiTac?: boolean }) {
  const [ts, setTs] = useState<any>(null);
  useEffect(() => { goiCong("/dat-ban").then((r) => setTs(r.tham_so)).catch(() => {}); }, []);
  const [mo, setMo] = useState<any>(null);
  const [f, setF] = useState<any>(null);
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const goi = useMemo(() => mo && f ? mo.thuc_don.find((t: any) => t.id === Number(f.thuc_don_id)) : null, [mo, f]);
  const tam = goi ? goi.gia_nguoi_lon * Number(f.nguoi_lon || 0) + (goi.gia_tre_em || 0) * Number(f.tre_em || 0) : 0;
  const soKhach = f ? Number(f.nguoi_lon || 0) + Number(f.tre_em || 0) : 0;
  const doan = !!(ts && goi && soKhach >= ts.doan_tu && goi.loai !== "goi_mon");
  const pctCoc = ts ? (doan ? ts.coc_doan : ts.coc_le) : 0;
  const traTruoc = f?.cach_tt === "du" ? tam : Math.min(tam, nghin(tam * pctCoc / 100));
  const datBan = (n: any, tid?: number) => {
    setMo(n); setLoi(""); setF({ thuc_don_id: tid || n.thuc_don[0]?.id, ngay: mai(), gio: "18:30", nguoi_lon: 2, tre_em: 0, ghi_chu: "", dien_thoai: "", ten_khach: "", cach_tt: "coc", dong_y: false, dong_y_khach: false }); window.scrollTo(0, 0); };
  const gui = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/dat-ban", { nha_hang_id: mo.id, thuc_don_id: Number(f.thuc_don_id), ngay: f.ngay, gio: f.gio, nguoi_lon: Number(f.nguoi_lon),
        tre_em: Number(f.tre_em || 0), cach_tt: f.cach_tt, ten_khach: f.ten_khach, dien_thoai: f.dien_thoai, ghi_chu: f.ghi_chu,
        dong_y_chinh_sach: f.dong_y, dong_y_khach: f.dong_y_khach });
      setMo(null); setF(null); daGui(r.message);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  if (mo && f) return (<>
    <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => { setMo(null); setF(null); }}><I n="arrow-left" /><span>Quay lại nhà hàng</span></button>
    {loi && <div className="v3-notice warn"><I n="info" /><span>{loi}</span></div>}
    <AlbumKhach album={mo.album} ten={mo.ten} coTab mon={mo.mon} thucDon={mo.thuc_don_nh} danhGia={mo.danh_gia} nhId={mo.id} oTrong={<OTrongNh n={mo} tl="16/9" />} nhan={<div style={{ marginTop: 8 }}><NhanPl n={mo} /></div>} gioiThieu={mo.mo_ta ? <p style={{ margin: 0 }}>{mo.mo_ta}</p> : <p style={{ margin: 0 }}>Vietourist đang biên tập phần giới thiệu nhà hàng này.</p>} />
    <section className="v3-panel"><div className="v3-section-title"><h2>{mo.ten}</h2><span className="v3-badge neutral">{mo.am_thuc}</span></div>
      <p>{[mo.tinh_thanh, mo.khu_vuc].filter(Boolean).join(" · ")}{mo.gio_phuc_vu ? ` · Giờ phục vụ ${mo.gio_phuc_vu}` : ""}</p>
      {mo.tien_ich && <p>{mo.tien_ich}</p>}{mo.mo_ta && <p>{mo.mo_ta}</p>}
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">Gói</th><th scope="col">Giá người lớn</th><th scope="col">Giá trẻ em</th><th scope="col">Điều kiện</th></tr></thead>
        <tbody>{mo.thuc_don.map((t: any) => <tr key={t.id}><th scope="row">{t.ten}<small>{t.loai_ten}{t.so_khach_toi_thieu > 1 ? ` · tối thiểu ${t.so_khach_toi_thieu} khách` : ""}{t.mo_ta ? ` · ${t.mo_ta}` : ""}</small></th>
          <td>{tien(t.gia_nguoi_lon)}</td><td>{t.gia_tre_em != null ? tien(t.gia_tre_em) : "—"}</td><td>{[t.dieu_kien, t.dieu_kien_huy].filter(Boolean).join(" · ") || "—"}</td></tr>)}</tbody></table></div>
    </section>
    <div className="v3-two">
      <section className="v3-panel"><h2>Đặt bàn</h2>
        <label className="v3-field">Gói<select value={f.thuc_don_id} onChange={(e) => setF({ ...f, thuc_don_id: e.target.value })}>{mo.thuc_don.map((t: any) => <option key={t.id} value={t.id}>{t.ten} · {tien(t.gia_nguoi_lon)}</option>)}</select></label>
        <div className="v3-form-grid">
          <label className="v3-field">Ngày đến<input type="date" min={mai()} value={f.ngay} onChange={(e) => setF({ ...f, ngay: e.target.value })} /></label>
          <label className="v3-field">Giờ đến<input type="time" value={f.gio} onChange={(e) => setF({ ...f, gio: e.target.value })} /></label>
          <label className="v3-field">Người lớn<input type="number" min={1} value={f.nguoi_lon} onChange={(e) => setF({ ...f, nguoi_lon: e.target.value })} /></label>
          <label className="v3-field">Trẻ em<input type="number" min={0} value={f.tre_em} onChange={(e) => setF({ ...f, tre_em: e.target.value })} /></label>
        </div>
        {doiTac ? <div className="v3-form-grid">
          <label className="v3-field">Tên khách<input value={f.ten_khach} onChange={(e) => setF({ ...f, ten_khach: e.target.value })} /></label>
          <label className="v3-field">SĐT khách<input inputMode="tel" value={f.dien_thoai} placeholder="09xx xxx xxx" onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label></div>
        : <><div className="v3-field">Người đặt<div className="v3-readonly">{ten || "Khách hàng"} · {lienHe}</div></div>
          <label className="v3-field">Số điện thoại liên hệ{coSdt ? " (để trống = số đã xác thực)" : ""}<input inputMode="tel" value={f.dien_thoai} placeholder={coSdt ? sdtCho : "09xx xxx xxx"} onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label></>}
        <label className="v3-field">Ghi chú<textarea rows={2} value={f.ghi_chu} placeholder="Ăn chay, ghế trẻ em, dịp đặc biệt…" onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
        <div className="v3-field">Thanh toán trước {doan ? `(đoàn từ ${ts?.doan_tu} khách đặt sẵn menu)` : ""}</div>
        <div className="v31-service-tabs" role="group" aria-label="Cách thanh toán">
          <button type="button" className="cursor-interaction" aria-pressed={f.cach_tt === "coc"} onClick={() => setF({ ...f, cach_tt: "coc" })}><span>Cọc {pctCoc}% · {tien(Math.min(tam, nghin(tam * pctCoc / 100)))}</span></button>
          <button type="button" className="cursor-interaction" aria-pressed={f.cach_tt === "du"} onClick={() => setF({ ...f, cach_tt: "du" })}><span>Trả đủ · {tien(tam)}</span></button></div>
        {ts && <small>Chính sách hủy: trước {ts.mien_phi_gio} giờ hoàn đủ · trong {ts.mien_phi_gio} giờ giữ {ts.phat}% bill · dưới {ts.gan_gio} giờ hoặc không đến: khách lẻ giữ {ts.phat}%, đoàn giữ {ts.phat_doan_gan}% bill. Không giữ quá số đã trả. Nhà hàng hủy hoặc bất khả kháng: hoàn đủ.</small>}
        {doiTac && <div className="v3-check"><input id="nh-dong-y-khach" type="checkbox" checked={f.dong_y_khach} onChange={(e) => setF({ ...f, dong_y_khach: e.target.checked })} />
          <label htmlFor="nh-dong-y-khach">Khách đã đồng ý để tôi chuyển thông tin cho Vietourist.</label></div>}
        <div className="v3-check"><input id="nh-dong-y" type="checkbox" checked={f.dong_y} onChange={(e) => setF({ ...f, dong_y: e.target.checked })} />
          <label htmlFor="nh-dong-y">Tôi đồng ý chính sách thanh toán và hủy bàn. Nhà hàng nhận bàn xong mới hiện thanh toán; bàn chỉ giữ khi tiền đã vào.</label></div>
      </section>
      <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Tạm tính</h3><span className="v3-badge demo">Chưa phải báo giá</span></div>
        {goi && <dl className="v3-stat-rows"><div><dt>{f.nguoi_lon} người lớn × {tien(goi.gia_nguoi_lon)}</dt><dd>{tien(goi.gia_nguoi_lon * Number(f.nguoi_lon || 0))}</dd></div>
          {Number(f.tre_em) > 0 && <div><dt>{f.tre_em} trẻ em × {tien(goi.gia_tre_em || 0)}</dt><dd>{tien((goi.gia_tre_em || 0) * Number(f.tre_em))}</dd></div>}</dl>}
        <div className="v3-total"><span>Tạm tính</span><strong>{tien(tam)}</strong></div>
        <dl className="v3-stat-rows"><div><dt>Trả trước qua Vietourist</dt><dd>{tien(traTruoc)}</dd></div>
          <div><dt>Trả tại nhà hàng sau khi ăn</dt><dd>{tien(Math.max(0, tam - traTruoc))}</dd></div></dl>
        <p>Đồ uống, món gọi thêm và phụ thu trả tại nhà hàng.</p>
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !f.dong_y || (doiTac && !f.dong_y_khach)} onClick={gui}><I n="send" /><span>{busy ? "Đang gửi…" : "Gửi đặt bàn"}</span></button>
      </section>
    </div>
  </>);

  return <KhamPhaAmThuc onDat={datBan} />;
}
