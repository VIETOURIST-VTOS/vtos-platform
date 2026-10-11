"use client";
/** Báo cáo tự động – hiện thẳng trên màn hình, không gửi mail hay Zalo (quyết định 09/9/2026).
 *
 *  BẢNG CHỈ TIÊU KHÔNG CÒN NẰM Ở ĐÂY (11/10/2026). Nó dời sang `components/BangChiTieuPhong.tsx`,
 *  vì từ hôm nay có HAI cửa dẫn tới cùng một bảng: màn hình này (chọn phòng bằng ô) và trang phân
 *  hệ `/phan-he/<khoa>` (phòng do cánh cửa quyết định). Hai bản chép tay của cùng một bảng thì sớm
 *  muộn lệch nhau; trang này nay chỉ còn là một cái vỏ.
 *
 *  Hành vi của màn hình KHÔNG đổi một chút nào: vẫn đủ ba ô Phạm vi · Kỳ · Thời điểm, vẫn đọc
 *  `?pham_vi=` từ đường dẫn, vẫn hiện cách tính và nguồn của từng chỉ tiêu.
 */
import Shell from "@/components/Shell";
import BangChiTieuPhong, { usePhamViBaoCao } from "@/components/BangChiTieuPhong";

function BaoCao() {
  const { meta, xong } = usePhamViBaoCao();
  if (!meta) return <p className="muted">{xong ? "Không đọc được phạm vi báo cáo." : "Đang tải…"}</p>;
  if (!meta.pham_vi.length) return (<>
    <h1>Báo cáo tự động</h1>
    <p className="muted">Chưa có báo cáo nào dành cho vai trò của anh/chị. Báo cáo phòng hiện cho
      trưởng phòng và giám đốc phòng đó; báo cáo toàn công ty cho Chủ tịch, Tổng giám đốc và Ban
      Kiểm soát.</p>
  </>);
  return (<>
    <h1>Báo cáo tự động</h1>
    <BangChiTieuPhong meta={meta} />
  </>);
}

export default function Page() { return <Shell><BaoCao /></Shell>; }
