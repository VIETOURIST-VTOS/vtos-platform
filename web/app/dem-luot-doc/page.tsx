"use client";
import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag } from "@/components/ui";

/** Đếm lượt mở cửa đọc — Đợt HD-Q2mh. Chủ tịch duyệt bố cục 16/10/2026.
 *
 *  ── MÀN HÌNH NÀY DÙNG ĐỂ QUYẾT MỘT VIỆC, KHÔNG PHẢI ĐỂ THEO DÕI AI ─────────────────────────
 *  Chủ tịch đang cân thu hẹp quyền đọc của Marketing và Điều hành (Đợt HD-Q2b). Khuôn đã duyệt
 *  hai lần là «đếm được trước, chặn sau»: siết một quyền người ta dùng hằng ngày mà không đếm
 *  trước là sáng hôm sau một phòng mở máy không thấy việc của mình. Bảng này là phần ĐẾM.
 *
 *  ── Ô TRỐNG GHI «chưa có số», KHÔNG GHI 0 ──────────────────────────────────────────────────
 *  Máy chủ chỉ bắt đầu ghi lượt đọc từ ngày Đợt HD-Q2a lên hệ thống thật; trước đó không có dữ
 *  liệu nào. Một người chưa mở cửa nào trong kỳ và một người mà hệ thống chưa từng ghi là hai
 *  chuyện khác nhau, và nếu cả hai cùng in ra số 0 thì Chủ tịch sẽ cắt nhầm. Nên màn hình in dấu
 *  gạch, và in luôn ngày bắt đầu đếm ở ngay đầu trang.
 *
 *  ── KHÔNG TỰ TÍNH MỘT CON SỐ NÀO ───────────────────────────────────────────────────────────
 *  Kể cả lượt trung bình mỗi ngày. Máy chủ cộng; tính lại ở đây là dựng công thức thứ hai, và
 *  ngày hai con số lệch nhau thì người dùng tin con số dễ đọc chứ không tin con số đúng.
 *
 *  ── ROBOT ĐỂ RIÊNG MỘT KHỐI, KHÔNG CỘNG VÀO NGƯỜI ──────────────────────────────────────────
 *  Robot Kiểm soát gọi cửa đọc theo lịch, mỗi ngày vài trăm lượt. Gộp nó vào lượt người là biến
 *  một con robot thành một phòng ban chăm chỉ.
 */

const so = (v: any) => (v === null || v === undefined ? "—" : String(v));

