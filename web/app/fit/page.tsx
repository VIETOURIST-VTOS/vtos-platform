"use client";
/** ĐỢT PH-1 — Kinh doanh lẻ, đường dẫn riêng `/fit`. Chủ tịch chốt 08/11/2026.
 *
 *  TRANG NÀY KHÔNG CÓ THÂN RIÊNG. Nó gọi `components/TrangPhanHe` với khoá `kdle` — đúng thân
 *  đang chạy ở `/phan-he/[khoa]` từ 11/10/2026. Chép thân ra đây là tạo bản thứ hai của cùng một
 *  trang, và hai bản thì sớm muộn lệch nhau; lúc ấy không ai biết bản nào đúng.
 *
 *  CHỖ Ở CŨ `/phan-he/kdle` ĐÃ BỎ, chỉ còn lối chỉ sang đây — xem `app/phan-he/[khoa]/page.tsx`.
 *
 *  BỌC `Suspense` — BẮT BUỘC, và vì một lý do KHÁC với `/phan-he/[khoa]`. Đường dẫn kia là đường
 *  ĐỘNG nên Next không dựng sẵn và không đòi ranh giới nào. `/fit` là đường TĨNH: Next dựng
 *  sẵn, mà `TrangPhanHe` gọi `useSearchParams` để đọc `?xem=muc-luc`. Thiếu lớp này thì
 *  `npm run build` CHẾT ở đúng trang này — luật 11/10/2026, canh ở
 *  tests/test_web_suspense_cho_search_params.py.
 *
 *  R5-2 · 13/11/2026 (Chủ tịch chốt) — GỘP /kinh-doanh-le VÀO ĐÂY, hai tab:
 *    · «Bảng chỉ tiêu phòng» — TrangPhanHe như cũ, bỏ hàng nút chức năng (thanh dọc đã có đủ, luật
 *      một nút một chỗ). Chỉ hiện với vai có phạm vi báo cáo `kd_le`.
 *    · «Doanh thu & chỉ tiêu» — thân màn /kinh-doanh-le dời nguyên sang `DoanhThuChiTieuKd`.
 *  `?xem=doanh-thu` mở thẳng tab thứ hai (đích chuyển của /kinh-doanh-le). Vai không có bảng chỉ
 *  tiêu phòng (nhân viên, trưởng nhóm) vào thẳng tab doanh thu. Chỉ phòng Kinh doanh lẻ mở được
 *  trang này — MENU_ROLES["/fit"].
 */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import TrangPhanHe from "@/components/TrangPhanHe";
import DoanhThuChiTieuKd from "@/components/DoanhThuChiTieuKd";
import { usePhamViBaoCao } from "@/components/BangChiTieuPhong";

function KinhDoanhLe() {
  const { user } = useShell();
  const sp = useSearchParams();
  const xem = sp?.get("xem") || "";
  // Bảng chỉ tiêu phòng chỉ cho vai có màn /bao-cao (nhân viên, trưởng nhóm không có) — vai ấy
  // không gọi cửa phạm vi báo cáo (xem `usePhamViBaoCao(boQua)`).
  const { meta, xong } = usePhamViBaoCao(user ? (user.hidden_menus || []).includes("/bao-cao") : undefined);
  const coBang = !!meta?.pham_vi.some((p) => p.ma === "kd_le");
  const [tab, setTab] = useState<"bang" | "doanh-thu" | "">("");
  useEffect(() => {
    if (!xong || tab) return;
    setTab(xem === "doanh-thu" || !coBang ? "doanh-thu" : "bang");
  }, [xong, coBang, xem, tab]);

  // R5-2: chỉ phòng Kinh doanh lẻ. Menu đã ẩn mục với vai khác; gõ thẳng đường dẫn cũng dừng ở đây.
  if (user && (user.hidden_menus || []).includes("/fit")) {
    return <div className="panel"><h2>Kinh doanh lẻ</h2><p className="muted">Trang này chỉ dành cho phòng Kinh doanh lẻ.</p></div>;
  }
  if (xem === "muc-luc") return <TrangPhanHe khoa="kdle" />;
  if (!tab) return <div className="panel muted">Đang tải…</div>;
  return (<>
    {coBang && <nav className="fit-tab" aria-label="Trang Kinh doanh lẻ">
      <button type="button" aria-pressed={tab === "bang"} onClick={() => setTab("bang")}>Bảng chỉ tiêu phòng</button>
      <button type="button" aria-pressed={tab === "doanh-thu"} onClick={() => setTab("doanh-thu")}>Doanh thu &amp; chỉ tiêu</button>
    </nav>}
    {tab === "bang" ? <TrangPhanHe khoa="kdle" khongThanh /> : <DoanhThuChiTieuKd />}
    <style>{`
.fit-tab{display:flex;gap:6px;flex-wrap:wrap;border-bottom:2px solid #dbe3ee;margin:0 0 14px}
.fit-tab button{font:inherit;font-weight:700;border:0;background:none;padding:9px 14px;cursor:pointer;color:#5f6f86;
  border-bottom:3px solid transparent;margin:0 0 -2px}
.fit-tab button[aria-pressed=true]{color:#2c5fa2;border-bottom-color:#2c5fa2}
`}</style>
  </>);
}

export default function Page() {
  return <Shell><Suspense fallback={<div className="panel muted">Đang tải…</div>}>
    <KinhDoanhLe />
  </Suspense></Shell>;
}
