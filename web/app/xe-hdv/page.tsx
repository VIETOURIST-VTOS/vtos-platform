"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Xe Vietrip & HDV – màn hình của chính người ở hiện trường (chỉ đạo 07/9/2026).
 *  Tài xế và hướng dẫn viên được cấp tài khoản nhưng chỉ thấy việc của mình: xe mình đứng tên, lệnh điều
 *  xe của mình, chuyến mình dẫn và hạn thẻ HDV. Không thấy giá xe nội bộ, không thấy hàng đợi của cả đội. */
function XeHdv() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api("/xe-hdv/cua-toi").then(setD).catch((x) => { setErr(errMsg(x)); toast(errMsg(x), true); }); }, []); // eslint-disable-line

  if (err) return <><h1>Xe Vietrip &amp; HDV</h1><p className="muted">{err}</p></>;
  if (!d) return <p className="muted">Đang tải…</p>;
  const st = (s: string) => s === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : s === "da_xac_nhan" ? <Tag cls="navy">Đã xác nhận</Tag> : s === "huy" ? <Tag cls="red">Hủy</Tag> : <Tag cls="warn">Chờ xác nhận</Tag>;

  return (<>
    <h1>Xe Vietrip &amp; HDV</h1>
    <div className="panel"><h2>{d.ho_so.full_name} <span className="muted">· mã {d.ho_so.code}</span></h2>
      <p className="muted">{d.ho_so.department_name} · {d.ho_so.position_name}{d.ho_so.phone ? ` · ${d.ho_so.phone}` : ""}</p></div>

    {d.the_hdv && <div className="panel"><h2>Thẻ hướng dẫn viên</h2>
      <p>Số thẻ <b className="mono">{d.the_hdv.card_no || "—"}</b> · hạn <b>{fmtD(d.the_hdv.card_expiry)}</b>{" "}
        {d.the_hdv.du_dieu_kien ? <Tag cls="ok">Đủ điều kiện dẫn đoàn</Tag> : <Tag cls="red">Chưa đủ điều kiện</Tag>}</p>
      {!d.the_hdv.du_dieu_kien && <p className="muted">{d.the_hdv.vi_sao} – liên hệ Điều hành hoặc HCNS để cập nhật hồ sơ trước khi nhận chuyến.</p>}</div>}

    {d.xe.length > 0 && <div className="panel wrap"><h2>Xe tôi đứng tên</h2>
      <table><thead><tr><th>Biển số</th><th className="num">Chỗ</th><th>Loại</th><th>Pháp nhân sở hữu</th><th>Trạng thái</th></tr></thead>
        <tbody>{d.xe.map((v: any) => <tr key={v.id}><td><b>{v.plate}</b></td><td className="num">{v.seats || "—"}</td><td>{v.kind}</td><td>{v.company || <Tag cls="warn">chưa gán</Tag>}</td>
          <td>{v.active ? <Tag cls="ok">Đang khai thác</Tag> : <Tag cls="red">Ngưng khai thác</Tag>}</td></tr>)}</tbody></table></div>}

    {d.lenh_dieu_xe.length > 0 && <div className="panel wrap"><h2>Lệnh điều xe của tôi</h2>
      <table><thead><tr><th>Tour</th><th>Xe</th><th>Thời gian</th><th className="num">Số ngày</th><th>Trạng thái</th><th>Xác nhận lúc</th><th>Sự cố</th></tr></thead>
        <tbody>{d.lenh_dieu_xe.map((x: any) => <tr key={x.id}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td><td className="mono">{x.vehicle}</td>
          <td>{fmtD(x.date_from)} → {fmtD(x.date_to)}</td><td className="num">{x.days}</td><td>{st(x.status)}</td><td>{fmtDT(x.confirmed_at)}</td><td className="muted">{x.incident_note}</td></tr>)}</tbody></table></div>}

    {d.phan_chuyen.length > 0 && <div className="panel wrap"><h2>Chuyến tôi dẫn</h2>
      <table><thead><tr><th>Tour</th><th>Khởi hành</th><th className="num">Số ngày</th><th className="num">Thù lao</th><th>Trạng thái</th><th>Báo cáo</th><th>Tạm ứng</th></tr></thead>
        <tbody>{d.phan_chuyen.map((x: any) => <tr key={x.id}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td><td>{fmtD(x.start_date)}</td>
          <td className="num">{x.days}{x.holiday && <Tag cls="warn">lễ ×2</Tag>}</td><td className="num">{vnd(x.amount)}</td><td>{st(x.status)}</td>
          <td>{x.report_submitted ? <Tag cls="ok">Đã nộp</Tag> : <Tag cls="warn">Chưa nộp</Tag>}</td>
          <td>{x.advance_settled ? <Tag cls="ok">Đã quyết toán</Tag> : <Tag cls="warn">Chưa</Tag>}</td></tr>)}</tbody></table></div>}

    {d.xe.length === 0 && d.lenh_dieu_xe.length === 0 && d.phan_chuyen.length === 0 &&
      <p className="muted">Chưa có xe, lệnh điều xe hay chuyến nào gắn với hồ sơ của bạn. Nếu sai, báo Điều hành hoặc HCNS.</p>}
  </>);
}

export default function Page() { return <Shell><XeHdv /></Shell>; }