function hom_nay_lui(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function DemLuot() {
  const [tu, setTu] = useState(hom_nay_lui(6));
  const [den, setDen] = useState(hom_nay_lui(0));
  const [kq, setKq] = useState<any>(null);
  const [loi, setLoi] = useState("");

  const tai = useCallback(() => {
    api(`/danh-gia/dem-luot?tu=${tu}&den=${den}`)
      .then((r: any) => { setKq(r); setLoi(""); })
      .catch((e: any) => { setKq(null); setLoi(e?.message || "Không đọc được bảng đếm"); });
  }, [tu, den]);
  useEffect(() => { tai(); }, [tai]);

  const rows: any[] = kq?.rows || [];
  const nguoi = rows.filter((r) => !r.la_robot);
  const robot = rows.filter((r) => r.la_robot);

  return (<>
    <h1>Đếm lượt mở cửa đọc</h1>
    <p className="muted">Ai đang thật sự mở những màn hình đánh giá và chăm sóc khách, mở bao nhiêu
      lần, và đọc được bao nhiêu dòng dữ liệu. Bảng dùng để quyết phạm vi quyền; nó <b>không</b> chứa
      nội dung mà người đọc đã xem.</p>

    <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap", margin: "12px 0" }}>
      <div>
        <label htmlFor="tu">Từ ngày</label>
        <input id="tu" type="date" value={tu} onChange={(e) => setTu(e.target.value)} />
      </div>
      <div>
        <label htmlFor="den">Đến ngày</label>
        <input id="den" type="date" value={den} onChange={(e) => setDen(e.target.value)} />
      </div>
      <button className="act teal" style={{ margin: 0 }} onClick={tai}>Xem</button>
    </div>

    {loi && <div className="gate fail">{loi}</div>}
    {kq?.luu_y && <div className="gate">{kq.luu_y}</div>}

    {kq && <div className="kpis">
      <div className="kpi"><b>{so(kq.so_ngay_ky)}</b><span>Số ngày của kỳ</span></div>
      <div className="kpi"><b>{new Set(nguoi.map((r) => r.username)).size}</b><span>Người có mở ít nhất một lần</span></div>
      <div className="kpi"><b>{nguoi.reduce((s, r) => s + (r.so_dong || 0), 0)}</b><span>Dòng dữ liệu đã đọc</span></div>
    </div>}

    {/* Đếm người có mở và cộng số dòng là PHÉP ĐẾM TRÊN DANH SÁCH máy chủ vừa trả, không phải một
        công thức thứ hai: không có dòng nào thì không có gì để đếm, và con số không thể lệch với
        bảng ngay bên dưới. Lượt trung bình mỗi ngày thì KHÔNG tính ở đây — đó là phép chia, và
        phép chia ấy máy chủ đã làm (`luot_moi_ngay`), chia lại ở màn hình là dựng công thức thứ hai. */}

    <div className="panel wrap">
      <h2>Từng người, từng cửa{kq ? ` · ${kq.tu} → ${kq.den}` : ""}</h2>
      <table>
        <thead><tr>
          <th>Người · vai trò</th><th>Cửa đã mở</th>
          <th className="num">Lượt</th><th className="num">Phút khác nhau</th>
          <th className="num">Ngày có mở</th><th className="num">Dòng đã đọc</th>
          <th className="num">Lượt mỗi ngày</th>
        </tr></thead>
        <tbody>{nguoi.length ? nguoi.map((r: any, i: number) => (
          <tr key={`${r.username}-${r.cua}-${i}`}>
            <td><b>{r.username}</b><div className="muted">{r.role}</div></td>
            <td>{r.cua_ten}</td>
            <td className="num">{so(r.so_luot)}</td>
            {/* Hai cột cạnh nhau cố ý: màn hình tự nạp lại làm số LƯỢT phồng lên, số PHÚT thì không. */}
            <td className="num">{so(r.so_phut)}</td>
            <td className="num">{so(r.so_ngay)}</td>
            <td className="num"><b>{so(r.so_dong)}</b></td>
            <td className="num">{so(r.luot_moi_ngay)}</td>
          </tr>
        )) : <tr><td colSpan={7} className="muted">
          Chưa có số nào trong kỳ này. Lưu ý: <b>chưa có số</b> không giống <b>không ai mở</b> — máy
          chủ chỉ ghi lượt đọc từ ngày đợt đếm lên hệ thống thật.
        </td></tr>}</tbody>
      </table>
    </div>

    {robot.length > 0 && <div className="panel wrap">
      <h2>Tài khoản robot <Tag cls="grey">không cộng vào các con số người ở trên</Tag></h2>
      <p className="muted">Robot gọi cửa đọc theo lịch. Để chung với người thì một con robot trông
        như một phòng ban chăm chỉ, và con số sẽ nói sai về việc ai cần quyền.</p>
      <table>
        <thead><tr>
          <th>Tài khoản · vai trò</th><th>Cửa đã mở</th>
          <th className="num">Lượt</th><th className="num">Phút khác nhau</th>
          <th className="num">Ngày có mở</th><th className="num">Dòng đã đọc</th>
          <th className="num">Lượt mỗi ngày</th>
        </tr></thead>
        <tbody>{robot.map((r: any, i: number) => (
          <tr key={`rb-${r.username}-${r.cua}-${i}`}>
            <td><b>{r.username}</b><div className="muted">{r.role}</div></td>
            <td>{r.cua_ten}</td>
            <td className="num">{so(r.so_luot)}</td>
            <td className="num">{so(r.so_phut)}</td>
            <td className="num">{so(r.so_ngay)}</td>
            <td className="num">{so(r.so_dong)}</td>
            <td className="num">{so(r.luot_moi_ngay)}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>}

    <p className="muted">Bảng ghi tên người đăng nhập, vai trò, tên cửa và số đếm — không ghi nội
      dung đã xem, không ghi tham số lọc, không ghi một chữ nào về khách. Chính cửa này cũng không
      tự đếm lượt mở của nó: nếu đếm thì con số sẽ nói về người đi đo chứ không nói về người bị đo.</p>
  </>);
}

export default function Page() { return <Shell><DemLuot /></Shell>; }
