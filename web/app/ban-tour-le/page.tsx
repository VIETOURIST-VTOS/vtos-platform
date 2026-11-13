"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, pct } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** Bàn bán tour lẻ – Phòng Kinh doanh Lẻ. Chủ tịch quyết 25/9/2026.
 *
 *  "Tour lẻ là do Phòng Điều hành tạo lịch khởi hành, sales lẻ chỉ việc bán."
 *  "Sales lẻ chỉ nhìn thấy dự toán 3 con số như trong file quyết toán tour của Điều hành."
 *
 *  KHÔNG CÓ NÚT NÀO TRÊN BẢNG NÀY. Bán một chỗ là việc phải mở chuyến ra đọc trước; một nút "đặt"
 *  cạnh một dòng tóm tắt là lời mời đặt mà chưa xem. Cửa bán nằm ở /requests, đã có từ đầu.
 *
 *  MÀN HÌNH KHÔNG TỰ TÍNH LẠI MỘT CON SỐ NÀO. Mọi số dưới đây do máy chủ gửi xuống nguyên vẹn từ
 *  `rules.calc`. Tính lại ở đây là dựng bản sao thứ hai của cổng biên, và bản sao nào rồi cũng lệch
 *  – lần này lệch theo hướng nguy hiểm nhất: người bán đọc một con biên, người duyệt đọc con khác.
 *
 *  R5-15 · 14/11/2026 (Chủ tịch duyệt bản xem trước: «kiểm tra lại cách thiết kế cho đẹp, dễ nhìn và chuyên
 *  nghiệp hơn, lấy navy sáng làm điểm nhấn»): đầu màn dải navy; ô số có vạch navy, ô gấp viền hồng logo; lọc
 *  thành nhóm nút có đếm + ô tìm; bảng 12 → 8 cột (chỗ thành thanh tiến độ có vạch hòa vốn, dự toán gộp, «ngưỡng
 *  bán» gộp hòa vốn / lãi / bán đủ, lợi nhuận gộp hai số); chuyến chưa đủ dự toán in MỘT ô xám gộp cột thay cho
 *  hàng loạt gạch; chia nhóm theo tháng khởi hành. Sửa lỗi «00»: cột hòa vốn in `0` của `hoa_von_khach` (máy
 *  chủ trả 0 khi chưa đủ dự toán) cạnh một `0` lọt ra từ biểu thức `&&` — nay chỉ đọc `khach_hoa_von` (None
 *  khi chưa đủ dự toán). Chữ số phông thường căn đều cột, bỏ phông máy chữ.
 */

const CONG: Record<string, [string, string]> = {
  dat: ["ĐẠT biên", "dat"],
  khong_dat: ["DƯỚI biên", "duoi"],
  chua_du_co_so: ["chưa đủ cơ sở", "chua"],
};
type Loc = "tat" | "gan" | "chuahv" | "codt" | "chuadt";
const du = (r: any) => r.loi_nhuan_ke_hoach != null;          // đủ ba con số dự toán (máy chủ quyết)
const chuaHv = (r: any) => r.khach_hoa_von != null && r.cho_da_ban < r.khach_hoa_von;

