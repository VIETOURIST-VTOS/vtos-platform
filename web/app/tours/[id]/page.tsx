"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT, getToken, soTien } from "@/lib/api";
import { ROLES, TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, Gate, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";
import QuyetToanForm from "@/components/QuyetToanForm";

// Đ-1 (12/9/2026) · tab "lop3" là CỬA còn thiếu của cả phân hệ quyết toán lớp 3.
//
// Máy chủ đã có 22 đường /api/v1/quyet-toan-lop3 và components/QuyetToanForm.tsx đã viết xong đủ sáu
// khối nhập – nhưng KHÔNG TRANG NÀO import nó. Tức là có phép tính mà không có cửa, đúng thứ ranh
// giới Chủ tịch chốt 09/9 gọi là "việc còn thiếu".
//
// GẮN VÀO ĐÂY chứ không dựng trang /quyet-toan riêng: access.py đã ghi rõ quyết định 11/9 – menu đã
// có mục "Quyết toán tour" trỏ vào /tours, và thêm một lối vào thứ hai cho cùng một việc là cách
// chắc chắn để người dùng không biết nên bấm vào đâu. Nhờ vậy cũng không phải khai thêm dòng nào
// trong MENU_ROLES hay MAN_HINH_API: tiền tố /api/v1/quyet-toan-lop3 đã nằm sẵn dưới /tours.
const TABS: [string, string][] = [["info", "Thông tin & quy trình"], ["budget", "Dự toán 3 con số"], ["bookings", "Booking & thu tiền"], ["cost", "Chi NCC & quyết toán"], ["lop3", "Quyết toán chi tiết"], ["ops", "HDV & xe"], ["history", "Quy trình & lịch sử"]];
const PR_ST: Record<string, string> = { cho_tp: "Chờ TP", cho_kt: "Chờ Kế toán", cho_duyet: "Chờ duyệt", cho_chi: "Chờ chi", da_chi: "Đã chi", tu_choi: "Từ chối", huy: "Hủy" };

function TourDetail() {
  const { id } = useParams<{ id: string }>();
  const { user, toast } = useShell();
  const [t, setT] = useState<any>(null);
  // Đ-5 (13/9/2026) · nhận ?tab=... để màn hình khác trỏ THẲNG vào đúng tab.
  //
  // Màn hình /non-package cần đưa người dùng tới ô nhập chi phí của một dịch vụ lẻ. Trước đây nó
  // chỉ có được một liên kết "chi tiết" mở ra tab Thông tin, rồi người dùng phải tự tìm tiếp — và
  // trên thực tế họ không tìm, họ quay ra Excel. Đó cũng chính là bệnh Đ-1: có cửa mà không ai
  // thấy đường vào thì bằng không có cửa.
  const sp = useSearchParams();
  const [tab, setTab] = useState(sp.get("tab") || "info");
  const [note, setNote] = useState("");
  const load = useCallback(() => api(`/tours/${id}/detail`).then(setT).catch((e) => toast(errMsg(e), true)), [id, toast]);
  useEffect(() => { load(); }, [load]);
  if (!t) return <p className="muted">Đang tải…</p>;
  // Ba bậc, và máy chủ nói thẳng bậc nào — KHÔNG suy quyền từ hình dạng dữ liệu nữa. Từ 25/9/2026
  // Kinh doanh Lẻ nhận `calc` CÓ mà giá vốn KHÔNG, nên phép đoán cũ (`t.calc != null`) sẽ bày ra
  // tab "Chi NCC & quyết toán" rỗng cho đúng người không được xem nó.
  const xemGiaVon = t.xem_gia_von ?? (t.calc != null);   // ?? : bản máy chủ cũ chưa gửi cờ
  const xemDuToan = t.xem_du_toan ?? (t.calc != null);
  const c = t.calc || {}, s = t.settlement, act: string[] = t.actions || [], sm = t.summary || {};
  // Lớp 3 đi cùng nhóm với dự toán và chi NCC: ai không xem được cơ cấu chi phí thì cũng không mở
  // được tab này. Hàng rào THẬT vẫn nằm ở máy chủ (danh sách XEM trong api/v1/quyet_toan_lop3.py);
  // đây chỉ là chuyện không bày ra một cái tab bấm vào sẽ báo lỗi quyền.
  const tabs = TABS.filter(([k]) => k === "budget" ? xemDuToan : !["cost", "lop3"].includes(k) || xemGiaVon);
  const can = (a: string) => act.includes(a);
  const run = async (path: string, json?: any) => { try { const r = await api(`/tours/${t.id}/${path}`, { method: "POST", json: { note, ...(json || {}) } }); toast(r.message); setNote(""); load(); } catch (e) { toast(errMsg(e), true); } };
  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    ["price_per_pax", "fixed_cost", "var_cost_per_pax", "hoa_hong_khach_tien"].forEach((k) => (d[k] = soTien(d[k])));
    d.planned_pax = Number(d.planned_pax || 0);
    try { await api(`/tours/${t.id}`, { method: "PUT", json: d }); toast("Đã lưu dự toán"); load(); } catch (x) { toast(errMsg(x), true); }
  };
  // `fixed_cost` RỖNG phải đi lên máy chủ là null, KHÔNG phải 0: `soTien("")` trả 0, và 0 ở đây
  // nghĩa là "chuyến này không còn chi phí cố định nào" — cổng lợi nhuận sẽ cho qua nhầm.
  const moThemCho = async (e: React.FormEvent) => {
    e.preventDefault(); const f = e.target as HTMLFormElement;
    const d: any = Object.fromEntries(new FormData(f).entries());
    const fc = String(d.fixed_cost || "").trim();
    try {
      const r = await api(`/tours/${t.id}/mo-them-cho`, { method: "POST", json: {
        so_cho: Number(d.so_cho || 0), fixed_cost: fc === "" ? null : soTien(fc), ly_do: String(d.ly_do || "") } });
      toast(r.message); f.reset(); load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const closeTour = async (e: React.FormEvent) => {
    e.preventDefault(); const d: any = Object.fromEntries(new FormData(e.target as HTMLFormElement).entries());
    run("close", { actual_revenue: soTien(d.actual_revenue), actual_cost: soTien(d.actual_cost), promo_value: soTien(d.promo_value) });
  };
  const bookedAmount = sm.revenue_booking || 0;
  const NoteBox = () => <label>Lời giải trình / ghi chú cho bước này (hiển thị ở Quy trình & lịch sử)<input value={note} onChange={(e) => setNote(e.target.value)} placeholder="VD: khách ít nên biên thấp, nhờ anh duyệt…" /></label>;
  return (<>
    <p><Link href="/tours">← Danh sách tour</Link>{t.product && <> · Sản phẩm <Link href="/products">{t.product.code}</Link></>}</p>
    <h1>{t.code} · {t.name} <Tag cls="navy">{TOUR_TYPES[t.tour_type]}</Tag> {t.below_margin && <Tag cls="warn">dưới biên</Tag>} {t.imported && <Tag>Vietrip</Tag>}</h1>
    <p className="muted">{fmtD(t.start_date)} → {fmtD(t.end_date)} · {t.days || ""} ngày · {t.transport} {t.vehicle_type} · KH {t.departure_point} · Điều hành <b>{t.operator_name}</b> · Trạng thái <b>{TOUR_STATUS[t.status]}</b> · Hạn quyết toán <b>{fmtD(t.settlement_deadline)}</b></p>
    <div className="kpis">
      <div className="kpi"><b>{t.seats.booked}/{t.seats.open || t.planned_pax}</b><span>Đã bán / mở bán · còn {t.seats.left}</span></div>
      <div className="kpi"><b>{vnd(bookedAmount)}</b><span>Doanh thu booking</span></div>
      <div className="kpi"><b>{vnd(sm.collected)}</b><span>Đã thu</span></div>
      {/* Hai ô này dựng trên chi phí THỰC TẾ — cùng loại thông tin với dòng NCC, chỉ ở dạng cộng
          gộp. Kinh doanh Lẻ không nhận chúng từ máy chủ, nên đừng vẽ ô rỗng: họ đọc lợi nhuận KẾ
          HOẠCH ở tab "Dự toán 3 con số". */}
      {xemGiaVon && <>
        <div className="kpi"><b>{vnd(sm.cost_actual)}</b><span>Chi phí đã ghi nhận{sm.cost_lines ? ` (${sm.cost_lines} dòng quyết toán)` : sm.cost_basis === "tong_hop_vietrip" ? " (tổng hợp Vietrip)" : " (chưa có dòng nào)"}</span></div>
        <div className="kpi">{sm.cost_basis === "chua_co"
          ? <><b className="muted">–</b><span>Chưa tính được lợi nhuận (chưa ghi nhận chi phí nào)</span></>
          : <><b style={{ color: sm.profit < 0 ? "var(--red)" : undefined }}>{vnd(sm.profit)}</b><span>{sm.profit_state === "xac_nhan" ? "Lợi nhuận đã xác nhận" : "Lợi nhuận tạm tính"}</span></>}</div>
      </>}
      {!xemGiaVon && xemDuToan && c.complete && <div className="kpi"><b>{vnd(c.profit)}</b><span>Lợi nhuận kế hoạch · biên {pct(c.margin)}</span></div>}
    </div>
    {sm.warning && <Gate ok={false}>{sm.warning}</Gate>}
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{tabs.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}</div>

    {tab === "info" && <div className="grid">
      <div className="panel"><h2>Thông tin tour</h2>
        <table><tbody>
          <tr><td>Mã tour / sản phẩm</td><td><b>{t.code}</b> · {t.product_code || "–"}</td></tr>
          <tr><td>Khởi hành – kết thúc</td><td>{fmtD(t.start_date)} – {fmtD(t.end_date)}</td></tr>
          <tr><td>Số chỗ mở bán / khuyến mãi</td><td>{t.seats.open} / {t.seats.promo}</td></tr>
          <tr><td>Giá ADL / CHD / INF / KM</td><td>{vnd(t.prices.adl)} / {vnd(t.prices.chd)} / {vnd(t.prices.inf)} / {vnd(t.prices.promo)}</td></tr>
          <tr><td>Người điều hành duy nhất</td><td>{t.operator_name}</td></tr>
          <tr><td>Điểm dừng nghỉ</td><td>{t.rest_stops || "–"}</td></tr>
          <tr><td>Duyệt</td><td>{t.confirmed_by && `TP ĐH: ${t.confirmed_by}`} {t.approved_by && `· ${t.approved_by}`} {t.chairman_run_decision}</td></tr>
        </tbody></table>
        {t.product?.program && <details><summary>Chương trình tour (từ sản phẩm)</summary><pre style={{ whiteSpace: "pre-wrap", fontSize: 12 }}>{t.product.program}</pre></details>}
      </div>
      <div className="panel"><h2>Luồng phê duyệt</h2>
        {/* Bước Kinh doanh Đoàn soạn — Chủ tịch quyết 24/9/2026. Cổng của Sale Admin là cổng CHẶN
            duy nhất của vị trí ấy (Phần V bản mô tả), nên nó phải là hai cái nút thật ở đây, chứ
            không phải một dòng nhắc. Sale Admin KHÔNG có nút duyệt — và không bao giờ có. */}
        {t.status === "nhap_kd" && <>
          <p>Dự toán đang ở bước <b>Kinh doanh Đoàn soạn</b>. Sale Admin soát rồi chuyển sang Phòng Điều hành,
            hoặc trả lại nhân viên phụ trách kèm ghi rõ thiếu gì.</p>
          {can("edit") && <p className="muted">Sửa dự toán ở tab <b>Dự toán 3 con số</b>.</p>}
          {can("chuyen_dieu_hanh") && <>
            <NoteBox />
            <button className="act teal" onClick={() => run("chuyen-dieu-hanh")}>Chuyển Phòng Điều hành</button>
            <button className="act grey" onClick={() => run("tra-lai-kinh-doanh")}>Trả lại Kinh doanh (ghi rõ lý do)</button>
            <p className="muted">Trả lại phải ghi lý do tối thiểu 20 ký tự vào ô trên — trả lại mà không nói thiếu gì
              thì người nhận lại hồ sơ phải đoán.</p>
          </>}
        </>}
        {t.status === "nhap" && (can("edit") ? <p className="muted">Sửa dự toán ở tab <b>Dự toán 3 con số</b> rồi bấm Trình.</p> : <p className="muted">Chỉ người điều hành chuyến ({t.operator_name}) hoặc TP Điều hành sửa được dự toán.</p>)}
        {t.status === "nhap" && can("submit") && <><NoteBox /><button className="act teal" onClick={() => run("submit")}>Trình Trưởng phòng Điều hành</button></>}
        {t.status === "cho_xac_nhan" && <><p>Chờ Trưởng phòng Điều hành xác nhận.</p>{can("confirm") && <><NoteBox /><button className="act teal" onClick={() => run("confirm")}>Xác nhận dự toán</button></>}</>}
        {t.status === "cho_duyet" && (t.below_margin ? <>
          <p>Chuyến dưới biên – cần đủ 2 chữ ký: Chủ tịch {t.signed_chutich ? "✔" : "…"} · TGĐ {t.signed_tgd ? "✔" : "…"}</p>
          <div className="gate"><b>Giải trình:</b> {t.justification}</div>
          {can("sign") && <><NoteBox /><button className="act orange" onClick={() => run("approve")}>Ký duyệt ({user?.role_name})</button></>}
        </> : <><p>Chờ <b>{ROLES[t.approver_role]}</b> duyệt.</p>{can("approve") && <><NoteBox /><button className="act teal" onClick={() => run("approve")}>Duyệt dự toán</button></>}</>)}
        {t.status === "da_duyet" && <p>Đã duyệt. Kinh doanh gửi yêu cầu, Điều hành tạo booking tại <Link href="/requests">Yêu cầu & booking</Link>.</p>}
        {/* CỬA MỞ THÊM CHỖ — Chủ tịch quyết 25/9/2026. Trước hôm nay `giu_cho.gia_han` bảo người
            dùng "Điều hành phải mở thêm chỗ" trong khi không có cửa nào làm việc ấy; đây là cửa.
            Ô chi phí cố định để TRỐNG nghĩa là KHÔNG ĐỔI, không phải bằng 0 — nói ra ngay dưới ô,
            vì một ô tiền để trống bị hiểu thành 0 thì cổng lợi nhuận sẽ cho qua nhầm. */}
        {t.status === "da_duyet" && can("mo_them_cho") && <details style={{ marginTop: 10 }}>
          <summary><b>Mở thêm chỗ trên chuyến đang bán</b></summary>
          <form onSubmit={moThemCho}>
            <label>Số chỗ mở bán MỚI (đang là {t.seats.open || t.planned_pax})
              <input name="so_cho" type="number" min={(t.seats.open || t.planned_pax || 0) + 1} required /></label>
            <label>Chi phí cố định mới (đ) — để TRỐNG nếu không đổi
              <input name="fixed_cost" placeholder="VD: đổi xe 29 chỗ sang 45 chỗ thì gõ số mới" /></label>
            <label>Vì sao mở thêm (tối thiểu 20 ký tự)
              <input name="ly_do" required minLength={20} placeholder="VD: khách đoàn xin thêm 6 người, đã xác nhận xe 45 chỗ…" /></label>
            <button className="act teal" type="submit">Mở thêm chỗ</button>
            <p className="muted">Số chỗ nằm trong dự toán đã ký. Cửa này tính lại lợi nhuận và biên với số chỗ mới:
              <b> tụt một trong hai là chặn</b>, kể cả khi con số kia tăng.</p>
          </form>
        </details>}
        {t.d7_flag && <>
          <Gate ok={false}>CỔNG 8 – Mốc D-7: {t.booked_pax}/{c.breakeven_pax} khách hòa vốn → ghép/dời/hủy; chạy tiếp cần Chủ tịch. {t.chairman_run_decision && <b>{t.chairman_run_decision}</b>}</Gate>
          {can("d7") && <><NoteBox /><button className="act grey" onClick={() => run("d7", { decision: "ghep" })}>Ghép</button><button className="act grey" onClick={() => run("d7", { decision: "doi" })}>Dời</button><button className="act red" onClick={() => run("d7", { decision: "huy" })}>Hủy</button>{user?.role === "chutich" && <button className="act orange" onClick={() => run("d7", { decision: "chay" })}>Chủ tịch duyệt chạy</button>}</>}
        </>}
        {t.status === "huy" && <p>{t.chairman_run_decision}</p>}
        {can("close") && <><h3>Đóng số quyết toán · một cửa · hạn {fmtD(t.settlement_deadline)} {new Date().toISOString().slice(0, 10) > t.settlement_deadline && <Tag cls="red">ĐÃ QUÁ HẠN</Tag>}</h3>
          <form onSubmit={closeTour}><div className="grid">
            <div><label>Doanh thu thực tế (đ)</label><input type="number" name="actual_revenue" step="1000" defaultValue={Math.round(t.actual_revenue || bookedAmount)} required /></div>
            <div><label>Giá vốn thực tế (đ){t.settlement_edit?.summary?.lines > 0 && <span className="muted"> – lấy từ {t.settlement_edit.summary.lines} dòng NCC ở tab Chi NCC & quyết toán</span>}</label><input type="number" name="actual_cost" step="1000" defaultValue={Math.round(t.settlement_edit?.summary?.lines > 0 ? t.settlement_edit.summary.actual : (sm.cost_actual || t.fixed_cost + t.var_cost_per_pax * t.booked_pax))} readOnly={t.settlement_edit?.summary?.lines > 0} required /></div>
            <div><label>Giảm giá / mã KM (đ)</label><input type="number" name="promo_value" step="1000" defaultValue={0} /></div>
          </div><NoteBox /><button className="act teal">Đóng số → Kế toán</button></form></>}
        {can("kt_confirm") && <><NoteBox /><button className="act teal" onClick={() => run("kt-confirm")}>Kế toán xác nhận (3 ngày làm việc)</button> <button className="act grey" onClick={() => run("kt-return")}>Trả lại Điều hành sửa (ghi lý do)</button></>}
        {can("cntt_check") && <><NoteBox /><button className="act teal" onClick={() => run("cntt-check")}>CNTT đối chiếu độc lập & khóa</button></>}
        {s && <><h3>Quyết toán và quỹ thưởng</h3><table><tbody>
          <tr><td>Doanh thu thực tế</td><td className="num">{vnd(s.revenue)}</td><td>Đóng số</td><td>{fmtDT(t.closed_at)} · {s.on_time ? "đúng hạn" : <b>QUÁ HẠN</b>}</td></tr>
          <tr><td>Giá vốn thực tế</td><td className="num">{vnd(s.cost)}</td><td>Kế toán xác nhận</td><td>{fmtDT(t.kt_confirmed_at)}</td></tr>
          <tr><td>Lợi nhuận / biên</td><td className="num"><b>{vnd(s.profit)} · {pct(s.margin)}</b></td><td>CNTT khóa</td><td>{fmtDT(t.cntt_checked_at)}</td></tr>
          <tr><td>Quỹ thưởng Điều hành ({pct(s.rate)})</td><td className="num"><b>{vnd(s.fund)}</b></td><td>NV 70% / TP 30%</td><td className="num">{vnd(s.fund_nv)} / {vnd(s.fund_tp)}</td></tr>
        </tbody></table>{!s.eligible && <Gate ok={false}>Không phát sinh quỹ thưởng: {!s.on_time ? "quá hạn quyết toán" : t.below_margin ? "chuyến duyệt chạy dưới biên" : "biên thực tế dưới ngưỡng"}.</Gate>}</>}
      </div>
    </div>}

    {tab === "budget" && <div className="grid">
      <div className="panel"><h2>Ba con số dự toán (ĐH Điều 2, 11)</h2>
        <table><tbody>
          <tr><td>Số khách dự toán</td><td className="num"><b>{t.planned_pax}</b></td></tr>
          <tr><td>Số khách hòa vốn</td><td className="num"><b>{c.breakeven_pax ?? "–"}</b></td></tr>
          <tr><td>Số khách đạt biên {pct(c.threshold)}</td><td className="num"><b>{c.pax_for_margin ?? "–"}</b></td></tr>
          <tr><td>Doanh thu kế hoạch</td><td className="num">{vnd(c.revenue)}</td></tr>
          <tr><td>Giá vốn kế hoạch (cố định {vnd(c.fixed_cost)} + {vnd(c.var_cost_per_pax)}/khách)</td><td className="num">{c.has_cost ? vnd(c.cost) : <span className="muted">chưa có</span>}</td></tr>
          <tr><td>Lợi nhuận / biên kế hoạch</td><td className="num">{c.complete ? <>{vnd(c.profit)} · <b>{pct(c.margin)}</b></> : <span className="muted">chưa đủ cơ sở tính</span>}</td></tr>
        </tbody></table>
        <Gate ok={c.gate_state === "chua_du_co_so" ? null : c.pass_gate}>CỔNG 1 – Biên {pct(c.threshold)}: {c.gate_state === "chua_du_co_so"
          ? "CHƯA ĐỦ CƠ SỞ TÍNH – dự toán thiếu giá vốn. Thiếu chi phí không phải là chi phí bằng 0: cổng không thể ĐẠT khi chưa có giá vốn."
          : c.pass_gate ? `ĐẠT → ${ROLES[t.approver_role]} duyệt` : "KHÔNG ĐẠT → giải trình + 2 chữ ký Chủ tịch và TGĐ"}</Gate>
        <p className="muted">Nguồn dự toán: <b>{c.budget_source_label}</b>{c.reference_only && " – chuyến chưa có dự toán riêng; số lấy từ cơ cấu chi phí sản phẩm chỉ để tham chiếu và KHÔNG dùng để mở cổng biên"}</p>
        {t.product && <p className="muted">Cơ cấu chi phí sản phẩm {t.product.code}: cố định {vnd(t.product.fixed_cost)} · theo khách {vnd(t.product.var_cost_per_pax)} · giá tham khảo {vnd(t.product.reference_price)}</p>}
      </div>
      <div className="panel"><h2>Sửa dự toán</h2>
        {/* `nhap_kd` là bước Kinh doanh Đoàn soạn (24/9/2026). Trước đây ô này chỉ mở ở `nhap`,
            nên quyền sửa đã mở ở máy chủ mà trên màn hình không có ô nào để gõ. */}
        {["nhap", "nhap_kd"].includes(t.status) && can("edit") ? <form onSubmit={saveEdit}>
          <div className="grid"><div><label>Giá bán/khách</label><input type="number" name="price_per_pax" defaultValue={t.price_per_pax} step="1000" /></div><div><label>Chi phí cố định</label><input type="number" name="fixed_cost" defaultValue={t.fixed_cost} step="1000" /></div>
            <div><label>Chi phí theo khách</label><input type="number" name="var_cost_per_pax" defaultValue={t.var_cost_per_pax} step="1000" /></div><div><label>Số khách dự toán</label><input type="number" name="planned_pax" defaultValue={t.planned_pax} /></div></div>
          <label>Điểm dừng nghỉ{t.status === "nhap_kd" ? " (Điều hành điền ở bước sau)" : " (bắt buộc)"}</label><input name="rest_stops" defaultValue={t.rest_stops} />
          {t.is_doan && <>
            <label>Đoàn này có hoa hồng dành cho khách không? (bắt buộc – Chủ tịch quyết 24/9/2026)</label>
            <select name="hoa_hong_khach" defaultValue={t.hoa_hong_khach || ""}>
              <option value="">— chưa trả lời —</option><option value="khong">Không</option><option value="co">Có</option>
            </select>
            <label>Số tiền hoa hồng dành cho khách (đ) – chỉ điền khi chọn Có</label>
            <input type="number" name="hoa_hong_khach_tien" step="1000" defaultValue={t.hoa_hong_khach_tien || 0} />
          </>}
          <label>Giải trình chuyến dưới biên (4 mục) – bắt buộc khi biên &lt; {pct(c.threshold)}</label><textarea name="justification" defaultValue={t.justification} />
          <button className="act grey" type="submit">Lưu dự toán</button>
        </form> : <p className="muted">Dự toán đã trình – không sửa ({TOUR_STATUS[t.status]}).</p>}
        {t.is_doan && <>
          <h3>Hoa hồng dành cho khách</h3>
          {!t.hoa_hong_khach
            ? <Gate ok={false}>CHƯA TRẢ LỜI. Sale Admin không chuyển được dự toán này sang Điều hành cho tới khi có câu trả lời.</Gate>
            : t.hoa_hong_khach === "khong"
              ? <p className="muted">Đã khai: <b>không có</b> hoa hồng dành cho khách.</p>
              : <table><tbody>
                <tr><td>Đã khai</td><td className="num"><b>{vnd(t.hoa_hong_khach_tien)}</b></td></tr>
                <tr><td>Biên kế hoạch theo giá vốn đã nhập</td><td className="num"><b>{pct(c.margin)}</b></td></tr>
                <tr><td>Biên <i>nếu khoản này chưa nằm trong giá vốn ấy</i></td>
                  <td className="num">{t.hoa_hong_khach_bien?.bien_neu_chua_vao != null
                    ? <b style={{ color: "var(--red)" }}>{pct(t.hoa_hong_khach_bien.bien_neu_chua_vao)}</b>
                    : <span className="muted">–</span>}</td></tr>
              </tbody></table>}
          {t.hoa_hong_khach === "co" && <p className="muted">Con số thứ hai là một <b>cận dưới</b>, không phải một khẳng định:
            phần mềm không biết khoản hoa hồng này có thật sự nằm trong giá vốn đã nhập hay không. Nó đặt hai con số cạnh
            nhau để người ký tự hỏi — và để người khai phải khai.</p>}
        </>}
      </div>
    </div>}

    {tab === "bookings" && <>
      <div className="panel wrap"><h2>Booking ({t.bookings.length}) · doanh thu {vnd(bookedAmount)} · đã thu {vnd(sm.collected)}</h2>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Nguồn</th><th className="num">ADL/CHD/INF</th><th className="num">Tiền</th><th className="num">Đã thu</th><th className="num">Còn lại</th><th>TT</th><th>Sale</th><th>Chỉ tiêu</th></tr></thead>
          <tbody>{t.bookings.length ? t.bookings.map((b: any) => <tr key={b.id} style={{ opacity: b.cancelled ? 0.5 : 1 }}><td>{b.code}{b.cancelled && <Tag cls="red">hủy</Tag>}</td><td>{b.customer_name} · {b.customer_phone}</td><td>{b.source}</td><td className="num">{b.adl}/{b.chd}/{b.inf}</td><td className="num">{vnd(b.amount - b.discount)}</td><td className="num">{vnd(b.paid)}</td><td className="num">{b.due > 0 ? <Tag cls="warn">{vnd(b.due)}</Tag> : <Tag cls="ok">Đủ</Tag>}</td><td>{b.pmt_status}</td><td>{b.sales_name}</td><td>{b.counts_for_target ? "có" : "không"}</td></tr>) : <tr><td colSpan={10} className="muted">Chưa có booking.</td></tr>}</tbody></table></div>
      <div className="panel wrap"><h2>Phiếu thu ({t.receipts.length})</h2>
        <table><thead><tr><th>Số PT</th><th>Booking</th><th className="num">Số tiền</th><th>Hình thức</th><th>Người nộp</th><th>Trạng thái</th><th>Lúc</th><th>Xác nhận</th></tr></thead>
          <tbody>{t.receipts.map((r: any) => <tr key={r.id}><td>{r.code}</td><td>{r.booking_code}</td><td className="num">{vnd(r.amount)}</td><td>{r.method === "tien_mat" ? "Tiền mặt" : "CK"}</td><td>{r.payer}</td><td>{r.status}</td><td>{fmtDT(r.created_at)}</td><td>{r.confirmed_by}</td></tr>)}</tbody></table></div>
    </>}

    {tab === "cost" && <>
      <div className="panel wrap"><h2>Đề nghị chi / lệnh chi NCC ({t.payment_requests.length}) · đã chi {vnd(sm.cost_paid)}</h2>
        <table><thead><tr><th>Mã</th><th>NCC</th><th>Nội dung</th><th className="num">Số tiền</th><th>Trạng thái</th><th>Lập</th><th>Chi</th></tr></thead>
          <tbody>{t.payment_requests.map((r: any) => <tr key={r.id}><td>{r.code}</td><td>{r.supplier_name}</td><td>{r.description}</td><td className="num">{vnd(r.amount)}</td><td><Tag cls={r.status === "da_chi" ? "ok" : "warn"}>{PR_ST[r.status] || r.status}</Tag></td><td>{fmtDT(r.created_at)}</td><td>{fmtDT(r.paid_at)}</td></tr>)}</tbody></table></div>
      <Settlement t={t} note={note} NoteBox={NoteBox} run={run} load={load} toast={toast} />
    </>}

    {tab === "lop3" && <QuyetToanForm tourId={t.id} toast={toast} />}

    {tab === "ops" && <div className="grid">
      <div className="panel wrap"><h2>Phân công HDV</h2><table><thead><tr><th>HDV</th><th>Ngày × đơn giá</th><th className="num">Thù lao</th><th>Trạng thái</th></tr></thead>
        <tbody>{t.guides.length ? t.guides.map((a: any) => <tr key={a.id}><td>{a.guide}</td><td>{a.days} × {vnd(a.rate_per_day)}{a.holiday && " ×2"}</td><td className="num">{vnd(a.amount)}</td><td>{a.status}</td></tr>) : <tr><td colSpan={4} className="muted">Chưa phân công – tab Nhân sự › HDV & phân chuyến.</td></tr>}</tbody></table></div>
      <div className="panel wrap"><h2>Lệnh điều xe</h2><table><thead><tr><th>Xe</th><th>Tài xế</th><th>Từ – đến</th><th className="num">Giá nội bộ</th><th>Trạng thái</th></tr></thead>
        <tbody>{t.dispatch.length ? t.dispatch.map((d: any) => <tr key={d.id}><td>{d.plate}</td><td>{d.driver}</td><td>{fmtD(d.date_from)} – {fmtD(d.date_to)}</td><td className="num">{vnd(d.internal_price)}</td><td>{d.status}</td></tr>) : <tr><td colSpan={5} className="muted">Chưa có lệnh điều xe – tab Nhân sự › Đội xe.</td></tr>}</tbody></table></div>
    </div>}

    {/* Ô đính kèm cho TOUR. Máy chủ khai "tour" là đối tượng gắn được tệp từ đầu (nhóm 05_Tour, lưu theo mã
        tour), nhưng đến 09/9/2026 không màn hình nào dựng ô ấy. Chương trình tour đã gửi khách, hợp đồng
        đoàn, xác nhận dịch vụ, biên bản sự cố – tất cả đều gắn với MỘT mã tour và đều là thứ phải lôi ra
        được khi quyết toán bị hỏi lại. Không có chỗ để nằm thì chúng nằm trong hộp thư của người điều hành.

        Đặt ở tab Quy trình & lịch sử chứ không ở tab Thông tin: đây là hồ sơ của chuyến, cùng chỗ với các
        bước đã đi qua, chứ không phải một thuộc tính của tour. */}
    {tab === "history" && <DinhKem doiTuong="tour" doiTuongId={t.code}
                                   tieuDe={`Hồ sơ tour ${t.code}`} />}

    {tab === "history" && <>
      <div className="panel"><h2>Quy trình & lịch sử</h2>
        {t.events.length ? t.events.map((e: any) => <div key={e.id} style={{ borderLeft: "3px solid " + (e.source === "vietrip" ? "var(--vtos-text-faint)" : "var(--teal)"), padding: "4px 10px", marginBottom: 8 }}>
          <b>{e.title}</b> {e.source === "vietrip" && <Tag>Vietrip</Tag>}<div className="muted">{fmtDT(e.at)} · {e.actor}</div>{e.note && <div style={{ background: "var(--panel2, #f4f6f8)", padding: 6, borderRadius: 6, marginTop: 4 }}>{e.note}</div>}
        </div>) : <p className="muted">Chưa có bước nào được ghi.</p>}
      </div>
      <div className="panel wrap"><h2>Nhật ký bất biến (hash-chain)</h2>
        <table><thead><tr><th>Lúc</th><th>Ai</th><th>Hành động</th><th>Trước → sau</th></tr></thead>
          <tbody>{(t.audit || []).map((l: any) => <tr key={l.id}><td>{fmtDT(l.ts)}</td><td>{l.actor}</td><td>{l.action}</td><td className="muted mono">{l.before ? JSON.stringify(l.before) + " → " : ""}{JSON.stringify(l.after || "")}</td></tr>)}</tbody></table></div>
    </>}
  </>);
}
const EMPTY = { description: "", service_type: "HOTEL", cost_kind: "theo_khach", supplier_name: "", supplier_tax_code: "", unit_price: 0, qty: 0, coef: 1, budget: 0, note: "", tien_te: "", so_tien_goc: 0, ty_gia: 0, ngay_ty_gia: "" };
// Danh sách ĐỒNG TIỀN chỉ để GỢI Ý, không để chặn — `models/ty_gia.py` nói rõ: gặp đồng tiền lạ
// mà chặn là đẩy người dùng sang gõ tay ra ngoài hệ. Nên ô cuối là "khác…" cho gõ tự do.
const DONG_TIEN: [string, string][] = [["", "VND (tiền đồng)"], ["USD", "USD – Đô la Mỹ"], ["EUR", "EUR – Euro"],
  ["THB", "THB – Baht Thái"], ["SGD", "SGD – Đô la Singapore"], ["JPY", "JPY – Yên Nhật"], ["KRW", "KRW – Won Hàn"],
  ["CNY", "CNY – Nhân dân tệ"], ["AUD", "AUD – Đô la Úc"], ["GBP", "GBP – Bảng Anh"], ["CAD", "CAD – Đô la Canada"],
  ["TWD", "TWD – Đô la Đài Loan"], ["HKD", "HKD – Đô la Hồng Kông"], ["KHAC", "khác – gõ mã 3 chữ"]];
function Settlement({ t, note, NoteBox, run, load, toast }: any) {
  const se = t.settlement_edit || {}; const sm = se.summary || {}; const checks: any[] = se.checks || []; const st: Record<string, string> = se.service_types || {};
  const [edit, setEdit] = useState<any>(null);
  const [showCancelled, setShowCancelled] = useState(false);
  // Đ-11 (13/9/2026) · dòng chi phí đang mở hồ sơ chứng từ. Xem chú thích ở ô DinhKem bên dưới.
  const [moHoSo, setMoHoSo] = useState<number | null>(null);
  const base = `/tours/${t.id}/settlement`;
  const lines = (t.cost_lines || []).filter((l: any) => showCancelled || l.status === "hd");
  const calc = (f: any) => Math.round(f.cost_kind === "theo_khach" ? f.unit_price * f.qty * f.coef : f.unit_price * f.coef);
  // Rỗng = VND. Chuỗi rỗng và "VND" là cùng một câu trả lời; "KHAC" là đang chờ gõ mã.
  const ngoaiTe = !!edit && !!edit.tien_te && edit.tien_te !== "VND";
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const body = { ...edit }; ["unit_price", "budget", "so_tien_goc"].forEach((k) => (body[k] = soTien(body[k])));
    ["qty", "coef", "ty_gia"].forEach((k) => (body[k] = Number(body[k] || 0)));
    if (body.tien_te === "KHAC") body.tien_te = (edit.tien_te_khac || "").trim().toUpperCase();
    try { await api(edit.id ? `${base}/lines/${edit.id}` : `${base}/lines`, { method: edit.id ? "PUT" : "POST", json: body }); toast(edit.id ? "Đã sửa dòng" : "Đã thêm dòng"); setEdit(null); load(); } catch (x) { toast(errMsg(x), true); }
  };
  const cancel = async (l: any) => { const r = prompt(`Lý do hủy dòng ${l.line_no} – ${l.description}?`); if (!r) return; try { await api(`${base}/lines/${l.id}/cancel`, { method: "POST", json: { note: r } }); toast("Đã hủy dòng"); load(); } catch (x) { toast(errMsg(x), true); } };
  const upload = (l: any) => {
    const inp = document.createElement("input"); inp.type = "file"; inp.accept = "image/*,application/pdf";
    inp.onchange = async () => { const f = inp.files?.[0]; if (!f) return; if (f.size > 1_500_000) { toast("Tệp quá 1,5 MB – hãy chụp/nén nhỏ hơn", true); return; }
      const data = await new Promise<string>((res) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result)); rd.readAsDataURL(f); });
      try { await api(`${base}/lines/${l.id}/doc`, { method: "POST", json: { name: f.name, data } }); toast("Đã gắn chứng từ"); load(); } catch (x) { toast(errMsg(x), true); } };
    inp.click();
  };
  const matchPaid = async () => { try { const r = await api(`${base}/match-paid`, { method: "POST" }); toast(r.message); load(); } catch (x) { toast(errMsg(x), true); } };
  const viewDoc = async (l: any) => { try { const r = await fetch(`/api/v1${base}/lines/${l.id}/doc`, { headers: { Authorization: `Bearer ${getToken() || ""}` } }); if (!r.ok) throw new Error("Không tải được chứng từ"); const u = URL.createObjectURL(await r.blob()); window.open(u, "_blank"); } catch (x: any) { toast(x.message || String(x), true); } };
  const F = (k: string, label: string, type = "text", extra: any = {}) => <div><label>{label}</label><input type={type} value={edit[k] ?? ""} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} {...extra} /></div>;
  return (<div className="panel wrap">
    <h2>Quyết toán chi phí thực tế sau tour <Tag cls="navy">V.{String(sm.version || 1).padStart(2, "0")}</Tag> · {sm.lines || 0} dòng · thực chi <b>{vnd(sm.actual)}</b> · đã thanh toán {vnd(sm.paid)} · còn phải trả <b>{vnd(sm.remaining)}</b></h2>
    <div className="kpis">
      <div className="kpi"><b>{vnd(sm.revenue)}</b><span>Tổng thu (booking)</span></div>
      <div className="kpi"><b>{vnd(sm.actual)}</b><span>Tổng chi (dòng NCC)</span></div>
      <div className="kpi"><b style={{ color: sm.profit < 0 ? "var(--red)" : undefined }}>{vnd(sm.profit)} · {pct(sm.margin)}</b><span>Lợi nhuận</span></div>
      <div className="kpi"><b style={{ color: sm.variance > 0 ? "var(--red)" : undefined }}>{vnd(sm.variance)} ({pct(sm.variance_pct)})</b><span>{sm.has_budget ? <>Lệch so dự toán ({sm.budget_source_label}) {vnd(sm.budget)}</> : "Chưa có dự toán để so sánh"}</span></div>
      <div className="kpi"><b>{sm.with_doc || 0}/{sm.lines || 0}</b><span>Dòng có chứng từ</span></div>
    </div>
    {checks.length > 0 && <div style={{ marginBottom: 8 }}>{checks.map((c, i) => <Gate key={i} ok={c.level === "info"}>{c.level === "block" ? "CHẶN ĐÓNG SỐ – " : c.level === "warn" ? "Lưu ý – " : ""}{c.msg}</Gate>)}</div>}
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      {se.can_edit && <button className="act teal" style={{ margin: 0 }} onClick={() => setEdit({ ...EMPTY, qty: t.booked_pax || t.seats?.booked || 0 })}>+ Thêm dòng chi phí</button>}
      <button className="act grey" style={{ margin: 0 }} onClick={matchPaid}>Khớp “Đã thanh toán” với lệnh chi / tạm ứng</button>
      <label style={{ margin: 0 }}><input type="checkbox" checked={showCancelled} onChange={(e) => setShowCancelled(e.target.checked)} /> hiện dòng đã hủy</label>
      {!se.can_edit && <span className="muted">{t.status === "da_dong_so" ? "Đã đóng số – chờ Kế toán xác nhận (Kế toán có thể trả lại để sửa)" : ["kt_xac_nhan", "khoa"].includes(t.status) ? "Kế toán đã xác nhận – số này là căn cứ duy nhất, không sửa" : "Chỉ người điều hành chuyến soạn quyết toán sau khi tour được duyệt"}</span>}
    </div>
    {edit && <form onSubmit={save} className="panel" style={{ marginTop: 8 }}>
      <h3>{edit.id ? `Sửa dòng ${edit.line_no}` : "Thêm chi phí quyết toán thực tế"}</h3>
      <div className="grid">
        {F("description", "Mô tả chi tiết *")}
        <div><label>Loại dịch vụ *</label><select value={edit.service_type} onChange={(e) => setEdit({ ...edit, service_type: e.target.value })}>{Object.entries(st).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        {F("supplier_name", "Nhà cung cấp *")}{F("supplier_tax_code", "Mã số thuế NCC")}
        <div><label>Cách tính chi *</label><select value={edit.cost_kind} onChange={(e) => setEdit({ ...edit, cost_kind: e.target.value })}><option value="theo_khach">Theo khách (đơn giá × pax × hệ số)</option><option value="co_dinh">Cố định (đơn giá × hệ số)</option></select></div>
        {ngoaiTe
          ? <div><label>Đơn giá thực tế (đ)</label><input value={Math.round(Number(edit.so_tien_goc || 0) * Number(edit.ty_gia || 0))} readOnly title="Máy nhân số gốc với tỷ giá — không gõ tay, để ba con số không lệch nhau" /></div>
          : F("unit_price", "Đơn giá thực tế (đ)", "number", { step: 1000, min: 0 })}
        {F("qty", "Số khách (pax)", "number", { min: 0 })}{F("coef", "Hệ số / số lượng", "number", { step: "0.5", min: 0 })}
        {F("budget", "Dự toán của dòng (đ)", "number", { step: 1000, min: 0 })}
        <div><label>Thực chi</label><input value={vnd(calc({ ...edit, unit_price: ngoaiTe ? Number(edit.so_tien_goc || 0) * Number(edit.ty_gia || 0) : Number(edit.unit_price || 0), qty: Number(edit.qty || 0), coef: Number(edit.coef || 0) }))} readOnly /></div>
      </div>
      {/* NGOẠI TỆ — mở cửa 25/9/2026 cho bốn cột đã có trên bảng từ lâu.
          Ô mặc định là VND và KHÔNG đòi gì thêm: tuyệt đại đa số dòng giá vốn là tiền đồng, bắt
          tất cả khai "VND" là thêm một ô bắt buộc cho hàng nghìn dòng để phục vụ vài chục dòng. */}
      <div className="grid">
        <div><label>Đồng tiền của khoản này</label>
          <select value={edit.tien_te || ""} onChange={(e) => setEdit({ ...edit, tien_te: e.target.value })}>
            {DONG_TIEN.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
        {edit.tien_te === "KHAC" && <div><label>Mã đồng tiền (3 chữ) *</label>
          <input value={edit.tien_te_khac || ""} maxLength={3} placeholder="VD: MMK" onChange={(e) => setEdit({ ...edit, tien_te_khac: e.target.value })} /></div>}
        {ngoaiTe && <>
          {F("so_tien_goc", `Số tiền bằng ${edit.tien_te === "KHAC" ? (edit.tien_te_khac || "đồng gốc") : edit.tien_te} *`, "number", { step: "0.01", min: 0 })}
          {F("ty_gia", "Tỷ giá *", "number", { step: "0.000001", min: 0 })}
          {F("ngay_ty_gia", "Ngày của tỷ giá *", "date")}
        </>}
      </div>
      {ngoaiTe && <p className="muted">Ba ô này đi cùng nhau: thiếu một ô thì không lưu được. Một số tiền ngoại tệ
        thiếu tỷ giá là con số không quy đổi được; một tỷ giá thiếu ngày là con số không kiểm lại được.
        Đơn giá đồng Việt Nam ở trên là <b>số máy nhân</b> — anh/chị không gõ, để ba con số không lệch nhau.
        Tỷ giá lấy theo <b>ngày chi thật</b> của khoản này; tra ở <Link href="/ty-gia">Sổ tỷ giá</Link>, máy không chọn hộ.</p>}
      <label>Ghi chú / lời giải trình (bắt buộc khi vượt dự toán)</label><input value={edit.note} onChange={(e) => setEdit({ ...edit, note: e.target.value })} />
      <button className="act teal" type="submit">Lưu dòng</button> <button type="button" className="act grey" onClick={() => setEdit(null)}>Đóng</button>
    </form>}
    <table style={{ marginTop: 8 }}><thead><tr><th>#</th><th>Mô tả</th><th>Loại DV</th><th>NCC (MST)</th><th className="num">Đơn giá</th><th className="num">SL</th><th className="num">HS</th><th className="num">Dự toán</th><th className="num">Thực chi</th><th className="num">Đã TT</th><th>Chứng từ</th><th>Ghi chú</th><th></th></tr></thead>
      <tbody>{lines.length ? lines.flatMap((l: any) => [<tr key={l.id} style={{ opacity: l.status === "hd" ? 1 : 0.45 }}>
        <td>{l.line_no}</td><td>{l.description} <Tag>{l.cost_kind === "theo_khach" ? "theo khách" : "cố định"}</Tag>{l.source === "vietrip" && <Tag>Vietrip</Tag>}</td><td>{l.service_name || l.service_type}</td>
        <td>{l.supplier_name}{l.supplier_tax_code && <span className="muted"> ({l.supplier_tax_code})</span>}</td>
        {/* Ngoại tệ: hiện SỐ GỐC trước, số VND sau. Người soát cần thấy con số đã cam kết với nhà
            cung cấp, không phải con số quy đổi — quy đổi là việc của máy và có thể tính lại. */}
        <td className="num">{l.tien_te
          ? <><b>{Number(l.so_tien_goc || 0).toLocaleString("vi-VN")} {l.tien_te}</b>
              <div className="muted" style={{ fontSize: 12 }}>× {Number(l.ty_gia || 0).toLocaleString("vi-VN")} · {fmtD(l.ngay_ty_gia)}</div>
              <div className="muted" style={{ fontSize: 12 }}>= {vnd(l.unit_price)}</div></>
          : vnd(l.unit_price)}</td><td className="num">{l.qty}</td><td className="num">{l.coef}</td><td className="num muted">{l.budget ? vnd(l.budget) : "–"}</td>
        <td className="num"><b style={{ color: l.budget && l.over_pct > 0.1 ? "var(--red)" : undefined }}>{vnd(l.actual)}</b></td>
        <td className="num">{l.remaining > 0 ? <Tag cls="warn">{vnd(l.paid)}</Tag> : <Tag cls="ok">{vnd(l.paid)}</Tag>}</td>
        <td>{l.has_doc ? <a href="#" onClick={(e) => { e.preventDefault(); viewDoc(l); }}>📎 {l.doc_name || "xem"}</a> : <span className="muted">–</span>} {(se.can_edit || t.status === "da_dong_so") && l.status === "hd" && <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => upload(l)}>tải</button>}
          {" "}<button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setMoHoSo(moHoSo === l.id ? null : l.id)}>hồ sơ</button></td>
        <td className="muted">{l.note}</td>
        <td>{se.can_edit && l.status === "hd" && <><button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => setEdit({
          ...EMPTY, ...l,
          // Ngày từ máy chủ về dạng ISO đầy đủ; ô <input type="date"> chỉ nhận 10 ký tự đầu.
          ngay_ty_gia: l.ngay_ty_gia ? String(l.ngay_ty_gia).slice(0, 10) : "",
          // Đồng tiền ngoài danh sách gợi ý thì ô chọn về "khác" và giữ nguyên mã đã lưu,
          // thay vì im lặng rơi về VND — rơi về VND là xoá một lời khai đã có.
          ...(l.tien_te && !DONG_TIEN.some(([v]) => v === l.tien_te)
              ? { tien_te: "KHAC", tien_te_khac: l.tien_te } : {}),
        })}>sửa</button> <button className="act grey" style={{ padding: "2px 6px", margin: 0 }} onClick={() => cancel(l)}>hủy</button></>}</td>
      </tr>,
        /* Đ-11 (13/9/2026) · CỬA của kho chứng từ chung cho từng dòng chi.
         *
         * Nút "tải" ngay bên trái là cửa CŨ: một tệp một dòng, ghi thẳng vào cột doc_data. Nó không có
         * bản thứ hai, không có lý do khi gỡ, không nằm trong thư mục hồ sơ kiểm toán, và không chống
         * trùng. Một dòng chi thật thường có hai ba tờ – hoá đơn, phiếu thu của nhà cung cấp, ảnh chụp
         * biên nhận – nên "một tệp" là con số sai ngay từ đầu.
         *
         * Ô này gắn vào kho tệp chung (doi_tuong="dong_chi_phi", đã khai trong attachments.py), nơi có
         * đủ bốn thứ trên. Cửa cũ để nguyên chứ không gỡ: những dòng đã gắn tệp từ trước vẫn phải xem
         * lại được, và gỡ nó đi là làm mất chứng từ cũ của người ta. */
        moHoSo === l.id
          ? <tr key={`${l.id}-hs`}><td colSpan={13}>
              <div style={{ margin: "0 0 8px 24px" }}>
                <DinhKem doiTuong="dong_chi_phi" doiTuongId={l.id} loai="chung_tu"
                         tieuDe={`Chứng từ của dòng ${l.line_no} – ${l.description}`}
                         chiXem={!se.can_edit && t.status !== "da_dong_so"} />
              </div></td></tr>
          : null,
      ]) : <tr><td colSpan={13} className="muted">Chưa có dòng quyết toán – bấm “Thêm dòng chi phí” (cùng bố cục bảng Vietrip) hoặc đồng bộ từ Vietrip.</td></tr>}</tbody>
      <tfoot><tr><td colSpan={8}><b>TỔNG CỘNG</b></td><td className="num"><b>{vnd(sm.actual)}</b></td><td className="num"><b>{vnd(sm.paid)}</b></td><td colSpan={3}>Còn lại cần thanh toán: <b>{vnd(sm.remaining)}</b></td></tr></tfoot></table>
    <p className="muted">Nguyên tắc: một cửa – chỉ người điều hành chuyến soạn; đóng số lấy tổng dòng làm giá vốn thực tế; vượt dự toán dòng &gt; 10% phải giải trình; Kế toán trả lại → phiên bản mới; sau Kế toán xác nhận không sửa.</p>
  </div>);
}

export default function Page() { return <Shell><TourDetail /></Shell>; }
