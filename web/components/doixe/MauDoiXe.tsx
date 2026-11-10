/** VH-5 · BỘ MÀU ĐỘI XE dùng chung cho /doi-xe và ba sổ con (Giá dầu, Phạt tài xế, Xe hôm nay) — Chủ tịch
 *  duyệt bản xem trước 10/11/2026: cùng điểm nhấn navy sáng với /xe, kiểu thẻ bo góc viền mảnh bóng nhẹ, nền
 *  vẫn trắng.
 *
 *  Chỉ sống bên trong `.dx-mau` của chính các trang ấy (kể cả khi trang mở trong khung nhúng của /xe). Không
 *  sửa `globals.css` hay `Shell.tsx`: nhiều làn cùng giữ hai tệp ấy, và các trang khác của CRM không đổi. */
const CSS = `
.dx-mau{--dx-nhan:#2c5fa2;--dx-dam:#183c69;--dx-nhat:#edf3fc;--dx-vien:#d6dfeb;--dx-bong:0 4px 14px #1b3a6214}
.dx-mau h1,.dx-mau h2{color:var(--dx-dam)}
.dx-mau .kpi{border-color:var(--dx-vien);border-radius:12px;box-shadow:var(--dx-bong)}
.dx-mau .kpi b{color:var(--dx-nhan)}
.dx-mau .panel{border-radius:12px;border-color:var(--dx-vien);box-shadow:var(--dx-bong)}
.dx-mau button.act.teal{background:var(--dx-nhan);border-color:var(--dx-nhan);color:#fff}
.dx-mau button.act.teal:hover{background:var(--dx-dam)}
.dx-mau button.act.grey,.dx-mau a.act.grey{background:#fff;color:var(--dx-nhan);border-color:#c9d6e8;font-weight:600}
.dx-mau .dx-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.dx-mau .dx-tabs button.act{margin:0;white-space:nowrap;border-radius:10px;padding:9px 14px;font-weight:600}
.dx-mau .dx-tabs button.act.teal{box-shadow:0 0 0 3px #9fc0ec}
.dx-mau th{background:var(--dx-nhat);color:var(--dx-dam);border-bottom:1px solid var(--dx-vien)}
.dx-mau tbody tr:hover td{background:#f8fbff}
`;

export default function MauDoiXe({ children }: { children: React.ReactNode }) {
  return <div className="dx-mau"><style>{CSS}</style>{children}</div>;
}
