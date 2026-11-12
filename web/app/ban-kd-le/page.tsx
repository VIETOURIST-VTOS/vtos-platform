"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import KhungNhung from "@/components/KhungNhung";
import { useHomNay } from "@/components/DauManHinh01";
import { api, vnd, fmtD } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** R5 · BÀN LÀM VIỆC GIÁM ĐỐC KINH DOANH LẺ — Chủ tịch duyệt bản xem trước 13/11/2026 03:21.
 *
 *  Dựng theo khuôn bàn Marketing (VH-41/43): MỘT thanh đầu bàn `.mh01-ban`, sáu nhóm nút, trang con
 *  mở NGAY TRONG BÀN (KhungNhung) — người dùng không phải nhảy sang màn khác (luật 13/11/2026).
 *  Sáu nhóm và các thẻ con lấy đúng theo bản v32 /giam-doc-kinh-doanh; mỗi thẻ con là một màn CRM
 *  đang chạy, giữ nguyên luật và quyền của màn ấy.
 *
 *  CHỈ ĐỌC. Bàn không có ô nhập nào. Mọi số đọc từ MỘT cửa `/ban-kd-le/tong-quan`, cửa ấy đọc lại
 *  các hàm đang nuôi màn gốc (xem backend/app/services/ban_kd_le.py). Ô nào máy chủ trả `null` thì
 *  in «chưa đo» kèm lý do — không in số 0.
 *
 *  `/kinh-doanh-le` (doanh thu & giao chỉ tiêu) GIỮ NGUYÊN, mở trong nhóm «Chỉ tiêu & báo cáo».
 *  «Bàn Sale Admin» của v32 KHÔNG ở đây: Chủ tịch chốt làm riêng một đợt sau.
 */

type Con = { ten: string; toi: string };
const NHOM_KD: { ma: string; ten: string; con: Con[] }[] = [
  { ma: "tq", ten: "Tổng quan", con: [] },
  { ma: "ban", ten: "Bán hàng", con: [
    { ten: "Bàn bán tour lẻ", toi: "/ban-tour-le" }, { ten: "Lịch khởi hành", toi: "/tours?mang=le" },
    { ten: "Lịch xe trống", toi: "/lich-xe-trong" }, { ten: "Báo giá", toi: "/bao-gia?mang=kd_le" },
    { ten: "Giá & chính sách bán", toi: "/bang-gia" }, { ten: "Dịch vụ lẻ", toi: "/non-package" },
    { ten: "Khách sạn & vé máy bay OTA", toi: "/khach-san-ota" }] },
  { ma: "khach", ten: "Khách & booking", con: [
    { ten: "Khách hàng & nguồn khách", toi: "/leads?tab=leads" }, { ten: "Hộp thư đa kênh", toi: "/inbox" },
    { ten: "Yêu cầu đặt dịch vụ", toi: "/requests?mang=le" }, { ten: "Booking & bảo lưu", toi: "/bookings?mang=le" },
    { ten: "Yêu cầu từ cổng khách", toi: "/yeu-cau-khach" }, { ten: "Đơn phòng OTA", toi: "/don-khach-san-ota" }] },
  { ma: "cs", ten: "Chăm sóc", con: [
    { ten: "Chăm sóc sau tour", toi: "/cham-soc" }, { ten: "Phản hồi & khiếu nại", toi: "/khieu-nai" },
    { ten: "Đánh giá sau tour", toi: "/danh-gia" }, { ten: "VTD Rewards", toi: "/vtd-rewards" },
    { ten: "Góp ý riêng lãnh đạo", toi: "/gop-y-lanh-dao" }] },
  { ma: "doi", ten: "Đội ngũ", con: [
    { ten: "Cơ cấu tổ chức", toi: "/to-chuc-kd" }, { ten: "Người bán hàng", toi: "/nguoi-ban-hang" }] },
  { ma: "ct", ten: "Chỉ tiêu & báo cáo", con: [
    { ten: "Chỉ tiêu kinh doanh", toi: "/kinh-doanh-le" }, { ten: "Báo cáo ngày / tuần / tháng", toi: "/fit" },
    { ten: "Báo cáo bán hàng", toi: "/sales-reports?mang=le" }, { ten: "Đối soát OTA", toi: "/doi-soat-ota" }] },
];

