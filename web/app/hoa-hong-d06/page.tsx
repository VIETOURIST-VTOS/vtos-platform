"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** DH-1 · HOA HỒNG ĐỐI TÁC BÁN HÀNG (D06) — Chủ tịch chốt 26/10/2026, duyệt bản xem thử cùng ngày.
 *  Mọi con số do MÁY CHỦ tính (services/hoa_hong_d06.py): số nguyên đồng, lũy tiến từng phần, làm tròn
 *  một lần trên tổng kỳ. Màn hình chỉ hiển thị. Chương trình chưa có ngày hiệu lực (tham số
 *  d06_hieu_luc_tu) thì mọi số là TÍNH THỬ: không ghi sổ, không chốt, không lập đề nghị chi. */
const d = (n: number) => (n ?? 0).toLocaleString("vi-VN");
const pct = (bps: number) => (bps / 100).toLocaleString("vi-VN") + "%";
const thangNay = () => { const t = new Date(Date.now() + 7 * 3600e3); return t.toISOString().slice(0, 7); };

function Trang() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const keToan = ["ketoan", "ketoan_truong", "ketoan_tt", "chutich", "tgd"].includes(role);
  const chonHT = ["gd_kd", "ketoan", "ketoan_truong", "ketoan_tt", "chutich", "tgd"].includes(role);
  const [ky, setKy] = useState(thangNay());
  const [x, setX] = useState<any>(null);
  const [mo, setMo] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api(`/hoa-hong-d06?ky=${ky}`).then(setX).catch((e) => toast(errMsg(e), true)); }, [ky, toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json?: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json: json ?? {} }); toast(r.message); load(); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const ten = (c: string) => (c === "dai_ly_d06" ? "Đại lý" : "CTV bán hàng");
  return (<>
    <h1>Hoa hồng đối tác bán hàng (D06)</h1>
    <p className="muted">Lũy tiến từng phần theo tháng, giờ Việt Nam · tháng mới tính lại từ 0 · không giới hạn tiền hoa hồng · Chủ tịch chốt 26/10/2026.</p>
    <div style={{ display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }}>
      <label>Kỳ<input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
      {keToan && <button className="act teal" style={{ margin: 0 }} disabled={busy || !x.dang_bat} onClick={() => goi("/hoa-hong-d06/tinh-lai", { ky })}>Tính lại kỳ {ky}</button>}
    </div>
    {!x.dang_bat && <div className="gate"><b>Chương trình chưa bật cho kỳ này.</b> Tham số «d06_hieu_luc_tu» {x.hieu_luc_tu ? `có hiệu lực từ ${fmtD(x.hieu_luc_tu)}` : "đang trống"} — số dưới đây là <b>tính thử</b>: không ghi sổ, không chốt, không lập đề nghị chi. Chủ tịch ký ngày hiệu lực ở màn Tham số.</div>}
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))" }}>
      {Object.entries(x.bac).map(([c, v]: any) => <div key={c} className="panel"><h3 style={{ marginTop: 0 }}>{ten(c)} — D06</h3>
        <table><tbody>{v.bac.map(([tu, den, bps]: number[]) => <tr key={tu}><td>{den ? (tu ? `Trên ${d(tu / 1e6)} đến ${d(den / 1e6)} triệu` : `${d(den / 1e6)} triệu đầu`) : `Trên ${d(tu / 1e6)} triệu`}</td><td className="num">{pct(bps)}</td></tr>)}</tbody></table></div>)}
      <div className="panel"><h3 style={{ marginTop: 0 }}>Đủ điều kiện khi</h3><ul style={{ margin: 0, paddingLeft: 18 }}>
        <li>Booking không hủy, gắn đối tác</li><li>Tour đã kết thúc <b>và</b> khách đã trả đủ</li><li>Doanh số = giá trị booking sau giảm giá</li>
        <li>Vào tháng của ngày muộn hơn trong hai điều kiện</li><li>Đối tác giá NET / chưa chọn: không tính</li></ul></div>
    </div>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
      {[["Doanh số đủ điều kiện", x.tong.doanh_so], ["Tổng quyền hưởng", x.tong.quyen_huong], ["Đã trả", x.tong.da_tra], ["Còn phải trả", x.tong.con_phai_tra]].map(([l, v]: any) =>
        <div key={l} className="panel"><div className="mono" style={{ fontSize: 22, fontWeight: 700, color: v < 0 ? "var(--red)" : "var(--navy)" }}>{d(v)}</div><div className="muted">{l}</div></div>)}
    </div>
    <div className="panel wrap"><h3 style={{ marginTop: 0 }}>Từng đối tác · kỳ {ky} · bấm một dòng để xem nguồn doanh số</h3>
      <table><thead><tr><th>Đối tác</th><th>Pháp nhân</th><th>Hình thức</th><th className="num">Doanh số đủ ĐK</th><th>Bậc hiện tại</th><th className="num">Cơ bản</th><th className="num">Thưởng vượt bậc</th><th className="num">Điều chỉnh</th><th className="num">Đã trả</th><th className="num">Đang đề nghị chi</th><th className="num">Còn phải trả</th><th>Kỳ</th></tr></thead>
        <tbody>{x.dong.length ? x.dong.map((r: any) => { const k = `${r.doi_tac_id}-${r.company_key}-${r.chuong_trinh}`; return <>
          <tr key={k} style={{ cursor: "pointer" }} onClick={() => setMo(mo === k ? null : k)}>
            <td><b>{r.ten}</b>{r.can_tinh_lai && <> <Tag cls="warn">nguồn đổi — cần tính lại</Tag></>}</td><td className="muted">{r.phap_nhan}</td><td>{r.hinh_thuc_ten}</td>
            <td className="num">{d(r.doanh_so)}</td>
            <td>{r.bac_hien_tai?.toi_da ? <Tag cls="ok">Đang hưởng tỷ lệ tối đa {pct(r.bac_hien_tai.bps)}</Tag> : <Tag cls="">{pct(r.bac_hien_tai?.bps || 0)} · còn {d((r.bac_hien_tai?.con_toi_bac_sau || 0) / 1e6)} tr tới bậc sau</Tag>}</td>
            <td className="num">{d(r.co_ban)}</td><td className="num">{d(r.thuong)}</td>
            <td className="num" style={{ color: r.dieu_chinh < 0 ? "var(--red)" : undefined }}>{d(r.dieu_chinh)}</td>
            <td className="num">{d(r.da_tra)}</td><td className="num">{d(r.dang_de_nghi)}</td>
            <td className="num" style={{ color: r.con_phai_tra < 0 ? "var(--red)" : undefined }}><b>{d(r.con_phai_tra)}</b></td>
            <td>{r.con_phai_tra < 0 ? <Tag cls="red">Vượt chi — lập hồ sơ thu hồi</Tag> : r.trang_thai === "da_chot" ? <Tag cls="ok">Đã chốt</Tag> : <Tag cls="">{r.da_ghi_so ? "Đang mở" : "Chưa ghi sổ"}</Tag>}</td></tr>
          {mo === k && <tr key={k + "d"}><td colSpan={12}><div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", display: "grid", gap: 10 }}>
            <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1.4fr)" }}>
              <div><b>Bậc</b><table><tbody>{r.bac.filter((b: any) => b.doanh_so > 0).map((b: any) => <tr key={b.tu}><td>{pct(b.bps)} × {d(b.doanh_so)}</td><td className="num">{d(b.tien)}</td></tr>)}
                <tr><td><b>Tổng quyền hưởng</b></td><td className="num"><b>{d(r.tong)}</b></td></tr></tbody></table>
                <p className="muted">Làm tròn một lần trên tổng kỳ (số nguyên đồng). Thưởng vượt bậc = tổng − tỷ lệ cơ bản × doanh số.</p></div>
              <div><b>Nguồn doanh số ({r.nguon.length} booking)</b><table><tbody>{r.nguon.map((n: any) => <tr key={n.booking}><td className="mono">{n.booking}</td><td>{n.ten_tour}</td><td className="muted">KT {fmtD(n.ket_thuc)} · đủ {fmtD(n.thu_du)}</td><td className="num">{d(n.doanh_so)}</td></tr>)}</tbody></table>
                <p className="muted">KT = tour kết thúc · đủ = ngày khách trả đủ. Hủy / hoàn sau này: tính lại đúng kỳ gốc, ghi dòng điều chỉnh có dấu.</p></div>
            </div>
            {r.so.length > 0 && <div><b>Sổ</b> {r.so.map((s: any, i: number) => <span key={i} className="muted"> · lần {s.revision} {s.thanh_phan === "BASE" ? "cơ bản" : "thưởng"} {d(s.so_tien)}{s.sau_chot ? " (sau chốt)" : ""} — {s.boi}</span>)}</div>}
            {keToan && x.dang_bat && r.ky_id && <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
              {r.trang_thai !== "da_chot" && <button className="act grey" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/hoa-hong-d06/ky/${r.ky_id}/chot`)}>Chốt kỳ</button>}
              {r.trang_thai === "da_chot" && r.co_the_de_nghi > 0 && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/hoa-hong-d06/ky/${r.ky_id}/de-nghi-chi`)}>Lập đề nghị chi {d(r.co_the_de_nghi)}</button>}
              <span className="muted">Đề nghị chi đi luồng duyệt chi: GĐ KD xác nhận → Kế toán → dưới 100 triệu TGĐ, từ 100 triệu Chủ tịch.</span></div>}
          </div></td></tr>}
        </>; }) : <tr><td colSpan={12} className="muted">Chưa có đối tác nào có doanh số đủ điều kiện trong kỳ này.</td></tr>}</tbody></table></div>
    <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)" }}>
      <div className="panel"><h3 style={{ marginTop: 0 }}>Đối tác chưa chọn hình thức <Tag cls="warn">{x.chua_chon.length}</Tag></h3>
        <p className="muted">Chưa chọn thì KHÔNG tính — không tự áp D06 cho ai.</p>
        <ul style={{ margin: 0, paddingLeft: 18 }}>{x.chua_chon.map((c: any) => <li key={c.doi_tac_id}>{c.ten} — {c.so_booking} booking, {d(c.doanh_so)} đ chờ cấu hình</li>)}</ul></div>
      <div className="panel"><h3 style={{ marginTop: 0 }}>Booking của đối tác chưa đủ điều kiện <Tag cls="">{x.chua_du.length}</Tag></h3>
        <p className="muted">Để biết sắp vào kỳ nào; không cộng.</p>
        <ul style={{ margin: 0, paddingLeft: 18 }}>{x.chua_du.slice(0, 30).map((c: any) => <li key={c.booking}><span className="mono">{c.booking}</span> · {c.ten} · {c.ly_do}{c.con_thieu ? ` (còn thiếu ${d(c.con_thieu)})` : ""}</li>)}</ul></div>
    </div>
    <div className="panel wrap"><h3 style={{ marginTop: 0 }}>Hình thức hưởng của từng đối tác</h3>
      <p className="muted">Lần chọn đầu có hiệu lực từ đầu tháng này; đổi sau đó có hiệu lực từ đầu tháng kế tiếp, không đổi kỳ đang mở. Thêm đối tác hoặc CTV bán hàng ở màn Người bán hàng.</p>
      <table><thead><tr><th>Đối tác</th><th>Loại</th><th>Kỳ {ky}</th><th>Tháng sau</th>{chonHT && <th>Chọn</th>}</tr></thead>
        <tbody>{x.doi_tac.map((t: any) => <tr key={t.id}><td>{t.ten}</td><td className="muted">{t.loai}</td>
          <td>{t.hinh_thuc ? x.hinh_thuc_chon[t.hinh_thuc] : <Tag cls="warn">Chưa chọn</Tag>}</td>
          <td className="muted">{t.hinh_thuc_thang_sau ? x.hinh_thuc_chon[t.hinh_thuc_thang_sau] : "—"}</td>
          {chonHT && <td><select value="" disabled={busy} onChange={(e) => e.target.value && goi("/hoa-hong-d06/hinh-thuc", { doi_tac_id: t.id, hinh_thuc: e.target.value })}>
            <option value="">— đổi —</option>{Object.entries(x.hinh_thuc_chon).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></td>}</tr>)}</tbody></table></div>
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
