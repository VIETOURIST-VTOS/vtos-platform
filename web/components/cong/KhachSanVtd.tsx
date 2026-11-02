"use client";
/* KS-13 · Khách sạn hợp tác VTD trên cổng (Chủ tịch duyệt bản demo 30/10/2026) — các bước như Agoda:
   tìm → danh sách (lọc, sắp xếp) → trang khách sạn (album, chọn phòng theo gói giá) → thông tin khách → gửi.
   Ở bước 12a khách GỬI YÊU CẦU GIỮ PHÒNG: Điều hành giữ phòng với khách sạn rồi báo lại (hàng chờ KS-11). Giá
   trên màn do máy chủ tính từ giá Điều hành nhập và TP Điều hành duyệt; trình duyệt không gửi số tiền nào lên.
   KS-14 (Chủ tịch duyệt bản xem thử 30/10/2026): khách sạn có giá đã duyệt thì khách ĐẶT VÀ TRẢ NGAY 100% —
   máy giữ phòng 15 phút, trả QR (máy tự khớp) hoặc thẻ qua cổng SePay (SP-1); Điều hành chốt với khách sạn trong 2 giờ làm
   việc; hủy theo gói. Phòng đã đặt nằm ở «Phòng đã đặt của tôi». Điểm thưởng: khi VTD Rewards chạy.
   KS-16p (Chủ tịch duyệt bản xem thử 01/11/2026): giao diện kiểu Agoda mang thương hiệu Vietourist — trang tìm, danh sách,
   trang khách sạn (album toàn màn theo nhóm ảnh + tab video), chọn phòng, 3 bước đặt (thông tin khách → bước cuối →
   đã giữ / đã xác nhận). Thêm «Đặt giữ, trả sau» cho gói miễn phí hủy: hạn trả do MÁY CHỦ tính (han_tra_sau).
   Chỉ số thật: «Chỉ còn N phòng» (con_it) và «Đã đặt N lần trong 24 giờ qua» (dat_24h) chỉ hiện khi máy chủ trả về. */
import { DaiVideo, VideoO } from "./VideoCong";   // KS-16f
import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { giaGon } from "./BanDoKs";
const BanDoKs = dynamic(() => import("./BanDoKs"), { ssr: false, loading: () => <div className="ksv-bando" style={{ height: 320 }} /> });   // KS-16s
import QRCode from "qrcode";
import { diCongThe, duongRieng, goiCong, moNgoai, xemCong } from "@/lib/cong";
import { DanhGiaKsCong, MUC_KS, OD, TomTatDg, VietDanhGiaKs, nhanDiem } from "./DanhGiaKs";

type Q = { tinh: string; vao: string; ra: string; nl: number; te: number; phong: number; tuoi?: number[] };
// KS-16j: như Agoda — có trẻ em thì chọn tuổi từng bé (-1 = chưa chọn); máy tính phụ thu theo chính sách khách sạn.
const tuoiStr = (q: Q) => { const t = (q.tuoi || []).slice(0, q.te); return q.te > 0 && t.length === q.te && t.every((x) => x >= 0) ? t.join(",") : ""; };
const tuoiDs = (q: Q) => (tuoiStr(q) ? (q.tuoi || []).slice(0, q.te) : []);
// KS-16s: bộ lọc kiểu Agoda — cách thanh toán (tt), điểm khách tối thiểu (dk), bữa ăn & ưu đãi (an), khoảng cách (kc), giường (gi)
type Loc = { min: number; max: number; coGia: boolean; huy: boolean; sang: boolean; diem9: boolean; conPhong: boolean; sao: number[]; loai: string[]; khu: string[]; ti: string[]; ten: string;
  tt: string[]; dk: number; an: string[]; kc: string[]; gi: string[] };
const LOC0: Loc = { min: 0, max: 0, coGia: false, huy: false, sang: false, diem9: false, conPhong: false, sao: [], loai: [], khu: [], ti: [], ten: "", tt: [], dk: 0, an: [], kc: [], gi: [] };
const LOC_TT: [string, string, (k: any) => boolean][] = [["huy", "Miễn phí hủy", (k) => !!k.co_mien_phi_huy], ["sau", "Đặt giữ, trả sau", (k) => !!k.co_tra_sau],
  ["ngay", "Trả ngay", (k) => !!k.co_tra_ngay], ["qr", "Không cần thẻ (QR chuyển khoản)", (k) => !!k.co_tra_ngay]];
const LOC_AN: [string, string, (k: any) => boolean][] = [["sang", "Bao gồm bữa sáng", (k) => !!k.co_bua_sang], ["chi", "Chỉ phòng", (k) => !!k.co_chi_phong],
  ["uudai", "Ưu đãi giảm giá", (k) => !!k.co_uu_dai]];
const LOC_KC: [string, string, (k: any) => boolean][] = [["2", "Dưới 2 km", (k) => k.km_trung_tam != null && k.km_trung_tam < 2],
  ["5", "2–5 km", (k) => k.km_trung_tam != null && k.km_trung_tam >= 2 && k.km_trung_tam < 5], ["10", "5–10 km", (k) => k.km_trung_tam != null && k.km_trung_tam >= 5 && k.km_trung_tam <= 10]];
const LOC_GI: [string, string, (k: any) => boolean][] = [["doi", "1 giường đôi lớn", (k) => (k.giuong_tom || []).includes("doi")],
  ["don2", "2 giường đơn", (k) => (k.giuong_tom || []).includes("don2")], ["gd", "Phòng gia đình (≥4 khách)", (k) => !!k.gia_dinh]];
