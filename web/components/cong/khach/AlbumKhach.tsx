"use client";
/* AT-2a · Album ảnh nhà hàng trên cổng khách (sau OTP) — Chủ tịch + Điều hành chốt 29/10/2026.
   Chỉ ảnh TP Điều hành đã duyệt, căn cứ quyền dùng đã xác minh; bản hiển thị nhẹ (bản gốc không ra cổng).
   Ảnh bìa lớn + 4 ảnh nhỏ; «Xem N ảnh» mở album theo nhóm; bấm ảnh để xem lớn, vuốt qua lại; chú thích dưới ảnh,
   credit chỉ hiện khi nhà hàng yêu cầu. */
import { useEffect, useRef, useState, type ReactNode } from "react";
import DanhGiaNhaHangKhach from "./DanhGiaNhaHangKhach";

type A = { id: number; nhom: string; nhom_ten: string; chu_thich: string; alt: string; credit: string; nho: string; hien: string };

/** Bố cục theo bản xem thử Điều hành 29/10/2026 («Khách hàng xem»): đầu trang (tên, nơi, «Xem album»), khảm 5 ảnh,
 *  rồi các tab Album ảnh / Giới thiệu. Không in số liệu nội bộ (hợp đồng, số ảnh trên hạn mức) ra cho khách. */
