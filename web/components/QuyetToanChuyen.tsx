"use client";
/** QT-1 · TỜ QUYẾT TOÁN CHUYẾN THEO MẪU 2 – Chủ tịch chốt mẫu ngày 13/10/2026.
 *
 * Ô NÀO CỘNG RA ĐƯỢC THÌ KHÔNG CÓ Ô ĐỂ GÕ.
 *
 * Đo trên hai bộ hồ sơ thật ngày 13/10/2026, mỗi bộ 8 trang (tờ quyết toán có chữ ký + ảnh đồng hồ
 * đầu/cuối + hoá đơn dầu + biên lai ngân hàng + vé gửi xe). CẢ HAI BỘ CỘNG ĐÚNG TỔNG CUỐI. Nhưng:
 *
 *   · 50F-034.71 (07–11/10): ô «TỔNG TÀI XẾ CHI» viết tay 1.360.000, trong khi công thức IN NGAY
 *     CẠNH NÓ là "phí gửi xe + phí khác" = 360.000. Người viết cộng nhầm cả công tác phí – mà công
 *     tác phí đã nằm ở «TỔNG CÔNG TY CHI» bên dưới. Tổng cuối vẫn đúng nên không ai thấy.
 *
 *   · 50F-046.22 (06–12/10): tờ giấy ghi km đầu 197.935; ảnh đồng hồ và tin Zalo của tài xế đều
 *     197.435. 199.768 − 197.435 = 2.333 km, đúng bằng «TỔNG KM TOUR» ghi trên CHÍNH TỜ ẤY.
 *     Lệch 500 km, và 500 km ấy đi thẳng vào phép tính chi phí mỗi km.
 *
 * Nên: ba ô tổng, tổng km và số ngày đều do MÁY CỘNG, in với dấu ⌁ và không có <input>. Con số
 * viết tay trên giấy gõ vào ô «tổng km ghi trên giấy» – một NGUỒN THỨ HAI để máy đối chiếu, KHÔNG
 * lưu lại. Hai nguồn lệch nhau thì phải có người nhìn, chứ không phải máy lặng lẽ chọn một.
 *
 * HAI CÂU HỎI KHÁC NHAU VỀ MỘT KHOẢN CHI. `ben_chiu` trả lời "ai gánh khoản này khi quyết toán với
 * chủ xe hợp tác". `tra_bang` trả lời "ai bỏ tiền ra tại chỗ". Xe của Vietourist thì ben_chiu luôn
 * là Vietourist, nhưng tiền có thể là tài xế ứng tiền mặt, thẻ công ty, hay trừ thẳng tài khoản
 * (ePass). Mẫu 2 tách TỔNG TÀI XẾ CHI với TỔNG CÔNG TY CHI theo CÂU HỎI THỨ HAI. Vì vậy bảng khoản
 * chi ở đây có ô khai `tra_bang`: không có ô ấy thì lời chặn "chưa khai ai trả" là một ngõ cụt.
 *
 * MÀN HÌNH KHÔNG CHÉP LẠI BẢNG VAI. Hiện nút nào, ký bước nào – máy chủ trả trong `quyen`, sinh ra
 * từ chính `co_the_ky` mà cửa ký gọi khi ghi thật. Chép lại là dùng hai bảng vai, và hai bảng vai
 * thì sớm muộn cũng nói khác nhau: nút hiện ra rồi bấm vào ăn 403, hoặc nút ẩn đi trong khi người
 * ấy ký được.
 *
 * Màn hình xếp ĐÚNG THỨ TỰ TỜ GIẤY, từ trên xuống: Đội xe cầm giấy gõ một mạch, không nhảy qua
 * nhảy lại tìm ô. Đó là lý do khối này không gom các ô tiền lại một chỗ cho "gọn".
 */
import { useCallback, useEffect, useState } from "react";
import { api, vnd, soTien } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

