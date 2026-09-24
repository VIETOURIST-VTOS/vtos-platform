"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Tài khoản trùng – gộp, sửa hồ sơ, và xoá tài khoản đã trống.
 *
 *  BA VIỆC, BA DANH SÁCH VAI, anh Tuấn chốt 24/9/2026:
 *      gộp  – chutich, tgd, hcns, cntt
 *      sửa  – hcns, chutich, tgd
 *      xoá  – hcns, chutich, tgd
 *  CNTT gộp được mà không sửa được, và đó là chủ ý: gộp là dọn dữ liệu, sửa họ tên là đổi hồ sơ
 *  nhân sự. Danh sách thật nằm ở máy chủ (api/v1/gop_tai_khoan.py); ba biến dưới đây chỉ quyết
 *  định hiện hay ẩn nút, không phải hàng rào.
 *
 *  BA BƯỚC CỦA GỘP KHÔNG RÚT GỌN ĐƯỢC: chọn giữ cái nào → xem trước bao nhiêu dòng sẽ chuyển →
 *  xác nhận. Gộp là việc MỘT CHIỀU: chuyển 290 booking sang nhầm người rồi thì không có nút tách.
 *
 *  XOÁ CÒN MỘT CHIỀU HƠN NỮA, nên nút của nó chỉ sáng khi máy chủ nói là sáng được — và khi nó
 *  tối, màn hình in ra CÂU GIẢI THÍCH chứ không để một nút tối câm. Một nút tối không nói vì sao
 *  là một nút người dùng bấm mãi rồi đi hỏi CNTT.
 *
 *  HAI CHỖ TỪNG LÀM MÀN HÌNH NÀY THÀNH NGÕ CỤT (anh Tuấn bắt được 25/9/2026, TC-85):
 *
 *    · Nút Gộp chỉ hiện khi tài khoản thừa CÒN ĐANG MỞ. Máy chủ chưa bao giờ đòi điều ấy –
 *      `services/gop_tai_khoan.py` không hề đọc `active`. Màn hình tự thêm vào. Hệ quả: một tài
 *      khoản đã bị khoá tay mà vẫn còn dòng dữ liệu thì không xoá được (còn dòng) và cũng không
 *      gộp được (không có nút) – kẹt cứng, không lối ra nào trên màn hình.
 *
 *    · Nút Gộp chỉ hiện khi MÁY ĐOÁN ĐƯỢC nên giữ cái nào, tức là đúng một tài khoản có mã nhân
 *      viên. Cả nhóm không ai có mã thì không dòng nào gộp được. Máy đoán không ra là chuyện của
 *      máy; người vẫn biết rõ giữ cái nào. Nay mỗi dòng có nút "Giữ cái này" để người tự chỉ.
 *
 *  Gợi ý của máy vẫn còn và vẫn được ưu tiên hiện, nhưng người chọn thì thắng gợi ý.
 *
 *  Màn hình cố ý KHÔNG có nút "gộp tất cả" hay "xoá tất cả". Mỗi dòng là một con người thật.
 */
