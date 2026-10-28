"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT, fmtD, taiTep } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** CD-1 (Chủ tịch duyệt bản xem thử 28/10/2026) — IR – PHÁP CHẾ QUẢN LÝ CỔNG CỔ ĐÔNG.
 *  · Tài liệu lên cổng CHỈ từ bản ghi công bố ĐÃ công bố ở màn IR – Pháp chế. Không có cửa thứ hai.
 *  · IR – Pháp chế đưa lên (PDF, nhóm, phạm vi); Chủ tịch, TGĐ, IR – Pháp chế gỡ ngay, có lý do.
 *  · Sự kiện: nháp → Thông báo (hiện trên cổng) → Hủy (có lý do, cổ đông đọc được).
 *  · Câu hỏi IR: trả lời phải tick «không chứa thông tin chưa công bố». */
type Tab = "tl" | "sk" | "ir" | "so" | "noi";
const TT_TL: Record<string, string> = { hien: "ok", thay_the: "", go: "red" };
const TT_SK: Record<string, string> = { nhap: "", cong_bo: "ok", huy: "red" };
const TT_IR: Record<string, string> = { cho: "warn", da_tra_loi: "ok", dong: "" };
const SK_TRONG = { id: 0, ten: "", loai: "gap_go", bat_dau: "", dia_diem: "", ngay_chot_ds: "", mo_ta: "", tai_lieu_ids: [] as number[], nhan_quan_tam: true };

