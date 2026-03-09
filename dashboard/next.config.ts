import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = process.env.LEAD_API_URL;
    if (!apiUrl) {
      console.warn("LEAD_API_URL is not set — /docs will not proxy to the API");
      return [];
    }
    return [
      { source: "/docs", destination: `${apiUrl}/docs` },
      { source: "/docs/:path*", destination: `${apiUrl}/docs/:path*` },
      { source: "/openapi.json", destination: `${apiUrl}/openapi.json` },
    ];
  },
};

export default nextConfig;
