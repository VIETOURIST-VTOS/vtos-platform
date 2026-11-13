#!/usr/bin/env node
/* HÀNG RÀO · KHÔNG HỘP THOẠI TRÌNH DUYỆT TRÊN GIAO DIỆN VTOS.  TR-10 đợt 2, 13/11/2026.
 *
 * CHUYỆN CÓ THẬT ĐÃ DỰNG RA HÀNG RÀO NÀY. Ngày 13/11/2026 phòng Điều hành được giao ghép link
 * web cho 22 tour thiếu ảnh. Không ghép được tour nào: nút «Ghép link» mở `window.prompt`, và
 * trình duyệt trả thẳng «prompt() is not supported». Hộp thoại của trình duyệt KHOÁ CẢ TRANG —
 * không bấm qua được bằng thao tác tự động, và trên điện thoại thì dán một đường dẫn dài vào nổi.
 * Quét bằng cây cú pháp hôm ấy: 125 chỗ gọi trên 54 tệp. (Quét bằng `grep "window.prompt("` chỉ
 * ra 58 — vì rất nhiều chỗ viết `confirm(...)` không có chữ `window.`. Đó là lý do hàng rào này
 * đọc CÂY CÚ PHÁP chứ không đọc văn bản.)
 *
 * SÁU LUẬT. Luật 3 là luật quan trọng nhất và là lý do tệp này tồn tại.
 *
 *   1. Không `prompt()` / `confirm()` ở đâu trong `app/` và `components/`.
 *   2. `alert()` chỉ còn đúng ở chỗ đã ghi nợ bên dưới, đúng số lượng — thêm một lượt là đỏ.
 *   3. Thành phần nào lấy móc `useHoi()` thì MỌI nhánh `return` của nó có nút hoặc có xử lý sự
 *      kiện ĐỀU phải vẽ `{hop}`. Đây là chỗ sai không ai thấy: đặt `{hop}` nhầm thành phần hay
 *      nhầm nhánh thì lệnh chờ không bao giờ trả về, nút đứng im — mà BẢN DỰNG VẪN XANH.
 *   4. Tên lấy từ `useHoi()` không được trùng tên đã có trong tệp hay trong thành phần. Ngày
 *      13/11 ba chỗ trùng thật: `DocChungTu` đã có hàm `xacNhan` (xác nhận chứng từ),
 *      `ChonDonVi` đã có `hop`, `AlbumNhaHang` đã có `nhap`, và `DeXuatChiTaiCho` có
 *      `function hop(x, tab)` khai Ở MỨC TỆP — cái thứ tư này `tsc` bắt được, mắt em thì không.
 *   5. Tệp nào dùng `useHoi` thì phải nhập nó từ `@/components/HopHoi`.
 *   6. `HopHoi.tsx` phải còn đó và còn trả ra cả ba thứ `xacNhan`, `nhap`, `hop`.
 *
 * Chạy: npm run hang-rao   (việc `web` trong ci.yml gọi nó trước `npm run build`)
 */
const ts = require("typescript"), fs = require("fs"), path = require("path");

/* NỢ ĐÃ GHI — `alert()` còn sót, có lý do, và bị chốt số.
 * Hai lượt này nằm trong `taiPdf()`, một hàm NGOÀI mọi thành phần, và chỉ báo «tải PDF thất bại».
 * Kéo `useHoi()` vào đó là phải luồn một hàm gọi lại qua một tệp dùng chung cho CẢ BA cổng khách
 * (khách sạn, nhà hàng, tour) — giá cao hơn cái được, nên để lại và ghi nợ. Số 2 là bản chốt:
 * đổi số này thì người đổi phải nhìn lại chỗ ấy. */
const ALERT_CON_NO = { "components/cong/KhachSanVtd.tsx": 2 };

const GOC = __dirname + "/..";
const BO_QUA_TEP = new Set(["HopHoi.tsx"]);
const KHOI = new Set(["div", "section", "main", "form", "fieldset", "article", "aside", "nav", "header", "footer", "dialog"]);
const laHam = (n) => ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n);

function quet(p, ra = []) {
  for (const e of fs.readdirSync(p, { withFileTypes: true })) {
    const q = path.join(p, e.name);
    if (e.isDirectory()) { if (e.name !== "node_modules" && e.name !== ".next") quet(q, ra); }
    else if (/\.tsx?$/.test(e.name)) ra.push(q);
  }
  return ra;
}
function tenHam(n) {
  const p = n.parent;
  if (ts.isFunctionDeclaration(n) && n.name) return n.name.text;
  if (p && ts.isVariableDeclaration(p) && ts.isIdentifier(p.name)) return p.name.text;
  if (p && ts.isPropertyAssignment(p) && ts.isIdentifier(p.name)) return p.name.text;
  return null;
}

