"use client";
/* KH-4 · Đánh giá chuyến đi (KH20/KH25), Góp ý riêng lãnh đạo (KH21), Hỗ trợ đổi · hủy · hóa đơn
   (KH22/KH24) — bộ giao diện v3.2, Chủ tịch duyệt bản xem thử 27/10/2026. Máy chủ quyết mục nào
   được chấm, ai đọc góp ý, yêu cầu về bộ phận nào; trang này chỉ hiện và gửi. */
import { useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "./icons";

const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const MAU: Record<string, string> = { moi: "demo", dang_xu_ly: "neutral", da_tra_loi: "good", dong: "neutral" };
const Loi = ({ m }: { m: string }) => (m ? <div className="v3-notice warn"><I n="info" /><span>{m}</span></div> : null);
const khoa = (m: any) => `${m.doi_tuong}:${m.id ?? ""}`;

function Sao({ v, dat }: { v: number | null; dat: (n: number | null) => void }) {
  return (<span className="kh-sao" role="radiogroup">{[1, 2, 3, 4, 5].map((n) =>
    <button key={n} type="button" role="radio" aria-checked={v === n} aria-label={`${n} sao`} className={`cursor-interaction ${v && n <= v ? "on" : ""}`}
      onClick={() => dat(v === n ? null : n)}>★</button>)}</span>);
}

// ── ĐÁNH GIÁ ─────────────────────────────────────────────────────────────────────────────────
export function DanhGiaKhach({ diHoTro }: { diHoTro: () => void }) {
  const [x, setX] = useState<any>(null);
  const [mo, setMo] = useState<any>(null);
  const [diem, setDiem] = useState<Record<string, { diem: number | null; nhan_xet: string }>>({});
  const [ck, setCk] = useState(""); const [tiep, setTiep] = useState(""); const [gy, setGy] = useState("");
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false); const [xong, setXong] = useState<any>(null);
  const tai = () => goiCong("/khach/danh-gia").then(setX).catch((e) => setLoi(e.message));
  useEffect(() => { tai(); }, []);
  const moPhieu = (c: any) => {
    const d: any = {};
    for (const m of c.muc) d[khoa(m)] = { diem: null, nhan_xet: "" };
    for (const m of c.da_cham || []) d[khoa(m)] = { diem: m.diem, nhan_xet: m.nhan_xet };
    setDiem(d); setCk(c.cong_khai || ""); setTiep(c.nhu_cau_tiep || ""); setGy(c.gop_y || ""); setLoi(""); setXong(null); setMo(c);
  };
  const gui = async () => {
    setBusy(true); setLoi("");
    try {
      const ds = mo.muc.map((m: any) => ({ doi_tuong: m.doi_tuong, id: m.id, ...diem[khoa(m)] }));
      const r = await goiCong("/khach/danh-gia", { ma_don: mo.ma, diem: ds, nhu_cau_tiep: tiep, cong_khai: ck, gop_y: gy });
      setXong({ ...mo, han_sua: r.han_sua, ds, ck }); setMo(null); tai();
    } catch (e: any) { setLoi(e.message); } finally { setBusy(false); }
  };
  if (!x) return <section className="v3-panel"><p>{loi || "Đang tải…"}</p></section>;
  if (xong) return (<section className="v3-panel">
    <div className="v3-notice info"><I n="check" /><span>Cảm ơn bạn đã đánh giá {xong.ten}. Bạn sửa được đến {ngay(xong.han_sua)}.</span></div>
    <dl className="v3-stat-rows">{xong.muc.map((m: any) => <div key={khoa(m)}><dt>{m.nhan}{m.ten && m.doi_tuong !== "tour" ? ` · ${m.ten}` : ""}</dt>
      <dd>{diem[khoa(m)]?.diem ? `${diem[khoa(m)].diem}★` : "Không chấm"}</dd></div>)}</dl>
    <p>Công khai nhận xét: <b>{xong.ck === "co" ? "Có, không kèm tên" : "Không"}</b>. Đánh giá thấp không bị ẩn vì điểm thấp.</p>
    <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setXong(null)}><span>Về danh sách chuyến</span></button>
  </section>);
  if (mo) {
    const lanDau = mo.trang_thai !== "da_gui";
    return (<section className="v3-panel">
      <div className="v3-section-title"><h2>{mo.ten}</h2><span className="v3-badge good">Đã đi · kết thúc {ngay(mo.ket_thuc)}</span></div>
      <p>Chấm mục bạn đã dùng; mục nào bỏ trống là không chấm (không tính là 0).</p>
      <div className="kh-dg-luoi">{mo.muc.map((m: any) => <div key={khoa(m)} className="kh-dg-o">
        <strong>{m.nhan}</strong>{m.ten && m.doi_tuong !== "tour" && <small>{m.ten}</small>}
        <Sao v={diem[khoa(m)]?.diem ?? null} dat={(n) => setDiem({ ...diem, [khoa(m)]: { ...diem[khoa(m)], diem: n } })} />
        <input placeholder="Nhận xét ngắn (không bắt buộc)" value={diem[khoa(m)]?.nhan_xet || ""} maxLength={500}
          onChange={(e) => setDiem({ ...diem, [khoa(m)]: { ...diem[khoa(m)], nhan_xet: e.target.value } })} /></div>)}</div>
      <label className="v3-field">Nhận xét chung<textarea rows={3} value={gy} maxLength={2000} onChange={(e) => setGy(e.target.value)} /></label>
      <fieldset className="kh-dg-hoi"><legend>Bạn có muốn Vietourist gợi ý chuyến đi tiếp theo?</legend>
        {[["co", "Có"], ["khong", "Không"]].map(([k, t]) => <label key={k} className="v3-check"><input type="radio" name="tiep" checked={tiep === k} onChange={() => setTiep(k)} />{t}</label>)}</fieldset>
      <fieldset className="kh-dg-hoi"><legend>Công khai nhận xét — chọn riêng, không bắt buộc đồng ý</legend>
        {lanDau || ck === "co" ? [["co", "Đồng ý Vietourist đăng nhận xét công khai, không kèm tên và liên hệ của tôi"], ["khong", "Không đồng ý — chỉ nội bộ Vietourist đọc"]].map(([k, t]) =>
          <label key={k} className="v3-check"><input type="radio" name="ck" checked={ck === k} onChange={() => setCk(k)} />{t}</label>)
          : <p>Bạn đã chọn không công khai.</p>}
      </fieldset>
      <div className="v3-notice warn"><I n="info" /><span>Có sự cố cần xử lý hoặc bồi thường? Gửi ở mục <button type="button" className="v3-link cursor-interaction" onClick={diHoTro}>Hỗ trợ</button> — khiếu nại tách khỏi đánh giá để được giao người xử lý.</span></div>
      <Loi m={loi} />
      <div className="v3-actions">
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !tiep || !ck} onClick={gui}><I n="send" /><span>{busy ? "Đang gửi…" : lanDau ? "Gửi đánh giá" : "Lưu đánh giá đã sửa"}</span></button>
        <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setMo(null)}><span>Quay lại</span></button></div>
    </section>);
  }
  return (<section className="v3-panel"><div className="v3-section-title"><h3>Chuyến đi của bạn</h3></div>
    <Loi m={loi} />
    {x.chuyen.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Chuyến</th><th scope="col">Ngày đi</th><th scope="col">Đánh giá</th><th scope="col"></th></tr></thead>
      <tbody>{x.chuyen.map((c: any) => <tr key={c.ma}><th scope="row">{c.ten}<small>{c.ma}</small></th><td>{ngay(c.khoi_hanh)}{c.ket_thuc ? ` – ${ngay(c.ket_thuc)}` : ""}</td>
        <td>{c.trang_thai === "da_gui" ? <span className="v3-badge good">Đã gửi{c.sua_duoc ? ` · sửa đến ${ngay(c.han_sua)}` : ""}</span>
          : c.trang_thai === "mo" ? <span className="v3-badge demo">Chưa chấm · mở đến {ngay(c.han_cham)}</span>
          : c.trang_thai === "chua_di" ? <span className="v3-badge neutral">Chưa đi</span> : <span className="v3-badge neutral">Đã hết hạn chấm</span>}</td>
        <td>{(c.trang_thai === "mo" || (c.trang_thai === "da_gui" && c.sua_duoc)) &&
          <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => moPhieu(c)}><span>{c.trang_thai === "mo" ? "Chấm điểm" : "Sửa"}</span></button>}</td></tr>)}</tbody></table></div>
      : <p>Chưa có chuyến nào gắn với tài khoản. Chuyến đi xong mở chấm trong {x.mo_cham_ngay} ngày.</p>}
    <p>Chỉ chuyến đã đi mới chấm được, mở {x.mo_cham_ngay} ngày sau khi về; gửi rồi sửa được {x.sua_ngay} ngày.</p>
  </section>);
}

