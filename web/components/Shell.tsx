"use client";
import { useEffect, useState, createContext, useContext, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getUser, clearSession, type User } from "@/lib/api";

/** Tám nhóm nghiệp vụ theo Đề xuất chỉnh sửa hệ thống quản trị VTOS 06/9/2026 (mục 2).
 *  Một màn hình có thể xuất hiện ở nhiều nhóm khi nhiều phòng cùng dùng – "không tách bản dữ liệu
 *  khi tạo nhiều lối truy cập"; đường dẫn giữ nguyên nên ma trận phân quyền không đổi. */
export const GROUPS: { key: string; label: string; items: [string, string][] }[] = [
  { key: "holdings", label: "1. Điều hành Holdings", items: [["/", "Bảng điều khiển"], ["/robot-reports", "Báo cáo quản trị tự động"], ["/alerts", "Cảnh báo & việc chờ duyệt"]] },
  { key: "marketing", label: "2. Marketing & CSKH", items: [["/leads", "CRM – Lead & nguồn khách"], ["/inbox", "Hộp thư đa kênh"]] },
  { key: "kinhdoanh", label: "3. Kinh doanh & Sản phẩm", items: [["/products", "Sản phẩm chuẩn"], ["/requests", "Yêu cầu đặt dịch vụ"], ["/bookings", "Booking & bảo lưu"], ["/non-package", "Dịch vụ lẻ"], ["/sales-reports", "Báo cáo bán hàng"]] },
  { key: "dieuhanh", label: "4. Điều hành", items: [["/tours", "Tour & dự toán"], ["/requests", "Hàng đợi yêu cầu"]] },
  { key: "taichinh", label: "5. Tài chính & Kế toán", items: [["/collections", "Thu tiền"], ["/expenses", "Chi tiền"], ["/accounting", "Kế toán"], ["/finance", "Tài chính"]] },
  { key: "nhansu", label: "6. Hành chính & Nhân sự", items: [["/hr", "Nhân sự – Lương"], ["/reports", "Báo cáo công việc"]] },
  { key: "kiemsoat", label: "7. Kiểm soát & Chính sách", items: [["/params", "Chính sách & định mức"], ["/audit", "Nhật ký nghiệp vụ"]] },
  { key: "hethong", label: "8. Hệ thống & Tích hợp", items: [["/vietrip", "Đồng bộ Vietrip"]] },
];

const isOn = (href: string, path: string) => (href === "/" ? path === "/" : path.startsWith(href));

type Toast = { msg: string; err?: boolean } | null;
const Ctx = createContext<{ user: User | null; toast: (m: string, err?: boolean) => void }>({ user: null, toast: () => {} });
export const useShell = () => useContext(Ctx);

export default function Shell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [t, setT] = useState<Toast>(null);
  const [pick, setPick] = useState<string | null>(null);   // nhóm người dùng bấm chọn
  const path = usePathname();
  const router = useRouter();
  useEffect(() => {
    const u = getUser(); if (!u) { router.replace("/login"); return; }
    setUser(u); setReady(true);
    // làm mới quyền (menu ẩn/hiện) từ máy chủ mỗi lần mở – phòng khi ma trận phân quyền đổi sau khi đăng nhập
    fetch("/api/v1/auth/me", { headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` } }).then((r) => r.ok ? r.json() : null).then((m) => { if (m) { localStorage.setItem("vtos_user", JSON.stringify(m)); setUser(m); } }).catch(() => {});
  }, [router]);
  const toast = useCallback((msg: string, err?: boolean) => { setT({ msg, err }); setTimeout(() => setT(null), err ? 6500 : 4000); }, []);

  const groups = useMemo(() => {
    const hid = user?.hidden_menus || [];
    return GROUPS.map((g) => ({ ...g, items: g.items.filter(([h]) => !hid.includes(h)) })).filter((g) => g.items.length > 0);
  }, [user]);

  // nhóm đang mở: ưu tiên nhóm người dùng bấm (nếu nhóm đó chứa trang hiện tại hoặc vừa bấm),
  // ngược lại lấy nhóm đầu tiên có chứa trang hiện tại
  const auto = groups.find((g) => g.items.some(([h]) => isOn(h, path)))?.key;
  const pickHasPath = pick ? groups.find((g) => g.key === pick)?.items.some(([h]) => isOn(h, path)) : false;
  const cur = (pickHasPath ? pick : null) || auto || pick || groups[0]?.key;
  const items = groups.find((g) => g.key === cur)?.items || [];

  if (!ready) return <main className="muted">Đang tải…</main>;
  return (
    <Ctx.Provider value={{ user, toast }}>
      <div className="top">
        <span className="brand">VTOS <small>Vietourist Operating System</small></span>
        <span className="right">{user?.full_name} · <b>{user?.role_name}</b><a href="/login" onClick={() => clearSession()}>Thoát</a></span>
      </div>
      <nav className="groups" aria-label="Nhóm nghiệp vụ">
        {groups.map((g) => <button key={g.key} type="button" className={g.key === cur ? "on" : ""} onClick={() => setPick(g.key)}>{g.label}</button>)}
      </nav>
      <nav className="tabs" aria-label="Màn hình trong nhóm">
        {items.map(([h, l]) => <Link key={h + l} href={h} className={isOn(h, path) ? "on" : ""}>{l}</Link>)}
      </nav>
      <main>{children}</main>
      {t && <div className={"toast" + (t.err ? " err" : "")} role="status">{t.msg}</div>}
    </Ctx.Provider>
  );
}
