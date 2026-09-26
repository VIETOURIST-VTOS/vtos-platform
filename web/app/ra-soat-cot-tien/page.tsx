"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Rà soát cột tiền (K1, K2) – bàn làm việc của Kế toán, KHÔNG nằm trong màn hình Kiểm soát.
 *
 *  Chủ tịch quyết ngày 08/9/2026: Kế toán không xem màn hình Kiểm soát. Nhưng chính Kế toán trưởng là
 *  người QUYẾT một cột có phải tiền hay không – đó là câu hỏi nghiệp vụ, không phải câu hỏi kỹ thuật.
 *
 *  Hai việc đó không mâu thuẫn, chúng chỉ cần ở hai chỗ khác nhau: kết quả quét của robot và bảng chấm
 *  điểm phòng ban ở lại màn hình Kiểm soát; bàn quyết cột tiền ra đây, dưới nhóm Tài chính & Kế toán.
 *  Người bị chấm điểm không ngồi cùng bàn với bảng chấm điểm.
 *
 *  Màn hình cố ý KHÔNG có nút "quyết tất cả": mỗi dòng là một quyết định về một cột trong sổ, và một
 *  lần bấm quyết cả trăm cột thì không còn là quyết định nữa.
 */
type Dong = {
  id: number; bang: string; cot: string; kieu: string;
  xep: string; xep_ten: string; xep_may: string; ly_do_may: string;
  quyet_nguoi: string; quyet_boi: string; ghi_chu: string;
  cho_rong: boolean; mac_dinh_0: boolean; thieu_thanh_0: boolean;
  da_quyet_giu: boolean; quyet_k2: string; quyet_k2_ten: string; can_doi_kieu: boolean;
};

const LOC: [string, string][] = [
  ["chua_ro", "Chờ tôi quyết (chưa rõ là tiền hay không)"],
  ["thieu_thanh_0", "K2 – cột tiền ghi 0 thay cho “chưa có số”"],
  ["can_doi_kieu", "K1 – cột tiền còn dùng số thực nhị phân"],
  ["tien", "Mọi cột đã xếp là tiền"],
  ["", "Toàn bộ"],
];

