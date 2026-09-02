import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {},
  webpack: (config) => {
    // Canvas / PDF.js compatibility
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
