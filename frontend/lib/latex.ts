/**
 * File: frontend/lib/latex.ts
 * Mô tả: Module tiền xử lý chuỗi Markdown trước khi đưa vào ReactMarkdown.
 * Chuẩn hóa triệt để các công thức toán LaTeX từ Gemini/LLM theo Task T8.5 (US 8.1 - AC 8.1.4):
 * - Chuyển \\[ ... \\] và \[ ... \] thành block math $$ ... $$
 * - Chuyển \\( ... \\) và \( ... \) thành inline math $ ... $
 * - Đảm bảo $$ display luôn có khoảng ngắt dòng \n\n hợp lệ để remark-math parse chuẩn
 * - Chuyển $$ giữa dòng văn bản (inline) thành $ ... $
 * - Xóa khoảng trắng thừa sát viền dấu $ ($ x $ -> $x$)
 * - Đảm bảo có khoảng trắng phân cách chữ tiếng Việt và công thức ($12$ không bị dính chữ thành "tử số12chia")
 * - Bảo vệ 100% các khối code (``` và `) không bị thay thế nhầm
 */

const VIETNAMESE_ACCENTS =
  "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ" +
  "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ";

const MATH_COMMANDS = new Set([
  "frac", "sqrt", "left", "right", "log", "ln", "sin", "cos", "tan", "cot",
  "le", "ge", "ne", "pm", "pi", "times", "div", "Delta", "circ", "square",
  "approx", "cdot", "cdots", "ldots"
]);

// Chỉ gồm từ tiếng Việt >= 2 âm tiết hoặc từ không thể là biến toán học.
// Loại bỏ: "a", "b", "c", "d", "co", "la", "va", "ba", "an", "vi", "ma", "ra", "di", "ha"
// vì những từ này rất hay là biến toán học (a, b, c...) → gây false positive khi detect "natural language"
const COMMON_WORDS = new Set([
  "sao", "cho", "em", "neu", "hay", "hoac",
  "khi", "nao", "vao", "trong", "ngoai", "tren", "duoi",
  "giup", "tinh", "bai", "toan", "khong", "biet", "nay", "lam", "hoi", "rut", "gon",
  "thay", "oi", "giai", "thi", "de", "voi", "mot", "hai", "bon", "nam",
  "dung", "sai", "ket", "qua", "dap", "buoc", "nhe"
]);

export function isTextToken(token: string): boolean {
  if (/[\\^_{}√±×÷≤≥≠π=<>]/.test(token)) {
    return false;
  }
  const clean = token.replace(/^[^\w\u00C0-\u1EF9]+|[^\w\u00C0-\u1EF9]+$/g, "");
  if (!clean) return false;

  for (let i = 0; i < clean.length; i++) {
    if (VIETNAMESE_ACCENTS.includes(clean[i])) return true;
  }
  const cl = clean.toLowerCase();
  if (COMMON_WORDS.has(cl)) return true;
  if (/^[a-zA-Z]{2,}$/.test(clean) && !MATH_COMMANDS.has(cl)) {
    return true;
  }
  return false;
}

export function hasNaturalLanguage(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    if (VIETNAMESE_ACCENTS.includes(text[i])) return true;
  }
  const words = text.match(/[a-zA-Z]+/g) || [];
  for (const w of words) {
    const wl = w.toLowerCase();
    if (COMMON_WORDS.has(wl)) return true;
    if (wl.length >= 3 && !MATH_COMMANDS.has(wl)) return true;
  }
  return false;
}

/**
 * Chuẩn hóa chuỗi LaTeX từ MathLive trước khi gửi vào Chat/Markdown.
 * Tách biệt rõ ràng giữa câu chữ tự nhiên và công thức toán học,
 * chỉ bọc $...$ cho các phân đoạn toán thực sự, tránh lỗi dính chữ (mất space) và font nghiêng (math mode).
 */
