import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = process.env.LEAD_API_URL;
    if (!apiUrl) return [];
    return [
      { source: "/docs", destination: `${apiUrl}/docs` },
      { source: "/openapi.json", destination: `${apiUrl}/openapi.json` },
    ];
  },
};

export default nextConfig;
