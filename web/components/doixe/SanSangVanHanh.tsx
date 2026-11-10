"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** Bảng sẵn sàng vận hành đội xe (Chủ tịch duyệt bản xem trước 10/11/2026).
 *
 *  Máy đếm còn thiếu gì để đội xe chạy thật trên VTOS; mỗi dòng mở đúng cửa nhập. Đủ hết thì thu
 *  thành một dòng. Màn hình chỉ in lại điều máy chủ trả (`/fleet/san-sang-van-hanh`) — không tự suy.
 *
 *  VH-4 · điểm nhấn navy (Chủ tịch duyệt 10/11/2026): mặc định chỉ hiện MỤC CÒN THIẾU; mục đã đạt gom
 *  thành nhãn nhỏ, «Mở đủ … mục» mới bày hết. Hai luật «mỗi nút một chỗ»:
 *   · `an`  — mã dòng (hoặc mã nhóm) mà «Việc cần xử lý» đã nói. Dòng ấy không hiện lại ở đây.
 *   · `khongNut` — mã trang con mà màn đã có nút riêng (cửa nhập). Dòng vẫn hiện, không kèm nút thứ hai. */
export default function SanSangVanHanh({ ky, mo, an = [], khongNut = [] }: {
  ky: string; mo: (trang: string) => void; an?: string[]; khongNut?: string[];
}) {
  const [d, setD] = useState<any>(null);
  const [du, setDu] = useState(false);
  useEffect(() => { api(`/fleet/san-sang-van-hanh?ky=${ky}`).then(setD).catch(() => setD(null)); }, [ky]);
  if (!d) return null;
  if (d.du) return <p className="tag ok" style={{ display: "inline-block", marginBottom: 12 }}>Đội xe đủ điều kiện vận hành · {d.tong}/{d.tong} mục</p>;
  const mau: Record<string, string> = { ok: "ok", warn: "warn", bad: "red" };
  const dong: any[] = d.dong.filter((x: any) => !an.includes(x.ma) && !an.includes(x.nhom));
  const thieu = dong.filter((x) => !x.dat), dat = dong.filter((x) => x.dat);
  // Nhiều dòng cùng mở một trang (vd. năm dòng «Mở hồ sơ xe»): chỉ dòng ĐẦU giữ nút, các dòng sau
  // ghi nhãn — một màn không có hai nút cùng làm một việc (Chủ tịch dặn 10/11/2026).
  const hien = du ? [...thieu, ...dat] : thieu;
  const coNut = new Set<string>();
  // Dòng đỏ giữ nút trước: tài xế chưa có tài khoản quan trọng hơn xe chưa gán tài xế, dù cùng mở «Tài xế».
  const uuTien = [...hien].sort((a, b) => Number(b.muc === "bad") - Number(a.muc === "bad"));
  for (const x of uuTien) if (!x.dat && x.mo && x.nut && !khongNut.includes(x.mo) && ![...coNut].some((k) => k.startsWith(x.mo + "|")))
    coNut.add(x.mo + "|" + x.ma);
  const Dong = ({ x }: { x: any }) => (
    <div className={"xe-it" + (!x.dat && x.muc === "bad" ? " xe-do" : "")}>
      <span style={{ flex: "1 1 240px", minWidth: 0 }}><b>{x.ten}{x.so != null ? ` · ${x.so}` : ""}</b>
        {x.ghi && <span className="muted" style={{ display: "block", fontSize: 12.5 }}>{x.ghi}</span>}</span>
      {x.dat ? <span className="tag ok">Đủ</span>
        : coNut.has(x.mo + "|" + x.ma)
          ? <button type="button" className={x.muc === "bad" ? "xe-nut-chinh" : undefined} onClick={() => mo(x.mo)}>{x.nut}</button>
          : <span className={`tag ${mau[x.muc]}`}>Chưa</span>}
    </div>);
  return <section className="xe-blk" aria-label="Sẵn sàng vận hành" style={{ marginBottom: 14 }}>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
      <div style={{ flex: "1 1 260px", minWidth: 0 }}>
        <strong>Sẵn sàng vận hành · {d.dat} / {d.tong}</strong>
        <div className="xe-thanh"><i style={{ width: `${Math.round((d.dat / d.tong) * 100)}%` }} /></div>
      </div>
      <button type="button" onClick={() => setDu(!du)} aria-expanded={du}>{du ? "Chỉ mục còn thiếu" : `Mở đủ ${d.tong} mục`}</button>
    </div>
    {hien.map((x) => <Dong key={x.ma} x={x} />)}
    {!du && dat.length > 0 && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginTop: 8 }}>
      <span className="muted" style={{ fontSize: 12.5 }}>Đã đạt:</span>
      {dat.slice(0, 4).map((x) => <span key={x.ma} className="tag ok" style={{ fontWeight: 500 }}>{x.ten}</span>)}
      {dat.length > 4 && <span className="muted" style={{ fontSize: 12.5 }}>+{dat.length - 4} mục</span>}
    </div>}
  </section>;
}
