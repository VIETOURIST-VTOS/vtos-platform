"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Đội xe v3.3 · MÀN GỌN cho từng trang con của /xe (Chủ tịch duyệt bản xem trước 10/11/2026).
 *
 *  Thay cho khung nhúng nguyên màn cũ: mỗi trang con hiện vài con số và danh sách cần nhìn, đúng như demo
 *  v3.3; nút «Mở…» mới mở màn chi tiết đang chạy (khung nhúng). Mọi số đọc từ CỬA ĐANG CÓ của máy chủ —
 *  không có phép tính thứ hai ở đây, và ô nào máy chủ chưa có số thì ghi «Chưa có số», không ghi 0. */

type Mo = (toi: string) => void;
const vnd = (n?: number | null) => (n === null || n === undefined ? "—" : Math.round(n).toLocaleString("vi-VN") + " đ");
const tr = (n?: number | null) => (n === null || n === undefined ? "—"
  : (n / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) + " tr");

function useDoc<T>(duong: string) {
  const [d, setD] = useState<T | null>(null);
  const [loi, setLoi] = useState("");
  useEffect(() => { api<T>(duong).then(setD).catch((e) => setLoi(String(e?.message || e))); }, [duong]);
  return { d, loi };
}
const O3 = ({ ds }: { ds: [string, React.ReactNode, string?][] }) => (
  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, margin: "10px 0" }}>
    {ds.map(([n, v, p]) => <div key={n} style={{ border: "1px solid #dce3ec", borderRadius: 10, padding: "10px 12px" }}>
      <span className="muted">{n}</span>
      <strong style={{ display: "block", fontSize: "1.45em", fontVariantNumeric: "tabular-nums" }}>{v}</strong>
      {p && <span className="muted" style={{ fontSize: 12.5 }}>{p}</span>}</div>)}
  </div>);
const Dong = ({ t, p, tag, cls, nut, onNut }: { t: React.ReactNode; p?: React.ReactNode; tag?: string; cls?: string; nut?: string; onNut?: () => void }) => (
  <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", padding: "9px 0", borderBottom: "1px solid #e6eaf0" }}>
    <span style={{ flex: "1 1 260px", minWidth: 0 }}><strong>{t}</strong>{p && <><br /><span className="muted">{p}</span></>}</span>
    {tag && <span className={`tag ${cls || ""}`}>{tag}</span>}
    {nut && <button type="button" onClick={onNut}>{nut}</button>}
  </div>);
const Chip = ({ on, t, onClick }: { on: boolean; t: string; onClick: () => void }) => (
  <button type="button" aria-pressed={on} onClick={onClick}
    style={{ borderRadius: 999, padding: "4px 11px", cursor: "pointer", border: "1px solid " + (on ? "#1d5bbf" : "#dce3ec"),
             background: on ? "#eef3fb" : "#fff", fontWeight: on ? 700 : 400 }}>{t}</button>);
const Loi = ({ loi }: { loi: string }) => loi ? <p className="muted">Không đọc được số: {loi}</p> : <p className="muted">Đang đọc…</p>;

/* ───────── Điều xe › Lịch & lệnh ───────── */
export function LichLenhGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any[]>("/fleet/lenh-dieu-xe");
  const hom = new Date().toISOString().slice(0, 10);
  if (!d) return <Loi loi={loi} />;
  const homNay = d.filter((x) => x.status !== "huy" && x.date_from <= hom && hom <= x.date_to);
  const chuaXacNhan = d.filter((x) => x.status === "cho_xac_nhan");
  return <>
    <div className="row" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Lịch & lệnh điều xe</h2>
      <button type="button" className="act teal" style={{ margin: 0 }} onClick={() => mo("/lenh-dieu-xe/lap-lenh")}>Lập lệnh xe</button></div>
    <O3 ds={[["Lệnh VTOS đang chạy hôm nay", homNay.length], ["Tổng lệnh trên VTOS", d.length],
             ["Lệnh chưa xác nhận", chuaXacNhan.length]]} />
    {homNay.map((x) => <Dong key={x.id} t={`${x.xe} · ${x.tour || "—"}`} p={`${x.date_from} → ${x.date_to} · ${x.tai_xe || "chưa có tài xế"}`} />)}
    {!homNay.length && <p className="muted">Hôm nay chưa có lệnh VTOS. Nhật trình có chuyến chưa gắn lệnh thì không dùng lịch trống để kết luận xe rảnh.</p>}
    <p><button type="button" onClick={() => mo("/lenh-dieu-xe")}>Mở lịch & lệnh đầy đủ</button></p>
  </>;
}

