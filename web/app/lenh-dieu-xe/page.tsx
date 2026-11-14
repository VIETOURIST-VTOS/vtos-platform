"use client";
import { useEffect, useState, useCallback } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtD, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";
import ThanhViec, { docUrl, baoDaDoi, useDaDoi, type Viec } from "@/components/ThanhViec";

/** Lệnh điều xe – Đợt 4, TÁCH MÀN 17/10/2026 (Chủ tịch duyệt bản xem thử 16/10/2026).
 *
 *  Màn này trước kia gánh 13 khối và 41 biến trạng thái trên một trang. Nay tách thành sáu màn:
 *
 *    /lenh-dieu-xe                 — màn chính: LỆNH ĐÃ LẬP (tệp này)
 *    /lenh-dieu-xe?ma=<id>         — màn MỘT LỆNH, toàn màn (tệp này)
 *    /lenh-dieu-xe/de-nghi         — đề nghị xe đang chờ, sửa số khách, đoàn thiếu chỗ
 *    /lenh-dieu-xe/lap-lenh        — tìm phương án và chốt lệnh
 *    /lenh-dieu-xe/de-nghi/moi     — Điều hành gửi đề nghị xe, toàn màn
 *    /lenh-dieu-xe/chua-nhan       — lệnh tài xế chưa nhận, toàn màn
 *
 *  Bốn việc trên một lệnh — đổi xe, đổi tài xế, đóng lệnh, xoá lệnh — mở ở tab riêng bằng
 *  `?ma=<id>&viec=<việc>` trên CHÍNH đường dẫn này, không đẻ thêm thư mục trang: bảng tách Chủ tịch
 *  duyệt có sáu màn, và bốn việc ấy là trạng thái của màn một lệnh, không phải màn thứ bảy.
 *
 *  Màn hình này gợi ý, không quyết. Đặc tả đặt ranh giới rõ: "Không để quyết định cho xe xuất bến
 *  phụ thuộc vào kết luận của mô hình ngôn ngữ." */

const DUONG = <><a href="/">VTOS</a> · <a href="/phan-he/dhxe">Đội xe</a> · <a href="/lenh-dieu-xe">Lệnh điều xe</a></>;
const VIEC_MOT = ["xac-nhan", "doi-xe", "doi-tai-xe", "dong-lenh", "xoa-lenh"] as const;

function LenhDieuXe() {
  // Đọc đường dẫn MỘT LẦN khi mở: `?ma=` là màn một lệnh, không có là màn danh sách. Chưa đọc xong
  // thì chưa vẽ gì — vẽ danh sách trước rồi mới nhảy sang một lệnh là một cái chớp giữa hai màn.
  const [doc, setDoc] = useState(false);
  const [ma, setMa] = useState<number | null>(null);
  const [viec, setViec] = useState("");
  useEffect(() => {
    const q = docUrl();
    const m = Number(q.get("ma"));
    if (m > 0) setMa(m);
    const v = q.get("viec") || "";
    if ((VIEC_MOT as readonly string[]).includes(v)) setViec(v);
    setDoc(true);
  }, []);
  if (!doc) return <p className="muted">Đang tải…</p>;
  if (ma) return <MotLenh ma={ma} viec={viec} />;
  return <DanhSach />;
}

