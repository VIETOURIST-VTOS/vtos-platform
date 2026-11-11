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

     `cho` – phần NỐI TIẾP mờ trên chính cây cột này: một phần của cùng một tháng, vẽ nối tiếp
             chứ không vẽ cột riêng. Cao cả cây = `gt` + `cho`, và hình này KHÔNG đổi.

             08/10/2026 — CHỖ GỌI ĐÃ ĐỔI NGHĨA, ghi lại để người đọc sau khỏi suy ra sai từ hình.
             Ở khối Kết quả kinh doanh, `cho` là doanh thu của chuyến chưa có giá vốn. Trước hôm
             nay phần ấy KHÔNG nằm trong con số doanh thu (cột lãi bên dưới không có chúng, và
             hai hình phải nói về cùng một tập chuyến). Chủ tịch chốt 08/10 lấy số liệu y chang
             của Vietrip, nên phần ấy NAY ĐÃ nằm trong doanh thu: bên ấy truyền `gt` là phần CÓ
             giá vốn và `cho` là phần thiếu, nên cao cả cây đúng bằng doanh thu gộp và con số in
             dưới hình khớp với chiều cao. Hình vẫn vẽ "nối tiếp"; chỉ ý nghĩa hai mảnh là đổi.

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

export function KhungBieuDo({ ten, phu, chan, chuGiai, ben_ten, children }: {
  ten: string; phu?: string; chan?: ReactNode; chuGiai?: ReactNode;
  /** TC-65 · Một cửa đứng NGAY CẠNH tên hình, trước chú giải.
   *
   *  Chỗ này dành cho đường dẫn tới màn hình mà chính hình đang tóm tắt — anh Tuấn 18/9/2026:
   *  "đưa chữ cấu trúc chi tiết dòng tiền lên kề bên chữ dự báo dòng tiền 13 tuần". Đặt cạnh tên
   *  hình thì đọc ra ngay nó dẫn đi đâu; để nó nằm một mình dưới đáy khối thì nó thành một dòng
   *  chữ trôi nổi giữa một dải trống. KHÔNG dùng chỗ này cho chú giải: chú giải có `chuGiai`, và
   *  nó phải bị đẩy sang mép phải để không chen vào giữa tên hình và cửa. */
  ben_ten?: ReactNode;
  children: ReactNode;
}) {
  return (
    <figure className="bd">
      <figcaption className="bd-dau">
        <b>{ten}</b>
        {phu && <span className="muted bd-phu">{phu}</span>}
        {ben_ten}
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
/** Biểu đồ CHƯA CÓ SỐ.
 *
 *  TC-49 · KHUNG RỖNG PHẢI GIỮ ĐÚNG HÌNH DÁNG CỦA BIỂU ĐỒ THẬT (anh Tuấn duyệt bản thử giao diện
 *  17/9/2026 rồi chốt "đưa lên web đúng y chang vậy").
 *
 *  Bản cũ chỉ in một dòng chữ. Chạy được, và đúng về nội dung — nhưng khi CẢ màn hình chưa có
 *  nguồn thì mọi khối co lại thành mấy đoạn văn xuôi, và bảng điều hành không còn ra hình dáng một
 *  bảng điều hành nữa. Anh Tuấn mở trang thật ngày 17/9 và nói đúng một câu: "trên màn hình chưa
 *  có biểu đồ, và giao diện chưa giống file ảnh anh gửi". Cả hai vế đều từ chỗ này mà ra.
 *
 *  BA ĐIỀU KHUNG RỖNG PHẢI LÀM, VÀ MỘT ĐIỀU TUYỆT ĐỐI KHÔNG:
 *    · giữ đúng chiều cao và bề ngang của hình thật, để bố cục không nhảy khi số về;
 *    · vẽ trục và NHÃN THẬT (T1…T12, bảy nhóm hạn) — người đọc thấy trước hình này sẽ nói gì;
 *    · nói rõ vì sao rỗng, ai nạp, cửa nào.
 *    · KHÔNG vẽ một cột nào có chiều cao. Ô trống là ô trống; một cột giả cao lên trong khung
 *      rỗng là con số bịa, và bịa trên bảng điều hành Chủ tịch là chỗ nguy hiểm nhất của cả hệ
 *      thống. Nên chỗ giữ chỗ chỉ là khung nét đứt, không có phần tô.
 */
export function BieuDoRong({ ten, phu, vi_sao, ai, cua, cua_ten, nhan, ngang }: {
  ten: string; phu?: string; vi_sao: string; ai?: string; cua?: string; cua_ten?: string;
  /** Nhãn của các ô sẽ có khi có số: "T1"…"T12", hoặc bảy nhóm hạn. Có nhãn thì vẽ khung. */
  nhan?: string[];
  /** Thanh NGANG (nhãn là tên) thay vì cột dọc (nhãn là kỳ). */
  ngang?: boolean;
}) {
  const ds = nhan || [];
  return (
    <figure className="bd bd-rong">
      <figcaption className="bd-dau">
        <b>{ten}</b>{phu && <span className="muted bd-phu"> {phu}</span>}
      </figcaption>

      {ds.length > 0 && (ngang ? (
        <div className="bd-rong-ngang" aria-hidden="true">
          {ds.map((n) => (
            <div key={n} className="bd-rong-hang">
              <span className="bd-rong-ten">{n}</span>
              <span className="bd-rong-ray" />
            </div>
          ))}
        </div>
      ) : (
        <div className={"bd-rong-khung" + (ds.length > 8 ? " day" : "")} aria-hidden="true">
          <div className="bd-rong-o">
            {/* Ba vạch lưới mờ: đủ để mắt đọc ra "đây là một khung biểu đồ", không nhiều tới mức
                trông như một hình đã có số. Không ghi nhãn trục tung — chưa có số thì chưa có
                thang đo, và in một thang đo bịa còn tệ hơn không in. */}
            <i className="bd-rong-luoi" style={{ top: "0%" }} />
            <i className="bd-rong-luoi" style={{ top: "50%" }} />
            <i className="bd-rong-luoi khong" style={{ top: "100%" }} />
            <div className="bd-rong-cot">
              {ds.map((n) => <span key={n} className="bd-rong-mot" />)}
            </div>
          </div>
          <div className="bd-nhanx">
            {ds.map((n) => <span key={n} className="muted">{n}</span>)}
          </div>
        </div>
      ))}

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
                           theo_dau, ten_duong, chuGiai, ten_cot2, ten_cho }: {
  ten: string; phu?: string; diem: Diem[]; dinh_dang?: DinhDang;
  moc?: { gt: number; nhan: string } | null;
  chan?: ReactNode; ai?: string; cua?: string; cua_ten?: string;
  /** TC-47 · tên của cột thứ hai (`Diem.gt2`). Có tên thì mới vẽ — cùng một trục tung. */
  ten_cot2?: string;
  /** TC-47 · tên của khúc nối tiếp mờ (`Diem.cho`). Có tên thì mới vẽ, và tên ấy đi thẳng vào câu
   *  chân: một khúc màu khác mà không nói nó là gì thì người đọc tự đoán, và đoán sai. */
  ten_cho?: string;
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
    // TC-49 · truyền NHÃN THẬT xuống khung rỗng, để hình rỗng giữ đúng hình dáng hình thật.
    return <BieuDoRong ten={ten} phu={phu} ai={ai} cua={cua} cua_ten={cua_ten}
      nhan={diem.map((d) => d.nhan)}
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
                  tabIndex={0} title={`${d.nhan}: chưa có số`}>
                  {/* Tháng TRỐNG cũng có nhãn rê chuột, và nó nói "chưa có số" chứ không nói 0.
                      Bỏ nhãn ở đây thì rê vào tháng 11 không ra gì, và người dùng không phân biệt
                      được "hình hỏng" với "tháng chưa có số" — hai việc khác hẳn nhau. */}
                  <span className="bd-cot-so trong" aria-hidden="true">
                    <i>{d.ghi || d.nhan}</i><b className="chua">chưa có số</b>
                  </span>
                </span>;
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
                  tabIndex={0}
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

                      ══ 12/10/2026 · HÌNH CÓ HAI CỘT NAY CŨNG GHI SỐ ═══════════════════════════
                      Luật cũ ở đây là `!ten_cot2`: hình nào có cột thứ hai thì KHÔNG ghi số nào
                      cả. Lý do cũ ĐÚNG và vẫn giữ nguyên hiệu lực — hai con số trên một tháng
                      rộng hai chục pixel thì chồng lên nhau. Nhưng nó chữa bằng cách bỏ CẢ HAI,
                      nên hình Lợi nhuận từng tháng không có lấy một con số, trong khi hình Doanh
                      thu ngay trên nó có bốn. Chủ tịch nêu đúng chỗ ấy hôm nay.

                      Cách chữa giữ được cả hai điều: ghi số cho ĐÚNG MỘT cột — cột chính — và
                      căn nhãn LỆCH sang nửa trái, đúng tâm cột chính. Không bao giờ có hai nhãn
                      cố định trên một tháng, nên cảnh chồng chữ mà luật cũ sợ không xảy ra; mà
                      hình vẫn có bốn con số để liếc. Con số của cột thứ hai đọc bằng rê chuột,
                      ở nhãn ngay bên dưới. */}
                  {ghiSo && <span className={"bd-so" + (am ? " am" : "") + (ten_cot2 ? " trai" : "")}
                    style={am ? { top: y0 + h + 2 } : { top: Math.max(0, y0 - h - cho - 15) }}>
                    {gonSo(d.gt, dinh_dang)}
                  </span>}
                  {/* NHÃN RÊ CHUỘT CHO TỪNG THÁNG — Chủ tịch chốt 12/10/2026: "4 con số hiển thị,
                      ngoài ra các tháng khác thêm phần rê chuột hoặc chạm vào sẽ hiện ra".

                      Nó liệt kê ĐỦ các con số của tháng ấy, mỗi con một dòng: cột chính, khúc chờ
                      nếu có, và cột thứ hai nếu có. KHÔNG cộng chúng lại — khúc chờ là doanh thu
                      của chuyến chưa có giá vốn, gộp vào là nói quá con số đã ghi nhận, đúng cái
                      bẫy đã ghi ở `ket_qua_kinh_doanh.py` ngày 08/10.

                      Đây là thứ nhãn cố định KHÔNG làm được: đọc được cả cặp của cùng một tháng
                      trong một lần nhìn — tháng lãi tour dương mà trước thuế âm là chuyện chỉ lộ
                      ra khi hai con số đứng cạnh nhau. */}
                  <span className="bd-cot-so" aria-hidden="true"
                    style={am ? { top: y0 + h + 6 } : { top: Math.max(0, y0 - h - cho - 44) }}>
                    <i>{d.ghi || d.nhan}</i>
                    <b>{daySo(d.gt, dinh_dang)}</b>
                    {cho > 0 && <i>{ten_cho}: {daySo(d.cho as number, dinh_dang)}</i>}
                    {g2 !== null && <b className="hai">{daySo(g2, dinh_dang)}</b>}
                  </span>
                </span>
              );
            })}
          </div>
        </div>
        <div className="bd-goc" />
        {/* TC-62 · `an_nhan_x` ĐÃ XOÁ cùng với bố cục hai tầng của TC-47. Nó chỉ có một người
            dùng — hình Doanh thu — và người ấy nay nằm ở khung riêng, mang đủ nhãn tháng của
            mình. Giữ lại một thuộc tính không ai truyền là để vòng sau dựng lại bố cục cũ mà
            không đọc lý do đảo chiều (ghi trong KhoiKetQuaKinhDoanh.tsx). */}
        {/* TC-67 · `dong-nhan` BẬT LUẬT ẨN NHÃN CHẴN KHI Ô NHÃN HẸP HƠN CHỮ (luật ở globals.css).
            Ngưỡng 10 nhãn, chứ không phải "cứ hẹp là ẩn": hình mười hai tháng thì ẩn bớt là đúng,
            còn hình bốn quý trong cùng bề rộng ấy thì bốn nhãn vẫn vừa — ẩn ở đó là giấu đi thứ
            đang đọc được. Luật CSS không đếm được số cột nên phải nói cho nó biết từ đây.
            Nhãn bị ẩn KHÔNG mất câu trả lời: rê chuột lên cột là đọc được tên và số của cột ấy. */}
        <div className={"bd-nhanx" + (diem.length >= 10 ? " dong-nhan" : "")}>
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
          {ten_cho && diem.some((d) => d.cho) && <>Khúc mờ ở phần trên cây cột là{" "}
            <b>{ten_cho}</b> — nằm TRONG con số của cột, tách ra để thấy riêng. </>}
          {diem.some((d) => d.mo) && <>Cột mờ là kỳ NGOÀI kỳ đang chọn. </>}
        </p>
      )}
    </KhungBieuDo>
  );
}

