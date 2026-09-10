"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, soTien, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lãi lỗ theo tour – hai lớp, một chuẩn phép tính.
 *
 *  Khảo sát 09/9/2026 tìm ra VTOS đang có BỐN công thức lãi lỗ tour ở bốn tệp khác nhau, đều đang chạy,
 *  và không cho cùng một con số. Màn hình này KHÔNG tự cộng lấy: mọi số đều lấy từ /api/v1/lai-lo-tour,
 *  vì bốn công thức song song kia sinh ra chính vì mỗi màn hình từng tự cộng một kiểu.
 *
 *  Hai điều màn hình phải nói ra, không được giấu:
 *   1. Dòng nào CHƯA có giá vốn thì để TRỐNG ở cột lợi nhuận, không hiện 0. Hiện 0 là báo lãi 100%.
 *   2. Tổng ở chân bảng chỉ cộng dòng đã có giá vốn, và phải ghi rõ đã bỏ ra bao nhiêu dòng. */

const NHAN: Record<string, { ten: string; cls: string }> = {
  quyet_toan_chi_tiet: { ten: "Quyết toán chi tiết", cls: "green" },
  quyet_toan_tong: { ten: "Quyết toán tổng", cls: "" },
  thieu_gia_von: { ten: "Chưa có giá vốn", cls: "red" },
  chua_co_so: { ten: "Chưa có số", cls: "muted" },
};

const so = (v: any) => (v === null || v === undefined
  ? <span className="muted" title="Chưa có số – khác với bằng 0">—</span>
  : <>{vnd(v)}</>);
const pc = (v: any) => (v === null || v === undefined
  ? <span className="muted">—</span>
  : <span className={Number(v) < 0 ? "red" : ""}>{(Number(v) * 100).toFixed(1)}%</span>);

/** Bốn mặt của bản quyết toán Điều hành – lớp 2 phần đến từ TỆP, không phải từ sổ VTOS.
 *
 *  Đặt ở đây, trong màn hình lãi lỗ sẵn có, chứ không dựng màn hình quyết toán riêng. Tệp
 *  lai_lo_tour.py sinh ra ngày 09/9 vì VTOS lúc ấy có bốn công thức lãi lỗ tour chạy song song cho ra
 *  bốn con số; thêm một màn hình quyết toán hai lớp nữa là tạo công thức thứ năm, và lần này còn khó
 *  thấy hơn vì hai màn hình sẽ trông giống hệt nhau.
 *
 *  Số tổng của chuyến vẫn do chuẩn phép tính ở /api/v1/lai-lo-tour quyết. Khối này chỉ nói thêm hai
 *  điều: số ấy đến từ đâu, và chỗ nào trong tệp gốc không khớp nhau. */
