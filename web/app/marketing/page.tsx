"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
// MKT-3 · 09/11/2026 — `GROUPS` là bảng menu mà THANH DỌC đọc. Thanh chức năng ngang ở
// dưới đọc đúng bảng ấy, nên hai chỗ không bao giờ lệch nhau được.
import Shell, { useShell, GROUPS, VAI_BAN_PTGD, VAI_BAN_NV } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT, pct, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import BaoCaoChuyenDoi, { tyLe } from "@/components/BaoCaoChuyenDoi";
// MKT-2 · 09/11/2026 — mục lục chức năng của phân hệ dọn về đây, thành tab thứ tám.
// `khongChip` vì đây đã là màn của phòng: chip sang phân hệ khác thuộc về trang mục lục
// đứng riêng, không thuộc một tab bên trong màn hình nghiệp vụ. Màn `/xe` đã gắn mục lục
// vào chính nó đúng kiểu này từ trước, nên đây là đi theo nếp có sẵn chứ không mở nếp mới.
import MucLucPhanHe from "@/components/MucLucPhanHe";
import KhungNhung from "@/components/KhungNhung";
import NutLich90, { VAI_NUT_LICH_90 } from "@/components/NutLich90";
import { useHomNay } from "@/components/DauManHinh01";
import { useHoi } from "@/components/HopHoi";

/** KHÔNG GIAN LÀM VIỆC MARKETING & PR — bảy màn hình, một chỗ (18/9/2026)
 *
 *  Dựng theo bản vẽ "VTOS · Marketing & PR · V3.0" anh Tuấn gửi, với MỘT khác biệt đã xin ý kiến và
 *  được chốt: bản vẽ nền SÁNG, còn VTOS đã chuyển sang nền TỐI từ 13/9/2026 (xem đầu tệp
 *  app/tokens.css). Dựng đúng bản vẽ thì Marketing thành căn phòng trắng duy nhất trong toà nhà
 *  tối, và mỗi lần đổi nhận diện phải sửa hai nơi. Nên bố cục, luồng và nội dung của V3.0 giữ
 *  nguyên; lớp màu lấy từ bộ nhận diện đang chạy. Màn hình này KHÔNG khai màu riêng một dòng nào.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *  HAI ĐƯỜNG DẪN CŨ KHÔNG ĐƯỢC GÃY
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *  Thanh menu (components/Shell.tsx) đang trỏ hai chỗ vào màn hình này, và test_menu.py canh đúng
 *  từng ký tự của hai dòng ấy:
 *      ["Kế hoạch & ngân sách", "/marketing?tab=ngansach"]
 *      ["Chiến dịch",           "/marketing"]
 *  Nên: `/marketing` không tham số vẫn mở THẲNG Chiến dịch (menu nói Chiến dịch thì phải ra Chiến
 *  dịch), và `?tab=ngansach` vẫn mở thẳng phần Ngân sách. Tổng quan là tab ĐẦU của dải, cách một
 *  cú bấm. Đổi nhãn menu để `/marketing` mở Tổng quan là việc HAI ĐẦU (Shell.tsx + test_menu.py),
 *  thuộc làn menu — không gộp vào đây, vì sửa một đầu là đầu kia đỏ.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *  BA MÀN HÌNH CỦA BẢN VẼ CHƯA CÓ SỐ ĐỂ CHẠY — VÀ MÀN HÌNH NÓI THẲNG RA
 *  ═══════════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9/2026: mỗi con số phải có một CỬA cho người dùng đưa số vào; không có cửa thì đó
 *  là việc còn thiếu, không phải chỗ để bịa một con số mẫu. Đo ngày 18/9 trên chính kho mã:
 *      · Tổng quan          – KHÔNG cần cửa mới: gộp lại từ bốn cửa đã có. Dựng được.
 *      · Đối soát dữ liệu   – có sẵn POST /leads/match và POST /leads/stats. Dựng được.
 *      · Thương hiệu & PR   – KHÔNG có bảng, KHÔNG có đường API nào. Dựng ra chỉ có thể là số giả.
 *  Nên tab Thương hiệu & PR ở đây là một BẢN KÊ VIỆC CÒN THIẾU, không phải một bảng trống.
 */

const today = () => new Date().toISOString().slice(0, 10);
const thang0 = () => new Date().toISOString().slice(0, 7);
const RONG = { name: "", objective: "ra_lead", product_id: "", mang: "le", channels: [] as string[],
               from_date: today(), to_date: "", budget: "", target_leads: "", target_bookings: "",
               owner_id: "", note: "", nguon_tao: "nguoi", ai_ghi_chu: "" };

const TABS: [string, string, string][] = [
  ["tongquan",   "Tổng quan",                "Nhìn kết quả, nhận biết tồn đọng, mở đúng hồ sơ cần xử lý."],
  ["khach",      "Khách tiềm năng & Sales",  "Một hồ sơ khách, nhiều nhu cầu; tiếp nhận và phối hợp trên cùng dữ liệu."],
  // MKT-5 · 09/11/2026 — tên cũ «Chuyển đổi & doanh thu» đụng CẢ HAI màn hình riêng của
  // phòng cùng lúc: «Chuyển đổi & phối hợp Sales» (/chuyen-doi-lead) và «Đóng góp doanh
  // thu» (/dong-gop-marketing). Việc thật của tab này hẹp hơn hai màn ấy, và tên mới nói
  // đúng cái việc hẹp ấy: tách ba cái tháng hay bị lẫn rồi ra tỷ lệ chốt theo quy tắc
  // overview-v1 Chủ tịch ký 14/9/2026.
  ["chuyendoi",  "Tỷ lệ chốt theo kỳ",
   "Tách tháng phát sinh lead, tháng chốt booking và tháng khởi hành."],
  ["chiendich",  "Ngân sách & chiến dịch",   "Theo dõi kế hoạch, chi phí và kết quả trên cùng chiến dịch."],
  // MKT-5 · 09/11/2026 — tên cũ TRÙNG Y HỆT màn hình «Đối soát dữ liệu Marketing»
  // (/doi-soat-marketing), mà hai chỗ làm hai việc khác nhau: ở ĐÂY là cửa KHAI số lead và
  // chi phí theo kênh, kèm nút CHẠY đối chiếu lead ↔ booking; còn ĐỌC kết quả — đối chiếu
  // ba sổ, trùng & thiếu nguồn, chuẩn kỳ & độ trôi — là ở màn hình kia. Một cái tên trỏ hai
  // nơi thì người bấm phải đoán, và đoán sai thì họ tưởng màn hình hỏng.
  //
  // ĐỔI NHÃN, KHÔNG ĐỔI KHOÁ: khoá `doisoat` giữ nguyên từng ký tự, nên mọi `?tab=doisoat`
  // đã gửi nhau, mọi dấu trang, và mọi ô trên hai bàn làm việc vẫn mở đúng chỗ cũ.
  ["doisoat",    "Khai kênh & chạy đối chiếu",
   "Khai số lead và chi phí theo kênh, rồi chạy đối chiếu lead ↔ booking."],
  // MKT-5 · 09/11/2026 — tên cũ «Nội dung & kênh» gần trùng màn hình «Nội dung & thương
  // hiệu» (/noi-dung). Tên mới không nghĩ ra gì cả, nó chép lại đúng câu mà CHÍNH TAB NÀY
  // đang tự viết ra cho người dùng đọc: «Soạn bài, đính tệp và chuyển trạng thái nằm ở màn
  // hình Nội dung & thương hiệu. Ở đây là hàng đợi của phòng: cái gì đang chờ ai.»
  // Trang đã biết nó là hàng đợi từ lâu; đợt này chỉ làm cái tên nói đúng điều ấy.
  ["noidung",    "Hàng đợi duyệt nội dung",
   "Nội dung nào đang chờ ai duyệt. Soạn bài ở màn hình Nội dung & thương hiệu."],
  // Tên cũ là "Thương hiệu & PR". Đổi 19/9/2026 vì tab này giữ HÀNG ĐỢI KHỦNG HOẢNG và sổ PR
  // kèm đồng hồ hai giờ — thứ người ta cần tìm lúc gấp nhất. Tên cũ không gợi gì tới việc ấy.
  ["thuonghieu", "Khủng hoảng, PR & thương hiệu",
   "Hàng đợi tin nghi ngờ, sổ hoạt động PR kèm hạn phản hồi, và tài sản thương hiệu."],
  // MKT-2 · 09/11/2026 — ĐỨNG CUỐI, và đó là chủ ý. Bảy tab trên là việc làm hằng ngày;
  // tab này trả lời một câu khác hẳn và hỏi mỗi tháng một lần: «phòng này còn nợ màn hình
  // nào so với bản vẽ V1.3». Đặt nó lên trên là bắt người làm việc đi qua một bản kiểm kê
  // mỗi lần mở máy.
  ["muc-luc", "Mục lục chức năng",
   "Toàn bộ mục của phân hệ theo bản vẽ V1.3, ghi rõ mục nào đã có trang và mục nào còn nợ."],
];

/** MƯỜI HAI MỤC CỦA PHÒNG MARKETING — đọc THẲNG từ bảng menu, không chép tay.
 *
 *  Chép tay thì ngày thêm một màn hình, một trong hai chỗ sẽ quên — và mục bị quên là mục
 *  không ai tới được. Đo được đúng chuyện ấy ngày 09/11/2026: mười hai mục này ĐÃ ĐƯỢC KHAI
 *  trong `GROUPS` từ lâu, nhưng thanh dọc của crm chỉ vẽ tám phân hệ và các phòng con, nên
 *  không mục nào trong số chúng có mặt trong DOM. Chúng chỉ tới được bằng cách gõ đường dẫn.
 */
//  MKT-4 · 09/11/2026 — SỬA LỖI CỦA CHÍNH MKT-3, đo được trên bản thật ngay sau khi gộp:
//  màn `/marketing` nổ trắng, «TypeError: n is not iterable». Chủ trương đúng, KIỂU DỮ LIỆU
//  sai. Trong `Shell.tsx`: `type Block = Item | Section` — `Item` là một cặp
//  ["tên", "đường dẫn"], còn `Section` là `{ label, items: Item[] }`. Nhóm `marketing` có
//  mười một phần tử: mười `Item`, và phần tử CUỐI là một `Section` — «Chăm sóc & khiếu nại»
//  với hai mục con `/cham-soc` và `/khieu-nai`. MKT-3 bóc mọi phần tử như một cặp nên tới
//  phần tử cuối thì cả màn hình chết.
//
//  GỠ PHẲNG, chứ không bỏ `Section` đi: bỏ thì mất đúng hai mục ấy khỏi thanh — tức là lặp
//  lại đúng cái lỗi mà MKT-3 sinh ra để chữa. `Item` lấy nguyên, `Section` lấy các mục con,
//  nên thanh ngang vẫn liệt kê đủ MƯỜI HAI mục.
//
//  VÀ CHỈ NHẬN PHẦN TỬ NÀO THẬT SỰ LÀ MỘT MẢNG. Ngày mai bảng menu thêm một kiểu thứ ba thì
//  màn hình BỎ QUA nó chứ không nổ: thiếu một mục trên thanh thì còn thấy được bằng mắt,
//  còn màn trắng thì không ai làm gì được. Bài học của chính đợt này, ghi ngay tại chỗ.
const MUC_PHONG: [string, string][] = (() => {
  const nhom = (GROUPS as any[]).find((g) => g.key === "marketing");
  const ra: [string, string][] = [];
  for (const b of (((nhom || {}).blocks) || []) as any[]) {
    if (Array.isArray(b)) { ra.push(b as [string, string]); continue; }
    for (const m of (((b || {}).items) || []) as any[]) {
      if (Array.isArray(m)) ra.push(m as [string, string]);
    }
  }
  return ra;
})();

/** VH-41 (Chủ tịch duyệt bản xem trước 12/11/2026 22:17) — BÀN LÀM VIỆC MARKETING & PR NHƯ BÀN /xe.
 *  Bảy NHÓM nút lớn thay cho hàng 12 liên kết đi khỏi màn + 8 nút chức năng; mỗi nhóm có trang con
 *  MỞ TẠI CHỖ: `tab` là phần của chính màn này, `toi` là màn riêng của phòng nhúng vào khung (không
 *  sang CRM tổng), `ban` là trang chủ theo vai — Phó TGĐ / Chủ tịch / TGĐ thấy bàn Phó TGĐ, nhân viên
 *  thấy bàn nhân viên, vai khác (gd_kd, kế toán: không mở được hai bàn) thấy Tổng quan số. */
