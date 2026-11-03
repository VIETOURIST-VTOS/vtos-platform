"use client";
/* TK-1 · KHÁCH TỰ THIẾT KẾ TOUR ĐOÀN — giai đoạn 1 (Chủ tịch 04/11/2026, gộp bản xem thử v7 với bản Codex).
   Sáu phần trên một trang: 1 nhóm & sở thích → 2 chuyến đi (trong nước / nước ngoài, khởi hành, ngày, khách, phòng)
   → 3 điểm đến theo thứ tự + số đêm + khách sạn từng điểm → 4 từng ngày (chặng + phương tiện + hãng bay, bữa trưa / tối,
   điểm tham quan; ăn sáng tại khách sạn tự có) → 5 dịch vụ cả chuyến → 6 tạm tính + gửi Sales.
   Trình duyệt CHỈ gửi lựa chọn; mọi con số tiền do máy chủ tính (/khach/tour-doan/tinh). Mục chưa có nguồn giá hiện
   «Sales báo giá», không tính 0. Chỗ nào danh sách không có thì có «Khác…» để khách tự ghi. */
import { useEffect, useMemo, useRef, useState } from "react";
import { goiCong } from "@/lib/cong";
import { DD, SB, XA, goiYPt, hangGoiY } from "./tuThietKeDuLieu";

const vnd = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");
const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const cong = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };
const ngayVn = (s: string) => s.split("-").reverse().slice(0, 2).join("/");
const KHOI_HANH = ["TP HCM", "Hà Nội", "Đà Nẵng", "Cần Thơ", "Hải Phòng", "Nha Trang", "Huế"];
const PT: [string, string][] = [["xe", "Xe du lịch"], ["bay", "Máy bay"], ["tau", "Tàu hỏa"], ["thuyen", "Du thuyền / tàu cao tốc"], ["khac", "Khác… (tự ghi)"]];
const HANG_VE: [string, string][] = [["pho_thong", "Phổ thông"], ["pho_thong_dac_biet", "Phổ thông đặc biệt"], ["thuong_gia", "Thương gia"]];
const NHOM: [string, string][] = [["gia_dinh", "Gia đình"], ["ban_be", "Bạn bè"], ["cong_ty", "Công ty / MICE"]];
const NHIP: [string, string][] = [["thu_tha", "Thư thả"], ["can_bang", "Cân bằng"], ["nhieu", "Nhiều trải nghiệm"]];
const DV: [string, string, string][] = [["hdv", "Hướng dẫn viên suốt tuyến", "ca"], ["bao_hiem", "Bảo hiểm du lịch", "ca"], ["nuoc", "Nước suối mỗi ngày", "ca"],
  ["visa", "Visa nhập cảnh", "nn"], ["hoi_nghi", "Phòng hội nghị (MICE)", "ca"], ["team_building", "Team building", "ca"]];

type Bua = { tu_tuc?: boolean; thuc_don_id?: number; khac?: string };
type Ngay = { trua: Bua; toi: Bua; tham_quan: string[] };
type Diem = { ten: string; dem: number; ks: { khach_san_id?: number; goi_id?: number; ten_khac?: string } };
type Chang = { pt: string; hang_bay: string; hang_ve: string; khac: string; tu_dong?: boolean; key?: string };

function Dem({ nhan, phu, v, dat, min = 0, max = 300 }: { nhan: string; phu?: string; v: number; dat: (n: number) => void; min?: number; max?: number }) {
  return <div className="ksv-step"><span>{nhan}{phu && <small className="ksv-muted" style={{ display: "block" }}>{phu}</small>}</span>
    <div><button type="button" aria-label={`Bớt ${nhan}`} disabled={v <= min} onClick={() => dat(Math.max(min, v - 1))}>−</button><b style={{ minWidth: 24, textAlign: "center" }}>{v}</b>
      <button type="button" aria-label={`Thêm ${nhan}`} disabled={v >= max} onClick={() => dat(Math.min(max, v + 1))}>+</button></div></div>;
}

