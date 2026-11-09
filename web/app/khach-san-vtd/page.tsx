"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { AnhNoiBo } from "@/components/nha-hang/AlbumNhaHang";
import VideoNoiBo from "@/components/VideoNoiBo";   // KS-16f
import DanhGiaKsNoiBo from "@/components/khach-san-vtd/DanhGiaKsNoiBo";

/** KS-13 · KHÁCH SẠN HỢP TÁC (CỔNG KHÁCH) — Chủ tịch duyệt bản demo 30/10/2026.
 *  NV / TP Điều hành nhập khách sạn, ảnh, loại phòng, gói giá và mùa giá (chỉ GIÁ BÁN, đã gồm 8% VAT — KS-19 / P0-03).
 *  TP Điều hành duyệt giá — người nhập không tự duyệt (trừ Chủ tịch, TGĐ). Sửa gói đã duyệt → về Nháp, thôi hiện.
 *  KS-16c (Chủ tịch 31/10/2026): bỏ duyệt ảnh — tải là hiện; người tải tự xóa, TP Điều hành xóa mọi ảnh.
 *  TP Điều hành bật «Hiện trên cổng» khi đủ điều kiện; người vừa sửa hồ sơ không tự bật.
 *  KS-14 (Chủ tịch duyệt bản xem thử 30/10/2026): khách trả ngay 100%. Điều hành sửa số phòng bán mỗi đêm (tab «Phòng trống»),
 *  chốt đơn đã trả với khách sạn hoặc báo hết phòng (tab «Đơn đặt phòng»); Sales xác nhận hoàn, Kế toán ghi sổ thu hộ,
 *  đối soát thẻ, hoàn tiền, chốt hoa hồng (tab «Tiền & hoàn»). */
const tien = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "");
const TT_DN: Record<string, string> = { cho_tp: "chờ robot", cho_kt: "robot dừng — bổ sung NCC", cho_duyet: "chờ TGĐ / CT duyệt", cho_chi: "lệnh chi chờ", da_chi: "đã chi", tu_choi: "từ chối" };   // KS-16d
const KS0 = { ten: "", tinh_thanh: "", khu_vuc: "", dia_chi: "", sao: 0, loai: "khach_san", km_trung_tam: "", gan: "", noi_bat: "", mo_ta: "",
  tien_ich: [] as string[], gio_nhan: "14:00", gio_tra: "12:00", cs_tre_em: "", cs_giuong_phu: "", cs_vat_nuoi: "", cs_khac: "", thue_phi_pt: "" as any, thue_phi_xac_nhan: false, phu_hop: [] as string[],
  lien_he_noi_bo: "", ghi_chu_noi_bo: "", link_ggmap: "",
  cs_nhan_tre_em: "chua_xac_nhan", cs_tre_tu_tuoi: "" as any, cs_moc_tuoi: [] as any[], cs_phi_giuong_phu: "" as any, cs_giuong_phu_an_sang: false, cs_noi: "",
  cs_so_tre_mien_phi: "" as any, cs_tre_mp_tinh_suc_chua: false, cs_giuong_phu_kieu: "co_dinh" };
// KS-16j (Chủ tịch duyệt bản xem thử 01/11/2026): trống = chưa xác nhận (null), khác 0; số phòng 0 là 0; không tự cắt đặc điểm.
// KS-17: người lớn tối đa và tổng khách để trống = CHƯA XÁC NHẬN (bản cũ tự gán 2 / 1).
const LP0 = { ten: "", dien_tich: 0, giuong: "", mo_ta: "", toi_da_nguoi_lon: "" as any, tong_khach_toi_da: "" as any, toi_da_tre_em: "" as any, so_phong: 0, thu_tu: 0, dang_ban: false,
  mo_ta_dai: "", tien_nghi: [] as string[], giuong_phu_toi_da: "" as any, noi_cui: null as boolean | null, nguon: "", ky_doi_chieu: "", ma_hang: "",
  ten_tuong_duong: "", can_xac_nhan: [] as string[], ghi_chu_doi_chieu: "", trang_thai_dc: "dang_doi_chieu" };
const soHoacNull = (v: any) => (v === "" || v === null || v === undefined ? null : Number(v));
const MUA0 = { tu_ngay: "", den_ngay: "", gia_thuong: "", gia_cuoi_tuan: "", gia_niem_yet: "", ghi_chu: "" };
const TT: Record<string, string> = { nhap: "", cho_duyet: "warn", da_duyet: "ok", tra_lai: "bad", an: "" };

async function guiTep(path: string, fd: FormData) {
  const headers: Record<string, string> = {}; const tok = getToken();
  if (tok) headers["Authorization"] = `Bearer ${tok}`;
  const r = await fetch(`/api/v1${path}`, { method: "POST", headers, body: fd });
  const d = await r.json().catch(() => null);
  if (!r.ok) throw { status: r.status, message: typeof d?.detail === "string" ? d.detail : `Lỗi ${r.status}` };
  return d;
}

