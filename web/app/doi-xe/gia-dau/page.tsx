"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, getUser, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { useDaDoi } from "@/components/ThanhViec";
import MauDoiXe from "@/components/doixe/MauDoiXe";

/** GIÁ DẦU THEO NGÀY + ĐỊNH MỨC TIÊU HAO — cửa còn thiếu, Chủ tịch chốt 16/10/2026.
 *
 *  VÌ SAO CẦN: sao kê thẻ dầu cho TIỀN, không cho LÍT. Không có giá từng ngày thì ô Tiêu hao không
 *  có số lít để tính, và `fleet_lai_lo` chỉ ra được "km mỗi lít" mà không so được với định mức —
 *  nên câu "xe này vượt định mức" hôm nay không ai trả lời được.
 *
 *  MỘT DÒNG CHO MỘT NGÀY CÓ GIÁ MỚI, không phải mỗi ngày một dòng. Giá giữ nguyên đến ngày có dòng
 *  kế tiếp, nên mỗi lần điều chỉnh giá chỉ nhập một lần.
 *
 *  MÁY CHỦ KHÔNG LẤY GIÁ GẦN NHẤT KHI THIẾU NGÀY — câu `ghi_chu` của cửa nói rõ, và đó là một
 *  quyết định chứ không phải thiếu sót: giá dầu đổi mười ngày một lần, lấy giá cách đó ba tuần ra
 *  số lít sai mà trông vẫn hợp lý. Màn này vì thế hiện thẳng những ngày CHƯA có giá thay vì lấp.
 *
 *  AI GHI ĐƯỢC: `GHI_GIA_DAU = ("cntt", "ketoan", "gd_doi_xe")`. Rộng hơn phạt tài xế một vai —
 *  kế toán ghi được giá dầu nhưng không ghi được phạt tài xế.
 */

const GHI_GIA_DAU = ["cntt", "ketoan", "gd_doi_xe"];

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/doi-xe">Đội xe</a> · Giá dầu</>;

function GiaDau() {
  const { toast } = useShell();
  const [gd, setGd] = useState<any>(undefined);
  const [dm, setDm] = useState<any>(undefined);
  const daDoi = useDaDoi();
  const vai = getUser()?.role || "";

  const load = useCallback(async () => {
    try {
      const [a, b] = await Promise.all([api<any>("/fleet/gia-dau"), api<any>("/fleet/dinh-muc-dau")]);
      setGd(a); setDm(b);
    } catch (e) { toast(errMsg(e), true); setGd(null); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const napLai = async () => { await load(); daDoi.xong(); };

  const rows: any[] = gd?.rows || [];
  const norms: any[] = dm?.rows || dm?.dinh_muc || [];

  const viec = [
    {
      nhan: "Ghi giá mới",
      href: "/doi-xe/gia-dau/moi",
      chinh: true,
      tat: GHI_GIA_DAU.includes(vai) ? "" : "Cửa ghi giá dầu mở cho kế toán, Giám đốc đội xe và CNTT.",
    },
    { nhan: "Phạt tài xế", href: "/doi-xe/phat-tai-xe" },
    { nhan: "Lãi lỗ đội xe", href: "/lai-lo-doi-xe" },
  ];

  return (<>
    <ThanhViec duong={DUONG} daDoi={{ ...daDoi, napLai }} viec={viec} />
    <h1>Giá dầu theo ngày</h1>

    {gd === undefined && <p className="muted">Đang tải…</p>}
    {gd === null && <p className="muted">Không đọc được sổ giá dầu.</p>}

    {gd && (rows.length ? <div className="wrap"><table>
      <thead><tr>
        <th>Ngày áp dụng</th><th>Loại</th><th style={{ textAlign: "right" }}>Giá một lít</th>
        <th>Nguồn</th><th>Người ghi</th>
      </tr></thead>
      <tbody>{rows.map((r) => (
        <tr key={r.id}>
          <td>{fmtD(r.ngay)}</td>
          <td>{r.loai_ten || r.loai}</td>
          <td style={{ textAlign: "right" }} className="mono">{vnd(r.gia_lit)}</td>
          <td>{r.nguon || <span className="muted">—</span>}</td>
          <td className="muted">{r.boi}</td>
        </tr>))}</tbody>
    </table></div>
      : <p><Tag cls="warn">chưa có dòng nào</Tag> Chưa ai khai giá dầu. Đến khi có dòng đầu tiên thì
        mọi ô Tiêu hao vẫn trống, vì máy không quy được tiền dầu ra lít.</p>)}

    {gd?.ghi_chu && <p className="muted">{gd.ghi_chu}</p>}

    <h2>Định mức tiêu hao theo số chỗ</h2>
    <p className="muted">Một dòng cho mỗi loại xe. Đây là mốc để so với số lít thực tế — không có
      mốc thì tính ra được lít/100km nhưng không nói được là cao hay thấp.</p>
    {norms.length ? <div className="wrap"><table>
      <thead><tr><th>Số chỗ</th><th style={{ textAlign: "right" }}>Lít / 100km</th><th>Ghi chú</th><th>Người đặt</th></tr></thead>
      <tbody>{norms.map((n: any) => (
        <tr key={n.id ?? n.seats}>
          <td className="mono">{n.seats}</td>
          <td style={{ textAlign: "right" }} className="mono">{n.l_100km}</td>
          <td>{n.ghi_chu || <span className="muted">—</span>}</td>
          <td className="muted">{n.boi}</td>
        </tr>))}</tbody>
    </table></div>
      : <p className="muted">Chưa có định mức nào. Đặt ở màn <a href="/doi-xe">Đội xe</a>.</p>}

    <h2>Phép tính ba bước mà hai bảng trên mở ra</h2>
    <ol>
      <li>Tiền dầu một chuyến ÷ giá dầu của ngày chạy = <b>số lít</b></li>
      <li>Số lít ÷ km chuyến × 100 = <b>lít/100km thực tế</b></li>
      <li>So với định mức của loại xe ấy → <b>vượt hay không vượt</b></li>
    </ol>
    <p className="muted">Thiếu bảng thứ nhất thì tắc ngay bước 1. Thiếu bảng thứ hai thì ra được số
      ở bước 2 mà không đọc được bước 3.</p>
  </>);
}

export default function Page() { return <Shell><MauDoiXe><GiaDau /></MauDoiXe></Shell>; }