/* ═══════════════════════ MÀN CHÍNH · LỆNH ĐÃ LẬP ═══════════════════════ */
function DanhSach() {
  const { toast } = useShell();
  const [ds, setDs] = useState<any[]>([]);
  const [ho, setHo] = useState<any>(null);             // đếm lệnh lập KHÔNG qua cửa đề nghị
  const [chuoi, setChuoi] = useState<any>(null);       // DL-3: hai số đo chỗ lệnh và chuyến chưa gặp nhau
  // Ba con số ĐẾM đứng trên thanh việc (Chủ tịch chốt: số đếm ở lại màn chính, nằm trên thanh việc).
  const [dn, setDn] = useState<any>(null);
  const [dnQ, setDnQ] = useState<any>(null);
  const [nhan, setNhan] = useState<any>(null);
  const daDoi = useDaDoi();

  const load = useCallback(async () => {
    try { setDs(await api("/fleet/lenh-dieu-xe")); } catch (e) { toast(errMsg(e), true); }
    try { setHo(await api("/de-nghi-xe/lenh-khong-qua-de-nghi")); } catch { /* chỉ là số đo */ }
    // DL-3 — hai số đo chỗ chuỗi chưa liền giữa LỆNH và CHUYẾN. Cùng khuôn: đếm, không chặn.
    try { setChuoi(await api("/dispatch/chuoi-lenh-chuyen")); } catch { /* chỉ là số đo */ }
    try { setDn(await api("/de-nghi-xe")); } catch { /* thiếu thì nút không có số, vẫn bấm được */ }
    try { setDnQ(await api("/de-nghi-xe/meta")); } catch { /* thiếu meta thì ẩn nút, không đoán quyền */ }
    try { setNhan(await api("/nhan-lenh/can-biet")); } catch { /* thiếu thì nút không có số */ }
  }, [toast]);
  useEffect(() => { load(); }, [load]);
  const napLai = async () => { await load(); daDoi.xong(); };

  const viec: Viec[] = [
    { nhan: "Lập lệnh mới", href: "/lenh-dieu-xe/lap-lenh", chinh: true },
    { nhan: "Đề nghị xe đang chờ", href: "/lenh-dieu-xe/de-nghi", so: dn?.dem?.cho_lap_lenh ?? null },
    // Hiện nút nào do MÁY CHỦ trả lời (meta.toi_duoc_*), không gõ lại danh sách vai ở đây.
    ...(dnQ?.toi_duoc_de_nghi ? [{ nhan: "Điều hành đề nghị xe", href: "/lenh-dieu-xe/de-nghi/moi" }] : []),
    { nhan: "Tài xế chưa nhận", href: "/lenh-dieu-xe/chua-nhan",
      so: nhan?.dem ? (nhan.dem.qua_han || 0) + (nhan.dem.tu_choi || 0) : null },
    // R5-30: hợp đồng thuê xe đội xe tự nhận (Chủ tịch duyệt 14/11/2026).
    { nhan: "Hợp đồng thuê xe", href: "/lenh-dieu-xe/thue-xe" },
  ];

  return (<>
    <h1>Lệnh điều xe</h1>
    <ThanhViec viec={viec} duong={DUONG} daDoi={{ ...daDoi, napLai }} />
    <p className="muted">Danh sách lệnh đã lập. <b>Lập lệnh mới</b>, đề nghị xe và lệnh tài xế chưa nhận mở ở tab riêng từ thanh việc trên; bấm số lệnh để mở một lệnh — đổi xe, đổi tài xế, đóng hay xoá đều làm ở đó.</p>

    <div className="panel wrap"><h2>Lệnh đã lập ({ds.length})</h2>
      <p className="muted">Cột cuối ghi vết: lệnh theo gợi ý hay chọn khác, và lý do khi chọn khác. Đây là dữ liệu để mỗi quý đánh giá lại chất lượng thuật toán gợi ý.</p>
      {/* CHỖ HỞ CỐ Ý, ĐO ĐƯỢC: cửa lập lệnh vẫn nhận lệnh không kèm đề nghị. Bắt buộc ngay thì
          Điều hành đứng việc. Nhưng một chỗ hở không đếm được là một chỗ hở sẽ ở lại mãi — nên nó
          hiện ra ở đây, và khi con số về 0 thì siết thành bắt buộc không còn làm ai đứng việc. */}
      {ho && ho.tong_lenh > 0 && <p className="muted">
        {ho.khong_qua_de_nghi > 0
          ? <><Tag cls="warn">chuỗi chưa liền</Tag> {ho.khong_qua_de_nghi}/{ho.tong_lenh} lệnh lập <b>không qua cửa đề nghị</b>. Khi con số này về 0 và giữ 0 một thời gian thì bắt buộc đề nghị được, mà không làm ai đứng việc.</>
          : <><Tag cls="ok">chuỗi liền</Tag> Cả {ho.tong_lenh} lệnh đều đi qua cửa đề nghị xe.</>}</p>}
      {/* DL-3: hai chỗ hở giữa lệnh và chuyến. Số bên phải đo được 15/10/2026 là 756 — toàn bộ
          chuyến đang không gắn lệnh nào, vì tới hôm ấy chưa có đường nào ghi `dispatch_id`. */}
      {chuoi && <p className="muted">
        {chuoi.lenh_xong_chua_co_chuyen?.so > 0
          ? <><Tag cls="warn">lệnh xong, chưa có chuyến</Tag> {chuoi.lenh_xong_chua_co_chuyen.so}/{chuoi.lenh_xong_chua_co_chuyen.tong_lenh_hoan_thanh} lệnh đã hoàn thành mà <b>chưa sinh ra chuyến nào</b> — đóng lệnh lại một lần nữa thì máy sinh, hoặc gắn tay vào chuyến đã nạp.</>
          : <><Tag cls="ok">lệnh nào xong cũng có chuyến</Tag> </>}
        {" · "}
        {chuoi.chuyen_chua_gan_lenh?.so > 0
          ? <><Tag cls="warn">chuyến chưa gắn lệnh</Tag> {chuoi.chuyen_chua_gan_lenh.so}/{chuoi.chuyen_chua_gan_lenh.tong_chuyen} chuyến <b>không gắn lệnh nào</b> — phần lớn là sổ cũ nạp bằng tệp trước khi có mối nối này.</>
          : <><Tag cls="ok">chuyến nào cũng có lệnh</Tag></>}</p>}

      {/* DL-6 · 16/10/2026: ô đếm thứ ba, KÈM DANH SÁCH. CHỈ ĐẾM CHUYẾN SINH TỪ LỆNH. Sổ cũ nạp bằng
          Excel cũng thiếu km, nhưng gộp vào thì con số này không bao giờ về 0 — và một con số không
          bao giờ về 0 thì chẳng mấy ai còn nhìn. */}
      {chuoi?.chuyen_tu_lenh_thieu_so && (chuoi.chuyen_tu_lenh_thieu_so.so > 0
        ? <div className="muted">
          <Tag cls="warn">chuyến sinh từ lệnh còn thiếu số thật</Tag>{" "}
          {chuoi.chuyen_tu_lenh_thieu_so.so}/{chuoi.chuyen_tu_lenh_thieu_so.tong_chuyen_tu_lenh} chuyến —
          giá vốn đội xe của những chuyến này còn thiếu một nửa cho tới khi Đội xe nhập km và chi phí.
          <table><thead><tr><th>Chuyến</th><th>Lệnh</th><th>Tour</th><th>Ngày đi</th><th>Còn thiếu</th><th></th></tr></thead>
            <tbody>{chuoi.chuyen_tu_lenh_thieu_so.danh_sach.map((c: any) => <tr key={c.chuyen_id}>
              <td><b>#{c.chuyen_id}</b></td><td>{c.lenh_id ? "#" + c.lenh_id : ""}</td>
              <td>{c.tour}</td><td>{fmtD(c.ngay_di)}</td>
              <td>{c.thieu.map((x: string, i: number) => <div key={i}><Tag cls="warn">thiếu</Tag> {x}</div>)}</td>
              <td><a className="act grey" style={{ margin: 0 }}
                href="/doi-xe?tab=chuyen">Nhập số</a></td>
            </tr>)}</tbody></table>
        </div>
        : <p className="muted"><Tag cls="ok">chuyến sinh từ lệnh đều có số thật</Tag></p>)}

      <table><thead><tr><th>#</th><th>Tour</th><th>Xe</th><th>Tài xế</th><th>Từ → đến</th><th>Giá nội bộ</th><th>Trạng thái</th><th>Tài xế nhận</th><th>Ghi vết gợi ý</th></tr></thead>
        <tbody>{ds.length ? ds.map((d) => <tr key={d.id}>
          {/* Số lệnh là đường vào màn MỘT LỆNH, mở tab mới — mọi việc trên một lệnh làm ở đó. */}
          <td><a href={`/lenh-dieu-xe?ma=${d.id}`} target="_blank" rel="noopener"
            title="Mở lệnh này trong tab mới"><b>#{d.id}</b> ↗</a></td>
          <td>{d.tour}</td><td>{d.ma_xe} · {d.xe}</td><td>{d.tai_xe}</td>
          <td>{fmtD(d.date_from)} → {fmtD(d.date_to)} <span className="muted">({d.so_ngay} ngày)</span></td>
          <td className="num">{d.internal_price?.toLocaleString("vi-VN")}</td>
          <td><TrangThai d={d} /></td>
          <td><DauNhan d={d} /></td>
          <td><GhiVet d={d} /></td>
        </tr>) : <tr><td colSpan={9} className="muted">Chưa có lệnh điều xe nào.</td></tr>}</tbody></table>
    </div>
  </>);
}

