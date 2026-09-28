"use client";
/** BIỂU ĐỒ CỦA MÀN HÌNH CHỦ TỊCH — dựng sẵn, giao cho TỪNG KHỐI tự bày.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  BIỂU ĐỒ VỀ NẰM CẠNH CON SỐ NÓ VẼ — ĐƯỜNG ĐI CỦA BA VÒNG
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TC-37 vẽ biểu đồ ngay trong từng khối. TC-38 gom thành BA khu riêng có đánh số ("Biểu đồ 1 ·
 *  Dòng tiền"...). TC-40 đưa trở lại vào từng khối. Ba vòng, và bài học đáng ghi:
 *
 *  Gom biểu đồ ra một khu riêng nghe rất hợp lý — "khu biểu đồ" là thứ mọi bảng điều hành đều
 *  có. Nhưng trên bản chạy thật nó đẻ ra đúng cái bệnh mà cả hệ này đang chữa: con số nằm ở khối,
 *  hình nằm ở khu, và người đọc phải cuộn qua lại để ghép hai thứ vốn là MỘT. Anh Tuấn nhìn phát
 *  hiện ngay — "các mục lặp lại khá nhiều".
 *
 *  Nên luật bây giờ: MỘT CON SỐ — MỘT CHỖ — MỘT HÌNH. Tệp này không còn dựng khu nào cả; nó nhận
 *  dữ liệu máy chủ và trả về ĐÚNG những biểu đồ vẽ được, để mỗi khối tự bày cái của mình.
 *
 *  Tên TỆP giữ nguyên vì đổi tên tệp trong luồng đẩy hiện tại là xoá một tệp và thêm một tệp —
 *  rủi ro hơn hẳn giá trị của một cái tên đẹp.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TỆP NÀY KHÔNG TÍNH GÌ CẢ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9: Claude viết cấu trúc và phép tính ở MÁY CHỦ, màn hình chỉ bày. Mọi con số dưới
 *  đây đã có sẵn trong /api/v1/dashboard; tệp này chỉ chọn trường nào vào biểu đồ nào. Chỗ duy
 *  nhất có phép tính là chuyển tỉ lệ nộp thành hai vế của một tổng, và chỗ ấy ghi rõ tại chỗ.
 *
 *  BIỂU ĐỒ CHƯA ĐỦ SỐ THÌ TRẢ VỀ `null`, không trả một khung rỗng. Khối nhận `null` thì chỉ hiện
 *  ô số của nó — vì bản thân ô số ĐÃ nói "Chưa kết nối" kèm bộ phận và cửa nhập. Bày thêm một
 *  khung xám ghi lại đúng điều ấy là nói hai lần cùng một chuyện, và đó là cái anh Tuấn bảo bỏ.
 */
import {
  BieuDoThanh, BieuDoCoCau, duVeCoCau,
  type Thanh, type Phan,
} from "@/components/BieuDo";

/* ─────────────────────────── ĐỌC DỮ LIỆU MÁY CHỦ ─────────────────────────── */

/* TC-42 (16/9/2026) – hai biểu đồ CỘT theo kỳ (doanh thu, lợi nhuận) RỜI khỏi tệp này.
   Chúng thành hai Ô LỚN có ô chọn Tháng / Quý / Năm, dựng ở components/KhoiSauO.tsx. Hàm đổi chuỗi
   xu hướng thành dãy điểm đi theo chúng sang đó — giữ lại một bản ở đây là để hai bản cùng đọc một
   cấu trúc dữ liệu, và ngày một bản sửa mà bản kia quên là ngày hai biểu đồ nói khác nhau.
   Tệp này nay chỉ còn các biểu đồ CƠ CẤU và XẾP HẠNG. */

/** Bảy nhóm hạn của máy chủ → bảy thanh ngang. Thứ tự lấy theo KHUNG, không theo thứ tự máy chủ
 *  trả về: khung là thứ tự hạn gần → xa, còn đối tượng JSON thì không hứa thứ tự nào.
 *
 *  TC-45 · THANH NGANG THAY CHO THANH CƠ CẤU MỘT VẠCH, và cũng thay luôn bảy ô số vuông.
 *  ═════════════════════════════════════════════════════════════════════════════════════════════
 *  Bản cũ bày CẢ HAI: năm ô số vuông ở trên, rồi một thanh chia khúc ở dưới — hai bức tranh của
 *  cùng một hàng số, đúng thứ luật "MỘT CON SỐ · MỘT CHỖ · MỘT HÌNH" (TC-40) cấm. Thanh chia khúc
 *  trả lời "bao nhiêu phần trăm tiền đã quá hạn"; ô số vuông trả lời "nhóm ấy bao nhiêu đồng". Bảy
 *  thanh ngang trả lời CẢ HAI trong một hình: con số nằm cuối mỗi thanh, còn bề dài so với nhau
 *  cho ngay tỉ lệ — mà không bắt mắt nhảy bảy lần rồi tự cộng nhẩm.
 *
 *  `xep={false}` là bắt buộc và là chỗ dễ quên nhất: bảy nhóm này xếp theo THỜI GIAN (quá hạn →
 *  dài hạn), không theo độ lớn. Để bộ biểu đồ tự xếp nhiều-trước thì trục thời gian biến mất, và
 *  "quá hạn" có thể rơi xuống giữa bảng — lúc ấy không ai đọc ra được nợ đang dồn về phía nào.
 */
