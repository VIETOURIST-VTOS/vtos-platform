"use client";
/* AT-3 · Đánh giá nhà hàng trên trang khách (Chủ tịch duyệt bản xem thử 29/10/2026).
   Chỉ bài của người đã đặt bàn qua Vietourist và được nhà hàng xác nhận «đã đến dùng». Tên che còn chữ đầu,
   không số điện thoại / mã đơn. Dưới 3 bài: «Mới — chưa đủ đánh giá» thay điểm trung bình; bài vẫn hiện đủ. */
import { useState } from "react";

const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const so = (x?: number | null) => (x == null ? "—" : x.toFixed(1).replace(".", ","));

export function Sao({ n, co = 16 }: { n: number; co?: number }) {
  const d = Math.round(n);
  return <span className="dg-sao" style={{ fontSize: co }} role="img" aria-label={`${n} trên 5 sao`}>
    {"★★★★★".slice(0, d)}<span className="dg-sao-mo">{"★★★★★".slice(d)}</span></span>;
}

/** Dòng ngắn trên thẻ nhà hàng. */
export function SaoThe({ sao }: { sao?: { so_bai: number; diem_tb: number | null } }) {
  if (!sao || !sao.so_bai) return null;
  return <div style={{ fontSize: 13, color: "#3d4b59" }}>{sao.diem_tb != null ? <><span style={{ color: "#b07a10" }} aria-hidden="true">★</span> <b>{so(sao.diem_tb)}</b> · {sao.so_bai} đánh giá</> : "Mới — chưa đủ đánh giá"}</div>;
}

export default function DanhGiaNhaHangKhach({ dau, nhId }: { dau: any; nhId?: number }) {
  const [x, setX] = useState<any>(dau);
  const [xep, setXep] = useState("moi");
  const [trang, setTrang] = useState(1);
  const [lon, setLon] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (!x) return null;
  const t = x.tom_tat;
  const tai = async (xx: string, tr: number) => {
    if (!nhId) return;
    setBusy(true);
    try {
      const r = await fetch(`/api/v1/am-thuc/danh-gia/${nhId}?xep=${xx}&trang=${tr}`).then((r) => (r.ok ? r.json() : null));
      if (r) setX(tr === 1 ? r : { ...r, bai: [...x.bai, ...r.bai] });
      setXep(xx); setTrang(tr);
    } finally { setBusy(false); }
  };
  return <section className="dg"><style>{CSS}</style>
    <div className="dg-luoi">
      <div className="dg-tong">
        {t.diem_tb != null ? <div className="dg-so"><b>{so(t.diem_tb)}</b><Sao n={t.diem_tb} co={22} /></div>
          : <div className="dg-moi">{t.so_bai ? "Mới — chưa đủ đánh giá" : "Chưa có đánh giá"}</div>}
        <span className="dg-phu">{t.so_bai} đánh giá · tất cả từ khách đã đặt bàn qua Vietourist và đến ăn</span>
        {t.diem_tb != null && <div className="dg-muc">{Object.entries(x.muc_ten as Record<string, string>).map(([k, ten]) =>
          <div key={k} className="dg-thanh"><span>{ten}</span><span className="dg-nen"><span style={{ width: `${((t.muc[k] || 0) / 5) * 100}%` }} /></span><b>{so(t.muc[k])}</b></div>)}</div>}
        {t.diem_tb != null && <div className="dg-pb">{[5, 4, 3, 2, 1].map((s) => <span key={s}>{s}★ · {t.phan_bo[s] || 0} bài</span>)}</div>}
        <div className="dg-luat">Chỉ người đã đặt bàn qua Vietourist và được nhà hàng xác nhận «đã đến dùng» mới viết được đánh giá.
          Vietourist không xóa bài chê; chỉ ẩn bài chửi bới hoặc lộ thông tin cá nhân.</div>
      </div>
      <div className="dg-ds">
        {x.tong > 1 && <div className="dg-loc" role="group" aria-label="Xếp đánh giá">{[["moi", "Mới nhất"], ["cao", "Sao cao"], ["thap", "Sao thấp"], ["anh", "Có ảnh"]].map(([k, ten]) =>
          <button key={k} type="button" className="dg-chip cursor-interaction" aria-pressed={xep === k} disabled={busy || !nhId} onClick={() => tai(k, 1)}>{ten}</button>)}</div>}
        {x.bai.map((b: any) => <article key={b.id} className="dg-bai">
          <div className="dg-dau"><div><b>{b.ten}</b><small>{b.la_doan ? "Đoàn" : "Bàn"} {b.so_khach} người · ăn ngày {ngay(b.ngay_an)}</small></div><Sao n={b.diem} /></div>
          <span className="dg-xn">✓ Đã đến ăn · đặt qua Vietourist</span>
          {b.nhan_xet && <p>{b.nhan_xet}</p>}
          {b.anh.length > 0 && <div className="dg-anh">{b.anh.map((a: any) => <button key={a.i} type="button" className="cursor-interaction" onClick={() => setLon(a.hien)} aria-label="Xem ảnh lớn">
            <img src={a.nho} alt={`Ảnh khách chụp tại nhà hàng`} loading="lazy" /></button>)}</div>}
          {b.tra_loi && <div className="dg-tl"><b>Nhà hàng trả lời · {ngay(b.tra_loi_luc)}</b><span>{b.tra_loi}</span></div>}
        </article>)}
        {!x.bai.length && <p className="dg-phu">{xep === "anh" ? "Chưa có đánh giá kèm ảnh." : "Chưa có đánh giá. Đặt bàn qua Vietourist, dùng bữa xong bạn sẽ chấm được ở «Đặt bàn của tôi»."}</p>}
        {x.bai.length < x.tong && nhId && <button type="button" className="dg-chip cursor-interaction" disabled={busy} onClick={() => tai(xep, trang + 1)}>Xem thêm ({x.bai.length} / {x.tong})</button>}
      </div>
    </div>
    {lon && <div className="dg-hop" role="dialog" aria-modal="true" aria-label="Ảnh khách" onClick={() => setLon(null)}>
      <img src={lon} alt="Ảnh khách chụp tại nhà hàng" /><button type="button" className="cursor-interaction" onClick={() => setLon(null)} aria-label="Đóng">×</button></div>}
  </section>;
}

