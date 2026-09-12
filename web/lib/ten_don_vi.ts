/** CẦU TẠM: tên đơn vị hiện trên thanh ngang, trong lúc chờ GET /pham-vi/don-vi của làn Phân quyền.
 *
 *  VÌ SAO CÓ TỆP NÀY. Bản vẽ giao diện 12/9 đòi thanh ngang hiện "Vietourist Holdings" kèm dòng phụ
 *  "Phạm vi báo cáo cấp Holdings". Trang thật hôm nay hiện "Chưa có nguồn · đơn vị" vì đường dẫn
 *  /api/v1/pham-vi/don-vi trả 404 – làn Phân quyền nhận dựng, hạn 20/9/2026 (đo lại 12/9).
 *
 *  KHÔNG BỊA GÌ. Cái tên ở đây không phải hằng số gõ tay, cũng không phải đoán. Nó lấy từ hai nguồn
 *  máy chủ đã trả về thật:
 *
 *      GET /auth/me   → pham_vi { company_id, company_name, bi_gioi_han, cau_hien_thi }
 *      GET /companies → danh mục pháp nhân, công ty mẹ là bản ghi có kind === "me"
 *
 *  Tài khoản bị giới hạn vào một pháp nhân thì hiện tên pháp nhân ấy. Tài khoản xem toàn tập đoàn
 *  (bi_gioi_han = false) thì hiện tên CÔNG TY MẸ – đúng cái máy chủ vừa nói, không phải cái mình
 *  muốn nó nói. Không đọc được nguồn nào thì trả null và nút quay về "Chưa có nguồn · đơn vị".
 *
 *  KHÔNG DỰNG NÚT ĐỔI ĐƠN VỊ Ở ĐÂY. /companies trả TOÀN BỘ danh mục cho mọi người đăng nhập, nó
 *  không cắt theo phạm vi được phép. Lấy danh sách ấy làm ô chọn là dựng một nút cho người ta bấm
 *  sang pháp nhân họ không được xem – nút sai, rồi lại phải gỡ. Phạm vi ĐƯỢC PHÉP chỉ có
 *  /pham-vi/don-vi mới trả lời được; tới lúc đó nút đổi mới mọc, và tệp này gỡ đi.
 */
import { api } from "@/lib/api";

export type TenDonVi = { ten: string; phu: string };

/** Đọc tên đơn vị đang xem. Trả null khi không dựng được từ nguồn thật – gọi bên ngoài phải lo
 *  đường rơi, chứ đừng thay bằng một chuỗi mặc định. */
export async function docTenDonVi(): Promise<TenDonVi | null> {
  try {
    const me: any = await api("/auth/me");
    const pv = me?.pham_vi;
    if (!pv) return null;

    // Bị giới hạn vào một pháp nhân: máy chủ đã nói tên thì dùng luôn, khỏi gọi thêm.
    if (pv.company_id != null) {
      if (pv.company_name) return { ten: pv.company_name, phu: "Phạm vi được cấp" };
      const ds: any[] = await api("/companies");
      const c = (ds || []).find((x) => x.id === pv.company_id);
      return c ? { ten: c.name, phu: "Phạm vi được cấp" } : null;
    }

    // Xem toàn tập đoàn: tên hiện là tên CÔNG TY MẸ, không phải chữ "Toàn tập đoàn" – bản vẽ ghi
    // tên pháp nhân, và người đọc cần biết mình đang đứng ở pháp nhân nào.
    if (pv.bi_gioi_han === false) {
      const ds: any[] = await api("/companies");
      const me_ = (ds || []).find((x) => x.kind === "me");
      if (me_) return { ten: me_.name, phu: "Phạm vi báo cáo cấp Holdings" };
    }
    return null;
  } catch {
    return null;   // 401/403/404 đều rơi về nút "Chưa có nguồn" cũ, không nuốt lỗi thành tên giả
  }
}
