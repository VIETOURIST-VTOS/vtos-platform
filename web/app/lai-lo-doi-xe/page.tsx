"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ChiPhiKyPanel from "@/components/doixe/ChiPhiKyPanel";

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
  const { toast } = useShell();
  const [ky, setKy] = useState(new Date().toISOString().slice(0, 7));
  const [tab, setTab] = useState("tong");
  const [phanBo, setPhanBo] = useState("khong");
  const [d, setD] = useState<any>(null);
  const [tour, setTour] = useState<any[]>([]);

  const load = useCallback(async () => {
    try {
      setD(await api(`/fleet/lai-lo?ky=${ky}&phan_bo=${phanBo}`));
      setTour(await api(`/fleet/lai-lo/theo-chuyen?ky=${ky}`));
    } catch (e) { toast(errMsg(e), true); }
  }, [ky, phanBo, toast]);
  useEffect(() => { load(); }, [load]);

  if (!d) return <p className="muted">Đang tải…</p>;
  const t = d.tong;

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
            <tr><td className="muted">− Chi phí của đội (bãi xe, điện nước, BHXH, quản lý)</td>
              <td className="num muted">{vnd(t.chi_phi_doi)}</td></tr>
            <tr><td><b>= LỢI NHUẬN ĐỘI XE</b> <span className="muted">(theo giá vốn vận tải)</span></td>
              <td className="num"><b style={{ color: t.loi_nhuan < 0 ? "var(--red)" : undefined }}>
                {vnd(t.loi_nhuan)}</b> <span className="muted">({pc(t.ty_le_loi_nhuan)})</span></td></tr>
            {/* HAI DÒNG TÁCH BẠCH. Chủ tịch quyết 11/10/2026: lãi vay không tính vào giá vốn. Trộn nó
                vào dòng trên thì tháng 5/2026 đội xe hiện 123.889.302 thay vì 445.504.964 — lệch 3,6
                lần, và người đọc kết luận sai rằng đội xe gần như không sinh lời. Nhưng BỎ HẲN dòng
                lãi vay khỏi màn hình cũng sai: khi ấy không ai nhìn đội xe mà biết nó đang gánh bao
                nhiêu lãi. Nên giữ cả hai, và ghi rõ dòng nào là giá vốn dòng nào không. */}
            <tr><td className="muted">− Lãi vay xe <span className="muted">— chi phí tài chính (TK 635),
              <b> không thuộc giá vốn</b></span></td>
              <td className="num muted">{vnd(t.chi_phi_tai_chinh)}</td></tr>
            <tr><td><b>= Kết quả sau lãi vay</b></td>
              <td className="num"><b style={{ color: t.ket_qua_sau_tai_chinh < 0 ? "var(--red)" : undefined }}>
                {vnd(t.ket_qua_sau_tai_chinh)}</b></td></tr>
          </tbody></table></div>
        {d.nhom_tai_chinh_chua_nhap?.length > 0 && <p className="muted">
          <Tag cls="warn">chưa nhập</Tag> {d.nhom_tai_chinh_chua_nhap.join(" · ")} — kỳ này chưa có số,
          nên dòng <b>kết quả sau lãi vay</b> đang bằng lợi nhuận đội xe. Đó là THIẾU SỐ, không phải
          bằng 0.</p>}
        <div className="kpis" style={{ marginTop: 10 }}>
          {/* HQ-1b (13/10/2026) — MẪU SỐ RỖNG THÌ ĐỪNG IN DẤU GẠCH CHÉO.
              Bản trước in thẳng `{so_xe_khai_thac}/{so_xe_trong_doi}`, nên khi đội hình chưa khai
              đủ thì ô đọc ra "14/" — một mẫu số cụt, trông như màn hình hỏng. Mẫu rỗng thì chỉ in
              tử số; cái thiếu nói ở dòng dưới, bằng chữ. */}
          <div className="kpi"><b>{t.so_xe_trong_doi == null ? t.so_xe_khai_thac
            : `${t.so_xe_khai_thac}/${t.so_xe_trong_doi}`}</b><span>xe có chạy trong kỳ</span></div>
          <div className="kpi"><b>{pc(t.cong_suat)}</b><span>công suất (ngày chạy / xe × ngày)</span></div>
          <div className="kpi"><b>{t.ngay_khai_thac}</b><span>ngày khai thác</span></div>
        </div>
        {/* Ô TRỐNG PHẢI NÓI AI LÀM. Máy chủ đã gửi đủ `cong_suat_thieu` (bộ phận, cửa nhập, danh
            sách xe còn thiếu) từ vòng HQ-1, nhưng màn hình chưa in ra — nên người đọc chỉ thấy một
            dấu gạch ngang và không có cách nào biết nó đang chờ ai. Đây đúng điều bản vẽ KhoiV14 đã
            cảnh báo: một ô trống không nói ai chịu trách nhiệm thì nó nằm đó mãi.
            Vòng này KHÔNG đổi phép tính nào — chỉ in cái đã có. */}
        {t.cong_suat_thieu && <p className="muted" style={{ marginTop: 8 }}>
          <Tag cls="warn">chưa tính được</Tag> <b>Công suất</b> — còn <b>{t.cong_suat_thieu.thieu.length} xe</b> chưa
          khai ngày vào đội, nên chưa biết kỳ này đội có bao nhiêu chiếc.{" "}
          {t.cong_suat_thieu.thieu.slice(0, 4).map((x: any) => x.xe).join(" · ")}
          {t.cong_suat_thieu.thieu.length > 4 && ` …và ${t.cong_suat_thieu.thieu.length - 4} chiếc nữa`}.
          {" "}Việc của <b>{t.cong_suat_thieu.bo_phan}</b>.{" "}
          <Link href={t.cong_suat_thieu.cua_nhap}>Mở cửa Hồ sơ xe →</Link></p>}
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
        {d.chi_tiet_chi_phi_tai_chinh?.length > 0 && <>
          <h2 style={{ marginTop: 14 }}>Ngoài giá vốn — chi phí tài chính</h2>
          <table><thead><tr><th>Nhóm</th><th className="num">Số tiền</th></tr></thead>
            <tbody>{d.chi_tiet_chi_phi_tai_chinh.map((c: any) => <tr key={c.nhom}>
              <td>{c.ten} <Tag cls="warn">ngoài giá vốn</Tag></td>
              <td className="num">{vnd(c.so_tien)}</td></tr>)}</tbody></table>
          <p className="muted">Chủ tịch quyết 11/10/2026: lãi vay là chi phí tài chính (TK 635), không
            tính vào giá vốn vận tải. Khối này <b>không</b> nằm trong lợi nhuận đội xe ở trên và
            <b> không</b> phân bổ về xe nào ở tab Theo xe.</p>
        </>}
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

    {tab === "cp" && <ChiPhiKyPanel ky={ky} onDoiSo={load} />}
  </>);
}

export default function Page() { return <Shell><LaiLo /></Shell>; }
