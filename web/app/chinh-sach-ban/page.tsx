"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** R5-16 · CHÍNH SÁCH BÁN — Chủ tịch duyệt bản xem trước 14/11/2026 (thay «Giá & chính sách bán» trên bàn Lẻ).
 *
 *  Giá bán tour lẻ đã nằm trên từng chuyến (Điều hành đặt khi mở lịch), nên màn này giữ CHÍNH SÁCH CÓ THỜI HẠN:
 *  ba phần MỚI GĐ KD / TP ban hành (chiết khấu tối đa theo vai · giá trẻ em / em bé / phụ thu · khuyến mãi) và
 *  hai phần ĐÃ CÓ đọc thẳng (hoa hồng đối tác / đại lý / CTV D06 · VTD Rewards) — sửa ở màn của chúng.
 *  Mọi số do máy chủ trả (`services/chinh_sach_ban.py`). Ô rỗng = «chưa ban hành», không phải 0.
 */
const VAI: [string, string][] = [["nv_kd", "Chuyên viên"], ["tn_kd", "Trưởng nhóm"], ["tp_kd", "Trưởng phòng"]];
const p = (x: any) => x == null ? null : `${String(x).replace(".", ",")}%`;
const ty = (v: number) => v >= 1e9 ? `${(v / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 })} tỷ` : `${Math.round(v / 1e6).toLocaleString("vi-VN")} tr`;
const RONG = { chiet_khau: { nv_kd: "", tn_kd: "", tp_kd: "" }, tre_em: { tre_em_pct: "", em_be_pct: "", phu_thu_phong_don: "" },
  khuyen_mai: [] as any[], hieu_luc_tu: "", hieu_luc_den: "", ghi_chu: "" };

function Dong({ nhan, gt, sau }: { nhan: string; gt: any; sau?: string }) {
  return <div className="cs-dong"><span>{nhan}</span>{gt == null || gt === "" ? <em>chưa ban hành</em> : <b>{gt}{sau || ""}</b>}</div>;
}

