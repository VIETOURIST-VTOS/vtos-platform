"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
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
  ["danh_muc", "Danh mục"],
];

function HachToanPage() {
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
  // Trình quy ước mới. KHÔNG có nút "sửa tại chỗ": một dòng định khoản đang chạy mà sửa được thì
  // bút toán tháng trước và bút toán tháng này cùng mang một mã nhưng khác nội dung, và kiểm toán
  // không dựng lại được. Sửa ở đây nghĩa là TRÌNH MỘT BẢN MỚI có ngày hiệu lực sau – bản cũ ở lại
  // nguyên vẹn để giải thích những gì đã ghi bằng nó.
  const [bieu, setBieu] = useState<any>(null);

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

  const RONG = { ma: "", ten: "", nguon: "", tk_no: "", tk_co: "", tk_thue: "", ben_thue: "",
                 ty_le_thue: 0, doi_tuong: "", can_cong_trinh: false, dien_giai: "", uu_tien: 100,
                 can_cu: "", ghi_chu: "", effective_from: "", dieu_kien_json: "{}" };

  const moBieu = (r?: any) => setBieu(r
    ? { ...RONG, ...r, effective_from: "", ty_le_thue: r.ty_le_thue || 0,
        dieu_kien_json: JSON.stringify(r.dieu_kien || {}, null, 0) }
    : { ...RONG });

  const trinh = async () => {
    let dieu_kien: any = {};
    try { dieu_kien = JSON.parse(bieu.dieu_kien_json || "{}"); }
    catch { toast("Điều kiện không đúng dạng JSON", true); return; }
    if (!bieu.ma.trim() || !bieu.tk_no.trim() || !bieu.tk_co.trim() || !bieu.effective_from) {
      toast("Thiếu mã, tài khoản Nợ/Có, hoặc ngày hiệu lực", true); return;
    }
    setDangChay("quy-tac");
    try {
      const r = await api<any>("/hach-toan/quy-tac", { method: "POST", json: {
        ma: bieu.ma.trim(), ten: bieu.ten, nguon: bieu.nguon, dieu_kien,
        tk_no: bieu.tk_no.trim(), tk_co: bieu.tk_co.trim(), tk_thue: bieu.tk_thue.trim(),
        ben_thue: bieu.ben_thue, ty_le_thue: Number(bieu.ty_le_thue) || 0,
        doi_tuong: bieu.doi_tuong, can_cong_trinh: !!bieu.can_cong_trinh,
        dien_giai: bieu.dien_giai, uu_tien: Number(bieu.uu_tien) || 100,
        can_cu: bieu.can_cu, ghi_chu: bieu.ghi_chu, effective_from: bieu.effective_from } });
      toast(r.message || "Đã trình"); setBieu(null); load();
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
          {laKeToan && (
            <div style={{ margin: "10px 0" }}>
              <button onClick={() => moBieu()} disabled={!!dangChay}>Trình quy ước mới</button>
              {bieu && <button className="" style={{ marginLeft: 8 }} onClick={() => setBieu(null)}>Đóng biểu</button>}
            </div>
          )}

          {bieu && (
            <div className="gate" style={{ marginBottom: 12 }}>
              <h3 style={{ marginTop: 0 }}>Trình một bản quy ước</h3>
              <p className="muted" style={{ fontSize: 13 }}>
                Trình xong <b>chưa chạy</b>: phải đủ chữ ký Chủ tịch và TGĐ. Trùng mã với một quy ước
                đang chạy là <b>bình thường</b> — đó chính là cách sửa: bản mới có ngày hiệu lực sau,
                bản cũ ở lại nguyên vẹn để giải thích những bút toán đã ghi bằng nó.
              </p>
              <div className="grid2">
                <label>Mã <input value={bieu.ma} onChange={(e) => setBieu({ ...bieu, ma: e.target.value })}
                                 placeholder="TOUR_DOANH_THU" /></label>
                <label>Tên / khi nào áp dụng
                  <input value={bieu.ten} onChange={(e) => setBieu({ ...bieu, ten: e.target.value })} /></label>
                <label>Nguồn nghiệp vụ
                  <select value={bieu.nguon} onChange={(e) => setBieu({ ...bieu, nguon: e.target.value })}>
                    <option value="">— chọn —</option>
                    {Object.entries(d?.nguon || {}).map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}
                  </select></label>
                <label>Tài khoản Nợ
                  <input value={bieu.tk_no} onChange={(e) => setBieu({ ...bieu, tk_no: e.target.value })} /></label>
                <label>Tài khoản Có
                  <input value={bieu.tk_co} onChange={(e) => setBieu({ ...bieu, tk_co: e.target.value })} /></label>
                <label>Tài khoản thuế
                  <input value={bieu.tk_thue} onChange={(e) => setBieu({ ...bieu, tk_thue: e.target.value })}
                         placeholder="để trống nếu không tách thuế" /></label>
                <label>Thuế ghi bên
                  <select value={bieu.ben_thue} onChange={(e) => setBieu({ ...bieu, ben_thue: e.target.value })}>
                    <option value="">—</option><option value="no">Nợ</option><option value="co">Có</option>
                  </select></label>
                <label>Tỷ lệ thuế (0.08 = 8%)
                  <input type="number" step="0.01" value={bieu.ty_le_thue}
                         onChange={(e) => setBieu({ ...bieu, ty_le_thue: e.target.value })} /></label>
                <label>Đối tượng
                  <select value={bieu.doi_tuong} onChange={(e) => setBieu({ ...bieu, doi_tuong: e.target.value })}>
                    <option value="">—</option>
                    {Object.entries(d?.doi_tuong || {}).map(([k, t]: any) => <option key={k} value={k}>{t}</option>)}
                  </select></label>
                <label>Thứ tự xét (số nhỏ xét trước)
                  <input type="number" value={bieu.uu_tien}
                         onChange={(e) => setBieu({ ...bieu, uu_tien: e.target.value })} /></label>
                <label>Ngày hiệu lực
                  <input type="date" value={bieu.effective_from}
                         onChange={(e) => setBieu({ ...bieu, effective_from: e.target.value })} /></label>
                <label>Căn cứ (điều khoản TT99 / quyết định nội bộ)
                  <input value={bieu.can_cu} onChange={(e) => setBieu({ ...bieu, can_cu: e.target.value })} /></label>
                <label>Mẫu diễn giải
                  <input value={bieu.dien_giai} onChange={(e) => setBieu({ ...bieu, dien_giai: e.target.value })}
                         placeholder="Doanh thu tour {ma} – {khach}" /></label>
                <label>Điều kiện (JSON)
                  <input value={bieu.dieu_kien_json}
                         onChange={(e) => setBieu({ ...bieu, dieu_kien_json: e.target.value })}
                         placeholder='{"ma_bat_dau": ["KLE"]}' /></label>
              </div>
              <label style={{ marginTop: 8 }}>
                <input type="checkbox" style={{ width: "auto", marginRight: 6 }}
                       checked={!!bieu.can_cong_trinh}
                       onChange={(e) => setBieu({ ...bieu, can_cong_trinh: e.target.checked })} />
                Bắt buộc có mã đơn / mã tour thì mới ghi được
              </label>
              <label>Ghi chú
                <textarea value={bieu.ghi_chu} rows={2}
                          onChange={(e) => setBieu({ ...bieu, ghi_chu: e.target.value })} /></label>
              <div style={{ marginTop: 10 }}>
                <button disabled={!!dangChay} onClick={trinh}>
                  {dangChay === "quy-tac" ? "Đang trình…" : "Trình – chờ hai chữ ký"}</button>
              </div>
            </div>
          )}

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
                    <th>Đối tượng</th><th>Hiệu lực</th><th>Trạng thái</th>{(kyDuoc || laKeToan) && <th></th>}
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
                        {(kyDuoc || laKeToan) && <td>
                          {kyDuoc && r.status === "pending" && r.proposed_by !== user?.username &&
                            !(vai === "chutich" ? r.signed_chutich : r.signed_tgd) && (
                            <button disabled={!!dangChay}
                              onClick={() => goi(`quy-tac/${r.id}/ky`)}>Ký</button>
                          )}
                          {laKeToan && r.status === "active" && (
                            <button disabled={!!dangChay} onClick={() => moBieu(r)}>Trình bản mới</button>
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
      {tab === "danh_muc" && <DanhMuc />}
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



// ── ĐỢT R3b 17/10/2026 — DANH MỤC KHOẢN MỤC & BỘ PHẬN ──────────────────────────────────────────
//
// VÌ SAO CẢ HAI NẰM CHUNG MỘT THẺ. Đợt R2 dựng danh mục khoản mục với đầy đủ cửa máy chủ nhưng
// KHÔNG dựng màn hình — đo được 17/10/2026: `/api/v1/hach-toan/khoan-muc` có, mà trang này không
// có một chữ "khoản mục" nào. Hệ quả: Kế toán muốn thêm một mã phải nhờ IT. Đó đúng là kiểu hỏng
// kho mã đã khai và đặt hàng rào để bắt — "cửa có tồn tại nhưng người phải dùng nó không với tới"
// — và nó lọt vì hàng rào chỉ quét các mục CÓ TRONG MENU, còn danh mục thì không có mục riêng.
// Đợt này trả nợ ấy cùng lúc với dựng danh mục bộ phận: hai chiều phân tích của cùng một bộ sổ,
// người mở màn để sửa một cái thường sửa luôn cái kia.
function DanhMuc() {
  const { user, toast } = useShell();
  const vai = user?.role || "";
  const laKeToan = ["chutich", "tgd", "ketoan"].includes(vai);     // sửa khoản mục
  const laHcns = ["chutich", "tgd", "hcns"].includes(vai);          // sửa bộ phận — cơ cấu là việc HCNS
  const [km, setKm] = useState<any>(null);
  const [bp, setBp] = useState<any>(null);
  const [la, setLa] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [ban, setBan] = useState("");
  const [bpMoi, setBpMoi] = useState({ ma: "", ten: "" });
  const [chon, setChon] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api("/hach-toan/khoan-muc?ca_ngung=true").then(setKm).catch((e) => setLoi(errMsg(e)));
    api("/hach-toan/bo-phan?ca_ngung=true").then(setBp).catch((e) => setLoi(errMsg(e)));
    api("/hach-toan/bo-phan/chua-gan").then(setLa).catch(() => setLa(null));
  }, []);
  useEffect(load, [load]);

  const goi = async (path: string, json?: any, ph: string = "POST") => {
    setBan(path); setLoi("");
    try {
      const ra: any = await api(path, json ? { method: ph, json } : { method: ph });
      if (ra?.message) toast(ra.message);
      load();
    } catch (e) { setLoi(errMsg(e)); } finally { setBan(""); }
  };

  return (
    <>
      {loi && <div className="loi" style={{ margin: "10px 0" }}>{loi}</div>}

      {/* ---- Khoản mục chi phí ---- */}
      <h3 style={{ margin: "14px 0 6px" }}>Khoản mục chi phí</h3>
      <p className="phu" style={{ marginTop: 0 }}>
        Chiều phân tích trả lời câu “một tour lỗ thì lỗ ở đâu”. Mã không đổi được — ngừng dùng rồi
        thêm dòng mới, vì bút toán cũ đang trỏ vào mã này và kỳ đã khoá thì không sửa lại được.
      </p>
      {laKeToan && (
        <div style={{ margin: "8px 0" }}>
          <button onClick={() => goi("/hach-toan/khoan-muc/nap-mac-dinh")} disabled={!!ban}>
            Nạp khuôn ngành tour
          </button>
        </div>
      )}
      <table>
        <thead><tr><th>Mã</th><th>Tên</th><th>Nhóm</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>
          {(km?.rows || []).map((r: any) => (
            <tr key={r.id}>
              <td><code>{r.ma}</code></td><td>{r.ten}</td>
              <td className="phu">{km?.nhom?.[r.nhom] || r.nhom}</td>
              <td><Tag cls={r.dung ? "ok" : "warn"}>{r.dung ? "đang dùng" : "ngừng dùng"}</Tag></td>
              <td>{laKeToan && (
                <button className="nho" disabled={!!ban}
                  onClick={() => goi(`/hach-toan/khoan-muc/${r.id}`, { dung: !r.dung }, "PATCH")}>
                  {r.dung ? "Ngừng dùng" : "Dùng lại"}
                </button>)}</td>
            </tr>
          ))}
          {!km?.rows?.length && <tr><td colSpan={5} className="phu">Chưa có khoản mục nào.</td></tr>}
        </tbody>
      </table>

      {/* ---- Bộ phận ---- */}
      <h3 style={{ margin: "22px 0 6px" }}>Bộ phận</h3>
      <p className="phu" style={{ marginTop: 0 }}>
        Cơ cấu phòng ban do Hành chính – Nhân sự giữ, không phải Kế toán.
      </p>
      {laHcns && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "flex-end", margin: "8px 0" }}>
          <button onClick={() => goi("/hach-toan/bo-phan/nap-mac-dinh")} disabled={!!ban}>
            Nạp khuôn cơ cấu
          </button>
          <input placeholder="Mã (BP_…)" value={bpMoi.ma}
            onChange={(e) => setBpMoi({ ...bpMoi, ma: e.target.value })} style={{ width: 130 }} />
          <input placeholder="Tên bộ phận" value={bpMoi.ten}
            onChange={(e) => setBpMoi({ ...bpMoi, ten: e.target.value })} style={{ width: 220 }} />
          <button disabled={!!ban || !bpMoi.ma.trim() || !bpMoi.ten.trim()}
            onClick={async () => { await goi("/hach-toan/bo-phan", { ...bpMoi }); setBpMoi({ ma: "", ten: "" }); }}>
            Thêm bộ phận
          </button>
        </div>
      )}
      <table>
        <thead><tr><th>Mã</th><th>Tên</th><th>Bút danh (chữ cũ trong sổ)</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>
          {(bp?.rows || []).map((r: any) => (
            <tr key={r.id}>
              <td><code>{r.ma}</code></td><td>{r.ten}</td>
              <td className="phu">
                {r.but_danh?.length ? r.but_danh.map((x: string) => (
                  <span key={x} style={{ marginRight: 6 }}>
                    <code>{x}</code>
                    {laHcns && <button className="nho" style={{ marginLeft: 3 }} disabled={!!ban}
                      onClick={() => goi(`/hach-toan/bo-phan/${r.ma}/but-danh/${encodeURIComponent(x)}`, undefined, "DELETE")}>
                      gỡ</button>}
                  </span>
                )) : "–"}
              </td>
              <td><Tag cls={r.dung ? "ok" : "warn"}>{r.dung ? "đang dùng" : "ngừng dùng"}</Tag></td>
              <td>{laHcns && (
                <button className="nho" disabled={!!ban}
                  onClick={() => goi(`/hach-toan/bo-phan/${r.id}`, { dung: !r.dung }, "PATCH")}>
                  {r.dung ? "Ngừng dùng" : "Dùng lại"}
                </button>)}</td>
            </tr>
          ))}
          {!bp?.rows?.length && <tr><td colSpan={5} className="phu">Chưa có bộ phận nào — bấm “Nạp khuôn cơ cấu”.</td></tr>}
        </tbody>
      </table>

      {/* ---- Gộp chữ cũ ---- */}
      <h3 style={{ margin: "22px 0 6px" }}>Chữ cũ trong sổ chưa ai nhận</h3>
      <p className="phu" style={{ marginTop: 0 }}>
        Máy chỉ LIỆT KÊ và đếm; người chọn mã. Nhận một chữ về KHÔNG sửa một dòng sổ nào — chữ cũ
        thành bút danh, sổ giữ nguyên chữ nó đã ghi. Gán nhầm thì gỡ bút danh, không phải dựng lại sổ.
      </p>
      {la?.de_trong ? (
        <p className="phu">
          Còn <b>{la.de_trong}</b> dòng sổ <b>để trống</b> bộ phận. Để trống nghĩa là chưa ai khai —
          không gán hộ về một bộ phận nào, vì gán đại cho đủ là bịa ra một con số rồi in lên báo cáo.
        </p>
      ) : null}
      <table>
        <thead><tr><th>Chữ trong sổ</th><th>Số dòng</th><th>Nhận về bộ phận</th></tr></thead>
        <tbody>
          {(la?.chua_gan || []).map((x: any) => (
            <tr key={x.chu}>
              <td><code>{x.chu}</code></td><td>{x.so_dong}</td>
              <td>
                <select value={chon[x.chu] || ""} disabled={!laHcns || !!ban}
                  onChange={(e) => setChon({ ...chon, [x.chu]: e.target.value })}>
                  <option value="">— chưa chọn —</option>
                  {(bp?.rows || []).filter((r: any) => r.dung).map((r: any) => (
                    <option key={r.ma} value={r.ma}>{r.ma} — {r.ten}</option>
                  ))}
                </select>
                {laHcns && (
                  <button className="nho" style={{ marginLeft: 6 }}
                    disabled={!!ban || !chon[x.chu]}
                    onClick={() => goi("/hach-toan/bo-phan/gan", { chu: x.chu, ma: chon[x.chu] })}>
                    Nhận
                  </button>
                )}
              </td>
            </tr>
          ))}
          {!la?.chua_gan?.length && (
            <tr><td colSpan={3} className="phu">Không còn chữ nào chưa nhận.</td></tr>
          )}
        </tbody>
      </table>
    </>
  );
}


// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><HachToanPage /></Shell>; }