/** Màn được mở TRONG khung: mọi trang con ở trên, cộng hồ sơ chuyến/booking/khách bấm từ bên trong chúng. */
const DUONG_KD = [...new Set(NHOM_KD.flatMap((g) => g.con.map((c) => c.toi.split("?")[0])))]
  .concat(["/tours", "/bookings", "/requests", "/leads"]);
const laKd = (h: string) => DUONG_KD.some((t) => h === t || h.startsWith(t + "/") || h.startsWith(t + "?"));

const MUC: Record<string, string> = { do: "ĐỎ", cam: "CAM", vang: "VÀNG", cho: "CHỜ NGƯỜI KHÁC" };
const so = (x: any) => (typeof x === "number" ? x.toLocaleString("vi-VN") : x);

function BanKdLe() {
  const { toast } = useShell();
  const homNay = useHomNay();
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [nhom, setNhom] = useState("tq");
  const [con, setCon] = useState(0);
  const [khung, setKhung] = useState<string | null>(null);

  const tai = useCallback(() => {
    api("/ban-kd-le/tong-quan").then((r) => { setD(r); setLoi(""); })
      .catch((e) => { setLoi(errMsg(e)); toast(errMsg(e), true); });
  }, []); // eslint-disable-line
  useEffect(() => { tai(); }, [tai]);

  /* Chữ «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu về trang tổng CRM — cùng cách /xe và /marketing. */
  useEffect(() => {
    const chu = document.querySelector("a.brand small") as HTMLElement | null;
    if (!chu) return;
    const ve = (e: Event) => { e.preventDefault(); e.stopPropagation(); window.location.assign("/"); };
    chu.title = "Về trang tổng CRM";
    chu.addEventListener("click", ve, true);
    return () => { chu.removeEventListener("click", ve, true); chu.removeAttribute("title"); };
  }, []);

  const moCon = (ma: string, i: number) => {
    const g = NHOM_KD.find((x) => x.ma === ma); if (!g) return;
    setNhom(ma); setCon(i); setKhung(g.con[i]?.toi || null);
    if (ma === "tq") tai();
  };
  /** Mở một màn theo đường dẫn: tìm thẻ con chứa nó; không thuộc thẻ nào thì vẫn mở trong khung. */
  const moToi = (toi: string) => {
    for (const g of NHOM_KD) {
      const i = g.con.findIndex((c) => c.toi === toi || c.toi.split("?")[0] === toi.split("?")[0]);
      if (i >= 0) { setNhom(g.ma); setCon(i); setKhung(toi); window.scrollTo({ top: 0 }); return; }
    }
    setKhung(toi); window.scrollTo({ top: 0 });
  };
  const ngoaiKhung = (h: string) => { if (!h.startsWith("/ban-kd-le")) return false; moCon("tq", 0); return true; };

  const g = NHOM_KD.find((x) => x.ma === nhom) || NHOM_KD[0];
  const the = d?.the || {};
  const viec: any[] = d?.viec || [];
  const nDo = viec.filter((v) => v.muc === "do").length;
  const nCho = viec.filter((v) => v.muc === "cho").length;

  return (<>
    {/* MỘT thanh đầu bàn — khuôn chung `.mh01-ban` như bàn Chủ tịch, bàn GĐ đội xe, bàn Marketing. */}
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten">Bàn làm việc Giám đốc Kinh doanh lẻ</h1>
      <div className="mh01-ban-cum"><div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div></div>
    </div>
    <nav className="kdl-nhom" aria-label="Nhóm nghiệp vụ Kinh doanh lẻ">
      {NHOM_KD.map((x) => (
        <button key={x.ma} type="button" aria-pressed={nhom === x.ma} onClick={() => moCon(x.ma, 0)}>{x.ten}</button>))}
    </nav>
    {g.con.length > 0 && <nav className="kdl-con" aria-label={`Trang của ${g.ten}`}>
      {g.con.map((c, i) => (
        <button key={c.toi} type="button" aria-pressed={con === i && khung === c.toi} onClick={() => moCon(g.ma, i)}>{c.ten}</button>))}
    </nav>}

    {khung && <KhungNhung key={khung} toi={khung} ten={g.con[con]?.ten || "Kinh doanh lẻ"}
      cuaBan={laKd} ngoai={ngoaiKhung} anDauBan />}

    {!khung && nhom === "tq" && <>
      {loi && <div className="panel"><p className="kdl-loi">Không đọc được số của bàn: {loi}</p></div>}
      {!d && !loi && <div className="panel"><p className="muted">Đang tải…</p></div>}
      {d && <>
        <div className="kdl-dai">
          {([["chuyen_dang_ban", "Chuyến đang bán", "từ bàn bán tour lẻ"],
             ["cho_con", "Chỗ còn trống", "cộng trên các chuyến đang bán"],
             ["sap_khoi_hanh", "Khởi hành trong 7 ngày", "lọc «sắp đi» của bàn bán tour lẻ"],
             ["doanh_thu_chi_tieu", "Doanh thu tính chỉ tiêu · " + (d.ket_qua?.ky || ""), "theo phạm vi đơn vị Kinh doanh lẻ"]] as const)
            .map(([k, nhan, nguon]) => { const o = the[k] || {}; return (
              <div key={k} className="kdl-the">
                <div className="t">{nhan}</div>
                {o.so == null ? <div className="s chua">chưa đo</div>
                  : <div className="s">{k === "doanh_thu_chi_tieu" ? vnd(o.so) : so(o.so)}</div>}
                <div className="d">{o.so == null ? o.ly_do : nguon}</div>
              </div>); })}
        </div>

        <div className="kdl-hai">
          <section className="kdl-khoi" aria-label="Việc cần xử lý">
            <h2>Việc cần xử lý</h2>
            <p className="kdl-dem">{viec.length} việc · {nDo} đỏ · {nCho} chờ người khác · bấm «Mở» thì màn đó mở ngay trong bàn này</p>
            {viec.map((v) => (
              <div key={v.ma} className={"kdl-v " + v.muc}>
                <div className="so">{v.muc === "cho" ? "—" : v.so == null ? "chưa đo" : so(v.so)}</div>
                <div className="g">
                  <h3>{v.ten}<span className={"muc " + v.muc}>{MUC[v.muc] || v.muc}</span>
                    {v.pham_vi === "toan_cong_ty" && <span className="nhan">toàn công ty</span>}</h3>
                  <p>{v.so == null && v.muc !== "cho" ? v.ly_do : v.mo_ta}</p>
                  {v.nguon && <div className="ng">nguồn: {v.nguon}</div>}
                </div>
                {v.toi ? <button type="button" onClick={() => moToi(v.toi)}>Mở</button>
                  : <span className="cho">chờ Điều hành</span>}
              </div>))}
          </section>

          <div className="kdl-cot">
            <section className="kdl-khoi" aria-label="Kết quả theo kỳ">
              <h2>Kết quả theo kỳ · {d.ket_qua?.ky}</h2>
              <div className="kdl-chan">
                Bảng chỉ tiêu đọc ra <b>{d.ket_qua?.booking ?? "chưa có"} booking · {d.ket_qua?.doanh_thu == null ? "chưa có" : vnd(d.ket_qua.doanh_thu) + " đ"}</b>
                {" "}doanh thu, tỷ lệ chốt báo giá <b>{d.ket_qua?.ty_le_chot == null ? "chưa có số" : d.ket_qua.ty_le_chot + "%"}</b>,
                trong khi lead mới là <b>{d.ket_qua?.lead ?? "chưa có"}</b> trên nguồn dùng chung.
                Hai số này cần đối chiếu — bàn không đoán lý do lệch.
              </div>
            </section>
            <section className="kdl-khoi" aria-label="Sẵn sàng bán">
              <h2>Sẵn sàng bán · {(d.san_sang || []).filter((x: any) => x.dat).length} / {(d.san_sang || []).length}</h2>
              <ul className="kdl-kiem">
                {(d.san_sang || []).map((x: any) => (
                  <li key={x.ten} className={x.dat ? "ok" : "chua"}><b>{x.dat ? "✓" : "·"}</b> {x.ten} · {x.so}</li>))}
              </ul>
            </section>
          </div>
        </div>

        <section className="kdl-khoi" aria-label="Chuyến cần thúc bán">
          <h2>Chuyến cần thúc bán</h2>
          <p className="kdl-dem">Chuyến khởi hành trong 7 ngày còn chỗ trống, trống nhiều nhất đứng đầu. Bấm một dòng là mở chuyến ngay trong bàn.</p>
          {(d.thuc_ban || []).length === 0 ? <p className="muted">Không có chuyến nào khởi hành trong 7 ngày còn chỗ trống.</p> :
          <div className="kdl-cuon"><table className="kdl-bang">
            <thead><tr><th>Chuyến · khởi hành</th><th>Đã bán / chỗ</th><th>Giá bán</th><th>Lợi nhuận tại số đang bán</th></tr></thead>
            <tbody>{d.thuc_ban.map((r: any) => (
              <tr key={r.id} onClick={() => moToi(`/tours/${r.id}`)}>
                <td><b>{r.code}</b> · {fmtD(r.start_date)}<div className="muted">{r.name}</div></td>
                <td>{r.cho_da_ban} / {r.cho_mo_ban}<div className="muted">còn {r.cho_con} chỗ</div></td>
                <td>{vnd(r.gia_ban)}</td>
                <td>{r.loi_nhuan_tai_so_dang_ban == null ? <span className="muted">chưa đủ cơ sở tính</span> : vnd(r.loi_nhuan_tai_so_dang_ban)}</td>
              </tr>))}</tbody>
          </table></div>}
        </section>
      </>}
    </>}
  </>);
}

