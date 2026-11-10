"use client";
import { useEffect, useState } from "react";
import DinhKem from "@/components/DinhKem";
import QuyetToanChuyen from "@/components/QuyetToanChuyen";
import { api, soTien } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { Cap, ConThieu, KhoiXem, OXacNhan, ThanhBuoc, TuyenDuyet, soDoc, tien, useNhap } from "./BonBuoc";

/** KS-64 · CỬA 2 — NHẬP BÁO CÁO TỪNG XE, bốn bước theo bản v3.3.
 *
 *  Cùng bộ trường và cùng cửa máy chủ với biểu mẫu một trang trước đây: `POST /fleet/chuyen`
 *  rồi bốn dòng `POST /fleet/chuyen/{id}/chi-phi`. KHÔNG đổi sổ, KHÔNG thêm cột.
 *
 *  Bốn bước: Gắn đúng xe và chuyến · Hành trình và nguồn số km · Doanh thu và chi phí chuyến ·
 *  Kiểm tra trước khi gửi.
 *
 *  BỐN LUẬT SỐ LIỆU màn này thi hành, và cả bốn đều đã có máu trong hồ sơ KS:
 *
 *  1 · Ô TRỐNG LÀ CHƯA CÓ SỐ, không phải 0. Màn đối chiếu in "Chưa nhập" bằng chữ xám. Để
 *      trống một khoản thì KHÔNG ghi dòng chi phí ấy — chứ không ghi một dòng 0 đ, vì một dòng
 *      0 đ đọc y như "đã xác nhận không phát sinh".
 *
 *  2 · KHÔNG LẤY SỐ KM ÂM. Km cuối nhỏ hơn km đầu là người gõ nhầm hoặc đồng hồ đã thay; cả
 *      hai đều phải người xem, không phải một phép trừ âm chạy tiếp vào báo cáo.
 *
 *  3 · LỆCH GPS LÀ VIỆC CẦN ĐỐI CHIẾU, không phải chỗ để tự ghi đè. Màn hình nêu ra con số
 *      lệch; nguồn km dùng cho báo cáo thì người nhập chọn và chịu trách nhiệm.
 *
 *  4 · GIÁ DẦU VÀ TIÊU HAO NGOÀI KHOẢNG THÌ NÓI RA NGAY Ở BƯỚC 3, lúc còn sửa được — chứ
 *      không chờ tới lúc một kỳ đã chốt rồi mới phát hiện ra giá dầu 23.173 đ/lít.
 */

const TEN_BUOC = ["Gắn đúng xe và chuyến", "Hành trình và nguồn số km", "Doanh thu và chi phí chuyến", "Kiểm tra trước khi gửi"];

// Chủ tịch chốt 10/11/2026: GĐ đội xe gửi → Chủ tịch duyệt (chuyến vào lợi nhuận) → Kế toán chi.
const TUYEN: [string, string][] = [
  ["Giám đốc đội xe", "Nhập báo cáo, chứng từ và gửi tờ quyết toán"],
  ["Chủ tịch", "Duyệt — từ lúc này chuyến mới vào lợi nhuận"],
  ["Kế toán", "Chi phần tạm ứng / hoàn trả / chi thêm"],
];

/** Ngưỡng cảnh báo — CÙNG BỘ SỐ với bộ nạp tự động mỗi tối (khuôn «Nạp xe Vietrip lên VTOS»).
 *  Hai nơi phải nói một điều về cùng một chuyến: nếu bộ nạp đêm gắn cờ mà màn nhập tay im
 *  lặng thì cùng một con số lại đúng hay sai tuỳ nó vào hệ bằng đường nào. */
const GIA_DAU_MIN = 25_000, GIA_DAU_MAX = 35_000;
const TIEU_HAO_MIN = 20, TIEU_HAO_MAX = 40;

const KHOAN: [string, string][] = [["dau", "Tiền dầu"], ["cau_duong", "Phí cầu đường"],
  ["cong_tac_phi", "Công tác phí tài xế"], ["giu_xe", "Phí gửi xe"]];

