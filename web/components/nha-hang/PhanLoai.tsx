"use client";
import { useCallback, useEffect, useState } from "react";
import { api, taiTep } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** PL-1 · PHÂN LOẠI NHÀ HÀNG (Chủ tịch duyệt bản xem thử 30/10/2026).
 *  «Đặc sản địa phương»: máy tự gắn khi nguồn là TasteAtlas; đổi tay qua đề xuất → chốt (gỡ phải ghi lý do).
 *  Bậc sang trọng: máy GỢI Ý; NV Điều hành đề xuất → TP Điều hành chốt; Chủ tịch / TGĐ chốt ngay.
 *  Cổng khách chỉ hiện bậc ĐÃ CHỐT. Hạng / mức giá Michelin do Điều hành nhập (tay hoặc Excel). */
type Toast = (m: string, loi?: boolean) => void;
const BAC: [string, string][] = [["binh_dan", "Bình dân"], ["tam_trung", "Tầm trung"], ["cao_cap", "Cao cấp"], ["sang_trong", "Sang trọng"]];
const TEN_BAC: Record<string, string> = Object.fromEntries(BAC);
const HANG: [string, string][] = [["", "— chưa ghi —"], ["sao3", "3 sao"], ["sao2", "2 sao"], ["sao1", "1 sao"], ["bib", "Bib Gourmand"], ["selected", "Selected"], ["khong", "Không có"]];
const TEN_HANG: Record<string, string> = Object.fromEntries(HANG.filter(([k]) => k));
const DS_TAY: Record<string, string> = { gan: "Gắn nhãn", go: "Gỡ nhãn", may: "Về theo máy" };
const gio = (s?: string | null) => (s ? `${s.slice(11, 16)} ${s.slice(8, 10)}/${s.slice(5, 7)}` : "");
const o = { border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 8 } as const;

async function goi(path: string, json: any, toast: Toast, xong: () => void) {
  try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); xong(); }
  catch (e) { toast(errMsg(e), true); }
}

