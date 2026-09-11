"use client";
import { useEffect, useState, useRef, createContext, useContext, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getUser, clearSession, type User } from "@/lib/api";
import ChonDonVi from "@/components/ChonDonVi";

/** Mục v1.1 §I.2 có tên nhưng CHƯA có trang. TC-2 yêu cầu ẩn chức năng "sắp có", nên chúng không vào
 *  menu – nhưng cũng không bị xoá khỏi mã, vì lộ trình còn nợ phải có chỗ đọc được. Phép thử test_menu
 *  đọc chính danh sách này để canh rằng một mục đã dựng xong thì phải RỜI khỏi đây và có đường dẫn
 *  thật – không được ở cả hai trạng thái cùng lúc.
 *
 *  Đây KHÔNG phải CHUA_CO_TRANG của cổng P11: cổng ấy nói về mục đã KHAI QUYỀN mà chưa có trang, và
 *  đòi ngày dự kiến. Sáu mục dưới đây chưa khai quyền, chưa có trang, nên chúng không thuộc cổng đó. */
export const CHUA_XAY = [
  "Việc của tôi", "Chỉ đạo & giao việc", "Ngân sách", "Phòng ban",
  "Hiệu quả đơn vị", "Hồ sơ pháp lý & thuế", "Văn bản", "Nhật ký kỹ thuật",
];

type Item = [string, string];
type Section = { label: string; items: Item[] };
type Block = Item | Section;
/** `icon` phục vụ trạng thái THU của menu (v1.1 §I.2: rộng 224–240px, thu còn 56–64px). Khi thu thì
 *  chỉ còn biểu tượng, và §I.2 đòi "biểu tượng phải có chú thích" – nhãn nhóm đi vào title và
 *  aria-label chứ không mất. Một hàng biểu tượng không chú thích là một hàng phải đoán. */
type Group = { key: string; label: string; icon: string; blocks: Block[] };

/** BẢY NHÓM – tên chính thức theo v1.1 §I.2 "Menu trái rút gọn", bản Chủ tịch duyệt 11/9/2026.
 *  Tối đa hai cấp, bỏ số thứ tự, nhóm Quản trị đặt cuối, ẩn mục chưa có trang.
 *
 *  NGUYÊN TẮC XẾP: v1.1 liệt kê mục con theo CHỨC NĂNG NGHIỆP VỤ, không theo đường dẫn. Ở đây chỉ
 *  GOM 53 đường dẫn đang có trong MENU_ROLES vào bảy nhóm ấy – KHÔNG thêm mục mới. Khai một mục trỏ
 *  tới trang chưa tồn tại là cổng P11 đỏ ngay, và người dùng thì gặp một đường dẫn hỏng.
 *
 *  `blocks` giữ ĐÚNG THỨ TỰ của v1.1: một phần tử là một mục (mảng hai phần) hoặc một mục con có
 *  nhóm nhỏ bên trong (đối tượng có label + items). Nếu tách làm hai trường items và sections thì
 *  phải vẽ hết mục rồi mới tới nhóm nhỏ, và thứ tự trong tài liệu không giữ được.
 *
 *  Ba chỗ em tự quyết vì v1.1 không nói, đã ghi rõ để anh lật lại được:
 *    · "Cảnh báo nghiệp vụ", "Ngoại lệ cần xử lý", "Kiểm soát (robot)" vào Quản trị. Chúng là ba
 *      màn hình giám sát, không thuộc sáu mục con v1.1 nêu cho nhóm ấy.
 *    · "Quyết toán" của nhóm Tài chính hiểu là KẾT SỔ KỲ. Quyết toán tour dùng chung trang /tours
 *      với Chuyến, nên để một lối vào ở Vận hành thay vì hai mục cùng trỏ một trang.
 *    · "Khách hàng" và "Nguồn khách" của v1.1 cùng trỏ /leads; gộp làm một mục để không có hai nhãn
 *      khác nhau mở ra đúng một màn hình.
 */
