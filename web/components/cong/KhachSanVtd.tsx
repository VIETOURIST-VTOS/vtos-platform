"use client";
/* KS-13 · Khách sạn hợp tác VTD trên cổng (Chủ tịch duyệt bản demo 30/10/2026) — các bước như Agoda:
   tìm → danh sách (lọc, sắp xếp) → trang khách sạn (album, chọn phòng theo gói giá) → thông tin khách → gửi.
   Ở bước 12a khách GỬI YÊU CẦU GIỮ PHÒNG: Điều hành giữ phòng với khách sạn rồi báo lại (hàng chờ KS-11). Giá
   trên màn do máy chủ tính từ giá Điều hành nhập và TP Điều hành duyệt; trình duyệt không gửi số tiền nào lên.
   KS-14 (Chủ tịch duyệt bản xem thử 30/10/2026): khách sạn có giá đã duyệt thì khách ĐẶT VÀ TRẢ NGAY 100% —
   máy giữ phòng 15 phút, trả QR (máy tự khớp) hoặc thẻ qua cổng SePay (SP-1); Điều hành chốt với khách sạn trong 2 giờ làm
   việc; hủy theo gói. Phòng đã đặt nằm ở «Phòng đã đặt của tôi». Điểm thưởng: khi VTD Rewards chạy. */
import { DaiVideo, VideoO } from "./VideoCong";   // KS-16f
import { useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";
import { diCongThe, goiCong } from "@/lib/cong";
import { DanhGiaKsCong, OD, TomTatDg, VietDanhGiaKs } from "./DanhGiaKs";

type Q = { tinh: string; vao: string; ra: string; nl: number; te: number; phong: number; tuoi?: number[] };
// KS-16j: như Agoda — có trẻ em thì chọn tuổi từng bé (-1 = chưa chọn); máy tính phụ thu theo chính sách khách sạn.
const tuoiStr = (q: Q) => { const t = (q.tuoi || []).slice(0, q.te); return q.te > 0 && t.length === q.te && t.every((x) => x >= 0) ? t.join(",") : ""; };
const tuoiDs = (q: Q) => (tuoiStr(q) ? (q.tuoi || []).slice(0, q.te) : []);
type Loc = { min: number; max: number; coGia: boolean; huy: boolean; sang: boolean; diem9: boolean; sao: number[]; loai: string[]; ten: string };
const LOC0: Loc = { min: 0, max: 0, coGia: false, huy: false, sang: false, diem9: false, sao: [], loai: [], ten: "" };
const vnd = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const themNgay = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };
const THU = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const ngay = (s: string) => { const d = new Date(s + "T00:00:00"); return `${THU[d.getDay()]}, ${d.getDate()} thg ${d.getMonth() + 1}`; };
const MAU: Record<string, string> = { bac: "#1f4e5f", trung: "#7a4a22", tay_nguyen: "#5b4a2e", nam: "#2f5d3a" };
const khongDau = (s: string) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
const nhan = (d?: number | null) => (!d ? "" : d >= 9 ? "Xuất sắc" : d >= 8.5 ? "Tuyệt vời" : d >= 8 ? "Rất tốt" : "Tốt");

const Kinh = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>;
const Ghim = () => <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" /></svg>;
const Tim = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#23252c" strokeWidth="2" aria-hidden="true"><path d="M12 20s-7-4.4-9.2-8.9A5 5 0 0 1 12 6.4a5 5 0 0 1 9.2 4.7C19 15.6 12 20 12 20z" /></svg>;
const Mui = ({ trai }: { trai?: boolean }) => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#23252c" strokeWidth="2.6" aria-hidden="true"><path d={trai ? "m15 6-6 6 6 6" : "m9 6 6 6-6 6"} /></svg>;

function AnhTrong({ k, cao }: { k: any; cao?: number }) {
  const chu = (k.ten || "?").normalize("NFC").trim().charAt(0).toUpperCase();
  return <span className="ksv-trong" style={{ minHeight: cao }}><b style={{ background: MAU[k.mien] || "#3d4b59" }}>{chu}</b><small>Ảnh đang cập nhật</small></span>;
}

