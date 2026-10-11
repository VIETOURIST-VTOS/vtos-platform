"use client";
/** TRANG PHÂN HỆ — từ 11/10/2026 mở ra MÀN HÌNH CHÍNH CỦA PHÒNG, không còn mở ra mục lục.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  CHỦ TỊCH CHỐT 11/10/2026
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *
 *  "Vào phân hệ của từng phòng ban thì phải thấy được giao diện chính của các giám đốc và trưởng
 *  phòng, thay vì mục lục như hiện tại."
 *
 *  Đây là LẬT LẠI phương án B mà chính Chủ tịch chốt ngày 13/9/2026, và lật có ý thức. Thứ đã có
 *  sẵn và đúng nghĩa "màn hình chính của trưởng phòng" là BẢNG CHỈ TIÊU TỰ ĐỘNG của phòng — bảng
 *  vốn sống ở `/bao-cao`, nơi Chủ tịch phải tự đổi ô chọn phòng mới tới được. Vòng này không dựng
 *  màn hình mới: nó mở đúng CÁNH CỬA còn thiếu.
 *
 *  MỤC LỤC KHÔNG BỊ BỎ. Nó lùi về `?xem=muc-luc`, có lối vào ở cả đầu lẫn cuối trang (Chủ tịch
 *  chọn "cả hai" khi em hỏi 11/10). Giữ nó là giữ chỗ duy nhất đọc được hệ thống CÒN NỢ những gì:
 *  bản vẽ v1.3 có 184 mục, VTOS thật có ngót 80 trang. Bỏ mục lục đi thì phần nợ ấy không biến
 *  mất, nó chỉ thành vô hình.
 *
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *  BA NHÁNH, VÀ VÌ SAO KHÔNG NỚI MỘT QUYỀN NÀO
 *  ─────────────────────────────────────────────────────────────────────────────────────────────
 *
 *    1. `?xem=muc-luc`, hoặc phân hệ KHÔNG có phòng tương ứng → mục lục, y như trước.
 *       Không có phòng: Tổng quan (bảng điều hành `/` đã là toàn công ty rồi — trỏ vào đây nữa là
 *       đặt một con số ở hai nơi), Báo cáo – Phân tích (trỏ vào chính nó là vòng tròn), Quản trị
 *       hệ thống (không phải phòng ban), và hai khoá gộp cũ `khachhang` · `vanhanh` còn sống cho
 *       ai đã lưu dấu trang.
 *    2. Có phòng, nhưng người đang xem không được xem bảng ấy → mục lục. Chủ tịch chốt "mọi
 *       người, theo quyền sẵn có": ai có quyền thì thấy bảng, ai không thì thấy mục lục như cũ.
 *    3. Còn lại → bảng chỉ tiêu của phòng.
 *
 *  Câu "được xem hay không" KHÔNG trả lời ở đây. Hai mốc đều là câu trả lời của máy chủ: danh
 *  sách `hidden_menus` của phiên (chặn sớm, khỏi gọi một cửa chắc chắn 403), và danh sách phạm vi
 *  do `/bao-cao/pham-vi` trả về. Bảng vai trò vẫn nằm đúng một chỗ ở `bao_cao_phong.PHONG`; mở
 *  thêm một cửa vào không nới một quyền nào, và máy chủ siết lúc nào thì cửa này siết theo.
 */
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import Shell, { useShell } from "@/components/Shell";
import BangChiTieuPhong, { usePhamViBaoCao } from "@/components/BangChiTieuPhong";
import BanLamViecPhong from "@/components/BanLamViecPhong";
import MucLucPhanHe from "@/components/MucLucPhanHe";
import { PHONG_CUA_PHAN_HE, timPhanHe } from "@/lib/cay_phan_he";

