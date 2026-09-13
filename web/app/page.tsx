"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT } from "@/lib/api";
import { ACTION_LABEL } from "@/lib/meta";
import { Tag, errMsg } from "@/components/ui";
import KhoiDongTien from "@/components/KhoiDongTien";
import KhoiTonDong from "@/components/KhoiTonDong";
import {
  DongLoc, KhoiQuyetDinh, TamThe, TieuDe, tien, dem, type The,
} from "@/components/DauManHinh01";

function Dash() {
  const { user } = useShell();
  const [d, setD] = useState<any>(null);
  // Trước đây lỗi bị nuốt bằng .catch(() => {}) nên máy chủ trả 500 mà người dùng chỉ thấy
  // "Đang tải…" đứng im vĩnh viễn – lỗi PostgreSQL ngày 07/9 sống sót nhiều ngày vì đúng chỗ này.
  const [loi, setLoi] = useState<string>("");
  const tai = () => { setLoi(""); api("/dashboard").then(setD).catch((e) => setLoi(errMsg(e) || "Không tải được bảng điều khiển")); };
  useEffect(tai, []);
  if (loi) return <div className="panel" style={{ borderColor: "var(--red)" }}>
    <b style={{ color: "var(--red)" }}>Không tải được bảng điều khiển.</b>
    <div className="muted" style={{ margin: "6px 0" }}>{loi}</div>
    <div className="muted">Các màn hình khác vẫn dùng được. Nếu lặp lại, báo CNTT kèm nguyên văn dòng trên.</div>
    <button className="act" onClick={tai}>Thử lại</button>
  </div>;
  if (!d) return <p className="muted">Đang tải…</p>;
  const c = d.counts || {};
  const k = d.kpis || {}; const sec = d.sections || {};

  /* TÁM THẺ CHỈ TIÊU theo bản vẽ V1.2. Mỗi thẻ chỉ ra đúng một con số chính, một dòng so sánh và
     một dòng trạng thái dữ liệu – không nhồi ba số vào một ô như hàng KPI cũ.

     KỲ BÁO CÁO: màn hình này CHỈ theo THÁNG (anh Tuấn chốt 13/9). Quý và năm xem ở báo cáo chi
     tiết – hàng lọc có đường dẫn sang đó. Nhờ vậy tám thẻ không phải mang theo một nhánh "nếu
     chọn quý thì rỗng", và không có chỗ nào lấy số tháng dán nhãn quý. */
  const tam: The[] = [
    /* Bản vẽ V1.4 chốt dòng phụ của thẻ này là "so với kế hoạch và kỳ trước". Máy chủ chưa có kế
       hoạch tháng và chưa trả kết quả kỳ trước, nên KHÔNG bịa một tỷ lệ phần trăm: ghi thẳng là
       chưa có nguồn so sánh và ai phải nhập. Một mũi tên tăng-giảm dựng từ số không có thật thì
       Chủ tịch đọc là kết quả, chứ không đọc là chỗ trống. */
    { nhan: "Doanh thu tháng", so: tien(k.doanh_thu_thang),
      duoi: `${k.so_chuyen_thang ?? 0} chuyến đã quyết toán · chưa có kế hoạch tháng và kỳ trước để so sánh (Kế toán)` },
    { nhan: "Lợi nhuận trước thuế", so: tien(k.ln_ke_toan_thang),
      duoi: "Lợi nhuận kế toán tháng, cùng phạm vi" },
    /* Bản vẽ chốt dòng phụ là "Khách đã chốt / chỗ còn". Máy chủ chưa trả sức chứa từng chuyến nên
       chưa tính được "chỗ còn" – ghi ra chỗ thiếu, không thay bằng con số khác rồi để người đọc
       tưởng đó là chỗ còn. */
    { nhan: "Tour đang bán", so: dem(c.da_duyet ?? 0),
      duoi: `${d.n_tours ?? 0} tour trên hệ thống · chưa có sức chứa từng chuyến nên chưa tính được chỗ còn (Điều hành)` },
    { nhan: "Tour chờ quyết toán", so: dem((c.ket_thuc || 0) + (c.da_dong_so || 0)),
      duoi: `${sec.qua_han_qt?.length ?? 0} chuyến quá hạn quyết toán`,
      do: (sec.qua_han_qt?.length ?? 0) > 0 },
    { nhan: "Tour sắp khởi hành", so: dem(sec.sap_khoi_hanh?.length),
      duoi: "21 ngày tới (bản vẽ ghi 14 – máy chủ đang tính 21)",
      ai: "Điều hành", cua: "/tours" },
    { nhan: "Đội xe hôm nay", so: null,
      ai: "Đội xe", cua: "/doi-xe",
      duoi: "Đang chạy / đủ điều kiện · xe trống · bảo dưỡng" },
    { nhan: "Marketing & PR", phu: "Khách tiềm năng mới", so: null,
      ai: "Marketing", cua: "/leads?tab=leads",
      duoi: "Đã chuyển Kinh doanh · đã chốt" },
    /* SỬA 13/9/2026 – thẻ này từng in `d.alerts.length`, tức SỐ DÒNG máy chủ gửi kèm trang này
       (đang cắt ở 60), chứ không phải số tồn đọng thật. Trên bản chạy thật nó ra "60" trong khi
       dòng phụ ngay dưới ghi "1387 cảnh báo đỏ đang mở": con số nhỏ nằm ở chỗ to nhất màn hình,
       con số thật nằm ở dòng chữ nhỏ. Nay lấy đúng `k.canh_bao_do`; nếu máy chủ không gửi thì thẻ
       để trống kèm cửa nhập, không lấy độ dài danh sách thay vào. */
    /* Bản vẽ chốt ba chỉ số: hồ sơ quá hạn · nghiêm trọng · chưa có người nhận. Máy chủ mới có
       "nghiêm trọng" (cảnh báo đỏ); chưa gán người nhận cho cảnh báo nên chưa đếm được cái thứ ba,
       và chưa tách hồ sơ quá hạn ra khỏi cảnh báo đỏ. Nói ra hai cái còn thiếu. */
    { nhan: "Tồn đọng cần xử lý", so: dem(k.canh_bao_do),
      duoi: "cảnh báo mức nghiêm trọng · chưa tách được hồ sơ quá hạn và hồ sơ chưa có người nhận (CNTT)",
      do: (k.canh_bao_do ?? 0) > 0, ai: "Công nghệ thông tin", cua: "/alerts" },
  ];

  return (<>
    <TieuDe vai={user?.role} ten_vai={user?.role_name} />
    <DongLoc />
    <KhoiQuyetDinh ds={d.approvals || []} vai={user?.role} />
    <TamThe ds={tam} />
    {/* Khối dòng tiền đứng SAU tám thẻ theo bản vẽ V1.2: thẻ trả lời "kết quả thế nào", dòng tiền
        trả lời "còn bao nhiêu và sắp hụt ngày nào". Khối tự ẩn với vai không được xem – không vẽ
        một khung rỗng để người ta dò xem trong đó có gì. */}
    <KhoiDongTien />
    <div className="grid" style={{ marginTop: 14 }}>
      <div id="viec-cua-toi" className="panel"><h2>Việc cần xử lý</h2>
        {d.todo.length ? <ul>{d.todo.map((t: any, i: number) => <li key={i}><Link href={`/tours/${t.tour_id}`}>{t.code}</Link> – {t.name}: <b>{ACTION_LABEL[t.action] || t.action}</b></li>)}</ul> : <p className="muted">Không có việc chờ ở vai trò này.</p>}
        {d.pending_params > 0 && ["chutich", "tgd"].includes(user?.role || "") && <p><Link href="/params">{d.pending_params} tham số chính sách chờ ký</Link></p>}
      </div>
      {/* Bảng cảnh báo phẳng cũ đã thay bằng khối gom nhóm: sáu mươi dòng gần giống hệt nhau thì
          cuộn hết màn hình mà vẫn không cho biết tồn đọng nằm ở đâu. Danh sách từng dòng vẫn còn,
          nằm trong phần bung ra của khối. */}
      <KhoiTonDong ds={d.alerts || []} tong={k.canh_bao_do ?? null} />
    </div>
    <div className="grid" style={{ marginTop: 14 }}>
      {sec.kd_le && <div className="panel"><h2>Kinh doanh Lẻ – doanh thu tính chỉ tiêu tháng (quyết toán)</h2><p className="muted"><Link href="/sales-reports?mang=le">Báo cáo bán hàng phòng Lẻ →</Link></p>{sec.kd_le.length ? <table><tbody>{sec.kd_le.map((r: any) => <tr key={r.sales}><td>{r.sales}</td><td style={{ textAlign: "right" }}>{vnd(r.revenue)}</td><td>{Math.round(r.pct * 100)}% mốc {r.pct >= 1 ? <Tag cls="ok">đạt</Tag> : <Tag cls="warn">chưa</Tag>}</td></tr>)}</tbody></table> : <p className="muted">Chưa có chuyến quyết toán trong tháng.</p>}</div>}
      {sec.kd_doan && <div className="panel"><h2>Kinh doanh Đoàn (MICE) – lợi nhuận chia tháng (quyết toán)</h2>
        <p className="muted">Phòng Đoàn hưởng theo <b>chia lợi nhuận</b> chuyến đã quyết toán, không theo mốc doanh thu như phòng Lẻ – nên bảng này là lợi nhuận, không phải doanh thu. Số chính thức nằm ở bảng lương.</p>
        {sec.kd_doan.rows.length ? <table><tbody>{sec.kd_doan.rows.map((r: any) => <tr key={r.sales}><td>{r.sales}</td><td style={{ textAlign: "right" }}>{vnd(r.profit_share)}</td><td>{r.profit_share > 0 ? <Tag cls="ok">có lãi</Tag> : <Tag cls="red">lỗ</Tag>}</td></tr>)}</tbody></table>
          : <p className="muted">Chưa có chuyến đoàn quyết toán trong tháng.</p>}
        <p className="muted">{sec.kd_doan.so_chuyen} chuyến đoàn đã quyết toán trong tháng. <Link href="/sales-reports?mang=doan">Báo cáo bán hàng phòng Đoàn →</Link></p></div>}
      {sec.sap_khoi_hanh && <div className="panel"><h2>Điều hành – chuyến khởi hành 21 ngày tới</h2>{sec.sap_khoi_hanh.length ? <table><tbody>{sec.sap_khoi_hanh.map((r: any) => <tr key={r.code}><td>{r.code}</td><td>{fmtD(r.start)} (D-{r.days_left})</td><td>{r.booked}/{r.breakeven} khách {r.below ? <Tag cls="red">dưới hòa vốn</Tag> : <Tag cls="ok">ok</Tag>}</td></tr>)}</tbody></table> : <p className="muted">Không có chuyến.</p>}{sec.qua_han_qt?.length > 0 && <p><Tag cls="red">Quá hạn quyết toán</Tag> {sec.qua_han_qt.map((t: any) => t.code).join(", ")}</p>}</div>}
      {sec.bao_cao_ngay && <div className="panel"><h2>Báo cáo ngày (Điều 12) – tháng này</h2><p>{sec.bao_cao_ngay.nhan_su} nhân sự · {sec.bao_cao_ngay.ngay_lam_viec} ngày làm việc · tỷ lệ nộp <b>{Math.round(sec.bao_cao_ngay.ty_le_nop * 100)}%</b> · thiếu 2 ngày liên tiếp: {sec.bao_cao_ngay.thieu_2_ngay}</p><Link href="/reports">Xem tổng hợp</Link></div>}
    </div>
    <p className="muted">Ngưỡng biên đang áp dụng {pct(d.threshold)} · Robot chạy mỗi 10 phút; CNTT có thể chạy tay ở trang Cảnh báo.</p>
  </>);
}
export default function Page() { return <Shell><Dash /></Shell>; }
