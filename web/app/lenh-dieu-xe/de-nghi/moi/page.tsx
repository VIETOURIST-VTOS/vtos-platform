"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { docUrl, ghiUrl, baoDaDoi } from "@/components/ThanhViec";

/** ĐIỀU HÀNH ĐỀ NGHỊ XE — tách khỏi /lenh-dieu-xe ngày 17/10/2026 (khối 6 của màn cũ). TOÀN MÀN.
 *
 *  Điều hành gửi đề nghị, KHÔNG chọn xe: chọn xe là việc của Giám đốc đội xe, vì chỉ người có xe mới
 *  biết xe nào rảnh ngày ấy.
 *
 *  Khoảng ngày trước đây DÙNG CHUNG với ô «Tìm phương án» của mẫu lập lệnh. Tách màn thì khối này có
 *  ô ngày riêng — và hai ô ấy nằm trên đường dẫn (tu, den, tour), để tab mở ra từ thanh việc hay từ
 *  một đường dẫn gửi qua tin nhắn đều dựng lại đúng danh sách chuyến. */

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/lenh-dieu-xe">Lệnh điều xe</a> · Đề nghị xe mới</>;
const homNay = () => new Date().toISOString().slice(0, 10);
const sauBaMuoiNgay = () => new Date(Date.now() + 30 * 864e5).toISOString().slice(0, 10);

