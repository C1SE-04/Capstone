/**
 * File: data/mockLessons.ts
 * Mô tả: File chứa dữ liệu giả lập (mock data) cho các bài học.
 * Được sử dụng tạm thời để test giao diện trước khi ghép nối với Backend API.
 */
export interface LessonProps {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  progress: number;
}

export const mockLessons: LessonProps[] = [
  {
    id: "1",
    title: "Toán học: Đại số tuyến tính",
    description: "Học về ma trận, định thức và hệ phương trình tuyến tính cơ bản.",
    thumbnail: "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800&auto=format&fit=crop&q=60",
    progress: 75,
  }
];
