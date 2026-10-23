"use client";
/** TQ-1 · MỤC «VẬN HÀNH & CÔNG VIỆC» — anh Tuấn duyệt bản vẽ 22/10/2026 (Tổng quan Vận hành v1.1).
 *
 *  Thay ĐÚNG chỗ hai khối cũ: «Tồn đọng cần xử lý» (KhoiTonDongMuc) và hàng thẻ nhỏ (HangThe), giữa
 *  khối dòng tiền và khối đội xe. Không thêm màn hình mới, không thêm quyền mới: hai danh sách mở
 *  NGAY TRÊN trang này qua `?xem=viec` và `?xem=qua-han`.
 *
 *  Bốn con số trước đây nói sai, và mỗi chỗ sửa ở máy chủ chứ không ở đây (ranh giới 09/9):
 *    · «Tồn đọng» đếm CẢNH BÁO; nay đếm VIỆC — gộp theo hồ sơ sau khi lọc theo quyền
 *      (`services/tong_quan_viec`). Số cảnh báo vẫn hiện, ở dòng phụ.
 *    · «Quá hạn quyết toán» bị trần 100; nay đếm đủ (`tong_quan_tour.qua_han_quyet_toan`).
 *    · «Chờ quyết toán» = A + B; nhóm C (đã về chưa đóng sổ) là dòng phụ, KHÔNG cộng vào tổng.
 *    · Mức giữa gọi là «Cảnh báo» (bản cũ gọi khác — Chủ tịch chốt đổi nhãn).
 *
 *  BA NHÓM TOUR (chuyển từ page.tsx, TC-42 · 16/9/2026): hệ thống KHÔNG có trạng thái «đang chạy» —
 *  một chuyến giữ `da_duyet` suốt từ lúc mở bán qua cả hành trình, nên phép chia đang bán / đang đi
 *  là theo NGÀY, làm ở máy chủ (`services/dem_tour.theo_giai_doan`). Nhóm thứ ba — đã qua ngày về
 *  mà vẫn «đã duyệt» — là dòng phụ của ô Chờ quyết toán, vì đó chính là việc còn thiếu (Điều hành
 *  chưa bấm kết thúc). Bỏ nó đi thì chỗ chênh biến mất lặng lẽ.
 *
 *  Danh sách TÍNH LẠI lúc mở (Chủ tịch chốt TT02) — nên nó có thể khác ô vừa đọc; khi khác, dải
 *  «Số đã cập nhật» nói rõ cũ → mới và giờ, thay vì để hai con số lệch nhau không lời giải thích.
 *
 *  Năm trạng thái của một ô, mỗi trạng thái một cách hiện: có số · số 0 thật · chưa kết nối (máy
 *  chủ cũ chưa trả trường) · lỗi (máy chủ trả `null` vì phép tính hỏng) · lưu đệm (bảng điều hành trả từ bộ nhớ đệm ≤ 5 phút).
 *  Không có trường hợp nào được thay bằng 0.
 */
import "./KhoiVanHanh.css";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

const so = (x: any) => Number(x || 0).toLocaleString("vi-VN");
const coSo = (x: any) => typeof x === "number" && Number.isFinite(x);
const ngay = (s?: string | null) => {
  if (!s) return "—";
  const [y, m, d] = String(s).slice(0, 10).split("-");
  return d && m && y ? `${d}/${m}/${y}` : String(s);
};
/** Giờ máy chủ in ra, đọc NGUYÊN CHỮ như `fmtDT` (lib/api.ts) — không đổi múi giờ ở trình duyệt:
 *  máy chủ trả giờ không kèm múi, và trình duyệt đoán múi là cách chắc nhất để lệch bảy tiếng. */
const gio = (s?: string | null) => (s && s.length >= 16 ? `${s.slice(11, 16)} · ${ngay(s)}` : "");

