/* ĐÃ CHẠY MỘT LẦN RỒI — 13/11/2026, vòng TR-10. ĐỪNG CHẠY LẠI KHI CHƯA ĐỌC HẾT PHẦN DƯỚI.
 *
 * Tệp này giữ lại làm HỒ SƠ: 125 chỗ gọi `prompt()`/`confirm()` trên 54 tệp đã được đổi bằng nó,
 * không phải bằng tay. Giữ vì ba lẽ: (a) để đọc lại được CÁCH đổi, không chỉ KẾT QUẢ; (b) nếu
 * `web/hang-rao/khong-hop-thoai-trinh-duyet.js` có đỏ vì ai thêm một hộp thoại mới, tệp này chỉ
 * ra cách sửa đúng; (c) nó mang bốn cái bẫy đã đo được, viết thành mã chứ không thành lời khuyên.
 *
 * CHẠY LẠI THÌ NHỚ: mặc định nó CHỈ BÁO. Phải thêm `--ghi` mới ghi. Và sau khi ghi thì BẮT BUỘC
 * chạy `npx tsc --noEmit` — lần 13/11 chính `tsc` bắt được cái bẫy thứ tư (một `function hop()`
 * khai ở MỨC TỆP bị móc che), thứ mà mắt người đọc không thấy và bản dựng vẫn xanh.
 */
/* TR-10 đợt 2 · Bộ đổi `prompt()` / `confirm()` sang hộp hỏi trên trang.
 *
 * VÌ SAO LÀ MÁY CHỨ KHÔNG PHẢI TAY: 125 chỗ gọi trên 54 tệp. Sửa tay 125 lần là 125 cơ hội sai,
 * và cái sai nguy hiểm nhất (đặt `{hop}` nhầm thành phần) thì bản dựng vẫn xanh.
 *
 * VÌ SAO AN TOÀN: bộ này chỉ CẮT DÁN TEXT theo vị trí cây cú pháp cho ra, nên bản khác (diff) nhỏ
 * nhất có thể và không định dạng lại tệp của làn khác. Và nó TỪ CHỐI mọi chỗ mà thêm `async` sẽ
 * làm hỏng: hàm vẽ ra JSX (thành async là trả Promise chứ không trả JSX), hàm đưa cho useEffect,
 * hàm đưa cho .map/.filter/... Những chỗ ấy nó in ra để người sửa tay.
 *
 * Chạy:  node doi-hop-thoai.js            -> chỉ BÁO, không ghi
 *        node doi-hop-thoai.js --ghi      -> ghi thật
 */
const ts = require("typescript"), fs = require("fs"), path = require("path");

const GHI = process.argv.includes("--ghi");
const GOC = process.cwd();
const BO_QUA = new Set(["HopHoi.tsx"]);
// Hàm đưa cho những chỗ này thì KHÔNG được thành async.
const CAM_ASYNC = new Set(["useMemo", "useEffect", "useLayoutEffect",
  "map", "filter", "sort", "find", "findIndex", "some", "every", "reduce", "flatMap"]);

function quetTep(p, ra = []) {
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    const q = path.join(p, e.name);
    if (e.isDirectory()) { if (e.name !== "node_modules" && e.name !== ".next") quetTep(q, ra); }
    else if (/\.tsx$/.test(e.name) && !BO_QUA.has(e.name)) ra.push(q);
  }
  return ra;
}

const laHam = (n) => ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n);

function tenHam(n) {
  const p = n.parent;
  if (ts.isFunctionDeclaration(n) && n.name) return n.name.text;
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && ts.isPropertyAssignment(p) && ts.isIdentifier(p.name)) return p.name.text;
  return null;
}

/** Hàm này có trả ra JSX không? (chỉ xét thân của chính nó, không vào hàm lồng) */
function traJSX(n, sf) {
  let co = false;
  const than = n.body;
  if (!than) return false;
  if (!ts.isBlock(than)) {
    const k = ts.isParenthesizedExpression(than) ? than.expression : than;
    return ts.isJsxElement(k) || ts.isJsxFragment(k) || ts.isJsxSelfClosingElement(k);
  }
  (function di(x) {
    if (co) return;
    if (x !== than && laHam(x)) return;
    if (ts.isReturnStatement(x) && x.expression) {
      const k = ts.isParenthesizedExpression(x.expression) ? x.expression.expression : x.expression;
      if (ts.isJsxElement(k) || ts.isJsxFragment(k) || ts.isJsxSelfClosingElement(k)) co = true;
    }
    ts.forEachChild(x, di);
  })(than);
  return co;
}

