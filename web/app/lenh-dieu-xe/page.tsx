"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lệnh điều xe – Đợt 4.
 *
 *  Màn hình này gợi ý, không quyết. Đặc tả đặt ranh giới rõ: "Không để quyết định cho xe xuất bến phụ thuộc
 *  vào kết luận của mô hình ngôn ngữ." Nên phần lọc và xếp hạng là mã xác định, còn người chốt lệnh vẫn là
 *  người quyết — và nếu chọn khác gợi ý thì phải ghi lý do. */
function LenhDieuXe() {
  const { toast } = useShell();
  const [tu, setTu] = useState(new Date().toISOString().slice(0, 10));
  const [den, setDen] = useState(new Date().toISOString().slice(0, 10));
  const [khach, setKhach] = useState(0);
  const [km, setKm] = useState(0);
  const [gy, setGy] = useState<any>(null);
  const [ds, setDs] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setDs(await api("/fleet/lenh-dieu-xe")); } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const chay = async () => {
    setBusy(true);
    try { setGy(await api(`/fleet/goi-y-dieu-xe?date_from=${tu}&date_to=${den}&so_khach=${khach}&km_du_kien=${km}`)); }
    catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  return (<>
    <h1>Lệnh điều xe</h1>
    <p className="muted">Hệ thống <b>lọc cứng trước, xếp hạng sau</b>: xe vi phạm điều kiện không xuất hiện trong gợi ý dù điểm có cao đến đâu. Đây là gợi ý — người chốt lệnh vẫn quyết, và chọn khác gợi ý thì phải ghi lý do.</p>

    <div className="panel"><h2>Tìm phương án cho một khoảng ngày</h2>
      <div className="grid">
        <div><label>Từ ngày</label><input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></div>
        <div><label>Đến ngày</label><input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></div>
        <div><label>Số khách</label><input type="number" value={khach} onChange={(e) => setKhach(Number(e.target.value))} /></div>
        <div><label>Km dự kiến (gồm chạy rỗng)</label><input type="number" value={km} onChange={(e) => setKm(Number(e.target.value))} /></div>
      </div>
      <button className="act teal" onClick={chay} disabled={busy}>{busy ? "Đang tính…" : "Xem phương án"}</button>
    </div>

    {gy && <>
      <div className="panel"><h2>Phương án đề xuất ({gy.phuong_an.length})</h2>
        <p className="muted">{gy.ghi_chu} <span className="muted">Bộ quy tắc {gy.rule_version}.</span></p>
        {gy.phuong_an.length ? <table><thead><tr><th>#</th><th>Xe</th><th>Chỗ</th><th>Điểm</th><th>Vì sao đề xuất</th><th>Điều kiện</th></tr></thead>
          <tbody>{gy.phuong_an.map((p: any, i: number) => <tr key={p.vehicle_id}>
            <td><b>{i + 1}</b></td><td>{p.ma_xe} · {p.xe}</td><td className="num">{p.so_cho}</td>
            <td className="num">{p.diem}</td>
            <td>{p.ly_do.join(" · ")}</td>
            <td><Tag cls={p.muc_kiem_tra === "OK" ? "ok" : "warn"}>{p.muc_kiem_tra === "OK" ? "Đạt" : p.muc_kiem_tra === "UNKNOWN" ? "Chưa đủ dữ liệu" : "Cần xem lại"}</Tag></td>
          </tr>)}</tbody></table>
          : <p className="muted">Không còn xe nào hợp lệ cho khoảng ngày này.</p>}
        {gy.con_lai > 0 && <p className="muted">Còn {gy.con_lai} xe hợp lệ khác không nằm trong nhóm đề xuất.</p>}
      </div>

      {gy.bi_loai.length > 0 && <div className="panel wrap"><h2>Xe bị loại ({gy.bi_loai.length})</h2>
        <p className="muted">Loại ở bước lọc cứng — không phải điểm thấp, mà là không đủ điều kiện.</p>
        <table><thead><tr><th>Xe</th><th>Lý do loại</th></tr></thead>
          <tbody>{gy.bi_loai.map((b: any) => <tr key={b.vehicle_id}>
            <td>{b.ma_xe} · {b.xe}</td><td>{b.ly_do.map((l: string, i: number) => <div key={i}><Tag cls="red">chặn</Tag> {l}</div>)}</td>
          </tr>)}</tbody></table>
      </div>}
    </>}

    <div className="panel wrap"><h2>Lệnh đã lập ({ds.length})</h2>
      <p className="muted">Cột cuối ghi vết: lệnh theo gợi ý hay chọn khác, và lý do khi chọn khác. Đây là dữ liệu để mỗi quý đánh giá lại chất lượng thuật toán gợi ý.</p>
      <table><thead><tr><th>#</th><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Từ → đến</th><th>Giá nội bộ</th><th>Trạng thái</th><th>Ghi vết gợi ý</th></tr></thead>
        <tbody>{ds.length ? ds.map((d) => <tr key={d.id}>
          <td>{d.id}</td><td>{d.tour}</td><td>{d.ma_xe} · {d.xe}</td><td>{d.tai_xe}</td>
          <td>{fmtD(d.date_from)} → {fmtD(d.date_to)} <span className="muted">({d.so_ngay} ngày)</span></td>
          <td className="num">{d.internal_price?.toLocaleString("vi-VN")}</td>
          <td>{d.status === "hoan_thanh" ? <Tag cls="ok">hoàn thành</Tag> : d.status === "da_xac_nhan" ? <Tag cls="ok">đã xác nhận</Tag> : d.status === "huy" ? <Tag cls="red">hủy</Tag> : <Tag cls="warn">chờ xác nhận</Tag>}</td>
          <td>{d.ly_do_khac_goi_y ? <><Tag cls="warn">chọn khác gợi ý</Tag> <div className="muted">{d.ly_do_khac_goi_y}</div></>
            : d.phuong_an_da_chon ? <Tag cls="ok">theo gợi ý</Tag> : <span className="muted">lệnh cũ, chưa có ghi vết</span>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có lệnh điều xe nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><LenhDieuXe /></Shell>; }