function RaSoatCotTien() {
  const { user, toast } = useShell();
  const [loc, setLoc] = useState("chua_ro");
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(false);
  const [nt, setNt] = useState<any>(null);
  const quyetDuoc = ["ketoan", "cntt", "chutich", "tgd"].includes(user?.role || "");

  const load = useCallback(async () => {
    try { setD(await api<any>(`/ra-soat-cot-tien${loc ? `?loc=${loc}` : ""}`)); }
    catch (e) { toast(errMsg(e), true); }
  }, [loc, toast]);
  useEffect(() => { load(); }, [load]);

  const quyet = async (id: number, truong: "quyet_nguoi" | "quyet_k2", gia_tri: string) => {
    let ghi_chu: string | undefined;
    if (truong === "quyet_k2" && gia_tri === "giu") {
      // Quyết GIỮ một cột tiền đang mặc định 0 là quyết rằng "chưa có số" sẽ tiếp tục bị ghi thành 0.
      // Đó là một quyết định phải giải trình được, nên bắt buộc có lý do.
      const ly_do = prompt("Giữ nguyên nghĩa là chấp nhận “chưa có số” bị ghi thành 0 ở cột này.\nLý do:");
      if (!ly_do || !ly_do.trim()) return;
      ghi_chu = ly_do.trim();
    }
    setDang(true);
    try {
      await api("/ra-soat-cot-tien/quyet", { method: "POST", json: { dong: [{ id, [truong]: gia_tri, ghi_chu }] } });
      await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const rows: Dong[] = d?.rows || [];
  const ntRows: any[] = nt?.rows || [];

  return (
    <div className="wrap">
      <h1>Rà soát cột tiền</h1>
      <p className="muted">
        Cột nào trong cơ sở dữ liệu là tiền, và cột tiền nào đang ghi <b>0</b> thay cho
        <b> “chưa có số”</b>. Máy xếp trước theo tên cột; chỗ tên cột không nói rõ thì để người quyết —
        vì đây là câu hỏi nghiệp vụ, không phải câu hỏi kỹ thuật.
      </p>

      {d ? (
        <div className="card">
          <div className="so">
            <span><b>{d.tong_cot}</b> cột số thực</span>
            <span><b>{d.so_tien}</b> là tiền</span>
            <span><b>{d.so_khong_tien}</b> không phải tiền</span>
            <span className={d.so_chua_ro ? "do" : ""}><b>{d.so_chua_ro}</b> chờ người quyết</span>
            <span><b>{d.so_float_tien}</b> còn số thực nhị phân (K1)</span>
            <span><b>{d.so_thieu_thanh_0}</b> ghi 0 thay “chưa có số” (K2)</span>
          </div>
          {d.so_chua_ro ? (
            <p className="warn">
              {d.so_chua_ro} cột chưa ai quyết. Chừng nào còn dòng ở đây thì V9 chưa đổi kiểu được cho
              chúng — đổi nhầm một cột không phải tiền cũng tốn đúng một lần nâng cấp cơ sở dữ liệu.
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="row">
        {LOC.map(([k, t]) => (
          <button key={k} className={loc === k ? "" : "ghost"} onClick={() => setLoc(k)}>{t}</button>
        ))}
      </div>

      <div className="card">
        <h3>{rows.length} dòng</h3>
        {rows.length === 0 ? <p className="muted">Không có dòng nào.</p> : (
          <table className="tbl">
            <thead>
              <tr><th>Bảng</th><th>Cột</th><th>Kiểu</th><th>Xếp loại</th>
                <th>Máy đọc vì sao</th><th>K2</th><th>Quyết</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.bang}</td>
                  <td className="mono">{r.cot}</td>
                  <td>{r.kieu === "Float" ? <Tag cls="warn">số thực</Tag> : <Tag>thập phân</Tag>}</td>
                  <td>
                    {r.xep_ten}
                    {r.quyet_nguoi ? <> <span className="muted small">· người quyết{r.quyet_boi ? ` (${r.quyet_boi})` : ""}</span></> : null}
                  </td>
                  <td className="muted small">{r.ly_do_may}</td>
                  <td>
                    {r.thieu_thanh_0 ? <Tag cls="warn">ghi 0 thay “chưa có số”</Tag>
                      : r.da_quyet_giu ? <Tag>giữ · {r.ghi_chu}</Tag>
                      : r.quyet_k2 ? <Tag>{r.quyet_k2_ten}</Tag> : <span className="muted">—</span>}
                  </td>
                  <td className="nut">
                    {quyetDuoc && r.xep === "chua_ro" ? (
                      <>
                        <button className="ghost" disabled={dang}
                                onClick={() => quyet(r.id, "quyet_nguoi", "tien")}>là tiền</button>
                        <button className="ghost" disabled={dang}
                                onClick={() => quyet(r.id, "quyet_nguoi", "khong_tien")}>không phải tiền</button>
                      </>
                    ) : null}
                    {quyetDuoc && r.thieu_thanh_0 ? (
                      <>
                        <button className="ghost" disabled={dang}
                                onClick={() => quyet(r.id, "quyet_k2", "sua")}>sửa</button>
                        <button className="ghost" disabled={dang}
                                onClick={() => quyet(r.id, "quyet_k2", "giu")}>giữ…</button>
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ══ SOÁT NGOẠI TỆ TRÊN DÒNG GIÁ VỐN — Chủ tịch quyết 27/9/2026 ══
          Đặt ở đây chứ không dựng màn hình mới: cùng một câu hỏi với cả trang này — con số tiền
          trong sổ có đang mang đúng nghĩa của nó không. CHỈ ĐỌC, cố ý không có nút nắn hàng loạt. */}
      <div className="card" style={{ marginTop: 18 }}>
        <h2 style={{ marginTop: 0 }}>Soát ngoại tệ trên dòng giá vốn</h2>
        <p className="muted small">
          Bảng <span className="mono">tour_cost_lines</span> có <b>hai cửa ghi</b>, và tới 27/9/2026 chúng hiểu
          ô <b>“số tiền gốc”</b> ngược nhau: cửa Điều hành hiểu là <b>đơn giá một đơn vị</b> (máy nhân tiếp với
          số lượng và hệ số), cửa Quyết toán chi tiết hiểu là <b>tổng cả dòng</b> (số lượng và hệ số biến mất).
          Chủ tịch chốt: <b>số tiền gốc là đơn giá</b>. Bảng này đếm xem bao nhiêu dòng đã ghi theo nghĩa kia
          và lệch bao nhiêu tiền — <b>máy không tự nắn</b>.
        </p>
        {!nt ? (
          <button className="ghost" onClick={() => api("/ra-soat-cot-tien/ngoai-te")
            .then(setNt).catch((e) => toast(errMsg(e), true))}>Chạy bản soát</button>
        ) : (<>
          <div className="so">
            <span><b>{nt.tong_dong_ngoai_te}</b> dòng khai ngoại tệ</span>
            <span><b>{nt.dem?.dung ?? 0}</b> đúng quy ước</span>
            <span style={{ color: nt.dem?.sai_bo_nhan ? "var(--vtos-danger)" : undefined }}>
              <b>{nt.dem?.sai_bo_nhan ?? 0}</b> bỏ mất số lượng/hệ số</span>
            <span><b>{nt.dem?.khong_phan_biet_duoc ?? 0}</b> chưa phân biệt được</span>
            <span><b>{nt.dem?.thieu_o ?? 0}</b> thiếu ô</span>
            <span><b>{nt.dem?.khong_khop_ca_hai ?? 0}</b> không khớp quy ước nào</span>
          </div>
          {!!nt.tong_lech && <p className="warn">
            Tổng thiếu so với quy ước đơn giá: <b>{Number(nt.tong_lech).toLocaleString("vi-VN")} đ</b>
          </p>}
          <p className="muted small">{nt.luu_y}</p>
          {ntRows.length > 0 && <table className="tbl">
            <thead><tr>
              <th>Chuyến</th><th>Dòng</th><th>Nhà cung cấp</th><th>Nhóm</th>
              <th>Gốc × tỷ giá</th><th>SL × hệ số</th><th>Đang ghi</th><th>Đáng lẽ</th><th>Thiếu</th>
            </tr></thead>
            <tbody>{ntRows.map((r: any, i: number) => (
              <tr key={i}>
                <td className="mono">{r.tour}</td>
                <td className="mono">#{r.dong}<div className="muted small">{r.mo_ta}</div></td>
                <td>{r.ncc}</td>
                <td>{r.nhom === "sai_bo_nhan" ? <Tag cls="red">{r.nhom_ten}</Tag> : <Tag cls="warn">{r.nhom_ten}</Tag>}
                  <div className="muted small">đơn giá đang mang: {r.don_gia_dang_mang === "dong_goc" ? "đồng gốc" : r.don_gia_dang_mang}</div></td>
                <td className="mono">{r.so_tien_goc?.toLocaleString("vi-VN")} {r.tien_te}
                  {r.ty_gia != null && <> × {Number(r.ty_gia).toLocaleString("vi-VN")}</>}</td>
                <td className="mono">{r.so_luong} × {r.he_so}<div className="muted small">{r.cach_tinh}</div></td>
                <td className="mono">{Number(r.actual || 0).toLocaleString("vi-VN")}</td>
                <td className="mono">{r.actual_dung != null ? Number(r.actual_dung).toLocaleString("vi-VN") : "—"}</td>
                <td className="mono" style={{ color: r.lech ? "var(--vtos-danger)" : undefined }}>
                  {r.lech ? Number(r.lech).toLocaleString("vi-VN") : "—"}</td>
              </tr>
            ))}</tbody>
          </table>}
          {nt.cham_tran && <p className="muted small">Đang hiện {ntRows.length} dòng đầu — còn nữa.</p>}
        </>)}
      </div>

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1150px; }
        .card { border: 1px solid var(--vtos-line); border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .so { display: flex; gap: 18px; flex-wrap: wrap; }
        .so .do { color: var(--vtos-danger); }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid var(--vtos-line); padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        .nut { white-space: nowrap; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid var(--vtos-sky);
                 background: var(--vtos-sky); color: var(--vtos-text-on-navy); cursor: pointer; margin-right: 6px; font-size: 13px; }
        button.ghost { background: var(--vtos-card); color: var(--vtos-text); border-color: var(--vtos-line); }
        button:disabled { opacity: .5; cursor: default; }
        .muted { color: var(--vtos-text-mute); }
        .small { font-size: 12px; }
        .warn { color: var(--vtos-warning); background: var(--vtos-warning-bg); padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() {
  return <Shell><RaSoatCotTien /></Shell>;
}