export default function KhachSanVtd({ lienHe = "", ten = "" }: { lienHe?: string; ten?: string }) {
  const homNay = iso(new Date());
  const [q, setQ] = useState<Q>({ tinh: "", vao: themNgay(homNay, 7), ra: themNgay(homNay, 9), nl: 2, te: 0, phong: 1 });
  const [ds, setDs] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [loc, setLoc] = useState<Loc>(LOC0);
  const [sx, setSx] = useState("phu_hop");
  const [pop, setPop] = useState(false);
  const [moLoc, setMoLoc] = useState(false);
  const [anhI, setAnhI] = useState<Record<number, number>>({});
  const [thich, setThich] = useState<Record<number, boolean>>({});
  const [ks, setKs] = useState<any>(null);
  const [chon, setChon] = useState<Record<number, number>>({});
  const [buoc, setBuoc] = useState<"ds" | "ks" | "gui" | "xong" | "tra" | "don">("ds");
  const [tinh, setTinh] = useState<any>(null);
  const [kh, setKh] = useState({ ten, lien_he: lienHe, email: "", yc: [] as string[], ghi: "", dongy: false });
  const [tt, setTt] = useState<"qr" | "the">("qr");
  const [donKs, setDonKs] = useState<any>(null);
  const [baoKs, setBaoKs] = useState("");
  const [lamMoi, setLamMoi] = useState(0);
  const [don, setDon] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [vc, setVc] = useState<{ ma: string; ap: any; loi: string }>({ ma: "", ap: null, loi: "" });   // KS-16
  const diem = ks?.diem || ds?.diem;
  const duKien = (tien: number) => diem?.dang_bat && tien > 0 ? Math.floor(tien / (diem.dong_moi_diem || 10000) * diem.he_so) : 0;
  const dem = Math.max(1, Math.round((new Date(q.ra).getTime() - new Date(q.vao).getTime()) / 864e5));

  const tim = async (qq: Q = q) => {
    setLoi(""); setBusy(true);
    try {
      // Lấy mọi thành phố một lần (danh mục nhỏ) rồi lọc ngay trên màn — đổi thành phố không phải chờ máy chủ.
      const p = new URLSearchParams({ tinh: "", vao: qq.vao, ra: qq.ra, nguoi_lon: String(qq.nl), tre_em: String(qq.te), so_phong: String(qq.phong), tuoi: tuoiStr(qq) });
      const r = await goiCong(`/ks-vtd/tim?${p}`);
      setDs(r);
      if (!qq.tinh && r.thanh_pho?.length) setQ({ ...qq, tinh: r.thanh_pho[0].ten });
      setBuoc("ds");
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  useEffect(() => { tim(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  // KS-14: quay về từ trang thẻ OnePay (?ks_vtd=…&the=ok|loi) → mở thẳng trang đơn.
  useEffect(() => {
    try {
      const u = new URLSearchParams(window.location.search), ma = u.get("ks_vtd");
      if (u.get("the") && ma !== null) {
        if (u.get("the") === "ok") setBaoKs("Thanh toán thẻ thành công — Vietourist đang chốt phòng với khách sạn.");
        if (u.get("the") === "cho") setBaoKs("Đã trả qua cổng thẻ — đơn chuyển «Đã thanh toán» ngay khi cổng thẻ báo về (thường vài giây).");
        if (u.get("the") === "huy") setLoi("Bạn đã thoát trang thanh toán thẻ — đơn chưa được trả.");
        else if (u.get("the") === "loi") setLoi("Thanh toán thẻ không thành công — bạn có thể thử lại hoặc dùng QR chuyển khoản.");
        window.history.replaceState(null, "", window.location.pathname);
        if (ma) goiCong(`/ks-vtd/don/${encodeURIComponent(ma)}`).then((d) => { setDonKs(d); setBuoc(d.trang_thai === "cho_tra" ? "tra" : "don"); }).catch(() => {});
      }
    } catch { /* bỏ qua */ }
  }, []);

  const moKs = async (id: number) => {
    setLoi(""); setBusy(true);
    try {
      const p = new URLSearchParams({ vao: q.vao, ra: q.ra, nguoi_lon: String(q.nl), tre_em: String(q.te), so_phong: String(q.phong), tuoi: tuoiStr(q) });
      setKs(await goiCong(`/ks-vtd/${id}?${p}`)); setChon({}); setBuoc("ks"); window.scrollTo(0, 0);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  const loc2 = useMemo(() => {
    if (!ds) return [];
    const L = loc, k0 = khongDau(L.ten.trim());
    let r = ds.khach_san.filter((k: any) => (!q.tinh || k.tinh_thanh === q.tinh)).filter((k: any) => {
      const g = k.gia_tu?.gia_dem;
      if (L.coGia && !k.gia_tu) return false;
      if (L.huy && !k.co_mien_phi_huy) return false;
      if (L.sang && !k.co_bua_sang) return false;
      if (L.diem9 && !((k.danh_gia?.diem_tb || 0) >= 9)) return false;
      if (L.sao.length && !L.sao.includes(k.sao)) return false;
      if (L.loai.length && !L.loai.includes(k.loai)) return false;
      if (k0 && !khongDau(`${k.ten} ${k.khu_vuc} ${k.gan}`).includes(k0)) return false;
      if (g != null && (g < L.min || (L.max && g > L.max))) return false;
      return true;
    });
    const gia = (k: any, mac: number) => k.gia_tu?.gia_dem ?? mac;
    const f: Record<string, (a: any, b: any) => number> = {
      phu_hop: (a, b) => (+!a.gia_tu) - (+!b.gia_tu) || (b.danh_gia?.diem_tb || 0) - (a.danh_gia?.diem_tb || 0) || a.ten.localeCompare(b.ten),
      gia_thap: (a, b) => gia(a, 9e12) - gia(b, 9e12), gia_cao: (a, b) => gia(b, -1) - gia(a, -1),
      diem: (a, b) => (b.danh_gia?.diem_tb || 0) - (a.danh_gia?.diem_tb || 0), sao: (a, b) => b.sao - a.sao,
      gan: (a, b) => (a.km_trung_tam ?? 999) - (b.km_trung_tam ?? 999),
    };
    return [...r].sort(f[sx]);
  }, [ds, loc, sx, q.tinh]);
  const trongTp = (ds?.khach_san || []).filter((k: any) => !q.tinh || k.tinh_thanh === q.tinh);
  const dem2 = (f: (k: any) => boolean) => trongTp.filter(f).length;
  const giaMax = Math.max(500000, ...trongTp.map((k: any) => k.gia_tu?.gia_dem || 0));

  const dongChon = useMemo(() => (ks?.phong || []).flatMap((p: any) => p.goi.filter((g: any) => chon[g.id]).map((g: any) => ({ p, g, n: chon[g.id] }))), [ks, chon]);
  // KS-14: số phòng chọn được ở một gói = số còn của loại phòng trừ số đã chọn ở các gói khác cùng loại.
  const conCho = (p: any, gid: number) => Math.max(0, (p.con ?? p.so_phong) - p.goi.filter((g: any) => g.id !== gid).reduce((a: number, g: any) => a + (chon[g.id] || 0), 0));
  const soChon = dongChon.reduce((a: number, x: any) => a + x.n, 0);
  const tienChon = dongChon.reduce((a: number, x: any) => a + x.n * x.g.tong, 0);

  const sangGui = async () => {
    setLoi(""); setBusy(true);
    try {
      setTinh(await goiCong(`/ks-vtd/${ks.id}/tinh`, { vao: q.vao, ra: q.ra, chon: dongChon.map((x: any) => ({ goi_id: x.g.id, so: x.n })),
        nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q) }));
      setVc({ ma: "", ap: null, loi: "" });
      setBuoc("gui"); window.scrollTo(0, 0);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const moYeuCauTrong = (loaiPhong = "") => { setTinh({ dong: [], so_phong: q.phong, tien_phong: 0, thue_phi: 0, tong: 0, dem, loai_phong: loaiPhong }); setBuoc("gui"); window.scrollTo(0, 0); };
  const gui = async () => {
    if (kh.ten.trim().split(/\s+/).length < 2) { setLoi("Ghi đủ họ và tên người nhận phòng"); return; }
    if (kh.lien_he.replace(/\D/g, "").length < 9 && !/@/.test(kh.lien_he)) { setLoi("Ghi số điện thoại / Zalo hoặc email để Vietourist báo lại"); return; }
    if (!kh.dongy) { setLoi("Đánh dấu đồng ý điều kiện giữ phòng để gửi"); return; }
    setLoi(""); setBusy(true);
    try {
      const r = await goiCong(`/ks-vtd/${ks.id}/yeu-cau`, { ngay_nhan: q.vao, ngay_tra: q.ra, nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q), so_phong: tinh?.so_phong || q.phong,
        chon: dongChon.map((x: any) => ({ goi_id: x.g.id, so: x.n })), loai_phong: tinh?.loai_phong || "",
        nguoi_nhan_phong: kh.ten, lien_he: kh.lien_he, yeu_cau_them: [kh.yc.join(", "), kh.ghi].filter(Boolean).join(" · ") });
      setDon(r.don); setBuoc("xong"); window.scrollTo(0, 0);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  const apVoucher = async () => {
    if (!vc.ma.trim()) { setVc({ ...vc, loi: "Ghi mã voucher" }); return; }
    setBusy(true);
    try { setVc({ ...vc, ap: await goiCong(`/ks-vtd/don/kiem-voucher`, { ma: vc.ma.trim(), tong: tinh.tong }), loi: "" }); }
    catch (x: any) { setVc({ ...vc, ap: null, loi: x.message }); } finally { setBusy(false); }
  };
  const giam = vc.ap?.gia_tri || 0;

  const datNgay = async () => {
    if (kh.ten.trim().split(/\s+/).length < 2) { setLoi("Ghi đủ họ và tên khách nhận phòng"); return; }
    if (kh.lien_he.replace(/\D/g, "").length < 9) { setLoi("Ghi số điện thoại / Zalo để Vietourist báo xác nhận"); return; }
    if (kh.email && !/^\S+@\S+\.\S+$/.test(kh.email)) { setLoi("Email chưa đúng"); return; }
    if (!kh.dongy) { setLoi("Đánh dấu đồng ý chính sách hủy và điều kiện đặt phòng"); return; }
    setLoi(""); setBusy(true);
    try {
      const r = await goiCong(`/ks-vtd/don/dat/${ks.id}`, { vao: q.vao, ra: q.ra, nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q),
        chon: dongChon.map((x: any) => ({ goi_id: x.g.id, so: x.n })), ho_ten: kh.ten, lien_he: kh.lien_he, email: kh.email,
        yeu_cau: [kh.yc.join(", "), kh.ghi].filter(Boolean).join(" · "), dong_y: kh.dongy, ma_voucher: vc.ap?.ma || "" });
      setDonKs(r.don);
      if (tt === "the") {
        diCongThe(await goiCong(`/ks-vtd/don/${encodeURIComponent(r.don.ma)}/the`, {})); return;
      }
      setBuoc("tra"); window.scrollTo(0, 0);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const moDon = (d: any) => { setDonKs(d); setBaoKs(""); setBuoc(d.trang_thai === "cho_tra" && d.co_the_tra ? "tra" : "don"); window.scrollTo(0, 0); };

  const thanhTim = <div className="ksv-band"><form className="ksv-search" onSubmit={(e) => { e.preventDefault(); setPop(false); tim(); }}>
    <label className="ksv-sbox"><Kinh /><span style={{ flex: 1, minWidth: 0 }}><small>Điểm đến</small>
      <select value={q.tinh} onChange={(e) => { const q2 = { ...q, tinh: e.target.value }; setQ(q2); setLoc(LOC0); }} aria-label="Điểm đến">
        {(ds?.thanh_pho || []).map((t: any) => <option key={t.ten} value={t.ten}>{t.ten} ({t.so})</option>)}
        {!(ds?.thanh_pho || []).length && <option value="">Chưa có khách sạn</option>}</select></span></label>
    <div className="ksv-sbox ksv-dates"><label><small>Nhận phòng</small><input type="date" value={q.vao} min={homNay} onChange={(e) => { const v = e.target.value; setQ({ ...q, vao: v, ra: q.ra <= v ? themNgay(v, 1) : q.ra }); }} /></label>
      <label><small>Trả phòng · {dem} đêm</small><input type="date" value={q.ra} min={themNgay(q.vao, 1)} onChange={(e) => e.target.value > q.vao && setQ({ ...q, ra: e.target.value })} /></label></div>
    <div className="ksv-sbox" style={{ position: "relative" }}><button type="button" className="ksv-khach" onClick={() => setPop(!pop)} aria-expanded={pop}>
      <small>Khách &amp; phòng</small><b>{q.nl} người lớn{q.te ? ` · ${q.te} trẻ em` : ""} · {q.phong} phòng</b></button>
      {pop && <div className="ksv-pop">{([["nl", "Người lớn", 1, 30], ["te", "Trẻ em", 0, 20], ["phong", "Phòng", 1, 9]] as const).map(([k, t, a, b]) =>
        <div key={k} className="ksv-step"><span>{t}</span><div>
          <button type="button" aria-label={`Bớt ${t}`} onClick={() => setQ({ ...q, [k]: Math.max(a, q[k] - 1) })}>−</button><b>{q[k]}</b>
          <button type="button" aria-label={`Thêm ${t}`} onClick={() => setQ({ ...q, [k]: Math.min(b, q[k] + 1) })}>+</button></div></div>)}
        {q.te > 0 && <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>{Array.from({ length: q.te }, (_, i) =>
          <label key={i} style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>Tuổi trẻ {i + 1}
            <select className="ksv-sel" value={(q.tuoi || [])[i] ?? -1} onChange={(e) => { const t = Array.from({ length: q.te }, (_x, j) => (q.tuoi || [])[j] ?? -1); t[i] = Number(e.target.value); setQ({ ...q, tuoi: t }); }}>
              <option value={-1}>Chọn tuổi</option>{Array.from({ length: 18 }, (_x, n) => <option key={n} value={n}>{n} tuổi</option>)}</select></label>)}
          <small className="ksv-muted" style={{ gridColumn: "1 / -1" }}>Chọn tuổi từng bé để xem giá đúng chính sách trẻ em của khách sạn.</small></div>}
        <button type="button" className="ksv-btn" onClick={() => setPop(false)}>Xong</button></div>}</div>
    <button className="ksv-btn-tim" type="submit" disabled={busy}>TÌM</button></form></div>;

  const css = <style>{CSS}</style>;
  if (!ds) return <div className="ksv">{css}<p>{loi || "Đang tải khách sạn…"}</p></div>;

  if (buoc === "tra" && donKs) return <div className="ksv">{css}
    <TraTien d={donKs} onDoi={(d) => { setDonKs(d); setLamMoi((x) => x + 1); if (d.trang_thai !== "cho_tra") { setBuoc("don"); window.scrollTo(0, 0); } }}
      onLai={() => { setBuoc("ds"); setKs(null); setChon({}); setDonKs(null); }} /></div>;

  if (buoc === "don" && donKs) return <div className="ksv">{css}
    <DonKs d={donKs} bao={baoKs} loi={loi} onDoi={(d) => { setDonKs(d); setLamMoi((x) => x + 1); }} onTra={() => setBuoc("tra")}
      onLai={() => { setBuoc("ds"); setKs(null); setChon({}); setDonKs(null); setBaoKs(""); setLoi(""); }} /></div>;

  if (buoc === "xong" && don) return <div className="ksv">{css}
    <div className="ksv-steps"><span className="xong"><b>✓</b>Chọn phòng</span><hr /><span className="xong"><b>✓</b>Thông tin của bạn</span><hr /><span className="on"><b>3</b>Đã gửi yêu cầu</span></div>
    <section className="ksv-panel" style={{ padding: 24 }}>
      <span className="ksv-ok" style={{ alignSelf: "flex-start" }}><b>✓ Đã gửi yêu cầu giữ phòng</b></span>
      <h2 style={{ margin: 0, fontSize: 24 }}>Vietourist đang giữ phòng cho bạn</h2>
      <span style={{ fontSize: 15 }}>Mã yêu cầu <b style={{ fontSize: 18 }}>{don.the_tham_chieu}</b> · {ks.ten}</span>
      <span>{ngay(q.vao)} → {ngay(q.ra)} · {don.so_phong} phòng · {don.nguoi_lon} người lớn{don.tre_em ? ` · ${don.tre_em} trẻ em` : ""}</span>
      <span className="ksv-muted">Điều hành Vietourist liên hệ khách sạn giữ phòng rồi báo lại qua {kh.lien_he} trong giờ làm việc. Bạn chưa phải trả tiền ở bước này. Theo dõi yêu cầu ở mục «Yêu cầu đặt phòng của bạn» bên dưới.</span>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}><button type="button" className="ksv-btn" onClick={() => { setBuoc("ds"); setKs(null); setChon({}); }}>Tìm chỗ ở khác</button></div>
    </section></div>;

  const coGia = !!(tinh && tinh.dong?.length);
  if (buoc === "gui" && ks && tinh) return <div className="ksv">{css}
    <div className="ksv-steps"><span className="xong"><b>✓</b>Chọn phòng</span><hr /><span className="on"><b>2</b>{coGia ? "Thông tin & thanh toán" : "Thông tin của bạn"}</span><hr /><span><b>3</b>{coGia ? "Khách sạn xác nhận" : "Gửi yêu cầu"}</span>
      <button type="button" className="ksv-link" style={{ marginLeft: "auto" }} onClick={() => setBuoc("ks")}>← Quay lại chọn phòng</button></div>
    <div className="ksv-co">
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>Ai là khách chính?</h2>
          <div className="ksv-f2">
            <label className="ksv-fld">Họ và tên (như trên CCCD / hộ chiếu)<input value={kh.ten} onChange={(e) => setKh({ ...kh, ten: e.target.value })} autoComplete="name" /></label>
            <label className="ksv-fld">{coGia ? "Số điện thoại / Zalo" : "Số điện thoại / Zalo hoặc email"}<input value={kh.lien_he} onChange={(e) => setKh({ ...kh, lien_he: e.target.value })} autoComplete="tel" /></label>
            {coGia && <label className="ksv-fld">Email nhận xác nhận (không bắt buộc)<input type="email" value={kh.email} onChange={(e) => setKh({ ...kh, email: e.target.value })} autoComplete="email" /></label>}</div></section>
        <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Yêu cầu đặc biệt</h2><small className="ksv-muted">Khách sạn sẽ cố gắng đáp ứng, nhưng không bảo đảm.</small>
          <div className="ksv-f2" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))" }}>{["Phòng không hút thuốc", "Tầng cao", "Giường đôi lớn", "Nhận phòng sớm", "Trả phòng muộn", "Đưa đón sân bay"].map((t) =>
            <label key={t} className="ksv-chk"><input type="checkbox" checked={kh.yc.includes(t)} onChange={(e) => setKh({ ...kh, yc: e.target.checked ? [...kh.yc, t] : kh.yc.filter((x) => x !== t) })} /><span>{t}</span></label>)}</div>
          <label className="ksv-fld">Ghi thêm<textarea value={kh.ghi} onChange={(e) => setKh({ ...kh, ghi: e.target.value })} maxLength={800} /></label></section>
        {coGia ? <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Chọn cách thanh toán</h2>
          {([["qr", "Chuyển khoản / quét mã QR", "Ngân hàng báo về, đơn tự chuyển «Đã thanh toán» trong 1–3 phút", "Không mất phí"],
            ["the", "Thẻ ATM nội địa / Visa / Mastercard / JCB", "Chuyển sang cổng thanh toán SePay — Vietourist không thấy và không lưu số thẻ", ""]] as const).filter(([v]) => v !== "the" || ks.the_bat).map(([v, t, m, n]) =>
            <label key={v} className={`ksv-pay ${tt === v ? "on" : ""}`}><input type="radio" name="ksv-tt" checked={tt === v} onChange={() => setTt(v)} />
              <span style={{ flex: 1 }}><b>{t}</b><br /><small className="ksv-muted">{m}</small></span>{n && <b className="ksv-okc" style={{ fontSize: 12 }}>{n}</b>}</label>)}
          <small className="ksv-muted">Phòng được giữ 15 phút sau khi bấm thanh toán. Trả đủ 100%; hủy theo chính sách của gói đã chọn.</small></section>
          : <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Thanh toán</h2>
          <span className="ksv-muted">Vietourist giữ phòng với khách sạn rồi gửi hướng dẫn thanh toán cho bạn. Trang này không nhận số thẻ.</span></section>}
        {coGia && diem?.dang_bat && <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Mã voucher VTD Rewards</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input className="ksv-vc" value={vc.ma} onChange={(e) => setVc({ ma: e.target.value.toUpperCase(), ap: null, loi: "" })} placeholder="VTD-XXXXXX" aria-label="Mã voucher" />
            {vc.ap ? <button type="button" className="ksv-btn line" onClick={() => setVc({ ma: "", ap: null, loi: "" })}>Bỏ voucher</button>
              : <button type="button" className="ksv-btn line" disabled={busy} onClick={apVoucher}>Áp dụng</button>}</div>
          {vc.ap && <span className="ksv-okc">Đã áp {vc.ap.ma} · giảm ₫ {vnd(vc.ap.gia_tri)} (tối đa 5% đơn = ₫ {vnd(vc.ap.tran)})</span>}
          {vc.loi && <span className="ksv-loi" style={{ padding: "8px 12px" }}>{vc.loi}</span>}
          <small className="ksv-muted">Đổi điểm lấy voucher ở mục «Điểm VTD Rewards». Hủy đơn được hoàn tiền thì điểm của voucher trả lại.</small></section>}
        {loi && <div className="ksv-loi">{loi}</div>}
        <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "16px 20px" }}>
          <label className="ksv-chk" style={{ flex: 1, minWidth: 220, alignItems: "flex-start" }}><input type="checkbox" checked={kh.dongy} onChange={(e) => setKh({ ...kh, dongy: e.target.checked })} />
            <span style={{ fontSize: 13 }}>{coGia ? "Tôi đã đọc và đồng ý chính sách hủy phòng của gói đã chọn và điều kiện đặt phòng của khách sạn và Vietourist."
              : "Tôi đồng ý để Vietourist liên hệ giữ phòng theo thông tin trên. Giá và chính sách hủy theo gói đã chọn."}</span></label>
          {coGia ? <button type="button" className="ksv-btn" style={{ minHeight: 52, padding: "0 28px", fontSize: 16 }} disabled={busy} onClick={datNgay}>Thanh toán ₫ {vnd(tinh.tong - giam)}</button>
            : <button type="button" className="ksv-btn" style={{ minHeight: 52, padding: "0 28px", fontSize: 16 }} disabled={busy} onClick={gui}>Gửi yêu cầu giữ phòng</button>}</div>
      </div>
      <TomTat ks={ks} q={q} tinh={tinh} giam={giam} maVc={vc.ap?.ma} hang={diem?.dang_bat ? diem : null} diemDk={duKien(tinh.tong - giam)} />
    </div></div>;

  if (buoc === "ks" && ks) return <div className="ksv">{css}
    <button type="button" className="ksv-link" onClick={() => setBuoc("ds")}>← Khách sạn ở {ks.tinh_thanh}</button>
    <div className="ksv-gal">{ks.anh.length || ks.video?.length ? <>
      {ks.video?.length > 0 && <span key="v0"><VideoO v={ks.video[0]} ten={ks.ten} /></span>}
      {ks.anh.slice(0, ks.video?.length ? 3 : 4).map((a: any, i: number) => <span key={a.id}><img src={i || ks.video?.length ? a.nho : a.hien} alt={a.chu_thich || `${ks.ten} — ${a.nhom_ten}`} loading="lazy" /></span>)}
      <span className="ksv-more">{ks.so_anh} ảnh{ks.so_video ? ` · ${ks.so_video} video` : ""}</span></> : <span style={{ gridColumn: "1 / -1" }}><AnhTrong k={ks} cao={260} /></span>}</div>
    {ks.video?.length > 1 && <DaiVideo video={ks.video} ten={ks.ten} bo={1} />}
    <nav className="ksv-tabs">{[["ksv-tq", "Tổng quan"], ["ksv-phong", "Phòng"], ["ksv-tn", "Tiện nghi"], ["ksv-cs", "Chính sách"], ["ksv-dg", "Đánh giá"]].map(([id, t]) =>
      <a key={id} href={`#${id}`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); }}>{t}</a>)}
      <span className="ksv-tp">{ks.gia_tu && <><small className="ksv-muted">từ</small><b className="ksv-big" style={{ fontSize: 19 }}>₫ {vnd(ks.gia_tu.gia_dem)}</b></>}
        <button type="button" className="ksv-btn" onClick={() => document.getElementById("ksv-phong")?.scrollIntoView({ behavior: "smooth" })}>Xem phòng</button></span></nav>
    <div className="ksv-two" id="ksv-tq">
      <div className="ksv-panel" style={{ padding: 20 }}><div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}><h2 style={{ margin: 0, fontSize: 26 }}>{ks.ten}</h2>{ks.sao > 0 && <span className="ksv-stars" aria-label={`${ks.sao} sao`}>{"★".repeat(ks.sao)}</span>}</div>
        <span className="ksv-where" style={{ color: "inherit", fontWeight: 500 }}><Ghim />{[ks.dia_chi, ks.khu_vuc, ks.tinh_thanh].filter(Boolean).join(", ")}</span>
        {ks.tien_ich.length > 0 && <div className="ksv-feat">{ks.tien_ich.slice(0, 5).map((t: string) => <span key={t}>{t}</span>)}</div>}
        <p style={{ margin: "4px 0 0", fontSize: 15, lineHeight: 1.65, whiteSpace: "pre-line", maxWidth: "68ch" }}>{ks.mo_ta || "Vietourist đang biên tập phần giới thiệu."}</p>
        {ks.gan && <span className="ksv-muted">{ks.gan}</span>}</div>
      <TomTatDg dg={ks.danh_gia} /></div>
    <div id="ksv-phong" style={{ display: "flex", flexDirection: "column", gap: 12, paddingBottom: soChon ? 90 : 16 }}>
      <div className="ksv-rhead"><h2 style={{ margin: 0, fontSize: 22 }}>Chọn phòng · {ks.dem} đêm · {q.nl} người lớn{q.te ? ` · ${q.te} trẻ em` : ""}</h2><span className="ksv-muted">{ngay(ks.vao)} → {ngay(ks.ra)}</span></div>
      {loi && <div className="ksv-loi">{loi}</div>}
      {!ks.phong.length && <div className="ksv-panel">Khách sạn chưa nhập loại phòng. <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong()}>Gửi yêu cầu giữ phòng</button></div>}
      {ks.phong.map((p: any) => <div key={p.id} className="ksv-room">
        <div className="ksv-rl"><b style={{ fontSize: 17 }}>{p.ten}</b>
          {p.anh?.[0] ? <img src={p.anh[0].nho} alt={p.ten} className="ksv-rp" loading="lazy" /> : <AnhTrong k={ks} cao={110} />}
          {p.video?.[0] && <div style={{ aspectRatio: "16 / 9", maxWidth: "100%" }}><VideoO v={p.video[0]} ten={p.ten} nhan="VIDEO PHÒNG" /></div>}
          <span className="ksv-muted" style={{ fontSize: 13 }}>{[p.dien_tich ? `${p.dien_tich} m²` : "", p.giuong].filter(Boolean).join(" · ")}{p.mo_ta && <><br />{p.mo_ta}</>}
            {(p.tien_nghi || []).length > 0 && <><br />{p.tien_nghi.join(" · ")}</>}
            <br />Tối đa {p.toi_da_nguoi_lon} người lớn{p.toi_da_tre_em ? ` + ${p.toi_da_tre_em} trẻ em` : ""}{p.giuong_phu_toi_da ? ` · kê được ${p.giuong_phu_toi_da} giường phụ` : ""}</span>
          {p.mo_ta_dai && <details><summary style={{ cursor: "pointer", fontSize: 13 }}>Xem thêm</summary><p className="ksv-muted" style={{ fontSize: 13, whiteSpace: "pre-line", margin: "4px 0 0" }}>{p.mo_ta_dai}</p></details>}
          {p.vua && p.phu_thu_ky > 0 && <small style={{ fontWeight: 600 }}>+ phụ thu ₫ {vnd(p.phu_thu_ky)} cho {q.phong} phòng × {ks.dem} đêm ({(p.phu_thu_ct || []).join(", ")}) — máy cộng vào tổng</small>}
          {!p.vua && <small style={{ color: "var(--ksv-price)", fontWeight: 600 }}>{p.ly_do || `Không đủ chỗ cho ${q.nl} người lớn / ${q.phong} phòng — tăng số phòng`}</small>}
          {!p.vua && /gửi yêu cầu/.test(p.ly_do || "") && <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong(p.ten)}>Gửi yêu cầu giữ phòng</button>}</div>
        <div className="ksv-rates">{p.goi.length ? <><div className="ksv-rhd"><span>Lợi ích</span><span>Số khách</span><span>Giá mỗi đêm</span><span>Số phòng</span></div>
          {p.goi.map((g: any) => <div key={g.id} className="ksv-rate">
            <div><ul>{g.mien_phi_huy ? <li className="ksv-okc"><b>✓ Miễn phí hủy trước {g.huy_han ? g.huy_han.split("-").reverse().join("/") : ""}</b></li> : <li className="ksv-muted"><b>Không hoàn tiền</b></li>}
              <li>{g.bua_sang ? "✓ Bữa sáng" : "Chỉ phòng"}{["chỉ phòng", "có bữa sáng", "bữa sáng"].includes(String(g.ten || "").trim().toLowerCase()) ? "" : ` · ${g.ten}`}</li><li>✓ Giá hợp đồng của Vietourist</li></ul></div>
            <div><b>{p.toi_da_nguoi_lon} người</b></div>
            <div>{g.niem_yet_dem && <><span className="ksv-old" style={{ fontSize: 13 }}>{vnd(g.niem_yet_dem)}</span><br /></>}<b className="ksv-big" style={{ fontSize: 20 }}>₫ {vnd(g.gia_dem)}</b><br /><small className="ksv-muted">chưa gồm thuế phí</small>
              {ks.dem > 1 && <><br /><small className="ksv-muted">₫ {vnd(g.tong)} / {ks.dem} đêm</small></>}</div>
            <div>{(p.con ?? p.so_phong) > 0 ? <><select className="ksv-sel" style={{ width: "100%" }} aria-label={`Số phòng ${p.ten} ${g.ten}`} disabled={!p.vua} value={chon[g.id] || 0}
              onChange={(e) => setChon({ ...chon, [g.id]: Number(e.target.value) })}>{Array.from({ length: Math.min(conCho(p, g.id), 9) + 1 }, (_, n) => <option key={n} value={n}>{n} phòng</option>)}</select>
              {(p.con ?? 9) <= 3 && <small style={{ color: "var(--ksv-price)", fontWeight: 600 }}>Chỉ còn {p.con} phòng</small>}</>
              : <b style={{ color: "var(--ksv-price)" }}>Hết phòng</b>}</div>
          </div>)}</> : <div style={{ padding: 16, display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ flex: 1, minWidth: 200 }}><b>Giá {ngay(ks.vao)} – {ngay(ks.ra)} đang cập nhật</b><br /><span className="ksv-muted">Gửi yêu cầu, Vietourist báo giá và giữ phòng cho bạn.</span></span>
            <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong(p.ten)}>Gửi yêu cầu giữ phòng</button></div>}</div></div>)}
    </div>
    <div className="ksv-grid2"><div className="ksv-panel" id="ksv-tn"><b style={{ fontSize: 18 }}>Tiện nghi</b>
      {ks.tien_ich.length ? <div className="ksv-grid2" style={{ gap: 8 }}>{ks.tien_ich.map((t: string) => <span key={t}>✓ {t}</span>)}</div> : <span className="ksv-muted">Đang cập nhật</span>}</div>
      <div className="ksv-panel" id="ksv-cs"><b style={{ fontSize: 18 }}>Chính sách chỗ ở</b>
        <span><b>Nhận phòng</b> từ {ks.gio_nhan} · <b>Trả phòng</b> trước {ks.gio_tra}</span>
        {ks.chinh_sach.tre ? <span><b>Trẻ em &amp; giường phụ</b>{ks.chinh_sach.tre.dong.map((d: string, i: number) => <span key={i} style={{ display: "block" }}>{d}</span>)}</span>
          : <>{ks.chinh_sach.tre_em && <span><b>Trẻ em</b> {ks.chinh_sach.tre_em}</span>}{ks.chinh_sach.giuong_phu && <span><b>Giường phụ</b> {ks.chinh_sach.giuong_phu}</span>}</>}
        {ks.chinh_sach.vat_nuoi && <span><b>Vật nuôi</b> {ks.chinh_sach.vat_nuoi}</span>}{ks.chinh_sach.khac && <span style={{ whiteSpace: "pre-line" }}>{ks.chinh_sach.khac}</span>}
        <span><b>Hủy phòng</b> theo từng gói giá đã chọn</span></div></div>
    <DanhGiaKsCong kid={ks.id} />
    {soChon > 0 && <div className="ksv-total"><span style={{ flex: 1, minWidth: 180 }}><b>{soChon} phòng · {ks.dem} đêm</b><br /><small className="ksv-muted">{dongChon.map((x: any) => `${x.n} × ${x.p.ten} (${x.g.ten})`).join(" · ")}</small></span>
      <span style={{ textAlign: "right" }}><b className="ksv-big" style={{ fontSize: 22 }}>₫ {vnd(tienChon)}</b><br /><small className="ksv-muted">+ thuế phí ₫ {vnd(tienChon * (ks.thue_phi_pt || 0) / 100)}</small>
        {dongChon.some((x: any) => x.p.phu_thu_ky > 0) && <><br /><small className="ksv-muted">+ phụ thu trẻ em / giường phụ (tính ở bước sau)</small></>}</span>
      <button type="button" className="ksv-btn" style={{ minHeight: 50, padding: "0 26px", fontSize: 16 }} disabled={busy} onClick={sangGui}>Đặt ngay</button></div>}
  </div>;

  const L = loc;
  return <div className="ksv">{css}{thanhTim}
    <PhongCuaToi gon lamMoi={lamMoi} onMo={moDon} />
    <div className="ksv-layout">
      <aside className={`ksv-loc ${moLoc ? "open" : ""}`} aria-label="Bộ lọc">
        {moLoc && <div className="ksv-rhead"><b style={{ fontSize: 20 }}>Bộ lọc</b><button type="button" className="ksv-btn" onClick={() => setMoLoc(false)}>Xem {loc2.length} kết quả</button></div>}
        <label className="ksv-pill"><Kinh /><input placeholder="Tìm theo tên khách sạn" value={L.ten} onChange={(e) => setLoc({ ...L, ten: e.target.value })} aria-label="Tìm theo tên khách sạn" /></label>
        <div className="ksv-panel"><b>Ngân sách mỗi đêm</b>
          <div className="ksv-mm"><label>TỐI THIỂU<input inputMode="numeric" value={`₫ ${vnd(L.min)}`} onChange={(e) => setLoc({ ...L, min: Number(e.target.value.replace(/\D/g, "")) || 0 })} /></label>
            <label>TỐI ĐA<input inputMode="numeric" value={`₫ ${vnd(L.max || giaMax)}`} onChange={(e) => setLoc({ ...L, max: Number(e.target.value.replace(/\D/g, "")) || 0 })} /></label></div>
          <input type="range" min={0} max={giaMax} step={50000} value={L.max || giaMax} onChange={(e) => setLoc({ ...L, max: Number(e.target.value) })} aria-label="Giá tối đa mỗi đêm" /></div>
        <div className="ksv-panel"><b>Lọc phổ biến{q.tinh ? ` ở ${q.tinh}` : ""}</b>
          {([["coGia", "Có giá đặt ngay", (k: any) => !!k.gia_tu], ["huy", "Miễn phí hủy", (k: any) => k.co_mien_phi_huy], ["sang", "Bao gồm bữa sáng", (k: any) => k.co_bua_sang],
            ["diem9", "Khách chấm 9+ Xuất sắc", (k: any) => (k.danh_gia?.diem_tb || 0) >= 9]] as const).map(([k, t, f]) =>
            <label key={k} className="ksv-chk"><input type="checkbox" checked={L[k]} onChange={(e) => setLoc({ ...L, [k]: e.target.checked })} /><span>{t}</span><small>{dem2(f)}</small></label>)}</div>
        <div className="ksv-panel"><b>Hạng sao</b>{[5, 4, 3, 2, 1].filter((s) => dem2((k) => k.sao === s)).map((s) =>
          <label key={s} className="ksv-chk"><input type="checkbox" checked={L.sao.includes(s)} onChange={(e) => setLoc({ ...L, sao: e.target.checked ? [...L.sao, s] : L.sao.filter((x) => x !== s) })} />
            <span className="ksv-stars">{"★".repeat(s)}</span><small>{dem2((k) => k.sao === s)}</small></label>)}
          <b style={{ marginTop: 4 }}>Loại chỗ ở</b>{Object.entries(ds.loai || {}).filter(([k]) => dem2((x) => x.loai === k)).map(([k, t]: any) =>
            <label key={k} className="ksv-chk"><input type="checkbox" checked={L.loai.includes(k)} onChange={(e) => setLoc({ ...L, loai: e.target.checked ? [...L.loai, k] : L.loai.filter((x) => x !== k) })} />
              <span>{t}</span><small>{dem2((x) => x.loai === k)}</small></label>)}
          <button type="button" className="ksv-btn line" onClick={() => setLoc(LOC0)}>Xóa bộ lọc</button></div>
      </aside>
      <main style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        {ds.diem?.dang_bat && <div className="ksv-hv">Hội viên <b>{ds.diem.hang}</b> · điểm ×{String(ds.diem.he_so).replace(".", ",")} — mỗi kỳ ở qua Vietourist được tích điểm VTD Rewards</div>}
        <div className="ksv-rhead"><h2 style={{ margin: 0, fontSize: 22 }}>{loc2.length} chỗ ở{q.tinh ? ` tại ${q.tinh}` : ""}</h2>
          <div style={{ display: "flex", gap: 8 }}><button type="button" className="ksv-btn line ksv-fbtn" onClick={() => setMoLoc(true)}>Bộ lọc</button>
            <select className="ksv-sel" value={sx} onChange={(e) => setSx(e.target.value)} aria-label="Sắp xếp">
              {[["phu_hop", "Phù hợp nhất"], ["gia_thap", "Giá thấp nhất trước"], ["gia_cao", "Giá cao nhất trước"], ["diem", "Điểm đánh giá"], ["sao", "Hạng sao"], ["gan", "Gần trung tâm nhất"]].map(([k, t]) =>
                <option key={k} value={k}>Sắp xếp: {t}</option>)}</select></div></div>
        {loi && <div className="ksv-loi">{loi}</div>}
        {!loc2.length && <div className="ksv-panel" style={{ textAlign: "center" }}><b>{trongTp.length ? "Không có chỗ ở khớp bộ lọc." : "Vietourist đang bổ sung khách sạn hợp tác ở đây."}</b>
          {trongTp.length > 0 && <button type="button" className="ksv-btn line" onClick={() => setLoc(LOC0)}>Xóa bộ lọc</button>}</div>}
        {loc2.map((k: any) => { const i = (anhI[k.id] || 0) % Math.max(1, k.anh.length), a = k.anh[i], g = k.gia_tu;
          return <article key={k.id} className="ksv-card">
            {g && k.co_mien_phi_huy && k.co_bua_sang && <div className="ksv-bar"><span>Giá hợp đồng của Vietourist</span><em>Miễn phí hủy</em><em>Bữa sáng</em></div>}
            <div className="ksv-crow">
              <div className="ksv-ph">{a ? <button type="button" className="ksv-phbtn" onClick={() => moKs(k.id)} aria-label={`Xem ${k.ten}`}><img src={a.nho} alt={a.chu_thich || k.ten} loading="lazy" /></button>
                : <button type="button" className="ksv-phbtn" onClick={() => moKs(k.id)} aria-label={`Xem ${k.ten}`}><AnhTrong k={k} /></button>}
                <button type="button" className={`ksv-ico ksv-heart ${thich[k.id] ? "on" : ""}`} aria-label={thich[k.id] ? "Bỏ yêu thích" : "Lưu vào yêu thích"} aria-pressed={!!thich[k.id]} onClick={() => setThich({ ...thich, [k.id]: !thich[k.id] })}><Tim /></button>
                {k.anh.length > 1 && <><button type="button" className="ksv-ico ksv-prv" aria-label="Ảnh trước" onClick={() => setAnhI({ ...anhI, [k.id]: (i - 1 + k.anh.length) % k.anh.length })}><Mui trai /></button>
                  <button type="button" className="ksv-ico ksv-nxt" aria-label="Ảnh tiếp" onClick={() => setAnhI({ ...anhI, [k.id]: (i + 1) % k.anh.length })}><Mui /></button></>}
                {k.so_anh > 0 && <span className="ksv-ct">{i + 1}/{k.so_anh}</span>}</div>
              <div className="ksv-info"><h3><button type="button" className="ksv-ten" onClick={() => moKs(k.id)}>{k.ten}</button></h3>
                {k.sao > 0 && <span className="ksv-stars" aria-label={`${k.sao} sao`}>{"★".repeat(k.sao)}</span>}
                <span className="ksv-where"><Ghim />{[k.khu_vuc, k.tinh_thanh].filter(Boolean).join(", ")}{k.km_trung_tam != null ? ` - ${String(k.km_trung_tam).replace(".", ",")} km tới trung tâm` : ""}</span>
                {k.gan && <span className="ksv-near">{k.gan}</span>}
                {k.noi_bat && <span className="ksv-hl">{k.noi_bat}</span>}
                {k.tien_ich.length > 0 && <div className="ksv-feat sm">{k.tien_ich.slice(0, 4).map((t: string) => <span key={t}>{t}</span>)}</div>}</div>
              <div className="ksv-side">
                {k.danh_gia?.diem_tb ? <><span className="ksv-score"><b>{String(k.danh_gia.diem_tb).replace(".", ",")}</b><b>{nhan(k.danh_gia.diem_tb)}</b></span><small className="ksv-muted">{k.danh_gia.so_bai} đánh giá</small></>
                  : <small className="ksv-muted">{k.danh_gia?.so_bai ? "Mới — chưa đủ đánh giá" : "Chưa có đánh giá"}</small>}
                {g ? <>{g.niem_yet_dem && <span style={{ marginTop: "auto" }}><span className="ksv-old">{vnd(g.niem_yet_dem)}</span> <span className="ksv-pct">-{Math.round((1 - g.gia_dem / g.niem_yet_dem) * 100)}%</span></span>}
                  <span className="ksv-big" style={g.niem_yet_dem ? undefined : { marginTop: "auto" }}><small>₫</small> {vnd(g.gia_dem)}</span><small className="ksv-muted">Mỗi đêm, chưa gồm thuế và phí</small>
                  {k.co_mien_phi_huy && <span className="ksv-free">+ MIỄN PHÍ HỦY</span>}
                  {duKien(g.gia_dem * dem * q.phong) > 0 && <span className="ksv-diem">+ khoảng {vnd(duKien(g.gia_dem * dem * q.phong))} điểm sau kỳ ở</span>}
                  <button type="button" className="ksv-btn wide" onClick={() => moKs(k.id)}>Chọn phòng</button></>
                  : k.het_phong ? <><b style={{ marginTop: "auto", color: "var(--ksv-price)" }}>Hết phòng ngày này</b><small className="ksv-muted">Đổi ngày để xem phòng trống</small>
                    <button type="button" className="ksv-btn line wide" onClick={() => moKs(k.id)}>Xem khách sạn</button></>
                  : <><b style={{ marginTop: "auto" }}>Giá đang cập nhật</b><small className="ksv-muted">Vietourist báo giá trong giờ làm việc</small>
                    <button type="button" className="ksv-btn line wide" onClick={() => moKs(k.id)}>Xem và gửi yêu cầu</button></>}</div>
            </div></article>; })}
      </main></div></div>;
}

