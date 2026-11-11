"use client";
import { useEffect, useState } from "react";
import DinhKem from "@/components/DinhKem";
import { api } from "@/lib/api";
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
 *  · TỆP CHỨNG TỪ — chỉ mở được SAU KHI LƯU, vì kho hồ sơ gắn tệp theo mã phiếu mà mã chỉ có
 *    sau khi máy chủ sinh ra. Bước 2 nói trước điều đó thay vì vẽ một ô tải tệp rồi làm mất tệp.
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
  ma_khoan_goc: "", chung_tu: "", hen_bo_sung: "", ghi_chu_kiem_tra: "", ma_so_thue: "",
  so_tai_khoan: "", ngan_hang: "", ok: false, chuyen_ngoai: "",
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
  const [dang, setDang] = useState(false);
  const [daLuu, setDaLuu] = useState<{ ma_gd: string } | null>(null);   // ma_gd = mã đề nghị chi DC…
  const [choTrung, setChoTrung] = useState(false);
  const dat = (k: string, v: any) => setData({ ...d, [k]: v });

  // Ngân hàng không thuộc vai GĐ đội xe. Máy chủ từ chối vai ấy, nên màn hình cũng không hỏi —
  // hỏi một ô rồi bị từ chối lúc gửi là cách tệ nhất để nói một quy tắc.
  const hienNganHang = vai !== "gd_doi_xe";
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
        ma_khoan_goc: d.ma_khoan_goc === NGOAI ? "" : d.ma_khoan_goc.trim(), hen_bo_sung: canHoaDon ? "" : d.hen_bo_sung.trim(),
        ghi_chu_kiem_tra: [d.ma_khoan_goc === NGOAI && d.chuyen_ngoai.trim() ? `Chuyến ngoài VTOS (xe thuê ngoài): ${d.chuyen_ngoai.trim()}.` : "",
          d.ghi_chu_kiem_tra.trim()].filter(Boolean).join(" "), cho_phep_trung: choTrung,
      };
      if (hienNganHang) { json.so_tai_khoan = d.so_tai_khoan.trim(); json.ngan_hang = d.ngan_hang.trim(); }
      const r = await api<any>("/fleet/de-nghi-chi", { method: "POST", json });
      toast(r.message);
      setDaLuu({ ma_gd: r.code });
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
    <p className="muted">Phiếu đã lên <b>Chủ tịch duyệt</b>. Đính kèm chứng từ <b>ngay bây giờ</b> nếu đã có —
      Kế toán không chi khi phiếu chưa có chứng từ;
      chứng từ nằm cùng phiếu thì đến kỳ đối soát không phải đi tìm, và người kiểm tra nhìn thấy
      đúng thứ họ đang kiểm.</p>
    <DinhKem doiTuong="de_xuat_chi_xe" doiTuongId={daLuu.ma_gd}
      tieuDe={`Chứng từ của đề xuất chi ${daLuu.ma_gd}`}
      goi="Hoá đơn, báo giá, phiếu sửa chữa, ảnh hiện trạng. Chưa có thì để trống – ô «hẹn bổ sung» ở bước 2 đã ghi lại lời hứa còn nợ giấy." />
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
      <label style={{ display: "block", marginTop: 8 }}>Bên nhận / nhà cung cấp <span aria-hidden="true">*</span>
        <input value={d.nguoi_thu_huong} onChange={(e) => dat("nguoi_thu_huong", e.target.value)}
          placeholder="Tên đơn vị hoặc người nhận tiền" /></label>
      <label style={{ display: "block", marginTop: 8 }}>Mã số thuế bên nhận <span className="muted">(garage, cửa hàng — Kế toán cần trước khi chi; tài xế, tạm ứng thì để trống)</span>
        <input value={d.ma_so_thue} onChange={(e) => dat("ma_so_thue", e.target.value)} inputMode="numeric" /></label>
      {nhomKhongPhaiChiPhi && <p className="muted">Nhóm này được đánh dấu <b>không phải chi phí kỳ này</b> nên
        không cộng vào tổng chi phí đội xe — tiền dầu thật nằm ở phiếu chi phí của từng chuyến.</p>}
    </>}

    {buoc === 1 && <>
      <h3>Số tiền và hồ sơ kèm theo</h3>
      <div className="grid2">
        <label>Số tiền đề nghị (đ) <span aria-hidden="true">*</span>
          <input type="number" min={0} value={d.so_tien ?? ""} onChange={(e) => dat("so_tien", e.target.value)} /></label>
        <label>Ngày cần xử lý <span aria-hidden="true">*</span>
          <input type="date" value={d.ngay} onChange={(e) => dat("ngay", e.target.value)} /></label>
        <label>Căn cứ số tiền <span aria-hidden="true">*</span>
          <select value={d.can_cu_so_tien} onChange={(e) => dat("can_cu_so_tien", e.target.value)}>
            <option value="">— chọn căn cứ —</option>
            {CAN_CU.map((c) => <option key={c} value={c}>{c}</option>)}
          </select></label>
        <div>
          <label>Khoản gốc đã ghi nhận (nếu có)
            <input value={timKg} onChange={(e) => setTimKg(e.target.value)} disabled={d.pham_vi !== "xe" || !xeChon}
              placeholder="Tìm theo mã tour / mã phiếu chuyến…" aria-label="Tìm khoản gốc theo mã tour" /></label>
          <select value={d.ma_khoan_goc} onChange={(e) => dat("ma_khoan_goc", e.target.value)}
            disabled={d.pham_vi !== "xe" || !xeChon} aria-label="Khoản gốc" style={{ marginTop: 6 }}>
            <option value="">{d.pham_vi !== "xe" ? "— chi phí toàn đội: không gắn —" : !xeChon ? "— chọn xe trước —" : "— không gắn khoản gốc —"}</option>
            <option value={NGOAI}>Xe thuê ngoài — tự ghi mã tour</option>
            {(kg || []).map((k) => <option key={k.ma} value={k.ma} disabled={!!k.de_nghi_chi}>
              {`${k.loai} · ${k.ten} · ${k.so_tien != null ? tien(k.so_tien) : "chưa có số"}`}{k.de_nghi_chi ? ` — đã có ${k.de_nghi_chi}` : ""}
            </option>)}
            {kg && kg.length === 0 && timKg.trim() && <option value="" disabled>Không tìm thấy «{timKg.trim()}»</option>}
          </select>
          {d.ma_khoan_goc === NGOAI && <input style={{ marginTop: 6 }} value={d.chuyen_ngoai}
            onChange={(e) => dat("chuyen_ngoai", e.target.value)} placeholder="Mã tour xe thuê ngoài *" aria-label="Mã tour xe thuê ngoài" />}
        </div>
        <label>Số hoá đơn {canHoaDon && <span aria-hidden="true">*</span>}
          <input value={d.chung_tu} onChange={(e) => dat("chung_tu", e.target.value)} placeholder="HĐ 0000xxxx" /></label>
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
          : d.ma_khoan_goc.trim() ? ((kg || []).find((k) => k.ma === d.ma_khoan_goc)?.ten || d.ma_khoan_goc) : ""} />
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
