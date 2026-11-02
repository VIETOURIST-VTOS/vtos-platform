"use client";
/* TR-1d · kh.vietourist.vn/thanh-toan/<mã> — link thanh toán tour đoàn riêng (Chủ tịch duyệt bản xem thử 02/11/2026).
   Khách KHÔNG cần đăng nhập. Số tiền, tài khoản, nội dung và chuỗi QR đều do MÁY CHỦ trả về; trang chỉ vẽ.
   Tour đoàn chỉ nhận chuyển khoản (QR hoặc chuyển tay) — không có thẻ Visa / Master. */
import { useEffect, useState } from "react";
import QRCode from "qrcode";

const tien = (n: number) => `${Math.round(n || 0).toLocaleString("vi-VN")} ₫`;
const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "–");

export default function Trang({ params }: { params: { ma: string } }) {
  const ma = decodeURIComponent(params.ma || "").toUpperCase();
  const [o, setO] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [anh, setAnh] = useState("");
  const [chep, setChep] = useState("");
  useEffect(() => {
    fetch(`/api/v1/cong/mo/tt-doan/${encodeURIComponent(ma)}`)
      .then(async (r) => { const d = await r.json().catch(() => ({})); if (!r.ok) throw new Error(d?.detail || `Lỗi ${r.status}`); return d; })
      .then((d) => { setO(d); return d.chuyen_khoan ? QRCode.toDataURL(d.chuyen_khoan.payload, { margin: 1, width: 240, errorCorrectionLevel: "M" }) : ""; })
      .then(setAnh).catch((x) => setLoi(x.message || "Không mở được link"));
  }, [ma]);
  const chepChu = async (v: string, nhan: string) => {
    try { await navigator.clipboard.writeText(v); setChep(`Đã chép ${nhan}`); } catch { setChep("Trình duyệt chặn chép — hãy bôi đen để chép"); }
  };
  const ck = o?.chuyen_khoan;
  return (<div className="ttd">
    <style dangerouslySetInnerHTML={{ __html: CSS }} />
    <header className="ttd-top"><div className="ttd-in"><a className="ttd-logo" href="/cong">VIET<em>OURIST</em></a><span>Thanh toán tour đoàn</span></div></header>
    <main className="ttd-in ttd-main">
      {loi ? <div className="ttd-card"><h1>Không mở được link</h1><p>{loi}</p><p className="ttd-mo">Vui lòng liên hệ Sales phụ trách đoàn của bạn.</p></div>
        : !o ? <div className="ttd-card"><p>Đang tải…</p></div> : (<>
        <section className="ttd-card">
          <dl className="ttd-kv">
            <div><dt>Khách</dt><dd>{o.khach}</dd></div>
            {o.tour ? <div><dt>Tour</dt><dd>{o.tour}{o.khoi_hanh ? ` · khởi hành ${ngay(o.khoi_hanh)}` : ""}{o.so_khach ? ` · ${o.so_khach} khách` : ""}</dd></div> : null}
            <div><dt>Hợp đồng</dt><dd>{o.so_hop_dong} · đợt {o.dot}/{o.so_dot}{o.ten_dot ? ` · ${o.ten_dot}` : ""}</dd></div>
          </dl>
          <div className="ttd-so"><span>Số tiền đợt này</span><b>{tien(o.so_tien)}</b>
            <small>Hạn {ngay(o.han)} · đã thanh toán {tien(o.da_thu)} / {tien(o.tong_hd)}</small></div>
          {o.trang_thai === "da_tra" ? <p className="ttd-ok">Đã thanh toán {o.tra_luc ? ngay(o.tra_luc) : ""}. Hóa đơn đã gửi qua email.</p>
            : o.trang_thai === "huy" ? <p className="ttd-warn">Link đã bị hủy. Liên hệ Sales phụ trách để nhận link mới.</p>
            : o.trang_thai === "het_han" ? <p className="ttd-warn">Link đã hết hạn ({ngay(o.han)}). Liên hệ Sales phụ trách để nhận link mới.</p> : null}
        </section>
        {o.trang_thai === "da_tra" ? (
          <section className="ttd-card"><a className="ttd-btn" href={`/api/v1/cong/mo/tt-doan/${encodeURIComponent(o.ma)}/hoa-don`}>Tải hóa đơn PDF</a>
            <p className="ttd-mo">Mở lại link sau khi đã trả chỉ để xem và tải hóa đơn.</p></section>) : null}
        {o.trang_thai === "mo" && !ck ? <section className="ttd-card"><p className="ttd-warn">Thông tin chuyển khoản chưa sẵn sàng — liên hệ Sales phụ trách.</p></section> : null}
        {o.trang_thai === "mo" && ck ? (
          <section className="ttd-card ttd-ck">
            <div className="ttd-qr">{anh ? <img src={anh} alt={`Mã QR chuyển ${tien(ck.so_tien)} nội dung ${ck.noi_dung}`} width={220} height={220} /> : <div style={{ width: 220, height: 220 }} />}
              <small>Quét bằng app ngân hàng bất kỳ — số tiền và nội dung đã điền sẵn.</small></div>
            <dl className="ttd-kv">
              <div><dt>Ngân hàng</dt><dd>{ck.ngan_hang}</dd></div>
              <div><dt>Số tài khoản</dt><dd>{ck.so_tk} <button type="button" onClick={() => chepChu(ck.so_tk, "số tài khoản")}>Chép</button></dd></div>
              <div><dt>Chủ tài khoản</dt><dd>{ck.chu_tk}</dd></div>
              <div><dt>Số tiền</dt><dd>{tien(ck.so_tien)} <button type="button" onClick={() => chepChu(String(ck.so_tien), "số tiền")}>Chép</button></dd></div>
              <div><dt>Nội dung</dt><dd><b>{ck.noi_dung}</b> <button type="button" onClick={() => chepChu(ck.noi_dung, "nội dung")}>Chép</button></dd></div>
            </dl>
            {chep ? <p className="ttd-mo" role="status">{chep}</p> : null}
            <p className="ttd-mo">Chuyển ĐÚNG số tiền và ghi ĐÚNG nội dung {ck.noi_dung} — hệ thống tự xác nhận và gửi hóa đơn qua email.
              Tour đoàn không nhận thẻ Visa / Master.</p>
          </section>) : null}
        <p className="ttd-mo">{o.ghi_chu}</p>
      </>)}
    </main>
  </div>);
}

