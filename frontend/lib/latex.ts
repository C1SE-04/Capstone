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

export function preprocessLaTeX(content: string): string {
  if (!content || typeof content !== "string") return content;

  // 1. Tách và bảo vệ các khối code (code block ```...``` và inline code `...`)
  const codeBlocks: { id: string; code: string }[] = [];
  let protectedContent = content.replace(/(```[\s\S]*?```|`[^`\n]+`)/g, (match) => {
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
  let t = content.trim();

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
    .replace(/\\(?:quad|enspace|;|,)*/g, " ")
    .replace(/\\ /g, " ")
    .replace(/\\[a-zA-Z]+/g, "") // Bỏ các lệnh LaTeX còn sót
    .replace(/[{}]/g, "") // Bỏ ngoặc nhọn thừa nếu còn
    .replace(/\\/g, "")
    .replace(/\s+/g, " ")
    .trim();

  // Tách số và chữ tiếng Việt nếu bị dính nhau (VD: "23bằng" -> "23 bằng")
  t = t.replace(/([0-9])([àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])/gi, "$1 $2");
  // Khắc phục tách chữ tiếng Việt nếu có (VD: "b ằng mấy" -> "bằng mấy")
  t = t.replace(/\b([a-zA-Z])\s+([àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])/gi, "$1$2");

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