function LoiVaoMucLuc({ khoa, duoi }: { khoa: string; duoi?: boolean }) {
  return (
    <p className={duoi ? "muted cay-cuoi" : "cay-chu"}>
      {duoi
        ? <>Phần hệ thống <b>còn nợ</b> của phân hệ này — những mục bản vẽ v1.3 có mà VTOS chưa
            dựng — nằm ở mục lục chức năng. </>
        : <>Đây là bảng chỉ tiêu của phòng. </>}
      <Link href={`/phan-he/${khoa}?xem=muc-luc`}>Xem mục lục chức năng →</Link>
    </p>
  );
}

/** Nhánh 2 và 3 nằm riêng một thành phần vì nó phải GỌI MÁY CHỦ, mà nhánh 1 thì không được gọi.
 *  React không cho gọi hook có điều kiện, nên nếu nhập chung thì mọi vai trò mở bất kỳ phân hệ
 *  nào cũng kéo theo một lượt hỏi `/bao-cao/pham-vi` — kể cả tài xế, người chắc chắn nhận 403 và
 *  sẽ thấy một dòng báo lỗi đỏ chỉ vì mở mục lục. Tách thành phần là cách để nhánh 1 thật sự
 *  không gọi gì. */
function BangCuaPhong({ khoa, phamVi }: { khoa: string; phamVi: string }) {
  const { meta, xong } = usePhamViBaoCao();
  const ph = timPhanHe(khoa);
  if (!xong) return <p className="muted">Đang tải…</p>;
  if (!meta?.pham_vi.some((p) => p.ma === phamVi)) return <MucLucPhanHe khoa={khoa} />;
  return (<>
    <h1>{ph?.ten || khoa}</h1>
    <LoiVaoMucLuc khoa={khoa} />
    {/* BD-1 · 12/10/2026 — VIỆC CẦN LÀM ĐỨNG TRÊN CHỈ TIÊU. Chủ tịch chốt sau khi xem bản dựng
        thử: người mở máy buổi sáng là để làm việc; chỉ tiêu tháng xem một lần đầu ngày là đủ.
        Bàn tự ẩn với phòng chưa khai hàng đợi, nên bảy phòng còn lại thấy y như trước. */}
    <BanLamViecPhong phong={phamVi} />
    <BangChiTieuPhong meta={meta} phamViCoDinh={phamVi} />
    <LoiVaoMucLuc khoa={khoa} duoi />
  </>);
}

function Trang({ khoa }: { khoa: string }) {
  const sp = useSearchParams();
  const { user } = useShell();
  const phamVi = PHONG_CUA_PHAN_HE[khoa];
  const an = user?.hidden_menus || [];
  if (sp?.get("xem") === "muc-luc" || !phamVi || an.includes("/bao-cao")) {
    return <MucLucPhanHe khoa={khoa} />;
  }
  return <BangCuaPhong khoa={khoa} phamVi={phamVi} />;
}

/** KHÔNG bọc `Suspense`, và đó là kết quả của một phép đo chứ không phải quên.
 *
 *  Next đòi ranh giới `Suspense` quanh `useSearchParams` khi trang bị DỰNG SẴN. Sáu màn hình
 *  dùng `useSearchParams` trong kho đều bọc — và cả sáu đều là đường dẫn TĨNH. Màn hình thứ bảy,
 *  `app/tours/[id]/page.tsx`, là đường dẫn ĐỘNG và KHÔNG bọc; nó nằm trên main và nhịp `web`
 *  vẫn xanh. Kho không có một `generateStaticParams` nào, nên đường dẫn động không bị dựng sẵn.
 *
 *  `/phan-he/[khoa]` là đường dẫn động, nên theo đúng tiền lệ ấy. Ngày nào ai thêm
 *  `generateStaticParams` cho nhánh này thì luật đổi — và `test_web_suspense_cho_search_params`
 *  đỏ đúng ngày đó, nên không phải nhớ.
 *
 *  Lấy khoá bằng useParams chứ không nhận qua tham số `params`: Next 15 đổi `params` thành
 *  Promise còn Next 14 thì không, và trang này là client component nên useParams chạy đúng ở cả
 *  hai. */
export default function Page() {
  const p = useParams<{ khoa: string }>();
  return <Shell><Trang khoa={String(p?.khoa || "")} /></Shell>;
}
