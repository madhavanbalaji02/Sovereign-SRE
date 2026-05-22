/** @type {import('next').NextConfig} */
const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000';

const nextConfig = {
    output: 'standalone',
    reactStrictMode: true,
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${BACKEND}/api/:path*`,
            },
        ];
    },
};

export default nextConfig;