export const GROUPS: Group[] = [
  // "Việc của tôi" và "Chỉ đạo & giao việc" chưa có trang (xem CHUA_XAY). "Việc của tôi" vẫn tới
  // được bằng neo trên thanh ngang, nên không mất lối đi.
  { key: "tongquan", label: "Tổng quan", icon: "🏠", blocks: [
    ["Bảng điều hành", "/"],
  ] },

  { key: "khachhang", label: "Khách hàng & Kinh doanh", icon: "🤝", blocks: [
    ["Hộp thư", "/inbox"],
    ["Khách hàng & nguồn khách", "/leads?tab=leads"],
    // Kinh doanh tách làm hai phòng (chỉ đạo 07/9/2026). Mảng nằm ở TOUR chứ không ở booking, và
    // được nhận theo HỢP của hai quy tắc: loại chuyến là đoàn, HOẶC mã tour bắt đầu bằng MICE. Đo
    // 07/9: 115/115 tour có chữ MICE đều là tour đoàn, nên hôm nay hai quy tắc trùng nhau – lấy hợp
    // để mai kia có ai nhập lệch thì tour vẫn không rơi khỏi màn hình của phòng mình.
    // Gộp hai phòng vào MỘT NHÓM không được làm mất việc tách mảng ấy: mỗi phòng vẫn mở đúng
    // ?mang= của mình, không cùng trỏ một danh sách rồi để người dùng tự lọc.
    { label: "Lẻ", items: [
      ["Tour lẻ", "/tours?mang=le"], ["Yêu cầu & booking", "/requests?mang=le"],
      ["Booking & bảo lưu", "/bookings?mang=le"], ["Dịch vụ lẻ", "/non-package"],
      ["Giá & chính sách bán", "/bang-gia"], ["Báo giá", "/bao-gia?mang=kd_le"],
      ["Báo cáo bán hàng", "/sales-reports?mang=le"]] },
    { label: "MICE", items: [
      ["Tour đoàn", "/tours?mang=doan"], ["Yêu cầu & booking", "/requests?mang=doan"],
      ["Booking & bảo lưu", "/bookings?mang=doan"], ["Báo giá đoàn", "/bao-gia?mang=kd_doan"],
      ["Hợp đồng", "/hop-dong-khach"], ["Báo cáo bán hàng", "/sales-reports?mang=doan"]] },
    { label: "Marketing", items: [
      ["Kế hoạch & ngân sách", "/marketing?tab=ngansach"], ["Chiến dịch", "/marketing"],
      ["Nội dung & thương hiệu", "/noi-dung"]] },
    { label: "Chăm sóc & khiếu nại", items: [
      ["Chăm sóc sau bán", "/cham-soc"], ["Phản hồi & khiếu nại", "/khieu-nai"]] },
  ] },

  { key: "vanhanh", label: "Vận hành", icon: "🧭", blocks: [
    ["Sản phẩm tour", "/products"],
    ["Yêu cầu chờ xử lý", "/requests"],
    ["Chuyến & quyết toán", "/tours"],
    ["Sự cố tour", "/su-co-tour"],
    // Lãi lỗ tour đứng NGAY SAU Chuyến vì đó là thứ tự thật của việc: nhập xong dòng chi phí quyết
    // toán thì mới có giá vốn, có giá vốn mới có lãi lỗ. Đặt trước thì người dùng gặp bảng lãi lỗ
    // rỗng trước khi gặp việc phải làm để nó có số.
    ["Lãi lỗ theo tour", "/lai-lo-tour"],
    { label: "Dịch vụ & NCC", items: [
      ["Nhà cung cấp & đặt dịch vụ", "/nha-cung-cap"], ["Hồ sơ visa", "/visa"]] },
    // Xe và hướng dẫn viên tách khỏi Điều hành thành đơn vị riêng (chỉ đạo 07/9/2026). Xe nội bộ
    // thuộc pháp nhân Công ty TNHH Vận tải Vietrip, còn hướng dẫn viên hưởng lương ở công ty mẹ.
    { label: "Xe & tài xế", items: [
      // Hồ sơ đội xe theo đặc tả "Quản lý vận hành xe Vietrip" v1.3: mã xe cố định, lịch sử biển,
      // giấy tờ có hạn và điều kiện khai thác. Màn hình /ops?tab=fleet cũ giữ nguyên cho phần bảng
      // giá và lệnh điều xe.
      ["Hồ sơ xe & điều kiện khai thác", "/doi-xe"], ["Bảng giá & lệnh", "/ops?tab=fleet"],
      ["Lệnh điều xe", "/lenh-dieu-xe"], ["Chi phí & hiệu quả", "/hieu-qua-doi-xe"],
      ["Lãi lỗ đội xe", "/lai-lo-doi-xe"], ["Việc của tài xế & HDV", "/xe-hdv"]] },
    { label: "Hướng dẫn viên", items: [
      ["Phòng Hướng dẫn", "/huong-dan"], ["HDV & phân chuyến (cũ)", "/ops?tab=guides"]] },
  ] },

  { key: "taichinh", label: "Tài chính", icon: "💰", blocks: [
    ["Thu & đối soát", "/collections"],
    ["Chi & thanh toán", "/expenses"],
    ["Công nợ", "/cong-no"],
    ["Bảo lưu & hoàn tiền", "/bookings"],
    ["Dòng tiền", "/finance?tab=forecast"],
    ["Vay & đầu tư", "/finance?tab=contracts"],
    ["Tài khoản ngân hàng", "/bank-accounts"],
    { label: "Sổ & kỳ kế toán", items: [
      ["Sổ kế toán", "/accounting?tab=journal"], ["Hóa đơn & thuế", "/accounting?tab=invoices"],
      // Kết sổ đứng NGAY TRƯỚC Khóa kỳ vì đó là thứ tự thật của việc: đưa sao kê vào sổ, kết chuyển
      // bốn bước, rồi mới khóa. Xếp ngược lại thì người dùng gặp nút khóa trước khi gặp việc phải làm.
      ["Kết sổ kỳ", "/ket-so"], ["Khóa kỳ", "/accounting?tab=periods"],
      ["Quy ước hạch toán", "/hach-toan"], ["Hồ sơ kiểm toán", "/ho-so-kiem-toan"]] },
  ] },

  { key: "nhansu", label: "Nhân sự & Nội bộ", icon: "👥", blocks: [
    ["Hồ sơ nhân sự", "/hr?tab=employees"],
    ["Hợp đồng lao động", "/hop-dong-lao-dong"],
    ["Lương, thưởng & hoa hồng", "/hr?tab=payroll"],
    ["Đánh giá & sự vụ", "/hr?tab=incidents"],
    ["Báo cáo công việc", "/reports"],
    ["Chính sách & quy trình", "/params"],
    ["Tài sản & mua sắm", "/tai-san"],
  ] },

  // Báo cáo tự động theo phòng (09/9/2026): Chủ tịch và TGĐ mở bản toàn công ty ở đây, trưởng phòng
  // mở bản của phòng mình ở CÙNG một đường dẫn – máy chủ cắt theo vai trò. Một đường dẫn cho mọi
  // cấp, không phải mỗi phòng một mục menu.
  //
  // "Kinh doanh" ở đây KHÔNG kèm ?mang=: hai phòng vào báo cáo của mình qua menu nhóm Khách hàng &
  // Kinh doanh. Nếu chỉ có hai lối đó thì không còn đường nào tới con số HỢP NHẤT.
  { key: "baocao", label: "Báo cáo", icon: "📊", blocks: [
    ["Điều hành", "/bao-cao"],
    ["Kinh doanh", "/sales-reports"],
    ["Marketing", "/leads?tab=report"],
    ["Tài chính", "/accounting?tab=bctc"],
    ["Báo cáo quản trị", "/robot-reports"],
  ] },

  // ĐẶT CUỐI theo v1.1 §I.2.
  { key: "quantri", label: "Quản trị", icon: "⚙️", blocks: [
    ["Tổ chức & đơn vị", "/companies"],
    { label: "Quyền", items: [
      ["Tài khoản & phân quyền", "/access"], ["Vị trí AI & quyền hạn", "/ai-roles"]] },
    { label: "Tích hợp", items: [
      ["Đồng bộ Vietrip", "/vietrip"], ["Kết nối MISA và các kênh", "/accounting?tab=misa"],
      ["Đọc chứng từ ảnh", "/doc-chung-tu"], ["Tệp & hình ảnh", "/tep"]] },
    ["Tự động hóa", "/tu-dong-hoa"],
    { label: "Chuẩn hóa dữ liệu", items: [
      ["Nạp dữ liệu", "/nap-du-lieu"],
      // Bàn quyết cột tiền K1/K2. Kế toán là người quyết một cột có phải tiền hay không (chốt 08/9),
      // nên mục này phải nằm ở chỗ Kế toán mở được – Quản trị mở cho cả Kế toán.
      ["Rà soát cột tiền", "/ra-soat-cot-tien"]] },
    // Ba màn hình giám sát. v1.1 không xếp chúng vào mục con nào; để cùng Nhật ký vì cùng một việc:
    // nhìn lại hệ thống đã làm gì và chỗ nào lệch.
    { label: "Kiểm soát & nhật ký", items: [
      ["Cảnh báo nghiệp vụ", "/alerts"], ["Ngoại lệ cần xử lý", "/ngoai-le"],
      ["Kiểm soát (robot)", "/kiem-soat"], ["Nhật ký nghiệp vụ", "/audit"]] },
  ] },
];

