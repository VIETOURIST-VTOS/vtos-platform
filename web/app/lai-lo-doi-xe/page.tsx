"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lãi lỗ đội xe: ba tầng chi phí, và khoảng cách giữa chúng.
 *
 *  Bảng quyết toán tháng 6/2026 là lý do màn hình này tồn tại: cộng lãi gộp 21 chiếc được 938 triệu,
 *  nhưng sau bảo hiểm, lương tài xế, phí bãi và 327 triệu lãi vay thì đội xe còn 227 triệu. Nếu màn hình
 *  chỉ hiện tầng đầu thì người đọc tưởng đội xe lãi gấp hơn bốn lần thực tế — nên ba tầng phải nằm cạnh
 *  nhau trên cùng một màn hình, không phải ở ba nơi khác nhau. */
const TABS: [string, string][] = [["tong", "Kết quả tháng"], ["xe", "Theo xe & tài xế"],
                                  ["tour", "Theo tour"], ["cp", "Chi phí kỳ"]];
const pc = (v: any) => v === null || v === undefined ? <span className="muted">—</span>
  : <span>{(Number(v) * 100).toFixed(1)}%</span>;

function LaiLo() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(new Date().toISOString().slice(0, 7));
  const [tab, setTab] = useState("tong");
  const [phanBo, setPhanBo] = useState("khong");
  const [d, setD] = useState<any>(null);
  const [tour, setTour] = useState<any[]>([]);
  const [cp, setCp] = useState<any>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [f, setF] = useState<any>(null);
  const [luu, setLuu] = useState(false);
  const canGhi = ["ketoan", "cntt", "gd_doi_xe"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setD(await api(`/fleet/lai-lo?ky=${ky}&phan_bo=${phanBo}`));
      setTour(await api(`/fleet/lai-lo/theo-chuyen?ky=${ky}`));
      setCp(await api(`/fleet/chi-phi-ky?ky=${ky}`));
    } catch (e) { toast(errMsg(e), true); }
  }, [ky, phanBo, toast]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { api("/fleet/xe").then((r: any) => setXe(r.rows || r)).catch(() => {}); }, []);

  const ghi = async () => {
    setLuu(true);
    try {
      const r = await api<any>("/fleet/chi-phi-ky", { method: "POST", json: {
        ky, nhom: f.nhom, so_tien: soTien(f.so_tien),
        vehicle_id: f.vehicle_id ? Number(f.vehicle_id) : null,
        mo_ta: f.mo_ta || "", chung_tu: f.chung_tu || "" } });
      toast(r.message); setF(null); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setLuu(false); }
  };

  const go = async (id: number) => {
    const ly_do = window.prompt("Gỡ khoản này khỏi kỳ vì lý do gì?\n\n" +
      "Một khoản chi phí biến mất khỏi báo cáo mà không ai biết vì sao là cách nhanh nhất làm cho lãi " +
      "lỗ tháng không đối chiếu được với tháng trước.");
    if (!ly_do || !ly_do.trim()) return;
    try { const r = await api<any>(`/fleet/chi-phi-ky/${id}?ly_do=${encodeURIComponent(ly_do)}`,
                                   { method: "DELETE" });
          toast(r.message); await load(); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!d) return <p className="muted">Đang tải…</p>;
  const t = d.tong;
  const nhomCua = (ma: string) => (cp?.nhom || []).find((n: any) => n.ma === ma);

  return (<>
    <h1>Lãi lỗ đội xe</h1>
    <p className="muted">Ba tầng chi phí để riêng: <b>chi phí chuyến</b> (dầu, cầu đường, công tác phí),
      <b> chi phí của xe</b> (bảo hiểm, lương tài xế, bảo dưỡng, phân bổ trả trước), và <b>chi phí của
      đội</b> (bãi xe, lãi vay, BHXH). Lãi gộp chuyến chưa phải lợi nhuận — khoảng cách giữa hai con số
      đó chính là chỗ đội xe lãi hay lỗ.</p>

    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", margin: "8px 0" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")}
        style={{ margin: 0 }} onClick={() => setTab(k)}>{l}</button>)}
      <label style={{ marginLeft: "auto" }}>Kỳ
        <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
    </div>

    {tab === "tong" && <>
      <div className="panel">
        <h2>Kết quả kỳ {d.ky}</h2>
        <div className="wrap"><table>
          <tbody>
            <tr><td>Doanh thu</td><td className="num"><b>{vnd(t.doanh_thu)}</b></td></tr>
            <tr><td className="muted">− Chi phí chuyến (dầu, cầu đường, công tác phí, gửi xe)</td>
              <td className="num muted">{vnd(t.chi_phi_chuyen)}</td></tr>
            <tr><td><b>= Lãi gộp chuyến</b></td><td className="num"><b>{vnd(t.lai_gop_chuyen)}</b></td></tr>
            <tr><td className="muted">− Chi phí của xe (bảo hiểm, lương, bảo dưỡng, wifi, trả trước)</td>
              <td className="num muted">{vnd(t.chi_phi_xe)}</td></tr>
            <tr><td><b>= Kết quả sau chi phí xe</b></td>
              <td className="num"><b>{vnd(t.ket_qua_sau_chi_phi_xe)}</b></td></tr>
            <tr><td className="muted">− Chi phí của đội (bãi xe, lãi vay, BHXH, quản lý)</td>
              <td className="num muted">{vnd(t.chi_phi_doi)}</td></tr>
            <tr><td><b>= LỢI NHUẬN ĐỘI XE</b></td>
              <td className="num"><b style={{ color: t.loi_nhuan < 0 ? "var(--red)" : undefined }}>
                {vnd(t.loi_nhuan)}</b> <span className="muted">({pc(t.ty_le_loi_nhuan)})</span></td></tr>
          </tbody></table></div>
        <div className="kpis" style={{ marginTop: 10 }}>
          <div className="kpi"><b>{t.so_xe_khai_thac}/{t.so_xe_trong_doi}</b><span>xe có chạy trong kỳ</span></div>
          <div className="kpi"><b>{pc(t.cong_suat)}</b><span>công suất (ngày chạy / xe × ngày)</span></div>
          <div className="kpi"><b>{t.ngay_khai_thac}</b><span>ngày khai thác</span></div>
        </div>
      </div>

      {/* TIỀN NẰM NGOÀI BA TẦNG. Đo trên hệ thật 07/10/2026: bảng giao dịch nguồn ngoài giữ
          1.121.825.494 đ, cả 36 dòng chưa khớp chuyến, trong khi khối lãi lỗ ngay trên đây in LỢI
          NHUẬN 50,3% cho kỳ 08/2026. Ba tầng chi phí đọc chi phí chuyến, bảo dưỡng và chi phí kỳ —
          KHÔNG đọc bảng nguồn ngoài. Người đọc không có cách nào biết điều đó, nên con số 50,3% đọc
          ra như kết quả thật của đội xe. Khối này tồn tại để nó không đọc ra như vậy nữa. */}
      {d.ngoai_so?.so_khoan > 0 && <div className="panel" style={{ borderColor: "var(--orange)" }}>
        <h2>Còn {vnd(d.ngoai_so.tong)} nằm NGOÀI ba tầng chi phí trên</h2>
        <p className="muted">{d.ngoai_so.so_khoan} khoản đã nạp vào bảng giao dịch nguồn ngoài (sao kê
          thẻ dầu, ePass, đề xuất chi Vietrip) nhưng chưa khớp vào chuyến nào và chưa nạp qua cửa chi
          phí kỳ — nên <b>lợi nhuận ở trên chưa trừ phần nào của số này</b>.</p>
        <div className="kpis" style={{ marginBottom: 10 }}>
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{vnd(d.ngoai_so.cua_doi_xe)}</b>
            <span>đã xác định là CỦA ĐỘI XE — phải trừ thêm</span></div>
          <div className="kpi"><b style={{ color: "var(--orange)" }}>{vnd(d.ngoai_so.chua_dinh_tuyen)}</b>
            <span>chưa định tuyến — chưa biết của ai</span></div>
        </div>
        <table><thead><tr><th>Ngả</th><th>Của đội xe?</th><th className="num">Số khoản</th><th className="num">Số tiền</th></tr></thead>
          <tbody>{(d.ngoai_so.theo_nga || []).map((n: any) => <tr key={n.nga || "chua"}>
            <td>{n.nga ? n.ten : <Tag cls="warn">{n.ten}</Tag>}</td>
            <td>{n.nga ? (n.cua_doi_xe ? "có" : "không") : "—"}</td>
            <td className="num">{n.so_khoan}</td>
            <td className="num">{vnd(n.so_tien)}</td>
          </tr>)}</tbody></table>
        <p className="muted">{d.ngoai_so.ghi_chu} Định tuyến ở <b>Hồ sơ xe › Đối soát nguồn ngoài</b>.
          Khoản của đội muốn vào ba tầng thì vẫn phải nạp qua cửa <b>Chi phí kỳ của đội xe</b> — một
          khoản một cửa, cộng ở hai đường là tính hai lần.</p>
      </div>}

      <div className="panel wrap">
        <h2>Chi phí của đội trong kỳ</h2>
        <table><thead><tr><th>Nhóm</th><th className="num">Số tiền</th></tr></thead>
          <tbody>{d.chi_tiet_chi_phi_doi.length
            ? d.chi_tiet_chi_phi_doi.map((c: any) => <tr key={c.nhom}>
                <td>{c.ten}</td><td className="num">{vnd(c.so_tien)}</td></tr>)
            : <tr><td colSpan={2} className="muted">Kỳ này chưa nhập chi phí đội nào.</td></tr>}</tbody></table>
        {d.nhom_chi_phi_doi_chua_nhap?.length > 0 && <p className="muted">
          <Tag cls="warn">chưa nhập</Tag> {d.nhom_chi_phi_doi_chua_nhap.join(" · ")} — lợi nhuận ở trên
          <b> chưa trừ</b> những khoản này, nên đang cao hơn thực tế.</p>}
      </div>
    </>}

    {tab === "xe" && <div className="panel wrap">
      <h2>Theo xe và tài xế</h2>
      <label>Phân bổ chi phí đội về từng xe
        <select value={phanBo} onChange={(e) => setPhanBo(e.target.value)}>
          {Object.entries(d.tieu_thuc).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
        </select></label>
      <p className="muted">Mặc định <b>không phân bổ</b>: chia lãi vay theo doanh thu, theo ngày chạy hay
        chia đều đều ra những con số khác nhau và đều &quot;có lý&quot;, mà người đọc lại nhớ nó như kết
        quả thật của chiếc xe rồi lấy ra quyết định bán xe hay đổi tài xế.</p>
      <table><thead><tr><th>Xe</th><th>Tài xế</th><th className="num">Chuyến</th><th className="num">Ngày</th>
        <th className="num">Km</th><th className="num">km/lít</th><th className="num">Doanh thu</th>
        <th className="num">CP chuyến</th><th className="num">Lãi gộp</th><th className="num">CP xe</th>
        <th className="num">Kết quả xe</th>{phanBo !== "khong" && <>
          <th className="num">Phân bổ CP đội</th><th className="num">Sau phân bổ</th></>}</tr></thead>
        <tbody>{d.xe.map((x: any) => <tr key={x.vehicle_id}>
          <td><b>{x.xe}</b></td><td className="muted">{x.tai_xe}</td>
          <td className="num">{x.so_chuyen}</td><td className="num">{x.ngay_khai_thac}</td>
          <td className="num muted">{x.km ? x.km.toLocaleString("vi-VN") : "—"}</td>
          <td className="num muted">{x.km_moi_lit ?? "—"}</td>
          <td className="num">{vnd(x.doanh_thu)}</td>
          <td className="num muted">{vnd(x.chi_phi_chuyen)}</td>
          <td className="num">{vnd(x.lai_gop_chuyen)} <span className="muted">{pc(x.ty_le_lai_gop)}</span></td>
          <td className="num muted">{vnd(x.chi_phi_xe)}</td>
          <td className="num"><b style={{ color: x.ket_qua_xe < 0 ? "var(--red)" : undefined }}>
            {vnd(x.ket_qua_xe)}</b></td>
          {phanBo !== "khong" && <>
            <td className="num muted">{vnd(x.phan_bo_chi_phi_doi || 0)}</td>
            <td className="num"><b style={{ color: (x.ket_qua_sau_phan_bo ?? 0) < 0 ? "var(--red)" : undefined }}>
              {vnd(x.ket_qua_sau_phan_bo || 0)}</b></td></>}
        </tr>)}</tbody></table>
    </div>}

    {tab === "tour" && <div className="panel wrap">
      <h2>Quyết toán theo tour</h2>
      <p className="muted">Mỗi chuyến một dòng. Ô để trống là <b>chưa có số</b> — không phải bằng 0.</p>
      <table><thead><tr><th>Mã phiếu</th><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Thời gian</th>
        <th className="num">Ngày</th><th className="num">Km</th><th className="num">km/lít</th>
        <th className="num">Đ/km dầu</th><th className="num">Doanh thu</th><th className="num">Chi phí</th>
        <th className="num">Lãi gộp</th></tr></thead>
        <tbody>{tour.length ? tour.map((c: any) => <tr key={c.trip_id}>
          <td className="mono">{c.ma_phieu || c.trip_id}</td><td>{c.ten_tour}</td>
          <td>{c.xe}</td><td className="muted">{c.tai_xe}</td>
          <td className="muted">{fmtD(c.ngay_di)} → {fmtD(c.ngay_ve)}</td>
          <td className="num">{c.so_ngay}</td>
          <td className="num muted">{c.km ? c.km.toLocaleString("vi-VN") : "—"}</td>
          <td className="num muted">{c.km_moi_lit ?? "—"}</td>
          <td className="num muted">{c.dau_moi_km ? c.dau_moi_km.toLocaleString("vi-VN") : "—"}</td>
          <td className="num">{vnd(c.doanh_thu)}</td><td className="num muted">{vnd(c.chi_phi_chuyen)}</td>
          <td className="num"><b style={{ color: c.lai_gop < 0 ? "var(--red)" : undefined }}>{vnd(c.lai_gop)}</b>
            {" "}<span className="muted">{pc(c.ty_le)}</span></td>
        </tr>) : <tr><td colSpan={12} className="muted">Kỳ này chưa có chuyến nào.</td></tr>}</tbody></table>
    </div>}

    {tab === "cp" && <>
      {canGhi && <div className="panel">
        <h2>Ghi chi phí kỳ {ky}</h2>
        <p className="muted">Khoản không gắn vào chuyến nào: bảo hiểm, đăng kiểm, lương tài xế, wifi,
          phân bổ chi phí trả trước, phí bãi, lãi vay, BHXH. Nhóm nào thuộc <b>xe</b> thì bắt buộc chọn
          xe; nhóm nào thuộc <b>đội</b> thì không gắn vào xe nào.</p>
        {!f && <button className="act" onClick={() => setF({ nhom: "", so_tien: "", vehicle_id: "",
                                                             mo_ta: "", chung_tu: "" })}>+ Thêm khoản</button>}
        {f && <>
          <div className="grid2">
            <label>Nhóm chi phí
              <select value={f.nhom} onChange={(e) => setF({ ...f, nhom: e.target.value, vehicle_id: "" })}>
                <option value="">— chọn nhóm —</option>
                {(cp?.nhom || []).map((n: any) =>
                  <option key={n.ma} value={n.ma}>{n.ten} ({n.pham_vi === "xe" ? "theo xe" : "cả đội"})</option>)}
              </select></label>
            {nhomCua(f.nhom)?.pham_vi === "xe" && <label>Xe
              <select value={f.vehicle_id} onChange={(e) => setF({ ...f, vehicle_id: e.target.value })}>
                <option value="">— chọn xe —</option>
                {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}</option>)}
              </select></label>}
            <label>Số tiền
              <input type="number" step={1000} value={f.so_tien}
                     onChange={(e) => setF({ ...f, so_tien: e.target.value })} /></label>
            <label>Diễn giải
              <input value={f.mo_ta} placeholder="VD: Bảo hiểm TNDS tháng 9"
                     onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
            <label>Chứng từ
              <input value={f.chung_tu} onChange={(e) => setF({ ...f, chung_tu: e.target.value })} /></label>
          </div>
          <button className="act teal" disabled={luu || !f.nhom || !f.so_tien} onClick={ghi}>
            {luu ? "Đang ghi…" : "Ghi vào kỳ"}</button>{" "}
          <button className="act grey" onClick={() => setF(null)}>Đóng</button>
        </>}
      </div>}
      <div className="panel wrap">
        <h2>Các khoản đã ghi trong kỳ</h2>
        <table><thead><tr><th>Nhóm</th><th>Phạm vi</th><th>Xe</th><th>Diễn giải</th>
          <th className="num">Số tiền</th><th>Người ghi</th>{canGhi && <th></th>}</tr></thead>
          <tbody>{cp?.rows?.length ? cp.rows.map((r: any) => <tr key={r.id}>
            <td>{r.nhom_ten}</td>
            <td>{r.pham_vi === "xe" ? <Tag cls="ok">theo xe</Tag> : <Tag cls="navy">cả đội</Tag>}</td>
            <td className="muted">{r.xe || "—"}</td><td className="muted">{r.mo_ta}</td>
            <td className="num">{vnd(r.so_tien)}</td><td className="muted">{r.boi}</td>
            {canGhi && <td><button className="act grey" style={{ margin: 0 }}
                                   onClick={() => go(r.id)}>Gỡ</button></td>}
          </tr>) : <tr><td colSpan={canGhi ? 7 : 6} className="muted">Kỳ này chưa ghi khoản nào.</td></tr>}</tbody></table>
      </div>
    </>}
  </>);
}

export default function Page() { return <Shell><LaiLo /></Shell>; }