/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */
const MAU = <style>{`
a.brand small{cursor:pointer;border-radius:6px;padding:2px 6px;transition:background .15s}
a.brand small:hover{background:#ffffff26;text-decoration:underline}
.kdl-nhom{position:sticky;top:var(--top-h);z-index:5;background:#eaf0f7;padding:6px 0 4px;margin-bottom:8px;
  display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px}
.kdl-nhom button{margin:0;font:inherit;font-size:13.5px;font-weight:700;color:#fff;background:#2c5fa2;border:0;
  border-radius:10px;min-height:46px;padding:8px 10px;cursor:pointer;line-height:1.2;text-align:center;box-shadow:0 2px 6px #2c5fa230}
.kdl-nhom button:hover{background:#3a6fb5}
.kdl-nhom button[aria-pressed=true]{background:#173f73;box-shadow:0 0 0 3px #9fc0ec}
.kdl-nhom button:focus-visible,.kdl-con button:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
@media(max-width:900px){.kdl-nhom{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:520px){.kdl-nhom{grid-template-columns:repeat(2,minmax(0,1fr))}}
.kdl-con{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.kdl-con button{margin:0;font:inherit;font-size:13.5px;font-weight:600;border:1px solid #c9d6e8;background:#fff;color:#1b2d44;
  border-radius:9px;padding:6px 12px;cursor:pointer}
.kdl-con button[aria-pressed=true]{border-color:#2c5fa2;color:#2c5fa2;box-shadow:inset 0 -2px 0 #2c5fa2}
.kdl-dai{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:12px}
.kdl-the{background:#fff;border:1px solid #dbe3ee;border-radius:12px;padding:12px 14px}
.kdl-the .t{font-size:12.5px;color:#5f6f86}
.kdl-the .s{font-size:30px;font-weight:800;color:#1d3a68;line-height:1.2;font-variant-numeric:tabular-nums}
.kdl-the .s.chua{font-size:16px;color:#8b9ab0;padding:10px 0 6px}
.kdl-the .d{font-size:12px;color:#8b9ab0}
.kdl-hai{display:grid;grid-template-columns:1.55fr 1fr;gap:12px;align-items:start;margin-bottom:12px}
.kdl-cot{display:grid;gap:12px;min-width:0}
.kdl-khoi{background:#fff;border:1px solid #dbe3ee;border-radius:12px;padding:14px 16px;min-width:0;margin-bottom:12px}
.kdl-hai .kdl-khoi,.kdl-cot .kdl-khoi{margin-bottom:0}
.kdl-khoi h2{margin:0 0 4px;font-size:16px;color:#1d3a68}
.kdl-dem{font-size:12.5px;color:#5f6f86;margin:0 0 6px}
.kdl-v{display:flex;gap:12px;padding:11px 0;border-top:1px solid #eef2f8;align-items:flex-start}
.kdl-v .so{flex:0 0 64px;text-align:right;font-weight:800;font-size:18px;font-variant-numeric:tabular-nums;color:#8b9ab0}
.kdl-v.do .so{color:var(--vtos-danger)}.kdl-v.cam .so{color:var(--vtos-warning)}.kdl-v.vang .so{color:#8d6200}
.kdl-v .g{flex:1;min-width:0}
.kdl-v h3{margin:0;font-size:14px;font-weight:600;color:#17263f}
.kdl-v p{margin:2px 0 0;font-size:12.5px;color:#5f6f86}
.kdl-v .ng{font-size:11.5px;color:#8b9ab0}
.kdl-v .muc,.kdl-v .nhan{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.05em;border-radius:5px;padding:1px 6px;margin-left:7px;vertical-align:1px}
.kdl-v .muc.do{background:var(--vtos-danger-bg);color:var(--vtos-danger)}
.kdl-v .muc.cam{background:var(--vtos-warning-bg);color:var(--vtos-warning)}
.kdl-v .muc.vang{background:#fbf3e0;color:#8d6200}
.kdl-v .muc.cho,.kdl-v .nhan{background:#f1f3fa;color:#5f6f86}
.kdl-v button{flex:0 0 auto;font:inherit;font-size:13px;font-weight:600;color:#2c5fa2;background:#fff;border:1px solid #c9d6e8;
  border-radius:8px;padding:4px 12px;cursor:pointer;white-space:nowrap}
.kdl-v button:hover{border-color:#2c5fa2}
.kdl-v .cho{flex:0 0 auto;font-size:12.5px;color:#8b9ab0;padding-top:4px}
.kdl-chan{background:#f4f5fc;border-radius:10px;padding:10px 12px;font-size:13px;color:#5f6f86;margin:8px 0 10px;line-height:1.6}
.kdl-kiem{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:6px;font-size:13.5px}
.kdl-kiem .ok{color:#5f6f86}.kdl-kiem .ok b{color:var(--vtos-success)}
.kdl-kiem .chua{color:#17263f}.kdl-kiem .chua b{color:#8b9ab0}
.kdl-cuon{overflow-x:auto}
.kdl-bang{width:100%;border-collapse:collapse;font-size:13px;min-width:620px}
.kdl-bang th{background:#eef2f8;text-align:left;padding:9px 12px;color:#5f6f86;font-weight:600}
.kdl-bang td{padding:10px 12px;border-top:1px solid #eef2f8;vertical-align:top}
.kdl-bang tbody tr{cursor:pointer}.kdl-bang tbody tr:hover td{background:#f6f9fd}
.kdl-loi{color:var(--vtos-danger);margin:0}
@media(max-width:1000px){.kdl-dai{grid-template-columns:repeat(2,minmax(0,1fr))}.kdl-hai{grid-template-columns:1fr}}
@media(max-width:520px){.kdl-dai{grid-template-columns:1fr}.kdl-v{flex-wrap:wrap}.kdl-v .so{flex-basis:auto;text-align:left}}
`}</style>;

export default function Page() { return <Shell khongThanhBen>{MAU}<BanKdLe /></Shell>; }