const do_ = [];
const tuongDoi = (q) => path.relative(GOC, q).split(path.sep).join("/");
const demAlert = {};

for (const q of quet(path.join(GOC, "app")).concat(quet(path.join(GOC, "components")))) {
  const rel = tuongDoi(q);
  const src = fs.readFileSync(q, "utf8");
  const sf = ts.createSourceFile(q, src, ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);
  const dong = (n) => sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1;
  const boQua = BO_QUA_TEP.has(path.basename(q));

  // ---- luật 1 & 2 ----
  (function w(n) {
    if (ts.isCallExpression(n)) {
      const t = n.expression.getText(sf);
      if (!boQua && /^(window\.)?(prompt|confirm)$/.test(t))
        do_.push(`L1  ${rel}:${dong(n)}  còn \`${t}(\` — hộp thoại trình duyệt khoá cả trang. Dùng \`await nhap()\` / \`await xacNhan()\` của \`useHoi()\`.`);
      if (/^(window\.)?alert$/.test(t)) demAlert[rel] = (demAlert[rel] || 0) + 1;
    }
    ts.forEachChild(n, w);
  })(sf);

  // ---- tên ở mức tệp (cho luật 4) ----
  const tenTep = new Set();
  for (const s of sf.statements) {
    if (ts.isImportDeclaration(s) && s.importClause) {
      const c = s.importClause;
      if (c.name) tenTep.add(c.name.text);
      if (c.namedBindings) {
        if (ts.isNamespaceImport(c.namedBindings)) tenTep.add(c.namedBindings.name.text);
        else for (const e of c.namedBindings.elements) tenTep.add(e.name.text);
      }
    }
    if ((ts.isFunctionDeclaration(s) || ts.isClassDeclaration(s)) && s.name) tenTep.add(s.name.text);
    if (ts.isVariableStatement(s)) for (const d of s.declarationList.declarations) {
      if (ts.isIdentifier(d.name)) tenTep.add(d.name.text);
      if (ts.isObjectBindingPattern(d.name)) for (const b of d.name.elements) if (ts.isIdentifier(b.name)) tenTep.add(b.name.text);
    }
  }

  // ---- tìm mọi lượt lấy móc useHoi() ----
  const mocs = [];
  (function w(n) {
    if (ts.isVariableDeclaration(n) && n.initializer && ts.isCallExpression(n.initializer)
        && n.initializer.expression.getText(sf) === "useHoi") {
      if (!ts.isObjectBindingPattern(n.name)) {
        do_.push(`L5  ${rel}:${dong(n)}  \`useHoi()\` phải lấy ra theo tên: \`const { xacNhan, nhap, hop } = useHoi()\`.`);
      } else {
        const lay = {};               // tên gốc -> tên dùng
        for (const b of n.name.elements) {
          const goc = (b.propertyName && ts.isIdentifier(b.propertyName) ? b.propertyName.text : (ts.isIdentifier(b.name) ? b.name.text : null));
          if (goc && ts.isIdentifier(b.name)) lay[goc] = b.name.text;
        }
        // thành phần bọc ngoài
        let x = n.parent, tp = null;
        while (x) { if (laHam(x)) { const nm = tenHam(x); if (nm && /^[A-Z]/.test(nm)) { tp = { n: x, ten: nm }; break; } } x = x.parent; }
        mocs.push({ n, lay, tp, dongMoc: dong(n) });
      }
    }
    ts.forEachChild(n, w);
  })(sf);

  if (mocs.length && !/from "@\/components\/HopHoi"/.test(src))
    do_.push(`L5  ${rel}  dùng \`useHoi\` mà không nhập từ "@/components/HopHoi".`);

  for (const m of mocs) {
    if (!m.tp) { do_.push(`L3  ${rel}:${m.dongMoc}  \`useHoi()\` không nằm trong thành phần nào.`); continue; }
    const than = m.tp.n.body;
    if (!than || !ts.isBlock(than)) { do_.push(`L3  ${rel}:${m.dongMoc}  thành phần ${m.tp.ten} không có thân {}.`); continue; }

    // ---- luật 4: va chạm tên ----
    const daCo = new Set(tenTep);
    for (const pr of m.tp.n.parameters || []) {
      const t = pr.name;
      if (ts.isIdentifier(t)) daCo.add(t.text);
      if (ts.isObjectBindingPattern(t)) for (const b of t.elements) if (ts.isIdentifier(b.name)) daCo.add(b.name.text);
    }
    (function w(x) {
      if (x !== than && laHam(x)) return;
      if (ts.isVariableDeclaration(x) && x !== m.n) {
        const t = x.name;
        if (ts.isIdentifier(t)) daCo.add(t.text);
        if (ts.isObjectBindingPattern(t)) for (const b of t.elements) if (ts.isIdentifier(b.name)) daCo.add(b.name.text);
      }
      if (ts.isFunctionDeclaration(x) && x.name) daCo.add(x.name.text);
      ts.forEachChild(x, w);
    })(than);
    for (const [goc, dung] of Object.entries(m.lay))
      if (daCo.has(dung))
        do_.push(`L4  ${rel}:${m.dongMoc}  tên \`${dung}\` (lấy từ \`${goc}\`) ĐÃ CÓ trong ${m.tp.ten} hoặc trong tệp — móc sẽ CHE cái cũ. Đặt tên khác: \`${goc}: ${goc}Hoi\`.`);

    // ---- luật 3: {hop} phải có ở mọi nhánh return có nút ----
    const tenHop = m.lay["hop"];
    if (!tenHop) continue;   // không lấy `hop` thì không có gì vẽ — luật 6 lo phần API
    const rets = [];
    (function w(x) {
      if (x !== than && laHam(x)) return;
      if (ts.isReturnStatement(x) && x.expression) {
        const k = ts.isParenthesizedExpression(x.expression) ? x.expression.expression : x.expression;
        if (ts.isJsxElement(k) || ts.isJsxFragment(k) || ts.isJsxSelfClosingElement(k)) rets.push(k);
      }
      ts.forEachChild(x, w);
    })(than);
    for (const k of rets) {
      const txt = k.getText(sf);
      if (!/<button|on[A-Z][A-Za-z]*=/.test(txt)) continue;          // nhánh không bấm được thì không cần
      if (new RegExp(`\\{\\s*${tenHop}\\s*\\}`).test(txt)) continue;  // có rồi
      const the = ts.isJsxFragment(k) ? "<>" : (ts.isJsxElement(k) ? k.openingElement.tagName.getText(sf) : k.tagName.getText(sf));
      do_.push(`L3  ${rel}:${dong(k)}  ${m.tp.ten} có nhánh return <${the}> CÓ NÚT mà THIẾU {${tenHop}} — nút sẽ đứng im và bản dựng vẫn xanh.`
             + (KHOI.has(the) || the === "<>" ? ` Nhét \`{${tenHop}}\` ngay sau thẻ mở.` : ` <${the}> không chứa được <div>, nên bọc ngoài: \`<>{${tenHop}}…</>\`.`));
    }
  }
}

