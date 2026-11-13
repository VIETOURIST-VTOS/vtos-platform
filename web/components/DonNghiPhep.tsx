"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import { useHoi } from "@/components/HopHoi";

/** Đơn nghỉ phép / ốm / vắng việc — MỘT thành phần cho MỌI màn hình có ô bấm đơn.
 *
 *  Tách ra ngày 08/10/2026, khi mở đơn nghỉ cho cả mười một phòng. Trước bản ấy hai khung này nằm
 *  thẳng trong `app/xe-hdv/page.tsx`, nên chỉ tài xế và hướng dẫn viên với tới — cửa máy chủ
 *  `POST /leaves` dùng `current_user` và nhận đơn của bất kỳ ai đăng nhập, nhưng chín phòng còn lại
 *  không có ô nào để bấm. Cửa mở mà người không với tới thì cửa ấy chưa tồn tại.
 *
 *  VÌ SAO MỘT THÀNH PHẦN, KHÔNG PHẢI HAI BẢN CHÉP: chép khung này sang màn hình thứ hai thì hôm nay
 *  giống nhau từng chữ, và lệch nhau ở lần sửa thứ nhất — thường là lúc thêm một loại đơn, hoặc lúc
 *  sửa câu nhắc "từ chối phải ghi lý do". Lúc ấy người của phòng này đọc một bộ luật, người của
 *  phòng kia đọc một bộ khác, mà cả hai đều tin mình đang xem cùng một màn hình.
 *
 *  Thành phần này KHÔNG tự tính gì cả: quỹ phép do `hrm.create_leave` canh lúc gửi, người ký do
 *  `hrm.nguoi_ky_don` quyết, và dòng nào ký được thì máy chủ trả về cờ `co_the_ky` của chính dòng ấy.
 *  Màn hình lọc theo cờ ấy là để đỡ rối; chặn thật nằm trong `hrm.decide_leave`.
 */

const RONG = { mo: false, kind: "phep_nam", date_from: "", date_to: "", days: "", reason: "" };

