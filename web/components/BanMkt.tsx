"use client";
/** MKT-1 · THÂN CHUNG CỦA HAI BÀN MARKETING — 09/11/2026.
 *
 *  Hai bàn, một thân. Bàn Phó TGĐ và bàn nhân viên khác nhau ở DANH SÁCH Ô, mà danh sách ô do máy
 *  chủ dựng — nên phần vẽ của hai bàn giống hệt nhau. Chép ra hai bản thì sớm muộn chúng lệch
 *  nhau, và lúc ấy không ai biết bản nào đúng; đó đúng là lý do `TrangPhanHe` ra đời hôm qua.
 *
 *  BA ĐIỀU THÂN NÀY PHẢI GIỮ, vì chúng là ba lần suýt nói dối đã ghi ở `services/ban_mkt.py`:
 *
 *   · `so_luong === null` thì vẽ CHỮ, không vẽ số 0. Một ô đọc hỏng mà hiện "0 việc" là nói với
 *     người ngồi bàn rằng hôm nay không có gì phải làm.
 *   · `tong_dang_cho === null` thì nói "chưa đủ dữ liệu", không cộng các ô còn lại.
 *   · Ô mẫu số nằm cuối và mang màu khác, để không ai đọc nó như một việc phải làm.
 *
 *  KHÔNG CÓ NÚT DUYỆT. Mỗi ô là một đường dẫn sang đúng tab của màn `/marketing`, nơi quyền và
 *  quy trình đã có chủ. Bàn này không bấm được gì ngoài việc đi sang chỗ khác — và đó là chủ ý.
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useShell } from "@/components/Shell";
import { api } from "@/lib/api";
import { errMsg } from "@/components/ui";

const MAU: Record<string, { cham: string; chu: string }> = {
  do: { cham: "#be2f2f", chu: "#be2f2f" },
  vang: { cham: "#c9a227", chu: "#6b5415" },
};

type O = {
  khoa: string; ten: string; so_luong: number | null; don_vi: string;
  muc: string; ghi_chu: string; den: string; nguon: string;
  trang_thai: string; ly_do: string;
};
type Ban = {
  ten: string; vai: string; o: O[]; tong_dang_cho: number | null;
  nguoi?: string; luu_y: string;
};

/** Một ô hàng đợi. Bốn phần, và phần thứ tư không được bỏ:
 *  con số · ô ấy là việc gì · con số ấy đọc từ đâu · CỬA để đi tới chỗ làm nó. */
function OViec({ o, mauSo }: { o: O; mauSo: boolean }) {
  const hong = o.trang_thai !== "san_sang";
  const mau = MAU[o.muc];
  return (
    <div className="panel" style={{
      display: "flex", flexDirection: "column", gap: 6, minWidth: 0,
      background: mauSo ? "#f6f8fb" : undefined,
      borderLeft: mau ? `3px solid ${mau.cham}` : undefined,
    }}>
      {/* Điều thứ nhất: chưa đọc được thì vẽ CHỮ, không vẽ số 0. */}
      {hong
        ? <strong style={{ color: "#a66a00" }}>chưa đọc được</strong>
        : <div style={{ fontSize: "1.6rem", fontWeight: 700, lineHeight: 1,
                        color: mau?.chu }}>
            {o.so_luong} <span className="muted" style={{ fontSize: ".8rem", fontWeight: 400 }}>{o.don_vi}</span>
          </div>}
      <strong>{o.ten}</strong>
      {o.ghi_chu && <span className="muted" style={{ fontSize: ".85rem" }}>{o.ghi_chu}</span>}
      {hong
        ? <span className="muted" style={{ fontSize: ".8rem" }}>{o.ly_do}</span>
        : <span className="muted" style={{ fontSize: ".8rem" }}>Đọc từ: {o.nguon}</span>}
      {o.den && <Link href={o.den}>Mở chỗ làm việc này →</Link>}
    </div>
  );
}

export default function BanMkt({ duong }: { duong: string }) {
  const { toast } = useShell();
  const [d, setD] = useState<Ban | null>(null);
  const [dang, setDang] = useState(true);

  const doc = useCallback(async () => {
    setDang(true);
    try { setD(await api(duong)); }
    catch (e) { toast(errMsg(e), true); }
    finally { setDang(false); }
  }, [duong, toast]);

  useEffect(() => { doc(); }, [doc]);

  if (dang && !d) return <p className="muted">Đang đọc số…</p>;
  if (!d) return <p className="muted">Chưa đọc được bàn làm việc. Thử tải lại trang.</p>;

  const viec = d.o.filter((x) => x.khoa !== "chien_dich_dang_chay");
  const mauSo = d.o.filter((x) => x.khoa === "chien_dich_dang_chay");

  return (<>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 14, alignItems: "flex-end",
                  justifyContent: "space-between", marginBottom: 18 }}>
      <div>
        <h1 style={{ margin: "0 0 4px" }}>{d.ten}</h1>
        <p className="muted" style={{ margin: 0 }}>
          Phòng Marketing{d.nguoi ? ` · ${d.nguoi}` : ""}
        </p>
      </div>
      <div style={{ textAlign: "right" }}>
        {/* Điều thứ hai: thiếu một ô thì KHÔNG có tổng. */}
        {d.tong_dang_cho === null
          ? <strong style={{ color: "#a66a00" }}>chưa đủ dữ liệu để cộng tổng</strong>
          : <><strong style={{ fontSize: "1.3rem" }}>{d.tong_dang_cho}</strong>{" "}
              <span className="muted">việc đang chờ</span></>}
      </div>
    </div>

    <div style={{ display: "grid", gap: 12,
                  gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
      {viec.map((o) => <OViec key={o.khoa} o={o} mauSo={false} />)}
      {/* Điều thứ ba: mẫu số đứng cuối và mang màu khác. */}
      {mauSo.map((o) => <OViec key={o.khoa} o={o} mauSo />)}
    </div>

    <p className="muted" style={{ marginTop: 16 }}>{d.luu_y}</p>
    <p style={{ marginTop: 4 }}>
      <button type="button" onClick={doc}>Đọc lại số</button>
    </p>
  </>);
}
