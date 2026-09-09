"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, getToken } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lệnh điều xe – Đợt 4.
 *
 *  Màn hình này gợi ý, không quyết. Đặc tả đặt ranh giới rõ: "Không để quyết định cho xe xuất bến phụ thuộc
 *  vào kết luận của mô hình ngôn ngữ." Nên phần lọc và xếp hạng là mã xác định, còn người chốt lệnh vẫn là
 *  người quyết — và nếu chọn khác gợi ý thì phải ghi lý do. */
function LenhDieuXe() {
  const { toast } = useShell();
  const [tu, setTu] = useState(new Date().toISOString().slice(0, 10));
  const [den, setDen] = useState(new Date().toISOString().slice(0, 10));
  const [khach, setKhach] = useState(0);
  const [km, setKm] = useState(0);
  const [gy, setGy] = useState<any>(null);
  const [ds, setDs] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  // Mẫu chốt lệnh. Trước 09/9/2026 màn hình này chỉ XEM: có bảng gợi ý, có bảng lệnh đã lập, không có
  // nút chốt. Mẫu lập lệnh duy nhất nằm ở /ops?tab=fleet – mà menu của gd_doi_xe không có /ops, trong
  // khi tham số xe_nguoi_lap_lenh lại chỉ định chính ông là người DUY NHẤT được chốt lệnh. Kết quả:
  // người được phép thì không thấy mẫu, người thấy mẫu thì không được phép.
  const [nen, setNen] = useState<any>(null);          // tour & bảng giá để lập lệnh
  const [chon, setChon] = useState<any>(null);        // phương án đang chốt
  const [tour, setTour] = useState("");
  const [rate, setRate] = useState("");
  const [lyDo, setLyDo] = useState("");
  const [hoi, setHoi] = useState<any>(null);          // máy chủ đòi lý do: giữ nhận xét của máy để người ký đọc

  const load = useCallback(async () => {
    try { setDs(await api("/fleet/lenh-dieu-xe")); } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  // Nạp danh sách tour NGAY KHI MỞ TRANG, và mỗi lần đổi khoảng ngày.
  //
  // Bản đầu (09/9/2026) chỉ nạp khi bấm "Xem phương án", vì mẫu chốt lệnh dùng chung khoảng ngày với
  // bảng gợi ý. Soi trên web thật thì thấy hậu quả đúng bằng chỗ hỏng bản này sinh ra để chữa: người
  // phụ trách mở trang lên, chỉ thấy ô tìm ngày và bảng lệnh cũ, rồi kết luận màn hình này chỉ để xem.
  // Một cái cửa chỉ hiện ra sau khi người ta đoán đúng phải bấm nút nào thì cũng gần bằng không có cửa.
  const nenRef = useCallback(async (a: string, b: string) => {
    try { setNen(await api(`/fleet/de-lap-lenh?tu=${a}&den=${b}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { if (tu && den && den >= tu) nenRef(tu, den); }, [tu, den, nenRef]);

  const chay = async () => {
    setBusy(true);
    try {
      setGy(await api(`/fleet/goi-y-dieu-xe?date_from=${tu}&date_to=${den}&so_khach=${khach}&km_du_kien=${km}`));
      setChon(null); setHoi(null); setLyDo("");
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  /** Chốt lệnh. Gọi thẳng fetch chứ không qua api() vì một lý do cụ thể:
   *
   *  Khi xe được chọn có điểm THẤP HƠN nhóm đề xuất, máy chủ trả 422 kèm cả nhận xét của mình –
   *  "he_thong_nhan_xet" – tức là nó chê xe này ở điểm gì. api() rút gọn lỗi còn mỗi câu message, nên
   *  người chốt lệnh sẽ chỉ đọc được "phải ghi lý do" mà không biết mình đang bác lại nhận xét nào.
   *  Một ô lý do không biết đang trả lời câu gì thì sẽ được điền cho xong, và ít lâu sau tính năng bị tắt. */
  const chot = async (p: any, lyDoGui: string) => {
    if (!tour) { toast("Chọn tour trước khi chốt lệnh", true); return; }
    setBusy(true);
    try {
      const r = await fetch("/api/v1/dispatch", { method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken() || ""}` },
        body: JSON.stringify({ tour_id: Number(tour), vehicle_id: p.vehicle_id, date_from: tu, date_to: den,
          rate_id: rate ? Number(rate) : null, so_khach: khach, km_du_kien: km,
          ly_do_khac_goi_y: lyDoGui.trim() }) });
      const d = await r.json().catch(() => null);
      if (r.ok) {
        toast(d?.message || "Đã lập lệnh"); setHoi(null); setLyDo(""); setChon(null); load();
      } else if (r.status === 422 && d?.detail?.he_thong_nhan_xet !== undefined) {
        setChon(p); setHoi(d.detail);       // giữ nguyên mẫu, mở ô lý do kèm nhận xét của máy
      } else {
        toast(typeof d?.detail === "string" ? d.detail : d?.detail?.message || `Lỗi ${r.status}`, true);
      }
    } catch (e) { toast(errMsg(e), true); }
    setBusy(false);
  };

  const matTour = nen?.tour?.find((t: any) => String(t.id) === tour);
  const coQuyen = nen ? nen.toi_duoc_lap : false;

  return (<>
    <h1>Lệnh điều xe</h1>
    <p className="muted">Đây là nơi <b>lập và chốt lệnh điều xe</b>: chọn tour bên dưới, đặt khoảng ngày và số khách, xem phương án, rồi bấm <b>Chốt lệnh</b> ngay trên dòng xe đã chọn.</p>
    <p className="muted">Hệ thống <b>lọc cứng trước, xếp hạng sau</b>: xe vi phạm điều kiện không xuất hiện trong gợi ý dù điểm có cao đến đâu. Đây là gợi ý — người chốt lệnh vẫn quyết, và chọn khác gợi ý thì phải ghi lý do.</p>

    <div className="panel"><h2>Tìm phương án cho một khoảng ngày</h2>
      <div className="grid">
        <div><label>Từ ngày</label><input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></div>
        <div><label>Đến ngày</label><input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></div>
        <div><label>Số khách</label><input type="number" value={khach} onChange={(e) => setKhach(Number(e.target.value))} /></div>
        <div><label>Km dự kiến (gồm chạy rỗng)</label><input type="number" value={km} onChange={(e) => setKm(Number(e.target.value))} /></div>
      </div>
      <button className="act teal" onClick={chay} disabled={busy}>{busy ? "Đang tính…" : "Xem phương án"}</button>
    </div>

    {nen && <div className="panel"><h2>Lệnh sẽ lập cho tour nào</h2>
      {!coQuyen && <p className="muted"><Tag cls="warn">chỉ xem</Tag>{" "}
        {nen.nguoi_duoc_lap_lenh.length
          ? <>Chỉ {nen.nguoi_duoc_lap_lenh.map((x: any) => `${x.full_name} (${x.username})`).join(", ")} được chốt lệnh (chỉ đạo Chủ tịch 07/9/2026). Đổi người phụ trách thì sửa tham số <b>xe_nguoi_lap_lenh</b>.</>
          : nen.ly_do_khong_gioi_han}</p>}
      <div className="grid">
        <div><label>Tour cần xe trong khoảng ngày này</label>
          <select value={tour} onChange={(e) => setTour(e.target.value)}>
            <option value="">– chọn tour –</option>
            {nen.tour.map((t: any) => <option key={t.id} value={t.id}>
              {t.code} · {t.name} · {fmtD(t.start_date)}→{fmtD(t.end_date)}{t.planned_pax ? ` · ${t.planned_pax} khách` : ""}
            </option>)}
          </select></div>
        <div><label>Tuyến trong bảng giá (để trống thì tính theo đơn giá ngày của xe)</label>
          <select value={rate} onChange={(e) => setRate(e.target.value)}>
            <option value="">– không theo bảng giá –</option>
            {nen.bang_gia.map((r: any) => <option key={r.id} value={r.id}>
              {r.route}{r.days ? ` · ${r.days} ngày` : ""} · nội bộ {r.internal_price?.toLocaleString("vi-VN")}
            </option>)}
          </select></div>
      </div>
      {!nen.tour.length && <p className="muted">Không có tour nào chạy trong khoảng ngày này. Đổi khoảng ngày ở ô trên, hoặc chờ Điều hành lập chuyến.</p>}
      {tour && !gy && <p className="muted"><Tag cls="warn">còn một bước</Tag> Đã chọn tour. Bấm <b>Xem phương án</b> ở khối trên để hệ thống lọc xe đủ điều kiện — nút Chốt lệnh nằm trên từng dòng xe được đề xuất.</p>}
      {matTour && matTour.planned_pax > 0 && khach === 0 &&
        <p className="muted"><Tag cls="warn">lưu ý</Tag> Tour này dự kiến {matTour.planned_pax} khách nhưng ô "Số khách" đang để 0 – gợi ý đang xếp hạng cho một chuyến không khách. Điền số khách rồi xem lại phương án.</p>}
      <p className="muted">{nen.ghi_chu}</p>
    </div>}

    {hoi && chon && <div className="panel"><h2>Hệ thống đánh giá xe này thấp hơn nhóm đề xuất</h2>
      <p>Xe <b>{chon.ma_xe} · {chon.xe}</b> được {hoi.diem_xe_chon} điểm, thấp nhất trong nhóm đề xuất là {hoi.diem_thap_nhat_trong_nhom_de_xuat} điểm.</p>
      {hoi.he_thong_nhan_xet?.length > 0 && <><p className="muted">Máy nhận xét về xe anh chọn:</p>
        <ul>{hoi.he_thong_nhan_xet.map((l: string, i: number) => <li key={i}>{l}</li>)}</ul></>}
      <p className="muted">Đây không phải nút chặn – anh vẫn chốt được. Nhưng lý do phải nằm lại trong hồ sơ, vì đây là dữ liệu duy nhất để mỗi quý biết thuật toán gợi ý có tốt lên không.</p>
      <div><label>Vì sao vẫn chọn xe này</label>
        <textarea rows={2} value={lyDo} onChange={(e) => setLyDo(e.target.value)}
          placeholder="Ví dụ: khách quen yêu cầu đúng xe này; xe điểm cao hơn đang chờ nghiệm thu bảo dưỡng" /></div>
      <button className="act orange" disabled={busy || !lyDo.trim()} onClick={() => chot(chon, lyDo)}>Chốt lệnh kèm lý do</button>{" "}
      <button className="act grey" onClick={() => { setHoi(null); setChon(null); setLyDo(""); }}>Bỏ, chọn xe khác</button>
    </div>}

    {gy && <>
      <div className="panel"><h2>Phương án đề xuất ({gy.phuong_an.length})</h2>
        <p className="muted">{gy.ghi_chu} <span className="muted">Bộ quy tắc {gy.rule_version}.</span></p>
        {gy.phuong_an.length ? <table><thead><tr><th>#</th><th>Xe</th><th>Chỗ</th><th>Điểm</th><th>Vì sao đề xuất</th><th>Điều kiện</th><th>Chốt</th></tr></thead>
          <tbody>{gy.phuong_an.map((p: any, i: number) => <tr key={p.vehicle_id}>
            <td><b>{i + 1}</b></td><td>{p.ma_xe} · {p.xe}</td><td className="num">{p.so_cho}</td>
            <td className="num">{p.diem}</td>
            <td>{p.ly_do.join(" · ")}</td>
            <td><Tag cls={p.muc_kiem_tra === "OK" ? "ok" : "warn"}>{p.muc_kiem_tra === "OK" ? "Đạt" : p.muc_kiem_tra === "UNKNOWN" ? "Chưa đủ dữ liệu" : "Cần xem lại"}</Tag></td>
            <td>{coQuyen && <button className="act teal" style={{ margin: 0 }} disabled={busy || !tour}
              title={tour ? "" : "Chọn tour trước"} onClick={() => chot(p, "")}>Chốt lệnh</button>}</td>
          </tr>)}</tbody></table>
          : <p className="muted">Không còn xe nào hợp lệ cho khoảng ngày này.</p>}
        {gy.con_lai > 0 && <p className="muted">Còn {gy.con_lai} xe hợp lệ khác không nằm trong nhóm đề xuất.</p>}
      </div>

      {gy.bi_loai.length > 0 && <div className="panel wrap"><h2>Xe bị loại ({gy.bi_loai.length})</h2>
        <p className="muted">Loại ở bước lọc cứng — không phải điểm thấp, mà là không đủ điều kiện.</p>
        <table><thead><tr><th>Xe</th><th>Lý do loại</th></tr></thead>
          <tbody>{gy.bi_loai.map((b: any) => <tr key={b.vehicle_id}>
            <td>{b.ma_xe} · {b.xe}</td><td>{b.ly_do.map((l: string, i: number) => <div key={i}><Tag cls="red">chặn</Tag> {l}</div>)}</td>
          </tr>)}</tbody></table>
      </div>}
    </>}

    <div className="panel wrap"><h2>Lệnh đã lập ({ds.length})</h2>
      <p className="muted">Cột cuối ghi vết: lệnh theo gợi ý hay chọn khác, và lý do khi chọn khác. Đây là dữ liệu để mỗi quý đánh giá lại chất lượng thuật toán gợi ý.</p>
      <table><thead><tr><th>#</th><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Từ → đến</th><th>Giá nội bộ</th><th>Trạng thái</th><th>Ghi vết gợi ý</th></tr></thead>
        <tbody>{ds.length ? ds.map((d) => <tr key={d.id}>
          <td>{d.id}</td><td>{d.tour}</td><td>{d.ma_xe} · {d.xe}</td><td>{d.tai_xe}</td>
          <td>{fmtD(d.date_from)} → {fmtD(d.date_to)} <span className="muted">({d.so_ngay} ngày)</span></td>
          <td className="num">{d.internal_price?.toLocaleString("vi-VN")}</td>
          <td>{d.status === "hoan_thanh" ? <Tag cls="ok">hoàn thành</Tag> : d.status === "da_xac_nhan" ? <Tag cls="ok">đã xác nhận</Tag> : d.status === "huy" ? <Tag cls="red">hủy</Tag> : <Tag cls="warn">chờ xác nhận</Tag>}</td>
          <td>{d.ly_do_khac_goi_y ? <><Tag cls="warn">chọn khác gợi ý</Tag> <div className="muted">{d.ly_do_khac_goi_y}</div></>
            : d.phuong_an_da_chon ? <Tag cls="ok">theo gợi ý</Tag> : <span className="muted">lệnh cũ, chưa có ghi vết</span>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có lệnh điều xe nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

export default function Page() { return <Shell><LenhDieuXe /></Shell>; }