/* ─────────────────────────── BIỂU ĐỒ ĐƯỜNG (NHIỀU CHUỖI) ───────────────────────────
   TC-59 · 17/9/2026. Anh Tuấn gửi một bản mẫu "BIẾN ĐỘNG DÒNG TIỀN" — ba đường THU · CHI · TỒN
   trên cùng một khung — và bảo dựng lại biểu đồ dòng tiền giống nó.

   VÌ SAO ĐƯỜNG Ở ĐÂY, TRONG KHI LUẬT CỦA TỆP NÀY NGHIÊNG VỀ CỘT
   `BieuDoCot` chọn cột vì dữ liệu VTOS có lỗ hổng: tháng nào chưa ai nộp báo cáo thì tháng ấy
   trống, và một đường nối liền qua chỗ trống là vẽ ra một giá trị không tồn tại. Lý lẽ ấy vẫn
   đúng — nên hàm này KHÔNG nối qua chỗ trống: gặp `null` là đường ĐỨT, và điểm ấy không có chấm.
   Ba chuỗi cùng một khung thì cột không dùng được (ba cột cạnh nhau ở mười ba tuần là ba mươi
   chín cột, không đọc nổi), còn đường thì so được ngay chuỗi nào đang vượt chuỗi nào.

   NĂM LUẬT Ở ĐẦU TỆP GIỮ NGUYÊN HẾT, và luật 4 (MỘT TRỤC TUNG) là luật khó nhất ở đây: ba chuỗi
   phải CÙNG ĐƠN VỊ. Bản mẫu của anh Tuấn có số ở cả mép trái lẫn mép phải — `doi_xung` vẽ lại
   đúng vậy, nhưng hai mép đọc từ CÙNG một mảng `moc`, nên đó là một thang đo in hai lần chứ không
   phải hai thang đo. Khác thang thì vẫn phải tách làm hai hình.

   MÀU — ĐÃ CHẠY BỘ KIỂM MÙ MÀU, KHÔNG CHỌN BẰNG MẮT
   Bản mẫu dùng cam (THU) · xanh dương (CHI) · xanh lá (TỒN). Chạy bộ kiểm tách màu trên đúng ba
   biến của bộ nhận diện VTOS: cặp xanh lá `--vtos-success` và hồng `--vtos-danger` chỉ cách nhau
   ΔE 2,1 với mắt mù màu lục (deutan) — người ấy KHÔNG phân biệt được đường thu với đường chi, mà
   đó là hai đường quan trọng nhất hình. Nên bộ ba chốt lại là:

       TỒN  → --vtos-navy      (chuỗi chính, cùng màu với cột của hình cũ)
       CHI  → --vtos-danger    (tiền rời khỏi tài khoản)
       THU  → --vtos-warning   (KHÔNG phải vì "cần chú ý" — mà vì xanh lá trượt phép kiểm trên)

   Ba cặp bất kỳ nay cách nhau ít nhất ΔE 14,7 với mọi kiểu mù màu. Ngoài màu, mỗi chuỗi còn có
   hình chấm riêng và nhãn số ở hai đầu, nên danh tính KHÔNG bao giờ chỉ nằm ở màu.

   VẠCH NGƯỠNG đổi sang màu chữ mờ, nét đứt — khác với `.bd-moc` của biểu đồ cột (vàng). Lý do
   hẹp và cụ thể: vàng ở hình này đã là đường THU rồi. Một vạch cùng màu với một chuỗi là chỗ
   người đọc nhìn nhầm vạch thành số. */

