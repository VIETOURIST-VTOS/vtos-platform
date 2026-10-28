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
type Tab = "tl" | "sk" | "ir";
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
      {([["tl", "Tài liệu trên cổng"], ["sk", "Sự kiện"], ["ir", `Yêu cầu IR${ir?.so_cho ? ` (${ir.so_cho} chờ)` : ""}`]] as [Tab, string][]).map(([k, t]) =>
        <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} style={{ margin: 0 }} onClick={() => { setTab(k); (k === "tl" ? taiTl : k === "sk" ? taiSk : taiIr)(); }}>{t}</button>)}
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
            <td style={{ maxWidth: 320 }}><b>{y.chu_de_ten}</b><div style={{ whiteSpace: "pre-wrap" }}>{y.noi_dung}</div></td>
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
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