export function HoSoPhanLoai({ nid, toast, onDoi }: { nid: number; toast: Toast; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [mi, setMi] = useState({ hang: "", gia: 0 });
  const [chon, setChon] = useState("");
  const [ds, setDs] = useState<{ tay: string; ly_do: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    api<any>(`/nha-hang/${nid}/phan-loai`).then((r) => { setX(r); setMi({ hang: r.michelin_hang, gia: r.michelin_gia }); setChon(r.bac_de_xuat || r.bac || r.goi_y || ""); })
      .catch((e) => toast(errMsg(e), true));
  }, [nid, toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải phân loại…</p>;
  const lam = async (path: string, json: any) => { setBusy(true); await goi(path, json, toast, () => { setDs(null); load(); onDoi?.(); }); setBusy(false); };
  const tuChot = x.toan_quyen;
  const choBac = x.bac_de_xuat && x.duoc_chot && (x.bac_de_xuat_boi !== x.toi || tuChot);
  const choDs = x.dac_san_de_xuat && x.duoc_chot && (x.dac_san_de_xuat_boi !== x.toi || tuChot);
  return <div id="pl-ho-so" style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 760 }}>
    <section>
      <h3 style={{ margin: "4px 0 8px" }}>1. Đặc sản địa phương</h3>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <span className={`tag ${x.dac_san ? "ok" : ""}`}>{x.dac_san ? "Đang gắn" : "Không gắn"}</span>
        <span className="muted" style={{ fontSize: 13 }}>{x.dac_san_tay ? `${DS_TAY[x.dac_san_tay]} · ${x.dac_san_ly_do || "không ghi lý do"}`
          : x.la_taste ? "Máy tự gắn vì nguồn là TasteAtlas" : "Máy chỉ tự gắn khi nguồn là TasteAtlas"}</span>
        {x.duoc_de_xuat && !x.dac_san_de_xuat && !ds && <button className="act grey" onClick={() => setDs({ tay: x.dac_san ? "go" : "gan", ly_do: "" })}>{tuChot ? "Đổi nhãn…" : "Đề xuất đổi nhãn…"}</button>}</div>
      {ds && <div className="panel" style={{ marginTop: 8 }}>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{Object.entries(DS_TAY).filter(([k]) => k !== "may" || x.dac_san_tay).map(([k, t]) =>
          <button key={k} className={`act ${ds.tay === k ? "teal" : "grey"}`} onClick={() => setDs({ ...ds, tay: k })}>{t}</button>)}</div>
        <label>Lý do {ds.tay === "go" ? "(bắt buộc)" : "(không bắt buộc)"}<input value={ds.ly_do} onChange={(e) => setDs({ ...ds, ly_do: e.target.value })} placeholder="vd: nhà hàng chuyển sang món Âu" /></label>
        <button className="act teal" disabled={busy || (ds.tay === "go" && ds.ly_do.trim().length < 5)} onClick={() => lam(`/nha-hang/${nid}/phan-loai/dac-san`, ds)}>{tuChot ? "Chốt" : "Gửi đề xuất"}</button>{" "}
        <button className="act grey" onClick={() => setDs(null)}>Thôi</button></div>}
      {x.dac_san_de_xuat && <div style={{ marginTop: 8, fontSize: 13, color: "#b07a10" }}>Đang chờ TP Điều hành chốt: <b>{DS_TAY[x.dac_san_de_xuat]}</b>
        {x.dac_san_de_xuat_ly_do && ` · ${x.dac_san_de_xuat_ly_do}`} · đề xuất bởi {x.dac_san_de_xuat_boi} {gio(x.dac_san_de_xuat_luc)}
        {choDs && <span style={{ marginLeft: 8 }}><button className="act teal" disabled={busy} onClick={() => lam(`/nha-hang/${nid}/phan-loai/dac-san/chot`, { dong_y: true })}>Chốt</button>{" "}
          <button className="act grey" disabled={busy} onClick={() => lam(`/nha-hang/${nid}/phan-loai/dac-san/chot`, { dong_y: false })}>Trả lại</button></span>}</div>}
    </section>

    <section>
      <h3 style={{ margin: "4px 0 8px" }}>2. Căn cứ từ Michelin (Điều hành nhập)</h3>
      <div className="grid">
        <label>Hạng Michelin<select value={mi.hang} disabled={!x.duoc_de_xuat} onChange={(e) => setMi({ ...mi, hang: e.target.value })}>
          {HANG.map(([k, t]) => <option key={k} value={k}>{t}</option>)}</select></label>
        <label>Mức giá Michelin<select value={mi.gia} disabled={!x.duoc_de_xuat} onChange={(e) => setMi({ ...mi, gia: Number(e.target.value) })}>
          <option value={0}>— chưa ghi —</option>{[1, 2, 3, 4].map((g) => <option key={g} value={g}>{"₫".repeat(g)}</option>)}</select></label></div>
      <div className="muted" style={{ fontSize: 12 }}>Ghi đúng như trang Michelin{x.nguon_ref?.includes("http") ? <> (<a href={x.nguon_ref.split("·").map((s: string) => s.trim()).find((s: string) => s.startsWith("http"))} target="_blank" rel="noopener noreferrer">mở trang</a>)</> : ""}.
        {x.michelin_boi && ` Ghi lần cuối: ${x.michelin_boi} ${gio(x.michelin_luc)}.`} Mức chi / người từ thực đơn đang bán: {x.muc_chi ? `${x.muc_chi.toLocaleString("vi-VN")} đ` : "chưa có"}.</div>
      {x.duoc_de_xuat && (mi.hang !== x.michelin_hang || mi.gia !== x.michelin_gia) &&
        <button className="act teal" style={{ marginTop: 6 }} disabled={busy} onClick={() => lam(`/nha-hang/${nid}/phan-loai/michelin`, mi)}>Lưu hạng / mức giá</button>}
    </section>

    <section className="panel" style={{ margin: 0 }}>
      <h3 style={{ margin: "0 0 8px" }}>3. Bậc sang trọng</h3>
      <div style={{ fontSize: 14 }}>Máy gợi ý: <b>{x.goi_y ? TEN_BAC[x.goi_y] : "—"}</b> <span className="muted">· {x.goi_y_ly_do}</span></div>
      <div style={{ fontSize: 14, marginTop: 4 }}>Đã chốt: <b>{x.bac ? TEN_BAC[x.bac] : "chưa xếp"}</b>{x.bac && <span className="muted"> · {x.bac_chot_boi} {gio(x.bac_chot_luc)}</span>}</div>
      {x.duoc_de_xuat && !x.bac_de_xuat && <>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 6, margin: "10px 0" }}>{BAC.map(([k, t]) =>
          <button key={k} className={`act ${chon === k ? "teal" : "grey"}`} style={{ minHeight: 44 }} onClick={() => setChon(k)}>{t}{x.goi_y === k ? " ·  gợi ý" : ""}</button>)}</div>
        <button className="act teal" disabled={busy || !chon || chon === x.bac} onClick={() => lam(`/nha-hang/${nid}/phan-loai/bac`, { bac: chon })}>{tuChot ? "Chốt bậc này" : "Đề xuất bậc này"}</button>
        <span className="muted" style={{ fontSize: 13, marginLeft: 8 }}>NV Điều hành đề xuất → TP Điều hành chốt. Chủ tịch / TGĐ chốt ngay.</span></>}
      {x.bac_de_xuat && <div style={{ marginTop: 10, fontSize: 13, color: "#b07a10" }}>Đang chờ TP Điều hành chốt: <b>{TEN_BAC[x.bac_de_xuat]}</b> · đề xuất bởi {x.bac_de_xuat_boi} {gio(x.bac_de_xuat_luc)}
        {choBac ? <span style={{ marginLeft: 8 }}><button className="act teal" disabled={busy} onClick={() => lam(`/nha-hang/${nid}/phan-loai/bac/chot`, { dong_y: true })}>Chốt</button>{" "}
          <button className="act grey" disabled={busy} onClick={() => lam(`/nha-hang/${nid}/phan-loai/bac/chot`, { dong_y: false })}>Trả lại</button></span>
          : x.duoc_chot && <span className="muted"> · người đề xuất không tự chốt</span>}</div>}
    </section>
    <QuyTac />
  </div>;
}

