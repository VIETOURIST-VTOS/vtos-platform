"use client";
import { useEffect, useState } from "react";
import DinhKem from "@/components/DinhKem";
import { api, getToken } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { Cap, ConThieu, KhoiXem, OXacNhan, ThanhBuoc, TuyenDuyet, tien, useNhap } from "./BonBuoc";

/** KS-64 · CỬA 1 — LẬP ĐỀ XUẤT CHI, bốn bước theo bản v3.3.
 *
 *  Đội xe v3.3 · Chủ tịch chốt 10/11/2026: phiếu gửi đi là một ĐỀ NGHỊ CHI 05-TT loại `chi_doi_xe`
 *  (`POST /fleet/de-nghi-chi`). Tuyến: GĐ đội xe gửi → Chủ tịch duyệt → Kế toán kiểm chứng từ và chi.
 *  Không còn ghi vào sổ đối soát nguồn ngoài; cửa ấy giữ cho bản trích Vietrip.
 *
 *  Bốn bước đặt đúng theo demo: Nội dung cần chi · Số tiền và hồ sơ · Đối chiếu trước khi gửi ·
 *  Luồng xử lý. Chia bước KHÔNG phải để màn hình đẹp hơn: nó để người lập đọc lại toàn bộ phiếu
 *  ở bước 3 trước khi phiếu thành một con số trong sổ.
 *
 *  BA CHỖ MÀN HÌNH NÀY CỐ Ý KHÔNG LÀM, và nói ra:
 *
 *  · SỐ TÀI KHOẢN VÀ NGÂN HÀNG — không hiện với vai `gd_doi_xe` (v3.3 §2, §7). Máy chủ cũng
 *    từ chối, không chỉ ẩn ô: ẩn nút là lời đề nghị, không phải hàng rào.
 *  · TỆP CHỨNG TỪ — VH-29 (đợt 2): CHỌN tệp ngay ở bước 2; tệp được tải lên kho «de_xuat_chi_xe» ngay sau
 *    khi máy chủ sinh mã phiếu, trong cùng một lần bấm «Gửi». Người ký thấy giấy từ lúc phiếu tới tay.
 *  · TUYẾN DUYỆT — chỉ xem: tuyến là của đề nghị chi 05-TT, máy chủ xếp, màn này không chọn người.
 */

const TEN_BUOC = ["Nội dung cần chi", "Số tiền và hồ sơ", "Đối chiếu trước khi gửi", "Luồng xử lý đề nghị"];

const LOAI: [string, string][] = [["thanh_toan", "Thanh toán"], ["tam_ung", "Tạm ứng"], ["hoan_ung", "Hoàn ứng / hoàn chi"]];

/** Bảy nhóm khoản — GIỮ NGUYÊN văn bản của bản một trang. Máy chủ nhận nhóm dưới dạng CHỮ và
 *  cờ "không phải chi phí" suy ra từ tiền tố "Nạp quỹ" / "Điều chuyển"; đổi câu chữ ở đây là
 *  lặng lẽ làm hai khoản ấy quay lại cộng vào chi phí đội xe. */
const NHOM = ["Chi phí riêng của xe", "Chi phí chung phân bổ", "Sửa chữa – bảo dưỡng",
  "Tài xế (công tác phí, lương)", "Quyết toán chủ xe / đối tác",
  "Nạp quỹ / tạm ứng (không phải chi phí)", "Điều chuyển tiền nội bộ (không phải chi phí)"];

const CAN_CU = ["Đã gồm thuế / phí theo chứng từ", "Không phát sinh thuế / phí",
  "Tạm tính · chờ kế toán kiểm tra"];

// Chủ tịch chốt 10/11/2026: «GĐ đội xe đề xuất lên thẳng Chủ tịch duyệt, sau đó Kế toán chi».
const TUYEN: [string, string][] = [
  ["Giám đốc đội xe", "Lập và gửi"],
  ["Chủ tịch", "Duyệt — mọi mức tiền"],
  ["Kế toán", "Kiểm chứng từ, bên nhận theo danh mục, rồi chi và gắn UNC"],
];

