"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Chi phí & hiệu quả đội xe – Đợt 4.
 *
 *  Ô ghi "chưa đủ dữ liệu" là chưa tính được, KHÔNG phải bằng 0. Điểm này quan trọng hơn nó trông có vẻ:
 *  0 đồng/km sẽ đứng đầu bảng xếp hạng tiết kiệm nhiên liệu, và đó lại đúng là chiếc xe chưa có số liệu nào. */
const CHUA_DU = "chua_du_du_lieu";
const so = (v: any) => (v === CHUA_DU || v === null || v === undefined)
  ? <span className="muted">chưa đủ dữ liệu</span> : Number(v).toLocaleString("vi-VN");

function HieuQua() {
  const { toast } = useShell();
  const [ky, setKy] = useState(new Date().toISOString().slice(0, 7));
  const [d, setD] = useState<any>(null);
  const [bt, setBt] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const chay = useCallback(async () => {
    setBusy(true);
    try { setD(await api(`/fleet/hieu-qua?ky=${ky}`)); } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  }, [ky, toast]);
  useEffect(() => { chay(); }, [chay]);
  useEffect(() => { api("/fleet/ban-tin-sang").then(setBt).catch(() => {}); }, []);

  return (<>
    <h1>Chi phí & hiệu quả đội xe</h1>

    {bt && <div className="panel" style={{ borderColor: bt.canh_bao_do?.length ? "var(--red)" : undefined }}>
      <h2>Bản tin sáng · {bt.ngay}</h2>
      {bt.canh_bao_do?.length > 0 && <div style={{ marginBottom: 8 }}>
        {bt.canh_bao_do.map((a: any) => <div key={a.id}><Tag cls="red">{a.kind}</Tag> {a.message}</div>)}
      </div>}
      <p>{bt.xe_chay_hom_nay.length} xe có lệnh hôm nay · {bt.xe_ranh.length} xe không có lệnh · {bt.so_canh_bao_vang} cảnh báo vàng · {bt.ky_quyet_toan_chua_dong} kỳ quyết toán chưa đóng</p>
      {bt.xe_chay_hom_nay.length > 0 && <table><tbody>{bt.xe_chay_hom_nay.map((x: any, i: number) => <tr key={i}>
        <td>{x.ma_xe} · {x.xe}</td><td>{x.tai_xe}</td><td>{x.tour}</td>
        <td>{x.trang_thai === "da_xac_nhan" ? <Tag cls="ok">đã xác nhận</Tag> : <Tag cls="warn">chờ xác nhận</Tag>}</td>
      </tr>)}</tbody></table>}
      <p className="muted">{bt.ghi_chu}</p>
    </div>}

    <div className="panel"><h2>Kỳ đánh giá</h2>
      <label>Tháng<input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
      <button className="act teal" onClick={chay} disabled={busy}>{busy ? "Đang tính…" : "Chạy lại"}</button>
    </div>

    {d && <>
      <div className="panel wrap"><h2>Hiệu quả từng xe – kỳ {d.ky} ({d.tap_so_sanh_xe} xe)</h2>
        <p className="muted">{d.ghi_chu}</p>
        <table><thead><tr><th>Hạng</th><th>Xe</th><th>Chuyến</th><th>Ngày khai thác</th><th>Km</th><th>Doanh thu</th><th>Chi phí</th><th>Lợi nhuận</th><th>LN/ngày</th><th>Dầu đ/km</th><th>km/lít</th><th>Sửa chữa/km</th></tr></thead>
          <tbody>{d.xe.length ? d.xe.map((r: any) => <tr key={r.vehicle_id}>
            <td><b>{r.hang}</b></td><td>{r.ma_xe} · {r.xe}</td>
            <td className="num">{r.so_chuyen}</td><td className="num">{r.ngay_khai_thac}</td>
            <td className="num">{r.km.toLocaleString("vi-VN")}</td>
            <td className="num">{so(r.doanh_thu)}</td><td className="num">{so(r.chi_phi)}</td>
            <td className="num" style={{ color: r.loi_nhuan < 0 ? "var(--red)" : undefined }}>{so(r.loi_nhuan)}</td>
            <td className="num">{so(r.loi_nhuan_moi_ngay)}</td><td className="num">{so(r.dau_dong_tren_km)}</td>
            <td className="num">{so(r.km_moi_lit)}</td><td className="num">{so(r.sua_chua_tren_km)}</td>
          </tr>) : <tr><td colSpan={12} className="muted">Kỳ này chưa có chuyến nào được ghi nhật trình.</td></tr>}</tbody></table>
      </div>

      <div className="panel wrap"><h2>Hiệu quả từng tài xế ({d.tap_so_sanh_tai_xe} người)</h2>
        <p className="muted"><b>{d.gioi_han}</b> Số liệu tính theo người <b>thực hiện từng chuyến</b>, không theo tài xế hiện tại của xe.</p>
        <table><thead><tr><th>Hạng</th><th>Tài xế</th><th>Chuyến</th><th>Ngày công</th><th>Km</th><th>Doanh thu</th><th>Chi phí</th><th>Lợi nhuận</th><th>Dầu đ/km</th></tr></thead>
          <tbody>{d.tai_xe.length ? d.tai_xe.map((r: any) => <tr key={r.driver_id}>
            <td><b>{r.hang}</b></td><td>{r.tai_xe}</td>
            <td className="num">{r.so_chuyen}</td><td className="num">{r.ngay_khai_thac}</td>
            <td className="num">{r.km.toLocaleString("vi-VN")}</td>
            <td className="num">{so(r.doanh_thu)}</td><td className="num">{so(r.chi_phi)}</td>
            <td className="num" style={{ color: r.loi_nhuan < 0 ? "var(--red)" : undefined }}>{so(r.loi_nhuan)}</td>
            <td className="num">{so(r.dau_dong_tren_km)}</td>
          </tr>) : <tr><td colSpan={9} className="muted">Kỳ này chưa có chuyến nào có tài xế.</td></tr>}</tbody></table>
      </div>
    </>}
  </>);
}

export default function Page() { return <Shell><HieuQua /></Shell>; }
