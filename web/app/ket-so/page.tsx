"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DinhKem from "@/components/DinhKem";

/** Kết sổ một kỳ – đường vào cho phần đã có ở app/services/ket_so.py.
 *
 *  Màn hình này CỐ Ý không thêm chức năng nào mới. Nó mở đúng bốn việc dịch vụ đã làm được: xem một
 *  kỳ còn thiếu chặng nào, đưa sao kê vào sổ hàng loạt, kết chuyển bốn bước, và khóa kỳ.
 *
 *  Hai chỗ trên giao diện là quy tắc chứ không phải trang trí:
 *
 *    - MỌI nút ghi đều đứng sau một bảng XEM TRƯỚC, và bảng đó phải bấm mở. Ghi sổ hàng loạt mà không
 *      nhìn trước cả lô là cách tạo vài trăm bút toán sai trong một giây rồi mất vài ngày đảo lại.
 *    - Dòng "chưa nhận diện" KHÔNG có nút ghi. Muốn ghi thì phải chọn phân loại trước – máy không đoán
 *      hộ một dòng tiền ra là trả nhà cung cấp hay tạm ứng hay trả gốc vay.
 */
type Buoc = { buoc: number; ten: string; dong: any[]; tong: number; da_ghi: boolean; chung_tu: string; lai?: number };

