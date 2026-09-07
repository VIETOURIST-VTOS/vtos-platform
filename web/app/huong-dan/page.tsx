"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import DinhKem from "@/components/DinhKem";
import { api, vnd, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Phòng Hướng dẫn – màn hình của người điều phối, khi toàn bộ HDV là cộng tác viên.
 *
 *  Chữ dùng ở đây là "chào chuyến", không phải "phân công". Không phải chuyện chữ nghĩa: luật xét NỘI
 *  DUNG quan hệ chứ không xét tên hợp đồng, và màn hình này cùng dữ liệu của nó chính là nơi lưu bằng
 *  chứng về nội dung đó. Hạn 24 giờ vẫn còn, nhưng là hạn hiệu lực của LỜI CHÀO – quá hạn thì chuyến
 *  chào người khác, không phải hướng dẫn viên vi phạm. */
const TABS: [string, string][] = [["viec", "Việc cần làm"], ["hdv", "Đội ngũ HDV"], ["chao", "Chào chuyến"]];

function HuongDan() {
  const { user, toast } = useShell();
  const [tab, setTab] = useState("viec");
  const [tq, setTq] = useState<any>(null);
  const [hdv, setHdv] = useState<any>(null);
  const [can, setCan] = useState<any[]>([]);
  const [chao, setChao] = useState<any[]>([]);
  const [tepHdv, setTepHdv] = useState("");
  const canDieuPhoi = ["tp_hd", "tp_dh", "nv_dh", "hcns", "cntt"].includes(user?.role || "");

  const load = useCallback(async () => {
    try {
      setTq(await api("/huong-dan/tong-quan"));
      setHdv(await api("/huong-dan/hdv"));
      setCan(await api("/huong-dan/chuyen-can-hdv"));
      setChao(await api("/huong-dan/chao-chuyen"));
    } catch (e) { toast(errMsg(e), true); }
  }, [toast]);
  useEffect(() => { load(); }, [load]);

  if (!tq) return <p className="muted">Đang tải…</p>;
  return (<>
    <h1>Phòng Hướng dẫn</h1>
    <p className="muted">Toàn bộ hướng dẫn viên là <b>cộng tác viên</b>. Vì vậy màn hình này <b>chào chuyến</b> chứ
      không phân công: công ty chào tuyến, ngày và đơn giá; hướng dẫn viên nhận hoặc từ chối. Hạn 24 giờ là
      hạn hiệu lực của lời chào — quá hạn thì chuyến chào người khác, không ghi nhận ai vi phạm.</p>

    <div className="kpis">
      <div className="kpi"><b>{tq.hdv_dang_cong_tac}</b><span>HDV đang cộng tác</span></div>
      <div className="kpi"><b style={{ color: tq.du_dieu_kien < tq.hdv_dang_cong_tac ? "var(--red)" : undefined }}>
        {tq.du_dieu_kien}</b><span>đủ điều kiện hành nghề (cổng 13)</span></div>
      <div className="kpi"><b>{tq.the_sap_het_han}</b><span>thẻ hết hạn trong 60 ngày</span></div>
      <div className="kpi"><b style={{ color: tq.chuyen_chua_co_hdv ? "var(--red)" : undefined }}>
        {tq.chuyen_chua_co_hdv}</b><span>chuyến 30 ngày tới chưa có HDV</span></div>
      <div className="kpi"><b>{tq.cho_nhan_chuyen}</b><span>lời chào đang chờ trả lời</span></div>
      <div className="kpi"><b>{tq.tre_bao_cao}</b><span>trễ báo cáo tour quá 3 ngày</span></div>
    </div>

    <div style={{ display: "flex", gap: 8, margin: "10px 0", flexWrap: "wrap" }}>
      {TABS.map(([k, l]) => <button key={k} className={"act " + (tab === k ? "" : "grey")} style={{ margin: 0 }}
                                    onClick={() => setTab(k)}>{l}</button>)}
    </div>

    {tab === "viec" && <div className="panel wrap">
      <h2>Chuyến sắp khởi hành chưa có hướng dẫn viên</h2>
      <p className="muted">Xếp theo ngày gần nhất. Không hiện danh sách khách — chọn người cần biết tuyến,
        ngày và quy mô, không cần biết ai đi chuyến đó.</p>
      <table><thead><tr><th>Mã tour</th><th>Tuyến</th><th>Khởi hành</th><th>Số ngày</th>
        <th>Khách dự kiến</th><th>Còn lại</th></tr></thead>
        <tbody>{can.length ? can.map((c) => <tr key={c.tour_id}>
          <td><b>{c.code}</b></td><td>{c.name}</td><td>{fmtD(c.start_date)}</td>
          <td className="num">{c.so_ngay}</td><td className="num muted">{c.so_khach_du_kien || "—"}</td>
          <td>{c.con_lai_ngay <= 3 ? <Tag cls="red">{c.con_lai_ngay} ngày</Tag>
            : <span className="muted">{c.con_lai_ngay} ngày</span>}</td>
        </tr>) : <tr><td colSpan={6} className="muted">Mọi chuyến trong 30 ngày tới đều đã có người nhận.</td></tr>}</tbody></table>
    </div>}

    {tab === "hdv" && hdv && <>
      <div className="panel wrap">
        <h2>Đội ngũ hướng dẫn viên</h2>
        <p className="muted">{hdv.ghi_chu} Ba điều kiện hiện thành ba cột riêng, không gộp thành một chữ
          &quot;đạt&quot; — người điều phối phải biết thiếu cái gì để đi đòi cái đó.</p>
        <table><thead><tr><th>Mã</th><th>Họ tên</th><th>Thẻ HDV</th><th>Hạn thẻ</th><th>Hội viên</th>
          <th>Hợp đồng cộng tác</th><th>Hạn mức ứng</th><th>Hành nghề</th><th></th></tr></thead>
          <tbody>{hdv.rows.map((h: any) => <tr key={h.id} style={{ opacity: h.dang_lam ? 1 : 0.55 }}>
            <td className="mono">{h.code}</td><td><b>{h.full_name}</b><div className="muted">{h.phone}</div></td>
            <td className="mono">{h.the_so || <Tag cls="red">chưa có</Tag>}
              <div className="muted">{h.the_loai === "quoc_te" ? "Quốc tế" : h.the_loai === "noi_dia" ? "Nội địa" : ""}</div></td>
            <td>{fmtD(h.the_het_han)}{h.sap_het_han && <div><Tag cls="warn">còn {h.con_lai_ngay} ngày</Tag></div>}</td>
            <td>{h.hoi_vien ? <Tag cls="ok">có</Tag> : <Tag cls="red">chưa</Tag>}</td>
            <td>{h.hop_dong_cong_tac ? <Tag cls="ok">đã ký</Tag> : <Tag cls="red">chưa ký</Tag>}</td>
            <td className="num muted">{h.han_muc_tam_ung ? vnd(h.han_muc_tam_ung) : "—"}</td>
            <td>{h.du_dieu_kien ? <Tag cls="ok">đủ điều kiện</Tag> : <Tag cls="red">{h.vi_sao}</Tag>}</td>
            <td><button className="act grey" style={{ margin: 0 }} onClick={() => setTepHdv(h.code)}>Hồ sơ</button></td>
          </tr>)}</tbody></table>
      </div>
      {tepHdv && <DinhKem doiTuong="nhan_su" doiTuongId={tepHdv} loai="hop_dong"
        tieuDe={`Hồ sơ hành nghề – ${tepHdv}`}
        goi={"Thẻ hướng dẫn viên (hai mặt), hợp đồng cộng tác và phụ lục đơn giá, thẻ hội viên tổ chức " +
             "xã hội – nghề nghiệp, chứng nhận bảo hiểm tai nạn. Đây là bộ hồ sơ trả lời cơ quan quản lý " +
             "khi bị hỏi về một chuyến dẫn cụ thể."} />}
    </>}

    {tab === "chao" && <div className="panel wrap">
      <h2>Chào chuyến và tình trạng nhận</h2>
      <p className="muted">Cột &quot;quá hạn&quot; nghĩa là lời chào hết hiệu lực và chuyến nên chào người
        khác — không phải hướng dẫn viên vi phạm. Khác biệt đó là khác biệt giữa quan hệ dịch vụ và quan
        hệ lao động, nên nó nằm trong dữ liệu chứ không chỉ nằm trong lời nói.</p>
      <table><thead><tr><th>Tour</th><th>HDV</th><th>Khởi hành</th><th>Ngày</th><th>Đơn giá</th>
        <th>Thù lao</th><th>Tình trạng</th><th>Sau tour</th></tr></thead>
        <tbody>{chao.length ? chao.map((c) => <tr key={c.id}>
          <td><b>{c.tour_code}</b><div className="muted">{c.tour_name}</div></td>
          <td>{c.hdv}</td><td>{fmtD(c.khoi_hanh)}</td><td className="num">{c.so_ngay}</td>
          <td className="num muted">{vnd(c.don_gia)}{c.le_tet && <div><Tag cls="warn">lễ Tết ×2</Tag></div>}</td>
          <td className="num"><b>{vnd(c.thu_lao)}</b></td>
          <td>{c.trang_thai === "da_xac_nhan" ? <Tag cls="ok">đã nhận</Tag>
            : c.trang_thai === "huy" ? <Tag cls="muted">đã hủy</Tag>
              : c.loi_chao_qua_han ? <Tag cls="warn">lời chào quá hạn – chào người khác</Tag>
                : <Tag>đang chờ trả lời</Tag>}
            <div className="muted">{fmtDT(c.chao_luc)}</div></td>
          <td>{c.da_bao_cao ? <Tag cls="ok">đã báo cáo</Tag> : c.tre_bao_cao ? <Tag cls="red">trễ báo cáo</Tag> : <span className="muted">—</span>}
            {!c.da_hoan_ung && <div><Tag cls="warn">chưa hoàn ứng</Tag></div>}
            {c.treo_chao_moi && <div className="muted">đang treo chào chuyến mới</div>}</td>
        </tr>) : <tr><td colSpan={8} className="muted">Chưa có lời chào nào.</td></tr>}</tbody></table>
      {!canDieuPhoi && <p className="muted">Anh/chị đang xem ở chế độ chỉ đọc.</p>}
    </div>}
  </>);
}

export default function Page() { return <Shell><HuongDan /></Shell>; }
