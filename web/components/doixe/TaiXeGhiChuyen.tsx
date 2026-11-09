"use client";
import { useEffect, useState } from "react";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Tài xế ghi chuyến ngay trên điện thoại (Chủ tịch duyệt bản xem trước 10/11/2026).
 *
 *  Một thẻ cho MỘT lệnh đã nhận: «Bắt đầu chuyến» (km xuất bến + ảnh đồng hồ) → ghi từng lần đổ dầu,
 *  qua trạm, gửi xe (kèm ảnh hoá đơn) → «Kết thúc chuyến, gửi Giám đốc đội xe» (km lúc về). Gửi rồi thì
 *  khoá. Màn hình không có ô doanh thu và không hiện giá thuê nội bộ — luật ở
 *  `services/tai_xe_ghi_chuyen.py`, màn hình chỉ in lại điều máy chủ trả về. */
export default function TaiXeGhiChuyen({ lenh, toast }: { lenh: any; toast: (s: string, loi?: boolean) => void }) {
  const [d, setD] = useState<any>(null);
  const [km, setKm] = useState("");
  const [anhKm, setAnhKm] = useState<File | null>(null);
  const [k, setK] = useState<any>({ kind: "dau", so_tien: "", lit: "", so_hoa_don: "", tra_bang: "tai_xe_tien_mat" });
  const [anh, setAnh] = useState<File | null>(null);
  const [dang, setDang] = useState(false);
  const duong = `/nhan-lenh/${lenh.id}/chuyen`;

  useEffect(() => { api(duong).then(setD).catch(() => setD(null)); }, [duong]);
  const so = (s: string) => Number(String(s).replace(/[^\d.]/g, "")) || 0;

  const gui = async (sau: string, f: Record<string, any>, tep: File | null, xong?: () => void) => {
    setDang(true);
    try {
      const fd = new FormData();
      Object.entries(f).forEach(([a, b]) => fd.append(a, String(b)));
      if (tep) fd.append("tep", tep);
      const r = await api<any>(`${duong}${sau}`, { method: "POST", body: fd });
      toast(r.message); setD(r); xong?.();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const xoa = async (cid: number) => {
    try { const r = await api<any>(`${duong}/khoan/${cid}`, { method: "DELETE" }); toast(r.message); setD(r); }
    catch (e) { toast(errMsg(e), true); }
  };

  if (!d) return null;
  const c = d.chuyen;
  const Anh = ({ chon, dat, nhan }: { chon: File | null; dat: (f: File | null) => void; nhan: string }) => (
    <label style={{ display: "block", border: "1.5px dashed var(--line, #ccd)", borderRadius: 8, padding: 10, textAlign: "center", cursor: "pointer" }}>
      {chon ? `Đã chọn ảnh: ${chon.name}` : nhan}
      <input type="file" accept="image/*" capture="environment" style={{ display: "none" }}
        onChange={(e) => dat(e.target.files?.[0] || null)} />
    </label>);

  return <div className="panel" style={{ maxWidth: 520 }}>
    <h2 style={{ marginTop: 0 }}>Chuyến {lenh.tour_code} · <span className="mono">{lenh.vehicle}</span></h2>

    {!c && (d.co_the_bat_dau ? <>
      <label>Km trên đồng hồ lúc xuất bến<br />
        <input inputMode="numeric" value={km} onChange={(e) => setKm(e.target.value)} placeholder="vd 120000" /></label>
      <Anh chon={anhKm} dat={setAnhKm} nhan="📷 Chụp đồng hồ km (nên có)" />
      <button className="act teal" disabled={dang} style={{ width: "100%", marginTop: 8 }}
        onClick={() => gui("/bat-dau", { km_dau: so(km) }, anhKm, () => { setKm(""); setAnhKm(null); })}>Bắt đầu chuyến</button>
    </> : <p className="muted">Nhận lệnh trước rồi mới bắt đầu chuyến.</p>)}

    {c && <>
      <p style={{ margin: "4px 0 10px" }}>Km xuất bến <b>{c.km_dau?.toLocaleString("vi-VN") ?? "—"}</b>
        {c.km_cuoi != null && <> · km về <b>{c.km_cuoi.toLocaleString("vi-VN")}</b> · chạy <b>{c.km_chay?.toLocaleString("vi-VN")} km</b></>}
        {" "}{c.da_gui ? <Tag cls="ok">Đã gửi Giám đốc đội xe</Tag> : <Tag cls="warn">Đang ghi</Tag>}</p>

      {d.chi_phi.length > 0 && <table style={{ marginBottom: 10 }}><tbody>
        {d.chi_phi.map((x: any) => <tr key={x.id}>
          <td>{x.ten}{x.lit ? ` · ${x.lit} L` : ""}<div className="muted">{x.tra_bang}{x.so_hoa_don ? ` · HĐ ${x.so_hoa_don}` : ""}{x.co_anh ? " · có ảnh" : ""}</div></td>
          <td className="num">{vnd(x.so_tien)}</td>
          <td>{!c.da_gui && x.cua_toi && <button className="act grey" style={{ margin: 0 }} onClick={() => xoa(x.id)}>Xoá</button>}</td>
        </tr>)}
        <tr><td><b>Cộng</b>{d.tong_lit ? ` · ${d.tong_lit} L` : ""}</td><td className="num"><b>{vnd(d.tong_tien)}</b></td><td /></tr>
      </tbody></table>}

      {!c.da_gui && <>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
          {Object.entries(d.khoan).map(([ma, ten]: any) =>
            <button key={ma} type="button" className={"act " + (k.kind === ma ? "teal" : "grey")} style={{ margin: 0 }}
              onClick={() => setK({ ...k, kind: ma })}>{ten}</button>)}
        </div>
        <div style={{ display: "grid", gridTemplateColumns: k.kind === "dau" ? "1fr 1fr" : "1fr", gap: 8 }}>
          {k.kind === "dau" && <label>Số lít<br /><input inputMode="decimal" value={k.lit} onChange={(e) => setK({ ...k, lit: e.target.value })} /></label>}
          <label>Thành tiền (đ)<br /><input inputMode="numeric" value={k.so_tien} onChange={(e) => setK({ ...k, so_tien: e.target.value })} /></label>
        </div>
        <label>Số hoá đơn <span className="muted">(không có ảnh thì ghi số)</span><br />
          <input value={k.so_hoa_don} onChange={(e) => setK({ ...k, so_hoa_don: e.target.value })} /></label>
        <label>Ai trả<br /><select value={k.tra_bang} onChange={(e) => setK({ ...k, tra_bang: e.target.value })}>
          {Object.entries(d.tra_bang).map(([ma, ten]: any) => <option key={ma} value={ma}>{ten}</option>)}</select></label>
        <Anh chon={anh} dat={setAnh} nhan="📷 Chụp hoá đơn" />
        <button className="act teal" disabled={dang} style={{ width: "100%", marginTop: 8 }}
          onClick={() => gui("/khoan", { kind: k.kind, so_tien: so(k.so_tien), lit: so(k.lit), so_hoa_don: k.so_hoa_don, tra_bang: k.tra_bang }, anh,
            () => { setK({ ...k, so_tien: "", lit: "", so_hoa_don: "" }); setAnh(null); })}>Lưu khoản này</button>

        <hr style={{ margin: "14px 0" }} />
        <label>Km trên đồng hồ lúc về bến<br />
          <input inputMode="numeric" value={km} onChange={(e) => setKm(e.target.value)} /></label>
        <Anh chon={anhKm} dat={setAnhKm} nhan="📷 Chụp đồng hồ km lúc về" />
        <button className="act orange" disabled={dang || !so(km)} style={{ width: "100%", marginTop: 8 }}
          onClick={() => gui("/ket-thuc", { km_cuoi: so(km) }, anhKm, () => { setKm(""); setAnhKm(null); })}>
          Kết thúc chuyến, gửi Giám đốc đội xe</button>
        <p className="muted" style={{ fontSize: 13 }}>Gửi rồi thì anh không sửa được nữa. Doanh thu do Giám đốc đội xe nhập.</p>
      </>}
    </>}
  </div>;
}
