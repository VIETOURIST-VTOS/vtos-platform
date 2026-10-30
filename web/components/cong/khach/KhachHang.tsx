"use client";
/* KH-1 · CỔNG KHÁCH HÀNG VTD — dựng theo bộ giao diện v3.2 (màn KH01–KH04, KH16, KH23), Chủ tịch duyệt
   26/10/2026. Dùng nguyên lớp CSS của bộ (v3-app, v3-sidebar, v3-panel…) nên trông đúng bản vẽ.

   Khác bản vẽ, có chủ ý:
   · Không có thanh «Bản xem thử», không có nút đổi sang cổng Đối tác / Cổ đông (đó là công cụ duyệt mẫu).
   · Mọi số là số THẬT từ VTOS. Phần chưa làm (khách sạn, nhà hàng, thanh toán, điểm, hạng, yêu thích,
     …) hiện «Sắp ra mắt» — KHÔNG hiện số mẫu như thật. KH-4 mở đánh giá, góp ý, hỗ trợ.
   · «Gửi yêu cầu» thay «Đặt thử»: chưa giữ chỗ, chưa thu tiền; Sales gọi lại và báo giá cuối. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { goiCong } from "@/lib/cong";
import { svg } from "./icons";
import NhaHangKhach from "./NhaHangKhach";
import QrThanhToan from "./QrThanhToan";
import DatBanCuaToi from "../DatBanCuaToi";
import { useDiem, DiemUuDai, HangThanhVien, YeuThich } from "./RewardsKhach";
import { DanhGiaKhach, GopYKhach, HoTroKhach } from "./ChamSocKhach";
import KhachSanOta from "../KhachSanOta";
import KhachSanVtd, { PhongCuaToi } from "../KhachSanVtd";
import VeMayBayOta from "../VeMayBayOta";

type Tab = "home" | "deals" | "tour" | "request" | "bookings" | "booking" | "rewards" | "tier" | "favorites" | "reviews" | "feedback" | "support" | "profile";
const MENU: [Tab, string, string][] = [
  ["home", "Khám phá", "house"], ["deals", "Đặt dịch vụ", "compass"], ["bookings", "Đơn của tôi", "luggage"],
  ["rewards", "Điểm & ưu đãi", "gift"], ["tier", "Hạng thành viên", "badge-check"], ["favorites", "Yêu thích & nhắc giá", "heart"],
  ["reviews", "Đánh giá", "star"], ["feedback", "Góp ý lãnh đạo", "message-square-heart"], ["support", "Hỗ trợ", "messages-square"],
  ["profile", "Hồ sơ & riêng tư", "user-round"],
];
const TIEU_DE: Partial<Record<Tab, string>> = { tour: "Chi tiết dịch vụ", request: "Gửi yêu cầu", booking: "Chi tiết đơn" };
// KH-4 (27/10/2026): đánh giá, góp ý lãnh đạo, hỗ trợ đã mở — không còn mục «Sắp ra mắt».
const SAP_RA_MAT: Partial<Record<Tab, [string, string]>> = {};

const I = ({ n, s }: { n: string; s?: number }) => <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: svg(n, s) }} />;
const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const BIEN = /phú quốc|nha trang|quy nhơn|côn đảo|biển|đảo|vũng tàu|phan thiết|mũi né|hạ long|cát bà|bali|phuket/i;
const DI_SAN = /huế|hội an|di sản|ninh bình|cố đô|mỹ sơn|tràng an|angkor|kyoto/i;
const canh = (t: any): [string, string] => BIEN.test(t.ten) ? ["sea", "palmtree"] : DI_SAN.test(t.ten) ? ["heritage", "landmark"] : t.nuoc_ngoai ? ["city", "plane"] : ["city", "compass"];

function Badge({ c, children }: { c?: string; children: any }) { return <span className={`v3-badge ${c || "neutral"}`}>{children}</span>; }
function Nut({ i, children, kieu = "secondary", ...p }: any) {
  return <button type="button" className={`v3-button v3-${kieu} cursor-interaction`} {...p}>{i && <I n={i} />}<span>{children}</span></button>;
}

// Bộ nhớ yêu thích dùng chung cho mọi thẻ tour trong một lần mở cổng (KH-3).
let _ytIds: number[] = []; const _ytNghe = new Set<(ids: number[]) => void>();
const datYt = (ids: number[]) => { _ytIds = ids; _ytNghe.forEach((f) => f(ids)); };
function useYt() {
  const [ids, setIds] = useState<number[]>(_ytIds);
  useEffect(() => { _ytNghe.add(setIds); return () => { _ytNghe.delete(setIds); }; }, []);
  return ids;
}

function TheTour({ t, mo }: { t: any; mo: (t: any) => void }) {
  const ids = useYt(); const da = ids.includes(t.id);
  const doi = (e: React.MouseEvent) => { e.stopPropagation(); goiCong("/khach/yeu-thich", { tour_id: t.id, luu: !da }).then((r) => datYt(r.ids)).catch(() => null); };
  const [c, icon] = canh(t);
  return (<article className="v3-product">
    <div className={`v3-scene ${c}`}><span className="v3-scene-orb" /><span className="v3-scene-icon"><I n={icon} /></span>
      <span className="v3-badge neutral">{t.nhan}</span>
      <button type="button" className="v3-favorite cursor-interaction" aria-pressed={da} aria-label={da ? `Bỏ lưu ${t.ten}` : `Lưu ${t.ten}`} onClick={doi}><I n="heart" /></button>
      <span className="v3-scene-title">{t.ten}</span></div>
    <div className="v3-product-body"><small>{t.thoi_gian} · {ngay(t.khoi_hanh)}{t.noi_khoi_hanh ? ` · từ ${t.noi_khoi_hanh}` : ""}</small>
      <h3>{t.ma}{t.it_cho ? " · sắp hết chỗ" : ""}</h3>
      <div className="v3-price">{t.gia_goc && <del>{tien(t.gia_goc)}</del>}<strong>{tien(t.gia)}</strong><small>/khách · giá bán hiện hành</small></div>
      <Nut i="arrow-up-right" onClick={() => mo(t)}>Xem hành trình</Nut></div>
  </article>);
}

function SapRaMat({ tab }: { tab: Tab }) {
  const [h, m] = SAP_RA_MAT[tab] || ["", ""];
  return (<section className="v3-panel"><div className="v3-section-title"><h3>{h}</h3><Badge c="demo">Sắp ra mắt</Badge></div><p>{m}</p></section>);
}

export default function KhachHang({ toi, thoat }: { toi: any; thoat: () => void }) {
  const [tab, setTab] = useState<Tab>("home");
  // DT-2: quay về từ trang thẻ OnePay (?dat_ban=…) → mở thẳng «Đơn của tôi», nơi có «Đặt bàn của tôi».
  useEffect(() => { try { if (new URLSearchParams(window.location.search).get("dat_ban")) setTab("bookings"); } catch { /* bỏ qua */ } }, []);
  const [menuMo, setMenuMo] = useState(false);
  const [home, setHome] = useState<any>(null);
  const [ds, setDs] = useState<any>(null);
  const [dv, setDv] = useState<"tour" | "nha_hang" | "khach_san" | "ve_may_bay">("tour");
  // KS-14: quay về từ trang thẻ OnePay (?ks_vtd=…) → mở thẳng Đặt dịch vụ › Khách sạn, nơi có trang đơn.
  useEffect(() => { try { if (new URLSearchParams(window.location.search).get("ks_vtd") !== null) { setTab("deals"); setDv("khach_san"); } } catch { /* bỏ qua */ } }, []);
  const [loc, setLoc] = useState({ q: "", tu_ngay: "", noi: "", ngan_sach: "", nhom: "" });
  const [tourMo, setTourMo] = useState<any>(null);
  const [loaiYc, setLoaiYc] = useState<"tour" | "tour_doan">("tour");
  const [yc, setYc] = useState({ so_khach: 2, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false });
  const [don, setDon] = useState<any>(null);
  const [donMo, setDonMo] = useState<any>(null);
  const [hs, setHs] = useState<any>(null);
  const [htDon, setHtDon] = useState("");
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  const di = useCallback((t: Tab) => { setTab(t); setMenuMo(false); setMsg(""); setErr(""); window.scrollTo(0, 0); }, []);
  const timTour = useCallback(async (l = loc) => {
    const q = new URLSearchParams(Object.entries(l).filter(([, v]) => v) as any).toString();
    try { setDs(await goiCong(`/khach/tour${q ? `?${q}` : ""}`)); } catch (x: any) { setErr(x.message); }
  }, [loc]);
  useEffect(() => { goiCong("/khach/trang-chu").then(setHome).catch((x) => setErr(x.message)); }, []);
  useEffect(() => { goiCong("/khach/yeu-thich").then((r) => datYt(r.ids)).catch(() => null); }, []);
  const diem = useDiem();
  useEffect(() => {
    if (tab === "deals" && !ds) timTour();
    if ((tab === "bookings" || tab === "booking" || tab === "feedback" || tab === "support") && !don) goiCong("/khach/don").then(setDon).catch((x) => setErr(x.message));
    if (tab === "profile" && !hs) goiCong("/khach/ho-so").then(setHs).catch((x) => setErr(x.message));
  }, [tab, ds, don, hs, timTour]);

  const moTour = (t: any) => { setTourMo(t); di("tour"); };
  const moYeuCau = (loai: "tour" | "tour_doan") => { setLoaiYc(loai); setYc({ so_khach: loai === "tour" ? 2 : 20, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false }); di("request"); };
  const guiYc = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await goiCong("/khach/yeu-cau", { loai: loaiYc, tour_id: loaiYc === "tour" ? tourMo?.id : null, so_khach: Number(yc.so_khach),
        dien_thoai: yc.dien_thoai, ngay_mong_muon: yc.ngay_mong_muon || null, ghi_chu: yc.ghi_chu, dong_y: yc.dong_y });
      setDon(null); setMsg(r.message); di("bookings"); setMsg(r.message);
    } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  const luuHs = async (patch: any) => {
    setErr(""); setMsg("");
    try { setHs(await goiCong("/khach/ho-so", patch)); setMsg("Đã lưu hồ sơ"); } catch (x: any) { setErr(x.message); }
  };
  const ten = hs?.ho_ten ?? toi.ho_ten;
  const lienHe = toi.dien_thoai || toi.email;
  const tamTinh = useMemo(() => (tourMo ? tourMo.gia * Number(yc.so_khach || 0) : 0), [tourMo, yc.so_khach]);
  const coSdt = !!toi.dien_thoai;
  const menuTab: Tab = tab === "tour" || tab === "request" ? "deals" : tab === "booking" ? "bookings" : tab;
  const nhanMenu = MENU.find(([k]) => k === menuTab)?.[1] || "";

  return (<section className="v3-app" data-portal="khach-hang">
    <header className="v3-topbar">
      <button type="button" className="v3-brand cursor-interaction" onClick={() => di("home")}>
        <span className="vh-logo"><img src="/cong/logo.png" alt="Vietourist Holdings" /></span><span>VTD<small>VIETOURIST HOLDINGS</small></span></button>
      <nav aria-label="Cổng"><button type="button" aria-pressed="true"><I n="luggage" /><span>Khách hàng</span></button></nav>
      <button type="button" className="v3-home-return cursor-interaction" aria-label="Đăng xuất" title="Đăng xuất" onClick={thoat}><I n="log-out" /></button>
    </header>
    <div className="v3-mobile-nav"><Nut i="menu" onClick={() => setMenuMo(!menuMo)}>Danh mục chức năng</Nut><strong>{nhanMenu}</strong></div>
    <div className="v3-layout">
      <aside className={`v3-sidebar ${menuMo ? "open" : ""}`}>
        <div className="v3-side-profile"><span className="v3-avatar"><I n="luggage" /></span><strong>Xin chào{ten ? `, ${ten}` : ", bạn"}!</strong><small>{lienHe}</small></div>
        <nav aria-label="Chức năng Khách hàng">{MENU.map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={menuTab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
        <div className="v3-side-bottom"><Nut kieu="quiet" i="log-out" onClick={thoat}>Đăng xuất</Nut></div>
      </aside>
      <main className="v3-main">
        <div className="v3-page-head"><div><div className="v3-eyebrow">VTD • Cổng khách hàng</div><h1>{TIEU_DE[tab] || nhanMenu}</h1></div></div>
        {msg && <div className="v3-notice info"><I n="check" /><span>{msg}</span></div>}
        {err && <div className="v3-notice warn"><I n="info" /><span>{err}</span></div>}

        {tab === "home" && <>
          <section className="v3-hero customer"><div><span className="v3-eyebrow">VIETOURIST • HÀNH TRÌNH CỦA BẠN</span>
            <h2>Đi để trải nghiệm.<br />Trở về với nhiều điều hơn.</h2><p>Ưu đãi phù hợp, hành trình rõ ràng,<br />quyền lợi được giữ trong một tài khoản.</p>
            <Nut kieu="primary" i="compass" onClick={() => di("deals")}>Tìm chuyến đi tiếp theo</Nut></div>
            <div className="v3-hero-art" aria-hidden="true"><I n="plane" /><span>EXPLORE<br />VIETNAM</span></div></section>
          <div className="v3-metrics">
            <section><span><I n="gift" />Điểm khả dụng</span><strong>{diem.x ? (diem.x.dang_bat ? Math.round(diem.x.kha_dung).toLocaleString("vi-VN") : "—") : "…"}</strong><small>{diem.x?.dang_bat ? `= ${Math.round(diem.x.kha_dung * 100).toLocaleString("vi-VN")} đ ưu đãi` : "VTD Rewards sắp bắt đầu"}</small></section>
            <section><span><I n="badge-check" />Hạng thành viên</span><strong>{diem.x ? diem.x.hang.hang : "…"}</strong><small>Chi tiêu xét hạng tách khỏi điểm</small></section>
            <section><span><I n="luggage" />Đơn sắp đi</span><strong>{home ? home.sap_di : "…"}</strong><small>Theo dõi phục vụ và thanh toán riêng</small></section>
          </div>
          <section className="v3-panel"><div className="v3-section-title"><h3>Chuyến đi đang chờ bạn</h3></div>
            {home?.chuyen_toi ? <div className="v3-journey"><div className="v3-journey-icon"><I n="palmtree" /></div>
              <div><strong>{home.chuyen_toi.ten} · {ngay(home.chuyen_toi.khoi_hanh)}–{ngay(home.chuyen_toi.ket_thuc)}</strong>
                <p>Đơn {home.chuyen_toi.ma} · {home.chuyen_toi.so_khach} khách</p>
                <Badge c={home.chuyen_toi.muc}>{home.chuyen_toi.phuc_vu}</Badge> <Badge c={home.chuyen_toi.thanh_toan === "Đã thu đủ" ? "good" : "warn"}>{home.chuyen_toi.thanh_toan}</Badge></div>
              <Nut i="arrow-right" onClick={() => { setDonMo(home.chuyen_toi); di("booking"); }}>Xem đơn</Nut></div>
              : <p>{home ? "Chưa có chuyến sắp đi gắn với " + lienHe + "." : "Đang tải…"}{home?.yeu_cau_dang_cho ? ` Bạn có ${home.yeu_cau_dang_cho} yêu cầu đang chờ Sales liên hệ.` : ""}</p>}
          </section>
          <div className="v3-section-title"><h2>Tour cho hành trình mới</h2><Nut kieu="quiet" i="arrow-right" onClick={() => di("deals")}>Xem tất cả</Nut></div>
          <div className="v3-products">{(home?.tour || []).map((t: any) => <TheTour key={t.id} t={t} mo={moTour} />)}</div>
          {home && !home.tour.length && <section className="v3-panel"><p>Chưa có tour mở bán. Gửi yêu cầu tour đoàn để Sales thiết kế hành trình riêng.</p></section>}
          <div className="v3-shortcuts"><Nut i="users" onClick={() => moYeuCau("tour_doan")}>Tour đoàn theo yêu cầu</Nut><Nut i="luggage" onClick={() => di("bookings")}>Đơn của tôi</Nut><Nut i="user-round" onClick={() => di("profile")}>Hồ sơ & riêng tư</Nut></div>
          <section className="v3-panel"><div className="v3-section-title"><h3>Thưởng thức một điểm đến</h3><Nut kieu="quiet" i="utensils" onClick={() => { setDv("nha_hang"); di("deals"); }}>Khám phá ẩm thực</Nut></div>
            <p>Chọn nhà hàng, xem thực đơn và gửi yêu cầu đặt bàn trong cùng tài khoản VTD. Đặt phòng khách sạn qua đối tác OTA của Vietourist.</p></section>
        </>}

        {tab === "deals" && <>
          <nav className="v31-service-tabs" aria-label="Loại dịch vụ">
            <button type="button" className="cursor-interaction" aria-pressed={dv === "tour"} onClick={() => setDv("tour")}><I n="plane" /><span>Tour du lịch</span></button>
            <button type="button" className="cursor-interaction" aria-pressed={dv === "khach_san"} onClick={() => setDv("khach_san")}><I n="hotel" /><span>Khách sạn</span></button>
            <button type="button" className="cursor-interaction" aria-pressed={dv === "ve_may_bay"} onClick={() => setDv("ve_may_bay")}><I n="plane" /><span>Vé máy bay</span></button>
            <button type="button" className="cursor-interaction" aria-pressed={dv === "nha_hang"} onClick={() => setDv("nha_hang")}><I n="utensils" /><span>Nhà hàng & ẩm thực</span></button></nav>
          {dv === "khach_san" ? <section className="v31-service-content" aria-label="Khách sạn"><KhachSanVtd ten={ten} lienHe={lienHe} /><h3 className="ksv-ota-dau">Hoặc đặt qua đối tác OTA của Vietourist</h3><KhachSanOta /></section>
          : dv === "ve_may_bay" ? <section className="v31-service-content" aria-label="Vé máy bay"><VeMayBayOta /></section>
          : dv === "nha_hang" ? <section className="v31-service-content" aria-label="Nhà hàng & ẩm thực">
            <NhaHangKhach ten={ten} lienHe={lienHe} coSdt={coSdt} sdtCho={toi.dien_thoai} daGui={(m) => { setDon(null); di("bookings"); setMsg(m); }} /></section>
          : <section className="v31-service-content" aria-label="Tour du lịch">
            <section className="v3-panel">
              <div className="v3-search"><label className="v3-field">Điểm đến hoặc tên tour<input type="search" value={loc.q} placeholder="Phú Quốc, Đà Nẵng, Huế…"
                onChange={(e) => setLoc({ ...loc, q: e.target.value })} onKeyDown={(e) => e.key === "Enter" && timTour()} /></label>
                <Nut kieu="primary" i="search" onClick={() => timTour()}>Tìm tour</Nut></div>
              <div className="v3-form-grid">
                <label className="v3-field">Khởi hành từ ngày<input type="date" value={loc.tu_ngay} onChange={(e) => setLoc({ ...loc, tu_ngay: e.target.value })} /></label>
                <label className="v3-field">Nơi khởi hành<select value={loc.noi} onChange={(e) => setLoc({ ...loc, noi: e.target.value })}>
                  <option value="">Tất cả</option>{(ds?.noi_khoi_hanh || []).map((n: string) => <option key={n} value={n}>{n}</option>)}</select></label>
                <label className="v3-field">Ngân sách / khách<select value={loc.ngan_sach} onChange={(e) => setLoc({ ...loc, ngan_sach: e.target.value })}>
                  <option value="">Tất cả</option><option value="1500000">Đến 1,5 triệu</option><option value="3500000">Đến 3,5 triệu</option>
                  <option value="5000000">Đến 5 triệu</option><option value="10000000">Đến 10 triệu</option></select></label>
              </div>
              <Nut i="sliders-horizontal" onClick={() => timTour()}>Áp dụng bộ lọc</Nut>
              <div className="v3-chips" aria-label="Nhóm tour">{[["", "Tất cả tour"], ["promo", "Khuyến mại"], ["last", "Giờ chót"]].map(([k, t]) =>
                <button key={k} type="button" className="cursor-interaction" aria-pressed={loc.nhom === k} onClick={() => { const l = { ...loc, nhom: k }; setLoc(l); timTour(l); }}>{t}</button>)}</div>
            </section>
            <div className="v3-section-title"><h2>Chọn hành trình của bạn</h2><Badge>{ds ? `${ds.tour.length} tour đang mở bán` : "Đang tải…"}</Badge></div>
            <div className="v3-products">{(ds?.tour || []).map((t: any) => <TheTour key={t.id} t={t} mo={moTour} />)}</div>
            {ds && !ds.tour.length && <section className="v3-panel"><p>Không có tour khớp bộ lọc. Thử bỏ bớt điều kiện hoặc gửi yêu cầu tour đoàn.</p></section>}
            <section className="v3-panel"><div className="v3-section-title"><h3>Tour đoàn theo yêu cầu</h3></div>
              <p>Hành trình riêng cho gia đình, doanh nghiệp và những dịp đặc biệt.</p>
              <Nut i="users" onClick={() => moYeuCau("tour_doan")}>Gửi yêu cầu tour đoàn</Nut></section>
          </section>}
        </>}

        {tab === "tour" && tourMo && <>
          <Nut kieu="quiet" i="arrow-left" onClick={() => di("deals")}>Quay lại danh sách</Nut>
          <section className="v3-product-detail">
            <div className={`v3-scene ${canh(tourMo)[0]}`}><span className="v3-scene-orb" /><span className="v3-scene-icon"><I n={canh(tourMo)[1]} /></span>
              <span className="v3-scene-title">{tourMo.ten}</span><span className="v3-badge neutral">{tourMo.nhan}</span></div>
            <div className="v3-panel"><div className="v3-section-title"><h2>{tourMo.ten}</h2><Badge>{tourMo.ma}</Badge></div>
              <dl className="v3-stat-rows">
                <div><dt>Thời gian</dt><dd>{tourMo.thoi_gian}</dd></div>
                <div><dt>Khởi hành</dt><dd>{ngay(tourMo.khoi_hanh)} – kết thúc {ngay(tourMo.ket_thuc)}</dd></div>
                {tourMo.noi_khoi_hanh && <div><dt>Nơi khởi hành</dt><dd>{tourMo.noi_khoi_hanh}</dd></div>}
                {tourMo.phuong_tien && <div><dt>Phương tiện</dt><dd>{tourMo.phuong_tien}</dd></div>}
                <div><dt>Giá người lớn</dt><dd>{tourMo.gia_goc && <del style={{ marginRight: 8 }}>{tien(tourMo.gia_goc)}</del>}{tien(tourMo.gia)} / khách</dd></div>
                {tourMo.gia_tre_em && <div><dt>Giá trẻ em</dt><dd>{tien(tourMo.gia_tre_em)} / khách</dd></div>}
                <div><dt>Chỗ</dt><dd>{tourMo.it_cho ? "Còn ít chỗ" : "Còn chỗ"}</dd></div>
              </dl>
              <div className="v3-notice warn"><I n="info" /><span>Chương trình chi tiết, dịch vụ bao gồm và điều kiện hủy do Sales gửi kèm báo giá. Gửi yêu cầu chưa giữ chỗ và chưa thu tiền.</span></div>
              <div className="v3-actions"><Nut kieu="primary" i="send" onClick={() => moYeuCau("tour")}>Gửi yêu cầu đặt tour</Nut></div>
            </div></section>
        </>}

        {tab === "request" && <div className="v3-two">
          <section className="v3-panel">
            <h2>{loaiYc === "tour" ? tourMo?.ten : "Tour đoàn theo yêu cầu"}</h2>
            <p>{loaiYc === "tour" ? `${ngay(tourMo?.khoi_hanh)} · ${tourMo?.thoi_gian}` : "Gia đình, doanh nghiệp, hội nhóm — Sales thiết kế hành trình riêng."}</p>
            <label className="v3-field">Số khách<input type="number" min={1} max={200} value={yc.so_khach} onChange={(e) => setYc({ ...yc, so_khach: Number(e.target.value) })} /></label>
            <div className="v3-field">Người gửi<div className="v3-readonly">{ten || "Khách hàng"} · {lienHe}</div></div>
            <label className="v3-field">Số điện thoại Sales gọi lại{coSdt ? " (để trống = số đã xác thực)" : ""}
              <input inputMode="tel" value={yc.dien_thoai} placeholder={coSdt ? toi.dien_thoai : "09xx xxx xxx"} onChange={(e) => setYc({ ...yc, dien_thoai: e.target.value })} /></label>
            {loaiYc === "tour_doan" && <label className="v3-field">Ngày mong muốn khởi hành<input type="date" value={yc.ngay_mong_muon} onChange={(e) => setYc({ ...yc, ngay_mong_muon: e.target.value })} /></label>}
            <label className="v3-field">Ghi chú cho Sales<textarea rows={3} value={yc.ghi_chu} placeholder={loaiYc === "tour" ? "Trẻ em, phòng, ăn chay…" : "Điểm đến, ngân sách, số ngày, nhu cầu đặc biệt…"}
              onChange={(e) => setYc({ ...yc, ghi_chu: e.target.value })} /></label>
            <div className="v3-check"><input id="kh-dong-y" type="checkbox" checked={yc.dong_y} onChange={(e) => setYc({ ...yc, dong_y: e.target.checked })} />
              <label htmlFor="kh-dong-y">Tôi hiểu gửi yêu cầu chưa giữ chỗ và chưa thu tiền; giá cuối, chương trình và điều kiện hủy do Sales gửi.</label></div>
          </section>
          <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Tạm tính</h3><Badge c="demo">Chưa phải báo giá</Badge></div>
            {loaiYc === "tour" ? <dl className="v3-stat-rows">
              <div><dt>Giá người lớn</dt><dd>{tien(tourMo?.gia)}</dd></div><div><dt>Số khách</dt><dd>{yc.so_khach}</dd></div></dl>
              : <p>Tour đoàn được báo giá riêng theo hành trình bạn mô tả.</p>}
            {loaiYc === "tour" && <div className="v3-total"><span>Tạm tính theo giá người lớn</span><strong>{tien(tamTinh)}</strong></div>}
            <p>Giá trẻ em, phụ thu phòng đơn và ưu đãi được Sales tính trong báo giá.</p>
            <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy || !yc.dong_y} onClick={guiYc}><span dangerouslySetInnerHTML={{ __html: svg("send") }} style={{ display: "contents" }} /><span>{busy ? "Đang gửi…" : "Gửi yêu cầu"}</span></button>
            <small>Yêu cầu vào hàng chờ Kinh doanh; Sales gọi lại trong giờ làm việc.</small>
          </section></div>}

        {tab === "bookings" && <>
          <section className="v3-panel"><div className="v3-section-title"><h3>Lịch sử đặt dịch vụ</h3></div>
            {!don ? <p>Đang tải…</p> : don.don.length ? <div className="v3-table-wrap"><table>
              <thead><tr><th scope="col">Mã đơn / dịch vụ</th><th scope="col">Phục vụ</th><th scope="col">Thanh toán</th><th scope="col">Giá trị</th><th scope="col"></th></tr></thead>
              <tbody>{don.don.map((d: any) => <tr key={d.ma}><th scope="row">{d.ma}<small>{d.ten} · {ngay(d.khoi_hanh)}</small></th>
                <td><Badge c={d.muc}>{d.phuc_vu}</Badge></td><td>{d.thanh_toan}</td><td>{tien(d.gia_tri)}</td>
                <td><Nut kieu="quiet" i="chevron-right" onClick={() => { setDonMo(d); di("booking"); }}>Chi tiết</Nut></td></tr>)}</tbody></table></div>
              : <p>Chưa có đơn nào gắn với {lienHe}. Đơn hiện ở đây khi số điện thoại hoặc email trên booking trùng liên hệ bạn đã xác thực.</p>}
          </section>
          <DatBanCuaToi />
          <PhongCuaToi />
          <section className="v3-panel"><div className="v3-section-title"><h3>Yêu cầu đã gửi</h3></div>
            {don?.yeu_cau?.length ? <div className="v3-table-wrap"><table>
              <thead><tr><th scope="col">Yêu cầu</th><th scope="col">Số khách</th><th scope="col">Gửi lúc</th><th scope="col">Trạng thái</th></tr></thead>
              <tbody>{don.yeu_cau.map((y: any) => <tr key={y.id}><th scope="row">{y.loai}<small>{y.noi_dung}</small></th><td>{y.so_khach}</td>
                <td>{ngay(y.gui_luc)} {y.gui_luc.slice(11, 16)}</td><td><Badge>{y.trang_thai}</Badge></td></tr>)}</tbody></table></div>
              : <p>Chưa gửi yêu cầu nào.</p>}
          </section>
        </>}

        {tab === "booking" && donMo && <>
          <Nut kieu="quiet" i="arrow-left" onClick={() => di("bookings")}>Quay lại đơn của tôi</Nut>
          <div className="v3-two">
            <section className="v3-panel"><div className="v3-section-title"><h2>{donMo.ten}</h2><Badge c={donMo.muc}>{donMo.phuc_vu}</Badge></div>
              <dl className="v3-stat-rows"><div><dt>Mã đơn</dt><dd>{donMo.ma}</dd></div>
                <div><dt>Ngày đi</dt><dd>{ngay(donMo.khoi_hanh)}{donMo.ket_thuc ? ` – ${ngay(donMo.ket_thuc)}` : ""}</dd></div>
                <div><dt>Số khách</dt><dd>{donMo.so_khach}</dd></div></dl>
              <Nut i="messages-square" onClick={() => { setHtDon(donMo.ma); di("support"); }}>Yêu cầu đổi · hủy · hóa đơn</Nut>
            </section>
            <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Thanh toán</h3><Badge c={donMo.thanh_toan === "Đã thu đủ" ? "good" : "warn"}>{donMo.thanh_toan}</Badge></div>
              <dl className="v3-stat-rows"><div><dt>Giá trị đơn</dt><dd>{tien(donMo.gia_tri)}</dd></div>
                <div><dt>Đã thu (kế toán xác nhận)</dt><dd>{tien(donMo.da_thu)}</dd></div>
                {donMo.dang_xac_nhan > 0 && <div><dt>Đang xác nhận</dt><dd>{tien(donMo.dang_xac_nhan)}</dd></div>}</dl>
              <div className="v3-total"><span>Còn lại</span><strong>{tien(donMo.con_lai)}</strong></div>
              <small>Tiền chỉ ghi «đã thu» khi kế toán xác nhận.</small>
            </section></div>
          {donMo.con_lai > 0 && donMo.muc !== "bad" && <section className="v3-panel"><div className="v3-section-title"><h3>Thanh toán bằng QR chuyển khoản</h3></div>
            <QrThanhToan ma={donMo.ma} /></section>}
        </>}

        {tab === "profile" && <>
          {!hs ? <section className="v3-panel"><p>Đang tải…</p></section> : <>
            <section className="v3-panel"><div className="v3-section-title"><h3>Thông tin tài khoản</h3></div>
              <label className="v3-field">Tên hiển thị<input defaultValue={hs.ho_ten} onBlur={(e) => e.target.value !== hs.ho_ten && luuHs({ ho_ten: e.target.value })} /></label>
              <p className="v3-small">{hs.dien_thoai ? `Điện thoại đã xác minh: ${hs.dien_thoai}` : `Email đã xác minh: ${hs.email}`}. Đổi liên hệ cần xác minh lại — liên hệ Vietourist.</p>
              <label className="v3-field">Sở thích tự chọn<select value={hs.so_thich || ""} onChange={(e) => luuHs({ so_thich: e.target.value })}>
                <option value="">Chưa chọn</option>{hs.so_thich_chon.map((s: string) => <option key={s} value={s}>{s}</option>)}</select></label>
            </section>
            <section className="v3-panel"><div className="v3-section-title"><h3>Quyền riêng tư & thông báo</h3></div>
              <label className="v3-check"><input type="checkbox" checked={!!hs.nhan_tin_quang_cao} onChange={(e) => luuHs({ nhan_tin_quang_cao: e.target.checked })} />Nhận ưu đãi du lịch qua kênh đã đăng ký (tự nguyện, bỏ chọn bất cứ lúc nào).</label>
              <p>Thông báo phục vụ đơn đặt dịch vụ được gửi riêng, không phụ thuộc lựa chọn trên.</p>
              <div className="v3-actions"><Nut i="log-out" onClick={thoat}>Đăng xuất</Nut></div>
            </section></>}
        </>}

        {tab === "rewards" && <DiemUuDai x={diem.x} tai={diem.tai} bao={(m) => setMsg(m)} />}
        {tab === "tier" && <HangThanhVien x={diem.x} />}
        {tab === "favorites" && <YeuThich mo={moTour} />}
        {tab === "reviews" && <DanhGiaKhach diHoTro={() => di("support")} />}
        {tab === "feedback" && <GopYKhach don={don?.don || []} bao={(m) => setMsg(m)} />}
        {tab === "support" && (don ? <HoTroKhach key={htDon} don={don.don} maDon={htDon} /> : <section className="v3-panel"><p>Đang tải…</p></section>)}
        {SAP_RA_MAT[tab] && <SapRaMat tab={tab} />}

        <footer className="v3-bottom"><I n="shield-check" />Dữ liệu và yêu cầu được quản lý tập trung trong VTOS · Vietourist Holdings</footer>
        <nav className="v3-bottom-nav" aria-label="Chức năng nhanh trên điện thoại">{([["home", "Khám phá", "compass"], ["bookings", "Đơn của tôi", "luggage"], ["deals", "Đặt dịch vụ", "plane"], ["support", "Hỗ trợ", "messages-square"], ["profile", "Tài khoản", "user-round"]] as [Tab, string, string][]).map(([k, t, i]) =>
          <button key={k} type="button" className="cursor-interaction" aria-current={menuTab === k ? "page" : undefined} onClick={() => di(k)}><I n={i} /><span>{t}</span></button>)}</nav>
      </main>
    </div>
  </section>);
}
