"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KS-2 (Chủ tịch duyệt 28/10/2026) — ĐỐI SOÁT ĐẶT PHÒNG & HOA HỒNG OTA.
 *  Kế toán tải tệp báo cáo từ OTA rồi đọc thử (chưa ghi gì) → gửi duyệt. Chủ tịch duyệt lô mới ghi sổ;
 *  người nạp không tự duyệt. Tiền giữ USD, không quy đổi, không cộng vào doanh thu Vietourist.
 *  Đặt phòng chỉ nối về khách / đại lý khi báo cáo có đúng mã lượt (SubID) VTOS đã gắn — không đoán. */
const usd = (c?: number | null) => (c || c === 0 ? (c / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—");
const TT: Record<string, string> = { cho_duyet: "warn", da_duyet: "ok", tu_choi: "red" };
const NHAN: Record<string, [string, string]> = { moi: ["mới", "ok"], cap_nhat: ["cập nhật", "warn"], trung: ["trùng", ""] };
const thangNay = () => new Date().toISOString().slice(0, 7);

function BangDong({ ds }: { ds: any[] }) {
  return (<div className="wrap"><table>
    <thead><tr><th>Ngày đặt</th><th>Thành phố</th><th>Ngày ở</th><th>Link</th><th className="num">Giá trị (USD)</th><th className="num">Hoa hồng (USD)</th><th>Chuyến</th><th>Thanh toán</th><th>SubID</th><th>Thay đổi</th></tr></thead>
    <tbody>{ds.map((x, i) => <tr key={i}>
      <td className="mono">{x.ngay_dat}</td><td>{x.thanh_pho || "—"}</td>
      <td className="mono">{x.ngay_den || ""}{x.ngay_di ? ` → ${x.ngay_di}` : ""}</td>
      <td className="muted" style={{ maxWidth: 180, overflowWrap: "anywhere" }}>{x.link}</td>
      <td className="mono num">{usd(x.gia_tri_cent)}</td><td className="mono num">{usd(x.hoa_hong_cent)}</td>
      <td>{x.trang_thai_chuyen}</td><td>{x.trang_thai_tt}</td><td className="mono">{x.subid || "—"}</td>
      <td>{x.thay_doi && <Tag cls={NHAN[x.thay_doi]?.[1] || ""}>{NHAN[x.thay_doi]?.[0] || x.thay_doi}</Tag>}
        {x.truong_doi?.length > 0 && <div className="muted" style={{ fontSize: 12 }}>{x.truong_doi.join(", ")}</div>}</td></tr>)}</tbody></table></div>);
}

function Trang() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [ota, setOta] = useState("");
  const [ky, setKy] = useState(thangNay());
  const [tep, setTep] = useState<File | null>(null);
  const [thu, setThu] = useState<any>(null);
  const [lo, setLo] = useState<any>(null);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api<any>("/doi-soat-ota").then((r) => { setD(r); setOta((o) => o || String(r.ota?.[0]?.id || "")); }).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  const fd = (them: Record<string, string> = {}) => { const f = new FormData(); f.append("ota_id", ota); f.append("tep", tep as File); Object.entries(them).forEach(([k, v]) => f.append(k, v)); return f; };
  const docThu = async () => {
    setBusy(true); setThu(null);
    try { setThu(await api<any>("/doi-soat-ota/doc-thu", { method: "POST", body: fd() })); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const gui = async () => {
    setBusy(true);
    try { const r = await api<any>("/doi-soat-ota/lo", { method: "POST", body: fd({ ky }) }); toast(r.message); setThu(null); setTep(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const moLo = (id: number) => api<any>(`/doi-soat-ota/lo/${id}`).then((r) => { setLo(r); setLyDo(""); }).catch((e) => toast(errMsg(e), true));
  const xuLy = async (hanh_dong: string) => {
    try { const r = await api<any>(`/doi-soat-ota/lo/${lo.id}`, { method: "POST", json: { hanh_dong, ly_do: lyDo } }); toast(r.message); setLo(r.lo); load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  return (<>
    <h1>Đối soát OTA</h1>
    <p className="muted">Kế toán tải tệp báo cáo đặt phòng từ OTA (Expedia: Creator Hub → Performance → Bookings → Download) rồi nạp ở đây. Đọc thử chưa ghi gì; Chủ tịch duyệt lô mới ghi sổ. Tiền giữ nguyên USD — hoa hồng thuộc pháp nhân hợp đồng OTA, KHÔNG cộng vào doanh thu Vietourist.</p>

    {d?.nap_duoc && <div className="panel"><b>Nạp báo cáo OTA</b>
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 8 }}>
        <label>OTA<select value={ota} onChange={(e) => { setOta(e.target.value); setThu(null); }}>{d.ota.map((o: any) => <option key={o.id} value={o.id}>{o.ten}</option>)}</select></label>
        <label>Kỳ báo cáo<input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
        <label>Tệp báo cáo (CSV / Excel)<input type="file" accept=".csv,.txt,.xlsx" onChange={(e) => { setTep(e.target.files?.[0] || null); setThu(null); }} /></label>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button className="act grey" style={{ margin: 0 }} disabled={!tep || busy} onClick={docThu}>Đọc thử</button>
        <button className="act teal" style={{ margin: 0 }} disabled={!tep || !thu || busy || !!thu?.da_nap || thu?.so_dong === 0} onClick={gui}>Gửi Chủ tịch duyệt</button>
      </div>
      {thu && <div style={{ marginTop: 10, display: "grid", gap: 6 }}>
        <div><b>Kết quả đọc thử — chưa ghi gì.</b> {thu.so_dong} dòng: <Tag cls="ok">{thu.tom.moi} mới</Tag> <Tag cls="warn">{thu.tom.cap_nhat} cập nhật</Tag> <Tag cls="">{thu.tom.trung} trùng</Tag> · hoa hồng thay đổi <b className="mono">{usd(thu.tom.chenh_hoa_hong_cent)} USD</b></div>
        {thu.da_nap && <div style={{ color: "var(--red)" }}>Tệp này đã nạp ở lô {thu.da_nap.ma} ({thu.da_nap.trang_thai}) — không nạp lại.</div>}
        {thu.trung_trong_tep > 0 && <div style={{ color: "var(--orange)" }}>{thu.trung_trong_tep} nhóm dòng giống hệt nhau trong tệp (không có mã đặt phòng) — máy đánh #1, #2…; Kế toán xem lại trên trang OTA trước khi gửi.</div>}
        {thu.loi.length > 0 && <div style={{ color: "var(--red)" }}>Lỗi đọc {thu.loi.length} dòng: {thu.loi.slice(0, 5).map((l: any) => `dòng ${l.dong}: ${l.loi}`).join("; ")}</div>}
        <div className="muted">Cột đọc được: {thu.cot_doc_duoc.join(", ")}</div>
        <BangDong ds={thu.dong} />
      </div>}
    </div>}

    <div className="panel wrap"><b>Sổ hoa hồng OTA (USD)</b>
      <table><thead><tr><th>Kỳ</th><th>OTA</th><th className="num">Đặt phòng</th><th className="num">Hủy</th><th className="num">Giá trị giao dịch</th><th className="num">Hoa hồng ước tính</th><th className="num">Đã hoàn tất</th><th className="num">OTA đã trả</th><th className="num">Nối được về khách</th></tr></thead>
        <tbody>{d?.so?.length ? d.so.map((m: any) => <tr key={m.ky + m.ota}><td className="mono">{m.ky}</td><td>{m.ota}</td><td className="mono num">{m.dat_phong}</td><td className="mono num">{m.huy}</td>
          <td className="mono num">{usd(m.gia_tri_cent)}</td><td className="mono num">{usd(m.uoc_tinh_cent)}</td><td className="mono num">{usd(m.hoan_tat_cent)}</td><td className="mono num">{usd(m.da_tra_cent)}</td><td className="mono num">{m.noi_duoc}</td></tr>)
          : <tr><td colSpan={9} className="muted">Chưa có đặt phòng OTA nào được duyệt.</td></tr>}</tbody></table>
      <div className="muted">Ước tính = OTA báo; hoàn tất = khách đã ở xong; đã trả = OTA ghi đã thanh toán. Quy đổi VND và hạch toán do Kế toán quyết theo chứng từ. {d && d.chua_noi > 0 && `${d.chua_noi} đặt phòng chưa nối được về khách (báo cáo không có mã lượt) — không đoán.`}</div>
    </div>

    <div className="panel wrap"><b>Các lô đã nạp</b>
      <table><thead><tr><th>Lô</th><th>OTA</th><th>Kỳ</th><th>Tệp</th><th>Nạp</th><th className="num">Dòng</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{d?.lo?.length ? d.lo.map((x: any) => <tr key={x.id}><td className="mono">{x.ma}</td><td>{x.ota}</td><td className="mono">{x.ky}</td><td className="muted">{x.ten_tep}</td>
          <td className="muted">{x.nap_boi} · {fmtDT(x.nap_luc)}</td><td className="mono num">{x.so_dong}</td>
          <td><Tag cls={TT[x.trang_thai] || ""}>{x.trang_thai_ten}</Tag>{x.ly_do && <div className="muted">{x.ly_do}</div>}</td>
          <td><button className="act grey" style={{ margin: 0 }} onClick={() => moLo(x.id)}>Xem</button></td></tr>)
          : <tr><td colSpan={8} className="muted">Chưa nạp lô nào.</td></tr>}</tbody></table>
    </div>

    {lo && <div className="panel" style={{ display: "grid", gap: 8 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}><b>Lô {lo.ma} · {lo.ota} · {lo.ky}</b><Tag cls={TT[lo.trang_thai] || ""}>{lo.trang_thai_ten}</Tag>
        <button className="act grey" style={{ margin: "0 0 0 auto" }} onClick={() => setLo(null)}>Đóng</button></div>
      <div className="muted">Kế toán {lo.nap_boi} nạp {fmtDT(lo.nap_luc)} · tệp {lo.ten_tep}{lo.duyet_boi && ` · ${lo.trang_thai === "tu_choi" ? "từ chối" : "duyệt"} bởi ${lo.duyet_boi} ${fmtDT(lo.duyet_luc)}`}</div>
      {lo.tom && <div><Tag cls="ok">{lo.tom.moi ?? 0} mới</Tag> <Tag cls="warn">{lo.tom.cap_nhat ?? 0} cập nhật</Tag> <Tag cls="">{lo.tom.trung ?? 0} trùng</Tag> · hoa hồng thay đổi <b className="mono">{usd(lo.tom.chenh_hoa_hong_cent)} USD</b></div>}
      <BangDong ds={lo.dong || []} />
      {lo.duyet_duoc && <>
        <input value={lyDo} onChange={(e) => setLyDo(e.target.value)} placeholder="Lý do (bắt buộc khi từ chối)" />
        <div style={{ display: "flex", gap: 8 }}>
          <button className="act teal" style={{ margin: 0 }} onClick={() => xuLy("duyet")}>Duyệt &amp; ghi sổ</button>
          <button className="act grey" style={{ margin: 0 }} disabled={!lyDo.trim()} onClick={() => xuLy("tu_choi")}>Từ chối</button></div></>}
      {lo.trang_thai === "cho_duyet" && !lo.duyet_duoc && <div className="muted">Chờ Chủ tịch duyệt — người nạp không tự duyệt lô của mình.</div>}
    </div>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
