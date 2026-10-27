"use client";
/* DT-1 · CỔNG ĐỐI TÁC VTD — Đại lý và Cộng tác viên bán hàng (Chủ tịch duyệt bản xem thử 27/10/2026).
   Dựng bằng cùng lớp v3 của cổng khách (bộ giao diện v3.2, màn DL01–DL07, CTV01–CTV06).

   · Mọi số là số THẬT của đúng đối tác đã nối; chưa nối thì chỉ hiện «Đang chờ nối hồ sơ».
   · Đại lý giữ chỗ = booking thật, máy chủ kiểm như Điều hành tạo booking; không giảm giá trên cổng.
   · Công nợ hai chiều hiện riêng, KHÔNG bù trừ thành một số.
   · CTV không giữ chỗ, không thu tiền: giới thiệu khách thành nhu cầu cho Sales. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "../khach/icons";
import QrThanhToan from "../khach/QrThanhToan";
import KhachSanOta from "../KhachSanOta";

type Tab = "home" | "tour" | "hold" | "bookings" | "booking" | "d06" | "debt" | "refer" | "referrals";
const MENU_DL: [Tab, string, string][] = [["home", "Bàn làm việc", "house"], ["tour", "Tour & giữ chỗ", "plane"], ["bookings", "Đã giữ chỗ", "luggage"],
  ["d06", "Hoa hồng D06", "gift"], ["debt", "Công nợ", "receipt"]];
const MENU_CTV: [Tab, string, string][] = [["home", "Bàn làm việc", "house"], ["refer", "Giới thiệu khách", "user-plus"],
  ["referrals", "Nhu cầu đã gửi", "send"], ["d06", "Hoa hồng D06", "gift"]];

const I = ({ n, s }: { n: string; s?: number }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n, s) }} />;
const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const trieu = (n: number) => `${(n / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr`;
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const gio = (s?: string | null) => (s ? `${ngay(s)} ${s.slice(11, 16)}` : "");
const thang = (k: string) => k.split("-").reverse().join("/");
const conGio = (h?: number | null) => (h == null ? "" : h <= 0 ? "đã quá hạn" : h < 24 ? `còn ${Math.max(1, Math.round(h))} giờ` : `còn ${Math.round(h / 24)} ngày`);
function Badge({ c, children }: { c?: string; children: any }) { return <span className={`v3-badge ${c || "neutral"}`}>{children}</span>; }
function Nut({ i, children, kieu = "secondary", ...p }: any) {
  return <button type="button" className={`v3-button v3-${kieu} cursor-interaction`} {...p}>{i && <I n={i} />}<span>{children}</span></button>;
}

function BacD06({ hh }: { hh: any }) {
  if (!hh?.bac?.length) return <p>Chưa chọn hình thức hoa hồng D06 — Vietourist sẽ cấu hình theo hợp đồng.</p>;
  const ht = hh.bac_hien_tai;
  return (<div className="v3-metrics">{hh.bac.map(([tu, den, bps]: number[]) => {
    const dang = !!ht && ht.bps === bps;
    return <section key={tu} style={dang ? { outline: "2px solid #c99a2e" } : undefined}><span>{den ? `${trieu(tu)} – ${trieu(den)}` : `từ ${trieu(tu)}`}</span>
      <strong>{(bps / 100).toLocaleString("vi-VN")}%</strong><small>{dang ? "bạn đang ở đây" : "phần doanh số trong khoảng"}</small></section>;
  })}</div>);
}

export default function DoiTac({ toi, thoat }: { toi: any; thoat: () => void }) {
  const [tab, setTab] = useState<Tab>("home");
  const [menuMo, setMenuMo] = useState(false);
  const [blv, setBlv] = useState<any>(null);
  const [cho, setCho] = useState<string>("");
  const [ds, setDs] = useState<any>(null);
  const [q, setQ] = useState("");
  const [dv, setDv] = useState<"tour" | "khach_san">("tour");
  const [tourMo, setTourMo] = useState<any>(null);
  const [f, setF] = useState({ ten_khach: "", dien_thoai: "", nguoi_lon: 2, tre_em: 0, ghi_chu: "" });
  const [bk, setBk] = useState<any>(null);
  const [bkMo, setBkMo] = useState<any>(null);
  const [hh, setHh] = useState<any>(null);
  const [no, setNo] = useState<any>(null);
  const [gt, setGt] = useState<any>(null);
  const [g, setG] = useState({ tour_id: "", ten_khach: "", dien_thoai: "", so_khach: 2, ghi_chu: "", dong_y: false });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  const ctv = !!blv?.ctv;
  const MENU = ctv ? MENU_CTV : MENU_DL;
  const di = useCallback((t: Tab) => { setTab(t); setMenuMo(false); setMsg(""); setErr(""); window.scrollTo(0, 0); }, []);
  const taiBlv = useCallback(() => goiCong("/doi-tac/ban-lam-viec").then(setBlv).catch((x) => { if (x.status === 403) setCho(x.message); else setErr(x.message); }), []);
  useEffect(() => { taiBlv(); }, [taiBlv]);
  const timTour = useCallback((k = q) => goiCong(`/doi-tac/tour${k ? `?q=${encodeURIComponent(k)}` : ""}`).then(setDs).catch((x) => setErr(x.message)), [q]);
  useEffect(() => {
    if (!blv) return;
    if ((tab === "tour" || tab === "refer") && !ds) timTour();
    if ((tab === "bookings" || tab === "booking") && !bk) goiCong("/doi-tac/booking").then(setBk).catch((x) => setErr(x.message));
    if (tab === "d06" && !hh) goiCong("/doi-tac/hoa-hong").then(setHh).catch((x) => setErr(x.message));
    if (tab === "debt" && !no) goiCong("/doi-tac/cong-no").then(setNo).catch((x) => setErr(x.message));
    if (tab === "referrals" && !gt) goiCong("/doi-tac/gioi-thieu").then(setGt).catch((x) => setErr(x.message));
  }, [tab, blv, ds, bk, hh, no, gt, timTour]);

  const moGiu = (t: any) => { setTourMo(t); setF({ ten_khach: "", dien_thoai: "", nguoi_lon: 2, tre_em: 0, ghi_chu: "" }); di("hold"); };
  const giu = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await goiCong("/doi-tac/giu-cho", { tour_id: tourMo.id, ...f, nguoi_lon: Number(f.nguoi_lon), tre_em: Number(f.tre_em) });
      setDs(null); setNo(null); const b = await goiCong("/doi-tac/booking"); setBk(b); taiBlv();
      setBkMo(b.booking.find((x: any) => x.ma === r.ma) || null); di(b.booking.find((x: any) => x.ma === r.ma) ? "booking" : "bookings"); setMsg(r.message);
    } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  const guiGt = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await goiCong("/doi-tac/gioi-thieu", { ...g, tour_id: g.tour_id ? Number(g.tour_id) : null, so_khach: Number(g.so_khach) });
      setGt(null); taiBlv(); setG({ tour_id: "", ten_khach: "", dien_thoai: "", so_khach: 2, ghi_chu: "", dong_y: false }); di("referrals"); setMsg(r.message);
    } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  const tamTinh = tourMo ? tourMo.gia * Number(f.nguoi_lon || 0) + (tourMo.gia_tre_em || tourMo.gia) * Number(f.tre_em || 0) : 0;
  const menuTab: Tab = tab === "hold" ? "tour" : tab === "booking" ? "bookings" : tab;
  const nhanMenu = MENU.find(([k]) => k === menuTab)?.[1] || (tab === "hold" ? "Giữ chỗ" : "");
  const ten = blv?.doi_tac?.ten || toi.ten_don_vi || toi.ho_ten || "Đối tác";

  if (cho || toi.loai_doi_tac === "ncc") return (<section className="v3-app" data-portal="doi-tac">
    <header className="v3-topbar"><span className="v3-brand"><span className="vh-logo"><img src="/cong/logo.png" alt="Vietourist Holdings" /></span><span>VTD<small>VIETOURIST HOLDINGS</small></span></span>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button></header>
    <main className="v3-main" style={{ maxWidth: 720, margin: "0 auto" }}>
      <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng đối tác</div><h1>Xin chào, {toi.ten_don_vi || toi.ho_ten || "đối tác"}</h1></div></div>
      <section className="v3-panel"><div className="v3-section-title"><h3>{toi.loai_doi_tac === "ncc" ? "Cổng nhà cung cấp" : "Đang chờ nối hồ sơ"}</h3><Badge c="demo">{toi.loai_doi_tac === "ncc" ? "Sắp ra mắt" : "Chờ Vietourist"}</Badge></div>
        <p>{toi.loai_doi_tac === "ncc" ? "Tài khoản đã được duyệt. Không gian nhà cung cấp (dịch vụ cung cấp, báo giá, đối soát) mở ở đợt sau." : cho}</p>
        <p className="v3-small">Liên hệ đăng nhập: {toi.dien_thoai || toi.email}.</p>
        <div className="v3-actions"><Nut i="log-out" onClick={thoat}>Đăng xuất</Nut></div></section>
    </main></section>);

  return (<section className="v3-app" data-portal="doi-tac">
    <header className="v3-topbar">
      <button type="button" className="v3-brand cursor-interaction" onClick={() => di("home")}>
        <span className="vh-logo"><img src="/cong/logo.png" alt="Vietourist Holdings" /></span><span>VTD<small>VIETOURIST HOLDINGS</small></span></button>
      <nav aria-label="Cổng"><button type="button" aria-pressed="true"><I n="handshake" /><span>{ctv ? "Cộng tác viên" : "Đại lý"}</span></button></nav>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button>
    </header>
    <div className="v3-mobile-nav"><Nut i="menu" onClick={() => setMenuMo(!menuMo)}>Danh mục chức năng</Nut><strong>{nhanMenu}</strong></div>
    <div className="v3-layout">
      <aside className={`v3-sidebar ${menuMo ? "open" : ""}`}>
        <div className="v3-side-profile"><span className="v3-avatar"><I n="handshake" /></span><strong>{ten}</strong><small>{blv ? `${blv.doi_tac.ma} · ${blv.doi_tac.loai_ten}` : "…"}</small></div>
        <nav aria-label="Chức năng đối tác">{MENU.map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={menuTab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
        <div className="v3-side-bottom"><Nut kieu="quiet" i="log-out" onClick={thoat}>Đăng xuất</Nut></div>
      </aside>
      <main className="v3-main">
        <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng đối tác · {ten}</div><h1>{nhanMenu}</h1></div></div>
        {msg && <div className="v3-notice info"><I n="check" /><span>{msg}</span></div>}
        {err && <div className="v3-notice warn"><I n="info" /><span>{err}</span></div>}
        {!blv && !err && <section className="v3-panel"><p>Đang tải…</p></section>}

        {blv && tab === "home" && <>
          <div className="v3-metrics">
            <section><span><I n="gift" />Doanh số D06 tháng {thang(blv.d06.ky)}</span><strong>{tien(blv.d06.doanh_so)}</strong>
              <small>{blv.d06.bac_hien_tai ? `bậc ${(blv.d06.bac_hien_tai.bps / 100).toLocaleString("vi-VN")}%` : blv.d06.hinh_thuc}</small></section>
            <section><span><I n="badge-check" />Hoa hồng tháng {thang(blv.d06.ky)}</span><strong>{tien(blv.d06.hoa_hong)}</strong><small>{blv.d06.trang_thai} — chỉ tính chuyến xong & thu đủ</small></section>
            {ctv ? <section><span><I n="send" />Nhu cầu chờ Sales</span><strong>{blv.dang_cho}</strong><small>Giới thiệu đang chờ liên hệ</small></section>
              : <section><span><I n="receipt" />Đại lý còn phải trả Vietourist</span><strong>{tien(blv.phai_tra)}</strong><small>{blv.so_booking_no} booking chưa thu đủ</small></section>}
          </div>
          {ctv ? <section className="v3-panel"><div className="v3-section-title"><h3>Giới thiệu gần đây</h3><Nut kieu="primary" i="user-plus" onClick={() => di("refer")}>Giới thiệu khách</Nut></div>
            {blv.gioi_thieu.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Gửi lúc</th><th scope="col">Khách</th><th scope="col">Trạng thái</th></tr></thead>
              <tbody>{blv.gioi_thieu.map((x: any) => <tr key={x.id}><td>{gio(x.gui_luc)}</td><th scope="row">{x.khach}<small>{x.tour}</small></th><td><Badge>{x.trang_thai}</Badge></td></tr>)}</tbody></table></div>
              : <p>Chưa có giới thiệu nào.</p>}</section>
          : <section className="v3-panel"><div className="v3-section-title"><h3>Giữ chỗ sắp hết hạn</h3><Badge c={blv.sap_het.length ? "warn" : "good"}>{blv.sap_het.length}</Badge></div>
            {blv.sap_het.length ? <div className="v3-table-wrap"><table><thead><tr><th scope="col">Booking</th><th scope="col">Khách</th><th scope="col">Hết hạn giữ chỗ</th><th scope="col">Cần cọc</th></tr></thead>
              <tbody>{blv.sap_het.map((b: any) => <tr key={b.ma}><th scope="row">{b.ma}<small>{b.ten} · {ngay(b.khoi_hanh)}</small></th><td>{b.so_khach}</td>
                <td>{conGio(b.con_gio)}</td><td><button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => { setBkMo(b); di("booking"); }}><span>{tien(b.coc_con)}</span></button></td></tr>)}</tbody></table></div>
              : <p>Không có giữ chỗ nào hết hạn trong 48 giờ tới.</p>}
            <small>Hết hạn mà chưa cọc: chỗ tự trả về tour (booking không bị hủy — cọc muộn thì lấy lại chỗ nếu còn).</small>
            <div className="v3-actions"><Nut kieu="primary" i="plane" onClick={() => di("tour")}>Tour & giữ chỗ</Nut></div></section>}
        </>}

        {blv && tab === "tour" && <>
          <nav className="v31-service-tabs" aria-label="Loại dịch vụ">
            <button type="button" className="cursor-interaction" aria-pressed={dv === "tour"} onClick={() => setDv("tour")}><I n="plane" /><span>Tour du lịch</span></button>
            <button type="button" className="cursor-interaction" aria-pressed={dv === "khach_san"} onClick={() => setDv("khach_san")}><I n="hotel" /><span>Khách sạn</span></button>
            <button type="button" className="cursor-interaction" aria-pressed="false" disabled><I n="utensils" /><span>Nhà hàng · sắp ra mắt</span></button></nav>
          {dv === "khach_san" ? <KhachSanOta ghiChu="Phòng đặt qua OTA chưa tính hoa hồng D06 cho đại lý / CTV — cơ sở tính cần duyệt riêng. Lượt chuyển vẫn ghi nguồn là đối tác của bạn." /> : <>
          <section className="v3-panel"><div className="v3-search"><label className="v3-field">Điểm đến hoặc tên tour<input type="search" value={q} placeholder="Phú Quốc, Huế…"
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && timTour()} /></label><Nut kieu="primary" i="search" onClick={() => timTour()}>Tìm tour</Nut></div></section>
          <section className="v3-panel">{!ds ? <p>Đang tải…</p> : ds.tour.length ? <div className="v3-table-wrap"><table>
            <thead><tr><th scope="col">Tour</th><th scope="col">Khởi hành</th><th scope="col">Giá bán / khách</th><th scope="col">Hoa hồng</th><th scope="col"></th></tr></thead>
            <tbody>{ds.tour.map((t: any) => <tr key={t.id}><th scope="row">{t.ten}<small>{t.ma}{t.noi_khoi_hanh ? ` · từ ${t.noi_khoi_hanh}` : ""}{t.it_cho ? " · sắp hết chỗ" : ""}</small></th>
              <td>{ngay(t.khoi_hanh)}</td><td>{tien(t.gia)}</td><td>{ds.bac_hien_tai ? `D06 · bậc ${(ds.bac_hien_tai.bps / 100).toLocaleString("vi-VN")}%` : ds.hoa_hong}</td>
              <td><Nut kieu="primary" i="tickets" onClick={() => moGiu(t)}>Giữ chỗ</Nut></td></tr>)}</tbody></table></div>
            : <p>Không có tour đang mở bán khớp tìm kiếm.</p>}
            <small>Giá bán công bố (như khách lẻ). Hoa hồng D06 tính theo tháng, chi sau khi chuyến xong và thu đủ.</small></section>
          </>}
        </>}

        {blv && tab === "hold" && tourMo && <div className="v3-two">
          <section className="v3-panel"><Nut kieu="quiet" i="arrow-left" onClick={() => di("tour")}>Quay lại danh sách</Nut>
            <h2>{tourMo.ten}</h2><p>{tourMo.ma} · {ngay(tourMo.khoi_hanh)} · {tourMo.thoi_gian}</p>
            <label className="v3-field">Tên khách đại diện<input value={f.ten_khach} onChange={(e) => setF({ ...f, ten_khach: e.target.value })} /></label>
            <label className="v3-field">SĐT khách<input inputMode="tel" value={f.dien_thoai} placeholder="09xx xxx xxx" onChange={(e) => setF({ ...f, dien_thoai: e.target.value })} /></label>
            <div className="v3-form-grid">
              <label className="v3-field">Người lớn<input type="number" min={1} value={f.nguoi_lon} onChange={(e) => setF({ ...f, nguoi_lon: Number(e.target.value) })} /></label>
              <label className="v3-field">Trẻ em<input type="number" min={0} value={f.tre_em} onChange={(e) => setF({ ...f, tre_em: Number(e.target.value) })} /></label></div>
            <label className="v3-field">Ghi chú cho Điều hành<textarea rows={2} value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
          </section>
          <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Tạm tính</h3><Badge>Giá bán công bố</Badge></div>
            <dl className="v3-stat-rows"><div><dt>Người lớn</dt><dd>{f.nguoi_lon} × {tien(tourMo.gia)}</dd></div>
              {Number(f.tre_em) > 0 && <div><dt>Trẻ em</dt><dd>{f.tre_em} × {tien(tourMo.gia_tre_em || tourMo.gia)}</dd></div>}</dl>
            <div className="v3-total"><span>Tạm tính</span><strong>{tien(tamTinh)}</strong></div>
            <p>Giữ chỗ đến theo tham số hiện hành, không muộn hơn hạn hủy chỗ của tour. Máy chủ kiểm như Điều hành tạo booking: tour đã duyệt, dự toán, còn chỗ. Không giảm giá trên cổng. Người tiếp nhận: bàn Sales Admin lẻ.</p>
            <Nut kieu="primary" i="tickets" disabled={busy} onClick={giu}>{busy ? "Đang giữ…" : "Xác nhận giữ chỗ"}</Nut></section></div>}

        {blv && tab === "bookings" && <section className="v3-panel">
          {!bk ? <p>Đang tải…</p> : bk.booking.length ? <div className="v3-table-wrap"><table>
            <thead><tr><th scope="col">Booking</th><th scope="col">Khách</th><th scope="col">Giá trị</th><th scope="col">Phục vụ</th><th scope="col">Thanh toán</th><th scope="col"></th></tr></thead>
            <tbody>{bk.booking.map((b: any) => <tr key={b.ma}><th scope="row">{b.ma}<small>{b.ten} · {ngay(b.khoi_hanh)}</small></th><td>{b.so_khach}</td><td>{tien(b.gia_tri)}</td>
              <td><Badge c={b.muc}>{b.phuc_vu}</Badge>{b.dang_giu && <small> {conGio(b.con_gio)}</small>}</td><td>{b.thanh_toan}</td>
              <td><Nut kieu="quiet" i="chevron-right" onClick={() => { setBkMo(b); di("booking"); }}>Chi tiết</Nut></td></tr>)}</tbody></table></div>
            : <p>Chưa có booking nào của {ten}.</p>}
          <small>Đổi / hủy: gửi yêu cầu cho bàn Sales Admin lẻ; phí hủy theo hợp đồng đại lý.</small></section>}

        {blv && tab === "booking" && bkMo && <>
          <Nut kieu="quiet" i="arrow-left" onClick={() => di("bookings")}>Quay lại danh sách</Nut>
          <div className="v3-two">
            <section className="v3-panel"><div className="v3-section-title"><h2>{bkMo.ma}</h2><Badge c={bkMo.muc}>{bkMo.phuc_vu}</Badge></div>
              <dl className="v3-stat-rows"><div><dt>Tour</dt><dd>{bkMo.ten}</dd></div><div><dt>Khởi hành</dt><dd>{ngay(bkMo.khoi_hanh)}</dd></div>
                <div><dt>Khách đại diện</dt><dd>{bkMo.khach} · {bkMo.so_khach} khách</dd></div>
                {bkMo.giu_den && <div><dt>Giữ chỗ đến</dt><dd>{gio(bkMo.giu_den)}{bkMo.dang_giu ? ` (${conGio(bkMo.con_gio)})` : ""}</dd></div>}</dl></section>
            <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Thanh toán</h3><Badge c={bkMo.thanh_toan === "Đã thu đủ" ? "good" : "warn"}>{bkMo.thanh_toan}</Badge></div>
              <dl className="v3-stat-rows"><div><dt>Giá trị</dt><dd>{tien(bkMo.gia_tri)}</dd></div><div><dt>Đã thu (kế toán xác nhận)</dt><dd>{tien(bkMo.da_thu)}</dd></div>
                {bkMo.dang_xac_nhan > 0 && <div><dt>Đang xác nhận</dt><dd>{tien(bkMo.dang_xac_nhan)}</dd></div>}
                {bkMo.coc_con > 0 && <div><dt>Cọc còn thiếu</dt><dd>{tien(bkMo.coc_con)}</dd></div>}</dl>
              <div className="v3-total"><span>Còn phải trả</span><strong>{tien(bkMo.con_lai)}</strong></div></section></div>
          {bkMo.con_lai > 0 && bkMo.muc !== "bad" && <section className="v3-panel"><div className="v3-section-title"><h3>Chuyển khoản bằng QR</h3></div>
            <QrThanhToan ma={bkMo.ma} duong="/doi-tac/booking" /></section>}
        </>}

        {blv && tab === "d06" && <>
          <section className="v3-panel"><div className="v3-section-title"><h3>{hh?.hinh_thuc_ten || "Hoa hồng D06"} · lũy tiến từng phần, tính lại mỗi tháng</h3></div>
            {hh ? <BacD06 hh={hh} /> : <p>Đang tải…</p>}</section>
          <section className="v3-panel">{!hh ? <p>Đang tải…</p> : <div className="v3-table-wrap"><table>
            <thead><tr><th scope="col">Tháng</th><th scope="col">Doanh số đủ điều kiện</th><th scope="col">Hoa hồng</th><th scope="col">Trạng thái</th></tr></thead>
            <tbody>{hh.thang.map((m: any) => <tr key={m.ky}><th scope="row">{thang(m.ky)}</th><td>{tien(m.doanh_so)}</td><td>{tien(m.hoa_hong)}</td>
              <td><Badge c={m.trang_thai === "Đã chi" ? "good" : m.da_chot ? "warn" : "neutral"}>{m.trang_thai}</Badge></td></tr>)}</tbody></table></div>}
            <small>Chỉ tính booking không hủy, tour xong VÀ thu đủ; vào tháng của ngày muộn hơn. Số do Kế toán tính và chốt trên VTOS; cổng chỉ hiện.
              {hh && !hh.hieu_luc_tu ? " D06 chưa có ngày hiệu lực — số hiện là tính thử." : ""}</small></section>
        </>}

        {blv && tab === "debt" && (!no ? <section className="v3-panel"><p>Đang tải…</p></section> : <>
          <div className="v3-metrics">
            <section><span><I n="receipt" />Đại lý còn phải trả Vietourist</span><strong>{tien(no.dai_ly_phai_tra)}</strong><small>tiền booking chưa thu đủ</small></section>
            <section><span><I n="gift" />Vietourist còn phải trả đại lý</span><strong>{tien(no.vietourist_phai_tra)}</strong><small>hoa hồng đã chốt, chưa chi</small></section></div>
          <div className="v3-notice warn"><I n="info" /><span>Hai chiều hiện riêng, KHÔNG tự bù trừ thành một số. Bù trừ cần thỏa thuận và chứng từ.</span></div>
          <section className="v3-panel"><div className="v3-section-title"><h3>Booking chưa thu đủ</h3></div>
            {no.booking.length ? <div className="v3-table-wrap"><table>
              <thead><tr><th scope="col">Booking</th><th scope="col">Giá trị</th><th scope="col">Đã thu (kế toán xác nhận)</th><th scope="col">Còn phải trả</th><th scope="col">Hạn</th></tr></thead>
              <tbody>{no.booking.map((b: any) => <tr key={b.ma}><th scope="row">{b.ma}<small>{b.ten} · {ngay(b.khoi_hanh)}</small></th><td>{tien(b.gia_tri)}</td><td>{tien(b.da_thu)}</td>
                <td>{tien(b.con_lai)}</td><td>{b.dang_giu && b.coc_con > 0 ? `cọc trước ${gio(b.giu_den)}` : "trước khởi hành"}</td></tr>)}</tbody></table></div>
              : <p>Không còn booking nào chưa thu đủ.</p>}</section>
          {no.hoa_hong.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Hoa hồng đã chốt chưa chi</h3></div>
            <div className="v3-table-wrap"><table><thead><tr><th scope="col">Tháng</th><th scope="col">Hoa hồng</th><th scope="col">Đã chi</th><th scope="col">Còn phải trả</th></tr></thead>
              <tbody>{no.hoa_hong.map((m: any) => <tr key={m.ky}><th scope="row">{thang(m.ky)}</th><td>{tien(m.hoa_hong)}</td><td>{tien(m.da_tra)}</td><td>{tien(m.con_phai_tra)}</td></tr>)}</tbody></table></div></section>}
        </>)}

        {blv && tab === "refer" && <div className="v3-two">
          <section className="v3-panel"><h2>Giới thiệu khách cho Vietourist</h2>
            <label className="v3-field">Tour quan tâm<select value={g.tour_id} onChange={(e) => setG({ ...g, tour_id: e.target.value })}>
              <option value="">Chưa chọn — để Sales tư vấn</option>{(ds?.tour || []).map((t: any) => <option key={t.id} value={t.id}>{t.ten} · {ngay(t.khoi_hanh)}</option>)}</select></label>
            <label className="v3-field">Số khách<input type="number" min={1} value={g.so_khach} onChange={(e) => setG({ ...g, so_khach: Number(e.target.value) })} /></label>
            <label className="v3-field">Tên khách<input value={g.ten_khach} onChange={(e) => setG({ ...g, ten_khach: e.target.value })} /></label>
            <label className="v3-field">SĐT khách<input inputMode="tel" value={g.dien_thoai} placeholder="09xx xxx xxx" onChange={(e) => setG({ ...g, dien_thoai: e.target.value })} /></label>
            <label className="v3-field">Ghi chú cho Sales<textarea rows={2} value={g.ghi_chu} onChange={(e) => setG({ ...g, ghi_chu: e.target.value })} /></label>
            <div className="v3-check"><input id="ctv-dong-y" type="checkbox" checked={g.dong_y} onChange={(e) => setG({ ...g, dong_y: e.target.checked })} />
              <label htmlFor="ctv-dong-y">Khách đã đồng ý để tôi chuyển thông tin liên hệ cho Vietourist.</label></div>
            <Nut kieu="primary" i="send" disabled={busy || !g.dong_y} onClick={guiGt}>{busy ? "Đang gửi…" : "Gửi giới thiệu"}</Nut></section>
          <section className="v3-panel"><div className="v3-section-title"><h3>Cách tính nguồn</h3></div>
            <p>CTV không giữ chỗ, không thu tiền: nhu cầu vào hàng chờ Sales kèm dấu thời gian làm chứng cứ nguồn. Khách đã có Sales chăm từ trước thì TP Kinh doanh xử lý tranh chấp nguồn, có nhật ký.</p>
            <p>Hoa hồng CTV theo D06 — xem mục Hoa hồng D06.</p></section></div>}

        {blv && tab === "referrals" && <section className="v3-panel">
          {!gt ? <p>Đang tải…</p> : gt.gioi_thieu.length ? <div className="v3-table-wrap"><table>
            <thead><tr><th scope="col">Gửi lúc</th><th scope="col">Khách</th><th scope="col">Tour</th><th scope="col">Trạng thái</th></tr></thead>
            <tbody>{gt.gioi_thieu.map((x: any) => <tr key={x.id}><td>{gio(x.gui_luc)}</td><th scope="row">{x.khach}<small>{x.so_khach} khách</small></th><td>{x.tour}</td><td><Badge>{x.trang_thai}</Badge></td></tr>)}</tbody></table></div>
            : <p>Chưa gửi giới thiệu nào.</p>}</section>}

        <footer className="v3-bottom"><I n="shield-check" />Số liệu lấy trực tiếp từ VTOS · chỉ booking của {ten}</footer>
        <nav className="v3-bottom-nav" aria-label="Chức năng nhanh trên điện thoại">{MENU.slice(0, 5).map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={menuTab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
      </main>
    </div>
  </section>);
}
