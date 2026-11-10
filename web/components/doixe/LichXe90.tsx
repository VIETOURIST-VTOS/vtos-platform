"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** VH-9 · LỊCH XE 90 NGÀY TỚI (Chủ tịch duyệt bản xem trước 11/11/2026).
 *
 *  Bốn thẻ số · lưới xe × ngày · khoảng trống để bán · công suất theo tuần. Mọi số do máy chủ tính
 *  (`/fleet/lich-xe-tuong-lai`), màn này chỉ vẽ. «Giữ xe cho tour» mở mẫu đề nghị xe với sẵn ngày đi / về —
 *  đề nghị vẫn đi qua Điều hành như luồng hiện có, nên xe không bị bán trùng. */
type Mo = (toi: string) => void;
const dd = (s: string) => s.slice(8, 10) + "/" + s.slice(5, 7);
const MAU: Record<string, string> = { lenh: "#2c5fa2", chan: "#c2475d", "": "#fff" };

export default function LichXe90({ mo }: { mo: Mo }) {
  const [soNgay, setSoNgay] = useState(90);
  const [cho, setCho] = useState(0);
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  useEffect(() => { setD(null); api(`/fleet/lich-xe-tuong-lai?so_ngay=${soNgay}`).then(setD).catch((e) => setLoi(String(e?.message || e))); }, [soNgay]);
  if (!d) return loi ? <p className="muted">Không đọc được lịch: {loi}</p>
    : <div className="xe-cho" aria-busy="true" aria-label="Đang đọc lịch xe"><i /><i /><i /><i /></div>;
  const loaiCho = Array.from(new Set<number>(d.xe.map((x: any) => x.so_cho))).sort((a, b) => a - b);
  const xe = d.xe.filter((x: any) => !cho || x.so_cho === cho);
  const kt = d.khoang_trong.filter((k: any) => !cho || k.so_cho === cho).slice(0, 12);
  const ngay: string[] = d.ngay;
  const pc = (v: number | null) => (v == null ? "—" : `${v}%`);
  return <>
    <div className="xe-dau-con"><h2 style={{ margin: 0 }}>Lịch xe {soNgay} ngày tới</h2>
      <div className="lx-chips">
        {[30, 60, 90].map((n) => <button key={n} type="button" aria-pressed={soNgay === n} onClick={() => setSoNgay(n)}>{n} ngày</button>)}
        <span className="lx-gach" />
        <button type="button" aria-pressed={!cho} onClick={() => setCho(0)}>Tất cả</button>
        {loaiCho.map((c) => <button key={c} type="button" aria-pressed={cho === c} onClick={() => setCho(c)}>{c} chỗ</button>)}
      </div></div>

    <div className="lx-so">
      <div className="lx-s s1"><small>Công suất 30 ngày tới</small><b>{pc(d.cong_suat_30)}</b><em>ngày-xe đã có lệnh</em></div>
      <div className="lx-s s2"><small>Công suất ngày 31–60</small><b>{pc(d.cong_suat_31_60)}</b><em>lệnh đã chốt</em></div>
      <div className="lx-s s3"><small>Ngày-xe còn trống</small><b>{d.ngay_xe_trong}</b><em>gồm {d.ngay_xe_trong_cuoi_tuan} ngày cuối tuần</em></div>
      <div className="lx-s s4"><small>Đề nghị xe chờ lệnh</small><b>{d.de_nghi_cho}</b><em>đang hỏi {d.ngay_xe_de_nghi} ngày-xe</em></div>
    </div>

    <div className="lx-boc"><table className="lx-luoi">
      <thead><tr><th className="lx-xe">Xe</th>
        {ngay.map((s, i) => { const dt = new Date(s); const dau = i === 0 || s.slice(8) === "01";
          return <th key={s} className={dau ? "lx-thang" : ""}>{dau ? "T" + Number(s.slice(5, 7)) : dt.getDay() === 1 && Number(s.slice(8)) < 28 ? Number(s.slice(8)) : ""}</th>; })}
        <th className="lx-cs">Công suất</th></tr></thead>
      <tbody>
        {xe.map((x: any) => <tr key={x.id}>
          <th className="lx-xe">{x.xe}<small>{x.so_cho} chỗ{x.bi_chan ? " · đang hỏng" : ""}</small></th>
          {x.o.map((t: string, i: number) => { const dt = new Date(ngay[i]); const ct = dt.getDay() === 0 || dt.getDay() === 6;
            return <td key={i} title={`${x.xe} · ${dd(ngay[i])} · ${t === "lenh" ? "đã có lệnh" : t === "chan" ? "bị chặn: " + x.bi_chan : "trống"}`}
              style={{ background: t ? MAU[t] : ct ? "#f3f6fa" : "#fff" }} className={dt.getDay() === 1 ? "lx-dt" : ""} />; })}
          <td className="lx-cs">{pc(x.cong_suat)}</td></tr>)}
        <tr><th className="lx-xe">Đề nghị chờ lệnh<small>số xe đang được hỏi</small></th>
          {d.hoi_theo_ngay.map((n: number, i: number) => <td key={i} className="lx-hoi">{n || ""}</td>)}<td className="lx-cs" /></tr>
      </tbody></table></div>
    <div className="lx-chu"><span><i style={{ background: "#2c5fa2" }} />Đã có lệnh</span><span><i style={{ background: "#c2475d" }} />Đang hỏng — không tính trống</span>
      <span><i style={{ background: "#fff" }} />Trống — bán được</span><span><i style={{ background: "#f3f6fa" }} />Cuối tuần</span></div>

    <div className="lx-hai">
      <section className="xe-blk"><div className="xe-dau-con"><h3 style={{ margin: 0 }}>Khoảng trống để bán</h3><span className="muted">từ 2 ngày liền · gần nhất trước</span></div>
        {kt.map((k: any, i: number) => <div key={i} className="xe-it">
          <span className="lx-ngay">{dd(k.tu)}–{dd(k.den)}</span>
          <span style={{ flex: "1 1 200px", minWidth: 0 }}><b>{k.xe} · {k.so_cho} chỗ</b><span className="muted" style={{ display: "block", fontSize: 13 }}>{k.so_ngay} ngày liền{k.cuoi_tuan ? " · có cuối tuần" : ""}</span></span>
          <button type="button" onClick={() => mo(`/lenh-dieu-xe/de-nghi/moi?tu=${k.tu}&den=${k.den}`)}>Giữ xe cho tour</button>
        </div>)}
        {!kt.length && <p className="muted">Không có khoảng trống từ 2 ngày trở lên.</p>}</section>
      <section className="xe-blk"><div className="xe-dau-con"><h3 style={{ margin: 0 }}>Công suất theo tuần</h3><span className="muted">vàng: dưới {d.nguong_thap}%</span></div>
        <div className="lx-cot">{d.tuan.map((t: any) => <div key={t.tu}>
          <b>{pc(t.cong_suat)}</b><i style={{ height: `${Math.max(4, (t.cong_suat || 0) * 1.3)}px`, background: (t.cong_suat ?? 0) < d.nguong_thap ? "#c98a14" : "#2c5fa2" }} />
          <span>{t.nhan}</span></div>)}</div></section>
    </div>
    <style>{CSS}</style>
  </>;
}

