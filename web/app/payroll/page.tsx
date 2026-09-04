"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { errMsg } from "@/components/ui";

function Payroll() {
  const { toast } = useShell();
  const [ym, setYm] = useState(new Date().toISOString().slice(0, 7)); const [d, setD] = useState<any>(null);
  useEffect(() => { api(`/payroll?ym=${ym}`).then(setD).catch((e) => toast(errMsg(e), true)); }, [ym, toast]);
  return (<>
    <h1>Bản nháp thu nhập biến đổi – Robot Lương</h1>
    <div className="panel" style={{ maxWidth: 340 }}><label>Tháng (theo tháng Kế toán xác nhận)</label><input type="month" value={ym} onChange={(e) => setYm(e.target.value)} /></div>
    <div className="panel wrap"><table><thead><tr><th>Người</th><th>Khoản</th><th className="num">Số chuyến</th><th className="num">Tiền (đ)</th></tr></thead>
      <tbody>{d?.rows?.length ? d.rows.map((r: any, i: number) => <tr key={i}><td>{r.nguoi}</td><td>{r.khoan}</td><td className="num">{r.so_chuyen}</td><td className="num">{vnd(r.tien)}</td></tr>) : <tr><td colSpan={4} className="muted">Chưa có chuyến nào được Kế toán xác nhận trong tháng.</td></tr>}
        <tr><td colSpan={3}><b>Tổng</b></td><td className="num"><b>{vnd(d?.total)}</b></td></tr></tbody></table>
      <p className="muted">Chỉ tính từ chuyến Kế toán đã xác nhận. Kế toán xác nhận cơ sở → HCNS lập bảng lương → Kế toán kiểm tra → TGĐ ký lô (ĐC Điều 5).</p></div>
  </>);
}
export default function Page() { return <Shell><Payroll /></Shell>; }
