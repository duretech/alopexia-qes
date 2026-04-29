import path from "node:path";
import type { NextConfig } from "next";

const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/clinic";

const nextConfig: NextConfig = {
  output: "standalone",
  basePath: "/clinic",
  experimental: {
    externalDir: true,
  },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "react-qr-code": path.join(process.cwd(), "node_modules", "react-qr-code"),
      canvas: false,
    };
    return config;
  },
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${api}/api/:path*`, basePath: false },
      { source: "/health/:path*", destination: `${api}/health/:path*`, basePath: false },
    ];
  },
};

export default nextConfig;
