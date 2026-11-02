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
            han_thanh_toan: string | null; trang_thai: string; phien_ban: number };

const vnd = (n: number) => (n || 0).toLocaleString("vi-VN") + " đ";
const pct = (n: number | null) => (n === null || n === undefined ? "–" : (n * 100).toFixed(1) + "%");

function HopDong() {
  const { toast, user } = useShell();
  // TR-1d (Chủ tịch 02/11/2026): CHỈ Sale Admin phòng Đoàn tạo / hủy link thanh toán; máy chủ chặn lại lần nữa.
  const laSA = user?.role === "sales_admin";
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

  // VPM-9 · CỬA LỊCH THANH TOÁN.
  //
  // Một hợp đồng khách đoàn hiếm khi trả một lần: ký đặt cọc, trả tiếp trước khởi hành, thanh toán nốt
  // sau tour. Máy chủ đã có đủ – bảng đợt, mốc hạn theo ngày ký / trước – sau khởi hành, phép rải tiền
  // thu vào từng đợt, cửa dời hạn có lý do. Màn hình thì trước 11/9/2026 KHÔNG có nút nào, nên cả phân
  // hệ ấy chỉ sống trong mã và Kinh doanh vẫn ghi hạn thanh toán vào một ô văn bản duy nhất.
  const [lich, setLich] = useState<Record<number, any>>({});
  const [soan, setSoan] = useState<{ hd: HD; dot: any[] } | null>(null);

  const xemLich = async (h: HD) => {
    if (lich[h.id]) { setLich({ ...lich, [h.id]: null }); return; }
    try { setLich({ ...lich, [h.id]: await api<any>(`/ban-hang/hop-dong/${h.id}/lich-thanh-toan`) }); taiLink(h.id); }
    catch (e) { toast(errMsg(e), true); }
  };

  // TR-1d · LINK THANH TOÁN TOUR ĐOÀN (Chủ tịch duyệt bản xem thử 02/11/2026). Mỗi đợt một link; số tiền MÁY lấy
  // (báo giá khách đã chốt → hợp đồng → phần còn thiếu của đợt), hạn = hạn đợt, khách chỉ chuyển khoản (không thẻ).
  const [lk, setLk] = useState<Record<number, any>>({});
  const [taoL, setTaoL] = useState<{ hid: number; d: any; email: string; dien_thoai: string } | null>(null);
  const taiLink = async (hid: number) => {
    try { const r = await api<any>(`/ban-hang/hop-dong/${hid}/link-thanh-toan`); setLk((x) => ({ ...x, [hid]: r })); }
    catch { /* không có quyền xem link thì bảng lịch vẫn hiện */ }
  };
  const linkCuaDot = (hid: number, did: number) =>
    (lk[hid]?.link || []).find((l: any) => l.lich_id === did && (l.trang_thai === "mo" || l.trang_thai === "da_tra"));
  const lamMoi = async (hid: number) => {
    setLich((x) => ({ ...x, [hid]: null }));
    try { const b = await api<any>(`/ban-hang/hop-dong/${hid}/lich-thanh-toan`); setLich((x) => ({ ...x, [hid]: b })); } catch { /* bỏ qua */ }
    await taiLink(hid);
  };
  const taoLink = async (guiEmail: boolean) => {
    if (!taoL) return;
    const lich_id = taoL.d.id;
    setDang(true);
    try {
      const r = await api<any>("/ban-hang/link-thanh-toan",
        { method: "POST", json: { lich_id, email: taoL.email, dien_thoai: taoL.dien_thoai, gui_email: guiEmail } });
      toast(`Đã tạo link ${r.ma}` + (guiEmail && r.email_link_luc ? ` và gửi tới ${r.email}` : ""));
      const hid = taoL.hid; setTaoL(null); await lamMoi(hid);
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };
  const chepLink = async (l: any) => {
    try { await navigator.clipboard.writeText(l.link); toast("Đã chép link — dán gửi khách qua Zalo / email"); }
    catch { window.prompt("Chép link này gửi khách:", l.link); }
  };
  const guiLaiLink = async (hid: number, l: any) => {
    try { await api<any>(`/ban-hang/link-thanh-toan/${l.ma}/gui-lai`, { method: "POST" }); toast(`Đã gửi lại email tới ${l.email}`); await taiLink(hid); }
    catch (e) { toast(errMsg(e), true); }
  };
  const huyLink = async (hid: number, l: any) => {
    const ly_do = (window.prompt(`Hủy link ${l.ma}? Ghi lý do (bắt buộc):`) || "").trim();
    if (!ly_do) return;
    try { await api<any>(`/ban-hang/link-thanh-toan/${l.ma}/huy`, { method: "POST", json: { ly_do } }); toast(`Đã hủy link ${l.ma}`); await taiLink(hid); }
    catch (e) { toast(errMsg(e), true); }
  };

  // Mở bảng soạn với lịch đang có; chưa có thì gợi hai đợt theo lối phổ biến nhất – cọc khi ký, nốt
  // trước khởi hành. Gợi ý chỉ là chỗ bắt đầu: người soạn sửa lại, và MÁY CHỦ mới là chỗ kiểm tổng
  // các đợt có khớp giá trị hợp đồng hay không.
  const moSoan = (h: HD) => {
    const dang = lich[h.id]?.dot || [];
    setSoan({ hd: h, dot: dang.length ? dang.map((d: any) => ({
      ten: d.ten, so_tien: d.so_tien, moc: d.moc, moc_so_ngay: d.moc_so_ngay ?? "", han: d.han || "", ghi_chu: d.ghi_chu || "" })) : [
      { ten: "Đặt cọc khi ký", so_tien: Math.round((h.dat_coc || h.gia_tri * 0.3)), moc: "ngay_ky", moc_so_ngay: 0, han: "", ghi_chu: "" },
      { ten: "Thanh toán nốt", so_tien: Math.round(h.gia_tri - (h.dat_coc || h.gia_tri * 0.3)), moc: "truoc_khoi_hanh", moc_so_ngay: 7, han: "", ghi_chu: "" },
    ] });
  };

  const datLich = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!soan) return;
    const dot = soan.dot.map((d, i) => ({
      ten: d.ten || `Đợt ${i + 1}`, so_tien: Number(d.so_tien) || 0, moc: d.moc,
      moc_so_ngay: d.moc === "co_dinh" ? null : Number(d.moc_so_ngay || 0),
      han: d.moc === "co_dinh" ? (d.han || null) : null, ghi_chu: d.ghi_chu || "",
    }));
    setDang(true);
    try {
      const r = await api<any>(`/ban-hang/hop-dong/${soan.hd.id}/lich-thanh-toan`,
        { method: "POST", json: { phien_ban: soan.hd.phien_ban, dot } });
      toast(r.message || "Đã đặt lịch thanh toán");
      setSoan(null); setLich({ ...lich, [soan.hd.id]: null }); await load();
    } catch (e2) { toast(errMsg(e2), true); }
    setDang(false);
  };

  // Dời hạn một đợt. Hạn GỐC được giữ lại ở máy chủ, nên về sau vẫn đọc được đợt này đã dời mấy lần
  // và vì sao – đó là điểm khác giữa "dời hạn" và "sửa cho khớp".
  const doiHan = async (hid: number, d: any) => {
    const han = (window.prompt(`Dời hạn đợt "${d.ten}" (${vnd(d.so_tien)}) sang ngày nào?\nDạng 2026-10-15`, d.han || "") || "").trim();
    if (!han) return;
    const ly_do = (window.prompt("Lý do dời hạn (bắt buộc – sẽ lưu cùng hạn gốc):") || "").trim();
    if (!ly_do) { toast("Phải ghi lý do dời hạn.", true); return; }
    try {
      const r = await api<any>(`/ban-hang/hop-dong/lich-thanh-toan/${d.id}/doi-han`, { method: "POST", json: { han, ly_do } });
      toast(r.message || "Đã dời hạn");
      setLich({ ...lich, [hid]: await api<any>(`/ban-hang/hop-dong/${hid}/lich-thanh-toan`) });
    } catch (e3) { toast(errMsg(e3), true); }
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
                      <button className="ghost" onClick={() => xemLich(h)}>Lịch thanh toán</button>
                      <button className="ghost" onClick={() => xemChuoi(h.id)}>Trọn đường</button>
                    </td>
                  </tr>
                  {lich[h.id] ? (
                    <tr key={`${h.id}-lich`}><td colSpan={9} className="chitiet">
                      <div className="dong-tieu-de">
                        <b>Lịch thanh toán – {lich[h.id].dot.length} đợt</b>
                        <button className="ghost" onClick={() => moSoan(h)}>
                          {lich[h.id].dot.length ? "Sửa lịch" : "Đặt lịch"}</button>
                      </div>
                      {lich[h.id].khop_gia_tri === false ? (
                        <p className="warn">Tổng các đợt <b>{vnd(lich[h.id].tong_cac_dot)}</b> không khớp
                          giá trị hợp đồng <b>{vnd(lich[h.id].gia_tri)}</b> — một trong hai con số đang sai,
                          và cái sai ấy chỉ lộ ra lúc đối chiếu doanh thu.</p>) : null}
                      {lich[h.id].dot.length === 0 ? (
                        <p className="muted">Chưa đặt lịch. Hợp đồng không có lịch thì hạn thanh toán chỉ
                          nằm trong một ô văn bản, và không ai đòi được theo đợt.</p>) : (
                        <table className="tbl">
                          <thead><tr><th>Đợt</th><th>Hạn</th>
                            <th style={{ textAlign: "right" }}>Số tiền</th>
                            <th style={{ textAlign: "right" }}>Đã rải</th>
                            <th style={{ textAlign: "right" }}>Còn thiếu</th>
                            <th>Trạng thái</th><th>Link thanh toán</th><th></th></tr></thead>
                          <tbody>{lich[h.id].dot.map((d: any) => (
                            <tr key={d.id}>
                              <td>{d.dot}. {d.ten}<div className="muted small">{d.moc_mo_ta}
                                {d.moc !== "co_dinh" && d.moc_so_ngay != null ? ` ${d.moc_so_ngay} ngày` : ""}</div></td>
                              <td>{d.han || "–"}{d.da_doi_han ? <div className="muted small">gốc {d.han_goc}</div> : null}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.so_tien)}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.da_rai)}</td>
                              <td style={{ textAlign: "right" }}>{d.con_thieu > 0 ? <b>{vnd(d.con_thieu)}</b> : "–"}</td>
                              <td><Tag cls={d.trang_thai === "da_du" ? "ok" : d.qua_han ? "red" : "warn"}>
                                {d.trang_thai === "da_du" ? "đã đủ" : d.qua_han ? "quá hạn" : "chờ đến hạn"}</Tag></td>
                              <td className="nut">{(() => {
                                const l = linkCuaDot(h.id, d.id);
                                if (l) return (<>
                                  <Tag cls={l.trang_thai === "da_tra" ? "ok" : "warn"}>{l.trang_thai_ten}</Tag>{" "}
                                  <span className="mono small">{l.ma} · {vnd(l.so_tien)}</span>
                                  {l.trang_thai === "mo" ? <div className="muted small">hết hạn {l.han}{l.email_link_luc ? ` · đã gửi ${l.email}` : ""}</div> : null}
                                  {l.email_loi ? <div className="warn small">Email lỗi: {l.email_loi}</div> : null}
                                  <div>
                                    {l.trang_thai === "mo" ? <button className="ghost" onClick={() => chepLink(l)}>Chép link</button> : null}
                                    {laSA && l.email ? <button className="ghost" onClick={() => guiLaiLink(h.id, l)}>
                                      {l.trang_thai === "da_tra" ? "Gửi lại hóa đơn" : "Gửi lại email"}</button> : null}
                                    {laSA && l.trang_thai === "mo" ? <button className="ghost" onClick={() => huyLink(h.id, l)}>Hủy link</button> : null}
                                  </div></>);
                                if (!laSA || d.con_thieu <= 0) return <span className="muted small">–</span>;
                                if (lk[h.id] && !lk[h.id].tt_chung) return <span className="muted small">công tắc thanh toán chung đang tắt</span>;
                                return <button onClick={() => setTaoL({ hid: h.id, d, email: "", dien_thoai: "" })}>Tạo link thanh toán</button>;
                              })()}</td>
                              <td className="nut"><button className="ghost" onClick={() => doiHan(h.id, d)}>Dời hạn</button></td>
                            </tr>))}</tbody>
                        </table>)}
                      <p className="muted small">{lich[h.id].ghi_chu_man_hinh}</p>
                      {lich[h.id].chua_gan_dot > 0 ? (
                        <p className="muted small">Còn <b>{vnd(lich[h.id].chua_gan_dot)}</b> đã thu chưa rải
                          vào đợt nào.</p>) : null}
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

      {taoL ? (
        <form className="card" onSubmit={(e) => { e.preventDefault(); taoLink(true); }}>
          <h3>Tạo link thanh toán · đợt {taoL.d.dot}. {taoL.d.ten}</h3>
          <p>Số tiền <b>{vnd(taoL.d.con_thieu)}</b> — phần còn thiếu của đợt, máy lấy từ hợp đồng (báo giá khách đã chốt), không sửa ở đây.
            Hạn link <b>{taoL.d.han || "–"}</b> (hạn của đợt). Khách chỉ chuyển khoản — QR hoặc chuyển tay, không thẻ.</p>
          <label>Email nhận link <input id="ttd-email" type="email" value={taoL.email} placeholder="để trống: lấy email trên báo giá / booking"
            onChange={(e) => setTaoL({ ...taoL, email: e.target.value })} /></label>
          <label>Điện thoại (để Zalo) <input id="ttd-dt" value={taoL.dien_thoai} placeholder="để trống: lấy trên báo giá / booking"
            onChange={(e) => setTaoL({ ...taoL, dien_thoai: e.target.value })} /></label>
          <div className="nut">
            <button type="submit" disabled={dang}>Tạo và gửi email</button>
            <button type="button" className="ghost" disabled={dang} onClick={() => taoLink(false)}>Chỉ tạo, tự gửi Zalo</button>
            <button type="button" className="ghost" onClick={() => setTaoL(null)}>Thôi</button>
          </div>
        </form>) : null}
      {soan ? (
        <form className="card" onSubmit={datLich}>
          <h3>Lịch thanh toán – {soan.hd.so_hop_dong} · giá trị {vnd(soan.hd.gia_tri)}</h3>
          <p className="muted small">
            Tổng các đợt phải khớp giá trị hợp đồng — máy chủ kiểm và từ chối nếu lệch. Mốc “trước / sau
            khởi hành” tự tính hạn theo ngày khởi hành của tour, nên đổi ngày khởi hành thì hạn đi theo;
            chọn “ngày cố định” thì hạn đứng yên dù tour dời.
          </p>
          <table className="tbl">
            <thead><tr><th>Tên đợt</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Mốc</th>
              <th>Số ngày</th><th>Ngày cố định</th><th>Ghi chú</th><th></th></tr></thead>
            <tbody>{soan.dot.map((d, i) => {
              const sua = (k: string, v: any) => setSoan({ ...soan, dot: soan.dot.map((x, j) => j === i ? { ...x, [k]: v } : x) });
              return (<tr key={i}>
                <td><input value={d.ten} onChange={(e) => sua("ten", e.target.value)} placeholder={`Đợt ${i + 1}`} /></td>
                <td><input type="number" min={0} step={1000} value={d.so_tien} onChange={(e) => sua("so_tien", e.target.value)} style={{ textAlign: "right" }} /></td>
                <td><select value={d.moc} onChange={(e) => sua("moc", e.target.value)}>
                  <option value="ngay_ky">sau ngày ký hợp đồng</option>
                  <option value="truoc_khoi_hanh">trước ngày khởi hành</option>
                  <option value="sau_khoi_hanh">sau ngày khởi hành</option>
                  <option value="co_dinh">ngày cố định do người nhập</option>
                </select></td>
                <td>{d.moc === "co_dinh" ? <span className="muted">–</span>
                  : <input type="number" min={0} value={d.moc_so_ngay} onChange={(e) => sua("moc_so_ngay", e.target.value)} style={{ width: 70 }} />}</td>
                <td>{d.moc === "co_dinh"
                  ? <input type="date" value={d.han} onChange={(e) => sua("han", e.target.value)} />
                  : <span className="muted">–</span>}</td>
                <td><input value={d.ghi_chu} onChange={(e) => sua("ghi_chu", e.target.value)} /></td>
                <td className="nut"><button type="button" className="ghost"
                  onClick={() => setSoan({ ...soan, dot: soan.dot.filter((_, j) => j !== i) })}>xoá</button></td>
              </tr>);
            })}</tbody>
          </table>
          <p className="muted small">
            Tổng các đợt đang là <b>{vnd(soan.dot.reduce((t, d) => t + (Number(d.so_tien) || 0), 0))}</b>
            {" "}/ giá trị hợp đồng <b>{vnd(soan.hd.gia_tri)}</b>.
          </p>
          <button type="button" className="ghost" onClick={() => setSoan({ ...soan, dot: [...soan.dot,
            { ten: "", so_tien: 0, moc: "truoc_khoi_hanh", moc_so_ngay: 0, han: "", ghi_chu: "" }] })}>Thêm đợt</button>
          {" "}<button type="submit" className="ghost" disabled={dang}>Lưu lịch</button>
          {" "}<button type="button" className="ghost" onClick={() => setSoan(null)}>Đóng</button>
        </form>) : null}

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1250px; }
        .card { border: 1px solid var(--vtos-line); border-radius: 10px; padding: 14px; margin: 14px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid var(--vtos-line); padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .chitiet { background: var(--vtos-info-bg); }
        .buoc { display: flex; gap: 10px; flex-wrap: wrap; margin: 6px 0 10px; }
        .o { border: 1px solid var(--vtos-line); border-radius: 8px; padding: 8px 10px; min-width: 150px; }
        .o.thieu { border-style: dashed; color: var(--vtos-warning); background: var(--vtos-warning-bg); }
        .o .ten { font-size: 12px; color: var(--vtos-text-mute); }
        .o .gt { font-weight: 600; font-size: 13px; }
        .nut { white-space: nowrap; }
        .dong-tieu-de { display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }
        input, select { padding: 4px 6px; border-radius: 6px; border: 1px solid var(--vtos-line);
                        font-size: 13px; max-width: 100%; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid var(--vtos-line);
                 background: var(--vtos-card); color: var(--vtos-text); cursor: pointer; font-size: 13px; }
        .muted { color: var(--vtos-text-mute); }
        .small { font-size: 12px; }
        .warn { color: var(--vtos-warning); background: var(--vtos-warning-bg); padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><HopDong /></Shell>; }
