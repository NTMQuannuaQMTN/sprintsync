/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Server-side only (no NEXT_PUBLIC_ prefix needed) — Vercel resolves
    // rewrites per-request on its edge/serverless layer, so this reads the
    // env var set in the Vercel dashboard, not anything bundled client-side.
    const apiUrl = process.env.API_URL || 'http://localhost:8000'
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ]
  },
  images: {
    domains: ['avatars.githubusercontent.com', 'github.com'],
  },
}

module.exports = nextConfig
