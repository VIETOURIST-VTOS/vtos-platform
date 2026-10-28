"use client";
/* CD-1 · CỔNG CỔ ĐÔNG ĐỢT 1 (Chủ tịch duyệt bản xem thử 28/10/2026; màn CD01, CD07–CD10, CD14–CD15 bộ v3.2).

   · Tài liệu: chỉ bản đã công bố mà IR – Pháp chế đưa lên; lịch sử bản thay hiện kèm lý do.
   · Sự kiện: «Ghi nhận quan tâm» — không phải đăng ký tham dự, không biểu quyết trên cổng.
   · Liên hệ IR: câu hỏi có mã IR-xxxx; IR trả lời bằng thông tin đã công bố, như nhau với mọi cổ đông.
   · Ưu đãi, cổ tức, hồ sơ sở hữu: Đợt 2 — KHÔNG hiện số mẫu như thật. */
import { useCallback, useEffect, useState } from "react";
import { goiCong, phienCong } from "@/lib/cong";
import { svg } from "../khach/icons";
import KhachSanOta from "../KhachSanOta";
import VeMayBayOta from "../VeMayBayOta";

type Tab = "home" | "docs" | "events" | "ir" | "hotel" | "flight";
const MENU: [Tab, string, string][] = [["home", "Tổng quan", "landmark"], ["docs", "Công bố thông tin", "file-text"],
  ["events", "Đại hội & sự kiện", "calendar"], ["ir", "Liên hệ IR", "messages-square"], ["hotel", "Khách sạn", "hotel"], ["flight", "Vé máy bay", "plane"]];
const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const gio = (s?: string | null) => (s ? `${ngay(s)} ${s.slice(11, 16)}` : "");
const kb = (n?: number) => (n ? `${Math.max(1, Math.round(n / 1024)).toLocaleString("vi-VN")} KB` : "");
function Badge({ c, children }: { c?: string; children: any }) { return <span className={`v3-badge ${c || "neutral"}`}>{children}</span>; }
function Nut({ i, children, kieu = "secondary", ...p }: any) {
  return <button type="button" className={`v3-button v3-${kieu} cursor-interaction`} {...p}>{i && <I n={i} />}<span>{children}</span></button>;
}
const MAU_IR: Record<string, string> = { cho: "warn", da_tra_loi: "good", dong: "neutral" };

/** Tải tệp tài liệu: máy chủ kiểm phiên + phạm vi rồi trả PDF; mở bằng URL tạm, thu hồi ngay sau. */
export async function moTep(url: string, ten: string, coPhien: boolean) {
  const headers: Record<string, string> = {};
  if (coPhien) { const p = phienCong(); if (p) headers.Authorization = `Bearer ${p}`; }
  const r = await fetch(url, { headers });
  if (!r.ok) { let m = `Lỗi ${r.status}`; try { const d = JSON.parse(await r.text())?.detail; if (d) m = typeof d === "string" ? d : d.message || m; } catch { /* giữ lỗi chung */ } throw new Error(m); }
  const u = URL.createObjectURL(await r.blob());
  const a = document.createElement("a"); a.href = u; a.download = ten || "tai-lieu.pdf";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(u), 2000);
}

