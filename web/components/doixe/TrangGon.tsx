"use client";
import NutExcel from "@/components/doixe/NutExcel";
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
    {ds.map(([n, v, p]) => <div key={n} style={{ border: "1px solid #d6dfeb", borderRadius: 12, padding: "10px 12px", boxShadow: "0 4px 14px #1b3a6214", background: "#fff" }}>
      <span className="muted">{n}</span>
      <strong style={{ display: "block", fontSize: "1.45em", fontVariantNumeric: "tabular-nums", color: "var(--xe-nhan, #2c5fa2)" }}>{v}</strong>
      {p && <span className="muted" style={{ fontSize: 12.5 }}>{p}</span>}</div>)}
  </div>);
const Dong = ({ t, p, tag, cls, nut, onNut, chinh, do: laDo }: { t: React.ReactNode; p?: React.ReactNode; tag?: string; cls?: string; nut?: string; onNut?: () => void; chinh?: boolean; do?: boolean }) => (
  <div className={"xe-it" + (laDo ? " xe-do" : "")} style={laDo ? { margin: "4px 0", borderRadius: 8, padding: "9px 12px" } : undefined}>
    <span style={{ flex: "1 1 260px", minWidth: 0 }}><strong>{t}</strong>{p && <><br /><span className="muted">{p}</span></>}</span>
    {tag && <span className={`tag ${cls || ""}`}>{tag}</span>}
    {nut && <button type="button" className={chinh ? "xe-nut-chinh" : undefined} onClick={onNut}>{nut}</button>}
  </div>);
const Chip = ({ on, t, onClick }: { on: boolean; t: string; onClick: () => void }) => (
  <button type="button" aria-pressed={on} onClick={onClick}
    style={{ borderRadius: 999, padding: "4px 11px", cursor: "pointer", border: "1px solid " + (on ? "var(--xe-nhan, #2c5fa2)" : "#dce3ec"),
             background: on ? "var(--xe-nhat, #edf3fc)" : "#fff", color: on ? "var(--xe-nhan, #2c5fa2)" : undefined, fontWeight: on ? 700 : 400 }}>{t}</button>);
const Loi = ({ loi }: { loi: string }) => loi ? <p className="muted">Không đọc được số: {loi}</p> : <p className="muted">Đang đọc…</p>;

/* ───────── Điều xe › Lịch & lệnh ───────── */
export function LichLenhGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any[]>("/fleet/lenh-dieu-xe");
  const hom = new Date().toISOString().slice(0, 10);
  if (!d) return <Loi loi={loi} />;
  const homNay = d.filter((x) => x.status !== "huy" && x.date_from <= hom && hom <= x.date_to);
  const chuaXacNhan = d.filter((x) => x.status === "cho_xac_nhan");
  return <>
    {/* VH-33: bỏ nút «Lập lệnh xe» — trùng trang con «Lập lệnh điều xe» ngay trên thanh (mỗi nút một chỗ). */}
    <h2 style={{ margin: 0 }}>Lịch & lệnh điều xe</h2>
    <O3 ds={[["Lệnh VTOS đang chạy hôm nay", homNay.length], ["Tổng lệnh trên VTOS", d.length],
             ["Lệnh chưa xác nhận", chuaXacNhan.length]]} />
    {homNay.map((x) => <Dong key={x.id} t={`${x.xe} · ${x.tour || "—"}`} p={`${x.date_from} → ${x.date_to} · ${x.tai_xe || "chưa có tài xế"}`} />)}
    {!homNay.length && <p className="muted">Hôm nay chưa có lệnh VTOS.</p>}
    {/* R5-26 (Chủ tịch duyệt 14/11/2026): nút navy sáng «Mở lịch và lập lệnh». */}
    <p><button type="button" className="act" style={{ margin: 0, background: "var(--vtos-sky)", borderColor: "var(--vtos-sky)", color: "var(--vtos-text-on-navy, #fff)" }}
      onClick={() => mo("/lenh-dieu-xe")}>Mở lịch và lập lệnh →</button></p>
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
        tag={t} cls={c} do={c === "red"} nut="Mở hồ sơ" onNut={() => mo(`/doi-xe?xe=${x.id}`)} />; })}
  </>;
}

