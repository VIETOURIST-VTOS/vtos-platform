"use client";
/** Phản hồi & khiếu nại của KHÁCH HÀNG.
 *
 *  Màn hình này KHÔNG có ô nhập số tiền bồi thường. Chỉ ghi đề nghị của khách bằng nguyên văn; số tiền
 *  công ty thực trả sinh ra ở Đề nghị chi nhóm "hoàn tiền" và đi đúng cấp duyệt theo ngưỡng hiện hành.
 *  Có ô số tiền ở đây là mở đường tiền thứ hai song song với cổng chi. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";

const RONG = { source: "dien_thoai", customer_name: "", customer_phone: "", booking_id: "", nhom: "chat_luong",
               level: 1, noi_dung: "", de_nghi_khach: "", handler: "", nguon_tao: "nguoi", ai_ghi_chu: "" };
const MAU: Record<string, string> = { moi: "warn", dang_xu_ly: "warn", cho_khach: "grey", da_dong: "ok", tai_mo: "red" };

function KhieuNai() {
  const { toast } = useShell();
  const [meta, setMeta] = useState<any>({ kn_nguon: {}, kn_nhom: {}, kn_muc: {}, kn_trang_thai: {}, kn_nguyen_nhan: {}, kn_huong: {}, kn_nhom_can_booking: [] });
  const [ds, setDs] = useState<any[]>([]);
  const [cs, setCs] = useState<any>({});
  const [bk, setBk] = useState<any[]>([]);
  const [pr, setPr] = useState<any[]>([]);
  const [f, setF] = useState<any>({ ...RONG });
  const [hien, setHien] = useState(false);
  const [mo, setMo] = useState<number | null>(null);
  const [loc, setLoc] = useState("");
  const [d, setD] = useState<any>({ nguyen_nhan_nhom: "do_ta", nguyen_nhan: "", huong_xu_ly: [] as string[], de_nghi_khach: "", khach_chap_nhan: "", payment_request_id: "" });

  const load = useCallback(() => {
    api("/khieu-nai" + (loc ? `?status=${loc}` : "")).then(setDs).catch((e) => toast(errMsg(e), true));
    api("/khieu-nai/chi-so").then(setCs).catch(() => {});
  }, [loc]); // eslint-disable-line
  useEffect(() => {
    api("/cskh/meta").then(setMeta).catch(() => {});
    api("/bookings?limit=300").then((r) => setBk(Array.isArray(r) ? r : r.rows || [])).catch(() => {});
    // Chỉ chứng từ nhóm hoàn tiền mới gắn được vào hồ sơ khiếu nại – lọc ở đây cho khớp chốt chặn ở máy chủ.
    api("/payment-requests").then((r) => setPr((Array.isArray(r) ? r : r.rows || []).filter((x: any) => x.category === "hoan_tien"))).catch(() => {});
  }, []);
  useEffect(load, [load]);

  const post = async (p: string, json?: any, method = "POST") => {
    try { const r = await api(p, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const canBooking = meta.kn_nhom_can_booking?.includes(f.nhom);
  const luu = () => post("/khieu-nai", { ...f, level: Number(f.level), booking_id: f.booking_id ? Number(f.booking_id) : null })
    .then((r) => { if (r) { setF({ ...RONG }); setHien(false); } });
  const doiHuong = (k: string) => setD({ ...d, huong_xu_ly: d.huong_xu_ly.includes(k) ? d.huong_xu_ly.filter((x: string) => x !== k) : [...d.huong_xu_ly, k] });
  const canChungTu = d.huong_xu_ly.some((h: string) => h === "hoan_mot_phan" || h === "hoan_toan_bo");

  return (<>
    <h1>Phản hồi & khiếu nại</h1>
    <p className="muted">Hồ sơ khiếu nại của <b>khách hàng</b> — khác với <b>Sự vụ</b> (kỷ luật nội bộ nhân viên). Màn hình này
      <b> không có ô nhập số tiền bồi thường</b>: chỉ ghi đề nghị của khách bằng nguyên văn, còn số tiền công ty thực trả
      sinh ra ở Đề nghị chi nhóm hoàn tiền và đi đúng cấp duyệt theo ngưỡng hiện hành.</p>

    <div className="kpis">
      <div className="kpi"><b>{cs.dang_mo ?? 0}</b><span>Đang mở</span></div>
      <div className="kpi"><b style={{ color: cs.qua_han_chua_phan_hoi ? "var(--red)" : undefined }}>{cs.qua_han_chua_phan_hoi ?? 0}</b><span>Quá hạn chưa phản hồi</span></div>
      <div className="kpi"><b>{cs.theo_muc?.["3"] ?? 0}</b><span>Mức 3 đang mở</span></div>
      <div className="kpi"><b>{cs.tong ?? 0}</b><span>Tổng hồ sơ</span></div>
    </div>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
      <button className="act" onClick={() => setHien(!hien)}>{hien ? "Đóng biểu mẫu" : "+ Ghi nhận phản hồi / khiếu nại"}</button>
      <select value={loc} onChange={(e) => setLoc(e.target.value)}>
        <option value="">— tất cả trạng thái —</option>
        {Object.entries(meta.kn_trang_thai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select>
    </div>

    {hien && <div className="panel"><h2>Hồ sơ phản hồi / khiếu nại</h2>
      <div className="grid">
        <label>Nguồn tiếp nhận *<select value={f.source} onChange={(e) => setF({ ...f, source: e.target.value })}>
          {Object.entries(meta.kn_nguon).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Tên khách hàng *<input value={f.customer_name} onChange={(e) => setF({ ...f, customer_name: e.target.value })} /></label>
        <label>Điện thoại<input value={f.customer_phone} onChange={(e) => setF({ ...f, customer_phone: e.target.value })} /></label>
        <label>Nhóm vấn đề *<select value={f.nhom} onChange={(e) => setF({ ...f, nhom: e.target.value })}>
          {Object.entries(meta.kn_nhom).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Chuyến / Booking {canBooking && <b style={{ color: "var(--red)" }}>*</b>}
          <select value={f.booking_id} onChange={(e) => setF({ ...f, booking_id: e.target.value })}>
            <option value="">— không gắn chuyến —</option>
            {bk.map((b: any) => <option key={b.id} value={b.id}>{b.code} · {b.customer_name}</option>)}</select></label>
        <label>Mức độ *<select value={f.level} onChange={(e) => setF({ ...f, level: e.target.value })}>
          {Object.entries(meta.kn_muc).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      <label>Nội dung khách phản ánh * <i className="muted">(ghi nguyên văn lời khách, không tóm tắt theo ý mình)</i>
        <textarea rows={3} style={{ width: "100%" }} value={f.noi_dung} onChange={(e) => setF({ ...f, noi_dung: e.target.value })} /></label>
      <label>Đề nghị của khách hàng * <i className="muted">(nguyên văn khách yêu cầu gì: xin lỗi, đổi lịch, hoàn tiền… — không quy ngay thành số tiền)</i>
        <textarea rows={2} style={{ width: "100%" }} value={f.de_nghi_khach} onChange={(e) => setF({ ...f, de_nghi_khach: e.target.value })} /></label>
      <div className="panel" style={{ background: "var(--bg2)" }}>
        <label><input type="checkbox" checked={f.nguon_tao === "ai"} onChange={(e) => setF({ ...f, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Hồ sơ do trợ lý AI ghi nhận</b></label>
        {f.nguon_tao === "ai" && <label>Căn cứ (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={f.ai_ghi_chu} onChange={(e) => setF({ ...f, ai_ghi_chu: e.target.value })} placeholder="Trích từ hội thoại nào, lúc nào" /></label>}
      </div>
      <button className="act" disabled={!f.customer_name || !f.noi_dung || !f.de_nghi_khach} onClick={luu}>Lưu hồ sơ</button>
    </div>}

    <div className="panel wrap"><table><thead><tr>
      <th>Mã</th><th>Khách</th><th>Nhóm</th><th>Mức</th><th>Chuyến</th><th>Hạn phản hồi</th><th>Trạng thái</th><th></th>
    </tr></thead><tbody>
      {ds.map((c) => [
        <tr key={c.id}>
          <td><b>{c.code}</b>{c.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</td>
          <td>{c.customer_name}<div className="muted">{c.customer_phone}</div>
            {c.lan_khieu_nai_12_thang > 1 && <Tag cls="red">khiếu nại lần {c.lan_khieu_nai_12_thang}/12 tháng</Tag>}</td>
          <td>{c.nhom_ten}</td>
          <td><Tag cls={c.level === 3 ? "red" : c.level === 2 ? "warn" : "grey"}>Mức {c.level}</Tag></td>
          <td className="muted">{c.tour_code || c.booking_code || "—"}</td>
          <td>{fmtDT(c.han_phan_hoi)}{c.qua_han && <Tag cls="red">quá hạn</Tag>}{c.tre_khi_phan_hoi && <Tag cls="warn">trả lời trễ</Tag>}</td>
          <td><Tag cls={MAU[c.status] || "grey"}>{c.status_ten}</Tag></td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(mo === c.id ? null : c.id)}>{mo === c.id ? "Ẩn" : "Xem"}</button></td>
        </tr>,
        mo === c.id && <tr key={c.id + "d"}><td colSpan={8} style={{ background: "var(--bg2)" }}>
          <p><b>Khách phản ánh:</b> {c.noi_dung}</p>
          <p><b>Đề nghị của khách:</b> {c.de_nghi_khach || <i className="muted">chưa ghi — hồ sơ tự mở từ phiếu chăm sóc, cần liên hệ khách ghi lại nguyên văn trước khi đóng</i>}</p>
          {c.ai_ghi_chu && <p className="muted"><b>Căn cứ AI:</b> {c.ai_ghi_chu}</p>}
          {c.nguyen_nhan && <p><b>Nguyên nhân ({c.nguyen_nhan_ten}):</b> {c.nguyen_nhan}</p>}
          {c.huong_ten?.length > 0 && <p><b>Hướng xử lý:</b> {c.huong_ten.join(" · ")}</p>}
          {c.payment_request_code && <p><b>Chứng từ hoàn tiền:</b> {c.payment_request_code} — {vnd(c.payment_request_amount)}đ ({c.payment_request_status})</p>}
          {c.incident_id && <p className="muted">Đã lập sự vụ nội bộ #{c.incident_id}</p>}

          {/* Ảnh và chứng từ khách gửi. Đặt TRƯỚC khối đóng hồ sơ, không phải sau: người ký đóng cần
              nhìn thấy bằng chứng ngay trên màn hình đang ký, chứ không phải nhớ là đã xem ở đâu đó. */}
          <DinhKem doiTuong="khieu_nai" doiTuongId={c.id} loai="hinh_anh"
                   tieuDe="Ảnh & chứng từ khách gửi"
                   chiXem={c.status === "da_dong"} />
          <p className="muted">Tiếp nhận {c.received_by} lúc {fmtDT(c.received_at)}{c.handler && ` · Xử lý ${c.handler}`}
            {c.closed_by && ` · Ký đóng ${c.closed_by}`}{c.reopen_reason && ` · Tái mở: ${c.reopen_reason}`}</p>

          {!c.first_response_at && c.status !== "da_dong" &&
            <button className="act" onClick={() => post(`/khieu-nai/${c.id}/phan-hoi`)}>Đã phản hồi khách</button>}
          {c.chuyen_duoc?.map((s: string) => <button key={s} className="act grey" style={{ marginRight: 6 }}
            onClick={() => s === "tai_mo"
              ? (() => { const l = prompt("Lý do tái mở hồ sơ:"); if (l && l.trim()) post(`/khieu-nai/${c.id}/tai-mo`, { ly_do: l.trim() }); })()
              : post(`/khieu-nai/${c.id}/chuyen-trang-thai`, { status: s })}>→ {meta.kn_trang_thai[s]}</button>)}

          {c.status !== "da_dong" && <div className="panel" style={{ marginTop: 8 }}>
            <h2 style={{ fontSize: 15 }}>Đóng hồ sơ</h2>
            {c.can_hai_chu_ky && <p className="muted">Hồ sơ <b>mức 3</b>: cần <b>hai chữ ký</b> và người xử lý không được tự đóng hồ sơ của mình.</p>}
            <div className="grid">
              <label>Nguyên nhân xác định *<select value={d.nguyen_nhan_nhom} onChange={(e) => setD({ ...d, nguyen_nhan_nhom: e.target.value })}>
                {Object.entries(meta.kn_nguyen_nhan).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
              <label>Khách đã chấp nhận? *<select value={d.khach_chap_nhan} onChange={(e) => setD({ ...d, khach_chap_nhan: e.target.value })}>
                <option value="">— chọn —</option><option value="co">Có</option><option value="khong">Chưa</option></select></label>
            </div>
            <label>Giải trình nguyên nhân *<textarea rows={2} style={{ width: "100%" }} value={d.nguyen_nhan} onChange={(e) => setD({ ...d, nguyen_nhan: e.target.value })} /></label>
            {!c.de_nghi_khach && <label>Đề nghị của khách (nguyên văn) *<textarea rows={2} style={{ width: "100%" }} value={d.de_nghi_khach} onChange={(e) => setD({ ...d, de_nghi_khach: e.target.value })} /></label>}
            <div style={{ margin: "6px 0" }}><b>Hướng xử lý *</b>{" "}
              {Object.entries(meta.kn_huong).map(([k, v]: any) => <button key={k} className={"act " + (d.huong_xu_ly.includes(k) ? "" : "grey")}
                style={{ margin: "4px 6px 0 0", fontSize: 13 }} onClick={() => doiHuong(k)}>{v}</button>)}</div>
            {canChungTu && <label>Số Đề nghị chi (nhóm hoàn tiền) * <i className="muted">— chọn chứng từ đã lập, màn hình này không có ô gõ số tiền</i>
              <select value={d.payment_request_id} onChange={(e) => setD({ ...d, payment_request_id: e.target.value })}>
                <option value="">— chọn chứng từ —</option>
                {pr.map((x: any) => <option key={x.id} value={x.id}>{x.code} · {vnd(x.amount)}đ · {x.status}</option>)}</select></label>}
            <button className="act" onClick={() => post(`/khieu-nai/${c.id}/dong`, {
              ...d, payment_request_id: d.payment_request_id ? Number(d.payment_request_id) : null })}>Ký đóng hồ sơ</button>
          </div>}
        </td></tr>,
      ])}
      {!ds.length && <tr><td colSpan={8} className="muted">Chưa có hồ sơ nào.</td></tr>}
    </tbody></table></div>
  </>);
}
export default function Page() { return <Shell><KhieuNai /></Shell>; }
