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
 *   2. Tổng ở chân bảng chỉ cộng dòng đã có giá vốn, và phải ghi rõ đã bỏ ra bao nhiêu dòng.
 *
 *  ── 29/9/2026 · SỔ QUYẾT TOÁN ĐIỀU HÀNH (lớp 1) GẮN VÀO ĐÂY, KHÔNG THÀNH TRANG RIÊNG ─────────
 *  Đo ngày 29/9: bảng `tour_settlements` và SÁU cửa `/api/v1/quyet-toan-tour/**` có đủ từ 10/9 mà
 *  không màn hình nào gọi tới — sáu cửa sống không có lối vào, tức là việc còn thiếu theo ranh
 *  giới 09/9/2026. Bản nháp đầu dựng một trang `/quyet-toan-tour` riêng; hàng rào
 *  `test_lop1_stt_gia_ban_va_man_hinh_lop2` đỏ ngay, và nó ĐỎ ĐÚNG: kho này từng có bốn công thức
 *  lãi lỗ tour chạy song song, hai trang trông giống nhau thì sinh cái thứ năm. Anh Tuấn chọn
 *  phương án gắn vào đây, KHÔNG nới hàng rào một dòng nào.
 *
 *  Khối thêm vào chỉ mang phần lớp 1 mà màn hình này chưa có: HAI HÀNG ĐỢI còn thiếu số, cửa nhập
 *  giá vốn và cửa phân loại. BỐN MẶT chi tiết KHÔNG nhân bản — chúng vẫn chỉ nằm ở lớp 2 ngay bên
 *  dưới, mở theo từng chuyến. */

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

/** Vai ĐỌC được sổ quyết toán lớp 1 — đúng bằng tuple `READ` của `api/v1/quyet_toan_tour.py`.
 *
 *  Màn hình này mở cho rộng hơn thế (có `sales_admin` và `robot_ks`), nên nếu vẽ khối sổ cho mọi
 *  người thì hai vai ấy thấy một khối luôn báo lỗi 403 — người dùng không phân biệt được "không có
 *  quyền" với "màn hình hỏng". Ẩn ở đây là TIỆN NGHI; hàng rào thật vẫn nằm ở chữ ký của cửa. */
const VAI_DOC_SO = ["chutich", "tgd", "ptgd_doan", "tp_dh", "nv_dh", "ketoan", "bks", "cntt"];
/** Vai GHI — đúng bằng tuple `WRITE` của cùng tệp ấy. */
const VAI_GHI_SO = ["tp_dh", "nv_dh", "ketoan", "cntt"];

/** SỔ QUYẾT TOÁN ĐIỀU HÀNH — lớp 1. Hai hàng đợi và hai cửa ghi, không có mặt chi tiết nào.
 *
 *  Không tự cộng một con số nào: băng tổng hợp lấy nguyên từ `/quyet-toan-tour/tong-hop`, kể cả
 *  dòng lời khai "lợi nhuận chỉ cộng trên đơn đã có giá vốn" (`ghi_chu`) — chép cứng câu ấy vào
 *  đây là dựng bản sao thứ hai của một lời hứa, và bản sao thì sẽ cũ đi.
 */
