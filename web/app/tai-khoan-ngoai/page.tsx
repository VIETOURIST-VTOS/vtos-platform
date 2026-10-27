"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** CG-1 (Chủ tịch duyệt 26/10/2026) — TÀI KHOẢN BÊN NGOÀI: hàng chờ duyệt hồ sơ đối tác / cổ đông gửi
 *  từ cổng kết nối VTD, và khoá / mở khoá.
 *
 *  Ai duyệt hồ sơ nào do MÁY CHỦ quyết (services/cong_ngoai.NGUOI_DUYET): NCC — TP Điều hành / GĐ KD;
 *  đại lý, CTV bán hàng — GĐ KD; cổ đông — IR – Pháp chế; Chủ tịch, TGĐ tất cả; Ban Kiểm soát chỉ xem.
 *  Nút chỉ hiện khi máy chủ nói `xu_ly_duoc` — không phải hàng rào, chỉ đỡ bấm vào cửa đóng.
 *  Bỏ trống lý do thì không trả bổ sung / từ chối / khoá được: người ngoài phải biết cần làm gì. */
const TT_TAG: Record<string, string> = { cho_duyet: "warn", bo_sung: "warn", hoat_dong: "ok", tu_choi: "red", khoa: "red", ho_so: "" };
const TABS: [string, string][] = [["cho_duyet", "Chờ duyệt"], ["bo_sung", "Cần bổ sung"], ["hoat_dong", "Đang hoạt động"], ["khoa", "Đã khoá"], ["", "Tất cả"]];

/** DT-1 (Chủ tịch duyệt 27/10/2026) — NỐI tài khoản đại lý / CTV với một đối tác bán hàng. Máy chỉ GỢI Ý
 *  (khớp MST trước, rồi SĐT; nhiều đối tác khớp thì không tự chọn); người duyệt bấm nối. Chưa nối thì
 *  cổng đối tác chỉ hiện «Đang chờ nối hồ sơ», không có số liệu. */
