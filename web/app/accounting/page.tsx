"use client";
import { useEffect, useState, useCallback } from "react";
import DinhKem from "@/components/DinhKem";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const SRC: Record<string, string> = { thu_tien: "Thu tiền (R1)", hoa_don: "Hóa đơn", quyet_toan: "Quyết toán tour", thu_cong: "Kế toán lập", dao: "Bút toán đảo", de_nghi_chi: "Đề nghị chi (R3)", lenh_chi: "Lệnh chi", luong: "Bảng lương (R6)", ket_chuyen: "Kết chuyển 911" };
const EST: Record<string, [string, string]> = { nhap: ["Nháp", "warn"], da_ghi_so: ["Đã ghi sổ", "ok"], huy: ["Hủy", "red"] };
// ĐỢT E7 13/10/2026 — trạng thái thứ tư, MÀU VÀNG. Nó là trạng thái "KHÔNG BIẾT", không phải
// "thất bại": đã gửi sang nhà cung cấp và chưa biết tờ ấy đã ra chưa. Tờ ở trạng thái này chỉ ra
// khỏi đó qua nút "Dò lại" — màn hình cố ý KHÔNG cho phát hành lại.
const IST: Record<string, [string, string]> = { nhap: ["Nháp", "warn"], dang_phat_hanh: ["ĐANG PHÁT HÀNH", "warn"], da_phat_hanh: ["Đã phát hành", "ok"], huy: ["Hủy", "red"] };
const thisPeriod = () => new Date().toISOString().slice(0, 7);
const TABS = [["journal", "Chứng từ ghi sổ"], ["so", "Sổ kế toán"], ["invoices", "Hóa đơn điện tử"], ["bctc", "BCTC TT99"], ["fs", "BCTC rút gọn"], ["tax", "Tờ khai thuế"], ["misa", "MISA ↔ VTOS"], ["periods", "Khóa kỳ"]];
const SRC2: Record<string, string> = { misa: "Sổ MISA", so_du_dau_ky: "Số dư đầu kỳ", kiem_toan: "Điều chỉnh kiểm toán" };
const dl = (path: string, name: string) => fetch(`/api/v1${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token")}` } }).then((r) => r.blob()).then((b) => { const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = name; a.click(); });

// ── ĐỢT E6 13/10/2026 — MỞ LẠI KỲ KẾ TOÁN ĐÃ KHÓA ────────────────────────────────────────────
// Khối này nằm DƯỚI bảng khóa kỳ, trong cùng tab "Khóa kỳ": mở lại là mặt sau của chính việc
// khóa, tách sang màn hình khác thì người làm phải nhớ đi hai nơi.
const MLST: Record<string, [string, string]> = {
  cho_ky: ["Chờ Chủ tịch ký", "warn"], da_ky: ["ĐANG MỞ LẠI – chưa khóa lại", "warn"],
  tu_choi: ["Chủ tịch từ chối", "red"], da_khoa_lai: ["Đã khóa lại", "ok"],
};

function MoLaiPanel({ toast, isKTT, isKy }: { toast: (m: string, e?: boolean) => void; isKTT: boolean; isKy: boolean }) {
  const [ds, setDs] = useState<any[]>([]);
  const [ky, setKy] = useState("");
  const [lyDo, setLyDo] = useState("");
  const tai = useCallback(() => { api("/periods/mo-lai").then(setDs).catch(() => setDs([])); }, []);
  useEffect(() => { tai(); }, [tai]);
  const post = async (path: string, json?: any) => {
    try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); tai(); }
    catch (x) { toast(errMsg(x), true); }
  };
  const mo = ds.filter((d) => d.trang_thai === "da_ky");
  const cho = ds.filter((d) => d.trang_thai === "cho_ky");

  return (<div className="panel" style={{ marginTop: 12 }}>
    <h3 style={{ margin: "0 0 4px" }}>Mở lại kỳ đã khóa</h3>
    <p className="muted">Kế toán trưởng trình, Chủ tịch HĐQT ký — hai người, không phải một. Lý do
      bắt buộc tối thiểu 30 ký tự và hiện cho người ký đọc trước khi ký. Kỳ đã chốt theo bản kiểm
      toán KHÔNG mở bằng cửa này: sửa số đã được kiểm toán xác nhận đi đường bút toán điều chỉnh
      ghi vào kỳ sau.</p>

    {mo.length > 0 && <p className="muted" style={{ fontWeight: 600 }}>⚠ Đang mở lại, chưa khóa
      lại: kỳ {mo.map((d) => d.period).join(", ")} — ghi xong thì khóa lại ở bảng trên.</p>}

    {isKTT && <div style={{ display: "flex", gap: 8, alignItems: "flex-start", flexWrap: "wrap", margin: "8px 0" }}>
      <label>Kỳ <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
      <textarea rows={2} style={{ flex: 1, minWidth: 320 }} value={lyDo} placeholder="Lý do mở lại kỳ (tối thiểu 30 ký tự) — người ký đọc đúng dòng này trước khi quyết"
        onChange={(e) => setLyDo(e.target.value)} />
      <button className="act orange" style={{ margin: 0 }} disabled={!ky || lyDo.trim().length < 30}
        onClick={() => post(`/periods/${ky}/mo-lai`, { ly_do: lyDo }).then(() => setLyDo(""))}>Trình Chủ tịch HĐQT</button>
    </div>}

    {ds.length === 0 ? <p className="muted">Chưa có đề nghị mở lại kỳ nào.</p> :
      <div className="wrap"><table><thead><tr><th>Kỳ</th><th>Trạng thái</th><th>Lý do</th><th>Người trình</th><th>Người ký</th>{isKy && <th></th>}</tr></thead>
        <tbody>{ds.map((d) => <tr key={d.id} style={d.trang_thai === "da_ky" ? { fontWeight: 600 } : undefined}>
          <td><b>{d.period}</b></td>
          <td><Tag cls={(MLST[d.trang_thai] || ["", ""])[1]}>{(MLST[d.trang_thai] || [d.trang_thai])[0]}</Tag></td>
          <td className="muted">{d.trang_thai === "tu_choi" ? <>{d.ly_do}<br /><b>Từ chối:</b> {d.tu_choi_ly_do}</> : d.ly_do}</td>
          <td>{d.trinh_vai} {d.trinh_boi}<br /><span className="muted">{fmtDT(d.trinh_luc)}</span></td>
          <td>{d.ky_boi ? <>{d.ky_vai} {d.ky_boi}<br /><span className="muted">{fmtDT(d.ky_luc)}</span></> : <span className="muted">—</span>}</td>
          {isKy && <td>{d.trang_thai === "cho_ky" && <>
            <button className="act orange" style={{ margin: 0 }} onClick={() => post(`/periods/mo-lai/${d.id}/ky`)}>Ký mở lại kỳ</button>
            <button className="act grey" style={{ margin: "0 0 0 6px" }} onClick={() => { const n = prompt("Lý do từ chối — người trình cần biết sửa gì để trình lại:"); if (n) post(`/periods/mo-lai/${d.id}/tu-choi`, { ly_do: n }); }}>Từ chối</button>
          </>}</td>}
        </tr>)}</tbody></table></div>}
    {cho.length > 0 && !isKy && <p className="muted">{cho.length} đề nghị đang chờ Chủ tịch HĐQT ký.</p>}
  </div>);
}

// ══ ĐỢT E16 14/10/2026 — BỘ SỐ BCTC KIỂM TOÁN: KẾ TOÁN TẢI LÊN, CHỦ TỊCH KÝ ═══════════════════
//
// Khung 7 cũ có đúng MỘT nút và không có ô tải tệp nào: nó phát lại ba mươi con số nằm sẵn trong
// kho mã (`app/data/kiem_toan_2026h1.json`), do robot gõ, không ai ký. Khung mới đi đủ ba bước —
// tải lên → ký → chốt sổ — và ba bước ấy là BA NÚT, không gộp.
const BSKT_ST: Record<string, string> = {
  cho_ky: "Chờ Chủ tịch HĐQT ký", da_ky: "Đã ký — dùng được để chốt sổ",
  tu_choi: "Chủ tịch từ chối", da_thay_the: "Đã bị một bản sau thay thế",
};

