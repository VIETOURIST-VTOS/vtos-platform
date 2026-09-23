"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** Đóng góp doanh thu của Marketing – nhóm 2.7.
 *
 *  ĐỘ PHỦ ĐỨNG TRƯỚC MỌI CON SỐ KHÁC, và đó là quyết định thiết kế chính của màn hình này.
 *  Một bảng "doanh thu theo kênh" nhìn rất thuyết phục kể cả khi nó chỉ truy được nguồn của 12%
 *  doanh thu – người đọc không có cách nào biết, vì bảng nào cũng cộng đủ 100% phần nó thấy. Nên
 *  khối đầu tiên của màn hình không phải bảng xếp hạng kênh, mà là câu "trong kỳ này truy được
 *  nguồn của bao nhiêu phần trăm doanh thu". Đọc con số ấy trước thì mới biết các bảng dưới đáng
 *  tin tới đâu.
 *
 *  BA THỨ KHÁC CŨNG KHÔNG ĐƯỢC GIẤU, mỗi thứ một khối riêng:
 *    – chi Marketing chưa gắn chiến dịch (bảng chiến dịch còn thiếu bấy nhiêu tiền chi)
 *    – booking mà hai đường truy nguồn nói khác nhau
 *    – booking bị nhiều lead cùng nhận (mức nhiễu của phép khớp theo số điện thoại)
 */

const MANG: [string, string][] = [["", "Cả ba luồng"], ["le", "Tour lẻ"], ["doan", "Tour đoàn"],
                                  ["dich_vu_le", "Dịch vụ lẻ"]];
const TEN_DUONG: Record<string, string> = {
  lead: "Qua lead (Marketing nhập)", booking: "Ô ghi trên booking", khong_ro: "Chưa rõ nguồn",
};

