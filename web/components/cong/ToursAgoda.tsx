"use client";
/* TR-1 · Tour kiểu Agoda / Klook trên kh.vietourist.vn/tours (Chủ tịch duyệt bản xem thử v4 01/11/2026, nối nội dung
   web 02/11/2026). Cùng khung, màu, thứ tự bước như khách sạn (KS-16p) và nhà hàng (AT-2):
   1 tìm (tab Trong nước | Nước ngoài · điểm đến · khởi hành từ · khoảng ngày + chọn nhanh · khách · loại tour)
   → 2 danh sách + bộ lọc (số đếm thật, nhóm không có tour thì ẩn) + dải Wellness (không có tour wellness thì ẩn)
   → 3 trang tour (ảnh, lịch trình, bao gồm / không bao gồm, quy định ĐỌC THẲNG từ trang tour trên vietourist.com.vn;
     thẻ ngày khởi hành từ crm) → 4–5 thông tin khách + cọc / trả đủ → 6 đã giữ chỗ (mã + QR, .ics, QR chuyển khoản,
     thẻ qua SePay, tải invoice). Tour đoàn riêng: «Gửi yêu cầu thiết kế tour».
   Máy chủ tính lại mọi con số. Công tắc thanh toán (chung + từng sản phẩm) chưa bật → nút cuối «Gửi yêu cầu giữ chỗ»
   (Sales gọi lại, không giữ chỗ, không thu tiền) — máy chủ cũng chặn đặt online bằng 409. */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import QRCode from "qrcode";
import { diCongThe, duongRieng, emailThat, goiCong, phienCong } from "@/lib/cong";
import { CSS_KSV } from "./KhachSanVtd";
import QrThanhToan from "./khach/QrThanhToan";
import TuThietKeTour from "./TuThietKeTour";   // TK-1: khách tự thiết kế tour đoàn

const vnd = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const themNgay = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };
const THU = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const ngayDep = (s: string) => { const d = new Date(s + "T00:00:00"); return `${THU[d.getDay()]} · ${d.getDate()}/${d.getMonth() + 1}`; };
const ngayVn = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const nghin = (x: number) => Math.ceil(Math.round(x) / 1000) * 1000;
const PT: Record<string, string> = { xe: "Xe du lịch", may_bay: "Máy bay", tau_hoa: "Tàu hỏa", du_thuyen: "Du thuyền" };
const BUA: Record<string, string> = { "sáng": "sáng", "trưa": "trưa", "tối": "tối" };

type Q = { tab: string; q: string; noi: string; tu: string; den: string; nl: number; te: number; eb: number; loai: string };
type Loc = { loai: string[]; well: boolean; tl: string[]; gia: string[]; ud: string[]; pt: string[] };
const LOC0: Loc = { loai: [], well: false, tl: [], gia: [], ud: [], pt: [] };
const TL: [string, string, (n: number) => boolean][] = [["1", "1 ngày", (n) => n <= 1], ["2_3", "2–3 ngày", (n) => n >= 2 && n <= 3],
  ["4_5", "4–5 ngày", (n) => n >= 4 && n <= 5], ["6", "6 ngày trở lên", (n) => n >= 6]];
const GIA: [string, string, (g: number) => boolean][] = [["d2", "Dưới 2 triệu", (g) => g < 2e6], ["2_5", "2–5 triệu", (g) => g >= 2e6 && g <= 5e6],
  ["t5", "Trên 5 triệu", (g) => g > 5e6]];
/* TR-4: lọc giá dùng giá thật của chuyến; tour chưa có lịch (TR-3) dùng giá tham khảo trên web. */
const giaLoc = (s: any): number | null => s.gia_tu ?? s.gia_tham_khao ?? null;
const UD: [string, string, (s: any) => boolean][] = [["km", "Khuyến mại", (s) => s.khuyen_mai], ["gc", "Giờ chót", (s) => s.gio_chot], ["it", "Còn ít chỗ", (s) => s.it_cho]];

function nhanh(k: string, homNay: string): [string, string] {
  const d = new Date(homNay + "T00:00:00");
  if (k === "cuoi_tuan") { const t7 = themNgay(homNay, (6 - d.getDay() + 7) % 7); return [t7, themNgay(t7, 1)]; }
  if (k === "thang_nay") return [homNay, iso(new Date(d.getFullYear(), d.getMonth() + 1, 0))];
  return [iso(new Date(d.getFullYear(), d.getMonth() + 1, 1)), iso(new Date(d.getFullYear(), d.getMonth() + 2, 0))];
}