function NoiDoiTac({ t, xong }: { t: any; xong: () => void }) {
  const { toast } = useShell();
  const [n, setN] = useState<any>(null);
  const [q, setQ] = useState("");
  const [kq, setKq] = useState<any[] | null>(null);
  const tai = useCallback(() => { api<any>(`/tai-khoan-ngoai/${t.id}/doi-tac`).then(setN).catch((e) => toast(errMsg(e), true)); }, [t.id, toast]);
  useEffect(() => { tai(); }, [tai]);
  const lam = async (hanh_dong: string, doi_tac_id?: number) => {
    try {
      const r = await api<any>(`/tai-khoan-ngoai/${t.id}/doi-tac`, { method: "POST", json: { hanh_dong, doi_tac_id, duyet: t.trang_thai === "cho_duyet" && hanh_dong !== "go" } });
      toast(r.message); setN(r.noi); setKq(null); xong();
    } catch (e) { toast(errMsg(e), true); }
  };
  const tim = () => api<any>(`/tai-khoan-ngoai/doi-tac-ban-hang?q=${encodeURIComponent(q)}`).then((r) => setKq(r.doi_tac)).catch((e) => toast(errMsg(e), true));
  if (!n) return <div className="muted">Đang tải hồ sơ đối tác…</div>;
  if (!n.co_cong) return <div className="muted">Cổng nhà cung cấp làm ở đợt sau — không cần nối.</div>;
  const nhanNoi = t.trang_thai === "cho_duyet" ? "Duyệt & nối" : "Nối";
  return (<div style={{ border: "1px solid var(--line)", borderRadius: 8, padding: "8px 10px", display: "grid", gap: 6 }}>
    {n.doi_tac ? <div>Đã nối: <b>{n.doi_tac.ten}</b> <span className="mono">({n.doi_tac.ma})</span> · {n.doi_tac.loai_ten} · {n.doi_tac.so_booking} booking
      {t.xu_ly_duoc && <button className="act grey" style={{ margin: "0 0 0 8px" }} onClick={() => lam("go")}>Gỡ nối</button>}</div>
    : <>
      {n.goi_y.khop.length ? <div>Máy gợi ý (trùng {n.goi_y.theo}){n.goi_y.khop.length > 1 ? " — nhiều đối tác khớp, máy không tự chọn" : ""}:
        {n.goi_y.khop.map((d: any) => <div key={d.id} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 4 }}>
          <b>{d.ten}</b><span className="mono">{d.ma}</span><span className="muted">{d.loai_ten} · {d.so_booking} booking{d.con_hop_tac ? "" : " · đã dừng hợp tác"}</span>
          {t.xu_ly_duoc && d.con_hop_tac && <button className="act teal" style={{ margin: 0 }} onClick={() => lam("noi", d.id)}>{nhanNoi} {d.ten}</button>}</div>)}</div>
        : <div className="muted">Máy không tìm thấy đối tác trùng mã số thuế hay số điện thoại.</div>}
      {t.xu_ly_duoc && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nối đối tác khác: tên, mã, MST" onKeyDown={(e) => e.key === "Enter" && tim()} style={{ maxWidth: 280 }} />
        <button className="act grey" style={{ margin: 0 }} onClick={tim}>Tìm</button>
        <button className="act grey" style={{ margin: 0 }} onClick={() => lam("tao_moi")}>{t.trang_thai === "cho_duyet" ? "Duyệt & tạo" : "Tạo"} đối tác mới từ hồ sơ</button></div>}
      {kq && (kq.length ? kq.map((d: any) => <div key={d.id} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <b>{d.ten}</b><span className="mono">{d.ma}</span><span className="muted">{d.loai_ten}{d.ma_so_thue ? ` · MST ${d.ma_so_thue}` : ""}</span>
        <button className="act teal" style={{ margin: 0 }} onClick={() => lam("noi", d.id)}>{nhanNoi}</button></div>) : <div className="muted">Không tìm thấy.</div>)}
      <div className="muted">Chưa nối thì cổng đối tác chỉ hiện «Đang chờ nối hồ sơ», không có số liệu.</div></>}
  </div>);
}

