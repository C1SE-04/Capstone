"use client";

import React, { useState, useEffect, useRef, ChangeEvent, DragEvent } from "react";
import { useSession } from "next-auth/react";
import {
  Send,
  Loader2,
  AlertCircle,
  UploadCloud,
  X,
  CheckCircle2,
  Image as ImageIcon,
  RotateCcw,
  Sparkles,
} from "lucide-react";

declare global {
  interface Window {
    grecaptcha?: {
      ready: (callback: () => void) => void;
      execute: (
        siteKey: string,
        options: { action: string }
      ) => Promise<string>;
    };
  }
}

/**
 * File: frontend/components/contact/ContactForm.tsx
 * Sprint 11 - Task T11.5.5: Code Biểu mẫu Liên hệ
 * ==============================================================================
 * Form góp ý & báo lỗi tối ưu UI/UX Pro Max:
 * - Tự động điền Họ tên & Email từ NextAuth Session
 * - Inline Validation thời gian thực tại sự kiện onBlur (không bắt người dùng đợi bấm Gửi)
 * - Textarea đếm ký tự (đổi màu cảnh báo >450 và đỏ tại 500)
 * - Drag & Drop Upload ảnh (Tối đa 2 ảnh, <= 5MB/ảnh, preview + xóa nhanh)
 * - Anti-spam double-click + Loading spinner
 * - Success Card thay thế form khi gửi thành công
 */

interface FormState {
  fullName: string;
  email: string;
  category: string;
  message: string;
}

interface FormErrors {
  fullName?: string;
  email?: string;
  category?: string;
  message?: string;
}

interface UploadedImage {
  id: string;
  file: File;
  previewUrl: string;
  name: string;
  size: number;
}

const CATEGORY_OPTIONS = [
  { value: "PEDAGOGY", label: "Thắc mắc phương pháp sư phạm & Gợi ý AI" },
  { value: "BUG_REPORT", label: "Báo lỗi kỹ thuật / Không nhận được phản hồi" },
  { value: "FEATURE_REQUEST", label: "Đề xuất tính năng học tập mới" },
  { value: "COOPERATION", label: "Hợp tác nhà trường & Nghiên cứu giáo dục" },
  { value: "OTHER", label: "Góp ý khác" },
];

const MAX_MESSAGE_LENGTH = 500;
const WARNING_THRESHOLD = 450;
const MAX_IMAGE_COUNT = 2;
const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024; // 5MB
const ALLOWED_MIME_TYPES = [
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
];