/** Hàm này được đưa làm đối số cho ai? (useEffect, .map, ...) */
function duocDuaCho(n, sf) {
  const p = n.parent;
  if (p && ts.isCallExpression(p) && p.arguments.includes(n)) {
    const t = p.expression;
    if (ts.isIdentifier(t)) return t.text;
    if (ts.isPropertyAccessExpression(t)) return t.name.text;
  }
  return null;
}

const bcTuChoi = [], bcLam = [];
let tongDoi = 0, tongAsync = 0, tongTep = 0;

for (const q of quetTep("app").concat(quetTep("components"))) {
  const src = fs.readFileSync(q, "utf8");
  if (!/\b(window\.)?(prompt|confirm)\s*\(/.test(src)) continue;
  const sf = ts.createSourceFile(q, src, ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);
  const dong = (p) => sf.getLineAndCharacterOfPosition(p).line + 1;

  const goi = [];
  (function di(n) {
    if (ts.isCallExpression(n)) {
      const t = n.expression.getText(sf);
      if (/^(window\.)?(prompt|confirm)$/.test(t)) goi.push({ n, loai: /prompt/.test(t) ? "nhap" : "xacNhan" });
    }
    ts.forEachChild(n, di);
  })(sf);
  if (!goi.length) continue;

  const cat = [];           // {tu, den, text}
  const themAsync = new Set();
  const thanhPhanCan = new Set();   // thành phần cần useHoi()
  let tepTuChoi = 0;

  /* VA CHẠM TÊN — bẫy đi lọt được. Ví dụ thật: `app/doc-chung-tu/page.tsx` ĐÃ CÓ một hàm tên
   * `xacNhan` (xác nhận chứng từ). Móc `const { xacNhan } = useHoi()` đặt vào đó là CHE hàm cũ,
   * nên mọi lượt gọi `xacNhan(...)` cũ lặng lẽ chạy sang hộp hỏi. `ChonDonVi` đã có `hop`,
   * `AlbumNhaHang` đã có `nhap`. Nên tên móc phải tính RIÊNG cho từng thành phần. */
  /* Tên ở MỨC TỆP cũng che được: `components/doixe/DeXuatChiTaiCho.tsx` có
   * `function hop(x, tab)` khai ở dòng 169 — NGOÀI thành phần. Lần ghi đầu em chỉ soát trong
   * thân thành phần nên móc `hop` che hàm ấy, và `tsc` báo 6 lỗi "Element has no call signatures".
   * Bắt được nhờ chạy tsc, không nhờ mắt. */
  const tenMucTep = new Set();
  for (const s of sf.statements) {
    if (ts.isImportDeclaration(s) && s.importClause) {
      const c = s.importClause;
      if (c.name) tenMucTep.add(c.name.text);
      if (c.namedBindings) {
        if (ts.isNamespaceImport(c.namedBindings)) tenMucTep.add(c.namedBindings.name.text);
        else for (const e of c.namedBindings.elements) tenMucTep.add(e.name.text);
      }
    }
    if (ts.isFunctionDeclaration(s) && s.name) tenMucTep.add(s.name.text);
    if (ts.isClassDeclaration(s) && s.name) tenMucTep.add(s.name.text);
    if (ts.isVariableStatement(s)) for (const d of s.declarationList.declarations) {
      if (ts.isIdentifier(d.name)) tenMucTep.add(d.name.text);
      if (ts.isObjectBindingPattern(d.name)) for (const b of d.name.elements) if (ts.isIdentifier(b.name)) tenMucTep.add(b.name.text);
    }
  }

  const tenDaCo = (tp) => {
    const co = new Set(tenMucTep);
    for (const pr of tp.parameters || []) {
      const t = pr.name;
      if (ts.isIdentifier(t)) co.add(t.text);
      if (ts.isObjectBindingPattern(t)) for (const b of t.elements) if (ts.isIdentifier(b.name)) co.add(b.name.text);
    }
    if (tp.body && ts.isBlock(tp.body)) (function w(x) {
      if (x !== tp.body && laHam(x)) return;
      if (ts.isVariableDeclaration(x)) {
        const t = x.name;
        if (ts.isIdentifier(t)) co.add(t.text);
        if (ts.isObjectBindingPattern(t)) for (const b of t.elements) if (ts.isIdentifier(b.name)) co.add(b.name.text);
      }
      if (ts.isFunctionDeclaration(x) && x.name) co.add(x.name.text);
      ts.forEachChild(x, w);
    })(tp.body);
    return co;
  };
  const tenMoc = new Map();   // nút thành phần -> {xacNhan, nhap, hop}
  const layTen = (tp) => {
    if (tenMoc.has(tp)) return tenMoc.get(tp);
    const co = tenDaCo(tp);
    const dat = (g) => { let t = g; let i = 0; while (co.has(t)) { i++; t = g + "Hoi" + (i > 1 ? i : ""); } return t; };
    const m = { xacNhan: dat("xacNhan"), nhap: dat("nhap"), hop: dat("hop") };
    tenMoc.set(tp, m);
    return m;
  };

  for (const g of goi) {
    // chuỗi hàm bọc, từ trong ra ngoài
    const chuoi = [];
    let x = g.n.parent, tp = null;
    while (x) {
      if (laHam(x)) {
        const nm = tenHam(x);
        if (nm && /^[A-Z]/.test(nm)) { tp = { n: x, ten: nm }; break; }
        chuoi.push(x);
      }
      x = x.parent;
    }
    if (!tp) {
      bcTuChoi.push(`${q}:${dong(g.n.getStart(sf))}  KHÔNG tìm được thành phần bọc ngoài`);
      tepTuChoi++; continue;
    }
    // CHỈ HÀM TRONG CÙNG cần async — `await` không đòi hàm bọc ngoài nó phải async.
    // (Lần chạy thử đầu em thêm async cho cả chuỗi, nên 46 chỗ bị từ chối oan vì cái `.map()`
    //  vẽ bảng ở ngoài. Hàm trong cùng là cái `onClick` — thành async là đúng và đủ.)
    let chan = null;
    const trongCung = chuoi[0];
    if (!trongCung) chan = `chỗ gọi nằm thẳng trong thân thành phần ${tp.ten} (gọi lúc vẽ)`;
    else if (traJSX(trongCung, sf)) chan = `hàm trong cùng trả ra JSX (thành async là trả Promise chứ không trả JSX)`;
    else {
      const cho = duocDuaCho(trongCung, sf);
      if (cho && CAM_ASYNC.has(cho)) chan = `hàm trong cùng được đưa cho \`${cho}\``;
    }
    if (chan) {
      bcTuChoi.push(`${q}:${dong(g.n.getStart(sf))}  TỪ CHỐI — ${chan}`);
      tepTuChoi++; continue;
    }
    // ăn: đổi tên hàm gọi (dùng tên móc RIÊNG của thành phần ấy)
    const ex = g.n.expression;
    cat.push({ tu: ex.getStart(sf), den: ex.getEnd(), text: `await ${layTen(tp.n)[g.loai]}` });
    const daAsync = (trongCung.modifiers || []).some(m => m.kind === ts.SyntaxKind.AsyncKeyword);
    if (!daAsync) themAsync.add(trongCung);
    thanhPhanCan.add(tp.n);
    tongDoi++;
  }

  if (!cat.length) { if (tepTuChoi) bcLam.push(`${q}: 0 đổi, ${tepTuChoi} từ chối`); continue; }

  for (const h of themAsync) { cat.push({ tu: h.getStart(sf), den: h.getStart(sf), text: "async " }); tongAsync++; }

  // --- useHoi() cho từng thành phần cần, và {hop} vào các nhánh return ---
  const batHop = [];
  for (const tpn of thanhPhanCan) {
    const nm = tenHam(tpn) || "?";
    const than = tpn.body;
    if (!than || !ts.isBlock(than)) { bcTuChoi.push(`${q}  TỪ CHỐI — thành phần ${nm} không có thân {}`); continue; }
    // dòng móc: ngay sau dấu { mở thân
    const T = layTen(tpn);
    const doi = (goc, moi) => (goc === moi ? goc : `${goc}: ${moi}`);
    cat.push({ tu: than.getStart(sf) + 1, den: than.getStart(sf) + 1,
      text: `\n  const { ${doi("xacNhan", T.xacNhan)}, ${doi("nhap", T.nhap)}, ${doi("hop", T.hop)} } = useHoi();` });
    if (T.hop !== "hop" || T.nhap !== "nhap" || T.xacNhan !== "xacNhan")
      bcLam.push(`    ^ ${nm}: ĐỔI TÊN MÓC vì trùng tên có sẵn -> ${T.xacNhan}/${T.nhap}/${T.hop}`);
    // các nhánh return JSX của CHÍNH thành phần này
    const rets = [];
    (function di(x) {
      if (x !== than && laHam(x)) return;
      if (ts.isReturnStatement(x) && x.expression) {
        const k = ts.isParenthesizedExpression(x.expression) ? x.expression.expression : x.expression;
        if (ts.isJsxElement(k) || ts.isJsxFragment(k)) rets.push(k);
        else if (ts.isJsxSelfClosingElement(k)) rets.push(null); // tự đóng: không nhét được
      }
      ts.forEachChild(x, di);
    })(than);
    for (const k of rets) {
      if (!k) { bcTuChoi.push(`${q}  CHÚ Ý — ${nm} có nhánh return thẻ tự đóng, không nhét {hop} được`); continue; }
      // chỉ nhét vào nhánh CÓ nút / có xử lý sự kiện — nhánh không có thì không cần
      const txt = k.getText(sf);
      if (!/<button|on[A-Z][A-Za-z]*=/.test(txt)) continue;
      // `hop` vẽ ra một <div>. Nhét <div> vào trong <button>, <p>, <span>, <td>… là LỒNG THẺ SAI
      // (React cảnh báo, và HTML không cho). Nên chỉ nhét VÀO TRONG khi thẻ gốc là thẻ khối;
      // còn lại thì BỌC NGOÀI bằng mảnh <>…</> — mảnh không sinh thẻ DOM nào, và `hop` là null
      // khi chưa hỏi gì, nên khi không có hộp thì DOM y như cũ.
      const KHOI = new Set(["div", "section", "main", "form", "fieldset", "article", "aside", "nav", "header", "footer", "dialog"]);
      const laManh = ts.isJsxFragment(k);
      const the = laManh ? "<>" : k.openingElement.tagName.getText(sf);
      if (laManh || KHOI.has(the)) {
        const mo = laManh ? k.openingFragment : k.openingElement;
        cat.push({ tu: mo.getEnd(), den: mo.getEnd(), text: `{${T.hop}}` });
        batHop.push(`${nm}@${dong(k.getStart(sf))} trong <${the}>`);
      } else {
        cat.push({ tu: k.getStart(sf), den: k.getStart(sf), text: `<>{${T.hop}}` });
        cat.push({ tu: k.getEnd(), den: k.getEnd(), text: `</>` });
        batHop.push(`${nm}@${dong(k.getStart(sf))} BỌC NGOÀI <${the}>`);
      }
    }
  }

  // --- import ---
  if (!/from "@\/components\/HopHoi"/.test(src)) {
    let cuoi = 0;
    sf.statements.forEach(s => { if (ts.isImportDeclaration(s)) cuoi = s.getEnd(); });
    cat.push({ tu: cuoi, den: cuoi, text: `\nimport { useHoi } from "@/components/HopHoi";` });
  }

  // áp từ phải sang trái
  cat.sort((a, b) => b.tu - a.tu || b.den - a.den);
  let out = src;
  for (const c of cat) out = out.slice(0, c.tu) + c.text + out.slice(c.den);

  if (GHI) fs.writeFileSync(q, out, "utf8");
  tongTep++;
  bcLam.push(`${q}: ${cat.filter(c => c.text.startsWith("await")).length} đổi, {hop} vào [${batHop.join(" ")}]${tepTuChoi ? `, ${tepTuChoi} TỪ CHỐI` : ""}`);
}

console.log("===== ĐÃ LÀM =====");
bcLam.forEach(x => console.log("  " + x));
console.log("\n===== TỪ CHỐI / CHÚ Ý (phải sửa tay) =====");
if (!bcTuChoi.length) console.log("  (không có)");
bcTuChoi.forEach(x => console.log("  " + x));
console.log(`\nTỔNG: ${tongDoi} chỗ đổi, ${tongAsync} hàm thêm async, ${tongTep} tệp, ${bcTuChoi.length} chỗ từ chối/chú ý`);
console.log(GHI ? "ĐÃ GHI THẬT." : "CHƯA GHI (chạy thử).");