function Trang() {
  const { toast } = useShell();
  const [x, setX] = useState<any>(null);
  const [tab, setTab] = useState<"ds" | "cd" | "don" | "tien" | "dg">("ds");
  const [demDon, setDemDon] = useState<any>({});
  useEffect(() => { api<any>("/khach-san-vtd/don?loc=cho_chot").then((r) => setDemDon(r.dem || {})).catch(() => {}); }, [tab]);
  const [mo, setMo] = useState<number | "moi" | null>(null);
  const [tim, setTim] = useState("");
  const [locBan, setLocBan] = useState<"" | "thieu" | "khong">("");   // P0-02
  const load = useCallback(() => { api("/khach-san-vtd").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const k = (s: string) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase();
  const banKhong = (h: any) => !!h.ban_cong && h.ban_cong.ma !== "den" && h.ban_cong.ma !== "ngung";   // P0-02
  const banThieu = (h: any) => !!h.ban_cong?.thieu_30;
  const ds = x.khach_san.filter((h: any) => (!tim || k(`${h.ten} ${h.ma} ${h.tinh_thanh} ${h.khu_vuc}`).includes(k(tim)))
    && (!locBan || (locBan === "thieu" ? banThieu(h) : banKhong(h))));
  return (<>
    <h1>Khách sạn (cổng khách)</h1>
    <p className="muted">Khách sạn VTD có hợp đồng trực tiếp. Điều hành nhập khách sạn, ảnh, loại phòng và GIÁ BÁN theo mùa (đã gồm 8% VAT); TP Điều hành duyệt
      ảnh, giá và bật «Hiện trên cổng». Người nhập không tự duyệt / tự bật (trừ Chủ tịch, TGĐ). Gói đã duyệt: khách đặt và trả ngay 100% (QR / thẻ),
      Điều hành chốt với khách sạn ở tab «Đơn đặt phòng»; chưa có giá thì khách gửi yêu cầu vào màn «Đơn khách sạn OTA › Yêu cầu của khách».
      Tiền phòng là tiền thu hộ khách sạn; hoa hồng Kế toán chốt ở tab «Tiền &amp; hoàn».</p>
    <div style={{ display: "flex", gap: 6, margin: "10px 0" }}>
      <button className={`act ${tab === "ds" ? "teal" : "grey"}`} onClick={() => setTab("ds")}>Khách sạn ({x.khach_san.length})</button>
      <button className={`act ${tab === "cd" ? "teal" : "grey"}`} onClick={() => setTab("cd")}>Chờ duyệt ({x.cho_duyet.goi} gói giá)</button>
      <button className={`act ${tab === "don" ? "teal" : "grey"}`} onClick={() => setTab("don")}>Đơn đặt phòng{demDon.cho_chot ? ` (${demDon.cho_chot} chờ chốt)` : ""}</button>
      <button className={`act ${tab === "tien" ? "teal" : "grey"}`} onClick={() => setTab("tien")}>Tiền &amp; hoàn</button>
      <button className={`act ${tab === "dg" ? "teal" : "grey"}`} onClick={() => setTab("dg")}>Đánh giá</button></div>
    {tab === "cd" && <ChoDuyet toast={toast} onDoi={load} />}
    {tab === "don" && <DonDat toast={toast} />}
    {tab === "tien" && <TienHoan toast={toast} />}
    {tab === "dg" && <DanhGiaKsNoiBo toast={toast} />}
    {tab === "ds" && mo === null && <section className="panel">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm tên, mã, thành phố" aria-label="Tìm khách sạn" style={{ maxWidth: 260 }} />
        <span style={{ flex: 1 }} />
        {x.duoc_duyet && <button className="act grey" onClick={async () => { try { const r = await api<any>("/khach-san-vtd/hien-cong-loat", { method: "POST", json: {} }); toast(r.message); load(); } catch (e) { toast(errMsg(e), true); } }}
          title="KS-16l: bật mọi khách sạn đủ hồ sơ + ảnh + giới thiệu; chưa có gói đặt được thì cổng mở trang web chính ở tab mới">Bật hiện tất cả khách sạn đủ điều kiện</button>}
        {x.duoc_duyet && <button className="act grey" onClick={async () => { toast("Đang lấy tọa độ — mỗi khách sạn khoảng 1 giây…"); try { const r = await api<any>("/khach-san-vtd/toa-do-loat", { method: "POST", json: {} }); toast(r.message); load(); } catch (e) { toast(errMsg(e), true); } }}
          title="KS-16s: máy tra địa chỉ (OpenStreetMap) cho khách sạn chưa có tọa độ; ghim Điều hành dán tay không bị ghi đè">Lấy tọa độ cho tất cả khách sạn</button>}
        {x.duoc_nhap && <button className="act teal" onClick={() => setMo("moi")}>+ Thêm khách sạn</button>}</div>
      {/* P0-02: lọc nhanh hồ sơ thiếu giá — chỉ xét gói giá đã duyệt, đang bán */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
        {([["", `Tất cả (${x.khach_san.length})`], ["thieu", `Thiếu giá ${BAN_NGAY} ngày tới (${x.khach_san.filter(banThieu).length})`],
          ["khong", `Chưa bán được (${x.khach_san.filter(banKhong).length})`]] as const).map(([v, t]) =>
          <button key={v} className={`act ${locBan === v ? "teal" : "grey"}`} aria-pressed={locBan === v} onClick={() => setLocBan(v)}>{t}</button>)}</div>
      {/* KS-16s: công tắc chung mở thanh toán trực tuyến — khách chỉ trả được khi công tắc chung VÀ công tắc của khách sạn đều bật */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", padding: "8px 10px", margin: "8px 0", borderRadius: 8, border: `1px solid ${x.tt_chung ? "#2bb39a" : "#d99a2b"}` }}>
        <b>Thanh toán trực tuyến cổng khách sạn:</b><Tag cls={x.tt_chung ? "ok" : "warn"}>{x.tt_chung ? "Đang MỞ" : "Đang ĐÓNG"}</Tag>
        <span className="muted" style={{ flex: 1, minWidth: 220 }}>Đóng: khách vẫn tìm, xem, chọn phòng, điền thông tin; bước thanh toán cuối bị khóa. Mở chung rồi bật từng khách sạn ở tab «Hiện trên cổng».</span>
        {x.duoc_duyet && <button className={`act ${x.tt_chung ? "grey" : "teal"}`} onClick={async () => { try { const r = await api<any>("/khach-san-vtd/thanh-toan-chung", { method: "POST", json: { bat: !x.tt_chung } }); toast(r.message); load(); } catch (e) { toast(errMsg(e), true); } }}>
          {x.tt_chung ? "Đóng thanh toán toàn cổng" : "Mở thanh toán toàn cổng"}</button>}</div>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th></th><th>Khách sạn</th><th>Thành phố</th><th>Ảnh</th><th>Loại phòng</th><th>Gói giá</th><th>Cổng khách</th><th>Bán được trên cổng</th><th></th></tr></thead>
        <tbody>{ds.map((h: any) => <tr key={h.id} className="ksv-dong">
          <td style={{ width: 72 }}>{h.bia ? <AnhNoiBo src={h.bia} alt={h.ten} style={{ width: 64, height: 48, borderRadius: 6 }} /> : <span className="muted">—</span>}</td>
          <td><b>{h.ten}</b><div className="muted">{h.ma} · {"★".repeat(h.sao) || "chưa xếp sao"}</div></td>
          <td>{h.tinh_thanh}<div className="muted">{h.khu_vuc}</div></td>
          <td>{h.anh_duyet} duyệt{h.anh_cho ? <> · <Tag cls="warn">{h.anh_cho} chờ</Tag></> : null}<div className="muted">{h.so_anh} ảnh{h.thieu_anh ? ` · thiếu ${h.thieu_anh}` : ""}</div>
            {/* P1-02: phòng chưa có ảnh riêng (cổng đang lấy ảnh khách sạn thay, có nhãn) và ảnh chưa phân nhóm */}
            {h.lp_chua_anh > 0 && <div><Tag cls="warn">{h.lp_chua_anh}/{h.lp_ban} loại phòng chưa có ảnh</Tag></div>}
            {h.anh_khac > 0 && <div><Tag cls="warn">{h.anh_khac} ảnh nhóm «Khác»</Tag></div>}
            {!h.lp_chua_anh && h.lp_ban > 0 && <div><Tag cls="ok">Ảnh phòng đủ</Tag></div>}</td>
          <td>{h.so_loai_phong}</td>
          <td>{h.goi_duyet} duyệt{h.goi_cho ? <> · <Tag cls="warn">{h.goi_cho} chờ</Tag></> : null}</td>
          <td>{h.ngung ? <Tag cls="bad">Ngừng hợp tác</Tag> : h.hien_cong ? <Tag cls="ok">Đang hiện</Tag> : <Tag cls="warn">Chưa hiện</Tag>}</td>
          <td><BanCong b={h.ban_cong} /></td>
          <td><button className="act grey" onClick={() => setMo(h.id)}>{x.duoc_nhap ? "Mở" : "Xem"}</button></td></tr>)}
          {!ds.length && <tr><td colSpan={9} className="muted">{x.khach_san.length ? "Không có khách sạn khớp." : "Chưa có khách sạn hợp tác. Bấm «+ Thêm khách sạn»."}</td></tr>}</tbody></table></div>
    </section>}
    {tab === "ds" && mo !== null && <HoSo x={x} kid={mo} toast={toast} onDong={() => { setMo(null); load(); }} onMoi={(id) => { setMo(id); load(); }} onDoi={load} />}
  </>);
}

const BAN_NGAY = 30;   // P0-02: khớp BAN_CONG_NGAY_CANH_BAO ở máy chủ
const dmY = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");

/** P0-02 (Chủ tịch duyệt 09/11/2026): khách sạn bán được trên cổng đến ngày nào — chỉ xét giá; phòng trống xem tab «Phòng trống». */
function BanCong({ b }: { b: any }) {
  if (!b) return <span className="muted">—</span>;
  const [cls, nhan, ghi] =
    b.ma === "ngung" ? ["bad", "Ngừng hợp tác", ""]
    : b.ma === "chua_hien" ? ["bad", "Chưa hiện trên cổng", b.den ? `Có giá đến ${dmY(b.den)}` : b.tu ? `Có giá từ ${dmY(b.tu)}` : "Chưa có mùa giá"]
    : b.ma === "chua_goi" ? ["bad", "Chưa bán được", "Chưa có gói đã duyệt đang bán"]
    : b.ma === "het_gia" ? ["bad", "Chưa bán được", "Mùa giá đã hết, chưa nhập mùa mới"]
    : b.ma === "tu_ngay" ? ["warn", `Từ ${dmY(b.tu)}`, "Từ hôm nay đến trước ngày này chưa có mùa giá"]
    : [b.thieu_30 ? "warn" : "ok", `Đến ${dmY(b.den)}`, b.thieu_30 ? `Chỉ còn ${b.dem} đêm có giá` : `Liền ${b.dem} đêm từ hôm nay`];
  return <><Tag cls={cls}>{nhan}</Tag>{ghi && <div className="muted">{ghi}</div>}</>;
}

function HoSo({ x, kid, toast, onDong, onMoi, onDoi }: { x: any; kid: number | "moi"; toast: (m: string, l?: boolean) => void; onDong: () => void; onMoi: (id: number) => void; onDoi: () => void }) {
  const [h, setH] = useState<any>(null);
  const [f, setF] = useState<any>(KS0);
  const [t, setT] = useState<"tt" | "anh" | "video" | "phong" | "trong" | "hien">("tt");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => {
    if (kid === "moi") { setH(null); setF(KS0); return; }
    api<any>(`/khach-san-vtd/${kid}`).then((r) => { setH(r); setF({ ...KS0, ...r.khach_san, km_trung_tam: r.khach_san.km_trung_tam ?? "" }); }).catch((e) => toast(errMsg(e), true));
  }, [kid, toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); load(); onDoi(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  const nhap = x.duoc_nhap;
  const o = (key: string, label: string, ph = "", type = "text") => <label>{label}<input type={type} value={f[key] ?? ""} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [key]: e.target.value })} /></label>;
  const ta = (key: string, label: string, rows = 3, ph = "") => <label>{label}<textarea rows={rows} value={f[key] ?? ""} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [key]: e.target.value })} /></label>;
  const luu = async () => {
    const body = { ...f, sao: Number(f.sao) || 0, km_trung_tam: f.km_trung_tam === "" ? null : Number(f.km_trung_tam), thue_phi_pt: soHoacNull(f.thue_phi_pt), thue_phi_xac_nhan: !!f.thue_phi_xac_nhan,   // KS-17
      cs_tre_tu_tuoi: soHoacNull(f.cs_tre_tu_tuoi), cs_phi_giuong_phu: soHoacNull(String(f.cs_phi_giuong_phu ?? "").replace(/[^\d.]/g, "")),
      cs_so_tre_mien_phi: soHoacNull(f.cs_so_tre_mien_phi), cs_moc_tuoi: guiBang(f.cs_moc_tuoi) };   // KS-16k
    const r = await goi(kid === "moi" ? "/khach-san-vtd" : `/khach-san-vtd/${kid}`, body);
    if (r && kid === "moi") onMoi(r.id);
  };
  return <section className="panel" id="ksv-ho-so">
    <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
      <h2 style={{ margin: 0 }}>{kid === "moi" ? "Thêm khách sạn" : h ? `${h.khach_san.ten}` : "…"}</h2>
      {h && <span className="muted">{h.khach_san.ma}</span>}{h && (h.khach_san.hien_cong ? <Tag cls="ok">Đang hiện trên cổng</Tag> : <Tag cls="warn">Chưa hiện</Tag>)}
      <span style={{ flex: 1 }} /><button className="act grey" onClick={onDong}>Đóng</button></div>
    {kid !== "moi" && <div style={{ display: "flex", gap: 4, flexWrap: "wrap", borderBottom: "1px solid var(--line, #2a3b4d)", margin: "10px 0" }}>
      {([["tt", "Thông tin"], ["anh", `Album ảnh (${h?.anh.length ?? 0}/${h?.album?.toi_da ?? 50})`], ["video", `Video (${h?.so_video ?? 0}/${h?.video_toi_da ?? 3})`], ["phong", `Loại phòng & giá (${h?.loai_phong.length ?? 0})`], ["trong", "Phòng trống"], ["hien", "Hiện trên cổng"]] as const).map(([k2, t2]) =>
        <button key={k2} className={`act ${t === k2 ? "teal" : "grey"}`} onClick={() => setT(k2)}>{t2}</button>)}</div>}
    {(kid === "moi" || t === "tt") && <>
      <div className="grid">
        {o("ten", "Tên khách sạn")}
        <label>Thành phố<select value={f.tinh_thanh} disabled={!nhap} onChange={(e) => setF({ ...f, tinh_thanh: e.target.value })}><option value="">— chọn —</option>
          {x.thanh_pho.map((c: any) => <option key={c.ten} value={c.ten}>{c.ten} · {c.mien}</option>)}</select></label>
        {o("khu_vuc", "Khu vực", "Mỹ Khê, Hải Châu…")}{o("dia_chi", "Địa chỉ (máy tự lấy vị trí bản đồ)")}
        {o("link_ggmap", "Link Google Maps (sửa ghim)", "https://www.google.com/maps/place/…/@16.06,108.24,17z")}
        <label>Hạng sao<select value={f.sao} disabled={!nhap} onChange={(e) => setF({ ...f, sao: Number(e.target.value) })}>{[0, 1, 2, 3, 4, 5].map((s) => <option key={s} value={s}>{s ? `${s} sao` : "Chưa xếp hạng"}</option>)}</select></label>
        <label>Loại chỗ ở<select value={f.loai} disabled={!nhap} onChange={(e) => setF({ ...f, loai: e.target.value })}>{Object.entries(x.loai).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
        {o("km_trung_tam", "Cách trung tâm (km) — trống: máy tính từ vị trí", "2.5", "number")}{o("gan", "Gần đâu (hiện trên thẻ)", "120 m tới biển · 3 km tới cầu Rồng")}
        {o("noi_bat", "Một dòng nổi bật", "Hồ bơi tầng thượng nhìn biển, bữa sáng buffet")}
        {o("gio_nhan", "Giờ nhận phòng", "14:00")}{o("gio_tra", "Giờ trả phòng", "12:00")}
        {/* KS-19 (Chủ tịch 05/11/2026): giá nhập đã gồm 8% VAT — máy không cộng thuế phí. Chưa xác nhận → không duyệt giá, không mở thanh toán. */}
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={!!f.thue_phi_xac_nhan} disabled={!nhap}
          onChange={(e) => setF({ ...f, thue_phi_xac_nhan: e.target.checked })} />Đã xác nhận với khách sạn: giá nhập đã gồm 8% VAT</label>
        {!f.thue_phi_xac_nhan && <span className="muted" style={{ color: "#d99a2b", fontSize: 12 }}>Chưa xác nhận giá gồm VAT — chưa duyệt giá, chưa mở thanh toán được.</span>}</div>
      {h && <span className="muted" style={{ fontSize: 12 }}>Vị trí bản đồ: {h.khach_san.vi_do != null ? <>{h.khach_san.vi_do}, {h.khach_san.kinh_do} · {h.khach_san.toa_do_nguon === "tay" ? "Điều hành dán link" : "máy lấy từ địa chỉ"}
        {" · "}<a href={`https://www.google.com/maps/search/?api=1&query=${h.khach_san.vi_do},${h.khach_san.kinh_do}`} target="_blank" rel="noopener noreferrer">kiểm tra trên Google Maps ↗</a></>
        : h.khach_san.toa_do_nguon === "khong_thay" ? "máy không tìm thấy địa chỉ — dán link Google Maps" : "chưa có (lưu hồ sơ để máy lấy)"}</span>}
      {ta("mo_ta", "Giới thiệu cho khách", 4)}
      <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10 }}><legend>Tiện nghi</legend>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 6 }}>{Object.entries(x.tien_ich).map(([k2, v]: any) =>
          <label key={k2} style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" disabled={!nhap} checked={f.tien_ich.includes(k2)}
            onChange={(e) => setF({ ...f, tien_ich: e.target.checked ? [...f.tien_ich, k2] : f.tien_ich.filter((y: string) => y !== k2) })} />{v}</label>)}</div></fieldset>
      {x.phu_hop && <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10 }}><legend>Phù hợp cho (bộ lọc trên cổng)</legend>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 6 }}>{Object.entries(x.phu_hop).map(([k2, v]: any) =>
          <label key={k2} style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" disabled={!nhap} checked={(f.phu_hop || []).includes(k2)}
            onChange={(e) => setF({ ...f, phu_hop: e.target.checked ? [...(f.phu_hop || []), k2] : (f.phu_hop || []).filter((y: string) => y !== k2) })} />{v}</label>)}</div></fieldset>}
      <CsTre f={f} setF={setF} x={x} nhap={nhap} />
      <div className="grid">{o("cs_tre_em", "Ghi chú thêm về trẻ em")}{o("cs_giuong_phu", "Ghi chú thêm về giường phụ")}{o("cs_vat_nuoi", "Vật nuôi")}</div>
      {ta("cs_khac", "Chính sách khác", 2)}
      <div className="grid">{o("lien_he_noi_bo", "Liên hệ khách sạn (nội bộ, không lên cổng)")}</div>
      {ta("ghi_chu_noi_bo", "Ghi chú nội bộ (không lên cổng)", 2)}
      {nhap && <button className="act teal" disabled={busy} onClick={luu}>{kid === "moi" ? "Thêm khách sạn" : "Lưu hồ sơ"}</button>}
    </>}
    {h && t === "anh" && <Album h={h} x={x} toast={toast} onDoi={() => { load(); onDoi(); }} />}
    {h && t === "video" && <VideoNoiBo goc="/khach-san-vtd" oid={h.khach_san.id} toast={toast} loaiPhong={h.loai_phong.map((p: any) => ({ id: p.id, ten: p.ten }))} onDoi={load} />}
    {h && t === "phong" && <Phong h={h} x={x} toast={toast} goi={goi} busy={busy} />}
    {h && t === "trong" && <PhongTrong kid={h.khach_san.id} toast={toast} />}
    {h && t === "hien" && <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <b>Điều kiện bật «Hiện trên cổng»</b>
      {h.dieu_kien.map((c: any) => <span key={c.ma} style={{ color: c.ok ? "#2bb39a" : "#d99a2b" }}>{c.ok ? "✓" : "✗"} {c.ten}</span>)}
      <span className="muted">Chưa có loại phòng đang bán với gói giá đã duyệt thì khách sạn vẫn hiện nhưng chưa đặt trên cổng — khách xem và gửi yêu cầu giữ phòng ở kh.vietourist.vn/hotel.</span>
      {x.duoc_duyet && <div style={{ display: "flex", gap: 8 }}>
        {h.khach_san.hien_cong ? <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/${kid}/hien-cong`, { bat: false })}>Tắt hiện</button>
          : <button className="act teal" disabled={busy || h.khach_san.ngung} onClick={() => goi(`/khach-san-vtd/${kid}/hien-cong`, { bat: true })}>Bật hiện trên cổng</button>}
        <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/${kid}/ngung`, { bat: !h.khach_san.ngung })}>{h.khach_san.ngung ? "Hợp tác lại" : "Ngừng hợp tác"}</button></div>}
      {!x.duoc_duyet && <span className="muted">TP Điều hành bật hiện.</span>}
      <b style={{ marginTop: 8 }}>Thanh toán trực tuyến của khách sạn này</b>
      <span><Tag cls={h.khach_san.mo_thanh_toan ? "ok" : "warn"}>{h.khach_san.mo_thanh_toan ? "Đã bật" : "Chưa bật"}</Tag>{" "}
        <span className="muted">Công tắc chung: {x.tt_chung ? "đang mở" : "đang đóng"} — khách chỉ trả được khi cả hai đều bật. Bật khi đã kiểm giá, phòng trống, chính sách.</span></span>
      {x.duoc_duyet && <div><button className={`act ${h.khach_san.mo_thanh_toan ? "grey" : "teal"}`} disabled={busy} onClick={() => goi(`/khach-san-vtd/${kid}/thanh-toan`, { bat: !h.khach_san.mo_thanh_toan })}>
        {h.khach_san.mo_thanh_toan ? "Đóng thanh toán khách sạn này" : "Mở thanh toán khách sạn này"}</button></div>}
    </div>}
  </section>;
}

