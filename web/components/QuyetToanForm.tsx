"use client";
/** BIỂU NHẬP TAY QUYẾT TOÁN TOUR – hai hình thức trong nước / nước ngoài.
 *
 * VÌ SAO CÓ BIỂU NÀY DÙ ĐÃ CÓ CỬA TẢI TỆP
 *
 * Cửa tải tệp hợp với người đã có sẵn một tệp Excel điền xong. Nhưng phần lớn chuyến lẻ thì điều
 * hành viên ngồi nhập thẳng, từng dòng một, ngay khi chuyến vừa về – không ai mở Excel ra điền rồi
 * tải lên cho một chuyến 12 khách. Không có biểu nhập tay thì họ vẫn phải đi qua Excel, và cái tệp
 * Excel ấy lại trở thành bản gốc nằm ngoài hệ thống, đúng chỗ mà cả đợt này sinh ra để chấm dứt.
 *
 * BỐN NGUYÊN TẮC, GIỐNG HỆT MẪU EXCEL
 *
 * 1. MÁY CỘNG, NGƯỜI KHÔNG GÕ TỔNG. Biểu này KHÔNG có một ô nào cho gõ tổng. Thành tiền của dòng do
 *    máy chủ nhân ra từ đơn giá × số lượng × hệ số; tổng của chuyến do máy chủ cộng từ các dòng. Đo
 *    trên tệp thật: ô tổng một nhóm chi ghi 3.990.000 trong khi năm dòng của chính nhóm ấy cộng lại
 *    được 4.200.000 – con số sai đi thẳng vào giá vốn mà mọi tầng vẫn cân.
 *
 * 2. RỖNG KHÁC KHÔNG. Ô tiền để trống nghĩa là CHƯA NHẬP, không phải 0 đồng. Mọi ô tiền đi qua
 *    soTien() của lib/api – Number("") bằng 0 chứ không phải NaN, và đó là lý do xưa nay không ai
 *    phân biệt được "chưa nhập" với "bằng 0".
 *
 * 3. CHỌN, KHÔNG GÕ. Khoản mục chọn từ danh mục 55 mã; nhà cung cấp gõ vài chữ rồi chọn, máy điền
 *    hộ mã số thuế và tên pháp nhân. Không có ô nào cho gõ tay mã số thuế: mười chữ số gõ lại ở
 *    từng dòng là cách chắc chắn để có mã sai một chữ số, mà mã sai thì hoá đơn không khấu trừ được
 *    và chỉ lộ ra vào lúc quyết toán thuế.
 *
 * 4. HAI HÌNH THỨC, MỘT BIỂU. Cột ngoại tệ và mục "Chi theo khách" chỉ hiện với tour nước ngoài.
 *    Dựng hai biểu chép đôi thì lần sau sửa một quy tắc sẽ sửa ở một bản và quên bản kia.
 */
import { useCallback, useEffect, useState } from "react";
import { api, vnd, soTien, fmtDT } from "@/lib/api";
import { errMsg } from "@/components/ui";

type Kieu = "chu" | "so" | "tien" | "ngay" | "gio" | "chon" | "ncc" | "co";

export type Cot = {
  khoa: string;
  nhan: string;
  kieu?: Kieu;
  chon?: [string, string][];
  rong?: number;          // px
  batBuoc?: boolean;
  chuThich?: string;
  chiNN?: boolean;        // chỉ hiện ở tour nước ngoài
  chiMay?: boolean;       // máy tính ra – chỉ hiện ở bảng đã ghi, không có ô nhập
};

const TIEN_TE: [string, string][] = [["", "VND"], ["USD", "USD"], ["EUR", "EUR"], ["GBP", "GBP"],
                                     ["SGD", "SGD"], ["THB", "THB"], ["JPY", "JPY"], ["CNY", "CNY"]];

/** Đọc một ô theo kiểu. Tiền và số dùng soTien: ô trống ra rỗng, KHÔNG ra 0. */
function docO(kieu: Kieu | undefined, v: FormDataEntryValue | null) {
  const s = v === null ? "" : String(v).trim();
  if (kieu === "tien" || kieu === "so") return soTien(s);
  if (kieu === "co") return s === "on" ? 1 : 0;
  return s === "" ? null : s;
}

// ---------------------------------------------------------------------------------------------
// Ô chọn nhà cung cấp – gõ vài chữ, chọn, máy điền hộ mã số thuế
// ---------------------------------------------------------------------------------------------

