/** Phạm vi đang xem – lớp gọi máy chủ cho nút chọn đơn vị (TC-1).
 *
 *  HAI ĐƯỜNG DẪN, không có đường thứ ba (hợp đồng làn Phân quyền, 11/9/2026):
 *
 *      GET  /api/v1/pham-vi/don-vi      → { duoc_phep, dang_xem, co_the_thu_hep }
 *      PUT  /api/v1/pham-vi/dang-xem    { kieu, company_id }
 *
 *  HÌNH DẠNG LẤY TỪ MÃ MÁY CHỦ, KHÔNG LẤY TỪ THƯ GIAO HỢP ĐỒNG
 *  ------------------------------------------------------------
 *  Thư giao hợp đồng viết thân lệnh đặt là `{ company_id }`. Nhưng `app/services/pham_vi_dang_xem.py`
 *  – mã thật, đã nằm trên nhánh chung – dựng lựa chọn thành BA KIỂU:
 *
 *      toan_pham_vi    toàn bộ phần được phép      company_id = null
 *      don_vi          đúng một đơn vị và cây con  company_id = <id>
 *      chua_xac_dinh   riêng hồ sơ chưa gán pháp nhân
 *
 *  Một mình `company_id` không nói được kiểu thứ ba: null vừa có nghĩa "toàn phạm vi" vừa có nghĩa
 *  "chưa gán", mà hai thứ ấy ra hai danh sách khác hẳn nhau. Nên ở đây gửi cả `kieu`. Thân lệnh này
 *  là BAO của thân cũ: một máy chủ chỉ đọc `company_id` vẫn hiểu đúng hai kiểu đầu, chỉ kiểu
 *  `chua_xac_dinh` là cần máy chủ đọc `kieu`. Chênh lệch ấy đã báo lại làn Phân quyền.
 *
 *  BA ĐIỀU PHẢI GIỮ, vì bỏ điều nào cũng biến nút chọn thành một lỗ quyền:
 *
 *  1. Trình duyệt KHÔNG tự lọc danh sách đơn vị. Máy chủ trả về đúng những đơn vị tài khoản này
 *     được xem; ở đây chỉ vẽ lại. Lọc ở trình duyệt nghĩa là dữ liệu đã rời máy chủ rồi mới bị
 *     giấu đi – đó là rò, không phải phân quyền.
 *
 *  2. Trình duyệt KHÔNG gửi mã đơn vị kèm mỗi truy vấn dữ liệu. Đổi đơn vị là một lần PUT; từ đó
 *     máy chủ tự đọc phạm vi từ phiên. Nếu mỗi truy vấn mang theo mã đơn vị và máy chủ tin nó thì
 *     sửa một con số trên đường dẫn là xem được công ty khác.
 *
 *  3. Đổi ĐƠN VỊ ĐANG XEM không đổi PHÁP NHÂN CỦA CHỨNG TỪ. Đây là hai khái niệm khác nhau: một
 *     cái là "tôi đang nhìn phần nào", cái kia là "tờ chứng từ này thuộc về ai". Không có chỗ nào
 *     trong tệp này ghi pháp nhân lên một bản ghi nghiệp vụ.
 *
 *  TRẠNG THÁI HÔM NAY (11/9/2026): `pham_vi_dang_xem.py` đã có, nhưng CHƯA có bộ định tuyến nào
 *  phơi nó ra HTTP – `app/api/v1/` không có tệp pham_vi và `main.py` không đăng ký. Cho tới lúc đó
 *  `docDonVi()` trả về trạng thái "chưa có nguồn" chứ KHÔNG bịa danh sách.
 */

/** Ba kiểu lựa chọn, giữ đúng tên chuỗi của máy chủ. */
export const TOAN_PHAM_VI = "toan_pham_vi";
export const DON_VI = "don_vi";
export const CHUA_XAC_DINH = "chua_xac_dinh";
export type Kieu = typeof TOAN_PHAM_VI | typeof DON_VI | typeof CHUA_XAC_DINH;

/** Một nút trên cây đơn vị. Tên trường lấy đúng `pham_vi_dang_xem.cay()`. */
export type DonVi = {
  company_id: number;
  ten: string;
  ma?: string | null;
  loai?: string | null;
  hoat_dong?: boolean;
  cap?: number;
  con?: DonVi[];
};

/** Lựa chọn đang có hiệu lực, đúng hình `doc_chon()` / `mo_ta()` trả về.
 *
 *  `luu_tru` = "chua_co" nghĩa là máy chủ CHƯA có bảng lưu: đăng nhập lại sẽ về mặc định. Màn hình
 *  phải nói ra, vì hứa "đã ghi nhớ lựa chọn" trong khi không nhớ là thứ người dùng chỉ phát hiện
 *  vào hôm sau. `ve_mac_dinh` nghĩa là máy chủ vừa BỎ lựa chọn cũ vì nó đã ra ngoài phạm vi. */
export type LuaChon = {
  kieu: Kieu;
  company_id: number | null;
  cau_hien_thi?: string;
  luu_tru?: "co" | "chua_co";
  ve_mac_dinh?: string;
};