const CSS = `
.dg{color:#1d2b3a}
.dg-luoi{display:grid;grid-template-columns:300px minmax(0,1fr);gap:18px;align-items:start}
@media (max-width:760px){.dg-luoi{grid-template-columns:1fr}}
.dg-tong{background:#fff;border:1px solid #d6dde4;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:12px}
.dg-so{display:flex;align-items:baseline;gap:10px}.dg-so b{font-size:40px;line-height:1}
.dg-moi{font-size:18px;font-weight:600}
.dg-sao{color:#b07a10;letter-spacing:2px}.dg-sao-mo{color:#c9d3dc}
.dg-phu{font-size:13px;color:#5b6b7a}
.dg-muc{display:flex;flex-direction:column;gap:8px;font-size:14px}
.dg-thanh{display:grid;grid-template-columns:104px minmax(0,1fr) 30px;gap:8px;align-items:center}
.dg-nen{height:8px;background:#e3e9ef;border-radius:4px;overflow:hidden}.dg-nen span{display:block;height:8px;background:#b07a10}
.dg-pb{display:flex;flex-direction:column;gap:4px;font-size:13px;color:#3d4b59;border-top:1px solid #e3e9ef;padding-top:10px}
.dg-luat{background:#f6f8fa;border-radius:10px;padding:10px 12px;font-size:13px;color:#3d4b59;line-height:1.5}
.dg-ds{display:flex;flex-direction:column;gap:12px;min-width:0}
.dg-loc{display:flex;gap:8px;flex-wrap:wrap}
.dg-chip{all:unset;cursor:pointer;border:1px solid #d6dde4;background:#fff;border-radius:999px;padding:6px 14px;font-size:13px;color:#1d2b3a;align-self:flex-start}
.dg .dg-chip[aria-pressed="true"]{background:#14628c;border-color:#14628c;color:#fff}
.dg-bai{background:#fff;border:1px solid #d6dde4;border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.dg-dau{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.dg-dau small{display:block;font-size:12px;color:#5b6b7a}
.dg-xn{font-size:12px;color:#17603f;font-weight:600}
.dg-bai p{margin:0;line-height:1.6;white-space:pre-line;overflow-wrap:anywhere}
.dg-anh{display:flex;gap:8px;flex-wrap:wrap}.dg-anh button{all:unset;cursor:pointer}
.dg-anh img{width:84px;height:84px;object-fit:cover;border-radius:8px;display:block;background:#e9eef2}
.dg-tl{margin-left:14px;background:#f6f8fa;border-radius:10px;padding:10px 12px;display:flex;flex-direction:column;gap:4px;font-size:14px}
.dg-tl b{font-size:13px}
.dg-the{font-size:13px;color:#3d4b59}
.dg-hop{position:fixed;inset:0;z-index:1000;background:rgba(10,16,24,.85);display:flex;align-items:center;justify-content:center;padding:16px}
.dg-hop img{max-width:100%;max-height:90vh;border-radius:8px}
.dg-hop button{all:unset;cursor:pointer;position:absolute;top:12px;right:18px;color:#fff;font-size:32px}
.dg button:focus-visible{outline:2px solid #14628c;outline-offset:2px}
`;
