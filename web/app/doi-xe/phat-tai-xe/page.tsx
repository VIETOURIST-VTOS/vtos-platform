"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, getUser, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { docUrl, ghiUrl, useDaDoi } from "@/components/ThanhViec";
import MauDoiXe from "@/components/doixe/MauDoiXe";

/** SỔ PHẠT TÀI XẾ — cửa còn thiếu, Chủ tịch chốt 16/10/2026 làm trước bốn chỗ hở của đội xe.
 *
 *  VÌ SAO LÀ MÀN RIÊNG, không phải một tab của /doi-xe. Tệp `web/app/doi-xe/page.tsx` đang 1092
 *  dòng và đã mang mười mấy tab; thêm tab thứ mười mấy nữa là làm cái tệp ấy dài thêm mà không ai
 *  đọc lại được. Khai thành TRANG CON của "/doi-xe" trong `access.py` (MAN_CON_DOI_XE) nên nó
 *  không sinh mục menu mới và không sinh dòng quyền mới — đúng khuôn làn R5 đã dùng cho bốn trang
 *  con của "/lenh-dieu-xe" ngày 17/10.
 *
 *  BẢNG `fleet_driver_penalties` VÀ CỬA `POST /fleet/phat-tai-xe` ĐÃ CÓ TỪ ĐỢT DX-3. Thiếu đúng
 *  một thứ: màn hình. Không màn nào gọi cửa ấy nên không ai nhập được — đúng cái mà
 *  `services/ks_cua_nhap.py` đã ghi ở dòng 141 trong `CUA_TAY`.
 *
 *  KHOẢN PHẠT VÀO LƯƠNG, KHÔNG VÀO GIÁ VỐN XE (Chủ tịch chốt 16/10). Màn này vì thế KHÔNG có cột
 *  nào cộng tiền phạt vào chi phí xe, và câu `ghi_chu` do máy chủ trả về được in ra nguyên văn chứ
 *  không viết lại ở đây — hai bản của cùng một câu là hai câu trả lời cho cùng một câu hỏi.
 *
 *  KỲ LƯƠNG NẰM TRÊN ĐƯỜNG DẪN (`?ky=`). Luật 4 anh Tuấn chốt 16/10: mỗi nút mở một tab mới, nên
 *  trạng thái màn phải dựng lại được từ địa chỉ. Đổi ô kỳ mà địa chỉ không đổi thì tab mới mở ra
 *  một kỳ khác với kỳ người ta đang xem.
 */

const GHI_PHAT = ["cntt", "gd_doi_xe"];
const DOI_CHIEU = ["cntt", "hcns"];

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/doi-xe">Đội xe</a> · Phạt tài xế</>;

const kyNay = () => {
  const d = new Date();
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
};