/* ───────── Xe & tài xế › Hồ sơ xe ───────── */
export function HoSoXeGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any[]>("/fleet/xe?kem_kiem_tra=true");
  const [loc, setLoc] = useState<"all" | "thieu" | "chan">("all");
  if (!d) return <Loi loi={loi} />;
  const muc = (x: any) => x.san_sang?.muc;
  const chan = d.filter((x) => muc(x) === "BLOCK"), thieu = d.filter((x) => muc(x) === "UNKNOWN");
  const kt = d.filter((x) => x.active).length, ban = d.filter((x) => !x.active).length;
  const ds = loc === "chan" ? chan : loc === "thieu" ? thieu : d;
  const nhan: Record<string, [string, string]> = { BLOCK: ["Đang bị chặn", "red"], UNKNOWN: ["Chưa đủ dữ liệu", "warn"],
    APPROVAL_REQUIRED: ["Cần duyệt ngoại lệ", "warn"], REVIEW: ["Cần xem lại", "warn"], OK: ["Sẵn sàng", "ok"] };
  return <>
    <h2 style={{ margin: 0 }}>Hồ sơ xe</h2>
    <p className="muted" style={{ margin: "2px 0 8px" }}>{d.length} xe danh mục · {kt} đang khai thác · {ban} ngừng / đã bán</p>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 6 }}>
      <Chip on={loc === "all"} t={`Tất cả ${d.length}`} onClick={() => setLoc("all")} />
      <Chip on={loc === "thieu"} t={`Thiếu dữ liệu · ${thieu.length}`} onClick={() => setLoc("thieu")} />
      <Chip on={loc === "chan"} t={`Đang bị chặn · ${chan.length}`} onClick={() => setLoc("chan")} /></div>
    {ds.map((x) => { const [t, c] = nhan[muc(x)] || ["—", ""];
      return <Dong key={x.id} t={x.plate} p={[x.code || "Chưa có mã", ...(x.san_sang?.ly_do || []).slice(0, 1), x.active ? "" : x.lifecycle_ten].filter(Boolean).join(" · ")}
        tag={t} cls={c} nut="Mở hồ sơ" onNut={() => mo(`/doi-xe?xe=${x.id}`)} />; })}
  </>;
}

