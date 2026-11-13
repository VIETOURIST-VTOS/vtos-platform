"use client";
import BanKdKhung, { BangThucBan, HangTien, OSo, so, type Tab } from "@/components/BanKdKhung";

/** R5-7 · BÀN LÀM VIỆC CHUYÊN VIÊN KINH DOANH — Chủ tịch duyệt bản xem trước 13/11/2026.
 *  CHỈ SỐ CỦA CHÍNH MÌNH (Chủ tịch: «chỉ của mình») — máy chủ không trả dòng của người khác.
 *  Lương của tôi đọc Phiếu lương của tôi; «Đề xuất gửi Ban lãnh đạo» TẠM DÙNG Báo cáo công việc (Chủ tịch
 *  13/11/2026). Chỉ đọc; mọi thẻ mở màn gốc ngay trong bàn. Khung chung: components/BanKdKhung.tsx. */
const TAB: Tab[] = [
  { ma: "tq", ten: "Tổng quan", the: [] },
  { ma: "khach", ten: "Khách của tôi", tieu_de: "Khách của tôi", the: [
    { ten: "Khách hàng & lead", mo_ta: "Lead được giao, lịch hẹn gọi lại", toi: "/leads?tab=leads" },
    { ten: "Hộp thư đa kênh", mo_ta: "Khách nhắn đang chờ trả lời", toi: "/inbox" },
    { ten: "Báo giá", mo_ta: "Soạn báo giá gửi khách", toi: "/bao-gia?mang=kd_le" },
    { ten: "Bàn bán tour lẻ", mo_ta: "Chuyến còn chỗ, giá bán", toi: "/ban-tour-le" }] },
  { ma: "bk", ten: "Booking của tôi", tieu_de: "Booking của tôi", the: [
    { ten: "Booking & bảo lưu", mo_ta: "Giữ chỗ, cọc, thu tiền, hủy", toi: "/bookings?mang=le" },
    { ten: "Yêu cầu đặt dịch vụ", mo_ta: "Gửi Điều hành, theo dõi hạn xử lý", toi: "/requests?mang=le" },
    { ten: "Dịch vụ lẻ", mo_ta: "Visa, vé, phòng, xe", toi: "/non-package" }] },
  { ma: "cs", ten: "Chăm sóc", tieu_de: "Chăm sóc khách của tôi", the: [
    { ten: "Chăm sóc sau tour", mo_ta: "Phiếu tới hạn, ghi kết quả liên hệ", toi: "/cham-soc" },
    { ten: "Phản hồi & khiếu nại", mo_ta: "Hồ sơ khách của tôi", toi: "/khieu-nai" }] },
  { ma: "luong", ten: "Lương & đề xuất", tieu_de: "Lương & đề xuất", the: [
    { ten: "Phiếu lương của tôi", mo_ta: "Lương, thưởng, hoa hồng — chỉ mình thấy", toi: "/phieu-luong" },
    { ten: "Đề xuất gửi Ban lãnh đạo", mo_ta: "Tạm gửi qua Báo cáo công việc", toi: "/reports" },
    { ten: "Đơn nghỉ phép của tôi", mo_ta: "Gửi và theo dõi đơn", toi: "/cham-cong" },
    { ten: "Đề nghị mua", mo_ta: "Đề nghị mua vật dụng", toi: "/de-nghi-mua" }] },
  { ma: "bc", ten: "Báo cáo", tieu_de: "Báo cáo", the: [
    { ten: "Báo cáo công việc của tôi", mo_ta: "Báo cáo ngày / tuần", toi: "/reports" },
    { ten: "Doanh thu & chỉ tiêu của tôi", mo_ta: "Từng booking tính chỉ tiêu", noi: "doanh-thu" }] },
];

export default function BanNvKd() {
  return <BanKdKhung ten="Bàn làm việc Chuyên viên Kinh doanh" tabs={TAB} phamVi={() => "Số của riêng tôi"}
    tongQuan={({ d, dt, moToi }) => {
      const th = d?.the || {};
      return <>
        {/* R5-14: bỏ ô «Doanh thu của tôi» và «Khách còn nợ» (trùng khối Doanh thu – Chỉ tiêu và Phải thu). */}
        <p className="g5-nhom">VIỆC CẦN XỬ LÝ</p>
        <div className="g5-dai3">
          <OSo nhan="Lead mới chưa liên hệ" nong v={d ? so(th.lead_moi?.so) : undefined} phu="Được giao cho tôi" lk="Khách của tôi" bam={() => moToi("/leads?tab=leads")} />
          <OSo nhan="Chăm sóc quá hạn" nong v={d ? so(th.cham_soc_qua_han?.so) : undefined} phu={d ? `${so(th.cham_soc_qua_han?.toi_han)} phiếu tới hạn` : ""} lk="Chăm sóc" bam={() => moToi("/cham-soc")} />
          <OSo nhan="Booking tháng này" v={d ? so(th.booking_moi?.so) : undefined} phu={d ? `${so(th.booking_moi?.chua_coc)} chưa cọc` : ""} lk="Booking" bam={() => moToi("/bookings?mang=le")} />
        </div>
        <BangThucBan ds={d?.thuc_ban} moToi={moToi} />
        <p className="g5-nhom">TIỀN · THÁNG NÀY</p>
        <HangTien duong="/ban-kd-le/vai/nhip" coToi pt={d?.phai_thu} moToi={moToi} />
        <div className="g5-hai">
          <section className="g5-khoi" aria-label="Việc hôm nay">
            <div className="g5-dau"><h2>Việc hôm nay</h2><span>Cũng hiện ở nút Công việc</span></div>
            {!d ? <p className="g5-nho">Đang đọc số…</p> : (d.viec || []).length === 0 ? <p className="g5-nho">Không có việc tồn.</p> :
              <ul className="g5-ds">{d.viec.map((v: any) => (
                <li key={v.ma}><span><b>{v.tieu_de}</b><small>{v.mo_ta}</small></span>
                  <button type="button" className="g5-cua" onClick={() => moToi(v.toi)}>Mở →</button></li>))}</ul>}
          </section>
          <section className="g5-khoi" aria-label="Lương, đề xuất và báo cáo">
            <div className="g5-dau"><h2>Lương, đề xuất &amp; báo cáo</h2><span>Mở ngay trong bàn</span></div>
            <ul className="g5-ds">
              <li><span><b>Phiếu lương của tôi</b><small>Lương, thưởng, hoa hồng — chỉ mình thấy</small></span><button type="button" className="g5-cua" onClick={() => moToi("/phieu-luong")}>Mở →</button></li>
              <li><span><b>Đề xuất gửi Ban lãnh đạo</b><small>Tạm gửi qua Báo cáo công việc</small></span><button type="button" className="g5-cua" onClick={() => moToi("/reports")}>Viết →</button></li>
              <li><span><b>Đơn nghỉ phép</b><small>Gửi và theo dõi đơn</small></span><button type="button" className="g5-cua" onClick={() => moToi("/cham-cong")}>Mở →</button></li>
            </ul>
          </section>
        </div>
      </>;
    }} />;
}
