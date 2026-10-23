"use client";
import { useCallback, useEffect, useState } from "react";
import Shell, { useShell } from "@/components/Shell";
import { api, fmtDT } from "@/lib/api";
import { Tag, errMsg } from "@/components/ui";

/** HỒ SƠ MỘT HƯỚNG DẪN VIÊN — trang riêng, đợt CUA-1 (22/10/2026).
 *
 *  Phần MÁY CHỦ xong từ đợt HD-14 (`services/ho_so_hdv.py`, `GET /api/v1/huong-dan/ho-so/{eid}`,
 *  16 phép thử trong `test_hd14_ho_so_hdv.py`). Thiếu đúng màn hình — không trang nào gọi cửa ấy.
 *
 *  BỐN LUẬT CỦA MÁY CHỦ, màn hình KHÔNG được làm hỏng cái nào:
 *
 *  1. KHÔNG CÓ NGƯỜI ẤY thì là 404, KHÔNG phải trang trống. Ghi chú của service nói rõ: *"trang
 *     trống nói «người này chưa có gì», còn sự thật là không có người này."* Màn này vì thế phân
 *     biệt 404 với «hồ sơ rỗng», và nói ra bằng hai câu khác nhau.
 *  2. CHƯA ĐỦ NGƯỠNG thì KHÔNG CÓ ĐIỂM, nhưng VẪN CÓ số lượt (`test_a1`, `test_a3`). Tuyệt đối
 *     không in 0 thay cho «chưa đủ» — `diem` là `null` và phải đọc là «chưa đủ lượt», khác hẳn
 *     «điểm bằng không». Máy chủ trả `nguong` để màn nói được còn thiếu BAO NHIÊU lượt.
 *  3. CHỈ NHẬN XÉT ĐÃ DUYỆT mới hiện (`test_b1`). Việc lọc nằm ở máy chủ; màn hình không tự thêm
 *     điều kiện công khai nào — `test_b2` canh đúng chỗ ấy.
 *  4. NHÃN NGƯỜI VIẾT KHÔNG MANG TÊN KHÁCH (`test_c1`). Máy chủ trả sẵn `nhan`; màn hình in
 *     nguyên văn và không ghép thêm gì vào đó.
 *
 *  MÀN CHỈ XEM, khai trong nhóm `HO_SO_NGUOI`. Thẻ hành nghề nhập ở Nhân sự; nhận xét do khách
 *  gửi sau tour và Phòng Hướng dẫn duyệt — hai cửa ấy nói ra ở cuối trang.
 */

type HoSo = {
  id: number; ma: string; ho_ten: string; phong_ban: string;
  the: { trang_thai: string; chu: string; so: string; loai: string };
  diem: { so_luot: number; du_nguong: boolean; diem: number | null; nguong: number };
  nhan_xet: { nhan_xet: string; diem: number | null; nhan: string; luc: string }[];
};

/* Trạng thái thẻ: máy chủ đã trả cả mã (`trang_thai`) và câu người đọc (`chu`). Màn hình chỉ chọn
   màu theo mã, và in `chu` nguyên văn — không viết lại câu, vì hai bản của cùng một câu là hai câu
   trả lời cho cùng một câu hỏi. */
const MAU_THE: Record<string, string> = {
  con_han: "ok", sap_han: "warn", het_han: "red", chua_co: "grey", khong_co: "grey",
};

