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
  const chot = d.don.filter((x: any) => x.trang_thai === "da_dung" && x.doi_tac_id);
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
      <div className="muted">Tiền về khi đơn đã hết hạn / đã hủy / bị từ chối: máy tự chuyển thành khoản phải hoàn (tab Hủy & hoàn).</div></div>}

    {tab === "the" && <div className="card"><h3>Giao dịch thẻ OnePay báo thành công — chờ đối soát</h3>
      {!d.the_cho_doi_soat.length ? <div className="muted">Không có giao dịch chờ.</div>
      : <table><thead><tr><th>Đơn</th><th>Số tiền</th><th>Mã GD OnePay</th><th>Lúc</th><th></th></tr></thead><tbody>{d.the_cho_doi_soat.map((t: any) => <tr key={t.id}>
        <td>{t.ma}<div className="muted" style={{ fontSize: 12 }}>{t.ma_gd}</div></td><td>{vnd(t.so_tien)}</td><td>{t.so_gd_cong}</td><td>{fmtDT(t.luc)}</td>
        <td>{Q.ke_toan && <button className="act teal" style={{ margin: 0 }} disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/the/${t.id}/doi-soat`)}>Khớp sao kê OnePay</button>}</td></tr>)}</tbody></table>}
      <div className="muted">Bàn đã giữ ngay khi OnePay báo thành công (chữ ký kiểm được). Phí thẻ Vietourist chịu — ghi chi phí theo sao kê.</div></div>}

    {tab === "hoan" && <div className="card"><h3>Hủy & hoàn</h3>
      {!hoan.length ? <div className="muted">Không có khoản chờ hoàn.</div>
      : <table><thead><tr><th>Đơn</th><th>Lý do</th><th>Đã trả · giữ · hoàn</th><th>Bước</th><th></th></tr></thead><tbody>{hoan.map((x: any) => <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nha_hang} · {fmtD(x.ngay)} {x.gio}{x.la_doan ? " · đoàn" : ""}</div></td>
        <td style={{ fontSize: 12 }}>{x.trang_thai_ten}<div className="muted">{x.huy_ly_do}{x.mien_phat ? " · miễn phạt" : ""}</div></td>
        <td>{vnd(x.da_tra)} · {vnd(x.so_giu || 0)} · <b>{vnd(x.so_hoan || 0)}</b><div className="muted" style={{ fontSize: 12 }}>{x.thanh_toan.map((t: any) => t.kenh).join(", ")}</div></td>
        <td><Tag cls="warn">{x.hoan_tt_ten}</Tag><div className="muted" style={{ fontSize: 12, whiteSpace: "pre-line" }}>{x.hoan_ghi_chu}</div></td>
        <td style={{ whiteSpace: "nowrap" }}>
          <input placeholder={x.hoan_tt === "cho_chi" ? "Mã hoàn OnePay / số UNC" : "Ghi chú"} value={q[`h${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`h${x.id}`]: e.target.value })} style={{ width: 150 }} />
          {x.hoan_tt === "cho_sales" && Q.sales && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/xac-nhan-hoan`, { ghi_chu: q[`h${x.id}`] || "" })}>Xác nhận hoàn</button>}
          {x.hoan_tt === "cho_chi" && Q.ke_toan && <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`h${x.id}`] || "").trim().length < 3} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/da-hoan`, { ghi_chu: q[`h${x.id}`] })}>Đã hoàn</button>}</td></tr>)}</tbody></table>}
      <div className="muted">Hoàn thẻ: làm trên trang quản trị OnePay (tiền về thẻ khách). Hoàn QR: chuyển khoản lại. Phần giữ lại thuộc nhà hàng.</div></div>}

    {tab === "chot" && <div className="card"><h3>Chốt doanh số đơn qua đại lý / CTV (vào D06)</h3>
      {!chot.length ? <div className="muted">Chưa có đơn qua đối tác đã dùng.</div>
      : <table><thead><tr><th>Đơn</th><th>Tiền</th><th>Nhà hàng báo</th><th>Doanh số</th></tr></thead><tbody>{chot.map((x: any) => <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nha_hang} · {fmtD(x.ngay)}</div></td>
        <td>Trả trước {vnd(x.da_tra)}<div className="muted" style={{ fontSize: 12 }}>{x.thanh_toan.map((t: any) => `${t.kenh}: ${t.trang_thai_ten}`).join("; ")}</div></td>
        <td>Bill {vnd(x.bill_thuc_te || 0)}<div className="muted" style={{ fontSize: 12 }}>thu tại bàn {vnd(x.thu_tai_ban || 0)}{x.co_bill ? " · có ảnh bill" : " · không ảnh bill"}{x.dung_ghi_chu ? ` · ${x.dung_ghi_chu}` : ""}</div></td>
        <td>{x.doanh_so != null ? <><b>{vnd(x.doanh_so)}</b><div className="muted" style={{ fontSize: 12 }}>kỳ {x.ky_d06} · {x.chot_boi} · khóa</div></>
          : Q.ke_toan ? <><input type="number" placeholder={String(x.bill_thuc_te || "")} value={q[`c${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`c${x.id}`]: e.target.value })} style={{ width: 120 }} />
            <button className="act teal" style={{ margin: "0 0 0 6px" }} disabled={busy || !Number(q[`c${x.id}`])} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/chot`, { doanh_so: Number(q[`c${x.id}`]) })}>Chốt</button></>
          : <span className="muted">Chờ Kế toán</span>}</td></tr>)}</tbody></table>}
      <div className="muted">Đối chiếu số trả trước Vietourist đã thu + số thu tại bàn với bill. Vào kỳ D06 của ngày muộn hơn giữa ngày ăn và ngày chốt.</div></div>}

    {tab === "don" && <div className="card"><h3>Tất cả đơn đặt bàn</h3>
      {!d.don.length ? <div className="muted">Chưa có đơn.</div>
      : <table><thead><tr><th>Đơn</th><th>Khách</th><th>Thanh toán</th><th>Trạng thái</th><th></th></tr></thead><tbody>{d.don.map((x: any) => <tr key={x.id}>
        <td>{x.ma}<div className="muted" style={{ fontSize: 12 }}>{x.nha_hang} · {x.thuc_don} · {fmtD(x.ngay)} {x.gio}</div></td>
        <td>{x.ten_khach} · {x.dien_thoai}<div className="muted" style={{ fontSize: 12 }}>{x.nguon} · {x.nguoi_lon} NL + {x.tre_em} TE{x.la_doan ? " · đoàn" : ""}</div></td>
        <td>{x.cach_tt_ten} · tạm tính {vnd(x.tam_tinh)}<div className="muted" style={{ fontSize: 12 }}>đã trả {vnd(x.da_tra)} / {vnd(x.phai_tra_truoc)}{x.han_tra ? ` · hạn ${fmtDT(x.han_tra)}` : ""}</div></td>
        <td><Tag cls={TT[x.trang_thai] || ""}>{x.trang_thai_ten}</Tag></td>
        <td style={{ whiteSpace: "nowrap" }}>{Q.sales && x.co_the_huy && <>
          <input placeholder="Lý do hủy" value={q[`u${x.id}`] || ""} onChange={(e) => setQ({ ...q, [`u${x.id}`]: e.target.value })} style={{ width: 130 }} />
          <button className="act red" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`u${x.id}`] || "").trim().length < 5} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/huy`, { ly_do: q[`u${x.id}`] })}>Hủy theo chính sách</button>
          {Q.mien_phat && <button className="act grey" style={{ margin: "0 0 0 6px" }} disabled={busy || (q[`u${x.id}`] || "").trim().length < 5} onClick={() => goi(`/dat-ban-nha-hang/${x.id}/huy`, { ly_do: q[`u${x.id}`], mien_phat: true })}>Hủy miễn phạt</button>}</>}</td></tr>)}</tbody></table>}
      <div className="muted">Miễn phạt (nhà hàng hủy, bất khả kháng, ngoại lệ) chỉ TP / GĐ Kinh doanh, phải ghi lý do.</div></div>}
  </div>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
