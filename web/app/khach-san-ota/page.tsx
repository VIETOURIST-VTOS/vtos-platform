"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KS-1 (Chủ tịch duyệt 28/10/2026) — KHÁCH SẠN QUA OTA. Khách bấm «Tiếp tục trên OTA» ở cổng, đặt và
 *  thanh toán trên OTA; VTOS chỉ ghi LƯỢT CHUYỂN (không phải đặt phòng). Chủ tịch nhập link và bật.
 *  Bật chỉ được khi đủ bốn điều — máy chủ kiểm, nút ở đây chỉ để đỡ bấm vào cửa đóng. Đổi link = phiên
 *  bản mới, OTA tự tắt và phải kiểm lại. */
const CHK: React.CSSProperties = { display: "flex", alignItems: "center", gap: 10, marginTop: 4, fontSize: 14, color: "var(--ink)", cursor: "pointer" };
const O_TICK: React.CSSProperties = { width: 18, height: 18, flex: "none", margin: 0, padding: 0, accentColor: "var(--teal)" };
const TT_TAG: Record<string, string> = { da_duyet: "ok", cho_duyet: "warn", chua_dang_ky: "", tam_dung: "red" };

function SuaOta({ o, tt, xong }: { o: any; tt: Record<string, string>; xong: (d: any) => void }) {
  const { toast } = useShell();
  const [f, setF] = useState({ trang_thai: o.trang_thai, link: o.link, ten_mien: o.ten_mien, duong_dan: o.duong_dan,
    da_kiem_link: o.da_kiem_link, duoc_dung_web: o.duoc_dung_web, bang_chung: o.bang_chung, ghi_chu: o.ghi_chu,
    subid_cho_phep: o.subid_cho_phep, subid_tham_so: o.subid_tham_so || "" });
  const doiLink = f.link !== o.link || f.ten_mien !== o.ten_mien || f.duong_dan !== o.duong_dan;
  const luu = async () => {
    try { const r = await api<any>(`/khach-san-ota/${o.id}`, { method: "POST", json: f }); toast(r.message); xong(r); }
    catch (e) { toast(errMsg(e), true); }
  };
  const o2 = (k: string, nhan: string, ph = "") => <label style={{ display: "grid", gap: 4 }}><span className="muted">{nhan}</span>
    <input value={(f as any)[k]} placeholder={ph} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  return (<div style={{ background: "var(--panel2)", borderRadius: 8, padding: "10px 12px", display: "grid", gap: 8 }}>
    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))", gap: 8 }}>
      <label style={{ display: "grid", gap: 4 }}><span className="muted">Trạng thái hợp tác</span>
        <select value={f.trang_thai} onChange={(e) => setF({ ...f, trang_thai: e.target.value })}>
          {Object.entries(tt).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      {o2("link", "Link Affiliate chính thức", "https://…")}
      {o2("ten_mien", "Tên miền cho phép", "expedia.com")}
      {o2("duong_dan", "Đường dẫn link bắt đầu bằng (không bắt buộc)", "/affiliate/")}
      {o2("bang_chung", "Bằng chứng (thư duyệt, số vụ hỗ trợ…)")}
      {o2("ghi_chu", "Ghi chú")}
    </div>
    {doiLink && o.link && <div className="muted">Đổi link / tên miền / đường dẫn = phiên bản mới: OTA tự tắt, phải kiểm lại link.</div>}
    {/* Ô tick phải tự đặt rộng: globals.css cho mọi input width:100%, ô tick sẽ chiếm hết dòng và đẩy chữ đi. */}
    <label style={CHK}><input type="checkbox" style={O_TICK} checked={f.da_kiem_link} onChange={(e) => setF({ ...f, da_kiem_link: e.target.checked })} />
      <span>Đã mở thử link — đúng tài khoản Affiliate của pháp nhân hợp đồng</span></label>
    <label style={CHK}><input type="checkbox" style={O_TICK} checked={f.duoc_dung_web} onChange={(e) => setF({ ...f, duoc_dung_web: e.target.checked })} />
      <span>OTA cho phép dùng link trên vietourist.vn</span></label>
    <div style={{ borderTop: "1px solid var(--line)", paddingTop: 8, display: "grid", gap: 6 }}>
      <b>Mã lượt chuyển (SubID) — đối soát về đúng khách / đại lý</b>
      <label style={CHK}><input type="checkbox" style={O_TICK} checked={f.subid_cho_phep} onChange={(e) => setF({ ...f, subid_cho_phep: e.target.checked })} />
        <span>OTA cho phép gắn SubID vào link và báo lại trong báo cáo</span></label>
      {o2("subid_tham_so", "Tên tham số SubID trên link (vd sid, subid)", "sid")}
      <div className="muted">Mã gắn vào là mã ngẫu nhiên của lượt chuyển — không chứa SĐT, email. Chỉ bật khi đã đọc tài liệu của OTA / mạng lưới.</div>
    </div>
    <button className="act teal" style={{ margin: 0, justifySelf: "start" }} onClick={luu}>Lưu</button>
  </div>);
}