function MotHoSo({ id }: { id: string }) {
  const { toast } = useShell();
  const [d, setD] = useState<HoSo | null | undefined>(undefined);
  const [khong, setKhong] = useState(false);

  const nap = useCallback(async () => {
    try {
      setD(await api<HoSo>("/huong-dan/ho-so/" + encodeURIComponent(id)));
    } catch (e: any) {
      /* 404 KHÁC mọi lỗi khác, và phải nói khác. Xem luật 1 ở đầu tệp. */
      if (e && e.status === 404) { setKhong(true); setD(null); return; }
      toast(errMsg(e), true);
      setD(null);
    }
  }, [id, toast]);
  useEffect(() => { nap(); }, [nap]);

  if (d === undefined) return <p className="muted">Đang tải…</p>;

  if (khong) return (<>
    <h1>Không có hồ sơ này</h1>
    <p className="panel">
      Mã <span className="mono">{id}</span> không ứng với hướng dẫn viên nào — hoặc người ấy không
      phải hướng dẫn viên.{" "}
      <span className="muted">Đây KHÔNG phải «hồ sơ chưa có gì»: nếu người ấy có mà hồ sơ rỗng thì
      trang vẫn mở, và nói rõ từng khối còn thiếu.</span>
    </p>
    <p><a href="/huong-dan">← Danh sách hướng dẫn viên</a></p>
  </>);

  if (d === null) return (<>
    <h1>Hồ sơ hướng dẫn viên</h1>
    <p className="muted">Không đọc được hồ sơ. Vai không được mở thì máy chủ trả 403.</p>
    <p><a href="/huong-dan">← Danh sách hướng dẫn viên</a></p>
  </>);

  const dm = d.diem || ({} as HoSo["diem"]);
  const thieu = Math.max(0, (dm.nguong ?? 0) - (dm.so_luot ?? 0));

  return (<>
    <h1>{d.ho_ten} <span className="muted" style={{ fontSize: "calc(15/14*1rem)" }}>
      · {d.ma || "chưa có mã"}</span></h1>
    <p className="muted">{d.phong_ban || "chưa gắn phòng ban"}</p>

    {/* ── KHỐI 1 · THẺ HÀNH NGHỀ ─────────────────────────────────────────────────────────── */}
    <h2>Thẻ hành nghề</h2>
    <div className="panel">
      <Tag cls={MAU_THE[d.the?.trang_thai] || "grey"}>{d.the?.trang_thai || "chưa rõ"}</Tag>{" "}
      {d.the?.chu && <span>{d.the.chu}</span>}
      <div className="wrap" style={{ marginTop: 10 }}><table><tbody>
        <tr><td style={{ width: 170 }} className="muted">Số thẻ</td>
          <td className="mono">{d.the?.so || <span className="muted">chưa có</span>}</td></tr>
        <tr><td className="muted">Loại thẻ</td>
          <td>{d.the?.loai || <span className="muted">chưa có</span>}</td></tr>
      </tbody></table></div>
    </div>

    {/* ── KHỐI 2 · ĐIỂM SAU TOUR ─────────────────────────────────────────────────────────── */}
    <h2>Điểm sau tour</h2>
    <div className="panel">
      {dm.du_nguong
        ? <>
            <span style={{ fontSize: "calc(26/14*1rem)", fontWeight: 700 }}>{dm.diem}</span>
            <span className="muted"> / 5 · từ {dm.so_luot} lượt đánh giá</span>
          </>
        : <>
            {/* LUẬT 2. KHÔNG in 0. «Chưa đủ lượt» và «điểm bằng không» là hai câu khác nhau. */}
            <Tag cls="warn">chưa đủ lượt để có điểm</Tag>
            <div style={{ marginTop: 6 }}>
              Đã có <b>{dm.so_luot ?? 0}</b> lượt đánh giá, ngưỡng hiện điểm là <b>{dm.nguong}</b> —
              {thieu > 0 ? <> còn thiếu <b>{thieu}</b> lượt nữa.</> : <> đã đủ, điểm sẽ hiện ở lượt tải sau.</>}
            </div>
            <p className="muted" style={{ marginTop: 6 }}>
              Ngưỡng tồn tại để một hai lượt lẻ không thành một con điểm: dưới ngưỡng thì điểm nói
              nhiều hơn nó biết.
            </p>
          </>}
    </div>

    {/* ── KHỐI 3 · NHẬN XÉT ĐÃ CÔNG KHAI ─────────────────────────────────────────────────── */}
    <h2>Nhận xét đã công khai ({(d.nhan_xet || []).length})</h2>
    {(d.nhan_xet || []).length
      ? (d.nhan_xet).map((n, i) => (
          <div className="panel" key={i}>
            <div style={{ display: "flex", gap: 10, alignItems: "baseline", flexWrap: "wrap" }}>
              {/* LUẬT 4 · `nhan` do máy chủ dựng và KHÔNG mang tên khách. In nguyên văn. */}
              <b>{n.nhan}</b>
              {n.diem !== null && n.diem !== undefined && <Tag cls="ok">{n.diem}/5</Tag>}
              <span className="muted">{n.luc ? fmtDT(n.luc) : ""}</span>
            </div>
            <div style={{ marginTop: 6 }}>{n.nhan_xet}</div>
          </div>))
      : <p><Tag cls="warn">chưa có</Tag> Chưa có nhận xét nào được duyệt công khai.
          <span className="muted"> Khách có thể đã gửi nhận xét mà Phòng Hướng dẫn chưa duyệt —
          màn này chỉ hiện phần đã duyệt.</span></p>}

    {/* ── KHỐI 4 · SỐ NÀY SỬA Ở ĐÂU ──────────────────────────────────────────────────────── */}
    <h2>Số trên hồ sơ này sửa ở đâu</h2>
    <p className="muted">
      Trang này <b>chỉ xem</b>. Họ tên, mã, phòng ban và thẻ hành nghề nhập tại{" "}
      <b>Nhân sự → Hồ sơ nhân viên</b>. Điểm và nhận xét không ai gõ tay được: khách gửi sau tour,
      Phòng Hướng dẫn duyệt công khai tại <b><a href="/duyet-cong-bo">Duyệt công bố</a></b> — điểm
      là số máy tính từ các lượt đã duyệt.
    </p>
    <p><a href="/huong-dan">← Danh sách hướng dẫn viên</a></p>
  </>);
}

export default function Page({ params }: { params: { id: string } }) {
  return <Shell><MotHoSo id={params.id} /></Shell>;
}
