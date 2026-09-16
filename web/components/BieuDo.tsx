"use client";
/** BỘ BIỂU ĐỒ DÙNG CHUNG CỦA VTOS — anh Tuấn chốt 15/9/2026.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  VÌ SAO MỘT BỘ DÙNG CHUNG, KHÔNG PHẢI VẼ TAY TỪNG CHỖ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  Trước vòng này VTOS đã có ba chỗ vẽ cột bằng tay: thẻ chỉ tiêu (the-xh), khối dòng tiền
 *  (dt-bd), khối tồn đọng (v14-bp). Ba chỗ ấy đã bắt đầu lệch nhau — chỗ có trục 0, chỗ không;
 *  chỗ coi ô trống là ô trống, chỗ suýt nữa quy thành 0. Thêm ba khu biểu đồ nữa mà vẫn vẽ tay
 *  là sáu bản chép của cùng một phép tính, và lúc chúng ra sáu kết quả thì không ai biết tin bản
 *  nào. Nên: MỘT bộ, mọi nơi gọi vào đây.
 *
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *  NĂM LUẬT, MỖI LUẬT SINH RA TỪ MỘT CÁCH ĐỌC SAI CỤ THỂ
 *  ═══════════════════════════════════════════════════════════════════════════════════════════
 *   1. RỖNG KHÁC KHÔNG. `null` là "chưa có số" và vẽ ra một chỗ trống giữ đúng vị trí. Quy nó
 *      thành 0 là nói kỳ ấy doanh thu bằng không; bỏ nó khỏi chuỗi là bóp méo khoảng thời gian
 *      mà biểu đồ vẫn trông bình thường.
 *   2. DƯỚI HAI ĐIỂM CÓ SỐ THÌ KHÔNG VẼ, và phải nói vì sao. Một cột đứng một mình không so với
 *      cái gì cả — người đọc vẫn sẽ đọc ra một xu hướng.
 *   3. TRỤC BẮT ĐẦU TỪ 0. Cắt chân trục làm một chênh lệch 3% trông như gấp đôi. Đây là cách bóp
 *      méo phổ biến nhất trên các bảng điều hành, và nó không cần ai cố ý.
 *   4. MỘT TRỤC TUNG. Không bao giờ hai thang đo trên một biểu đồ: đổi thang là đổi được kết
 *      luận, và hai đường cắt nhau ở đâu là do người vẽ chọn chứ không do số liệu. Hai đại lượng
 *      khác thang thì tách làm hai biểu đồ.
 *   5. NỐI THẲNG, KHÔNG LÀM MƯỢT. Đường cong mượt vẽ ra những giá trị NẰM GIỮA hai mốc, mà giữa
 *      tháng 5 và tháng 6 không tồn tại số nào. Đó là số do máy vẽ tự sinh ra.
 *
 *  Và một điều về màu: mọi màu lấy từ biến của bộ nhận diện, không gõ mã màu. Màu trạng thái
 *  (đỏ/vàng/xanh lá) chỉ dùng cho TRẠNG THÁI, không bao giờ làm "màu chuỗi thứ tư".
 *
 *  RANH GIỚI 09/9 GIỮ NGUYÊN: tệp này KHÔNG tính ra một con số nghiệp vụ nào. Nó nhận số đã tính
 *  sẵn và vẽ. Mọi phép tính nằm ở máy chủ.
 */
import { ReactNode } from "react";

/* ─────────────────────────── KIỂU DỮ LIỆU ─────────────────────────── */

