"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Phiếu lương của CHÍNH người đăng nhập – /phieu-luong (08/9/2026).
 *
 *  Vì sao trang này phải có, và phải mở cho mọi vai trò: endpoint phiếu lương cá nhân đã có từ trước và
 *  ai đăng nhập cũng gọi được, nhưng /payroll chỉ chuyển hướng sang /hr – mà /hr thì tài xế, hướng dẫn
 *  viên và chuyên viên visa không mở được. Quyền có, dữ liệu có, chỉ thiếu cái cửa. Người lao động không
 *  xem được lương của chính mình là chỗ khó chấp nhận nhất trong cả hệ thống.
 *
 *  Trang này KHÔNG phải bảng lương công ty. Nó chỉ gọi tiền tố /api/v1/phieu-luong – tiền tố chỉ chứa
 *  endpoint tự lọc về đúng người – chứ KHÔNG gọi /api/v1/payroll-runs, vốn chứa cả bảng lương toàn công
 *  ty. Hàng rào phạm vi ngoài chỉ phân biệt tới mức tiền tố, nên gọi nhầm tiền tố ở đây buộc phải mở
 *  bảng lương công ty cho mọi vai trò để trang này chạy được.
 *
 *  Chỉ hiển thị, không sửa: phiếu lương sửa được trên màn hình là phiếu không còn đối chiếu được với sổ. */

type Ky = { period: string; trang_thai: string; da_ky: boolean; thuc_nhan: number | null; dang_giu?: boolean };

const TRANG_THAI: Record<string, [string, string]> = {
  nhap: ["Bản nháp robot – chưa ai xác nhận", "warn"],
  kt_xac_nhan: ["Kế toán đã xác nhận cơ sở tính", "ok"],
  hcns_lap: ["HCNS đã lập", "ok"],
  tgd_ky: ["TGĐ đã ký lô", "ok"],
};

const num = { textAlign: "right" as const, whiteSpace: "nowrap" as const };

