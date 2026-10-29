"use client";
/* KS-1 · KHÁCH SẠN QUA OTA — dùng chung cho cổng Khách hàng, Đối tác, Cổ đông (Chủ tịch duyệt 28/10/2026).
   KS-7 (Chủ tịch duyệt bố cục 29/10/2026) — dựng lại bố cục theo cách Agoda sắp xếp: thanh tìm một hàng,
   ba bước ở đỉnh, mỗi đối tác là một THẺ chia ba cột (khung ảnh 4:3 — thông tin — cột giá và nút).

   Việc máy chủ làm KHÔNG đổi một dòng nào: trang vẫn chỉ gửi mã OTA + request_id + lựa chọn, vẫn mở
   CÙNG THẺ, vẫn không gửi link hay thông tin khách. Vòng này chỉ đổi cách bày ra màn hình.

   Vẫn KHÔNG hiện giá và phòng trống: VTD chưa có nguồn giá được cấp. Chỗ lẽ ra là giá được nói thẳng
   «xem trên trang đối tác» chứ không bỏ trống — ô trống làm khách tưởng đang tải. */
import { useCallback, useEffect, useState } from "react";
import { goiCong } from "@/lib/cong";

const ngay = (s?: string | null) => (s ? s.slice(0, 10).split("-").reverse().join("/") : "");
const uuid = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID()
  : "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => { const r = (Math.random() * 16) | 0; return (c === "x" ? r : (r & 3) | 8).toString(16); }));

/* Số đêm — khách đọc con số này trước cả giá. Lệch ngày thì trả 0 chứ không trả số âm. */
const soDem = (a: string, b: string) => {
  if (!a || !b) return 0;
  const t = (new Date(b + "T00:00:00").getTime() - new Date(a + "T00:00:00").getTime()) / 86400000;
  return t > 0 ? Math.round(t) : 0;
};

/* Nền trung tính: không đặt màu cứng, để chạy đúng trên cả nền sáng lẫn nền tối của cổng. */
const KHUNG: React.CSSProperties = {
  aspectRatio: "4 / 3", borderRadius: 10, background: "rgba(128,128,128,0.18)",
  display: "flex", alignItems: "center", justifyContent: "center", padding: 12, boxSizing: "border-box",
};
const VIEN = "1px solid rgba(128,128,128,0.28)";

function BaBuoc({ dang }: { dang: 1 | 2 | 3 }) {
  const b = ["Chọn đối tác", "Xem giá trên trang đối tác", "Đặt và thanh toán với đối tác"];
  return (<ol style={{ listStyle: "none", margin: "0 0 4px", padding: 0, display: "flex", flexWrap: "wrap", gap: 8 }}>
    {b.map((t, i) => {
      const n = (i + 1) as 1 | 2 | 3;
      return (<li key={t} style={{ flex: "1 1 180px", minWidth: 0, display: "flex", alignItems: "center", gap: 10,
        padding: "10px 12px", border: VIEN, borderRadius: 10, opacity: n === dang ? 1 : 0.62 }}>
        <span aria-hidden="true" style={{ flex: "none", width: 26, height: 26, borderRadius: "50%", border: VIEN,
          display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13 }}>{n}</span>
        <span style={{ fontSize: 14, fontWeight: n === dang ? 700 : 400 }}>{t}</span>
        {n === dang && <span className="v3-badge neutral" style={{ marginLeft: "auto" }}>đang ở đây</span>}
      </li>);
    })}
  </ol>);
}