/* ── KS-14 · trả tiền, trang đơn, phòng đã đặt ─────────────────────────────────────────────────── */
const ngayGio = (s?: string | null) => { if (!s) return ""; const d = new Date(s); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")} ${d.getDate()}/${d.getMonth() + 1}`; };
const MAU_TT: Record<string, string> = { cho_tra: "ksv-tt-cho", het_han: "ksv-tt-xam", da_tra: "ksv-tt-xanh", da_xac_nhan: "ksv-tt-ok", da_huy: "ksv-tt-xam" };

function TomTatDon({ d }: { d: any }) {
  const k = d.khach_san || {};
  return <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
    <div className="ksv-panel" style={{ gap: 6 }}><b style={{ fontSize: 16 }}>{k.ten}</b>
      {k.sao > 0 && <span className="ksv-stars" style={{ fontSize: 13 }}>{"★".repeat(k.sao)}</span>}
      <span className="ksv-muted">{ngay(d.vao)} → {ngay(d.ra)} · {d.dem} đêm · {d.nguoi_lon} người lớn{d.tre_em ? ` · ${d.tre_em} trẻ em` : ""}</span>
      {d.dong.map((x: any, i: number) => <span key={i}><b>{x.so} × {x.loai_phong}</b> · {x.goi}<br />{x.huy_han ? <span className="ksv-okc">✓ Miễn phí hủy trước {x.huy_han.split("-").reverse().join("/")}</span> : <span className="ksv-muted">Không hoàn tiền</span>}</span>)}
      <span className="ksv-sum"><span>Giá phòng</span><span>₫ {vnd(d.tien_phong)}</span></span>
      <span className="ksv-sum"><span>Thuế và phí</span><span>₫ {vnd(d.thue_phi)}</span></span>
      {d.giam_voucher > 0 && <span className="ksv-sum ksv-okc"><span>Voucher {d.voucher?.ma}{d.voucher?.trang_thai === "da_hoan" ? " · đã trả điểm" : ""}</span><span>− ₫ {vnd(d.giam_voucher)}</span></span>}
      <span className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 10, alignItems: "baseline" }}><b style={{ fontSize: 16 }}>{d.giam_voucher > 0 ? "Bạn trả" : "Tổng"}</b><b className="ksv-big" style={{ fontSize: 22 }}>₫ {vnd(d.tong)}</b></span>
      {d.da_tra > 0 && <span className="ksv-sum"><span>Đã trả</span><b>₫ {vnd(d.da_tra)}</b></span>}</div></aside>;
}