function PhieuLuongPage() {
  const { toast } = useShell();
  const [ds, setDs] = useState<any>(null);
  const [ky, setKy] = useState("");
  const [p, setP] = useState<any>(null);
  const [loi, setLoi] = useState("");

  useEffect(() => {
    api<any>("/phieu-luong/ky-cua-toi")
      .then((r) => { setDs(r); if (r.rows?.length) setKy(r.rows[0].period); })
      .catch((e) => toast(errMsg(e), true));
  }, [toast]);

  const load = useCallback((k: string) => {
    if (!k) { setP(null); return; }
    setP(null); setLoi("");
    api<any>(`/phieu-luong/${k}`).then(setP).catch((e) => setLoi(errMsg(e)));
  }, []);
  useEffect(() => { load(ky); }, [ky, load]);

  if (!ds) return <p className="muted">Đang tải…</p>;

  if (!ds.co_ho_so) return <>
    <h1>Phiếu lương của tôi</h1>
    <p><Tag cls="warn">Chưa mở được</Tag> {ds.message}</p>
  </>;

  return <>
    <h1>Phiếu lương của tôi</h1>
    <p className="muted">Phiếu của chính bạn — mã nhân viên {ds.ma_nv}. Màn hình này chỉ hiện phần của bạn,
      không phải bảng lương công ty.</p>

    {ds.rows.length === 0 ? <p><Tag cls="warn">Chưa có</Tag> {ds.message}</p> : <>
      <div className="row" style={{ gap: 8, flexWrap: "wrap", margin: "10px 0", alignItems: "center" }}>
        <span className="muted">Kỳ lương:</span>
        <select value={ky} onChange={(e) => setKy(e.target.value)} style={{ minWidth: 260 }}>
          {ds.rows.map((r: Ky) => <option key={r.period} value={r.period}>
            {r.period} — {r.dang_giu ? "đang giữ" : vnd(r.thuc_nhan ?? 0)}{r.da_ky ? " (đã ký)" : ""}
          </option>)}
        </select>
        <span className="muted">{ds.rows.length} kỳ</span>
      </div>

      {loi && <p><Tag cls="warn">Không mở được</Tag> {loi}</p>}

      {/* CN-2 (Chủ tịch chốt 21/10/2026): lương bị giữ thì phiếu chỉ ghi «đang giữ», không số dự kiến. */}
      {p?.dang_giu && <div className="panel wrap">
        <h2 style={{ margin: 0 }}>{p.nhan_su.ten}</h2>
        <p className="muted">Kỳ {p.period} · {p.nhan_su.phong}</p>
        <p><Tag cls="warn">Đang giữ</Tag> {p.thong_bao}</p>
      </div>}
      {p && !p.dang_giu && <div className="panel wrap">
        <div className="row" style={{ gap: 10, flexWrap: "wrap", alignItems: "baseline" }}>
          <h2 style={{ margin: 0 }}>{p.nhan_su.ten}</h2>
          <Tag cls={TRANG_THAI[p.trang_thai_bang_luong]?.[1] || "warn"}>
            {TRANG_THAI[p.trang_thai_bang_luong]?.[0] || p.trang_thai_bang_luong}
          </Tag>
        </div>
        <p className="muted">
          Kỳ {p.period} · {p.nhan_su.phong} · {p.nhan_su.chuc_vu || "—"} · hợp đồng {p.nhan_su.hop_dong}
          {p.nhan_su.che_do_cong ? ` · ${p.nhan_su.che_do_cong}` : ""}
          {p.nhan_su.phap_nhan_tra_luong ? ` · trả bởi ${p.nhan_su.phap_nhan_tra_luong}` : ""}
        </p>
        {p.xac_dinh_luong && <p className="muted">Căn cứ xác định mức lương kỳ này: {p.xac_dinh_luong}</p>}

        <h3 style={{ marginTop: 14 }}>Thu nhập</h3>
        <table><tbody>
          <tr><td>Lương cơ bản của kỳ</td><td style={num}>{vnd(p.thu_nhap.luong_co_ban_ky)}</td></tr>
          {p.thu_nhap.cac_khoan.map((k: any, i: number) =>
            <tr key={i}><td>{k.ten}</td><td style={num}>{vnd(k.tien)}</td></tr>)}
          <tr><td><b>Tổng thu nhập</b></td><td style={num}><b>{vnd(p.thu_nhap.tong)}</b></td></tr>
        </tbody></table>

        <h3 style={{ marginTop: 14 }}>Khoản trừ</h3>
        <table><tbody>
          {p.khoan_tru.chi_tiet_che_tai.map((k: any, i: number) =>
            <tr key={i}><td>{k.ten}</td><td style={num}>{vnd(-k.tien)}</td></tr>)}
          <tr><td>Bảo hiểm xã hội phần người lao động
            {p.muc_dong_bhxh ? <span className="muted"> (trên {vnd(p.muc_dong_bhxh)})</span> : ""}</td>
            <td style={num}>{vnd(p.khoan_tru.bhxh_nguoi_lao_dong)}</td></tr>
          <tr><td>Đoàn phí công đoàn</td><td style={num}>{vnd(p.khoan_tru.doan_phi_cong_doan)}</td></tr>
          {p.khoan_tru.tncn_khau_tru > 0 &&
            <tr><td>Thuế TNCN khấu trừ</td><td style={num}>{vnd(p.khoan_tru.tncn_khau_tru)}</td></tr>}
          <tr><td><b>Tổng khoản trừ</b></td><td style={num}><b>{vnd(p.khoan_tru.tong)}</b></td></tr>
        </tbody></table>

        <p style={{ fontSize: 18, marginTop: 14 }}>
          <b>Thực nhận: {vnd(p.thuc_nhan)}</b>{" "}
          {p.da_ky ? <Tag cls="ok">TGĐ đã ký lô</Tag> : <Tag cls="warn">Chưa ký lô</Tag>}
          {p.bo_sung_so && <> <Tag cls="navy">trả qua bảng bổ sung số {p.bo_sung_so}</Tag></>}
        </p>
        {p.ghi_chu && <p className="muted">{p.ghi_chu}</p>}

        {p.khoan_dang_treo?.length > 0 && <>
          <h3 style={{ marginTop: 16 }}>Đang treo {p.khoan_dang_treo.length} khoản</h3>
          <p className="muted">{p.luu_y}</p>
          <div className="wrap"><table><thead><tr>
            <th>Chuyến</th><th>Kết thúc</th><th>Hạn quyết toán</th><th className="num">Quá hạn</th><th>Bước tiếp theo</th>
          </tr></thead><tbody>
            {p.khoan_dang_treo.slice(0, 20).map((x: any, i: number) => <tr key={i}>
              <td><b>{x.tour_code}</b></td><td>{fmtD(x.ket_thuc)}</td><td>{fmtD(x.han_quyet_toan)}</td>
              <td className="num">{x.qua_han_ngay ? <Tag cls="red">{x.qua_han_ngay} ngày</Tag> : "—"}</td>
              <td className="muted">{x.buoc_tiep_theo || x.ly_do}</td>
            </tr>)}
          </tbody></table></div>
        </>}

        <p className="muted" style={{ marginTop: 16 }}>
          Số liệu sai hoặc thiếu một khoản: báo HCNS kèm kỳ lương và tên khoản. Màn hình này chỉ hiển thị,
          không sửa được — phiếu lương sửa trên màn hình là phiếu không còn đối chiếu được với sổ.
        </p>
      </div>}
    </>}
  </>;
}

export default function Page() {
  return <Shell><PhieuLuongPage /></Shell>;
}
