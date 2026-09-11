"use client";
/** Sự cố tour – V7 Đợt 3 (10/9/2026).
 *
 *  Màn hình này KHÔNG có ô nhập chi phí phát sinh. Sự cố hay đẻ ra chi phí – thuê xe thay, đổi vé, đặt
 *  phòng khác – nhưng số tiền ấy đi qua ĐÚNG MỘT đường: Đề nghị chi nhóm "Chi phí tour", đúng cấp duyệt
 *  theo ngưỡng. Ở đây chỉ gắn SỐ HIỆU chứng từ đó. Có ô số tiền tại đây là mở đường tiền thứ hai song
 *  song với cổng chi, và lúc quyết toán chuyến sẽ có hai con số không ai biết cái nào thật.
 *
 *  Cũng KHÔNG phải màn hình kỷ luật. Sự vụ nhân viên nằm ở /hr?tab=incidents; khi kết luận sự cố là do
 *  lỗi của một người cụ thể thì lập Sự vụ bên đó rồi gắn số hiệu về đây. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";

const RONG = {
  tour_id: "", booking_id: "", nhom: "xe", muc: 1, xay_ra_luc: "", noi_xay_ra: "",
  so_khach_anh_huong: "", mo_ta: "", nguoi_bao: "", supplier_id: "",
};
const MAU: Record<string, string> = { moi: "red", dang_xu_ly: "warn", da_xu_ly: "grey", dong: "ok" };

function SuCoTour() {
  const { toast } = useShell();
  const [meta, setMeta] = useState<any>({ nhom: {}, muc: {}, trang_thai: {}, nguyen_nhan: {}, nha_cung_cap: [] });
  const [ds, setDs] = useState<any[]>([]);
  const [cs, setCs] = useState<any>({});
  // Booking của ĐÚNG chuyến đang chọn, nạp khi người dùng chọn chuyến. Không nạp cả sổ booking:
  // xem ghi chú ở /su-co-tour/chon/booking.
  const [bk, setBk] = useState<any>({ co_ten_khach: false, rows: [] });
  // Hai danh sách của bước kết luận, chỉ nạp cho vai trò đóng được hồ sơ.
  const [kl, setKl] = useState<any>({ chi_phi_tour: [], khieu_nai: [] });
  const [f, setF] = useState<any>({ ...RONG });
  const [hien, setHien] = useState(false);
  const [mo, setMo] = useState<number | null>(null);
  const [ct, setCt] = useState<any>(null);
  const [buoc, setBuoc] = useState("");
  const [loc, setLoc] = useState("");
  const [k, setK] = useState<any>({ nguyen_nhan_nhom: "do_ncc", nguyen_nhan: "", ket_qua: "",
                                    huong_xu_ly: "", payment_request_id: "", complaint_id: "", incident_id: "" });

  const load = useCallback(() => {
    api("/su-co-tour" + (loc ? `?trang_thai=${loc}` : "")).then(setDs).catch((e) => toast(errMsg(e), true));
    api("/su-co-tour/chi-so").then(setCs).catch(() => {});
  }, [loc]); // eslint-disable-line
  useEffect(() => {
    api("/su-co-tour/meta").then(setMeta).catch(() => {});
    // Danh sách của bước kết luận nằm sau hàng rào vai trò – vai trò không đóng được hồ sơ nhận 403,
    // và đó là câu trả lời đúng, không phải lỗi cần báo.
    api("/su-co-tour/chon/ket-luan").then(setKl).catch(() => {});
  }, []);
  useEffect(load, [load]);

  // Chọn chuyến xong mới nạp booking CỦA CHUYẾN ẤY.
  useEffect(() => {
    if (!f.tour_id) { setBk({ co_ten_khach: false, rows: [] }); return; }
    api(`/su-co-tour/chon/booking?tour_id=${f.tour_id}`).then(setBk)
      .catch(() => setBk({ co_ten_khach: false, rows: [] }));
  }, [f.tour_id]);

  const xemChiTiet = (id: number) => {
    if (mo === id) { setMo(null); setCt(null); return; }
    setMo(id); setCt(null);
    api(`/su-co-tour/${id}`).then(setCt).catch((e) => toast(errMsg(e), true));
  };

  const post = async (p: string, json?: any, method = "POST") => {
    try {
      const r = await api(p, { method, json });
      toast(r.message || "Xong");
      load();
      if (mo) api(`/su-co-tour/${mo}`).then(setCt).catch(() => {});
      return r;
    } catch (x) { toast(errMsg(x), true); }
  };

  const luu = () => post("/su-co-tour", {
    ...f, muc: Number(f.muc),
    tour_id: Number(f.tour_id),
    booking_id: f.booking_id ? Number(f.booking_id) : null,
    supplier_id: f.supplier_id ? Number(f.supplier_id) : null,
    so_khach_anh_huong: Number(f.so_khach_anh_huong || 0),
    xay_ra_luc: f.xay_ra_luc || null,
  }).then((r) => { if (r) { setF({ ...RONG }); setHien(false); } });

  const dong = (id: number) => post(`/su-co-tour/${id}/dong`, {
    ...k,
    payment_request_id: k.payment_request_id ? Number(k.payment_request_id) : null,
    complaint_id: k.complaint_id ? Number(k.complaint_id) : null,
    incident_id: k.incident_id ? Number(k.incident_id) : null,
  });

  return (<>
    <h1>Sự cố tour</h1>
    <p className="muted">Chuyện xảy ra với <b>một chuyến đang chạy</b> — khác với <b>Sự vụ</b> (kỷ luật nội bộ nhân viên,
      ở màn hình Nhân sự) và khác với <b>Khiếu nại</b> (quan hệ với khách mua dịch vụ). Phần lớn sự cố không có ai sai:
      thời tiết, hãng bay dời chuyến, lỗi nhà cung cấp. Màn hình này <b>không có ô nhập chi phí phát sinh</b>: khoản chi
      đi qua Đề nghị chi nhóm “Chi phí tour”, ở đây chỉ gắn số hiệu chứng từ.</p>

    <div className="kpis">
      <div className="kpi"><b>{cs.dang_mo ?? 0}</b><span>Đang mở</span></div>
      <div className="kpi"><b style={{ color: cs.qua_han_chua_nhan ? "var(--red)" : undefined }}>{cs.qua_han_chua_nhan ?? 0}</b><span>Quá hạn chưa có người nhận</span></div>
      <div className="kpi"><b>{cs.theo_muc?.["3"] ?? 0}</b><span>Mức 3 (mọi kỳ)</span></div>
      <div className="kpi"><b>{cs.tong ?? 0}</b><span>Tổng hồ sơ</span></div>
    </div>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
      <button className="act" onClick={() => setHien(!hien)}>{hien ? "Đóng biểu mẫu" : "+ Ghi nhận sự cố"}</button>
      <select value={loc} onChange={(e) => setLoc(e.target.value)}>
        <option value="">— tất cả trạng thái —</option>
        {Object.entries(meta.trang_thai).map(([kk, v]: any) => <option key={kk} value={kk}>{v}</option>)}</select>
    </div>

    {hien && <div className="panel"><h2>Ghi nhận sự cố</h2>
      <div className="grid">
        <label>Chuyến tour *<select value={f.tour_id} onChange={(e) => setF({ ...f, tour_id: e.target.value, booking_id: "" })}>
          <option value="">— chọn chuyến —</option>
          {(meta.tours || []).map((t: any) => <option key={t.id} value={t.id}>{t.code} · {t.name}</option>)}</select></label>
        <label>Booking <i className="muted">(chỉ khi sự cố chạm một nhóm khách cụ thể)</i>
          <select value={f.booking_id} disabled={!f.tour_id} onChange={(e) => setF({ ...f, booking_id: e.target.value })}>
            <option value="">{f.tour_id ? "— cả đoàn —" : "— chọn chuyến trước —"}</option>
            {(bk.rows || []).map((b: any) => <option key={b.id} value={b.id}>{b.code}{b.khach ? " · " + b.khach : ""}</option>)}</select></label>
        <label>Nhóm sự cố *<select value={f.nhom} onChange={(e) => setF({ ...f, nhom: e.target.value })}>
          {Object.entries(meta.nhom).map(([kk, v]: any) => <option key={kk} value={kk}>{v}</option>)}</select></label>
        <label>Mức *<select value={f.muc} onChange={(e) => setF({ ...f, muc: e.target.value })}>
          {Object.entries(meta.muc).map(([kk, v]: any) => <option key={kk} value={kk}>{v}</option>)}</select></label>
        <label>Xảy ra lúc <i className="muted">(hạn xử lý tính từ mốc này, không phải lúc ghi)</i>
          <input type="datetime-local" value={f.xay_ra_luc} onChange={(e) => setF({ ...f, xay_ra_luc: e.target.value })} /></label>
        <label>Nơi xảy ra<input value={f.noi_xay_ra} onChange={(e) => setF({ ...f, noi_xay_ra: e.target.value })} placeholder="Đèo Hải Vân, sân bay Cam Ranh…" /></label>
        <label>Số khách ảnh hưởng<input type="number" min={0} value={f.so_khach_anh_huong} onChange={(e) => setF({ ...f, so_khach_anh_huong: e.target.value })} /></label>
        <label>Người báo về<input value={f.nguoi_bao} onChange={(e) => setF({ ...f, nguoi_bao: e.target.value })} placeholder="Tên HDV / tài xế gọi về" /></label>
        <label>Nhà cung cấp liên quan <i className="muted">(để trống khi chưa rõ)</i>
          <select value={f.supplier_id} onChange={(e) => setF({ ...f, supplier_id: e.target.value })}>
            <option value="">— chưa xác định —</option>
            {(meta.nha_cung_cap || []).map((n: any) => <option key={n.id} value={n.id}>{n.name}</option>)}</select></label>
      </div>
      <label>Diễn biến * <i className="muted">(ghi nguyên văn lời người ở hiện trường, không tóm tắt theo ý mình)</i>
        <textarea rows={3} style={{ width: "100%" }} value={f.mo_ta} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
      <button className="act" disabled={!f.tour_id || !f.mo_ta} onClick={luu}>Lưu sự cố</button>
    </div>}

    <div className="panel wrap"><table><thead><tr>
      <th>Mã</th><th>Chuyến</th><th>Nhóm</th><th>Mức</th><th>Xảy ra</th><th>Hạn nhận</th><th>Trạng thái</th><th></th>
    </tr></thead><tbody>
      {ds.map((s) => [
        <tr key={s.id}>
          <td><b>{s.code}</b></td>
          <td>{s.tour_code}<div className="muted">{s.booking_code || "cả đoàn"}</div></td>
          <td>{s.nhom_ten}{s.supplier_name && <div className="muted">{s.supplier_name}</div>}</td>
          <td><Tag cls={s.muc === 3 ? "red" : s.muc === 2 ? "warn" : "grey"}>Mức {s.muc}</Tag></td>
          <td>{fmtDT(s.xay_ra_luc)}<div className="muted">{s.noi_xay_ra}</div></td>
          <td>{fmtDT(s.han_xu_ly)}{s.qua_han && <Tag cls="red">quá hạn chưa ai nhận</Tag>}
            {s.nhan_luc && <div className="muted">nhận {fmtDT(s.nhan_luc)} · {s.nguoi_xu_ly}</div>}</td>
          <td><Tag cls={MAU[s.trang_thai] || "grey"}>{s.trang_thai_ten}</Tag></td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => xemChiTiet(s.id)}>{mo === s.id ? "Ẩn" : "Xem"}</button></td>
        </tr>,
        mo === s.id && <tr key={s.id + "d"}><td colSpan={8} style={{ background: "var(--bg2)" }}>
          <p><b>Diễn biến:</b> {s.mo_ta}</p>
          {s.nguoi_bao && <p className="muted"><b>Người báo:</b> {s.nguoi_bao}</p>}
          {s.so_khach_anh_huong > 0 && <p className="muted"><b>Số khách ảnh hưởng:</b> {s.so_khach_anh_huong}</p>}

          <h3>Nhật ký xử lý</h3>
          {ct?.id === s.id ? (ct.xu_ly?.length
            ? <ul>{ct.xu_ly.map((x: any) => <li key={x.id}><b>{fmtDT(x.luc)}</b> · {x.nguoi}: {x.noi_dung}</li>)}</ul>
            : <p className="muted">Chưa ai ghi bước xử lý nào. Dòng đầu tiên cũng là lúc hệ thống ghi nhận có người nhận việc.</p>)
            : <p className="muted">Đang tải…</p>}
          {s.trang_thai !== "dong" && <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input style={{ flex: "1 1 320px" }} value={buoc} onChange={(e) => setBuoc(e.target.value)} placeholder="Đã làm gì: gọi xe thay, báo khách, đổi khách sạn…" />
            <button className="act" disabled={!buoc.trim()} onClick={() => post(`/su-co-tour/${s.id}/xu-ly`, { noi_dung: buoc }).then((r) => { if (r) setBuoc(""); })}>Ghi bước xử lý</button>
            {s.chuyen_duoc?.map((tt: string) => <button key={tt} className="act grey" onClick={() => post(`/su-co-tour/${s.id}/chuyen`, { trang_thai: tt })}>→ {meta.trang_thai[tt]}</button>)}
          </div>}

          {s.trang_thai === "dong" ? <div className="panel" style={{ background: "var(--bg)" }}>
            <p><b>Nguyên nhân ({s.nguyen_nhan_ten}):</b> {s.nguyen_nhan}</p>
            <p><b>Kết quả:</b> {s.ket_qua}</p>
            {s.huong_xu_ly && <p><b>Hướng xử lý:</b> {s.huong_xu_ly}</p>}
            {s.payment_request_code && <p><b>Chứng từ chi phí:</b> {s.payment_request_code} — {vnd(s.payment_request_amount)}đ ({s.payment_request_status})</p>}
            {s.complaint_code && <p className="muted">Khách đã lập khiếu nại {s.complaint_code}</p>}
            {s.incident_id && <p className="muted">Đã lập sự vụ nội bộ #{s.incident_id}</p>}
            <p className="muted">Đóng bởi {s.closed_by} lúc {fmtDT(s.closed_at)}</p>
          </div> : (s.trang_thai !== "moi" && <div className="panel" style={{ background: "var(--bg)" }}>
            <h3>Kết luận & đóng hồ sơ</h3>
            <div className="grid">
              <label>Nhóm nguyên nhân *<select value={k.nguyen_nhan_nhom} onChange={(e) => setK({ ...k, nguyen_nhan_nhom: e.target.value })}>
                {Object.entries(meta.nguyen_nhan).map(([kk, v]: any) => <option key={kk} value={kk}>{v}</option>)}</select></label>
              <label>Chứng từ chi phí <i className="muted">(Đề nghị chi nhóm “Chi phí tour”)</i>
                <select value={k.payment_request_id} onChange={(e) => setK({ ...k, payment_request_id: e.target.value })}>
                  <option value="">— không phát sinh chi phí —</option>
                  {(kl.chi_phi_tour || []).map((x: any) => <option key={x.id} value={x.id}>{x.code} · {vnd(x.amount)}đ</option>)}</select></label>
              <label>Khiếu nại của khách <i className="muted">(nếu khách đã lập)</i>
                <select value={k.complaint_id} onChange={(e) => setK({ ...k, complaint_id: e.target.value })}>
                  <option value="">— khách không khiếu nại —</option>
                  {(kl.khieu_nai || []).map((x: any) => <option key={x.id} value={x.id}>{x.code} · {x.khach}</option>)}</select></label>
              <label>Số hiệu Sự vụ <i className="muted">(chỉ khi lỗi thuộc về một người cụ thể — lập ở màn hình Nhân sự)</i>
                <input type="number" value={k.incident_id} onChange={(e) => setK({ ...k, incident_id: e.target.value })} placeholder="để trống nếu là lỗi quy trình" /></label>
            </div>
            <label>Nguyên nhân * <i className="muted">(ít nhất 20 ký tự — “do khách quan” không phải là một nguyên nhân)</i>
              <textarea rows={2} style={{ width: "100%" }} value={k.nguyen_nhan} onChange={(e) => setK({ ...k, nguyen_nhan: e.target.value })} /></label>
            <label>Kết quả cuối cùng cho khách *
              <textarea rows={2} style={{ width: "100%" }} value={k.ket_qua} onChange={(e) => setK({ ...k, ket_qua: e.target.value })} /></label>
            <label>Hướng xử lý đã áp dụng
              <textarea rows={2} style={{ width: "100%" }} value={k.huong_xu_ly} onChange={(e) => setK({ ...k, huong_xu_ly: e.target.value })} /></label>
            <button className="act" disabled={!k.nguyen_nhan || !k.ket_qua} onClick={() => dong(s.id)}>Đóng hồ sơ</button>
          </div>)}

          <DinhKem doiTuong="su_co_tour" doiTuongId={s.id} loai="hinh_anh"
                   tieuDe="Bằng chứng sự cố (ảnh xe hỏng, thông báo dời chuyến, biên bản với nhà cung cấp)" />
        </td></tr>,
      ])}
    </tbody></table>
    {ds.length === 0 && <p className="muted">Chưa có sự cố nào được ghi nhận.</p>}
    </div>
  </>);
}
export default function Page() { return <Shell><SuCoTour /></Shell>; }
