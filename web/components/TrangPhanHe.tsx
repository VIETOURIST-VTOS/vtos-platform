"use client";
/** ĐỢT PH-1 — THÂN CỦA TRANG PHÂN HỆ, tách ra khỏi `app/phan-he/[khoa]/page.tsx` ngày 08/11/2026.
 *
 *  VÌ SAO TÁCH. Năm phòng — Kinh doanh lẻ, Kinh doanh đoàn, Điều hành tour, Điều hành xe, Hướng
 *  dẫn — chuyển sang đường dẫn riêng `/fit`, `/mice`, `/op`, `/xe`, `/guide`. Cách rẻ trước mắt là
 *  chép tệp trang ra năm bản. Không làm thế: năm bản rồi sẽ lệch nhau, và lúc ấy không ai biết bản
 *  nào đúng. Thân trang nằm ở ĐÂY, sáu đường dẫn cùng gọi vào một chỗ.
 *
 *  ───────────────────────────────────────────────────────────────────────────────────────────
 *  LUẬT CŨ GIỮ NGUYÊN — chép lại để người đọc sau không phải đi tìm:
 *
 *  Vào phân hệ của một phòng thì thấy BẢNG CHỈ TIÊU của phòng ấy, không phải mục lục (Chủ tịch
 *  chốt 11/10/2026). Mục lục lùi về `?xem=muc-luc`, có lối vào ở cả đầu lẫn cuối trang — giữ nó
 *  là giữ chỗ duy nhất đọc được hệ thống CÒN NỢ những gì.
 *
 *  Ba nhánh:
 *    1. `?xem=muc-luc`, hoặc phân hệ KHÔNG có phòng tương ứng → mục lục.
 *    2. Có phòng, nhưng người đang xem không được xem bảng ấy → mục lục.
 *    3. Còn lại → bảng chỉ tiêu của phòng.
 *
 *  Câu "được xem hay không" KHÔNG trả lời ở đây: nó là câu trả lời của máy chủ (`hidden_menus` của
 *  phiên, và phạm vi do `/bao-cao/pham-vi` trả về). Bảng vai trò vẫn nằm đúng một chỗ ở
 *  `bao_cao_phong.PHONG`; mở thêm cửa vào không nới một quyền nào.
 *  ───────────────────────────────────────────────────────────────────────────────────────────
 *
 *  KHÔNG BỌC `Suspense` Ở ĐÂY, mà để người gọi bọc. Hai loại đường dẫn gọi vào tệp này và chúng
 *  có luật KHÁC NHAU: `/phan-he/[khoa]` là đường dẫn ĐỘNG nên không bị dựng sẵn và không cần ranh
 *  giới `Suspense`; còn `/fit` và bốn bạn của nó là đường dẫn TĨNH, Next ĐÒI ranh giới ấy quanh
 *  `useSearchParams`. Bọc sẵn ở đây thì đường động mang theo một lớp thừa; không bọc ở đây và
 *  quên bọc ở đường tĩnh thì `test_web_suspense_cho_search_params` đỏ. Nên tệp này không quyết
 *  thay, và năm trang tĩnh bọc đúng một lớp mỗi trang.
 */
import Link from "next/link";
import { useSearchParams } from "next/navigation";
// PH-2 · 11/11/2026 — `GROUPS` là bảng menu mà THANH DỌC đọc. Thanh chức năng ngang ở dưới
// đọc đúng bảng ấy, nên hai chỗ không bao giờ lệch nhau được.
import { useShell, GROUPS } from "@/components/Shell";
import BangChiTieuPhong, { usePhamViBaoCao } from "@/components/BangChiTieuPhong";
import BanLamViecPhong from "@/components/BanLamViecPhong";
import MucLucPhanHe from "@/components/MucLucPhanHe";
import { PHONG_CUA_PHAN_HE, timPhanHe } from "@/lib/cay_phan_he";
import { duongCuaPhong } from "@/lib/duong_phong";

function LoiVaoMucLuc({ khoa, duoi }: { khoa: string; duoi?: boolean }) {
  return (
    <p className={duoi ? "muted cay-cuoi" : "cay-chu"}>
      {duoi
        ? <>Phần hệ thống <b>còn nợ</b> của phân hệ này — những mục bản vẽ v1.3 có mà VTOS chưa
            dựng — nằm ở mục lục chức năng. </>
        : <>Đây là bảng chỉ tiêu của phòng. </>}
      <Link href={`${duongCuaPhong(khoa)}?xem=muc-luc`}>Xem mục lục chức năng →</Link>
    </p>
  );
}

/** Nhánh 2 và 3 nằm riêng một thành phần vì nó phải GỌI MÁY CHỦ, mà nhánh 1 thì không được gọi.
 *  React không cho gọi hook có điều kiện, nên nếu nhập chung thì mọi vai trò mở bất kỳ phân hệ
 *  nào cũng kéo theo một lượt hỏi `/bao-cao/pham-vi` — kể cả tài xế, người chắc chắn nhận 403 và
 *  sẽ thấy một dòng báo lỗi đỏ chỉ vì mở mục lục. Tách thành phần là cách để nhánh 1 thật sự
 *  không gọi gì. */
