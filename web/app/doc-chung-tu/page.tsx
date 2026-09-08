"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Đọc chứng từ ảnh ra số – cửa thứ ba của khuôn ba cửa nhập liệu.
 *
 *  Màn hình này cố ý KHÔNG có nút "nạp tất cả". Máy đọc xong thì số nằm ở hàng chờ; mỗi dòng phải
 *  được một người mở ra, nhìn lại ảnh gốc, sửa chỗ máy đọc sai rồi bấm xác nhận. Người bấm chịu
 *  trách nhiệm về con số y như người gõ tay – nên không có đường nào bấm hộ cả tệp.
 *
 *  Hai chi tiết trên giao diện là quy tắc chứ không phải trang trí:
 *    - Ô máy không đọc được để TRỐNG và tô vàng. Không điền 0, và không tự đoán theo ô bên cạnh.
 *    - Nút xác nhận chỉ hiện với vai trò được phép; máy chủ vẫn kiểm lại, đây chỉ là để đỡ mất công.
 */
type Ban = {
  id: number; loai: string; ten_loai: string; bo_nap: string; mo_hinh: string;
  so_may_doc: Record<string, string>; truong_khong_doc_duoc: string[]; ghi_chu_may: string;
  trang_thai: string; ten_trang_thai: string; truong_da_sua: string[];
  xac_nhan_boi: string; ket_qua_ghi: string; boi: string; luc: string;
};

const TEN_O: Record<string, string> = {
  mst_nguoi_ban: "MST người bán", ten_nguoi_ban: "Tên người bán", ky_hieu: "Ký hiệu",
  so_hoa_don: "Số hóa đơn", ngay_hd: "Ngày hóa đơn", noi_dung: "Nội dung",
  tien_truoc_thue: "Tiền trước thuế", thue_suat: "Thuế suất (%)", tien_thue: "Tiền thuế",
  tong_tien: "Tổng tiền", ma_gd: "Mã giao dịch", ngan_hang: "Ngân hàng",
  so_tai_khoan: "Số tài khoản", thoi_diem: "Thời điểm", loai: "Vào / ra", so_tien: "Số tiền",
  ma_tham_chieu: "Mã tham chiếu", ma_phieu: "Mã phiếu", bien_so: "Biển số", ten_tour: "Tour",
  ngay_di: "Ngày đi", ngay_ve: "Ngày về", km_dau: "Km đầu", km_cuoi: "Km cuối",
  doanh_thu: "Doanh thu", tien_dau: "Tiền dầu", so_lit: "Số lít", cau_duong: "Cầu đường",
  cong_tac_phi: "Công tác phí", the_4so: "Bốn số cuối thẻ", lit: "Số lít", mo_ta: "Diễn giải",
};

