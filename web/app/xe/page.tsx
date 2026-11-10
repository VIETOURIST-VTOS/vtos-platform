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
import LichXe90 from "@/components/doixe/LichXe90";

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
    // VH-9 (Chủ tịch duyệt 11/11/2026): lịch 90 ngày tới — công suất và khoảng trống để Kinh doanh đẩy bán.
    { ma: "lich-90", ten: "Lịch xe 90 ngày", toi: "/lenh-dieu-xe" },
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
    // VH-11 (Chủ tịch duyệt 11/11/2026): nút «Hiệu quả» bỏ — tổng kết kỳ và bản tin sáng trùng bàn làm
    // việc; hai phần KHÔNG trùng chuyển về đây. `chi=xep-hang` giấu hai khối trùng của trang cũ.
    { ma: "hieu-qua", ten: "Xếp hạng xe & tài xế", toi: "/hieu-qua-doi-xe?chi=xep-hang" },
    { ma: "nhin-lai", ten: "Nhìn lại thuê xe ngoài", toi: "/doi-xe?tab=nhin-lai" },
  ] },
  { ma: "technical", ten: "Bảo dưỡng & sự cố", tom: "Bảo dưỡng · báo hỏng · dầu và định mức", trang: [
    { ma: "bao-duong", ten: "Bảo dưỡng", toi: "/doi-xe?tab=bao-duong" },
    { ma: "bao-hong", ten: "Báo hỏng", toi: "/doi-xe?tab=bao-hong" },
    { ma: "dau", ten: "Dầu & định mức", toi: "/doi-xe/gia-dau" },
    { ma: "su-co", ten: "Sự cố tour", toi: "/su-co-tour" },
  ] },
];

/** MÀN GỌN theo mã trang con — trang nào không có ở đây thì vẫn mở màn đang chạy. */
type GonProps = { mo: (toi: string) => void; ky: string; onNhap: () => void };
const MAN_GON: Record<string, (p: GonProps) => React.ReactNode> = {
  "lich": (p) => <G.LichLenhGon mo={p.mo} />,
  "lich-90": (p) => <LichXe90 mo={p.mo} />,
  "ho-so-xe": (p) => <G.HoSoXeGon mo={p.mo} />,
  "bao-cao-xe": (p) => <G.BaoCaoXeGon mo={p.mo} onNhap={p.onNhap} ky={p.ky} />,
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
/** VH-6 (Chủ tịch dặn 10/11/2026): «bấm vào chi tiết thì nhảy qua màn hình tổng CRM — không phải thao tác
 *  trên màn hình riêng». Mọi đường dẫn có tiền tố dưới đây là màn của đội xe: bấm ở /xe hay bấm trong khung
 *  nhúng đều MỞ TẠI CHỖ trong /xe, không sang trang có thanh dọc CRM, không mở tab mới. Lối ra duy nhất là
 *  chữ «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu (VH-8). */
const DUONG_DOI_XE = ["/doi-xe", "/lai-lo-doi-xe", "/lenh-dieu-xe", "/tai-xe", "/hieu-qua-doi-xe", "/su-co-tour", "/nap-du-lieu"];
const laDoiXe = (href: string) => DUONG_DOI_XE.some((t) => href === t || href.startsWith(t + "/") || href.startsWith(t + "?"));

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
        st.textContent = ".top,aside.side{display:none!important}main{max-width:none!important;padding:0!important;margin:0!important}body{background:transparent!important}"
          // VH-6: vụn đường «VTOS · Đội xe · …» dẫn về trang chủ CRM — trong /xe thì giấu, cùng mũi tên «mở tab mới».
          + ".thanh-viec .tv-duong,.thanh-viec .tv-mui{display:none!important}";
        doc.head.appendChild(st);
        // VH-6: liên kết trong khung — màn đội xe mở NGAY TRONG KHUNG (kể cả nút ↗ vốn mở tab mới);
        // liên kết về trang chủ / phân hệ CRM thì không đi đâu cả.
        doc.addEventListener("click", (e) => {
          const a = (e.target as HTMLElement | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
          if (!a) return;
          const h = a.getAttribute("href") || "";
          if (!h.startsWith("/")) return;
          e.preventDefault();
          if (laDoiXe(h)) f.contentWindow?.location.assign(h);
        }, true);
      }
      const dat = () => setCao(Math.max(400, b.scrollHeight + 24));
      dat();
      const ro = new ResizeObserver(dat);
      ro.observe(b);
    } catch { /* khác nguồn thì giữ chiều cao mặc định */ }
  };
  // VH-6: bỏ «Mở toàn trang ↗» — nó đưa người dùng sang màn có thanh dọc CRM.
  return <>
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

