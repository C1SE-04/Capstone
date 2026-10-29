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
