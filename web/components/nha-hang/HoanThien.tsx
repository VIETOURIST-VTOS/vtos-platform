"use client";
import { useCallback, useEffect, useState } from "react";
import { api, taiTep } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** AT-2c · BIÊN TẬP VÀ MỨC HOÀN THIỆN (Chủ tịch duyệt bản xem thử 29/10/2026).
 *  Máy chấm từ dữ liệu ĐÃ DUYỆT: bìa 20, album 20, món 15, thực đơn 15, giới thiệu 15, liên hệ 15; ≥ 80% = đủ.
 *  Chỉ Chủ tịch giao việc; người nhận là NV Điều hành / NV Marketing. Cột «Việc của tôi» do máy xếp, không kéo thả. */

type Toast = (m: string, loi?: boolean) => void;
const MA = ["bia", "album", "mon", "thuc_don", "gioi_thieu", "lien_he"] as const;
const COT_NGAN: Record<string, string> = { bia: "BÌA", album: "ALBUM", mon: "MÓN", thuc_don: "THỰC ĐƠN", gioi_thieu: "GIỚI THIỆU", lien_he: "LIÊN HỆ" };
const mau = (md: string) => (md === "du" ? "#1f7a50" : md === "dang" ? "#b07a10" : "#b33a3a");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "—");

function Thanh({ diem, md }: { diem: number; md: string }) {
  return <span style={{ display: "flex", flexDirection: "column", gap: 3, minWidth: 64 }}>
    <b style={{ color: mau(md) }}>{diem}%</b>
    <span style={{ height: 6, background: "rgba(127,140,153,.25)", borderRadius: 3 }}>
      <span style={{ display: "block", width: `${diem}%`, height: 6, background: mau(md), borderRadius: 3 }} /></span></span>;
}

function O({ m }: { m: any }) {
  const sl = m.ma === "album" || m.ma === "mon" ? (m.chi_tiet.match(/^(\d+)/)?.[1] ?? "") : "";
  if (m.dat) return <span title={m.chi_tiet} style={{ color: "#1f7a50" }}>✓{sl ? ` ${sl}` : ""}</span>;
  if (m.diem > 0) return <span title={m.chi_tiet} style={{ color: "#b07a10" }}>½{sl ? ` ${sl}` : ""}</span>;
  return <span title={m.chi_tiet} style={{ color: "#b33a3a" }}>✗</span>;
}