const rong = () => ({
  vehicle_id: "" as any, ten_tour: "", ngay_di: "", ngay_ve: "",
  km_dau: "" as any, km_cuoi: "" as any, km_gps: "" as any, km_nguon: "",
  doanh_thu: "" as any, dau: "" as any, lit: "" as any, cau_duong: "" as any,
  cong_tac_phi: "" as any, giu_xe: "" as any, chung_tu: "", note: "", hen_bo_sung: "", ok: false,
  // Vào vận hành (Chủ tịch duyệt 10/11/2026): phiếu gắn lệnh điều xe — tour, tài xế, ngày theo lệnh.
  dispatch_id: "" as any, driver_id: "" as any, tour_id: "" as any, phieu: null as any,
});

const n = (v: any): number | null => (v === "" || v === null || v === undefined ? null : Number(v));

export default function BonBuocBaoCaoXe({ xe, kmNguon, toast, onXong, onDong }: {
  xe: any[]; kmNguon: Record<string, string>;
  toast: (s: string, loi?: boolean) => void; onXong: () => void; onDong: () => void;
}) {
  const { data: d, setData, xoaNhap, coNhapCu } = useNhap("vtos.doixe.bao-cao-xe.nhap", rong);
  const [buoc, setBuoc] = useState(0);
  const [dang, setDang] = useState(false);
  const [daLuu, setDaLuu] = useState<{ id: number; ma_phieu?: string } | null>(null);
  const dat = (k: string, v: any) => setData({ ...d, [k]: v });
  /** Lệnh điều xe của xe đang chọn, kèm phiếu chuyến đã có (phiếu tài xế ghi trên điện thoại). */
  const [lenhDs, setLenhDs] = useState<any[] | null>(null);
  useEffect(() => {
    if (!d.vehicle_id) { setLenhDs(null); return; }
    api<any>(`/fleet/lenh-cho-bao-cao?xe_id=${d.vehicle_id}`).then((r) => setLenhDs(r.rows || [])).catch(() => setLenhDs([]));
  }, [d.vehicle_id]);
  /** Khoản tài xế đã ghi (theo loại): không nhập lại, không ghi dòng thứ hai. */
  const daTX: Record<string, { tien: number; lit: number }> = {};
  for (const k of (d.phieu?.tai_xe_da_gui ? d.phieu.khoan : []) || [])
    daTX[k.kind] = { tien: (daTX[k.kind]?.tien || 0) + (k.so_tien || 0), lit: (daTX[k.kind]?.lit || 0) + (k.lit || 0) };
  const chonLenh = (id: string) => {
    const l = (lenhDs || []).find((x) => String(x.id) === id);
    if (!l) { setData({ ...d, dispatch_id: "", driver_id: "", tour_id: "", phieu: null }); return; }
    const p = l.phieu;
    const tx: any = {};
    if (p?.tai_xe_da_gui) {
      for (const k of p.khoan) tx[k.kind] = (tx[k.kind] || 0) + (k.so_tien || 0);
      tx.lit = p.khoan.filter((k: any) => k.kind === "dau").reduce((a: number, k: any) => a + (k.lit || 0), 0) || "";
    }
    setData({ ...d, dispatch_id: l.id, driver_id: l.driver_id || "", tour_id: l.tour_id || "", phieu: p,
      ten_tour: l.tour || d.ten_tour, ngay_di: String(l.date_from).slice(0, 10), ngay_ve: String(l.date_to).slice(0, 10),
      ...(p?.tai_xe_da_gui ? { km_dau: p.km_dau ?? "", km_cuoi: p.km_cuoi ?? "", km_nguon: d.km_nguon || "anh_dong_ho",
        dau: tx.dau ?? d.dau, lit: tx.lit || d.lit, cau_duong: tx.cau_duong ?? d.cau_duong, giu_xe: tx.giu_xe ?? d.giu_xe } : {}) });
  };

  const kd = n(d.km_dau), kc = n(d.km_cuoi), gps = n(d.km_gps);
  const kmDongHo = kd !== null && kc !== null ? kc - kd : null;
  const kmDung = d.km_nguon === "gps" ? gps : kmDongHo;
  const lechGps = kmDongHo !== null && gps !== null ? gps - kmDongHo : null;

  const dauTien = n(d.dau), lit = n(d.lit);
  const giaDau = dauTien !== null && lit !== null && lit > 0 ? dauTien / lit : null;
  const tieuHao = lit !== null && kmDung !== null && kmDung > 0 ? (lit / kmDung) * 100 : null;
  const tongChi = KHOAN.reduce((a, [k]) => a + (n((d as any)[k]) ?? 0), 0);
  const thieuKhoan = KHOAN.filter(([k]) => n((d as any)[k]) === null).length;
  const dt = n(d.doanh_thu);

  /** Cảnh báo — KHÔNG chặn gửi. Số nghi sai vẫn nạp nguyên trạng và gắn cờ; sửa hộ người nhập
   *  là cách chắc chắn để một con số sai trở thành một con số sai mà không ai biết. */
  const canh = (): string[] => {
    const c: string[] = [];
    if (kmDongHo !== null && kmDongHo < 0) c.push(`Km cuối nhỏ hơn km đầu (${kmDongHo.toLocaleString("vi-VN")} km) – kiểm lại số đọc, hoặc xe đã thay đồng hồ.`);
    if (lechGps !== null && Math.abs(lechGps) > 0.5) c.push(`GPS lệch ${lechGps > 0 ? "+" : ""}${lechGps.toLocaleString("vi-VN")} km so với đồng hồ – cần đối chiếu, VTOS không tự ghi đè bên nào.`);
    if (giaDau !== null && (giaDau < GIA_DAU_MIN || giaDau > GIA_DAU_MAX)) c.push(`Giá dầu ${giaDau.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} đ/lít nằm ngoài khoảng ${GIA_DAU_MIN.toLocaleString("vi-VN")}–${GIA_DAU_MAX.toLocaleString("vi-VN")} – kiểm lại tiền dầu hoặc số lít.`);
    if (tieuHao !== null && (tieuHao < TIEU_HAO_MIN || tieuHao > TIEU_HAO_MAX)) c.push(`Tiêu hao ${tieuHao.toFixed(1)} lít/100km nằm ngoài khoảng ${TIEU_HAO_MIN}–${TIEU_HAO_MAX} – kiểm lại số lít hoặc km.`);
    if (dt !== null && dt > 0 && tongChi === 0) c.push("Có doanh thu mà chưa nhập một khoản chi phí nào – chuyến sẽ đọc ra lãi bằng toàn bộ doanh thu.");
    return c;
  };
  const canhNay = canh();

  const thieu = (b: number): string[] => {
    const t: string[] = [];
    if (b >= 0) {
      if (!d.vehicle_id) t.push("Chọn xe.");
      if (!d.ten_tour.trim()) t.push("Ghi tour / khách hàng.");
      if (!d.ngay_di) t.push("Chọn ngày đi.");
      if (!d.ngay_ve) t.push("Chọn ngày về.");
      if (d.ngay_di && d.ngay_ve && d.ngay_ve < d.ngay_di) t.push("Ngày về trước ngày đi – kiểm lại.");
      if (d.phieu && !d.phieu.tai_xe_da_gui) t.push(d.phieu.tu_tai_xe
        ? `Tài xế đang ghi phiếu #${d.phieu.id} trên điện thoại, chưa gửi – chờ tài xế bấm «Kết thúc chuyến».`
        : `Lệnh này đã có báo cáo xe #${d.phieu.id} – mở phiếu ấy ở «Báo cáo từng xe», không lập phiếu thứ hai.`);
    }
    if (b >= 1) {
      if (!d.km_nguon) t.push("Chọn nguồn số km dùng cho báo cáo.");
      if (d.km_nguon === "gps" && gps === null) t.push("Đã chọn nguồn GPS nhưng chưa nhập km GPS.");
      if (d.km_nguon !== "gps" && d.km_nguon !== "" && kmDongHo === null) t.push("Chưa đủ km đầu và km cuối để ra quãng đường.");
    }
    if (b >= 2) {
      if (dt === null || !(dt > 0)) t.push("Nhập doanh thu chuyến.");
      if (dauTien !== null && dauTien > 0 && (lit === null || !(lit > 0))) t.push("Có tiền dầu thì phải có số lít – thiếu lít thì không tính được giá dầu và tiêu hao.");
    }
    if (b >= 3 && !d.ok) t.push("Xác nhận đã đối chiếu xe, kỳ, nguồn km và chứng từ.");
    return t;
  };
  const thieuNay = thieu(buoc);

  const gui = async () => {
    setDang(true);
    try {
      const ghiChu = [d.note.trim(), d.hen_bo_sung.trim() ? `Hẹn bổ sung chứng từ: ${d.hen_bo_sung.trim()}` : ""]
        .filter(Boolean).join(" | ");
      // Phiếu tài xế đã gửi: SỬA đúng phiếu ấy (thêm doanh thu, kiểm km) — không lập phiếu thứ hai.
      const r = d.phieu?.tai_xe_da_gui
        ? { ...(await api<any>(`/fleet/chuyen/${d.phieu.id}`, { method: "PUT", json: {
            phien_ban: d.phieu.phien_ban, ten_tour: d.ten_tour.trim(), ngay_di: d.ngay_di, ngay_ve: d.ngay_ve,
            km_dau: kd, km_cuoi: kc, km_gps: gps, km_nguon: d.km_nguon || "anh_dong_ho", doanh_thu: dt,
            ...(ghiChu ? { note: ghiChu } : {}) } })), id: d.phieu.id }
        : await api<any>("/fleet/chuyen", { method: "POST", json: {
        vehicle_id: Number(d.vehicle_id), ten_tour: d.ten_tour.trim(),
        ngay_di: d.ngay_di, ngay_ve: d.ngay_ve,
        km_dau: kd, km_cuoi: kc, km_gps: gps, km_nguon: d.km_nguon || "nhap_tay",
        doanh_thu: dt, quyet_toan: false,   // v3.3: vào lợi nhuận khi Chủ tịch duyệt tờ
        ...(d.dispatch_id ? { dispatch_id: Number(d.dispatch_id) } : {}),
        ...(d.driver_id ? { driver_id: Number(d.driver_id) } : {}),
        ...(d.tour_id ? { tour_id: Number(d.tour_id) } : {}),
        note: ghiChu } });
      // Bốn khoản ghi thành bốn dòng riêng — mỗi dòng phải trả lời được loại gì, ai chịu, chứng
      // từ đâu. Khoản để TRỐNG thì không ghi dòng nào: xem luật 1 ở đầu tệp.
      const loi: string[] = [];
      for (const [k] of KHOAN) {
        const v = soTien((d as any)[k]);
        if (!v || v <= 0) continue;
        if (daTX[k]) continue;            // tài xế đã ghi khoản này kèm ảnh hoá đơn — không ghi lần hai
        try {
          await api(`/fleet/chuyen/${r.id}/chi-phi`, { method: "POST", json: {
            kind: k, amount: v, lit: k === "dau" ? (soTien(d.lit) || 0) : 0, chung_tu: d.chung_tu.trim() } });
        } catch (e) { loi.push(`${k}: ${errMsg(e)}`); }
      }
      // Phiếu đã vào sổ mà một dòng chi phí bị từ chối thì PHẢI NÓI RA, không được báo "đã lưu"
      // trơn: người nhập sẽ tưởng đủ bốn khoản và không ai quay lại bù.
      if (loi.length) toast(`Đã lưu phiếu #${r.id} nhưng ${loi.length} khoản chi phí KHÔNG ghi được: ${loi.join(" · ")}`, true);
      else toast(`Đã ghi báo cáo xe #${r.id}`);
      setDaLuu({ id: r.id, ma_phieu: r.ma_phieu });
      xoaNhap();
      onXong();
    } catch (e) {
      const m = errMsg(e);
      toast(m, true);
      if (m.includes("chứng từ")) setBuoc(2);
    } finally { setDang(false); }
  };

  /* ───────────── đã lưu: giờ mới có số phiếu để gắn tệp và khai quyết toán ───────────── */
  if (daLuu) return <div className="panel">
    <h2>Đã ghi báo cáo xe {daLuu.ma_phieu || `#${daLuu.id}`}</h2>
    <p className="muted">Phiếu đã vào nhật trình chuyến. Hai việc còn lại làm được <b>ngay tại đây</b>:
      đính chứng từ, và khai tờ quyết toán Mẫu 2 nếu tài xế đã ký giấy.</p>
    <DinhKem doiTuong="chuyen_xe" doiTuongId={daLuu.id}
      tieuDe={`Chứng từ của phiếu chuyến #${daLuu.id}`}
      goi="Ảnh hoá đơn dầu, vé cầu đường, phiếu gửi xe, ảnh đồng hồ km." />
    <QuyetToanChuyen tripId={daLuu.id} toast={toast} />
    <div className="bb-nut">
      <button className="act teal" onClick={() => { setDaLuu(null); setBuoc(0); setData(rong()); }}>Nhập phiếu tiếp</button>
      <button className="act grey" onClick={onDong}>Xong</button>
    </div>
  </div>;

  /* ───────────────────────────── bốn bước ───────────────────────────── */
  return <div className="panel">
    <h2>Nhập báo cáo từng xe</h2>
    <ThanhBuoc ten={TEN_BUOC} buoc={buoc} veBuoc={setBuoc} />
    {coNhapCu && buoc === 0 && <p className="muted">Đang mở lại <b>nháp lưu trong máy này</b> từ lần gõ trước.
      Nháp không nằm trên máy chủ: đổi máy hoặc xoá dữ liệu trình duyệt là mất.
      {" "}<button className="act grey" style={{ margin: 0 }} onClick={() => { xoaNhap(); setBuoc(0); }}>Bỏ nháp, gõ lại từ đầu</button></p>}
    <ConThieu ds={thieuNay} />

    {buoc === 0 && <>
      <h3>Gắn đúng xe và chuyến</h3>
      <div className="grid2">
        <label>Xe <span aria-hidden="true">*</span>
          <select value={d.vehicle_id} onChange={(e) => dat("vehicle_id", e.target.value)}>
            <option value="">— chọn xe —</option>
            {xe.map((v: any) => <option key={v.id} value={v.id}>{v.plate}{v.code ? ` · ${v.code}` : ""}</option>)}
          </select></label>
        <label>Lệnh điều xe
          <select value={d.dispatch_id} disabled={!d.vehicle_id} onChange={(e) => chonLenh(e.target.value)}>
            <option value="">{!d.vehicle_id ? "— chọn xe trước —" : lenhDs?.length ? "— không qua lệnh (chuyến ngoài, thuê lẻ) —" : "— xe này chưa có lệnh gần đây —"}</option>
            {(lenhDs || []).map((l) => <option key={l.id} value={l.id}>
              {`#${l.id} · ${l.tour || "?"} · ${String(l.date_from).slice(5, 10)}→${String(l.date_to).slice(5, 10)} · ${l.tai_xe || "chưa có tài xế"}`}
              {l.phieu ? (l.phieu.tai_xe_da_gui ? " · tài xế đã gửi số" : l.phieu.tu_tai_xe ? " · tài xế đang ghi" : ` · đã có báo cáo #${l.phieu.id}`) : ""}
            </option>)}
          </select></label>
        <label>Tour / khách hàng <span aria-hidden="true">*</span>
          <input value={d.ten_tour} onChange={(e) => dat("ten_tour", e.target.value)} placeholder="Đà Lạt (lẻ)" /></label>
        <label>Ngày đi <span aria-hidden="true">*</span>
          <input type="date" value={d.ngay_di} onChange={(e) => dat("ngay_di", e.target.value)} /></label>
        <label>Ngày về <span aria-hidden="true">*</span>
          <input type="date" value={d.ngay_ve} onChange={(e) => dat("ngay_ve", e.target.value)} /></label>
      </div>
      {d.phieu?.tai_xe_da_gui && <p className="muted">Tài xế đã gửi phiếu #{d.phieu.id}: km {d.phieu.km_dau ?? "?"} → {d.phieu.km_cuoi ?? "?"},
        {" "}{d.phieu.khoan.length} khoản kèm ảnh hoá đơn. Anh kiểm số và thêm doanh thu — không nhập lại các khoản tài xế đã ghi.</p>}
      {!d.dispatch_id && d.vehicle_id && <p className="muted">Không chọn lệnh thì phiếu ghi là <b>không qua lệnh</b>: không đối chiếu được với lệnh, tài xế và tour.</p>}
      <label style={{ display: "block", marginTop: 8 }}>Ghi chú chuyến
        <input value={d.note} onChange={(e) => dat("note", e.target.value)} /></label>
      <p className="muted">Biển số đối chiếu theo <b>ngày chuyến</b>: mã xe theo chiếc xe suốt vòng đời, đổi biển
        hay chuyển sở hữu đều giữ nguyên lịch sử của chính chiếc đó.</p>
    </>}

    {buoc === 1 && <>
      <h3>Hành trình và nguồn số km</h3>
      <div className="grid2">
        <label>Km đầu<input type="number" value={d.km_dau ?? ""} onChange={(e) => dat("km_dau", e.target.value)}
          placeholder="đọc trên đồng hồ đầu chuyến" /></label>
        <label>Km cuối<input type="number" value={d.km_cuoi ?? ""} onChange={(e) => dat("km_cuoi", e.target.value)}
          placeholder="đọc trên đồng hồ cuối chuyến" /></label>
        <label>Km theo GPS<input type="number" value={d.km_gps ?? ""} onChange={(e) => dat("km_gps", e.target.value)}
          placeholder="để trống nếu kỳ này chưa lấy số GPS" /></label>
        <label>Nguồn số km dùng cho báo cáo <span aria-hidden="true">*</span>
          {/* Dựng từ danh mục máy chủ, KHÔNG gõ lại danh sách ở đây. */}
          <select value={d.km_nguon} onChange={(e) => dat("km_nguon", e.target.value)}>
            <option value="">— chọn nguồn —</option>
            {Object.entries(kmNguon || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
      </div>
      <KhoiXem>
        <Cap nhan="Quãng đường theo đồng hồ" value={kmDongHo === null ? undefined : kmDongHo < 0 ? "Cần sửa – đang âm" : `${kmDongHo.toLocaleString("vi-VN")} km`} />
        <Cap nhan="Quãng đường theo nguồn đã chọn" value={kmDung === null ? undefined : `${kmDung.toLocaleString("vi-VN")} km`} />
        <Cap nhan="Lệch GPS so với đồng hồ" value={lechGps === null ? undefined : `${lechGps > 0 ? "+" : ""}${lechGps.toLocaleString("vi-VN")} km`} />
      </KhoiXem>
      <p className="muted">Ô để trống nghĩa là <b>chưa đo</b>, không phải bằng 0 — hệ thống không tự điền 0 và không
        tính ra quãng đường âm. Lệch GPS là việc cần đối chiếu, không phải chỗ để ghi đè đồng hồ.</p>
    </>}

    {buoc === 2 && <>
      <h3>Doanh thu và chi phí chuyến</h3>
      <label style={{ display: "block" }}>Doanh thu (đ) <span aria-hidden="true">*</span>
        <input type="number" value={d.doanh_thu ?? ""} onChange={(e) => dat("doanh_thu", e.target.value)}
          placeholder="theo chứng từ / căn cứ chuyến" /></label>
      <h4 style={{ margin: "12px 0 4px" }}>Vietourist tạm ứng · bốn khoản chi phí chuyến</h4>
      <p className="muted">Quy tắc chốt 07/9/2026. Để trống khoản nào thì <b>không ghi dòng đó</b> — khác với ghi 0 đ,
        vì 0 đ đọc ra là «đã xác nhận không phát sinh».</p>
      <div className="grid2">
        <label>Tiền dầu (đ){daTX.dau ? " · tài xế đã ghi" : ""}<input type="number" disabled={!!daTX.dau} value={d.dau ?? ""} onChange={(e) => dat("dau", e.target.value)} /></label>
        <label>Số lít{daTX.dau ? " · tài xế đã ghi" : ""}<input type="number" step="0.001" disabled={!!daTX.dau} value={d.lit ?? ""} onChange={(e) => dat("lit", e.target.value)} /></label>
        <label>Phí cầu đường (đ){daTX.cau_duong ? " · tài xế đã ghi" : ""}<input type="number" disabled={!!daTX.cau_duong} value={d.cau_duong ?? ""} onChange={(e) => dat("cau_duong", e.target.value)} /></label>
        <label>Công tác phí tài xế (đ)<input type="number" value={d.cong_tac_phi ?? ""} onChange={(e) => dat("cong_tac_phi", e.target.value)} /></label>
        <label>Phí gửi xe (đ){daTX.giu_xe ? " · tài xế đã ghi" : ""}<input type="number" disabled={!!daTX.giu_xe} value={d.giu_xe ?? ""} onChange={(e) => dat("giu_xe", e.target.value)} /></label>
        <label>Số chứng từ<input value={d.chung_tu} onChange={(e) => dat("chung_tu", e.target.value)} /></label>
      </div>
      <KhoiXem>
        <Cap nhan="Vietourist tạm ứng" value={`${tongChi.toLocaleString("vi-VN")} đ${thieuKhoan ? ` · còn ${thieuKhoan} khoản chưa nhập` : ""}`} />
        <Cap nhan="Giá dầu" value={giaDau === null ? undefined : `${giaDau.toLocaleString("vi-VN", { maximumFractionDigits: 0 })} đ/lít`} />
        <Cap nhan="Tiêu hao" value={tieuHao === null ? undefined : `${tieuHao.toFixed(1)} lít/100km`} />
        <Cap nhan="Lợi nhuận chuyến (tạm tính)" value={dt === null ? undefined : `${(dt - tongChi).toLocaleString("vi-VN")} đ`} />
      </KhoiXem>
      {!d.chung_tu.trim() && <label style={{ display: "block", marginTop: 8 }}>Hẹn bổ sung chứng từ
        <input value={d.hen_bo_sung} onChange={(e) => dat("hen_bo_sung", e.target.value)}
          placeholder="VD: tài xế gửi vé cầu đường ngày 12/11" /></label>}
      <p className="muted">Khoản <b>chủ xe chịu</b> khai ở tờ quyết toán Mẫu 2, mở ngay sau khi lưu phiếu — nó
        không cộng vào bốn khoản Vietourist tạm ứng ở trên.</p>
    </>}

    {buoc === 3 && <>
      <h3>Kiểm tra báo cáo trước khi gửi</h3>
      <KhoiXem>
        <Cap nhan="Xe" value={xe.find((v: any) => String(v.id) === String(d.vehicle_id))?.plate} />
        <Cap nhan="Tour / khách hàng" value={d.ten_tour.trim()} />
        <Cap nhan="Thời gian" value={d.ngay_di && d.ngay_ve ? `${d.ngay_di} → ${d.ngay_ve}` : undefined} />
        <Cap nhan="Km sử dụng" value={kmDung === null ? undefined : `${kmDung.toLocaleString("vi-VN")} km · ${kmNguon?.[d.km_nguon] || d.km_nguon}`} />
        <Cap nhan="Doanh thu" value={tien(d.doanh_thu)} />
        {KHOAN.map(([k, ten]) => <Cap key={k} nhan={ten} value={tien((d as any)[k])} />)}
        <Cap nhan="Số lít dầu" value={soDoc(d.lit) ? `${soDoc(d.lit)} lít` : undefined} />
        <Cap nhan="Vietourist tạm ứng" value={`${tongChi.toLocaleString("vi-VN")} đ${thieuKhoan ? ` · còn ${thieuKhoan} khoản chưa nhập` : ""}`} />
        <Cap nhan="Chứng từ" value={d.chung_tu.trim()} />
        {!d.chung_tu.trim() && <Cap nhan="Hẹn bổ sung" value={d.hen_bo_sung.trim()} />}
      </KhoiXem>
      {canhNay.length > 0 && <div className="bb-thieu"><b>{canhNay.length} chỗ nghi sai – vẫn gửi được, nhưng xem lại trước đã:</b>
        <ul>{canhNay.map((c) => <li key={c}>{c}</li>)}</ul></div>}
      <TuyenDuyet tuyen={TUYEN} ghi={"Lưu ở đây là ghi phiếu vào nhật trình — CHƯA vào lợi nhuận. Khai tờ quyết toán " +
        "ngay sau khi lưu rồi bấm gửi: tờ lên thẳng Chủ tịch duyệt, Chủ tịch duyệt xong chuyến mới tính vào lợi nhuận, " +
        "sau đó Kế toán chi."} />
      <OXacNhan cho={d.ok} doi={(v) => dat("ok", v)}
        chu="Tôi đã đối chiếu xe, kỳ, nguồn km và chứng từ; các khoản ghi 0 là đã xác nhận không phát sinh, các khoản để trống là chưa có số." />
    </>}

    <div className="bb-nut">
      {buoc > 0 && <button className="act grey" onClick={() => setBuoc(buoc - 1)}>← Quay lại</button>}
      {buoc < 3 && <button className="act teal" disabled={thieuNay.length > 0} onClick={() => setBuoc(buoc + 1)}>
        Tiếp: {TEN_BUOC[buoc + 1]}</button>}
      {buoc === 3 && <button className="act teal" disabled={dang || thieuNay.length > 0} onClick={gui}>
        {dang ? "Đang lưu…" : "Gửi báo cáo"}</button>}
      <button className="act grey" onClick={onDong}>Đóng</button>
      <span className="bb-nhap">Nháp tự lưu trong máy này</span>
    </div>
  </div>;
}
