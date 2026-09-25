"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, pct, fmtD, fmtDT, getToken, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const PMT: Record<string, [string, string]> = { UNPAID: ["Chưa cọc", "red"], DEPO: ["Đặt cọc", "warn"], PAID: ["Đã thanh toán", "ok"], CANCEL: ["Đã hủy", ""] };

function NonPackage() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [data, setData] = useState<any>({ kinds: {}, rows: [], summary: { by_type: [], total: {} } });
  const [month, setMonth] = useState(new Date().toISOString().slice(0, 7)); const [kind, setKind] = useState(""); const [paid, setPaid] = useState(""); const [q, setQ] = useState("");
  const [showForm, setShowForm] = useState(false); const [edit, setEdit] = useState<any>(null);
  const load = useCallback(() => api(`/non-package?month=${month}&service_type=${kind}&paid=${paid}&q=${encodeURIComponent(q)}`).then(setData).catch((e) => toast(errMsg(e), true)), [month, kind, paid, q, toast]);
  useEffect(() => { load(); }, [load]);
  // Đ-5 (13/9/2026) · phép soát tháng, ĐỌC từ chính booking và dòng chi phí đang có – không có sổ
  // thứ hai. Nó trả lời một câu mà màn hình này chưa hỏi bao giờ: dịch vụ nào có doanh thu mà
  // KHÔNG có một dòng giá vốn nào? Lãi của những dòng ấy đang bằng đúng toàn bộ số thu.
  const [soat, setSoat] = useState<any>(null);
  useEffect(() => {
    const [y, m] = month.split("-");
    api(`/quyet-toan-lop3/dich-vu-le/${y}/${Number(m)}`).then(setSoat).catch(() => setSoat(null));
  }, [month]);
  const canCreate = ["nv_kd", "gd_kd", "nv_dh", "tp_dh"].includes(role), isDH = ["nv_dh", "tp_dh"].includes(role);
  // Chủ tịch quyết 25/9/2026 – "gỡ quyền". Chốt tháng chỉ còn Kế toán: nút ấy vừa đóng số vừa ký
  // xác nhận kế toán trong một cú bấm. Giá vốn chỉ còn Điều hành và người điều hành của chính
  // dịch vụ ấy (với dịch vụ do Kinh doanh tạo thì đó là sale phụ trách).
  const canClose = role === "ketoan" || role === "chutich";
  // Giá vốn + nhà cung cấp: chỉ Phòng Điều hành. Phòng Kinh doanh LẺ gỡ hết, kể cả sale phụ trách
  // của chính dịch vụ ấy — họ vẫn XEM được số, chỉ không sửa. (Phòng Kinh doanh ĐOÀN không liên
  // quan tới màn hình này: quyền giá vốn của họ nằm trên chuyến đoàn, ở /tours.)
  const canCost = isDH || role === "chutich";
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); const f = e.target as HTMLFormElement; const d: any = Object.fromEntries(new FormData(f).entries());
    ["amount", "discount", "cost_amount"].forEach((k) => (d[k] = soTien(d[k]))); d.pax = Number(d.pax || 1); if (!d.service_date) delete d.service_date;
    if (!canCost) { delete d.cost_amount; delete d.supplier_name; }
    try { const r = await api("/non-package", { method: "POST", json: d }); toast(r.message); f.reset(); setShowForm(false); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    ["amount", "cost_amount"].forEach((k) => (d[k] = d[k] === "" ? undefined : Number(d[k]))); if (!d.service_date) delete d.service_date;
    // Ô giá vốn không hiện với người không được sửa, nên FormData không có nó – xoá cho chắc:
    // gửi kèm một ô mình không được ghi thì cả lần sửa tên khách cũng bị từ chối 403.
    if (!canCost) { delete d.cost_amount; delete d.supplier_name; }
    try { await api(`/non-package/${edit.id}`, { method: "PUT", json: d }); toast("Đã lưu dịch vụ"); setEdit(null); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const cancel = async (r: any) => { const reason = prompt(`Lý do hủy ${r.tour_code} – ${r.customer_name}?`); if (!reason) return; const ch = prompt(`Phí hủy giữ lại (đ), đã thu ${vnd(r.paid)} – để 0 nếu không thu phí:`, "0"); if (ch === null) return;
    try { const x = await api(`/bookings/${r.id}/cancel`, { method: "POST", json: { reason, charge: soTien(ch), retain: true } }); toast(x.message); load(); } catch (e) { toast(errMsg(e), true); } };
  const printIt = async (r: any) => { try { const res = await fetch(`/api/v1/non-package/${r.id}/print`, { headers: { Authorization: `Bearer ${getToken() || ""}` } }); const html = await res.text(); const w = window.open("", "_blank"); if (w) { w.document.write(html); w.document.close(); } } catch { toast("Không in được", true); } };
  const closeMonth = async () => { const m = prompt("Chốt dịch vụ lẻ tháng (YYYY-MM, phải là tháng đã kết thúc):", month); if (!m) return; try { const r = await api("/non-package/close-month", { method: "POST", json: { month: m } }); toast(r.message); load(); } catch (e) { toast(errMsg(e), true); } };
  const K = data.kinds || {}; const S = data.summary || {}; const T = S.total || {};
  return (<>
    <h1>Dịch vụ lẻ – Non-package</h1>
    <p className="muted">Bán visa, vé máy bay, khách sạn, xe, nhà hàng, land, HDV không gắn tour trọn gói – như màn hình Non-package của Vietrip: mỗi dịch vụ có mã KLEddmmyy, thu tiền theo mã booking (SePay/tiền mặt), in phiếu, hủy có phí → bảo lưu; Kế toán chốt tháng để ghi doanh thu – giá vốn.</p>
    <div className="kpis">
      <div className="kpi"><b>{T.n || 0}</b><span>Dịch vụ tháng {month}{T.cancelled ? ` · ${T.cancelled} hủy` : ""}</span></div>
      <div className="kpi"><b>{vnd(T.revenue)}</b><span>Doanh thu</span></div>
      <div className="kpi"><b>{vnd(T.paid)}</b><span>Đã thu · còn {vnd(T.due)}</span></div>
      <div className="kpi"><b>{vnd(T.cost)}</b><span>Giá vốn NCC</span></div>
      <div className="kpi"><b style={{ color: (T.profit || 0) < 0 ? "var(--red)" : undefined }}>{vnd(T.profit)}</b><span>Lợi nhuận</span></div>
    </div>
    <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
        <label>Tháng tạo<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></label>
        <label>Loại dịch vụ<select value={kind} onChange={(e) => setKind(e.target.value)}><option value="">Tất cả dịch vụ</option>{Object.entries(K).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Trạng thái TT<select value={paid} onChange={(e) => setPaid(e.target.value)}><option value="">Tất cả</option><option value="due">Còn phải thu</option><option value="paid">Đã thanh toán</option><option value="cancelled">Đã hủy</option></select></label>
        <label style={{ flex: 1, minWidth: 200 }}>Tìm<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="KLE… / khách / SĐT / nội dung" /></label>
        {canCreate && <button className="act teal" style={{ margin: 0 }} onClick={() => setShowForm(!showForm)}>+ Tạo dịch vụ lẻ</button>}
        {canClose && <button className="act grey" style={{ margin: 0 }} onClick={closeMonth}>Chốt tháng (Kế toán)</button>}
      </div>
      {showForm && <form onSubmit={submit} className="panel" style={{ marginTop: 8 }}><h2>Dịch vụ lẻ mới</h2>
        <div className="grid">
          <div><label>Loại dịch vụ *</label><select name="service_type" defaultValue="VISA">{Object.entries(K).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></div>
          <div><label>Nội dung dịch vụ *</label><input name="description" required placeholder="VD: Visa Mỹ B1/B2 · Vé SGN–BKK 12/10" /></div>
          <div><label>Quốc gia</label><input name="country" placeholder="MỸ / THÁI LAN…" /></div><div><label>Ngày sử dụng</label><input name="service_date" type="date" /></div>
          <div><label>Tên khách *</label><input name="customer_name" required /></div><div><label>SĐT *</label><input name="customer_phone" required /></div><div><label>Email</label><input name="customer_email" type="email" /></div>
          <div><label>Nguồn khách *</label><input name="source" required placeholder="Zalo / Facebook / Web / Khách cũ…" /></div><div><label>Số khách</label><input name="pax" type="number" min={1} defaultValue={1} /></div>
          <div><label>Giá dịch vụ (đ) *</label><input name="amount" type="number" step={1000} min={1} required /></div><div><label>Giảm giá (đ)</label><input name="discount" type="number" step={1000} defaultValue={0} /></div>
          {canCost
            ? <><div><label>Giá vốn NCC (đ)</label><input name="cost_amount" type="number" step={1000} defaultValue={0} /></div><div><label>Nhà cung cấp</label><input name="supplier_name" /></div></>
            : <div style={{ gridColumn: "span 2" }}><p className="muted">Giá vốn NCC và nhà cung cấp do <b>Phòng Điều hành</b> nhập sau
                (Chủ tịch quyết 25/9/2026). Ô để trống là <b>chưa có số</b>, không phải bằng 0 — dòng lãi lỗ của dịch vụ này
                chưa đọc được cho tới lúc ấy.</p></div>}
        </div>
        <label>Ghi chú chăm sóc</label><input name="note" />
        <button className="act teal" type="submit">Tạo dịch vụ</button> <button type="button" className="act grey" onClick={() => setShowForm(false)}>Đóng</button></form>}
      {edit && <form onSubmit={saveEdit} className="panel" style={{ marginTop: 8 }}><h2>Sửa {edit.tour_code} – {edit.customer_name}</h2>
        <div className="grid">
          <div><label>Loại dịch vụ</label><select name="service_type" defaultValue={edit.service_type}>{Object.entries(K).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></div>
          <div><label>Nội dung</label><input name="description" defaultValue={edit.description} /></div><div><label>Quốc gia</label><input name="country" defaultValue={edit.country} /></div>
          <div><label>Ngày sử dụng</label><input name="service_date" type="date" defaultValue={edit.service_date || ""} /></div>
          <div><label>Giá dịch vụ (đ)</label><input name="amount" type="number" step={1000} defaultValue={edit.amount} disabled={edit.locked} /></div>
          {canCost
            ? <><div><label>Giá vốn NCC (đ)</label><input name="cost_amount" type="number" step={1000} defaultValue={edit.cost_amount} /></div><div><label>Nhà cung cấp</label><input name="supplier_name" defaultValue={edit.supplier_name} /></div></>
            : <div style={{ gridColumn: "span 2" }}><label>Giá vốn NCC · nhà cung cấp</label>
                <p className="muted">{edit.cost_amount ? vnd(edit.cost_amount) : "chưa có — chờ Phòng Điều hành nhập"}{edit.supplier_name ? ` · ${edit.supplier_name}` : ""}
                  {" — "}Phòng Điều hành nhập ô này (Chủ tịch quyết 25/9/2026).</p></div>}
        </div>
        <button className="act teal" type="submit">Lưu</button> <button type="button" className="act grey" onClick={() => setEdit(null)}>Đóng</button></form>}
      <h2 style={{ marginTop: 10 }}>Danh sách dịch vụ Non-Package ({data.rows.length})</h2>
      <table><thead><tr><th>Mã</th><th>Sale</th><th>Khách</th><th>Dịch vụ</th><th>Nước · ngày</th><th className="num">Giá</th><th className="num">Đã thu</th><th className="num">Giá vốn</th><th className="num">LN</th><th>TT</th><th>Tạo</th><th></th></tr></thead>
        <tbody>{data.rows.length ? data.rows.map((r: any) => { const [pl, pc] = PMT[r.pmt_status] || [r.pmt_status, ""]; return <tr key={r.id} style={{ opacity: r.cancelled ? 0.55 : 1 }}>
          <td><b>{r.tour_code}</b><div className="muted">{r.code}{r.imported && " · Vietrip"}</div></td><td>{r.sales_name}</td>
          <td>{r.customer_name}<div className="muted">{r.customer_phone}{r.customer_email && ` · ${r.customer_email}`}</div>{r.cancelled && <div className="muted">Hủy: {r.cancel_reason}</div>}</td>
          <td><Tag cls="navy">{r.service_name}</Tag><div>{r.description}</div></td><td>{r.country}<div className="muted">{fmtD(r.service_date)}</div></td>
          <td className="num">{vnd(r.net)}</td><td className="num">{vnd(r.paid)}{r.due > 0 && !r.cancelled && <div><Tag cls="warn">còn {vnd(r.due)}</Tag></div>}</td><td className="num muted">{vnd(r.cost_amount)}{r.supplier_name && <div>{r.supplier_name}</div>}</td>
          <td className="num" style={{ color: r.profit < 0 ? "var(--red)" : undefined }}>{vnd(r.profit)}</td><td><Tag cls={pc}>{pl}</Tag>{r.locked && <div className="muted">🔒</div>}</td><td>{fmtDT(r.created_at)}</td>
          <td style={{ whiteSpace: "nowrap" }}>
            <Link href={`/tours/${r.tour_id}`}>chi tiết</Link>{" "}
            {/* Đ-5 (13/9/2026) · đường THẲNG tới ô nhập bốn khoản chi của dịch vụ này.
                Ô "Giá vốn NCC" ở biểu sửa bên trên chỉ là MỘT con số gộp – nó không tách được
                phí lãnh sự / phí dịch vụ visa / phí điều hành / phí dịch thuật, và không mang
                được ngoại tệ kèm tỷ giá ngày nộp hồ sơ. Bốn thứ ấy nhập ở chiết tính. */}
            <Link href={`/tours/${r.tour_id}?tab=lop3`} title="Nhập phí LSQ, phí dịch vụ visa, phí điều hành, phí dịch thuật – tách dòng, có ngoại tệ và tỷ giá">chiết tính</Link>{" "}
            <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => printIt(r)}>in phiếu</button>{" "}
            {!r.cancelled && ["da_duyet", "ket_thuc"].includes(r.tour_status) && (isDH || role === "gd_kd" || user?.full_name === r.sales_name) && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setEdit(r)}>sửa</button>}{" "}
            {!r.cancelled && isDH && ["da_duyet", "ket_thuc"].includes(r.tour_status) && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => cancel(r)}>hủy</button>}
          </td></tr>; }) : <tr><td colSpan={12} className="muted">Chưa có dịch vụ lẻ theo bộ lọc.</td></tr>}</tbody></table>
    </div>
    {(soat?.chan?.length > 0 || soat?.canh_bao?.length > 0) && (
      <div className="panel wrap">
        <h2>Soát tháng {month} – {soat.so_chan} chặn · {soat.so_canh_bao} cảnh báo</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Đọc từ chính booking và dòng chi phí của từng dịch vụ – không phải một sổ thứ hai. Bốn cột
          chi (phí LSQ · phí dịch vụ visa · phí điều hành · phí dịch thuật) lấy theo mã khoản mục;
          khoản không thuộc bốn mã ấy gom vào «Phí khác» để không con số nào biến mất.
        </p>
        {soat.chan.map((c: any, i: number) => (
          <div key={`c${i}`} className="gate fail"><b>CHẶN – </b>{c.vi_sao} {c.can_lam}</div>
        ))}
        {soat.canh_bao.map((c: any, i: number) => (
          <div key={`w${i}`} className="gate warn">{c.vi_sao} {c.can_lam}</div>
        ))}
      </div>
    )}
    {S.by_type?.length > 0 && <div className="panel wrap"><h2>Tổng hợp theo loại dịch vụ – tháng {month}</h2>
      <table><thead><tr><th>Loại</th><th className="num">Số DV</th><th className="num">Doanh thu</th><th className="num">Đã thu</th><th className="num">Giá vốn</th><th className="num">Lợi nhuận</th><th className="num">Biên</th></tr></thead>
        <tbody>{S.by_type.map((d: any) => <tr key={d.service_type}><td>{d.service_name}</td><td className="num">{d.n}</td><td className="num">{vnd(d.revenue)}</td><td className="num">{vnd(d.paid)}</td><td className="num">{vnd(d.cost)}</td><td className="num"><b>{vnd(d.profit)}</b></td><td className="num">{pct(d.margin)}</td></tr>)}</tbody></table></div>}
  </>);
}

export default function Page() { return <Shell><NonPackage /></Shell>; }