/* ───────── Báo cáo & chi phí › Báo cáo từng xe ───────── */
export function BaoCaoXeGon({ mo, onNhap }: { mo: Mo; onNhap: () => void }) {
  const { d, loi } = useDoc<any[]>("/fleet/chuyen");
  const [loc, setLoc] = useState("all");
  if (!d) return <Loi loi={loi} />;
  const NHOM: [string, string, (x: any) => boolean][] = [
    ["all", "Tất cả", () => true],
    ["nhap", "Đang nhập", (x) => (x.qt_trang_thai || "nhap") === "nhap"],
    ["cho", "Chờ duyệt / chờ chi", (x) => ["cho_tgd", "cho_dieu_hanh", "cho_ke_toan"].includes(x.qt_trang_thai)],
    ["tra", "Trả bổ sung", (x) => x.qt_trang_thai === "tra_lai"],
    ["xong", "Đã chốt", (x) => x.qt_trang_thai === "da_duyet" || (x.quyet_toan && (x.qt_trang_thai || "nhap") === "nhap")],
  ];
  const f = NHOM.find((n) => n[0] === loc)![2];
  const ds = d.filter(f).slice(0, 60);
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Báo cáo từng xe</h2>
      <button type="button" className="act teal" style={{ margin: 0 }} onClick={onNhap}>Nhập báo cáo từng xe</button></div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {NHOM.map(([k, t, g]) => <Chip key={k} on={loc === k} t={`${t} · ${d.filter(g).length}`} onClick={() => setLoc(k)} />)}</div>
    {ds.map((x) => <Dong key={x.id} t={`${x.ma_phieu || "#" + x.id} · ${x.xe}`}
      p={[x.ten_tour, `${x.ngay_di} → ${x.ngay_ve}`, x.km_chay != null ? `${x.km_chay.toLocaleString("vi-VN")} km` : "",
          x.qt_trang_thai === "tra_lai" && x.qt_tra_lai_ly_do ? `trả lại: ${x.qt_tra_lai_ly_do}` : ""].filter(Boolean).join(" · ")}
      tag={x.qt_ten_trang_thai || (x.quyet_toan ? "Đã quyết toán" : "Chưa quyết toán")}
      cls={x.qt_trang_thai === "tra_lai" ? "red" : x.qt_trang_thai === "da_duyet" || x.quyet_toan ? "ok" : "warn"}
      nut="Mở" onNut={() => mo("/doi-xe?tab=chuyen")} />)}
    {!ds.length && <p className="muted">Không có phiếu ở nhóm này.</p>}
  </>;
}

/* ───────── Báo cáo & chi phí › Quyết toán ───────── */
export function QuyetToanGon({ ky, mo }: { ky: string; mo: Mo }) {
  const { d, loi } = useDoc<any>(`/fleet/lai-lo?ky=${ky}`);
  if (!d) return <Loi loi={loi} />;
  const t = d.tong || {};
  return <>
    <h2 style={{ margin: 0 }}>Quyết toán & đối soát · kỳ {ky.split("-").reverse().join("/")}</h2>
    <O3 ds={[["Chuyến chưa chốt", t.so_chuyen_chua_quyet_toan ?? "—", `${tr(t.doanh_thu_chua_quyet_toan)} doanh thu đang treo`],
             ["Doanh thu chuyến đã quyết toán", tr(t.doanh_thu)],
             ["Chuyến đã quyết toán", t.so_chuyen ?? (d.xe || []).reduce((a: number, x: any) => a + (x.so_chuyen || 0), 0)]]} />
    <p className="muted">Doanh thu chưa quyết toán không cộng vào lợi nhuận kỳ. Chuyến vào lợi nhuận khi Chủ tịch duyệt tờ quyết toán.</p>
    <p style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button type="button" onClick={() => mo("/doi-xe?tab=quyettoan")}>Mở bảng quyết toán chủ xe</button>
      <button type="button" onClick={() => mo("/doi-xe?tab=giaodich")}>Mở đối soát nguồn ngoài</button></p>
  </>;
}

/* ───────── Báo cáo & chi phí › Công nợ ───────── */
export function CongNoGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/fleet/cong-no");
  if (!d) return <Loi loi={loi} />;
  return <>
    <h2 style={{ margin: 0 }}>Công nợ theo đối tượng</h2>
    <p className="muted" style={{ margin: "2px 0 0" }}>Giữ nguyên từng sổ · không cộng thành một tổng chung</p>
    <O3 ds={[["Công ty phải trả chủ xe", vnd(d.voi_chu_xe?.cong_ty_phai_tra)],
             ["Chủ xe phải trả công ty", vnd(d.voi_chu_xe?.chu_xe_phai_tra_cong_ty)],
             ["Còn phải thu người mua xe", vnd(d.ban_xe?.con_phai_thu)]]} />
    <p className="muted">Khoản vay và tài khoản ngân hàng chỉ hiện ở màn chi tiết với người có quyền tài chính.</p>
    <p><button type="button" onClick={() => mo("/doi-xe?tab=congno")}>Mở công nợ chi tiết</button></p>
  </>;
}