function BoSoKiemToanPanel({ toast, isKT, isKy, onKetQua }: { toast: (m: string, e?: boolean) => void; isKT: boolean; isKy: boolean; onKetQua: (r: any) => void }) {
  const [rows, setRows] = useState<any[]>([]);
  const [dangDung, setDangDung] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const [tep, setTep] = useState<File | null>(null);
  const [replace, setReplace] = useState(false);
  const [col, setCol] = useState("close");
  const [k, setK] = useState({ as_of: "2026-06-30", ky: "H1/2026", don_vi_kiem_toan: "", so_bao_cao: "", ngay_bao_cao: "", loai_bao_cao: "soat_xet", ghi_chu: "" });
  const load = () => api("/misa/bo-so-kiem-toan").then((r: any) => { setRows(r.rows || []); setDangDung(r.dang_dung || null); }).catch(() => { });
  useEffect(() => { load(); }, []);
  const o = (t: string, v: string) => <input value={(k as any)[t]} onChange={(e) => setK({ ...k, [t]: e.target.value })} placeholder={v} />;

  const taiLen = async () => {
    if (!tep) { toast("Chọn tệp Excel trước", true); return; }
    const fd = new FormData(); fd.append("file", tep);
    Object.entries(k).forEach(([a, b]) => { if (b) fd.append(a, b); });
    setBusy("tai");
    try { const r = await api("/misa/bo-so-kiem-toan", { method: "POST", body: fd }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const bam = async (path: string, json?: any) => {
    setBusy(path);
    try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const chotSo = async () => {
    const fd = new FormData(); fd.append("column", col); fd.append("replace", String(replace));
    setBusy("chot");
    try { const r = await api("/misa/kiem-toan-checkpoint", { method: "POST", body: fd }); onKetQua(r); toast(r.message || "Xong"); } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };

  return <div className="panel"><h3>7. BCTC kiểm toán / soát xét — bộ số đã ký</h3>
    <p className="muted">Bộ số của bản BCTC đã kiểm toán hoặc soát xét — KHÁC số MISA thô, đó chính là lý do có cửa này. Chốt sổ chỉ chạy được trên một bộ số <b>đã có chữ ký Chủ tịch HĐQT</b>. Nguồn “Điều chỉnh kiểm toán” trên Chứng từ ghi sổ.</p>
    <button className="act grey" onClick={() => dl("/misa/bo-so-kiem-toan/mau.xlsx", "Mau_bo_so_BCTC_kiem_toan.xlsx")}>Tải mẫu Excel</button>
    <span className="muted"> TK · Tên · Mã đối tượng · Tên đối tượng · Dư Nợ/Có đầu kỳ · Dư Nợ/Có cuối kỳ</span>

    {isKT && <><hr /><b>Tải lên một bản mới</b>
      <div><input type="file" accept=".xlsx" onChange={(e) => setTep(e.target.files?.[0] || null)} /></div>
      <label>Ngày số liệu <input type="date" value={k.as_of} onChange={(e) => setK({ ...k, as_of: e.target.value })} /></label>{" "}
      <label>Kỳ {o("ky", "H1/2026")}</label>{" "}
      <label>Loại <select value={k.loai_bao_cao} onChange={(e) => setK({ ...k, loai_bao_cao: e.target.value })}><option value="soat_xet">Soát xét bán niên</option><option value="kiem_toan_nam">Kiểm toán BCTC năm</option></select></label><br />
      <label>Đơn vị kiểm toán {o("don_vi_kiem_toan", "Baker Tilly A&C")}</label>{" "}
      <label>Số báo cáo {o("so_bao_cao", "4.0299/26/TC-AC")}</label>{" "}
      <label>Ngày báo cáo <input type="date" value={k.ngay_bao_cao} onChange={(e) => setK({ ...k, ngay_bao_cao: e.target.value })} /></label><br />
      <button className="act orange" disabled={!!busy} onClick={taiLen}>Tải lên — chuyển Chủ tịch ký</button>
      <p className="muted">Ba ô khai nguồn là bắt buộc. Máy kiểm trước khi nhận: tổng Nợ phải bằng tổng Có ở cả hai cột, và các dòng đối tượng của một tài khoản cộng lại phải bằng đúng dòng tài khoản ấy — sai một phép là trả cả tệp, chưa ghi gì.</p></>}

    {rows.length > 0 && <><hr /><table><thead><tr><th>Ngày số liệu</th><th>Nguồn</th><th>Dòng</th><th>Trạng thái</th><th>Tải lên</th><th>Ký</th></tr></thead>
      <tbody>{rows.map((d) => <tr key={d.id} style={d.trang_thai === "da_ky" ? { fontWeight: 600 } : undefined}>
        <td className="mono">{fmtD(d.as_of)}<br /><span className="muted">{d.ky}</span></td>
        <td>{d.nguon}{d.trang_thai === "tu_choi" && d.tu_choi_ly_do ? <><br /><span className="muted"><b>Từ chối:</b> {d.tu_choi_ly_do}</span></> : null}</td>
        <td>{d.so_tai_khoan} TK{d.so_doi_tuong ? ` + ${d.so_doi_tuong} đối tượng` : ""}</td>
        <td>{BSKT_ST[d.trang_thai] || d.trang_thai}</td>
        <td className="muted">{d.tai_len_boi}<br />{fmtDT(d.tai_len_luc)}</td>
        <td>{d.trang_thai === "cho_ky" && isKy ? <>
          <button className="act orange" style={{ margin: 0 }} disabled={!!busy} onClick={() => bam(`/misa/bo-so-kiem-toan/${d.id}/ky`)}>Ký</button>
          <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={!!busy} onClick={() => { const n = prompt("Lý do từ chối — người tải lên cần biết sửa gì để tải lại:"); if (n) bam(`/misa/bo-so-kiem-toan/${d.id}/tu-choi`, { ly_do: n }); }}>Từ chối</button>
        </> : d.ky_boi ? <span className="muted">{d.ky_boi}<br />{fmtDT(d.ky_luc)}</span> : <span className="muted">—</span>}</td>
      </tr>)}</tbody></table></>}

    <hr /><b>Chốt sổ theo bộ số đã ký</b>
    {dangDung
      ? <p className="muted">Đang dùng: bộ số <b>{fmtD(dangDung.as_of)}</b> — {dangDung.nguon}. Ký bởi {dangDung.ky_boi} {fmtDT(dangDung.ky_luc)}.</p>
      : <p className="muted"><b>Chưa có bộ số nào đã ký.</b> Tải tệp lên và nhờ Chủ tịch HĐQT ký trước — trước 14/10/2026 chỗ này phát lại một bộ số nằm trong kho mã mà không ai ký, và đó là chỗ đợt này sửa.</p>}
    <label>Lấy cột <select value={col} onChange={(e) => setCol(e.target.value)}><option value="close">Cuối kỳ</option><option value="open">Đầu kỳ</option></select></label>{" "}
    <label><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> Thay thế nếu đã chốt</label><br />
    {isKT && <button className="act orange" disabled={!!busy || !dangDung} onClick={chotSo}>Chốt sổ theo BCTC kiểm toán</button>}
    <p className="muted">Ký là xác nhận <b>bộ số đúng</b>; chốt sổ là việc riêng, bấm riêng, ghi một chứng từ riêng. Gộp hai việc thì không ai lùi lại được một bước.</p>
  </div>;
}

function MisaPanel({ toast, isKT, isKy }: { toast: (m: string, e?: boolean) => void; isKT: boolean; isKy: boolean }) {
  const [stats, setStats] = useState<any>(null);
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState("");
  const [asOf, setAsOf] = useState("2026-06-30");
  const [col, setCol] = useState("close");
  const [replace, setReplace] = useState(false);
  const [range, setRange] = useState({ from: "2026-01-01", to: "2026-06-30" });
  const files = useState<Record<string, File | null>>({})[0];
  const reload = () => api("/partners/stats").then(setStats);
  useEffect(() => { reload(); }, []);
  const send = async (path: string, key: string, extra: Record<string, string> = {}, objKey?: string) => {
    const f = files[key]; if (!f) { toast("Chọn tệp Excel trước", true); return; }
    const fd = new FormData(); fd.append("file", f); if (objKey && files[objKey]) fd.append("objects", files[objKey]!);
    Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
    setBusy(path);
    try { const r = await api(path, { method: "POST", body: fd }); setRes(r); toast(r.message || "Xong"); reload(); } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const pick = (key: string) => <input type="file" accept=".xlsx" onChange={(e) => { files[key] = e.target.files?.[0] || null; }} />;
  return <>
    <p className="muted">Một cấu trúc dữ liệu với MISA (định hướng 06/9/2026): cùng số hiệu tài khoản, mã đối tượng (MST/CCCD), mã công trình = mã tour. Nạp các tệp Excel xuất từ MISA AMIS – không cần API.</p>
    {stats && <div className="panel"><b>Hiện có:</b> {stats.partners} đối tượng ({stats.customers} khách, {stats.suppliers} NCC) · {stats.projects} công trình ({stats.projects_linked} đã gắn tour) · {stats.misa_entries} chứng từ nạp từ sổ MISA · số dư đầu kỳ: {stats.opening_entries.join(", ") || "chưa nhập"}</div>}
    <div className="grid">
      <div className="panel"><h3>1. Danh mục đối tượng</h3><p className="muted">“Danh sách khách hàng”, “Danh sách nhà cung cấp” (MISA) hoặc DataNCC của Điều hành.</p>{pick("p")}{isKT && <button className="act" disabled={!!busy} onClick={() => send("/misa/partners", "p")}>Nạp</button>}</div>
      <div className="panel"><h3>2. Danh mục công trình (tour)</h3><p className="muted">“Danh sách công trình” MISA. Mã trùng mã tour VTOS → tự gắn.</p>{pick("c")}{isKT && <button className="act" disabled={!!busy} onClick={() => send("/misa/projects", "c")}>Nạp</button>}</div>
      <div className="panel"><h3>3. Số dư đầu kỳ</h3><p className="muted">“Bảng cân đối tài khoản (mẫu quản trị)” + tùy chọn “Tổng hợp công nợ theo đối tượng” để tách 131/331/1388/141 theo từng khách/NCC. Chỉ ghi tài khoản chi tiết.</p>
        Bảng cân đối: {pick("tb")}<br />Công nợ theo đối tượng: {pick("ob")}<br />
        <label>Ngày số dư <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label> <label>Lấy cột <select value={col} onChange={(e) => setCol(e.target.value)}><option value="close">Cuối kỳ</option><option value="open">Đầu kỳ</option></select></label> <label><input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} /> Thay thế số dư đã nhập</label><br />
        <button className="act grey" disabled={!!busy} onClick={() => send("/misa/trial-balance/preview", "tb")}>Xem trước</button> {isKT && <button className="act orange" disabled={!!busy} onClick={() => send("/misa/opening-balance", "tb", { as_of: asOf, column: col, replace: String(replace) }, "ob")}>Ghi số dư đầu kỳ</button>}</div>
      <div className="panel"><h3>4. Sổ nhật ký chung</h3><p className="muted">“Sổ nhật ký chung” MISA (có Mã đối tượng). Mỗi số chứng từ = một chứng từ VTOS nguồn “Sổ MISA”; đã nạp thì bỏ qua. Nên chạy “Đọc thử” trước.</p>{pick("j")}<br />
        <label>Từ <input type="date" value={range.from} onChange={(e) => setRange({ ...range, from: e.target.value })} /></label> <label>đến <input type="date" value={range.to} onChange={(e) => setRange({ ...range, to: e.target.value })} /></label><br />
        <button className="act grey" disabled={!!busy} onClick={() => send("/misa/journal", "j", { dry_run: "true", date_from: range.from, date_to: range.to })}>Đọc thử</button> {isKT && <button className="act orange" disabled={!!busy} onClick={() => send("/misa/journal", "j", { date_from: range.from, date_to: range.to })}>Nạp vào sổ</button>}</div>
      <div className="panel"><h3>5. Đối chiếu VTOS – MISA</h3><p className="muted">Nạp “Bảng cân đối tài khoản” MISA của kỳ cần so; liệt kê tài khoản lệch.</p>{pick("r")}<br /><button className="act" disabled={!!busy} onClick={() => send("/misa/reconcile", "r", { column: col })}>Đối chiếu</button></div>
      <div className="panel"><h3>6. Xuất ngược sang MISA (mẫu Import)</h3><p className="muted">Kế toán nhập vào MISA trong thời gian chạy song song.</p>
        <button className="act grey" onClick={() => dl(`/misa/export/purchases.xlsx?date_from=${range.from}&date_to=${range.to}`, "Import_MISA_MuaDichVu.xlsx")}>Mua dịch vụ (57 cột)</button>
        <button className="act grey" onClick={() => dl(`/misa/export/entries.xlsx?date_from=${range.from}&date_to=${range.to}`, "Import_MISA_ButToan.xlsx")}>Bút toán tổng hợp</button>
        <button className="act grey" onClick={() => dl(`/misa/export/projects.xlsx?date_from=${range.from}`, "Import_DanhMuc_CongTrinh.xlsx")}>Danh mục công trình</button></div>
      <BoSoKiemToanPanel toast={toast} isKT={isKT} isKy={isKy} onKetQua={setRes} />
    </div>
    {busy && <p className="muted">Đang xử lý {busy}… (sổ nhật ký lớn có thể mất vài phút)</p>}
    {res && <div className="panel wrap"><h3>Kết quả</h3>
      {res.rows && res.diff_count !== undefined ? <><p>{res.period} · {res.accounts} tài khoản · <b>{res.diff_count} lệch</b> · tổng lệch {vnd(res.diff_total)}</p><table><thead><tr><th>TK</th><th>Tên</th><th>MISA</th><th>VTOS</th><th>Lệch</th></tr></thead><tbody>{res.rows.map((r: any) => <tr key={r.account}><td className="mono">{r.account}</td><td>{r.name}</td><td style={{ textAlign: "right" }}>{vnd(r.misa)}</td><td style={{ textAlign: "right" }}>{vnd(r.vtos)}</td><td style={{ textAlign: "right", color: "var(--vtos-danger)" }}>{vnd(r.diff)}</td></tr>)}</tbody></table></>
        : res.rows ? <><p>{res.period} · {res.accounts} TK ({res.detail_accounts} chi tiết) · đầu kỳ Nợ {vnd(res.open_debit)} / Có {vnd(res.open_credit)} · cuối kỳ Nợ {vnd(res.close_debit)} / Có {vnd(res.close_credit)}</p><table><thead><tr><th>TK</th><th>Tên</th><th>ĐK Nợ</th><th>ĐK Có</th><th>CK Nợ</th><th>CK Có</th></tr></thead><tbody>{res.rows.map((r: any) => <tr key={r.code}><td className="mono">{r.code}</td><td>{r.name}</td><td style={{ textAlign: "right" }}>{vnd(r.open_d)}</td><td style={{ textAlign: "right" }}>{vnd(r.open_c)}</td><td style={{ textAlign: "right" }}>{vnd(r.close_d)}</td><td style={{ textAlign: "right" }}>{vnd(r.close_c)}</td></tr>)}</tbody></table></>
        : <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(res, null, 1)}</pre>}</div>}
  </>;
}

/** Kỳ hiệu lực của cả màn hình quyết định khoảng ngày báo cáo (B6 – Ý kiến thẩm định 06/9/2026):
 *  BCTC lũy kế từ 01/01 của năm thuộc kỳ đến ngày cuối kỳ. Kế toán có thể đổi tay, khi đó hiện cảnh báo lệch. */
function rangeOfPeriod(period: string) {
  const [y, m] = period.split("-").map(Number);
  const last = new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
  return { since: `${y}-01-01`, upto: last };
}

// ĐỢT R1 15/10/2026 — BẢN BÁO CÁO ĐÃ LẬP.
//
// Khung này đứng TRÊN bảng số, vì câu hỏi đầu tiên khi mở màn hình BCTC là "tôi đang nhìn số
// nào": số tính lại từ sổ ngay lúc này, hay số của bản Chủ tịch đã ký. Trước Đợt R1 màn hình
// chỉ có một câu trả lời và không nói ra.
//
// LẬP và KÝ là hai nút ở hai chỗ, cố ý: lập là tính, ký là chịu trách nhiệm. Gộp lại thì không
// ai lùi được một bước.
const BBC_ST: Record<string, string> = {
  nhap: "Kế toán đã lập, chưa trình", cho_ky: "Đã trình, chờ Chủ tịch ký",
  da_ky: "Chủ tịch đã ký — bản chính thức của kỳ", tu_choi: "Chủ tịch từ chối",
  da_thay_the: "Đã bị một bản lập sau thay thế",
};

function BanDaLapPanel({ toast, isKT, isKy, since, upto, onXem }: {
  toast: (m: string, e?: boolean) => void; isKT: boolean; isKy: boolean;
  since: string; upto: string; onXem: (d: any) => void;
}) {
  const [rows, setRows] = useState<any[]>([]);
  const [busy, setBusy] = useState("");
  const [k, setK] = useState({ ky: "", nguoi_dai_dien: "", ghi_chu: "" });
  const load = () => api("/reports/ban-da-lap").then((r) => setRows(r.rows || [])).catch(() => setRows([]));
  useEffect(() => { load(); }, []); // eslint-disable-line

  const lap = async () => {
    if (!k.ky.trim()) { toast("Phải đặt tên kỳ — một bản không nói được nó của kỳ nào thì không ai tìm lại được nó.", true); return; }
    setBusy("lap");
    try {
      const r = await api("/reports/ban-da-lap", { method: "POST", json: { loai: "bctc", loai_ky: "tuy_chon", ky: k.ky, tu_ngay: since, den_ngay: upto, nguoi_dai_dien: k.nguoi_dai_dien, ghi_chu: k.ghi_chu } });
      toast(r.message); load();
    } catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const bam = async (path: string, json?: any) => {
    setBusy(path);
    try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); }
    catch (x) { toast(errMsg(x), true); }
    setBusy("");
  };
  const xem = async (id: number) => {
    try { const r = await api(`/reports/ban-da-lap/${id}`); onXem(r.du_lieu); toast(`Đang xem bản đã lập kỳ ${r.ky}.`); }
    catch (x) { toast(errMsg(x), true); }
  };

  const daKy = rows.find((d) => d.trang_thai === "da_ky");
  return <div className="panel"><h3>Bản báo cáo đã lập</h3>
    <p className="muted">Bảng số bên dưới <b>tính lại từ sổ mỗi lần mở</b>, nên con số của một kỳ đã qua đổi theo sổ: một bút toán đề ngày cũ là báo cáo kỳ ấy khác đi. Một BẢN ĐÃ LẬP là lát cắt của sổ tại ngày lập, đóng băng từng chỉ tiêu, có chữ ký — và đó mới là con số đã phát hành. <b>Lập</b> là tính; <b>Ký</b> là chịu trách nhiệm; hai việc, hai nút.</p>

    {isKT && <><hr /><b>Lập một bản cho khoảng ngày đang chọn ({fmtD(since)} – {fmtD(upto)})</b>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginTop: 6 }}>
        <label>Tên kỳ <input value={k.ky} placeholder="2026-H1" onChange={(e) => setK({ ...k, ky: e.target.value })} /></label>
        <label>Người đại diện theo pháp luật <input value={k.nguoi_dai_dien} onChange={(e) => setK({ ...k, nguoi_dai_dien: e.target.value })} /></label>
        <label>Ghi chú <input value={k.ghi_chu} onChange={(e) => setK({ ...k, ghi_chu: e.target.value })} /></label>
        <button className="act orange" disabled={!!busy} onClick={lap}>Lập bản</button>
      </div>
      <p className="muted">Lập ra một bản <b>nháp</b>. Bấm “Trình” khi muốn chuyển Chủ tịch ký — người lập không tự ký được.</p></>}

    {rows.length > 0 && <><hr /><table><thead><tr><th>Kỳ</th><th>Khoảng ngày</th><th>Chỉ tiêu</th><th>Trạng thái</th><th>Lập</th><th>Ký</th><th>Việc</th></tr></thead>
      <tbody>{rows.map((d) => <tr key={d.id} style={d.trang_thai === "da_ky" ? { fontWeight: 600 } : undefined}>
        <td className="mono">{d.ky}</td>
        <td className="muted">{fmtD(d.tu_ngay)} – {fmtD(d.den_ngay)}</td>
        <td>{d.so_dong}</td>
        <td>{BBC_ST[d.trang_thai] || d.trang_thai}{d.trang_thai === "tu_choi" && d.tu_choi_ly_do ? <><br /><span className="muted"><b>Từ chối:</b> {d.tu_choi_ly_do}</span></> : null}</td>
        <td className="muted">{d.lap_boi}<br />{fmtDT(d.lap_luc)}</td>
        <td className="muted">{d.ky_boi ? <>{d.ky_boi}<br />{fmtDT(d.ky_luc)}</> : "—"}</td>
        <td>
          <button className="act grey" style={{ margin: 0 }} onClick={() => xem(d.id)}>Xem số của bản</button>
          {d.trang_thai === "nhap" && isKT && <button className="act" style={{ margin: "0 0 0 6px" }} disabled={!!busy} onClick={() => bam(`/reports/ban-da-lap/${d.id}/trinh`)}>Trình</button>}
          {d.trang_thai === "cho_ky" && isKy && <>
            <button className="act orange" style={{ margin: "0 0 0 6px" }} disabled={!!busy} onClick={() => bam(`/reports/ban-da-lap/${d.id}/ky`)}>Ký</button>
            <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={!!busy} onClick={() => { const n = prompt("Lý do từ chối — người lập cần biết sửa gì để lập lại:"); if (n) bam(`/reports/ban-da-lap/${d.id}/tu-choi`, { ly_do: n }); }}>Từ chối</button>
          </>}
        </td>
      </tr>)}</tbody></table></>}
    {!daKy && <p className="muted"><b>Chưa có bản nào đã ký.</b> Bảng số bên dưới đang là số tính lại từ sổ ngay lúc này — không phải một bản đã phát hành.</p>}
  </div>;
}

