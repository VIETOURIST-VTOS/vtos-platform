"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import KhungNhung from "@/components/KhungNhung";
import TrangPhanHe from "@/components/TrangPhanHe";
import DoanhThuChiTieuKd from "@/components/DoanhThuChiTieuKd";
import { useHomNay } from "@/components/DauManHinh01";
import NutLich90, { VAI_NUT_LICH_90 } from "@/components/NutLich90";
import { api, vnd, fmtD } from "@/lib/api";
import { errMsg } from "@/components/ui";

/** R5-4 · BÀN LÀM VIỆC GIÁM ĐỐC KINH DOANH LẺ THEO MẪU v32 — Chủ tịch 13/11/2026 05:49:
 *  «giao diện bàn làm việc của GĐKD chưa giống theo mẫu đề xuất» (vietourist-vtd-v32-demo
 *  /giam-doc-kinh-doanh, bản vẽ đã duyệt 13/11/2026). GĐ KD đăng nhập vào /fit là gặp bàn này.
 *
 *  Khuôn v32: dòng tiêu đề (nhãn nhỏ · tên bàn · câu dẫn · ô Hôm nay), thanh sáu tab trắng (tab đang
 *  mở tô navy), Tổng quan = 4 thẻ số + «Việc cần xử lý» + «Kết quả theo kỳ» + «Chuyến cần thúc bán»;
 *  năm tab còn lại = lưới thẻ hai cột. KHÁC v32 MỘT CHỖ, theo luật 13/11/2026 «mỗi người chỉ làm việc
 *  trên một bàn của mình»: bấm thẻ thì màn ấy mở NGAY TRONG BÀN (khung nhúng, hoặc thân màn đặt thẳng
 *  vào với hai màn của chính /fit), không nhảy sang màn khác.
 *
 *  R5-6 · 13/11/2026 (Chủ tịch duyệt bản xem trước): thanh ngang dùng `.mh01-ban` như bàn Chủ tịch và GĐ
 *  đội xe; sáu nút tab đều xanh navy sáng, nút đang mở đậm hơn có viền sáng; điểm nhấn navy sáng ở thẻ số,
 *  đầu khối, nút kỳ, đầu bảng.
 *
 *  CHỈ ĐỌC, mọi số đọc từ `/ban-kd-le/tong-quan` (backend/app/services/ban_kd_le.py). Ô `null` in
 *  «chưa đo» kèm lý do, không in 0. «Bàn Sale Admin» của v32 KHÔNG có: Chủ tịch chốt làm đợt riêng.
 */

type The = { ten: string; mo_ta: string; toi?: string; noi?: "doanh-thu" | "bang" };
const TAB: { ma: string; ten: string; tieu_de?: string; the: The[] }[] = [
  { ma: "tq", ten: "Tổng quan", the: [] },
  { ma: "ban", ten: "Bán hàng", tieu_de: "Bán hàng", the: [
    { ten: "Bàn bán tour lẻ", mo_ta: "Chỗ trống, ngày đi và dự toán chuyến", toi: "/ban-tour-le" },
    { ten: "Lịch khởi hành", mo_ta: "Danh sách chuyến tour lẻ", toi: "/tours?mang=le" },
    { ten: "Lịch xe trống", mo_ta: "Phối hợp đội xe để bán tour", toi: "/lich-xe-trong" },
    { ten: "Báo giá", mo_ta: "Soạn nháp, kiểm tra biên trước khi gửi khách", toi: "/bao-gia?mang=kd_le" },
    { ten: "Giá & chính sách bán", mo_ta: "Bảng giá và thời hạn áp dụng", toi: "/bang-gia" },
    { ten: "Dịch vụ lẻ", mo_ta: "Visa, vé, phòng, xe và dịch vụ rời", toi: "/non-package" },
    { ten: "Khách sạn & vé máy bay OTA", mo_ta: "Màn liên kết OTA trong phân hệ", toi: "/khach-san-ota" }] },
  { ma: "khach", ten: "Khách & booking", tieu_de: "Khách & booking", the: [
    { ten: "Khách hàng & nguồn khách", mo_ta: "Hồ sơ, lead, kênh và đối chiếu chuyển đổi", toi: "/leads?tab=leads" },
    { ten: "Hộp thư đa kênh", mo_ta: "Hội thoại và khách chờ sale", toi: "/inbox" },
    { ten: "Yêu cầu đặt dịch vụ", mo_ta: "Gửi Điều hành, theo dõi người nhận và hạn xử lý", toi: "/requests?mang=le" },
    { ten: "Booking & bảo lưu", mo_ta: "Cọc, thu tiền, giữ chỗ, hủy và bảo lưu", toi: "/bookings?mang=le" },
    { ten: "Yêu cầu từ cổng khách", mo_ta: "Phản hồi yêu cầu khách gửi từ VTD", toi: "/yeu-cau-khach" },
    { ten: "Đơn phòng OTA", mo_ta: "Theo dõi đơn khách sạn OTA", toi: "/don-khach-san-ota" }] },
  { ma: "cs", ten: "Chăm sóc", tieu_de: "Chăm sóc khách hàng", the: [
    { ten: "Chăm sóc sau tour", mo_ta: "Kết quả liên hệ, quá hạn, khách quay lại", toi: "/cham-soc" },
    { ten: "Phản hồi & khiếu nại", mo_ta: "Hồ sơ khiếu nại hiện có", toi: "/khieu-nai" },
    { ten: "Đánh giá sau tour", mo_ta: "Theo dõi phản hồi chuyến đi", toi: "/danh-gia" },
    { ten: "VTD Rewards", mo_ta: "Chương trình khách hàng", toi: "/vtd-rewards" },
    { ten: "Góp ý riêng lãnh đạo", mo_ta: "Chỉ hiển thị theo quyền đã được cấp", toi: "/gop-y-lanh-dao" }] },
  { ma: "doi", ten: "Đội ngũ", tieu_de: "Đội ngũ kinh doanh", the: [
    { ten: "Cơ cấu tổ chức", mo_ta: "Chi nhánh → phòng → team → người; có ngày hiệu lực", toi: "/to-chuc-kd" },
    { ten: "Người bán hàng", mo_ta: "Danh mục và phạm vi người bán", toi: "/nguoi-ban-hang" }] },
  { ma: "ct", ten: "Chỉ tiêu & báo cáo", tieu_de: "Chỉ tiêu & báo cáo", the: [
    { ten: "Chỉ tiêu kinh doanh", mo_ta: "Doanh thu theo phạm vi và kỳ, giao chỉ tiêu", noi: "doanh-thu" },
    { ten: "Báo cáo bán hàng", mo_ta: "Bán tour, nhắc thu, hủy chỗ, kinh doanh, tour lẻ", toi: "/sales-reports?mang=le" },
    { ten: "Báo cáo ngày / tuần / tháng", mo_ta: "Bảng chỉ tiêu phòng và bản chụp kỳ trước", noi: "bang" },
    { ten: "Đối soát OTA", mo_ta: "Màn đối soát hiện có trong menu", toi: "/doi-soat-ota" }] },
];