function TraTien({ d, onDoi, onLai }: { d: any; onDoi: (d: any) => void; onLai: () => void }) {
  const [qr, setQr] = useState<any>(null);
  const [anh, setAnh] = useState("");
  const [loi, setLoi] = useState("");
  const [con, setCon] = useState<number>(d.giay_con || 0);
  const [busy, setBusy] = useState(false);
  const [chep, setChep] = useState("");
  useEffect(() => {
    setLoi("");
    goiCong(`/ks-vtd/don/${encodeURIComponent(d.ma)}/qr`).then((r) => { setQr(r); return QRCode.toDataURL(r.payload, { margin: 1, width: 240, errorCorrectionLevel: "M" }); })
      .then(setAnh).catch((x) => setLoi(x.message || "Chưa tạo được mã QR"));
  }, [d.ma]);
  useEffect(() => { const h = setInterval(() => setCon((x) => Math.max(0, x - 1)), 1000); return () => clearInterval(h); }, []);
  useEffect(() => {   // máy hỏi lại trạng thái mỗi 5 giây: tiền về là chuyển trang đơn
    const h = setInterval(() => { goiCong(`/ks-vtd/don/${encodeURIComponent(d.ma)}`).then((x) => { if (x.trang_thai !== "cho_tra") onDoi(x); }).catch(() => {}); }, 5000);
    return () => clearInterval(h);
  }, [d.ma]);  // eslint-disable-line react-hooks/exhaustive-deps
  const the = async () => {
    setBusy(true); setLoi("");
    try { diCongThe(await goiCong(`/ks-vtd/don/${encodeURIComponent(d.ma)}/the`, {})); }
    catch (x: any) { setLoi(x.message); setBusy(false); }
  };
  const huy = async () => {
    setBusy(true); setLoi("");
    try { const r = await goiCong(`/ks-vtd/don/${encodeURIComponent(d.ma)}/huy`, { ly_do: "Khách hủy khi chưa thanh toán" }); onDoi(r.don); }
    catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const chepChu = async (v: string, nhan: string) => { try { await navigator.clipboard.writeText(v); setChep(`Đã chép ${nhan}`); } catch { setChep("Trình duyệt chặn chép — hãy bôi đen để chép"); } };
  const mm = `${String(Math.floor(con / 60)).padStart(2, "0")}:${String(con % 60).padStart(2, "0")}`;
  return <>
    <div className="ksv-steps"><span className="xong"><b>✓</b>Thông tin của bạn</span><hr /><span className="on"><b>2</b>Thanh toán</span><hr /><span><b>3</b>Khách sạn xác nhận</span>
      <span style={{ marginLeft: "auto", fontWeight: 500 }}>{con > 0 ? <>Phòng được giữ cho bạn trong <b style={{ color: "var(--ksv-price)", fontSize: 16 }}>{mm}</b></> : <b style={{ color: "var(--ksv-price)" }}>Hết giờ giữ phòng</b>}</span></div>
    <div className="ksv-co">
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <span style={{ fontSize: 15 }}>Mã đặt phòng <b style={{ fontSize: 17 }}>{d.ma}</b> · đơn nằm ở «Phòng khách sạn đã đặt của bạn».</span>
        {con <= 0 ? <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>Hết 15 phút giữ phòng</h2>
          <span>Nếu bạn ĐÃ chuyển khoản, đừng chuyển lại — khi tiền về, máy giữ đơn nếu phòng còn, hết phòng thì Vietourist hoàn đủ.</span>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}><button type="button" className="ksv-btn" onClick={onLai}>Chọn lại phòng</button></div></section>
          : <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 21 }}>Quét mã để thanh toán</h2>
            {loi && <div className="ksv-loi">{loi}</div>}
            {qr && <div className="ksv-qr">{anh ? <img src={anh} alt={`Mã QR chuyển ₫ ${vnd(qr.so_tien)} cho đơn ${qr.ma}`} width={200} height={200} /> : <span style={{ width: 200, height: 200 }} />}
              <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 0, flex: "1 1 260px" }}>
                <span className="ksv-muted">Số tiền</span><b className="ksv-big" style={{ fontSize: 28 }}>₫ {vnd(qr.so_tien)}</b>
                <span>Nội dung chuyển khoản <b className="ksv-ma">{qr.noi_dung}</b> <button type="button" className="ksv-link" onClick={() => chepChu(qr.noi_dung, "nội dung")}>Chép</button></span>
                <span>{qr.ngan_hang} · <b>{qr.so_tk}</b> <button type="button" className="ksv-link" onClick={() => chepChu(qr.so_tk, "số tài khoản")}>Chép</button> · {qr.chu_tk}</span>
                {chep && <small>{chep}</small>}
                <small className="ksv-muted">Giữ nguyên nội dung để máy tự khớp. Trang tự chuyển khi tiền về (1–3 phút).</small></div></div>}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {d.the_bat && <button type="button" className="ksv-btn line" disabled={busy} onClick={the}>Trả bằng thẻ thay</button>}
              <button type="button" className="ksv-btn line" disabled={busy} onClick={huy}>Hủy đơn</button></div></section>}
        <section className="ksv-panel" style={{ padding: "16px 20px", gap: 6 }}><b>Điều gì xảy ra tiếp theo</b>
          <span>1. Tiền vào → đơn «Đã thanh toán», bạn nhận tin ngay.</span>
          <span>2. Điều hành Vietourist chốt phòng với khách sạn trong 2 giờ làm việc → phiếu xác nhận có mã của khách sạn.</span>
          <span>3. Khách sạn không giữ được phòng → hoàn đủ 100%.</span></section>
      </div>
      <TomTatDon d={d} /></div></>;
}

