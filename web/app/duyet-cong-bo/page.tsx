"use client";
import { useCallback, useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api } from "@/lib/api";
import { Tag } from "@/components/ui";

/** Duyệt công bố nhận xét — Đợt HD-DG3. Chủ tịch duyệt bố cục 16/10/2026.
 *
 *  ── ĐỦ CẢ HAI MỚI HIỆN ─────────────────────────────────────────────────────────────────────
 *  Một nhận xét lên hồ sơ hướng dẫn viên công khai khi khách ĐÃ ĐỒNG Ý và người có thẩm quyền
 *  ĐÃ DUYỆT. Màn hình này là vế thứ hai. Dòng nào khách chưa đồng ý thì KHÔNG có nút — không
 *  phải nút mờ, mà không có, vì một cái nút mờ vẫn mời người ta đi tìm cách bấm.
 *
 *  ── MÁY CHE THÌ PHẢI NÓI ĐANG CHE CHỖ NÀO ──────────────────────────────────────────────────
 *  Chủ tịch chọn nhãn người viết có tên tuyến. Hôm nay VTOS chưa có trường tuyến, nên máy chủ
 *  lùi về nhãn chỉ có tháng và trả kèm `ly_do_lui_nhan`. Màn hình IN RA lý do ấy. Che lén là
 *  cách chắc nhất để một ngày ai đó gỡ hàng rào đi mà không ai nhận ra.
 *
 *  ── KHÔNG TỰ TÍNH MỘT CON SỐ NÀO ───────────────────────────────────────────────────────────
 *  Ba ô đếm, số ngày chờ, nhãn người viết — máy chủ cộng hết. Tính lại ở đây là dựng công thức
 *  thứ hai, và ngày hai con số lệch nhau thì người dùng tin con số dễ đọc chứ không tin con số
 *  đúng.
 *
 *  ── GỠ LỆCH CHIỀU SO VỚI ĐĂNG, CỐ Ý ────────────────────────────────────────────────────────
 *  Đăng cần một trong ba người; gỡ thì ai trong ba cũng gỡ được ngay. Đăng nhầm thì sửa được
 *  bằng cách gỡ; không gỡ được mới là cái kẹt.
 */

const so = (v: any) => (v === null || v === undefined ? "—" : String(v));