function Album({ h, x, toast, onDoi }: { h: any; x: any; toast: (m: string, l?: boolean) => void; onDoi: () => void }) {
  const [teps, setTeps] = useState<File[]>([]);
  const [nhom, setNhom] = useState("");
  const [lp, setLp] = useState("");
  const [nguon, setNguon] = useState("");
  const [tien, setTien] = useState("");
  const [chon, setChon] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [sua, setSua] = useState<any>(null);   // KS-17: ảnh đang sửa {id, nhom, loai_phong_id, chu_thich, mo_ta_thay_the}
  const kid = h.khach_san.id;
  const tai = async () => {
    if (!teps.length || !nhom) { toast("Chọn tệp ảnh và nhóm ảnh", true); return; }
    setBusy(true); let ok = 0;
    for (let i = 0; i < teps.length; i++) {
      setTien(`Đang tải ${i + 1}/${teps.length}…`);
      try { const fd = new FormData(); fd.append("tep", teps[i]); fd.append("nhom", nhom); fd.append("loai_phong_id", lp); fd.append("nguon", nguon);
        await guiTep(`/khach-san-vtd/${kid}/anh`, fd); ok++; }
      catch (e) { toast(`${teps[i].name}: ${errMsg(e)}`, true); }
    }
    setBusy(false); setTien(""); setTeps([]); toast(`Đã tải ${ok}/${teps.length} ảnh`); onDoi();
  };
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setChon([]); onDoi(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const tenLp: Record<number, string> = Object.fromEntries(h.loai_phong.map((p: any) => [p.id, p.ten]));
  const luuSua = async () => {   // KS-17: sửa ảnh đã có — không phải xóa rồi tải lại
    await goi(`/khach-san-vtd/anh/${sua.id}`, { nhom: sua.nhom, loai_phong_id: sua.loai_phong_id === "" ? null : Number(sua.loai_phong_id),
      chu_thich: sua.chu_thich, mo_ta_thay_the: sua.mo_ta_thay_the });
    setSua(null);
  };
  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    {x.duoc_nhap && <div className="panel" style={{ margin: 0 }}>
      <div className="grid">
        <label>Ảnh (JPG / PNG / WEBP, chọn nhiều)<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(e) => setTeps(Array.from(e.target.files || []))} /></label>
        <label>Nhóm ảnh<select value={nhom} onChange={(e) => setNhom(e.target.value)}><option value="">— chọn —</option>{Object.entries(x.nhom_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Ảnh của loại phòng (nếu là ảnh phòng)<select value={lp} onChange={(e) => setLp(e.target.value)}><option value="">— không —</option>{h.loai_phong.map((p: any) => <option key={p.id} value={p.id}>{p.ten}</option>)}</select></label>
        <label>Nguồn ảnh (nội bộ)<input value={nguon} onChange={(e) => setNguon(e.target.value)} placeholder="Khách sạn gửi qua email 30/10 / VTD tự chụp" /></label></div>
      <button className="act teal" disabled={busy || !teps.length} onClick={tai}>Tải {teps.length || ""} ảnh lên</button> {tien && <span className="muted">{tien}</span>}</div>}
    <p className="muted" style={{ margin: 0, fontSize: 12 }}>Ảnh tải lên là hiện ngay trên cổng (Chủ tịch bỏ khâu duyệt ảnh 31/10/2026). Ảnh sai: người tải tự xóa, TP Điều hành xóa được mọi ảnh.</p>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 10 }}>{h.anh.map((a: any) =>
      <div key={a.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
        <AnhNoiBo src={a.nho} alt={a.mo_ta_thay_the || a.chu_thich || a.nhom_ten} style={{ width: "100%", aspectRatio: "4 / 3", borderRadius: 6 }} />
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <Tag cls={TT[a.trang_thai]}>{a.trang_thai === "da_duyet" ? "Đang hiện" : a.trang_thai_ten}</Tag>{a.la_bia && <Tag cls="ok">Bìa</Tag>}<span className="muted" style={{ fontSize: 12 }}>{a.nhom_ten}{a.loai_phong_id ? ` · ${tenLp[a.loai_phong_id] || ""}` : ""}</span></div>
        {a.ly_do_tra_lai && <small style={{ color: "#d99a2b" }}>Trả lại: {a.ly_do_tra_lai}</small>}
        <small className="muted">tải: {a.tai_boi}{a.duyet_boi && a.duyet_boi !== "tu_dong" ? ` · duyệt: ${a.duyet_boi}` : ""}</small>
        {a.chu_thich && <small>{a.chu_thich}</small>}
        {a.mo_ta_thay_the ? <small className="muted">Mô tả thay thế: {a.mo_ta_thay_the}</small> : <small className="muted" style={{ color: "#d99a2b" }}>Chưa có mô tả thay thế</small>}
        {sua && sua.id === a.id && <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <label style={{ fontSize: 12 }}>Nhóm ảnh<select value={sua.nhom} onChange={(e) => setSua({ ...sua, nhom: e.target.value })}>
            {Object.entries(x.nhom_anh).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label style={{ fontSize: 12 }}>Loại phòng<select value={sua.loai_phong_id ?? ""} onChange={(e) => setSua({ ...sua, loai_phong_id: e.target.value })}>
            <option value="">— không —</option>{h.loai_phong.map((p: any) => <option key={p.id} value={p.id}>{p.ten}</option>)}</select></label>
          <label style={{ fontSize: 12 }}>Chú thích (khách thấy)<input value={sua.chu_thich} maxLength={200} onChange={(e) => setSua({ ...sua, chu_thich: e.target.value })} /></label>
          <label style={{ fontSize: 12 }}>Mô tả thay thế (cho người không xem được ảnh)<input value={sua.mo_ta_thay_the} maxLength={200} placeholder="vd: Giường đôi lớn, cửa kính nhìn ra biển" onChange={(e) => setSua({ ...sua, mo_ta_thay_the: e.target.value })} /></label>
          <div style={{ display: "flex", gap: 4 }}><button className="act teal" disabled={busy} onClick={luuSua}>Lưu</button><button className="act grey" onClick={() => setSua(null)}>Thôi</button></div></div>}
        {x.duoc_nhap && <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {!(sua && sua.id === a.id) && <button className="act grey" disabled={busy} onClick={() => setSua({ id: a.id, nhom: a.nhom, loai_phong_id: a.loai_phong_id ?? "",
            chu_thich: a.chu_thich || "", mo_ta_thay_the: a.mo_ta_thay_the || "" })}>Sửa</button>}
          {a.trang_thai === "da_duyet" && !a.la_bia && <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}`, { la_bia: true })}>Đặt bìa</button>}
          {a.trang_thai !== "an" ? <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: true })}>Ẩn</button>
            : <button className="act grey" disabled={busy} onClick={() => goi(`/khach-san-vtd/anh/${a.id}/an`, { bat: false })}>Bỏ ẩn</button>}
          {(a.tai_boi === x.toi || x.duoc_duyet) && <button className="act grey" disabled={busy} onClick={() => { if (window.confirm("Xóa ảnh này khỏi album?")) goi(`/khach-san-vtd/anh/${a.id}/xoa`, {}); }}>Xóa</button>}</div>}
      </div>)}
      {h.album?.nhac && <p className="muted" style={{ gridColumn: "1 / -1", margin: 0, color: h.album.thieu ? "#d99a2b" : undefined }}>
        {h.album.nhac} — khuyến nghị {h.album.chuan}–{h.album.toi_da} ảnh / khách sạn{h.album.thieu ? " (chỉ nhắc, vẫn bật hiện được)" : ""}.</p>}
      {!h.anh.length && <p className="muted">Chưa có ảnh. Ảnh do khách sạn gửi hoặc VTD tự chụp; tải lên là hiện trên cổng.</p>}</div>
  </div>;
}

/** KS-16k · Bảng giá trẻ em theo nhóm tuổi (cách Agoda YCS) — dùng cho khách sạn (mặc định), loại phòng và gói (ghi đè).
 *  Trên tuổi lớn nhất của bảng = người lớn. Ô ăn sáng trống = cần khách sạn xác nhận (không tự hiểu là miễn phí). */
const BANG0 = [{ tu: 0, den: 1, nhom: "so_sinh", cach: "mien_phi", gia: "", an_sang: "" }, { tu: 2, den: 11, nhom: "tre_em", cach: "co_dinh", gia: "", an_sang: "" }];
const soTien = (v: any) => (v === "" || v === null || v === undefined ? "" : tien(Number(String(v).replace(/\D/g, ""))));
const guiBang = (b: any[]) => (b || []).filter((m: any) => m.tu !== "" || m.den !== "").map((m: any) => ({ ...m, tu: Number(m.tu), den: Number(m.den),
  gia: m.cach === "mien_phi" ? 0 : Number(String(m.gia ?? "").replace(/[^\d.]/g, "")) || 0,
  an_sang: m.an_sang === "" || m.an_sang === null || m.an_sang === undefined ? null : Number(String(m.an_sang).replace(/\D/g, "")) }));
function BangTre({ bang, setBang, x, nhap }: { bang: any[]; setBang: (b: any[]) => void; x: any; nhap: boolean }) {
  const sua = (i: number, k: string, v: any) => setBang(bang.map((m, j) => (j === i ? { ...m, [k]: v } : m)));
  const tren = bang.length ? Math.max(...bang.map((m) => Number(m.den) || 0)) + 1 : null;
  return <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Nhóm</th><th>Từ tuổi</th><th>Đến tuổi</th><th>Ở chung, giường có sẵn</th><th>Giá / đêm</th><th>Ăn sáng / đêm (gói có bữa sáng)</th><th></th></tr></thead>
      <tbody>{bang.map((m, i) => <tr key={i}>
        <td><select value={m.nhom || "tre_em"} disabled={!nhap} onChange={(e) => sua(i, "nhom", e.target.value)} aria-label="Nhóm">{Object.entries(x.nhom_tuoi || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></td>
        <td><input type="number" min={0} max={17} style={{ width: 64 }} value={m.tu} disabled={!nhap} onChange={(e) => sua(i, "tu", e.target.value)} aria-label="Từ tuổi" /></td>
        <td><input type="number" min={0} max={17} style={{ width: 64 }} value={m.den} disabled={!nhap} onChange={(e) => sua(i, "den", e.target.value)} aria-label="Đến tuổi" /></td>
        <td><select value={m.cach} disabled={!nhap} onChange={(e) => sua(i, "cach", e.target.value)} aria-label="Cách tính">{Object.entries(x.cach_tinh_tre || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></td>
        <td>{m.cach === "mien_phi" ? "0 đ" : m.cach === "phan_tram"
          ? <><input inputMode="decimal" style={{ width: 70 }} value={m.gia ?? ""} disabled={!nhap} onChange={(e) => sua(i, "gia", e.target.value.replace(/[^\d.]/g, ""))} aria-label="Phần trăm" /> %</>
          : <input inputMode="numeric" style={{ width: 120 }} value={soTien(m.gia)} placeholder="150.000" disabled={!nhap} onChange={(e) => sua(i, "gia", e.target.value.replace(/\D/g, ""))} aria-label="Giá trẻ em" />}</td>
        <td><input inputMode="numeric" style={{ width: 120 }} value={soTien(m.an_sang)} placeholder="trống = cần xác nhận" disabled={!nhap} onChange={(e) => sua(i, "an_sang", e.target.value.replace(/\D/g, ""))} aria-label="Giá ăn sáng" /></td>
        <td>{nhap && <button className="act grey" onClick={() => setBang(bang.filter((_m, j) => j !== i))}>Bỏ</button>}</td></tr>)}</tbody></table></div>
    {nhap && <button className="act grey" style={{ alignSelf: "flex-start" }} onClick={() => setBang([...bang, { tu: tren ?? 0, den: tren ?? 0, nhom: "tre_em", cach: "co_dinh", gia: "", an_sang: "" }])}>+ Thêm nhóm tuổi</button>}
    {tren !== null && <span className="muted">Từ {tren} tuổi: tính như người lớn. Giá trẻ em chỉ tính khi trẻ vượt «số trẻ miễn phí» của phòng; ăn sáng tính cho mọi trẻ khi gói có bữa sáng (ghi 0 nếu miễn phí).</span>}
  </div>;
}

/** KS-16j/16k · Chính sách tuổi + giá trẻ em mặc định của khách sạn — máy dùng để tính phụ thu khi khách đặt. */
function CsTre({ f, setF, x, nhap }: { f: any; setF: (v: any) => void; x: any; nhap: boolean }) {
  const nhan = f.cs_nhan_tre_em || "chua_xac_nhan";
  return <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
    <legend>Chính sách trẻ em (theo cách Agoda)</legend>
    <div className="grid">
      <label>Nhận trẻ em<select value={nhan} disabled={!nhap} onChange={(e) => setF({ ...f, cs_nhan_tre_em: e.target.value,
        cs_moc_tuoi: (e.target.value === "moi_tuoi" || e.target.value === "tu_tuoi") && !(f.cs_moc_tuoi || []).length ? BANG0.map((m) => ({ ...m })) : f.cs_moc_tuoi })}>
        {Object.entries(x.nhan_tre_em || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{k2 === "tu_tuoi" ? "Chỉ nhận khách từ … tuổi" : v}</option>)}</select></label>
      {nhan === "tu_tuoi" && <label>Tuổi tối thiểu của khách<input type="number" min={0} max={18} value={f.cs_tre_tu_tuoi ?? ""} disabled={!nhap} onChange={(e) => setF({ ...f, cs_tre_tu_tuoi: e.target.value })} /></label>}
    </div>
    {(nhan === "moi_tuoi" || nhan === "tu_tuoi") && <>
      <b style={{ fontSize: 13 }}>Giá trẻ em mặc định (áp cho mọi phòng, mọi gói — phòng / gói có thể ghi đè)</b>
      <BangTre bang={f.cs_moc_tuoi || []} setBang={(b) => setF({ ...f, cs_moc_tuoi: b })} x={x} nhap={nhap} />
      <div className="grid">
        <label>Số trẻ ở chung miễn phí mỗi phòng<input inputMode="numeric" value={f.cs_so_tre_mien_phi ?? ""} placeholder="trống = cần xác nhận" disabled={!nhap} onChange={(e) => setF({ ...f, cs_so_tre_mien_phi: e.target.value.replace(/\D/g, "") })} /></label>
        <label>Trẻ miễn phí có tính vào sức chứa phòng<select value={f.cs_tre_mp_tinh_suc_chua ? "1" : "0"} disabled={!nhap} onChange={(e) => setF({ ...f, cs_tre_mp_tinh_suc_chua: e.target.value === "1" })}>
          <option value="0">Không tính</option><option value="1">Có tính</option></select></label>
      </div></>}
    <div className="grid">
      <label>Giá giường phụ<select value={f.cs_giuong_phu_kieu || "co_dinh"} disabled={!nhap} onChange={(e) => setF({ ...f, cs_giuong_phu_kieu: e.target.value })}>
        {Object.entries(x.kieu_gia || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
      <label>{(f.cs_giuong_phu_kieu || "co_dinh") === "phan_tram" ? "Giường phụ (% giá phòng / đêm)" : "Giường phụ / đêm (đã gồm 8% VAT)"}
        <input inputMode="numeric" value={(f.cs_giuong_phu_kieu || "co_dinh") === "phan_tram" ? (f.cs_phi_giuong_phu ?? "") : soTien(f.cs_phi_giuong_phu)}
          placeholder="trống = cần xác nhận" disabled={!nhap} onChange={(e) => setF({ ...f, cs_phi_giuong_phu: e.target.value.replace(/[^\d.]/g, "") })} /></label>
      <label>Nôi / cũi (khách yêu cầu khi nhận phòng)<input value={f.cs_noi ?? ""} placeholder="Miễn phí" disabled={!nhap} onChange={(e) => setF({ ...f, cs_noi: e.target.value })} /></label>
    </div>
    <span className="muted">Còn «Chưa xác nhận» thì cổng ghi «Cần khách sạn xác nhận»; khách có trẻ em gửi yêu cầu, không đặt ngay.
      Khách đặt có trẻ em: trẻ nhỏ nhất ở chung miễn phí trong số trẻ miễn phí; vượt sức chứa cơ bản thì nằm giường phụ (trẻ lớn nhất trước) và trả giá giường phụ thay giá trẻ em; máy tự cộng vào tiền phòng.</span>
  </fieldset>;
}

function Phong({ h, x, toast, goi, busy }: { h: any; x: any; toast: (m: string, l?: boolean) => void; goi: (p: string, j: any) => Promise<any>; busy: boolean }) {
  const [lp, setLp] = useState<any>(null);
  const [g, setG] = useState<any>(null);   // {lid, id?, ten, bua_sang, huy_truoc_ngay, dang_ban, mua:[]}
  const kid = h.khach_san.id;
  const luuLp = async () => { const r = await goi(lp.id ? `/khach-san-vtd/${kid}/loai-phong/${lp.id}` : `/khach-san-vtd/${kid}/loai-phong`,
    { ...lp, dien_tich: Number(lp.dien_tich) || 0, toi_da_nguoi_lon: soHoacNull(lp.toi_da_nguoi_lon), tong_khach_toi_da: soHoacNull(lp.tong_khach_toi_da),   // KS-17
      toi_da_tre_em: soHoacNull(lp.toi_da_tre_em),
      giuong_phu_toi_da: soHoacNull(lp.giuong_phu_toi_da), so_phong: Number(lp.so_phong) || 0, thu_tu: Number(lp.thu_tu) || 0,
      // KS-16k
      suc_chua: soHoacNull(lp.suc_chua), khach_them_toi_da: soHoacNull(lp.khach_them_toi_da), so_tre_mien_phi: soHoacNull(lp.so_tre_mien_phi),
      phi_giuong_phu: soHoacNull(String(lp.phi_giuong_phu ?? "").replace(/[^\d.]/g, "")), gia_tre_rieng: lp.gia_tre_rieng ? guiBang(lp.gia_tre_rieng) : null }); if (r) setLp(null); };
  const [tnThem, setTnThem] = useState("");
  const bat = (k2: string, v: string) => setLp({ ...lp, [k2]: (lp[k2] || []).includes(v) ? lp[k2].filter((y: string) => y !== v) : [...(lp[k2] || []), v] });
  const chip = (on: boolean) => ({ padding: "3px 10px", borderRadius: 99, fontSize: 12, border: "1px solid var(--line, #2a3b4d)", cursor: "pointer",
    background: on ? "var(--teal, #0f7b74)" : "transparent", color: on ? "#fff" : "inherit" });
  const luuGoi = async () => {
    const mua = g.mua.filter((m: any) => m.tu_ngay || m.den_ngay || m.gia_thuong).map((m: any) => ({ ...m, gia_thuong: Number(String(m.gia_thuong).replace(/\D/g, "")) || 0,
      gia_cuoi_tuan: m.gia_cuoi_tuan ? Number(String(m.gia_cuoi_tuan).replace(/\D/g, "")) : null, gia_niem_yet: m.gia_niem_yet ? Number(String(m.gia_niem_yet).replace(/\D/g, "")) : null }));
    const r = await goi(g.id ? `/khach-san-vtd/loai-phong/${g.lid}/goi/${g.id}` : `/khach-san-vtd/loai-phong/${g.lid}/goi`,
      { ten: g.ten, bua_sang: g.bua_sang, huy_truoc_ngay: g.huy_truoc_ngay === "" || g.huy_truoc_ngay === null ? null : Number(g.huy_truoc_ngay), dang_ban: g.dang_ban, mua,
        tre_em_che_do: g.tre_em_che_do || "", gia_tre: g.tre_em_che_do === "rieng" ? guiBang(g.gia_tre || []) : null,   // KS-16k
        huy_gio_chot: g.huy_gio_chot || "", huy_mui_gio: g.huy_mui_gio || "Asia/Ho_Chi_Minh", cho_tra_sau: g.cho_tra_sau !== false });   // KS-17
    if (r) setG(null);
  };
  const nhap = x.duoc_nhap;
  return <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
    <p className="muted" style={{ margin: 0 }}>Giá bán / phòng / đêm, ĐÃ GỒM 8% VAT (máy không cộng thêm thuế phí). Đêm thứ Sáu, thứ Bảy dùng «giá cuối tuần» nếu có.
      Đêm nào không nằm trong mùa giá nào thì gói đó không bán cho kỳ ở ấy. Sửa gói đã duyệt → về Nháp, thôi hiện trên cổng tới khi duyệt lại.</p>
    {nhap && !lp && <button className="act teal" style={{ alignSelf: "flex-start" }} onClick={() => setLp({ ...LP0 })}>+ Thêm loại phòng</button>}
    {lp && <div className="panel" style={{ margin: 0, display: "flex", flexDirection: "column", gap: 10 }}><b>{lp.id ? `Sửa ${lp.ten}` : "Loại phòng mới"}</b>
      <div className="grid">{([["ten", "Tên loại phòng", "Deluxe hướng biển"], ["dien_tich", "Diện tích (m²)", "32"], ["giuong", "Giường", "1 giường đôi lớn"], ["thu_tu", "Thứ tự hiện", "0"]] as const).map(([k2, t2, ph]) =>
        <label key={k2}>{t2}<input value={lp[k2] ?? ""} placeholder={ph} onChange={(e) => setLp({ ...lp, [k2]: e.target.value })} /></label>)}</div>
      <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}><legend>Đặc điểm</legend>
        <label>Đặc điểm ngắn (hiện ở thẻ phòng) <span className="muted" style={{ color: (lp.mo_ta || "").length > 300 ? "var(--vtos-danger)" : undefined }}>{(lp.mo_ta || "").length} / 300 ký tự</span>
          <input value={lp.mo_ta ?? ""} placeholder="Ban công hướng biển · bồn tắm" onChange={(e) => setLp({ ...lp, mo_ta: e.target.value })} /></label>
        {(lp.mo_ta || "").length > 300 && <span style={{ color: "var(--vtos-danger)", fontSize: 12 }}>Quá 300 ký tự — rút gọn, phần dài đưa xuống Mô tả chi tiết. Máy không tự cắt.</span>}
        <label>Mô tả chi tiết <span className="muted">{(lp.mo_ta_dai || "").length} / 3.000 ký tự · khách bấm «Xem thêm» mới hiện</span>
          <textarea rows={4} value={lp.mo_ta_dai ?? ""} onChange={(e) => setLp({ ...lp, mo_ta_dai: e.target.value })} /></label>
        <div>Tiện nghi <span className="muted">(chọn sẵn + thêm tên khác)</span>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
            {Array.from(new Set([...(x.tien_nghi_phong || []), ...(lp.tien_nghi || [])])).map((v: any) =>
              <button key={v} type="button" style={chip((lp.tien_nghi || []).includes(v))} onClick={() => bat("tien_nghi", v)}>{(lp.tien_nghi || []).includes(v) ? "✓ " : ""}{v}</button>)}
            <input value={tnThem} placeholder="+ tiện nghi khác" style={{ width: 150 }} onChange={(e) => setTnThem(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && tnThem.trim()) { setLp({ ...lp, tien_nghi: [...(lp.tien_nghi || []), tnThem.trim()] }); setTnThem(""); } }} />
            {tnThem.trim() && <button type="button" className="act grey" onClick={() => { setLp({ ...lp, tien_nghi: [...(lp.tien_nghi || []), tnThem.trim()] }); setTnThem(""); }}>Thêm</button>}</div></div>
      </fieldset>
      <div className="grid">
        <label>Tối đa người lớn<input inputMode="numeric" value={lp.toi_da_nguoi_lon ?? ""} placeholder="trống = chưa xác nhận" onChange={(e) => setLp({ ...lp, toi_da_nguoi_lon: e.target.value.replace(/\D/g, "") })} />
          <span className="muted">Chưa xác nhận thì phòng chưa bán, chưa duyệt giá được.</span></label>
        <label>Tổng khách tối đa (người lớn + trẻ em)<input inputMode="numeric" value={lp.tong_khach_toi_da ?? ""} placeholder="trống = chưa xác nhận" onChange={(e) => setLp({ ...lp, tong_khach_toi_da: e.target.value.replace(/\D/g, "") })} /></label>
        <label>Tối đa trẻ em ở chung<select value={lp.toi_da_tre_em === null || lp.toi_da_tre_em === undefined ? "" : String(lp.toi_da_tre_em)} onChange={(e) => setLp({ ...lp, toi_da_tre_em: e.target.value })}>
          <option value="">Chưa xác nhận</option><option value="0">0 — không nhận trẻ em ở chung</option>{[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}</select>
          <span className="muted">Để «Chưa xác nhận» thì lưu là chưa biết, không thành 0.</span></label>
        <label>Giường phụ tối đa<select value={lp.giuong_phu_toi_da === null || lp.giuong_phu_toi_da === undefined ? "" : String(lp.giuong_phu_toi_da)} onChange={(e) => setLp({ ...lp, giuong_phu_toi_da: e.target.value })}>
          <option value="">Chưa xác nhận</option><option value="0">0 — không kê thêm</option>{[1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
        <label>Sức chứa cơ bản<input inputMode="numeric" value={lp.suc_chua ?? ""} placeholder="trống = bằng tối đa người lớn" onChange={(e) => setLp({ ...lp, suc_chua: e.target.value.replace(/\D/g, "") })} /></label>
        <label>Khách thêm tối đa (nằm giường phụ)<input inputMode="numeric" value={lp.khach_them_toi_da ?? ""} placeholder="trống = cần xác nhận" onChange={(e) => setLp({ ...lp, khach_them_toi_da: e.target.value.replace(/\D/g, "") })} /></label>
        <label>Số trẻ ở chung miễn phí của phòng<input inputMode="numeric" value={lp.so_tre_mien_phi ?? ""} placeholder="trống = theo khách sạn" onChange={(e) => setLp({ ...lp, so_tre_mien_phi: e.target.value.replace(/\D/g, "") })} /></label>
        <label>Giường phụ<select value={lp.giuong_phu_xac_nhan ? "1" : "0"} onChange={(e) => setLp({ ...lp, giuong_phu_xac_nhan: e.target.value === "1" })}>
          <option value="0">Có sẵn — bán ngay</option><option value="1">Theo xác nhận của khách sạn — vẫn bán, Điều hành hỏi KS</option></select></label>
        <label>Giá giường phụ của phòng<select value={lp.giuong_phu_kieu || ""} onChange={(e) => setLp({ ...lp, giuong_phu_kieu: e.target.value })}>
          <option value="">Theo khách sạn</option>{Object.entries(x.kieu_gia || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
        {lp.giuong_phu_kieu && <label>{lp.giuong_phu_kieu === "phan_tram" ? "% giá phòng / đêm" : "Giá giường phụ / đêm"}<input inputMode="numeric"
          value={lp.giuong_phu_kieu === "phan_tram" ? (lp.phi_giuong_phu ?? "") : soTien(lp.phi_giuong_phu)} onChange={(e) => setLp({ ...lp, phi_giuong_phu: e.target.value.replace(/[^\d.]/g, "") })} /></label>}
        <label>Nôi / cũi em bé<select value={lp.noi_cui === null || lp.noi_cui === undefined ? "" : lp.noi_cui ? "1" : "0"} onChange={(e) => setLp({ ...lp, noi_cui: e.target.value === "" ? null : e.target.value === "1" })}>
          <option value="">Chưa xác nhận</option><option value="1">Có</option><option value="0">Không</option></select></label>
        <label>Số phòng VTD được bán mỗi đêm<input inputMode="numeric" value={lp.so_phong ?? ""} placeholder="0" onChange={(e) => setLp({ ...lp, so_phong: e.target.value.replace(/\D/g, "") })} />
          <span className="muted">Hồ sơ nháp được để 0. Lưu 0 thì mở lại vẫn là 0.</span></label>
      </div>
      <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}><legend>Giá trẻ em của phòng</legend>
        <label>Đổi giá trẻ em cho phòng này<select value={lp.gia_tre_rieng ? "1" : "0"} onChange={(e) => setLp({ ...lp, gia_tre_rieng: e.target.value === "1"
          ? ((h.khach_san.cs_moc_tuoi || []).length ? h.khach_san.cs_moc_tuoi.map((m: any) => ({ ...m, an_sang: m.an_sang ?? "" })) : BANG0.map((m) => ({ ...m }))) : null })}>
          <option value="0">Không — theo khách sạn</option><option value="1">Có — sao chép từ mặc định rồi sửa</option></select></label>
        {lp.gia_tre_rieng && <BangTre bang={lp.gia_tre_rieng} setBang={(b) => setLp({ ...lp, gia_tre_rieng: b })} x={x} nhap />}
      </fieldset>
      <fieldset style={{ border: "1px solid var(--line, #2a3b4d)", borderRadius: 8, padding: 10, display: "flex", flexDirection: "column", gap: 8 }}><legend>Nguồn & đối chiếu (nội bộ)</legend>
        <div className="grid">
          <label>Nguồn<select value={lp.nguon ?? ""} onChange={(e) => setLp({ ...lp, nguon: e.target.value })}><option value="">— chọn —</option>
            {Object.entries(x.nguon_lp || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
          <label>Kỳ / ngày đối chiếu<input value={lp.ky_doi_chieu ?? ""} placeholder="10–11/12/2026 · đọc ngày 31/10/2026" onChange={(e) => setLp({ ...lp, ky_doi_chieu: e.target.value })} /></label>
          <label>Mã hạng phòng (KS / OTA)<input value={lp.ma_hang ?? ""} placeholder="ghi đúng mã nguồn, không đoán từ tên" onChange={(e) => setLp({ ...lp, ma_hang: e.target.value })} /></label>
          <label>Tên tương đương<input value={lp.ten_tuong_duong ?? ""} placeholder="Superior (có thể cùng hạng)" onChange={(e) => setLp({ ...lp, ten_tuong_duong: e.target.value })} /></label>
          <label>Trạng thái đối chiếu<select value={lp.trang_thai_dc ?? ""} onChange={(e) => setLp({ ...lp, trang_thai_dc: e.target.value })}><option value="">—</option>
            {Object.entries(x.trang_thai_dc || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select>
            <span className="muted">Điều hành tự ghi, không chặn bật bán.</span></label>
        </div>
        <div>Còn cần xác nhận<div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
          {Object.entries(x.can_xac_nhan || {}).map(([k2, v]: any) => <button key={k2} type="button" style={chip((lp.can_xac_nhan || []).includes(k2))} onClick={() => bat("can_xac_nhan", k2)}>{(lp.can_xac_nhan || []).includes(k2) ? "✓ " : ""}{v}</button>)}</div></div>
        <label>Ghi chú đối chiếu<input value={lp.ghi_chu_doi_chieu ?? ""} maxLength={500} onChange={(e) => setLp({ ...lp, ghi_chu_doi_chieu: e.target.value })} /></label>
      </fieldset>
      <label style={{ display: "flex", gap: 6, alignItems: "center", flexDirection: "row" }}><input type="checkbox" checked={!!lp.dang_ban} onChange={(e) => setLp({ ...lp, dang_ban: e.target.checked })} />Đang bán</label>
      {lp.dang_ban && !(Number(lp.so_phong) >= 1) && <span style={{ color: "#d99a2b", fontSize: 13 }}>Đang bán cần số phòng VTD được bán mỗi đêm ≥ 1 theo hợp đồng.</span>}
      <div><button className="act teal" disabled={busy} onClick={luuLp}>Lưu loại phòng</button> <button className="act grey" onClick={() => setLp(null)}>Thôi</button></div></div>}
    {h.loai_phong.map((p: any) => <div key={p.id} className="panel" style={{ margin: 0 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}><b style={{ fontSize: 16 }}>{p.ten}</b>
        <span className="muted">{[p.dien_tich ? `${p.dien_tich} m²` : "", p.giuong, p.toi_da_nguoi_lon == null ? "người lớn chưa xác nhận" : `tối đa ${p.toi_da_nguoi_lon} NL`,
          p.tong_khach_toi_da ? `tổng ${p.tong_khach_toi_da} khách` : "",
          p.toi_da_tre_em === null ? "trẻ em chưa xác nhận" : p.toi_da_tre_em ? `${p.toi_da_tre_em} TE` : "không nhận TE ở chung",
          p.giuong_phu_toi_da ? `${p.giuong_phu_toi_da} giường phụ` : "", `${p.so_phong} phòng / đêm`].filter(Boolean).join(" · ")}</span>
        {!p.dang_ban && <Tag cls="warn">Ngừng bán</Tag>}
        {(p.trang_thai_dc || p.nguon || (p.can_xac_nhan || []).length > 0) && <Tag cls={p.trang_thai_dc === "da_xac_nhan" ? "ok" : "warn"}>{[x.trang_thai_dc?.[p.trang_thai_dc], x.nguon_lp?.[p.nguon], p.ky_doi_chieu,
          (p.can_xac_nhan || []).length ? `còn ${(p.can_xac_nhan || []).length} mục cần xác nhận` : ""].filter(Boolean).join(" · ")}</Tag>}<span style={{ flex: 1 }} />
        {nhap && <><button className="act grey" onClick={() => setLp({ ...p })}>Sửa phòng</button>
          <button className="act grey" onClick={() => setG({ lid: p.id, ten: "Chỉ phòng", bua_sang: false, huy_truoc_ngay: 2, dang_ban: true, mua: [{ ...MUA0 }] })}>+ Gói giá</button></>}</div>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Gói</th><th>Mùa giá (giá / đêm, đã gồm 8% VAT)</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{p.goi.map((q: any) => <tr key={q.id} className="ksv-goi">
          <td><b>{q.ten}</b><div className="muted">{q.bua_sang ? "Có bữa sáng" : "Chỉ phòng"} · {q.huy_truoc_ngay === null ? "Không hoàn tiền" : `Miễn phí hủy trước ${q.huy_truoc_ngay} ngày${q.huy_gio_chot ? `, trước ${q.huy_gio_chot} (${x.mui_gio_huy?.[q.huy_mui_gio] || q.huy_mui_gio})` : ""}`}{q.cho_tra_sau === false ? " · không trả sau" : ""}{q.dang_ban ? "" : " · ngừng bán"}</div></td>
          <td>{q.mua.map((m: any) => <div key={m.id}>{m.tu_ngay.split("-").reverse().join("/")} – {m.den_ngay.split("-").reverse().join("/")}: <b>{tien(m.gia_thuong)}</b>{m.gia_cuoi_tuan ? ` · T6-T7 ${tien(m.gia_cuoi_tuan)}` : ""}{m.gia_niem_yet ? <span className="muted"> · niêm yết {tien(m.gia_niem_yet)}</span> : null}</div>)}</td>
          <td><Tag cls={TT[q.trang_thai]}>{q.trang_thai_ten}</Tag><div className="muted" style={{ fontSize: 12 }}>nhập: {q.sua_boi}{q.duyet_boi ? ` · duyệt: ${q.duyet_boi}` : ""}</div>
            {q.ly_do_tra_lai && <small style={{ color: "#d99a2b" }}>Trả lại: {q.ly_do_tra_lai}</small>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{nhap && <button className="act grey" onClick={() => setG({ lid: p.id, ...q, huy_truoc_ngay: q.huy_truoc_ngay ?? "", mua: q.mua.map((m: any) => ({ ...m, gia_cuoi_tuan: m.gia_cuoi_tuan ?? "", gia_niem_yet: m.gia_niem_yet ?? "" })) })}>Sửa</button>}
            {nhap && ["nhap", "tra_lai"].includes(q.trang_thai) && <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/goi/${q.id}/gui-duyet`, {})}>Gửi duyệt</button>}</td></tr>)}
          {!p.goi.length && <tr><td colSpan={4} className="muted">Chưa có gói giá — khách thấy «Giá đang cập nhật» và gửi yêu cầu.</td></tr>}</tbody></table></div>
      {g && g.lid === p.id && <div className="panel" style={{ margin: "8px 0 0" }}><b>{g.id ? `Sửa gói ${g.ten}` : "Gói giá mới"}</b>
        <div className="grid">
          <label>Tên gói<input value={g.ten} onChange={(e) => setG({ ...g, ten: e.target.value })} placeholder="Chỉ phòng / Có bữa sáng" /></label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={g.bua_sang} onChange={(e) => setG({ ...g, bua_sang: e.target.checked })} />Có bữa sáng</label>
          <label>Hủy phòng<select value={g.huy_truoc_ngay === "" || g.huy_truoc_ngay === null ? "khong" : String(g.huy_truoc_ngay)} onChange={(e) => setG({ ...g, huy_truoc_ngay: e.target.value === "khong" ? "" : Number(e.target.value) })}>
            <option value="khong">Không hoàn tiền</option>{[0, 1, 2, 3, 5, 7, 14, 30].map((n) => <option key={n} value={n}>Miễn phí hủy trước {n} ngày</option>)}</select></label>
          {/* KS-17: giờ chốt + múi giờ của hạn hủy, và gói có cho «đặt giữ, trả sau» không */}
          <label>Giờ chốt hủy (trong ngày hạn hủy)<input value={g.huy_gio_chot || ""} placeholder="trống = hết ngày · vd 18:00" disabled={g.huy_truoc_ngay === "" || g.huy_truoc_ngay === null}
            onChange={(e) => setG({ ...g, huy_gio_chot: e.target.value.replace(/[^\d:]/g, "").slice(0, 5) })} /></label>
          <label>Múi giờ của giờ chốt<select value={g.huy_mui_gio || "Asia/Ho_Chi_Minh"} onChange={(e) => setG({ ...g, huy_mui_gio: e.target.value })}>
            {Object.entries(x.mui_gio_huy || { "Asia/Ho_Chi_Minh": "Giờ Việt Nam (GMT+7)" }).map(([k2, v]: any) => <option key={k2} value={k2}>{v}</option>)}</select></label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={g.cho_tra_sau !== false} onChange={(e) => setG({ ...g, cho_tra_sau: e.target.checked })} />Cho khách đặt giữ, trả sau</label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={g.dang_ban} onChange={(e) => setG({ ...g, dang_ban: e.target.checked })} />Đang bán</label>
          <label>Giá trẻ em của gói<select value={g.tre_em_che_do || ""} onChange={(e) => {
            const p = h.loai_phong.find((y: any) => y.id === g.lid); const goc = p?.gia_tre_rieng || h.khach_san.cs_moc_tuoi || [];
            setG({ ...g, tre_em_che_do: e.target.value, gia_tre: e.target.value === "rieng" && !(g.gia_tre || []).length ? (goc.length ? goc.map((m: any) => ({ ...m, an_sang: m.an_sang ?? "" })) : BANG0.map((m) => ({ ...m }))) : g.gia_tre }); }}>
            {Object.entries(x.che_do_tre_goi || {}).map(([k2, v]: any) => <option key={k2} value={k2}>{k2 === "rieng" ? "Riêng cho gói — sao chép từ mặc định rồi sửa" : v}</option>)}</select></label></div>
        {g.tre_em_che_do === "rieng" && <BangTre bang={g.gia_tre || []} setBang={(b) => setG({ ...g, gia_tre: b })} x={x} nhap />}
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Từ ngày</th><th>Đến ngày (gồm)</th><th>Giá ngày thường</th><th>Giá T6–T7</th><th>Giá niêm yết KS</th><th>Ghi chú</th><th></th></tr></thead>
          <tbody>{g.mua.map((m: any, i: number) => { const s = (k2: string, v: any) => setG({ ...g, mua: g.mua.map((y: any, j: number) => j === i ? { ...y, [k2]: v } : y) });
            return <tr key={i}><td><input type="date" value={m.tu_ngay} onChange={(e) => s("tu_ngay", e.target.value)} aria-label="Từ ngày" /></td>
              <td><input type="date" value={m.den_ngay} onChange={(e) => s("den_ngay", e.target.value)} aria-label="Đến ngày" /></td>
              <td><input inputMode="numeric" value={m.gia_thuong} onChange={(e) => s("gia_thuong", e.target.value)} placeholder="1.790.000" aria-label="Giá ngày thường" /></td>
              <td><input inputMode="numeric" value={m.gia_cuoi_tuan} onChange={(e) => s("gia_cuoi_tuan", e.target.value)} placeholder="để trống = như ngày thường" aria-label="Giá cuối tuần" /></td>
              <td><input inputMode="numeric" value={m.gia_niem_yet} onChange={(e) => s("gia_niem_yet", e.target.value)} placeholder="không bắt buộc" aria-label="Giá niêm yết" /></td>
              <td><input value={m.ghi_chu} onChange={(e) => s("ghi_chu", e.target.value)} aria-label="Ghi chú" /></td>
              <td><button className="act grey" onClick={() => setG({ ...g, mua: g.mua.filter((_: any, j: number) => j !== i) })}>Bỏ</button></td></tr>; })}</tbody></table></div>
        <button className="act grey" onClick={() => setG({ ...g, mua: [...g.mua, { ...MUA0 }] })}>+ Thêm mùa</button>{" "}
        <button className="act teal" disabled={busy} onClick={luuGoi}>Lưu gói</button> <button className="act grey" onClick={() => setG(null)}>Thôi</button>
        <p className="muted" style={{ fontSize: 12 }}>Chỉ GIÁ BÁN cho khách. Lưu xong gói ở trạng thái «Nháp» — bấm «Gửi duyệt» để TP Điều hành duyệt; người nhập không tự duyệt.</p></div>}
    </div>)}
    {!h.loai_phong.length && <p className="muted">Chưa có loại phòng.</p>}
  </div>;
}

