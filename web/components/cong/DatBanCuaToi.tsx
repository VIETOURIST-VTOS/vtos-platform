"use client";
/* DT-2 · «Đặt bàn của tôi» — dùng chung cho cổng khách, cổ đông, đại lý, CTV (Chủ tịch duyệt 28/10/2026).
   · Nhà hàng nhận bàn xong mới hiện thanh toán: QR vào tài khoản Vietourist hoặc thẻ Visa / Master / JCB qua
     OnePay (chỉ hiện khi cổng thẻ đã bật). Số tiền do máy chủ tính.
   · Hủy: hiện trước số bị giữ theo chính sách, người đặt xác nhận rồi mới hủy.
   · Đối tác thấy thêm tên khách và doanh số D06 Kế toán đã chốt. */
import { Fragment, useCallback, useEffect, useState } from "react";
import { goiCong, phienCong, diCongThe } from "@/lib/cong";
import QrThanhToan from "./khach/QrThanhToan";

const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const gio = (s?: string | null) => (s ? `${s.slice(11, 16)} ${ngay(s)}` : "");
// AT-3 · đánh giá sao (Chủ tịch duyệt 29/10/2026): người đặt, đơn «khách đã dùng», 30 ngày; sửa trong 7 ngày.
const MUC_DG: [string, string][] = [["diem_mon", "Món ăn"], ["diem_phuc_vu", "Phục vụ"], ["diem_khong_gian", "Không gian"], ["diem_gia", "Đáng giá tiền"]];
async function guiDanhGia(ma: string, fd: FormData) {
  const headers: Record<string, string> = {}; const p = phienCong();
  if (p) headers["Authorization"] = `Bearer ${p}`;
  const r = await fetch(`/api/v1/cong/dat-ban/${encodeURIComponent(ma)}/danh-gia`, { method: "POST", headers, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw { message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}
function ChonSao({ v, dat, ten, co = 30 }: { v: number; dat: (n: number) => void; ten: string; co?: number }) {
  return <span role="radiogroup" aria-label={ten} style={{ display: "inline-flex", gap: 2 }}>{[1, 2, 3, 4, 5].map((n) =>
    <button key={n} type="button" role="radio" aria-checked={v === n} aria-label={`${n} sao`} className="cursor-interaction"
      onClick={() => dat(v === n && !ten.startsWith("Tổng") ? 0 : n)}
      style={{ all: "unset", cursor: "pointer", fontSize: co, lineHeight: 1, padding: "4px 2px", color: n <= v ? "#b07a10" : "#c9d3dc", minWidth: 28, textAlign: "center" }}>★</button>)}</span>;
}
const MAU: Record<string, string> = { cho_nhan: "warn", cho_tra: "warn", da_giu: "good", het_han: "bad", tu_choi: "bad", da_dung: "good", khong_den: "bad", huy: "neutral" };

export default function DatBanCuaToi({ doiTac = false, moMa = "" }: { doiTac?: boolean; moMa?: string }) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [mo, setMo] = useState<string>(moMa);
  const [huy, setHuy] = useState<string>("");
  const [doi, setDoi] = useState<any>(null);   // DT-3: form thay đổi {ma, ngay, gio, nguoi_lon, tre_em}
  const [lyDo, setLyDo] = useState("");
  const [dg, setDg] = useState<any>(null);     // AT-3: form đánh giá {ma, diem, ..., nhan_xet, dong_y, giu: number[], tep: File[], cu: []}
  const [msg, setMsg] = useState(""); const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const [vc, setVc] = useState("");             // KS-16b: mã voucher VTD Rewards đang gõ
  const voucher = async (ma: string, bo = false) => {
    setBusy(true); setLoi(""); setMsg("");
    try { const r = await goiCong(`/dat-ban/${encodeURIComponent(ma)}/${bo ? "bo-voucher" : "voucher"}`, bo ? {} : { ma_voucher: vc.trim() }); setDs(r.dat_ban); setMsg(r.message); setVc(""); }
    catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const tai = useCallback(() => goiCong("/dat-ban").then((r) => setDs(r.dat_ban)).catch((x) => setLoi(x.message)), []);
  useEffect(() => {
    tai();
    try {
      const q = new URLSearchParams(window.location.search);
      if (q.get("the") === "ok") setMsg(`Thanh toán thẻ thành công — đơn ${q.get("dat_ban") || ""} đã giữ bàn.`);
      if (q.get("the") === "cho") setMsg(`Đã trả qua cổng thẻ — đơn ${q.get("dat_ban") || ""} chuyển «Đã giữ bàn» ngay khi cổng thẻ báo về (thường vài giây).`);
      if (q.get("the") === "huy") setLoi("Bạn đã thoát trang thanh toán thẻ — đơn chưa được trả.");
      if (q.get("the") === "loi") setLoi("Thanh toán thẻ không thành công — bạn có thể thử lại hoặc dùng QR chuyển khoản.");
      if (q.get("the")) window.history.replaceState(null, "", window.location.pathname);
    } catch { /* bỏ qua */ }
  }, [tai]);
  const the = async (ma: string) => {
    setBusy(true); setLoi("");
    try { diCongThe(await goiCong(`/dat-ban/${encodeURIComponent(ma)}/the`, {})); } catch (x: any) { setLoi(x.message); setBusy(false); }
  };
  const guiDoi = async () => {
    setBusy(true); setLoi(""); setMsg("");
    try {
      const r = await goiCong(`/dat-ban/${encodeURIComponent(doi.ma)}/thay-doi`, { ngay: doi.ngay, gio: doi.gio, nguoi_lon: Number(doi.nguoi_lon), tre_em: Number(doi.tre_em) });
      setDs(r.dat_ban); setMsg(r.message); setDoi(null);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const moDg = (d: any) => {
    const b = d.danh_gia?.bai;
    setDg({ ma: d.ma, nha_hang: d.nha_hang, ngay: d.ngay, con_ngay: d.danh_gia?.con_ngay, sua: !!b, diem: b?.diem || 0,
      diem_mon: b?.diem_mon || 0, diem_phuc_vu: b?.diem_phuc_vu || 0, diem_khong_gian: b?.diem_khong_gian || 0, diem_gia: b?.diem_gia || 0,
      nhan_xet: b?.nhan_xet || "", dong_y: !!b, cu: b?.anh || [], giu: (b?.anh || []).map((a: any) => a.i), tep: [] as File[] });
    setLoi(""); setMsg("");
  };
  const guiDg = async () => {
    setBusy(true); setLoi(""); setMsg("");
    try {
      const fd = new FormData();
      for (const k of ["diem", "diem_mon", "diem_phuc_vu", "diem_khong_gian", "diem_gia"]) fd.append(k, String(dg[k] || 0));
      fd.append("nhan_xet", dg.nhan_xet); fd.append("dong_y", dg.dong_y ? "true" : "false"); fd.append("giu_anh", dg.giu.join(","));
      dg.tep.forEach((f: File) => fd.append("anh", f));
      const r = await guiDanhGia(dg.ma, fd); setDs(r.dat_ban); setMsg(r.message); setDg(null);
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
        <td>{d.cach_tt_ten} · {tien(d.phai_tra_truoc)}<small>đã trả {tien(d.da_tra)} · tại nhà hàng ~{tien(d.tra_tai_ban_du_kien)}</small>
          {d.voucher && <small>Voucher {d.voucher.ma} −{tien(d.giam_voucher)}{d.voucher.trang_thai === "da_hoan" ? " · đã trả điểm" : ""}</small>}</td>
        <td><span className={`v3-badge ${MAU[d.trang_thai] || "neutral"}`}>{d.trang_thai_ten}</span>
          {d.ly_do_tu_choi && <small>{d.ly_do_tu_choi}</small>}
          {d.co_the_tra && d.han_tra && <small>Hạn trả {gio(d.han_tra)}</small>}
          {d.hoan_tt_ten && <small>{d.so_giu != null ? `Giữ ${tien(d.so_giu)} · ` : ""}hoàn {tien(d.so_hoan)}{d.da_hoan_tien ? ` (đã hoàn ${tien(d.da_hoan_tien)})` : ""} · {d.hoan_tt_ten}</small>}
          {d.thay_doi && <small>Chờ nhà hàng nhận thay đổi: {ngay(d.thay_doi.ngay)} {d.thay_doi.gio} · {d.thay_doi.nguoi_lon} NL{d.thay_doi.tre_em ? ` + ${d.thay_doi.tre_em} TE` : ""}</small>}
          {d.thay_doi_ghi_chu && <small>{d.thay_doi_ghi_chu}</small>}</td>
        {doiTac && <td>{d.doanh_so != null ? <>{tien(d.doanh_so)}<small>tháng {String(d.ky_d06 || "").split("-").reverse().join("/")}</small></> : "—"}</td>}
        <td style={{ minWidth: 150 }}>
          {d.co_the_tra && (d.mo_thanh_toan === false ? <small>Thanh toán trực tuyến sắp mở cho nhà hàng này</small>   /* AT-2 */
            : <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => setMo(mo === d.ma ? "" : d.ma)}><span>Thanh toán</span></button>)}
          {d.co_the_doi && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setDoi(doi?.ma === d.ma ? null : { ma: d.ma, ngay: d.ngay, gio: d.gio, nguoi_lon: d.nguoi_lon, tre_em: d.tre_em, so_lan_doi: d.so_lan_doi })}><span>Thay đổi</span></button>}
          {d.co_the_huy && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => { setHuy(huy === d.ma ? "" : d.ma); setLyDo(""); }}><span>Hủy đặt bàn</span></button>}
          {d.danh_gia?.duoc_viet && <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => moDg(d)}><span>Đánh giá</span></button>}
          {d.danh_gia?.bai && <small>Đã đánh giá {d.danh_gia.bai.diem}★{d.danh_gia.bai.an ? " · đang tạm ẩn (vi phạm)" : ""}</small>}
          {d.danh_gia?.duoc_sua && <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => moDg(d)}><span>Sửa đánh giá</span></button>}
        </td></tr>)}</tbody></table></div>}

    {ds && ds.filter((d) => d.ma === mo && d.co_the_tra && d.mo_thanh_toan !== false).map((d) => <div key={d.ma} className="v3-panel" style={{ marginTop: 12 }}>
      <div className="v3-section-title"><h3>Thanh toán {d.ma} · {tien(d.con_phai_tra_truoc)}</h3></div>
      {!doiTac && d.dung_voucher && (d.voucher ? <div className="v3-notice info"><span>Đã áp voucher {d.voucher.ma} · trừ {tien(d.giam_voucher)} vào số trả trước.</span>
          <button type="button" className="v3-button v3-quiet cursor-interaction" disabled={busy} onClick={() => voucher(d.ma, true)}><span>Bỏ voucher</span></button></div>
        : <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label className="v3-field" style={{ flex: "1 1 200px" }}>Mã voucher VTD Rewards (không bắt buộc)<input value={vc} placeholder="VTD-XXXXXX" onChange={(e) => setVc(e.target.value.toUpperCase())} /></label>
          <button type="button" className="v3-button v3-quiet cursor-interaction" disabled={busy || !vc.trim()} onClick={() => voucher(d.ma)}><span>Áp dụng</span></button>
          <small style={{ flexBasis: "100%" }}>Trừ vào tiền trả trước, tối đa 5% tạm tính. Hủy được hoàn tiền thì điểm của voucher trả lại.</small></div>)}
      {d.the_bat && <><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={() => the(d.ma)}><span>Trả bằng thẻ Visa / Master / JCB / ATM</span></button>
        <small>Mở trang thanh toán của cổng thẻ (SePay). Vietourist không thấy và không lưu số thẻ. Phí thẻ Vietourist chịu.</small></>}
      <QrThanhToan key={`${d.ma}-${d.con_phai_tra_truoc}`} ma={d.ma} duong="/dat-ban" />
    </div>)}

    {dg && <div className="v3-panel" style={{ marginTop: 12 }} id="dg-form">
      <div className="v3-section-title"><h3>{dg.sua ? "Sửa đánh giá" : "Bữa ăn của bạn thế nào?"} · {dg.nha_hang}</h3></div>
      <small>Ăn ngày {ngay(dg.ngay)}{!dg.sua && dg.con_ngay ? ` · còn ${dg.con_ngay} ngày để đánh giá` : ""}{dg.sua ? " · sửa thì bài cũ được thay hẳn" : ""}</small>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, margin: "10px 0" }}><b>Tổng thể (bắt buộc)</b>
        <ChonSao v={dg.diem} dat={(n) => setDg({ ...dg, diem: n })} ten="Tổng thể" co={34} /></div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(110px, auto) 1fr", gap: "4px 10px", alignItems: "center" }}>
        {MUC_DG.map(([k, t]) => <Fragment key={k}><span>{t}</span><ChonSao v={dg[k]} dat={(n) => setDg({ ...dg, [k]: n })} ten={t} co={24} /></Fragment>)}</div>
      <small>Bốn mục phụ không bắt buộc — bấm lại sao đang chọn để bỏ trống; bỏ trống thì không tính vào điểm mục đó.</small>
      <label className="v3-field">Nhận xét<textarea rows={5} maxLength={1000} value={dg.nhan_xet} placeholder="Món nào ngon, điều gì nhà hàng nên làm tốt hơn…"
        onChange={(e) => setDg({ ...dg, nhan_xet: e.target.value })} /></label>
      <small>{dg.nhan_xet.length}/1.000 ký tự. Không ghi số điện thoại, địa chỉ của người khác.</small>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}><b>Ảnh (tối đa 3)</b>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          {dg.cu.map((a: any) => <label key={a.i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2, fontSize: 12 }}>
            <img src={a.nho} alt="Ảnh đã gửi" style={{ width: 76, height: 76, objectFit: "cover", borderRadius: 8, opacity: dg.giu.includes(a.i) ? 1 : .35 }} />
            <span><input type="checkbox" checked={dg.giu.includes(a.i)} onChange={(e) => setDg({ ...dg, giu: e.target.checked ? [...dg.giu, a.i] : dg.giu.filter((v: number) => v !== a.i) })} /> giữ</span></label>)}
          {dg.tep.map((f: File, k: number) => <span key={k} style={{ fontSize: 12 }}>{f.name} <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setDg({ ...dg, tep: dg.tep.filter((_x: File, j: number) => j !== k) })}><span>Bỏ</span></button></span>)}
          {dg.giu.length + dg.tep.length < 3 && <label className="v3-button v3-quiet cursor-interaction"><span>+ Thêm ảnh</span>
            <input type="file" accept="image/jpeg,image/png,image/webp" multiple style={{ display: "none" }}
              onChange={(e) => { const fs = Array.from(e.target.files || []).slice(0, 3 - dg.giu.length - dg.tep.length); setDg({ ...dg, tep: [...dg.tep, ...fs] }); e.target.value = ""; }} /></label>}</div>
        <small>Ảnh món ăn, không gian (JPG / PNG / WEBP). Máy làm nhẹ ảnh và bỏ thông tin vị trí trong ảnh.</small></div>
      <label style={{ display: "flex", gap: 8, alignItems: "flex-start", margin: "10px 0" }}><input type="checkbox" checked={dg.dong_y} onChange={(e) => setDg({ ...dg, dong_y: e.target.checked })} style={{ marginTop: 3 }} />
        <span>Tôi đồng ý cho Vietourist hiện đánh giá và ảnh này trên trang nhà hàng, tên che còn chữ đầu.</span></label>
      <small>Gửi xong hiện ngay trên trang nhà hàng. Sửa được trong 7 ngày, sau đó khóa. Mỗi đơn một bài.</small>
      <div className="v3-actions"><button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !dg.diem || !dg.dong_y} onClick={guiDg}><span>{dg.sua ? "Lưu đánh giá" : "Gửi đánh giá"}</span></button>
        <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setDg(null)}><span>Thôi</span></button></div>
    </div>}

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
