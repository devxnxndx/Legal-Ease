import type { NextConfig } from 'next'

const PYTHON_BACKEND = process.env.PYTHON_BACKEND_URL ?? 'http://127.0.0.1:8000'

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${PYTHON_BACKEND}/api/:path*`,
      },
    ]
  },
  // Increase body size limit for PDF uploads (default 1MB is too small)
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
  },
  // Increase proxy timeout to handle long-running AI requests
  httpAgentOptions: {
    keepAlive: true,
  },
}

export default nextConfig