/* ───────── Báo cáo & chi phí › Báo cáo từng xe ───────── */
export function BaoCaoXeGon({ mo, onNhap, ky: kyChon }: { mo: Mo; onNhap: () => void; ky: string }) {
  const { d, loi } = useDoc<any[]>("/fleet/chuyen");
  const ky = useDoc<any>("/fleet/quyet-toan-chuyen/cho-toi-ky");
  const [loc, setLoc] = useState("all");
  if (!d) return <Loi loi={loi} />;
  // VH-4 «mỗi nút một chỗ»: tờ đã nằm trong ô «Chờ tôi ký» không hiện lại ở danh sách bên dưới.
  const daKy = new Set<number>((ky.d?.rows || []).map((x: any) => x.id));
  const NHOM: [string, string, (x: any) => boolean][] = [
    ["all", "Tất cả", () => true],
    ["nhap", "Đang nhập", (x) => (x.qt_trang_thai || "nhap") === "nhap"],
    ["cho", "Chờ duyệt / chờ chi", (x) => ["cho_tgd", "cho_dieu_hanh", "cho_ke_toan"].includes(x.qt_trang_thai)],
    ["tra", "Trả bổ sung", (x) => x.qt_trang_thai === "tra_lai"],
    ["xong", "Đã chốt", (x) => x.qt_trang_thai === "da_duyet" || (x.quyet_toan && (x.qt_trang_thai || "nhap") === "nhap")],
  ];
  const f = NHOM.find((n) => n[0] === loc)![2];
  const ds = d.filter(f).filter((x) => !daKy.has(x.id)).slice(0, 60);
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Báo cáo từng xe</h2>
      <span style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {/* VH-13: một nút Excel — mọi chuyến khởi hành trong tháng đang chọn ở đầu /xe. */}
        <NutExcel duong={`/fleet/chuyen.xlsx?ky=${kyChon}`} ten={`BAO_CAO_TUNG_XE_${kyChon.replace("-", "")}.xlsx`} />
        <button type="button" className="act teal" style={{ margin: 0 }} onClick={onNhap}>Nhập báo cáo từng xe</button></span></div>
    <ChoToiKy mo={mo} d={ky.d} />
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {NHOM.map(([k, t, g]) => <Chip key={k} on={loc === k} t={`${t} · ${d.filter(g).length}`} onClick={() => setLoc(k)} />)}</div>
    {ds.map((x) => <Dong key={x.id} t={`${x.ma_phieu || "#" + x.id} · ${x.xe}`}
      p={[x.ten_tour, `${x.ngay_di} → ${x.ngay_ve}`, x.km_chay != null ? `${x.km_chay.toLocaleString("vi-VN")} km` : "",
          x.qt_trang_thai === "tra_lai" && x.qt_tra_lai_ly_do ? `trả lại: ${x.qt_tra_lai_ly_do}` : ""].filter(Boolean).join(" · ")}
      tag={x.qt_ten_trang_thai || (x.quyet_toan ? "Đã quyết toán" : "Chưa quyết toán")}
      cls={x.qt_trang_thai === "tra_lai" ? "red" : x.qt_trang_thai === "da_duyet" || x.quyet_toan ? "ok" : "warn"}
      do={x.qt_trang_thai === "tra_lai"}
      nut="Mở" onNut={() => mo(`/doi-xe?tab=chuyen&chuyen=${x.id}`)} />)}
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
    <p className="muted">Doanh thu chưa quyết toán không vào lợi nhuận kỳ.</p>
    <p style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe?tab=quyettoan")}>Mở bảng quyết toán chủ xe</button>
      <button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe?tab=giaodich")}>Mở đối soát nguồn ngoài</button></p>
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
    <p><button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe?tab=congno")}>Mở công nợ chi tiết</button></p>
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
      tag={r.muc_do_ten} cls={r.muc_do === "phai_dung_xe" ? "red" : "warn"} do={r.muc_do === "phai_dung_xe"} />)}
    {!mo_.length && <p className="muted">Hiện chưa có báo hỏng đang mở.</p>}
    <p><button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe?tab=bao-hong")}>Mở sổ báo hỏng</button></p>
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
    <p><button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe/gia-dau")}>Mở giá dầu & định mức</button></p>
  </>;
}

/* ═════════ VH-3 · màn gọn cho năm trang điều xe còn lại + ô «Chờ tôi ký» (Chủ tịch duyệt 10/11/2026) ═════════ */
const ngayVN = (s?: string | null) => (s ? String(s).slice(0, 10).split("-").reverse().slice(0, 2).join("/") : "—");
const isoHom = () => new Date().toISOString().slice(0, 10);

