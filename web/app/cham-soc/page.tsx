"use client";
/** Chăm sóc sau bán.
 *
 *  Phiếu TỰ SINH khi tour kết thúc, mỗi booking một phiếu, giao cho chính nhân viên đã bán. Không có nút
 *  "thêm phiếu" cho một khách lẻ: danh sách nhập tay sẽ đầy đủ hai tuần đầu rồi thưa dần và bỏ hẳn, còn
 *  số phiếu chưa ai đụng tới mới là con số đo được việc chăm sóc có làm thật hay không. */
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, pct } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

const RONG = { hinh_thuc: "goi", lien_he_duoc: "co", ly_do_khong: "", hai_long: 5,
               diem_chua_hai_long: [] as string[], nhu_cau_tiep: "", dong_y_dung_danh_gia: "", ghi_chu: "" };
const MAU: Record<string, string> = { moi: "warn", hen_lai: "warn", xong: "ok", khong_lien_he_duoc: "grey" };

function ChamSoc() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const sinhDuoc = ["ptgd_mkt", "nv_mkt", "gd_kd", "tp_dh", "tgd", "chutich", "cntt"].includes(role);
  const [meta, setMeta] = useState<any>({ cs_hinh_thuc: {}, cs_diem: {}, cs_trang_thai: {} });
  const [ds, setDs] = useState<any[]>([]);
  const [dangTai, setDangTai] = useState(true);
  const [cs, setCs] = useState<any>({});
  const [loc, setLoc] = useState("moi");
  const [mo, setMo] = useState<number | null>(null);
  const [f, setF] = useState<any>({ ...RONG });

  /** Danh sách này mất vài giây: cuối tháng 9/2026 đã là 1.267 phiếu, và con số ấy chỉ có tăng.
   *  Trong lúc chờ, bảng PHẢI nói là đang tải. Trước 29/9/2026 nó in thẳng câu "Không có phiếu nào
   *  ở bộ lọc này" ngay từ mili-giây đầu tiên — nhân viên mở lên, đọc đúng câu ấy, đóng trang, và
   *  tưởng hôm nay không có việc. Một câu KHẲNG ĐỊNH VỀ DỮ LIỆU chỉ được in sau khi đã biết dữ
   *  liệu, không phải khi còn chưa hỏi xong. */
  const load = useCallback(() => {
    setDangTai(true);
    api("/cham-soc" + (loc ? `?status=${loc}` : ""))
      .then(setDs).catch((e) => toast(errMsg(e), true)).finally(() => setDangTai(false));
    api("/cham-soc/chi-so").then(setCs).catch(() => {});
  }, [loc]); // eslint-disable-line
  useEffect(() => { api("/cskh/meta").then(setMeta).catch(() => {}); }, []);
  useEffect(load, [load]);

  const post = async (p: string, json?: any, method = "POST") => {
    try { const r = await api(p, { method, json }); toast(r.message || "Xong"); load(); return r; }
    catch (x) { toast(errMsg(x), true); }
  };
  const doiDiem = (k: string) => setF({ ...f, diem_chua_hai_long: f.diem_chua_hai_long.includes(k) ? f.diem_chua_hai_long.filter((x: string) => x !== k) : [...f.diem_chua_hai_long, k] });
  const ghi = (id: number) => post(`/cham-soc/${id}`, { ...f, hai_long: Number(f.hai_long) }, "PUT")
    .then((r) => { if (r) { setF({ ...RONG }); setMo(null); } });

  return (<>
    <h1>Chăm sóc sau bán</h1>
    <p className="muted">Phiếu <b>tự sinh</b> khi tour kết thúc — mỗi booking một phiếu, mặc định giao cho nhân viên đã bán.
      Nhân viên chỉ ghi <b>kết quả</b>. Điểm hài lòng dưới ngưỡng chính sách sẽ <b>tự mở hồ sơ khiếu nại</b>;
      khách còn nhu cầu thì <b>tự tạo lead khách cũ</b>.</p>

    <div className="kpis">
      <div className="kpi"><b style={{ color: cs.chua_ghi ? "var(--orange)" : undefined }}>{cs.chua_ghi ?? 0}</b><span>Chưa ghi kết quả</span></div>
      <div className="kpi"><b style={{ color: cs.qua_han ? "var(--red)" : undefined }}>{cs.qua_han ?? 0}</b><span>Quá hạn liên hệ</span></div>
      <div className="kpi"><b>{pct(cs.ty_le_lien_he)}</b><span>Tỷ lệ liên hệ được</span></div>
      <div className="kpi"><b>{cs.hai_long_tb || "—"}</b><span>Hài lòng bình quân /5</span></div>
      <div className="kpi"><b>{cs.lead_khach_cu ?? 0}</b><span>Lead khách cũ sinh ra</span></div>
      <div className="kpi"><b>{cs.khieu_nai_tu_mo ?? 0}</b><span>Khiếu nại tự mở</span></div>
    </div>

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
      <select value={loc} onChange={(e) => setLoc(e.target.value)}>
        <option value="">— tất cả —</option>
        {Object.entries(meta.cs_trang_thai).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select>
      {sinhDuoc && <button className="act grey" onClick={() => post("/cham-soc/sinh-phieu")}>Quét tour đã kết thúc, bù phiếu thiếu</button>}
    </div>

    <div className="panel wrap"><table><thead><tr>
      <th>Chuyến</th><th>Khách</th><th>Phụ trách</th><th>Hạn liên hệ</th><th>Kết quả</th><th>Hài lòng</th><th>Trạng thái</th><th></th>
    </tr></thead><tbody>
      {ds.map((t) => [
        <tr key={t.id}>
          <td><b>{t.tour_code}</b><div className="muted">{t.booking_code}</div></td>
          <td>{t.customer_name}<div className="muted">{t.customer_phone}</div></td>
          <td className="muted">{t.phu_trach || "—"}</td>
          <td>{fmtD(t.han_lien_he)}{t.qua_han && <Tag cls="red">quá hạn</Tag>}</td>
          <td>{t.lien_he_duoc === "co" ? "Liên hệ được" : t.lien_he_duoc === "khong" ? "Không liên hệ được" : t.lien_he_duoc === "hen_lai" ? "Hẹn lại" : "—"}</td>
          <td>{t.hai_long ? `${t.hai_long}/5` : "—"}{t.complaint_code && <Tag cls="red">{t.complaint_code}</Tag>}</td>
          <td><Tag cls={MAU[t.status] || "grey"}>{t.status_ten}</Tag></td>
          <td><button className="act grey" style={{ margin: 0, fontSize: 12 }} onClick={() => { setMo(mo === t.id ? null : t.id); setF({ ...RONG }); }}>{mo === t.id ? "Ẩn" : t.status === "xong" ? "Xem" : "Ghi"}</button></td>
        </tr>,
        mo === t.id && <tr key={t.id + "d"}><td colSpan={8} style={{ background: "var(--bg2)" }}>
          {t.status === "xong" || t.status === "khong_lien_he_duoc" ? <>
            <p><b>Hình thức:</b> {t.hinh_thuc_ten} · <b>Kết quả:</b> {t.lien_he_duoc === "co" ? `hài lòng ${t.hai_long}/5` : t.ly_do_khong || t.lien_he_duoc}</p>
            {t.diem_ten?.length > 0 && <p><b>Điểm chưa hài lòng:</b> {t.diem_ten.join(" · ")}</p>}
            <p><b>Khách có nhu cầu tiếp:</b> {t.nhu_cau_tiep === "co" ? "Có" : t.nhu_cau_tiep === "khong" ? "Không" : "—"}
              {t.lead_id ? ` (đã tạo lead #${t.lead_id})` : ""}</p>
            <p><b>Đồng ý cho dùng đánh giá:</b> {t.dong_y_dung_danh_gia === "co" ? "Có" :
              t.dong_y_dung_danh_gia === "khong" ? <span style={{ color: "var(--red)" }}>Không — tuyệt đối không đưa lời khách này lên kênh truyền thông</span> : "—"}</p>
            {t.ghi_chu && <p className="muted">{t.ghi_chu}</p>}
            <p className="muted">Ghi bởi {t.updated_by}</p>
          </> : <>
            <div className="grid">
              <label>Hình thức liên hệ *<select value={f.hinh_thuc} onChange={(e) => setF({ ...f, hinh_thuc: e.target.value })}>
                {Object.entries(meta.cs_hinh_thuc).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}</select></label>
              <label>Đã liên hệ được? *<select value={f.lien_he_duoc} onChange={(e) => setF({ ...f, lien_he_duoc: e.target.value })}>
                <option value="co">Có</option><option value="khong">Không</option><option value="hen_lai">Hẹn lại</option></select></label>
              {f.lien_he_duoc === "co" && <label>Mức hài lòng (1–5) *<select value={f.hai_long} onChange={(e) => setF({ ...f, hai_long: e.target.value })}>
                {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>}
              {f.lien_he_duoc === "co" && <label>Khách có nhu cầu tiếp? *<select value={f.nhu_cau_tiep} onChange={(e) => setF({ ...f, nhu_cau_tiep: e.target.value })}>
                <option value="">— chọn —</option><option value="co">Có</option><option value="khong">Không</option></select></label>}
              {f.lien_he_duoc === "co" && <label>Đồng ý cho dùng đánh giá? *<select value={f.dong_y_dung_danh_gia} onChange={(e) => setF({ ...f, dong_y_dung_danh_gia: e.target.value })}>
                <option value="">— chọn —</option><option value="co">Có</option><option value="khong">Không</option></select></label>}
            </div>
            {f.lien_he_duoc === "khong" && <label>Lý do không liên hệ được * <i className="muted">(đánh dấu cho xong là làm hỏng chính con số này)</i>
              <input style={{ width: "100%" }} value={f.ly_do_khong} onChange={(e) => setF({ ...f, ly_do_khong: e.target.value })} /></label>}
            {f.lien_he_duoc === "co" && <div style={{ margin: "6px 0" }}><b>Điểm chưa hài lòng</b>{" "}
              {Object.entries(meta.cs_diem).map(([k, v]: any) => <button key={k} className={"act " + (f.diem_chua_hai_long.includes(k) ? "" : "grey")}
                style={{ margin: "4px 6px 0 0", fontSize: 13 }} onClick={() => doiDiem(k)}>{v}</button>)}</div>}
            <label>Ghi chú<textarea rows={2} style={{ width: "100%" }} value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} /></label>
            {f.lien_he_duoc === "co" && Number(f.hai_long) < 3 &&
              <p className="muted" style={{ color: "var(--orange)" }}>Điểm dưới 3 — hệ thống sẽ tự mở một hồ sơ khiếu nại và bạn cần liên hệ khách ghi lại nguyên văn đề nghị của họ.</p>}
            <button className="act" onClick={() => ghi(t.id)}>Lưu kết quả</button>
          </>}
        </td></tr>,
      ])}
      {dangTai
        ? <tr><td colSpan={8} className="muted">Đang tải danh sách phiếu…</td></tr>
        : !ds.length && <tr><td colSpan={8} className="muted">Không có phiếu nào ở bộ lọc này.</td></tr>}
    </tbody></table></div>
  </>);
}
export default function Page() { return <Shell><ChamSoc /></Shell>; }
