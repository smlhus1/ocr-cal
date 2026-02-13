const { withSentryConfig } = require("@sentry/nextjs");

const isDev = process.env.NODE_ENV !== 'production';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Security headers
  async headers() {
    // Skip CSP in dev - Next.js hot-reload needs unsafe-eval and inline scripts
    if (isDev) return [];

    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' https://*.sentry.io",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob:",
              "font-src 'self'",
              "connect-src 'self' http://localhost:8000 https://api.shiftsync.no https://*.ingest.sentry.io",
              "frame-ancestors 'none'",
            ].join('; ')
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()'
          }
        ]
      }
    ];
  },
  
  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  }
};

module.exports = process.env.SENTRY_AUTH_TOKEN
  ? withSentryConfig(nextConfig, {
      org: "shiftsync",
      project: "shiftsync-frontend",
      silent: true,
      hideSourceMaps: true,
    })
  : nextConfig;

