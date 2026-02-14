import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import './globals.css'
import ToastContainer from '@/components/Toast'
import CookieConsent from '@/components/CookieConsent'

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
  openGraph: {
    title: 'ShiftSync - Vaktplan til Kalender',
    description: 'Konverter vaktplan-bilder til iCalendar med OCR. Aldri skriv inn vakter manuelt igjen!',
    url: 'https://shiftsync.no',
    siteName: 'ShiftSync',
    locale: 'nb_NO',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ShiftSync - Vaktplan til Kalender',
    description: 'Konverter vaktplan-bilder til iCalendar med OCR. Aldri skriv inn vakter manuelt igjen!',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="nb">
      <body className={inter.className}>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-sky-600 focus:text-white focus:rounded"
        >
          Hopp til hovedinnhold
        </a>
        <nav aria-label="Hovednavigasjon" className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center">
                <Link href="/" className="text-2xl font-bold text-sky-600 focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  ShiftSync
                </Link>
              </div>
              <div className="flex items-center space-x-4">
                <Link href="/" className="text-gray-600 hover:text-gray-900 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Hjem
                </Link>
                <Link href="/about" className="text-gray-600 hover:text-gray-900 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Om oss
                </Link>
              </div>
            </div>
          </div>
        </nav>
        <main id="main-content" className="min-h-screen bg-gray-50">
          {children}
        </main>
        <footer className="bg-white border-t border-gray-200 mt-12">
          <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col sm:flex-row justify-center items-center gap-2 sm:gap-6 text-sm text-gray-500">
              <p>
                &copy; {new Date().getFullYear()} ShiftSync
              </p>
              <nav aria-label="Footer" className="flex gap-4">
                <Link href="/personvern" className="hover:text-gray-700 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Personvern
                </Link>
                <Link href="/vilkar" className="hover:text-gray-700 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Vilk&aring;r
                </Link>
                <Link href="/about" className="hover:text-gray-700 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
                  Om oss
                </Link>
              </nav>
            </div>
          </div>
        </footer>
        <ToastContainer />
        <CookieConsent />
      </body>
    </html>
  )
}