function QuyTac() {
  return <section><b style={{ fontSize: 14 }}>Quy tắc gợi ý của máy</b>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, fontSize: 13, marginTop: 6 }}>
      <div style={o}><b>Bình dân</b><br />₫ · hoặc dưới 250k / người</div>
      <div style={o}><b>Tầm trung</b><br />₫₫ · hoặc 250–600k</div>
      <div style={o}><b>Cao cấp</b><br />₫₫₫ · hoặc 600k–1,5tr · hoặc có sao mà chưa ghi giá</div>
      <div style={o}><b>Sang trọng</b><br />₫₫₫₫ · hoặc trên 1,5tr / người</div></div>
    <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>Có thực đơn đang bán kèm giá thì tính theo mức chi / người (trung vị giá người lớn); chưa có thì theo ký hiệu Michelin. Không có cả hai: không gợi ý, Điều hành chọn tay.</div></section>;
}

const LOC: [string, string][] = [["", "Tất cả"], ["cho", "Chờ chốt"], ["chua", "Chưa xếp"], ["ds", "Đặc sản địa phương"], ["mi", "Michelin chưa ghi hạng"]];

export function BangPhanLoai({ toast, onMo }: { toast: Toast; onMo: (nid: number, tab: string) => void }) {
  const [x, setX] = useState<any>(null);
  const [loc, setLoc] = useState("");
  const [tim, setTim] = useState("");
  const [tep, setTep] = useState<File | null>(null);
  const [thu, setThu] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/nha-hang/phan-loai").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải phân loại…</p>;
  const nhap = async (ghi: boolean) => {
    if (!tep) return;
    setBusy(true);
    try { const fd = new FormData(); fd.append("tep", tep); fd.append("thu", ghi ? "false" : "true");
      const r = await api<any>("/nha-hang/phan-loai/nhap-michelin", { method: "POST", body: fd });
      setThu(r); if (ghi) { toast(`Đã ghi ${r.doi.length} nhà hàng`); setTep(null); load(); } }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const k = tim.trim().toLowerCase();
  const dong = x.dong.filter((d: any) => (!k || d.ten.toLowerCase().includes(k) || (d.tinh_thanh || "").toLowerCase().includes(k)) &&
    (loc === "" || (loc === "cho" && (d.bac_de_xuat || d.dac_san_de_xuat)) || (loc === "chua" && !d.bac) || (loc === "ds" && d.dac_san) || (loc === "mi" && d.la_michelin && !d.michelin_hang)));
  const the = (t: string, v: any, c?: string) => <div style={{ ...o, display: "flex", flexDirection: "column" }}><span className="muted" style={{ fontSize: 12 }}>{t}</span><b style={{ fontSize: 22, color: c }}>{v}</b></div>;
  return <section className="panel" id="pl-bang">
    <h2 style={{ margin: 0 }}>Phân loại nhà hàng</h2>
    <div className="muted">«Đặc sản địa phương» và 4 bậc sang trọng. Cổng khách chỉ hiện bậc đã chốt; nhà hàng chưa chốt vẫn hiện, không có nhãn mức.</div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 8, margin: "12px 0" }}>
      {the("Đặc sản địa phương", x.dem.dac_san)}{the("Đã chốt bậc", x.dem.da_chot)}{the("Chờ TP ĐH chốt", x.dem.cho_chot, "#b07a10")}
      {the("Chưa xếp bậc", x.dem.chua_xep)}{the("Michelin chưa ghi hạng", `${x.dem.michelin_chua_ghi} / ${x.dem.michelin}`)}</div>

    {x.duoc_de_xuat && <div className="panel" style={{ margin: "0 0 12px" }}>
      <b>Nhập hạng & mức giá Michelin bằng Excel</b>
      <div className="muted" style={{ fontSize: 13 }}>Tải tệp mẫu ({x.dem.michelin} nhà hàng Michelin: mã, tên, đường dẫn trang Michelin). Điền 2 cột «Hạng Michelin» và «Mức giá Michelin» đúng như trang Michelin rồi tải lên. Ô trống giữ nguyên. Máy đọc thử trước, chỉ ghi khi bấm «Ghi».</div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <button className="act grey" onClick={() => taiTep("/nha-hang/phan-loai/mau-michelin.xlsx", "michelin_hang_gia.xlsx").catch((e) => toast(errMsg(e), true))}>Tải tệp mẫu</button>
        <input type="file" accept=".xlsx,.xls,.csv" aria-label="Tệp Michelin đã điền" onChange={(e) => { setTep(e.target.files?.[0] || null); setThu(null); }} />
        <button className="act teal" disabled={!tep || busy} onClick={() => nhap(false)}>Đọc thử</button></div>
      {thu && <div style={{ marginTop: 8, fontSize: 13 }}>
        <div>{thu.da_ghi ? "Đã ghi" : "Sẽ đổi"} <b>{thu.doi.length}</b> nhà hàng · giữ nguyên {thu.giu_nguyen} · lỗi {thu.loi.length}</div>
        {thu.doi.slice(0, 15).map((d: any) => <div key={d.id} className="muted">{d.ma} · {d.ten}: {d.hang_cu || "—"} {"₫".repeat(d.gia_cu) || ""} → <b>{d.hang || "—"} {"₫".repeat(d.gia)}</b></div>)}
        {thu.doi.length > 15 && <div className="muted">… và {thu.doi.length - 15} nhà hàng nữa</div>}
        {thu.loi.map((l: any, i: number) => <div key={i} style={{ color: "var(--vtos-danger)" }}>Dòng {l.dong} · {l.ma}: {l.loi}</div>)}
        {!thu.da_ghi && thu.doi.length > 0 && <button className="act teal" style={{ marginTop: 6 }} disabled={busy} onClick={() => nhap(true)}>Ghi {thu.doi.length} nhà hàng</button>}</div>}
    </div>}

    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", margin: "8px 0" }}>{LOC.map(([v, t]) =>
      <button key={v} className={`act ${loc === v ? "teal" : "grey"}`} onClick={() => setLoc(v)}>{t}</button>)}
      <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm tên, thành phố" aria-label="Tìm nhà hàng" style={{ maxWidth: 220 }} /></div>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Nhà hàng</th><th>Nhãn</th><th>Michelin</th><th>Máy gợi ý</th><th>Bậc đã chốt</th><th></th></tr></thead>
      <tbody>{dong.slice(0, 200).map((d: any) => <tr key={d.id} className="pl-dong">
        <td><b>{d.ten}</b><div className="muted">{d.tinh_thanh} · {d.nguon || "—"}</div></td>
        <td>{d.dac_san ? <span className="tag ok">Đặc sản</span> : "—"}{d.dac_san_de_xuat && <div style={{ fontSize: 12, color: "#b07a10" }}>chờ chốt: {DS_TAY[d.dac_san_de_xuat]}</div>}</td>
        <td>{d.michelin_hang ? TEN_HANG[d.michelin_hang] : d.la_michelin ? <span className="muted">chưa ghi</span> : "—"}{d.michelin_gia ? ` · ${"₫".repeat(d.michelin_gia)}` : ""}</td>
        <td>{d.goi_y ? TEN_BAC[d.goi_y] : <span className="muted">Chưa đủ căn cứ</span>}</td>
        <td>{d.bac_de_xuat ? <span style={{ color: "#b07a10" }}>Chờ chốt: {TEN_BAC[d.bac_de_xuat]}</span> : d.bac ? <span style={{ color: "#1f7a50" }}>{TEN_BAC[d.bac]} ✓</span> : <span className="muted">Chưa xếp</span>}</td>
        <td><button className="act grey" onClick={() => onMo(d.id, "pl")}>Mở</button></td></tr>)}
        {!dong.length && <tr><td colSpan={6} className="muted">Không có nhà hàng khớp bộ lọc.</td></tr>}</tbody></table></div>
    {dong.length > 200 && <p className="muted">Hiện 200 / {dong.length} dòng — lọc hoặc tìm để thu hẹp.</p>}
    <p className="muted" style={{ fontSize: 12 }}>Mọi lần gắn / gỡ nhãn, ghi hạng Michelin, đề xuất và chốt bậc đều ghi nhật ký. Gỡ nhãn «Đặc sản» phải ghi lý do.</p>
  </section>;
}
