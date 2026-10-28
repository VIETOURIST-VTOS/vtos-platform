"use client";
import { useCallback, useEffect, useState } from "react";
import { api, getToken, taiTep } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { AnhNoiBo } from "./AlbumNhaHang";

/** AT-2b · MÓN ĂN và THỰC ĐƠN nhà hàng (Chủ tịch chốt 29/10/2026).
 *  Món KHÔNG có giá — giá chỉ trên thực đơn. 40 món, 6 món ★. Dị ứng 7 loại + cay / chay.
 *  Thực đơn 4 loại (gọi món, set menu, buffet, khách đoàn), mỗi lần tải là một phiên bản mới; bản cũ giữ.
 *  TP Điều hành duyệt; người thêm / tải không tự duyệt. */

const MAU_TT: Record<string, string> = { nhap: "", cho_duyet: "warn", da_duyet: "ok", an: "red" };
const MON_TRONG = { ten: "", ten_khac: "", nhom: "mon_chinh", mo_ta: "", di_ung: [] as string[], cay: false, chay: false, anh_id: null as number | null };
const kb = (n: number) => `${(n / 1024 / 1024).toFixed(1).replace(".", ",")} MB`;

export function MonAnNhaHang({ nid, toast, onDoi }: { nid: number; toast: (m: string, loi?: boolean) => void; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [album, setAlbum] = useState<any[]>([]);
  const [loc, setLoc] = useState("");
  const [f, setF] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    api(`/nha-hang/${nid}/mon`).then(setX).catch((e) => toast(errMsg(e), true));
    api<any>(`/nha-hang/${nid}/album`).then((r) => setAlbum(r.anh.filter((a: any) => a.trang_thai !== "an"))).catch(() => {});
  }, [nid, toast]);
  useEffect(() => { load(); setF(null); }, [load]);
  if (!x) return <p className="muted">Đang tải món…</p>;
  const goi = async (path: string, json: any, sau?: () => void) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); sau?.(); load(); onDoi?.(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  const ds = x.mon.filter((m: any) => !loc || m.nhom === loc);
  const nhap = x.mon.filter((m: any) => m.trang_thai === "nhap").length;
  const anhMon = [...album].sort((a, b) => Number(b.nhom === "mon_an") - Number(a.nhom === "mon_an"));
  return (<div className="panel" style={{ marginTop: 14 }}>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "flex-start" }}>
      <div><h3 style={{ margin: 0 }}>Món ăn nổi bật</h3>
        <div className="muted">Ảnh riêng từng món, thành phần, dị ứng. Không ghi giá — giá chỉ nằm trên thực đơn. Tối đa {x.toi_da} món · {x.noi_bat_toi_da} món ★ hiện đầu trang khách.</div></div>
      {x.duoc_sua && <div style={{ display: "flex", gap: 6 }}>
        <button className="act grey" onClick={() => setF({ ...MON_TRONG })}>+ Thêm món</button>
        <button className="act teal" disabled={busy || !nhap} onClick={() => goi(`/nha-hang/${nid}/mon/gui-duyet`, {})}>Gửi duyệt{nhap ? ` ${nhap} món` : ""}</button></div>}
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      <button className={`act ${!loc ? "teal" : "grey"}`} onClick={() => setLoc("")}>Tất cả {x.mon.length}</button>
      {Object.entries(x.nhom_mon).map(([k, v]: any) => <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{v} {x.mon.filter((m: any) => m.nhom === k).length}</button>)}</div>

    {f && <div className="panel" style={{ border: "1px solid var(--teal, #2bb5a0)", marginBottom: 10 }}>
      <b>{f.id ? `Sửa món · ${f.ten}` : "Thêm món"}</b>
      <div className="grid">
        <label>Tên món (hiện cho khách)<input value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
        <label>Tên khác / tiếng Anh<input value={f.ten_khac} onChange={(e) => setF({ ...f, ten_khac: e.target.value })} /></label>
        <label>Nhóm<select value={f.nhom} onChange={(e) => setF({ ...f, nhom: e.target.value })}>{Object.entries(x.nhom_mon).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Ảnh món (từ album)<select value={f.anh_id ?? ""} onChange={(e) => setF({ ...f, anh_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">— chưa chọn —</option>
          {anhMon.map((a: any) => <option key={a.id} value={a.id}>#{a.id} · {a.nhom_ten}{a.chu_thich ? ` · ${a.chu_thich}` : ""} · {a.trang_thai_ten}</option>)}</select></label>
      </div>
      <label>Mô tả ngắn (VTD viết, không chép nguồn ngoài)<input value={f.mo_ta} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", margin: "6px 0" }}>
        <span className="muted">Thành phần dễ dị ứng (nhà hàng xác nhận):</span>
        {Object.entries(x.di_ung).map(([k, v]: any) => { const co = f.di_ung.includes(k);
          return <button key={k} type="button" className={`act ${co ? "teal" : "grey"}`} aria-pressed={co}
            onClick={() => setF({ ...f, di_ung: co ? f.di_ung.filter((y: string) => y !== k) : [...f.di_ung, k] })}>{v}{co ? " ✓" : ""}</button>; })}
        <button type="button" className={`act ${f.cay ? "teal" : "grey"}`} aria-pressed={f.cay} onClick={() => setF({ ...f, cay: !f.cay })}>Cay{f.cay ? " ✓" : ""}</button>
        <button type="button" className={`act ${f.chay ? "teal" : "grey"}`} aria-pressed={f.chay} onClick={() => setF({ ...f, chay: !f.chay })}>Món chay{f.chay ? " ✓" : ""}</button>
      </div>
      <div className="muted">Ảnh món lấy trong Album (nên để nhóm «Món ăn»). Ảnh chưa duyệt thì trang khách chưa hiện ảnh. Sửa tên, mô tả, dị ứng, ảnh của món đã duyệt → về «Chờ duyệt».</div>
      <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
        <button className="act teal" disabled={busy} onClick={() => goi(f.id ? `/nha-hang/${nid}/mon/${f.id}` : `/nha-hang/${nid}/mon`,
          { ten: f.ten, ten_khac: f.ten_khac, nhom: f.nhom, mo_ta: f.mo_ta, di_ung: f.di_ung, cay: f.cay, chay: f.chay, anh_id: f.anh_id }, () => setF(null))}>Lưu</button>
        <button className="act grey" onClick={() => setF(null)}>Bỏ</button></div>
    </div>}

    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 260px), 1fr))", gap: 14 }}>
      {ds.map((m: any) => <div key={m.id} style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ position: "relative" }}>
          {m.anh_nho ? <AnhNoiBo src={m.anh_nho} alt={m.ten} style={{ width: "100%", aspectRatio: "16 / 10" }} />
            : <div style={{ aspectRatio: "16 / 10", display: "flex", alignItems: "center", justifyContent: "center", border: "1px dashed var(--line, #2a3b4d)" }} className="muted">Chưa có ảnh món</div>}
          {m.noi_bat && <span style={{ position: "absolute", left: 10, top: 10, background: "rgba(0,0,0,.65)", color: "#fff", borderRadius: 6, padding: "2px 8px", fontSize: 12 }}>★ Nổi bật</span>}
        </div>
        <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
          <div className="muted" style={{ fontSize: 12, letterSpacing: ".06em" }}>{m.nhom_ten.toUpperCase()}</div>
          <b>{m.ten}</b>{m.ten_khac && <span className="muted">{m.ten_khac}</span>}
          {m.mo_ta && <div style={{ fontSize: 13 }}>{m.mo_ta}</div>}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>{m.di_ung_ten.map((d: string) => <Tag key={d} cls="warn">{d}</Tag>)}{m.cay && <Tag cls="red">Cay</Tag>}{m.chay && <Tag cls="ok">Chay</Tag>}</div>
          {m.anh_id && !m.anh_da_duyet && <div className="muted" style={{ fontSize: 12 }}>Ảnh món chưa duyệt — khách chưa thấy ảnh</div>}
          {m.ly_do_tra_lai && <div style={{ color: "var(--red, #e5484d)", fontSize: 13 }}>Trả lại: {m.ly_do_tra_lai}</div>}
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", gap: 6, alignItems: "center", borderTop: "1px solid var(--line, #2a3b4d)", paddingTop: 8, flexWrap: "wrap" }}>
            <Tag cls={MAU_TT[m.trang_thai]}>{m.trang_thai_ten}</Tag><span style={{ flex: 1 }} />
            {x.duoc_sua && <>
              <button className="act grey" onClick={() => setF({ ...MON_TRONG, ...m })}>Sửa</button>
              {m.trang_thai !== "an" && <button className="act grey" disabled={busy} aria-label={m.noi_bat ? "Bỏ nổi bật" : "Gắn nổi bật"} onClick={() => goi(`/nha-hang/mon/${m.id}/noi-bat`, { bat: !m.noi_bat })}>{m.noi_bat ? "Bỏ ★" : "★"}</button>}
              <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/mon/${m.id}/an`, { an: m.trang_thai !== "an" })}>{m.trang_thai === "an" ? "Bỏ ẩn" : "Ẩn"}</button></>}
          </div>
        </div></div>)}
      {!ds.length && <p className="muted">Chưa có món{loc ? " trong nhóm này" : ""}.</p>}
    </div>
    <p className="muted" style={{ marginTop: 8 }}>Món không có giá (Chủ tịch chốt 29/10/2026): giá chỉ trên thực đơn nhà hàng; giá bán qua VTD ở tab «Gói đặt bàn». Trang khách luôn kèm câu «hỏi lại nhà hàng nếu bị dị ứng».</p>
  </div>);
}

const TT_BAN: Record<string, [string, string]> = { dang_dung: ["Đang dùng", "ok"], cho_hieu_luc: ["Chờ ngày hiệu lực", "warn"], da_thay: ["Đã thay", ""],
  cho_duyet: ["Chờ duyệt", "warn"], tra_lai: ["Trả lại", "red"] };

export function ThucDonNhaHangTab({ nid, toast, onDoi }: { nid: number; toast: (m: string, loi?: boolean) => void; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [loai, setLoai] = useState("goi_mon");
  const [banId, setBanId] = useState<number | null>(null);
  const [trang, setTrang] = useState(0);
  const [tep, setTep] = useState<File[]>([]);
  const [hl, setHl] = useState("");
  const [cc, setCc] = useState("");
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api(`/nha-hang/${nid}/thuc-don-nh`).then(setX).catch((e) => toast(errMsg(e), true)), [nid, toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải thực đơn…</p>;
  const L = x.loai[loai];
  const ban = L.ban.find((b: any) => b.id === banId) || L.ban[0];
  const tai = async () => {
    if (!tep.length) { toast("Chọn tệp thực đơn (PDF hoặc ảnh)", true); return; }
    const qua = tep.find((t) => t.size > x.toi_da_mb * 1024 * 1024);
    if (qua) { toast(`«${qua.name}» ${kb(qua.size)}, quá ${x.toi_da_mb} MB`, true); return; }
    setBusy(true);
    try {
      const fd = new FormData(); tep.forEach((t) => fd.append("tep", t)); fd.append("loai", loai); fd.append("hieu_luc_tu", hl); fd.append("can_cu", cc);
      const r = await fetch(`/api/v1/nha-hang/${nid}/thuc-don-nh`, { method: "POST", headers: { Authorization: `Bearer ${getToken() || ""}` }, body: fd });
      const d = await r.json().catch(() => null);
      if (!r.ok) throw new Error(typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}`);
      toast(d.message); setTep([]); setCc(""); setHl(""); setBanId(d.id); setTrang(0); await load(); onDoi?.();
    } catch (e: any) { toast(e.message, true); } finally { setBusy(false); }
  };
  const duyet = async (d: boolean) => {
    setBusy(true);
    try { const r = await api<any>(`/nha-hang/thuc-don-nh/${ban.id}/duyet`, { method: "POST", json: { duyet: d, ly_do: lyDo } }); toast(r.message); setLyDo(""); await load(); onDoi?.(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const tr = ban?.trang?.[Math.min(trang, (ban?.trang?.length || 1) - 1)];
  return (<div className="panel" style={{ marginTop: 14 }}>
    <h3 style={{ margin: 0 }}>Thực đơn nhà hàng</h3>
    <div className="muted">Menu ảnh / PDF nhiều trang theo 4 loại. Mỗi lần thay là một phiên bản mới; bản cũ giữ nguyên. Không tính vào 60 ảnh album. Giá trên thực đơn chỉ để khách tham khảo — giá bán qua VTD ở tab «Gói đặt bàn».</div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10, margin: "10px 0" }}>
      {Object.entries(x.loai).map(([k, v]: any) => { const hh = v.ban.find((b: any) => b.trang_thai === "dang_dung"); const cho = v.ban.filter((b: any) => b.trang_thai === "cho_duyet").length;
        return <button key={k} type="button" onClick={() => { setLoai(k); setBanId(null); setTrang(0); }} aria-pressed={loai === k}
          style={{ all: "unset", cursor: "pointer", border: loai === k ? "2px solid var(--teal, #2bb5a0)" : "1px solid var(--line, #2a3b4d)", borderRadius: 12, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
          <b>{v.ten}</b><span className="muted" style={{ fontSize: 13 }}>{hh ? `${hh.ten} đang dùng · ${hh.so_trang} trang` : "Chưa có bản đang dùng"}{cho ? ` · ${cho} chờ duyệt` : ""}</span></button>; })}
    </div>
    <b>Phiên bản · {L.ten}</b>
    <div className="wrap"><table><thead><tr><th>Bản</th><th>Hiệu lực từ</th><th>Trang</th><th>Căn cứ</th><th>Trạng thái</th><th>Tải / duyệt</th></tr></thead>
      <tbody>{L.ban.map((b: any) => <tr key={b.id} onClick={() => { setBanId(b.id); setTrang(0); }} style={{ cursor: "pointer", outline: ban?.id === b.id ? "1px solid var(--teal, #2bb5a0)" : undefined }}>
        <td><b>{b.ten}</b></td><td>{b.hieu_luc_tu}</td><td>{b.so_trang}</td><td className="muted">{b.can_cu}</td>
        <td><Tag cls={TT_BAN[b.trang_thai]?.[1] || ""}>{TT_BAN[b.trang_thai]?.[0] || b.trang_thai}</Tag>{b.ly_do_tra_lai && <div className="muted">{b.ly_do_tra_lai}</div>}</td>
        <td className="muted">{b.tai_boi}{b.duyet_boi ? ` / ${b.duyet_boi}` : ""}</td></tr>)}
        {!L.ban.length && <tr><td colSpan={6} className="muted">Chưa có bản nào.</td></tr>}</tbody></table></div>
    <div className="muted" style={{ fontSize: 12 }}>Bản được duyệt tự thành «Đang dùng» từ ngày hiệu lực; bản trước chuyển «Đã thay», vẫn mở xem được. Không xoá phiên bản.</div>

    <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 10 }}>
      {ban && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <b>Xem {ban.ten} · trang {Math.min(trang, ban.trang.length - 1) + 1} / {ban.trang.length}</b>
        {tr && <AnhNoiBo src={tr.hien} alt={`${L.ten} ${ban.ten} trang ${trang + 1}`} style={{ width: 340, maxWidth: "100%", aspectRatio: "3 / 4", objectFit: "contain", background: "#fffdf8", borderRadius: 8 }} />}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{ban.trang.map((t: any, i: number) => <button key={t.id} type="button" className={`act ${i === trang ? "teal" : "grey"}`} onClick={() => setTrang(i)}>{i + 1}</button>)}</div>
        <button className="act grey" onClick={() => tr && taiTep(tr.goc.replace(/^\/api\/v1/, ""), `thuc-don-${ban.ten}`).catch((e) => toast(errMsg(e), true))}>Tải bản gốc</button>
        {x.duoc_duyet && ban.trang_thai === "cho_duyet" && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <button className="act teal" disabled={busy} onClick={() => duyet(true)}>Duyệt {ban.ten}</button>
          <input placeholder="Lý do trả lại" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
          <button className="act grey" disabled={busy} onClick={() => duyet(false)}>Trả lại</button></div>}
      </div>}
      {x.duoc_tai && <div className="panel" style={{ flex: 1, minWidth: 260 }}>
        <b>Tải bản mới · {L.ten}</b>
        <label>Tệp (một PDF, hoặc nhiều ảnh — mỗi ảnh một trang)<input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={(e) => setTep(Array.from(e.target.files || []))} /></label>
        {tep.length > 0 && <div className="muted">{tep.map((t) => `${t.name} · ${kb(t.size)}`).join(" · ")}</div>}
        <label>Hiệu lực từ ngày (trống = hôm nay)<input type="date" value={hl} onChange={(e) => setHl(e.target.value)} /></label>
        <label>Căn cứ (ai gửi, kênh nào, ngày)<input value={cc} placeholder="Email chị Lan, quản lý, 29/10/2026" onChange={(e) => setCc(e.target.value)} /></label>
        <button className="act teal" disabled={busy} onClick={tai}>Tải lên và gửi duyệt</button>
        <div className="muted">PDF / JPG / PNG / WEBP · tối đa {x.toi_da_mb} MB mỗi tệp, {x.toi_da_trang} trang mỗi bản. PDF máy tách thành trang ảnh để khách lật; giữ tệp gốc. Tải thực đơn không đổi giá gói, không mở đặt bàn.</div>
      </div>}
    </div>
  </div>);
}

/** Món và thực đơn chờ TP Điều hành duyệt — gắn vào tab «Chờ duyệt». */
export function NoiDungChoDuyet({ toast, onDoi }: { toast: (m: string, loi?: boolean) => void; onDoi?: () => void }) {
  const [x, setX] = useState<any>(null);
  const [chon, setChon] = useState<number[]>([]);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api("/nha-hang/noi-dung-cho-duyet").then((r: any) => { setX(r); setChon([]); }).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return null;
  const goi = async (path: string, json: any) => {
    if (json.duyet === false && lyDo.trim().length < 3) { toast("Trả lại phải ghi lý do", true); return; }
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json: { ...json, ly_do: lyDo } }); toast(r.message + (r.bo_qua?.length ? ` — ${r.bo_qua[0].ly_do}` : "")); setLyDo(""); load(); onDoi?.(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const duocChon = x.mon.filter((m: any) => !m.khong_duyet).map((m: any) => m.id);
  return (<>
    <section className="panel" style={{ marginTop: 14 }}>
      <h2>Món chờ duyệt <Tag cls="warn">{x.mon.length}</Tag></h2>
      {x.duoc_duyet && x.mon.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", margin: "6px 0" }}>
        <label style={{ display: "flex", flexDirection: "row", gap: 6, alignItems: "center" }}><input type="checkbox" aria-label="Chọn tất cả món duyệt được" checked={duocChon.length > 0 && chon.length === duocChon.length} onChange={(e) => setChon(e.target.checked ? duocChon : [])} />Chọn tất cả</label>
        <button className="act teal" disabled={busy || !chon.length} onClick={() => goi("/nha-hang/mon/duyet", { ids: chon, duyet: true })}>Duyệt {chon.length} món</button>
        <input placeholder="Lý do trả lại" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
        <button className="act grey" disabled={busy || !chon.length} onClick={() => goi("/nha-hang/mon/duyet", { ids: chon, duyet: false })}>Trả lại</button></div>}
      <div className="wrap"><table><thead><tr>{x.duoc_duyet && <th></th>}<th>Nhà hàng</th><th>Món</th><th>Dị ứng</th><th>Ảnh</th><th>Người sửa</th></tr></thead>
        <tbody>{x.mon.map((m: any) => <tr key={m.id}>
          {x.duoc_duyet && <td><input type="checkbox" aria-label={`Chọn món ${m.ten}`} disabled={!!m.khong_duyet} checked={chon.includes(m.id)} onChange={(e) => setChon(e.target.checked ? [...chon, m.id] : chon.filter((i) => i !== m.id))} /></td>}
          <td>{m.nha_hang_ten}</td><td><b>{m.ten}</b> <span className="muted">· {m.nhom_ten}</span>{m.mo_ta && <div className="muted">{m.mo_ta}</div>}{m.khong_duyet && <div style={{ color: "var(--red, #e5484d)" }}>{m.khong_duyet}</div>}</td>
          <td>{[...m.di_ung_ten, m.cay ? "Cay" : "", m.chay ? "Chay" : ""].filter(Boolean).join(", ") || "—"}</td>
          <td>{m.anh_nho ? <AnhNoiBo src={m.anh_nho} alt={m.ten} style={{ width: 72, height: 54, borderRadius: 6 }} /> : <span className="muted">—</span>}</td>
          <td className="muted">{m.sua_boi || m.tao_boi}</td></tr>)}
          {!x.mon.length && <tr><td colSpan={6} className="muted">Không có món chờ duyệt.</td></tr>}</tbody></table></div>
    </section>
    <section className="panel" style={{ marginTop: 14 }}>
      <h2>Thực đơn chờ duyệt <Tag cls="warn">{x.thuc_don.length}</Tag></h2>
      <div className="wrap"><table><thead><tr><th>Trang đầu</th><th>Nhà hàng</th><th>Loại · bản</th><th>Hiệu lực</th><th>Căn cứ</th><th>Người tải</th>{x.duoc_duyet && <th></th>}</tr></thead>
        <tbody>{x.thuc_don.map((b: any) => <tr key={b.id}>
          <td>{b.trang_dau ? <AnhNoiBo src={b.trang_dau} alt={`${b.loai_ten} ${b.ten}`} style={{ width: 60, height: 80, borderRadius: 4, objectFit: "contain" }} /> : "—"}</td>
          <td>{b.nha_hang_ten}</td><td>{b.loai_ten} · <b>{b.ten}</b> <span className="muted">· {b.so_trang} trang</span></td><td>{b.hieu_luc_tu}</td>
          <td className="muted">{b.can_cu}</td><td className="muted">{b.tai_boi}{b.khong_duyet && <div style={{ color: "var(--red, #e5484d)" }}>{b.khong_duyet}</div>}</td>
          {x.duoc_duyet && <td style={{ whiteSpace: "nowrap" }}><button className="act teal" disabled={busy || !!b.khong_duyet} onClick={() => goi(`/nha-hang/thuc-don-nh/${b.id}/duyet`, { duyet: true })}>Duyệt</button>
            <button className="act grey" disabled={busy} onClick={() => goi(`/nha-hang/thuc-don-nh/${b.id}/duyet`, { duyet: false })}>Trả lại</button></td>}</tr>)}
          {!x.thuc_don.length && <tr><td colSpan={7} className="muted">Không có thực đơn chờ duyệt.</td></tr>}</tbody></table></div>
      {x.duoc_duyet && x.thuc_don.length > 0 && <input placeholder="Lý do trả lại (ghi trước khi bấm Trả lại)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />}
    </section>
  </>);
}
