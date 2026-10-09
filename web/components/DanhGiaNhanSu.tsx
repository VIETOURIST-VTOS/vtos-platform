"use client";
import { useEffect, useState } from "react";
import { api, getUser } from "@/lib/api";

/** 5.6 Đánh giá nhân sự — hai thành phần, hai màn hình, hai nhóm người.
 *
 *  `BangChamDiem`  đứng ở /hr thẻ "Đánh giá & sự vụ" — người CHẤM và người đọc tổng hợp.
 *  `DanhGiaCuaToi` đứng ở /cham-cong — MỌI nhân viên đọc bản của chính mình (Chủ tịch chốt 08/10/2026).
 *
 *  BA Ô MÁY ĐIỀN HIỆN RA NHƯNG KHÔNG SỬA ĐƯỢC, và màn hình phải NÓI RA điều đó cùng với NGUỒN của
 *  từng ô. Một ô điểm không nói được nguồn thì người bị chấm 2 điểm không có cách nào cãi — và một
 *  thang điểm không cãi được thì không ai tin, kể cả khi nó đúng.
 *
 *  Ô "chưa có số" in bằng chữ, KHÔNG in số 0: hai thứ ấy khác nhau, và gộp chúng lại là biến một
 *  chỗ VTOS chưa đo được thành một điểm kém của người đi làm.
 */

type O = { diem: number | null; nguon?: string; ly_do?: string };
type Ban = any;

const A = ["a1", "a2", "a3"] as const;
const B = ["b1", "b2", "b3"] as const;

function Diem({ v }: { v: number | null | undefined }) {
  if (v === null || v === undefined) return <i className="muted">chưa có số</i>;
  return <b>{v}</b>;
}