function BanQuyetToan({ q }: { q: any }) {
  const [mat, setMat] = useState<"khach" | "chiet_tinh" | "hdv" | "booking">("khach");
  const TAB: [string, string, number][] = [
    ["khach", "Từng khách", q.khach.length],
    ["chiet_tinh", "Chiết tính", q.chiet_tinh.length],
    ["hdv", "Chi trên tour của HDV", q.hdv_chi.length],
    ["booking", "Doanh thu theo booking", q.booking.length],
  ];
  return (<>
    <h4 style={{ marginTop: 18 }}>Quyết toán của Điều hành — {q.ten_tep || "tệp đã nạp"}</h4>

    {/* Phát hiện đối chiếu hiện TRƯỚC bảng số, không giấu xuống cuối. Ba chỗ vênh đo được trên tệp
        thật đều thuộc loại đọc lướt sẽ bỏ qua: ngày khởi hành lệch giữa các sheet, số khách lệch,
        HDV chi nhiều hơn chiết tính. */}
    {(q.phat_hien || []).length > 0 && <div className="gate fail">
      <b>Các sheet trong tệp nói khác nhau ở {q.phat_hien.length} chỗ</b>
      <ul style={{ margin: "6px 0 0 16px", fontSize: 13 }}>
        {q.phat_hien.map((x: string, i: number) => <li key={i}>{x}</li>)}
      </ul>
      <p className="muted" style={{ fontSize: 12, marginTop: 6 }}>
        Hệ thống KHÔNG tự chọn nguồn nào đúng — nó giữ nguyên số của từng nguồn để Điều hành sửa tệp
        gốc. Chọn hộ một lần là sau đó không còn dấu vết nào cho thấy đã từng có hai số.
      </p>
    </div>}

    <div className="kpis">
      <div className="kpi"><b>{q.so_dong_khach}</b><span>dòng khách</span></div>
      <div className="kpi"><b>{q.so_khach_tep_ghi ?? "—"}</b><span>số khách tệp ghi</span></div>
      <div className="kpi"><b>{so(q.gia_ban)}</b>
        <span>giá bán{q.nhieu_muc_gia ? " (nhiều mức)" : ""}</span></div>
      <div className="kpi"><b>{q.so_dong_chi_co_chung_tu}/{q.so_dong_chi}</b>
        <span>dòng chi có chứng từ</span></div>
      <div className="kpi"><b>{q.so_chung_tu_co_mst}</b><span>dòng có MST nhà cung cấp</span></div>
    </div>

    {/* Chênh giữa lớp 1 và tổng lớp 2. Hiện cả khi bằng 0: "đã đối chiếu, khớp" khác với "chưa đối
        chiếu bao giờ", và một ô trống không phân biệt được hai chuyện đó. */}
    <p className="muted" style={{ fontSize: 12 }}>
      Chênh giữa số tổng và cộng dòng: thu {so(q.chenh_thu)} · chi {so(q.chenh_chi)}
    </p>

    <div className="row" style={{ gap: 6, margin: "10px 0" }}>
      {TAB.map(([k, ten, n]) => (
        <button key={k} className={"act sm" + (mat === k ? "" : " ghost")}
                onClick={() => setMat(k as any)}>{ten} ({n})</button>))}
    </div>

    {mat === "khach" && <table><thead><tr>
      <th className="num">STT</th><th>Sale</th><th>Tên khách</th>
      <th className="num">Giá bán</th><th className="num">Thu khác</th><th className="num">Tổng thu</th>
      <th>Các khoản chi</th><th className="num">Tổng chi</th><th className="num">Lợi nhuận</th>
    </tr></thead><tbody>
      {q.khach.map((k: any, i: number) => (<tr key={i} style={k.co_lech ? { background: "var(--warnbg)" } : undefined} title={k.co_lech || ""}>
        <td className="num">{k.stt}</td><td>{k.sales}</td><td>{k.ten_khach}</td>
        <td className="num">{so(k.gia_ban)}</td><td className="num">{so(k.thu_khac)}</td>
        <td className="num">{so(k.tong_thu)}</td>
        <td style={{ fontSize: 12 }}>{k.khoan_chi.map((c: any, j: number) => (
          <span key={j} title={c.ma_khoan ? c.ten_khoan : "Nhãn chưa được xếp mã — chờ người ánh xạ"}>
            {c.nhan}: {vnd(c.so_tien)}{c.ma_khoan ? "" : " ⚑"}{j < k.khoan_chi.length - 1 ? " · " : ""}
          </span>))}</td>
        <td className="num">{so(k.tong_chi)}</td><td className="num">{so(k.loi_nhuan)}</td>
      </tr>))}
    </tbody></table>}

    {mat === "chiet_tinh" && <><table><thead><tr>
      <th>Vế</th><th>Nhóm</th><th>Nội dung</th><th>Đối tác</th>
      <th className="num">Đơn giá</th><th className="num">SL</th><th className="num">Hệ số</th>
      <th className="num">Thành tiền</th><th>Số chứng từ</th><th>MST</th>
    </tr></thead><tbody>
      {q.chiet_tinh.map((x: any, i: number) => (<tr key={i} style={x.co_lech ? { background: "var(--warnbg)" } : undefined} title={x.co_lech || ""}>
        <td>{x.ve === "thu" ? "Thu" : "Chi"}</td><td style={{ fontSize: 12 }}>{x.nhom}</td>
        <td>{x.noi_dung}</td><td>{x.doi_tac}</td>
        <td className="num">{so(x.don_gia)}</td><td className="num">{x.so_luong ?? ""}</td>
        <td className="num">{x.he_so ?? ""}</td><td className="num">{so(x.thanh_tien)}</td>
        <td>{x.so_chung_tu || <span className="muted">—</span>}</td>
        <td>{x.mst_ncc || <span className="muted">—</span>}</td>
      </tr>))}
    </tbody></table>
    <p className="muted" style={{ fontSize: 12 }}>
      Thành tiền phải bằng <b>đơn giá × số lượng × hệ số</b> — cột “DIỄN GIẢI” trong tệp chính là hệ
      số (số đêm lưu trú, số bữa ăn). Dòng nào lệch được tô cảnh báo: đó là chỗ có người gõ tay đè lên
      công thức. Cột MST là thứ nối bản quyết toán này với bảng kê thuế GTGT đầu vào.
    </p></>}

    {mat === "hdv" && <><table><thead><tr>
      <th>Nội dung</th><th className="num">Đơn giá</th><th className="num">SL</th>
      <th className="num">Tổng chi</th><th className="num">Tiền ứng</th><th className="num">Dư</th>
      <th className="num">CTP</th><th>Ghi chú</th>
    </tr></thead><tbody>
      {q.hdv_chi.map((x: any, i: number) => (<tr key={i} style={x.la_dong_tong ? { fontWeight: 600 } : undefined}>
        <td>{x.noi_dung}</td><td className="num">{so(x.don_gia)}</td>
        <td className="num">{x.so_luong ?? ""}</td><td className="num">{so(x.tong_chi)}</td>
        <td className="num">{so(x.tien_ung)}</td><td className="num">{so(x.du)}</td>
        <td className="num">{so(x.ctp)}</td><td>{x.ghi_chu || ""}</td>
      </tr>))}
    </tbody></table>
    <p className="muted" style={{ fontSize: 12 }}>
      HDV chi theo số khách <b>thực đi</b>, chiết tính lập theo số khách <b>đã đặt</b>. Phần chênh là
      tiền đã ra khỏi công ty mà chưa vào giá vốn — nó không nằm trong giá vốn, không trong công nợ,
      cũng không trong hoàn ứng. Không có bảng này thì khoản đó vô hình ở mọi chuyến.
    </p></>}

    {mat === "booking" && <table><thead><tr>
      <th>Mã booking</th><th>Người book</th><th>Điện thoại</th><th className="num">Khách</th>
      <th className="num">Tổng thu</th><th className="num">Đã đóng</th><th className="num">Còn phải thu</th>
      <th>Người bán</th><th>Nối vào VTOS</th>
    </tr></thead><tbody>
      {q.booking.map((b: any, i: number) => (<tr key={i}>
        <td>{b.ma_booking_nguon}</td><td>{b.ten_nguoi_book}</td><td>{b.dien_thoai}</td>
        <td className="num">{b.so_khach ?? ""}</td><td className="num">{so(b.tong_thu)}</td>
        <td className="num">{so(b.da_dong)}</td>
        <td className={"num " + (b.con_phai_thu ? "red" : "")}>{so(b.con_phai_thu)}</td>
        <td>{b.nguoi_ban}</td>
        <td>{b.booking_id
          ? <Tag cls="ok">đã nối</Tag>
          : <Tag cls="">chưa tra ra</Tag>}</td>
      </tr>))}
    </tbody></table>}
  </>);
}