function ChoDuyet({ toast, onDoi }: { toast: (m: string, l?: boolean) => void; onDoi: () => void }) {
  const [x, setX] = useState<any>(null);
  const [chon, setChon] = useState<number[]>([]);
  const [lyDo, setLyDo] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/khach-san-vtd/cho-duyet").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  if (!x) return <p className="muted">Đang tải…</p>;
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setChon([]); load(); onDoi(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  return <section className="panel" id="ksv-cho-duyet">
    <h2 style={{ marginTop: 0 }}>Chờ duyệt</h2>
    {!x.duoc_duyet && <p className="muted">TP Điều hành duyệt. Bạn chỉ xem.</p>}
    <label>Lý do trả lại (bắt buộc khi trả lại)<input value={lyDo} onChange={(e) => setLyDo(e.target.value)} placeholder="vd: ảnh mờ, giá cuối tuần thấp hơn ngày thường" /></label>
    <h3>Ảnh ({x.anh.length})</h3>
    {x.duoc_duyet && x.anh.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
      <button className="act grey" onClick={() => setChon(x.anh.filter((a: any) => a.tai_boi !== x.toi || x.toan_quyen).map((a: any) => a.id))}>Chọn tất cả ({x.anh.length})</button>
      <button className="act teal" disabled={busy || !chon.length} onClick={() => goi("/khach-san-vtd/anh/duyet", { ids: chon, dong_y: true })}>Duyệt {chon.length} ảnh</button>
      <button className="act grey" disabled={busy || !chon.length || lyDo.trim().length < 5} onClick={() => goi("/khach-san-vtd/anh/duyet", { ids: chon, dong_y: false, ly_do: lyDo })}>Trả lại</button></div>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(170px,1fr))", gap: 10 }}>{x.anh.slice(0, 120).map((a: any) =>
      <label key={a.id} className="panel" style={{ margin: 0, padding: 8, display: "flex", flexDirection: "column", gap: 4, cursor: "pointer" }}>
        <AnhNoiBo src={a.nho} alt={a.chu_thich || a.nhom_ten} style={{ width: "100%", aspectRatio: "4 / 3", borderRadius: 6 }} />
        <span style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" disabled={!x.duoc_duyet || (a.tai_boi === x.toi && !x.toan_quyen)} checked={chon.includes(a.id)} onChange={(e) => setChon(e.target.checked ? [...chon, a.id] : chon.filter((y) => y !== a.id))} />
          <b style={{ fontSize: 13 }}>{a.khach_san}</b></span>
        <small className="muted">{a.nhom_ten} · tải: {a.tai_boi}{a.tai_boi === x.toi && !x.toan_quyen ? " (bạn tải — không tự duyệt)" : ""}</small></label>)}</div>
    {x.anh.length > 120 && <p className="muted">Hiện 120 / {x.anh.length} ảnh — duyệt xong lô này để xem tiếp.</p>}
    <h3>Gói giá ({x.goi.length})</h3>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Khách sạn · phòng · gói</th><th>Mùa giá</th><th>Nhập</th><th></th></tr></thead>
      <tbody>{x.goi.map((g: any) => <tr key={g.id}>
        <td><b>{g.khach_san}</b><div>{g.loai_phong} · {g.ten}</div><div className="muted">{g.bua_sang ? "Có bữa sáng" : "Chỉ phòng"} · {g.huy_truoc_ngay === null ? "Không hoàn tiền" : `Miễn phí hủy trước ${g.huy_truoc_ngay} ngày`}</div></td>
        <td>{g.mua.map((m: any) => <div key={m.id}>{m.tu_ngay.split("-").reverse().join("/")} – {m.den_ngay.split("-").reverse().join("/")}: <b>{tien(m.gia_thuong)}</b>{m.gia_cuoi_tuan ? ` · T6-T7 ${tien(m.gia_cuoi_tuan)}` : ""}{m.gia_niem_yet ? ` · niêm yết ${tien(m.gia_niem_yet)}` : ""}</div>)}</td>
        <td>{g.sua_boi}</td>
        <td style={{ whiteSpace: "nowrap" }}>{x.duoc_duyet && (g.sua_boi !== x.toi || x.toan_quyen) ? <>
          <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/goi/${g.id}/duyet`, { dong_y: true })}>Duyệt</button>{" "}
          <button className="act grey" disabled={busy || lyDo.trim().length < 5} onClick={() => goi(`/khach-san-vtd/goi/${g.id}/duyet`, { dong_y: false, ly_do: lyDo })}>Trả lại</button></>
          : <span className="muted">{g.sua_boi === x.toi ? "Bạn nhập — không tự duyệt" : "Chờ TP Điều hành"}</span>}</td></tr>)}
        {!x.goi.length && <tr><td colSpan={4} className="muted">Không có gói chờ duyệt.</td></tr>}</tbody></table></div>
  </section>;
}

/* ── KS-14 · Phòng trống, Đơn đặt phòng, Tiền & hoàn ─────────────────────────────────────────────── */
const hom = () => { const d = new Date(); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); };
const THU2 = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];
const dm = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().slice(0, 2).join("/") : "");
const gio = (s?: string | null) => (s ? `${s.slice(11, 16)} ${dm(s)}` : "");
const MAU_DON: Record<string, string> = { cho_tra: "warn", het_han: "", da_tra: "warn", da_xac_nhan: "ok", da_huy: "bad" };

function PhongTrong({ kid, toast }: { kid: number; toast: (m: string, l?: boolean) => void }) {
  const [tu, setTu] = useState(hom());
  const [b, setB] = useState<any>(null);
  const [sua, setSua] = useState<any>(null);   // {lid, ten, ngay:[...], so_ban, dong}
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>(`/khach-san-vtd/don/phong-trong/${kid}?tu=${tu}&so_ngay=14`).then(setB).catch((e) => toast(errMsg(e), true)); }, [kid, tu, toast]);
  useEffect(() => { load(); }, [load]);
  const luu = async (dong: boolean, veMacDinh = false) => {
    setBusy(true);
    try { const r = await api<any>(`/khach-san-vtd/don/phong-trong/${sua.lid}`, { method: "POST",
      json: { ngay: sua.ngay, so_ban: veMacDinh || sua.so_ban === "" ? null : Number(sua.so_ban), dong } }); toast(r.message); setSua(null); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!b) return <p className="muted">Đang tải…</p>;
  const chonO = (p: any, o: any) => {
    if (!b.duoc_sua) return;
    if (sua && sua.lid === p.id) { const ngay = sua.ngay.includes(o.ngay) ? sua.ngay.filter((x: string) => x !== o.ngay) : [...sua.ngay, o.ngay]; setSua(ngay.length ? { ...sua, ngay } : null); }
    else setSua({ lid: p.id, ten: p.ten, ngay: [o.ngay], so_ban: o.da_sua ? String(o.ban) : "", dong: o.dong });
  };
  return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
    <p className="muted" style={{ margin: 0 }}>Số phòng VTD được bán mỗi đêm. Mặc định = «số phòng / đêm» ở hồ sơ loại phòng; bấm ô để sửa hoặc đóng bán (chọn nhiều ô cùng loại phòng rồi lưu một lần).
      Ô ghi <b>còn / tổng</b>; «đã nhận» gồm đơn đang giữ 15 phút chờ trả tiền, đã trả và đã xác nhận.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <button className="act grey" onClick={() => { const d = new Date(tu + "T00:00:00"); d.setDate(d.getDate() - 14); const s2 = new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10); setTu(s2 < hom() ? hom() : s2); }}>← 14 ngày</button>
      <input type="date" value={tu} min={hom()} onChange={(e) => e.target.value && setTu(e.target.value)} aria-label="Từ ngày" style={{ maxWidth: 170 }} />
      <button className="act grey" onClick={() => { const d = new Date(tu + "T00:00:00"); d.setDate(d.getDate() + 14); setTu(new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)); }}>14 ngày →</button></div>
    <div style={{ overflowX: "auto" }}><table className="ksv-lich"><thead><tr><th style={{ textAlign: "left" }}>Loại phòng</th>
      {b.ngay.map((n: string) => { const d = new Date(n + "T00:00:00"); return <th key={n} style={{ textAlign: "center", whiteSpace: "nowrap" }}>{THU2[d.getDay()]}<br />{dm(n)}</th>; })}</tr></thead>
      <tbody>{b.phong.map((p: any) => <tr key={p.id}><td><b>{p.ten}</b><div className="muted">{p.so_phong} phòng / đêm{p.dang_ban ? "" : " · ngừng bán"}</div></td>
        {p.o.map((o: any) => { const on = sua && sua.lid === p.id && sua.ngay.includes(o.ngay);
          return <td key={o.ngay} style={{ padding: 3 }}><button type="button" disabled={!b.duoc_sua} onClick={() => chonO(p, o)} aria-pressed={!!on}
            aria-label={`${p.ten} đêm ${dm(o.ngay)}: ${o.dong ? "đóng bán" : `còn ${o.con} trên ${o.ban}`}`}
            className={`ksv-o ${o.dong ? "dong" : o.con === 0 ? "het" : ""} ${on ? "chon" : ""}`}>
            {o.dong ? "Đóng" : <>{o.con}<span className="muted">/{o.ban}</span></>}{o.da_sua && !o.dong ? <i>•</i> : null}</button></td>; })}</tr>)}
        {!b.phong.length && <tr><td colSpan={15} className="muted">Chưa có loại phòng.</td></tr>}</tbody></table></div>
    {sua && <div className="panel" style={{ margin: 0 }}><b>{sua.ten} · {sua.ngay.length} đêm: {[...sua.ngay].sort().map(dm).join(", ")}</b>
      <div className="grid"><label>Số phòng bán mỗi đêm (để trống = theo hồ sơ)<input inputMode="numeric" value={sua.so_ban} onChange={(e) => setSua({ ...sua, so_ban: e.target.value.replace(/\D/g, "") })} /></label></div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button className="act teal" disabled={busy} onClick={() => luu(false)}>Lưu số phòng</button>
        <button className="act grey" disabled={busy} onClick={() => luu(true)}>Đóng bán các đêm này</button>
        <button className="act grey" disabled={busy} onClick={() => luu(false, true)}>Về theo hồ sơ</button>
        <button className="act grey" onClick={() => setSua(null)}>Thôi</button></div></div>}
    <style>{`.ksv-lich td,.ksv-lich th{padding:6px}.ksv-o{min-width:46px;min-height:44px;border-radius:6px;border:1px solid transparent;background:#1c3d5e;color:inherit;font:inherit;cursor:pointer;position:relative}
      .ksv-o.het{background:#5a4614;color:#ffe08a}.ksv-o.dong{background:var(--vtos-danger-bg);color:var(--vtos-danger);font-weight:700}.ksv-o.chon{border-color:#4cc38a;box-shadow:0 0 0 2px #4cc38a}
      .ksv-o i{position:absolute;top:2px;right:4px;font-style:normal;color:#7fc4ff}.ksv-o:disabled{cursor:default}`}</style>
  </div>;
}

function DongDon({ d }: { d: any }) {
  return <><td><b>{d.ma}</b><div className="muted">{d.ho_ten} · {d.lien_he}</div></td>
    <td>{d.khach_san?.ten}<div className="muted">{d.dong.map((x: any) => `${x.so} × ${x.loai_phong} · ${x.goi}${x.phu_thu ? ` · phụ thu trẻ em / giường phụ ${tien(x.phu_thu)} đ` : ""}`).join("; ")}</div>
      {d.dong.some((x: any) => x.giuong_phu_cho_xac_nhan) && <Tag cls="warn">Giường phụ chờ KS xác nhận</Tag>}</td>
    <td style={{ whiteSpace: "nowrap" }}>{dm(d.vao)} – {dm(d.ra)}<div className="muted">{d.dem} đêm · {d.nguoi_lon} NL{d.tre_em ? ` + ${d.tre_em} TE` : ""}</div>
      {d.gio_den && <div className="muted">đến {d.gio_den}</div>}</td>
    <td style={{ whiteSpace: "nowrap" }}>₫ {tien(d.tong)}<div className="muted">đã trả {tien(d.da_tra)}{d.thanh_toan?.length ? ` · ${d.thanh_toan.map((t: any) => t.kenh === "qr" ? "QR" : "thẻ").join(", ")}` : ""}</div>
      {d.giam_voucher > 0 && <div className="muted" style={{ color: "#ffcf7a" }}>voucher {d.voucher?.ma} −{tien(d.giam_voucher)}{d.voucher?.trang_thai === "da_hoan" ? " · đã trả điểm" : " · VTD chịu"}</div>}</td></>;
}

function DonDat({ toast }: { toast: (m: string, l?: boolean) => void }) {
  const [loc, setLoc] = useState("cho_chot");
  const [x, setX] = useState<any>(null);
  const [o, setO] = useState<Record<number, { ma: string; ly: string }>>({});
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>(`/khach-san-vtd/don?loc=${loc}`).then(setX).catch((e) => toast(errMsg(e), true)); }, [loc, toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { await api<any>(path, { method: "POST", json }); toast("Đã lưu"); load(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const v = (id: number) => o[id] || { ma: "", ly: "" };
  return <section className="panel">
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
      {([["cho_chot", `Chờ chốt với khách sạn (${x.dem.cho_chot || 0})`], ["da_xac_nhan", `Đã xác nhận (${x.dem.da_xac_nhan || 0})`], ["cho_tra", `Chờ thanh toán (${x.dem.cho_tra || 0})`],
        ["da_huy", `Đã hủy (${x.dem.da_huy || 0})`], ["", "Tất cả"]] as const).map(([k, t]) =>
        <button key={k} className={`act ${loc === k ? "teal" : "grey"}`} onClick={() => setLoc(k)}>{t}</button>)}</div>
    <p className="muted" style={{ margin: "0 0 8px" }}>Khách trả đủ là máy xác nhận và gửi phiếu ngay (phòng đã khóa lúc đặt). Điều hành báo khách sạn và ghi mã xác nhận của khách sạn trong 2 giờ làm việc.
      Đơn có giường phụ hoặc trẻ em cần hỏi khách sạn thì chờ Điều hành chốt rồi khách mới nhận phiếu. Khách sạn không giữ được phòng → bấm «KS hết phòng»: đơn hủy, hoàn 100% qua Sales → Kế toán.</p>
    <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn · phòng</th><th>Ngày ở</th><th>Tiền</th><th>Trạng thái</th><th>Việc</th></tr></thead>
      <tbody>{x.don.map((d: any) => <tr key={d.id}><DongDon d={d} />
        <td><Tag cls={MAU_DON[d.trang_thai]}>{d.trang_thai_ten}</Tag>
          {d.trang_thai === "da_tra" && <div style={{ color: d.qua_han_chot ? "var(--vtos-danger)" : undefined, fontWeight: d.qua_han_chot ? 700 : 400 }}>{d.qua_han_chot ? "Quá hạn chốt" : "Hạn chốt"} {gio(d.han_chot)}</div>}
          {d.trang_thai === "da_xac_nhan" && <div className="muted">mã KS {d.ma_xac_nhan_ks} · {d.xac_nhan_boi}</div>}
          {d.trang_thai === "da_huy" && <div className="muted">{d.ly_do_huy}{d.so_hoan ? ` · hoàn ${tien(d.so_hoan)} (${d.hoan_tt_ten || "xong"})` : ""}</div>}
          {d.yeu_cau && <div className="muted">Yêu cầu: {d.yeu_cau}</div>}</td>
        <td style={{ minWidth: 230 }}>{x.vai.dh && ["da_tra"].includes(d.trang_thai) && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label>Mã xác nhận của khách sạn<input value={v(d.id).ma} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ma: e.target.value } })} /></label>
          <button className="act teal" disabled={busy || v(d.id).ma.trim().length < 3} onClick={() => goi(`/khach-san-vtd/don/${d.id}/xac-nhan`, { ma_ks: v(d.id).ma })}>Đã xác nhận → gửi phiếu</button></div>}
          {x.vai.dh && ["da_tra", "da_xac_nhan"].includes(d.trang_thai) && <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
            <label>Lý do (khi khách sạn hết phòng)<input value={v(d.id).ly} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ly: e.target.value } })} placeholder="KS báo hết Deluxe ngày 6/11" /></label>
            <button className="act grey" style={{ color: "var(--vtos-danger)" }} disabled={busy || v(d.id).ly.trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/het-phong`, { ly_do: v(d.id).ly })}>KS hết phòng → hoàn 100%</button></div>}
          {x.vai.mien_phat && d.trang_thai === "da_huy" && d.giu_lai > 0 && d.hoa_hong === null && <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label>Lý do miễn phạt<input value={v(d.id).ly} onChange={(e) => setO({ ...o, [d.id]: { ...v(d.id), ly: e.target.value } })} /></label>
            <button className="act grey" disabled={busy || v(d.id).ly.trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/mien-phat`, { ly_do: v(d.id).ly })}>Miễn phạt · hoàn đủ {tien(d.da_tra)}</button></div>}
        </td></tr>)}
        {!x.don.length && <tr><td colSpan={6} className="muted">Không có đơn.</td></tr>}</tbody></table></div>
  </section>;
}

