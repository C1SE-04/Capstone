/**
 * File: frontend/lib/latex.ts
 * Mô tả: Module tiền xử lý chuỗi Markdown trước khi đưa vào ReactMarkdown.
 * Chuẩn hóa triệt để các công thức toán LaTeX từ Gemini/LLM theo Task T8.5 (US 8.1 - AC 8.1.4):
 * - Chuyển \\[ ... \\] và \[ ... \] thành block math $$ ... $$
 * - Chuyển \\( ... \\) và \( ... \) thành inline math $ ... $
 * - Đảm bảo $$ display luôn có khoảng ngắt dòng \n\n hợp lệ để remark-math parse chuẩn
 * - Chuyển $$ giữa dòng văn bản (inline) thành $ ... $
 * - Xóa khoảng trắng thừa sát viền dấu $ ($ x $ -> $x$)
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

  // 6. Xóa khoảng trắng thừa sát viền dấu $ mở hoặc $ đóng ($ x + 1 $ -> $x + 1$)
  // remark-math từ chối parse math nếu ngay sau $ mở hoặc trước $ đóng có space
  protectedContent = protectedContent.replace(
    /(^|[^\\])\$([ \t]+)([^$\n]+?)([ \t]*)\$/g,
    (_, prefix, _s, inner) => `${prefix}$${inner.trim()}$`
  );
  protectedContent = protectedContent.replace(
    /(^|[^\\])\$([^$\n]+?)([ \t]+)\$/g,
    (_, prefix, inner) => `${prefix}$${inner.trim()}$`
  );

  // 7. Khôi phục lại các khối code nguyên bản (dùng callback để tránh ký tự $ trong code bị hàm replace biến dạng)
  for (const block of codeBlocks) {
    protectedContent = protectedContent.replace(block.id, () => block.code);
  }

  return protectedContent;
}