const TrangThai = ({ d }: { d: any }) => (d.status === "hoan_thanh" ? <Tag cls="ok">hoàn thành</Tag>
  : d.status === "da_xac_nhan" ? <Tag cls="ok">đã xác nhận</Tag>
  : d.status === "huy" ? <Tag cls="red">hủy</Tag> : <Tag cls="warn">chờ xác nhận</Tag>);

/* Cột này đứng CẠNH cột trạng thái, không thay nó: "đã xác nhận" là GĐ đội xe đã chốt lệnh — nghĩa
   có từ trước — còn cột này là tài xế đã nhận chưa. */
const DauNhan = ({ d }: { d: any }) => (d.trang_thai_nhan === "da_nhan" ? <><Tag cls="ok">đã nhận</Tag> <div className="muted">{fmtDT(d.nhan_luc)}</div></>
  : d.trang_thai_nhan === "tu_choi" ? <><Tag cls="red">không nhận được</Tag> <div className="muted">{d.tu_choi_nhan_ly_do}</div></>
  : d.trang_thai_nhan === "qua_han" ? <><Tag cls="warn">quá hạn</Tag> <div className="muted">hạn {fmtDT(d.han_nhan)}</div></>
  : d.trang_thai_nhan === "chua_nhan" ? <><Tag cls="warn">chưa nhận</Tag> <div className="muted">hạn {fmtDT(d.han_nhan)}</div></>
  : <span className="muted">—</span>);

