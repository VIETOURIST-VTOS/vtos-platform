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
  return <KhungRieng dang={dang} toi={toi} xong={xong}>
    {!xong ? <p style={{ padding: 24 }}>Đang tải…</p>
      : dang === "hotel" ? <section aria-label="Khách sạn"><KhachSanVtd rieng moId={so} ten={ten} lienHe={lienHe} /></section>
      : dang === "restaurant" ? <section aria-label="Nhà hàng & ẩm thực">
        <NhaHangAgoda moId={so} ten={ten} lienHe={lienHe} coSdt={!!toi?.dien_thoai} sdtCho={toi?.dien_thoai || ""} doiTac={toi?.loai === "doi_tac"} /></section>
      : <ToursAgoda toi={toi} moId={so} moDon={don} />}
  </KhungRieng>;
}
