import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Ikke funnet - ShiftSync',
}

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <p className="text-6xl font-bold text-gray-300 mb-4" aria-hidden="true">404</p>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          Siden ble ikke funnet
        </h1>
        <p className="text-gray-600 mb-6">
          Beklager, vi kunne ikke finne siden du leter etter.
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
        >
          Tilbake til forsiden
        </Link>
      </div>
    </div>
  )
}
