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
 *  ĐIỀU HÀNH XE CŨNG KHÔNG CÓ TRONG BẢNG, và đây là chỗ đợt này đã gần làm sai. Bản đầu khai
 *  `dhxe` trỏ sang `/xe`. Nhưng `/xe` đã có chủ: PR #744 (KS-46, 08/11/2026) dựng ở đó BÀN LÀM
 *  VIỆC của Giám đốc đội xe — màn riêng, không thanh dọc, có hàng đợi việc và ngăn kéo dẫn sang
 *  cửa nhập. Khai như thế nghĩa là bảng chỉ tiêu phòng sẽ ĐÈ LÊN bàn làm việc ấy. Nên `dhxe` ở
 *  lại `/phan-he/dhxe` và không chuyển hướng đi đâu; ngày nào đội xe muốn gộp hai thứ thì đó là
 *  một đợt riêng, có người quyết, chứ không phải một dòng trong bảng này.
 *
 *  Vậy bảng dưới đây có BỐN dòng, không phải năm và cũng không phải tám.
 */

/** Khoá phân hệ → đường dẫn mới. CHỈ gồm những phòng đã DỜI khỏi `/phan-he/<khoá>`. */
export const DUONG_PHONG: Record<string, string> = {
  kdle: "/fit",
  kddoan: "/mice",
  dhtour: "/op",
  hdv: "/guide",
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