/** Thư viện tài liệu — dùng chung cho cổ đông (coPhien) và khách xem IR công khai (A18). */
export function ThuVien({ coPhien }: { coPhien: boolean }) {
  const goc = coPhien ? "/api/v1/cong/co-dong" : "/api/v1/cong/ir-cong-khai";
  const [d, setD] = useState<any>(null);
  const [nhom, setNhom] = useState(""); const [nam, setNam] = useState("");
  const [mo, setMo] = useState<any>(null); const [loi, setLoi] = useState("");
  const doc = useCallback(async (p: string) => {
    const headers: Record<string, string> = {};
    if (coPhien) { const s = phienCong(); if (s) headers.Authorization = `Bearer ${s}`; }
    const r = await fetch(`${goc}${p}`, { headers }); const t = await r.json().catch(() => null);
    if (!r.ok) throw new Error(typeof t?.detail === "string" ? t.detail : `Lỗi ${r.status}`);
    return t;
  }, [coPhien, goc]);
  useEffect(() => {
    const q = new URLSearchParams(); if (nhom) q.set("nhom", nhom); if (nam) q.set("nam", nam);
    doc(`/tai-lieu?${q}`).then(setD).catch((x) => setLoi(x.message));
  }, [doc, nhom, nam]);
  const xem = (id: number) => { setLoi(""); doc(`/tai-lieu/${id}`).then(setMo).catch((x) => setLoi(x.message)); };
  const tai = (t: any) => moTep(`${goc}/tai-lieu/${t.id}/tep`, t.ten_tep, coPhien).catch((x) => setLoi(x.message));

  return (<>
    <section className="v3-panel v3-form-grid">
      <label className="v3-field">Nhóm tài liệu<select value={nhom} onChange={(e) => setNhom(e.target.value)}>
        <option value="">Tất cả</option>{d && Object.entries(d.nhom).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
      <label className="v3-field">Năm công bố<select value={nam} onChange={(e) => setNam(e.target.value)}>
        <option value="">Tất cả</option>{d?.nam?.map((n: number) => <option key={n} value={n}>{n}</option>)}</select></label>
    </section>
    {loi && <div className="v3-notice warn"><I n="info" /><span>{loi}</span></div>}
    <section className="v3-panel"><div className="v3-section-title"><h3>Tài liệu đã công bố</h3>{d && <Badge>{d.tai_lieu.length}</Badge>}</div>
      {!d ? <p>Đang tải…</p> : d.tai_lieu.length ? <div className="v3-table-wrap"><table>
        <thead><tr><th scope="col">Tài liệu</th><th scope="col">Ngày công bố</th>{coPhien && <th scope="col">Phạm vi</th>}<th scope="col"></th></tr></thead>
        <tbody>{d.tai_lieu.map((t: any) => <tr key={t.id}><th scope="row">{t.tieu_de}<small>{t.nhom_ten}{t.thay_cho_id ? " · bản thay" : ""}</small></th>
          <td>{ngay(t.da_cong_bo_luc)}<small>{t.noi_cong_bo}</small></td>
          {coPhien && <td><Badge c={t.pham_vi === "cong_khai" ? "good" : "warn"}>{t.pham_vi_ten}</Badge></td>}
          <td><Nut kieu="quiet" i="chevron-right" onClick={() => xem(t.id)}>Xem</Nut></td></tr>)}</tbody></table></div>
        : <p>Chưa có tài liệu {nhom || nam ? "khớp bộ lọc" : "nào được đưa lên"}.</p>}
      <small>Chỉ tài liệu Vietourist đã công bố chính thức. {coPhien ? "Tài liệu «Công khai» ai cũng xem được tại ir.vietourist.vn." : "Tài liệu riêng cho cổ đông cần đăng nhập."}</small></section>
    {mo && <section className="v3-panel"><div className="v3-section-title"><h3>{mo.tieu_de}</h3><Nut kieu="quiet" i="x" onClick={() => setMo(null)}>Đóng</Nut></div>
      <div className="v3-table-wrap"><table><tbody>
        <tr><th scope="row">Nhóm</th><td>{mo.nhom_ten}</td></tr>
        <tr><th scope="row">Thời điểm công bố</th><td>{gio(mo.da_cong_bo_luc)}</td></tr>
        <tr><th scope="row">Nơi công bố</th><td>{mo.noi_cong_bo || "—"}</td></tr>
        <tr><th scope="row">Tệp</th><td>{mo.ten_tep} {kb(mo.kich_thuoc)}</td></tr>
        {mo.thay_cho_id && <tr><th scope="row">Lý do có bản này</th><td>{mo.ly_do_thay}</td></tr>}
      </tbody></table></div>
      {mo.trang_thai === "thay_the" && <div className="v3-notice warn"><I n="info" /><span>Đã có bản mới thay bản này.{mo.ban_moi_id && <> <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => xem(mo.ban_moi_id)}><span>Xem bản mới</span></button></>}</span></div>}
      {mo.lich_su?.length > 0 && <><h4 style={{ margin: "8px 0 4px" }}>Lịch sử phiên bản</h4><ul>{mo.lich_su.map((h: any) =>
        <li key={h.id}><button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => xem(h.id)}><span>{h.tieu_de} · {ngay(h.da_cong_bo_luc)}</span></button>
          <small> — thay vì: {h.ly_do_thay_boi_ban_sau}</small></li>)}</ul></>}
      <div className="v3-actions"><Nut kieu="primary" i="file-text" onClick={() => tai(mo)}>Tải tệp PDF</Nut></div></section>}
  </>);
}

