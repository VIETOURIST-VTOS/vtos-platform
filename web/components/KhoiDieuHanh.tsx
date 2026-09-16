"use client";
/** KHỐI 04a · ĐIỀU HÀNH — chuyến khởi hành trong N ngày tới.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TÁCH RA KHỎI MÀN HÌNH 01 NGÀY 15/9/2026, VÀ VÌ SAO KHÔNG XOÁ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Anh Tuấn xem bản chạy thật và chốt bỏ khối này khỏi bảng điều hành Chủ tịch: đo được là nó cao
 *  3.693px — 45% chiều cao toàn trang — để trình một danh sách 92 chuyến mà bốn trên bảy cột đều
 *  ghi "chưa nối". Ông ấy mở bảng ra để quyết việc, không để đọc danh sách điều hành.
 *
 *  Nhưng mã KHÔNG xoá, và đây là lý do: khối này mang theo bốn luật đã phải trả giá mới có, và cả
 *  bốn vẫn đúng ở bất kỳ màn hình nào trình danh sách chuyến sắp đi:
 *
 *   1. BẢY ĐẦU CỘT DỰNG ĐỦ dù máy chủ mới trả ba. Đầu cột chính là bản mô tả việc còn nợ; giấu đi
 *      thì đến lúc dựng phải đi tìm lại bản vẽ.
 *   2. MỐC HOÀ VỐN BẰNG 0 KHÔNG PHẢI LÀ ĐẠT MỐC. Máy chủ trả breakeven = 0 cho hầu hết chuyến vì
 *      chưa ai nhập điểm hoà vốn; câu cũ `r.below ? đỏ : xanh` đọc số 0 ấy thành "đã vượt mốc" và
 *      dán nhãn xanh "ok" lên cả chuyến 0 khách.
 *   3. KHÔNG MẶC ĐỊNH CHUYẾN ĐÃ SẴN SÀNG — bản vẽ V1.4 ghi thẳng, và nó là hệ quả của luật 2.
 *   4. CUỘN TRONG KHUNG, KHÔNG CẮT DÒNG. 92 chuyến là 92 việc có thật trong 14 ngày tới; giấu
 *      dòng nào là giấu đúng việc ấy.
 *
 *  Lắp lại vào màn hình Điều hành thì dùng được ngay, không phải dựng lại từ đầu.
 */
import Link from "next/link";
import { fmtD } from "@/lib/api";
import { Tag } from "@/components/ui";

