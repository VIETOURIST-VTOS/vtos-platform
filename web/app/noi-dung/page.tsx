"use client";
/** Nội dung & thương hiệu — SỔ DUYỆT, không phải thư viện ảnh.
 *
 *  Vietourist là công ty đại chúng (VTD, UPCoM). Một bài hứa "cam kết hoàn tiền 100%" hay một con số tài
 *  chính đưa ra ngoài mà chưa ai duyệt là rủi ro pháp lý và rủi ro công bố thông tin. Vì vậy nội dung trả
 *  lời "Có" ở một trong hai ô cam kết / số liệu tài chính phải có chữ ký thứ hai của Ban TGĐ hoặc Pháp chế
 *  trước khi được duyệt. Bỏ chốt này thì màn hình chỉ còn là một danh sách bài đăng. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const today = () => new Date().toISOString().slice(0, 10);
const RONG = { title: "", loai: "bai_dang", campaign_id: "", kenh: [] as string[], ngay_du_kien: today(),
               ban_thao: "", co_cam_ket: false, co_so_lieu_tc: false, note: "", nguon_tao: "nguoi", ai_ghi_chu: "" };
const MAU: Record<string, string> = { nhap: "grey", cho_duyet: "warn", cho_ky_2: "red", da_duyet: "ok", da_dang: "ok", go: "grey" };

function NoiDung() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const soanDuoc = ["nv_mkt", "ptgd_mkt", "cntt"].includes(role);
  const duyetDuoc = ["ptgd_mkt", "tgd", "chutich", "hanh_chinh"].includes(role);
  const [meta, setMeta] = useState<any>({ loai: {}, kenh: {}, trang_thai: {}, vai_tro_ky_2: [] });
  const [ds, setDs] = useState<any[]>([]);
  const [cd, setCd] = useState<any[]>([]);
  const [f, setF] = useState<any>({ ...RONG });
  const [hien, setHien] = useState(false);
  const [mo, setMo] = useState<number | null>(null);

  const load = useCallback(() => { api("/noi-dung").then(setDs).catch((e) => toast(errMsg(e), true)); }, []); // eslint-disable-line
  useEffect(() => {
    api("/noi-dung/meta").then(setMeta).catch(() => {});
    api("/marketing/campaigns").then((r) => setCd(Array.isArray(r) ? r : [])).catch(() => {});
    load();
  }, [load]);

  const post = async (p: string, json?: any, method = "POST") => {
    try { const r = await api(p, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiKenh = (k: string) => setF({ ...f, kenh: f.kenh.includes(k) ? f.kenh.filter((x: string) => x !== k) : [...f.kenh, k] });
  const luu = () => post("/noi-dung", { ...f, campaign_id: f.campaign_id ? Number(f.campaign_id) : null })
    .then((r) => { if (r) { setF({ ...RONG }); setHien(false); } });
  const canKy2 = f.co_cam_ket || f.co_so_lieu_tc;

  return (<>
    <h1>Nội dung & thương hiệu</h1>
    <p className="muted">Đây là <b>sổ duyệt</b>: nội dung nào đã đăng, ai duyệt, đăng ở đâu, và trong đó có cam kết gì với khách không.
      Nội dung có <b>cam kết với khách</b> hoặc có <b>số liệu tài chính</b> cần <b>chữ ký thứ hai</b> của Ban TGĐ hoặc Pháp chế —
      Vietourist là công ty đại chúng, đây là nghĩa vụ công bố thông tin chứ không phải thủ tục nội bộ Marketing.</p>

    {soanDuoc && <button className="act" onClick={() => setHien(!hien)}>{hien ? "Đóng biểu mẫu" : "+ Lập hồ sơ nội dung"}</button>}

    {hien && <div className="panel"><h2>Hồ sơ nội dung</h2>
      <div className="grid">
        <label>Tiêu đề *<input value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></label>
        <label>Loại nội dung *<select value={f.loai} onChange={(e) => setF({ ...f, loai: e.target.value })}>
          {Object.entries(meta.loai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
        <label>Chiến dịch<select value={f.campaign_id} onChange={(e) => setF({ ...f, campaign_id: e.target.value })}>
          <option value="">— nội dung thường xuyên —</option>
          {cd.map((c: any) => <option key={c.id} value={c.id}>{c.code} · {c.name}</option>)}</select></label>
        <label>Ngày dự kiến đăng *<input type="date" value={f.ngay_du_kien} onChange={(e) => setF({ ...f, ngay_du_kien: e.target.value })} /></label>
      </div>
      <div style={{ margin: "6px 0" }}><b>Kênh đăng *</b>{" "}
        {Object.entries(meta.kenh).map(([k, v]: any) => <button key={k} className={"act " + (f.kenh.includes(k) ? "" : "grey")}
          style={{ margin: "4px 6px 0 0", fontSize: 13 }} onClick={() => doiKenh(k)}>{v}</button>)}</div>
      <label>Đường dẫn bản thảo * <i className="muted">(bản thảo không xem được thì không duyệt được)</i>
        <input style={{ width: "100%" }} value={f.ban_thao} onChange={(e) => setF({ ...f, ban_thao: e.target.value })} placeholder="Link Drive / mã tệp đính kèm" /></label>
      <div className="panel" style={{ background: "var(--bg2)" }}>
        <label><input type="checkbox" checked={f.co_cam_ket} onChange={(e) => setF({ ...f, co_cam_ket: e.target.checked })} /> <b>Có cam kết với khách</b> <i className="muted">— giá, khuyến mãi, chính sách hoàn huỷ, cam kết dịch vụ</i></label>
        <label><input type="checkbox" checked={f.co_so_lieu_tc} onChange={(e) => setF({ ...f, co_so_lieu_tc: e.target.checked })} /> <b>Có số liệu tài chính</b> <i className="muted">— doanh thu, lợi nhuận, quy mô</i></label>
        {canKy2 && <p style={{ color: "var(--orange)", margin: "4px 0" }}>Hồ sơ này sẽ cần <b>chữ ký thứ hai</b> ({(meta.vai_tro_ky_2 || []).join(", ")}) trước khi được duyệt.</p>}
      </div>
      <label>Ghi chú<textarea rows={2} style={{ width: "100%" }} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></label>
      <div className="panel" style={{ background: "var(--bg2)" }}>
        <label><input type="checkbox" checked={f.nguon_tao === "ai"} onChange={(e) => setF({ ...f, nguon_tao: e.target.checked ? "ai" : "nguoi" })} /> <b>Nội dung do trợ lý AI soạn</b></label>
        {f.nguon_tao === "ai" && <label>Căn cứ (bắt buộc)<textarea rows={2} style={{ width: "100%" }} value={f.ai_ghi_chu} onChange={(e) => setF({ ...f, ai_ghi_chu: e.target.value })} /></label>}
      </div>
      <button className="act" disabled={!f.title || !f.kenh.length || !f.ban_thao} onClick={luu}>Lưu ở trạng thái Nháp</button>
    </div>}

    <div className="panel wrap"><table><thead><tr>
      <th>Mã</th><th>Tiêu đề</th><th>Loại</th><th>Kênh</th><th>Dự kiến đăng</th><th>Cờ</th><th>Trạng thái</th><th></th>
    </tr></thead><tbody>
      {ds.map((n) => [
        <tr key={n.id}>
          <td><b>{n.code}</b>{n.nguon_tao === "ai" && <Tag cls="warn">AI</Tag>}</td>
          <td>{n.title}{n.chien_dich && <div className="muted">{n.chien_dich}</div>}</td>
          <td>{n.loai_ten}</td><td className="muted">{n.kenh_ten.join(" · ")}</td>
          <td>{fmtD(n.ngay_du_kien)}</td>
          <td>{n.co_cam_ket && <Tag cls="red">cam kết</Tag>}{n.co_so_lieu_tc && <Tag cls="red">số liệu TC</Tag>}</td>
          <td><Tag cls={MAU[n.status] || "grey"}>{n.status_ten}</Tag></td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => setMo(mo === n.id ? null : n.id)}>{mo === n.id ? "Ẩn" : "Xem"}</button></td>
        </tr>,
        mo === n.id && <tr key={n.id + "d"}><td colSpan={8} style={{ background: "var(--bg2)" }}>
          <p><b>Bản thảo:</b> {n.ban_thao}</p>
          {n.link_dang && <p><b>Bài đã đăng:</b> {n.link_dang}{n.posted_at && <span className="muted"> · {fmtDT(n.posted_at)}</span>}</p>}
          {n.note && <p className="muted">{n.note}</p>}
          {n.ai_ghi_chu && <p className="muted"><b>Căn cứ AI:</b> {n.ai_ghi_chu}</p>}
          {n.ly_do_go && <p style={{ color: "var(--red)" }}><b>Lý do gỡ:</b> {n.ly_do_go}</p>}
          <p className="muted">Soạn {n.nguoi_soan}{n.nguoi_duyet && ` · Ký duyệt: ${n.nguoi_duyet}`}</p>
          {n.status === "cho_ky_2" && <p style={{ color: "var(--orange)" }}>Đang chờ <b>chữ ký thứ hai</b> — phải là {(n.vai_tro_ky_2 || []).join(", ")}. Người soạn và người đã ký không ký lại được.</p>}

          {n.status === "nhap" && soanDuoc && <button className="act" onClick={() => post(`/noi-dung/${n.id}/chuyen-trang-thai`, { status: "cho_duyet" })}>Trình duyệt</button>}
          {(n.status === "cho_duyet" || n.status === "cho_ky_2") && duyetDuoc &&
            <button className="act" onClick={() => post(`/noi-dung/${n.id}/duyet`)}>Ký duyệt</button>}
          {n.status === "da_duyet" && <button className="act" onClick={() => {
            const l = prompt("Đường dẫn bài đã đăng (bắt buộc):");
            if (l && l.trim()) post(`/noi-dung/${n.id}/chuyen-trang-thai`, { status: "da_dang", link_dang: l.trim() });
          }}>Đánh dấu đã đăng</button>}
          {(n.status === "da_dang" || n.status === "da_duyet") && <button className="act grey" onClick={() => {
            const l = prompt("Lý do gỡ nội dung:");
            if (l && l.trim()) post(`/noi-dung/${n.id}/chuyen-trang-thai`, { status: "go", ly_do_go: l.trim() });
          }}>Gỡ / hết hiệu lực</button>}
        </td></tr>,
      ])}
      {!ds.length && <tr><td colSpan={8} className="muted">Chưa có hồ sơ nội dung nào.</td></tr>}
    </tbody></table></div>
  </>);
}
export default function Page() { return <Shell><NoiDung /></Shell>; }