export default function KhachSanOta({ ghiChu }: { ghiChu?: string }) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [ls, setLs] = useState<any[]>([]);
  const [dp, setDp] = useState<any[]>([]);
  const [f, setF] = useState({ diem_den: "", nhan_phong: "", tra_phong: "", so_phong: 1, nguoi_lon: 2, tre_em: 0 });
  const [chon, setChon] = useState<any>(null);
  const [rid, setRid] = useState("");
  const [loi, setLoi] = useState(""); const [busy, setBusy] = useState(false);
  const tai = useCallback(() => {
    goiCong("/khach-san/ota").then((r) => setDs(r.ota)).catch((x) => { setDs([]); setLoi(x.message); });
    goiCong("/khach-san/lich-su").then((r) => { setLs(r.luot); setDp(r.dat_phong || []); }).catch(() => null);
  }, []);
  useEffect(() => { tai(); }, [tai]);
  const dem = soDem(f.nhan_phong, f.tra_phong);
  const tom = [f.diem_den, f.nhan_phong && `${ngay(f.nhan_phong)}${f.tra_phong ? ` – ${ngay(f.tra_phong)}` : ""}`,
    `${f.so_phong} phòng · ${f.nguoi_lon} người lớn${Number(f.tre_em) ? ` · ${f.tre_em} trẻ em` : ""}`].filter(Boolean).join(" · ");
  const moXacNhan = (o: any) => { setChon(o); setRid(uuid()); setLoi(""); };
  const di = async () => {
    setBusy(true); setLoi("");
    try {
      const r = await goiCong("/khach-san/chuyen", { ota: chon.ma, request_id: rid, ...f, nhan_phong: f.nhan_phong || null, tra_phong: f.tra_phong || null,
        so_phong: Number(f.so_phong), nguoi_lon: Number(f.nguoi_lon), tre_em: Number(f.tre_em) });
      window.location.assign(r.url);
    } catch (x: any) { setLoi(x.message); setBusy(false); }
  };

  if (chon) return (<section className="v3-panel ks-xac-nhan">
    <BaBuoc dang={2} />
    <h2>Bạn sắp chuyển sang {chon.ten}</h2>
    <p>Bạn xem giá, đặt phòng và thanh toán trên {chon.ten}, theo điều kiện của {chon.ten}. Đổi, hủy, hoàn tiền làm với {chon.ten}.</p>
    <div className="v3-notice warn"><span>Trên {chon.ten}, hãy chọn lại: <b>{tom}</b>. Link hiện tại không mang được ngày và điểm đến.</span></div>
    <p className="v3-small">Vietourist có thể nhận hoa hồng từ đặt phòng hợp lệ — giá bạn trả không đổi. Vietourist không gửi số điện thoại, email của bạn cho {chon.ten}.</p>
    {loi && <div className="v3-notice warn"><span>{loi}</span></div>}
    <div className="v3-actions">
      <button type="button" className="v3-button v3-secondary cursor-interaction" onClick={() => setChon(null)}><span>Ở lại</span></button>
      <button type="button" className="v3-button v3-primary cursor-interaction" disabled={busy} onClick={di}><span>{busy ? "Đang mở…" : `Mở ${chon.ten} ↗`}</span></button>
    </div></section>);

  return (<>
    <section className="v3-panel">
      <BaBuoc dang={1} />
      <div className="v3-section-title"><h3>Bạn muốn ở đâu?</h3>
        {dem > 0 && <span className="v3-badge neutral">{dem} đêm</span>}</div>
      {/* Thanh tìm một hàng: điểm đến chiếm phần rộng nhất, ngày và số khách bám bên phải, xuống dòng khi màn hẹp. */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end" }}>
        <label className="v3-field" style={{ flex: "999 1 240px", minWidth: 0 }}>Điểm đến
          <input value={f.diem_den} placeholder="Đà Nẵng, Phú Quốc…" onChange={(e) => setF({ ...f, diem_den: e.target.value })} /></label>
        <label className="v3-field" style={{ flex: "1 1 150px", minWidth: 0 }}>Nhận phòng
          <input type="date" value={f.nhan_phong} onChange={(e) => setF({ ...f, nhan_phong: e.target.value })} /></label>
        <label className="v3-field" style={{ flex: "1 1 150px", minWidth: 0 }}>Trả phòng
          <input type="date" value={f.tra_phong} onChange={(e) => setF({ ...f, tra_phong: e.target.value })} /></label>
        <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Số phòng
          <input type="number" min={1} max={9} value={f.so_phong} onChange={(e) => setF({ ...f, so_phong: Number(e.target.value) })} /></label>
        <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Người lớn
          <input type="number" min={1} max={30} value={f.nguoi_lon} onChange={(e) => setF({ ...f, nguoi_lon: Number(e.target.value) })} /></label>
        <label className="v3-field" style={{ flex: "1 1 110px", minWidth: 0 }}>Trẻ em
          <input type="number" min={0} max={20} value={f.tre_em} onChange={(e) => setF({ ...f, tre_em: Number(e.target.value) })} /></label>
      </div>
      <p className="v3-small">Lựa chọn này để bạn nhớ khi sang trang đối tác — bạn chọn lại trên trang đối tác.</p>
    </section>

    <section className="v3-panel"><div className="v3-section-title"><h3>Đặt phòng qua đối tác của Vietourist</h3>
      <span className="v3-badge neutral">{ds ? `${ds.length} đối tác đang mở` : "Đang tải…"}</span></div>

      {ds && ds.length > 0 ? <div style={{ display: "grid", gap: 12 }}>{ds.map((o) => (
        <article key={o.ma} style={{ border: VIEN, borderRadius: 12, overflow: "hidden", display: "flex", flexWrap: "wrap" }}>

          {/* cột 1 · khung ảnh 4:3 — chưa có ảnh được cấp nên để khung thật, không để ô trống */}
          <div style={{ flex: "1 1 220px", minWidth: 0, maxWidth: 280, padding: 12, boxSizing: "border-box" }}>
            <div style={KHUNG}>
              <span style={{ fontSize: 15, fontWeight: 700, textAlign: "center", overflowWrap: "anywhere" }}>{o.ten}</span>
            </div>
          </div>

          {/* cột 2 · thông tin */}
          <div style={{ flex: "999 1 260px", minWidth: 0, padding: "14px 12px" }}>
            <strong style={{ fontSize: 18, display: "block", marginBottom: 6 }}>{o.ten}</strong>
            <p style={{ margin: "0 0 10px" }}>Xem giá, chọn phòng, đặt và thanh toán trên {o.ten}.</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              <span className="v3-badge neutral">Thanh toán trên {o.ten}</span>
              <span className="v3-badge neutral">Hủy theo chính sách {o.ten}</span>
              <span className="v3-badge good">Giá bạn trả không đổi</span>
            </div>
          </div>

          {/* cột 3 · chỗ của giá và nút */}
          <div style={{ flex: "1 1 200px", minWidth: 0, maxWidth: 240, padding: "14px 12px", borderLeft: VIEN,
            display: "flex", flexDirection: "column", justifyContent: "center", gap: 8 }}>
            <div>
              <div className="v3-small" style={{ marginBottom: 2 }}>Giá mỗi đêm</div>
              <strong style={{ fontSize: 16 }}>Xem trên {o.ten}</strong>
            </div>
            <button type="button" className="v3-button v3-primary cursor-interaction" onClick={() => moXacNhan(o)}>
              <span>Tiếp tục trên {o.ten} ↗</span></button>
          </div>
        </article>))}</div>
        : ds && <p>Chưa có đối tác khách sạn nào đang mở. Vui lòng quay lại sau hoặc liên hệ Vietourist.</p>}

      {loi && !chon && <div className="v3-notice warn"><span>{loi}</span></div>}
      <p className="v3-small">VTD chưa hiện giá và phòng trống — giá, phòng và thanh toán xem trên trang đối tác.</p>
      {ghiChu && <div className="v3-notice warn"><span>{ghiChu}</span></div>}</section>

    {dp.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đặt phòng OTA đã xác minh</h3><span className="v3-badge good">{dp.length}</span></div>
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">OTA</th><th scope="col">Thành phố</th><th scope="col">Ngày ở</th><th scope="col">Trạng thái</th></tr></thead>
        <tbody>{dp.map((d, i) => <tr key={i}><th scope="row">{d.ota}</th><td>{d.thanh_pho || "—"}</td><td>{ngay(d.ngay_den)}{d.ngay_di ? ` – ${ngay(d.ngay_di)}` : ""}</td><td>{d.trang_thai}</td></tr>)}</tbody></table></div>
      <p className="v3-small">Đặt phòng do OTA báo về, nối được với lượt bạn mở từ VTD. Đổi, hủy, hoàn tiền làm với OTA.</p></section>}

    {ls.length > 0 && <section className="v3-panel"><div className="v3-section-title"><h3>Đã mở OTA</h3><span className="v3-badge neutral">không phải đặt phòng</span></div>
      <div className="v3-table-wrap"><table><thead><tr><th scope="col">Lúc</th><th scope="col">OTA</th><th scope="col">Bạn đã chọn</th></tr></thead>
        <tbody>{ls.map((l, i) => <tr key={i}><td>{ngay(l.luc)} {l.luc.slice(11, 16)}</td><th scope="row">{l.ota}</th><td>{l.da_chon}</td></tr>)}</tbody></table></div>
      <p className="v3-small">Mở trang OTA không chứng minh đã đặt hay đã trả tiền. Cần hỗ trợ một đặt phòng: vào Hỗ trợ, ghi mã đặt phòng OTA.</p></section>}
  </>);
}