function DonKs({ d, bao, loi: loi0, onDoi, onTra, onLai }: { d: any; bao?: string; loi?: string; onDoi: (d: any) => void; onTra: () => void; onLai: () => void }) {
  const [loi, setLoi] = useState(loi0 || "");
  const [hoi, setHoi] = useState(false);
  const [viet, setViet] = useState(false);
  const dg = d.danh_gia || {};
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(bao || "");
  const huy = async () => {
    setBusy(true); setLoi("");
    try { const r = await goiCong(`/ks-vtd/don/${encodeURIComponent(d.ma)}/huy`, { ly_do: "Khách hủy" }); setHoi(false); setMsg(r.message); onDoi(r.don); }
    catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const buoc = [["Đã đặt", d.tao_luc], ["Đã thanh toán", d.tra_luc], ["Khách sạn xác nhận", d.xac_nhan_luc]] as const;
  const toi = d.trang_thai === "da_xac_nhan" ? 3 : d.trang_thai === "da_tra" ? 2 : 1;
  return <div className="ksv-co">
    <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
      {msg && <div className="ksv-ok" style={{ padding: "10px 14px" }}>{msg}</div>}
      {loi && <div className="ksv-loi">{loi}</div>}
      <section className="ksv-panel" style={{ padding: 22 }}>
        <span className={`ksv-tt ${MAU_TT[d.trang_thai] || ""}`}>{d.trang_thai === "da_tra" ? `✓ Đã thanh toán ₫ ${vnd(d.da_tra)}` : d.trang_thai_ten}</span>
        <h2 style={{ margin: 0, fontSize: 24 }}>{d.trang_thai === "da_xac_nhan" ? "Đặt phòng thành công" : d.trang_thai === "da_tra" ? "Đang chốt phòng với khách sạn"
          : d.trang_thai === "da_huy" ? "Đơn đã hủy" : d.trang_thai === "het_han" ? "Hết giờ giữ phòng" : "Chờ thanh toán"}</h2>
        <span style={{ fontSize: 15 }}>Mã đặt phòng <b style={{ fontSize: 18 }}>{d.ma}</b></span>
        {d.trang_thai === "da_tra" && <span className="ksv-muted">Điều hành Vietourist xác nhận chậm nhất {ngayGio(d.han_chot)}. Khách sạn hết phòng → hoàn đủ 100%.</span>}
        {d.trang_thai === "da_huy" && <span>{d.ly_do_huy}{d.so_hoan > 0 ? <> · Hoàn <b>₫ {vnd(d.so_hoan)}</b> — {d.hoan_tt_ten || "đang xử lý"}</> : d.da_tra > 0 ? " · Gói không hoàn tiền" : ""}</span>}
        {d.trang_thai === "het_han" && <span className="ksv-muted">{d.da_tra > 0 ? "Vietourist đã nhận một phần tiền và sẽ liên hệ hoàn lại." : "Phòng đã được nhả. Bạn có thể đặt lại."}</span>}
        {d.trang_thai !== "da_huy" && d.trang_thai !== "het_han" && <ol className="ksv-tl">{buoc.map(([t, luc], i) =>
          <li key={t} className={i < toi ? "xong" : i === toi ? "on" : ""}><b>{t}</b>{luc ? <small className="ksv-muted"> · {ngayGio(luc)}</small> : null}</li>)}
          <li><b>Nhận phòng</b><small className="ksv-muted"> · {ngay(d.vao)}</small></li></ol>}
      </section>
      {d.trang_thai === "da_xac_nhan" && <section className="ksv-panel ksv-phieu" style={{ padding: 22 }}>
        <small className="ksv-muted" style={{ fontWeight: 700, letterSpacing: ".5px" }}>PHIẾU XÁC NHẬN ĐẶT PHÒNG</small>
        <div className="ksv-grid2"><span>Mã Vietourist<br /><b style={{ fontSize: 16 }}>{d.ma}</b></span><span>Mã xác nhận khách sạn<br /><b style={{ fontSize: 16 }}>{d.ma_xac_nhan_ks}</b></span>
          <span>Khách chính<br /><b style={{ fontSize: 16 }}>{d.ho_ten}</b></span><span>Trạng thái<br /><b className="ksv-okc" style={{ fontSize: 16 }}>Đã xác nhận · Đã thanh toán đủ</b></span></div>
        <span className="ksv-muted">{d.khach_san?.ten}{d.khach_san?.dia_chi ? ` · ${d.khach_san.dia_chi}` : ""} · nhận phòng từ {d.khach_san?.gio_nhan}, trả trước {d.khach_san?.gio_tra}.
          Xuất trình phiếu hoặc mã khi nhận phòng; không phải trả thêm tại khách sạn, trừ dịch vụ bạn tự dùng.</span>
        <div><button type="button" className="ksv-btn" onClick={() => window.print()}>In / lưu PDF</button></div></section>}
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        {d.co_the_tra && <button type="button" className="ksv-btn" onClick={onTra}>Thanh toán ₫ {vnd(d.con_phai_tra)}</button>}
        {d.co_the_huy && <button type="button" className="ksv-btn line" style={{ color: "var(--ksv-price)", borderColor: "var(--ksv-price)" }} onClick={() => setHoi(true)}>Hủy phòng</button>}
        {(dg.duoc_viet || dg.duoc_sua) && !viet && <button type="button" className="ksv-btn" onClick={() => setViet(true)}>{dg.bai ? "Sửa đánh giá" : "Viết đánh giá"}</button>}
        <button type="button" className="ksv-btn line" onClick={onLai}>Tìm chỗ ở khác</button></div>
      {dg.duoc_viet && !viet && <small className="ksv-muted">Bạn đã ở — đánh giá giúp khách sau (còn {dg.con_ngay} ngày, tới {dg.han_viet.split("-").reverse().join("/")}).</small>}
      {dg.bai && !viet && <section className="ksv-panel" style={{ gap: 6 }}><b>Đánh giá của bạn</b>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}><OD d={dg.bai.diem} /><b>{dg.bai.tieu_de || dg.bai.nhan}</b>{dg.bai.an && <span className="ksv-tt ksv-tt-xam">Đang ẩn · {dg.bai.an_ly_do}</span>}</div>
        {dg.bai.nhan_xet && <span style={{ whiteSpace: "pre-line" }}>{dg.bai.nhan_xet}</span>}
        {dg.bai.tra_loi && <div className="ksv-tl-ks"><b>Phản hồi của khách sạn</b><br />{dg.bai.tra_loi}</div>}</section>}
      {viet && <VietDanhGiaKs d={d} onThoi={() => setViet(false)} onXong={(r) => { setViet(false); setMsg(r.message); onDoi(r.don); }} />}
      {hoi && <HoiHuy d={d} busy={busy} onThoi={() => setHoi(false)} onHuy={huy} />}
    </div>
    <TomTatDon d={d} /></div>;
}

