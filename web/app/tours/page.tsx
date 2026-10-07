"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, fmtD, soTien } from "@/lib/api";
import { TOUR_TYPES, TOUR_STATUS } from "@/lib/meta";
import { Tag, errMsg, MangTag } from "@/components/ui";
import KhoCuLo from "@/components/KhoCuLo";
import KhoCuNguoiBan from "@/components/KhoCuNguoiBan";
import KhoCuDongSoBu from "@/components/KhoCuDongSoBu";

function Tours() {
  const { user, toast } = useShell();
  const [rows, setRows] = useState<any[]>([]); const [ops, setOps] = useState<any[]>([]); const [open, setOpen] = useState(false);
  const [q, setQ] = useState(""); const [month, setMonth] = useState(""); const [st, setSt] = useState("");
  const mang = useSearchParams().get("mang") || "";
  const [tong, setTong] = useState(0); const [chamTran, setChamTran] = useState(false);
  // KS-5 · T5: cửa /tours cắt ở 300 chuyến. Trước 11/9/2026 nó trả về một mảng trần nên màn hình
  // không biết là đã cắt – với 1.200+ tour nhập từ Vietrip, người đọc tin mình đang nhìn toàn bộ
  // trong khi đang nhìn một phần tư. Nay phản hồi mang `tong` và `cham_tran`, và dòng chữ dưới đây
  // nói thẳng ra. Cắt thì được, im lặng thì không.
  const load = () => api(`/tours?limit=300&q=${encodeURIComponent(q)}&month=${month}&status=${st}&mang=${mang}`)
    .then((r) => { setRows(r.rows || []); setTong(r.tong || 0); setChamTran(!!r.cham_tran); }).catch(() => {});
  useEffect(() => { load(); }, [q, month, st, mang]); // eslint-disable-line
  useEffect(() => { api("/users?role=nv_dh,tp_dh").then(setOps).catch(() => {}); }, []);
  // Chủ tịch quyết 24/9/2026: Kinh doanh Đoàn tự lập dự toán đoàn. Cửa máy chủ đã mở từ vòng 2;
  // thiếu dòng này thì quyền có trong mã mà không có ô nào để dùng — và một quyền không bấm được
  // thì trên thực tế là chưa mở.
  const laKinhDoanh = ["gd_kd", "tp_kd", "tn_kd", "nv_kd"].includes(user?.role || "");
  const canCreate = ["nv_dh", "tp_dh"].includes(user?.role || "") || laKinhDoanh;
  // Kinh doanh chỉ mở được chuyến ĐOÀN (ĐH Điều 2 còn nguyên cho mảng lẻ), nên danh sách loại
  // chuyến của họ hẹp lại ngay tại ô chọn — thay vì để họ chọn rồi nhận 403.
  const loaiChoPhep = laKinhDoanh
    ? { doan_noi_dia: TOUR_TYPES.doan_noi_dia, doan_nuoc_ngoai: TOUR_TYPES.doan_nuoc_ngoai }
    : TOUR_TYPES;
  const [loai, setLoai] = useState(laKinhDoanh ? "doan_noi_dia" : "le_noi_dia");
  const laDoan = loai.startsWith("doan_");
  /** Hợp đồng thuê xe riêng — Chủ tịch chọn 07/10/2026: dựng như một CHUYẾN RÚT GỌN, không sửa
   *  bảng lệnh điều xe. Màn hình đổi lời chứ KHÔNG đổi luật: máy chủ vẫn nhận đúng một cửa
   *  `POST /tours`, vẫn qua đúng cổng biên và cổng điểm dừng nghỉ như mọi chuyến khác. */
  const laThueXe = loai === "thue_xe";
  const [hhKhach, setHhKhach] = useState("");
  async function create(e: React.FormEvent) {
    e.preventDefault(); const f = new FormData(e.target as HTMLFormElement); const d: any = Object.fromEntries(f.entries());
    ["price_per_pax", "fixed_cost", "var_cost_per_pax", "hoa_hong_khach_tien"].forEach((k) => (d[k] = soTien(d[k])));
    ["planned_pax", "operator_id"].forEach((k) => (d[k] = Number(d[k] || 0)));
    // MỘT HỢP ĐỒNG = MỘT "KHÁCH". Đây là cách ghi, nói thẳng ra để không ai đọc nhầm: hợp đồng
    // thuê xe bán trọn gói chứ không bán theo đầu người, nên `price_per_pax` mang GIÁ TRỌN HỢP
    // ĐỒNG và `planned_pax` bằng 1. Nhờ vậy mọi phép tính doanh thu, giá vốn và biên đang chạy
    // vẫn ra đúng số mà không phải dựng một công thức thứ hai cho riêng loại này — và một công
    // thức thứ hai là chỗ hai màn hình bắt đầu nói hai con số khác nhau.
    if (d.tour_type === "thue_xe") d.planned_pax = 1;
    try { const t = await api("/tours", { method: "POST", json: d }); toast("Đã tạo tour – kiểm tra 3 con số rồi trình Trưởng phòng"); location.href = `/tours/${t.id}`; } catch (x) { toast(errMsg(x), true); }
  }
  const today = new Date().toISOString().slice(0, 10);
  return (<>
    <h1>Tour & dự toán</h1>
    {/* Kho quyết toán cũ T1–T6/2026: nạp và GỠ CẢ LÔ. Đặt ở đây vì đây là chỗ
        người ta nhìn thấy hậu quả của việc nạp — mấy trăm dòng chuyến mới. Ô tự
        ẩn với vai trò không có quyền, và mặc định đóng. */}
    <KhoCuLo onXong={load} />
    {/* Gán tên người bán trong tệp ↔ tài khoản VTOS. Đặt cạnh ô trên vì hai việc đi liền nhau:
        nạp xong thì phần máy không khớp được nằm ở đây, và gán xong thì doanh số về đúng người. */}
    <KhoCuNguoiBan onXong={load} />
    {/* Đóng số bù cho kho cũ, chạy THEO LÔ. Đặt ngay sau hai ô trên vì đây là bước CUỐI của cùng
        một việc: nạp xong, gán người bán xong, thì phải đóng số thì doanh thu và giá vốn mới lên
        báo cáo. Trước 19/9/2026 cửa này chỉ bấm được bằng cách gõ lệnh trong bảng điều khiển
        trình duyệt — một cửa ghi vào 476 chuyến mà chỉ mình người viết nó dùng được. */}
    <KhoCuDongSoBu onXong={load} />
    <p className="muted">
      {chamTran
        ? `Đang hiện ${rows.length} chuyến mới nhất trong ${tong} chuyến khớp bộ lọc — thu hẹp bằng tìm kiếm, tháng hoặc trạng thái để thấy phần còn lại.`
        : `${tong} chuyến khớp bộ lọc.`}
    </p>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
      <input placeholder="Tìm mã tour / tên / mã sản phẩm…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 300 }} />
      <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
      <select value={st} onChange={(e) => setSt(e.target.value)}><option value="">Mọi trạng thái</option>{Object.entries(TOUR_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      <span className="muted">{rows.length} chuyến (tối đa 300 mới nhất)</span>
      {canCreate && <Link href="/products" className="act" style={{ margin: 0 }}>Mở chuyến từ sản phẩm →</Link>}
    </div>
    {canCreate && <details className="panel" open={open} onToggle={(e) => setOpen((e.target as any).open)}>
      <summary style={{ cursor: "pointer", fontWeight: 600, color: "var(--navy)" }}>
        + Tạo tour / dự toán {laKinhDoanh ? "(Kinh doanh Đoàn – chỉ chuyến đoàn)" : "(Điều hành)"}</summary>
      <form onSubmit={create}>
        <div className="grid"><div><label>Mã tour</label><input name="code" required placeholder="VD: PT-DL-1015" /></div>
          <div><label>Loại chuyến</label><select name="tour_type" value={loai} onChange={(e) => setLoai(e.target.value)}>{Object.entries(loaiChoPhep).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div></div>
        {laThueXe && <p className="muted">Hợp đồng thuê xe riêng dựng như một <b>chuyến rút gọn</b>: có mã, có ngày,
          có người phụ trách, để lệnh điều xe gắn vào được. Doanh thu của nó <b>đứng thành một dòng riêng</b> trên
          bảng Kết quả kinh doanh, không cộng vào doanh thu tour và không tính chỉ tiêu doanh số của sale.
          Giá ghi là <b>giá trọn hợp đồng</b>, không phải giá một người.</p>}
        <label>{laThueXe ? "Tên khách thuê và tuyến đi" : "Tên tour"}</label><input name="name" required />
        <div className="grid"><div><label>{laThueXe ? "Ngày bắt đầu thuê" : "Khởi hành"}</label><input type="date" name="start_date" required /></div><div><label>{laThueXe ? "Ngày trả xe" : "Kết thúc"}</label><input type="date" name="end_date" required /></div>
          <div><label>Người điều hành duy nhất</label><select name="operator_id" defaultValue={user?.id}>{ops.map((o) => <option key={o.id} value={o.id}>{o.full_name}</option>)}</select></div></div>
        <h3>{laThueXe ? "Giá thuê và giá vốn" : "Dự toán – tách chi phí cố định / theo khách (ĐH Điều 11)"}</h3>
        <div className="grid"><div><label>{laThueXe ? "Giá thuê trọn hợp đồng (đ)" : "Giá bán / khách (đ)"}</label><input type="number" name="price_per_pax" step="1000" /></div><div><label>{laThueXe ? "Chi phí cố định (dầu, cầu đường, lương lái)" : "Chi phí cố định"}</label><input type="number" name="fixed_cost" step="1000" /></div>
          {!laThueXe && <><div><label>Chi phí theo khách</label><input type="number" name="var_cost_per_pax" step="1000" /></div><div><label>Số khách dự toán</label><input type="number" name="planned_pax" /></div></>}</div>
        {/* Điểm dừng nghỉ KHÔNG bỏ cho hợp đồng thuê xe, và đó là có chủ ý: ĐH Điều 11 là điều về
            giờ nghỉ của người lái, không phải về chương trình tour. Xe chở khách thuê thì điều ấy
            càng áp dụng chứ không kém. Máy chủ cũng vẫn đòi ở cổng trình. */}
        <label>Điểm dừng nghỉ (bắt buộc)</label><input name="rest_stops" />
        {laDoan && <>
          <h3>Hoa hồng dành cho khách (bắt buộc – Chủ tịch quyết 24/9/2026)</h3>
          <p className="muted">Mục 4.2 bản mô tả Sale Admin: hoa hồng và quà tặng dành cho khách phải nằm trong
            giá vốn của chính đoàn này. Bỏ trống ô này thì <b>Sale Admin không chuyển được</b> dự toán sang Điều hành.</p>
          <div className="grid">
            <div><label>Đoàn này có hoa hồng dành cho khách không?</label>
              <select name="hoa_hong_khach" value={hhKhach} onChange={(e) => setHhKhach(e.target.value)}>
                <option value="">— chưa trả lời —</option><option value="khong">Không</option><option value="co">Có</option>
              </select></div>
            <div><label>Số tiền hoa hồng (đ)</label>
              <input type="number" name="hoa_hong_khach_tien" step="1000" disabled={hhKhach !== "co"} placeholder={hhKhach === "co" ? "" : "chỉ điền khi chọn Có"} /></div>
          </div>
        </>}
        <button className="act teal">Lưu nháp</button>
      </form></details>}
    <MangTag mang={mang} />
    <div className="panel wrap"><table><thead><tr><th>Mã</th><th>Tên</th><th>Loại</th><th>Khởi hành</th><th className="num">Biên KH</th><th className="num">Hòa vốn</th><th className="num">Đạt 10%</th><th className="num">Đã bán</th><th>Trạng thái</th><th>Hạn QT</th></tr></thead>
      <tbody>{rows.map((t) => { const c = t.calc; return <tr key={t.id}><td><Link href={`/tours/${t.id}`}>{t.code}</Link></td><td>{t.name}</td><td>{TOUR_TYPES[t.tour_type]}</td><td>{fmtD(t.start_date)}</td>
        <td className="num">{c.complete ? <Tag cls={c.pass_gate ? "ok" : "red"}>{pct(c.margin)}</Tag> : <Tag cls="warn">chưa đủ cơ sở</Tag>}</td><td className="num">{c.breakeven_pax ?? "–"}</td><td className="num">{c.pax_for_margin ?? "–"}</td>
        <td className="num">{t.booked_pax} {t.d7_flag && <Tag cls="red">D-7</Tag>}</td><td>{TOUR_STATUS[t.status]} {t.below_margin && <Tag cls="warn">dưới biên</Tag>}</td>
        <td>{fmtD(t.settlement_deadline)} {t.status === "ket_thuc" && today > t.settlement_deadline && <Tag cls="red">quá hạn</Tag>}</td></tr>; })}</tbody></table></div>
  </>);
}
export default function Page() { return <Shell><Suspense><Tours /></Suspense></Shell>; }
