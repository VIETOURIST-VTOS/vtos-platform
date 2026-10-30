"use client";
/* KH-3 · VTD Rewards trên cổng khách — Điểm & ưu đãi, Hạng thành viên, Yêu thích & nhắc giá
   (bộ giao diện v3.2, màn KH17–KH19), Chủ tịch duyệt bản xem thử 26/10/2026. Mọi số do máy chủ tính. */
import { useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "./icons";

const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const so = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const trieu = (n: number) => `${(n / 1e6).toLocaleString("vi-VN")} triệu`;
const NGUON: Record<string, string> = { tour: "Tour", dat_ban: "Đặt bàn", khach_san: "Khách sạn", voucher: "Voucher" };   // KS-16

export function useDiem() {
  const [x, setX] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const tai = () => goiCong("/khach/diem").then(setX).catch((e) => setLoi(e.message));
  useEffect(() => { tai(); }, []);
  return { x, loi, tai };
}

export function DiemUuDai({ x, tai, bao }: { x: any; tai: () => void; bao: (m: string) => void }) {
  const [n, setN] = useState("");
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  if (!x) return <section className="v3-panel"><p>Đang tải…</p></section>;
  const doi = async () => {
    setBusy(true); setLoi("");
    try { const r = await goiCong("/khach/diem/doi", { so_diem: Number(n) }); setN(""); bao(r.message); tai(); } catch (e: any) { setLoi(e.message); } finally { setBusy(false); }
  };
  return (<>
    {!x.dang_bat && <div className="v3-notice warn"><I n="info" /><span>VTD Rewards {x.hieu_luc_tu ? `bắt đầu từ ${ngay(x.hieu_luc_tu)}` : "sắp bắt đầu"}. Hiện bạn xem được hạng và chi tiêu; điểm được cộng cho chuyến hoàn tất từ ngày bắt đầu.</span></div>}
    <div className="v3-metrics">
      <section><span><I n="gift" />Điểm khả dụng</span><strong>{so(x.kha_dung)}</strong><small>= {so(x.kha_dung * x.quy_doi)} đ ưu đãi</small></section>
      <section><span><I n="lock-keyhole" />Đang giữ cho voucher</span><strong>{so(x.dang_giu)}</strong><small>{x.voucher.filter((v: any) => v.trang_thai === "cho_dung").length} voucher chưa dùng</small></section>
      <section><span><I n="clock" />Sắp hết hạn (30 ngày)</span><strong>{so(x.sap_het_han)}</strong><small>{x.sap_het_han_ngay ? `sớm nhất ${ngay(x.sap_het_han_ngay)}` : "Không có"}</small></section>
    </div>
    {x.am < 0 && <div className="v3-notice warn"><I n="info" /><span>Ví đang âm {so(-x.am)} điểm do chuyến đã cộng điểm bị hủy / hoàn sau khi điểm đã dùng. Điểm cộng lần sau sẽ bù phần này.</span></div>}
    <div className="v3-two">
      <section className="v3-panel"><div className="v3-section-title"><h3>Đổi điểm lấy voucher</h3></div>
        {loi && <div className="v3-notice warn"><I n="info" /><span>{loi}</span></div>}
        <label className="v3-field">Số điểm muốn đổi (tối thiểu {so(x.doi_toi_thieu)})<input type="number" min={x.doi_toi_thieu} step={100} value={n} disabled={!x.dang_bat} onChange={(e) => setN(e.target.value)} /></label>
        <p>{Number(n) > 0 ? `= ${so(Number(n) * x.quy_doi)} đ. ` : ""}Voucher dùng trong 30 ngày: đặt tour thì đọc mã cho Sales; đặt khách sạn thì tự nhập mã ở bước thanh toán. Một đơn dùng tối đa 5% giá trị. Hết hạn không dùng → điểm trả lại ví.</p>
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !x.dang_bat || Number(n) < x.doi_toi_thieu} onClick={doi}><I n="gift" /><span>{busy ? "Đang đổi…" : "Đổi voucher"}</span></button>
      </section>
      <section className="v3-panel"><div className="v3-section-title"><h3>Voucher của tôi</h3></div>
        {x.voucher.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Mã</th><th scope="col">Giá trị</th><th scope="col">Hạn dùng</th><th scope="col">Trạng thái</th></tr></thead>
          <tbody>{x.voucher.map((v: any) => <tr key={v.ma}><th scope="row">{v.ma}</th><td>{so(v.gia_tri)} đ</td><td>{ngay(v.han_dung)}</td>
            <td><span className={`v3-badge ${v.trang_thai === "cho_dung" ? "demo" : v.trang_thai === "da_dung" ? "good" : "neutral"}`}>{v.trang_thai_ten}{v.booking ? ` · ${v.booking}` : ""}</span></td></tr>)}</tbody></table></div>
          : <p>Chưa có voucher. Đọc mã cho Sales khi đặt tour, hoặc tự nhập khi thanh toán khách sạn.</p>}
      </section>
    </div>
    <section className="v3-panel"><div className="v3-section-title"><h3>Lịch sử điểm</h3></div>
      {x.lich_su.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Ngày</th><th scope="col">Nội dung</th><th scope="col">Điểm</th><th scope="col">Hết hạn</th></tr></thead>
        <tbody>{x.lich_su.map((r: any, i: number) => <tr key={i}><th scope="row">{ngay(r.luc)}</th><td>{r.nguon && <span className="v3-badge neutral" style={{ marginRight: 6 }}>{NGUON[r.nguon] || r.nguon}</span>}{r.loai}<small>{r.noi_dung}</small></td>
          <td>{r.so_diem > 0 ? "+" : "−"}{so(Math.abs(r.so_diem))}</td><td>{r.het_han ? ngay(r.het_han) : "—"}</td></tr>)}</tbody></table></div>
        : <p>Chưa có giao dịch điểm.</p>}
      {(x.cho_cong || []).map((c: any) => <div key={c.ma} className="v3-notice"><I n="clock" /><span>Khách sạn {c.ma}: đã ở, chờ Vietourist chốt đơn — dự kiến +{so(c.du_kien)} điểm.</span></div>)}
      <div className="v3-notice warn"><I n="info" /><span>Điểm tour cộng khi chuyến đã kết thúc và khách đã trả đủ; khách sạn và đặt bàn cộng sau khi Vietourist chốt đơn. Booking qua đại lý / CTV không tích điểm. Hủy hoặc hoàn tiền sau khi cộng → điểm tự trừ tương ứng.</span></div>
    </section>
  </>);
}

