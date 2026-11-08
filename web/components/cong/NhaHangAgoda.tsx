"use client";
/* AT-2 · Nhà hàng kiểu Agoda trên trang riêng kh.vietourist.vn/restaurant (Chủ tịch duyệt bản xem thử 01/11/2026).
   Cùng khung, màu, thứ tự bước như cổng khách sạn (KS-16p/16s): 1 tìm → 2 danh sách + bộ lọc + bản đồ → 3 trang nhà hàng
   (album theo nhóm, mục dính, món nên thử, giờ phục vụ, đánh giá, vị trí) → 4 chọn giờ + thực đơn → 5–6 thông tin khách +
   cách trả (cọc theo tỷ lệ đã duyệt / trả đủ) → 7 đã gửi đặt bàn (mã, QR, thêm vào lịch, chỉ đường, đơn + thanh toán).
   Luồng đặt bàn giữ nguyên DT-2: gửi đơn → nhà hàng nhận bàn → mới hiện QR / thẻ (DatBanCuaToi). Máy chủ tự tính tiền.
   Công tắc thanh toán (chung + từng nhà hàng) chưa bật thì khách vẫn đi hết các bước nhưng nút cuối khóa, không gửi gì.
   Số đếm bộ lọc là số thật; nhóm lọc không có nơi nào khớp thì ẩn. Chưa có sức chứa theo giờ → mọi giờ trong giờ phục vụ
   đều chọn được, nhà hàng xác nhận. */
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import dynamic from "next/dynamic";
import QRCode from "qrcode";
import { goiCong, xemCong } from "@/lib/cong";
import { CSS_KSV } from "./KhachSanVtd";
import { giaGon, type Ghim } from "./BanDoKs";
import { VideoO } from "./VideoCong";
import DanhGiaNhaHangKhach, { SaoThe } from "./khach/DanhGiaNhaHangKhach";
import { NhanPl } from "./khach/KhamPhaAmThuc";
import DatBanCuaToi from "./DatBanCuaToi";

const BanDo = dynamic(() => import("./BanDoKs"), { ssr: false, loading: () => <div className="ksv-bando" style={{ height: 420 }} /> });

const vnd = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const themNgay = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };
const THU = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const ngayDep = (s: string) => { const d = new Date(s + "T00:00:00"); return `${THU[d.getDay()]}, ${d.getDate()}/${d.getMonth() + 1}`; };
const khongDau = (s: string) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d");
const nghin = (x: number) => Math.ceil(Math.round(x) / 1000) * 1000;
const MAU: Record<string, string> = { bac: "#1f4e5f", trung: "#7a4a22", tay_nguyen: "#5b4a2e", nam: "#2f5d3a" };

/** Khung giờ đặt bàn từ «giờ phục vụ» (vd «10:00–14:00, 17:00–22:00»). Không đọc được → khung mặc định 10:30–21:00. */
export function khungGio(gioPv: string): string[] {
  const cap = Array.from((gioPv || "").matchAll(/(\d{1,2})[:h.](\d{2})?\s*[–\-—~đến]+\s*(\d{1,2})[:h.](\d{2})?/g));
  const phut = (h: string, m?: string) => Number(h) * 60 + Number(m || 0);
  const ds = cap.length ? cap.map((m) => [phut(m[1], m[2]), phut(m[3], m[4])] as [number, number])
    .map(([a, b]) => [a, b <= a ? b + 24 * 60 : b] as [number, number]) : [[630, 21 * 60 + 30]] as [number, number][];
  const ra: string[] = [];
  for (const [a, b] of ds) for (let t = Math.ceil(a / 30) * 30; t <= b - 60; t += 30) {
    const h = Math.floor(t / 60) % 24, m = t % 60, s = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
    if (!ra.includes(s)) ra.push(s);
  }
  return ra.length ? ra : ["11:00", "11:30", "12:00", "18:00", "18:30", "19:00", "19:30"];
}
const trongGio = (gioPv: string, gio: string) => !gioPv || khungGio(gioPv).includes(gio);

type Q = { q: string; tinh: string; ngay: string; gio: string; nl: number; te: number };
type Loc = { dat: boolean; con: boolean; at: string[]; gia: string[]; ph: string[]; loai: string[]; ten: string };
const LOC0: Loc = { dat: false, con: false, at: [], gia: [], ph: [], loai: [], ten: "" };
const GIA: [string, string, (g: number) => boolean][] = [["duoi300", "Dưới 300.000 ₫", (g) => g < 300000],
  ["300_700", "300.000 – 700.000 ₫", (g) => g >= 300000 && g <= 700000], ["tren700", "Trên 700.000 ₫", (g) => g > 700000]];
const PH: [string, string][] = [["gia_dinh", "Gia đình có trẻ em"], ["tiec", "Tiệc / đoàn từ 10 khách"], ["phong_rieng", "Phòng riêng"]];
const LOAI: [string, string, (n: any) => boolean][] = [["dac_san", "Đặc sản địa phương", (n) => !!n.dac_san], ["michelin", "Michelin / Bib Gourmand", (n) => !!n.la_michelin],
  ["hai_san", "Hải sản", (n) => n.am_thuc === "Hải sản"], ["chay", "Chay", (n) => n.am_thuc === "Chay"], ["phong_rieng", "Phòng riêng · tiệc", (n) => !!n.phong_rieng]];

function OTrong({ n, cao = 200 }: { n: any; cao?: number }) {
  const chu = (n.ten || "?").normalize("NFC").trim().charAt(0).toUpperCase();
  return <span className="ksv-trong" style={{ minHeight: cao }}><b style={{ background: MAU[n.mien] || "#7a4a22" }}>{chu}</b><small>Ảnh đang cập nhật</small></span>;
}