function SoPhat() {
  const { toast } = useShell();
  const [so, setSo] = useState<any>(undefined);
  const [ky, setKy] = useState(() => docUrl().get("ky") || kyNay());
  const daDoi = useDaDoi();
  const vai = getUser()?.role || "";

  const load = useCallback(async (k: string) => {
    try { setSo(await api("/fleet/phat-tai-xe?ky=" + encodeURIComponent(k))); }
    catch (e) { toast(errMsg(e), true); setSo(null); }
  }, [toast]);

  useEffect(() => { load(ky); }, [load, ky]);
  const napLai = async () => { await load(ky); daDoi.xong(); };

  const doiKy = (k: string) => { setKy(k); ghiUrl({ ky: k }); };

  /* Đánh dấu đã đối chiếu: HCNS làm, và làm NGAY TRÊN DÒNG chứ không mở màn khác — nó là một cái
     bấm, không phải một việc cần biểu mẫu. */
  const doiChieu = async (id: number) => {
    try {
      await api("/fleet/phat-tai-xe/" + id + "/doi-chieu", { method: "POST" });
      toast("Đã đánh dấu đối chiếu khoản #" + id);
      await load(ky);
    } catch (e) { toast(errMsg(e), true); }
  };

  const rows: any[] = so?.rows || [];
  const choDoiChieu = so?.chua_doi_chieu ?? null;

  const viec = [
    {
      nhan: "Ghi phạt mới",
      href: "/doi-xe/phat-tai-xe/moi?ky=" + encodeURIComponent(ky),
      chinh: true,
      tat: GHI_PHAT.includes(vai) ? "" : "Chỉ Giám đốc đội xe ghi phiếu phạt; vai của anh/chị chỉ xem được.",
    },
    { nhan: "Định mức & giá dầu", href: "/doi-xe/gia-dau" },
    { nhan: "Hồ sơ xe", href: "/doi-xe" },
  ];

  return (<>
    <ThanhViec duong={DUONG} daDoi={{ ...daDoi, napLai }} viec={viec} />
    <h1>Phạt tài xế</h1>

    {/* Ô kỳ đứng ngay dưới tiêu đề, không nhét vào thanh việc: nó không phải một VIỆC, nó là
        phạm vi của mọi con số bên dưới. */}
    <div className="panel" style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
      <div>
        <label htmlFor="ky">Kỳ lương</label>
        <input id="ky" type="month" value={ky} onChange={(e) => doiKy(e.target.value)} />
      </div>
      {so && <>
        <div><div className="muted">Số khoản</div><b>{so.so_khoan}</b></div>
        <div><div className="muted">Tổng tiền</div><b>{vnd(so.tong_tien)} đ</b></div>
        <div>
          <div className="muted">Chờ HCNS đối chiếu</div>
          <b>{choDoiChieu}</b>{" "}
          {choDoiChieu ? <Tag cls="warn">còn {choDoiChieu}</Tag> : <Tag cls="ok">xong</Tag>}
        </div>
      </>}
    </div>

    {so === undefined && <p className="muted">Đang tải…</p>}
    {so === null && <p className="muted">Không đọc được sổ phạt.</p>}

    {so && (rows.length ? <div className="wrap"><table>
      <thead><tr>
        <th>Ngày</th><th>Tài xế</th><th>Kỳ lương</th><th style={{ textAlign: "right" }}>Số tiền</th>
        <th>Lý do</th><th>Gắn chuyến / xe</th><th>HCNS</th><th>Người ghi</th>
      </tr></thead>
      <tbody>{rows.map((r) => (
        <tr key={r.id}>
          <td>{fmtD(r.ngay)}</td>
          <td>{r.tai_xe || <span className="muted">#{r.driver_id}</span>}</td>
          <td className="mono">{r.ky}</td>
          <td style={{ textAlign: "right" }} className="mono">{vnd(r.so_tien)}</td>
          <td>{r.ly_do}</td>
          <td className="muted">
            {r.trip_id ? <>chuyến #{r.trip_id}</> : null}
            {r.trip_id && r.vehicle_id ? " · " : null}
            {r.vehicle_id ? <>xe #{r.vehicle_id}</> : null}
            {!r.trip_id && !r.vehicle_id ? "—" : null}
          </td>
          <td>{r.da_doi_chieu
            ? <><Tag cls="ok">đã đối chiếu</Tag>{r.doi_chieu_boi ? <div className="muted">{r.doi_chieu_boi}</div> : null}</>
            : DOI_CHIEU.includes(vai)
              ? <button className="act" onClick={() => doiChieu(r.id)}>Đánh dấu đã đối chiếu</button>
              : <Tag cls="warn">chờ</Tag>}</td>
          <td className="muted">{r.boi}</td>
        </tr>))}</tbody>
    </table></div>
      : <p><Tag cls="ok">chưa có khoản nào</Tag> Kỳ {ky} chưa có phiếu phạt nào được ghi.</p>)}

    {/* Câu này do MÁY CHỦ trả về. In nguyên văn, không viết lại. */}
    {so?.ghi_chu && <p className="muted">{so.ghi_chu}</p>}
  </>);
}

export default function Page() { return <Shell><MauDoiXe><SoPhat /></MauDoiXe></Shell>; }
