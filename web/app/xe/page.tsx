"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import { KhoiHieuQuaXe } from "@/components/KhoiV14";
import ChiPhiKyPanel from "@/components/doixe/ChiPhiKyPanel";
import DeXuatChiTaiCho from "@/components/doixe/DeXuatChiTaiCho";
import * as G from "@/components/doixe/TrangGon";
import SanSangVanHanh from "@/components/doixe/SanSangVanHanh";

/** Bàn làm việc Giám đốc đội xe — màn `/xe`. Bố cục v3.3, bản vẽ anh Tuấn gửi 09/11/2026.
 *
 *  Màn RIÊNG của đội xe, không cột dọc bên trái, không phân hệ phòng khác (anh Tuấn 08/11/2026).
 *  Shell vẫn bọc — canh đăng nhập, mật khẩu tạm, toast — nhưng ẩn thanh dọc (`khongThanhBen`).
 *
 *  ═══ BỐN ĐIỀU CỦA BẢN VẼ v3.3 ═══════════════════════════════════════════════════════════════
 *   1. NĂM MỤC NGHIỆP VỤ trên một hàng, KHÔNG có mục "Bàn làm việc". Lối về tổng quan là CHỮ VTOS
 *      ở đầu trang (00-Doc-truoc.txt, điểm 4) — nên ở đây không có nút «Tổng quan» thứ sáu.
 *   2. Nhóm nào có nhiều trang thì hiện THANH CON ngay dưới, và vùng nội dung đổi TẠI CHỖ.
 *   3. HAI CỬA NHẬP chỉ xuất hiện MỘT lần, trên tổng quan, kèm chuỗi bước của chính nó.
 *   4. Biểu đồ chiếm toàn chiều ngang; hàng đợi việc đặt DƯỚI biểu đồ.
 *
 *  ═══ RÁP KHỐI CỦA MÀN CHỦ TỊCH, KHÔNG DỰNG BỘ SỐ THỨ HAI ════════════════════════════════════
 *  Anh Tuấn 09/11: "lấy màn hình xe bên chủ tịch để ráp qua cho nhanh". Đúng — và nó còn quan
 *  trọng hơn chuyện nhanh: `KhoiHieuQuaXe` đọc `hieu_qua_xe.chi_so`, mà hàm ấy lấy số từ
 *  `fleet_lai_lo.bao_cao` — CÙNG một phép tính với màn Lãi lỗ đội xe, đã trừ chi phí kỳ của xe
 *  và của đội, đã loại lãi vay khỏi giá vốn.
 *
 *  Bản trước của màn này tự vẽ một bảng doanh thu/lợi nhuận riêng đọc `fleet_ai.hieu_qua_ky`.
 *  Hai bộ số trên hai màn là hai chỗ để lệch nhau; nên bảng ấy GỠ, và màn này đọc đúng khối mà
 *  Chủ tịch đang đọc. Cái KHÔNG gỡ là câu cảnh báo «chưa nhập»: nó không phải một con số cạnh
 *  tranh, nó là lời nói ra rằng con số bên trên còn thiếu nhóm nào.
 *
 *  Khối ấy mang sẵn những thứ bản vẽ đòi mà màn này chưa có: biên lợi nhuận, ngày xe hoạt động,
 *  tiêu hao L/100km, km chạy rỗng, công suất khai thác (kèm ngày cắt mẫu số), xe đang đi hôm nay,
 *  ô chọn kỳ Tháng/Quý/Năm, và hình diễn biến 12 kỳ. Không viết lại một dòng nào.
 *
 *  ═══ HAI LUẬT CŨ VẪN NGUYÊN ═════════════════════════════════════════════════════════════════
 *  Ô KỲ CHỈ CÓ HAI MŨI TÊN, KHÔNG CÓ CHỖ GÕ. Lỗi thật trên màn Lãi lỗ: gõ «102026» thì ô hiện
 *  October 2026 nhưng thân trang vẽ kỳ 2026-01. Ở đây kỳ là một giá trị YYYY-MM đổi bằng số
 *  tháng, không bao giờ đi qua trạng thái gõ dở.
 *
 *  CHƯA NHẬP ≠ BẰNG 0 — khoản thiếu đeo nhãn vàng, không bao giờ hiện 0. Luật này đã cứu tháng 10
 *  khỏi đọc sai 84,5 tr (KS-36) và 77 tr lương (KS-41). */

