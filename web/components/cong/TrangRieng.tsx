"use client";
/* KS-16q · nội dung ba trang riêng (Chủ tịch duyệt bản xem thử 01/11/2026): /hotel = giao diện khách sạn kiểu Agoda
   (KS-16p), /restaurant = nhà hàng kiểu Agoda + đặt bàn (AT-2, DT-2), /tours = tour + gửi yêu cầu. Dùng lại đúng các màn
   đã có, chỉ đặt vào KhungRieng. Mã trong app/kham-pha/*; tên miền cổng viết lại /hotel → /kham-pha/hotel. */
import { emailThat, type TrangRieng as Loai } from "@/lib/cong";
import KhungRieng, { useToiRieng } from "./KhungRieng";
import KhachSanVtd from "./KhachSanVtd";
import NhaHangAgoda from "./NhaHangAgoda";   // AT-2: nhà hàng kiểu Agoda (thay Khám phá ẩm thực trên trang riêng)
import ToursAgoda from "./ToursAgoda";   // TR-1: tour kiểu Agoda + đặt online (thay danh sách tour + gửi yêu cầu KS-16q)

export default function TrangRieng({ dang, id, don }: { dang: Loai; id?: string; don?: string }) {
  const { toi, xong } = useToiRieng();
  const so = id && /^\d+$/.test(id) ? Number(id) : undefined;
  const ten = toi?.ho_ten || "";
  // KS-19e: /cong/toi trả email ĐÃ CHE (vi•••@gmail.com) — không điền bản che vào ô liên hệ (trước đây hiện ở ô «Số điện thoại / Zalo»).
  const lienHe = toi?.dien_thoai || emailThat(toi?.email);
  // TR-19 · MÀN TOUR KHÔNG CÒN ĐỢI CÂU HỎI «AI ĐANG ĐĂNG NHẬP» NỮA.
  // Đo trang HC001 trên bản chạy sau TR-18: cửa /cong/toi mất 371 ms và chạy TRƯỚC, nên mãi
  // tới 724 ms trang mới bắt đầu hỏi dữ liệu tour — gần một nửa thời gian còn lại là ngồi đợi
  // một câu hỏi không liên quan gì tới tour. Cửa ấy gắn với từng người nên không đệm được,
  // nhưng không có lý do gì nó phải chạy trước: khách vào đây để XEM tour, và xem tour vốn
  // KHÔNG cần đăng nhập (KS-16q). Dựng màn tour ngay, phiên về lúc nào thì điền lúc ấy —
  // ToursAgoda nhận `toi` đổi từ rỗng sang có và tự điền nốt ô liên hệ CÒN TRỐNG.
  //
  // Hai màn kia (khách sạn, nhà hàng) GIỮ NGUYÊN lối cũ: chúng nhận `ten` và `lienHe` dưới
  // dạng chuỗi dựng sẵn, chưa có đường điền bù khi phiên về muộn. Sửa mò là làm hỏng ô liên
  // hệ của khách. Đo xong từng màn rồi mở tiếp, không mở cả ba theo cảm giác.
  return <KhungRieng dang={dang} toi={toi} xong={xong}>
    {dang === "tours" ? <ToursAgoda toi={toi} moId={so} moDon={don} />
      : !xong ? <p style={{ padding: 24 }}>Đang tải…</p>
      : dang === "hotel" ? <section aria-label="Khách sạn"><KhachSanVtd rieng moId={so} ten={ten} lienHe={lienHe} /></section>
      : <section aria-label="Nhà hàng & ẩm thực">
        <NhaHangAgoda moId={so} ten={ten} lienHe={lienHe} coSdt={!!toi?.dien_thoai} sdtCho={toi?.dien_thoai || ""} doiTac={toi?.loai === "doi_tac"} /></section>}
  </KhungRieng>;
}
