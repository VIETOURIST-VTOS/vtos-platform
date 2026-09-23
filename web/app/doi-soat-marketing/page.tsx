"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Đối soát dữ liệu Marketing – nhóm 2.8.
 *
 *  MÀN HÌNH NÀY KHÔNG CHỌN BÊN NÀO ĐÚNG. Nó đặt hai sổ cạnh nhau, chỉ ra phần chênh, và dừng ở
 *  đó. Chọn hộ một bên là đúng cái việc mà nhóm 2.8 sinh ra để ngăn – và người duy nhất biết bên
 *  nào đúng là người đã ghi sổ ấy, không phải phần mềm.
 *
 *  BA THẺ, VÀ THẺ "ĐỐI CHIẾU" MỞ SẴN vì nó là câu hỏi hay được mang đi họp nhất: số của Marketing
 *  và số của Kinh doanh có khớp nhau không.
 */

const THE: [string, string][] = [
  ["doi", "Đối chiếu ba sổ"], ["trung", "Trùng & thiếu nguồn"], ["troi", "Chuẩn kỳ & độ trôi"]];

function kyMacDinh() {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}`;
}

/** Chênh lệch. RỖNG hiện gạch, KHÔNG hiện 0 – "chưa ai khai" khác hẳn "khai rồi và khớp". */
function Lech({ x, tien }: { x: number | null | undefined; tien?: boolean }) {
  if (x === null || x === undefined) return <span className="muted">chưa xác định</span>;
  if (x === 0) return <Tag cls="ok">khớp</Tag>;
  const s = x > 0 ? "+" : "";
  return <b>{s}{tien ? vnd(x) : x}</b>;
}

function DoiSoatMarketing() {
  const { user, toast } = useShell();
  const [the, setThe] = useState("doi");
  const [ky, setKy] = useState(kyMacDinh());
  const [d, setD] = useState<any>(null);
  const [t, setT] = useState<any>(null);
  const [tr, setTr] = useState<any>(null);
  const [chot, setChot] = useState<any>(null);

  const chotDuoc = ["chutich", "tgd", "ptgd_mkt", "cntt"].includes(user?.role || "");

  const load = useCallback(() => {
    if (the === "doi") api(`/doi-soat-marketing/doi-chieu?ky=${ky}`).then(setD).catch((x) => toast(errMsg(x), true));
    if (the === "trung") api(`/doi-soat-marketing/trung-va-thieu-nguon?ky=${ky}`).then(setT).catch((x) => toast(errMsg(x), true));
    if (the === "troi") api(`/doi-soat-marketing/do-troi?ky=${ky}`).then(setTr).catch((x) => toast(errMsg(x), true));
  }, [the, ky]);                  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);

  const luuChot = async () => {
    try {
      const r = await api("/doi-soat-marketing/chot-ky", { method: "POST", json: {
        ky, ghi_chu: chot?.ghi_chu || "" } });
      toast(r.message || "Đã chốt"); setChot(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  return (<>
    <h1>Đối soát dữ liệu Marketing</h1>

    <div className="panel">
      <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        {THE.map(([v, n]) => <button key={v} className={"act" + (the === v ? " orange" : "")}
          onClick={() => setThe(v)}>{n}</button>)}
        <label style={{ marginLeft: 12 }}>Kỳ<br />
          <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>
      </div>
    </div>

    {/* ───────── 2.8.2 ĐỐI CHIẾU ───────── */}
    {the === "doi" && (!d ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      {d.canh_bao_chua_khai && <div className="panel"><p><Tag cls="warn">{d.canh_bao_chua_khai}</Tag></p></div>}

      <div className="panel"><h2>Hai sổ chi phí Marketing</h2>
        <div className="wrap"><table>
          <thead><tr><th>Sổ</th><th className="num">Số tiền</th></tr></thead>
          <tbody>
            <tr><td>Theo <b>đề nghị chi</b> đã chi (hạng mục &amp; chiến dịch)</td>
              <td className="num">{vnd(d.hai_so_chi_phi.theo_de_nghi_chi)}</td></tr>
            <tr><td>Theo <b>kênh</b> (Marketing khai khi nhập số lead)</td>
              <td className="num">{d.hai_so_chi_phi.theo_kenh_khai === null
                ? <span className="muted">chưa ai khai</span> : vnd(d.hai_so_chi_phi.theo_kenh_khai)}</td></tr>
            <tr><td><b>Chênh</b></td><td className="num"><Lech x={d.hai_so_chi_phi.lech} tien /></td></tr>
            <tr><td className="muted">Dự toán kỳ (không đem trừ – khác loại)</td>
              <td className="num muted">{vnd(d.hai_so_chi_phi.du_toan_ky)}</td></tr>
          </tbody></table></div>
        <p className="muted">{d.hai_so_chi_phi.co_so}</p>
        <p className="muted"><b>Màn hình này không chọn bên nào đúng.</b> Người duy nhất biết bên nào
          đúng là người đã ghi sổ ấy.</p>
      </div>

      <div className="panel wrap"><h2>Số lead: sổ thực so với khai báo</h2>
        <table><thead><tr><th>Kênh</th><th className="num">Sổ lead (dòng)</th>
          <th className="num">Số điện thoại khác nhau</th><th className="num">Marketing khai</th>
          <th className="num">Chênh</th><th>Khai lúc</th></tr></thead>
          <tbody>{(d.theo_kenh || []).map((r: any) => <tr key={r.kenh}>
            <td>{r.kenh}</td><td className="num">{r.so_lead_so_sach}</td>
            <td className="num">{r.so_sdt_so_sach}</td>
            <td className="num">{r.so_lead_khai_bao === null ? <span className="muted">–</span> : r.so_lead_khai_bao}</td>
            <td className="num"><Lech x={r.lech_lead} /></td>
            <td><small className="muted">{r.khai_luc ? r.khai_luc.replace("T", " ") : ""}{r.khai_boi ? ` · ${r.khai_boi}` : ""}</small></td>
          </tr>)}
          </tbody></table>
        <p className="muted"><b>Số điện thoại khác nhau</b> không phải là "số khách": hai người dùng
          chung một số đếm thành một, một người đổi số đếm thành hai.</p></div>

      <div className="panel"><h2>Doanh thu kỳ này</h2>
        <p>Tổng <b>{vnd(d.doanh_thu.tong)}</b> đ · truy được nguồn <b>{vnd(d.doanh_thu.truy_duoc_nguon)}</b> đ
          {d.doanh_thu.ty_le_truy_duoc !== null && <> ({Math.round(d.doanh_thu.ty_le_truy_duoc * 100)}%)</>}</p>
        {!!d.doanh_thu.chua_ro_nguon && <p><Tag cls="warn">
          Chưa rõ nguồn: {vnd(d.doanh_thu.chua_ro_nguon)} đ</Tag></p>}
        <p className="muted">Con số này lấy thẳng từ màn hình <b>Đóng góp doanh thu của Marketing</b>,
          không đếm lại — nên hai màn hình không thể ra hai số khác nhau.</p></div>
    </>)}

    {/* ───────── 2.8.1 TRÙNG & THIẾU NGUỒN ───────── */}
    {the === "trung" && (!t ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      <div className="panel"><h2>Kỳ {t.ky} – {t.tong_lead} lead</h2></div>

      <div className="panel wrap"><h2>Trùng dấu vân tay</h2>
        <p>{t.trung_dau_van_tay.so_nhom
          ? <Tag cls="red">{t.trung_dau_van_tay.so_nhom} nhóm</Tag>
          : <Tag cls="ok">Không có nhóm nào</Tag>}</p>
        <p className="muted">{t.trung_dau_van_tay.co_so}</p>
        {!!t.trung_dau_van_tay.so_nhom && <table>
          <thead><tr><th>Dấu vân tay</th><th className="num">Số lead</th><th>Mã lead</th></tr></thead>
          <tbody>{t.trung_dau_van_tay.rows.map((r: any) => <tr key={r.dau_van_tay}>
            <td className="mono">{r.dau_van_tay}</td><td className="num">{r.so_lead}</td>
            <td className="mono">{r.lead_id.join(", ")}</td></tr>)}
          </tbody></table>}</div>

      <div className="panel wrap"><h2>Nhiều lead cùng số điện thoại</h2>
        <p><Tag cls="navy">{t.nhieu_lead_cung_sdt.so_sdt} số</Tag></p>
        <p className="muted">{t.nhieu_lead_cung_sdt.co_so}</p>
        <table><thead><tr><th>Số điện thoại</th><th className="num">Số lead</th><th>Các lead</th></tr></thead>
          <tbody>{t.nhieu_lead_cung_sdt.rows.map((r: any) => <tr key={r.phone}>
            <td className="mono">{r.phone}</td><td className="num">{r.so_lead}</td>
            <td><small>{r.lead.map((x: any) => `${x.ten} (${x.kenh || "–"}, ${x.trang_thai})`).join(" · ")}</small></td>
          </tr>)}
          </tbody></table></div>

      <div className="panel"><h2>Thiếu nguồn</h2>
        <p>Lead chưa ghi kênh: <b>{t.lead_thieu_kenh.so_lead}</b></p>
        <p>Booking chưa truy được nguồn: <b>{t.booking_thieu_nguon.so_booking}</b> –{" "}
          {vnd(t.booking_thieu_nguon.tien)} đ</p>
        <p className="muted">{t.booking_thieu_nguon.ghi_chu}</p></div>
    </>)}

    {/* ───────── 2.8.3 CHUẨN KỲ & ĐỘ TRÔI ───────── */}
    {the === "troi" && (!tr ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      <div className="panel">
        <h2>Chuẩn kỳ {tr.ky}</h2>
        {!tr.da_chot
          ? <p><Tag cls="warn">{tr.canh_bao}</Tag></p>
          : <>
            <p className="muted">Chốt lúc <b>{tr.chot_luc.replace("T", " ")}</b> bởi <b>{tr.chot_boi}</b>
              {tr.ghi_chu ? ` · ${tr.ghi_chu}` : ""}</p>
            <p>{tr.co_troi ? <Tag cls="warn">Số đã trôi so với lúc chốt</Tag>
              : <Tag cls="ok">Chưa trôi ô nào</Tag>}</p>
          </>}
        {chotDuoc && <div style={{ marginTop: 12 }}>
          {chot ? <>
            <label>Ghi chú (không bắt buộc)<br />
              <input value={chot.ghi_chu} onChange={(e) => setChot({ ghi_chu: e.target.value })} /></label>
            <div style={{ marginTop: 8 }}>
              <button className="act orange" onClick={luuChot}>Xác nhận chốt số kỳ {ky}</button>{" "}
              <button className="act" onClick={() => setChot(null)}>Thôi</button></div>
          </> : <button className="act" onClick={() => setChot({ ghi_chu: "" })}>
            {tr.da_chot ? "Chốt lại số kỳ này" : "Chốt số kỳ này"}</button>}
          <p className="muted">Chốt lại là <b>ghi đè mốc cũ</b>: mỗi kỳ giữ đúng một mốc chuẩn. Muốn
            biết nó từng là gì thì tra nhật ký nghiệp vụ — mỗi lần chốt để lại một dòng kèm cả bộ số
            cũ lẫn bộ số mới.</p>
        </div>}
      </div>

      {tr.da_chot && <div className="panel wrap"><h2>Đã trôi bao nhiêu</h2>
        <table><thead><tr><th>Chỉ tiêu</th><th className="num">Lúc chốt</th>
          <th className="num">Hiện tại</th><th className="num">Trôi</th></tr></thead>
          <tbody>{tr.dong.map((r: any) => <tr key={r.o}>
            <td>{r.ten}</td>
            <td className="num">{r.luc_chot === null || r.luc_chot === undefined ? <span className="muted">–</span> : vnd(r.luc_chot)}</td>
            <td className="num">{vnd(r.hien_tai)}</td>
            <td className="num"><Lech x={r.troi} tien /></td></tr>)}
          </tbody></table>
        <p className="muted">{tr.co_so}</p></div>}
    </>)}
  </>);
}

export default function Page() { return <Shell><DoiSoatMarketing /></Shell>; }