function taiLich(d: { ma: string; ten: string; khoi_hanh: string; ket_thuc: string; noi?: string }) {
  const den = themNgay(d.ket_thuc, 1).replace(/-/g, "");
  const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Vietourist//VTOS//VI", "BEGIN:VEVENT", `UID:${d.ma}@vietourist.vn`,
    `DTSTART;VALUE=DATE:${d.khoi_hanh.replace(/-/g, "")}`, `DTEND;VALUE=DATE:${den}`, `SUMMARY:Tour ${d.ten} (${d.ma})`.replace(/,/g, "\\,"),
    `LOCATION:${(d.noi || "").replace(/,/g, "\\,")}`, `DESCRIPTION:Mã đơn ${d.ma} · Vietourist`, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
  const url = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = `${d.ma}.ics`; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Invoice chỉ chủ đơn tải được: gọi kèm phiên cổng (máy chủ trả 404 cho tài khoản khác), rồi lưu thành tệp. */
async function taiInvoice(ma: string) {
  const r = await fetch(`/api/v1/cong/khach/tour-online/don/${encodeURIComponent(ma)}/invoice`, { headers: { Authorization: `Bearer ${phienCong()}` } });
  if (!r.ok) { let m = `Lỗi ${r.status}`; try { m = (await r.json()).detail || m; } catch { /* bỏ qua */ } throw new Error(m); }
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a"); a.href = url; a.download = `Invoice-${ma}.pdf`; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function AnhTrong({ ten, cao = 200 }: { ten: string; cao?: number }) {
  return <span className="ksv-trong" style={{ minHeight: cao }}><b style={{ background: "#1f4e5f" }}>{(ten || "?").trim().charAt(0).toUpperCase()}</b><small>Ảnh đang cập nhật</small></span>;
}

/* ═════════════════════════════════ 6 · ĐƠN TOUR (mã + QR, thanh toán, invoice) ═════════════════════════════════ */
export function DonTour({ ma, ve }: { ma: string; ve?: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [qrMa, setQrMa] = useState("");
  const [cach, setCach] = useState<"qr" | "the">("qr");
  const [busy, setBusy] = useState(false);
  const [giay, setGiay] = useState(0);
  const tu = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("the") || "" : "";
  const tai = () => goiCong(`/khach/tour-online/don/${encodeURIComponent(ma)}`).then((o) => { setD(o); setGiay(o.giay_con); }).catch((x) => setLoi(x.message));
  useEffect(() => {
    tai();
    QRCode.toDataURL(ma, { margin: 1, width: 180, errorCorrectionLevel: "M" }).then(setQrMa).catch(() => setQrMa(""));
    const h = setInterval(tai, tu === "cho" ? 5000 : 20000);       // từ cổng thẻ về: hỏi dồn 5 giây cho tới khi tiền vào
    return () => clearInterval(h);
  }, [ma]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (giay <= 0) return; const h = setInterval(() => setGiay((g) => Math.max(0, g - 1)), 1000); return () => clearInterval(h); }, [giay > 0]);  // eslint-disable-line react-hooks/exhaustive-deps
  const the = async () => {
    setBusy(true); setLoi("");
    try { diCongThe(await goiCong(`/khach/tour-online/don/${encodeURIComponent(ma)}/the`, { muc: "" })); }
    catch (x: any) { setLoi(x.message); setBusy(false); }
  };
  if (!d) return <section className="ksv-panel">{loi ? <div className="ksv-loi">{loi}</div> : "Đang tải đơn…"}</section>;
  const ttLop = d.trang_thai.startsWith("Đã thanh toán") ? "ksv-tt-ok" : d.trang_thai.startsWith("Đã đặt cọc") ? "ksv-tt-xanh" : d.trang_thai === "Chờ thanh toán" ? "ksv-tt-cho" : "ksv-tt-xam";
  return <>
    <div className="ksv-steps"><span className="xong"><b>✓</b>Số khách</span><hr /><span className="xong"><b>✓</b>Thông tin khách</span><hr />
      <span className={d.da_tra ? "xong" : "on"}><b>{d.da_tra ? "✓" : 3}</b>Thanh toán</span><hr /><span className={d.da_tra ? "on" : ""}><b>4</b>Xác nhận</span></div>
    <section className="ksv-panel" style={{ padding: 20 }}>
      <div className="tra-xong-dau"><div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
        <span className={`ksv-tt ${ttLop}`}>{d.trang_thai}</span>
        <h2 style={{ margin: 0, fontSize: 24 }}>{d.ten}</h2>
        <span>Mã đơn <b className="ksv-ma">{d.ma}</b> · chuyến {d.ma_chuyen}</span>
        <span>Khởi hành {ngayDep(d.khoi_hanh)}/{d.khoi_hanh.slice(0, 4)}{d.noi_khoi_hanh ? ` · ${d.noi_khoi_hanh}` : ""} · {d.nguoi_lon} người lớn{d.tre_em ? ` · ${d.tre_em} trẻ em` : ""}{d.em_be ? ` · ${d.em_be} em bé` : ""}</span>
        <span className="ksv-muted">Tổng ₫ {vnd(d.tong)} · đã trả ₫ {vnd(d.da_tra)} · còn lại ₫ {vnd(d.con_lai)}
          {d.cach_tra === "coc" && d.han_tra_con_lai && d.con_lai > 0 ? ` — trả phần còn lại trước ${d.han_tra_con_lai.slice(11)} ngày ${ngayVn(d.han_tra_con_lai)}` : ""}</span>
        {giay > 0 && <span className="ksv-hv">Giữ chỗ còn <b>{Math.floor(giay / 60)}:{String(giay % 60).padStart(2, "0")}</b> — chưa thanh toán thì chỗ tự trả lại cho người khác.</span>}
        {tu === "cho" && !d.da_tra && <span className="ksv-hv">Đang chờ cổng thẻ báo kết quả — trang tự cập nhật.</span>}
        {(tu === "loi" || tu === "huy") && !d.da_tra && <span className="ksv-loi">{tu === "huy" ? "Bạn đã hủy thanh toán thẻ." : "Cổng thẻ báo thanh toán không thành công."} Thử lại hoặc dùng QR chuyển khoản.</span>}
        {d.email_gui_luc && <span className="ksv-okc">Đã gửi email «Xác nhận đã thanh toán» kèm invoice tới {d.email}.</span>}
      </div>
        {qrMa && <figure className="tra-qr"><img src={qrMa} alt={`Mã đơn ${d.ma}`} width={140} height={140} /><figcaption>Mã đơn — đưa HDV khi tập trung</figcaption></figure>}</div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button type="button" className="ksv-btn line" onClick={() => taiLich({ ma: d.ma, ten: d.ten, khoi_hanh: d.khoi_hanh, ket_thuc: d.ket_thuc, noi: d.noi_khoi_hanh })}>Thêm vào lịch</button>
        {d.co_hoa_don && <button type="button" className="ksv-btn line" onClick={() => taiInvoice(d.ma).catch((x) => setLoi(x.message))}>Tải invoice (PDF)</button>}
        {ve && <button type="button" className="ksv-btn" onClick={ve}>Xem tour khác</button>}</div>
      {loi && <div className="ksv-loi">{loi}</div>}
    </section>
    {d.co_the_tra && (d.mo_thanh_toan ? <section className="ksv-panel" style={{ padding: 20 }}>
      <b style={{ fontSize: 18 }}>Thanh toán {d.con_phai_tra_ngay > 0 ? `₫ ${vnd(d.con_phai_tra_ngay)} (${d.cach_tra === "coc" ? "cọc" : "toàn bộ"})` : `phần còn lại ₫ ${vnd(d.con_lai)}`}</b>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button type="button" className={`ksv-chip${cach === "qr" ? " on" : ""}`} aria-pressed={cach === "qr"} onClick={() => setCach("qr")}>QR chuyển khoản</button>
        {d.the_bat && <button type="button" className={`ksv-chip${cach === "the" ? " on" : ""}`} aria-pressed={cach === "the"} onClick={() => setCach("the")}>Thẻ Visa · Master · JCB · ATM</button>}</div>
      {cach === "qr" ? <QrThanhToan ma={d.ma} duong="/khach/tour-online/don" />
        : <><span className="ksv-muted">Bạn sẽ sang trang cổng SePay để nhập thẻ. Vietourist không thấy và không lưu số thẻ.</span>
          <button type="button" className="ksv-btn" style={{ alignSelf: "flex-start" }} disabled={busy} onClick={the}>{busy ? "Đang mở cổng thẻ…" : "Thanh toán bằng thẻ"}</button></>}
    </section> : <section className="ksv-panel"><span className="ksv-muted">Thanh toán trực tuyến đang tạm đóng cho tour này — Sales Vietourist sẽ liên hệ hướng dẫn thanh toán.</span></section>)}
    <section className="ksv-panel"><b>Khách đi tour</b><ol style={{ margin: 0, paddingLeft: 20 }}>{(d.khach || []).map((k: any, i: number) =>
      <li key={i}>{k.ho_ten} · {ngayVn(k.ngay_sinh)}{k.loai ? ` · ${k.loai === "tre_em" ? "trẻ em" : k.loai === "em_be" ? "em bé" : "người lớn"}` : ""}</li>)}</ol>
      {d.hoa_don_cong_ty && <span className="ksv-muted">Hóa đơn GTGT cho {d.hoa_don_cong_ty.ten} (MST {d.hoa_don_cong_ty.mst}) — Kế toán phát hành theo quy trình.</span>}</section>
  </>;
}

/* ═════════════════════════════════════════════════ TRANG CHÍNH ═════════════════════════════════════════════════ */
export default function ToursAgoda({ toi, moId, moDon }: { toi: any; moId?: number; moDon?: string }) {
  const homNay = iso(new Date());
  const [q, setQ] = useState<Q>({ tab: "trong_nuoc", q: "", noi: "", tu: "", den: "", nl: 2, te: 0, eb: 0, loai: "" });
  const [ds, setDs] = useState<any>(null);
  const [loc, setLoc] = useState<Loc>(LOC0);
  const [sx, setSx] = useState("som");
  const [moLoc, setMoLoc] = useState(false);
  const [popKhach, setPopKhach] = useState(false);
  const [sp, setSp] = useState<any>(null);
  const [lt, setLt] = useState<any>(null);
  const [chon, setChon] = useState<number | null>(null);
  const [buoc, setBuoc] = useState<"ds" | "sp" | "dat" | "doan" | "da_gui" | "don">(moDon ? "don" : "ds");
  const [don, setDon] = useState(moDon || "");
  const [gia, setGia] = useState<any>(null);
  const [kh, setKh] = useState<any>({ ho_ten: toi?.ho_ten || "", dien_thoai: toi?.dien_thoai || "", email: emailThat(toi?.email), cach: "coc", yeu_cau: "",
    vat: false, mst: "", cty: "", dc: "", vat_email: "", dong_y: false, khach: [] as any[] });
  const [yc, setYc] = useState<any>({ so_khach: 20, tu: "", den: "", noi: "", ngan_sach: "", hang_ks: "", cong_ty: "", hoa_don: false, dien_thoai: "", ghi_chu: "", dong_y: false });
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState("");
  const len = () => { try { window.scrollTo(0, 0); } catch { /* bỏ qua */ } };
  const datDuong = (p: string) => { try { window.history.replaceState(null, "", p); } catch { /* bỏ qua */ } };

  const tim = async (qq = q) => {
    setLoi("");
    const p = new URLSearchParams({ tab: qq.tab, q: qq.q, noi: qq.noi, tu: qq.tu, den: qq.den, nguoi_lon: String(qq.nl), tre_em: String(qq.te), loai: qq.loai });
    for (const k of Array.from(p.keys())) if (!p.get(k)) p.delete(k);
    try { setDs(await goiCong(`/mo/tour-online/tim?${p}`)); } catch (x: any) { setLoi(x.message); }
  };
  const moSp = async (id: number) => {
    setLoi(""); setBusy(true);
    try {
      const o = await goiCong(`/mo/tour-online/san-pham/${id}?nguoi_lon=${q.nl}&tre_em=${q.te}`);
      setSp(o); setLt(o.lich_trinh); setBuoc("sp"); len(); datDuong(duongRieng("tours", id));
      if (o.chua_co_lich) setYc((y: any) => ({ ...y, so_khach: Math.max(1, q.nl + q.te), tu: q.tu || y.tu, den: q.den || y.den }));   // TR-3
      const dau = (o.chuyen || []).find((c: any) => c.du_cho && (!q.tu || c.khoi_hanh >= q.tu) && (!q.den || c.khoi_hanh <= q.den));
      setChon(dau ? dau.tour_id : null);
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };
  useEffect(() => { if (!moDon) { tim(); if (moId) moSp(moId); } }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {      // đổi ngày → lịch trình của đúng chuyến (chuyến có chương trình riêng thì hiện chương trình ấy)
    if (!sp || !chon) return;
    goiCong(`/mo/tour-online/san-pham/${sp.id}/lich-trinh/${chon}`).then(setLt).catch(() => { /* giữ lịch trình đang hiện */ });
  }, [chon]);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {      // số tiền: máy chủ tính (giá chuyến, trẻ em, em bé, cọc, hạn)
    if (buoc !== "dat" || !chon) return;
    goiCong(`/mo/tour-online/tinh?tour_id=${chon}&nguoi_lon=${q.nl}&tre_em=${q.te}&em_be=${q.eb}&cach_tra=${kh.cach}`).then(setGia).catch((x) => setLoi(x.message));
  }, [buoc, chon, q.nl, q.te, q.eb, kh.cach]);

  // ---------- bộ lọc mặt: chạy trên trình duyệt, số đếm thật, nhóm không có tour thì ẩn ----------
  const tat: any[] = ds?.san_pham || [];
  const khop = (s: any, bo?: keyof Loc) => {
    const L = loc;
    if (bo !== "loai" && L.loai.length && !L.loai.includes(s.loai)) return false;
    if (bo !== "well" && L.well && !s.wellness) return false;
    if (bo !== "tl" && L.tl.length && !TL.some(([k, , f]) => L.tl.includes(k) && f(s.ngay))) return false;
    if (bo !== "gia" && L.gia.length && !((g) => g != null && GIA.some(([k, , f]) => L.gia.includes(k) && f(g)))(giaLoc(s))) return false;
    if (bo !== "ud" && L.ud.length && !L.ud.every((k) => UD.find((x) => x[0] === k)?.[2](s))) return false;
    if (bo !== "pt" && L.pt.length && !L.pt.some((k) => (s.phuong_tien || []).includes(k))) return false;
    return true;
  };
  const kq = useMemo(() => {
    const r = tat.filter((s) => khop(s));
    const f: Record<string, (a: any, b: any) => number> = {
      som: (a, b) => (a.khoi_hanh_gan[0] || "9999").localeCompare(b.khoi_hanh_gan[0] || "9999") || a.ten.localeCompare(b.ten),
      gia_thap: (a, b) => (a.gia_tu ?? 9e12) - (b.gia_tu ?? 9e12), gia_cao: (a, b) => (b.gia_tu ?? -1) - (a.gia_tu ?? -1),
      ngan: (a, b) => a.ngay - b.ngay, dai: (a, b) => b.ngay - a.ngay,
    };
    return [...r].sort(f[sx]);
  }, [tat, loc, sx]);  // eslint-disable-line react-hooks/exhaustive-deps
  const dem = (f: (s: any) => boolean, bo: keyof Loc) => tat.filter((s) => khop(s, bo) && f(s)).length;
  const bat = (a: string[], k: string, v: boolean) => (v ? [...a, k] : a.filter((x) => x !== k));
  // TR-4: «Giá mỗi khách» và «Phương tiện» luôn hiện đủ mức (mức chưa có tour thì mờ, số 0) — các nhóm khác ẩn mức trống.
  const nhom = (tieuDe: string, muc: [string, string, (s: any) => boolean][], khoa: "loai" | "tl" | "gia" | "ud" | "pt", du = false,
                them?: ReactNode) => {
    const co = du ? muc : muc.filter(([, , f]) => dem(f, khoa) > 0);
    return (co.length > 0 || !!them) && <div className="ksv-panel"><b>{tieuDe}</b>{co.map(([m, t, f]) =>
      <label key={khoa + m} className="ksv-chk" style={dem(f, khoa) === 0 ? { opacity: 0.55 } : undefined}><input type="checkbox" checked={(loc[khoa] as string[]).includes(m)}
        disabled={dem(f, khoa) === 0 && !(loc[khoa] as string[]).includes(m)}
        onChange={(e) => setLoc({ ...loc, [khoa]: bat(loc[khoa] as string[], m, e.target.checked) })} /><span>{t}</span><small>{dem(f, khoa)}</small></label>)}{them}</div>;
  };

  // ---------- đặt ----------
  const chuyen = sp?.chuyen?.find((c: any) => c.tour_id === chon);
  const doiKhach = (nl: number, te: number, eb: number) => {
    const cu: any[] = kh.khach;
    const loai = [...Array(nl).fill("nguoi_lon"), ...Array(te).fill("tre_em"), ...Array(eb).fill("em_be")];
    setKh((k: any) => ({ ...k, khach: loai.map((l, i) => ({ ho_ten: i === 0 ? k.ho_ten : "", ngay_sinh: "", gioi_tinh: "", giay_to: "", ...(cu[i] || {}), loai: l })) }));
  };
  const moDat = () => {
    if (!chuyen) { setLoi("Chọn một ngày khởi hành còn chỗ"); return; }
    setLoi(""); doiKhach(q.nl, q.te, q.eb);
    setBuoc("dat"); len();
  };
  useEffect(() => { if (buoc === "dat") doiKhach(q.nl, q.te, q.eb); }, [q.nl, q.te, q.eb]);  // eslint-disable-line react-hooks/exhaustive-deps
  const moTt = !!(gia ? gia.mo_thanh_toan : sp?.mo_thanh_toan);
  const datTour = async () => {
    setLoi("");
    if (!kh.dong_y) { setLoi("Đánh dấu ô đồng ý điều kiện tour, thanh toán và hủy"); return; }
    setBusy(true);
    try {
      if (!moTt) {           // công tắc đóng: gửi yêu cầu giữ chỗ như cổng hiện nay (Sales gọi lại)
        const r = await goiCong("/khach/yeu-cau", { loai: "tour", tour_id: chon, so_khach: q.nl + q.te + q.eb, dien_thoai: kh.dien_thoai,
          ngay_mong_muon: null, ghi_chu: [`${q.nl} NL · ${q.te} TE · ${q.eb} EB`, kh.yeu_cau].filter(Boolean).join(" · "), dong_y: true });
        setMsg(r.message); setBuoc("da_gui"); len(); return;
      }
      const r = await goiCong("/khach/tour-online/dat", { tour_id: chon, nguoi_lon: q.nl, tre_em: q.te, em_be: q.eb, cach_tra: kh.cach,
        ho_ten: kh.ho_ten, dien_thoai: kh.dien_thoai, email: kh.email, khach: kh.khach, yeu_cau: kh.yeu_cau, dong_y: kh.dong_y,
        hoa_don_cong_ty: kh.vat ? { mst: kh.mst, ten: kh.cty, dia_chi: kh.dc, email: kh.vat_email || kh.email } : null });
      setDon(r.don.ma); setBuoc("don"); len(); datDuong(`${duongRieng("tours")}/don/${encodeURIComponent(r.don.ma)}`);
    } catch (x: any) { if (x.status !== 401) setLoi(x.message); } finally { setBusy(false); }
  };
  const guiDoan = async () => {
    setLoi("");
    if (!yc.dong_y) { setLoi("Đánh dấu ô đồng ý để Sales liên hệ"); return; }
    setBusy(true);
    try {
      const r = await goiCong("/khach/tour-online/yeu-cau-doan", { product_id: sp?.id ?? null, so_khach: Number(yc.so_khach), dien_thoai: yc.dien_thoai,
        tu_ngay: yc.tu, den_ngay: yc.den, noi_khoi_hanh: yc.noi, ngan_sach: Number(yc.ngan_sach || 0), hang_ks: yc.hang_ks,
        cong_ty: yc.cong_ty, hoa_don: yc.hoa_don, ghi_chu: yc.ghi_chu, dong_y: yc.dong_y });
      setMsg(r.message); setBuoc("da_gui"); len();
    } catch (x: any) { if (x.status !== 401) setLoi(x.message); } finally { setBusy(false); }
  };
  const veDs = () => { setBuoc("ds"); setSp(null); setLoi(""); len(); datDuong(duongRieng("tours")); if (!ds) tim(); };

  const css = <style dangerouslySetInnerHTML={{ __html: CSS_KSV + CSS }} />;
  const soKhach = `${q.nl} người lớn${q.te ? ` · ${q.te} trẻ em` : ""}${q.eb ? ` · ${q.eb} em bé` : ""}`;

  const thanhTim = (gon = false) => <form className={`tra-hero${gon ? " gon" : ""}`} onSubmit={(e) => { e.preventDefault(); setBuoc("ds"); setSp(null); setLoc(LOC0); tim(); datDuong(duongRieng("tours")); }}>
    <div className="tra-tabs" role="tablist" aria-label="Khu vực">{[["trong_nuoc", "Tour trong nước"], ["nuoc_ngoai", "Tour nước ngoài"]].map(([k, t]) =>
      <button key={k} type="button" role="tab" aria-selected={q.tab === k} className={q.tab === k ? "on" : ""} onClick={() => { const qq = { ...q, tab: k }; setQ(qq); setLoc(LOC0); setBuoc("ds"); setSp(null); tim(qq); }}>{t}</button>)}</div>
    {!gon && <b className="tra-ht">Tour trọn gói Vietourist · khởi hành mỗi tuần</b>}
    <div className="tra-sbar">
      <label className="ksv-sbox"><span style={{ flex: 1, minWidth: 0 }}><small>Điểm đến hoặc tên tour</small>
        <input value={q.q} onChange={(e) => setQ({ ...q, q: e.target.value })} placeholder={q.tab === "nuoc_ngoai" ? "Nhật Bản, Hàn Quốc, Châu Âu…" : "Đà Lạt, Phú Quốc, Huế…"} aria-label="Điểm đến hoặc tên tour" /></span></label>
      <label className="ksv-sbox"><span style={{ flex: 1 }}><small>Khởi hành từ</small><select value={q.noi} onChange={(e) => setQ({ ...q, noi: e.target.value })} aria-label="Khởi hành từ">
        <option value="">Tất cả</option>{(ds?.noi_khoi_hanh || []).map((n: string) => <option key={n} value={n}>{n}</option>)}</select></span></label>
      <div className="ksv-sbox ksv-dates"><label><small>Đi từ ngày</small><input type="date" value={q.tu} min={homNay} onChange={(e) => setQ({ ...q, tu: e.target.value })} aria-label="Đi từ ngày" /></label>
        <label><small>Đến ngày</small><input type="date" value={q.den} min={q.tu || homNay} onChange={(e) => setQ({ ...q, den: e.target.value })} aria-label="Đến ngày" /></label></div>
      <div className="ksv-sbox" style={{ position: "relative" }}><button type="button" className="ksv-khach" aria-expanded={popKhach} onClick={() => setPopKhach(!popKhach)}><small>Khách</small><b>{soKhach}</b></button>
        {popKhach && <div className="ksv-pop" role="dialog" aria-label="Chọn số khách">{([["nl", "Người lớn", "từ 12 tuổi", 1], ["te", "Trẻ em", "2–11 tuổi", 0], ["eb", "Em bé", "dưới 2 tuổi", 0]] as [keyof Q, string, string, number][]).map(([k, t, m, min]) =>
          <div key={k} className="ksv-step"><span><b>{t}</b><br /><small className="ksv-muted">{m}</small></span><div>
            <button type="button" aria-label={`Bớt ${t}`} onClick={() => setQ({ ...q, [k]: Math.max(min, (q[k] as number) - 1) })}>−</button><b>{q[k] as number}</b>
            <button type="button" aria-label={`Thêm ${t}`} onClick={() => setQ({ ...q, [k]: Math.min(k === "eb" ? q.nl : 60, (q[k] as number) + 1) })}>+</button></div></div>)}
          <small className="ksv-muted">Mỗi em bé đi cùng một người lớn. Đoàn trên 60 khách: gửi yêu cầu thiết kế tour.</small>
          <button type="button" className="ksv-btn" onClick={() => setPopKhach(false)}>Xong</button></div>}</div>
      <label className="ksv-sbox"><span style={{ flex: 1 }}><small>Loại tour</small><select value={q.loai} onChange={(e) => setQ({ ...q, loai: e.target.value })} aria-label="Loại tour">
        <option value="">Tất cả</option><option value="ghep">Tour ghép</option><option value="doan">Tour đoàn riêng</option></select></span></label>
      <button className="ksv-btn-tim" type="submit">TÌM TOUR</button></div>
    {!gon && <div className="tra-chips">{[["cuoi_tuan", "Cuối tuần này"], ["thang_nay", "Tháng này"], ["thang_sau", "Tháng sau"]].map(([k, t]) => {
      const [a, b] = nhanh(k, homNay); const on = q.tu === a && q.den === b;
      return <button key={k} type="button" className={`tra-chip${on ? " on" : ""}`} aria-pressed={on} onClick={() => { const qq = on ? { ...q, tu: "", den: "" } : { ...q, tu: a, den: b }; setQ(qq); tim(qq); }}>{t}</button>; })}</div>}
  </form>;

  // ═══════════════════════════════════ ĐƠN (6) / ĐÃ GỬI YÊU CẦU ═══════════════════════════════════
  if (buoc === "don" && don) return <div className="ksv tra">{css}<DonTour ma={don} ve={veDs} /></div>;
  if (buoc === "da_gui") return <div className="ksv tra">{css}<section className="ksv-panel" style={{ padding: 20 }}>
    <span className="ksv-ok" style={{ alignSelf: "flex-start" }}><b>✓ Đã gửi yêu cầu</b></span><p style={{ margin: 0 }}>{msg}</p>
    <span className="ksv-muted">Chưa giữ chỗ và chưa thu tiền. Sales Vietourist gọi lại trong giờ làm việc; theo dõi ở «Đơn của tôi» trên cổng khách.</span>
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}><button type="button" className="ksv-btn" onClick={veDs}>Xem tour khác</button><a className="ksv-btn line tra-a" href="/cong">Đơn của tôi</a></div></section></div>;

  // ═══════════════════════════════════ 4–5 · THÔNG TIN KHÁCH + THANH TOÁN (tour ghép) ═══════════════════════════════════
  if (buoc === "dat" && sp && chuyen) {
    const nn = sp.nuoc_ngoai;
    const coc = gia?.coc ?? nghin((chuyen.gia * q.nl + chuyen.gia_tre_em * q.te) * (sp.coc_pt || 0) / 100);
    return <div className="ksv tra">{css}
      <div className="ksv-steps"><span className="xong"><b>✓</b>Số khách</span><hr /><span className="on"><b>2</b>Thông tin khách</span><hr /><span className="on"><b>3</b>Thanh toán</span><hr /><span><b>4</b>Xác nhận</span>
        <button type="button" className="ksv-link" style={{ marginLeft: "auto" }} onClick={() => { setBuoc("sp"); len(); }}>← Quay lại chọn ngày</button></div>
      <div className="ksv-co">
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>Người liên hệ</h2>
            <div className="ksv-f2"><label className="ksv-fld">Họ và tên<input value={kh.ho_ten} autoComplete="name" onChange={(e) => setKh({ ...kh, ho_ten: e.target.value })} /></label>
              <label className="ksv-fld">Số điện thoại<input inputMode="tel" value={kh.dien_thoai} autoComplete="tel" placeholder="09xx xxx xxx" onChange={(e) => setKh({ ...kh, dien_thoai: e.target.value })} /></label></div>
            <label className="ksv-fld">Email nhận xác nhận và invoice<input type="email" value={kh.email} autoComplete="email" onChange={(e) => setKh({ ...kh, email: e.target.value })} /></label>
          </section>
          <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Thông tin từng khách ({q.nl + q.te + q.eb})</h2>
            <span className="ksv-muted" style={{ fontSize: 13 }}>Họ tên đúng giấy tờ, ngày sinh{nn ? ", số hộ chiếu (tour nước ngoài)" : ""}. Dùng cho bảo hiểm du lịch và danh sách đoàn.</span>
            {kh.khach.map((k: any, i: number) => <div key={i} className="tra-khach"><b>{i + 1}. {k.loai === "tre_em" ? "Trẻ em" : k.loai === "em_be" ? "Em bé" : "Người lớn"}</b>
              <div className="tra-k4"><label className="ksv-fld">Họ và tên<input value={k.ho_ten} onChange={(e) => { const a = [...kh.khach]; a[i] = { ...k, ho_ten: e.target.value }; setKh({ ...kh, khach: a }); }} /></label>
                <label className="ksv-fld">Ngày sinh<input type="date" value={k.ngay_sinh} max={homNay} onChange={(e) => { const a = [...kh.khach]; a[i] = { ...k, ngay_sinh: e.target.value }; setKh({ ...kh, khach: a }); }} /></label>
                <label className="ksv-fld">Giới tính<select className="ksv-sel" value={k.gioi_tinh} onChange={(e) => { const a = [...kh.khach]; a[i] = { ...k, gioi_tinh: e.target.value }; setKh({ ...kh, khach: a }); }}>
                  <option value="">—</option><option value="nam">Nam</option><option value="nu">Nữ</option></select></label>
                <label className="ksv-fld">{nn ? "Số hộ chiếu" : "CCCD (không bắt buộc)"}<input value={k.giay_to} onChange={(e) => { const a = [...kh.khach]; a[i] = { ...k, giay_to: e.target.value }; setKh({ ...kh, khach: a }); }} /></label></div></div>)}
            <label className="ksv-fld">Yêu cầu thêm<textarea maxLength={800} value={kh.yeu_cau} placeholder="Ăn chay, phòng đơn, ghế trẻ em…" onChange={(e) => setKh({ ...kh, yeu_cau: e.target.value })} /></label>
            <label className="ksv-chk"><input type="checkbox" checked={kh.vat} onChange={(e) => setKh({ ...kh, vat: e.target.checked })} /><span>Cần hóa đơn công ty (GTGT)</span></label>
            {kh.vat && <div className="ksv-f2"><label className="ksv-fld">Mã số thuế<input inputMode="numeric" value={kh.mst} onChange={(e) => setKh({ ...kh, mst: e.target.value })} /></label>
              <label className="ksv-fld">Tên công ty<input value={kh.cty} onChange={(e) => setKh({ ...kh, cty: e.target.value })} /></label>
              <label className="ksv-fld">Địa chỉ<input value={kh.dc} onChange={(e) => setKh({ ...kh, dc: e.target.value })} /></label>
              <label className="ksv-fld">Email nhận hóa đơn<input type="email" value={kh.vat_email} placeholder={kh.email} onChange={(e) => setKh({ ...kh, vat_email: e.target.value })} /></label></div>}
          </section>
          <section className="ksv-panel" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 18 }}>Cách thanh toán</h2>
            {gia?.cho_coc !== false && <label className={`ksv-pay${kh.cach === "coc" ? " on" : ""}`}><input type="radio" name="tra-tt" checked={kh.cach === "coc"} onChange={() => setKh({ ...kh, cach: "coc" })} />
              <span><b>Giữ chỗ — đặt cọc {gia?.coc_pt ?? sp.coc_pt}%</b><br /><small className="ksv-muted">Trả ₫ {vnd(coc)} bây giờ để giữ chỗ. Phần còn lại trả trước {gia ? `17:00 ngày ${ngayVn(gia.han_tra_con_lai)}` : `ngày khởi hành ${sp.dong_so_truoc} ngày`}.</small></span></label>}
            <label className={`ksv-pay${kh.cach === "du" || gia?.cho_coc === false ? " on" : ""}`}><input type="radio" name="tra-tt" checked={kh.cach === "du" || gia?.cho_coc === false} onChange={() => setKh({ ...kh, cach: "du" })} />
              <span><b>Thanh toán toàn bộ online</b><br /><small className="ksv-muted">₫ {vnd(gia?.tong)} · {sp.the_bat ? "Visa · Mastercard · JCB · thẻ ATM nội địa (qua cổng SePay) hoặc " : ""}QR chuyển khoản. Vietourist không thấy và không lưu số thẻ.</small></span></label>
            {gia?.cho_coc === false && <small className="ksv-muted">Đã qua hạn đóng sổ đặt cọc của chuyến này — thanh toán toàn bộ.</small>}
            <small className="ksv-muted">Sau khi đặt, chỗ được giữ 15 phút để thanh toán. Tiền vào là đơn được xác nhận và email «Xác nhận đã thanh toán» kèm invoice (PDF) gửi tới {kh.email || "email của bạn"}.</small>
          </section>
          {loi && <div className="ksv-loi">{loi}</div>}
          <div className="ksv-panel" style={{ flexDirection: "row", alignItems: "center", gap: 14, flexWrap: "wrap", padding: "16px 20px" }}>
            <label className="ksv-chk" style={{ flex: 1, minWidth: 220, alignItems: "flex-start" }}><input type="checkbox" checked={kh.dong_y} onChange={(e) => setKh({ ...kh, dong_y: e.target.checked })} />
              <span style={{ fontSize: 13 }}>Tôi đã đọc chương trình, giá bao gồm / không bao gồm và quy định hủy của tour; đồng ý cho Vietourist dùng thông tin khách để làm bảo hiểm và danh sách đoàn.</span></label>
            {moTt ? <button type="button" className="ksv-btn" style={{ minHeight: 52, padding: "0 28px", fontSize: 16 }} disabled={busy || !gia} onClick={datTour}>
              {busy ? "Đang giữ chỗ…" : `Đặt và thanh toán ₫ ${vnd(gia?.phai_tra)}`}</button>
              : <button type="button" className="ksv-btn" style={{ minHeight: 52, padding: "0 24px", fontSize: 15 }} disabled={busy} onClick={datTour}>{busy ? "Đang gửi…" : "Gửi yêu cầu giữ chỗ"}</button>}</div>
          {!moTt && <small className="ksv-muted">Thanh toán trực tuyến sắp mở cho tour này. Gửi yêu cầu giữ chỗ: Sales Vietourist gọi lại xác nhận chỗ và hướng dẫn thanh toán — bạn chưa phải trả gì.</small>}
        </div>
        <aside className="ksv-panel" aria-label="Tóm tắt đặt tour">
          {sp.anh?.[0] ? <img src={sp.anh[0]} alt={sp.ten} className="tra-tom-anh" /> : <AnhTrong ten={sp.ten} cao={120} />}
          <b style={{ fontSize: 17 }}>{sp.ten}</b><span className="ksv-muted">Khởi hành {ngayDep(chuyen.khoi_hanh)} · {sp.noi_khoi_hanh || "—"} · {sp.thoi_luong}</span>
          {(gia?.dong || []).map((x: any) => <div key={x.nhan} className="ksv-sum"><span>{x.nhan}</span><span>₫ {vnd(x.tien)}</span></div>)}
          <div className="ksv-sum"><b>Tổng</b><b>₫ {vnd(gia?.tong)}</b></div>
          <div className="ksv-sum" style={{ borderTop: "1px solid var(--ksv-line)", paddingTop: 8 }}><b>{gia?.cach_tra === "coc" ? `Cọc bây giờ (${gia.coc_pt}%)` : "Trả bây giờ"}</b>
            <b className="ksv-big" style={{ fontSize: 20 }}>₫ {vnd(gia?.phai_tra)}</b></div>
          <small className="ksv-muted">Số chính thức do máy chủ tính theo giá chuyến hôm nay.</small>
        </aside>
      </div></div>;
  }

  // ═══════════════════════════════════ ĐOÀN RIÊNG · GỬI YÊU CẦU THIẾT KẾ TOUR ═══════════════════════════════════
  const chuaLich = !!sp?.chua_co_lich;      // TR-3: tour ghép chưa có chuyến mở bán → gửi yêu cầu giữ chỗ
  const formDoan = <section className="ksv-panel" id="tra-doan" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>{chuaLich ? "Gửi yêu cầu giữ chỗ" : "Gửi yêu cầu thiết kế tour"}</h2>
    <span className="ksv-muted">{chuaLich ? "Tour này đang cập nhật lịch khởi hành. Chọn ngày muốn đi và số khách — Sales Vietourist gọi lại báo ngày và giá chính xác. Chưa thu tiền."
      : "Tour đoàn không có lịch cố định. Sales thiết kế hành trình và báo giá; đồng ý thì link thanh toán cọc hiện ở «Đơn của tôi»."}</span>
    <div className="ksv-f2">
      <label className="ksv-fld">Đi từ ngày<input type="date" value={yc.tu} min={homNay} onChange={(e) => setYc({ ...yc, tu: e.target.value })} /></label>
      <label className="ksv-fld">Đến ngày<input type="date" value={yc.den} min={yc.tu || homNay} onChange={(e) => setYc({ ...yc, den: e.target.value })} /></label>
      <label className="ksv-fld">Số khách<input type="number" min={chuaLich ? 1 : 2} max={2000} value={yc.so_khach} onChange={(e) => setYc({ ...yc, so_khach: e.target.value })} /></label>
      <label className="ksv-fld">Nơi khởi hành<input value={yc.noi} placeholder={sp?.noi_khoi_hanh || "TP HCM"} onChange={(e) => setYc({ ...yc, noi: e.target.value })} /></label>
      <label className="ksv-fld">Ngân sách / khách (₫)<input inputMode="numeric" value={yc.ngan_sach} onChange={(e) => setYc({ ...yc, ngan_sach: e.target.value.replace(/\D/g, "") })} /></label>
      <label className="ksv-fld">Hạng khách sạn<select className="ksv-sel" value={yc.hang_ks} onChange={(e) => setYc({ ...yc, hang_ks: e.target.value })}>
        {["", "3 sao", "4 sao", "5 sao", "Resort"].map((x) => <option key={x} value={x}>{x || "Chưa chọn"}</option>)}</select></label>
      <label className="ksv-fld">Công ty / người liên hệ<input value={yc.cong_ty} onChange={(e) => setYc({ ...yc, cong_ty: e.target.value })} /></label>
      <label className="ksv-fld">Số điện thoại<input inputMode="tel" value={yc.dien_thoai} placeholder={toi?.dien_thoai || "09xx xxx xxx"} onChange={(e) => setYc({ ...yc, dien_thoai: e.target.value })} /></label></div>
    <label className="ksv-fld">Yêu cầu riêng<textarea maxLength={1500} value={yc.ghi_chu} placeholder="Gala dinner, team building, ăn chay, xe đời mới…" onChange={(e) => setYc({ ...yc, ghi_chu: e.target.value })} /></label>
    <label className="ksv-chk"><input type="checkbox" checked={yc.hoa_don} onChange={(e) => setYc({ ...yc, hoa_don: e.target.checked })} /><span>Cần xuất hóa đơn công ty</span></label>
    <label className="ksv-chk"><input type="checkbox" checked={yc.dong_y} onChange={(e) => setYc({ ...yc, dong_y: e.target.checked })} /><span style={{ fontSize: 13 }}>Đồng ý để Sales Vietourist liên hệ báo giá. Gửi yêu cầu chưa giữ chỗ và chưa thu tiền.</span></label>
    {loi && <div className="ksv-loi">{loi}</div>}
    <button type="button" className="ksv-btn" style={{ alignSelf: "flex-start", minHeight: 50 }} disabled={busy} onClick={guiDoan}>{busy ? "Đang gửi…" : chuaLich ? "Gửi yêu cầu giữ chỗ" : "Gửi yêu cầu thiết kế tour"}</button></section>;
  // TK-1: «Tour đoàn theo yêu cầu» (không gắn tour mẫu) → màn tự thiết kế có tạm tính; tour mẫu / tour chưa có lịch giữ form cũ
  if (buoc === "doan") return <div className="ksv tra">{css}{thanhTim(true)}<button type="button" className="ksv-link" onClick={veDs}>← Tất cả tour</button>{sp ? formDoan : <TuThietKeTour toi={toi} />}</div>;

  // ═══════════════════════════════════ 3 · TRANG TOUR ═══════════════════════════════════
  if (buoc === "sp" && sp) {
    const anh: string[] = sp.anh || [];
    const doan = sp.loai === "doan" || !!sp.chua_co_lich;
    const keo = (id: string) => (e: React.MouseEvent) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }); };
    const ngayLt: any[] = lt?.ngay || [];
    return <div className="ksv tra">{css}{thanhTim(true)}
      <button type="button" className="ksv-link" onClick={veDs}>← {q.tab === "nuoc_ngoai" ? "Tour nước ngoài" : "Tour trong nước"}</button>
      <div className="ksv-gal tra-gal">{anh.length ? anh.slice(0, 5).map((a, i) => <span key={a}><img src={a} alt={`${sp.ten} — ảnh ${i + 1}`} loading={i ? "lazy" : "eager"} referrerPolicy="no-referrer" /></span>)
        : <span style={{ gridColumn: "1 / -1", gridRow: "1 / 3" }}><AnhTrong ten={sp.ten} cao={300} /></span>}</div>
      <nav className="ksv-tabs" aria-label="Mục của trang tour">{[["tra-tq", "Tổng quan"], [doan ? "tra-doan" : "tra-ngay", sp.chua_co_lich ? "Gửi yêu cầu" : doan ? "Yêu cầu thiết kế" : "Ngày khởi hành"], ["tra-lt", "Lịch trình"],
        ["tra-bg", "Bao gồm"], ["tra-cs", "Chính sách"]].map(([id, t]) => <a key={id} href={`#${id}`} onClick={keo(id)}>{t}</a>)}
        <span className="ksv-tp">{sp.gia_tu ? <><small className="ksv-muted">từ</small><b className="ksv-big" style={{ fontSize: 19 }}>₫ {vnd(sp.gia_tu)}</b><small className="ksv-muted">/ khách</small></> : null}
          <button type="button" className="ksv-btn" onClick={keo(doan ? "tra-doan" : "tra-ngay")}>{doan ? "Gửi yêu cầu" : "Chọn ngày"}</button></span></nav>
      <div className="ksv-two" id="tra-tq">
        <div className="ksv-panel" style={{ padding: 20 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}><h2 style={{ margin: 0, fontSize: 26 }}>{sp.ten}</h2>
            <span className="tra-tag">{sp.loai_ten}</span>{sp.wellness && <span className="tra-tag ok">Wellness &amp; retreat</span>}{sp.chua_co_lich && <span className="tra-tag">Lịch khởi hành đang cập nhật</span>}{sp.gio_chot && <span className="tra-tag hot">Giờ chót</span>}</div>
          <span className="ksv-muted">{sp.ma} · {sp.thoi_luong}{sp.noi_khoi_hanh ? ` · khởi hành ${sp.noi_khoi_hanh}` : ""}{sp.phuong_tien?.length ? ` · ${sp.phuong_tien.map((p: string) => PT[p] || p).join(", ")}` : ""}</span>
          {sp.khoi_hanh_text && <span>Lịch khởi hành: {sp.khoi_hanh_text}</span>}
          {sp.noi_bat?.length > 0 && <ul className="tra-nb">{sp.noi_bat.map((x: string) => <li key={x}>{x}</li>)}</ul>}
        </div>
        <div className="ksv-panel">{sp.gia_tu ? <><span className="ksv-muted">Giá từ</span>{sp.gia_goc && <span className="ksv-old">₫ {vnd(sp.gia_goc)}</span>}
          <b className="ksv-big">₫ {vnd(sp.gia_tu)}</b><span className="ksv-muted">/ người lớn · trẻ em ₫ {vnd(sp.gia_tre_em)}</span></>
          : sp.chua_co_lich ? (sp.gia_tham_khao ? <><span className="ksv-muted">Giá tham khảo từ</span><b className="ksv-big">₫ {vnd(sp.gia_tham_khao)}</b>
            <span className="ksv-muted">/ người lớn — theo bảng giá trên web; Sales báo giá chính xác theo ngày bạn chọn</span></> : <span className="ksv-muted">Giá liên hệ — Sales báo giá theo ngày bạn chọn.</span>)
          : <span className="ksv-muted">Báo giá theo hành trình và số khách.</span>}
          {sp.link_web && <a className="ksv-link" href={sp.link_web} target="_blank" rel="noopener noreferrer">Xem trang tour trên vietourist.com.vn ↗</a>}</div>
      </div>

      {doan ? formDoan : <section className="ksv-panel" id="tra-ngay" style={{ padding: 20 }}><div className="ksv-rhead"><h2 style={{ margin: 0, fontSize: 22 }}>Chọn ngày khởi hành</h2>
        <span className="ksv-muted">{soKhach}</span></div>
        <div className="tra-dates" role="group" aria-label="Ngày khởi hành">{sp.chuyen.map((c: any) => <button key={c.tour_id} type="button" disabled={!c.du_cho}
          className={`tra-dt${chon === c.tour_id ? " on" : ""}${c.du_cho ? "" : " off"}`} aria-pressed={chon === c.tour_id} onClick={() => setChon(c.tour_id)}>
          <b>{ngayDep(c.khoi_hanh)}</b>{c.du_cho ? <>{c.gia_goc && <s>₫ {vnd(c.gia_goc)}</s>}<span className="tra-pr">₫ {vnd(c.gia)}</span>
            <small>{c.con > 20 ? "Còn nhiều chỗ" : `Còn ${c.con} chỗ`}</small></> : <small>{c.con > 0 ? `Còn ${c.con} chỗ` : "Hết chỗ"}</small>}</button>)}</div>
        {loi && <div className="ksv-loi">{loi}</div>}
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="ksv-btn" style={{ minHeight: 50, padding: "0 26px" }} disabled={!chuyen || busy} onClick={moDat}>{chuyen ? `Đặt ngày ${ngayDep(chuyen.khoi_hanh)}` : "Chọn một ngày còn chỗ"}</button>
          <span className="ksv-muted">{sp.mo_thanh_toan ? `Giữ chỗ bằng cọc ${sp.coc_pt}% hoặc trả đủ · thẻ / QR` : "Thanh toán trực tuyến sắp mở — gửi yêu cầu giữ chỗ, Sales gọi lại"}</span></div>
      </section>}

      <section className="ksv-panel" id="tra-lt" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 22 }}>Lịch trình</h2>
        {ngayLt.length ? <ol className="tra-lt">{ngayLt.map((n: any) => <li key={n.ngay}><b>Ngày {n.ngay}{n.tieu_de ? ` · ${String(n.tieu_de).replace(/^\s*ng[aà]y\s*0?\d+\s*[:.\-–·]?\s*/i, "")}` : ""}</b>
          {(n.bua?.length > 0 || n.khach_san) && <small className="ksv-muted">{n.bua?.length ? `Bữa: ${n.bua.map((b: string) => BUA[b] || b).join(", ")}` : ""}{n.khach_san ? ` · ${n.khach_san}` : ""}</small>}
          {n.noi_dung && <p>{n.noi_dung}</p>}
          {n.anh?.length > 0 && <div className="tra-lt-anh">{n.anh.slice(0, 3).map((a: string) => <img key={a} src={a} alt={`Ngày ${n.ngay}`} loading="lazy" referrerPolicy="no-referrer" />)}</div>}</li>)}</ol>
          : lt?.van_ban ? <p style={{ whiteSpace: "pre-line", margin: 0, lineHeight: 1.65 }}>{lt.van_ban}</p>
          : <span className="ksv-muted">Chương trình chi tiết đang cập nhật — Sales gửi kèm xác nhận.</span>}</section>

      <section className="ksv-grid2" id="tra-bg">
        <div className="ksv-panel"><b>Giá bao gồm</b>{sp.bao_gom?.length ? <ul className="tra-ok">{sp.bao_gom.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
          : sp.dich_vu ? <p style={{ whiteSpace: "pre-line", margin: 0 }}>{sp.dich_vu}</p> : <span className="ksv-muted">Đang cập nhật.</span>}</div>
        <div className="ksv-panel"><b>Giá không bao gồm</b>{sp.khong_bao_gom?.length ? <ul className="tra-ko">{sp.khong_bao_gom.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
          : <span className="ksv-muted">Chi phí cá nhân và dịch vụ ngoài chương trình.</span>}</div>
      </section>
      {sp.bang_gia_web?.length > 0 && <section className="ksv-panel"><b>Bảng giá theo đối tượng (trang tour)</b>{sp.bang_gia_web.map((b: any, i: number) =>
        <div key={i} className="ksv-sum"><span>{b.doi_tuong}</span><span>{b.gia ? `₫ ${vnd(b.gia)}` : b.ghi || "—"}</span></div>)}
        <small className="ksv-muted">Giá đặt online theo từng ngày khởi hành ở trên.</small></section>}
      <section className="ksv-panel" id="tra-cs" style={{ padding: 20 }}><h2 style={{ margin: 0, fontSize: 20 }}>Chính sách</h2>
        {!doan && <span>Đặt cọc {sp.coc_pt}% để giữ chỗ; phần còn lại trả trước ngày khởi hành {sp.dong_so_truoc} ngày (17:00). Đặt sau hạn đó: thanh toán toàn bộ.</span>}
        {sp.quy_dinh ? <p style={{ whiteSpace: "pre-line", margin: 0, lineHeight: 1.6 }}>{sp.quy_dinh}</p> : <span className="ksv-muted">Điều kiện hủy gửi kèm xác nhận đặt tour.</span>}
        {sp.web_cap_nhat && <small className="ksv-muted">Nội dung đọc từ vietourist.com.vn lúc {sp.web_cap_nhat.replace("T", " ").slice(0, 16)}.</small>}</section>
    </div>;
  }

  // ═══════════════════════════════════ 1–2 · TÌM + DANH SÁCH ═══════════════════════════════════
  const coWell = tat.some((s) => s.wellness);
  // KS-19l (Chủ tịch chọn phương án C 06/11/2026): lối vào «Tour đoàn theo yêu cầu» nằm ngay dưới «Tour ghép» trong bộ lọc
  // Loại tour. Điện thoại giấu bộ lọc sau nút «Bộ lọc», nên ở đó lối vào hiện thêm một ô ngay đầu danh sách.
  const moDoan = () => { setMoLoc(false); setSp(null); setBuoc("doan"); len(); };
  return <div className="ksv tra">{css}{thanhTim()}
    {coWell && <button type="button" className="tra-well" onClick={() => setLoc({ ...LOC0, well: true })}>
      <span><b>Wellness &amp; Retreat</b><small>Nghỉ dưỡng, thiền, yoga, spa — trong nước và nước ngoài</small></span><em>Xem các tour wellness →</em></button>}
    {loi && <div className="ksv-loi">{loi}</div>}
    <div className="ksv-layout">
      <aside className={`ksv-loc${moLoc ? " open" : ""}`} aria-label="Bộ lọc">
        {moLoc && <button type="button" className="ksv-btn" onClick={() => setMoLoc(false)}>Xem {kq.length} tour</button>}
        {nhom("Loại tour", [["ghep", "Tour ghép", (s) => s.loai === "ghep"], ["doan", "Tour đoàn riêng", (s) => s.loai === "doan"]], "loai", false,
          <button type="button" className="tra-doan" onClick={moDoan}><b>Tour đoàn theo yêu cầu →</b><small>Tự thiết kế, xem giá tạm tính ngay</small></button>)}
        {dem((s) => s.wellness, "well") > 0 && <div className="ksv-panel"><b>Chủ đề</b><label className="ksv-chk"><input type="checkbox" checked={loc.well} onChange={(e) => setLoc({ ...loc, well: e.target.checked })} />
          <span>Wellness &amp; retreat</span><small>{dem((s) => s.wellness, "well")}</small></label></div>}
        {nhom("Thời lượng", TL.map(([k, t, f]) => [k, t, (s: any) => f(s.ngay)]), "tl")}
        {nhom("Giá mỗi khách", GIA.map(([k, t, f]) => [k, t, (s: any) => ((g) => g != null && f(g))(giaLoc(s))]), "gia", true)}
        {nhom("Ưu đãi", UD, "ud")}
        {nhom("Phương tiện", Object.entries(PT).map(([k, t]) => [k, (ds?.phuong_tien || PT)[k] || t, (s: any) => (s.phuong_tien || []).includes(k)]), "pt", true)}
      </aside>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 0 }}>
        <div className="ksv-rhead"><b style={{ fontSize: 18 }}>{ds ? `${kq.length} tour${q.q ? ` ${q.q}` : ""}` : "Đang tải tour…"}</b>
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}><button type="button" className="ksv-btn line ksv-fbtn" onClick={() => setMoLoc(true)}>Bộ lọc</button>
            <select className="ksv-sel" value={sx} onChange={(e) => setSx(e.target.value)} aria-label="Sắp xếp">
              <option value="som">Khởi hành sớm nhất</option><option value="gia_thap">Giá thấp nhất</option><option value="gia_cao">Giá cao nhất</option>
              <option value="ngan">Ngắn ngày trước</option><option value="dai">Dài ngày trước</option></select></span></div>
        <section className="ksv-panel tra-doan-dt"><b>Tour đoàn theo yêu cầu</b><span className="ksv-muted">Gia đình, doanh nghiệp, hội nhóm — tự chọn điểm đến, khách sạn, bữa ăn, phương tiện và xem giá tạm tính ngay.</span>
          <button type="button" className="ksv-btn line" style={{ alignSelf: "flex-start" }} onClick={moDoan}>Tự thiết kế tour đoàn</button></section>
        {kq.map((s: any) => <article key={s.id} className="ksv-card">
          {(s.gio_chot || s.khuyen_mai) && <div className="ksv-bar"><span>{s.gio_chot ? "Giờ chót — khởi hành trong vài ngày tới" : "Đang khuyến mại"}</span>{s.it_cho && <em>Còn ít chỗ</em>}</div>}
          <div className="ksv-crow">
            <div className="ksv-ph"><button type="button" className="ksv-phbtn" onClick={() => moSp(s.id)} aria-label={`Xem ${s.ten}`}>
              {s.anh?.[0] ? <img src={s.anh[0]} alt={s.ten} loading="lazy" referrerPolicy="no-referrer" /> : <AnhTrong ten={s.ten} />}</button>
              {s.anh?.length > 1 && <span className="ksv-ct">{s.anh.length} ảnh</span>}</div>
            <div className="ksv-info"><h3><button type="button" className="ksv-ten" onClick={() => moSp(s.id)}>{s.ten}</button></h3>
              <span className="ksv-muted" style={{ fontSize: 13 }}>{s.ma} · {s.thoi_luong}{s.noi_khoi_hanh ? ` · khởi hành ${s.noi_khoi_hanh}` : ""}{s.phuong_tien?.length ? ` · ${s.phuong_tien.map((p: string) => PT[p] || p).join(", ")}` : ""}</span>
              <div className="ksv-feat sm"><span>{s.loai_ten}</span>{s.wellness && <span>Wellness</span>}{s.diem_den && <span>{s.diem_den}</span>}{s.chua_co_lich && <span>Lịch khởi hành đang cập nhật</span>}</div>
              {s.noi_bat?.length > 0 && <span className="ksv-hl">{s.noi_bat.slice(0, 3).join(" · ")}</span>}
              {s.khoi_hanh_gan?.length > 0 && <span className="ksv-where" style={{ fontSize: 13 }}>{s.so_chuyen} ngày khởi hành · gần nhất {s.khoi_hanh_gan.slice(0, 3).map((k: string) => ngayDep(k)).join(", ")}</span>}</div>
            <div className="ksv-side">{s.gia_tu ? <><small className="ksv-muted">Từ</small>{s.gia_goc && <span className="ksv-old">₫ {vnd(s.gia_goc)}</span>}
              <b className="ksv-big">₫ {vnd(s.gia_tu)}</b><small className="ksv-muted">/ khách{s.gia_tre_em && s.gia_tre_em !== s.gia_tu ? ` · trẻ em ₫ ${vnd(s.gia_tre_em)}` : ""}</small></>
              : s.chua_co_lich ? (s.gia_tham_khao ? <><small className="ksv-muted">Giá tham khảo từ</small><b className="ksv-big">₫ {vnd(s.gia_tham_khao)}</b><small className="ksv-muted">theo bảng giá trên web</small></>
                : <span className="ksv-muted">Giá liên hệ</span>)
              : <span className="ksv-muted">{s.loai === "doan" ? "Báo giá theo yêu cầu" : "Hết chỗ cho số khách đã chọn"}</span>}
              <button type="button" className="ksv-btn wide" onClick={() => moSp(s.id)}>{s.loai === "doan" || s.chua_co_lich ? "Xem & gửi yêu cầu" : "Xem ngày đi"}</button></div>
          </div></article>)}
        {ds && !kq.length && <section className="ksv-panel"><span>Không có tour khớp. Thử bỏ bớt bộ lọc, đổi khoảng ngày, hoặc gửi yêu cầu thiết kế tour riêng.</span></section>}
      </div>
    </div>
  </div>;
}

