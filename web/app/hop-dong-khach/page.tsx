"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** V6 – Hợp đồng khách: mắt xích giữa báo giá đã chốt và booking.
 *
 *  Số hợp đồng và ngày ký là thứ kiểm toán hỏi đầu tiên khi đối chiếu doanh thu, và trước V6 hệ thống
 *  không có chỗ nào giữ chúng.
 *
 *  Giá trị hợp đồng lấy từ BẢN BÁO GIÁ ĐÃ GỬI, không lấy từ bản đang soạn: khách chốt con số hôm ấy.
 */
type HD = { id: number; so_hop_dong: string; bao_gia_id: number | null; booking_id: number | null;
            khach_ten: string; khach_dai_dien: string; khach_ma_so_thue: string;
            ngay_ky: string | null; gia_tri: number; dat_coc: number;
            han_thanh_toan: string | null; trang_thai: string };

const vnd = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";
const pct = (n: number | null) => (n === null || n === undefined ? "–" : (n * 100).toFixed(1) + "%");

function HopDong() {
  const { toast } = useShell();
  const [ds, setDs] = useState<HD[]>([]);
  const [chuoi, setChuoi] = useState<Record<number, any>>({});

  const load = useCallback(async () => {
    try { setDs(await api<HD[]>("/ban-hang/hop-dong")); }
    catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const [dang, setDang] = useState(false);

  // Nối hợp đồng với booking đã tạo. Đây là mắt xích cuối của chuỗi bán hàng, và trước 09/9 nó KHÔNG
  // có nút nào: màn hình này chỉ đọc, nên chuỗi dừng ở hợp đồng và không ai nối được sang booking.
  // Bộ kiểm cửa nhập của làn Kiểm soát bắt được chỗ hở này.
  const noiBooking = async (h: HD) => {
    const id = window.prompt(`Nối hợp đồng ${h.so_hop_dong} với booking nào?\n` +
                             "Nhập SỐ ID của booking (xem ở màn hình Booking):");
    if (!id || !id.trim()) return;
    const bid = id.trim();
    if (!/^\d+$/.test(bid)) { toast("ID booking phải là một số", true); return; }
    setDang(true);
    try {
      // Đặt bid ra một biến riêng thay vì gọi id.trim() thẳng trong chuỗi: bộ kiểm cửa nhập đọc mã
      // bằng biểu thức chính quy, và một lời gọi lồng trong chuỗi làm nó cắt sớm rồi kết luận màn
      // hình này KHÔNG có cửa ghi. Viết phẳng ra thì cả người lẫn máy đọc đều thấy đúng.
      const r = await api<any>(`/ban-hang/hop-dong/${h.id}/booking/${bid}`, { method: "POST" });
      toast(r.message || "Đã nối booking");
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  // VPM-9 – lịch thanh toán theo tiến độ. Trước bản này một hợp đồng đoàn vài trăm triệu chỉ có MỘT
  // hạn, nên câu hỏi của người thu công nợ — "đến hôm nay khách phải trả bao nhiêu" — không có chỗ
  // nào trong phần mềm trả lời được.
  const [lich, setLich] = useState<Record<number, any>>({});
  const [soan, setSoan] = useState<any>(null);
  const [dongSoan, setDongSoan] = useState<any[]>([]);

  const xemLich = async (id: number) => {
    if (lich[id]) { setLich({ ...lich, [id]: null }); return; }
    try { setLich({ ...lich, [id]: await api<any>(`/ban-hang/hop-dong/${id}/lich-thanh-toan`) }); }
    catch (e) { toast(errMsg(e), true); }
  };

  const moSoan = (h: HD) => {
    setSoan(h);
    const cu = lich[h.id]?.dot || [];
    setDongSoan(cu.length ? cu.map((d: any) => ({
      ten: d.ten, so_tien: String(d.so_tien || ""), ty_le: d.ty_le ?? "",
      moc: d.moc, moc_so_ngay: d.moc_so_ngay ?? "", han: d.han || "", ghi_chu: d.ghi_chu || "",
    })) : [{ ten: "Đặt cọc khi ký", so_tien: "", ty_le: "", moc: "ngay_ky", moc_so_ngay: 0, han: "", ghi_chu: "" }]);
  };

  const luuLich = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!soan) return;
    const dot = dongSoan.map((d) => ({
      ten: d.ten, so_tien: Number(d.so_tien || 0),
      ty_le: d.ty_le === "" ? null : Number(d.ty_le),
      moc: d.moc, moc_so_ngay: d.moc_so_ngay === "" ? null : Number(d.moc_so_ngay),
      han: d.moc === "co_dinh" ? (d.han || null) : null, ghi_chu: d.ghi_chu,
    }));
    try {
      const r = await api<any>(`/ban-hang/hop-dong/${soan.id}/lich-thanh-toan`, { method: "POST", json: { dot } });
      toast(r.message);
      setSoan(null); setLich({ ...lich, [soan.id]: null }); await xemLich(soan.id);
    } catch (x) { toast(errMsg(x), true); }
  };

  const doiHan = async (hid: number, d: any) => {
    const ngay = window.prompt(`Dời hạn đợt ${d.dot} (${d.ten}) — hạn hiện tại ${d.han || "chưa có"}.\n` +
                               "Nhập ngày mới dạng YYYY-MM-DD:");
    if (!ngay || !ngay.trim()) return;
    const ly_do = window.prompt("Lý do dời hạn (bắt buộc — hạn này đã nằm trong hợp đồng khách đang cầm):");
    if (!ly_do || !ly_do.trim()) { toast("Phải ghi lý do dời hạn", true); return; }
    const han = ngay.trim();
    try {
      const r = await api<any>(`/ban-hang/hop-dong/lich-thanh-toan/${d.id}/doi-han`,
                               { method: "POST", json: { han, ly_do } });
      toast(r.message);
      setLich({ ...lich, [hid]: null }); await xemLich(hid);
    } catch (x) { toast(errMsg(x), true); }
  };

  const xemChuoi = async (id: number) => {
    if (chuoi[id]) { setChuoi({ ...chuoi, [id]: null }); return; }
    try { setChuoi({ ...chuoi, [id]: await api<any>(`/ban-hang/hop-dong/${id}/chuoi`) }); }
    catch (e) { toast(errMsg(e), true); }
  };

  return (
    <div className="wrap">
      <h1>Hợp đồng khách</h1>
      <p className="muted">
        Mắt xích giữa báo giá đã chốt và booking. Giá trị hợp đồng lấy từ <b>bản báo giá đã gửi</b>,
        không lấy từ bản đang soạn — khách chốt con số hôm ấy, và chênh lệch chỉ lộ ra lúc đối chiếu
        doanh thu vài tháng sau.
      </p>

      <div className="card">
        <h3>{ds.length} hợp đồng</h3>
        {ds.length === 0 ? <p className="muted">Chưa có hợp đồng nào.</p> : (
          <table className="tbl">
            <thead><tr><th>Số HĐ</th><th>Khách</th><th>MST</th><th>Ngày ký</th>
              <th style={{ textAlign: "right" }}>Giá trị</th>
              <th style={{ textAlign: "right" }}>Đặt cọc</th><th>Booking</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>
              {ds.map((h) => (
                <>
                  <tr key={h.id}>
                    <td className="mono">{h.so_hop_dong}</td>
                    <td><b>{h.khach_ten}</b>
                      {h.khach_dai_dien ? <div className="muted small">đại diện: {h.khach_dai_dien}</div> : null}</td>
                    <td className="mono">{h.khach_ma_so_thue || "–"}</td>
                    <td>{h.ngay_ky || <Tag cls="warn">chưa ký</Tag>}</td>
                    <td style={{ textAlign: "right" }}>{vnd(h.gia_tri)}</td>
                    <td style={{ textAlign: "right" }}>{vnd(h.dat_coc)}</td>
                    <td>{h.booking_id ? `#${h.booking_id}` : <Tag cls="warn">chưa nối</Tag>}</td>
                    <td>{h.trang_thai}</td>
                    <td className="nut">
                      {!h.booking_id ? (
                        <button className="ghost" disabled={dang}
                                onClick={() => noiBooking(h)}>Nối booking</button>) : null}
                      <button className="ghost" onClick={() => xemChuoi(h.id)}>Trọn đường</button>
                      <button className="ghost" onClick={() => xemLich(h.id)}>Lịch thanh toán</button>
                    </td>
                  </tr>
                  {lich[h.id] ? (
                    <tr key={`${h.id}-lich`}><td colSpan={9} className="chitiet">
                      <p>
                        <b>Phải trả đến hôm nay: {vnd(lich[h.id].phai_tra_den_hom_nay)}</b>
                        {" · "}đã đến hạn {vnd(lich[h.id].den_han_hom_nay)}
                        {" · "}đã thu {vnd(lich[h.id].da_thu)}
                        {lich[h.id].khop_gia_tri === false ?
                          <Tag cls="red"> tổng các đợt KHÔNG khớp giá trị hợp đồng</Tag> : null}
                      </p>
                      {(lich[h.id].canh_bao || []).map((c: string, i: number) => (
                        <p className="warn" key={i}>{c}</p>))}
                      {lich[h.id].dot.length === 0 ? (
                        <p className="muted">Chưa có lịch — hợp đồng này đang chỉ có một hạn duy nhất.</p>
                      ) : (
                        <table className="tbl">
                          <thead><tr><th>Đợt</th><th>Tên</th><th>Mốc</th><th>Hạn</th>
                            <th style={{ textAlign: "right" }}>Số tiền</th>
                            <th style={{ textAlign: "right" }}>Đã rải</th>
                            <th style={{ textAlign: "right" }}>Còn thiếu</th><th>Trạng thái</th><th></th></tr></thead>
                          <tbody>{lich[h.id].dot.map((d: any) => (
                            <tr key={d.id}>
                              <td>{d.dot}</td>
                              <td>{d.ten}{d.ty_le ? <div className="muted small">{d.ty_le}% giá trị HĐ</div> : null}
                                {d.ghi_chu ? <div className="muted small">{d.ghi_chu}</div> : null}</td>
                              <td className="muted small">{d.moc_mo_ta}{d.moc_so_ngay != null ? ` ${d.moc_so_ngay} ngày` : ""}</td>
                              <td>{d.han || "–"}{d.da_doi_han ? <div className="muted small">gốc {d.han_goc}</div> : null}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.so_tien)}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.da_rai)}</td>
                              <td style={{ textAlign: "right" }}>{d.con_thieu > 0 ? vnd(d.con_thieu) : "–"}</td>
                              <td>{d.trang_thai === "da_du" ? <Tag cls="ok">đã đủ</Tag>
                                : d.qua_han ? <Tag cls="red">quá hạn</Tag> : <Tag cls="warn">chờ đến hạn</Tag>}</td>
                              <td className="nut"><button className="ghost" onClick={() => doiHan(h.id, d)}>dời hạn</button></td>
                            </tr>))}</tbody>
                        </table>
                      )}
                      <p className="muted small">{lich[h.id].ghi_chu_man_hinh}</p>
                      <button className="ghost" onClick={() => moSoan(h)}>
                        {lich[h.id].dot.length ? "Sửa lịch" : "Đặt lịch thanh toán"}</button>
                    </td></tr>
                  ) : null}
                  {chuoi[h.id] ? (
                    <tr key={`${h.id}-chuoi`}><td colSpan={9} className="chitiet">
                      <div className="buoc">
                        {[["Bảng giá", chuoi[h.id].bang_gia && `${chuoi[h.id].bang_gia.ma} · ${chuoi[h.id].bang_gia.ten}`],
                          ["Báo giá", chuoi[h.id].bao_gia && `${chuoi[h.id].bao_gia.ma} · ${chuoi[h.id].bao_gia.trang_thai}`],
                          ["Bản đã gửi", chuoi[h.id].ban_da_gui &&
                            `lần ${chuoi[h.id].ban_da_gui.lan} · ${vnd(chuoi[h.id].ban_da_gui.tong_ban)} · biên ` +
                            (chuoi[h.id].ban_da_gui.du_co_so ? pct(chuoi[h.id].ban_da_gui.bien) : "chưa đủ cơ sở")],
                          ["Hợp đồng", `${h.so_hop_dong} · ${vnd(h.gia_tri)}`],
                          ["Booking", h.booking_id ? `#${h.booking_id}` : null],
                        ].map(([ten, gt]: any) => (
                          <div className={`o ${gt ? "co" : "thieu"}`} key={ten}>
                            <div className="ten">{ten}</div>
                            <div className="gt">{gt || "chưa có"}</div>
                          </div>
                        ))}
                      </div>
                      {chuoi[h.id].bao_gia?.duoi_bien ? (
                        <p className="warn">Báo giá này đã gửi khách <b>dưới ngưỡng biên</b> (biên lúc gửi{" "}
                          {pct(chuoi[h.id].bao_gia.bien_luc_gui)}) — có giải trình kèm theo ở màn hình Báo giá.</p>
                      ) : null}
                      {!chuoi[h.id].day_du ? (
                        <p className="warn">Chuỗi còn <b>đứt</b> — ô nào ghi “chưa có” là mắt xích còn thiếu.</p>
                      ) : null}
                    </td></tr>
                  ) : null}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {soan ? (
        <form className="card" onSubmit={luuLich}>
          <h3>Lịch thanh toán — {soan.so_hop_dong} · giá trị {vnd(soan.gia_tri)}</h3>
          <p className="muted">
            Tổng các đợt phải <b>bằng đúng</b> giá trị hợp đồng, lệch thì hệ thống không ghi gì. Số tiền
            của đợt được <b>chốt thành tiền</b>; tỷ lệ % chỉ để kể lại con số từ đâu ra, sửa giá trị hợp
            đồng sau này sẽ không lặng lẽ đổi số tiền đòi khách.
          </p>
          <table className="tbl">
            <thead><tr><th>Tên đợt</th><th>Số tiền</th><th>% (ghi chú)</th><th>Mốc hạn</th>
              <th>Số ngày</th><th>Ngày cố định</th><th>Ghi chú</th><th></th></tr></thead>
            <tbody>{dongSoan.map((d, i) => (
              <tr key={i}>
                <td><input value={d.ten} onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, ten: e.target.value }; setDongSoan(a); }} /></td>
                <td><input type="number" step={1000} value={d.so_tien} required
                           onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, so_tien: e.target.value }; setDongSoan(a); }} /></td>
                <td><input type="number" step="0.1" value={d.ty_le}
                           onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, ty_le: e.target.value }; setDongSoan(a); }} /></td>
                <td><select value={d.moc} onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, moc: e.target.value }; setDongSoan(a); }}>
                  <option value="ngay_ky">sau ngày ký hợp đồng</option>
                  <option value="truoc_khoi_hanh">trước ngày khởi hành</option>
                  <option value="sau_khoi_hanh">sau ngày khởi hành</option>
                  <option value="co_dinh">ngày cố định</option>
                </select></td>
                <td><input type="number" value={d.moc_so_ngay} disabled={d.moc === "co_dinh"}
                           onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, moc_so_ngay: e.target.value }; setDongSoan(a); }} /></td>
                <td><input type="date" value={d.han} disabled={d.moc !== "co_dinh"}
                           onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, han: e.target.value }; setDongSoan(a); }} /></td>
                <td><input value={d.ghi_chu} onChange={(e) => { const a = [...dongSoan]; a[i] = { ...d, ghi_chu: e.target.value }; setDongSoan(a); }} /></td>
                <td className="nut"><button type="button" className="ghost"
                    onClick={() => setDongSoan(dongSoan.filter((_, j) => j !== i))}>bỏ</button></td>
              </tr>))}</tbody>
          </table>
          <p>
            Tổng đang soạn: <b>{vnd(dongSoan.reduce((t, d) => t + Number(d.so_tien || 0), 0))}</b>
            {" / "}{vnd(soan.gia_tri)}
            {Math.abs(dongSoan.reduce((t, d) => t + Number(d.so_tien || 0), 0) - soan.gia_tri) > 0.5 ?
              <Tag cls="warn"> chưa khớp</Tag> : <Tag cls="ok"> khớp</Tag>}
          </p>
          <button type="button" className="ghost" onClick={() => setDongSoan([...dongSoan,
            { ten: `Đợt ${dongSoan.length + 1}`, so_tien: "", ty_le: "", moc: "truoc_khoi_hanh", moc_so_ngay: 7, han: "", ghi_chu: "" }])}>
            Thêm đợt</button>{" "}
          <button type="submit">Lưu lịch</button>{" "}
          <button type="button" className="ghost" onClick={() => setSoan(null)}>Đóng</button>
        </form>
      ) : null}

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1250px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .chitiet { background: #f8fafc; }
        .buoc { display: flex; gap: 10px; flex-wrap: wrap; margin: 6px 0 10px; }
        .o { border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; min-width: 150px; }
        .o.thieu { border-style: dashed; color: #92400e; background: #fffbeb; }
        .o .ten { font-size: 12px; color: #64748b; }
        .o .gt { font-weight: 600; font-size: 13px; }
        .nut { white-space: nowrap; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid #cbd5e1;
                 background: #fff; color: #0f172a; cursor: pointer; font-size: 13px; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><HopDong /></Shell>; }
