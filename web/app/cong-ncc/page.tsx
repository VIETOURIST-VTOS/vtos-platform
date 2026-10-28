"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, taiTep, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** NCC-1 (Chủ tịch duyệt bản xem thử 28/10/2026) — QUẢN LÝ CỔNG NHÀ CUNG CẤP trong VTOS.
 *  · Nối tài khoản cổng vào danh mục NCC: gợi ý theo MST (rồi SĐT); TP Điều hành / Chủ tịch / TGĐ / GĐ KD nối.
 *  · Đề xuất giá: chỉ TP Điều hành duyệt; duyệt mới sinh giá áp dụng.
 *  · Đơn NCC từ chối: Điều hành xử lý (đổi NCC / hủy ở màn Đơn dịch vụ), rồi đánh dấu đã xử lý.
 *  · Bản kê: Kế toán lập theo kỳ từ đơn đã xác nhận / đã dùng; trả lời từng dòng chênh lệch.
 *  · Đề nghị NCC: không tự thành phiếu chi. Học liệu: TP Điều hành, Marketing đưa / gỡ. */
type Tab = "noi" | "gia" | "tc" | "bk" | "dn" | "hl";
const TT: Record<string, string> = { cho: "warn", duyet: "ok", tu_choi: "red", cho_ncc: "warn", co_chenh_lech: "red", da_xac_nhan: "ok",
  moi: "warn", dang_xu_ly: "warn", xong: "ok" };

