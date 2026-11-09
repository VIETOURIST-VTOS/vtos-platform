/** ĐỢT PH-1 — MỘT CHỖ DUY NHẤT KHAI ĐƯỜNG DẪN CỦA TỪNG PHÒNG.
 *
 *  Chủ tịch chốt 08/11/2026: mỗi phòng ban có một đường dẫn riêng, tên ngắn, và bấm vào phân hệ
 *  nào thì ra đúng trang của phòng ấy.
 *
 *  VÌ SAO MỘT TỆP RIÊNG, KHÔNG RẢI MỖI CHỖ MỘT ÍT. Bảng này được ba nơi đọc: thanh menu dọc, năm
 *  trang mới, và lối chuyển tiếp từ đường dẫn cũ. Chép tay ba bản thì ngày đổi một đường dẫn sẽ
 *  có đúng hai nơi đổi theo và một nơi quên — mà nơi quên ấy không đỏ ở đâu cả, nó chỉ dẫn người
 *  dùng tới một trang 404 vào một buổi sáng nào đó.
 *
 *  BA PHÒNG KHÔNG CÓ TRONG BẢNG NÀY, và đó là chủ ý. Marketing, HC–NS và Tài chính – Kế toán đã
 *  có MÀN HÌNH LÀM VIỆC THẬT ở `/marketing`, `/hr`, `/finance`. Chủ tịch chốt 08/11/2026: dùng
 *  đúng ba màn ấy, không dời đi đâu cả. Giữ nguyên chỗ của chúng là giữ nguyên luôn phần khai
 *  phạm vi API trong `access.py` — đó là cái lợi lớn nhất của cách này.
 *
 *  ĐIỀU HÀNH XE VÀO BẢNG NGÀY 09/11/2026, và đây là một quyết định có người ký chứ không phải
 *  một dòng thêm cho đủ. Đợt PH-1 (08/11) CỐ Ý để `dhxe` ở ngoài, vì `/xe` đã có chủ: PR #744
 *  dựng ở đó BÀN LÀM VIỆC của Giám đốc đội xe, và khai vào bảng này lúc ấy nghĩa là bảng chỉ
 *  tiêu phòng ĐÈ LÊN bàn làm việc. Ghi chú hôm ấy để ngỏ: "ngày nào đội xe muốn gộp hai thứ thì
 *  đó là một đợt riêng, có người quyết".
 *
 *  Anh Tuấn quyết 09/11/2026: "em bỏ màn hình này, để gộp qua chung 1 màn hình /xe".
 *
 *  Và lo ngại cũ KHÔNG còn đúng, vì KS-54/KS-56 đổi cách gắn: `/xe` gắn `TrangPhanHe` thành MỘT
 *  VÙNG ở cuối màn, không thay thế bàn làm việc. Ai xem được bảng chỉ tiêu đội xe thì vẫn thấy
 *  đủ bảng ấy — chỉ là thấy ở dưới bàn làm việc chứ không ở một trang riêng. Không ai mất gì,
 *  nên dời chỗ ở là dời thật, không phải đánh đổi.
 *
 *  Vậy bảng dưới đây có NĂM dòng, không phải bốn và cũng không phải tám.
 */

/** Khoá phân hệ → đường dẫn mới. CHỈ gồm những phòng đã DỜI khỏi `/phan-he/<khoá>`. */
export const DUONG_PHONG: Record<string, string> = {
  kdle: "/fit",
  kddoan: "/mice",
  dhtour: "/op",
  dhxe: "/xe",
  hdv: "/guide",
  // MKT-2 · 09/11/2026 — Marketing vào bảng này, và nó vào theo một lẽ KHÁC bốn dòng trên.
  // Bốn phòng kia dời sang một trang MỚI dựng. Marketing thì không dời đi đâu cả: `/marketing`
  // đã chạy từ lâu, và đợt này gộp nốt mục lục của `/phan-he/marketing` vào đó rồi bỏ trang
  // cũ. Kết quả giống nhau — `/phan-he/marketing` chuyển hướng về `/marketing` — nên nó
  // thuộc đúng bảng này, chỗ duy nhất trả lời câu «phòng này ở đường dẫn nào».
  marketing: "/marketing",
};

/** Đường dẫn mới → khoá phân hệ. Bốn trang mới đọc bảng này để biết mình là phòng nào. */
export const KHOA_THEO_DUONG: Record<string, string> = Object.fromEntries(
  Object.entries(DUONG_PHONG).map(([khoa, duong]) => [duong, khoa]),
);

/** Đường dẫn của một phòng trên thanh menu.
 *
 *  Chưa dời thì vẫn là `/phan-he/<khoá>` — hàm này KHÔNG đoán: không có trong bảng nghĩa là phòng
 *  ấy còn ở chỗ cũ, và trả về chỗ cũ là đúng, không phải là thiếu sót.
 */
export function duongCuaPhong(khoa: string): string {
  return DUONG_PHONG[khoa] || `/phan-he/${khoa}`;
}
