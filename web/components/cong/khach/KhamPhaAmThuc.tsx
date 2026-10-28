"use client";
/* AT-1c · «Hương vị Việt Nam» — trang Khám phá ẩm thực (Chủ tịch duyệt bản xem thử AT-1c, 28/10/2026).
   Bố cục theo trang quốc gia của TasteAtlas (ảnh bìa, mục lục dính, thành phố, món theo nhóm, đặc sản, danh sách,
   nhà hàng, bản đồ), màu và chữ VTD. Chữ, ảnh là của VTD (Marketing biên tập trong VTOS, ảnh ghi nguồn).
   Đặt bàn giữ như cũ: chỉ nơi đã ký hợp đồng (máy tính đủ 5 điều kiện) mới có nút «Đặt bàn qua Vietourist · tích
   điểm» → màn đặt bàn sẵn có. Xem sau khi nhận mã OTP qua Zalo / email (Chủ tịch chốt 28/10/2026: không tạo tài
   khoản, không mật khẩu) — dùng chung cho cổng khách / cổ đông / đối tác. Ảnh tải qua cửa /api/v1/am-thuc/anh. */
import { useCallback, useEffect, useMemo, useState } from "react";
import { goiCong } from "@/lib/cong";
import AlbumKhach from "./AlbumKhach";
import { BD_W, BD_H, BD_VN, BD_LANG_GIENG, BD_TP, BD_HOANG_SA, BD_TRUONG_SA, BD_NHAN_HS, BD_NHAN_TS } from "./banDoVN";

const tien = (n?: number | null) => (n || n === 0 ? `${Math.round(n).toLocaleString("vi-VN")} đ` : "—");
const NHAN: Record<string, [number, number, "start" | "end"]> = {
  "Hà Nội": [-4, -6, "end"], "TP. Hồ Chí Minh": [6, 3, "start"], "Huế": [-5, 3, "end"], "Đà Nẵng": [6, -1, "start"], "Hội An": [6, 6, "start"],
  "Sa Pa": [-4, 3, "end"], "Hạ Long": [5, -3, "start"], "Đà Lạt": [-5, 3, "end"], "Nha Trang": [5, 3, "start"], "Phú Quốc": [-4, 3, "end"],
  "Cần Thơ": [-4, 6, "end"], "Pleiku": [-5, 3, "end"], "Quy Nhơn": [5, 3, "start"], "Đồng Hới": [5, 2, "start"], "Côn Đảo": [5, 3, "start"], "Vinh": [-5, 3, "end"],
};

function Anh({ src, nguon, ten, tl = "1/1", cls = "" }: { src?: string | null; nguon?: string; ten: string; tl?: string; cls?: string }) {
  return (<div className={`at-anh ${cls}`} style={{ aspectRatio: tl }}>
    {src ? <img src={src} alt={ten} loading="lazy" /> : <span className="at-anh-trong">{ten}</span>}
    {src && nguon && <small className="at-nguon">{nguon}</small>}
  </div>);
}

const Ghim = () => <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" /></svg>;

type Loc = { tinh: string; q: string; chi_dat: string; trang: string };