export default function KhoiDieuHanh({ sec, soNgayKH }: { sec: any; soNgayKH: number }) {
  if (!sec?.sap_khoi_hanh) return null;
  return (
    <div className="grid" style={{ marginTop: 14 }}>
    {/* KHỐI 04a · ĐIỀU HÀNH. Bản vẽ V1.4 đòi bảy cột: Chuyến · Ngày đi · Số khách · Dịch vụ còn
        thiếu · Xe · HDV · Phụ trách, và ưu tiên chuyến CÒN THIẾU ĐIỀU KIỆN lên trước.

        Máy chủ hôm nay mới trả ba cột đầu. Bốn cột sau vẫn DỰNG ĐỦ ĐẦU CỘT và ghi "chưa nối" ở
        từng ô: đầu cột chính là bản mô tả việc còn nợ, giấu đi thì đến lúc dựng phải đi tìm lại
        bản vẽ. Cũng KHÔNG suy "đã đủ điều kiện" từ việc thiếu dữ liệu – bản vẽ ghi thẳng: không
        mặc định chuyến đã sẵn sàng.

        SỐ NGÀY: anh Tuấn chốt 14/9/2026 lấy theo BẢN VẼ, tức 14 ngày. Máy chủ đổi từ 21 xuống
        14 và TRẢ LUÔN con số ấy ra (`sap_khoi_hanh_so_ngay`); màn hình đọc nó chứ không gõ lại.
        Trước đó hai nơi mang hai con số nên phải in cả hai ra — mà in cả hai thì chẳng ai biết
        tin con nào. */}
    {sec.sap_khoi_hanh && <div className="panel" id="dieu-hanh"><h2>Điều hành – chuyến khởi hành {soNgayKH} ngày tới</h2>
      <p className="muted">Ưu tiên chuyến còn thiếu điều kiện — <b>không</b> mặc định chuyến đã sẵn sàng.</p>
      {/* TC-35 · KHUNG CUỘN, KHÔNG CẮT DÒNG. Đo trên bản chạy thật 15/9: khối này cao 3.693px —
          45% chiều cao toàn trang — vì 92 chuyến đổ hết ra một mạch, trong khi bản vẽ để khối
          cao 158px. Hệ quả: mở trang phải cuộn gần bốn nghìn pixel mới tới khối kế tiếp, nên
          đọc từ trên xuống ra một trang khác hẳn bản vẽ dù đủ khối.

          Cách chữa là CUỘN TRONG KHUNG, không phải cắt bớt dòng rồi ghi "xem thêm": 92 chuyến
          này là 92 việc có thật trong 14 ngày tới, giấu đi dòng nào là giấu đúng dòng ấy. Đầu
          bảng dính lại khi cuộn để không mất tên cột. */}
      {sec.sap_khoi_hanh.length ? <div className="wrap mh01-cuon"><table className="v14-bang">
        <thead><tr><th>Chuyến</th><th>Ngày đi</th><th>Số khách</th><th>Dịch vụ còn thiếu</th><th>Xe</th><th>HDV</th><th>Phụ trách</th></tr></thead>
        <tbody>{sec.sap_khoi_hanh.map((r: any) => <tr key={r.code}>
          <td>{r.code}</td>
          <td>{fmtD(r.start)} (D-{r.days_left})</td>
          {/* MỐC HOÀ VỐN BẰNG 0 KHÔNG PHẢI LÀ ĐẠT MỐC. Máy chủ hiện trả breakeven = 0 cho hầu hết
              chuyến vì chưa ai nhập điểm hoà vốn. Câu cũ `r.below ? đỏ : xanh` đọc số 0 ấy thành
              "đã vượt mốc" và dán nhãn xanh "ok" lên cả chuyến 0 khách — đúng cái bản vẽ cấm:
              không mặc định chuyến đã sẵn sàng. Chưa có mốc thì nói chưa có mốc. */}
          <td>{r.booked}/{r.breakeven || "—"} khách {
            !r.breakeven
              ? <Tag>chưa có mốc hoà vốn</Tag>
              : r.below ? <Tag cls="red">dưới hòa vốn</Tag> : <Tag cls="ok">ok</Tag>
          }</td>
          <td>{r.dich_vu_thieu ?? <span className="muted">chưa nối</span>}</td>
          <td>{r.xe ?? <span className="muted">chưa nối</span>}</td>
          <td>{r.hdv ?? <span className="muted">chưa nối</span>}</td>
          <td>{r.phu_trach ?? <span className="muted">chưa nối</span>}</td>
        </tr>)}</tbody></table></div> : <p className="muted">Không có chuyến.</p>}
      <p className="muted">Bốn cột <b>Dịch vụ còn thiếu · Xe · HDV · Phụ trách</b> máy chủ chưa trả — <b>Điều hành</b> nhập ở <Link className="the-cua" href="/lenh-dieu-xe">Lệnh điều xe →</Link></p>
      {/* Danh sách 100 mã quá hạn quyết toán: gấp lại. Trải thẳng ra thì nó là một đoạn chữ
          dài bằng cả một khối, mà không ai đọc một trăm mã liền nhau — đếm được số thì đủ để
          quyết có mở ra hay không. Vẫn là thẻ <details> nên in ra giấy và tìm chữ vẫn thấy. */}
      {sec.qua_han_qt?.length > 0 && <details className="mh01-gap">
        <summary><Tag cls="red">Quá hạn quyết toán</Tag> {sec.qua_han_qt.length} chuyến</summary>
        <p className="muted">{sec.qua_han_qt.map((t: any) => t.code).join(", ")}</p>
      </details>}</div>}
    </div>
  );
}
