import path from "node:path";
import type { NextConfig } from "next";

const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    externalDir: true,
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "react-qr-code": path.join(process.cwd(), "node_modules", "react-qr-code"),
    };
    return config;
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*` },
      { source: "/health/:path*", destination: `${api}/health/:path*` },
    ];
  },
};

export default nextConfig;
