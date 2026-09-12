/** Thứ tự pháp nhân dùng CHUNG cho mọi ô chọn đơn vị trong VTOS.
 *
 *  Vì sao không để máy chủ xếp theo mã: xếp theo bảng chữ cái thì Buffalotours đứng đầu và
 *  Vietourist Holdings — công ty mẹ, nơi người xem đang ngồi — nằm gần cuối. Người mở màn hình
 *  thấy số của một pháp nhân nhỏ trước, và con số đầu tiên đập vào mắt là con số họ ít cần nhất.
 *
 *  Thứ tự dưới đây là thứ tự anh Tuấn chốt 12/9/2026: công ty mẹ, rồi vận tải, rồi các pháp nhân
 *  còn lại. Mã nào KHÔNG có trong danh sách này vẫn hiện đầy đủ, chỉ xếp sau và theo bảng chữ cái
 *  — thêm một pháp nhân mới thì nó xuất hiện ngay, không phải sửa tệp này mới thấy.
 */
export const THU_TU_MA = [
  "VTD",        // Công ty Cổ phần Vietourist Holdings – công ty mẹ
  "VTRIP-VT",   // Công ty TNHH Vận tải Vietrip
  "LANGAU",     // Công ty Cổ phần Retreat & Wellness La Ngâu
  "HKTN",       // Công ty Cổ phần Xã hội Hoàng Kim Tây Nguyên
];

type CoMa = { code?: string | null };

/** Một dòng trong ô chọn đơn vị, đúng như /dong-tien/meta và /pham-vi/don-vi trả về.
 *
 *  Có kiểu này vì gọi `xepDonVi(r.phap_nhan)` với `r` kiểu any thì T rơi về đúng ràng buộc {code}
 *  và mọi trường khác biến mất — màn hình đọc `ds[0].id` sẽ không biên dịch được.
 */
export type DonViChon = { id: number; code?: string | null; name?: string | null };

/** Vị trí của một pháp nhân trong thứ tự trên. Mã lạ trả về một số lớn để rơi xuống cuối. */
export function viTri(ma?: string | null): number {
  const i = THU_TU_MA.indexOf((ma || "").trim().toUpperCase());
  return i === -1 ? THU_TU_MA.length : i;
}

/** Xếp một danh sách pháp nhân theo thứ tự chốt, phần còn lại theo bảng chữ cái.
 *
 *  KHÔNG sửa mảng gốc: danh sách này còn được dùng ở chỗ khác trong cùng màn hình, và một hàm xếp
 *  tại chỗ là chỗ thứ tự đổi ở nơi không ai gọi nó.
 */
export function xepDonVi<T extends CoMa>(ds: T[]): T[] {
  return [...ds].sort((a, b) => {
    const va = viTri(a.code), vb = viTri(b.code);
    if (va !== vb) return va - vb;
    return (a.code || "").localeCompare(b.code || "", "vi");
  });
}