export function formatLatexForChat(latex: string): string {
  if (!latex) return "";

  // Xử lý multiline: mỗi dòng được xử lý riêng lẻ, giữ nguyên ký tự xuống dòng
  if (latex.includes("\n")) {
    return latex
      .split("\n")
      .map((line) => formatLatexForChat(line))
      .join("\n");
  }

  let text = latex.trim();
  if (!text) return "";

  // 1. Chuẩn hóa Unicode ký tự toán học (như 𝑥, 𝑦, 𝐴, 𝟐 copy từ web/Word) về ký tự chuẩn
  text = text.normalize("NFKC");

  // 2. Gỡ bỏ các lệnh bọc font chữ LaTeX thừa do paste từ MathLive hoặc trang web khác (VD: \text{...}, \mathrm{...}, \textbf{...}, \textit{...})
  // Giúp toàn bộ chữ đàm thoại / đề bài trở về dạng văn bản thuần túy, render đúng 100% font Geist Sans chuẩn của website
  // Hỗ trợ nested braces 1 cấp: \text{Tìm x biết \frac{1}{2}} → "Tìm x biết \frac{1}{2}"
  const TEXT_WRAP_RE = /\\(?:text|mathrm|textrm|textsf|textbf|textit|mathbf|mathit)\s*\{((?:[^{}]|\{[^{}]*\})*)\}/g;
  while (TEXT_WRAP_RE.test(text)) {
    TEXT_WRAP_RE.lastIndex = 0; // reset sau .test()
    text = text.replace(TEXT_WRAP_RE, "$1");
  }

  // 3. Gỡ bỏ dấu $ bao quanh toàn bộ nếu có từ trước
  if (text.startsWith("$") && text.endsWith("$") && text.length > 2) {
    text = text.substring(1, text.length - 1).trim();
  }

  // 2. Chuyển các ký tự thoát dấu khoảng trắng, placeholder & dấu câu của MathLive về văn bản tự nhiên
  text = text
    .replace(/\\placeholder\{[^}]*\}/g, "\\square")
    .replace(/\\operatorname\{(th|ch|sh|tg|cotg|cth)\}/gi, "$1")
    .replace(/\\ /g, " ")
    .replace(/\\,/g, ",")
    .replace(/\\;/g, ";")
    .replace(/\\:/g, ":")
    .replace(/\\!/g, "")
    .replace(/\\+$/g, "")
    .trim();

  // 3. Chuyển x đơn lẻ giữa các biểu thức số/lũy thừa thành \times (VD: 2^3 x 2^4 -> 2^3 \times 2^4)
  text = text.replace(/([0-9\}\)])\s+x\s+([0-9\\\(])/g, "$1 \\times $2");

  // 4. Tách từ chữ dính vào lệnh LaTeX (VD: "toán\frac{1}{2}" -> "toán \frac{1}{2}")
  text = text.replace(/([a-zA-Z\u00C0-\u1EF9])\\([a-zA-Z])/g, "$1 \\$2");

  // 5. Tách chữ dính sau dấu đóng ngoặc hoặc số nếu từ đó là từ tự nhiên (VD: "2^{4}này" -> "2^{4} này", "\frac{1}{2}ạ" -> "\frac{1}{2} ạ")
  text = text.replace(/([\}\)\]0-9])([a-zA-Z\u00C0-\u1EF9]+)/g, (match, prefix, word) => {
    if (isTextToken(word) || hasNaturalLanguage(word)) {
      return `${prefix} ${word}`;
    }
    return match;
  });

  // 6. Khắc phục hiện tượng tách chữ do bộ gõ tiếng Việt (VD: "th ầy" -> "thầy", "b ằng mấy" -> "bằng mấy", "ng ười" -> "người")
  const vietSeparatedRegex = /(^|\s)([b-df-hj-np-tv-zB-DF-HJ-NP-TV-ZđĐ]+)\s+([àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zA-Z\u00C0-\u1EF9]*)/gi;
  let prevText;
  do {
    prevText = text;
    text = text.replace(vietSeparatedRegex, "$1$2$3");
  } while (text !== prevText);

  // 7. Nếu không có ký hiệu toán hay backslash nào -> văn bản thuần túy
  const hasMathSyntax = /[\\^_{}√±×÷≤≥≠π]/.test(text);
  if (!hasMathSyntax) {
    return text;
  }

  // 8. Kiểm tra xem chuỗi có chứa từ ngữ tự nhiên (tiếng Việt/đàm thoại) hay không
  const tokens = text.split(/\s+/);
  const hasText = tokens.some((tok) => isTextToken(tok));

  // 9. Nếu KHÔNG có từ ngữ tự nhiên nào -> Biểu thức toán học thuần túy
  if (!hasText) {
    return `$${text}$`;
  }

  // 10. Chuỗi hỗn hợp: Gom cụm các token toán và bọc $...$ cho từng cụm
  const resultParts: string[] = [];
  const currentMath: string[] = [];

  const flushMath = () => {
    if (currentMath.length === 0) return;
    let mStr = currentMath.join(" ").trim();
    currentMath.length = 0;
    if (!mStr) return;

    if (/[\\^_{}√±×÷≤≥≠π0-9\+\-\*\/=]/.test(mStr)) {
      const punctMatch = mStr.match(/([,\.\?\!;:]+)$/);
      let punct = "";
      if (punctMatch) {
        punct = punctMatch[1];
        mStr = mStr.slice(0, -punct.length).trim();
      }
      if (mStr) {
        resultParts.push(`$${mStr}$${punct}`);
      } else if (punct) {
        resultParts.push(punct);
      }
    } else {
      resultParts.push(mStr);
    }
  };

  for (const tok of tokens) {
    if (isTextToken(tok)) {
      flushMath();
      resultParts.push(tok);
    } else {
      currentMath.push(tok);
    }
  }

  flushMath();

  return resultParts.join(" ");
}

