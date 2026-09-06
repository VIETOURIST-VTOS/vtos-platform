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
    ["Tổng quan", "/"], ["Công ty thành viên & liên kết", ""], ["Kết quả từng đơn vị", ""],
    ["Báo cáo quản trị", "/robot-reports"], ["Chỉ đạo & theo dõi thực hiện", ""]] },
  { key: "marketing", label: "2. Marketing & CSKH", items: [
    ["Kế hoạch & ngân sách", ""], ["Chiến dịch", ""], ["Nội dung & thương hiệu", ""],
    ["Kênh & hộp thư", "/inbox"], ["Nguồn khách", "/leads?tab=leads"], ["Chăm sóc sau bán", ""],
    ["Phản hồi & khiếu nại", ""], ["Báo cáo hiệu quả", "/leads?tab=report"]] },
  { key: "kinhdoanh", label: "3. Kinh doanh & Sản phẩm", items: [
    ["Khách hàng & cơ hội bán", "/leads?tab=leads"], ["Sản phẩm", "/products"], ["Giá & chính sách bán", ""],
    ["Báo giá", ""], ["Yêu cầu & booking", "/requests"], ["Dịch vụ lẻ", "/non-package"],
    ["Hợp đồng", ""], ["Báo cáo bán hàng", "/sales-reports"]] },
  { key: "dieuhanh", label: "4. Điều hành", items: [
    ["Yêu cầu chờ xử lý", "/requests"], ["Chuyến tour & dự toán", "/tours"], ["Nhà cung cấp & đặt dịch vụ", ""],
    ["Hồ sơ visa", "/ops?tab=visa"], ["HDV & phân chuyến", "/ops?tab=guides"], ["Đội xe", "/ops?tab=fleet"],
    ["Sự cố tour", ""], ["Quyết toán tour", "/tours"]] },
  { key: "taichinh", label: "5. Tài chính & Kế toán", items: [
    ["Thu & đối soát", "/collections"], ["Đề nghị chi & thanh toán", "/expenses"], ["Công nợ", ""],
    ["Bảo lưu & hoàn tiền", "/bookings"], ["Dòng tiền", "/finance?tab=forecast"], ["Vay & đầu tư", "/finance?tab=contracts"],
    ["Sổ kế toán", "/accounting?tab=journal"], ["Hóa đơn & thuế", "/accounting?tab=invoices"],
    ["Báo cáo tài chính", "/accounting?tab=bctc"], ["Hồ sơ kiểm toán", ""], ["Khóa kỳ", "/accounting?tab=periods"]] },
  { key: "nhansu", label: "6. Hành chính & Nhân sự", items: [
    ["Hồ sơ nhân sự", "/hr?tab=employees"], ["Hợp đồng lao động", ""], ["Lương, thưởng & hoa hồng", "/hr?tab=payroll"],
    ["Báo cáo công việc", "/reports"], ["Đánh giá & sự vụ", "/hr?tab=incidents"], ["Văn bản", ""], ["Tài sản & mua sắm", ""]] },
  { key: "kiemsoat", label: "7. Kiểm soát & Chính sách", items: [
    ["Chính sách & định mức", "/params"], ["Cảnh báo nghiệp vụ", "/alerts"], ["Kiểm tra & đối chiếu", "/accounting?tab=misa"],
    ["Ngoại lệ cần xử lý", ""], ["Nhật ký nghiệp vụ", "/audit"]] },
  { key: "hethong", label: "8. Hệ thống & Tích hợp", items: [
    ["Cấu hình tổ chức", ""], ["Tài khoản & phân quyền", ""], ["Vị trí AI & quyền hạn", ""],
    ["Đồng bộ Vietrip", "/vietrip"], ["Kết nối MISA và các kênh", "/accounting?tab=misa"],
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
    const h = { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` };
    // làm mới quyền (menu ẩn/hiện) từ máy chủ mỗi lần mở – phòng khi ma trận phân quyền đổi sau khi đăng nhập
    fetch("/api/v1/auth/me", { headers: h }).then((r) => r.ok ? r.json() : null).then((m) => { if (m) { localStorage.setItem("vtos_user", JSON.stringify(m)); setUser(m); } }).catch(() => {});
    fetch("/api/v1/alerts", { headers: h }).then((r) => r.ok ? r.json() : null).then((a) => { if (Array.isArray(a)) setAlerts(a.length); else if (a?.rows) setAlerts(a.rows.length); }).catch(() => {});
  }, [router]);

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
