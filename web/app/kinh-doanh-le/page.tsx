"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import NhipPhanDau, { Nhip } from "@/components/NhipPhanDau";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

/** Kinh doanh Lẻ – doanh thu, chỉ tiêu, và xem xuống từng cấp.
 *
 *  MỘT MÀN HÌNH CHO BỐN VAI. Giám đốc, Trưởng phòng, Team Leader, Nhân viên mở cùng đường dẫn này;
 *  độ sâu do MÁY CHỦ quyết theo phân công, không do màn hình tự chọn. Dựng bốn màn hình riêng thì
 *  bốn nơi cùng quyết một hàng rào, và ngày một nơi quên thì không ai biết nơi nào.
 *
 *  `/toi-la-ai` chỉ dùng để VẼ – ẩn nút, đổi lời dẫn. Nó KHÔNG cắt dòng: dòng đã được máy chủ cắt
 *  theo `to_chuc_kd.pham_vi_xem` trước khi gửi xuống. Sửa biến trong trình duyệt không mở thêm được
 *  dòng nào.
 *
 *  HAI CON SỐ ĐẶT CẠNH NHAU, CỐ Ý. Bảng này đọc GIÁ TRỊ BOOKING theo tháng TOUR KẾT THÚC; màn hình
 *  Chủ tịch đọc QUYẾT TOÁN CHUYẾN theo ngày đóng sổ. Hai cơ sở khác nhau nên hai số không khớp, và
 *  chúng được in cạnh nhau kèm lời giải thích – giấu một trong hai đi thì ba tháng nữa sẽ có người
 *  mang cả hai ra hỏi bên nào sai.
 */

const LUONG: [string, string][] = [["", "Cả ba luồng"], ["le", "Tour lẻ"], ["doan", "Tour đoàn"],
                                   ["dich_vu_le", "Dịch vụ lẻ (visa, lẻ rời)"]];
const TEN_LUONG: Record<string, string> = { le: "Tour lẻ", doan: "Tour đoàn", dich_vu_le: "Dịch vụ lẻ" };
const TEN_NGAN: Record<string, string> = {
  khoi_kd: "Khối Kinh doanh (vào chỉ tiêu)", ngoai_khoi: "Ngoài khối đã mở quyền bán",
  doi_tac: "Đối tác ngoài công ty", chua_ro: "Chưa biết ai bán",
};
const TEN_CAP: Record<string, string> = { chi_nhanh: "Chi nhánh", phong: "Phòng", team: "Team" };