/** Một điểm trên biểu đồ. `gt === null` nghĩa là CHƯA CÓ SỐ — không phải 0. */
export type Diem = {
  nhan: string; gt: number | null; ghi?: string;
  /* TC-44 · ba trường của bản vẽ "Kết quả kinh doanh" anh Tuấn gửi 16/9/2026.
     `mo`      – cột NGOÀI kỳ đang chọn: vẫn vẽ, nhưng mờ đi. Bỏ hẳn nó thì tháng 9 mất chỗ đứng
                 trong cả năm, và đó chính là thứ một hình 12 cột cho được mà ba hình riêng không.
     `ke_hoach`– chỉ tiêu của ĐÚNG kỳ ấy, để vẽ đường kế hoạch chạy theo từng cột. Một vạch ngang
                 duy nhất là nói dối về mười một tháng còn lại: chỉ tiêu tháng 1 khác tháng 12.
     `nhan_so` – có ghi số trên đầu cột này không. Mười hai con số chen nhau thì không đọc được cái
                 nào; bản vẽ chỉ ghi ở cột đầu và cột cuối. */
  mo?: boolean; ke_hoach?: number | null; nhan_so?: boolean;
  /* TC-47 · hai trường của bản vẽ "hai hình chung một trục ngang" anh Tuấn chốt 16/9/2026.

     `cho` – phần NỐI TIẾP mờ trên chính cây cột này: giá trị ĐÃ BIẾT nhưng CHƯA ĐỦ điều kiện để
             vào con số chính. Ở khối Kết quả kinh doanh, đó là doanh thu của chuyến đã đóng số mà
             Điều hành chưa nhập giá vốn — không được cộng vào cột chính (vì cột lãi bên dưới
             không có chúng, và hai hình phải nói về cùng một tập chuyến), nhưng cũng không được
             biến mất. Vẽ nối tiếp chứ không vẽ cột riêng: nó là MỘT phần của cùng một tháng.

     `gt2`  – cột thứ hai đứng cạnh, CÙNG một trục tung. Đây KHÔNG phải trục tung thứ hai (luật 4
             ở đầu tệp vẫn nguyên): hai cột chỉ đứng cạnh nhau khi cùng đơn vị và cùng thang đo,
             ví dụ lợi nhuận tour và lợi nhuận trước thuế. Khác thang thì tách thành hai hình. */
  cho?: number | null; gt2?: number | null;
};

/** Cách đọc con số. Quyết định cả nhãn trục lẫn nhãn trên cột: 1.840.000.000 đồng phải đọc là
 *  "1,8 tỷ" trên trục, còn 412 hồ sơ thì tuyệt đối không được gọi là "0,4 ng". */
export type DinhDang = "tien" | "dem" | "phan_tram";

/* ─────────────────────────── ĐỊNH DẠNG SỐ ─────────────────────────── */

export function gonSo(v: number, dd: DinhDang = "tien"): string {
  if (dd === "phan_tram") return `${Math.round(v * 100)}%`;
  if (dd === "dem") return v.toLocaleString("vi-VN");
  const a = Math.abs(v);
  const so = (x: number, le: number) => x.toLocaleString("vi-VN", { maximumFractionDigits: le });
  if (a >= 1e9) return `${so(v / 1e9, 1)} tỷ`;
  if (a >= 1e6) return `${so(v / 1e6, 0)} tr`;
  if (a >= 1e3) return `${so(v / 1e3, 0)} ng`;
  return so(v, 0);
}

export function daySo(v: number, dd: DinhDang = "tien"): string {
  if (dd === "phan_tram") return `${(v * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%`;
  return v.toLocaleString("vi-VN");
}

/* ─────────────────────────── MỐC TRỤC ─────────────────────────── */

/** Bước nhảy "đẹp": 1, 2, 5 nhân với luỹ thừa của 10. Bước lẻ (ví dụ 3.700.000) thì nhãn trục
 *  đọc ra toàn số lẻ và không ai ước lượng được cột cao bao nhiêu chỉ bằng mắt. */
function buoc(tho: number): number {
  if (!(tho > 0)) return 1;
  const mu = Math.pow(10, Math.floor(Math.log10(tho)));
  const ty = tho / mu;
  return (ty <= 1 ? 1 : ty <= 2 ? 2 : ty <= 5 ? 5 : 10) * mu;
}

/** Mốc trục, LUÔN CHỨA 0 (luật 3). Trả về từ thấp lên cao. */
export function mocTruc(min: number, max: number, soMoc = 4): number[] {
  if (!isFinite(min) || !isFinite(max)) return [0];
  const thap = Math.min(0, min);
  const cao = Math.max(0, max);
  if (thap === cao) return [0];
  const b = buoc((cao - thap) / Math.max(1, soMoc));
  const dau = Math.floor(thap / b) * b;
  const cuoi = Math.ceil(cao / b) * b;
  const ds: number[] = [];
  for (let v = dau; v <= cuoi + b * 1e-9; v += b) ds.push(Number(v.toPrecision(12)));
  return ds;
}

/* ─────────────────────────── ĐỦ ĐIỀU KIỆN VẼ CHƯA? ───────────────────────────
   Ba hàm thuần dưới đây là ĐÚNG những điều kiện mà ba thành phần vẽ dùng — và chúng phải là MỘT
   bản duy nhất, không phải hai bản giống nhau.

   Vì sao cần chúng đứng riêng: từ vòng TC-40, màn hình Chủ tịch KHÔNG bày biểu đồ rỗng nữa. Anh
   Tuấn chụp màn hình bản chạy thật và chốt 15/9/2026 — trên đó tám trong mười một biểu đồ là ô
   rỗng, và tám khung chữ "chưa có số" chiếm gần trọn màn hình của một người mở bảng ra để quyết
   việc. Nên nơi gọi phải HỎI TRƯỚC khi vẽ, để gom mọi chỗ rỗng vào đúng một dòng ở cuối.

   Nhưng "không bày" KHÔNG phải "giấu đi": dòng gom ấy nêu đích danh từng biểu đồ còn thiếu, bộ
   phận phải nạp và cửa nhập. Ranh giới 09/9 giữ nguyên — mỗi con số vẫn phải có một cửa, và chỗ
   chưa có cửa vẫn phải đọc được từ màn hình này. */

