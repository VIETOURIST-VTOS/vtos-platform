"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

function Params() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]);
  const load = useCallback(() => api("/params").then(setRows), []);
  useEffect(() => { load(); }, [load]);
  const active = rows.filter((p) => p.status === "active"); const keys = Array.from(new Set(active.map((p) => p.key)));
  async function propose(e: React.FormEvent) {
    e.preventDefault(); const f = e.target as HTMLFormElement; const d: any = Object.fromEntries(new FormData(f).entries());
    try { const r = await api("/params", { method: "POST", json: d }); toast(r.message); f.reset(); load(); } catch (x) { toast(errMsg(x), true); }
  }
  async function sign(id: number) { try { const r = await api(`/params/${id}/sign`, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); } }
  const canSign = ["chutich", "tgd"].includes(user?.role || "");
  return (<>
    <h1>Chính sách &amp; định mức – hiệu lực theo ngày, đổi phải đủ 2 chữ ký</h1>
    <div className="panel"><h2>Đề xuất thay đổi</h2>
      <form onSubmit={propose}><div className="grid">
        <div><label>Tham số</label><select name="key">{keys.map((k) => <option key={k} value={k}>{k} – {active.find((p) => p.key === k)?.label}</option>)}</select></div>
        <div><label>Giá trị mới</label><input name="value" required /></div>
        <div><label>Hiệu lực từ</label><input type="date" name="effective_from" required defaultValue={new Date().toISOString().slice(0, 10)} /></div>
        <div><label>Căn cứ</label><input name="source" /></div>
      </div><button className="act orange">Trình Chủ tịch + TGĐ</button></form></div>
    <div className="panel wrap"><table><thead><tr><th>Khóa</th><th>Tên</th><th className="num">Giá trị</th><th>Đơn vị</th><th>Hiệu lực</th><th>Căn cứ</th><th>Trạng thái</th><th>Chữ ký</th><th></th></tr></thead>
      <tbody>{rows.map((p) => <tr key={p.id}><td className="mono">{p.key}</td><td>{p.label}</td><td className="num">{p.key === "thang_f_bang" ? <FTable v={p.value} /> : <b>{Number(p.value) >= 1000 ? vnd(Number(p.value)) : p.value}</b>}</td><td>{p.unit}</td><td>{fmtD(p.effective_from)}</td><td className="muted">{p.source}</td>
        <td><Tag cls={p.status === "active" ? "ok" : "warn"}>{p.status}</Tag></td><td>CT {p.signed_chutich ? "✔" : "…"} · TGĐ {p.signed_tgd ? "✔" : "…"}</td>
        <td>{p.status === "pending" && canSign && <button className="act" style={{ margin: 0 }} onClick={() => sign(p.id)}>Ký</button>}</td></tr>)}</tbody></table></div>
  </>);
}
function FTable({ v }: { v: string }) {
  const rows = v.split(",").map((x) => x.split(":")).filter((x) => x.length === 2);
  return (<details><summary><b>Bảng B.1 – {rows.length} bậc (bấm xem)</b></summary>
    <table style={{ fontSize: 12, marginTop: 4 }}><thead><tr><th>Bậc</th><th>Từ % mốc</th><th>HCM (mốc 200tr)</th><th>Tỉnh (mốc 120tr)</th><th>Hệ số</th></tr></thead>
      <tbody><tr><td>f0</td><td>dưới {rows[0]?.[0]}%</td><td>dưới {vnd(Number(rows[0]?.[0]) / 100 * 200e6)}</td><td>dưới {vnd(Number(rows[0]?.[0]) / 100 * 120e6)}</td><td>0%</td></tr>
        {rows.map(([t, r], i) => <tr key={t}><td>{i === rows.length - 1 ? "trần" : `f${i + 1}`}</td><td>{t}%</td><td>{vnd(Number(t) / 100 * 200e6)}</td><td>{vnd(Number(t) / 100 * 120e6)}</td><td>{r}%</td></tr>)}</tbody></table>
    <div className="muted">Hoa hồng = hệ số bậc sàn × (doanh thu tính chỉ tiêu − mốc), không nội suy; chỉ booking đủ 4 trường bắt buộc.</div></details>);
}
/* ══════════════════════════════════════════════════════════════════════════════════════════════
   ĐỢT E4a · ĐIỀU KHOẢN THANH TOÁN — cửa nhập trên chính màn hình chính sách
   ══════════════════════════════════════════════════════════════════════════════════════════════
   ĐẶT Ở ĐÂY CHỨ KHÔNG DỰNG MÀN HÌNH MỚI, và đó là chủ ý: màn hình mới là một khoá mới trong
   MENU_ROLES và MAN_HINH_API, tức là xin thêm quyền cho một loạt vai mà chưa ai ký. Điều khoản là
   CHÍNH SÁCH, có hiệu lực theo ngày, do Chủ tịch ký — nó thuộc về đúng màn hình này.

   `test_cn1` của bộ kiểm cửa nhập đỏ ngay khi một bảng vào kho mà không có cửa. Bảng
   `dieu_khoan_thanh_toan` và `dot_thanh_toan` được khai vào CUA_TAY, và lời khai ấy chỉ đúng khi
   màn hình này có thật — nên hai thứ đi cùng một đợt, không tách. */