const hopNhom = (ds: [string, string, (k: any) => boolean][], chon: string[], k: any) => !chon.length || ds.some(([m, , f]) => chon.includes(m) && f(k));
// KS-16s: giờ đến dự kiến (như Agoda) — gửi khách sạn cùng đơn
const GIO_DEN = ["Chưa rõ", ...Array.from({ length: 10 }, (_, i) => `${String(14 + i).padStart(2, "0")}:00–${String((15 + i) % 24).padStart(2, "0")}:00`), "Sau nửa đêm"];
const ggDuong = (k: any) => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(k.vi_do != null && k.kinh_do != null ? `${k.vi_do},${k.kinh_do}` : [k.ten, k.dia_chi, k.tinh_thanh].filter(Boolean).join(", "))}`;
const vnd = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const themNgay = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };
const THU = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const THU_DAI = ["Chủ nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
const ngay = (s: string) => { const d = new Date(s + "T00:00:00"); return `${THU[d.getDay()]}, ${d.getDate()} thg ${d.getMonth() + 1}`; };
const ngayDai = (s: string) => { const d = new Date(s + "T00:00:00"); return `${d.getDate()} Th${d.getMonth() + 1} ${d.getFullYear()}`; };
const thuDai = (s: string) => THU_DAI[new Date(s + "T00:00:00").getDay()];
export const dmy = (s?: string | null) => (s ? String(s).slice(0, 10).split("-").reverse().join("/") : "");
const MAU: Record<string, string> = { bac: "#1f4e5f", trung: "#7a4a22", tay_nguyen: "#5b4a2e", nam: "#2f5d3a" };
const khongDau = (s: string) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
const nhan = (d?: number | null) => nhanDiem(d);
const phay = (x: number) => String(x).replace(".", ",");
// Ước đoán trên màn: gói miễn phí hủy thì có thể «đặt giữ, trả sau» (hạn = hạn hủy − 2 ngày). Máy chủ tính lại ở bước sau.
const traSauGoi = (g: any, homNay: string) => { if (!g?.mien_phi_huy || !g?.huy_han || g?.cho_tra_sau === false) return ""; /* KS-17 */ const h = themNgay(String(g.huy_han).slice(0, 10), -2); return h > homNay ? h : ""; };

const Ico = ({ d, s = 16, fill = false }: { d: string; s?: number; fill?: boolean }) =>
  <svg width={s} height={s} viewBox="0 0 24 24" fill={fill ? "currentColor" : "none"} stroke={fill ? "none" : "currentColor"} strokeWidth="1.9" aria-hidden="true" style={{ flex: "none" }}><path d={d} /></svg>;
const P = {
  kinh: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-3.5-3.5", lich: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
  nguoi: "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21v-1a7 7 0 0 1 14 0v1M17 11a3 3 0 1 0 0-6M22 21v-1a5 5 0 0 0-4-4.9",
  giuong: "M3 18V7M3 13h18v5M21 13a4 4 0 0 0-4-4h-6v4", ghim: "M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z",
  dung: "M5 13l4 4L19 7", coc: "M4 8h13v5a6 6 0 0 1-6 6h-1a6 6 0 0 1-6-6zM17 9h1a3 3 0 0 1 0 6h-1",
  khien: "M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5z", gio: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm0 4v5l3 2",
  tim: "M12 20s-7-4.4-9.2-8.9A5 5 0 0 1 12 6.4a5 5 0 0 1 9.2 4.7C19 15.6 12 20 12 20z", phai: "m9 6 6 6-6 6", trai: "m15 6-6 6 6 6",
  may: "M4 7h4l2-2h4l2 2h4v12H4zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", khoa: "M7 10V7a5 5 0 0 1 10 0v3M5 10h14v11H5z",
  the: "M3 12V4h8l10 10-8 8z", sao: "m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z",
  qua: "M4 11h16v10H4zM3 7h18v4H3zM12 7v14M12 7S10 3 7.5 4 9 7 12 7zm0 0s2-4 4.5-3S15 7 12 7z",
};

/* KS-18 · Ảnh tạm cho thẻ phòng (Chủ tịch chọn «3» 03/11/2026): 1.358 ảnh nhưng chỉ 56 ảnh gắn loại phòng → thẻ
   phòng trống «Ảnh đang cập nhật». Phòng chưa có ảnh riêng thì mượn ảnh khách sạn — ưu tiên nhóm «Phòng» chưa gắn
   phòng nào, rồi ảnh album không phải bìa — mỗi phòng một ảnh (theo thứ tự thẻ), góc ảnh ghi «Ảnh khách sạn».
   Điều hành gắn ảnh cho phòng (nút «Sửa» trong Album, KS-17) thì thẻ tự về ảnh riêng, nhãn tự mất. */
export function anhTamPhong(anh: any[], i: number): any | null {
  const tu = anh.filter((a) => !a.loai_phong_id);
  const phong = tu.filter((a) => a.nhom === "phong");
  const kho = phong.length ? phong : tu.filter((a) => !a.la_bia).length ? tu.filter((a) => !a.la_bia) : tu.length ? tu : anh;
  return kho.length ? kho[i % kho.length] : null;
}

function AnhTrong({ k, cao }: { k: any; cao?: number }) {
  const chu = (k.ten || "?").normalize("NFC").trim().charAt(0).toUpperCase();
  return <span className="ksv-trong" style={{ minHeight: cao }}><b style={{ background: MAU[k.mien] || "#3d4b59" }}>{chu}</b><small>Ảnh đang cập nhật</small></span>;
}

/** Thanh tiến trình 3 bước của phần đặt phòng (KS-16p). */
export function Buoc3({ toi, coGia = true }: { toi: 1 | 2 | 3; coGia?: boolean }) {
  const ten = coGia ? ["Thông tin khách", "Thanh toán", "Đã xác nhận"] : ["Thông tin khách", "Gửi yêu cầu", "Vietourist báo lại"];
  return <div className="ksv-bk"><div className="ksv-stp">{ten.map((t, i) => <span key={t} style={{ display: "contents" }}>
    {i > 0 && <span className={`ln ${i < toi ? "on" : ""}`} />}
    <span className={`s ${i + 1 < toi ? "dn" : i + 1 === toi ? "on" : ""}`}><i>{i + 1 < toi ? "✓" : i + 1}</i>{t}</span></span>)}</div></div>;
}

/** Album toàn màn: tab theo nhóm ảnh (đếm số thật) + tab Video (tối đa 3). */
function Album({ ks, dau, onDong }: { ks: any; dau?: { nhom?: string; lp?: number }; onDong: () => void }) {
  const anh: any[] = ks.anh || [], video: any[] = (ks.video || []).slice(0, 3);
  const nhom = Object.entries(ks.nhom_anh || {}).map(([k, t]) => [k, t as string, anh.filter((a) => a.nhom === k).length] as const).filter((x) => x[2] > 0);
  const [tab, setTab] = useState<string>(dau?.lp ? `lp${dau.lp}` : dau?.nhom || "");
  const [i, setI] = useState(0);
  const ds = tab === "video" ? [] : tab.startsWith("lp") ? anh.filter((a) => a.loai_phong_id === Number(tab.slice(2))) : tab ? anh.filter((a) => a.nhom === tab) : anh;
  const a = ds[Math.min(i, Math.max(0, ds.length - 1))];
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onDong(); if (e.key === "ArrowRight") setI((x) => (x + 1) % Math.max(1, ds.length)); if (e.key === "ArrowLeft") setI((x) => (x - 1 + ds.length) % Math.max(1, ds.length)); };
    window.addEventListener("keydown", h); document.body.style.overflow = "hidden";
    return () => { window.removeEventListener("keydown", h); document.body.style.overflow = ""; };
  }, [ds.length, onDong]);
  const chon = (t: string) => { setTab(t); setI(0); };
  return <div className="ksv-alb" role="dialog" aria-modal="true" aria-label={`Album ảnh ${ks.ten}`}>
    <div className="ksv-alb-in">
      <div className="ksv-alb-hd"><b>{ks.ten} <span>· {anh.length} ảnh{video.length ? ` · ${video.length} video` : ""}</span></b>
        <button type="button" className="ksv-alb-x" onClick={onDong} aria-label="Đóng album">✕</button></div>
      <div className="ksv-alb-tabs">
        <button type="button" className={!tab ? "on" : ""} onClick={() => chon("")}>Tất cả {anh.length}</button>
        {video.length > 0 && <button type="button" className={tab === "video" ? "on" : ""} onClick={() => chon("video")}>▶ Video {video.length}</button>}
        {dau?.lp && <button type="button" className={tab === `lp${dau.lp}` ? "on" : ""} onClick={() => chon(`lp${dau.lp}`)}>Phòng đã chọn {anh.filter((x) => x.loai_phong_id === dau.lp).length}</button>}
        {nhom.map(([k, t, n]) => <button key={k} type="button" className={tab === k ? "on" : ""} onClick={() => chon(k)}>{t} {n}</button>)}</div>
      {tab === "video" ? <div className="ksv-alb-vid">{video.map((v) => <div key={v.id ?? v.xem} style={{ aspectRatio: "16 / 9" }}><VideoO v={v} ten={ks.ten} /></div>)}</div>
        : a ? <>
          <div className="ksv-alb-big"><img src={a.hien} alt={a.mo_ta_thay_the || a.chu_thich || `${ks.ten} — ${a.nhom_ten}`} />
            {ds.length > 1 && <><button type="button" className="ksv-alb-nv l" aria-label="Ảnh trước" onClick={() => setI((i - 1 + ds.length) % ds.length)}><Ico d={P.trai} s={20} /></button>
              <button type="button" className="ksv-alb-nv r" aria-label="Ảnh tiếp" onClick={() => setI((i + 1) % ds.length)}><Ico d={P.phai} s={20} /></button></>}
            <span className="ksv-alb-cap">{Math.min(i, ds.length - 1) + 1} / {ds.length}{a.chu_thich ? ` · ${a.chu_thich}` : ` · ${a.nhom_ten}`}</span></div>
          <div className="ksv-alb-th">{ds.map((x, j) => <button key={x.id} type="button" className={j === i ? "on" : ""} onClick={() => setI(j)} aria-label={`Ảnh ${j + 1}`}><img src={x.nho} alt="" loading="lazy" /></button>)}</div></>
          : <p style={{ color: "#cfd8e6" }}>Nhóm này chưa có ảnh.</p>}
    </div></div>;
}

// KS-16q: rieng = đang ở trang riêng kh.vietourist.vn/hotel (khách có thể chưa đăng nhập — xem qua cửa /cong/mo);
// moId = đường dẫn /hotel/<id> mở thẳng khách sạn đó.
export default function KhachSanVtd({ lienHe = "", ten = "", rieng = false, moId }: { lienHe?: string; ten?: string; rieng?: boolean; moId?: number }) {
  const homNay = iso(new Date());
  const [q, setQ] = useState<Q>({ tinh: "", vao: themNgay(homNay, 7), ra: themNgay(homNay, 9), nl: 2, te: 0, phong: 1 });
  const [ds, setDs] = useState<any>(null);
  const [daTim, setDaTim] = useState(false);      // KS-16p: bước 1 là trang tìm; bấm TÌM mới sang danh sách
  const [chiDat, setChiDat] = useState(false);
  const [loi, setLoi] = useState("");
  const [loc, setLoc] = useState<Loc>(LOC0);
  const [sx, setSx] = useState("phu_hop");
  const [pop, setPop] = useState(false);
  const [moLoc, setMoLoc] = useState(false);
  const [anhI, setAnhI] = useState<Record<number, number>>({});
  const [thich, setThich] = useState<Record<number, boolean>>({});
  const [ks, setKs] = useState<any>(null);
  const [album, setAlbum] = useState<{ nhom?: string; lp?: number } | null>(null);
  const [locP, setLocP] = useState<string[]>([]);
  const [chon, setChon] = useState<Record<number, number>>({});
  const [buoc, setBuoc] = useState<"ds" | "ks" | "gui" | "cuoi" | "xong" | "tra" | "don">("ds");
  const [tinh, setTinh] = useState<any>(null);
  const [kh, setKh] = useState({ ten, lien_he: lienHe, email: "", yc: [] as string[], ghi: "", dongy: false, khac: false });
  const [cach, setCach] = useState<"ngay" | "sau">("ngay");
  const [tt, setTt] = useState<"qr" | "the">("qr");
  const [donKs, setDonKs] = useState<any>(null);
  const [baoKs, setBaoKs] = useState("");
  const [lamMoi, setLamMoi] = useState(0);
  const [don, setDon] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [vc, setVc] = useState<{ ma: string; ap: any; loi: string }>({ ma: "", ap: null, loi: "" });   // KS-16
  const [gioDen, setGioDen] = useState("Chưa rõ");                   // KS-16s
  const [banDo, setBanDo] = useState(false);
  const [theoKhung, setTheoKhung] = useState(true);
  const [khung, setKhung] = useState<{ s: number; w: number; n: number; e: number } | null>(null);
  const [ghimChon, setGhimChon] = useState<number | null>(null);
  const diem = ks?.diem || ds?.diem;
  const duKien = (tien: number) => diem?.dang_bat && tien > 0 ? Math.floor(tien / (diem.dong_moi_diem || 10000) * diem.he_so) : 0;
  const dem = Math.max(1, Math.round((new Date(q.ra).getTime() - new Date(q.vao).getTime()) / 864e5));
  const len = () => window.scrollTo(0, 0);

  const tim = async (qq: Q = q, sang = false) => {
    setLoi(""); setBusy(true);
    try {
      // Lấy mọi thành phố một lần (danh mục nhỏ) rồi lọc ngay trên màn — đổi thành phố không phải chờ máy chủ.
      const p = new URLSearchParams({ tinh: "", vao: qq.vao, ra: qq.ra, nguoi_lon: String(qq.nl), tre_em: String(qq.te), so_phong: String(qq.phong), tuoi: tuoiStr(qq) });
      const r = await xemCong(`/ks-vtd/tim?${p}`);
      setDs(r);
      // KS-16s: mặc định «Tất cả điểm đến» — không tự chọn thành phố đầu danh sách
      setBuoc("ds");
      if (sang) { setDaTim(true); len(); }
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  useEffect(() => { tim().then(() => { if (moId) moKs(moId); }); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
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
        if (ma) goiCong(`/ks-vtd/don/${encodeURIComponent(ma)}`).then((d) => { setDonKs(d); setBuoc(d.trang_thai === "cho_tra" && d.cach_tra !== "sau" ? "tra" : "don"); }).catch(() => {});
      }
    } catch { /* bỏ qua */ }
  }, []);

  const moKs = async (id: number, qq: Q = q) => {
    setLoi(""); setBusy(true);
    try {
      const p = new URLSearchParams({ vao: qq.vao, ra: qq.ra, nguoi_lon: String(qq.nl), tre_em: String(qq.te), so_phong: String(qq.phong), tuoi: tuoiStr(qq) });
      setKs(await xemCong(`/ks-vtd/${id}?${p}`)); setChon({}); setLocP([]); setBuoc("ks"); len();
      if (rieng) { try { window.history.replaceState(null, "", duongRieng("hotel", id)); } catch { /* bỏ qua */ } }
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  // KS-16l → KS-16q: trên cổng, khách sạn chưa có gói đặt được mở trang riêng /hotel/<id> ở tab mới; ở chính trang
  // riêng thì mở chi tiết ngay tại chỗ (gửi yêu cầu giữ phòng).
  const moThe = (k: any) => { if (!rieng && k.dat_ngay === false && k.link_ngoai) { moNgoai(duongRieng("hotel", k.id)); return; } moKs(k.id); };

  const loc2 = useMemo(() => {
    if (!ds) return [];
    const L = loc, k0 = khongDau(L.ten.trim());
    const r = ds.khach_san.filter((k: any) => (!q.tinh || k.tinh_thanh === q.tinh)).filter((k: any) => {
      const g = k.gia_tu?.gia_dem;
      if ((L.coGia || chiDat) && !k.gia_tu) return false;
      if (L.huy && !k.co_mien_phi_huy) return false;
      if (L.sang && !k.co_bua_sang) return false;
      if (L.diem9 && !((k.danh_gia?.diem_tb || 0) >= 9)) return false;
      if (L.conPhong && k.het_phong) return false;
      if (L.sao.length && !L.sao.includes(k.sao)) return false;
      if (L.loai.length && !L.loai.includes(k.loai)) return false;
      if (L.khu.length && !L.khu.includes(k.khu_vuc)) return false;
      if (L.ti.length && !L.ti.every((t) => (k.tien_ich || []).includes(t))) return false;
      if (k0 && !khongDau(`${k.ten} ${k.khu_vuc} ${k.gan} ${k.tinh_thanh}`).includes(k0)) return false;
      if (!hopNhom(LOC_TT, L.tt, k) || !hopNhom(LOC_AN, L.an, k) || !hopNhom(LOC_KC, L.kc, k) || !hopNhom(LOC_GI, L.gi, k)) return false;
      if (L.dk && !((k.danh_gia?.diem_tb || 0) >= L.dk)) return false;
      if (g != null && (g < L.min || (L.max && g > L.max))) return false;
      return true;
    });
    const gia = (k: any, mac: number) => k.gia_tu?.gia_dem ?? mac;
    const uuDai = (k: any) => (k.gia_tu?.niem_yet_dem && k.gia_tu.niem_yet_dem > k.gia_tu.gia_dem ? 1 - k.gia_tu.gia_dem / k.gia_tu.niem_yet_dem : 0);
    const f: Record<string, (a: any, b: any) => number> = {
      phu_hop: (a, b) => (+!a.gia_tu) - (+!b.gia_tu) || (b.danh_gia?.diem_tb || 0) - (a.danh_gia?.diem_tb || 0) || a.ten.localeCompare(b.ten),
      gia_thap: (a, b) => gia(a, 9e12) - gia(b, 9e12), gia_cao: (a, b) => gia(b, -1) - gia(a, -1),
      diem: (a, b) => (b.danh_gia?.diem_tb || 0) - (a.danh_gia?.diem_tb || 0), sao: (a, b) => b.sao - a.sao,
      gan: (a, b) => (a.km_trung_tam ?? 999) - (b.km_trung_tam ?? 999),
      uu_dai: (a, b) => uuDai(b) - uuDai(a) || gia(a, 9e12) - gia(b, 9e12),
    };
    return [...r].sort(f[sx]);
  }, [ds, loc, sx, q.tinh, chiDat]);
  const trongTp = (ds?.khach_san || []).filter((k: any) => !q.tinh || k.tinh_thanh === q.tinh);
  const dem2 = (f: (k: any) => boolean) => trongTp.filter(f).length;
  const giaMax = Math.max(500000, ...trongTp.map((k: any) => k.gia_tu?.gia_dem || 0));
  const khuDs = Array.from(new Set(trongTp.map((k: any) => k.khu_vuc).filter(Boolean))) as string[];
  const tiDs = Array.from(new Set(trongTp.flatMap((k: any) => k.tien_ich || []))) as string[];

  const dongChon = useMemo(() => (ks?.phong || []).flatMap((p: any) => p.goi.filter((g: any) => chon[g.id]).map((g: any) => ({ p, g, n: chon[g.id] }))), [ks, chon]);
  // KS-14: số phòng chọn được ở một gói = số còn của loại phòng trừ số đã chọn ở các gói khác cùng loại.
  const conCho = (p: any, gid: number) => Math.max(0, (p.con ?? p.so_phong) - p.goi.filter((g: any) => g.id !== gid).reduce((a: number, g: any) => a + (chon[g.id] || 0), 0));
  const soChon = dongChon.reduce((a: number, x: any) => a + x.n, 0);
  const tienChon = dongChon.reduce((a: number, x: any) => a + x.n * x.g.tong, 0);

  const sangGui = async (dongMoi?: Record<number, number>) => {
    const cs = dongMoi || chon;
    const ds_ = (ks?.phong || []).flatMap((p: any) => p.goi.filter((g: any) => cs[g.id]).map((g: any) => ({ goi_id: g.id, so: cs[g.id] })));
    if (!ds_.length) { setLoi("Chọn ít nhất 1 phòng"); return; }
    setLoi(""); setBusy(true);
    try {
      const r = await goiCong(`/ks-vtd/${ks.id}/tinh`, { vao: q.vao, ra: q.ra, chon: ds_, nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q) });
      setTinh(r); if (dongMoi) setChon(dongMoi);
      setCach(r.han_tra_sau ? "sau" : "ngay");
      setVc({ ma: "", ap: null, loi: "" });
      setBuoc("gui"); len();
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const moYeuCauTrong = (loaiPhong = "") => { setTinh({ dong: [], so_phong: q.phong, tien_phong: 0, thue_phi: 0, tong: 0, dem, loai_phong: loaiPhong }); setBuoc("gui"); len(); };
  const kiemKhach = (coGia: boolean) => {
    if (kh.ten.trim().split(/\s+/).length < 2) return coGia ? "Ghi đủ họ và tên khách nhận phòng" : "Ghi đủ họ và tên người nhận phòng";
    if (coGia ? kh.lien_he.replace(/\D/g, "").length < 9 : kh.lien_he.replace(/\D/g, "").length < 9 && !/@/.test(kh.lien_he))
      return coGia ? "Ghi số điện thoại / Zalo để Vietourist báo xác nhận" : "Ghi số điện thoại / Zalo hoặc email để Vietourist báo lại";
    if (kh.email && !/^\S+@\S+\.\S+$/.test(kh.email)) return "Email chưa đúng";
    return "";
  };
  const yeuCau = () => [kh.yc.join(", "), kh.ghi].filter(Boolean).join(" · ");
  const gui = async () => {
    const e = kiemKhach(false); if (e) { setLoi(e); return; }
    if (!kh.dongy) { setLoi("Đánh dấu đồng ý điều kiện giữ phòng để gửi"); return; }
    setLoi(""); setBusy(true);
    try {
      const r = await goiCong(`/ks-vtd/${ks.id}/yeu-cau`, { ngay_nhan: q.vao, ngay_tra: q.ra, nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q), so_phong: tinh?.so_phong || q.phong,
        chon: dongChon.map((x: any) => ({ goi_id: x.g.id, so: x.n })), loai_phong: tinh?.loai_phong || "",
        nguoi_nhan_phong: kh.ten, lien_he: kh.lien_he, yeu_cau_them: yeuCau(), gio_den: gioDen === "Chưa rõ" ? "" : gioDen });
      setDon(r.don); setBuoc("xong"); len();
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const sangCuoi = () => { const e = kiemKhach(true); if (e) { setLoi(e); return; } setLoi(""); setBuoc("cuoi"); len(); };

  const apVoucher = async () => {
    if (!vc.ma.trim()) { setVc({ ...vc, loi: "Ghi mã voucher" }); return; }
    setBusy(true);
    try { setVc({ ...vc, ap: await goiCong(`/ks-vtd/don/kiem-voucher`, { ma: vc.ma.trim(), tong: tinh.tong }), loi: "" }); }
    catch (x: any) { setVc({ ...vc, ap: null, loi: x.message }); } finally { setBusy(false); }
  };
  const giam = vc.ap?.gia_tri || 0;
  const traSau = cach === "sau" && !!tinh?.han_tra_sau;

  const datNgay = async () => {
    if (tinh && tinh.mo_thanh_toan === false) return;                // KS-16s: thanh toán chưa mở — không gửi gì, không giữ phòng
    const e = kiemKhach(true); if (e) { setLoi(e); setBuoc("gui"); return; }
    if (!kh.dongy) { setLoi("Đánh dấu đồng ý chính sách hủy và điều kiện đặt phòng"); return; }
    setLoi(""); setBusy(true);
    try {
      const r = await goiCong(`/ks-vtd/don/dat/${ks.id}`, { vao: q.vao, ra: q.ra, nguoi_lon: q.nl, tre_em: q.te, tuoi_tre_em: tuoiDs(q),
        chon: dongChon.map((x: any) => ({ goi_id: x.g.id, so: x.n })), ho_ten: kh.ten, lien_he: kh.lien_he, email: kh.email,
        yeu_cau: yeuCau(), dong_y: kh.dongy, ma_voucher: vc.ap?.ma || "", cach_tra: traSau ? "sau" : "ngay", gio_den: gioDen === "Chưa rõ" ? "" : gioDen });
      setDonKs(r.don); setLamMoi((x) => x + 1);
      if (traSau) { setBaoKs(""); setBuoc("don"); len(); return; }
      if (tt === "the") { diCongThe(await goiCong(`/ks-vtd/don/${encodeURIComponent(r.don.ma)}/the`, {})); return; }
      setBuoc("tra"); len();
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  const moDon = (d: any) => { setDonKs(d); setBaoKs(""); setBuoc(d.trang_thai === "cho_tra" && d.co_the_tra && d.cach_tra !== "sau" ? "tra" : "don"); len(); };
  const veDs = () => { setBuoc("ds"); setKs(null); setChon({}); setDonKs(null); setBaoKs(""); setLoi(""); };

  const doiQ = (k: "nl" | "te" | "phong", v: number) => setQ({ ...q, [k]: v });
  const khachPop = pop && <div className="ksv-pop">{([["nl", "Người lớn", 1, 30], ["te", "Trẻ em", 0, 20], ["phong", "Phòng", 1, 9]] as const).map(([k, t, a, b]) =>
    <div key={k} className="ksv-step"><span>{t}</span><div>
      <button type="button" aria-label={`Bớt ${t}`} onClick={() => doiQ(k, Math.max(a, q[k] - 1))}>−</button><b>{q[k]}</b>
      <button type="button" aria-label={`Thêm ${t}`} onClick={() => doiQ(k, Math.min(b, q[k] + 1))}>+</button></div></div>)}
    {q.te > 0 && <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>{Array.from({ length: q.te }, (_, i) =>
      <label key={i} style={{ display: "flex", flexDirection: "column", fontSize: 12 }}>Tuổi trẻ {i + 1}
        <select className="ksv-sel" value={(q.tuoi || [])[i] ?? -1} onChange={(e) => { const t = Array.from({ length: q.te }, (_x, j) => (q.tuoi || [])[j] ?? -1); t[i] = Number(e.target.value); setQ({ ...q, tuoi: t }); }}>
          <option value={-1}>Chọn tuổi</option>{Array.from({ length: 18 }, (_x, n) => <option key={n} value={n}>{n} tuổi</option>)}</select></label>)}
      <small className="ksv-muted" style={{ gridColumn: "1 / -1" }}>Chọn tuổi từng bé để xem giá đúng chính sách trẻ em của khách sạn.</small></div>}
    <button type="button" className="ksv-btn" onClick={() => setPop(false)}>Xong</button></div>;
  const chonTp = <select value={q.tinh} onChange={(e) => { setQ({ ...q, tinh: e.target.value }); setLoc(LOC0); }} aria-label="Điểm đến">
    <option value="">Tất cả điểm đến ({(ds?.thanh_pho || []).reduce((a: number, t: any) => a + t.so, 0)})</option>
    {(ds?.thanh_pho || []).map((t: any) => <option key={t.ten} value={t.ten}>{t.ten} ({t.so})</option>)}</select>;
  // KS-16s: «Điểm đến phổ biến» — mỗi thành phố một ô có ảnh bìa của một khách sạn ở đó + số khách sạn thật
  const diemDen = (ds?.thanh_pho || []).slice(0, 8).map((t: any) => ({ ...t, anh: (ds.khach_san.find((k: any) => k.tinh_thanh === t.ten && k.anh?.length)?.anh || [])[0] }));
  const doiTp = (t: string) => { setQ({ ...q, tinh: t }); setLoc(LOC0); setKhung(null); };
  const dsDiemDen = diemDen.length > 1 && <section className="ksv-dd"><h2 className="ksv-h2">Điểm đến phổ biến</h2><div className="ksv-ddr">{diemDen.map((t: any) =>
    <button type="button" key={t.ten} className={`ksv-ddc ${q.tinh === t.ten ? "on" : ""}`} onClick={() => { doiTp(t.ten); if (!daTim) tim({ ...q, tinh: t.ten }, true); }}>
      {t.anh ? <img src={t.anh.nho} alt="" loading="lazy" /> : <span className="ph" />}<b>{t.ten}</b><small>{t.so} khách sạn</small></button>)}</div></section>;
  const oVao = <input type="date" value={q.vao} min={homNay} aria-label="Ngày nhận phòng" onChange={(e) => { const v = e.target.value; if (v) setQ({ ...q, vao: v, ra: q.ra <= v ? themNgay(v, 1) : q.ra }); }} />;
  const oRa = <input type="date" value={q.ra} min={themNgay(q.vao, 1)} aria-label="Ngày trả phòng" onChange={(e) => e.target.value > q.vao && setQ({ ...q, ra: e.target.value })} />;
  const khachTxt = `${q.nl} người lớn${q.te ? ` · ${q.te} trẻ em` : ""}`;

  // Thanh tìm gọn (danh sách, trang khách sạn) — nền xanh đậm như Agoda.
  const thanhTim = (kieu: "ds" | "ks") => <form className="ksv-sbar" onSubmit={(e) => { e.preventDefault(); setPop(false); if (kieu === "ks" && ks) moKs(ks.id); else tim(q, true); }}>
    <label className="ksv-f ksv-f-tp"><Ico d={P.kinh} s={18} /><span><small>{kieu === "ks" ? "Khách sạn" : "Điểm đến"}</small>{kieu === "ks" && ks ? <b>{ks.ten}</b> : chonTp}</span></label>
    <label className="ksv-f"><Ico d={P.lich} s={18} /><span><small>Nhận phòng · {thuDai(q.vao)}</small>{oVao}</span></label>
    <label className="ksv-f"><Ico d={P.lich} s={18} /><span><small>Trả phòng · {dem} đêm</small>{oRa}</span></label>
    <div className="ksv-f" style={{ position: "relative" }}><Ico d={P.nguoi} s={18} /><button type="button" className="ksv-khach" onClick={() => setPop(!pop)} aria-expanded={pop}>
      <small>{q.phong} phòng</small><b>{q.nl} NL{q.te ? ` · ${q.te} TE` : ""}</b></button>{khachPop}</div>
    <button className="ksv-go" type="submit" disabled={busy}>{kieu === "ks" ? "Cập nhật" : "TÌM"}</button></form>;

  const css = <style dangerouslySetInnerHTML={{ __html: CSS }} />;
  if (!ds) return <div className="ksv">{css}<p>{loi || "Đang tải khách sạn…"}</p></div>;

  if (buoc === "tra" && donKs) return <div className="ksv">{css}
    <TraTien d={donKs} onDoi={(d) => { setDonKs(d); setLamMoi((x) => x + 1); if (d.trang_thai !== "cho_tra") { setBuoc("don"); len(); } }}
      onLai={veDs} /></div>;

  if (buoc === "don" && donKs) return <div className="ksv">{css}
    <DonKs d={donKs} bao={baoKs} loi={loi} onDoi={(d) => { setDonKs(d); setLamMoi((x) => x + 1); }} onTra={() => { setBuoc("tra"); len(); }} onLai={veDs} /></div>;

  if (buoc === "xong" && don) return <div className="ksv">{css}<Buoc3 toi={3} coGia={false} />
    <div className="ksv-done"><span className="ck2"><Ico d={P.dung} s={28} /></span><div><div className="ksv-h1" style={{ color: "var(--ksv-ok)" }}>Đã gửi yêu cầu giữ phòng</div>
      <div style={{ fontSize: 15, marginTop: 4 }}>Mã yêu cầu <b>{don.the_tham_chieu}</b> · {ks.ten}</div></div></div>
    <section className="ksv-panel" style={{ padding: 20 }}>
      <span>{ngay(q.vao)} → {ngay(q.ra)} · {don.so_phong} phòng · {don.nguoi_lon} người lớn{don.tre_em ? ` · ${don.tre_em} trẻ em` : ""}</span>
      <span className="ksv-muted">Điều hành Vietourist liên hệ khách sạn giữ phòng rồi báo lại qua {kh.lien_he} trong giờ làm việc. Bạn chưa phải trả tiền ở bước này. Theo dõi yêu cầu ở mục «Yêu cầu đặt phòng của bạn» bên dưới.</span>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}><button type="button" className="ksv-btn" onClick={veDs}>Tìm chỗ ở khác</button></div>
    </section></div>;

  const coGia = !!(tinh && tinh.dong?.length);
  const tomTat = tinh && ks && <TomTat ks={ks} q={q} tinh={tinh} giam={giam} maVc={vc.ap?.ma} hang={diem?.dang_bat ? diem : null} diemDk={duKien(tinh.tong - giam)}
    traSau={traSau} chon={dongChon} homNay={homNay} />;
  const loiBox = loi && <div className="ksv-loi">{loi}</div>;

  if (buoc === "gui" && ks && tinh) return <div className="ksv">{css}<Buoc3 toi={1} coGia={coGia} />
    <div className="ksv-tmr" style={coGia ? undefined : { background: "var(--ksv-asoft)", color: "var(--ksv-ink)" }}><Ico d={P.gio} s={16} />
      {coGia ? (traSau ? <span>Gói này cho <b>đặt giữ, trả trước {dmy(tinh.han_tra_sau)}</b> — hôm nay chưa phải trả</span>
        : <span>Phòng được giữ <b>15 phút</b> khi bạn bấm thanh toán ở bước cuối</span>)
        : <span>Vietourist báo giá và giữ phòng — bạn chưa trả tiền ở bước này</span>}</div>
    <button type="button" className="ksv-link" onClick={() => { setBuoc("ks"); setLoi(""); }}>← Quay lại chọn phòng</button>
    <div className="ksv-co">
      <div className="ksv-col">
        {kh.ten.trim() && <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 12 }}><span className="ksv-av">{kh.ten.trim().split(/\s+/).pop()?.charAt(0).toUpperCase()}</span>
          <span>Chào <b>{kh.ten.trim().split(/\s+/).pop()}</b>! Thông tin đã điền sẵn từ tài khoản của bạn — kiểm tra lại trước khi tiếp.</span></div>}
        {coGia && <section className="ksv-panel ksv-sec0"><h3>Chọn cách thanh toán</h3>
          {tinh.han_tra_sau && <label className={`ksv-radio ${traSau ? "on" : ""}`}><input type="radio" name="ksv-cach" checked={traSau} onChange={() => setCach("sau")} />
            <span><b>Đặt giữ, trả trước {dmy(tinh.han_tra_sau)}</b><span className="ksv-okc" style={{ display: "block" }}>✓ Hôm nay chưa phải trả</span>
              {tinh.huy_mien_phi_den && <span className="ksv-okc" style={{ display: "block" }}>✓ Miễn phí hủy trước {dmy(tinh.huy_mien_phi_den)}</span>}
              <small className="ksv-muted">Vietourist không lưu thẻ: bạn tự trả trước hạn bằng QR hoặc thẻ từ trang đơn; quá hạn chưa trả, đơn tự hủy, không mất phí.</small></span></label>}
          <label className={`ksv-radio ${!traSau ? "on" : ""}`}><input type="radio" name="ksv-cach" checked={!traSau} onChange={() => setCach("ngay")} />
            <span><b>Trả ngay</b><span className="ksv-muted" style={{ display: "block" }}>QR chuyển khoản hoặc thẻ qua cổng thanh toán</span>
              <span className="ksv-logos"><span>QR</span><span>NAPAS</span>{ks.the_bat && <><span>VISA</span><span>Mastercard</span><span>JCB</span></>}</span></span></label>
          {!tinh.han_tra_sau && <small className="ksv-muted" style={{ padding: "0 14px 10px" }}>{tinh.dong.some((x: any) => !x.huy_han) ? "Có gói «Không hoàn tiền» nên chỉ trả ngay." : "Ngày nhận phòng gần hạn hủy miễn phí nên chỉ trả ngay."}</small>}</section>}
        <section className="ksv-panel" style={{ padding: 18 }}><h3 className="ksv-h3">Ai nhận phòng?</h3><small className="ksv-muted" style={{ marginTop: -6 }}>Tên phải khớp giấy tờ tùy thân khi nhận phòng.</small>
          <div className="ksv-f2">
            <label className="ksv-fld">Họ và tên (như trên CCCD / hộ chiếu)<input value={kh.ten} onChange={(e) => setKh({ ...kh, ten: e.target.value })} autoComplete="name" /></label>
            <label className="ksv-fld">{coGia ? "Số điện thoại / Zalo" : "Số điện thoại / Zalo hoặc email"}<input value={kh.lien_he} onChange={(e) => setKh({ ...kh, lien_he: e.target.value })} autoComplete="tel" /></label>
            {coGia && <label className="ksv-fld">Email nhận xác nhận (không bắt buộc)<input type="email" value={kh.email} onChange={(e) => setKh({ ...kh, email: e.target.value })} autoComplete="email" /></label>}</div>
          <label className="ksv-chk"><input type="checkbox" checked={kh.khac} onChange={(e) => setKh({ ...kh, khac: e.target.checked })} /><span>Tôi đặt phòng cho người khác — ghi tên người ở phía trên</span></label></section>
        <section className="ksv-panel" style={{ padding: 18 }}><h3 className="ksv-h3">Giờ đến dự kiến</h3><small className="ksv-muted" style={{ marginTop: -6 }}>Khách sạn chuẩn bị phòng theo giờ bạn đến. Nhận phòng từ {ks.gio_nhan}.</small>
          <label className="ksv-fld" style={{ maxWidth: 320 }}>Bạn đến khoảng<select className="ksv-sel" value={gioDen} onChange={(e) => setGioDen(e.target.value)}>{GIO_DEN.map((t) => <option key={t} value={t}>{t}</option>)}</select></label></section>
        <section className="ksv-panel" style={{ padding: 18 }}><h3 className="ksv-h3">Yêu cầu đặc biệt</h3><small className="ksv-muted" style={{ marginTop: -6 }}>Tùy tình trạng phòng. Gửi khách sạn cùng đơn; khách sạn cố gắng đáp ứng nhưng không bảo đảm.</small>
          <div className="ksv-req">{([["Loại phòng bạn muốn?", ["Không hút thuốc", "Hút thuốc"]], ["Kiểu giường bạn muốn?", ["Một giường lớn", "Hai giường đơn"]]] as const).map(([h, ops]) =>
            <div key={h}><b>{h}</b>{ops.map((t) => <label key={t} className="ksv-chk"><input type="radio" name={h} checked={kh.yc.includes(t)}
              onChange={() => setKh({ ...kh, yc: [...kh.yc.filter((x) => !(ops as readonly string[]).includes(x)), t] })} /><span>{t}</span></label>)}</div>)}</div>
          <details><summary className="ksv-link" style={{ fontSize: 13 }}>Thêm yêu cầu khác (tầng cao, nôi em bé, đưa đón…)</summary>
            <div className="ksv-f2" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", marginTop: 8 }}>{["Tầng cao", "Nôi em bé", "Nhận phòng sớm", "Trả phòng muộn", "Phòng liền kề", "Đưa đón sân bay"].map((t) =>
              <label key={t} className="ksv-chk"><input type="checkbox" checked={kh.yc.includes(t)} onChange={(e) => setKh({ ...kh, yc: e.target.checked ? [...kh.yc, t] : kh.yc.filter((x) => x !== t) })} /><span>{t}</span></label>)}</div>
            <label className="ksv-fld" style={{ marginTop: 8 }}>Ghi thêm<textarea value={kh.ghi} onChange={(e) => setKh({ ...kh, ghi: e.target.value })} maxLength={800} /></label></details></section>
        {coGia && <QuyenLoi tinh={tinh} traSau={traSau} diemDk={diem?.dang_bat && diem.cach_tinh !== "hoa_hong" ? duKien(tinh.tong - giam) : 0} hang={diem} />}
        {coGia && dongChon.some((x: any) => (x.p.con ?? 9) === 1) && <div className="ksv-hurry">Nhanh tay! Phòng cuối cùng ở giá này cho ngày bạn chọn</div>}
        {loiBox}
        {coGia ? <div className="ksv-panel" style={{ padding: 16 }}><button type="button" className="ksv-btn big wide" onClick={sangCuoi}>TIẾP: BƯỚC CUỐI</button>
          <div className="ksv-okc" style={{ textAlign: "center", fontSize: 13 }}>{traSau ? "Hôm nay bạn trả ₫ 0" : `Bạn trả ₫ ${vnd(tinh.tong - giam)}`}</div></div>
          : <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "16px 20px" }}>
            <label className="ksv-chk" style={{ flex: 1, minWidth: 220, alignItems: "flex-start" }}><input type="checkbox" checked={kh.dongy} onChange={(e) => setKh({ ...kh, dongy: e.target.checked })} />
              <span style={{ fontSize: 13 }}>Tôi đồng ý để Vietourist liên hệ giữ phòng theo thông tin trên. Giá và chính sách hủy theo gói đã chọn.</span></label>
            <button type="button" className="ksv-btn big" disabled={busy} onClick={gui}>Gửi yêu cầu giữ phòng</button></div>}
      </div>
      {tomTat}
    </div></div>;

  if (buoc === "cuoi" && ks && tinh) return <div className="ksv">{css}<Buoc3 toi={2} />
    {traSau ? <div className="ksv-tmr" style={{ background: "var(--ksv-oksoft)", color: "var(--ksv-ok)" }}><Ico d={P.khien} s={16} fill /><span>Bấm đặt giữ: phòng được giữ cho bạn tới hết ngày <b>{dmy(tinh.han_tra_sau)}</b> — hôm nay chưa phải trả</span></div>
      : <div className="ksv-tmr"><Ico d={P.gio} s={16} /><span>Bấm thanh toán: phòng được giữ cho bạn <b>15 phút</b> để trả</span></div>}
    <button type="button" className="ksv-link" onClick={() => setBuoc("gui")}>← Sửa thông tin khách</button>
    <div className="ksv-co">
      <div className="ksv-col">
        <section className="ksv-panel ksv-sec0"><h3>Chọn cách thanh toán</h3>
          {tinh.han_tra_sau && <label className={`ksv-radio ${traSau ? "on" : ""}`}><input type="radio" name="ksv-cach2" checked={traSau} onChange={() => setCach("sau")} />
            <span><b>Đặt giữ, trả trước {dmy(tinh.han_tra_sau)}</b><span className="ksv-okc" style={{ display: "block" }}>✓ Hôm nay chưa phải trả{tinh.huy_mien_phi_den ? ` · ✓ Hủy miễn phí trước ${dmy(tinh.huy_mien_phi_den)}` : ""}</span></span></label>}
          <label className={`ksv-radio ${!traSau ? "on" : ""}`}><input type="radio" name="ksv-cach2" checked={!traSau} onChange={() => setCach("ngay")} />
            <span><b>Trả ngay</b><span className="ksv-muted" style={{ display: "block" }}>Thanh toán ngay để Vietourist chốt phòng với khách sạn sớm</span></span></label></section>
        {!traSau && <section className="ksv-panel ksv-sec0"><h3>Phương thức thanh toán <small className="ksv-muted" style={{ fontWeight: 400 }}><Ico d={P.khoa} s={13} /> mã hóa, bảo mật</small></h3>
          <label className={`ksv-radio ${tt === "qr" ? "on" : ""}`}><input type="radio" name="ksv-tt" checked={tt === "qr"} onChange={() => setTt("qr")} />
            <span style={{ flex: 1 }}><b>QR chuyển khoản ngân hàng</b><span className="ksv-muted" style={{ display: "block" }}>Mọi ngân hàng · ngân hàng báo về, đơn tự chuyển «Đã thanh toán» trong 1–3 phút</span></span><span className="ksv-b green">Không mất phí</span></label>
          {ks.the_bat && <label className={`ksv-radio ${tt === "the" ? "on" : ""}`}><input type="radio" name="ksv-tt" checked={tt === "the"} onChange={() => setTt("the")} />
            <span><b>Thẻ ATM nội địa / tín dụng / ghi nợ</b><span className="ksv-logos"><span>VISA</span><span>Mastercard</span><span>JCB</span><span>NAPAS</span></span>
              <span className="ksv-muted" style={{ display: "block", marginTop: 4 }}>Nhập thẻ trên trang bảo mật của cổng thanh toán SePay — Vietourist không thấy và không lưu số thẻ.</span></span></label>}</section>}
        {diem?.dang_bat && <section className="ksv-panel" style={{ padding: 18 }}><h3 className="ksv-h3">Mã voucher VTD Rewards</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input className="ksv-vc" value={vc.ma} onChange={(e) => setVc({ ma: e.target.value.toUpperCase(), ap: null, loi: "" })} placeholder="VTD-XXXXXX" aria-label="Mã voucher" />
            {vc.ap ? <button type="button" className="ksv-btn line" onClick={() => setVc({ ma: "", ap: null, loi: "" })}>Bỏ voucher</button>
              : <button type="button" className="ksv-btn line" disabled={busy} onClick={apVoucher}>Áp dụng</button>}</div>
          {vc.ap && <span className="ksv-okc">Đã áp {vc.ap.ma} · giảm ₫ {vnd(vc.ap.gia_tri)} (tối đa 5% đơn = ₫ {vnd(vc.ap.tran)})</span>}
          {vc.loi && <span className="ksv-loi" style={{ padding: "8px 12px" }}>{vc.loi}</span>}
          <small className="ksv-muted">Đổi điểm lấy voucher ở mục «Điểm VTD Rewards». Hủy đơn được hoàn tiền thì điểm của voucher trả lại.</small></section>}
        <small className="ksv-muted" style={{ padding: "0 4px" }}>✉ Xác nhận gửi tới {kh.email ? <><b>{kh.email}</b> và </> : ""}Zalo / điện thoại <b>{kh.lien_he}</b></small>
        {loiBox}
        <div className="ksv-panel" style={{ padding: 16 }}>
          <label className="ksv-chk" style={{ alignItems: "flex-start" }}><input type="checkbox" checked={kh.dongy} onChange={(e) => setKh({ ...kh, dongy: e.target.checked })} />
            <span style={{ fontSize: 13 }}>Tôi đã đọc và đồng ý chính sách hủy phòng của gói đã chọn và điều kiện đặt phòng của khách sạn và Vietourist.</span></label>
          {tinh.mo_thanh_toan === false ? <><button type="button" className="ksv-btn big wide ksv-khoa" disabled aria-disabled="true"><Ico d={P.khoa} s={16} /> Thanh toán trực tuyến sắp mở cho khách sạn này</button>
            <small className="ksv-muted" style={{ textAlign: "center" }}>Vietourist đang hoàn tất mở thanh toán cho khách sạn này. Chưa giữ phòng, chưa gửi đơn.</small></>
            : <button type="button" className="ksv-btn big wide" disabled={busy} onClick={datNgay}><Ico d={P.khoa} s={16} />{traSau ? " ĐẶT GIỮ PHÒNG — TRẢ SAU" : ` THANH TOÁN ₫ ${vnd(tinh.tong - giam)}`}</button>}
          {tinh.huy_mien_phi_den && <div className="ksv-okc" style={{ textAlign: "center", fontSize: 13 }}>Linh hoạt! Hủy miễn phí trước {dmy(tinh.huy_mien_phi_den)}</div>}</div>
      </div>
      {tomTat}
    </div></div>;

  if (buoc === "ks" && ks) {
    const anh: any[] = ks.anh || [], video: any[] = (ks.video || []).slice(0, 3);
    const traSauCo = (g: any) => traSauGoi(g, homNay);
    const hop = (g: any) => (!locP.includes("sang") || g.bua_sang) && (!locP.includes("huy") || g.mien_phi_huy) && (!locP.includes("sau") || traSauCo(g));
    const hetLoai = ks.phong.filter((p: any) => p.vua && p.goi.length && (p.con ?? 1) === 0).length;
    const phongHien = ks.phong.filter((p: any) => !locP.length || p.goi.some(hop));
    const chips: [string, string, boolean][] = [["sang", "Bữa sáng", ks.phong.some((p: any) => p.goi.some((g: any) => g.bua_sang))],
      ["huy", "Miễn phí hủy", ks.phong.some((p: any) => p.goi.some((g: any) => g.mien_phi_huy))], ["sau", "Đặt giữ, trả sau", ks.phong.some((p: any) => p.goi.some((g: any) => traSauCo(g)))]];
    const nhomDem = Object.entries(ks.nhom_anh || {}).map(([k, t]) => [k, t as string, anh.filter((a) => a.nhom === k).length] as const).filter((x) => x[2] > 0);
    const keo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    const dg = ks.danh_gia || {};
    return <div className="ksv">{css}{thanhTim("ks")}
      {album && <Album ks={ks} dau={album} onDong={() => setAlbum(null)} />}
      <button type="button" className="ksv-link" onClick={() => setBuoc("ds")}>← Khách sạn ở {ks.tinh_thanh}</button>
      <div className="ksv-gal">{anh.length || video.length ? <>
        {anh.slice(0, 7).map((a: any, i: number) => <button type="button" key={a.id} onClick={() => setAlbum({ nhom: "" })} aria-label={`Xem ảnh ${i + 1}`}>
          <img src={i ? a.nho : a.hien} alt={a.mo_ta_thay_the || a.chu_thich || `${ks.ten} — ${a.nhom_ten}`} loading={i ? "lazy" : undefined} />
          {i === 0 && <span className="ksv-see"><Ico d={P.may} s={15} />Xem tất cả ảnh</span>}
          {i === 1 && video.length > 0 && <span className="ksv-ct" onClick={(e) => { e.stopPropagation(); setAlbum({ nhom: "video" }); }}>▶ Video</span>}
          {i === Math.min(6, anh.length - 1) && i > 0 && <span className="ksv-see">{anh.length > 7 ? `+${anh.length - 7} ảnh` : `${anh.length} ảnh`}{video.length ? ` · ${video.length} video` : ""}</span>}</button>)}
        {!anh.length && video[0] && <span style={{ gridColumn: "1 / -1", gridRow: "1 / 3" }}><VideoO v={video[0]} ten={ks.ten} /></span>}</>
        : <span style={{ gridColumn: "1 / -1", gridRow: "1 / 3" }}><AnhTrong k={ks} cao={260} /></span>}</div>
      <nav className="ksv-sub">
        <div className="tb">{[["ksv-tq", "Tổng quan"], ["ksv-phong", "Phòng"], ["ksv-tn", "Tiện nghi"], ["ksv-dg", "Đánh giá"], ["ksv-vt", "Vị trí"], ["ksv-cs", "Chính sách"]].map(([id, t]) =>
          <a key={id} href={`#${id}`} onClick={(e) => { e.preventDefault(); keo(id); }}>{t}</a>)}</div>
        <span className="from">{ks.gia_tu && <><small className="ksv-muted">từ</small><b className="ksv-big" style={{ fontSize: 20 }}><small>₫</small>{vnd(ks.gia_tu.gia_dem)}</b></>}
          <button type="button" className="ksv-btn sm" onClick={() => keo("ksv-phong")}>XEM PHÒNG</button></span></nav>
      <div className="ksv-g2" id="ksv-tq">
        <div className="ksv-col">
          <div className="ksv-panel" style={{ padding: 18 }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{ks.gia_tu && <span className="ksv-b navy">Giá hợp đồng VTD</span>}{diem?.dang_bat && <span className="ksv-b purple">Tích điểm VTD</span>}
              {ks.loai_ten && <span className="ksv-b out">{ks.loai_ten}</span>}</div>
            <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}><h2 className="ksv-h1">{ks.ten}</h2>{ks.sao > 0 && <span className="ksv-stars" aria-label={`${ks.sao} sao`}>{"★".repeat(ks.sao)}</span>}</div>
            <span className="ksv-muted" style={{ fontSize: 13.5 }}>{[ks.dia_chi, ks.khu_vuc, ks.tinh_thanh].filter(Boolean).join(", ")} · <a className="ksv-link" href="#ksv-vt" onClick={(e) => { e.preventDefault(); keo("ksv-vt"); }}>XEM VỊ TRÍ</a></span></div>
          {(ks.noi_bat || ks.gan || ks.mo_ta || ks.co_mien_phi_huy || ks.co_bua_sang) && <div className="ksv-panel" style={{ padding: 18 }}><h2 className="ksv-h2">Điểm nổi bật</h2>
            {ks.noi_bat && <div className="ksv-hlr"><span className="ic"><Ico d={P.sao} s={20} fill /></span><div><b>{ks.noi_bat}</b></div></div>}
            {ks.gan && <div className="ksv-hlr"><span className="ic"><Ico d={P.ghim} s={20} fill /></span><div><b>Vị trí</b> — {ks.gan}{ks.km_trung_tam != null && <div className="ksv-muted">{phay(ks.km_trung_tam)} km tới trung tâm</div>}</div></div>}
            {(ks.co_mien_phi_huy || ks.co_bua_sang) && <div className="ksv-hlr"><span className="ic"><Ico d={P.khien} s={20} fill /></span><div><b>Đặt linh hoạt</b> — {[ks.co_mien_phi_huy && "có gói miễn phí hủy", ks.co_bua_sang && "có gói gồm bữa sáng"].filter(Boolean).join(", ")}
              <div className="ksv-muted">Giá hợp đồng của Vietourist, máy tính đúng ngày bạn chọn.</div></div></div>}
            {ks.mo_ta && <p style={{ margin: "8px 0 0", fontSize: 14.5, lineHeight: 1.65, whiteSpace: "pre-line", maxWidth: "72ch" }}>{ks.mo_ta}</p>}</div>}
          <div className="ksv-panel" id="ksv-tn" style={{ padding: 18 }}><h2 className="ksv-h2">Tiện nghi</h2>
            {ks.tien_ich.length ? <div className="ksv-facs">{ks.tien_ich.map((t: string) => <span key={t}><Ico d={P.dung} s={15} />{t}</span>)}</div> : <span className="ksv-muted">Đang cập nhật</span>}</div>
          {ks.dat_24h > 0 && <div className="ksv-hot"><b>Khách sạn đang được đặt nhiều!</b> Đã đặt {ks.dat_24h} lần trong 24 giờ qua.</div>}
        </div>
        <div className="ksv-col">
          <div className="ksv-panel" style={{ padding: 18 }}>
            {dg.diem_tb != null ? <><div style={{ display: "flex", alignItems: "center", gap: 10 }}><OD d={dg.diem_tb} lon /><div><b style={{ color: "var(--ksv-ink)", fontSize: 17 }}>{dg.nhan || nhan(dg.diem_tb)}</b>
              <div className="ksv-muted">{dg.so_bai} đánh giá của khách đã ở</div></div><a className="ksv-link" style={{ marginLeft: "auto", fontSize: 13 }} href="#ksv-dg" onClick={(e) => { e.preventDefault(); keo("ksv-dg"); }}>Xem tất cả</a></div>
              {Object.keys(dg.muc || {}).length > 0 && <div className="ksv-bars">{MUC_KS.filter(([k]) => dg.muc[k] != null).map(([k, t]) =>
                <div key={k}><span>{t} {phay(dg.muc[k])}</span><s><i style={{ width: `${Math.min(100, dg.muc[k] * 10)}%` }} /></s></div>)}</div>}</>
              : <TomTatDg dg={dg} />}</div>
          <div className="ksv-panel" id="ksv-vt" style={{ padding: 0, overflow: "hidden" }}>
            {ks.vi_do != null && ks.kinh_do != null ? <BanDoKs mot cao={190} ghim={[{ id: ks.id, vi_do: ks.vi_do, kinh_do: ks.kinh_do, nhan: ks.ten }]} chon={ks.id} />
              : <a className="ksv-map" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([ks.ten, ks.dia_chi, ks.tinh_thanh].filter(Boolean).join(", "))}`} target="_blank" rel="noopener noreferrer">
              <span><Ico d={P.ghim} s={30} fill /></span><b>XEM BẢN ĐỒ ↗</b></a>}
            <a className="ksv-btn line" style={{ margin: "10px 16px 0", display: "inline-flex", flexDirection: "row", gap: 6, alignItems: "center", justifyContent: "center" }} href={ggDuong(ks)} target="_blank" rel="noopener noreferrer"><Ico d={P.ghim} s={15} fill /> Chỉ đường trên Google Maps ↗</a>
            <div style={{ padding: "12px 16px", display: "flex", flexDirection: "column", gap: 4, fontSize: 13.5 }}><b>{[ks.khu_vuc, ks.tinh_thanh].filter(Boolean).join(", ")}</b>
              {ks.dia_chi && <span>{ks.dia_chi}</span>}{ks.km_trung_tam != null && <span>✓ {phay(ks.km_trung_tam)} km tới trung tâm</span>}{ks.gan && <span>✓ {ks.gan}</span>}</div></div>
        </div></div>
      {video.length > 1 && <DaiVideo video={video} ten={ks.ten} bo={1} />}
      <div id="ksv-phong" className="ksv-col" style={{ paddingBottom: soChon ? 90 : 16, scrollMarginTop: 70 }}>
        <div className="ksv-panel" style={{ padding: 16 }}>
          <div className="ksv-rhead"><h2 className="ksv-h1" style={{ fontSize: 20 }}>Chọn phòng</h2><span className="ksv-okc" style={{ fontWeight: 600 }}>✓ Giá hợp đồng Vietourist</span></div>
          <span className="ksv-muted">{ngay(ks.vao)} → {ngay(ks.ra)} · {ks.dem} đêm · {q.nl} người lớn{q.te ? ` · ${q.te} trẻ em` : ""} · {q.phong} phòng</span>
          {chips.some((c) => c[2]) && <><b style={{ fontSize: 14 }}>Lọc</b><div className="ksv-chips">{chips.filter((c) => c[2]).map(([k, t]) =>
            <button key={k} type="button" className={`ksv-chip ${locP.includes(k) ? "on" : ""}`} aria-pressed={locP.includes(k)} onClick={() => setLocP(locP.includes(k) ? locP.filter((x) => x !== k) : [...locP, k])}>{t}</button>)}</div></>}</div>
        {hetLoai > 0 && <div className="ksv-sold"><Ico d={P.gio} s={15} />Nhanh tay! {hetLoai} loại phòng đã hết cho ngày bạn chọn.</div>}
        {loiBox}
        {!ks.phong.length && <div className="ksv-panel">Khách sạn chưa nhập loại phòng. <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong()}>Gửi yêu cầu giữ phòng</button></div>}
        {locP.length > 0 && !phongHien.length && <div className="ksv-panel">Không có gói nào khớp bộ lọc. <button type="button" className="ksv-btn line" onClick={() => setLocP([])}>Xóa bộ lọc</button></div>}
        {phongHien.map((p: any, iP: number) => { const aP = anh.filter((a) => a.loai_phong_id === p.id); const rieng = p.anh?.[0] || aP[0];
          const anhP = rieng || anhTamPhong(anh, iP), tam = !rieng && !!anhP;
          return <div key={p.id} className="ksv-room">
          <div className="ksv-rl">
            <button type="button" className="ksv-rph" onClick={() => setAlbum(aP.length ? { lp: p.id } : { nhom: anh.some((a) => a.nhom === "phong") ? "phong" : "" })} aria-label={`Xem ảnh ${p.ten}`}>
              {anhP ? <img src={anhP.nho} alt={tam ? `${ks.ten} — ảnh khách sạn` : (anhP.mo_ta_thay_the || p.ten)} loading="lazy" /> : <AnhTrong k={ks} cao={150} />}
              {tam && <span className="ksv-ct ksv-tam">Ảnh khách sạn</span>}
              {(p.con ?? 9) > 0 && (p.con ?? 9) <= 3 && p.goi.length > 0 && <span className="ksv-b aw" style={{ background: "#fff", color: "var(--ksv-price)" }}>Còn {p.con} phòng!</span>}
              {aP.length > 0 && <span className="ksv-ct">1/{aP.length}</span>}</button>
            {p.video?.[0] && <div style={{ aspectRatio: "16 / 9", maxWidth: "100%" }}><VideoO v={p.video[0]} ten={p.ten} nhan="VIDEO PHÒNG" /></div>}
            <b className="ksv-rn">{p.ten}</b>
            <span className="ksv-spec">{[p.dien_tich ? `${p.dien_tich} m²` : "", `Tối đa ${p.toi_da_nguoi_lon} người lớn${p.toi_da_tre_em ? ` + ${p.toi_da_tre_em} trẻ em` : ""}`, p.giuong,
              p.giuong_phu_toi_da ? `kê được ${p.giuong_phu_toi_da} giường phụ` : ""].filter(Boolean).join(" · ")}</span>
            {p.mo_ta && <span className="ksv-muted" style={{ fontSize: 13 }}>{p.mo_ta}</span>}
            {(p.tien_nghi || []).length > 0 && <div className="ksv-amen">{p.tien_nghi.map((t: string) => <span key={t}>✓ {t}</span>)}</div>}
            {p.mo_ta_dai && <details><summary style={{ cursor: "pointer", fontSize: 13 }} className="ksv-link">Xem thêm</summary><p className="ksv-muted" style={{ fontSize: 13, whiteSpace: "pre-line", margin: "4px 0 0" }}>{p.mo_ta_dai}</p></details>}
            {!p.vua && <small style={{ color: "var(--ksv-price)", fontWeight: 600 }}>{p.ly_do || `Không đủ chỗ cho ${q.nl} người lớn / ${q.phong} phòng — tăng số phòng`}</small>}
            {!p.vua && /gửi yêu cầu/.test(p.ly_do || "") && <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong(p.ten)}>Gửi yêu cầu giữ phòng</button>}</div>
          <div className="ksv-rates">{p.goi.length ? p.goi.filter((g: any) => !locP.length || hop(g)).map((g: any) => { const ts = traSauCo(g), con = p.con ?? p.so_phong, tat = !p.vua || g.vua === false;
            return <div key={g.id} className="ksv-rr">
            {con > 0 && con <= 3 && !tat && <div className="deal"><Ico d={P.gio} s={14} />Còn {con} phòng giá này</div>}
            <div className="ben">
              <span><Ico d={P.nguoi} s={14} /> {p.toi_da_nguoi_lon} người lớn{p.toi_da_tre_em ? ` + ${p.toi_da_tre_em} trẻ em` : ""}</span>
              {g.bua_sang ? <span className="ksv-okc"><Ico d={P.coc} s={14} /> Bao gồm bữa sáng</span> : <span>Chỉ phòng</span>}
              {["chỉ phòng", "có bữa sáng", "bữa sáng"].includes(String(g.ten || "").trim().toLowerCase()) ? null : <span>{g.ten}</span>}
              {g.mien_phi_huy ? <span className="ksv-okc"><Ico d={P.khien} s={14} fill /> Miễn phí hủy trước {g.huy_gio_chot ? `${g.huy_gio_chot} ` : ""}{dmy(g.huy_han)}{g.huy_gio_chot && g.huy_mui_gio ? ` (${g.huy_mui_gio})` : ""}</span> : <span className="ksv-muted">Không hoàn tiền</span>}
              {ts ? <span className="ksv-okc">✓ Đặt giữ, trả trước {dmy(ts)}</span> : <span className="ksv-muted">Trả ngay khi đặt</span>}
              {diem?.dang_bat && diem.cach_tinh !== "hoa_hong" && duKien(g.tong) > 0 && <span className="ksv-diem">✦ Tích khoảng {vnd(duKien(g.tong))} điểm VTD</span>}
              {g.vua !== false && (g.phu_thu_ct || []).filter((c: any) => c.tien > 0).map((c: any, j: number) => <span key={j} className="ksv-muted">{c.nhan}</span>)}
              {g.vua !== false && g.cho_xac_nhan && <span className="ksv-muted">Giường phụ chờ khách sạn xác nhận — không xếp được thì hoàn 100%</span>}</div>
            <div className="pc">{g.niem_yet_dem > g.gia_dem && <><span className="ksv-cheap">Giá tốt cho ngày này</span><span><span className="ksv-old">₫ {vnd(g.niem_yet_dem)}</span> <span className="ksv-pct">−{Math.round((1 - g.gia_dem / g.niem_yet_dem) * 100)}%</span></span></>}
              <b className="ksv-big"><small>₫</small>{vnd(g.gia_dem)}</b><small className="ksv-muted">Mỗi đêm, chưa gồm thuế phí</small>
              {ks.dem > 1 && <small className="ksv-muted">₫ {vnd(g.tong)} / {ks.dem} đêm</small>}
              {g.vua !== false && g.phu_thu_ky > 0 && <small style={{ fontWeight: 600 }}>+ trẻ em / giường phụ ₫ {vnd(g.phu_thu_ky)}</small>}
              {p.vua && g.vua === false && <small style={{ color: "var(--ksv-price)", fontWeight: 600 }}>{g.ly_do}</small>}</div>
            <div className="act">{con > 0 ? <>
              <select className="ksv-sel" aria-label={`Số phòng ${p.ten} ${g.ten}`} disabled={tat} value={chon[g.id] || 0}
                onChange={(e) => setChon({ ...chon, [g.id]: Number(e.target.value) })}>{Array.from({ length: Math.min(conCho(p, g.id), 9) + 1 }, (_, n) => <option key={n} value={n}>{n} phòng</option>)}</select>
              <button type="button" className={`ksv-btn ${chon[g.id] ? "" : "line"}`} disabled={tat || busy} onClick={() => sangGui({ ...chon, [g.id]: chon[g.id] || 1 })}>
                Đặt ngay{ts && <small style={{ display: "block", fontWeight: 500, fontSize: 12 }}>Trả sau</small>}</button>
              {ts && !tat && <span className="ksv-okc" style={{ fontSize: 12.5, fontWeight: 600 }}>Hôm nay chưa trả</span>}</>
              : <b style={{ color: "var(--ksv-price)" }}>Hết phòng</b>}</div>
          </div>; }) : <div style={{ padding: 16, display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
              <span style={{ flex: 1, minWidth: 200 }}><b>Giá {ngay(ks.vao)} – {ngay(ks.ra)} đang cập nhật</b><br /><span className="ksv-muted">Gửi yêu cầu, Vietourist báo giá và giữ phòng cho bạn.</span></span>
              <button type="button" className="ksv-btn line" onClick={() => moYeuCauTrong(p.ten)}>Gửi yêu cầu giữ phòng</button></div>}</div></div>; })}
      </div>
      <div className="ksv-panel" id="ksv-cs" style={{ padding: 18 }}><h2 className="ksv-h2">Chính sách chỗ ở</h2>
        <span><b>Nhận phòng</b> từ {ks.gio_nhan} · <b>Trả phòng</b> trước {ks.gio_tra}</span>
        {ks.chinh_sach.tre ? <span><b>Trẻ em &amp; giường phụ</b>{ks.chinh_sach.tre.dong.map((d: string, i: number) => <span key={i} style={{ display: "block" }}>{d}</span>)}</span>
          : <>{ks.chinh_sach.tre_em && <span><b>Trẻ em</b> {ks.chinh_sach.tre_em}</span>}{ks.chinh_sach.giuong_phu && <span><b>Giường phụ</b> {ks.chinh_sach.giuong_phu}</span>}</>}
        {ks.chinh_sach.vat_nuoi && <span><b>Vật nuôi</b> {ks.chinh_sach.vat_nuoi}</span>}{ks.chinh_sach.khac && <span style={{ whiteSpace: "pre-line" }}>{ks.chinh_sach.khac}</span>}
        <span><b>Hủy phòng</b> theo từng gói giá đã chọn. <b>Đặt giữ, trả sau</b>: chỉ gói miễn phí hủy; quá hạn trả chưa trả thì đơn tự hủy, không mất phí.</span></div>
      <DanhGiaKsCong kid={ks.id} />
      {nhomDem.length > 0 && <span className="ksv-muted" style={{ fontSize: 12 }}>Ảnh: {nhomDem.map(([, t, n]) => `${t} ${n}`).join(" · ")}</span>}
      {soChon > 0 && <div className="ksv-total"><span style={{ flex: 1, minWidth: 180 }}><b>{soChon} phòng · {ks.dem} đêm</b><br /><small className="ksv-muted">{dongChon.map((x: any) => `${x.n} × ${x.p.ten} (${x.g.ten})`).join(" · ")}</small></span>
        <span style={{ textAlign: "right" }}><b className="ksv-big" style={{ fontSize: 22 }}>₫ {vnd(tienChon)}</b><br /><small className="ksv-muted">+ thuế phí ₫ {vnd(tienChon * (ks.thue_phi_pt || 0) / 100)}</small>
          {dongChon.some((x: any) => x.g.phu_thu_ky > 0) && <><br /><small className="ksv-muted">+ trẻ em / giường phụ (máy tính lại ở bước sau)</small></>}</span>
        <button type="button" className="ksv-btn big" disabled={busy} onClick={() => sangGui()}>Đặt ngay</button></div>}
    </div>;
  }

  if (!daTim) return <div className="ksv">{css}
    <div className="ksv-hero"><div className="ksv-hero-in">
      <h1>Khách sạn hợp tác Vietourist · Giá hợp đồng{ds.diem?.dang_bat ? " · Tích điểm VTD" : ""}</h1>
      <form className="ksv-sbox2" onSubmit={(e) => { e.preventDefault(); setPop(false); tim(q, true); }}>
        <div className="ksv-stabs"><span className="on"><Ico d={P.giuong} s={16} />Khách sạn</span></div>
        <div className="ksv-sbody">
          <label className="ksv-fl"><Ico d={P.kinh} s={22} /><span style={{ flex: 1, minWidth: 0 }}><small>Điểm đến</small>{chonTp}</span></label>
          <div className="ksv-fl2"><label className="ksv-fl"><Ico d={P.lich} s={22} /><span><small>Nhận phòng · {thuDai(q.vao)}</small>{oVao}</span></label>
            <label className="ksv-fl"><Ico d={P.lich} s={22} /><span><small>Trả phòng · {thuDai(q.ra)} · {dem} đêm</small>{oRa}</span></label></div>
          <div className="ksv-fl" style={{ position: "relative" }}><Ico d={P.nguoi} s={22} /><button type="button" className="ksv-khach" onClick={() => setPop(!pop)} aria-expanded={pop}>
            <small>{q.phong} phòng</small><b>{khachTxt}</b></button>{khachPop}</div>
          <label className="ksv-chk"><input type="checkbox" checked={chiDat} onChange={(e) => setChiDat(e.target.checked)} /><span>Chỉ hiện khách sạn đặt ngay được trên Vietourist</span></label>
        </div>
        <div className="ksv-sgo"><button className="ksv-btn big" type="submit" disabled={busy}>TÌM</button></div></form></div></div>
    {loiBox}
    {dsDiemDen}
    <div className="ksv-promo">
      <div className="ksv-panel"><b>Giá hợp đồng Vietourist</b><span className="ksv-muted">{(ds.thanh_pho || []).reduce((a: number, t: any) => a + t.so, 0)} khách sạn hợp tác ở {(ds.thanh_pho || []).length} điểm đến</span></div>
      <div className="ksv-panel"><b>Đặt giữ, trả sau</b><span className="ksv-muted">Gói miễn phí hủy: hôm nay chưa phải trả, trả trước hạn bằng QR hoặc thẻ</span></div>
      {ds.diem?.dang_bat ? <div className="ksv-panel"><b>Hội viên {ds.diem.hang}</b><span className="ksv-muted">Hệ số điểm ×{phay(ds.diem.he_so)} cho mỗi kỳ ở qua Vietourist</span></div>
        : <div className="ksv-panel"><b>Thanh toán an toàn</b><span className="ksv-muted">QR chuyển khoản máy tự khớp, hoặc thẻ qua cổng SePay — Vietourist không lưu số thẻ</span></div>}</div>
    <PhongCuaToi gon lamMoi={lamMoi} onMo={moDon} />
  </div>;

  const L = loc;
  const ck = (on: boolean, doi: (v: boolean) => void, nd: any, so?: number, key?: string) => <label key={key} className="ksv-chk"><input type="checkbox" checked={on} onChange={(e) => doi(e.target.checked)} /><span>{nd}</span>{so != null && <small>{so}</small>}</label>;
  const bat = (arr: string[], v: string, on: boolean) => (on ? [...arr, v] : arr.filter((x) => x !== v));
  // KS-16s: nhóm lọc kiểu Agoda — chỉ hiện lựa chọn có ít nhất một khách sạn (số đếm thật)
  const nhomLoc = (tieuDe: string, ds_: [string, string, (k: any) => boolean][], khoa: "tt" | "an" | "kc" | "gi") => {
    const co = ds_.filter(([, , f]) => dem2(f) > 0);
    return co.length > 0 && <div className="fsec"><h4>{tieuDe}</h4>{co.map(([m, t, f]) => ck(L[khoa].includes(m), (v) => setLoc({ ...L, [khoa]: bat(L[khoa], m, v) }), t, dem2(f), `${khoa}${m}`))}</div>;
  };
  const goiY = Array.from(new Set(trongTp.flatMap((k: any) => [k.ten, k.khu_vuc].filter(Boolean)))) as string[];
  // KS-16s: bản đồ — ghim mọi khách sạn khớp bộ lọc có tọa độ; «Tìm khi di chuyển bản đồ» lọc danh sách theo vùng đang xem
  const coToaDo = (k: any) => k.vi_do != null && k.kinh_do != null;
  const ghim = loc2.filter(coToaDo).map((k: any) => ({ id: k.id, vi_do: k.vi_do, kinh_do: k.kinh_do, nhan: giaGon(k.gia_tu?.gia_dem) }));
  const trongKhung = (k: any) => !khung || !coToaDo(k) || (k.vi_do >= khung.s && k.vi_do <= khung.n && k.kinh_do >= khung.w && k.kinh_do <= khung.e);
  const dsHien = banDo && theoKhung ? loc2.filter((k: any) => coToaDo(k) && trongKhung(k)) : loc2;
  const khongViTri = loc2.filter((k: any) => !coToaDo(k)).length;
  return <div className="ksv">{css}{thanhTim("ds")}
    <PhongCuaToi gon lamMoi={lamMoi} onMo={moDon} />
    {ds.diem?.dang_bat && <div className="ksv-coupon"><Ico d={P.the} s={30} fill /><div><b style={{ fontSize: 15 }}>Hội viên {ds.diem.hang} · điểm ×{phay(ds.diem.he_so)}</b>
      <div style={{ fontSize: 13 }}>Mỗi kỳ ở qua Vietourist được tích điểm VTD Rewards. Có voucher? Áp ở bước cuối khi đặt phòng.</div></div></div>}
    {!q.tinh && dsDiemDen}
    <div className="ksv-layout">
      <aside className={`ksv-loc ${moLoc ? "open" : ""}`} aria-label="Bộ lọc">
        {moLoc && <div className="ksv-rhead"><b style={{ fontSize: 20 }}>Bộ lọc</b><button type="button" className="ksv-btn" onClick={() => setMoLoc(false)}>Xem {loc2.length} kết quả</button></div>}
        <div className="ksv-panel ksv-fbox">
          <div className="fsec"><label className="ksv-pill"><Ico d={P.kinh} s={18} /><input placeholder="Tên khách sạn hoặc khu vực" value={L.ten} list="ksv-goi-y" onChange={(e) => setLoc({ ...L, ten: e.target.value })} aria-label="Tìm theo tên khách sạn hoặc khu vực" /></label>
            <datalist id="ksv-goi-y">{goiY.map((t) => <option key={t} value={t} />)}</datalist></div>
          <div className="fsec"><h4>Ngân sách mỗi đêm</h4>
            <div className="ksv-mm"><label>TỐI THIỂU<input inputMode="numeric" value={`₫ ${vnd(L.min)}`} onChange={(e) => setLoc({ ...L, min: Number(e.target.value.replace(/\D/g, "")) || 0 })} /></label>
              <label>TỐI ĐA<input inputMode="numeric" value={`₫ ${vnd(L.max || giaMax)}`} onChange={(e) => setLoc({ ...L, max: Number(e.target.value.replace(/\D/g, "")) || 0 })} /></label></div>
            <input type="range" min={0} max={giaMax} step={50000} value={L.max || giaMax} onChange={(e) => setLoc({ ...L, max: Number(e.target.value) })} aria-label="Giá tối đa mỗi đêm" /></div>
          <div className="fsec"><h4>Lọc phổ biến{q.tinh ? ` ở ${q.tinh}` : ""}</h4>
            {([["coGia", "Có giá đặt ngay", (k: any) => !!k.gia_tu], ["huy", "Miễn phí hủy", (k: any) => k.co_mien_phi_huy], ["sang", "Bao gồm bữa sáng", (k: any) => k.co_bua_sang],
              ["diem9", "Khách chấm 9+ Xuất sắc", (k: any) => (k.danh_gia?.diem_tb || 0) >= 9], ["conPhong", "Chỉ hiện nơi còn phòng", (k: any) => !k.het_phong]] as const).map(([k, t, f]) =>
              ck(L[k], (v) => setLoc({ ...L, [k]: v }), t, dem2(f), k))}</div>
          {nhomLoc("Cách thanh toán", LOC_TT, "tt")}
          {[9, 8, 7].some((d) => dem2((k) => (k.danh_gia?.diem_tb || 0) >= d)) && <div className="fsec"><h4>Điểm khách đánh giá</h4>{([[9, "9+ Xuất sắc"], [8, "8+ Rất tốt"], [7, "7+ Tốt"]] as const).map(([d, t]) =>
            ck(L.dk === d, (v) => setLoc({ ...L, dk: v ? d : 0 }), t, dem2((k) => (k.danh_gia?.diem_tb || 0) >= d), `dk${d}`))}</div>}
          {nhomLoc("Bữa ăn & ưu đãi", LOC_AN, "an")}
          {nhomLoc("Khoảng cách tới trung tâm", LOC_KC, "kc")}
          {nhomLoc("Phòng & giường", LOC_GI, "gi")}
          {[5, 4, 3, 2, 1].some((s) => dem2((k) => k.sao === s)) && <div className="fsec"><h4>Hạng sao</h4>{[5, 4, 3, 2, 1].filter((s) => dem2((k) => k.sao === s)).map((s) =>
            ck(L.sao.includes(s), (v) => setLoc({ ...L, sao: v ? [...L.sao, s] : L.sao.filter((x) => x !== s) }), <span className="ksv-stars">{"★".repeat(s)}</span>, dem2((k) => k.sao === s), `s${s}`))}</div>}
          {khuDs.length > 1 && <div className="fsec"><h4>Khu vực</h4>{khuDs.map((t) => ck(L.khu.includes(t), (v) => setLoc({ ...L, khu: bat(L.khu, t, v) }), t, dem2((k) => k.khu_vuc === t), t))}</div>}
          {Object.keys(ds.loai || {}).some((k) => dem2((x) => x.loai === k)) && <div className="fsec"><h4>Loại chỗ ở</h4>{Object.entries(ds.loai || {}).filter(([k]) => dem2((x) => x.loai === k)).map(([k, t]: any) =>
            ck(L.loai.includes(k), (v) => setLoc({ ...L, loai: bat(L.loai, k, v) }), t, dem2((x) => x.loai === k), k))}</div>}
          {tiDs.length > 0 && <div className="fsec"><h4>Tiện nghi</h4>{tiDs.slice(0, 8).map((t) => ck(L.ti.includes(t), (v) => setLoc({ ...L, ti: bat(L.ti, t, v) }), t, dem2((k) => (k.tien_ich || []).includes(t)), t))}</div>}
          <div className="fsec"><button type="button" className="ksv-btn line wide" onClick={() => setLoc(LOC0)}>Xóa bộ lọc</button></div></div>
      </aside>
      <main className="ksv-col" style={{ minWidth: 0 }}>
        <div className="ksv-rhead"><h2 className="ksv-h1" style={{ fontSize: 20 }}>{loc2.length} chỗ ở{q.tinh ? ` tại ${q.tinh}` : ""}</h2>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><button type="button" className="ksv-btn line ksv-fbtn" onClick={() => setMoLoc(true)}>Bộ lọc</button>
            <button type="button" className={`ksv-btn ${banDo ? "" : "line"}`} style={{ display: "inline-flex", flexDirection: "row", gap: 6, alignItems: "center" }} aria-pressed={banDo} onClick={() => { setBanDo(!banDo); setKhung(null); }}><Ico d={P.ghim} s={15} fill /> {banDo ? "Danh sách" : "Xem trên bản đồ"}</button>
            <select className="ksv-sel" value={sx} onChange={(e) => setSx(e.target.value)} aria-label="Sắp xếp">
              {[["phu_hop", "Phù hợp nhất"], ["gia_thap", "Giá thấp nhất trước"], ["gia_cao", "Giá cao nhất trước"], ["diem", "Điểm khách cao nhất"], ["uu_dai", "Ưu đãi nhiều nhất"], ["sao", "Hạng sao"], ["gan", "Gần trung tâm nhất"]].map(([k, t]) =>
                <option key={k} value={k}>Sắp xếp: {t}</option>)}</select></div></div>
        {loiBox}
        {!loc2.length && <div className="ksv-panel" style={{ textAlign: "center" }}><b>{trongTp.length ? "Không có chỗ ở khớp bộ lọc." : "Vietourist đang bổ sung khách sạn hợp tác ở đây."}</b>
          {trongTp.length > 0 && <button type="button" className="ksv-btn line" onClick={() => { setLoc(LOC0); setChiDat(false); }}>Xóa bộ lọc</button>}</div>}
        {banDo && <div className="ksv-mapbox">
          <div className="ksv-mapbar"><label className="ksv-chk"><input type="checkbox" checked={theoKhung} onChange={(e) => setTheoKhung(e.target.checked)} /><span>Tìm khi di chuyển bản đồ</span></label>
            <small className="ksv-muted">{ghim.length} khách sạn trên bản đồ{khongViTri ? ` · ${khongViTri} chưa có vị trí trên bản đồ` : ""}</small></div>
          <BanDoKs ghim={ghim} chon={ghimChon} cao="min(62vh, 560px)" onKhung={setKhung}
            onChon={(id) => { setGhimChon(id); document.getElementById(`ksv-the-${id}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }} /></div>}
        {banDo && theoKhung && !dsHien.length && <div className="ksv-panel" style={{ textAlign: "center" }}>Không có khách sạn trong vùng bản đồ đang xem — kéo hoặc thu nhỏ bản đồ.</div>}
        {dsHien.map((k: any) => { const i = (anhI[k.id] || 0) % Math.max(1, k.anh.length), a = k.anh[i], g = k.gia_tu;
          return <article key={k.id} id={`ksv-the-${k.id}`} className={`ksv-card ${ghimChon === k.id ? "ksv-card-on" : ""}`} onMouseEnter={() => banDo && setGhimChon(k.id)}>
            {g && <div className="ksv-banner"><b>Giá hợp đồng Vietourist</b>{diem?.dang_bat ? " — tích điểm VTD sau kỳ ở" : ""}{k.co_mien_phi_huy ? " · có gói miễn phí hủy" : ""}</div>}
            <div className="ksv-crow">
              <div className="ksv-ph">{a ? <button type="button" className="ksv-phbtn" onClick={() => moThe(k)} aria-label={`Xem ${k.ten}`}><img src={a.nho} alt={a.mo_ta_thay_the || a.chu_thich || k.ten} loading="lazy" /></button>
                : <button type="button" className="ksv-phbtn" onClick={() => moThe(k)} aria-label={`Xem ${k.ten}`}><AnhTrong k={k} /></button>}
                {(k.danh_gia?.diem_tb || 0) >= 9 && <span className="ksv-b navy aw"><Ico d={P.sao} s={12} fill /> Khách chấm 9+</span>}
                <button type="button" className={`ksv-ico ksv-heart ${thich[k.id] ? "on" : ""}`} aria-label={thich[k.id] ? "Bỏ yêu thích" : "Lưu vào yêu thích"} aria-pressed={!!thich[k.id]} onClick={() => setThich({ ...thich, [k.id]: !thich[k.id] })}><Ico d={P.tim} s={20} /></button>
                {k.anh.length > 1 && <><button type="button" className="ksv-ico ksv-prv" aria-label="Ảnh trước" onClick={() => setAnhI({ ...anhI, [k.id]: (i - 1 + k.anh.length) % k.anh.length })}><Ico d={P.trai} /></button>
                  <button type="button" className="ksv-ico ksv-nxt" aria-label="Ảnh tiếp" onClick={() => setAnhI({ ...anhI, [k.id]: (i + 1) % k.anh.length })}><Ico d={P.phai} /></button></>}
                {k.so_anh > 0 && <span className="ksv-ct">{i + 1}/{k.so_anh}</span>}</div>
              <div className="ksv-info"><h3><button type="button" className="ksv-ten" onClick={() => moThe(k)}>{k.ten}</button></h3>
                {k.sao > 0 && <span className="ksv-stars" aria-label={`${k.sao} sao`}>{"★".repeat(k.sao)}</span>}
                <span className="ksv-where"><Ico d={P.ghim} s={14} fill />{[k.khu_vuc, k.tinh_thanh].filter(Boolean).join(", ")}{k.km_trung_tam != null ? ` · ${phay(k.km_trung_tam)} km tới trung tâm` : ""}</span>
                {k.gan && <span className="ksv-near">{k.gan}</span>}
                {banDo && !coToaDo(k) && <small className="ksv-muted">Chưa có vị trí trên bản đồ</small>}
                {(k.con_it > 0 || k.dat_24h > 0) && <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
                  {k.con_it > 0 && <span className="ksv-b" style={{ background: "var(--ksv-price)", color: "#fff" }}>Chỉ còn {k.con_it} phòng</span>}
                  {k.dat_24h > 0 && <span style={{ color: "var(--ksv-price)", fontSize: 12.5, fontWeight: 600 }}>Đã đặt {k.dat_24h} lần trong 24 giờ qua</span>}</div>}
                {k.tien_ich.length > 0 && <div className="ksv-feat sm">{k.tien_ich.slice(0, 4).map((t: string) => <span key={t}>{t}</span>)}</div>}
                {k.noi_bat && <span className="ksv-hl"><Ico d={P.sao} s={14} fill /> {k.noi_bat}</span>}</div>
              <div className="ksv-side">
                {k.danh_gia?.diem_tb ? <span className="ksv-score"><span><b>{k.danh_gia.nhan || nhan(k.danh_gia.diem_tb)}</b><small className="ksv-muted">{k.danh_gia.so_bai} đánh giá</small></span><b>{phay(k.danh_gia.diem_tb)}</b></span>
                  : <small className="ksv-muted">{k.danh_gia?.so_bai ? "Mới — chưa đủ đánh giá" : "Chưa có đánh giá"}</small>}
                {g ? <div className="ksv-pblk">
                  {g.niem_yet_dem > g.gia_dem && <><span className="ksv-vp">↓ Giá tốt</span><span><span className="ksv-old">{vnd(g.niem_yet_dem)}</span> <span className="ksv-pct">−{Math.round((1 - g.gia_dem / g.niem_yet_dem) * 100)}%</span></span></>}
                  <span className="ksv-big"><small>₫</small>{vnd(g.gia_dem)}</span><small className="ksv-muted">Mỗi đêm, chưa gồm thuế phí</small>
                  {k.co_mien_phi_huy && <span className="ksv-free">+ MIỄN PHÍ HỦY</span>}
                  {duKien(g.gia_dem * dem * q.phong) > 0 && <span className="ksv-diem">+ khoảng {vnd(duKien(g.gia_dem * dem * q.phong))} điểm sau kỳ ở</span>}
                  <button type="button" className="ksv-btn wide" onClick={() => moThe(k)}>Chọn phòng</button></div>
                  : k.het_phong ? <div className="ksv-pblk"><span className="ksv-hetb">Hết phòng ngày bạn chọn</span><small className="ksv-muted">Đổi ngày để xem phòng trống</small>
                    <button type="button" className="ksv-btn line wide" onClick={() => moThe(k)}>Xem khách sạn</button></div>
                  : k.dat_ngay === false ? <div className="ksv-pblk"><b>Chưa mở đặt trực tuyến</b><small className="ksv-muted">Xem khách sạn · gửi yêu cầu giữ phòng</small>
                    <button type="button" className="ksv-btn line wide" onClick={() => moThe(k)}>{rieng ? "Xem khách sạn" : "Xem khách sạn ↗"}</button></div>
                  : <div className="ksv-pblk"><b>Giá đang cập nhật</b><small className="ksv-muted">Vietourist báo giá trong giờ làm việc</small>
                    <button type="button" className="ksv-btn line wide" onClick={() => moThe(k)}>Xem và gửi yêu cầu</button></div>}</div>
            </div></article>; })}
      </main></div></div>;
}