export function duVeCot(diem: Diem[]): boolean {
  return diem.filter((d) => d.gt !== null).length >= 2;
}

export function duVeThanh(ds: Thanh[]): boolean {
  const v = ds.filter((h) => typeof h.gt === "number").map((h) => h.gt as number);
  if (v.length < 2) return false;
  // Mọi dòng đều 0 thì không có gì để so — đây là số THẬT, nhưng một biểu đồ toàn thanh dài 0 thì
  // không nói thêm được điều gì mà bảng chưa nói.
  return !(Math.max(...v, 0) === 0 && Math.min(...v, 0) === 0);
}

export function duVeCoCau(ds: Phan[]): boolean {
  if (ds.some((p) => p.gt === null || p.gt === undefined)) return false;
  const v = ds.map((p) => p.gt as number);
  return !v.some((x) => x < 0) && v.reduce((a, b) => a + b, 0) !== 0;
}

/* ─────────────────────────── KHUNG & Ô RỖNG ─────────────────────────── */

export function KhungBieuDo({ ten, phu, chan, chuGiai, children }: {
  ten: string; phu?: string; chan?: ReactNode; chuGiai?: ReactNode; children: ReactNode;
}) {
  return (
    <figure className="bd">
      <figcaption className="bd-dau">
        <b>{ten}</b>
        {phu && <span className="muted bd-phu">{phu}</span>}
        {chuGiai}
      </figcaption>
      {children}
      {chan && <p className="muted bd-chan">{chan}</p>}
    </figure>
  );
}

/** Ô rỗng CHUẨN: nói chưa vẽ được, nói VÌ SAO, và nếu biết thì nói AI phải nạp số.
 *  Một khung xám không lời thì người đọc kết luận hệ thống hỏng — mà sự thật thường là chưa ai
 *  nhập, tức là một việc có chủ. */
export function BieuDoRong({ ten, vi_sao, ai, cua, cua_ten }: {
  ten: string; vi_sao: string; ai?: string; cua?: string; cua_ten?: string;
}) {
  return (
    <figure className="bd bd-rong">
      <figcaption className="bd-dau"><b>{ten}</b></figcaption>
      <p className="muted bd-rong-ly">{vi_sao}</p>
      {ai && (
        <p className="muted bd-rong-ai">
          <b>{ai}</b> nạp số.{" "}
          {cua && <a className="the-cua" href={cua}>{cua_ten || "Cửa nhập"} →</a>}
        </p>
      )}
    </figure>
  );
}

export function ChuGiai({ ds }: { ds: { ten: string; lop: string }[] }) {
  return (
    <span className="bd-chugiai">
      {ds.map((c) => (
        <span key={c.ten} className="bd-cg-mot">
          <i className={"bd-cg-cham " + c.lop} aria-hidden="true" />{c.ten}
        </span>
      ))}
    </span>
  );
}

/* ─────────────────────────── BIỂU ĐỒ CỘT ─────────────────────────── */

const CAO = 168;   // chiều cao vùng vẽ, px

/** Cột dọc theo kỳ. Dùng cho chuỗi thời gian: doanh thu tháng, lợi nhuận tháng, dòng tiền theo mốc.
 *
 *  CỘT CHỨ KHÔNG PHẢI ĐƯỜNG, và đây là lựa chọn có lý do: dữ liệu VTOS có lỗ hổng — tháng nào
 *  chưa ai nộp báo cáo thì tháng ấy trống. Đường nối liền qua chỗ trống là vẽ ra một giá trị
 *  không tồn tại; cột thì chỗ trống nhìn ra ngay là chỗ trống.
 *
 *  `moc` là một vạch mốc nằm ngang (kế hoạch tháng chẳng hạn). Nó là MỘT VẠCH trên CÙNG một trục,
 *  không phải một trục tung thứ hai — xem luật 4 ở đầu tệp.
 */
