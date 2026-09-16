"use client";
/** BA KHU BIỂU ĐỒ TRÊN MÀN HÌNH 01 — anh Tuấn chốt 15/9/2026.
 *
 *  Anh Tuấn gửi mấy mẫu bảng điều hành (Power BI, dashboard bán hàng) và chốt hai điều: biểu đồ
 *  dựng "đầy đủ — trục, lưới, nhãn số, chú giải", và chia làm ba nhóm:
 *
 *      Khu 1 · Dòng tiền              — tiền vào, tiền ra, tiền đang kẹt
 *      Khu 2 · Doanh thu & Lợi nhuận  — kết quả kinh doanh
 *      Khu 3 · Nhân sự & Quản trị nội bộ — việc tồn, tiến độ nộp báo cáo
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  TỆP NÀY KHÔNG TÍNH GÌ CẢ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Ranh giới 09/9: Claude viết cấu trúc và phép tính ở MÁY CHỦ, màn hình chỉ bày. Mọi con số dưới
 *  đây đã có sẵn trong /api/v1/dashboard; tệp này chỉ chọn trường nào vào biểu đồ nào. Không chỗ
 *  nào cộng, trừ hay suy ra một con số nghiệp vụ mới — chỗ duy nhất có phép tính là chuyển tỉ lệ
 *  nộp thành hai phần của một tổng, và phần ấy ghi rõ ngay tại chỗ.
 *
 *  BIỂU ĐỒ NÀO CHƯA CÓ NGUỒN THÌ VẪN DỰNG, ở dạng ô rỗng có lời. Giấu nó đi thì đến lúc nối số
 *  không ai nhớ còn thiếu cái gì; mà bày một khung xám không lời thì người đọc kết luận hệ thống
 *  hỏng. Ô rỗng của bộ biểu đồ luôn nói: chưa vẽ được VÌ SAO, AI nạp số, và cửa nhập ở ĐÂU.
 */
import { BieuDoCot, BieuDoThanh, BieuDoCoCau, type Diem, type Thanh, type Phan } from "@/components/BieuDo";

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

function Khu({ so, ten, mo, children }: { so: number; ten: string; mo: string; children: any }) {
  return (
    <section className="mh01-khu" id={`khu-bieu-do-${so}`}>
      <div className="mh01-khu-dau">
        <h3>Biểu đồ {so} · {ten}</h3>
        <p className="muted">{mo}</p>
      </div>
      <div className="mh01-bd-luoi">{children}</div>
    </section>
  );
}

/* ─────────────────────────── BA KHU ─────────────────────────── */

