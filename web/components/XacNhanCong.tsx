"use client";
import { Fragment, useCallback, useEffect, useState } from "react";
import { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** CN-1 · Xác nhận công tháng — Chủ tịch chốt 21/10/2026.
 *
 *  Mỗi phòng áp dụng một khối: HCNS xác nhận → TGĐ (hoặc Chủ tịch) duyệt. Số đã đổi sau khi xác
 *  nhận thì máy chủ trả «het_hieu_luc» và cả hai bước làm lại. Phòng chưa được duyệt công thì bảng
 *  lương kỳ ấy bị chặn. Ẩn nút ở đây KHÔNG phải hàng rào — hàng rào ở máy chủ.
 */
const MAU: Record<string, string> = { chua: "warn", hcns_xac_nhan: "navy", da_duyet: "ok", het_hieu_luc: "red" };

export default function XacNhanCong({ period }: { period: string }) {
  const { user, toast } = useShell();
  const role = user?.role || "";
  const [d, setD] = useState<any>(null);
  const [mo, setMo] = useState<string>("");
  const tai = useCallback(() => {
    api(`/attendance/xac-nhan-cong?period=${period}`).then(setD).catch((e) => { setD(null); toast(errMsg(e), true); });
  }, [period, toast]);
  useEffect(() => { tai(); }, [tai]);

  const bam = async (phong: string, buoc: "hcns" | "duyet") => {
    try {
      const r = await api<any>(`/attendance/xac-nhan-cong/${period}/${phong}/${buoc}`, { method: "POST" });
      toast(r.message); tai();
    } catch (e) { toast(errMsg(e), true); tai(); }
  };

  if (!d) return null;
  const xong = d.phong.filter((k: any) => k.trang_thai === "da_duyet").length;
  return <div className="panel wrap">
    <h2>Xác nhận công kỳ {period} · {xong}/{d.phong.length} phòng đã duyệt</h2>
    <p className="muted">HCNS xác nhận, TGĐ duyệt. Hạn {fmtD(d.han)}. Phòng chưa được duyệt công thì bảng lương kỳ này
      bị chặn. Hướng dẫn và Đội xe không áp dụng.</p>
    <table><thead><tr><th>Phòng</th><th>Chế độ công</th><th>Trạng thái</th><th>HCNS</th><th>TGĐ</th><th></th></tr></thead>
      <tbody>{d.phong.map((k: any) => <Fragment key={k.phong}>
        <tr>
          <td><button className="act grey" style={{ margin: 0, padding: "1px 8px" }} onClick={() => setMo(mo === k.phong ? "" : k.phong)}>
            {mo === k.phong ? "▾" : "▸"} {k.phong_ten}</button></td>
          <td className="muted">{k.che_do === "cham_cong" ? "Chấm công ngày" : "Báo cáo trước 20 giờ"}</td>
          <td><Tag cls={MAU[k.trang_thai] || "warn"}>{k.trang_thai_ten}</Tag>{k.qua_han && <> <Tag cls="red">quá hạn</Tag></>}</td>
          <td className="muted">{k.hcns_by ? `${k.hcns_by} · ${fmtDT(k.hcns_at)}` : "—"}</td>
          <td className="muted">{k.tgd_by ? `${k.tgd_by} · ${fmtDT(k.tgd_at)}` : "—"}</td>
          <td>
            {role === "hcns" && k.trang_thai !== "da_duyet" &&
              <button className="act teal" style={{ margin: 0 }} onClick={() => bam(k.phong, "hcns")}>
                {k.trang_thai === "chua" ? "Xác nhận công" : "Xác nhận lại"}</button>}
            {["tgd", "chutich"].includes(role) && k.trang_thai === "hcns_xac_nhan" &&
              <button className="act" style={{ margin: 0 }} onClick={() => bam(k.phong, "duyet")}>Duyệt công</button>}
          </td>
        </tr>
        {mo === k.phong && <tr><td colSpan={6}>
          {/* CN-3 (21/10/2026): báo cáo ngày chưa đi qua VTOS nên tạm không đếm — nói ra, không để cột trống. */}
          {k.che_do !== "cham_cong" && !k.dem_bao_cao &&
            <p className="muted" style={{ fontSize: 12 }}>Tạm chưa đếm báo cáo ngày (Chủ tịch chốt 21/10/2026) — bảng này chỉ có ngày nghỉ đã duyệt.</p>}
          {!k.dong.length ? <p className="muted">Phòng này không có nhân viên đang làm.</p> :
            <table><thead><tr><th>Nhân viên</th>
              {k.che_do === "cham_cong"
                ? <><th className="num">Công</th><th className="num">Phép</th><th className="num">Không lương</th></>
                : k.dem_bao_cao && <><th className="num">Ngày có báo cáo</th><th className="num">Đúng giờ</th><th className="num">TP đã chấm</th></>}
              <th className="num">Nghỉ đã duyệt</th><th>Cần xem</th></tr></thead>
              <tbody>{k.dong.map((r: any) => <tr key={r.employee_id}>
                <td>{r.ho_ten} <span className="muted mono">{r.ma}</span></td>
                {k.che_do === "cham_cong"
                  ? <><td className="num">{r.cong}</td><td className="num">{r.ngay_phep}</td><td className="num">{r.ngay_khong_luong}</td></>
                  : k.dem_bao_cao && <><td className="num">{r.ngay_bao_cao}</td><td className="num">{r.dung_gio}</td><td className="num">{r.tp_da_cham}</td></>}
                <td className="num">{r.nghi_da_duyet}</td>
                <td className="warn">{r.can_xem}</td></tr>)}</tbody></table>}
        </td></tr>}
      </Fragment>)}</tbody></table>
  </div>;
}