export function BieuDoCot({ ten, phu, diem, dinh_dang = "tien", moc, chan, ai, cua, cua_ten,
                           theo_dau, ten_duong, chuGiai, ten_cot2, ten_cho, an_nhan_x }: {
  ten: string; phu?: string; diem: Diem[]; dinh_dang?: DinhDang;
  moc?: { gt: number; nhan: string } | null;
  chan?: ReactNode; ai?: string; cua?: string; cua_ten?: string;
  /** TC-47 · tên của cột thứ hai (`Diem.gt2`). Có tên thì mới vẽ — cùng một trục tung. */
  ten_cot2?: string;
  /** TC-47 · tên của khúc nối tiếp mờ (`Diem.cho`). Có tên thì mới vẽ, và tên ấy đi thẳng vào câu
   *  chân: một khúc màu khác mà không nói nó là gì thì người đọc tự đoán, và đoán sai. */
  ten_cho?: string;
  /** TC-47 · giấu hàng nhãn trục ngang của hình này. Dùng khi hai hình xếp dọc DÙNG CHUNG một
   *  trục ngang: hình trên giấu, hình dưới hiện, và nhãn ấy nói cho cả hai. In hai lần thì người
   *  đọc phải kiểm xem hai hàng có khớp nhau không — một việc thừa trên mọi lần mở màn hình. */
  an_nhan_x?: boolean;
  /** TC-44 · tô cột theo DẤU: dương xanh lá, âm hồng. Dùng cho lãi/lỗ, nơi dấu chính là điều
   *  người đọc tìm. KHÔNG bật cho doanh thu: doanh thu âm là chuyện khác hẳn, và tô nó cùng màu
   *  với "lỗ" là trộn hai khái niệm. */
  theo_dau?: boolean;
  /** Tên của đường kế hoạch, hiện ở chú giải và ở câu chân. Có tên thì mới vẽ đường. */
  ten_duong?: string;
  chuGiai?: ReactNode;
}) {
  const coSo = diem.filter((d) => d.gt !== null) as { nhan: string; gt: number }[];
  if (!duVeCot(diem)) {
    return <BieuDoRong ten={ten} ai={ai} cua={cua} cua_ten={cua_ten}
      vi_sao={coSo.length === 0
        ? `Chưa có kỳ nào có số trong ${diem.length} kỳ gần nhất, nên chưa vẽ được.`
        : `Mới có 1/${diem.length} kỳ có số. Một cột đứng một mình không so được với gì — cần ít nhất hai kỳ.`} />;
  }

  const gt = coSo.map((d) => d.gt);
  // Đường kế hoạch phải nằm TRONG thang đo: một chỉ tiêu cao hơn mọi cột mà thang không tính nó
  // thì đường bị cắt ở mép trên, và một đường cụt đọc ra là "đã đạt" trong khi sự thật ngược lại.
  const kh = diem.map((d) => d.ke_hoach).filter((x): x is number => typeof x === "number");
  // TC-47 · CỘT THỨ HAI VÀ KHÚC NỐI TIẾP CŨNG PHẢI NẰM TRONG THANG ĐO, vì cùng một trục tung.
  // Quên chúng thì thang tính theo cột chính, còn cột kia cao hơn sẽ bị cắt ngang ở mép trên —
  // và một cột cụt vẫn trông như một cột, chỉ là thấp hơn sự thật.
  const g2 = ten_cot2
    ? diem.map((d) => d.gt2).filter((x): x is number => typeof x === "number") : [];
  const dinh_cho = ten_cho
    ? diem.map((d) => (typeof d.gt === "number" ? d.gt : 0) + (d.cho || 0)) : [];
  const thap = Math.min(...gt, ...kh, ...g2, ...dinh_cho, moc ? moc.gt : 0);
  const cao = Math.max(...gt, ...kh, ...g2, ...dinh_cho, moc ? moc.gt : 0);
  const mocs = mocTruc(thap, cao);
  const tMin = mocs[0];
  const tMax = mocs[mocs.length - 1];
  const bien = tMax - tMin || 1;
  const y = (v: number) => ((tMax - v) / bien) * CAO;   // px tính từ mép trên
  const y0 = y(0);
  const coAm = gt.some((v) => v < 0);

  return (
    <KhungBieuDo ten={ten} phu={phu} chan={chan} chuGiai={chuGiai}>
      {/* `day` = biểu đồ DÀY CỘT (trên tám cột). Mười hai cột tháng ở bề ngang điện thoại chỉ còn
          chừng hai chục pixel mỗi cột, và nhãn "T10" bị cắt thành "T.." — tìm ra bằng cách dựng ảnh
          ở bề ngang 390px, đọc mã thì không thấy. Nhãn cắt cụt còn tệ hơn không có nhãn: người đọc
          tưởng mình đọc được. Lớp này để CSS thu hẹp khe và cỡ chữ ĐÚNG những hình dày cột, không
          động tới các hình sáu cột vốn đang vừa vặn. */}
      <div className={"bd-than" + (diem.length > 8 ? " day" : "")}>
        <div className="bd-truc" style={{ height: CAO }}>
          {mocs.map((m) => (
            <span key={m} className="bd-truc-nhan" style={{ top: y(m) }}>{gonSo(m, dinh_dang)}</span>
          ))}
        </div>
        <div className="bd-o" style={{ height: CAO }}>
          {mocs.map((m) => (
            <i key={m} aria-hidden="true"
              className={"bd-luoi" + (m === 0 ? " khong" : "")} style={{ top: y(m) }} />
          ))}
          {moc && (
            <i className="bd-moc" style={{ top: y(moc.gt) }}
              title={`${moc.nhan}: ${daySo(moc.gt, dinh_dang)}`} aria-hidden="true" />
          )}
          {/* ĐƯỜNG KẾ HOẠCH — vẽ bằng SVG phủ lên vùng cột, KHÔNG phải một vạch ngang.
              `preserveAspectRatio="none"` để toạ độ x chạy theo phần trăm bề ngang: nhờ vậy đường
              luôn khớp tâm cột dù khung rộng hay hẹp, không phải đo lại bằng JavaScript.
              Đoạn nào thiếu chỉ tiêu thì ĐỨT — nối liền qua chỗ trống là bịa ra một chỉ tiêu. */}
          {ten_duong && (
            <svg className="bd-duong" viewBox={`0 0 100 ${CAO}`} preserveAspectRatio="none"
                 aria-hidden="true">
              {diem.map((d, i) => {
                const k = d.ke_hoach, k2 = diem[i + 1]?.ke_hoach;
                if (typeof k !== "number" || typeof k2 !== "number") return null;
                const b = 100 / diem.length;
                return <line key={d.nhan} x1={b * (i + 0.5)} y1={y(k)}
                  x2={b * (i + 1.5)} y2={y(k2)} />;
              })}
            </svg>
          )}
          <div className="bd-cot">
            {diem.map((d) => {
              if (d.gt === null) {
                // `mo` phải theo cả ô TRỐNG, không riêng cột có số: ở kỳ Quý, tháng 11 vừa ngoài
                // kỳ vừa chưa có số, mà bỏ `mo` đi thì nó nhìn hệt tháng trống NẰM TRONG kỳ — hai
                // việc khác hẳn nhau (một cái chưa xảy ra, một cái chưa ai nộp sổ).
                return <span key={d.nhan} className={"bd-mot bd-khuyet" + (d.mo ? " mo" : "")}
                  title={`${d.nhan}: chưa có số`} />;
              }
              const h = Math.max(1, Math.abs(y(d.gt) - y0));
              const am = d.gt < 0;
              // `nhan_so` chưa khai thì giữ nết cũ: cột nào cũng ghi số. Khai rồi thì chỉ ghi ở
              // những cột được chọn — bản vẽ ghi ở cột đầu và cột cuối.
              const ghiSo = d.nhan_so === undefined ? true : d.nhan_so;
              // TC-47 · khúc CHỜ nối tiếp: chỉ vẽ cho cột DƯƠNG. Nối một khúc "chưa đủ điều kiện"
              // lên đầu một cột âm thì không còn đọc ra được nó cộng vào đâu.
              const cho = ten_cho && !am && d.cho ? Math.abs(y(d.gt + d.cho) - y(d.gt)) : 0;
              const g2 = ten_cot2 && typeof d.gt2 === "number" ? d.gt2 : null;
              const h2 = g2 === null ? 0 : Math.max(1, Math.abs(y(g2) - y0));
              const am2 = g2 !== null && g2 < 0;
              return (
                <span key={d.nhan} className={"bd-mot" + (d.mo ? " mo" : "")
                      + (ten_cot2 ? " doi" : "")}
                  title={`${d.nhan}: ${daySo(d.gt, dinh_dang)}${d.ghi ? " · " + d.ghi : ""}`}>
                  <span className={"bd-thanh" + (am ? " am" : "")
                        + (theo_dau ? (am ? " lo" : " lai") : "")}
                    style={{ height: h, top: am ? y0 : y0 - h }} />
                  {cho > 0 && (
                    <span className="bd-thanh cho" style={{ height: cho, top: y0 - h - cho }}
                      title={`${d.nhan}: ${daySo(d.cho as number, dinh_dang)} — ${ten_cho}`} />
                  )}
                  {g2 !== null && (
                    <span className={"bd-thanh hai" + (am2 ? " am" : "")
                          + (theo_dau ? (am2 ? " lo" : " lai") : "")}
                      style={{ height: h2, top: am2 ? y0 : y0 - h2 }}
                      title={`${d.nhan}: ${daySo(g2, dinh_dang)} — ${ten_cot2}`} />
                  )}
                  {/* Nhãn số nằm NGOÀI cột, phía đầu cột — đặt trong lòng cột thì cột thấp không
                      chứa nổi chữ và chữ tràn ra trông như thuộc cột bên cạnh.
                      CÓ CỘT THỨ HAI THÌ KHÔNG GHI SỐ: hai con số trên một tháng rộng hai chục
                      pixel thì chồng lên nhau, và lúc ấy không đọc được con số nào thuộc cột nào.
                      Chiều cao hai cột cạnh nhau đã nói đủ điều cần nói ở hình này. */}
                  {ghiSo && !ten_cot2 && <span className={"bd-so" + (am ? " am" : "")}
                    style={am ? { top: y0 + h + 2 } : { top: Math.max(0, y0 - h - cho - 15) }}>
                    {gonSo(d.gt, dinh_dang)}
                  </span>}
                </span>
              );
            })}
          </div>
        </div>
        <div className="bd-goc" />
        {/* TC-47 · hình trên của một cặp dùng chung trục ngang thì giấu hàng nhãn này. Giấu bằng
            `aria-hidden` + CSS chứ không bỏ hẳn thẻ: bỏ hẳn thì hai hình lệch nhau đúng chiều cao
            hàng nhãn, và tháng 9 của hình trên không còn nằm trên tháng 9 của hình dưới — mất
            chính cái mà "chung một trục ngang" sinh ra để có. */}
        <div className={"bd-nhanx" + (an_nhan_x ? " an" : "")} aria-hidden={an_nhan_x || undefined}>
          {diem.map((d) => <span key={d.nhan} className={d.gt === null ? "muted" : ""}>{d.nhan}</span>)}
        </div>
      </div>
      {(moc || coAm || ten_duong || ten_cho || diem.some((d) => d.gt === null)) && (
        <p className="muted bd-chu">
          {diem.some((d) => d.gt === null) && <>Ô trống = <b>chưa có số</b>, không phải 0. </>}
          {coAm && <>Vạch đậm là mốc 0; cột dưới vạch là số âm. </>}
          {moc && <>Vạch đứt là <b>{moc.nhan}</b> ({daySo(moc.gt, dinh_dang)}), cùng một trục. </>}
          {ten_duong && <>Đường đứt là <b>{ten_duong}</b>, cùng một trục; đoạn nào đứt là kỳ ấy
            chưa có chỉ tiêu. </>}
          {ten_cho && diem.some((d) => d.cho) && <>Khúc mờ trên đầu cột là <b>{ten_cho}</b> —
            đã biết nhưng chưa vào con số chính. </>}
          {diem.some((d) => d.mo) && <>Cột mờ là kỳ NGOÀI kỳ đang chọn. </>}
        </p>
      )}
    </KhungBieuDo>
  );
}

