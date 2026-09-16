"use client";
/** SÁU Ô LỚN của màn hình Chủ tịch — anh Tuấn chốt 16/9/2026.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TÁM THẺ NHỎ → SÁU Ô LỚN + MỘT HÀNG THẺ NHỎ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Anh Tuấn mở bản chạy thật rồi chốt: *"8 ô này anh muốn thay đổi vị trí — doanh thu, lợi nhuận
 *  trước thuế, dòng tiền, phải thu, phải trả, tồn đọng cần xử lý: 6 ô này làm biểu đồ lớn lên,
 *  chia ra các chart khác nhau theo cấu trúc; phần doanh thu và lợi nhuận phân ra theo tháng, quý,
 *  năm. Giảm từ 8 ô xuống còn 6 ô. Các phần tour đang bán, tour chờ quyết toán, tour sắp khởi
 *  hành, đội xe hôm nay, marketing đưa xuống vị trí dưới."*
 *
 *  Điều đáng ghi lại là VÌ SAO sáu ô ấy khác năm ô kia, chứ không phải chúng to hơn:
 *
 *    · SÁU Ô LỚN là những con số phải NGHĨ mới hiểu — chúng chỉ có nghĩa khi đặt cạnh kỳ trước,
 *      cạnh kế hoạch, hoặc chia theo cơ cấu. Một mình chúng không nói gì: "doanh thu 4,3 tỷ" là
 *      tốt hay xấu thì không ai trả lời được nếu không biết kế hoạch và tháng trước.
 *    · NĂM THẺ NHỎ là những con số chỉ để LIẾC — 349 tour đang bán, 93 tour sắp khởi hành. Đọc
 *      xong là xong, không cần so với gì cả. Thêm biểu đồ vào chúng là kéo mắt khỏi sáu ô trên.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  BA KHỐI CHUYỂN HẲN LÊN, KHÔNG ĐỂ LẠI BẢN SAO
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Dòng tiền · Phải thu · Phải trả trước vòng này là ba khối riêng nằm phía dưới. Anh Tuấn chọn
 *  "thay luôn — gộp lên trên". Nếu giữ cả hai thì mỗi con số nằm hai chỗ, đúng cái ông bảo bỏ ở
 *  vòng TC-40 ("các mục lặp lại thì bỏ hết"). Nên ba khối ấy KHÔNG có bản mới ở tệp này — chúng
 *  đổi CHỖ, không đổi mã. Tệp này dựng ba khối còn thiếu: Doanh thu, Lợi nhuận, Tồn đọng — và từ
 *  TC-44 (chiều cùng ngày) thì chỉ còn Tồn đọng, xem ghi chú giữa tệp.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TỆP NÀY KHÔNG TÍNH GÌ CẢ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9 giữ nguyên. Ba chuỗi tháng/quý/năm do `services/xu_huong.bo_ba_ky` dựng; tỉ lệ
 *  đạt kế hoạch do `services/ke_hoach.ty_le_dat` tính; ba mức tồn đọng do `services/canh_bao_muc`
 *  gom. Ở đây chỉ chọn trường nào vào hình nào, và diễn đạt lại thành câu.
 */
import Link from "next/link";
import { BieuDoCoCau, duVeCoCau, gonSo, type Phan } from "@/components/BieuDo";