/** VH-8 · biểu tượng năm nhóm — nét mảnh, màu theo chữ của nút. */
const ICON_NHOM: Record<string, React.ReactNode> = {
  dispatch: <><rect x="3" y="7" width="13" height="9" rx="2" /><path d="M16 10h3l2 3v3h-5" /><circle cx="7" cy="17" r="2" /><circle cx="17" cy="17" r="2" /></>,
  fleet: <><circle cx="12" cy="8" r="4" /><path d="M4 21c1-4 4-6 8-6s7 2 8 6" /></>,
  finance: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  technical: <path d="M14 7l3-3 3 3-3 3M17 4v6M4 20l7-7M9 9l6 6" />,
};

/** Nhãn viền màu của thẻ việc theo mức máy chủ trả. */
const NHAN_MUC: Record<string, string> = { do: "Đỏ", cam: "Cam", vang: "Vàng", trang: "Chờ người khác" };

/** Việc của hàng đợi ↔ dòng của bảng sẵn sàng nói CÙNG một chuyện. Hàng đợi giữ, bảng sẵn sàng bỏ. */
const TRUNG_SAN_SANG: Record<string, string[]> = {
  chi_phi_ky_thieu_nhom: ["ky"],
  xe_bi_chan_khai_thac: ["xe_bi_chan"],
  xe_chua_co_lich_su_bao_duong: ["xe_chua_bao_duong"],
};

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
  /* VH-10: số ngày-xe còn trống trong 30 ngày tới, in trên nút vàng «Lịch xe 90 ngày». Gọi riêng, không
     chờ; hỏng thì nút vẫn hiện, chỉ thiếu con số. */
  const [trong30, setTrong30] = useState<number | null>(null);
  useEffect(() => {
    if (khongCoQuyen) return;
    api("/fleet/lich-xe-tuong-lai?so_ngay=30").then((r: any) => setTrong30(r?.ngay_xe_trong ?? null)).catch(() => {});
  }, [khongCoQuyen]);
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

  /* VH-8 (Chủ tịch 11/11/2026): gộp «Trang tổng CRM» vào chữ «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu. Thanh đầu là
     Shell.tsx (làn R2 giữ) nên không sửa ở đó: /xe gắn một lối bấm vào chính chữ ấy khi màn này đang mở. Logo bên
     cạnh vẫn về tổng quan /xe như cũ. */
  useEffect(() => {
    const chu = document.querySelector("a.brand small") as HTMLElement | null;
    if (!chu) return;
    const ve = (e: Event) => { e.preventDefault(); e.stopPropagation(); window.location.assign("/"); };
    chu.title = "Về trang tổng CRM";
    chu.addEventListener("click", ve, true);
    return () => { chu.removeEventListener("click", ve, true); chu.removeAttribute("title"); };
  }, []);
  /* VH-12 (Chủ tịch duyệt 11/11/2026): logo nổi bật trên ô nền trắng bo tròn — cần bản chữ navy cho nền sáng
     (`khoachu-holdings-ngang.svg`). Đổi ảnh khi /xe mở, trả lại khi rời màn; Shell.tsx không sửa. */
  useEffect(() => {
    const img = document.querySelector("a.brand img.brand-logo") as HTMLImageElement | null;
    if (!img) return;
    const cu = img.getAttribute("src") || "";
    img.setAttribute("src", "/thuong-hieu/v2/khoachu-holdings-ngang.svg");
    img.classList.add("xe-logo-o");
    return () => { img.setAttribute("src", cu); img.classList.remove("xe-logo-o"); };
  }, []);
  const hd = d?.hang_doi, sk = d?.so_ky, xe = d?.xe_hom_nay;
  /** «Mỗi nút một chỗ» (Chủ tịch dặn 10/11/2026): việc nào «Việc cần xử lý» đã nói thì bảng sẵn sàng
   *  không nói lại. Khoá là mã việc của hàng đợi → mã dòng / mã nhóm của bảng sẵn sàng. */
  const daNoi: string[] = (hd?.viec || []).flatMap((v: any) => TRUNG_SAN_SANG[v.ma] || []);
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

  /** VH-6: mở một đường dẫn đội xe TẠI CHỖ — chọn trang con có `toi` khớp dài nhất, rồi mở chi tiết. */
  const moTaiCho = (href: string) => {
    const duong = href.split("?")[0];
    let tot: { n: string; t: string; dai: number } | null = null;
    for (const n of NHOM) for (const t of n.trang) {
      const td = t.toi.split("?")[0];
      const khop = href === t.toi ? 1000 : (duong === td || duong.startsWith(td + "/")) ? td.length : -1;
      if (khop > (tot?.dai ?? -1)) tot = { n: n.ma, t: t.ma, dai: khop };
    }
    // Không khớp trang con nào (vd. /nap-du-lieu — cửa nạp hồ sơ xe): đặt dưới «Hồ sơ xe».
    setNhom(tot ? tot.n : "fleet"); setTrang(tot ? tot.t : "ho-so-xe"); setMoSan(""); setChiTiet(href);
    setKeo(null);
    try { window.scrollTo({ top: 0 }); } catch { /* không cuộn được thì thôi */ }
  };
  const giuTaiCho = (e: React.MouseEvent) => {
    const a = (e.target as HTMLElement).closest?.("a[href]") as HTMLAnchorElement | null;
    const h = a?.getAttribute("href") || "";
    if (!a || !laDoiXe(h) || e.ctrlKey || e.metaKey || e.button === 1) return;
    e.preventDefault(); e.stopPropagation(); moTaiCho(h);
  };

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

  return (<div onClickCapture={giuTaiCho}>
    {/* VH-8 (Chủ tịch duyệt bản xem trước 11/11/2026): TIÊU ĐỀ LÊN ĐẦU, in hoa đậm; năm nhóm xuống dưới. */}
    <div className="xe-dau">
      <div>
        <span className="xe-dau-eb">Đội xe · Công ty TNHH Vận tải Vietrip</span>
        <h1>Bàn làm việc Giám đốc đội xe</h1>
      </div>
      <div className="xe-ky">
        <button type="button" className="xe-ky-quyen" onClick={() => setQuyen(!quyen)} aria-expanded={quyen}>Quyền của tôi</button>
        <button type="button" aria-label="Kỳ trước" onClick={() => setKy(doiKy(ky, -1))}>‹</button>
        <strong>{kyDoc(ky)}</strong>
        <button type="button" aria-label="Kỳ sau" onClick={() => setKy(doiKy(ky, 1))}>›</button>
      </div>
    </div>

    {/* ① NĂM MỤC NGHIỆP VỤ — một hàng ngang, KHÔNG có mục "Bàn làm việc" (v3.3). Lối ra khỏi đội xe nằm
        cuối hàng, vì màn này ẩn thanh dọc. VH-4: mỗi nhóm một nút navy sáng riêng, rộng theo chữ, thiếu chỗ
        thì cả nút xuống hàng. VH-8: có biểu tượng, và dính ở đầu màn khi cuộn. */}
    <div className="xe-nhom-dinh">
    <nav aria-label="Nghiệp vụ đội xe" className="xe-nhom">
      {/* VH-11: «Trang chủ» đầu dòng — đóng nhóm/trang con đang mở, về đầu bàn làm việc, không rời /xe. */}
      <button type="button" title="Về bàn làm việc Giám đốc đội xe" aria-pressed={nhom === null}
        onClick={() => { setNhom(null); setTrang(null); setMoSan(""); setChiTiet(null); window.scrollTo({ top: 0, behavior: "smooth" }); }}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11l9-7 9 7M5 10v10h5v-6h4v6h5V10" /></svg>
        Trang chủ
      </button>
      {NHOM.map((n) => (
        <button key={n.ma} type="button" title={n.tom}
          onClick={() => { setNhom(nhom === n.ma ? null : n.ma); setTrang(null); setMoSan(""); setChiTiet(null); }}
          aria-pressed={nhom === n.ma}>
          <svg viewBox="0 0 24 24" aria-hidden="true">{ICON_NHOM[n.ma]}</svg>
          {n.ten}
        </button>))}
    </nav>

    {/* ② THANH CON — chỉ hiện khi nhóm có nhiều hơn một trang (v3.3). */}
    {nhomMo && nhomMo.trang.length > 1 && <nav aria-label={`Trang của ${nhomMo.ten}`} className="xe-con">
      {nhomMo.trang.map((t) => (
        <button key={t.ma} type="button" onClick={() => { setTrang(t.ma); setMoSan(""); setChiTiet(null); }}
          aria-pressed={trangMo?.ma === t.ma}>
          {t.ten}
        </button>))}
    </nav>}
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
          // VH-13: trang nhúng có bảng theo kỳ (Xếp hạng, Lãi lỗ) đọc ĐÚNG tháng đang chọn ở ‹ › đầu /xe,
          // để màn và tệp Excel xuất ra cùng một kỳ — không có ô chọn kỳ thứ hai.
          const TRANG_THEO_KY = ["hieu-qua", "lai-lo"];
          const toi = chiTiet || (TRANG_THEO_KY.includes(trangMo.ma)
            ? trangMo.toi + (trangMo.toi.includes("?") ? "&" : "?") + `ky=${ky}` : trangMo.toi);
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
      {dang && !d && <div className="xe-cho" aria-busy="true" aria-label="Đang đọc số"><i /><i /><i /><i /></div>}

      {/* ⑥ HÀNG ĐỢI VIỆC — VH-4 (Chủ tịch duyệt 10/11/2026): LÊN ĐẦU tổng quan, viền navy; mục đỏ nền đỏ nhạt. */}
      {hd && <section className="xe-uu" aria-label="Việc cần xử lý">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "baseline",
                      justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Việc cần xử lý</h2>
          <span className="muted">
            {hd.so_viec_cua_toi} việc · <strong style={{ color: "#be2f2f" }}>{hd.so_do} đỏ</strong>
            {hd.so_cho_nguoi_khac > 0 && ` · ${hd.so_cho_nguoi_khac} đang chờ người khác`}
          </span>
        </div>

        {hd.viec.length === 0
          ? <p className="muted">Không có việc nào đang mở.</p>
          : <div className="xe-the-luoi">
          {/* VH-5 · kiểu thẻ (Chủ tịch duyệt 10/11/2026): mỗi việc một thẻ — mã việc nhỏ góc trái, nhãn viền
              màu góc phải, tên việc, mô tả, nút ở đáy. */}
          {hd.viec.map((v: any, i: number) => (
            <div key={v.ma} className={"xe-the" + (v.muc === "do" ? " xe-the-do" : "")}>
              <div className="xe-the-dau">
                <span className="xe-the-ma">VIỆC {String(i + 1).padStart(2, "0")}</span>
                <span className={"xe-pill xe-pill-" + (v.muc in NHAN_MUC ? v.muc : "vang")}>{(NHAN_MUC[v.muc] || NHAN_MUC.vang)}</span>
              </div>
              <strong className="xe-the-ten">{v.tieu_de}</strong>
              <span className="muted" style={{ fontSize: 13 }}>{v.mo_ta}</span>
              {/* Quyền ẩn NÚT, không ẩn VIỆC: giám đốc vẫn thấy tiền đang treo kể cả khi chưa
                  được bấm. Giấu việc đi thì tiền treo biến mất khỏi tầm mắt người duy nhất
                  quan tâm đến nó. */}
              <div className="xe-the-day">
                {v.bam_duoc && v.ngan_keo
                  ? <button type="button" className={v.muc === "do" ? "xe-nut-chinh" : undefined} onClick={() => setKeo(v.ngan_keo)}>{v.nhan_nut}</button>
                  : <span className="muted"><strong>{v.nhan_nut}</strong></span>}
              </div>
            </div>))}</div>}

        {hd.bo_do_hong?.length > 0 && <p style={{ color: "#a66a00" }}>
          {hd.bo_do_hong.length} bộ dò lỗi ({hd.bo_do_hong.join(", ")}) — hàng đợi đang thiếu dòng,
          báo CNTT.
        </p>}
      </section>}

      {/* HAI CỬA NHẬP — chỉ xuất hiện MỘT lần trên cả màn (v3.3). */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center",
                    justifyContent: "space-between", marginBottom: 10 }}>
        {/* VH-10 (Chủ tịch duyệt 11/11/2026): bỏ chữ «THÁNG …» lặp ô chọn kỳ; chỗ ấy là nút vàng nổi bật
            nhất màn, mở Lịch xe 90 ngày tại chỗ — xe nào còn trống để ưu tiên bán tour. */}
        <button type="button" className="xe-n90"
              onClick={() => { setNhom("dispatch"); setTrang("lich-90"); setMoSan(""); setChiTiet(null); }}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="17" rx="2" />
            <path d="M3 9h18M8 2v4M16 2v4M8 14h2M14 14h2M8 17h2" /></svg>
          <span><span className="xe-n90-t">Lịch xe 90 ngày</span>
            <span className="xe-n90-p">Xe nào còn trống · ưu tiên bán tour</span></span>
          {trong30 !== null && <span className="xe-n90-so">{trong30} ngày-xe trống</span>}
        </button>
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
                className="xe-cua">
            {/* VH-8: chữ canh giữa thẻ, bỏ dòng các bước, tên cửa nhập to và đậm. */}
            <small className="muted">{c.nhan}</small>
            <strong>{c.ten}</strong>
          </button>))}
      </div>

      {/* ⑤ KHỐI HIỆU QUẢ ĐỘI XE — RÁP NGUYÊN KHỐI CỦA MÀN CHỦ TỊCH.
          Doanh thu · lợi nhuận · biên · ngày xe · tiêu hao · km rỗng · công suất · xe đang đi,
          ô chọn kỳ Tháng/Quý/Năm, và hình diễn biến 12 kỳ — tất cả đã có sẵn, không viết lại.
          Số của nó đi qua `fleet_lai_lo.bao_cao`, cùng phép tính với màn Lãi lỗ đội xe. */}
      {!boKy && <div className="xe-cho xe-cho-3" aria-busy="true" aria-label="Đang tính khối hiệu quả đội xe"><i /><i /><i /></div>}
      <KhoiHieuQuaXe gon theo_ky={boKy} xe={d?.xe_lenh} sheet={xe}
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
      {sk?.chua_nhap?.length > 0 && !daNoi.includes("ky") && <p style={{ margin: "10px 0 18px" }}>
        <ChuaNhap />{" "}
        <span className="muted">
          Kỳ {kyDoc(sk.ky)} chưa có số cho: {sk.chua_nhap.map((n: any) => n.ten).join(" · ")} —
          lợi nhuận ở trên đang cao hơn thực tế. Đó là THIẾU SỐ, không phải bằng 0.{" "}
          <Link href="/lai-lo-doi-xe">Mở sổ chi phí kỳ →</Link>
        </span>
      </p>}
      {/* Nguồn «xe đang đi» lệch nhau thì nói thẳng, không để ô kia đứng một mình (KS-49). */}
      {xe?.canh_bao && <p style={{ color: "#a66a00" }}>{xe.canh_bao}</p>}

      {/* SẴN SÀNG VẬN HÀNH (Chủ tịch duyệt 10/11/2026): còn thiếu gì, mỗi dòng mở đúng trang con. */}
      <SanSangVanHanh ky={ky} an={daNoi} khongNut={["bao-cao-xe"]} mo={(ma) => {
        const n = NHOM.find((g) => g.trang.some((t) => t.ma === ma));
        if (n) { setNhom(n.ma); setTrang(ma); setMoSan(""); setChiTiet(null); }
      }} />

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
  </div>);
}

