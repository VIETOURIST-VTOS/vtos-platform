"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** DT-2 (Chủ tịch duyệt bản xem thử 28/10/2026) — ĐẶT BÀN NHÀ HÀNG: TIỀN VÀO, HỦY & HOÀN, DOANH SỐ.
 *  · Tiền QR: Kế toán gán giao dịch ngân hàng có mã đơn (NHyymmxxxx) vào đơn. Tiền thẻ: OnePay báo có chữ ký,
 *    Kế toán đối soát với sao kê OnePay.
 *  · Hủy & hoàn: máy tính số giữ / hoàn theo tham số; Sales xác nhận, Kế toán ghi đã hoàn kèm chứng từ.
 *    Hủy miễn phạt chỉ TP / GĐ Kinh doanh, có lý do.
 *  · Doanh số: đơn qua đại lý / CTV đã dùng → Kế toán chốt (vào D06), chốt rồi khóa. */
const TT_DN: Record<string, string> = { cho_tp: "chờ robot", cho_kt: "robot dừng — bổ sung NCC", cho_duyet: "chờ TGĐ / CT duyệt", cho_chi: "lệnh chi chờ", da_chi: "đã chi", tu_choi: "từ chối" };   // KS-16d
type Tab = "tien" | "the" | "hoan" | "chot" | "don";
const TT: Record<string, string> = { cho_nhan: "warn", cho_tra: "warn", da_giu: "ok", het_han: "red", tu_choi: "red", da_dung: "ok", khong_den: "red", huy: "" };

