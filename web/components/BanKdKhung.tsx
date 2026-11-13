"use client";
import { ReactNode, useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import KhungNhung from "@/components/KhungNhung";
import TrangPhanHe from "@/components/TrangPhanHe";
import DoanhThuChiTieuKd from "@/components/DoanhThuChiTieuKd";
import { useHomNay } from "@/components/DauManHinh01";
import NutLich90, { VAI_NUT_LICH_90 } from "@/components/NutLich90";
import { api, vnd, fmtD } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { BieuDoDuong, gonSo } from "@/components/BieuDo";

/** R5-7 · KHUNG CHUNG của ba bàn phòng Kinh doanh lẻ (Trưởng phòng, Trưởng nhóm, Chuyên viên) — Chủ tịch
 *  duyệt bản xem trước 13/11/2026. Ba bàn là BA TỆP RIÊNG (`BanTpKd`, `BanTnKd`, `BanNvKd`), mỗi tệp tự
 *  chọn tab, thẻ và khối của mình; tệp này chỉ giữ phần mà cả ba phải GIỐNG HỆT bàn GĐ (R5-6): thanh ngang
 *  `.mh01-ban`, sáu nút tab navy sáng, mở màn ngay trong bàn (KhungNhung), việc lên nút Công việc.
 *
 *  CHỈ ĐỌC. Số đọc từ `/ban-kd-le/vai/*` (backend/app/services/ban_kd_vai.py); phạm vi (cả phòng / nhóm /
 *  chính mình) cắt ở máy chủ. Ô null in «chưa giao» / «chưa đo», không in 0. */

export type The = { ten: string; mo_ta: string; toi?: string; noi?: "doanh-thu" | "bang" };
export type Tab = { ma: string; ten: string; tieu_de?: string; the: The[] };
export type Ctx = { d: any; dt: any; moToi: (toi: string) => void };

const BIEU_TAB: Record<string, string> = { ban: "🛒", khach: "👥", bk: "🧾", cs: "♡", doi: "⬢", ct: "📊", bc: "📊", luong: "💼" };
/** Biểu tượng thẻ theo đường dẫn màn — chỉ để nhận diện nhanh, không mang nghĩa nghiệp vụ. */
function bieuThe(x: The): string {
  const t = (x.toi || x.noi || "").split("?")[0];
  const B: [string, string][] = [["/ban-tour-le", "▦"], ["/tours", "🗓"], ["/bao-gia", "✎"], ["/bang-gia", "₫"], ["/non-package", "✈"],
    ["/leads", "◎"], ["/inbox", "✉"], ["/requests", "⇄"], ["/bookings", "▤"], ["/cham-soc", "♡"], ["/khieu-nai", "⚑"],
    ["/danh-gia", "★"], ["/to-chuc-kd", "⬢"], ["/reports", "✍"], ["/sales-reports", "📈"], ["/phieu-luong", "💼"],
    ["/cham-cong", "🗒"], ["/de-nghi-mua", "🛍"], ["doanh-thu", "📊"], ["bang", "▥"]];
  return (B.find(([k]) => t === k || t.startsWith(k)) || ["", "◆"])[1];
}

export const so = (x: any) => (typeof x === "number" ? x.toLocaleString("vi-VN") : x);
export const tien = (v: number) => v >= 1e9 ? (v / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 }) + " tỷ"
  : v >= 1e6 ? Math.round(v / 1e6).toLocaleString("vi-VN") + " tr" : vnd(v) + " đ";
const pct = (x: number | null | undefined) => (x == null ? "—" : Math.round(x * 100) + "%");

/** Một thẻ số của dải trên cùng. `v` undefined = đang đọc; null = chưa đo / chưa giao (kèm `chua`). */
export function OSo({ nhan, v, phu, lk, bam, nong, chua }: {
  nhan: string; v: any; phu: string; lk: string; bam?: () => void; nong?: boolean; chua?: string;
}) {
  return <div className={"g5-hd" + (nong && v && v !== "0" ? " do" : "")}>
    <span className="n">{nhan}</span>
    <span className={"s" + (v === undefined || v === null ? " dang" : "")}>{v === undefined ? "…" : v === null ? (chua || "—") : v}</span>
    <span className="p">{phu}</span>
    {bam ? <button type="button" className="g5-cua" onClick={bam}>{lk} →</button> : <span className="g5-cua tat">{lk}</span>}
  </div>;
}

/** Ô doanh thu: «198 tr / 300 tr» khi đã giao chỉ tiêu; «chưa giao» khi chưa. */
export function giaTriDt(o: any): { v: any; phu: string } {
  if (!o) return { v: undefined, phu: "" };
  if (o.so == null) return { v: null, phu: o.ly_do || "chưa đo" };
  const ct = o.chi_tieu;
  // R5-10 (Chủ tịch 14/11/2026): kèm mốc nhận lương cơ bản (200 tr HCM) — chỉ hiện, không đổi cách tính lương.
  const lcb = o.moc_lcb ? ` · mốc lương cơ bản ${tien(o.moc_lcb)}: ${o.dat_lcb ? "đã đạt" : "chưa đạt"}` : "";
  return { v: <>{tien(o.so)} <small>/ {ct == null ? "chưa giao" : tien(ct)}</small></>,
           phu: (ct ? `Đạt ${pct(o.so / ct)} chỉ tiêu tháng` : "Chỉ tiêu tháng chưa giao") + lcb };
}

/** R5-12 · 14/11/2026 (Chủ tịch duyệt bản xem trước): MỘT khối «Doanh thu – Chỉ tiêu» cho bàn GĐ KD, TP,
 *  Trưởng nhóm, Chuyên viên — đường lũy kế + nhịp cần đi như «Nhịp phấn đấu» (vẽ bằng `BieuDoDuong` chung).
 *  «Của phòng» = doanh thu chuyến Lẻ (cùng số màn Chủ tịch / TGĐ); «Của tôi» = giá trị booking của chính
 *  mình. Bàn GĐ chỉ «Của phòng» (`coToi` = false). Mọi con số tính ở máy chủ (`ban_kd_vai.nhip`). */