function taiLich(d: { ma: string; ten: string; ngay: string; gio: string; dia_chi: string; nguoi: number }) {
  const t = d.ngay.replace(/-/g, "") + "T" + d.gio.replace(":", "") + "00";
  const [h, m] = d.gio.split(":").map(Number), ket = new Date(2000, 0, 1, h + 2, m);
  const t2 = d.ngay.replace(/-/g, "") + "T" + String(ket.getHours()).padStart(2, "0") + String(ket.getMinutes()).padStart(2, "0") + "00";
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Vietourist//VTOS//VI", "BEGIN:VEVENT", `UID:${d.ma}@vietourist.vn`,
    `DTSTART:${t}`, `DTEND:${t2}`, `SUMMARY:Đặt bàn ${d.ten} (${d.ma})`, `LOCATION:${d.dia_chi.replace(/,/g, "\\,")}`,
    `DESCRIPTION:${d.nguoi} khách · mã ${d.ma} · Vietourist`, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = `${d.ma}.ics`; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const chiDuong = (n: any) => n.vi_do != null
  ? `https://www.google.com/maps/dir/?api=1&destination=${n.vi_do},${n.kinh_do}`
  : `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent([n.ten, n.khu_vuc, n.tinh_thanh].filter(Boolean).join(", "))}`;

export default function NhaHangAgoda({ ten = "", lienHe = "", coSdt = false, sdtCho = "", doiTac = false, moId }:
  { ten?: string; lienHe?: string; coSdt?: boolean; sdtCho?: string; doiTac?: boolean; moId?: number }) {
  const homNay = iso(new Date());
  const [ds, setDs] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [q, setQ] = useState<Q>({ q: "", tinh: "", ngay: themNgay(homNay, 1), gio: "19:00", nl: 2, te: 0 });
  const [loc, setLoc] = useState<Loc>(LOC0);
  const [sx, setSx] = useState("phu_hop");
  const [moLoc, setMoLoc] = useState(false);
  const [banDo, setBanDo] = useState(false);
  const [theoKhung, setTheoKhung] = useState(false);
  const [khung, setKhung] = useState<any>(null);
  const [chonBd, setChonBd] = useState<number | null>(null);
  const [anhI, setAnhI] = useState<Record<number, number>>({});
  const [nh, setNh] = useState<any>(null);
  const [album, setAlbum] = useState<{ nhom: string; i: number | null } | null>(null);
  const [buoc, setBuoc] = useState<"ds" | "nh" | "dat" | "xong">("ds");
  const [chon, setChon] = useState<{ td: number | null; gio: string }>({ td: null, gio: "19:00" });
  const [kh, setKh] = useState({ sdt: "", ten_khach: "", ghi: "", cach: "coc", dongy: false, dongy_khach: false, dip: "" });
  const [busy, setBusy] = useState(false);
  const [xong, setXong] = useState<any>(null);
  const [qrMa, setQrMa] = useState("");

  useEffect(() => {
    goiCong("/mo/nha-hang/tat-ca").then(setDs).catch((x) => setLoi(x.message));
    if (moId) moNh(moId);
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const moNh = async (id: number, toiThucDon = false) => {
    setLoi(""); setBusy(true);
    try {
      const o = await xemCong(`/dat-ban/nha-hang/${id}`);
      setNh(o); setBuoc("nh"); setChon({ td: o.thuc_don?.[0]?.id ?? null, gio: q.gio });
      setTimeout(() => { if (toiThucDon) document.getElementById("nhv-td")?.scrollIntoView({ behavior: "smooth" }); else window.scrollTo(0, 0); }, 60);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  // ---------- danh sách + bộ lọc (chạy trên máy khách, số đếm thật) ----------
  const tat = ds?.nha_hang || [];
  const k0 = khongDau(q.q.trim());
  const coTim = (n: any) => !k0 || khongDau(`${n.ten} ${n.mon_noi_bat || ""} ${n.tinh_thanh} ${n.khu_vuc || ""} ${n.dia_danh_nguon || ""}`).includes(k0);
  const goc = useMemo(() => tat.filter((n: any) => (!q.tinh || n.tinh_thanh === q.tinh) && coTim(n)), [tat, q.tinh, k0]);  // eslint-disable-line react-hooks/exhaustive-deps
  const conBan = (n: any) => n.mo_dat && trongGio(n.gio_phuc_vu, q.gio);
  const khop = (n: any, bo?: keyof Loc) => {
    const L = loc;
    if (bo !== "dat" && L.dat && !n.mo_dat) return false;
    if (bo !== "con" && L.con && !conBan(n)) return false;
    if (bo !== "at" && L.at.length && !L.at.includes(n.am_thuc)) return false;
    if (bo !== "gia" && L.gia.length && !(n.gia_tu != null && GIA.some(([k, , f]) => L.gia.includes(k) && f(n.gia_tu)))) return false;
    if (bo !== "ph" && L.ph.length && !L.ph.every((k) => n[k])) return false;
    if (bo !== "loai" && L.loai.length && !L.loai.every((k) => LOAI.find((x) => x[0] === k)?.[2](n))) return false;
    if (bo !== "ten" && L.ten && !khongDau(n.ten).includes(khongDau(L.ten))) return false;
    return true;
  };
  const loc2 = useMemo(() => {
    let r = goc.filter((n: any) => khop(n));
    if (banDo && theoKhung && khung) r = r.filter((n: any) => n.vi_do != null && n.vi_do >= khung.s && n.vi_do <= khung.n && n.kinh_do >= khung.w && n.kinh_do <= khung.e);
    const gia = (n: any, mac: number) => n.gia_tu ?? mac;
    const f: Record<string, (a: any, b: any) => number> = {
      phu_hop: (a, b) => (+!a.mo_dat) - (+!b.mo_dat) || (+!a.anh) - (+!b.anh) || (b.sao?.diem_tb || 0) - (a.sao?.diem_tb || 0) || a.ten.localeCompare(b.ten),
      gia_thap: (a, b) => gia(a, 9e12) - gia(b, 9e12), gia_cao: (a, b) => gia(b, -1) - gia(a, -1),
      diem: (a, b) => (b.sao?.diem_tb || 0) - (a.sao?.diem_tb || 0) || (b.sao?.so_bai || 0) - (a.sao?.so_bai || 0), ten: (a, b) => a.ten.localeCompare(b.ten),
    };
    return [...r].sort(f[sx]);
  }, [goc, loc, sx, banDo, theoKhung, khung, q.gio]);  // eslint-disable-line react-hooks/exhaustive-deps
  const dem = (f: (n: any) => boolean, bo: keyof Loc) => goc.filter((n: any) => khop(n, bo) && f(n)).length;
  const bat = (ds_: string[], k: string, v: boolean) => (v ? [...ds_, k] : ds_.filter((x) => x !== k));
  const ck = (on: boolean, doi: (v: boolean) => void, t: React.ReactNode, so: number, id: string) =>
    <label key={id} className="ksv-chk"><input type="checkbox" checked={on} onChange={(e) => doi(e.target.checked)} /><span>{t}</span><small>{so}</small></label>;
  const nhom = (tieuDe: string, muc: [string, React.ReactNode, (n: any) => boolean][], khoa: "at" | "gia" | "ph" | "loai") => {
    const co = muc.filter(([, , f]) => dem(f, khoa) > 0);
    return co.length > 0 && <div className="ksv-panel"><b>{tieuDe}</b>{co.map(([m, t, f]) =>
      ck((loc[khoa] as string[]).includes(m), (v) => setLoc({ ...loc, [khoa]: bat(loc[khoa] as string[], m, v) }), t, dem(f, khoa), `${khoa}${m}`))}</div>;
  };
  const ghim: Ghim[] = loc2.filter((n: any) => n.vi_do != null).map((n: any) => ({ id: n.id, vi_do: n.vi_do, kinh_do: n.kinh_do, nhan: n.mo_dat && n.gia_tu ? giaGon(n.gia_tu) : "Xem" }));
  const tps: [string, number][] = Object.entries(ds?.dem_tinh || {}).sort((a: any, b: any) => b[1] - a[1]) as any;

  // ---------- đặt bàn: số do máy chủ tính lại; ở đây chỉ hiện để khách hình dung ----------
  const ts = ds?.tham_so;
  const td = nh?.thuc_don?.find((t: any) => t.id === chon.td);
  const tam = td ? td.gia_nguoi_lon * q.nl + (td.gia_tre_em || 0) * q.te : 0;
  const doan = !!(ts && td && q.nl + q.te >= ts.doan_tu && td.loai !== "goi_mon");
  const pct = ts ? (doan ? ts.coc_doan : ts.coc_le) : 0;
  const traTruoc = kh.cach === "du" ? tam : Math.min(tam, nghin(tam * pct / 100));
  const moTt = !!nh?.mo_thanh_toan;
  const gui = async () => {
    setLoi("");
    if (!td) { setLoi("Chọn một thực đơn"); return; }
    if (td.so_khach_toi_thieu > q.nl + q.te) { setLoi(`Gói này tối thiểu ${td.so_khach_toi_thieu} khách`); return; }
    if (!kh.dongy) { setLoi("Đánh dấu ô đồng ý chính sách thanh toán và hủy bàn"); return; }
    if (!moTt) return;
    setBusy(true);
    try {
      const r = await goiCong("/dat-ban", { nha_hang_id: nh.id, thuc_don_id: td.id, ngay: q.ngay, gio: chon.gio, nguoi_lon: q.nl, tre_em: q.te,
        cach_tt: kh.cach, ten_khach: kh.ten_khach, dien_thoai: kh.sdt, ghi_chu: [kh.dip, kh.ghi].filter(Boolean).join(" · "),
        dong_y_chinh_sach: kh.dongy, dong_y_khach: kh.dongy_khach });
      setXong({ ...r, ten: nh.ten, ngay: q.ngay, gio: chon.gio, nguoi: q.nl + q.te, td: td.ten, tam, traTruoc, dia_chi: [nh.khu_vuc, nh.tinh_thanh].filter(Boolean).join(", ") });
      setBuoc("xong"); window.scrollTo(0, 0);
      QRCode.toDataURL(r.ma, { margin: 1, width: 200, errorCorrectionLevel: "M" }).then(setQrMa).catch(() => setQrMa(""));
    } catch (x: any) { if (x.status !== 401) setLoi(x.message); } finally { setBusy(false); }
  };

  const css = <style dangerouslySetInnerHTML={{ __html: CSS_KSV + CSS }} />;
  if (!ds) return <div className="ksv nhv">{css}<p>{loi || "Đang tải nhà hàng…"}</p></div>;

  const thanhTim = (gon = false) => <form className={`nhv-hero${gon ? " gon" : ""}`} onSubmit={(e) => { e.preventDefault(); setBuoc("ds"); setNh(null); setLoc({ ...loc }); }}>
    {!gon && <><b className="nhv-ht">Bàn đẹp ở {ds.tong_nha_hang} nhà hàng · đặc sản {Object.keys(ds.dem_tinh || {}).length} thành phố</b>
      <span className="nhv-hs">Giá hợp đồng của Vietourist · đặt cọc hoặc trả trước · tích điểm VTD</span></>}
    <div className="nhv-sbar">
      <label className="ksv-sbox"><span style={{ flex: 1, minWidth: 0 }}><small>Thành phố, món, tên nhà hàng</small>
        <input value={q.q} onChange={(e) => setQ({ ...q, q: e.target.value })} placeholder="Lẩu riêu cua, Hội An, 1946…" list="nhv-goiy" aria-label="Tìm theo món, thành phố, tên nhà hàng" /></span></label>
      <datalist id="nhv-goiy">{tat.slice(0, 400).map((n: any) => <option key={n.id} value={n.ten} />)}{tps.map(([t]) => <option key={t} value={t} />)}</datalist>
      <label className="ksv-sbox"><span style={{ flex: 1 }}><small>Thành phố</small><select value={q.tinh} onChange={(e) => setQ({ ...q, tinh: e.target.value })} aria-label="Thành phố">
        <option value="">Tất cả ({ds.tong_nha_hang})</option>{tps.map(([t, s]) => <option key={t} value={t}>{t} ({s})</option>)}</select></span></label>
      <label className="ksv-sbox"><span style={{ flex: 1 }}><small>Ngày · {ngayDep(q.ngay)}</small><input type="date" value={q.ngay} min={themNgay(homNay, 1)} onChange={(e) => e.target.value && setQ({ ...q, ngay: e.target.value })} /></span></label>
      <label className="ksv-sbox"><span style={{ flex: 1 }}><small>Giờ</small><select value={q.gio} onChange={(e) => { setQ({ ...q, gio: e.target.value }); setChon({ ...chon, gio: e.target.value }); }} aria-label="Giờ">
        {khungGio("").concat(["06:30", "07:00", "07:30", "08:00"]).sort().map((g) => <option key={g} value={g}>{g}</option>)}</select></span></label>
      <div className="ksv-sbox nhv-khach"><span style={{ flex: 1 }}><small>Khách</small>
        <span className="nhv-so"><button type="button" aria-label="Bớt người lớn" onClick={() => setQ({ ...q, nl: Math.max(1, q.nl - 1) })}>−</button><b>{q.nl} NL</b>
          <button type="button" aria-label="Thêm người lớn" onClick={() => setQ({ ...q, nl: Math.min(200, q.nl + 1) })}>+</button>
          <button type="button" aria-label="Bớt trẻ em" onClick={() => setQ({ ...q, te: Math.max(0, q.te - 1) })}>−</button><b>{q.te} TE</b>
          <button type="button" aria-label="Thêm trẻ em" onClick={() => setQ({ ...q, te: Math.min(100, q.te + 1) })}>+</button></span></span></div>
      <button className="ksv-btn-tim" type="submit">TÌM BÀN</button></div>
    {!gon && <div className="nhv-chips">{LOAI.map(([k, t, f]) => tat.some(f) && <button key={k} type="button" className={`nhv-chip${loc.loai.includes(k) ? " on" : ""}`}
      aria-pressed={loc.loai.includes(k)} onClick={() => setLoc({ ...loc, loai: bat(loc.loai, k, !loc.loai.includes(k)) })}>{t}</button>)}</div>}
  </form>;

  // ============================== 7 · ĐÃ GỬI ĐẶT BÀN ==============================
  if (buoc === "xong" && xong) return <div className="ksv nhv">{css}
    <div className="ksv-steps"><span className="xong"><b>✓</b>Thông tin khách</span><hr /><span className="xong"><b>✓</b>Cách thanh toán</span><hr /><span className="on"><b>3</b>Đã gửi đặt bàn</span></div>
    <section className="ksv-panel nhv-xong">
      <div className="nhv-xong-dau"><div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <span className="ksv-b out" style={{ alignSelf: "flex-start", whiteSpace: "normal", fontSize: 13 }}><b>Đã gửi · chờ nhà hàng nhận bàn {xong.ma}</b></span>
        <h2 style={{ margin: 0, fontSize: 24 }}>{xong.ten}</h2>
        <span>{ngayDep(xong.ngay)} · {xong.gio} · {xong.nguoi} khách · {xong.td}</span>
        <span className="ksv-muted">{xong.message}</span>
        <span className="ksv-muted">Trả trước dự kiến ₫ {vnd(xong.traTruoc)} · phần còn lại trả tại nhà hàng theo hóa đơn thực tế.</span></div>
        {qrMa && <figure className="nhv-qr"><img src={qrMa} alt={`Mã đặt bàn ${xong.ma}`} width={140} height={140} /><figcaption>Đưa mã này cho nhà hàng</figcaption></figure>}</div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" className="ksv-btn line" onClick={() => taiLich({ ma: xong.ma, ten: xong.ten, ngay: xong.ngay, gio: xong.gio, dia_chi: xong.dia_chi, nguoi: xong.nguoi })}>Thêm vào lịch</button>
        <a className="ksv-btn line nhv-a" href={chiDuong(nh || {})} target="_blank" rel="noopener noreferrer">Chỉ đường trên Google Maps</a>
        <button type="button" className="ksv-btn" onClick={() => { setBuoc("ds"); setNh(null); setXong(null); }}>Tìm nhà hàng khác</button></div>
      <ol className="nhv-tiep"><li>Nhà hàng nhận bàn (thường trong giờ làm việc).</li><li>Nút <b>Thanh toán</b> hiện ở đơn bên dưới — trả cọc / trả đủ bằng QR hoặc thẻ trước hạn.</li>
        <li>Đổi giờ hoặc hủy theo chính sách ngay trong đơn.</li></ol>
    </section>
    <section className="ksv-panel"><b style={{ fontSize: 18 }}>Đặt bàn của tôi</b><DatBanCuaToi doiTac={doiTac} moMa={xong.ma} /></section>
  </div>;

  // ============================== 5–6 · THÔNG TIN KHÁCH + THANH TOÁN ==============================
  if (buoc === "dat" && nh && td) return <div className="ksv nhv">{css}
    <div className="ksv-steps"><span className="on"><b>1</b>Thông tin khách</span><hr /><span className="on"><b>2</b>Cách thanh toán</span><hr /><span><b>3</b>Xác nhận</span>
      <button type="button" className="ksv-link" style={{ marginLeft: "auto" }} onClick={() => setBuoc("nh")}>← Quay lại chọn giờ</button></div>
    <div className="ksv-co">
      <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
        <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>Ai đến ăn?</h2>
          {doiTac ? <div className="ksv-f2">
            <label className="ksv-fld">Tên khách<input value={kh.ten_khach} onChange={(e) => setKh({ ...kh, ten_khach: e.target.value })} autoComplete="name" /></label>
            <label className="ksv-fld">Số điện thoại khách<input inputMode="tel" value={kh.sdt} placeholder="09xx xxx xxx" onChange={(e) => setKh({ ...kh, sdt: e.target.value })} /></label></div>
            : <div className="ksv-f2">
              <div className="ksv-fld">Người đặt<div className="nhv-ro">{ten || "Khách hàng Vietourist"}{lienHe ? ` · ${lienHe}` : ""}</div></div>
              <label className="ksv-fld">Số điện thoại liên hệ{coSdt ? " (trống = số đã xác thực)" : ""}<input inputMode="tel" value={kh.sdt} placeholder={coSdt ? sdtCho : "09xx xxx xxx"} onChange={(e) => setKh({ ...kh, sdt: e.target.value })} autoComplete="tel" /></label></div>}
          <div className="ksv-f2">
            <label className="ksv-fld">Dịp đặc biệt<select className="ksv-sel" value={kh.dip} onChange={(e) => setKh({ ...kh, dip: e.target.value })}>
              {["", "Sinh nhật", "Kỷ niệm", "Gặp gỡ công việc", "Gia đình có trẻ nhỏ"].map((x) => <option key={x} value={x}>{x || "Không có"}</option>)}</select></label>
            <label className="ksv-fld">Ghi chú cho nhà hàng<textarea value={kh.ghi} maxLength={800} placeholder="Ăn chay, ghế trẻ em, dị ứng…" onChange={(e) => setKh({ ...kh, ghi: e.target.value })} /></label></div>
          {doiTac && <label className="ksv-chk"><input type="checkbox" checked={kh.dongy_khach} onChange={(e) => setKh({ ...kh, dongy_khach: e.target.checked })} /><span>Khách đã đồng ý để tôi chuyển thông tin cho Vietourist.</span></label>}
        </section>
        <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Cách thanh toán</h2>
          {[["coc", `Đặt cọc ${pct}%`, `Trả ₫ ${vnd(Math.min(tam, nghin(tam * pct / 100)))} sau khi nhà hàng nhận bàn, phần còn lại trả tại nhà hàng.`],
            ["du", "Trả trước toàn bộ", `₫ ${vnd(tam)} · QR chuyển khoản hoặc thẻ (cổng SePay).`]].map(([v, t, m]) =>
            <label key={v} className={`nhv-pay${kh.cach === v ? " on" : ""}`}><input type="radio" name="nhv-tt" checked={kh.cach === v} onChange={() => setKh({ ...kh, cach: v })} />
              <span><b>{t}</b><br /><small className="ksv-muted">{m}</small></span></label>)}
          {doan && <small className="ksv-muted">Từ {ts.doan_tu} khách là đoàn: cọc {ts.coc_doan}%.</small>}
          {ts && <small className="ksv-muted">Hủy trước {ts.mien_phi_gio} giờ: hoàn đủ. Trong {ts.mien_phi_gio} giờ: giữ {ts.phat}% hóa đơn. Dưới {ts.gan_gio} giờ hoặc không đến: khách lẻ giữ {ts.phat}%, đoàn giữ {ts.phat_doan_gan}%. Không giữ quá số đã trả. Nhà hàng hủy: hoàn đủ.</small>}
          <small className="ksv-muted">Voucher VTD Rewards áp ở bước thanh toán (sau khi nhà hàng nhận bàn), tối đa 5% tạm tính.</small>
        </section>
        {loi && <div className="ksv-loi">{loi}</div>}
        <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "16px 20px" }}>
          <label className="ksv-chk" style={{ flex: 1, minWidth: 220, alignItems: "flex-start" }}><input type="checkbox" checked={kh.dongy} onChange={(e) => setKh({ ...kh, dongy: e.target.checked })} />
            <span style={{ fontSize: 13 }}>Tôi đồng ý chính sách thanh toán và hủy bàn. Nhà hàng nhận bàn xong mới hiện thanh toán; bàn chỉ giữ khi tiền đã vào.</span></label>
          {moTt ? <button type="button" className="ksv-btn" style={{ minHeight: 52, padding: "0 28px", fontSize: 16 }} disabled={busy || (doiTac && !kh.dongy_khach)} onClick={gui}>
            {busy ? "Đang gửi…" : `Gửi đặt bàn · trả trước ₫ ${vnd(traTruoc)}`}</button>
            : <button type="button" className="ksv-btn ksv-khoa" disabled style={{ minHeight: 52, padding: "0 24px", fontSize: 15 }}>Thanh toán trực tuyến sắp mở cho nhà hàng này</button>}</div>
        {!moTt && <small className="ksv-muted">Vietourist đang hoàn tất hợp tác với nhà hàng này. Bạn chưa phải trả gì và chưa có bàn nào được giữ.</small>}
      </div>
      <aside className="ksv-panel nhv-tom" aria-label="Tóm tắt đặt bàn">
        {nh.anh_nho ? <img src={nh.anh_nho} alt={nh.ten} className="nhv-tom-anh" /> : <OTrong n={nh} cao={120} />}
        <b style={{ fontSize: 17 }}>{nh.ten}</b><span className="ksv-muted">{[nh.khu_vuc, nh.tinh_thanh].filter(Boolean).join(", ")}</span>
        <div className="nhv-tom-o"><span>{ngayDep(q.ngay)}</span><span>{chon.gio}</span><span>{q.nl} NL{q.te ? ` + ${q.te} TE` : ""}</span></div>
        <div className="ksv-sum"><span>{td.ten} · NL × {q.nl}</span><span>₫ {vnd(td.gia_nguoi_lon * q.nl)}</span></div>
        {q.te > 0 && <div className="ksv-sum"><span>Trẻ em × {q.te}</span><span>₫ {vnd((td.gia_tre_em || 0) * q.te)}</span></div>}
        <div className="ksv-sum"><span>Tạm tính</span><span>₫ {vnd(tam)}</span></div>
        {/* P0-05: nhắc lại điều kiện riêng của gói ngay trước nút gửi (bước chọn gói có thể đã bị lướt qua) */}
        {(td.dieu_kien || td.dieu_kien_huy) && <small className="nhv-dk"><b>Điều kiện của gói:</b> {[td.dieu_kien, td.dieu_kien_huy].filter(Boolean).join(" · ")}</small>}
        <div className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 8 }}><b>Trả trước {kh.cach === "du" ? "(toàn bộ)" : `(cọc ${pct}%)`}</b><b className="ksv-big" style={{ fontSize: 20 }}>₫ {vnd(traTruoc)}</b></div>
        <small className="ksv-muted">Trả tại nhà hàng ~₫ {vnd(Math.max(0, tam - traTruoc))} · đồ uống, món gọi thêm theo hóa đơn thực tế. Máy chủ tính lại số chính thức.</small>
      </aside>
    </div></div>;

  // ============================== 3–4 · TRANG NHÀ HÀNG + CHỌN GIỜ / THỰC ĐƠN ==============================
  if (buoc === "nh" && nh) {
    const al: any[] = nh.album || [];
    const nhoms = Array.from(new Map(al.map((a) => [a.nhom, a.nhom_ten || "Ảnh"])).entries());
    const vids: any[] = nh.video || [];
    const gios = khungGio(nh.gio_phuc_vu);
    const khongGian = al.filter((a) => ["khong_gian", "phong_rieng", "mat_tien"].includes(a.nhom));
    const mons: any[] = (nh.mon || []).filter((m: any) => m.noi_bat).concat((nh.mon || []).filter((m: any) => !m.noi_bat)).slice(0, 8);
    const anhAl = album ? al.filter((a) => !album.nhom || a.nhom === album.nhom) : [];
    return <div className="ksv nhv">{css}{thanhTim(true)}
      <button type="button" className="ksv-link" onClick={() => { setBuoc("ds"); setNh(null); }}>← Nhà hàng{q.tinh ? ` ở ${q.tinh}` : ""}</button>
      <div className="ksv-gal nhv-gal">{al.length ? <>
        {al.slice(0, 5).map((a, i) => <span key={a.id}><button type="button" className="ksv-phbtn" onClick={() => setAlbum({ nhom: "", i })} aria-label={`Xem ảnh ${i + 1}`}>
          <img src={i ? a.nho : a.hien} alt={a.alt || `${nh.ten} — ${a.nhom_ten}`} loading="lazy" /></button>
          {i === 0 && vids.length > 0 && <em className="nhv-vbad">▶ {vids.length} video</em>}</span>)}
        <button type="button" className="nhv-xem" onClick={() => setAlbum({ nhom: "", i: null })}>Xem tất cả {al.length} ảnh{vids.length ? ` · ${vids.length} video` : ""}</button></>
        : <span style={{ gridColumn: "1 / -1", gridRow: "1 / 3" }}><OTrong n={nh} cao={260} /></span>}</div>
      <nav className="ksv-tabs" aria-label="Mục của trang nhà hàng">{[["nhv-tq", "Tổng quan"], ["nhv-td", "Thực đơn"], ["nhv-kg", "Không gian"], ["nhv-dg", "Đánh giá"], ["nhv-vt", "Vị trí"], ["nhv-cs", "Chính sách"]].map(([id, t]) =>
        <a key={id} href={`#${id}`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); }}>{t}</a>)}
        <span className="ksv-tp">{nh.mo_dat && nh.gia_tu ? <><small className="ksv-muted">từ</small><b className="ksv-big" style={{ fontSize: 19 }}>₫ {vnd(nh.gia_tu)}</b><small className="ksv-muted">/ người</small></> : null}
          <button type="button" className="ksv-btn" onClick={() => document.getElementById("nhv-td")?.scrollIntoView({ behavior: "smooth" })}>{nh.mo_dat ? "Chọn giờ" : "Xem thực đơn"}</button></span></nav>
      <div className="ksv-two" id="nhv-tq">
        <div className="ksv-panel" style={{ padding: 20 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}><h2 style={{ margin: 0, fontSize: 26 }}>{nh.ten}</h2>
            <span className="nhv-tag">{nh.am_thuc}</span>{nh.mo_dat ? <span className="nhv-tag ok">Đặt qua Vietourist · tích điểm</span> : <span className="nhv-tag muted">Chưa mở đặt bàn trực tuyến</span>}</div>
          <NhanPl n={nh} />
          <span className="ksv-where" style={{ fontWeight: 500, color: "inherit" }}>{[nh.khu_vuc, nh.tinh_thanh].filter(Boolean).join(", ")}
            {" · "}<a className="ksv-link" href="#nhv-vt" onClick={(e) => { e.preventDefault(); document.getElementById("nhv-vt")?.scrollIntoView({ behavior: "smooth" }); }}>XEM VỊ TRÍ</a></span>
          <div className="nhv-hl">
            {nh.mon_noi_bat && <div><b>Món nên thử</b><span>{nh.mon_noi_bat}</span></div>}
            <div><b>Giờ phục vụ</b><span>{nh.gio_phuc_vu || "Đang cập nhật"}</span></div>
            {nh.tien_ich && <div><b>Tiện ích</b><span>{nh.tien_ich}</span></div>}
            {nh.dac_san && <div><b>Đặc sản địa phương</b><span>Nổi tiếng với món đặc trưng của {nh.tinh_thanh}</span></div>}
            {nh.michelin && <div><b>Michelin</b><span>{nh.michelin}</span></div>}
          </div>
          <p style={{ margin: "4px 0 0", fontSize: 15, lineHeight: 1.65, whiteSpace: "pre-line", maxWidth: "70ch" }}>{nh.mo_ta || "Vietourist đang biên tập phần giới thiệu nhà hàng này."}</p>
        </div>
        <div className="ksv-panel"><b>Khách đánh giá</b><SaoThe sao={nh.danh_gia?.tom_tat ? { so_bai: nh.danh_gia.tom_tat.so_bai, diem_tb: nh.danh_gia.tom_tat.diem_tb } : nh.sao} />
          <small className="ksv-muted">Chỉ khách đã đặt và dùng bữa qua Vietourist mới viết được.</small>
          {nh.vi_do != null && <BanDo ghim={[{ id: nh.id, vi_do: nh.vi_do, kinh_do: nh.kinh_do, nhan: nh.ten }]} mot cao={180} />}
          <a className="ksv-btn line nhv-a" href={chiDuong(nh)} target="_blank" rel="noopener noreferrer">Chỉ đường trên Google Maps</a></div>
      </div>

      <section className="ksv-panel nhv-dat" id="nhv-td"><div className="ksv-rhead"><h2 style={{ margin: 0, fontSize: 22 }}>Thực đơn và giờ đến</h2>
        <span className="ksv-muted">{ngayDep(q.ngay)} · {q.nl} người lớn{q.te ? ` · ${q.te} trẻ em` : ""}</span></div>
        {loi && <div className="ksv-loi">{loi}</div>}
        {nh.mo_dat && nh.thuc_don?.length ? <>
          <div className="nhv-f"><label className="ksv-fld">Ngày<input type="date" value={q.ngay} min={themNgay(homNay, 1)} onChange={(e) => e.target.value && setQ({ ...q, ngay: e.target.value })} /></label>
            <div className="ksv-fld">Khách<span className="nhv-so nhv-so2"><button type="button" aria-label="Bớt người lớn" onClick={() => setQ({ ...q, nl: Math.max(1, q.nl - 1) })}>−</button><b>{q.nl} người lớn</b>
              <button type="button" aria-label="Thêm người lớn" onClick={() => setQ({ ...q, nl: q.nl + 1 })}>+</button>
              <button type="button" aria-label="Bớt trẻ em" onClick={() => setQ({ ...q, te: Math.max(0, q.te - 1) })}>−</button><b>{q.te} trẻ em</b>
              <button type="button" aria-label="Thêm trẻ em" onClick={() => setQ({ ...q, te: q.te + 1 })}>+</button></span></div></div>
          <div><b style={{ fontSize: 14 }}>Giờ đến</b><div className="nhv-slots" role="group" aria-label="Giờ đến">{gios.map((g) =>
            <button key={g} type="button" className={`nhv-slot${chon.gio === g ? " on" : ""}`} aria-pressed={chon.gio === g} onClick={() => setChon({ ...chon, gio: g })}>{g}</button>)}</div>
            <small className="ksv-muted">Khung giờ theo giờ phục vụ của nhà hàng. Nhà hàng xác nhận bàn sau khi nhận đơn.</small></div>
          <div className="nhv-menu">{nh.thuc_don.map((t: any) => { const thieu = t.so_khach_toi_thieu > q.nl + q.te;
            return <button key={t.id} type="button" className={`nhv-mn${chon.td === t.id ? " on" : ""}`} aria-pressed={chon.td === t.id} onClick={() => setChon({ ...chon, td: t.id })}>
              <span className="nhv-tag">{t.loai_ten}</span><b>{t.ten}</b>{t.mo_ta && <small className="ksv-muted">{t.mo_ta}</small>}
              <span className="ksv-big" style={{ fontSize: 19 }}>₫ {vnd(t.gia_nguoi_lon)}<small className="ksv-muted" style={{ fontWeight: 400 }}> / người lớn</small></span>
              {t.gia_tre_em != null && <small className="ksv-muted">Trẻ em ₫ {vnd(t.gia_tre_em)}</small>}
              {t.so_khach_toi_thieu > 1 && <small className={thieu ? "nhv-warn" : "ksv-muted"}>Tối thiểu {t.so_khach_toi_thieu} khách</small>}
              {(t.dieu_kien || t.dieu_kien_huy) && <small className="ksv-muted">{[t.dieu_kien, t.dieu_kien_huy].filter(Boolean).join(" · ")}</small>}</button>; })}</div>
          {td && <div className="ksv-total"><span style={{ flex: 1, minWidth: 180 }}><b>{td.ten} · {ngayDep(q.ngay)} {chon.gio} · {q.nl + q.te} khách</b><br />
            <small className="ksv-muted">Tạm tính ₫ {vnd(tam)} · trả trước từ ₫ {vnd(Math.min(tam, nghin(tam * pct / 100)))} (cọc {pct}%)</small></span>
            <button type="button" className="ksv-btn" style={{ minHeight: 50, padding: "0 26px", fontSize: 16 }} disabled={td.so_khach_toi_thieu > q.nl + q.te}
              onClick={() => { setLoi(""); setBuoc("dat"); window.scrollTo(0, 0); }}>Đặt bàn</button></div>}
        </> : <div className="nhv-chua"><b>Nhà hàng chưa mở đặt bàn qua Vietourist</b><span className="ksv-muted">Vietourist đang hoàn tất hợp tác. Bạn vẫn xem thực đơn, ảnh và chỉ đường.</span></div>}
        {(nh.thuc_don_nh || []).map((b: any) => <details key={b.loai} className="nhv-tdnh"><summary>{b.ten} · bản {b.ban} ({b.trang.length} trang)</summary>
          <div className="nhv-tdnh-tr">{b.trang.map((t: any, i: number) => <a key={i} href={t.hien} target="_blank" rel="noopener noreferrer"><img src={t.nho} alt={`${b.ten} trang ${i + 1}`} loading="lazy" /></a>)}</div></details>)}
        {mons.length > 0 && <><b style={{ fontSize: 16 }}>Món nên thử</b><div className="nhv-mons">{mons.map((m) => <div key={m.id} className="nhv-mon">
          {m.anh_nho ? <img src={m.anh_nho} alt={m.ten} loading="lazy" /> : <span className="nhv-mon-o">{m.ten.charAt(0)}</span>}
          <b>{m.ten}</b><small className="ksv-muted">{[m.nhom_ten, m.chay ? "Chay" : "", m.cay ? "Cay" : ""].filter(Boolean).join(" · ")}</small></div>)}</div></>}
      </section>

      <section className="ksv-panel" id="nhv-kg"><b style={{ fontSize: 18 }}>Không gian</b>
        {khongGian.length ? <div className="nhv-kg">{khongGian.slice(0, 8).map((a) => <button key={a.id} type="button" className="ksv-phbtn" onClick={() => setAlbum({ nhom: a.nhom, i: null })}>
          <img src={a.nho} alt={a.alt || a.nhom_ten} loading="lazy" /><small>{a.nhom_ten}</small></button>)}</div>
          : <span className="ksv-muted">Ảnh không gian đang cập nhật.</span>}
        {vids.length > 0 && <div className="nhv-kg">{vids.slice(0, 3).map((v) => <div key={v.id} style={{ aspectRatio: "16 / 9" }}><VideoO v={v} ten={nh.ten} /></div>)}</div>}</section>
      <section id="nhv-dg"><DanhGiaNhaHangKhach dau={nh.danh_gia} nhId={nh.id} /></section>
      <section className="ksv-panel" id="nhv-vt"><b style={{ fontSize: 18 }}>Vị trí</b><span>{[nh.khu_vuc, nh.tinh_thanh].filter(Boolean).join(", ")}</span>
        {nh.vi_do != null ? <BanDo ghim={[{ id: nh.id, vi_do: nh.vi_do, kinh_do: nh.kinh_do, nhan: nh.ten }]} mot cao={300} /> : <span className="ksv-muted">Vị trí trên bản đồ đang cập nhật.</span>}
        <a className="ksv-btn line nhv-a" style={{ alignSelf: "flex-start" }} href={chiDuong(nh)} target="_blank" rel="noopener noreferrer">Chỉ đường trên Google Maps</a></section>
      <section className="ksv-panel" id="nhv-cs"><b style={{ fontSize: 18 }}>Chính sách</b>
        {ts && <><span><b>Đặt cọc</b> khách lẻ {ts.coc_le}% · đoàn từ {ts.doan_tu} khách {ts.coc_doan}% tạm tính, hoặc trả trước toàn bộ.</span>
          <span><b>Hủy bàn</b> trước {ts.mien_phi_gio} giờ hoàn đủ · trong {ts.mien_phi_gio} giờ giữ {ts.phat}% hóa đơn · dưới {ts.gan_gio} giờ hoặc không đến: khách lẻ {ts.phat}%, đoàn {ts.phat_doan_gan}%. Không giữ quá số đã trả.</span>
          <span><b>Đổi giờ</b> báo trước {ts.mien_phi_gio} giờ, đổi miễn phí 1 lần.</span></>}
        <span><b>Hạn trả</b> sau khi nhà hàng nhận bàn{ts ? `, trong ${ts.han_tra_gio} giờ` : ""}; quá hạn chưa trả thì bàn không được giữ.</span></section>

      {album && createPortal(<div className="nhv-al" role="dialog" aria-modal="true" aria-label={`Album ảnh ${nh.ten}`}>
        <div className="nhv-al-dau"><b>{nh.ten}</b>
          <div className="nhv-al-tabs">{[["", `Tất cả (${al.length})`], ...nhoms.map(([k, t]) => [k, `${t} (${al.filter((a) => a.nhom === k).length})`]), ...(vids.length ? [["__video", `Video (${vids.length})`]] : [])].map(([k, t]) =>
            <button key={k} type="button" className={album.nhom === k ? "on" : ""} onClick={() => setAlbum({ nhom: k, i: null })}>{t}</button>)}</div>
          <button type="button" className="nhv-al-x" aria-label="Đóng album" onClick={() => setAlbum(null)}>✕</button></div>
        {album.nhom === "__video" ? <div className="nhv-al-luoi">{vids.map((v) => <div key={v.id} style={{ aspectRatio: "16 / 9" }}><VideoO v={v} ten={nh.ten} /></div>)}</div>
          : album.i != null && anhAl[album.i] ? <div className="nhv-al-mot">
            <button type="button" aria-label="Ảnh trước" onClick={() => setAlbum({ ...album, i: (album.i! - 1 + anhAl.length) % anhAl.length })}>‹</button>
            <figure><img src={anhAl[album.i].hien} alt={anhAl[album.i].alt || nh.ten} /><figcaption>{[anhAl[album.i].nhom_ten, anhAl[album.i].chu_thich].filter(Boolean).join(" · ")} · {album.i + 1}/{anhAl.length}{anhAl[album.i].credit ? ` · ${anhAl[album.i].credit}` : ""}</figcaption></figure>
            <button type="button" aria-label="Ảnh tiếp" onClick={() => setAlbum({ ...album, i: (album.i! + 1) % anhAl.length })}>›</button></div>
          : <div className="nhv-al-luoi">{anhAl.map((a, i) => <button key={a.id} type="button" className="ksv-phbtn" onClick={() => setAlbum({ ...album, i })}><img src={a.nho} alt={a.alt || a.nhom_ten} loading="lazy" /></button>)}</div>}
      </div>, document.body)}
    </div>;
  }

  // ============================== 1–2 · TÌM + DANH SÁCH + BẢN ĐỒ ==============================
  const L = loc;
  const danhSach = <main style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
    <div className="ksv-rhead"><h2 style={{ margin: 0, fontSize: 22 }}>{loc2.length} nhà hàng{q.tinh ? ` tại ${q.tinh}` : ""}</h2>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className="ksv-btn line ksv-fbtn" onClick={() => setMoLoc(true)}>Bộ lọc</button>
        <button type="button" className="ksv-btn line" aria-pressed={banDo} onClick={() => { setBanDo(!banDo); setTheoKhung(false); }}>{banDo ? "Ẩn bản đồ" : "Xem trên bản đồ"}</button>
        <select className="ksv-sel" value={sx} onChange={(e) => setSx(e.target.value)} aria-label="Sắp xếp">
          {[["phu_hop", "Phù hợp nhất"], ["gia_thap", "Giá thấp nhất trước"], ["gia_cao", "Giá cao nhất trước"], ["diem", "Điểm khách cao nhất"], ["ten", "Tên A–Z"]].map(([k, t]) =>
            <option key={k} value={k}>Sắp xếp: {t}</option>)}</select></div></div>
    {loi && <div className="ksv-loi">{loi}</div>}
    {!loc2.length && <div className="ksv-panel" style={{ textAlign: "center" }}><b>Không có nhà hàng khớp tìm kiếm và bộ lọc.</b>
      <button type="button" className="ksv-btn line" onClick={() => { setLoc(LOC0); setQ({ ...q, q: "", tinh: "" }); }}>Xóa tìm kiếm và bộ lọc</button></div>}
    {loc2.slice(0, 120).map((n: any) => {
      const ds_ = n.anh_ds?.length ? n.anh_ds : n.anh_nho ? [n.anh_nho] : [];
      const i = (anhI[n.id] || 0) % Math.max(1, ds_.length);
      return <article key={n.id} className={`ksv-card${chonBd === n.id ? " ksv-card-on" : ""}`} id={`nhv-c${n.id}`}>
        {n.mo_dat && <div className="ksv-bar"><span>Giá hợp đồng của Vietourist · tích điểm VTD</span>{n.dac_san && <em>Đặc sản</em>}{n.phong_rieng && <em>Phòng riêng</em>}</div>}
        <div className="ksv-crow">
          <div className="ksv-ph"><button type="button" className="ksv-phbtn" onClick={() => moNh(n.id)} aria-label={`Xem ${n.ten}`}>
            {ds_[i] ? <img src={ds_[i]} alt={n.anh_alt || n.ten} loading="lazy" /> : <OTrong n={n} />}</button>
            {ds_.length > 1 && <><button type="button" className="ksv-ico ksv-prv" aria-label="Ảnh trước" onClick={() => setAnhI({ ...anhI, [n.id]: (i - 1 + ds_.length) % ds_.length })}>‹</button>
              <button type="button" className="ksv-ico ksv-nxt" aria-label="Ảnh tiếp" onClick={() => setAnhI({ ...anhI, [n.id]: (i + 1) % ds_.length })}>›</button></>}
            {n.so_anh > 0 && <span className="ksv-ct">{i + 1}/{n.so_anh}</span>}</div>
          <div className="ksv-info"><h3><button type="button" className="ksv-ten" onClick={() => moNh(n.id)}>{n.ten}</button></h3>
            <span className="ksv-muted" style={{ fontSize: 13 }}>{[n.am_thuc, n.tinh_thanh].filter(Boolean).join(" · ")}</span>
            {n.khu_vuc && <span className="ksv-where" style={{ fontSize: 13 }}>{n.khu_vuc}</span>}
            <NhanPl n={n} />
            {n.mon_noi_bat && <span className="ksv-hl">«{String(n.mon_noi_bat).split(/[;,]/).slice(0, 3).join(", ")}»</span>}
            <div className="ksv-feat sm">{n.gia_dinh && <span>Gia đình</span>}{n.tiec && <span>Tiệc / đoàn</span>}{n.goi_mon && <span>Gọi món</span>}{n.vi_do == null && <span>Chưa có vị trí trên bản đồ</span>}</div></div>
          <div className="ksv-side"><SaoThe sao={n.sao} />
            {n.mo_dat && n.gia_tu ? <><small className="ksv-muted" style={{ marginTop: "auto" }}>Thực đơn từ</small><span className="ksv-big">₫ {vnd(n.gia_tu)}</span><small className="ksv-muted">/ người</small>
              {!trongGio(n.gio_phuc_vu, q.gio) && <small className="nhv-warn">Ngoài giờ phục vụ lúc {q.gio}</small>}
              <button type="button" className="ksv-btn wide" onClick={() => moNh(n.id, true)}>Chọn giờ</button></>
              : <><small className="ksv-muted" style={{ marginTop: "auto" }}>Chưa mở đặt trực tuyến</small>
                <button type="button" className="ksv-btn line wide" onClick={() => moNh(n.id)}>Xem nhà hàng</button></>}</div></div></article>;
    })}
    {loc2.length > 120 && <small className="ksv-muted">Hiện 120 / {loc2.length} nhà hàng — chọn thành phố hoặc thêm bộ lọc để thu hẹp.</small>}
  </main>;

  return <div className="ksv nhv">{css}{thanhTim()}
    {!q.tinh && !k0 && tps.length > 0 && <section className="ksv-dd"><b style={{ fontSize: 18 }}>Thành phố ẩm thực</b>
      <div className="ksv-ddr">{tps.slice(0, 12).map(([t, so]) => { const a = tat.find((n: any) => n.tinh_thanh === t && n.anh_nho);
        return <button key={t} type="button" className="ksv-ddc" onClick={() => setQ({ ...q, tinh: t })}>
          {a ? <img src={a.anh_nho} alt={t} loading="lazy" /> : <span className="ph" />}<b>{t}</b><small>{so} nhà hàng</small></button>; })}</div></section>}
    <div className="ksv-layout">
      <aside className={`ksv-loc ${moLoc ? "open" : ""}`} aria-label="Bộ lọc">
        {moLoc && <div className="ksv-rhead"><b style={{ fontSize: 20 }}>Bộ lọc</b><button type="button" className="ksv-btn" onClick={() => setMoLoc(false)}>Xem {loc2.length} nhà hàng</button></div>}
        <label className="ksv-pill"><input placeholder="Tìm theo tên nhà hàng" value={L.ten} onChange={(e) => setLoc({ ...L, ten: e.target.value })} aria-label="Tìm theo tên nhà hàng" /></label>
        {(dem((n) => n.mo_dat, "dat") > 0 || dem(conBan, "con") > 0) && <div className="ksv-panel"><b>Đặt bàn</b>
          {dem((n) => n.mo_dat, "dat") > 0 && ck(L.dat, (v) => setLoc({ ...L, dat: v }), "Đặt được qua Vietourist", dem((n) => n.mo_dat, "dat"), "dat")}
          {dem(conBan, "con") > 0 && ck(L.con, (v) => setLoc({ ...L, con: v }), `Còn bàn lúc ${q.gio}`, dem(conBan, "con"), "con")}</div>}
        {nhom("Ẩm thực", (ds.am_thuc || []).map((a: string) => [a, a, (n: any) => n.am_thuc === a] as [string, string, (n: any) => boolean]), "at")}
        {nhom("Giá mỗi người", GIA.map(([k, t, f]) => [k, t, (n: any) => n.gia_tu != null && f(n.gia_tu)] as [string, string, (n: any) => boolean]), "gia")}
        {nhom("Phù hợp", PH.map(([k, t]) => [k, t, (n: any) => !!n[k]] as [string, string, (n: any) => boolean]), "ph")}
        {nhom("Nổi bật", LOAI.map(([k, t, f]) => [k, t, f]), "loai")}
        <button type="button" className="ksv-btn line" onClick={() => setLoc(LOC0)}>Xóa bộ lọc</button>
      </aside>
      {banDo ? <div className="nhv-mapwrap">
        <div className="ksv-mapbox"><div className="ksv-mapbar"><label className="ksv-chk"><input type="checkbox" checked={theoKhung} onChange={(e) => setTheoKhung(e.target.checked)} /><span>Tìm khi di chuyển bản đồ</span></label>
          <small className="ksv-muted">{ghim.length}/{goc.filter((n: any) => khop(n)).length} nhà hàng có vị trí</small></div>
          <BanDo ghim={ghim} chon={chonBd} onChon={(id) => { setChonBd(id); document.getElementById(`nhv-c${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" }); }} onKhung={setKhung} cao="min(70vh,620px)" /></div>
        {danhSach}</div> : danhSach}
    </div></div>;
}

const CSS = `
.nhv{--ksv-accent:#14538D;--ksv-ink:#14538D}
.nhv-hero{background:linear-gradient(135deg,#0B2545,#1E63C8);border-radius:12px;padding:18px;display:flex;flex-direction:column;gap:12px;color:#fff}
.nhv-hero.gon{padding:10px;background:#14538D}
.nhv-ht{font-size:22px;font-weight:800;text-wrap:balance}.nhv-hs{font-size:13px;opacity:.9;margin-top:-6px}
.nhv-sbar{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) minmax(0,.9fr) minmax(0,.7fr) minmax(0,1.1fr) auto;gap:8px}
.nhv-khach{padding:6px 10px}
.nhv-sbar input[type=date],#vtd-access .nhv .nhv-sbar input[type=date]{color:#23252c;-webkit-text-fill-color:#23252c;min-width:118px;font-size:14px}
.nhv-so{display:flex;align-items:center;gap:4px;flex-wrap:nowrap}.nhv-so b{font-size:14px;white-space:nowrap;padding:0 2px}
.nhv-so button{width:26px;height:26px;border-radius:50%;border:1px solid #e1e4eb;background:#fff;font-size:15px;line-height:1;padding:0;color:#23252c;flex:none}
.nhv-so2{gap:8px;flex-wrap:wrap}.nhv-so2 button{width:32px;height:32px}
.nhv-chips{display:flex;gap:8px;flex-wrap:wrap}
.nhv-chip{border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.1);color:#fff;border-radius:99px;padding:6px 14px;font-weight:600;font-size:13px}
.nhv-chip.on{background:#fff;color:#7a2e1b}
.nhv-tag{display:inline-block;font-size:12px;font-weight:700;padding:3px 9px;border-radius:99px;background:#fbeee0;color:#7a4a22}
.nhv-tag.ok{background:var(--ksv-oksoft);color:var(--ksv-ok)}.nhv-tag.muted{background:var(--ksv-soft);color:var(--ksv-muted)}
.nhv-warn{color:#b45309;font-weight:600}
.nhv .nhv-gal{position:relative;display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:170px 170px;gap:6px;border-radius:12px;overflow:hidden}
.nhv .nhv-gal>span{position:relative;background:var(--ksv-soft);min-width:0}.nhv .nhv-gal>span:first-child{grid-row:span 2;grid-column:auto}.nhv .nhv-gal>span:nth-child(n+6){display:none}
.nhv .nhv-gal img{width:100%;height:100%;object-fit:cover;display:block}
.nhv .nhv-gal .nhv-xem{display:block;z-index:3;position:absolute;right:12px;bottom:12px;border:0;border-radius:99px;background:#fff;color:#23252c;font-weight:700;padding:8px 14px;box-shadow:0 2px 8px rgba(0,0,0,.25)}
.nhv-vbad{position:absolute;left:10px;bottom:10px;background:rgba(20,20,30,.7);color:#fff;font-style:normal;font-size:12px;font-weight:700;padding:3px 9px;border-radius:5px}
.nhv-hl{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.nhv-hl div{background:var(--ksv-soft);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:3px;font-size:14px}
.nhv-hl b{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--ksv-muted)}
.nhv-dat{gap:14px;padding:18px}
.nhv-f{display:grid;grid-template-columns:220px minmax(0,1fr);gap:12px;align-items:end}
.nhv-slots{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 4px}
.nhv-slot{border:1px solid var(--ksv-line);background:#fff;border-radius:8px;padding:8px 12px;font-weight:700;font-size:14px;color:var(--ksv-fg);font-variant-numeric:tabular-nums}
.nhv-slot.on{background:#1E63C8;border-color:#1E63C8;color:#fff}
.nhv-menu{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.nhv-mn{all:unset;box-sizing:border-box;cursor:pointer;border:1px solid var(--ksv-line);border-radius:12px;padding:12px 14px;display:flex;flex-direction:column;gap:5px;background:#fff}
.nhv-mn.on{border-color:#1E63C8;box-shadow:0 0 0 2px #1E63C8}.nhv-mn:focus-visible{outline:2px solid var(--ksv-accent)}
.nhv-mn .nhv-tag{align-self:flex-start}
.nhv-chua{display:flex;flex-direction:column;gap:4px;background:var(--ksv-soft);border-radius:10px;padding:14px}
.nhv-tdnh summary{cursor:pointer;font-weight:600}.nhv-tdnh-tr{display:flex;gap:8px;overflow-x:auto;padding:8px 0}.nhv-tdnh-tr img{height:160px;border-radius:6px;border:1px solid var(--ksv-line)}
.nhv-mons{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.nhv-mon{display:flex;flex-direction:column;gap:3px}.nhv-mon img,.nhv-mon-o{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:8px;background:#f3e7de;display:grid;place-items:center;font-size:28px;font-weight:800;color:#7a4a22}
.nhv-kg{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}
.nhv-kg .ksv-phbtn{position:relative}.nhv-kg img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:8px;display:block}
.nhv-kg small,#vtd-access .nhv .nhv-kg small{position:absolute;left:6px;bottom:6px;background:rgba(0,0,0,.55);color:#fff;font-size:11px;padding:1px 6px;border-radius:4px}
.nhv-a,#vtd-access .nhv a.nhv-a{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;color:var(--ksv-ink)}
.nhv-ro{min-height:46px;border:1px solid var(--ksv-line);border-radius:8px;padding:0 12px;display:flex;align-items:center;background:var(--ksv-soft);font-weight:400}
.nhv-pay{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--ksv-line);border-radius:10px;padding:12px;cursor:pointer}
.nhv-pay.on{border-color:var(--ksv-accent);background:var(--ksv-asoft)}.nhv-pay input,#vtd-access .nhv .nhv-pay input{width:18px;height:18px;min-height:0;flex:none;margin:3px 0 0;padding:0;accent-color:var(--ksv-accent)}
.nhv-pay>span{flex:1;min-width:0}
.nhv-tom{position:sticky;top:76px;gap:8px}.nhv-tom-anh{width:100%;height:140px;object-fit:cover;border-radius:8px}
.nhv-dk{background:var(--ksv-soft);border-radius:8px;padding:8px 10px;font-size:12.5px;line-height:1.45}
.nhv-tom-o{display:flex;gap:6px;flex-wrap:wrap}.nhv-tom-o span{background:var(--ksv-soft);border-radius:8px;padding:6px 10px;font-weight:600;font-size:13px}
.nhv-xong{padding:22px;gap:14px}.nhv-xong-dau{display:flex;gap:18px;justify-content:space-between;flex-wrap:wrap}
.nhv-qr{margin:0;display:flex;flex-direction:column;align-items:center;gap:4px;font-size:12px;color:var(--ksv-muted)}
.nhv-tiep{margin:0;padding-left:20px;line-height:1.8;color:var(--ksv-muted)}
.nhv-mapwrap{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:14px;align-items:start}
.nhv-mapwrap .ksv-crow{grid-template-columns:180px minmax(0,1fr)}.nhv-mapwrap .ksv-side{grid-column:1 / -1;border-left:0;border-top:1px solid var(--ksv-line);flex-direction:row;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:8px}
.nhv-mapwrap .ksv-side .ksv-btn.wide{width:auto;margin:0}
.nhv-mapwrap .ksv-ph img{min-height:150px}
.nhv-al{position:fixed;inset:0;z-index:200;font-family:"Be Vietnam Pro",system-ui,sans-serif;background:#0d1117;color:#fff;display:flex;flex-direction:column;padding:env(safe-area-inset-top,0px) max(16px,env(safe-area-inset-right,0px)) env(safe-area-inset-bottom,0px) max(16px,env(safe-area-inset-left,0px))}
.nhv-al-dau{display:flex;gap:12px;align-items:center;padding:12px 0;flex-wrap:wrap}
.nhv-al-tabs{display:flex;gap:6px;overflow-x:auto;flex:1;min-width:0}
.nhv-al-tabs button{border:1px solid #3a4352;background:transparent;color:#d6dbe3;border-radius:99px;padding:6px 12px;white-space:nowrap;font-weight:600}
.nhv-al-tabs button.on{background:#fff;color:#0d1117}
.nhv-al-x{border:0;background:#2a313d;color:#fff;width:40px;height:40px;border-radius:50%;font-size:18px}
.nhv-al-luoi{flex:1;overflow:auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;align-content:start;padding-bottom:16px}
.nhv-al-luoi img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:6px;display:block}
.nhv-al-mot{flex:1;display:grid;grid-template-columns:48px minmax(0,1fr) 48px;align-items:center;gap:8px;min-height:0}
.nhv-al-mot figure{margin:0;display:flex;flex-direction:column;align-items:center;gap:8px;min-height:0;height:100%;justify-content:center}
.nhv-al-mot img{max-width:100%;max-height:calc(100vh - 140px);object-fit:contain}
.nhv-al-mot figcaption{font-size:13px;color:#c7cdd6;text-align:center}
.nhv-al-mot>button{border:0;background:#2a313d;color:#fff;width:44px;height:44px;border-radius:50%;font-size:24px}
@media (max-width:1100px){.nhv-sbar{grid-template-columns:1fr 1fr 1fr}.nhv-sbar .ksv-btn-tim{grid-column:span 3}}
@media (max-width:900px){.nhv .nhv-gal{grid-template-columns:1fr 1fr;grid-template-rows:200px 110px}.nhv .nhv-gal>span:first-child{grid-column:1 / -1;grid-row:auto}.nhv .nhv-gal>span:nth-child(n+4){display:none}.nhv-mapwrap{grid-template-columns:1fr}.nhv-f{grid-template-columns:1fr}.nhv-tom{position:static}}
@media (max-width:640px){.nhv-sbar{grid-template-columns:1fr 1fr}.nhv-sbar>label:first-child,.nhv-sbar>label:nth-child(3),.nhv-khach{grid-column:span 2}.nhv-sbar .ksv-btn-tim{grid-column:span 2}
  .nhv-ht{font-size:19px}.nhv-al-mot{grid-template-columns:36px minmax(0,1fr) 36px}.nhv-mapwrap .ksv-crow{grid-template-columns:1fr}}
`;
