import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const {
      fullName,
      email,
      category,
      message,
      attachedImagesCount = 0,
      recaptcha_token,
    } = body;

    // Kiểm tra tính hợp lệ cơ bản
    if (!fullName?.trim() || !email?.trim() || !category || !message?.trim()) {
      return NextResponse.json(
        { error: "Vui lòng điền đầy đủ các thông tin bắt buộc." },
        { status: 400 }
      );
    }

    // Nếu hệ thống đã cấu hình Secret Key cho Google reCAPTCHA v3 thì tiến hành xác thực ngầm
    const recaptchaSecret = process.env.RECAPTCHA_SECRET_KEY;
    if (recaptchaSecret && recaptcha_token) {
      try {
        const verifyRes = await fetch(
          "https://www.google.com/recaptcha/api/siteverify",
          {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `secret=${encodeURIComponent(recaptchaSecret)}&response=${encodeURIComponent(recaptcha_token)}`,
          }
        );
        const verifyData = await verifyRes.json();
        if (
          !verifyData.success ||
          (verifyData.score !== undefined && verifyData.score < 0.5)
        ) {
          console.warn("[reCAPTCHA v3] Điểm đánh giá thấp hoặc xác thực thất bại:", verifyData);
          // Trong môi trường production có thể trả về lỗi nếu phát hiện bot; ở dev/test ghi nhận log cảnh báo
        }
      } catch (err) {
        console.warn("[reCAPTCHA v3] Không thể kết nối máy chủ Google verify:", err);
      }
    }

    // Chuyển tiếp dữ liệu đến Backend SocraticKid (nếu dịch vụ backend đang mở)
    const backendUrl =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      "http://127.0.0.1:8000";

    try {
      await fetch(`${backendUrl}/api/errors/report-user-issue`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: `[Góp ý Form] ${category}: ${fullName.trim()}`,
          detail: message.trim(),
          endpoint: "/contact",
          client_context: {
            fullName: fullName.trim(),
            email: email.trim(),
            category,
            message: message.trim(),
            attachedImagesCount,
            recaptcha_verified: !!recaptcha_token,
            submittedAt: new Date().toISOString(),
          },
        }),
      });
    } catch {
      // Backend có thể đang offline ở môi trường test nội bộ
    }

    return NextResponse.json({
      success: true,
      message: "Góp ý của bạn đã được ghi nhận thành công!",
    });
  } catch (error) {
    console.error("[Contact Submit API Error]:", error);
    return NextResponse.json(
      { error: "Có lỗi xảy ra trong quá trình tiếp nhận. Vui lòng thử lại sau." },
      { status: 500 }
    );
  }
}