/** Quyền lợi miễn phí ở bước thông tin khách — chỉ những gì gói đã chọn thật sự có. */
function QuyenLoi({ tinh, traSau, diemDk, hang }: { tinh: any; traSau: boolean; diemDk: number; hang?: any }) {
  const sang = tinh.dong.some((x: any) => x.bua_sang);
  const muc: [string, string, string, string][] = [];
  if (sang) muc.push([P.coc, "Bữa sáng", "Bữa sáng đã gồm trong giá phòng của gói đã chọn.", "MIỄN PHÍ"]);
  if (tinh.huy_mien_phi_den) muc.push([P.lich, "Hoàn tiền đầy đủ", `Hủy miễn phí trước ${dmy(tinh.huy_mien_phi_den)}`, "MIỄN PHÍ"]);
  if (traSau) muc.push([P.khoa, "Chưa trả hôm nay", `Trả trước ${dmy(tinh.han_tra_sau)} bằng QR hoặc thẻ`, "MIỄN PHÍ"]);
  muc.push([P.khien, "Phí đặt phòng", "Vietourist không thu phí đặt phòng", "MIỄN PHÍ"]);
  if (diemDk > 0) muc.push([P.qua, "Điểm VTD", `Khoảng ${vnd(diemDk)} điểm sau kỳ ở${hang?.hang ? ` (hạng ${hang.hang} ×${phay(hang.he_so)})` : ""}`, "THƯỞNG"]);
  return <section className="ksv-panel" style={{ padding: 18 }}><h3 className="ksv-h3" style={{ color: "var(--ksv-ok)" }}>Quyền lợi miễn phí</h3>
    {muc.map(([d, t, m, n]) => <div key={t} className="ksv-ben"><span className="bi"><Ico d={d} s={20} /></span><div><b>{t}</b><small>{m}</small></div>
      <span className="fr" style={n === "THƯỞNG" ? { background: "var(--ksv-purple)" } : undefined}>{n}</span></div>)}</section>;
}