export default function CoDong({ toi, thoat }: { toi: any; thoat: () => void }) {
  const [tab, setTab] = useState<Tab>("home");
  const [menuMo, setMenuMo] = useState(false);
  const [tq, setTq] = useState<any>(null);
  const [sk, setSk] = useState<any[] | null>(null);
  const [ir, setIr] = useState<any>(null);
  const [f, setF] = useState({ chu_de: "tai_lieu", noi_dung: "" });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const loi = (x: any) => setErr(x.message || String(x));
  const taiTq = useCallback(() => goiCong("/co-dong/tong-quan").then(setTq).catch(loi), []);
  const taiSk = useCallback(() => goiCong("/co-dong/su-kien").then((r) => setSk(r.su_kien)).catch(loi), []);
  const taiIr = useCallback(() => goiCong("/co-dong/ir").then(setIr).catch(loi), []);
  useEffect(() => { taiTq(); }, [taiTq]);
  const di = (t: Tab) => {
    setTab(t); setMenuMo(false); setMsg(""); setErr("");
    if (t === "home") taiTq(); if (t === "events") taiSk(); if (t === "ir") taiIr();
  };
  const quanTam = async (s: any, bat: boolean) => {
    setBusy(true); setErr("");
    try { const r = await goiCong(`/co-dong/su-kien/${s.id}/quan-tam`, { bat }); setMsg(r.message); setSk((ds) => (ds || []).map((x) => (x.id === s.id ? r.su_kien : x))); }
    catch (x) { loi(x); } finally { setBusy(false); }
  };
  const guiIr = async () => {
    setBusy(true); setErr(""); setMsg("");
    try { const r = await goiCong("/co-dong/ir", f); setMsg(r.message); setIr((o: any) => ({ ...o, yeu_cau: r.yeu_cau })); setF({ ...f, noi_dung: "" }); }
    catch (x) { loi(x); } finally { setBusy(false); }
  };
  const nhan = MENU.find(([k]) => k === tab)?.[1] || "";
  const ten = toi.ho_ten || "Cổ đông";

  return (<section className="v3-app" data-portal="co-dong">
    <header className="v3-topbar">
      <button type="button" className="v3-brand cursor-interaction" onClick={() => di("home")}>
        <span className="vh-logo"><img src="/cong/logo.png" alt="Vietourist Holdings" /></span><span>VTD<small>VIETOURIST HOLDINGS</small></span></button>
      <nav aria-label="Cổng"><button type="button" aria-pressed="true"><I n="landmark" /><span>Cổ đông</span></button></nav>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button>
    </header>
    <div className="v3-mobile-nav"><Nut i="menu" onClick={() => setMenuMo(!menuMo)}>Danh mục chức năng</Nut><strong>{nhan}</strong></div>
    <div className="v3-layout">
      <aside className={`v3-sidebar ${menuMo ? "open" : ""}`}>
        <div className="v3-side-profile"><span className="v3-avatar"><I n="landmark" /></span><strong>{ten}</strong><small>Cổ đông · đã xác minh bởi IR</small></div>
        <nav aria-label="Chức năng cổ đông">{MENU.map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={tab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
        <div className="v3-side-bottom"><Nut kieu="quiet" i="log-out" onClick={thoat}>Đăng xuất</Nut></div>
      </aside>
      <main className="v3-main">
        <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng cổ đông</div><h1>{nhan}</h1></div></div>
        {msg && <div className="v3-notice info"><I n="check" /><span>{msg}</span></div>}
        {err && <div className="v3-notice warn"><I n="info" /><span>{err}</span></div>}

        {tab === "home" && <>
          <section className="v3-hero shareholder"><div><span className="v3-eyebrow">QUAN HỆ NHÀ ĐẦU TƯ</span><h2>Thông tin minh bạch.<br />Đồng hành dài hạn.</h2>
            <p>Tài liệu đã công bố, đại hội và kênh hỏi IR trong một tài khoản.</p>
            <Nut kieu="primary" i="file-text" onClick={() => di("docs")}>Tra cứu công bố thông tin</Nut></div>
            <div className="v3-hero-art" aria-hidden="true"><I n="landmark" /></div></section>
          {!tq ? <section className="v3-panel"><p>Đang tải…</p></section> : <div className="v3-metrics">
            <section><span><I n="file-text" />Tài liệu mới nhất</span><strong>{tq.tai_lieu_moi[0]?.tieu_de || "Chưa có"}</strong>
              <small>{tq.tai_lieu_moi[0] ? `Công bố ${ngay(tq.tai_lieu_moi[0].da_cong_bo_luc)}` : "IR đưa lên sau khi công bố"}</small></section>
            <section><span><I n="calendar" />Sự kiện sắp tới</span><strong>{tq.su_kien_sap_toi?.ten || "Chưa có"}</strong>
              <small>{tq.su_kien_sap_toi ? `${gio(tq.su_kien_sap_toi.bat_dau)}${tq.su_kien_sap_toi.dia_diem ? ` · ${tq.su_kien_sap_toi.dia_diem}` : ""}` : "Thông báo sẽ hiện tại đây"}</small></section>
            <section><span><I n="messages-square" />Câu hỏi IR của tôi</span><strong>{tq.ir_cho ? `${tq.ir_cho} đang chờ trả lời` : "Không có câu chờ"}</strong>
              <small>{tq.ir_moi_nhat ? `${tq.ir_moi_nhat.ma} · ${tq.ir_moi_nhat.trang_thai_ten}` : "Gửi câu hỏi ở mục Liên hệ IR"}</small></section>
          </div>}
          <section className="v3-panel"><div className="v3-section-title"><h3>Sở hữu & ưu đãi cổ đông</h3><Badge c="demo">Đợt sau</Badge></div>
            <p>Số cổ phần, hạng ưu đãi và cổ tức chưa hiện trên cổng. IR đối chiếu sổ cổ đông ở đợt sau; VTOS không tự ghi số sở hữu.</p></section>
        </>}

        {tab === "docs" && <ThuVien coPhien />}

        {tab === "events" && <>{!sk ? <section className="v3-panel"><p>Đang tải…</p></section> : !sk.length
          ? <section className="v3-panel"><div className="v3-section-title"><h3>Chưa có thông báo đại hội hay sự kiện</h3></div>
            <p>Khi IR thông báo sẽ có ngày họp, ngày chốt danh sách, tài liệu và hướng dẫn tham dự.</p></section>
          : sk.map((s) => <section key={s.id} className="v3-panel">
            <div className="v3-section-title"><h3>{s.ten}</h3>{s.trang_thai === "huy" ? <Badge c="warn">Đã hủy</Badge>
              : s.da_dien_ra ? <Badge>Đã diễn ra</Badge> : s.toi_quan_tam ? <Badge c="good">Đã ghi nhận quan tâm</Badge> : <Badge c="good">Đã thông báo</Badge>}</div>
            <div className="v3-table-wrap"><table><tbody>
              <tr><th scope="row">Loại</th><td>{s.loai_ten}</td></tr>
              <tr><th scope="row">Thời gian</th><td>{gio(s.bat_dau)}</td></tr>
              {s.dia_diem && <tr><th scope="row">Địa điểm</th><td>{s.dia_diem}</td></tr>}
              {s.ngay_chot_ds && <tr><th scope="row">Ngày chốt danh sách</th><td>{ngay(s.ngay_chot_ds)}</td></tr>}
              {s.tai_lieu.length > 0 && <tr><th scope="row">Tài liệu</th><td>{s.tai_lieu.map((t: any) =>
                <button key={t.id} type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => moTep(`/api/v1/cong/co-dong/tai-lieu/${t.id}/tep`, `${t.tieu_de}.pdf`, true).catch(loi)}><span>{t.tieu_de}</span></button>)}</td></tr>}
            </tbody></table></div>
            {s.mo_ta && <p style={{ whiteSpace: "pre-wrap" }}>{s.mo_ta}</p>}
            {s.trang_thai === "huy" && <div className="v3-notice warn"><I n="info" /><span>Lý do hủy: {s.ly_do_huy}</span></div>}
            {s.trang_thai === "cong_bo" && !s.da_dien_ra && s.nhan_quan_tam && <div className="v3-actions">
              {s.toi_quan_tam ? <><Nut disabled>Đã ghi nhận quan tâm · {ngay(s.quan_tam_luc)}</Nut><Nut kieu="quiet" disabled={busy} onClick={() => quanTam(s, false)}>Bỏ quan tâm</Nut></>
                : <Nut kieu="primary" i="calendar" disabled={busy} onClick={() => quanTam(s, true)}>Ghi nhận quan tâm</Nut>}</div>}
            {s.loai.startsWith("dhdcd") ? <small>Đăng ký tham dự, ủy quyền và biểu quyết theo thư mời chính thức. Cổng chưa nhận biểu quyết.</small>
              : <small>Ghi nhận quan tâm giúp IR chuẩn bị, chưa phải giữ chỗ. IR liên hệ lại để xác nhận.</small>}
          </section>)}</>}

        {tab === "ir" && <>
          <section className="v3-panel"><div className="v3-section-title"><h3>Gửi câu hỏi tới IR</h3></div>
            <label className="v3-field">Chủ đề<select value={f.chu_de} onChange={(e) => setF({ ...f, chu_de: e.target.value })}>
              {ir && Object.entries(ir.chu_de).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label className="v3-field">Nội dung<textarea rows={4} maxLength={2000} value={f.noi_dung} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
            <div className="v3-actions"><Nut kieu="primary" i="send" disabled={busy || f.noi_dung.trim().length < 5} onClick={guiIr}>{busy ? "Đang gửi…" : "Gửi câu hỏi"}</Nut></div></section>
          <section className="v3-panel"><div className="v3-section-title"><h3>Câu hỏi của tôi</h3></div>
            {!ir ? <p>Đang tải…</p> : ir.yeu_cau.length ? <div className="v3-table-wrap"><table>
              <thead><tr><th scope="col">Mã</th><th scope="col">Câu hỏi</th><th scope="col">Trạng thái</th><th scope="col">Trả lời</th></tr></thead>
              <tbody>{ir.yeu_cau.map((y: any) => <tr key={y.ma}><th scope="row">{y.ma}<small>{ngay(y.luc)}</small></th>
                <td>{y.chu_de_ten}<small style={{ whiteSpace: "pre-wrap" }}>{y.noi_dung}</small></td>
                <td><Badge c={MAU_IR[y.trang_thai]}>{y.trang_thai_ten}</Badge></td>
                <td style={{ whiteSpace: "pre-wrap" }}>{y.tra_loi || y.ly_do_dong || "—"}{y.tra_loi_luc && <small>IR – Pháp chế · {ngay(y.tra_loi_luc)}</small>}</td></tr>)}</tbody></table></div>
              : <p>Chưa có câu hỏi nào.</p>}
            <small>IR chỉ trả lời bằng thông tin đã hoặc được phép công bố, như nhau với mọi cổ đông.</small></section>
        </>}

        {tab === "hotel" && <KhachSanOta ghiChu="Chưa có ưu đãi cổ đông cho phòng đặt qua OTA." />}
        {tab === "flight" && <VeMayBayOta />}
        <footer className="v3-bottom"><I n="shield-check" />Dữ liệu và yêu cầu được quản lý tập trung trong VTOS</footer>
      </main>
    </div>
  </section>);
}