export default function AlbumKhach({ album, ten, dong2, coTab = false, gioiThieu, nhan, mon, thucDon, danhGia, nhId, oTrong }:
  { album?: A[]; ten: string; dong2?: string; coTab?: boolean; gioiThieu?: ReactNode; nhan?: ReactNode; mon?: any[]; thucDon?: any[];
    danhGia?: any; nhId?: number; oTrong?: ReactNode }) {
  const ds = album || [];
  const [mo, setMo] = useState(false);
  const [nhom, setNhom] = useState("");          // nhóm trong hộp album
  const [nhomTr, setNhomTr] = useState("");      // nhóm ở tab Album ảnh trên trang
  const mons = mon || [];
  const tds = thucDon || [];
  const [tab, setTab] = useState<"album" | "mon" | "td" | "gt" | "dg">(ds.length ? "album" : mons.length ? "mon" : tds.length ? "td" : "gt");
  const [nhomMon, setNhomMon] = useState("");
  const [loaiTd, setLoaiTd] = useState(tds[0]?.loai || "");
  const [trang, setTrang] = useState(0);
  const td = tds.find((t) => t.loai === loaiTd) || tds[0];
  const soTrang = td?.trang?.length || 0;
  const tr = soTrang ? td.trang[Math.min(trang, soTrang - 1)] : null;
  const nhomMons = Array.from(new Map(mons.map((m) => [m.nhom, m.nhom_ten])).entries());
  const [i, setI] = useState<number | null>(null);
  const cham = useRef<number | null>(null);
  const loc = ds.filter((x) => !nhom || x.nhom === nhom);
  const nhoms = Array.from(new Map(ds.map((x) => [x.nhom, x.nhom_ten])).entries()).filter(([k]) => k)
    .map(([k, t]) => [k, t, ds.filter((x) => x.nhom === k).length] as [string, string, number]).sort((a, b) => b[2] - a[2]);
  const dong = () => { if (i !== null) setI(null); else setMo(false); };
  const lui = () => setI((v) => (v === null ? v : (v - 1 + loc.length) % loc.length));
  const toi = () => setI((v) => (v === null ? v : (v + 1) % loc.length));
  useEffect(() => {
    if (!mo) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") dong(); else if (e.key === "ArrowLeft") lui(); else if (e.key === "ArrowRight") toi(); };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  });
  const moAlbum = (idx: number | null = null, n = "") => { setNhom(n); setMo(true); setI(idx); };
  const x = i !== null ? loc[i] : null;
  const [bia, ...con] = ds;
  const nho = con.slice(0, 4);
  const locTr = ds.filter((a) => !nhomTr || a.nhom === nhomTr);

  return (<div className="ab"><style>{CSS}</style>
    {dong2 !== undefined && <div className="ab-dau-trang">
      <div><div className="ab-kicker">KHÁM PHÁ ẨM THỰC VIỆT NAM</div><h2>{ten}</h2>{dong2 && <div className="ab-phu">{dong2}</div>}{nhan}</div>
      {ds.length > 0 && <button type="button" className="ab-nut cursor-interaction" onClick={() => moAlbum(null)}>Xem album</button>}</div>}

    {ds.length ? <div className={`ab-kham ${nho.length ? "" : "mot"}`}>
      <button type="button" className="ab-o ab-bia cursor-interaction" onClick={() => moAlbum(0)} aria-label={`Xem ảnh lớn: ${bia.alt || ten}`}>
        <img src={bia.hien} alt={bia.alt || ten} />{bia.credit && <small className="ab-cr">{bia.credit}</small>}
        <span className="ab-chip">Khám phá album ảnh</span></button>
      {nho.map((a, k) => <button key={a.id} type="button" className="ab-o cursor-interaction" onClick={() => moAlbum(k + 1)} aria-label={`Xem ảnh lớn: ${a.alt || a.nhom_ten}`}>
        <img src={a.nho} alt={a.alt || a.nhom_ten} loading="lazy" />
        <span className="ab-them">Xem {ds.length} ảnh</span></button>)}
    </div> : oTrong ? <div className="ab-o-trong">{oTrong}</div>
      : <div className="ab-trong" role="img" aria-label={`Chưa có ảnh ${ten}`}><span>{ten}</span><small>Nhà hàng đang bổ sung ảnh</small></div>}

    {coTab && <>
      <div className="ab-tab-trang" role="tablist" aria-label="Nội dung nhà hàng">
        {ds.length > 0 && <button type="button" role="tab" aria-selected={tab === "album"} className="cursor-interaction" onClick={() => setTab("album")}>Album ảnh</button>}
        {mons.length > 0 && <button type="button" role="tab" aria-selected={tab === "mon"} className="cursor-interaction" onClick={() => setTab("mon")}>Món ăn</button>}
        {tds.length > 0 && <button type="button" role="tab" aria-selected={tab === "td"} className="cursor-interaction" onClick={() => setTab("td")}>Thực đơn</button>}
        <button type="button" role="tab" aria-selected={tab === "gt"} className="cursor-interaction" onClick={() => setTab("gt")}>Giới thiệu</button>
        {danhGia && <button type="button" role="tab" aria-selected={tab === "dg"} className="cursor-interaction" onClick={() => setTab("dg")}>Đánh giá ({danhGia.tom_tat?.so_bai ?? 0})</button>}</div>
      {tab === "album" && ds.length > 0 && <section className="ab-muc">
        <h3>Không gian &amp; hương vị</h3><div className="ab-phu">Khám phá không gian và những món ăn gợi ý.</div>
        <div className="ab-tabs" role="group" aria-label="Nhóm ảnh">
          <button type="button" className="ab-tab cursor-interaction" aria-pressed={!nhomTr} onClick={() => setNhomTr("")}>Tất cả {ds.length}</button>
          {nhoms.map(([k, t, c]) => <button key={k} type="button" className="ab-tab cursor-interaction" aria-pressed={nhomTr === k} onClick={() => setNhomTr(k)}>{t} {c}</button>)}</div>
        <div className="ab-the-luoi">{locTr.map((a, k) => <button key={a.id} type="button" className="ab-the cursor-interaction" onClick={() => moAlbum(k, nhomTr)} aria-label={`Xem ảnh lớn: ${a.alt || a.nhom_ten}`}>
          <span className="ab-the-anh"><img src={a.hien} alt={a.alt || a.nhom_ten} loading="lazy" />{a.id === bia.id && <span className="ab-nhan">Ảnh bìa</span>}</span>
          <b>{a.chu_thich || a.nhom_ten}</b><small>{a.nhom_ten}{a.credit ? ` · ${a.credit}` : ""}</small></button>)}</div>
      </section>}
      {tab === "mon" && mons.length > 0 && <section className="ab-muc">
        <h3>Món nên thử</h3><div className="ab-phu">Ảnh và thành phần do nhà hàng cung cấp{tds.length ? ", giá xem ở tab Thực đơn" : ""}.</div>
        {nhomMons.length > 1 && <div className="ab-tabs" role="group" aria-label="Nhóm món">
          <button type="button" className="ab-tab cursor-interaction" aria-pressed={!nhomMon} onClick={() => setNhomMon("")}>Tất cả {mons.length}</button>
          {nhomMons.map(([k, t]) => <button key={k} type="button" className="ab-tab cursor-interaction" aria-pressed={nhomMon === k} onClick={() => setNhomMon(k)}>{t} {mons.filter((m) => m.nhom === k).length}</button>)}</div>}
        <div className="ab-mon-luoi">{mons.filter((m) => !nhomMon || m.nhom === nhomMon).map((m) => <article key={m.id} className="ab-mon">
          {m.anh_nho ? <img src={m.anh_nho} alt={m.ten} loading="lazy" /> : <div className="ab-mon-trong" aria-hidden="true">{m.ten}</div>}
          <div className="ab-mon-chu"><small className="ab-kicker">{(m.nhom_ten || "").toUpperCase()}</small><b>{m.ten}</b>{m.ten_khac && <small className="ab-phu">{m.ten_khac}</small>}
            {m.mo_ta && <p>{m.mo_ta}</p>}
            {(m.di_ung_ten.length > 0 || m.cay || m.chay) && <small className="ab-phu">{[m.cay ? "Cay" : "", m.chay ? "Món chay" : "", m.di_ung_ten.length ? `Có: ${m.di_ung_ten.join(", ").toLowerCase()}` : ""].filter(Boolean).join(" · ")}</small>}
            {tds.length > 0 && <button type="button" className="ab-lien cursor-interaction" onClick={() => setTab("td")}>Xem giá trong thực đơn</button>}</div></article>)}</div>
        <small className="ab-phu">Bị dị ứng thực phẩm? Hỏi lại nhà hàng trước khi gọi món — thông tin thành phần chỉ để tham khảo.</small>
      </section>}
      {tab === "td" && td && <section className="ab-muc">
        <h3>Thực đơn nhà hàng</h3><div className="ab-phu">Bản do nhà hàng gửi · {td.ban} · hiệu lực từ {td.hieu_luc_tu.split("-").reverse().join("/")}</div>
        {tds.length > 1 && <div className="ab-tabs" role="group" aria-label="Loại thực đơn">{tds.map((t) =>
          <button key={t.loai} type="button" className="ab-tab cursor-interaction" aria-pressed={td.loai === t.loai} onClick={() => { setLoaiTd(t.loai); setTrang(0); }}>{t.ten}</button>)}</div>}
        {tr && <div className="ab-td" onTouchStart={(e) => { cham.current = e.touches[0].clientX; }}
          onTouchEnd={(e) => { const d = cham.current === null ? 0 : e.changedTouches[0].clientX - cham.current; cham.current = null; if (d > 40) setTrang((v) => Math.max(0, v - 1)); else if (d < -40) setTrang((v) => Math.min(soTrang - 1, v + 1)); }}>
          <button type="button" className="ab-mui-td cursor-interaction" aria-label="Trang trước" disabled={trang === 0} onClick={() => setTrang((v) => Math.max(0, v - 1))}>‹</button>
          <a href={tr.hien} target="_blank" rel="noopener" className="ab-trang" aria-label="Mở trang thực đơn cỡ lớn"><img src={tr.hien} alt={`${td.ten} trang ${trang + 1}`} /></a>
          <button type="button" className="ab-mui-td cursor-interaction" aria-label="Trang sau" disabled={trang >= soTrang - 1} onClick={() => setTrang((v) => Math.min(soTrang - 1, v + 1))}>›</button>
        </div>}
        <div className="ab-tabs" role="group" aria-label="Trang">{td.trang.map((_t: any, i: number) => <button key={i} type="button" className="ab-tab cursor-interaction" aria-pressed={i === trang} onClick={() => setTrang(i)}>{i + 1}</button>)}</div>
        <small className="ab-phu">Trang {Math.min(trang, soTrang - 1) + 1} / {soTrang}. Giá, thuế, phí phục vụ theo nhà hàng và có thể thay đổi. Đặt bàn qua Vietourist dùng giá gói hiện ở bước đặt bàn.</small>
      </section>}
      {tab === "gt" && <section className="ab-muc">{gioiThieu}</section>}
      {tab === "dg" && danhGia && <DanhGiaNhaHangKhach dau={danhGia} nhId={nhId} />}
    </>}

    {mo && <div className="ab-hop" role="dialog" aria-modal="true" aria-label={`Ảnh ${ten}`} onClick={(e) => { if (e.target === e.currentTarget) dong(); }}>
      <div className="ab-khung">
        <div className="ab-dau"><b>{ten}</b><button type="button" className="ab-x cursor-interaction" onClick={() => setMo(false)} aria-label="Đóng album">×</button></div>
        {x ? <div className="ab-lon" onTouchStart={(e) => { cham.current = e.touches[0].clientX; }}
            onTouchEnd={(e) => { const d = cham.current === null ? 0 : e.changedTouches[0].clientX - cham.current; cham.current = null; if (d > 40) lui(); else if (d < -40) toi(); }}>
            <button type="button" className="ab-quay cursor-interaction" onClick={() => setI(null)}>← Tất cả ảnh</button>
            <figure><img src={x.hien} alt={x.alt || x.nhom_ten} />
              <figcaption>{x.chu_thich || x.nhom_ten}{x.credit && <small> · {x.credit}</small>}<span className="ab-dem">{(i ?? 0) + 1}/{loc.length}</span></figcaption></figure>
            {loc.length > 1 && <><button type="button" className="ab-mui trai cursor-interaction" onClick={lui} aria-label="Ảnh trước">‹</button>
              <button type="button" className="ab-mui phai cursor-interaction" onClick={toi} aria-label="Ảnh sau">›</button></>}
          </div>
          : <>
            <div className="ab-tabs" role="group" aria-label="Nhóm ảnh">
              <button type="button" className="ab-tab cursor-interaction" aria-pressed={!nhom} onClick={() => setNhom("")}>Tất cả {ds.length}</button>
              {nhoms.map(([k, t, c]) => <button key={k} type="button" className="ab-tab cursor-interaction" aria-pressed={nhom === k} onClick={() => setNhom(k)}>{t} {c}</button>)}</div>
            <div className="ab-luoi">{loc.map((a, k) => <button key={a.id} type="button" className="ab-o cursor-interaction" onClick={() => setI(k)} aria-label={`Xem ảnh lớn: ${a.alt || a.nhom_ten}`}>
              <img src={a.nho} alt={a.alt || a.nhom_ten} loading="lazy" /><span className="ab-ct">{a.chu_thich || a.nhom_ten}</span></button>)}</div>
            <small className="ab-goi">Bấm ảnh để xem lớn, vuốt qua lại.</small></>}
      </div></div>}
  </div>);
}

const CSS = `
.ab{min-width:0;display:flex;flex-direction:column;gap:16px;color:#1d2b3a}
.ab-dau-trang{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.ab .ab-dau-trang h2{font-size:30px!important;line-height:1.2;margin:2px 0;color:#1d2b3a!important}
.ab-kicker{font-size:12px;letter-spacing:.08em;color:#5b6b7a}
.ab-phu{font-size:13px;color:#5b6b7a}
.ab-nut{all:unset;cursor:pointer;border:1px solid #d6dde4;background:#fff;border-radius:8px;padding:9px 18px;font-weight:600;font-size:14px;color:#1d2b3a}
.ab-chip{position:absolute;left:12px;bottom:12px;background:rgba(22,34,46,.85);color:#fff;font-size:12px;padding:6px 10px;border-radius:6px}
.ab-tab-trang{display:flex;gap:22px;border-bottom:1px solid #d6dde4;overflow-x:auto}
.ab-tab-trang button{all:unset;cursor:pointer;padding:8px 0 10px;font-weight:600;font-size:15px;color:#5b6b7a;border-bottom:2px solid transparent;white-space:nowrap}
.ab .ab-tab-trang button[aria-selected="true"]{color:#14628c!important;border-bottom-color:#14628c}
.ab-muc{display:flex;flex-direction:column;gap:10px}.ab-muc h3{font-size:22px;margin:0}
.ab-the-luoi{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
@media (max-width:560px){.ab-the-luoi{grid-template-columns:1fr}}
.ab-the{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:2px;background:#fff;border:1px solid #d6dde4;border-radius:12px;overflow:hidden;padding-bottom:12px;min-width:0}
.ab-the b,.ab-the small{padding:0 12px}.ab-the b{margin-top:10px;font-size:15px}.ab-the small{color:#5b6b7a}
.ab-the-anh{position:relative;display:block;aspect-ratio:16/9;background:#e9eef2}.ab-the-anh img{width:100%;height:100%;object-fit:cover;display:block}
.ab-mon-luoi{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
@media (max-width:900px){.ab-mon-luoi{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){.ab-mon-luoi{grid-template-columns:1fr}}
.ab-mon{background:#fff;border:1px solid #d6dde4;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.ab-mon img,.ab-mon-trong{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;background:#e9eef2}
.ab-mon-trong{display:grid;place-items:center;color:#5b6b7a;font-size:13px}
.ab-mon-chu{padding:12px 14px;display:flex;flex-direction:column;gap:4px}.ab-mon-chu b{font-size:16px}.ab-mon-chu p{margin:0;font-size:13px;color:#3d4b59}
.ab-lien{all:unset;cursor:pointer;color:#14628c;font-weight:600;font-size:13px;margin-top:4px}
.ab-td{display:flex;align-items:center;gap:12px;justify-content:center}
.ab-trang{display:block;width:min(520px,100%);background:#fffdf8;border:1px solid #d6dde4;border-radius:10px;box-shadow:0 4px 14px rgba(20,30,40,.1);overflow:hidden}
.ab-trang img{width:100%;display:block}
.ab-mui-td{all:unset;cursor:pointer;flex:none;width:44px;height:44px;border-radius:50%;border:1px solid #d6dde4;background:#fff;display:grid;place-items:center;font-size:22px;color:#1d2b3a}
.ab-mui-td:disabled{opacity:.35;cursor:default}
@media (max-width:560px){.ab-mui-td{display:none}}
.ab-nhan{position:absolute;left:10px;top:10px;background:rgba(22,34,46,.85);color:#fff;font-size:12px;padding:3px 8px;border-radius:6px}
.ab-kham{display:grid;grid-template-columns:2fr 1fr 1fr;grid-template-rows:repeat(2,minmax(0,1fr));gap:6px;aspect-ratio:16/9;border-radius:12px;overflow:hidden}
.ab-kham.mot{grid-template-columns:1fr;grid-template-rows:minmax(0,1fr);aspect-ratio:4/3}
.ab-o{all:unset;position:relative;cursor:pointer;min-width:0;min-height:0;background:#e9eef2;display:block;overflow:hidden}
.ab-o img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.ab-bia{grid-row:span 2}
.ab-kham .ab-o:last-child .ab-them{display:grid}
.ab-them{position:absolute;inset:0;display:none;place-items:center;background:rgba(0,0,0,.45);color:#fff;font-weight:600;font-size:14px}
.ab-cr{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.5);color:#fff;font-size:11px;padding:1px 6px;border-radius:4px}
.ab-trong{aspect-ratio:4/3;border-radius:12px;background:#e9eef2;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;color:#5b6b7a;text-align:center;padding:8px}
.ab-trong small{font-size:12px}
.ab-o-trong{max-width:560px;width:100%}
@media (max-width:560px){.ab-kham{grid-template-columns:1fr 1fr;grid-template-rows:minmax(0,2fr) minmax(0,1fr);aspect-ratio:4/3}.ab-bia{grid-column:span 2;grid-row:auto}
  .ab-kham .ab-o:nth-child(n+4){display:none}.ab-kham .ab-o .ab-them{display:none}
  .ab-kham .ab-o:nth-child(3) .ab-them,.ab-kham .ab-o:nth-child(2):last-child .ab-them{display:grid}}
.ab-hop{position:fixed;inset:0;z-index:1000;background:rgba(10,16,24,.82);display:flex;align-items:center;justify-content:center;padding:16px}
.ab-khung{background:#fff;color:#16222e;border-radius:12px;width:min(1100px,100%);max-height:100%;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
.ab-dau{display:flex;justify-content:space-between;align-items:center;gap:10px}
.ab-x{all:unset;cursor:pointer;font-size:26px;line-height:1;padding:0 6px}
.ab-tabs{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px}
.ab-tab{white-space:nowrap;border:1px solid #d6dde4;background:#fff;border-radius:999px;padding:6px 14px;font-size:14px;color:#16222e;cursor:pointer}
.ab .ab-tab[aria-pressed="true"]{background:#0f8c7e;border-color:#0f8c7e;color:#fff!important}
.ab-luoi{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.ab-luoi .ab-o{aspect-ratio:4/3;border-radius:8px}
.ab-ct{position:absolute;left:0;right:0;bottom:0;background:linear-gradient(transparent,rgba(0,0,0,.6));color:#fff;font-size:12px;padding:14px 6px 4px}
.ab-goi{color:#5b6b7a}
.ab-lon{position:relative;display:flex;flex-direction:column;gap:6px}
.ab-quay{all:unset;cursor:pointer;color:#0f8c7e;font-weight:600;font-size:14px}
.ab-lon figure{margin:0;display:flex;flex-direction:column;gap:6px}
.ab-lon img{width:100%;max-height:70vh;object-fit:contain;background:#0d141b;border-radius:8px}
.ab-lon figcaption{font-size:14px;display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}.ab-lon figcaption small{color:#5b6b7a}
.ab-dem{margin-left:auto;color:#5b6b7a;font-size:13px;font-variant-numeric:tabular-nums}
.ab-mui{all:unset;cursor:pointer;position:absolute;top:45%;width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.9);display:grid;place-items:center;font-size:26px;box-shadow:0 1px 4px rgba(0,0,0,.25)}
.ab-mui.trai{left:8px}.ab-mui.phai{right:8px}
.ab button:focus-visible{outline:2px solid #0f8c7e;outline-offset:2px}
`;