const GhiVet = ({ d }: { d: any }) => (d.ly_do_khac_goi_y ? <><Tag cls="warn">chọn khác gợi ý</Tag> <div className="muted">{d.ly_do_khac_goi_y}</div></>
  : d.phuong_an_da_chon ? <Tag cls="ok">theo gợi ý</Tag> : <span className="muted">lệnh cũ, chưa có ghi vết</span>);

/* ═══════════════════════ MÀN MỘT LỆNH · ?ma=<id> (toàn màn) ═══════════════════════ */
function MotLenh({ ma, viec }: { ma: number; viec: string }) {
  const { toast } = useShell();
  const [d, setD] = useState<any>(undefined);          // undefined: đang nạp · null: không có lệnh này
  const daDoi = useDaDoi();

  // Không có cửa đọc MỘT lệnh: đọc danh sách rồi lọc. Danh sách đã là cửa mà màn chính dùng, nên
  // quyền đọc của màn một lệnh y hệt màn chính — không mở thêm cửa nào trên máy chủ.
  const load = useCallback(async () => {
    try {
      const ds: any[] = await api("/fleet/lenh-dieu-xe");
      setD(ds.find((x) => x.id === ma) || null);
    } catch (e) { toast(errMsg(e), true); setD(null); }
  }, [ma, toast]);
  useEffect(() => { load(); }, [load]);
  const napLai = async () => { await load(); daDoi.xong(); };

  const duong = <>{DUONG} · Lệnh #{ma}{viec && <> · {TEN_VIEC[viec]}</>}</>;
  const veMot = `/lenh-dieu-xe?ma=${ma}`;
  // Việc xong thì quay về màn một lệnh ở CHÍNH tab này, và báo cho tab danh sách biết đã có đổi.
  const xongViec = (loi: string) => { baoDaDoi(`lệnh #${ma} ${loi}`); window.location.href = veMot; };

  if (d === undefined) return <><ThanhViec toanMan duong={duong} viec={[]} /><p className="muted">Đang tải lệnh #{ma}…</p></>;
  if (d === null) return (<>
    <ThanhViec toanMan duong={duong} viec={[{ nhan: "‹ Danh sách lệnh", href: "/lenh-dieu-xe", len: true }]} />
    <div className="panel"><h1>Không thấy lệnh #{ma}</h1>
      <p className="muted">Lệnh này không có trong danh sách anh được xem — có thể đã bị xoá, hoặc số lệnh trên đường dẫn bị gõ sai.</p></div>
  </>);

  const doiDuoc = d.status === "cho_xac_nhan" || d.status === "da_xac_nhan";
  const lyDoKhongDoi = d.status === "hoan_thanh"
    ? "Lệnh đã hoàn thành — đã sinh chuyến trong nhật trình, đổi xe lúc này là sửa lịch sử."
    : d.status === "huy" ? "Lệnh đã huỷ." : "";
  const dongDuoc = d.status === "da_xac_nhan";

  if (viec) return (<>
    <ThanhViec toanMan duong={duong} viec={[{ nhan: "‹ Lên một cấp", href: veMot, len: true }]} />
    <h1>{TEN_VIEC[viec]} · lệnh #{d.id}</h1>
    <TomTat d={d} />
    <div className="panel">
      {viec === "doi-xe" && <DoiXe key={"doi" + d.id} lenh={d} che="xe" xong={() => xongViec("vừa đổi xe")} thoi={() => { window.location.href = veMot; }} />}
      {viec === "doi-tai-xe" && <DoiXe key={"tx" + d.id} lenh={d} che="tx" xong={() => xongViec("vừa đổi tài xế")} thoi={() => { window.location.href = veMot; }} />}
      {viec === "xac-nhan" && <XacNhanLenh key={"xn" + d.id} lenh={d} xong={() => xongViec("vừa được xác nhận")} />}
      {viec === "dong-lenh" && <DongLenh key={"dong" + d.id} lenh={d} xong={() => xongViec("vừa đóng")} />}
      {/* `key` theo id lệnh là BẮT BUỘC: không có nó thì soát lệnh này rồi bấm sang lệnh khác
          sẽ thấy câu trả lời của lệnh trước — đã xảy ra thật ở cửa xoá xe ngày 14/10/2026,
          và đây là khối quyết định có làm mất hẳn một chứng từ hay không. */}
      {viec === "xoa-lenh" && <XoaLenh key={d.id} lenh={d}
        xong={() => { baoDaDoi(`lệnh #${ma} vừa bị xoá`); window.location.href = "/lenh-dieu-xe"; }} />}
    </div>
  </>);

  return (<>
    <ThanhViec toanMan duong={duong} daDoi={{ ...daDoi, napLai }} viec={[
      { nhan: "‹ Lên một cấp", href: "/lenh-dieu-xe", len: true },
      // R5-27 (Chủ tịch 14/11/2026 chọn «Xác nhận lệnh»): GĐ đội xe xác nhận lệnh ngay trên màn một lệnh —
      // trước đây chỉ có ở màn cũ cho các vai mà máy chủ không cho xác nhận, nên lệnh kẹt ở «chờ xác nhận».
      { nhan: "Xác nhận lệnh", href: `${veMot}&viec=xac-nhan`, chinh: d.status === "cho_xac_nhan",
        tat: d.status === "cho_xac_nhan" ? "" : "Chỉ xác nhận được lệnh đang chờ xác nhận." },
      { nhan: "Đổi xe", href: `${veMot}&viec=doi-xe`, chinh: d.status !== "cho_xac_nhan", tat: doiDuoc ? "" : lyDoKhongDoi },
      { nhan: "Đổi tài xế", href: `${veMot}&viec=doi-tai-xe`, tat: doiDuoc ? "" : lyDoKhongDoi },
      { nhan: "Đóng lệnh", href: `${veMot}&viec=dong-lenh`,
        tat: dongDuoc ? "" : "Chỉ đóng được lệnh đã xác nhận." },
      { nhan: "Xoá lệnh", href: `${veMot}&viec=xoa-lenh` },
    ]} />
    <h1>Lệnh điều xe #{d.id}</h1>
    <TomTat d={d} />
    {!doiDuoc && lyDoKhongDoi && <p className="muted">{lyDoKhongDoi}</p>}
  </>);
}