/* ── KS-14 · trả tiền, trang đơn, phòng đã đặt ─────────────────────────────────────────────────── */
const ngayGio = (s?: string | null) => { if (!s) return ""; const d = new Date(s); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")} ${d.getDate()}/${d.getMonth() + 1}`; };
const MAU_TT: Record<string, string> = { cho_tra: "ksv-tt-cho", het_han: "ksv-tt-xam", da_tra: "ksv-tt-xanh", da_xac_nhan: "ksv-tt-ok", da_huy: "ksv-tt-xam" };

/** KS-16s: «Thêm vào lịch» — tệp .ics tạo ngay trên máy khách (nhận phòng → trả phòng, cả ngày). */
function themLich(d: any) {
  const k = d.khach_san || {}, ng = (x: string) => String(x).slice(0, 10).replace(/-/g, "");
  const thoat = (x: string) => String(x || "").replace(/[\\;,]/g, (c) => `\\${c}`).replace(/\n/g, "\\n");
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Vietourist//VTOS//VI", "BEGIN:VEVENT", `UID:${d.ma}@vietourist.vn`,
    `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").slice(0, 15)}Z`, `DTSTART;VALUE=DATE:${ng(d.vao)}`, `DTEND;VALUE=DATE:${ng(d.ra)}`,
    `SUMMARY:${thoat(`${k.ten || "Khách sạn"} · đơn ${d.ma}`)}`, `LOCATION:${thoat([k.dia_chi, k.tinh_thanh].filter(Boolean).join(", "))}`,
    `DESCRIPTION:${thoat(`Nhận phòng từ ${k.gio_nhan || "14:00"}, trả phòng trước ${k.gio_tra || "12:00"}.${d.ma_xac_nhan_ks ? ` Mã xác nhận khách sạn: ${d.ma_xac_nhan_ks}.` : ""}`)}`,
    "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = `${d.ma}.ics`; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function TomTatDon({ d }: { d: any }) {
  const k = d.khach_san || {};
  return <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
    <div className="ksv-panel" style={{ gap: 6 }}><b style={{ fontSize: 16 }}>{k.ten}</b>
      {k.sao > 0 && <span className="ksv-stars" style={{ fontSize: 13 }}>{"★".repeat(k.sao)}</span>}
      <span className="ksv-muted">{ngay(d.vao)} → {ngay(d.ra)} · {d.dem} đêm · {d.nguoi_lon} người lớn{d.tre_em ? ` · ${d.tre_em} trẻ em` : ""}</span>
      {d.gio_den && <span className="ksv-muted">Giờ đến dự kiến: <b>{d.gio_den}</b></span>}
      {["da_tra", "da_xac_nhan"].includes(d.trang_thai) || d.cach_tra === "sau" ? <button type="button" className="ksv-btn line" onClick={() => themLich(d)}><Ico d={P.lich} s={15} /> Thêm vào lịch</button> : null}
      {d.dong.map((x: any, i: number) => <span key={i}><b>{x.so} × {x.loai_phong}</b> · {x.goi}<br />{x.huy_han ? <span className="ksv-okc">✓ Miễn phí hủy trước {x.huy_han.split("-").reverse().join("/")}</span> : <span className="ksv-muted">Không hoàn tiền</span>}</span>)}
      <span className="ksv-sum"><span>Giá phòng</span><span>₫ {vnd(d.tien_phong)}</span></span>
      <span className="ksv-sum"><span>Thuế và phí{k.thue_phi_pt ? ` (${k.thue_phi_pt}%)` : ""}</span><span>₫ {vnd(d.thue_phi)}</span></span>
      {d.giam_voucher > 0 && <span className="ksv-sum ksv-okc"><span>Voucher {d.voucher?.ma}{d.voucher?.trang_thai === "da_hoan" ? " · đã trả điểm" : ""}</span><span>− ₫ {vnd(d.giam_voucher)}</span></span>}
      <span className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 10, alignItems: "baseline" }}><b style={{ fontSize: 16 }}>{d.giam_voucher > 0 ? "Bạn trả" : "Tổng"}</b><b className="ksv-big" style={{ fontSize: 22 }}>₫ {vnd(d.tong)}</b></span>
      {d.da_tra > 0 && <span className="ksv-sum"><span>Đã trả</span><b>₫ {vnd(d.da_tra)}</b></span>}
      {d.cach_tra === "sau" && d.trang_thai === "cho_tra" && <span className="ksv-okc" style={{ fontSize: 13 }}>Hôm nay ₫ 0 · Hạn trả {dmy(d.han_tra)}</span>}</div></aside>;
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
  const sau = d.cach_tra === "sau";
  return <>
    <Buoc3 toi={2} />
    {sau ? <div className="ksv-tmr" style={{ background: "var(--ksv-oksoft)", color: "var(--ksv-ok)" }}><span>Phòng được giữ cho bạn tới hết ngày <b>{dmy(d.han_tra)}</b> — trả trước hạn để Vietourist chốt phòng</span></div>
      : <div className="ksv-tmr">{con > 0 ? <><span>Phòng được giữ cho bạn trong</span><b>{mm}</b></> : <b>Hết giờ giữ phòng</b>}</div>}
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
  const giu = d.cach_tra === "sau" && d.trang_thai === "cho_tra";   // KS-16p: đặt giữ, trả sau — chưa trả
  const tot = ["da_tra", "da_xac_nhan"].includes(d.trang_thai) || giu;
  return <><Buoc3 toi={tot ? 3 : 2} />
    {tot && <div className="ksv-done"><span className="ck2"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" aria-hidden="true"><path d="M5 13l4 4L19 7" /></svg></span>
      <div><div className="ksv-h1" style={{ color: "var(--ksv-ok)" }}>{giu ? "Đã giữ phòng cho bạn!" : d.trang_thai === "da_xac_nhan" ? "Đặt phòng thành công!" : "Đã nhận thanh toán!"}</div>
        <div style={{ fontSize: 15, marginTop: 4 }}>Mã đơn <b>{d.ma}</b>{d.email ? <> · Xác nhận gửi tới {d.email}</> : ""}</div></div></div>}
    <div className="ksv-co">
    <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
      {msg && <div className="ksv-ok" style={{ padding: "10px 14px" }}>{msg}</div>}
      {loi && <div className="ksv-loi">{loi}</div>}
      {giu && <section className="ksv-panel" style={{ padding: 20 }}><h2 className="ksv-h2">Trả trước {dmy(d.han_tra)} để giữ chỗ</h2>
        <span className="ksv-muted">Trả ngay bây giờ cũng được — Vietourist chốt phòng với khách sạn trong 2 giờ làm việc sau khi nhận tiền.</span>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{d.co_the_tra && <button type="button" className="ksv-btn" onClick={onTra}>Trả ngay ₫ {vnd(d.con_phai_tra)} (QR / thẻ)</button>}</div>
        <b style={{ marginTop: 6 }}>Tiếp theo</b>
        <ol style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4, fontSize: 14 }}>
          <li>Vietourist nhắc hạn trả qua email trước 3 ngày và 1 ngày (nếu bạn đã ghi email).</li>
          <li>Trả xong, Vietourist chốt phòng với khách sạn trong 2 giờ làm việc và gửi mã xác nhận của khách sạn.</li>
          <li>Quá {dmy(d.han_tra)} chưa trả: đơn tự hủy, nhả phòng, không mất phí.</li></ol></section>}
      <section className="ksv-panel" style={{ padding: 22 }}>
        <span className={`ksv-tt ${MAU_TT[d.trang_thai] || ""}`}>{d.trang_thai === "da_tra" ? `✓ Đã thanh toán ₫ ${vnd(d.da_tra)}` : d.trang_thai_ten}</span>
        <h2 style={{ margin: 0, fontSize: 22 }}>{d.trang_thai === "da_xac_nhan" ? "Đặt phòng thành công" : d.trang_thai === "da_tra" ? "Đang chốt phòng với khách sạn"
          : d.trang_thai === "da_huy" ? "Đơn đã hủy" : d.trang_thai === "het_han" ? (d.cach_tra === "sau" ? "Quá hạn trả — đơn đã tự hủy" : "Hết giờ giữ phòng") : giu ? `Đặt giữ — trả trước ${dmy(d.han_tra)}` : "Chờ thanh toán"}</h2>
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
        {d.co_the_tra && !giu && <button type="button" className="ksv-btn" onClick={onTra}>Thanh toán ₫ {vnd(d.con_phai_tra)}</button>}
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
    <TomTatDon d={d} /></div></>;
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
  const [tra, setTra] = useState(false);
  const [loi, setLoi] = useState("");
  const tai = () => goiCong("/ks-vtd/don").then((r) => setDs(r.don)).catch((x) => setLoi(x.status === 403 ? "" : x.message));
  useEffect(() => { tai(); }, [lamMoi]);  // eslint-disable-line react-hooks/exhaustive-deps
  const hien = (ds || []).filter((d) => !gon || ["cho_tra", "da_tra", "da_xac_nhan"].includes(d.trang_thai) || (d.trang_thai === "da_huy" && d.hoan_tt && d.hoan_tt !== "da_hoan"));
  if (!ds || (!hien.length && gon)) return loi && !gon ? <div className="ksv"><style dangerouslySetInnerHTML={{ __html: CSS }} /><div className="ksv-loi">{loi}</div></div> : null;
  const xem = (d: any) => (onMo ? onMo(d) : setMo(d));
  return <div className="ksv">{gon ? null : <style dangerouslySetInnerHTML={{ __html: CSS }} />}
    {mo && !onMo && tra ? <TraTien d={mo} onDoi={(d) => { setMo(d); tai(); if (d.trang_thai !== "cho_tra") setTra(false); }} onLai={() => { setTra(false); setMo(null); }} />
      : mo && !onMo ? <DonKs d={mo} onDoi={(d) => { setMo(d); tai(); }} onTra={() => setTra(true)} onLai={() => setMo(null)} />
      : <section className="ksv-panel" style={{ gap: 10 }}><b style={{ fontSize: 17 }}>Phòng khách sạn đã đặt của bạn</b>
        {!hien.length && <span className="ksv-muted">Chưa có đơn đặt phòng nào.</span>}
        {hien.map((d) => <div key={d.ma} className="ksv-donrow">
          <span style={{ flex: "1 1 240px", minWidth: 0 }}><b>{d.khach_san?.ten}</b><br /><small className="ksv-muted">{d.ma} · {ngay(d.vao)} → {ngay(d.ra)} · {d.so_phong} phòng</small>
            {d.cach_tra === "sau" && d.trang_thai === "cho_tra" && <><br /><small className="ksv-okc" style={{ fontWeight: 600 }}>Đặt giữ · trả trước {dmy(d.han_tra)}</small></>}</span>
          <span className={`ksv-tt ${MAU_TT[d.trang_thai] || ""}`}>{d.trang_thai === "da_huy" && d.so_hoan > 0 ? `Đã hủy · ${d.hoan_tt_ten || "đã hoàn"}` : d.trang_thai_ten}</span>
          <b style={{ minWidth: 110, textAlign: "right" }}>₫ {vnd(d.tong)}</b>
          <button type="button" className="ksv-btn line" onClick={() => xem(d)}>{d.co_the_tra ? "Thanh toán" : d.danh_gia?.duoc_viet ? "Viết đánh giá" : "Xem"}</button></div>)}</section>}</div>;
}