/* ─────────────────────────── BIỂU ĐỒ THANH NGANG ─────────────────────────── */

export type Thanh = {
  ten: string; gt: number | null; nhan_phu?: boolean; ghi?: string;
  /** TC-45 · dòng này là một TRẠNG THÁI chứ không phải một nấc của thang (ví dụ "Quá hạn" giữa các
   *  mốc hạn còn lại). Mang màu cảnh báo, và KHÔNG bị đẩy xuống cuối như `nhan_phu` — nó vẫn là
   *  một trong các nhóm, vẫn đứng đúng chỗ của nó trong thứ tự. Cùng nghĩa với `Phan.trang_thai`
   *  ở biểu đồ cơ cấu, nên phải cùng một màu: một khái niệm hai màu là hai khái niệm. */
  trang_thai?: boolean;
};

/** Thanh ngang xếp hạng. Dùng khi nhãn là TÊN (bộ phận, nhân viên, khách hàng) chứ không phải kỳ:
 *  cột dọc thì tên tiếng Việt phải xoay nghiêng hoặc cắt cụt mới vừa.
 *
 *  `nhan_phu` = dòng này KHÔNG cùng loại với các dòng kia (ví dụ "Chưa rõ bộ phận" giữa các
 *  phòng). Nó mang màu khác và luôn đứng cuối — tô cùng màu là xếp một chỗ chưa ai nhận ngang
 *  hàng với một phòng có người chịu trách nhiệm.
 */
