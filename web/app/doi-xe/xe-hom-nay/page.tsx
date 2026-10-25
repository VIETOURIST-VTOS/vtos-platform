"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** XS-1 · XE HÔM NAY THEO SHEET ĐỘI XE — Chủ tịch duyệt bản xem thử 25/10/2026.
 *
 *  Trong lúc Đội xe chưa lập lệnh điều xe trên VTOS, robot đọc sheet «Quyết Toán dữ liệu xe» của anh
 *  Huân qua link CSV công bố, và đếm xe có chuyến mà ngày đi ≤ hôm nay ≤ ngày về. Khi đã có lệnh thì
 *  lệnh thay sheet (bảng điều hành thôi đọc sheet) — màn này vẫn mở được để đối chiếu.
 *
 *  CHỈ ĐỌC. Không nút nào ở đây ghi vào sheet hay vào VTOS. Sai ở sheet thì sửa ở sheet; danh sách
 *  «Dòng sheet cần sửa» là để anh Huân biết sửa chỗ nào. VTOS tự cộng lại từ các cột chi tiết, không
 *  lấy ô Tổng chi và Lợi nhuận của sheet.
 *
 *  XS-1b (Chủ tịch 25/10/2026, «Giữ ký duyệt Chủ tịch»): ô dán link nằm Ở ĐÂY (đúng bản xem thử),
 *  cho Giám đốc đội xe / TP Điều hành / CNTT. Dán xong máy ĐỌC THỬ trước; đọc được mới trình, và link
 *  chỉ có hiệu lực khi Chủ tịch ký ở màn Chính sách & định mức. Cửa `/params` không dùng được cho
 *  việc này: nó chỉ nhận số.
 */

const DUONG = <><a href="/">VTOS</a> · <a href="/doi-xe">Đội xe</a> · Xe hôm nay theo sheet</>;

const TEN_LOAI: Record<string, string> = {
  tong_chi: "Tổng chi", loi_nhuan: "Lợi nhuận", tong_km: "Tổng km", km_noi: "Km nối chuyến",
  chong_ngay: "Chồng ngày", thieu_ngay: "Ngày đi/về", ve_truoc_di: "Ngày về", dong_khong_tour: "Dòng không tên tour", ctp_thieu_ngay: "CTP thiếu ngày", ctp_chua_vao_vtos: "CTP chưa vào VTOS",
};