export type Duong = {
  ten: string;
  /** Lớp màu: "d1" | "d2" | "d3" — khai ở globals.css, lấy từ biến bộ nhận diện. */
  lop: string;
  diem: Diem[];
};

/** Đủ điều kiện vẽ: ÍT NHẤT MỘT chuỗi có từ hai điểm có số (luật 2). */
export function duVeDuong(ds: Duong[]): boolean {
  return ds.some((d) => d.diem.filter((p) => p.gt !== null && p.gt !== undefined).length >= 2);
}

/** Cắt một chuỗi thành các ĐOẠN LIỀN: mỗi đoạn là một dãy điểm liên tiếp CÓ SỐ.
 *
 *  Đây là chỗ luật 1 (rỗng khác không) sống trong hình này. Nối hai điểm hai bên một lỗ hổng là
 *  vẽ ra giá trị của tuần ở giữa — một con số không ai nhập và không ai kiểm được. */
export function doanLien(diem: Diem[]): { i: number; gt: number }[][] {
  const ra: { i: number; gt: number }[][] = [];
  let cur: { i: number; gt: number }[] = [];
  diem.forEach((p, i) => {
    if (p.gt === null || p.gt === undefined) { if (cur.length) { ra.push(cur); cur = []; } return; }
    cur.push({ i, gt: p.gt });
  });
  if (cur.length) ra.push(cur);
  return ra;
}

