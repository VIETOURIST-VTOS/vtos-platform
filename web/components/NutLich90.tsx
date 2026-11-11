"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

/** VH-17 · nút vàng nhỏ «Lịch xe 90 ngày» của lãnh đạo và trưởng phòng. Quyền vào trang/cửa do máy chủ giữ
 *  (MENU_ROLES["/lich-xe-trong"], fleet.KHOANG_TRONG_XEM); danh sách này chỉ quyết ai THẤY NÚT.
 *  VH-27 (Chủ tịch 12/11/2026): rời thanh ngang, xuống góc phải đầu bàn làm việc, cạnh ô ngày — thanh ngang
 *  thôi bị ép đè lên chữ «Hệ thống điều hành». Số trên nút = ngày-xe trống 30 ngày tới. */
export const VAI_NUT_LICH_90 = ["chutich", "tgd", "ptgd_doan", "ptgd_mkt", "gd_kd", "tp_dh", "tp_kd", "tp_hd",
  "ketoan_truong", "hcns"];

export default function NutLich90() {
  const [trong, setTrong] = useState<number | null>(null);
  useEffect(() => {
    api("/fleet/lich-xe-tuong-lai?so_ngay=30").then((r: any) => setTrong(r?.ngay_xe_trong ?? null)).catch(() => {});
  }, []);
  return <Link href="/lich-xe-trong" className="n90s" title="Lịch xe 90 ngày — xe nào còn trống, ưu tiên bán tour">
    <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M3 9h18M8 2v4M16 2v4" /></svg>
    <span>Lịch xe 90 ngày</span>{trong !== null && <b>{trong} trống</b>}
  </Link>;
}