// ── GÓP Ý RIÊNG LÃNH ĐẠO ─────────────────────────────────────────────────────────────────────
export function GopYKhach({ don, bao }: { don: any[]; bao: (m: string) => void }) {
  const [x, setX] = useState<any>(null);
  const [f, setF] = useState({ tieu_de: "", noi_dung: "", muc: "thuong", lien_he_qua: "email", ma_don: "" });
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = () => goiCong("/khach/gop-y").then(setX).catch((e) => setLoi(e.message));
  useEffect(() => { tai(); }, []);
  const gui = async () => {
    setBusy(true); setLoi("");
    try { const r = await goiCong("/khach/gop-y", f); bao(r.message); setF({ ...f, tieu_de: "", noi_dung: "" }); tai(); }
    catch (e: any) { setLoi(e.message); } finally { setBusy(false); }
  };
  return (<>
    <div className="v3-notice info"><I n="lock-keyhole" /><span>Góp ý này <b>chỉ Chủ tịch HĐQT và Tổng Giám đốc đọc và trả lời</b>. Nhân viên, kể cả người được nhắc tên, không xem được và không đóng được vụ việc.</span></div>
    <div className="v3-two">
      <section className="v3-panel"><div className="v3-section-title"><h3>Gửi góp ý riêng tới lãnh đạo</h3></div>
        <label className="v3-field">Liên quan đơn (không bắt buộc)<select value={f.ma_don} onChange={(e) => setF({ ...f, ma_don: e.target.value })}>
          <option value="">Không gắn đơn</option>{don.map((d) => <option key={d.ma} value={d.ma}>{d.ma} · {d.ten}</option>)}</select></label>
        <label className="v3-field">Tiêu đề<input value={f.tieu_de} maxLength={200} onChange={(e) => setF({ ...f, tieu_de: e.target.value })} /></label>
        <label className="v3-field">Nội dung<textarea rows={5} value={f.noi_dung} maxLength={5000} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
        <fieldset className="kh-dg-hoi"><legend>Mức độ</legend>{Object.entries(x?.muc || { thuong: "Bình thường", khan: "Khẩn" }).map(([k, t]: any) =>
          <label key={k} className="v3-check"><input type="radio" name="muc" checked={f.muc === k} onChange={() => setF({ ...f, muc: k })} />{t}</label>)}</fieldset>
        <fieldset className="kh-dg-hoi"><legend>Muốn được liên hệ lại qua</legend>{Object.entries(x?.lien_he || {}).map(([k, t]: any) =>
          <label key={k} className="v3-check"><input type="radio" name="lh" checked={f.lien_he_qua === k} onChange={() => setF({ ...f, lien_he_qua: k })} />{t}</label>)}</fieldset>
        <Loi m={loi} />
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || f.tieu_de.trim().length < 3 || f.noi_dung.trim().length < 10} onClick={gui}><I n="send" /><span>{busy ? "Đang gửi…" : "Gửi góp ý"}</span></button>
      </section>
      <section className="v3-panel"><div className="v3-section-title"><h3>Góp ý đã gửi</h3></div>
        {x?.gop_y?.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Mã</th><th scope="col">Tiêu đề</th><th scope="col">Trạng thái</th></tr></thead>
          <tbody>{x.gop_y.map((g: any) => <tr key={g.id}><th scope="row">{g.ma}<small>{ngay(g.gui_luc)}</small></th><td>{g.tieu_de}{g.tra_loi && <small>Trả lời: {g.tra_loi}</small>}</td>
            <td><span className={`v3-badge ${MAU[g.trang_thai]}`}>{g.trang_thai === "moi" ? "Đã tiếp nhận" : g.trang_thai_ten}</span></td></tr>)}</tbody></table></div>
          : <p>Chưa gửi góp ý nào.</p>}
      </section>
    </div></>);
}

