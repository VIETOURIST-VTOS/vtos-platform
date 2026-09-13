"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  docDonVi, datDangXem, duyetCay, nhanNgan,
  TOAN_PHAM_VI, DON_VI, CHUA_XAC_DINH,
  KHOA_YEU_THICH, KHOA_GAN_NHAT,
  type DonVi, type Kieu, type KetQuaPhamVi,
} from "@/lib/phamvi";
import { tenNgan } from "@/lib/ten_don_vi";

/** TC-1 · Nút chọn đơn vị trên thanh ngang.
 *
 *  Sáu việc lệnh giao: tìm kiếm · nhóm thu/mở · đơn vị yêu thích · lựa chọn gần nhất · luôn hiện
 *  đơn vị đang chọn · cảnh báo khi còn dữ liệu chưa lưu.
 *
 *  BA MỤC CHỌN, không phải hai. Ngoài "Toàn công ty" và từng đơn vị còn có "Chưa xác định pháp
 *  nhân" – hồ sơ chưa gán công ty. Trước đây chúng lẫn vào mọi danh sách nên không ai đếm được;
 *  đứng riêng thì đếm được và sửa được. Đây là kiểu `chua_xac_dinh` của máy chủ.
 *
 *  BỐN RÀNG BUỘC, mỗi cái là một chỗ dễ làm sai:
 *
 *  1. QUYỀN KIỂM TẠI MÁY CHỦ. Danh sách vẽ ra đây là danh sách máy chủ đã lọc. Thành phần này
 *     KHÔNG có một dòng nào lọc theo vai trò – tìm kiếm chỉ lọc theo chữ người dùng gõ.
 *
 *  2. ĐỔI ĐƠN VỊ KHÔNG ĐỔI PHÁP NHÂN CỦA CHỨNG TỪ. Đổi đơn vị là đổi "tôi đang nhìn phần nào";
 *     pháp nhân của một tờ chứng từ là chuyện khác và không ai sửa nó từ đây.
 *
 *  3. "TOÀN CÔNG TY" KHÔNG CỘNG TRÙNG. Nó gửi kiểu `toan_pham_vi` và để MÁY CHỦ gom theo cây
 *     parent_id. Mỗi hồ sơ mang đúng một pháp nhân nên không có đường cộng trùng – miễn là trình
 *     duyệt không tự cộng, và ở đây nó không cộng gì cả.
 *
 *  4. CÒN DỮ LIỆU CHƯA LƯU THÌ HỎI TRƯỚC. Đổi phạm vi giữa chừng một biểu đang gõ dở là mất việc
 *     người ta vừa làm, mà mất im lặng.
 *
 *  Hôm nay hai đường dẫn của hợp đồng chưa có trên máy chủ. Khi ấy thành phần này KHÔNG VẼ GÌ CẢ
 *  (anh Tuấn chốt 12/9) – không nút chết, không chữ thay thế. Chưa đổi được đơn vị thì thanh ngang
 *  để trống chỗ ấy; đường dẫn có thật thì ô chọn tự hiện. Xem thử giao diện: ?giaLapDonVi=1.
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
    for (const { dv } of phang) m.set(String(dv.company_id), dv);
    return m;
  }, [phang]);

  const chon_ht = duLieu?.dang_xem ?? null;
  const dangK = String(chon_ht?.company_id ?? "");
  const nhan = tenNgan(nhanNgan(chon_ht, theoMa.get(dangK)?.ten));

  function luu(khoa: string, v: string[]) {
    try { localStorage.setItem(khoa, JSON.stringify(v)); } catch { /* bỏ qua */ }
  }

  function doiYeuThich(id: string) {
    const moi = yeuThich.includes(id) ? yeuThich.filter((x) => x !== id) : [...yeuThich, id].slice(-8);
    setYeuThich(moi); luu(KHOA_YEU_THICH, moi);
  }

  async function chon(kieu: Kieu, ma: number | null, ten: string) {
    // Ràng buộc 4: hỏi TRƯỚC khi đổi, không hỏi sau.
    if (chuaLuu?.()) {
      const ok = window.confirm(
        `Màn hình đang mở còn dữ liệu chưa lưu.\n\nĐổi sang “${ten}” sẽ tải lại dữ liệu và phần đang gõ dở sẽ mất.\n\nVẫn đổi?`);
      if (!ok) return;
    }
    setDangDat(true);
    const r = await datDangXem(kieu, ma);
    setDangDat(false);
    if (!r.ok) { toast?.(r.loi || "Không đổi được đơn vị đang xem", true); return; }
    if (kieu === DON_VI && ma !== null) {
      const khoa = String(ma);
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
        const k = String(dv.company_id);
        if (duoi) an.add(k);
        if (dv.con?.length) di(dv.con, duoi || thu.has(k));
      }
    };
    di(duLieu.duoc_phep, false);
    return an;
  }, [duLieu, thu, tim]);

  if (kq?.tinh_trang === "chua_co_nguon") {
    // KHÔNG VẼ GÌ CẢ (anh Tuấn chốt 12/9: "xoá bỏ chữ Vietourist Holdings").
    //
    // Trước đây chỗ này lần lượt là nút "Chưa có nguồn · đơn vị", rồi ô hai dòng ghi tên pháp nhân.
    // Cả hai đều chiếm một khoảng thanh ngang để nói một điều người dùng KHÔNG cần: họ đang ở
    // Holdings – thứ mà logo bên trái đã nói rồi.
    //
    // Chưa có GET /pham-vi/don-vi thì chưa ĐỔI được đơn vị, mà một ô không bấm được thì không phải
    // là công cụ, chỉ là chữ. Khi làn Phân quyền dựng xong đường dẫn ấy, nhánh này không chạy nữa
    // và ô chọn thật ở dưới tự hiện ra – không phải sửa gì thêm ở đây.
    return null;
  }
  if (kq?.tinh_trang === "loi") {
    return <button type="button" className="soon" disabled title={kq.loi}>Không đọc được đơn vị</button>;
  }
  if (!kq) return <button type="button" className="soon" disabled>Đang tải đơn vị…</button>;

  // Chỉ một đơn vị trong phạm vi thì nút chọn không đổi được gì – hiện tên, không hiện hộp. Đây là
  // `co_the_thu_hep` của máy chủ: một ô bấm mở ra rồi đóng lại mà không làm gì là một lời hứa hụt.
  if (duLieu && !duLieu.co_the_thu_hep) {
    return <button type="button" className="soon" disabled title={chon_ht?.cau_hien_thi || nhan}>{nhan}</button>;
  }

  const muc = (nhan_: string, kieu: Kieu, ma: number | null, chuThich: string) => (
    <button type="button" onClick={() => chon(kieu, ma, nhan_)} title={chuThich}
      style={{ textAlign: "left", padding: "5px 6px", fontFamily: "inherit", fontSize: 12.5,
               fontWeight: chon_ht?.kieu === kieu && (chon_ht?.company_id ?? null) === ma ? 700 : 400 }}>
      {nhan_}
    </button>
  );

  return (
    <span ref={hop} style={{ position: "relative" }}>
      <button type="button" onClick={() => setMo((m) => !m)} aria-haspopup="listbox" aria-expanded={mo}
        title={chon_ht?.cau_hien_thi || `Đơn vị đang xem: ${nhan}`} disabled={dangDat}>
        {nhan} ▾
      </button>
      {mo && (
        <span role="listbox" aria-label="Chọn đơn vị đang xem"
          style={{ position: "absolute", right: 0, top: "100%", zIndex: 50, width: 300, maxHeight: 420,
                   overflowY: "auto", display: "flex", flexDirection: "column", gap: 2,
                   background: "var(--vtos-card)", color: "var(--vtos-text)",
                   border: "1px solid var(--vtos-line)", borderRadius: 6, padding: 8,
                   boxShadow: "0 6px 18px rgba(0,0,0,.18)" }}>
          {kq.gia_lap && (
            <b style={{ background: "var(--vtos-warning-bg)", color: "var(--vtos-warning)", borderRadius: 4, padding: "4px 6px", fontSize: 11.5 }}>
              DỮ LIỆU GIẢ LẬP — chỉ để xem giao diện. Bỏ ?giaLapDonVi=1 để về bản thật.
            </b>
          )}

          {/* Máy chủ vừa BỎ lựa chọn cũ vì nó ra ngoài phạm vi. Nói thẳng, vì im lặng đưa người ta
              về "Toàn công ty" thì họ tưởng mình vẫn đang xem đơn vị hôm qua. */}
          {chon_ht?.ve_mac_dinh === "lua_chon_cu_ngoai_pham_vi" && (
            <b style={{ background: "var(--vtos-danger-bg)", color: "var(--vtos-danger)", borderRadius: 4, padding: "4px 6px", fontSize: 11.5 }}>
              Lựa chọn trước đã ra ngoài phạm vi tài khoản của bạn nên đã trở về mặc định.
            </b>
          )}

          <input value={tim} onChange={(e) => setTim(e.target.value)} placeholder="Tìm đơn vị…"
            aria-label="Tìm đơn vị" style={{ padding: "5px 7px", fontSize: 12.5, fontFamily: "inherit" }} />

          {/* Luôn hiện đơn vị đang chọn, ngay cả khi đang tìm chữ khác – lệnh TC-1 đòi vậy, và nó
              đúng: người dùng phải biết mình đang đứng ở đâu trước khi quyết định đi đâu. */}
          <span style={{ fontSize: 11.5, color: "var(--vtos-text-mute)", padding: "2px 4px" }}>
            {chon_ht?.cau_hien_thi ? chon_ht.cau_hien_thi : <>Đang xem: <b>{nhan}</b></>}
          </span>

          {muc("Toàn công ty", TOAN_PHAM_VI, null,
               "Toàn bộ phạm vi tài khoản được xem, gồm đơn vị trực thuộc – máy chủ gom, không cộng trùng")}
          {muc("Chưa xác định pháp nhân", CHUA_XAC_DINH, null,
               "Hồ sơ chưa gán công ty. Đứng riêng để đếm được và sửa được, thay vì lẫn vào mọi danh sách.")}

          {yeuThich.length > 0 && !tim.trim() && (
            <>
              <span style={{ fontSize: 11, color: "var(--vtos-text-mute)", padding: "4px 4px 0" }}>YÊU THÍCH</span>
              {yeuThich.filter((k) => theoMa.has(k)).map((k) => {
                const dv = theoMa.get(k)!;
                return <button key={"yt" + k} type="button" onClick={() => chon(DON_VI, dv.company_id, dv.ten)}
                  style={{ textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5 }}>★ {dv.ten}</button>;
              })}
            </>
          )}

          {ganNhat.length > 0 && !tim.trim() && (
            <>
              <span style={{ fontSize: 11, color: "var(--vtos-text-mute)", padding: "4px 4px 0" }}>GẦN NHẤT</span>
              {ganNhat.filter((k) => theoMa.has(k)).map((k) => {
                const dv = theoMa.get(k)!;
                return <button key={"gn" + k} type="button" onClick={() => chon(DON_VI, dv.company_id, dv.ten)}
                  style={{ textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5 }}>{dv.ten}</button>;
              })}
            </>
          )}

          <span style={{ fontSize: 11, color: "var(--vtos-text-mute)", padding: "4px 4px 0" }}>TẤT CẢ ĐƠN VỊ ĐƯỢC XEM</span>
          {hienThi.length === 0 && <span style={{ fontSize: 12, color: "var(--vtos-text-mute)", padding: 4 }}>Không có đơn vị nào khớp.</span>}
          {hienThi.map(({ dv, sau }) => {
            const k = String(dv.company_id);
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
                <button type="button" onClick={() => chon(DON_VI, dv.company_id, dv.ten)}
                  style={{ flex: 1, textAlign: "left", padding: "4px 6px", fontFamily: "inherit", fontSize: 12.5,
                           fontWeight: chon_ht?.kieu === DON_VI && dangK === k ? 700 : 400 }}>
                  {dv.ten}{dv.ma ? <i style={{ color: "var(--vtos-text-faint)", fontStyle: "normal" }}> · {dv.ma}</i> : null}
                  {/* Đơn vị đã ngừng hoạt động VẪN ở trong danh sách – sáu tháng số liệu của nó
                      không biến mất theo. Nhưng phải có nhãn, kẻo người ta chọn nhầm rồi tưởng
                      đơn vị đang chạy mà không có doanh thu. */}
                  {dv.hoat_dong === false ? <i style={{ color: "var(--vtos-danger)", fontStyle: "normal" }}> · đã ngừng</i> : null}
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

          {/* Máy chủ chưa có bảng lưu lựa chọn (KHO_LUU is None). Không hứa "đã ghi nhớ". */}
          {chon_ht?.luu_tru === "chua_co" && (
            <span style={{ fontSize: 11, color: "var(--vtos-warning)", padding: "6px 4px 0", borderTop: "1px solid var(--vtos-line)", marginTop: 4 }}>
              Máy chủ chưa lưu lựa chọn này: đăng nhập lại sẽ trở về mặc định.
            </span>
          )}
        </span>
      )}
    </span>
  );
}
