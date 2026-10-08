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
                  <th>Phân loại</th><th>Mã đối tượng</th></tr></thead>
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

export default function Page() {
  return <Shell><KetSo /></Shell>;
}
