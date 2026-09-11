/** Phạm vi đang xem – lớp gọi máy chủ cho nút chọn đơn vị (TC-1).
 *
 *  HỢP ĐỒNG do làn Phân quyền chốt 11/9/2026. Hai đường dẫn, không có đường thứ ba:
 *
 *      GET  /api/v1/pham-vi/don-vi      → { duoc_phep, dang_xem, co_the_thu_hep }
 *      PUT  /api/v1/pham-vi/dang-xem    { company_id }  → máy chủ kiểm rồi lưu theo phiên
 *
 *  BA ĐIỀU PHẢI GIỮ, vì bỏ điều nào cũng biến nút chọn thành một lỗ quyền:
 *
 *  1. Trình duyệt KHÔNG tự lọc danh sách đơn vị. Máy chủ trả về đúng những đơn vị tài khoản này
 *     được xem; ở đây chỉ vẽ lại. Lọc ở trình duyệt nghĩa là dữ liệu đã rời máy chủ rồi mới bị
 *     giấu đi – đó là rò, không phải phân quyền.
 *
 *  2. Trình duyệt KHÔNG gửi company_id kèm mỗi truy vấn dữ liệu. Đổi đơn vị là một lần PUT; từ đó
 *     máy chủ tự đọc phạm vi từ phiên. Nếu mỗi truy vấn mang theo mã đơn vị và máy chủ tin nó thì
 *     sửa một con số trên đường dẫn là xem được công ty khác.
 *
 *  3. Đổi ĐƠN VỊ ĐANG XEM không đổi PHÁP NHÂN CỦA CHỨNG TỪ. Đây là hai khái niệm khác nhau: một
 *     cái là "tôi đang nhìn phần nào", cái kia là "tờ chứng từ này thuộc về ai". Không có chỗ nào
 *     trong tệp này được ghi company_id lên một bản ghi nghiệp vụ.
 *
 *  TRẠNG THÁI HÔM NAY (11/9/2026): hai đường dẫn trên CHƯA có trên máy chủ – companies.py mới chỉ
 *  có GET /pham-vi cũ (đọc phạm vi, từ 08/9). Làn Phân quyền hẹn bản chạy thật trước 20/9. Cho tới
 *  lúc đó `docDonVi()` trả về trạng thái "chưa có nguồn" chứ KHÔNG bịa danh sách.
 */

export type DonVi = {
  id: number | "chua_gan";
  ma?: string;
  ten: string;
  con?: DonVi[];
};

export type PhamViXem = {
  duoc_phep: DonVi[];
  dang_xem: { id: number | "chua_gan"; ten: string } | null;  // null = toàn bộ phạm vi được phép
  co_the_thu_hep: boolean;
};

/** Trạng thái đọc: có nguồn, chưa có nguồn (máy chủ chưa dựng), hoặc lỗi thật. */
export type KetQuaPhamVi =
  | { tinh_trang: "co"; du_lieu: PhamViXem; gia_lap?: boolean }
  | { tinh_trang: "chua_co_nguon"; bo_phan: string }
  | { tinh_trang: "loi"; loi: string };

const DUONG_DAN = "/api/v1/pham-vi/don-vi";
const DUONG_DAN_DAT = "/api/v1/pham-vi/dang-xem";

function dau(): Record<string, string> {
  let t = "";
  try { t = localStorage.getItem("vtos_token") || ""; } catch { /* bỏ qua */ }
  return { Authorization: `Bearer ${t}`, "Content-Type": "application/json" };
}

/** Cờ xem thử giao diện. KHÔNG bao giờ bật mặc định, và khi bật thì nút chọn hiện một dải cảnh báo.
 *
 *  Vì sao phải có cờ và phải có dải cảnh báo: ranh giới Chủ tịch 09/9 nói robot không nhập và không
 *  tải SỐ LIỆU. Một danh sách đơn vị bịa ra nằm im trên màn hình là số liệu giả – ai chụp màn hình
 *  gửi đi thì nó thành số liệu thật. Cờ làm nó không tự xuất hiện; dải cảnh báo làm nó không thể
 *  bị nhầm. */