// ── HỖ TRỢ: ĐỔI · HỦY · HÓA ĐƠN · KHÁC ──────────────────────────────────────────────────────
export function HoTroKhach({ don, maDon }: { don: any[]; maDon?: string }) {
  const [x, setX] = useState<any>(null);
  const [f, setF] = useState({ loai: "doi", ma_don: maDon || "", noi_dung: "" });
  const [hd, setHd] = useState({ ten_don_vi: "", mst: "", dia_chi: "", email: "" });
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false); const [xong, setXong] = useState<any>(null);
  const tai = () => goiCong("/khach/ho-tro").then(setX).catch((e) => setLoi(e.message));
  useEffect(() => { tai(); }, []);
  const gui = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach/ho-tro", { ...f, hoa_don: f.loai === "hoa_don" ? hd : null });
      setXong(r); setF({ ...f, noi_dung: "" }); tai();
    } catch (e: any) { setLoi(e.message); } finally { setBusy(false); }
  };
  const canDon = f.loai !== "khac";
  const duHd = f.loai !== "hoa_don" || (hd.ten_don_vi.trim() && hd.mst.trim() && hd.dia_chi.trim());
  return (<>
    {xong && <div className="v3-notice info"><I n="check" /><span>Đã gửi yêu cầu <b>{xong.ma}</b> ({xong.loai}) tới <b>{xong.bo_phan}</b>. Người phụ trách trả lời tại đây; yêu cầu chưa được duyệt cho tới khi có trả lời.</span></div>}
    <div className="v3-two">
      <section className="v3-panel"><div className="v3-section-title"><h3>Gửi yêu cầu hỗ trợ</h3></div>
        <fieldset className="kh-dg-hoi"><legend>Loại yêu cầu</legend>{Object.entries(x?.loai || {}).map(([k, t]: any) =>
          <label key={k} className="v3-check"><input type="radio" name="loai" checked={f.loai === k} onChange={() => setF({ ...f, loai: k })} />{t}</label>)}</fieldset>
        <label className="v3-field">Đơn{canDon ? "" : " (không bắt buộc)"}<select value={f.ma_don} onChange={(e) => setF({ ...f, ma_don: e.target.value })}>
          <option value="">{canDon ? "Chọn đơn" : "Không gắn đơn"}</option>{don.map((d) => <option key={d.ma} value={d.ma}>{d.ma} · {d.ten} · {ngay(d.khoi_hanh)}</option>)}</select></label>
        {f.loai === "hoa_don" && <div className="v3-form-grid">
          <label className="v3-field">Tên đơn vị<input value={hd.ten_don_vi} onChange={(e) => setHd({ ...hd, ten_don_vi: e.target.value })} /></label>
          <label className="v3-field">Mã số thuế<input value={hd.mst} inputMode="numeric" onChange={(e) => setHd({ ...hd, mst: e.target.value })} /></label>
          <label className="v3-field">Địa chỉ<input value={hd.dia_chi} onChange={(e) => setHd({ ...hd, dia_chi: e.target.value })} /></label>
          <label className="v3-field">Email nhận hóa đơn<input type="email" value={hd.email} onChange={(e) => setHd({ ...hd, email: e.target.value })} /></label></div>}
        <label className="v3-field">{f.loai === "doi" ? "Muốn đổi gì (ngày đi, người đi…)" : f.loai === "huy" ? "Lý do hủy" : "Ghi chú"}
          <textarea rows={3} value={f.noi_dung} maxLength={3000} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
        <div className="v3-notice warn"><I n="info" /><span>Gửi yêu cầu <b>không tự hủy đơn, không tự hoàn tiền, không tự xuất hóa đơn</b>. Phí đổi / hủy tính theo hợp đồng và người phụ trách báo lại trước khi làm; bạn đồng ý thì mới thực hiện.</span></div>
        <Loi m={loi} />
        <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || (canDon && !f.ma_don) || !duHd} onClick={gui}><I n="send" /><span>{busy ? "Đang gửi…" : "Gửi yêu cầu"}</span></button>
      </section>
      <section className="v3-panel"><div className="v3-section-title"><h3>Yêu cầu của tôi</h3></div>
        {x?.yeu_cau?.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Mã</th><th scope="col">Loại · đơn</th><th scope="col">Trạng thái</th></tr></thead>
          <tbody>{x.yeu_cau.map((y: any) => <tr key={y.id}><th scope="row">{y.ma}<small>{ngay(y.gui_luc)}</small></th>
            <td>{y.loai_ten}{y.don ? ` · ${y.don}` : ""}<small>{y.bo_phan_ten}</small></td>
            <td><span className={`v3-badge ${MAU[y.trang_thai]}`}>{y.trang_thai_ten}</span>{y.tra_loi && <small>«{y.tra_loi}»</small>}</td></tr>)}</tbody></table></div>
          : <p>Chưa có yêu cầu nào.</p>}
        <p>Đổi / hủy → người Kinh doanh phụ trách đơn · Hóa đơn → Kế toán · Khác → Sale Admin.</p>
      </section>
    </div></>);
}