export default function KhamPhaAmThuc({ onDat }: { onDat: (n: any) => void }) {
  const [ds, setDs] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [loc, setLoc] = useState<Loc>({ tinh: "", q: "", chi_dat: "", trang: "1" });
  const [mien, setMien] = useState("");
  const [nhom, setNhom] = useState("");
  const [moMon, setMoMon] = useState(12);
  const [mon, setMon] = useState<any>(null);       // trang một món / đặc sản
  const [nh, setNh] = useState<any>(null);         // trang giới thiệu nhà hàng
  const tai = useCallback((l: Loc) => {
    const q = new URLSearchParams(Object.entries(l).filter(([k, v]) => v && !(k === "trang" && v === "1")) as any).toString();
    goiCong(`/dat-ban/nha-hang${q ? `?${q}` : ""}`).then(setDs).catch((x) => setLoi(x.message));
  }, []);
  useEffect(() => { tai(loc); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const doi = (them: Partial<Loc>) => { const l = { ...loc, trang: "1", ...them }; setLoc(l); tai(l); };
  const xemNh = async (id: number) => {
    try { const o = await goiCong(`/dat-ban/nha-hang/${id}`); if (o.mo_dat) onDat(o); else { setNh(o); setMon(null); window.scrollTo(0, 0); } }
    catch (x: any) { setLoi(x.message); }
  };
  const nd = ds?.noi_dung || [];
  const bia = nd.find((x: any) => x.loai === "bia");
  const mons = useMemo(() => nd.filter((x: any) => x.loai === "mon" && (!nhom || x.nhom === nhom)), [nd, nhom]);
  const nhomCo = useMemo(() => Array.from(new Set(nd.filter((x: any) => x.loai === "mon").map((x: any) => x.nhom).filter(Boolean))) as string[], [nd]);
  const dacSan = nd.filter((x: any) => x.loai === "dac_san");
  const dsGoiY = nd.filter((x: any) => x.loai === "danh_sach");
  const tps = (ds?.thanh_pho || []).filter((t: any) => !mien || t.mien_ten === mien);
  const soTrang = ds ? Math.max(1, Math.ceil((ds.tong || 0) / (ds.so || 24))) : 1;
  const dem: Record<string, number> = ds?.dem_tinh || {};

  if (!ds) return <section className="v3-panel"><p>{loi || "Đang tải…"}</p></section>;

  if (mon) return (<div className="at"><style>{CSS}</style>
    <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setMon(null)}><span>← Hương vị Việt Nam</span></button>
    <section className="at-mon">
      <Anh src={mon.anh} nguon={mon.anh_nguon} ten={mon.ten} tl="4/3" cls="at-bo" />
      <div className="at-mon-chu">
        <div className="at-loai">{[mon.nhom || mon.loai_ten, mon.tinh_thanh].filter(Boolean).join(" · ")}</div>
        <div><h2>{mon.ten}</h2>{mon.ten_khac && <div className="at-phu">{mon.ten_khac}</div>}</div>
        {mon.noi_dung ? <p style={{ whiteSpace: "pre-line" }}>{mon.noi_dung}</p> : mon.tom_tat && <p>{mon.tom_tat}</p>}
        {(mon.vung || mon.nen_an || mon.thanh_phan || mon.cach_goi) && <dl className="at-facts">
          {mon.vung && <><dt>Vùng</dt><dd>{mon.vung}</dd></>}{mon.nen_an && <><dt>Nên ăn</dt><dd>{mon.nen_an}</dd></>}
          {mon.thanh_phan && <><dt>Thành phần chính</dt><dd>{mon.thanh_phan}</dd></>}{mon.cach_goi && <><dt>Cách gọi</dt><dd>{mon.cach_goi}</dd></>}</dl>}
        {mon.an_o_dau?.length > 0 && <><h3>Ăn ở đâu</h3><div className="at-an">{mon.an_o_dau.map((a: any) => <div key={a.id}>
          <span><b>{a.ten}</b>{a.khu_vuc || a.tinh_thanh ? ` · ${[a.khu_vuc, a.tinh_thanh].filter(Boolean).join(", ")}` : ""}</span>
          {a.mo_dat ? <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => xemNh(a.id)}><span>Đặt bàn qua Vietourist · tích điểm</span></button>
            : <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => xemNh(a.id)}><span>Xem nhà hàng</span></button>}</div>)}</div></>}
      </div>
    </section>
  </div>);

  if (nh) return (<div className="at"><style>{CSS}</style>
    <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => setNh(null)}><span>← Hương vị Việt Nam</span></button>
    <AlbumKhach album={nh.album} ten={nh.ten} coTab
      dong2={[[nh.khu_vuc, nh.tinh_thanh].filter(Boolean).join(", ") || nh.dia_danh_nguon, nh.am_thuc ? `Ẩm thực ${nh.am_thuc}` : ""].filter(Boolean).join(" · ")}
      nhan={<div style={{ marginTop: 8 }}><span className="at-chua">Chưa mở đặt bàn qua Vietourist</span></div>}
      gioiThieu={<div className="at-mon-chu at-the-gt">
        <h3>Câu chuyện nhà hàng</h3>
        {nh.mon_noi_bat && <p><b>Nổi tiếng với:</b> {nh.mon_noi_bat}</p>}
        <p>{nh.mo_ta || "Vietourist đang biên tập phần giới thiệu nhà hàng này."}</p>
        <dl className="at-facts"><dt>Giờ mở cửa</dt><dd>{nh.gio_phuc_vu || "Đang cập nhật"}</dd><dt>Giá, thực đơn</dt><dd>Đang cập nhật</dd>
          <dt>Thông tin liên hệ</dt><dd>{nh.da_xac_minh ? "Vietourist đã xác minh" : "Đang xác minh"}</dd></dl>
        <small className="at-phu">Nhà hàng chưa ký hợp tác với Vietourist. Thông tin có thể đã thay đổi — Vietourist đang cập nhật.</small>
      </div>} />
  </div>);

  const muc = [["at-tp", "Thành phố ẩm thực"], ["at-mon", "Món ăn Việt Nam", mons.length || nd.some((x: any) => x.loai === "mon")],
    ["at-ds", "Đặc sản mang về", dacSan.length], ["at-goiy", "Danh sách gợi ý", dsGoiY.length], ["at-nh", "Nhà hàng"], ["at-bd", "Bản đồ ẩm thực"]]
    .filter((m) => m[2] === undefined || m[2]) as [string, string][];
  const tong = ds.tong_nha_hang ?? ds.tong;

  return (<div className="at">
    <style>{CSS}</style>
    <header className="at-bia">
      {bia?.anh ? <img src={bia.anh} alt="" /> : <span className="at-bia-nen" />}
      <div className="at-bia-chu">
        <div className="at-crumb">VTD › Ẩm thực › Việt Nam</div>
        <h1><span className="at-co" aria-hidden="true"><svg viewBox="0 0 24 24"><path fill="#ffde00" d="M12 3l2.6 6.3 6.8.5-5.2 4.4 1.6 6.6L12 17.3l-5.8 3.5 1.6-6.6L2.6 9.8l6.8-.5z" /></svg></span>{bia?.ten || "Hương vị Việt Nam"}</h1>
        <div className="at-so"><span>{tong} nhà hàng</span><span>{(ds.thanh_pho || []).length} thành phố</span>{ds.so_mo_dat > 0 && <span>{ds.so_mo_dat} nơi đặt bàn qua Vietourist · tích điểm</span>}</div>
      </div>
      {bia?.anh && bia.anh_nguon && <small className="at-nguon">{bia.anh_nguon}</small>}
    </header>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}

    <div className="at-than">
      <aside className="at-muc" aria-label="Mục lục"><h3>Mục lục</h3>{muc.map(([id, t]) => <a key={id} href={`#${id}`}>{t}</a>)}</aside>
      <div className="at-noi">
        <p className="at-dan">{bia?.tom_tat || "Mỗi vùng một khẩu vị: miền Bắc thanh, miền Trung đậm cay, miền Nam ngọt và nhiều rau. Chọn món muốn ăn, xem nơi nấu ngon, và đặt bàn ở những nhà hàng hợp tác với Vietourist để tích điểm thành viên."}</p>

        <section className="at-khoi" id="at-tp">
          <h2>Thành phố ẩm thực</h2>
          <div className="at-tabs" role="group" aria-label="Miền">
            {[["", `Tất cả ${(ds.thanh_pho || []).length}`], ...Object.values(ds.mien || {}).map((m: any) => [m, m])].map(([k, t]) =>
              <button key={k} type="button" className="at-tab cursor-interaction" aria-pressed={mien === k} onClick={() => setMien(k)}>{t}</button>)}
          </div>
          <div className="at-luoi-tp">{tps.map((t: any) => <button key={t.ten} type="button" className="at-tp cursor-interaction" onClick={() => { doi({ tinh: t.ten }); document.getElementById("at-nh")?.scrollIntoView(); }}>
            <Anh src={t.anh} ten={t.ten} tl="3/4" /><b>{t.ten}</b><small>{[t.so_nha_hang ? `${t.so_nha_hang} nhà hàng` : "", t.tom_tat].filter(Boolean).join(" · ") || " "}</small></button>)}</div>
        </section>

        {muc.some(([id]) => id === "at-mon") && <section className="at-khoi" id="at-mon">
          <h2>Món ăn Việt Nam</h2>
          {nhomCo.length > 0 && <div className="at-tabs" role="group" aria-label="Nhóm món">
            {["", ...nhomCo].map((g) => <button key={g} type="button" className="at-tab cursor-interaction" aria-pressed={nhom === g} onClick={() => { setNhom(g); setMoMon(12); }}>{g || "Phải thử"}</button>)}</div>}
          <div className="at-luoi">{mons.slice(0, moMon).map((x: any) => <article key={x.id} className="at-the">
            <button type="button" className="at-the-anh cursor-interaction" onClick={() => { setMon(x); window.scrollTo(0, 0); }} aria-label={`Xem ${x.ten}`}><Anh src={x.anh} nguon={x.anh_nguon} ten={x.ten} /></button>
            <div className="at-loai">{x.nhom || "Món ăn"}</div><h3>{x.ten}{x.ten_khac && <em> ({x.ten_khac})</em>}</h3>
            {x.tinh_thanh && <div className="at-noi-o"><span className="at-ghim"><Ghim /></span>{x.tinh_thanh}</div>}
            {x.an_o_dau?.[0] && <div className="at-phu">Ngon nhất tại <b>{x.an_o_dau[0].ten}</b></div>}
            {x.an_o_dau?.some((a: any) => a.mo_dat) && <span className="at-vtd">★ Đặt qua Vietourist · tích điểm</span>}
          </article>)}</div>
          {mons.length > moMon && <button type="button" className="at-them cursor-interaction" onClick={() => setMoMon(moMon + 12)}>Xem thêm</button>}
        </section>}

        {dacSan.length > 0 && <section className="at-khoi" id="at-ds"><h2>Đặc sản mang về</h2>
          <div className="at-luoi">{dacSan.map((x: any) => <article key={x.id} className="at-the">
            <button type="button" className="at-the-anh cursor-interaction" onClick={() => { setMon(x); window.scrollTo(0, 0); }} aria-label={`Xem ${x.ten}`}><Anh src={x.anh} nguon={x.anh_nguon} ten={x.ten} /></button>
            <div className="at-loai">{x.nhom || "Đặc sản"}</div><h3>{x.ten}</h3>{x.tinh_thanh && <div className="at-noi-o"><span className="at-ghim"><Ghim /></span>{x.tinh_thanh}</div>}</article>)}</div></section>}

        {dsGoiY.length > 0 && <section className="at-khoi" id="at-goiy"><h2>Danh sách gợi ý</h2>
          <div className="at-luoi3">{dsGoiY.map((x: any) => <button key={x.id} type="button" className="at-goiy cursor-interaction" onClick={() => { setMon(x); window.scrollTo(0, 0); }}>
            <Anh src={x.anh} nguon={x.anh_nguon} ten={x.ten} tl="16/10" /><b>{x.ten}</b>{x.tom_tat && <small>{x.tom_tat}</small>}</button>)}</div></section>}

        <section className="at-khoi" id="at-nh">
          <h2>Nhà hàng{loc.tinh ? ` ở ${loc.tinh}` : ""}</h2>
          <div className="at-tim"><input type="search" aria-label="Tìm nhà hàng, món" placeholder="Tìm món, nhà hàng…" value={loc.q}
            onChange={(e) => setLoc({ ...loc, q: e.target.value })} onKeyDown={(e) => { if (e.key === "Enter") doi({}); }} />
            <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => doi({})}><span>Tìm</span></button>
            <label className="at-chk"><input type="checkbox" checked={loc.chi_dat === "true"} onChange={(e) => doi({ chi_dat: e.target.checked ? "true" : "" })} />Chỉ nơi đặt qua Vietourist</label></div>
          <div className="at-tabs" role="group" aria-label="Thành phố">
            <button type="button" className="at-tab cursor-interaction" aria-pressed={!loc.tinh} onClick={() => doi({ tinh: "" })}>Tất cả {tong}</button>
            {Object.entries(dem).sort((a, b) => b[1] - a[1]).map(([t, c]) => <button key={t} type="button" className="at-tab cursor-interaction" aria-pressed={loc.tinh === t} onClick={() => doi({ tinh: t })}>{t} {c}</button>)}</div>
          <div className="at-luoi">{ds.nha_hang.map((n: any) => <article key={n.id} className="at-the">
            <button type="button" className="at-the-anh cursor-interaction" onClick={() => xemNh(n.id)} aria-label={`Xem ${n.ten}`}><Anh src={n.anh_nho || n.anh} nguon={n.anh_nguon} ten={n.ten} tl="4/3" /></button>
            <h3>{n.ten}</h3><div className="at-noi-o"><span className="at-ghim"><Ghim /></span>{[n.khu_vuc, n.tinh_thanh].filter(Boolean).join(", ") || n.dia_danh_nguon}</div>
            {n.mon_noi_bat && <div className="at-phu">Nổi tiếng với: <b>{n.mon_noi_bat}</b></div>}
            {n.mo_dat ? <><span className="at-vtd">★ Đặt qua Vietourist · tích điểm</span><div className="at-phu">Thực đơn từ <b>{tien(n.gia_tu)}</b>/người</div>
              <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => xemNh(n.id)}><span>Đặt bàn qua Vietourist</span></button></>
              : <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => xemNh(n.id)}><span>Xem nhà hàng</span></button>}
          </article>)}</div>
          {!ds.nha_hang.length && <p className="at-phu">Chưa có nhà hàng{loc.tinh || loc.q || loc.chi_dat ? " khớp bộ lọc" : ""}. Vietourist đang bổ sung danh mục.</p>}
          {soTrang > 1 && <div className="at-trang">
            <button type="button" className="v3-button v3-quiet cursor-interaction" disabled={ds.trang <= 1} onClick={() => doi({ trang: String(ds.trang - 1) })}><span>‹ Trước</span></button>
            <span>Trang {ds.trang}/{soTrang} · {ds.tong} kết quả</span>
            <button type="button" className="v3-button v3-quiet cursor-interaction" disabled={ds.trang >= soTrang} onClick={() => doi({ trang: String(ds.trang + 1) })}><span>Sau ›</span></button></div>}
        </section>

        <section className="at-khoi" id="at-bd">
          <h2>Bản đồ ẩm thực</h2>
          <div className="at-bd">
            <svg className="at-vn" viewBox={`0 0 ${BD_W} ${BD_H}`} role="img" aria-label="Bản đồ Việt Nam: thành phố ẩm thực, quần đảo Hoàng Sa và Trường Sa">
              <path className="nb" d={BD_LANG_GIENG} /><path className="vn" d={BD_VN} />
              <g className="isl">{[...BD_HOANG_SA, ...BD_TRUONG_SA].map(([x, y], i) => <circle key={i} cx={x} cy={y} r={1.1} />)}</g>
              <text className="isl-l" x={BD_NHAN_HS[0]} y={BD_NHAN_HS[1]} textAnchor="middle">QĐ. Hoàng Sa</text>
              <text className="isl-l" x={BD_NHAN_TS[0]} y={BD_NHAN_TS[1]} textAnchor="middle">QĐ. Trường Sa</text>
              <text className="sea" x={BD_W * 0.76} y={BD_H * 0.66} textAnchor="middle">Biển Đông</text>
              {Object.entries(BD_TP).map(([t, [x, y]]) => {
                const c = dem[t] || 0; const l = NHAN[t];
                return (<g key={t} className="tp" role="button" tabIndex={0} aria-label={`${t}${c ? `, ${c} nhà hàng` : ""}`}
                  onClick={() => { doi({ tinh: t }); document.getElementById("at-nh")?.scrollIntoView(); }}
                  onKeyDown={(e) => { if (e.key === "Enter") { doi({ tinh: t }); document.getElementById("at-nh")?.scrollIntoView(); } }}>
                  <title>{t}{c ? ` · ${c} nhà hàng` : ""}</title>
                  <circle cx={x} cy={y} r={c ? 2.2 + Math.sqrt(c) * 0.75 : 2} />
                  {(l || c > 0) && <text x={x + (l ? l[0] : 5)} y={y + (l ? l[1] : 3)} textAnchor={l ? l[2] : "start"}>{t}{c ? ` ${c}` : ""}</text>}</g>);
              })}
            </svg>
            <div className="at-chu-bd">{Object.entries(dem).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([t, c]) =>
              <button key={t} type="button" className="cursor-interaction" onClick={() => { doi({ tinh: t }); document.getElementById("at-nh")?.scrollIntoView(); }}><span>{t}</span><b>{c}</b></button>)}
              <small className="at-phu">Bấm một thành phố để xem nhà hàng. Bản đồ vẽ từ dữ liệu địa lý Natural Earth, có quần đảo Hoàng Sa và Trường Sa của Việt Nam.</small></div>
          </div>
        </section>
      </div>
    </div>
  </div>);
}