/* ───────── Điều xe › Đề nghị xe ───────── */
export function DeNghiXeGon({ mo }: { mo: Mo }) {
  // «Không còn xe» mở màn đề nghị đầy đủ — cửa từ chối kèm lý do nằm ở đó. Màn gọn chỉ đọc, không ghi.
  const { d, loi } = useDoc<any>("/de-nghi-xe");
  if (!d) return <Loi loi={loi} />;
  const rows: any[] = d.rows || [];
  const cho = rows.filter((x) => x.trang_thai === "cho_lap_lenh").sort((a, b) => a.ngay_di.localeCompare(b.ngay_di));
  const thang = isoHom().slice(0, 7);
  const coLenh = rows.filter((x) => x.trang_thai === "da_lap_lenh" && (x.xu_ly_luc || x.luc || "").slice(0, 7) === thang).length;
  const conNgay = (s: string) => Math.round((new Date(s).getTime() - new Date(isoHom()).getTime()) / 864e5);
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Đề nghị xe</h2></div>
    <O3 ds={[["Chờ lập lệnh", d.dem?.cho_lap_lenh ?? cho.length], ["Đã có lệnh tháng này", coLenh],
             ["Đội xe từ chối", d.dem?.tu_choi ?? 0, "Điều hành thấy lý do và thuê xe ngoài"]]} />
    {cho.map((x) => { const n = conNgay(x.ngay_di);
      return <div key={x.id} style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", padding: "9px 0", borderBottom: "1px solid #e6eaf0" }}>
        <span style={{ flex: "1 1 260px", minWidth: 0 }}><strong>{x.ma_tour} · {x.ten_tour}</strong><br />
          <span className="muted">{ngayVN(x.ngay_di)}→{ngayVN(x.ngay_ve)} · {x.so_khach} khách · {x.so_xe_can} xe · {x.nguoi_de_nghi}</span></span>
        {n <= 3 && <span className={"tag " + (n < 0 ? "cb-do" : "cb-vang")}>{n < 0 ? "đã qua ngày đi" : `còn ${n} ngày`}</span>}
        <button type="button" className="act teal" style={{ margin: 0 }} onClick={() => mo(`/lenh-dieu-xe/lap-lenh?de_nghi=${x.id}`)}>Lập lệnh</button>
        <button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/lenh-dieu-xe/de-nghi")}>Không còn xe</button>
      </div>; })}
    {!cho.length && <p className="muted">Không có đề nghị nào đang chờ lập lệnh.</p>}
    <p><button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/lenh-dieu-xe/de-nghi")}>Mở danh sách đề nghị đầy đủ</button></p>
  </>;
}

/* ───────── Điều xe › Lập lệnh điều xe ───────── */
const NHAN: Record<string, [string, string]> = { da_nhan: ["tài xế đã nhận", "ok"], chua_nhan: ["chưa nhận", "warn"],
  qua_han: ["quá hạn chưa nhận", "red"], tu_choi: ["tài xế báo không nhận", "red"] };
export function LapLenhGon({ mo }: { mo: Mo }) {
  const l = useDoc<any[]>("/fleet/lenh-dieu-xe"), dn = useDoc<any>("/de-nghi-xe?trang_thai=cho_lap_lenh");
  if (!l.d || !dn.d) return <Loi loi={l.loi || dn.loi} />;
  const hom = isoHom(), toi = new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10);
  const sap = l.d.filter((x) => x.status !== "huy" && x.date_from >= hom && x.date_from <= toi)
    .sort((a, b) => String(a.date_from).localeCompare(String(b.date_from)));
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Lập lệnh điều xe</h2>
      <button type="button" className="act teal" style={{ margin: 0 }} onClick={() => mo("/lenh-dieu-xe/lap-lenh")}>Mở màn tìm phương án</button></div>
    <Dong t="Đề nghị đang chờ lệnh" tag={String((dn.d.rows || []).length)} cls="warn" />
    <Dong t="Lệnh chạy trong 7 ngày tới" tag={String(sap.length)} />
    {sap.map((x) => { const [t, c] = NHAN[x.trang_thai_nhan] || ["—", ""];
      return <Dong key={x.id} t={`${x.xe} · ${x.tour || "—"} · ${ngayVN(x.date_from)}`} p={x.tai_xe || "chưa có tài xế"}
        tag={x.trang_thai_nhan === "chua_nhan" && x.han_nhan ? `${t} · hạn ${ngayVN(x.han_nhan)}` : t} cls={c} do={c === "red"} />; })}
    {!sap.length && <p className="muted">7 ngày tới chưa có lệnh VTOS nào.</p>}
  </>;
}

/* ───────── Điều xe › Xe hôm nay ───────── */
export function XeHomNayGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/fleet/xe-hom-nay-gon");
  if (!d) return <Loi loi={loi} />;
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Xe hôm nay</h2><span className="muted">{ngayVN(d.ngay)}/{String(d.ngay).slice(0, 4)}</span></div>
    <O3 ds={[["Đang đi tour", d.dang_di.length], ["Ở bãi", d.o_bai.length], ["Đang sửa / bị chặn", d.bi_chan.length, "báo hỏng mức phải dừng xe"]]} />
    {d.bi_chan.map((x: any) => <Dong key={"c" + x.id} t={x.xe} p={`báo hỏng «${x.ly_do}»`} tag="bị chặn" cls="red" do />)}
    {d.dang_di.map((x: any) => <Dong key={"d" + x.id} t={`${x.xe} · ${x.tour || "—"}`} p={`về ${ngayVN(x.ve)} · ${x.tai_xe || "chưa có tài xế"}`} tag="đang đi" />)}
    <p className="muted">{d.ghi_chu}</p>
    <p><button type="button" className="act grey" style={{ margin: 0 }} onClick={() => mo("/doi-xe/xe-hom-nay")}>Mở bảng theo sheet</button></p>
  </>;
}