function BanTourLe() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [loc, setLoc] = useState<Loc>("tat");
  const [tim, setTim] = useState("");
  // R5-16 · Chủ tịch 14/11/2026: «Lịch khởi hành» gộp vào đây — thêm hai phạm vi CHỈ XEM.
  const [phamVi, setPhamVi] = useState<"dang_ban" | "sap_mo_ban" | "da_di">("dang_ban");
  const load = useCallback(() => api(`/ban-tour-le/ban-lam-viec?pham_vi=${phamVi}`).then(setD).catch((e) => toast(errMsg(e), true)), [toast, phamVi]);
  useEffect(() => { load(); }, [load]);

  const all: any[] = d?.rows || [];
  const dem = useMemo(() => ({
    tat: all.length, gan: all.filter((r) => r.days_left <= 7).length, chuahv: all.filter(chuaHv).length,
    codt: all.filter(du).length, chuadt: all.filter((r) => !du(r)).length,
  }), [all]);
  const rows = all.filter((r) => (loc === "tat" || (loc === "gan" && r.days_left <= 7) || (loc === "chuahv" && chuaHv(r))
      || (loc === "codt" && du(r)) || (loc === "chuadt" && !du(r)))
    && (!tim || (r.code + " " + r.name).toLowerCase().includes(tim.toLowerCase())));
  // Nhóm theo tháng khởi hành — máy chủ đã sắp theo ngày đi gần nhất.
  const nhom: { ky: string; ds: any[] }[] = [];
  for (const r of rows) {
    const ky = String(r.start_date).slice(0, 7);
    if (!nhom.length || nhom[nhom.length - 1].ky !== ky) nhom.push({ ky, ds: [] });
    nhom[nhom.length - 1].ds.push(r);
  }
  if (!d) return <p className="muted">Đang tải…</p>;
  const T = d.tong || {};
  const bien = Math.round(((all[0]?.bien_muc_tieu) ?? 0.1) * 100);

  return (<div className="btl">
    <div className="btl-dau"><h1>Bàn bán tour lẻ</h1>
      <p>Chuyến lẻ đang bán, sắp theo ngày khởi hành gần nhất. Lịch do Phòng Điều hành mở — xem còn chỗ và còn lời bao nhiêu trước khi trả lời khách.</p></div>

    {phamVi === "dang_ban" && <div className="btl-o5">
      <div className="o"><b>{vnd(T.chuyen)}</b><span>Chuyến đang bán</span></div>
      <div className="o"><b>{vnd(T.cho_con)}</b><span>Chỗ còn trống</span></div>
      <div className={"o" + (T.sap_khoi_hanh ? " hong" : "")}><b>{vnd(T.sap_khoi_hanh)}</b><span>Khởi hành trong 7 ngày</span></div>
      <div className={"o" + (T.chua_hoa_von ? " hong" : "")}><b>{vnd(T.chua_hoa_von)}</b><span>Chưa bán đủ số khách hòa vốn</span></div>
      <div className="o mo"><b>{vnd(T.chua_du_co_so)}</b><span>Chưa có dự toán riêng</span></div>
    </div>}

    <div className="btl-loc">
      <div className="btl-seg btl-pv" role="group" aria-label="Phạm vi chuyến">
        {([["dang_ban", "Đang bán"], ["sap_mo_ban", "Sắp mở bán (nháp)"], ["da_di", "Đã đi"]] as const).map(([k, t]) =>
          <button key={k} type="button" aria-pressed={phamVi === k} onClick={() => { setD(null); setPhamVi(k); }}>{t}<em>{d?.dem_pham_vi?.[k] ?? ""}</em></button>)}
      </div>
      {phamVi !== "dang_ban" && <span className="btl-chi">Chỉ xem{phamVi === "sap_mo_ban" ? " — chuyến Điều hành đã tạo, chưa duyệt nên chưa bán được" : " — chuyến đã khởi hành"}{d?.cat_bot ? ` · hiện ${vnd((d.rows || []).length)} chuyến gần nhất, còn ${vnd(d.cat_bot)} chuyến cũ hơn` : ""}</span>}
    </div>

    {/* Lời lưu ý do MÁY CHỦ gửi xuống, không viết cứng ở đây: câu này là một phần của con số. */}
    {d.luu_y && <div className="btl-luu"><i aria-hidden="true">i</i><span>{d.luu_y}</span></div>}

    <div className="btl-loc">
      <div className="btl-seg" role="group" aria-label="Lọc chuyến">
        {([["tat", "Tất cả"], ["gan", "≤ 7 ngày"], ["chuahv", "Chưa hòa vốn"], ["codt", "Có dự toán"], ["chuadt", "Chưa có dự toán"]] as [Loc, string][])
          .map(([k, t]) => <button key={k} type="button" aria-pressed={loc === k} onClick={() => setLoc(k)}>{t}<em>{dem[k]}</em></button>)}
      </div>
      <input className="btl-tim" type="search" value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm mã chuyến, tuyến…" aria-label="Tìm chuyến" />
    </div>

    <div className="btl-bang"><div className="btl-cuon"><table>
      <thead><tr><th>Chuyến</th><th>Khởi hành</th><th>Chỗ đã bán / mở</th><th className="so">Giá bán</th><th className="so">Dự toán</th>
        <th>Ngưỡng bán</th><th className="so">Lợi nhuận</th><th>Cổng biên</th></tr></thead>
      <tbody>{nhom.length ? nhom.map((g) => {
        const cho = g.ds.reduce((a, r) => a + (r.cho_con || 0), 0);
        return [<tr key={"k" + g.ky} className="thang"><td colSpan={8}>THÁNG {Number(g.ky.slice(5))}/{g.ky.slice(0, 4)}<small>{g.ds.length} chuyến · {vnd(cho)} chỗ trống</small></td></tr>,
          ...g.ds.map((r: any) => {
            const [nhan, mau] = CONG[r.trang_thai_cong] || [r.trang_thai_cong, "chua"];
            const p = r.cho_mo_ban ? Math.min(100, (r.cho_da_ban / r.cho_mo_ban) * 100) : 0;
            const dd = du(r);
            const coMot = !dd && (r.chi_phi_co_dinh || r.chi_phi_theo_khach);
            return <tr key={r.id}>
              <td data-n=""><Link className="ma" href={`/tours/${r.id}`}>{r.code}</Link><span className="ten">{r.name}</span></td>
              <td data-n="Khởi hành" className="ngay"><b>{fmtD(r.start_date)}</b>
                <span className={"con" + (r.days_left >= 0 && r.days_left <= 7 ? " gap" : "")}>{r.days_left < 0 ? `đã đi ${-r.days_left} ngày` : r.days_left === 0 ? "đi hôm nay" : `còn ${r.days_left} ngày`}</span></td>
              <td data-n="Chỗ" className="cho"><div className="s"><b>{r.cho_da_ban} / {r.cho_mo_ban}</b><small>còn {r.cho_con}</small></div>
                <div className="bar"><i style={{ width: p + "%" }} />{r.khach_hoa_von != null && r.cho_mo_ban ? <s style={{ left: Math.min(100, (r.khach_hoa_von / r.cho_mo_ban) * 100) + "%" }} /> : null}</div></td>
              <td data-n="Giá bán" className="so gia">{vnd(r.gia_ban)}</td>
              {dd || coMot ? <td data-n="Dự toán" className="so dt">{r.chi_phi_co_dinh ? vnd(r.chi_phi_co_dinh) : "—"}
                <small>{r.chi_phi_theo_khach ? `+ ${vnd(r.chi_phi_theo_khach)} / khách` : "chưa có chi phí / khách"}</small></td> : null}
              {dd ? <>
                <td data-n="Ngưỡng bán"><div className="ng">
                  <div><span>Hòa vốn</span>{r.khach_hoa_von == null ? <b>—</b> : chuaHv(r)
                    ? <b className="thieu">{r.khach_hoa_von} · thiếu {r.khach_hoa_von - r.cho_da_ban}</b> : <b className="dat">{r.khach_hoa_von} · đã đạt</b>}</div>
                  <div><span>Lãi {bien}%</span>{r.khach_dat_bien == null ? <b>không đạt ở giá này</b> : r.khach_dat_bien > r.cho_da_ban
                    ? <b>{r.khach_dat_bien} · thiếu {r.khach_dat_bien - r.cho_da_ban}</b> : <b className="dat">{r.khach_dat_bien} · đã đạt</b>}</div>
                  {r.bien_khi_day != null && <div><span>Bán đủ {r.khach_toi_da}</span><b className={r.bien_khi_day < 0 ? "thieu" : "dat"}>lãi {pct(r.bien_khi_day)}</b></div>}
                </div></td>
                <td data-n="Lợi nhuận" className="so ln"><b className={r.loi_nhuan_ke_hoach < 0 ? "am" : "duong"}>{vnd(r.loi_nhuan_ke_hoach)}</b><small>kế hoạch · biên {pct(r.bien_ke_hoach)}</small>
                  {r.loi_nhuan_tai_so_dang_ban != null && <><b className={r.loi_nhuan_tai_so_dang_ban < 0 ? "am" : "duong"}>{vnd(r.loi_nhuan_tai_so_dang_ban)}</b><small>tại số đang bán</small></>}</td>
              </> : <td colSpan={coMot ? 2 : 3} className="rong"><div className="chua"><i aria-hidden="true">!</i>
                {coMot ? `Thiếu ${r.chi_phi_co_dinh ? "chi phí / khách" : "chi phí cố định"} — chưa tính được hòa vốn và lợi nhuận`
                  : "Chưa có dự toán riêng — Điều hành nhập 3 con số dự toán thì hòa vốn, lãi và lợi nhuận tự hiện"}</div></td>}
              <td data-n="Cổng biên"><span className={"cong " + mau}>{nhan}</span>{r.duoi_bien && <span className="cong duoi">đã ký dưới biên</span>}
                {r.chi_tham_chieu && <span className="tc">số chỉ để tham chiếu</span>}</td>
            </tr>; })];
      }) : <tr><td colSpan={8} className="trong">Không có chuyến nào khớp bộ lọc.</td></tr>}</tbody>
    </table></div>
      <div className="btl-chan"><span><b>Lợi nhuận kế hoạch</b> tính ở số khách dự toán; <b>tại số đang bán</b> tính ở số khách đã bán hôm nay — chênh nhau là khoảng còn phải bán, không phải lỗi bảng.</span><span>Vạch hồng trên thanh = điểm hòa vốn.</span></div>
    </div>

    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.btl{display:grid;gap:14px;font-variant-numeric:tabular-nums;--n1:#1f4f97;--n2:#2f6fc0;--n3:#5b9be6;--nn:#e8f0fc;--vien:#e6ecf5;--mo:#7d8ca3;--chu:#1d3a68;--hong:var(--vtos-logo-hong);--hongd:#d6336c;--hongn:#fff0f4;--ok:#2f7d3b;--okn:#ecf7ee;--nen:#f6f9fe}
.btl-dau{padding:16px 20px;border-radius:16px;color:#fff;background:linear-gradient(120deg,#3a7bd0,#2a63b5 55%,var(--n1));box-shadow:0 10px 26px rgba(31,79,151,.22)}
.btl-dau h1{margin:0;font-size:20px;color:#fff}.btl-dau p{margin:4px 0 0;font-size:12.5px;opacity:.9;max-width:80ch;color:#fff}
.btl-o5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.btl-o5 .o{background:#fff;border:1px solid var(--vien);border-radius:14px;padding:12px 14px 12px 18px;display:grid;gap:3px;position:relative;overflow:hidden;min-width:0}
.btl-o5 .o::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(var(--n3),var(--n1))}
.btl-o5 .o b{font-size:26px;font-weight:800;color:var(--n1)}.btl-o5 .o span{font-size:12.5px;color:var(--mo)}
.btl-o5 .o.hong::before{background:var(--hong)}.btl-o5 .o.hong b{color:var(--hongd)}.btl-o5 .o.mo b{color:var(--mo)}
.btl-luu{display:flex;gap:10px;align-items:flex-start;background:var(--nn);border:1px solid #c9dbf5;border-radius:12px;padding:10px 14px;font-size:12.5px;line-height:1.55;color:var(--chu)}
.btl-luu i{font-style:normal;display:grid;place-items:center;flex:none;width:22px;height:22px;border-radius:50%;background:var(--n2);color:#fff;font-weight:800;font-size:12px}
.btl-loc{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.btl-seg{display:inline-flex;background:#fff;border:1px solid var(--vien);border-radius:999px;padding:3px;gap:2px;flex-wrap:wrap}
.btl-seg button{font:inherit;font-size:12.5px;font-weight:700;border:0;background:none;color:var(--chu);padding:7px 13px;border-radius:999px;cursor:pointer;min-height:36px}
.btl-seg button[aria-pressed=true]{background:linear-gradient(120deg,var(--n2),var(--n1));color:#fff}
.btl-seg button em{font-style:normal;font-size:11px;opacity:.75;margin-left:5px}
.btl-pv{background:var(--nn)}
.btl-chi{font-size:12.5px;color:var(--mo);font-weight:600}
.btl-tim{flex:1;min-width:180px;max-width:320px;margin-left:auto;font:inherit;font-size:13px;background:#fff;border:1px solid var(--vien);border-radius:999px;padding:9px 14px;color:var(--chu)}
.btl-tim:focus{outline:2px solid var(--n3);outline-offset:1px}
.btl-bang{background:#fff;border:1px solid var(--vien);border-radius:16px;overflow:hidden}
.btl-cuon{overflow:auto;max-height:70vh}
.btl table{width:100%;border-collapse:separate;border-spacing:0;min-width:1040px;margin:0}
.btl thead th{position:sticky;top:0;z-index:2;background:linear-gradient(120deg,var(--n2),var(--n1));color:#fff;font-size:11.5px;font-weight:700;text-align:left;padding:10px 12px;white-space:nowrap;border:0;text-transform:none;letter-spacing:0}
.btl th.so,.btl td.so{text-align:right}
.btl td{padding:10px 12px;border:0;border-bottom:1px solid var(--vien);vertical-align:middle;color:var(--chu);font-family:inherit}
.btl tbody tr:hover td{background:var(--nen)}
.btl tr.thang td{background:var(--nn);color:var(--n1);font-weight:800;font-size:12px;letter-spacing:.06em;padding:7px 12px;position:sticky;top:36px;z-index:1}
.btl tr.thang td small{font-weight:600;color:var(--mo);letter-spacing:0;margin-left:8px}
.btl .ma{color:var(--n1);font-weight:800;text-decoration:none;border-bottom:1px dashed rgba(31,79,151,.45)}
.btl .ma:hover{color:var(--n2);border-bottom-style:solid}
.btl .ten{display:block;color:var(--mo);font-size:12px;margin-top:2px}
.btl .ngay b{display:block;font-weight:700}
.btl .con{display:inline-block;margin-top:3px;font-size:11px;font-weight:800;border-radius:999px;padding:2px 9px;background:var(--nn);color:var(--n1)}
.btl .con.gap{background:var(--hongn);color:var(--hongd)}
.btl .cho{min-width:120px}.btl .cho .s{display:flex;justify-content:space-between;gap:8px;font-size:12.5px}.btl .cho .s b{color:var(--n1)}.btl .cho .s small{color:var(--mo)}
.btl .bar{position:relative;height:7px;border-radius:99px;background:var(--nn);margin-top:5px}
.btl .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,var(--n2),var(--n3))}
.btl .bar s{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--hongd)}
.btl .gia{font-weight:700}
.btl .dt small,.btl .ln small{display:block;color:var(--mo);font-size:11.5px}
.btl .ng{display:grid;gap:3px;font-size:12px;min-width:160px}
.btl .ng div{display:flex;justify-content:space-between;gap:10px}.btl .ng div span{color:var(--mo)}
.btl .thieu,.btl .ln .am{color:var(--hongd);font-weight:800}.btl .dat,.btl .ln .duong{color:var(--ok);font-weight:800}
.btl .ln b{display:block}
.btl .chua{display:flex;align-items:center;gap:8px;color:var(--mo);font-size:12.5px;background:var(--nen);border:1px dashed var(--vien);border-radius:10px;padding:8px 12px}
.btl .chua i{font-style:normal;font-weight:800;color:var(--n2)}
.btl .cong{display:inline-block;font-size:11.5px;font-weight:800;border-radius:999px;padding:4px 10px;white-space:nowrap;margin:1px 0}
.btl .cong.dat{background:var(--okn);color:var(--ok)}.btl .cong.duoi{background:var(--hongn);color:var(--hongd)}.btl .cong.chua{background:var(--nen);color:var(--mo);border:1px solid var(--vien);padding:3px 9px}
.btl .tc{display:block;font-size:11px;color:var(--mo);margin-top:3px}
.btl .trong{color:var(--mo);text-align:center;padding:24px}
.btl-chan{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--mo);padding:10px 14px;border-top:1px solid var(--vien);background:var(--nen)}
.btl-chan b{color:var(--chu)}
@media(max-width:900px){.btl-o5{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){
  .btl table{min-width:0}.btl thead{display:none}.btl tbody{display:grid;gap:8px;padding:8px}
  .btl tbody tr{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 10px;border:1px solid var(--vien);border-left:4px solid var(--n2);border-radius:12px;padding:10px 12px;background:#fff}
  .btl tbody tr.thang{display:block;border:0;padding:0;background:none}.btl tr.thang td{position:static;border-radius:8px}
  .btl td{display:block;padding:0;border:0;min-width:0;text-align:left}.btl td.so{text-align:left}
  .btl td[data-n=""],.btl td.rong,.btl td[data-n="Ngưỡng bán"]{grid-column:1/-1}
  .btl td[data-n]:not([data-n=""])::before{content:attr(data-n);display:block;font-size:10.5px;font-weight:600;color:var(--mo)}
  .btl-tim{max-width:none;margin-left:0}
}
`}</style>
  </div>);
}

export default function Page() { return <Shell><BanTourLe /></Shell>; }