export function BieuDoDuong({ ten, phu, ds, nhan, dinh_dang = "tien", moc, chan, ai, cua, cua_ten,
                             ben_ten, doi_xung = false }: {
  ten: string; phu?: string; ds: Duong[]; nhan: string[]; dinh_dang?: DinhDang;
  /** TC-65 · Cửa đứng cạnh tên hình — xem chú thích ở `KhungBieuDo`. */
  ben_ten?: ReactNode;
  /** Vạch mốc nằm ngang trên CÙNG một trục (ngưỡng dự phòng chẳng hạn). */
  moc?: { gt: number; nhan: string } | null;
  chan?: ReactNode; ai?: string; cua?: string; cua_ten?: string;
  /** In lại mốc trục ở mép PHẢI. Cùng một mảng `moc`, nên là một thang in hai lần. */
  doi_xung?: boolean;
}) {
  if (!duVeDuong(ds)) {
    return <BieuDoRong ten={ten} phu={phu} nhan={nhan} ai={ai} cua={cua} cua_ten={cua_ten}
      vi_sao="Cần ít nhất hai kỳ có số thì mới vẽ được đường — một điểm đứng một mình không so với kỳ nào." />;
  }

  const giaTri = ds.flatMap((d) => d.diem.map((p) => p.gt)).filter((v): v is number => typeof v === "number");
  const canMoc = typeof moc?.gt === "number" ? [moc.gt] : [];
  const mocs = mocTruc(Math.min(...giaTri, ...canMoc, 0), Math.max(...giaTri, ...canMoc, 0));
  const day = mocs[0];
  const dinh = mocs[mocs.length - 1];
  const khoang = dinh - day || 1;
  /** Đổi một giá trị thành % tính từ ĐÁY khung. */
  const pct = (v: number) => ((v - day) / khoang) * 100;
  /** Vị trí ngang của điểm thứ i, tính bằng %. Một điểm duy nhất thì đặt giữa. */
  const n = nhan.length;
  const x = (i: number) => (n <= 1 ? 50 : (i / (n - 1)) * 100);

  return (
    <KhungBieuDo ten={ten} phu={phu} chan={chan} ben_ten={ben_ten}
      chuGiai={<ChuGiai ds={ds.map((d) => ({ ten: d.ten, lop: d.lop }))} />}>
      <div className="bd-duong-vung">
        {/* Cột mốc trục bên TRÁI. Mỗi nhãn đặt TUYỆT ĐỐI ở đúng chiều cao của vạch lưới nó
            nói về — không xếp đều bằng flex. Xếp đều chỉ trùng khi các mốc cách đều nhau, mà
            `mocTruc` có thể trả về mốc đầu lệch (khi có giá trị âm); lúc ấy nhãn và vạch lệch
            nhau, và người đọc tin nhãn. */}
        <div className="bd-duong-truc" aria-hidden="true">
          {mocs.map((m) => (
            <span key={m} className="bd-truc-nhan" style={{ bottom: `${pct(m)}%` }}>
              {gonSo(m, dinh_dang)}
            </span>
          ))}
        </div>

        <div className="bd-duong-khung">
          {/* Lưới ngang — một vạch cho mỗi mốc, kể cả vạch 0. */}
          {mocs.map((m) => (
            <div key={m} className="bd-luoi" style={{ bottom: `${pct(m)}%` }} />
          ))}
          {/* Vạch ngưỡng: CÙNG trục với ba đường, không phải trục thứ hai. */}
          {/* KHÔNG in nhãn ngay trên vạch: ngưỡng thường nằm sát đáy, đúng chỗ nhãn số của điểm
              đầu và điểm cuối các chuỗi đứng, và ba mẩu chữ chồng lên nhau ở góc trái. Tên và giá
              trị của vạch nói ở câu chân hình — cùng lối `BieuDoCot` đã dùng. */}
          {/* TC-60 · GIÁ TRỊ CỦA VẠCH NẰM Ở NHÃN RÊ CHUỘT, không ở một mẩu chữ trên hình.
              Câu chân hình đã bỏ theo chốt 17/9, nên nếu vạch cũng không mang số thì trên cả màn
              hình không còn chỗ nào nói ngưỡng dự phòng là bao nhiêu — mất một con số khác hẳn
              với gọn một câu chữ. */}
          {typeof moc?.gt === "number" && moc.gt >= day && moc.gt <= dinh && (
            <div className="bd-nguong" style={{ bottom: `${pct(moc.gt)}%` }}
              title={`${moc.nhan}: ${daySo(moc.gt, dinh_dang)}`} />
          )}

          {/* Các đường. SVG kéo giãn theo khung (preserveAspectRatio none) nên nét vẽ dùng
              vector-effect để bề dày không bị méo theo. */}
          <svg className="bd-duong-svg" viewBox="0 0 100 100" preserveAspectRatio="none"
               aria-hidden="true">
            {ds.map((d) => doanLien(d.diem).map((doan, k) => (
              doan.length < 2 ? null : (
                <polyline key={d.ten + "-" + k} className={"bd-net " + d.lop}
                  points={doan.map((p) => `${x(p.i)},${100 - pct(p.gt)}`).join(" ")}
                  vectorEffect="non-scaling-stroke" />
              )
            )))}
          </svg>

          {/* Chấm: div tuyệt đối chứ không phải hình trong SVG — SVG bị kéo giãn nên hình tròn
              trong đó sẽ thành bầu dục. */}
          {/* RÊ CHUỘT VÀO CHẤM LÀ HIỆN SỐ NGAY — Chủ tịch chốt 12/10/2026.
                "mỗi mốc dòng tiền có 1 chấm tròn là kèm theo 1 con số khi rê chuột vào sẽ hiện ra"

              Con số ĐÃ CÓ TỪ TRƯỚC, nhưng nằm trong `title` — mẹo của trình duyệt. Ba chỗ dở, và
              chỉ chỗ thứ ba mới là chỗ thật sự đáng sửa:
                · phải giữ chuột đứng im khoảng một giây mới hiện;
                · hiện ra một ô xám của hệ điều hành, không mang màu của chuỗi, không theo nền tối;
                · trên điện thoại thì KHÔNG BAO GIỜ hiện — tức là với người xem trên máy, con số
                  ấy coi như không tồn tại.

              Nay mỗi chấm mang một nhãn của chính màn hình, hiện tức thì. `title` GIỮ NGUYÊN, cố
              ý: nó là lối đọc của trình đọc màn hình và của người rê chuột theo thói quen cũ. Bỏ
              nó đi là đổi một chỗ dở lấy một chỗ mất.

              VÙNG BẮT CHUỘT RỘNG HƠN CHẤM: chấm 9px, vùng nhận 24px, dựng bằng `::before` trong
              CSS. Không có nó thì người dùng phải nhắm vào một chấm 9px — và bốn mươi chấm trên
              một hình thì nhắm trượt là chuyện thường.

              `tabIndex` để bàn phím tới được: Tab tới chấm thì nhãn hiện y như rê chuột. */}
          {ds.map((d) => d.diem.map((p, i) => (
            p.gt === null || p.gt === undefined ? null : (
              {/* GD-1 · 12/11/2026 — CHẤM ĐẦU và CHẤM CUỐI mang thêm một lớp để nhãn của chúng
                  neo vào trong khung thay vì căn giữa. Nhãn rộng ~200px; căn giữa chấm cuối thì
                  nửa nhãn thò ra khỏi mép phải và đẩy CẢ TRANG tràn ngang 16px. Chỉ hai chấm ấy
                  cần, vì khoảng cách giữa hai chấm giữa rộng hơn nửa nhãn. Lý do đầy đủ ở
                  `.bd-cham.dau` / `.bd-cham.cuoi` trong globals.css. */}
              <span key={d.ten + "-" + i}
                className={"bd-cham " + d.lop
                  + (i === 0 ? " dau" : i === d.diem.length - 1 ? " cuoi" : "")}
                style={{ left: `${x(i)}%`, bottom: `${pct(p.gt)}%` }}
                tabIndex={0}
                title={`${d.ten} · ${nhan[i]}: ${daySo(p.gt, dinh_dang)}`}>
                <span className="bd-cham-so" aria-hidden="true">
                  <b>{daySo(p.gt, dinh_dang)}</b>
                  <i>{d.ten} · {nhan[i]}</i>
                </span>
              </span>
            )
          )))}

          {/* NHÃN SỐ CÓ CHỌN LỌC: chỉ đầu và cuối mỗi chuỗi. Ghi số lên cả ba mươi chín điểm thì
              không đọc được điểm nào — và người đọc cần biết "bắt đầu từ đâu, kết thúc ở đâu",
              phần giữa là việc của hình. */}
          {ds.map((d) => {
            const co = d.diem.map((p, i) => ({ p, i })).filter((o) => o.p.gt !== null && o.p.gt !== undefined);
            if (!co.length) return null;
            const canhan = co.length === 1 ? [{ o: co[0], cuoi: false }]
              : [{ o: co[0], cuoi: false }, { o: co[co.length - 1], cuoi: true }];
            /* Nhãn đầu MỞ SANG PHẢI, nhãn cuối MỞ SANG TRÁI — không căn giữa điểm. Căn giữa thì
               nhãn của điểm đầu thò ra ngoài mép trái khung, và nhãn của điểm cuối đè lên cột mốc
               trục bên phải. Cả hai chỉ lộ ra khi dựng ảnh. */
            return canhan.map(({ o, cuoi }) => (
              <span key={d.ten + "-nhan-" + o.i}
                className={"bd-duong-nhan " + d.lop + (cuoi ? " cuoi" : "")}
                style={{ left: `${x(o.i)}%`, bottom: `${pct(o.p.gt as number)}%` }}>
                {gonSo(o.p.gt as number, dinh_dang)}
              </span>
            ));
          })}
        </div>

        {/* Cột mốc trục bên PHẢI — cùng mảng `mocs`, nên cùng một thang đo. */}
        {doi_xung && (
          <div className="bd-duong-truc bd-truc-phai" aria-hidden="true">
            {mocs.map((m) => (
              <span key={m} className="bd-truc-nhan" style={{ bottom: `${pct(m)}%` }}>
                {gonSo(m, dinh_dang)}
              </span>
            ))}
          </div>
        )}

        {/* Hàng nhãn trục ngang nằm TRONG cùng lưới, ở đúng cột của vùng vẽ — không phải một
            hàng riêng chạy hết bề ngang hình. Chạy hết bề ngang thì nhãn lệch sang trái đúng
            bằng bề rộng cột mốc trục, và mười ba nhãn đều lệch khỏi mười ba điểm của chúng. */}
        <div className="bd-duong-nhanx" style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}>
          {nhan.map((t, i) => <span key={t + i}>{t}</span>)}
        </div>
      </div>
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
    // TC-49 · bảy nhóm hạn vẫn hiện ĐỦ BẢY TÊN dù chưa có số. Người đọc thấy trước hình này sẽ
    // trả lời câu gì, và thấy luôn rằng nó có bảy nhóm chứ không phải năm — điều mà một đoạn chữ
    // "chưa có nguồn" không nói được.
    return <BieuDoRong ten={ten} phu={phu} ai={ai} cua={cua} cua_ten={cua_ten}
      ngang nhan={hang.map((h) => h.ten)}
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