function XeHomNay() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(undefined);
  const [dang, setDang] = useState(false);
  const [link, setLink] = useState("");
  const [thu, setThu] = useState<any>(null);
  const [gui, setGui] = useState(false);

  async function danLink(chiDocThu: boolean) {
    setGui(true); setThu(null);
    try {
      const r = await api<any>("/fleet/xe-theo-sheet/link", { method: "POST", json: { url: link, chi_doc_thu: chiDocThu } });
      setThu(r.doc_thu);
      if (r.da_trinh) { toast(r.message); setLink(""); await load(); }
    } catch (e) { toast(errMsg(e), true); }
    finally { setGui(false); }
  }

  const load = useCallback(async (lai = false) => {
    setDang(true);
    try { setD(await api<any>(`/fleet/xe-theo-sheet${lai ? "?doc_lai=1" : ""}`)); }
    catch (e) { toast(errMsg(e), true); setD(null); }
    finally { setDang(false); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  if (d === undefined) return <><div className="muted">{DUONG}</div><p className="muted">Đang đọc sheet…</p></>;

  return (<>
    <div className="muted">{DUONG}</div>
    <h1>Xe hôm nay theo sheet Đội xe</h1>
    <p className="muted">Đọc từ sheet «Quyết Toán dữ liệu xe» của anh Huân. Robot chỉ đọc, không ghi
      vào sheet. Khi Đội xe đã lập lệnh điều xe trên VTOS thì lệnh thay sheet.</p>

    {d === null ? <p className="muted">Không mở được màn này.</p>
      : !d.co_link ? (
        <div className="panel"><b>Chưa nối sheet.</b>{" "}
          <span className="muted">Dán link CSV ở ô dưới; Chủ tịch ký xong robot mới đọc.</span></div>
      ) : d.loi ? (
        <div className="panel"><Tag cls="red">Không đọc được</Tag> {d.loi}
          {d.doc_luc && <span className="muted"> · lần đọc được gần nhất {d.doc_luc}</span>}
          <div style={{ marginTop: 8 }}><button className="act" disabled={dang} onClick={() => load(true)}>Đọc lại ngay</button></div>
        </div>
      ) : (<>
        <div className="panel" style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div className="muted">Xe đang đi · {fmtD(d.ngay)}</div>
            <div style={{ fontSize: "calc(28/14*1rem)", fontWeight: 700 }}>{d.dang_di}
              <span className="muted" style={{ fontSize: "calc(13/14*1rem)", fontWeight: 500 }}> / {d.dieu_duoc} xe điều được</span></div>
            <div className="muted">{d.o_bai} xe nằm bãi · sheet có {d.so_xe_sheet} xe, {d.so_chuyen} chuyến
              {!!d.khong_khop && <> · <Tag cls="warn">{d.khong_khop} xe trong sheet không khớp xe VTOS</Tag></>}</div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div className="muted">Đọc lúc {d.doc_luc}{d.ban_cu && <> · <Tag cls="warn">bản cũ</Tag></>}</div>
            {d.loi_tai && <div className="muted">{d.loi_tai}</div>}
            <button className="act" style={{ margin: "6px 0 0" }} disabled={dang} onClick={() => load(true)}>
              {dang ? "Đang đọc…" : "Đọc lại ngay"}</button>
          </div>
        </div>

        <div className="panel wrap">
          <h2>Xe đang đi hôm nay</h2>
          {d.danh_sach.length === 0 ? <p className="muted">Sheet không có chuyến nào phủ ngày hôm nay.</p> : (
            <table><thead><tr><th>Xe</th><th>Biển số</th><th>Lái xe</th><th>Chuyến</th><th>Đi</th><th>Về</th><th>Trạng thái</th></tr></thead>
              <tbody>{d.danh_sach.map((x: any, i: number) => <tr key={i}>
                <td>{x.khoi}</td><td className="mono">{x.bien}{!x.khop_vtos && <> <Tag cls="warn">không khớp VTOS</Tag></>}</td>
                <td>{x.lai_xe}</td><td>{x.tour}</td><td>{fmtD(x.di)}</td><td>{fmtD(x.ve)}</td><td>{x.trang_thai}</td></tr>)}
                {d.nam_bai.length > 0 && <tr className="muted"><td colSpan={2}>Nằm bãi</td>
                  <td colSpan={5}>{d.nam_bai.map((x: any) => `${x.khoi} (${x.bien})`).join(" · ")}</td></tr>}
              </tbody></table>)}
        </div>

        <div className="panel wrap">
          <h2>Dòng sheet cần anh Huân sửa <span className="muted">· {d.can_sua.length} dòng · báo vàng, không chặn</span></h2>
          {d.can_sua.length === 0 ? <p className="muted">Không thấy dòng nào lệch.</p> : (
            <table><thead><tr><th>Xe</th><th>Dòng sheet</th><th>Chuyến</th><th>Loại</th><th>Chi tiết</th></tr></thead>
              <tbody>{d.can_sua.map((x: any, i: number) => <tr key={i}>
                <td>{x.khoi}</td><td className="num">{x.dong}</td>
                <td>{x.tour || "—"}{x.di && <span className="muted"> · {fmtD(x.di)}</span>}</td>
                <td><Tag cls="warn">{TEN_LOAI[x.loai] || x.loai}</Tag></td><td>{x.noi_dung}</td></tr>)}
              </tbody></table>)}
        </div>
      </>)}

    {d && (d.duoc_dan || d.cho_ky) && (
      <div className="panel">
        <h2>Link sheet Đội xe</h2>
        {d.cho_ky && <p><Tag cls="warn">Chờ Chủ tịch ký</Tag> link do {d.cho_ky.boi} trình, hiệu lực từ {fmtD(d.cho_ky.hieu_luc)}.
          {" "}<a href="/params">Màn Chính sách &amp; định mức →</a></p>}
        {d.duoc_dan && <>
          <label htmlFor="xs-link">Link CSV «Công bố lên web» của trang «Quyết Toán dữ liệu xe»</label>
          <input id="xs-link" type="url" value={link} onChange={(e) => setLink(e.target.value)}
            placeholder="https://docs.google.com/spreadsheets/d/e/…/pub?gid=0&single=true&output=csv" style={{ width: "100%" }} />
          <p className="muted">Trong sheet: Tệp → Chia sẻ → Công bố lên web → chọn trang, định dạng CSV → Công bố.
            Ai có link này đều xem được số của sheet.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button className="act grey" style={{ margin: 0 }} disabled={gui || !link} onClick={() => danLink(true)}>Đọc thử</button>
            <button className="act" style={{ margin: 0 }} disabled={gui || !link} onClick={() => danLink(false)}>Trình Chủ tịch ký</button>
          </div>
          {thu && (thu.ok
            ? <p className="ok">Đọc được {thu.so_xe} xe, {thu.so_chuyen} chuyến · {thu.so_can_sua} dòng cần sửa.</p>
            : <p className="err">{thu.loi}</p>)}
        </>}
      </div>
    )}
  </>);
}

export default function Page() { return <Shell><XeHomNay /></Shell>; }
