"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DonNghiPhep from "@/components/DonNghiPhep";

/** Xe Vietrip & HDV – màn hình của chính người ở hiện trường (chỉ đạo 07/9/2026).
 *  Tài xế và hướng dẫn viên được cấp tài khoản nhưng chỉ thấy việc của mình: xe mình đứng tên, lệnh điều
 *  xe của mình, chuyến mình dẫn và hạn thẻ HDV. Không thấy giá xe nội bộ, không thấy hàng đợi của cả đội.
 *
 *  05/10/2026 — thêm CỬA GHI đầu tiên của người ở hiện trường: đề nghị tạm ứng của chính mình.
 *  Màn hình KHÔNG tự tính tuyến ký và không tự đặt tên người duyệt: nó in lại đúng những gì máy chủ
 *  trả về sau khi lập. Luật nằm ở `services/ops.py::CATEGORY_CONFIRMER`, một chỗ. */
function XeHdv() {
  // `user.role` chỉ dùng để ẨN khối không liên quan cho hướng dẫn viên — KHÔNG phải để canh quyền.
  // Cửa thật nằm ở máy chủ: `require_roles` của /payment-requests không có `hdv`, nên dù khối này
  // có hiện ra thì bấm vẫn 403. Màn hình giấu để đỡ rối, máy chủ chặn để đỡ sai.
  const { toast, user } = useShell();
  const laTaiXe = user?.role === "tai_xe";
  /** Người ở hiện trường — cả tài xế và hướng dẫn viên đều nộp được đơn nghỉ. Dùng để ẨN khối, KHÔNG
   *  để canh quyền: ai KÝ được đơn nào thì máy chủ trả lời bằng cờ `co_the_ky` của từng dòng. */
  const laHienTruong = user?.role === "tai_xe" || user?.role === "hdv";
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  /** Đề nghị tạm ứng của CHÍNH người đang đăng nhập. Máy chủ lọc theo `created_by`; màn hình không
   *  gửi kèm một bộ lọc nào – lọc ở màn hình là lọc tin được, lọc ở máy chủ mới là lọc. */
  const [ung, setUng] = useState<any[]>([]);
  const [formUng, setFormUng] = useState<any>({ mo: false, amount: "", description: "" });
  /** Báo hư hỏng của CHÍNH mình. Máy chủ lọc theo người báo; màn hình không gửi bộ lọc nào. */
  const [hong, setHong] = useState<any>(null);
  const [formHong, setFormHong] = useState<any>({ mo: false, vehicle_id: "", hien_tuong: "", muc_do: "con_chay_duoc", odo_km: "", noi_xay_ra: "" });
  /** Báo cáo sau tour của CHÍNH mình (Đợt 2 phòng HDV, 06/10/2026). Soạn ở đây rồi gửi; gửi rồi thì
   *  khoá, muốn sửa phải lập bản mới — bản cũ vẫn còn để đọc lại. Màn hình KHÔNG tự quyết chỗ nào:
   *  nó in lại đúng trạng thái máy chủ trả về. */
  const [bc, setBc] = useState<any>({ mo: 0, chuong_trinh_thuc_hien: "", so_khach_thuc_te: "",
    danh_gia_ncc: "", su_co: "", khoan_chi_thu_ho: "", viec_chua_xong: "" });
  /** Đơn nghỉ / ốm / vắng việc nay là MỘT thành phần dùng chung `components/DonNghiPhep` — cùng
   *  thành phần ấy đứng trên màn hình /cham-cong của cả mười một phòng. Khung này trước nằm thẳng ở
   *  đây, nên chín phòng không có ô nào để bấm dù cửa máy chủ nhận đơn của bất kỳ ai đăng nhập.
   *  Thành phần tự gọi `/leaves` và `/leave-balance`, nên hai lời gọi ấy đã rời khỏi `tai()`. */
  const tai = () => {
    api("/xe-hdv/cua-toi").then(setD).catch((x) => { setErr(errMsg(x)); toast(errMsg(x), true); });
    api<any[]>("/payment-requests").then(setUng).catch(() => setUng([]));
    api<any>("/fleet/bao-hong").then(setHong).catch(() => setHong(null));
  };
  useEffect(() => { tai(); }, []); // eslint-disable-line

  /** Lưu nháp hoặc lập bản mới cho báo cáo sau tour. Bản đã gửi thì máy chủ từ chối sửa đè —
   *  màn hình gọi cửa "bản mới" thay vì cố ghi đè, và nói rõ cho người dùng vì sao. */
  const luuBaoCao = async (aid: number, banMoi: boolean) => {
    const than: any = {
      chuong_trinh_thuc_hien: bc.chuong_trinh_thuc_hien || "",
      // Số khách để TRỐNG thì gửi null, không gửi 0: "chưa đếm" khác "đi 0 khách".
      so_khach_thuc_te: String(bc.so_khach_thuc_te).trim() === "" ? null : Number(bc.so_khach_thuc_te),
      danh_gia_ncc: bc.danh_gia_ncc || "", su_co: bc.su_co || "",
      khoan_chi_thu_ho: bc.khoan_chi_thu_ho || "", viec_chua_xong: bc.viec_chua_xong || "" };
    try {
      const duong = banMoi ? `/xe-hdv/bao-cao/${aid}/ban-moi` : `/xe-hdv/bao-cao/${aid}`;
      const r = await api<any>(duong, { method: "POST", json: than });
      toast(r.message); setBc({ ...bc, mo: 0 }); tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  const guiBaoCao = async (aid: number, pb: number | null) => {
    try {
      const r = await api<any>(`/xe-hdv/bao-cao/${aid}/gui`,
        { method: "POST", json: { phien_ban: pb } });
      toast(r.message + (r.tre_han ? " (nộp trễ hạn)" : "")); tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  /** Lập đề nghị tạm ứng. Người thụ hưởng là chính mình, nên màn hình KHÔNG hỏi nhà cung cấp —
   *  máy chủ điền tên người đăng nhập. Hỏi một ô mà câu trả lời luôn giống nhau là cách chắc chắn
   *  nhất để người ta gõ bừa. */
  const luuUng = async () => {
    const soTien = Number(String(formUng.amount).replace(/[^\d]/g, ""));
    if (!(soTien > 0)) { toast("Số tiền phải lớn hơn 0", true); return; }
    if (!String(formUng.description).trim()) { toast("Ghi rõ xin ứng để làm gì — người duyệt cần biết", true); return; }
    try {
      const r = await api<any>("/payment-requests", {
        method: "POST",
        json: { category: "tam_ung_tai_xe", supplier_name: "", amount: soTien, description: formUng.description },
      });
      toast(r.message);
      setFormUng({ mo: false, amount: "", description: "" });
      tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  /** Nhận hoặc từ chối một lời chào chuyến.
   *  Từ chối KHÔNG kèm hệ quả gì: hướng dẫn viên là cộng tác viên, và từ chối một lời chào là quyền của
   *  người cung cấp dịch vụ. Nút này nói rõ điều đó để không ai ngại bấm. */
  const traLoi = async (id: number, nhan: boolean) => {
    let ly_do = "";
    if (!nhan) {
      const v = window.prompt("Từ chối chuyến này. Ghi lý do nếu muốn (không bắt buộc).\n\n" +
        "Từ chối không ảnh hưởng gì đến việc được chào chuyến sau.");
      if (v === null) return;
      ly_do = v;
    }
    try {
      const d2 = await api<any>(`/xe-hdv/chao-chuyen/${id}/${nhan ? "nhan" : "tu-choi"}`,
                                { method: "POST", json: nhan ? {} : { ly_do } });
      toast(d2.message); await tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  /** Báo một chiếc xe đang hỏng. Màn hình KHÔNG hỏi số tiền và KHÔNG hỏi garage: lúc đứng cạnh
   *  chiếc xe thì tài xế chưa biết hai con số ấy, và một ô bắt buộc mà người gõ không biết câu trả
   *  lời thì ô ấy sẽ được điền bừa. Đề nghị sửa chữa do đội xe lập sau khi có báo giá. */
  const luuHong = async () => {
    if (!formHong.vehicle_id) { toast("Chọn xe", true); return; }
    if (!String(formHong.hien_tuong).trim()) { toast("Ghi rõ hiện tượng — người tiếp nhận cần biết hỏng cái gì", true); return; }
    try {
      const km = String(formHong.odo_km).replace(/[^\d]/g, "");
      const r = await api<any>("/fleet/bao-hong", {
        method: "POST",
        json: { vehicle_id: Number(formHong.vehicle_id), hien_tuong: formHong.hien_tuong,
                muc_do: formHong.muc_do, odo_km: km ? Number(km) : null, noi_xay_ra: formHong.noi_xay_ra },
      });
      toast(r.message);
      setFormHong({ mo: false, vehicle_id: "", hien_tuong: "", muc_do: "con_chay_duoc", odo_km: "", noi_xay_ra: "" });
      tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  if (err) return <><h1>Xe Vietrip &amp; HDV</h1><p className="muted">{err}</p></>;
  if (!d) return <p className="muted">Đang tải…</p>;
  const st = (s: string) => s === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : s === "da_xac_nhan" ? <Tag cls="navy">Đã nhận</Tag> : s === "huy" ? <Tag cls="red">Hủy</Tag> : s === "tu_choi" ? <Tag>Đã từ chối</Tag> : s === "het_han" ? <Tag>Lời chào hết hạn</Tag> : <Tag cls="warn">Đang chờ trả lời</Tag>;

  return (<>
    <h1>Xe Vietrip &amp; HDV</h1>
    <div className="panel"><h2>{d.ho_so.full_name} <span className="muted">· mã {d.ho_so.code}</span></h2>
      <p className="muted">{d.ho_so.department_name} · {d.ho_so.position_name}{d.ho_so.phone ? ` · ${d.ho_so.phone}` : ""}</p></div>

    {d.the_hdv && <div className="panel"><h2>Thẻ hướng dẫn viên</h2>
      <p>Số thẻ <b className="mono">{d.the_hdv.card_no || "—"}</b> · hạn <b>{fmtD(d.the_hdv.card_expiry)}</b>{" "}
        {d.the_hdv.du_dieu_kien ? <Tag cls="ok">Đủ điều kiện dẫn đoàn</Tag> : <Tag cls="red">Chưa đủ điều kiện</Tag>}</p>
      {!d.the_hdv.du_dieu_kien && <p className="muted">{d.the_hdv.vi_sao} – liên hệ Điều hành hoặc HCNS để cập nhật hồ sơ trước khi nhận chuyến.</p>}</div>}

    {d.xe.length > 0 && <div className="panel wrap"><h2>Xe tôi đứng tên</h2>
      <table><thead><tr><th>Biển số</th><th className="num">Chỗ</th><th>Loại</th><th>Pháp nhân sở hữu</th><th>Trạng thái</th></tr></thead>
        <tbody>{d.xe.map((v: any) => <tr key={v.id}><td><b>{v.plate}</b></td><td className="num">{v.seats || "—"}</td><td>{v.kind}</td><td>{v.company || <Tag cls="warn">chưa gán</Tag>}</td>
          <td>{v.active ? <Tag cls="ok">Đang khai thác</Tag> : <Tag cls="red">Ngưng khai thác</Tag>}</td></tr>)}</tbody></table></div>}

    {d.lenh_dieu_xe.length > 0 && <div className="panel wrap"><h2>Lệnh điều xe của tôi</h2>
      <table><thead><tr><th>Tour</th><th>Xe</th><th>Thời gian</th><th className="num">Số ngày</th><th>Trạng thái</th><th>Xác nhận lúc</th><th>Sự cố</th></tr></thead>
        <tbody>{d.lenh_dieu_xe.map((x: any) => <tr key={x.id}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td><td className="mono">{x.vehicle}</td>
          <td>{fmtD(x.date_from)} → {fmtD(x.date_to)}</td><td className="num">{x.days}</td><td>{st(x.status)}</td><td>{fmtDT(x.confirmed_at)}</td><td className="muted">{x.incident_note}</td></tr>)}</tbody></table></div>}

    {d.phan_chuyen.length > 0 && <div className="panel wrap"><h2>Chuyến được chào cho tôi</h2>
      <p className="muted">Mỗi dòng là một <b>lời chào</b>: nhận hoặc từ chối đều được. Từ chối không kèm
        hệ quả gì và không ghi vào hồ sơ — quá hạn trả lời thì lời chào hết hiệu lực, chuyến được chào
        cho người khác.</p>
      <table><thead><tr><th>Tour</th><th>Khởi hành</th><th className="num">Số ngày</th><th className="num">Thù lao</th><th>Trạng thái</th><th>Báo cáo</th><th>Tạm ứng</th><th></th></tr></thead>
        <tbody>{d.phan_chuyen.map((x: any) => <tr key={x.id}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td><td>{fmtD(x.start_date)}</td>
          <td className="num">{x.days}{x.holiday && <Tag cls="warn">lễ ×2</Tag>}</td><td className="num">{vnd(x.amount)}</td><td>{st(x.status)}</td>
          {/* Ba tình trạng, KHÔNG gộp thành một ô đúng/sai: chưa viết gì · đang chờ Trưởng phòng kiểm ·
              bị trả lại. Ba cái ấy đòi ba việc khác nhau từ chính người này. */}
          <td>{!x.bao_cao ? <Tag cls="warn">Chưa viết</Tag>
             : x.bao_cao.trang_thai === "da_xac_nhan" ? <Tag cls="ok">Đã xác nhận</Tag>
             : x.bao_cao.trang_thai === "da_gui" ? <Tag>Chờ TP kiểm · bản {x.bao_cao.ban_so}</Tag>
             : x.bao_cao.trang_thai === "can_bo_sung" ? <Tag cls="red">Trả lại</Tag>
             : <Tag cls="warn">Nháp</Tag>}
            {x.bao_cao?.tre_han && <div className="muted" style={{ color: "var(--red)" }}>quá hạn nộp</div>}
            {x.bao_cao?.han_nop && !x.bao_cao?.tre_han && <div className="muted">hạn {fmtD(x.bao_cao.han_nop)}</div>}</td>
          <td>{x.advance_settled ? <Tag cls="ok">Đã quyết toán</Tag> : <Tag cls="warn">Chưa</Tag>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{x.con_tra_loi_duoc ? <>
            <button className="act teal" style={{ margin: 0 }} onClick={() => traLoi(x.id, true)}>Nhận</button>{" "}
            <button className="act grey" style={{ margin: 0 }} onClick={() => traLoi(x.id, false)}>Từ chối</button>
            <div className="muted">trả lời trước {fmtDT(x.han_tra_loi)}</div>
          </> : x.ly_do ? <span className="muted">{x.ly_do}</span> : null}</td></tr>)}</tbody></table></div>}

    {/* BÁO CÁO SAU TOUR — cửa ghi của chính hướng dẫn viên (Đợt 2 phòng HDV, Chủ tịch chốt 06/10/2026).
        Hạn 3 ngày kể từ ngày tour kết thúc. Chưa nộp thì treo chào chuyến mới và treo thù lao —
        luật ấy đã có từ trước, màn hình này chỉ cho người ta chỗ để nộp. */}
    {!laTaiXe && d.phan_chuyen.some((x: any) => x.status === "da_xac_nhan") &&
      <div className="panel"><h2>Báo cáo sau tour của tôi</h2>
      <p className="muted">Nộp trong <b>3 ngày</b> kể từ ngày tour kết thúc. Gửi rồi thì khoá lại —
        muốn sửa thì lập <b>bản mới</b>, bản cũ vẫn còn để đọc lại. Trưởng phòng kiểm rồi mới tính là xong.</p>
      <table><thead><tr><th>Tour</th><th>Tình trạng</th><th></th></tr></thead>
        <tbody>{d.phan_chuyen.filter((x: any) => x.status === "da_xac_nhan").map((x: any) => (
          <tr key={x.id}><td><b>{x.tour_code}</b><div className="muted">{x.tour_name}</div></td>
            <td>{!x.bao_cao ? <span className="muted">chưa viết gì</span>
               : <>{x.bao_cao.trang_thai === "can_bo_sung"
                     ? <span><Tag cls="red">Trả lại</Tag><div className="muted">{x.bao_cao.y_kien_kiem}</div></span>
                     : <Tag cls={x.bao_cao.trang_thai === "da_xac_nhan" ? "ok" : "warn"}>
                         bản {x.bao_cao.ban_so} · {x.bao_cao.trang_thai}</Tag>}</>}</td>
            <td style={{ whiteSpace: "nowrap" }}>
              {x.bao_cao?.trang_thai !== "da_xac_nhan" &&
                <button className="act" style={{ margin: 0 }}
                        onClick={() => setBc({ ...bc, mo: bc.mo === x.id ? 0 : x.id })}>
                  {bc.mo === x.id ? "Đóng" : (x.bao_cao?.da_khoa ? "Lập bản mới" : "Viết báo cáo")}
                </button>}
              {x.bao_cao && !x.bao_cao.da_khoa &&
                <> <button className="act teal" style={{ margin: 0 }}
                           onClick={() => guiBaoCao(x.id, x.bao_cao.phien_ban)}>Gửi</button></>}
            </td></tr>))}</tbody></table>

      {bc.mo > 0 && <div className="wrap" style={{ marginTop: 12 }}>
        <label>Chương trình thực hiện <span className="muted">(bắt buộc — đây là phần Trưởng phòng đối chiếu với chương trình đã bán)</span><br />
          <textarea value={bc.chuong_trinh_thuc_hien}
                    onChange={(e) => setBc({ ...bc, chuong_trinh_thuc_hien: e.target.value })} /></label>
        <label>Số khách thực tế <span className="muted">(để trống nếu chưa đếm — trống khác 0)</span><br />
          <input value={bc.so_khach_thuc_te} inputMode="numeric"
                 onChange={(e) => setBc({ ...bc, so_khach_thuc_te: e.target.value })} /></label>
        <label>Đánh giá nhà cung cấp<br />
          <textarea value={bc.danh_gia_ncc} onChange={(e) => setBc({ ...bc, danh_gia_ncc: e.target.value })} /></label>
        <label>Sự cố trong tour<br />
          <textarea value={bc.su_co} onChange={(e) => setBc({ ...bc, su_co: e.target.value })} /></label>
        <label>Khoản chi và thu hộ<br />
          <textarea value={bc.khoan_chi_thu_ho} onChange={(e) => setBc({ ...bc, khoan_chi_thu_ho: e.target.value })} /></label>
        <label>Việc chưa xong<br />
          <textarea value={bc.viec_chua_xong} onChange={(e) => setBc({ ...bc, viec_chua_xong: e.target.value })} /></label>
        <div>
          <button className="act teal" onClick={() => {
            const x = d.phan_chuyen.find((y: any) => y.id === bc.mo);
            luuBaoCao(bc.mo, !!x?.bao_cao?.da_khoa);
          }}>Lưu nháp</button>{" "}
          <button className="act grey" onClick={() => setBc({ ...bc, mo: 0 })}>Thôi</button>
        </div>
      </div>}
    </div>}

    {/* SỐ DƯ TẠM ỨNG CỦA TÔI — tách theo từng túi (Đợt 3 phòng HDV).
        Không gộp khác chủ tiền, khác loại tiền: 5 triệu đồng của công ty và 300 đô của đối tác cộng
        lại thành một con số không ai trả được. Tiền thu hộ khách là túi riêng, không bù trừ. */}
    {(d.tui_ung || []).length > 0 && <div className="panel wrap"><h2>Tiền tôi đang giữ</h2>
      <table><thead><tr><th>Chủ tiền</th><th>Loại tiền</th><th className="num">Đã nhận</th>
        <th className="num">Chi hộ được duyệt</th><th className="num">Đã nộp lại</th><th className="num">Số dư</th><th></th></tr></thead>
        <tbody>{d.tui_ung.map((t: any, i: number) => <tr key={i}>
          <td>{t.chu_tien === "khach" ? "Thu hộ khách" : t.chu_tien === "doi_tac" ? "Đối tác" : "Vietourist"}</td>
          <td>{t.loai_tien}</td><td className="num">{vnd(t.da_nhan)}</td>
          <td className="num">{vnd(t.chi_ho_duyet)}</td><td className="num">{vnd(t.da_nop_lai)}</td>
          <td className="num"><b>{vnd(t.so_du)}</b></td>
          <td>{t.khong_bu_tru ? <Tag>không bù trừ</Tag>
             : t.cong_ty_no_lai ? <Tag cls="warn">công ty nợ lại</Tag> : null}</td></tr>)}</tbody></table>
      <p className="muted">Số dư âm nghĩa là <b>công ty nợ lại bạn</b> — Kế toán xem xét trả, hệ thống
        không tự trả. Tiền thu hộ khách để riêng, không trừ sang tiền công ty.</p></div>}

    {/* ĐỀ NGHỊ TẠM ỨNG — cửa GHI đầu tiên của người ở hiện trường (Chủ tịch quyết 05/10/2026).
        Khối này KHÔNG tự đặt tuyến ký và không in tên người duyệt từ màn hình: câu trả lời nằm ở
        máy chủ, và màn hình chỉ in lại lời máy chủ trả về. */}
    {laTaiXe && <div className="panel"><h2>Đề nghị tạm ứng của tôi</h2>
      <p className="muted">Xin ứng tiền đi đường. Hồ sơ đi qua <b>Giám đốc đội xe</b> xác nhận, rồi
        <b> Kế toán</b> kiểm chứng từ, rồi <b>Tổng giám đốc</b> ký. Bạn chỉ thấy đề nghị của chính mình.</p>

      {!formUng.mo
        ? <button className="act teal" onClick={() => setFormUng({ ...formUng, mo: true })}>Xin tạm ứng</button>
        : <div className="wrap">
            <label>Số tiền (đồng)<br />
              <input value={formUng.amount} inputMode="numeric"
                     onChange={(e) => setFormUng({ ...formUng, amount: e.target.value })} /></label>
            <label>Xin ứng để làm gì<br />
              <input value={formUng.description} style={{ minWidth: 320 }}
                     placeholder="vd: tiền cầu đường và ăn dọc đường chuyến Đà Lạt 12–14/10"
                     onChange={(e) => setFormUng({ ...formUng, description: e.target.value })} /></label>
            <div>
              <button className="act teal" onClick={luuUng}>Gửi đề nghị</button>{" "}
              <button className="act grey" onClick={() => setFormUng({ mo: false, amount: "", description: "" })}>Thôi</button>
            </div>
          </div>}

      {ung.length > 0 && <table style={{ marginTop: 12 }}>
        <thead><tr><th>Mã</th><th>Lập lúc</th><th className="num">Số tiền</th><th>Nội dung</th><th>Đang ở đâu</th></tr></thead>
        <tbody>{ung.map((x: any) => <tr key={x.id}><td className="mono">{x.code}</td><td>{fmtDT(x.created_at)}</td>
          <td className="num"><b>{vnd(x.amount)}</b></td><td>{x.description}</td>
          <td>{x.status === "da_chi" ? <Tag cls="ok">Đã chi</Tag>
            : x.status === "tu_choi" ? <Tag cls="red">Từ chối{x.reject_reason ? ` – ${x.reject_reason}` : ""}</Tag>
            : x.status === "cho_chi" ? <Tag cls="navy">Đã duyệt, chờ chi</Tag>
            : x.status === "cho_duyet" ? <Tag cls="warn">Chờ Tổng giám đốc ký</Tag>
            : x.status === "cho_kt" ? <Tag cls="warn">Chờ Kế toán kiểm</Tag>
            : <Tag cls="warn">Chờ Giám đốc đội xe xác nhận</Tag>}</td></tr>)}</tbody></table>}
      {ung.length === 0 && !formUng.mo && <p className="muted">Chưa có đề nghị tạm ứng nào.</p>}
    </div>}

    {laTaiXe && <div className="panel"><h2>Báo xe hỏng</h2>
      <p className="muted">Báo xe nào hỏng gì, <b>không cần biết tiền</b>. Đội xe tiếp nhận, rồi lập
        đề nghị sửa chữa khi có báo giá của garage. Chọn <b>Phải dừng xe</b> thì chiếc xe này bị
        chặn khi ai đó lập lệnh điều xe, cho tới khi đội xe đóng báo hỏng.</p>

      {!formHong.mo
        ? <button className="act teal" onClick={() => setFormHong({ ...formHong, mo: true })}>Báo xe hỏng</button>
        : <div className="wrap">
            <label>Xe<br />
              <select value={formHong.vehicle_id} onChange={(e) => setFormHong({ ...formHong, vehicle_id: e.target.value })}>
                <option value="">— chọn xe —</option>
                {(d.xe || []).map((v: any) => <option key={v.id} value={v.id}>{v.plate}</option>)}
                {(d.lenh_dieu_xe || []).map((x: any) => <option key={`l${x.id}`} value={x.vehicle_id}>{x.vehicle}</option>)}
              </select></label>
            <label>Hỏng cái gì<br />
              <input value={formHong.hien_tuong} style={{ minWidth: 320 }}
                     placeholder="vd: phanh kêu và ăn lệch về bên trái khi đạp gấp"
                     onChange={(e) => setFormHong({ ...formHong, hien_tuong: e.target.value })} /></label>
            <label>Mức độ<br />
              <select value={formHong.muc_do} onChange={(e) => setFormHong({ ...formHong, muc_do: e.target.value })}>
                <option value="con_chay_duoc">Còn chạy được</option>
                <option value="phai_dung_xe">Phải dừng xe</option>
              </select></label>
            <label>Số km đồng hồ <span className="muted">(nếu nhớ)</span><br />
              <input value={formHong.odo_km} inputMode="numeric"
                     onChange={(e) => setFormHong({ ...formHong, odo_km: e.target.value })} /></label>
            <label>Đang ở đâu <span className="muted">(không bắt buộc)</span><br />
              <input value={formHong.noi_xay_ra}
                     onChange={(e) => setFormHong({ ...formHong, noi_xay_ra: e.target.value })} /></label>
            <div>
              <button className="act teal" onClick={luuHong}>Gửi báo hỏng</button>{" "}
              <button className="act grey" onClick={() => setFormHong({ mo: false, vehicle_id: "", hien_tuong: "", muc_do: "con_chay_duoc", odo_km: "", noi_xay_ra: "" })}>Thôi</button>
            </div>
          </div>}

      {hong?.rows?.length > 0 && <table style={{ marginTop: 12 }}>
        <thead><tr><th>Xe</th><th>Báo lúc</th><th>Hiện tượng</th><th>Mức độ</th><th>Đang ở đâu</th><th>Kết quả</th></tr></thead>
        <tbody>{hong.rows.map((x: any) => <tr key={x.id}><td className="mono">{x.plate}</td><td>{fmtDT(x.bao_luc)}</td>
          <td>{x.hien_tuong}{x.noi_xay_ra ? <div className="muted">{x.noi_xay_ra}</div> : null}</td>
          <td>{x.muc_do === "phai_dung_xe" ? <Tag cls="red">Phải dừng xe</Tag> : <Tag cls="warn">Còn chạy được</Tag>}</td>
          <td>{x.trang_thai === "da_dong" ? <Tag cls="ok">Đã xử lý xong</Tag>
            : x.trang_thai === "da_tiep_nhan" ? <Tag cls="navy">Đội xe đã tiếp nhận</Tag>
            : <Tag cls="warn">Chờ đội xe tiếp nhận</Tag>}</td>
          <td className="muted">{x.ket_qua}</td></tr>)}</tbody></table>}
      {!hong?.rows?.length && !formHong.mo && <p className="muted">Bạn chưa báo hỏng xe nào.</p>}
    </div>}

    <DonNghiPhep guiDuoc={laHienTruong} />

    {d.xe.length === 0 && d.lenh_dieu_xe.length === 0 && d.phan_chuyen.length === 0 &&
      <p className="muted">Chưa có xe, lệnh điều xe hay chuyến nào gắn với hồ sơ của bạn. Nếu sai, báo Điều hành hoặc HCNS.</p>}
  </>);
}

export default function Page() { return <Shell><XeHdv /></Shell>; }