function BctcPanel({ toast, period, isKT, isKy }: { toast: (m: string, e?: boolean) => void; period: string; isKT: boolean; isKy: boolean }) {
  const def = rangeOfPeriod(period);
  const [upto, setUpto] = useState(def.upto);
  const [since, setSince] = useState(def.since);
  const [rep, setRep] = useState<any>(null);
  const load = () => api(`/reports/bctc?upto=${upto}&since=${since}`).then(setRep).catch((x) => toast(errMsg(x), true));
  useEffect(() => { const d = rangeOfPeriod(period); setSince(d.since); setUpto(d.upto); }, [period]);
  useEffect(() => { load(); }, [since, upto]); // eslint-disable-line
  const lech = since !== def.since || upto !== def.upto;
  const row = (r: any) => <tr key={r.code + r.name} style={{ fontWeight: r.group ? 700 : 400 }}><td>{r.name}</td><td className="mono">{r.code}</td><td className="muted">{r.note}</td><td style={{ textAlign: "right" }}>{r.now === null ? "" : vnd(r.now)}</td><td style={{ textAlign: "right" }}>{r.prev === null ? "" : vnd(r.prev)}</td></tr>;
  return <>
    <p className="muted">Mẫu Thông tư 99/2025 đúng cấu trúc bộ đã nộp UBCK: mỗi tài khoản chi tiết ánh xạ mã chỉ tiêu (dư Nợ / dư Có); 131, 331, 1388, 3388, 141 xét theo từng đối tượng; lãi/lỗ chưa kết chuyển cộng vào 420.</p>
    <BanDaLapPanel toast={toast} isKT={isKT} isKy={isKy} since={since} upto={upto} onXem={setRep} />
    {rep?.tu_ban && <p><Tag cls="ok">Đang xem BẢN ĐÃ LẬP kỳ {rep.ky}</Tag> <span className="muted">Số đóng băng lúc lập, ký bởi {rep.ky_boi} {fmtDT(rep.ky_luc)}. Bấm “Lập báo cáo” để quay về số tính lại từ sổ.</span></p>}
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}><label>Từ <input type="date" value={since} onChange={(e) => setSince(e.target.value)} /></label><label>đến <input type="date" value={upto} onChange={(e) => setUpto(e.target.value)} /></label><button className="act" onClick={load}>Lập báo cáo</button><button className="act grey" onClick={() => dl(`/reports/bctc.xlsx?upto=${upto}&since=${since}`, `BCTC_TT99_${upto}.xlsx`)}>Xuất Excel (bố cục UBCK)</button>{rep && (rep.balanced ? <Tag cls="ok">Cân: 280 = 440</Tag> : <Tag cls="red">LỆCH 280 ≠ 440</Tag>)}
      {lech ? <Tag cls="warn">Khoảng ngày khác kỳ {period} đang chọn ({fmtD(def.since)}–{fmtD(def.upto)})</Tag> : <Tag>Theo kỳ {period}</Tag>}
      {lech && <button className="act grey" style={{ margin: 0 }} onClick={() => { setSince(def.since); setUpto(def.upto); }}>Về đúng kỳ</button>}</div>
    {rep && <>
      <h2>Báo cáo tình hình tài chính – tại {fmtD(rep.upto)} (so với {fmtD(rep.compare_upto)})</h2>
      <div className="panel wrap"><table><thead><tr><th>Chỉ tiêu</th><th>Mã</th><th>TM</th><th>Số cuối kỳ</th><th>Số đầu năm</th></tr></thead><tbody>{rep.thtc.map(row)}</tbody></table></div>
      <h2>Báo cáo kết quả hoạt động kinh doanh – từ {fmtD(rep.since)} đến {fmtD(rep.upto)}</h2>
      <div className="panel wrap"><table><thead><tr><th>Chỉ tiêu</th><th>Mã</th><th>TM</th><th>Kỳ này</th><th>Cùng kỳ năm trước</th></tr></thead><tbody>{rep.kqkd.map(row)}</tbody></table></div>
      <p className="muted">Lãi/lỗ chưa kết chuyển tính vào 420: {vnd(rep.unposted_pl)}. Lưu chuyển tiền tệ gián tiếp và thuyết minh B09 làm ở bước tiếp theo.</p>
    </>}
  </>;
}