function TomTat({ ks, q, tinh, giam = 0, maVc, hang, diemDk = 0, traSau = false, chon = [], homNay }: { ks: any; q: Q; tinh: any; giam?: number; maVc?: string; hang?: any; diemDk?: number;
  traSau?: boolean; chon?: any[]; homNay?: string }) {
  const tong = tinh.tong - giam;
  // Giá niêm yết (Điều hành nhập) → số tiết kiệm. Chỉ hiện khi mọi gói đã chọn có giá niêm yết cao hơn.
  const niemYet = chon.length && chon.every((x: any) => x.g.niem_yet_dem > x.g.gia_dem) ? chon.reduce((a: number, x: any) => a + x.n * x.g.niem_yet_dem * (tinh.dem || 1), 0) : 0;
  const phongGoc = chon.reduce((a: number, x: any) => a + x.n * x.g.tong, 0);
  const tk = niemYet > phongGoc ? niemYet - phongGoc : 0;
  const huy = tinh.huy_mien_phi_den as string | null;
  const pctHuy = huy && homNay ? Math.max(8, Math.min(92, (new Date(huy).getTime() - new Date(homNay).getTime()) / Math.max(1, new Date(q.vao).getTime() - new Date(homNay).getTime()) * 100)) : 0;
  const dau = ks.danh_gia || {};
  return <aside className="ksv-col">
    <div className="ksv-panel"><div className="ksv-dts"><div><small>Nhận phòng</small><b>{ngay(q.vao)}</b><small>từ {ks.gio_nhan}</small></div>
      <span className="ksv-muted">→</span><div><small>Trả phòng</small><b>{ngay(q.ra)}</b><small>trước {ks.gio_tra}</small></div>
      <div style={{ textAlign: "center" }}><b style={{ fontSize: 22 }}>{tinh.dem}</b><small>đêm</small></div></div></div>
    <div className="ksv-panel">
      <div className="ksv-hsum">{ks.anh?.[0] ? <img src={ks.anh[0].nho} alt="" /> : null}
        <div><b style={{ fontSize: 16 }}>{ks.ten}</b>{ks.sao > 0 && <div className="ksv-stars" style={{ fontSize: 13 }}>{"★".repeat(ks.sao)}</div>}
          {dau.diem_tb != null && <div style={{ color: "var(--ksv-ink)", fontWeight: 700 }}>{phay(dau.diem_tb)} {dau.nhan || nhan(dau.diem_tb)} <span className="ksv-muted" style={{ fontWeight: 400 }}>{dau.so_bai} đánh giá</span></div>}
          <div className="ksv-muted">{[ks.dia_chi, ks.khu_vuc, ks.tinh_thanh].filter(Boolean).join(", ")}</div></div></div>
      {huy && <span className="ksv-okc" style={{ fontSize: 13, fontWeight: 600 }}>✓ Linh hoạt! Hủy miễn phí trước {dmy(huy)}.</span>}
      {tinh.dong.length ? tinh.dong.map((x: any, i: number) => <div key={i} className="ksv-rsum"><div style={{ display: "flex", flexDirection: "column" }}><b>{x.so} × {x.loai_phong}</b>
        <span className="ksv-muted">{x.goi} · {tinh.dem} đêm{x.bua_sang ? " · bữa sáng" : ""}</span>
        {(x.phu_thu_ct || []).map((c: any, j: number) => <span key={j} className="ksv-sum" style={{ fontSize: 13 }}><span>{c.nhan}{c.tien ? ` (${vnd(c.tien / Math.max(1, c.dem))} × ${c.dem} đêm)` : ""}</span><span>{c.tien ? `₫ ${vnd(c.tien)}` : "Miễn phí"}</span></span>)}
        {x.cho_xac_nhan && <small className="ksv-muted">Giường phụ chờ khách sạn xác nhận — không xếp được thì Vietourist hoàn 100%.</small>}
        {x.huy_han ? <span className="ksv-okc">✓ Miễn phí hủy trước {dmy(x.huy_han)}</span> : <span className="ksv-muted">Không hoàn tiền</span>}</div></div>)
        : <span>{tinh.loai_phong ? `Loại phòng: ${tinh.loai_phong} · ` : ""}{q.phong} phòng · {q.nl} người lớn · Vietourist báo giá</span>}</div>
    {tinh.dong.length > 0 && <div className="ksv-panel"><b>Hủy phòng tốn bao nhiêu?</b>
      {huy ? <><span className="ksv-okc" style={{ fontSize: 13 }}>Hủy miễn phí trước {dmy(huy)}; sau đó theo chính sách gói.</span>
        <div className="ksv-tlh"><b /><s style={{ width: `${pctHuy}%` }} /><b /><s className="gr" /><b className="gr" /></div>
        <div className="ksv-tll"><span>Hôm nay</span><span>{dmy(huy).slice(0, 5)}</span><span>Nhận phòng</span></div></>
        : <span className="ksv-muted" style={{ fontSize: 13 }}>Có gói không hoàn tiền: hủy không được hoàn phần gói đó.</span>}</div>}
    {giam > 0 && <div className="ksv-panel"><b>Voucher đã áp</b><div className="ksv-cp"><div><b>−₫ {vnd(giam)}</b><small className="ksv-muted">{maVc}</small></div><span><Ico d={P.qua} s={22} /></span></div></div>}
    {tk > 0 && <div className="ksv-saved">✓ Bạn tiết kiệm ₫ {vnd(tk)} so với giá niêm yết</div>}
    {tinh.tong > 0 && <div className="ksv-panel ksv-pb">{tk > 0 && <div className="tt">Giảm {Math.round(tk / niemYet * 100)}% so với giá niêm yết</div>}
      <div className="ksv-pbd">
        {tk > 0 && <span className="ksv-sum"><span>Giá niêm yết ({tinh.so_phong} phòng × {tinh.dem} đêm)</span><s className="ksv-muted">₫ {vnd(niemYet)}</s></span>}
        <span className="ksv-sum"><span>Giá phòng ({tinh.so_phong} phòng × {tinh.dem} đêm){tinh.phu_thu ? " · gồm phụ thu" : ""}</span><span>₫ {vnd(tinh.tien_phong)}</span></span>
        <span className="ksv-sum"><span>Thuế và phí ({ks.thue_phi_pt || 0}%)</span><span>₫ {vnd(tinh.thue_phi)}</span></span>
        {giam > 0 && <span className="ksv-sum ksv-okc"><span>Voucher {maVc}</span><span>− ₫ {vnd(giam)}</span></span>}
        <span className="ksv-sum ksv-okc"><span>Phí đặt phòng</span><span>MIỄN PHÍ</span></span>
        <span className="ksv-tot"><span>{giam > 0 ? "Bạn trả" : "Tổng cộng"}</span><span>₫ {vnd(tong)}</span></span>
        <small className="ksv-muted">Đã gồm thuế và phí.{traSau ? ` Hôm nay trả ₫ 0 · hạn trả ${dmy(tinh.han_tra_sau)}.` : ""}</small>
        {hang?.cach_tinh === "hoa_hong" && tong > 0 && <span className="ksv-diem-box">Đơn này tích điểm sau khi trả phòng và Vietourist chốt đơn: điểm = 20% hoa hồng Vietourist nhận ÷ 100 đ × {phay(hang.he_so)} (hạng {hang.hang}). Không tính vào chi tiêu xét hạng.</span>}
        {hang?.cach_tinh !== "hoa_hong" && hang && diemDk > 0 && <span className="ksv-diem-box"><b>+ {vnd(diemDk)} điểm</b> sau khi trả phòng và Vietourist chốt đơn ({vnd(tong)} ÷ {vnd(hang.dong_moi_diem)} × {phay(hang.he_so)} hạng {hang.hang}). Kỳ ở này cũng tính vào chi tiêu xét hạng.</span>}
        <small className="ksv-muted">{tinh.dong?.length ? "Giá do máy chủ tính lại lúc giữ phòng. Trả xong, Điều hành chốt với khách sạn trong 2 giờ làm việc — khách sạn hết phòng thì hoàn 100%."
          : "Giá Vietourist tính lúc bạn chọn. Điều hành xác nhận lại với khách sạn trước khi bạn trả tiền."}</small></div></div>}
  </aside>;
}

