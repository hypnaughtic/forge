/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode for catching common issues
  reactStrictMode: true,

  // Experimental features
  experimental: {
    // Enable server actions
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
};

module.exports = nextConfig;