// ── ĐỢT R7-SO 28/10/2026 — MỘT THẺ "SỔ KẾ TOÁN", MƯỜI BA SỔ ──────────────────────────────────
// Chủ tịch chốt 24/10/2026. `/api/v1/books` đã có đủ 13 sổ và một cửa danh mục (`GET /books`)
// viết sẵn "để dựng menu Sổ kế toán giống MISA" từ Đợt R4a — nhưng CHƯA MÀN HÌNH NÀO GỌI NÓ.
// Một phân hệ không có cửa cho người dùng thì chưa phải là một phân hệ, nó là một thư viện.
//
// VÌ SAO GỘP VÀO `/accounting` CHỨ KHÔNG DỰNG MÀN HÌNH MỚI: hai thẻ "Sổ cái" và "Cân đối phát
// sinh" đang gọi `/ledger` và `/trial-balance` — hai cửa CŨ, hẹp hơn `/books`, không có TK đối
// ứng, không có Dư Nợ/Dư Có riêng, không xuất Excel, không có trần dòng. Để chúng cạnh thẻ mới
// là để hai sổ cái trên cùng một màn hình, và sớm muộn có người đối chiếu nhầm bản. Nên thẻ mới
// THAY hai thẻ cũ, không nằm cạnh.
const SO_NHOM: [string, string[]][] = [
  ["Sổ tổng hợp", ["nhat-ky-chung", "so-cai", "can-doi-tai-khoan", "chung-tu-goc"]],
  ["Sổ chi tiết", ["so-chi-tiet", "so-quy", "so-tien-gui", "nhat-ky-tien"]],
  ["Công nợ", ["cong-no", "cong-no-tong-hop", "hoa-don-thieu"]],
  ["Công trình (tour)", ["cong-trinh", "cong-trinh-tong-hop"]],
];
type Cot = [string, string, "n" | "d" | "t"];
const C = (k: string, t: string, kind: "n" | "d" | "t" = "t"): Cot => [k, t, kind];
const COT_NKC: Cot[] = [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("doc_no", "Số CT gốc"), C("description", "Diễn giải"), C("account", "TK"), C("contra", "TK đối ứng"), C("partner", "Đối tượng"), C("project_code", "Công trình"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n")];
const COT_CT: Cot[] = [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("doc_no", "Số CT gốc"), C("ngay_hoa_don", "Ngày hóa đơn", "d"), C("so_hoa_don", "Số hóa đơn"), C("description", "Diễn giải"), C("account", "TK"), C("contra", "TK đối ứng"), C("partner", "Đối tượng"), C("project_code", "Công trình"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n")];
const COT_TIEN: Cot[] = [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("doc_no", "Số CT gốc"), C("description", "Diễn giải"), C("contra", "TK đối ứng"), C("partner", "Đối tượng"), C("amount_in", "Thu", "n"), C("amount_out", "Chi", "n"), C("balance", "Tồn", "n")];
const SO_COT: Record<string, Cot[]> = {
  "nhat-ky-chung": COT_NKC,
  "so-cai": [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("description", "Diễn giải"), C("account", "TK"), C("contra", "TK đối ứng"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n"), C("balance_debit", "Dư Nợ", "n"), C("balance_credit", "Dư Có", "n")],
  "so-chi-tiet": COT_CT,
  "cong-no": COT_CT,
  "so-quy": COT_TIEN,
  "so-tien-gui": COT_TIEN,
  "nhat-ky-tien": [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("doc_no", "Số CT gốc"), C("description", "Diễn giải"), C("account", "TK tiền"), C("contra", "TK đối ứng"), C("partner", "Đối tượng"), C("project_code", "Công trình"), C("amount", "Số tiền", "n")],
  "can-doi-tai-khoan": [C("account", "TK"), C("name", "Tên tài khoản"), C("open_debit", "Dư đầu Nợ", "n"), C("open_credit", "Dư đầu Có", "n"), C("debit", "PS Nợ", "n"), C("credit", "PS Có", "n"), C("close_debit", "Dư cuối Nợ", "n"), C("close_credit", "Dư cuối Có", "n")],
  "cong-no-tong-hop": [C("partner_code", "Mã đối tượng"), C("partner", "Tên đối tượng"), C("opening", "Dư đầu", "n"), C("debit", "PS Nợ", "n"), C("credit", "PS Có", "n"), C("closing", "Dư cuối", "n")],
  "chung-tu-goc": [C("ma", "Mã loại"), C("ten", "Loại chứng từ"), C("so_chung_tu", "Số chứng từ", "n"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n"), C("tk_hay_gap", "TK hay gặp")],
  "cong-trinh": [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("description", "Diễn giải"), C("account", "TK"), C("account_name", "Tên TK"), C("contra", "TK đối ứng"), C("partner", "Đối tượng"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n")],
  "cong-trinh-tong-hop": [C("project_code", "Mã công trình"), C("revenue", "Doanh thu", "n"), C("cost", "Chi phí", "n"), C("profit", "Lãi lỗ", "n")],
  "hoa-don-thieu": [C("date", "Ngày", "d"), C("code", "Số chứng từ"), C("description", "Diễn giải"), C("account", "TK"), C("partner", "Đối tượng"), C("debit", "Phát sinh Nợ", "n"), C("credit", "Phát sinh Có", "n"), C("so_ngay", "Quá (ngày)", "n")],
};
// Sổ nào có tệp Excel — ĐO TỪ `api/v1/books.py`, không đoán. `test_r7so_5` canh hai bên khớp nhau.
const SO_XLSX = ["nhat-ky-chung", "so-cai", "so-chi-tiet", "so-quy", "so-tien-gui", "cong-no", "cong-no-tong-hop", "can-doi-tai-khoan", "nhat-ky-tien", "cong-trinh-tong-hop", "chung-tu-goc"];
// Ô nhập mỗi sổ NHẬN, và ô nào BẮT BUỘC. Cửa nào không nhận thì ô ấy xám — người dùng thấy ngay
// "sổ này không lọc theo đối tượng", thay vì gõ vào rồi tưởng đã lọc.
const SO_NHAN: Record<string, string[]> = {
  "nhat-ky-chung": [], "so-cai": ["account"], "so-chi-tiet": ["account", "partner_code", "project_code"],
  "so-quy": [], "so-tien-gui": ["partner_code"], "cong-no": ["account", "partner_code"],
  "cong-no-tong-hop": ["account"], "can-doi-tai-khoan": ["level"], "chung-tu-goc": [],
  "nhat-ky-tien": ["direction"], "cong-trinh": ["project_code"], "cong-trinh-tong-hop": [],
  "hoa-don-thieu": ["partner_code"],
};
const SO_BAT_BUOC: Record<string, string[]> = {
  "so-cai": ["account"], "so-chi-tiet": ["account"], "cong-no": ["account", "partner_code"],
  "cong-no-tong-hop": ["account"], "cong-trinh": ["project_code"],
};
const soTen = (dm: any[], k: string) => dm.find((d) => d.key === k)?.ten || k;
const soMau = (dm: any[], k: string) => dm.find((d) => d.key === k)?.mau || "";

// QUY TẮC 4 — Ô TRỐNG LÀ CHƯA CÓ SỐ, KHÔNG PHẢI SỐ KHÔNG. Mọi ô số của màn hình này đi qua
// đúng một hàm, nên không có chỗ nào lọt một `|| 0`. Bảng cân đối tài khoản là nơi quan trọng
// nhất: ô "Dư cuối Nợ" trống nghĩa là số dư KHÔNG nằm bên Nợ — viết 0 vào đó là nói sai.
const oSo = (v: any) => (v === null || v === undefined || v === 0 || v === "" ? "" : vnd(v));

function SoKeToanPanel({ toast }: { toast: (m: string, e?: boolean) => void }) {
  const [dm, setDm] = useState<any[]>([]);
  const [so, setSo] = useState("nhat-ky-chung");
  const [since, setSince] = useState(`${new Date().getFullYear()}-01-01`);
  const [upto, setUpto] = useState(new Date().toISOString().slice(0, 10));
  const [f, setF] = useState({ account: "", partner_code: "", project_code: "", direction: "thu", level: "0" });
  const [rep, setRep] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api("/books").then(setDm).catch(() => setDm([])); }, []);

  const nhan = (o: string) => (SO_NHAN[so] || []).includes(o);
  const thieu = (SO_BAT_BUOC[so] || []).filter((o) => !(f as any)[o]);
  const qs = () => {
    const p = new URLSearchParams({ since, upto });
    (SO_NHAN[so] || []).forEach((o) => { const v = (f as any)[o]; if (v !== "" && v !== undefined) p.set(o, v); });
    return p.toString();
  };
  const xem = async () => {
    setBusy(true);
    try { setRep({ ...(await api(`/books/${so}?${qs()}`)), _so: so }); }
    catch (x) { setRep(null); toast(errMsg(x), true); }
    finally { setBusy(false); }
  };
  const tai = () => dl(`/books/${so}.xlsx?${qs()}`, `${so}_${since}_${upto}.xlsx`);

  const cot = SO_COT[rep?._so] || [];
  const cong: Record<string, any> | null = (() => {
    if (!rep) return null;
    const t = rep.total;
    switch (rep._so) {
      case "nhat-ky-chung": case "cong-trinh": return { description: "TỔNG CỘNG", debit: t?.debit ?? rep.revenue, credit: t?.credit ?? rep.cost };
      case "so-cai": case "so-chi-tiet": case "cong-no":
        return { description: "Cộng phát sinh / Số dư cuối kỳ", debit: t?.debit, credit: t?.credit,
                 balance_debit: rep.closing > 0 ? rep.closing : null, balance_credit: rep.closing < 0 ? -rep.closing : null };
      case "so-quy": case "so-tien-gui":
        return { description: "Cộng phát sinh / Tồn cuối kỳ", amount_in: t?.in, amount_out: t?.out, balance: rep.closing };
      case "nhat-ky-tien": return { description: "TỔNG CỘNG", amount: rep.total };
      case "can-doi-tai-khoan": return { name: "Cộng", ...t };
      case "cong-no-tong-hop": return { partner: "Cộng", opening: t?.opening, debit: t?.debit, credit: t?.credit, closing: t?.closing };
      case "cong-trinh-tong-hop": return { project_code: "Cộng", revenue: t?.revenue, cost: t?.cost, profit: t?.profit };
      case "chung-tu-goc": return { ten: "Cộng", so_chung_tu: t?.so_chung_tu, debit: t?.debit, credit: t?.credit };
      default: return null;
    }
  })();
  const dauKy = rep && ["so-cai", "so-chi-tiet", "cong-no", "so-quy", "so-tien-gui"].includes(rep._so);

  return (<>
    <div className="panel">
      <div className="grid">
        <label>Sổ<select value={so} onChange={(e) => { setSo(e.target.value); setRep(null); }}>
          {SO_NHOM.map(([ten, ks]) => <optgroup key={ten} label={ten}>
            {ks.map((k) => <option key={k} value={k}>{soTen(dm, k)}{soMau(dm, k) ? ` (${soMau(dm, k)})` : ""}</option>)}
          </optgroup>)}
        </select></label>
        <label>Từ ngày<input type="date" value={since} onChange={(e) => setSince(e.target.value)} /></label>
        <label>Đến ngày<input type="date" value={upto} onChange={(e) => setUpto(e.target.value)} /></label>
        <label style={{ opacity: nhan("account") ? 1 : 0.45 }}>Tài khoản<input disabled={!nhan("account")} placeholder={nhan("account") ? "131" : "sổ này không lọc theo TK"} value={f.account} onChange={(e) => setF({ ...f, account: e.target.value })} /></label>
        <label style={{ opacity: nhan("partner_code") ? 1 : 0.45 }}>Mã đối tượng<input disabled={!nhan("partner_code")} placeholder={nhan("partner_code") ? "KH0001" : "sổ này không lọc theo đối tượng"} value={f.partner_code} onChange={(e) => setF({ ...f, partner_code: e.target.value })} /></label>
        <label style={{ opacity: nhan("project_code") ? 1 : 0.45 }}>Mã công trình<input disabled={!nhan("project_code")} placeholder={nhan("project_code") ? "mã tour" : "sổ này không lọc theo công trình"} value={f.project_code} onChange={(e) => setF({ ...f, project_code: e.target.value })} /></label>
        {nhan("direction") && <label>Chiều tiền<select value={f.direction} onChange={(e) => setF({ ...f, direction: e.target.value })}><option value="thu">Thu tiền (S03a1-DN)</option><option value="chi">Chi tiền (S03a2-DN)</option></select></label>}
        {nhan("level") && <label>Cấp tài khoản<select value={f.level} onChange={(e) => setF({ ...f, level: e.target.value })}><option value="0">Tất cả các cấp</option><option value="1">Cấp 1</option><option value="2">Cấp 2</option><option value="3">Cấp 3</option></select></label>}
      </div>
      <button className="act" disabled={busy || !!thieu.length} onClick={xem}>{busy ? "Đang đọc sổ…" : "Xem sổ"}</button>
      {SO_XLSX.includes(so) && <button className="act grey" disabled={busy || !!thieu.length} onClick={tai}>Tải Excel</button>}
      <button className="act grey" disabled={!rep} onClick={() => window.print()}>In</button>
      {!!thieu.length && <span className="muted" style={{ marginLeft: 8 }}>Còn thiếu: {thieu.join(", ")}</span>}
    </div>

    <p className="muted" style={{ background: "#fff8e1", border: "1px solid #ffe08a", borderRadius: 6, padding: "6px 10px" }}>
      Số dư đầu kỳ của mọi sổ ở đây tính TỪ CHỨNG TỪ ĐÃ GHI SỔ, không lấy từ bảng số dư nhập tay.
      Kỳ đầu tiên sau khi cắt chuyển từ MISA phải nạp số dư đầu kỳ ở thẻ “MISA ↔ VTOS” trước, nếu không
      cột “Dư đầu” sẽ trống — trống nghĩa là CHƯA CÓ SỐ, không phải bằng không.
    </p>

    {rep && <>
      <h2 style={{ marginBottom: 2 }}>{soTen(dm, rep._so)} {soMau(dm, rep._so) && <span className="muted">· mẫu {soMau(dm, rep._so)}</span>}</h2>
      <p className="muted" style={{ marginTop: 0 }}>Từ {fmtD(rep.since)} đến {fmtD(rep.upto)}{rep.account ? ` · TK ${rep.account} – ${rep.name || ""}` : ""}{rep.partner_code ? ` · đối tượng ${rep.partner_code}` : ""}{rep.project_code ? ` · công trình ${rep.project_code}` : ""}</p>

      {rep._so === "nhat-ky-chung" && <p>{rep.balanced ? <Tag cls="ok">Cân Nợ = Có</Tag> : <Tag cls="red">LỆCH – kiểm tra ngay</Tag>}</p>}
      {rep._so === "can-doi-tai-khoan" && <p>{rep.balanced ? <Tag cls="ok">Cân cả ba cặp cột</Tag> : <Tag cls="red">LỆCH – kiểm tra ngay</Tag>}</p>}
      {rep._so === "chung-tu-goc" && rep.so_chua_khai > 0 && <p><Tag cls="warn">{rep.so_chua_khai} chứng từ chưa khai loại</Tag></p>}
      {rep._so === "hoa-don-thieu" && rep.dem && <div className="kpis">
        <div className="kpi"><b>{rep.dem.chua_nhan}</b><span>Chưa nhận hóa đơn</span></div>
        <div className="kpi"><b>{oSo(rep.tien)}</b><span>Số tiền chưa có hóa đơn</span></div>
        <div className="kpi"><b>{rep.tuoi?.qua_60 ?? 0}</b><span>Quá 60 ngày</span></div>
        <div className="kpi"><b>{rep.cu_nhat ? fmtD(rep.cu_nhat) : "—"}</b><span>Cũ nhất</span></div>
      </div>}
      {dauKy && <div className="kpis">
        <div className="kpi"><b>{oSo(rep.opening)}</b><span>Dư đầu kỳ</span></div>
        <div className="kpi"><b>{oSo(rep.total?.debit ?? rep.total?.in)}</b><span>{rep._so === "so-quy" || rep._so === "so-tien-gui" ? "Tổng thu" : "Phát sinh Nợ"}</span></div>
        <div className="kpi"><b>{oSo(rep.total?.credit ?? rep.total?.out)}</b><span>{rep._so === "so-quy" || rep._so === "so-tien-gui" ? "Tổng chi" : "Phát sinh Có"}</span></div>
        <div className="kpi"><b>{oSo(rep.closing)}</b><span>{rep._so === "so-quy" || rep._so === "so-tien-gui" ? "Tồn cuối kỳ" : "Dư cuối kỳ"}</span></div>
      </div>}
      {rep._so === "cong-trinh" && <div className="kpis">
        <div className="kpi"><b>{oSo(rep.revenue)}</b><span>Doanh thu</span></div>
        <div className="kpi"><b>{oSo(rep.cost)}</b><span>Chi phí</span></div>
        <div className="kpi"><b>{oSo(rep.profit)}</b><span>Lãi lỗ</span></div>
      </div>}

      <div className="panel wrap"><table>
        <thead><tr>{cot.map(([k, t, kind]) => <th key={k} style={kind === "n" ? { textAlign: "right" } : undefined}>{t}</th>)}</tr></thead>
        <tbody>
          {(rep.rows || []).length ? (rep.rows as any[]).map((r, i) => <tr key={i}>
            {cot.map(([k, , kind]) => <td key={k} style={kind === "n" ? { textAlign: "right" } : undefined} className={kind === "t" && (k === "partner" || k === "account_name") ? "muted" : undefined}>
              {kind === "n" ? oSo(r[k]) : kind === "d" ? (r[k] ? fmtD(r[k]) : "") : (r[k] ?? "")}
            </td>)}
          </tr>) : <tr><td colSpan={cot.length} className="muted">Không phát sinh trong khoảng ngày này.</td></tr>}
          {cong && <tr>{cot.map(([k, , kind]) => <td key={k} style={kind === "n" ? { textAlign: "right" } : undefined}><b>{kind === "n" ? oSo(cong[k]) : (cong[k] ?? "")}</b></td>)}</tr>}
        </tbody>
      </table></div>

      {rep.truncated
        ? <p className="muted">Hiện {rep.shown_rows} trong {rep.total_rows} dòng — màn hình cắt ở {rep.limit} dòng cho nhanh. <b>Tệp Excel KHÔNG bị cắt ở mức này</b>; muốn xem đủ thì tải Excel hoặc thu hẹp khoảng ngày.</p>
        : rep.total_rows !== undefined && <p className="muted">Hiện đủ {rep.total_rows} dòng.</p>}
    </>}
  </>);
}

function Accounting() {
  const { user, toast } = useShell();
  const isKT = user?.role === "ketoan";
  // Đợt E6 13/10/2026 — hai vai KHÁC `isKT`: người TRÌNH đề nghị mở lại kỳ và người KÝ.
  // Giao diện chỉ ẨN nút; chặn thật ở `require_roles` của cửa và ở `mo_lai_ky.ky`.
  const isKTT = user?.role === "ketoan_truong" || user?.role === "cntt";
  const isKy = user?.role === "chutich" || user?.role === "cntt";
  // DOT R7-SO 28/10/2026 — `tp_dh` vao /accounting de xem hoa don cua doan, nhung `books.READ`
  // CHAN vai ay doc so. De the "So ke toan" hien ra chi tao mot nut bam vao la 403. An o day;
  // chan that van o `require_roles` cua cua.
  const xemSo = user?.role !== "tp_dh";
  const [tab, setTab] = useState("journal");
  // mở đúng tab khi vào từ menu bên trái (?tab=...)
  useEffect(() => { const q = new URLSearchParams(window.location.search).get("tab"); if (q) setTab(q); }, []);
  const [period, setPeriod] = useState(thisPeriod());
  const [accounts, setAccounts] = useState<any[]>([]);
  const [entries, setEntries] = useState<any[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [invs, setInvs] = useState<any[]>([]);
  const [tepHD, setTepHD] = useState("");   // hóa đơn đang mở tệp kèm theo
  // ĐỢT E7 13/10/2026. `maViec` GIỮ mã của lần bấm theo id hóa đơn — giữ lại mới là chỗ chống bấm
  // hai lần: lần bấm thứ hai gửi lại ĐÚNG mã ấy. `dangGui` chỉ để khoá nút cho người bấm thấy máy
  // đã nhận; nó không chặn được gì (tải lại trang là mất), và hai hàng rào thật nằm ở mã việc cộng
  // chỉ mục duy nhất (ký hiệu, số) trong cơ sở dữ liệu.
  const [maViec, setMaViec] = useState<Record<number, string>>({});
  const [dangGui, setDangGui] = useState<Record<number, boolean>>({});
  const [soNhay, setSoNhay] = useState<any[]>([]);
  const [periods, setPeriods] = useState<any[]>([]);
  const [fs, setFs] = useState<any>({});
  const [tax, setTax] = useState<any>({});
  const [bookings, setBookings] = useState<any[]>([]);
  const [lines, setLines] = useState([{ account: "642", debit: "", credit: "" }, { account: "111", debit: "", credit: "" }]);
  const [desc, setDesc] = useState("");
  // ĐỢT E14 13/10/2026 — Kế toán chọn ĐÂY LÀ BÚT TOÁN GÌ. Hai ô mốc chỉ hiện khi chọn "điều
  // chỉnh": bắt mọi bút toán khai "sửa cho kỳ nào" là bắt gõ một ô vô nghĩa 300 lần một tháng,
  // rồi lần thứ 301 có nghĩa cũng bị gõ cho xong.
  const [nvLap, setNvLap] = useState("but_toan_tay");
  const [kyGoc, setKyGoc] = useState("");
  const [ngayPH, setNgayPH] = useState("");
  const [inv, setInv] = useState({ booking_id: "", customer_tax_code: "", customer_address: "", vat_rate: "" });

  const load = useCallback(async () => {
    if (!accounts.length) api("/accounts").then(setAccounts);
    if (tab === "journal") api(`/journal?period=${period}`).then(setEntries);
    if (tab === "invoices") { api("/invoices").then(setInvs); api("/collections/summary").then((s) => setBookings(s.bookings)); api("/invoices/so-nhay").then(setSoNhay).catch(() => setSoNhay([])); }
    if (tab === "periods") api("/periods").then(setPeriods);
    if (tab === "fs") Promise.all([api(`/reports/balance-sheet?period=${period}`), api(`/reports/income-statement?period=${period}`), api(`/reports/cash-flow?period=${period}`)]).then(([bs, pl, cf]) => setFs({ bs, pl, cf }));
    if (tab === "tax") Promise.all([api(`/tax/vat?period=${period}`), api(`/tax/pit?period=${period}`)]).then(([vat, pit]) => setTax({ vat, pit }));
  }, [tab, period, accounts.length]);
  useEffect(() => { load(); }, [load]);
  const post = async (path: string, json?: any) => { try { const r = await api(path, { method: "POST", json }); toast(r.message || "Xong"); load(); return r; } catch (x) { toast(errMsg(x), true); } };
  const num = (v: string) => Number(String(v).replace(/[^\d.-]/g, "")) || 0;
  const td = lines.reduce((a, l) => a + num(l.debit), 0), tc = lines.reduce((a, l) => a + num(l.credit), 0);

  return (<>
    <h1>Kế toán TT99/2025 – robot R2 ghi sổ tự động</h1>
    <p className="muted">Bút toán sinh tự động khi Kế toán xác nhận phiếu thu (Nợ 111/112 – Có 131), phát hành hóa đơn (Nợ 131 – Có 511, 3331), xác nhận quyết toán tour (Nợ 154 – Có 331; Nợ 632 – Có 154). Chứng từ đã ghi sổ không sửa – chỉ lập bút toán đảo. Kỳ đã khóa không ghi sổ.</p>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {TABS.filter(([k]) => k !== "so" || xemSo).map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} /></label>
    </div>

    {tab === "journal" && <>
      {isKT && <div className="panel"><h2>Lập chứng từ tay</h2>
        <label>Diễn giải<input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="VD: Chi tiền điện tháng 9" /></label>
        <table><thead><tr><th>Tài khoản</th><th>Nợ</th><th>Có</th><th></th></tr></thead><tbody>
          {lines.map((l, i) => <tr key={i}>
            <td><select value={l.account} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, account: e.target.value } : x))}>{accounts.map((a) => <option key={a.code} value={a.code}>{a.code} – {a.name}</option>)}</select></td>
            <td><input value={l.debit} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, debit: e.target.value } : x))} /></td>
            <td><input value={l.credit} onChange={(e) => setLines(lines.map((x, j) => j === i ? { ...x, credit: e.target.value } : x))} /></td>
            <td>{lines.length > 2 && <button className="act grey" style={{ margin: 0 }} onClick={() => setLines(lines.filter((_, j) => j !== i))}>×</button>}</td></tr>)}
          <tr><td><b>Tổng</b></td><td><b>{vnd(td)}</b></td><td><b>{vnd(tc)}</b></td><td>{Math.abs(td - tc) >= 1 && <Tag cls="red">Chưa cân</Tag>}</td></tr>
        </tbody></table>
        <button className="act grey" onClick={() => setLines([...lines, { account: "111", debit: "", credit: "" }])}>+ dòng</button>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
          <label>Loại bút toán <select value={nvLap} onChange={(e) => { setNvLap(e.target.value); if (e.target.value === "but_toan_tay") { setKyGoc(""); setNgayPH(""); } }}>
            <option value="but_toan_tay">Bút toán Kế toán lập tay</option>
            <option value="dieu_chinh_ky_truoc">Điều chỉnh sai sót kỳ trước</option>
          </select></label>
          {nvLap === "dieu_chinh_ky_truoc" && <>
            {/* Hai ô này CHỈ hiện với bút toán điều chỉnh, và máy chủ chặn cả hai chiều: điều
                chỉnh mà thiếu thì không ghi được, nghiệp vụ thường mà điền vào cũng không ghi
                được — điền hai mốc cho một bút toán bình thường là khai nó thành bút toán sửa sai. */}
            <label title="Kỳ GỐC mà bút toán này đi sửa. Đây là một NHÃN — nó không mở kỳ đã khóa; muốn ghi thẳng vào kỳ cũ thì đi cửa mở lại kỳ, hai người ký.">
              Sửa cho kỳ <input type="month" value={kyGoc} onChange={(e) => setKyGoc(e.target.value)} /></label>
            <label title="Ngày NGƯỜI nhận ra sai sót. Kiểm toán hỏi: biết từ bao giờ, sửa sau bao lâu.">
              Phát hiện ngày <input type="date" value={ngayPH} onChange={(e) => setNgayPH(e.target.value)} /></label>
          </>}
        </div>
        <button className="act" disabled={!desc || td <= 0 || Math.abs(td - tc) >= 1} onClick={() => post("/journal", { entry_date: new Date().toISOString().slice(0, 10), description: desc, post: false, nghiep_vu: nvLap, ky_goc: kyGoc, ngay_phat_hien: ngayPH || null, lines: lines.map((l) => ({ account: l.account, debit: num(l.debit), credit: num(l.credit) })) }).then((r) => { if (r) { setDesc(""); setLines([{ account: "642", debit: "", credit: "" }, { account: "111", debit: "", credit: "" }]); } })}>Lưu nháp</button>
      </div>}
      <div className="panel wrap"><table><thead><tr><th>Số CT</th><th>Ngày</th><th>Diễn giải</th><th>Nguồn</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Trạng thái</th><th>Người ghi</th><th></th></tr></thead>
        <tbody>{entries.length ? entries.map((e) => <>
          <tr key={e.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === e.id ? null : e.id)}><td><b>{e.code}</b></td><td>{fmtD(e.entry_date)}</td><td>{e.description}</td><td className="muted">{SRC[e.source_type] || SRC2[e.source_type] || e.source_type}<div>{e.source_ref}</div></td><td style={{ textAlign: "right" }}>{vnd(e.amount)}</td>
            <td><Tag cls={EST[e.status]?.[1]}>{EST[e.status]?.[0]}</Tag>{e.reversed_by_id && <Tag cls="red">đã đảo</Tag>}</td><td className="muted">{e.posted_by || e.created_by}</td>
            <td onClick={(ev) => ev.stopPropagation()}>{isKT && e.status === "nhap" && <button className="act teal" style={{ margin: 0 }} onClick={() => post(`/journal/${e.id}/post`)}>Ghi sổ</button>}
              {isKT && e.status === "da_ghi_so" && !e.reversed_by_id && <button className="act grey" style={{ margin: 0 }} onClick={() => { const r = prompt("Lý do đảo bút toán?"); if (r) post(`/journal/${e.id}/reverse`, { reason: r }); }}>Đảo</button>}</td></tr>
          {open === e.id && <tr key={e.id + "l"}><td colSpan={8}><table style={{ margin: "4px 0 8px 24px", width: "auto" }}><tbody>{e.lines.map((l: any) => <tr key={l.id}><td className="mono">{l.account}</td><td>{accounts.find((a) => a.code === l.account)?.name}</td><td style={{ textAlign: "right" }}>{l.debit ? "Nợ " + vnd(l.debit) : ""}</td><td style={{ textAlign: "right" }}>{l.credit ? "Có " + vnd(l.credit) : ""}</td><td className="muted">{l.partner_code && <code>{l.partner_code}</code>} {l.partner} {l.project_code && <Tag cls="grey">{l.project_code}</Tag>} {l.note}</td></tr>)}</tbody></table>
            {/* Chứng từ gốc của bút toán. Quyết định "nhập là dùng luôn" (08/9/2026) đã bỏ khâu trưởng
                phòng duyệt từng dòng; tờ chứng từ đính ở đây là thứ còn lại để hậu kiểm truy ngược một
                con số về nguồn của nó. Bút toán đã ghi sổ thì CHỈ XEM – sổ đã ghi không sửa, và bộ hồ sơ
                của nó cũng không. */}
            <div style={{ margin: "0 0 8px 24px" }}>
              <DinhKem doiTuong="but_toan" doiTuongId={e.id} loai="chung_tu"
                       tieuDe={`Chứng từ gốc của ${e.code}`}
                       chiXem={e.status === "da_ghi_so"} />
            </div></td></tr>}
        </>) : <tr><td colSpan={8} className="muted">Chưa có chứng từ trong kỳ.</td></tr>}</tbody></table></div>
    </>}

    {tab === "so" && xemSo && <SoKeToanPanel toast={toast} />}

    {tab === "invoices" && <>
      {isKT && <div className="panel"><h2>Lập hóa đơn GTGT từ booking</h2><div className="grid">
        <label>Booking<select value={inv.booking_id} onChange={(e) => setInv({ ...inv, booking_id: e.target.value })}><option value="">– chọn –</option>{bookings.map((b) => <option key={b.booking_id} value={b.booking_id}>{b.code} · {b.customer_name} · {vnd(b.total)}</option>)}</select></label>
        <label>Mã số thuế người mua<input value={inv.customer_tax_code} onChange={(e) => setInv({ ...inv, customer_tax_code: e.target.value })} /></label>
        <label>Địa chỉ<input value={inv.customer_address} onChange={(e) => setInv({ ...inv, customer_address: e.target.value })} /></label>
        <label>Thuế suất (trống = tham số)<input placeholder="0.10 hoặc 0.08" value={inv.vat_rate} onChange={(e) => setInv({ ...inv, vat_rate: e.target.value })} /></label>
      </div><button className="act" disabled={!inv.booking_id} onClick={() => post("/invoices", { booking_id: Number(inv.booking_id), customer_tax_code: inv.customer_tax_code, customer_address: inv.customer_address, vat_rate: inv.vat_rate ? Number(inv.vat_rate) : null }).then((r) => r && setInv({ booking_id: "", customer_tax_code: "", customer_address: "", vat_rate: "" }))}>Lập hóa đơn nháp</button></div>}
      <div className="panel wrap"><table><thead><tr><th>Số HĐ</th><th>Ngày</th><th>Booking</th><th>Người mua</th><th style={{ textAlign: "right" }}>Chưa thuế</th><th style={{ textAlign: "right" }}>GTGT</th><th style={{ textAlign: "right" }}>Tổng</th><th>Trạng thái</th><th>Mã tra cứu</th>{isKT && <th></th>}</tr></thead>
        <tbody>{invs.length ? invs.map((i) => <tr key={i.id}><td><b>{i.no || "(nháp)"}</b></td><td>{fmtD(i.issue_date)}</td><td>{i.booking_code}<div className="muted">{i.tour_code}</div></td><td>{i.customer_name}<div className="muted">{i.customer_tax_code}</div></td><td style={{ textAlign: "right" }}>{vnd(i.pre_tax)}</td><td style={{ textAlign: "right" }}>{vnd(i.vat)} <span className="muted">({Math.round(i.vat_rate * 100)}%)</span></td><td style={{ textAlign: "right" }}><b>{vnd(i.total)}</b></td>
          <td><Tag cls={IST[i.status]?.[1]}>{IST[i.status]?.[0]}</Tag></td><td className="mono muted">{i.provider_ref}</td>
          {isKT && <td>{i.status === "nhap" && <button className="act teal" style={{ margin: 0 }} disabled={!!dangGui[i.id]}
            onClick={() => {
              // MỘT LẦN BẤM, MỘT MÃ VIỆC. Mã sinh ở đây và GIỮ LẠI theo id hóa đơn: bấm lần thứ hai
              // gửi lại ĐÚNG mã ấy, nên máy chủ trả về kết quả lần một chứ không phát hành thêm tờ
              // nào. Sinh mã mới ở mỗi lần bấm thì hai lần bấm là hai lần phát hành — đúng cái lỗi
              // đợt này đi sửa. Khoá nút chỉ để người bấm thấy máy đã nhận; chặn thật là mã việc
              // này cộng chỉ mục duy nhất ở cơ sở dữ liệu.
              const mv = maViec[i.id] || `web:${i.id}:${Date.now()}:${Math.random().toString(36).slice(2, 10)}`;
              setMaViec((m) => ({ ...m, [i.id]: mv }));
              setDangGui((m) => ({ ...m, [i.id]: true }));
              post(`/invoices/${i.id}/issue`, { ma_viec: mv }).finally(() => setDangGui((m) => ({ ...m, [i.id]: false })));
            }}>{dangGui[i.id] ? "Đang gửi…" : "Phát hành"}</button>}{i.status === "dang_phat_hanh" && <>
            <button className="act orange" style={{ margin: 0 }} onClick={() => post(`/invoices/${i.id}/do-lai`)}>Dò lại nhà cung cấp</button>
            <div className="muted" style={{ fontSize: 11.5 }}>gửi lúc {fmtDT(i.issue_sent_at)} · chưa biết kết quả</div></>}{i.status !== "huy" && <button className="act grey" style={{ margin: "0 0 0 4px" }} onClick={() => { const r = prompt("Lý do hủy hóa đơn?"); if (r) post(`/invoices/${i.id}/cancel`, { reason: r }); }}>Hủy</button>}
            {" "}<button className="act grey" style={{ margin: "0 0 0 4px" }} title="Tệp hóa đơn (PDF/XML) và chứng từ kèm" onClick={() => setTepHD(i.no || `nhap-${i.id}`)}>Tệp</button></td>}</tr>) : <tr><td colSpan={10} className="muted">Chưa có hóa đơn.</td></tr>}</tbody></table></div>
      {tepHD && <DinhKem doiTuong="hoa_don" doiTuongId={tepHD} loai="hoa_don" tieuDe={`Tệp của hóa đơn ${tepHD}`}
        goi={"Bản PDF và XML hóa đơn điện tử, biên bản điều chỉnh/hủy nếu có. Nhóm 03_Thue, giữ 10 năm " +
             "theo thời hiệu truy thu thuế."} />}
      <h3 style={{ margin: "18px 0 4px" }}>Sổ số hóa đơn</h3>
      <p className="muted">Số cuối ĐÃ CẤP của từng ký hiệu. Sổ này chỉ tăng, không bao giờ lùi: số đã
        cấp là số đã tiêu, kể cả khi tờ của nó sau đó bị hủy hoặc nhà cung cấp xác nhận chưa ra. Một
        khoảng trống trong dãy số là điều CÓ THẬT và phải nhìn thấy được — đây là nơi duy nhất trả lời
        được câu kiểm toán hỏi: số hóa đơn có liên tục không, có số nào nhảy mất không.</p>
      <div className="panel wrap"><table><thead><tr><th>Ký hiệu</th><th style={{ textAlign: "right" }}>Số cuối đã cấp</th><th style={{ textAlign: "right" }}>Đã phát hành</th><th style={{ textAlign: "right" }}>Đang phát hành</th><th style={{ textAlign: "right" }}>Đã hủy</th><th>Dãy số</th></tr></thead>
        <tbody>{soNhay.length ? soNhay.map((s) => <tr key={s.series}><td className="mono"><b>{s.series}</b></td>
          <td style={{ textAlign: "right" }}><b>{s.so_cuoi}</b></td>
          <td style={{ textAlign: "right" }}>{s.da_phat_hanh}</td>
          <td style={{ textAlign: "right" }}>{s.dang_phat_hanh || "—"}</td>
          <td style={{ textAlign: "right" }}>{s.da_huy}</td>
          <td>{s.so_thieu_tong === 0 ? <Tag cls="ok">Liên tục, không mất số</Tag>
            : <Tag cls="warn">Thiếu {s.so_thieu_tong} số: {s.so_thieu.join(", ")}{s.so_thieu_tong > s.so_thieu.length ? "…" : ""}</Tag>}</td>
        </tr>) : <tr><td colSpan={6} className="muted">Chưa cấp số hóa đơn nào.</td></tr>}</tbody></table></div>
      <p className="muted">Bản pilot cấp số nội bộ (adapter <code>noi_bo</code>). Khi ký hợp đồng nhà cung cấp HĐĐT (Viettel / VNPT / MISA meInvoice…) thay adapter gọi API, số hóa đơn và mã CQT lấy từ nhà cung cấp.</p>
    </>}

    {tab === "fs" && fs.bs && <>
      <h2>Báo cáo kết quả kinh doanh (B02-DN) – kỳ {period}</h2>
      <div className="panel wrap"><table><tbody>{fs.pl.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["20", "30", "50", "60"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table>
        <p className="muted">Quản trị: lãi vay {vnd(fs.pl.management.interest)} · khấu hao {vnd(fs.pl.management.depreciation)} · LN sau lãi vay trước khấu hao <b>{vnd(fs.pl.management.profit_after_interest_before_dep)}</b> (căn cứ thưởng GĐ KD).</p></div>
      <h2>Bảng cân đối kế toán (B01-DN) – cuối kỳ {period} {fs.bs.balanced ? <Tag cls="ok">Cân</Tag> : <Tag cls="red">LỆCH</Tag>}</h2>
      <div className="grid">
        <div className="panel wrap"><b>TÀI SẢN</b><table><tbody>{fs.bs.assets.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}<tr><td><b>Tổng tài sản</b></td><td style={{ textAlign: "right" }}><b>{vnd(fs.bs.total_assets)}</b></td></tr></tbody></table></div>
        <div className="panel wrap"><b>NGUỒN VỐN</b><table><tbody>{fs.bs.liabilities.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}{fs.bs.equity.map((r: any) => <tr key={r[0]}><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}<tr><td><b>Tổng nguồn vốn</b></td><td style={{ textAlign: "right" }}><b>{vnd(fs.bs.total_liabilities + fs.bs.total_equity)}</b></td></tr></tbody></table></div>
      </div>
      <h2>Lưu chuyển tiền tệ trực tiếp (B03-DN) {fs.cf.reconciled ? <Tag cls="ok">Khớp tiền đầu/cuối kỳ</Tag> : <Tag cls="red">Chưa khớp</Tag>}</h2>
      <div className="panel wrap"><table><tbody>{fs.cf.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["20", "30", "40", "50", "70"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table></div>
      {fs.cf.cong_thuc && <p className="muted" style={{ fontSize: 12 }}>{fs.cf.cong_thuc.ghi_chu}</p>}
      {isKT && <button className="act orange" onClick={() => post(`/reports/closing-entries/${period}`)}>Robot lập chứng từ kết chuyển 911 (nháp)</button>}
      <p className="muted">Mẫu rút gọn theo nhóm tài khoản cấp 1 từ chứng từ đã ghi sổ; số dư đầu kỳ chuyển từ MISA/BCTC kiểm toán nhập khi cắt chuyển. Kế toán trưởng đối chiếu mẫu đầy đủ TT99/2025 trước khi phát hành; hợp nhất 2 pháp nhân và công ty liên kết làm ở giai đoạn 4.</p>
    </>}

    {tab === "tax" && tax.vat && <>
      <h2>Tờ khai GTGT (01/GTGT) – kỳ {period} · {tax.vat.invoices} hóa đơn đầu ra</h2>
      <div className="panel wrap"><table><tbody>{tax.vat.rows.map((r: any) => <tr key={r[0]} style={{ fontWeight: ["[40]", "[43]"].includes(r[0]) ? 700 : 400 }}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table><p className="muted">{tax.vat.note}</p>
        {isKT && <a className="act" style={{ display: "inline-block", textDecoration: "none" }} href={`/api/v1/tax/vat/xml?period=${period}`} onClick={(e) => { e.preventDefault(); fetch(`/api/v1/tax/vat/xml?period=${period}`, { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token")}` } }).then((r) => r.blob()).then((b) => { const u = URL.createObjectURL(b); const a = document.createElement("a"); a.href = u; a.download = `01GTGT_${period}.xml`; a.click(); }); }}>Xuất XML nạp HTKK/eTax</a>}</div>
      <h2>Tờ khai TNCN (05/KK-TNCN)</h2>
      <div className="panel wrap"><table><tbody>{tax.pit.rows.map((r: any) => <tr key={r[0]}><td className="mono">{r[0]}</td><td>{r[1]}</td><td style={{ textAlign: "right" }}>{vnd(r[2])}</td></tr>)}</tbody></table><p className="muted">{tax.pit.note}</p></div>
      <p className="muted">Robot R5 chỉ lập tờ khai từ sổ và xuất XML; Kế toán trưởng kiểm tra, ký số bằng token công ty và nộp trên eTax; lưu biên nhận vào kho chứng từ. Cấu trúc XML cần đối chiếu với phiên bản HTKK hiện hành trước lần nộp đầu.</p>
    </>}

    {tab === "misa" && <MisaPanel toast={toast} isKT={isKT || user?.role === "cntt"} isKy={isKy} />}
    {tab === "bctc" && <BctcPanel toast={toast} period={period} isKT={isKT || isKTT} isKy={isKy} />}

    {tab === "periods" && <div className="panel wrap"><table><thead><tr><th>Kỳ</th><th>Trạng thái</th><th>Khóa bởi</th><th>Lúc</th><th>Ghi chú</th>{isKT && <th></th>}</tr></thead>
      <tbody>{periods.map((p) => <tr key={p.period}><td><b>{p.period}</b></td><td>{p.locked ? <Tag cls="navy">Đã khóa</Tag> : <Tag cls="ok">Mở</Tag>}</td><td>{p.locked_by}</td><td>{fmtDT(p.locked_at)}</td><td className="muted">{p.note}</td>
        {isKT && <td>{!p.locked && <button className="act orange" style={{ margin: 0 }} onClick={() => { const n = prompt(`Khóa kỳ ${p.period}? Ghi chú:`); if (n !== null) post(`/periods/${p.period}/lock`, { note: n }); }}>Khóa kỳ</button>}</td>}</tr>)}</tbody></table></div>}
    {tab === "periods" && <MoLaiPanel toast={toast} isKTT={isKTT} isKy={isKy} />}
  </>);
}
export default function Page() { return <Shell><Accounting /></Shell>; }
