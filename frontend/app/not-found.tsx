export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h2 className="text-6xl font-bold text-gray-300 mb-4">404</h2>
        <h3 className="text-2xl font-bold text-gray-900 mb-4">
          Siden ble ikke funnet
        </h3>
        <p className="text-gray-600 mb-6">
          Beklager, vi kunne ikke finne siden du leter etter.
        </p>
        <a
          href="/"
          className="inline-block px-6 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2"
        >
          Tilbake til forsiden
        </a>
      </div>
    </div>
  )
}
