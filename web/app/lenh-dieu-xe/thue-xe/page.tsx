"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec from "@/components/ThanhViec";

/** R5-30 · HỢP ĐỒNG THUÊ XE ĐỘI XE TỰ NHẬN (Chủ tịch 14/11/2026: phương án B; «CT duyệt, TGĐ thấy»; duyệt mẫu).
 *
 *  Giám đốc đội xe tạo hợp đồng ngay trên bàn Đội xe (chỉ loại thuê xe, không tạo tour), trình thẳng Chủ tịch.
 *  Duyệt xong bấm «Lập lệnh»: máy tạo một đề nghị xe thay Điều hành rồi mở màn lập lệnh đã điền sẵn — mọi luật
 *  của lệnh giữ nguyên. Luật ở máy chủ: `backend/app/services/hop_dong_thue_xe.py`. */

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/lenh-dieu-xe">Lệnh điều xe</a> · Hợp đồng thuê xe</>;
const RONG = { ma: "", khach: "", lo_trinh: "", ngay_di: "", ngay_ve: "", so_xe: "1", so_khach: "", gia: "", chi_phi: "", diem_dung: "" };
const so = (v: string) => Number(String(v).replace(/[^\d]/g, "")) || 0;

function HopDongThueXe() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(undefined);
  const [f, setF] = useState<any>(RONG);
  const [busy, setBusy] = useState(false);
  const [giaiTrinh, setGiaiTrinh] = useState<{ id: number; text: string } | null>(null);
  const load = useCallback(async () => {
    try { setD(await api("/fleet/hop-dong-thue-xe")); } catch (e) { toast(errMsg(e), true); setD(null); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const dat = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });

  const luu = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true);
    try {
      const r: any = await api("/fleet/hop-dong-thue-xe", { method: "POST", json: {
        ...f, so_xe: so(f.so_xe), so_khach: so(f.so_khach), gia: so(f.gia), chi_phi: so(f.chi_phi) } });
      toast(r.message); setF(RONG); await load();
    } catch (x) { toast(errMsg(x), true); }
    setBusy(false);
  };
  const trinh = async (id: number, text = "") => {
    setBusy(true);
    try {
      const r: any = await api(`/fleet/hop-dong-thue-xe/${id}/trinh`, { method: "POST", json: { giai_trinh: text } });
      toast(r.message); setGiaiTrinh(null); await load();
    } catch (x) {
      const m = errMsg(x); toast(m, true);
      if (m.includes("giải trình")) setGiaiTrinh({ id, text });
    }
    setBusy(false);
  };
  const duyet = async (id: number) => {
    setBusy(true);
    try { const r: any = await api(`/tours/${id}/approve`, { method: "POST", json: {} }); toast(r.message || "Đã duyệt"); await load(); }
    catch (x) { toast(errMsg(x), true); }
    setBusy(false);
  };
  const lapLenh = async (id: number) => {
    setBusy(true);
    try {
      const r: any = await api(`/fleet/hop-dong-thue-xe/${id}/lap-lenh`, { method: "POST" });
      window.location.href = `/lenh-dieu-xe/lap-lenh?de_nghi=${r.de_nghi_id}`;
    } catch (x) { toast(errMsg(x), true); setBusy(false); }
  };

  return (<>
    <ThanhViec duong={DUONG} viec={[{ nhan: "‹ Lệnh đã lập", href: "/lenh-dieu-xe", len: true }]} />
    <h1>Hợp đồng thuê xe</h1>
    <p className="muted">Khách thuê xe đội xe tự nhận: Giám đốc đội xe tạo hợp đồng và trình <b>Chủ tịch duyệt</b>{" "}
      (Tổng giám đốc xem được). Duyệt xong bấm <b>Lập lệnh</b> — không cần đề nghị của Điều hành. Ngày lệnh phải nằm
      trong ngày hợp đồng; số lệnh không quá số xe cần.</p>

    {d?.duoc_tao && <form className="panel" onSubmit={luu}><h2>Tạo hợp đồng</h2>
      <div className="grid">
        <div><label>Mã hợp đồng</label><input value={f.ma} onChange={dat("ma")} placeholder="TX-2611-01" required /></div>
        <div><label>Khách thuê</label><input value={f.khach} onChange={dat("khach")} required /></div>
        <div><label>Lộ trình / ghi chú</label><input value={f.lo_trinh} onChange={dat("lo_trinh")} /></div>
        <div><label>Ngày đi</label><input type="date" value={f.ngay_di} onChange={dat("ngay_di")} required /></div>
        <div><label>Ngày về</label><input type="date" value={f.ngay_ve} onChange={dat("ngay_ve")} required /></div>
        <div><label>Số xe cần</label><input inputMode="numeric" value={f.so_xe} onChange={dat("so_xe")} required /></div>
        <div><label>Số khách</label><input inputMode="numeric" value={f.so_khach} onChange={dat("so_khach")} required /></div>
        <div><label>Giá trọn hợp đồng (đ)</label><input inputMode="numeric" value={f.gia} onChange={dat("gia")} required /></div>
        <div><label>Chi phí dự kiến (dầu, cầu đường, tài xế…) (đ)</label><input inputMode="numeric" value={f.chi_phi} onChange={dat("chi_phi")} required /></div>
        <div><label>Điểm dừng nghỉ</label><input value={f.diem_dung} onChange={dat("diem_dung")} required /></div>
      </div>
      <button className="act" style={{ background: "var(--vtos-sky)", borderColor: "var(--vtos-sky)" }} disabled={busy}>Lưu nháp</button>
    </form>}

    {giaiTrinh && <div className="panel"><h2>Giải trình biên dưới ngưỡng</h2>
      <p className="muted">Biên của hợp đồng dưới ngưỡng — ghi lý do (tối thiểu 30 ký tự) để Chủ tịch xem khi duyệt.</p>
      <textarea rows={3} value={giaiTrinh.text} onChange={(e) => setGiaiTrinh({ ...giaiTrinh, text: e.target.value })} />
      <button className="act" disabled={busy || giaiTrinh.text.trim().length < 30} onClick={() => trinh(giaiTrinh.id, giaiTrinh.text)}>Trình kèm giải trình</button>{" "}
      <button className="act grey" onClick={() => setGiaiTrinh(null)}>Thôi</button></div>}

    <div className="panel wrap"><h2>Hợp đồng thuê xe của đội xe</h2>
      {d === undefined && <p className="muted">Đang tải…</p>}
      {d === null && <p className="muted">Không đọc được danh sách.</p>}
      {d && (d.rows.length ? <table><thead><tr><th>Mã</th><th>Khách · lộ trình</th><th>Ngày</th><th className="num">Xe</th>
          <th className="num">Giá trọn HĐ</th><th className="num">Biên</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{d.rows.map((r: any) => <tr key={r.id}>
          <td><b>{r.ma}</b></td><td>{r.khach}<div className="muted">{r.so_khach ? `${r.so_khach} khách · ` : ""}{r.diem_dung}</div></td>
          <td>{fmtD(r.ngay_di)} → {fmtD(r.ngay_ve)}</td><td className="num">{r.so_xe}</td>
          <td className="num">{vnd(r.gia)}</td>
          <td className="num">{r.bien == null ? "—" : `${(r.bien * 100).toFixed(1)}%`}{r.duoi_bien && <div><Tag cls="red">dưới ngưỡng</Tag></div>}</td>
          <td><Tag cls={r.trang_thai === "da_duyet" ? "ok" : r.trang_thai === "cho_duyet" ? "warn" : ""}>{r.trang_thai_ten}</Tag></td>
          <td style={{ whiteSpace: "nowrap" }}>
            {d.duoc_tao && r.trang_thai === "nhap" && <button className="act" style={{ margin: 0 }} disabled={busy} onClick={() => trinh(r.id)}>Trình duyệt</button>}
            {d.duoc_duyet && r.trang_thai === "cho_duyet" && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => duyet(r.id)}>Duyệt</button>}
            {d.duoc_tao && ["da_duyet", "dang_chay"].includes(r.trang_thai) && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => lapLenh(r.id)}>Lập lệnh</button>}
            {r.trang_thai === "cho_duyet" && !d.duoc_duyet && <span className="muted">chờ Chủ tịch</span>}
          </td></tr>)}</tbody></table>
        : <p className="muted">Chưa có hợp đồng thuê xe nào của đội xe.</p>)}
    </div>
  </>);
}

export default function Page() { return <Shell><HopDongThueXe /></Shell>; }