function thanhTu(khung: { nhan: string; trang_thai?: boolean }[],
                 ds: Record<string, number | null> | null | undefined): Thanh[] {
  const s = ds || {};
  return khung.map((k) => ({
    ten: k.nhan,
    gt: s[k.nhan] === null || s[k.nhan] === undefined ? null : Number(s[k.nhan]),
    trang_thai: k.trang_thai,
  }));
}

/* MỘT khung cho cả hai hướng — anh Tuấn chốt 16/9/2026. Nhãn phải khớp TỪNG CHỮ với `MOC` ở
   backend/app/services/han_cong_no.py. */
const KHUNG_HAN = [
  { nhan: "Quá hạn", trang_thai: true }, { nhan: "1 tuần" }, { nhan: "2 tuần" },
  { nhan: "4 tuần" }, { nhan: "2 tháng" }, { nhan: "3 tháng" }, { nhan: "Dài hạn" },
];

/* ─────────────────────────── DỰNG BIỂU ĐỒ CHO TỪNG KHỐI ─────────────────────────── */

/** Tập biểu đồ của màn hình 01. Mỗi trường là một phần tử JSX, hoặc `null` khi chưa đủ số để vẽ.
 *  Nơi gọi chỉ việc `{bd.phai_thu}` — không phải chép lại điều kiện vẽ lần thứ hai. */
export type BoBieuDo = {
  phai_thu: any; phai_tra: any;
  kd_le: any; kd_doan: any;
  bao_cao_ngay: any;
};

export function bieuDoCua(sec: any): BoBieuDo {
  const thu = thanhTu(KHUNG_HAN, sec?.phai_thu_theo_han);
  const tra = thanhTu(KHUNG_HAN, sec?.phai_tra_theo_han);
  const le: Thanh[] = (sec?.kd_le || []).map((r: any) => ({
    ten: r.sales, gt: r.revenue === null || r.revenue === undefined ? null : Number(r.revenue),
  }));
  const doan: Thanh[] = (sec?.kd_doan?.rows || []).map((r: any) => ({
    ten: r.sales,
    gt: r.profit_share === null || r.profit_share === undefined ? null : Number(r.profit_share),
  }));

  /* Báo cáo ngày: máy chủ trả TỈ LỆ nộp, không trả hai vế. Tách nó thành "đã nộp" và "chưa nộp"
     là phép tính DUY NHẤT của tệp này — và nó chỉ là 1 trừ đi tỉ lệ ấy, không phải một con số
     nghiệp vụ mới. Ghi ra đây để lần sau không ai tưởng màn hình tự tính doanh thu. */
  const tyLe = sec?.bao_cao_ngay?.ty_le_nop;
  const bcNgay: Phan[] = typeof tyLe === "number"
    ? [{ ten: "Đã nộp", gt: tyLe }, { ten: "Chưa nộp", gt: 1 - tyLe, trang_thai: true }]
    : [{ ten: "Đã nộp", gt: null }, { ten: "Chưa nộp", gt: null }];

  /* TC-49 · KHÔNG CÒN CỔNG `duVe… ? … : null` Ở ĐÂY.
   *
   *  Bản cũ: chưa đủ số thì trả `null`, khối bên ngoài không vẽ gì, và cả màn hình co lại thành
   *  mấy đoạn văn xuôi. Anh Tuấn mở trang thật ngày 17/9: "trên màn hình chưa có biểu đồ".
   *
   *  Phép quyết "đủ số hay chưa" KHÔNG bị bỏ — nó chuyển vào trong chính bộ biểu đồ, nơi nó vốn
   *  thuộc về (`BieuDoThanh`/`BieuDoCot` tự gọi `duVeThanh`/`duVeCot` rồi trả `BieuDoRong`). Nhờ
   *  vậy chỉ còn MỘT chỗ quyết, và khung rỗng giữ đúng hình dáng của hình thật.
   *
   *  Hệ quả phải nói ra: nơi gọi không còn phân biệt được "có hình" với "không có hình" bằng cách
   *  kiểm `null`. Đó là chủ ý — luôn luôn có hình, chỉ là hình rỗng hay hình đầy.
   */
  return {
    // 29/9/2026: bỏ câu chân và dòng phụ — khối Phải thu · Phải trả chỉ còn biểu đồ và con số.
    phai_thu: <BieuDoThanh ten="Theo hạn" ds={thu} dinh_dang="tien" xep={false}
      cua="/cong-no" cua_ten="Xem chi tiết" />,
    phai_tra: <BieuDoThanh ten="Theo hạn" ds={tra} dinh_dang="tien" xep={false}
      cua="/cong-no?tab=tra" cua_ten="Xem chi tiết" />,
    kd_le: <BieuDoThanh ten="Xếp hạng theo nhân viên" ds={le} dinh_dang="tien"
      ai="Kinh doanh" cua="/bookings" cua_ten="Cửa nhập booking" />,
    kd_doan: <BieuDoThanh ten="Xếp hạng theo nhân viên" ds={doan} dinh_dang="tien"
      ai="Kinh doanh" cua="/bookings" cua_ten="Cửa nhập booking" />,
    bao_cao_ngay: duVeCoCau(bcNgay)
      ? <BieuDoCoCau ten="Tỉ lệ nộp" ds={bcNgay} dinh_dang="phan_tram" />
      : null,
  };
}