export function dangGiaLap(): boolean {
  try { return new URLSearchParams(window.location.search).get("giaLapDonVi") === "1"; }
  catch { return false; }
}

/** Cây đơn vị GIẢ, chỉ dùng khi có cờ ?giaLapDonVi=1. Tên đặt rõ là giả để không ai đọc nhầm thành
 *  danh mục pháp nhân thật. Danh mục thật nằm ở bảng companies và do Hành chính nhập. */
const CAY_GIA: DonVi[] = [
  { id: -1, ma: "GIA-ME", ten: "(GIẢ LẬP) Công ty mẹ", con: [
    { id: -2, ma: "GIA-1", ten: "(GIẢ LẬP) Đơn vị trực thuộc 1" },
    { id: -3, ma: "GIA-2", ten: "(GIẢ LẬP) Đơn vị trực thuộc 2", con: [
      { id: -4, ma: "GIA-2A", ten: "(GIẢ LẬP) Đơn vị cấp dưới 2A" },
    ] },
  ] },
  { id: "chua_gan", ten: "(GIẢ LẬP) Hồ sơ chưa xác định pháp nhân" },
];

export async function docDonVi(): Promise<KetQuaPhamVi> {
  if (dangGiaLap()) {
    return { tinh_trang: "co", gia_lap: true,
             du_lieu: { duoc_phep: CAY_GIA, dang_xem: null, co_the_thu_hep: true } };
  }
  let r: Response;
  try { r = await fetch(DUONG_DAN, { headers: dau() }); }
  catch (e) { return { tinh_trang: "loi", loi: String(e) }; }
  // 404 = máy chủ chưa dựng đường dẫn này. Phân biệt với lỗi thật: một bên là việc còn nợ có tên
  // và có người chịu, một bên là hỏng. Gộp hai thứ vào một câu "không tải được" thì không ai biết
  // phải đi hỏi ai.
  if (r.status === 404) return { tinh_trang: "chua_co_nguon", bo_phan: "Phân quyền" };
  if (!r.ok) return { tinh_trang: "loi", loi: `máy chủ trả ${r.status}` };
  try { return { tinh_trang: "co", du_lieu: await r.json() }; }
  catch (e) { return { tinh_trang: "loi", loi: String(e) }; }
}

/** Đặt đơn vị đang xem. `null` = toàn bộ phạm vi được phép ("Toàn công ty").
 *
 *  Máy chủ kiểm id có nằm trong phạm vi được phép không; ngoài phạm vi thì 403. Ở đây KHÔNG kiểm
 *  lại bằng danh sách trong trình duyệt: kiểm hai nơi thì nơi yếu hơn là nơi quyết định. */
export async function datDangXem(company_id: number | "chua_gan" | null): Promise<{ ok: boolean; loi?: string }> {
  if (dangGiaLap()) return { ok: true };
  try {
    const r = await fetch(DUONG_DAN_DAT, { method: "PUT", headers: dau(), body: JSON.stringify({ company_id }) });
    if (r.status === 403) return { ok: false, loi: "Đơn vị này ngoài phạm vi tài khoản của bạn." };
    if (!r.ok) return { ok: false, loi: `máy chủ trả ${r.status}` };
    return { ok: true };
  } catch (e) { return { ok: false, loi: String(e) }; }
}

/** Duyệt cây thành danh sách phẳng kèm độ sâu, để vẽ thụt đầu dòng và để tìm kiếm. */
export function duyetCay(cay: DonVi[], sau = 0): { dv: DonVi; sau: number }[] {
  const ra: { dv: DonVi; sau: number }[] = [];
  for (const dv of cay) {
    ra.push({ dv, sau });
    if (dv.con?.length) ra.push(...duyetCay(dv.con, sau + 1));
  }
  return ra;
}

export const KHOA_YEU_THICH = "vtos_donvi_yeu_thich";
export const KHOA_GAN_NHAT = "vtos_donvi_gan_nhat";