const CSS = `
.ksv-dd{display:flex;flex-direction:column;gap:10px}
.ksv-ddr{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px}
.ksv-ddc{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:2px;background:#fff;border:1px solid #dde3ee;border-radius:12px;overflow:hidden;padding-bottom:8px}
.ksv-ddc img,.ksv-ddc .ph{width:100%;height:84px;object-fit:cover;background:#dfe7f3}
.ksv-ddc b{padding:0 10px;font-size:14px;color:#1a2233}.ksv-ddc small{padding:0 10px;color:#5d6a7d;font-size:12px}
.ksv-ddc.on,.ksv-ddc:focus-visible{outline:2px solid #2a5bd7}
.ksv-bando{width:100%;border-radius:12px;background:#e6eef5;z-index:0}
.ksv-mapbox{display:flex;flex-direction:column;gap:8px;position:sticky;top:8px;z-index:2;background:#f4f6fa;padding-bottom:6px}
.ksv-mapbar{display:flex;gap:10px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.ksv-pin{display:inline-block;transform:translate(-50%,-100%);background:#fff;color:#1a2233;border:2px solid #d92d20;border-radius:99px;padding:3px 8px;font:800 12px/1.2 system-ui,sans-serif;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.25)}
.ksv-pin.on{background:#d92d20;color:#fff}
.ksv-card-on{outline:2px solid #2a5bd7;outline-offset:0}
.ksv-khoa{background:#c9d1de!important;color:#4a5568!important;border-color:#c9d1de!important;cursor:not-allowed}
@media (max-width:760px){.ksv-mapbox{position:relative;top:0}}
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
.ksv-ct.ksv-tam{font-weight:500}
.ksv-ico{position:absolute;border:0;border-radius:50%;background:#fff;display:grid;place-items:center;box-shadow:0 1px 4px rgba(0,0,0,.2)}
.ksv-heart{right:10px;top:10px;width:38px;height:38px}.ksv-heart.on svg{fill:#e0335a;stroke:#e0335a}
.ksv-nxt{right:10px;top:calc(50% - 16px);width:32px;height:32px}.ksv-prv{left:10px;top:calc(50% - 16px);width:32px;height:32px}
.ksv-trong{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;width:100%;height:100%;min-height:200px;background:#eef2f5}
.ksv-trong b{width:52px;height:52px;border-radius:50%;color:#fff;font-size:24px;display:grid;place-items:center}
.ksv-trong small{font-size:12px;color:#3d4b59}
.ksv-info{padding:14px 18px;display:flex;flex-direction:column;gap:5px;min-width:0}
.ksv-info h3{margin:0;font-size:20px}.ksv-ten{all:unset;cursor:pointer;font-weight:800;color:var(--ksv-fg)}.ksv-ten:hover{color:var(--ksv-ink)}
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
/* ── KS-16p · giao diện kiểu Agoda, thương hiệu Vietourist ── */
.ksv h1,.ksv h2,.ksv h3,.ksv h4{color:inherit;text-transform:none;letter-spacing:normal;font-family:inherit}
.ksv-fl,.ksv-f,.ksv-radio,.ksv-fbox .ksv-chk,.ksv-sbody .ksv-chk,.ksv-req .ksv-chk{margin-top:0}
.ksv-sbody .ksv-chk,.ksv-req .ksv-chk,.ksv-fbox .ksv-chk{color:#3c4657;font-size:13.5px}
.ksv-radio,.ksv-fld,.ksv-chk{color:var(--ksv-fg)}
.ksv-fld input,.ksv-fld textarea,.ksv-vc,#vtd-access .ksv .ksv-fld input,#vtd-access .ksv .ksv-fld textarea{color:#23252c;-webkit-text-fill-color:#23252c}
.ksv{--ksv-navy:#14284b;--ksv-purple:#6b3fd1;--ksv-redsoft:#fdecec;--ksv-line2:#eef1f5;--ksv-sh:0 1px 2px rgba(16,24,40,.06),0 2px 8px rgba(16,24,40,.06);font-size:14px;line-height:1.45}
.ksv-h1{font-size:22px;font-weight:800;margin:0;line-height:1.2}.ksv-h2{font-size:18px;font-weight:800;margin:0}.ksv-h3{font-size:17px;font-weight:700;margin:0}
.ksv-col{display:flex;flex-direction:column;gap:14px;min-width:0}
.ksv-panel{box-shadow:var(--ksv-sh);border-radius:12px}
.ksv-btn{border-radius:99px;display:inline-flex;align-items:center;justify-content:center;gap:6px;flex-direction:column}
.ksv-btn.sm{min-height:36px;padding:0 16px;font-size:13.5px}.ksv-btn.big{min-height:52px;padding:0 26px;font-size:16px;letter-spacing:.3px;flex-direction:row}
.ksv-btn:not(.line):hover:not(:disabled){background:#2a50c8}
.ksv-b{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;font-weight:700;border-radius:4px;padding:2px 7px;white-space:nowrap;align-self:flex-start}
.ksv-b.navy{background:var(--ksv-navy);color:#fff}.ksv-b.purple{background:var(--ksv-purple);color:#fff}.ksv-b.green{background:var(--ksv-oksoft);color:var(--ksv-ok)}.ksv-b.out{border:1px solid var(--ksv-line);color:#3c4657;font-weight:500}
.ksv-b.aw{position:absolute;left:8px;top:8px}
/* tìm */
.ksv-hero{border-radius:16px;overflow:hidden;background:linear-gradient(180deg,#2a7fb6 0%,#3fa7d3 55%,#7fd0e8 100%);padding:36px 16px 0;position:relative}
.ksv-hero::after{content:"";position:absolute;left:0;right:0;bottom:0;height:70px;background:linear-gradient(180deg,transparent,rgba(241,226,184,.85))}
.ksv-hero-in{position:relative;z-index:1;max-width:880px;margin:0 auto;display:flex;flex-direction:column;align-items:center}
.ksv-hero h1{color:#fff;font-size:28px;font-weight:800;text-align:center;margin:0 0 18px;text-shadow:0 2px 10px rgba(0,0,0,.3);text-wrap:balance}
.ksv-sbox2{width:100%;background:#fff;border-radius:16px;box-shadow:0 8px 28px rgba(16,24,40,.18);margin-bottom:32px}
.ksv-stabs{display:flex;justify-content:center;border-bottom:1px solid var(--ksv-line);padding:0 10px}
.ksv-stabs span{padding:12px 14px;font-weight:600;color:#3c4657;display:flex;gap:6px;align-items:center;border-bottom:3px solid transparent}.ksv-stabs span.on{color:var(--ksv-accent);border-color:var(--ksv-accent)}
.ksv-sbody{padding:16px 22px 0;display:flex;flex-direction:column;gap:10px}
.ksv-fl{border:1px solid var(--ksv-line);border-radius:10px;padding:10px 14px;display:flex;align-items:center;gap:12px;background:#fff;color:#23252c;min-width:0}
.ksv-fl small,.ksv-f small{display:block;font-size:11.5px;color:#6b7686}
.ksv-fl select,.ksv-fl input,.ksv-f select,.ksv-f input,#vtd-access .ksv .ksv-fl select,#vtd-access .ksv .ksv-fl input,#vtd-access .ksv .ksv-f select,#vtd-access .ksv .ksv-f input{border:0;background:transparent;font-weight:600;font-size:16px;width:100%;outline:none;padding:0;color:#23252c;min-width:0;font-family:inherit}
.ksv-fl2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ksv-sgo{display:flex;justify-content:center;transform:translateY(50%)}.ksv-sgo .ksv-btn{width:min(480px,90%);font-size:17px}
.ksv-promo{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}
.ksv-promo .ksv-panel{gap:4px}
/* thanh tìm gọn */
.ksv-sbar{background:var(--ksv-navy);border-radius:12px;padding:10px;display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) minmax(0,1fr) minmax(0,1fr) auto;gap:6px}
.ksv-f{background:#fff;color:#23252c;border-radius:8px;display:flex;align-items:center;gap:10px;padding:7px 12px;min-height:52px;min-width:0}
.ksv-f>span{flex:1;min-width:0}.ksv-f b{display:block;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ksv-f input,#vtd-access .ksv .ksv-f input{font-size:14.5px}
.ksv-go{border:0;border-radius:10px;background:var(--ksv-accent);color:#fff;font-weight:700;font-size:15px;padding:0 26px;min-height:52px}
.ksv-coupon{display:flex;align-items:center;gap:14px;background:linear-gradient(90deg,#fff1e6,#fde9f1);border-radius:12px;padding:12px 16px;color:#3a2a1a}.ksv-coupon svg{color:#e8590c}
/* danh sách */
.ksv-layout{grid-template-columns:268px minmax(0,1fr);gap:18px;align-items:start}
.ksv-fbox{padding:0;gap:0;overflow:hidden}.ksv-fbox .fsec{padding:12px 16px;border-top:1px solid var(--ksv-line);display:flex;flex-direction:column;gap:6px}.ksv-fbox .fsec:first-child{border-top:0}
.ksv-fbox h4{margin:0 0 2px;font-size:14px}.ksv-fbox .ksv-chk{font-size:13.5px;color:#3c4657;min-height:28px}
.ksv-card{border:1px solid var(--ksv-line);box-shadow:var(--ksv-sh)}
.ksv-banner{background:var(--ksv-navy);color:#fff;font-size:12.5px;padding:6px 14px}.ksv-banner b{color:#ffd54a}
.ksv-crow{grid-template-columns:250px minmax(0,1fr) 215px;min-height:210px}
.ksv-info{gap:6px}.ksv-info h3{font-size:19px;font-weight:800;line-height:1.2}
.ksv-hl{display:flex;gap:6px;align-items:flex-start;color:#3c4657;font-size:12.5px;margin-top:auto}.ksv-hl svg{color:var(--ksv-purple);margin-top:1px}
.ksv-side{border-left:1px solid var(--ksv-line2);gap:4px}
.ksv-score{display:flex;gap:8px;align-items:center;justify-content:flex-end}.ksv-score>span{display:flex;flex-direction:column;align-items:flex-end}.ksv-score>span>b:first-child{color:var(--ksv-ink);background:none;padding:0}
.ksv-score>b{background:var(--ksv-ink);color:#fff;padding:3px 7px;border-radius:6px 6px 6px 0;font-size:14px}
.ksv-pblk{margin-top:auto;display:flex;flex-direction:column;align-items:inherit;gap:3px;width:100%}
.ksv-vp{background:var(--ksv-redsoft);color:var(--ksv-price);font-size:12px;font-weight:700;border-radius:6px;padding:3px 8px;align-self:flex-end}
.ksv-hetb{background:var(--ksv-line2);border-radius:8px;padding:8px 12px;font-weight:600}
.ksv-big{font-weight:800;font-size:24px}
/* trang khách sạn */
.ksv-gal{grid-template-columns:2fr 1fr 1fr 1fr;grid-template-rows:150px 150px;gap:8px;border-radius:12px}
.ksv-gal>button{all:unset;cursor:pointer;position:relative;background:var(--ksv-soft);border-radius:10px;overflow:hidden;min-width:0}
.ksv-gal>button:first-child{grid-row:1 / 3}
.ksv-gal>button:focus-visible{outline:2px solid var(--ksv-accent);outline-offset:2px}
.ksv-gal>button>.ksv-see,.ksv-gal>button>.ksv-ct{position:absolute;grid-row:auto}.ksv-gal>button>.ksv-see{background:#fff}.ksv-gal>button>.ksv-ct{background:rgba(20,20,30,.66);cursor:pointer}
.ksv-see{position:absolute;right:10px;bottom:10px;background:#fff;color:#1b2230;border-radius:99px;padding:6px 12px;font-weight:600;font-size:13px;display:flex;gap:6px;align-items:center;box-shadow:var(--ksv-sh)}
.ksv-sub{position:sticky;top:0;z-index:15;background:#fff;border:1px solid var(--ksv-line);border-radius:12px;box-shadow:var(--ksv-sh);display:flex;align-items:center;gap:8px;padding:0 12px}
.ksv-sub .tb{display:flex;gap:2px;overflow-x:auto;flex:1;min-width:0}
.ksv-sub .tb a{padding:14px 12px;font-weight:600;color:#3c4657;border-bottom:3px solid transparent;white-space:nowrap;text-decoration:none}.ksv-sub .tb a:hover{color:var(--ksv-accent);border-color:var(--ksv-accent)}
.ksv-sub .from{display:flex;align-items:baseline;gap:6px;white-space:nowrap}.ksv-sub .from .ksv-btn{align-self:center}
.ksv-g2{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:14px;align-items:start;scroll-margin-top:70px}
.ksv-hlr{display:flex;gap:12px;padding:10px 0;border-top:1px solid var(--ksv-line2)}.ksv-h2+.ksv-hlr{border-top:0}
.ksv-hlr .ic{width:42px;height:42px;border-radius:10px;background:var(--ksv-asoft);color:var(--ksv-accent);display:flex;align-items:center;justify-content:center;flex:none}
.ksv-facs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px 12px;font-size:13.5px}.ksv-facs span{display:flex;gap:6px;align-items:center}.ksv-facs svg{color:var(--ksv-ok)}
.ksv-hot{background:var(--ksv-redsoft);border-radius:10px;padding:12px 16px}.ksv-hot b{color:var(--ksv-price)}
.ksv-bars{display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;font-size:12.5px}.ksv-bars div{display:flex;flex-direction:column;gap:3px}
.ksv-bars s{display:block;height:5px;border-radius:3px;background:var(--ksv-line);text-decoration:none;position:relative;overflow:hidden}.ksv-bars s i{position:absolute;inset:0 auto 0 0;background:var(--ksv-ink)}
.ksv-map{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;height:120px;text-decoration:none;color:#23252c;
  background:repeating-linear-gradient(0deg,transparent 0 38px,#fff 38px 41px),repeating-linear-gradient(90deg,#eef2e6 0 70px,#f3d36a 70px 75px);}
.ksv-map span{color:#e5484d}.ksv-map b{font-size:13px;letter-spacing:.5px;background:#fff;padding:3px 10px;border-radius:99px}
.ksv-chips{display:flex;flex-wrap:wrap;gap:8px}
.ksv-sold{display:inline-flex;gap:6px;align-items:center;background:var(--ksv-redsoft);color:var(--ksv-price);border-radius:8px;padding:6px 10px;font-size:12.5px;font-weight:600;align-self:flex-start}
.ksv-room{grid-template-columns:290px minmax(0,1fr);border:1px solid var(--ksv-line);border-radius:14px}
.ksv-rl{border-right:1px solid var(--ksv-line2);padding:12px}
.ksv-rph{all:unset;cursor:pointer;position:relative;display:block;height:180px;border-radius:10px;overflow:hidden;background:var(--ksv-soft)}
.ksv-rph img{width:100%;height:100%;object-fit:cover;display:block}
.ksv-rn{font-size:18px;font-weight:800}.ksv-spec{font-size:12.5px;font-weight:600;color:#3c4657}
.ksv-amen{display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;font-size:12.5px;color:#3c4657}
.ksv-rr{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr) 190px;border-top:1px solid var(--ksv-line2)}.ksv-rr:first-child{border-top:0}
.ksv-rr>div{padding:12px 14px;display:flex;flex-direction:column;gap:5px;font-size:13px;min-width:0}
.ksv-rr .deal{grid-column:1 / -1;flex-direction:row;align-items:center;background:var(--ksv-price);color:#fff;padding:5px 14px;font-weight:700;font-size:12.5px}
.ksv-rr .ben span{display:flex;gap:5px;align-items:center}.ksv-rr .ben .ksv-okc{font-weight:600}
.ksv-rr .pc{border-left:1px solid var(--ksv-line2);border-right:1px solid var(--ksv-line2);align-items:flex-end;text-align:right}
.ksv-rr .act{align-items:stretch;text-align:center}.ksv-rr .act .ksv-sel{border-radius:99px}
.ksv-cheap{color:var(--ksv-price);font-size:12.5px;font-weight:600}
/* album */
.ksv-alb{position:fixed;inset:0;z-index:60;background:rgba(8,12,20,.94);overflow:auto;padding:16px}
.ksv-alb-in{max-width:1100px;margin:0 auto;color:#fff;display:flex;flex-direction:column;gap:12px}
.ksv-alb-hd{display:flex;align-items:center;gap:12px;font-size:18px}.ksv-alb-hd span{font-weight:400;color:#9fb0c2;font-size:13px}
.ksv-alb-x{margin-left:auto;width:40px;height:40px;border-radius:99px;border:0;background:#26324a;color:#fff;font-size:18px;flex:none}
.ksv-alb-tabs{display:flex;gap:6px;flex-wrap:wrap}
.ksv-alb-tabs button{border:1px solid #33415a;background:transparent;border-radius:99px;padding:7px 13px;font-size:13px;color:#cfd8e6;min-height:36px}
.ksv-alb-tabs button.on{background:#fff;color:#111;font-weight:700;border-color:#fff}
.ksv-alb-big{position:relative;height:min(62vh,560px);border-radius:10px;overflow:hidden;background:#000}.ksv-alb-big img{width:100%;height:100%;object-fit:contain;display:block}
.ksv-alb-nv{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border-radius:99px;border:0;background:rgba(255,255,255,.95);color:#111;display:flex;align-items:center;justify-content:center}
.ksv-alb-nv.l{left:12px}.ksv-alb-nv.r{right:12px}
.ksv-alb-cap{position:absolute;left:12px;bottom:12px;background:rgba(0,0,0,.6);padding:3px 10px;border-radius:99px;font-size:12.5px;max-width:calc(100% - 24px)}
.ksv-alb-th{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px}
.ksv-alb-th button{all:unset;cursor:pointer;width:92px;height:62px;flex:none;border-radius:6px;overflow:hidden;opacity:.55}.ksv-alb-th button.on{opacity:1;outline:2px solid #fff;outline-offset:-2px}
.ksv-alb-th img{width:100%;height:100%;object-fit:cover;display:block}
.ksv-alb-vid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
/* đặt phòng */
.ksv-bk{background:#fff;border:1px solid var(--ksv-line);border-radius:12px;padding:12px 16px;box-shadow:var(--ksv-sh)}
.ksv-stp{display:flex;align-items:center;justify-content:center;gap:10px;font-size:13.5px;color:var(--ksv-muted)}
.ksv-stp .s{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:110px;text-align:center}
.ksv-stp .s i{width:26px;height:26px;border-radius:99px;border:1.5px solid var(--ksv-line);display:flex;align-items:center;justify-content:center;font-style:normal;font-weight:700;background:#fff}
.ksv-stp .s.on{color:var(--ksv-accent);font-weight:700}.ksv-stp .s.on i{background:var(--ksv-accent);color:#fff;border-color:var(--ksv-accent)}
.ksv-stp .s.dn{color:var(--ksv-ok)}.ksv-stp .s.dn i{background:var(--ksv-ok);color:#fff;border-color:var(--ksv-ok)}
.ksv-stp .ln{height:3px;width:90px;background:var(--ksv-line);border-radius:2px;margin-bottom:20px}.ksv-stp .ln.on{background:var(--ksv-accent)}
.ksv-tmr{background:#fdeaea;color:#8a1c1c;text-align:center;padding:9px 12px;font-weight:600;border-radius:10px;display:flex;justify-content:center;align-items:center;gap:8px;flex-wrap:wrap}
.ksv-tmr b{font-variant-numeric:tabular-nums}
.ksv-co{grid-template-columns:minmax(0,1fr) 390px}
.ksv-sec0{padding:16px 4px 4px;gap:0}.ksv-sec0 h3{margin:0 0 8px;padding:0 14px;font-size:17px}
.ksv-radio{display:flex;gap:12px;padding:12px 14px;border-top:1px solid var(--ksv-line2);cursor:pointer;align-items:flex-start}.ksv-sec0 h3+.ksv-radio{border-top:0}
.ksv-radio input,#vtd-access .ksv .ksv-radio input{width:20px;height:20px;margin:2px 0 0;flex:none;accent-color:var(--ksv-accent)}
.ksv-radio.on{background:var(--ksv-asoft)}.ksv-radio b{font-size:15px}
.ksv-logos{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}.ksv-logos span{border:1px solid var(--ksv-line);border-radius:4px;font-size:10.5px;font-weight:800;padding:2px 6px;color:#3c4657;background:#fff}
.ksv-av{width:36px;height:36px;border-radius:99px;background:var(--ksv-accent);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex:none}
.ksv-req{display:grid;grid-template-columns:1fr 1fr;gap:12px;background:var(--ksv-asoft);border-radius:10px;padding:12px 14px}.ksv-req>div{display:flex;flex-direction:column;gap:6px;font-size:13.5px}
.ksv-ben{display:flex;align-items:center;gap:12px;background:var(--ksv-line2);border-radius:10px;padding:10px 12px}
.ksv-ben .bi{width:38px;height:38px;border-radius:10px;background:#fff;color:var(--ksv-accent);display:flex;align-items:center;justify-content:center;flex:none}
.ksv-ben small{display:block;color:var(--ksv-muted)}
.ksv-ben .fr{margin-left:auto;background:var(--ksv-ok);color:#fff;font-size:11px;font-weight:800;border-radius:4px;padding:3px 7px;white-space:nowrap}
.ksv-hurry{color:var(--ksv-price);text-align:right;font-weight:600;font-size:13.5px}
.ksv-dts{display:grid;grid-template-columns:1fr auto 1fr auto;align-items:center;gap:10px}.ksv-dts>div{display:flex;flex-direction:column}.ksv-dts small{color:var(--ksv-muted);font-size:12px}
.ksv-hsum{display:flex;gap:12px}.ksv-hsum img{width:92px;height:110px;object-fit:cover;border-radius:10px;flex:none}
.ksv-rsum{background:var(--ksv-asoft);border-radius:10px;padding:10px 12px}
.ksv-tlh{display:flex;align-items:center;margin:8px 4px 2px}.ksv-tlh b{width:12px;height:12px;border-radius:99px;background:var(--ksv-ok);flex:none}.ksv-tlh s{height:4px;background:var(--ksv-ok);text-decoration:none}
.ksv-tlh s.gr{flex:1;background:var(--ksv-line)}.ksv-tlh b.gr{background:var(--ksv-line)}
.ksv-tll{display:flex;justify-content:space-between;font-size:11.5px;color:var(--ksv-muted)}
.ksv-cp{display:flex;align-items:center;border:1.5px solid var(--ksv-ok);border-radius:10px;overflow:hidden}.ksv-cp>div{padding:10px 12px;flex:1;display:flex;flex-direction:column}
.ksv-cp>span{border-left:1.5px dashed var(--ksv-ok);padding:10px 14px;color:var(--ksv-ok)}
.ksv-saved{background:var(--ksv-oksoft);color:var(--ksv-ok);border-radius:10px;padding:10px 12px;font-weight:600;font-size:13px}
.ksv-pb{padding:0;overflow:hidden;gap:0}.ksv-pb .tt{background:var(--ksv-price);color:#fff;font-weight:700;font-size:13px;padding:6px 14px}
.ksv-pb .ksv-pbd{padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.ksv-tot{display:flex;justify-content:space-between;font-size:18px;font-weight:800;border-top:1px solid var(--ksv-line);padding-top:10px;margin-top:4px}
.ksv-done{display:flex;gap:16px;align-items:center;background:var(--ksv-oksoft);border-radius:14px;padding:18px}
.ksv-done .ck2{width:52px;height:52px;border-radius:99px;background:var(--ksv-ok);color:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.ksv-btn.ksv-fbtn{display:none}
@media (max-width:900px){
  .ksv-btn.ksv-fbtn{display:inline-flex;flex-direction:row;white-space:nowrap}
  .ksv-layout{grid-template-columns:1fr}
  .ksv-sbar{grid-template-columns:1fr 1fr}.ksv-sbar .ksv-f-tp{grid-column:1 / -1}.ksv-go{grid-column:1 / -1}
  .ksv-promo{grid-template-columns:1fr}
  .ksv-crow{grid-template-columns:1fr}.ksv-side{align-items:stretch;text-align:left}.ksv-score{justify-content:flex-start}.ksv-score>span{align-items:flex-start}.ksv-vp{align-self:flex-start}
  .ksv-g2,.ksv-co{grid-template-columns:1fr}
  .ksv-gal{grid-template-columns:1fr 1fr;grid-template-rows:200px 110px 110px}.ksv-gal>button:first-child{grid-column:1 / -1;grid-row:auto}.ksv-gal>button:nth-child(n+6){display:none}
  .ksv-sub .from .ksv-muted{display:none}.ksv-sub .from .ksv-big{display:none}
  .ksv-room{grid-template-columns:1fr}.ksv-rl{border-right:0;border-bottom:1px solid var(--ksv-line2)}
  .ksv-rr{grid-template-columns:1fr}.ksv-rr .pc{border:0;align-items:flex-start;text-align:left;padding-top:0}
  .ksv-facs{grid-template-columns:1fr 1fr}
  .ksv-stp .ln{width:30px}.ksv-stp .s{min-width:70px;font-size:11.5px}
}
@media (max-width:600px){.ksv-fl2,.ksv-req{grid-template-columns:1fr}.ksv-hero h1{font-size:22px}.ksv-sbody{padding:14px 14px 0}.ksv-alb{padding:10px}.ksv-alb-big{height:46vh}}
/* KS-16q: trong cổng (#vtd-access .v3-app) bộ CSS v3 đè màu chữ nút, tiêu đề, ô nhập — giữ đúng màu của giao diện khách sạn. */
#vtd-access .ksv .ksv-hero h1{color:#fff;letter-spacing:0;line-height:1.25}
/* «#vtd-access button{color:inherit}» của vtd.css mạnh hơn lớp .ksv-* → nút xanh ra chữ tối. Nhắc lại màu chữ nút ở đây. */
#vtd-access .ksv button.ksv-btn-tim,#vtd-access .ksv button.ksv-btn,#vtd-access .ksv button.ksv-go,#vtd-access .ksv button.ksv-alb-x{color:#fff}
#vtd-access .ksv button.ksv-btn.line,#vtd-access .ksv button.ksv-link{color:var(--ksv-ink)}
#vtd-access .ksv button.ksv-ten{color:var(--ksv-fg)}#vtd-access .ksv button.ksv-ten:hover{color:var(--ksv-ink)}
#vtd-access .ksv button.ksv-alb-nv{color:#111}
#vtd-access .ksv button.ksv-chip{color:#3d4556}#vtd-access .ksv button.ksv-chip.on{color:var(--ksv-ink)}
#vtd-access .ksv input[type=date]{color:inherit;-webkit-text-fill-color:currentColor}
`;
export const CSS_KSV = CSS;   // AT-2: trang nhà hàng dùng chung ngôn ngữ giao diện
