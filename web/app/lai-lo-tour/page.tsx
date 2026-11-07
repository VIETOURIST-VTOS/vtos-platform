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
  // globals.css chỉ khai bốn lớp thẻ: ok · warn · red · navy. "green" từng được dùng ở đây và nó
  // không lỗi, không cảnh báo – chỉ lặng lẽ ra một thẻ trơn không màu, tức là mất đúng cái dấu
  // hiệu mà cột "nguồn số" sinh ra để nói.
  quyet_toan_chi_tiet: { ten: "Quyết toán chi tiết", cls: "ok" },
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
  const [mat, setMat] = useState("khach");     // mặt đang mở của bản quyết toán Điều hành

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
      <div key={w.loai} className={w.muc === "do" ? "cb-do" : "cb-vang"} style={{ marginTop: 10 }}>
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
      {c.so_dong_bo_qua > 0 && <div className="kpi"><b className="so-do">{c.so_dong_bo_qua}</b><span>tour KHÔNG tính (chưa có giá vốn)</span></div>}
    </div>}
    {c && <p className="muted" style={{ fontSize: 12 }}>{c.ghi_chu}</p>}

    {busy ? <p className="muted">Đang tính…</p> : <table><thead><tr>
      <th>Mã tour</th><th>Tên tour</th><th>Khởi hành</th><th>Kết thúc</th>
      <th className="num">Khách</th><th className="num">Doanh thu</th><th className="num">Giá vốn</th>
      <th className="num">Lợi nhuận</th><th className="num">Biên</th><th>Nguồn số</th><th></th>
    </tr></thead><tbody>
      {(d?.rows || []).map((r: any) => (<tr key={r.tour_id}>
        <td>{r.ma_tour}</td>
        <td title={r.ten_tour}>{r.ten_tour?.slice(0, 42)}</td>
        <td>{fmtD(r.ngay_khoi_hanh)}</td><td>{fmtD(r.ngay_ket_thuc)}</td>
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
        <BanQuyetToan qt={mo.quyet_toan_dieu_hanh} mat={mat} setMat={setMat} />

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

/** Bốn mặt của bản quyết toán Điều hành – KHÔNG phải một màn hình quyết toán thứ hai.
 *
 *  Bốn mặt vì tệp quyết toán của Điều hành trả lời bốn loại câu hỏi khác nhau, và gộp chúng vào một
 *  bảng thì mất hết:
 *    khách      – ai đi, bán bao nhiêu, chi cho người ấy bao nhiêu
 *    chiết tính – từng khoản mua vào: đối tác, đơn giá, số chứng từ, MÃ SỐ THUẾ (lý do mặt này tồn
 *                 tại: không có MST thì đối chiếu tờ khai thuế phải mở lại từng tệp Excel gốc)
 *    HDV        – tiền ứng và chi của hướng dẫn viên, và số dư phải hoàn
 *    booking    – doanh thu theo booking nguồn, để ghép ngược về hệ bán hàng
 *
 *  MỌI SỐ Ở ĐÂY LÀ SỐ TRONG TỆP, không phải số chuẩn của hệ thống. Số chuẩn nằm ở lớp 1 và ở phần
 *  trên của lớp 2; khối này chỉ nói "tệp gốc ghi gì" và "chỗ nào không khớp". Trộn hai thứ ấy chính
 *  là cách VTOS từng có bốn công thức lãi lỗ chạy song song.
 *
 *  STT lấy từ máy chủ ({r.stt}), không dùng chỉ số vòng lặp: đánh lại số ở màn hình thì đúng ở trang
 *  đầu và sai ở mọi trang sau, mà kiểu sai ấy chỉ lộ ra ở nhà khách hàng.
 */
function BanQuyetToan({ qt, mat, setMat }: { qt: any; mat: string; setMat: (m: string) => void }) {
  if (!qt) return (<>
    <h4>Bản quyết toán của Điều hành</h4>
    <p className="muted" style={{ fontSize: 13 }}>
      Chuyến này <b>chưa nạp tệp quyết toán chi tiết</b>. Rỗng ở đây nghĩa là chưa có tệp — khác hẳn
      với đã nạp mà tệp không có dòng nào.
    </p>
  </>);

  const MAT: [string, string, number][] = [
    ["khach", "Khách", qt.khach.length],
    ["chiet_tinh", "Chiết tính", qt.chiet_tinh.length],
    ["hdv", "Hướng dẫn viên", qt.hdv_chi.length],
    ["booking", "Booking nguồn", qt.booking.length],
  ];

  return (<>
    <h4>Bản quyết toán của Điều hành — {qt.ten_tep}
      <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>
        {" "}· nạp bởi {qt.nap_boi} · {fmtD(qt.nap_luc)}</span></h4>

    {/* Chênh lệch giữa số chuẩn và tổng trong tệp. 0 nghĩa là ĐÃ ĐỐI CHIẾU VÀ KHỚP – khác với chưa
        đối chiếu bao giờ, nên vẫn hiện chứ không ẩn đi. */}
    <p className="muted" style={{ fontSize: 13 }}>
      Tệp ghi <b>{qt.so_khach_tep_ghi ?? "—"}</b> khách trên <b>{qt.so_dong_khach}</b> dòng
      {qt.hdv ? <> · HDV {qt.hdv}</> : null}{qt.bien_so_xe ? <> · xe {qt.bien_so_xe}</> : null}
      {qt.nhieu_muc_gia ? <> · <b>nhiều mức giá</b></> : null}
      {" "}· chênh thu {so(qt.chenh_thu)} · chênh chi {so(qt.chenh_chi)}
    </p>

    {qt.phat_hien?.length ? (
      <div className="gate fail">
        <b>{qt.phat_hien.length} chỗ tệp gốc tự mâu thuẫn</b>
        <ul style={{ margin: "4px 0 0 18px" }}>
          {qt.phat_hien.map((x: string, i: number) => <li key={i}>{x}</li>)}
        </ul>
      </div>) : null}

    <div className="row" style={{ gap: 6, margin: "8px 0" }}>
      {MAT.map(([k, ten, n]) => (
        <button key={k} className={"act sm" + (mat === k ? "" : " ghost")}
                onClick={() => setMat(k)}>{ten} ({n})</button>))}
    </div>

    {mat === "khach" && (qt.khach.length ? <table><thead><tr>
      <th className="num">STT</th><th>Sales</th><th>Tên khách</th>
      <th className="num">Giá bán</th><th className="num">Thu khác</th><th className="num">Tổng thu</th>
      <th className="num">Tổng chi</th><th className="num">Lợi nhuận</th><th>Khoản chi</th>
    </tr></thead><tbody>
      {qt.khach.map((r: any) => (<tr key={r.stt} className={r.co_lech ? "red" : ""}>
        <td className="num">{r.stt}</td><td>{r.sales}</td><td>{r.ten_khach}</td>
        <td className="num">{so(r.gia_ban)}</td><td className="num">{so(r.thu_khac)}</td>
        <td className="num">{so(r.tong_thu)}</td><td className="num">{so(r.tong_chi)}</td>
        <td className="num">{so(r.loi_nhuan)}</td>
        <td className="muted" style={{ fontSize: 12 }}>
          {r.khoan_chi.map((k: any) => `${k.ten_khoan} ${k.so_tien === null ? "—" : vnd(k.so_tien)}`).join(" · ")}
          {r.co_lech ? <div className="so-do">{r.co_lech}</div> : null}</td>
      </tr>))}
    </tbody></table> : <p className="muted">Tệp không có dòng khách nào.</p>)}

    {mat === "chiet_tinh" && (<>
      <p className="muted" style={{ fontSize: 12 }}>
        {qt.so_chung_tu_co_mst}/{qt.chiet_tinh.length} dòng có mã số thuế ·
        {" "}{qt.so_dong_chi_co_chung_tu}/{qt.so_dong_chi} dòng chi có số chứng từ. Thiếu MST thì lúc
        đối chiếu tờ khai thuế phải mở lại tệp Excel gốc từng chuyến một.
      </p>
      {qt.chiet_tinh.length ? <table><thead><tr>
        <th>Vế</th><th>Nhóm</th><th>Nội dung</th><th>Đối tác</th><th>MST</th>
        <th className="num">Đơn giá</th><th className="num">SL</th><th className="num">Hệ số</th>
        <th className="num">Thành tiền</th><th>Chứng từ</th>
      </tr></thead><tbody>
        {qt.chiet_tinh.map((r: any, i: number) => (<tr key={i} className={r.co_lech ? "red" : ""}>
          <td>{r.ve}</td><td>{r.nhom}</td><td title={r.noi_dung}>{r.noi_dung?.slice(0, 34)}</td>
          <td>{r.doi_tac || <span className="muted">—</span>}</td>
          <td>{r.mst_ncc || <span className="muted" title="Chưa có MST – không đối chiếu được tờ khai thuế">—</span>}</td>
          <td className="num">{so(r.don_gia)}</td><td className="num">{r.so_luong ?? "—"}</td>
          <td className="num">{r.he_so ?? "—"}</td><td className="num">{so(r.thanh_tien)}</td>
          <td>{r.so_chung_tu || <span className="muted">—</span>}</td>
        </tr>))}
      </tbody></table> : <p className="muted">Tệp không có dòng chiết tính nào.</p>}
    </>)}

    {mat === "hdv" && (qt.hdv_chi.length ? <table><thead><tr>
      <th>Nội dung</th><th className="num">Đơn giá</th><th className="num">SL</th>
      <th className="num">Tổng chi</th><th className="num">Tiền ứng</th><th className="num">Dư</th>
      <th className="num">CTP</th><th>Ghi chú</th>
    </tr></thead><tbody>
      {qt.hdv_chi.map((r: any, i: number) => (<tr key={i} className={r.la_dong_tong ? "" : "muted"}>
        <td>{r.la_dong_tong ? <b>{r.noi_dung}</b> : r.noi_dung}</td>
        <td className="num">{so(r.don_gia)}</td><td className="num">{r.so_luong ?? "—"}</td>
        <td className="num">{so(r.tong_chi)}</td><td className="num">{so(r.tien_ung)}</td>
        <td className="num">{so(r.du)}</td><td className="num">{so(r.ctp)}</td>
        <td className="muted" style={{ fontSize: 12 }}>{r.ghi_chu || ""}</td>
      </tr>))}
    </tbody></table> : <p className="muted">Tệp không có dòng chi hướng dẫn viên nào.</p>)}

    {mat === "booking" && (qt.booking.length ? <table><thead><tr>
      <th>Mã booking nguồn</th><th>Người book</th><th>Điện thoại</th><th className="num">Khách</th>
      <th className="num">Tổng thu</th><th className="num">Đã đóng</th><th className="num">Còn phải thu</th>
      <th>Người bán</th>
    </tr></thead><tbody>
      {qt.booking.map((r: any, i: number) => (<tr key={i}>
        <td>{r.ma_booking_nguon}{r.booking_id ? null : <div className="muted" style={{ fontSize: 12 }}>chưa ghép vào hệ bán hàng</div>}</td>
        <td>{r.ten_nguoi_book}</td><td>{r.dien_thoai}</td><td className="num">{r.so_khach ?? "—"}</td>
        <td className="num">{so(r.tong_thu)}</td><td className="num">{so(r.da_dong)}</td>
        <td className="num">{so(r.con_phai_thu)}</td><td>{r.nguoi_ban}</td>
      </tr>))}
    </tbody></table> : <p className="muted">Tệp không có dòng booking nguồn nào.</p>)}
  </>);
}

export default function Page() { return <Shell><LaiLoTour /></Shell>; }