type ConMkt = { ten: string; tab?: string; sub?: string; toi?: string; ban?: true };
const NHOM_MKT: { ma: string; ten: string; khan?: true; con: ConMkt[] }[] = [
  { ma: "chu", ten: "Trang chủ", con: [{ ten: "Bàn làm việc của tôi", ban: true }] },
  { ma: "khach", ten: "Khách tiềm năng & Sales", con: [
    { ten: "Khách tiềm năng", tab: "khach" }, { ten: "Chuyển đổi & phối hợp Sales", toi: "/chuyen-doi-lead" },
    { ten: "Tỷ lệ chốt theo kỳ", tab: "chuyendoi" }] },
  { ma: "cd", ten: "Chiến dịch & ngân sách", con: [
    { ten: "Chiến dịch", tab: "chiendich", sub: "chiendich" }, { ten: "Ngân sách", tab: "chiendich", sub: "ngansach" },
    { ten: "Khai kênh & chạy đối chiếu", tab: "doisoat" }] },
  { ma: "nd", ten: "Nội dung & thương hiệu", con: [
    { ten: "Nội dung & thương hiệu", toi: "/noi-dung" }, { ten: "Hàng đợi duyệt nội dung", tab: "noidung" },
    { ten: "Báo chí, KOL & sự kiện", toi: "/bao-chi-kol" }] },
  // Nút ĐỎ riêng: cửa báo động phải thấy ngay lúc gấp (bài học 19/9/2026 ở Shell — đừng để sâu ba lớp).
  { ma: "kh", ten: "Khủng hoảng & PR", khan: true, con: [{ ten: "Khủng hoảng & phản ứng nhanh", tab: "thuonghieu" }] },
  { ma: "ds", ten: "Doanh thu & đối soát", con: [
    { ten: "Tổng quan số", tab: "tongquan" }, { ten: "Đóng góp doanh thu", toi: "/dong-gop-marketing" },
    { ten: "Đối soát dữ liệu", toi: "/doi-soat-marketing" }] },
  { ma: "cs", ten: "Chăm sóc & khiếu nại", con: [
    { ten: "Chăm sóc sau bán", toi: "/cham-soc" }, { ten: "Phản hồi & khiếu nại", toi: "/khieu-nai" }] },
];
/** Màn của phòng được mở TRONG khung của bàn; liên kết ra ngoài danh sách này bị chặn trong khung. */
const DUONG_MKT = ["/lich-xe-trong", "/ptgd-mkt", "/ban-mkt", "/noi-dung", "/bao-chi-kol", "/dong-gop-marketing", "/doi-soat-marketing",
  "/chuyen-doi-lead", "/cham-soc", "/khieu-nai", "/leads"];
const laMkt = (h: string) => DUONG_MKT.some((t) => h === t || h.startsWith(t + "/") || h.startsWith(t + "?"));
/** VH-43: tên trên thanh đầu bàn — theo bàn mà trang chủ mở cho vai ấy. */
const tenBan = (vai: string) => VAI_BAN_NV.includes(vai) ? "Bàn làm việc nhân viên Marketing"
  : VAI_BAN_PTGD.includes(vai) ? "Bàn làm việc P.TGĐ Marketing" : "Bàn làm việc Marketing & PR";
const banCuaVai = (vai: string) => VAI_BAN_NV.includes(vai) ? "/ban-mkt" : VAI_BAN_PTGD.includes(vai) ? "/ptgd-mkt" : "";

/** Một THẺ SỐ của Tổng quan. Bốn phần, và phần thứ tư không được bỏ:
 *      nhãn · số · số ấy đọc từ đâu · CỬA để đi tới chỗ sửa nó.
 *  Thẻ không có cửa là một con số người đọc không làm gì được với nó. */
function The({ nhan, so, nguon, cua, cuaTen, rong, canhBao }:
  { nhan: string; so: React.ReactNode; nguon: string; cua?: () => void; cuaTen?: string; rong?: boolean; canhBao?: boolean }) {
  return <div className={"the-ct" + (rong ? " rong" : "")}>
    <div className="the-nhan">{nhan}</div>
    <div className={"the-so" + (canhBao ? " do" : "")}>{so}</div>
    <div className="the-duoi">{nguon}</div>
    {cua && <div className="the-thieu">
      <button type="button" className="the-cua" style={{ background: "none", border: 0, padding: 0, cursor: "pointer" }}
        onClick={cua}>{cuaTen || "Mở cửa nhập"}</button>
    </div>}
  </div>;
}