/** Màn được mở TRONG khung: mọi thẻ ở trên, cộng hồ sơ chuyến/booking/khách bấm từ bên trong chúng. */
const DUONG_KD = [...new Set(TAB.flatMap((t) => t.the.filter((x) => x.toi).map((x) => (x.toi as string).split("?")[0])))]
  .concat(["/tours", "/bookings", "/requests", "/leads"]);
const laKd = (h: string) => DUONG_KD.some((t) => h === t || h.startsWith(t + "/") || h.startsWith(t + "?"));

const BIEU: Record<string, string> = {
  chua_don_vi: "⬢", chua_du_toan: "▣", cham_soc_qua_han: "♡", hop_thu_cho: "✉",
  sap_khoi_hanh: "◴", lech_mang: "☰", cho_dieu_hanh: "⟳",
};
const LOI_VAO: Record<string, string> = {
  chua_don_vi: "Cơ cấu tổ chức", chua_du_toan: "Xem chuyến", cham_soc_qua_han: "Xem chăm sóc",
  hop_thu_cho: "Xem hộp thư", sap_khoi_hanh: "Xem chuyến gần", lech_mang: "Xem báo cáo",
};
const CONG: Record<string, [string, string]> = {
  dat: ["Đạt biên", "dat"], khong_dat: ["Dưới biên", "duoi"], chua_du_co_so: ["Chưa đủ dữ liệu", "chua"],
};
const so = (x: any) => (typeof x === "number" ? x.toLocaleString("vi-VN") : x);
const chuThuong = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);

/** Một ô số của dải «Hoạt động tour lẻ». */
function OSo({ nhan, v, phu, lk, bam }: { nhan: string; v: any; phu: string; lk: string; bam?: () => void }) {
  return <div className="g5-hd">
    <span className="n">{nhan}</span>
    <span className={"s" + (v === undefined ? " dang" : "")}>{v === undefined ? "…" : v === null ? "—" : so(v)}</span>
    <span className="p">{phu}</span>
    {bam ? <button type="button" className="g5-cua" onClick={bam}>{lk} →</button> : <span className="g5-cua tat">{lk}</span>}
  </div>;
}

const tien = (v: number) => v >= 1e9 ? (v / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) + " tỷ"
  : v >= 1e6 ? Math.round(v / 1e6).toLocaleString("vi-VN") + " tr" : vnd(v) + " đ";

