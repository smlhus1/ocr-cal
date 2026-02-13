'use client'

import { Suspense, useEffect, useState } from 'react'
import { useParams, useRouter, useSearchParams } from 'next/navigation'
import ShiftTable from '@/components/ShiftTable'
import { apiClient, Shift, ProcessResponse, ApiError, downloadBlob } from '@/lib/api-client'
import { sanitizeInput } from '@/lib/validation'
import { showToast } from '@/components/Toast'

function PreviewContent() {
  const params = useParams()
  const router = useRouter()
  const searchParams = useSearchParams()
  const uploadId = params.id as string
  const method = (searchParams.get('method') || 'ocr') as 'ocr' | 'ai'

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ProcessResponse | null>(null)
  const [shifts, setShifts] = useState<Shift[]>([])
  const [ownerName, setOwnerName] = useState('')
  const [generating, setGenerating] = useState(false)
  const [hasProcessed, setHasProcessed] = useState(false)

  useEffect(() => {
    if (!hasProcessed && uploadId) {
      setHasProcessed(true)
      processUpload()
    }
  }, [uploadId, hasProcessed])

  const processUpload = async () => {
    try {
      setLoading(true)
      const response = await apiClient.process(uploadId, method)
      setData(response)
      setShifts(response.shifts)
      setLoading(false)
    } catch (err) {
      console.error('Processing error:', err)
      if (err instanceof ApiError) {
        if (err.statusCode === 404) {
          setError('Filen ble ikke funnet. Den kan ha utløpt (filer slettes etter 24 timer).')
        } else if (err.statusCode === 400) {
          setError(err.detail || 'Ugyldig forespørsel. Sjekk at AI-metoden er konfigurert riktig.')
        } else {
          setError(err.detail || 'Kunne ikke prosessere filen. Prøv igjen.')
        }
      } else {
        setError('En ukjent feil oppstod')
      }
      setLoading(false)
    }
  }

  const handleGenerateCalendar = async () => {
    if (shifts.length === 0) {
      showToast('Ingen vakter å eksportere', 'warning')
      return
    }

    if (!ownerName.trim()) {
      showToast('Vennligst skriv inn navn', 'warning')
      return
    }

    try {
      setGenerating(true)
      const sanitizedName = sanitizeInput(ownerName)

      const blob = await apiClient.generateCalendar(shifts, sanitizedName)

      const filename = `vakter_${sanitizedName.replace(/\s+/g, '_')}.ics`
      downloadBlob(blob, filename)

      setGenerating(false)

      showToast(`Kalenderfil lastet ned! Importer "${filename}" til kalender-appen din.`, 'success')

    } catch (err) {
      console.error('Calendar generation error:', err)
      if (err instanceof ApiError) {
        showToast(err.detail || 'Kunne ikke generere kalenderfil', 'error')
      } else {
        showToast('En ukjent feil oppstod', 'error')
      }
      setGenerating(false)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="text-center" role="status" aria-live="polite">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-sky-100 rounded-full mb-4">
            <svg className="animate-spin h-8 w-8 text-sky-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Prosesserer vaktplan...
          </h2>
          <p className="text-gray-600">
            Dette kan ta noen sekunder
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6" role="alert">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Prosessering feilet
              </h3>
              <div className="mt-2 text-sm text-red-700">
                {error}
              </div>
              <div className="mt-4">
                <button
                  onClick={() => router.push('/')}
                  className="text-sm font-medium text-red-800 hover:text-red-900 inline-flex items-center min-h-[44px] focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 rounded"
                >
                  ← Tilbake til start
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/')}
          className="text-sky-600 hover:text-sky-700 mb-4 inline-flex items-center"
        >
          <svg className="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Tilbake
        </button>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Forhåndsvis og Rediger Vakter
        </h1>
        <p className="text-gray-600">
          Funnet <span className="font-semibold">{shifts.length}</span> vakt{shifts.length !== 1 ? 'er' : ''}
          {data && ` (${Math.round(data.confidence * 100)}% sikkerhet)`}
        </p>
      </div>

      {/* Warnings */}
      {data && data.warnings.length > 0 && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Advarsler
              </h3>
              <div className="mt-2 text-sm text-yellow-700">
                <ul className="list-disc list-inside space-y-1">
                  {data.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Shift Table */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <ShiftTable
          initialShifts={shifts}
          onShiftsChange={setShifts}
        />
      </div>

      {/* Generate Calendar Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Generer Kalenderfil
        </h2>

        <div className="max-w-md">
          <label htmlFor="owner-name" className="block text-sm font-medium text-gray-700 mb-2">
            Navn (vises i kalenderen)
          </label>
          <input
            type="text"
            id="owner-name"
            value={ownerName}
            onChange={(e) => setOwnerName(e.target.value)}
            placeholder="F.eks. 'Anna Hansen'"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-sky-500 focus:border-sky-500"
            maxLength={100}
          />
        </div>

        <div className="mt-6 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {shifts.length} vakt{shifts.length !== 1 ? 'er' : ''} vil bli lagt til i kalenderen
          </p>

          <button
            onClick={handleGenerateCalendar}
            disabled={generating || shifts.length === 0}
            className={`
              inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white
              ${generating || shifts.length === 0
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-sky-600 hover:bg-sky-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-sky-500'
              }
            `}
          >
            {generating ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Genererer...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Last ned Kalenderfil
              </>
            )}
          </button>
        </div>
      </div>

      {/* Processing time */}
      {data && (
        <div className="mt-4 text-center text-sm text-gray-500">
          Prosessert på {data.processing_time_ms}ms
        </div>
      )}
    </div>
  )
}

export default function PreviewPage() {
  return (
    <Suspense fallback={
      <div className="max-w-6xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        <div className="text-center" role="status">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-sky-100 rounded-full mb-4">
            <svg className="animate-spin h-8 w-8 text-sky-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Laster...</h2>
        </div>
      </div>
    }>
      <PreviewContent />
    </Suspense>
  )
}