function Marketing() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const role = user?.role || "";
  const lapDuoc = ["ptgd_mkt", "nv_mkt", "cntt"].includes(role);
  // Gương của hàng rào THẬT ở backend (`require_roles(*EDIT_ROLES, "tp_dh")` trên POST
  // /leads/match). Đây chỉ để KHÔNG hiện một cái nút bấm vào là bị từ chối — hàng rào vẫn nằm
  // ở phía sổ, không nằm ở đây.
  const doiSoatDuoc = ["nv_kd", "tn_kd", "tp_kd", "gd_kd", "nv_mkt", "ptgd_mkt", "cntt", "tgd", "tp_dh"].includes(role);

  // MKT-6 · 11/11/2026 — Đ1: MỞ MÀN VÀO TỔNG QUAN. Mặc định cũ là danh sách chiến
  // dịch, tức là người mở màn gặp ngay một bảng thay vì gặp tình hình của phòng.
  // `hienTab` vẫn đưa về "chiendich" khi một nhóm bị khoá — Tổng quan luôn mở được
  // nên nhánh ấy không bao giờ chạm vào dòng này.
  const [tab, setTab] = useState("tongquan");
  const [sub, setSub] = useState("chiendich");          // trong tab "chiendich": chiendich | ngansach
  // VH-41: nhóm đang mở và màn đang nhúng (null = nội dung của chính màn này theo `tab`).
  const [nhom, setNhom] = useState("chu");
  const homNay = useHomNay();
  /* VH-43 (Chủ tịch 13/11/2026): bấm chữ «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu là về trang tổng CRM — cùng cách /xe
     (VH-8): logo bên cạnh vẫn về trang chủ của bàn này. */
  useEffect(() => {
    const chu = document.querySelector("a.brand small") as HTMLElement | null;
    if (!chu) return;
    const ve = (e: Event) => { e.preventDefault(); e.stopPropagation(); window.location.assign("/"); };
    chu.title = "Về trang tổng CRM";
    chu.addEventListener("click", ve, true);
    return () => { chu.removeEventListener("click", ve, true); chu.removeAttribute("title"); };
  }, []);
  const [khung, setKhung] = useState<string | null>(null);
  const [con, setCon] = useState(0);
  const moCon = (ma: string, i: number) => {
    const g = NHOM_MKT.find((x) => x.ma === ma); const c = g?.con[i]; if (!g || !c) return;
    setNhom(ma); setCon(i);
    if (c.ban) { const b = banCuaVai(role); setKhung(b || null); if (!b) setTab("tongquan"); return; }
    if (c.toi) { setKhung(c.toi); return; }
    setKhung(null); if (c.tab) setTab(c.tab); if (c.sub) setSub(c.sub);
  };
  /** Mở theo `?tab=` (đường dẫn cũ, dấu trang, ô trên bàn Phó TGĐ): tìm nhóm chứa tab ấy. */
  const moTheoTab = (t: string) => {
    const k = t === "ngansach" ? "chiendich" : t;
    for (const g of NHOM_MKT) g.con.forEach((c, i) => {
      if (c.tab === k && (t !== "ngansach" || c.sub === "ngansach") && (t === "ngansach" || !c.sub || c.sub === "chiendich")) {
        setNhom(g.ma); setCon(i); setKhung(null);
      }
    });
  };
  /** Trang chủ theo vai: mở MỘT lần khi đã biết người đăng nhập, trừ khi đường dẫn đã chỉ sẵn một tab. */
  const daMo = useRef(false);
  const urlDau = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    if (daMo.current || !role) return;
    daMo.current = true;
    const b = banCuaVai(role); setKhung(b || null); if (!b) setTab("tongquan");
  }, [role]);
  /** Liên kết bấm trong khung: `/marketing?tab=…` đổi nhóm TẠI CHỖ (không lồng bàn trong bàn). */
  const ngoaiKhung = (h: string) => {
    if (!h.startsWith("/marketing")) return false;
    const t = new URLSearchParams(h.split("?")[1] || "").get("tab") || "tongquan";
    if (t === "ngansach") { setTab("chiendich"); setSub("ngansach"); } else setTab(t);
    moTheoTab(t);
    return true;
  };

  // ── chiến dịch & ngân sách (giữ nguyên từ bản trước, không sửa logic) ──
  const [meta, setMeta] = useState<any>({ muc_tieu: {}, kenh: {}, trang_thai: {}, mang: {} });
  const [ds, setDs] = useState<any[]>([]);
  const [sp, setSp] = useState<any[]>([]);
  const [nv, setNv] = useState<any[]>([]);
  const [chua, setChua] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [f, setF] = useState<any>({ ...RONG });
  const [hienForm, setHienForm] = useState(false);
  const [ns, setNs] = useState<any[]>([]);
  const [hm, setHm] = useState<any>({});
  const [fn, setFn] = useState<any>({ period: thang0(), target_leads: "", target_revenue: "", rationale: "", lines: [] as any[], nguon_tao: "nguoi", ai_ghi_chu: "" });
  const [hienNs, setHienNs] = useState(false);

  // ── khách tiềm năng ──
  const [lmeta, setLmeta] = useState<any>({ channels: [], status: {} });
  const [thang, setThang] = useState(thang0());
  const [kenh, setKenh] = useState(""); const [tt, setTt] = useState(""); const [q, setQ] = useState("");
  const [leads, setLeads] = useState<any>({ rows: [], counts: {} });

  // ── chuyển đổi ──
  const [repThang, setRepThang] = useState(thang0());
  const [rep, setRep] = useState<any>(null);

  // ── đối soát: cửa nhập thống kê kênh ──
  const [stats, setStats] = useState<any[]>([]);
  const [sThang, setSThang] = useState(thang0());
  const [sMoi, setSMoi] = useState<any>({ channel: "", leads: "", cost: "" });

  // ── thương hiệu ──
  const [th, setTh] = useState<any>({ rows: [], dem: {}, loai: {}, trang_thai_ds: {} });
  const [thLoai, setThLoai] = useState("");

  // ── hoạt động PR ──
  const [pr, setPr] = useState<any>({ rows: [], dem: {}, loai: {}, trang_thai_ds: {}, han_khung_hoang_gio: 0 });
  const [prKh, setPrKh] = useState(false);

  // ── cửa lọc tin khủng hoảng ──
  const [lk, setLk] = useState<any>({ rows: [], dem: {}, tu_do: [], nguong: 0, nguong_ky: 0, ngay: 7 });
  const [lkNgay, setLkNgay] = useState(7);
  const [lkRong, setLkRong] = useState(false);          // hạ ngưỡng để XEM LẠI, không đổi luật
  const [lkLyDo, setLkLyDo] = useState<any>({});
  const [lkDo, setLkDo] = useState<any>(null);

  // ── nội dung ──
  const [nd, setNd] = useState<any[]>([]);

  /** BỐN TAB ĐỌC DỮ LIỆU KHÁCH TỰ ẨN VỚI VAI KHÔNG MỞ ĐƯỢC SỔ LEAD (18/9/2026)
   *
   *  Bảng quyền thật nằm ở backend/app/services/access.py. Chép nó sang đây là dựng bản thứ hai của
   *  một bảng đã có — và bản thứ hai thì luôn là bản lạc hậu. Nên màn hình KHÔNG đọc vai trò để
   *  đoán: nó gọi thử `/leads/meta` và `/noi-dung/meta`, gọi được thì hiện tab, bị chặn thì ẩn.
   *
   *  ĐÂY KHÔNG PHẢI HÀNG RÀO. Hàng rào là hai lớp ở phía sổ (phạm vi ngoài suy từ MENU_ROLES, và
   *  require_roles trên từng tuyến). Ẩn tab chỉ để Kế toán — vai có /marketing mà không có /leads —
   *  mở không gian Marketing ra không gặp bốn tab đỏ mà không hiểu vì sao.
   *
   *  `null` = chưa biết. Hiện tab rồi giật mất còn khó chịu hơn là chờ nửa giây. */
  const [xemLead, setXemLead] = useState<boolean | null>(null);
  const [xemNoiDung, setXemNoiDung] = useState<boolean | null>(null);

  const load = useCallback(() => {
    api("/marketing/campaigns").then(setDs).catch((e) => toast(errMsg(e), true));
    api("/marketing/campaigns/lead-chua-gan").then(setChua).catch(() => {});
    api("/marketing/budgets").then(setNs).catch(() => {});
    api("/noi-dung").then((r) => setNd(Array.isArray(r) ? r : [])).catch(() => {});
  }, []); // eslint-disable-line

  useEffect(() => {
    api("/marketing/meta").then(setMeta).catch(() => {});
    api("/leads/meta").then((r) => { setLmeta(r); setXemLead(true); }).catch(() => setXemLead(false));
    api("/noi-dung/meta").then(() => setXemNoiDung(true)).catch(() => setXemNoiDung(false));
    api("/products").then((r) => setSp(Array.isArray(r) ? r : r.rows || [])).catch(() => {});
    api("/users").then((r) => setNv(Array.isArray(r) ? r : [])).catch(() => {});
    api("/marketing/budgets/hang-muc").then(setHm).catch(() => {});
    // VH-41: đọc `?tab=` của đường dẫn LÚC MỞ đúng một lần và giữ trong ref — hiệu ứng ghi đường dẫn bên dưới
    // có thể ghi đè `?tab=` trước khi `setTab` kịp áp (React chạy hai hiệu ứng trong cùng một nhịp).
    if (urlDau.current === undefined) urlDau.current = new URLSearchParams(window.location.search).get("tab");
    const url = urlDau.current;
    // Đường dẫn CŨ của menu vẫn phải mở đúng chỗ cũ – xem ghi chú "HAI ĐƯỜNG DẪN CŨ" ở đầu tệp.
    if (url === "ngansach") { setTab("chiendich"); setSub("ngansach"); }
    else if (url && TABS.some(([k]) => k === url)) setTab(url);
    // VH-41: có `?tab=` thì mở đúng nhóm chứa nó; không có thì trang chủ theo vai (effect dưới, chờ biết vai).
    if (url === "ngansach" || (url && TABS.some(([k]) => k === url))) { moTheoTab(url); daMo.current = true; }
    // MKT-2 · 09/11/2026 — `/phan-he/marketing?xem=muc-luc` nay chuyển hướng về đây mang
    // theo nguyên tham số. Đọc nó ra thành tab là để những dấu trang và tin nhắn đã gửi
    // nhau vẫn mở đúng chỗ người gửi muốn, thay vì rơi về tab Tổng quan rồi tự đi tìm.
    else if (new URLSearchParams(window.location.search).get("xem") === "muc-luc")
      setTab("muc-luc");
    load();
  }, [load]);

  /** MKT-6 · 11/11/2026 — Đ2: GHI NHÓM ĐANG MỞ VÀO ĐƯỜNG DẪN.
   *
   *  Màn này ĐỌC `?tab=` lúc tải từ lâu nhưng chưa bao giờ GHI lại, nên gửi đường dẫn
   *  cho nhau hay bấm tải lại là rơi về nhóm mặc định — người nhận không mở đúng chỗ
   *  người gửi đang đứng, mà cả hai đều không biết.
   *
   *  `replaceState` CHỨ KHÔNG `pushState`: đẩy vào lịch sử thì nút Lùi của trình duyệt
   *  phải bấm tám lần mới ra khỏi màn, và người dùng đọc đó là màn hình bị kẹt.
   *
   *  GHI "ngansach" KHI ĐANG Ở NGĂN ẤY, giữ đúng phép ánh xạ hai chiều mà đoạn đọc ở
   *  trên đã có: `?tab=ngansach` mở tab Chiến dịch với ngăn Ngân sách. Ghi trống một
   *  bên thì đường dẫn copy ra lại mở về ngăn Chiến dịch.
   */
  useEffect(() => {
    if (khung) return;   // VH-41: đang nhúng màn khác thì không ghi tab của màn này
    const ghi = (tab === "chiendich" && sub === "ngansach") ? "ngansach" : tab;
    const u = new URL(window.location.href);
    if (u.searchParams.get("tab") === ghi) return;
    u.searchParams.set("tab", ghi);
    window.history.replaceState(null, "", u.toString());
  }, [tab, sub, khung]);

  // Báo cáo chuyển đổi nuôi CẢ tab Tổng quan lẫn tab Chuyển đổi, nên nạp ngay từ đầu.
  useEffect(() => { api(`/leads/conversion?month=${repThang}`).then(setRep).catch(() => {}); }, [repThang]);
  // Nạp danh sách lead cho CẢ tab Khách tiềm năng lẫn thẻ "quá hạn xử lý" của Tổng quan — thẻ ấy
  // đọc `so_qua_han` do chính đường này trả về. Tab Thương hiệu và Ngân sách không cần, nên không nạp.
  useEffect(() => {
    if (tab !== "khach" && tab !== "tongquan") return;
    if (xemLead === false) return;
    api(`/leads?month=${thang}&channel=${encodeURIComponent(kenh)}&status=${tt}&q=${encodeURIComponent(q)}`)
      .then(setLeads).catch((e) => { if (tab === "khach") toast(errMsg(e), true); });
  }, [tab, thang, kenh, tt, q, xemLead, toast]);
  /** Ký một bộ nhận diện. Nút CHỈ hiện cho vai còn thiếu chữ ký – gương của hàng rào thật ở
   *  máy chủ (tham số `thuong_hieu_vai_ky`), không thay cho nó. Và cố ý KHÔNG hiện nút cho vai đã
   *  ký rồi: hai chữ ký phải là hai người bấm, không phải một người bấm hai lần. */
  const kyTh = async (id: number) => {
    try {
      const r = await api(`/marketing/thuong-hieu/${id}/ky`, { method: "POST" });
      toast(r.message);
      setTh(await api(`/marketing/thuong-hieu?loai=${encodeURIComponent(thLoai)}`));
    } catch (e) { toast(errMsg(e), true); }
  };

  /** Bấm PHÁT. Nút chỉ hiện cho P.TGĐ Marketing – gương của hàng rào thật ở máy chủ, không thay
   *  cho nó. Phát ngôn CHÍNH LÀ phản hồi với một vụ khủng hoảng, nên bấm nút này cũng dừng luôn
   *  đồng hồ hai giờ; không bắt người ta bấm thêm một nút nữa. */
  const prPhat = async (id: number) => {
    try { toast((await api(`/marketing/pr/${id}/phat`, { method: "POST" })).message); await napPr(); }
    catch (e) { toast(errMsg(e), true); }
  };
  /** Ghi rằng vụ khủng hoảng đã xử lý bằng đường khác (gọi điện, gặp trực tiếp). Không có cửa này
   *  thì những vụ ấy nằm mãi ở bảng quá hạn, và bảng quá hạn mất hết ý nghĩa. */
  const prPhanHoi = async (id: number) => {
    try { toast((await api(`/marketing/pr/${id}/phan-hoi`, { method: "POST" })).message); await napPr(); }
    catch (e) { toast(errMsg(e), true); }
  };
  const napPr = useCallback(async () => {
    setPr(await api(`/marketing/pr?chi_khung_hoang=${prKh}`));
  }, [prKh]);
  useEffect(() => { if (tab === "thuonghieu") napPr().catch((e) => toast(errMsg(e), true)); },
           [tab, napPr, toast]);

  /** Hàng đợi cảnh báo hộp thư. Bộ lọc chỉ XẾP HÀNG — nó không đặt "là khủng hoảng" và không bấm
   *  đồng hồ hai giờ. Ô tích ở nút "Lập dòng PR" mới làm việc đó, và người tích mới là người
   *  quyết. Nút hạ ngưỡng ở dưới là cách giữ lời hứa "không vứt tin nào đi". */
  const napLk = useCallback(async () => {
    setLk(await api(`/marketing/hop-thu-canh-bao?ngay=${lkNgay}${lkRong ? "&nguong=1" : ""}`));
  }, [lkNgay, lkRong]);
  useEffect(() => { if (tab === "thuonghieu") napLk().catch((e) => toast(errMsg(e), true)); },
           [tab, napLk, toast]);
  const lkBoQua = async (r: any) => {
    const mid = r.nguon_id;
    const ly_do = (lkLyDo[`${r.nguon}-${mid}`] || "").trim();
    if (!ly_do) { toast("Phải ghi lý do bỏ qua – hàng đợi chỉ sửa được khi biết nó sai ở đâu", true); return; }
    try { toast((await api(`/marketing/hop-thu-canh-bao/${r.nguon}/${r.nguon_id}/bo-qua`, { method: "POST", json: { ly_do } })).message); await napLk(); }
    catch (e) { toast(errMsg(e), true); }
  };
  const lkLapPr = async (r: any, kh: boolean) => {
    try {
      toast((await api(`/marketing/hop-thu-canh-bao/${r.nguon}/${r.nguon_id}/lap-pr`,
        { method: "POST", json: { la_khung_hoang: kh, loai: "khung_hoang" } })).message);
      await napLk(); await napPr();
    } catch (e) { toast(errMsg(e), true); }
  };
  const napLkDo = async () => {
    try { setLkDo(await api(`/marketing/hop-thu-canh-bao/do`)); }
    catch (e) { toast(errMsg(e), true); }
  };

  // Sổ nhận diện. Chỉ nạp khi mở tab – sổ này đọc từ bảng tài sản, không phải thứ cần sẵn ở
  // mọi màn hình.
  useEffect(() => {
    if (tab !== "thuonghieu") return;
    api(`/marketing/thuong-hieu?loai=${encodeURIComponent(thLoai)}`).then(setTh)
      .catch((e) => toast(errMsg(e), true));
  }, [tab, thLoai, toast]);
  useEffect(() => {
    if (tab !== "doisoat") return;
    api(`/leads/stats?month=${sThang}`).then((r) => setStats(Array.isArray(r) ? r : [])).catch(() => {});
  }, [tab, sThang]);

  const post = async (path: string, json?: any, method = "POST") => {
    try { const r = await api(path, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiKenh = (k: string) => setF({ ...f, channels: f.channels.includes(k) ? f.channels.filter((x: string) => x !== k) : [...f.channels, k] });
  const luu = () => post("/marketing/campaigns", {
    ...f, product_id: f.product_id ? Number(f.product_id) : null, owner_id: f.owner_id ? Number(f.owner_id) : null,
    budget: soTien(f.budget), target_leads: Number(f.target_leads) || 0,
    target_bookings: Number(f.target_bookings) || 0, to_date: f.to_date || null,
  }).then((r) => { if (r) { setF({ ...RONG }); setHienForm(false); } });

  const mau: Record<string, string> = { nhap: "grey", cho_duyet: "warn", dang_chay: "ok", tam_dung: "warn", ket_thuc: "grey", da_danh_gia: "ok" };

  const luuNs = () => {
    // TC-77 – mỗi dòng mang thêm chiến dịch. Rỗng vẫn hợp lệ: chi chung cả tháng là việc có
    // thật, ép gắn chiến dịch là ép người nhập chọn bừa một cái cho qua cửa.
    const lines = (fn.lines || []).filter((l: any) => Number(l.amount) > 0)
      .map((l: any) => ({ hang_muc: l.hang_muc, amount: Number(l.amount),
                          campaign_id: l.campaign_id ? Number(l.campaign_id) : null }));
    post("/marketing/budgets", { period: fn.period, target_leads: Number(fn.target_leads) || 0,
      target_revenue: soTien(fn.target_revenue), rationale: fn.rationale, lines,
      nguon_tao: fn.nguon_tao, ai_ghi_chu: fn.ai_ghi_chu })
      .then((r) => { if (r) { setFn({ ...fn, rationale: "", lines: [] }); setHienNs(false); } });
  };

  /** ĐỐI SOÁT CHẠY TRÊN TOÀN BỘ SỔ LEAD, KHÔNG GIỚI HẠN MỘT THÁNG.
   *
   *  `/leads/match` nhận tham số `months` để lọc theo THÁNG PHÁT SINH LEAD. Truyền tháng đang xem
   *  vào đó là sai hai lần: tháng đang xem là tháng TOUR KHỞI HÀNH (khác loại), và quy tắc đã ký
   *  `overview-v1` cần cả lead của các kỳ TRƯỚC được gắn booking thì tử số mới đúng. Lọc một tháng
   *  là tự tay làm tỷ lệ của các kỳ trước tụt xuống mà không ai biết vì sao. Nên: không truyền gì. */
  const chayDoiSoat = async () => {
    try {
      const r = await api("/leads/match", { method: "POST" });
      toast(`Đã gắn ${r.matched} lead với booking (soát ${r.leads} lead)`);
      api(`/leads/conversion?month=${repThang}`).then(setRep).catch(() => {});
      load();
    } catch (x) { toast(errMsg(x), true); }
  };
  const luuStat = () => {
    if (!sMoi.channel) return;
    post("/leads/stats", [{ lead_month: sThang, channel: sMoi.channel, leads: Number(sMoi.leads) || 0, cost: soTien(sMoi.cost) || 0 }])
      .then((r) => { if (r) { setSMoi({ channel: "", leads: "", cost: "" }); api(`/leads/stats?month=${sThang}`).then((x) => setStats(Array.isArray(x) ? x : [])).catch(() => {}); } });
  };

  /** Tab nào hiện được. Ba tab KHÔNG đụng sổ khách (Tổng quan, Ngân sách & chiến dịch, Thương hiệu)
   *  luôn hiện. Bốn tab còn lại chờ đo xong rồi mới quyết. */
  const hienTab = (k: string) => {
    if (k === "khach" || k === "chuyendoi" || k === "doisoat") return xemLead !== false;
    if (k === "noidung") return xemNoiDung !== false;
    return true;
  };
  // Đang đứng ở một tab vừa bị đo là không mở được thì đưa về Chiến dịch, đừng để màn hình trắng.
  useEffect(() => { if (!hienTab(tab)) setTab("chiendich"); }); // eslint-disable-line

  // ── số của Tổng quan, gộp từ các cửa đã có ──
  const nsKy = ns[0]?.bang || null;
  const dangChay = ds.filter((c) => c.status === "dang_chay").length;
  const ndChoDuyet = nd.filter((n) => ["cho_duyet", "cho_ky_2"].includes(n.status)).length;
  const lechLon = (rep?.by_channel_month || []).filter((a: any) => a.lech_khai_bao).length;

  return (<>{hop}
    {/* THANH CHỨC NĂNG — MKT-3 · 09/11/2026, khuôn lấy từ màn `/xe`. Thay cho thanh dọc đã
        ẩn: người của phòng vẫn đi được tới MỌI màn của chính phân hệ mình, nhưng không thấy
        phân hệ của phòng khác — đúng điều Chủ tịch chốt 08/11 cho trang riêng từng phòng.

        KHÔNG LỌC THEO QUYỀN Ở ĐÂY, cùng lẽ với `/xe`: hàng rào nằm ở máy chủ và ở chính màn
        hình đích. Giấu một mục đi thì người thiếu quyền không biết là mình thiếu quyền, và
        họ sẽ đi hỏi người khác thay vì xin quyền ở Quản trị hệ thống.

        LỐI RA PHẢI CÓ: ẩn thanh dọc là lấy mất đường sang phân hệ khác, nên «Trang tổng CRM»
        đứng cuối hàng. Thiếu nó thì màn này thành một ngõ cụt đẹp. */}
    {/* MKT-6 · 11/11/2026 — Đ4: HÀNG NÀY TỰ ẨN KHI ĐANG Ở MỤC LỤC.
        Chủ tịch dặn 10/11/2026: «các nút chức năng không được lặp lại trên cùng một màn
        hình — mỗi nút một chỗ». Mục lục liệt kê đúng mười hai mục này rồi, nên để thêm
        hàng liên kết lên trên nó là hai bảng nút cho cùng một việc. Làn R2 đã áp đúng
        luật ấy ở đợt PH-2 cùng ngày cho các trang phòng khác; màn này chưa được hưởng
        vì ở đây mục lục là một NHÓM chứ không phải một trang riêng. */}
    {/* VH-41 (Chủ tịch duyệt bản xem trước 12/11/2026 22:17): bàn làm việc như /xe — đầu bàn navy sáng,
        bảy nhóm nút lớn, trang con mở tại chỗ. Thay cho hàng 12 liên kết đi KHỎI màn (MKT-3) và tám nút
        chức năng (MKT-6): mỗi việc một nút, không nút nào lặp. Lối ra CRM tổng: chữ «HỆ THỐNG ĐIỀU HÀNH» trên thanh đầu. */}
    {/* VH-43 (Chủ tịch 13/11/2026): MỘT thanh đầu bàn — khuôn chung `.mh01-ban` như bàn Chủ tịch và bàn GĐ đội xe:
        tên bàn theo vai, ô «Hôm nay», nút «Lịch xe 90 ngày». Thanh đầu của bàn nhúng bên dưới bị giấu (`anDauBan`),
        nên không còn hai thanh «Bàn làm việc» chồng nhau. Lịch xe 90 ngày mở TẠI CHỖ trong khung, không rời bàn. */}
    <div className="mh01-ban" onClickCapture={(e) => {
      const a = (e.target as HTMLElement).closest("a[href]") as HTMLAnchorElement | null;
      const h = a?.getAttribute("href") || "";
      if (h.startsWith("/lich-xe-trong")) { e.preventDefault(); setNhom(""); setCon(0); setKhung(h); }
    }}>
      <h1 className="mh01-ban-ten">{tenBan(role)}</h1>
      <div className="mh01-ban-cum">
        <div className="mh01-ban-ngay"><span>Hôm nay</span>{homNay || "…"}</div>
        {VAI_NUT_LICH_90.includes(role) && <NutLich90 />}
      </div>
    </div>
    <nav className="mkt-nhom" aria-label="Nhóm nghiệp vụ Marketing">
      {NHOM_MKT.map((g) => (
        <button key={g.ma} type="button" className={g.khan ? "khan" : undefined} aria-pressed={nhom === g.ma}
          onClick={() => moCon(g.ma, 0)}>{g.ten}</button>))}
    </nav>
    {(() => { const g = NHOM_MKT.find((g) => g.ma === nhom) || NHOM_MKT[0]; return g.con.length > 1 && (
      <nav className="mkt-con" aria-label={`Trang của ${g.ten}`}>
        {g.con.map((c, i) => {
          const tat = !!c.tab && !hienTab(c.tab);
          return tat ? null : <button key={c.ten} type="button" aria-pressed={con === i} onClick={() => moCon(g.ma, i)}>{c.ten}</button>;
        })}
      </nav>); })()}
    {khung && <KhungNhung key={khung} toi={khung} ten={(NHOM_MKT.find((g) => g.ma === nhom) || NHOM_MKT[0]).con[con]?.ten || "Marketing"}
      cuaBan={laMkt} ngoai={ngoaiKhung} anDauBan />}
    {!khung && <>

    {/* ═══════════════ 8 · MỤC LỤC CHỨC NĂNG ═══════════════
        MKT-2 · 09/11/2026 — gộp từ `/phan-he/marketing`. Trang ấy không còn: bấm vào nó
        chuyển hướng về đây. Chủ tịch chốt cùng ngày — một phòng, một trang.

        HỆ QUẢ ĐÃ NÓI RA TRƯỚC KHI LÀM: mục lục cũ ai cũng mở được, màn này chỉ mở cho vai
        của phòng. Nên người ngoài phòng — ví dụ Giám đốc đội xe — từ nay không xem được
        mục lục Marketing nữa. Đó là một lần SIẾT có người quyết, không phải tác dụng phụ.

        KHÔNG gọi máy chủ ở tab này: mục lục đọc cây tĩnh `cay_phan_he.ts`. Luật ấy là ranh
        giới 09/9/2026 và hàng rào soi theo TỆP `MucLucPhanHe.tsx`, nên nó còn nguyên. */}
    {tab === "muc-luc" && <MucLucPhanHe khoa="marketing" khongChip />}

    {/* ═══════════════ 1 · TỔNG QUAN ═══════════════ */}
    {tab === "tongquan" && <>
      <div className="mh01-the">
        {xemLead === false && <The rong nhan="Số liệu khách tiềm năng" so="không mở"
             nguon="Vai trò của anh/chị không mở được sổ lead, nên bốn tab đọc dữ liệu khách đã tự ẩn. Đây là hàng rào ở phía sổ, không phải lỗi màn hình." />}
        {xemLead !== false && <>
        <The nhan={`Tỷ lệ chốt ${rep?.quy_tac_ty_le_chot || "đã ký"} · ${repThang}`}
             so={tyLe(rep?.total_current?.ty_le_chot_overview)}
             nguon={rep?.da_doi_chieu ? "Sổ lead ↔ booking, tính đến hôm nay. Còn tăng khi kỳ trước chốt muộn."
                                      : "Chưa chạy đối chiếu lead ↔ booking — đây là CHƯA XÁC ĐỊNH, không phải 0%."}
             cua={() => setTab(rep?.da_doi_chieu ? "chuyendoi" : "doisoat")}
             cuaTen={rep?.da_doi_chieu ? "Xem bảng chuyển đổi" : "Chạy đối chiếu"}
             rong={!rep?.da_doi_chieu} />
        <The nhan={`Số điện thoại phát sinh · ${repThang}`}
             so={rep?.total_current?.so_sdt ?? "—"}
             nguon="Đếm trên tập số điện thoại của sổ lead, không cộng dồn từng kênh."
             cua={() => setTab("khach")} cuaTen="Xem danh sách lead" />
        <The nhan={`Lead quá hạn xử lý${leads.han_xu_ly_gio ? ` · hạn ${leads.han_xu_ly_gio} giờ` : ""}`}
             so={leads.so_qua_han ?? "—"}
             nguon="Quá hạn đã ký mà chưa ai liên hệ và trạng thái vẫn là Mới. Hạn đếm từ lúc lead vào sổ; P.TGĐ Phan Ngọc Tuấn chốt 18/9/2026."
             cua={() => setTab("khach")} cuaTen="Mở danh sách lead"
             canhBao={!!leads.so_qua_han} />
        <The nhan="Lead chưa gắn chiến dịch"
             so={chua?.tong ?? "—"}
             nguon="Sổ lead, những dòng chưa có chiến dịch. Hệ thống không tự đoán."
             cua={() => setTab("doisoat")} cuaTen="Gán chiến dịch"
             canhBao={!!chua?.tong} />
        </>}
        <The nhan="Chiến dịch đang chạy"
             so={dangChay}
             nguon={`${ds.length} chiến dịch đã lập. Chi phí đọc từ đề nghị chi đã duyệt.`}
             cua={() => { setTab("chiendich"); setSub("chiendich"); }} cuaTen="Mở chiến dịch" />
        <The nhan={nsKy ? `Ngân sách kỳ ${ns[0].period} · còn lại` : "Ngân sách kỳ"}
             so={nsKy ? vnd(nsKy.tong_con_lai) : "chưa lập"}
             nguon={nsKy ? "Dự toán trừ đã chi và đang treo. Không có ô gõ tay cho phần đã chi."
                         : "Chưa có kỳ ngân sách nào — đây là việc còn thiếu, không phải số 0."}
             cua={() => { setTab("chiendich"); setSub("ngansach"); }} cuaTen="Mở ngân sách"
             rong={!nsKy} canhBao={!!nsKy && nsKy.tong_con_lai < 0} />
        <The nhan="Nội dung chờ duyệt"
             so={ndChoDuyet}
             nguon={`${nd.length} nội dung trong sổ. Bản có cam kết hoặc số liệu tài chính cần chữ ký thứ hai.`}
             cua={() => setTab("noidung")} cuaTen="Mở hàng đợi duyệt" />
      </div>

      {(rep?.canh_bao || []).map((c: string, i: number) =>
        <div className="panel mkt-canh" key={i}><b>⚠ {c}</b></div>)}

      <div className="panel mkt-thieu">
        <h2>Việc còn thiếu của phòng</h2>
        {/* Danh sách này ĐỌC TỪ SỐ THẬT, không phải một bảng kê viết cứng. Không có việc nào thì nói
            là không có, chứ không ẩn đi cho đẹp. */}
        <ul>
          {!!chua?.tong && <li><b>{chua.tong} lead chưa gắn chiến dịch</b> — chưa gán thì chi phí không quy được về chiến dịch nào.</li>}
          {!rep?.da_doi_chieu && <li><b>Chưa chạy đối chiếu lead ↔ booking</b> — tỷ lệ chốt theo quy tắc đã ký đang là <i>chưa xác định</i>.</li>}
          {!!lechLon && <li><b>{lechLon} dòng kênh × tháng lệch giữa khai báo và số đếm được</b> — tệp nguồn có thể chỉ có phần chi tiết của vài kênh.</li>}
          {!nsKy && <li><b>Chưa lập ngân sách kỳ</b> — không có dự toán thì không có chỗ để so phần đã chi.</li>}
          {!!ndChoDuyet && <li><b>{ndChoDuyet} nội dung đang chờ duyệt</b>.</li>}
          {/* MKT-6 · 11/11/2026 — Đ5: ĐÃ XOÁ dòng «Thương hiệu & PR chưa có sổ».
              Sai: sổ PR đã chạy — màn «Báo chí, KOL & sự kiện» có hàng đợi tin nghi ngờ
              và sổ hoạt động PR kèm đồng hồ hai giờ.
              Và nó là dòng DUY NHẤT viết cứng không điều kiện, nên cũng là dòng duy nhất
              phạm đúng câu chú thích đứng ngay trên danh sách này. Không thay bằng một
              dòng viết cứng khác: muốn có một dòng về PR thì phải đọc từ sổ PR trước. */}
        </ul>
      </div>
    </>}

    {/* ═══════════════ 2 · KHÁCH TIỀM NĂNG & SALES ═══════════════ */}
    {tab === "khach" && <>
      <p className="muted">Đây là <b>cửa nhìn</b> của Marketing vào sổ khách hàng do Kinh doanh giữ.
        Sửa hồ sơ, nhắn Zalo và nhập tệp lead nằm ở màn hình <a href="/leads?tab=leads">Khách hàng &amp;
        nguồn khách</a> — dựng thêm một biểu nhập thứ hai ở đây là hai đầu cho cùng một việc, và sớm
        muộn hai đầu nói khác nhau.</p>
      <div className="panel">
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "end" }}>
          <label>Tháng lead<input type="month" value={thang} onChange={(e) => setThang(e.target.value)} /></label>
          <label>Kênh<select value={kenh} onChange={(e) => setKenh(e.target.value)}>
            <option value="">— tất cả —</option>
            {(lmeta.channels || []).map((x: string) => <option key={x}>{x}</option>)}</select></label>
          <label>Trạng thái<select value={tt} onChange={(e) => setTt(e.target.value)}>
            <option value="">— tất cả —</option>
            {Object.entries(lmeta.status || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
          <label>Tìm<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="SĐT, tên, tour quan tâm" /></label>
        </div>
        <p className="muted">{Object.entries(leads.counts || {}).map(([k, v]: any) =>
          <span key={k} style={{ marginRight: 12 }}>{(lmeta.status || {})[k] || k}: <b>{v}</b></span>)}
          {leads.han_xu_ly_gio ? <span>Quá hạn {leads.han_xu_ly_gio} giờ: <b>{leads.so_qua_han ?? 0}</b></span> : null}</p>
        {/* Con số quá hạn đếm trên TOÀN bộ lọc, không phải trên trang đang hiện — nói ra để không ai
            đếm tay các dòng đỏ rồi tưởng bảng sai. */}
        <p className="muted">Số quá hạn đếm trên toàn bộ bộ lọc đang chọn, không chỉ những dòng hiện trên trang này.</p>
      </div>
      <div className="panel wrap"><table>
        <thead><tr><th>SĐT</th><th>Khách</th><th>Kênh</th><th>Tháng</th><th>Tour quan tâm</th>
          <th>Chiến dịch</th><th>Trạng thái</th><th>Hạn xử lý</th><th>Booking</th><th>Sale</th><th></th></tr></thead>
        <tbody>{(leads.rows || []).length ? leads.rows.map((l: any) => <tr key={l.id}>
          <td>{l.phone}</td><td>{l.name}</td><td>{l.channel}</td><td>{l.lead_month}</td>
          <td>{l.interest}</td><td className="muted">{l.campaign}</td>
          <td><Tag cls={l.status === "chot" ? "ok" : l.status === "mat" ? "" : "warn"}>{l.status_name}</Tag></td>
          {/* KHÔNG CÓ HẠN thì in dấu gạch, không in "đúng hạn". Lead không biết vào sổ lúc nào thì
              sổ không chứng minh được gì — và im lặng gán cho nó một kết luận là kết luận sai. */}
          <td>{l.han_xu_ly
            ? (l.qua_han ? <Tag cls="red">quá hạn</Tag> : <span className="muted">{fmtDT(l.han_xu_ly)}</span>)
            : <span className="muted">—</span>}</td>
          <td>{l.booking_code}{l.booking_tour && <div className="muted">{l.booking_tour}</div>}</td>
          <td>{l.sales_name}</td>
          <td><a className="the-cua" href="/leads?tab=leads">mở hồ sơ</a></td>
        </tr>) : <tr><td colSpan={11} className="muted">Chưa có lead nào khớp bộ lọc — bấm “mở hồ sơ” để sang màn hình Kinh doanh nhập tệp lead.</td></tr>}</tbody>
      </table></div>
    </>}

    {/* ═══════════════ 3 · CHUYỂN ĐỔI & DOANH THU ═══════════════ */}
    {tab === "chuyendoi" && <div className="panel wrap">
      <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
        <label>Tháng tour khởi hành<input type="month" value={repThang} onChange={(e) => setRepThang(e.target.value)} /></label>
        {rep && <span className="muted">Lead các tháng {(rep.lead_months || []).join(", ")}</span>}
      </div>
      {/* Bảng dùng CHUNG với màn hình Khách hàng & nguồn khách — một đầu, hai nơi gọi. */}
      <BaoCaoChuyenDoi rep={rep} />
    </div>}

    {/* ═══════════════ 4 · NGÂN SÁCH & CHIẾN DỊCH ═══════════════ */}
    {tab === "chiendich" && <>
      {/* VH-41: hai nút «Chiến dịch / Kế hoạch & ngân sách» đã là trang con của nhóm «Chiến dịch & ngân sách»
          trên thanh của bàn — để thêm ở đây là lặp nút trên một màn. */}

      {sub === "ngansach" && <>
        <p className="muted">Màn hình này chỉ giữ phần <b>dự toán</b>. Số <b>đã chi</b> đọc từ đề nghị chi đã duyệt — không có ô nào để gõ tay. Chi vượt phần còn lại của hạng mục sẽ tự bật cờ ngoài dự toán và cần hai chữ ký; hệ thống không chặn cứng việc chi, nhưng không cho chi âm thầm.</p>
        {lapDuoc && <button className="act" onClick={() => setHienNs(!hienNs)}>{hienNs ? "Đóng biểu mẫu" : "+ Lập ngân sách kỳ"}</button>}
        {hienNs && <div className="panel"><h2>Biểu mẫu ngân sách kỳ</h2>
          <div className="grid">
            <label>Kỳ *<input value={fn.period} onChange={(e) => setFn({ ...fn, period: e.target.value })} placeholder="2026-09 hoặc 2026-Q4" /></label>
            <label>Mục tiêu lead *<input type="number" value={fn.target_leads} onChange={(e) => setFn({ ...fn, target_leads: e.target.value })} /></label>
            <label>Mục tiêu doanh thu quy đổi<input type="number" value={fn.target_revenue} onChange={(e) => setFn({ ...fn, target_revenue: e.target.value })} /></label>
          </div>
          <b>Dự toán theo hạng mục *</b>
          {/* TC-77 · 23/9/2026 – trước đây khối này là một lưới CỐ ĐỊNH, mỗi hạng mục đúng một ô số.
              Nay mỗi dòng gắn thêm một chiến dịch, nên một hạng mục có thể xuất hiện nhiều lần:
              tháng 9 chi Facebook Ads 100 triệu cho chiến dịch A và 50 triệu cho chiến dịch B là
              hai dòng cùng hạng mục. Lưới cố định không diễn đạt được điều đó, nên nó thành danh
              sách dòng thêm được.
              Ô chiến dịch để TRỐNG vẫn hợp lệ – chi chung cả tháng là việc có thật. */}
          <div className="wrap"><table>
            <thead><tr><th>Hạng mục</th><th>Chiến dịch</th><th className="num">Số tiền</th><th></th></tr></thead>
            <tbody>{(fn.lines || []).map((l: any, i: number) => <tr key={i}>
              <td><select value={l.hang_muc || ""} onChange={(e) => { const d = [...fn.lines]; d[i] = { ...d[i], hang_muc: e.target.value }; setFn({ ...fn, lines: d }); }}>
                <option value="">— chọn hạng mục —</option>
                {Object.entries(hm).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></td>
              <td><select value={l.campaign_id || ""} onChange={(e) => { const d = [...fn.lines]; d[i] = { ...d[i], campaign_id: e.target.value }; setFn({ ...fn, lines: d }); }}>
                <option value="">— chi chung, không gắn chiến dịch —</option>
                {ds.map((c: any) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}</select></td>
              <td className="num"><input type="number" value={l.amount || ""} onChange={(e) => { const d = [...fn.lines]; d[i] = { ...d[i], amount: e.target.value }; setFn({ ...fn, lines: d }); }} /></td>
              <td><button className="act" onClick={() => setFn({ ...fn, lines: fn.lines.filter((_: any, j: number) => j !== i) })}>Bỏ</button></td>
            </tr>)}
            {!(fn.lines || []).length && <tr><td colSpan={4} className="muted">Chưa có dòng nào – bấm “Thêm dòng chi”.</td></tr>}
            </tbody></table></div>
          <button className="act" onClick={() => setFn({ ...fn, lines: [...(fn.lines || []), { hang_muc: "", campaign_id: "", amount: "" }] })}>+ Thêm dòng chi</button>
          <p className="muted">Tổng dự toán: <b>{vnd((fn.lines || []).reduce((s: number, l: any) => s + (Number(l.amount) || 0), 0))}</b> — tổng tự cộng, không có ô gõ tay.</p>
          <p className="muted">Gắn chiến dịch cho dòng chi thì màn hình <b>Đóng góp doanh thu của Marketing</b>
            mới tính được chiến dịch ấy tiêu thật bao nhiêu và thu về bao nhiêu. Để trống cũng chạy
            bình thường, phần ấy hiện riêng là “chi chưa gắn chiến dịch”.</p>
          <label>Căn cứ lập ngân sách *<textarea rows={2} style={{ width: "100%" }} value={fn.rationale}
            onChange={(e) => setFn({ ...fn, rationale: e.target.value })} placeholder="Vì sao con số này – kỳ sau còn đối chiếu lại được" /></label>
          <div className="panel">
            <label><input type="checkbox" checked={fn.nguon_tao === "ai"} onChange={(e) => setFn({ ...fn, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Đề xuất do trợ lý AI soạn</b></label>
            {fn.nguon_tao === "ai" && <label>Căn cứ đề xuất (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={fn.ai_ghi_chu} onChange={(e) => setFn({ ...fn, ai_ghi_chu: e.target.value })} /></label>}
          </div>
          <button className="act" disabled={!fn.rationale} onClick={luuNs}>Lưu ở trạng thái Nháp</button>
        </div>}

        {ns.map((b) => { const g = b.bang || {}; return <div className="panel" key={b.id}>
          <h2>Kỳ {b.period} · <Tag cls={b.status === "hieu_luc" ? "ok" : b.status === "cho_duyet" ? "warn" : "grey"}>{b.status_ten}</Tag>
            {b.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</h2>
          <div className="kpis">
            <div className="kpi"><b>{vnd(g.tong_du_toan)}</b><span>Dự toán</span></div>
            <div className="kpi"><b>{vnd(g.tong_da_chi)}</b><span>Đã chi</span></div>
            <div className="kpi"><b>{vnd(g.tong_treo)}</b><span>Đang treo (đã cam kết)</span></div>
            <div className="kpi"><b style={{ color: g.tong_con_lai < 0 ? "var(--vtos-danger)" : undefined }}>{vnd(g.tong_con_lai)}</b><span>Còn lại</span></div>
          </div>
          <div className="wrap"><table><thead><tr><th>Hạng mục</th><th className="num">Dự toán</th>
            <th className="num">Đã chi</th><th className="num">Đang treo</th>
            <th className="num">Còn lại</th></tr></thead><tbody>
            {(g.rows || []).map((r: any) => <tr key={r.hang_muc}>
              <td>{r.ten}</td><td className="num">{vnd(r.du_toan)}</td>
              <td className="num">{vnd(r.da_chi)}</td><td className="num">{vnd(r.dang_treo)}</td>
              <td className="num" style={{ color: r.vuot ? "var(--vtos-danger)" : undefined }}><b>{vnd(r.con_lai)}</b>{r.vuot && <Tag cls="red">vượt</Tag>}</td></tr>)}
            {g.chua_phan_muc && (g.chua_phan_muc.da_chi > 0 || g.chua_phan_muc.dang_treo > 0) && <tr>
              <td><i>Chi marketing chưa gán hạng mục</i></td><td className="num">—</td>
              <td className="num">{vnd(g.chua_phan_muc.da_chi)}</td>
              <td className="num">{vnd(g.chua_phan_muc.dang_treo)}</td>
              <td className="num"><Tag cls="warn">cần gán</Tag></td></tr>}
            {(g.ngoai_ngan_sach || []).map((x: any) => <tr key={x.hang_muc}>
              <td><i>{x.ten} — ngoài ngân sách kỳ</i></td><td className="num">—</td>
              <td className="num">{vnd(x.da_chi)}</td><td className="num">{vnd(x.dang_treo)}</td>
              <td className="num"><Tag cls="warn">ngoài</Tag></td></tr>)}
          </tbody></table></div>
          <p className="muted">Chi phí/lead kế hoạch <b>{vnd(g.chi_phi_lead_ke_hoach)}</b> · thực tế <b>{vnd(g.chi_phi_lead_thuc_te)}</b> ({g.so_lead} lead trong kỳ) · Mục tiêu {b.target_leads} lead</p>
          <p className="muted"><b>Căn cứ:</b> {b.rationale}</p>
          {b.ai_ghi_chu && <p className="muted"><b>Căn cứ AI:</b> {b.ai_ghi_chu}</p>}
          <p className="muted">Người lập {b.created_by}{b.approved_by && ` · Duyệt bởi ${b.approved_by}`}</p>
          {b.status === "nhap" && lapDuoc && <button className="act" onClick={() => post(`/marketing/budgets/${b.id}/trinh`)}>Trình duyệt</button>}
          {b.status === "cho_duyet" && ["tgd", "chutich"].includes(role) && <button className="act" onClick={() => post(`/marketing/budgets/${b.id}/duyet`)}>Duyệt ngân sách</button>}
        </div>; })}
        {!ns.length && <p className="muted">Chưa có ngân sách kỳ nào.</p>}
      </>}

      {sub === "chiendich" && <>
        <p className="muted">Chiến dịch là trục nối tiền – khách – doanh thu. Chi phí đọc từ đề nghị chi đã duyệt, lead đọc từ Nguồn khách, doanh thu đọc từ booking đã chốt — <b>không có ô nào để gõ tay ba con số đó</b>.</p>

        {lapDuoc && <button className="act" onClick={() => setHienForm(!hienForm)}>{hienForm ? "Đóng biểu mẫu" : "+ Lập chiến dịch mới"}</button>}

        {hienForm && <div className="panel">
          <h2>Biểu mẫu chiến dịch</h2>
          <div className="grid">
            <label>Tên chiến dịch *<input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="Tết 2026 – Miền Bắc" /></label>
            <label>Mục tiêu *<select value={f.objective} onChange={(e) => setF({ ...f, objective: e.target.value })}>
              {Object.entries(meta.muc_tieu).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Mảng kinh doanh *<select value={f.mang} onChange={(e) => setF({ ...f, mang: e.target.value })}>
              {Object.entries(meta.mang).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            <label>Sản phẩm / tuyến {f.objective === "ban_tour" && <b style={{ color: "var(--vtos-danger)" }}>*</b>}
              <select value={f.product_id} onChange={(e) => setF({ ...f, product_id: e.target.value })}>
                <option value="">— không gắn sản phẩm —</option>
                {sp.map((p: any) => <option key={p.id} value={p.id}>{p.code} · {p.name}</option>)}</select></label>
            <label>Từ ngày *<input type="date" value={f.from_date} onChange={(e) => setF({ ...f, from_date: e.target.value })} /></label>
            <label>Đến ngày<input type="date" value={f.to_date} onChange={(e) => setF({ ...f, to_date: e.target.value })} /></label>
            <label>Ngân sách duyệt (đ) *<input type="number" value={f.budget} onChange={(e) => setF({ ...f, budget: e.target.value })} /></label>
            <label>Chỉ tiêu lead *<input type="number" value={f.target_leads} onChange={(e) => setF({ ...f, target_leads: e.target.value })} /></label>
            <label>Chỉ tiêu booking<input type="number" value={f.target_bookings} onChange={(e) => setF({ ...f, target_bookings: e.target.value })} /></label>
            <label>Người phụ trách<select value={f.owner_id} onChange={(e) => setF({ ...f, owner_id: e.target.value })}>
              <option value="">— chọn —</option>{nv.map((x: any) => <option key={x.id} value={x.id}>{x.full_name}</option>)}</select></label>
          </div>
          <div style={{ margin: "8px 0" }}><b>Kênh triển khai *</b>{" "}
            {Object.entries(meta.kenh).map(([k, v]: any) => <button key={k} className={"act " + (f.channels.includes(k) ? "" : "grey")}
              style={{ margin: "4px 6px 0 0", fontSize: 13 }} onClick={() => doiKenh(k)}>{v}</button>)}</div>
          <label>Ghi chú<textarea rows={2} style={{ width: "100%" }} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
          <div className="panel">
            <label><input type="checkbox" checked={f.nguon_tao === "ai"} onChange={(e) => setF({ ...f, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Đề xuất do trợ lý AI soạn</b></label>
            <p className="muted" style={{ margin: "4px 0" }}>Bản do AI soạn luôn dừng ở <b>Nháp</b> và phải người có thẩm quyền xem lại rồi duyệt — AI đề xuất, người quyết.</p>
            {f.nguon_tao === "ai" && <label>Căn cứ đề xuất (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={f.ai_ghi_chu}
              onChange={(e) => setF({ ...f, ai_ghi_chu: e.target.value })} placeholder="Dựa trên 3 kỳ gần nhất: chi phí/lead kênh Zalo thấp hơn Facebook 32%…" /></label>}
          </div>
          <button className="act" disabled={!f.name || !f.channels.length} onClick={luu}>Lưu ở trạng thái Nháp</button>
        </div>}

        <h2>Danh sách chiến dịch</h2>
        <div className="panel wrap"><table><thead><tr>
          <th>Mã</th><th>Tên</th><th>Mục tiêu</th><th>Kênh</th><th>Thời gian</th>
          <th className="num">Ngân sách</th><th className="num">Đã chi</th>
          <th className="num">Lead</th><th className="num">Chốt</th>
          <th className="num">CP/lead</th><th>Trạng thái</th><th></th></tr></thead><tbody>
          {ds.map((c) => { const k = c.ket_qua || {}; return [
            <tr key={c.id}>
              <td><b>{c.code}</b>{c.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</td>
              <td>{c.name}{c.san_pham && <div className="muted">{c.san_pham}</div>}</td>
              <td>{c.objective_ten}</td><td className="muted">{c.kenh_ten.join(" · ")}</td>
              <td>{fmtD(c.from_date)}{c.to_date ? ` → ${fmtD(c.to_date)}` : " → nay"}</td>
              <td className="num">{vnd(c.budget)}</td>
              <td className="num" style={{ color: k.vuot_ngan_sach ? "var(--vtos-danger)" : undefined }}>{vnd(k.chi_phi)}{k.chi_phi_treo > 0 && <div className="muted">treo {vnd(k.chi_phi_treo)}</div>}</td>
              <td className="num">{k.so_lead}{c.target_leads > 0 && <div className="muted">/{c.target_leads}</div>}</td>
              <td className="num">{k.chuyen_doi}{k.so_lead > 0 && <div className="muted">{pct(k.ty_le_chuyen_doi)}</div>}</td>
              <td className="num">{k.chi_phi_moi_lead ? vnd(k.chi_phi_moi_lead) : "—"}</td>
              <td><Tag cls={mau[c.status] || "grey"}>{c.status_ten}</Tag></td>
              <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(mo === c.id ? null : c.id)}>{mo === c.id ? "Ẩn" : "Xem"}</button></td>
            </tr>,
            mo === c.id && <tr key={c.id + "d"}><td colSpan={12}>
              <div className="kpis">
                <div className="kpi"><b>{vnd(k.doanh_thu)}</b><span>Doanh thu quy về</span></div>
                <div className="kpi"><b>{k.hieu_qua ? k.hieu_qua.toFixed(2) + "×" : "—"}</b><span>Doanh thu / chi phí</span></div>
                <div className="kpi"><b>{k.chi_phi_moi_booking ? vnd(k.chi_phi_moi_booking) : "—"}</b><span>Chi phí / booking</span></div>
                <div className="kpi"><b style={{ color: k.con_lai_ngan_sach < 0 ? "var(--vtos-danger)" : undefined }}>{vnd(k.con_lai_ngan_sach)}</b><span>Còn lại ngân sách</span></div>
              </div>
              {c.nguon_tao === "ai" && c.ai_ghi_chu && <p><b>Căn cứ AI đề xuất:</b> {c.ai_ghi_chu}</p>}
              {c.evaluation && <p><b>Đánh giá kết thúc:</b> {c.evaluation}</p>}
              <p className="muted">Người lập {c.created_by}{c.approved_by && ` · Duyệt bởi ${c.approved_by}`}</p>
              {c.chuyen_duoc.map((s: string) => <button key={s} className="act" style={{ marginRight: 6 }} onClick={async () => {
                if (s === "da_danh_gia") { const dg = await nhap("Đánh giá kết thúc chiến dịch (bắt buộc):"); if (dg && dg.trim()) post(`/marketing/campaigns/${c.id}/chuyen-trang-thai`, { status: s, danh_gia: dg.trim() }); }
                else post(`/marketing/campaigns/${c.id}/chuyen-trang-thai`, { status: s });
              }}>→ {meta.trang_thai[s]}</button>)}
            </td></tr>,
          ]; })}
          {!ds.length && <tr><td colSpan={12} className="muted">Chưa có chiến dịch nào.</td></tr>}
        </tbody></table></div>
      </>}
    </>}

    {/* ═══════════════ 5 · ĐỐI SOÁT DỮ LIỆU ═══════════════ */}
    {tab === "doisoat" && <>
      <div className="panel">
        <h2>Đối soát lead ↔ booking</h2>
        <p className="muted">Đây là việc biến <b>chưa xác định</b> thành một con số. Chưa chạy lần nào
          thì tỷ lệ chốt theo quy tắc đã ký không có giá trị — và báo cáo sẽ nói đúng như vậy chứ
          không hiện 0%.</p>
        <p className="muted">Lần đối chiếu gần nhất:{" "}
          {rep?.da_doi_chieu ? <b>đã có dấu đối chiếu trên sổ lead</b> : <Tag cls="warn">chưa chạy lần nào</Tag>}</p>
        {doiSoatDuoc
          ? <button className="act" onClick={chayDoiSoat}>Chạy đối chiếu toàn bộ sổ lead</button>
          : <p className="muted">Vai trò của anh/chị không chạy được đối chiếu — việc này thuộc Marketing hoặc Trưởng phòng Điều hành.</p>}
      </div>

      <div className="panel">
        <h2>Cửa nhập thống kê kênh — mẫu số khai báo</h2>
        <p className="muted">Mẫu số của tỷ lệ chốt lấy <b>số khai báo</b> nếu có, và chỉ khi không có
          mới lấy số đếm được. Đây là cửa để khai con số ấy, kèm chi phí kênh. Không khai thì không
          sao — báo cáo sẽ ghi rõ mẫu số là “đếm được”.</p>
        <div style={{ display: "flex", gap: 8, alignItems: "end", flexWrap: "wrap" }}>
          <label>Tháng lead<input type="month" value={sThang} onChange={(e) => setSThang(e.target.value)} /></label>
        </div>
        <div className="wrap"><table>
          <thead><tr><th>Kênh</th><th className="num">Lead khai báo</th><th className="num">Chi phí kênh</th><th>Người khai</th></tr></thead>
          <tbody>
            {stats.length ? stats.map((s) => <tr key={s.id}>
              <td>{s.channel}</td><td className="num">{s.leads}</td><td className="num">{vnd(s.cost)}</td>
              <td className="muted">{s.updated_by}</td>
            </tr>) : <tr><td colSpan={4} className="muted">Chưa khai kênh nào cho tháng này.</td></tr>}
          </tbody>
        </table></div>
        {lapDuoc && <div className="grid">
          <label>Kênh<select value={sMoi.channel} onChange={(e) => setSMoi({ ...sMoi, channel: e.target.value })}>
            <option value="">— chọn kênh —</option>
            {(lmeta.channels || []).map((x: string) => <option key={x}>{x}</option>)}</select></label>
          <label>Lead khai báo<input type="number" value={sMoi.leads} onChange={(e) => setSMoi({ ...sMoi, leads: e.target.value })} /></label>
          <label>Chi phí kênh (đ)<input type="number" value={sMoi.cost} onChange={(e) => setSMoi({ ...sMoi, cost: e.target.value })} /></label>
        </div>}
        {lapDuoc && <button className="act" disabled={!sMoi.channel} onClick={luuStat}>Lưu dòng khai báo</button>}
      </div>

      <div className="panel">
        <h2>Lệch giữa khai báo và số đếm được</h2>
        <p className="muted">Lệch không phải lỗi — nhưng lệch lớn thường nghĩa là tệp nguồn chỉ có
          phần chi tiết của vài kênh. Hiện ra để người khai nhìn thấy, không san phẳng.</p>
        <div className="wrap"><table>
          <thead><tr><th>Kênh</th><th>Tháng lead</th><th className="num">Khai báo</th>
            <th className="num">SĐT đếm được</th><th className="num">Lệch</th></tr></thead>
          <tbody>{(rep?.by_channel_month || []).filter((a: any) => a.lech_khai_bao).length
            ? rep.by_channel_month.filter((a: any) => a.lech_khai_bao).map((a: any, i: number) => <tr key={i}>
              <td>{a.channel}</td><td>{a.lead_month}</td>
              <td className="num">{a.so_khai_bao}</td><td className="num">{a.so_sdt}</td>
              <td className="num"><Tag cls="warn">{a.lech_khai_bao > 0 ? "+" : ""}{a.lech_khai_bao}</Tag></td>
            </tr>)
            : <tr><td colSpan={5} className="muted">Không có dòng nào lệch trong các tháng đang xem.</td></tr>}
          </tbody>
        </table></div>
      </div>

      {/* MKT-8 · 11/11/2026 — lớp `mkt-luu-y` thay cho viền khai bằng thuộc tính nội dòng:
          `main .panel{border:0!important}` của MKT-6 đã xoá mất viền ấy. */}
      {chua && chua.tong > 0 && <div className="panel mkt-luu-y">
        <h2>{chua.tong} lead chưa gắn chiến dịch</h2>
        <p className="muted">Gom theo ô chữ chiến dịch cũ. Hệ thống không tự đoán — chọn một chiến dịch bên dưới rồi bấm gán.</p>
        <div className="wrap"><table><thead><tr><th>Ô chữ cũ</th><th className="num">Số lead</th><th>Gán vào</th></tr></thead><tbody>
          {chua.nhom.slice(0, 20).map((n: any) => <tr key={n.campaign_cu}>
            <td>{n.campaign_cu}</td><td className="num">{n.so_lead}</td>
            <td>{lapDuoc && <select defaultValue="" onChange={(e) => { if (e.target.value) post(`/marketing/campaigns/${e.target.value}/gan-lead`, { campaign_cu: n.campaign_cu === "(không ghi)" ? "" : n.campaign_cu }); }}>
              <option value="">— chọn chiến dịch —</option>{ds.map((c) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select>}</td></tr>)}
        </tbody></table></div>
      </div>}
    </>}

    {/* ═══════════════ 6 · NỘI DUNG & KÊNH ═══════════════ */}
    {tab === "noidung" && <>
      <p className="muted">Soạn bài, đính tệp và chuyển trạng thái nằm ở màn hình{" "}
        <a href="/noi-dung">Nội dung &amp; thương hiệu</a>. Ở đây là <b>hàng đợi</b> của phòng: cái gì
        đang chờ ai.</p>
      <div className="panel wrap"><table>
        <thead><tr><th>Mã</th><th>Tiêu đề</th><th>Loại</th><th>Chiến dịch</th><th>Kênh</th>
          <th>Ngày dự kiến</th><th>Người soạn</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>{nd.length ? nd.map((n) => <tr key={n.id}>
          <td><b>{n.code}</b>{n.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</td>
          <td>{n.title}</td><td>{n.loai_ten}</td><td className="muted">{n.chien_dich}</td>
          <td className="muted">{(n.kenh_ten || []).join(" · ")}</td>
          <td>{fmtD(n.ngay_du_kien)}</td><td>{n.nguoi_soan}</td>
          <td><Tag cls={n.status === "da_dang" ? "ok" : n.status === "go" ? "red" : ["cho_duyet", "cho_ky_2"].includes(n.status) ? "warn" : "grey"}>{n.status_ten}</Tag>
            {n.can_ky_2 && <div className="muted">cần chữ ký thứ hai</div>}</td>
          <td><a className="the-cua" href="/noi-dung">mở</a></td>
        </tr>) : <tr><td colSpan={9} className="muted">Chưa có nội dung nào — bấm “Nội dung &amp; thương hiệu” ở menu để soạn bài đầu tiên.</td></tr>}</tbody>
      </table></div>
    </>}

    {/* ═══════════════ 7 · THƯƠNG HIỆU & PR ═══════════════ */}
    {tab === "thuonghieu" && <>
      <div className="panel">
        <h2>Sổ tài sản thương hiệu</h2>
        <p className="muted">Chủ tịch chốt 18/9/2026: sổ này <b>dùng chung bảng tài sản cố định</b> của
          Kế toán chứ không dựng bảng riêng — một bộ nhận diện mua ngoài có hoá đơn đúng là TSCĐ vô
          hình, nó vốn thuộc về đó. Thẻ <b>đã khai nguyên giá</b> thì đồng thời nằm trong danh sách
          TSCĐ của Kế toán; thẻ chưa khai là nhận diện nội bộ tự tạo, chỉ Marketing thấy.</p>
        <p className="muted">Một bản mới chỉ có hiệu lực khi đủ <b>hai chữ ký: Chủ tịch và P.TGĐ
          Marketing</b>. Cửa nhập nằm ở màn hình Nạp dữ liệu — mục “Tài sản thương hiệu”.</p>
      </div>
      <div className="mh01-the">
        <The nhan="Bản đang dùng" so={th.dem?.dang_dung ?? 0} nguon="đủ hai chữ ký và đã tới ngày hiệu lực" />
        <The nhan="Đang chờ chữ ký" so={th.dem?.cho_chu_ky ?? 0} canhBao={(th.dem?.cho_chu_ky ?? 0) > 0}
             nguon="thiếu chữ ký của Chủ tịch hoặc P.TGĐ Marketing – chưa bản nào trong số này có hiệu lực" />
        <The nhan="Có trong sổ Kế toán" so={th.dem?.vao_so_ke_toan ?? 0}
             nguon="đã khai nguyên giá nên hiện trong danh sách TSCĐ như TSCĐ vô hình" />
        <The nhan="Tổng số thẻ nhận diện" so={th.dem?.tong ?? 0} nguon="cả sổ, mọi trạng thái" />
      </div>
      <div className="panel">
        <div className="hang">
          <label>Loại</label>
          <select value={thLoai} onChange={(e) => setThLoai(e.target.value)}>
            <option value="">– tất cả –</option>
            {Object.entries(th.loai || {}).map(([ma, ten]: any) => <option key={ma} value={ma}>{ten}</option>)}
          </select>
        </div>
        {(th.rows || []).length === 0
          ? <p className="muted">Sổ chưa có dòng nào. Nhập ở màn hình <b>Nạp dữ liệu</b> — mục “Tài sản
              thương hiệu”. Màn hình này KHÔNG tự sinh dòng mẫu: một sổ nhận diện có sẵn mấy dòng
              không ai nhập là một sổ không ai tin.</p>
          : <table className="bang">
            <thead><tr>
              <th>Mã</th><th>Loại</th><th>Tên</th><th>Phiên bản</th><th>Hiệu lực</th>
              <th>Đang dùng ở đâu</th><th>Chữ ký</th><th>Sổ Kế toán</th><th></th>
            </tr></thead>
            <tbody>
              {th.rows.map((r: any) => <tr key={r.id}>
                <td>{r.ma}</td>
                <td>{r.loai_ten}</td>
                <td>{r.ten}</td>
                <td>{r.phien_ban || <span className="muted">chưa ghi</span>}</td>
                <td>{r.hieu_luc_tu ? fmtD(r.hieu_luc_tu) : <span className="muted">chưa có</span>}
                    {r.hieu_luc_den ? ` → ${fmtD(r.hieu_luc_den)}` : ""}</td>
                <td>{r.noi_su_dung || <span className="muted">chưa ghi</span>}</td>
                <td>{r.con_thieu_chu_ky.length === 0
                      ? <Tag cls="ok">đủ hai chữ ký</Tag>
                      : <Tag cls="warn">còn thiếu: {r.con_thieu_chu_ky.join(", ")}</Tag>}</td>
                <td>{r.vao_so_ke_toan
                      ? <>{vnd(r.nguyen_gia)} <span className="muted">· có trong sổ</span></>
                      : <span className="muted">{r.vi_sao}</span>}</td>
                <td>{r.con_thieu_chu_ky.includes(role) &&
                      <button className="act teal" onClick={() => kyTh(r.id)}>Ký</button>}</td>
              </tr>)}
            </tbody>
          </table>}
      </div>
      <div className="panel">
        <h2>Sổ hoạt động PR &amp; truyền thông</h2>
        <p className="muted">Sổ ghi việc truyền thông <b>đã xảy ra</b> và ai chịu trách nhiệm —
          khác với màn hình Nội dung, chỗ giữ bản thảo trước khi đăng. Chủ tịch chốt 18/9/2026:
          người phát ngôn là <b>P.TGĐ Marketing</b>, và một vụ khủng hoảng phải có phản hồi trong
          <b> {pr.han_khung_hoang_gio} giờ</b> kể từ lúc việc được ghi vào sổ.</p>
        <p className="muted">Mốc ấy chạy theo <b>đồng hồ thật</b>: không trừ ngày nghỉ, không quy ra
          giờ hành chính — một việc ghi lúc 22h thứ Bảy thì 0h là quá hạn. Chỉ dòng có đánh dấu
          khủng hoảng mới có hạn; những dòng khác không nằm trong con số quá hạn.</p>
      </div>
      <div className="mh01-the">
        <The nhan="Quá hạn phản hồi" so={pr.dem?.qua_han ?? 0} canhBao={(pr.dem?.qua_han ?? 0) > 0}
             nguon={`vụ khủng hoảng chưa có phản hồi sau ${pr.han_khung_hoang_gio} giờ – đếm trên CẢ sổ, không phải trang đang xem`} />
        <The nhan="Vụ khủng hoảng" so={pr.dem?.khung_hoang ?? 0} nguon="dòng có đánh dấu khủng hoảng" />
        <The nhan="Chờ người phát ngôn" so={pr.dem?.cho_phat ?? 0} nguon="đã soạn xong, chờ P.TGĐ Marketing bấm phát" />
        <The nhan="Đã phát" so={pr.dem?.da_phat ?? 0} nguon="đã ra ngoài, có tên người phát ngôn" />
      </div>
      <div className="panel">
        <div className="hang">
          <label><input type="checkbox" checked={prKh} onChange={(e) => setPrKh(e.target.checked)} />
            {" "}Chỉ xem vụ khủng hoảng</label>
        </div>
        {(pr.rows || []).length === 0
          ? <p className="muted">Sổ chưa có dòng nào. Nhập ở màn hình <b>Nạp dữ liệu</b> — mục
              “Hoạt động PR &amp; truyền thông”.</p>
          : <table className="bang">
            <thead><tr>
              <th>Mã</th><th>Loại</th><th>Tiêu đề</th><th>Nơi đăng</th><th>Vào sổ</th>
              <th>Hạn phản hồi</th><th>Người phát ngôn</th><th>Trạng thái</th><th></th>
            </tr></thead>
            <tbody>
              {pr.rows.map((r: any) => <tr key={r.id}>
                <td>{r.ma}</td>
                <td>{r.loai_ten}{r.la_khung_hoang && <> <Tag cls="warn">khủng hoảng</Tag></>}</td>
                <td>{r.tieu_de}</td>
                <td>{r.noi_dang || <span className="muted">chưa ghi</span>}</td>
                <td>{fmtDT(r.ghi_nhan_luc)}</td>
                <td>{!r.la_khung_hoang ? <span className="muted">không có hạn</span>
                     : r.phan_hoi_luc ? <>đã phản hồi {fmtDT(r.phan_hoi_luc)}</>
                     : r.qua_han ? <Tag cls="err">QUÁ HẠN {fmtDT(r.han_phan_hoi)}</Tag>
                     : <>hạn {fmtDT(r.han_phan_hoi)}</>}</td>
                <td>{r.nguoi_phat_ngon || <span className="muted">chưa phát</span>}</td>
                <td>{r.trang_thai_ten}</td>
                <td>
                  {r.trang_thai !== "da_phat" && role === "ptgd_mkt" &&
                    <button className="act teal" onClick={() => prPhat(r.id)}>Phát</button>}
                  {r.la_khung_hoang && !r.phan_hoi_luc && lapDuoc &&
                    <> <button className="act grey" onClick={() => prPhanHoi(r.id)}>Đã phản hồi</button></>}
                </td>
              </tr>)}
            </tbody>
          </table>}
      </div>
      <div className="panel">
        <h2>Hàng đợi cảnh báo hộp thư</h2>
        <p className="muted">Bộ lọc đọc <b>hai nguồn</b>: tin nhắn riêng (Messenger / Zalo OA / chat web)
          và <b>bình luận công khai dưới bài đăng Fanpage</b>, rồi
          <b> xếp lên đầu</b> những tin đáng đọc trước. Nó <b>không</b> tự đánh dấu khủng hoảng và
          <b> không</b> tự bấm đồng hồ {pr.han_khung_hoang_gio} giờ — đồng hồ chạy đúng lúc người
          trực tích ô “là khủng hoảng” ở nút Lập dòng PR.</p>
        <p className="muted">Bốn dấu hiệu cộng điểm: <b>từ đỏ</b> (+2), <b>công khai</b> (+1),
          <b> dốc</b> – nhiều tin liên tiếp trên cùng hội thoại, hoặc nhiều bình luận dồn vào cùng
          một bài đăng (+1), <b>quá hạn trả lời</b> (+1). Ngưỡng đang ký
          là <b>{lk.nguong_ky}</b>. Danh sách từ đỏ sửa ở màn hình Tham số, không phải bằng bản nâng cấp.</p>
      </div>
      <div className="mh01-the">
        <The nhan="Chờ người xem" so={lk.dem?.cho_xem ?? 0} canhBao={(lk.dem?.cho_xem ?? 0) > 0}
             nguon={`tin đạt ngưỡng trong ${lk.ngay} ngày gần nhất, chưa ai kết luận`} />
        <The nhan="Bình luận công khai" so={lk.dem?.cong_khai ?? 0} canhBao={(lk.dem?.cong_khai ?? 0) > 0}
             nguon="bình luận dưới bài đăng Fanpage – người ngoài đọc được ngay, nên nó được cộng điểm và đứng trên tin nhắn riêng" />
        <The nhan="Có từ đỏ" so={lk.dem?.co_tu_do ?? 0} nguon="tin chứa ít nhất một từ trong danh sách đã ký" />
        <The nhan="Bắt đúng" so={lkDo ? lkDo.bat_dung : "—"} nguon="hàng đợi nêu, người xác nhận là khủng hoảng"
             cua={napLkDo} cuaTen="Đo bộ lọc" />
        <The nhan="Bỏ sót" so={lkDo ? lkDo.bo_sot : "—"} canhBao={!!lkDo && lkDo.bo_sot > 0}
             nguon="vụ khủng hoảng có tin nguồn mà chấm lại vẫn dưới ngưỡng – con số duy nhất thật sự quan trọng, mục tiêu 0"
             cua={napLkDo} cuaTen="Đo bộ lọc" />
      </div>
      <div className="panel">
        <div className="hang">
          <label>Nhìn lại{" "}
            <select value={lkNgay} onChange={(e) => setLkNgay(Number(e.target.value))}>
              <option value={1}>1 ngày</option><option value={7}>7 ngày</option>
              <option value={30}>30 ngày</option>
            </select>
          </label>{" "}
          <label><input type="checkbox" checked={lkRong} onChange={(e) => setLkRong(e.target.checked)} />
            {" "}Hạ ngưỡng xuống 1 để xem lại tin bị xếp sau</label>
        </div>
        {lkRong && <p className="muted">Đang XEM LẠI ở ngưỡng 1. Đây chỉ là cách nhìn của một lần
          xem — tham số đã ký vẫn là {lk.nguong_ky}.</p>}
        {/* Chạm trần thì NÓI RA. Một hàng đợi thiếu dòng mà im lặng tệ hơn hẳn một hàng đợi chậm:
            người trực đóng màn hình với cảm giác đã nhìn hết, trong khi phần chưa nhìn mới là
            phần có thể đang chứa vụ thật. */}
        {lk.cat_bot && <p className="muted" style={{ color: "var(--vtos-danger)" }}>Đang nhìn <b>một phần</b>: khoảng thời gian này có
          nhiều hơn {lk.tran_dong} tin nên hàng đợi chỉ chấm {lk.tran_dong} tin gần nhất. Thu hẹp
          số ngày lại để nhìn đủ.</p>}
        {(lk.rows || []).length === 0
          ? <p className="muted">Không có tin nào đạt ngưỡng trong {lk.ngay} ngày gần nhất.</p>
          : <table className="bang">
            <thead><tr>
              <th>Điểm</th><th>Lúc</th><th>Kênh</th><th>Khách</th><th>Trích tin</th>
              <th>Vì sao được nêu</th><th></th>
            </tr></thead>
            <tbody>
              {lk.rows.map((r: any) => <tr key={`${r.nguon}-${r.nguon_id}`}>
                <td>{r.co_tu_do ? <Tag cls="err">{r.diem}</Tag> : <Tag cls="warn">{r.diem}</Tag>}</td>
                <td>{r.luc}</td>
                <td>
                  {r.nguon === "binh_luan" ? <Tag cls="err">công khai</Tag> : <Tag>riêng</Tag>}{" "}
                  {r.kenh}
                  {r.da_xoa && <> <Tag cls="warn">đã xoá</Tag></>}
                  {r.da_sua && <> <Tag>đã sửa</Tag></>}
                </td>
                <td>{r.khach}</td>
                <td style={{ maxWidth: 420 }}>
                  {r.trich}
                  {r.link && <> <a href={r.link} target="_blank" rel="noreferrer">mở</a></>}
                </td>
                <td>{(r.ly_do || []).map((l: string, i: number) => <div key={i}>{l}</div>)}</td>
                <td>
                  {r.ket_luan
                    ? <span className="muted">{r.ket_luan === "lap_pr" ? "đã lập dòng PR" : "đã bỏ qua"}
                        {r.xu_ly_boi ? ` – ${r.xu_ly_boi}` : ""}</span>
                    : lapDuoc && <>
                      <button className="act teal" onClick={() => lkLapPr(r, true)}>Lập dòng PR – là khủng hoảng</button>{" "}
                      <button className="act" onClick={() => lkLapPr(r, false)}>Lập dòng PR – chưa phải</button>
                      <div style={{ marginTop: 4 }}>
                        <input placeholder="lý do bỏ qua (bắt buộc)" value={lkLyDo[`${r.nguon}-${r.nguon_id}`] || ""}
                               onChange={(e) => setLkLyDo({ ...lkLyDo, [`${r.nguon}-${r.nguon_id}`]: e.target.value })} />{" "}
                        <button className="act grey" onClick={() => lkBoQua(r)}>Bỏ qua</button>
                      </div>
                    </>}
                </td>
              </tr>)}
            </tbody>
          </table>}
        {lkDo && <p className="muted">Đo bộ lọc: bắt đúng <b>{lkDo.bat_dung}</b> · báo nhầm{" "}
          <b>{lkDo.bao_nham}</b> · bỏ sót <b>{lkDo.bo_sot}</b> · không có tin nguồn để đối chiếu{" "}
          <b>{lkDo.khong_co_tin_nguon}</b>. {lkDo.ghi_chu}</p>}
      </div>
      {/* MKT-8 · 11/11/2026 — xem chú thích của lớp `mkt-luu-y` trong thẻ style cuối tệp. */}
      <div className="panel mkt-luu-y">
        <h2>Còn thiếu</h2>
        <div className="mh01-the">
          <The rong nhan="Ai trực ngoài giờ, báo về đâu" so="chưa ký"
               nguon="Đồng hồ 2 giờ chạy theo đồng hồ thật, kể cả 22h thứ Bảy. Chưa có ca trực và đường báo thì hàng đợi này không ai mở lúc nửa đêm." />
          <The rong nhan="Theo dõi nhắc tên thương hiệu" so="chưa có"
               nguon="Cần một cửa nhập hoặc một mối nối với dịch vụ đo bên ngoài. Không có cửa thì con số này không thể có, kể cả ước lượng." />
        </div>
      </div>
    </>}
    </>}
  </>);
}
// MKT-3 · 09/11/2026 — `khongThanhBen`: Chủ tịch chốt «bỏ màn hình dọc giống bên đội xe».
// Màn `/xe` đã làm đúng thế từ 08/11, và lý do giống nhau: đây là trang RIÊNG của một phòng,
// không phải một chỗ đứng để nhìn sang phòng khác. Thanh chức năng ngang ở trên thay chỗ nó.
/* MKT-6 · 11/11/2026 — BẢNG MÀU CỦA RIÊNG MÀN NÀY, chỉ sống khi `/marketing` đang mở.
   Đúng nếp màn `/xe` đã đặt ra: không thêm một lớp nào vào `globals.css` hay `Shell.tsx`,
   vì nhiều làn cùng giữ hai tệp ấy. Mã màu lấy NGUYÊN từ khối `:root` của chính màn `/xe`
   trong `globals.css` — không thêm một mã màu mới nào vào hệ thống. */
const MAU = <style>{`
/* MKT-7 · 11/11/2026 — THÂN TRANG RỘNG RA CHO BẰNG THANH ĐẦU.
   Đo trên bản thật: nội dung dừng ở khoảng 950px trong khi thanh đầu trải hết màn, nên
   nửa phải màn hình trống trơn. Không phải MKT-6 gây ra — nó có từ đợt MKT-3 ngày
   09/11/2026, hôm ẩn thanh dọc bằng khongThanhBen mà không nới main: chiều rộng cũ
   là chiều rộng cho một trang CÒN thanh dọc, và thanh dọc thì không còn.
   LẤY NGUYÊN CON SỐ 1440 CỦA MÀN /xe, không tự chọn một số khác: hai màn của hai phòng
   cạnh nhau phải rộng bằng nhau, chứ không phải mỗi màn một khổ. */
main{max-width:1440px!important;margin:0 auto!important}
body,.shell{background:#eaf0f7!important}
:root{--mkt-b1:0 1px 2px #12305414,0 4px 12px #1230541a;
  --mkt-nhan:#2c5fa2;--mkt-dam:#183c69;--mkt-vien:#e1e7ef}
main .panel{background:#fff;border:0!important;border-radius:16px!important;
  box-shadow:var(--mkt-b1)!important}
main h1{color:var(--mkt-dam)}

/* MKT-8 11/11/2026 TRA LAI MAU DO CHO SO CANH BAO.
   globals.css co .the-so.do mau danger kem chu thich cua ban ve V1.2: do chi nhan phan
   qua han hoac thieu dieu kien, khong to do ca con so tong. MKT-6 viet
   .mh01-the .the-so mau navy, CUNG do uu tien 0-2-0, va the style cua man nap sau
   globals.css nen no thang. Bay con so tren khap man mat mau do: so qua han, lead chua
   gan chien dich, cho chu ky, qua han phan hoi, cho nguoi xem, binh luan cong khai.
   Khai 0-3-0 o day de manh hon ca hai luat tren. Khong dung !important: do uu tien la
   du, va mot dau !important them vao la mot cho nua cho nguoi sau phai go ra.
   Mau do lay cua man /xe chu khong lay --vtos-danger: man nay la nen SANG, the trang,
   con danger cua ban toi la hong nhat, tren trang doc khong ra. */
.mh01-the .the-so.do{color:#b72f45}

/* KHUNG LUU Y. Hai khung khai vien vang bang thuoc tinh noi dong, va border 0 !important
   o tren xoa mat vien ay. Thay bang nen vang nhat va mot vach doc ben trai. KHONG dung
   lai bang vang dac cua canh bao may chu: bang ay danh cho mot cau ngan, con hai khung
   nay co bang va nut ben trong, to vang het ca khung thi chu kho doc. */
main .panel.mkt-luu-y{background:#fdf6e7!important;
  box-shadow:inset 5px 0 0 #a66a00,var(--mkt-b1)!important}

/* HÀNG CHỨC NĂNG — khuôn .xe-nhom. Điểm nhấn của màn nằm Ở NÚT, không ở gạch chân: tám nhóm
   là tám nút navy đặc, nút đang mở navy đậm có vòng sáng. Dính trên cùng như /xe, để cuộn
   xuống giữa một bảng dài vẫn đổi nhóm được mà không phải cuộn ngược lên. */
/* MKT-7 · 11/11/2026 — DÍNH Ở ĐÁY THANH ĐẦU, KHÔNG DÍNH Ở ĐỈNH MÀN.
   Đo trên bản thật ngay sau khi MKT-6 gộp: cuộn xuống thì hàng chức năng trùm lên nửa
   trái thanh đầu, che mất ô logo và chữ HỆ THỐNG ĐIỀU HÀNH.
   MKT-6 chép khuôn .xe-nhom-dinh của màn /xe kể cả top:0, mà nếp của kho không phải
   thế: chú thích của đợt LOGO-1 cùng ngày ghi rõ nav.tabs và aside.side đều dính ở
   top: var(--top-h). Biến ấy là chiều cao THẬT của thanh đầu, đã tính cả ô logo, đệm
   và viền đáy — nên dùng nó thì ngày thanh đầu cao lên, hàng này tụt theo đúng chừng ấy.
   Màn /xe đang sai y hệt. Không sửa tệp của làn khác; đã báo sang làn giữ màn ấy. */
.mkt-chuc{position:sticky;top:var(--top-h);z-index:5;background:#eaf0f7;padding:6px 0 4px;margin-bottom:10px;
  display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}
.mkt-chuc button{display:inline-flex;align-items:center;justify-content:center;gap:8px;margin:0;
  font:inherit;font-size:13.5px;font-weight:600;color:#fff;background:var(--mkt-nhan);border:0;
  border-radius:10px;min-height:46px;padding:8px 12px;cursor:pointer;line-height:1.2;
  text-align:center;box-shadow:0 2px 6px #2c5fa230;transition:background .15s,box-shadow .15s}
.mkt-chuc button:hover{background:#3a6fb5}
.mkt-chuc button[aria-pressed=true]{background:var(--mkt-dam);box-shadow:0 0 0 3px #9fc0ec}
.mkt-chuc button:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
@media(max-width:980px){.mkt-chuc{grid-template-columns:repeat(2,minmax(0,1fr))}}

/* Mười hai màn riêng của phòng: nhạt hơn hàng chức năng một bậc — chúng dẫn ĐI KHỎI màn này,
   còn hàng chức năng đổi nội dung ngay tại chỗ. Hai việc khác nhau thì không cùng một sức nặng. */
.mkt-man{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.mkt-man a{font-size:13.5px;border:1px solid var(--mkt-vien);background:#fff;color:#1b2d44;
  border-radius:8px;padding:6px 12px;text-decoration:none;margin:0}
.mkt-man a:hover{background:var(--mkt-nhan);border-color:var(--mkt-nhan);color:#fff}
.mkt-ra{display:flex;margin:0 0 10px}
.mkt-ra a{margin-left:auto;color:var(--mkt-nhan);font-weight:600;font-size:13.5px}

/* VH-43 — chữ «HỆ THỐNG ĐIỀU HÀNH» bấm được (về trang tổng CRM), khuôn của /xe. */
a.brand small{cursor:pointer;border-radius:6px;padding:2px 6px;transition:background .15s}
a.brand small:hover{background:#ffffff26;text-decoration:underline}

/* VH-41 — ĐẦU BÀN + BẢY NHÓM + TRANG CON, khuôn của /xe (navy sáng như thanh đầu bàn VH-30). */
.mkt-nhom{position:sticky;top:var(--top-h);z-index:5;background:#eaf0f7;padding:6px 0 4px;margin-bottom:8px;
  display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:9px}
.mkt-nhom button{margin:0;font:inherit;font-size:13.5px;font-weight:700;color:#fff;background:var(--mkt-nhan);border:0;
  border-radius:10px;min-height:46px;padding:8px 10px;cursor:pointer;line-height:1.2;text-align:center;box-shadow:0 2px 6px #2c5fa230}
.mkt-nhom button:hover{background:#3a6fb5}
.mkt-nhom button[aria-pressed=true]{background:var(--mkt-dam);box-shadow:0 0 0 3px #9fc0ec}
.mkt-nhom button.khan{background:#a8243f}.mkt-nhom button.khan[aria-pressed=true]{background:#7d1530;box-shadow:0 0 0 3px #f3b3c2}
.mkt-nhom button:focus-visible,.mkt-con button:focus-visible{outline:3px solid #719ee1;outline-offset:2px}
@media(max-width:1100px){.mkt-nhom{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:560px){.mkt-nhom{grid-template-columns:repeat(2,minmax(0,1fr))}}
.mkt-con{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.mkt-con button{margin:0;font:inherit;font-size:13.5px;font-weight:600;border:1px solid var(--mkt-vien);background:#fff;color:#1b2d44;
  border-radius:9px;padding:6px 12px;cursor:pointer}
.mkt-con button[aria-pressed=true]{border-color:var(--mkt-nhan);color:var(--mkt-nhan);box-shadow:inset 0 -2px 0 var(--mkt-nhan)}

/* BẢY THẺ — giữ nguyên bộ khung .the-ct của bản vẽ, chỉ đổi nền và bóng cho khớp /xe. */
.mh01-the .the-ct{background:#fff;border:0;border-radius:14px;box-shadow:var(--mkt-b1);
  padding:14px 16px 12px}
.mh01-the .the-ct.rong{background:transparent;box-shadow:none;border:1px dashed var(--mkt-vien)}
.mh01-the .the-so{color:var(--mkt-nhan)}
.mh01-the .the-cua{color:var(--mkt-nhan);border-bottom-color:var(--mkt-nhan)}

/* MKT-8 11/11/2026 CUA CUA THE DONG HANG O DAY, dung nhu ban ve de xuat.
   Ban ve ve ba o mot hang co cua thang hang nhau va cach phan chu nguon bang mot vach
   ngan. Ban chay thi cua bam ngay duoi doan chu nguon, nen ba cua cao thap khac nhau
   theo do dai doan chu -- do duoc 105 / 119 / 133 o hang dau cua Tong quan, lech nhau
   28 diem. Mat phai di tim cua cua tung the mot thay vi luot mot duong ngang.
   globals.css da dat san .the-ct la mot khung flex doc, nen chi can day phan cua xuong
   day bang margin-top:auto. Khai o 0-3-0 de manh hon .the-thieu cua globals. */
.mh01-the .the-ct .the-thieu{margin-top:auto;padding-top:9px;
  border-top:1px solid var(--mkt-vien)}

/* CẢNH BÁO CỦA MÁY CHỦ — khuôn băng vàng .xe-n90. Cùng một dữ liệu rep.canh_bao, chỉ nổi
   hơn: hôm nay nó là một khung viền vàng nằm lẫn giữa các khung trắng khác. */
main .panel.mkt-canh{background:linear-gradient(135deg,#ffd76a 0%,#ffb627 55%,#ff9a1f 100%)!important;
  box-shadow:0 0 0 3px #ffe7a8,0 6px 22px #ff9f1f55!important;color:#3b2300;
  border-radius:14px!important;padding:13px 18px}
main .panel.mkt-canh b{font-size:15px}

/* VIỆC CÒN THIẾU — đánh số bằng CSS, không đụng một dòng JSX nào của danh sách. Thứ tự ở đây
   là thứ tự thật của danh sách, không phải một bảng xếp hạng: dữ liệu KHÔNG có trường mức độ,
   nên không tô đỏ tô cam dòng nào. Bịa ra một mức là nói với người đọc một điều mình không biết. */
.mkt-thieu ul{list-style:none;padding:0;margin:0;counter-reset:mktv}
.mkt-thieu li{counter-increment:mktv;display:block;position:relative;background:#fff;
  border:1px solid var(--mkt-vien);border-radius:12px;margin:0 0 9px;padding:11px 14px 11px 78px}
.mkt-thieu li::before{content:"VIỆC " counter(mktv,decimal-leading-zero);position:absolute;
  left:14px;top:12px;font-family:var(--vtos-font-mono);font-size:11px;letter-spacing:.09em;
  color:#6b7d92;font-weight:700}
@media(max-width:560px){.mkt-thieu li{padding:30px 14px 11px 14px}}
`}</style>;

export default function Page() { return <Shell khongThanhBen>{MAU}<Marketing /></Shell>; }