const TEN_VIEC: Record<string, string> = {
  "xac-nhan": "Xác nhận lệnh", "doi-xe": "Đổi xe", "doi-tai-xe": "Đổi tài xế", "dong-lenh": "Đóng lệnh", "xoa-lenh": "Xoá lệnh",
};

/** Nội dung lệnh, in trước mọi việc: người bấm phải nhìn tận mắt tour, xe, tài xế, ngày và giá rồi
 *  mới quyết — `status` một mình không chứng minh được gì. */
const TomTat = ({ d }: { d: any }) => (
  <div className="panel wrap"><table><tbody>
    <tr><td>Tour</td><td><b>{d.tour}</b></td></tr>
    <tr><td>Xe</td><td>{d.ma_xe} · {d.xe}</td></tr>
    <tr><td>Tài xế</td><td>{d.tai_xe}</td></tr>
    <tr><td>Từ → đến</td><td>{fmtD(d.date_from)} → {fmtD(d.date_to)} <span className="muted">({d.so_ngay} ngày)</span></td></tr>
    <tr><td>Giá nội bộ</td><td className="num">{d.internal_price?.toLocaleString("vi-VN")}</td></tr>
    <tr><td>Trạng thái</td><td><TrangThai d={d} /></td></tr>
    <tr><td>Tài xế nhận</td><td><DauNhan d={d} /></td></tr>
    <tr><td>Ghi vết gợi ý</td><td><GhiVet d={d} /></td></tr>
    <tr><td>Người lập</td><td>{d.created_by}{d.confirmed_at && <span className="muted"> · chốt {fmtDT(d.confirmed_at)}</span>}</td></tr>
  </tbody></table></div>);

/** R5-27 · XÁC NHẬN LỆNH (Chủ tịch chọn 14/11/2026). Hai bước như đóng lệnh: màn hình nói trước điều sẽ xảy
 *  ra, nút xác nhận đứng riêng. Máy chủ quyết ai được bấm (chỉ người lập lệnh theo `xe_nguoi_lap_lenh`); xác nhận
 *  lại một lệnh tài xế đã nhận thì dấu nhận hết hiệu lực (LUẬT 3, 12/10/2026) — nói trước cho người bấm. */