const MAU: Record<string, { cham: string; chu: string }> = {
  do:    { cham: "#be2f2f", chu: "#be2f2f" },
  cam:   { cham: "#a66a00", chu: "#a66a00" },
  vang:  { cham: "#c9a227", chu: "#6b5415" },
  trang: { cham: "#fff",    chu: "#5b6b82" },
};

/** Đổi kỳ bằng SỐ THÁNG — không đi qua chuỗi gõ dở. */
function doiKy(ky: string, buoc: number) {
  let [n, t] = ky.split("-").map(Number);
  t += buoc;
  while (t > 12) { t -= 12; n += 1; }
  while (t < 1) { t += 12; n -= 1; }
  return `${String(n).padStart(4, "0")}-${String(t).padStart(2, "0")}`;
}
const kyDoc = (ky: string) => ky.split("-").reverse().join(" / ");

/** Nhãn dùng chung cho mọi chỗ có thể thiếu số. */
const ChuaNhap = () => (
  <span className="tag" style={{ background: "#fdf6e7", color: "#a66a00", fontWeight: 700 }}>
    CHƯA NHẬP
  </span>
);

/** NĂM NHÓM NGHIỆP VỤ và TRANG CON của chúng — tên lấy đúng bản vẽ v3.3.
 *
 *  Mọi đường dẫn ở đây là MÀN HÌNH CÓ THẬT đang chạy; v3.3 §11 gọi đợt này là "nối giao diện với
 *  chức năng hiện có", nên không dựng màn mới nào. Trang con nào là một TAB của /doi-xe thì trỏ
 *  thẳng vào tab ấy. */
type Trang = { ma: string; ten: string; toi: string; ghi?: string };
const NHOM: { ma: string; ten: string; tom: string; trang: Trang[] }[] = [
  { ma: "dispatch", ten: "Điều xe", tom: "Đề nghị xe · lịch và lệnh · tài xế nhận lệnh", trang: [
    { ma: "lich", ten: "Lịch & lệnh điều xe", toi: "/lenh-dieu-xe" },
    { ma: "de-nghi", ten: "Đề nghị xe", toi: "/lenh-dieu-xe/de-nghi",
      ghi: "Điều hành tour gửi sang sau khi dự toán được duyệt" },
    { ma: "lap-lenh", ten: "Lập lệnh điều xe", toi: "/lenh-dieu-xe/lap-lenh" },
    { ma: "chua-nhan", ten: "Tài xế chưa nhận lệnh", toi: "/lenh-dieu-xe/chua-nhan",
      ghi: "Hạn nhận: trước giờ khởi hành 24 giờ" },
    { ma: "xe-hom-nay", ten: "Xe hôm nay", toi: "/doi-xe/xe-hom-nay" },
  ] },
  { ma: "fleet", ten: "Xe & tài xế", tom: "Hồ sơ xe · tài xế · chủ xe và hợp đồng", trang: [
    { ma: "ho-so-xe", ten: "Hồ sơ xe", toi: "/doi-xe" },
    { ma: "tai-xe", ten: "Tài xế", toi: "/tai-xe" },
    { ma: "chu-xe", ten: "Chủ xe & hợp đồng", toi: "/doi-xe?tab=quyettoan" },
    { ma: "phat", ten: "Phạt tài xế", toi: "/doi-xe/phat-tai-xe" },
  ] },
  { ma: "finance", ten: "Báo cáo & chi phí", tom: "Báo cáo từng xe · đề xuất chi · quyết toán · công nợ", trang: [
    { ma: "bao-cao-xe", ten: "Báo cáo từng xe", toi: "/doi-xe?tab=chuyen", ghi: "Nhật trình chuyến" },
    { ma: "de-xuat-chi", ten: "Đề xuất chi", toi: "/doi-xe?tab=giaodich", ghi: "Tab Đối soát nguồn ngoài" },
    { ma: "quyet-toan", ten: "Quyết toán", toi: "/doi-xe?tab=quyettoan" },
    { ma: "cong-no", ten: "Công nợ", toi: "/doi-xe?tab=congno" },
    { ma: "lai-lo", ten: "Lãi lỗ đội xe", toi: "/lai-lo-doi-xe", ghi: "Ba tầng chi phí và chi phí kỳ" },
  ] },
  { ma: "technical", ten: "Bảo dưỡng & sự cố", tom: "Bảo dưỡng · báo hỏng · dầu và định mức", trang: [
    { ma: "bao-duong", ten: "Bảo dưỡng", toi: "/doi-xe?tab=bao-duong" },
    { ma: "bao-hong", ten: "Báo hỏng", toi: "/doi-xe?tab=bao-hong" },
    { ma: "dau", ten: "Dầu & định mức", toi: "/doi-xe/gia-dau" },
    { ma: "su-co", ten: "Sự cố tour", toi: "/su-co-tour" },
  ] },
  { ma: "performance", ten: "Hiệu quả", tom: "Công suất · tiêu hao · kết quả từng xe", trang: [
    { ma: "hieu-qua", ten: "Hiệu quả khai thác", toi: "/hieu-qua-doi-xe" },
    { ma: "nhin-lai", ten: "Nhìn lại — thuê xe ngoài khi xe nhà đậu", toi: "/doi-xe?tab=nhin-lai" },
  ] },
];