const CSS = `
.tra-hero{background:var(--ksv-band);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:12px;color:#fff}
.tra-hero.gon{padding:10px}.tra-hero.gon .tra-tabs{display:none}
.tra-ht{font-size:22px}
.tra-tabs{display:flex;gap:6px}.tra-tabs button{border:0;border-radius:99px;min-height:40px;padding:0 18px;background:rgba(255,255,255,.12);color:#fff;font-weight:700}
.tra-tabs button.on,#vtd-access .tra .tra-tabs button.on{background:#fff;color:#14538D;-webkit-text-fill-color:#14538D}
#vtd-access .tra .tra-tabs button:not(.on){color:#fff;-webkit-text-fill-color:#fff}
.tra-gal{display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:170px 170px;gap:6px;border-radius:12px;overflow:hidden}
.tra-gal>span{position:relative;background:var(--ksv-soft);min-width:0}
.tra-gal>span:first-child{grid-row:span 2;grid-column:auto}
.tra-gal>span:nth-child(n+6){display:none}
.tra-gal img{width:100%;height:100%;object-fit:cover;display:block}
.tra-sbar{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr) minmax(0,1.6fr) minmax(0,1.2fr) minmax(0,.9fr) auto;gap:8px}
.tra-chips{display:flex;gap:8px;flex-wrap:wrap}
.tra-chip{min-height:36px;padding:0 14px;border-radius:99px;border:1px solid rgba(255,255,255,.4);background:transparent;color:#fff}
.tra-chip.on{background:#fff;color:var(--ksv-band);font-weight:700}
.tra-well{all:unset;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;background:linear-gradient(110deg,#e7f3ec,#f3efe2);border:1px solid #cfe2d6;border-radius:12px;padding:14px 18px}
.tra-well span{display:flex;flex-direction:column;gap:2px}.tra-well b{font-size:18px;color:#1f4d36}.tra-well small{color:#41594c}.tra-well em{font-style:normal;font-weight:700;color:#1f4d36}
.tra-well:focus-visible{outline:2px solid var(--ksv-accent)}
.tra-doan{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:2px;margin-top:4px;border:1.5px solid var(--ksv-accent);border-radius:10px;padding:10px 12px;min-height:44px;box-sizing:border-box}
.tra-doan b{font-size:14px;color:var(--ksv-accent)}.tra-doan small{font-size:12px;color:var(--ksv-muted)}
.tra-doan:hover{background:var(--ksv-soft)}.tra-doan:focus-visible{outline:2px solid var(--ksv-accent);outline-offset:2px}
.tra-doan-dt{display:none}
@media (max-width:900px){.tra-doan-dt{display:flex}}
.tra-tag{background:var(--ksv-soft);border-radius:99px;padding:3px 10px;font-size:12px;font-weight:600}
.tra-tag.ok{background:var(--ksv-oksoft);color:var(--ksv-ok)}.tra-tag.hot{background:#E8F0FB;color:#1E63C8}
.tra-nb{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:4px}
.tra-dates{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.tra-dt{display:flex;flex-direction:column;gap:2px;align-items:flex-start;text-align:left;border:1px solid var(--ksv-line);border-radius:10px;background:#fff;padding:10px 12px;min-height:84px}
.tra-dt s{color:var(--ksv-muted);font-size:12px}.tra-dt small{color:var(--ksv-muted);font-size:12px}
.tra-dt.on{border:2px solid var(--ksv-accent);background:var(--ksv-asoft);padding:9px 11px}
.tra-dt.off{opacity:.55;cursor:not-allowed;background:#f6f7f9}
.tra-pr{color:var(--ksv-price);font-weight:700;font-variant-numeric:tabular-nums}
.tra-lt{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0}
.tra-lt li{position:relative;padding:0 0 16px 28px;display:flex;flex-direction:column;gap:4px}
.tra-lt li::before{content:"";position:absolute;left:0;top:3px;width:14px;height:14px;border-radius:50%;background:var(--ksv-accent)}
.tra-lt li::after{content:"";position:absolute;left:6px;top:20px;bottom:0;width:2px;background:#d5dae3}.tra-lt li:last-child::after{display:none}
.tra-lt p{margin:0;white-space:pre-line;line-height:1.6;max-width:80ch}
.tra-lt-anh{display:flex;gap:8px;flex-wrap:wrap}.tra-lt-anh img{width:180px;height:120px;object-fit:cover;border-radius:8px;background:var(--ksv-soft)}
.tra-ok,.tra-ko{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:6px}
.tra-ok li::before{content:"✓ ";color:var(--ksv-ok);font-weight:700}.tra-ko li::before{content:"✕ ";color:#1E63C8;font-weight:700}
.tra-khach{border-top:1px solid var(--ksv-line);padding-top:10px;display:flex;flex-direction:column;gap:8px}
.tra-k4{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr) minmax(0,.7fr) minmax(0,1.2fr);gap:10px}
.tra-tom-anh{width:100%;height:150px;object-fit:cover;border-radius:8px}
.tra-xong-dau{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.tra-qr{margin:0;display:flex;flex-direction:column;align-items:center;gap:4px;font-size:12px;color:var(--ksv-muted)}
.tra-qr img{border:1px solid var(--ksv-line);border-radius:10px;background:#fff}
.tra-a{display:inline-flex;align-items:center;text-decoration:none}
@media (max-width:1100px){.tra-sbar{grid-template-columns:1fr 1fr}.tra-sbar .ksv-btn-tim{grid-column:span 2}}
@media (max-width:900px){.tra-gal{grid-template-columns:1fr 1fr;grid-template-rows:200px 110px}.tra-gal>span:first-child{grid-column:1 / -1;grid-row:auto}.tra-gal>span:nth-child(n+4){display:none}}
@media (max-width:640px){.tra-sbar{grid-template-columns:1fr}.tra-sbar .ksv-btn-tim{grid-column:auto}.tra-k4{grid-template-columns:1fr 1fr}.tra-ht{font-size:18px}}
`;
