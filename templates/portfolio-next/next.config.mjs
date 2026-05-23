/** @type {import('next').NextConfig} */
const assetPrefix = process.env.NEXT_PUBLIC_ASSET_PREFIX || undefined;

const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: false,
  ...(assetPrefix ? { assetPrefix } : {}),
};

export default nextConfig;