/** MÀN GỌN theo mã trang con — trang nào không có ở đây thì vẫn mở màn đang chạy. */
type GonProps = { mo: (toi: string) => void; ky: string; onNhap: () => void };
const MAN_GON: Record<string, (p: GonProps) => React.ReactNode> = {
  "lich": (p) => <G.LichLenhGon mo={p.mo} />,
  "ho-so-xe": (p) => <G.HoSoXeGon mo={p.mo} />,
  "bao-cao-xe": (p) => <G.BaoCaoXeGon mo={p.mo} onNhap={p.onNhap} />,
  "quyet-toan": (p) => <G.QuyetToanGon mo={p.mo} ky={p.ky} />,
  "cong-no": (p) => <G.CongNoGon mo={p.mo} />,
  "bao-duong": (p) => <G.BaoDuongGon mo={p.mo} />,
  "bao-hong": (p) => <G.BaoHongGon mo={p.mo} />,
  "dau": (p) => <G.DauGon mo={p.mo} />,
  // VH-3 (Chủ tịch duyệt 10/11/2026): năm trang điều xe còn mở màn cũ toàn trang.
  "de-nghi": (p) => <G.DeNghiXeGon mo={p.mo} />,
  "lap-lenh": (p) => <G.LapLenhGon mo={p.mo} />,
  "xe-hom-nay": (p) => <G.XeHomNayGon mo={p.mo} />,
  "tai-xe": (p) => <G.TaiXeGon mo={p.mo} />,
  "chu-xe": (p) => <G.ChuXeGon mo={p.mo} />,
};

/** HAI CỬA NHẬP CHÍNH — Chủ tịch duyệt 10/11/2026: mở TẠI CHỖ, đúng trang con của nó, không rời /xe.
 *  `trang` là mã trang con trong nhóm «Báo cáo & chi phí»; `mo` bảo trang ấy bật sẵn biểu mẫu. */
const CUA_NHAP: { nhan: string; ten: string; buoc: string; trang: string; mo: string }[] = [
  { nhan: "ĐỀ NGHỊ THANH TOÁN / TẠM ỨNG", ten: "Lập đề xuất chi",
    buoc: "Nội dung → chứng từ → kiểm tra → gửi xử lý", trang: "de-xuat-chi", mo: "de-xuat-chi" },
  { nhan: "NHẬT TRÌNH & CHI PHÍ CHUYẾN", ten: "Nhập báo cáo từng xe",
    buoc: "Xe & chuyến → km → thu chi → gửi kiểm tra", trang: "bao-cao-xe", mo: "phieu-chi-phi" },
];

/** Trang con mở TẠI CHỖ (bản vẽ v3.3 điểm 2): nhúng CHÍNH màn đang chạy. Không chép lại một màn nào: mọi
 *  luật, mọi cửa nhập vẫn là của màn gốc. Cùng tên miền nên khung đọc được trang con: giấu thanh ngang và
 *  thanh dọc của nó (đã có ở /xe) và tự co chiều cao theo nội dung.
 *
 *  Vì sao không sửa Shell để có chế độ nhúng: Shell đang được làn R2 giữ chỗ (MKT-1, MKT-2, PH-1). Giấu bằng
 *  một thẻ style chèn vào khung thì không đụng tệp của làn khác. */
