"use client";
import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";
import BonBuocDeXuatChi from "./BonBuocDeXuatChi";

/** Đội xe v3.3 · thanh con «Đề xuất chi» trên màn /xe — nội dung đổi TẠI CHỖ (Chủ tịch duyệt 10/11/2026).
 *
 *  Một nguồn cho cả nút tạo mới lẫn danh sách theo dõi (tài liệu v3.3 mục 1): danh sách đọc
 *  `GET /fleet/de-nghi-chi` — chính các đề nghị chi 05-TT loại đội xe — và nút «Lập đề xuất chi» mở
 *  đúng màn bốn bước đang có, không dựng biểu mẫu thứ hai. */
export default function DeXuatChiTaiCho({ vai, toast, moSan = false }: {
  vai: string; toast: (s: string, loi?: boolean) => void; moSan?: boolean;
}) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [nguong, setNguong] = useState<number | null>(null);
  const [mo, setMo] = useState(moSan);
  /** Hồ sơ bị «Trả bổ sung» đang sửa — gửi lại qua cửa chung của 05-TT, cùng mã cũ. */
  const [sua, setSua] = useState<any>(null);
  const guiLai = async () => {
    try {
      const r = await api<any>(`/fleet/de-nghi-chi/${sua.id}/gui-lai`, { method: "POST", json: {
        so_tien: Number(sua.so_tien), noi_dung: sua.noi_dung, nguoi_thu_huong: sua.ben_nhan,
        ma_so_thue: sua.ma_so_thue, can_cu: sua.can_cu } });
      toast(r.message); setSua(null); doc();
    } catch (e) { toast(errMsg(e), true); }
  };
  const lap = vai === "gd_doi_xe" || vai === "cntt";
  /* VH-23 · bản 2 đợt 1 (Chủ tịch duyệt 12/11/2026): tab theo trạng thái, «Việc của tôi» do máy chủ trả
     (`viec`), ngăn chi tiết dưới dòng, ký / trả / từ chối / đã chi ngay tại đây qua `/fleet/de-nghi-chi/{id}/buoc`. */
  const [tab, setTab] = useState("viec");
  const [moCT, setMoCT] = useState<number | null>(null);
  const [httt, setHttt] = useState<Record<string, string>>({});
  const [chi, setChi] = useState<any>(null);       // phiếu đang ghi «Đã chi»
  const [dang, setDang] = useState(false);
  const buoc = async (x: any, action: string, them: any = {}) => {
    let reason = "";
    if (action === "reject" || action === "tra_bo_sung") {
      reason = window.prompt(action === "reject" ? `Lý do từ chối ${x.code} (bắt buộc):`
        : `Trả ${x.code} về người lập — cần bổ sung gì? (bắt buộc)`) || "";
      if (!reason.trim()) return;
    }
    if (action === "approve" && !window.confirm(`Ký lệnh chi ${x.code} — ${vnd(x.so_tien)} đ cho ${x.ben_nhan}?`)) return;
    setDang(true);
    try {
      const r = await api<any>(`/fleet/de-nghi-chi/${x.id}/buoc`, { method: "POST", json: { action, reason, ...them } });
      toast(r.message); setChi(null); doc();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const lamViec = (x: any, action: string) => {
    if (action === "gui_lai") { setSua({ ...x }); return; }
    if (action === "pay") { setMoCT(x.id); setChi({ x, hinh_thuc_tt: "", so_tien: String(x.con_phai_chi ?? x.so_tien) }); return; }
    buoc(x, action);
  };

  const doc = useCallback(async () => {
    try { const d = await api<any>("/fleet/de-nghi-chi"); setDs(d.de_nghi); setHttt(d.hinh_thuc_tt || {}); }
    catch (e) { setDs([]); toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { doc(); }, [doc]);
  useEffect(() => { setMo(moSan); }, [moSan]);
  useEffect(() => {
    if (!mo) return;
    api<any[]>("/fleet/xe?kem_kiem_tra=true").then(setXe).catch(() => setXe([]));
    api<any>("/fleet/danh-muc-dot3").then((d) => setNguong(d?.nguong_chung_tu ?? null)).catch(() => setNguong(null));
  }, [mo]);

  const vnd = (n: number) => Math.round(n || 0).toLocaleString("vi-VN");
  const mau = (tt: string) => tt === "da_chi" ? "ok" : tt === "tu_choi" || tt === "tra_bo_sung" ? "red" : "warn";

  return <>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
      <h2 style={{ margin: 0 }}>Đề xuất chi của đội xe</h2>
      {lap && !mo && <button className="act teal" style={{ margin: 0 }} onClick={() => setMo(true)}>+ Lập đề xuất chi</button>}
    </div>
    {mo && <BonBuocDeXuatChi xe={xe} vai={vai} nguongChungTu={nguong} toast={toast}
      onXong={doc} onDong={() => setMo(false)} />}
    {sua && <div className="panel" style={{ border: "1px solid #b42318", margin: "10px 0" }}>
      <strong>Bổ sung & gửi lại – {sua.code}</strong>
      <p className="muted" style={{ margin: "4px 0 8px" }}>Lý do trả: {sua.ly_do_tu_choi || "—"}. Gửi lại thì lên lại Chủ tịch duyệt; chữ ký cũ không còn.</p>
      {[["noi_dung", "Nội dung"], ["ben_nhan", "Bên nhận"], ["ma_so_thue", "Mã số thuế"], ["can_cu", "Căn cứ"], ["so_tien", "Số tiền (đ)"]].map(([k, l]) =>
        <label key={k} style={{ display: "block", marginTop: 6 }}>{l}
          <input type={k === "so_tien" ? "number" : "text"} value={sua[k] ?? ""} onChange={(e) => setSua({ ...sua, [k]: e.target.value })} /></label>)}
      <p style={{ marginTop: 10 }}><button className="act teal" onClick={guiLai}>Gửi lại</button>
        <button className="act grey" style={{ marginLeft: 8 }} onClick={() => setSua(null)}>Thôi</button></p>
    </div>}
    {ds === null ? <p className="muted">Đang đọc danh sách…</p>
      : ds.length === 0 ? <p className="muted">Chưa có đề nghị chi nào của đội xe. Đây là số thật, không phải thiếu nguồn.</p>
      : <>
      <div className="dxc-tab" role="tablist">{TAB.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k}
        className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l} <span>{ds.filter((x) => hop(x, k)).length}</span></button>)}</div>
      <div className="dxc-bang"><table>
        <thead><tr><th>Mã</th><th>Xe</th><th>Bên nhận · nội dung</th><th style={{ textAlign: "right" }}>Số tiền</th>
          <th>Kiểm</th><th>Đang ở</th><th className="dxc-viec">Việc của anh</th></tr></thead>
        <tbody>{ds.filter((x) => hop(x, tab)).map((x) => <Fragment key={x.id}><tr className={moCT === x.id ? "mo" : ""}>
          <td><b>{x.code}</b></td>
          <td>{x.bien_so || (x.pham_vi === "doi" ? "Toàn đội" : "—")}</td>
          {/* VH-26 (Chủ tịch 12/11/2026): mỗi đề xuất MỘT dòng ngang — bên nhận + nội dung gọn 1 dòng, «xem thêm» mở chi tiết. */}
          <td className="dxc-dong"><div className="dxc-nd" title={`${x.ben_nhan} — ${x.noi_dung}`}><b>{x.ben_nhan}</b>
            <span className="muted"> — {x.noi_dung}</span></div>
            <button type="button" className="dxc-them" aria-expanded={moCT === x.id}
              onClick={() => { setMoCT(moCT === x.id ? null : x.id); setChi(null); }}>{moCT === x.id ? "thu gọn" : "xem thêm"}</button></td>
          <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}><b>{vnd(x.so_tien)}</b></td>
          <td>{(() => { const d = (x.kiem || []).filter((k: any) => k.muc === "do").length, v = (x.kiem || []).filter((k: any) => k.muc === "vang").length;
            return d ? <span className="tag red">{d} chặn</span> : v ? <span className="tag warn">{v} lưu ý</span> : <span className="tag ok">đủ</span>; })()}</td>
          <td><span className={`tag ${mau(x.trang_thai)}`} title={x.ly_do_tu_choi || undefined}>{x.buoc}</span></td>
          <td className="dxc-viec"><div className="dxc-nut">
            {(x.viec || []).map(([a, l]: [string, string]) => <button key={a} type="button" disabled={dang}
              className={"act " + (a === "approve" || a === "pay" ? "teal" : a === "gui_lai" ? "teal" : "grey")}
              onClick={() => lamViec(x, a)}>{l}</button>)}
          </div></td></tr>
          {moCT === x.id && <tr className="dxc-ct"><td colSpan={7}>
            <div className="dxc-ngan">
              <dl>
                <div className="dai"><dt>Nội dung</dt><dd>{x.noi_dung}</dd></div>
                <div><dt>Loại · nhóm</dt><dd>{[x.loai, x.nhom].filter(Boolean).join(" · ") || "—"}</dd></div>
                <div><dt>Bên nhận</dt><dd>{x.ben_nhan}{x.ma_so_thue ? ` · MST ${x.ma_so_thue}` : x.can_mst ? " · chưa MST" : ""}</dd></div>
                <div><dt>Ngày lập</dt><dd>{x.ngay || "—"}</dd></div>
                {x.ly_do_tu_choi && <div className="dai"><dt>Lý do trả / từ chối</dt><dd>{x.ly_do_tu_choi}</dd></div>}
                <div><dt>Căn cứ số tiền</dt><dd>{x.can_cu || "—"}</dd></div>
                <div><dt>Số hoá đơn</dt><dd>{x.chung_tu || "—"}</dd></div>
                <div className="dai"><dt>Khoản gốc</dt><dd>{x.khoan_goc ? `${x.khoan_goc.ten} · ${vnd(x.khoan_goc.so_tien)} đ` : "Không gắn"}</dd></div>
                {x.ghi_chu_kiem_tra && <div className="dai"><dt>Ghi chú cho người kiểm</dt><dd>{x.ghi_chu_kiem_tra}</dd></div>}
                {x.hen_bo_sung && <div className="dai"><dt>Hẹn bổ sung</dt><dd>{x.hen_bo_sung}</dd></div>}
                <div className="dai"><dt>Tuyến ký</dt><dd className="dxc-tuyen">{(x.tuyen || []).map((t: any) =>
                  <span key={t.buoc} className={t.luc ? "xong" : ""}>{t.buoc}{t.nguoi ? ` · ${t.nguoi}` : ""}{t.luc ? ` · ${String(t.luc).slice(11, 16)} ${String(t.luc).slice(8, 10)}/${String(t.luc).slice(5, 7)}` : ""}</span>)}
                  {x.trang_thai !== "da_chi" && x.trang_thai !== "tu_choi" && <span className="nay">Đang: {x.buoc}</span>}</dd></div>
                {/* VH-34 · lịch sử phiên bản: bản 1 → trả bổ sung (ai, lý do) → bản 2 gửi lại (ô nào đổi, cũ → mới). */}
                {(x.phien_ban || []).length > 1 && <div className="dai"><dt>Lịch sử phiên bản</dt><dd><ol className="dxc-pb">
                  {x.phien_ban.map((p: any, i: number) => <li key={i} className={p.loai}>
                    <b>{p.loai === "lap" ? `Bản ${p.ban} · lập` : p.loai === "tra" ? "Trả bổ sung" : `Bản ${p.ban} · gửi lại`}</b>
                    <span className="muted"> · {p.nguoi}{p.luc ? ` · ${String(p.luc).slice(11, 16)} ${String(p.luc).slice(8, 10)}/${String(p.luc).slice(5, 7)}` : ""}</span>
                    {p.ly_do && <div className="muted">«{p.ly_do}»</div>}
                    {(p.doi || []).map((o: any, j: number) => <div key={j}>{o.o}: <s>{typeof o.cu === "number" ? vnd(o.cu) : String(o.cu ?? "—")}</s>
                      {" → "}<b>{typeof o.moi === "number" ? vnd(o.moi) : String(o.moi ?? "—")}</b></div>)}
                  </li>)}</ol></dd></div>}
                {x.da_chi_tien > 0 && <div><dt>Đã chi</dt><dd>{vnd(x.da_chi_tien)} đ · còn {vnd(x.con_phai_chi)} đ</dd></div>}
              </dl>
              <div className="dxc-kiem"><b>Máy đã kiểm</b><ul>{(x.kiem || []).map((k: any, i: number) =>
                <li key={i}><span className={"dau " + k.muc}>{k.muc === "ok" ? "✓" : k.muc === "do" ? "!" : "i"}</span>{k.chu}</li>)}</ul></div>
            </div>
            {chi && chi.x.id === x.id && <div className="dxc-chi">
              <b>Ghi nhận đã chi – {x.code}</b>
              {!x.co_unc && <p className="muted" style={{ margin: "4px 0" }}>Tải UNC / phiếu chi ở ô dưới trước — máy chủ chặn «Đã chi» khi chưa có UNC.</p>}
              <label>Hình thức thanh toán<select value={chi.hinh_thuc_tt} onChange={(e) => setChi({ ...chi, hinh_thuc_tt: e.target.value })}>
                <option value="">— chọn —</option>{Object.entries(httt).filter(([k]) => k && k !== "chua_tt").map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
              <label>Số tiền chi lần này (đ)<input type="number" value={chi.so_tien} onChange={(e) => setChi({ ...chi, so_tien: e.target.value })} /></label>
              <label>Mã giao dịch / số chứng từ<input value={chi.ma || ""} onChange={(e) => setChi({ ...chi, ma: e.target.value })} /></label>
              <div><button type="button" className="act teal" disabled={dang || !chi.hinh_thuc_tt}
                onClick={() => buoc(x, "pay", { hinh_thuc_tt: chi.hinh_thuc_tt, so_tien: chi.so_tien === "" ? null : Number(chi.so_tien), reason: chi.ma || "" })}>Ghi nhận đã chi</button>
                <button type="button" className="act grey" onClick={() => setChi(null)}>Thôi</button></div>
              <DinhKem doiTuong="de_nghi_chi" doiTuongId={x.code} loai="unc" tieuDe={`UNC / phiếu chi của ${x.code}`} onDoi={doc} />
            </div>}
            <DinhKem key={`dxc-${x.code}`} doiTuong="de_xuat_chi_xe" doiTuongId={x.code} tieuDe={`Chứng từ của ${x.code}`}
              chiXem={!(lap && ["cho_duyet", "tra_bo_sung"].includes(x.trang_thai))}
              goi="Hoá đơn, báo giá, phiếu sửa chữa, ảnh hiện trạng — người ký nhìn đúng giấy mình đang ký." onDoi={doc} />
          </td></tr>}</Fragment>)}</tbody></table></div>
      {!ds.some((x) => hop(x, tab)) && <p className="muted">{tab === "viec" ? "Không có phiếu nào đang chờ anh/chị." : "Không có phiếu ở mục này."}</p>}
      <style>{DXC_CSS}</style></>}
  </>;
}

