"use client";
import { useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KH-3 · VTD REWARDS (Kinh doanh) — Chủ tịch duyệt bản xem thử 26/10/2026.
 *  Tra điểm khách theo SĐT / email; áp voucher khách đổi ở cổng vào booking. Áp = cộng giá trị voucher vào
 *  giảm giá của booking (máy chủ ghi nhật ký). Máy chủ kiểm: cùng chủ, booking trực tiếp, chưa khoá / hủy, ≤ 5%. */
const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") : "—");

function Trang() {
  const { user, toast } = useShell();
  const ap = ["nv_kd", "tn_kd", "tp_kd", "gd_kd", "sales_admin", "chutich", "tgd"].includes(user?.role || "");
  const [q, setQ] = useState("");
  const [kq, setKq] = useState<any>(null);
  const [mv, setMv] = useState("");
  const [mb, setMb] = useState("");
  const [v, setV] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const traCuu = async () => { setKq(null); try { setKq(await api(`/rewards/tra-cuu?q=${encodeURIComponent(q)}`)); } catch (e) { toast(errMsg(e), true); } };
  const xemV = async () => { setV(null); if (!mv.trim()) return; try { setV(await api(`/rewards/voucher/${encodeURIComponent(mv.trim().toUpperCase())}`)); } catch (e) { toast(errMsg(e), true); } };
  const apV = async () => {
    setBusy(true);
    try { const r = await api<any>("/rewards/ap-voucher", { method: "POST", json: { ma_voucher: mv.trim().toUpperCase(), ma_booking: mb.trim() } }); toast(r.message); setV(null); setMv(""); setMb(""); }
    catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  return (<>
    <h1>VTD Rewards</h1>
    <p className="muted">Hạng: Member dưới 30 tr ×1,0 · Plus 30–100 tr ×1,25 · Premium từ 100 tr ×1,5 (chi tiêu 12 tháng). 10.000 đ = 1 điểm · 1 điểm = 100 đ · voucher tối đa 5% booking · điểm hết hạn 12 tháng.
      Chỉ booking trực tiếp, tour đã kết thúc và đã thu đủ mới được cộng điểm.</p>
    <div className="grid">
      <section className="panel">
        <h2>Áp voucher vào booking</h2>
        <label>Mã voucher<input value={mv} placeholder="VTD-XXXXXX" onChange={(e) => setMv(e.target.value)} onBlur={xemV} /></label>
        {v && <p>Chủ: <b>{v.chu}</b> · {d(v.gia_tri)} đ · hạn {v.han_dung.split("-").reverse().join("/")} · <Tag cls={v.trang_thai === "Chưa dùng" ? "ok" : "warn"}>{v.trang_thai}</Tag></p>}
        <label>Mã booking<input value={mb} placeholder="BK26100031" onChange={(e) => setMb(e.target.value)} /></label>
        {ap ? <button className="act teal" disabled={busy || !mv.trim() || !mb.trim()} onClick={apV}>Áp voucher</button>
          : <p className="muted">Chỉ Kinh doanh / Sale Admin áp voucher.</p>}
        <p className="muted">Booking phải cùng SĐT / email với chủ voucher, đặt trực tiếp (không qua đại lý / CTV), chưa khoá, chưa hủy; giá trị voucher ≤ 5% giá trị booking. Áp xong giá trị voucher vào ô giảm giá của booking.</p>
      </section>
      <section className="panel">
        <h2>Tra điểm khách</h2>
        <label>SĐT hoặc email<input value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && traCuu()} /></label>
        <button className="act grey" onClick={traCuu} disabled={!q.trim()}>Tra</button>
        {kq && <>
          {!kq.dang_bat && <div className="gate">Chương trình chưa bật (tham số «rewards_hieu_luc_tu» trống hoặc chưa tới ngày) — chỉ có hạng và chi tiêu, chưa cộng điểm.</div>}
          <p>{kq.lien_he} · hạng <b>{kq.hang}</b> · chi tiêu 12 tháng {d(kq.chi_tieu_12_thang)} đ</p>
          <p>Khả dụng <b>{d(kq.kha_dung)}</b> điểm · đang giữ {d(kq.dang_giu)}</p>
          {kq.voucher.length > 0 && <div className="panel wrap"><table><thead><tr><th>Voucher chưa dùng</th><th className="num">Giá trị</th><th>Hạn</th></tr></thead>
            <tbody>{kq.voucher.map((x: any) => <tr key={x.ma}><td className="mono">{x.ma}</td><td className="num">{d(x.gia_tri)} đ</td><td>{x.han_dung.split("-").reverse().join("/")}</td></tr>)}</tbody></table></div>}
          {kq.khoan?.length > 0 && <div className="panel wrap"><table><thead><tr><th>Khoản</th><th>Loại</th><th className="num">Giá trị tính điểm</th><th>Trạng thái</th><th className="num">Điểm</th></tr></thead>
            <tbody>{kq.khoan.map((x: any) => <tr key={x.loai + x.ma}><td className="mono">{x.ma}</td><td>{x.loai}</td><td className="num">{x.du_dieu_kien ? `${d(x.co_so)} đ` : "—"}</td>
              <td>{x.huy ? "Đã hủy" : x.du_dieu_kien ? "Đủ điều kiện" : "Chưa đủ điều kiện (chưa xong / chưa chốt)"}</td><td className="num">{x.diem ? (x.diem > 0 ? "+" : "") + d(x.diem) : "chưa cộng"}</td></tr>)}</tbody></table></div>}
        </>}
      </section>
    </div>
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
