import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Om oss - ShiftSync',
  description: 'ShiftSync konverterer bilder av vaktplaner til kalenderfiler (.ics) ved hjelp av OCR-teknologi.',
}

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Om ShiftSync</h1>

      <div className="prose prose-gray max-w-none space-y-6">
        <p className="text-lg text-gray-600">
          ShiftSync konverterer bilder av vaktplaner til kalenderfiler (.ics) ved hjelp av OCR-teknologi.
          Last opp et bilde av vaktplanen din, og f&aring; en ferdig kalenderfil p&aring; sekunder.
        </p>

        <h2 className="text-xl font-semibold text-gray-900 mt-8">Personvern</h2>
        <p className="text-gray-600">
          Vi tar personvern p&aring; alvor. Alle opplastede filer slettes automatisk etter 24 timer.
          Vi lagrer ingen personlige data &mdash; kun anonymisert statistikk for &aring; forbedre tjenesten.
        </p>

        <h2 className="text-xl font-semibold text-gray-900 mt-8">Kontakt</h2>
        <p className="text-gray-600">
          Sp&oslash;rsm&aring;l eller tilbakemeldinger? Send oss en e-post p&aring;{' '}
          <a href="mailto:kontakt@shiftsync.no" className="text-sky-600 hover:text-sky-700 focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 rounded">
            kontakt@shiftsync.no
          </a>
        </p>
      </div>
    </div>
  )
}