function DeNghiMoi() {
  const { toast } = useShell();
  const [tu, setTu] = useState(homNay());
  const [den, setDen] = useState(sauBaMuoiNgay());
  const [busy, setBusy] = useState(false);
  const [dnQ, setDnQ] = useState<any>(undefined);       // undefined: đang hỏi · null: không hỏi được
  const [tourDN, setTourDN] = useState<any[]>([]);       // chuyến ĐỀ NGHỊ ĐƯỢC (đã duyệt dự toán)
  const [dnTour, setDnTour] = useState("");
  const [dnKhach, setDnKhach] = useState(0);
  const [dnKm, setDnKm] = useState(0);
  const [dnSoXe, setDnSoXe] = useState(1);
  const [dnYeuCau, setDnYeuCau] = useState("");
  const [docXong, setDocXong] = useState(false);

  useEffect(() => {
    const q = docUrl();
    const a = q.get("tu"), b = q.get("den");
    if (a) setTu(a);
    if (b) setDen(b);
    setDnTour(q.get("tour") || "");
    setDocXong(true);
    api("/de-nghi-xe/meta").then(setDnQ).catch(() => setDnQ(null));
  }, []);
  useEffect(() => { if (docXong) ghiUrl({ tu, den, tour: dnTour }); }, [docXong, tu, den, dnTour]);

  // Danh sách cho mẫu đề nghị đi đường RIÊNG, vì nó phải lọc theo dự toán đã duyệt. Dùng lại danh
  // sách tour của mẫu lập lệnh thì mẫu bày ra chuyến chưa duyệt, người điều hành bấm gửi và nhận 422.
  const napTour = useCallback(async (a: string, b: string) => {
    try { setTourDN(await api(`/de-nghi-xe/tour-cho-de-nghi?tu=${a}&den=${b}`)); }
    catch { setTourDN([]); }
  }, []);
  useEffect(() => { if (tu && den && den >= tu) napTour(tu, den); }, [tu, den, napTour]);

  /** Điều hành gửi đề nghị. KHÔNG chọn xe ở đây – chọn xe là việc của Giám đốc đội xe. */
  const guiDeNghi = async () => {
    if (!dnTour) { toast("Chọn chuyến cần xe", true); return; }
    setBusy(true);
    try {
      const r = await api("/de-nghi-xe", { method: "POST", json: {
        tour_id: Number(dnTour), so_khach: dnKhach, km_du_kien: dnKm, so_xe_can: dnSoXe,
        yeu_cau: dnYeuCau.trim() } });
      toast(r?.message || "Đã gửi đề nghị");
      baoDaDoi("vừa có một đề nghị xe mới");
      setDnYeuCau(""); napTour(tu, den);
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  const thanh = <ThanhViec toanMan duong={DUONG} viec={[{ nhan: "‹ Lên một cấp", href: "/lenh-dieu-xe/de-nghi", len: true }]} />;
  if (dnQ === undefined) return <>{thanh}<p className="muted">Đang tải…</p></>;
  // Quyền do MÁY CHỦ trả lời (meta.toi_duoc_de_nghi), không gõ lại danh sách vai ở đây. Không được
  // phép thì nói ra, chứ không vẽ một mẫu mà bấm gửi mới biết là 403.
  if (!dnQ?.toi_duoc_de_nghi) return (<>{thanh}
    <div className="panel"><h1>Điều hành đề nghị xe</h1>
      <p className="muted"><Tag cls="warn">không có quyền</Tag> Vai của anh không gửi được đề nghị xe. Đề nghị xe là việc của Điều hành tour.</p></div>
  </>);

  return (<>
    {thanh}
    <h1>Điều hành đề nghị xe</h1>
    <div className="panel">
      <p className="muted">Chỉ chuyến <b>đã duyệt dự toán</b> mới hiện ở đây — chi phí xe nằm trong dự toán ấy, nên không cần thêm chữ ký nào nữa (Chủ tịch quyết 11/10/2026).</p>
      <div className="grid">
        <div><label>Chuyến đi từ ngày</label><input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></div>
        <div><label>đến ngày</label><input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></div>
      </div>
      <div className="grid">
        <div><label>Chuyến cần xe</label>
          <select value={dnTour} onChange={(e) => {
            setDnTour(e.target.value);
            const t = tourDN.find((x: any) => String(x.id) === e.target.value);
            if (t?.planned_pax) setDnKhach(t.planned_pax);   // số khách dự kiến của chuyến, sửa được
          }}>
            <option value="">– chọn chuyến –</option>
            {tourDN.map((t: any) => <option key={t.id} value={t.id}>
              {t.code} · {t.name} · {fmtD(t.start_date)}→{fmtD(t.end_date)}{t.planned_pax ? ` · ${t.planned_pax} khách` : ""}{t.da_co_de_nghi ? ` · đã có ${t.da_co_de_nghi} đề nghị` : ""}
            </option>)}
          </select></div>
        <div><label>Số khách</label><input type="number" value={dnKhach} onChange={(e) => setDnKhach(Number(e.target.value))} /></div>
        <div><label>Km dự kiến (gồm chạy rỗng)</label><input type="number" value={dnKm} onChange={(e) => setDnKm(Number(e.target.value))} /></div>
        <div><label>Số xe cần</label><input type="number" min={1} value={dnSoXe} onChange={(e) => setDnSoXe(Number(e.target.value))} /></div>
      </div>
      <div><label>Yêu cầu riêng (nếu có)</label><textarea rows={2} value={dnYeuCau} onChange={(e) => setDnYeuCau(e.target.value)}
        placeholder="Ví dụ: khách yêu cầu xe đời 2022 trở lên; cần xe có khoang hành lý rộng" /></div>
      <p className="muted">Đề nghị <b>không chọn xe</b>: chọn xe là việc của Giám đốc đội xe, vì chỉ người có xe mới biết xe nào rảnh ngày ấy.</p>
      {!tourDN.length && <p className="muted"><Tag cls="warn">chưa có chuyến</Tag> Không có chuyến nào đã duyệt dự toán trong khoảng ngày này. Đổi khoảng ngày, hoặc chờ dự toán được duyệt.</p>}
      <button className="act teal" disabled={busy || !dnTour || dnKhach <= 0} onClick={guiDeNghi}>
        {busy ? "Đang gửi…" : "Gửi đề nghị xe"}</button>
      {dnTour && dnKhach <= 0 && <p className="muted">Phải ghi số khách — bộ gợi ý điều xe lọc theo số ghế, thiếu số khách thì nó đề xuất một chiếc 29 chỗ cho đoàn 40 người.</p>}
    </div>
  </>);
}

export default function Page() { return <Shell><DeNghiMoi /></Shell>; }
