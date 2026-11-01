"use client";
/* KS-16q (Chủ tịch duyệt bản xem thử 01/11/2026) · trang riêng kh.vietourist.vn/tours: danh sách tour (lọc điểm đến,
   ngày, nơi khởi hành, ngân sách) → chi tiết tour → gửi yêu cầu đặt tour, như cổng khách trước KS-16m. Khách chưa
   đăng nhập xem qua cửa /cong/mo; gửi yêu cầu cần đăng nhập (khung trang riêng hiện ô đăng nhập).
   Gửi yêu cầu chưa giữ chỗ, chưa thu tiền: Sales gọi lại và báo giá cuối (KH-1). */
import { useCallback, useEffect, useMemo, useState } from "react";
import { duongRieng, goiCong, xemCong } from "@/lib/cong";
import { Badge, I, Nut, TheTour, canh, ngay, tien } from "./KhachHang";

type Man = "ds" | "tour" | "yc" | "xong";

export default function ToursRieng({ toi, moId }: { toi: any; moId?: number }) {
  const [man, setMan] = useState<Man>("ds");
  const [ds, setDs] = useState<any>(null);
  const [loc, setLoc] = useState({ q: "", tu_ngay: "", noi: "", ngan_sach: "", nhom: "" });
  const [tour, setTour] = useState<any>(null);
  const [loai, setLoai] = useState<"tour" | "tour_doan">("tour");
  const [yc, setYc] = useState({ so_khach: 2, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false });
  const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const len = () => { try { window.scrollTo(0, 0); } catch { /* bỏ qua */ } };

  const tim = useCallback(async (l = loc) => {
    const q = new URLSearchParams(Object.entries(l).filter(([, v]) => v) as any).toString();
    try { setDs(await xemCong(`/khach/tour${q ? `?${q}` : ""}`)); } catch (x: any) { setErr(x.message); }
  }, [loc]);
  const mo = async (t: any) => {
    setErr(""); setMsg("");
    try {
      const o = t.khoi_hanh ? t : await xemCong(`/khach/tour/${t.id}`);
      setTour(o); setMan("tour"); len();
      try { window.history.replaceState(null, "", duongRieng("tours", o.id)); } catch { /* bỏ qua */ }
    } catch (x: any) { setErr(x.message); }
  };
  useEffect(() => { tim(); if (moId) mo({ id: moId }); }, []);  // eslint-disable-line react-hooks/exhaustive-deps
  const veDs = () => { setMan("ds"); setErr(""); len(); try { window.history.replaceState(null, "", duongRieng("tours")); } catch { /* bỏ qua */ } };
  const moYc = (l: "tour" | "tour_doan") => { setLoai(l); setYc({ so_khach: l === "tour" ? 2 : 20, dien_thoai: "", ngay_mong_muon: "", ghi_chu: "", dong_y: false }); setErr(""); setMan("yc"); len(); };
  const gui = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      const r = await goiCong("/khach/yeu-cau", { loai, tour_id: loai === "tour" ? tour?.id : null, so_khach: Number(yc.so_khach),
        dien_thoai: yc.dien_thoai, ngay_mong_muon: yc.ngay_mong_muon || null, ghi_chu: yc.ghi_chu, dong_y: yc.dong_y });
      setMsg(r.message); setMan("xong"); len();
    } catch (x: any) { setErr(x.status === 401 ? "Đăng nhập để gửi yêu cầu — thông tin bạn vừa điền vẫn giữ trên trang." : x.message); }
    finally { setBusy(false); }
  };
  const tamTinh = useMemo(() => (tour ? tour.gia * Number(yc.so_khach || 0) : 0), [tour, yc.so_khach]);
  const coSdt = !!toi?.dien_thoai;
  const thongBao = <>{msg && <div className="v3-notice info"><I n="check" /><span>{msg}</span></div>}
    {err && <div className="v3-notice warn"><I n="info" /><span>{err}</span></div>}</>;

  if (man === "xong") return <section className="v3-panel">{thongBao}
    <h2>Đã gửi yêu cầu</h2><p>Sales Vietourist gọi lại trong giờ làm việc và gửi báo giá cuối. Theo dõi ở «Đơn của tôi» trên cổng khách.</p>
    <div className="v3-actions"><Nut kieu="primary" i="arrow-left" onClick={veDs}>Xem tour khác</Nut><a className="v3-button v3-secondary" href="/cong">Đơn của tôi</a></div></section>;

  if (man === "yc") return <div className="v3-two">
    <section className="v3-panel">
      <Nut kieu="quiet" i="arrow-left" onClick={() => setMan(loai === "tour" && tour ? "tour" : "ds")}>Quay lại</Nut>
      <h2>{loai === "tour" ? tour?.ten : "Tour đoàn theo yêu cầu"}</h2>
      <p>{loai === "tour" ? `${ngay(tour?.khoi_hanh)} · ${tour?.thoi_gian}` : "Gia đình, doanh nghiệp, hội nhóm — Sales thiết kế hành trình riêng."}</p>
      <label className="v3-field">Số khách<input type="number" min={1} max={200} value={yc.so_khach} onChange={(e) => setYc({ ...yc, so_khach: Number(e.target.value) })} /></label>
      {toi && <div className="v3-field">Người gửi<div className="v3-readonly">{toi.ho_ten || "Khách hàng"} · {toi.dien_thoai || toi.email}</div></div>}
      <label className="v3-field">Số điện thoại Sales gọi lại{coSdt ? " (để trống = số đã xác thực)" : ""}
        <input inputMode="tel" value={yc.dien_thoai} placeholder={coSdt ? toi.dien_thoai : "09xx xxx xxx"} onChange={(e) => setYc({ ...yc, dien_thoai: e.target.value })} /></label>
      {loai === "tour_doan" && <label className="v3-field">Ngày mong muốn khởi hành<input type="date" value={yc.ngay_mong_muon} onChange={(e) => setYc({ ...yc, ngay_mong_muon: e.target.value })} /></label>}
      <label className="v3-field">Ghi chú cho Sales<textarea rows={3} value={yc.ghi_chu} placeholder={loai === "tour" ? "Trẻ em, phòng, ăn chay…" : "Điểm đến, ngân sách, số ngày, nhu cầu đặc biệt…"}
        onChange={(e) => setYc({ ...yc, ghi_chu: e.target.value })} /></label>
      <div className="v3-check"><input id="tr-dong-y" type="checkbox" checked={yc.dong_y} onChange={(e) => setYc({ ...yc, dong_y: e.target.checked })} />
        <label htmlFor="tr-dong-y">Tôi hiểu gửi yêu cầu chưa giữ chỗ và chưa thu tiền; giá cuối, chương trình và điều kiện hủy do Sales gửi.</label></div>
    </section>
    <section className="v3-panel v3-quote"><div className="v3-section-title"><h3>Tạm tính</h3><Badge c="demo">Chưa phải báo giá</Badge></div>
      {loai === "tour" ? <dl className="v3-stat-rows"><div><dt>Giá người lớn</dt><dd>{tien(tour?.gia)}</dd></div><div><dt>Số khách</dt><dd>{yc.so_khach}</dd></div></dl>
        : <p>Tour đoàn được báo giá riêng theo hành trình bạn mô tả.</p>}
      {loai === "tour" && <div className="v3-total"><span>Tạm tính theo giá người lớn</span><strong>{tien(tamTinh)}</strong></div>}
      <p>Giá trẻ em, phụ thu phòng đơn và ưu đãi được Sales tính trong báo giá.</p>
      {thongBao}
      <Nut kieu="primary" i="send" disabled={busy || !yc.dong_y} onClick={gui}>{busy ? "Đang gửi…" : toi ? "Gửi yêu cầu" : "Đăng nhập và gửi yêu cầu"}</Nut>
      <small>Yêu cầu vào hàng chờ Kinh doanh; Sales gọi lại trong giờ làm việc.</small>
    </section></div>;

  if (man === "tour" && tour) return <>
    <Nut kieu="quiet" i="arrow-left" onClick={veDs}>Tất cả tour</Nut>{thongBao}
    <section className="v3-product-detail">
      <div className={`v3-scene ${canh(tour)[0]}`}><span className="v3-scene-orb" /><span className="v3-scene-icon"><I n={canh(tour)[1]} /></span>
        <span className="v3-scene-title">{tour.ten}</span><span className="v3-badge neutral">{tour.nhan}</span></div>
      <div className="v3-panel"><div className="v3-section-title"><h2>{tour.ten}</h2><Badge>{tour.ma}</Badge></div>
        <dl className="v3-stat-rows">
          <div><dt>Thời gian</dt><dd>{tour.thoi_gian}</dd></div>
          <div><dt>Khởi hành</dt><dd>{ngay(tour.khoi_hanh)} – kết thúc {ngay(tour.ket_thuc)}</dd></div>
          {tour.noi_khoi_hanh && <div><dt>Nơi khởi hành</dt><dd>{tour.noi_khoi_hanh}</dd></div>}
          {tour.phuong_tien && <div><dt>Phương tiện</dt><dd>{tour.phuong_tien}</dd></div>}
          <div><dt>Giá người lớn</dt><dd>{tour.gia_goc && <del style={{ marginRight: 8 }}>{tien(tour.gia_goc)}</del>}{tien(tour.gia)} / khách</dd></div>
          {tour.gia_tre_em && <div><dt>Giá trẻ em</dt><dd>{tien(tour.gia_tre_em)} / khách</dd></div>}
          <div><dt>Chỗ</dt><dd>{tour.it_cho ? "Còn ít chỗ" : "Còn chỗ"}</dd></div>
        </dl>
        <div className="v3-notice warn"><I n="info" /><span>Chương trình chi tiết, dịch vụ bao gồm và điều kiện hủy do Sales gửi kèm báo giá. Gửi yêu cầu chưa giữ chỗ và chưa thu tiền.</span></div>
        <div className="v3-actions"><Nut kieu="primary" i="send" onClick={() => moYc("tour")}>Gửi yêu cầu đặt tour</Nut></div>
      </div></section></>;

  return <>
    <section className="v3-panel">
      <div className="v3-section-title"><h2>Tour du lịch Vietourist</h2><Badge>{ds ? `${ds.tour.length} tour đang mở bán` : "Đang tải…"}</Badge></div>
      <div className="v3-search"><label className="v3-field">Điểm đến hoặc tên tour<input type="search" value={loc.q} placeholder="Phú Quốc, Đà Nẵng, Huế…"
        onChange={(e) => setLoc({ ...loc, q: e.target.value })} onKeyDown={(e) => e.key === "Enter" && tim()} /></label>
        <Nut kieu="primary" i="search" onClick={() => tim()}>Tìm tour</Nut></div>
      <div className="v3-form-grid">
        <label className="v3-field">Khởi hành từ ngày<input type="date" value={loc.tu_ngay} onChange={(e) => setLoc({ ...loc, tu_ngay: e.target.value })} /></label>
        <label className="v3-field">Nơi khởi hành<select value={loc.noi} onChange={(e) => setLoc({ ...loc, noi: e.target.value })}>
          <option value="">Tất cả</option>{(ds?.noi_khoi_hanh || []).map((n: string) => <option key={n} value={n}>{n}</option>)}</select></label>
        <label className="v3-field">Ngân sách / khách<select value={loc.ngan_sach} onChange={(e) => setLoc({ ...loc, ngan_sach: e.target.value })}>
          <option value="">Tất cả</option><option value="1500000">Đến 1,5 triệu</option><option value="3500000">Đến 3,5 triệu</option>
          <option value="5000000">Đến 5 triệu</option><option value="10000000">Đến 10 triệu</option></select></label>
      </div>
      <div className="v3-actions"><Nut i="sliders-horizontal" onClick={() => tim()}>Áp dụng bộ lọc</Nut></div>
      <div className="v3-chips" aria-label="Nhóm tour">{[["", "Tất cả tour"], ["promo", "Khuyến mại"], ["last", "Giờ chót"]].map(([k, t]) =>
        <button key={k} type="button" className="cursor-interaction" aria-pressed={loc.nhom === k} onClick={() => { const l = { ...loc, nhom: k }; setLoc(l); tim(l); }}>{t}</button>)}</div>
    </section>
    {thongBao}
    <div className="v3-products">{(ds?.tour || []).map((t: any) => <TheTour key={t.id} t={t} mo={mo} ngoai={false} />)}</div>
    {ds && !ds.tour.length && <section className="v3-panel"><p>Không có tour khớp bộ lọc. Thử bỏ bớt điều kiện hoặc gửi yêu cầu tour đoàn.</p></section>}
    <section className="v3-panel"><div className="v3-section-title"><h3>Tour đoàn theo yêu cầu</h3></div>
      <p>Hành trình riêng cho gia đình, doanh nghiệp và những dịp đặc biệt.</p>
      <div className="v3-actions"><Nut i="users" onClick={() => moYc("tour_doan")}>Gửi yêu cầu tour đoàn</Nut></div></section>
  </>;
}