/** Tab «Hoàn thiện» — bảng mọi nhà hàng, lọc, giao việc (Chủ tịch), xuất Excel. */
export function BangHoanThien({ toast, onMo }: { toast: Toast; onMo: (nid: number, tab: string) => void }) {
  const [x, setX] = useState<any>(null);
  const [loc, setLoc] = useState(""); const [tp, setTp] = useState(""); const [ng, setNg] = useState("");
  const [chon, setChon] = useState<number[]>([]);
  const [giao, setGiao] = useState({ nguoi: "", han: "" });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/nha-hang/hoan-thien").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang chấm mức hoàn thiện…</p>;
  const ds = x.nha_hang.filter((o: any) =>
    (!loc || o.muc.some((m: any) => m.ma === loc && !m.dat)) && (!tp || o.tinh_thanh === tp) &&
    (!ng || (ng === "-" ? !o.nguoi : o.nguoi === ng)));
  const tps = Array.from(new Set(x.nha_hang.map((o: any) => o.tinh_thanh).filter(Boolean))) as string[];
  const ngs = Array.from(new Set(x.nha_hang.map((o: any) => o.nguoi).filter(Boolean))) as string[];
  const giaoNgay = async (bo = false) => {
    setBusy(true);
    try {
      const r = await api<any>("/nha-hang/bien-tap/giao", { method: "POST", json: { ids: chon, nguoi: bo ? "" : giao.nguoi, han: bo ? null : giao.han || null } });
      toast(r.message); setChon([]); load();
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const the = (t: string, v: any, c?: string) => <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 4, margin: 0 }}>
    <span className="muted" style={{ fontSize: 13 }}>{t}</span><b style={{ fontSize: 26, color: c }}>{v}</b></div>;
  return <section className="panel" id="at-ht">
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
      <div><h2 style={{ margin: 0 }}>Mức hoàn thiện hồ sơ</h2>
        <div className="muted">Máy chấm từ dữ liệu đã DUYỆT — không ai chấm tay. {x.duoc_giao ? "Chọn nhà hàng để giao người biên tập." : "Chủ tịch giao người biên tập."}</div></div>
      <button className="act grey" onClick={() => taiTep("/nha-hang/hoan-thien.xlsx", "nha_hang_con_thieu.xlsx").catch((e) => toast(errMsg(e), true))}>Xuất Excel danh sách thiếu</button></div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 10, margin: "12px 0" }}>
      {the(`Đủ để giới thiệu đẹp (≥ ${x.nguong.du}%)`, x.dem.du, "#1f7a50")}
      {the(`Đang hoàn thiện (${x.nguong.thieu}–${x.nguong.du - 1}%)`, x.dem.dang, "#b07a10")}
      {the(`Thiếu nhiều (< ${x.nguong.thieu}%)`, x.dem.thieu, "#b33a3a")}
      {the("Chưa giao người biên tập", x.chua_giao)}</div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 10 }}>
      <button className={`act ${!loc ? "teal" : "grey"}`} onClick={() => setLoc("")}>Tất cả {x.nha_hang.length}</button>
      {MA.map((k) => <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>Thiếu {COT_NGAN[k].toLowerCase()}</button>)}
      <span style={{ flex: 1 }} />
      <select style={{ width: "auto" }} value={tp} onChange={(e) => setTp(e.target.value)} aria-label="Thành phố"><option value="">Thành phố: mọi nơi</option>{tps.map((t) => <option key={t}>{t}</option>)}</select>
      <select style={{ width: "auto" }} value={ng} onChange={(e) => setNg(e.target.value)} aria-label="Người biên tập"><option value="">Người biên tập: tất cả</option><option value="-">— chưa giao —</option>{ngs.map((t) => <option key={t}>{t}</option>)}</select></div>
    {x.duoc_giao && chon.length > 0 && <div className="panel" style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
      <b>Giao {chon.length} nhà hàng đã chọn cho</b>
      <select style={{ width: "auto" }} value={giao.nguoi} onChange={(e) => setGiao({ ...giao, nguoi: e.target.value })} aria-label="Người nhận">
        <option value="">— chọn người —</option>{x.nguoi_nhan.map((p: any) => <option key={p.username} value={p.username}>{p.ten || p.username} · {p.role === "nv_dh" ? "NV Điều hành" : "NV Marketing"}</option>)}</select>
      <label style={{ display: "flex", gap: 6, alignItems: "center" }}>Hạn<input type="date" style={{ width: "auto" }} value={giao.han} onChange={(e) => setGiao({ ...giao, han: e.target.value })} /></label>
      <button className="act teal" disabled={busy || !giao.nguoi} onClick={() => giaoNgay()}>Giao</button>
      <button className="act grey" disabled={busy} onClick={() => giaoNgay(true)}>Bỏ giao</button>
      <button className="act grey" onClick={() => setChon([])}>Bỏ chọn</button></div>}
    <div style={{ overflowX: "auto" }}><table><thead><tr>
      {x.duoc_giao && <th><input type="checkbox" aria-label="Chọn tất cả" checked={ds.length > 0 && ds.every((o: any) => chon.includes(o.id))}
        onChange={(e) => setChon(e.target.checked ? ds.map((o: any) => o.id) : [])} /></th>}
      <th>Nhà hàng</th><th>Thành phố</th><th>Điểm</th>{MA.map((k) => <th key={k}>{COT_NGAN[k]}</th>)}<th>Người biên tập</th><th>Hạn</th></tr></thead>
      <tbody>{ds.map((o: any) => <tr key={o.id} className="at-ht-dong">
        {x.duoc_giao && <td><input type="checkbox" aria-label={`Chọn ${o.ten}`} checked={chon.includes(o.id)}
          onChange={(e) => setChon(e.target.checked ? [...chon, o.id] : chon.filter((i) => i !== o.id))} /></td>}
        <td><a href="#" onClick={(e) => { e.preventDefault(); const m = o.muc.find((v: any) => !v.dat); onMo(o.id, m ? TAB[m.ma] : "album"); }}><b>{o.ten}</b></a>
          {o.cho_duyet > 0 && <div className="muted">{o.cho_duyet} mục chờ duyệt</div>}</td>
        <td>{o.tinh_thanh || "—"}</td><td><Thanh diem={o.diem} md={o.muc_do} /></td>
        {MA.map((k) => <td key={k}><O m={o.muc.find((m: any) => m.ma === k)} /></td>)}
        <td>{o.nguoi || <span className="muted">— chưa giao —</span>}</td>
        <td>{o.han ? <span style={{ color: o.qua_han ? "#b33a3a" : undefined }}>{o.qua_han ? "quá hạn " : ""}{ngay(o.han)}</span> : <span className="muted">—</span>}</td></tr>)}
        {!ds.length && <tr><td colSpan={12} className="muted">Không có nhà hàng khớp bộ lọc.</td></tr>}</tbody></table></div>
    <p className="muted" style={{ fontSize: 12 }}>Bấm tên nhà hàng → mở hồ sơ ở đúng tab còn thiếu. ✓ đạt · ½ một phần · ✗ thiếu; con số = số đã duyệt. Hợp đồng và đặt bàn không tính ở đây (đã có 5 điều kiện mở đặt bàn riêng).</p>
  </section>;
}

