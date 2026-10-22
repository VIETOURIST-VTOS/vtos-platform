"use client";
import { Fragment, useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/* ĐỢT R4b-2b 23/10/2026 — MÀN HÌNH "HÓA ĐƠN CÒN THIẾU".
 *
 * Đây là CỬA NHẬP của hai cột `ngay_hoa_don` / `so_hoa_don` mà Đợt R4b-2a thêm vào dòng bút
 * toán. Theo ranh giới 09/9/2026: máy dựng cấu trúc và phép tính, SỐ do người nhập — nên hai
 * cột ấy không có màn hình thì đó là việc còn thiếu, không phải chỗ để ai nhập hộ.
 *
 * Luật đếm nằm ở MÁY CHỦ (`services/books.py`), màn hình chỉ hiển thị: một dòng cần hóa đơn khi
 * chứng từ của nó có chạm thuế GTGT. Không chép lại luật ấy vào đây — hai nơi khai thì sớm muộn
 * lệch, và lúc lệch không ai biết bên nào đúng.
 *
 * KHÔNG chặn khóa kỳ. Màn hình này chỉ đếm và nhập.
 */

const dauThang = () => new Date().toISOString().slice(0, 8) + "01";
const homNay = () => new Date().toISOString().slice(0, 10);

type Dong = {
  line_id: number; date: string; code: string; doc_no: string; description: string;
  account: string; contra: string; partner: string; partner_code: string;
  debit: number; credit: number; so_ngay: number;
  ngay_hoa_don: string | null; so_hoa_don: string; hoa_don_trang_thai: string;
};

const NHAN: Record<string, { ten: string; cls: string }> = {
  "": { ten: "Chưa nhận được", cls: "warn" },
  da_nhap: { ten: "Đã nhập", cls: "ok" },
  khong_phat_sinh: { ten: "Không phát sinh hóa đơn", cls: "grey" },
};

function HopGhi({ d, xong }: { d: Dong; xong: () => void }) {
  const { toast } = useShell();
  const [tt, setTt] = useState(d.hoa_don_trang_thai || "da_nhap");
  const [ngay, setNgay] = useState(d.ngay_hoa_don ? d.ngay_hoa_don.slice(0, 10) : d.date.slice(0, 10));
  const [so, setSo] = useState(d.so_hoa_don || "");
  const [ly, setLy] = useState("");
  const [dangGhi, setDangGhi] = useState(false);
  const ghi = async () => {
    setDangGhi(true);
    try {
      await api("/books/hoa-don-thieu/ghi", {
        method: "POST",
        json: { line_id: d.line_id, trang_thai: tt, ngay_hoa_don: tt === "da_nhap" ? ngay : null, so_hoa_don: tt === "da_nhap" ? so : "", ly_do: tt === "khong_phat_sinh" ? ly : "" },
      });
      toast("Đã ghi hóa đơn cho dòng " + d.code);
      xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDangGhi(false); }
  };
  return (
    <div className="panel" style={{ margin: 0, background: "var(--panel2, #fafbff)" }}>
      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label style={{ minWidth: 190 }}>Trạng thái
          <select value={tt} onChange={(e) => setTt(e.target.value)}>
            <option value="da_nhap">Đã nhập — có hóa đơn</option>
            <option value="khong_phat_sinh">Không phát sinh hóa đơn</option>
            <option value="">Chưa nhận được</option>
          </select>
        </label>
        {tt === "da_nhap" && <>
          <label>Ngày hóa đơn<input type="date" value={ngay} onChange={(e) => setNgay(e.target.value)} /></label>
          <label style={{ minWidth: 190 }}>Số hóa đơn<input value={so} placeholder="1C26TSH 0004127" onChange={(e) => setSo(e.target.value)} /></label>
        </>}
        {tt === "khong_phat_sinh" &&
          <label style={{ flexGrow: 1, minWidth: 260 }}>Lý do <b style={{ color: "var(--orange)" }}>(bắt buộc)</b>
            <input value={ly} placeholder="ví dụ: vé giấy tại trạm, không lấy được hóa đơn" onChange={(e) => setLy(e.target.value)} /></label>}
        <button className="act" onClick={ghi} disabled={dangGhi}>{dangGhi ? "Đang ghi…" : "Ghi"}</button>
      </div>
      <p className="muted" style={{ margin: "8px 0 0" }}>
        Ngày hóa đơn <b>không</b> đổi ngày hạch toán và <b>không</b> đổi kỳ của bút toán — nó là một mốc riêng.
        Hệ thống lưu người ghi và giờ ghi; không cần ai duyệt.
      </p>
    </div>
  );
}

export default function HoaDonThieu() {
  const { toast } = useShell();
  const [tu, setTu] = useState(dauThang());
  const [den, setDen] = useState(homNay());
  const [tt, setTt] = useState("");
  const [doiTuong, setDoiTuong] = useState("");
  const [quaNgay, setQuaNgay] = useState(0);
  const [rep, setRep] = useState<any>(null);
  const [mo, setMo] = useState<number | null>(null);
  const [dangTai, setDangTai] = useState(false);

  const tai = useCallback(async () => {
    setDangTai(true);
    try {
      const q = new URLSearchParams({ since: tu, upto: den, trang_thai: tt, partner_code: doiTuong, qua_ngay: String(quaNgay) });
      setRep(await api("/books/hoa-don-thieu?" + q.toString()));
    } catch (e) { toast(errMsg(e), true); } finally { setDangTai(false); }
  }, [tu, den, tt, doiTuong, quaNgay, toast]);
  useEffect(() => { tai(); }, [tai]);

  const dem = rep?.dem || { chua_nhan: 0, da_nhap: 0, khong_phat_sinh: 0 };
  const tuoi = rep?.tuoi || { duoi_30: 0, tu_31_60: 0, qua_60: 0 };

  return (
    <Shell>
      <div className="panel">
        <h2 style={{ marginBottom: 2 }}>Hóa đơn còn thiếu</h2>
        <span className="muted">
          Những dòng bút toán <b>có chạm thuế GTGT</b> mà chưa ghi ngày và số hóa đơn. Có thuế thì phải có hóa đơn.
          Màn hình này <b>không chặn khóa kỳ</b> — nó chỉ đếm và cho nhập.
        </span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        <div className="panel"><span className="muted">Chưa nhận được</span><h3 style={{ margin: "4px 0 0" }}>{dem.chua_nhan} dòng</h3>
          <span className="muted">{vnd(rep?.tien)} đ · thuế {vnd(rep?.thue)} đ</span></div>
        <div className="panel"><span className="muted">Không phát sinh hóa đơn</span><h3 style={{ margin: "4px 0 0" }}>{dem.khong_phat_sinh} dòng</h3>
          <span className="muted">đã ghi lý do</span></div>
        <div className="panel"><span className="muted">Đã nhập</span><h3 style={{ margin: "4px 0 0" }}>{dem.da_nhap} dòng</h3>
          <span className="muted">của kỳ đang xem</span></div>
        <div className="panel"><span className="muted">Theo tuổi</span>
          <h3 style={{ margin: "4px 0 0" }}>{tuoi.duoi_30} · {tuoi.tu_31_60} · {tuoi.qua_60}</h3>
          <span className="muted">dưới 30 · 31–60 · quá 60 ngày{rep?.cu_nhat ? " · cũ nhất " + fmtD(rep.cu_nhat) : ""}</span></div>
      </div>

      <div className="panel" style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Từ ngày<input type="date" value={tu} onChange={(e) => setTu(e.target.value)} /></label>
        <label>Đến ngày<input type="date" value={den} onChange={(e) => setDen(e.target.value)} /></label>
        <label>Trạng thái
          <select value={tt} onChange={(e) => setTt(e.target.value)}>
            <option value="">Chưa nhận được</option>
            <option value="da_nhap">Đã nhập</option>
            <option value="khong_phat_sinh">Không phát sinh hóa đơn</option>
          </select></label>
        <label>Mã đối tượng<input value={doiTuong} placeholder="mã NCC / khách" onChange={(e) => setDoiTuong(e.target.value)} /></label>
        <label>Tuổi
          <select value={quaNgay} onChange={(e) => setQuaNgay(Number(e.target.value))}>
            <option value={0}>Tất cả</option><option value={30}>Quá 30 ngày</option><option value={60}>Quá 60 ngày</option>
          </select></label>
        <button className="act" onClick={tai} disabled={dangTai}>{dangTai ? "Đang lọc…" : "Lọc"}</button>
      </div>

      <div className="panel">
        {!rep ? <p className="muted">Đang tải…</p> : rep.rows.length === 0 ? (
          <div className="gate pass">Không còn dòng nào ở trạng thái này trong kỳ đang xem.</div>
        ) : (<>
          {rep.truncated && <p className="muted">Danh sách bị cắt còn {rep.shown_rows} trên {rep.total_rows} dòng — thu hẹp kỳ hoặc lọc theo đối tượng.</p>}
          <table>
            <thead><tr>
              <th>Ngày HT</th><th>Chứng từ</th><th>Diễn giải</th><th>Đối tượng</th>
              <th>TK / đối ứng</th><th style={{ textAlign: "right" }}>Phát sinh</th>
              <th>Hóa đơn</th><th>Tuổi</th><th></th>
            </tr></thead>
            <tbody>
              {rep.rows.map((d: Dong) => {
                const n = NHAN[d.hoa_don_trang_thai || ""] || NHAN[""];
                return (<Fragment key={d.line_id}>
                  <tr>
                    <td>{fmtD(d.date)}</td>
                    <td>{d.code}</td>
                    <td>{d.description}</td>
                    <td>{d.partner || d.partner_code || "—"}</td>
                    <td>{d.account} / {d.contra || "—"}</td>
                    <td style={{ textAlign: "right" }}>{vnd(d.debit || d.credit)}</td>
                    <td>{d.hoa_don_trang_thai === "da_nhap"
                      ? <span>{fmtD(d.ngay_hoa_don)} · {d.so_hoa_don}</span>
                      : <Tag cls={n.cls}>{n.ten}</Tag>}</td>
                    <td>{d.so_ngay} ngày</td>
                    <td><button className="act grey" style={{ margin: 0 }} onClick={() => setMo(mo === d.line_id ? null : d.line_id)}>
                      {mo === d.line_id ? "Đóng" : "Ghi"}</button></td>
                  </tr>
                  {mo === d.line_id && <tr><td colSpan={9}>
                    <HopGhi d={d} xong={() => { setMo(null); tai(); }} />
                  </td></tr>}
                </Fragment>);
              })}
            </tbody>
          </table>
        </>)}
      </div>
    </Shell>
  );
}
