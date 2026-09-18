"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, soTien, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import BangBonMoc from "@/components/BangBonMoc";

/** Dòng tiền – bảng bốn mốc, đường số dư từng ngày, và cửa Kế toán chốt số dư.
 *
 *  TRANG NÀY LÀ BẢN TẠM CỦA ROBOT A, và nói ra điều đó ở ngay đầu trang.
 *
 *  Theo lệnh giao việc 11/9/2026 thì web/** thuộc Robot B (TC-1 → TC-4). Nhưng bốn hàng rào của hệ
 *  thống – cửa nhập của mọi bảng, phạm vi vai trò, mục khai quyền phải có trang thật, và mọi mục
 *  khai quyền phải nằm trong menu – đều đòi màn hình CÓ THẬT trước khi phần máy chủ gộp lên nhánh
 *  chính được. Không có trang thì hoặc nhánh chính đỏ cho mọi làn, hoặc cả gói DT-1→DT-6 nằm ngoài
 *  kho mã tới 30/9. Chủ tịch chọn dựng trang tạm (11/9/2026).
 *
 *  Đây là trang MỚI, không sửa trang nào của ai, nên Robot B thay bằng bản theo TC-3 mà không phải
 *  gỡ việc của ai ra.
 *
 *  BA ĐIỀU TRANG NÀY KHÔNG LÀM, và chúng quan trọng hơn những gì nó làm:
 *
 *  1. KHÔNG hiện 0 thay cho "chưa có số". Máy chủ trả `null` kèm `vi_sao`; trang hiện đúng câu ấy.
 *     Một ô ghi "0 đ" trông như bảng chạy tốt và công ty hết tiền – người đọc TIN nó.
 *  2. KHÔNG cộng bốn cột. Chúng lũy kế từ cùng một ngày nên chồng lên nhau; cộng lại ra một con số
 *     lớn gấp mấy lần thực tế.
 *  3. KHÔNG tự dựng dòng đáy khi còn dòng thiếu nguồn. Cộng sáu dòng có số rồi bỏ qua năm dòng rỗng
 *     là ra con số ĐẸP HƠN thực tế, và đẹp hơn đúng ở chỗ người đọc cần chính xác nhất.
 */

const so = (v: any) =>
  v === null || v === undefined
    ? <span className="muted" title="Chưa có số – khác hẳn với bằng 0">—</span>
    : <>{vnd(v)}</>;