function TienHoan({ toast }: { toast: (m: string, l?: boolean) => void }) {
  const [x, setX] = useState<any>(null);
  const [o, setO] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api<any>("/khach-san-vtd/don/tien").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r?.message || "Đã lưu"); load(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const nhap = (k: string, ph = "", so = false) => <input value={o[k] || ""} placeholder={ph} inputMode={so ? "numeric" : undefined}
    onChange={(e) => setO({ ...o, [k]: so ? e.target.value.replace(/\D/g, "") : e.target.value })} style={{ minWidth: 150 }} />;
  const kt = x.vai.kt, sales = x.vai.sales;
  return <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
    <p className="muted" style={{ margin: 0 }}>Tiền phòng khách sạn VTD là tiền THU HỘ khách sạn (như đặt bàn DT-3): tiền vào Nợ 1121 / Có 3388, phí thẻ 6428, hoàn Nợ 3388 / Có 1121.
      Doanh thu Vietourist là hoa hồng Kế toán gõ theo hợp đồng sau khi khách trả phòng; phần còn lại trả khách sạn qua đề nghị chi NCC. Không ô nào gõ số tiền khách trả / số hoàn.</p>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>1 · Tiền vào chờ ghi sổ ({x.tien_cho.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Đơn</th><th>Cách trả</th><th>Số tiền</th><th>Trạng thái</th><th>Việc</th></tr></thead>
        <tbody>{x.tien_cho.map((t: any) => <tr key={t.id}><td><b>{t.ma}</b></td><td>{t.kenh_ten}{t.so_gd_cong ? ` · GD ${t.so_gd_cong}` : ""}</td><td>₫ {tien(t.so_tien)}</td><td>{t.trang_thai_ten}<div className="muted">{gio(t.luc)}</div></td>
          <td>{kt && (t.trang_thai === "tu_khop" ? <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/tt/${t.id}/xac-nhan`, {})}>Xác nhận · ghi sổ</button>
            : <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}><label>Phí thẻ theo sao kê{nhap(`phi${t.id}`, "0", true)}</label>
              <button className="act teal" disabled={busy || o[`phi${t.id}`] === undefined || o[`phi${t.id}`] === ""} onClick={() => goi(`/khach-san-vtd/don/tt/${t.id}/doi-soat`, { phi: Number(o[`phi${t.id}`]) })}>Đối soát</button></span>)}</td></tr>)}
          {!x.tien_cho.length && <tr><td colSpan={5} className="muted">Không có khoản chờ.</td></tr>}</tbody></table></div>
      {kt && <><h3>Giao dịch có mã đặt phòng chưa khớp ({x.giao_dich_cho.length})</h3>
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Lúc</th><th>Nội dung</th><th>Số tiền</th><th>Đơn</th><th>Việc</th></tr></thead>
          <tbody>{x.giao_dich_cho.map((g: any) => <tr key={g.txn_id}><td>{gio(g.luc)}</td><td>{g.noi_dung}<div className="muted">{g.ghi_chu}</div></td><td>₫ {tien(g.so_tien)}</td>
            <td><b>{g.ma}</b><div className="muted">{g.trang_thai_ten}{g.con_phai_tra != null ? ` · còn phải trả ${tien(g.con_phai_tra)}` : ""}</div></td>
            <td>{g.don_id && <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/${g.don_id}/gan-qr`, { txn_id: g.txn_id })}>Gán vào đơn · ghi sổ</button>}</td></tr>)}
            {!x.giao_dich_cho.length && <tr><td colSpan={5} className="muted">Không có giao dịch chờ.</td></tr>}</tbody></table></div></>}
      {x.thieu.length > 0 && <><h3>Đơn có tiền nhưng chưa đủ / đã hết giờ giữ ({x.thieu.length})</h3>
        <table><tbody>{x.thieu.map((d: any) => <tr key={d.id}><DongDon d={d} /><td>{kt && <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`cv${d.id}`, "Lý do")}
          <button className="act grey" disabled={busy || (o[`cv${d.id}`] || "").trim().length < 5} onClick={() => goi(`/khach-san-vtd/don/${d.id}/chuyen-hoan`, { ly_do: o[`cv${d.id}`] })}>Hủy · hoàn đủ {tien(d.da_tra)}</button></span>}</td></tr>)}</tbody></table></>}
    </section>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>2 · Hoàn tiền — Sales xác nhận → Kế toán chuyển ({x.hoan.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn</th><th>Ngày ở</th><th>Tiền</th><th>Lý do · số hoàn</th><th>Việc</th></tr></thead>
        <tbody>{x.hoan.map((d: any) => <tr key={d.id}><DongDon d={d} /><td>{d.ly_do_huy}<div><b>Hoàn ₫ {tien(d.so_hoan - d.da_hoan_tien)}</b> · <Tag cls="warn">{d.hoan_tt_ten}</Tag></div>
          {d.hoan_ghi_chu && <div className="muted" style={{ whiteSpace: "pre-line" }}>{d.hoan_ghi_chu}</div>}</td>
          <td>{d.hoan_tt === "cho_sales" && (sales ? <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/${d.id}/sales-hoan`, {})}>Xác nhận số hoàn</button> : <span className="muted">chờ Sales</span>)}
            {d.hoan_tt === "cho_chi" && (kt ? <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`ct${d.id}`, "Số UNC / mã hoàn OnePay")}
              <button className="act teal" disabled={busy || (o[`ct${d.id}`] || "").trim().length < 3} onClick={() => goi(`/khach-san-vtd/don/${d.id}/da-hoan`, { ghi_chu: o[`ct${d.id}`] })}>Đã hoàn · ghi sổ</button></span> : <span className="muted">chờ Kế toán</span>)}</td></tr>)}
          {!x.hoan.length && <tr><td colSpan={6} className="muted">Không có khoản hoàn chờ.</td></tr>}</tbody></table></div></section>
    <section className="panel" style={{ margin: 0 }}><h3 style={{ marginTop: 0 }}>3 · Sau khi khách trả phòng — chốt hoa hồng ({x.cho_chot.length})</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Mã · khách</th><th>Khách sạn</th><th>Ngày ở</th><th>Tiền</th><th>Giữ lại</th><th>Hoa hồng theo hợp đồng</th></tr></thead>
        <tbody>{x.cho_chot.map((d: any) => { const giu = d.da_tra - d.so_hoan + (d.khuyen_mai || 0); return <tr key={d.id}><DongDon d={d} /><td>₫ {tien(giu)}{d.khuyen_mai > 0 ? <div className="muted">gồm voucher VTD chịu {tien(d.khuyen_mai)} — chốt ghi Nợ 641 / Có 3388</div> : null}{d.trang_thai === "da_huy" ? <div className="muted">đơn hủy, giữ theo gói</div> : null}</td>
          <td>{kt ? <span style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>{nhap(`hh${d.id}`, "số tiền", true)}
            <button className="act teal" disabled={busy || !o[`hh${d.id}`]} onClick={() => goi(`/khach-san-vtd/don/${d.id}/chot`, { hoa_hong: Number(o[`hh${d.id}`]) })}>Chốt</button>
            {o[`hh${d.id}`] ? <span className="muted">→ trả khách sạn ₫ {tien(giu - Number(o[`hh${d.id}`]))}</span> : null}</span> : <span className="muted">Kế toán chốt</span>}</td></tr>; })}
          {!x.cho_chot.length && <tr><td colSpan={6} className="muted">Không có đơn chờ chốt.</td></tr>}</tbody></table></div>
      <h3>Phải trả từng khách sạn (đã chốt)</h3>
      <div style={{ overflowX: "auto" }}><table><thead><tr><th>Khách sạn</th><th>Số đơn</th><th>Tiền giữ lại</th><th>Voucher VTD chịu</th><th>Hoa hồng VTD</th><th>Phải trả khách sạn</th><th>Đề nghị chi (mỗi đơn một)</th></tr></thead>
        <tbody>{x.phai_tra_ks.map((k: any) => <tr key={k.ma}><td><b>{k.khach_san}</b><div className="muted">{k.ma}</div></td><td>{k.so_don}</td><td>₫ {tien(k.giu_lai)}</td><td>₫ {tien(k.khuyen_mai || 0)}</td><td>₫ {tien(k.hoa_hong)}</td><td><b>₫ {tien(k.phai_tra)}</b></td>
          <td>{(k.de_nghi_chi || []).map((p: any) => <div key={p.id} style={{ fontSize: 12 }}><b>{p.code}</b> · {p.don} · ₫ {tien(p.so_tien)} · {TT_DN[p.status] || p.status}</div>)}{!(k.de_nghi_chi || []).length && <span className="muted">—</span>}</td></tr>)}
          {!x.phai_tra_ks.length && <tr><td colSpan={7} className="muted">Chưa có đơn đã chốt.</td></tr>}</tbody></table></div>
      {(x.cho_ghi_dt || []).length > 0 && <><h3>Chờ ghi doanh thu hoa hồng ({x.cho_ghi_dt.length})</h3>
        <div style={{ overflowX: "auto" }}><table><thead><tr><th>Đơn</th><th>Khách sạn</th><th>Đề nghị chi</th><th>Hoa hồng</th><th></th></tr></thead>
          <tbody>{x.cho_ghi_dt.map((d: any) => <tr key={d.id}><td><b>{d.ma}</b>{d.chot_luc && <div className="muted">chốt {d.chot_luc.slice(8, 10)}/{d.chot_luc.slice(5, 7)}</div>}</td><td>{d.khach_san}</td>
            <td>{d.de_nghi_chi || <span className="muted">— (chi tay)</span>}</td><td>₫ {tien(d.hoa_hong)}</td>
            <td>{kt ? <button className="act teal" disabled={busy} onClick={() => goi(`/khach-san-vtd/don/${d.id}/ghi-dt-hoa-hong`, {})}>Ghi doanh thu hoa hồng</button> : <span className="muted">Kế toán ghi</span>}</td></tr>)}</tbody></table></div>
        <p className="muted" style={{ fontSize: 12 }}>Bình thường máy tự ghi Nợ 3388 / Có 511 khi Kế toán bấm «Đã chi» đề nghị trả khách sạn (trả 0 thì ghi lúc chốt). Bảng này chỉ còn đơn cũ hoặc lần ghi bị kỳ khóa chặn. Hoa hồng chưa gồm VAT — VAT Kế toán xử lý riêng.</p></>}
      <p className="muted" style={{ fontSize: 12 }}>Kế toán chốt → máy lập đề nghị chi; robot kế toán kiểm (thiếu NCC / MST / số tài khoản thì dừng) → TGĐ / Chủ tịch duyệt → Kế toán chuyển khoản, tải UNC, bấm Đã chi.</p></section>
  </div>;
}
export default function Page() { return <Shell><Trang /></Shell>; }