function Trang() {
  const { toast } = useShell();
  const [tab, setTab] = useState("cho_duyet");
  const [d, setD] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [ly, setLy] = useState("");
  const load = useCallback(() => { api(`/tai-khoan-ngoai?trang_thai=${tab}`).then(setD).catch((e) => toast(errMsg(e), true)); }, [tab, toast]);
  useEffect(() => { load(); }, [load]);
  const lam = async (t: any, hanh_dong: string) => {
    try { const r = await api<any>(`/tai-khoan-ngoai/${t.id}`, { method: "POST", json: { hanh_dong, ly_do: ly } }); toast(r.message); setLy(""); setMo(null); load(); }
    catch (e) { toast(errMsg(e), true); }
  };
  const kenh = d?.kenh || {};
  return (<>
    <h1>Tài khoản bên ngoài</h1>
    <p className="muted">Khách hàng, đối tác và cổ đông đăng nhập ở cổng kết nối bằng mã một lần qua Zalo hoặc Email. Khách hàng dùng được ngay; đối tác và cổ đông gửi hồ sơ, được duyệt ở đây mới vào được không gian riêng. Tài khoản bên ngoài không bao giờ mở được màn hình nội bộ VTOS.</p>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))" }}>
      {Object.entries(kenh).map(([k, v]: any) => <div key={k} className="panel"><b>Kênh {v.ten}</b> {v.ok ? <Tag cls="ok">Đang mở</Tag> : <Tag cls="warn">Chưa cấu hình</Tag>}
        <div className="muted">{v.ok ? `Gửi mã tới ${v.cho === "email" ? "hộp thư" : "số điện thoại"}.` : v.ly_do}</div></div>)}
    </div>
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "10px 0" }}>
      {TABS.map(([k, l]) => <button key={k || "all"} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
    </div>
    <div className="panel wrap"><table>
      <thead><tr><th>Loại</th><th>Tên</th><th>Liên hệ</th><th>Hồ sơ gửi lúc</th><th>Người duyệt</th><th>Trạng thái</th></tr></thead>
      <tbody>{d?.dong?.length ? d.dong.map((t: any) => <>
        <tr key={t.id} style={{ cursor: "pointer" }} onClick={() => { setMo(mo === t.id ? null : t.id); setLy(""); }}>
          <td>{t.loai_ten}{t.loai_doi_tac_ten && <div className="muted">{t.loai_doi_tac_ten}</div>}</td>
          <td><b>{t.ten_don_vi || t.ho_ten || "—"}</b>{t.ten_don_vi && t.ho_ten && <div className="muted">{t.ho_ten}</div>}</td>
          <td className="mono">{t.dien_thoai || t.email}</td>
          <td className="mono">{t.gui_ho_so_luc ? fmtDT(t.gui_ho_so_luc) : "—"}</td>
          <td className="muted">{t.nguoi_duyet.join(" / ") || "Chủ tịch / TGĐ"}</td>
          <td><Tag cls={TT_TAG[t.trang_thai] || ""}>{t.trang_thai_ten}</Tag></td></tr>
        {mo === t.id && <tr key={t.id + "d"}><td colSpan={6}><div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", display: "grid", gap: 6 }}>
          {t.loai !== "khach_hang" && <div>
            {t.ma_so_thue && <span>MST <b className="mono">{t.ma_so_thue}</b> · </span>}
            {t.giay_to && <span>CCCD / MSDN <b className="mono">{t.giay_to}</b> · </span>}
            {t.tk_luu_ky && <span>TK lưu ký <b className="mono">{t.tk_luu_ky}</b> · </span>}
            {t.ghi_chu_ho_so && <div style={{ whiteSpace: "pre-wrap" }}>{t.ghi_chu_ho_so}</div>}</div>}
          {t.loai === "doi_tac" && t.trang_thai !== "tu_choi" && <NoiDoiTac t={t} xong={load} />}
          <div className="muted">Tạo {fmtDT(t.tao_luc)} · đăng nhập cuối {t.dang_nhap_cuoi ? fmtDT(t.dang_nhap_cuoi) : "—"}{t.duyet_boi && ` · duyệt bởi ${t.duyet_boi} lúc ${fmtDT(t.duyet_luc)}`}{t.ly_do && ` · lý do: ${t.ly_do}`}</div>
          {t.xu_ly_duoc ? <>
            <input value={ly} onChange={(e) => setLy(e.target.value)} placeholder="Lý do (bắt buộc khi trả bổ sung, từ chối, khoá)" />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {t.trang_thai === "cho_duyet" && <>
                <button className="act teal" style={{ margin: 0 }} onClick={() => lam(t, "duyet")}>Duyệt</button>
                <button className="act orange" style={{ margin: 0 }} disabled={!ly.trim()} onClick={() => lam(t, "bo_sung")}>Yêu cầu bổ sung</button>
                <button className="act grey" style={{ margin: 0 }} disabled={!ly.trim()} onClick={() => lam(t, "tu_choi")}>Từ chối</button></>}
              {t.trang_thai !== "khoa" && t.trang_thai !== "tu_choi" && <button className="act grey" style={{ margin: 0 }} disabled={!ly.trim()} onClick={() => lam(t, "khoa")}>Khoá</button>}
              {t.trang_thai === "khoa" && <button className="act grey" style={{ margin: 0 }} onClick={() => lam(t, "mo_khoa")}>Mở khoá</button>}
            </div></> : <div className="muted">Hồ sơ này do {t.nguoi_duyet.join(" / ") || "Chủ tịch / TGĐ"} xử lý.</div>}
        </div></td></tr>}
      </>) : <tr><td colSpan={6} className="muted">Không có tài khoản nào ở mục này.</td></tr>}</tbody></table></div>
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