export function HangThanhVien({ x }: { x: any }) {
  if (!x) return <section className="v3-panel"><p>Đang tải…</p></section>;
  const h = x.hang; const max = h.bang_hang[h.bang_hang.length - 1].tu;
  const pct = Math.min(100, (h.chi_tieu_12_thang / max) * 100);
  return (<section className="v3-panel">
    <div className="v3-section-title"><h2>Hạng hiện tại: {h.hang}</h2><span className="v3-badge good">Hệ số điểm ×{h.he_so.toLocaleString("vi-VN")}</span></div>
    <p>Chi tiêu xét hạng 12 tháng gần nhất: <b>{so(h.chi_tieu_12_thang)} đ</b>.{h.hang_sau ? <> Cần thêm <b>{so(h.con_thieu)} đ</b> để lên {h.hang_sau}.</> : " Bạn đang ở hạng cao nhất."}</p>
    <div className="kh-thanh" role="img" aria-label={`${pct.toFixed(0)}%`}><i style={{ width: `${pct}%` }} /></div>
    {h.giu_den && <div className="v3-notice warn"><I n="info" /><span>Chi tiêu 12 tháng đang ở mức {h.hang_theo_chi_tieu}. Bạn được giữ hạng {h.hang} đến {ngay(h.giu_den)}.</span></div>}
    <div className="kh-bac">{h.bang_hang.map((b: any, i: number) => <div key={b.hang} className={`kh-bac-o ${b.hang === h.hang ? "on" : ""}`}>
      <b>{b.hang}</b><small>{i + 1 < h.bang_hang.length ? `${b.tu ? `từ ${trieu(b.tu)} ` : ""}dưới ${trieu(h.bang_hang[i + 1].tu)}` : `từ ${trieu(b.tu)}`} · ×{b.he_so.toLocaleString("vi-VN")}</small></div>)}</div>
    <p>Hạng xét lại mỗi ngày theo chuyến đã hoàn tất 12 tháng gần nhất. Tụt dưới ngưỡng thì được giữ hạng thêm 30 ngày.</p>
  </section>);
}

export function YeuThich({ mo }: { mo: (t: any) => void }) {
  const [x, setX] = useState<any>(null);
  const tai = () => goiCong("/khach/yeu-thich").then(setX).catch(() => setX({ yeu_thich: [] }));
  useEffect(() => { tai(); }, []);
  const bo = async (id: number) => { await goiCong("/khach/yeu-thich", { tour_id: id, luu: false }).catch(() => null); tai(); };
  if (!x) return <section className="v3-panel"><p>Đang tải…</p></section>;
  return (<section className="v3-panel"><div className="v3-section-title"><h3>Tour đã lưu</h3></div>
    {x.yeu_thich.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Tour</th><th scope="col">Khởi hành</th><th scope="col">Giá lúc lưu</th><th scope="col">Giá hiện tại</th><th scope="col"></th></tr></thead>
      <tbody>{x.yeu_thich.map((t: any) => <tr key={t.tour_id}><th scope="row">{t.ten}</th><td>{ngay(t.khoi_hanh)}</td><td>{so(t.gia_luc_luu)} đ</td>
        <td>{t.con_ban ? `${so(t.gia_hien_tai)} đ` : "—"}</td>
        <td>{!t.con_ban ? <span className="v3-badge warn">Đã ngừng bán</span> : t.giam > 0 ? <span className="v3-badge good">Giá đã giảm {so(t.giam)} đ</span> : <span className="v3-badge neutral">Chưa đổi</span>}
          {" "}{t.con_ban && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => mo(t.tour)}><span>Xem</span></button>}
          <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => bo(t.tour_id)}><span>Bỏ lưu</span></button></td></tr>)}</tbody></table></div>
      : <p>Chưa lưu tour nào. Bấm ♥ trên thẻ tour để lưu.</p>}
    <p>Nhắc giá hiện ở đây; gửi Zalo / Email khi kênh đã mở và bạn bật «Nhận tin ưu đãi».</p>
  </section>);
}
