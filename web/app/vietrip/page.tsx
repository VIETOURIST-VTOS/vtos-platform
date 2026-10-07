"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

// Vai được bấm nút nạp bù — KHỚP ĐÚNG `SYNC_ROLES` của cửa máy chủ (cntt · ketoan · tgd · chutich),
// rộng hơn hai nút cũ trên màn hình này. Cố ý: một cửa SỬA CHỮA mà người phát hiện ra hỏng hóc không
// bấm được thì vẫn là cửa chưa tới tay người dùng — đúng cái thiếu mà vòng này đi vá. Siết hẹp hơn
// máy chủ ở giao diện chỉ giấu nút đi chứ không chặn được ai, nên nới ở đây không mở thêm quyền nào.
const NAP_BU_VAI = ["cntt", "ketoan", "tgd", "chutich"];

const E: Record<string, string> = { product: "Sản phẩm", tour: "Tour", booking: "Booking", receipt: "Phiếu thu khách", supplier_payment: "Chi NCC", settlement: "Quyết toán chi tiết tour", user: "Người dùng", vehicle: "Xe", proposal: "Đề xuất chi" };

function Vietrip() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [st, setSt] = useState<any>(null);
  const [ent, setEnt] = useState("booking");
  const [rows, setRows] = useState<any[]>([]);
  const [unapplied, setUnapplied] = useState(false);
  const [rb, setRb] = useState<any>(null);
  const [rf, setRf] = useState({ from_date: new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10), to_date: new Date().toISOString().slice(0, 10), products: false, settlements_days: "10" });
  const loadRb = useCallback(() => api("/import/vietrip/robot-status").then(setRb).catch(() => {}), []);
  useEffect(() => { loadRb(); const t = setInterval(loadRb, 15000); return () => clearInterval(t); }, [loadRb]);
  const runRobot = async () => { try { const r = await api("/import/vietrip/sync", { method: "POST", json: { ...rf, settlements_days: Number(rf.settlements_days) || 10 } }); toast(r.message); loadRb(); } catch (x) { toast(errMsg(x), true); } };
  const load = useCallback(() => { api("/import/vietrip/status").then(setSt).catch((e) => toast(errMsg(e), true)); api(`/import/vietrip/records?entity=${ent}&limit=50&unapplied=${unapplied}`).then(setRows).catch(() => {}); }, [ent, unapplied]); // eslint-disable-line
  useEffect(() => { load(); }, [load]);
  // CỬA NẠP BÙ BOOKING CHO PHIẾU THU — đo 07/10/2026: 364 phiếu treo (299 phiếu thu 4.567.266.609 đ
  // + 65 phiếu chi), TẤT CẢ cùng một lý do "chưa có booking". Cửa máy chủ đã có từ 26/9 nhưng CHƯA
  // MÀN HÌNH NÀO GỌI TỚI — có cửa mà người phải dùng không với tới được, theo ranh giới 09/9 thì đó
  // là việc còn thiếu chứ không phải cửa đã xong.
  const [nb, setNb] = useState<any>(null);
  const [nbChay, setNbChay] = useState(false);
  const napBuBooking = async () => {
    // GỌI LẶP, KHÔNG GỌI MỘT PHÁT: cửa máy chủ CỐ Ý chia lô (mỗi lượt lật tối đa 3 trang Vietrip) vì
    // bản đầu lật 60 trang trong một lượt và Render giết máy chủ giữa chừng do nhịp tim /health quá
    // 5 giây — yêu cầu đang chạy nhận 503 và trông y hệt một lỗi mã. Vòng lặp nằm ở TRÌNH DUYỆT là
    // đúng chỗ: mỗi lượt gọi vẫn ngắn, và dừng giữa chừng không mất phần đã lấy được.
    setNbChay(true); setNb(null);
    let bat_dau = 0, luot = 0, tim_thay = 0, booking = 0, phieu = 0, trang = 0, dung_vi = "";
    try {
      while (luot < 40) {   // trần 40 lượt: một con số có đáy còn hơn một vòng lặp tin vào máy chủ
        const r = await api(`/import/vietrip/nap-bu/booking-cho-phieu-thu?gioi_han=500&bat_dau=${bat_dau}`, { method: "POST" });
        luot += 1; tim_thay += r.tim_thay || 0; booking += r.booking_da_anh_xa || 0;
        phieu += r.phieu_thu_da_anh_xa || 0; trang += r.so_trang || 0;
        setNb({ luot, tim_thay, booking, phieu, trang, can_tim: r.can_tim, con_treo: r.phieu_thu_con_treo, xong: r.xong, dung_vi });
        if (r.can_tim === 0) { dung_vi = "không còn phiếu nào treo vì thiếu booking"; break; }
        if (r.xong) { dung_vi = "máy chủ báo đã lật hết"; break; }
        // KHÔNG TIẾN THÌ DỪNG. `xong` là câu trả lời dứt khoát của máy chủ, nhưng nếu một ngày nó trả
        // `bat_dau_tiep` đứng yên thì vòng lặp này sẽ gọi mãi — và mỗi lượt là một lần đăng nhập
        // Vietrip. Thà dừng sớm và nói ra, còn hơn quay vòng im lặng.
        if (typeof r.bat_dau_tiep !== "number" || r.bat_dau_tiep <= bat_dau) {
          dung_vi = `máy chủ không trả mốc tiếp (bat_dau_tiep=${r.bat_dau_tiep}) – dừng để không gọi vòng`; break;
        }
        bat_dau = r.bat_dau_tiep;
      }
      if (!dung_vi && luot >= 40) dung_vi = "chạm trần 40 lượt – bấm lại để lật tiếp";
      setNb((o: any) => ({ ...(o || {}), luot, tim_thay, booking, phieu, trang, dung_vi }));
      toast(`Nạp bù xong ${luot} lượt: ánh xạ ${booking} booking, ${phieu} phiếu thu.`);
    } catch (x) { toast(errMsg(x), true); }
    setNbChay(false); load();
  };
  const apply = async () => { try { const r = await api("/import/vietrip/apply", { method: "POST" }); toast(r.message + " – " + Object.entries(r.applied).map(([k, v]) => `${k}: ${v}`).join(", ")); load(); } catch (x) { toast(errMsg(x), true); } };
  return (<>
    <h1>Đồng bộ Vietrip → VTOS (chuyển đổi dữ liệu, mục 11.3)</h1>
    <p className="muted">Robot đồng bộ chạy trong trình duyệt đã đăng nhập Vietrip (CNTT), đọc API Vietrip và đẩy vào VTOS theo lô; VTOS giữ bản gốc (vt_records) rồi ánh xạ sang tour, booking, phiếu thu, chi NCC, dòng chi phí quyết toán, người dùng, xe. Mã Vietrip lưu trong trường tham chiếu (VT…, VTPT…, VTDC…). Dữ liệu nhập không sinh bút toán – số dư đầu kỳ lấy từ MISA/BCTC khi cắt chuyển.</p>
    {st && <div className="kpis">{Object.entries(st).map(([k, v]: any) => <div className="kpi" key={k}><b>{v.total}</b><span>{E[k] || k} · đã ánh xạ {v.applied}{v.from && ` · ${fmtD(v.from)} → ${fmtD(v.to)}`}</span></div>)}</div>}
    {rb && <div className="panel"><h2>Robot đồng bộ tự động (phía máy chủ – không cần mở Chrome)</h2>
      <div className="grid">
        <div><b>Tài khoản robot Vietrip</b><div>{rb.credentials_set ? <Tag cls="ok">Đã cấu hình</Tag> : <Tag cls="red">Chưa đặt VIETRIP_PHONE / VIETRIP_PASSWORD trên Render</Tag>}</div><div className="muted">Nên tạo riêng 1 tài khoản Vietrip quyền Kế toán/Giám đốc chỉ để robot đọc.</div></div>
        <div><b>Trạng thái</b><div>{rb.running ? <Tag cls="warn">Đang chạy từ {fmtDT(rb.started)}</Tag> : rb.error ? <Tag cls="red">Lỗi: {rb.error}</Tag> : rb.finished ? <Tag cls="ok">Xong {fmtDT(rb.finished)}</Tag> : <Tag>Chưa chạy</Tag>}</div>
          {rb.result && <div className="muted">{Object.entries(rb.result).filter(([k]) => k !== "applied").map(([k, v]: any) => `${k}: ${v}`).join(" · ")}{rb.result.applied && ` · ánh xạ: ${Object.entries(rb.result.applied).map(([k, v]) => `${k} ${v}`).join(", ")}`}</div>}</div>
        <div><b>Lịch tự động (GitHub Actions)</b><div className="muted">03:00 hằng ngày: đồng bộ 7 ngày gần nhất + quyết toán tour kết thúc 10 ngày · SePay 30 phút/lần · báo cáo ngày 20:30 · tuần T7 · tháng ngày 10. Cần đặt secret ROBOT_TOKEN trên GitHub.</div></div>
      </div>
      {["cntt", "ketoan"].includes(role) && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
        <label>Từ <input type="date" value={rf.from_date} onChange={(e) => setRf({ ...rf, from_date: e.target.value })} /></label>
        <label>Đến <input type="date" value={rf.to_date} onChange={(e) => setRf({ ...rf, to_date: e.target.value })} /></label>
        <label>Quyết toán tour kết thúc trong (ngày) <input type="number" value={rf.settlements_days} onChange={(e) => setRf({ ...rf, settlements_days: e.target.value })} style={{ width: 70 }} /></label>
        <label><input type="checkbox" checked={rf.products} onChange={(e) => setRf({ ...rf, products: e.target.checked })} /> kéo lại 354 sản phẩm (~10 phút)</label>
        <button className="act" style={{ margin: 0 }} disabled={rb.running || !rb.credentials_set} onClick={runRobot}>Chạy robot ngay</button>
      </div>}
      {rb.log?.length > 0 && <details><summary className="muted">Nhật ký chạy ({rb.log.length})</summary><pre style={{ fontSize: 12, maxHeight: 220, overflow: "auto" }}>{rb.log.join("\n")}</pre></details>}
    </div>}
    {NAP_BU_VAI.includes(role) && <div className="panel"><h2>Nạp bù booking cho phiếu thu treo</h2>
      <p className="muted">Phiếu thu treo vì “chưa có booking” <b>không phải phiếu mồ côi</b> – mỗi phiếu đều mang mã booking của Vietrip, chỉ là VTOS chưa có booking ấy. Robot kéo booking theo NGÀY ĐẶT với cửa sổ 7 ngày, nên khách đặt tháng 3 mà trả tiền tháng 9 thì phiếu lọt lưới còn booking thì không. Cửa này <b>không truyền khoảng ngày nào</b> – nó lần theo đúng id mà những phiếu đang treo trỏ tới, nên lấy một booking tháng 3 để gắn khoản tiền trả tháng 9 <b>không phải</b> là nạp lại tháng 3 (Chủ tịch chốt phương án A, 26/9/2026).</p>
      <p className="muted">Bấm một lần là chạy nhiều lượt: mỗi lượt lật vài trang Vietrip rồi ánh xạ, lặp tới khi máy chủ báo xong. Dừng giữa chừng không mất phần đã lấy được – bấm lại là chạy tiếp.</p>
      <button className="act orange" style={{ margin: 0 }} disabled={nbChay} onClick={napBuBooking}>{nbChay ? "Đang chạy…" : "Nạp bù booking cho phiếu thu"}</button>
      {nb && <div className="kpis" style={{ marginTop: 8 }}>
        <div className="kpi"><b>{nb.tim_thay}</b><span>booking tìm thấy trên Vietrip{nb.can_tim != null && ` / ${nb.can_tim} cần tìm`}</span></div>
        <div className="kpi"><b>{nb.booking}</b><span>booking đã ánh xạ vào VTOS</span></div>
        <div className="kpi"><b>{nb.phieu}</b><span>phiếu thu đã gắn được</span></div>
        <div className="kpi"><b>{nb.con_treo ?? "—"}</b><span>phiếu CÒN treo</span></div>
      </div>}
      {nb && <div className="muted" style={{ marginTop: 6 }}>Đã chạy {nb.luot} lượt, lật {nb.trang} trang.{nb.dung_vi && ` Dừng vì: ${nb.dung_vi}.`}</div>}
    </div>}
    {["cntt", "ketoan"].includes(role) && <button className="act orange" onClick={apply}>Ánh xạ dữ liệu đã nạp vào VTOS</button>}
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 8 }}>{Object.entries(E).map(([k, l]) => <button key={k} className={"act " + (ent === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setEnt(k)}>{l}</button>)}
      <label><input type="checkbox" checked={unapplied} onChange={(e) => setUnapplied(e.target.checked)} /> chỉ bản ghi chưa ánh xạ</label></div>
    <div className="panel wrap"><table><thead><tr><th>Vietrip ID</th><th>Tham chiếu</th><th>Ngày</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Ánh xạ</th><th>Ghi chú</th><th>Đồng bộ lúc</th></tr></thead>
      <tbody>{rows.length ? rows.map((r) => <tr key={r.id}><td className="mono">{r.vietrip_id}</td><td>{r.ref}</td><td>{fmtD(r.on_date)}</td><td style={{ textAlign: "right" }}>{vnd(r.amount)}</td><td>{r.applied ? <Tag cls="ok">✔</Tag> : <Tag cls="warn">chưa</Tag>}</td><td className="muted">{r.apply_note}</td><td className="muted">{fmtDT(r.synced_at)}</td></tr>) : <tr><td colSpan={7} className="muted">Chưa có dữ liệu.</td></tr>}</tbody></table></div>
    <p className="muted">Cách 2 (thủ công): kịch bản <code>docs/vietrip-sync.js</code> trong repo – CNTT mở trang Vietrip đã đăng nhập, dán vào Console cùng token VTOS, chọn khoảng ngày; chạy lại bất kỳ lúc nào (không nhân bản).</p>
  </>);
}
export default function Page() { return <Shell><Vietrip /></Shell>; }