/* ═══════════════════════════════════════════════════════════════════════════════════════════
   16/9/2026 · TC-44 · HAI Ô LỚN ĐẦU TIÊN ĐÃ RỜI TỆP NÀY
   ═══════════════════════════════════════════════════════════════════════════════════════════
   `KhoiBaKy`, `KhoiDoanhThu`, `KhoiLoiNhuan`, `docHoKeHoachKy` và `mocKeHoach` từng nằm ở đây.
   Anh Tuấn gửi bản vẽ chiều 16/9 và chốt hai ô ấy dùng CHUNG một bộ chọn kỳ; chúng chuyển hẳn
   sang components/KhoiKetQuaKinhDoanh.tsx.

   XOÁ chứ không để lại bản cũ, và đây là chỗ đáng ghi lý do: giữ `KhoiDoanhThu` lại "phòng khi
   cần" là để kho có hai cái tên cùng vẽ doanh thu, hai cách đọc kế hoạch, hai chỗ phải sửa khi
   luật đổi — đúng cái bệnh mà luật "MỘT CON SỐ · MỘT CHỖ · MỘT HÌNH" (TC-40) sinh ra để chặn.
   Bản cũ vẫn còn nguyên trong lịch sử git nếu cần đọc lại.

   Một điều bản cũ biết mà bản mới KHÔNG cần biết nữa: câu "kế hoạch chỉ có cho kỳ tháng". Bản cũ
   phải tự canh vì nó dựng vạch mốc từ kế hoạch THÁNG; bản mới đọc thẳng ô chỉ tiêu của ĐÚNG kỳ ấy
   (`services/ket_qua_kinh_doanh.bang` → `ke_hoach.hop_nhat(db, ky)`), nên không còn chỗ nào để suy
   ra một chỉ tiêu chưa ai duyệt. Luật không mất, nó chuyển xuống máy chủ.
   ═══════════════════════════════════════════════════════════════════════════════════════════ */

/** TỒN ĐỌNG CẦN XỬ LÝ, tách theo ba mức độ.
 *
 *  Trước vòng này khối này là một con số duy nhất (1483 cảnh báo đỏ). Một con số nằm một mình thì
 *  không nói được điều gì để hành động — không biết bao nhiêu phần trong đó là việc phải làm ngay.
 *
 *  Nhóm "Chưa phân loại" hiện RA chứ không bị gộp lặng lẽ: `Alert.level` là cột chuỗi, nên một
 *  robot viết sai chính tả mức là sinh ra một mức thứ tư. Gộp nó vào đâu đó thì tổng trên màn hình
 *  nhỏ hơn số việc thật; hiện nó ra thì trong tuần sẽ có người đi sửa.
 */
export function KhoiTonDongMuc({ d }: { d?: any | null }) {
  if (!d) {
    return (
      <section className="panel" id="ton-dong">
        <div className="mh01-dau"><h2>Tồn đọng cần xử lý</h2></div>
        <p className="muted">
          <span className="tag">Chưa kết nối</span> Máy chủ chưa trả bảng tồn đọng theo mức độ.{" "}
          <Link className="the-cua" href="/alerts">Trang cảnh báo →</Link>
        </p>
      </section>
    );
  }
  const phan: Phan[] = (d.phan || []).map((p: any) => ({
    ten: p.ten, gt: p.so === null || p.so === undefined ? null : Number(p.so),
    trang_thai: !!p.trang_thai,
  }));
  const do_ = (d.phan || []).find((p: any) => p.ma === "red")?.so ?? 0;
  return (
    <section className="panel" id="ton-dong">
      <div className="mh01-dau">
        <h2>Tồn đọng cần xử lý</h2>
        <span className="tag">chưa xử lý</span>
      </div>
      <div className="o6-so">
        <b className={"o6-lon" + (do_ > 0 ? " do" : "")}>{gonSo(Number(d.tong || 0), "dem")}</b>
        <span className="muted o6-nhan">việc đang mở · {gonSo(Number(do_), "dem")} mức nghiêm trọng</span>
      </div>
      {duVeCoCau(phan)
        ? <BieuDoCoCau ten="Cơ cấu theo mức độ" ds={phan} dinh_dang="dem"
            chan="Mức Nghiêm trọng mang màu cảnh báo vì nó là TRẠNG THÁI — việc đã thành vấn đề, không phải nấc nặng nhất của một thang." />
        : <p className="muted v14-ghi">Chưa có việc nào đang mở, nên chưa có cơ cấu để vẽ.</p>}
      <p className="muted v14-ghi">
        {d.co_muc_la
          ? <>Có việc mang mức KHÔNG nằm trong ba mức đã khai — hiện ở nhóm “Chưa phân loại”. Gộp
              lặng lẽ vào một mức khác là làm tổng trên màn hình nhỏ hơn số việc thật. (CNTT) </>
          : <>Chưa tách được hồ sơ quá hạn và hồ sơ chưa có người nhận — hai chỉ tiêu ấy máy chủ
              chưa đếm. (CNTT) </>}
        <Link className="the-cua" href="/alerts">Xem danh sách →</Link>
      </p>
    </section>
  );
}
