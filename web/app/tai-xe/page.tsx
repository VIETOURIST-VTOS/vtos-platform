"use client";
import { useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Điều hành xe ▸ Hồ sơ tài xế.
 *
 *  Trước 05/10/2026 mục "Tài xế" trong cây phân hệ trỏ vào /xe-hdv – màn hình VIỆC CỦA CHÍNH TÀI XẾ.
 *  Người quản lý đội xe bấm vào không thấy hồ sơ ai; tài khoản không gắn mã nhân viên chỉ nhận được
 *  một dòng báo lỗi. Hồ sơ tài xế chưa từng có màn hình, dù dữ liệu đã nằm sẵn trong hệ thống.
 *
 *  Màn hình này CHỈ ĐỌC. Ba đường sửa đã có chỗ của nó và không gom về đây: hồ sơ nhân sự ở Nhân sự,
 *  bằng lái ở bộ nạp tệp, gán xe ở màn hình Đội xe. Mỗi dòng đều chỉ đúng chỗ phải đi để sửa. */

const KHOANG: [string, string][] = [
  ["tat_ca", "Tất cả"],
  ["du", "Đủ điều kiện"],
  ["chua_du_du_lieu", "Chưa đủ dữ liệu"],
  ["khong_dat", "Không đạt"],
  ["sap_het_han", "Bằng sắp hết hạn"],
  ["chua_gan_xe", "Chưa gắn xe"],
];

function soCho(x: any): string {
  // Ba thứ khác nhau, in ra ba kiểu khác nhau. -1 là CHƯA ĐỌC ĐƯỢC hạng, null là hạng KHÔNG giới
  // hạn số chỗ. Quy cả hai về một dấu gạch là xoá mất khác biệt mà người điều xe cần thấy.
  if (x.so_cho_toi_da === -1) return "chưa đọc được";
  if (x.so_cho_toi_da === null || x.so_cho_toi_da === undefined) return "không giới hạn";
  return `tối đa ${x.so_cho_toi_da} chỗ`;
}

function TaiXe() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [dangTai, setDangTai] = useState(true);
  const [loc, setLoc] = useState("tat_ca");
  const [tim, setTim] = useState("");

  useEffect(() => {
    api("/tai-xe").then(setD).catch((e) => toast(errMsg(e), true)).finally(() => setDangTai(false));
  }, [toast]);

  const rows: any[] = (d?.rows || []).filter((x: any) => {
    if (loc === "du" && !x.du_dieu_kien) return false;
    if (loc === "chua_du_du_lieu" && !x.chua_du_du_lieu) return false;
    if (loc === "khong_dat" && !x.khong_dat) return false;
    if (loc === "sap_het_han" && !x.sap_het_han) return false;
    if (loc === "chua_gan_xe" && x.xe_dang_dung_ten?.length) return false;
    const q = tim.trim().toLowerCase();
    if (!q) return true;
    return [x.full_name, x.code, x.phone, x.gplx_so].some((v: string) => (v || "").toLowerCase().includes(q));
  });

  return (<>
    <h1>Hồ sơ tài xế</h1>
    <p className="muted">Ai lái được xe hôm nay, và nếu không thì thiếu đúng cái gì. Hạng bằng có đủ cho
      một chiếc xe cụ thể hay không thì <b>cổng điều xe</b> quyết định lúc phát lệnh – câu đó phụ thuộc
      vào số chỗ của chiếc xe, nên không trả lời được ở màn hình danh sách người.</p>

    <div className="kpis">
      <div className="kpi"><b>{d?.dang_lam ?? "—"}</b><span>Tài xế đang cộng tác</span></div>
      <div className="kpi"><b>{d?.du_dieu_kien ?? "—"}</b><span>Đủ điều kiện lái</span></div>
      <div className="kpi"><b style={{ color: d?.chua_du_du_lieu ? "var(--orange)" : undefined }}>{d?.chua_du_du_lieu ?? "—"}</b><span>Chưa đủ dữ liệu để kết luận</span></div>
      <div className="kpi"><b style={{ color: d?.khong_dat ? "var(--red)" : undefined }}>{d?.khong_dat ?? "—"}</b><span>Không đạt – chưa được điều xe</span></div>
      <div className="kpi"><b>{d?.bang_sap_het_han ?? "—"}</b><span>Bằng hết hạn trong 60 ngày</span></div>
      <div className="kpi"><b>{d?.chua_gan_xe ?? "—"}</b><span>Chưa gắn xe nào</span></div>
    </div>
    {d?.ghi_chu && <p className="muted">{d.ghi_chu}</p>}

    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
      <select value={loc} onChange={(e) => setLoc(e.target.value)}>
        {KHOANG.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
      </select>
      <input placeholder="Tìm tên, mã nhân viên, số điện thoại, số GPLX"
             value={tim} onChange={(e) => setTim(e.target.value)} style={{ minWidth: 280 }} />
    </div>

    <div className="panel wrap"><table><thead><tr>
      <th>Tài xế</th><th>Bằng lái</th><th>Hạng</th><th>Hạn</th><th>Xe đang đứng tên</th>
      <th className="num">Chuyến 90 ngày</th><th>Tình trạng</th>
    </tr></thead><tbody>
      {dangTai
        ? <tr><td colSpan={7} className="muted">Đang tải danh sách tài xế…</td></tr>
        : !rows.length && <tr><td colSpan={7} className="muted">Không có tài xế nào ở bộ lọc này.</td></tr>}
      {!dangTai && rows.map((x: any) => (
        <tr key={x.id} style={{ opacity: x.dang_lam ? 1 : 0.55 }}>
          <td><b>{x.full_name}</b><div className="muted">{x.code}{x.phone ? ` · ${x.phone}` : ""}</div></td>
          <td>{x.gplx_so || <span className="muted">—</span>}
            {x.gplx_cap && <div className="muted">cấp {fmtD(x.gplx_cap)}</div>}</td>
          <td>{x.gplx_hang || <span className="muted">—</span>}
            <div className="muted">{soCho(x)}</div></td>
          <td>{x.gplx_het_han ? fmtD(x.gplx_het_han) : <span className="muted">chưa ghi</span>}
            {x.sap_het_han && <Tag cls="warn">còn {x.con_lai_ngay} ngày</Tag>}</td>
          <td>{x.xe_dang_dung_ten?.length
            ? x.xe_dang_dung_ten.map((v: any) => <div key={v.bien}>{v.bien} <span className="muted">{v.so_cho} chỗ</span></div>)
            : <span className="muted">chưa gắn xe</span>}</td>
          <td className="num">{x.so_chuyen_90_ngay}</td>
          <td>
            {x.du_dieu_kien
              ? <Tag cls="ok">Đủ điều kiện</Tag>
              : x.khong_dat ? <Tag cls="red">Không đạt</Tag> : <Tag cls="warn">Chưa đủ dữ liệu</Tag>}
            {x.thieu?.map((t: string, i: number) => <div key={i} className="muted">{t}</div>)}
          </td>
        </tr>
      ))}
    </tbody></table></div>

    {d?.cua_nhap && <p className="muted">Sửa ở đâu: {d.cua_nhap}</p>}
  </>);
}

export default function Page() { return <Shell><TaiXe /></Shell>; }