type Lech = { muc: string; o: string; noi: string };
type Ky = { buoc: string; nguoi: string; luc: string | null };
type Dong = {
  id: number; kind: string; kind_ten: string; amount: number | null; lit: number | null;
  chung_tu: string; tra_bang: string; tra_bang_ten: string;
};
type To = {
  id: number; ma_phieu: string; bien_so: string; ma_xe: string;
  ten_tour: string; hdv: string; hanh_trinh: string;
  ngay_di: string; ngay_ve: string; so_ngay: number | null;
  km_dau: number | null; km_cuoi: number | null; km_tour: number | null;
  tam_ung: number | null; hoan_tra: number | null; chi_them: number | null; phu_thu: number | null;
  bc_tinh_trang_xe: string;
  tong: {
    tai_xe_chi: number; cong_ty_chi: number; chua_khai_ai_tra: number;
    tong_chi_phi_tour: number; tai_xe_con_nhan: number; so_khoan: number;
  };
  chi_phi: Dong[];
  tra_bang_danh_muc: Record<string, string>;
  qt_trang_thai: string; qt_ten_trang_thai: string; qt_tra_lai_ly_do: string;
  ky: Ky[]; diem_lech: Lech[];
  quyen: { ghi: boolean; ky: boolean; buoc_ky_duoc: string[]; vi_sao_chua_ky: Record<string, string> };
};

const TEN_BUOC: Record<string, string> = {
  dieu_hanh: "Điều hành", ke_toan: "Kế toán", tgd: "T. Giám đốc",
};

/** Ô máy cộng. KHÔNG phải <input> – không có chỗ để gõ sai, nên cũng không có chỗ để cộng nhầm. */
function OMay({ nhan, gt, duoi }: { nhan: string; gt: React.ReactNode; duoi?: string }) {
  return (
    <div>
      <label style={{ marginBottom: 0 }}>
        {nhan} <span className="tag" title="máy cộng ra từ các dòng – không gõ được">⌁ máy cộng</span>
      </label>
      <div style={{
        padding: "7px 9px", border: "1px dashed var(--line)", borderRadius: 6,
        background: "var(--panel2)", fontFamily: "var(--vtos-font-mono)",
        fontVariantNumeric: "tabular-nums", fontSize: "calc(13.5/14*1rem)",
      }}>{gt}</div>
      {duoi && <small className="muted">{duoi}</small>}
    </div>
  );
}