function DongTien() {
  const { toast } = useShell();
  const [dsPn, setDsPn] = useState<any[]>([]);
  const [pn, setPn] = useState<number | null>(null);
  const [bang, setBang] = useState<any>(null);
  const [ngay, setNgay] = useState<any>(null);
  const [mo, setMo] = useState(false);      // cửa chốt số dư

  // Danh mục đi qua CHÍNH phân hệ này (/dong-tien/meta), không gọi thẳng /companies hay
  // /bank-accounts. Gọi thẳng là nhân danh sách vai trò của phân hệ khác lên cho mọi ai mở được màn
  // hình này – bài học vòng 1 của Sự cố tour ngày 10/9/2026, và bộ kiểm P2 canh đúng chuyện đó.
  const [dsTk, setDsTk] = useState<any[]>([]);
  useEffect(() => {
    api("/dong-tien/meta").then((r) => {
      const ds = r.phap_nhan || [];
      setDsPn(ds); setDsTk(r.tai_khoan || []);
      if (ds.length && pn === null) setPn(ds[0].id);
    }).catch(() => {});
  }, []); // eslint-disable-line

  const load = useCallback(async () => {
    if (!pn) return;
    try {
      setBang(await api(`/dong-tien/bang/${pn}`));
      setNgay(await api(`/dong-tien/so-du-tung-ngay/${pn}`));
    } catch (e) { toast(errMsg(e), true); }
  }, [pn, toast]);
  useEffect(() => { load(); }, [load]);


  return (<>
    <h1>Dòng tiền</h1>
    <p className="muted">
      Bản tạm của phần máy chủ (DT-1→DT-6). Giao diện đầy đủ theo đề xuất TC-3 sẽ thay trang này.
      Ô để <b>trống</b> nghĩa là chưa có số — khác hẳn với bằng 0.
    </p>

    <div className="panel" style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
      <label>Pháp nhân
        <select value={pn ?? ""} onChange={(e) => setPn(Number(e.target.value))}>
          {dsPn.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.name}</option>)}
        </select>
      </label>
      <button className="act" onClick={() => setMo(true)}>Chốt số dư đã đối soát</button>
    </div>

    {bang && <>
      <div className="kpis">
        <div className="kpi"><b>{so(bang.tien_kha_dung_dau_ky)}</b><span>tiền khả dụng đầu kỳ</span></div>
        <div className="kpi"><b>{bang.doi_soat_den_ngay ? fmtD(bang.doi_soat_den_ngay) : "—"}</b>
          <span>đối soát đến ngày</span></div>
        <div className="kpi"><b>{so(bang.ghi_nho?.tien_thu_ho_khach)}</b><span>ghi nhớ – thu hộ khách</span></div>
        <div className="kpi"><b>{so(bang.ghi_nho?.ky_quy_giay_phep)}</b><span>ghi nhớ – ký quỹ giấy phép</span></div>
      </div>

      {bang.chua_co_nguon?.length ? (
        <div className="gate fail">
          <b>{bang.chua_co_nguon.length} dòng chưa có nguồn số — bảng KHÔNG dựng được số dư cuối kỳ</b>
          <ul style={{ margin: "4px 0 0 18px" }}>
            {bang.chua_co_nguon.map((t: string) => <li key={t}>{t}</li>)}
          </ul>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Cộng các dòng có số rồi bỏ qua các dòng rỗng sẽ ra con số đẹp hơn thực tế. Ô dòng tiền
            thuần và số dư cuối để trống cho tới khi các cửa nhập trên có thật (DT-7).
          </div>
        </div>) : null}

    </>}

    {/* ══════════════════════════════════════════════════════════════════════════════════════════
        TC-63 · BẢNG BỐN MỐC CŨ ĐÃ THAY BẰNG KHỐI TỪ MÀN HÌNH CHỦ TỊCH
        ══════════════════════════════════════════════════════════════════════════════════════════
        "em chuyển qua gộp với dòng tiền hoặc là ẩn khỏi màn hình chủ tịch"  — anh Tuấn 18/9/2026

        Trang này vốn tự dựng một bảng bốn mốc từ `/dong-tien/bang`. Khối chuyển sang dựng từ
        `/dong-tien/khung`, mà `khung_dong_tien.ghep()` nhận CHÍNH `bang` ấy làm đầu vào rồi bổ
        sung trạng thái nguồn số, số theo từng khoảng và dòng đáy — tức nó là tập CHA của bảng cũ.
        Vì vậy THAY chứ không đặt cạnh: để cả hai là chuyển cái trùng từ màn hình Chủ tịch sang
        đây, không phải bỏ nó đi.

        BA THỨ BẢNG CŨ KHÔNG CÓ mà khối mới mang sang: nút đổi kiểu xem (luỹ kế ↔ trong từng
        khoảng), nút Xuất Excel, và hình bốn mốc kèm câu đọc hộ.

        CÁC PHẦN KHÁC CỦA TRANG GIỮ NGUYÊN `/dong-tien/bang`: hàng bốn ô ở trên (tiền khả dụng đầu
        kỳ, ngày đối soát, hai khoản ghi nhớ) và ô cảnh báo "còn N dòng chưa có nguồn" — hai thứ ấy
        gói khung không trả về. */}
    <BangBonMoc pn={pn} />

    {ngay && <div className="panel wrap">
      <h2>Số dư theo từng ngày</h2>
      {ngay.muc_du_phong === null
        ? <p className="muted">{ngay.vi_sao_chua_co_nguong}</p>
        : <p className="muted">Mức dự phòng tối thiểu: <b>{vnd(ngay.muc_du_phong)}</b> (đủ hai chữ ký
          Tổng giám đốc và Chủ tịch).</p>}
      {!ngay.ngay?.length
        ? <p className="muted">{ngay.vi_sao_khong_ve_duoc}</p>
        : <>
          {ngay.ngay_dau_thieu_tien && <div className="gate fail">
            <b>Thiếu tiền giữa kỳ từ ngày {fmtD(ngay.ngay_dau_thieu_tien)}</b>
            <div>Mức thiếu lớn nhất so với dự phòng: <b>{vnd(ngay.muc_thieu_lon_nhat)}</b></div>
          </div>}
          <table><thead><tr><th>Ngày</th><th className="num">Biến động</th>
            <th className="num">Số dư</th><th className="num">Thiếu so với dự phòng</th></tr></thead>
            <tbody>{ngay.ngay.filter((d: any) => d.bien_dong !== 0 || d.thieu_so_voi_du_phong > 0)
              .map((d: any) => (
                <tr key={String(d.ngay)}>
                  <td>{fmtD(d.ngay)}</td>
                  <td className="num">{d.bien_dong ? vnd(d.bien_dong) : <span className="muted">—</span>}</td>
                  <td className="num">{vnd(d.so_du)}</td>
                  <td className="num">{d.thieu_so_voi_du_phong > 0
                    ? <Tag cls="red">{vnd(d.thieu_so_voi_du_phong)}</Tag>
                    : <span className="muted">—</span>}</td>
                </tr>))}</tbody></table>
          <p className="muted" style={{ fontSize: 12 }}>
            Chỉ hiện ngày có biến động hoặc ngày thiếu tiền — ngày đứng yên không thêm thông tin gì.
          </p>
        </>}
    </div>}

    {mo && <CuaChot pn={pn} dsTk={dsTk} dong={() => setMo(false)} xong={() => { setMo(false); load(); }} />}
  </>);
}