export type PhamViXem = {
  duoc_phep: DonVi[];
  dang_xem: LuaChon | null;
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
  { company_id: -1, ma: "GIA-ME", ten: "(GIẢ LẬP) Công ty mẹ", cap: 0, hoat_dong: true, con: [
    { company_id: -2, ma: "GIA-1", ten: "(GIẢ LẬP) Đơn vị trực thuộc 1", cap: 1, hoat_dong: true },
    { company_id: -3, ma: "GIA-2", ten: "(GIẢ LẬP) Đơn vị trực thuộc 2", cap: 1, hoat_dong: false, con: [
      { company_id: -4, ma: "GIA-2A", ten: "(GIẢ LẬP) Đơn vị cấp dưới 2A", cap: 2, hoat_dong: true },
    ] },
  ] },
];

/** Nhận cả hình cũ của thư giao hợp đồng (`{id, ten}` cho nút, `{id, ten}` cho lựa chọn) lẫn hình
 *  thật của máy chủ. Chỗ này KHÔNG phải để chiều hai hợp đồng mãi mãi – nó để một bên đổi trước
 *  bên kia không làm trắng màn hình, và để chênh lệch còn đọc được ra bằng mắt khi gỡ đi. */
function nut(o: any): DonVi {
  return {
    company_id: o?.company_id ?? o?.id,
    ten: o?.ten ?? "",
    ma: o?.ma ?? null,
    loai: o?.loai ?? null,
    hoat_dong: o?.hoat_dong ?? true,
    cap: o?.cap ?? 0,
    con: Array.isArray(o?.con) ? o.con.map(nut) : [],
  };
}

function luaChon(o: any): LuaChon | null {
  if (!o) return null;
  if (typeof o.kieu === "string") return o as LuaChon;
  // Hình cũ: { id, ten }. id rỗng = toàn phạm vi.
  const i = o.id;
  if (i === null || i === undefined) return { kieu: TOAN_PHAM_VI, company_id: null };
  return { kieu: DON_VI, company_id: Number(i) };
}

export async function docDonVi(): Promise<KetQuaPhamVi> {
  if (dangGiaLap()) {
    return { tinh_trang: "co", gia_lap: true,
             du_lieu: { duoc_phep: CAY_GIA,
                        dang_xem: { kieu: TOAN_PHAM_VI, company_id: null, luu_tru: "chua_co",
                                    cau_hien_thi: "(GIẢ LẬP) Bạn đang xem toàn bộ phạm vi được phép." },
                        co_the_thu_hep: true } };
  }
  let r: Response;
  try { r = await fetch(DUONG_DAN, { headers: dau() }); }
  catch (e) { return { tinh_trang: "loi", loi: String(e) }; }
  // 404 = máy chủ chưa dựng đường dẫn này. Phân biệt với lỗi thật: một bên là việc còn nợ có tên
  // và có người chịu, một bên là hỏng. Gộp hai thứ vào một câu "không tải được" thì không ai biết
  // phải đi hỏi ai.
  if (r.status === 404) return { tinh_trang: "chua_co_nguon", bo_phan: "Phân quyền" };
  if (!r.ok) return { tinh_trang: "loi", loi: `máy chủ trả ${r.status}` };
  try {
    const j = await r.json();
    return { tinh_trang: "co", du_lieu: {
      duoc_phep: Array.isArray(j?.duoc_phep) ? j.duoc_phep.map(nut) : [],
      dang_xem: luaChon(j?.dang_xem),
      co_the_thu_hep: j?.co_the_thu_hep !== false,
    } };
  } catch (e) { return { tinh_trang: "loi", loi: String(e) }; }
}

/** Đặt đơn vị đang xem.
 *
 *  Máy chủ kiểm lựa chọn có nằm trong phạm vi được phép không; ngoài phạm vi thì 403 kèm câu tiếng
 *  Việt đủ nghĩa (`kiem_chon()` viết sẵn câu ấy). Ở đây KHÔNG kiểm lại bằng danh sách trong trình
 *  duyệt: kiểm hai nơi thì nơi yếu hơn là nơi quyết định. */
export async function datDangXem(kieu: Kieu, ma?: number | null): Promise<{ ok: boolean; loi?: string; luu_tru?: string }> {
  if (dangGiaLap()) return { ok: true, luu_tru: "chua_co" };
  const than = JSON.stringify({ kieu, company_id: kieu === DON_VI ? ma : null });
  try {
    const r = await fetch(DUONG_DAN_DAT, { method: "PUT", headers: dau(), body: than });
    let j: any = null;
    try { j = await r.json(); } catch { /* máy chủ có thể trả rỗng */ }
    // Câu từ chối do máy chủ viết. Không thay bằng câu của mình: câu của mình sẽ nói sai chuyện
    // vừa xảy ra, vì ở đây không biết vì sao bị từ chối.
    if (!r.ok) return { ok: false, loi: j?.ly_do || j?.detail || `máy chủ trả ${r.status}` };
    return { ok: true, luu_tru: j?.luu_tru };
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

/** Nhãn ngắn cho nút trên thanh ngang. Câu dài `cau_hien_thi` của máy chủ đi vào tooltip và vào
 *  dòng "Đang xem" trong hộp – nhét cả câu lên nút thì nút nuốt mất thanh ngang. */
export function nhanNgan(chon: LuaChon | null, ten?: string): string {
  if (!chon || chon.kieu === TOAN_PHAM_VI) return "Toàn công ty";
  if (chon.kieu === CHUA_XAC_DINH) return "Chưa xác định pháp nhân";
  return ten || `Đơn vị #${chon.company_id}`;
}

export const KHOA_YEU_THICH = "vtos_donvi_yeu_thich";
export const KHOA_GAN_NHAT = "vtos_donvi_gan_nhat";