const CSS = `
.xe-dau-con{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.lx-chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.lx-chips button{font:inherit;font-size:13px;border:1px solid #c9d6e8;background:#fff;color:var(--xe-nhan,#2c5fa2);border-radius:999px;padding:5px 12px;cursor:pointer;font-weight:600}
.lx-chips button[aria-pressed=true]{background:var(--xe-nhan,#2c5fa2);border-color:var(--xe-nhan,#2c5fa2);color:#fff}
.lx-gach{width:1px;height:22px;background:#dbe4ef;margin:0 4px}
.lx-so{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:16px}
@media (max-width:900px){.lx-so{grid-template-columns:repeat(2,minmax(0,1fr))}}
.lx-s{border-radius:16px;padding:14px 18px;color:#fff;display:grid;gap:2px;box-shadow:var(--xe-b1)}
.lx-s small{font-size:12px;letter-spacing:.8px;text-transform:uppercase;opacity:.85}
.lx-s b{font-size:30px;font-variant-numeric:tabular-nums;line-height:1.1}
.lx-s em{font-style:normal;font-size:12.5px;opacity:.85}
.lx-s.s1{background:linear-gradient(135deg,#2c5fa2,#214c82)}.lx-s.s2{background:linear-gradient(135deg,#1f7a63,#14604e)}
.lx-s.s3{background:linear-gradient(135deg,#b07a12,#8a5d08)}.lx-s.s4{background:linear-gradient(135deg,#3b4f7a,#2b3b5e)}
.lx-boc{overflow-x:auto;border:1px solid #dbe4ef;border-radius:12px;background:#fff}
.lx-luoi{border-collapse:separate;border-spacing:0;font-size:12px;width:auto}
.lx-luoi th,.lx-luoi td{padding:0;border-bottom:1px solid #eef2f7;text-transform:none;letter-spacing:0}
.lx-luoi thead th{position:sticky;top:0;background:#f6f9fd;height:26px;min-width:13px;text-align:center;color:#5b6876;font-weight:600}
.lx-luoi thead th.lx-thang{color:#183c69;text-align:left}
.lx-luoi .lx-xe{position:sticky;left:0;background:#fff;z-index:1;text-align:left;padding:4px 10px;min-width:150px;border-right:1px solid #dbe4ef;white-space:nowrap;color:#16202a}
.lx-luoi .lx-xe small{display:block;color:#5b6876;font-weight:500}
.lx-luoi td{width:13px;height:30px;border-right:1px solid #eef2f7}
.lx-luoi td.lx-dt{border-left:1px solid #c9d6e8}
.lx-luoi td.lx-hoi{text-align:center;font-size:11px;color:#a66a00;font-weight:700}
.lx-luoi .lx-cs{position:sticky;right:0;background:#fff;min-width:64px;text-align:right;padding:0 10px;border-left:1px solid #dbe4ef;font-weight:700;color:#183c69}
.lx-chu{display:flex;gap:14px;flex-wrap:wrap;font-size:12.5px;color:#5b6876;margin:10px 0 16px}
.lx-chu i{display:inline-block;width:13px;height:13px;border-radius:3px;border:1px solid #dbe4ef;vertical-align:-2px;margin-right:5px}
.lx-hai{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:16px}
@media (max-width:1000px){.lx-hai{grid-template-columns:minmax(0,1fr)}}
.lx-ngay{font-variant-numeric:tabular-nums;font-weight:700;color:#183c69;min-width:110px}
.lx-cot{display:flex;align-items:flex-end;gap:8px;height:170px}
.lx-cot div{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:5px;height:100%}
.lx-cot i{display:block;width:100%;border-radius:7px 7px 0 0}
.lx-cot b{font-size:12px;color:#183c69}.lx-cot span{font-size:11.5px;color:#5b6876}
`;