const TEN_MUC: Record<string, string> = {
  red: "Nghiêm trọng", warn: "Cảnh báo", info: "Theo dõi", chua_phan_loai: "Chưa phân loại",
};
const MAU_MUC: Record<string, string> = { red: "c-do", warn: "c-vang", info: "c-xam", chua_phan_loai: "c-la" };

/** Một con số trong ô. `undefined` = máy chủ chưa có trường; `null` = máy chủ tính hỏng. */
function So({ v, dv, onThuLai }: { v: any; dv?: string; onThuLai?: () => void }) {
  if (v === undefined) return <div className="vh-so rong">—</div>;
  if (v === null) return <div><span className="vh-loi">Không tải được</span>{" "}
    {onThuLai && <button type="button" className="vh-nut phu" onClick={onThuLai}>Thử lại</button>}</div>;
  return <div className="vh-so">{so(v)}{dv && <span className="dv">{dv}</span>}</div>;
}

export type DuLieuVanHanh = {
  viec?: any | null;              // sec.viec_van_hanh
  qua_han?: number | null;        // sec.qua_han_qt_tong
  cho_qt?: any | null;            // sec.cho_quyet_toan
  thieu_lich?: number | null;     // sec.thieu_lich
  giai_doan?: any;                // sec.tour_giai_doan
  sap_kh?: number | null;         // sec.sap_khoi_hanh.length
  so_ngay_kh: number;             // sec.sap_khoi_hanh_so_ngay
};

export function docDuLieuVanHanh(sec: any): DuLieuVanHanh {
  const g = (k: string) => (k in (sec || {}) ? sec[k] : undefined);
  return {
    viec: g("viec_van_hanh"), qua_han: g("qua_han_qt_tong"), cho_qt: g("cho_quyet_toan"),
    thieu_lich: g("thieu_lich"), giai_doan: g("tour_giai_doan"),
    sap_kh: Array.isArray(sec?.sap_khoi_hanh) ? sec.sap_khoi_hanh.length : undefined,
    so_ngay_kh: sec?.sap_khoi_hanh_so_ngay ?? 14,
  };
}

function soMuc(viec: any, ma: string): number | undefined {
  if (!viec) return undefined;
  if (!ma) return viec.viec;
  const m = (viec.theo_muc || []).find((x: any) => x.ma === ma);
  return m ? m.viec : 0;
}

/** `luu_dem` = bảng điều hành trả từ bộ nhớ đệm (`cached`, ≤ 5 phút). Báo ra thay vì so đồng hồ
 *  trình duyệt với giờ máy chủ — hai đồng hồ ấy không chung múi giờ nên phép so sẽ nói dối. */