export default function ContactForm() {
  const { data: session } = useSession();

  // ── 1. Quản lý Trạng thái Biểu mẫu ──
  const [formData, setFormData] = useState<FormState>({
    fullName: "",
    email: "",
    category: "PEDAGOGY",
    message: "",
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Record<keyof FormState, boolean>>({
    fullName: false,
    email: false,
    category: false,
    message: false,
  });

  const [images, setImages] = useState<UploadedImage[]>([]);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{
    text: string;
    type: "error" | "info";
  } | null>(null);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isSuccess, setIsSuccess] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ── Tự động điền Họ tên và Email từ NextAuth Session (Auto-fill) ──
  useEffect(() => {
    if (session?.user) {
      setFormData((prev) => ({
        ...prev,
        fullName: prev.fullName || session.user?.name || "",
        email: prev.email || session.user?.email || "",
      }));
    }
  }, [session]);

  // Helper hiển thị thông báo Toast ngắn hạn
  const showToast = (text: string, type: "error" | "info" = "error") => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
    }
    setToastMessage({ text, type });
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  // ── 2. Inline Validation Rules ──
  const validateField = (field: keyof FormState, value: string): string | undefined => {
    switch (field) {
      case "fullName": {
        const trimmed = value.trim();
        if (!trimmed) return "Vui lòng nhập họ và tên của bạn.";
        if (trimmed.length < 2) return "Họ và tên phải có ít nhất 2 ký tự.";
        return undefined;
      }

      case "email": {
        const trimmed = value.trim();
        if (!trimmed) return "Vui lòng nhập địa chỉ email liên hệ.";
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(trimmed)) {
          return "Định dạng email chưa hợp lệ (Ví dụ: ten@gmail.com).";
        }
        return undefined;
      }

      case "category": {
        if (!value) return "Vui lòng chọn danh mục nội dung.";
        return undefined;
      }

      case "message": {
        const trimmed = value.trim();
        if (!trimmed) return "Vui lòng chia sẻ nội dung bạn muốn gửi tới SocraticKid.";
        if (trimmed.length < 10) return "Nội dung cần tối thiểu 10 ký tự để chúng mình hiểu rõ vấn đề.";
        if (trimmed.length > MAX_MESSAGE_LENGTH) return `Nội dung không được vượt quá ${MAX_MESSAGE_LENGTH} ký tự.`;
        return undefined;
      }

      default:
        return undefined;
    }
  };

  // Xử lý sự kiện onBlur (Kiểm tra lỗi ngay khi người dùng rời khỏi ô nhập)
  const handleBlur = (field: keyof FormState) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const errorMsg = validateField(field, formData[field]);
    setErrors((prev) => ({ ...prev, [field]: errorMsg }));
  };

  // Xử lý sự kiện onChange (Xóa lỗi trường đó ngay khi người dùng bắt đầu sửa)
  const handleChange = (
    field: keyof FormState,
    value: string
  ) => {
    if (field === "message" && value.length > MAX_MESSAGE_LENGTH) {
      value = value.slice(0, MAX_MESSAGE_LENGTH);
    }

    setFormData((prev) => ({ ...prev, [field]: value }));

    // Nếu trường đã từng bị báo lỗi, kiểm tra lại để xóa lỗi ngay lập tức
    if (errors[field]) {
      const errorMsg = validateField(field, value);
      setErrors((prev) => ({ ...prev, [field]: errorMsg }));
    }
  };

  // ── 3. Quản lý Tệp tải lên (Drag & Drop + Validation) ──
  const handleFiles = (incomingFiles: FileList | File[]) => {
    const fileArray = Array.from(incomingFiles);

    if (images.length + fileArray.length > MAX_IMAGE_COUNT) {
      showToast(`Bạn chỉ có thể đính kèm tối đa ${MAX_IMAGE_COUNT} ảnh minh họa.`);
      return;
    }

    const newUploaded: UploadedImage[] = [];

    for (const file of fileArray) {
      // Kiểm tra định dạng
      if (!ALLOWED_MIME_TYPES.includes(file.type)) {
        showToast(`Định dạng "${file.name}" không hợp lệ. Chỉ chấp nhận JPG, PNG hoặc WEBP.`);
        continue;
      }

      // Kiểm tra dung lượng <= 5MB
      if (file.size > MAX_FILE_SIZE_BYTES) {
        showToast(`Ảnh "${file.name}" vượt quá 5MB. Vui lòng chọn ảnh dung lượng nhẹ hơn.`);
        continue;
      }

      // Tạo preview
      const previewUrl = URL.createObjectURL(file);
      newUploaded.push({
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        file,
        previewUrl,
        name: file.name,
        size: file.size,
      });
    }

    if (newUploaded.length > 0) {
      setImages((prev) => [...prev, ...newUploaded].slice(0, MAX_IMAGE_COUNT));
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleRemoveImage = (idToRemove: string) => {
    setImages((prev) => {
      const target = prev.find((img) => img.id === idToRemove);
      if (target?.previewUrl) {
        URL.revokeObjectURL(target.previewUrl);
      }
      return prev.filter((img) => img.id !== idToRemove);
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // ── 4. Xử lý Gửi Biểu mẫu & Anti-spam ──
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Đánh dấu tất cả trường là touched
    setTouched({
      fullName: true,
      email: true,
      category: true,
      message: true,
    });

    // Validate toàn bộ form
    const fullNameErr = validateField("fullName", formData.fullName);
    const emailErr = validateField("email", formData.email);
    const categoryErr = validateField("category", formData.category);
    const messageErr = validateField("message", formData.message);

    const allErrors = {
      fullName: fullNameErr,
      email: emailErr,
      category: categoryErr,
      message: messageErr,
    };

    setErrors(allErrors);

    if (fullNameErr || emailErr || categoryErr || messageErr) {
      showToast("Vui lòng kiểm tra và hoàn thiện các trường còn thiếu màu đỏ.");
      return;
    }

    // Chặn Double-Click / Spam
    if (isSubmitting) return;

    try {
      setIsSubmitting(true);

      // ── Tích hợp Google reCAPTCHA v3 ngầm (Invisible) ──
      let recaptchaToken: string | null = null;
      const siteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY;

      if (siteKey && typeof window !== "undefined" && window.grecaptcha) {
        try {
          recaptchaToken = await window.grecaptcha.execute(siteKey, {
            action: "contact_submit",
          });
        } catch (recaptchaErr) {
          console.warn(
            "[reCAPTCHA v3] Không thể lấy token từ Google reCAPTCHA, tiếp tục ở chế độ dự phòng:",
            recaptchaErr
          );
        }
      } else {
        if (!siteKey) {
          console.warn(
            "[reCAPTCHA v3] Biến môi trường NEXT_PUBLIC_RECAPTCHA_SITE_KEY chưa được cấu hình. Cho phép gửi form ở chế độ thử nghiệm nội bộ."
          );
        }
      }

      // Đóng gói payload gửi tới POST /api/contact/submit
      const payload = {
        fullName: formData.fullName.trim(),
        email: formData.email.trim(),
        category: formData.category,
        message: formData.message.trim(),
        attachedImagesCount: images.length,
        submittedAt: new Date().toISOString(),
        recaptcha_token: recaptchaToken,
      };

      const res = await fetch("/api/contact/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.error || "Gửi thông tin không thành công.");
      }

      // Đánh dấu hoàn tất gửi thành công
      setIsSuccess(true);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : "Có lỗi xảy ra trong quá trình gửi. Vui lòng thử lại sau giây lát.";
      showToast(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Reset form về trạng thái ban đầu
  const handleResetForm = () => {
    // Dọn dẹp URL previews
    images.forEach((img) => URL.revokeObjectURL(img.previewUrl));

    setFormData({
      fullName: session?.user?.name || "",
      email: session?.user?.email || "",
      category: "PEDAGOGY",
      message: "",
    });
    setImages([]);
    setErrors({});
    setTouched({
      fullName: false,
      email: false,
      category: false,
      message: false,
    });
    setIsSuccess(false);
  };

  // ── 5. Màn hình Thành công (Success Card State) ──
  if (isSuccess) {
    return (
      <div className="p-8 sm:p-12 text-center flex flex-col items-center justify-center animate-in fade-in zoom-in-95 duration-300">
        <div className="w-20 h-20 rounded-3xl bg-[#ECFDF5] border border-[#10B981]/30 flex items-center justify-center text-[#10B981] mb-6 shadow-sm ring-8 ring-[#ECFDF5]/50">
          <CheckCircle2 className="w-10 h-10 stroke-[2.2]" />
        </div>

        <span className="text-xs uppercase tracking-wider font-extrabold text-[#10B981] bg-[#ECFDF5] py-1.5 px-3.5 rounded-full border border-[#10B981]/30 mb-3">
          Gửi Thành Công
        </span>

        <h3 className="text-2xl sm:text-3xl font-extrabold text-[#1C1917] tracking-tight mb-3">
          Cảm Ơn Bạn Đã Đóng Góp Ý Kiến!
        </h3>

        <p className="text-sm sm:text-base text-[#7A3E04] max-w-lg leading-relaxed mb-8">
          Đội ngũ sư phạm và kỹ sư của SocraticKid đã nhận được thông tin từ bạn (
          <span className="font-semibold text-[#1C1917]">{formData.email}</span>
          ). Chúng mình sẽ nghiên cứu kỹ lưỡng và phản hồi sớm nhất có thể.
        </p>

        <button
          type="button"
          onClick={handleResetForm}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-white border border-[#F1CCA6] text-[#8C4905] font-bold text-sm shadow-xs hover:shadow-md hover:bg-[#F7ECE1]/60 active:scale-95 transition-all cursor-pointer group"
        >
          <RotateCcw className="w-4 h-4 transition-transform group-hover:-rotate-90" />
          <span>Gửi ý kiến đóng góp khác</span>
        </button>
      </div>
    );
  }

  const charCount = formData.message.length;
  const isCharWarning = charCount > WARNING_THRESHOLD && charCount < MAX_MESSAGE_LENGTH;
  const isCharMax = charCount >= MAX_MESSAGE_LENGTH;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {/* Toast Notification Box */}
      {toastMessage && (
        <div
          role="alert"
          className={`flex items-center gap-2.5 p-3.5 rounded-2xl text-xs sm:text-sm font-semibold border shadow-xs animate-in fade-in slide-in-from-top-2 duration-200 ${
            toastMessage.type === "error"
              ? "bg-red-50 text-red-700 border-red-200"
              : "bg-amber-50 text-amber-800 border-amber-200"
          }`}
        >
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1">{toastMessage.text}</span>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="p-1 hover:bg-black/5 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* ── Hàng 1: Họ tên & Email ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {/* Họ và tên */}
        <div>
          <label
            htmlFor="fullName"
            className="block text-xs sm:text-sm font-bold text-[#1C1917] mb-1.5"
          >
            Họ và tên của bạn <span className="text-red-500">*</span>
          </label>
          <input
            id="fullName"
            type="text"
            value={formData.fullName}
            onChange={(e) => handleChange("fullName", e.target.value)}
            onBlur={() => handleBlur("fullName")}
            placeholder="Ví dụ: Nguyễn Minh Thư"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-2xl text-xs sm:text-sm bg-white text-[#1C1917] placeholder:text-[#C1762A]/40 border transition-all duration-150 focus:outline-hidden ${
              errors.fullName && touched.fullName
                ? "border-red-500 ring-2 ring-red-100 bg-red-50/20"
                : "border-[#F1CCA6] hover:border-[#C1762A]/70 focus:border-[#C1762A] focus:ring-3 focus:ring-[#C1762A]/15"
            }`}
          />
          {errors.fullName && touched.fullName && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-red-600 animate-in fade-in slide-in-from-top-1 duration-150">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.fullName}</span>
            </div>
          )}
        </div>

        {/* Địa chỉ Email */}
        <div>
          <label
            htmlFor="email"
            className="block text-xs sm:text-sm font-bold text-[#1C1917] mb-1.5"
          >
            Địa chỉ Email liên hệ <span className="text-red-500">*</span>
          </label>
          <input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => handleChange("email", e.target.value)}
            onBlur={() => handleBlur("email")}
            placeholder="ten@vidu.edu.vn"
            disabled={isSubmitting}
            className={`w-full px-4 py-2.5 rounded-2xl text-xs sm:text-sm bg-white text-[#1C1917] placeholder:text-[#C1762A]/40 border transition-all duration-150 focus:outline-hidden ${
              errors.email && touched.email
                ? "border-red-500 ring-2 ring-red-100 bg-red-50/20"
                : "border-[#F1CCA6] hover:border-[#C1762A]/70 focus:border-[#C1762A] focus:ring-3 focus:ring-[#C1762A]/15"
            }`}
          />
          {errors.email && touched.email && (
            <div className="flex items-center gap-1.5 mt-1.5 text-xs text-red-600 animate-in fade-in slide-in-from-top-1 duration-150">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{errors.email}</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Hàng 2: Danh mục / Chủ đề ── */}
      <div>
        <label
          htmlFor="category"
          className="block text-xs sm:text-sm font-bold text-[#1C1917] mb-1.5"
        >
          Chủ đề góp ý hoặc loại sự cố <span className="text-red-500">*</span>
        </label>
        <select
          id="category"
          value={formData.category}
          onChange={(e) => handleChange("category", e.target.value)}
          onBlur={() => handleBlur("category")}
          disabled={isSubmitting}
          className="w-full px-4 py-2.5 rounded-2xl text-xs sm:text-sm bg-white text-[#1C1917] border border-[#F1CCA6] hover:border-[#C1762A]/70 focus:border-[#C1762A] focus:ring-3 focus:ring-[#C1762A]/15 transition-all duration-150 focus:outline-hidden cursor-pointer"
        >
          {CATEGORY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* ── Hàng 3: Textarea Nội dung & Bộ đếm ký tự ── */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label
            htmlFor="message"
            className="block text-xs sm:text-sm font-bold text-[#1C1917]"
          >
            Nội dung chi tiết <span className="text-red-500">*</span>
          </label>

          {/* Bộ đếm ký tự góc trên/dưới */}
          <span
            className={`text-xs transition-colors duration-150 ${
              isCharMax
                ? "text-red-600 font-bold"
                : isCharWarning
                ? "text-amber-600 font-semibold"
                : "text-[#7A3E04]/60 font-medium"
            }`}
          >
            {charCount}/{MAX_MESSAGE_LENGTH} ký tự
          </span>
        </div>

        <div className="relative">
          <textarea
            id="message"
            rows={4}
            value={formData.message}
            onChange={(e) => handleChange("message", e.target.value)}
            onBlur={() => handleBlur("message")}
            placeholder="Hãy mô tả chi tiết trải nghiệm, bài toán hoặc lỗi bạn gặp phải để chúng mình hỗ trợ nhanh nhất nhé..."
            maxLength={MAX_MESSAGE_LENGTH}
            disabled={isSubmitting}
            className={`w-full px-4 py-3 rounded-2xl text-xs sm:text-sm bg-white text-[#1C1917] placeholder:text-[#C1762A]/40 border resize-none transition-all duration-150 focus:outline-hidden ${
              (errors.message && touched.message) || isCharMax
                ? "border-red-500 ring-2 ring-red-100 bg-red-50/10"
                : "border-[#F1CCA6] hover:border-[#C1762A]/70 focus:border-[#C1762A] focus:ring-3 focus:ring-[#C1762A]/15"
            }`}
          />
        </div>

        {errors.message && touched.message && (
          <div className="flex items-center gap-1.5 mt-1.5 text-xs text-red-600 animate-in fade-in slide-in-from-top-1 duration-150">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <span>{errors.message}</span>
          </div>
        )}
      </div>

      {/* ── Hàng 4: Vùng Đính kèm & Kéo thả ảnh (Drag & Drop) ── */}
      <div>
        <label className="block text-xs sm:text-sm font-bold text-[#1C1917] mb-1.5">
          Đính kèm ảnh chụp màn hình{" "}
          <span className="font-normal text-[#7A3E04]/70">
            (Tối đa 2 ảnh, ≤ 5MB/ảnh)
          </span>
        </label>

        {/* Input file ẩn */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/webp"
          multiple
          onChange={handleFileInputChange}
          className="hidden"
          disabled={isSubmitting || images.length >= MAX_IMAGE_COUNT}
        />

        {/* Khung thả file (Dropzone) */}
        {images.length < MAX_IMAGE_COUNT && (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`p-5 rounded-2xl border-2 border-dashed transition-all duration-200 text-center flex flex-col items-center justify-center cursor-pointer group ${
              isDragging
                ? "border-[#C1762A] bg-[#F7ECE1] scale-[1.01]"
                : "border-[#F1CCA6] bg-[#F7ECE1]/30 hover:bg-[#F7ECE1]/60 hover:border-[#C1762A]"
            }`}
          >
            <div className="w-10 h-10 rounded-xl bg-white border border-[#F1CCA6] flex items-center justify-center text-[#C1762A] mb-2 shadow-xs group-hover:scale-105 transition-transform">
              <UploadCloud className="w-5 h-5" />
            </div>
            <p className="text-xs sm:text-sm font-semibold text-[#1C1917] mb-1">
              Kéo thả ảnh vào đây, hoặc{" "}
              <span className="text-[#C1762A] underline underline-offset-2">
                duyệt từ máy tính
              </span>
            </p>
            <p className="text-[11px] text-[#7A3E04]/70">
              Hỗ trợ PNG, JPG, JPEG, WEBP (Tối đa 5MB)
            </p>
          </div>
        )}

        {/* Danh sách ảnh Preview */}
        {images.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-3">
            {images.map((img) => (
              <div
                key={img.id}
                className="relative group w-24 h-24 rounded-2xl border-2 border-[#F1CCA6] overflow-hidden bg-white shadow-xs shrink-0"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.previewUrl}
                  alt={img.name}
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveImage(img.id)}
                  className="absolute top-1 right-1 w-6 h-6 rounded-full bg-red-600/90 text-white flex items-center justify-center shadow-md hover:bg-red-700 transition-colors cursor-pointer"
                  title="Xóa ảnh này"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
                <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-[9px] px-1 py-0.5 truncate text-center">
                  {(img.size / 1024 / 1024).toFixed(1)} MB
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Hàng 5: Nút Gửi Form & Anti-Spam Loading ── */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full inline-flex items-center justify-center gap-2 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white font-bold text-sm sm:text-base shadow-md hover:shadow-xl hover:brightness-105 active:scale-[0.98] transition-all duration-200 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed group"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Đang gửi thông tin...</span>
            </>
          ) : (
            <>
              <span>Gửi thông tin cho chúng mình</span>
              <Send className="w-4 h-4 transition-transform group-hover:translate-x-1 group-hover:-translate-y-0.5" />
            </>
          )}
        </button>

        <p className="text-[11px] text-center text-[#7A3E04]/70 mt-3 leading-relaxed">
          Trang này được bảo vệ bởi reCAPTCHA và tuân theo{" "}
          <a
            href="https://policies.google.com/privacy"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-[#C1762A] transition-colors"
          >
            Chính sách quyền riêng tư
          </a>{" "}
          &{" "}
          <a
            href="https://policies.google.com/terms"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-[#C1762A] transition-colors"
          >
            Điều khoản dịch vụ
          </a>{" "}
          của Google.
        </p>
      </div>
    </form>
  );
}