function Trang() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [luot, setLuot] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [pn, setPn] = useState({ ma: "", ten: "", quoc_gia: "" });
  const load = useCallback(() => {
    api("/khach-san-ota").then(setD).catch((e) => toast(errMsg(e), true));
    api("/khach-san-ota/luot?so_ngay=7").then(setLuot).catch(() => null);
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const bat = async (o: any, b: boolean) => {
    try { const r = await api<any>(`/khach-san-ota/${o.id}/bat`, { method: "POST", json: { bat: b } }); toast(r.message); setD(r); }
    catch (e) { toast(errMsg(e), true); }
  };
  const themPn = async () => {
    try { const r = await api<any>("/khach-san-ota/phap-nhan", { method: "POST", json: pn }); toast(r.message); setD(r); setPn({ ma: "", ten: "", quoc_gia: "" }); }
    catch (e) { toast(errMsg(e), true); }
  };
  return (<>
    <h1>Khách sạn qua OTA</h1>
    <p className="muted">Khách chọn khách sạn, xem giá, đặt và thanh toán trên OTA; VTD chuyển khách bằng link Affiliate chính thức. Một lượt chuyển KHÔNG phải đặt phòng, không phải doanh thu — đặt phòng và hoa hồng do OTA báo về được đối soát ở màn Đối soát OTA. OTA chỉ hiện cho khách khi đủ bốn điều: hợp tác đã duyệt · link hợp lệ · đã kiểm link · được dùng trên web.</p>

    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))" }}>
      <div className="panel"><b>Lượt chuyển 7 ngày</b><div style={{ fontSize: 26, fontWeight: 700 }}>{luot ? luot.tong : "…"}</div><div className="muted">không phải đặt phòng</div></div>
      <div className="panel"><b>Theo cổng</b><div className="muted">{luot ? `Khách hàng ${luot.theo_cong.khach_hang || 0} · Đối tác ${luot.theo_cong.doi_tac || 0} · Cổ đông ${luot.theo_cong.co_dong || 0}` : "…"}</div></div>
      <div className="panel"><b>Đặt phòng đã xác minh</b><div style={{ fontSize: 26, fontWeight: 700 }}>—</div><div className="muted">Kế toán nạp báo cáo OTA ở màn <a href="/doi-soat-ota">Đối soát OTA</a></div></div>
    </div>

    <div className="panel wrap"><b>Đối tác OTA</b>
      <table><thead><tr><th>OTA</th><th>Pháp nhân</th><th>Hợp tác</th><th>Link</th><th>Đã kiểm</th><th>Dùng trên web</th><th>Lượt 7 ngày</th><th>Hiện cho khách</th><th></th></tr></thead>
        <tbody>{d?.ota?.map((o: any) => <>
          <tr key={o.id}>
            <td><b>{o.ten}</b><div className="muted">phiên bản link {o.phien_ban}</div></td>
            <td className="muted">{o.phap_nhan?.ten || "—"}</td>
            <td><Tag cls={TT_TAG[o.trang_thai] || ""}>{o.trang_thai_ten}</Tag></td>
            <td className="mono" style={{ maxWidth: 260, overflowWrap: "anywhere" }}>{o.link || <span className="muted">chưa nhập</span>}{o.loi_link && <div style={{ color: "var(--red)" }}>{o.loi_link}</div>}</td>
            <td>{o.da_kiem_link ? <Tag cls="ok">✓</Tag> : "—"}</td>
            <td>{o.duoc_dung_web ? <Tag cls="ok">✓</Tag> : "—"}</td>
            <td className="mono">{o.luot_7_ngay}</td>
            <td>{o.dang_mo ? <Tag cls="ok">Đang hiện</Tag> : <><Tag cls="">Tắt</Tag>{o.thieu.length > 0 && <div className="muted" style={{ fontSize: 12 }}>Thiếu: {o.thieu.join("; ")}</div>}</>}</td>
            <td style={{ whiteSpace: "nowrap" }}>{o.sua_duoc && <>
              <button className="act grey" style={{ margin: 0 }} onClick={() => setMo(mo === o.id ? null : o.id)}>{mo === o.id ? "Đóng" : "Sửa"}</button>{" "}
              {o.bat ? <button className="act orange" style={{ margin: 0 }} onClick={() => bat(o, false)}>Tắt</button>
                : <button className="act teal" style={{ margin: 0 }} disabled={o.thieu.length > 0} title={o.thieu.join("; ")} onClick={() => bat(o, true)}>Bật</button>}</>}</td></tr>
          {mo === o.id && <tr key={o.id + "s"}><td colSpan={9}><SuaOta o={o} tt={d.trang_thai} xong={(r) => { setD(r); setMo(null); }} /></td></tr>}
        </>)}</tbody></table>
      {d && !d.sua_duoc && <div className="muted">Chỉ Chủ tịch nhập link và bật OTA; vai của bạn chỉ xem.</div>}
    </div>

    <div className="panel"><b>Pháp nhân hợp đồng OTA</b>
      <div className="muted">Danh mục riêng cho pháp nhân ký Affiliate và hưởng hoa hồng OTA — KHÔNG phải danh sách công ty của tập đoàn (không vào hợp nhất, dòng tiền, suy pháp nhân booking).</div>
      <ul style={{ margin: "6px 0" }}>{d?.phap_nhan?.map((p: any) => <li key={p.id}><b>{p.ten}</b> · {p.quoc_gia || "—"} · <span className="mono">{p.ma}</span></li>)}</ul>
      {d?.sua_duoc && <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input value={pn.ma} placeholder="Mã (vd INFINIS_CA)" onChange={(e) => setPn({ ...pn, ma: e.target.value })} style={{ maxWidth: 160 }} />
        <input value={pn.ten} placeholder="Tên pháp nhân" onChange={(e) => setPn({ ...pn, ten: e.target.value })} style={{ maxWidth: 280 }} />
        <input value={pn.quoc_gia} placeholder="Quốc gia" onChange={(e) => setPn({ ...pn, quoc_gia: e.target.value })} style={{ maxWidth: 140 }} />
        <button className="act grey" style={{ margin: 0 }} disabled={!pn.ma.trim() || !pn.ten.trim()} onClick={themPn}>Thêm pháp nhân</button></div>}
    </div>

    <div className="panel wrap"><b>Lượt chuyển gần đây</b>
      <table><thead><tr><th>Ngày</th><th>OTA</th><th>Cổng</th><th>Đối tác bán hàng</th><th>Lượt</th></tr></thead>
        <tbody>{luot?.dong?.length ? luot.dong.map((x: any, i: number) => <tr key={i}><td className="mono">{x.ngay.split("-").reverse().join("/")}</td><td>{x.ota}</td><td>{x.cong_ten}</td><td>{x.doi_tac || "—"}</td><td className="mono">{x.luot}</td></tr>)
          : <tr><td colSpan={5} className="muted">Chưa có lượt chuyển nào trong 7 ngày.</td></tr>}</tbody></table>
      <div className="muted">Không lưu số điện thoại, email vào link; không gửi gì của khách sang OTA.</div>
    </div>
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