function Trang() {
  const { toast } = useShell();
  const [tab, setTab] = useState<Tab>("tien");
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [q, setQ] = useState<Record<string, string>>({});
  const [chon, setChon] = useState<Record<number, string>>({});
  const tai = useCallback(() => api<any>("/dat-ban-nha-hang").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { tai(); }, [tai]);
  const goi = async (path: string, json: any = {}) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); setD(r); } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };
  if (!d) return <div className="card">Đang tải…</div>;
  const Q = d.quyen;
  const hoan = d.don.filter((x: any) => x.hoan_tt === "cho_sales" || x.hoan_tt === "cho_chi");
  const chot = d.don.filter((x: any) => x.trang_thai === "da_dung");   // AT-1c: chốt cả đơn khách tự đặt để cộng điểm
  const kmCho = d.don.filter((x: any) => x.km_vtd > 0 && !x.km_but_toan && ["huy", "khong_den"].includes(x.trang_thai));   // KS-16b
  const cho_tien = d.don.filter((x: any) => ["cho_nhan", "cho_tra", "het_han", "huy", "tu_choi"].includes(x.trang_thai));
  const TABS: [Tab, string, number][] = [["tien", "Tiền QR chờ gán", d.giao_dich_cho.length], ["the", "Thẻ chờ đối soát", d.the_cho_doi_soat.length],
    ["hoan", "Hủy & hoàn", hoan.length], ["chot", "Chốt doanh số", chot.filter((x: any) => x.doanh_so == null).length], ["don", "Tất cả đơn", 0]];
  const ts = d.tham_so;

  return (<div>
    <h1 style={{ margin: "4px 0" }}>Đặt bàn nhà hàng: tiền & hoàn</h1>
    <div className="muted">Khách lẻ cọc {ts.coc_le}% hoặc trả đủ; đoàn từ {ts.doan_tu} khách đặt sẵn menu cọc {ts.coc_doan}% hoặc trả đủ. Hủy trước {ts.mien_phi_gio} giờ hoàn đủ;
      dưới {ts.mien_phi_gio} giờ giữ {ts.phat}% bill; dưới {ts.gan_gio} giờ hoặc không đến: lẻ {ts.phat}%, đoàn {ts.phat_doan_gan}%. Thẻ OnePay: {d.the_bat ? <Tag cls="ok">đang bật</Tag> : <Tag cls="">chưa bật — chỉ QR</Tag>}</div>
    <div className="tabs" style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0" }}>
      {TABS.map(([k, t, n]) => <button key={k} className={`act ${tab === k ? "teal" : "grey"}`} style={{ margin: 0 }} onClick={() => setTab(k)}>{t}{n ? ` (${n})` : ""}</button>)}</div>

    {tab === "tien" && <div className="card"><h3>Giao dịch QR có mã đơn đặt bàn — chưa gán</h3>
      {!d.giao_dich_cho.length ? <div className="muted">Không có giao dịch chờ.</div>
      : <table><thead><tr><th>Lúc</th><th>Số tiền</th><th>Nội dung</th><th>Đơn</th><th></th></tr></thead><tbody>{d.giao_dich_cho.map((t: any) => <tr key={t.txn_id}>
        <td>{fmtDT(t.luc)}</td><td>{vnd(t.so_tien)}</td><td style={{ fontSize: 12 }}>{t.noi_dung}</td>
        <td>{t.ma}<div className="muted" style={{ fontSize: 12 }}>{t.trang_thai_ten}{t.con_phai_tra != null ? ` · còn phải trả trước ${vnd(t.con_phai_tra)}` : ""}</div></td>
        <td>{Q.ke_toan && t.don_id && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/${t.don_id}/qr`, { txn_id: t.txn_id })}>Xác nhận vào {t.ma}</button>}</td></tr>)}</tbody></table>}
      {Q.ke_toan && cho_tien.length > 0 && <><h4 style={{ margin: "10px 0 4px" }}>Gán tay (nội dung chuyển khoản sai mã)</h4>
        <div className="muted" style={{ fontSize: 12 }}>Ghi số giao dịch (txn) ở màn Đối soát ngân hàng vào ô của đơn.</div>
        <table><tbody>{cho_tien.slice(0, 30).map((x: any) => <tr key={x.id}><td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nha_hang} · {fmtD(x.ngay)} {x.gio}</div></td>
          <td>{x.trang_thai_ten}<div className="muted" style={{ fontSize: 12 }}>đã trả {vnd(x.da_tra)} / phải trả trước {vnd(x.phai_tra_truoc)}</div></td>
          <td><input placeholder="Số txn" value={chon[x.id] || ""} onChange={(e) => setChon({ ...chon, [x.id]: e.target.value })} style={{ width: 90 }} />
            <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={busy || !Number(chon[x.id])} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/qr`, { txn_id: Number(chon[x.id]) })}>Gán</button></td></tr>)}</tbody></table></>}
      <div className="muted">Xác nhận là máy ghi sổ Nợ 1121 / Có 3388 phải trả nhà hàng (Vietourist thu hộ). Tiền về khi đơn đã hết hạn / đã hủy / bị từ chối: máy tự chuyển thành khoản phải hoàn (tab Hủy & hoàn).</div></div>}

    {tab === "the" && <div className="card"><h3>Giao dịch thẻ OnePay báo thành công — chờ đối soát</h3>
      {!d.the_cho_doi_soat.length ? <div className="muted">Không có giao dịch chờ.</div>
      : <table><thead><tr><th>Đơn</th><th>Số tiền</th><th>Mã GD OnePay</th><th>Lúc</th><th></th></tr></thead><tbody>{d.the_cho_doi_soat.map((t: any) => <tr key={t.id}>
        <td>{t.ma}<div className="muted" style={{ fontSize: 12 }}>{t.ma_gd}</div></td><td>{vnd(t.so_tien)}</td><td>{t.so_gd_cong}</td><td>{fmtDT(t.luc)}</td>
        <td style={{ whiteSpace: "nowrap" }}>{Q.ke_toan && <><input type="number" placeholder="Phí thẻ (đ)" value={q[`p${t.id}`] ?? ""} onChange={(e) => setQ({ ...q, [`p${t.id}`]: e.target.value })} style={{ width: 110 }} />
          <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || q[`p${t.id}`] === undefined || q[`p${t.id}`] === ""} onClick={() => goi(`/dat-ban-nha-hang/the/${t.id}/doi-soat`, { phi: Number(q[`p${t.id}`]) })}>Khớp sao kê · ghi sổ</button></>}</td></tr>)}</tbody></table>}
      <div className="muted">Bàn đã giữ ngay khi cổng thẻ báo thành công (chữ ký kiểm được). Ghi phí thẻ theo sao kê: máy ghi Nợ 1121 thực nhận + Nợ 6428 phí / Có 3388 phải trả nhà hàng (sổ CTCP Vietourist Holdings).</div></div>}

    {tab === "hoan" && <div className="card"><h3>Hủy & hoàn</h3>
      {!hoan.length ? <div className="muted">Không có khoản chờ hoàn.</div>
      : <table><thead><tr><th>Đơn</th><th>Lý do</th><th>Đã trả · giữ · hoàn</th><th>Bước</th><th></th></tr></thead><tbody>{hoan.map((x: any) => <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nha_hang} · {fmtD(x.ngay)} {x.gio}{x.la_doan ? " · đoàn" : ""}</div></td>
        <td style={{ fontSize: 12 }}>{x.trang_thai_ten}<div className="muted">{x.huy_ly_do}{x.mien_phat ? " · miễn phạt" : ""}</div></td>
        <td>{vnd(x.da_tra)} · {vnd(x.so_giu || 0)} · <b>{vnd((x.so_hoan || 0) - (x.da_hoan_tien || 0))}</b>{x.da_hoan_tien ? <div className="muted" style={{ fontSize: 12 }}>đã hoàn trước {vnd(x.da_hoan_tien)}</div> : null}<div className="muted" style={{ fontSize: 12 }}>{x.thanh_toan.map((t: any) => t.kenh).join(", ")}</div></td>
        <td><Tag cls="warn">{x.hoan_tt_ten}</Tag><div className="muted" style={{ fontSize: 12, whiteSpace: "pre-line" }}>{x.hoan_ghi_chu}</div></td>
        <td style={{ whiteSpace: "nowrap" }}>
          <input placeholder={x.hoan_tt === "cho_chi" ? "Mã hoàn OnePay / số UNC" : "Ghi chú"} value={q[`h${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`h${x.id}`]: e.target.value })} style={{ width: 150 }} />
          {x.hoan_tt === "cho_sales" && Q.sales && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/xac-nhan-hoan`, { ghi_chu: q[`h${x.id}`] || "" })}>Xác nhận hoàn</button>}
          {x.hoan_tt === "cho_chi" && Q.ke_toan && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`h${x.id}`] || "").trim().length < 3} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/da-hoan`, { ghi_chu: q[`h${x.id}`] })}>Đã hoàn</button>}</td></tr>)}</tbody></table>}
      {kmCho.length > 0 && <><h3>Voucher VTD chịu — đơn hủy / không đến chưa ghi sổ ({kmCho.length})</h3>
        <table><thead><tr><th>Đơn</th><th>Voucher</th><th>Thuộc nhà hàng</th><th></th></tr></thead><tbody>{kmCho.map((x: any) => <tr key={x.id}>
          <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nha_hang} · {x.trang_thai_ten}</div></td><td>{x.voucher?.ma} · {vnd(x.giam_voucher)}</td><td><b>{vnd(x.km_vtd)}</b></td>
          <td>{Q.ke_toan ? <button className="act teal" disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/ghi-km`, {})}>Ghi Nợ 641 / Có 3388</button> : <span className="muted">Kế toán ghi</span>}</td></tr>)}</tbody></table></>}
      <div className="muted">Hoàn thẻ: làm trên trang quản trị cổng thẻ (tiền về thẻ khách). Hoàn QR: chuyển khoản lại. «Đã hoàn» là máy ghi sổ Nợ 3388 / Có 1121. Phần giữ lại thuộc nhà hàng. Bớt khách cũng sinh khoản hoàn (hoàn được nhiều lần).</div></div>}

    {tab === "chot" && <div className="card"><h3>Chốt doanh số đơn đã dùng</h3><div className="muted">Đơn qua đại lý / CTV → vào D06. Đơn khách / cổ đông tự đặt → cộng điểm thành viên trên số đã trả qua Vietourist.</div>
      {!chot.length ? <div className="muted">Chưa có đơn đã dùng.</div>
      : <table><thead><tr><th>Đơn</th><th>Tiền</th><th>Nhà hàng báo</th><th>Doanh số</th><th>Hoa hồng NH · trả nhà hàng</th></tr></thead><tbody>{chot.map((x: any) => { const giu = (x.da_tra || 0) - (x.so_hoan || 0) + (x.km_vtd || 0); const hh = Number(q[`h${x.id}`] || 0); return <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nha_hang} · {fmtD(x.ngay)}</div></td>
        <td>Trả trước {vnd(x.da_tra)}<div className="muted" style={{ fontSize: 12 }}>{x.thanh_toan.map((t: any) => `${t.kenh}: ${t.trang_thai_ten}`).join("; ")}</div>
          {x.km_vtd > 0 && <div className="muted" style={{ fontSize: 12 }}>+ voucher {x.voucher?.ma} {vnd(x.km_vtd)} VTD chịu{x.km_but_toan ? ` · đã ghi ${x.km_but_toan}` : " · chốt sẽ ghi Nợ 641 / Có 3388"}</div>}</td>
        <td>Bill {vnd(x.bill_thuc_te || 0)}<div className="muted" style={{ fontSize: 12 }}>thu tại bàn {vnd(x.thu_tai_ban || 0)}{x.co_bill ? " · có ảnh bill" : " · không ảnh bill"}{x.dung_ghi_chu ? ` · ${x.dung_ghi_chu}` : ""}</div></td>
        <td>{x.doanh_so != null ? <><b>{vnd(x.doanh_so)}</b><div className="muted" style={{ fontSize: 12 }}>kỳ {x.ky_d06} · {x.chot_boi} · khóa</div></>
          : Q.ke_toan ? <input type="number" placeholder={String(x.bill_thuc_te || "")} value={q[`c${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`c${x.id}`]: e.target.value })} style={{ width: 120 }} />
          : <span className="muted">Chờ Kế toán</span>}</td>
        <td>{x.doanh_so != null ? <>{x.hoa_hong != null ? <>hoa hồng {vnd(x.hoa_hong)} · trả <b>{vnd(x.phai_tra_nh || 0)}</b></> : <span className="muted">chốt trước KS-16d</span>}
            {x.de_nghi_chi && <div style={{ fontSize: 12 }}>Đề nghị chi <b>{x.de_nghi_chi.code}</b> · {TT_DN[x.de_nghi_chi.status] || x.de_nghi_chi.status}</div>}
            {x.dt_but_toan ? <div className="muted" style={{ fontSize: 12 }}>Doanh thu HH: {x.dt_but_toan}</div>
              : (x.hoa_hong > 0 && (!x.de_nghi_chi || x.de_nghi_chi.status === "da_chi") && Q.ke_toan)
                ? <div><button className="act teal" style={{ margin: "4px 0 0" }} disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/ghi-dt-hoa-hong`, {})}>Ghi doanh thu HH</button></div> : null}</>
          : Q.ke_toan ? <><input type="number" placeholder="0" value={q[`h${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`h${x.id}`]: e.target.value })} style={{ width: 110 }} />
            <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || !Number(q[`c${x.id}`]) || hh < 0 || hh > giu} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/chot`, { doanh_so: Number(q[`c${x.id}`]), hoa_hong: hh })}>Chốt</button>
            <div className="muted" style={{ fontSize: 12 }}>→ trả nhà hàng {vnd(Math.max(giu - hh, 0))} = {vnd(x.da_tra || 0)}{x.so_hoan ? ` − hoàn ${vnd(x.so_hoan)}` : ""}{x.km_vtd ? ` + voucher ${vnd(x.km_vtd)}` : ""} − hoa hồng {vnd(hh)}</div></>
          : <span className="muted">Chờ Kế toán</span>}</td></tr>; })}</tbody></table>}
      <div className="muted">Đối chiếu số trả trước Vietourist đã thu + số thu tại bàn với bill. Vào kỳ D06 của ngày muộn hơn giữa ngày ăn và ngày chốt. Hoa hồng nhà hàng theo hợp đồng (trống = 0); phải trả nhà hàng &gt; 0 → máy lập đề nghị chi, robot kế toán kiểm → TGĐ / Chủ tịch duyệt.</div></div>}

    {tab === "don" && <div className="card"><h3>Tất cả đơn đặt bàn</h3>
      {!d.don.length ? <div className="muted">Chưa có đơn.</div>
      : <table><thead><tr><th>Đơn</th><th>Khách</th><th>Thanh toán</th><th>Trạng thái</th><th></th></tr></thead><tbody>{d.don.map((x: any) => <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nha_hang} · {x.thuc_don} · {fmtD(x.ngay)} {x.gio}</div></td>
        <td>{x.ten_khach} · {x.dien_thoai}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nguoi_lon} NL + {x.tre_em} TE{x.la_doan ? " · đoàn" : ""}</div></td>
        <td>{x.cach_tt_ten} · tạm tính {vnd(x.tam_tinh)}<div className="muted" style={{ fontSize: 12 }}>đã trả {vnd(x.da_tra)} / {vnd(x.phai_tra_truoc)}{x.han_tra ? ` · hạn ${fmtDT(x.han_tra)}` : ""}</div></td>
        <td><Tag cls={TT[x.trang_thai] || ""}>{x.trang_thai_ten}</Tag>
          {/* P1-03: quá hạn nhà hàng trả lời — Sales gọi nhà hàng; đơn không tự hủy */}
          {x.qua_han_phan_hoi && <div><Tag cls="red">Quá hạn nhà hàng trả lời</Tag><div className="muted" style={{ fontSize: 12 }}>hạn {fmtDT(x.han_phan_hoi)} · gọi nhà hàng, báo khách</div></div>}
          {!x.qua_han_phan_hoi && x.trang_thai === "cho_nhan" && x.han_phan_hoi && <div className="muted" style={{ fontSize: 12 }}>nhà hàng trả lời trước {fmtDT(x.han_phan_hoi)}</div>}
          {(x.phu_thu || []).length > 0 && <div className="muted" style={{ fontSize: 12 }}>phụ thu: {x.phu_thu.map((p: any) => `${p.ten} ${vnd(p.so_tien)}`).join("; ")}</div>}</td>
        <td style={{ whiteSpace: "nowrap" }}>{Q.sales && x.co_the_huy && <>
          <input placeholder="Lý do hủy" value={q[`u${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`u${x.id}`]: e.target.value })} style={{ width: 130 }} />
          <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`u${x.id}`] || "").trim().length < 5} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/huy`, { ly_do: q[`u${x.id}`] })}>Hủy theo chính sách</button>
          {Q.mien_phat && <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`u${x.id}`] || "").trim().length < 5} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/huy`, { ly_do: q[`u${x.id}`], mien_phat: true })}>Hủy miễn phạt</button>}</>}</td></tr>)}</tbody></table>}
      <div className="muted">Miễn phạt (nhà hàng hủy, bất khả kháng, ngoại lệ) chỉ TP / GĐ Kinh doanh, phải ghi lý do.</div></div>}
  </div>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