function ChinhSachBan() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [bieu, setBieu] = useState<any>(null);
  const [cu, setCu] = useState(false);
  const load = useCallback(() => api("/ban-hang/chinh-sach").then(setD).catch((e) => toast(errMsg(e), true)), [toast]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="muted">Đang tải…</p>;
  const hh = d.hien_hanh, nd = hh?.noi_dung || {}, ck = nd.chiet_khau || {}, te = nd.tre_em || {}, km: any[] = nd.khuyen_mai || [];
  const lk = d.lien_ket || {}, d6 = lk.d06 || {}, rw = lk.rewards || {};

  const moBieu = () => setBieu(hh ? { ...RONG, chiet_khau: { ...RONG.chiet_khau, ...ck }, tre_em: { ...RONG.tre_em, ...te }, khuyen_mai: km.map((k) => ({ ...k })) } : { ...RONG, khuyen_mai: [] });
  const dat = (nhom: string, k: string, v: string) => setBieu({ ...bieu, [nhom]: { ...bieu[nhom], [k]: v } });
  const datKm = (i: number, k: string, v: string) => setBieu({ ...bieu, khuyen_mai: bieu.khuyen_mai.map((x: any, j: number) => j === i ? { ...x, [k]: v } : x) });
  const luu = async () => {
    try {
      await api("/ban-hang/chinh-sach", { method: "POST", json: { hieu_luc_tu: bieu.hieu_luc_tu, hieu_luc_den: bieu.hieu_luc_den || null, ghi_chu: bieu.ghi_chu,
        noi_dung: { chiet_khau: bieu.chiet_khau, tre_em: bieu.tre_em, khuyen_mai: bieu.khuyen_mai } } });
      toast("Đã ban hành chính sách bán"); setBieu(null); load();
    } catch (e) { toast(errMsg(e), true); }
  };

  return (<div className="csb">
    <div className="csb-dau"><h1>Chính sách bán · Kinh doanh Lẻ</h1>
      <p>Giá bán tour lẻ nằm trên từng chuyến (xem ở Bàn bán tour lẻ). Màn này giữ chính sách có thời hạn và gom về một chỗ hoa hồng đối tác / đại lý / CTV và điểm thưởng khách.</p></div>

    <section className="csb-khoi">
      <div className="csb-hang">
        <div>{hh ? <><b className="csb-ma">Chính sách bán tour lẻ · {hh.ma}</b>
          <small>Hiệu lực {fmtD(hh.hieu_luc_tu)} → {hh.hieu_luc_den ? fmtD(hh.hieu_luc_den) : "chưa đặt ngày hết"} · ban hành bởi {hh.tao_boi}</small></>
          : <><b className="csb-ma">Chưa ban hành chính sách bán</b><small>GĐ KD / Trưởng phòng KD ban hành bản đầu tiên.</small></>}</div>
        <div className="csb-nut">{hh && <span className="csb-tt dat">● Đang hiệu lực</span>}
          {d.cac_ban?.length > 0 && <button type="button" className="phu" onClick={() => setCu(!cu)}>Bản cũ ({d.cac_ban.length})</button>}
          {d.duoc_ban_hanh && <button type="button" onClick={moBieu}>Ban hành bản mới</button>}</div>
      </div>

      <div className="csb-luoi">
        <div className="csb-o"><h3><i>%</i>Chiết khấu tối đa người bán được tự cho</h3>
          {VAI.map(([k, t]) => <Dong key={k} nhan={t} gt={p(ck[k])} sau=" giá bán" />)}
          <p className="csb-ghi">Vượt mức thì gửi duyệt; không làm chuyến xuống dưới cổng biên.</p></div>
        <div className="csb-o"><h3><i>👶</i>Giá trẻ em · em bé · phụ thu</h3>
          <Dong nhan="Trẻ em 5 – dưới 12 tuổi (ngủ chung)" gt={p(te.tre_em_pct)} sau=" giá người lớn" />
          <Dong nhan="Em bé dưới 5 tuổi" gt={p(te.em_be_pct)} sau=" giá người lớn" />
          <Dong nhan="Phụ thu phòng đơn (mặc định)" gt={te.phu_thu_phong_don == null ? null : vnd(te.phu_thu_phong_don)} sau=" đ" /></div>
        <div className="csb-o"><h3><i>🏷</i>Khuyến mãi</h3>
          {km.length === 0 ? <p className="csb-ghi">Chưa ban hành khuyến mãi nào.</p> : km.map((k, i) => (
            <div key={i} className="csb-km"><span className="ma">{k.ma || "—"}</span><span>{k.ten}<small>{k.ap_dung || "mọi tuyến"}{k.tu ? ` · ${fmtD(k.tu)}` : ""}{k.den ? ` – ${fmtD(k.den)}` : ""}</small></span>
              <span className="chip">{k.gia_tri == null ? "—" : k.kieu === "pct" ? `−${p(k.gia_tri)}` : `−${vnd(k.gia_tri)} đ`}</span></div>))}</div>
      </div>

      <p className="csb-nhom">ĐÃ CÓ SẴN TRONG VTOS — ĐỌC THẲNG, KHÔNG NHẬP LẦN HAI</p>
      <div className="csb-luoi hai">
        <div className="csb-o lk"><h3><i>🤝</i>Đối tác · Đại lý · CTV bán hàng</h3>
          <Dong nhan="Đối tác đang hợp tác" gt={(d6.doi_tac || []).map((x: any) => `${x.ten} ${x.so}`).join(" · ")} />
          {Object.entries(d6.bac || {}).map(([k, v]: [string, any]) => (
            <Dong key={k} nhan={`Hoa hồng ${k.startsWith("dai_ly") ? "Đại lý" : "CTV bán hàng"} (D06, lũy tiến)`}
              gt={v.bac.map((b: any) => `${String(b.ty_le).replace(".", ",")}%${b.den ? ` đến ${ty(b.den)}` : " phần trên"}`).join(" · ")} />))}
          <div className="csb-hang2"><span className={"csb-tt " + (d6.bat ? "dat" : "cho")}>{d6.bat ? `Đang áp dụng từ ${fmtD(d6.hieu_luc_tu)}` : "Chưa bật — đang tính thử"}</span>
            <Link className="csb-lk" href="/hoa-hong-d06">Mở Hoa hồng D06 →</Link><Link className="csb-lk" href="/nguoi-ban-hang">Danh sách đối tác →</Link></div></div>
        <div className="csb-o lk"><h3><i>⭐</i>Khách hàng · VTD Rewards</h3>
          <Dong nhan="Hạng (chi tiêu tour 12 tháng)" gt={(rw.hang || []).map((h: any) => `${h.ten}${h.tu ? ` từ ${ty(h.tu)}` : ""} ×${String(h.he_so).replace(".", ",")}`).join(" · ")} />
          <Dong nhan="Cộng điểm" gt={rw.dong_moi_diem ? `1 điểm / ${vnd(rw.dong_moi_diem)} đ × hệ số hạng` : null} />
          <Dong nhan="Giá trị điểm" gt={rw.gia_tri_diem ? `1 điểm = ${vnd(rw.gia_tri_diem)} đ ưu đãi` : null} />
          <Dong nhan="Voucher mỗi booking" gt={rw.tran_voucher_pct != null ? `tối đa ${String(rw.tran_voucher_pct).replace(".", ",")}% giá trị` : null} />
          <Dong nhan="Giới thiệu khách" gt={rw.gioi_thieu_mo ? "đang mở" : "đang đóng"} />
          <div className="csb-hang2"><span className={"csb-tt " + (rw.bat ? "dat" : "cho")}>{rw.bat ? `Đang áp dụng từ ${fmtD(rw.hieu_luc_tu)}` : "Chưa bật cộng / đổi điểm"}</span>
            <Link className="csb-lk" href="/vtd-rewards">Mở VTD Rewards →</Link></div></div>
      </div>
    </section>

    {cu && <section className="csb-khoi"><h3 className="csb-h">Các bản đã ban hành</h3>
      <table className="csb-bang"><thead><tr><th>Mã</th><th>Hiệu lực</th><th>Chiết khấu NV / TN / TP</th><th>Trẻ em / em bé</th><th>Khuyến mãi</th><th>Ban hành</th></tr></thead>
        <tbody>{d.cac_ban.map((c: any) => { const n = c.noi_dung || {}; return <tr key={c.id}><td><b>{c.ma}</b></td>
          <td>{fmtD(c.hieu_luc_tu)} → {c.hieu_luc_den ? fmtD(c.hieu_luc_den) : "…"}</td>
          <td>{VAI.map(([k]) => p(n.chiet_khau?.[k]) ?? "—").join(" / ")}</td><td>{p(n.tre_em?.tre_em_pct) ?? "—"} / {p(n.tre_em?.em_be_pct) ?? "—"}</td>
          <td>{(n.khuyen_mai || []).length}</td><td>{c.tao_boi}</td></tr>; })}</tbody></table></section>}

    {bieu && <section className="csb-khoi csb-bieu"><h3 className="csb-h">Ban hành chính sách bán mới</h3>
      <p className="csb-ghi">Bản đang hiệu lực sẽ tự khép ngày hết = ngày trước bản mới. Ô để trống là «chưa ban hành», không phải 0.</p>
      <div className="csb-f3">
        <label>Hiệu lực từ *<input type="date" value={bieu.hieu_luc_tu} onChange={(e) => setBieu({ ...bieu, hieu_luc_tu: e.target.value })} /></label>
        <label>Hiệu lực đến<input type="date" value={bieu.hieu_luc_den} onChange={(e) => setBieu({ ...bieu, hieu_luc_den: e.target.value })} /></label>
        <span />
        {VAI.map(([k, t]) => <label key={k}>Chiết khấu tối đa · {t} (%)<input type="number" step="0.1" min={0} max={100} value={bieu.chiet_khau[k] ?? ""} onChange={(e) => dat("chiet_khau", k, e.target.value)} /></label>)}
        <label>Trẻ em 5 – dưới 12 tuổi (% giá NL)<input type="number" step="1" min={0} max={100} value={bieu.tre_em.tre_em_pct ?? ""} onChange={(e) => dat("tre_em", "tre_em_pct", e.target.value)} /></label>
        <label>Em bé dưới 5 tuổi (% giá NL)<input type="number" step="1" min={0} max={100} value={bieu.tre_em.em_be_pct ?? ""} onChange={(e) => dat("tre_em", "em_be_pct", e.target.value)} /></label>
        <label>Phụ thu phòng đơn mặc định (đ)<input type="number" step="10000" min={0} value={bieu.tre_em.phu_thu_phong_don ?? ""} onChange={(e) => dat("tre_em", "phu_thu_phong_don", e.target.value)} /></label>
      </div>
      <h4 className="csb-h4">Khuyến mãi</h4>
      {bieu.khuyen_mai.map((k: any, i: number) => <div key={i} className="csb-f3 km">
        <label>Mã<input value={k.ma || ""} onChange={(e) => datKm(i, "ma", e.target.value)} placeholder="EARLY30" /></label>
        <label>Tên chương trình *<input value={k.ten || ""} onChange={(e) => datKm(i, "ten", e.target.value)} /></label>
        <label>Áp dụng cho<input value={k.ap_dung || ""} onChange={(e) => datKm(i, "ap_dung", e.target.value)} placeholder="Tour nội địa / mọi tuyến" /></label>
        <label>Kiểu giảm<select value={k.kieu || "pct"} onChange={(e) => datKm(i, "kieu", e.target.value)}><option value="pct">% giá bán</option><option value="tien">số tiền / khách</option></select></label>
        <label>Mức giảm<input type="number" value={k.gia_tri ?? ""} onChange={(e) => datKm(i, "gia_tri", e.target.value)} /></label>
        <label>Từ – đến<span className="csb-2"><input type="date" value={k.tu || ""} onChange={(e) => datKm(i, "tu", e.target.value)} /><input type="date" value={k.den || ""} onChange={(e) => datKm(i, "den", e.target.value)} /></span></label>
      </div>)}
      <button type="button" className="phu" onClick={() => setBieu({ ...bieu, khuyen_mai: [...bieu.khuyen_mai, { kieu: "pct" }] })}>+ Thêm khuyến mãi</button>
      <label className="csb-gc">Ghi chú<input value={bieu.ghi_chu} onChange={(e) => setBieu({ ...bieu, ghi_chu: e.target.value })} /></label>
      <div className="csb-nut"><button type="button" onClick={luu}>Ban hành</button><button type="button" className="phu" onClick={() => setBieu(null)}>Đóng</button></div>
    </section>}

    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.csb{display:grid;gap:14px;font-variant-numeric:tabular-nums;--n1:#1f4f97;--n2:#2f6fc0;--n3:#5b9be6;--nn:#e8f0fc;--vien:#e6ecf5;--mo:#7d8ca3;--chu:#1d3a68;--nen:#f6f9fe}
.csb-dau{padding:16px 20px;border-radius:16px;color:#fff;background:linear-gradient(120deg,#3a7bd0,#2a63b5 55%,var(--n1));box-shadow:0 10px 26px rgba(31,79,151,.22)}
.csb-dau h1{margin:0;font-size:20px;color:#fff}.csb-dau p{margin:4px 0 0;font-size:12.5px;opacity:.9;color:#fff;max-width:85ch}
.csb-khoi{background:#fff;border:1px solid var(--vien);border-radius:16px;padding:16px 18px;display:grid;gap:12px}
.csb-hang{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center}
.csb-ma{display:block;font-size:16px;color:var(--chu)}.csb-hang small{color:var(--mo);font-size:12px}
.csb-nut{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.csb button{font:inherit;font-size:12.5px;font-weight:700;border:0;border-radius:999px;padding:9px 15px;cursor:pointer;background:linear-gradient(120deg,var(--n2),var(--n1));color:#fff;min-height:38px}
.csb button.phu{background:var(--nn);color:var(--n1)}
.csb-tt{font-size:12px;font-weight:700;border-radius:999px;padding:5px 11px}.csb-tt.dat{background:#ecf7ee;color:#2f7d3b}.csb-tt.cho{background:#fff4e5;color:#b45309}
.csb-luoi{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.csb-luoi.hai{grid-template-columns:repeat(2,minmax(0,1fr))}
.csb-o{border:1px solid var(--vien);border-radius:14px;padding:12px 14px;display:grid;gap:6px;align-content:start;min-width:0}
.csb-o.lk{border-left:4px solid var(--n2);background:linear-gradient(180deg,var(--nen),#fff 80px)}
.csb-o h3{margin:0 0 4px;font-size:14px;display:flex;align-items:center;gap:8px;color:var(--chu)}
.csb-o h3 i{font-style:normal;display:grid;place-items:center;width:28px;height:28px;border-radius:9px;background:var(--nn);color:var(--n1)}
.cs-dong{display:flex;justify-content:space-between;gap:10px;font-size:13px;padding:6px 0;border-bottom:1px dashed var(--vien)}
.cs-dong span{color:var(--mo)}.cs-dong b{color:var(--n1);text-align:right}.cs-dong em{color:var(--mo);font-style:normal;font-size:12px;background:var(--nen);border-radius:999px;padding:1px 8px}
.csb-ghi{margin:0;font-size:12px;color:var(--mo);background:var(--nen);border-radius:10px;padding:8px 12px;line-height:1.5}
.csb-km{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:8px 10px;border:1px solid var(--vien);border-left:4px solid var(--vtos-logo-hong);border-radius:10px;font-size:13px}
.csb-km .ma{font-weight:800;color:#d6336c}.csb-km small{display:block;color:var(--mo);font-size:11.5px}.csb-km .chip{font-size:11.5px;font-weight:800;border-radius:999px;padding:4px 10px;background:var(--nn);color:var(--n1)}
.csb-nhom{margin:4px 0 0;font-size:11.5px;font-weight:800;letter-spacing:.08em;color:var(--n1)}
.csb-hang2{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:4px}
.csb-lk{font-size:12.5px;font-weight:700;color:var(--n1);background:var(--nn);border-radius:999px;padding:7px 13px;text-decoration:none}
.csb-h{margin:0;font-size:15px;color:var(--chu)}.csb-h4{margin:6px 0 0;font-size:13px;color:var(--n1)}
.csb-bang{width:100%;border-collapse:separate;border-spacing:0;font-size:13px}.csb-bang th{background:linear-gradient(120deg,var(--n2),var(--n1));color:#fff;text-align:left;padding:9px 10px;font-size:12px}
.csb-bang td{padding:9px 10px;border-bottom:1px solid var(--vien)}
.csb-f3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.csb-f3.km{border:1px dashed var(--vien);border-radius:12px;padding:10px}
.csb label{display:grid;gap:4px;font-size:12px;font-weight:700;color:var(--mo)}
.csb input,.csb select{font:inherit;font-size:13px;border:1px solid var(--vien);border-radius:10px;padding:8px 10px;color:var(--chu);background:#fff;min-width:0}
.csb-2{display:grid;grid-template-columns:1fr 1fr;gap:6px}.csb-gc{max-width:640px}
@media(max-width:900px){.csb-luoi,.csb-luoi.hai,.csb-f3{grid-template-columns:1fr}}
`}</style>
  </div>);
}

export default function Page() { return <Shell><ChinhSachBan /></Shell>; }
