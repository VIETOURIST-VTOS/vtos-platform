"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import Shell, { useShell } from "@/components/Shell";
import { api, vnd, fmtD } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** BÀN LÀM VIỆC CỦA SALE ADMIN PHÒNG ĐOÀN — 24/9/2026, vòng 3/3.
 *
 *  Sáu khối việc trong bản mô tả công việc hiệu lực 01/9/2026. Màn hình này KHÔNG thêm một quyền
 *  ghi nào: hai cửa ghi của vị trí ấy đã mở ở vòng 2 và nằm đúng chỗ của chúng — trên chính chuyến,
 *  ở `/tours/{id}`. Mỗi dòng dưới đây có đường dẫn sang đó.
 *
 *  ── VÌ SAO KHÔNG CÓ NÚT CHUYỂN NGAY TRÊN NÀY ───────────────────────────────────────────────
 *  Vì chuyển một dự toán là việc phải ĐỌC dự toán ấy, không phải việc phải bấm. Một nút "chuyển"
 *  cạnh một dòng tóm tắt là lời mời chuyển mà chưa mở ra xem — và cái cổng duy nhất của vị trí này
 *  mất hết ý nghĩa đúng vào lúc nó trở nên tiện tay.
 *
 *  ── MÀN HÌNH KHÔNG TỰ TÍNH MỘT CON SỐ NÀO ──────────────────────────────────────────────────
 *  Kể cả biên. Máy chủ tính bằng đúng `rules.calc` mà cổng biên dùng; tính lại ở đây là dựng công
 *  thức thứ hai, và ngày hai bên lệch thì con số nằm cạnh quyết định là con số sai.
 *
 *  ── BÁO CÁO NGÀY: KHÔNG CÓ Ô GỬI THƯ ───────────────────────────────────────────────────────
 *  Bản mô tả viết là gửi thư trước 20:00. VTOS đã có đúng cơ chế ấy từ Điều 12 và Chủ tịch đã quyết
 *  09/9/2026: báo cáo lập tự động trên màn hình, không cần gửi mail hay Zalo. Nên khối ấy là một
 *  đường dẫn tới màn hình đã có, không phải một hộp thư thứ hai.
 */

const pct = (v: any) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

/** Rỗng KHÁC không. Một màn hình in "0%" cho một đoàn chưa khai là nói với người đọc rằng đoàn ấy
 *  hoà vốn — trong khi sự thật là chưa ai trả lời. */
const so = (v: any) => (v === null || v === undefined
  ? <span className="muted" title="Chưa có số – khác với bằng 0">—</span>
  : <>{vnd(v)}</>);

function ConLai({ n }: { n: number | null }) {
  if (n === null || n === undefined) return <span className="muted">—</span>;
  if (n < 0) return <Tag cls="red">đã khởi hành {-n} ngày</Tag>;
  if (n <= 7) return <Tag cls="red">còn {n} ngày</Tag>;
  if (n <= 14) return <Tag cls="warn">còn {n} ngày</Tag>;
  return <span className="muted">còn {n} ngày</span>;
}

function O({ nhan, so: n, phu, manh }: { nhan: string; so: number; phu?: string; manh?: boolean }) {
  return (
    <div className="panel" style={{ marginBottom: 0, borderLeft: `4px solid var(--${manh ? "red" : "orange"})` }}>
      <div className="muted" style={{ fontSize: "calc(11/14*1rem)", textTransform: "uppercase", letterSpacing: ".04em", fontWeight: 600 }}>{nhan}</div>
      <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.2 }}>{n}</div>
      {phu ? <div className="muted" style={{ fontSize: "calc(12/14*1rem)" }}>{phu}</div> : null}
    </div>
  );
}

function Khoi({ ten, mo_ta, children }: { ten: string; mo_ta: React.ReactNode; children: React.ReactNode }) {
  return (<div className="panel wrap">
    <h2>{ten}</h2>
    <p className="muted">{mo_ta}</p>
    {children}
  </div>);
}

function Trong({ cot, chu }: { cot: number; chu: string }) {
  return <tr><td colSpan={cot} className="muted">{chu}</td></tr>;
}

