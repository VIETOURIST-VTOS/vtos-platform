"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  docDonVi, datDangXem, duyetCay,
  KHOA_YEU_THICH, KHOA_GAN_NHAT,
  type DonVi, type KetQuaPhamVi,
} from "@/lib/phamvi";

/** TC-1 · Nút chọn đơn vị trên thanh ngang.
 *
 *  Sáu việc lệnh giao: tìm kiếm · nhóm thu/mở · đơn vị yêu thích · lựa chọn gần nhất · luôn hiện
 *  đơn vị đang chọn · cảnh báo khi còn dữ liệu chưa lưu.
 *
 *  BỐN RÀNG BUỘC, mỗi cái là một chỗ dễ làm sai:
 *
 *  1. QUYỀN KIỂM TẠI MÁY CHỦ. Danh sách vẽ ra đây là danh sách máy chủ đã lọc. Thành phần này
 *     KHÔNG có một dòng nào lọc theo vai trò – tìm kiếm chỉ lọc theo chữ người dùng gõ.
 *
 *  2. ĐỔI ĐƠN VỊ KHÔNG ĐỔI PHÁP NHÂN CỦA CHỨNG TỪ. Đổi đơn vị là đổi "tôi đang nhìn phần nào";
 *     pháp nhân của một tờ chứng từ là chuyện khác và không ai sửa nó từ đây.
 *
 *  3. "TOÀN CÔNG TY" KHÔNG CỘNG TRÙNG. Nó gửi lên `null` và để MÁY CHỦ gom theo cây parent_id.
 *     Mỗi hồ sơ mang đúng một company_id nên không có đường cộng trùng – miễn là trình duyệt
 *     không tự cộng, và ở đây nó không cộng gì cả.
 *
 *  4. CÒN DỮ LIỆU CHƯA LƯU THÌ HỎI TRƯỚC. Đổi phạm vi giữa chừng một biểu đang gõ dở là mất việc
 *     người ta vừa làm, mà mất im lặng.
 *
 *  Hôm nay hai đường dẫn của hợp đồng chưa có trên máy chủ. Khi ấy nút này hiện "Chưa có nguồn"
 *  kèm tên bộ phận chịu trách nhiệm – theo đúng ranh giới 09/9: chưa có cửa thì nói ra, không hiện
 *  0 và không bịa danh sách. Muốn xem thử giao diện thì thêm ?giaLapDonVi=1 vào đường dẫn.
 */