/* ───────── Bảo dưỡng & sự cố › Bảo dưỡng ───────── */
export function BaoDuongGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/fleet/bao-duong/theo-xe");
  if (!d) return <Loi loi={loi} />;
  const xe: any[] = d.xe || [];
  const thieu = xe.filter((x) => x.muc === "UNKNOWN"), qua = xe.filter((x) => x.muc === "BLOCK" || x.muc === "APPROVAL_REQUIRED");
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Bảo dưỡng</h2>
      <button type="button" className="act teal" style={{ margin: 0 }} onClick={() => mo("/doi-xe?tab=bao-duong")}>Ghi phiếu bảo dưỡng</button></div>
    <p className="muted" style={{ margin: "2px 0 0" }}>{xe.length} xe đang khai thác · không tính xe đã bán</p>
    <O3 ds={[["Chưa đủ lịch sử bảo dưỡng", `${thieu.length} xe`, "cần phiếu gần nhất và km đã xác nhận"],
             ["Quá mốc / cần duyệt", qua.length], ["Đạt", xe.filter((x) => x.muc === "OK").length]]} />
    {qua.map((x) => <Dong key={x.vehicle_id} t={x.plate} p={x.viec || x.ghi_chu_moc} tag={x.muc_ten} cls="red" />)}
  </>;
}

/* ───────── Bảo dưỡng & sự cố › Báo hỏng ───────── */
export function BaoHongGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/fleet/bao-hong");
  if (!d) return <Loi loi={loi} />;
  const mo_: any[] = (d.rows || []).filter((r: any) => ["moi", "da_tiep_nhan"].includes(r.trang_thai));
  return <>
    <h2 style={{ margin: 0 }}>Báo hỏng → sửa chữa</h2>
    <O3 ds={[["Đang mở", d.dem?.dang_mo ?? mo_.length], ["Phải dừng xe", d.dem?.phai_dung_xe ?? 0, "chặn điều xe tới khi nghiệm thu"]]} />
    {mo_.map((r) => <Dong key={r.id} t={`${r.plate} · ${r.hien_tuong}`} p={[String(r.bao_luc || "").slice(0, 10), r.trang_thai_ten, r.nguoi_bao].filter(Boolean).join(" · ")}
      tag={r.muc_do_ten} cls={r.muc_do === "phai_dung_xe" ? "red" : "warn"} />)}
    {!mo_.length && <p className="muted">Hiện chưa có báo hỏng đang mở.</p>}
    <p><button type="button" onClick={() => mo("/doi-xe?tab=bao-hong")}>Mở sổ báo hỏng</button></p>
  </>;
}

/* ───────── Bảo dưỡng & sự cố › Dầu & định mức ───────── */
export function DauGon({ mo }: { mo: Mo }) {
  const g = useDoc<any>("/fleet/gia-dau"), m = useDoc<any>("/fleet/dinh-muc-dau");
  if (!g.d || !m.d) return <Loi loi={g.loi || m.loi} />;
  const moi = (g.d.rows || [])[0];
  const nhom: any[] = m.d.rows || [];
  const dem = m.d.so_xe_theo_cho || {};
  return <>
    <h2 style={{ margin: 0 }}>Giá dầu & định mức</h2>
    <O3 ds={[["Giá dầu gần nhất", moi ? vnd(moi.gia_lit) + "/lít" : "Chưa có số", moi ? `${moi.ngay} · ${moi.nguon || "chưa ghi nguồn"}` : "chưa khai ngày nào"],
             ...nhom.map((n) => [`Nhóm ${n.seats} chỗ · ${dem[n.seats] ?? "?"} xe`, n.l_100km != null ? `${n.l_100km} L/100km` : "Chưa khai",
               n.l_100km == null ? "thiếu định mức thì chưa kết luận vượt" : ""] as [string, React.ReactNode, string])]} />
    <p><button type="button" onClick={() => mo("/doi-xe/gia-dau")}>Mở giá dầu & định mức</button></p>
  </>;
}