const TAB: Record<string, string> = { bia: "album", album: "album", mon: "mon", thuc_don: "tdnh", gioi_thieu: "gt", lien_he: "tt" };

/** Tab «Việc của tôi» — 4 cột do máy xếp. */
export function ViecCuaToi({ toast, onMo, ten }: { toast: Toast; onMo: (nid: number, tab: string) => void; ten: string }) {
  const [x, setX] = useState<any>(null);
  useEffect(() => { api("/nha-hang/viec-cua-toi").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  if (!x) return <p className="muted">Đang tải việc…</p>;
  const qh = x.nha_hang.filter((o: any) => o.qua_han).length;
  return <section className="panel" id="at-vct">
    <div className="muted" style={{ fontSize: 12, letterSpacing: ".08em" }}>NHÀ HÀNG / VIỆC BIÊN TẬP CỦA TÔI · {ten}</div>
    <h2 style={{ margin: "2px 0 12px" }}>{x.nha_hang.length} nhà hàng được giao{qh ? ` · ${qh} quá hạn` : ""}</h2>
    {!x.nha_hang.length ? <p className="muted">Chưa có nhà hàng nào được giao cho anh/chị. Chủ tịch giao ở tab «Hoàn thiện».</p> :
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12, alignItems: "start" }}>
        {Object.entries(x.cot as Record<string, string>).map(([k, t]) => {
          const ds = x.nha_hang.filter((o: any) => o.cot === k);
          return <div key={k} className="at-vct-cot" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <b className="muted" style={{ fontSize: 13 }}>{t.toUpperCase()} · {ds.length}</b>
            {ds.map((o: any) => {
              const thieu = o.muc.filter((m: any) => !m.dat).map((m: any) => COT_NGAN[m.ma].toLowerCase());
              return <a key={o.id} href="#" className="panel" style={{ margin: 0, display: "flex", flexDirection: "column", gap: 3, textDecoration: "none", color: "inherit" }}
                onClick={(e) => { e.preventDefault(); const m = o.muc.find((v: any) => !v.dat); onMo(o.id, m ? TAB[m.ma] : "album"); }}>
                <b>{o.ten}</b>
                <span className="muted" style={{ fontSize: 13 }}>{o.diem}%{k === "cho_duyet" ? ` · ${o.cho_duyet} mục chờ duyệt` : thieu.length ? ` · thiếu ${thieu.join(", ")}` : ""}</span>
                {o.han && <span style={{ fontSize: 13, color: o.qua_han ? "#b33a3a" : undefined }}>{o.qua_han ? "Quá hạn" : "Hạn"} {ngay(o.han)}</span>}</a>;
            })}</div>;
        })}</div>}
    <p className="muted" style={{ fontSize: 12 }}>Cột do máy xếp theo dữ liệu: «Đang xin nhà hàng» khi bấm ghi đã xin; «Chờ duyệt» khi có ảnh / món / thực đơn chờ TP ĐH; «Đủ» khi điểm ≥ 80%.</p>
  </section>;
}

