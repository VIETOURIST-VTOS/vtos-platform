"use client";
/* KS-11 · GỬI YÊU CẦU ĐẶT PHÒNG & ĐƠN CỦA TÔI (Chủ tịch chốt 29/10/2026).

   Bốn màn theo bố cục Agoda là đích đến khi Vietourist nối được Demand API. Màn này là thứ
   CHẠY ĐƯỢC NGAY, và nó đúng mô hình Fulfill Assisted hơn: khách khai nơi đến và ngày đi,
   Điều hành tra giá bên Agoda rồi chạy sáu bước, khách theo dõi đơn của mình.

   TRANG NÀY KHÔNG CÓ Ô SỐ THẺ, và sẽ không bao giờ có: theo Fulfill Assisted, «Agoda will
   directly charge your customers» — Vietourist không chạm vào tiền của khách.

   Mọi bảng chữ (trạng thái, tên ô) lấy từ máy chủ, không gõ lại ở đây. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";

const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const tien = (n?: number | null, dv?: string) =>
  n == null ? "" : new Intl.NumberFormat("vi-VN").format(Math.round(n)) + " " + (dv || "VND");

const VIEN = "1px solid rgba(128,128,128,0.28)";
const RONG = { flex: "1 1 150px", minWidth: 0 } as React.CSSProperties;

/* Bốn chặng khách đi qua. Chặng nào cũng nói rõ KHÁCH có phải làm gì không — đó là điều một
   dòng trạng thái phải trả lời, chứ không phải chỉ đặt tên cho tình trạng. */
const VIEC_CUA_KHACH: Record<string, string> = {
  da_gui: "Bạn không phải làm gì thêm — Vietourist đang nhận yêu cầu.",
  dang_tra_gia: "Vietourist đang tra giá với đối tác. Bạn không phải làm gì thêm.",
  co_gia: "Vietourist sẽ liên hệ bạn theo số đã ghi để xác nhận trước khi đặt.",
  da_dat: "Đã đặt xong. Giữ số xác nhận khách sạn để nhận phòng.",
  da_huy: "Đơn này đã huỷ.",
  that_bai: "Chưa đặt được. Vietourist sẽ liên hệ bạn.",
};