function HoiHuy({ d, busy, onThoi, onHuy }: { d: any; busy: boolean; onThoi: () => void; onHuy: () => void }) {
  return <section className="ksv-panel ksv-hoi" role="dialog" aria-label={`Hủy ${d.ma}`}>
    <h3 style={{ margin: 0, fontSize: 19 }}>Hủy {d.ma}?</h3>
    <div className="ksv-hoan"><span className="ksv-sum"><span>Đã trả</span><span>₫ {vnd(d.da_tra)}</span></span>
      <span className="ksv-sum"><span>Giữ lại theo gói</span><span>₫ {vnd(d.da_tra - d.hoan_neu_huy)}</span></span>
      <span className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 8 }}><b>Hoàn lại</b><b className="ksv-okc">₫ {vnd(d.hoan_neu_huy)}</b></span></div>
    <small className="ksv-muted">Hoàn theo chính sách từng gói: trước hạn miễn phí hủy hoàn đủ phần gói đó; sau hạn hoặc gói «Không hoàn tiền» không hoàn. Tiền về tài khoản / thẻ đã dùng trong 3–7 ngày làm việc.</small>
    <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", flexWrap: "wrap" }}>
      <button type="button" className="ksv-btn line" onClick={onThoi}>Giữ phòng</button>
      <button type="button" className="ksv-btn" style={{ background: "var(--ksv-price)" }} disabled={busy} onClick={onHuy}>{d.hoan_neu_huy > 0 ? `Hủy và hoàn ₫ ${vnd(d.hoan_neu_huy)}` : "Hủy phòng"}</button></div></section>;
}

/** «Phòng đã đặt của tôi» — dùng ở mục Khách sạn (gọn) và ở «Đơn của tôi». */
export function PhongCuaToi({ gon = false, lamMoi = 0, onMo }: { gon?: boolean; lamMoi?: number; onMo?: (d: any) => void }) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [mo, setMo] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const tai = () => goiCong("/ks-vtd/don").then((r) => setDs(r.don)).catch((x) => setLoi(x.status === 403 ? "" : x.message));
  useEffect(() => { tai(); }, [lamMoi]);  // eslint-disable-line react-hooks/exhaustive-deps
  const hien = (ds || []).filter((d) => !gon || ["cho_tra", "da_tra", "da_xac_nhan"].includes(d.trang_thai) || (d.trang_thai === "da_huy" && d.hoan_tt && d.hoan_tt !== "da_hoan"));
  if (!ds || (!hien.length && gon)) return loi && !gon ? <div className="ksv"><style>{CSS}</style><div className="ksv-loi">{loi}</div></div> : null;
  const xem = (d: any) => (onMo ? onMo(d) : setMo(d));
  return <div className="ksv">{gon ? null : <style>{CSS}</style>}
    {mo && !onMo ? <DonKs d={mo} onDoi={(d) => { setMo(d); tai(); }} onTra={() => setMo(null)} onLai={() => setMo(null)} />
      : <section className="ksv-panel" style={{ gap: 10 }}><b style={{ fontSize: 17 }}>Phòng khách sạn đã đặt của bạn</b>
        {!hien.length && <span className="ksv-muted">Chưa có đơn đặt phòng nào.</span>}
        {hien.map((d) => <div key={d.ma} className="ksv-donrow">
          <span style={{ flex: "1 1 240px", minWidth: 0 }}><b>{d.khach_san?.ten}</b><br /><small className="ksv-muted">{d.ma} · {ngay(d.vao)} → {ngay(d.ra)} · {d.so_phong} phòng</small></span>
          <span className={`ksv-tt ${MAU_TT[d.trang_thai] || ""}`}>{d.trang_thai === "da_huy" && d.so_hoan > 0 ? `Đã hủy · ${d.hoan_tt_ten || "đã hoàn"}` : d.trang_thai_ten}</span>
          <b style={{ minWidth: 110, textAlign: "right" }}>₫ {vnd(d.tong)}</b>
          <button type="button" className="ksv-btn line" onClick={() => xem(d)}>{d.co_the_tra ? "Thanh toán" : d.danh_gia?.duoc_viet ? "Viết đánh giá" : "Xem"}</button></div>)}</section>}</div>;
}