/* Màn không thanh dọc trải hết bề ngang — bản vẽ v3.3: biểu đồ chiếm toàn hàng. Thẻ style của riêng màn
   này (chỉ sống khi /xe đang mở), không thêm lớp vào globals.css hay Shell.tsx (nhiều làn cùng giữ). */
const RONG = <style>{`main{max-width:1440px!important;margin:0 auto!important}
/* VH-8 · HAI TẦNG: nền xám xanh (tầng 1), thẻ trắng có bóng nổi lên (tầng 2). Chỉ sống khi /xe đang mở. */
body,.shell{background:#eaf0f7!important}
:root{--xe-b1:0 1px 2px #12305414,0 4px 12px #1230541a;--xe-b2:0 2px 4px #12305414,0 10px 24px #12305421}
.xe-dau{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin:6px 0 16px}
.xe-dau-eb{display:block;font-size:11.5px;letter-spacing:1.6px;text-transform:uppercase;font-weight:700;color:var(--xe-nhan);margin-bottom:4px}
/* Tiêu đề nổi bật + hiệu ứng sáng (Chủ tịch dặn 11/11/2026): chữ chuyển màu navy → xanh sáng, một vệt sáng
   lướt qua chậm, quầng sáng nhẹ quanh chữ. Người tắt chuyển động thì chữ đứng yên, vẫn chuyển màu. */
.xe-dau h1{margin:0;font-size:34px;font-weight:800;letter-spacing:.6px;text-transform:uppercase;line-height:1.15;color:var(--xe-dam);
  background:linear-gradient(100deg,#183c69 0%,#2c5fa2 35%,#8cc4ff 50%,#2c5fa2 65%,#183c69 100%);background-size:220% 100%;
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 2px 10px #2c5fa240);animation:xe-sang 5s ease-in-out infinite}
@keyframes xe-sang{0%,100%{background-position:100% 0}50%{background-position:0 0}}
@media (prefers-reduced-motion:reduce){.xe-dau h1{animation:none;background-position:50% 0}}
.xe-dau p{margin:6px 0 0}
@media (max-width:640px){.xe-dau h1{font-size:23px}}
.xe-ky{display:flex;align-items:center;gap:6px;background:#fff;border-radius:12px;padding:6px;box-shadow:var(--xe-b1)}
.xe-ky button{font:inherit;border:0;background:var(--xe-nhat);color:var(--xe-nhan);min-width:34px;height:34px;border-radius:9px;font-weight:700;cursor:pointer}
.xe-ky .xe-ky-quyen{background:#fff;border:1px solid #c9d6e8;padding:0 12px;font-weight:600}
.xe-ky strong{min-width:92px;text-align:center;color:var(--xe-dam);font-variant-numeric:tabular-nums}
/* VH-10 · nút vàng Lịch xe 90 ngày — khác hẳn dàn nút navy; quầng sáng thở + vệt sáng lướt. */
.xe-n90{position:relative;overflow:hidden;display:inline-flex;align-items:center;gap:14px;border:0;cursor:pointer;
  padding:12px 22px 12px 16px;border-radius:14px;color:#3b2300;font:inherit;text-align:left;
  background:linear-gradient(135deg,#ffd76a 0%,#ffb627 55%,#ff9a1f 100%);
  box-shadow:0 0 0 3px #ffe7a8,0 6px 22px #ff9f1f66;animation:xe-tho 2.4s ease-in-out infinite;transition:transform .15s}
.xe-n90::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(110deg,transparent 35%,#ffffffb0 50%,transparent 65%);transform:translateX(-120%);animation:xe-luot 3.2s ease-in-out infinite}
.xe-n90:hover{transform:translateY(-2px)}
.xe-n90:focus-visible{outline:3px solid #b86b00;outline-offset:3px}
.xe-n90 svg{width:30px;height:30px;flex:none;fill:none;stroke:#5a3500;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.xe-n90-t{display:block;font-size:19px;font-weight:800;letter-spacing:.4px;text-transform:uppercase}
.xe-n90-p{display:block;font-size:13px;font-weight:600;opacity:.85}
.xe-n90-so{margin-left:6px;background:#3b2300;color:#ffd76a;border-radius:999px;padding:4px 11px;font-weight:800;font-size:13.5px;white-space:nowrap}
@keyframes xe-tho{0%,100%{box-shadow:0 0 0 3px #ffe7a8,0 6px 22px #ff9f1f55}50%{box-shadow:0 0 0 5px #ffe7a8,0 8px 34px #ff9f1fa0}}
@keyframes xe-luot{0%,55%{transform:translateX(-120%)}100%{transform:translateX(120%)}}
@media (prefers-reduced-motion:reduce){.xe-n90,.xe-n90::after{animation:none}}
@media (max-width:900px){.xe-n90{width:100%}.xe-n90-so{margin-left:auto}}
.xe-nhom-dinh{position:sticky;top:0;z-index:5;background:#eaf0f7;padding:6px 0 2px;margin-bottom:8px}
.xe-nhom button{display:inline-flex;gap:9px;align-items:center;justify-content:center;transition:transform .15s,box-shadow .15s,background .15s}
.xe-nhom button svg{width:18px;height:18px;flex:none;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.xe-nhom button:hover{transform:translateY(-1px);box-shadow:var(--xe-b2)}
main .panel{background:#fff;border:0!important;border-radius:16px!important;box-shadow:var(--xe-b1)!important}
.xe-cho{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:6px 0 16px}
.xe-cho-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.xe-cho i{display:block;height:96px;border-radius:14px;background:linear-gradient(90deg,#dfe7f1 25%,#eef3f9 50%,#dfe7f1 75%);background-size:200% 100%;animation:xe-nhay 1.2s linear infinite}
@keyframes xe-nhay{to{background-position:-200% 0}}
@media (prefers-reduced-motion:reduce){.xe-cho i{animation:none}.xe-the,.xe-cua,.xe-nhom button{transition:none!important}}
.xe-so-chu{position:relative;border:0!important;border-radius:16px!important;padding:18px 20px!important;box-shadow:var(--xe-b2)!important;
  background:linear-gradient(135deg,#2c5fa2,#214c82)!important;color:#fff}
.xe-so-chu:nth-child(2){background:linear-gradient(135deg,#1f7a63,#14604e)!important}
.xe-so-chu:nth-child(3){background:linear-gradient(135deg,#3b4f7a,#2b3b5e)!important}
.xe-so-chu .v14-o-nhan{color:#fff!important;opacity:.85;text-transform:uppercase;letter-spacing:.8px;font-size:12.5px}
.xe-so-chu .v14-o-so{color:#fff!important;font-size:40px!important;font-weight:600}
.xe-so-chu *{color:#fff}
/* VH-4 · điểm nhấn navy sáng trên nền trắng (Chủ tịch duyệt bản xem trước 10/11/2026). Chỉ sống khi /xe
   đang mở; không thêm vào globals.css hay Shell.tsx. */
:root{--xe-nhan:#2c5fa2;--xe-dam:#183c69;--xe-nhat:#edf3fc;--xe-vien:#e1e7ef;--xe-do:#b72f45;--xe-do-nen:#fff0f3}
/* VH-8: năm nút chia đều cả hàng; màn hẹp thì xuống hai cột. */
.xe-nhom{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;align-items:stretch;margin-bottom:8px}
@media (max-width:900px){.xe-nhom{grid-template-columns:repeat(2,minmax(0,1fr))}.xe-nhom button:last-child{grid-column:span 2}}
.xe-nhom button{flex:1 1 auto;white-space:nowrap;font:inherit;font-size:14.5px;font-weight:600;color:#fff;
  background:var(--xe-nhan);border:0;border-radius:10px;min-height:46px;padding:8px 14px;cursor:pointer;box-shadow:0 2px 6px #2c5fa230}
.xe-nhom button:hover{background:#3a6fb5}
.xe-nhom button[aria-pressed=true]{background:var(--xe-dam);box-shadow:0 0 0 3px #9fc0ec}
.xe-nhom button:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
@media (max-width:520px){.xe-nhom button{font-size:14px}}
.xe-con{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 14px}
.xe-con button{font:inherit;font-size:13.5px;border:1px solid var(--xe-vien);background:#fff;border-radius:8px;padding:6px 12px;cursor:pointer}
.xe-con button[aria-pressed=true]{background:var(--xe-nhan);border-color:var(--xe-nhan);color:#fff;font-weight:600}
.xe-uu{border:0;border-radius:16px;background:#fff;padding:16px 20px 10px;margin-bottom:18px;box-shadow:var(--xe-b1)}
.xe-uu h2{color:var(--xe-dam)}
.xe-it{display:flex;flex-wrap:wrap;gap:10px;align-items:center;padding:10px 0;border-bottom:1px solid #eef2f7}
.xe-it:last-child{border-bottom:0}
.xe-do{background:var(--xe-do-nen);margin:0 -15px;padding:10px 15px;border-bottom-color:#f6d6dd}
.xe-do strong,.xe-do b{color:var(--xe-do)}
.xe-nut-chinh{background:var(--xe-nhan)!important;border-color:var(--xe-nhan)!important;color:#fff!important;font-weight:600}
.xe-cua{text-align:left;display:block;padding:13px 16px;border-radius:10px;cursor:pointer;border:1px solid var(--xe-vien);
  border-top:3px solid var(--xe-nhan);background:#fff;font:inherit}
.xe-cua strong{color:var(--xe-nhan)}
.xe-blk{border:1px solid var(--xe-vien);border-radius:12px;padding:12px 15px;background:#fff}
.xe-blk .xe-do{margin:0;border-radius:8px;padding:10px 12px}
.xe-thanh{height:6px;border-radius:99px;background:var(--xe-vien);overflow:hidden;margin-top:6px}
.xe-thanh i{display:block;height:100%;background:var(--xe-nhan)}
/* VH-5 · kiểu thẻ: bo góc 12px, viền mảnh, bóng nhẹ; nhãn viền màu; mã nhỏ chữ đơn cách */
.xe-the-luoi{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:14px;padding:6px 0 10px}
.xe-the{background:#fbfcfe;border:1px solid #d6dfeb;border-radius:13px;padding:14px;display:flex;flex-direction:column;gap:6px;min-width:0;transition:transform .15s,box-shadow .15s,background .15s}
.xe-the:hover{transform:translateY(-2px);box-shadow:var(--xe-b2);background:#fff}
.xe-the-do{background:#fffafb}
/* nút nhỏ một cỡ một kiểu */
.xe-the-day button,.xe-it button,.xe-blk button{font:inherit;font-size:13px;font-weight:600;border-radius:9px;padding:7px 13px;cursor:pointer;
  border:1px solid #c9d6e8;background:#fff;color:var(--xe-nhan);margin:0}
.xe-the-day button:hover,.xe-it button:hover,.xe-blk button:hover{background:var(--xe-nhat)}
.xe-the-do{border-color:#efc3cc}
.xe-the-dau{display:flex;justify-content:space-between;align-items:center;gap:8px}
.xe-the-ma{font-family:var(--vtos-font-mono,ui-monospace,monospace);font-size:12px;color:#5b6876;letter-spacing:.5px}
.xe-the-ten{font-size:15.5px;color:var(--xe-dam)}
.xe-the-do .xe-the-ten{color:var(--xe-do)}
.xe-the-day{margin-top:auto;padding-top:4px;display:flex;justify-content:flex-end}
.xe-pill{font-size:12px;font-weight:600;border-radius:999px;padding:1px 10px;border:1.5px solid currentColor;white-space:nowrap}
.xe-pill-do{color:var(--xe-do)}.xe-pill-cam{color:#a66a00}.xe-pill-vang{color:#885b08}.xe-pill-trang{color:#5b6876}
.xe-cua,.xe-blk,#hieu-qua-doi-xe{border:0!important;border-radius:16px!important;box-shadow:var(--xe-b1)!important;background:#fff}
.xe-cua{border-top:4px solid var(--xe-nhan)!important;transition:transform .15s,box-shadow .15s;
  display:flex!important;flex-direction:column;align-items:center;justify-content:center;text-align:center!important;gap:4px;min-height:104px}
.xe-cua small{display:block;font-size:11.5px;letter-spacing:1.2px;text-transform:uppercase}
.xe-cua strong{display:block;font-size:23px;font-weight:800;letter-spacing:.2px;color:var(--xe-nhan)}
/* VH-8: «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu là lối về trang tổng CRM (thay nút «Trang tổng CRM →»). */
/* VH-12 · logo trên ô trắng bo tròn: viền ba màu logo chạy chậm (lớp border-box), vệt sáng lướt (lớp
   padding-box, nằm dưới nét logo), quầng sáng xanh quanh ô. */
a.brand img.xe-logo-o{box-sizing:content-box;height:46px;width:auto;padding:7px 18px;border:2px solid transparent;border-radius:16px;
  background:linear-gradient(110deg,#fff 40%,#eef5ff 50%,#fff 60%) padding-box,
    linear-gradient(120deg,#5A9BD4,#FF6F96,#5FAE66,#5A9BD4) border-box;
  background-size:250% 100%,300% 100%;box-shadow:0 0 0 4px #8cc4ff40,0 6px 20px #0a234866;
  animation:xe-logo-vien 6s linear infinite;transition:transform .2s,box-shadow .2s}
a.brand:hover img.xe-logo-o{transform:translateY(-1px);box-shadow:0 0 0 6px #8cc4ff70,0 10px 26px #0a234888}
@keyframes xe-logo-vien{from{background-position:120% 0,0 0}to{background-position:-120% 0,300% 0}}
@media (prefers-reduced-motion:reduce){a.brand img.xe-logo-o{animation:none}}
@media (max-width:640px){a.brand img.xe-logo-o{height:32px;padding:5px 12px;border-radius:12px}}
a.brand:has(img.xe-logo-o) small{font-size:12px;font-weight:700;letter-spacing:.18em;opacity:1;text-shadow:0 0 12px #8cc4ff99}
a.brand small{cursor:pointer;border-radius:6px;padding:2px 6px;transition:background .15s}
a.brand small:hover{background:#ffffff26;text-decoration:underline}
.xe-cua:hover{transform:translateY(-2px);box-shadow:var(--xe-b2)!important}
button.act.teal{background:var(--xe-nhan)!important;border-color:var(--xe-nhan)!important;color:#fff!important}
`}</style>;

export default function Page() {
  return <Shell khongThanhBen>{RONG}<BanLamViecXe /></Shell>;
}