export default function DonNghiPhep({ guiDuoc = true, tieuDe = "Đơn nghỉ phép / ốm / vắng việc" }:
  { guiDuoc?: boolean; tieuDe?: string }) {
  const { xacNhan, nhap, hop } = useHoi();
  const { toast } = useShell();
  const [don, setDon] = useState<any[]>([]);
  const [quy, setQuy] = useState<any>(null);
  const [f, setF] = useState<any>(RONG);

  /** MỘT lời gọi cho cả hai khung: máy chủ lọc ba tầng (`api/v1/hrm.py::list_leaves`), nên người
   *  thường nhận về đơn của chính mình còn người ký nhận thêm đơn của phòng mình. */
  const tai = useCallback(() => {
    api<any[]>("/leaves").then(setDon).catch(() => setDon([]));
    api<any[]>("/leave-balance").then((r) => setQuy(r?.[0] || null)).catch(() => setQuy(null));
  }, []);
  useEffect(() => { tai(); }, [tai]);

  const luu = async () => {
    if (!f.date_from) { toast("Chọn ngày bắt đầu nghỉ", true); return; }
    if (!String(f.reason).trim()) { toast("Ghi lý do — người ký cần biết để quyết", true); return; }
    try {
      await api("/leaves", {
        method: "POST",
        json: {
          kind: f.kind, date_from: f.date_from,
          date_to: f.date_to || f.date_from,
          days: f.days ? Number(f.days) : null,
          reason: String(f.reason).trim(),
        },
      });
      setF(RONG);
      toast("Đã gửi đơn. Đơn nằm ở hàng đợi của người ký cho tới khi có quyết định.");
      tai();
    } catch (x: any) { toast(errMsg(x), true); }
  };

  /** Từ chối bắt buộc có lý do, và đòi ở CẢ HAI chỗ là có chủ ý: máy chủ đòi để không ai lách được
   *  bằng cửa khác, màn hình đòi để người dùng khỏi gửi đi rồi bị trả về. */
  const quyet = async (id: number, duyet: boolean) => {
    let note = "";
    if (!duyet) {
      const v = await nhap("Từ chối đơn này. Ghi lý do để người làm đơn biết vì sao:");
      if (v === null) return;
      if (!v.trim()) { toast("Từ chối phải ghi lý do", true); return; }
      note = v.trim();
    }
    try {
      await api(`/leaves/${id}/decide`, { method: "POST", json: { approve: duyet, note } });
      toast(duyet ? "Đã duyệt đơn" : "Đã từ chối đơn");
      tai();
    } catch (x: any) { toast(errMsg(x), true); }
  };

  const st = (s: string) => s === "duyet" ? <Tag cls="ok">Đã duyệt</Tag>
    : s === "tu_choi" ? <Tag cls="red">Từ chối</Tag>
    : s === "huy" ? <Tag>Đã hủy</Tag> : <Tag cls="warn">Chờ ký</Tag>;

  // Bảng thứ nhất in CẢ `don`, không lọc bỏ đơn của phòng mình — giữ nguyên hành vi của khung cũ ở
  // /xe-hdv. Máy chủ đã lọc ba tầng; lọc thêm một tầng ở đây là đoán xem máy chủ vừa trả về những gì,
  // và cái đoán ấy sai vào đúng ngày tầng lọc máy chủ đổi.
  const choKy = don.filter((x: any) => x.co_the_ky);

  return (<>{hop}
    {guiDuoc && <div className="panel"><h2>{tieuDe}</h2>
      <p className="muted">Gửi đơn ở đây. Đơn đi thẳng tới người ký của phòng bạn — <b>một chữ ký</b>,
        không qua bàn nào khác. Tổng giám đốc và Chủ tịch đọc được mọi đơn nhưng không ký ở bước này.
        {quy ? <> Phép năm {quy.year}: còn <b>{quy.remaining}</b> ngày
          {quy.pending > 0 ? <> (đang chờ ký {quy.pending} ngày)</> : null}.</> : null}</p>

      {!f.mo
        ? <button className="act teal" onClick={() => setF({ ...f, mo: true })}>Gửi đơn</button>
        : <div className="wrap">
            <label>Loại đơn<br />
              <select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
                <option value="phep_nam">Nghỉ phép năm</option>
                <option value="om_dau">Nghỉ ốm</option>
                <option value="khong_luong">Nghỉ không lương</option>
                <option value="thai_san">Nghỉ thai sản</option>
                <option value="cong_tac">Đi công tác</option>
              </select></label>
            <label>Từ ngày<br />
              <input type="date" value={f.date_from}
                     onChange={(e) => setF({ ...f, date_from: e.target.value })} /></label>
            <label>Đến ngày <span className="muted">(để trống = nghỉ một ngày)</span><br />
              <input type="date" value={f.date_to}
                     onChange={(e) => setF({ ...f, date_to: e.target.value })} /></label>
            <label>Số ngày <span className="muted">(để trống = máy tính; 0.5 = nửa ngày)</span><br />
              <input value={f.days} inputMode="decimal" style={{ width: 90 }}
                     onChange={(e) => setF({ ...f, days: e.target.value })} /></label>
            <label>Lý do<br />
              <input value={f.reason} style={{ minWidth: 320 }}
                     placeholder="vd: về quê giỗ, đã nhờ anh Hùng chạy thay chuyến ngày 12"
                     onChange={(e) => setF({ ...f, reason: e.target.value })} /></label>
            <div>
              <button className="act teal" onClick={luu}>Gửi đơn</button>{" "}
              <button className="act grey" onClick={() => setF(RONG)}>Thôi</button>
            </div>
          </div>}

      {don.length > 0 && <table style={{ marginTop: 12 }}>
        <thead><tr><th>Loại</th><th>Từ – đến</th><th className="num">Số ngày</th><th>Lý do</th><th>Trạng thái</th><th>Ghi chú của người ký</th></tr></thead>
        <tbody>{don.map((x: any) => <tr key={x.id}><td>{x.kind_name}</td>
          <td>{fmtD(x.date_from)} → {fmtD(x.date_to)}</td><td className="num">{x.days}</td>
          <td>{x.reason}</td><td>{st(x.status)}</td>
          <td className="muted">{x.decision_note}</td></tr>)}</tbody></table>}
      {don.length === 0 && !f.mo && <p className="muted">Bạn chưa gửi đơn nào.</p>}
    </div>}

    {choKy.length > 0 && <div className="panel wrap"><h2>Đơn chờ bạn ký</h2>
      <p className="muted">Đơn của người thuộc phòng bạn phụ trách. <b>Từ chối phải ghi lý do</b> —
        người làm đơn cần biết để sửa và gửi lại. Không ai ký được đơn của chính mình.</p>
      <table><thead><tr><th>Người làm đơn</th><th>Loại</th><th>Từ – đến</th><th className="num">Số ngày</th><th>Lý do</th><th></th></tr></thead>
        <tbody>{choKy.map((x: any) => <tr key={`k${x.id}`}>
          <td>{x.employee_name} <span className="muted mono">{x.employee_code}</span></td>
          <td>{x.kind_name}</td><td>{fmtD(x.date_from)} → {fmtD(x.date_to)}</td>
          <td className="num">{x.days}</td><td>{x.reason}</td>
          <td><button className="act teal" onClick={() => quyet(x.id, true)}>Duyệt</button>{" "}
            <button className="act grey" onClick={() => quyet(x.id, false)}>Từ chối</button></td></tr>)}</tbody></table>
    </div>}
  </>);
}
