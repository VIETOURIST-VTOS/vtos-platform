"use client";
import { useEffect, useState, useCallback } from "react";
import { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Quy ước hạch toán – bảng quy ước máy đọc được, thay cho một tệp Excel và trí nhớ của kế toán.
 *
 *  Ba điều màn hình phải nói thẳng:
 *   - Máy chạy quy ước, người sửa quy ước chứ không sửa từng bút toán. Sửa một dòng ở đây là sửa
 *     cách hạch toán của mọi nghiệp vụ cùng loại từ ngày hiệu lực trở đi.
 *   - Không ai một mình đổi được một dòng định khoản: Kế toán trình, Chủ tịch và TGĐ ký.
 *   - Đơn có doanh thu mà chưa có giá vốn thì KHÔNG ghi doanh thu. Ghi vào là đơn đó lãi 100%
 *     và lãi gộp toàn công ty bị thổi lên mà không ai nhìn thấy. */
const TABS: [string, string][] = [
  ["quy_tac", "Bảng quy ước"], ["thieu_gia_von", "Đơn bị giữ vì thiếu giá vốn"], ["thu", "Định khoản thử"],
];

export default function HachToanPage() {
  const { user, toast } = useShell();
  const vai = user?.role || "";
  const laKeToan = ["chutich", "tgd", "ketoan"].includes(vai);
  const kyDuoc = ["chutich", "tgd"].includes(vai);
  const quetDuoc = ["chutich", "tgd", "ketoan", "cntt", "bks"].includes(vai);
  const [tab, setTab] = useState("quy_tac");
  const [d, setD] = useState<any>(null);
  const [q, setQ] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangChay, setDangChay] = useState("");
  const [trangThai, setTrangThai] = useState("cho");

  const load = useCallback(() => {
    api("/hach-toan").then(setD).catch((e) => setLoi(errMsg(e)));
  }, []);
  const loadQ = useCallback(() => {
    api(`/hach-toan/thieu-gia-von?trang_thai=${trangThai}`).then(setQ).catch((e) => setLoi(errMsg(e)));
  }, [trangThai]);
  useEffect(load, [load]);
  useEffect(loadQ, [loadQ]);

  const goi = async (path: string, json?: any) => {
    setDangChay(path);
    try {
      const r = await api<any>(`/hach-toan/${path}`, { method: "POST", json });
      toast(r.message || "Xong"); load(); loadQ();
    } catch (e) { toast(errMsg(e), true); } finally { setDangChay(""); }
  };

  const boQua = async (ma: string) => {
    const gt = window.prompt(`Cho qua đơn ${ma} mà KHÔNG bổ sung giá vốn.\nGhi rõ vì sao (ít nhất 20 ký tự) – lý do này vào nhật ký bất biến:`);
    if (!gt) return;
    await goi("thieu-gia-von/bo-qua", { ma_don: ma, giai_trinh: gt });
  };

  const nhomNguon: Record<string, any[]> = {};
  (d?.quy_tac || []).forEach((r: any) => { (nhomNguon[r.nguon] ||= []).push(r); });
  const choKy = (d?.quy_tac || []).filter((r: any) => r.status === "pending");

  return (
    <main>
      <h1>Quy ước hạch toán</h1>
      <p className="muted" style={{ marginTop: -6 }}>
        Máy chạy quy ước, người sửa quy ước – <b>không sửa từng bút toán</b>. Mỗi dòng dưới đây nói
        "gặp nghiệp vụ thế này thì ghi Nợ tài khoản này, Có tài khoản kia", có ngày hiệu lực và hai
        chữ ký như tham số chính sách. Căn cứ: Thông tư 99/2025/TT-BTC và bốn quyết định ngày 08/9/2026
        (công ty là bên chính; mọi đơn đều có doanh thu và giá vốn; mọi khách đi qua 131/511; số bảo
        hiểm lấy từ bảng lương).
      </p>

      {loi && <div className="gate fail">{loi}</div>}

      <div className="kpis" style={{ marginBottom: 12 }}>
        <div className="kpi"><b>{(d?.quy_tac || []).filter((r: any) => r.dang_dung).length}</b>
          <span>Quy ước đang chạy</span></div>
        <div className="kpi" style={{ borderColor: choKy.length ? "var(--amber)" : undefined }}>
          <b>{choKy.length}</b><span>Chờ đủ hai chữ ký</span></div>
        <div className="kpi" style={{ borderColor: q?.tong_so_don ? "var(--red)" : undefined }}>
          <b style={{ color: q?.tong_so_don ? "var(--red)" : undefined }}>{q?.tong_so_don ?? "–"}</b>
          <span>Đơn bị giữ vì thiếu giá vốn</span></div>
        <div className="kpi"><b>{vnd(q?.tong_doanh_thu)}</b>
          <span>Doanh thu chưa được ghi sổ</span></div>
      </div>

      <div className="tabs">
        {TABS.map(([k, t]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{t}</button>
        ))}
      </div>

      {/* ---------------- Bảng quy ước ---------------- */}
      {tab === "quy_tac" && (
        <>
          {kyDuoc && choKy.length > 0 && (
            <div className="gate fail" style={{ marginBottom: 10 }}>
              {choKy.length} quy ước đang chờ chữ ký. Quy ước chưa đủ hai chữ ký thì <b>chưa chạy</b> –
              nghiệp vụ tương ứng vẫn phải định khoản tay.
            </div>
          )}
          {Object.entries(d?.nguon || {}).map(([k, ten]: any) => (
            (nhomNguon[k] || []).length > 0 && (
              <div key={k} style={{ marginTop: 14 }}>
                <h3 style={{ marginBottom: 6 }}>{ten}</h3>
                <table>
                  <thead><tr>
                    <th>Mã</th><th>Khi nào áp dụng</th><th>Nợ</th><th>Có</th><th>Thuế</th>
                    <th>Đối tượng</th><th>Hiệu lực</th><th>Trạng thái</th>{kyDuoc && <th></th>}
                  </tr></thead>
                  <tbody>
                    {nhomNguon[k].map((r: any) => (
                      <tr key={r.id} style={{ opacity: r.dang_dung ? 1 : 0.55 }}>
                        <td><b>{r.ma}</b></td>
                        <td>{r.ten}
                          {r.can_cu && <div className="muted" style={{ fontSize: 12 }}>{r.can_cu}</div>}
                          {r.can_cong_trinh && <Tag>cần mã đơn</Tag>}
                        </td>
                        <td><b>{r.tk_no}</b></td>
                        <td><b>{r.tk_co}</b></td>
                        <td>{r.ty_le_thue ? `${r.tk_thue} · ${(r.ty_le_thue * 100).toFixed(0)}%` : "–"}</td>
                        <td>{d?.doi_tuong?.[r.doi_tuong] || "–"}</td>
                        <td>{r.effective_from}</td>
                        <td>
                          {r.status === "active" ? <Tag cls="ok">đang chạy</Tag>
                            : r.status === "pending" ? <Tag cls="warn">chờ ký
                              {r.signed_chutich ? " (CT ✓)" : ""}{r.signed_tgd ? " (TGĐ ✓)" : ""}</Tag>
                              : <Tag>{r.status}</Tag>}
                        </td>
                        {kyDuoc && <td>
                          {r.status === "pending" && r.proposed_by !== user?.username &&
                            !(vai === "chutich" ? r.signed_chutich : r.signed_tgd) && (
                            <button disabled={!!dangChay}
                              onClick={() => goi(`quy-tac/${r.id}/ky`)}>Ký</button>
                          )}
                        </td>}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ))}
        </>
      )}

      {/* ---------------- Hàng đợi thiếu giá vốn ---------------- */}
      {tab === "thieu_gia_von" && (
        <>
          <p className="muted">
            Mọi đơn đều có doanh thu và giá vốn – công ty thu hộ chi hộ và ăn phần chênh lệch. Vì vậy
            "giá vốn bằng 0" <b>không phải một bản chất nghiệp vụ khác</b>, nó là một ô chưa ai điền.
            Đơn nằm ở đây chưa được ghi doanh thu; để tới kỳ khóa sổ là doanh thu của tháng bị thiếu.
          </p>
          <div className="row" style={{ gap: 8, alignItems: "center", margin: "10px 0" }}>
            <select value={trangThai} onChange={(e) => setTrangThai(e.target.value)}>
              {Object.entries(q?.trang_thai || { cho: "Chờ Điều hành bổ sung" }).map(([k, v]: any) =>
                <option key={k} value={k}>{v}</option>)}
            </select>
            {quetDuoc && <button disabled={!!dangChay}
              onClick={() => goi("thieu-gia-von/quet")}>Quét lại toàn bộ đơn đã kết thúc</button>}
          </div>
          {q && Object.keys(q.theo_ly_do || {}).length > 0 && (
            <table style={{ marginBottom: 12 }}>
              <thead><tr><th>Vì sao bị giữ</th><th>Số đơn</th><th>Doanh thu</th></tr></thead>
              <tbody>
                {Object.entries(q.theo_ly_do).map(([k, v]: any) => (
                  <tr key={k}><td>{v.ten}</td><td>{v.so_don}</td><td>{vnd(v.doanh_thu)}</td></tr>
                ))}
              </tbody>
            </table>
          )}
          <table>
            <thead><tr>
              <th>Mã đơn</th><th>Kỳ</th><th>Tên</th><th>Doanh thu</th><th>Giá vốn</th>
              <th>Vì sao</th><th>Ai phải bổ sung</th>{laKeToan && <th></th>}
            </tr></thead>
            <tbody>
              {(q?.rows || []).map((r: any) => (
                <tr key={r.id}>
                  <td><a href={r.duong_dan}><b>{r.ma_don}</b></a></td>
                  <td>{r.ky}</td>
                  <td>{r.ten || <i className="muted">không đọc được là dịch vụ gì</i>}</td>
                  <td>{vnd(r.doanh_thu)}</td>
                  <td>{r.gia_von ? vnd(r.gia_von) : <b style={{ color: "var(--red)" }}>trống</b>}</td>
                  <td>{r.ly_do_ten}</td>
                  <td>{r.nguoi_phu_trach || <i className="muted">chưa có người điều hành</i>}
                    {r.giai_trinh && <div className="muted" style={{ fontSize: 12 }}>{r.giai_trinh}</div>}</td>
                  {laKeToan && <td>{r.trang_thai === "cho" &&
                    <button disabled={!!dangChay} onClick={() => boQua(r.ma_don)}>Cho qua có lý do</button>}</td>}
                </tr>
              ))}
              {q && (q.rows || []).length === 0 && (
                <tr><td colSpan={8} className="muted">Không có đơn nào ở trạng thái này.</td></tr>
              )}
            </tbody>
          </table>
        </>
      )}

      {tab === "thu" && <DinhKhoanThu nguon={d?.nguon || {}} />}
    </main>
  );
}

/** Định khoản thử: gõ một nghiệp vụ, xem máy sẽ ghi bút toán nào – KHÔNG ghi sổ.
 *  Đây là chỗ đối chiếu quy ước với kiểm toán trước khi chạy hàng loạt, chứ không phải chỗ ghi sổ. */
function DinhKhoanThu({ nguon }: { nguon: Record<string, string> }) {
  const [ng, setNg] = useState("quyet_toan");
  const [soTien, setSoTien] = useState("108000000");
  const [bc, setBc] = useState('{"da_ket_thuc": true, "co_gia_von": true, "ma": "KLE010826", "khach": "Công ty ABC", "ten": "Visa Hàn Quốc"}');
  const [ra, setRa] = useState<any>(null);
  const [loi, setLoi] = useState("");

  const chay = async () => {
    setLoi(""); setRa(null);
    let boi_canh: any;
    try { boi_canh = JSON.parse(bc); } catch { setLoi("Bối cảnh không phải JSON hợp lệ"); return; }
    try {
      setRa(await api("/hach-toan/xem-truoc", { method: "POST", json: { nguon: ng, so_tien: Number(soTien), boi_canh } }));
    } catch (e) { setLoi(errMsg(e)); }
  };

  return (
    <>
      <p className="muted">
        Gõ một nghiệp vụ, xem máy định khoản thế nào. Màn hình này <b>không ghi sổ</b> – nó để đối chiếu
        quy ước trước khi chạy hàng loạt, và để trả lời kiểm toán câu "vì sao dòng này vào tài khoản đó".
      </p>
      <div className="row" style={{ gap: 8, alignItems: "flex-end", flexWrap: "wrap", margin: "10px 0" }}>
        <label>Nguồn nghiệp vụ<br />
          <select value={ng} onChange={(e) => setNg(e.target.value)}>
            {Object.entries(nguon).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
        <label>Số tiền (đã gồm thuế)<br />
          <input value={soTien} onChange={(e) => setSoTien(e.target.value)} style={{ width: 160 }} /></label>
        <button onClick={chay}>Định khoản thử</button>
      </div>
      <label>Bối cảnh (JSON)<br />
        <textarea value={bc} onChange={(e) => setBc(e.target.value)} rows={3} style={{ width: "100%", fontFamily: "monospace" }} />
      </label>

      {loi && <div className="gate fail">{loi}</div>}
      {ra && !ra.khop && <div className="gate fail" style={{ marginTop: 10 }}>{ra.ly_do}</div>}
      {ra?.khop && (
        <div style={{ marginTop: 12 }}>
          <div className="gate pass">
            Quy ước <b>{ra.quy_tac}</b> – {ra.ten_quy_tac} (hiệu lực từ {ra.hieu_luc_tu})
            {ra.can_cu && <div className="muted" style={{ fontSize: 12 }}>{ra.can_cu}</div>}
          </div>
          <p style={{ margin: "8px 0 4px" }}><b>{ra.dien_giai}</b></p>
          <table>
            <thead><tr><th>Tài khoản</th><th>Nợ</th><th>Có</th><th>Đối tượng</th><th>Mã đơn</th></tr></thead>
            <tbody>
              {ra.lines.map((l: any, i: number) => (
                <tr key={i}>
                  <td><b>{l.account}</b></td>
                  <td>{l.debit ? vnd(l.debit) : ""}</td>
                  <td>{l.credit ? vnd(l.credit) : ""}</td>
                  <td>{l.partner || "–"}</td>
                  <td>{l.project_code || "–"}</td>
                </tr>
              ))}
              <tr><td><b>Cộng</b></td>
                <td><b>{vnd(ra.lines.reduce((s: number, l: any) => s + (l.debit || 0), 0))}</b></td>
                <td><b>{vnd(ra.lines.reduce((s: number, l: any) => s + (l.credit || 0), 0))}</b></td>
                <td colSpan={2}></td></tr>
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