function Trang() {
  const { toast } = useShell();
  const [tab, setTab] = useState<Tab>("noi");
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState<Record<string, string>>({});
  const [tim, setTim] = useState<Record<string, any[]>>({});
  const [bk, setBk] = useState<{ ncc?: any; ky: string }>({ ky: "" });
  const [hl, setHl] = useState<any>({ tieu_de: "", nhom: "quy_trinh", danh_cho: ["ncc"], tep: null });

  const tai = useCallback(() => api<any>("/cong-ncc").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { tai(); }, [tai]);
  const chay = async (fn: () => Promise<any>, sau?: () => void) => {
    setBusy(true);
    try { const r = await fn(); toast(r.message); setD(r); sau?.(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  const goi = (path: string, json: any = {}, sau?: () => void) => chay(() => api<any>(path, { method: "POST", json }), sau);
  const timNcc = (k: string) => api<any>(`/cong-ncc/tim-ncc?q=${encodeURIComponent(q[k] || "")}`).then((r) => setTim({ ...tim, [k]: r.ncc })).catch((e) => toast(errMsg(e), true));
  const Chon = ({ k, onChon }: { k: string; onChon: (n: any) => void }) => <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
    <input placeholder="Tìm tên / mã / MST" value={q[k] || ""} onChange={(e) => setQ({ ...q, [k]: e.target.value })} style={{ width: 150 }} />
    <button className="act grey" style={{ margin: 0 }} onClick={() => timNcc(k)}>Tìm</button>
    {(tim[k] || []).map((n) => <button key={n.id} className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => onChon(n)}>{n.code} · {n.ten}</button>)}</span>;

  if (!d) return <div className="card">Đang tải…</div>;
  const Q = d.quyen;
  const so = { noi: d.tai_khoan.filter((t: any) => !t.ncc).length, gia: d.de_xuat.length, tc: d.tu_choi.length,
    bk: d.ban_ke.filter((b: any) => b.trang_thai === "co_chenh_lech").length, dn: d.de_nghi.filter((x: any) => x.trang_thai === "moi" || x.trang_thai === "dang_xu_ly").length, hl: 0 };
  const TABS: [Tab, string][] = [["noi", "Nối tài khoản"], ["gia", "Đề xuất giá"], ["tc", "Đơn bị từ chối"], ["bk", "Bản kê"], ["dn", "Đề nghị NCC"], ["hl", "Học liệu"]];

  return (<div>
    <h1 style={{ margin: "4px 0" }}>Cổng nhà cung cấp</h1>
    <div className="muted">Mọi số NCC thấy trên cổng lấy từ danh mục NCC, đơn dịch vụ và đề nghị chi trong VTOS. Cổng không có cửa nhập số thứ hai.</div>
    <div className="tabs" style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {TABS.map(([k, t]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} style={{ margin: 0 }} onClick={() => setTab(k)}>{t}{so[k] ? ` (${so[k]})` : ""}</button>)}</div>

    {tab === "noi" && <><div className="card"><h3>Tài khoản đối tác loại NCC</h3>
      {!d.tai_khoan.length ? <div className="muted">Chưa có tài khoản NCC nào đăng ký ở dt.vietourist.vn.</div>
      : <table><thead><tr><th>Tài khoản</th><th>MST khai</th><th>Đang nối</th><th>Gợi ý</th><th></th></tr></thead>
        <tbody>{d.tai_khoan.map((t: any) => <tr key={t.tai_khoan_id}>
          <td>{t.ten_don_vi || "—"}<div className="muted" style={{ fontSize: 12 }}>{t.ho_ten} · {t.lien_he} · {t.trang_thai}</div></td>
          <td>{t.ma_so_thue || "—"}</td>
          <td>{t.ncc ? <Tag cls="ok">{t.ncc.code} · {t.ncc.ten}</Tag> : <Tag cls="warn">Chưa nối</Tag>}</td>
          <td>{t.goi_y?.khop?.length ? <>{t.goi_y.khop.map((n: any) => <div key={n.id}>{n.code} · {n.ten}<span className="muted"> (khớp {t.goi_y.theo})</span>
            {Q.noi && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => goi(`/cong-ncc/noi/${t.tai_khoan_id}`, { ncc_id: n.id })}>Nối</button>}</div>)}</>
            : !t.ncc && <span className="muted">Không khớp MST / SĐT</span>}</td>
          <td>{Q.noi && (t.ncc ? <button className="act red" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/cong-ncc/noi/${t.tai_khoan_id}`, { ncc_id: null })}>Gỡ nối</button>
            : <Chon k={`tk${t.tai_khoan_id}`} onChon={(n) => goi(`/cong-ncc/noi/${t.tai_khoan_id}`, { ncc_id: n.id })} />)}</td></tr>)}</tbody></table>}
      <div className="muted">Gợi ý khi MST khai trùng MST trong danh mục NCC (bỏ dấu cách / gạch), không có thì theo SĐT. Người nối phải kiểm giấy tờ trước khi nối. Thêm NCC mới ở màn Nhà cung cấp.</div></div>
      <div className="card"><h3>Nhà hàng gắn với NCC</h3>
        {!d.nha_hang.length ? <div className="muted">Chưa có nhà hàng trong danh mục.</div>
        : <table><thead><tr><th>Nhà hàng</th><th>NCC</th><th></th></tr></thead><tbody>{d.nha_hang.map((n: any) => <tr key={n.id}>
          <td>{n.ma} · {n.ten}</td><td>{n.supplier_id ? <Tag cls="ok">NCC #{n.supplier_id}</Tag> : <Tag cls="">Chưa gắn</Tag>}</td>
          <td>{Q.noi && <Chon k={`nh${n.id}`} onChon={(x) => goi(`/cong-ncc/nha-hang/${n.id}`, { ncc_id: x.id })} />}
            {Q.noi && n.supplier_id && <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => goi(`/cong-ncc/nha-hang/${n.id}`, { ncc_id: null })}>Bỏ gắn</button>}</td></tr>)}</tbody></table>}
        <div className="muted">Gắn nhà hàng thì NCC thấy thực đơn và đơn đặt bàn của nhà hàng đó trên cổng.</div></div></>}

    {tab === "gia" && <div className="card"><h3>Đề xuất giá chờ duyệt</h3>
      {!d.de_xuat.length ? <div className="muted">Không có đề xuất chờ duyệt.</div>
      : <table><thead><tr><th>NCC · dịch vụ</th><th>Giá</th><th>Hiệu lực</th><th>Ghi chú</th><th></th></tr></thead><tbody>{d.de_xuat.map((x: any) => <tr key={x.id}>
        <td>{x.ncc}<div className="muted" style={{ fontSize: 12 }}>{x.dich_vu} {x.don_vi && `/ ${x.don_vi}`} · {x.gia_ncc_id || x.thuc_don_id ? "cập nhật" : "mới"} · {x.loai === "thuc_don" ? "thực đơn" : "giá"}</div></td>
        <td>{vnd(x.gia)}{x.gia_tre_em != null && <div className="muted" style={{ fontSize: 12 }}>trẻ em {vnd(x.gia_tre_em)}</div>}{x.so_luong_mo != null && <div className="muted" style={{ fontSize: 12 }}>mở {x.so_luong_mo}</div>}</td>
        <td>{fmtD(x.tu_ngay) || "—"} – {fmtD(x.den_ngay) || "—"}{x.ngay_khong_phuc_vu && <div className="muted" style={{ fontSize: 12 }}>không phục vụ {x.ngay_khong_phuc_vu}</div>}</td>
        <td>{x.ghi_chu}<div className="muted" style={{ fontSize: 12 }}>{fmtDT(x.luc)}</div></td>
        <td style={{ whiteSpace: "nowrap" }}>{Q.duyet_gia ? <>
          <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/cong-ncc/de-xuat/${x.id}`, { duyet: true })}>Duyệt</button>
          <input placeholder="Lý do từ chối" value={q[`dx${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`dx${x.id}`]: e.target.value })} style={{ width: 120, marginLeft: 6 }} />
          <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy || !(q[`dx${x.id}`] || "").trim()} onClick={() => goi(`/cong-ncc/de-xuat/${x.id}`, { duyet: false, ly_do: q[`dx${x.id}`] })}>Từ chối</button></>
          : <span className="muted">TP Điều hành duyệt</span>}</td></tr>)}</tbody></table>}
      <div className="muted">Duyệt thì giá áp dụng cho đơn đặt sau; đơn đã đặt giữ giá cũ.</div></div>}

    {tab === "tc" && <div className="card"><h3>Đơn NCC từ chối — chờ Điều hành xử lý</h3>
      {!d.tu_choi.length ? <div className="muted">Không có đơn bị từ chối.</div>
      : <table><thead><tr><th>Đơn</th><th>NCC</th><th>Lý do</th><th></th></tr></thead><tbody>{d.tu_choi.map((x: any) => <tr key={x.id}>
        <td>{x.don}<div className="muted" style={{ fontSize: 12 }}>{x.noi_dung} · {x.status}</div></td><td>{x.ncc}</td><td>{x.ly_do}<div className="muted" style={{ fontSize: 12 }}>{fmtDT(x.luc)}</div></td>
        <td>{Q.dieu_hanh && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/cong-ncc/tu-choi/${x.id}`)}>Đã xử lý</button>}</td></tr>)}</tbody></table>}
      <div className="muted">Đơn giữ nguyên trạng thái. Điều hành đổi NCC hoặc hủy đơn ở màn Đơn dịch vụ, rồi bấm «Đã xử lý».</div></div>}

    {tab === "bk" && <>{Q.ke_toan && <div className="card"><h3>Lập bản kê gửi NCC</h3>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        {bk.ncc ? <Tag cls="ok">{bk.ncc.code} · {bk.ncc.ten}</Tag> : <Chon k="bk" onChon={(n) => setBk({ ...bk, ncc: n })} />}
        {bk.ncc && <button className="act grey" style={{ margin: 0 }} onClick={() => setBk({ ...bk, ncc: undefined })}>Đổi</button>}
        <input type="month" value={bk.ky} onChange={(e) => setBk({ ...bk, ky: e.target.value })} />
        <button className="act teal" style={{ margin: 0 }} disabled={busy || !bk.ncc || !bk.ky} onClick={() => goi("/cong-ncc/ban-ke", { ncc_id: bk.ncc.id, ky: bk.ky }, () => setBk({ ky: "" }))}>Lập & gửi NCC</button></div>
      <div className="muted">Lấy mọi đơn đã xác nhận / đã dùng của NCC trong kỳ (theo ngày sử dụng). Bản kê đã NCC xác nhận thì khóa.</div></div>}
      <div className="card"><h3>Bản kê</h3>
        {!d.ban_ke.length ? <div className="muted">Chưa có bản kê.</div> : d.ban_ke.map((b: any) => <details key={b.id} style={{ marginBottom: 8 }} open={b.trang_thai === "co_chenh_lech"}>
          <summary>{b.ma} · {b.ncc?.ten} · kỳ {b.ky} · {vnd(b.tong)} đ <Tag cls={TT[b.trang_thai] || ""}>{b.trang_thai_ten}</Tag></summary>
          <table><thead><tr><th>Đơn</th><th>Nội dung</th><th>Giá trị</th><th>NCC báo</th><th>Trả lời</th></tr></thead><tbody>{b.dong.map((x: any) => <tr key={x.id}>
            <td>{x.ma_don}<div className="muted" style={{ fontSize: 12 }}>{fmtD(x.ngay)}</div></td><td>{x.noi_dung}</td><td>{vnd(x.gia_tri)}</td>
            <td>{x.ncc_ghi_chu ? <><Tag cls="red">{x.ncc_gia_tri != null ? vnd(x.ncc_gia_tri) : "chênh"}</Tag><div className="muted" style={{ fontSize: 12 }}>{x.ncc_ghi_chu}</div></> : "—"}</td>
            <td>{x.tra_loi || (x.ncc_ghi_chu && Q.ke_toan && <><input placeholder="Trả lời / căn cứ" value={q[`bk${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`bk${x.id}`]: e.target.value })} style={{ width: 150 }} />
              <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || !(q[`bk${x.id}`] || "").trim()} onClick={() => goi(`/cong-ncc/ban-ke/dong/${x.id}`, { tra_loi: q[`bk${x.id}`] })}>Gửi</button></>)}</td></tr>)}</tbody></table>
          <div className="muted" style={{ fontSize: 12 }}>Lập {fmtDT(b.lap_luc)} bởi {b.lap_boi}{b.xac_nhan_luc ? ` · NCC xác nhận ${fmtDT(b.xac_nhan_luc)}` : ""}</div></details>)}
        <div className="muted">Sai sau khi khóa: lập bản kê kỳ đó lần nữa sau khi xử lý đề nghị đối chiếu của NCC.</div></div></>}

    {tab === "dn" && <div className="card"><h3>Đề nghị từ NCC</h3>
      {!d.de_nghi.length ? <div className="muted">Chưa có đề nghị.</div>
      : <table><thead><tr><th>Mã · NCC</th><th>Loại · nội dung</th><th>Bộ phận</th><th>Trạng thái</th><th></th></tr></thead><tbody>{d.de_nghi.map((x: any) => {
        const duoc = x.bo_phan_ma === "ketoan" ? Q.ke_toan : Q.dieu_hanh; const mo = x.trang_thai === "moi" || x.trang_thai === "dang_xu_ly";
        return <tr key={x.id}>
          <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.ncc_code} · {x.ncc} · {fmtDT(x.luc)}</div></td>
          <td>{x.loai_ten}{x.so_tien != null && ` · ${vnd(x.so_tien)} đ`}<div className="muted" style={{ fontSize: 12 }}>{x.noi_dung}</div>
            {x.co_tep && <span className="muted" style={{ fontSize: 12 }}>Có tệp kèm (hồ sơ NCC)</span>}</td>
          <td>{x.bo_phan}</td>
          <td><Tag cls={TT[x.trang_thai] || ""}>{x.trang_thai_ten}</Tag>{x.tra_loi && <div className="muted" style={{ fontSize: 12 }}>«{x.tra_loi}» {x.xu_ly_boi}</div>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{duoc && mo && <>
            <input placeholder="Trả lời NCC" value={q[`dn${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`dn${x.id}`]: e.target.value })} style={{ width: 140 }} />
            {(["dang_xu_ly", "xong", "tu_choi"] as const).map((t) => <button key={t} className={`act ${t === "tu_choi" ? "red" : t === "xong" ? "teal" : "grey"}`} style={{ margin: "0 0 0 6px" }}
              disabled={busy || !(q[`dn${x.id}`] || "").trim()} onClick={() => goi(`/cong-ncc/de-nghi/${x.id}`, { trang_thai: t, tra_loi: q[`dn${x.id}`] })}>{t === "dang_xu_ly" ? "Đang xử lý" : t === "xong" ? "Xong" : "Từ chối"}</button>)}</>}</td></tr>; })}</tbody></table>}
      <div className="muted">Đề nghị thanh toán không tự thành phiếu chi — Kế toán lập đề nghị chi theo quy trình duyệt hiện hành.</div></div>}

    {tab === "hl" && <>{Q.hoc_lieu && <div className="card"><h3>Đưa học liệu lên</h3>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <input placeholder="Tiêu đề" value={hl.tieu_de} onChange={(e) => setHl({ ...hl, tieu_de: e.target.value })} style={{ width: 220 }} />
        <select value={hl.nhom} onChange={(e) => setHl({ ...hl, nhom: e.target.value })}>{Object.entries(d.nhom_hoc_lieu).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select>
        {Object.entries(d.danh_cho).map(([k, v]: any) => <label key={k} style={{ display: "inline-flex", gap: 4 }}><input type="checkbox" checked={hl.danh_cho.includes(k)}
          onChange={(e) => setHl({ ...hl, danh_cho: e.target.checked ? [...hl.danh_cho, k] : hl.danh_cho.filter((x: string) => x !== k) })} />{v}</label>)}
        <input type="file" accept=".pdf,image/*" onChange={(e) => setHl({ ...hl, tep: e.target.files?.[0] || null })} />
        <button className="act teal" style={{ margin: 0 }} disabled={busy || !hl.tieu_de.trim() || !hl.tep || !hl.danh_cho.length} onClick={() => {
          const fd = new FormData(); fd.append("tieu_de", hl.tieu_de); fd.append("nhom", hl.nhom); fd.append("danh_cho", hl.danh_cho.join(",")); fd.append("tep", hl.tep);
          chay(() => api<any>("/cong-ncc/hoc-lieu", { method: "POST", body: fd }), () => setHl({ tieu_de: "", nhom: "quy_trinh", danh_cho: ["ncc"], tep: null }));
        }}>Đưa lên</button></div></div>}
      <div className="card"><h3>Học liệu</h3>
        {!d.hoc_lieu.length ? <div className="muted">Chưa có học liệu.</div>
        : <table><thead><tr><th>Tiêu đề</th><th>Nhóm</th><th>Dành cho</th><th>Trạng thái</th><th></th></tr></thead><tbody>{d.hoc_lieu.map((h: any) => <tr key={h.id}>
          <td>{h.tieu_de}<div className="muted" style={{ fontSize: 12 }}>{fmtDT(h.luc)} · {h.dang_boi}</div></td><td>{h.nhom_ten}</td>
          <td>{h.danh_cho.map((k: string) => d.danh_cho[k] || k).join(", ")}</td><td><Tag cls={h.hien ? "ok" : ""}>{h.hien ? "Đang hiện" : "Đã gỡ"}</Tag></td>
          <td style={{ whiteSpace: "nowrap" }}><button className="act grey" style={{ margin: 0 }} onClick={() => taiTep(`/cong-ncc/hoc-lieu/${h.id}/tep`, "hoc-lieu.pdf").catch((e) => toast(errMsg(e), true))}>Xem</button>
            {Q.hoc_lieu && h.hien && <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => goi(`/cong-ncc/hoc-lieu/${h.id}/go`)}>Gỡ</button>}</td></tr>)}</tbody></table>}</div></>}
  </div>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