const rong = () => ({
  pham_vi: "xe", bien_so: "", loai: "thanh_toan", nhom: "", noi_dung: "", nguoi_thu_huong: "",
  so_tien: "" as any, ngay: new Date().toISOString().slice(0, 10), can_cu_so_tien: "",
  ma_khoan_goc: "", ma_khoan_goc_ds: [] as string[], chung_tu: "", hen_bo_sung: "", ghi_chu_kiem_tra: "", ma_so_thue: "",
  so_tai_khoan: "", ngan_hang: "", ok: false, chuyen_ngoai: "", ben_nhan_ma: "",
});
/** Giá trị đặc biệt của ô khoản gốc: chuyến KHÔNG có trên VTOS (xe thuê ngoài…) — GĐ đội xe tự ghi mã tour. */
const NGOAI = "__ngoai";

export default function BonBuocDeXuatChi({ xe, vai, nguongChungTu, toast, onXong, onDong }: {
  xe: any[]; vai: string; nguongChungTu?: number | null;
  toast: (s: string, loi?: boolean) => void; onXong: () => void; onDong: () => void;
}) {
  const { data: d, setData, xoaNhap } = useNhap("vtos.doixe.de-xuat-chi.nhap", rong);
  const [buoc, setBuoc] = useState(0);
  // Chống ghi chi phí hai lần (Chủ tịch duyệt 10/11/2026): khoản gốc CHỌN từ sổ của chính xe, không gõ tay.
  const xeChon = xe.find((v) => v.plate === d.bien_so);
  const [kg, setKg] = useState<any[] | null>(null);
  // VH-26 (Chủ tịch 12/11/2026): tour quá nhiều → ô TÌM theo mã tour / mã phiếu; máy chủ tìm trong cả sổ của xe.
  const [timKg, setTimKg] = useState("");
  useEffect(() => {
    if (d.pham_vi !== "xe" || !xeChon) { setKg(null); return; }
    const t = setTimeout(() => {
      api<any>(`/fleet/khoan-goc?xe_id=${xeChon.id}${timKg.trim() ? `&q=${encodeURIComponent(timKg.trim())}` : ""}`)
        .then((r) => setKg(r.rows || [])).catch(() => setKg([]));
    }, 300);
    return () => clearTimeout(t);
  }, [d.pham_vi, xeChon?.id, timKg]); // eslint-disable-line
  // VH-29 · đợt 2: bên nhận CHỌN từ danh mục (tài xế + nhà cung cấp); gõ tên ngoài danh mục vẫn được, máy
  // gắn cờ cho Kế toán. Tệp chứng từ chọn ngay lúc lập (không lưu trong nháp — tệp không cất được vào máy).
  const [dmBenNhan, setDmBenNhan] = useState<any[]>([]);
  useEffect(() => { api<any>("/fleet/ben-nhan-chon").then((r) => setDmBenNhan(r.rows || [])).catch(() => {}); }, []);
  const [tepChon, setTepChon] = useState<File[]>([]);
  const trongDanhMuc = dmBenNhan.find((b) => b.ten.trim().toLowerCase() === d.nguoi_thu_huong.trim().toLowerCase());
  const [dang, setDang] = useState(false);
  const [daLuu, setDaLuu] = useState<{ ma_gd: string; tep_loi?: string[] } | null>(null);   // ma_gd = mã DC…
  const [choTrung, setChoTrung] = useState(false);
  const dat = (k: string, v: any) => setData({ ...d, [k]: v });

  // Ngân hàng không thuộc vai GĐ đội xe. Máy chủ từ chối vai ấy, nên màn hình cũng không hỏi —
  // hỏi một ô rồi bị từ chối lúc gửi là cách tệ nhất để nói một quy tắc.
  const hienNganHang = vai !== "gd_doi_xe";
  // VH-29: tick NHIỀU khoản gốc → số tiền là TỔNG máy cộng (không gõ tay). Không tick khoản nào thì gõ tay.
  const dsKg: string[] = d.ma_khoan_goc === NGOAI ? [] : (d.ma_khoan_goc_ds || []);
  const kgChon = (kg || []).filter((k) => dsKg.includes(k.ma));
  const tongKg = kgChon.reduce((a, k) => a + (Number(k.so_tien) || 0), 0);
  const mayCong = dsKg.length > 0 && kgChon.length === dsKg.length && tongKg > 0;
  const tickKg = (ma: string) => {
    const moi = dsKg.includes(ma) ? dsKg.filter((m) => m !== ma) : [...dsKg, ma];
    const tong = (kg || []).filter((k) => moi.includes(k.ma)).reduce((a, k) => a + (Number(k.so_tien) || 0), 0);
    setData({ ...d, ma_khoan_goc: "", ma_khoan_goc_ds: moi, so_tien: moi.length && tong > 0 ? tong : d.so_tien });
  };
  const soTien = d.so_tien === "" || d.so_tien === null ? null : Number(d.so_tien);
  const nhomKhongPhaiChiPhi = d.nhom.startsWith("Nạp quỹ");
  // Điều chuyển nội bộ không phải một đề nghị chi (Chủ tịch 10/11/2026) — Kế toán lập bút toán điều chuyển.
  const nhomDieuChuyen = d.nhom.startsWith("Điều chuyển");
  // VH-26: số hoá đơn BẮT BUỘC; trừ tạm ứng / nạp quỹ — tiền chưa tiêu thì chưa có hoá đơn.
  const canHoaDon = d.loai !== "tam_ung" && !nhomKhongPhaiChiPhi;

  const thieu = (b: number): string[] => {
    const t: string[] = [];
    if (b >= 0) {
      if (d.pham_vi === "xe" && !d.bien_so) t.push("Chọn xe, hoặc đổi phạm vi sang «chi phí toàn đội».");
      if (!d.nhom) t.push("Chọn nhóm khoản chi – không phân loại lúc lập thì cuối tháng phải đọc lại từng phiếu để đoán.");
      if (nhomDieuChuyen) t.push("Điều chuyển tiền nội bộ không lập ở đây — báo Kế toán lập bút toán điều chuyển giữa VTD và Vietrip.");
      if (!d.noi_dung.trim()) t.push("Ghi nội dung và căn cứ đề nghị.");
      if (!d.nguoi_thu_huong.trim()) t.push("Ghi bên nhận / nhà cung cấp.");
    }
    if (b >= 1) {
      if (soTien === null || !(soTien > 0)) t.push("Nhập số tiền đề nghị lớn hơn 0.");
      if (!d.ngay) t.push("Chọn ngày cần xử lý.");
      if (!d.can_cu_so_tien) t.push("Chọn căn cứ số tiền – VTOS không tự cộng VAT, nên con số này phải nói rõ nó đã gồm gì.");
      if (canHoaDon && !d.chung_tu.trim()) t.push("Ghi số hoá đơn — bắt buộc (Chủ tịch 12/11/2026).");
      if (d.ma_khoan_goc === NGOAI && !d.chuyen_ngoai.trim()) t.push("Ghi mã tour / chuyến của xe thuê ngoài.");
      if (mayCong && soTien !== null && soTien > tongKg + 0.5)
        t.push(`Số tiền ${tien(soTien)} vượt tổng khoản gốc đã tick ${tien(tongKg)} — không chi vượt khoản gốc.`);
    }
    if (b >= 2 && !d.ok) t.push("Xác nhận đã đối chiếu số tiền, chứng từ và khoản chi gốc.");
    return t;
  };
  const thieuNay = thieu(buoc);

  const gui = async () => {
    setDang(true);
    try {
      const json: any = {
        ngay: d.ngay, so_tien: soTien, noi_dung: d.noi_dung.trim(),
        bien_so: d.pham_vi === "xe" ? d.bien_so : "",
        nhom: d.nhom, ma_so_thue: d.ma_so_thue.trim(),
        nguoi_thu_huong: d.nguoi_thu_huong.trim(), chung_tu: d.chung_tu.trim(),
        pham_vi: d.pham_vi, loai: d.loai, can_cu_so_tien: d.can_cu_so_tien,
        ma_khoan_goc: "", ma_khoan_goc_ds: dsKg, ben_nhan_ma: d.ben_nhan_ma || "", hen_bo_sung: canHoaDon ? "" : d.hen_bo_sung.trim(),
        ghi_chu_kiem_tra: [d.ma_khoan_goc === NGOAI && d.chuyen_ngoai.trim() ? `Chuyến ngoài VTOS (xe thuê ngoài): ${d.chuyen_ngoai.trim()}.` : "",
          d.ghi_chu_kiem_tra.trim()].filter(Boolean).join(" "), cho_phep_trung: choTrung,
      };
      if (hienNganHang) { json.so_tai_khoan = d.so_tai_khoan.trim(); json.ngan_hang = d.ngan_hang.trim(); }
      const r = await api<any>("/fleet/de-nghi-chi", { method: "POST", json });
      toast(r.message);
      // VH-29: phiếu đã có mã → tải ngay các tệp đã chọn ở bước 2 vào kho của phiếu.
      const tepLoi: string[] = [];
      for (const f of tepChon) {
        try {
          const fd = new FormData();
          fd.append("doi_tuong", "de_xuat_chi_xe"); fd.append("doi_tuong_id", r.code);
          fd.append("tep", f); fd.append("loai", "chung_tu");
          const t = await fetch("/api/v1/tep", { method: "POST", body: fd, headers: { Authorization: `Bearer ${getToken() || ""}` } });
          if (!t.ok) tepLoi.push(f.name);
        } catch { tepLoi.push(f.name); }
      }
      setTepChon([]);
      setDaLuu({ ma_gd: r.code, tep_loi: tepLoi });
      xoaNhap();            // đã vào sổ thì nháp không còn nghĩa gì, giữ lại chỉ gây lập hai lần
      onXong();
    } catch (e) {
      const m = errMsg(e);
      toast(m, true);
      // Máy chủ là nơi duy nhất biết ngưỡng chứng từ và biết phiếu nào trùng. Nó từ chối thì
      // đưa người dùng về đúng bước có ô phải sửa, đừng để họ đứng ở bước 4 đọc một câu lỗi
      // về một ô không nhìn thấy.
      if (m.includes("chứng từ") || m.includes("trùng") || m.includes("Đã có phiếu")) setBuoc(1);
      if (m.includes("ngân hàng") || m.includes("tài khoản")) setBuoc(1);
    } finally { setDang(false); }
  };

  /* ───────────── đã lưu: mở ô đính kèm, vì giờ mới có mã phiếu để gắn tệp ───────────── */
  if (daLuu) return <div className="panel">
    <h2>Đã lập đề xuất chi {daLuu.ma_gd}</h2>
    <p className="muted">Phiếu đã lên <b>Chủ tịch duyệt</b>.</p>
    {!!daLuu.tep_loi?.length && <p className="cb-do">Chưa tải được: {daLuu.tep_loi.join(", ")} — tải lại ở ô dưới.</p>}
    <DinhKem doiTuong="de_xuat_chi_xe" doiTuongId={daLuu.ma_gd}
      tieuDe={`Chứng từ của đề xuất chi ${daLuu.ma_gd}`}
      goi="Hoá đơn, báo giá, phiếu sửa chữa, ảnh hiện trạng." />
    <div className="bb-nut">
      <button className="act teal" onClick={() => { setDaLuu(null); setBuoc(0); setChoTrung(false); setData(rong()); }}>Lập phiếu tiếp</button>
      <button className="act grey" onClick={onDong}>Xong</button>
    </div>
  </div>;

  /* ───────────────────────────── bốn bước ───────────────────────────── */
  return <div className="panel">
    <h2>Lập đề xuất chi</h2>
    <ThanhBuoc ten={TEN_BUOC} buoc={buoc} veBuoc={setBuoc} />
    <ConThieu ds={thieuNay} />

    {buoc === 0 && <>
      <h3>Nội dung cần chi</h3>
      <div className="grid2">
        <label>Phạm vi khoản chi
          <select value={d.pham_vi} onChange={(e) => dat("pham_vi", e.target.value)}>
            <option value="xe">Chi phí một xe</option>
            <option value="doi">Chi phí toàn đội</option>
          </select></label>
        {d.pham_vi === "xe"
          ? <label>Xe <span aria-hidden="true">*</span>
              <select value={d.bien_so} onChange={(e) => dat("bien_so", e.target.value)}>
                <option value="">— chọn xe —</option>
                {xe.map((v: any) => <option key={v.id} value={v.plate}>{v.plate}{v.code ? ` · ${v.code}` : ""}</option>)}
              </select></label>
          : <div><label style={{ display: "block" }}>Đối tượng nhận chi phí</label>
              <p className="muted" style={{ margin: "4px 0 0" }}>Toàn đội — <b>không gán vào một xe</b>.
                Gắn vào một chiếc là làm chiếc đó gánh phần của cả đội.</p></div>}
        <label>Loại đề nghị
          <select value={d.loai} onChange={(e) => dat("loai", e.target.value)}>
            {LOAI.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
          </select></label>
        <label>Nhóm khoản <span aria-hidden="true">*</span>
          <select value={d.nhom} onChange={(e) => dat("nhom", e.target.value)}>
            <option value="">— chọn nhóm —</option>
            {NHOM.map((n) => <option key={n} value={n}>{n}</option>)}
          </select></label>
      </div>
      <label style={{ display: "block", marginTop: 8 }}>Nội dung và căn cứ đề nghị <span aria-hidden="true">*</span>
        <textarea rows={3} value={d.noi_dung} onChange={(e) => dat("noi_dung", e.target.value)}
          placeholder="Hạng mục, lý do, mã báo hỏng / bảo dưỡng hoặc chuyến liên quan" /></label>
      <label style={{ display: "block", marginTop: 8 }}>Bên nhận / nhà cung cấp — chọn từ danh mục <span aria-hidden="true">*</span>
        <input value={d.nguoi_thu_huong} list="dxc-ben-nhan" placeholder="Gõ vài chữ để chọn tài xế / nhà cung cấp"
          onChange={(e) => {
            const v = e.target.value, b = dmBenNhan.find((x) => x.ten === v);
            setData({ ...d, nguoi_thu_huong: v, ben_nhan_ma: b?.ma || "", ma_so_thue: b?.ma_so_thue ? b.ma_so_thue : d.ma_so_thue });
          }} /></label>
      <datalist id="dxc-ben-nhan">{dmBenNhan.map((b, i) => <option key={i} value={b.ten}>{b.loai}{b.ma ? ` · ${b.ma}` : ""}</option>)}</datalist>
      {d.nguoi_thu_huong.trim() && dmBenNhan.length > 0 && <p className="muted" style={{ margin: "4px 0 0" }}>
        {trongDanhMuc ? <span className="tag ok">{trongDanhMuc.loai} trong danh mục</span>
          : <span className="tag warn">Ngoài danh mục — vẫn gửi được, Kế toán sẽ đối chiếu</span>}</p>}
      <label style={{ display: "block", marginTop: 8 }}>Mã số thuế bên nhận <span className="muted">(garage, cửa hàng — Kế toán cần trước khi chi; tài xế, tạm ứng thì để trống)</span>
        <input value={d.ma_so_thue} onChange={(e) => dat("ma_so_thue", e.target.value)} inputMode="numeric" /></label>
      {nhomKhongPhaiChiPhi && <p className="muted">Nhóm này được đánh dấu <b>không phải chi phí kỳ này</b> nên
        không cộng vào tổng chi phí đội xe — tiền dầu thật nằm ở phiếu chi phí của từng chuyến.</p>}
    </>}

    {buoc === 1 && <>
      <h3>Số tiền và hồ sơ kèm theo</h3>
      <div className="grid2">
        <label>Số tiền đề nghị (đ) <span aria-hidden="true">*</span>
          <input type="number" min={0} value={d.so_tien ?? ""} onChange={(e) => dat("so_tien", e.target.value)} />
          {mayCong && <span className="muted">Máy cộng {kgChon.length} khoản gốc đã tick: <b>{tien(tongKg)}</b>
            {soTien !== tongKg && <> · <button type="button" className="dxc-them" onClick={() => dat("so_tien", tongKg)}>lấy đúng tổng</button></>}</span>}</label>
        <label>Ngày cần xử lý <span aria-hidden="true">*</span>
          <input type="date" value={d.ngay} onChange={(e) => dat("ngay", e.target.value)} /></label>
        <label>Căn cứ số tiền <span aria-hidden="true">*</span>
          <select value={d.can_cu_so_tien} onChange={(e) => dat("can_cu_so_tien", e.target.value)}>
            <option value="">— chọn căn cứ —</option>
            {CAN_CU.map((c) => <option key={c} value={c}>{c}</option>)}
          </select></label>
        <div style={{ gridColumn: "1 / -1" }}>
          <label>Khoản gốc đã ghi nhận — tick các khoản sẽ chi (nếu có)
            <input value={timKg} onChange={(e) => setTimKg(e.target.value)} disabled={d.pham_vi !== "xe" || !xeChon}
              placeholder="Tìm theo mã tour / mã phiếu chuyến…" aria-label="Tìm khoản gốc theo mã tour" /></label>
          {/* VH-29: TICK nhiều khoản gốc; khoản đã có đề xuất chi khác hoặc công ty đã trả thì khoá. */}
          {d.pham_vi !== "xe" ? <p className="muted" style={{ margin: "6px 0 0" }}>Chi phí toàn đội: không gắn khoản gốc.</p>
            : !xeChon ? <p className="muted" style={{ margin: "6px 0 0" }}>Chọn xe trước.</p>
            : <div className="dxc-kg" role="group" aria-label="Khoản gốc">
              <button type="button" className={"dxc-kg-dong" + (d.ma_khoan_goc === NGOAI ? " on" : "")} aria-pressed={d.ma_khoan_goc === NGOAI}
                onClick={() => setData({ ...d, ma_khoan_goc: d.ma_khoan_goc === NGOAI ? "" : NGOAI, ma_khoan_goc_ds: [] })}>
                <span className="o">{d.ma_khoan_goc === NGOAI ? "✓" : ""}</span><span>Xe thuê ngoài — tự ghi mã tour</span></button>
              {d.ma_khoan_goc !== NGOAI && (kg || []).map((k) => {
                const on = dsKg.includes(k.ma);
                return <button type="button" key={k.ma} className={"dxc-kg-dong" + (on ? " on" : "")} aria-pressed={on}
                  disabled={!!k.de_nghi_chi || !!k.cong_ty_da_tra} onClick={() => tickKg(k.ma)}
                  title={k.de_nghi_chi ? `Đã có ${k.de_nghi_chi}` : k.cong_ty_da_tra ? `Công ty đã trả: ${k.cong_ty_da_tra}` : undefined}>
                  <span className="o">{on ? "✓" : ""}</span>
                  <span>{k.ten}<small>{k.loai}{k.de_nghi_chi ? ` · đã có ${k.de_nghi_chi}` : ""}{k.cong_ty_da_tra ? ` · ${k.cong_ty_da_tra}` : ""}</small></span>
                  <b>{k.so_tien != null ? tien(k.so_tien) : "chưa có số"}</b></button>;
              })}
              {kg && kg.length === 0 && <p className="muted" style={{ margin: 4 }}>{timKg.trim() ? `Không tìm thấy «${timKg.trim()}»` : "Xe chưa có khoản nào."}</p>}
            </div>}
          {d.ma_khoan_goc === NGOAI && <input style={{ marginTop: 6 }} value={d.chuyen_ngoai}
            onChange={(e) => dat("chuyen_ngoai", e.target.value)} placeholder="Mã tour xe thuê ngoài *" aria-label="Mã tour xe thuê ngoài" />}
        </div>
        <label>Số hoá đơn {canHoaDon && <span aria-hidden="true">*</span>}
          <input value={d.chung_tu} onChange={(e) => dat("chung_tu", e.target.value)} placeholder="HĐ 0000xxxx" /></label>
        <label>Tệp chứng từ (ảnh hoá đơn, báo giá)
          <input type="file" multiple accept="image/*,application/pdf"
            onChange={(e) => setTepChon(Array.from(e.target.files || []))} />
          {tepChon.length > 0 && <span className="muted">{tepChon.length} tệp — tải lên ngay khi gửi phiếu</span>}</label>
        {hienNganHang && <label>Số tài khoản bên nhận
          <input value={d.so_tai_khoan} onChange={(e) => dat("so_tai_khoan", e.target.value)} /></label>}
        {hienNganHang && <label>Ngân hàng
          <input value={d.ngan_hang} onChange={(e) => dat("ngan_hang", e.target.value)} /></label>}
      </div>
      <p className="muted">VTOS <b>không tự cộng VAT</b>. Số tiền ghi đúng như chứng từ, và ô «căn cứ» ở trên
        là chỗ nói ra con số ấy đã gồm những gì.</p>
      {!hienNganHang && <p className="muted">Số tài khoản và ngân hàng của bên nhận <b>do Kế toán kiểm soát</b>,
        không nhập ở màn Giám đốc đội xe (v3.3 §2, §7). Ghi tên bên nhận ở bước 1 là đủ.</p>}
      {!canHoaDon && !d.chung_tu.trim() && <label style={{ display: "block", marginTop: 8 }}>Hẹn bổ sung hoá đơn
        <input value={d.hen_bo_sung} onChange={(e) => dat("hen_bo_sung", e.target.value)}
          placeholder="VD: hoá đơn nộp sau khi hoàn ứng" /></label>}
      <label style={{ display: "block", marginTop: 8 }}>Ghi chú cho người kiểm tra
        <textarea rows={2} value={d.ghi_chu_kiem_tra} onChange={(e) => dat("ghi_chu_kiem_tra", e.target.value)} /></label>
    </>}

    {(buoc === 2 || buoc === 3) && <>
      <h3>{buoc === 2 ? "Đối chiếu trước khi gửi" : "Luồng xử lý đề nghị"}</h3>
      <KhoiXem>
        <Cap nhan="Xe / phạm vi" value={d.pham_vi === "doi" ? "Toàn đội xe" : d.bien_so} />
        <Cap nhan="Loại đề nghị" value={LOAI.find(([v]) => v === d.loai)?.[1]} />
        <Cap nhan="Nhóm khoản" value={d.nhom} />
        <Cap nhan="Nội dung" value={d.noi_dung.trim()} />
        <Cap nhan="Bên nhận" value={d.nguoi_thu_huong.trim()} />
        <Cap nhan="Mã số thuế bên nhận" value={d.ma_so_thue.trim()} />
        <Cap nhan="Số tiền đề nghị" value={tien(d.so_tien)} />
        <Cap nhan="Căn cứ số tiền" value={d.can_cu_so_tien} />
        <Cap nhan="Ngày cần xử lý" value={d.ngay} />
        {hienNganHang && <Cap nhan="Tài khoản bên nhận" value={[d.so_tai_khoan.trim(), d.ngan_hang.trim()].filter(Boolean).join(" · ")} />}
        <Cap nhan="Số hoá đơn" value={d.chung_tu.trim()} />
        {!d.chung_tu.trim() && <Cap nhan="Hẹn bổ sung" value={d.hen_bo_sung.trim()} />}
        <Cap nhan="Liên kết khoản gốc" value={d.ma_khoan_goc === NGOAI ? `Xe thuê ngoài · ${d.chuyen_ngoai.trim()}`
          : kgChon.length ? kgChon.map((k) => `${k.ten} (${tien(k.so_tien)})`).join("; ") : ""} />
        <Cap nhan="Tệp chứng từ" value={tepChon.map((f) => f.name).join(", ")} />
      </KhoiXem>
      {buoc === 2 && <>
        <OXacNhan cho={d.ok} doi={(v) => dat("ok", v)}
          chu="Tôi đã kiểm tra số tiền, chứng từ và khoản chi gốc; đề nghị chuyển đúng người có quyền duyệt." />
      </>}
      {buoc === 3 && <>
        <TuyenDuyet tuyen={TUYEN} ghi="" />
        <button type="button" className={"act " + (choTrung ? "teal" : "grey")} aria-pressed={choTrung}
          onClick={() => setChoTrung(!choTrung)}>{choTrung ? "✓ Vẫn gửi dù trùng phiếu" : "Vẫn gửi dù trùng phiếu"}</button>
      </>}
    </>}

    <style>{KG_CSS}</style>
    <div className="bb-nut">
      {buoc > 0 && <button className="act grey" onClick={() => setBuoc(buoc - 1)}>← Quay lại</button>}
      {buoc < 3 && <button className="act teal" disabled={thieuNay.length > 0} onClick={() => setBuoc(buoc + 1)}>
        Tiếp: {TEN_BUOC[buoc + 1]}</button>}
      {buoc === 3 && <button className="act teal" disabled={dang || thieu(2).length > 0} onClick={gui}>
        {dang ? "Đang gửi…" : "Gửi đề nghị"}</button>}
      <button className="act grey" onClick={onDong}>Đóng</button>
    </div>
  </div>;
}

const KG_CSS = `
.dxc-kg{display:flex;flex-direction:column;gap:4px;margin-top:6px;max-height:260px;overflow:auto;border:1px solid var(--line);border-radius:8px;padding:4px;background:var(--panel)}
.dxc-kg-dong{display:flex;align-items:center;gap:8px;width:100%;text-align:left;font:inherit;font-size:calc(13/14*1rem);background:none;border:1px solid transparent;border-radius:6px;padding:6px 8px;cursor:pointer;color:var(--ink);margin:0}
.dxc-kg-dong:hover:not(:disabled){background:var(--panel2)}
.dxc-kg-dong.on{border-color:var(--teal);background:var(--okbg)}
.dxc-kg-dong:disabled{opacity:.55;cursor:not-allowed}
.dxc-kg-dong .o{flex:none;width:18px;height:18px;border:1.5px solid var(--line);border-radius:4px;display:grid;place-items:center;font-size:12px;font-weight:700;color:var(--teal)}
.dxc-kg-dong.on .o{border-color:var(--teal)}
.dxc-kg-dong>span:nth-child(2){flex:1;min-width:0}
.dxc-kg-dong small{display:block;color:var(--ink2);font-size:calc(12/14*1rem)}
.dxc-kg-dong b{flex:none;font-variant-numeric:tabular-nums}
.dxc-them{font:inherit;background:none;border:0;padding:0;margin:0;color:var(--navy);text-decoration:underline;cursor:pointer}
`;
