"use client";
/** TR-1 · TOUR TRÊN CỔNG KHÁCH (Chủ tịch duyệt 01–02/11/2026).
 *  Ảnh, lịch trình, bảng giá, bao gồm / không bao gồm, quy định KHÔNG nhập ở đây: máy đọc thẳng từ trang tour trên
 *  vietourist.com.vn (chỉ đọc, không sửa web). Ở đây chỉ:
 *   · Ghép: tour trên web ↔ sản phẩm crm (máy gợi ý theo tên + số ngày, TP Điều hành / TP-GĐ Kinh doanh xác nhận).
 *   · Hồ sơ cổng: điểm đến, 3–5 điểm nổi bật, Wellness & retreat, phương tiện (Điều hành / Marketing).
 *   · Công tắc thanh toán: chung (Chủ tịch / TGĐ) + từng sản phẩm. Đóng → khách chỉ «Gửi yêu cầu giữ chỗ».
 *   · Đơn đặt online + yêu cầu hóa đơn GTGT công ty (Kế toán đánh dấu đã xuất).
 *  Ma trận quản lý do máy chủ trả về (ma_tran) — màn chỉ hiện, không tự quyết quyền. */
import { useEffect, useMemo, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const luc = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");
const VAI: Record<string, string> = { chutich: "Chủ tịch", tgd: "TGĐ", bks: "BKS", nv_dh: "NV Điều hành", tp_dh: "TP Điều hành", nv_kd: "NV KD",
  tn_kd: "TN KD", tp_kd: "TP KD", gd_kd: "GĐ KD", sales_admin: "Sales admin", nv_mkt: "NV Marketing", ptgd_mkt: "PTGĐ Marketing", ketoan: "Kế toán", robot_ks: "Robot Kiểm soát (chỉ đọc)" };

function Trang() {
  const { toast } = useShell();
  const [x, setX] = useState<any>(null);
  const [tab, setTab] = useState<"sp" | "web" | "don" | "mt">("sp");
  const [tim, setTim] = useState(""); const [loc, setLoc] = useState("");
  const [locLo, setLocLo] = useState<"co_chuyen" | "tat_ca">("co_chuyen");   // TR-6b · phạm vi bật / đóng hàng loạt
  // TR-9 (13/11/2026): hai ô nhập NGAY TRÊN TRANG, thay cho hộp thoại của trình duyệt.
  // `window.prompt` / `window.confirm` CHẶN mọi thao tác tự động (trợ lý không bấm qua được) và
  // trên điện thoại thì hộp thoại hệ thống rất khó thao tác. Báo cáo 13/11: người đi ghép link
  // cho 22 tour thiếu ảnh bị kẹt đúng ở đây, không ghép được tour nào.
  const [ghep, setGhep] = useState<any>(null);      // ghép link web ↔ sản phẩm
  const [xacNhan, setXacNhan] = useState<any>(null); // xác nhận bật / đóng hàng loạt
  // TR-8 (13/11/2026) · album ảnh tour. Đo cùng ngày: 13/85 tour trên cổng không có tấm ảnh nào,
  // 22/33 tour đang mở bán thiếu ảnh. Nội dung đọc từ web cũ nên chỗ này chỉ vá được bằng cửa tải.
  const [alb, setAlb] = useState<any>(null);         // album đang mở
  const [lo, setLo] = useState<any>({ nhom: "diem_den", can_cu: "vtd_chup", chu_thich: "", credit: "", can_cu_ghi_chu: "" });
  const [dangTai, setDangTai] = useState("");
  const moAlbum = async (pid: number) => { try { setAlb(await api(`/tour-online/${pid}/album`)); } catch (e) { toast(errMsg(e), true); } };
  const taiLaiAlbum = async () => { if (alb) setAlb(await api(`/tour-online/${alb.san_pham.id}/album`)); };
  const [sua, setSua] = useState<any>(null);
  const [web, setWeb] = useState<any[] | null>(null);
  const [don, setDon] = useState<any[] | null>(null); const [chiVat, setChiVat] = useState(false);
  const [busy, setBusy] = useState(false);
  const tai = () => api("/tour-online").then(setX).catch((e) => toast(errMsg(e), true));
  useEffect(() => { tai(); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (tab === "don" && x?.duoc?.don) api(`/tour-online/don?chi_vat=${chiVat}`).then((r) => setDon(r.don)).catch((e) => toast(errMsg(e), true)); }, [tab, chiVat]);  // eslint-disable-line react-hooks/exhaustive-deps
  const lam = async (f: () => Promise<any>) => { setBusy(true); try { const r = await f(); if (r?.message) toast(r.message); await tai(); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); } };
  const taiWeb = async () => { setBusy(true); setWeb(null); try { setWeb((await api("/tour-online/web")).web); } catch (e) { toast(errMsg(e), true); setWeb([]); } finally { setBusy(false); } };

  const sps: any[] = x?.san_pham || [];
  const ds = useMemo(() => {
    const k = tim.trim().toLowerCase();
    return sps.filter((p) => (!k || `${p.ma} ${p.ten} ${p.diem_den_suy}`.toLowerCase().includes(k))
      && (!loc || (loc === "chua_ghep" ? !p.link_web : loc === "loi" ? !!p.web.loi : loc === "mo_tt" ? p.mo_thanh_toan : loc === "co_chuyen" ? p.so_chuyen > 0 : loc === "thieu" ? (p.thieu || []).length > 0 : true)));
  }, [sps, tim, loc]);
  // TR-6b · số sản phẩm mỗi phạm vi hàng loạt sẽ xét — in ra nút để người bấm biết mình đang đổi bao nhiêu.
  // Máy chủ TỰ đếm lại khi nhận lệnh; con số này chỉ để xem trước, không phải con số quyết định.
  const soLo = useMemo(() => ({ tat_ca: sps.length, co_chuyen: sps.filter((p) => p.so_chuyen > 0).length }), [sps]);
  if (!x) return <p>Đang tải…</p>;
  const duoc = x.duoc || {};

  return (<>
    <h1>Tour trên cổng khách</h1>
    <p className="muted">Ảnh, lịch trình, bảng giá, bao gồm / không bao gồm và quy định đọc thẳng từ trang tour trên vietourist.com.vn (chỉ đọc, không sửa web) — không nhập lại ở đây.
      Ở đây: ghép tour web ↔ sản phẩm, hồ sơ cổng, công tắc thanh toán, đơn đặt online. Khách đặt tại kh.vietourist.vn/tours.</p>
    <div className="panel" style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
      <b>Thanh toán trực tuyến tour (chung):</b>
      {x.tt_chung ? <Tag cls="ok">Đang mở</Tag> : <Tag cls="grey">Đang đóng — khách chỉ gửi yêu cầu giữ chỗ</Tag>}
      {duoc.tt_chung && <button className="act grey" disabled={busy} onClick={() => lam(() => api("/tour-online/thanh-toan-chung", { method: "POST", json: { bat: !x.tt_chung } }))}>
        {x.tt_chung ? "Đóng thanh toán chung" : "Mở thanh toán chung"}</button>}
      <span className="muted" style={{ fontSize: 13 }}>Khách đặt online được khi công tắc chung VÀ công tắc của sản phẩm cùng mở.</span>
    </div>
    <div style={{ display: "flex", gap: 6, margin: "8px 0", flexWrap: "wrap" }}>{([["sp", `Sản phẩm (${sps.length})`], ...(duoc.sua || duoc.ghep ? [["web", "Tour trên web · ghép"]] : []),
      ...(duoc.don ? [["don", "Đơn đặt online"]] : []), ["mt", "Ma trận quản lý"]] as [typeof tab, string][]).map(([k, t]) =>
      <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} aria-pressed={tab === k} onClick={() => setTab(k)}>{t}</button>)}</div>

    {tab === "sp" && <div className="panel">
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 10 }}>
        <input placeholder="Mã, tên, điểm đến…" value={tim} onChange={(e) => setTim(e.target.value)} style={{ minWidth: 220 }} />
        <select value={loc} onChange={(e) => setLoc(e.target.value)}><option value="">Tất cả</option><option value="co_chuyen">Có chuyến mở bán</option>
          <option value="chua_ghep">Chưa ghép web</option><option value="loi">Đọc web lỗi</option><option value="mo_tt">Đang mở thanh toán</option>
          <option value="thieu">Thiếu nội dung ({sps.filter((p) => (p.thieu || []).length > 0).length})</option></select>
        <span className="muted">{ds.length} sản phẩm</span></div>
      {/* TR-6b (13/11/2026) · BẬT / ĐÓNG HÀNG LOẠT — một lần bấm, MỘT giao dịch trên máy chủ.
          Vì sao có khối này: bấm từng sản phẩm 380 lượt đã làm VTOS mất API hai lần đêm 13/11/2026.
          Chỉ Chủ tịch / TGĐ thấy (`duoc.tt_chung`) — bằng đúng quyền của công tắc chung, vì mở cả kho
          là quyết định kinh doanh, không phải việc thường ngày như mở một tour. */}
      {duoc.tt_chung && <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10,
        padding: "8px 10px", borderRadius: 8, border: "1px solid var(--vien, #d7dce6)" }}>
        <b>Bật / đóng hàng loạt:</b>
        <select value={locLo} onChange={(e) => setLocLo(e.target.value as typeof locLo)} aria-label="Phạm vi bật / đóng hàng loạt">
          <option value="co_chuyen">Chỉ sản phẩm có chuyến đang mở bán ({soLo.co_chuyen})</option>
          <option value="tat_ca">Tất cả sản phẩm đang hoạt động ({soLo.tat_ca})</option></select>
        {([[true, "Mở thanh toán"], [false, "Đóng thanh toán"]] as [boolean, string][]).map(([bat, nhan]) =>
          <button key={nhan} className={`act ${bat ? "teal" : "grey"}`} disabled={busy}
            onClick={() => setXacNhan({ bat, nhan, loc: locLo, so: soLo[locLo] })}>{nhan}</button>)}
        <span className="muted" style={{ fontSize: 13 }}>Máy báo lại số sản phẩm THỰC SỰ đổi. Bấm lần hai ra 0 nghĩa là lần đầu đã ăn.
          Khách vẫn cần công tắc chung ở trên cùng mở.</span>
        {/* TR-9: hỏi lại NGAY TRÊN TRANG, không dùng hộp thoại trình duyệt. */}
        {xacNhan && <div style={{ flexBasis: "100%", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap",
          padding: "10px 12px", borderRadius: 8, border: "2px solid var(--accent, #14538D)" }}>
          <b>{xacNhan.nhan} trực tuyến cho {xacNhan.so} sản phẩm ({xacNhan.loc === "co_chuyen" ? "có chuyến đang mở bán" : "tất cả đang hoạt động"})?</b>
          <button className="act teal" disabled={busy} onClick={() => { const x = xacNhan; setXacNhan(null);
            lam(() => api("/tour-online/thanh-toan-hang-loat", { method: "POST", json: { bat: x.bat, loc: x.loc } })); }}>Đồng ý, {xacNhan.nhan.toLowerCase()}</button>
          <button className="act grey" onClick={() => setXacNhan(null)}>Hủy</button></div>}</div>}
      <div className="wrap"><table><thead><tr><th>Sản phẩm</th><th>Loại</th><th>Chuyến</th><th>Nội dung web</th><th>Nội dung trên cổng</th><th>Hồ sơ cổng</th><th>Thanh toán</th><th /></tr></thead>
        <tbody>{ds.map((p) => <tr key={p.id}>
          <td><b>{p.ma}</b><br />{p.ten}</td>
          <td>{p.loai === "doan" ? "Đoàn riêng" : "Ghép"} · {p.nuoc_ngoai ? "Nước ngoài" : "Trong nước"}</td>
          <td>{p.so_chuyen}</td>
          <td style={{ maxWidth: 260 }}>{p.link_web ? <>
            <a href={p.link_web} target="_blank" rel="noopener noreferrer">{p.web.ten || "Trang tour"}</a><br />
            <small className="muted">{p.web.so_anh} ảnh · {p.web.so_ngay} ngày · {p.web.so_bao_gom} mục bao gồm · {luc(p.web.cap_nhat_luc)}</small>
            {p.web.loi && <><br /><Tag cls="red">Lỗi: {p.web.loi}</Tag></>}</> : <span className="muted">Chưa ghép</span>}</td>
          <td style={{ maxWidth: 280 }}><NoiDungCong p={p} ten={x.thieu_nd || {}} /></td>
          <td><small>{p.diem_den || <i className="muted">{p.diem_den_suy} (máy suy)</i>}{p.wellness ? " · Wellness" : ""}<br />
            {(p.phuong_tien_ds.length ? p.phuong_tien_ds : p.phuong_tien_suy).map((k: string) => x.phuong_tien[k]).join(", ")}
            {p.noi_bat.length ? ` · ${p.noi_bat.length} điểm nổi bật` : ""}</small></td>
          <td>{p.mo_thanh_toan ? <Tag cls="ok">Mở</Tag> : <Tag cls="grey">Đóng</Tag>}
            {duoc.ghep && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-online/${p.id}/thanh-toan`, { method: "POST", json: { bat: !p.mo_thanh_toan } }))}>{p.mo_thanh_toan ? "Đóng" : "Mở"}</button>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{duoc.sua && <button className="act grey" onClick={() => setSua({ id: p.id, ma: p.ma, diem_den: p.diem_den, noi_bat: p.noi_bat.join("\n"), wellness: p.wellness, phuong_tien_ds: p.phuong_tien_ds })}>Sửa hồ sơ</button>}
            {duoc.sua && p.link_web && <button className="act grey" disabled={busy} onClick={() => lam(() => api(`/tour-online/${p.id}/doc-web`, { method: "POST" }))}>Đọc lại web</button>}
            {duoc.ghep && <button className="act grey" disabled={busy} onClick={() => setGhep({ id: p.id, ma: p.ma, ten: p.ten, link: p.link_web || "" })}>{p.link_web ? "Sửa link" : "Ghép link"}</button>}
            {/* TR-8: ảnh tải lên đứng TRƯỚC ảnh đọc từ web — số trên nút là ảnh ĐÃ TẢI, không gồm ảnh web. */}
            <button className={`act ${p.so_anh_tai ? "teal" : "grey"}`} onClick={() => moAlbum(p.id)}>Ảnh{p.so_anh_tai ? ` (${p.so_anh_tai})` : ""}</button></td>
        </tr>)}</tbody></table></div>
    </div>}

    {/* TR-8 (13/11/2026) · ALBUM ẢNH TOUR.
        Ảnh tải lên ĐỨNG TRƯỚC ảnh đọc từ vietourist.com.vn, không xoá ảnh web nào — vá được tour
        nào hay tour ấy. Tải là HIỆN NGAY, không có bước duyệt (KS-16c 31/10, nhắc lại 13/11).
        Gửi TỪNG TỆP một để báo được tiến độ và thử lại đúng tấm hỏng. */}
    {alb && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <h3 style={{ margin: 0 }}>Ảnh tour · {alb.san_pham.ma}</h3>
        <button className="act grey" onClick={() => setAlb(null)}>Đóng</button></div>
      <span className="muted">{alb.san_pham.ten}</span>
      <span className="muted" style={{ fontSize: 13 }}>Đã tải <b>{alb.tong}</b>/{alb.toi_da} ảnh
        · đọc từ web {alb.so_anh_web} ảnh · <b>ảnh tải lên hiện trước ảnh web trên cổng khách</b>.
        Mỗi tệp tối đa {alb.toi_da_mb} MB, nhận JPG / PNG / WEBP. Máy tự thu nhỏ và <b>xoá dữ liệu
        vị trí GPS</b> trong ảnh trước khi đưa ra ngoài.</span>

      {alb.duoc_tai && <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end",
        padding: "10px 12px", borderRadius: 8, border: "1px solid var(--vien, #d7dce6)", margin: "10px 0" }}>
        <label>Nhóm ảnh<select value={lo.nhom} onChange={(e) => setLo({ ...lo, nhom: e.target.value })}>
          {Object.entries(alb.nhom_anh).map(([k, t]) => <option key={k} value={k}>{t as string}</option>)}</select></label>
        <label>Căn cứ quyền dùng<select value={lo.can_cu} onChange={(e) => setLo({ ...lo, can_cu: e.target.value })}>
          {Object.entries(alb.can_cu_anh).map(([k, t]) => <option key={k} value={k}>{t as string}</option>)}</select></label>
        <label style={{ flex: 1, minWidth: 180 }}>Chú thích (không bắt buộc)
          <input value={lo.chu_thich} onChange={(e) => setLo({ ...lo, chu_thich: e.target.value })} /></label>
        <label style={{ minWidth: 150 }}>Ghi công (nếu có)
          <input value={lo.credit} onChange={(e) => setLo({ ...lo, credit: e.target.value })} /></label>
        <label className="act teal" style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", minHeight: 44, padding: "0 16px" }}>
          {dangTai || "Chọn ảnh để tải lên"}
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple style={{ display: "none" }}
            onChange={async (e) => {
              const fs = Array.from(e.target.files || []); e.target.value = "";
              let ok = 0, bo = 0;
              for (let i = 0; i < fs.length; i++) {
                setDangTai(`Đang tải ${i + 1}/${fs.length}…`);
                const fd = new FormData();
                fd.append("tep", fs[i]); fd.append("nhom", lo.nhom); fd.append("can_cu", lo.can_cu);
                fd.append("chu_thich", lo.chu_thich); fd.append("credit", lo.credit);
                fd.append("can_cu_ghi_chu", lo.can_cu_ghi_chu); fd.append("mo_ta_thay_the", "");
                try { const r = await api<any>(`/tour-online/${alb.san_pham.id}/anh`, { method: "POST", body: fd }); r.moi ? ok++ : bo++; }
                catch (ex) { toast(`${fs[i].name}: ${errMsg(ex)}`, true); }
              }
              setDangTai("");
              toast(`Đã tải ${ok} ảnh${bo ? `, bỏ qua ${bo} ảnh trùng` : ""}`);
              await taiLaiAlbum(); await tai();
            }} /></label>
        <span className="muted" style={{ fontSize: 12, flexBasis: "100%" }}>Chọn được nhiều tệp một lần — máy gửi lần lượt từng tấm
          và báo đúng tấm nào hỏng. Ảnh trùng nội dung không tạo bản mới.</span></div>}

      {!alb.anh.length ? <p className="muted">Chưa có ảnh nào tải lên. Cổng khách đang dùng {alb.so_anh_web} ảnh đọc từ web.</p>
        : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(190px,1fr))", gap: 12 }}>
          {alb.anh.map((x: any, i: number) => <div key={x.id} style={{ border: "1px solid var(--vien, #d7dce6)", borderRadius: 8, overflow: "hidden",
            opacity: x.trang_thai === "an" ? 0.5 : 1 }}>
            <img src={x.nho} alt={x.mo_ta_thay_the || x.chu_thich || `Ảnh ${i + 1} của ${alb.san_pham.ma}`}
              style={{ width: "100%", aspectRatio: "16/9", objectFit: "cover", display: "block", background: "#eef2f5" }} />
            <div style={{ padding: "6px 8px", display: "flex", flexDirection: "column", gap: 4 }}>
              <small>{i === 0 ? <b>Ảnh bìa · </b> : null}{x.nhom_ten}{x.trang_thai === "an" ? " · ĐANG ẨN" : ""}</small>
              <small className="muted">{x.can_cu_ten}{x.credit ? ` · ${x.credit}` : ""}</small>
              <small className="muted">{x.rong}×{x.cao} · {x.tai_boi} · {x.tai_luc}</small>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                {i > 0 && <button className="act grey" onClick={() => lam(async () => {
                  const ids = alb.anh.map((y: any) => y.id); [ids[i - 1], ids[i]] = [ids[i], ids[i - 1]];
                  const r = await api(`/tour-online/${alb.san_pham.id}/anh/xep`, { method: "POST", json: { ids } });
                  await taiLaiAlbum(); return r; })}>↑ Lên</button>}
                <button className="act grey" onClick={() => lam(async () => {
                  const r = await api(`/tour-online/anh/${x.id}/an`, { method: "POST", json: { an: x.trang_thai !== "an" } });
                  await taiLaiAlbum(); return r; })}>{x.trang_thai === "an" ? "Cho hiện lại" : "Gỡ khỏi cổng"}</button>
                <button className="act grey" onClick={() => setAlb({ ...alb, xoa: x.id })}>Xoá</button></div>
              {alb.xoa === x.id && <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                <small><b>Xoá hẳn ảnh này?</b></small>
                <button className="act teal" onClick={() => lam(async () => {
                  const r = await api(`/tour-online/anh/${x.id}`, { method: "DELETE" });
                  await taiLaiAlbum(); await tai(); return r; })}>Xoá</button>
                <button className="act grey" onClick={() => setAlb({ ...alb, xoa: null })}>Thôi</button></div>}
            </div></div>)}
        </div>}
    </div>}

    {/* TR-9 (13/11/2026) · GHÉP LINK WEB — BIỂU MẪU TRÊN TRANG, KHÔNG DÙNG HỘP THOẠI.
        Trước đây ô này là `window.prompt`. Hộp thoại của trình duyệt khoá cả trang: trợ lý không
        bấm qua được, và trên điện thoại thì không dán link dài vào nổi. Báo cáo 13/11/2026: người
        đi ghép link cho 22 tour thiếu ảnh kẹt đúng ở đây và không ghép được tour nào.
        Biểu mẫu này đặt cạnh «Hồ sơ cổng» — cùng một chỗ, cùng một kiểu, mỗi nút vẫn một chỗ. */}
    {ghep && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
      <h3 style={{ marginTop: 0 }}>Ghép link web · {ghep.ma}</h3>
      <span className="muted">{ghep.ten}</span>
      <label>Link trang tour trên vietourist.com.vn
        <input value={ghep.link} autoFocus placeholder="https://vietourist.com.vn/vn/tour/..."
          onChange={(e) => setGhep({ ...ghep, link: e.target.value })} /></label>
      <span className="muted" style={{ fontSize: 13 }}>Chỉ nhận địa chỉ trên vietourist.com.vn. Để TRỐNG rồi bấm Lưu
        nghĩa là <b>bỏ ghép</b>. Ghép xong máy tự đọc ảnh, lịch trình và mục «Giá tour bao gồm» từ trang ấy.</span>
      <div style={{ display: "flex", gap: 10, marginTop: 10, flexWrap: "wrap" }}>
        <button className="act teal" disabled={busy} onClick={() => lam(async () => {
          const r = await api(`/tour-online/${ghep.id}/ghep-web`, { method: "POST", json: { link_web: ghep.link.trim() } });
          setGhep(null); return r; })}>{ghep.link.trim() ? "Lưu và đọc web" : "Bỏ ghép"}</button>
        <button className="act grey" onClick={() => setGhep(null)}>Hủy</button></div>
    </div>}

    {sua && <div className="panel" style={{ border: "2px solid var(--accent, #3f66e0)" }}>
      <h3 style={{ marginTop: 0 }}>Hồ sơ cổng · {sua.ma}</h3>
      <label>Điểm đến (trống = máy suy từ tên)<input value={sua.diem_den} onChange={(e) => setSua({ ...sua, diem_den: e.target.value })} /></label>
      <label>Điểm nổi bật (3–5 dòng ngắn, mỗi dòng một ý)<textarea rows={5} value={sua.noi_bat} onChange={(e) => setSua({ ...sua, noi_bat: e.target.value })} /></label>
      <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={sua.wellness} onChange={(e) => setSua({ ...sua, wellness: e.target.checked })} />Wellness &amp; retreat</label>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>Phương tiện: {Object.entries(x.phuong_tien).map(([k, t]) =>
        <label key={k} style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={sua.phuong_tien_ds.includes(k)}
          onChange={(e) => setSua({ ...sua, phuong_tien_ds: e.target.checked ? [...sua.phuong_tien_ds, k] : sua.phuong_tien_ds.filter((y: string) => y !== k) })} />{t as string}</label>)}</div>
      <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
        <button className="act teal" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/${sua.id}/cong`, { method: "PUT", json: { diem_den: sua.diem_den,
          noi_bat: sua.noi_bat.split("\n").map((s: string) => s.trim()).filter(Boolean), wellness: sua.wellness, phuong_tien_ds: sua.phuong_tien_ds } }); setSua(null); return r; })}>Lưu</button>
        <button className="act grey" onClick={() => setSua(null)}>Hủy</button></div>
    </div>}

    {tab === "web" && <div className="panel">
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
        <button className="act teal" disabled={busy} onClick={taiWeb}>{busy && !web ? "Đang đọc vietourist.com.vn…" : "Đọc danh sách tour trên web"}</button>
        <span className="muted" style={{ fontSize: 13 }}>Chỉ đọc hai trang danh sách tour trong nước / nước ngoài. Máy gợi ý sản phẩm giống tên + cùng số ngày; người có quyền xác nhận mới ghép.</span></div>
      {web && <div className="wrap"><table><thead><tr><th>Tour trên web</th><th>Đã ghép</th><th>Gợi ý</th><th /></tr></thead>
        <tbody>{web.map((w) => <tr key={w.url}><td><a href={w.url} target="_blank" rel="noopener noreferrer">{w.ten}</a>{w.muc && <><br /><small className="muted">{w.muc}</small></>}
          {w.goi_y_wellness && <> <Tag cls="ok">Gợi ý Wellness — xác nhận ở «Sửa hồ sơ»</Tag></>}</td>
          <td>{w.da_ghep ? <><b>{w.da_ghep.ma}</b> {w.da_ghep.ten}</> : <span className="muted">—</span>}</td>
          <td>{w.goi_y ? <>{w.goi_y.ma} {w.goi_y.ten} <small className="muted">({Math.round(w.goi_y.diem * 100)}%)</small></> : <span className="muted">Không có gợi ý</span>}</td>
          <td>{duoc.ghep && !w.da_ghep && w.goi_y && <button className="act grey" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/${w.goi_y.pid}/ghep-web`, { method: "POST", json: { link_web: w.url } }); await taiWeb(); return r; })}>Xác nhận ghép {w.goi_y.ma}</button>}</td></tr>)}
          {!web.length && <tr><td colSpan={4} className="muted">Không đọc được tour nào.</td></tr>}</tbody></table></div>}
    </div>}

    {tab === "don" && <div className="panel">
      <label style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 10 }}><input type="checkbox" checked={chiVat} onChange={(e) => setChiVat(e.target.checked)} />Chỉ đơn cần hóa đơn GTGT công ty</label>
      {!don ? <p>Đang tải…</p> : <div className="wrap"><table><thead><tr><th>Mã</th><th>Tour</th><th>Khách</th><th>Tiền</th><th>Trạng thái</th><th>Email</th><th>Hóa đơn công ty</th></tr></thead>
        <tbody>{don.map((o) => <tr key={o.id}><td><b>{o.ma}</b><br /><small className="muted">{luc(o.tao_luc)}</small></td>
          <td>{o.ten}<br /><small className="muted">{o.ma_chuyen} · {o.khoi_hanh}</small></td>
          <td>{o.khach_hang}<br /><small className="muted">{o.dien_thoai} · {o.nguoi_lon} NL{o.tre_em ? ` ${o.tre_em} TE` : ""}{o.em_be ? ` ${o.em_be} EB` : ""} · Sales {o.sales}</small></td>
          <td>Tổng {d(o.tong)}<br />Đã trả {d(o.da_tra)}<br /><small className="muted">{o.cach_tra_ten}</small></td>
          <td><Tag cls={o.trang_thai.startsWith("Đã thanh toán") ? "ok" : o.trang_thai.startsWith("Đã đặt cọc") ? "navy" : o.trang_thai === "Chờ thanh toán" ? "warn" : "grey"}>{o.trang_thai}</Tag></td>
          <td>{o.email_gui_luc ? `Đã gửi ${luc(o.email_gui_luc)}` : "—"}{o.email_loi && <><br /><Tag cls="red">{o.email_loi}</Tag></>}</td>
          <td>{o.hoa_don_cong_ty ? <>{o.hoa_don_cong_ty.ten}<br /><small>MST {o.hoa_don_cong_ty.mst}</small><br />
            {o.hoa_don_da_xuat ? <Tag cls="ok">Đã xuất · {o.hoa_don_xuat_boi}</Tag>
              : duoc.vat ? <button className="act grey" disabled={busy} onClick={() => lam(async () => { const r = await api(`/tour-online/don/${o.id}/da-xuat-vat`, { method: "POST" }); setDon((await api(`/tour-online/don?chi_vat=${chiVat}`)).don); return r; })}>Đánh dấu đã xuất</button>
              : <Tag cls="warn">Chờ Kế toán</Tag>}</> : <span className="muted">—</span>}</td></tr>)}
          {!don.length && <tr><td colSpan={7} className="muted">Chưa có đơn.</td></tr>}</tbody></table></div>}
    </div>}

    {tab === "mt" && <div className="panel"><h3 style={{ marginTop: 0 }}>Ma trận quản lý</h3>
      <div className="wrap"><table><thead><tr><th>Việc</th><th>Vai trò được làm</th></tr></thead>
        <tbody>{Object.entries(x.ma_tran || {}).map(([viec, vai]) => <tr key={viec}><td>{viec}</td><td>{(vai as string[]).map((v) => VAI[v] || v).join(", ")}</td></tr>)}</tbody></table></div>
      <p className="muted" style={{ fontSize: 13 }}>Máy chủ kiểm quyền ở từng cửa; bảng này đọc từ máy chủ. Không ai sửa nội dung trên vietourist.com.vn từ đây.</p></div>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }

/** P1-01 (Chủ tịch duyệt 09/11/2026): khách đang thấy gì trên kh.vietourist.vn — thiếu mục nào, nhập ở đâu. Chỉ báo, không chặn. */
function NoiDungCong({ p, ten }: { p: any; ten: Record<string, string> }) {
  const th: string[] = p.thieu || [];
  if (!th.length) return <Tag cls="ok">Đủ nội dung</Tag>;
  const goiY: string[] = [];
  if (th.includes("anh") || th.includes("lich")) goiY.push(p.link_web
    ? "Sửa bài trên web (ảnh, mốc «NGÀY 1:») rồi bấm «Đọc lại web»."
    : "Ghép link web, hoặc nhập «NGÀY 1:… NGÀY 2:…» vào ô Chương trình của sản phẩm.");
  if (th.includes("bao_gom")) goiY.push("Nhập mục «Giá tour bao gồm» trên web hoặc ô Dịch vụ của sản phẩm.");
  if (th.includes("tre_em")) goiY.push("Nhập giá trẻ em ở chuyến đang mở bán (Điều hành).");
  return <>{th.map((k) => <Tag key={k} cls="warn">{ten[k] || k}</Tag>)}<div className="muted" style={{ fontSize: 12 }}>{goiY.join(" ")}</div></>;
}