function BanLamViec() {
  const { toast } = useShell();
  const [d, setD] = useState<any>(null);
  const [dang, setDang] = useState(true);

  const nap = useCallback(async () => {
    setDang(true);
    try { setD(await api("/sales-admin/ban-lam-viec")); }
    catch (e) { toast(errMsg(e), true); setD(null); }
    finally { setDang(false); }
  }, [toast]);
  useEffect(() => { nap(); }, [nap]);

  if (dang && !d) return <div className="panel"><p className="muted">Đang tải…</p></div>;
  if (!d) return <div className="panel"><p className="muted">Không đọc được dữ liệu.</p></div>;

  const dem = d.dem || {};
  const thu = d.tien_do_thu_tien || {};
  const qt = d.tien_do_quyet_toan || {};
  const bc = d.bao_cao_ngay || {};

  return (<>
    <h1>Bàn làm việc — Sale Admin phòng Đoàn</h1>
    <p className="muted">Sáu khối việc theo bản mô tả công việc hiệu lực 01/9/2026. Màn hình chỉ đọc:
      chuyển hoặc trả lại một dự toán làm ở chính chuyến ấy, sau khi đã mở ra đọc.</p>

    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 12 }}>
      <O nhan="Chờ tôi chuyển" so={dem.cho_toi_chuyen || 0} phu={`${dem.chuyen_duoc_ngay || 0} đủ trường · ${dem.phai_tra_lai || 0} phải trả lại`} manh={(dem.phai_tra_lai || 0) > 0} />
      <O nhan="Chưa trả lời hoa hồng khách" so={dem.doan_chua_tra_loi_hoa_hong || 0} phu="Bỏ trống thì không chuyển được" manh={(dem.doan_chua_tra_loi_hoa_hong || 0) > 0} />
      <O nhan="Hồ sơ còn thiếu" so={dem.ho_so_con_thieu || 0} phu="Năm loại giấy tờ trên từng mã đoàn" />
      <O nhan="Mốc thu quá hạn" so={dem.moc_thu_qua_han || 0} phu={`${dem.moc_thu_sap_toi_han || 0} mốc tới hạn trong 14 ngày`} manh={(dem.moc_thu_qua_han || 0) > 0} />
      <O nhan="Quá hạn chốt sổ" so={dem.qua_han_chua_dong_so || 0} phu={`${dem.dong_so_muon || 0} chuyến đóng muộn`} manh={(dem.qua_han_chua_dong_so || 0) > 0} />
      <O nhan="Đoàn thiếu tên khách" so={dem.doan_thieu_ten_khach || 0} phu="So với số khách theo hợp đồng" />
    </div>

    <div className="panel" style={{ borderLeft: "4px solid var(--navy)" }}>
      <h2>Báo cáo công việc hôm nay — hạn {bc.han}</h2>
      <p className="muted">{bc.ghi_chu}</p>
      <Link href={bc.man_hinh || "/"} className="act teal" style={{ margin: 0 }}>Mở màn hình báo cáo ngày →</Link>
    </div>

    <Khoi ten="1 · Dự toán chờ tôi chuyển Phòng Điều hành"
      mo_ta={<>Đây là cổng chặn duy nhất của vị trí này (Phần V bản mô tả): dự toán thiếu trường bắt buộc thì
        trả lại nhân viên phụ trách kèm ghi rõ thiếu gì, không chuyển đi. <b>Tôi không duyệt dự toán.</b></>}>
      <table><thead><tr><th>Mã đoàn</th><th>Tên</th><th>Khởi hành</th><th className="num">Biên kế hoạch</th><th>Trường còn thiếu</th><th></th></tr></thead>
        <tbody>{(d.cho_toi_chuyen || []).length ? d.cho_toi_chuyen.map((r: any) => (
          <tr key={r.tour_id}>
            <td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td>
            <td>{r.ten}</td>
            <td>{fmtD(r.khoi_hanh)} <ConLai n={r.con_bao_nhieu_ngay} /></td>
            <td className="num">{pct(r.bien_ke_hoach)} {r.duoi_bien && <Tag cls="warn">dưới biên</Tag>}</td>
            <td>{r.thieu.length ? r.thieu.join(" · ") : <Tag cls="ok">đủ trường</Tag>}</td>
            <td><Link href={`/tours/${r.tour_id}`} className="act grey" style={{ margin: 0 }}>
              {r.chuyen_duoc ? "Mở để đọc rồi chuyển" : "Mở để trả lại"}</Link></td>
          </tr>)) : <Trong cot={6} chu="Không có dự toán nào đang chờ." />}</tbody></table>
      <p className="muted">Đoàn có biên kế hoạch dưới ngưỡng vẫn chuyển được — cổng biên và hai chữ ký Chủ tịch +
        Tổng giám đốc nằm ở bước DUYỆT phía sau, không phải ở đây, và lần thêm việc này không đụng tới chúng.</p>
    </Khoi>

    <Khoi ten="2 · Soát giá vốn và chứng từ nhà cung cấp"
      mo_ta={<>Mục 4.2 buộc kiểm hoa hồng và quà tặng dành cho khách đã được đưa vào giá vốn của chính đoàn đó.
        Cột cuối là biên <i>nếu khoản hoa hồng đã khai chưa nằm trong giá vốn đã nhập</i> — một <b>cận dưới</b>,
        không phải một khẳng định. Ở đây tôi <b>đọc và soát</b>; tôi không đặt dịch vụ và không liên hệ nhà cung cấp.</>}>
      <table><thead><tr><th>Mã đoàn</th><th>Khởi hành</th><th>Hoa hồng khách</th><th className="num">Đã khai</th><th className="num">Biên đã nhập</th><th className="num">Biên nếu chưa vào giá vốn</th><th>Cảnh báo chứng từ</th></tr></thead>
        <tbody>{(d.soat_gia_von || []).length ? d.soat_gia_von.map((r: any) => (
          <tr key={r.tour_id}>
            <td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td>
            <td>{fmtD(r.khoi_hanh)}</td>
            <td>{r.hoa_hong_khach === "co" ? <Tag cls="warn">có</Tag>
              : r.hoa_hong_khach === "khong" ? <Tag cls="ok">không</Tag>
                : <Tag cls="red">chưa trả lời</Tag>}</td>
            <td className="num">{r.hoa_hong_khach === "co" ? so(r.hoa_hong_khach_tien) : <span className="muted">—</span>}</td>
            <td className="num">{pct(r.bien_ke_hoach)}</td>
            <td className="num">{r.bien_neu_hoa_hong_chua_vao != null
              ? <b style={{ color: "var(--red)" }}>{pct(r.bien_neu_hoa_hong_chua_vao)}</b>
              : <span className="muted">—</span>}</td>
            <td>{r.canh_bao?.length
              ? r.canh_bao.slice(0, 3).map((c: any, i: number) => <div key={i}><Tag cls={c.level === "block" ? "red" : "warn"}>{c.level}</Tag> {c.msg}</div>)
              : <span className="muted">—</span>}</td>
          </tr>)) : <Trong cot={7} chu="Không có đoàn nào cần soát." />}</tbody></table>
    </Khoi>

    <Khoi ten="3 · Hồ sơ đoàn — năm loại giấy tờ trên từng mã đoàn"
      mo_ta={<>Lưu trên phần mềm <b>theo từng mã đoàn</b>, không lưu rời trên máy cá nhân. Cột “còn thiếu” dựng
        bằng phép suy trên kho tệp đã có — loại tệp do người tải lên khai, hệ thống không đoán từ tên tệp.</>}>
      <table><thead><tr><th>Mã đoàn</th><th>Khởi hành</th><th className="num">Số tệp</th><th>Còn thiếu</th></tr></thead>
        <tbody>{(d.ho_so_doan || []).length ? d.ho_so_doan.map((r: any) => (
          <tr key={r.tour_id}>
            <td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td>
            <td>{fmtD(r.khoi_hanh)}</td>
            <td className="num">{r.so_tep}</td>
            <td>{r.thieu.length ? r.thieu.join(" · ") : <Tag cls="ok">đủ</Tag>}
              {r.khoa_chua_khai_bao?.length ? <div><Tag cls="warn">cấu hình</Tag> loại tệp chưa khai báo: {r.khoa_chua_khai_bao.join(", ")} — cột ấy sẽ luôn hiện “thiếu” cho tới khi được khai</div> : null}</td>
          </tr>)) : <Trong cot={4} chu="Không có đoàn nào đang mở." />}</tbody></table>
    </Khoi>

    <Khoi ten="4 · Tiến độ thu tiền theo mốc hợp đồng"
      mo_ta={<>Nhắc <b>trước</b> mỗi mốc, không đợi tới lúc quá hạn — nên hai nhóm tách riêng. Gộp chung thì cái
        sắp tới hạn chìm dưới cái đã hỏng.</>}>
      <h3>Sắp tới hạn (14 ngày tới)</h3>
      <table><thead><tr><th>Hợp đồng</th><th>Khách</th><th>Đợt</th><th className="num">Số tiền</th><th>Hạn</th></tr></thead>
        <tbody>{(thu.sap_toi_han || []).length ? thu.sap_toi_han.map((r: any, i: number) => (
          <tr key={i}><td>{r.so_hop_dong}</td><td>{r.khach_ten}</td><td>{r.dot} · {r.ten}</td>
            <td className="num">{so(r.so_tien)}</td><td>{fmtD(r.han)} <ConLai n={r.con_bao_nhieu_ngay} /></td></tr>
        )) : <Trong cot={5} chu="Không có mốc nào tới hạn trong 14 ngày." />}</tbody></table>
      <h3>Đã quá hạn</h3>
      <table><thead><tr><th>Hợp đồng</th><th>Khách</th><th>Đợt</th><th className="num">Còn thiếu</th><th>Hạn</th></tr></thead>
        <tbody>{(thu.qua_han || []).length ? thu.qua_han.map((r: any, i: number) => (
          <tr key={i}><td>{r.so_hop_dong}</td><td>{r.khach_ten}</td><td>{r.dot} · {r.ten}</td>
            <td className="num">{so(r.con_thieu)}</td><td>{fmtD(r.han)} <Tag cls="red">trễ {r.tre_ngay} ngày</Tag></td></tr>
        )) : <Trong cot={5} chu="Không có mốc nào quá hạn." />}</tbody></table>
    </Khoi>

    <Khoi ten="5 · Tiến độ quyết toán"
      mo_ta={<>Hạn chốt sổ đọc từ tham số công ty ({qt.han_theo_tham_so_ngay} ngày kể từ ngày đoàn kết thúc), không
        viết cứng. Đoàn quá hạn thì hoa hồng của đoàn ấy <b>hoãn</b> tới khi chốt sổ — cơ chế hoãn, không phải cắt.
        Số liệu quyết toán ở đây <b>chỉ đọc</b>: tôi đôn đốc, tôi không sửa số của bất kỳ đoàn nào.</>}>
      <h3>Chưa đóng sổ, đã quá hạn</h3>
      <table><thead><tr><th>Mã đoàn</th><th>Kết thúc</th><th>Hạn chốt sổ</th><th className="num">Quá hạn</th><th>Đang chờ tiền</th></tr></thead>
        <tbody>{(qt.chua_dong_so || []).length ? qt.chua_dong_so.map((r: any) => (
          <tr key={r.tour_id}><td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td><td>{fmtD(r.ket_thuc)}</td>
            <td>{fmtD(r.han_chot_so)}</td><td className="num"><Tag cls="red">{r.qua_han_ngay} ngày</Tag></td>
            <td>{r.dang_cho_tien?.length ? r.dang_cho_tien.map((x: any, i: number) => <div key={i}>{x.ten} ({x.vai_tro})</div>) : <span className="muted">—</span>}</td></tr>
        )) : <Trong cot={5} chu="Không có đoàn nào quá hạn chốt sổ." />}</tbody></table>
      <h3>Đã đóng sổ nhưng muộn</h3>
      <table><thead><tr><th>Mã đoàn</th><th>Hạn chốt sổ</th><th>Đóng lúc</th><th className="num">Muộn</th></tr></thead>
        <tbody>{(qt.dong_muon || []).length ? qt.dong_muon.map((r: any) => (
          <tr key={r.tour_id}><td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td><td>{fmtD(r.han_chot_so)}</td>
            <td>{fmtD(r.dong_luc)}</td><td className="num"><Tag cls="warn">{r.muon_ngay} ngày</Tag></td></tr>
        )) : <Trong cot={4} chu="Không có đoàn nào đóng sổ muộn." />}</tbody></table>
      <p className="muted">Hai nhóm đếm RIÊNG, không cộng chung: chỉ đếm nhóm đầu thì con số tự đẹp lên mỗi lần có
        người đóng muộn một chuyến — thước đo tự lành, và cái nó đo được thì biến mất.</p>
    </Khoi>

    <Khoi ten="6 · Dữ liệu khách đoàn — phải đủ trước khi đoàn chạy"
      mo_ta={<>So số khách theo hợp đồng với số chỗ đã đặt, và soát booking nào chưa ghi nguồn khách.</>}>
      <table><thead><tr><th>Mã đoàn</th><th>Khởi hành</th><th className="num">Theo hợp đồng</th><th className="num">Chỗ đã đặt</th><th>Booking chưa ghi nguồn</th><th>Thoả thuận chia data</th></tr></thead>
        <tbody>{(d.du_lieu_khach || []).length ? d.du_lieu_khach.map((r: any) => (
          <tr key={r.tour_id}>
            <td><Link href={`/tours/${r.tour_id}`}>{r.ma}</Link></td>
            <td>{fmtD(r.khoi_hanh)}</td>
            <td className="num">{r.khach_theo_hop_dong || <span className="muted">—</span>}</td>
            <td className="num">{r.cho_da_dat < (r.khach_theo_hop_dong || 0) ? <Tag cls="warn">{r.cho_da_dat}</Tag> : r.cho_da_dat}</td>
            <td>{r.booking_chua_ghi_nguon?.length ? r.booking_chua_ghi_nguon.join(", ") : <Tag cls="ok">đủ</Tag>}</td>
            <td><span className="muted" title="Hệ thống chưa có ô này – khác với 'chưa ghi'">chưa có ô nhập</span></td>
          </tr>)) : <Trong cot={6} chu="Không có đoàn nào sắp khởi hành." />}</tbody></table>
      <p className="muted">Cột cuối để trống có chủ ý: <b>thoả thuận chia data chưa có ô nhập nào trong hệ thống.</b> In
        “chưa ghi” ở đó là nói với người dùng rằng họ quên một việc, trong khi thật ra là một việc phần mềm chưa mở
        cửa cho họ làm.</p>
    </Khoi>
  </>);
}

export default function Page() { return <Shell><BanLamViec /></Shell>; }