export default function YeuCauKhachSan() {
  const [don, setDon] = useState<any[] | null>(null);
  const [ten, setTen] = useState<Record<string, string>>({});
  const [f, setF] = useState({
    noi_den: "", ngay_nhan: "", ngay_tra: "", so_phong: 1, nguoi_lon: 2, tre_em: 0,
    nguoi_nhan_phong: "", lien_he: "", yeu_cau_them: "",
  });
  const [loi, setLoi] = useState(""); const [xong, setXong] = useState("");
  const [busy, setBusy] = useState(false); const [mo, setMo] = useState(false);

  const tai = useCallback(() => {
    goiCong("/khach-san/don-cua-toi")
      .then((r) => { setDon(r.don || []); setTen(r.trang_thai || {}); })
      .catch(() => setDon([]));
  }, []);
  useEffect(() => { tai(); }, [tai]);

  const gui = async () => {
    setBusy(true); setLoi(""); setXong("");
    try {
      const r = await goiCong("/khach-san/yeu-cau", {
        ...f, ngay_nhan: f.ngay_nhan || null, ngay_tra: f.ngay_tra || null,
        so_phong: Number(f.so_phong), nguoi_lon: Number(f.nguoi_lon), tre_em: Number(f.tre_em),
      });
      setXong(r.message);
      setF({ ...f, noi_den: "", yeu_cau_them: "" });
      setMo(false);
      tai();
    } catch (x: any) { setLoi(x.message); }
    setBusy(false);
  };

  return (<>
    <section className="v3-panel">
      <div className="v3-section-title"><h3>Gửi yêu cầu đặt phòng cho Vietourist</h3>
        <span className="v3-badge neutral">Vietourist tra giá giúp bạn</span></div>
      <p>Bạn ghi nơi đến và ngày đi. Vietourist tra giá với đối tác rồi báo lại cho bạn trước
        khi đặt. Trang này không nhận số thẻ — đối tác thu tiền trực tiếp của bạn.</p>

      {!mo && <div className="v3-actions">
        <button type="button" className="v3-button v3-primary cursor-interaction"
          onClick={() => { setMo(true); setXong(""); }}><span>Gửi một yêu cầu</span></button></div>}

      {mo && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
          <label className="v3-field" style={{ flex: "999 1 240px", minWidth: 0 }}>Nơi đến
            <input value={f.noi_den} placeholder="Đà Nẵng, Phú Quốc…"
              onChange={(e) => setF({ ...f, noi_den: e.target.value })} /></label>
          <label className="v3-field" style={RONG}>Nhận phòng
            <input type="date" value={f.ngay_nhan}
              onChange={(e) => setF({ ...f, ngay_nhan: e.target.value })} /></label>
          <label className="v3-field" style={RONG}>Trả phòng
            <input type="date" value={f.ngay_tra}
              onChange={(e) => setF({ ...f, ngay_tra: e.target.value })} /></label>
          <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Số phòng
            <input type="number" min={1} max={9} value={f.so_phong}
              onChange={(e) => setF({ ...f, so_phong: Number(e.target.value) })} /></label>
          <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Người lớn
            <input type="number" min={1} max={30} value={f.nguoi_lon}
              onChange={(e) => setF({ ...f, nguoi_lon: Number(e.target.value) })} /></label>
          <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Trẻ em
            <input type="number" min={0} max={20} value={f.tre_em}
              onChange={(e) => setF({ ...f, tre_em: Number(e.target.value) })} /></label>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
          <label className="v3-field" style={{ flex: "1 1 240px", minWidth: 0 }}>Tên người nhận phòng
            <input value={f.nguoi_nhan_phong}
              onChange={(e) => setF({ ...f, nguoi_nhan_phong: e.target.value })} /></label>
          <label className="v3-field" style={{ flex: "1 1 240px", minWidth: 0 }}>Số điện thoại hoặc email để báo giá
            <input value={f.lien_he}
              onChange={(e) => setF({ ...f, lien_he: e.target.value })} /></label>
        </div>
        <label className="v3-field" style={{ display: "block", marginTop: 8 }}>Yêu cầu thêm
          <textarea rows={2} value={f.yeu_cau_them} placeholder="Phòng tầng cao, nhận phòng sớm…"
            onChange={(e) => setF({ ...f, yeu_cau_them: e.target.value })} /></label>
        {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
        <div className="v3-actions">
          <button type="button" className="v3-button v3-secondary cursor-interaction"
            onClick={() => { setMo(false); setLoi(""); }}><span>Thôi</span></button>
          <button type="button" className="v3-button v3-primary cursor-interaction"
            disabled={busy} onClick={gui}><span>{busy ? "Đang gửi…" : "Gửi yêu cầu"}</span></button>
        </div></>}

      {xong && <div className="v3-notice good"><span>{xong}</span></div>}
      <p className="v3-small">Vietourist không giữ và không nhập số thẻ của bạn. Khi đặt được,
        đối tác thu tiền trực tiếp của bạn theo điều kiện của họ.</p>
    </section>

    {don && don.length > 0 && <section className="v3-panel">
      <div className="v3-section-title"><h3>Đơn của tôi</h3>
        <span className="v3-badge neutral">{don.length}</span></div>
      <div style={{ display: "grid", gap: 10 }}>{don.map((d) => (
        <article key={d.id} style={{ border: VIEN, borderRadius: 12, padding: "12px 14px" }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "baseline" }}>
            <strong style={{ fontSize: 17 }}>{d.noi_den || "—"}</strong>
            <span className="v3-badge neutral">{ten[d.trang_thai] || d.trang_thai_ten}</span>
            {d.gia_gom_thue != null && <span className="v3-badge good">
              {tien(d.gia_gom_thue, d.tien_te)}</span>}
          </div>
          <p className="v3-small" style={{ margin: "6px 0" }}>
            {ngay(d.ngay_nhan)}{d.ngay_tra ? ` – ${ngay(d.ngay_tra)}` : ""} · {d.so_phong} phòng
            {" "}· {d.nguoi_lon} người lớn{d.tre_em ? ` · ${d.tre_em} trẻ em` : ""}
            {d.nguoi_nhan_phong ? ` · ${d.nguoi_nhan_phong}` : ""}</p>
          <p style={{ margin: "0 0 6px" }}>{VIEC_CUA_KHACH[d.trang_thai] || ""}</p>
          {d.so_xac_nhan_ks && <p className="v3-small">Số xác nhận khách sạn:{" "}
            <b>{d.so_xac_nhan_ks}</b></p>}
          <p className="v3-small">Mã theo dõi: {d.the_tham_chieu}</p>
        </article>))}</div>
      <p className="v3-small">Chỉ bạn xem được những đơn này — Vietourist chặn ở tầng dữ liệu
        theo tài khoản đăng nhập, không theo mã theo dõi.</p>
    </section>}
  </>);
}
