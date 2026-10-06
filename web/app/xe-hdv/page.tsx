"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

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
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState("");
  /** Đề nghị tạm ứng của CHÍNH người đang đăng nhập. Máy chủ lọc theo `created_by`; màn hình không
   *  gửi kèm một bộ lọc nào – lọc ở màn hình là lọc tin được, lọc ở máy chủ mới là lọc. */
  const [ung, setUng] = useState<any[]>([]);
  const [formUng, setFormUng] = useState<any>({ mo: false, amount: "", description: "" });
  const tai = () => {
    api("/xe-hdv/cua-toi").then(setD).catch((x) => { setErr(errMsg(x)); toast(errMsg(x), true); });
    api<any[]>("/payment-requests").then(setUng).catch(() => setUng([]));
  };
  useEffect(() => { tai(); }, []); // eslint-disable-line

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
          <td>{x.report_submitted ? <Tag cls="ok">Đã nộp</Tag> : <Tag cls="warn">Chưa nộp</Tag>}</td>
          <td>{x.advance_settled ? <Tag cls="ok">Đã quyết toán</Tag> : <Tag cls="warn">Chưa</Tag>}</td>
          <td style={{ whiteSpace: "nowrap" }}>{x.con_tra_loi_duoc ? <>
            <button className="act teal" style={{ margin: 0 }} onClick={() => traLoi(x.id, true)}>Nhận</button>{" "}
            <button className="act grey" style={{ margin: 0 }} onClick={() => traLoi(x.id, false)}>Từ chối</button>
            <div className="muted">trả lời trước {fmtDT(x.han_tra_loi)}</div>
          </> : x.ly_do ? <span className="muted">{x.ly_do}</span> : null}</td></tr>)}</tbody></table></div>}

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

    {laTaiXe && <div className="panel"><h2>Xe hỏng thì báo thế nào</h2>
      <p className="muted">Hiện <b>chưa có cửa báo hư hỏng</b> trên phần mềm — báo trực tiếp cho Giám đốc
        đội xe. Đề nghị sửa chữa do đội xe lập sau khi có báo giá của garage, vì lúc xe vừa hỏng thì
        chưa ai biết số tiền và chưa chọn garage; bắt bạn gõ hai con số ấy là bắt bạn đoán.</p></div>}

    {d.xe.length === 0 && d.lenh_dieu_xe.length === 0 && d.phan_chuyen.length === 0 &&
      <p className="muted">Chưa có xe, lệnh điều xe hay chuyến nào gắn với hồ sơ của bạn. Nếu sai, báo Điều hành hoặc HCNS.</p>}
  </>);
}

export default function Page() { return <Shell><XeHdv /></Shell>; }
