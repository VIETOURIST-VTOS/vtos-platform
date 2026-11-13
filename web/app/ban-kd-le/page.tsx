"use client";
import { useEffect } from "react";

/** R5-5 · 13/11/2026 (Chủ tịch «ok sửa»): một bàn, một đường dẫn — bàn GĐ KD lẻ ở /fit. Trang này chỉ chuyển hướng. */
export default function Page() {
  useEffect(() => { location.replace("/fit"); }, []);
  return null;
}
