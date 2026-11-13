"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** V6 – Báo giá. MỘT màn hình cho cả lẻ và đoàn, lọc bằng ?mang=.
 *
 *  Cổng biên đứng ở bước GỬI, không ở bước lưu nháp: nháp là chỗ để thử con số, chặn ở nháp thì sale
 *  không ước lượng được gì và cách lách rõ nhất là ghi một giá vốn bịa cho qua cổng. Cam kết với
 *  khách xảy ra lúc gửi, nên cổng đứng ở đó.
 *
 *  Màn hình cố ý hiện thẳng ba con số (bán · vốn · biên) ngay cạnh nút Gửi, kể cả khi chưa đủ cơ sở.
 *  Giấu chúng đi rồi chỉ báo lỗi lúc bấm là bắt người dùng đoán mình sai ở đâu.
 */
type Dong = { hang_khach: string; mo_ta: string; so_luong: number; don_gia: number;
              gia_von_don_vi: number | null; chiet_khau: number };
type BG = { id: number; ma: string; mang: string; khach_ten: string; khach_dien_thoai: string;
            so_khach: number; ngay_khoi_hanh: string | null; trang_thai: string; trang_thai_ten: string;
            khach_email: string; bang_gia_id: number | null;
            duoi_bien: boolean; giai_trinh: string; bien_luc_gui: number | null; phien_ban: number;
            dong: Dong[]; ban_da_gui: any[]; cong_bien: any;
            // KS-19k: báo giá đoàn lập từ thiết kế — chung bảng, chỉ xem ở đây; tiền lấy từ phần riêng (không giá vốn)
            nguon?: string; thiet_ke?: { ma: string; tong_ban: number | null } };

type BangGia = { id: number; ma: string; ten: string; mang: string; hieu_luc_tu: string;
                 hieu_luc_den: string | null; con_hieu_luc: boolean;
                 dong: { hang_khach: string; mo_ta: string; gia_ban: number;
                         gia_von: number | null; chiet_khau_toi_da: number }[] };

const RONG: Dong = { hang_khach: "nguoi_lon", mo_ta: "", so_luong: 1, don_gia: 0,
                     gia_von_don_vi: null, chiet_khau: 0 };

const vnd = (n: number | null | undefined) => (n || 0).toLocaleString("vi-VN") + " đ";
const pct = (n: number | null) => (n === null || n === undefined ? "–" : (n * 100).toFixed(1) + "%");