function kyMacDinh() {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}`;
}

/** Ô so chỉ tiêu với thực hiện. Chưa giao chỉ tiêu thì hiện dấu gạch, KHÔNG hiện 0% –
 *  "chưa giao" khác hẳn "giao rồi mà không đạt đồng nào". */
function DatBaoNhieu({ lam, dich }: { lam: number; dich: number | undefined }) {
  if (!dich) return <span className="muted">–</span>;
  const p = Math.round((lam / dich) * 100);
  return <span><b>{p}%</b> <small className="muted">/ {vnd(dich)}</small></span>;
}

function KinhDoanhLe() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(kyMacDinh());
  const [luong, setLuong] = useState("");
  const [toi, setToi] = useState<any>(null);
  const [d, setD] = useState<any>(null);
  const [duong, setDuong] = useState<any[]>([]);      // đường đã bấm xuống: [{id, ten, cap}]
  const [nguoi, setNguoi] = useState<any>(null);      // booking của một người đang mở
  const [giao, setGiao] = useState<any>(null);        // ô đang giao chỉ tiêu
  const [nhip, setNhip] = useState<Nhip | null>(null);  // biểu đồ phấn đấu của CHÍNH tôi

  // Mảng lấy từ đường dẫn: mục 3.8 (Lẻ) và 3.9 (Đoàn) trỏ vào cùng màn hình này. Trước 28/9 ô
  // này viết cứng "le", nên phòng Đoàn không có màn hình chỉ tiêu nào — xem TC-92.
  const mangTuUrl = useSearchParams().get("mang") || "";
  const mang = mangTuUrl === "doan" ? "doan" : "le";
  const q = `ky=${ky}&mang=${mang}${luong ? `&luong=${luong}` : ""}`;
  const dangO = duong.length ? duong[duong.length - 1] : null;

  const load = useCallback(() => {
    api(`/kinh-doanh/toi-la-ai?ky=${ky}&mang=${mang}`).then(setToi).catch(() => {});
    // Cửa này KHÔNG nhận user_id — máy chủ luôn trả nhịp của chính người đăng nhập.
    api(`/kinh-doanh/nhip-cua-toi?ky=${ky}&mang=${mang}`).then(setNhip).catch(() => setNhip(null));
    const url = dangO ? `/kinh-doanh/don-vi/${dangO.id}?${q}` : `/kinh-doanh/thang?${q}`;
    api(url).then(setD).catch((x) => { toast(errMsg(x), true); setD(null); });
  }, [ky, luong, mang, dangO?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);

  const xuong = (dv: any) => { setNguoi(null); setDuong([...duong, { id: dv.don_vi_id ?? dv.id, ten: dv.ten, cap: dv.cap }]); };
  const ve = (i: number) => { setNguoi(null); setDuong(duong.slice(0, i)); };

  const moNguoi = async (r: any) => {
    try { setNguoi(await api(`/kinh-doanh/nguoi/${r.user_id}?${q}`)); }
    catch (x) { toast(errMsg(x), true); }
  };

  const luuChiTieu = async () => {
    if (!giao) return;
    try {
      const r = await api("/kinh-doanh/chi-tieu", { method: "POST", json: {
        ky, muc_tieu: Number(giao.muc_tieu), luong: giao.luong || "tat_ca",
        don_vi_id: giao.don_vi_id ?? null, user_id: giao.user_id ?? null,
        ghi_chu: giao.ghi_chu || "", ly_do: giao.ly_do || "" } });
      toast(r.message || "Đã giao chỉ tiêu"); setGiao(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const ct = d?.chi_tieu || { don_vi: {}, nguoi: {} };
  const khoaLuong = luong || "tat_ca";
  const dichDonVi = (id: number) => ct.don_vi?.[`${id}|${khoaLuong}`];
  const dichNguoi = (id: number) => ct.nguoi?.[`${id}|${khoaLuong}`];
  const coTheGiao = !!toi?.duoc_giao_chi_tieu;

  return (<>
    <h1>Kinh doanh {mang === "doan" ? "Đoàn" : "Lẻ"}</h1>

    <NhipPhanDau d={nhip} />

    <div className="panel">
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Kỳ<br /><input type="month" value={ky} onChange={(e) => { setDuong([]); setNguoi(null); setKy(e.target.value); }} /></label>
        <label>Luồng<br /><select value={luong} onChange={(e) => setLuong(e.target.value)}>
          {LUONG.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></label>
        {toi && <span>{toi.xem_toan_cay
          ? <Tag cls="navy">Xem toàn cây</Tag>
          : <Tag cls="navy">Xem {toi.so_don_vi_xem_duoc} đơn vị</Tag>}
          {toi.don_vi_cua_toi && <> <Tag>{TEN_CAP[toi.don_vi_cua_toi.cap] || toi.don_vi_cua_toi.cap}: {toi.don_vi_cua_toi.ten}</Tag></>}
        </span>}
      </div>
      {toi?.canh_bao && <p><Tag cls="warn">{toi.canh_bao}</Tag></p>}
    </div>

    {/* Đường đã bấm xuống. Luôn hiện, kể cả khi đang ở gốc – người dùng phải biết mình đang đứng đâu. */}
    <p className="muted">
      <a href="#" onClick={(e) => { e.preventDefault(); ve(0); }}>Toàn phạm vi của tôi</a>
      {duong.map((b, i) => <span key={b.id}> › {i === duong.length - 1
        ? <b>{b.ten}</b>
        : <a href="#" onClick={(e) => { e.preventDefault(); ve(i + 1); }}>{b.ten}</a>}</span>)}
    </p>

    {!d ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>

      <div className="panel">
        <h2>{dangO ? dangO.ten : "Tổng trong phạm vi của tôi"} – kỳ {d.ky}</h2>
        <p style={{ fontSize: 24, margin: "4px 0" }}><b>{vnd(d.tong_tinh_chi_tieu)}</b> đ
          {dangO && dichDonVi(dangO.id) ? <small style={{ marginLeft: 12 }}>
            <DatBaoNhieu lam={d.tong_tinh_chi_tieu} dich={dichDonVi(dangO.id)} /></small> : null}</p>

        {/* NHÃN CƠ SỞ – bắt buộc hiện, xem chú thích đầu tệp và đầu services/doanh_thu_kd.py */}
        <p className="muted">{d.co_so}</p>
        <p className="muted">Cùng kỳ, theo cách <b>màn hình Chủ tịch</b> đọc
          ({d.doi_chieu_quyet_toan?.co_so}): <b>{vnd(d.doi_chieu_quyet_toan?.tien)}</b> đ
          trên {d.doi_chieu_quyet_toan?.so_chuyen} chuyến. Hai số này <b>không khớp nhau và không bao
          giờ khớp</b> – khác cơ sở tính, không phải bên nào sai.</p>

        <div className="wrap"><table>
          <thead><tr><th>Luồng</th><th className="num">Doanh thu</th><th className="num">Số booking</th></tr></thead>
          <tbody>{Object.entries(d.theo_luong || {}).map(([k, v]: any) => <tr key={k}>
            <td>{TEN_LUONG[k] || k}</td><td className="num">{vnd(v.tien)}</td><td className="num">{v.so_booking}</td></tr>)}
          </tbody></table></div>
      </div>

      {/* BỐN NGĂN – chỉ ngăn đầu vào chỉ tiêu, ba ngăn sau hiện ra chứ không giấu. */}
      <div className="panel wrap"><h2>Ai bán – bốn ngăn, cộng lại bằng toàn bộ doanh thu kỳ</h2>
        <table><thead><tr><th>Ngăn</th><th className="num">Số booking</th><th className="num">Doanh thu</th></tr></thead>
          <tbody>{Object.entries(d.theo_ngan || {}).map(([k, v]: any) => <tr key={k}>
            <td>{TEN_NGAN[k] || k}{k === "khoi_kd" && <> <Tag cls="ok">vào chỉ tiêu</Tag></>}</td>
            <td className="num">{v.so_booking}</td><td className="num">{vnd(v.tien)}</td></tr>)}
            <tr><td><b>Tổng cả bốn ngăn</b></td><td className="num"></td><td className="num"><b>{vnd(d.tong_moi_ngan)}</b></td></tr>
          </tbody></table>
        <p className="muted">Bốn ngăn <b>rời nhau</b>: không booking nào nằm ở hai ngăn, không booking
          nào rơi ra ngoài. Chỉ ngăn đầu cộng vào chỉ tiêu – ba ngăn sau là doanh thu thật nhưng
          không phải chỉ tiêu của ai trong khối.</p>
        {!!(d.theo_doi_tac || []).length && <>
          <h3>Bán qua đối tác</h3>
          <table><thead><tr><th>Đối tác</th><th className="num">Số booking</th><th className="num">Doanh thu</th></tr></thead>
            <tbody>{d.theo_doi_tac.map((r: any) => <tr key={r.doi_tac_id}>
              <td>{r.ten}</td><td className="num">{r.so_booking}</td><td className="num">{vnd(r.tien)}</td></tr>)}
            </tbody></table></>}
      </div>

      {/* XEM XUỐNG: đơn vị con của chỗ đang đứng, hoặc cả cây khi đang ở gốc. */}
      {!!((dangO ? d.don_vi_con : d.theo_don_vi) || []).length &&
        <div className="panel wrap"><h2>{dangO ? "Đơn vị bên trong" : "Theo đơn vị"}</h2>
          <table><thead><tr><th>Cấp</th><th>Đơn vị</th><th className="num">Doanh thu</th>
            <th className="num">Đạt chỉ tiêu</th>{coTheGiao && <th></th>}</tr></thead>
            <tbody>{(dangO ? d.don_vi_con : d.theo_don_vi).map((r: any) => {
              const id = r.don_vi_id ?? r.id;
              return <tr key={id}>
                <td>{TEN_CAP[r.cap] || r.cap}</td>
                <td><a href="#" onClick={(e) => { e.preventDefault(); xuong(r); }}>{r.ten}</a></td>
                <td className="num">{r.tien === undefined ? <span className="muted">bấm để xem</span> : vnd(r.tien)}</td>
                <td className="num">{r.tien === undefined ? "" : <DatBaoNhieu lam={r.tien} dich={dichDonVi(id)} />}</td>
                {coTheGiao && <td><button className="act" onClick={() => setGiao({ don_vi_id: id, ten: r.ten, luong: khoaLuong, muc_tieu: dichDonVi(id) || "" })}>Giao chỉ tiêu</button></td>}
              </tr>; })}
            </tbody></table>
          {!dangO && <p className="muted">Số của một phòng <b>đã gồm</b> các team bên trong nó, nên
            đừng cộng các dòng trong bảng này lại với nhau – sẽ đếm hai lần. Tổng đúng là con số lớn ở trên.</p>}
        </div>}

      {/* NGƯỜI BÁN */}
      <div className="panel wrap"><h2>Theo người bán</h2>
        <table><thead><tr><th>Người</th><th>Đơn vị</th><th className="num">Doanh thu</th>
          <th className="num">Booking</th><th className="num">Khách</th><th className="num">Đạt chỉ tiêu</th>{coTheGiao && <th></th>}</tr></thead>
          <tbody>{(d.theo_nguoi || []).map((r: any) => <tr key={r.user_id}>
            <td><a href="#" onClick={(e) => { e.preventDefault(); moNguoi(r); }}>{r.nguoi_ban}</a>
              {r.user_id === user?.id && <> <Tag cls="navy">bạn</Tag></>}</td>
            <td>{r.don_vi || <span className="muted">chưa phân công</span>}</td>
            <td className="num">{vnd(r.tien)}</td><td className="num">{r.so_booking}</td><td className="num">{r.so_khach}</td>
            <td className="num"><DatBaoNhieu lam={r.tien} dich={dichNguoi(r.user_id)} /></td>
            {coTheGiao && <td><button className="act" onClick={() => setGiao({ user_id: r.user_id, ten: r.nguoi_ban, luong: khoaLuong, muc_tieu: dichNguoi(r.user_id) || "" })}>Giao chỉ tiêu</button></td>}
          </tr>)}
          {!(d.theo_nguoi || []).length && <tr><td colSpan={coTheGiao ? 7 : 6} className="muted">Kỳ này chưa có dòng nào trong phạm vi của bạn.</td></tr>}
          </tbody></table>
      </div>

      {/* NGƯỜI BÁN CHƯA CÓ ĐƠN VỊ – hiện ra chứ không nhét tạm vào một đơn vị nào cho đủ tổng. */}
      {!!d.chua_co_don_vi?.so_nguoi && <div className="panel wrap">
        <h2>Người bán chưa được phân công đơn vị</h2>
        <p><Tag cls="warn">{d.chua_co_don_vi.so_nguoi} người – {vnd(d.chua_co_don_vi.tien)} đ</Tag></p>
        <p className="muted">Số của họ <b>không</b> cộng lên team hay phòng nào, vì chưa biết cộng vào
          đâu. Nhét tạm vào một đơn vị cho đủ tổng là làm sai số của đơn vị ấy. Hành chính – Nhân sự
          phân công ở màn hình <b>Cơ cấu tổ chức Kinh doanh</b> thì họ tự vào bảng trên.</p>
        <table><thead><tr><th>Người</th><th className="num">Doanh thu</th><th className="num">Booking</th></tr></thead>
          <tbody>{d.chua_co_don_vi.rows.map((r: any) => <tr key={r.user_id}>
            <td>{r.nguoi_ban}</td><td className="num">{vnd(r.tien)}</td><td className="num">{r.so_booking}</td></tr>)}
          </tbody></table></div>}

      {/* MỘT NGƯỜI – từng booking. Nhân viên mở màn hình sẽ thấy đúng khung này cho chính mình. */}
      {nguoi && <div className="panel wrap">
        <h2>Từng booking – {(d.theo_nguoi || []).find((x: any) => x.user_id === nguoi.user_id)?.nguoi_ban || "người đang xem"}</h2>
        <p><b>{vnd(nguoi.tien)}</b> đ · {nguoi.so_booking} booking · {nguoi.so_khach} khách</p>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Chuyến</th><th>Kết thúc</th><th>Luồng</th><th className="num">Tiền</th></tr></thead>
          <tbody>{nguoi.rows.map((r: any) => <tr key={r.booking_id}>
            <td className="mono">{r.ma}</td><td>{r.khach}</td>
            <td className="mono">{r.tour_ma}</td><td>{r.ket_thuc}</td>
            <td>{TEN_LUONG[r.luong] || r.luong}</td><td className="num">{vnd(r.tien)}</td></tr>)}
          </tbody></table>
        <button className="act" onClick={() => setNguoi(null)}>Đóng</button></div>}
    </>}

    {/* GIAO CHỈ TIÊU */}
    {giao && <div className="panel"><h2>Giao chỉ tiêu – {giao.ten}</h2>
      <p className="muted">Kỳ <b>{ky}</b>, luồng <b>{giao.luong === "tat_ca" ? "cả ba luồng" : (TEN_LUONG[giao.luong] || giao.luong)}</b>.
        Một ô = một kỳ × một nơi nhận × một luồng; giao lại thì đè lên số cũ chứ không thêm dòng.</p>
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Mức chỉ tiêu (đồng)<br /><input type="number" min={0} value={giao.muc_tieu}
          onChange={(e) => setGiao({ ...giao, muc_tieu: e.target.value })} /></label>
        <label>Ghi chú<br /><input value={giao.ghi_chu || ""} onChange={(e) => setGiao({ ...giao, ghi_chu: e.target.value })} /></label>
        <label>Lý do (bắt buộc khi đè lên số đã giao)<br /><input value={giao.ly_do || ""}
          onChange={(e) => setGiao({ ...giao, ly_do: e.target.value })} /></label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="act orange" onClick={luuChiTieu}>Lưu chỉ tiêu</button>{" "}
        <button className="act" onClick={() => setGiao(null)}>Thôi</button></div>
      <p className="muted">Chỉ tiêu là điều <b>người ta quyết định</b>, không phải điều hệ thống đo
        được – nên không có nút "lấy theo kỳ trước". Suy chỉ tiêu từ thực hiện kỳ trước là biến
        thước đo thành cái bóng của chính số bị đo.</p>
    </div>}
  </>);
}

export default function Page() { return <Shell><Suspense><KinhDoanhLe /></Suspense></Shell>; }
