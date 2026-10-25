import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async redirects() {
    return [
      {
        source: '/dashboard',
        destination: '/dashboard/chat',
        permanent: true, // hoac false tuy muc dich, de true hien tai vi tam thoi an
      },
    ];
  },
};

export default nextConfig;