function ONcc({ onChon }: { onChon: (s: any | null) => void }) {
  const [tim, setTim] = useState("");
  const [ds, setDs] = useState<any[]>([]);
  const [chon, setChon] = useState<any | null>(null);
  useEffect(() => {
    if (chon || tim.trim().length < 2) { setDs([]); return; }
    const h = setTimeout(() => {
      api(`/quyet-toan-lop3/tra-ncc?tim=${encodeURIComponent(tim.trim())}`)
        .then((r: any) => setDs(r.dong || [])).catch(() => setDs([]));
    }, 250);
    return () => clearTimeout(h);
  }, [tim, chon]);

  if (chon) return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
      <b style={{ fontSize: 12 }}>{chon.ten}</b>
      {/* Nói ra chỗ THIẾU ngay tại ô chọn. Người nhập biết trước khi dùng, thay vì phát hiện lúc
          kê khai thuế rằng nhà cung cấp này chưa có mã số thuế. */}
      <span className="muted" style={{ fontSize: 11 }}>
        {chon.ma_so_thue ? `MST ${chon.ma_so_thue}` : "chưa có MST"}
        {chon.ten_phap_nhan && chon.ten_phap_nhan !== chon.ten ? ` · ${chon.ten_phap_nhan}` : ""}
      </span>
      {chon.thieu?.length > 0 && (
        <span className="tag" title="Hồ sơ nhà cung cấp còn thiếu – sửa ở màn hình Nhà cung cấp">
          thiếu {chon.thieu.join(", ")}
        </span>
      )}
      <button type="button" className="act grey" style={{ margin: 0, padding: "2px 8px" }}
              onClick={() => { setChon(null); setTim(""); onChon(null); }}>đổi</button>
    </div>
  );

  return (
    <div style={{ position: "relative" }}>
      <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="gõ tên NCC…"
             style={{ width: "100%" }} />
      {ds.length > 0 && (
        <div className="panel" style={{ position: "absolute", zIndex: 20, top: "100%", left: 0,
                                        minWidth: 300, maxHeight: 220, overflow: "auto", padding: 4 }}>
          {ds.map((s) => (
            <button key={s.supplier_id} type="button" className="act grey"
                    style={{ display: "block", width: "100%", textAlign: "left", margin: "2px 0" }}
                    onClick={() => { setChon(s); setDs([]); onChon(s); }}>
              {s.ten}
              <span className="muted" style={{ fontSize: 11 }}>
                {" "}{s.ma_so_thue || "(chưa có MST)"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Bảng nhập dùng chung: danh sách dòng đã ghi + MỘT dòng để thêm
// ---------------------------------------------------------------------------------------------

function BangNhap({ tieuDe, giaiThich, cot, dong, nn, them, dangGhi, tong }: {
  tieuDe: string; giaiThich?: string; cot: Cot[]; dong: any[]; nn: boolean;
  them: (d: Record<string, any>) => Promise<void>; dangGhi: boolean;
  tong?: { nhan: string; gia: any }[];
}) {
  const [ncc, setNcc] = useState<any | null>(null);
  const hien = cot.filter((c) => !c.chiNN || nn);
  const nhap = hien.filter((c) => !c.chiMay);

  const guiDi = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = e.currentTarget;
    const fd = new FormData(f);
    const d: Record<string, any> = {};
    nhap.forEach((c) => { d[c.khoa] = docO(c.kieu, fd.get(c.khoa)); });
    if (ncc) d.supplier_id = ncc.supplier_id;
    await them(d);
    f.reset();
    setNcc(null);
  };

  return (
    <div className="panel" style={{ marginBottom: 14 }}>
      <h3 style={{ margin: "0 0 4px" }}>{tieuDe}</h3>
      {giaiThich && <p className="muted" style={{ marginTop: 0 }}>{giaiThich}</p>}

      {dong.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead><tr>{hien.map((c) => <th key={c.khoa}>{c.nhan}</th>)}</tr></thead>
            <tbody>
              {dong.map((r, i) => (
                <tr key={r.id ?? i}>
                  {hien.map((c) => (
                    <td key={c.khoa} style={{ textAlign: c.kieu === "tien" ? "right" : undefined }}>
                      {c.kieu === "tien"
                        ? (r[c.khoa] === null || r[c.khoa] === undefined ? "—" : vnd(r[c.khoa]))
                        : c.kieu === "co" ? (r[c.khoa] ? "x" : "")
                        : (r[c.khoa] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            {tong && tong.length > 0 && (
              <tfoot>
                <tr>
                  <td colSpan={Math.max(1, hien.length - tong.length)}><b>CỘNG</b></td>
                  {tong.map((t) => (
                    <td key={t.nhan} style={{ textAlign: "right" }}>
                      <b title={t.nhan}>{t.gia === null || t.gia === undefined ? "—" : vnd(t.gia)}</b>
                    </td>
                  ))}
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}

      <form onSubmit={guiDi} style={{ marginTop: 8 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
          {nhap.map((c) => (
            <div key={c.khoa} style={{ minWidth: c.rong || 120 }}>
              <label title={c.chuThich}>
                {c.nhan}{c.batBuoc ? " *" : ""}
                {c.chuThich && <span className="muted"> ⓘ</span>}
              </label>
              {c.kieu === "ncc" ? <ONcc onChon={setNcc} />
                : c.kieu === "chon" ? (
                  <select name={c.khoa} required={c.batBuoc} defaultValue="">
                    <option value="">—</option>
                    {(c.khoa === "tien_te" ? TIEN_TE : c.chon || []).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                ) : c.kieu === "co" ? <input type="checkbox" name={c.khoa} />
                : (
                  <input name={c.khoa} required={c.batBuoc}
                         type={c.kieu === "ngay" ? "date" : c.kieu === "gio" ? "time"
                               : c.kieu === "tien" || c.kieu === "so" ? "number" : "text"}
                         step={c.kieu === "tien" ? "1" : c.kieu === "so" ? "any" : undefined}
                         style={{ width: "100%" }} />
                )}
            </div>
          ))}
          <button className="act" disabled={dangGhi} style={{ margin: 0 }}>
            {dangGhi ? "Đang ghi…" : "Thêm dòng"}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------
// Biểu chính
// ---------------------------------------------------------------------------------------------

// ---------------------------------------------------------------------------------------------
// TIỀN TIP — Đ-6, Chủ tịch chốt 12/9/2026
// ---------------------------------------------------------------------------------------------
//
//   "tiền tip tour châu Âu chia 1 phần với công ty"
//   "tỷ lệ chia tiền tip em cài phép toán và form sẵn cho điều hành tự nhập % vào ô đó"
//
// BA THỨ Ở ĐÂY LÀ CỐ Ý, không phải cho đẹp:
//
//  1. ĐƠN VỊ LÀ Ô BẮT BUỘC, và không có lựa chọn mặc định. Chính tệp châu Âu 6 nước ghi cùng một
//     khoản 810 € bằng HAI đơn vị: sheet QT ghi 27 €/khách/CHUYẾN, sheet Quyết toán TL ghi
//     3 €/khách/NGÀY × 9 ngày. Gõ 27 vào ô "mỗi ngày" là ra GẤP CHÍN LẦN, và con số ấy vẫn trông
//     hợp lệ. Bỏ trống thì phép tính dừng chứ máy không đoán.
//
//  2. XEM TRƯỚC RỒI MỚI GHI. Nút "Tính thử" không chạm vào cơ sở dữ liệu. Người nhập nhìn thấy
//     "đã thu X, công ty Y, trưởng đoàn Z" rồi mới bấm ghi.
//
//  3. Ô % LÀ PHẦN TRĂM, KHÔNG CÓ LUẬT NGẦM. Gõ 40 là 40%, gõ 0,4 là 0,4%. Máy chủ nói ra khi thấy
//     số nhỏ hơn 1 nhưng KHÔNG tự sửa số của người ta.
function TienTip({ tourId, nn, toast, xong }: {
  tourId: number; nn: boolean; toast: (m: string, e?: boolean) => void; xong: () => void;
}) {
  const [v, setV] = useState<any>({ don_vi: "" });
  const [kq, setKq] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const o = (k: string) => (e: any) => { setV({ ...v, [k]: e.target.value }); setKq(null); };

  const goi = async (duong: string) => {
    setBusy(true);
    try {
      const r = await api(`/quyet-toan-lop3/${tourId}/tip${duong}`, {
        method: "POST",
        json: {
          don_gia: soTien(v.don_gia), don_vi: v.don_vi || null,
          so_khach: soTien(v.so_khach), so_ngay: soTien(v.so_ngay),
          ty_gia: soTien(v.ty_gia), tien_te: v.tien_te || null,
          ty_le_phan_tram: v.ty_le_phan_tram || null,
        },
      });
      setKq(r);
      if (duong === "") { toast("Đã ghi phần tiền tip của công ty vào doanh thu"); xong(); }
    } catch (e) { toast(errMsg(e), true); } finally { setBusy(false); }
  };

  return (
    <div className="panel wrap">
      <h3 style={{ margin: "0 0 4px" }}>Tiền tip – chia với trưởng đoàn</h3>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 8px" }}>
        Tiền tip là tiền của KHÁCH trả cho hướng dẫn viên, công ty giữ hộ. Chỉ phần công ty giữ lại
        sau khi chia mới vào doanh thu; phần của trưởng đoàn là khoản phải trả, đi vào bản chốt công
        nợ TL.
      </p>
      <div className="row" style={{ gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>Đơn giá<input value={v.don_gia || ""} onChange={o("don_gia")} style={{ width: 110 }} /></label>
        <label>
          Đơn vị{" "}
          <select value={v.don_vi || ""} onChange={o("don_vi")} style={{ width: 210 }}>
            <option value="">— chọn —</option>
            <option value="moi_khach_ca_chuyen">mỗi khách CẢ CHUYẾN</option>
            <option value="moi_khach_moi_ngay">mỗi khách mỗi NGÀY</option>
          </select>
        </label>
        <label>Số khách<input value={v.so_khach || ""} onChange={o("so_khach")} style={{ width: 90 }} /></label>
        {v.don_vi === "moi_khach_moi_ngay" && (
          <label>Số ngày<input value={v.so_ngay || ""} onChange={o("so_ngay")} style={{ width: 90 }} /></label>
        )}
        {nn && <>
          <label>Tiền tệ<input value={v.tien_te || ""} onChange={o("tien_te")} style={{ width: 80 }} /></label>
          <label>Tỷ giá<input value={v.ty_gia || ""} onChange={o("ty_gia")} style={{ width: 110 }} /></label>
        </>}
        <label>
          Phần công ty (%)
          <input value={v.ty_le_phan_tram || ""} onChange={o("ty_le_phan_tram")} style={{ width: 90 }}
                 placeholder="vd 40" />
        </label>
        <button className="grey" disabled={busy} onClick={() => goi("/xem-truoc")}>Tính thử</button>
        <button disabled={busy || !kq || !!kq?.chua_chia} onClick={() => goi("")}>Ghi vào doanh thu</button>
      </div>

      {kq && (kq.chua_chia ? (
        <div className="gate warn" style={{ marginTop: 8 }}>
          {kq.tong != null && <><b>Đã thu {vnd(kq.tong)}</b>. </>}{kq.vi_sao}
        </div>
      ) : (
        <div className="gate ok" style={{ marginTop: 8 }}>
          <b>Đã thu {vnd(kq.tong)}</b> · công ty <b>{vnd(kq.cong_ty)}</b> ({kq.ty_le_phan_tram}%)
          {" "}· trưởng đoàn <b>{vnd(kq.truong_doan)}</b>
          <div className="muted" style={{ fontSize: 12 }}>
            Tỷ lệ lấy từ: {kq.nguon_ty_le === "go_tren_chuyen" ? "ô vừa gõ trên chuyến này"
              : "tham số công ty đang hiệu lực"}. Ai gõ và gõ lúc nào sẽ vào sổ dấu vết.
          </div>
        </div>
      ))}
      {kq?.canh_bao?.map((c: string, i: number) => (
        <div key={i} className="gate warn" style={{ marginTop: 6 }}>{c}</div>
      ))}
    </div>
  );
}


export default function QuyetToanForm({ tourId, toast }: {
  tourId: number; toast: (m: string, err?: boolean) => void;
}) {
  // HÌNH THỨC LẤY TỪ MÁY CHỦ, không nhận từ màn hình gọi.
  //
  // Nó quyết định biểu có cột ngoại tệ hay không, có mục "chi theo từng khách" hay không, và tỷ lệ
  // giá trẻ em đem ra soát (trong nước 80%, nước ngoài 90%). Nhận từ bên ngoài thì một chỗ gọi
  // quên truyền là cả biểu dựng sai hình mà không có gì báo.
  const [hinhThuc, setHinhThuc] = useState<string>("");
  const nn = hinhThuc === "nuoc_ngoai";
  const [dm, setDm] = useState<any>(null);
  const [kh, setKh] = useState<any>(null);
  const [dt, setDt] = useState<any>(null);
  const [chi, setChi] = useState<any>(null);
  const [pt, setPt] = useState<any>(null);
  const [hdv, setHdv] = useState<any>(null);
  const [ck, setCk] = useState<any>(null);
  const [sg, setSg] = useState<any>(null);
  const [dv, setDv] = useState<any>(null);
  const [ghi, setGhi] = useState(false);

  const nap = useCallback(async () => {
    const g = (p: string) => api(`/quyet-toan-lop3/${p}`).catch(() => null);
    const [a, b, c, d, e, f, s] = await Promise.all([
      g(`${tourId}/khach`), g(`${tourId}/doanh-thu`), g(`${tourId}/chi`),
      g(`${tourId}/phuong-tien`), g(`${tourId}/hdv-chi`),
      nn ? g(`${tourId}/khach-chi-phi`) : Promise.resolve(null), g(`${tourId}/soat-gia`),
    ]);
    setKh(a); setDt(b); setChi(c); setPt(d); setHdv(e); setCk(f); setSg(s);
    g(`${tourId}/dau-vet`).then(setDv);
    if (s?.hinh_thuc) setHinhThuc(s.hinh_thuc);
  }, [tourId, nn]);

  // Khai hình thức. Lần đầu trên tờ trắng thì không hỏi lý do; máy chủ mới là nơi quyết định khi
  // nào cần lý do (tờ đã có dòng), màn hình chỉ chuyển tiếp thông báo của nó.
  const datHinhThuc = async (ht: "trong_nuoc" | "nuoc_ngoai") => {
    setGhi(true);
    try {
      await api(`/quyet-toan-lop3/${tourId}/hinh-thuc`, { method: "PUT", json: { hinh_thuc: ht } });
      setHinhThuc(ht);
      toast(ht === "nuoc_ngoai" ? "Đã khai: tour nước ngoài" : "Đã khai: tour trong nước");
      await nap();
    } catch (e) { toast(errMsg(e), true); } finally { setGhi(false); }
  };

  useEffect(() => { nap(); }, [nap]);
  useEffect(() => {
    api(`/quyet-toan-lop3/danh-muc?hinh_thuc=${hinhThuc || ""}`).then(setDm).catch(() => setDm(null));
  }, [hinhThuc]);

  if (!dm) return <p className="muted">Đang tải danh mục…</p>;

  // CHƯA KHAI HÌNH THỨC – hỏi ngay tại đây, không đẩy người dùng đi tìm chỗ khác.
  //
  // Bản trước bảo "khai ở tab Thông tin trước", nhưng tab ấy KHÔNG có ô hình thức và máy chủ cũng
  // chưa có cửa ghi – nên lời chặn ấy là một ngõ cụt: cả 5 chuyến trên máy đều rỗng hình thức và
  // không ai khai được. Hỏi tại chỗ vừa mở được biểu, vừa giữ nguyên nguyên tắc: người khai, máy
  // không tự suy.
  if (!hinhThuc) return (
    <div className="gate warn">
      <b>Chuyến này chưa khai HÌNH THỨC.</b>
      <p className="muted">
        Biểu quyết toán dựng theo hình thức: tour nước ngoài có cột ngoại tệ, bắt buộc tỷ giá và
        ngày tỷ giá cho mọi khoản; tour trong nước thì không. Giá trẻ em cũng soát theo tỷ lệ khác
        nhau (trong nước 80%, nước ngoài 90%). Chọn một lần, sau đó biểu mở ra.
      </p>
      {sg?.goi_y_hinh_thuc && (
        <p className="muted">
          Máy đoán đây là tour{" "}
          <b>{sg.goi_y_hinh_thuc === "nuoc_ngoai" ? "NƯỚC NGOÀI" : "TRONG NƯỚC"}</b>
          {sg.nuoc ? <> (nước ghi trên chuyến: {sg.nuoc})</> : null}. Đoán để đỡ phải nghĩ, không
          phải để thay người khai – anh/chị vẫn bấm chọn.
        </p>
      )}
      {sg?.nhap_duoc === false ? (
        <p className="muted">Vai trò của anh/chị không khai được hình thức. Việc này thuộc phòng
          Điều hành và Kế toán.</p>
      ) : (
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button disabled={ghi} onClick={() => datHinhThuc("trong_nuoc")}>
            Tour TRONG NƯỚC
          </button>
          <button disabled={ghi} onClick={() => datHinhThuc("nuoc_ngoai")}>
            Tour NƯỚC NGOÀI
          </button>
        </div>
      )}
    </div>
  );

  const chonTu = (o: Record<string, string> | string[] | undefined): [string, string][] => {
    if (!o) return [];
    return Array.isArray(o) ? o.map((x) => [x, x] as [string, string])
                            : Object.entries(o).map(([k, v]) => [k, String(v)]);
  };
  const khoanMuc: [string, string][] = (dm.khoan_muc || []).map(
    (k: any) => [k.ma, `${k.ten_nhom ? k.ten_nhom + " – " : ""}${k.ten}`] as [string, string]);
  const dsDongChi: [string, string][] = (chi?.dong || []).map(
    (x: any) => [String(x.id), `${x.ma_khoan_muc ?? ""} – ${x.mo_ta ?? ""}`.trim()] as [string, string]);
  const dsKhach: [string, string][] = (kh?.dong || []).map(
    (k: any) => [String(k.id), `${k.stt ?? ""} ${k.ho_ten ?? ""}`.trim()] as [string, string]);

  const gui = async (p: string, d: any, ten: string) => {
    setGhi(true);
    try {
      await api(`/quyet-toan-lop3/${tourId}/${p}`, { method: "POST", json: d });
      toast(`Đã ghi ${ten}`);
      await nap();
    } catch (e) { toast(errMsg(e), true); } finally { setGhi(false); }
  };

  // Quyền nhập do MÁY CHỦ trả về (soat-gia.nhap_duoc), không do màn hình tự suy từ trạng thái
  // chuyến – xem giải thích ở chính cửa ấy.
  if (sg && sg.nhap_duoc === false) return (
    <p className="muted">Vai trò của anh/chị xem được số nhưng không nhập được tờ quyết toán.
      Việc nhập thuộc phòng Điều hành và Kế toán.</p>
  );

  return (
    <div>
      <p className="muted">
        Đang nhập theo mẫu <b>{nn ? "TOUR NƯỚC NGOÀI" : "TOUR TRONG NƯỚC"}</b>.
        {" "}Ô tiền để trống nghĩa là <b>chưa nhập</b>, không phải 0 đồng. Không ô nào cho gõ tổng –
        máy chủ cộng lại từ các dòng.
      </p>

      {/* ---------------------------------------------------------------- 1. khách */}
      <BangNhap
        tieuDe="1. Dòng khách" nn={nn} dangGhi={ghi} dong={kh?.dong || []}
        giaiThich="Ghi HẾT mọi người ngồi trên chuyến, kể cả khách miễn phí, người nội bộ và khách của đại lý – họ vẫn ăn suất ăn và vẫn ngồi ghế."
        them={(d) => gui("khach", d, "dòng khách")}
        cot={[
          { khoa: "booking_id", nhan: "Mã phiếu đặt", kieu: "so", batBuoc: true, rong: 110,
            chuThich: "Phiếu đặt của khách này. Chuyến có nhiều phiếu đặt thì mỗi khách một mã – gán sai thì doanh thu chạy sang sale khác." },
          { khoa: "stt", nhan: "STT", kieu: "so", rong: 70 },
          { khoa: "nhom_khach", nhan: "Nhóm khách", kieu: "chon", chon: chonTu(dm.nhom_khach), rong: 150 },
          { khoa: "ho_ten", nhan: "Họ và tên", batBuoc: true, rong: 200 },
          { khoa: "ngay_sinh", nhan: "Ngày sinh", kieu: "ngay", rong: 140,
            chuThich: "Thu ở khâu ĐĂNG KÝ. Không có ngày sinh thì quy tắc giá theo tuổi không kiểm được." },
          { khoa: "gia_ban", nhan: "Giá bán", kieu: "tien", rong: 130 },
          { khoa: "ly_do_khac_chuan", nhan: "Note", rong: 200 },
          { khoa: nn ? "so_ho_chieu" : "so_ho_chieu", nhan: nn ? "Số hộ chiếu" : "CCCD", rong: 140 },
          { khoa: "ma_dat_cho", nhan: "Mã đặt chỗ (PNR)", rong: 130 },
          { khoa: "loai_tuoi", nhan: "Loại tuổi", chiMay: true },
          { khoa: "gia_chuan", nhan: "Giá chuẩn", kieu: "tien", chiMay: true },
        ]}
      />
      {sg?.lech?.length > 0 && (
        <div className="gate fail" style={{ marginBottom: 14 }}>
          <b>{sg.lech.length} khách có giá bán khác giá chuẩn theo tuổi.</b>
          {" "}Không phải lỗi – bán khác chuẩn là chuyện thường – nhưng phải ghi lý do ở ô Note.
        </div>
      )}

      {/* ---------------------------------------------------------------- 2. doanh thu */}
      <BangNhap
        tieuDe="2. Doanh thu" nn={nn} dangGhi={ghi} dong={dt?.dong || []}
        giaiThich="Tour lẻ ghi theo khách; tour đoàn ghi theo khoản hợp đồng. Dòng ÂM (hoàn tiền, thanh lý) BẮT BUỘC ghi số hiệu chứng từ – không có thì không phân biệt được với gõ nhầm dấu trừ."
        them={(d) => gui("doanh-thu", d, "dòng doanh thu")}
        tong={[{ nhan: "Tổng thu", gia: dt?.tong_thu }]}
        cot={[
          { khoa: "loai", nhan: "Loại", kieu: "chon", chon: chonTu(dm.loai_doanh_thu), rong: 150 },
          { khoa: "noi_dung", nhan: "Nội dung", batBuoc: true, rong: 220 },
          { khoa: "khach_id", nhan: "Của khách", kieu: "chon", chon: dsKhach, rong: 170 },
          { khoa: "don_gia_truoc_thue", nhan: "Đơn giá trước thuế", kieu: "tien", rong: 150 },
          { khoa: "so_luong", nhan: "Số lượng", kieu: "so", rong: 90 },
          { khoa: "thue_suat", nhan: "Thuế suất", kieu: "so", rong: 100,
            chuThich: "Ghi dạng thập phân: 0,08 cho 8%. Bán lẻ thì để trống." },
          { khoa: "chung_tu", nhan: "Chứng từ (bắt buộc nếu ÂM)", rong: 200 },
          { khoa: "thanh_tien", nhan: "Thành tiền", kieu: "tien", chiMay: true },
        ]}
      />

      {/* ---------------------------------------------------------------- 3. chi */}
      <BangNhap
        tieuDe="3. Chi phí" nn={nn} dangGhi={ghi} dong={chi?.dong || []}
        giaiThich="Chọn khoản mục từ danh mục – máy tự điền nhóm, đối tượng và quy tắc phân bổ. Chọn nhà cung cấp – máy tự điền mã số thuế và tên pháp nhân. Anh/chị chỉ gõ số tiền."
        them={(d) => gui("chi", d, "dòng chi")}
        tong={[{ nhan: "Dự chi", gia: chi?.tong_du_chi }, { nhan: "Thực chi", gia: chi?.tong_thuc_chi }]}
        cot={[
          { khoa: "ma_khoan_muc", nhan: "Khoản mục", kieu: "chon", chon: khoanMuc, batBuoc: true, rong: 260,
            chuThich: "55 mã trong 9 nhóm, rút từ 8 tệp quyết toán thật. Không có ô gõ tự do: cùng một khoản gõ bốn cách thì không cộng theo khoản mục được." },
          { khoa: "mo_ta", nhan: "Chi tiết dòng", rong: 220,
            chuThich: "Cái phân biệt dòng này với dòng kia: 'Ăn trưa ngày 2 – Marina Beach'." },
          { khoa: "ngay", nhan: "Ngày", rong: 110, chuThich: "Ghi tự do: '10/07', 'Ngày 1', '10-12/07'." },
          { khoa: "supplier_id", nhan: "Nhà cung cấp", kieu: "ncc", rong: 240 },
          { khoa: "nha_cung_cap", nhan: "NCC đã ghi", chiMay: true },
          { khoa: "mst_ncc", nhan: "MST", chiMay: true },
          { khoa: "don_gia", nhan: "Đơn giá", kieu: "tien", rong: 130 },
          { khoa: "so_luong", nhan: "Số lượng", kieu: "so", rong: 90 },
          { khoa: "he_so", nhan: "Hệ số", kieu: "so", rong: 80,
            chuThich: "Số lần lặp: 2 đêm, 3 bữa. Để trống hiểu là 1." },
          { khoa: "du_chi", nhan: "DỰ CHI", kieu: "tien", rong: 130 },
          { khoa: "thuc_chi", nhan: "THỰC CHI", kieu: "tien", rong: 130 },
          { khoa: "tien_te", nhan: "Tiền tệ", kieu: "chon", chiNN: true, rong: 100 },
          { khoa: "so_tien_goc", nhan: "Số tiền gốc", kieu: "tien", chiNN: true, rong: 130 },
          { khoa: "ty_gia", nhan: "Tỷ giá", kieu: "so", chiNN: true, rong: 110 },
          { khoa: "ngay_ty_gia", nhan: "Ngày tỷ giá", kieu: "ngay", chiNN: true, rong: 150,
            chuThich: "Tỷ giá của NGÀY CHI THẬT. Một tệp thật có hai tỷ giá GBP khác nhau; riêng một khoản land, 56 đồng chênh là 1.667.155 đ." },
          { khoa: "thue_suat", nhan: "Thuế suất", kieu: "so", rong: 100 },
          { khoa: "khong_hoa_don", nhan: "Phần KHÔNG hoá đơn", kieu: "tien", rong: 160,
            chuThich: "Đã xác nhận KHÔNG CÓ hoá đơn – khác với chưa nhập. Đây là phần giá vốn không khấu trừ được thuế." },
          { khoa: "so_hoa_don", nhan: "Số hoá đơn", rong: 130 },
          { khoa: "nhom", nhan: "Nhóm", chiMay: true },
          { khoa: "quy_tac_phan_bo", nhan: "Phân bổ", chiMay: true },
        ]}
      />

      {/* ---------------------------------------------------------------- 4. chi theo khách */}
      {nn && (
        <BangNhap
          tieuDe="4. Chi theo từng khách" nn={nn} dangGhi={ghi} dong={ck?.dong || []}
          giaiThich="Vé máy bay, phí lãnh sự quán, dịch thuật, quà tặng. Trên tệp thật, cùng một chuyến mà vé khách này 22.435.959 đ còn khách kia 21.903.700 đ, và bốn khách không mua visa vì đã có sẵn – ép vào phép chia là làm hỏng cả hai đầu."
          them={(d) => gui("khach-chi-phi", d, "chi theo khách")}
          cot={[
            { khoa: "khach_id", nhan: "Khách", kieu: "chon", chon: dsKhach, batBuoc: true, rong: 180 },
            { khoa: "loai", nhan: "Loại chi phí", rong: 160 },
            { khoa: "noi_dung", nhan: "Nội dung", rong: 200 },
            { khoa: "nha_cung_cap", nhan: "Nhà cung cấp", rong: 180 },
            { khoa: "tien_te", nhan: "Tiền tệ", kieu: "chon", rong: 100 },
            { khoa: "so_tien_goc", nhan: "Số tiền gốc", kieu: "tien", rong: 130 },
            { khoa: "ty_gia", nhan: "Tỷ giá", kieu: "so", rong: 110 },
            { khoa: "ngay_ty_gia", nhan: "Ngày tỷ giá", kieu: "ngay", rong: 150 },
            { khoa: "so_tien", nhan: "Thành tiền (VND)", kieu: "tien", rong: 150 },
            { khoa: "so_hoa_don", nhan: "Số hoá đơn", rong: 130 },
          ]}
        />
      )}

      {/* ---------------------------------------------------------------- 5. phương tiện */}
      <BangNhap
        tieuDe={`${nn ? "5" : "4"}. Phương tiện`} nn={nn} dangGhi={ghi} dong={pt?.dong || []}
        giaiThich="Một chiều riêng, không phải một dòng chi: tour đoàn Phú Quốc là tour trong nước nhưng đi máy bay."
        them={(d) => gui("phuong-tien", d, "chặng phương tiện")}
        tong={[{ nhan: "Tổng", gia: pt?.tong }]}
        cot={[
          { khoa: "loai", nhan: "Loại", kieu: "chon", chon: chonTu(dm.loai_phuong_tien), batBuoc: true, rong: 150 },
          { khoa: "chang", nhan: "Chặng", rong: 180 },
          { khoa: "ngay", nhan: "Ngày", kieu: "ngay", rong: 140 },
          { khoa: "gio_di", nhan: "Giờ đi", kieu: "gio", rong: 100 },
          { khoa: "gio_den", nhan: "Giờ đến", kieu: "gio", rong: 100 },
          { khoa: "so_hieu", nhan: "Số hiệu / biển số", rong: 150 },
          { khoa: "ma_dat_cho", nhan: "Mã đặt chỗ", rong: 130 },
          { khoa: "nha_cung_cap", nhan: "Nhà cung cấp", rong: 180 },
          { khoa: "xe_nha", nhan: "Xe nhà?", kieu: "co", rong: 80 },
          { khoa: "so_cho", nhan: "Số chỗ", kieu: "so", rong: 90 },
          { khoa: "so_khach_su_dung", nhan: "Số khách dùng", kieu: "so", rong: 120 },
          { khoa: "don_gia", nhan: "Đơn giá", kieu: "tien", rong: 130 },
          { khoa: "so_luong", nhan: "Số lượng", kieu: "so", rong: 90 },
          { khoa: "thanh_tien", nhan: "Thành tiền", kieu: "tien", chiMay: true },
        ]}
      />

      {/* ---------------------------------------------------------------- 6. HDV */}
      <BangNhap
        tieuDe={`${nn ? "6" : "5"}. Hướng dẫn viên – ứng, chi, vượt`} nn={nn} dangGhi={ghi}
        dong={hdv?.dong || []}
        giaiThich="HAI phép so ngược chiều nhau: VƯỢT = thực chi − chiết tính (HDV tiêu quá dự toán, không duyệt thì HDV bù). CÒN LẠI = tiền ứng − thực chi (âm nghĩa là CÔNG TY nợ HDV). Cả hai đều xảy ra thật."
        them={(d) => gui("hdv-chi", d, "khoản HDV chi")}
        tong={[{ nhan: "Tổng chi", gia: hdv?.tong_chi }, { nhan: "Tổng ứng", gia: hdv?.tong_ung },
               { nhan: "Còn lại", gia: hdv?.con_lai }]}
        cot={[
          { khoa: "noi_dung", nhan: "Nội dung", batBuoc: true, rong: 220 },
          { khoa: "don_gia", nhan: "Đơn giá", kieu: "tien", rong: 130 },
          { khoa: "so_luong", nhan: "Số lượng", kieu: "so", rong: 90 },
          { khoa: "tien_ung", nhan: "Tiền ứng", kieu: "tien", rong: 130,
            chuThich: "Tiền công ty đưa trước cho HDV. Ứng một lần cho cả tour thì ghi vào MỘT dòng." },
          // KHÔNG cho gõ tay số chiết tính: CHỌN đúng dòng chi phí tương ứng, máy lấy số từ dòng ấy
          // rồi trừ ra phần vượt. Gõ tay là mở đường cho người chi vượt tự khai mình không vượt.
          { khoa: "dong_chiet_tinh_id", nhan: "Đối chiếu dòng chi", kieu: "chon", chon: dsDongChi,
            rong: 240,
            chuThich: "Chọn dòng chi phí mà khoản này phải nằm trong. Máy lấy số của dòng ấy làm mức chiết tính rồi tính phần vượt." },
          { khoa: "thanh_tien_chiet_tinh", nhan: "Theo chiết tính", kieu: "tien", chiMay: true },
          { khoa: "tien_te", nhan: "Tiền tệ", kieu: "chon", chiNN: true, rong: 100 },
          { khoa: "so_tien_goc", nhan: "Số gốc", kieu: "tien", chiNN: true, rong: 120 },
          { khoa: "ty_gia", nhan: "Tỷ giá", kieu: "so", chiNN: true, rong: 110 },
          { khoa: "loai_chung_tu", nhan: "Chứng từ", rong: 130 },
          { khoa: "thu_ho_khach", nhan: "Thu hộ khách?", kieu: "co", rong: 120,
            chuThich: "Tiền của KHÁCH, không phải của công ty. Không vào giá vốn, cũng không vào doanh thu." },
          { khoa: "thanh_tien", nhan: "Thực chi", kieu: "tien", chiMay: true },
          { khoa: "vuot", nhan: "VƯỢT", kieu: "tien", chiMay: true },
          { khoa: "con_lai", nhan: "CÒN LẠI", kieu: "tien", chiMay: true },
          { khoa: "trang_thai_duyet", nhan: "Duyệt", chiMay: true },
        ]}
      />
      {hdv?.so_dong_cho_duyet > 0 && (
        <div className="gate fail">
          <b>{hdv.so_dong_cho_duyet} khoản HDV chi còn chờ duyệt.</b>{" "}
          Im lặng không được tính là đồng ý – tờ quyết toán chưa đóng được khi còn dòng chờ duyệt.
        </div>
      )}

      <TienTip tourId={tourId} nn={nn} toast={toast} xong={nap} />

      {/* SỔ DẤU VẾT – CHỈ ĐỌC, KHÔNG CÓ NÚT NÀO.
          Chủ tịch chốt 10/9/2026: sửa tờ đã ký thì phải để lại dấu vết và lý do. Sổ này không có cửa
          ghi tay và không có cửa xoá, kể cả cho Chủ tịch – một sổ dấu vết mà người quyền cao nhất
          xoá được thì không phải sổ dấu vết. Chỉ hiện khi ĐÃ CÓ lần sửa: một mục rỗng nằm đó mỗi
          ngày sẽ thành thứ người ta nhìn mà không đọc. */}
      {dv?.so_lan_sua > 0 && (
        <div className="panel">
          <h3 style={{ margin: "0 0 4px" }}>Sổ dấu vết – {dv.so_lan_sua} lần sửa sau khi ký</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            Chỉ đọc. Không có cửa ghi tay và không có cửa xoá, kể cả cho Chủ tịch. Sửa sai thì sửa
            tiếp và ghi tiếp.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead><tr>
                <th>Lúc</th><th>Người sửa</th><th>Vai trò</th><th>Bảng</th><th>Trường</th>
                <th>Từ</th><th>Thành</th><th>Lý do</th>
              </tr></thead>
              <tbody>
                {dv.dong.map((x: any) => (
                  <tr key={x.id}>
                    <td>{fmtDT(x.sua_luc)}</td><td>{x.nguoi_sua}</td><td>{x.vai_tro}</td>
                    <td>{x.bang}</td><td>{x.truong}</td>
                    <td>{x.gia_tri_cu ?? "—"}</td><td>{x.gia_tri_moi ?? "—"}</td>
                    <td>{x.ly_do}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