export default function QuyetToanChuyen({ tripId, toast }: {
  tripId: number; toast?: (m: string, loi?: boolean) => void;
}) {
  const [d, setD] = useState<To | null>(null);
  const [loi, setLoi] = useState("");
  const [giay, setGiay] = useState<string>("");          // tổng km VIẾT TAY trên tờ giấy
  const [f, setF] = useState<Record<string, any>>({});
  const [dang, setDang] = useState(false);

  const tai = useCallback(async () => {
    try {
      const q = soTien(giay) === null ? "" : `?km_tour_tren_giay=${soTien(giay)}`;
      const o: To = await api(`/fleet/quyet-toan-chuyen/${tripId}${q}`);
      setD(o); setLoi("");
      setF({
        hdv: o.hdv, hanh_trinh: o.hanh_trinh, km_dau: o.km_dau ?? "", km_cuoi: o.km_cuoi ?? "",
        tam_ung: o.tam_ung ?? "", hoan_tra: o.hoan_tra ?? "", chi_them: o.chi_them ?? "",
        phu_thu: o.phu_thu ?? "", bc_tinh_trang_xe: o.bc_tinh_trang_xe,
      });
    } catch (e) { setLoi(errMsg(e)); }
  }, [tripId, giay]);

  useEffect(() => { tai(); }, [tai]);

  const goi = async (duong: string, json?: any, pp = "POST", xong?: string) => {
    setDang(true);
    try {
      await api(duong, { method: pp, json });
      await tai();
      if (xong) toast?.(xong);
    } catch (e) { const m = errMsg(e); setLoi(m); toast?.(m, true); }
    finally { setDang(false); }
  };

  if (loi && !d) return <div className="panel"><div className="gate fail">{loi}</div></div>;
  if (!d) return <div className="panel"><p className="muted">Đang tải tờ quyết toán…</p></div>;

  const sua = d.quyen.ghi;
  const chan = d.diem_lech.filter((x) => x.muc === "do");
  const t = d.tong;
  const o = (k: string) => ({
    value: f[k] ?? "", onChange: (e: any) => setF({ ...f, [k]: e.target.value }),
    disabled: !sua || dang,
  });

  return (
    <div className="panel">
      <h2>Quyết toán chuyến · Mẫu 2 {d.ma_phieu && <span className="muted">#{d.ma_phieu}</span>}{" "}
        <Tag cls={d.qt_trang_thai === "da_duyet" ? "ok" : d.qt_trang_thai === "tra_lai" ? "red" : "warn"}>
          {d.qt_ten_trang_thai}</Tag></h2>
      <p className="muted">{d.bien_so}{d.ma_xe ? ` · ${d.ma_xe}` : ""} · {d.ten_tour}.
        Tài xế ký trên giấy, Đội xe nhập hộ. Ô có dấu <b>⌁</b> là ô <b>máy cộng ra</b> – không gõ
        được, và đó đúng là chỗ tờ giấy hay cộng nhầm.</p>

      {d.qt_tra_lai_ly_do && <div className="gate fail"><b>Bị trả lại:</b> {d.qt_tra_lai_ly_do}</div>}
      {loi && <div className="gate fail">{loi}</div>}

      {d.diem_lech.map((x, i) => (
        <div key={i} className={`gate ${x.muc === "do" ? "fail" : ""}`}>
          <Tag cls={x.muc === "do" ? "red" : "warn"}>{x.muc === "do" ? "chặn ký" : "phải đọc"}</Tag>{" "}
          {x.noi}
        </div>
      ))}

      <h3>Chuyến</h3>
      <div className="grid2">
        <label>Hướng dẫn viên<input {...o("hdv")} /></label>
        <label>Hành trình<input {...o("hanh_trinh")} placeholder="Đà Lạt – Nha Trang" /></label>
        <label>Số km đầu<input type="number" {...o("km_dau")} /></label>
        <label>Số km cuối<input type="number" {...o("km_cuoi")} /></label>
        <OMay nhan="Tổng km tour"
          gt={d.km_tour === null ? "— chưa đủ km đầu/cuối" : `${d.km_tour.toLocaleString("vi-VN")} km`} />
        <label>Tổng km <b>ghi trên giấy</b>
          <input type="number" value={giay} disabled={dang}
            onChange={(e) => setGiay(e.target.value)} placeholder="gõ con số viết tay để đối chiếu" />
          <small className="muted">Không lưu. Chỉ để máy so với km đầu/cuối – đây là phép bắt được
            lỗi 500 km của bộ 50F-046.22.</small></label>
        <OMay nhan="Số ngày" gt={d.so_ngay ?? "—"} duoi="ngày về − ngày đi + 1" />
        <div />
      </div>

      <h3>Khoản chi · ai bỏ tiền ra tại chỗ</h3>
      <p className="muted">Hai tổng của Mẫu 2 tách theo cột <b>Trả bằng</b> này, không theo
        «Bên chịu». Để trống nghĩa là <b>chưa khai</b>, không phải công ty trả.</p>
      {d.chi_phi.length === 0
        ? <div className="gate fail">Chưa có khoản chi nào. Thêm ở biểu <b>phiếu chuyến</b> bên trên.</div>
        : <div className="wrap"><table>
            <thead><tr><th>Khoản</th><th className="num">Số tiền</th><th className="num">Lít</th>
              <th>Chứng từ</th><th>Trả bằng</th></tr></thead>
            <tbody>
              {d.chi_phi.map((c) => (
                <tr key={c.id}>
                  <td>{c.kind_ten}</td>
                  <td className="num">{vnd(c.amount)}</td>
                  <td className="num">{c.lit ? c.lit.toLocaleString("vi-VN") : ""}</td>
                  <td>{c.chung_tu || <span className="muted">—</span>}</td>
                  <td style={{ minWidth: 190 }}>
                    {sua
                      ? <select value={c.tra_bang} disabled={dang}
                          onChange={(e) => goi(`/fleet/chuyen/${tripId}/chi-phi/${c.id}`,
                            { tra_bang: e.target.value }, "PUT", "Đã khai ai trả khoản này")}>
                          <option value="">— chưa khai —</option>
                          {Object.entries(d.tra_bang_danh_muc).map(([k, v]) =>
                            <option key={k} value={k}>{v}</option>)}
                        </select>
                      : (c.tra_bang_ten || <Tag cls="warn">chưa khai</Tag>)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table></div>}

      <h3>Tài xế ứng tiền mặt</h3>
      <div className="grid2">
        <OMay nhan="TỔNG TÀI XẾ CHI" gt={vnd(t.tai_xe_chi)}
          duoi="cộng các khoản khai là tài xế ứng tiền mặt – không cộng công tác phí" />
        <OMay nhan="Tài xế còn được nhận" gt={vnd(t.tai_xe_con_nhan)}
          duoi="tài xế chi + chi thêm − tạm ứng − hoàn trả (số âm = tài xế còn nợ công ty)" />
        <label>Tạm ứng<input type="number" {...o("tam_ung")} /></label>
        <label>Hoàn trả<input type="number" {...o("hoan_tra")} /></label>
        <label>Chi thêm<input type="number" {...o("chi_them")} /></label>
        <label>Phụ thu<input type="number" {...o("phu_thu")} /></label>
      </div>

      <h3>Tổng của tờ</h3>
      <div className="grid2">
        <OMay nhan="TỔNG CÔNG TY CHI" gt={vnd(t.cong_ty_chi)}
          duoi="thẻ công ty + trừ tài khoản công ty (ePass, chuyển khoản)" />
        <OMay nhan="TỔNG CHI PHÍ TOUR" gt={<b>{vnd(t.tong_chi_phi_tour)}</b>}
          duoi="tất cả khoản chi, bất kể ai ứng ra. Tạm ứng / hoàn trả / chi thêm KHÔNG nằm trong
                đây – đó là tiền đi qua tay tài xế, cộng vào là đếm hai lần vào giá vốn." />
      </div>

      <div className="grid2">
        <label>Đề xuất · báo cáo tình trạng xe
          <textarea rows={2} {...o("bc_tinh_trang_xe")} /></label>
        <div />
      </div>

      {sua && <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <button className="act teal" disabled={dang} style={{ margin: 0 }}
          onClick={() => goi(`/fleet/quyet-toan-chuyen/${tripId}`, {
            hdv: f.hdv, hanh_trinh: f.hanh_trinh, bc_tinh_trang_xe: f.bc_tinh_trang_xe,
            km_dau: soTien(f.km_dau), km_cuoi: soTien(f.km_cuoi),
            tam_ung: soTien(f.tam_ung), hoan_tra: soTien(f.hoan_tra),
            chi_them: soTien(f.chi_them), phu_thu: soTien(f.phu_thu),
            km_tour_tren_giay: soTien(giay),
          }, "PUT", "Đã lưu tờ quyết toán")}>Lưu</button>
        <button className="act" disabled={dang || chan.length > 0} style={{ margin: 0 }}
          title={chan.length ? "Còn điểm chặn chưa xử – xem các dòng đỏ ở trên" : ""}
          onClick={() => goi(`/fleet/quyet-toan-chuyen/${tripId}/gui`, undefined, "POST",
            "Đã gửi vào tuyến ký")}>Gửi vào tuyến ký</button>
      </div>}

      <h3>Tuyến ký</h3>
      <div className="kpis">
        <div className="kpi"><b style={{ fontSize: "1rem" }}>Tài xế</b>
          <span>đã ký trên giấy · ảnh đính kèm ở trên</span></div>
        {d.ky.map((k) => (
          <div key={k.buoc} className="kpi">
            <b style={{ fontSize: "1rem", color: k.nguoi ? "var(--teal)" : "var(--ink2)" }}>
              {TEN_BUOC[k.buoc] || k.buoc}</b>
            <span>{k.nguoi
              ? `${k.nguoi} · ${k.luc ? new Date(k.luc).toLocaleString("vi-VN") : ""}`
              : (d.quyen.vi_sao_chua_ky?.[k.buoc] || "chờ")}</span>
          </div>
        ))}
      </div>

      {d.quyen.buoc_ky_duoc.length > 0 && (
        <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
          {d.quyen.buoc_ky_duoc.map((b) => (
            <button key={b} className="act teal" disabled={dang} style={{ margin: 0 }}
              onClick={() => goi(`/fleet/quyet-toan-chuyen/${tripId}/ky`, { buoc: b }, "POST",
                `Đã ký bước ${TEN_BUOC[b] || b}`)}>Ký bước {TEN_BUOC[b] || b}</button>
          ))}
          <button className="act grey" disabled={dang} style={{ margin: 0 }} onClick={() => {
            const ly = window.prompt("Trả lại để sửa – ghi rõ phải sửa cái gì:");
            if (ly && ly.trim()) goi(`/fleet/quyet-toan-chuyen/${tripId}/tra-lai`, { ly_do: ly },
              "POST", "Đã trả lại để sửa");
          }}>Trả lại để sửa</button>
        </div>
      )}
      {d.quyen.buoc_ky_duoc.length > 0 && <p className="muted" style={{ marginTop: 8 }}>
        Trả lại sẽ <b>xoá hết chữ ký đã có</b> – giữ lại là giữ một chữ ký cho nội dung người ấy
        chưa từng đọc.</p>}
    </div>
  );
}
