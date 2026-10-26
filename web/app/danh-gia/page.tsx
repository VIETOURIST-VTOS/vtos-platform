"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Đánh giá sau tour — bảng điểm và ba con số của báo cáo tuần. Chủ tịch quyết 25/9/2026.
 *
 *  ── BA CON SỐ ĐỨNG CẠNH NHAU, CỐ Ý ─────────────────────────────────────────────────────────
 *  Gọi điện thì "không nghe máy" là một kết quả có người ghi lại. Tin nhắn tự động thì "không trả
 *  lời" chỉ là một dòng trống. Một bảng chỉ in "điểm trung bình 4,6" là điểm của NHỮNG NGƯỜI CHỊU
 *  TRẢ LỜI — và người bực nhất thường là người không buồn trả lời. Nên trang này in đã gửi · đã
 *  trả lời · không gửi được cạnh nhau, và không cho giấu con số nào.
 *
 *  ── MẶC ĐỊNH CHỈ CỘNG ĐIỂM KHÁCH TỰ CHẤM ───────────────────────────────────────────────────
 *  Khi không còn bộ phận chăm sóc riêng, người ghi hộ chính là người bị chấm. Trộn hai loại số vào
 *  nhau thì bảng điểm không đo được ai. Mở được cả hai để so, nhưng phải bấm.
 *
 *  ── MÀN HÌNH KHÔNG TỰ TÍNH MỘT CON SỐ NÀO ──────────────────────────────────────────────────
 *  Kể cả điểm trung bình. Máy chủ cộng; tính lại ở đây là dựng công thức thứ hai.
 */

const LOAI: [string, string][] = [
  ["hdv", "Hướng dẫn viên"], ["tai_xe", "Tài xế"], ["tour", "Chuyến đi"],
  ["khach_san", "Khách sạn"], ["an_uong", "Ăn uống"],
  // KH-4 · 27/10/2026: bốn mảng khách chấm thêm trên cổng khách hàng.
  ["hanh_trinh", "Hành trình"], ["xe", "Chất lượng xe"], ["tham_quan", "Điểm tham quan"], ["tu_van", "Tư vấn & đặt chỗ"],
];

const so = (v: any) => (v === null || v === undefined ? "—" : String(v));
const pct = (v: any) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