/** Ba mục của CHÍNH người đăng nhập – nằm trên thanh ngang, không thuộc phòng ban nào. Lọc theo
 *  hidden_menus vẫn áp dụng: vai trò không phải nộp báo cáo ngày thì mục đó tự rụng (đính chính
 *  08/9 – bộ mẫu báo cáo ngày chỉ có bảy phòng văn phòng, tài xế và HDV không nộp). Hai mục còn lại
 *  không bao giờ rụng vì chúng nằm trong MAN_HINH_KHONG_DUOC_AN.
 *
 *  Hai tệp phép thử cắt khối GROUPS ra để đọc bằng biểu thức chính quy (test_menu.py và
 *  test_man_hinh_co_cua_nhap.py). Cả hai lấy `export const CA_NHAN` ngay dưới đây làm MỐC KẾT THÚC.
 *  Trước 11/9/2026 chúng bám vào hai thứ khác nhau, và đều là thứ tình cờ đứng sau bảng: chuỗi
 *  "/** Vai trò" và tên hằng "const ROADMAP_ROLES". Bỏ ROADMAP_ROLES là một tệp phép thử vỡ ngay,
 *  báo ValueError không nói gì về nguyên nhân. Mốc mới là MÃ THẬT chứ không phải chú thích: bộ đọc
 *  của tệp kia xoá hết chú thích trước khi tìm mốc. */