export default function TuThietKeTour({ toi }: { toi?: any }) {
  const homNay = iso(new Date());
  const [pv, setPv] = useState<"dn" | "nn">("dn");
  const [nhom, setNhom] = useState("cong_ty"); const [nhip, setNhip] = useState("can_bang");
  const [nganSach, setNganSach] = useState(""); const [uuTien, setUuTien] = useState("");
  const [kh, setKh] = useState("TP HCM"); const [khKhac, setKhKhac] = useState("");
  const [ngayDi, setNgayDi] = useState(cong(homNay, 30));
  const [k, setK] = useState({ nl: 20, te: 0, eb: 0 }); const [tuoi, setTuoi] = useState<number[]>([]);
  const [ph, setPh] = useState({ p2: 10, p3: 0, p1: 0 }); const [tayPhong, setTayPhong] = useState(false);
  const [hangKs, setHangKs] = useState("");
  const [diem, setDiem] = useState<Diem[]>([]); const [ddKhac, setDdKhac] = useState(""); const [moKhac, setMoKhac] = useState(false);
  const [ngay, setNgay] = useState<Ngay[]>([]); const [chang, setChang] = useState<Chang[]>([]);
  const [dv, setDv] = useState<string[]>(["hdv", "bao_hiem", "nuoc"]);
  const [mo, setMo] = useState<"" | "khach" | "phong">("");
  const [nguon, setNguon] = useState<Record<string, any>>({});
  const [kq, setKq] = useState<any>(null); const [loiTinh, setLoiTinh] = useState("");
  const [gui, setGui] = useState({ dien_thoai: toi?.dien_thoai || "", ghi_chu: "", dong_y: false });
  const [daGui, setDaGui] = useState<any>(null); const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const [them, setThem] = useState<Record<number, string>>({});
  const nn = pv === "nn";
  const khoiHanh = kh === "khac" ? (khKhac.trim() || "Khác") : kh;

  // Tự xếp phòng: ưu tiên phòng đôi, lẻ một người lớn → một phòng 3
  useEffect(() => {
    if (tayPhong) return;
    const n = k.nl; setPh(n % 2 && n >= 3 ? { p2: (n - 3) / 2, p3: 1, p1: 0 } : { p2: Math.ceil(n / 2), p3: 0, p1: 0 });
  }, [k.nl, tayPhong]);
  useEffect(() => { setTuoi((t) => Array.from({ length: k.te }, (_, i) => t[i] ?? 8)); }, [k.te]);

  // Khung ngày — cùng phép với máy chủ (thiet_ke_doan.khung)
  const N = useMemo(() => {
    const ra: any[] = []; let i = 0;
    diem.forEach((h, hi) => {
      for (let d = 0; d < Math.max(1, h.dem); d++) {
        const tu = hi === 0 ? khoiHanh : diem[hi - 1].ten;
        ra.push({ i, ngay: cong(ngayDi, i), o: h.ten, hi, dem: h.dem > d, ci: d === 0 ? hi : null, tu: d === 0 ? tu : null, den: d === 0 ? h.ten : null }); i++;
      }
    });
    if (diem.length) { const c = diem[diem.length - 1].ten; ra.push({ i, ngay: cong(ngayDi, i), o: c, hi: diem.length - 1, dem: false, ci: diem.length, tu: c, den: khoiHanh, ve: true }); }
    return ra;
  }, [diem, ngayDi, khoiHanh]);

  // Giữ mảng ngày / chặng đúng độ dài; chặng đổi điểm thì gợi ý lại phương tiện
  useEffect(() => { setNgay((x) => N.map((_, i) => x[i] || { trua: {}, toi: {}, tham_quan: [] })); }, [N]);
  useEffect(() => {
    setChang((x) => N.filter((d) => d.ci !== null).map((d) => {
      const key = `${d.tu}>${d.den}`; const cu = x[d.ci];
      return cu && cu.key === key ? cu : { pt: goiYPt(d.tu, d.den, nn), hang_bay: "", hang_ve: "pho_thong", khac: "", key };
    }));
  }, [N, nn]);

  // Nguồn khách sạn + nhà hàng theo từng điểm (giá đã là giá bán tạm tính)
  const offs = useMemo(() => { let o = 0; return diem.map((h) => { const v = o; o += Math.max(1, h.dem); return v; }); }, [diem]);
  const khoaNguon = (h: Diem, hi: number) => `${h.ten}|${cong(ngayDi, offs[hi])}|${cong(ngayDi, offs[hi] + Math.max(1, h.dem))}|${k.nl}|${k.te}`;
  useEffect(() => {
    diem.forEach((h, hi) => {
      const key = khoaNguon(h, hi);
      if (nguon[key]) return;
      const q = new URLSearchParams({ diem: h.ten, vao: cong(ngayDi, offs[hi]), ra: cong(ngayDi, offs[hi] + Math.max(1, h.dem)), nguoi_lon: "2", tre_em: "0", so_phong: "1" });
      setNguon((x) => ({ ...x, [key]: { dang: true, khach_san: [], nha_hang: [] } }));
      goiCong(`/khach/tour-doan/nguon?${q.toString()}`).then((r) => setNguon((x) => ({ ...x, [key]: r })))
        .catch(() => setNguon((x) => ({ ...x, [key]: { khach_san: [], nha_hang: [] } })));
    });
  }, [diem, ngayDi, offs]); // eslint-disable-line react-hooks/exhaustive-deps

  const thietKe = () => ({
    pham_vi: pv, khoi_hanh: khoiHanh, ngay_di: ngayDi, nhom, nhip, ngan_sach: nganSach ? Number(nganSach) : null, uu_tien: uuTien,
    khach: { ...k, tuoi_tre: tuoi }, phong: ph, hang_ks: hangKs, diem, ngay,
    chang: chang.map(({ pt, hang_bay, hang_ve, khac }) => ({ pt, hang_bay, hang_ve, khac })), dich_vu: dv, ghi_chu: gui.ghi_chu });

  // Tạm tính: gọi máy chủ sau mỗi lần đổi (đợi 600 ms)
  const hen = useRef<any>(null);
  useEffect(() => {
    if (!diem.length || !ngayDi) { setKq(null); return; }
    clearTimeout(hen.current);
    hen.current = setTimeout(() => {
      goiCong("/khach/tour-doan/tinh", { thiet_ke: thietKe() }).then((r) => { setKq(r.du_toan); setLoiTinh(""); })
        .catch((x) => { setKq(null); setLoiTinh(x.message); });
    }, 600);
    return () => clearTimeout(hen.current);
  }, [pv, kh, khKhac, ngayDi, nhom, nhip, nganSach, k, tuoi, ph, hangKs, diem, ngay, chang, dv]); // eslint-disable-line react-hooks/exhaustive-deps

  const doiPv = (v: "dn" | "nn") => { if (v === pv) return; setPv(v); setDiem([]); setDv(v === "nn" ? ["hdv", "bao_hiem", "nuoc", "visa"] : ["hdv", "bao_hiem", "nuoc"]); };
  const themDiem = (ten: string) => { const t = ten.trim(); if (!t) return; setDiem((d) => [...d, { ten: t, dem: 2, ks: {} }]); setDdKhac(""); setMoKhac(false); };
  const suaDiem = (i: number, o: Partial<Diem>) => setDiem((d) => d.map((x, j) => (j === i ? { ...x, ...o } : x)));
  const doiCho = (i: number, j: number) => setDiem((d) => { const c = [...d]; [c[i], c[j]] = [c[j], c[i]]; return c; });
  const suaNgay = (i: number, o: Partial<Ngay>) => setNgay((d) => d.map((x, j) => (j === i ? { ...x, ...o } : x)));
  const suaChang = (i: number, o: Partial<Chang>) => setChang((d) => d.map((x, j) => (j === i ? { ...x, ...o } : x)));
  const xa = nn && diem.some((h) => XA.has(h.ten));
  const ngu = k.nl + k.te, choNgu = 2 * ph.p2 + 3 * ph.p3 + ph.p1, soPhong = ph.p2 + ph.p3 + ph.p1;

  const guiDi = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach/tour-doan/gui", { thiet_ke: thietKe(), dien_thoai: gui.dien_thoai, dong_y: gui.dong_y, ma: daGui?.ma || "" });
      setDaGui(r); setKq(r.du_toan);
      try { window.scrollTo(0, 0); } catch { /* bỏ qua */ }
    } catch (x: any) { setLoi(x.message); } finally { setBusy(false); }
  };

  // ── ô chọn bữa: thực đơn nhà hàng tại điểm + Tự túc + Khác…
  const chonBua = (i: number, kieu: "trua" | "toi", nhs: any[]) => {
    const b = ngay[i]?.[kieu] || {};
    const v = b.tu_tuc ? "tu" : b.thuc_don_id ? String(b.thuc_don_id) : b.khac !== undefined ? "khac" : "";
    return <div className="tk-hang"><span className="tk-nh">Ăn {kieu === "trua" ? "trưa" : "tối"}</span>
      <select className="ksv-sel" value={v} onChange={(e) => {
        const x = e.target.value;
        suaNgay(i, { [kieu]: x === "tu" ? { tu_tuc: true } : x === "khac" ? { khac: "" } : x ? { thuc_don_id: Number(x) } : {} } as any);
      }}>
        <option value="">Chưa chọn</option><option value="tu">Tự túc</option>
        {nhs.map((n) => <optgroup key={n.id} label={n.ten}>{n.thuc_don.map((t: any) =>
          <option key={t.id} value={t.id}>{n.ten} · {t.ten}{t.gia_nguoi_lon ? ` — ${vnd(t.gia_nguoi_lon)}₫/khách` : ""}{t.so_khach_toi_thieu > 1 ? ` (từ ${t.so_khach_toi_thieu} khách)` : ""}</option>)}</optgroup>)}
        <option value="khac">Khác… (tự ghi)</option></select>
      {b.khac !== undefined && !b.tu_tuc && !b.thuc_don_id && <input className="tk-in" value={b.khac} maxLength={160} placeholder="Tên nhà hàng / món mong muốn"
        onChange={(e) => suaNgay(i, { [kieu]: { khac: e.target.value } } as any)} />}
    </div>;
  };

  const dsDiem = DD[pv];
  return <div className="ksv tk">
    <style>{CSS}</style>
    {daGui && <section className="ksv-panel tk-ok"><b>Đã gửi thiết kế {daGui.ma} · phiên bản {daGui.phien_ban}</b>
      <span>Sales Vietourist liên hệ để chốt dịch vụ và gửi báo giá chính thức. Bạn vẫn sửa được bên dưới và bấm «Gửi lại phiên bản mới».</span></section>}
    <section className="ksv-panel"><h2 style={{ margin: 0, fontSize: 20 }}>Tự thiết kế tour đoàn</h2>
      <span className="ksv-muted">Chọn điểm đến, khách sạn, bữa ăn, phương tiện theo lịch trình của đoàn. Giá tạm tính lấy từ bảng giá Vietourist; mục chưa có giá Sales báo sau.</span></section>

    {/* 1 · Nhóm & sở thích */}
    <section className="ksv-panel"><h3 className="tk-h">1 · Nhóm & sở thích</h3>
      <div className="tk-chips" role="group" aria-label="Loại đoàn">{NHOM.map(([v, t]) => <button key={v} type="button" aria-pressed={nhom === v} onClick={() => setNhom(v)}>{t}</button>)}</div>
      <div className="tk-chips" role="group" aria-label="Nhịp đi">{NHIP.map(([v, t]) => <button key={v} type="button" aria-pressed={nhip === v} onClick={() => setNhip(v)}>{t}</button>)}</div>
      <div className="ksv-f2">
        <label className="ksv-fld">Ngân sách / khách (₫)<input inputMode="numeric" value={nganSach ? vnd(Number(nganSach)) : ""} placeholder="Không bắt buộc" onChange={(e) => setNganSach(e.target.value.replace(/\D/g, ""))} /></label>
        <label className="ksv-fld">Điều quan trọng với đoàn<input value={uuTien} maxLength={300} placeholder="Gala dinner, nghỉ dưỡng, ăn chay…" onChange={(e) => setUuTien(e.target.value)} /></label></div>
    </section>

    {/* 2 · Chuyến đi */}
    <section className="ksv-panel"><h3 className="tk-h">2 · Chuyến đi</h3>
      <div className="tk-chips" role="group" aria-label="Phạm vi"><button type="button" aria-pressed={!nn} onClick={() => doiPv("dn")}>Trong nước</button>
        <button type="button" aria-pressed={nn} onClick={() => doiPv("nn")}>Nước ngoài</button></div>
      <div className="ksv-f2">
        <label className="ksv-fld">Khởi hành từ<select className="ksv-sel" value={kh} onChange={(e) => setKh(e.target.value)}>
          {KHOI_HANH.map((x) => <option key={x}>{x}</option>)}<option value="khac">Khác… (tự ghi)</option></select>
          {kh === "khac" && <input className="tk-in" value={khKhac} maxLength={80} placeholder="Tỉnh / thành khởi hành" onChange={(e) => setKhKhac(e.target.value)} />}</label>
        <label className="ksv-fld">Ngày khởi hành<input type="date" value={ngayDi} min={cong(homNay, 1)} onChange={(e) => setNgayDi(e.target.value)} /></label>
        <div className="ksv-fld" style={{ position: "relative" }}>Số khách
          <button type="button" className="tk-dd" aria-expanded={mo === "khach"} onClick={() => setMo(mo === "khach" ? "" : "khach")}>
            {k.nl + k.te + k.eb} khách · {k.nl} NL{k.te ? `, ${k.te} trẻ` : ""}{k.eb ? `, ${k.eb} bé` : ""} ▾</button>
          {mo === "khach" && <div className="ksv-pop" style={{ left: 0, right: "auto" }}>
            <Dem nhan="Người lớn" phu="từ 12 tuổi" v={k.nl} min={1} dat={(n) => setK({ ...k, nl: n })} />
            <Dem nhan="Trẻ em" phu={nn ? "2–11 tuổi" : "5–11 tuổi"} v={k.te} dat={(n) => setK({ ...k, te: n })} max={100} />
            {k.te > 0 && k.te <= 12 && <div className="tk-tuoi">{tuoi.map((t, i) => <label key={i}>Trẻ {i + 1}<select className="ksv-sel" value={t}
              onChange={(e) => setTuoi(tuoi.map((x, j) => (j === i ? Number(e.target.value) : x)))}>{Array.from({ length: 12 }, (_, a) => <option key={a} value={a}>{a} tuổi</option>)}</select></label>)}</div>}
            <Dem nhan="Em bé" phu={nn ? "dưới 2 tuổi" : "dưới 5 tuổi"} v={k.eb} dat={(n) => setK({ ...k, eb: n })} max={50} />
            <button type="button" className="ksv-btn" onClick={() => setMo("")}>Xong</button></div>}
        </div>
        <div className="ksv-fld" style={{ position: "relative" }}>Phòng
          <button type="button" className="tk-dd" aria-expanded={mo === "phong"} onClick={() => setMo(mo === "phong" ? "" : "phong")}>
            {[ph.p2 && `${ph.p2} đôi`, ph.p3 && `${ph.p3} phòng 3`, ph.p1 && `${ph.p1} đơn`].filter(Boolean).join(" · ") || "Chưa xếp"} ▾</button>
          {mo === "phong" && <div className="ksv-pop" style={{ left: 0, right: "auto" }}>
            <Dem nhan="Phòng đôi / twin" phu="2 khách" v={ph.p2} dat={(n) => { setTayPhong(true); setPh({ ...ph, p2: n }); }} max={200} />
            <Dem nhan="Phòng 3 (triple)" phu="3 khách" v={ph.p3} dat={(n) => { setTayPhong(true); setPh({ ...ph, p3: n }); }} max={200} />
            <Dem nhan="Phòng đơn" phu="1 khách" v={ph.p1} dat={(n) => { setTayPhong(true); setPh({ ...ph, p1: n }); }} max={200} />
            <span className={choNgu < ngu ? "ksv-loi" : "ksv-muted"}>{soPhong} phòng · ngủ được {choNgu}/{ngu} khách{k.eb ? " (em bé ngủ cùng bố mẹ)" : ""}</span>
            <button type="button" className="ksv-btn line" onClick={() => setTayPhong(false)}>Tự xếp phòng</button>
            <button type="button" className="ksv-btn" onClick={() => setMo("")}>Xong</button></div>}
        </div>
        <label className="ksv-fld">Hạng khách sạn<select className="ksv-sel" value={hangKs} onChange={(e) => setHangKs(e.target.value)}>
          <option value="">Chưa chọn</option><option value="3">3 sao</option><option value="4">4 sao</option><option value="5">5 sao</option></select></label>
      </div>
    </section>

    {/* 3 · Điểm đến */}
    <section className="ksv-panel"><h3 className="tk-h">3 · Điểm đến theo thứ tự</h3>
      <label className="ksv-fld">{nn ? "Thêm quốc gia" : "Thêm điểm đến"}<select className="ksv-sel" value="" onChange={(e) => { if (e.target.value === "__khac") setMoKhac(true); else themDiem(e.target.value); }}>
        <option value="">{nn ? "Chọn quốc gia…" : "Chọn điểm đến…"}</option>
        {Object.entries(dsDiem).map(([g, ds]) => <optgroup key={g} label={g}>{ds.map((t) => <option key={t} value={t}>{t}</option>)}</optgroup>)}
        <option value="__khac">Khác… (tự ghi)</option></select></label>
      {moKhac && <div className="tk-hang"><input className="tk-in" autoFocus value={ddKhac} maxLength={80} placeholder={nn ? "Thành phố / quốc gia" : "Tên điểm đến"}
        onChange={(e) => setDdKhac(e.target.value)} onKeyDown={(e) => e.key === "Enter" && themDiem(ddKhac)} /><button type="button" className="ksv-btn" onClick={() => themDiem(ddKhac)}>Thêm</button></div>}
      {!diem.length && <span className="ksv-muted">Chưa có điểm đến — chọn một điểm ở trên để bắt đầu.</span>}
      {diem.map((h, hi) => {
        const ng = nguon[khoaNguon(h, hi)];
        const kv = h.ks.goi_id ? `${h.ks.khach_san_id}:${h.ks.goi_id}` : h.ks.ten_khac !== undefined ? "khac" : "";
        return <div key={hi} className="tk-diem">
          <div className="tk-hang"><b>{hi + 1}. {h.ten}</b><span className="ksv-muted">{ngayVn(cong(ngayDi, offs[hi]))}</span>
            <span className="tk-dem"><button type="button" aria-label="Bớt đêm" onClick={() => suaDiem(hi, { dem: Math.max(0, h.dem - 1) })}>−</button>
              <b>{h.dem} đêm</b><button type="button" aria-label="Thêm đêm" onClick={() => suaDiem(hi, { dem: Math.min(14, h.dem + 1) })}>+</button></span>
            <button type="button" className="tk-nho" disabled={!hi} aria-label="Lên" onClick={() => doiCho(hi, hi - 1)}>↑</button>
            <button type="button" className="tk-nho" disabled={hi === diem.length - 1} aria-label="Xuống" onClick={() => doiCho(hi, hi + 1)}>↓</button>
            <button type="button" className="tk-nho" onClick={() => setDiem(diem.filter((_, j) => j !== hi))}>Bỏ</button></div>
          {h.dem > 0 && <div className="tk-hang"><span className="tk-nh">Khách sạn</span>
            <select className="ksv-sel" value={kv} onChange={(e) => {
              const x = e.target.value;
              if (x === "khac") suaDiem(hi, { ks: { ten_khac: "" } });
              else if (!x) suaDiem(hi, { ks: {} });
              else { const [a, b] = x.split(":").map(Number); suaDiem(hi, { ks: { khach_san_id: a, goi_id: b } }); }
            }}>
              <option value="">{ng?.dang ? "Đang tải khách sạn…" : ng?.khach_san?.length ? "Chọn khách sạn…" : "Chưa có khách sạn VTD tại đây"}</option>
              {(ng?.khach_san || []).filter((x: any) => !hangKs || String(x.sao) === hangKs || !x.sao).map((x: any) => <optgroup key={x.id} label={`${x.ten}${x.sao ? ` · ${x.sao}★` : ""}`}>
                {x.phong.flatMap((p: any) => p.goi.map((g: any) => <option key={g.id} value={`${x.id}:${g.id}`}>{x.ten} · {p.ten} · {g.ten}{g.bua_sang ? " (ăn sáng)" : ""} — {vnd(g.gia_dem)}₫/đêm</option>))}</optgroup>)}
              <option value="khac">Khác… (tự ghi)</option></select>
            {h.ks.ten_khac !== undefined && !h.ks.goi_id && <input className="tk-in" value={h.ks.ten_khac} maxLength={120} placeholder="Tên khách sạn mong muốn"
              onChange={(e) => suaDiem(hi, { ks: { ten_khac: e.target.value } })} />}</div>}
        </div>;
      })}
    </section>

    {/* 4 · Từng ngày */}
    {N.length > 0 && <section className="ksv-panel"><h3 className="tk-h">4 · Lịch trình từng ngày ({N.length} ngày)</h3>
      {N.map((d) => {
        const h = diem[d.hi]; const ng = h ? nguon[khoaNguon(h, d.hi)] : null; const nhs = ng?.nha_hang || [];
        const c = d.ci !== null ? chang[d.ci] : null;
        const truoc = d.i > 0 && N[d.i - 1].dem; const ksTruoc = truoc ? diem[N[d.i - 1].hi]?.ks : null;
        const goiSang = ksTruoc?.goi_id ? (nguon[khoaNguon(diem[N[d.i - 1].hi], N[d.i - 1].hi)]?.khach_san || [])
          .flatMap((x: any) => x.phong.flatMap((p: any) => p.goi)).find((g: any) => g.id === ksTruoc.goi_id) : null;
        const x = ngay[d.i] || { trua: {}, toi: {}, tham_quan: [] };
        return <div key={d.i} className="tk-ngay">
          <div className="tk-hang"><b>Ngày {d.i + 1} · {ngayVn(d.ngay)}</b><span className="ksv-muted">{d.ci !== null ? `${d.tu} → ${d.den}` : d.o}</span></div>
          {c && <><div className="tk-hang"><span className="tk-nh">Chặng {d.tu} → {d.den}</span>
            <select className="ksv-sel" value={c.pt} onChange={(e) => suaChang(d.ci, { pt: e.target.value })}>
              {PT.map(([v, t]) => <option key={v} value={v}>{t}{v === goiYPt(d.tu, d.den, nn) ? " (gợi ý)" : ""}</option>)}</select></div>
            {c.pt === "bay" && <div className="tk-hang"><span className="tk-nh">Hãng bay</span>
              <select className="ksv-sel" value={c.hang_bay} onChange={(e) => suaChang(d.ci, { hang_bay: e.target.value })}>
                <option value="">Hãng nào cũng được — giờ bay, giá tốt nhất</option>
                {hangGoiY(d.tu, d.den, nn).map((t) => <option key={t}>{t}</option>)}</select>
              <select className="ksv-sel" value={c.hang_ve} onChange={(e) => suaChang(d.ci, { hang_ve: e.target.value })}>{HANG_VE.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select>
              {!nn && SB[d.tu] && SB[d.den] && <span className="ksv-muted">{SB[d.tu]} → {SB[d.den]}</span>}</div>}
            {c.pt === "khac" && <div className="tk-hang"><span className="tk-nh" /><input className="tk-in" value={c.khac} maxLength={160} placeholder="VD: limousine riêng, trực thăng…"
              onChange={(e) => suaChang(d.ci, { khac: e.target.value })} /></div>}</>}
          {truoc && <div className="tk-hang"><span className="tk-nh">Ăn sáng</span><span>{ksTruoc?.goi_id ? (goiSang?.bua_sang ? "Tại khách sạn" : "Gói phòng không gồm ăn sáng") : "Tại khách sạn (theo gói phòng)"}</span></div>}
          {chonBua(d.i, "trua", nhs)}{chonBua(d.i, "toi", nhs)}
          <div className="tk-hang"><span className="tk-nh">Tham quan</span><div className="tk-chips">{x.tham_quan.map((t, j) =>
            <button key={j} type="button" aria-pressed="true" onClick={() => suaNgay(d.i, { tham_quan: x.tham_quan.filter((_, q) => q !== j) })}>{t} ×</button>)}</div>
            <input className="tk-in" value={them[d.i] || ""} maxLength={120} placeholder="Gõ điểm tham quan rồi Enter"
              onChange={(e) => setThem({ ...them, [d.i]: e.target.value })}
              onKeyDown={(e) => { if (e.key === "Enter" && (them[d.i] || "").trim()) { suaNgay(d.i, { tham_quan: [...x.tham_quan, them[d.i].trim()] }); setThem({ ...them, [d.i]: "" }); } }} /></div>
        </div>;
      })}
    </section>}

    {/* 5 · Dịch vụ cả chuyến */}
    <section className="ksv-panel"><h3 className="tk-h">5 · Dịch vụ cả chuyến</h3>
      {DV.filter(([, , p]) => p === "ca" || nn).map(([v, t]) => <label key={v} className="ksv-chk"><input type="checkbox" checked={dv.includes(v)}
        onChange={(e) => setDv(e.target.checked ? [...dv, v] : dv.filter((z) => z !== v))} />
        <span>{v === "hdv" && xa ? "Trưởng đoàn kiêm hướng dẫn viên suốt tuyến" : t}</span></label>)}
      {nn && <span className="ksv-muted">Tips tài xế và HDV địa phương không gồm trong giá — trưởng đoàn thu của khách và chi lại tại điểm đến.</span>}
    </section>

    {/* 6 · Tạm tính + gửi */}
    <section className="ksv-panel tk-tinh"><h3 className="tk-h">6 · Tạm tính</h3>
      {!diem.length && <span className="ksv-muted">Thêm điểm đến để xem tạm tính.</span>}
      {loiTinh && <div className="ksv-loi">{loiTinh}</div>}
      {kq && <>
        <table className="tk-bang"><thead><tr><th>Hạng mục</th><th>Tính theo</th><th style={{ textAlign: "right" }}>Tạm tính</th></tr></thead>
          <tbody>{kq.dong.map((x: any, i: number) => <tr key={i}><td><small className="ksv-muted">{x.nhom}</small><br />{x.ten}</td><td>{x.chi_tiet}</td><td style={{ textAlign: "right" }}>{vnd(x.ban)}₫</td></tr>)}</tbody></table>
        <div className="ksv-sum"><b>Tổng tạm tính ({kq.so_ngay} ngày {kq.so_dem} đêm)</b><b className="ksv-big">₫ {vnd(kq.tong_ban)}</b></div>
        {kq.moi_khach && <span className="ksv-muted">Bình quân ₫ {vnd(kq.moi_khach)} / khách (để so ngân sách — chưa phải giá bán người lớn / trẻ em).</span>}
        {kq.thieu_gia.length > 0 && <div className="tk-thieu"><b>Sales báo giá ({kq.thieu_gia.length} mục chưa tính)</b>
          <ul>{kq.thieu_gia.map((x: any, i: number) => <li key={i}>{x.nhom}: {x.ten} — {x.ly_do}</li>)}</ul></div>}
        {kq.canh_bao.length > 0 && <div className="ksv-hv"><ul style={{ margin: 0, paddingLeft: 18 }}>{kq.canh_bao.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul></div>}
        <div className="ksv-f2"><div><b>Bao gồm</b><ul className="tk-ul">{kq.bao_gom.map((x: string) => <li key={x}>{x}</li>)}</ul></div>
          <div><b>Không bao gồm</b><ul className="tk-ul">{kq.khong_bao_gom.map((x: string) => <li key={x}>{x}</li>)}</ul></div></div>
      </>}
      <div className="ksv-f2">
        <label className="ksv-fld">Số điện thoại<input inputMode="tel" value={gui.dien_thoai} placeholder="09xx xxx xxx" onChange={(e) => setGui({ ...gui, dien_thoai: e.target.value })} /></label>
        <label className="ksv-fld">Ghi chú cho Sales<input value={gui.ghi_chu} maxLength={1000} placeholder="Gala, hóa đơn công ty, ăn chay…" onChange={(e) => setGui({ ...gui, ghi_chu: e.target.value })} /></label></div>
      {!daGui && <label className="ksv-chk"><input type="checkbox" checked={gui.dong_y} onChange={(e) => setGui({ ...gui, dong_y: e.target.checked })} />
        <span style={{ fontSize: 13 }}>Tôi hiểu tạm tính chưa phải báo giá; gửi thiết kế chưa giữ chỗ và chưa thu tiền. Sales Vietourist liên hệ xác nhận.</span></label>}
      {loi && <div className="ksv-loi">{loi}</div>}
      <button type="button" className="ksv-btn" disabled={busy || !diem.length} onClick={guiDi}>{busy ? "Đang gửi…" : daGui ? "Gửi lại phiên bản mới" : "Gửi thiết kế cho Sales"}</button>
    </section>
  </div>;
}

const CSS = `
.tk .tk-h{margin:0;font-size:16px}
.tk-chips{display:flex;flex-wrap:wrap;gap:6px}
.tk-chips button{border:1px solid var(--ksv-line);background:#fff;border-radius:99px;padding:6px 12px;font-size:13px;color:var(--ksv-fg)}
.tk-chips button[aria-pressed="true"]{background:var(--ksv-asoft);border-color:var(--ksv-accent);color:var(--ksv-ink);font-weight:600}
.tk-hang{display:flex;flex-wrap:wrap;gap:8px;align-items:center;min-width:0}
.tk-hang>select,.tk-hang>.tk-in{flex:1 1 220px;min-width:0}
.tk-nh{flex:0 0 120px;font-size:13px;color:var(--ksv-muted)}
@media (max-width:560px){.tk-nh{flex-basis:100%}}
.tk-in{border:1px solid var(--ksv-line);border-radius:8px;padding:8px 10px;font:inherit;min-height:40px;background:#fff;color:var(--ksv-fg)}
.tk-dd{all:unset;cursor:pointer;border:1px solid var(--ksv-line);border-radius:8px;padding:8px 10px;min-height:24px;background:#fff;font-weight:600}
.tk-tuoi{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px;font-size:12px}
.tk-diem,.tk-ngay{border:1px solid var(--ksv-line);border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:8px}
.tk-dem{display:inline-flex;align-items:center;gap:8px}
.tk-dem button,.tk-nho{border:1px solid var(--ksv-line);background:#fff;border-radius:8px;min-width:34px;min-height:34px}
.tk-nho:disabled{opacity:.4}
.tk-bang{width:100%;border-collapse:collapse;font-size:13px}
.tk-bang th,.tk-bang td{border-bottom:1px solid var(--ksv-line);padding:6px 4px;vertical-align:top;text-align:left}
.tk-thieu{background:#fff4dc;color:#6d4300;border-radius:10px;padding:10px 14px;font-size:13px}
.tk-thieu ul,.tk-ul{margin:4px 0 0;padding-left:18px;font-size:13px}
.tk-ok{background:var(--ksv-oksoft);border-color:var(--ksv-ok)}
`;