/** Cửa Kế toán chốt số dư đã đối soát (DT-2).
 *
 *  Máy chủ CHẶN nếu số chốt lệch với số cộng từ sao kê mà không ghi lý do. Trang không tự đoán lý do
 *  hộ và không ẩn ô ấy đi: người chốt là người biết vì sao lệch.
 */
function CuaChot({ pn, dsTk, dong, xong }:
  { pn: number | null; dsTk: any[]; dong: () => void; xong: () => void }) {
  const { toast } = useShell();
  const tk = dsTk;      // danh mục lấy từ /dong-tien/meta, không gọi thẳng phân hệ ngân hàng
  const [nguon, setNguon] = useState("ngan_hang");
  const [dang, setDang] = useState(false);

  const gui = async (e: React.FormEvent) => {
    e.preventDefault();
    const f = new FormData(e.target as HTMLFormElement);
    const d: any = Object.fromEntries(f.entries());
    setDang(true);
    try {
      const r = await api("/dong-tien/chot-so-du", { method: "POST", json: {
        company_id: pn, nguon,
        tai_khoan_id: nguon === "ngan_hang" ? Number(d.tai_khoan_id) : null,
        den_ngay: d.den_ngay, so_du: soTien(d.so_du),
        ly_do_lech: d.ly_do_lech || "", ghi_chu: d.ghi_chu || "" } });
      toast(r.message || "Đã chốt");
      xong();
    } catch (x) { toast(errMsg(x), true); }
    setDang(false);
  };

  return (
    <form onSubmit={gui} className="panel">
      <h2>Chốt số dư đã đối soát</h2>
      <p className="muted" style={{ fontSize: 13 }}>
        Đến hết ngày này, nguồn tiền này của pháp nhân này còn ngần này — và đây là tên người đã soát.
        Chốt lại cùng một ngày thì bản cũ được <b>giữ lại</b> và đánh dấu đã thay thế, không bị xoá.
      </p>
      <div className="grid">
        <div><label>Nguồn tiền</label>
          <select value={nguon} onChange={(e) => setNguon(e.target.value)}>
            <option value="ngan_hang">Tài khoản ngân hàng – đối soát với sao kê</option>
            <option value="tien_mat">Quỹ tiền mặt – đối soát với sổ quỹ đã kiểm kê</option>
          </select></div>
        {nguon === "ngan_hang" && <div><label>Tài khoản</label>
          <select name="tai_khoan_id" required>
            {tk.map((t) => <option key={t.id} value={t.id}>{t.code} – {t.bank_name}</option>)}
          </select></div>}
        <div><label>Đã đối soát đến hết ngày</label>
          <input name="den_ngay" type="date" required
            max={new Date().toISOString().slice(0, 10)} /></div>
        <div><label>Số dư (đ)</label><input name="so_du" required placeholder="5.000.000.000" /></div>
      </div>
      <label>Lý do lệch so với sao kê (chỉ điền khi có lệch)</label>
      <input name="ly_do_lech" placeholder="VD: SePay chưa đẩy giao dịch ngày 11/9" />
      <label>Ghi chú</label><input name="ghi_chu" />
      <p className="muted" style={{ fontSize: 12 }}>
        Không chốt được cho ngày chưa tới — đối soát là việc đã làm xong, không phải việc dự kiến.
      </p>
      <button className="act teal" type="submit" disabled={dang}>Chốt</button>{" "}
      <button type="button" className="act grey" onClick={dong}>Đóng</button>
    </form>
  );
}

export default function Page() { return <Shell><DongTien /></Shell>; }