function TomTat({ ks, q, tinh, giam = 0, maVc, hang, diemDk = 0 }: { ks: any; q: Q; tinh: any; giam?: number; maVc?: string; hang?: any; diemDk?: number }) {
  return <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
    <div className="ksv-panel" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ display: "flex", gap: 12, padding: 14 }}>{ks.anh?.[0] ? <img src={ks.anh[0].nho} alt="" style={{ width: 92, height: 76, objectFit: "cover", borderRadius: 8 }} /> : null}
        <span><b style={{ fontSize: 16 }}>{ks.ten}</b><br />{ks.sao > 0 && <span className="ksv-stars" style={{ fontSize: 13 }}>{"★".repeat(ks.sao)}</span>}<br /><small className="ksv-muted">{[ks.khu_vuc, ks.tinh_thanh].filter(Boolean).join(", ")}</small></span></div>
      <div className="ksv-grid2" style={{ gap: 0, borderBlock: "1px solid var(--ksv-line)" }}>
        <span style={{ padding: "12px 14px", borderRight: "1px solid var(--ksv-line)" }}><small className="ksv-muted">Nhận phòng</small><br /><b>{ngay(q.vao)}</b><br /><small className="ksv-muted">từ {ks.gio_nhan}</small></span>
        <span style={{ padding: "12px 14px" }}><small className="ksv-muted">Trả phòng</small><br /><b>{ngay(q.ra)}</b><br /><small className="ksv-muted">trước {ks.gio_tra}</small></span></div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 4 }}>
        {tinh.dong.length ? tinh.dong.map((x: any, i: number) => <div key={i} style={{ display: "flex", flexDirection: "column" }}><b>{x.so} × {x.loai_phong}</b>
          <span className="ksv-muted">{x.goi} · {tinh.dem} đêm{x.phu_thu ? ` · gồm phụ thu trẻ em / giường phụ ₫ ${vnd(x.phu_thu)}` : ""}</span>{x.huy_han ? <span className="ksv-okc">✓ Miễn phí hủy trước {x.huy_han.split("-").reverse().join("/")}</span> : <span className="ksv-muted">Không hoàn tiền</span>}</div>)
          : <span>{tinh.loai_phong ? `Loại phòng: ${tinh.loai_phong} · ` : ""}{q.phong} phòng · {q.nl} người lớn · Vietourist báo giá</span>}</div></div>
    {tinh.tong > 0 && <div className="ksv-panel"><span className="ksv-sum"><span>Giá phòng ({tinh.so_phong} phòng × {tinh.dem} đêm){tinh.phu_thu ? " · gồm phụ thu" : ""}</span><span>₫ {vnd(tinh.tien_phong)}</span></span>
      <span className="ksv-sum"><span>Thuế và phí ({ks.thue_phi_pt || 0}%)</span><span>₫ {vnd(tinh.thue_phi)}</span></span>
      {giam > 0 && <span className="ksv-sum ksv-okc"><span>Voucher {maVc}</span><span>− ₫ {vnd(giam)}</span></span>}
      <span className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 10, alignItems: "baseline" }}><b style={{ fontSize: 16 }}>{giam > 0 ? "Bạn trả" : "Tổng cộng"}</b><b className="ksv-big" style={{ fontSize: 22 }}>₫ {vnd(tinh.tong - giam)}</b></span>
      {hang?.cach_tinh === "hoa_hong" && tinh.tong - giam > 0 && <span className="ksv-diem-box">Đơn này tích điểm sau khi trả phòng và Vietourist chốt đơn: điểm = 20% hoa hồng Vietourist nhận ÷ 100 đ × {String(hang.he_so).replace(".", ",")} (hạng {hang.hang}). Không tính vào chi tiêu xét hạng.</span>}
      {hang?.cach_tinh !== "hoa_hong" && hang && diemDk > 0 && <span className="ksv-diem-box"><b>+ {vnd(diemDk)} điểm</b> sau khi trả phòng và Vietourist chốt đơn ({vnd(tinh.tong - giam)} ÷ {vnd(hang.dong_moi_diem)} × {String(hang.he_so).replace(".", ",")} hạng {hang.hang}). Kỳ ở này cũng tính vào chi tiêu xét hạng.</span>}
      <small className="ksv-muted">{tinh.dong?.length ? "Đã gồm thuế phí. Giá do máy chủ tính lại lúc giữ phòng. Trả xong, Điều hành chốt với khách sạn trong 2 giờ làm việc — khách sạn hết phòng thì hoàn 100%."
        : "Giá Vietourist tính lúc bạn chọn. Điều hành xác nhận lại với khách sạn trước khi bạn trả tiền."}</small></div>}
  </aside>;
}