function KhungNhung({ toi, ten, mo }: { toi: string; ten: string; mo?: string }) {
  const [cao, setCao] = useState(640);
  const src = toi + (mo ? (toi.includes("?") ? "&" : "?") + `mo=${mo}` : "");
  const doCao = (f: HTMLIFrameElement) => {
    try {
      const doc = f.contentDocument;
      const b = doc?.body;
      if (!doc || !b) return;
      if (!doc.getElementById("vtos-nhung")) {
        const st = doc.createElement("style");
        st.id = "vtos-nhung";
        st.textContent = ".top,aside.side{display:none!important}main{max-width:none!important;padding:0!important;margin:0!important}body{background:transparent!important}";
        doc.head.appendChild(st);
      }
      const dat = () => setCao(Math.max(400, b.scrollHeight + 24));
      dat();
      const ro = new ResizeObserver(dat);
      ro.observe(b);
    } catch { /* khác nguồn thì giữ chiều cao mặc định */ }
  };
  return <>
    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
      <Link href={toi} className="muted">Mở toàn trang ↗</Link></div>
    <iframe key={src} src={src} title={ten} onLoad={(e) => doCao(e.currentTarget)}
      style={{ width: "100%", height: cao, border: 0, display: "block" }} />
  </>;
}

/** Ô «Quyền của tôi» — ma trận quyền GĐ đội xe của tài liệu v3.3 mục 7. Chỉ để đọc; quyền thật do máy
 *  chủ kiểm ở từng cửa. */
const QUYEN_GD: [string, string][] = [
  ["Xem xe và chỉ số đội", "Trong phạm vi được giao"],
  ["Lập đề xuất chi", "Tạo, sửa nháp, gửi — Kế toán kiểm, TGĐ / Chủ tịch ký"],
  ["Duyệt đề xuất tự lập", "Không"],
  ["Thực hiện thanh toán", "Không — Kế toán"],
  ["Nhập báo cáo xe", "Tạo, sửa nháp, gửi kiểm tra"],
  ["Lập và chốt lệnh xe", "Theo người được cấu hình"],
  ["Bảng giá vận tải", "Chưa có quyền"],
  ["Đổi thông tin ngân hàng", "Không — Kế toán"],
];

/** Ngăn kéo: xử lý tại chỗ, đóng lại là bàn tự đọc lại số. */
const NGAN_KEO: Record<string, { ten: string; toi: string; nhan: string }> = {
  "quyet-toan": { ten: "Quyết toán chuyến", toi: "/doi-xe", nhan: "Mở bảng quyết toán" },
  "chi-phi-ky": { ten: "Nhập chi phí kỳ", toi: "/lai-lo-doi-xe", nhan: "Mở sổ chi phí kỳ" },
  "ho-so-xe":   { ten: "Hồ sơ xe", toi: "/doi-xe", nhan: "Mở hồ sơ xe" },
  "bao-duong":  { ten: "Bảo dưỡng", toi: "/doi-xe", nhan: "Mở tab bảo dưỡng" },
  "de-xuat":    { ten: "Đề xuất chờ duyệt", toi: "/requests", nhan: "Mở màn đề xuất" },
};