const TAB: [string, string][] = [["viec", "Việc của tôi"], ["dang", "Đang xử lý"], ["tra_bo_sung", "Trả bổ sung"],
  ["da_chi", "Đã chi"], ["tu_choi", "Từ chối"], ["", "Tất cả"]];
function hop(x: any, tab: string): boolean {
  if (tab === "viec") return (x.viec || []).length > 0;
  if (tab === "dang") return ["cho_tp", "cho_kt", "cho_duyet", "cho_chi"].includes(x.trang_thai);
  return !tab || x.trang_thai === tab;
}
const DXC_CSS = `
.dxc-tab{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.dxc-tab button{font:inherit;font-size:calc(13/14*1rem);border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:999px;padding:4px 12px;cursor:pointer;margin:0}
.dxc-tab button span{font-weight:700;margin-left:4px;opacity:.75}
.dxc-tab button.on{background:var(--navy);border-color:var(--navy);color:#fff}
.dxc-bang{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.dxc-bang table{min-width:900px;width:100%}
.dxc-viec{position:sticky;right:0;background:var(--panel);box-shadow:-8px 0 10px -8px rgba(18,48,84,.25);min-width:170px;z-index:1}
.dxc-nut{display:flex;flex-wrap:nowrap;gap:6px}.dxc-nut .act{margin:0;white-space:nowrap}
.dxc-bang td,.dxc-bang th{white-space:nowrap;vertical-align:middle}
.dxc-bang td.dxc-dong{white-space:normal;width:100%;max-width:0}
td.dxc-dong>.dxc-nd{display:inline-block;max-width:calc(100% - 78px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle}
.dxc-them{font:inherit;font-size:calc(13/14*1rem);background:none;border:0;padding:0 0 0 8px;margin:0;color:var(--navy);text-decoration:underline;cursor:pointer;vertical-align:middle;white-space:nowrap}
tr.mo>td{background:var(--panel2)}
tr.dxc-ct>td{background:var(--panel2);padding:14px 16px;white-space:normal}
.dxc-ngan{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:16px;margin-bottom:10px}
@media (max-width:760px){.dxc-ngan{grid-template-columns:1fr}}
.dxc-ngan dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px 18px;margin:0}
.dxc-ngan dl>div{min-width:0}.dxc-ngan .dai{grid-column:1/-1}
.dxc-ngan dt{font-size:calc(11/14*1rem);font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2)}
.dxc-ngan dd{margin:1px 0 0;white-space:pre-wrap}
.dxc-tuyen{display:flex;flex-wrap:wrap;gap:6px}
.dxc-pb{list-style:none;margin:2px 0 0;padding:0 0 0 14px;border-left:2px solid var(--line);display:flex;flex-direction:column;gap:6px}
.dxc-pb li{position:relative}
.dxc-pb li::before{content:"";position:absolute;left:-20px;top:5px;width:10px;height:10px;border-radius:50%;background:var(--navy)}
.dxc-pb li.tra::before{background:var(--red)}.dxc-pb li.gui_lai::before{background:var(--teal)}
.dxc-pb s{color:var(--red)}
.dxc-tuyen span{font-size:calc(12/14*1rem);border:1px solid var(--line);border-radius:999px;padding:1px 9px;background:var(--panel)}
.dxc-tuyen span.xong{background:#2f8a57;border-color:#2f8a57;color:#fff}
.dxc-tuyen span.nay{background:var(--navy);border-color:var(--navy);color:#fff}
.dxc-kiem ul{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:6px}
.dxc-kiem li{display:flex;gap:8px;align-items:flex-start;font-size:calc(13/14*1rem)}
.dxc-kiem .dau{flex:none;width:18px;height:18px;border-radius:50%;display:grid;place-items:center;font-size:11px;font-weight:700;color:#fff;background:#c27a00}
.dxc-kiem .dau.ok{background:#2f8a57}.dxc-kiem .dau.do{background:#b72f45}
.dxc-chi{border:1px solid #0f6f5c;border-radius:8px;padding:12px;margin:0 0 10px;display:flex;flex-direction:column;gap:8px;max-width:520px;background:var(--panel)}
`;