function Trang() {
  const { toast } = useShell();
  const [tab, setTab] = useState<Tab>("tl");
  const [tl, setTl] = useState<any>(null);
  const [sk, setSk] = useState<any>(null);
  const [ir, setIr] = useState<any>(null);
  const [dua, setDua] = useState<any>(null);          // form đưa lên cho một bản ghi
  const [goId, setGoId] = useState<number | null>(null);
  const [lyDo, setLyDo] = useState("");
  const [f, setF] = useState<any>(null);              // form sự kiện
  const [qt, setQt] = useState<any>(null);
  const [traLoi, setTraLoi] = useState<Record<number, string>>({});
  const [xn, setXn] = useState<Record<number, boolean>>({});
  const [busy, setBusy] = useState(false);

  const taiTl = useCallback(() => api<any>("/ir-cong-co-dong/tai-lieu").then(setTl).catch((e) => toast(errMsg(e), true)), [toast]);
  const taiSk = useCallback(() => api<any>("/ir-cong-co-dong/su-kien").then(setSk).catch((e) => toast(errMsg(e), true)), [toast]);
  const taiIr = useCallback(() => api<any>("/ir-cong-co-dong/ir").then(setIr).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { taiTl(); taiSk(); taiIr(); }, [taiTl, taiSk, taiIr]);

  const chay = async (fn: () => Promise<any>, sau: (r: any) => void) => {
    setBusy(true);
    try { const r = await fn(); toast(r.message); sau(r); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const guiDua = () => {
    const fd = new FormData();
    fd.append("ban_ghi_id", String(dua.ban_ghi.id)); fd.append("tieu_de", dua.tieu_de); fd.append("nhom", dua.nhom);
    fd.append("pham_vi", dua.pham_vi); fd.append("tep", dua.tep);
    if (dua.thay_cho_id) { fd.append("thay_cho_id", dua.thay_cho_id); fd.append("ly_do_thay", dua.ly_do_thay); }
    chay(() => api<any>("/ir-cong-co-dong/tai-lieu", { method: "POST", body: fd }), (r) => { setTl(r); setDua(null); });
  };
  const guiGo = (id: number) => chay(() => api<any>(`/ir-cong-co-dong/tai-lieu/${id}/go`, { method: "POST", json: { ly_do: lyDo } }),
    (r) => { setTl(r); setGoId(null); setLyDo(""); });
  const luuSk = () => {
    const body = { ...f, ngay_chot_ds: f.ngay_chot_ds || null };
    chay(() => api<any>(f.id ? `/ir-cong-co-dong/su-kien/${f.id}` : "/ir-cong-co-dong/su-kien", { method: f.id ? "PUT" : "POST", json: body }),
      (r) => { setSk(r); setF(null); });
  };
  const doiSk = (id: number, trang_thai: string) => chay(() => api<any>(`/ir-cong-co-dong/su-kien/${id}/trang-thai`, { method: "POST", json: { trang_thai, ly_do: lyDo } }),
    (r) => { setSk(r); setLyDo(""); });
  const moQt = (s: any) => api<any>(`/ir-cong-co-dong/su-kien/${s.id}/quan-tam`).then((r) => setQt({ ...s, ds: r.quan_tam })).catch((e) => toast(errMsg(e), true));
  const guiTraLoi = (id: number) => chay(() => api<any>(`/ir-cong-co-dong/ir/${id}/tra-loi`, { method: "POST", json: { tra_loi: traLoi[id] || "", xac_nhan_da_cong_bo: !!xn[id] } }), setIr);
  const dongIr = (id: number) => chay(() => api<any>(`/ir-cong-co-dong/ir/${id}/dong`, { method: "POST", json: { ly_do: traLoi[id] || "" } }), setIr);
  const xemTep = (id: number) => taiTep(`/ir-cong-co-dong/tai-lieu/${id}/tep`, "tai-lieu.pdf").catch((e) => toast(errMsg(e), true));

  return (<>
    <h1>Cổng cổ đông</h1>
    <p className="muted">Quản lý những gì cổ đông thấy tại ir.vietourist.vn. Tài liệu chỉ lấy từ bản ghi công bố ĐÃ công bố ở màn IR – Pháp chế. Ưu đãi, cổ tức và hồ sơ sở hữu làm ở đợt sau.</p>
    <div className="tabs" style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {([["tl", "Tài liệu trên cổng"], ["sk", "Sự kiện"], ["ir", `Yêu cầu IR${ir?.so_cho ? ` (${ir.so_cho} chờ)` : ""}`], ["so", "Sổ cổ đông"], ["noi", "Nối tài khoản"]] as [Tab, string][]).map(([k, t]) =>
        <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} style={{ margin: 0 }} onClick={() => { setTab(k); if (k === "tl") taiTl(); else if (k === "sk") taiSk(); else if (k === "ir") taiIr(); }}>{t}</button>)}
    </div>

    {tab === "tl" && tl && <>
      <div className="panel wrap"><h2>Bản ghi đã công bố chưa đưa lên cổng</h2>
        {!tl.cho_dua_len.length ? <p className="muted">Không có. Ghi lần công bố ở màn IR – Pháp chế trước, rồi quay lại đây.</p> :
          <table><thead><tr><th>Nghĩa vụ</th><th>Kỳ</th><th>Đã công bố</th><th>Nơi</th><th></th></tr></thead>
            <tbody>{tl.cho_dua_len.map((b: any) => <tr key={b.id}>
              <td>{b.nghia_vu}</td><td className="mono">{b.ky}</td><td className="mono">{fmtDT(b.da_cong_bo_luc)}</td><td>{b.noi_cong_bo}</td>
              <td>{tl.duoc_dua && <button className="act teal" style={{ margin: 0 }} onClick={() => setDua({ ban_ghi: b, tieu_de: `${b.nghia_vu} ${b.ky}`, nhom: "tai_chinh", pham_vi: "cong_khai", tep: null, thay_cho_id: "", ly_do_thay: "" })}>Đưa lên cổng</button>}</td></tr>)}</tbody></table>}
      </div>

      {dua && <div className="panel" style={{ display: "grid", gap: 8 }}>
        <b>Đưa lên cổng · {dua.ban_ghi.nghia_vu} · {dua.ban_ghi.ky}</b>
        <label>Tên hiện trên cổng<input value={dua.tieu_de} onChange={(e) => setDua({ ...dua, tieu_de: e.target.value })} /></label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 8 }}>
          <label>Nhóm<select value={dua.nhom} onChange={(e) => setDua({ ...dua, nhom: e.target.value })}>
            {Object.entries(tl.nhom).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>Phạm vi<select value={dua.pham_vi} onChange={(e) => setDua({ ...dua, pham_vi: e.target.value })}>
            <option value="cong_khai">Công khai — ai cũng xem, không cần đăng nhập</option><option value="co_dong">Chỉ cổ đông đã xác minh</option></select></label>
          <label>Thay cho tài liệu đang hiện (nếu là bản đính chính)<select value={dua.thay_cho_id} onChange={(e) => setDua({ ...dua, thay_cho_id: e.target.value })}>
            <option value="">— không —</option>{tl.dang_hien.map((t: any) => <option key={t.id} value={t.id}>{t.tieu_de}</option>)}</select></label>
        </div>
        {dua.thay_cho_id && <label>Lý do thay (cổ đông đọc được)<input value={dua.ly_do_thay} onChange={(e) => setDua({ ...dua, ly_do_thay: e.target.value })} /></label>}
        <label>Tệp PDF<input type="file" accept="application/pdf,.pdf" onChange={(e) => setDua({ ...dua, tep: e.target.files?.[0] || null })} /></label>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="act teal" style={{ margin: 0 }} disabled={busy || !dua.tep || !dua.tieu_de.trim() || (!!dua.thay_cho_id && !dua.ly_do_thay.trim())} onClick={guiDua}>{busy ? "Đang đưa…" : "Đưa lên cổng"}</button>
          <button className="act grey" style={{ margin: 0 }} onClick={() => setDua(null)}>Thôi</button></div>
      </div>}

      <div className="panel wrap"><h2>Đang hiện trên cổng</h2>
        {!tl.dang_hien.length ? <p className="muted">Chưa có tài liệu nào trên cổng.</p> :
          <table><thead><tr><th>Tài liệu</th><th>Nhóm</th><th>Phạm vi</th><th>Công bố</th><th>Người đưa</th><th></th></tr></thead>
            <tbody>{tl.dang_hien.map((t: any) => <tr key={t.id}>
              <td>{t.tieu_de}{t.thay_cho_id && <div className="muted" style={{ fontSize: 12 }}>bản thay · {t.ly_do_thay}</div>}</td>
              <td>{t.nhom_ten}</td><td><Tag cls={t.pham_vi === "cong_khai" ? "ok" : "warn"}>{t.pham_vi_ten}</Tag></td>
              <td className="mono">{fmtD(t.da_cong_bo_luc)}</td><td className="muted">{t.dang_boi} · {fmtD(t.dang_luc)}</td>
              <td style={{ whiteSpace: "nowrap" }}><button className="act grey" style={{ margin: 0 }} onClick={() => xemTep(t.id)}>Tệp</button>
                {tl.duoc_go && (goId === t.id ? <span style={{ display: "inline-flex", gap: 4, marginLeft: 6 }}>
                  <input placeholder="Lý do gỡ (bắt buộc)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} style={{ width: 180 }} />
                  <button className="act red" style={{ margin: 0 }} disabled={busy || !lyDo.trim()} onClick={() => guiGo(t.id)}>Gỡ</button>
                  <button className="act grey" style={{ margin: 0 }} onClick={() => { setGoId(null); setLyDo(""); }}>Thôi</button></span>
                  : <button className="act grey" style={{ margin: "0 0 0 6px" }} onClick={() => { setGoId(t.id); setLyDo(""); }}>Gỡ khỏi cổng</button>)}</td></tr>)}</tbody></table>}
      </div>

      {tl.da_go_hoac_thay.length > 0 && <div className="panel wrap"><h2>Đã gỡ / đã có bản thay</h2>
        <table><thead><tr><th>Tài liệu</th><th>Trạng thái</th><th>Ghi chú</th></tr></thead>
          <tbody>{tl.da_go_hoac_thay.map((t: any) => <tr key={t.id}><td>{t.tieu_de}</td><td><Tag cls={TT_TL[t.trang_thai] || ""}>{t.trang_thai_ten}</Tag></td>
            <td className="muted">{t.trang_thai === "go" ? `${t.go_boi} · ${fmtDT(t.go_luc)} · ${t.ly_do_go}` : "bản mới đang hiện"}</td></tr>)}</tbody></table></div>}
    </>}

    {tab === "sk" && sk && <>
      {sk.duoc_ghi && !f && <button className="act teal" style={{ margin: "0 0 8px" }} onClick={() => setF({ ...SK_TRONG })}>Tạo sự kiện</button>}
      {f && <div className="panel" style={{ display: "grid", gap: 8 }}>
        <b>{f.id ? "Sửa sự kiện" : "Sự kiện mới (bản nháp)"}</b>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 8 }}>
          <label>Tên<input value={f.ten} onChange={(e) => setF({ ...f, ten: e.target.value })} /></label>
          <label>Loại<select value={f.loai} onChange={(e) => setF({ ...f, loai: e.target.value })}>
            {Object.entries(sk.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>Bắt đầu<input type="datetime-local" value={f.bat_dau} onChange={(e) => setF({ ...f, bat_dau: e.target.value })} /></label>
          <label>Địa điểm<input value={f.dia_diem} onChange={(e) => setF({ ...f, dia_diem: e.target.value })} /></label>
          <label>Ngày chốt danh sách (nếu có)<input type="date" value={f.ngay_chot_ds || ""} onChange={(e) => setF({ ...f, ngay_chot_ds: e.target.value })} /></label>
        </div>
        <label>Mô tả<textarea rows={3} value={f.mo_ta} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
        <div><span className="muted">Tài liệu kèm (chỉ tài liệu đang hiện trên cổng):</span>
          {!sk.tai_lieu_hien.length ? <span className="muted"> chưa có.</span> : sk.tai_lieu_hien.map((t: any) => <label key={t.id} style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={f.tai_lieu_ids.includes(t.id)}
              onChange={(e) => setF({ ...f, tai_lieu_ids: e.target.checked ? [...f.tai_lieu_ids, t.id] : f.tai_lieu_ids.filter((x: number) => x !== t.id) })} />{t.tieu_de}</label>)}</div>
        <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" style={{ width: "auto" }} checked={f.nhan_quan_tam} onChange={(e) => setF({ ...f, nhan_quan_tam: e.target.checked })} />Cho cổ đông bấm «Ghi nhận quan tâm»</label>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="act teal" style={{ margin: 0 }} disabled={busy || !f.ten.trim() || !f.bat_dau} onClick={luuSk}>Lưu</button>
          <button className="act grey" style={{ margin: 0 }} onClick={() => setF(null)}>Thôi</button></div>
      </div>}
      <div className="panel wrap"><h2>Sự kiện</h2>
        {!sk.su_kien.length ? <p className="muted">Chưa có sự kiện nào.</p> :
          <table><thead><tr><th>Sự kiện</th><th>Bắt đầu</th><th>Địa điểm</th><th>Trạng thái</th><th className="num">Quan tâm</th><th></th></tr></thead>
            <tbody>{sk.su_kien.map((s: any) => <tr key={s.id}>
              <td>{s.ten}<div className="muted" style={{ fontSize: 12 }}>{s.loai_ten}{s.ngay_chot_ds && ` · chốt DS ${fmtD(s.ngay_chot_ds)}`}</div></td>
              <td className="mono">{fmtDT(s.bat_dau)}</td><td>{s.dia_diem}</td>
              <td><Tag cls={TT_SK[s.trang_thai] || ""}>{s.trang_thai_ten}</Tag>{s.ly_do_huy && <div className="muted" style={{ fontSize: 12 }}>{s.ly_do_huy}</div>}</td>
              <td className="num"><button className="act grey" style={{ margin: 0 }} onClick={() => moQt(s)}>{s.so_quan_tam}{s.so_da_rut ? ` (+${s.so_da_rut} rút)` : ""}</button></td>
              <td style={{ whiteSpace: "nowrap" }}>{sk.duoc_ghi && s.trang_thai !== "huy" && <>
                <button className="act grey" style={{ margin: 0 }} onClick={() => setF({ ...s, bat_dau: String(s.bat_dau).slice(0, 16), ngay_chot_ds: s.ngay_chot_ds || "" })}>Sửa</button>
                {s.trang_thai === "nhap" && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => doiSk(s.id, "cong_bo")}>Thông báo</button>}
                <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy || !lyDo.trim()} title="Ghi lý do ở ô dưới bảng" onClick={() => doiSk(s.id, "huy")}>Hủy</button></>}</td></tr>)}</tbody></table>}
        {sk.duoc_ghi && sk.su_kien.length > 0 && <input style={{ marginTop: 8 }} placeholder="Lý do hủy (bắt buộc khi bấm Hủy — cổ đông đọc được)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />}
      </div>
      {qt && <div className="panel wrap"><div style={{ display: "flex", alignItems: "center", gap: 8 }}><h2 style={{ margin: 0 }}>Quan tâm · {qt.ten}</h2>
        <button className="act grey" style={{ margin: "0 0 0 auto" }} onClick={() => setQt(null)}>Đóng</button></div>
        <p className="muted">Ghi nhận quan tâm, chưa phải đăng ký tham dự. IR liên hệ để xác nhận.</p>
        {!qt.ds.length ? <p className="muted">Chưa có ai.</p> : <table><thead><tr><th>Cổ đông</th><th>Liên hệ</th><th>Lúc</th><th>Trạng thái</th></tr></thead>
          <tbody>{qt.ds.map((x: any) => <tr key={x.tai_khoan_id}><td>{x.ho_ten || "—"}</td><td className="mono">{x.lien_he}</td><td className="mono">{fmtDT(x.luc)}</td>
            <td>{x.bo_luc ? <Tag cls="">đã rút {fmtD(x.bo_luc)}</Tag> : <Tag cls="ok">quan tâm</Tag>}</td></tr>)}</tbody></table>}</div>}
    </>}

    {tab === "ir" && ir && <div className="panel wrap"><h2>Câu hỏi của cổ đông</h2>
      <p className="muted">Chỉ trả lời bằng thông tin đã công bố hoặc được phép công bố, như nhau với mọi cổ đông.</p>
      {!ir.yeu_cau.length ? <p className="muted">Chưa có câu hỏi nào.</p> :
        <table><thead><tr><th>Mã</th><th>Cổ đông</th><th>Câu hỏi</th><th>Trạng thái</th><th>Trả lời</th></tr></thead>
          <tbody>{ir.yeu_cau.map((y: any) => <tr key={y.id}>
            <td className="mono">{y.ma}<div className="muted" style={{ fontSize: 12 }}>{fmtDT(y.luc)}</div></td>
            <td>{y.ho_ten || "—"}<div className="muted mono" style={{ fontSize: 12 }}>{y.lien_he}</div></td>
            <td style={{ maxWidth: 320 }}><b>{y.chu_de_ten}</b><div style={{ whiteSpace: "pre-wrap" }}>{y.noi_dung}</div>
              {y.co_tep && <button className="act grey" style={{ margin: "4px 0 0" }} onClick={() => taiTep(`/ir-cong-co-dong/ir/${y.id}/tep`, "giay-to").catch((e) => toast(errMsg(e), true))}>Giấy tờ kèm</button>}</td>
            <td><Tag cls={TT_IR[y.trang_thai] || ""}>{y.trang_thai_ten}</Tag></td>
            <td style={{ minWidth: 260 }}>{y.trang_thai === "cho" ? (ir.duoc_ghi ? <div style={{ display: "grid", gap: 6 }}>
              <textarea rows={3} placeholder="Trả lời — hoặc lý do đóng" value={traLoi[y.id] || ""} onChange={(e) => setTraLoi({ ...traLoi, [y.id]: e.target.value })} />
              <label style={{ display: "flex", gap: 6, alignItems: "flex-start" }}><input type="checkbox" style={{ width: "auto", marginTop: 3 }} checked={!!xn[y.id]} onChange={(e) => setXn({ ...xn, [y.id]: e.target.checked })} />
                <span>Câu trả lời không chứa thông tin chưa công bố.</span></label>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="act teal" style={{ margin: 0 }} disabled={busy || !xn[y.id] || !(traLoi[y.id] || "").trim()} onClick={() => guiTraLoi(y.id)}>Gửi trả lời</button>
                <button className="act grey" style={{ margin: 0 }} disabled={busy || !(traLoi[y.id] || "").trim()} onClick={() => dongIr(y.id)}>Đóng không trả lời</button></div></div>
              : <span className="muted">Chờ IR – Pháp chế</span>)
              : <div><div style={{ whiteSpace: "pre-wrap" }}>{y.tra_loi || y.ly_do_dong}</div><div className="muted" style={{ fontSize: 12 }}>{y.tra_loi_boi} · {fmtDT(y.tra_loi_luc)}</div></div>}</td></tr>)}</tbody></table>}
    </div>}
    {tab === "so" && <SoCoDong />}
    {tab === "noi" && <NoiTaiKhoan />}
  </>);
}

