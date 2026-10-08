"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** SỔ TỶ GIÁ – nhân viên tự nhập tỷ giá của từng ngày, kèm chứng từ.
 *
 *  Chủ tịch chốt 16/9/2026: "tỷ giá để nhân viên tự nhập tại từng thời điểm; tạo form để nhân viên
 *  tự nhập tay và tải tệp/ảnh."
 *
 *  VÌ SAO MÀN HÌNH NÀY TỒN TẠI, ĐO CHỨ KHÔNG SUY
 *    · Tệp quyết toán UK: HAI tỷ giá GBP trong CÙNG MỘT TỆP – 36.000 ở sheet chiết tính, 35.944 ở
 *      sheet quyết toán. Trên giá land 692,34 GBP × 43 khách, 56 đồng chênh ấy là 1.667.155 đ.
 *    · 21 tệp quyết toán visa T1–T6/2026: tỷ giá nằm rải trong ô đầu bảng (CAD 19.000, USD 25.500,
 *      AUD 18.500) và không tệp nào ghi tỷ giá ấy lấy từ đâu, ngày nào.
 *
 *  MÀN HÌNH NÀY KHÔNG CHỌN HỘ. Tra cứu bày ra TẤT CẢ tỷ giá đã nhập cho một ngày; hai nguồn lệch
 *  nhau là hai sự thật, không phải lỗi dữ liệu. Người lập chứng từ chọn, máy không chọn. */

type Row = {
  id: number; tien_te: string; ngay: string; ty_gia: number; nguon: string;
  loai_gia: string; ten_loai_gia: string; ghi_chu: string; nguoi_nhap: string;
  luc: string | null; so_lan_sua: number; lich_su: string;
  lech_ngay?: number; canh_bao?: string;
};

const hnay = () => new Date().toISOString().slice(0, 10);