export function KhoiNhipDoanhThu({ duong, coToi }: { duong: string; coToi: boolean }) {
  const [pv, setPv] = useState<"phong" | "toi">("phong");
  const [ky, setKy] = useState<"thang" | "quy" | "nam">("thang");
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  useEffect(() => {
    setD(null); setLoi("");
    api(`${duong}?ky=${ky}${coToi ? `&pham_vi=${pv}` : ""}`).then(setD).catch((e) => setLoi(errMsg(e)));
  }, [duong, coToi, pv, ky]);
  const diem: any[] = d?.diem || [];
  const nhan = diem.map((x) => x.nhan);
  const lech = d?.lech;
  const bac = d?.bac;
  const nut = <div className="nh-cum">
    {coToi && <div className="nh-seg" role="group" aria-label="Phạm vi">
      {([["phong", "Của phòng"], ["toi", "Của tôi"]] as const).map(([k, t]) =>
        <button key={k} type="button" aria-pressed={pv === k} onClick={() => setPv(k)}>{t}</button>)}
    </div>}
    <div className="nh-seg" role="group" aria-label="Kỳ">
      {([["thang", "Tháng"], ["quy", "Quý"], ["nam", "Năm"]] as const).map(([k, t]) =>
        <button key={k} type="button" aria-pressed={ky === k} onClick={() => setKy(k)}>{t}</button>)}
    </div>
  </div>;
  return <section className={"g5-khoi nh-khoi nh-ky-" + ky} aria-label="Doanh thu – chỉ tiêu">
    <div className="g5-dau"><h2>Doanh thu – chỉ tiêu · {pv === "phong" ? "Của phòng" : "Của tôi"}</h2>{nut}</div>
    {loi ? <p className="g5-loi">Không đọc được doanh thu: {loi}</p> : !d ? <p className="g5-nho">Đang đọc doanh thu…</p> : <>
      <div className="nh-o4">
        <div><b>{tien(d.da)}</b><small>Lũy kế · {d.ten_ky}</small></div>
        <div><b>{d.chi_tieu == null ? "chưa giao" : tien(d.chi_tieu)}</b><small>Chỉ tiêu kỳ{d.pham_vi === "phong" ? ` · cộng ${d.so_nguoi} người` : ""}</small></div>
        <div><b>{d.ty_le == null ? "—" : pct(d.ty_le)}</b><small>Tỷ lệ đạt</small></div>
        <div className={lech == null ? "" : lech >= 0 ? "tot" : "xau"}><b>{lech == null ? "—" : (lech >= 0 ? "+" : "−") + gonSo(Math.abs(lech))}</b>
          <small>{lech == null ? "Chưa có nhịp" : lech >= 0 ? "Trên nhịp" : "Dưới nhịp"}</small></div>
      </div>
      <BieuDoDuong
        ten={`Nhịp ${d.ten_ky.toLowerCase()}`}
        phu={d.co_so === "doanh_thu_chuyen"
          ? "Doanh thu chuyến Lẻ — cùng số khối «Doanh thu theo phòng» trên màn Chủ tịch / TGĐ. Chỉ tiêu phòng = cộng chỉ tiêu từng người."
          : "Giá trị booking theo ngày tour kết thúc — cùng cơ sở với bảng chấm chỉ tiêu."}
        ds={[{ ten: "Lũy kế doanh thu", lop: "d1", diem: diem.map((x) => ({ nhan: x.nhan, gt: x.luy_ke })) },
             { ten: "Nhịp cần đi", lop: "d2", diem: diem.map((x) => ({ nhan: x.nhan, gt: x.nhip })) }]}
        nhan={nhan}
        dinh_dang="tien"
        moc={d.chi_tieu != null ? { gt: d.chi_tieu, nhan: `Chỉ tiêu ${gonSo(d.chi_tieu)}` } : null}
        chan={<span className="nh-chan">
          {lech == null ? "Chỉ tiêu chưa giao cho phạm vi này — chỉ vẽ đường lũy kế." : <>
            <b className={lech >= 0 ? "tot" : "xau"}>{lech >= 0 ? "Trên" : "Dưới"} nhịp {vnd(Math.abs(lech))}</b>
            {" "}· còn <b>{vnd(d.con_phai)}</b> trong {d.con_don_vi} {d.don_vi} nữa
            {d.con_phai > 0 && d.con_don_vi > 0 && <> → mỗi {d.don_vi} cần <b>{gonSo(d.moi_don_vi)}</b></>}</>}
          {bac?.dang_o && <> · đang ở <b>{bac.dang_o.bac}</b> ({bac.dang_o.pct_moc}% mốc)</>}
          {bac?.ke_tiep && <> · còn <b>{vnd(bac.ke_tiep.con_thieu)}</b> nữa lên <b>{bac.ke_tiep.bac}</b></>}
        </span>}
      />
    </>}
    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.nh-khoi .g5-dau{flex-wrap:wrap;gap:10px}
.nh-cum{display:flex;gap:8px;flex-wrap:wrap}
.nh-seg{display:inline-flex;background:#eef3fb;border-radius:999px;padding:3px;gap:2px}
.nh-seg button{font:inherit;font-size:12.5px;font-weight:600;border:0;background:transparent;color:#1d3a68;border-radius:999px;padding:6px 12px;cursor:pointer}
.nh-seg button[aria-pressed="true"]{background:#fff;color:#1f4f97;box-shadow:0 1px 4px rgba(31,79,151,.18)}
.nh-o4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:12px}
.nh-o4>div{border:1px solid #e6ecf5;border-radius:12px;padding:10px 12px;background:linear-gradient(180deg,#f3f7fd,#fff);min-width:0}
.nh-o4 b{display:block;font-size:20px;font-weight:800;color:#1f4f97}
.nh-o4 small{font-size:12px;color:#7d8ca3}
.nh-o4 .tot b,.nh-chan .tot{color:#1c7a52}.nh-o4 .xau b,.nh-chan .xau{color:#b3281f}
.nh-chan{font-size:12.5px;color:#7d8ca3}.nh-chan b{color:#1d3a68}
@media(max-width:720px){.nh-o4{grid-template-columns:repeat(2,minmax(0,1fr))}.nh-o4 b{font-size:17px}}
`}</style>
  </section>;
}

/** Biểu đồ 12 tháng doanh thu – chỉ tiêu của phạm vi bàn. */
export function BieuDo12({ dt, ten }: { dt: any; ten: string }) {
  const thangNay = new Date().getMonth() + 1;
  const ds: any[] = dt?.thang || [];
  const dinh = Math.max(1, ...ds.map((x) => Math.max(x.doanh_thu || 0, x.chi_tieu || 0)));
  const nay = ds[thangNay - 1] || {};
  return <section className="g5-khoi" aria-label={ten}>
    <div className="g5-dau"><h2>{ten}</h2><span>Năm {dt?.nam || ""} · vạch đứt = chỉ tiêu</span></div>
    {!dt ? <p className="g5-nho">Đang đọc doanh thu…</p> : dt.loi ? <p className="g5-loi">Không đọc được doanh thu.</p> : <>
      <div className="g5-ba">
        <div><b>{nay.doanh_thu == null ? "chưa có" : tien(nay.doanh_thu)}</b><small>Tháng {thangNay}</small></div>
        <div><b>{nay.chi_tieu == null ? "chưa giao" : tien(nay.chi_tieu)}</b><small>Chỉ tiêu</small></div>
        <div><b>{nay.doanh_thu != null && nay.chi_tieu ? pct(nay.doanh_thu / nay.chi_tieu) : "—"}</b><small>Tỷ lệ đạt</small></div>
      </div>
      <div className="g5-bd" role="img" aria-label={ten + " 12 tháng"}>
        {ds.map((x, i) => (
          <div key={x.ky} className={"g5-c" + (i + 1 === thangNay ? " on" : "")} title={`${x.ky}: ${x.doanh_thu == null ? "chưa có" : tien(x.doanh_thu)}`}>
            <div className="g5-c-o">
              {x.chi_tieu != null && <s style={{ bottom: (x.chi_tieu / dinh) * 100 + "%" }} />}
              {x.doanh_thu != null && <i style={{ height: Math.max(1, (x.doanh_thu / dinh) * 100) + "%" }} />}
            </div>
            <span>T{i + 1}</span>
          </div>))}
      </div>
      <p className="g5-nho">{dt.co_so}</p>
    </>}
  </section>;
}

/** R5-11 · 14/11/2026 (Chủ tịch duyệt bản xem trước): Đội ngũ và Theo nhóm CAO BẰNG NHAU, khung Đội ngũ có
 *  thanh kéo trượt (dọc + ngang, đầu bảng đứng yên); mã nhóm thành ô navy, mỗi nhóm có thanh tiến độ. Dùng chung
 *  cho bàn TP và bàn GĐ KD — CSS đi kèm khối (`.dn-*`) để bàn GĐ (khung CSS riêng) cũng hiện đúng. */
export function BangDoiNgu({ ds, coNhom, don }: { ds: any[]; coNhom?: boolean; don?: boolean }) {
  return <section className={"g5-khoi dn-khoi" + (don ? " dn-don" : "")} aria-label="Đội ngũ">
    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.dn-hai{display:grid;grid-template-columns:1.55fr 1fr;gap:14px;align-items:stretch}
.dn-khoi{display:flex;flex-direction:column;height:520px}
.dn-khoi .g5-dau{flex:none}
.dn-cuon{flex:1;min-height:0;overflow:auto;border-radius:10px;scrollbar-width:thin;scrollbar-color:#5b9be6 #e8f0fc}
.dn-cuon::-webkit-scrollbar{width:8px;height:8px}.dn-cuon::-webkit-scrollbar-track{background:#e8f0fc;border-radius:99px}
.dn-cuon::-webkit-scrollbar-thumb{background:linear-gradient(#5b9be6,#2f6fc0);border-radius:99px}
.dn-bang{width:100%;border-collapse:separate;border-spacing:0;font-size:13px;min-width:640px}
.dn-bang th{position:sticky;top:0;z-index:1;background:linear-gradient(120deg,#2f6fc0,#1f4f97);color:#fff;font-weight:600;font-size:12px;text-align:left;padding:10px 12px;white-space:nowrap}
.dn-bang th:first-child{border-radius:10px 0 0 10px}.dn-bang th:last-child{border-radius:0 10px 10px 0}
.dn-bang td{padding:10px 12px;border-bottom:1px solid #eef2f8;vertical-align:middle}
.dn-bang tbody tr:hover td{background:#f6f9fe}
.dn-bang b{color:#1d3a68}
.dn-hang{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:800;background:#e8f0fc;color:#1f4f97}
.dn-hang.v1{background:linear-gradient(120deg,#ffd24a,#f0a500);color:#3a2a00}
.dn-toi{margin-left:6px;font-size:11px;font-weight:700;color:#fff;background:#2f6fc0;border-radius:999px;padding:1px 7px}
.dn-nhom{display:inline-block;font-size:11.5px;font-weight:800;color:#1f4f97;background:#e8f0fc;border:1px solid #c9dbf5;border-radius:999px;padding:2px 9px;white-space:nowrap}
.dn-mo{font-size:12px;color:#8b9ab0}
.dn-tr{display:inline-block;width:56px;height:7px;border-radius:99px;background:#eef2f8;overflow:hidden;vertical-align:middle;margin-right:6px}
.dn-tr i{display:block;height:100%;background:linear-gradient(90deg,#2f6fc0,#5b9be6)}
.dn-lcb{display:inline-block;font-size:11.5px;font-weight:700;border-radius:999px;padding:3px 9px;background:#fdeceb;color:#b3281f;white-space:nowrap}
.dn-lcb.dat{background:#e8f5ef;color:#1c6f50}
.dn-ds{list-style:none;margin:0;padding:0 4px 0 0;display:grid;gap:8px}
.dn-ds li{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;padding:10px 12px;border:1px solid #eef2f8;border-left:4px solid #2f6fc0;border-radius:12px;background:linear-gradient(90deg,#f6f9fe,#fff 60%)}
.dn-ds li:hover{border-color:#c9dbf5;border-left-color:#1f4f97;box-shadow:0 4px 14px rgba(31,79,151,.1)}
.dn-ma{display:grid;place-items:center;min-width:46px;height:34px;padding:0 8px;border-radius:10px;font-weight:800;font-size:13px;color:#fff;background:linear-gradient(120deg,#2f6fc0,#1f4f97)}
.dn-ma.xam{background:linear-gradient(120deg,#9aa9bf,#7d8ca3);font-size:11px}
.dn-g{min-width:0}.dn-g b{display:block;font-size:13.5px;color:#1d3a68}.dn-g small{display:block;font-size:12px;color:#8b9ab0}
.dn-thanh{display:block;height:6px;border-radius:99px;background:#eef2f8;overflow:hidden;margin-top:6px}
.dn-thanh i{display:block;height:100%;background:linear-gradient(90deg,#2f6fc0,#5b9be6)}
.dn-pt{font-weight:800;color:#1f4f97;font-size:14px}
.dn-khoi.dn-don{height:auto;max-height:520px}
@media(max-width:1000px){.dn-hai{grid-template-columns:1fr}.dn-khoi{height:auto;max-height:560px}}
`}</style>

    <div className="g5-dau"><h2>Đội ngũ · xếp hạng tháng</h2><span>Giá trị booking · chỉ tiêu mặc định: Chuyên viên 500 tr, Trưởng nhóm và Trưởng phòng 1 tỷ · kéo để xem cả {ds.length} người</span></div>
    {ds.length === 0 ? <p className="g5-nho">Chưa có người nào trong phạm vi.</p> :
      <div className="dn-cuon"><table className="dn-bang">
        <thead><tr><th>#</th><th>Người</th>{coNhom && <th>Nhóm</th>}<th>Doanh thu</th><th>Chỉ tiêu</th><th>Đạt</th><th>Mốc lương cơ bản</th><th>Booking</th></tr></thead>
        <tbody>{ds.map((x, i) => (
          <tr key={x.user_id}>
            <td className="c-hang"><span className={"dn-hang" + (i === 0 && x.tien > 0 ? " v1" : "")}>{i + 1}</span></td>
            <td className="c-ten"><b>{x.ho_ten}</b>{x.la_toi && <span className="dn-toi">tôi</span>}</td>
            {coNhom && <td className="c-nhom">{x.don_vi ? <span className="dn-nhom">{x.don_vi}</span> : "—"}</td>}
            <td className="c-dt" data-n="Doanh thu">{tien(x.tien)}</td>
            <td className="c-ct" data-n="Chỉ tiêu">{x.chi_tieu == null ? <span className="dn-mo">chưa giao</span> : tien(x.chi_tieu)}</td>
            <td className="c-dat">{x.ty_le == null ? "—" : <><span className="dn-tr"><i style={{ width: Math.min(100, x.ty_le * 100) + "%" }} /></span>{pct(x.ty_le)}</>}</td>
            <td className="c-lcb">{x.moc_lcb == null ? "—" : <span className={"dn-lcb" + (x.dat_lcb ? " dat" : "")}>{x.dat_lcb ? "Đạt" : "Chưa"} {tien(x.moc_lcb)}</span>}</td>
            <td className="c-bk" data-n="Booking">{x.so_booking}</td>
          </tr>))}</tbody>
      </table></div>}
  </section>;
}

export function KhoiTheoNhom({ ds, dang }: { ds: any[] | undefined; dang?: boolean }) {
  return <section className="g5-khoi dn-khoi" aria-label="Theo nhóm">
    <div className="g5-dau"><h2>Theo nhóm</h2><span>Doanh thu / chỉ tiêu tháng</span></div>
    {dang ? <p className="g5-nho">Đang đọc số…</p> : !ds || ds.length === 0 ? <p className="g5-nho">Chưa có nhóm nào trong phạm vi.</p> :
      <div className="dn-cuon"><ul className="dn-ds">{ds.map((g: any) => {
        const chua = g.ma === "Chưa có nhóm";
        return <li key={String(g.don_vi_id)}>
          <span className={"dn-ma" + (chua || String(g.ma).length > 5 ? " xam" : "")}>{chua ? "—" : g.ma}</span>
          <span className="dn-g"><b>{chua ? g.ten : (String(g.ten).startsWith("Nhóm") ? g.ten : "Nhóm " + g.ten)}</b>
            <small>{so(g.so_nguoi)} người · {tien(g.tien)} / {g.chi_tieu == null ? "chưa giao" : tien(g.chi_tieu)}</small>
            <span className="dn-thanh"><i style={{ width: Math.min(100, (g.ty_le || 0) * 100) + "%" }} /></span></span>
          <span className="dn-pt">{g.ty_le == null ? "—" : pct(g.ty_le)}</span>
        </li>; })}</ul></div>}
  </section>;
}

/** Hai khối đứng cạnh nhau, cùng chiều cao. */
export function DoiNguVaNhom({ doi, nhom, dang }: { doi: any[]; nhom: any[] | undefined; dang?: boolean }) {
  return <div className="dn-hai">
    <BangDoiNgu ds={doi} coNhom />
    <KhoiTheoNhom ds={nhom} dang={dang} />
  </div>;
}

/** Phải thu khách — booking lẻ của người trong phạm vi, theo bảy mốc hạn (cùng khối bàn GĐ). */
/** R5-14 · Chủ tịch duyệt 14/11/2026 («thanh công nợ phải thu quá dài»): bản GỌN — một số tổng, MỘT thanh
 *  chồng màu theo hạn (quá hạn = hồng logo), bảng các mốc chia hai cột, nợ cũ thành ô cảnh báo riêng. Dùng chung
 *  bốn bàn; đứng cạnh khối Doanh thu – Chỉ tiêu trong `HangTien`. CSS đi kèm (`pt-*`). */
const MAU_HAN = ["var(--vtos-logo-hong)", "#2f6fc0", "#4a86d4", "#6c9fe0", "#8fb7ea", "#b0cdf1", "#cfdff6"];
export function KhoiPhaiThu({ pt, moToi }: { pt: any; moToi: (t: string) => void }) {
  const ds: [string, number][] = pt?.nhom ? Object.entries(pt.nhom).map(([k, v]: [string, any]) => [k, Number(v || 0)]) : [];
  const tong = ds.reduce((a, [, v]) => a + v, 0) || 1;
  return <section className="g5-khoi pt-khoi" aria-label="Phải thu khách hàng">
    <div className="g5-dau"><h2>Phải thu khách</h2><span>Booking tour lẻ · theo hạn đi</span></div>
    {!pt ? <p className="g5-nho">Đang đọc số…</p> : pt.tong == null ? <p className="g5-nho">{pt.ly_do || "chưa đo"}</p> : <>
      <div className="pt-tong"><b>{tien(pt.tong)}</b><small>{so(pt.so_booking)} booking còn nợ · hạn = ngày khởi hành</small></div>
      <div className="pt-chong" role="img" aria-label="Phải thu chia theo hạn">
        {ds.map(([k, v], i) => v > 0 && <i key={k} title={`${k}: ${tien(v)}`} style={{ width: (v / tong) * 100 + "%", background: MAU_HAN[i % MAU_HAN.length] }} />)}
      </div>
      <div className="pt-ht">
        {ds.map(([k, v], i) => <div key={k} className={k === "Quá hạn" ? "qh" : ""}>
          <i style={{ background: MAU_HAN[i % MAU_HAN.length] }} /><span>{k}</span><b>{tien(v)}</b></div>)}
      </div>
    </>}
    {pt?.no_cu?.tong != null && <div className="pt-nocu"><span aria-hidden="true">⚠</span>
      <span>Nợ cũ cần đối soát <b>{tien(pt.no_cu.tong)}</b> · {so(pt.no_cu.so_booking)} booking — {pt.no_cu.ghi}. Không cộng vào số tổng ở trên.</span></div>}
    {pt?.tong != null && <button type="button" className="g5-cua pt-nut" onClick={() => moToi("/bookings?mang=le")}>Xem booking còn nợ →</button>}
    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.pt-khoi{display:flex;flex-direction:column;gap:12px}
.pt-tong{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.pt-tong b{font-size:28px;font-weight:800;color:#1f4f97}.pt-tong small{color:#7d8ca3;font-size:12.5px}
.pt-chong{display:flex;height:16px;border-radius:99px;overflow:hidden;gap:2px;background:#eef3fb}.pt-chong i{display:block;height:100%;min-width:3px}
.pt-ht{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:2px 16px}
.pt-ht div{display:grid;grid-template-columns:10px 1fr auto;gap:8px;align-items:center;font-size:13px;padding:6px 0;border-bottom:1px dashed #e6ecf5}
.pt-ht i{width:10px;height:10px;border-radius:3px}.pt-ht b{font-variant-numeric:tabular-nums;color:#1d3a68}
.pt-ht .qh span,.pt-ht .qh b{color:#d6336c;font-weight:800}
.pt-nocu{display:flex;gap:10px;align-items:flex-start;background:#fff4e5;border:1px solid #f3d3a4;border-radius:12px;padding:10px 12px;font-size:12.5px;line-height:1.5;color:#5b4520}
.pt-nocu b{color:#b45309}
.pt-khoi .pt-nut{align-self:flex-start;font-size:12.5px;font-weight:700;color:#1f4f97;background:#e8f0fc;border-radius:999px;padding:7px 14px}
@media(max-width:600px){.pt-ht{grid-template-columns:1fr}}
`}</style>
  </section>;
}

/** R5-14: hàng tiền — Doanh thu – Chỉ tiêu bên trái, Phải thu gọn bên phải. */
export function HangTien({ duong, coToi, pt, moToi }: { duong: string; coToi: boolean; pt: any; moToi: (t: string) => void }) {
  return <div className="g5-tien">
    <KhoiNhipDoanhThu duong={duong} coToi={coToi} />
    <KhoiPhaiThu pt={pt} moToi={moToi} />
    <style>{`
.g5-tien{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:14px;align-items:start}
@media(max-width:1100px){.g5-tien{grid-template-columns:1fr}}
`}</style>
  </div>;
}

/** R5-14 · Chủ tịch duyệt 14/11/2026: «Chuyến cần thúc bán» thành CẢNH BÁO KHẨN — khung và đầu màu hồng logo,
 *  chuông nháy, đếm chuyến / chỗ trống / khách còn thiếu để hòa vốn, mỗi chuyến một thẻ có «còn N ngày».
 *  Cùng hàm, cùng số với bàn GĐ (`ban_kd_le.thuc_ban`). Không còn chuyến nào thì thu về một dòng xanh. */
function ngayCon(d: string): number {
  const a = new Date(d + "T00:00:00"), h = new Date(); h.setHours(0, 0, 0, 0);
  return Math.round((a.getTime() - h.getTime()) / 86400000);
}
export function BangThucBan({ ds, moToi }: { ds: any[] | undefined; moToi: (t: string) => void }) {
  const [het, setHet] = useState(false);
  const thieuHv = (r: any) => r.khach_hoa_von == null ? 0 : Math.max(0, r.khach_hoa_von - r.cho_da_ban);
  const cho = (ds || []).reduce((a, r) => a + (r.cho_con || 0), 0);
  const thieu = (ds || []).reduce((a, r) => a + thieuHv(r), 0);
  const css = <style>{`
.kh-khoi{border:2px solid var(--vtos-logo-hong);border-radius:18px;background:linear-gradient(180deg,#fff0f4,#fff 160px);overflow:hidden}
.kh-dau{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 16px;color:#fff;background:linear-gradient(120deg,var(--vtos-logo-hong),#e0466f)}
.kh-chuong{position:relative;display:grid;place-items:center;width:36px;height:36px;border-radius:50%;background:rgba(255,255,255,.2);font-size:18px;flex:none}
.kh-chuong::after{content:"";position:absolute;inset:-4px;border-radius:50%;border:2px solid rgba(255,255,255,.75);animation:khNhay 1.6s ease-out infinite}
@keyframes khNhay{0%{transform:scale(.85);opacity:1}100%{transform:scale(1.35);opacity:0}}
@media (prefers-reduced-motion:reduce){.kh-chuong::after{animation:none}}
.kh-dau h2{margin:0;font-size:16px;letter-spacing:.03em;color:#fff}.kh-dau p{margin:2px 0 0;font-size:12.5px;opacity:.92}
.kh-dem{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}.kh-dem span{background:rgba(255,255,255,.2);border-radius:999px;padding:4px 11px;font-size:12px;font-weight:700}
.kh-ds{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:12px}
.kh-the{background:#fff;border:1px solid #f3dbe3;border-left:5px solid var(--vtos-logo-hong);border-radius:12px;padding:10px 12px;display:grid;gap:7px;min-width:0}
.kh-the.cam{border-left-color:#d97706}
.kh-the .d{display:flex;justify-content:space-between;align-items:center;gap:8px}
.kh-the .ma{font-weight:800;color:#1d3a68}
.kh-con{font-size:11.5px;font-weight:800;color:#fff;background:var(--vtos-logo-hong);border-radius:999px;padding:3px 10px;white-space:nowrap}
.kh-the.cam .kh-con{background:#d97706}
.kh-the small{color:#7d8ca3;font-size:12px}
.kh-bar{height:8px;border-radius:99px;background:#eef3fb;position:relative}.kh-bar i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:#2f6fc0}
.kh-bar s{position:absolute;top:-4px;bottom:-4px;width:2px;background:#d6336c}
.kh-so{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;flex-wrap:wrap}.kh-so b{color:#d6336c}.kh-so .dat{color:#1c7a52;font-weight:700}
.kh-the.cam .kh-so b{color:#b45309}
.kh-phu{font-size:11.5px;color:#7d8ca3}
.kh-the .g5-cua{justify-content:center;font-size:12.5px;font-weight:700;border-radius:999px;padding:8px;background:#fff0f4;color:#d6336c;text-decoration:none}
.kh-the .g5-cua:hover{background:var(--vtos-logo-hong);color:#fff}
.kh-them{margin:0 12px 12px}
.kh-yen{display:flex;align-items:center;gap:10px;background:#e8f5ef;border:1px solid #bfe3d0;color:#1c7a52;border-radius:14px;padding:12px 16px;font-weight:600}
@media(max-width:1100px){.kh-ds{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){.kh-ds{grid-template-columns:1fr}.kh-dem{margin-left:0}}
`}</style>;
  if (!ds) return <section className="g5-khoi" aria-label="Chuyến cần thúc bán"><p className="g5-nho">Đang đọc chuyến cần thúc bán…</p></section>;
  if (ds.length === 0) return <div className="kh-yen" role="status">✓ Không có chuyến nào khởi hành trong 7 ngày còn chỗ trống cần thúc bán.{css}</div>;
  const bien = Math.round(((ds[0]?.bien_muc_tieu) || 0.1) * 100);
  return <section className="kh-khoi" aria-label="Cảnh báo khẩn: chuyến cần thúc bán">
    <div className="kh-dau"><span className="kh-chuong" aria-hidden="true">🔔</span>
      <div><h2>KHẨN · CHUYẾN CẦN THÚC BÁN</h2><p>Khởi hành trong 7 ngày, còn chỗ trống</p></div>
      <div className="kh-dem"><span>{so(ds.length)} chuyến</span><span>{so(cho)} chỗ trống</span>{thieu > 0 && <span>thiếu {so(thieu)} khách hòa vốn</span>}</div></div>
    <div className="kh-ds">{(het ? ds : ds.slice(0, 6)).map((r: any) => {
      const n = ngayCon(r.start_date);
      const p = r.cho_mo_ban ? Math.min(100, (r.cho_da_ban / r.cho_mo_ban) * 100) : 0;
      const co = r.khach_hoa_von != null, t = thieuHv(r);
      return <div key={r.id} className={"kh-the" + (n > 4 ? " cam" : "")}>
        <div className="d"><span className="ma">{r.code}</span><span className="kh-con">{n <= 0 ? "đi hôm nay" : `còn ${n} ngày`}</span></div>
        <small>{r.name} · đi {fmtD(r.start_date)}</small>
        <div className="kh-bar"><i style={{ width: p + "%" }} />{co && r.cho_mo_ban ? <s style={{ left: Math.min(100, (r.khach_hoa_von / r.cho_mo_ban) * 100) + "%" }} /> : null}</div>
        <div className="kh-so"><span>Đã bán {r.cho_da_ban} / {r.cho_mo_ban} · còn {r.cho_con} chỗ</span>
          {!co ? <span className="kh-phu">chưa có dự toán</span> : t > 0 ? <span>thiếu <b>{t} khách</b> hòa vốn</span> : <span className="dat">đã hòa vốn</span>}</div>
        <div className="kh-phu">Giá bán {vnd(r.gia_ban)} đ{r.khach_dat_bien != null && <> · lãi {bien}% cần {r.khach_dat_bien} khách</>}{r.bien_khi_day != null && <> · bán đủ {r.khach_toi_da} khách lãi {(r.bien_khi_day * 100).toFixed(1).replace(".", ",")}%</>}</div>
        <button type="button" className="g5-cua" onClick={() => moToi(`/tours/${r.id}`)}>Chi tiết →</button>
      </div>; })}</div>
    {ds.length > 6 && <button type="button" className="g5-them kh-them" onClick={() => setHet(!het)}>{het ? "Thu gọn" : `Xem thêm ${ds.length - 6} chuyến`}</button>}
    {css}
  </section>;
}

export default function BanKdKhung({ ten, phamVi, tabs, tongQuan }: {
  ten: string; phamVi: (d: any) => string; tabs: Tab[]; tongQuan: (c: Ctx) => ReactNode;
}) {
  const { toast, datViecBan, user } = useShell();
  const homNay = useHomNay();
  const [d, setD] = useState<any>(null);
  const dt = null;
  const [loi, setLoi] = useState("");
  const [tab, setTab] = useState(tabs[0].ma);
  const [mo, setMo] = useState<The | null>(null);
  const [khung, setKhung] = useState<string | null>(null);

  const DUONG = [...new Set(tabs.flatMap((t) => t.the.filter((x) => x.toi).map((x) => (x.toi as string).split("?")[0])))]
    .concat(["/tours", "/bookings", "/requests", "/leads", "/cham-soc", "/phieu-luong", "/reports"]);
  const laKd = (h: string) => DUONG.some((t) => h === t || h.startsWith(t + "/") || h.startsWith(t + "?"));

  const tai = useCallback(() => {
    api("/ban-kd-le/vai/tong-quan").then((r) => { setD(r); setLoi(""); })
      .catch((e) => { setLoi(errMsg(e)); toast(errMsg(e), true); });
  }, []); // eslint-disable-line
  useEffect(() => { tai(); }, [tai]);
  // R5-12: khối «Doanh thu – Chỉ tiêu» tự đọc `/vai/nhip`; biểu đồ cột 12 tháng (`/vai/doanh-thu`) đã bỏ.

  const moTab = (ma: string) => { setTab(ma); setMo(null); setKhung(null); if (ma === tabs[0].ma) tai(); };
  const moThe = (t: The) => { setMo(t); setKhung(t.toi || null); window.scrollTo({ top: 0 }); };
  const moToi = (toi: string) => {
    for (const t of tabs) {
      const x = t.the.find((c) => c.toi && c.toi.split("?")[0] === toi.split("?")[0]);
      if (x) { setTab(t.ma); setMo(x); setKhung(toi); window.scrollTo({ top: 0 }); return; }
    }
    if (toi.startsWith("/fit")) { setMo({ ten: "Chỉ tiêu theo người & nhóm", mo_ta: "", noi: "doanh-thu" }); setKhung(null); return; }
    setMo({ ten: "Chi tiết", mo_ta: "" }); setKhung(toi); window.scrollTo({ top: 0 });
  };
  const ngoaiKhung = (h: string) => { if (h.startsWith("/fit")) { moTab(tabs[0].ma); return true; } return false; };

  // Việc cần xử lý lên nút Công việc trên thanh ngang — cùng cơ chế bàn GĐ (VH-42 / R5-4).
  useEffect(() => {
    if (!d) return;
    datViecBan((d.viec || []).map((v: any) => ({ ma: v.ma, muc: v.muc, tieu_de: v.tieu_de, mo_ta: v.mo_ta,
      bam: v.toi ? () => moToi(v.toi) : undefined })));
  }, [d, datViecBan]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => datViecBan(null), [datViecBan]);

  const t = tabs.find((x) => x.ma === tab) || tabs[0];
  return (<div className="g5">
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten">{ten}</h1>
      <div className="mh01-ban-cum">
        {d && <div className="mh01-ban-ngay"><span>Phạm vi</span>{phamVi(d)}</div>}
        <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
        {user?.role && VAI_NUT_LICH_90.includes(user.role) && <NutLich90 />}
      </div>
    </div>

    <nav className="g5-tab" aria-label={ten}>
      {tabs.map((x) => <button key={x.ma} type="button" aria-pressed={tab === x.ma} onClick={() => moTab(x.ma)}>{x.ten}</button>)}
    </nav>

    {mo && <div className="g5-mo">
      <button type="button" className="g5-lui" onClick={() => { setMo(null); setKhung(null); }}>‹ {t.tieu_de || t.ten}</button>
      <b>{mo.ten}</b>
    </div>}
    {mo && khung && <KhungNhung key={khung} toi={khung} ten={mo.ten} cuaBan={laKd} ngoai={ngoaiKhung} anDauBan khungBan />}
    {mo && !khung && mo.noi === "doanh-thu" && <DoanhThuChiTieuKd anNhip />}
    {mo && !khung && mo.noi === "bang" && <TrangPhanHe khoa="kdle" khongThanh />}

    {!mo && tab !== tabs[0].ma && <>
      {/* R5-11: đầu tab là dải navy sáng; mỗi thẻ có vạch navy bên trái và ô biểu tượng. */}
      <div className="g5-muc2"><span className="bi" aria-hidden="true">{BIEU_TAB[t.ma] || "◆"}</span><div><b>{t.tieu_de || t.ten}</b><small>Bấm là mở ngay trong bàn</small></div></div>
      <div className="g5-luoi">
        {t.the.map((x) => (
          <button key={x.ten} type="button" className="g5-the-lk" onClick={() => moThe(x)}>
            <span className="bi" aria-hidden="true">{bieuThe(x)}</span>
            <span className="g"><b>{x.ten}</b><small>{x.mo_ta}</small></span><i aria-hidden="true">↗</i>
          </button>))}
      </div>
    </>}

    {!mo && tab === tabs[0].ma && <>
      {loi && <div className="g5-khoi"><p className="g5-loi">Không đọc được số của bàn: {loi}</p></div>}
      {d?.canh_bao && <div className="g5-khoi g5-canh"><p>{d.canh_bao}</p></div>}
      {/* R5-15 · Chủ tịch 14/11/2026: «hình 1 xoá» — bỏ các dòng ghi chú phạm vi / đối chiếu ở đầu bàn. */}
      {tongQuan({ d, dt, moToi })}
    </>}

    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.g5{--g5-ns-a:#2f6fc0;--g5-ns-b:#1f4f97;--g5-ns-c:#5b9be6;--g5-ns-nhat:#e8f0fc;--g5-ns-vien:#c9dbf5;--g5-line:#e3e9f2;--g5-line2:#eef2f8;
  --g5-chu:#17263f;--g5-chu2:#5a6b85;--g5-chu3:#8b9ab0;--g5-dam:#1d3a68;display:flex;flex-direction:column;gap:14px;color:var(--g5-chu)}
.g5-tab{display:flex;gap:8px;background:#fff;border:1px solid var(--g5-ns-vien);border-radius:16px;padding:6px;overflow-x:auto;
  box-shadow:0 1px 2px rgba(31,79,151,.06),0 6px 18px rgba(31,79,151,.08)}
.g5-tab button{flex:1 0 auto;margin:0;font:inherit;text-align:center;padding:11px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.2);
  font-size:14px;font-weight:700;color:#fff;cursor:pointer;white-space:nowrap;transition:background .15s,transform .15s;
  background:linear-gradient(120deg,var(--g5-ns-c),#3f80d0);box-shadow:0 2px 6px rgba(31,79,151,.22),inset 0 1px 0 rgba(255,255,255,.3)}
.g5-tab button:hover{background:linear-gradient(120deg,#4a8ddc,var(--g5-ns-a));transform:translateY(-1px)}
.g5-tab button[aria-pressed=true]{background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));
  box-shadow:0 0 0 2px #fff,0 0 0 4px #7fb2f0,0 6px 16px rgba(31,79,151,.4),inset 0 1px 0 rgba(255,255,255,.25)}
.g5-tab button:focus-visible,.g5-the-lk:focus-visible,.g5-cua:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
.g5-mo{display:flex;align-items:center;gap:12px}
.g5-lui{margin:0;font:inherit;font-size:13px;font-weight:700;color:var(--g5-ns-b);background:var(--g5-ns-nhat);border:1px solid var(--g5-ns-vien);border-radius:999px;padding:5px 12px;cursor:pointer}
.g5-muc h2{margin:0;font-size:19px;font-weight:600;color:var(--g5-dam)}
.g5-muc p{margin:2px 0 0;font-size:12.5px;color:var(--g5-chu3)}
.g5-luoi{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.g5-the-lk{margin:0;font:inherit;text-align:left;display:flex;justify-content:space-between;align-items:center;gap:10px;background:#fff;
  border:1px solid var(--g5-line);border-left:4px solid var(--g5-ns-a);border-radius:10px;padding:16px;cursor:pointer;color:inherit}
.g5-the-lk:hover{border-color:var(--g5-ns-vien);box-shadow:0 8px 20px rgba(31,79,151,.12)}
.g5-the-lk b{display:block;font-size:14.5px;color:var(--g5-dam)}
.g5-the-lk small{display:block;font-size:12.5px;color:var(--g5-chu2);margin-top:3px}
.g5-the-lk i{font-style:normal;flex:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;color:#fff;background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b))}
.g5-the-lk{position:relative;overflow:hidden;justify-content:flex-start;border-radius:14px;transition:border-color .15s,box-shadow .15s,transform .15s}
.g5-the-lk:hover{transform:translateY(-1px)}
.g5-the-lk .bi{flex:none;display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:var(--g5-ns-nhat);color:var(--g5-ns-b);font-size:18px}
.g5-the-lk .g{flex:1;min-width:0}
.g5-the-lk i{margin-left:auto}
.g5-muc2{display:flex;align-items:center;gap:12px;padding:14px 18px;border-radius:14px;color:#fff;background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));box-shadow:0 6px 18px rgba(31,79,151,.25)}
.g5-muc2 .bi{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:rgba(255,255,255,.18);font-size:18px}
.g5-muc2 b{display:block;font-size:17px}.g5-muc2 small{display:block;font-size:12.5px;opacity:.85}
.g5-nhom{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:800;letter-spacing:.12em;color:var(--g5-ns-b);margin:2px 0 -6px}
.g5-nhom::before{content:"";width:4px;height:14px;border-radius:3px;background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-dai5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.g5-dai3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.g5-hd{position:relative;overflow:hidden;background:#fff;border:1px solid var(--g5-line);border-radius:14px;padding:16px 16px 14px;display:flex;flex-direction:column;gap:2px;min-width:0;
  box-shadow:0 1px 2px rgba(23,38,63,.04);transition:border-color .15s,box-shadow .15s,transform .15s}
.g5-hd::before{content:"";position:absolute;inset:0 0 auto;height:4px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-hd:hover{border-color:var(--g5-ns-vien);box-shadow:0 8px 20px rgba(31,79,151,.12);transform:translateY(-1px)}
.g5-hd .n{font-size:13px;font-weight:600;color:var(--g5-chu2)}
.g5-hd .s{font-size:26px;font-weight:800;color:var(--g5-ns-b);font-variant-numeric:tabular-nums;line-height:1.2}
.g5-hd .s small{font-size:13px;color:var(--g5-chu3);font-weight:700}
.g5-hd .s.dang{color:var(--g5-chu3);font-size:20px}
.g5-hd.do .s{color:#b3281f}
.g5-hd .p{font-size:12.5px;color:var(--g5-chu3);flex:1}
.g5-cua{flex:0 0 auto;margin:0;font:inherit;font-size:13px;font-weight:600;color:var(--g5-dam);background:none;border:0;padding:3px 0;cursor:pointer;white-space:nowrap}
.g5-cua:hover{color:var(--g5-ns-a);text-decoration:underline}
.g5-hd .g5-cua{align-self:flex-start;margin-top:8px;font-size:12.5px;font-weight:700;color:var(--g5-ns-b);background:var(--g5-ns-nhat);border-radius:999px;padding:5px 11px}
.g5-hd .g5-cua:hover{background:var(--g5-ns-a);color:#fff;text-decoration:none}
.g5-cua.tat{color:var(--g5-chu3);font-weight:500;cursor:default}
.g5-hai{display:grid;grid-template-columns:1.4fr 1fr;gap:14px;align-items:start}
.g5-khoi{background:#fff;border:1px solid var(--g5-line);border-radius:16px;padding:18px 20px;min-width:0;box-shadow:0 1px 2px rgba(23,38,63,.04)}
.g5-canh{background:#fbf3e0;border-color:#f1d98a}.g5-canh p{margin:0;font-size:13px;color:#8d6200}
.g5-ghi{margin:-4px 2px 0;font-size:12px;color:var(--g5-chu3)}
.g5-dau{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--g5-line2)}
.g5-dau h2{margin:0;font-size:16.5px;font-weight:700;color:var(--g5-dam);display:flex;align-items:center;gap:9px}
.g5-dau h2::before{content:"";flex:none;width:4px;height:18px;border-radius:3px;background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-dau span{font-size:12px;color:var(--g5-chu3)}
.g5-nho{font-size:12.5px;color:var(--g5-chu2);margin:10px 0 0;line-height:1.6}
.g5-nocu{border-top:1px dashed var(--g5-line);padding-top:8px;color:#8d6200}
.g5-lcb{display:inline-block;font-size:11.5px;font-weight:700;border-radius:999px;padding:3px 9px;background:#fdeceb;color:#b3281f;white-space:nowrap}
.g5-lcb.dat{background:#e8f5ef;color:#1c6f50}
.g5-loi{color:var(--vtos-danger);margin:0}
.g5-cuon{overflow-x:auto}
.g5-bang{width:100%;border-collapse:separate;border-spacing:0;margin-top:6px;font-size:13px;min-width:600px}
.g5-bang th{background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));color:#fff;font-weight:600;font-size:12px;text-align:left;padding:11px 13px}
.g5-bang th:first-child{border-radius:10px 0 0 10px}.g5-bang th:last-child{border-radius:0 10px 10px 0}
.g5-bang td{padding:12px 13px;border-bottom:1px solid var(--g5-line2);vertical-align:top}
.g5-bang tbody tr:hover td{background:#f6f9fe}
.g5-bang tr:last-child td{border-bottom:0}
.g5-bang .ma{color:var(--g5-dam);font-variant-numeric:tabular-nums}
.g5-bang .ngay{font-size:12px;color:var(--g5-chu3);margin-top:2px}
.g5-bang .ngay b.cam{color:#a85c16}.g5-bang .ngay.dat{color:#1c6f50;font-weight:600}
.g5-bang b.lai{color:#1c6f50;font-size:15px}.g5-bang b.lai.lo{color:#b3281f}
.g5-bang .vach{position:relative;width:74px;height:4px;border-radius:2px;background:#e4eaf4;margin-top:6px}
.g5-bang .vach i{display:block;height:100%;border-radius:2px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-bang .vach s{position:absolute;top:-3px;width:2px;height:10px;background:#b3281f;text-decoration:none}
.g5-bang .nhan{display:inline-block;font-size:11.5px;font-weight:600;border-radius:6px;padding:4px 9px}
.g5-bang .nhan.chua{background:#fbf3e0;color:#8d6200}
.g5-hang{display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:800;background:var(--g5-ns-nhat);color:var(--g5-ns-b)}
.g5-hang.v1{background:linear-gradient(120deg,#ffd24a,#f0a500);color:#3a2a00}
.g5-toi{margin-left:6px;font-size:11px;font-weight:700;color:#fff;background:var(--g5-ns-a);border-radius:999px;padding:1px 7px}
.g5-tr{display:inline-block;width:70px;height:7px;border-radius:99px;background:var(--g5-line2);overflow:hidden;vertical-align:middle;margin-right:6px}
.g5-tr i{display:block;height:100%;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-ba{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 8px}
.g5-ba>div{background:linear-gradient(180deg,#f6f9fe,#eef4fc);border:1px solid var(--g5-ns-vien);border-radius:12px;padding:10px 14px;min-width:130px}
.g5-ba b{display:block;font-size:19px;font-weight:800;color:var(--g5-ns-b)}.g5-ba small{font-size:12px;color:var(--g5-chu3)}
.g5-bd{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:6px;height:170px;align-items:end;border-bottom:1px solid var(--g5-line);padding-top:6px}
.g5-c{display:flex;flex-direction:column;align-items:center;height:100%;gap:4px}
.g5-c-o{position:relative;flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center}
.g5-c-o i{display:block;width:62%;background:#c9dbf5;border-radius:6px 6px 2px 2px}
.g5-c.on .g5-c-o i{background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-c-o s{position:absolute;left:4%;right:4%;border-top:2px dashed #e0a64b;text-decoration:none}
.g5-c span{font-size:10.5px;color:var(--g5-chu3)}
.g5-han{display:grid;gap:9px;margin-top:6px}
.g5-han .h{display:grid;grid-template-columns:74px 1fr 64px;gap:10px;align-items:center;font-size:13px}
.g5-han .tr{height:12px;border-radius:6px;background:var(--g5-line2);overflow:hidden}
.g5-han .tr i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-han .h.qh .tr i{background:#a3185a}
.g5-han b{text-align:right;font-variant-numeric:tabular-nums}
.g5-them{margin:12px 0 0;font:inherit;font-size:13px;font-weight:700;color:var(--g5-ns-b);background:#fff;border:1px solid var(--g5-ns-vien);border-radius:999px;padding:6px 14px;cursor:pointer}
.g5-ds{list-style:none;margin:0;padding:0}
.g5-ds li{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid var(--g5-line2);font-size:13.5px}
.g5-ds li:last-child{border-bottom:0}
.g5-ds small{display:block;color:var(--g5-chu3);font-size:12px}
.g5-ds .g5-cua{font-size:12.5px;font-weight:700;color:var(--g5-ns-b);background:var(--g5-ns-nhat);border-radius:999px;padding:5px 11px}
@media(max-width:1100px){.g5-dai5{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:1000px){.g5-hai{grid-template-columns:1fr}}
@media(max-width:620px){.g5-dai5,.g5-luoi{grid-template-columns:1fr 1fr}.g5-luoi{grid-template-columns:1fr}.g5-dai3{grid-template-columns:1fr 1fr}}
`}</style>
  </div>);
}
