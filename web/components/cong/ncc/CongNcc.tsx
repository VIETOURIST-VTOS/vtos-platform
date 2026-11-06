"use client";
/* NCC-1 · CỔNG NHÀ CUNG CẤP (Chủ tịch duyệt bản xem thử 28/10/2026; màn N01–N18 bộ v3.2).
   · Chưa nối vào danh mục NCC: chỉ «Đang chờ nối hồ sơ», không số liệu nào.
   · Đơn: chỉ đơn của mình, không thấy tên / SĐT khách. Xác nhận → đơn đổi ngay sang «NCC đã xác nhận».
   · Giá: chỉ đề xuất; Điều hành duyệt mới áp dụng. Công nợ hai chiều không bù trừ; chiều NCC trả chưa có nguồn.
   · Bản kê: xác nhận hoặc báo chênh lệch từng dòng; đã xác nhận thì khóa. Đổi TK: quy trình hai người. */
import { useCallback, useEffect, useState } from "react";
import { goiCong, phienCong } from "@/lib/cong";
import { svg } from "../khach/icons";

type Tab = "home" | "gia" | "don" | "dat_ban" | "dg" | "dgks" | "no" | "bk" | "dn" | "hs" | "nh" | "hl";
const I = ({ n }: { n: string }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n) }} />;
const tien = (n?: number | null) => (n == null ? "—" : `${Math.round(n).toLocaleString("vi-VN")} đ`);
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
function Badge({ c, children }: { c?: string; children: any }) { return <span className={`v3-badge ${c || "neutral"}`}>{children}</span>; }
function Nut({ i, children, kieu = "secondary", ...p }: any) {
  return <button type="button" className={`v3-button v3-${kieu} cursor-interaction`} {...p}>{i && <I n={i} />}<span>{children}</span></button>;
}
const MAU: Record<string, string> = { da_gui: "warn", da_xac_nhan: "good", da_su_dung: "good", huy: "neutral", cho: "warn", duyet: "good", tu_choi: "warn",
  cho_ncc: "warn", co_chenh_lech: "warn", da_xac_nhan_bk: "good", moi: "warn", dang_xu_ly: "warn", xong: "good", nhan: "good" };
// DT-2: nhà hàng nhận bàn → khách trả trước qua Vietourist → ăn xong nhà hàng báo «Khách đã dùng» kèm bill.

