"use client";
/* KH-2 · Khung thanh toán QR chuyển khoản trong chi tiết đơn (Chủ tịch duyệt 26/10/2026).
   Số tiền, nội dung và tài khoản đều do MÁY CHỦ trả về; trang chỉ vẽ mã QR từ chuỗi VietQR. */
import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { goiCong } from "@/lib/cong";

const tien = (n: number) => `${Math.round(n).toLocaleString("vi-VN")} đ`;

export default function QrThanhToan({ ma }: { ma: string }) {
  const [muc, setMuc] = useState<string>("");
  const [q, setQ] = useState<any>(null);
  const [anh, setAnh] = useState("");
  const [loi, setLoi] = useState("");
  const [chep, setChep] = useState("");
  useEffect(() => {
    setLoi(""); setAnh("");
    goiCong(`/khach/don/${encodeURIComponent(ma)}/qr${muc ? `?muc=${muc}` : ""}`)
      .then((r) => { setQ(r); return QRCode.toDataURL(r.payload, { margin: 1, width: 240, errorCorrectionLevel: "M" }); })
      .then(setAnh).catch((x) => { setQ(null); setLoi(x.message || "Chưa tạo được mã QR"); });
  }, [ma, muc]);
  const chepChu = async (v: string, nhan: string) => {
    try { await navigator.clipboard.writeText(v); setChep(`Đã chép ${nhan}`); } catch { setChep("Trình duyệt chặn chép — hãy bôi đen để chép"); }
  };
  if (loi) return <div className="v3-notice warn"><span>{loi}</span></div>;
  if (!q) return <p>Đang tạo mã QR…</p>;
  return (<div className="kh-qr">
    <div className="v31-service-tabs kh-qr-muc" role="group" aria-label="Số tiền thanh toán">
      {q.coc > 0 && <button type="button" className="cursor-interaction" aria-pressed={q.muc === "coc"} onClick={() => setMuc("coc")}><span>Cọc · {tien(q.coc)}</span></button>}
      <button type="button" className="cursor-interaction" aria-pressed={q.muc === "du"} onClick={() => setMuc("du")}><span>Toàn bộ còn lại · {tien(q.con_lai)}</span></button>
    </div>
    <div className="kh-qr-than">
      {anh ? <img src={anh} alt={`Mã QR chuyển ${tien(q.so_tien)} cho đơn ${q.ma}`} width={200} height={200} /> : <div style={{ width: 200, height: 200 }} />}
      <dl className="v3-stat-rows">
        <div><dt>Ngân hàng</dt><dd>{q.ngan_hang}</dd></div>
        <div><dt>Số tài khoản</dt><dd>{q.so_tk} <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => chepChu(q.so_tk, "số tài khoản")}><span>Chép</span></button></dd></div>
        <div><dt>Chủ tài khoản</dt><dd>{q.chu_tk}</dd></div>
        <div><dt>Số tiền</dt><dd>{tien(q.so_tien)}</dd></div>
        <div><dt>Nội dung</dt><dd>{q.noi_dung} <button type="button" className="v3-button v3-quiet cursor-interaction" onClick={() => chepChu(q.noi_dung, "nội dung")}><span>Chép</span></button></dd></div>
      </dl>
    </div>
    {chep && <small>{chep}</small>}
    <div className="v3-notice warn"><span>Quét bằng ứng dụng ngân hàng và GIỮ NGUYÊN nội dung «{q.noi_dung}». {q.tu_khop
      ? "Trả toàn bộ: hệ thống đối chiếu và ghi nhận tự động khi tiền về."
      : "Trả cọc: kế toán xác nhận khi tiền về."} Đơn chỉ ghi «đã thu» sau khi được xác nhận.</span></div>
  </div>);
}