export function KhoiVanHanh({ d, onThuLai, luu_dem }: {
  d: DuLieuVanHanh; onThuLai?: () => void; luu_dem?: boolean;
}) {
  const v = d.viec;
  const luc = v?.luc;
  const soCu = !!luu_dem;
  const phamVi = v ? (v.pham_vi === "toan_bo" ? "Toàn bộ" : "Theo quyền của anh/chị") : "";
  const moc = v === undefined ? "Chưa kết nối" : v === null ? "Lỗi tải"
    : `${soCu ? "Số lưu đệm · " : ""}Cập nhật ${gio(luc)} · ${phamVi}`;
  const do_ = v ? soMuc(v, "red") : v;
  const cq = d.cho_qt;
  const gd = d.giai_doan;
  const tong = v?.viec || 0;
  const thanh = (v?.theo_muc || []).filter((m: any) => m.viec > 0);

  return (
    <section className="panel vh" id="van-hanh" aria-labelledby="vh-tieu-de">
      <div className="vh-dau">
        <div><div className="vh-eb">Tổng quan</div><h2 id="vh-tieu-de">Vận hành &amp; công việc</h2>
          <div className="vh-phu">Ưu tiên cần xử lý, tình trạng tour và nguồn khách.</div></div>
        <span className={"vh-moc" + (v === null ? " cu" : "")}>{moc}</span>
      </div>

      <div className="vh-nhom"><h3>Ưu tiên cần xử lý</h3></div>
      <div className="vh-hang h2">
        <div className="vh-khoi do">
          <div className="vh-nhan">Việc nghiêm trọng</div>
          <So v={do_} dv="việc đang mở ở mức đỏ" onThuLai={onThuLai} />
          {v && tong > 0 && coSo(do_) && <div className="vh-thanh" aria-hidden="true">
            <i className="c-qh" style={{ width: `${((do_ as number) / tong) * 100}%` }} /></div>}
          {v && <>
            <div className="vh-dong qh"><span className="v">{so(do_)}</span>
              <span className="t"><b>Nghiêm trọng · mức đỏ</b>
                <small>gồm {so((v.theo_muc || []).find((m: any) => m.ma === "red")?.canh_bao)} cảnh báo</small></span></div>
            <div className="vh-dong"><span className="v">{so(v.viec)}</span>
              <span className="t"><b>Tổng việc đang mở</b></span></div>
          </>}
          <div className="vh-day"><div className="vh-cuoi">
            {v && <Link className="vh-nut" href="/?xem=viec&muc=red">Xem việc nghiêm trọng →</Link>}
          </div></div>
        </div>

        <div className="vh-khoi do">
          <div className="vh-nhan">Quyết toán</div>
          <So v={cq ? cq.tong : cq} dv="tour chưa quyết toán xong" onThuLai={onThuLai} />
          {cq && cq.tong > 0 && <div className="vh-thanh"
               role="img" aria-label={`${so(cq.qua_han)} quá hạn, ${so(cq.con_trong_han)} còn trong hạn, ${so(cq.da_dong_so)} chờ Kế toán`}>
            <i className="c-qh" style={{ width: `${(cq.qua_han / cq.tong) * 100}%` }} />
            <i className="c-ch" style={{ width: `${(cq.con_trong_han / cq.tong) * 100}%` }} />
            <i className="c-nn" style={{ width: `${(cq.chua_co_ngay_ve / cq.tong) * 100}%` }} />
            <i className="c-kt" style={{ width: `${(cq.da_dong_so / cq.tong) * 100}%` }} /></div>}
          {cq && <>
            <div className="vh-dong ch"><span className="v">{so(cq.ket_thuc)}</span>
              <span className="t"><b>Kết thúc · chờ ĐIỀU HÀNH</b></span></div>
            <div className="vh-trong">
              <div className="vh-dong qh"><span className="v">{so(cq.qua_han)}</span>
                <span className="t"><b>QUÁ HẠN</b></span></div>
              <div className="vh-dong ch"><span className="v">{so(cq.con_trong_han)}</span>
                <span className="t">Còn trong hạn</span></div>
              {cq.chua_co_ngay_ve > 0 && <div className="vh-dong qh">
                <span className="v">{so(cq.chua_co_ngay_ve)}</span>
                <span className="t"><b>Chưa có ngày về</b>
                  <small>không bao giờ hiện ở ô quá hạn — phải soát tay</small></span></div>}
            </div>
            <div className="vh-dong kt"><span className="v">{so(cq.da_dong_so)}</span>
              <span className="t"><b>Đã đóng sổ · chờ KẾ TOÁN</b></span></div>
          </>}
          <div className="vh-day">
            {cq && <div className="vh-ghi">{so(cq.da_ve_chua_dong_so)} · đã về chưa đóng sổ — không cộng vào tổng</div>}
            <div className="vh-cuoi">
              {coSo(d.qua_han) && <Link className="vh-nut" href="/?xem=qua-han">Xem tour quá hạn →</Link>}
              <Link className="vh-nut phu" href="/so-con-no">Xem quyết toán →</Link>
            </div>
          </div>
        </div>
      </div>

      <div className="vh-nhom"><h3>Hoạt động tour</h3>
        <span className="vh-phu">Theo trạng thái · các nhóm có thể giao nhau</span></div>
      <div className="vh-hang h3">
        <div className="vh-o"><div className="vh-nhan">Tour đang bán</div><So v={gd ? gd.dang_ban : gd} />
          <div className="vh-phu">Đã duyệt, chưa tới ngày đi</div>
          <Link className="vh-lk" href="/tours">Xem tour đang bán →</Link></div>
        <div className="vh-o"><div className="vh-nhan">Tour đang đi</div><So v={gd ? gd.dang_chay : gd} />
          <div className="vh-phu">Đang trong hành trình</div>
          {coSo(d.thieu_lich) && (d.thieu_lich as number) > 0 && <div className="vh-phu">
            {so(d.thieu_lich)} chuyến thiếu lịch cần rà soát — đang được tính trong số trên</div>}
          <Link className="vh-lk" href="/tours">Xem tour đang đi →</Link></div>
        <div className="vh-o"><div className="vh-nhan">Sắp khởi hành</div><So v={d.sap_kh} />
          <div className="vh-phu">{d.so_ngay_kh} ngày tới</div>
          <Link className="vh-lk" href="/tours">Xem lịch khởi hành →</Link></div>
      </div>

      <div className="vh-hang h2b">
        <div className="vh-o">
          <div className="vh-nhom"><h3>Tồn đọng công việc</h3><span className="tag">Chưa xử lý</span></div>
          <div className="vh-so">{v ? so(v.viec) : <So v={v} onThuLai={onThuLai} />}
            {v && <span className="dv">việc đang mở · gồm {so(v.canh_bao)} cảnh báo</span>}</div>
          {v && tong > 0 && <div className="vh-thanh" aria-hidden="true">
            {thanh.map((m: any) => <i key={m.ma} className={MAU_MUC[m.ma] || "c-la"}
              style={{ width: `${(m.viec / tong) * 100}%` }} />)}</div>}
          {v && <div className="vh-chu">{(v.theo_muc || []).map((m: any) => (
            <span key={m.ma}><span className={"vh-cham " + (MAU_MUC[m.ma] || "c-la")} />
              {TEN_MUC[m.ma] || m.ten} <b>{so(m.viec)}</b>
              {tong > 0 && m.viec > 0 ? ` · ${Math.round((m.viec / tong) * 100)}%` : ""}</span>))}</div>}
          {v && v.chua_anh_xa > 0 && <div className="vh-phu">
            {so(v.chua_anh_xa)} cảnh báo chưa xác định được hồ sơ — mỗi cảnh báo tính một việc. (CNTT)</div>}
          <div className="vh-chan">
            <span className="vh-phu">{v ? `Mốc dữ liệu: ${gio(luc)}` : ""}</span>
            {v ? <Link className="vh-lk" href="/?xem=viec">Xem toàn bộ công việc →</Link>
              : <Link className="vh-lk" href="/alerts">Trang cảnh báo →</Link>}
          </div>
        </div>
        <div className="vh-o">
          <div className="vh-nhom"><h3>Khách tiềm năng mới</h3><span className="tag">Chưa có nguồn</span></div>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <span className="vh-so rong">—</span>
            <div><b>Chờ cập nhật dữ liệu</b><div className="vh-phu">Bộ phận phụ trách: Marketing</div></div>
          </div>
          <div className="vh-phu">Số khách mới chưa được xác định — không thay bằng 0.</div>
          <div className="vh-chan"><span className="vh-phu">Nguồn khách hàng</span>
            <Link className="vh-lk" href="/leads?tab=leads">Cửa nhập →</Link></div>
        </div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════ HAI DANH SÁCH ═══════════════════════════════ */

function DaiCapNhat({ cu: a, moi: b, ten, lucO, lucMoi }: {
  cu?: number; moi?: number; ten: string; lucO?: string; lucMoi?: string;
}) {
  if (!coSo(a) || !coSo(b) || a === b) return null;
  return <div className="vh-dai" role="status">
    Số đã cập nhật: <b>{so(a)} → {so(b)}</b> {ten} lúc {gio(lucMoi)}
    {lucO ? <> (ô ở màn hình chính đọc lúc {gio(lucO)})</> : null}.
  </div>;
}

function PhanTrang({ trang, co, tong, chu, den }: {
  trang: number; co: number; tong: number; chu: string; den: (t: number) => string;
}) {
  const tu = tong === 0 ? 0 : (trang - 1) * co + 1;
  const toi = Math.min(trang * co, tong);
  return <div className="vh-trang">
    <span>{so(tu)}–{so(toi)} trong {so(tong)} {chu}</span>
    <span style={{ display: "flex", gap: 6 }}>
      {trang > 1 ? <Link className="vh-nut phu" href={den(trang - 1)}>‹ Trước</Link>
        : <button className="vh-nut phu" disabled>‹ Trước</button>}
      {toi < tong ? <Link className="vh-nut phu" href={den(trang + 1)}>Sau ›</Link>
        : <button className="vh-nut phu" disabled>Sau ›</button>}
    </span>
  </div>;
}

function useTai(duong: string) {
  const [kq, setKq] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [lan, setLan] = useState(0);
  useEffect(() => {
    let song = true;
    setKq(null); setLoi("");
    api(duong).then((r) => song && setKq(r)).catch((e) => song && setLoi(errMsg(e) || "Không tải được"));
    return () => { song = false; };
  }, [duong, lan]);
  return { kq, loi, thuLai: () => setLan((n) => n + 1) };
}

function TrangThai({ loi, thuLai }: { loi: string; thuLai: () => void }) {
  if (loi) return <div className="panel"><span className="vh-loi">Không tải được danh sách.</span>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <button type="button" className="act" onClick={thuLai}>Thử lại</button></div>;
  return <p className="muted">Đang tính lại…</p>;
}

/** Danh sách việc. `o` = số ô ở màn hình chính (để báo «số đã cập nhật»). */
export function DanhSachViec({ muc, trang, o }: { muc: string; trang: number; o?: any | null }) {
  const CO = 50;
  const { kq, loi, thuLai } = useTai(`/dashboard/viec?muc=${encodeURIComponent(muc)}&trang=${trang}&co=${CO}`);
  const den = (m: string, t = 1) => `/?xem=viec${m ? `&muc=${m}` : ""}${t > 1 ? `&trang=${t}` : ""}`;
  const t = kq?.tong;
  const tenMuc = muc ? `việc ${(TEN_MUC[muc] || muc).toLowerCase()}` : "việc đang mở";
  return (
    <div className="vh-ds" id="van-hanh">
      <Link className="vh-ve" href="/#van-hanh">← Về Vận hành &amp; công việc</Link>
      <div className="vh-dau">
        <div><h2>Công việc đang mở</h2>
          <div className="vh-phu">Đã gộp theo hồ sơ · {t?.pham_vi === "toan_bo" ? "toàn bộ" : "chỉ phần anh/chị được xem"}</div></div>
        {t && <span className="vh-moc">Tính lại {gio(t.luc)}</span>}
      </div>
      {!kq ? <TrangThai loi={loi} thuLai={thuLai} /> : <>
        <DaiCapNhat cu={soMuc(o, muc)} moi={soMuc(t, muc)} ten={tenMuc} lucO={o?.luc} lucMoi={t.luc} />
        <nav className="vh-chip" aria-label="Mức độ">
          {(t.theo_muc || []).map((m: any) => (
            <Link key={m.ma} href={den(m.ma)} aria-current={muc === m.ma ? "true" : undefined}>
              {TEN_MUC[m.ma] || m.ten} · {so(m.viec)}</Link>))}
          <Link href={den("")} aria-current={!muc ? "true" : undefined}>Tất cả · {so(t.viec)}</Link>
        </nav>
        <div className="vh-bang"><table>
          <thead><tr><th>Loại hồ sơ</th><th>Mã</th><th>Mức</th><th className="so">Cảnh báo</th>
            <th>Loại cảnh báo</th><th>Hạn xử lý</th><th>Phụ trách</th></tr></thead>
          <tbody>
            {kq.dong.length === 0 && <tr><td colSpan={7} className="muted">Không có việc nào ở mức này.</td></tr>}
            {kq.dong.map((r: any) => (
              <tr key={r.loai + ":" + r.ma}>
                <td>{r.loai_ten}</td><td className="vh-ma">{r.ma}</td>
                <td><span className={"vh-muc " + r.muc}>{TEN_MUC[r.muc] || r.muc}</span></td>
                <td className="so">{so(r.so_canh_bao)}</td>
                <td className="vh-loai">{(r.nhan_canh_bao || r.loai_canh_bao || []).join(" · ")}</td>
                <td className="muted">{r.han_xu_ly ? ngay(r.han_xu_ly) : "—"}</td>
                <td className={r.nguoi_phu_trach ? "" : "muted"}>{r.nguoi_phu_trach || "chưa giao"}</td>
              </tr>))}
          </tbody>
        </table></div>
        <PhanTrang trang={kq.trang} co={kq.co} tong={kq.so_dong} chu="việc · nặng trước, hạn gần trước, rồi theo mã"
          den={(n) => den(muc, n)} />
      </>}
    </div>
  );
}

/** Tour quá hạn quyết toán. `o` = số ô ở màn hình chính. */
export function DanhSachQuaHan({ trang, o, lucO }: { trang: number; o?: number | null; lucO?: string }) {
  const CO = 50;
  const { kq, loi, thuLai } = useTai(`/dashboard/qua-han-quyet-toan?trang=${trang}&co=${CO}`);
  return (
    <div className="vh-ds" id="van-hanh">
      <Link className="vh-ve" href="/#van-hanh">← Về Vận hành &amp; công việc</Link>
      <div className="vh-dau">
        <div><h2>Tour quá hạn quyết toán</h2>
          <div className="vh-phu">Chuyến đã kết thúc, quá hạn quyết toán theo tham số hạn Lẻ · Đoàn.
            Chuyến đã đóng sổ chờ Kế toán không nằm ở đây.</div></div>
        {kq && <span className="vh-moc">Tính lại {gio(kq.luc)}</span>}
      </div>
      {!kq ? <TrangThai loi={loi} thuLai={thuLai} /> : <>
        <DaiCapNhat cu={o ?? undefined} moi={kq.tong} ten="tour quá hạn" lucO={lucO} lucMoi={kq.luc} />
        <div className="vh-bang"><table>
          <thead><tr><th>Mã tour</th><th>Mảng</th><th>Kết thúc</th><th>Hạn quyết toán</th>
            <th className="so">Quá hạn</th><th>Việc tiếp</th></tr></thead>
          <tbody>
            {kq.dong.length === 0 && <tr><td colSpan={6} className="muted">Không có tour nào quá hạn quyết toán.</td></tr>}
            {kq.dong.map((r: any) => (
              <tr key={r.tour_id}>
                <td className="vh-ma"><Link href={`/tours/${r.tour_id}`}>{r.code}</Link></td>
                <td>{r.mang === "doan" ? "Đoàn" : "Lẻ"}</td>
                <td>{ngay(r.ket_thuc)}</td><td>{ngay(r.han)}</td>
                <td className="so">{so(r.qua_han_ngay)} ngày</td>
                <td className="muted">Điều hành chốt quyết toán</td>
              </tr>))}
          </tbody>
        </table></div>
        <PhanTrang trang={kq.trang} co={kq.co} tong={kq.tong} chu="tour · hạn sớm trước, rồi theo mã"
          den={(n) => `/?xem=qua-han${n > 1 ? `&trang=${n}` : ""}`} />
      </>}
    </div>
  );
}