/** Gửi form (có tệp) lên cổng — goiCong chỉ gửi JSON. */
async function guiForm(path: string, f: Record<string, any>) {
  const fd = new FormData();
  Object.entries(f).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== "") fd.append(k, v as any); });
  const r = await fetch(`/api/v1/cong${path}`, { method: "POST", headers: { Authorization: `Bearer ${phienCong()}` }, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw new Error(typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}`);
  return d;
}
async function moTep(path: string, ten: string) {
  const r = await fetch(`/api/v1/cong${path}`, { headers: { Authorization: `Bearer ${phienCong()}` } });
  if (!r.ok) throw new Error(`Lỗi ${r.status}`);
  const u = URL.createObjectURL(await r.blob()); const a = document.createElement("a"); a.href = u; a.download = ten;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 2000);
}

export default function CongNcc({ toi, thoat }: { toi: any; thoat: () => void }) {
  const [tab, setTab] = useState<Tab>("home");
  const [menuMo, setMenuMo] = useState(false);
  const [blv, setBlv] = useState<any>(null);
  const [cho, setCho] = useState("");
  const [d, setD] = useState<Record<string, any>>({});
  const [don, setDon] = useState<any>(null);
  const [f, setF] = useState<Record<string, any>>({});
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const loi = (x: any) => setErr(x.message || String(x));
  const taiBlv = useCallback(() => goiCong("/ncc/ban-lam-viec").then(setBlv).catch((x) => { if (x.status === 409 || x.status === 403) setCho(x.message); else loi(x); }), []);
  useEffect(() => { taiBlv(); }, [taiBlv]);
  const NGUON: Record<string, string> = { gia: "/ncc/gia", don: "/ncc/don", dat_ban: "/ncc/dat-ban", dg: "/ncc/danh-gia", dgks: "/ncc/danh-gia-ks", no: "/ncc/cong-no", bk: "/ncc/ban-ke", dn: "/ncc/de-nghi", hs: "/ncc/ho-so", nh: "/ncc/ho-so", hl: "/ncc/hoc-lieu" };
  const tai = (t: Tab) => { const p = NGUON[t]; if (p) goiCong(p).then((r) => setD((o) => ({ ...o, [t]: r }))).catch(loi); };
  const di = (t: Tab) => { setTab(t); setMenuMo(false); setMsg(""); setErr(""); setDon(null); setF({}); if (t === "home") taiBlv(); else tai(t); window.scrollTo(0, 0); };
  const chay = async (fn: () => Promise<any>, sau?: (r: any) => void) => {
    setBusy(true); setErr(""); setMsg("");
    try { const r = await fn(); setMsg(r.message); sau?.(r); } catch (x) { loi(x); } finally { setBusy(false); }
  };
  const nhaHang = !!blv?.la_nha_hang;
  const khachSan = !!blv?.la_khach_san;   // KS-15: NCC gắn với khách sạn VTD → tab đánh giá khách sạn
  const MENU: [Tab, string, string][] = [["home", "Bàn làm việc", "house"], ["gia", nhaHang ? "Thực đơn & giá" : "Dịch vụ & giá", "tickets"],
    ["don", "Đơn dịch vụ", "receipt"], ...(nhaHang ? [["dat_ban", "Đơn đặt bàn", "utensils"], ["dg", "Đánh giá của khách", "badge-check"]] as [Tab, string, string][] : []),
    ...(khachSan ? [["dgks", "Đánh giá khách sạn", "badge-check"]] as [Tab, string, string][] : []),
    ["no", "Công nợ", "badge-check"], ["bk", "Đối soát", "check"], ["dn", "Đề nghị", "send"], ["hs", "Hợp đồng & hồ sơ", "file-text"],
    ["nh", "Thành viên & ngân hàng", "users"], ["hl", "Học liệu", "info"]];
  const nhan = MENU.find(([k]) => k === tab)?.[1] || "";
  const ten = blv?.ncc?.ten || toi.ten_don_vi || toi.ho_ten || "Nhà cung cấp";

  if (cho) return (<section className="v3-app" data-portal="doi-tac">
    <header className="v3-topbar"><span className="v3-brand">{/* eslint-disable-next-line @next/next/no-img-element */}<img className="logo-v2" src="/thuong-hieu/v2/khoachu-holdings-nen-trong.svg" alt="Vietourist Holdings" width={1107} height={269} /></span>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button></header>
    <main className="v3-main" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng nhà cung cấp</div><h1>Xin chào, {toi.ten_don_vi || toi.ho_ten || "đối tác"}</h1></div></div>
      <section className="v3-panel"><div className="v3-section-title"><h3>Đang chờ nối hồ sơ</h3><Badge c="demo">Chờ Vietourist</Badge></div>
        <p>{cho}</p><p className="v3-small">Liên hệ đăng nhập: {toi.dien_thoai || toi.email}.</p>
        <div className="v3-actions"><Nut i="log-out" onClick={thoat}>Đăng xuất</Nut></div></section></main></section>);

  const Bang = ({ cot, children }: { cot: string[]; children: any }) => <div className="v3-table-wrap"><table><thead><tr>{cot.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead><tbody>{children}</tbody></table></div>;
  const o = (k: string, nhan: string, kieu = "text", ph = "") => <label className="v3-field">{nhan}<input type={kieu} value={f[k] ?? ""} placeholder={ph} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  const tep = (k = "tep", nhan = "Tệp (PDF / ảnh)") => <label className="v3-field">{nhan}<input type="file" accept=".pdf,image/*" onChange={(e) => setF({ ...f, [k]: e.target.files?.[0] || null })} /></label>;

  return (<section className="v3-app" data-portal="doi-tac">
    <header className="v3-topbar">
      <button type="button" className="v3-brand cursor-interaction" onClick={() => di("home")}>{/* eslint-disable-next-line @next/next/no-img-element */}<img className="logo-v2" src="/thuong-hieu/v2/khoachu-holdings-nen-trong.svg" alt="Vietourist Holdings" width={1107} height={269} /></button>
      <nav aria-label="Cổng"><button type="button" aria-pressed="true"><I n="building-2" /><span>Nhà cung cấp</span></button></nav>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button>
    </header>
    <div className="v3-mobile-nav"><Nut i="menu" onClick={() => setMenuMo(!menuMo)}>Danh mục chức năng</Nut><strong>{nhan}</strong></div>
    <div className="v3-layout">
      <aside className={`v3-sidebar ${menuMo ? "open" : ""}`}>
        <div className="v3-side-profile"><span className="v3-avatar"><I n="building-2" /></span><strong>{ten}</strong><small>{blv ? `${blv.ncc.code} · ${blv.ncc.loai_ten}` : "…"}</small></div>
        <nav aria-label="Chức năng nhà cung cấp">{MENU.map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={tab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
        <div className="v3-side-bottom"><Nut kieu="quiet" i="log-out" onClick={thoat}>Đăng xuất</Nut></div>
      </aside>
      <main className="v3-main">
        <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng nhà cung cấp · {ten}</div><h1>{nhan}</h1></div></div>
        {msg && <div className="v3-notice info"><I n="check" /><span>{msg}</span></div>}
        {err && <div className="v3-notice warn"><I n="info" /><span>{err}</span></div>}
        {!blv && !err && <section className="v3-panel"><p>Đang tải…</p></section>}

        {blv && tab === "home" && <>
          <section className="v3-hero"><div><span className="v3-eyebrow">KẾT NỐI CÙNG VIETOURIST</span><h2>Rõ việc cần làm.<br />Rõ từng khoản thanh toán.</h2><p>{ten} · {blv.ncc.code}</p></div>
            <div className="v3-hero-art" aria-hidden="true"><I n="handshake" /></div></section>
          <div className="v3-metrics">
            <section><span><I n="receipt" />Đơn chờ bạn xác nhận</span><strong>{blv.don_cho}</strong><small>Phản hồi trước lịch phục vụ</small>
              <Nut kieu="primary" onClick={() => di("don")}>Xem đơn</Nut></section>
            {blv.la_nha_hang && <section><span><I n="utensils" />Đặt bàn chờ nhận</span><strong>{blv.dat_ban_cho}</strong><small>Khách đặt qua Vietourist</small>
              <Nut kieu="primary" onClick={() => di("dat_ban")}>Xem</Nut></section>}
            <section><span><I n="tickets" />Đề xuất giá chờ duyệt</span><strong>{blv.de_xuat_cho}</strong><small>Điều hành duyệt mới áp dụng</small></section>
            <section><span><I n="send" />Đề nghị đang xử lý</span><strong>{blv.de_nghi_mo}</strong><small>Theo dõi ở mục Đề nghị</small></section>
          </div>
          <div className="v3-metrics">
            <section><span><I n="arrow-left" />Vietourist phải trả bạn</span><strong>{tien(blv.vtd_phai_tra)}</strong><small>Đơn đã xác nhận / đã dùng chưa chi</small></section>
            <section><span><I n="arrow-right" />Bạn phải trả Vietourist</span><strong>Chưa có nguồn</strong><small>Không hiện là 0 · không tự bù trừ</small></section>
            <section><span><I n="check" />Bản kê</span><strong>{blv.ban_ke_cho ? blv.ban_ke_cho.ky.split("-").reverse().join("/") : "Không có"}</strong>
              <small>{blv.ban_ke_cho ? blv.ban_ke_cho.trang_thai_ten : "Kế toán gửi theo kỳ"}</small></section>
          </div>
        </>}

        {tab === "gia" && d.gia && <>
          {!nhaHang ? <section className="v3-panel"><div className="v3-section-title"><h3>Giá, chỗ và ngày không phục vụ (đang áp dụng)</h3></div>
            {d.gia.gia.length ? <Bang cot={["Dịch vụ", "Giá mua", "Số lượng mở", "Hiệu lực", ""]}>{d.gia.gia.map((g: any) => <tr key={g.id}>
              <th scope="row">{g.dich_vu}<small>{g.don_vi}</small></th><td>{tien(g.gia)}</td><td>{g.so_luong_mo ?? "—"}</td>
              <td>{ngay(g.tu_ngay) || "—"} – {ngay(g.den_ngay) || "—"}{g.ngay_khong_phuc_vu && <small>không phục vụ {g.ngay_khong_phuc_vu}</small>}</td>
              <td><Nut kieu="quiet" onClick={() => setF({ loai: "gia", gia_ncc_id: g.id, dich_vu: g.dich_vu, gia: g.gia, so_luong_mo: g.so_luong_mo ?? "" })}>Đề xuất sửa</Nut></td></tr>)}</Bang>
              : <p>Chưa có giá nào được duyệt. Gửi đề xuất bên dưới — Điều hành duyệt mới áp dụng.</p>}</section>
          : <section className="v3-panel"><div className="v3-section-title"><h3>Thực đơn đang bán</h3></div>
            {d.gia.thuc_don.length ? <Bang cot={["Thực đơn", "Người lớn", "Trẻ em", "Hiệu lực", ""]}>{d.gia.thuc_don.map((t: any) => <tr key={t.id}>
              <th scope="row">{t.ten}<small>{t.nha_hang}{t.dang_ban ? "" : " · đang tắt"}</small></th><td>{tien(t.gia_nguoi_lon)}</td><td>{tien(t.gia_tre_em)}</td>
              <td>{ngay(t.tu_ngay) || "—"} – {ngay(t.den_ngay) || "—"}</td>
              <td><Nut kieu="quiet" onClick={() => setF({ loai: "thuc_don", thuc_don_id: t.id, dich_vu: t.ten, gia: t.gia_nguoi_lon ?? "", gia_tre_em: t.gia_tre_em ?? "" })}>Đề xuất sửa</Nut></td></tr>)}</Bang>
              : <p>Chưa có thực đơn.</p>}</section>}
          <section className="v3-panel"><div className="v3-section-title"><h3>{f.gia_ncc_id || f.thuc_don_id ? `Đề xuất cập nhật · ${f.dich_vu}` : nhaHang ? "Đề xuất thực đơn mới" : "Đề xuất dịch vụ / giá mới"}</h3></div>
            <div className="v3-form-grid">
              {!(f.gia_ncc_id || f.thuc_don_id) && o("dich_vu", nhaHang ? "Tên thực đơn" : "Dịch vụ", "text", nhaHang ? "Set Hương Việt" : "Phòng Deluxe")}
              {!nhaHang && !f.gia_ncc_id && o("don_vi", "Đơn vị", "text", "đêm, khách, xe…")}
              {nhaHang && !f.thuc_don_id && <label className="v3-field">Nhà hàng<select value={f.nha_hang_id ?? ""} onChange={(e) => setF({ ...f, nha_hang_id: e.target.value })}>
                <option value="">— chọn —</option>{d.gia.nha_hang.map((n: any) => <option key={n.id} value={n.id}>{n.ten}</option>)}</select></label>}
              {o("gia", nhaHang ? "Giá người lớn (đ)" : "Giá đề xuất (đ)", "number")}
              {nhaHang ? o("gia_tre_em", "Giá trẻ em (đ)", "number") : o("so_luong_mo", "Số lượng mở", "number")}
              {o("tu_ngay", "Từ ngày", "date")}{o("den_ngay", "Đến ngày", "date")}
              {!nhaHang && o("ngay_khong_phuc_vu", "Ngày không phục vụ", "text", "24/12, 31/12")}
            </div>
            <label className="v3-field">Ghi chú<textarea rows={2} value={f.ghi_chu ?? ""} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
            <div className="v3-actions"><Nut kieu="primary" i="send" disabled={busy || !Number(f.gia)} onClick={() => chay(() => goiCong("/ncc/de-xuat", {
              loai: nhaHang ? "thuc_don" : "gia", gia_ncc_id: f.gia_ncc_id || null, thuc_don_id: f.thuc_don_id || null, nha_hang_id: f.nha_hang_id ? Number(f.nha_hang_id) : null,
              dich_vu: f.dich_vu || "", don_vi: f.don_vi || "", gia: Number(f.gia), gia_tre_em: f.gia_tre_em ? Number(f.gia_tre_em) : null,
              so_luong_mo: f.so_luong_mo !== undefined && f.so_luong_mo !== "" ? Number(f.so_luong_mo) : null, tu_ngay: f.tu_ngay || null, den_ngay: f.den_ngay || null,
              ngay_khong_phuc_vu: f.ngay_khong_phuc_vu || "", ghi_chu: f.ghi_chu || "" }), (r) => { setD((x) => ({ ...x, gia: r })); setF({}); })}>Gửi Điều hành duyệt</Nut>
              {(f.gia_ncc_id || f.thuc_don_id) && <Nut kieu="quiet" onClick={() => setF({})}>Thôi</Nut>}</div>
            <small>Điều hành duyệt mới áp dụng. Không đổi giá trên đơn đã đặt.</small></section>
          <section className="v3-panel"><div className="v3-section-title"><h3>Đề xuất đã gửi</h3></div>
            {d.gia.de_xuat.length ? <Bang cot={["Dịch vụ", "Giá", "Hiệu lực", "Trạng thái"]}>{d.gia.de_xuat.map((x: any) => <tr key={x.id}>
              <th scope="row">{x.dich_vu}<small>{ngay(x.luc)}</small></th><td>{tien(x.gia)}{x.gia_tre_em != null && <small>trẻ em {tien(x.gia_tre_em)}</small>}</td>
              <td>{ngay(x.tu_ngay) || "—"} – {ngay(x.den_ngay) || "—"}</td><td><Badge c={MAU[x.trang_thai]}>{x.trang_thai_ten}</Badge>{x.ly_do && <small>{x.ly_do}</small>}</td></tr>)}</Bang>
              : <p>Chưa gửi đề xuất nào.</p>}</section>
          {!nhaHang && d.gia.loai_ncc !== "khac" && <section className="v3-panel"><div className="v3-section-title"><h3>Dịch vụ chưa được cấp</h3></div>
            <p>Tài khoản này được cấp nhóm «{blv?.ncc?.loai_ten}». Muốn mở thêm nhóm dịch vụ khác, gửi đề nghị «Hợp tác / hỗ trợ».</p></section>}
        </>}

        {tab === "don" && d.don && !don && <section className="v3-panel"><div className="v3-section-title"><h3>Đơn dịch vụ Vietourist gửi bạn</h3><Badge>{d.don.don.length}</Badge></div>
          {d.don.don.length ? <Bang cot={["Mã · dịch vụ", "Ngày · số lượng", "Giá trị", "Trạng thái", ""]}>{d.don.don.map((x: any) => <tr key={x.id}>
            <th scope="row">{x.code}<small>{x.noi_dung}{x.tour ? ` · đoàn ${x.tour}` : ""}</small></th><td>{ngay(x.ngay_su_dung)}<small>{x.so_luong} {x.don_vi}</small></td>
            <td>{tien(x.thanh_tien)}</td><td><Badge c={MAU[x.status]}>{x.status_ten}</Badge></td>
            <td><Nut kieu="quiet" i="chevron-right" onClick={() => goiCong(`/ncc/don/${x.id}`).then((r) => { setDon(r); setF({}); }).catch(loi)}>Xem</Nut></td></tr>)}</Bang>
            : <p>Chưa có đơn nào.</p>}</section>}
        {tab === "don" && don && <section className="v3-panel">
          <div className="v3-section-title"><h3>{don.code}</h3><Badge c={MAU[don.status]}>{don.status_ten}</Badge></div>
          <Bang cot={["", ""]}>
            <tr><th scope="row">Dịch vụ</th><td>{don.noi_dung}</td></tr>
            <tr><th scope="row">Đoàn</th><td>{don.tour || "—"}{don.so_khach_doan ? ` · ${don.so_khach_doan} khách` : ""} (không hiện tên khách)</td></tr>
            <tr><th scope="row">Ngày · số lượng</th><td>{ngay(don.ngay_su_dung)} · {don.so_luong} {don.don_vi}</td></tr>
            <tr><th scope="row">Đơn giá · thành tiền</th><td>{tien(don.don_gia)} · {tien(don.thanh_tien)}</td></tr>
            {don.xac_nhan_ncc && <tr><th scope="row">Xác nhận</th><td>{don.xac_nhan_ncc}</td></tr>}
            <tr><th scope="row">Thanh toán</th><td>{don.da_chi ? `Đã chi · ${don.phieu_chi}` : don.phieu_chi ? `Đề nghị chi ${don.phieu_chi}` : "Chưa lập đề nghị chi"}</td></tr>
          </Bang>
          {don.status === "da_gui" && <div className="v3-form-grid">{o("ma", "Mã / số xác nhận của bạn", "text", "BX-77821")}{o("ghi_chu", "Ghi chú / lý do từ chối")}</div>}
          {don.status !== "da_gui" && o("ghi_chu", "Ghi chú kèm chứng từ")}
          {tep()}
          <div className="v3-actions">
            {don.status === "da_gui" && <><Nut kieu="primary" i="check" disabled={busy || !f.ma} onClick={() => chay(() => guiForm(`/ncc/don/${don.id}`, { hanh_dong: "xac_nhan", ma: f.ma, ghi_chu: f.ghi_chu }), (r) => { setDon(r.don); tai("don"); })}>Xác nhận đơn</Nut>
              <Nut i="x" disabled={busy || !(f.ghi_chu || "").trim()} onClick={() => chay(() => guiForm(`/ncc/don/${don.id}`, { hanh_dong: "tu_choi", ghi_chu: f.ghi_chu }), (r) => { setDon(r.don); tai("don"); })}>Từ chối có lý do</Nut></>}
            <Nut i="file-text" disabled={busy || !f.tep} onClick={() => chay(() => guiForm(`/ncc/don/${don.id}`, { hanh_dong: "chung_tu", ghi_chu: f.ghi_chu, tep: f.tep }), (r) => setDon(r.don))}>Gửi chứng từ</Nut>
            <Nut kieu="quiet" i="arrow-left" onClick={() => { setDon(null); tai("don"); }}>Quay lại</Nut></div>
          {don.phan_hoi?.length > 0 && <><h4 style={{ margin: "8px 0 4px" }}>Lịch sử phản hồi</h4><ul>{don.phan_hoi.map((p: any, i: number) =>
            <li key={i}>{ngay(p.luc)} · {p.hanh_dong === "xac_nhan" ? `Xác nhận ${p.ma_xac_nhan}` : p.hanh_dong === "tu_choi" ? `Từ chối: ${p.ghi_chu}` : `Chứng từ${p.ghi_chu ? `: ${p.ghi_chu}` : ""}`}{p.xu_ly_luc ? " · Điều hành đã xử lý" : ""}</li>)}</ul></>}
          <small>Xác nhận → đơn trong VTOS đổi ngay sang «NCC đã xác nhận». Từ chối → Điều hành xử lý, đơn giữ nguyên.</small></section>}

        {tab === "dat_ban" && d.dat_ban && <section className="v3-panel"><div className="v3-section-title"><h3>Đơn đặt bàn</h3></div>
          {d.dat_ban.dat_ban.length ? <Bang cot={["Mã · thực đơn", "Ngày giờ", "Khách", "Thanh toán", "Trạng thái", ""]}>{d.dat_ban.dat_ban.map((x: any) => <tr key={x.id}>
            <th scope="row">{x.ma_don || x.ma}<small>{x.nha_hang} · {x.thuc_don}{x.la_doan ? " · đoàn" : ""}</small></th><td>{ngay(x.ngay)} {x.gio}</td>
            <td>{x.nguoi_lon} NL{x.tre_em ? ` + ${x.tre_em} TE` : ""}{x.ghi_chu && <small>{x.ghi_chu}</small>}</td>
            <td>{x.ma_don ? <>{x.cach_tt_ten} · {tien(x.phai_tra_truoc)}<small>Vietourist đã thu {tien(x.da_tra_vtd)} · thu tại bàn ~{tien(x.thu_tai_ban_du_kien)}</small>
              {x.bill_thuc_te != null && <small>Bill {tien(x.bill_thuc_te)} · đã thu tại bàn {tien(x.thu_tai_ban)}</small>}</> : "Yêu cầu cũ · Sales xử lý"}</td>
            <td><Badge c={MAU[x.trang_thai]}>{x.trang_thai_ten}</Badge>{x.tt_don_ten && <small>{x.tt_don_ten}</small>}{x.ghi_chu_nh && <small>{x.ghi_chu_nh}</small>}</td>
            <td>{x.trang_thai === "cho" && <div style={{ display: "grid", gap: 4 }}>
              <Nut kieu="primary" disabled={busy} onClick={() => chay(() => goiCong(`/ncc/dat-ban/${x.id}`, { nhan: true, ghi_chu: f[`g${x.id}`] || "" }), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Nhận bàn</Nut>
              <input placeholder="Lý do từ chối" value={f[`g${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`g${x.id}`]: e.target.value })} />
              <Nut disabled={busy || !(f[`g${x.id}`] || "").trim()} onClick={() => chay(() => goiCong(`/ncc/dat-ban/${x.id}`, { nhan: false, ghi_chu: f[`g${x.id}`] }), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Từ chối</Nut></div>}
              {x.thay_doi && <div style={{ display: "grid", gap: 4 }}>
                <small><b>Khách đề nghị đổi:</b> {ngay(x.thay_doi.ngay)} {x.thay_doi.gio} · {x.thay_doi.nguoi_lon} NL{x.thay_doi.tre_em ? ` + ${x.thay_doi.tre_em} TE` : ""}</small>
                <Nut kieu="primary" disabled={busy} onClick={() => chay(() => goiCong(`/ncc/dat-ban/${x.id}/thay-doi`, { nhan: true, ghi_chu: "" }), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Nhận thay đổi</Nut>
                <input placeholder="Lý do từ chối thay đổi" value={f[`d${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`d${x.id}`]: e.target.value })} />
                <Nut disabled={busy || !(f[`d${x.id}`] || "").trim()} onClick={() => chay(() => goiCong(`/ncc/dat-ban/${x.id}/thay-doi`, { nhan: false, ghi_chu: f[`d${x.id}`] }), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Từ chối thay đổi</Nut></div>}
              {x.thay_doi_ghi_chu && <small>{x.thay_doi_ghi_chu}</small>}
              {x.bao_dung_duoc && <div style={{ display: "grid", gap: 4 }}>
                <input type="number" placeholder="Bill thực tế (đ)" value={f[`b${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`b${x.id}`]: e.target.value })} />
                <input type="number" placeholder="Đã thu tại bàn (đ)" value={f[`t${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`t${x.id}`]: e.target.value })} />
                <input type="file" accept=".pdf,image/*" aria-label="Ảnh bill" onChange={(e) => setF({ ...f, [`f${x.id}`]: e.target.files?.[0] || null })} />
                <Nut kieu="primary" disabled={busy || !Number(f[`b${x.id}`]) || f[`t${x.id}`] === undefined || f[`t${x.id}`] === ""} onClick={() => chay(() => guiForm(`/ncc/dat-ban/${x.id}/da-dung`,
                  { bill: f[`b${x.id}`], thu_tai_ban: f[`t${x.id}`], tep: f[`f${x.id}`] }), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Khách đã dùng</Nut>
                {x.bao_khong_den_duoc && <Nut disabled={busy} onClick={() => chay(() => goiCong(`/ncc/dat-ban/${x.id}/khong-den`, {}), (r) => setD((o2) => ({ ...o2, dat_ban: r })))}>Khách không đến</Nut>}</div>}</td></tr>)}</Bang>
            : <p>Chưa có đơn đặt bàn nào.</p>}
          <small>Bạn thấy số khách, giờ, thực đơn; không thấy số điện thoại khách. Nhận bàn xong khách mới thanh toán trước qua Vietourist; ăn xong thu phần còn lại tại bàn rồi bấm «Khách đã dùng» kèm bill. Không đến quá 30 phút: bấm «Khách không đến» — tiền giữ theo chính sách thuộc nhà hàng.</small></section>}

        {tab === "dg" && d.dg && <section className="v3-panel">{/* AT-3 · nhà hàng trả lời công khai một lần, sửa trong 24 giờ */}
          <div className="v3-section-title"><h3>Đánh giá của khách{d.dg.nha_hang.length === 1 && d.dg.nha_hang[0].diem_tb != null ? ` · ${String(d.dg.nha_hang[0].diem_tb).replace(".", ",")}★ (${d.dg.nha_hang[0].so_bai} bài)` : ""}</h3></div>
          <p className="v3-small">Nhà hàng trả lời công khai, một lần mỗi bài (tối đa 600 ký tự), sửa được trong 24 giờ. Nhà hàng không ẩn, không sửa được bài của khách.</p>
          {d.dg.bai.length ? d.dg.bai.map((b: any) => <div key={b.id} className="v3-panel" style={{ marginTop: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
              <b>{b.ten} · {b.la_doan ? "Đoàn" : "Bàn"} {b.so_khach} người · {ngay(b.ngay_an)}{d.dg.nha_hang.length > 1 ? ` · ${b.nha_hang}` : ""}</b>
              <span style={{ color: b.diem <= 2 ? "#8a1f1f" : "#b07a10", letterSpacing: 2 }} aria-label={`${b.diem} sao`}>{"★★★★★".slice(0, b.diem)}<span style={{ color: "#c9d3dc" }}>{"★★★★★".slice(b.diem)}</span></span></div>
            {b.nhan_xet && <p style={{ margin: "6px 0", whiteSpace: "pre-line" }}>{b.nhan_xet}</p>}
            {b.anh.length > 0 && <div style={{ display: "flex", gap: 6 }}>{b.anh.map((a: any) => <img key={a.i} src={a.nho} alt="Ảnh khách" style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 6 }} />)}</div>}
            {b.tra_loi_bi_an && <small>Lời trả lời đã bị Vietourist ẩn vì vi phạm quy tắc.</small>}
            {(b.duoc_tra_loi || b.duoc_sua_tra_loi) ? <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
              <label className="v3-field">{b.duoc_sua_tra_loi ? "Sửa trả lời (trong 24 giờ)" : "Trả lời công khai"}
                <textarea rows={3} maxLength={600} value={f[`r${b.id}`] ?? b.tra_loi_cua_minh ?? ""} onChange={(e) => setF({ ...f, [`r${b.id}`]: e.target.value })} /></label>
              <div><Nut kieu="primary" disabled={busy || !(f[`r${b.id}`] ?? b.tra_loi_cua_minh ?? "").trim()} onClick={() => chay(() => goiCong(`/ncc/danh-gia/${b.id}/tra-loi`, { noi_dung: f[`r${b.id}`] ?? b.tra_loi_cua_minh }), (r) => setD((o2) => ({ ...o2, dg: r })))}>{b.duoc_sua_tra_loi ? "Lưu trả lời" : "Gửi trả lời"}</Nut></div></div>
              : b.tra_loi_cua_minh && !b.tra_loi_bi_an && <div style={{ background: "rgba(127,140,153,.12)", borderRadius: 8, padding: "8px 10px", marginTop: 6 }}><small><b>Nhà hàng đã trả lời:</b> {b.tra_loi_cua_minh}</small></div>}
          </div>) : <p>Chưa có đánh giá. Khách đặt bàn qua Vietourist và được nhà hàng báo «Khách đã dùng» mới viết được đánh giá.</p>}
          <small>Bạn thấy tên khách đã che như trên trang khách; không thấy số điện thoại hay mã đơn của người viết.</small></section>}

        {tab === "dgks" && d.dgks && <section className="v3-panel">{/* KS-15 · khách sạn trả lời công khai một lần, sửa trong 24 giờ */}
          <div className="v3-section-title"><h3>Đánh giá khách sạn{d.dgks.khach_san.length === 1 && d.dgks.khach_san[0].diem_tb != null ? ` · ${String(d.dgks.khach_san[0].diem_tb).replace(".", ",")}/10 (${d.dgks.khach_san[0].so_bai} bài)` : ""}</h3></div>
          <p className="v3-small">Khách sạn trả lời công khai, một lần mỗi bài (tối đa 600 ký tự), sửa được trong 24 giờ. Khách sạn không ẩn, không sửa được bài của khách.</p>
          {d.dgks.bai.length ? d.dgks.bai.map((b: any) => <div key={b.id} className="v3-panel" style={{ marginTop: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
              <b>{b.ten} · {b.loai_phong} · ở {b.thang_o}{d.dgks.khach_san.length > 1 ? ` · ${b.khach_san}` : ""}</b>
              <b style={{ color: b.diem <= 5 ? "#8a1f1f" : "#1f4fae" }}>{b.diem}/10</b></div>
            {b.tieu_de && <b style={{ display: "block", marginTop: 6 }}>{b.tieu_de}</b>}
            {b.nhan_xet && <p style={{ margin: "6px 0", whiteSpace: "pre-line" }}>{b.nhan_xet}</p>}
            {b.anh.length > 0 && <div style={{ display: "flex", gap: 6 }}>{b.anh.map((a: any) => <img key={a.i} src={a.nho} alt="Ảnh khách" style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 6 }} />)}</div>}
            {b.tra_loi_bi_an && <small>Lời trả lời đã bị Vietourist ẩn vì vi phạm quy tắc.</small>}
            {(b.duoc_tra_loi || b.duoc_sua_tra_loi) ? <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
              <label className="v3-field">{b.duoc_sua_tra_loi ? "Sửa trả lời (trong 24 giờ)" : "Trả lời công khai"}
                <textarea rows={3} maxLength={600} value={f[`k${b.id}`] ?? b.tra_loi_cua_minh ?? ""} onChange={(e) => setF({ ...f, [`k${b.id}`]: e.target.value })} /></label>
              <div><Nut kieu="primary" disabled={busy || !(f[`k${b.id}`] ?? b.tra_loi_cua_minh ?? "").trim()} onClick={() => chay(() => goiCong(`/ncc/danh-gia-ks/${b.id}/tra-loi`, { noi_dung: f[`k${b.id}`] ?? b.tra_loi_cua_minh }), (r) => setD((o2) => ({ ...o2, dgks: r })))}>{b.duoc_sua_tra_loi ? "Lưu trả lời" : "Gửi trả lời"}</Nut></div></div>
              : b.tra_loi_cua_minh && !b.tra_loi_bi_an && <div style={{ background: "rgba(127,140,153,.12)", borderRadius: 8, padding: "8px 10px", marginTop: 6 }}><small><b>Khách sạn đã trả lời:</b> {b.tra_loi_cua_minh}</small></div>}
          </div>) : <p>Chưa có đánh giá. Khách đặt phòng qua Vietourist, được xác nhận và đã ở mới viết được.</p>}
          <small>Bạn thấy tên khách đã che như trên trang khách; không thấy số điện thoại hay mã đơn của người viết.</small></section>}

        {tab === "no" && d.no && <>
          <div className="v3-metrics">
            <section><span>Vietourist phải trả bạn</span><strong>{tien(d.no.vtd_phai_tra)}</strong><small>Đơn đã xác nhận / đã dùng chưa chi</small></section>
            <section><span>Bạn phải trả Vietourist</span><strong>Chưa có nguồn</strong><small>Không hiện là 0</small></section></div>
          <section className="v3-panel"><div className="v3-section-title"><h3>Căn cứ</h3></div>
            {d.no.dong.length ? <Bang cot={["Đơn", "Ngày dùng", "Giá trị", "Thanh toán", "Còn"]}>{d.no.dong.map((x: any) => <tr key={x.code}>
              <th scope="row">{x.code}<small>{x.noi_dung}</small></th><td>{ngay(x.ngay_su_dung)}{x.ngay_den_han && <small>hạn trả {ngay(x.ngay_den_han)}</small>}</td>
              <td>{tien(x.gia_tri)}</td><td>{x.da_chi ? <Badge c="good">Đã chi · {x.phieu_chi}</Badge> : x.phieu_chi ? `${x.phieu_chi} (đang duyệt)` : "Chưa lập đề nghị chi"}</td>
              <td>{tien(x.con)}</td></tr>)}</Bang> : <p>Chưa có đơn đã xác nhận.</p>}
            <small>{d.no.ghi_chu}</small></section>
          {d.no.dat_ban_thu_ho?.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đặt bàn — Vietourist thu hộ</h3></div>
            <Bang cot={["Đơn", "Ngày", "Đã thu hộ", "Hoàn khách", "Thuộc nhà hàng"]}>{d.no.dat_ban_thu_ho.map((x: any) => <tr key={x.ma}>
              <th scope="row">{x.ma}<small>{x.nha_hang} · {x.trang_thai_ten}</small></th><td>{ngay(x.ngay)}</td><td>{tien(x.da_thu_ho)}</td><td>{tien(x.hoan_khach)}</td><td>{tien(x.thuoc_nha_hang)}{x.voucher_vtd ? <small>gồm voucher VTD trả thay khách {tien(x.voucher_vtd)}</small> : null}</td></tr>)}</Bang>
            <small>Tiền khách trả trước qua Vietourist. Vietourist chi cho nhà hàng theo đề nghị chi; trạng thái chi xem ở Đề nghị.</small></section>}</>}

        {tab === "bk" && d.bk && (d.bk.ban_ke.length ? d.bk.ban_ke.map((b: any) => <section key={b.id} className="v3-panel">
          <div className="v3-section-title"><h3>Bản kê {b.ma} · kỳ {b.ky.split("-").reverse().join("/")}</h3><Badge c={b.trang_thai === "da_xac_nhan" ? "good" : "warn"}>{b.trang_thai_ten}</Badge></div>
          <Bang cot={["Đơn", "Nội dung", "Giá trị", "Chênh lệch"]}>{b.dong.map((x: any) => <tr key={x.id}>
            <th scope="row">{x.ma_don}<small>{ngay(x.ngay)}</small></th><td>{x.noi_dung}</td><td>{tien(x.gia_tri)}</td>
            <td>{x.ncc_ghi_chu ? <><Badge c="warn">Bạn báo {tien(x.ncc_gia_tri)}</Badge><small>{x.ncc_ghi_chu}</small>{x.tra_loi && <small>Kế toán: {x.tra_loi}</small>}</>
              : b.trang_thai !== "da_xac_nhan" && <div style={{ display: "grid", gap: 4 }}>
                <input type="number" placeholder="Số bạn ghi nhận" value={f[`v${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`v${x.id}`]: e.target.value })} />
                <input placeholder="Căn cứ chênh lệch" value={f[`c${x.id}`] ?? ""} onChange={(e) => setF({ ...f, [`c${x.id}`]: e.target.value })} />
                <Nut kieu="quiet" disabled={busy || !(f[`c${x.id}`] || "").trim()} onClick={() => chay(() => goiCong(`/ncc/ban-ke/${b.id}/chenh-lech`, { dong_id: x.id, gia_tri: f[`v${x.id}`] ? Number(f[`v${x.id}`]) : null, ghi_chu: f[`c${x.id}`] }), (r) => setD((o2) => ({ ...o2, bk: r })))}>Gửi chênh lệch</Nut></div>}</td></tr>)}
            <tr><th scope="row">Tổng</th><td /><td><b>{tien(b.tong)}</b></td><td /></tr></Bang>
          {b.trang_thai !== "da_xac_nhan" && <div className="v3-actions"><Nut kieu="primary" i="check" disabled={busy} onClick={() => chay(() => goiCong(`/ncc/ban-ke/${b.id}/xac-nhan`, {}), (r) => setD((o2) => ({ ...o2, bk: r })))}>Xác nhận bản kê</Nut></div>}
          <small>Xác nhận bản kê không phải duyệt chi hay xác nhận tiền đã về. Đã xác nhận thì khóa; sai thì gửi đề nghị để Kế toán lập bản kê điều chỉnh.</small></section>)
          : <section className="v3-panel"><p>Chưa có bản kê nào. Kế toán gửi bản kê theo kỳ.</p></section>)}

        {tab === "dn" && d.dn && <>
          <section className="v3-panel"><div className="v3-section-title"><h3>Gửi đề nghị</h3></div>
            <div className="v3-form-grid">
              <label className="v3-field">Loại<select value={f.loai ?? "thanh_toan"} onChange={(e) => setF({ ...f, loai: e.target.value })}>
                {Object.entries(d.dn.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
              {o("so_tien", "Số tiền (nếu có)", "number")}</div>
            <label className="v3-field">Nội dung / căn cứ<textarea rows={3} value={f.noi_dung ?? ""} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
            {tep()}
            <div className="v3-actions"><Nut kieu="primary" i="send" disabled={busy || (f.noi_dung || "").trim().length < 5} onClick={() => chay(() => guiForm("/ncc/de-nghi", { loai: f.loai || "thanh_toan", so_tien: f.so_tien, noi_dung: f.noi_dung, tep: f.tep }), (r) => { setD((o2) => ({ ...o2, dn: { ...o2.dn, de_nghi: r.de_nghi } })); setF({}); })}>Gửi đề nghị</Nut></div>
            <small>Đề nghị không tự thành phiếu chi. Kế toán / Điều hành trả lời và lập đề nghị chi theo quy trình duyệt hiện hành.</small></section>
          <section className="v3-panel"><div className="v3-section-title"><h3>Theo dõi</h3></div>
            {d.dn.de_nghi.length ? <Bang cot={["Mã", "Loại", "Bộ phận", "Tiến độ"]}>{d.dn.de_nghi.map((x: any) => <tr key={x.id}>
              <th scope="row">{x.ma}<small>{ngay(x.luc)}{x.so_tien != null ? ` · ${tien(x.so_tien)}` : ""}</small></th><td>{x.loai_ten}<small>{x.noi_dung}</small></td><td>{x.bo_phan}</td>
              <td><Badge c={MAU[x.trang_thai]}>{x.trang_thai_ten}</Badge>{x.tra_loi && <small>«{x.tra_loi}»</small>}</td></tr>)}</Bang> : <p>Chưa gửi đề nghị nào.</p>}</section></>}

        {tab === "hs" && d.hs && <section className="v3-panel"><div className="v3-section-title"><h3>Thông tin hợp tác</h3></div>
          <Bang cot={["", ""]}>
            <tr><th scope="row">Tên giao dịch</th><td>{d.hs.ncc.ten}</td></tr>
            <tr><th scope="row">Tên pháp nhân</th><td>{d.hs.ncc.ten_phap_nhan || "—"}</td></tr>
            <tr><th scope="row">Mã số thuế</th><td>{d.hs.ncc.ma_so_thue || "—"}</td></tr>
            <tr><th scope="row">Điều khoản thanh toán</th><td>{d.hs.ncc.dieu_khoan_tt || "Theo hợp đồng"}</td></tr></Bang>
          <h4 style={{ margin: "8px 0 4px" }}>Hồ sơ đã gửi</h4>
          {d.hs.tep.length ? <ul>{d.hs.tep.map((t: any) => <li key={t.id}>{t.ten_tep} · {ngay(t.luc)}</li>)}</ul> : <p>Chưa có hồ sơ.</p>}
          {o("mo_ta", "Mô tả hồ sơ")}{tep("tep", "Tệp hồ sơ (hợp đồng, giấy phép…)")}
          <div className="v3-actions"><Nut i="file-text" disabled={busy || !f.tep} onClick={() => chay(() => guiForm("/ncc/ho-so", { mo_ta: f.mo_ta, tep: f.tep }), (r) => { setD((o2) => ({ ...o2, hs: r })); setF({}); })}>Bổ sung hồ sơ</Nut></div></section>}

        {tab === "nh" && d.nh && <>
          <section className="v3-panel"><div className="v3-section-title"><h3>Tài khoản nhận thanh toán</h3></div>
            <Bang cot={["", ""]}>
              <tr><th scope="row">Đang dùng</th><td>{d.nh.ngan_hang.so_tai_khoan || "—"} · {d.nh.ngan_hang.ngan_hang || "—"} · {d.nh.ngan_hang.chu_tai_khoan || "—"}</td></tr>
              <tr><th scope="row">Đề nghị đổi</th><td>{d.nh.ngan_hang.dang_cho_doi ? <Badge c="warn">Chờ người thứ hai xác nhận · chưa dùng để chi</Badge> : "Chưa có"}</td></tr></Bang>
            {!d.nh.ngan_hang.dang_cho_doi && <><div className="v3-form-grid">{o("so_tk", "Số tài khoản mới")}{o("ngan_hang", "Ngân hàng")}{o("chu_tk", "Chủ tài khoản")}{o("ly_do", "Lý do")}</div>
              {tep("tep", "Văn bản đề nghị đổi tài khoản (bắt buộc)")}
              <div className="v3-actions"><Nut i="shield-check" disabled={busy || !f.so_tk || !f.tep} onClick={() => chay(() => guiForm("/ncc/doi-tai-khoan", { so_tk: f.so_tk, ngan_hang: f.ngan_hang, chu_tk: f.chu_tk, ly_do: f.ly_do, tep: f.tep }), (r) => { setD((o2) => ({ ...o2, nh: r })); setF({}); })}>Đề nghị đổi tài khoản</Nut></div></>}
            <small>Tài khoản mới chỉ dùng sau khi Kế toán đề nghị và người thứ hai xác nhận. Phiếu đã duyệt không tự đổi người nhận.</small></section>
          <section className="v3-panel"><div className="v3-section-title"><h3>Thành viên</h3></div>
            <ul>{d.nh.thanh_vien.map((t: any, i: number) => <li key={i}>{t.ho_ten || "—"} · {t.lien_he}</li>)}</ul>
            <small>Thêm thành viên: người đó đăng ký tài khoản đối tác tại dt.vietourist.vn, TP Điều hành nối vào cùng nhà cung cấp.</small></section></>}

        {tab === "hl" && d.hl && <section className="v3-panel"><div className="v3-section-title"><h3>Học liệu & thương hiệu</h3></div>
          {d.hl.hoc_lieu.length ? <Bang cot={["Tài liệu", ""]}>{d.hl.hoc_lieu.map((h: any) => <tr key={h.id}>
            <th scope="row">{h.tieu_de}<small>{h.nhom_ten}</small></th>
            <td><Nut kieu="quiet" i="file-text" onClick={() => moTep(`/ncc/hoc-lieu/${h.id}/tep`, `${h.tieu_de}.pdf`).catch(loi)}>Tải</Nut></td></tr>)}</Bang>
            : <p>Chưa có học liệu.</p>}
          <small>Chỉ dùng giá và nội dung đã được duyệt. Thông tin khách chỉ dùng để phục vụ đơn được giao.</small></section>}

        <footer className="v3-bottom"><I n="shield-check" />Dữ liệu và yêu cầu được quản lý tập trung trong VTOS</footer>
      </main>
    </div>
  </section>);
}
