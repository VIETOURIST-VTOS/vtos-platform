"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import DonNghiPhep from "@/components/DonNghiPhep";
import TaiXeGhiChuyen from "@/components/doixe/TaiXeGhiChuyen";

/** Xe & lệnh của tôi — màn hình của chính TÀI XẾ (chỉ đạo 07/9/2026; Chủ tịch tách HDV ra 10/11/2026).
 *
 *  10/11/2026: Chủ tịch chốt «tài xế thấy lệnh điều xe bấm nhận, bỏ HDV ra — HDV sẽ đi một phòng khác».
 *  Mọi khối của hướng dẫn viên (thẻ HDV, chào chuyến, báo cáo sau tour, tiền đang giữ) đã gỡ khỏi màn
 *  này; cửa máy chủ `/api/v1/xe-hdv/...` của HDV GIỮ NGUYÊN để màn của phòng Hướng dẫn dùng lại.
 *
 *  Ghi chú cũ:
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
  // VH-34 (Chủ tịch duyệt 12/11/2026): tài xế XEM đề xuất chi đội xe trả cho chính mình — chỉ xem.
  const [tien, setTien] = useState<any>(null);
  const [formHong, setFormHong] = useState<any>({ mo: false, vehicle_id: "", hien_tuong: "", muc_do: "con_chay_duoc", odo_km: "", noi_xay_ra: "" });
  /** Đơn nghỉ / ốm / vắng việc nay là MỘT thành phần dùng chung `components/DonNghiPhep` — cùng
   *  thành phần ấy đứng trên màn hình /cham-cong của cả mười một phòng. Khung này trước nằm thẳng ở
   *  đây, nên chín phòng không có ô nào để bấm dù cửa máy chủ nhận đơn của bất kỳ ai đăng nhập.
   *  Thành phần tự gọi `/leaves` và `/leave-balance`, nên hai lời gọi ấy đã rời khỏi `tai()`. */
  const tai = () => {
    api("/xe-hdv/cua-toi").then(setD).catch((x) => { setErr(errMsg(x)); toast(errMsg(x), true); });
    api<any[]>("/payment-requests").then(setUng).catch(() => setUng([]));
    api<any>("/fleet/bao-hong").then(setHong).catch(() => setHong(null));
    if (laTaiXe) api<any>("/nhan-lenh/tien-cua-toi").then(setTien).catch(() => setTien(null));
  };
  useEffect(() => { tai(); }, []); // eslint-disable-line


  // ─── DL-1b: MẮT THỨ BA của chuỗi điều xe — tài xế NHẬN lệnh.
  // Hai nút nằm NGAY TRÊN khối "Lệnh điều xe của tôi" đã có, không dựng màn hình mới: tài xế mở
  // đúng một trang để xem lệnh và để trả lời về lệnh ấy.
  const [tuChoi, setTuChoi] = useState<any>(null);
  const [lyDoTuChoi, setLyDoTuChoi] = useState("");

  const nhanLenh = async (id: number) => {
    try {
      const r = await api<any>(`/nhan-lenh/${id}/nhan`, { method: "POST" });
      toast(r.message); tai();
    } catch (e) { toast(errMsg(e), true); }
  };

  const guiTuChoi = async () => {
    if (!tuChoi || !lyDoTuChoi.trim()) return;
    try {
      const r = await api<any>(`/nhan-lenh/${tuChoi.id}/tu-choi`,
        { method: "POST", json: { ly_do: lyDoTuChoi.trim() } });
      toast(r.message); setTuChoi(null); setLyDoTuChoi(""); tai();
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

  // HDV đã tách sang phòng Hướng dẫn (10/11/2026). Vai khác vào đây chỉ thấy một dòng nói rõ, không thấy
  // một màn hình rỗng như hỏng.
  if (!laTaiXe) return <><h1>Xe &amp; lệnh của tôi</h1>
    <div className="panel"><p>Màn hình này dành cho <b>tài xế</b>. Việc của hướng dẫn viên (chào chuyến,
      báo cáo sau tour, thẻ HDV) chuyển sang màn của <b>phòng Hướng dẫn</b>.</p></div>
    <DonNghiPhep guiDuoc={laHienTruong} /></>;
  if (err) return <><h1>Xe &amp; lệnh của tôi</h1><p className="muted">{err}</p></>;
  if (!d) return <p className="muted">Đang tải…</p>;

  return (<>
    <h1>Xe &amp; lệnh của tôi</h1>
    <div className="panel"><h2>{d.ho_so.full_name} <span className="muted">· mã {d.ho_so.code}</span></h2>
      <p className="muted">{d.ho_so.department_name} · {d.ho_so.position_name}{d.ho_so.phone ? ` · ${d.ho_so.phone}` : ""}</p></div>


    {d.xe.length > 0 && <div className="panel wrap"><h2>Xe tôi đứng tên</h2>
      <table><thead><tr><th>Biển số</th><th className="num">Chỗ</th><th>Loại</th><th>Pháp nhân sở hữu</th><th>Trạng thái</th></tr></thead>
        <tbody>{d.xe.map((v: any) => <tr key={v.id}><td><b>{v.plate}</b></td><td className="num">{v.seats || "—"}</td><td>{v.kind}</td><td>{v.company || <Tag cls="warn">chưa gán</Tag>}</td>
          <td>{v.active ? <Tag cls="ok">Đang khai thác</Tag> : <Tag cls="red">Ngưng khai thác</Tag>}</td></tr>)}</tbody></table></div>}

    {d.lenh_dieu_xe.length > 0 && <div className="panel"><h2>Lệnh điều xe của tôi</h2>
      <p className="muted">Lệnh nào còn chờ thì anh bấm <b>Tôi nhận lệnh này</b>. Không nhận được thì bấm nút bên cạnh và ghi lý do — <b>lệnh vẫn còn hiệu lực</b> cho tới khi Giám đốc đội xe quyết, anh đừng tự bỏ chuyến.</p>
      {/* VH-2: thẻ dọc thay bảng bảy cột — tài xế đọc trên điện thoại, bảng rộng phải kéo ngang. */}
      {d.lenh_dieu_xe.map((x: any) => <div key={x.id} style={{ borderTop: "1px solid var(--line, #e6eaf0)", padding: "10px 0" }}>
        <div><b>{x.tour_code}</b> · <span className="mono">{x.vehicle}</span>{" "}
          {x.status === "huy" ? <Tag cls="red">Lệnh đã huỷ</Tag> : x.status === "hoan_thanh" ? <Tag cls="ok">Hoàn thành</Tag> : null}</div>
        <div className="muted">{x.tour_name}</div>
        <div>{fmtD(x.date_from)} → {fmtD(x.date_to)} · {x.days} ngày</div>
        <div style={{ marginTop: 4 }}>
          {/* Đây là TÔI đã nhận chưa — khác với Giám đốc đội xe đã chốt lệnh chưa. */}
          {x.trang_thai_nhan === "da_nhan"
            ? <><Tag cls="ok">tôi đã nhận</Tag> <span className="muted">{fmtDT(x.nhan_luc)}</span></>
            : x.trang_thai_nhan === "tu_choi"
            ? <><Tag cls="red">tôi báo không nhận được</Tag> <div className="muted">{x.tu_choi_nhan_ly_do}</div></>
            : x.con_cho_nhan
            ? <>
                {x.trang_thai_nhan === "qua_han"
                  ? <div className="muted"><Tag cls="warn">quá hạn</Tag> hạn là {fmtDT(x.han_nhan)}</div>
                  : <div className="muted">hạn nhận {fmtDT(x.han_nhan)}</div>}
                <button className="act teal" style={{ margin: "6px 6px 0 0" }}
                  onClick={() => nhanLenh(x.id)}>Tôi nhận lệnh này</button>
                <button className="act grey" style={{ margin: "6px 0 0 0" }}
                  onClick={() => { setTuChoi(x); setLyDoTuChoi(""); }}>Tôi không nhận được</button>
              </>
            : null}
        </div>
        {x.incident_note && <div className="muted">Sự cố: {x.incident_note}</div>}
      </div>)}</div>}

    {/* GHI CHUYẾN TRÊN ĐIỆN THOẠI (Chủ tịch duyệt 10/11/2026): một thẻ cho mỗi lệnh đã nhận còn đang chạy
        hoặc vừa về trong 7 ngày. */}
    {(d.lenh_dieu_xe || []).filter((x: any) => x.trang_thai_nhan === "da_nhan" && x.status !== "huy"
        && new Date(x.date_to).getTime() >= Date.now() - 7 * 86400000)
      .map((x: any) => <TaiXeGhiChuyen key={`gc${x.id}`} lenh={x} toast={toast} />)}

    {laTaiXe && tien && <div className="panel"><h2>Tiền công ty trả cho tôi</h2>
      {tien.ghi && <p className="muted">{tien.ghi}</p>}
      {!tien.ghi && !(tien.rows || []).length && <p className="muted">Chưa có đề xuất chi nào trả cho anh.</p>}
      {(tien.rows || []).map((r: any) => <div key={r.code} style={{ display: "flex", justifyContent: "space-between", gap: 10,
        padding: "8px 0", borderTop: "1px solid var(--line)" }}>
        <div style={{ minWidth: 0 }}><b>{r.code}</b><div className="muted">{r.noi_dung}</div></div>
        <div style={{ textAlign: "right", whiteSpace: "nowrap" }}><b>{Number(r.so_tien).toLocaleString("vi-VN")} đ</b>
          <div><Tag cls={r.trang_thai === "da_chi" ? "ok" : r.trang_thai === "tu_choi" ? "red" : "warn"}>{r.buoc}</Tag></div></div>
      </div>)}
    </div>}

    {/* Ô lý do. BẮT BUỘC: đây là thứ duy nhất trả lời được câu hỏi của tháng sau — vì sao chuyến ấy
        phải đổi xe, hoặc phải thuê xe ngoài. */}
    {tuChoi && <div className="panel"><h2>Vì sao anh không nhận được lệnh này?</h2>
      <p className="muted">Lệnh <b>{tuChoi.tour_code}</b> · xe {tuChoi.vehicle} · {fmtD(tuChoi.date_from)} → {fmtD(tuChoi.date_to)}</p>
      <div><label>Lý do</label><textarea rows={2} value={lyDoTuChoi}
        onChange={(e) => setLyDoTuChoi(e.target.value)}
        placeholder="Ví dụ: xe đang nằm xưởng · tôi đang chạy chuyến khác · tôi nghỉ phép ngày đó" /></div>
      <p className="muted">Giám đốc đội xe thấy lý do này ngay. <b>Lệnh vẫn còn hiệu lực</b> cho tới khi ông quyết đổi xe hay đổi người.</p>
      <button className="act orange" disabled={!lyDoTuChoi.trim()} onClick={guiTuChoi}>Gửi lý do</button>{" "}
      <button className="act grey" onClick={() => { setTuChoi(null); setLyDoTuChoi(""); }}>Thôi, để tôi nhận</button>
    </div>}

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

    <DonNghiPhep guiDuoc={laTaiXe} />

    {d.xe.length === 0 && d.lenh_dieu_xe.length === 0 &&
      <p className="muted">Chưa có xe hay lệnh điều xe nào gắn với hồ sơ của bạn. Nếu sai, báo Giám đốc đội xe hoặc HCNS.</p>}
  </>);
}

export default function Page() { return <Shell><XeHdv /></Shell>; }