function kyMacDinh() {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, "0")}`;
}

/** Thu trên mỗi đồng chi. Chưa gắn đồng chi nào thì hiện gạch, KHÔNG hiện 0 và không chia cho 0 –
 *  "chưa gắn chi" khác hẳn "chi mà không thu được gì". */
function ThuTrenChi({ x }: { x: number | null | undefined }) {
  if (x === null || x === undefined) return <span className="muted">–</span>;
  return <b>{x.toFixed(1)}×</b>;
}

function DongGopMarketing() {
  const { user, toast } = useShell();
  const [ky, setKy] = useState(kyMacDinh());
  const [mang, setMang] = useState("");
  const [d, setD] = useState<any>(null);
  const [cd, setCd] = useState<any>(null);
  const [hienChuaRo, setHienChuaRo] = useState(false);
  const [gan, setGan] = useState<any>(null);
  const ganDuoc = ["chutich", "tgd", "ptgd_mkt", "cntt", "nv_mkt"].includes(user?.role || "");

  const load = useCallback(() => {
    const q = `ky=${ky}${mang ? `&mang=${mang}` : ""}`;
    api(`/dong-gop-marketing/thang?${q}`).then(setD).catch((x) => { toast(errMsg(x), true); setD(null); });
  }, [ky, mang]);                     // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [load]);

  const luuGan = async () => {
    if (!gan) return;
    try {
      const r = await api("/dong-gop-marketing/gan-nguon", { method: "POST", json: {
        booking_id: gan.booking_id, kenh: gan.kenh,
        chien_dich_id: gan.chien_dich_id ? Number(gan.chien_dich_id) : null, ly_do: gan.ly_do } });
      toast(r.message || "Đã gắn nguồn"); setGan(null); load();
    } catch (x) { toast(errMsg(x), true); }
  };

  const moChienDich = async (id: number) => {
    try { setCd(await api(`/dong-gop-marketing/chien-dich/${id}?ky=${ky}`)); }
    catch (x) { toast(errMsg(x), true); }
  };

  const phu = d?.do_phu;
  const tyLe = phu?.ty_le === null || phu?.ty_le === undefined ? null : Math.round(phu.ty_le * 100);

  return (<>
    <h1>Đóng góp doanh thu của Marketing</h1>

    <div className="panel">
      <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Kỳ<br /><input type="month" value={ky} onChange={(e) => { setCd(null); setKy(e.target.value); }} /></label>
        <label>Luồng<br /><select value={mang} onChange={(e) => { setCd(null); setMang(e.target.value); }}>
          {MANG.map(([v, t]) => <option key={v} value={v}>{t}</option>)}</select></label>
      </div>
    </div>

    {!d ? <div className="panel"><p className="muted">Đang tải…</p></div> : <>

      {/* ĐỘ PHỦ ĐỨNG TRƯỚC – xem chú thích đầu tệp. */}
      <div className="panel">
        <h2>Truy được nguồn bao nhiêu phần doanh thu kỳ {d.ky}</h2>
        <p style={{ fontSize: 24, margin: "4px 0" }}>
          {tyLe === null ? <span className="muted">Kỳ này chưa có doanh thu nào</span>
            : <><b>{tyLe}%</b> <small style={{ fontSize: 15 }}>
              — {vnd(phu.truy_duoc_nguon)} đ trên tổng {vnd(d.tong_doanh_thu)} đ</small></>}
        </p>
        {!!phu.so_booking_chua_ro && <p><Tag cls="warn">
          {phu.so_booking_chua_ro} booking chưa rõ nguồn – {vnd(phu.chua_ro_nguon)} đ</Tag>{" "}
          <button className="act" onClick={() => setHienChuaRo(!hienChuaRo)}>
            {hienChuaRo ? "Ẩn danh sách" : "Xem và gắn nguồn"}</button></p>}
        <p className="muted"><b>Đọc con số này trước.</b> Mọi bảng bên dưới chỉ chia phần doanh thu
          đã truy được nguồn. Truy được càng ít thì bảng xếp hạng kênh càng nói được ít, dù nhìn nó
          vẫn cộng đủ 100% phần nó thấy.</p>
        <div className="wrap"><table>
          <thead><tr><th>Biết nguồn nhờ đường nào</th><th className="num">Booking</th><th className="num">Doanh thu</th></tr></thead>
          <tbody>{Object.entries(d.theo_duong || {}).map(([k, v]: any) => <tr key={k}>
            <td>{TEN_DUONG[k] || k}</td><td className="num">{v.so_booking}</td><td className="num">{vnd(v.tien)}</td></tr>)}
          </tbody></table></div>
        <p className="muted">{d.co_so}</p>

        {/* CỬA NHẬP DUY NHẤT CỦA MÀN HÌNH NÀY.
            Đặt ngay dưới con số độ phủ, cố ý: người ta chỉ biết một booking thiếu nguồn khi nhìn
            đúng bảng này, nên chỗ sửa phải ở ngay đây. Bắt họ nhớ mã rồi đi sang màn hình Booking
            gõ lại là cách chắc chắn để không ai sửa. */}
        {hienChuaRo && <div className="wrap" style={{ marginTop: 12 }}>
          <table><thead><tr><th>Mã</th><th>Khách</th><th>Chuyến</th><th>Kết thúc</th>
            <th className="num">Tiền</th>{ganDuoc && <th>Gắn nguồn</th>}</tr></thead>
            <tbody>{(phu.rows || []).map((r: any) => <tr key={r.booking_id}>
              <td className="mono">{r.ma}</td><td>{r.khach}</td><td className="mono">{r.tour_ma}</td>
              <td>{r.ket_thuc}</td><td className="num">{vnd(r.tien)}</td>
              {ganDuoc && <td><button className="act" onClick={() => setGan({ booking_id: r.booking_id, ma: r.ma, kenh: "", chien_dich_id: "", ly_do: "" })}>Gắn</button></td>}
            </tr>)}
            </tbody></table>
          <p className="muted">Cửa này chỉ <b>điền chỗ trống</b>. Booking đã có nguồn ghi sẵn, hoặc đã
            khớp với một lead, thì không sửa ở đây được — sửa một câu trả lời đã có phải làm ở màn
            hình Booking, nơi có nhật ký sửa đầy đủ.</p>
        </div>}
      </div>

      {gan && <div className="panel"><h2>Gắn nguồn cho booking {gan.ma}</h2>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
          <label>Kênh<br /><input value={gan.kenh} onChange={(e) => setGan({ ...gan, kenh: e.target.value })} placeholder="facebook, zalo, gioi thieu…" /></label>
          <label>Chiến dịch<br /><select value={gan.chien_dich_id} onChange={(e) => setGan({ ...gan, chien_dich_id: e.target.value })}>
            <option value="">— không gắn chiến dịch —</option>
            {(d.theo_chien_dich || []).map((c: any) => <option key={c.chien_dich_id} value={c.chien_dich_id}>{c.ma} – {c.ten}</option>)}
          </select></label>
          <label>Lý do (bắt buộc)<br /><input value={gan.ly_do} onChange={(e) => setGan({ ...gan, ly_do: e.target.value })} /></label>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="act orange" onClick={luuGan}>Lưu</button>{" "}
          <button className="act" onClick={() => setGan(null)}>Thôi</button></div>
        <p className="muted">Gắn nguồn là đổi con số đóng góp của một chiến dịch, tức là đổi cơ sở để
          đánh giá một khoản chi — nên phải ghi lý do, và mỗi lần gắn đều để lại một dòng nhật ký.</p>
      </div>}

      <div className="panel">
        <p><Tag cls="warn">Lưu ý khi đọc tỷ lệ thu trên chi</Tag></p>
        <p className="muted">{d.canh_bao_lech_ky}</p>
      </div>

      {/* THEO CHIẾN DỊCH */}
      <div className="panel wrap"><h2>Theo chiến dịch</h2>
        <table><thead><tr>
          <th>Mã</th><th>Chiến dịch</th><th className="num">Doanh thu</th><th className="num">Booking</th>
          <th className="num">Chi thực tế</th><th className="num">Chi kế hoạch</th><th className="num">Thu / chi</th>
        </tr></thead>
          <tbody>{(d.theo_chien_dich || []).map((r: any) => <tr key={r.chien_dich_id}>
            <td className="mono"><a href="#" onClick={(e) => { e.preventDefault(); moChienDich(r.chien_dich_id); }}>{r.ma}</a></td>
            <td>{r.ten}</td>
            <td className="num">{vnd(r.tien)}</td>
            <td className="num">{r.so_booking}</td>
            <td className="num">{r.chi_thuc_te ? vnd(r.chi_thuc_te) : <span className="muted">chưa gắn</span>}</td>
            <td className="num">{r.chi_ke_hoach ? vnd(r.chi_ke_hoach) : <span className="muted">–</span>}</td>
            <td className="num"><ThuTrenChi x={r.thu_tren_chi} /></td>
          </tr>)}
          {!(d.theo_chien_dich || []).length && <tr><td colSpan={7} className="muted">Kỳ này chưa có booking nào gắn được chiến dịch.</td></tr>}
          </tbody></table>
        <p className="muted">Chiến dịch <b>có chi mà không có doanh thu</b> vẫn nằm trong bảng này với
          doanh thu bằng 0 – đó thường là nhóm đáng xem nhất, và nó sẽ không tự hiện ra nếu chỉ duyệt
          theo booking.</p>
      </div>

      {/* CHI MARKETING CỦA KỲ */}
      <div className="panel"><h2>Chi Marketing kỳ {d.ky}</h2>
        {!d.chi_marketing.co_ngan_sach
          ? <p><Tag cls="warn">Kỳ này chưa có ngân sách Marketing nào được lập, nên chưa có số chi để so.</Tag></p>
          : <>
            <p>Tổng chi <b>{vnd(d.chi_marketing.tong_chi)}</b> đ trên {d.chi_marketing.so_dong} dòng.</p>
            {!!d.chi_marketing.chi_chua_gan && <p><Tag cls="warn">
              {vnd(d.chi_marketing.chi_chua_gan)} đ chưa gắn chiến dịch</Tag></p>}
            <p className="muted">Phần chưa gắn <b>không được chia đều</b> cho các chiến dịch. Chia đều
              là đoán: một dòng chi có thể là của một chiến dịch, cũng có thể là chi chung cả tháng,
              và không ai ở đây biết là cái nào. Gắn chiến dịch cho từng dòng ở màn hình <b>Ngân sách
              &amp; chiến dịch</b> thì bảng trên đầy dần lên.</p>
          </>}
      </div>

      {/* THEO KÊNH */}
      <div className="panel wrap"><h2>Theo kênh</h2>
        <table><thead><tr><th>Kênh</th><th className="num">Doanh thu</th><th className="num">Booking</th><th className="num">Khách</th></tr></thead>
          <tbody>{(d.theo_kenh || []).map((r: any) => <tr key={r.kenh}>
            <td>{r.kenh}</td><td className="num">{vnd(r.tien)}</td>
            <td className="num">{r.so_booking}</td><td className="num">{r.so_khach}</td></tr>)}
          </tbody></table></div>

      {/* HAI ĐƯỜNG BẤT ĐỒNG */}
      {!!d.bat_dong?.so_dong && <div className="panel wrap">
        <h2>Hai đường truy nguồn nói khác nhau</h2>
        <p><Tag cls="warn">{d.bat_dong.so_dong} booking</Tag></p>
        <p className="muted">Số chính ở các bảng trên đã lấy theo <b>đường lead</b> đúng luật anh Tuấn
          chốt 23/9. Những dòng dưới đây liệt kê ra để có người đi soát, chứ không phải để bỏ đi.</p>
        <table><thead><tr><th>Mã booking</th><th>Khách</th><th>Kết thúc</th>
          <th>Lead nói</th><th>Booking ghi</th><th className="num">Tiền</th></tr></thead>
          <tbody>{d.bat_dong.rows.map((r: any) => <tr key={r.booking_id}>
            <td className="mono">{r.ma}</td><td>{r.khach}</td><td>{r.ket_thuc}</td>
            <td className="mono">{r.theo_lead}</td><td className="mono">{r.theo_booking}</td>
            <td className="num">{vnd(r.tien)}</td></tr>)}
          </tbody></table></div>}

      {!!d.nhieu_lead_mot_booking && <div className="panel">
        <p><Tag cls="warn">{d.nhieu_lead_mot_booking} booking bị nhiều lead cùng nhận</Tag></p>
        <p className="muted">Lead khớp với booking theo số điện thoại, nên một khách gọi ba lần qua ba
          kênh sẽ sinh ba lead cùng trỏ vào một đơn. Hệ thống lấy <b>lead sớm nhất</b> – kênh kéo được
          khách đến lần đầu mới là kênh tạo ra đơn ấy. Con số này cho biết phép khớp đang nhiễu tới đâu.</p>
      </div>}

      {/* MỘT CHIẾN DỊCH – TRUY XUỐNG TỪNG BOOKING */}
      {cd && <div className="panel wrap">
        <h2>{cd.chien_dich.ma} – {cd.chien_dich.ten}</h2>
        <p>{vnd(cd.tien)} đ · {cd.so_booking} booking · {cd.so_khach} khách
          {" · "}ngân sách kế hoạch {vnd(cd.chien_dich.ngan_sach_ke_hoach)} đ</p>
        <table><thead><tr><th>Mã</th><th>Khách</th><th>Chuyến</th><th>Kết thúc</th>
          <th>Biết nhờ</th><th className="num">Tiền</th></tr></thead>
          <tbody>{cd.rows.map((r: any) => <tr key={r.booking_id}>
            <td className="mono">{r.ma}</td><td>{r.khach}</td><td className="mono">{r.tour_ma}</td>
            <td>{r.ket_thuc}</td>
            <td>{TEN_DUONG[r.duong] || r.duong}{r.bat_dong && <> <Tag cls="warn">bất đồng</Tag></>}</td>
            <td className="num">{vnd(r.tien)}</td></tr>)}
          {!cd.rows.length && <tr><td colSpan={6} className="muted">Kỳ này chiến dịch chưa kéo về booking nào.</td></tr>}
          </tbody></table>
        <button className="act" onClick={() => setCd(null)}>Đóng</button></div>}
    </>}
  </>);
}

export default function Page() { return <Shell><DongGopMarketing /></Shell>; }