export const CA_NHAN: Item[] = [
  ["Báo cáo công việc của tôi", "/reports"],
  ["Phiếu lương của tôi", "/phieu-luong"],
  ["Đổi mật khẩu", "/doi-mat-khau"],
];

const base = (href: string) => href.split("?")[0];
const isOn = (href: string, path: string) => { const b = base(href); return b === "/" ? path === "/" : path.startsWith(b); };
const laMuc = (b: Block): b is Item => Array.isArray(b);

type Toast = { msg: string; err?: boolean } | null;

/** `datChuaLuu` là sổ ghi "màn hình này còn dữ liệu chưa lưu", dùng cho TC-1: đổi đơn vị đang xem
 *  giữa chừng một biểu đang gõ dở là mất việc người ta vừa làm, mà mất im lặng.
 *
 *  Mỗi màn hình có biểu nhập gọi `datChuaLuu(true)` khi người dùng bắt đầu sửa và `datChuaLuu(false)`
 *  sau khi lưu xong. Màn hình chưa gọi thì coi như không có gì để mất – đúng với màn hình chỉ đọc,
 *  và KHÔNG chặn nhầm người dùng ở những chỗ không cần chặn. */
const Ctx = createContext<{
  user: User | null;
  toast: (m: string, err?: boolean) => void;
  datChuaLuu: (co: boolean) => void;
}>({ user: null, toast: () => {}, datChuaLuu: () => {} });
export const useShell = () => useContext(Ctx);

const KHOA_MENU = "vtos_menu_mo";
const KHOA_THU = "vtos_menu_thu";