export default function ChonDonVi({ chuaLuu, toast }: { chuaLuu?: () => boolean; toast?: (m: string, e?: boolean) => void }) {
  const [mo, setMo] = useState(false);
  const [kq, setKq] = useState<KetQuaPhamVi | null>(null);
  const [tim, setTim] = useState("");
  const [thu, setThu] = useState<Set<string>>(new Set());      // nhánh đang THU lại
  const [yeuThich, setYeuThich] = useState<string[]>([]);
  const [ganNhat, setGanNhat] = useState<string[]>([]);
  const [dangDat, setDangDat] = useState(false);
  const hop = useRef<HTMLSpanElement>(null);

  useEffect(() => { docDonVi().then(setKq); }, []);

  useEffect(() => {
    try {
      setYeuThich(JSON.parse(localStorage.getItem(KHOA_YEU_THICH) || "[]"));
      setGanNhat(JSON.parse(localStorage.getItem(KHOA_GAN_NHAT) || "[]"));
    } catch { /* máy chặn localStorage thì bỏ hai tiện ích này, không phải lỗi */ }
  }, []);

  // Bấm ra ngoài thì đóng. Không dùng phím Esc thay thế: bàn phím còn dùng cho ô tìm kiếm.
  useEffect(() => {
    if (!mo) return;
    const f = (e: MouseEvent) => { if (hop.current && !hop.current.contains(e.target as Node)) setMo(false); };
    document.addEventListener("mousedown", f);
    return () => document.removeEventListener("mousedown", f);
  }, [mo]);

  const duLieu = kq?.tinh_trang === "co" ? kq.du_lieu : null;
  const phang = useMemo(() => duLieu ? duyetCay(duLieu.duoc_phep) : [], [duLieu]);
  const theoMa = useMemo(() => {
    const m = new Map<string, DonVi>();
    for (const { dv } of phang) m.set(String(dv.id), dv);
    return m;
  }, [phang]);

  const nhan = duLieu?.dang_xem?.ten ?? "Toàn công ty";

  function luu(khoa: string, v: string[]) {
    try { localStorage.setItem(khoa, JSON.stringify(v)); } catch { /* bỏ qua */ }
  }

  function doiYeuThich(id: string) {
    const moi = yeuThich.includes(id) ? yeuThich.filter((x) => x !== id) : [...yeuThich, id].slice(-8);
    setYeuThich(moi); luu(KHOA_YEU_THICH, moi);
  }

  async function chon(id: number | "chua_gan" | null, ten: string) {
    // Ràng buộc 4: hỏi TRƯỚC khi đổi, không hỏi sau.
    if (chuaLuu?.()) {
      const ok = window.confirm(
        `Màn hình đang mở còn dữ liệu chưa lưu.\n\nĐổi sang “${ten}” sẽ tải lại dữ liệu và phần đang gõ dở sẽ mất.\n\nVẫn đổi?`);
      if (!ok) return;
    }
    setDangDat(true);
    const r = await datDangXem(id);
    setDangDat(false);
    if (!r.ok) { toast?.(r.loi || "Không đổi được đơn vị đang xem", true); return; }
    if (id !== null) {
      const khoa = String(id);
      const moi = [khoa, ...ganNhat.filter((x) => x !== khoa)].slice(0, 5);
      setGanNhat(moi); luu(KHOA_GAN_NHAT, moi);
    }
    setMo(false);
    // Tải lại để mọi màn hình đang mở đọc theo phạm vi mới. Làm mới cả trang thay vì báo từng
    // thành phần: một nửa màn hình theo phạm vi cũ và một nửa theo phạm vi mới là thứ không ai
    // nhìn ra được là sai.
    window.location.reload();
  }

  const hienThi = useMemo(() => {
    const t = tim.trim().toLowerCase();
    if (!t) return phang;
    // Tìm kiếm lọc theo CHỮ NGƯỜI GÕ, không theo quyền. Khi đang tìm thì bỏ thụt đầu dòng vì cây
    // đã bị cắt rời, thụt theo độ sâu cũ sẽ đọc như một cây khác.
    return phang.filter(({ dv }) =>
      dv.ten.toLowerCase().includes(t) || (dv.ma || "").toLowerCase().includes(t)
    ).map((x) => ({ ...x, sau: 0 }));
  }, [phang, tim]);

  const bi_an = useMemo(() => {
    // Nhánh nằm dưới một nút đang THU thì không vẽ. Chỉ áp dụng khi KHÔNG tìm kiếm.
    if (tim.trim() || !duLieu) return new Set<string>();
    const an = new Set<string>();
    const di = (ds: DonVi[], duoi: boolean) => {
      for (const dv of ds) {
        const k = String(dv.id);
        if (duoi) an.add(k);
        if (dv.con?.length) di(dv.con, duoi || thu.has(k));
      }
    };
    di(duLieu.duoc_phep, false);
    return an;
  }, [duLieu, thu, tim]);

  const nut = (
    <button type="button" onClick={() => setMo((m) => !m)} aria-haspopup="listbox" aria-expanded={mo}
      title={`Đơn vị đang xem: ${nhan}`} disabled={dangDat}>
      {nhan} ▾
    </button>
  );

  if (kq?.tinh_trang === "chua_co_nguon") {
    return (
      <button type="button" className="soon" disabled
        title={`Chưa có nguồn – máy chủ chưa có đường dẫn phạm vi đơn vị. Bộ phận chịu: ${kq.bo_phan}.`}>
        Chưa có nguồn · đơn vị
      </button>
    );
  }
  if (kq?.tinh_trang === "loi") {
    return <button type="button" className="soon" disabled title={kq.loi}>Không đọc được đơn vị</button>;
  }
  if (!kq) return <button type="button" className="soon" disabled>Đang tải đơn vị…</button>;

  return (
    <span ref={hop} style={{ position: "relative" }}>
      {nut}
      {mo && (
        <span role="listbox" aria-label="Chọn đơn vị đang xem"
          style={{ position: "absolute", right: 0, top: "100%", zIndex: 50, width: 300, maxHeight: 420,
                   overflowY: "auto", display: "flex", flexDirection: "column", gap: 2, background: "#fff",
                   color: "var(--ink, #222)", border: "1px solid #ddd", borderRadius: 6, padding: 8,
                   boxShadow: "0 6px 18px rgba(0,0,0,.18)" }}>
          {kq.gia_lap && (
            <b style={{ background: "#fde9d0", color: "#8a4b00", borderRadius: 4, padding: "4px 6px", fontSize: 11.5 }}>
              DỮ LIỆU GIẢ LẬP — chỉ để xem giao diện. Bỏ ?giaLapDonVi=1 để về bản thật.
            </b>
          )}

          <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm đơn vị…"
            aria-label="Tìm đơn vị" style={{ padding: "5px 7px", fontSize: 12.5, fontFamily: "inherit" }} />

          {/* Luôn hiện đơn vị đang chọn, ngay cả khi đang tìm chữ khác – lệnh TC-1 đòi vậy, và nó
              đúng: người dùng phải biết mình đang đứng ở đâu trước khi quyết định đi đâu. */}
          <span style={{ fontSize: 11.5, color: "#666", padding: "2px 4px" }}>
            Đang xem: <b>{nhan}</b>
          </span>

          <button type="button" onClick={() => chon(null, "Toàn công ty")}
            title="Toàn bộ phạm vi tài khoản được xem, gồm đơn vị trực thuộc – máy chủ gom, không cộng trùng"
            style={{ textAlign: "left", padding: "5px 6px", fontFamily: "inherit", fontSize: 12.5 }}>
            Toàn công ty
          </button>

          {yeuThich.length > 0 && !tim.trim() && (
            <>
              <span style={{ fontSize: 11, color: "#888", padding: "4px 4px 0" }}>YÊU THÍCH</span>
              {yeuThich.filter((k) => theoMa.has(k)).map((k) => {
                const dv = theoMa.get(k)!;
                return <button key={"yt" + k} type="button" onClick={() => chon(dv.id, dv.ten)}
                  style={{ textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5 }}>★ {dv.ten}</button>;
              })}
            </>
          )}

          {ganNhat.length > 0 && !tim.trim() && (
            <>
              <span style={{ fontSize: 11, color: "#888", padding: "4px 4px 0" }}>GẦN NHẤT</span>
              {ganNhat.filter((k) => theoMa.has(k)).map((k) => {
                const dv = theoMa.get(k)!;
                return <button key={"gn" + k} type="button" onClick={() => chon(dv.id, dv.ten)}
                  style={{ textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5 }}>{dv.ten}</button>;
              })}
            </>
          )}

          <span style={{ fontSize: 11, color: "#888", padding: "4px 4px 0" }}>TẤT CẢ ĐƠN VỊ ĐƯỢC XEM</span>
          {hienThi.length === 0 && <span style={{ fontSize: 12, color: "#888", padding: 4 }}>Không có đơn vị nào khớp.</span>}
          {hienThi.map(({ dv, sau }) => {
            const k = String(dv.id);
            if (bi_an.has(k)) return null;
            const coCon = !!dv.con?.length && !tim.trim();
            return (
              <span key={k} style={{ display: "flex", alignItems: "center", gap: 2, paddingLeft: sau * 12 }}>
                {coCon ? (
                  <button type="button" onClick={() => setThu((s) => {
                    const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n;
                  })} title={thu.has(k) ? "Mở nhánh" : "Thu nhánh"} aria-label={thu.has(k) ? "Mở nhánh" : "Thu nhánh"}
                    style={{ border: 0, background: "none", cursor: "pointer", fontSize: 11, padding: "0 2px" }}>
                    {thu.has(k) ? "▸" : "▾"}
                  </button>
                ) : <span style={{ width: 15 }} />}
                <button type="button" onClick={() => chon(dv.id, dv.ten)}
                  style={{ flex: 1, textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5,
                           fontWeight: String(duLieu?.dang_xem?.id) === k ? 700 : 400 }}>
                  {dv.ten}{dv.ma ? <i style={{ color: "#999", fontStyle: "normal" }}> · {dv.ma}</i> : null}
                </button>
                <button type="button" onClick={() => doiYeuThich(k)}
                  title={yeuThich.includes(k) ? "Bỏ khỏi yêu thích" : "Thêm vào yêu thích"}
                  aria-label={yeuThich.includes(k) ? "Bỏ khỏi yêu thích" : "Thêm vào yêu thích"}
                  style={{ border: 0, background: "none", cursor: "pointer", fontSize: 12, padding: "0 2px" }}>
                  {yeuThich.includes(k) ? "★" : "☆"}
                </button>
              </span>
            );
          })}
        </span>
      )}
    </span>
  );
}
