/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'export',   // Static HTML export — required for Amplify manual zip deploy
    reactStrictMode: true,
    trailingSlash: true,
};

export default nextConfig;
