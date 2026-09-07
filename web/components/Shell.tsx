"use client";
import { useEffect, useState, createContext, useContext, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getUser, clearSession, type User } from "@/lib/api";

/** Cấu trúc đích theo đề xuất 06/9/2026: thanh ngang chọn phạm vi và xử lý việc chung,
 *  thanh dọc vào 8 nhóm nghiệp vụ. Mục có đường dẫn rỗng là phần còn phải xây (hiện nhãn "sắp có",
 *  không bấm được) – giữ trong menu để lãnh đạo thấy toàn bộ lộ trình. */
export const GROUPS: { key: string; label: string; items: [string, string][] }[] = [
  { key: "holdings", label: "1. Điều hành Holdings", items: [
    ["Tổng quan", "/"], ["Công ty thành viên & liên kết", "/companies"], ["Kết quả từng đơn vị", ""],
    ["Báo cáo quản trị", "/robot-reports"],
    // Hai phòng Kinh doanh vào báo cáo qua menu của mình (?mang=le / ?mang=doan). Nếu chỉ có hai lối đó thì
    // không còn đường nào tới con số HỢP NHẤT – nên Điều hành Holdings giữ một lối vào không kèm tham số.
    ["Báo cáo bán hàng toàn hệ thống", "/sales-reports"],
    ["Chỉ đạo & theo dõi thực hiện", ""]] },
  { key: "marketing", label: "2. Marketing & CSKH", items: [
    ["Kế hoạch & ngân sách", ""], ["Chiến dịch", ""], ["Nội dung & thương hiệu", ""],
    ["Kênh & hộp thư", "/inbox"], ["Nguồn khách", "/leads?tab=leads"], ["Chăm sóc sau bán", ""],
    ["Phản hồi & khiếu nại", ""], ["Báo cáo hiệu quả", "/leads?tab=report"]] },
  // Kinh doanh tách làm hai phòng (chỉ đạo 07/9/2026). Mảng nằm ở TOUR chứ không ở booking, và được nhận theo
  // HỢP của hai quy tắc: loại chuyến là đoàn, HOẶC mã tour bắt đầu bằng MICE (quy ước đặt mã của phòng Đoàn).
  // Đo ngày 07/9/2026: 115/115 tour có chữ MICE đều là tour đoàn, nên hôm nay hai quy tắc trùng nhau – lấy hợp
  // để mai kia có ai nhập lệch thì tour vẫn không rơi khỏi màn hình của phòng mình.
  { key: "kd_le", label: "3. Kinh doanh Lẻ", items: [
    ["Khách hàng & cơ hội bán", "/leads?tab=leads"], ["Sản phẩm", "/products"],
    ["Tour lẻ", "/tours?mang=le"], ["Yêu cầu & booking", "/requests?mang=le"],
    ["Booking & bảo lưu", "/bookings?mang=le"], ["Dịch vụ lẻ", "/non-package"],
    ["Giá & chính sách bán", ""], ["Báo giá", ""], ["Báo cáo bán hàng", "/sales-reports?mang=le"]] },
  { key: "kd_doan", label: "4. Kinh doanh Đoàn (MICE)", items: [
    ["Tour đoàn", "/tours?mang=doan"], ["Yêu cầu & booking", "/requests?mang=doan"],
    ["Booking & bảo lưu", "/bookings?mang=doan"],
    ["Báo giá đoàn", ""], ["Hợp đồng", ""], ["Báo cáo bán hàng", "/sales-reports?mang=doan"]] },
  { key: "dieuhanh", label: "5. Điều hành", items: [
    ["Yêu cầu chờ xử lý", "/requests"], ["Chuyến tour & dự toán", "/tours"], ["Nhà cung cấp & đặt dịch vụ", "/nha-cung-cap"],
    ["Hồ sơ visa", "/visa"],
    ["Sự cố tour", ""], ["Quyết toán tour", "/tours"]] },
  // Xe và hướng dẫn viên tách khỏi Điều hành thành đơn vị riêng (chỉ đạo 07/9/2026). Xe nội bộ thuộc pháp nhân
  // Công ty TNHH Vận tải Vietrip, còn hướng dẫn viên hưởng lương ở công ty mẹ – gom vào một nhóm menu để
  // người phụ trách có màn hình của mình, thay vì nằm lẫn trong nghiệp vụ tour.
  { key: "vantai", label: "6. Vận tải & Hướng dẫn viên", items: [
    // Hồ sơ đội xe theo đặc tả "Quản lý vận hành xe Vietrip" v1.3: mã xe cố định, lịch sử biển, giấy tờ có
    // hạn và điều kiện khai thác. Màn hình /ops?tab=fleet cũ giữ nguyên cho phần bảng giá và lệnh điều xe.
    ["Hồ sơ xe & điều kiện khai thác", "/doi-xe"],
    ["Đội xe (bảng giá & lệnh)", "/ops?tab=fleet"], ["HDV & phân chuyến", "/ops?tab=guides"],
    ["Việc của tôi (tài xế & HDV)", "/xe-hdv"],
    // Đợt 4 đội xe: hai mục này trước để trống. Gợi ý điều xe lọc cứng trước, xếp hạng sau, và ghi vết
    // khi người chốt lệnh chọn khác gợi ý. Bảng hiệu quả ghi "chưa đủ dữ liệu" chứ không ghi 0.
    ["Lệnh điều xe", "/lenh-dieu-xe"], ["Chi phí & hiệu quả đội xe", "/hieu-qua-doi-xe"]] },
  { key: "taichinh", label: "7. Tài chính & Kế toán", items: [
    ["Thu & đối soát", "/collections"], ["Đề nghị chi & thanh toán", "/expenses"], ["Công nợ", "/cong-no"],
    ["Bảo lưu & hoàn tiền", "/bookings"], ["Dòng tiền", "/finance?tab=forecast"], ["Vay & đầu tư", "/finance?tab=contracts"],
    ["Tài khoản ngân hàng", "/bank-accounts"], ["Sổ kế toán", "/accounting?tab=journal"], ["Hóa đơn & thuế", "/accounting?tab=invoices"],
    ["Báo cáo tài chính", "/accounting?tab=bctc"], ["Hồ sơ kiểm toán", ""], ["Khóa kỳ", "/accounting?tab=periods"]] },
  { key: "nhansu", label: "8. Hành chính & Nhân sự", items: [
    ["Hồ sơ nhân sự", "/hr?tab=employees"], ["Hợp đồng lao động", ""], ["Lương, thưởng & hoa hồng", "/hr?tab=payroll"],
    ["Báo cáo công việc", "/reports"], ["Đánh giá & sự vụ", "/hr?tab=incidents"], ["Văn bản", ""], ["Tài sản & mua sắm", ""]] },
  { key: "kiemsoat", label: "9. Kiểm soát & Chính sách", items: [
    ["Chính sách & định mức", "/params"], ["Cảnh báo nghiệp vụ", "/alerts"], ["Kiểm tra & đối chiếu", "/accounting?tab=misa"],
    ["Ngoại lệ cần xử lý", ""], ["Nhật ký nghiệp vụ", "/audit"]] },
  { key: "taikhoan", label: "0. Tài khoản của tôi", items: [
    ["Đổi mật khẩu", "/doi-mat-khau"]] },
  { key: "hethong", label: "10. Hệ thống & Tích hợp", items: [
    ["Cấu hình tổ chức", "/companies"], ["Tài khoản & phân quyền", "/access"], ["Vị trí AI & quyền hạn", "/ai-roles"],
    ["Nạp dữ liệu", "/nap-du-lieu"], ["Đồng bộ Vietrip", "/vietrip"], ["Kết nối MISA và các kênh", "/accounting?tab=misa"],
    ["Lịch tự động hóa", ""], ["Nhật ký kỹ thuật", ""]] },
];