function DanhGia() {
  const { toast } = useShell();
  const [loai, setLoai] = useState("hdv");
  const [chiKhach, setChiKhach] = useState(true);
  const [bang, setBang] = useState<any>(null);
  const [cs, setCs] = useState<any>(null);
  const [cho, setCho] = useState<any[]>([]);
  const [ghi, setGhi] = useState<any>(null);

  // Bảng xếp hạng là cửa HẸP HƠN màn hình: nhân viên kinh doanh mở được trang này để làm phần
  // "khách chưa chấm", nhưng cửa bảng điểm trả 403. Không kêu lỗi đỏ ở đó — 403 ở đây là câu trả
  // lời đúng, không phải sự cố. Hàng rào thật nằm ở máy chủ; đây chỉ là không vẽ thứ không lấy được.
  const tai = useCallback(() => {
    api(`/danh-gia/bang-diem/${loai}?chi_khach=${chiKhach}`).then(setBang).catch(() => setBang(null));
    api("/danh-gia/chi-so").then(setCs).catch(() => setCs(null));
    api("/danh-gia/chua-tra-loi").then((r: any) => setCho(r.rows || [])).catch(() => setCho([]));
  }, [loai, chiKhach]);
  useEffect(() => { tai(); }, [tai]);

  const luuGhiHo = async (e: React.FormEvent) => {
    e.preventDefault();
    const f = e.target as HTMLFormElement;
    const d: any = Object.fromEntries(new FormData(f).entries());
    // Ô để TRỐNG gửi lên là null, không phải 0 — khách không có mục ấy thì mục ấy rỗng.
    const muc = ["tour", "hdv", "tai_xe", "khach_san", "an_uong"]
      .filter((k) => String(d[k] || "").trim() !== "" || String(d[`nx_${k}`] || "").trim() !== "")
      .map((k) => ({ doi_tuong: k, diem: String(d[k] || "").trim() === "" ? null : Number(d[k]),
                     nhan_xet: String(d[`nx_${k}`] || "") }));
    if (!muc.length) { toast("Chưa chấm mục nào", true); return; }
    try {
      await api(`/danh-gia/ghi-ho/${ghi.care_id}`, { method: "POST", json: { diem: muc } });
      toast("Đã ghi hộ khách"); setGhi(null); tai();
    } catch (x) { toast(errMsg(x), true); }
  };

  const T = cs || {};
  return (<>
    <h1>Đánh giá sau tour</h1>
    <p className="muted">Điểm do khách tự chấm qua đường dẫn gửi trong tin Zalo sau khi chuyến kết thúc.
      Khách không dùng Zalo thì nhân viên ghi hộ ở màn hình <b>Chăm sóc sau bán</b> — phần ấy được đánh dấu riêng.</p>

    <div className="kpis">
      <div className="kpi"><b>{so(T.tin_da_gui)}</b><span>Tin đã gửi</span></div>
      <div className="kpi"><b>{so(T.khach_mo)}</b><span>Khách mở đường dẫn</span></div>
      <div className="kpi"><b>{so(T.khach_tra_loi)}</b><span>Khách đã chấm điểm</span></div>
      <div className="kpi"><b style={{ color: T.tin_loi ? "var(--red)" : undefined }}>{so(T.tin_loi)}</b><span>Tin KHÔNG gửi được</span></div>
      <div className="kpi"><b>{pct(T.ty_le_tra_loi)}</b><span>Tỷ lệ trả lời</span></div>
    </div>
    {T.luu_y && <div className="gate">{T.luu_y}</div>}

    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", margin: "14px 0" }}>
      {LOAI.map(([k, l]) => (
        <button key={k} className={"act " + (loai === k ? "" : "grey")} style={{ margin: 0 }}
          onClick={() => setLoai(k)}>{l}</button>
      ))}
      <button className={"act " + (chiKhach ? "teal" : "grey")} style={{ margin: 0, marginLeft: 12 }}
        onClick={() => setChiKhach(!chiKhach)}>
        {chiKhach ? "Chỉ điểm khách tự chấm" : "Gồm cả điểm nhân viên ghi hộ"}
      </button>
    </div>

    {/* KHỐI VIỆC: khách đã được mời mà chưa chấm. Mục 6 của đề xuất giao nhóm này cho sale đã
        bán tour — câu ấy chỉ thành việc làm được khi có danh sách và có nút. */}
    <div className="panel wrap">
      <h2>Khách chưa chấm điểm ({cho.length})</h2>
      <p className="muted">Hai nhóm khác nhau: <b>không gửi được tin</b> nghĩa là khách chưa từng biết có ai hỏi —
        nhóm này phải gọi. <b>Đã gửi mà chưa mở</b> thì hệ thống còn nhắc một lần nữa.</p>
      <table>
        <thead><tr><th>Khách</th><th>Chuyến</th><th>Người bán</th><th>Tình trạng</th><th className="num">Lượt mở</th><th></th></tr></thead>
        <tbody>{cho.length ? cho.map((r: any) => (
          <tr key={r.care_id}>
            <td><b>{r.khach}</b></td>
            <td>{r.tour_ma}<div className="muted">{r.tour_ten}</div></td>
            <td>{r.nguoi_ban || "—"}</td>
            <td>{r.tin_loi && !r.tin_da_gui ? <Tag cls="red">{r.tinh_trang}</Tag> : <Tag cls="warn">{r.tinh_trang}</Tag>}</td>
            <td className="num">{r.so_lan_mo}</td>
            <td><button className="act grey" style={{ padding: "2px 6px", margin: 0 }}
              onClick={() => setGhi(r)}>ghi hộ</button></td>
          </tr>
        )) : <tr><td colSpan={6} className="muted">Không còn khách nào chờ chấm điểm.</td></tr>}</tbody>
      </table>
    </div>

    {ghi && <div className="panel"><h2>Ghi hộ khách {ghi.khach} · {ghi.tour_ma}</h2>
      <p className="muted">Dùng khi khách không dùng Zalo, hoặc gọi điện xin sửa. Bản ghi này được
        đánh dấu là <b>nhân viên ghi hộ</b> và KHÔNG cộng vào bảng xếp hạng mặc định — đó là chỗ giữ
        cho bảng điểm còn đọc được khi người ghi cũng là người bị chấm.</p>
      <form onSubmit={luuGhiHo}>
        <div className="grid">
          {[["tour", "Chuyến đi"], ["hdv", "Hướng dẫn viên"], ["tai_xe", "Tài xế"],
            ["khach_san", "Khách sạn"], ["an_uong", "Ăn uống"]].map(([k, l]) => (
            <div key={k}>
              <label>{l} (1–5, để trống nếu chuyến không có)</label>
              <input name={k} type="number" min={1} max={5} />
              <input name={`nx_${k}`} placeholder="Lời khách nói (nếu có)" style={{ marginTop: 6 }} />
            </div>
          ))}
        </div>
        <button className="act teal" type="submit">Lưu</button>{" "}
        <button type="button" className="act grey" onClick={() => setGhi(null)}>Đóng</button>
      </form>
    </div>}

    {bang && <>
      <div className="panel wrap">
        <h2>{bang.ten_loai} · {bang.tu} → {bang.den}</h2>
        <table>
          <thead><tr><th>Tên</th><th className="num">Số lượt chấm</th><th className="num">Điểm trung bình</th><th className="num">Lượt ≤3 sao</th></tr></thead>
          <tbody>{bang.rows.length ? bang.rows.map((r: any, i: number) => (
            <tr key={`${r.id ?? "x"}-${i}`}>
              <td><b>{r.ten}</b></td>
              <td className="num">{r.so_luot}</td>
              {/* Điểm trung bình và số lượt đọc CÙNG LÚC: một bảng xếp hạng dựng trên mười lượt
                  chấm không phải là một bảng xếp hạng. */}
              <td className="num"><b style={{ color: r.diem_tb !== null && r.diem_tb < 3.5 ? "var(--red)" : undefined }}>
                {r.diem_tb === null ? "—" : r.diem_tb.toFixed(2)}</b>
                {r.so_luot < 10 && <div className="muted">ít lượt</div>}</td>
              <td className="num">{r.so_luot_thap ? <Tag cls="warn">{r.so_luot_thap}</Tag> : "0"}</td>
            </tr>
          )) : <tr><td colSpan={4} className="muted">Chưa có lượt chấm nào trong kỳ.</td></tr>}</tbody>
        </table>
      </div>
      <p className="muted">{bang.luu_y}</p>
    </>}
  </>);
}

export default function Page() { return <Shell><DanhGia /></Shell>; }