function BaoGia() {
  const { xacNhan, nhap, hop } = useHoi();
  const { user, toast } = useShell();
  const [mang, setMang] = useState("kd_le");
  const [ds, setDs] = useState<BG[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [dang, setDang] = useState(false);
  const [bgs, setBgs] = useState<BangGia[]>([]);
  const [tours, setTours] = useState<any[]>([]);
  const [gvTour, setGvTour] = useState<any>(null);
  const [soanMo, setSoanMo] = useState(false);
  const [suaId, setSuaId] = useState<number | null>(null);
  const [suaPb, setSuaPb] = useState<number | null>(null);
  // Biểu soạn giữ giá vốn là null khi CHƯA CÓ. Không đổi thành 0 ở giao diện: 0 là một con số có
  // nghĩa (miễn phí), còn null là chưa biết — và cổng biên phân biệt hai cái đó.
  const [f, setF] = useState<any>({ khach_ten: "", khach_dien_thoai: "", khach_email: "",
                                    so_khach: 1, ngay_khoi_hanh: "", han_hieu_luc: "",
                                    bang_gia_id: "", tour_id: "",
                                    dong: [ { ...RONG } ] as Dong[] });
  const soan = ["nv_kd", "tn_kd", "tp_kd", "gd_kd", "ptgd_mkt", "tgd", "chutich", "cntt"]
    .includes(user?.role || "");

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("mang");
    if (q) setMang(q);
    api("/ban-hang/meta").then(setMeta).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    try {
      setDs(await api<BG[]>(`/ban-hang/bao-gia?mang=${mang}`));
      setBgs(await api<BangGia[]>(`/ban-hang/bang-gia?mang=${mang}`));
      setTours(await api<any[]>("/ban-hang/tour-de-chon"));
    } catch (e) { toast(errMsg(e), true); }
  }, [mang, toast]);
  useEffect(() => { load(); }, [load]);

  const dat = (k: string, v: any) => setF((x: any) => ({ ...x, [k]: v }));
  const datDong = (i: number, k: string, v: any) =>
    setF((x: any) => ({ ...x, dong: x.dong.map((d: Dong, j: number) => j === i ? { ...d, [k]: v } : d) }));

  const moSoanMoi = () => {
    setSuaId(null); setSuaPb(null); setSoanMo(true);
    setGvTour(null);
    setF({ khach_ten: "", khach_dien_thoai: "", khach_email: "", so_khach: 1,
           ngay_khoi_hanh: "", han_hieu_luc: "", bang_gia_id: "", tour_id: "",
           dong: [{ ...RONG }] });
  };

  const moSua = (b: BG) => {
    setSuaId(b.id); setSuaPb(b.phien_ban); setSoanMo(true); setGvTour(null);
    setF({ khach_ten: b.khach_ten, khach_dien_thoai: b.khach_dien_thoai || "",
           khach_email: b.khach_email || "", so_khach: b.so_khach,
           ngay_khoi_hanh: b.ngay_khoi_hanh || "", han_hieu_luc: "",
           bang_gia_id: b.bang_gia_id ?? "", tour_id: (b as any).tour_id ?? "",
           dong: b.dong.length ? b.dong.map((d) => ({ ...d })) : [{ ...RONG }] });
  };

  // Lấy dòng từ bảng giá hiệu lực. CHÉP giá vốn sang, kể cả khi bảng giá để trống — chép cái trống
  // đúng như nó là, chứ không lấp bằng 0 để cổng biên đi qua được.
  const layTuBangGia = (id: string) => {
    dat("bang_gia_id", id);
    const bg = bgs.find((x) => String(x.id) === String(id));
    if (!bg || !bg.dong.length) return;
    dat("dong", bg.dong.map((d) => ({ hang_khach: d.hang_khach, mo_ta: d.mo_ta, so_luong: 1,
                                      don_gia: d.gia_ban, gia_von_don_vi: d.gia_von, chiet_khau: 0 })));
    toast(`Đã lấy ${bg.dong.length} dòng từ bảng giá ${bg.ma}`);
  };

  // Hỏi giá vốn một khách từ dự toán tour. CHỈ HIỆN RA, không tự điền vào dòng nào: chia giá vốn cho
  // người lớn / trẻ em / em bé là việc có phán đoán, và một con số máy chia hộ trông rất gọn rồi
  // người ký duyệt tin theo là cách hỏng đắt nhất. Nút "dùng số này" nằm ở từng dòng, người bấm.
  const hoiGiaVon = async (tid: string) => {
    dat("tour_id", tid); setGvTour(null);
    if (!tid) return;
    try {
      setGvTour(await api<any>(`/ban-hang/tour/${tid}/gia-von?so_khach=${Number(f.so_khach) || 1}`));
    } catch (e) { toast(errMsg(e), true); }
  };

  const luuNhap = async () => {
    if (!f.khach_ten.trim()) { toast("Chưa có tên khách", true); return; }
    setDang(true);
    try {
      const than = {
        mang, khach_ten: f.khach_ten.trim(), khach_dien_thoai: f.khach_dien_thoai,
        khach_email: f.khach_email,
        bang_gia_id: f.bang_gia_id ? Number(f.bang_gia_id) : null,
        tour_id: f.tour_id ? Number(f.tour_id) : null,
        so_khach: Number(f.so_khach) || 1,
        ngay_khoi_hanh: f.ngay_khoi_hanh || null,
        han_hieu_luc: f.han_hieu_luc || null,
        phien_ban: suaPb,
        dong: f.dong.filter((d: Dong) => d.mo_ta || d.don_gia).map((d: Dong) => ({
          hang_khach: d.hang_khach, mo_ta: d.mo_ta, so_luong: Number(d.so_luong) || 1,
          don_gia: Number(d.don_gia) || 0,
          gia_von_don_vi: d.gia_von_don_vi === null || (d.gia_von_don_vi as any) === ""
                            ? null : Number(d.gia_von_don_vi),
          chiet_khau: Number(d.chiet_khau) || 0 })),
      };
      const r = suaId
        ? await api<any>(`/ban-hang/bao-gia/${suaId}`, { method: "PUT", json: than })
        : await api<any>("/ban-hang/bao-gia", { method: "POST", json: than });
      toast(r.message || `Đã lưu nháp ${r.ma || ""}`);
      setSoanMo(false); setSuaId(null); setSuaPb(null);
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const gui = async (b: BG) => {
    const c = b.cong_bien;
    let giai_trinh = "";
    if (!c.du_co_so || !c.dat) {
      const nhac = c.du_co_so
        ? `Biên ${pct(c.bien)} dưới ngưỡng ${pct(c.nguong)}.`
        : `Chưa đủ cơ sở tính biên: ${c.dong_thieu_gia_von.length} dòng chưa có giá vốn.`;
      const ly_do = await nhap(`${nhac}\n\nGửi vẫn được, nhưng phải giải trình (ít nhất ` +
                           `${meta?.dai_giai_trinh || 30} ký tự):\nvì sao chấp nhận · khoản nào làm ` +
                           `mỏng biên · bù bằng gì`);
      if (!ly_do || !ly_do.trim()) return;
      giai_trinh = ly_do.trim();
    }
    setDang(true);
    try {
      // Một lần bấm nút = một khóa. Bấm lại vì mạng chập không được thành hai cam kết với khách.
      const khoa = `bg-${b.id}-${b.phien_ban}-${Date.now()}`;
      const r = await api<any>(`/ban-hang/bao-gia/${b.id}/gui`,
                               { method: "POST", json: { giai_trinh }, headers: { "X-Khoa-Ghi": khoa } });
      toast(r.message || "Đã gửi khách");
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  // Lập hợp đồng từ báo giá khách đã chốt. Cửa này đứng ở ĐÂY chứ không ở màn hình Hợp đồng: giá trị
  // hợp đồng lấy từ BẢN BÁO GIÁ ĐÃ GỬI, nên chỗ bấm phải là chỗ nhìn thấy bản đã gửi. Đặt ở màn hình
  // kia thì người lập phải nhớ mã báo giá, và nhớ nhầm thì hợp đồng mang giá trị của một bản khác.
  const lapHopDong = async (b: BG) => {
    const so = await nhap(`Lập hợp đồng cho báo giá ${b.ma} – khách ${b.khach_ten}.\n` +
                             "Số hợp đồng (để trống thì hệ thống tự sinh):") ?? null;
    if (so === null) return;               // bấm Huỷ – khác với để trống rồi bấm Đồng ý
    setDang(true);
    try {
      const r = await api<any>(`/ban-hang/bao-gia/${b.id}/hop-dong`, { method: "POST", json: {
        so_hop_dong: so.trim(), khach_ten: b.khach_ten } });
      toast(r.message || "Đã lập hợp đồng");
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const hanh = async (b: BG, duong: string, xong: string) => {
    setDang(true);
    try { const r = await api<any>(`/ban-hang/bao-gia/${b.id}/${duong}`, { method: "POST", json: {} });
          toast(r.message || xong); await load(); }
    catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  return (
    <div className="wrap">{hop}
      <h1>Báo giá {mang === "kd_doan" ? "đoàn" : "lẻ"}</h1>
      <p className="muted">
        Cổng biên đứng ở bước <b>gửi khách</b>, vì cam kết xảy ra ở đó chứ không phải lúc lập dự toán.
        Thiếu giá vốn <b>không phải</b> giá vốn bằng 0 — không có giá vốn thì cổng không thể ĐẠT.
      </p>

      <div className="row">
        {[["kd_le", "Lẻ"], ["kd_doan", "Đoàn (MICE)"]].map(([k, t]) => (
          <button key={k} className={mang === k ? "" : "ghost"} onClick={() => setMang(k)}>{t}</button>
        ))}
        {meta ? <span className="muted small">Ngưỡng biên hiện hành: <b>{pct(meta.nguong_bien)}</b></span> : null}
      </div>

      {soan ? (
        <div className="row">
          <button onClick={moSoanMoi}>Soạn báo giá mới</button>
          {soanMo ? <button className="ghost" onClick={() => { setSoanMo(false); setSuaId(null); }}>Đóng biểu</button> : null}
        </div>
      ) : null}

      {soanMo ? (
        <div className="card">
          <h3>{suaId ? "Sửa báo giá nháp" : "Soạn báo giá mới"}</h3>
          <p className="muted small">
            Lưu nháp <b>chưa cam kết gì với khách</b> — nháp là chỗ để thử con số. Biên do máy chủ tính
            và hiện ở bảng dưới ngay sau khi lưu; màn hình không tự tính lấy một con số biên thứ hai, vì
            hai chỗ cùng tính một con số thì sớm muộn lệch nhau và người dùng tin chỗ dễ hơn.
          </p>

          <div className="luoi">
            <label>Tên khách <span className="do">*</span>
              <input value={f.khach_ten} onChange={(e) => dat("khach_ten", e.target.value)} /></label>
            <label>Điện thoại
              <input value={f.khach_dien_thoai} onChange={(e) => dat("khach_dien_thoai", e.target.value)} /></label>
            <label>Email
              <input value={f.khach_email} onChange={(e) => dat("khach_email", e.target.value)} /></label>
            <label>Số khách
              <input type="number" min={1} value={f.so_khach}
                     onChange={(e) => dat("so_khach", e.target.value)} /></label>
            <label>Ngày khởi hành
              <input type="date" value={f.ngay_khoi_hanh}
                     onChange={(e) => dat("ngay_khoi_hanh", e.target.value)} /></label>
            <label>Báo giá có hiệu lực đến
              <input type="date" value={f.han_hieu_luc}
                     onChange={(e) => dat("han_hieu_luc", e.target.value)} /></label>
          </div>

          <label className="ca-dong">Gắn với tour (để lấy giá vốn từ dự toán)
            <select value={f.tour_id} onChange={(e) => hoiGiaVon(e.target.value)}>
              <option value="">— không gắn tour —</option>
              {tours.map((t) => (
                <option key={t.id} value={t.id}>{t.code} · {t.name} · {t.start_date}</option>))}
            </select></label>

          {gvTour ? (
            <div className={gvTour.co_du_toan ? "hop" : "hop thieu"}>
              {gvTour.co_du_toan ? <>
                <b>Giá vốn một khách theo dự toán tour {gvTour.tour}: {vnd(gvTour.gia_von_moi_khach)}</b>
                <div className="muted small">{gvTour.message}</div>
                {gvTour.dong_chua_co_so_tien?.length ? (
                  <div className="muted small">Dòng dự toán chưa có số tiền: {gvTour.dong_chua_co_so_tien.join(", ")}</div>
                ) : null}
                <div className="muted small">
                  Con số này <b>chưa vào dòng nào</b>. Chia giá vốn cho người lớn / trẻ em / em bé là
                  việc của người soạn — bấm “dùng số này” ở đúng dòng muốn gán.
                </div>
              </> : <>
                <b>Tour {gvTour.tour} chưa có dự toán.</b>
                <div className="muted small">
                  Chưa có dự toán <b>không phải</b> giá vốn bằng 0. Ô giá vốn ở dưới cứ để trống — cổng
                  biên lúc gửi sẽ báo “chưa đủ cơ sở”, đúng như thực tế.
                </div>
              </>}
            </div>
          ) : null}

          <label className="ca-dong">Lấy dòng từ bảng giá
            <select value={f.bang_gia_id} onChange={(e) => layTuBangGia(e.target.value)}>
              <option value="">— gõ tay, không lấy từ bảng giá —</option>
              {bgs.map((b) => (
                <option key={b.id} value={b.id} disabled={!b.con_hieu_luc}>
                  {b.ma} · {b.ten} · từ {b.hieu_luc_tu}{b.con_hieu_luc ? "" : " (đã hết hiệu lực)"}
                </option>))}
            </select></label>
          {bgs.length === 0 ? <p className="muted small">Mảng này chưa có bảng giá nào — vẫn soạn tay được,
            nhưng bảng giá là chỗ giá vốn có sẵn, không phải gõ lại mỗi lần.</p> : null}

          <b>Dòng báo giá</b>
          <table className="tbl">
            <thead><tr><th>Hạng khách</th><th>Diễn giải</th><th style={{ width: 70 }}>SL</th>
              <th style={{ width: 130 }}>Đơn giá</th><th style={{ width: 130 }}>Giá vốn/đơn vị</th>
              <th style={{ width: 90 }}>Chiết khấu</th><th></th></tr></thead>
            <tbody>{f.dong.map((d: Dong, i: number) => (
              <tr key={i}>
                <td><select value={d.hang_khach} onChange={(e) => datDong(i, "hang_khach", e.target.value)}>
                  {(meta?.hang_khach || ["nguoi_lon"]).map((h: string) =>
                    <option key={h} value={h}>{h}</option>)}
                </select></td>
                <td><input value={d.mo_ta} onChange={(e) => datDong(i, "mo_ta", e.target.value)} /></td>
                <td><input type="number" min={1} value={d.so_luong}
                           onChange={(e) => datDong(i, "so_luong", e.target.value)} /></td>
                <td><input type="number" value={d.don_gia}
                           onChange={(e) => datDong(i, "don_gia", e.target.value)} /></td>
                <td><input type="number" placeholder="chưa có"
                           value={d.gia_von_don_vi === null ? "" : d.gia_von_don_vi}
                           onChange={(e) => datDong(i, "gia_von_don_vi",
                             e.target.value === "" ? null : e.target.value)} /></td>
                <td><input type="number" value={d.chiet_khau}
                           onChange={(e) => datDong(i, "chiet_khau", e.target.value)} /></td>
                <td className="nut">
                  {gvTour?.gia_von_moi_khach ? (
                    <button className="ghost"
                            onClick={() => datDong(i, "gia_von_don_vi", gvTour.gia_von_moi_khach)}>
                      dùng số này</button>) : null}
                  <button className="ghost" onClick={() => dat("dong",
                    f.dong.length > 1 ? f.dong.filter((_: Dong, j: number) => j !== i) : f.dong)}>Xóa</button>
                </td>
              </tr>))}
            </tbody>
          </table>
          <div className="row">
            <button className="ghost" onClick={() => dat("dong", [...f.dong, { ...RONG }])}>Thêm dòng</button>
            <span className="muted small">Ô giá vốn để trống nghĩa là <b>chưa có giá vốn</b> — không phải
              giá vốn bằng 0. Cổng biên lúc gửi sẽ báo “chưa đủ cơ sở”, đúng như thực tế.</span>
          </div>

          <div className="row">
            <button disabled={dang} onClick={luuNhap}>{dang ? "Đang lưu…" : "Lưu nháp"}</button>
            <span className="muted small">Lưu xong, bấm <b>Gửi khách</b> ở bảng dưới — cổng biên đứng ở đó.</span>
          </div>
        </div>
      ) : null}

      <div className="card">
        <h3>{ds.length} báo giá</h3>
        {ds.length === 0 ? <p className="muted">Chưa có báo giá nào ở mảng này.</p> : (
          <table className="tbl">
            <thead><tr><th>Mã</th><th>Khách</th><th>Khách/số</th><th>Khởi hành</th>
              <th style={{ textAlign: "right" }}>Tổng bán</th><th>Biên</th><th>Trạng thái</th><th></th></tr></thead>
            <tbody>
              {ds.map((b) => {
                const c = b.cong_bien;
                const tuTK = b.nguon === "thiet_ke";
                return (
                  <>
                    <tr key={b.id}>
                      <td className="mono"><a onClick={() => setMo(mo === b.id ? null : b.id)}>{b.ma}</a></td>
                      <td><b>{b.khach_ten}</b><div className="muted small">{b.khach_dien_thoai}</div></td>
                      <td>{b.so_khach}</td>
                      <td>{b.ngay_khoi_hanh || "–"}</td>
                      <td style={{ textAlign: "right" }}>{vnd(tuTK ? b.thiet_ke?.tong_ban : c.tong_ban)}</td>
                      <td>
                        {tuTK ? (b.bien_luc_gui != null ? <Tag cls={b.duoi_bien ? "red" : "ok"}>{pct(b.bien_luc_gui)}</Tag> : "–")
                          : !c.du_co_so ? <Tag cls="warn">chưa đủ cơ sở</Tag>
                          : c.dat ? <Tag cls="ok">{pct(c.bien)}</Tag>
                          : <Tag cls="red">{pct(c.bien)}</Tag>}
                        {b.duoi_bien ? <div className="muted small">đã gửi dưới biên</div> : null}
                      </td>
                      <td>{b.trang_thai_ten}</td>
                      <td className="nut">
                        {tuTK && <span className="muted small">Từ thiết kế {b.thiet_ke?.ma} · xử lý ở Tour đoàn</span>}
                        {soan && !tuTK && b.trang_thai === "nhap" &&
                          <button className="ghost" disabled={dang} onClick={() => moSua(b)}>Sửa</button>}
                        {soan && !tuTK && ["nhap", "da_gui"].includes(b.trang_thai) &&
                          <button className="ghost" disabled={dang} onClick={() => gui(b)}>Gửi khách</button>}
                        {soan && !tuTK && b.trang_thai === "da_gui" &&
                          <button className="ghost" disabled={dang}
                                  onClick={() => hanh(b, "khach-chot", "Khách đã chốt")}>Khách chốt</button>}
                        {soan && !tuTK && b.trang_thai === "khach_chot" &&
                          <button className="ghost" disabled={dang}
                                  onClick={() => lapHopDong(b)}>Lập hợp đồng</button>}
                      </td>
                    </tr>
                    {mo === b.id ? (
                      <tr key={`${b.id}-chi-tiet`}><td colSpan={8} className="chitiet">
                        <b>Dòng báo giá</b>
                        <table className="tbl">
                          <thead><tr><th>Hạng khách</th><th>Diễn giải</th><th>SL</th>
                            <th style={{ textAlign: "right" }}>Đơn giá</th>
                            <th style={{ textAlign: "right" }}>Giá vốn</th></tr></thead>
                          <tbody>{b.dong.map((d, i) => (
                            <tr key={i}><td>{d.hang_khach}</td><td>{d.mo_ta}</td><td>{d.so_luong}</td>
                              <td style={{ textAlign: "right" }}>{vnd(d.don_gia)}</td>
                              <td style={{ textAlign: "right" }}>
                                {d.gia_von_don_vi === null
                                  ? <Tag cls="warn">chưa có</Tag> : vnd(d.gia_von_don_vi)}</td></tr>))}
                          </tbody>
                        </table>
                        {b.giai_trinh ? <p className="warn"><b>Giải trình khi gửi dưới biên:</b> {b.giai_trinh}</p> : null}
                        <b>Các bản đã gửi khách</b>
                        {b.ban_da_gui.length === 0 ? <p className="muted">Chưa gửi lần nào.</p> : (
                          <table className="tbl">
                            <thead><tr><th>Lần</th><th>Lúc</th><th>Người gửi</th>
                              <th style={{ textAlign: "right" }}>Tổng bán</th><th>Biên</th></tr></thead>
                            <tbody>{b.ban_da_gui.map((v: any) => (
                              <tr key={v.id}><td>{v.lan}</td><td>{v.gui_luc}</td><td>{v.gui_boi}</td>
                                <td style={{ textAlign: "right" }}>{vnd(v.tong_ban)}</td>
                                <td>{v.du_co_so ? pct(v.bien) : "chưa đủ cơ sở"}</td></tr>))}
                            </tbody>
                          </table>
                        )}
                        <p className="muted small">
                          Bản đã gửi là bản <b>đóng băng</b> — sửa báo giá không làm nó đổi theo, vì câu
                          hỏi lúc tranh chấp là “hôm ấy ta hứa với khách bao nhiêu”.
                        </p>
                      </td></tr>
                    ) : null}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1250px; }
        .card { border: 1px solid var(--vtos-line); border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 12px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid var(--vtos-line); padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .chitiet { background: var(--vtos-info-bg); }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        .mono a { cursor: pointer; text-decoration: underline; }
        .nut { white-space: nowrap; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid var(--vtos-sky);
                 background: var(--vtos-sky); color: var(--vtos-text-on-navy); cursor: pointer; margin-right: 6px; font-size: 13px; }
        button.ghost { background: var(--vtos-card); color: var(--vtos-text); border-color: var(--vtos-line); }
        button:disabled { opacity: .5; cursor: default; }
        .muted { color: var(--vtos-text-mute); }
        .small { font-size: 12px; }
        .luoi { display: grid; gap: 0 14px; grid-template-columns: repeat(auto-fit, minmax(200px,1fr)); }
        label { display: block; font-size: 12px; color: var(--vtos-text-mute); margin-top: 8px; }
        label.ca-dong { grid-column: 1 / -1; }
        input, select { width: 100%; padding: 5px 7px; border: 1px solid var(--vtos-line); border-radius: 6px;
                        font-size: 13px; color: var(--vtos-text); background: var(--vtos-card); }
        .do { color: var(--vtos-danger); }
        .hop { border: 1px solid var(--vtos-success); background: var(--vtos-success-bg); border-radius: 8px;
               padding: 8px 10px; margin: 10px 0; font-size: 13px; }
        .hop.thieu { border-color: var(--vtos-warning); background: var(--vtos-warning-bg); }
        .warn { color: var(--vtos-warning); background: var(--vtos-warning-bg); padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() { return <Shell><BaoGia /></Shell>; }
