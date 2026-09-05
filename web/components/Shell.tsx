"use client";
import { useEffect, useState, createContext, useContext, useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getUser, clearSession, type User } from "@/lib/api";

const NAV = [["/", "Bảng điều khiển"], ["/products", "Sản phẩm"], ["/tours", "Tour & dự toán"], ["/requests", "Yêu cầu & booking"], ["/collections", "Thu tiền"], ["/expenses", "Chi tiền"], ["/accounting", "Kế toán"], ["/finance", "Tài chính"], ["/alerts", "Cảnh báo"], ["/params", "Tham số chính sách"], ["/hr", "Nhân sự – Lương"], ["/reports", "Báo cáo ngày"], ["/robot-reports", "Robot báo cáo"], ["/vietrip", "Đồng bộ Vietrip"], ["/audit", "Nhật ký"]];

type Toast = { msg: string; err?: boolean } | null;
const Ctx = createContext<{ user: User | null; toast: (m: string, err?: boolean) => void }>({ user: null, toast: () => {} });
export const useShell = () => useContext(Ctx);

export default function Shell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [t, setT] = useState<Toast>(null);
  const path = usePathname();
  const router = useRouter();
  useEffect(() => { const u = getUser(); if (!u) router.replace("/login"); else { setUser(u); setReady(true); } }, [router]);
  const toast = useCallback((msg: string, err?: boolean) => { setT({ msg, err }); setTimeout(() => setT(null), err ? 6500 : 4000); }, []);
  if (!ready) return <main className="muted">Đang tải…</main>;
  return (
    <Ctx.Provider value={{ user, toast }}>
      <div className="top">
        <span className="brand">VTOS <small>Vietourist Operating System</small></span>
        <span className="right">{user?.full_name} · <b>{user?.role_name}</b><a href="/login" onClick={() => clearSession()}>Thoát</a></span>
      </div>
      <nav className="tabs">{NAV.map(([h, l]) => <Link key={h} href={h} className={(h === "/" ? path === "/" : path.startsWith(h)) ? "on" : ""}>{l}</Link>)}</nav>
      <main>{children}</main>
      {t && <div className={"toast" + (t.err ? " err" : "")} role="status">{t.msg}</div>}
    </Ctx.Provider>
  );
}