export function BieuDoThanh({ ten, phu, ds, dinh_dang = "dem", chan, ai, cua, cua_ten, xep = true,
                             chuGiai }: {
  ten: string; phu?: string; ds: Thanh[]; dinh_dang?: DinhDang;
  chan?: ReactNode; ai?: string; cua?: string; cua_ten?: string; xep?: boolean;
  /** Chú giải tuỳ chọn, cùng kiểu với hai biểu đồ kia. Thân hàm đã chuyền nó xuống `KhungBieuDo`
   *  từ vòng TC-44 nhưng QUÊN khai ở đây — esbuild không bắt lỗi ấy (nó chỉ dịch, không kiểm
   *  kiểu), CI mới bắt, mất một vòng dựng. Từ TC-45 có bộ soát kiểu chạy cục bộ. */
  chuGiai?: ReactNode;
}) {
  const hang = xep ? xepThanh(ds) : ds;
  const coSo = hang.filter((h) => typeof h.gt === "number").map((h) => h.gt as number);
  if (!duVeThanh(hang)) {
    return <BieuDoRong ten={ten} ai={ai} cua={cua} cua_ten={cua_ten}
      vi_sao={coSo.length === 0
        ? "Chưa dòng nào có số, nên chưa vẽ được."
        : "Mới có 1 dòng có số. Một thanh dài hết khung không so với gì cả — cần ít nhất hai dòng."} />;
  }
  const max = Math.max(...coSo, 0);
  const min = Math.min(...coSo, 0);
  if (max === 0 && min === 0) {
    return <BieuDoRong ten={ten}
      vi_sao="Mọi dòng đều bằng 0. Đây là số THẬT — không có gì để so, nên không vẽ." />;
  }
  /* Có số âm thì thang phải trải từ min tới max và mốc 0 nằm giữa; không có số âm thì 0 nằm ở
     mép trái như bình thường. Vẽ mọi thanh từ mép trái khi có số âm là biến một khoản âm thành
     một thanh ngắn trông như khoản dương ít tiền. */
  const bien = max - Math.min(0, min) || 1;
  const goc = (-Math.min(0, min) / bien) * 100;   // vị trí mốc 0, tính bằng % bề ngang

  return (
    <KhungBieuDo ten={ten} phu={phu} chan={chan} chuGiai={chuGiai}>
      <div className="bd-th" role="img"
        aria-label={`${ten}: ` + hang.map((h) =>
          `${h.ten} ${h.gt === null ? "chưa có số" : daySo(h.gt, dinh_dang)}`).join(" · ")}>
        {hang.map((h) => (
          <div key={h.ten} className="bd-th-hang">
            <span className="bd-th-ten" title={h.ten}>{h.ten}</span>
            <span className="bd-th-rai">
              {min < 0 && <i className="bd-th-truc0" style={{ left: `${goc}%` }} aria-hidden="true" />}
              {h.gt === null
                ? <span className="bd-th-khuyet">chưa có số</span>
                : <span
                    className={"bd-th-thanh" + (h.nhan_phu ? " phu" : "")
                      + (h.trang_thai ? " tt" : "") + (h.gt < 0 ? " am" : "")}
                    style={h.gt < 0
                      ? { right: `${100 - goc}%`, width: `max(3px, ${(-h.gt / bien) * 100}%)` }
                      : { left: `${goc}%`, width: h.gt === 0 ? 0 : `max(3px, ${(h.gt / bien) * 100}%)` }}
                    title={`${h.ten}: ${daySo(h.gt, dinh_dang)}${h.ghi ? " · " + h.ghi : ""}`} />}
            </span>
            <span className="bd-th-so">{h.gt === null ? "" : gonSo(h.gt, dinh_dang)}</span>
          </div>
        ))}
      </div>
    </KhungBieuDo>
  );
}

