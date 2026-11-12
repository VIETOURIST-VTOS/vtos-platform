"use client";
import Shell from "@/components/Shell";
import BanGdKdLe from "@/components/BanGdKdLe";

/** R5 · Bàn làm việc Giám đốc Kinh doanh lẻ. R5-4 (13/11/2026): thân bàn dời sang
 *  `components/BanGdKdLe.tsx` theo mẫu v32 — GĐ KD gặp bàn này ngay ở /fit; đường dẫn này giữ cho
 *  Chủ tịch, TGĐ (chip «Kinh doanh lẻ» trên thanh dọc) và mọi dấu trang cũ. */
export default function Page() { return <Shell khongThanhBen><BanGdKdLe /></Shell>; }
