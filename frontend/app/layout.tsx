import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ToastContainer from '@/components/Toast'

const inter = Inter({ subsets: ['latin'] })

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0ea5e9',
}

export const metadata: Metadata = {
  title: 'ShiftSync - Vaktplan til Kalender',
  description: 'Konverter vaktplan-bilder til iCalendar med OCR. Aldri skriv inn vakter manuelt igjen!',
  keywords: 'vaktplan, kalender, OCR, shift schedule, ical, vakter',
  authors: [{ name: 'ShiftSync' }],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="no">
      <body className={inter.className}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-sky-600 focus:text-white focus:rounded"
        >
          Hopp til hovedinnhold
        </a>
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center">
                <h1 className="text-2xl font-bold text-sky-600">
                  ShiftSync
                </h1>
              </div>
              <div className="flex items-center space-x-4">
                <a href="/" className="text-gray-600 hover:text-gray-900 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Hjem
                </a>
                <a href="/about" className="text-gray-600 hover:text-gray-900 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Om oss
                </a>
              </div>
            </div>
          </div>
        </nav>
        <main id="main-content" className="min-h-screen bg-gray-50">
          {children}
        </main>
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <p className="text-center text-gray-500 text-sm">
              &copy; {new Date().getFullYear()} ShiftSync. Utviklet med fokus p&aring; sikkerhet og personvern.
            </p>
          </div>
        </footer>
        <ToastContainer />
      </body>
    </html>
  )
}