function DieuKhoan() {
  const { user, toast } = useShell();
  const [d, setD] = useState<any>({ rows: [], moc: [], ai_ky: [] });
  const [dot, setDot] = useState<any[]>([{ ty_le: 50, lech_ngay: -30, dien_giai: "" },
                                         { ty_le: 50, lech_ngay: -7, dien_giai: "" }]);
  const [xem, setXem] = useState<any>(null);
  const load = useCallback(() => api("/params/dieu-khoan").then(setD), []);
  useEffect(() => { load(); }, [load]);

  /* Tổng tỷ lệ tính NGAY TRÊN MÀN HÌNH, không chờ máy chủ trả lời. Người gõ thấy ngay mình đang
     thiếu bao nhiêu phần trăm; máy chủ vẫn kiểm lại, vì một hàng rào chỉ ở giao diện là không có
     hàng rào nào. */
  const tong = dot.reduce((s, x) => s + (Number(x.ty_le) || 0), 0);
  const du = Math.abs(tong - 100) <= 0.01;

  function sua(i: number, k: string, v: any) {
    setDot(dot.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  }
  async function trinh(e: React.FormEvent) {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    const o: any = Object.fromEntries(new FormData(f).entries());
    try {
      const r = await api("/params/dieu-khoan", { method: "POST", json: { ...o, dot } });
      toast(r.message); f.reset(); load();
    } catch (x) { toast(errMsg(x), true); }
  }
  async function ky(id: number) {
    try { const r = await api(`/params/dieu-khoan/${id}/ky`, { method: "POST" }); toast(r.message); load(); }
    catch (x) { toast(errMsg(x), true); }
  }
  async function xemTruoc(id: number) {
    try { setXem({ ...(await api(`/params/dieu-khoan/${id}/xem-truoc-tinh-lai`)), id }); }
    catch (x) { toast(errMsg(x), true); }
  }
  async function ap(id: number) {
    try { const r = await api(`/params/dieu-khoan/${id}/ap-tinh-lai`, { method: "POST" }); toast(r.message); setXem(null); load(); }
    catch (x) { toast(errMsg(x), true); }
  }
  const coKy = (d.ai_ky || []).length > 0 && (user?.role === "chutich" || user?.role === "tgd");

  return (<>
    <h1>Điều khoản thanh toán – khai một lần, dùng cho nhiều hợp đồng</h1>
    <div className="muted" style={{ marginBottom: 8 }}>
      Mỗi điều khoản nói ba điều: đếm ngày <b>từ mốc nào</b>, chia <b>mấy đợt</b>, mỗi đợt <b>bao nhiêu
      phần trăm và lệch mốc mấy ngày</b>. Số âm là TRƯỚC mốc, dương là SAU. Hạn của từng đợt do máy
      suy ra từ đây, không gõ tay. Người ký: {(d.ai_ky || []).join(" và ") || "—"}.
    </div>

    <div className="panel"><h2>Thêm điều khoản</h2>
      <form onSubmit={trinh}>
        <div className="grid">
          <div><label>Mã</label><input name="ma" required placeholder="COC50-KH7" /></div>
          <div><label>Tên điều khoản</label><input name="ten" required placeholder="50% cọc – 50% trước khởi hành 7 ngày" /></div>
          <div><label>Đếm ngày từ mốc</label><select name="moc">{(d.moc || []).map((m: any) => <option key={m.ma} value={m.ma}>{m.ten}</option>)}</select></div>
          <div><label>Hiệu lực từ</label><input type="date" name="effective_from" defaultValue={new Date().toISOString().slice(0, 10)} /></div>
        </div>

        <div className="wrap"><table><thead><tr><th>Đợt</th><th className="num">Tỷ lệ %</th><th className="num">Lệch mốc (ngày)</th><th>Diễn giải</th><th></th></tr></thead>
          <tbody>{dot.map((x, i) => <tr key={i}>
            <td>{i + 1}</td>
            <td className="num"><input style={{ width: 90 }} type="number" step="0.01" value={x.ty_le} onChange={(e) => sua(i, "ty_le", e.target.value)} /></td>
            <td className="num"><input style={{ width: 100 }} type="number" value={x.lech_ngay} onChange={(e) => sua(i, "lech_ngay", e.target.value)} /></td>
            <td><input value={x.dien_giai} onChange={(e) => sua(i, "dien_giai", e.target.value)} placeholder="Đặt cọc khi chốt đoàn" /></td>
            <td>{dot.length > 1 && <button type="button" className="act" style={{ margin: 0 }} onClick={() => setDot(dot.filter((_, j) => j !== i))}>Bỏ</button>}</td>
          </tr>)}</tbody></table></div>

        <button type="button" className="act" onClick={() => setDot([...dot, { ty_le: 0, lech_ngay: 0, dien_giai: "" }])}>Thêm đợt</button>
        {/* Không đủ 100% thì nút trình KHOÁ. Một điều khoản thiếu phần trăm là một khoản tiền không
            có hạn, và phần tiền ấy sẽ không hiện ở tháng nào trên bảng dòng tiền. */}
        <Tag cls={du ? "ok" : "red"}>Tổng các đợt: {tong.toFixed(2)}%</Tag>
        {!du && <span className="muted"> – phải đúng 100% mới trình được.</span>}
        <button className="act orange" disabled={!du}>Trình {(d.ai_ky || []).join(" và ")}</button>
      </form>
    </div>

    <div className="panel wrap"><table>
      <thead><tr><th>Mã</th><th>Tên điều khoản</th><th>Mốc đếm</th><th>Các đợt</th><th className="num">Đang dùng ở</th><th>Trạng thái</th><th></th></tr></thead>
      <tbody>{(d.rows || []).map((r: any) => <tr key={r.id}>
        <td className="mono">{r.ma}</td><td>{r.ten}</td><td>{r.ten_moc}</td>
        <td className="muted">{(r.dot || []).map((x: any, i: number) => `${x.ty_le}% ở ${Number(x.lech_ngay) < 0 ? "−" : "+"}${Math.abs(Number(x.lech_ngay))}`).join(" · ") || "—"}</td>
        <td className="num">{r.dung_o ? `${r.dung_o} hợp đồng` : "chưa dùng"}</td>
        <td><Tag cls={r.status === "active" ? "ok" : r.status === "pending" ? "warn" : "red"}>{r.status}</Tag></td>
        <td>
          {r.status === "pending" && coKy && <button className="act" style={{ margin: 0 }} onClick={() => ky(r.id)}>Ký</button>}
          {r.status === "active" && r.dung_o > 0 && <button className="act" style={{ margin: 0 }} onClick={() => xemTruoc(r.id)}>Xem trước tính lại</button>}
        </td>
      </tr>)}</tbody></table></div>

    {/* XEM TRƯỚC RỒI MỚI ÁP — Chủ tịch chốt 12/10/2026. Một lần bấm có thể dời hạn của hàng chục
        khoản tiền, nên người bấm phải thấy trước đúng những đợt nào đổi, từ ngày nào sang ngày nào.
        Khối "giữ nguyên" KHÔNG bị giấu đi: nó là chỗ luật cũ (11/9/2026) vẫn đang có hiệu lực. */}
    {xem && <div className="panel">
      <h2>Tính lại hạn theo điều khoản {xem.dieu_khoan}</h2>
      <div className="muted">{xem.message}</div>
      {xem.doi?.length > 0 && <div className="wrap"><table>
        <thead><tr><th>Nghĩa vụ</th><th>Đối tượng</th><th>Đợt</th><th className="num">Số tiền</th><th>Hạn cũ</th><th>Hạn mới</th></tr></thead>
        <tbody>{xem.doi.map((x: any, i: number) => <tr key={i}>
          <td className="mono">{x.nghia_vu}</td><td>{x.doi_tuong}</td><td>{x.dot}</td>
          <td className="num">{vnd(x.so_tien)}</td><td>{fmtD(x.han_cu)}</td><td><b>{fmtD(x.han_moi)}</b></td>
        </tr>)}</tbody></table></div>}
      {xem.giu_nguyen?.length > 0 && <>
        <h3>Giữ nguyên, không dời</h3>
        <div className="wrap"><table>
          <thead><tr><th>Nghĩa vụ</th><th>Đợt</th><th>Hạn</th><th>Vì sao giữ nguyên</th></tr></thead>
          <tbody>{xem.giu_nguyen.map((x: any, i: number) => <tr key={i}>
            <td className="mono">{x.nghia_vu}</td><td>{x.dot}</td><td>{fmtD(x.han_cu)}</td><td className="muted">{x.ly_do}</td>
          </tr>)}</tbody></table></div>
      </>}
      <button className="act orange" onClick={() => ap(xem.id)} disabled={!xem.doi?.length}>Áp cho {xem.doi?.length || 0} đợt</button>
      <button className="act" onClick={() => setXem(null)}>Đóng</button>
    </div>}
  </>);
}
export default function Page() { return <Shell><Params /><DieuKhoan /></Shell>; }