function XacNhanLenh({ lenh, xong }: { lenh: any; xong: () => void }) {
  const { toast } = useShell();
  const [dang, setDang] = useState(false);
  const xacNhan = async () => {
    setDang(true);
    try {
      const r: any = await api(`/dispatch/${lenh.id}/update`, { method: "POST", json: { status: "da_xac_nhan" } });
      toast(r.message); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  if (lenh.status !== "cho_xac_nhan") return <p className="muted">
    Chỉ xác nhận được lệnh <b>đang chờ xác nhận</b>. Lệnh này đang ở trạng thái <TrangThai d={lenh} />.</p>;
  return (<div>
    <p>Xác nhận là chốt lệnh này để chạy: tour, xe, tài xế, ngày và giá như bảng trên. Sau khi xác nhận, lệnh
      mới <b>đóng được</b> khi chuyến chạy xong.</p>
    {lenh.nhan_luc && <p className="muted">Tài xế đã nhận lệnh này. Xác nhận bây giờ thì tài xế phải bấm nhận lại
      trên điện thoại (lệnh được chốt lại).</p>}
    <button className="act" style={{ margin: "8px 0 0", background: "var(--vtos-sky)", borderColor: "var(--vtos-sky)" }}
      disabled={dang} onClick={xacNhan}>{dang ? "Đang xác nhận…" : `Xác nhận lệnh #${lenh.id}`}</button>
  </div>);
}

/** DL-3 · ĐÓNG LỆNH (Chủ tịch chốt 15/10/2026: đóng lệnh thì máy sinh chuyến).
 *
 *  Hai bước như cửa xoá: màn hình nói trước điều sẽ xảy ra, nút xác nhận đứng riêng. KHÔNG dùng
 *  hộp thoại xác nhận của trình duyệt — một hộp thoại bấm quen tay thì không còn là một lần cân
 *  nhắc. Màn hình không tự quyết thay máy chủ: máy chủ trả lời đã sinh chuyến hay chưa, và câu ấy
 *  được in nguyên. */
function DongLenh({ lenh, xong }: { lenh: any; xong: () => void }) {
  const { toast } = useShell();
  const [dang, setDang] = useState(false);
  const dong = async () => {
    setDang(true);
    try {
      const r: any = await api(`/dispatch/${lenh.id}/update`, { method: "POST", json: { status: "hoan_thanh" } });
      toast(r.message); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  if (lenh.status !== "da_xac_nhan") return <p className="muted">
    Chỉ đóng được lệnh <b>đã xác nhận</b>. Lệnh này đang ở trạng thái <TrangThai d={lenh} />.</p>;
  return (<div>
    <p>Đóng lệnh là báo <b>chuyến đã chạy xong</b>. Máy sẽ sinh một chuyến trong nhật trình đội xe từ lệnh
      này; Đội xe nhập km và chi phí thật vào chuyến ấy sau.</p>
    <p className="muted">Lệnh đã đóng thì không đổi xe hay đổi tài xế được nữa — đổi lúc ấy là sửa lịch sử.</p>
    <button className="act teal" style={{ margin: "8px 0 0" }} disabled={dang} onClick={dong}>
      {dang ? "Đang đóng…" : `Xác nhận đóng lệnh #${lenh.id}`}</button>
  </div>);
}

/** DL-5 · ĐỔI XE / ĐỔI TÀI XẾ trên một lệnh đã lập (Chủ tịch chốt 15/10/2026).
 *
 *  Trước vòng này, xe hỏng trước giờ chạy thì Điều hành phải XOÁ lệnh rồi LẬP LẠI — mất dấu lệnh
 *  cũ, mất dấu ai đã nhận, và tháng sau không ai trả lời được vì sao đổi.
 *
 *  HAI BƯỚC, KHÔNG MỘT. Bước chọn xe và bước xác nhận tách rời nhau vì giá nội bộ ĐỔI THEO XE:
 *  xe hợp tác ăn giá đối tác, xe nhà ăn giá nội bộ. Người bấm phải nhìn thấy «2.400.000 →
 *  3.100.000» trước khi quyết, chứ không phát hiện ra vào cuối tháng.
 *
 *  Màn hình KHÔNG tự quyết thay máy chủ: nút vẫn bấm được khi vai sai hoặc xe vướng điều kiện, và
 *  máy chủ trả lời vì sao. Giấu nút đi thì người dùng chỉ thấy một màn hình thiếu, không biết
 *  thiếu gì.
 *
 *  Tách màn 17/10/2026: hai nút «Đổi xe / Đổi tài xế» nay nằm trên thanh việc của màn một lệnh và
 *  mở tab riêng, nên thành phần này nhận sẵn `che` và nạp ngay khi mở. */
function DoiXe({ lenh, che, xong, thoi }: { lenh: any; che: "xe" | "tx"; xong: () => void; thoi: () => void }) {
  const { toast } = useShell();
  const [mo, setMo] = useState<"" | "xe" | "tx">("");
  const [ds, setDs] = useState<any>(null);
  const [chonXe, setChonXe] = useState<any>(null);     // bảng cũ → mới của xe đang chọn
  const [chonTx, setChonTx] = useState<number | null>(null);
  const [ly, setLy] = useState("");
  const [dang, setDang] = useState(false);

  const doiDuoc = lenh.status === "cho_xac_nhan" || lenh.status === "da_xac_nhan";
  const nap = useCallback(async () => {
    setDang(true);
    try { setDs(await api(`/dispatch/${lenh.id}/thay-the-duoc`)); setMo(che); }
    catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  }, [lenh.id, che, toast]);
  useEffect(() => { if (doiDuoc) nap(); }, [doiDuoc, nap]);
  const soatXe = async (xid: number) => {
    setDang(true);
    try { setChonXe(await api(`/dispatch/${lenh.id}/soat-doi-xe/${xid}`)); }
    catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const gui = async (duong: string, than: any) => {
    setDang(true);
    try {
      const r: any = await api(`/dispatch/${lenh.id}/${duong}`,
        { method: "POST", body: JSON.stringify({ ...than, ly_do: ly, phien_ban: lenh.phien_ban }) });
      toast(r.message); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!doiDuoc) return <div className="muted">{lenh.status === "hoan_thanh"
    ? "Lệnh đã hoàn thành — đã sinh chuyến trong nhật trình, đổi xe lúc này là sửa lịch sử."
    : "Lệnh đã huỷ."}</div>;
  if (!mo) return <p className="muted">{dang ? "Đang nạp danh sách thay thế…" : "Không nạp được danh sách thay thế."}</p>;

  const ly_do_o = (<label>Lý do đổi <span className="muted">(bắt buộc — không có ô này thì đổi xe
    chỉ là một cách xoá dấu vết êm hơn xoá lệnh)</span>
    <input value={ly} onChange={(e) => setLy(e.target.value)}
      placeholder="ví dụ: xe hỏng hộp số sáng 17/10, gara báo 3 ngày" /></label>);
  const nutThoi = <p><button className="act grey" style={{ margin: "8px 0 0" }}
    onClick={thoi}>Thôi</button></p>;

  if (mo === "xe" && chonXe) return (<div>
    <table><tbody>
      <tr><td>Xe</td><td><s className="muted">{chonXe.xe_cu}</s> → <b>{chonXe.xe_moi}</b></td></tr>
      <tr><td>Tài xế</td><td><s className="muted">{chonXe.tai_xe_cu}</s> → <b>{chonXe.tai_xe_moi || chonXe.tai_xe_cu}</b>
        {chonXe.tai_xe_doi_theo && <div className="muted">Tài xế đi theo xe. Muốn giữ người thì dùng nút Đổi tài xế.</div>}</td></tr>
      <tr><td>Giá nội bộ</td><td><s className="muted">{chonXe.gia_cu?.toLocaleString("vi-VN")}</s> → <b>{chonXe.gia_moi?.toLocaleString("vi-VN")}</b>
        {chonXe.gia_cu !== chonXe.gia_moi && <div className="muted">Giá đổi vì loại xe khác — xe hợp tác ăn giá đối tác, xe nhà ăn giá nội bộ.</div>}
        {chonXe.loi_gia && <div><Tag cls="red">chặn</Tag> {chonXe.loi_gia}</div>}</td></tr>
    </tbody></table>
    {chonXe.vi_pham?.length > 0
      ? <div className="gate fail">{chonXe.vi_pham.map((v: any) => v.msg).join(" · ")}</div>
      : <div className="gate pass">Xe mới đủ điều kiện nhận lệnh này.</div>}
    {chonXe.canh_bao?.map((c: string, i: number) => <div key={i} className="muted"><Tag cls="warn">lưu ý</Tag> {c}</div>)}
    {chonXe.se_xoa_dau_nhan && <div className="muted"><Tag cls="warn">lưu ý</Tag> Dấu nhận của tài xế
      sẽ bị xoá — lệnh cần tài xế mới nhận lại.</div>}
    {ly_do_o}
    <button className="act teal" style={{ margin: "8px 0 0" }} disabled={dang || !ly.trim()}
      onClick={() => gui("doi-xe", { xe_id: ds.xe.find((x: any) => x.bien === chonXe.xe_moi)?.id })}>
      Xác nhận đổi</button>
    <button className="act grey" style={{ margin: "8px 0 0 6px" }}
      onClick={() => setChonXe(null)}>Chọn xe khác</button>
    {nutThoi}
  </div>);

  if (mo === "xe") return (<div>
    <div className="muted">Lệnh #{lenh.id} đang là <b>{lenh.xe}</b>. Chọn xe thay thế:</div>
    <table><thead><tr><th>Xe</th><th>Chỗ</th><th>Tài xế</th><th>Giá</th><th>Điều kiện</th><th></th></tr></thead>
      <tbody>{(ds?.xe || []).map((x: any) => <tr key={x.id}>
        <td>{x.ma} · {x.bien} {x.loai === "hop_tac" && <Tag cls="warn">hợp tác</Tag>}</td>
        <td className="num">{x.ghe}</td><td>{x.tai_xe}</td>
        <td className="num">{x.gia?.toLocaleString("vi-VN")}</td>
        <td><Tag cls={x.nhan_duoc ? "ok" : "red"}>{x.muc_ten}</Tag>
          {!x.nhan_duoc && <div className="muted">{x.ly_do.join(" · ")}</div>}</td>
        <td><button className="act grey" style={{ margin: 0 }} disabled={dang}
          onClick={() => soatXe(x.id)}>Xem cũ → mới</button></td>
      </tr>)}</tbody></table>
    {nutThoi}
  </div>);

  return (<div>
    <div className="muted">Lệnh #{lenh.id} · xe <b>{lenh.xe}</b> không đổi. Tài xế đang là <b>{lenh.tai_xe}</b>.</div>
    <table><thead><tr><th></th><th>Tài xế</th><th>Điều kiện</th></tr></thead>
      <tbody>{(ds?.tai_xe || []).map((t: any) => <tr key={t.id}>
        <td><input type="radio" name={"tx" + lenh.id} checked={chonTx === t.id}
          onChange={() => setChonTx(t.id)} /></td>
        <td>{t.ma} · {t.ten}</td>
        <td><Tag cls={t.nhan_duoc ? "ok" : "red"}>{t.nhan_duoc ? "nhận được" : "vướng"}</Tag>
          {t.ly_do.length > 0 && <div className="muted">{t.ly_do.join(" · ")}</div>}</td>
      </tr>)}</tbody></table>
    <div className="muted">Giá nội bộ <b>không đổi</b> — giá tính theo xe và tuyến, không theo người lái.</div>
    {ly_do_o}
    <button className="act teal" style={{ margin: "8px 0 0" }}
      disabled={dang || !ly.trim() || !chonTx}
      onClick={() => gui("doi-tai-xe", { tai_xe_id: chonTx })}>Xác nhận đổi tài xế</button>
    {nutThoi}
  </div>);
}

/** DL-4 · Xoá một lệnh điều xe CHƯA TỪNG CHẠY (Chủ tịch chọn 14/10/2026).
 *
 *  Hai bước chứ không một: bấm SOÁT trước, máy in ra nội dung lệnh và nói vướng gì; nút xoá chỉ
 *  hiện khi máy đã trả lời là xoá được. KHÔNG dùng hộp thoại xác nhận của trình duyệt — một hộp
 *  thoại bấm quen tay thì không còn là một lần cân nhắc.
 *
 *  Máy in cả nội dung lệnh ra trước khi xoá, vì `status` không chứng minh được gì: `DL-0825` mang
 *  chữ "hoàn thành" mà không có lấy một chuyến nào. Người bấm phải nhìn tận mắt tour, xe, tài xế,
 *  ngày và giá rồi mới quyết. */
function XoaLenh({ lenh, xong }: { lenh: any; xong: () => void }) {
  const { user, toast } = useShell();
  const [s, setS] = useState<any>(null);
  const [ly, setLy] = useState("");
  const [dang, setDang] = useState(false);
  // PHẢI khớp với XOA_LENH trong backend/app/api/v1/hr.py — có phép thử canh.
  const XOA_LENH_VAI = ["cntt", "chutich"];
  const quyen = XOA_LENH_VAI.includes(user?.role || "");

  const soat = async () => {
    setDang(true);
    try { setS(await api(`/dispatch/${lenh.id}/xoa-duoc`)); }
    catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };
  const xoa = async () => {
    setDang(true);
    try {
      const r: any = await api(`/dispatch/${lenh.id}?ly_do=${encodeURIComponent(ly)}`, { method: "DELETE" });
      toast(r.message); setS(null); setLy(""); xong();
    } catch (e) { toast(errMsg(e), true); } finally { setDang(false); }
  };

  if (!s) return <button className="act grey" style={{ margin: 0 }} disabled={dang}
    onClick={soat}>Xoá được không?</button>;
  return (<div>
    <div className={"gate " + (s.xoa_duoc ? "pass" : "fail")}>{s.noi}</div>
    {s.vuong?.length > 0 && <div className="muted">Đang vướng: {s.vuong.map((x: any) => `${x.so_dong} ${x.ten}`).join(" · ")}.</div>}
    {s.xoa_duoc && (quyen
      ? <>
        <label>Lý do xoá <span className="muted">(bắt buộc — tháng sau còn trả lời được vì sao
          chứng từ này biến mất)</span>
          <input value={ly} onChange={(e) => setLy(e.target.value)}
            placeholder="ví dụ: lệnh dữ liệu mẫu, chưa từng chạy" /></label>
        <button className="act orange" style={{ margin: "8px 0 0" }}
          disabled={dang || !ly.trim()} onClick={xoa}>Xoá lệnh #{lenh.id}</button>
      </>
      : <p className="muted">Xoá được, nhưng chỉ <b>CNTT</b> hoặc <b>Chủ tịch</b> bấm được nút xoá.</p>)}
    <p><button className="act grey" style={{ margin: "8px 0 0" }}
      onClick={() => { setS(null); setLy(""); }}>Thôi</button></p>
  </div>);
}

export default function Page() { return <Shell><LenhDieuXe /></Shell>; }