/** Xếp nhiều trước; dòng chưa có số dồn xuống cuối; dòng `nhan_phu` luôn ở cuối cùng.
 *
 *  VÌ SAO DÒNG CHƯA CÓ SỐ KHÔNG COI LÀ 0: xếp theo độ lớn thì một dòng chưa ai đếm không có chỗ
 *  nào trong thứ tự ấy cả. Nhét nó xuống cuối THEO SỐ 0 là gán cho nó một giá trị nó không có, và
 *  người đọc sẽ đọc ra "phòng này sạch nhất". */
export function xepThanh(ds: Thanh[]): Thanh[] {
  const chinh = ds.filter((d) => !d.nhan_phu);
  const phu = ds.filter((d) => d.nhan_phu);
  chinh.sort((a, b) => {
    if (a.gt === null && b.gt === null) return 0;
    if (a.gt === null) return 1;
    if (b.gt === null) return -1;
    return b.gt - a.gt;
  });
  return [...chinh, ...phu];
}

/* ─────────────────────────── THANH CƠ CẤU ─────────────────────────── */

export type Phan = { ten: string; gt: number | null; trang_thai?: boolean };

/** Một thanh chia khúc: các phần của MỘT tổng.
 *
 *  CHỈ DÙNG KHI CÁC PHẦN KHÔNG TRÙNG NHAU. Bảng bốn mốc dòng tiền ở khối 06 là LUỸ KẾ — cột sau
 *  đã chứa trọn cột trước — nên tuyệt đối không được vẽ kiểu này: làm thế là cộng một khoản tiền
 *  vào chính nó bốn lần.
 *
 *  Bề rộng đặt bằng flex-grow chứ không phải width phần trăm: các khúc cách nhau 2px, mà các bề
 *  rộng phần trăm cộng đúng 100% thì tổng cả gap vượt khung và khúc CUỐI bị cắt cụt — tức phần
 *  cuối luôn trông nhỏ hơn sự thật. flex chia phần còn lại sau khi trừ gap nên tỉ lệ đúng.
 */