export default function BaKhuBieuDo({ sec, approvals }: { sec: any; approvals?: any[] }) {
  const xh = sec?.xu_huong || {};

  /* ══ KHU 1 · DÒNG TIỀN ══
     Hai khối công nợ hôm nay chưa có sổ, nên hai biểu đồ đầu ra ô rỗng có lời — đúng hiện trạng,
     và câu chữ chỉ thẳng Kế toán cùng cửa nhập. Biểu đồ thứ ba có số thật: số tour chờ quyết toán
     là tiền đã bán mà chưa chốt sổ được. */
  const khu1 = (
    <Khu so={1} ten="Dòng tiền"
      mo="Tiền sắp vào, tiền sắp ra, và tiền đang kẹt ở chuyến chưa chốt sổ.">
      <BieuDoCoCau ten="Phải thu theo hạn thanh toán" phu="5 nhóm không trùng nhau"
        ds={phanTu(KHUNG_THU, sec?.phai_thu_theo_han)}
        ai="Kế toán" cua="/ra-soat-cot-tien" cua_ten="Cửa nhập công nợ phải thu"
        chan="Nhóm Quá hạn mang màu cảnh báo vì nó là TRẠNG THÁI — tiền đã trễ, không phải nấc gần nhất của thang hạn còn lại." />
      <BieuDoCoCau ten="Phải trả theo hạn thanh toán" phu="5 nhóm không trùng nhau"
        ds={phanTu(KHUNG_TRA, sec?.phai_tra_theo_han)}
        ai="Kế toán" cua="/nha-cung-cap" cua_ten="Cửa nhập công nợ phải trả"
        chan="Phải trả quá hạn theo dõi riêng ở khối 05b, KHÔNG nằm trong năm nhóm này — gộp vào là đếm hai lần." />
      <BieuDoCot ten="Tour chờ quyết toán" phu="cuối mỗi tháng đã đóng" dinh_dang="dem"
        diem={diemTu(xh.tour_cho_quyet_toan)}
        ai="Kế toán" cua="/reports" cua_ten="Bản lưu chỉ tiêu theo kỳ"
        chan="Đây là số ĐẾM TẠI MỘT THỜI ĐIỂM, không tính lại được cho kỳ đã qua — kỳ nào không ai chụp bản lưu thì vĩnh viễn không biết." />
    </Khu>
  );

  /* ══ KHU 2 · DOANH THU & LỢI NHUẬN ══
     Khu có nhiều số thật nhất hôm nay: hai chuỗi tháng tính lại được từ sổ quyết toán, và hai
     bảng xếp hạng nhân viên lấy thẳng từ khối Kinh doanh. */
  const le: Thanh[] = (sec?.kd_le || []).map((r: any) => ({
    ten: r.sales, gt: r.revenue === null || r.revenue === undefined ? null : Number(r.revenue),
  }));
  const doan: Thanh[] = (sec?.kd_doan?.rows || []).map((r: any) => ({
    ten: r.sales,
    gt: r.profit_share === null || r.profit_share === undefined ? null : Number(r.profit_share),
  }));

  const khu2 = (
    <Khu so={2} ten="Doanh thu & Lợi nhuận"
      mo="Kết quả kinh doanh theo tháng đã đóng, và xếp hạng trong tháng này.">
      <BieuDoCot ten="Doanh thu tháng" phu="6 tháng đã đóng gần nhất"
        diem={diemTu(xh.doanh_thu_thang)}
        ai="Kế toán" cua="/reports" cua_ten="Báo cáo quyết toán"
        chan="Tháng đang chạy KHÔNG nằm trong biểu đồ: đặt một tháng mới đi nửa đường cạnh các tháng đủ ngày thì cột cuối luôn thấp và đường xu hướng luôn trông như đang lao dốc." />
      <BieuDoCot ten="Lợi nhuận trước thuế" phu="6 tháng đã đóng gần nhất"
        diem={diemTu(xh.ln_ke_toan_thang)}
        ai="Kế toán" cua="/reports" cua_ten="Báo cáo quyết toán"
        chan="Cột dưới vạch 0 là tháng lỗ. Lỗ ít đi so với tháng trước vẫn tính là TĂNG — so sánh chia cho trị tuyệt đối." />
      <BieuDoThanh ten="Doanh thu theo nhân viên · phòng Lẻ" phu="chuyến đã quyết toán trong tháng"
        ds={le} dinh_dang="tien"
        ai="Kinh doanh Lẻ" cua="/sales-reports?mang=le" cua_ten="Báo cáo bán hàng phòng Lẻ"
        chan="Phòng Lẻ hưởng theo MỐC DOANH THU, nên bảng này là doanh thu." />
      <BieuDoThanh ten="Lợi nhuận chia · phòng Đoàn" phu="chuyến đã quyết toán trong tháng"
        ds={doan} dinh_dang="tien"
        ai="Kinh doanh Đoàn" cua="/sales-reports?mang=doan" cua_ten="Báo cáo bán hàng phòng Đoàn"
        chan="Phòng Đoàn hưởng theo CHIA LỢI NHUẬN, không theo mốc doanh thu như phòng Lẻ — nên bảng này là lợi nhuận, không so thẳng được với bảng bên cạnh. Số chính thức nằm ở bảng lương." />
      <BieuDoCot ten="Tour đang bán" phu="cuối mỗi tháng đã đóng" dinh_dang="dem"
        diem={diemTu(xh.tour_dang_ban)}
        ai="Điều hành" cua="/tours" cua_ten="Danh sách tour"
        chan="Số đếm tại một thời điểm — cần bản lưu chỉ tiêu mỗi cuối kỳ mới có chuỗi." />
    </Khu>
  );

  /* ══ KHU 3 · NHÂN SỰ & QUẢN TRỊ NỘI BỘ ══ */
  const bp: Thanh[] = (sec?.ton_dong_bo_phan || []).map((r: any) => ({
    ten: r.bo_phan,
    gt: r.ho_so_qua_han === null || r.ho_so_qua_han === undefined ? null : Number(r.ho_so_qua_han),
  }));
  if (sec?.ton_dong_chua_ro_bo_phan) {
    bp.push({ ten: "Chưa rõ bộ phận", gt: Number(sec.ton_dong_chua_ro_bo_phan.so), nhan_phu: true });
  }

  const daNop = sec?.tien_do_so_da_nop;
  const thieu = sec?.tien_do_so_thieu;
  const tienDo: Phan[] = [
    { ten: "Đã nộp", gt: daNop === null || daNop === undefined ? null : Number(daNop) },
    { ten: "Còn thiếu", gt: thieu === null || thieu === undefined ? null : Number(thieu), trang_thai: true },
  ];

  /* Báo cáo ngày: máy chủ trả TỈ LỆ nộp, không trả hai vế. Tách nó thành "đã nộp" và "chưa nộp"
     là phép tính DUY NHẤT của tệp này — và nó chỉ là 1 trừ đi tỉ lệ ấy, không phải một con số
     nghiệp vụ mới. Ghi ra đây để lần sau không ai tưởng màn hình tự tính doanh thu. */
  const tyLe = sec?.bao_cao_ngay?.ty_le_nop;
  const bcNgay: Phan[] = typeof tyLe === "number"
    ? [{ ten: "Đã nộp", gt: tyLe }, { ten: "Chưa nộp", gt: 1 - tyLe, trang_thai: true }]
    : [{ ten: "Đã nộp", gt: null }, { ten: "Chưa nộp", gt: null }];

  const khu3 = (
    <Khu so={3} ten="Nhân sự & Quản trị nội bộ"
      mo="Việc đang tồn ở đâu, và các bộ phận có nộp báo cáo đúng hạn không.">
      <BieuDoThanh ten="Tồn đọng theo bộ phận" phu="mỗi hồ sơ chỉ tính một lần"
        ds={bp} dinh_dang="dem"
        ai="Công nghệ thông tin" cua="/alerts" cua_ten="Trang cảnh báo"
        chan={<>Thanh dài nhất là bộ phận đang tồn nhiều nhất, <b>không</b> phải bộ phận vượt ngưỡng nào — chưa có ngưỡng nào được khai. Dòng <b>Chưa rõ bộ phận</b> mang màu khác vì nó không phải một phòng.</>} />
      <BieuDoCoCau ten={`Tiến độ báo cáo kỳ${sec?.tien_do_ten_ky ? " · " + sec.tien_do_ten_ky : ""}`}
        phu="kỳ vừa đóng" ds={tienDo} dinh_dang="dem"
        ai="Các phòng ban" cua="/reports" cua_ten="Trang báo cáo"
        chan="Đo KỲ VỪA ĐÓNG, không đo kỳ đang chạy: kỳ đang chạy thì hồ sơ chưa tới hạn nộp, tính vào là bộ phận nào cũng trông như đang trễ." />
      <BieuDoCoCau ten="Báo cáo ngày (Điều 12) · tháng này" phu="tỉ lệ nộp trên tổng lượt phải nộp"
        ds={bcNgay} dinh_dang="phan_tram"
        ai="Các phòng ban" cua="/reports" cua_ten="Tổng hợp báo cáo ngày"
        chan={sec?.bao_cao_ngay
          ? `${sec.bao_cao_ngay.nhan_su} nhân sự · ${sec.bao_cao_ngay.ngay_lam_viec} ngày làm việc · thiếu 2 ngày liên tiếp: ${sec.bao_cao_ngay.thieu_2_ngay}`
          : undefined} />
    </Khu>
  );

  return (
    <div id="ba-khu-bieu-do">
      {/* Ba khu này KHÔNG có trong bản vẽ V1.4 — nói thẳng ra, đúng như phần khối riêng của VTOS
          ở cuối trang. Bản vẽ chốt bố cục tám khối; biểu đồ là việc anh Tuấn giao thêm sau. */}
      <hr className="mh01-ngan" />
      <h2 className="mh01-them">Biểu đồ điều hành — thêm ngoài bản vẽ (anh Tuấn giao 15/9/2026)</h2>
      {khu1}
      {khu2}
      {khu3}
      <p className="muted">
        Ba khu này chỉ VẼ LẠI số đã có ở các khối bên trên, không tính thêm con số nào. Biểu đồ nào
        còn ô rỗng là chỗ chưa ai nạp số — ô rỗng ghi rõ bộ phận và cửa nhập.
      </p>
    </div>
  );
}