export default function Shell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [t, setT] = useState<Toast>(null);
  const [open, setOpen] = useState<string[]>([]);      // nhóm đang bung
  const [side, setSide] = useState(false);             // màn hình nhỏ: mở/đóng thanh dọc
  const [menuToi, setMenuToi] = useState(false);       // menu cá nhân trên thanh ngang
  const [thu, setThu] = useState(false);               // thanh dọc thu còn một cột biểu tượng
  const [alerts, setAlerts] = useState(0);
  const path = usePathname();
  const router = useRouter();

  useEffect(() => {
    const u = getUser(); if (!u) { router.replace("/login"); return; }
    setUser(u); setReady(true);
    // Tài khoản còn mật khẩu tạm: đưa thẳng tới màn hình đổi mật khẩu. Máy chủ đã chặn mọi đường dẫn
    // khác, nên nếu không chuyển hướng ở đây thì người dùng chỉ thấy một loạt lỗi 403 mà không hiểu.
    if (u.must_change_password && path !== "/doi-mat-khau") { router.replace("/doi-mat-khau"); return; }
    // Nhớ trạng thái nhóm đang bung THEO NGƯỜI DÙNG. Khoá gắn tên đăng nhập vì một máy dùng chung
    // (máy quầy, máy điều hành) thì trạng thái của người trước không được đè lên người sau.
    try {
      const luu = localStorage.getItem(`${KHOA_MENU}_${u.username}`);
      if (luu) setOpen(JSON.parse(luu));
      setThu(localStorage.getItem(`${KHOA_THU}_${u.username}`) === "1");
    } catch { /* máy chặn localStorage thì mở mặc định – không phải lỗi */ }
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    // làm mới quyền (menu ẩn/hiện) từ máy chủ mỗi lần mở – phòng khi ma trận phân quyền đổi sau khi đăng nhập
    fetch("/api/v1/auth/me", { headers: h }).then((r) => r.ok ? r.json() : null).then((m) => {
      if (!m) return;
      localStorage.setItem("vtos_user", JSON.stringify(m)); setUser(m);
      if (m.must_change_password && path !== "/doi-mat-khau") router.replace("/doi-mat-khau");
    }).catch(() => {});
    fetch("/api/v1/alerts", { headers: h }).then((r) => r.ok ? r.json() : null).then((a) => { if (Array.isArray(a)) setAlerts(a.length); else if (a?.rows) setAlerts(a.tong ?? a.rows.length); }).catch(() => {});
  }, [router, path]);

  const toast = useCallback((msg: string, err?: boolean) => { setT({ msg, err }); setTimeout(() => setT(null), err ? 6500 : 4000); }, []);

  // Dùng ref chứ không dùng state: cờ này chỉ được ĐỌC lúc người dùng bấm đổi đơn vị, không có gì
  // phải vẽ lại theo nó. Để vào state thì mỗi lần gõ một chữ trong biểu là vẽ lại cả khung.
  const chuaLuu = useRef(false);
  const datChuaLuu = useCallback((co: boolean) => { chuaLuu.current = co; }, []);

  const doiNhom = useCallback((k: string) => {
    setOpen((o) => {
      const moi = o.includes(k) ? o.filter((x) => x !== k) : [...o, k];
      try { if (user) localStorage.setItem(`${KHOA_MENU}_${user.username}`, JSON.stringify(moi)); } catch { /* bỏ qua */ }
      return moi;
    });
  }, [user]);

  /** Thu / bung thanh dọc. §I.2 đòi nhớ trạng thái THEO TỪNG NGƯỜI DÙNG, nên khoá gắn tên đăng nhập
   *  y như trạng thái nhóm đang mở. */
  const doiThu = useCallback(() => {
    setThu((t2) => {
      const moi2 = !t2;
      try { if (user) localStorage.setItem(`${KHOA_THU}_${user.username}`, moi2 ? "1" : "0"); } catch { /* bỏ qua */ }
      return moi2;
    });
  }, [user]);

  /** Lọc theo quyền, giữ nguyên thứ tự và hai cấp. Mục con rỗng thì bỏ mục con; nhóm rỗng thì bỏ
   *  nhóm – không để lại nhãn nhóm mở ra không có gì bên trong. */
  const groups = useMemo(() => {
    const hid = user?.hidden_menus || [];
    const duoc = (h: string) => !hid.includes(base(h));
    return GROUPS.map((g) => {
      const blocks = g.blocks
        .map((b): Block | null => {
          if (laMuc(b)) return duoc(b[1]) ? b : null;
          const items = b.items.filter(([, h]) => duoc(h));
          return items.length ? { ...b, items } : null;
        })
        .filter((b): b is Block => b !== null);
      const dem = blocks.reduce((n, b) => n + (laMuc(b) ? 1 : b.items.length), 0);
      return { ...g, blocks, dem };
    }).filter((g) => g.dem > 0);
  }, [user]);

  const caNhan = useMemo(() => {
    const hid = user?.hidden_menus || [];
    return CA_NHAN.filter(([, h]) => !hid.includes(base(h)));
  }, [user]);

  // nhóm chứa trang hiện tại luôn được bung ("mở sẵn nhóm đang dùng" – v1.1 §I.2)
  const auto = groups.find((g) => g.blocks.some((b) =>
    laMuc(b) ? isOn(b[1], path) : b.items.some(([, h]) => isOn(h, path))
  ))?.key;
  const opened = new Set(open);
  if (auto) opened.add(auto);

  if (!ready) return <main className="muted">Đang tải…</main>;

  const lien = (l: string, h: string) => (
    <Link key={l + h} href={h} className={isOn(h, path) ? "on" : ""} onClick={() => setSide(false)}>{l}</Link>
  );

  return (
    <Ctx.Provider value={{ user, toast, datChuaLuu }}>
      <div className="top">
        <button type="button" className="burger" onClick={() => setSide((s) => !s)} aria-label="Menu">☰</button>
        <Link href="/" className="brand">VTOS <small>Vietourist Operating System</small></Link>
        <span className="bar">
          <ChonDonVi chuaLuu={() => chuaLuu.current} toast={toast} />
          <button type="button" className="soon" title="Sắp có" onClick={() => toast("Tìm kiếm: đang xây dựng")}>Tìm kiếm</button>
          <Link href="/#viec-cua-toi">Việc của tôi</Link>
          <Link href="/#cho-toi-duyet">Chờ tôi duyệt</Link>
          <Link href="/alerts" title="Thông báo & cảnh báo">🔔{alerts > 0 && <b> {alerts}</b>}</Link>
          <button type="button" className="soon" title="Sắp có" onClick={() => toast("Trợ lý AI: đang xây dựng")}>Trợ lý AI</button>
          {/* Menu cá nhân: ba mục của chính người đăng nhập, rời khỏi menu trái theo TC-2. */}
          <span style={{ position: "relative" }}>
            <button type="button" className="who" aria-haspopup="menu" aria-expanded={menuToi}
              onClick={() => setMenuToi((m) => !m)}
              style={{ background: "none", border: 0, cursor: "pointer", font: "inherit", color: "inherit" }}>
              {user?.full_name} · <b>{user?.role_name}</b> ▾
            </button>
            {menuToi && (
              <span role="menu" onClick={() => setMenuToi(false)}
                style={{ position: "absolute", right: 0, top: "100%", zIndex: 40, minWidth: 220,
                         display: "flex", flexDirection: "column", gap: 2, background: "#fff",
                         border: "1px solid #ddd", borderRadius: 6, padding: 6,
                         boxShadow: "0 6px 18px rgba(0,0,0,.15)" }}>
                {caNhan.map(([l, h]) => lien(l, h))}
                <a href="/login" onClick={() => clearSession()}>Thoát</a>
              </span>
            )}
          </span>
        </span>
      </div>
      <div className="shell">
        <aside className={"side" + (side ? "" : " hide") + (thu ? " thu" : "")}>
          {/* Nút thu/bung. §I.2: rộng 224–240px, thu còn 56–64px. Ẩn trên màn hình nhỏ vì ở đó thanh
              dọc đã đóng mở bằng nút ☰ – hai cách thu cùng lúc là hai cách mâu thuẫn nhau. */}
          <button type="button" className="thu-nut" onClick={doiThu}
            title={thu ? "Bung thanh menu" : "Thu thanh menu"}
            aria-label={thu ? "Bung thanh menu" : "Thu thanh menu"} aria-expanded={!thu}>
            {thu ? "»" : "«"}
          </button>
          {groups.map((g) => (
            <div key={g.key}>
              {/* Khi THU thì chỉ còn biểu tượng, nhưng nhãn nhóm vẫn nằm ở title và aria-label:
                  §I.2 đòi "biểu tượng phải có chú thích". Bấm một biểu tượng lúc đang thu thì BUNG
                  lại rồi mới mở nhóm – nếu không thì người dùng bấm xong không thấy gì xảy ra. */}
              <button type="button" className={"grp" + (opened.has(g.key) ? " on" : "")}
                title={g.label} aria-label={g.label}
                onClick={() => { if (thu) doiThu(); doiNhom(g.key); }}>
                {thu ? <span className="bt">{g.icon}</span>
                     : <>{opened.has(g.key) ? "▾ " : "▸ "}{g.label}</>}
              </button>
              {!thu && opened.has(g.key) && <div className="sub">
                {g.blocks.map((b, i) => laMuc(b) ? lien(b[0], b[1]) : (
                  <div key={b.label + i}>
                    <div className="muted" style={{ padding: "6px 0 2px", fontSize: ".82em", textTransform: "uppercase", letterSpacing: ".04em" }}>{b.label}</div>
                    {b.items.map(([l, h]) => lien(l, h))}
                  </div>
                ))}
              </div>}
            </div>
          ))}
        </aside>
        <main>{children}</main>
      </div>
      {t && <div className={"toast" + (t.err ? " err" : "")} role="status">{t.msg}</div>}
    </Ctx.Provider>
  );
}
