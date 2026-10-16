"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { useDaDoi } from "@/components/ThanhViec";

/** LỆNH TÀI XẾ CHƯA NHẬN — tách khỏi /lenh-dieu-xe ngày 17/10/2026 (khối 7 của màn cũ). TOÀN MÀN.
 *
 *  DL-1b: quá hạn chưa nhận và tài xế báo không nhận được gộp vào MỘT cửa — với Giám đốc đội xe cả
 *  hai là một việc: "chuyến này chưa chắc có người lái".
 *
 *  Trên màn cũ khối này chỉ hiện khi có việc, để khỏi để lại một bảng rỗng phải cuộn qua mỗi ngày.
 *  Nay nó là một màn riêng người ta CHỦ Ý mở, nên hết việc thì nói thẳng là hết việc. Mỗi dòng mở
 *  màn một lệnh ở tab mới — đổi tài xế làm ở đó. */

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/lenh-dieu-xe">Lệnh điều xe</a> · Tài xế chưa nhận</>;

function ChuaNhan() {
  const { toast } = useShell();
  const [nhan, setNhan] = useState<any>(undefined);
  const daDoi = useDaDoi();
  const load = useCallback(async () => {
    try { setNhan(await api("/nhan-lenh/can-biet")); } catch (e) { toast(errMsg(e), true); setNhan(null); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const napLai = async () => { await load(); daDoi.xong(); };

  const ds = nhan ? [...(nhan.tu_choi || []), ...(nhan.qua_han || [])] : [];
  return (<>
    <ThanhViec toanMan duong={DUONG} daDoi={{ ...daDoi, napLai }}
      viec={[{ nhan: "‹ Lên một cấp", href: "/lenh-dieu-xe", len: true }]} />
    <h1>Lệnh tài xế chưa nhận ({ds.length})</h1>
    {nhan === undefined && <p className="muted">Đang tải…</p>}
    {nhan === null && <p className="muted">Không đọc được danh sách nhận lệnh.</p>}
    {nhan && <div className="panel wrap">
      <p className="muted">{nhan.ghi_chu}</p>
      {ds.length ? <table><thead><tr><th>Lệnh</th><th>Xe · tài xế</th><th>Tình hình</th></tr></thead>
        <tbody>{ds.map((r: any) => <tr key={r.id}>
          <td><a href={`/lenh-dieu-xe?ma=${r.id}`} target="_blank" rel="noopener" title="Mở lệnh này trong tab mới"><b>#{r.id}</b> ↗</a>
            <div className="muted">đi {fmtD(r.ngay_di)}</div></td>
          <td>{r.xe}<div className="muted">{r.tai_xe}</div></td>
          <td>{r.trang_thai_nhan === "tu_choi"
            ? <><Tag cls="red">báo không nhận được</Tag><div className="muted">{r.tu_choi_nhan_ly_do}</div></>
            : <><Tag cls="warn">quá hạn, chưa bấm</Tag><div className="muted">hạn {fmtDT(r.han_nhan)}</div></>}</td>
        </tr>)}</tbody></table>
        : <p><Tag cls="ok">hết việc</Tag> Không có lệnh nào quá hạn hay bị tài xế báo không nhận được.</p>}
      {nhan.dem && <p className="muted">Đã nhận: {nhan.dem.da_nhan} / {nhan.dem.dang_cho} lệnh còn hiệu lực — con số này để đọc con số ở trên: 2 trên 13 là chuyện thường, 2 trên 3 là đội xe đang có vấn đề.</p>}
    </div>}
  </>);
}

export default function Page() { return <Shell><ChuaNhan /></Shell>; }
