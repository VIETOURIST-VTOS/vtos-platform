"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** HS-6 · Hộp Sửa tài khoản — Chủ tịch duyệt bản vẽ 15/10/2026, dựng 16/10/2026.
 *
 *  VÌ SAO GOM VỀ MỘT HỘP. Trước vòng này, sáu việc trên cùng một con người nằm rải ba màn hình:
 *  sửa mã NV · họ tên · phòng và gán pháp nhân ở màn Tài khoản; ghi nhận nghỉ việc ở màn Nhân sự;
 *  xoá bản ghi ở màn Gộp tài khoản. Người làm phải nhớ việc nào ở đâu, và nhớ sai thì hoặc không
 *  tìm thấy, hoặc tìm thấy nút gần giống rồi bấm nhầm.
 *
 *  HỘP NÀY KHÔNG VIẾT THÊM MỘT CỬA MÁY CHỦ NÀO. Sáu cửa dưới đây đều đã có từ trước; vòng này chỉ
 *  nối màn hình vào đúng cửa và bày ra theo đúng thứ tự người ta làm việc.
 *
 *  BỐN DANH SÁCH VAI, KHÔNG PHẢI MỘT — và đây là chỗ dễ sai nhất của tệp này. Sáu cửa ấy có bốn
 *  bộ vai khác nhau, vì chúng là bốn mức hệ quả khác nhau. Danh sách dưới đây là BẢN SAO của bộ
 *  vai khai ở máy chủ, nên `test_hs6` đọc chính tệp này và so với mã Python: lệch một tên là đỏ.
 *  Bản sao mà không ai canh thì sớm muộn lệch, và lệch ở đây hiện ra dưới dạng một cái nút bấm
 *  vào nhận 403 mà không ai giải thích được.
 */

// `THAO_TAC + chutich + tgd` của app/api/v1/access.py — sửa mã NV, họ tên, phòng, pháp nhân, biên chế.
const VAI_SUA_HO_SO = ["cntt", "hcns", "chutich", "tgd"];
// `HR_WRITE` của app/api/v1/hr.py — khoá/mở đăng nhập và đặt lại mật khẩu. HẸP HƠN hẳn ở trên:
// Chủ tịch và TGĐ KHÔNG gọi được hai cửa này. Màn hình cũ hiện nút «Khoá» cho cả bốn vai nên hai
// vai lãnh đạo bấm vào là 403 — đúng cái bệnh mà chú thích của chính màn hình ấy đã cảnh báo cho
// nút «Đặt lại MK» mà lại bỏ sót nút «Khoá». Vòng này sửa.
const VAI_KHOA = ["hcns", "cntt"];
// `GHI` của app/api/v1/bien_dong_ns.py — ghi ngày nghỉ việc.
const VAI_NGHI_VIEC = ["hcns", "cntt", "tgd", "chutich"];
// `XOA` của app/api/v1/gop_tai_khoan.py — xoá vĩnh viễn bản ghi.
// Bản vẽ Chủ tịch duyệt ghi «chỉ Chủ tịch · CNTT». MÃ THẬT khác: hcns · chutich · tgd, KHÔNG có
// cntt. Màn hình theo MÃ, vì mã là thứ quyết định ai qua được cửa; chỗ lệch đã báo lại Chủ tịch.
const VAI_XOA = ["hcns", "chutich", "tgd"];

/** Hiện mờ chứ không ẩn (Chủ tịch chốt trên bản vẽ): người dùng thấy việc đó CÓ TỒN TẠI và biết
 *  phải nhờ ai, thay vì tưởng phần mềm thiếu chức năng. Ẩn hẳn thì mỗi vai thấy một hộp khác
 *  nhau, và hai người không hướng dẫn nhau qua điện thoại được. */
function Khoa({ co, can, children }: { co: boolean; can: string; children: React.ReactNode }) {
  if (co) return <>{children}</>;
  return <div style={{ opacity: 0.45 }}>
    {children}
    <p className="muted" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
      Cần vai {can}. Nhờ bộ phận ấy bấm hộ.
    </p>
  </div>;
}