const CSS = `
.ksv{--ksv-fg:#23252c;--ksv-muted:#5f6472;--ksv-line:#e1e4eb;--ksv-soft:#eef1f7;--ksv-card:#fff;--ksv-band:#1f2a5a;--ksv-accent:#3f66e0;--ksv-ink:#2459cf;
  --ksv-asoft:#e8eefc;--ksv-price:#d3261b;--ksv-ok:#1c7f46;--ksv-oksoft:#e5f4ea;--ksv-star:#e39a2d;
  display:flex;flex-direction:column;gap:14px;color:var(--ksv-fg);min-width:0}
.ksv h2,.ksv h3{text-wrap:balance}
.ksv button{cursor:pointer;font:inherit}
.ksv :focus-visible{outline:2px solid var(--ksv-accent);outline-offset:2px}
.ksv-band{background:var(--ksv-band);border-radius:12px;padding:12px}
.ksv-hv{background:#fff4dc;color:#6d4300;border-radius:10px;padding:10px 14px;font-size:14px}
.ksv-diem{color:var(--ksv-ok);font-size:12px;font-weight:600}
.ksv-diem-box{background:var(--ksv-oksoft);color:#14562f;border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.5}
.ksv-vc,#vtd-access .ksv .ksv-vc{flex:1 1 200px;min-height:44px;border:1px solid var(--ksv-line);border-radius:8px;padding:0 12px;font:inherit;background:#fff;color:var(--ksv-fg);text-transform:uppercase}
.ksv-search{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1.4fr) minmax(0,1fr) auto;gap:8px}
.ksv-sbox{background:#fff;color:#23252c;border-radius:8px;display:flex;align-items:center;gap:10px;padding:6px 12px;min-height:54px;min-width:0}
.ksv-sbox small{display:block;font-size:11px;color:#5f6472}.ksv-sbox select,.ksv-sbox input,#vtd-access .ksv .ksv-sbox select,#vtd-access .ksv .ksv-sbox input{border:0;background:transparent;font-weight:600;font-size:15px;width:100%;outline:none;padding:0;color:#23252c;min-width:0}
.ksv-dates{padding:0}.ksv-dates label{flex:1;display:flex;flex-direction:column;justify-content:center;padding:6px 12px;min-width:0}
.ksv-dates label+label{border-left:1px solid #e1e4eb}
.ksv-khach{all:unset;flex:1;cursor:pointer;min-width:0}.ksv-khach b{font-size:15px}
.ksv-btn-tim{border:0;border-radius:99px;background:var(--ksv-accent);color:#fff;font-weight:700;font-size:16px;padding:0 32px;min-height:54px;letter-spacing:.03em}
.ksv-pop{position:absolute;top:calc(100% + 6px);right:0;width:280px;background:#fff;border:1px solid var(--ksv-line);border-radius:12px;box-shadow:0 8px 28px rgba(0,0,0,.18);padding:14px;display:flex;flex-direction:column;gap:10px;z-index:25}
.ksv-step{display:flex;align-items:center;justify-content:space-between}.ksv-step div{display:flex;align-items:center;gap:10px}
.ksv-step button{width:34px;height:34px;border-radius:50%;border:1px solid var(--ksv-line);background:#fff;font-size:18px;line-height:1}
.ksv-layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:16px}
.ksv-loc{display:flex;flex-direction:column;gap:12px}
.ksv-panel{background:var(--ksv-card);border:1px solid var(--ksv-line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:10px}
.ksv-pill{display:flex;align-items:center;gap:8px;background:var(--ksv-soft);border-radius:99px;padding:0 14px;min-height:44px}.ksv-pill input,#vtd-access .ksv .ksv-pill input{border:0;background:transparent;outline:none;width:100%}
.ksv-chk{display:flex;gap:10px;align-items:center;cursor:pointer}.ksv-chk input,#vtd-access .ksv .ksv-chk input{width:18px;height:18px;accent-color:var(--ksv-accent)}
.ksv-chk span{flex:1}.ksv-chk small{color:var(--ksv-muted)}
.ksv-mm{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.ksv-mm label{border:1px solid var(--ksv-line);border-radius:6px;padding:4px 8px;font-size:11px;color:var(--ksv-muted)}.ksv-mm input,#vtd-access .ksv .ksv-mm input{border:0;background:transparent;width:100%;font-weight:600;font-size:14px;color:var(--ksv-fg);outline:none;padding:0}.ksv input[type=range],#vtd-access .ksv input[type=range]{width:100%;accent-color:var(--ksv-accent)}
.ksv-rhead{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.ksv .ksv-sel,#vtd-access .ksv .ksv-sel{border:1px solid var(--ksv-line);background:#fff;background-color:#fff;color:#23252c;-webkit-text-fill-color:#23252c;border-radius:8px;min-height:44px;padding:0 10px;font-weight:600;box-shadow:none}.ksv .ksv-sel:disabled,#vtd-access .ksv .ksv-sel:disabled{background:#f2f3f5;color:#8a8f99;-webkit-text-fill-color:#8a8f99}.ksv .ksv-sel option,#vtd-access .ksv .ksv-sel option{color:#23252c;background:#fff}
.ksv-card{background:var(--ksv-card);border-radius:12px;box-shadow:0 1px 4px rgba(16,24,40,.12);overflow:hidden;display:flex;flex-direction:column}
.ksv-bar{background:var(--ksv-accent);color:#fff;font-size:12px;padding:6px 14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.ksv-bar span{flex:1;min-width:150px}.ksv-bar em{font-style:normal;background:#fff;color:var(--ksv-ink);font-weight:600;padding:2px 8px;border-radius:3px}
.ksv-crow{display:grid;grid-template-columns:270px minmax(0,1fr) 205px;min-height:220px}
.ksv-ph{position:relative;background:var(--ksv-soft)}
.ksv-phbtn{all:unset;cursor:pointer;display:block;width:100%;height:100%}
.ksv-ph img{width:100%;height:100%;min-height:200px;object-fit:cover;display:block}
.ksv-ct{position:absolute;left:10px;bottom:10px;background:rgba(20,20,30,.66);color:#fff;font-size:12px;font-weight:600;padding:2px 8px;border-radius:4px}
.ksv-ico{position:absolute;border:0;border-radius:50%;background:#fff;display:grid;place-items:center;box-shadow:0 1px 4px rgba(0,0,0,.2)}
.ksv-heart{right:10px;top:10px;width:38px;height:38px}.ksv-heart.on svg{fill:#e0335a;stroke:#e0335a}
.ksv-nxt{right:10px;top:calc(50% - 16px);width:32px;height:32px}.ksv-prv{left:10px;top:calc(50% - 16px);width:32px;height:32px}
.ksv-trong{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;width:100%;height:100%;min-height:200px;background:#eef2f5}
.ksv-trong b{width:52px;height:52px;border-radius:50%;color:#fff;font-size:24px;display:grid;place-items:center}
.ksv-trong small{font-size:12px;color:#3d4b59}
.ksv-info{padding:14px 18px;display:flex;flex-direction:column;gap:5px;min-width:0}
.ksv-info h3{margin:0;font-size:20px}.ksv-ten{all:unset;cursor:pointer;font-weight:700}.ksv-ten:hover{color:var(--ksv-ink)}
.ksv-stars{color:var(--ksv-star);letter-spacing:2px}
.ksv-where{color:var(--ksv-ink);font-weight:600;display:flex;gap:5px;align-items:center}
.ksv-near{color:var(--ksv-muted);font-size:13px;padding-left:19px}
.ksv-hl{color:var(--ksv-muted);font-size:13px;margin-top:auto}
.ksv-feat{display:flex;gap:8px;flex-wrap:wrap}.ksv-feat span{border:1px solid var(--ksv-line);border-radius:10px;padding:8px 12px;font-size:13px}
.ksv-feat.sm span{padding:3px 8px;border-radius:6px;font-size:12px;background:var(--ksv-soft);border:0}
.ksv-side{border-left:1px solid var(--ksv-line);padding:14px 16px;display:flex;flex-direction:column;align-items:flex-end;text-align:right;gap:3px}
.ksv-score{display:flex;gap:8px;align-items:center}.ksv-score b:first-child{background:var(--ksv-ink);color:#fff;padding:3px 7px;border-radius:6px 6px 6px 0}
.ksv-score b+b{color:var(--ksv-ink)}
.ksv-old{color:var(--ksv-muted);text-decoration:line-through;font-size:16px}.ksv-pct{color:var(--ksv-price);font-weight:700}
.ksv-big{color:var(--ksv-price);font-size:26px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}.ksv-big small{font-size:14px}
.ksv-free{color:var(--ksv-ok);font-weight:600;font-size:13px}
.ksv-btn{border:0;border-radius:8px;background:var(--ksv-accent);color:#fff;font-weight:700;min-height:44px;padding:0 18px}
.ksv-btn:disabled{opacity:.6;cursor:default}
.ksv-btn.line{background:transparent;border:1.5px solid var(--ksv-ink);color:var(--ksv-ink)}
.ksv-btn.wide{width:100%;margin-top:6px}
.ksv-link{all:unset;cursor:pointer;color:var(--ksv-ink);font-weight:600}
.ksv-muted{color:var(--ksv-muted)}.ksv-okc{color:var(--ksv-ok)}
.ksv-loi{background:#fdecea;color:#8a1f1f;border-radius:8px;padding:10px 14px}
.ksv-ok{background:var(--ksv-oksoft);color:var(--ksv-ok);border-radius:10px;padding:10px 14px}
.ksv-gal{display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:170px 170px;gap:6px;border-radius:12px;overflow:hidden}
.ksv-gal span{position:relative;background:var(--ksv-soft)}.ksv-gal span:first-child{grid-row:span 2}
.ksv-gal img{width:100%;height:100%;object-fit:cover;display:block}
.ksv-more{display:grid;place-items:center;color:#fff;font-weight:700;background:linear-gradient(160deg,#3c4a63,#8d99ad)!important}
.ksv-tabs{position:sticky;top:0;z-index:15;background:#fff;border:1px solid var(--ksv-line);border-radius:10px;display:flex;gap:2px;align-items:center;overflow-x:auto;padding:0 8px}
.ksv-tabs a{padding:12px;font-weight:600;color:var(--ksv-muted);white-space:nowrap;text-decoration:none}.ksv-tabs a:hover{color:var(--ksv-ink)}
.ksv-tp{margin-left:auto;display:flex;align-items:center;gap:10px;white-space:nowrap;padding:6px 0}
.ksv-two{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:14px}
.ksv-room{background:var(--ksv-card);border-radius:12px;box-shadow:0 1px 4px rgba(16,24,40,.1);display:grid;grid-template-columns:260px minmax(0,1fr);overflow:hidden}
.ksv-rl{padding:16px;border-right:1px solid var(--ksv-line);display:flex;flex-direction:column;gap:8px}
.ksv-rp{width:100%;height:140px;object-fit:cover;border-radius:8px}
.ksv-rates{display:flex;flex-direction:column;min-width:0}
.ksv-rhd,.ksv-rate{display:grid;grid-template-columns:minmax(0,1fr) 100px 170px 120px}
.ksv-rhd{background:var(--ksv-soft);font-size:11px;font-weight:700;color:var(--ksv-muted);text-transform:uppercase;letter-spacing:.04em}
.ksv-rhd span,.ksv-rate>div{padding:12px 14px}.ksv-rate+.ksv-rate{border-top:1px solid var(--ksv-line)}
.ksv-rate ul{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:4px}
.ksv-total{position:sticky;bottom:0;z-index:15;background:#fff;border:1px solid var(--ksv-line);border-radius:12px;box-shadow:0 -4px 16px rgba(0,0,0,.08);padding:12px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.ksv-grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.ksv-steps{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-weight:600;color:var(--ksv-muted)}
.ksv-steps b{width:26px;height:26px;border-radius:50%;border:2px solid var(--ksv-line);display:inline-grid;place-items:center;font-size:12px;margin-right:6px}
.ksv-steps .on{color:var(--ksv-ink)}.ksv-steps .on b{background:var(--ksv-ink);border-color:var(--ksv-ink);color:#fff}
.ksv-steps .xong{color:var(--ksv-ok)}.ksv-steps .xong b{background:var(--ksv-ok);border-color:var(--ksv-ok);color:#fff}
.ksv-steps hr{width:40px;border:0;border-top:2px solid var(--ksv-line);margin:0}
.ksv-co{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:16px;align-items:start}
.ksv-f2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.ksv-fld{display:flex;flex-direction:column;gap:5px;font-size:13px;font-weight:600}.ksv-fld input,.ksv-fld textarea,#vtd-access .ksv .ksv-fld input,#vtd-access .ksv .ksv-fld textarea{font-weight:400;font-size:15px;min-height:46px;border:1px solid var(--ksv-line);border-radius:8px;padding:0 12px;background:#fff}.ksv-fld textarea,#vtd-access .ksv .ksv-fld textarea{padding:10px 12px;min-height:70px}
.ksv-sum{display:flex;justify-content:space-between;gap:10px;font-variant-numeric:tabular-nums}
.ksv-fbtn{display:none}
@media (max-width:900px){
  .ksv-search{grid-template-columns:1fr 1fr}.ksv-btn-tim{grid-column:span 2}
  .ksv-layout,.ksv-two,.ksv-co,.ksv-grid2{grid-template-columns:1fr}
  .ksv-loc{display:none}.ksv-loc.open{display:flex;position:fixed;inset:0;z-index:40;background:#f3f6fa;overflow:auto;padding:16px max(16px,env(safe-area-inset-right,0px)) calc(16px + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px))}
  .ksv-fbtn{display:inline-flex;align-items:center}
  .ksv-crow{grid-template-columns:1fr}.ksv-side{border-left:0;border-top:1px solid var(--ksv-line);align-items:stretch;text-align:left}
  .ksv-room{grid-template-columns:1fr}.ksv-rl{border-right:0;border-bottom:1px solid var(--ksv-line)}
  .ksv-rhd{display:none}.ksv-rate{grid-template-columns:1fr 1fr}.ksv-rate>div:first-child{grid-column:span 2}
  .ksv-gal{grid-template-columns:1fr 1fr;grid-template-rows:200px 110px}.ksv-gal span:first-child{grid-column:span 2;grid-row:auto}.ksv-gal span:nth-child(n+4){display:none}
  .ksv-f2{grid-template-columns:1fr}
}
.ksv-ota-dau{margin:18px 0 6px;font-size:18px}
.ksv-pay{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--ksv-line);border-radius:10px;padding:14px;min-height:44px;cursor:pointer}
.ksv-pay.on{border:2px solid var(--ksv-accent);background:var(--ksv-asoft);padding:13px}
.ksv-pay input,#vtd-access .ksv .ksv-pay input{width:18px;height:18px;margin:3px 0 0;flex:0 0 auto;accent-color:var(--ksv-accent)}
.ksv-qr{display:flex;gap:22px;flex-wrap:wrap;align-items:center}
.ksv-qr img{border:1px solid var(--ksv-line);border-radius:10px;background:#fff}
.ksv-ma{background:#fff6d6;padding:2px 8px;border-radius:6px;letter-spacing:.5px;font-size:17px}
.ksv-tt{align-self:flex-start;font-weight:700;font-size:12px;padding:4px 10px;border-radius:99px;background:var(--ksv-soft);color:#3d4556;white-space:nowrap}
.ksv-tt-ok{background:var(--ksv-oksoft);color:#146c3f}.ksv-tt-xanh{background:var(--ksv-asoft);color:#1f4fae}.ksv-tt-cho{background:#fff3d6;color:#7a5200}.ksv-tt-xam{background:#f1f2f5;color:#4a5160}
.ksv-tl{list-style:none;margin:6px 0 0;padding:0;display:flex;flex-direction:column;gap:0}
.ksv-tl li{position:relative;padding:0 0 14px 32px;font-size:14px}
.ksv-tl li::before{content:"";position:absolute;left:0;top:0;width:20px;height:20px;border-radius:50%;border:1px solid #a9b1bf;box-sizing:border-box;background:#fff}
.ksv-tl li::after{content:"";position:absolute;left:9px;top:22px;bottom:2px;width:2px;background:#d5dae3}
.ksv-tl li:last-child::after{display:none}
.ksv-tl li.xong::before{background:var(--ksv-ok);border-color:var(--ksv-ok)}.ksv-tl li.xong::after{background:var(--ksv-ok)}
.ksv-tl li.on::before{border:2px solid var(--ksv-accent)}.ksv-tl li.on b{color:var(--ksv-ink)}
.ksv-hoi{border:2px solid var(--ksv-fg);box-shadow:0 12px 32px rgba(20,30,50,.18);padding:20px;max-width:520px}
.ksv-hoan{display:flex;flex-direction:column;gap:6px;background:#f6f8fb;border-radius:10px;padding:12px}
.ksv-donrow{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;border-top:1px solid var(--ksv-line);padding-top:10px}
.ksv-phieu{border:2px dashed #b9c6dd}
.ksv-od{display:inline-block;background:var(--ksv-ink);color:#fff;font-weight:700;border-radius:8px 8px 8px 2px;padding:4px 8px;min-width:24px;text-align:center}
.ksv-od.xam{background:#5f6472}.ksv-od.lon{font-size:26px;padding:10px 14px;border-radius:12px 12px 12px 3px}
.ksv-bar10{flex:1;height:8px;background:#e7ebf2;border-radius:99px;overflow:hidden}.ksv-bar10 span{display:block;height:100%;background:var(--ksv-ink)}
.ksv-moi{background:#fff8e6;border:1px solid #f0d38a;border-radius:10px;padding:10px 14px;font-size:14px}
.ksv-chip{min-height:40px;padding:0 14px;border-radius:99px;border:1px solid #c9cfda;background:#fff;color:#3d4556}
.ksv-chip.on{border-color:var(--ksv-ink);background:var(--ksv-asoft);color:var(--ksv-ink);font-weight:600}
.ksv-bai{border-top:1px solid var(--ksv-line);padding-top:14px;display:flex;flex-wrap:wrap;gap:14px}
.ksv-bai-ai{flex:0 0 170px;display:flex;flex-direction:column;gap:3px;font-size:13px;color:var(--ksv-muted)}.ksv-bai-ai b{color:var(--ksv-fg);font-size:15px}
.ksv-tl-ks{background:#f5f7fb;border-radius:10px;padding:10px 12px;font-size:14px}
.ksv-so{width:44px;height:44px;border-radius:8px;border:1px solid #c9cfda;background:#fff;color:#23252c}
.ksv-so.on{border:2px solid var(--ksv-ink);background:var(--ksv-ink);color:#fff;font-weight:700}
@media print{body *{visibility:hidden}.ksv-phieu,.ksv-phieu *{visibility:visible}.ksv-phieu{position:absolute;left:0;top:0;width:100%}.ksv-phieu button{display:none}}
@media (max-width:560px){.ksv-search{grid-template-columns:1fr}.ksv-btn-tim{grid-column:auto}}
`;