function TyGiaPage() {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const ghiDuoc = !user?.read_only &&
    ["chutich", "tgd", "ketoan", "tp_dh", "nv_dh", "cntt"].includes(role);

  const [dm, setDm] = useState<any>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [loi, setLoi] = useState("");
  const [locTien, setLocTien] = useState("");

  const [f, setF] = useState({ tien_te: "USD", ngay: hnay(), ty_gia: "", nguon: "", loai_gia: "", ghi_chu: "" });
  const [tra, setTra] = useState<any>(null);
  const [sua, setSua] = useState<{ id: number; ty_gia: string; ly_do: string } | null>(null);
  const [gan, setGan] = useState<number | null>(null);

  const load = useCallback(() => {
    const q = new URLSearchParams();
    if (locTien) q.set("tien_te", locTien);
    api<any>(`/ty-gia?${q}`).then((x) => { setRows(x.rows || []); setLoi(""); })
      .catch((e) => setLoi(errMsg(e)));
  }, [locTien]);

  useEffect(() => { api<any>("/ty-gia/danh-muc").then(setDm).catch(() => {}); }, []);
  // Bản ĐO chênh lệch tỷ giá (KY-3). Đặt ngay trên màn hình này chứ không dựng màn hình riêng: người
  // đọc thấy "ngày này sổ chưa có tỷ giá" xong thì việc tiếp theo của họ là nhập nó, mà form nhập ở
  // ngay dưới. Một màn hình thứ hai là một cú bấm nữa giữa chỗ biết và chỗ làm.
  const [cl, setCl] = useState<any>(null);
  useEffect(() => { api<any>("/ty-gia/chenh-lech").then(setCl).catch(() => setCl(null)); }, []);
  useEffect(load, [load]);

  /* Tra cứu chạy theo đồng tiền + ngày đang gõ trong form, để người nhập THẤY NGAY là ngày ấy đã có
   * ai nhập chưa – thay vì gõ xong mới ăn lỗi trùng. */
  useEffect(() => {
    if (!f.tien_te || f.tien_te === "VND" || !f.ngay) { setTra(null); return; }
    api<any>(`/ty-gia/tra-cuu?tien_te=${encodeURIComponent(f.tien_te)}&ngay=${f.ngay}`)
      .then(setTra).catch(() => setTra(null));
  }, [f.tien_te, f.ngay]);

  const them = async () => {
    try {
      const r = await api<any>("/ty-gia", {
        method: "POST",
        json: { ...f, ty_gia: Number(f.ty_gia) },
      });
      toast(r.message || "Đã ghi");
      setF({ ...f, ty_gia: "", ghi_chu: "" });
      load();
    } catch (e) { setLoi(errMsg(e)); }
  };

  const luuSua = async () => {
    if (!sua) return;
    try {
      const r = await api<any>(`/ty-gia/${sua.id}`, {
        method: "PUT", json: { ty_gia: Number(sua.ty_gia), ly_do_sua: sua.ly_do },
      });
      toast(r.message || "Đã sửa"); setSua(null); load();
    } catch (e) { setLoi(errMsg(e)); }
  };

  /* Chứng từ đi qua Ô ĐÍNH KÈM CHUNG (`<DinhKem>`), không tự viết một ô tải tệp riêng ở đây.
   * Ô chung giữ một bộ quy tắc cho cả hệ: giới hạn dung lượng nói bằng số trước khi người ta chọn
   * nhầm tệp 40 MB, tải lại đúng tệp cũ thì báo "đã có" chứ không tạo bản thứ hai, và gỡ tệp phải
   * ghi lý do. Viết riêng một ô ở đây là ba quy tắc ấy không áp cho chứng từ tỷ giá. */

  return (
    <main>
      <h1>Sổ tỷ giá</h1>
      <p className="muted">
        Tỷ giá dùng cho một khoản là tỷ giá <b>ngày chi thật</b> của khoản ấy. Sổ này là bản tham
        chiếu để điền sẵn vào form, <b>không</b> tự thay tỷ giá đã khai trên một khoản đã lập.
      </p>

      {loi && <p className="err">{loi}</p>}

      {cl && (cl.so_chuyen_hai_ty_gia > 0 || cl.so_cap_so_chua_co > 0 || cl.so_dong_lech_so > 0
              || cl.so_dong_thieu_ngay > 0) && (
        <div className="card">
          <h3>Chênh lệch tỷ giá — bản đo</h3>
          <p className="muted">{cl.ghi_chu}</p>
          <ul>
            {cl.so_chuyen_cung_ngay_khac_gia > 0 && (
              <li><b>{cl.so_chuyen_cung_ngay_khac_gia}</b> chuyến dùng <b>hai tỷ giá khác nhau cho
                cùng một ngày</b> — chỗ không giải thích được bằng &ldquo;khác ngày nên khác giá&rdquo;.</li>)}
            {cl.so_chuyen_hai_ty_gia > 0 && (
              <li><b>{cl.so_chuyen_hai_ty_gia}</b> chuyến dùng nhiều hơn một tỷ giá cho cùng một đồng tiền.</li>)}
            {cl.so_dong_lech_so > 0 && (
              <li><b>{cl.so_dong_lech_so}</b> dòng dùng tỷ giá <b>không khớp sổ</b> của đúng ngày ấy.</li>)}
            {cl.so_cap_so_chua_co > 0 && (
              <li><b>{cl.so_cap_so_chua_co}</b> cặp (đồng tiền, ngày) đang được dùng mà <b>sổ chưa
                có</b> — nhập ở form ngay dưới.</li>)}
            {cl.so_dong_thieu_ngay > 0 && (
              <li><b>{cl.so_dong_thieu_ngay}</b> dòng có tỷ giá mà <b>không có ngày</b> nên không
                đối chiếu được.</li>)}
          </ul>
          {(cl.hai_ty_gia_mot_chuyen || []).length > 0 && (
            <table>
              <thead><tr><th>Chuyến</th><th>Đồng tiền</th><th>Các tỷ giá</th><th>Chênh</th>
                <th>Cùng ngày khác giá</th><th>Số dòng</th><th>Tiền ước tính</th></tr></thead>
              <tbody>{cl.hai_ty_gia_mot_chuyen.slice(0, 20).map((x: any, i: number) => (
                <tr key={i}>
                  <td>{x.ma_tour || x.tour_id}</td><td>{x.tien_te}</td>
                  <td>{(x.ty_gia || []).map((t: any) => `${t.ty_gia} (${t.so_dong} dòng)`).join(" · ")}</td>
                  <td>{x.chenh_ty_gia}</td>
                  <td>{(x.cung_ngay_khac_gia || []).join(", ")}</td>
                  <td>{x.so_dong}</td>
                  <td>{x.uoc_tinh_thieu ? "— chưa đủ cột để ước tính" : x.tien_uoc_tinh?.toLocaleString("vi-VN")}</td>
                </tr>))}</tbody>
            </table>)}
          {(cl.so_chua_co || []).length > 0 && (
            <p className="muted">Sổ còn thiếu:{" "}
              {cl.so_chua_co.slice(0, 20).map((x: any) => `${x.tien_te} ${x.ngay}`).join(" · ")}</p>)}
        </div>
      )}

      {ghiDuoc && (
        <div className="card">
          <h3>Nhập tỷ giá</h3>
          <div className="grid">
            <div>
              <label>Đồng tiền</label>
              <input list="dsTien" value={f.tien_te}
                     onChange={(e) => setF({ ...f, tien_te: e.target.value.toUpperCase() })} />
              <datalist id="dsTien">
                {Object.entries(dm?.dong_tien || {}).map(([k, v]) => (
                  <option key={k} value={k}>{String(v)}</option>
                ))}
              </datalist>
              <span className="muted">Danh sách là gợi ý – đồng tiền lạ vẫn nhập được.</span>
            </div>
            <div>
              <label>Ngày của tỷ giá</label>
              <input type="date" value={f.ngay} max={hnay()}
                     onChange={(e) => setF({ ...f, ngay: e.target.value })} />
            </div>
            <div>
              <label>1 {f.tien_te || "?"} = ? đồng</label>
              <input type="number" step="0.000001" value={f.ty_gia}
                     onChange={(e) => setF({ ...f, ty_gia: e.target.value })} />
            </div>
            <div>
              <label>Nguồn</label>
              <input value={f.nguon} placeholder="Vietcombank bán ra / hợp đồng đối tác / sao kê"
                     onChange={(e) => setF({ ...f, nguon: e.target.value })} />
            </div>
            <div>
              <label>Loại giá</label>
              <select value={f.loai_gia} onChange={(e) => setF({ ...f, loai_gia: e.target.value })}>
                {Object.entries(dm?.loai_gia || { "": "Không ghi rõ" }).map(([k, v]) => (
                  <option key={k} value={k}>{String(v)}</option>
                ))}
              </select>
            </div>
          </div>
          <label>Ghi chú</label>
          <input value={f.ghi_chu} onChange={(e) => setF({ ...f, ghi_chu: e.target.value })} />

          {/* Nói trước khi người ta gõ xong, chứ không để họ ăn lỗi trùng sau khi bấm. */}
          {tra?.dung_ngay?.length > 0 && (
            <p className={tra.nhieu_nguon ? "err" : "muted"}>
              Ngày này đã có {tra.dung_ngay.length} tỷ giá {tra.tien_te}:{" "}
              {tra.dung_ngay.map((x: Row) => `${x.ty_gia.toLocaleString("vi-VN")} (${x.nguon || "không ghi nguồn"})`).join(" · ")}
              {tra.nhieu_nguon && <> — <b>hai nguồn đang lệch nhau</b>, người lập chứng từ phải chọn.</>}
            </p>
          )}
          {tra?.gan_nhat && (
            <p className="warn">{tra.gan_nhat.canh_bao} Số: {tra.gan_nhat.ty_gia.toLocaleString("vi-VN")}</p>
          )}

          <button className="act" disabled={!f.ty_gia || !f.tien_te} onClick={them}>Ghi tỷ giá</button>
          <span className="muted" style={{ marginLeft: 8 }}>
            Ghi xong thì đính kèm ảnh bảng tỷ giá ngân hàng hoặc sao kê vào đúng dòng ở bảng dưới.
          </span>
        </div>
      )}

      <div className="card">
        <h3>Sổ</h3>
        <label>Lọc theo đồng tiền</label>
        <input value={locTien} placeholder="để trống = tất cả"
               onChange={(e) => setLocTien(e.target.value.toUpperCase())} />
        <table>
          <thead>
            <tr>
              <th>Ngày</th><th>Đồng tiền</th><th style={{ textAlign: "right" }}>Tỷ giá</th>
              <th>Nguồn</th><th>Loại giá</th><th>Người nhập</th><th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.ngay}</td>
                <td><b>{r.tien_te}</b></td>
                <td style={{ textAlign: "right" }}>{r.ty_gia.toLocaleString("vi-VN")}</td>
                <td>{r.nguon || <span className="muted">không ghi nguồn</span>}</td>
                <td>{r.ten_loai_gia}</td>
                <td>
                  {r.nguoi_nhap} <span className="muted">{fmtDT(r.luc)}</span>
                  {r.so_lan_sua > 0 && <Tag cls="warn">đã sửa {r.so_lan_sua} lần</Tag>}
                </td>
                <td>
                  <button onClick={() => setGan(gan === r.id ? null : r.id)}>
                    {gan === r.id ? "Đóng chứng từ" : "Chứng từ"}
                  </button>
                  {ghiDuoc && (
                    <button onClick={() => setSua({ id: r.id, ty_gia: String(r.ty_gia), ly_do: "" })}>
                      Sửa
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} className="muted">Chưa có dòng nào.</td></tr>
            )}
          </tbody>
        </table>

        {/* Ô đính kèm của ĐÚNG dòng đang mở. Đặt ngay dưới bảng chứ không bắt người dùng sang
          * màn hình "Tệp & hình ảnh" rồi gõ lại mã hồ sơ – việc ấy sẽ không ai làm, và ảnh bảng tỷ
          * giá ở lại trong điện thoại. */}
        {gan !== null && (
          <DinhKem doiTuong="ty_gia" doiTuongId={gan} loai="chung_tu" chiXem={!ghiDuoc}
                   tieuDe={`Chứng từ tỷ giá #${gan} – ảnh bảng niêm yết, sao kê, hoặc trang hợp đồng`} />
        )}

        {/* Lịch sử sửa hiện ngay dưới bảng, không giấu sau một nút: số cũ là thứ người đối chiếu
          * cần thấy, và giấu nó đi thì việc giữ lại cũng bằng thừa. */}
        {rows.filter((r) => r.lich_su).map((r) => (
          <div key={`ls${r.id}`} className="muted" style={{ fontSize: 12 }}>
            <b>#{r.id} {r.tien_te} {r.ngay}</b>
            {r.lich_su.split("\n").map((d, i) => <div key={i}>· {d}</div>)}
          </div>
        ))}
      </div>

      {sua && (
        <div className="card">
          <h3>Sửa tỷ giá #{sua.id}</h3>
          <p className="muted">
            Tỷ giá là con số <b>nhân vào tiền</b>. Sửa 25.500 thành 25.620 trên một khoản 40.000 USD
            là 4,8 triệu đổi chủ – nên phải nói vì sao, và số cũ vẫn được giữ lại.
          </p>
          <label>Tỷ giá mới</label>
          <input type="number" step="0.000001" value={sua.ty_gia}
                 onChange={(e) => setSua({ ...sua, ty_gia: e.target.value })} />
          <label>Lý do sửa (tối thiểu 10 ký tự)</label>
          <input value={sua.ly_do} onChange={(e) => setSua({ ...sua, ly_do: e.target.value })}
                 placeholder="Ngân hàng đính chính bảng niêm yết ngày…" />
          <button className="act" disabled={sua.ly_do.trim().length < 10} onClick={luuSua}>Lưu</button>
          <button onClick={() => setSua(null)}>Thôi</button>
        </div>
      )}
    </main>
  );
}

// Bọc trong Shell: không bọc thì trang chạy NGOÀI khung – mất thanh điều hướng, và tệ hơn là
// useShell() trả user rỗng nên mọi nút theo vai trò lặng lẽ biến mất mà không báo lỗi gì.
export default function Page() { return <Shell><TyGiaPage /></Shell>; }