/** Vai trò được nhìn thấy các mục chưa xây (để theo dõi lộ trình); nhân viên nghiệp vụ chỉ thấy mục dùng được. */
const ROADMAP_ROLES = ["chutich", "tgd", "ptgd_doan", "ptgd_mkt", "ketoan", "cntt", "bks"];

const base = (href: string) => href.split("?")[0];
const isOn = (href: string, path: string) => { const b = base(href); return b === "/" ? path === "/" : path.startsWith(b); };

type Toast = { msg: string; err?: boolean } | null;
const Ctx = createContext<{ user: User | null; toast: (m: string, err?: boolean) => void }>({ user: null, toast: () => {} });
export const useShell = () => useContext(Ctx);

export default function Shell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [t, setT] = useState<Toast>(null);
  const [open, setOpen] = useState<string[]>([]);      // nhóm đang bung
  const [side, setSide] = useState(false);             // màn hình nhỏ: mở/đóng thanh dọc
  const [alerts, setAlerts] = useState(0);
  const path = usePathname();
  const router = useRouter();

  useEffect(() => {
    const u = getUser(); if (!u) { router.replace("/login"); return; }
    setUser(u); setReady(true);
    // Tài khoản còn mật khẩu tạm: đưa thẳng tới màn hình đổi mật khẩu. Máy chủ đã chặn mọi đường dẫn khác,
    // nên nếu không chuyển hướng ở đây thì người dùng chỉ thấy một loạt lỗi 403 mà không hiểu vì sao.
    if (u.must_change_password && path !== "/doi-mat-khau") { router.replace("/doi-mat-khau"); return; }
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    // làm mới quyền (menu ẩn/hiện) từ máy chủ mỗi lần mở – phòng khi ma trận phân quyền đổi sau khi đăng nhập
    fetch("/api/v1/auth/me", { headers: h }).then((r) => r.ok ? r.json() : null).then((m) => {
      if (!m) return;
      localStorage.setItem("vtos_user", JSON.stringify(m)); setUser(m);
      if (m.must_change_password && path !== "/doi-mat-khau") router.replace("/doi-mat-khau");
    }).catch(() => {});
    fetch("/api/v1/alerts", { headers: h }).then((r) => r.ok ? r.json() : null).then((a) => { if (Array.isArray(a)) setAlerts(a.length); else if (a?.rows) setAlerts(a.rows.length); }).catch(() => {});
  }, [router, path]);

  const toast = useCallback((msg: string, err?: boolean) => { setT({ msg, err }); setTimeout(() => setT(null), err ? 6500 : 4000); }, []);

  const groups = useMemo(() => {
    const hid = user?.hidden_menus || [];
    const roadmap = ROADMAP_ROLES.includes(user?.role || "");
    return GROUPS.map((g) => {
      const usable = g.items.filter(([, h]) => h && !hid.includes(base(h)));
      const items = g.items.filter(([, h]) => (h ? !hid.includes(base(h)) : roadmap && usable.length > 0));
      return { ...g, items, usable: usable.length };
    }).filter((g) => g.usable > 0);
  }, [user]);

  // nhóm chứa trang hiện tại luôn được bung
  const auto = groups.find((g) => g.items.some(([, h]) => h && isOn(h, path)))?.key;
  const opened = new Set(open);
  if (auto) opened.add(auto);

  if (!ready) return <main className="muted">Đang tải…</main>;
  const bar = (label: string, href?: string, title?: string) => href
    ? <Link key={label} href={href}>{label}</Link>
    : <button key={label} type="button" className="soon" title={title || "Sắp có"} onClick={() => toast(`${label}: đang xây dựng`)}>{label}</button>;

  return (
    <Ctx.Provider value={{ user, toast }}>
      <div className="top">
        <button type="button" className="burger" onClick={() => setSide((s) => !s)} aria-label="Menu">☰</button>
        <Link href="/" className="brand">VTOS <small>Vietourist Operating System</small></Link>
        <span className="bar">
          <select className="soon" disabled title="Chọn công ty / đơn vị – sắp có"><option>Vietourist Holdings</option></select>
          {bar("Tìm kiếm")}
          <Link href="/#viec-cua-toi">Việc của tôi</Link>
          <Link href="/#cho-toi-duyet">Chờ tôi duyệt</Link>
          <Link href="/alerts" title="Thông báo & cảnh báo">🔔{alerts > 0 && <b> {alerts}</b>}</Link>
          {bar("Trợ lý AI")}
          <span className="who">{user?.full_name} · <b>{user?.role_name}</b></span>
          <a href="/login" onClick={() => clearSession()}>Thoát</a>
        </span>
      </div>
      <div className="shell">
        <aside className={"side" + (side ? "" : " hide")}>
          {groups.map((g) => (
            <div key={g.key}>
              <button type="button" className={"grp" + (opened.has(g.key) ? " on" : "")}
                onClick={() => setOpen((o) => o.includes(g.key) ? o.filter((k) => k !== g.key) : [...o, g.key])}>
                {opened.has(g.key) ? "▾ " : "▸ "}{g.label}
              </button>
              {opened.has(g.key) && <div className="sub">
                {g.items.map(([l, h]) => h
                  ? <Link key={l} href={h} className={isOn(h, path) ? "on" : ""} onClick={() => setSide(false)}>{l}</Link>
                  : <span key={l} className="soon">{l} <i>sắp có</i></span>)}
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
