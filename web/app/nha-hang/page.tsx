"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** KH-2 · NHÀ HÀNG (CỔNG KHÁCH) — Chủ tịch duyệt bản xem thử 26/10/2026.
 *  Điều hành nhập nhà hàng + thực đơn (chỉ GIÁ BÁN). TP Điều hành bật «Hiện trên cổng» (DT-2b, Chủ tịch 28/10/2026);
 *  người vừa nhập / sửa không tự bật.
 *  Sửa nội dung bán của nhà hàng đang hiện → máy chủ tự tắt và ghi lý do; TP Điều hành bật lại. */
const d = (n?: number | null) => (n || n === 0 ? Math.round(n).toLocaleString("vi-VN") + " đ" : "—");
const NH_TRONG = { ten: "", tinh_thanh: "", khu_vuc: "", am_thuc: "Việt Nam", gio_phuc_vu: "", tien_ich: "", mo_ta: "", ghi_chu_noi_bo: "" };
const TD_TRONG = { ten: "", loai: "set", gia_nguoi_lon: "", gia_tre_em: "", so_khach_toi_thieu: 1, mo_ta: "", dieu_kien: "", dieu_kien_huy: "", tu_ngay: "", den_ngay: "", dang_ban: true };

function Trang() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const nhap = ["tp_dh", "nv_dh", "chutich", "tgd"].includes(role);
  const bat = ["tp_dh", "chutich", "tgd"].includes(role);
  const [x, setX] = useState<any>(null);
  const [sua, setSua] = useState<any>(null);       // nhà hàng đang sửa (id hoặc "moi")
  const [f, setF] = useState<any>(NH_TRONG);
  const [td, setTd] = useState<any>(null);         // {id?, ...} gói đang sửa
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => { api("/nha-hang").then(setX).catch((e) => toast(errMsg(e), true)); }, [toast]);
  useEffect(() => { load(); }, [load]);
  const goi = async (path: string, json: any) => {
    setBusy(true);
    try { const r = await api<any>(path, { method: "POST", json }); toast(r.message); load(); return r; }
    catch (e) { toast(errMsg(e), true); return null; } finally { setBusy(false); }
  };
  if (!x) return <p className="muted">Đang tải…</p>;
  const dang = sua && sua !== "moi" ? x.nha_hang.find((n: any) => n.id === sua) : null;
  const o = (k: string, nhan: string, ph = "") => <label>{nhan}<input value={f[k]} placeholder={ph} disabled={!nhap} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>;
  const t = (k: string, nhan: string, type = "text") => <label>{nhan}<input type={type} value={td[k] ?? ""} onChange={(e) => setTd({ ...td, [k]: e.target.value })} /></label>;
  const luuTd = async () => {
    const body = { ...td, gia_nguoi_lon: td.gia_nguoi_lon === "" ? null : Number(td.gia_nguoi_lon), gia_tre_em: td.gia_tre_em === "" || td.gia_tre_em == null ? null : Number(td.gia_tre_em),
      so_khach_toi_thieu: Number(td.so_khach_toi_thieu || 1), tu_ngay: td.tu_ngay || null, den_ngay: td.den_ngay || null };
    const r = await goi(`/nha-hang/${dang.id}/thuc-don${td.id ? `/${td.id}` : ""}`, body);
    if (r) setTd(null);
  };
  return (<>
    <h1>Nhà hàng (cổng khách)</h1>
    <p className="muted">Điều hành nhập và sửa. Chỉ TP Điều hành bật «Hiện trên cổng»; người vừa nhập / sửa không tự bật. Sửa giá hoặc thực đơn của nhà hàng đang hiện → tự tắt, chờ TP Điều hành bật lại.
      Chỉ nhập <b>giá bán cho khách</b>; giá vốn / phí NCC theo hợp đồng nhà cung cấp, không nhập ở đây.</p>
    {nhap && <button className="act teal" onClick={() => { setSua("moi"); setF(NH_TRONG); setTd(null); }}>+ Thêm nhà hàng</button>}

    <div className="panel wrap"><table><thead><tr><th>Nhà hàng</th><th>Địa điểm</th><th>Ẩm thực</th><th>Thực đơn đang bán</th><th>Trên cổng</th><th></th></tr></thead>
      <tbody>{x.nha_hang.map((n: any) => <tr key={n.id}>
        <td><b>{n.ten}</b><div className="muted">{n.ma} · nhập bởi {n.tao_boi}</div></td>
        <td>{[n.tinh_thanh, n.khu_vuc].filter(Boolean).join(" · ")}</td><td>{n.am_thuc}</td>
        <td>{n.so_dang_ban}{n.so_dang_ban ? ` (từ ${d(Math.min(...n.thuc_don.filter((t: any) => t.dang_ban).map((t: any) => t.gia_nguoi_lon)))})` : ""}</td>
        <td>{n.ngung ? <Tag cls="red">Ngừng hợp tác</Tag> : n.hien_cong ? <><Tag cls="ok">Đang hiện</Tag><div className="muted">{n.hien_boi}</div></>
          : <><Tag cls="warn">Chưa hiện</Tag>{n.tat_ly_do && <div className="muted">{n.tat_ly_do}</div>}</>}</td>
        <td style={{ whiteSpace: "nowrap" }}>
          <button className="act grey" onClick={() => { setSua(n.id); setF({ ...NH_TRONG, ...n }); setTd(null); }}>{nhap ? "Sửa" : "Xem"}</button>
          {bat && !n.ngung && <button className="act teal" disabled={busy} onClick={() => goi(`/nha-hang/${n.id}/hien-cong`, { bat: !n.hien_cong })}>{n.hien_cong ? "Tắt khỏi cổng" : "Bật hiện cổng"}</button>}
        </td></tr>)}
        {!x.nha_hang.length && <tr><td colSpan={6} className="muted">Chưa có nhà hàng nào. Điều hành bấm «Thêm nhà hàng».</td></tr>}</tbody></table></div>

    {sua && <section className="panel" style={{ marginTop: 14 }}>
      <h2>{sua === "moi" ? "Thêm nhà hàng" : `${dang?.ma} · ${dang?.ten}`}</h2>
      <div className="grid">
        {o("ten", "Tên nhà hàng")}{o("tinh_thanh", "Tỉnh / thành", "TP Hồ Chí Minh")}{o("khu_vuc", "Khu vực / địa chỉ hiển thị", "Q1 · ven sông")}
        <label>Ẩm thực<select value={f.am_thuc} disabled={!nhap} onChange={(e) => setF({ ...f, am_thuc: e.target.value })}>{x.am_thuc.map((a: string) => <option key={a}>{a}</option>)}</select></label>
        {o("gio_phuc_vu", "Giờ phục vụ", "10:00–14:00 · 17:00–22:00")}{o("tien_ich", "Tiện ích", "Phòng riêng · Chỗ đỗ xe")}
      </div>
      <label>Giới thiệu cho khách<textarea rows={2} value={f.mo_ta} disabled={!nhap} onChange={(e) => setF({ ...f, mo_ta: e.target.value })} /></label>
      <label>Ghi chú nội bộ (không lên cổng)<textarea rows={2} value={f.ghi_chu_noi_bo} disabled={!nhap} onChange={(e) => setF({ ...f, ghi_chu_noi_bo: e.target.value })} /></label>
      {nhap && <button className="act teal" disabled={busy} onClick={async () => { const r = await goi(sua === "moi" ? "/nha-hang" : `/nha-hang/${sua}`, f); if (r && sua === "moi") setSua(r.id); }}>Lưu nhà hàng</button>}
      <button className="act grey" onClick={() => setSua(null)}>Đóng</button>

      {dang && <>
        <h3 style={{ marginTop: 14 }}>Thực đơn / gói</h3>
        <div className="panel wrap"><table><thead><tr><th>Gói</th><th>Loại</th><th>Giá người lớn</th><th>Giá trẻ em</th><th>Áp dụng</th><th>Điều kiện / hủy</th><th>Đang bán</th><th></th></tr></thead>
          <tbody>{dang.thuc_don.map((g: any) => <tr key={g.id}><td><b>{g.ten}</b>{g.so_khach_toi_thieu > 1 && <div className="muted">tối thiểu {g.so_khach_toi_thieu} khách</div>}</td>
            <td>{g.loai_ten}</td><td>{d(g.gia_nguoi_lon)}</td><td>{d(g.gia_tre_em)}</td>
            <td>{g.tu_ngay || g.den_ngay ? `${g.tu_ngay || "…"} → ${g.den_ngay || "…"}` : "Quanh năm"}</td>
            <td className="muted">{[g.dieu_kien, g.dieu_kien_huy].filter(Boolean).join(" · ")}</td>
            <td>{g.dang_ban ? <Tag cls="ok">Có</Tag> : <Tag>Không</Tag>}</td>
            <td>{nhap && <button className="act grey" onClick={() => setTd({ ...TD_TRONG, ...g, gia_tre_em: g.gia_tre_em ?? "", tu_ngay: g.tu_ngay || "", den_ngay: g.den_ngay || "" })}>Sửa</button>}</td></tr>)}
            {!dang.thuc_don.length && <tr><td colSpan={8} className="muted">Chưa có gói. Cần ít nhất một gói đang bán thì Kinh doanh mới bật được.</td></tr>}</tbody></table></div>
        {nhap && !td && <button className="act teal" onClick={() => setTd({ ...TD_TRONG })}>+ Thêm gói</button>}
        {td && <div className="panel" style={{ marginTop: 10 }}>
          <div className="grid">
            {t("ten", "Tên gói")}
            <label>Loại<select value={td.loai} onChange={(e) => setTd({ ...td, loai: e.target.value })}>{Object.entries(x.loai_goi).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
            {t("so_khach_toi_thieu", "Khách tối thiểu", "number")}
            {t("gia_nguoi_lon", "Giá bán người lớn (đ)", "number")}{t("gia_tre_em", "Giá bán trẻ em (đ, để trống nếu không bán)", "number")}
            {t("tu_ngay", "Áp dụng từ", "date")}{t("den_ngay", "Áp dụng đến", "date")}
            {t("dieu_kien", "Điều kiện (đồ uống, phụ thu…)")}{t("dieu_kien_huy", "Điều kiện hủy")}
          </div>
          <label>Món trong gói<textarea rows={2} value={td.mo_ta} onChange={(e) => setTd({ ...td, mo_ta: e.target.value })} /></label>
          <label style={{ display: "flex", gap: 6, alignItems: "center" }}><input type="checkbox" checked={!!td.dang_ban} onChange={(e) => setTd({ ...td, dang_ban: e.target.checked })} />Đang bán</label>
          <button className="act teal" disabled={busy} onClick={luuTd}>Lưu gói</button><button className="act grey" onClick={() => setTd(null)}>Bỏ</button>
        </div>}
      </>}
    </section>}
  </>);
}

export default function Page() { return <Shell><Trang /></Shell>; }
