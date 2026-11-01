"use client";
// TR-1 · kh.vietourist.vn/tours/don/<mã> — đơn tour online: thanh toán QR / thẻ, cổng SePay trả về đây, tải invoice.
import TrangRieng from "@/components/cong/TrangRieng";

export default function Trang({ params }: { params: { ma: string } }) { return <TrangRieng dang="tours" don={decodeURIComponent(params.ma)} />; }