const KY_MAC_DINH = () => {
  const d = new Date(); d.setMonth(d.getMonth() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

function KetSo() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(KY_MAC_DINH());
  const [tt, setTt] = useState<any>(null);
  const [sk, setSk] = useState<any>(null);
  const [kc, setKc] = useState<any>(null);
  const [pl, setPl] = useState<Record<number, any>>({});
  const [dang, setDang] = useState(false);
  const ghiDuoc = user?.role === "ketoan";

  const load = useCallback(async () => {
    try { setTt(await api<any>(`/ket-so/tinh-trang?ky=${ky}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [ky, toast]);
  useEffect(() => { load(); setSk(null); setKc(null); setPl({}); }, [load]);

  const xem = async (loai: "sao-ke" | "ket-chuyen") => {
    setDang(true);
    try {
      const d = await api<any>(`/ket-so/${loai}/xem-truoc?ky=${ky}`);
      loai === "sao-ke" ? setSk(d) : setKc(d);
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const ghiSaoKe = async (ids?: number[]) => {
    setDang(true);
    try {
      const d = await api<any>("/ket-so/sao-ke/ghi-so", { method: "POST", json: { ky, ids, phan_loai: pl } });
      toast(d.message);
      await load(); await xem("sao-ke");
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  // Tách chênh lệch tỷ giá ra 635/515 (KY-4). Đứng RIÊNG khỏi bốn bước kết chuyển vì nó lấy số từ
  // các dòng quyết toán chứ không từ số dư tài khoản – gộp chung một khung thì người đọc tưởng nó
  // cũng đọc sổ như bốn bước kia.
  const [tg, setTg] = useState<any>(null);
  const taiTg = useCallback(() => {
    api<any>(`/ket-so/tach-ty-gia/xem-truoc?ky=${ky}`).then(setTg).catch(() => setTg(null));
  }, [ky]);
  useEffect(taiTg, [taiTg]);
  const tachTg = async () => {
    setDang(true);
    try {
      const d = await api<any>("/ket-so/tach-ty-gia", { method: "POST", json: { ky } });
      setTg(d); toast(d.message); load();
    } catch (x) { toast(errMsg(x), true); } finally { setDang(false); }
  };

  // ĐỢT GTGT-2 07/11/2026 — BÙ TRỪ THUẾ GTGT CUỐI KỲ. Đứng RIÊNG khỏi bốn bước kết chuyển, y
  // như tách tỷ giá ngay trên, và vì một lý do mạnh hơn: bốn bước kia đóng tài khoản KẾT QUẢ
  // KINH DOANH về 911 hoặc 154, còn 133 và 3331 là tài khoản BẢNG CÂN ĐỐI — chúng bù trừ vào
  // nhau, không đóng về đâu. Gộp chung một khung thì người đọc tưởng nó cũng là một bước kết
  // chuyển, và sẽ đi tìm nó trong danh sách bước.
  const [gt, setGt] = useState<any>(null);
  const taiGt = useCallback(() => {
    api<any>(`/ket-so/bu-tru-gtgt/xem-truoc?ky=${ky}`).then(setGt).catch(() => setGt(null));
  }, [ky]);
  useEffect(taiGt, [taiGt]);
  const buTruGt = async () => {
    setDang(true);
    try {
      const d = await api<any>("/ket-so/bu-tru-gtgt", { method: "POST", json: { ky } });
      setGt(d); toast(d.message); load();
    } catch (x) { toast(errMsg(x), true); } finally { setDang(false); }
  };

  const ketChuyen = async (buoc?: number[]) => {
    setDang(true);
    try {
      const d = await api<any>("/ket-so/ket-chuyen", { method: "POST", json: { ky, buoc } });
      toast(d.message);
      await load(); await xem("ket-chuyen");
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const khoaKy = async () => {
    const note = prompt(`Khóa sổ kỳ ${ky}. Sau khi khóa, không ghi thêm bút toán nào vào kỳ này được nữa.\nGhi chú:`);
    if (note === null) return;
    setDang(true);
    try {
      const d = await api<any>(`/periods/${ky}/lock`, { method: "POST", json: { note } });
      toast(d.message); await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const datPl = (id: number, k: string, v: string) =>
    setPl({ ...pl, [id]: { ...(pl[id] || {}), [k]: v } });

  return (
    <div className="wrap">
      <h1>Kết sổ kỳ</h1>
      <div className="row">
        <label>Kỳ</label>
        <input value={ky} onChange={(e) => setKy(e.target.value)} placeholder="2026-08" style={{ width: 120 }} />
        <button className="ghost" onClick={load} disabled={dang}>Xem lại</button>
        {tt?.da_khoa ? <Tag cls="warn">kỳ đã khóa sổ</Tag> : null}
      </div>

      {tt ? (
        <div className="card">
          <h3>Kỳ này đi tới đâu rồi</h3>
          {tt.san_sang_len_bao_cao
            ? <p className="ok">Mọi chứng từ của kỳ đã vào sổ.</p>
            : <ul>{tt.chua_xong.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>}
          <p className="muted small">{tt.ghi_chu}</p>
          {tt.canh_bao?.length ? (
            <div className="warn">{tt.canh_bao.map((c: string, i: number) => <p key={i}>{c}</p>)}</div>
          ) : null}
          <table className="tbl">
            <tbody>
              <tr><td className="lbl">Sao kê</td><td>
                {tt.sao_ke.tong_dong} dòng · đã ghi {tt.sao_ke.da_ghi} · chờ ghi {tt.sao_ke.cho_ghi} ·
                chưa định khoản {tt.sao_ke.chua_nhan_dien}</td></tr>
              <tr><td className="lbl">Bảng lương</td><td>
                {tt.bang_luong.co ? `${tt.bang_luong.trang_thai} · ${tt.bang_luong.so_chung_tu} chứng từ`
                                  : "chưa có bảng lương kỳ này"}</td></tr>
              <tr><td className="lbl">Kết chuyển</td><td>
                {tt.ket_chuyen.map((b: any) => (
                  <span key={b.buoc} className="chip">
                    {b.buoc}. {b.da_ghi ? "✓" : "○"} {vnd(b.tong)}
                  </span>
                ))}</td></tr>
            </tbody>
          </table>
        </div>
      ) : null}

      {/* Hồ sơ của kỳ: biên bản đối chiếu, xác nhận số dư ngân hàng, bảng kê đính kèm. Đặt NGAY DƯỚI
          bảng tình trạng kỳ, trước các bước ghi sổ – người khóa kỳ nhìn thấy bộ hồ sơ trước khi bấm
          khóa, chứ không phải đi tìm nó sau khi kỳ đã đóng. Gắn theo MÃ KỲ, không theo bút toán. */}
      <div className="card">
        <DinhKem doiTuong="ket_so" doiTuongId={ky} loai="chung_tu"
                 tieuDe={`Hồ sơ kết sổ kỳ ${ky}`}
                 chiXem={!!tt?.da_khoa} />
      </div>

      <div className="card">
        <h3>1. Sao kê ngân hàng vào sổ</h3>
        <button className="ghost" onClick={() => xem("sao-ke")} disabled={dang}>Xem trước cả lô</button>
        {sk ? (
          <>
            <p className="muted small">{sk.ghi_chu}</p>
            <h4>Nhận diện được – chờ ghi ({sk.khop.length} dòng · {vnd(sk.tong_khop)} đ)</h4>
            {sk.khop.length === 0 ? <p className="muted">Không có dòng nào.</p> : (
              <table className="tbl">
                <thead><tr><th>Ngày</th><th>Nội dung</th><th>Số tiền</th><th>Quy ước</th></tr></thead>
                <tbody>{sk.khop.map((x: any) => (
                  <tr key={x.id}><td>{x.ngay}</td><td>{x.noi_dung}</td>
                    <td className="num">{vnd(x.so_tien)}</td><td>{x.ten_quy_tac}</td></tr>
                ))}</tbody>
              </table>
            )}
            {ghiDuoc && sk.khop.length > 0 ? (
              <button onClick={() => ghiSaoKe()} disabled={dang}>Ghi sổ {sk.khop.length} dòng này</button>
            ) : null}

            <h4>Chưa định khoản ({sk.chua_nhan_dien.length} dòng · {vnd(sk.tong_chua_nhan_dien)} đ)</h4>
            <p className="muted small">
              Máy không đoán hộ: một dòng tiền ra 50 triệu là trả nhà cung cấp, tạm ứng hay trả gốc vay
              thì sao kê không nói. Chọn phân loại rồi xem lại – dòng nào khớp sẽ chuyển lên bảng trên.
            </p>
            {sk.chua_nhan_dien.length === 0 ? <p className="muted">Không có dòng nào.</p> : (
              <table className="tbl">
                <thead><tr><th>Ngày</th><th>Nội dung</th><th>Số tiền</th><th>Vì sao chưa ghi được</th>
                  <th>Phân loại</th><th>Hình thức</th><th>Mã đối tượng</th></tr></thead>
                <tbody>{sk.chua_nhan_dien.map((x: any) => (
                  <tr key={x.id}>
                    <td>{x.ngay}</td><td>{x.noi_dung}</td><td className="num">{vnd(x.so_tien)}</td>
                    <td className="muted small">{x.ly_do}</td>
                    <td>
                      <select value={pl[x.id]?.muc_chi || pl[x.id]?.muc_thu || ""}
                              onChange={(e) => {
                                const g = (x.phan_loai_giup_khop || []).find((y: any) => y.gia_tri === e.target.value);
                                setPl({ ...pl, [x.id]: { ...(pl[x.id] || {}), muc_chi: undefined, muc_thu: undefined,
                                                         ...(g ? { [g.khoa]: g.gia_tri } : {}) } });
                              }}>
                        <option value="">— chọn —</option>
                        {(x.phan_loai_giup_khop || []).map((g: any) => (
                          <option key={g.quy_tac + g.gia_tri} value={g.gia_tri}>{g.ten}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select value={pl[x.id]?.hinh_thuc_tt || "chuyen_khoan"}
                              onChange={(e) => datPl(x.id, "hinh_thuc_tt", e.target.value)}>
                        {Object.entries(sk?.hinh_thuc_tt || {})
                          .filter(([k]: any) => k)
                          .map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}
                      </select>
                    </td>
                    <td><input value={pl[x.id]?.ma_doi_tuong || ""} placeholder="mã NCC / khách"
                               onChange={(e) => datPl(x.id, "ma_doi_tuong", e.target.value)} /></td>
                  </tr>
                ))}</tbody>
              </table>
            )}
            {sk.da_ghi_so.length ? (
              <p className="muted small">Đã ghi sổ trước đó: {sk.da_ghi_so.length} dòng.</p>
            ) : null}
          </>
        ) : null}
      </div>

      <div className="card">
        <h3>2. Kết chuyển cuối kỳ</h3>
        <button className="ghost" onClick={() => xem("ket-chuyen")} disabled={dang}>Xem trước bốn bước</button>
        {kc ? (
          <>
            <p className="muted small">{kc.ghi_chu}</p>
            {kc.canh_bao?.map((c: string, i: number) => <p key={i} className="warn">{c}</p>)}
            {tg && (
              <div className="buoc">
                <b>Tách chênh lệch tỷ giá ra 635 / 515</b>{" "}
                {tg.da_ghi ? <>✓ {tg.chung_tu}</> : "○"}{" "}
                <span className="muted">
                  lỗ {vnd(tg.lo)} · lãi {vnd(tg.lai)} · {(tg.tach_duoc || []).length} dòng
                  {tg.tu_ngay ? <> · từ ngày {tg.tu_ngay} về sau</> : <> · <b>chưa đặt mốc ngày</b></>}
                </span>
                {tg.canh_bao?.map((c: string, i: number) => <p key={i} className="warn">{c}</p>)}
                <p className="muted">{tg.ghi_chu}</p>
                {!tg.da_ghi && tg.da_bat && (tg.but_toan || []).length > 0 && (
                  <button onClick={tachTg} disabled={dang}>Ghi bút toán tách</button>)}
              </div>)}
            {/* ĐỢT GTGT-2 — thẻ CHỈ HIỆN câu máy chủ đã nói: không tự cộng lại một con số nào,
                không tự diễn giải cảnh báo. Máy chủ trả gì thì in nấy, y như thẻ tách tỷ giá. */}
            {gt && (
              <div className="buoc">
                <b>Bù trừ thuế GTGT đầu vào – đầu ra</b>{" "}
                {gt.da_ghi ? <>✓ {gt.chung_tu}</> : "○"}{" "}
                <span className="muted">
                  đầu ra phải nộp {vnd(gt.dau_ra_phai_nop)} · đầu vào được khấu trừ{" "}
                  {vnd(gt.dau_vao_duoc_khau_tru)} · <b>bù trừ {vnd(gt.so_bu_tru)}</b>
                  {gt.ky_ke_khai ? <> · kê khai theo {gt.ky_ke_khai === "quy" ? "quý" : "tháng"}</>
                                 : <> · <b>chưa đặt kỳ kê khai</b></>}
                </span>
                <p className="muted small" style={{ margin: "6px 0 0" }}>
                  Nợ {gt.tk_no} / Có {gt.tk_co} · còn phải nộp {vnd(gt.con_phai_nop)} · còn được
                  khấu trừ {vnd(gt.con_duoc_khau_tru)}
                </p>
                {gt.canh_bao?.map((c: string, i: number) => <p key={i} className="warn">{c}</p>)}
                <p className="muted">{gt.ghi_chu}</p>
                {!gt.da_ghi && gt.da_bat && (gt.but_toan || []).length > 0 && (
                  <button onClick={buTruGt} disabled={dang}>Ghi bút toán bù trừ</button>)}
              </div>)}
            {kc.buoc.map((b: Buoc) => (
              <div key={b.buoc} className="buoc">
                <b>Bước {b.buoc} – {b.ten}</b>{" "}
                {b.da_ghi ? <Tag>đã ghi · {b.chung_tu}</Tag> : <Tag cls="warn">chưa ghi</Tag>}
                <span className="num"> {vnd(b.tong)} đ</span>
                {b.dong?.length ? (
                  <div className="muted small">
                    {b.dong.map((d: any) => `${d.tk} ${vnd(d.so_tien)}`).join(" · ")}
                  </div>
                ) : null}
              </div>
            ))}
            {ghiDuoc ? (
              <button onClick={() => ketChuyen()} disabled={dang}>Ghi các bước chưa ghi</button>
            ) : null}
          </>
        ) : null}
      </div>

      {ghiDuoc ? (
        <div className="card">
          <h3>3. Khóa sổ kỳ</h3>
          <p className="muted small">
            Khóa là chốt chặn cuối của quyết định &quot;nhập là dùng luôn&quot;. Sau khi khóa, số của kỳ này
            không sửa được bằng cách nhập đè – phải lập bút toán điều chỉnh ở kỳ hiện tại.
          </p>
          <button onClick={khoaKy} disabled={dang || tt?.da_khoa}>
            {tt?.da_khoa ? `Kỳ ${ky} đã khóa` : `Khóa sổ kỳ ${ky}`}
          </button>
        </div>
      ) : null}

      <MucDoChan />
      <TachNhiem />
      <TienCapCha />
      <DoiChieuLaiLo />

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1000px; }
        .card { border: 1px solid var(--vtos-line); border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
        .tbl { width: 100%; border-collapse: collapse; margin: 8px 0; }
        .tbl td, .tbl th { border-bottom: 1px solid var(--vtos-line); padding: 6px 8px; text-align: left; }
        .num { text-align: right; font-variant-numeric: tabular-nums; }
        .lbl { width: 130px; color: var(--vtos-text-mute); }
        .chip { display: inline-block; margin-right: 10px; }
        .buoc { padding: 6px 0; border-bottom: 1px solid var(--vtos-line); }
        input, select { padding: 6px 8px; border: 1px solid var(--vtos-line); border-radius: 6px; }
        button { padding: 7px 12px; border-radius: 8px; border: 1px solid var(--vtos-sky);
                 background: var(--vtos-sky); color: var(--vtos-text-on-navy); cursor: pointer; margin-right: 8px; }
        button.ghost { background: var(--vtos-card); color: var(--vtos-text); border-color: var(--vtos-line); }
        button:disabled { opacity: .5; cursor: default; }
        .muted { color: var(--vtos-text-mute); }
        .small { font-size: 12px; }
        .ok { color: var(--vtos-success); }
        .warn { color: var(--vtos-warning); background: var(--vtos-warning-bg); padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

/** Đợt E1 – cửa nhập mức độ chặn và chiều phân tích.
 *
 *  Hai bảng này là CHÍNH SÁCH, không phải số liệu, nên chúng ở cùng màn hình kết sổ: người quyết
 *  một phép kiểm chặn hay không chính là người chịu trách nhiệm kỳ sổ ấy.
 *
 *  Ba chỗ trên giao diện là quy tắc chứ không phải trang trí:
 *    - Ô "Mức" để TRỐNG được, và trống không phải "không chặn" — nó là CHƯA AI ĐẶT, và những
 *      phép kiểm như vậy hiện thành một dòng đếm riêng ở đầu bảng.
 *    - Bốn LUẬT CỨNG chỉ hiện ra để đọc, không có ô chọn. Chúng luôn chặn.
 *    - Cờ chiều phân tích: BẬT thì Kế toán bấm được, TẮT thì máy chủ đòi chữ ký — giao diện không
 *      giấu nút, vì giấu nút không phải một hàng rào. Máy chủ trả 403 và người dùng đọc được lý do.
 */
function MucDoChan() {
  const { user, toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [tk, setTk] = useState<any>(null);
  const [m, setM] = useState<any>({ ma_phep_kiem: "", ten: "", muc_do: "", nguoi_xu_ly: "",
                                    han_xu_ly_ngay: "", nguoi_thay_the: "", can_cu: "" });
  const [maTk, setMaTk] = useState("");
  const kyDuoc = user?.role === "chutich" || user?.role === "tgd";

  const load = useCallback(async () => {
    try {
      setD(await api<any>("/hach-toan/muc-do-chan"));
      setTk(await api<any>("/hach-toan/tai-khoan-chieu?chi_da_khai=true"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const dat = async () => {
    try {
      const body: any = { ...m };
      body.han_xu_ly_ngay = m.han_xu_ly_ngay ? Number(m.han_xu_ly_ngay) : null;
      const r = await api<any>("/hach-toan/muc-do-chan", { method: "POST", json: body });
      toast(r.message); await load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const khai = async (code: string, patch: any) => {
    try {
      const r = await api<any>("/hach-toan/tai-khoan-chieu",
                               { method: "POST", json: { code, ...patch } });
      toast(r.message); await load();
    } catch (e) { toast(errMsg(e), true); }
  };

  if (!d) return null;
  return (
    <>
      <h2 style={{ marginTop: 28 }}>Mức độ chặn của từng phép kiểm</h2>
      {d.chua_dat_muc?.length ? (
        <p className="cb-vang">
          {d.chua_dat_muc.length} phép kiểm chưa ai đặt mức, đang chạy ở mức nhẹ nhất
          (cảnh báo nhưng cho qua): {d.chua_dat_muc.join(", ")}
        </p>
      ) : <p className="small ok">Mọi phép kiểm của đợt này đã có người đặt mức.</p>}

      <p className="small muted">
        Bốn luật cứng luôn chặn và không đặt mức được: {d.luat_cung.join(" · ")}
      </p>

      <table><thead><tr>
        <th>Phép kiểm</th><th>Mức</th><th>Ai xử lý</th><th>Hạn</th><th>Người thay</th>
        <th>Hiệu lực</th><th>Người ký</th>
      </tr></thead><tbody>
        {d.dong.map((r: any) => (
          <tr key={r.id}>
            <td>{r.ten}<div className="small muted">{r.ma_phep_kiem}</div></td>
            <td>{r.muc_do ? d.muc_do[r.muc_do] : <span className="so-vang">chưa đặt</span>}</td>
            <td>{r.nguoi_xu_ly || "—"}</td>
            <td>{r.han_xu_ly_ngay ? `${r.han_xu_ly_ngay} ngày` : "—"}</td>
            <td>{r.nguoi_thay_the || "—"}</td>
            <td>{r.ngay_hieu_luc || "ngay"}</td>
            <td>{r.nguoi_ky || "—"}</td>
          </tr>
        ))}
        {d.dong.length === 0 ? (
          <tr><td colSpan={7} className="muted">Chưa có dòng nào. Bảng bắt đầu rỗng.</td></tr>
        ) : null}
      </tbody></table>

      {kyDuoc ? (
        <div className="row" style={{ flexWrap: "wrap", marginTop: 10 }}>
          <input placeholder="mã phép kiểm" value={m.ma_phep_kiem}
                 onChange={(e) => setM({ ...m, ma_phep_kiem: e.target.value })} style={{ width: 200 }} />
          <input placeholder="tên đọc được" value={m.ten}
                 onChange={(e) => setM({ ...m, ten: e.target.value })} style={{ width: 240 }} />
          <select value={m.muc_do} onChange={(e) => setM({ ...m, muc_do: e.target.value })}>
            <option value="">— chưa đặt —</option>
            {Object.entries(d.muc_do).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select>
          <input placeholder="vai xử lý" value={m.nguoi_xu_ly}
                 onChange={(e) => setM({ ...m, nguoi_xu_ly: e.target.value })} style={{ width: 120 }} />
          <input placeholder="hạn (ngày)" value={m.han_xu_ly_ngay}
                 onChange={(e) => setM({ ...m, han_xu_ly_ngay: e.target.value })} style={{ width: 100 }} />
          <input placeholder="vai thay khi quá hạn" value={m.nguoi_thay_the}
                 onChange={(e) => setM({ ...m, nguoi_thay_the: e.target.value })} style={{ width: 160 }} />
          <input placeholder="căn cứ" value={m.can_cu}
                 onChange={(e) => setM({ ...m, can_cu: e.target.value })} style={{ width: 240 }} />
          <button onClick={dat}>Đặt mức</button>
        </div>
      ) : <p className="small muted">Đặt mức là việc của Chủ tịch hoặc TGĐ — hạ một mức chặn là nới một hàng rào.</p>}

      <h2 style={{ marginTop: 28 }}>Chiều phân tích đã khai trên tài khoản</h2>
      <p className="small muted">
        {tk ? `${tk.tong} tài khoản, trong đó ${tk.chua_khai_tinh_chat} tài khoản chưa khai tính chất.` : ""}
        {" "}Trống không phải &quot;dư Nợ&quot; — trống là chưa ai khai, nên phép kiểm số dư bất thường
        bỏ qua tài khoản ấy.
      </p>
      <table><thead><tr>
        <th>TK</th><th>Tên</th><th>Tính chất</th><th>Đối tượng</th><th>Công trình</th><th>Khoản mục</th>
      </tr></thead><tbody>
        {(tk?.dong || []).map((t: any) => (
          <tr key={t.code}>
            <td>{t.code}</td><td>{t.name}</td>
            <td>{t.tinh_chat ? tk.tinh_chat[t.tinh_chat] : <span className="muted">chưa khai</span>}</td>
            <td>{t.td_doi_tuong ? (t.td_doi_tuong_loai || "tất cả") : "—"}</td>
            <td>{t.td_cong_trinh ? "bắt buộc" : "—"}</td>
            <td>{t.td_khoan_muc ? "bắt buộc" : "—"}</td>
          </tr>
        ))}
        {(tk?.dong || []).length === 0 ? (
          <tr><td colSpan={6} className="muted">Chưa tài khoản nào khai chiều.</td></tr>
        ) : null}
      </tbody></table>
      <div className="row" style={{ marginTop: 10 }}>
        <input placeholder="số tài khoản" value={maTk}
               onChange={(e) => setMaTk(e.target.value)} style={{ width: 120 }} />
        <button className="ghost" onClick={() => khai(maTk, { td_cong_trinh: true })}>
          Bắt buộc mã tour
        </button>
        <button className="ghost" onClick={() => khai(maTk, { td_doi_tuong: true })}>
          Bắt buộc đối tượng
        </button>
        <button className="ghost" onClick={() => khai(maTk, { td_khoan_muc: true })}>
          Bắt buộc khoản mục
        </button>
      </div>
    </>
  );
}


/** Sổ tách bạch trách nhiệm — Đợt E2b-1, cửa cho những gì Đợt E2a đã dựng.
 *
 *  Đợt E2a dựng hai bảng, một bộ kiểm và năm cửa API rồi dừng. Không màn hình nào. Mà quy tắc đã
 *  ghi từ 09/9/2026: mỗi con số hệ thống cần một cửa cho người bấm; không có cửa thì đó là việc
 *  CÒN THIẾU. Màn hình này là cái cửa ấy, không thêm một phép tính nào mới.
 *
 *  Bốn chỗ trên giao diện là quy tắc chứ không phải trang trí:
 *
 *    - Ô "Mức" để TRỐNG được, và trống KHÔNG phải "không chặn" — nó là CHƯA AI ĐẶT, và những cặp
 *      như vậy hiện thành một dòng đếm riêng. Cho qua mà có người đếm thì được; cho qua trong im
 *      lặng thì không.
 *    - HẠ mức hay TẮT một cặp thì hỏi CĂN CỨ trước khi gửi. Máy chủ vẫn đòi lần nữa và vẫn đòi
 *      chữ ký Chủ tịch/TGĐ — giao diện hỏi sớm để người bấm biết mình đang nới cái gì, chứ không
 *      phải để thay hàng rào. Giấu nút không phải một hàng rào.
 *    - Dấu chân CHỈ ĐỌC, không có nút thêm. Gõ tay được vào sổ này thì dựng được một dấu chân cho
 *      một bước chưa ai làm — đúng thứ nó sinh ra để chống.
 *    - Bảng HAI VAI TRÙNG NGƯỜI không có nút sửa. Việc phải làm là thu hồi một quyền, ở màn hình
 *      phân quyền và do người có quyền ấy làm. Ở đây nó chỉ phải ĐẾM ĐƯỢC và GỌI ĐƯỢC TÊN.
 */
function TachNhiem() {
  const { user, toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [tk, setTk] = useState<any>(null);
  const [hv, setHv] = useState<any>(null);
  const [pv, setPv] = useState("");
  const [dc, setDc] = useState<any>(null);
  const [dang, setDang] = useState(false);
  const kyDuoc = user?.role === "chutich" || user?.role === "tgd";

  const load = useCallback(async () => {
    try {
      const [a, b, c] = await Promise.all([
        api<any>("/hach-toan/cap-tach-nhiem"),
        api<any>("/hach-toan/thieu-ma-nhan-vien"),
        api<any>("/hach-toan/hai-vai-trung-nguoi"),
      ]);
      setD(a); setTk(b); setHv(c);
    } catch (e) { toast(errMsg(e)); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  const nap = async () => {
    setDang(true);
    try {
      const r = await api<any>("/hach-toan/cap-tach-nhiem/nap-da-ky", { method: "POST" });
      toast(r.message); await load();
    } catch (e) { toast(errMsg(e)); } finally { setDang(false); }
  };

  const datMuc = async (c: any, muc_do: string) => {
    // NỚI thì hỏi căn cứ TRƯỚC khi gửi. Máy chủ vẫn kiểm lại — đây là để người bấm đọc được
    // mình đang làm gì, không phải để thay hàng rào.
    const dangChan = c.muc_do_dang_ap === "canh_bao_va_chan";
    const noi = dangChan && muc_do !== "canh_bao_va_chan";
    let can_cu = "";
    if (noi) {
      can_cu = prompt(
        `Hạ mức cặp "${c.ma_cap}" từ "chặn" xuống "${d?.muc_do?.[muc_do] || muc_do}".\n` +
        `Phải ghi CĂN CỨ, và phải có chữ ký Chủ tịch hoặc TGĐ.\nCăn cứ:`) || "";
      if (!can_cu.trim()) { toast("Chưa ghi căn cứ — không gửi."); return; }
    }
    setDang(true);
    try {
      const r = await api<any>("/hach-toan/cap-tach-nhiem", {
        method: "POST",
        json: { ma_cap: c.ma_cap, buoc_a: c.buoc_a, buoc_b: c.buoc_b, muc_do, can_cu },
      });
      toast(r.message); await load();
    } catch (e) { toast(errMsg(e)); } finally { setDang(false); }
  };

  const xemDauChan = async () => {
    if (!pv.trim()) { toast("Nhập phạm vi, ví dụ dc:12 hoặc ky:2026-09"); return; }
    try {
      setDc(await api<any>(`/hach-toan/dau-chan/${encodeURIComponent(pv.trim())}`));
    } catch (e) { toast(errMsg(e)); }
  };

  const chuaDat = d?.chua_dat_muc || [];

  return (
    <>
      <h3 style={{ marginTop: 28 }}>Sổ tách bạch trách nhiệm</h3>
      <p className="muted">
        Một người không được đi cả hai bước của một cặp đã ký. So theo NGƯỜI (mã nhân viên), không
        theo tài khoản — hai tài khoản của cùng một người vẫn là một người.
      </p>

      <div className="row" style={{ gap: 8, marginBottom: 10 }}>
        <button className="ghost" onClick={nap} disabled={dang}>
          Nạp các cặp đã ký
        </button>
        {chuaDat.length > 0 ? (
          <Tag cls="warn">{chuaDat.length} cặp chưa ai đặt mức — đang chạy mức nhẹ nhất
            “{d?.muc_do?.[d?.mac_dinh_khi_chua_khai] || d?.mac_dinh_khi_chua_khai}”</Tag>
        ) : null}
        {!kyDuoc ? <span className="muted">Hạ mức hoặc tắt một cặp cần chữ ký Chủ tịch/TGĐ.</span> : null}
      </div>

      <table><thead><tr>
        <th>Mã cặp</th><th>Hai bước không được cùng người</th><th>Mức đang áp</th>
        <th>Đặt mức</th><th>Người ký</th><th>Căn cứ</th>
      </tr></thead><tbody>
        {(d?.cac_cap || []).map((c: any) => (
          <tr key={c.ma_cap}>
            <td>{c.ma_cap}{!c.dang_ap_dung ? <> <Tag cls="warn">đã tắt</Tag></> : null}</td>
            <td>{c.ten || `${c.buoc_a} ↔ ${c.buoc_b}`}</td>
            <td>
              {d?.muc_do?.[c.muc_do_dang_ap] || c.muc_do_dang_ap}
              {!c.muc_do_khai ? <> <span className="muted">(chưa ai đặt)</span></> : null}
            </td>
            <td>
              <select value={c.muc_do_khai || ""} disabled={dang}
                      onChange={(e) => datMuc(c, e.target.value)}>
                <option value="">— chưa đặt —</option>
                {Object.entries(d?.muc_do || {}).map(([k, v]: any) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </td>
            <td>{c.nguoi_ky || <span className="muted">—</span>}</td>
            <td style={{ maxWidth: 320 }}>{c.can_cu || <span className="muted">—</span>}</td>
          </tr>
        ))}
        {(d?.cac_cap || []).length === 0 ? (
          <tr><td colSpan={6} className="muted">
            Chưa nạp cặp nào. Bấm “Nạp các cặp đã ký”.
          </td></tr>
        ) : null}
      </tbody></table>

      <h4 style={{ marginTop: 22 }}>Dấu chân — ai đã làm bước gì</h4>
      <div className="row" style={{ gap: 8 }}>
        <input placeholder="dc:12 hoặc ky:2026-09" value={pv}
               onChange={(e) => setPv(e.target.value)} style={{ width: 200 }} />
        <button className="ghost" onClick={xemDauChan}>Xem dấu chân</button>
        <span className="muted">Chỉ đọc — hệ thống tự ghi khi một bước hoàn thành.</span>
      </div>
      {dc ? (
        <table style={{ marginTop: 8 }}><thead><tr>
          <th>Bước</th><th>Mã người</th><th>Tài khoản</th><th>Vai</th><th>Lúc</th>
        </tr></thead><tbody>
          {(dc.dau_chan || []).map((x: any, i: number) => (
            <tr key={i}>
              <td>{x.ma_buoc}</td><td>{x.ma_nguoi}</td><td>{x.username}</td>
              <td>{x.vai}</td><td>{x.luc}</td>
            </tr>
          ))}
          {(dc.dau_chan || []).length === 0 ? (
            <tr><td colSpan={5} className="muted">
              Phạm vi “{dc.pham_vi}” chưa có dấu chân nào.
            </td></tr>
          ) : null}
        </tbody></table>
      ) : null}

      <h4 style={{ marginTop: 22 }}>Hai vai không được kiêm nhau</h4>
      <p className="muted">
        Chủ tịch chốt 10/10/2026: HCNS riêng, thủ quỹ riêng. Một tài khoản không thể là cả hai —
        chỗ lọt được là một người hai tài khoản. Bảng này chỉ ĐẾM và GỌI TÊN; thu hồi quyền làm ở
        màn hình phân quyền.
      </p>
      {hv ? (
        <div className="row" style={{ gap: 8, marginBottom: 8 }}>
          {hv.so_truong_hop === 0
            ? <Tag cls="ok">Không trường hợp nào</Tag>
            : <Tag cls="red">{hv.so_truong_hop} người đang giữ cả hai vai</Tag>}
          {hv.mu_khi_thieu_ma_nv ? (
            <Tag cls="warn">
              Chưa đọc được hết: {hv.so_tai_khoan_thieu_ma_nv} tài khoản chưa có mã nhân viên,
              số trên không có nghĩa là sạch
            </Tag>
          ) : null}
        </div>
      ) : null}
      {(hv?.cac_truong_hop || []).length > 0 ? (
        <table><thead><tr>
          <th>Cặp vai</th><th>Mã người</th><th>Họ tên</th><th>Tài khoản</th>
        </tr></thead><tbody>
          {hv.cac_truong_hop.map((x: any, i: number) => (
            <tr key={i}>
              <td>{x.ten || x.ma_cap}</td><td>{x.ma_nguoi}</td>
              <td>{x.ho_ten || <span className="muted">—</span>}</td>
              <td>{(x.tai_khoan || []).join(", ")}</td>
            </tr>
          ))}
        </tbody></table>
      ) : null}

      <h4 style={{ marginTop: 22 }}>Tài khoản vai tiền chưa có mã nhân viên</h4>
      <div className="row" style={{ gap: 8, marginBottom: 8 }}>
        {tk ? (tk.so_tai_khoan === 0
          ? <Tag cls="ok">Đủ mã</Tag>
          : <Tag cls="warn">{tk.so_tai_khoan} tài khoản thiếu mã</Tag>) : null}
        {tk ? (
          <span className="muted">
            {tk.dang_bat_buoc
              ? "Đang BẮT BUỘC: thiếu mã thì chặn bước nhạy cảm."
              : `Chưa bắt buộc. Tham số bật: ${tk.tham_so_bat}`}
          </span>
        ) : null}
      </div>
      {(tk?.tai_khoan || []).length > 0 ? (
        <table><thead><tr>
          <th>Tài khoản</th><th>Họ tên</th><th>Vai</th><th>Bộ phận</th>
        </tr></thead><tbody>
          {tk.tai_khoan.map((x: any) => (
            <tr key={x.id}>
              <td>{x.username}</td><td>{x.ho_ten || <span className="muted">—</span>}</td>
              <td>{x.vai}</td><td>{x.bo_phan || <span className="muted">—</span>}</td>
            </tr>
          ))}
        </tbody></table>
      ) : null}
    </>
  );
}

/** Đợt TKC-1 — THẺ ĐỌC: bút toán đã ghi vào tài khoản CHA.
 *
 *  Cửa `/accounting/tien-ghi-cap-cha` có trên main từ Đợt R4c-3, nhưng cho tới hôm nay KHÔNG màn
 *  hình nào gọi nó — nên con số ấy có mà không ai nhìn thấy, và theo ranh giới 09/9/2026 thì một
 *  con số không có chỗ để đọc là việc còn thiếu, không phải việc đã xong.
 *
 *  THẺ NÀY KHÔNG CÓ NÚT NÀO LÀM ĐỔI SỔ. Không sửa, không đảo, không sinh bút toán điều chỉnh —
 *  Chủ tịch chốt 02/11/2026 để nguyên bút toán cũ. Nó chỉ ra CHỖ PHẢI NHÌN.
 *
 *  Hai bảng chứ không một, và đó là một phân biệt có lý do: bảng «từng chứng từ» bị cắt ở
 *  `gioi_han` dòng, nên ai cộng nhẩm trên đó sẽ cộng một phần rồi tưởng là toàn bộ. Bảng «theo
 *  tài khoản» đếm trên TOÀN BỘ, không cắt — nên con số tổng phải đọc ở bảng ấy.
 */
function TienCapCha() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(false);
  // Từ ĐẦU NĂM, không theo ô «Kỳ» ở đầu màn hình: câu hỏi «sổ đã ghi vào tài khoản cha bao nhiêu»
  // là câu hỏi LŨY KẾ, không phải câu hỏi của một kỳ. Để trống thì nặng, nên mặc định là đầu năm
  // và người đọc tự nới ra nếu muốn.
  const dauNam = `${new Date().getFullYear()}-01-01`;
  const homNay = new Date().toISOString().slice(0, 10);
  const [tu, setTu] = useState(dauNam);
  const [den, setDen] = useState(homNay);

  const load = useCallback(async () => {
    setDang(true);
    try {
      const q = new URLSearchParams();
      if (tu) q.set("tu", tu);
      if (den) q.set("den", den);
      setD(await api<any>(`/accounting/tien-ghi-cap-cha?${q.toString()}`));
    } catch (e: any) {
      toast(e?.message || "không đọc được");
    } finally {
      setDang(false);
    }
  }, [tu, den, toast]);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      <h2 style={{ marginTop: 28 }}>Bút toán đã ghi vào tài khoản cha</h2>

      <div className="row">
        <label>Từ ngày</label>
        <input type="date" value={tu} onChange={(e) => setTu(e.target.value)} />
        <label>Đến ngày</label>
        <input type="date" value={den} onChange={(e) => setDen(e.target.value)} />
        <button className="ghost" onClick={load} disabled={dang}>Xem lại</button>
        <Tag cls="warn">CHỈ ĐỌC — không sửa, không đảo</Tag>
      </div>

      {d ? (
        <div className="card">
          <div className="row">
            <span className="chip"><b>{d.so_tai_khoan_cha}</b> tài khoản cha trong danh mục</span>
            <span className="chip"><b>{d.so_tai_khoan_co_but_toan}</b> tài khoản cha có bút toán</span>
            <span className="chip"><b>{d.so_dong}</b> dòng sổ</span>
            <span className="chip">tổng <b>{vnd(d.so_tien)}</b></span>
          </div>

          {d.so_dong === 0 ? (
            <p className="ok">Không có bút toán nào ghi vào tài khoản cha trong khoảng này.</p>
          ) : null}

          <p className="muted small">{d.ghi_chu}</p>

          {/* Cờ `is_detail` lệch với bảng quan hệ cha–con là một chuyện phải nói ra, không phải
              một chi tiết kỹ thuật giấu đi: ai viết phép chặn dựa vào cờ ấy sẽ chặn sai chỗ. */}
          {d.co_is_detail_lech?.length ? (
            <div className="cb-vang">
              <p><b>{d.co_is_detail_lech.length} tài khoản có cờ `is_detail` lệch</b> với bảng
                 quan hệ cha–con: {d.co_is_detail_lech.join(", ")}.</p>
              <p className="small">Thẻ này đọc bảng quan hệ, nên số ở trên vẫn đúng. Nhưng phép
                 chặn sau này mà đọc cờ thì sẽ chặn sai chỗ — phải dọn cờ trước.</p>
            </div>
          ) : null}

          {d.theo_tai_khoan?.length ? (
            <>
              <h4 style={{ marginTop: 20 }}>Theo tài khoản</h4>
              <table><thead><tr>
                <th>Tài khoản cha</th><th>Tên</th><th className="num">Số con</th>
                <th className="num">Dòng</th><th className="num">Nợ</th><th className="num">Có</th>
              </tr></thead><tbody>
                {d.theo_tai_khoan.map((g: any) => (
                  <tr key={g.tai_khoan}>
                    <td>{g.tai_khoan}</td>
                    <td>{g.ten || <span className="muted">—</span>}</td>
                    <td className="num">{g.so_con}</td>
                    <td className="num">{g.so_dong}</td>
                    <td className="num">{vnd(g.no)}</td>
                    <td className="num">{vnd(g.co)}</td>
                  </tr>
                ))}
              </tbody></table>
            </>
          ) : null}

          {/* ĐỢT TKC-2 — GỘP THEO ĐƯỜNG GHI. Đây là bảng để QUYẾT nhịp 2: tài khoản không cho
              biết phải sửa tệp nào, đường ghi thì cho. Cột «Kỳ cuối» chia việc làm hai loại —
              còn ghi gần đây thì phải NẮN MÃ trước khi chặn; kỳ cuối đã lâu thì chỉ còn SỐ CŨ,
              là việc Kế toán trưởng quyết riêng, không sửa một dòng mã nào. */}
          {d.theo_duong_ghi?.length ? (
            <>
              <h4 style={{ marginTop: 20 }}>Theo đường ghi</h4>
              <p className="muted small" style={{ margin: "0 0 4px" }}>
                Đếm trên TOÀN BỘ, không cắt ở giới hạn. «Kỳ cuối» còn gần đây nghĩa là đường ghi
                ấy vẫn đang chạy — phải nắn mã trước khi bật chặn.
              </p>
              <table><thead><tr>
                <th>Đường ghi</th><th>Nghiệp vụ</th><th className="num">Dòng</th>
                <th className="num">Chứng từ</th><th>Tài khoản cha chạm</th>
                <th>Kỳ đầu</th><th>Kỳ cuối</th><th className="num">Tiền</th>
              </tr></thead><tbody>
                {d.theo_duong_ghi.map((g: any) => (
                  <tr key={g.nguon + "|" + g.nghiep_vu}>
                    <td>{g.nguon || <span className="muted">—</span>}</td>
                    <td>{g.ten_nghiep_vu || g.nghiep_vu || <span className="muted">—</span>}</td>
                    <td className="num">{g.so_dong}</td>
                    <td className="num">{g.so_chung_tu}</td>
                    <td>{(g.tai_khoan || []).join(" ")}</td>
                    <td>{g.ky_dau || <span className="muted">—</span>}</td>
                    <td><b>{g.ky_cuoi || "—"}</b></td>
                    <td className="num">{vnd(g.no + g.co)}</td>
                  </tr>
                ))}
              </tbody></table>
            </>
          ) : null}

          {d.dong?.length ? (
            <>
              <h4 style={{ marginTop: 20 }}>Từng chứng từ</h4>
              {d.cat_bot ? (
                <p className="muted small">
                  Hiện {d.dong.length} dòng gần nhất trên tổng {d.so_dong} — bảng này ĐÃ CẮT BỚT,
                  nên đừng cộng nhẩm ở đây; số tổng đọc ở bảng «Theo tài khoản».
                </p>
              ) : null}
              <table><thead><tr>
                <th>Chứng từ</th><th>Ngày</th><th>Tài khoản</th><th>Diễn giải</th>
                <th className="num">Nợ</th><th className="num">Có</th><th>Nguồn</th>
              </tr></thead><tbody>
                {d.dong.map((x: any, i: number) => (
                  <tr key={`${x.chung_tu}-${i}`}>
                    <td>{x.chung_tu}</td><td>{x.ngay}</td><td>{x.tai_khoan}</td>
                    <td>{x.dien_giai || <span className="muted">—</span>}</td>
                    <td className="num">{vnd(x.no)}</td><td className="num">{vnd(x.co)}</td>
                    <td>{x.nguon || <span className="muted">—</span>}</td>
                  </tr>
                ))}
              </tbody></table>
            </>
          ) : null}
        </div>
      ) : null}
    </>
  );
}

/** Đợt R5b-2 — THẺ ĐỌC: đối chiếu lãi lỗ tour, SỔ ↔ BẢNG TÍNH — trên màn KẾT SỔ.
 *
 *  VÌ SAO Ở `/ket-so` CHỨ KHÔNG Ở `/accounting`: màn Kế toán KHÔNG khai nhóm
 *  `/api/v1/accounting` trong `MAN_HINH_API`, nên đặt thẻ ở đó buộc phải thêm một dòng vào
 *  bảng quyền — và dòng ấy cộng vào `pham_vi_day_du`, tức bảng ký sẽ nói `tp_dh` (Trưởng
 *  phòng Điều hành) với tới được cửa này, đúng thứ Đợt R5b-1 cố ý không mở. `/ket-so` đã
 *  khai sẵn cả nhóm ấy và chỉ Kế toán + CNTT thấy, nên đặt ở đây KHÔNG đụng bảng quyền
 *  một dòng nào. Chủ tịch chốt 06/11/2026 sau khi hàng rào `test_p2` bắt được chỗ này.
 *
 *  Cửa `/accounting/doi-chieu-lai-lo` vào main hôm nay (Đợt R5b-1, viết 02/11). Nhưng một con số
 *  không có chỗ để đọc là việc CÒN THIẾU, không phải việc đã xong — ranh giới 09/9/2026. Thẻ này
 *  là chỗ đọc ấy.
 *
 *  KHÔNG CÓ NÚT NÀO SỬA BÊN NÀO. Đối chiếu là để NÓI RA chênh lệch, không để sửa cho khớp. Sửa
 *  bên bảng tính là đổi số qua một cửa không có bộ kiểm; sửa bên sổ còn là ghi sổ không qua
 *  chứng từ.
 *
 *  BA ĐIỀU GIAO DIỆN PHẢI GIỮ, và cả ba là quy tắc chứ không phải trang trí:
 *
 *    - DÒNG CỘNG CHỈ GỘP NHỮNG DÒNG SO ĐƯỢC CẢ HAI BÊN. Máy chủ đã cộng đúng như vậy trong
 *      `cong`; màn hình KHÔNG được tự cộng lại từ `dong`, vì `dong` bị cắt ở `gioi_han`.
 *    - DÒNG THIẾU MỘT BÊN HIỆN LÀ «chưa so được», không phải «lệch bằng cả bên kia». Một tour
 *      chưa ghi sổ mà báo lệch 900 triệu là nói SỔ SAI, trong khi sự thật là sổ chưa có gì.
 *    - HAI CƠ SỞ NGÀY KHÁC NHAU thì NÓI RA. Sổ lọc theo ngày hạch toán, bảng tính lấy chuyến
 *      theo ngày khởi hành. Lệch do chuyến tháng 12 mà hóa đơn về tháng 1 là lệch THẬT và là
 *      một việc phải xử — gộp hai cơ sở ngày lại là xoá mất chính câu hỏi ấy.
 */
function DoiChieuLaiLo() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  // THÁNG TRƯỚC, không phải từ đầu năm: đối chiếu là việc CỦA MỘT KỲ — xong một kỳ rồi mới sang
  // kỳ sau. (Thẻ «tài khoản cha» thì ngược lại, để từ đầu năm, vì đó là câu hỏi lũy kế.)
  const thangTruoc = () => {
    const n = new Date();
    const d1 = new Date(n.getFullYear(), n.getMonth() - 1, 1);
    const d2 = new Date(n.getFullYear(), n.getMonth(), 0);
    const s = (x: Date) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
    return [s(d1), s(d2)];
  };
  const [tu, setTu] = useState(thangTruoc()[0]);
  const [den, setDen] = useState(thangTruoc()[1]);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setD(await api<any>(`/accounting/doi-chieu-lai-lo?tu=${tu}&den=${den}`));
    } catch (e: any) {
      toast(errMsg(e), true);
    } finally {
      setBusy(false);
    }
  }, [tu, den, toast]);

  useEffect(() => { load(); }, [load]);

  // `fmtD` KHONG duoc nhap o man Ket so — khong them import chi de dinh dang mot cot.
  const fmtNgay = (v: any) => (typeof v === "string" && v.length >= 10
    ? `${v.slice(8, 10)}-${v.slice(5, 7)}-${v.slice(0, 4)}` : String(v ?? ""));
  const oSo = (v: any) => (v === null || v === undefined ? "—" : vnd(v));
  const c = d?.cong;

  return (<>
    <h2 style={{ marginTop: 28 }}>Đối chiếu lãi lỗ tour — SỔ ↔ BẢNG TÍNH</h2>

    <div className="row">
      <label>Từ ngày <input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></label>
      <label>đến <input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></label>
      <button className="ghost" onClick={load} disabled={busy}>Xem lại</button>
      <Tag cls="warn">CHỈ ĐỌC — không sửa bên nào</Tag>
      {d ? (d.khop ? <Tag cls="ok">Khớp</Tag> : <Tag cls="red">Có chênh lệch</Tag>) : null}
    </div>

    {d && <>
      <div className="card">
        <div className="row">
          <span className="chip"><b>{d.tong_dong}</b> mã tour</span>
          <span className="chip"><b>{c?.so_dong_so_duoc ?? 0}</b> so được cả hai bên</span>
          <span className="chip"><b>{c?.so_dong_chua_so_duoc ?? 0}</b> chưa so được</span>
          <span className="chip">lệch lợi nhuận <b>{oSo(c?.lech_loi_nhuan)}</b></span>
        </div>
        <p className="muted">{d.ghi_chu}</p>

        {/* Hai cơ sở ngày — nói ra, không gộp. */}
        <p className="muted small">
          {d.co_so_ngay?.so} · {d.co_so_ngay?.bang_tinh}
        </p>

        {/* Ba rổ cảnh báo đến THẲNG từ máy chủ — màn hình không tự nghĩ ra rổ nào. */}
        {(d.canh_bao || []).map((cb: any, i: number) => (
          <div key={i} className={cb.muc === "do" ? "cb-do" : "cb-vang"}>
            <b>{cb.so_dong} dòng — {cb.ten}</b>
            <div className="small">{cb.chi_tiet}</div>
            {(cb.ma || []).length ? <div className="small">Mã: {(cb.ma || []).join(", ")}</div> : null}
          </div>
        ))}
      </div>

      <table>
        <thead>
          <tr>
            <th rowSpan={2}>Mã tour</th><th rowSpan={2}>Tên chuyến</th><th rowSpan={2}>Khởi hành</th>
            <th colSpan={3} style={{ textAlign: "center" }}>SỔ</th>
            <th colSpan={3} style={{ textAlign: "center" }}>BẢNG TÍNH</th>
            <th rowSpan={2} className="num">Lệch lợi nhuận</th>
          </tr>
          <tr>
            <th className="num">Doanh thu</th><th className="num">Chi phí</th><th className="num">Lợi nhuận</th>
            <th className="num">Doanh thu</th><th className="num">Giá vốn</th><th className="num">Lợi nhuận</th>
          </tr>
        </thead>
        <tbody>
          {(d.dong || []).length ? (d.dong as any[]).map((r, i) => (
            <tr key={r.ma || i}>
              <td>{r.ma}</td>
              <td className="muted">{r.ten_tour || "—"}</td>
              <td>{r.ngay_khoi_hanh ? fmtNgay(r.ngay_khoi_hanh) : "—"}</td>
              <td className="num">{oSo(r.so_doanh_thu)}</td>
              <td className="num">{oSo(r.so_chi_phi)}</td>
              <td className="num">{oSo(r.so_loi_nhuan)}</td>
              <td className="num">{oSo(r.bt_doanh_thu)}</td>
              <td className="num">{oSo(r.bt_gia_von)}</td>
              <td className="num">{oSo(r.bt_loi_nhuan)}</td>
              {/* Thiếu một bên thì KHÔNG in một con số lệch — in trạng thái thứ ba. */}
              <td className="num">
                {r.chua_so_duoc ? <Tag>chưa so được</Tag>
                  : r.khop ? <Tag cls="ok">khớp</Tag>
                    : <b>{oSo(r.lech_loi_nhuan)}</b>}
              </td>
            </tr>
          )) : <tr><td colSpan={10} className="muted">Không có mã tour nào trong khoảng ngày này.</td></tr>}

          {/* DÒNG CỘNG LẤY THẲNG TỪ `cong` CỦA MÁY CHỦ, không tự cộng lại từ `dong`: `dong` bị
              cắt ở `gioi_han`, nên cộng ở đây là cộng một phần rồi gọi đó là tổng. */}
          {c && <tr>
            <td colSpan={3}><b>Cộng</b> <span className="muted small">({c.so_dong_so_duoc} dòng so được)</span></td>
            <td className="num"><b>{oSo(c.so_doanh_thu)}</b></td>
            <td className="num"><b>{oSo(c.so_chi_phi)}</b></td>
            <td className="num"><b>{oSo(c.so_loi_nhuan)}</b></td>
            <td className="num"><b>{oSo(c.bt_doanh_thu)}</b></td>
            <td className="num"><b>{oSo(c.bt_gia_von)}</b></td>
            <td className="num"><b>{oSo(c.bt_loi_nhuan)}</b></td>
            <td className="num"><b>{oSo(c.lech_loi_nhuan)}</b></td>
          </tr>}
        </tbody>
      </table>

      {d.cat_bot
        ? <p className="muted">Hiện {d.hien_dong} trong {d.tong_dong} mã — bảng này ĐÃ CẮT BỚT, nên đừng cộng nhẩm ở đây; <b>dòng Cộng mới là tổng</b>, và nó chỉ gộp những dòng so được cả hai bên.</p>
        : <p className="muted">Hiện đủ {d.tong_dong} mã. Dòng Cộng chỉ gộp {c?.so_dong_so_duoc ?? 0} dòng so được cả hai bên — hai rổ thiếu ở trên KHÔNG vào tổng.</p>}
    </>}
  </>);
}

export default function Page() {
  return <Shell><KetSo /></Shell>;
}
