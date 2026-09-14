"use client";
/** HAI Ô THUẾ SUẤT CỦA CHUYẾN — Đ-2c, Chủ tịch chốt 14/9/2026.
 *
 *   "Thuế GTGT tour châu Âu là tour nước ngoài nên tính 0%, nhưng em cứ viết cấu trúc và thuật
 *    toán, còn tỷ lệ % để cho Điều hành nhập vào."
 *
 * Nên 0% không phải một con số trong mã, và 8% cũng vậy. Cả hai là ô trên chuyến; rỗng thì lùi về
 * tham số công ty đã ký.
 *
 * BA ĐIỀU Ô NÀY TỰ BUỘC MÌNH
 *
 * 1. LUÔN BÀY MỨC ĐANG ÁP DỤNG, kể cả khi ô rỗng. Ô rỗng nghĩa là "dùng tham số công ty" — không
 *    nói con số ấy là bao nhiêu thì người nhập phải đoán, và họ sẽ gõ đè một con số để cho chắc.
 * 2. ĐƠN VỊ NẰM TRONG NHÃN. Ô là PHẦN TRĂM: gõ 8 nghĩa là 8%. Gõ số nhỏ hơn 1 thì máy nói ra —
 *    nhưng KHÔNG tự sửa số của người ta. Đây đúng là cái bẫy đã phải gỡ ở ô % chia tip (12/9).
 * 3. Ô THỨ HAI CHỈ HIỆN VỚI TOUR NƯỚC NGOÀI. Tour trong nước không có dòng "ngoài Việt Nam", bày ra
 *    là mời người ta điền một con số không đi đâu cả.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

type Xem = {
  thue_suat_ra_pt: number | null;
  thue_suat_ngoai_vn_pt: number | null;
  dang_ap_dung: {
    thue_suat_ra: number; thue_suat_ngoai_vn: number;
    nguon_ra: string; nguon_ngoai_vn: string;
  };
  hinh_thuc: string | null;
  nhap_duoc: boolean;
};

const pt = (x: number) => `${+(x * 100).toFixed(4)}%`;
const NGUON: Record<string, string> = {
  go_tren_chuyen: "ô gõ trên chuyến này",
  tham_so_cong_ty: "tham số công ty",
};

export default function ThueSuatChuyen({ tourId, onXong }: { tourId: number; onXong?: () => void }) {
  const [x, setX] = useState<Xem | null>(null);
  const [ra, setRa] = useState("");
  const [ng, setNg] = useState("");
  const [ghi, setGhi] = useState(false);
  const [loi, setLoi] = useState("");
  const [tin, setTin] = useState("");

  useEffect(() => { tai(); }, [tourId]); // eslint-disable-line

  async function tai() {
    try {
      const r = await api<Xem>(`/quyet-toan-lop3/${tourId}/thue-suat`);
      setX(r);
      setRa(r.thue_suat_ra_pt == null ? "" : String(r.thue_suat_ra_pt));
      setNg(r.thue_suat_ngoai_vn_pt == null ? "" : String(r.thue_suat_ngoai_vn_pt));
    } catch (e) { setLoi(errMsg(e)); }
  }

  async function luu() {
    setGhi(true); setLoi(""); setTin("");
    try {
      const r = await api<any>(`/quyet-toan-lop3/${tourId}/thue-suat`, {
        method: "PUT",
        json: {
          thue_suat_ra_pt: ra.trim() === "" ? null : Number(ra),
          thue_suat_ngoai_vn_pt: ng.trim() === "" ? null : Number(ng),
        },
      });
      setTin((r.canh_bao || []).join(" ") || "Đã lưu thuế suất của chuyến.");
      await tai(); onXong?.();
    } catch (e) { setLoi(errMsg(e)); }
    finally { setGhi(false); }
  }

  if (!x) return null;
  const nn = x.hinh_thuc === "nuoc_ngoai";

  return (
    <div className="card" style={{ marginBottom: 10 }}>
      <b>Thuế suất GTGT của chuyến này</b>
      <p className="muted" style={{ marginTop: 4 }}>
        Ô là <b>phần trăm</b>: gõ <code>8</code> nghĩa là 8%. <b>Để trống</b> thì chuyến dùng tham
        số công ty đang hiệu lực — và tham số có hiệu lực theo ngày, nên chuyến đã đi giữ nguyên
        thuế suất của ngày khởi hành.
      </p>

      <div className="row" style={{ gap: 14, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label>
          <div className="muted">Thuế suất đầu ra (%)</div>
          <input value={ra} onChange={(e) => setRa(e.target.value)} disabled={!x.nhap_duoc || ghi}
                 inputMode="decimal" style={{ width: 110 }} placeholder="để trống = theo tham số" />
          <div className="muted" style={{ fontSize: 12 }}>
            đang áp dụng <b>{pt(x.dang_ap_dung.thue_suat_ra)}</b>{" "}
            ({NGUON[x.dang_ap_dung.nguon_ra] || x.dang_ap_dung.nguon_ra})
          </div>
        </label>

        {/* Chỉ tour nước ngoài mới có dòng "ngoài Việt Nam" trên hoá đơn. */}
        {nn && (
          <label>
            <div className="muted">Dòng ngoài Việt Nam (%)</div>
            <input value={ng} onChange={(e) => setNg(e.target.value)} disabled={!x.nhap_duoc || ghi}
                   inputMode="decimal" style={{ width: 110 }} placeholder="để trống = theo tham số" />
            <div className="muted" style={{ fontSize: 12 }}>
              đang áp dụng <b>{pt(x.dang_ap_dung.thue_suat_ngoai_vn)}</b>{" "}
              ({NGUON[x.dang_ap_dung.nguon_ngoai_vn] || x.dang_ap_dung.nguon_ngoai_vn})
            </div>
          </label>
        )}

        {x.nhap_duoc && (
          <button disabled={ghi} onClick={luu}>{ghi ? "Đang lưu…" : "Lưu thuế suất"}</button>
        )}
      </div>

      {nn && (
        <p className="muted" style={{ marginTop: 8 }}>
          Tour nước ngoài xuất hoá đơn <b>hai dòng</b>: phần dịch vụ tiêu dùng ngoài Việt Nam theo
          thuế suất ô thứ hai (chính sách hiện hành là 0%), phần chênh lệch còn lại theo thuế suất
          đầu ra. Ranh giới giữa hai dòng là <b>giá vốn</b>, không phải một tỷ lệ.
        </p>
      )}

      {loi && <p className="err">{loi}</p>}
      {tin && <p className="ok">{tin}</p>}
    </div>
  );
}