function GopTaiKhoan() {
  const { user, toast } = useShell();
  const vai = user?.role || "";
  const canGop = ["chutich", "tgd", "hcns", "cntt"].includes(vai);
  const canSua = ["hcns", "chutich", "tgd"].includes(vai);
  const canXoa = ["hcns", "chutich", "tgd"].includes(vai);

  const [d, setD] = useState<any>(null);
  const [xt, setXt] = useState<any>(null);
  const [dang, setDang] = useState<{ giu: number; bo: number } | null>(null);
  const [sua, setSua] = useState<any>(null);      // tài khoản đang sửa
  const [xoa, setXoa] = useState<any>(null);      // kết quả co-the-xoa
  const [bm, setBm] = useState<any>(null);        // bia mộ
  const [moBm, setMoBm] = useState(false);
  // NGƯỜI CHỌN GIỮ CÁI NÀO, khi máy không đoán được. Khoá là id nhỏ nhất của nhóm, không phải họ
  // tên: hai người trùng tên là đúng cái mà màn hình này sinh ra để xử lý, lấy tên làm khoá là
  // gộp nhầm hai nhóm vào nhau.
  const [chonGiu, setChonGiu] = useState<Record<number, number>>({});

  // "BAM KHONG AN" (anh Tuan bao 25/9/2026). Ba khung Xem truoc / Sua / Xoa duoc ve SAU bang tai
  // khoan trung. Bang ay cao 8 dong, nen tren dien thoai mot cu bam mo khung o ngoai tam nhin:
  // man hinh dung im, va nguoi bam ket luan la nut hong. Khung VAN mo dung — cai thieu la nguoi
  // dung khong duoc dua toi cho no. Day la lan thu hai cung mot man hinh bi bao "bam khong an",
  // lan truoc la nut Gop that su khong lam gi; lan nay nut chay dung ma khong ai thay.
  //
  // KHONG doi cho ve khung len tren bang: khung mo ra tu MOT DONG cu the, doc no phai con thay
  // dong nao dang noi toi. Cuon toi khung la cach giu duoc ca hai.
  const khungRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!(xt || sua || xoa)) return;
    khungRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [xt, sua, xoa]);

  const load = useCallback(() => {
    api("/gop-tai-khoan/cap-trung").then(setD).catch(() => {});
    if (moBm) api("/gop-tai-khoan/bia-mo").then(setBm).catch(() => {});
  }, [moBm]);
  useEffect(() => { load(); }, [load]);

  const xem = async (giu: number, bo: number) => {
    setXt(null); setDang({ giu, bo }); setSua(null); setXoa(null);
    try { setXt(await api(`/gop-tai-khoan/xem-truoc?giu_id=${giu}&bo_id=${bo}`)); }
    catch (x) { toast(errMsg(x), true); setDang(null); }
  };

  const gop = async () => {
    if (!dang || !xt) return;
    const ly = prompt(`Gộp ${xt.bo.ho_ten} (${xt.bo.tai_khoan}) vào ${xt.giu.ho_ten} (${xt.giu.tai_khoan}).\n` +
                      `${xt.tong_dong_se_chuyen} dòng dữ liệu sẽ chuyển. Việc này KHÔNG hoàn lại được.\n\nLý do:`);
    if (!ly) return;
    try {
      const r = await api("/gop-tai-khoan", { method: "POST", json: { giu_id: dang.giu, bo_id: dang.bo, ly_do: ly, xac_nhan: true } });
      toast(r.message || "Đã gộp"); setXt(null); setDang(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const moSua = (t: any) => {
    setXt(null); setDang(null); setXoa(null);
    setSua({ id: t.id, tai_khoan: t.tai_khoan, full_name: t.ho_ten, staff_code: t.ma_nv || "", department: "" });
  };
  const luuSua = async () => {
    if (!sua) return;
    try {
      const r = await api(`/gop-tai-khoan/ho-so/${sua.id}`, { method: "PUT", json: {
        full_name: sua.full_name, staff_code: sua.staff_code, department: sua.department || null } });
      toast(r.message || "Đã sửa"); setSua(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const moXoa = async (t: any) => {
    setXt(null); setDang(null); setSua(null);
    try { setXoa(await api(`/gop-tai-khoan/co-the-xoa/${t.id}`)); }
    catch (x) { toast(errMsg(x), true); }
  };
  const xoaThat = async () => {
    if (!xoa?.xoa_duoc) return;
    const t = xoa.tai_khoan;
    const ly = prompt(`XOÁ VĨNH VIỄN tài khoản ${t.tai_khoan} (${t.ho_ten}).\n` +
                      `Không có nút hoàn lại. Hệ thống chỉ giữ một dòng bia mộ để nhật ký cũ còn tra ra người.\n\nLý do:`);
    if (!ly) return;
    try {
      const r = await api(`/gop-tai-khoan/${t.id}`, { method: "DELETE", json: { ly_do: ly, xac_nhan: true } });
      toast(r.message || "Đã xoá"); setXoa(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const soCot = 6 + (canGop || canSua || canXoa ? 1 : 0);

  return (<>
    <h1>Tài khoản trùng</h1>
    <p className="muted">Một người có hai tài khoản thì doanh số bị xẻ đôi, và không bảng nào báo lỗi.
      <b> Gộp</b> là chuyển hết dữ liệu sang một tài khoản rồi khoá cái thừa – không xoá, để nhật ký
      nghiệp vụ còn tra ra ai đã làm gì. <b>Xoá</b> chỉ mở cho tài khoản <b>đã khoá và còn 0 dòng dữ liệu</b>,
      tức là sau khi đã gộp.</p>

    <div className="panel wrap"><h2>Những người có nhiều hơn một tài khoản</h2>
      <table><thead><tr><th>Họ tên</th><th>Tài khoản</th><th>Vai</th><th>Mã NV</th><th className="num">Dòng dữ liệu</th><th>Trạng thái</th>{(canGop || canSua || canXoa) && <th></th>}</tr></thead>
        <tbody>{(d?.rows || []).map((n: any) => {
          const khoa = Math.min(...n.tai_khoan.map((x: any) => x.id));
          const giu = chonGiu[khoa] ?? n.goi_y_giu ?? null;     // người chọn thắng gợi ý của máy
          const tenGiu = n.tai_khoan.find((x: any) => x.id === giu)?.tai_khoan;
          return n.tai_khoan.map((t: any, i: number) => (
          <tr key={t.id}>
            {i === 0 && <td rowSpan={n.tai_khoan.length}><b>{n.ten}</b>
              <small style={{ display: "block", color: "var(--vtos-text-faint)" }}>{n.vi_sao}</small>
              {!giu && <small style={{ display: "block", color: "var(--vtos-text-faint)" }}>
                Bấm <b>Giữ cái này</b> ở dòng muốn giữ, rồi các dòng còn lại sẽ có nút gộp.</small>}</td>}
            <td className="mono">{t.tai_khoan}
              {t.id === n.goi_y_giu && <> <Tag cls="ok">nên giữ</Tag></>}
              {t.id === giu && t.id !== n.goi_y_giu && <> <Tag cls="ok">đang chọn giữ</Tag></>}</td>
            <td>{t.vai}</td>
            <td className="mono">{t.ma_nv || <span className="muted">–</span>}</td>
            <td className="num">{t.so_dong}</td>
            <td>{t.dang_mo ? <Tag cls="navy">Đang mở</Tag> : <Tag cls="red">Đã khoá</Tag>}</td>
            {(canGop || canSua || canXoa) && <td style={{ whiteSpace: "nowrap" }}>
              {canGop && t.id !== giu &&
                <button className="act grey" onClick={() => setChonGiu({ ...chonGiu, [khoa]: t.id })}>Giữ cái này</button>}
              {canGop && giu && t.id !== giu && <> <button className="act" onClick={() => xem(giu, t.id)}>Gộp vào {tenGiu}</button></>}
              {canSua && <> <button className="act grey" onClick={() => moSua(t)}>Sửa</button></>}
              {canXoa && <> <button className="act grey" onClick={() => moXoa(t)}>Xoá…</button></>}
            </td>}
          </tr>));
        }).flat()}
        {!(d?.rows || []).length && <tr><td colSpan={soCot}><Tag cls="ok">Không còn ai trùng tài khoản</Tag></td></tr>}
        </tbody></table>
      <p className="muted">{d?.ghi_chu}</p></div>

    <div ref={khungRef}>
    {/* ───────────── XEM TRƯỚC GỘP ───────────── */}
    {xt && <div className="panel"><h2>Xem trước – chưa ghi gì</h2>
      <p>Chuyển <b>{xt.tong_dong_se_chuyen}</b> dòng từ <b className="mono">{xt.bo.tai_khoan}</b> ({xt.bo.ho_ten})
        sang <b className="mono">{xt.giu.tai_khoan}</b> ({xt.giu.ho_ten}), rồi khoá tài khoản cũ.</p>
      {xt.canh_bao && <p><Tag cls="warn">{xt.canh_bao}</Tag></p>}
      <div className="wrap"><table><thead><tr><th>Bảng</th><th>Cột</th><th className="num">Số dòng</th></tr></thead>
        <tbody>{xt.chi_tiet.map((c: any) => <tr key={c.bang + c.cot}>
          <td className="mono">{c.bang}</td><td className="mono">{c.cot}</td><td className="num">{c.so_dong}</td></tr>)}
        {!xt.chi_tiet.length && <tr><td colSpan={3} className="muted">Tài khoản này không giữ dòng nào – gộp xong chỉ là khoá lại.</td></tr>}
        </tbody></table></div>
      <div style={{ marginTop: 12 }}>
        <button className="act orange" onClick={gop}>Xác nhận gộp</button>{" "}
        <button className="act" onClick={() => { setXt(null); setDang(null); }}>Thôi</button>
      </div>
      <p className="muted"><b>Việc này không hoàn lại được.</b> Không có nút tách ngược – muốn tách phải sửa tay từng bảng.
        Đọc kỹ bảng trên rồi hãy bấm.</p>
    </div>}

    {/* ───────────── SỬA HỒ SƠ ───────────── */}
    {sua && <div className="panel"><h2>Sửa hồ sơ – <span className="mono">{sua.tai_khoan}</span></h2>
      <div className="grid">
        <label>Họ tên<input value={sua.full_name} onChange={(e) => setSua({ ...sua, full_name: e.target.value })} /></label>
        <label>Mã nhân viên<input value={sua.staff_code} onChange={(e) => setSua({ ...sua, staff_code: e.target.value })} />
          <span className="muted">Mã nhân viên là thứ nhận ra người. Hai tài khoản cùng mã sẽ bị chặn – nếu đúng là một người thì dùng nút <b>Gộp</b>.</span></label>
        <label>Bộ phận<input value={sua.department} onChange={(e) => setSua({ ...sua, department: e.target.value })} placeholder="để trống là không đổi" /></label>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="act" disabled={!sua.full_name?.trim()} onClick={luuSua}>Lưu</button>{" "}
        <button className="act grey" onClick={() => setSua(null)}>Thôi</button>
      </div>
      <p className="muted"><b>Vai trò, mật khẩu và phân công đơn vị không sửa ở đây.</b> Vai trò và mật khẩu
        ở màn hình <b>Tài khoản &amp; phân quyền</b>; phân công đơn vị ở <b>Cơ cấu tổ chức Kinh doanh</b>.
        Hai lối vào cho cùng một việc là hai chỗ phải rào.</p>
    </div>}

    {/* ───────────── XOÁ ───────────── */}
    {xoa && <div className="panel"><h2>Xoá tài khoản – <span className="mono">{xoa.tai_khoan.tai_khoan}</span></h2>
      <p>{xoa.tai_khoan.ho_ten} · vai <b>{xoa.tai_khoan.vai}</b> ·
        {xoa.tai_khoan.dang_mo ? <> <Tag cls="navy">Đang mở</Tag></> : <> <Tag cls="red">Đã khoá</Tag></>}</p>

      {xoa.xoa_duoc
        ? <>
          <p><Tag cls="ok">Tài khoản này đã trống – xoá được.</Tag></p>
          <button className="act orange" onClick={xoaThat}>Xoá vĩnh viễn</button>{" "}
          <button className="act grey" onClick={() => setXoa(null)}>Thôi</button>
        </>
        : <>
          <p><Tag cls="warn">Chưa xoá được</Tag></p>
          <ul>{xoa.can_tro.map((c: string, i: number) => <li key={i}>{c}</li>)}</ul>
          {!!xoa.chi_tiet.length && <div className="wrap"><table>
            <thead><tr><th>Bảng</th><th>Cột</th><th className="num">Số dòng</th></tr></thead>
            <tbody>{xoa.chi_tiet.map((c: any) => <tr key={c.bang + c.cot}>
              <td className="mono">{c.bang}</td><td className="mono">{c.cot}</td><td className="num">{c.so_dong}</td></tr>)}
            </tbody></table></div>}
          <button className="act grey" onClick={() => setXoa(null)}>Đóng</button>
        </>}
      <p className="muted">{xoa.ghi_chu}</p>
    </div>}
    </div>

    {/* ───────────── BIA MỘ ───────────── */}
    <div className="panel">
      <button className="act grey" onClick={() => setMoBm(!moBm)}>
        {moBm ? "Ẩn" : "Xem"} tài khoản đã xoá</button>
      {moBm && <div style={{ marginTop: 12 }}>
        <div className="wrap"><table>
          <thead><tr><th>Tài khoản</th><th>Họ tên</th><th>Mã NV</th><th>Vai</th><th>Đã gộp vào</th><th>Lý do</th><th>Xoá bởi</th><th>Lúc</th></tr></thead>
          <tbody>{(bm?.rows || []).map((r: any) => <tr key={r.id}>
            <td className="mono">{r.tai_khoan}</td><td>{r.ho_ten}</td>
            <td className="mono">{r.ma_nv || <span className="muted">–</span>}</td>
            <td>{r.vai}</td>
            <td className="mono">{r.da_gop_vao || <span className="muted">–</span>}</td>
            <td>{r.ly_do}</td><td className="mono">{r.xoa_boi}</td><td>{r.xoa_luc}</td></tr>)}
          {!(bm?.rows || []).length && <tr><td colSpan={8} className="muted">Chưa xoá tài khoản nào.</td></tr>}
          </tbody></table></div>
        <p className="muted">{bm?.ghi_chu}</p>
      </div>}
    </div>
  </>);
}

export default function Page() { return <Shell><GopTaiKhoan /></Shell>; }
