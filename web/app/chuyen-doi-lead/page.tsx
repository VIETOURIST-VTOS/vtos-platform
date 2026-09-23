"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Chuyển đổi & phối hợp Sales – nhóm 2.6.
 *
 *  BA THẺ, BA CÂU HỎI VỀ QUÃNG GIỮA HAI PHÒNG. Marketing giao lead, Sales xử lý; cả ba câu đều
 *  hỏi về đoạn ở giữa, đoạn mà trước vòng này không bảng nào nhìn vào.
 *
 *  THẺ "TỒN ĐỌNG" LÀ THẺ MỞ SẴN, cố ý. Hai thẻ kia nhìn về quá khứ đã khép và chỉ để rút kinh
 *  nghiệm; thẻ tồn đọng nhìn vào việc đang dở, và nó là thứ duy nhất còn sửa được bằng hành động
 *  hôm nay. Mở màn hình ra thấy ngay việc phải làm, không phải bấm thêm một nhát.
 */

const THE: [string, string][] = [
  ["ton", "Lead tồn đọng"], ["chuyen", "Chốt sau bao lâu"], ["mat", "Lý do mất khách"]];

function kyMacDinh() {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}`;
}

function ChuyenDoiLead() {
  const { user, toast } = useShell();
  const [the, setThe] = useState("ton");
  const [ky, setKy] = useState(kyMacDinh());
  const [ton, setTon] = useState<any>(null);
  const [cd, setCd] = useState<any>(null);
  const [mat, setMat] = useState<any>(null);
  const [nguoi, setNguoi] = useState<any[]>([]);
  const [giao, setGiao] = useState<any>(null);
  const [ghi, setGhi] = useState<any>(null);
  const [su, setSu] = useState<any>(null);

  const ghiDuoc = ["chutich", "tgd", "ptgd_mkt", "gd_kd", "tp_kd", "cntt", "nv_mkt"]
    .includes(user?.role || "");

  const load = useCallback(() => {
    if (the === "ton") api("/chuyen-doi-lead/ton-dong").then(setTon).catch((x) => toast(errMsg(x), true));
    if (the === "chuyen") api(`/chuyen-doi-lead/chuyen-doi?ky=${ky}`).then(setCd).catch((x) => toast(errMsg(x), true));
    if (the === "mat") api(`/chuyen-doi-lead/ly-do-mat?ky=${ky}`).then(setMat).catch((x) => toast(errMsg(x), true));
  }, [the, ky]);                    // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);
  // Danh sách người nhận đi kèm luôn trong bản trả của thẻ "tồn đọng" – CỐ Ý không gọi sang
  // /api/v1/users. Gọi sang nhóm khác thì phép thử khai quyền bắt khai nhóm ấy, và khai là cấp
  // CẢ nhóm tài khoản cho mọi vai mở được màn hình này, trong đó có nv_kd. Vấp đúng chỗ này một
  // lần ở TC-73 rồi.
  useEffect(() => { setNguoi(ton?.nguoi_nhan || []); }, [ton]);

  const luuGiao = async () => {
    if (!giao) return;
    try {
      const r = await api("/chuyen-doi-lead/ban-giao", { method: "POST", json: {
        lead_id: giao.lead_id,
        den_nguoi_id: giao.den_nguoi_id ? Number(giao.den_nguoi_id) : null,
        han_moi: giao.han_moi || null, ly_do: giao.ly_do } });
      toast(r.message || "Đã ghi"); setGiao(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const luuGhi = async () => {
    if (!ghi) return;
    try {
      const r = await api("/chuyen-doi-lead/ly-do-mat", { method: "POST", json: {
        lead_id: ghi.lead_id, ma_ly_do: ghi.ma_ly_do, ghi_chu: ghi.ghi_chu || "" } });
      toast(r.message || "Đã ghi"); setGhi(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const moSu = async (lead_id: number) => {
    try { setSu(await api(`/chuyen-doi-lead/lead/${lead_id}/ban-giao`)); }
    catch (x) { toast(errMsg(x), true); }
  };

  return (<>
    <h1>Chuyển đổi &amp; phối hợp Sales</h1>

    <div className="panel">
      <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
        {THE.map(([v, t]) => <button key={v} className={"act" + (the === v ? " orange" : "")}
          onClick={() => setThe(v)}>{t}</button>)}
        {the !== "ton" && <label style={{ marginLeft: 12 }}>Kỳ lead<br />
          <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></label>}
      </div>
    </div>

    {/* ───────── 2.6.2 TỒN ĐỌNG ───────── */}
    {the === "ton" && (!ton ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      <div className="panel">
        <h2>Lead đang mở</h2>
        <p style={{ fontSize: 24, margin: "4px 0" }}>
          <b>{ton.tong_qua_han}</b> quá hạn <small style={{ fontSize: 15 }}>trên {ton.tong_dang_mo} lead đang mở</small></p>
        <p className="muted">Hạn đã ký: <b>{ton.gio_han_da_ky} giờ</b>. Tính đến {ton.tinh_den}.</p>
        <p className="muted">{ton.co_so}</p>
      </div>

      <div className="panel wrap"><h2>Theo người đang giữ</h2>
        <table><thead><tr><th>Người</th><th className="num">Đang giữ</th><th className="num">Quá hạn</th><th className="num">Chưa ai chạm</th></tr></thead>
          <tbody>{(ton.theo_nguoi || []).map((r: any) => <tr key={r.nguoi}>
            <td>{r.nguoi}</td><td className="num">{r.tong}</td>
            <td className="num">{r.qua_han ? <b>{r.qua_han}</b> : 0}</td>
            <td className="num">{r.chua_cham}</td></tr>)}
          </tbody></table></div>

      <div className="panel wrap"><h2>Nằm im bao lâu</h2>
        <table><thead><tr><th>Khoảng</th><th className="num">Số lead</th></tr></thead>
          <tbody>
            <tr><td>Đến 30 ngày</td><td className="num">{ton.theo_tuoi.den_30}</td></tr>
            <tr><td>31–60 ngày</td><td className="num">{ton.theo_tuoi.den_60}</td></tr>
            <tr><td>61–90 ngày</td><td className="num">{ton.theo_tuoi.den_90}</td></tr>
            <tr><td>Trên 90 ngày</td><td className="num">{ton.theo_tuoi.tren_90}</td></tr>
          </tbody></table>
        <p className="muted">Bốn khoảng này dùng đúng bộ mốc của thẻ <b>Chốt sau bao lâu</b> — hai
          thẻ đọc chung một bộ mốc thì mới so được với nhau.</p></div>

      <div className="panel wrap"><h2>Từng lead</h2>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Kênh</th><th>Người giữ</th>
          <th>Hạn</th><th className="num">Nằm im</th><th></th>{ghiDuoc && <th></th>}</tr></thead>
          <tbody>{(ton.rows || []).map((r: any) => <tr key={r.lead_id}>
            <td className="mono">{r.ma_lead || r.lead_id}</td>
            <td>{r.ten}<br /><small className="muted">{r.phone}</small></td>
            <td>{r.kenh}</td><td>{r.nguoi_giu}</td>
            <td>{r.han ? r.han.slice(0, 10) : <span className="muted">–</span>}{" "}
              {r.nguon_han === "da_hen" ? <Tag>đã hẹn</Tag> : null}
              {r.qua_han && <> <Tag cls="red">quá hạn</Tag></>}</td>
            <td className="num">{r.so_ngay_nam_im}</td>
            <td><button className="act" onClick={() => moSu(r.lead_id)}>Lịch sử</button></td>
            {ghiDuoc && <td><button className="act" onClick={() => setGiao({ lead_id: r.lead_id, ma: r.ma_lead || r.lead_id, den_nguoi_id: "", han_moi: "", ly_do: "" })}>Bàn giao</button></td>}
          </tr>)}
          {!(ton.rows || []).length && <tr><td colSpan={ghiDuoc ? 8 : 7}><Tag cls="ok">Không còn lead nào đang mở</Tag></td></tr>}
          </tbody></table>
        <p className="muted">Lead có <b>hạn đã hẹn</b> thì chấm theo hạn ấy, không theo luật chung —
          Sales đã hứa một ngày cụ thể với khách thì đó mới là lời hứa có thật.</p></div>
    </>)}

    {/* ───────── 2.6.1 CHỐT SAU BAO LÂU ───────── */}
    {the === "chuyen" && (!cd ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      <div className="panel">
        <h2>Lead kỳ {cd.ky} chốt sau bao lâu</h2>
        <p style={{ fontSize: 24, margin: "4px 0" }}>
          {cd.ty_le_chot === null ? <span className="muted">Chưa xác định</span>
            : <><b>{Math.round(cd.ty_le_chot * 100)}%</b> <small style={{ fontSize: 15 }}>
              — {cd.da_chot} trên {cd.tong_lead} lead</small></>}</p>
        {cd.canh_bao_chua_doi_chieu && <p><Tag cls="warn">{cd.canh_bao_chua_doi_chieu}</Tag></p>}
        <p className="muted">{cd.co_so}</p>
        <div className="wrap"><table>
          <thead><tr><th>Ngăn</th><th className="num">Số lead</th><th className="num">Cộng dồn</th></tr></thead>
          <tbody>
            <tr><td>{cd.ten_ngan.trong_30}</td><td className="num">{cd.theo_ngan.trong_30}</td><td className="num">{cd.cong_don.den_30}</td></tr>
            <tr><td>{cd.ten_ngan.trong_60}</td><td className="num">{cd.theo_ngan.trong_60}</td><td className="num">{cd.cong_don.den_60}</td></tr>
            <tr><td>{cd.ten_ngan.trong_90}</td><td className="num">{cd.theo_ngan.trong_90}</td><td className="num">{cd.cong_don.den_90}</td></tr>
            <tr><td>{cd.ten_ngan.tren_90}</td><td className="num">{cd.theo_ngan.tren_90}</td><td className="num"></td></tr>
            <tr><td>{cd.ten_ngan.da_chot_khong_ro_ngay} <Tag cls="warn">không xếp mốc</Tag></td>
              <td className="num">{cd.theo_ngan.da_chot_khong_ro_ngay}</td><td className="num"></td></tr>
            <tr><td>{cd.ten_ngan.chua_chot_con_mo}</td><td className="num">{cd.theo_ngan.chua_chot_con_mo}</td><td className="num"></td></tr>
            <tr><td>{cd.ten_ngan.da_mat}</td><td className="num">{cd.theo_ngan.da_mat}</td><td className="num"></td></tr>
          </tbody></table></div>
        <p className="muted"><b>Đã chốt, không rõ ngày</b> nằm riêng chứ không nhét vào mốc nào:
          phép đối chiếu theo số điện thoại biết lead ấy đã chốt nhưng không biết chốt lúc nào. Nhét
          vào “trên 90 ngày” cho gọn là bịa; xếp vào “trong 30” cho đẹp lại càng bịa.</p>
        <p className="muted"><b>Chưa chốt, còn đang chăm sóc</b> khác <b>đã đánh dấu không chốt</b>:
          gộp hai ngăn ấy là kết luận thay cho tương lai của những lead còn đang mở.</p>
      </div>

      <div className="panel wrap"><h2>Theo kênh</h2>
        <table><thead><tr><th>Kênh</th><th className="num">Lead</th><th className="num">≤30</th>
          <th className="num">31–60</th><th className="num">61–90</th><th className="num">&gt;90</th>
          <th className="num">Chưa rõ ngày</th></tr></thead>
          <tbody>{(cd.theo_kenh || []).map((r: any) => <tr key={r.kenh}>
            <td>{r.kenh}</td><td className="num">{r.tong}</td>
            <td className="num">{r.trong_30}</td><td className="num">{r.trong_60}</td>
            <td className="num">{r.trong_90}</td><td className="num">{r.tren_90}</td>
            <td className="num">{r.da_chot_khong_ro_ngay}</td></tr>)}
          </tbody></table></div>
    </>)}

    {/* ───────── 2.6.3 LÝ DO MẤT ───────── */}
    {the === "mat" && (!mat ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>
      <div className="panel wrap"><h2>Mất vì lý do gì – kỳ {mat.ky}</h2>
        <p><b>{mat.tong_mat}</b> lead đã đánh dấu không chốt</p>
        <table><thead><tr><th>Lý do</th><th className="num">Số lead</th></tr></thead>
          <tbody>{(mat.theo_ly_do || []).map((r: any) => <tr key={r.ma}>
            <td>{r.ten}</td><td className="num">{r.so_lead}</td></tr>)}
          {!(mat.theo_ly_do || []).length && <tr><td colSpan={2} className="muted">Chưa lead nào được ghi lý do.</td></tr>}
          </tbody></table></div>

      <div className="panel">
        <h2>Tái chăm sóc</h2>
        <p><b>{mat.tai_cham_soc.so_sdt_quay_lai}</b> trên {mat.tai_cham_soc.tren_tong_sdt_mat} số
          điện thoại từng đánh dấu mất sau đó đã chốt</p>
        <p className="muted">{mat.tai_cham_soc.co_so}</p>
      </div>

      {!!mat.chua_ghi_ly_do.so_lead && <div className="panel wrap">
        <h2>Chưa ai ghi lý do</h2>
        <p><Tag cls="warn">{mat.chua_ghi_ly_do.so_lead} lead</Tag></p>
        <p className="muted">Đánh dấu mất mà không ghi vì sao thì bảng trên chỉ nói được một phần,
          và phần thiếu ấy không ai nhìn thấy nếu không liệt kê ra đây.</p>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Kênh</th>{ghiDuoc && <th></th>}</tr></thead>
          <tbody>{mat.chua_ghi_ly_do.rows.map((r: any) => <tr key={r.lead_id}>
            <td className="mono">{r.ma_lead || r.lead_id}</td>
            <td>{r.ten}<br /><small className="muted">{r.phone}</small></td><td>{r.kenh}</td>
            {ghiDuoc && <td><button className="act" onClick={() => setGhi({ lead_id: r.lead_id, ma_ly_do: "", ghi_chu: "" })}>Ghi lý do</button></td>}
          </tr>)}
          </tbody></table></div>}
    </>)}

    {/* ───────── BÀN GIAO ───────── */}
    {giao && <div className="panel"><h2>Bàn giao lead {giao.ma}</h2>
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Giao cho<br /><select value={giao.den_nguoi_id} onChange={(e) => setGiao({ ...giao, den_nguoi_id: e.target.value })}>
          <option value="">— giữ nguyên người đang có —</option>
          {nguoi.map((n: any) => <option key={n.id} value={n.id}>{n.full_name || n.username}</option>)}
        </select></label>
        <label>Hạn mới<br /><input type="date" value={giao.han_moi} onChange={(e) => setGiao({ ...giao, han_moi: e.target.value })} /></label>
        <label>Lý do (bắt buộc)<br /><input value={giao.ly_do} onChange={(e) => setGiao({ ...giao, ly_do: e.target.value })} /></label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="act orange" onClick={luuGiao}>Lưu</button>{" "}
        <button className="act" onClick={() => setGiao(null)}>Thôi</button></div>
      <p className="muted">Người nhận cần biết vì sao lead đến tay mình, và cuối kỳ còn tra lại được —
        nên lý do là bắt buộc. Mỗi lần bàn giao để lại một dòng trong sổ bàn giao của lead.</p>
    </div>}

    {/* ───────── GHI LÝ DO MẤT ───────── */}
    {ghi && <div className="panel"><h2>Ghi lý do không chốt</h2>
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Lý do<br /><select value={ghi.ma_ly_do} onChange={(e) => setGhi({ ...ghi, ma_ly_do: e.target.value })}>
          <option value="">— chọn —</option>
          {Object.entries(mat?.danh_muc_ly_do || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
        </select></label>
        <label>Ghi chú{ghi.ma_ly_do === "khac" ? " (bắt buộc)" : ""}<br />
          <input value={ghi.ghi_chu} onChange={(e) => setGhi({ ...ghi, ghi_chu: e.target.value })} /></label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="act orange" disabled={!ghi.ma_ly_do} onClick={luuGhi}>Lưu</button>{" "}
        <button className="act" onClick={() => setGhi(null)}>Thôi</button></div>
      <p className="muted">Cửa này chỉ <b>điền chỗ trống</b>. Lead đã có lý do thì sửa ở màn hình
        Khách hàng tiềm năng, nơi có nhật ký sửa đầy đủ.</p>
    </div>}

    {/* ───────── SỔ BÀN GIAO ───────── */}
    {su && <div className="panel wrap"><h2>Sổ bàn giao – lead {su.lead_id}</h2>
      <table><thead><tr><th>Lúc</th><th>Việc</th><th>Từ</th><th>Đến</th><th>Hạn cũ</th><th>Hạn mới</th><th>Lý do</th><th>Bởi</th></tr></thead>
        <tbody>{su.rows.map((r: any) => <tr key={r.id}>
          <td>{r.luc.replace("T", " ")}</td><td>{r.viec_ten}</td>
          <td>{r.tu_nguoi}</td><td>{r.den_nguoi}</td>
          <td>{r.han_cu}</td><td>{r.han_moi}</td><td>{r.ly_do}</td><td>{r.boi}</td></tr>)}
        {!su.rows.length && <tr><td colSpan={8} className="muted">Lead này chưa có lần bàn giao nào.</td></tr>}
        </tbody></table>
      <button className="act" onClick={() => setSu(null)}>Đóng</button></div>}
  </>);
}

export default function Page() { return <Shell><ChuyenDoiLead /></Shell>; }