/* ───────── Xe & tài xế › Tài xế ───────── */
export function TaiXeGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/tai-xe");
  const [loc, setLoc] = useState("all");
  if (!d) return <Loi loi={loi} />;
  const rows: any[] = (d.rows || []).filter((x: any) => x.dang_lam);
  const thieuBang = (x: any) => !x.gplx_so && !x.gplx_het_han;
  const NH: [string, string, (x: any) => boolean][] = [
    ["all", "Tất cả", () => true], ["bang", "Thiếu bằng lái", thieuBang],
    ["sap", "Bằng sắp hết hạn", (x) => x.sap_het_han], ["tk", "Chưa có tài khoản", (x) => !x.co_tai_khoan]];
  const f = NH.find((n) => n[0] === loc)![2];
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Tài xế</h2><span className="muted">{rows.length} người đang làm</span></div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {NH.map(([k, t, g]) => <Chip key={k} on={loc === k} t={`${t} · ${rows.filter(g).length}`} onClick={() => setLoc(k)} />)}</div>
    {rows.filter(f).map((x) => {
      const tag = !x.co_tai_khoan ? ["chưa có tài khoản", "red"] : thieuBang(x) ? ["thiếu bằng lái", "warn"]
        : x.sap_het_han ? ["bằng sắp hết hạn", "warn"] : x.du_dieu_kien ? ["đủ điều kiện", "ok"] : [x.thieu?.[0] || "thiếu dữ liệu", "warn"];
      return <Dong key={x.id} t={x.full_name}
        p={[(x.xe_dang_dung_ten || []).map((v: any) => v.bien).join(", ") || "chưa gán xe", `${x.so_chuyen_90_ngay} chuyến/90 ngày`].join(" · ")}
        tag={tag[0]} cls={tag[1]} do={tag[1] === "red"} nut="Mở hồ sơ" onNut={() => mo("/tai-xe")} />; })}
    <p className="muted">Chưa có tài khoản = không nhận lệnh được — báo HCNS.</p>
  </>;
}

/* ───────── Xe & tài xế › Chủ xe & hợp đồng ───────── */
export function ChuXeGon({ mo }: { mo: Mo }) {
  const { d, loi } = useDoc<any>("/fleet/cong-no");
  if (!d) return <Loi loi={loi} />;
  const ds: any[] = d.voi_chu_xe?.chi_tiet || [];
  return <>
    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
      <h2 style={{ margin: 0 }}>Chủ xe & hợp đồng</h2></div>
    <O3 ds={[["Chủ xe", ds.length], ["Xe hợp tác", ds.reduce((a, c) => a + (c.so_xe || 0), 0)],
             ["Công ty phải trả", tr(d.voi_chu_xe?.cong_ty_phai_tra), "chỉ tính kỳ đã chốt"]]} />
    {ds.map((c) => { const k = (c.cac_ky || []).slice(-1)[0];
      return <Dong key={c.partner_id} t={c.ho_ten} p={`${c.so_xe} xe${c.xe?.length ? " · " + c.xe.map((v: any) => v.plate).join(", ") : ""}`}
        tag={k ? `kỳ ${k.ky} ${k.da_chot ? "đã chốt" : "chưa chốt"}` : "chưa có bảng quyết toán"} cls={k?.da_chot ? "ok" : "warn"}
        nut="Mở" onNut={() => mo("/doi-xe?tab=quyettoan")} />; })}
    {!ds.length && <p className="muted">Chưa có chủ xe hợp tác nào.</p>}
  </>;
}

/* ───────── Báo cáo từng xe › ô «Chờ tôi ký» ───────── */
export function ChoToiKy({ mo, d }: { mo: Mo; d: any }) {
  if (!d || !d.rows?.length) return null;
  return <div className="xe-uu" style={{ margin: "10px 0" }}>
    <strong style={{ fontSize: 16 }}>{d.rows[0].buoc_ten} · {d.tong} tờ</strong>
    {d.rows.map((x: any) => <Dong key={x.id} t={`QT-${x.id} · ${x.xe} · ${x.tour || x.ten_tour || "—"}`}
      p={`${ngayVN(x.ngay_di)}→${ngayVN(x.ngay_ve)} · doanh thu ${vnd(x.doanh_thu)}`} nut="Mở tờ để ký" chinh
      onNut={() => mo(`/doi-xe?tab=chuyen&chuyen=${x.id}`)} />)}
  </div>;
}