function DocChungTu() {
  const { user, toast } = useShell();
  const [meta, setMeta] = useState<any>(null);
  const [loai, setLoai] = useState("");
  const [ds, setDs] = useState<Ban[]>([]);
  const [mo, setMo] = useState<Ban | null>(null);
  const [so, setSo] = useState<Record<string, string>>({});
  const [dang, setDang] = useState(false);
  const [cl, setCl] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const m = await api<any>("/doc-chung-tu/meta");
      setMeta(m); if (!loai) setLoai(m.loai[0]?.ma || "");
      const d = await api<any>("/doc-chung-tu");
      setDs(d.rows);
      setCl(await api<any>("/doc-chung-tu/chat-luong"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast, loai]);
  useEffect(() => { load(); }, [load]);

  const tai = async (f: File | null) => {
    if (!f || !loai) return;
    setDang(true);
    try {
      const fd = new FormData(); fd.append("loai", loai); fd.append("tep", f);
      const r = await fetch("/api/v1/doc-chung-tu/doc", {
        method: "POST", body: fd,
        headers: { Authorization: `Bearer ${localStorage.getItem("vtos_token") || ""}` },
      });
      const d = await r.json();
      if (!r.ok) throw { message: d?.detail || "Không đọc được" };
      toast(d.message);
      setMo(d); setSo({ ...d.so_may_doc });
      await load();
    } catch (e: any) { toast(errMsg(e), true); }
    setDang(false);
  };

  const xacNhan = async () => {
    if (!mo) return;
    setDang(true);
    try {
      const d = await api<any>(`/doc-chung-tu/${mo.id}/xac-nhan`, { method: "POST", json: { so } });
      toast(`Đã ghi vào hệ thống. Bạn sửa ${d.so_o_da_sua}/${d.so_o} ô máy đọc.`);
      setMo(null); await load();
    } catch (e) { toast(errMsg(e), true); }
    setDang(false);
  };

  const boBan = async () => {
    if (!mo) return;
    const ly_do = prompt("Vì sao bỏ bản này? (máy đọc sai / chứng từ không dùng / …)") || "";
    if (!ly_do.trim()) return;
    try {
      await api(`/doc-chung-tu/${mo.id}/bo`, { method: "POST", json: { ly_do } });
      toast("Đã bỏ bản nháp"); setMo(null); await load();
    } catch (e) { toast(errMsg(e), true); }
  };

  const truong: string[] = meta?.loai?.find((l: any) => l.ma === mo?.loai)?.truong || [];
  const chuaDoc = new Set(mo?.truong_khong_doc_duoc || []);

  return (
    <div className="wrap">
      <h1>Đọc chứng từ ảnh ra số</h1>
      <p className="muted">
        Máy soạn nháp, người xác nhận. Số máy đọc <b>không nằm ở bất kỳ báo cáo nào</b> cho tới khi
        có một lần bấm của người – và lần bấm đó đi đúng cửa nhập tay, qua đúng bộ kiểm của nó.
      </p>

      <div className="card">
        <h3>1. Tải ảnh chứng từ</h3>
        <div className="row">
          <select value={loai} onChange={(e) => setLoai(e.target.value)}>
            {meta?.loai?.map((l: any) => <option key={l.ma} value={l.ma}>{l.ten}</option>)}
          </select>
          <input type="file" accept="image/*,application/pdf" disabled={dang}
                 onChange={(e) => tai(e.target.files?.[0] || null)} />
        </div>
        {meta?.cam_doc?.length ? (
          <p className="muted small">
            Không đọc bằng máy: {meta.cam_doc.map((c: any) => c.ly_do).join(" · ")}. Hai loại này
            nhập tay; tệp gốc vẫn lưu vào kho hồ sơ nhân sự với phân quyền riêng.
          </p>
        ) : null}
      </div>

      {mo ? (
        <div className="card">
          <h3>2. Kiểm lại số máy đọc — {mo.ten_loai}</h3>
          {mo.mo_hinh ? null : (
            <p className="warn">Chưa cấu hình mô hình đọc ảnh – biểu để trống, mời nhập tay.
              Ảnh vẫn đã lưu vào kho chứng từ và gắn với dòng này.</p>
          )}
          {mo.ghi_chu_may ? <p className="muted small">Máy ghi chú: {mo.ghi_chu_may}</p> : null}
          <table className="tbl">
            <tbody>
              {truong.map((t) => (
                <tr key={t}>
                  <td className="lbl">{TEN_O[t] || t}</td>
                  <td>
                    <input value={so[t] ?? ""} onChange={(e) => setSo({ ...so, [t]: e.target.value })}
                           className={chuaDoc.has(t) ? "chua-doc" : ""} />
                  </td>
                  <td className="muted small">
                    {chuaDoc.has(t) ? <Tag cls="warn">máy không đọc được</Tag>
                      : (so[t] ?? "") !== (mo.so_may_doc[t] ?? "")
                        ? <Tag>bạn đã sửa (máy đọc: {mo.so_may_doc[t] || "—"})</Tag> : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            <button onClick={xacNhan} disabled={dang}>Xác nhận và ghi vào hệ thống</button>
            <button onClick={boBan} className="ghost">Bỏ bản này</button>
            <button onClick={() => setMo(null)} className="ghost">Để lại, xem sau</button>
          </div>
          <p className="muted small">
            Bấm xác nhận là bạn chịu trách nhiệm về con số này, y như khi gõ tay. Ô nào máy không đọc
            được thì để trống – <b>đừng điền 0</b>, vì &quot;chưa có số&quot; và &quot;bằng 0&quot; là hai chuyện khác nhau.
          </p>
        </div>
      ) : null}

      <div className="card">
        <h3>Hàng chờ xác nhận ({ds.length})</h3>
        {ds.length === 0 ? <p className="muted">Không có bản nào đang chờ.</p> : (
          <table className="tbl">
            <thead><tr><th>Loại</th><th>Máy đọc được</th><th>Người tải</th><th>Lúc</th><th></th></tr></thead>
            <tbody>
              {ds.map((b) => (
                <tr key={b.id}>
                  <td>{b.ten_loai}</td>
                  <td>{Object.values(b.so_may_doc || {}).filter(Boolean).slice(0, 3).join(" · ") || "—"}
                    {b.truong_khong_doc_duoc?.length
                      ? <> <Tag cls="warn">thiếu {b.truong_khong_doc_duoc.length} ô</Tag></> : null}</td>
                  <td>{b.boi}</td>
                  <td>{fmtDT(b.luc)}</td>
                  <td><button className="ghost"
                              onClick={() => { setMo(b); setSo({ ...b.so_may_doc }); }}>Mở</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {cl ? (
        <div className="card">
          <h3>Máy đọc đúng đến đâu</h3>
          <p>
            {cl.du_du_lieu
              ? <>Trong {cl.so_ngay} ngày, người phải sửa <b>{(cl.ty_le * 100).toFixed(1)}%</b> số ô
                  máy đọc ({cl.so_o_sua}/{cl.so_o} ô, {cl.so_ban} bản).</>
              : cl.ghi_chu}
          </p>
          {cl.de_xuat_ha_muc ? (
            <p className="warn">
              Vượt ngưỡng {(cl.nguong_ha_muc * 100).toFixed(0)}% – đề xuất <b>hạ mức AI</b> cho nhóm
              việc đọc chứng từ. Khi máy đọc kém đi thì thứ phải giảm là mức tự chủ của máy, không
              phải mức chú ý của người.
            </p>
          ) : null}
        </div>
      ) : null}

      <style jsx>{`
        .wrap { padding: 16px; max-width: 900px; }
        .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; margin: 14px 0; }
        .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin: 8px 0; }
        .tbl { width: 100%; border-collapse: collapse; }
        .tbl td, .tbl th { border-bottom: 1px solid #f1f5f9; padding: 6px 8px; text-align: left; }
        .lbl { width: 190px; color: #475569; }
        input { padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; width: 100%; }
        input.chua-doc { background: #fffbeb; border-color: #fbbf24; }
        button { padding: 7px 12px; border-radius: 8px; border: 1px solid #0f172a;
                 background: #0f172a; color: #fff; cursor: pointer; }
        button.ghost { background: #fff; color: #0f172a; border-color: #cbd5e1; }
        .muted { color: #64748b; }
        .small { font-size: 12px; }
        .warn { color: #92400e; background: #fffbeb; padding: 8px 10px; border-radius: 8px; }
      `}</style>
    </div>
  );
}

export default function Page() {
  return <Shell><DocChungTu /></Shell>;
}
