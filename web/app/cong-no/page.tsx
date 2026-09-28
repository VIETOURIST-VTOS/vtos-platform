"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Sổ công nợ toàn hệ thống.
 *
 *  Nguyên tắc hiển thị: KHÔNG có một con số "công nợ ròng". Phải thu của khách và phải trả nhà cung cấp là
 *  hai quan hệ với hai đối tượng khác nhau; trừ vào nhau ra một con số không đòi được của ai và cũng không
 *  trả cho ai. Hai vế nằm hai khối, và màn hình nói thẳng điều đó ra. */
const n = (x: any) => Number(x || 0).toLocaleString("vi-VN");

function CongNo() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [tab, setTab] = useState<"thu" | "tra" | "xe">("thu");

  const load = useCallback(async () => {
    try { setD(await api("/cong-no")); } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  if (!d) return <p className="muted">Đang tải…</p>;
  const thu = d.phai_thu_khach, tra = d.phai_tra_ncc, xe = d.doi_xe;
  return (<>
    <h1>Công nợ</h1>
    <p className="muted">Tính đến {fmtDT(d.tinh_den)}.</p>

    <div className="panel">
      <div className="kpis">
        <div className="kpi"><b>{n(thu.tong_con_phai_thu)}</b><span>khách còn phải trả công ty ({thu.so_booking} booking)</span></div>
        <div className="kpi"><b style={{ color: thu.trong_do_qua_han ? "var(--red)" : undefined }}>{n(thu.trong_do_qua_han)}</b><span>trong đó ĐÃ QUÁ HẠN (tour đã khởi hành)</span></div>
        <div className="kpi"><b>{n(tra.tong_phai_tra)}</b><span>công ty phải trả nhà cung cấp ({tra.so_phieu} phiếu đã duyệt, chờ chi)</span></div>
        <div className="kpi"><b className="muted">{n(tra.dang_cho_duyet)}</b><span>đề nghị chi đang chờ duyệt — chưa phải nợ</span></div>
      </div>
      <div className="kpis">
        <div className="kpi"><b style={{ color: thu.tong_thu_thua_phai_tra_lai ? "var(--orange)" : undefined }}>{n(thu.tong_thu_thua_phai_tra_lai)}</b><span>khách chuyển thừa — công ty phải trả lại</span></div>
        <div className="kpi"><b style={{ color: tra.thieu_hoa_don_gtgt ? "var(--orange)" : undefined }}>{n(tra.thieu_hoa_don_gtgt)}</b><span>khoản chờ chi chưa có hóa đơn GTGT</span></div>
        <div className="kpi"><b>{n(xe.cong_ty_phai_tra_chu_xe)}</b><span>phải trả chủ xe hợp tác</span></div>
        <div className="kpi"><b>{n(xe.con_phai_thu_ban_xe)}</b><span>còn phải thu của người mua xe</span></div>
      </div>
      <ul className="muted" style={{ marginTop: 8 }}>{d.giai_thich.map((g: string, i: number) => <li key={i}>{g}</li>)}</ul>
    </div>

    <div style={{ display: "flex", gap: 8, margin: "10px 0" }}>
      {([["thu", `Phải thu khách (${thu.so_booking})`], ["tra", `Phải trả NCC (${tra.so_phieu})`], ["xe", "Đội xe"]] as const)
        .map(([k, ten]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} onClick={() => setTab(k as any)}>{ten}</button>)}
    </div>

    {tab === "thu" && <>
      <div className="panel wrap"><h2>Khách còn phải trả</h2>
        <table><thead><tr><th>Booking</th><th>Khách</th><th>Tour</th><th>Khởi hành</th><th>Sales</th>
          <th>Phải thu</th><th>Đã thu</th><th>Còn lại</th><th></th></tr></thead>
          <tbody>{thu.chi_tiet.length ? thu.chi_tiet.map((b: any) => <tr key={b.booking_id}>
            <td>{b.code}</td><td>{b.khach}</td>
            <td className="muted">{b.tour}</td>
            <td className="muted">{b.khoi_hanh ? fmtD(b.khoi_hanh) : "—"}</td>
            <td className="muted">{b.sales}</td>
            <td className="num">{n(b.phai_thu)}</td><td className="num">{n(b.da_thu)}</td>
            <td className="num"><b>{n(b.con_lai)}</b></td>
            <td>{b.qua_han && <Tag cls="red">Quá hạn</Tag>}</td>
          </tr>) : <tr><td colSpan={9} className="muted">Không có khoản nào còn phải thu.</td></tr>}</tbody></table>
      </div>
      {thu.thu_thua.length > 0 && <div className="panel wrap"><h2>Khách chuyển thừa — phải trả lại</h2>
        <p className="muted">Đây là khoản công ty NỢ khách, không phải phải thu âm. Để nó nằm trong cột phải thu
          với dấu trừ là vừa giấu một khoản phải trả, vừa làm tổng phải thu nhỏ hơn sự thật.</p>
        <table><thead><tr><th>Booking</th><th>Khách</th><th>Tour</th><th>Phải thu</th><th>Đã thu</th><th>Phải trả lại</th></tr></thead>
          <tbody>{thu.thu_thua.map((b: any) => <tr key={b.booking_id}>
            <td>{b.code}</td><td>{b.khach}</td><td className="muted">{b.tour}</td>
            <td className="num">{n(b.phai_thu)}</td><td className="num">{n(b.da_thu)}</td>
            <td className="num"><b>{n(b.phai_tra_lai)}</b></td>
          </tr>)}</tbody></table>
      </div>}
    </>}

    {tab === "tra" && <>
      <div className="panel wrap"><h2>Phải trả nhà cung cấp — đã duyệt, chờ chi</h2>
        <table><thead><tr><th>Phiếu</th><th>Nhà cung cấp</th><th>Tour</th><th>Nội dung</th><th>Số tiền</th><th>Chứng từ</th></tr></thead>
          <tbody>{tra.chi_tiet.length ? tra.chi_tiet.map((p: any) => <tr key={p.id}>
            <td>{p.code}</td><td>{p.ncc}</td><td className="muted">{p.tour}</td>
            <td className="muted">{p.noi_dung}</td>
            <td className="num"><b>{n(p.so_tien)}</b></td>
            <td>{p.co_hoa_don ? <Tag cls="ok">Có hóa đơn</Tag> : <Tag cls="warn">Chưa có hóa đơn GTGT</Tag>}</td>
          </tr>) : <tr><td colSpan={6} className="muted">Không có khoản nào đã duyệt đang chờ chi.</td></tr>}</tbody></table>
      </div>
      <div className="panel wrap"><h2>Theo nhà cung cấp</h2>
        <table><thead><tr><th>Nhà cung cấp</th><th>Số tiền</th></tr></thead>
          <tbody>{tra.theo_nha_cung_cap.map((x: any) => <tr key={x.ncc}>
            <td>{x.ncc}</td><td className="num">{n(x.so_tien)}</td></tr>)}</tbody></table>
      </div>
      <div className="panel wrap"><h2>Đang chờ duyệt — chưa phải nợ ({tra.so_phieu_cho_duyet})</h2>
        <p className="muted">Một đề nghị đang chờ Trưởng phòng xem có thể bị từ chối. Gộp vào phải trả là thổi
          phồng nghĩa vụ và làm hỏng dự báo dòng tiền.</p>
        <table><thead><tr><th>Phiếu</th><th>Nhà cung cấp</th><th>Nội dung</th><th>Số tiền</th><th>Trạng thái</th></tr></thead>
          <tbody>{tra.cho_duyet.length ? tra.cho_duyet.map((p: any) => <tr key={p.id}>
            <td>{p.code}</td><td>{p.ncc}</td><td className="muted">{p.noi_dung}</td>
            <td className="num">{n(p.so_tien)}</td><td className="muted">{p.status}</td>
          </tr>) : <tr><td colSpan={5} className="muted">Không có đề nghị nào đang chờ duyệt.</td></tr>}</tbody></table>
      </div>
    </>}

    {tab === "xe" && <div className="panel">
      <h2>Công nợ đội xe</h2>
      <div className="kpis">
        <div className="kpi"><b>{n(xe.cong_ty_phai_tra_chu_xe)}</b><span>công ty phải trả chủ xe hợp tác</span></div>
        <div className="kpi"><b>{n(xe.chu_xe_phai_tra_cong_ty)}</b><span>chủ xe phải trả công ty</span></div>
        <div className="kpi"><b>{n(xe.con_phai_thu_ban_xe)}</b><span>còn phải thu của người mua xe</span></div>
        <div className="kpi"><b>{n(xe.du_no_vay_the_chap_xe)}</b><span>dư nợ ngân hàng có thế chấp xe</span></div>
      </div>
      <p className="muted">Chi tiết từng chủ xe, từng kỳ quyết toán và nhật ký đã trả/đã thu nằm ở
        <b> Đội xe → Công nợ đội xe</b>.</p>
    </div>}
  </>);
}

/** Công nợ khách theo VIETRIP – ảnh chụp báo cáo 8h sáng mỗi ngày (nạp qua /cong-no-vietrip/nap, tệp gốc
 *  lưu R2). Tải RIÊNG với sổ bên dưới: sổ lỗi thì khối này vẫn hiện, và ngược lại. */
function CongNoVietrip() {
  const [d, setD] = useState<any>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [nhom, setNhom] = useState<number>(1);
  const [loi, setLoi] = useState<string>("");
  useEffect(() => {
    api("/cong-no-vietrip").then(setD).catch((e) => setLoi(errMsg(e)));
    api("/cong-no-vietrip/lich-su?so_ngay=30").then(setLs).catch(() => {});
  }, []);
  if (loi) return null;                       // vai không được xem – không hiện khối này
  if (!d) return <div className="panel"><p className="muted">Đang tải công nợ Vietrip…</p></div>;
  if (!d.co_du_lieu) return <div className="panel"><h2>Công nợ khách theo Vietrip</h2><p className="muted">{d.thong_bao}</p></div>;
  const mau: Record<number, string> = { 1: "var(--red)", 2: "var(--orange)", 3: "#c9a400", 4: "#3b82f6", 0: undefined as any };
  const dong = d.dong.filter((r: any) => r.nhom === nhom);
  const truoc = ls.length > 1 ? ls[ls.length - 2] : null;
  return (<>
    <div className="panel">
      <h2>Công nợ khách theo Vietrip — {fmtD(d.ngay)}</h2>
      <p className="muted">Báo cáo tự động 8h sáng, nạp lúc {fmtDT(d.luc)} ({d.so_lan_nap} lần)
        {d.cu_ngay > 1 && <b style={{ color: "var(--red)" }}> · đã cũ {d.cu_ngay} ngày — lịch chạy sáng có thể đã hỏng</b>}
        {!d.tep.ben_vung && <span> · tệp gốc CHƯA nằm trên R2 (kho tạm)</span>}.</p>
      <div className="kpis">
        <div className="kpi"><b>{n(d.tong_con_thieu)}</b><span>tổng còn thiếu ({d.so_booking} booking)
          {truoc && <> · {d.tong_con_thieu - truoc.tong_con_thieu >= 0 ? "tăng " : "giảm "}
            {n(Math.abs(d.tong_con_thieu - truoc.tong_con_thieu))} so với {fmtD(truoc.ngay)}</>}</span></div>
        {d.nhom.filter((g: any) => g.nhom > 0).map((g: any) => <div className="kpi" key={g.nhom} style={{ cursor: "pointer" }} onClick={() => setNhom(g.nhom)}>
          <b style={{ color: mau[g.nhom] }}>{n(g.con_thieu)}</b><span>{g.ten} ({g.so_booking})</span></div>)}
      </div>
    </div>
    <div style={{ display: "flex", gap: 8, margin: "10px 0", flexWrap: "wrap" }}>
      {d.nhom.map((g: any) => <button key={g.nhom} className={`act ${nhom === g.nhom ? "teal" : "grey"}`} onClick={() => setNhom(g.nhom)}>
        {g.nhom ? `Nhóm ${g.nhom}` : "Bảo lưu"} ({g.so_booking})</button>)}
      <button className={`act ${nhom === -1 ? "teal" : "grey"}`} onClick={() => setNhom(-1)}>Theo Sale</button>
    </div>
    {nhom === -1 ? <div className="panel wrap"><table><thead><tr><th>Sales</th><th>Số booking</th><th>Còn thiếu</th></tr></thead>
      <tbody>{d.theo_sale.map((s: any) => <tr key={s.sales}><td>{s.sales}</td><td className="num">{s.so_booking}</td>
        <td className="num"><b>{n(s.con_thieu)}</b></td></tr>)}</tbody></table></div>
    : <div className="panel wrap"><table><thead><tr><th>Booking</th><th>Mã tour</th><th>Tên tour</th><th>Khách</th><th>SĐT</th>
        <th>Sales</th><th>Tổng</th><th>Đã thu</th><th>Còn thiếu</th><th>Khởi hành</th><th>Ghi chú</th></tr></thead>
      <tbody>{dong.length ? dong.map((r: any) => <tr key={r.booking_id}>
        <td>{r.booking_id}</td><td>{r.ma_tour}</td><td className="muted">{r.ten_tour}</td><td>{r.khach}</td>
        <td className="muted">{r.sdt_khach}</td><td className="muted">{r.sales}</td>
        <td className="num">{n(r.tong)}</td><td className="num">{n(r.da_thu)}</td><td className="num"><b>{n(r.con_thieu)}</b></td>
        <td className="muted">{r.khoi_hanh ? fmtD(r.khoi_hanh) : "—"}</td><td>{r.ghi_chu && <Tag cls="warn">{r.ghi_chu}</Tag>}</td>
      </tr>) : <tr><td colSpan={11} className="muted">Không có booking nào trong nhóm này.</td></tr>}</tbody></table></div>}
  </>);
}

export default function Page() { return <Shell><CongNoVietrip /><CongNo /></Shell>; }
