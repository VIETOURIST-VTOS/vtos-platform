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
  BieuDoCot, BieuDoThanh, BieuDoCoCau, duVeCot, duVeThanh, duVeCoCau,
  type Diem, type Thanh, type Phan,
} from "@/components/BieuDo";

/* ─────────────────────────── ĐỌC DỮ LIỆU MÁY CHỦ ─────────────────────────── */

const tenKy = (ky: string) => { const [y, m] = String(ky).split("-"); return `${m}/${y}`; };

/** Một chuỗi xu hướng của máy chủ → dãy điểm của biểu đồ.
 *  `gia_tri === null` giữ nguyên là null: đó là kỳ CHƯA CÓ SỐ, và bộ biểu đồ vẽ nó thành ô trống
 *  đúng vị trí. Quy nó thành 0 ở đây là phá luật ngay tại cửa vào. */
function diemTu(xh: any): Diem[] {
  return (xh?.diem || []).map((d: any) => ({
    nhan: tenKy(d.ky),
    gt: d.gia_tri === null || d.gia_tri === undefined ? null : Number(d.gia_tri),
  }));
}

/** Năm nhóm hạn của máy chủ → các phần của một tổng. Thứ tự lấy theo KHUNG, không theo thứ tự
 *  máy chủ trả về: khung là thứ tự hạn gần → xa, còn đối tượng JSON thì không hứa thứ tự nào. */
function phanTu(khung: { nhan: string; trang_thai?: boolean }[],
                ds: Record<string, number | null> | null | undefined): Phan[] {
  const s = ds || {};
  return khung.map((k) => ({
    ten: k.nhan,
    gt: s[k.nhan] === null || s[k.nhan] === undefined ? null : Number(s[k.nhan]),
    trang_thai: k.trang_thai,
  }));
}

const KHUNG_THU = [
  { nhan: "Quá hạn", trang_thai: true }, { nhan: "2 tuần" }, { nhan: "4 tuần" },
  { nhan: "2 tháng" }, { nhan: "Dài hạn" },
];
const KHUNG_TRA = [
  { nhan: "1 tuần" }, { nhan: "2 tuần" }, { nhan: "4 tuần" },
  { nhan: "3 tháng" }, { nhan: "Dài hạn" },
];

/* ─────────────────────────── DỰNG BIỂU ĐỒ CHO TỪNG KHỐI ─────────────────────────── */

/** Tập biểu đồ của màn hình 01. Mỗi trường là một phần tử JSX, hoặc `null` khi chưa đủ số để vẽ.
 *  Nơi gọi chỉ việc `{bd.phai_thu}` — không phải chép lại điều kiện vẽ lần thứ hai. */
export type BoBieuDo = {
  phai_thu: any; phai_tra: any;
  doanh_thu: any; loi_nhuan: any;
  kd_le: any; kd_doan: any;
  bao_cao_ngay: any;
};

export function bieuDoCua(sec: any): BoBieuDo {
  const xh = sec?.xu_huong || {};

  const thu = phanTu(KHUNG_THU, sec?.phai_thu_theo_han);
  const tra = phanTu(KHUNG_TRA, sec?.phai_tra_theo_han);
  const dtThang = diemTu(xh.doanh_thu_thang);
  const lnThang = diemTu(xh.ln_ke_toan_thang);

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

  return {
    phai_thu: duVeCoCau(thu)
      ? <BieuDoCoCau ten="Cơ cấu theo hạn" ds={thu}
          chan="Nhóm Quá hạn mang màu cảnh báo vì nó là TRẠNG THÁI — tiền đã trễ, không phải nấc gần nhất của thang hạn còn lại." />
      : null,
    phai_tra: duVeCoCau(tra)
      ? <BieuDoCoCau ten="Cơ cấu theo hạn" ds={tra}
          chan="Phải trả quá hạn theo dõi riêng ở dưới, KHÔNG nằm trong năm nhóm này — gộp vào là đếm hai lần." />
      : null,
    doanh_thu: duVeCot(dtThang)
      ? <BieuDoCot ten="Doanh thu theo tháng" phu="6 tháng đã đóng gần nhất" diem={dtThang}
          chan="Tháng đang chạy KHÔNG nằm trong biểu đồ: đặt một tháng mới đi nửa đường cạnh các tháng đủ ngày thì cột cuối luôn thấp và đường xu hướng luôn trông như đang lao dốc." />
      : null,
    loi_nhuan: duVeCot(lnThang)
      ? <BieuDoCot ten="Lợi nhuận trước thuế theo tháng" phu="6 tháng đã đóng gần nhất" diem={lnThang}
          chan="Cột dưới vạch 0 là tháng lỗ. Lỗ ít đi so với tháng trước vẫn tính là TĂNG — so sánh chia cho trị tuyệt đối." />
      : null,
    kd_le: duVeThanh(le)
      ? <BieuDoThanh ten="Xếp hạng theo nhân viên" ds={le} dinh_dang="tien" />
      : null,
    kd_doan: duVeThanh(doan)
      ? <BieuDoThanh ten="Xếp hạng theo nhân viên" ds={doan} dinh_dang="tien" />
      : null,
    bao_cao_ngay: duVeCoCau(bcNgay)
      ? <BieuDoCoCau ten="Tỉ lệ nộp" ds={bcNgay} dinh_dang="phan_tram" />
      : null,
  };
}