export default function BanGdKdLe() {
  const { toast, datViecBan, user } = useShell();
  const homNay = useHomNay();
  const [d, setD] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [tab, setTab] = useState("tq");
  const [mo, setMo] = useState<The | null>(null);
  const [khung, setKhung] = useState<string | null>(null);
  const [hetBang, setHetBang] = useState(false);   // bảng chuyến: 6 dòng đầu, bấm để xem hết

  const [dt, setDt] = useState<any>(null);
  const [kyDt, setKyDt] = useState<"thang" | "quy" | "nam">("nam");
  const taiDt = useCallback(() => {
    api(`/ban-kd-le/doanh-thu?nam=${new Date().getFullYear()}`).then(setDt).catch(() => setDt({ loi: true }));
  }, []);
  useEffect(() => { taiDt(); }, [taiDt]);
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

  const moTab = (ma: string) => { setTab(ma); setMo(null); setKhung(null); if (ma === "tq") tai(); };
  const moThe = (t: The) => { setMo(t); setKhung(t.toi || null); window.scrollTo({ top: 0 }); };
  /** Mở theo đường dẫn (từ một việc / một dòng chuyến): tìm thẻ chứa nó, không có thì vẫn mở trong khung. */
  const moToi = (toi: string) => {
    for (const t of TAB) {
      const x = t.the.find((c) => c.toi && c.toi.split("?")[0] === toi.split("?")[0]);
      if (x) { setTab(t.ma); setMo(x); setKhung(toi); window.scrollTo({ top: 0 }); return; }
    }
    if (toi.startsWith("/fit")) { setTab("ct"); moThe(TAB[5].the[2]); return; }
    setMo({ ten: "Chi tiết", mo_ta: "" }); setKhung(toi); window.scrollTo({ top: 0 });
  };
  const ngoaiKhung = (h: string) => {
    if (h.startsWith("/fit")) { moTab("tq"); return true; }
    return false;
  };

  /* R5-4 (Chủ tịch 13/11/2026): «việc cần xử lý đưa lên mục Công việc trên thanh ngang» — cùng cơ chế
     bàn đội xe (VH-42): rê chuột vào nút Công việc là xổ, bấm một dòng thì màn ấy mở NGAY TRONG BÀN. */
  useEffect(() => {
    if (!d) return;
    datViecBan((d.viec || []).map((v: any) => ({
      ma: v.ma, muc: v.muc,
      tieu_de: v.muc === "cho" || v.so == null ? v.ten : `${so(v.so)} ${chuThuong(v.ten)}`,
      mo_ta: v.so == null && v.muc !== "cho" ? `chưa đo — ${v.ly_do}` : v.mo_ta + (v.pham_vi === "toan_cong_ty" ? " · số toàn công ty" : ""),
      bam: v.toi ? () => moToi(v.toi) : undefined })));
  }, [d, datViecBan]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => datViecBan(null), [datViecBan]);

  const t = TAB.find((x) => x.ma === tab) || TAB[0];
  const the = d?.the || {};
  const viec: any[] = d?.viec || [];
  const hd = d?.hoat_dong;
  const pt = d?.phai_thu;
  // Doanh thu – chỉ tiêu: kỳ đang chọn tô đậm trên cùng 12 cột (khuôn TC-44 của Chủ tịch).
  const thangNay = new Date().getMonth() + 1;
  const trongKy = (m: number) => kyDt === "nam" || (kyDt === "thang" ? m === thangNay : Math.ceil(m / 3) === Math.ceil(thangNay / 3));
  const dsT: any[] = dt?.thang || [];
  const cong = (k: string) => { const v = dsT.filter((x, i) => trongKy(i + 1) && x[k] != null).map((x) => x[k]); return v.length ? v.reduce((a: number, b: number) => a + b, 0) : null; };
  const dtKy = cong("doanh_thu"), ctKy = cong("chi_tieu");
  const dinh = Math.max(1, ...dsT.map((x) => Math.max(x.doanh_thu || 0, x.chi_tieu || 0)));
  const nhanKy = kyDt === "nam" ? `Năm ${dt?.nam || ""}` : kyDt === "quy" ? `Quý ${Math.ceil(thangNay / 3)}/${dt?.nam || ""}` : `Tháng ${thangNay}/${dt?.nam || ""}`;

  return (<div className="g5">
    {/* R5-6 · Chủ tịch duyệt 13/11/2026: thanh ngang ĐỒNG NHẤT với bàn Chủ tịch và GĐ đội xe — cùng lớp
        `.mh01-ban` (globals.css): tên bàn in hoa có vệt sáng, ô Hôm nay, nút Lịch xe 90 ngày. */}
    <div className="mh01-ban">
      <h1 className="mh01-ban-ten">Bàn làm việc Giám đốc Kinh doanh lẻ</h1>
      <div className="mh01-ban-cum">
        <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
        {user?.role && VAI_NUT_LICH_90.includes(user.role) && <NutLich90 />}
      </div>
    </div>

    <nav className="g5-tab" aria-label="Bàn Giám đốc Kinh doanh lẻ">
      {TAB.map((x) => (
        <button key={x.ma} type="button" aria-pressed={tab === x.ma} onClick={() => moTab(x.ma)}>{x.ten}</button>))}
    </nav>

    {mo && <div className="g5-mo">
      <button type="button" className="g5-lui" onClick={() => { setMo(null); setKhung(null); }}>‹ {t.tieu_de || "Tổng quan"}</button>
      <b>{mo.ten}</b>
    </div>}
    {mo && khung && <KhungNhung key={khung} toi={khung} ten={mo.ten} cuaBan={laKd} ngoai={ngoaiKhung} anDauBan />}
    {mo && !khung && mo.noi === "doanh-thu" && <DoanhThuChiTieuKd />}
    {mo && !khung && mo.noi === "bang" && <TrangPhanHe khoa="kdle" khongThanh />}

    {!mo && tab !== "tq" && <>
      <div className="g5-muc"><h2>{t.tieu_de}</h2><p>Mỗi chức năng có một vị trí chính · bấm là mở ngay trong bàn</p></div>
      <div className="g5-luoi">
        {t.the.map((x) => (
          <button key={x.ten} type="button" className="g5-the-lk" onClick={() => moThe(x)}>
            <span><b>{x.ten}</b><small>{x.mo_ta}</small></span><i aria-hidden="true">↗</i>
          </button>))}
      </div>
    </>}

    {!mo && tab === "tq" && <>
      {loi && <div className="g5-khoi"><p className="g5-loi">Không đọc được số của bàn: {loi}</p></div>}

      {/* R5-4: 4 thẻ số + khối Hoạt động tour gộp MỘT dải, bỏ hai thẻ trùng (Chủ tịch 13/11/2026). */}
      <p className="g5-nhom">HOẠT ĐỘNG TOUR LẺ</p>
      <div className="g5-dai5">
        <OSo nhan="Tour đang bán" v={d ? hd?.dang_ban : undefined} phu="Đã duyệt, chưa tới ngày đi" lk="Xem tour đang bán" bam={() => moToi("/tours?mang=le")} />
        <OSo nhan="Chỗ còn trống" v={d ? hd?.cho_con : undefined} phu="Trên các chuyến đang bán" lk="Bàn bán tour lẻ" bam={() => moToi("/ban-tour-le")} />
        <OSo nhan="Sắp khởi hành" v={d ? hd?.sap_khoi_hanh : undefined} phu="7 ngày tới" lk="Xem chuyến gần" bam={() => moToi("/ban-tour-le")} />
        <OSo nhan="Tour đang đi" v={d ? hd?.dang_di : undefined} phu="Đang trong hành trình · mọi tour" lk="Xem tour đang đi" bam={() => moToi("/tours?mang=le")} />
        <OSo nhan="Khách tiềm năng mới" v={null} phu="Chưa có nguồn · không thay bằng 0 (Marketing)" lk="Cửa nhập" bam={() => moToi("/leads?tab=leads")} />
      </div>

      <div className="g5-hai">
        <section className="g5-khoi" aria-label="Doanh thu – chỉ tiêu tour lẻ">
          <div className="g5-dau"><h2>Doanh thu – chỉ tiêu tour lẻ</h2><span>{nhanKy}</span></div>
          <div className="g5-ky" role="group" aria-label="Kỳ">
            {([["thang", "Tháng"], ["quy", "Quý"], ["nam", "Năm"]] as const).map(([k, ten]) => (
              <button key={k} type="button" aria-pressed={kyDt === k} onClick={() => setKyDt(k)}>{ten}</button>))}
          </div>
          {!dt ? <p className="g5-nho">Đang đọc doanh thu…</p> : dt.loi ? <p className="g5-loi">Không đọc được doanh thu.</p> : <>
            <div className="g5-ba">
              <div><b>{dtKy == null ? "chưa có" : tien(dtKy)}</b><small>Doanh thu · {nhanKy}</small></div>
              <div><b>{ctKy == null ? "chưa giao" : tien(ctKy)}</b><small>Chỉ tiêu</small></div>
              <div className="dat"><b>{dtKy != null && ctKy ? Math.round((dtKy / ctKy) * 100) + "%" : "—"}</b><small>Tỷ lệ đạt</small></div>
            </div>
            {dt.ly_do_chi_tieu && <p className="g5-nho">{dt.ly_do_chi_tieu}</p>}
            <div className="g5-chu"><span><i className="c" />Doanh thu</span><span><i className="k" />Chỉ tiêu tháng</span></div>
            <div className="g5-bd" role="img" aria-label="Doanh thu và chỉ tiêu tour lẻ 12 tháng">
              {dsT.map((x, i) => (
                <div key={x.ky} className={"g5-c" + (trongKy(i + 1) ? " on" : "")} title={`${x.ky}: ${x.doanh_thu == null ? "chưa có" : tien(x.doanh_thu)}`}>
                  <div className="g5-c-o">
                    {x.chi_tieu != null && <s style={{ bottom: (x.chi_tieu / dinh) * 100 + "%" }} />}
                    {x.doanh_thu != null && <i style={{ height: Math.max(1, (x.doanh_thu / dinh) * 100) + "%" }} />}
                  </div>
                  <span>T{i + 1}</span>
                </div>))}
            </div>
          </>}
        </section>

        <section className="g5-khoi" aria-label="Phải thu khách hàng">
          <div className="g5-dau"><h2>Phải thu khách hàng</h2><span>Booking tour lẻ · theo hạn</span></div>
          {!d ? <p className="g5-nho">Đang đọc số…</p> : !pt || pt.tong == null ? <p className="g5-nho">{pt?.ly_do || "chưa đo"}</p> : <>
            <div className="g5-han">
              {Object.entries(pt.nhom).map(([nhan, v]: [string, any]) => {
                const max = Math.max(1, ...Object.values(pt.nhom).map((x: any) => x || 0));
                return <div key={nhan} className={"h" + (nhan === "Quá hạn" ? " qh" : "")}>
                  <span>{nhan}</span><span className="tr"><i style={{ width: ((v || 0) / max) * 100 + "%" }} /></span><b>{tien(v || 0)}</b></div>; })}
            </div>
            <p className="g5-nho">Tổng phải thu <b>{tien(pt.tong)}</b> · <b>{so(pt.so_booking)}</b> booking còn nợ. Hạn = ngày khởi hành của chuyến.</p>
            <button type="button" className="g5-cua" onClick={() => moToi("/bookings?mang=le")}>Xem booking còn nợ →</button>
          </>}
        </section>
      </div>

      <section className="g5-khoi" aria-label="Chuyến cần thúc bán">
        <div className="g5-dau"><div><h2>Chuyến cần thúc bán</h2>
          <span>Khởi hành trong 7 ngày, còn chỗ trống · ưu tiên chuyến trống nhiều</span></div></div>
        {!d ? <p className="g5-nho">Đang đọc số…</p> : (d.thuc_ban || []).length === 0
          ? <p className="g5-nho">Không có chuyến nào khởi hành trong 7 ngày còn chỗ trống.</p>
          : <div className="g5-cuon"><table className="g5-bang">
            <thead><tr><th>Chuyến / khởi hành</th><th>Đã bán / chỗ mở</th><th>Giá bán</th><th>Hòa vốn</th>
              <th>Lãi {Math.round(((d.thuc_ban[0]?.bien_muc_tieu) || 0.1) * 100)}%</th><th>Bán đủ khách</th><th /></tr></thead>
            <tbody>{(hetBang ? d.thuc_ban : d.thuc_ban.slice(0, 6)).map((r: any) => {
              const pt2 = r.cho_mo_ban ? Math.min(100, Math.round((r.cho_da_ban / r.cho_mo_ban) * 100)) : 0;
              const co = r.khach_hoa_von != null;
              const thieu = (n: number | null) => n == null ? <div className="ngay">không đạt được ở giá này</div>
                : n - r.cho_da_ban > 0 ? <div className="ngay">còn thiếu <b className="cam">{n - r.cho_da_ban}</b> khách</div>
                : <div className="ngay dat">đã đạt</div>;
              return (
              <tr key={r.id}>
                <td><b className="ma">{r.code}</b><div className="ngay">{fmtD(r.start_date)} · {r.name}</div></td>
                <td><b>{r.cho_da_ban} / {r.cho_mo_ban}</b><div className="ngay">Còn {r.cho_con} chỗ</div>
                  <div className="vach">{co && r.cho_mo_ban ? <s style={{ left: Math.min(100, (r.khach_hoa_von / r.cho_mo_ban) * 100) + "%" }} /> : null}
                    <i style={{ width: pt2 + "%" }} /></div></td>
                <td>{vnd(r.gia_ban)} đ</td>
                {co ? <>
                  <td><b>{r.khach_hoa_von} khách</b>{thieu(r.khach_hoa_von)}</td>
                  <td>{r.khach_dat_bien == null ? <span className="ngay">không đạt được ở giá này</span>
                    : <><b>{r.khach_dat_bien} khách</b>{thieu(r.khach_dat_bien)}</>}</td>
                  <td><b className={"lai" + ((r.bien_khi_day ?? 0) < 0 ? " lo" : "")}>{r.bien_khi_day == null ? "—" : (r.bien_khi_day * 100).toFixed(1).replace(".", ",") + "%"}</b>
                    <div className="ngay">nếu bán đủ {r.khach_toi_da} khách</div></td>
                </> : <td colSpan={3}><span className="nhan chua">Chưa có dự toán riêng — Điều hành nhập ba con số dự toán thì ba cột này tự hiện</span></td>}
                <td><button type="button" className="g5-cua" onClick={() => moToi(`/tours/${r.id}`)}>Chi tiết →</button></td>
              </tr>); })}</tbody>
          </table>
          {d.thuc_ban.length > 6 && <button type="button" className="g5-them" onClick={() => setHetBang(!hetBang)}>
            {hetBang ? "Thu gọn" : `Xem thêm ${d.thuc_ban.length - 6} chuyến`}</button>}
          <p className="g5-nho">Vạch đỏ trên thanh tiến độ là điểm hòa vốn. Tính từ ba con số dự toán của chuyến; mức lãi đọc tham số «ngưỡng biên»; bán đủ = 45 khách, chuyến mở ít chỗ hơn thì tính theo số chỗ mở.</p>
          </div>}
      </section>

      {d && <details className="g5-nguon">
        <summary>Nguồn số liệu &amp; trạng thái</summary>
        <ul>{viec.filter((v) => v.nguon).map((v) => <li key={v.ma}><b>{v.ten}</b> — {v.nguon}{v.pham_vi === "toan_cong_ty" ? " · toàn công ty, chưa tách phần Kinh doanh lẻ" : ""}</li>)}
          <li><b>Hoạt động tour, chuyến cần thúc bán</b> — /ban-tour-le, đọc ngày {fmtD(d.ngay)}; «Tour đang đi» đếm mọi tour như trang chủ</li>
          <li><b>Doanh thu</b> — ngăn tour lẻ của doanh thu Chủ tịch đang xem; <b>chỉ tiêu</b> — chỉ tiêu giao cho đơn vị gốc Kinh doanh lẻ</li>
          <li><b>Phải thu</b> — booking tour lẻ chưa huỷ, giá trị trừ đã thu; hạn là ngày khởi hành</li></ul>
      </details>}
    </>}

    {/* Không dùng dấu backtick trong khối style dưới đây (bài học MKT-6/7). */}
    <style>{`
.g5{--g5-ns-a:#2f6fc0;--g5-ns-b:#1f4f97;--g5-ns-c:#5b9be6;--g5-ns-nhat:#e8f0fc;--g5-ns-vien:#c9dbf5;--g5-navy:#1f3b6d;--g5-xanh:#2b5ea8;--g5-line:#e3e9f2;--g5-line2:#eef2f8;--g5-chu:#17263f;--g5-chu2:#5a6b85;--g5-chu3:#8b9ab0;--g5-dam:#1d3a68;
  display:flex;flex-direction:column;gap:14px;color:var(--g5-chu)}
.g5-tab{display:flex;gap:8px;background:#fff;border:1px solid var(--g5-ns-vien);border-radius:16px;padding:6px;overflow-x:auto;
  box-shadow:0 1px 2px rgba(31,79,151,.06),0 6px 18px rgba(31,79,151,.08)}
.g5-tab button{flex:1 0 auto;margin:0;font:inherit;text-align:center;padding:11px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.2);
  font-size:14px;font-weight:700;color:#fff;cursor:pointer;white-space:nowrap;transition:background .15s,transform .15s;
  background:linear-gradient(120deg,var(--g5-ns-c),#3f80d0);box-shadow:0 2px 6px rgba(31,79,151,.22),inset 0 1px 0 rgba(255,255,255,.3)}
.g5-tab button:hover{background:linear-gradient(120deg,#4a8ddc,var(--g5-ns-a));transform:translateY(-1px)}
.g5-tab button[aria-pressed=true]{background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));
  box-shadow:0 0 0 2px #fff,0 0 0 4px #7fb2f0,0 6px 16px rgba(31,79,151,.4),inset 0 1px 0 rgba(255,255,255,.25)}
.g5-tab button:focus-visible,.g5-the-lk:focus-visible,.g5-cua:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
.g5-mo{display:flex;align-items:center;gap:12px}
.g5-lui{margin:0;font:inherit;font-size:13px;font-weight:700;color:var(--g5-ns-b);background:var(--g5-ns-nhat);border:1px solid var(--g5-ns-vien);border-radius:999px;padding:5px 12px;cursor:pointer}
.g5-muc h2{margin:0;font-size:19px;font-weight:600;color:var(--g5-dam)}
.g5-muc p{margin:2px 0 0;font-size:12.5px;color:var(--g5-chu3)}
.g5-luoi{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.g5-the-lk{margin:0;font:inherit;text-align:left;display:flex;justify-content:space-between;align-items:center;gap:10px;background:#fff;
  border:1px solid var(--g5-line);border-radius:10px;padding:16px 16px;cursor:pointer;color:inherit}
.g5-the-lk:hover{border-color:var(--g5-ns-vien);box-shadow:0 8px 20px rgba(31,79,151,.12)}
.g5-the-lk{border-left:4px solid var(--g5-ns-a)}
.g5-the-lk b{display:block;font-size:14.5px;color:var(--g5-dam)}
.g5-the-lk small{display:block;font-size:12.5px;color:var(--g5-chu2);margin-top:3px}
.g5-the-lk i{font-style:normal;flex:none;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;color:#fff;background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b))}
.g5-dai{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}
.g5-so{background:#fff;border:1px solid var(--g5-line);border-radius:12px;padding:16px 18px}
.g5-so .t{font-size:12.5px;color:var(--g5-chu2)}
.g5-so .s{font-size:34px;font-weight:800;color:var(--g5-dam);line-height:1.15;margin:4px 0 6px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.g5-so .s.dang{color:var(--g5-chu3)}
.g5-so .gach{display:block;width:34px;height:5px;border-radius:3px;background:var(--g5-dam);margin:16px 0 15px}
.g5-so .d{font-size:12px;color:var(--g5-chu3)}
.g5-hai{display:grid;grid-template-columns:1.55fr 1fr;gap:14px;align-items:start}
.g5-cot{display:grid;gap:14px;min-width:0}
.g5-khoi{background:#fff;border:1px solid var(--g5-line);border-radius:16px;padding:18px 20px;min-width:0;box-shadow:0 1px 2px rgba(23,38,63,.04)}
.g5-dau{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--g5-line2)}
.g5-dau h2{margin:0;font-size:16.5px;font-weight:700;color:var(--g5-dam);display:flex;align-items:center;gap:9px}
.g5-dau h2::before{content:"";flex:none;width:4px;height:18px;border-radius:3px;background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-dau span{font-size:12px;color:var(--g5-chu3)}
.g5-v{display:flex;gap:13px;align-items:flex-start;padding:13px 0;border-top:1px solid var(--g5-line2)}
.g5-v .bi{flex:0 0 auto;width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:14px;margin-top:1px;background:#f4f5fc;color:var(--g5-chu2)}
.g5-v.do .bi{background:#fdeceb;color:#b3281f}.g5-v.cam .bi{background:#fcf1e5;color:#a85c16}.g5-v.vang .bi{background:#fbf3e0;color:#8d6200}
.g5-v .g{flex:1;min-width:0}
.g5-v h3{margin:0;font-size:14.5px;font-weight:600;color:var(--g5-chu);line-height:1.4}
.g5-v p{margin:2px 0 0;font-size:12.5px;color:var(--g5-chu3)}
.g5-cua{flex:0 0 auto;margin:0;font:inherit;font-size:13px;font-weight:600;color:var(--g5-dam);background:none;border:0;padding:3px 0;cursor:pointer;white-space:nowrap}
.g5-cua:hover{color:var(--g5-xanh);text-decoration:underline}
.g5-cua.tat{color:var(--g5-chu3);font-weight:500;cursor:default}
.g5-chan{background:#f4f5fc;border:1px solid #e4e7f6;border-radius:11px;padding:15px 16px;margin-top:8px}
.g5-chan h3{margin:0 0 6px;font-size:15px;font-weight:700;color:var(--g5-chu)}
.g5-chan p{margin:0;font-size:12.5px;color:var(--g5-chu2);line-height:1.6}
.g5-nho{font-size:12.5px;color:var(--g5-chu2);margin:10px 0 0;line-height:1.6}
.g5-kiem{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:7px;font-size:13px}
.g5-kiem b{display:inline-block;width:16px}
.g5-kiem .ok{color:var(--g5-chu2)}.g5-kiem .ok b{color:#1c6f50}.g5-kiem .chua b{color:var(--g5-chu3)}
.g5-cuon{overflow-x:auto}
.g5-bang{width:100%;border-collapse:separate;border-spacing:0;margin-top:10px;font-size:13px;min-width:640px}
.g5-bang th{background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));color:#fff;font-weight:600;font-size:12px;text-align:left;padding:11px 13px}
.g5-bang th:first-child{border-radius:10px 0 0 10px}.g5-bang th:last-child{border-radius:0 10px 10px 0}
.g5-bang tbody tr:hover td{background:#f6f9fe}
.g5-bang td{padding:13px;border-bottom:1px solid var(--g5-line2);vertical-align:top}
.g5-bang tr:last-child td{border-bottom:0}
.g5-bang .ma{color:var(--g5-dam);font-variant-numeric:tabular-nums}
.g5-bang .ngay{font-size:12px;color:var(--g5-chu3);margin-top:2px}
.g5-bang .vach{width:74px;height:4px;border-radius:2px;background:#e4eaf4;margin-top:6px;overflow:hidden}
.g5-bang .vach i{display:block;height:100%;border-radius:2px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-bang .nhan{display:inline-block;font-size:11.5px;font-weight:600;border-radius:6px;padding:4px 9px}
.g5-bang .nhan.chua{background:#fbf3e0;color:#8d6200}.g5-bang .nhan.dat{background:#e8f5ef;color:#1c6f50}.g5-bang .nhan.duoi{background:#fdeceb;color:#b3281f}
.g5-loi{color:var(--vtos-danger);margin:0}
.g5-nhom{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:800;letter-spacing:.12em;color:var(--g5-ns-b);margin:2px 0 -6px}
.g5-nhom::before{content:"";width:4px;height:14px;border-radius:3px;background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-dai5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}
.g5-hd{position:relative;overflow:hidden;background:#fff;border:1px solid var(--g5-line);border-radius:14px;padding:16px 16px 14px;display:flex;flex-direction:column;gap:2px;min-width:0;
  box-shadow:0 1px 2px rgba(23,38,63,.04);transition:border-color .15s,box-shadow .15s,transform .15s}
.g5-hd::before{content:"";position:absolute;inset:0 0 auto;height:4px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}
.g5-hd:hover{border-color:var(--g5-ns-vien);box-shadow:0 8px 20px rgba(31,79,151,.12);transform:translateY(-1px)}
.g5-hd .n{font-size:13px;font-weight:600;color:var(--g5-chu2)}
.g5-hd .s{font-size:30px;font-weight:800;color:var(--g5-ns-b);font-variant-numeric:tabular-nums}.g5-hd .s.dang{color:var(--g5-chu3)}
.g5-hd .p{font-size:12.5px;color:var(--g5-chu3);flex:1}
.g5-hd .g5-cua{align-self:flex-start;margin-top:8px;font-size:12.5px;font-weight:700;color:var(--g5-ns-b);background:var(--g5-ns-nhat);border-radius:999px;padding:5px 11px}
.g5-hd .g5-cua:hover{background:var(--g5-ns-a);color:#fff;text-decoration:none}
.g5-hd .g5-cua.tat{background:#f1f3f7;color:var(--g5-chu3)}
.g5-ky{display:inline-flex;background:var(--g5-ns-nhat);border-radius:999px;padding:3px;margin:2px 0 8px}
.g5-ky button{margin:0;font:inherit;font-size:12.5px;font-weight:600;border:0;background:none;color:var(--g5-ns-b);padding:5px 14px;border-radius:999px;cursor:pointer}
.g5-ky button[aria-pressed=true]{background:linear-gradient(120deg,var(--g5-ns-a),var(--g5-ns-b));color:#fff;box-shadow:0 2px 6px rgba(31,79,151,.3)}
.g5-ba{display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 8px}
.g5-ba>div{background:linear-gradient(180deg,#f6f9fe,#eef4fc);border:1px solid var(--g5-ns-vien);border-radius:12px;padding:10px 14px;min-width:150px}
.g5-ba b{display:block;font-size:20px;font-weight:800;color:var(--g5-ns-b)}.g5-ba small{font-size:12px;color:var(--g5-chu3)}.g5-ba .dat b{color:#1c6f50}
.g5-chu{display:flex;gap:14px;font-size:12px;color:var(--g5-chu2);margin:6px 0}
.g5-chu i{display:inline-block;width:12px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.g5-chu i.c{background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}.g5-chu i.k{height:0;border-top:2px dashed #e0a64b;border-radius:0;vertical-align:3px}
.g5-bd{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:6px;height:190px;align-items:end;border-bottom:1px solid var(--g5-line);padding-top:6px}
.g5-c{display:flex;flex-direction:column;align-items:center;height:100%;gap:4px;opacity:.45}.g5-c.on{opacity:1}
.g5-c-o{position:relative;flex:1;width:100%;display:flex;align-items:flex-end;justify-content:center}
.g5-c-o i{display:block;width:62%;background:linear-gradient(var(--g5-ns-c),var(--g5-ns-a));border-radius:6px 6px 2px 2px}
.g5-c.on .g5-c-o i{background:linear-gradient(var(--g5-ns-a),var(--g5-ns-b))}
.g5-c-o s{position:absolute;left:4%;right:4%;border-top:2px dashed #e0a64b;text-decoration:none}
.g5-c span{font-size:10.5px;color:var(--g5-chu3)}
.g5-han{display:grid;gap:9px;margin-top:6px}
.g5-han .h{display:grid;grid-template-columns:74px 1fr 64px;gap:10px;align-items:center;font-size:13px}
.g5-han .tr{height:12px;border-radius:6px;background:var(--g5-line2);overflow:hidden}
.g5-han .tr i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,var(--g5-ns-a),var(--g5-ns-c))}.g5-han .h.qh .tr i{background:#a3185a}
.g5-han b{text-align:right;font-variant-numeric:tabular-nums}
.g5-bang .ngay b.cam{color:#a85c16}.g5-bang .ngay.dat{color:#1c6f50;font-weight:600}
.g5-bang b.lai{color:#1c6f50;font-size:15px}.g5-bang b.lai.lo{color:#b3281f}
.g5-bang .vach{position:relative;overflow:visible}.g5-bang .vach s{position:absolute;top:-3px;width:2px;height:9px;background:#b3281f;text-decoration:none}
@media(max-width:1100px){.g5-dai5{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:620px){.g5-dai5{grid-template-columns:repeat(2,minmax(0,1fr))}}
.g5-them{margin:12px 0 0;font:inherit;font-size:13px;font-weight:700;color:var(--g5-ns-b);background:#fff;border:1px solid var(--g5-ns-vien);border-radius:999px;padding:6px 14px;cursor:pointer}
.g5-nguon{background:#fff;border:1px solid var(--g5-line);border-radius:12px;padding:14px 18px}
.g5-nguon summary{cursor:pointer;font-size:13.5px;font-weight:600;color:var(--g5-dam)}
.g5-nguon ul{margin:10px 0 0;padding-left:18px;display:grid;gap:4px;font-size:12.5px;color:var(--g5-chu2)}
@media(max-width:1000px){.g5-dai{grid-template-columns:repeat(2,minmax(0,1fr))}.g5-hai{grid-template-columns:1fr}}
@media(max-width:620px){.g5-dai,.g5-luoi{grid-template-columns:1fr}.g5-v{flex-wrap:wrap}}
`}</style>
  </div>);
}