// ---- luật 2: chốt số alert ----
for (const [rel, n] of Object.entries(demAlert)) {
  const cho = ALERT_CON_NO[rel];
  if (cho === undefined) do_.push(`L2  ${rel}  có ${n} lượt \`alert()\` MỚI. \`alert()\` khoá cả trang y như \`confirm()\`. Dùng hộp hỏi trên trang, hoặc dòng thông báo (toast).`);
  else if (n !== cho) do_.push(`L2  ${rel}  có ${n} lượt \`alert()\`, nợ đã ghi là ${cho}. Nếu đã dọn thì sửa \`ALERT_CON_NO\` trong tệp này; nếu vừa thêm thì đừng thêm.`);
}
for (const [rel, cho] of Object.entries(ALERT_CON_NO))
  if (!(rel in demAlert)) do_.push(`L2  ${rel}  nợ ghi ${cho} lượt \`alert()\` mà không còn lượt nào — dọn xong rồi thì bỏ dòng ấy khỏi \`ALERT_CON_NO\`.`);

// ---- luật 6: HopHoi.tsx còn nguyên ----
const qHop = path.join(GOC, "components", "HopHoi.tsx");
if (!fs.existsSync(qHop)) do_.push(`L6  components/HopHoi.tsx không còn — mọi màn đang dựa vào nó.`);
else {
  const s = fs.readFileSync(qHop, "utf8");
  for (const t of ["xacNhan", "nhap", "hop"])
    if (!new RegExp(`return\\s*\\{[^}]*\\b${t}\\b`).test(s)) do_.push(`L6  components/HopHoi.tsx không còn trả ra \`${t}\`.`);
}

if (do_.length) {
  console.error("HÀNG RÀO HỘP THOẠI — ĐỎ, " + do_.length + " chỗ:\n");
  do_.forEach((x) => console.error("  " + x));
  console.error("\nVì sao có hàng rào này: xem phần đầu tệp web/hang-rao/khong-hop-thoai-trinh-duyet.js");
  process.exit(1);
}
console.log("HÀNG RÀO HỘP THOẠI — XANH. Không còn prompt()/confirm() trên giao diện, và mọi {hop} nằm đúng nhánh.");