/** Danh mục kiểm trong hồ sơ một nhà hàng: điểm, 6 mục, tin xin bổ sung, nhật ký. */
export function HoSoHoanThien({ nid, toast, onTab, lamMoi }: { nid: number; toast: Toast; onTab: (t: string) => void; lamMoi?: number }) {
  const [x, setX] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api(`/nha-hang/${nid}/hoan-thien`).then(setX).catch(() => setX(null)); }, [nid]);
  useEffect(() => { load(); }, [load, lamMoi]);
  if (!x) return null;
  const con = x.muc.filter((m: any) => !m.dat);
  const vien = (m: any) => (m.dat ? ["#cfe6da", "rgba(31,122,80,.08)"] : m.diem > 0 ? ["#f0dcb0", "rgba(176,122,16,.08)"] : ["#f0c9c9", "rgba(179,58,58,.08)"]);
  const NUT: Record<string, string> = { album: "Mở Album →", mon: "Món ăn →", tdnh: "Thực đơn →", gt: "Giới thiệu →", tt: "Thông tin →" };
  const ghi = async () => {
    setBusy(true);
    try { const r = await api<any>(`/nha-hang/${nid}/da-xin`, { method: "POST", json: {} }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  return <div className="panel" id="at-hs-ht" style={{ margin: "10px 0" }}>
    <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
      <b style={{ fontSize: 32, color: mau(x.muc_do) }}>{x.diem}%</b>
      <div style={{ flex: 1, minWidth: 200, display: "flex", flexDirection: "column", gap: 4 }}>
        <span style={{ height: 10, background: "rgba(127,140,153,.25)", borderRadius: 5 }}>
          <span style={{ display: "block", width: `${x.diem}%`, height: 10, background: mau(x.muc_do), borderRadius: 5 }} /></span>
        <span className="muted" style={{ fontSize: 13 }}>{x.muc_do === "du" ? "Đủ để giới thiệu đẹp" : `${x.muc_do === "dang" ? "Đang hoàn thiện" : "Thiếu nhiều"} · còn ${con.length} mục chưa đạt (đủ khi ≥ ${x.nguong.du}%)`}</span></div>
      <span className="muted" style={{ fontSize: 13 }}>Người biên tập: <b>{x.nguoi || "chưa giao"}</b>{x.han ? ` · hạn ${ngay(x.han)}` : ""}</span></div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 8, marginTop: 10 }}>
      {x.muc.map((m: any) => { const [b, n] = vien(m); return <div key={m.ma} className="at-hs-muc" style={{ border: `1px solid ${b}`, background: n, borderRadius: 10, padding: "10px 12px", display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" }}>
        <div><b>{m.dat ? "✓" : m.diem > 0 ? "½" : "✗"} {m.ten}</b> <span className="muted" style={{ fontSize: 12 }}>{m.diem}/{m.diem_toi_da}</span>
          <div className="muted" style={{ fontSize: 13 }}>{m.chi_tiet}</div></div>
        <button className="act grey" onClick={() => onTab(m.tab)}>{NUT[m.tab] || "Mở →"}</button></div>; })}</div>
    {x.tin_xin && <div style={{ marginTop: 12 }}>
      <b>Xin nhà hàng bổ sung</b>
      <div className="muted" style={{ fontSize: 13 }}>Máy soạn sẵn thứ còn thiếu để gửi nhà hàng (Zalo / email). Máy không tự gửi.</div>
      <div style={{ whiteSpace: "pre-line", border: "1px solid rgba(127,140,153,.35)", borderRadius: 8, padding: "10px 12px", margin: "6px 0", lineHeight: 1.6 }}>{x.tin_xin}</div>
      <button className="act teal" onClick={() => navigator.clipboard?.writeText(x.tin_xin).then(() => toast("Đã sao chép nội dung"), () => toast("Không sao chép được — bôi đen để chép tay", true))}>Sao chép nội dung</button>{" "}
      <button className="act grey" disabled={busy} onClick={ghi}>Ghi «đã xin nhà hàng»</button>
      {x.da_xin_luc && <span className="muted" style={{ fontSize: 13 }}> · Lần ghi gần nhất {ngay(x.da_xin_luc)}</span>}</div>}
    {x.nhat_ky?.length > 0 && <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>Nhật ký biên tập: {x.nhat_ky.slice(0, 6).map((k: any) => `${ngay(k.luc).slice(0, 5)} ${k.viec}`).join(" · ")}</div>}
  </div>;
}

export function TagMucDo({ md }: { md: string }) {
  return <Tag cls={md === "du" ? "ok" : md === "dang" ? "warn" : "red"}>{md === "du" ? "Đủ" : md === "dang" ? "Đang hoàn thiện" : "Thiếu nhiều"}</Tag>;
}