function BanLamViecXe() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(() => new Date().toISOString().slice(0, 7));
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);
  const [keo, setKeo] = useState<string | null>(null);
  /** `null` = đang ở TỔNG QUAN. Khác null = mã nhóm nghiệp vụ đang mở. */
  const [nhom, setNhom] = useState<string | null>(null);
  /** Bộ ba kỳ Tháng/Quý/Năm cho khối hiệu quả — CHÍNH cửa mà màn Chủ tịch đọc. */
  const [boKy, setBoKy] = useState<any>(null);

  /** Vai này có được vào màn /xe không — hỏi `hidden_menus` của phiên, tức lời của chính
   *  ma trận quyền ở access.py. Không dựng danh sách vai thứ hai ở web, và không thêm một
   *  cửa hỏi quyền nữa: câu trả lời đã nằm sẵn trong trình duyệt từ lúc đăng nhập. */
  const khongCoQuyen = (user?.hidden_menus || []).includes("/xe");

  const doc = useCallback(async (k: string) => {
    setDang(true);
    try { setD(await api(`/fleet/ban-lam-viec?ky=${k}`)); }
    catch (e) { toast(errMsg(e), true); }
    finally { setDang(false); }
  }, [toast]);

  useEffect(() => { if (!khongCoQuyen) doc(ky); }, [ky, doc, khongCoQuyen]);
  /* Cửa này nặng — HQ-6 đo 10–30 giây vì nó tính lại ba kỳ, kỳ liền trước để so, và 12 cột của
     hình. Nên gọi RIÊNG một lần, không gộp vào cửa bàn làm việc: gộp thì cả màn phải chờ nó. */
  useEffect(() => {
    if (khongCoQuyen) return;
    api("/fleet/hieu-qua-doi-xe").then(setBoKy).catch(() => setBoKy(null));
  }, [khongCoQuyen]);
  useEffect(() => {
    if (!keo) return;
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setKeo(null); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [keo]);

  const hd = d?.hang_doi, sk = d?.so_ky, xe = d?.xe_hom_nay;
  const k = keo ? NGAN_KEO[keo] : null;
  const nhomMo = nhom ? NHOM.find((n) => n.ma === nhom) : null;
  const [trang, setTrang] = useState<string | null>(null);
  /** Cửa nhập vừa bấm — trang con mở sẵn biểu mẫu. */
  const [moSan, setMoSan] = useState<string>("");
  /** Màn chi tiết đang mở từ một màn gọn (nút «Mở…»). */
  const [chiTiet, setChiTiet] = useState<string | null>(null);
  const [quyen, setQuyen] = useState(false);
  /** «Số tiền theo»: mặc định chuyến đã quyết toán (KS-65); chọn «tất cả» thì nói thêm phần đang treo. */
  const [theoTien, setTheoTien] = useState<"qt" | "tat_ca">("qt");
  const trangMo = nhomMo ? (nhomMo.trang.find((t) => t.ma === trang) || nhomMo.trang[0]) : null;

  // THIẾU QUYỀN: nói rõ, và dừng ở đây. Không vẽ thanh nghiệp vụ, không vẽ hai nút nhập —
  // một cái khung đầy đủ mà rỗng ruột đọc ra như phần mềm hỏng.
  if (khongCoQuyen) return (
    <div className="panel">
      <h1 style={{ marginTop: 0 }}>Bàn làm việc Giám đốc đội xe</h1>
      <p><b>Màn hình này của Công ty TNHH Vận tải Vietrip.</b> Vai trò của bạn chưa được mở
        quyền vào đây, nên VTOS không tải số liệu đội xe.</p>
      <p className="muted">Nếu bạn cần xem, xin quyền ở <b>Quản trị hệ thống → Tài khoản &amp;
        phân quyền</b>. Đây không phải lỗi hệ thống, và cũng không phải màn hình chưa dựng.</p>
      <p><Link href="/">← Về trang tổng CRM</Link></p>
    </div>
  );

  return (<>
    {/* ① NĂM MỤC NGHIỆP VỤ — một hàng ngang, KHÔNG có mục "Bàn làm việc" (v3.3).
        Lối về tổng quan là chữ VTOS ở đầu trang; lối ra khỏi đội xe nằm cuối hàng, vì màn
        này ẩn thanh dọc nên nếu đây không có thì người dùng chỉ còn nút Back. */}
    <nav aria-label="Nghiệp vụ đội xe"
         style={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(max-content, 1fr)) auto", overflowX: "auto",
                  gap: 4, marginBottom: 4, borderBottom: "1px solid #dce3ec" }}>
      {NHOM.map((n) => (
        <button key={n.ma} type="button" title={n.tom}
          onClick={() => { setNhom(nhom === n.ma ? null : n.ma); setTrang(null); setMoSan(""); setChiTiet(null); }}
          aria-pressed={nhom === n.ma}
          style={{ padding: "8px 12px", border: 0, background: "none", cursor: "pointer",
                   fontWeight: nhom === n.ma ? 700 : 400,
                   borderBottom: nhom === n.ma ? "3px solid #1d5bbf" : "3px solid transparent" }}>
          {n.ten}
        </button>))}
      <Link href="/" style={{ padding: "8px 12px", marginLeft: "auto" }}>Trang tổng CRM →</Link>
    </nav>

    {/* ② THANH CON — chỉ hiện khi nhóm có nhiều hơn một trang (v3.3). */}
    {nhomMo && nhomMo.trang.length > 1 && <nav aria-label={`Trang của ${nhomMo.ten}`}
      style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 14, paddingTop: 8 }}>
      {nhomMo.trang.map((t) => (
        <button key={t.ma} type="button" onClick={() => { setTrang(t.ma); setMoSan(""); setChiTiet(null); }}
          aria-pressed={trangMo?.ma === t.ma}
          style={{ padding: "6px 10px", borderRadius: 6, cursor: "pointer",
                   border: "1px solid " + (trangMo?.ma === t.ma ? "#1d5bbf" : "#dce3ec"),
                   background: trangMo?.ma === t.ma ? "#eef3fb" : "#fff",
                   fontWeight: trangMo?.ma === t.ma ? 700 : 400 }}>
          {t.ten}
        </button>))}
    </nav>}

    <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-end",
                  justifyContent: "space-between", margin: "14px 0 18px" }}>
      <div>
        <h1 style={{ margin: "0 0 4px" }}>Bàn làm việc Giám đốc đội xe</h1>
        <p className="muted" style={{ margin: 0 }}>
          Công ty TNHH Vận tải Vietrip · chỉ dữ liệu đội xe
        </p>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <button type="button" onClick={() => setQuyen(!quyen)} aria-expanded={quyen}>Quyền của tôi</button>
        <span className="muted">Kỳ</span>
        <button type="button" aria-label="Kỳ trước" onClick={() => setKy(doiKy(ky, -1))}>‹</button>
        <strong style={{ minWidth: 92, textAlign: "center" }}>{kyDoc(ky)}</strong>
        <button type="button" aria-label="Kỳ sau" onClick={() => setKy(doiKy(ky, 1))}>›</button>
      </div>
    </div>

    {quyen && <section className="panel" aria-label="Quyền của tôi">
      <h2 style={{ marginTop: 0 }}>Quyền của Giám đốc đội xe</h2>
      <div style={{ overflowX: "auto" }}><table><tbody>{QUYEN_GD.map(([a, b]) =>
        <tr key={a}><td>{a}</td><td>{b}</td></tr>)}</tbody></table></div>
      <p className="muted" style={{ marginBottom: 0 }}>Theo ma trận quyền của bản v3.3. Nút ẩn chỉ là cách trình bày — máy chủ kiểm quyền ở từng cửa.</p>
    </section>}

    {/* ③ MỘT NGHIỆP VỤ ĐANG MỞ — vùng nội dung đổi TẠI CHỖ (v3.3 điểm 2, Chủ tịch duyệt 10/11/2026). */}
    {nhomMo && trangMo && <section className="panel">
      {trangMo.ma === "de-xuat-chi"
        ? <DeXuatChiTaiCho vai={user?.role || ""} toast={toast} moSan={moSan === "de-xuat-chi"} />
        : (() => {
          // v3.3 màn gọn (Chủ tịch duyệt bản xem trước 10/11/2026): trang có màn gọn thì hiện màn gọn;
          // «Mở…» hoặc cửa nhập mới mở màn chi tiết đang chạy, ngay tại đây.
          const Gon: ((p: GonProps) => React.ReactNode) | undefined = MAN_GON[trangMo.ma];
          const moCT = (toi: string) => setChiTiet(toi);
          if (Gon && !chiTiet && !moSan) return Gon({ mo: moCT, ky, onNhap: () => setMoSan("phieu-chi-phi") });
          const toi = chiTiet || trangMo.toi;
          const coGon = trangMo.ma in MAN_GON;
          return <>
            {coGon && <p style={{ margin: "0 0 8px" }}><button type="button"
              onClick={() => { setChiTiet(null); setMoSan(""); }}>← Về màn gọn {trangMo.ten}</button></p>}
            {!coGon && <h2 style={{ marginTop: 0 }}>{trangMo.ten}</h2>}
            {!coGon && trangMo.ghi && <p className="muted">{trangMo.ghi}</p>}
            <KhungNhung key={toi + moSan} toi={toi} ten={trangMo.ten} mo={moSan || undefined} />
          </>;
        })()}
    </section>}

    {/* ④ TỔNG QUAN */}
    {!nhomMo && <>
      {dang && !d && <p className="muted">Đang đọc số…</p>}

      {/* SẴN SÀNG VẬN HÀNH (Chủ tịch duyệt 10/11/2026): còn thiếu gì, mỗi dòng mở đúng trang con. */}
      <SanSangVanHanh ky={ky} mo={(ma) => {
        const n = NHOM.find((g) => g.trang.some((t) => t.ma === ma));
        if (n) { setNhom(n.ma); setTrang(ma); setMoSan(""); setChiTiet(null); }
      }} />

      {/* HAI CỬA NHẬP — chỉ xuất hiện MỘT lần trên cả màn (v3.3). */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center",
                    justifyContent: "space-between", marginBottom: 10 }}>
        <strong>THÁNG {kyDoc(ky)}</strong>
        <label className="muted">Số tiền theo{" "}
          <select value={theoTien} onChange={(e) => setTheoTien(e.target.value as any)}>
            <option value="qt">Chuyến đã quyết toán</option>
            <option value="tat_ca">Tất cả chuyến ghi nhận</option>
          </select></label>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 12, marginBottom: 18 }}>
        {CUA_NHAP.map((c) => (
          <button key={c.trang} type="button"
                onClick={() => { setNhom("finance"); setTrang(c.trang); setMoSan(c.mo); }}
                style={{ textAlign: "left", display: "block", padding: "14px 16px", borderRadius: 10, cursor: "pointer",
                         border: "1px solid #dce3ec", borderTop: "3px solid #1d5bbf", background: "#fff" }}>
            <small className="muted" style={{ display: "block", letterSpacing: ".04em" }}>{c.nhan}</small>
            <strong style={{ display: "block", fontSize: "1.1em", margin: "2px 0" }}>{c.ten}</strong>
            <span className="muted">{c.buoc} →</span>
          </button>))}
      </div>

      {/* ⑤ KHỐI HIỆU QUẢ ĐỘI XE — RÁP NGUYÊN KHỐI CỦA MÀN CHỦ TỊCH.
          Doanh thu · lợi nhuận · biên · ngày xe · tiêu hao · km rỗng · công suất · xe đang đi,
          ô chọn kỳ Tháng/Quý/Năm, và hình diễn biến 12 kỳ — tất cả đã có sẵn, không viết lại.
          Số của nó đi qua `fleet_lai_lo.bao_cao`, cùng phép tính với màn Lãi lỗ đội xe. */}
      {!boKy && <p className="muted">Đang tính khối hiệu quả đội xe… (cửa này nặng, 10–30 giây)</p>}
      <KhoiHieuQuaXe theo_ky={boKy} xe={d?.xe_lenh} sheet={xe}
        chuaKhop={xe?.canh_bao ? { sheet: xe.dang_di ?? 0, nhat_trinh: xe.vtos_dang_chay ?? 0 } : null} />
      {/* «Số tiền theo: tất cả chuyến ghi nhận» — lợi nhuận vẫn chỉ đếm chuyến đã quyết toán (KS-65): chuyến chưa
          quyết toán chưa có dòng chi phí nào, cộng doanh thu của nó vào lợi nhuận là làm biên đẹp hơn sự thật. */}
      {theoTien === "tat_ca" && boKy && (() => {
        const o = boKy?.[boKy?.mac_dinh || "thang"] || {};
        const treo = o?.doanh_thu_chua_quyet_toan ?? sk?.doanh_thu_chua_quyet_toan;
        return <p className="muted" style={{ margin: "8px 0" }}>
          Tất cả chuyến ghi nhận: doanh thu {(((o?.doanh_thu || 0) + (treo || 0)) / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr
          {treo ? <> — gồm <b>{(treo / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} tr</b> chuyến chưa quyết toán, chưa có chi phí</> : null}.
          Lợi nhuận tạm tính vẫn chỉ đếm chuyến đã quyết toán.</p>;
      })()}

      {/* CHƯA NHẬP ≠ BẰNG 0 — không phải một con số cạnh tranh với khối trên, mà là lời nói ra
          rằng con số ấy còn thiếu nhóm nào. Giữ lại chính vì thế. */}
      {sk?.chua_nhap?.length > 0 && <p style={{ margin: "10px 0 18px" }}>
        <ChuaNhap />{" "}
        <span className="muted">
          Kỳ {kyDoc(sk.ky)} chưa có số cho: {sk.chua_nhap.map((n: any) => n.ten).join(" · ")} —
          lợi nhuận ở trên đang cao hơn thực tế. Đó là THIẾU SỐ, không phải bằng 0.{" "}
          <Link href="/lai-lo-doi-xe">Mở sổ chi phí kỳ →</Link>
        </span>
      </p>}
      {/* Nguồn «xe đang đi» lệch nhau thì nói thẳng, không để ô kia đứng một mình (KS-49). */}
      {xe?.canh_bao && <p style={{ color: "#a66a00" }}>{xe.canh_bao}</p>}

      {/* ⑥ HÀNG ĐỢI VIỆC — v3.3 đặt DƯỚI biểu đồ. */}
      {hd && <section style={{ marginBottom: 18 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "baseline",
                      justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Việc cần xử lý</h2>
          <span className="muted">
            {hd.so_viec_cua_toi} việc · <strong style={{ color: "#be2f2f" }}>{hd.so_do} đỏ</strong>
            {hd.so_cho_nguoi_khac > 0 && ` · ${hd.so_cho_nguoi_khac} đang chờ người khác`}
          </span>
        </div>

        {hd.viec.length === 0
          ? <p className="muted">Không có việc nào đang mở. Đây là số thật, không phải thiếu nguồn.</p>
          : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 440px), 1fr))", columnGap: 28 }}>
          {hd.viec.map((v: any) => (
            <div key={v.ma} style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center",
                                     padding: "12px 0", borderBottom: "1px solid #e6eaf0" }}>
              <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: "50%",
                flex: "0 0 10px", background: (MAU[v.muc] || MAU.vang).cham,
                border: v.muc === "trang" ? "2px solid #afbcce" : undefined }} />
              <span style={{ flex: "999 1 320px", minWidth: 0 }}>
                <strong style={{ display: "block" }}>{v.tieu_de}</strong>
                <span className="muted">{v.mo_ta}</span>
              </span>
              {/* Quyền ẩn NÚT, không ẩn VIỆC: giám đốc vẫn thấy tiền đang treo kể cả khi chưa
                  được bấm. Giấu việc đi thì tiền treo biến mất khỏi tầm mắt người duy nhất
                  quan tâm đến nó. */}
              {v.bam_duoc && v.ngan_keo
                ? <button type="button" onClick={() => setKeo(v.ngan_keo)}>{v.nhan_nut}</button>
                : <span className="muted"><strong>{v.nhan_nut}</strong></span>}
            </div>))}</div>}

        {hd.bo_do_hong?.length > 0 && <p style={{ color: "#a66a00" }}>
          {hd.bo_do_hong.length} bộ dò lỗi ({hd.bo_do_hong.join(", ")}) — hàng đợi đang thiếu dòng,
          báo CNTT.
        </p>}
      </section>}

      {/* ⑦ KHỐI MỤC LỤC PHÂN HỆ (KS-56) ĐÃ GỠ — Chủ tịch duyệt 10/11/2026 theo demo v3.3: màn kết thúc ở
          «Việc cần xử lý». Khối ấy lặp lại thanh năm mục và còn ghi mục «Bàn làm việc». Mọi trang của
          nó vẫn mở được từ thanh con ở trên. */}
    </>}

    {/* NGĂN KÉO */}
    {k && <>
      <div onClick={() => setKeo(null)}
           style={{ position: "fixed", inset: 0, background: "rgba(14,42,82,.42)", zIndex: 40 }} />
      <aside role="dialog" aria-modal="true" aria-label={k.ten}
             style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: "min(720px, 94vw)",
                      background: "#fff", zIndex: 41, overflowY: "auto", padding: 22,
                      boxShadow: "-12px 0 28px rgba(14,42,82,.22)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start",
                      gap: 12, marginBottom: 14 }}>
          <div>
            <h2 style={{ margin: 0 }}>{k.ten}</h2>
            <p className="muted" style={{ margin: 0 }}>Kỳ {kyDoc(ky)}</p>
          </div>
          <button type="button" aria-label="Đóng ngăn kéo" onClick={() => setKeo(null)}>✕</button>
        </div>
        {/* NGĂN KÉO GẮN LẠI CHÍNH KHỐI CỦA MÀN CÓ SẴN, không dựng form thứ hai.
            `ChiPhiKyPanel` là tab «Chi phí kỳ» của /lai-lo-doi-xe chuyển nguyên văn ra. */}
        {hd?.viec.filter((v: any) => v.ngan_keo === keo).map((v: any) => (
          <p key={v.ma}><strong>{v.tieu_de}</strong><br /><span className="muted">{v.mo_ta}</span></p>
        ))}
        {keo === "chi-phi-ky"
          ? <ChiPhiKyPanel ky={ky} onDoiSo={() => doc(ky)} />
          : <p><Link href={k.toi}>{k.nhan} →</Link></p>}
        <p className="muted">Đóng ngăn kéo thì bàn tự đọc lại số.</p>
        <button type="button" onClick={() => { setKeo(null); doc(ky); }}>Xong — đọc lại số</button>
      </aside>
    </>}
  </>);
}

/* Màn không thanh dọc trải hết bề ngang — bản vẽ v3.3: biểu đồ chiếm toàn hàng. Thẻ style của riêng màn
   này (chỉ sống khi /xe đang mở), không thêm lớp vào globals.css hay Shell.tsx (nhiều làn cùng giữ). */
const RONG = <style>{`main{max-width:none!important}`}</style>;

export default function Page() {
  return <Shell khongThanhBen>{RONG}<BanLamViecXe /></Shell>;
}