/** CD-2 · SỔ CỔ ĐÔNG — IR tải danh sách người sở hữu VSD, Chủ tịch duyệt; người tải không tự duyệt.
 *  Không có ô gõ số cổ phần. Số giấy tờ là dữ liệu cá nhân — chỉ IR, Chủ tịch, TGĐ, Ban Kiểm soát xem. */
function SoCoDong() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [ngayCc, setNgayCc] = useState("");
  const [tep, setTep] = useState<File | null>(null);
  const [thu, setThu] = useState<any>(null);
  const [lyDo, setLyDo] = useState("");
  const [xem, setXem] = useState<any>(null);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const tai = useCallback(() => api<any>("/ir-cong-co-dong/so-co-dong").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { tai(); }, [tai]);
  const docThu = async () => {
    setBusy(true); setThu(null);
    try { const f = new FormData(); f.append("tep", tep as File); setThu(await api<any>("/ir-cong-co-dong/so-co-dong/doc-thu", { method: "POST", body: f })); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const gui = async () => {
    setBusy(true);
    try { const f = new FormData(); f.append("tep", tep as File); f.append("ngay_can_cu", ngayCc);
      const r = await api<any>("/ir-cong-co-dong/so-co-dong", { method: "POST", body: f }); toast(r.message); setD(r); setThu(null); setTep(null); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const xuLy = async (id: number, hanh_dong: string) => {
    try { const r = await api<any>(`/ir-cong-co-dong/so-co-dong/${id}`, { method: "POST", json: { hanh_dong, ly_do: lyDo } }); toast(r.message); setD(r); setLyDo(""); }
    catch (e) { toast(errMsg(e), true); }
  };
  const moLo = (lo: any, tim = "") => api<any>(`/ir-cong-co-dong/so-co-dong/${lo.id}/dong?q=${encodeURIComponent(tim)}`).then((r) => setXem({ ...lo, dong: r.dong })).catch((e) => toast(errMsg(e), true));
  if (!d) return <p className="muted">Đang tải…</p>;
  return (<>
    {d.duoc_nap && <div className="panel" style={{ display: "grid", gap: 8 }}><h2 style={{ margin: 0 }}>Tải danh sách người sở hữu (VSD)</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 8 }}>
        <label>Ngày chốt / ngày căn cứ<input type="date" value={ngayCc} onChange={(e) => setNgayCc(e.target.value)} /></label>
        <label>Tệp Excel / CSV<input type="file" accept=".xlsx,.csv" onChange={(e) => { setTep(e.target.files?.[0] || null); setThu(null); }} /></label></div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="act grey" style={{ margin: 0 }} disabled={busy || !tep} onClick={docThu}>Đọc thử</button>
        <button className="act teal" style={{ margin: 0 }} disabled={busy || !tep || !ngayCc || !thu} onClick={gui}>Gửi Chủ tịch duyệt</button></div>
      {thu && <div className="muted">Đọc thử: <b>{thu.so_dong.toLocaleString("vi-VN")}</b> dòng · <b>{thu.so_nguoi.toLocaleString("vi-VN")}</b> người · tổng <b>{thu.tong_cp.toLocaleString("vi-VN")}</b> cổ phần · {thu.loi.length} dòng lỗi · cột nhận ra: {Object.values(thu.cot).join(", ")}. Đọc thử chưa ghi gì.
        {thu.loi.length > 0 && <div>Lỗi: {thu.loi.slice(0, 10).map((x: any) => `dòng ${x.dong} (${x.loi})`).join("; ")}</div>}</div>}
      <div className="muted">Cần ba cột: Họ tên · Số giấy tờ (ĐKSH / CCCD / ĐKKD) · Số lượng cổ phần. Cột Tài khoản lưu ký nếu có.</div></div>}
    <div className="panel wrap"><h2>Các lô danh sách sở hữu</h2>
      {!d.lo.length ? <p className="muted">Chưa có lô nào. Cổ đông chưa thấy số cổ phần cho đến khi có lô được duyệt.</p> :
        <table><thead><tr><th>Lô</th><th>Ngày căn cứ</th><th className="num">Dòng</th><th className="num">Tổng CP</th><th>Trạng thái</th><th></th></tr></thead>
          <tbody>{d.lo.map((l: any) => <tr key={l.id}>
            <td className="mono">{l.ma}<div className="muted" style={{ fontSize: 12 }}>{l.nap_boi} · {fmtDT(l.nap_luc)}</div></td>
            <td className="mono">{fmtD(l.ngay_can_cu)}</td><td className="num mono">{l.so_dong.toLocaleString("vi-VN")}</td>
            <td className="num mono">{Number(l.tong_cp).toLocaleString("vi-VN")}</td>
            <td><Tag cls={l.trang_thai === "da_duyet" ? "ok" : l.trang_thai === "tu_choi" ? "red" : "warn"}>{l.trang_thai_ten}</Tag>{l.dang_dung && <> <Tag cls="ok">đang dùng</Tag></>}
              {l.ly_do && <div className="muted" style={{ fontSize: 12 }}>{l.ly_do}</div>}</td>
            <td style={{ whiteSpace: "nowrap" }}><button className="act grey" style={{ margin: 0 }} onClick={() => moLo(l)}>Xem</button>
              {d.duoc_duyet && l.trang_thai === "cho_duyet" && <>
                <button className="act teal" style={{ margin: "0 0 0 6px" }} onClick={() => xuLy(l.id, "duyet")}>Duyệt</button>
                <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={!lyDo.trim()} onClick={() => xuLy(l.id, "tu_choi")}>Từ chối</button></>}</td></tr>)}</tbody></table>}
      {d.duoc_duyet && d.lo.some((l: any) => l.trang_thai === "cho_duyet") && <input style={{ marginTop: 8 }} placeholder="Lý do từ chối (bắt buộc khi từ chối)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />}
      <div className="muted">Người tải không tự duyệt. Lô duyệt mới nhất là danh sách đang dùng; lô cũ giữ để tra.</div></div>
    {xem && <div className="panel wrap"><div style={{ display: "flex", gap: 8, alignItems: "center" }}><h2 style={{ margin: 0 }}>Lô {xem.ma} · {fmtD(xem.ngay_can_cu)}</h2>
      <input placeholder="Tìm tên / số giấy tờ" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && moLo(xem, q)} style={{ maxWidth: 240, marginLeft: "auto" }} />
      <button className="act grey" style={{ margin: 0 }} onClick={() => setXem(null)}>Đóng</button></div>
      <table><thead><tr><th>Họ tên</th><th>Số giấy tờ</th><th>TK lưu ký</th><th className="num">Số CP</th></tr></thead>
        <tbody>{xem.dong.map((r: any, i: number) => <tr key={i}><td>{r.ho_ten}</td><td className="mono">{r.giay_to}</td><td className="mono">{r.tk_luu_ky}</td><td className="num mono">{Number(r.so_cp).toLocaleString("vi-VN")}</td></tr>)}</tbody></table>
      <div className="muted">Hiện tối đa 200 dòng — tìm theo tên hoặc số giấy tờ để thu hẹp.</div></div>}
  </>);
}

/** CD-2 · NỐI TÀI KHOẢN — gợi ý khi số giấy tờ khớp đúng; IR bấm nối. Tên giống nhau không tự nối. */
function NoiTaiKhoan() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [tay, setTay] = useState<Record<number, string>>({});
  const tai = useCallback(() => api<any>("/ir-cong-co-dong/noi").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { tai(); }, [tai]);
  const goi = async (path: string, json: any) => {
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setD(r); } catch (e) { toast(errMsg(e), true); }
  };
  if (!d) return <p className="muted">Đang tải…</p>;
  return (<div className="panel wrap"><h2>Tài khoản cổ đông</h2>
    <p className="muted">{d.lo_hien_hanh ? `Đối chiếu với danh sách đang dùng: lô ${d.lo_hien_hanh.ma}, ngày căn cứ ${fmtD(d.lo_hien_hanh.ngay_can_cu)}.` : "Chưa có danh sách sở hữu nào được duyệt — tải ở tab Sổ cổ đông."}</p>
    {!d.tai_khoan.length ? <p className="muted">Chưa có tài khoản cổ đông nào.</p> :
      <table><thead><tr><th>Tài khoản</th><th>Giấy tờ khai</th><th>Trong danh sách</th><th></th></tr></thead>
        <tbody>{d.tai_khoan.map((t: any) => <tr key={t.tai_khoan_id}>
          <td>{t.ho_ten || "—"}<div className="muted mono" style={{ fontSize: 12 }}>{t.lien_he} · {t.trang_thai}</div></td>
          <td className="mono">{t.giay_to_khai || "—"}</td>
          <td>{t.da_noi ? (t.so_huu ? <><Tag cls="ok">đã nối</Tag> {t.so_huu.ho_ten} · {Number(t.so_huu.so_cp).toLocaleString("vi-VN")} CP</> : <><Tag cls="warn">đã nối · không có tên ở lô đang dùng</Tag></>)
            : t.goi_y ? <>{t.goi_y.ho_ten} · {Number(t.goi_y.so_cp).toLocaleString("vi-VN")} CP <Tag cls="ok">khớp số giấy tờ</Tag></>
            : <Tag cls="warn">Không tìm thấy — kiểm lại giấy tờ</Tag>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{d.duoc_noi && (t.da_noi
            ? <><input placeholder="Lý do gỡ" value={tay[t.tai_khoan_id] || ""} onChange={(e) => setTay({ ...tay, [t.tai_khoan_id]: e.target.value })} style={{ width: 140 }} />
              <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={!(tay[t.tai_khoan_id] || "").trim()} onClick={() => goi(`/ir-cong-co-dong/noi/${t.tai_khoan_id}/go`, { ly_do: tay[t.tai_khoan_id] })}>Gỡ nối</button></>
            : t.goi_y ? <button className="act teal" style={{ margin: 0 }} onClick={() => goi(`/ir-cong-co-dong/noi/${t.tai_khoan_id}`, { giay_to: t.giay_to_khai })}>Nối</button>
            : <><input placeholder="Số giấy tờ trong danh sách" value={tay[t.tai_khoan_id] || ""} onChange={(e) => setTay({ ...tay, [t.tai_khoan_id]: e.target.value })} style={{ width: 180 }} />
              <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={!(tay[t.tai_khoan_id] || "").trim()} onClick={() => goi(`/ir-cong-co-dong/noi/${t.tai_khoan_id}`, { giay_to: tay[t.tai_khoan_id] })}>Nối tay</button></>)}</td></tr>)}</tbody></table>}
    <div className="muted">Chỉ gợi ý khi số giấy tờ khớp đúng sau khi bỏ dấu cách / chấm / gạch. Nối tay vẫn phải đúng một số giấy tờ có trong danh sách. Gỡ nối phải ghi lý do.</div>
  </div>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