/** MỤC CỦA NHÓM chứa phòng này — đọc THẲNG từ bảng menu, không chép tay.
 *
 *  ĐO ĐƯỢC TRÊN BẢN THẬT 11/11/2026: thanh dọc chỉ vẽ sáu nhóm có `href` và các PHÒNG CON.
 *  Nó KHÔNG vẽ danh sách mục bên trong một nhóm. Nên mọi mục của nhóm Kinh doanh và nhóm
 *  Điều hành — «Hộp thư», «Khách hàng & nguồn khách», «Duyệt dự toán đoàn», «Lịch xe trống
 *  để bán» — chưa bao giờ bấm tới được, chỉ gõ đường dẫn mới vào. Đúng điều đã tìm ra cho
 *  phòng Marketing ngày 09/11 và là lý do có đợt MKT-3; đợt này chữa cho các nhóm còn lại.
 *
 *  GỠ PHẲNG `Item | Section` — BÀI HỌC MKT-4. `blocks` không thuần một kiểu: `Item` là cặp
 *  ["tên", "đường dẫn"], `Section` là `{ label, items }`. Đợt MKT-3 bóc mọi phần tử như một
 *  cặp và màn `/marketing` nổ trắng ngay khi tải. Ở đây gỡ phẳng, và CHỈ NHẬN phần tử nào
 *  thật sự là một mảng: ngày mai bảng menu thêm một kiểu thứ ba thì màn hình bỏ qua nó chứ
 *  không nổ — thiếu một mục trên thanh thì còn thấy được bằng mắt, màn trắng thì không.
 */
function mucCuaNhom(khoa: string): [string, string][] {
  const nhom = (GROUPS as any[]).find(
    (g) => g.key === khoa || (g.phans || []).some((f: any) => f.khoa === khoa));
  const ra: [string, string][] = [];
  for (const b of (((nhom || {}).blocks) || []) as any[]) {
    if (Array.isArray(b)) { ra.push(b as [string, string]); continue; }
    for (const m of (((b || {}).items) || []) as any[]) {
      if (Array.isArray(m)) ra.push(m as [string, string]);
    }
  }
  return ra;
}

/** THANH CHỨC NĂNG — khuôn lấy từ `/marketing` (MKT-3) và `/xe`, không tự nghĩ ra.
 *
 *  KHÔNG LỌC THEO QUYỀN Ở ĐÂY, cùng lẽ với hai màn ấy: hàng rào nằm ở máy chủ và ở chính
 *  màn hình đích. Giấu một mục đi thì người thiếu quyền không biết mình thiếu quyền, và họ
 *  sẽ đi hỏi người khác thay vì xin quyền ở Quản trị hệ thống.
 *
 *  KHÔNG ẨN THANH DỌC. `/marketing` và `/xe` có ẩn, nhưng đó là hai quyết định riêng Chủ
 *  tịch đã chốt cho từng màn. Ở đây thanh dọc vẫn là lối sang phân hệ khác, và đợt này
 *  không lấy của ai đường đi nào — nó chỉ THÊM một đường chưa có.
 */
function ThanhChucNang({ khoa }: { khoa: string }) {
  const muc = mucCuaNhom(khoa);
  if (muc.length === 0) return null;
  return (
    <nav aria-label="Chức năng của phân hệ"
         style={{ display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center",
                  marginBottom: 14, paddingBottom: 8, borderBottom: "1px solid #e6eaf0" }}>
      {muc.map(([ten, duong]) => (
        <Link key={duong + ten} href={duong} className="act grey" style={{ margin: 0 }}>{ten}</Link>
      ))}
    </nav>);
}

function BangCuaPhong({ khoa, phamVi, khongChip }: { khoa: string; phamVi: string; khongChip?: boolean }) {
  const { meta, xong } = usePhamViBaoCao();
  const ph = timPhanHe(khoa);
  if (!xong) return <p className="muted">Đang tải…</p>;
  if (!meta?.pham_vi.some((p) => p.ma === phamVi)) return <MucLucPhanHe khoa={khoa} khongChip={khongChip} />;
  return (<>
    <h1>{ph?.ten || khoa}</h1>
    {/* PH-2 · 11/11/2026 — CHỈ Ở NHÁNH NÀY, không ở nhánh mục lục. Chủ tịch dặn 10/11/2026:
        «các nút chức năng không được lặp lại trên cùng một màn hình — mỗi nút một chỗ».
        Màn mục lục đã liệt kê đúng những mục ấy rồi; đặt thêm thanh ngang lên trên nó là
        hai bảng nút cho cùng một việc. */}
    <ThanhChucNang khoa={khoa} />
    <LoiVaoMucLuc khoa={khoa} />
    {/* BD-1 · 12/10/2026 — VIỆC CẦN LÀM ĐỨNG TRÊN CHỈ TIÊU. Chủ tịch chốt sau khi xem bản dựng
        thử: người mở máy buổi sáng là để làm việc; chỉ tiêu tháng xem một lần đầu ngày là đủ.
        Bàn tự ẩn với phòng chưa khai hàng đợi, nên bảy phòng còn lại thấy y như trước. */}
    <BanLamViecPhong phong={phamVi} />
    <BangChiTieuPhong meta={meta} phamViCoDinh={phamVi} />
    <LoiVaoMucLuc khoa={khoa} duoi />
  </>);
}

export default function TrangPhanHe({ khoa, khongChip }: { khoa: string; khongChip?: boolean }) {
  const sp = useSearchParams();
  const { user } = useShell();
  const phamVi = PHONG_CUA_PHAN_HE[khoa];
  const an = user?.hidden_menus || [];
  if (sp?.get("xem") === "muc-luc" || !phamVi || an.includes("/bao-cao")) {
    return <MucLucPhanHe khoa={khoa} khongChip={khongChip} />;
  }
  return <BangCuaPhong khoa={khoa} phamVi={phamVi} khongChip={khongChip} />;
}