/**
 * Loại bỏ triệt để toàn bộ thẻ ẩn (hidden metadata tags) và HTML comments khỏi chuỗi hiển thị:
 * - HTML comment: <!-- PROBE_PENDING -->, <!-- SUMMER_PROBE_PENDING -->, <!-- AUDIT_AGENT: ... -->, v.v.
 * - Thẻ đóng mở dang dở khi đang stream: <!-- ...
 * - Thẻ vuông metadata: [PROBE_PENDING], [SUMMER_PROBE_PENDING], [COMPREHENSION_CHECK]
 */
export function stripHiddenTags(content: string): string {
  if (!content || typeof content !== "string") return "";
  return content
    .replace(/<!--[\s\S]*?(?:-->|$)/g, "")
    .replace(/\s*\[(?:SUMMER_)?PROBE_PENDING\]/gi, "")
    .replace(/\s*\[COMPREHENSION_CHECK\]/gi, "")
    .trim();
}

export function preprocessLaTeX(content: string): string {
  if (!content || typeof content !== "string") return content;
  content = content.normalize("NFKC");

  // 0. Làm sạch thẻ ẩn (hidden tags) để không bao giờ lộ ra trên màn hình chat của học sinh
  const cleaned = stripHiddenTags(content);

  // 1. Tách và bảo vệ các khối code (code block ```...``` và inline code `...`)
  const codeBlocks: { id: string; code: string }[] = [];
  let protectedContent = cleaned.replace(/(```[\s\S]*?```|`[^`\n]+`)/g, (match) => {
    const id = `%%%CODE_BLOCK_${codeBlocks.length}%%%`;
    codeBlocks.push({ id, code: match });
    return id;
  });

  // 2. Chuẩn hóa display math: \\[ ... \\] hoặc \[ ... \] -> \n\n$$\n... \n$$\n\n
  // Hỗ trợ cả trường hợp backslash bị escape kép qua JSON
  protectedContent = protectedContent.replace(
    /(?:\\\\\[|\\\[)([\s\S]*?)(?:\\\\\]|\\\])/g,
    (_, equation) => `\n\n$$\n${equation.trim()}\n$$\n\n`
  );

  // 3. Chuẩn hóa inline math: \\( ... \\) hoặc \( ... \) -> $...$
  protectedContent = protectedContent.replace(
    /(?:\\\\\(|\\\()([\s\S]*?)(?:\\\\\)|\\\))/g,
    (_, equation) => `$${equation.trim()}$`
  );

  // 4. Chuẩn hóa display math $$...$$ đứng độc lập / riêng dòng:
  // Đảm bảo luôn có dòng trống \n\n bao bọc để remark-math bắt buộc render block display
  protectedContent = protectedContent.replace(
    /(?:^|\n)\s*\$\$\s*([\s\S]*?)\s*\$\$\s*(?:\n|$)/g,
    (_, equation) => `\n\n$$\n${equation.trim()}\n$$\n\n`
  );

  // 5. Chuẩn hóa $$...$$ xuất hiện giữa dòng văn bản (inline $$) thành $...$ để render inline tự nhiên
  protectedContent = protectedContent.replace(
    /\$\$([^\$\n]+?)\$\$/g,
    (_, equation) => `$${equation.trim()}$`
  );

  // 6. Chuẩn hóa khoảng trắng của inline math $...$:
  // - Xóa khoảng trắng thừa BÊN TRONG $ ($ x $ -> $x$) để remark-math parse được chuẩn
  // - Đảm bảo có khoảng trắng phân cách BÊN NGOÀI giữa chữ/số và dấu $ (tránh dính chữ số như "tử số$12$chia")
  // - Bảo toàn 100% khoảng trắng ngoài và dấu câu (, . ! ? : ;) giữa các công thức
  const isWordChar = (ch: string) => {
    if (!ch) return false;
    return /[a-zA-Z0-9\u00C0-\u024F\u1EA0-\u1EF9]/.test(ch);
  };

  const lines = protectedContent.split("\n");
  const processedLines = lines.map((line) => {
    if (line.trim().startsWith("$$")) return line;

    let result = "";
    let i = 0;

    while (i < line.length) {
      // Escaped \$
      if (line[i] === "\\" && line[i + 1] === "$") {
        result += "\\$";
        i += 2;
        continue;
      }

      // Display math delimiter $$
      if (line[i] === "$" && line[i + 1] === "$") {
        result += "$$";
        i += 2;
        continue;
      }

      // Single $
      if (line[i] === "$") {
        // Tìm dấu $ đóng duy nhất cùng dòng
        let closeIdx = -1;
        let j = i + 1;
        while (j < line.length) {
          if (line[j] === "\\" && line[j + 1] === "$") {
            j += 2;
            continue;
          }
          if (line[j] === "$" && line[j + 1] === "$") {
            j += 2;
            continue;
          }
          if (line[j] === "$") {
            closeIdx = j;
            break;
          }
          j++;
        }

        if (closeIdx !== -1) {
          const rawMath = line.slice(i + 1, closeIdx);
          const trimmedMath = rawMath.trim();

          if (trimmedMath.length > 0) {
            // Nếu bên trong dấu $ có chứa từ ngữ tự nhiên (tiếng Việt/đàm thoại),
            // ví dụ như do tin nhắn bị bao $...$ toàn bộ: $Thầy ơi, bài tính lũy thừa 2^3 x 2^4 này làm sao ạ?$
            // Ta cần giải phóng văn bản ra ngoài dấu $ và chỉ bọc $ cho biểu thức toán thực sự.
            if (
              hasNaturalLanguage(trimmedMath) ||
              /\\(?:text|mathrm|textrm|textsf|textbf|textit|mathbf|mathit)\s*\{/.test(trimmedMath)
            ) {
              const formatted = formatLatexForChat(trimmedMath);
              result += formatted;
            } else {
              // Kiểm tra ký tự liền trước dấu $ mở (trong chuỗi result hiện tại)
              const prevChar = result.length > 0 ? result[result.length - 1] : "";
              if (isWordChar(prevChar)) {
                result += " ";
              }

              result += `$${trimmedMath}$`;

              // Kiểm tra ký tự liền sau dấu $ đóng
              const nextChar = closeIdx + 1 < line.length ? line[closeIdx + 1] : "";
              if (isWordChar(nextChar)) {
                result += " ";
              }
            }
          } else {
            result += "$$";
          }

          i = closeIdx + 1;
          continue;
        } else {
          result += "$";
          i++;
          continue;
        }
      }

      result += line[i];
      i++;
    }

    return result;
  });

  protectedContent = processedLines.join("\n");

  // 7. Khôi phục lại các khối code nguyên bản (dùng callback để tránh ký tự $ trong code bị hàm replace biến dạng)
  for (const block of codeBlocks) {
    protectedContent = protectedContent.replace(block.id, () => block.code);
  }

  return protectedContent;
}

/**
 * US 9.4: Làm sạch chuỗi LaTeX để hiển thị văn bản tự nhiên, dễ đọc.
 * Chuyển đổi các công thức LaTeX như $\frac{10}{2} = ?$ thành 10/2 = ?, $5^2+ 5^2$ thành 5² + 5²,
 * \sqrt{...} thành √(...), loại bỏ hoàn toàn các ký hiệu $ và lệnh LaTeX code thừa.
 */
export function cleanLatexForDisplay(content: string | null | undefined, maxLength?: number): string {
  if (!content || typeof content !== "string") return "";
  let t = stripHiddenTags(content).trim();

  // Bỏ dấu ngoặc kép thừa nếu chuỗi bị bọc lặp (VD: "\"$\frac{...}$\"")
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith('“') && t.endsWith('”'))) {
    t = t.slice(1, -1).trim();
  }

  // 1. Gỡ bỏ dấu $ và $$
  t = t.replace(/\$/g, "");

  // 2. Chuyển phân số \frac{a}{b} thành a/b đệ quy
  while (/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/.test(t)) {
    t = t.replace(/\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, "$1/$2");
  }
  t = t.replace(/\\frac\s*([0-9a-zA-Z])([0-9a-zA-Z])/g, "$1/$2");

  // 3. Chuyển căn thức \sqrt{...} thành √(...)
  while (/\\sqrt\s*\{([^{}]*)\}/.test(t)) {
    t = t.replace(/\\sqrt\s*\{([^{}]*)\}/g, "√($1)");
  }
  t = t.replace(/\\sqrt\s*([0-9a-zA-Z])/g, "√$1");

  // 4. Lũy thừa phổ biến: ^2 -> ², ^3 -> ³, ^{...} -> ^(...)
  t = t.replace(/\^2(?![0-9])/g, "²");
  t = t.replace(/\^3(?![0-9])/g, "³");
  t = t.replace(/\^\{([^{}]*)\}/g, "^($1)");

  // 5. Các ký hiệu toán học phổ biến
  t = t
    .replace(/\\times/g, "×")
    .replace(/\\cdot/g, "·")
    .replace(/\\div/g, "÷")
    .replace(/\\pm/g, "±")
    .replace(/\\pi/g, "π")
    .replace(/\\le(?:q)?(?![a-zA-Z])/g, "≤")
    .replace(/\\ge(?:q)?(?![a-zA-Z])/g, "≥")
    .replace(/\\ne(?:q)?(?![a-zA-Z])/g, "≠")
    .replace(/\\approx/g, "≈")
    .replace(/\\circ|\\degree/g, "°")
    .replace(/\\left\|/g, "|")
    .replace(/\\right\|/g, "|")
    .replace(/\\left\[/g, "[")
    .replace(/\\right\]/g, "]")
    .replace(/\\left\(/g, "(")
    .replace(/\\right\)/g, ")")
    .replace(/\\left\./g, "")
    .replace(/\\right\./g, "")
    .replace(/\\left/g, "")
    .replace(/\\right/g, "")
    .replace(/\\text\s*\{([^{}]*)\}/g, "$1")
    .replace(/\\placeholder\{[^}]*\}/g, "...")
    .replace(/\\square/g, "...")
    .replace(/\\operatorname\{(th|ch|sh|tg|cotg|cth)\}/gi, "$1")
    .replace(/\\(?:quad|enspace|;|,)*/g, " ")
    .replace(/\\ /g, " ")
    .replace(/\\[a-zA-Z]+/g, "") // Bỏ các lệnh LaTeX còn sót
    .replace(/[{}]/g, "") // Bỏ ngoặc nhọn thừa nếu còn
    .replace(/\\/g, "")
    .replace(/\s+/g, " ")
    .trim();

  // Tách số và chữ tiếng Việt nếu bị dính nhau (VD: "23bằng" -> "23 bằng")
  t = t.replace(/([0-9])([àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])/gi, "$1 $2");
  // Khắc phục tách chữ tiếng Việt nếu có (VD: "th ầy" -> "thầy", "b ằng mấy" -> "bằng mấy", "ng ười" -> "người")
  let prevT;
  do {
    prevT = t;
    t = t.replace(/(^|\s)([b-df-hj-np-tv-zB-DF-HJ-NP-TV-ZđĐ]+)\s+([àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ][a-zA-Z\u00C0-\u1EF9]*)/gi, "$1$2$3");
  } while (t !== prevT);

  if (maxLength && t.length > maxLength) {
    return t.slice(0, maxLength) + "...";
  }

  return t;
}

export function cleanLatexForTitle(content: string): string {
  if (!content || typeof content !== "string") return "Phòng chat mới";
  const cleaned = cleanLatexForDisplay(content, 25);
  return cleaned || "Phòng chat mới";
}
