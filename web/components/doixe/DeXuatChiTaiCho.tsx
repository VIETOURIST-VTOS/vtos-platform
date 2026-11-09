"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";
import BonBuocDeXuatChi from "./BonBuocDeXuatChi";

/** Đội xe v3.3 · thanh con «Đề xuất chi» trên màn /xe — nội dung đổi TẠI CHỖ (Chủ tịch duyệt 10/11/2026).
 *
 *  Một nguồn cho cả nút tạo mới lẫn danh sách theo dõi (tài liệu v3.3 mục 1): danh sách đọc
 *  `GET /fleet/de-nghi-chi` — chính các đề nghị chi 05-TT loại đội xe — và nút «Lập đề xuất chi» mở
 *  đúng màn bốn bước đang có, không dựng biểu mẫu thứ hai. */
export default function DeXuatChiTaiCho({ vai, toast, moSan = false }: {
  vai: string; toast: (s: string, loi?: boolean) => void; moSan?: boolean;
}) {
  const [ds, setDs] = useState<any[] | null>(null);
  const [xe, setXe] = useState<any[]>([]);
  const [nguong, setNguong] = useState<number | null>(null);
  const [mo, setMo] = useState(moSan);
  /** Hồ sơ bị «Trả bổ sung» đang sửa — gửi lại qua cửa chung của 05-TT, cùng mã cũ. */
  const [sua, setSua] = useState<any>(null);
  const guiLai = async () => {
    try {
      const r = await api<any>(`/fleet/de-nghi-chi/${sua.id}/gui-lai`, { method: "POST", json: {
        so_tien: Number(sua.so_tien), noi_dung: sua.noi_dung, nguoi_thu_huong: sua.ben_nhan,
        ma_so_thue: sua.ma_so_thue, can_cu: sua.can_cu } });
      toast(r.message); setSua(null); doc();
    } catch (e) { toast(errMsg(e), true); }
  };
  const lap = vai === "gd_doi_xe" || vai === "cntt";

  const doc = useCallback(async () => {
    try { setDs((await api<any>("/fleet/de-nghi-chi")).de_nghi); }
    catch (e) { setDs([]); toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { doc(); }, [doc]);
  useEffect(() => { setMo(moSan); }, [moSan]);
  useEffect(() => {
    if (!mo) return;
    api<any[]>("/fleet/xe?kem_kiem_tra=true").then(setXe).catch(() => setXe([]));
    api<any>("/fleet/danh-muc-dot3").then((d) => setNguong(d?.nguong_chung_tu ?? null)).catch(() => setNguong(null));
  }, [mo]);

  const vnd = (n: number) => Math.round(n || 0).toLocaleString("vi-VN");
  const mau = (tt: string) => tt === "da_chi" ? "ok" : tt === "tu_choi" || tt === "tra_bo_sung" ? "red" : "warn";

  return <>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", justifyContent: "space-between" }}>
      <h2 style={{ margin: 0 }}>Đề xuất chi của đội xe</h2>
      {lap && !mo && <button className="act teal" style={{ margin: 0 }} onClick={() => setMo(true)}>+ Lập đề xuất chi</button>}
    </div>
    {mo && <BonBuocDeXuatChi xe={xe} vai={vai} nguongChungTu={nguong} toast={toast}
      onXong={doc} onDong={() => setMo(false)} />}
    {sua && <div className="panel" style={{ border: "1px solid #b42318", margin: "10px 0" }}>
      <strong>Bổ sung & gửi lại – {sua.code}</strong>
      <p className="muted" style={{ margin: "4px 0 8px" }}>Lý do trả: {sua.ly_do_tu_choi || "—"}. Gửi lại thì lên lại Chủ tịch duyệt; chữ ký cũ không còn.</p>
      {[["noi_dung", "Nội dung"], ["ben_nhan", "Bên nhận"], ["ma_so_thue", "Mã số thuế"], ["can_cu", "Căn cứ"], ["so_tien", "Số tiền (đ)"]].map(([k, l]) =>
        <label key={k} style={{ display: "block", marginTop: 6 }}>{l}
          <input type={k === "so_tien" ? "number" : "text"} value={sua[k] ?? ""} onChange={(e) => setSua({ ...sua, [k]: e.target.value })} /></label>)}
      <p style={{ marginTop: 10 }}><button className="act teal" onClick={guiLai}>Gửi lại</button>
        <button className="act grey" style={{ marginLeft: 8 }} onClick={() => setSua(null)}>Thôi</button></p>
    </div>}
    {ds === null ? <p className="muted">Đang đọc danh sách…</p>
      : ds.length === 0 ? <p className="muted">Chưa có đề nghị chi nào của đội xe. Đây là số thật, không phải thiếu nguồn.</p>
      : <div className="wrap" style={{ overflowX: "auto" }}><table style={{ minWidth: 720 }}>
        <thead><tr><th>Mã</th><th>Nội dung · bên nhận</th><th>Xe / phạm vi</th><th style={{ textAlign: "right" }}>Số tiền</th><th>Đang ở bước</th></tr></thead>
        <tbody>{ds.map((x) => <tr key={x.id}>
          <td>{x.code}<div className="muted" style={{ fontSize: 12 }}>{x.ngay}</div></td>
          <td>{x.noi_dung}<div className="muted" style={{ fontSize: 12 }}>{[x.ben_nhan, x.nhom, x.loai].filter(Boolean).join(" · ")}</div></td>
          <td>{x.bien_so || (x.pham_vi === "doi" ? "Toàn đội" : "—")}</td>
          <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{vnd(x.so_tien)}</td>
          <td><span className={`tag ${mau(x.trang_thai)}`}>{x.buoc}</span>
            {x.ly_do_tu_choi && <div className="muted" style={{ fontSize: 12 }}>{x.ly_do_tu_choi}</div>}
            {x.trang_thai === "tra_bo_sung" && lap && <button type="button" style={{ marginTop: 4 }}
              onClick={() => setSua({ ...x })}>Bổ sung & gửi lại</button>}</td>
        </tr>)}</tbody></table></div>}
    <p className="muted" style={{ marginBottom: 0 }}>Cùng danh sách dù mở từ nút trên tổng quan, từ thanh con hay từ hồ sơ xe.
      Tuyến: GĐ đội xe gửi → Chủ tịch duyệt → Kế toán kiểm chứng từ và chi.</p>
  </>;
}