const CSS = `
.at{display:flex;flex-direction:column;gap:16px;--at-ink:var(--v3-ink,#162d47);--at-muted:var(--v3-muted,#566a80);--at-line:var(--v3-line,#e0e7ee);
  --at-teal:#147866;--at-tint:#e7f4ef;--at-gold:#a8783c;--at-gold-tint:#f6eddf;--at-slot:#e3e8ee;--at-sea:#e3eef7;--at-land:#eef1f4;--at-pin:#e0405f}
.at h1,.at h2,.at h3{text-wrap:balance;margin:0}
.at-bia{position:relative;min-height:240px;border-radius:14px;overflow:hidden;display:flex;align-items:flex-end;color:#fff;background:linear-gradient(160deg,#0b2c49,#081826)}
.at-bia img,.at-bia-nen{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.at-bia-nen{background:radial-gradient(90% 80% at 10% 100%,rgba(20,120,102,.7),transparent 60%),radial-gradient(120% 90% at 85% 10%,rgba(183,139,79,.5),transparent 55%)}
.at-bia::after{content:"";position:absolute;inset:0;background:linear-gradient(transparent 35%,rgba(8,24,38,.8))}
.at-bia-chu{position:relative;z-index:1;padding:20px 22px}
.at-crumb{font-size:13px;opacity:.85;margin-bottom:6px}
.at .at-bia h1{font-size:clamp(28px,4.4vw,46px);font-weight:600;display:flex;gap:12px;align-items:center;color:#fff!important}
.at-co{width:34px;height:34px;border-radius:50%;background:#da251d;display:grid;place-items:center;flex:none}.at-co svg{width:18px;height:18px}
.at-so{display:flex;gap:14px;flex-wrap:wrap;font-size:14px;opacity:.92;margin-top:6px}
.at-nguon{position:absolute;right:8px;bottom:6px;z-index:1;font-size:10px;color:#fff;background:rgba(8,24,38,.55);padding:1px 6px;border-radius:4px}
.at-than{display:grid;grid-template-columns:200px minmax(0,1fr);gap:28px}
.at-muc{position:sticky;top:12px;align-self:start;font-size:14px;display:flex;flex-direction:column;gap:4px}
.at-muc h3{font-size:15px;margin-bottom:6px}
.at-muc a{padding:4px 0 4px 12px;border-left:3px solid var(--at-teal);color:var(--at-muted);text-decoration:none}
.at-muc a:hover{color:var(--at-ink)}
.at-noi{min-width:0}
.at-dan{color:var(--at-muted);max-width:72ch;margin:0 0 20px}
.at-khoi{display:flex;flex-direction:column;gap:14px;padding-bottom:28px;margin-bottom:28px;border-bottom:1px solid var(--at-line);scroll-margin-top:12px}
.at-khoi:last-child{border-bottom:0}
.at-khoi h2{font-size:24px;font-weight:600}
.at-tabs{display:flex;gap:8px;overflow-x:auto;padding-bottom:2px}
.at-tab{white-space:nowrap;border:1px solid var(--at-line);background:#fff;border-radius:999px;padding:6px 14px;font-size:14px;color:var(--at-ink)}
.at .at-tab[aria-pressed="true"]{background:var(--at-teal);border-color:var(--at-teal);color:#fff!important}
.at-anh{position:relative;width:100%;max-width:100%;border-radius:10px;overflow:hidden;background:var(--at-slot);display:grid;place-items:center}
.at-anh img{width:100%;height:100%;object-fit:cover;display:block}
.at-anh-trong{font-size:12px;color:var(--at-muted);padding:8px;text-align:center}
.at-luoi-tp{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:14px}
@media (max-width:560px){.at-luoi-tp{grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.at-tp b{font-size:13px}}
.at-tp{all:unset;display:flex;flex-direction:column;gap:4px;cursor:pointer;min-width:0}
.at-tp b{font-size:15px}.at-tp small{color:var(--at-muted);font-size:12px}
.at-luoi{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px 16px}
.at-luoi3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.at-the{display:flex;flex-direction:column;gap:4px;min-width:0}
.at-the-anh{all:unset;cursor:pointer;margin-bottom:6px;display:block}
.at-the h3{font-size:16px;font-weight:600;line-height:1.3}.at-the h3 em{font-style:normal;color:var(--at-muted);font-weight:500}
.at-the .v3-button{margin-top:6px;align-self:flex-start}
.at-loai{font-size:13px;color:var(--at-muted);display:flex;align-items:center;gap:4px}
.at-noi-o{display:flex;gap:4px;align-items:center;font-size:13px;font-weight:600}
.at-ghim{width:13px;height:13px;color:var(--at-pin);display:inline-flex}.at-ghim svg{width:13px;height:13px}
.at-phu{font-size:13px;color:var(--at-muted)}.at-phu b{color:var(--at-ink)}
.at-vtd{font-size:12px;font-weight:600;color:var(--at-gold);background:var(--at-gold-tint);border-radius:999px;padding:2px 9px;width:max-content;max-width:100%}
.at-chua{font-size:12px;font-weight:600;color:var(--at-muted);border:1px solid var(--at-line);border-radius:999px;padding:2px 9px;width:max-content}
.at-them{align-self:center;border:1px solid var(--at-line);background:#fff;border-radius:999px;padding:9px 32px;font-weight:600;cursor:pointer}
.at-goiy{all:unset;display:flex;flex-direction:column;gap:6px;cursor:pointer;min-width:0}.at-goiy small{color:var(--at-muted)}
.at-tim{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.at .at-tim input[type=search]{flex:1 1 220px;min-width:0;border:1px solid var(--at-line);border-radius:999px;padding:8px 14px;font-size:14px;background:#fff;color:var(--at-ink)}
.at-chk{display:flex;gap:6px;align-items:center;font-size:14px}
.at-trang{display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap}
.at-bd{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:20px;align-items:center;border:1px solid var(--at-line);border-radius:12px;padding:14px;background:#fff}
.at-vn{width:100%;height:auto;background:var(--at-sea);border-radius:10px}
.at-vn .nb{fill:var(--at-land);stroke:#d3dae2;stroke-width:.4}
.at-vn .vn{fill:var(--at-tint);stroke:var(--at-teal);stroke-width:.8;stroke-linejoin:round}
.at-vn .isl circle{fill:var(--at-teal)}
.at-vn .isl-l{font-size:6.5px;font-weight:600;fill:var(--at-ink)}
.at-vn .sea{font-size:8px;font-style:italic;fill:var(--at-muted);letter-spacing:.1em}
.at-vn .tp{cursor:pointer;outline:none}.at-vn .tp circle{fill:var(--at-teal);stroke:#fff;stroke-width:.6}
.at-vn .tp:hover circle,.at-vn .tp:focus circle{fill:var(--at-gold)}
.at-vn .tp text{font-size:6px;font-weight:600;fill:var(--at-ink);paint-order:stroke;stroke:var(--at-tint);stroke-width:1.6px}
.at-chu-bd{display:flex;flex-direction:column;gap:6px;font-size:14px;font-variant-numeric:tabular-nums}
.at-chu-bd button{all:unset;cursor:pointer;display:flex;justify-content:space-between;border-bottom:1px dashed var(--at-line);padding-bottom:4px}
.at-mon{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:26px}
.at-mon-chu{display:flex;flex-direction:column;gap:12px;min-width:0}.at-mon-chu h2{font-size:30px}.at-mon-chu p{margin:0;max-width:62ch}
.at-mon-chu h3{font-size:16px}
.at-facts{display:grid;grid-template-columns:auto 1fr;gap:6px 16px;font-size:14px;margin:0}.at-facts dt{color:var(--at-muted)}.at-facts dd{margin:0}
.at-the-gt{background:#fff;border:1px solid var(--at-line);border-radius:12px;padding:18px}
.at-an{display:flex;flex-direction:column;gap:8px}
.at-an>div{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 12px;border:1px solid var(--at-line);border-radius:10px}
.at button:focus-visible,.at a:focus-visible{outline:2px solid var(--at-teal);outline-offset:2px}
@media (max-width:920px){.at-than{grid-template-columns:1fr}.at-muc{display:none}.at-luoi{grid-template-columns:repeat(2,minmax(0,1fr))}
  .at-luoi3,.at-mon,.at-bd{grid-template-columns:1fr}}
`;
