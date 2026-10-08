"use client";
import { useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Lưới chấm công tháng — CỬA NHẬP ĐẦU TIÊN của bảng `attendance_days`, dựng 08/10/2026.
 *
 *  Bảng ấy được khai "có cửa nhập tay" trong bộ kiểm 09/9/2026, và `GET`/`POST /attendance` nằm trên
 *  máy chủ từ lúc ấy. Nhưng ra cả thư mục `web/` thì KHÔNG MỘT TỆP NÀO gọi `/attendance`: cửa có trên
 *  máy chủ, người phải dùng nó không với tới. Bộ kiểm chỉ biết bảng ĐÃ ĐƯỢC KHAI — chính docstring của
 *  nó nói trước điều ấy, và nói "chỗ đó do K12 gác". Đã mở K12 ra đọc: nó đối chiếu ma trận quyền với
 *  thư mục trang, nó không hỏi câu này. Không ai gác.
 *
 *  VÌ SAO LƯỚI ĐỨNG Ở MÀN HÌNH LƯƠNG, KHÔNG Ở /cham-cong. Ô ghi của lưới đòi `HR_ADMIN`, ô đọc đòi
 *  `HR_READ`. Nếu đặt lưới trên /cham-cong — màn hình mở cho cả 22 vai để ai cũng gửi được đơn nghỉ —
 *  thì `MAN_HINH_API` phải khai thêm tiền tố `/api/v1/attendance` cho cả 22 vai, mà phạm vi vai trò
 *  CỘNG RA TỪ bảng ấy. Mười sáu vai sẽ mang trong phạm vi một cửa máy chủ từ chối họ: bảng phân quyền
 *  đầy đủ hơn thực tế, đúng loại hỏng mà cả vòng này đi tìm. Người GHI lưới đã có mặt ở màn hình Lương
 *  rồi, và màn hình ấy khai `/api/v1/attendance` từ trước — nên đặt ở đây không nới phạm vi của ai.
 */

/** Ký hiệu một ô trong lưới. Hàng rào `test_ns2` đòi MỌI mã trong `ATT_KINDS` có một ký hiệu ở đây —
 *  bài học TX-7: một danh sách gõ tay song song với bảng của máy chủ thì lệch ở lần thêm mã thứ nhất.
 *  Vẫn giữ nhánh đỡ `|| c.kind` để lúc lệch thì ô in mã gốc chứ không in trống: trống là chỗ người
 *  đọc tưởng "chưa chấm". */
const KY_HIEU: Record<string, string> = {
  lam_viec: "x", phep_nam: "P", khong_luong: "K", om_dau: "Ô",
  thai_san: "TS", cong_tac: "CT", le: "L", vang: "V",
};

export default function LuoiChamCong({ period }: { period: string }) {
  const { toast } = useShell();
  const [bang, setBang] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [o, setO] = useState<any>(null);   // ô đang sửa

  const tai = useCallback(() => {
    api<any>(`/attendance?period=${period}`).then((r) => { setBang(r); setLoi(""); })
      .catch((x) => { setBang(null); setLoi(errMsg(x)); });
  }, [period]);
  useEffect(() => { tai(); }, [tai]);

  const luuO = async () => {
    try {
      await api("/attendance", { method: "POST", json: {
        employee_id: o.employee_id, day: `${period}-${String(o.day).padStart(2, "0")}`,
        kind: o.kind, work: Number(o.work), ot_hours: Number(o.ot_hours || 0), note: o.note || "" } });
      toast(`Đã chấm ${o.ma} ngày ${o.day}`);
      setO(null); tai();
    } catch (x: any) { toast(errMsg(x), true); }
  };

  return (<div className="panel">
    <h2>Bảng chấm công tháng {period}</h2>
    <p className="muted">Đơn nghỉ đã duyệt tự ghi vào lưới này. <b>Lưới KHÔNG phải căn cứ trả lương</b>:
      bảng lương lấy số công nhập ở bảng &quot;Công thực tế&quot; bên dưới, và chỗ hai số lệch nhau được
      đếm ra ở khung <b>Bảng chấm công chưa khớp bảng lương</b>. Đổi căn cứ trả lương là quyết định của
      Chủ tịch / Kế toán trưởng, không phải việc màn hình tự chọn.</p>
    {loi ? <p className="muted">{loi}</p> : <>
      {bang && <p className="muted">Công chuẩn tháng: <b>{bang.standard_days}</b> ngày.{" "}
        {Object.entries(KY_HIEU).map(([k, v]) => `${v} = ${bang.kinds?.[k] || k}`).join(" · ")}</p>}

      {bang && <div className="wrap"><table><thead><tr>
        <th>Mã</th><th>Họ tên</th>
        {bang.days.map((d: any) => <th key={d.day} className={d.weekend ? "muted" : ""}>{d.day}</th>)}
        <th className="num">Công</th><th className="num">Phép</th><th className="num">Không lương</th><th className="num">Giờ OT</th>
      </tr></thead>
      <tbody>{bang.rows.map((r: any) => <tr key={r.employee_id}>
        <td className="mono">{r.code}</td><td>{r.full_name}</td>
        {r.cells.map((c: any) => <td key={c.day} style={{ textAlign: "center", cursor: "pointer" }}
          title={`${r.full_name} · ngày ${c.day} · ${bang.kinds?.[c.kind] || c.kind} · ${c.work} công`}
          onClick={() => setO({ employee_id: r.employee_id, ma: r.code, ho_ten: r.full_name,
            day: c.day, kind: c.kind, work: c.work, ot_hours: c.ot_hours, note: "" })}>
          {KY_HIEU[c.kind] || c.kind}</td>)}
        <td className="num"><b>{r.work_days}</b></td><td className="num">{r.leave_days || ""}</td>
        <td className="num">{r.unpaid_days ? <Tag cls="warn">{r.unpaid_days}</Tag> : ""}</td>
        <td className="num">{r.ot_hours || ""}</td></tr>)}
      </tbody></table></div>}

      {o && <div className="panel" style={{ marginTop: 12 }}>
        <h3>Chấm ngày {o.day} — {o.ho_ten} <span className="muted mono">{o.ma}</span></h3>
        <div className="wrap">
          <label>Loại<br /><select value={o.kind} onChange={(e) => setO({ ...o, kind: e.target.value })}>
            {Object.entries(bang?.kinds || {}).map(([k, v]: any) => <option key={k} value={k}>{v}</option>)}
          </select></label>
          <label>Công <span className="muted">(0 · 0.5 · 1)</span><br />
            <input value={o.work} inputMode="decimal" style={{ width: 80 }}
              onChange={(e) => setO({ ...o, work: e.target.value })} /></label>
          <label>Giờ làm thêm<br />
            <input value={o.ot_hours} inputMode="decimal" style={{ width: 80 }}
              onChange={(e) => setO({ ...o, ot_hours: e.target.value })} /></label>
          <label>Ghi chú<br />
            <input value={o.note} style={{ minWidth: 280 }}
              onChange={(e) => setO({ ...o, note: e.target.value })} /></label>
          <div><button className="act teal" onClick={luuO}>Lưu</button>{" "}
            <button className="act grey" onClick={() => setO(null)}>Thôi</button></div>
        </div>
        <p className="muted">Ô nào chưa có bản ghi thì lưới hiển thị mặc định — đi làm ngày thường, nghỉ
          lễ cuối tuần. Lưu một ô là tạo bản ghi thật cho ngày ấy, đè lên mặc định.</p>
      </div>}
    </>}
  </div>);
}