const CSS = `
.ttd{--bg:#eef2f8;--card:#fff;--fg:#1b2433;--muted:#5d6a7d;--line:#dbe2ec;--brand:#2a5bd7;--brand2:#0f2f6b;--sun:#f2a516;--ok:#127a4b;--warn:#9a5a00;
  min-height:100vh;background:var(--bg);color:var(--fg);font-family:"Be Vietnam Pro",system-ui,sans-serif;font-size:15px}
@media (prefers-color-scheme:dark){.ttd{--bg:#0e1622;--card:#162233;--fg:#e6ecf4;--muted:#9fb0c4;--line:#2a3a50;--brand:#7ea2ff;--brand2:#0a1a3a;--ok:#5fd39b;--warn:#f0c060}}
.ttd-in{max-width:760px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.ttd-top{background:var(--brand2);color:#fff}.ttd-top .ttd-in{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-block:12px}
.ttd-logo{color:#fff;text-decoration:none;font-weight:800;font-size:18px}.ttd-logo em{color:var(--sun);font-style:normal}
.ttd-main{display:flex;flex-direction:column;gap:14px;padding-block:18px 40px}
.ttd-card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;display:flex;flex-direction:column;gap:12px;min-width:0}
.ttd-card h1{font-size:19px;margin:0}
.ttd-kv{display:grid;gap:6px;margin:0}.ttd-kv div{display:grid;grid-template-columns:120px 1fr;gap:10px}
.ttd-kv dt{color:var(--muted)}.ttd-kv dd{margin:0;min-width:0;overflow-wrap:anywhere}
.ttd-kv button{border:1px solid var(--line);background:transparent;color:var(--brand);border-radius:6px;padding:2px 8px;font:600 12px inherit;cursor:pointer}
.ttd-so{display:flex;flex-direction:column;gap:2px}.ttd-so span{color:var(--muted);font-size:13px}
.ttd-so b{font-size:28px;color:var(--brand);font-variant-numeric:tabular-nums}.ttd-so small{color:var(--muted)}
.ttd-ck{display:grid;grid-template-columns:auto minmax(0,1fr);gap:16px;align-items:start}
.ttd-ck .ttd-mo{grid-column:1/-1}
.ttd-qr{display:flex;flex-direction:column;gap:6px;align-items:center;max-width:220px}.ttd-qr small{color:var(--muted);text-align:center}
.ttd-mo{color:var(--muted);font-size:13px;margin:0;line-height:1.55}
.ttd-ok{color:var(--ok);font-weight:600;margin:0}.ttd-warn{color:var(--warn);font-weight:600;margin:0}
.ttd-btn{display:inline-block;width:max-content;background:var(--brand);color:#fff;text-decoration:none;border-radius:8px;padding:9px 16px;font-weight:600}
@media (max-width:560px){.ttd-ck{grid-template-columns:1fr}.ttd-qr{margin:0 auto}.ttd-kv div{grid-template-columns:100px 1fr}}
`;
