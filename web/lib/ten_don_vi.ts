/** Rút gọn tên pháp nhân cho những chỗ chật – thanh ngang và ô chọn đơn vị.
 *
 *  LỊCH SỬ, ghi lại để lần sau không dựng lại cái đã bỏ: tệp này sinh ra 12/9/2026 làm CẦU TẠM cho
 *  ô đơn vị trên thanh ngang, lúc GET /pham-vi/don-vi còn trả 404. Cùng ngày anh Tuấn chốt BỎ HẲN ô
 *  ấy khỏi thanh ngang ("xoá bỏ chữ Vietourist Holdings") – logo bên trái đã nói người dùng đang ở
 *  Holdings rồi, thêm một ô chữ nữa là thừa.
 *
 *  Còn lại đúng phần vẫn dùng: hàm tenNgan(), gọi từ ChonDonVi để ô chọn đơn vị hiện tên gọn.
 *  docTenDonVi() giữ nguyên cho ngày làn Phân quyền dựng xong /pham-vi/don-vi và ô chọn thật cần
 *  biết tên pháp nhân đang xem mà không phải gọi thêm một vòng.
 */
import { api } from "@/lib/api";

export type TenDonVi = { ten: string; phu: string; day_du: string };

/** Bỏ phần loại hình đứng đầu tên pháp nhân để còn lại cái TÊN.
 *
 *  Bản vẽ ghi "Vietourist Holdings", còn trong sổ đăng ký thì pháp nhân tên là "Công ty Cổ phần
 *  Vietourist Holdings". Trên thanh ngang, chín pháp nhân đều mở đầu bằng "Công ty ..." nên phần ấy
 *  không phân biệt được gì, chỉ chiếm chỗ – đo 12/9: chip dài 249px đẩy cả cụm nút xuống hàng hai.
 *
 *  Tên ĐẦY ĐỦ không mất: nó nằm ở thuộc tính title, rê chuột là thấy.
 */
export function tenNgan(ten: string): string {
  const t = (ten || "").trim();
  const cat = t.replace(/^(công\s+ty\s+(cổ\s+phần|tnhh(\s+mtv)?|hợp\s+danh)?|ctcp|cty)\s+/iu, "").trim();
  return cat || t;      // cắt xong mà rỗng thì giữ nguyên, thà dài còn hơn trống
}

/** Đọc tên đơn vị đang xem. Trả null khi không dựng được từ nguồn thật – gọi bên ngoài phải lo
 *  đường rơi, chứ đừng thay bằng một chuỗi mặc định. */
export async function docTenDonVi(): Promise<TenDonVi | null> {
  try {
    const me: any = await api("/auth/me");
    const pv = me?.pham_vi;
    if (!pv) return null;

    // Bị giới hạn vào một pháp nhân: máy chủ đã nói tên thì dùng luôn, khỏi gọi thêm.
    if (pv.company_id != null) {
      if (pv.company_name) return { ten: tenNgan(pv.company_name), phu: "Phạm vi được cấp", day_du: pv.company_name };
      const ds: any[] = await api("/companies");
      const c = (ds || []).find((x) => x.id === pv.company_id);
      return c ? { ten: tenNgan(c.name), phu: "Phạm vi được cấp", day_du: c.name } : null;
    }

    // Xem toàn tập đoàn: tên hiện là tên CÔNG TY MẸ, không phải chữ "Toàn tập đoàn" – bản vẽ ghi
    // tên pháp nhân, và người đọc cần biết mình đang đứng ở pháp nhân nào.
    if (pv.bi_gioi_han === false) {
      const ds: any[] = await api("/companies");
      const me_ = (ds || []).find((x) => x.kind === "me");
      if (me_) return { ten: tenNgan(me_.name), phu: "Phạm vi báo cáo cấp Holdings", day_du: me_.name };
    }
    return null;
  } catch {
    return null;   // 401/403/404 đều rơi về nút "Chưa có nguồn" cũ, không nuốt lỗi thành tên giả
  }
}