function DuyetCongBo() {
  const [kq, setKq] = useState<any>(null);
  const [loi, setLoi] = useState("");
  const [dangBam, setDangBam] = useState<number | null>(null);
  const [lyDo, setLyDo] = useState<Record<number, string>>({});

  const tai = useCallback(() => {
    api("/cong-bo/hang-doi")
      .then((r: any) => { setKq(r); setLoi(""); })
      .catch((e: any) => { setKq(null); setLoi(e?.message || "Không đọc được hàng đợi"); });
  }, []);
  useEffect(() => { tai(); }, [tai]);

  const bam = async (id: number, duong: string, than: any) => {
    setDangBam(id);
    try {
      await api(`/cong-bo/${id}/${duong}`, { method: "POST", body: JSON.stringify(than) });
      tai();
    } catch (e: any) {
      setLoi(e?.message || "Không bấm được");
    } finally {
      setDangBam(null);
    }
  };

  const rows: any[] = kq?.rows || [];

  return (<>
    <h1>Duyệt công bố nhận xét</h1>
    <p className="muted">Một nhận xét chỉ hiện trên hồ sơ hướng dẫn viên công khai khi <b>đủ cả
      hai</b>: khách đã đồng ý, và người có thẩm quyền đã duyệt. Thiếu một trong hai thì không hiện.</p>

    {kq && !kq.ban_duyet_duoc && <div className="gate">
      Anh/chị đọc được hàng đợi này nhưng không bấm được. Quyền duyệt công bố thuộc Chủ tịch HĐQT,
      Tổng giám đốc, và người được cấp đích danh có thời hạn.
    </div>}
    {kq?.ban_duyet_bang === "cap_dich_danh" && <div className="gate">
      Anh/chị duyệt bằng <b>quyền cấp đích danh có thời hạn</b>, không phải bằng vai trò. Mỗi lần
      bấm đều ghi lại điều đó.
    </div>}
    {loi && <div className="gate fail">{loi}</div>}
    {kq?.luu_y && <div className="gate">{kq.luu_y}</div>}

    {kq && <div className="kpis">
      <div className="kpi"><b>{so(kq.dang_cho)}</b><span>Đang chờ duyệt</span></div>
      <div className="kpi"><b>{so(kq.cho_lau_nhat_ngay)}</b><span>Cái chờ lâu nhất (ngày)</span></div>
      <div className="kpi"><b>{so(kq.da_dang)}</b><span>Đã đăng</span></div>
      <div className="kpi"><b>{so(kq.da_rut)}</b><span>Khách đã rút</span></div>
    </div>}

    {/* Ba ô đếm để Chủ tịch quyết có cần thêm người duyệt hay không, sau khi nhìn số thật một
        tháng. Số ngày chờ tính từ lúc KHÁCH ĐỒNG Ý — con số cần đo là «người có quyền để nó nằm
        đấy bao lâu», không phải «nhận xét này cũ bao nhiêu». Máy chủ tính, màn hình chỉ in. */}

    <div className="panel wrap">
      <h2>Đang chờ duyệt</h2>
      {rows.length === 0 && <p className="muted">
        Chưa có nhận xét nào chờ duyệt. Lưu ý: <b>rỗng</b> không có nghĩa là <b>không ai khen</b> —
        hàng đợi chỉ chứa nhận xét có câu đồng ý mới của Đợt HD-DG3, và nhận xét thu trước đợt này
        không có câu ấy.
      </p>}
      {rows.map((r: any) => (
        <div key={r.danh_gia_id} className="wrap" style={{ borderTop: "1px solid var(--vtos-line)", paddingTop: 14, marginTop: 14 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <b>{r.hdv_ten}</b>
            <Tag cls="green">{so(r.diem)} điểm</Tag>
            <span className="muted">Khách đồng ý {r.dong_y_luc} · chờ {so(r.cho_ngay)} ngày</span>
          </div>
          <blockquote style={{ margin: "10px 0", padding: "12px 14px", background: "var(--vtos-info-bg)", borderRadius: 6 }}>
            {r.nhan_xet}
          </blockquote>
          <p className="muted">Đăng lên sẽ ghi người viết là <b>{r.nhan_nguoi_viet}</b>.</p>
          {r.ly_do_lui_nhan && <div className="gate">{r.ly_do_lui_nhan}</div>}
          {r.vuong_chong_vai
            ? <div className="gate fail">{r.vuong_chong_vai}</div>
            : kq?.ban_duyet_duoc && <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginTop: 8 }}>
                <button className="act teal" style={{ margin: 0 }} disabled={dangBam === r.danh_gia_id}
                        onClick={() => bam(r.danh_gia_id, "duyet", { dong_y: true })}>Đăng công khai</button>
                <input placeholder="Lý do nếu không đăng" value={lyDo[r.danh_gia_id] || ""}
                       onChange={(e) => setLyDo({ ...lyDo, [r.danh_gia_id]: e.target.value })} />
                <button className="act" style={{ margin: 0 }} disabled={dangBam === r.danh_gia_id}
                        onClick={() => bam(r.danh_gia_id, "duyet",
                          { dong_y: false, ly_do: lyDo[r.danh_gia_id] || "" })}>Không đăng</button>
                <span className="muted">Không đăng thì phải ghi lý do. Lý do vào sổ, không hiện cho khách.</span>
              </div>}
        </div>
      ))}
    </div>

    <div className="panel wrap">
      <h2>Câu đã hỏi khách, nguyên văn</h2>
      <p style={{ fontStyle: "italic" }}>{kq?.cau_hoi || "—"}</p>
      <p className="muted">Hai chữ <b>không kèm tên và thông tin liên hệ</b> là một hàng rào trong
        mã, không phải một lời hứa trong tài liệu: cửa công khai bị cấm in tên và số điện thoại
        người nhận xét, và có phép thử canh điều đó. Khách rút lúc nào cũng được, bằng đường dẫn
        trong chính email khảo sát — rút là <b>ngừng công khai</b>, không phải xoá: lời nhận xét
        vẫn ở sổ nội bộ và vẫn tính vào điểm hướng dẫn viên.</p>
    </div>
  </>);
}

export default function Page() { return <Shell><DuyetCongBo /></Shell>; }
