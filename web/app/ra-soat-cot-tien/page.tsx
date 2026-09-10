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

      <style jsx>{`
        .wrap { padding: 16px; max-width: 1150px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
        .so { display: flex; gap: 18px; flex-wrap: wrap; }
        .so .do { color: #b91c1c; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left;
                           vertical-align: top; }
        .mono { font-family: ui-monospace, monospace; font-size: 13px; }
        .nut { white-space: nowrap; }
        button { padding: 5px 10px; border-radius: 8px; border: 1px solid #0f172a;
                 background: #0f172a; color: #fff; cursor: pointer; margin-right: 6px; font-size: 13px; }
        button.ghost { background: #fff; color: #0f172a; border-color: #cbd5e1; }
        button:disabled { opacity: .5; cursor: default; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() {
  return <Shell><RaSoatCotTien /></Shell>;
}
