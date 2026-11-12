"use client";
import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import DoanhThuChiTieuKd from "@/components/DoanhThuChiTieuKd";

/** R5-2 · 13/11/2026 (Chủ tịch chốt) — MÀN /kinh-doanh-le GỘP VÀO /fit.
 *
 *  Phần Kinh doanh LẺ nay là tab «Doanh thu & chỉ tiêu» của /fit. Đường dẫn cũ KHÔNG GÃY: ai mở
 *  /kinh-doanh-le (dấu trang, mục menu, tin nhắn đã gửi) được chuyển sang /fit?xem=doanh-thu.
 *  `?mang=doan` (Kinh doanh Đoàn) GIỮ NGUYÊN ở đợt này — vẫn chạy đúng thân cũ ngay tại đây.
 *  Thân màn đã dời sang `components/DoanhThuChiTieuKd.tsx`, không chép.
 */
function KinhDoanhLe() {
  const router = useRouter();
  const doan = useSearchParams().get("mang") === "doan";
  useEffect(() => { if (!doan) router.replace("/fit?xem=doanh-thu"); }, [doan, router]);
  if (doan) return <DoanhThuChiTieuKd />;
  return <div className="panel"><h2>Kinh doanh lẻ</h2><p className="muted">Màn này đã gộp vào trang Kinh doanh lẻ — đang chuyển…</p></div>;
}

export default function Page() { return <Shell><Suspense><KinhDoanhLe /></Suspense></Shell>; }
