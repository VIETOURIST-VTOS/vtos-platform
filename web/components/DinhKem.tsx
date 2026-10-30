"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Ô đính kèm tệp & hình ảnh – dùng lại ở mọi màn hình phòng ban.
 *
 *  Đặt một ô chung thay vì mỗi màn hình tự làm một kiểu tải ảnh: chứng từ ảnh đi kèm gần như mọi nghiệp
 *  vụ, và nếu mỗi nơi một quy tắc về kích thước, loại tệp, ai được gỡ thì quy tắc chặt nhất thành vô nghĩa.
 *
 *  Ba điều ô này luôn nói ra bằng chữ, không giấu trong mã:
 *    · tải lại đúng tệp cũ thì báo "đã có", không tạo bản thứ hai;
 *    · gỡ tệp phải ghi lý do, và bản ghi vẫn còn để đối chiếu;
 *    · giới hạn dung lượng nói bằng số trước khi người ta chọn nhầm tệp 40 MB. */
export default function DinhKem({ doiTuong, doiTuongId, tieuDe = "Tệp & hình ảnh đính kèm", loai = "chung_tu",
                                  goi = "", chiXem = false, onDoi }:
  { doiTuong: string; doiTuongId: string | number; tieuDe?: string; loai?: string; goi?: string; chiXem?: boolean;
    onDoi?: () => void }) {
  const [ds, setDs] = useState<any[]>([]);
  const [cf, setCf] = useState<any>(null);
  const [dang, setDang] = useState(false);
  const [msg, setMsg] = useState("");
  const [keCa, setKeCa] = useState(false);
  const inp = useRef<HTMLInputElement>(null);
  const id = String(doiTuongId ?? "");

  const load = useCallback(async () => {
    if (!id) { setDs([]); return; }
    try {
      setDs(await api(`/tep?doi_tuong=${doiTuong}&doi_tuong_id=${encodeURIComponent(id)}` +
                      (keCa ? "&ke_ca_thu_hoi=true" : "")));
    } catch (e) { setMsg(errMsg(e)); }
  }, [doiTuong, id, keCa]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api("/tep/cau-hinh").then(setCf).catch(() => {}); }, []);

  const tai = async (f: File) => {
    setDang(true); setMsg("");
    try {
      const fd = new FormData();
      fd.append("doi_tuong", doiTuong); fd.append("doi_tuong_id", id);
      fd.append("tep", f); fd.append("loai", loai);
      const r = await fetch("/api/v1/tep", { method: "POST", body: fd,
        headers: { Authorization: `Bearer ${getToken() || ""}` } });
      const d = await r.json();
      if (!r.ok) throw { status: r.status, message: d?.detail || "Không tải được tệp" };
      setMsg(d.message); await load(); onDoi?.();   // KS-16d: màn gọi làm mới (vd. UNC vừa tải → mở nút «Đã chi»)
    } catch (e) { setMsg(errMsg(e)); } finally { setDang(false); if (inp.current) inp.current.value = ""; }
  };

  const go = async (a: any) => {
    const ly_do = window.prompt(`Gỡ "${a.ten_tep}" khỏi hồ sơ vì lý do gì?\n\n` +
      "Tệp không bị xóa – bản ghi vẫn còn kèm lý do để sau này đối chiếu.");
    if (!ly_do || !ly_do.trim()) return;
    try { const d = await api<any>(`/tep/${a.id}/thu-hoi`, { method: "POST", json: { ly_do } });
          setMsg(d.message); await load(); onDoi?.(); }
    catch (e) { setMsg(errMsg(e)); }
  };

  const xem = (a: any) => {
    fetch(`/api/v1/tep/${a.id}/tai`, { headers: { Authorization: `Bearer ${getToken() || ""}` } })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json())?.detail || "Không đọc được tệp");
                           return r.blob(); })
      .then((b) => window.open(URL.createObjectURL(b), "_blank"))
      .catch((e) => setMsg(String(e.message || e)));
  };

  if (!id) return null;
  return (
    <div className="panel">
      <h2>{tieuDe}</h2>
      {goi && <p className="muted">{goi}</p>}
      {!chiXem && <>
        <input ref={inp} type="file" disabled={dang}
               accept=".png,.jpg,.jpeg,.webp,.heic,.pdf,.csv,.xls,.xlsx,.doc,.docx"
               onChange={(e) => { const f = e.target.files?.[0]; if (f) tai(f); }} />
        {cf?.doi_tuong?.find((x: any) => x.ma === doiTuong) && (() => {
          const dt = cf.doi_tuong.find((x: any) => x.ma === doiTuong);
          const nh = cf.nhom_ho_so?.find((n: any) => n.ma === dt.nhom_ho_so);
          return <p className="muted">Lưu vào nhóm <b>{dt.nhom_ho_so}</b>{nh ? ` (${nh.ten})` : ""} theo {dt.luu_theo},
            giữ tối thiểu <b>{nh?.thoi_han_luu}</b>.
            {dt.nhay_cam && <> <Tag cls="warn">dữ liệu cá nhân</Tag> Phân quyền riêng theo Nghị định 13/2023 —
              chỉ HCNS, Ban TGĐ, Chủ tịch và Ban Kiểm soát đọc được.</>}</p>;
        })()}
        {cf && <p className="muted">Nhận ảnh, PDF, Excel, Word — tối đa <b>{cf.gioi_han_mb} MB</b> mỗi tệp.
          Tải lại đúng tệp đã có thì hệ thống báo &quot;đã có&quot; chứ không tạo bản thứ hai.
          {cf.kho_luu?.durable === false && <> {" "}<Tag cls="warn">kho tạm</Tag> {cf.kho_luu.canh_bao}</>}</p>}
      </>}
      {msg && <p className="muted"><b>{msg}</b></p>}
      <div className="wrap"><table>
        <thead><tr><th>Tệp</th><th>Loại</th><th>Dung lượng</th><th>Người tải</th><th>Lúc</th><th></th></tr></thead>
        <tbody>{ds.length ? ds.map((a) => <tr key={a.id} style={{ opacity: a.thu_hoi ? 0.55 : 1 }}>
          <td><a href="#" onClick={(e) => { e.preventDefault(); xem(a); }}>{a.ten_tep}</a>
            {a.la_anh && <> <Tag cls="ok">ảnh</Tag></>}
            {a.nguon === "ai" && <> <Tag cls="warn">AI: {a.tac_nhan}</Tag></>}
            {a.thu_hoi && <div className="muted">đã gỡ · {a.thu_hoi_boi} · {a.ly_do_thu_hoi}</div>}</td>
          <td className="muted">{a.loai_ten}</td>
          <td className="num muted">{(a.kich_thuoc / 1024).toFixed(0)} KB</td>
          <td className="muted">{a.boi}</td>
          <td className="muted">{fmtDT(a.luc)}</td>
          <td>{!chiXem && !a.thu_hoi &&
            <button className="act grey" onClick={() => go(a)}>Gỡ</button>}</td>
        </tr>) : <tr><td colSpan={6} className="muted">Chưa có tệp nào đính kèm.</td></tr>}</tbody></table></div>
      <label style={{ display: "block", marginTop: 6 }}>
        <input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={keCa}
               onChange={(e) => setKeCa(e.target.checked)} />
        <span className="muted">Hiện cả tệp đã gỡ (không tệp nào bị xóa hẳn)</span>
      </label>
    </div>
  );
}
