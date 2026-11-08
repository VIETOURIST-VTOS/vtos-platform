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
import { useShell } from "@/components/Shell";
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

export default function TrangPhanHe({ khoa }: { khoa: string }) {
  const sp = useSearchParams();
  const { user } = useShell();
  const phamVi = PHONG_CUA_PHAN_HE[khoa];
  const an = user?.hidden_menus || [];
  if (sp?.get("xem") === "muc-luc" || !phamVi || an.includes("/bao-cao")) {
    return <MucLucPhanHe khoa={khoa} />;
  }
  return <BangCuaPhong khoa={khoa} phamVi={phamVi} />;
}