function SoQuyetToan({ toast, duocGhi }: { toast: (m: string, x?: boolean) => void; duocGhi: boolean }) {
  const [meta, setMeta] = useState<any>(null);
  const [tong, setTong] = useState<any>(null);
  const [rows, setRows] = useState<any[] | null>(null);
  const [ky, setKy] = useState("");
  const [hangDoi, setHangDoi] = useState<"" | "thieu_gia_von" | "cho_phan_loai">("thieu_gia_von");
  const [dang, setDang] = useState(false);
  const [oGiaVon, setOGiaVon] = useState<any>(null);
  const [oPhanLoai, setOPhanLoai] = useState<any>(null);

  const napTong = useCallback(async () => {
    try {
      const [t, m] = await Promise.all([
        api(`/quyet-toan-tour/tong-hop${ky ? `?ky=${ky}` : ""}`),
        api("/quyet-toan-tour/meta"),
      ]);
      setTong(t); setMeta(m);
    } catch (e) { toast(errMsg(e), true); }
  }, [ky, toast]);
  useEffect(() => { void napTong(); }, [napTong]);

  const moSo = useCallback(async () => {
    setDang(true);
    try {
      const q = new URLSearchParams();
      if (ky) q.set("ky", ky);
      if (hangDoi === "thieu_gia_von") q.set("thieu_gia_von", "true");
      if (hangDoi === "cho_phan_loai") q.set("cho_phan_loai", "true");
      setRows(await api(`/quyet-toan-tour${q.toString() ? `?${q}` : ""}`));
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  }, [ky, hangDoi, toast]);

  const luuGiaVon = async () => {
    // `soTien` trả null khi ô rỗng hoặc gõ chữ — và null KHÔNG so sánh được với 0 theo kiểu
    // "lớn hơn", nên phải quy về 0 trước. Đây đúng là chỗ "rỗng khác không" mà cả bảng này sinh ra
    // để canh: rỗng ở đây nghĩa là chưa gõ gì, và nó phải bị chặn y như gõ số 0.
    const v = Number(soTien(oGiaVon.gia_von) ?? 0);
    if (!(v > 0)) {
      // Cùng một câu với máy chủ, cố ý: người đọc không phải đoán hai cách nói là một luật.
      toast("Giá vốn phải lớn hơn 0. Đơn không phát sinh giá vốn thì PHÂN LOẠI, đừng ghi 0 – "
            + "0 và “chưa có số” là hai chuyện khác nhau.", true);
      return;
    }
    try {
      await api(`/quyet-toan-tour/${oGiaVon.id}/gia-von`, { method: "POST",
        json: { gia_von: v, ghi_chu: oGiaVon.ghi_chu || "" } });
      setOGiaVon(null); toast("Đã ghi giá vốn"); await napTong(); await moSo();
    } catch (e) { toast(errMsg(e), true); }
  };

  const luuPhanLoai = async () => {
    if (!oPhanLoai.phan_loai) { toast("Chọn một phân loại", true); return; }
    try {
      await api(`/quyet-toan-tour/${oPhanLoai.id}/phan-loai`, { method: "POST",
        json: { phan_loai: oPhanLoai.phan_loai, ghi_chu: oPhanLoai.ghi_chu || "",
                han_bao_luu: oPhanLoai.han_bao_luu || null } });
      setOPhanLoai(null); toast("Đã phân loại"); await napTong(); await moSo();
    } catch (e) { toast(errMsg(e), true); }
  };

  const hdTour = tong?.hang_doi_thieu_gia_von;
  const hdLe = tong?.khach_le_cho_phan_loai;

  return (<>
    <h3 style={{ marginTop: 18 }}>Sổ quyết toán Điều hành — hàng đợi còn thiếu số</h3>
    <p className="muted" style={{ marginTop: -6 }}>
      Sổ lớp 1 do Điều hành nạp qua màn hình <b>Nạp dữ liệu</b>. Ở đây chỉ có hai hàng đợi và hai
      cửa người làm được: <b>nhập giá vốn</b> và <b>phân loại</b>. Bốn mặt chi tiết của một bản
      quyết toán nằm ở <b>lớp 2 ngay bên dưới</b>, mở theo từng chuyến — không nhân bản lên đây.
    </p>

    <div className="grid" style={{ gridTemplateColumns: "repeat(2, minmax(140px, 1fr))", gap: 8 }}>
      <div><label>Kỳ (tháng tour kết thúc)</label>
        <input type="month" value={ky} onChange={(e) => setKy(e.target.value)} /></div>
      <div><label>Hàng đợi</label>
        <select value={hangDoi} onChange={(e) => setHangDoi(e.target.value as any)}>
          <option value="thieu_gia_von">Tour thiếu giá vốn</option>
          <option value="cho_phan_loai">Khách lẻ chờ phân loại</option>
          <option value="">Tất cả bản quyết toán</option>
        </select></div>
    </div>

    {tong && <div className="kpis" style={{ marginTop: 10 }}>
      <div className="kpi"><b className={Number(hdTour?.so_don || 0) > 0 ? "red" : ""}>{hdTour?.so_don ?? 0}</b>
        <span>tour thiếu giá vốn — {so(hdTour?.doanh_thu)}</span></div>
      <div className="kpi"><b className={Number(hdLe?.so_don || 0) > 0 ? "red" : ""}>{hdLe?.so_don ?? 0}</b>
        <span>khách lẻ chờ phân loại — {so(hdLe?.doanh_thu)}</span></div>
      <div className="kpi"><b>{tong.so_don_du_so ?? 0}</b><span>đơn đã đủ số / {tong.so_don ?? 0}</span></div>
      <div className="kpi"><b className={Number(tong.chua_anh_xa_dieu_hanh || 0) > 0 ? "red" : ""}>
        {tong.chua_anh_xa_dieu_hanh ?? 0}</b><span>dòng chưa tra ra người điều hành</span></div>
    </div>}
    {tong?.ghi_chu && <p className="muted" style={{ fontSize: 12 }}>{tong.ghi_chu}</p>}

    <p><button className="btn" onClick={() => void moSo()} disabled={dang}>
      {dang ? "Đang mở…" : rows ? "Nạp lại sổ" : "Mở sổ"}</button></p>

    {rows && (rows.length ? <table><thead><tr>
      <th>Mã tour</th><th>Kỳ</th><th>Loại</th><th>Điều hành</th><th>Kết thúc</th>
      <th className="num">Doanh thu</th><th className="num">Giá vốn</th><th className="num">Lợi nhuận</th>
      <th>Trạng thái</th><th>Phân loại</th><th></th>
    </tr></thead><tbody>
      {rows.map((r: any) => (<tr key={r.id}>
        <td><b>{r.ma_tour}</b><div className="muted" style={{ fontSize: 12 }}>{r.ten_tour}</div></td>
        <td>{r.ky}</td><td>{r.loai_ten}</td>
        <td>{r.dieu_hanh || "—"}
          {r.dieu_hanh && !r.da_anh_xa && <div className="muted" style={{ fontSize: 12 }}>chưa tra ra người thật</div>}</td>
        <td>{fmtD(r.ngay_kt)}</td>
        <td className="num">{so(r.doanh_thu)}</td><td className="num">{so(r.gia_von)}</td>
        <td className="num">{so(r.loi_nhuan)}</td>
        <td><Tag cls={r.trang_thai_qt === "da_qt" ? "ok" : ""}>{r.trang_thai_ten}</Tag></td>
        <td>{r.phan_loai ? <>{r.phan_loai_ten}
          {r.han_bao_luu && <div className="muted" style={{ fontSize: 12 }}>hạn {fmtD(r.han_bao_luu)}</div>}</>
          : <span className="muted">—</span>}</td>
        <td className="num">{duocGhi && r.gia_von === null && (<>
          <button className="btn" onClick={() => setOGiaVon({ id: r.id, ma: r.ma_tour, gia_von: "", ghi_chu: "" })}>Nhập giá vốn</button>{" "}
          <button className="btn" onClick={() => setOPhanLoai({ id: r.id, ma: r.ma_tour, phan_loai: "", ghi_chu: "", han_bao_luu: "" })}>Phân loại</button>
        </>)}</td>
      </tr>))}
    </tbody></table> : <p className="muted">Hàng đợi này đang rỗng.</p>)}

    {oGiaVon && <div className="note warn" style={{ marginTop: 10 }}>
      <b>Nhập giá vốn — {oGiaVon.ma}</b>
      <div className="muted" style={{ fontSize: 13 }}>
        Đơn <b>không phát sinh</b> giá vốn thì dùng cửa Phân loại, đừng ghi 0: “0 đồng” và “chưa ai
        điền” là hai chuyện khác nhau, và sổ không phân biệt được hai chuyện ấy là sổ báo lãi 100%.
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(2, minmax(140px, 1fr))", gap: 8 }}>
        <div><label>Giá vốn (đ)</label>
          <input value={oGiaVon.gia_von} onChange={(e) => setOGiaVon({ ...oGiaVon, gia_von: e.target.value })} /></div>
        <div><label>Ghi chú</label>
          <input value={oGiaVon.ghi_chu} onChange={(e) => setOGiaVon({ ...oGiaVon, ghi_chu: e.target.value })} /></div>
      </div>
      <p><button className="btn" onClick={() => void luuGiaVon()}>Ghi giá vốn</button>{" "}
        <button className="btn" onClick={() => setOGiaVon(null)}>Thôi</button></p>
    </div>}

    {oPhanLoai && meta && <div className="note warn" style={{ marginTop: 10 }}>
      <b>Phân loại — {oPhanLoai.ma}</b>
      <div className="muted" style={{ fontSize: 13 }}>
        Máy <b>không đoán</b> thay: chỉ người đọc chứng từ mới biết một khoản là doanh thu khách lẻ
        hay chi phí nội bộ ghi nhầm. Hai thứ đó khác nhau hoàn toàn trên báo cáo.
      </div>
      <div className="grid" style={{ gridTemplateColumns: "repeat(3, minmax(140px, 1fr))", gap: 8 }}>
        <div><label>Phân loại</label>
          <select value={oPhanLoai.phan_loai} onChange={(e) => setOPhanLoai({ ...oPhanLoai, phan_loai: e.target.value })}>
            <option value="">— chọn —</option>
            {Object.entries(meta.phan_loai).filter(([k]) => k).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select></div>
        {oPhanLoai.phan_loai === "bao_luu_huy_tour" && <div><label>Hạn bảo lưu</label>
          <input type="date" value={oPhanLoai.han_bao_luu}
                 onChange={(e) => setOPhanLoai({ ...oPhanLoai, han_bao_luu: e.target.value })} /></div>}
        <div><label>Ghi chú</label>
          <input value={oPhanLoai.ghi_chu} onChange={(e) => setOPhanLoai({ ...oPhanLoai, ghi_chu: e.target.value })} /></div>
      </div>
      <p><button className="btn" onClick={() => void luuPhanLoai()}>Ghi phân loại</button>{" "}
        <button className="btn" onClick={() => setOPhanLoai(null)}>Thôi</button></p>
    </div>}
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
  const doc_so = !!user && VAI_DOC_SO.includes(user.role);
  const ghi_so = !!user && VAI_GHI_SO.includes(user.role);
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

    {doc_so && <SoQuyetToan toast={toast} duocGhi={ghi_so} />}

    <h3 style={{ marginTop: 18 }}>Lãi lỗ từng chuyến</h3>
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
          {r.co_lech ? <div className="red">{r.co_lech}</div> : null}</td>
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
