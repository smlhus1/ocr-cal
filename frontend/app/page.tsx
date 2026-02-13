import UploadSection from '@/components/UploadSection'

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Fra Vaktplan til Kalender på 60 Sekunder
        </h1>
        <p className="text-xl text-gray-600 mb-2">
          Last opp bilde av vaktplanen din, vi konverterer den til iCalendar-format
        </p>
        <p className="text-sm text-gray-500">
          Støtter bilder (JPG, PNG) og PDF-filer
        </p>
      </div>

      {/* Upload (Client Component) */}
      <UploadSection />

      {/* Pricing */}
      <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border border-gray-200 rounded-lg p-6 bg-white">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Gratis</h3>
            <span className="text-2xl font-bold text-gray-900">0 kr</span>
          </div>
          <p className="text-sm text-gray-500 mb-4">per mnd</p>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-center">
              <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              2 konverteringer per mnd
            </li>
            <li className="flex items-center">
              <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Standard OCR (Tesseract)
            </li>
            <li className="flex items-center">
              <svg className="w-4 h-4 text-green-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Rediger vakter manuelt
            </li>
          </ul>
        </div>
        <div className="border-2 border-purple-400 rounded-lg p-6 bg-purple-50 relative">
          <div className="absolute -top-3 left-4 bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-full">
            Anbefalt
          </div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-900">Premium</h3>
            <span className="text-2xl font-bold text-gray-900">99 kr</span>
          </div>
          <p className="text-sm text-gray-500 mb-4">per mnd</p>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-center">
              <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Ubegrenset konverteringer
            </li>
            <li className="flex items-center">
              <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              AI-forbedret OCR (GPT-4 Vision)
            </li>
            <li className="flex items-center">
              <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Batch-opplasting (opptil 10 filer)
            </li>
            <li className="flex items-center">
              <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Prioritert prosessering
            </li>
          </ul>
        </div>
      </div>

      {/* Features */}
      <h2 className="sr-only">Funksjoner</h2>
      <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="text-center">
          <div className="bg-sky-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">Sikker & Privat</h3>
          <p className="text-gray-600 text-sm">
            Filene dine slettes automatisk etter 24 timer. GDPR-compliant.
          </p>
        </div>

        <div className="text-center">
          <div className="bg-sky-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">Lynrask OCR</h3>
          <p className="text-gray-600 text-sm">
            Avansert tekstgjenkjenning med norsk språkstøtte.
          </p>
        </div>

        <div className="text-center">
          <div className="bg-sky-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-2">Smart Redigering</h3>
          <p className="text-gray-600 text-sm">
            Forhåndsvis og rediger vakter før du laster ned.
          </p>
        </div>
      </div>

      {/* Tips */}
      <div className="mt-12 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-3">
          Tips for beste resultat:
        </h3>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start">
            <svg className="w-5 h-5 text-blue-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Ta bildet i godt lys og unngå refleksjoner
          </li>
          <li className="flex items-start">
            <svg className="w-5 h-5 text-blue-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Hold kameraet rett foran (ikke skrått)
          </li>
          <li className="flex items-start">
            <svg className="w-5 h-5 text-blue-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Sørg for at all tekst er skarp og lesbar
          </li>
        </ul>
      </div>
    </div>
  )
}