function LaiLoTour() {
  const { user, toast } = useShell();
  const [loai, setLoai] = useState<"ghep" | "le" | "tat_ca">("ghep");
  const [tt, setTt] = useState("ket_thuc");
  const [tu, setTu] = useState("");
  const [den, setDen] = useState("");
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [mo, setMo] = useState<any>(null);      // tour đang mở lớp 2
  const [hd, setHd] = useState<any>(null);      // dòng chi phí đang nhập hoá đơn

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const q = new URLSearchParams({ loai, gioi_han: "200" });
      if (tt) q.set("trang_thai", tt);
      if (tu) q.set("tu", tu);
      if (den) q.set("den", den);
      setD(await api(`/lai-lo-tour?${q}`));
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  }, [loai, tt, tu, den, toast]);
  useEffect(() => { load(); }, [load]);

  const moTour = async (r: any) => {
    try { setMo(await api(`/lai-lo-tour/${r.tour_id}`)); }
    catch (e) { toast(errMsg(e), true); }
  };

  const luuHoaDon = async () => {
    try {
      await api(`/lai-lo-tour/dong-chi-phi/${hd.line_id}/hoa-don`, { method: "PUT", json: {
        so_hoa_don: hd.so_hoa_don || null, ngay_hoa_don: hd.ngay_hoa_don || null,
        vat_hoa_don: soTien(hd.vat_hoa_don) } });
      toast("Đã ghi hoá đơn đầu vào");
      const t = mo.tong_hop.tour_id; setHd(null); setMo(await api(`/lai-lo-tour/${t}`)); load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const c = d?.cong;
  return (<>
    <h2>Lãi lỗ theo tour</h2>
    <p className="muted" style={{ marginTop: -6 }}>
      Doanh thu = tiền booking chưa huỷ + phí huỷ giữ lại. Giá vốn = thực chi các dòng quyết toán +
      giá trị khuyến mãi. Ô để <b>trống</b> nghĩa là chưa có số – khác hẳn với bằng 0.
    </p>

    <div className="grid" style={{ gridTemplateColumns: "repeat(4, minmax(120px, 1fr))", gap: 8 }}>
      <div><label>Loại</label>
        <select value={loai} onChange={(e) => setLoai(e.target.value as any)}>
          <option value="ghep">Tour ghép</option>
          <option value="le">Dịch vụ lẻ</option>
          <option value="tat_ca">Tất cả</option>
        </select></div>
      <div><label>Trạng thái</label>
        <select value={tt} onChange={(e) => setTt(e.target.value)}>
          <option value="ket_thuc">Đã kết thúc</option>
          <option value="">Tất cả</option>
          <option value="da_duyet">Đã duyệt</option>
        </select></div>
      <div><label>Khởi hành từ</label><input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></div>
      <div><label>Đến</label><input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></div>
    </div>

    {/* Cảnh báo chất lượng đặt Ở ĐẦU bảng. Giấu ở cuối thì người đọc đã ra quyết định xong mới thấy. */}
    {d?.canh_bao?.map((w: any) => (
      <div key={w.loai} className={"note " + (w.muc === "do" ? "red" : "warn")} style={{ marginTop: 10 }}>
        <b>{w.tom_tat}</b>
        <div className="muted" style={{ fontSize: 13 }}>{w.chi_tiet}</div>
        {w.ma_tour?.length ? <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
          {w.ma_tour.join(" · ")}{w.so_dong > w.ma_tour.length ? ` … và ${w.so_dong - w.ma_tour.length} tour nữa` : ""}
        </div> : null}
      </div>))}

    {c && <div className="kpis" style={{ marginTop: 10 }}>
      <div className="kpi"><b>{vnd(c.doanh_thu)}</b><span>doanh thu</span></div>
      <div className="kpi"><b>{vnd(c.gia_von)}</b><span>giá vốn</span></div>
      <div className="kpi"><b className={c.loi_nhuan < 0 ? "red" : ""}>{vnd(c.loi_nhuan)}</b><span>lợi nhuận</span></div>
      <div className="kpi"><b>{pc(c.bien)}</b><span>biên</span></div>
      <div className="kpi"><b>{c.so_dong_tinh}</b><span>tour đã tính</span></div>
      {c.so_dong_bo_qua > 0 && <div className="kpi"><b className="red">{c.so_dong_bo_qua}</b><span>tour KHÔNG tính (chưa có giá vốn)</span></div>}
    </div>}
    {c && <p className="muted" style={{ fontSize: 12 }}>{c.ghi_chu}</p>}

    {busy ? <p className="muted">Đang tính…</p> : <table><thead><tr>
      <th className="num">STT</th><th>Mã tour</th><th>Tên tour</th><th>Khởi hành</th><th>Kết thúc</th>
      <th className="num">Giá bán</th>
      <th className="num">Khách</th><th className="num">Doanh thu</th><th className="num">Giá vốn</th>
      <th className="num">Lợi nhuận</th><th className="num">Biên</th><th>Nguồn số</th><th></th>
    </tr></thead><tbody>
      {(d?.rows || []).map((r: any) => (<tr key={r.tour_id}>
        {/* STT do máy chủ đánh, tính từ đầu bảng chứ không từ đầu trang: trang 3 bắt đầu ở 401.
            Đánh số ở màn hình thì mỗi trang lại từ 1, và người đọc tưởng bảng chỉ có 200 dòng. */}
        <td className="num muted">{r.stt}</td>
        <td>{r.ma_tour}</td>
        <td title={r.ten_tour}>{r.ten_tour?.slice(0, 42)}</td>
        <td>{fmtD(r.ngay_khoi_hanh)}</td><td>{fmtD(r.ngay_ket_thuc)}</td>
        {/* Giá bán NIÊM YẾT, không phải doanh thu chia đầu khách. Rỗng khi tour chưa khai giá –
            không lấp bằng phép chia, vì con số ấy không có trong bảng giá nào. */}
        <td className="num">{so(r.gia_ban)}</td>
        <td className="num">{r.so_khach || <span className="muted">0</span>}</td>
        <td className="num">{so(r.doanh_thu)}</td>
        <td className="num">{so(r.gia_von)}</td>
        <td className={"num " + (r.loi_nhuan !== null && r.loi_nhuan < 0 ? "red" : "")}>{so(r.loi_nhuan)}</td>
        <td className="num">{pc(r.bien)}</td>
        <td><Tag cls={NHAN[r.nguon_so]?.cls}>{NHAN[r.nguon_so]?.ten || r.nguon_so}</Tag></td>
        <td><button className="act sm" onClick={() => moTour(r)}>Chi tiết</button></td>
      </tr>))}
    </tbody></table>}
    {d?.con_nua && <p className="muted">Đang xem {d.rows.length} / {d.tong} tour. Thu hẹp khoảng ngày để xem phần còn lại.</p>}

    {/* ---------- LỚP 2 ---------- */}
    {mo && <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) setMo(null); }}>
      <div className="box wide">
        <h3>{mo.tong_hop.ma_tour} – {mo.tong_hop.ten_tour}</h3>
        <div className="kpis">
          <div className="kpi"><b>{so(mo.tong_hop.doanh_thu)}</b><span>doanh thu</span></div>
          <div className="kpi"><b>{so(mo.tong_hop.gia_von)}</b><span>giá vốn</span></div>
          <div className="kpi"><b>{so(mo.tong_hop.loi_nhuan)}</b><span>lợi nhuận</span></div>
          <div className="kpi"><b>{so(mo.tong_hop.con_phai_thu)}</b><span>còn phải thu</span></div>
          <div className="kpi"><b>{so(mo.tong_hop.con_phai_tra)}</b><span>còn phải trả NCC</span></div>
        </div>

        <h4>Khách của chuyến ({mo.khach.length})</h4>
        <table><thead><tr>
          <th>Tên khách</th><th>Điện thoại</th><th>Mã booking</th><th className="num">Khách</th>
          <th className="num">Doanh thu</th><th className="num">Đã thu</th><th className="num">Còn phải thu</th>
          {mo.co_gia_von_theo_khach && <th className="num">Giá vốn</th>}<th>Trạng thái</th>
        </tr></thead><tbody>
          {mo.khach.map((k: any) => (<tr key={k.booking_id} className={k.da_huy ? "muted" : ""}>
            <td>{k.ten_khach}</td><td>{k.dien_thoai}</td><td>{k.ma_booking}</td>
            <td className="num">{k.so_khach}</td>
            <td className="num">{so(k.doanh_thu)}</td><td className="num">{so(k.da_thu)}</td>
            <td className="num">{so(k.con_phai_thu)}</td>
            {mo.co_gia_von_theo_khach && <td className="num">{so(k.gia_von_khach)}</td>}
            <td>{k.da_huy ? <Tag cls="red">Đã huỷ</Tag> : <Tag>{k.trang_thai_thu || "—"}</Tag>}</td>
          </tr>))}
        </tbody></table>
        {!mo.co_gia_von_theo_khach && <p className="muted" style={{ fontSize: 12 }}>
          {mo.vi_sao_khong_co_gia_von_theo_khach}</p>}

        <h4>Chi phí theo nhà cung cấp ({mo.chi_phi.length})</h4>
        <table><thead><tr>
          <th>Nội dung</th><th>Nhà cung cấp</th><th>Mã số thuế</th><th>Địa chỉ</th>
          <th>Số hoá đơn</th><th>Ngày HĐ</th><th className="num">Thực chi</th><th className="num">Đã trả</th><th></th>
        </tr></thead><tbody>
          {mo.chi_phi.map((l: any) => (<tr key={l.line_id} className={l.trang_thai !== "hd" ? "muted" : ""}>
            <td title={l.mo_ta}>{l.mo_ta?.slice(0, 34)}</td>
            <td>{l.ncc || <span className="muted">—</span>}</td>
            <td>{l.ma_so_thue || <span className="muted">—</span>}</td>
            <td title={l.dia_chi || ""}>{l.dia_chi ? l.dia_chi.slice(0, 22) : <span className="muted">—</span>}</td>
            <td>{l.so_hoa_don || <span className="muted" title="Chưa nhập – không đối chiếu được với tờ khai thuế">chưa có</span>}</td>
            <td>{l.ngay_hoa_don ? fmtD(l.ngay_hoa_don) : <span className="muted">—</span>}</td>
            <td className="num">{so(l.thuc_chi)}</td><td className="num">{so(l.da_tra)}</td>
            <td><button className="act sm" onClick={() => setHd({ ...l })}>Hoá đơn</button></td>
          </tr>))}
        </tbody></table>
        {mo.quyet_toan_dieu_hanh && <BanQuyetToan q={mo.quyet_toan_dieu_hanh} />}
        {!mo.quyet_toan_dieu_hanh && <p className="muted" style={{ fontSize: 12 }}>
          Chuyến này chưa nạp tệp quyết toán chi tiết của Điều hành. Nạp ở <b>Nạp dữ liệu → Quyết toán
          tour – chi tiết một chuyến</b> để có thêm bốn mặt: từng khách, chiết tính (kèm số hoá đơn và
          mã số thuế nhà cung cấp), chi trên tour của HDV, và doanh thu theo booking.</p>}

        <div className="row end"><button className="act ghost" onClick={() => setMo(null)}>Đóng</button></div>
      </div>
    </div>}

    {/* ---------- CỬA NHẬP HOÁ ĐƠN ĐẦU VÀO ---------- */}
    {hd && <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) setHd(null); }}>
      <div className="box">
        <h3>Hoá đơn đầu vào</h3>
        <p className="muted" style={{ fontSize: 13 }}>{hd.mo_ta} — {hd.ncc || "chưa có nhà cung cấp"}</p>
        <label>Số hoá đơn<input value={hd.so_hoa_don ?? ""}
          onChange={(e) => setHd({ ...hd, so_hoa_don: e.target.value })} /></label>
        <label>Ngày hoá đơn<input type="date" value={hd.ngay_hoa_don ?? ""}
          onChange={(e) => setHd({ ...hd, ngay_hoa_don: e.target.value || null })} /></label>
        <label>Tiền thuế GTGT được khấu trừ (đ)<input type="number" value={hd.vat_hoa_don ?? ""}
          onChange={(e) => setHd({ ...hd, vat_hoa_don: e.target.value })} /></label>
        <p className="muted" style={{ fontSize: 12 }}>
          Để trống được cả ba ô – có thể mới cầm số hoá đơn mà chưa có ngày. Trống nghĩa là chưa nhập.
        </p>
        <div className="row end">
          <button className="act ghost" onClick={() => setHd(null)}>Huỷ</button>
          <button className="act" onClick={luuHoaDon}>Lưu</button>
        </div>
      </div>
    </div>}
  </>);
}

export default function Page() { return <Shell><LaiLoTour /></Shell>; }
