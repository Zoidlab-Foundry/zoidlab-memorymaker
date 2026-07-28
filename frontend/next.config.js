/** @type {import('next').NextConfig} */
const API = process.env.MEMORYMAKER_API_URL || "http://127.0.0.1:8500";
module.exports = {
  transpilePackages: ["@foundry/ui"],
  reactStrictMode: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
