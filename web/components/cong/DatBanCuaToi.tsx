"use client";
/* DT-2 · «Đặt bàn của tôi» — dùng chung cho cổng khách, cổ đông, đại lý, CTV (Chủ tịch duyệt 28/10/2026).
   · Nhà hàng nhận bàn xong mới hiện thanh toán: QR vào tài khoản Vietourist hoặc thẻ Visa / Master / JCB qua
     OnePay (chỉ hiện khi cổng thẻ đã bật). Số tiền do máy chủ tính.
   · Hủy: hiện trước số bị giữ theo chính sách, người đặt xác nhận rồi mới hủy.
   · Đối tác thấy thêm tên khách và doanh số D06 Kế toán đã chốt. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";
import QrThanhToan from "./khach/QrThanhToan";

const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const gio = (s?: string | null) => (s ? `${s.slice(11, 16)} ${ngay(s)}` : "");
const MAU: Record<string, string> = { cho_nhan: "warn", cho_tra: "warn", da_giu: "good", het_han: "bad", tu_choi: "bad", da_dung: "good", khong_den: "bad", huy: "neutral" };

export default function DatBanCuaToi({ doiTac = false, moMa = "" }: { doiTac?: boolean; moMa?: string }) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [mo, setMo] = useState<string>(moMa);
  const [huy, setHuy] = useState<string>("");
  const [doi, setDoi] = useState<any>(null);   // DT-3: form thay đổi {ma, ngay, gio, nguoi_lon, tre_em}
  const [lyDo, setLyDo] = useState("");
  const [msg, setMsg] = useState(""); const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback(() => goiCong("/dat-ban").then((r) => setDs(r.dat_ban)).catch((x) => setLoi(x.message)), []);
  useEffect(() => {
    tai();
    try {
      const q = new URLSearchParams(window.location.search);
      if (q.get("the") === "ok") setMsg(`Thanh toán thẻ thành công — đơn ${q.get("dat_ban") || ""} đã giữ bàn.`);
      if (q.get("the") === "loi") setLoi("Thanh toán thẻ không thành công — bạn có thể thử lại hoặc dùng QR chuyển khoản.");
      if (q.get("the")) window.history.replaceState(null, "", window.location.pathname);
    } catch { /* bỏ qua */ }
  }, [tai]);
  const the = async (ma: string) => {
    setBusy(true); setLoi("");
    try { const r = await goiCong(`/dat-ban/${encodeURIComponent(ma)}/the`, {}); window.location.href = r.url; } catch (x: any) { setLoi(x.message); setBusy(false); }
  };
  const guiDoi = async () => {
    setBusy(true); setLoi(""); setMsg("");
    try {
      const r = await goiCong(`/dat-ban/${encodeURIComponent(doi.ma)}/thay-doi`, { ngay: doi.ngay, gio: doi.gio, nguoi_lon: Number(doi.nguoi_lon), tre_em: Number(doi.tre_em) });
      setDs(r.dat_ban); setMsg(r.message); setDoi(null);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const xacNhanHuy = async (ma: string) => {
    setBusy(true); setLoi(""); setMsg("");
    try { const r = await goiCong(`/dat-ban/${encodeURIComponent(ma)}/huy`, { ly_do: lyDo }); setDs(r.dat_ban); setMsg(r.message); setHuy(""); setLyDo(""); }
    catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  return (<section className="v3-panel"><div className="v3-section-title"><h3>Đặt bàn nhà hàng {doiTac ? "đã gửi" : "của tôi"}</h3><span className="v3-badge neutral">{ds ? ds.length : "…"}</span></div>
    {msg && <div className="v3-notice info"><span>{msg}</span></div>}
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    {!ds ? <p>Đang tải…</p> : !ds.length ? <p>Chưa có đơn đặt bàn nào.</p> : <div className="v3-table-wrap"><table>
      <thead><tr><th scope="col">Mã · nhà hàng</th><th scope="col">Ngày giờ</th><th scope="col">Tiền</th><th scope="col">Trạng thái</th>{doiTac && <th scope="col">Doanh số D06</th>}<th scope="col"></th></tr></thead>
      <tbody>{ds.map((d: any) => <tr key={d.ma}>
        <th scope="row">{d.ma}<small>{d.nha_hang} · {d.thuc_don}{doiTac && d.ten_khach ? ` · ${d.ten_khach}` : ""}</small></th>
        <td>{ngay(d.ngay)} {d.gio}<small>{d.nguoi_lon} NL{d.tre_em ? ` + ${d.tre_em} TE` : ""}{d.la_doan ? " · đoàn" : ""}</small></td>
        <td>{d.cach_tt_ten} · {tien(d.phai_tra_truoc)}<small>đã trả {tien(d.da_tra)} · tại nhà hàng ~{tien(d.tra_tai_ban_du_kien)}</small></td>
        <td><span className={`v3-badge ${MAU[d.trang_thai] || "neutral"}`}>{d.trang_thai_ten}</span>
          {d.ly_do_tu_choi && <small>{d.ly_do_tu_choi}</small>}
          {d.co_the_tra && d.han_tra && <small>Hạn trả {gio(d.han_tra)}</small>}
          {d.hoan_tt_ten && <small>{d.so_giu != null ? `Giữ ${tien(d.so_giu)} · ` : ""}hoàn {tien(d.so_hoan)}{d.da_hoan_tien ? ` (đã hoàn ${tien(d.da_hoan_tien)})` : ""} · {d.hoan_tt_ten}</small>}
          {d.thay_doi && <small>Chờ nhà hàng nhận thay đổi: {ngay(d.thay_doi.ngay)} {d.thay_doi.gio} · {d.thay_doi.nguoi_lon} NL{d.thay_doi.tre_em ? ` + ${d.thay_doi.tre_em} TE` : ""}</small>}
          {d.thay_doi_ghi_chu && <small>{d.thay_doi_ghi_chu}</small>}</td>
        {doiTac && <td>{d.doanh_so != null ? <>{tien(d.doanh_so)}<small>tháng {String(d.ky_d06 || "").split("-").reverse().join("/")}</small></> : "—"}</td>}
        <td style={{ minWidth: 150 }}>
          {d.co_the_tra && <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => setMo(mo === d.ma ? "" : d.ma)}><span>Thanh toán</span></button>}
          {d.co_the_doi && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setDoi(doi?.ma === d.ma ? null : { ma: d.ma, ngay: d.ngay, gio: d.gio, nguoi_lon: d.nguoi_lon, tre_em: d.tre_em, so_lan_doi: d.so_lan_doi })}><span>Thay đổi</span></button>}
          {d.co_the_huy && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => { setHuy(huy === d.ma ? "" : d.ma); setLyDo(""); }}><span>Hủy đặt bàn</span></button>}
        </td></tr>)}</tbody></table></div>}

    {ds && ds.filter((d) => d.ma === mo && d.co_the_tra).map((d) => <div key={d.ma} className="v3-panel" style={{ marginTop: 12 }}>
      <div className="v3-section-title"><h3>Thanh toán {d.ma} · {tien(d.con_phai_tra_truoc)}</h3></div>
      {d.the_bat && <><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={() => the(d.ma)}><span>Trả bằng thẻ Visa / Master / JCB</span></button>
        <small>Mở trang thanh toán OnePay. Vietourist không thấy và không lưu số thẻ. Phí thẻ Vietourist chịu.</small></>}
      <QrThanhToan ma={d.ma} duong="/dat-ban" />
    </div>)}

    {doi && <div className="v3-panel" style={{ marginTop: 12 }}>
      <div className="v3-section-title"><h3>Thay đổi {doi.ma}</h3></div>
      <div className="v3-form-grid">
        <label className="v3-field">Ngày<input type="date" value={doi.ngay} disabled={doi.so_lan_doi >= 1} onChange={(e) => setDoi({ ...doi, ngay: e.target.value })} /></label>
        <label className="v3-field">Giờ<input type="time" value={doi.gio} disabled={doi.so_lan_doi >= 1} onChange={(e) => setDoi({ ...doi, gio: e.target.value })} /></label>
        <label className="v3-field">Người lớn<input type="number" min={1} value={doi.nguoi_lon} onChange={(e) => setDoi({ ...doi, nguoi_lon: e.target.value })} /></label>
        <label className="v3-field">Trẻ em<input type="number" min={0} value={doi.tre_em} onChange={(e) => setDoi({ ...doi, tre_em: e.target.value })} /></label></div>
      <small>Đổi ngày giờ: báo trước 24 giờ, miễn phí 1 lần{doi.so_lan_doi >= 1 ? " — bạn đã dùng lần đổi miễn phí" : ""}; nhà hàng nhận lại khung mới, nếu từ chối bạn giữ lịch cũ hoặc hủy được hoàn đủ.
        Thêm khách: chờ nhà hàng nhận; đủ đoàn thì phần trả trước theo mức đoàn. Bớt khách: áp ngay — trước 24 giờ tính theo số mới và hoàn phần dư, trong 24 giờ tính tối thiểu 80% số đã đặt.</small>
      <div className="v3-actions"><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={guiDoi}><span>Gửi thay đổi</span></button>
        <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setDoi(null)}><span>Thôi</span></button></div>
    </div>}

    {ds && ds.filter((d) => d.ma === huy && d.co_the_huy).map((d) => <div key={d.ma} className="v3-panel" style={{ marginTop: 12 }}>
      <div className="v3-section-title"><h3>Hủy {d.ma}?</h3></div>
      <p>Nếu hủy bây giờ: giữ lại {tien(d.phat_neu_huy_bay_gio)} theo chính sách, hoàn {tien(Math.max(0, d.da_tra - d.phat_neu_huy_bay_gio))}.
        Hoàn tiền: Sales xác nhận, Kế toán hoàn trong 7 ngày làm việc (thẻ về lại thẻ, QR chuyển khoản lại).</p>
      <label className="v3-field">Lý do (không bắt buộc)<input value={lyDo} onChange={(e) => setLyDo(e.target.value)} /></label>
      <div className="v3-actions"><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={() => xacNhanHuy(d.ma)}><span>Xác nhận hủy</span></button>
        <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setHuy("")}><span>Không hủy</span></button></div>
    </div>)}
  </section>);
}
