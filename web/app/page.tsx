"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, pct, vnd, fmtD, fmtDT } from "@/lib/api";
import { ACTION_LABEL } from "@/lib/meta";
import { Tag } from "@/components/ui";

function Dash() {
  const { user } = useShell();
  const [d, setD] = useState<any>(null);
  useEffect(() => { api("/dashboard").then(setD).catch(() => {}); }, []);
  if (!d) return <p className="muted">Đang tải…</p>;
  const c = d.counts || {};
  const k = d.kpis || {}; const sec = d.sections || {};
  return (<>
    <h1>Bảng điều khiển · {user?.role_name}</h1>
    {d.approvals?.length > 0 && <div id="cho-toi-duyet" className="panel" style={{ borderColor: "var(--orange)" }}><b>Việc chờ tôi xử lý:</b> {d.approvals.map((a: any, i: number) => <Link key={i} href={a.href} className="act orange" style={{ display: "inline-block", textDecoration: "none", margin: "4px 6px 0 0" }}>{a.label}</Link>)}</div>}
    {"tien" in k && <div className="kpis">
      <div className="kpi"><b>{vnd(k.tien)}</b><span>Tiền (111+112)</span></div><div className="kpi"><b>{vnd(k.no_vay)}</b><span>Dư nợ vay</span></div><div className="kpi"><b>{vnd(k.phai_thu)}</b><span>Phải thu khách</span></div>
      <div className="kpi"><b style={{ color: k.du_bao_canh_bao ? "var(--red)" : undefined }}>{k.du_bao_canh_bao}</b><span>Tuần cảnh báo dòng tiền (13 tuần)</span></div><div className="kpi"><b>{vnd(k.ln_ke_toan_thang)}</b><span>LN kế toán tháng (trước thuế)</span></div>
    </div>}
    <div className="kpis">
      <div className="kpi"><b>{vnd(k.doanh_thu_thang)}</b><span>Doanh thu quyết toán tháng ({k.so_chuyen_thang} chuyến KT xác nhận)</span></div><div className="kpi"><b>{vnd(k.loi_nhuan_thang)}</b><span>Lợi nhuận chuyến tháng · {k.chuyen_duoi_10} chuyến dưới 10%</span></div>
      <div className="kpi"><b>{k.booking_thang}</b><span>Booking tháng · {vnd(k.doanh_thu_booking_thang)} đ</span></div><div className="kpi"><b style={{ color: k.canh_bao_do ? "var(--red)" : undefined }}>{k.canh_bao_do}</b><span>Cảnh báo đỏ đang mở</span></div>
    </div>
    <div className="kpis">
      <div className="kpi"><b>{d.n_tours}</b><span>tour trên hệ thống</span></div>
      <div className="kpi"><b>{c.da_duyet || 0}</b><span>đang bán (đã duyệt)</span></div>
      <div className="kpi"><b>{(c.ket_thuc || 0) + (c.da_dong_so || 0)}</b><span>chờ quyết toán / Kế toán</span></div>
      <div className="kpi"><b>{d.pending_requests}</b><span>yêu cầu chưa tạo booking</span></div>
      <div className="kpi"><b style={{ color: "var(--red)" }}>{d.alerts.length}</b><span>cảnh báo mở cho vai trò này</span></div>
    </div>
    <div className="grid" style={{ marginTop: 14 }}>
      <div id="viec-cua-toi" className="panel"><h2>Việc cần xử lý</h2>
        {d.todo.length ? <ul>{d.todo.map((t: any, i: number) => <li key={i}><Link href={`/tours/${t.tour_id}`}>{t.code}</Link> – {t.name}: <b>{ACTION_LABEL[t.action] || t.action}</b></li>)}</ul> : <p className="muted">Không có việc chờ ở vai trò này.</p>}
        {d.pending_params > 0 && ["chutich", "tgd"].includes(user?.role || "") && <p><Link href="/params">{d.pending_params} tham số chính sách chờ ký</Link></p>}
      </div>
      <div className="panel"><h2>Cảnh báo từ robot</h2>
        {d.alerts.length ? <table><tbody>{d.alerts.map((a: any) => <tr key={a.id}><td><Tag cls={a.level}>{a.kind}</Tag></td><td>{a.message}</td></tr>)}</tbody></table> : <p className="muted">Không có cảnh báo.</p>}
      </div>
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