export default function SuaTaiKhoan(
  { r, acc, vaiNguoiDung, onClose, onDone }:
  { r: any; acc: any; vaiNguoiDung: string; onClose: () => void; onDone: (msg: string) => void }
) {
  const duocSua = VAI_SUA_HO_SO.includes(vaiNguoiDung);
  const duocKhoa = VAI_KHOA.includes(vaiNguoiDung);
  const duocNghi = VAI_NGHI_VIEC.includes(vaiNguoiDung);
  const duocXoa = VAI_XOA.includes(vaiNguoiDung);

  const [maNv, setMaNv] = useState(r.staff_code || "");
  const [hoTen, setHoTen] = useState(r.full_name || "");
  const [phong, setPhong] = useState(r.department || "");
  const [ban, setBan] = useState(false);                 // đang gửi
  const [meta, setMeta] = useState<any>(null);           // danh sách lý do nghỉ, lấy từ máy chủ
  const [nvNgay, setNvNgay] = useState("");
  const [nvLoai, setNvLoai] = useState("tu_xin");
  const [nvLyDo, setNvLyDo] = useState("");
  const [bgDen, setBgDen] = useState("");               // người nhận bàn giao
  const [bgLyDo, setBgLyDo] = useState("");
  const [bgXem, setBgXem] = useState<any>(null);        // bản xem trước máy chủ trả về
  const [xoaDuoc, setXoaDuoc] = useState<any>(null);
  const [loi, setLoi] = useState("");

  // Lý do nghỉ lấy từ cửa `GET /bien-dong-ns/meta`, KHÔNG gõ cứng vào đây: thêm một loại lý do ở
  // máy chủ mà màn hình không biết thì người dùng không chọn được, và gõ cứng thì một ngày nào đó
  // màn hình gửi lên một mã lý do máy chủ đã bỏ.
  useEffect(() => {
    if (!duocNghi) return;
    api("/bien-dong-ns/meta").then(setMeta).catch(() => setMeta(null));
  }, [duocNghi]);

  // Xoá được hay không là việc của MÁY CHỦ trả lời, và nó trả lời kèm LÝ DO. Màn hình không tự
  // đoán theo "số việc đang gánh bằng 0" — chính Chủ tịch đã bác cách đoán ấy: lịch sử đã phát
  // sinh (kỳ lương, hợp đồng, đánh giá, tài sản) mới là thứ chặn, chứ không phải việc đang mở.
  useEffect(() => {
    if (!duocXoa) return;
    api(`/gop-tai-khoan/co-the-xoa/${r.id}`).then(setXoaDuoc).catch(() => setXoaDuoc(null));
  }, [duocXoa, r.id]);

  const goi = async (path: string, json: any, method: string, xong: string) => {
    setBan(true); setLoi("");
    try {
      const kq = await api<any>(path, { method, json });
      onDone(kq?.message || xong);
    } catch (e) { setLoi(errMsg(e)); }
    finally { setBan(false); }
  };

  const luuHoSo = () => {
    if (!hoTen.trim()) { setLoi("Họ tên không được để trống"); return; }
    goi(`/access/users/${r.id}/ho-so`,
        { ma_nv: maNv.trim(), ho_ten: hoTen.trim(), department: phong.trim() },
        "PUT", "Đã lưu");
  };

  const ghiNghiViec = () => {
    if (!r.ho_so_id) { setLoi("Tài khoản này chưa nối với hồ sơ nhân sự nào — đặt mã nhân viên trước."); return; }
    if (!nvNgay) { setLoi("Chưa chọn ngày nghỉ việc"); return; }
    if (!window.confirm(
      `Ghi nhận ${r.full_name} nghỉ việc từ ${nvNgay}?\n\n` +
      `Hồ sơ nhân sự đóng lại và người này ra khỏi bảng lương kỳ sau. ` +
      `Tài khoản đăng nhập KHÔNG tự khoá — đó là một việc riêng ở trên.`)) return;
    goi("/bien-dong-ns/nghi-viec",
        { employee_id: r.ho_so_id, ngay: nvNgay, ly_do_loai: nvLoai, ly_do: nvLyDo.trim() },
        "POST", "Đã ghi nhận nghỉ việc");
  };

  // HAI BƯỚC, cùng nếp với nút Xoá: `xac_nhan=false` chỉ lấy bản xem trước và KHÔNG ghi gì.
  // Bàn giao dịch chuyển doanh số giữa hai người, nên bước mặc định phải là bước không làm gì.
  const banGiao = async (that: boolean) => {
    if (!bgDen) { setLoi("Chưa chọn người nhận"); return; }
    if (!bgLyDo.trim()) { setLoi("Chưa ghi lý do bàn giao"); return; }
    setBan(true); setLoi("");
    try {
      const kq = await api<any>("/bien-dong-ns/ban-giao-viec", { method: "POST", json: {
        tu_user_id: r.id, den_user_id: Number(bgDen), ly_do: bgLyDo.trim(), xac_nhan: that } });
      if (that) { onDone(kq?.message || "Đã bàn giao"); } else { setBgXem(kq); }
    } catch (e) { setLoi(errMsg(e)); }
    finally { setBan(false); }
  };

  const xoaBanGhi = async () => {
    const ly = window.prompt(
      `XOÁ VĨNH VIỄN bản ghi ${r.full_name} (${r.username}). Không có nút hoàn lại.\n\n` +
      `Lý do (bắt buộc, vào bia mộ và nhật ký):`, "");
    if (!ly || !ly.trim()) { setLoi("Chưa ghi lý do – không xoá"); return; }
    // HAI BƯỚC, cố ý: `xac_nhan=false` chỉ lấy bản xem trước và KHÔNG ghi gì. Một thao tác không
    // hoàn lại được thì bước mặc định phải là bước không làm gì.
    setBan(true); setLoi("");
    try {
      const xt = await api<any>(`/gop-tai-khoan/${r.id}`, { method: "DELETE", json: { ly_do: ly.trim(), xac_nhan: false } });
      if (!window.confirm(
        `${xt?.ghi_chu || ""}\n\n`
        + `Còn ${xt?.tong_dong_con_lai ?? "?"} dòng dữ liệu trỏ tới tài khoản này.\n\n`
        + `Xoá thật ${r.username}?`)) { setBan(false); return; }
      const kq = await api<any>(`/gop-tai-khoan/${r.id}`, { method: "DELETE", json: { ly_do: ly.trim(), xac_nhan: true } });
      onDone(kq?.message || "Đã xoá bản ghi");
    } catch (e) { setLoi(errMsg(e)); }
    finally { setBan(false); }
  };

  const o: React.CSSProperties = { width: "100%", boxSizing: "border-box" };

  return <div style={{ border: "1px solid var(--line, #2a3b55)", borderRadius: 8, padding: 14, marginTop: 14 }}>
    <div className="row" style={{ gap: 10, alignItems: "baseline", marginBottom: 4 }}>
      <h3 style={{ margin: 0 }}>Sửa tài khoản — {r.full_name}</h3>
      <span className="muted" style={{ fontSize: 12 }}>
        {r.username} · {r.staff_code ? `mã NV ${r.staff_code}` : "chưa có mã NV"} ·{" "}
        {r.active ? "đang hoạt động" : "đã khoá"}
      </span>
      <button className="act grey" style={{ margin: 0, marginLeft: "auto" }} onClick={onClose}>Đóng</button>
    </div>
    {loi && <p style={{ color: "#f2868a", fontSize: 12.5 }}>{loi}</p>}

    {/* ---- 1. Thông tin tài khoản ---- */}
    <div style={{ borderTop: "1px solid var(--line, #2a3b55)", paddingTop: 12, marginTop: 10 }}>
      <b style={{ fontSize: 13 }}>Thông tin tài khoản</b>
      <Khoa co={duocSua} can="CNTT, HCNS, Chủ tịch hoặc TGĐ">
        <div className="row" style={{ gap: 10, marginTop: 8, flexWrap: "wrap" }}>
          <label style={{ flex: "1 1 150px" }}><span className="muted" style={{ fontSize: 11.5 }}>Mã nhân viên</span>
            <input style={o} value={maNv} disabled={!duocSua} onChange={(e) => setMaNv(e.target.value)} /></label>
          <label style={{ flex: "2 1 220px" }}><span className="muted" style={{ fontSize: 11.5 }}>Họ tên</span>
            <input style={o} value={hoTen} disabled={!duocSua} onChange={(e) => setHoTen(e.target.value)} /></label>
          <label style={{ flex: "1 1 150px" }}><span className="muted" style={{ fontSize: 11.5 }}>Phòng</span>
            <input style={o} value={phong} disabled={!duocSua} onChange={(e) => setPhong(e.target.value)} /></label>
        </div>
        <p className="muted" style={{ fontSize: 11.5, margin: "6px 0 0" }}>
          Mã nhân viên là khoá nối tài khoản với hồ sơ và bảng lương. Thiếu nó thì người này nằm
          ngoài mọi đối chiếu, và cũng không đặt lại mật khẩu mặc định được.
        </p>
        <div className="row" style={{ marginTop: 8 }}>
          <button className="act" style={{ margin: 0 }} disabled={!duocSua || ban} onClick={luuHoSo}>Lưu thay đổi</button>
        </div>
      </Khoa>
    </div>

    {/* ---- 2. Pháp nhân và biên chế. Vai trò KHÔNG ở đây: nó đã có ô chọn riêng trên bảng, kèm
            hộp hỏi lý do bắt buộc. Dựng ô thứ hai cho cùng một việc là hai đường đổi vai trò,
            và một trong hai đường sớm muộn quên mất phần hỏi lý do. ---- */}
    <div style={{ borderTop: "1px solid var(--line, #2a3b55)", paddingTop: 12, marginTop: 12 }}>
      <b style={{ fontSize: 13 }}>Pháp nhân và biên chế</b>
      <Khoa co={duocSua} can="CNTT, HCNS, Chủ tịch hoặc TGĐ">
        <div className="row" style={{ gap: 12, marginTop: 8, alignItems: "center", flexWrap: "wrap" }}>
          <label><span className="muted" style={{ fontSize: 11.5 }}>Pháp nhân chủ quản </span>
            <select value={r.company_id || ""} disabled={!duocSua}
              onChange={(e) => goi(`/access/users/${r.id}/company`,
                { company_id: e.target.value ? Number(e.target.value) : null }, "PUT", "Đã cập nhật pháp nhân")}>
              <option value="">— chưa xác định —</option>
              {(acc?.companies || []).map((c: any) => <option key={c.id} value={c.id}>{c.code}</option>)}
            </select></label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
            <input type="checkbox" checked={!!r.ngoai_bien_che} disabled={!duocSua}
              onChange={(e) => goi(`/access/users/${r.id}/bien-che`,
                { ngoai_bien_che: e.target.checked }, "PUT", "Đã cập nhật biên chế")} />
            Ngoài biên chế (có tài khoản nhưng không có trong bảng lương)
          </label>
        </div>
      </Khoa>
    </div>

    {/* ---- 3. A · Khoá đăng nhập ---- */}
    <div style={{ borderTop: "1px solid var(--line, #2a3b55)", paddingTop: 12, marginTop: 12 }}>
      <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
        <b style={{ fontSize: 13 }}>A · Khoá đăng nhập</b>
        <span className="muted" style={{ fontSize: 11.5 }}>HCNS · CNTT</span>
      </div>
      <Khoa co={duocKhoa} can="HCNS hoặc CNTT">
        <div className="row" style={{ gap: 10, marginTop: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button className="act" style={{ margin: 0 }} disabled={!duocKhoa || ban}
            onClick={() => goi(`/users/${r.id}`, { active: !r.active }, "PUT",
              r.active ? "Đã khoá đăng nhập" : "Đã mở lại")}>
            {r.active ? "Khoá đăng nhập" : "Mở lại"}</button>
          <button className="act grey" style={{ margin: 0 }} disabled={!duocKhoa || ban}
            onClick={() => {
              if (!window.confirm(`Đặt lại mật khẩu của ${r.full_name} về mã nhân viên?\n\n`
                + `Người này sẽ phải đổi mật khẩu ở lần đăng nhập tới — báo họ đăng nhập và đổi càng sớm càng tốt.`)) return;
              goi(`/users/${r.id}/reset-password`, { new_password: "" }, "POST", "Đã đặt lại mật khẩu");
            }}>Đặt lại mật khẩu = mã NV</button>
          <span className="muted" style={{ fontSize: 11.5 }}>
            Khoá chứ không xoá — nhật ký và chứng từ cũ vẫn truy ra được người thực hiện. Mở lại được bất cứ lúc nào.
          </span>
        </div>
      </Khoa>
    </div>

    {/* ---- 4. B · Ghi nhận nghỉ việc ---- */}
    <div style={{ borderTop: "1px solid var(--line, #2a3b55)", paddingTop: 12, marginTop: 12 }}>
      <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
        <b style={{ fontSize: 13 }}>B · Ghi nhận nghỉ việc</b>
        <span className="muted" style={{ fontSize: 11.5 }}>HCNS · CNTT · TGĐ · Chủ tịch</span>
      </div>
      <Khoa co={duocNghi} can="HCNS, CNTT, TGĐ hoặc Chủ tịch">
        <p className="muted" style={{ fontSize: 12, margin: "6px 0 0" }}>
          Kết thúc quan hệ công việc: đóng hồ sơ nhân sự và đưa người này ra khỏi bảng lương kỳ
          sau. KHÔNG tự chấm dứt hợp đồng lao động và KHÔNG tự khoá đăng nhập — ba chứng từ khác
          nhau, ba ngày có thể khác nhau.
        </p>
        {!r.ho_so_id
          ? <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
              <Tag cls="warn">chưa nối hồ sơ</Tag> Tài khoản này chưa có hồ sơ nhân sự nào —
              đặt mã nhân viên ở trên trước, cửa ghi nghỉ việc làm việc theo hồ sơ chứ không theo tài khoản.
            </p>
          : <>
            <div className="row" style={{ gap: 10, marginTop: 8, flexWrap: "wrap" }}>
              <label style={{ flex: "1 1 150px" }}><span className="muted" style={{ fontSize: 11.5 }}>Ngày nghỉ việc</span>
                <input style={o} type="date" value={nvNgay} disabled={!duocNghi}
                  onChange={(e) => setNvNgay(e.target.value)} /></label>
              <label style={{ flex: "1 1 200px" }}><span className="muted" style={{ fontSize: 11.5 }}>Lý do giảm</span>
                <select style={o} value={nvLoai} disabled={!duocNghi} onChange={(e) => setNvLoai(e.target.value)}>
                  {Object.entries(meta?.ly_do_giam || { tu_xin: "Tự xin nghỉ" })
                    .map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
                </select></label>
              <label style={{ flex: "2 1 240px" }}><span className="muted" style={{ fontSize: 11.5 }}>Ghi chú</span>
                <input style={o} value={nvLyDo} disabled={!duocNghi} onChange={(e) => setNvLyDo(e.target.value)} /></label>
            </div>
            <div className="row" style={{ marginTop: 8 }}>
              <button className="act orange" style={{ margin: 0 }} disabled={!duocNghi || ban}
                onClick={ghiNghiViec}>Ghi nhận nghỉ việc</button>
            </div>
          </>}

        {/* BÀN GIAO LÀ MỘT NÚT RIÊNG, không phải hệ quả của nút trên — HS-7, 16/10/2026.
            `ghi_nghi_viec` KHÔNG chuyển một tour, booking hay phân công nào; nó chỉ đóng hồ sơ.
            Gộp hai việc vào một lần bấm thì người bấm đọc một câu xác nhận mà làm hai thứ không
            hoàn lại được như nhau. Và bàn giao còn cần dùng khi người ta KHÔNG nghỉ: chuyển
            vùng, nghỉ thai sản, đi học. */}
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px dashed var(--line, #2a3b55)" }}>
          <b style={{ fontSize: 12.5 }}>Bàn giao việc đang mở</b>
          <p className="muted" style={{ fontSize: 11.5, margin: "4px 0 0" }}>
            Chỉ VIỆC ĐANG MỞ đổi người. Lịch sử đã phát sinh — tour đã kết thúc, booking đã huỷ,
            báo cáo, quyết toán, chỉ tiêu — giữ nguyên tên người cũ. Báo cáo kỳ ĐÃ CHỐT không đổi
            số; kỳ sau tính cho người nhận.
          </p>
          <div className="row" style={{ gap: 10, marginTop: 8, flexWrap: "wrap" }}>
            <label style={{ flex: "1 1 220px" }}><span className="muted" style={{ fontSize: 11.5 }}>Người nhận</span>
              <select style={o} value={bgDen} disabled={!duocNghi}
                onChange={(e) => { setBgDen(e.target.value); setBgXem(null); }}>
                <option value="">— chọn người nhận —</option>
                {(acc?.rows || []).filter((x: any) => x.id !== r.id && x.active)
                  .map((x: any) => <option key={x.id} value={x.id}>{x.full_name} ({x.username})</option>)}
              </select></label>
            <label style={{ flex: "2 1 240px" }}><span className="muted" style={{ fontSize: 11.5 }}>Lý do bàn giao</span>
              <input style={o} value={bgLyDo} disabled={!duocNghi}
                onChange={(e) => setBgLyDo(e.target.value)} /></label>
          </div>

          {/* Bản xem trước phải kê CẢ PHẦN Ở LẠI. Chỉ liệt kê thứ sắp chuyển sẽ khiến người bấm
              tin rằng mọi thứ khác không tồn tại. */}
          {bgXem && <div style={{ marginTop: 8, fontSize: 12, background: "var(--panel2, #0b1829)",
                                  border: "1px solid var(--line, #2a3b55)", borderRadius: 6, padding: "9px 11px" }}>
            <div><b>Sẽ chuyển sang {bgXem.den?.ho_ten}:</b>{" "}
              {bgXem.se_chuyen?.length
                ? bgXem.se_chuyen.map((x: any) => `${x.ten} (${x.so_dong})`).join(" · ")
                : "không có việc nào đang mở"}</div>
            {bgXem.o_lai?.length > 0 && <div style={{ marginTop: 5 }} className="muted">
              Ở lại với tên {bgXem.tu?.ho_ten}:{" "}
              {bgXem.o_lai.map((x: any) => `${x.bang} (${x.so_dong})`).join(" · ")}</div>}
          </div>}

          <div className="row" style={{ gap: 8, marginTop: 8 }}>
            <button className="act grey" style={{ margin: 0 }} disabled={!duocNghi || ban}
              onClick={() => banGiao(false)}>Xem trước</button>
            <button className="act orange" style={{ margin: 0 }}
              disabled={!duocNghi || ban || !bgXem}
              onClick={() => banGiao(true)}>Bàn giao</button>
          </div>
        </div>
      </Khoa>
    </div>

    {/* ---- 5. C · Xoá bản ghi ---- */}
    <div style={{ borderTop: "1px solid var(--line, #2a3b55)", paddingTop: 12, marginTop: 12 }}>
      <div className="row" style={{ gap: 8, alignItems: "baseline" }}>
        <b style={{ fontSize: 13, color: "#f2868a" }}>C · Xoá bản ghi</b>
        <span className="muted" style={{ fontSize: 11.5 }}>HCNS · Chủ tịch · TGĐ</span>
      </div>
      <Khoa co={duocXoa} can="HCNS, Chủ tịch hoặc TGĐ">
        <p className="muted" style={{ fontSize: 12, margin: "6px 0 0" }}>
          Chỉ cho bản ghi <b>tạo nhầm, chưa từng phát sinh liên kết nào</b>. Không phải cho người
          nghỉ việc: việc đang gánh về 0 KHÔNG làm bản ghi xoá được — lịch sử đã phát sinh (kỳ
          lương, hợp đồng, đánh giá, tài sản đã cấp) là thứ không bỏ đi.
        </p>
        {/* Nút tối mà không nói vì sao là nút người ta bấm mãi rồi đi hỏi CNTT. Câu giải thích
            lấy từ chính cửa `co-the-xoa`, không phải một câu đoán ở màn hình. */}
        {xoaDuoc && <div style={{ marginTop: 8, fontSize: 12 }}>
          {xoaDuoc.xoa_duoc
            ? <span style={{ color: "#58d79b" }}>✓ Bản ghi trống, xoá được.</span>
            : <div style={{ color: "#f2868a" }}>✕ Chưa xoá được:
                <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                  {(xoaDuoc.can_tro || []).map((c: string, i: number) => <li key={i}>{c}</li>)}
                </ul>
              </div>}
        </div>}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="act red" style={{ margin: 0 }}
            disabled={!duocXoa || ban || !(xoaDuoc && xoaDuoc.xoa_duoc)}
            onClick={xoaBanGhi}>Xoá bản ghi</button>
        </div>
      </Khoa>
    </div>
  </div>;
}