export function DanhGiaCuaToi() {
  const [rows, setRows] = useState<Ban[]>([]);
  const [loi, setLoi] = useState("");
  useEffect(() => {
    api<{ rows: Ban[] }>("/danh-gia-cua-toi")
      .then((r) => setRows(r.rows || []))
      .catch((e) => setLoi(String(e?.message || e)));
  }, []);
  return (
    <section>
      <h2>Đánh giá của tôi</h2>
      <p className="muted">
        Bản đánh giá của chính bạn, từ kỳ trưởng phòng đã chấm xong. <b>Ba ô đầu do hệ thống điền</b> từ
        số có sẵn (chỉ tiêu, chấm công, sổ sự vụ) — trưởng phòng không sửa được, và nguồn của từng ô in
        ngay cạnh điểm. <b>Ba ô sau do trưởng phòng chấm</b>, kèm lý do bắt buộc khi cho 5 điểm hoặc
        1–2 điểm. Điểm <b>chỉ để xét</b> thưởng: mức thưởng do TGĐ / Chủ tịch quyết, không có công
        thức nào trong phần mềm biến điểm thành tiền.
      </p>
      {loi && <p className="loi">{loi}</p>}
      {!loi && rows.length === 0 && (
        <p className="muted">Chưa có bản đánh giá nào đã chấm xong cho bạn.</p>
      )}
      {rows.map((r) => (
        <div key={r.id} className="the">
          <h3>
            Kỳ {r.ky} · {r.xep_hang_ten || "chưa đủ điểm"}{" "}
            {r.diem_tong !== null && <>· điểm tổng <b>{r.diem_tong}</b></>}
          </h3>
          <table className="bang">
            <thead><tr><th>Tiêu chí</th><th>Điểm</th><th>Nguồn / lý do</th></tr></thead>
            <tbody>
              {A.map((k) => (
                <tr key={k}>
                  <td>{k.toUpperCase()}</td>
                  <td><Diem v={r[`${k}_diem`]} /></td>
                  <td className="muted">{r[`${k}_nguon`]}</td>
                </tr>
              ))}
              {B.map((k) => (
                <tr key={k}>
                  <td>{k.toUpperCase()}</td>
                  <td><Diem v={r[`${k}_diem`]} /></td>
                  <td>{r[`${k}_ly_do`] || <i className="muted">không ghi</i>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {r.thieu_ky_con && (
            <p className="canh-bao">
              Kỳ tổng hợp này <b>thiếu kỳ con</b>: {r.thieu_ky_con}. Trung bình ở trên tính trên các kỳ
              đã có, không phải trên đủ kỳ.
            </p>
          )}
          {r.viec_phai_sua && <p><b>Việc phải sửa kỳ tới:</b> {r.viec_phai_sua}</p>}
          {r.nhan_xet && <p><b>Nhận xét:</b> {r.nhan_xet}</p>}
          {r.de_xuat && <p><b>Đề xuất:</b> {r.de_xuat}</p>}
        </div>
      ))}
    </section>
  );
}

export function BangChamDiem() {
  const u = getUser();
  const [ky, setKy] = useState(() => new Date().toISOString().slice(0, 7));
  const [kyLoai, setKyLoai] = useState("thang");
  const [rows, setRows] = useState<Ban[]>([]);
  const [lech, setLech] = useState<any>(null);
  const [thieu, setThieu] = useState<any>(null);
  const [khongAiCham, setKhongAiCham] = useState<any[]>([]);
  const [loi, setLoi] = useState("");

  async function nap() {
    setLoi("");
    try {
      const r = await api<{ rows: Ban[] }>(
        `/api/v1/danh-gia-ns?ky_loai=${kyLoai}&ky=${encodeURIComponent(ky)}`);
      setRows(r.rows || []);
      setLech(await api(`/danh-gia-ns/do-lech?ky_loai=${kyLoai}&ky=${encodeURIComponent(ky)}`));
      if (kyLoai === "thang") {
        setThieu(await api(`/danh-gia-ns/thieu-nguon?ky=${encodeURIComponent(ky)}`));
      } else setThieu(null);
      const k = await api<{ rows: any[] }>("/danh-gia-ns/phong-khong-ai-cham");
      setKhongAiCham(k.rows || []);
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }
  useEffect(() => { nap(); /* eslint-disable-next-line */ }, [ky, kyLoai]);

  async function luu(r: Ban, o: any) {
    try {
      await api("/danh-gia-ns/cham", {
        method: "POST",
        json: { employee_id: r.employee_id, ky_loai: kyLoai, ky, ...o },
      });
      nap();
    } catch (e: any) { setLoi(String(e?.message || e)); }
  }

  async function gui(r: Ban) {
    try { await api(`/danh-gia-ns/${r.id}/gui`, { method: "POST" }); nap(); }
    catch (e: any) { setLoi(String(e?.message || e)); }
  }

  return (
    <section>
      <h2>Đánh giá nhân sự theo kỳ</h2>
      <p className="muted">
        Sáu tiêu chí, thang 1–5. <b>A1–A3 do hệ thống điền</b> và không sửa được — chúng là cái neo để
        đo độ lệch khi điểm bắt đầu dùng xét thưởng. <b>B1–B3 do bạn chấm</b>; cho 5 điểm hoặc 1–2 điểm
        thì bắt buộc ghi lý do. Kỳ quý và năm <b>tự tổng hợp</b> từ kỳ con, thiếu kỳ nào thì nói ra kỳ ấy.
      </p>
      <div className="hang">
        <label>Loại kỳ{" "}
          <select value={kyLoai} onChange={(e) => setKyLoai(e.target.value)}>
            <option value="thang">Tháng</option>
            <option value="quy">Quý</option>
            <option value="nam">Năm</option>
          </select>
        </label>
        <label>Kỳ{" "}
          <input value={ky} onChange={(e) => setKy(e.target.value)}
                 placeholder={kyLoai === "thang" ? "2026-10" : kyLoai === "quy" ? "2026-Q4" : "2026"} />
        </label>
        <button onClick={nap}>Xem</button>
      </div>
      {loi && <p className="loi">{loi}</p>}

      {khongAiCham.length > 0 && (
        <p className="canh-bao">
          <b>Phòng không ai chấm được:</b>{" "}
          {khongAiCham.map((p: any) => `${p.phong || p.department} (vai ${p.vai || p.vai_ky})`).join(", ")}.
          Bảng của cả phòng ấy sẽ nằm im — HCNS cấp một tài khoản giữ vai đó thì thông.
        </p>
      )}
      {thieu && thieu.tong_thieu && (thieu.tong_thieu.a1 > 0 || thieu.tong_thieu.a2 > 0) && (
        <div className="the">
          <h3>Chỗ VTOS chưa có số</h3>
          <p className="muted">
            Đây là <b>việc còn phải làm</b>, không phải ô trống. Ô không có số thì không kéo điểm tổng
            xuống — nhưng cũng không ai đo được phần ấy.
          </p>
          <ul>
            {["a1", "a2"].map((o) =>
              Object.entries(thieu.theo_o?.[o] || {}).map(([ly, n]: any) => (
                <li key={o + ly}><b>{o.toUpperCase()}</b> · {n} người — {ly}</li>
              )))}
          </ul>
        </div>
      )}

      <table className="bang">
        <thead>
          <tr>
            <th>Người</th><th>A1</th><th>A2</th><th>A3</th>
            <th>B1</th><th>B2</th><th>B3</th><th>Tổng</th><th>Trạng thái</th><th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.ho_ten} <span className="muted">{r.ma_nv}</span></td>
              {A.map((k) => (
                <td key={k} title={r[`${k}_nguon`]}><Diem v={r[`${k}_diem`]} /></td>
              ))}
              {B.map((k) => (
                <td key={k}>
                  <select value={r[`${k}_diem`] ?? ""} disabled={r.trang_thai === "da_gui"}
                          onChange={(e) => luu(r, { [`${k}_diem`]: e.target.value === "" ? null : Number(e.target.value) })}>
                    <option value="">—</option>
                    {[5, 4, 3, 2, 1].map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                </td>
              ))}
              <td>{r.diem_tong ?? <i className="muted">—</i>}</td>
              <td>
                {r.trang_thai_ten}
                {r.thieu_chu?.length > 0 && (
                  <div className="canh-bao">Còn thiếu: {r.thieu_chu.join("; ")}</div>
                )}
              </td>
              <td>
                {r.trang_thai !== "da_gui" && (
                  <button onClick={() => gui(r)} disabled={r.thieu_chu?.length > 0}>Gửi HCNS</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && <p className="muted">Kỳ này chưa mở bảng chấm cho ai.</p>}

      {lech && Object.keys(lech.theo_nguoi_cham || {}).length > 0 && (
        <div className="the">
          <h3>Độ lệch điểm người − điểm máy</h3>
          <p className="muted">
            Ba ô máy điền không ai sửa được, nên chúng là <b>cái neo</b>. Ai chấm tay cao hơn số máy một
            cách đều đặn thì hiện ra ngay kỳ sau, không phải đợi hết năm. Kỳ đầu — kỳ chưa nối thưởng —
            là <b>mốc so</b>.
          </p>
          <table className="bang">
            <thead><tr><th>Người chấm</th><th>Vai</th><th>Số bản</th><th>Lệch trung bình</th></tr></thead>
            <tbody>
              {Object.entries(lech.theo_nguoi_cham).map(([ten, g]: any) => (
                <tr key={ten}>
                  <td>{ten}</td><td>{g.vai}</td><td>{g.so_ban}</td>
                  <td>{g.lech_tb > 0 ? `+${g.lech_tb}` : g.lech_tb}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
