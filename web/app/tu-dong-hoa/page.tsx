"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** V11 – Lịch tự động hóa. Mở VTOS ra là biết cái gì đang tự chạy, lúc nào, lần gần nhất ra sao.
 *
 *  Điều màn hình này phải nói ra rõ hơn mọi thứ khác: IM LẶNG LÀ MỘT TRẠNG THÁI HỎNG.
 *
 *  Một tác vụ chạy rồi báo lỗi thì ai cũng thấy. Một tác vụ NGỪNG CHẠY thì không sinh ra dòng nào –
 *  không lỗi, không cảnh báo, màn hình toàn xanh – và tuần sau kế toán mới phát hiện sao kê ba ngày
 *  chưa về. Nên thẻ "quá hạn" đứng ĐẦU tiên, trước cả thẻ thất bại.
 */
const MAU: Record<string, string> = { binh_thuong: "ok", that_bai: "red", im_lang: "red",
                                      chua_chay: "warn", tat: "" };

function TuDongHoa() {
  const { user, toast } = useShell();
  const vai = user?.role || "";
  const khaiDuoc = ["cntt", "chutich", "tgd"].includes(vai);
  const [d, setD] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [ls, setLs] = useState<Record<number, any[]>>({});
  const [bieu, setBieu] = useState<any>(null);
  const [dang, setDang] = useState(false);

  const load = useCallback(async () => {
    try { setD(await api("/tu-dong")); } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const xemLanChay = async (t: any) => {
    if (mo === t.id) { setMo(null); return; }
    setMo(t.id);
    if (ls[t.id]) return;
    try {
      const r = await api<any>(`/tu-dong/tac-vu/${t.id}/lan-chay?limit=30`);
      setLs((x) => ({ ...x, [t.id]: r.lan_chay }));
    } catch (e) { toast(errMsg(e), true); }
  };

  const RONG = { ma: "", ten: "", mo_ta: "", he_thong: "n8n", lich_doc: "", lich_cron: "",
                 phong_ban: "", nguoi_phu_trach: "", han_toi_da_phut: 0, quan_trong: false,
                 bat: true, ly_do_tat: "" };

  const luu = async () => {
    if (!bieu.ma.trim() || !bieu.ten.trim()) { toast("Thiếu mã hoặc tên tác vụ", true); return; }
    setDang(true);
    try {
      const than = { ...bieu, han_toi_da_phut: Number(bieu.han_toi_da_phut) || 0 };
      const r = bieu.id
        ? await api<any>(`/tu-dong/tac-vu/${bieu.id}`, { method: "PUT", json: than })
        : await api<any>("/tu-dong/tac-vu", { method: "POST", json: than });
      toast(r.message || "Đã lưu"); setBieu(null); setLs({}); await load();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!d) return <p className="muted">Đang tải…</p>;
  const dem = d.dem || {};

  return (<>
    <h1>Lịch tự động hóa</h1>
    <p className="muted">
      Lịch chạy nằm ở n8n <b>ngoài</b> VTOS; mỗi lần chạy nó báo về đây. Màn hình này trả lời hai câu:
      cái gì đang tự chạy, và <b>cái gì lẽ ra phải chạy mà chưa chạy</b>. Câu thứ hai quan trọng hơn —
      một tác vụ ngừng chạy không sinh ra dòng lỗi nào, nên nó không nằm trong bất kỳ nhật ký nào.
    </p>

    <div className="kpis">
      <div className="kpi"><b style={{ color: dem.im_lang ? "var(--red)" : undefined }}>{dem.im_lang || 0}</b>
        <span>quá hạn – không thấy chạy</span></div>
      <div className="kpi"><b style={{ color: dem.that_bai ? "var(--red)" : undefined }}>{dem.that_bai || 0}</b>
        <span>lần gần nhất thất bại</span></div>
      <div className="kpi"><b>{dem.chua_chay || 0}</b><span>khai rồi, chưa chạy lần nào</span></div>
      <div className="kpi"><b>{dem.binh_thuong || 0}</b><span>bình thường</span></div>
      <div className="kpi"><b className="muted">{dem.tat || 0}</b><span>đã tắt</span></div>
    </div>

    {khaiDuoc && <div style={{ margin: "10px 0" }}>
      <button className="act" onClick={() => setBieu({ ...RONG })}>Khai tác vụ mới</button>
      {bieu && <button className="act grey" style={{ marginLeft: 8 }} onClick={() => setBieu(null)}>Đóng biểu</button>}
    </div>}

    {bieu && <div className="panel">
      <h2>{bieu.id ? `Sửa tác vụ ${bieu.ma}` : "Khai một tác vụ tự động"}</h2>
      <p className="muted">Mã ở đây phải <b>khớp từng chữ</b> với mã luồng bên n8n gửi về — đây là chỗ
        nối duy nhất giữa hai hệ thống. Sai một chữ thì lần chạy báo về không tìm thấy chỗ đậu và bị
        từ chối, chứ không lặng lẽ tạo một tác vụ lạ.</p>
      <div className="grid2">
        <label>Mã tác vụ {!bieu.id && <span style={{ color: "var(--red)" }}>*</span>}
          <input value={bieu.ma} disabled={!!bieu.id} placeholder="sao_ke_tpbank_sang"
                 onChange={(e) => setBieu({ ...bieu, ma: e.target.value })} /></label>
        <label>Tên<input value={bieu.ten} onChange={(e) => setBieu({ ...bieu, ten: e.target.value })} /></label>
        <label>Hệ thống chạy
          <select value={bieu.he_thong} onChange={(e) => setBieu({ ...bieu, he_thong: e.target.value })}>
            {Object.entries(d.he_thong).map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}
          </select></label>
        <label>Lịch (cho người đọc)
          <input value={bieu.lich_doc} placeholder="mỗi ngày 06:00"
                 onChange={(e) => setBieu({ ...bieu, lich_doc: e.target.value })} /></label>
        <label>Lịch cron (nếu có)
          <input value={bieu.lich_cron} placeholder="0 6 * * *"
                 onChange={(e) => setBieu({ ...bieu, lich_cron: e.target.value })} /></label>
        <label>Phòng ban<input value={bieu.phong_ban}
          onChange={(e) => setBieu({ ...bieu, phong_ban: e.target.value })} /></label>
        <label>Người phụ trách<input value={bieu.nguoi_phu_trach}
          onChange={(e) => setBieu({ ...bieu, nguoi_phu_trach: e.target.value })} /></label>
        <label>Lẽ ra chạy lại trong (phút)
          <input type="number" min={0} value={bieu.han_toi_da_phut}
                 onChange={(e) => setBieu({ ...bieu, han_toi_da_phut: e.target.value })} /></label>
      </div>
      <p className="muted">Ô <b>lẽ ra chạy lại trong</b> là thứ duy nhất cho phép hệ thống phát hiện tác
        vụ đã ngừng chạy. Để <b>0</b> nghĩa là không canh — chỉ đúng với tác vụ chạy theo sự kiện.
        Tác vụ chạy theo lịch mà để 0 là một lỗ hổng: nó im ba ngày cũng không ai biết.</p>
      <label><input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={!!bieu.quan_trong}
        onChange={(e) => setBieu({ ...bieu, quan_trong: e.target.checked })} />
        Quan trọng — thất bại hoặc im lặng thì báo mức ĐỎ cho robot Kiểm soát</label>
      <label><input type="checkbox" style={{ width: "auto", marginRight: 6 }} checked={!!bieu.bat}
        onChange={(e) => setBieu({ ...bieu, bat: e.target.checked })} /> Đang bật</label>
      {!bieu.bat && <label>Lý do tắt <span style={{ color: "var(--red)" }}>*</span>
        <input value={bieu.ly_do_tat} onChange={(e) => setBieu({ ...bieu, ly_do_tat: e.target.value })}
               placeholder="vì sao tắt, và khi nào bật lại" /></label>}
      <label>Mô tả<textarea rows={2} value={bieu.mo_ta}
        onChange={(e) => setBieu({ ...bieu, mo_ta: e.target.value })} /></label>
      <button className="act teal" disabled={dang} onClick={luu} style={{ marginTop: 8 }}>
        {dang ? "Đang lưu…" : bieu.id ? "Lưu thay đổi" : "Khai tác vụ"}</button>
    </div>}

    <div className="panel wrap">
      <table>
        <thead><tr><th>Mã</th><th>Tác vụ</th><th>Chạy ở</th><th>Lịch</th><th>Canh im lặng</th>
          <th>Lần gần nhất</th><th>Trạng thái</th>{khaiDuoc && <th></th>}</tr></thead>
        <tbody>{d.tac_vu.length ? d.tac_vu.map((t: any) => {
          const tt = t.trang_thai;
          return (<>
            <tr key={t.id}>
              <td className="muted"><a style={{ cursor: "pointer", textDecoration: "underline" }}
                onClick={() => xemLanChay(t)}>{t.ma}</a></td>
              <td><b>{t.ten}</b>{t.quan_trong && <Tag cls="warn">quan trọng</Tag>}
                <div className="muted" style={{ fontSize: 12 }}>{t.phong_ban} {t.nguoi_phu_trach}</div></td>
              <td className="muted">{t.he_thong_ten}</td>
              <td className="muted">{t.lich_doc || t.lich_cron || "—"}</td>
              <td>{t.han_toi_da_phut
                ? <span className="muted">{t.han_toi_da_phut} phút</span>
                : <Tag cls="warn">không canh</Tag>}</td>
              <td className="muted">{tt.lan_cuoi
                ? <>{fmtDT(tt.lan_cuoi.bat_dau)}<div style={{ fontSize: 12 }}>
                    {tt.lan_cuoi.trang_thai_ten}
                    {tt.lan_cuoi.so_ban_ghi === null
                      ? " · không đếm" : ` · ${tt.lan_cuoi.so_ban_ghi} bản ghi`}</div></>
                : "chưa có"}</td>
              <td><Tag cls={MAU[tt.ma]}>{tt.ten}</Tag>
                {tt.vi_sao && <div className="muted" style={{ fontSize: 12 }}>{tt.vi_sao}</div>}</td>
              {khaiDuoc && <td><button className="act grey" style={{ margin: 0 }}
                onClick={() => setBieu({ ...RONG, ...t, trang_thai: undefined })}>Sửa</button></td>}
            </tr>
            {mo === t.id && <tr key={`${t.id}-lc`}><td colSpan={khaiDuoc ? 8 : 7}>
              <b>30 lần chạy gần nhất</b>
              {(ls[t.id] || []).length ? <table>
                <thead><tr><th>Bắt đầu</th><th>Xong</th><th>Giây</th><th>Bản ghi</th>
                  <th>Trạng thái</th><th>Thông báo</th></tr></thead>
                <tbody>{ls[t.id].map((l: any) => <tr key={l.id}>
                  <td className="muted">{fmtDT(l.bat_dau)}</td>
                  <td className="muted">{l.ket_thuc ? fmtDT(l.ket_thuc) : "—"}</td>
                  <td className="num">{l.giay || ""}</td>
                  <td className="num">{l.so_ban_ghi === null
                    ? <span className="muted">không đếm</span> : l.so_ban_ghi}</td>
                  <td><Tag cls={l.trang_thai === "thanh_cong" ? "ok"
                    : l.trang_thai === "that_bai" ? "red" : "warn"}>{l.trang_thai_ten}</Tag></td>
                  <td className="muted">{l.thong_bao}</td>
                </tr>)}</tbody></table>
                : <p className="muted">Chưa nhận được lần chạy nào cho tác vụ này.</p>}
            </td></tr>}
          </>);
        }) : <tr><td colSpan={8} className="muted">Chưa khai tác vụ tự động nào.
          Khai xong mới có chỗ cho n8n báo về.</td></tr>}</tbody>
      </table>
    </div>

    <div className="panel">
      <h2>Vì sao phải khai trước, không để máy tự nhận</h2>
      <ul className="muted">{(d.chu_thich || []).map((c: string, i: number) => <li key={i}>{c}</li>)}</ul>
    </div>
  </>);
}

export default function Page() { return <Shell><TuDongHoa /></Shell>; }