export function BieuDoCoCau({ ten, phu, ds, dinh_dang = "tien", chan, ai, cua, cua_ten }: {
  ten: string; phu?: string; ds: Phan[]; dinh_dang?: DinhDang;
  chan?: ReactNode; ai?: string; cua?: string; cua_ten?: string;
}) {
  const thieu = ds.filter((p) => p.gt === null || p.gt === undefined);
  if (thieu.length) {
    return <BieuDoRong ten={ten} ai={ai} cua={cua} cua_ten={cua_ten}
      vi_sao={`Còn thiếu ${thieu.length}/${ds.length} phần: ${thieu.map((p) => p.ten).join(" · ")}. `
        + "Mọi tỉ lệ đều tính trên tổng các phần, nên thiếu một phần là mọi tỉ lệ đều sai. "
        + "Hệ thống không quy đổi phần thiếu thành 0."} />;
  }
  const gt = ds.map((p) => p.gt as number);
  if (gt.some((v) => v < 0)) {
    return <BieuDoRong ten={ten}
      vi_sao="Có phần mang số âm. Một phần âm của một tổng thì không có bề dài nào biểu diễn đúng được." />;
  }
  const tong = gt.reduce((a, b) => a + b, 0);
  if (tong === 0) {
    return <BieuDoRong ten={ten}
      vi_sao="Tổng các phần bằng 0 — không có gì để chia tỉ lệ. Đây là số THẬT, khác hẳn chưa có nguồn số." />;
  }
  return (
    <KhungBieuDo ten={ten} phu={phu} chan={chan}
      chuGiai={<ChuGiai ds={ds.map((p, i) => ({
        ten: p.ten, lop: p.trang_thai ? "bd-mau-tt" : `bd-mau-${Math.min(i + 1, 5)}`,
      }))} />}>
      <div className="bd-cc" role="img"
        aria-label={`${ten}: ` + ds.map((p, i) =>
          `${p.ten} ${Math.round((gt[i] / tong) * 100)}%`).join(" · ")}>
        {ds.map((p, i) => (
          <span key={p.ten} style={{ flexGrow: gt[i], flexBasis: 0 }}
            className={"bd-cc-o " + (p.trang_thai ? "bd-mau-tt" : `bd-mau-${Math.min(i + 1, 5)}`)}
            title={`${p.ten}: ${daySo(gt[i], dinh_dang)} · ${Math.round((gt[i] / tong) * 100)}%`} />
        ))}
      </div>
      <div className="bd-cc-so">
        {ds.map((p, i) => (
          <span key={p.ten}>
            <b>{Math.round((gt[i] / tong) * 100)}%</b>
            {/* Số gốc in KÈM tỉ lệ, vì tỉ lệ một mình không nói được quy mô: 33% của 9 hồ sơ và
                33% của 900 hồ sơ là hai việc khác hẳn nhau. Trừ khi bản thân số gốc ĐÃ là tỉ lệ
                — lúc ấy in ra sẽ thành "63% 63%". */}
            {dinh_dang !== "phan_tram" && <span className="muted">{gonSo(gt[i], dinh_dang)}</span>}
          </span>
        ))}
      </div>
      {dinh_dang !== "phan_tram" && (
        <p className="muted bd-chu">
          Tổng <b>{daySo(tong, dinh_dang)}</b>. Các phần không trùng nhau nên cộng đủ 100%.
        </p>
      )}
    </KhungBieuDo>
  );
}
