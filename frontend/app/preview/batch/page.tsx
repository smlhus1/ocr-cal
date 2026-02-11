'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import ShiftTable from '@/components/ShiftTable'
import { apiClient, Shift, ProcessResponse, ApiError, downloadBlob } from '@/lib/api-client'
import { sanitizeInput } from '@/lib/validation'
import { showToast } from '@/components/Toast'

interface FileProcessingState {
  uploadId: string
  status: 'pending' | 'processing' | 'success' | 'error'
  shifts: Shift[]
  confidence: number
  warnings: string[]
  error?: string
  processingTime?: number
}

export default function BatchPreviewPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const idsParam = searchParams.get('ids') || ''
  const method = (searchParams.get('method') || 'ocr') as 'ocr' | 'ai'
  
  const uploadIds = idsParam.split(',').filter(id => id.length > 0)

  const [processing, setProcessing] = useState(true)
  const [fileStates, setFileStates] = useState<FileProcessingState[]>([])
  const [allShifts, setAllShifts] = useState<Shift[]>([])
  const [ownerName, setOwnerName] = useState('')
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (uploadIds.length === 0) {
      router.push('/')
      return
    }

    // Initialize file states
    const initialStates: FileProcessingState[] = uploadIds.map(id => ({
      uploadId: id,
      status: 'pending',
      shifts: [],
      confidence: 0,
      warnings: []
    }))
    setFileStates(initialStates)

    // Process all files
    processAllFiles()
  }, [])

  const processAllFiles = async () => {
    console.log(`🚀 [ShiftSync Batch] Prosesserer ${uploadIds.length} filer med metode: ${method.toUpperCase()}`)
    
    // Process each file sequentially to avoid overwhelming the backend
    for (let i = 0; i < uploadIds.length; i++) {
      const uploadId = uploadIds[i]
      
      // Update status to processing
      setFileStates(prev => prev.map((state, idx) => 
        idx === i ? { ...state, status: 'processing' } : state
      ))

      try {
        console.log(`📋 [ShiftSync] Prosesserer fil ${i + 1}/${uploadIds.length}: ${uploadId}`)
        
        const startTime = Date.now()
        const response = await apiClient.process(uploadId, method)
        const duration = Date.now() - startTime
        
        console.log(`✅ [ShiftSync] Fil ${i + 1} fullført: ${response.shifts.length} vakter (${duration}ms)`)
        
        // Update state with success
        setFileStates(prev => prev.map((state, idx) => 
          idx === i ? {
            ...state,
            status: 'success',
            shifts: response.shifts,
            confidence: response.confidence,
            warnings: response.warnings,
            processingTime: duration
          } : state
        ))

        // Add shifts to combined list
        setAllShifts(prev => [...prev, ...response.shifts])

      } catch (err) {
        console.error(`❌ [ShiftSync] Feil i fil ${i + 1}:`, err)
        
        let errorMessage = 'Prosessering feilet'
        if (err instanceof ApiError) {
          console.error(`❌ [ShiftSync] Status: ${err.statusCode}`)
          console.error(`❌ [ShiftSync] Detaljer: ${err.detail}`)
          errorMessage = err.detail || errorMessage
        }
        
        // Update state with error
        setFileStates(prev => prev.map((state, idx) => 
          idx === i ? {
            ...state,
            status: 'error',
            error: errorMessage
          } : state
        ))
      }
    }

    setProcessing(false)
    console.log(`✅ [ShiftSync Batch] Alle filer prosessert. Totalt ${allShifts.length} vakter funnet.`)
  }

  const handleShiftsChange = (updatedShifts: Shift[]) => {
    setAllShifts(updatedShifts)
  }

  const handleGenerateCalendar = async () => {
    const sanitizedName = sanitizeInput(ownerName.trim() || 'Ansatt')

    try {
      setGenerating(true)
      const blob = await apiClient.generateCalendar(allShifts, sanitizedName)
      downloadBlob(blob, 'vakter.ics')
      showToast('Kalenderfil lastet ned!', 'success')
    } catch (error) {
      console.error('Calendar generation error:', error)
      if (error instanceof ApiError) {
        showToast(error.detail || 'Kunne ikke generere kalender. Prøv igjen.', 'error')
      } else {
        showToast('En ukjent feil oppstod', 'error')
      }
    } finally {
      setGenerating(false)
    }
  }

  const successCount = fileStates.filter(s => s.status === 'success').length
  const errorCount = fileStates.filter(s => s.status === 'error').length
  const avgConfidence = fileStates
    .filter(s => s.status === 'success')
    .reduce((sum, s) => sum + s.confidence, 0) / Math.max(successCount, 1)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push('/')}
          className="text-sky-600 hover:text-sky-700 mb-4 flex items-center"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Tilbake
        </button>
        <h1 className="text-3xl font-bold text-gray-900">
          Batch-prosessering: {uploadIds.length} filer
        </h1>
        <p className="text-gray-600 mt-2">
          Metode: {method === 'ai' ? '🤖 AI-forbedret (GPT-4 Vision)' : '📝 Standard OCR (Tesseract)'}
        </p>
      </div>

      {/* Processing Status */}
      {processing && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-center mb-4">
            <svg className="animate-spin h-6 w-6 text-sky-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <h2 className="text-xl font-semibold text-gray-900">Prosesserer filer...</h2>
          </div>
          
          <div className="space-y-2">
            {fileStates.map((state, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="text-sm text-gray-700">Fil {idx + 1}</span>
                <span className="text-xs">
                  {state.status === 'pending' && '⏳ Venter...'}
                  {state.status === 'processing' && '⚙️ Prosesserer...'}
                  {state.status === 'success' && `✅ ${state.shifts.length} vakter`}
                  {state.status === 'error' && `❌ ${state.error}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {!processing && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Totalt vakter</div>
            <div className="text-2xl font-bold text-gray-900">{allShifts.length}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Vellykkede</div>
            <div className="text-2xl font-bold text-green-600">{successCount}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Feilet</div>
            <div className="text-2xl font-bold text-red-600">{errorCount}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">Gjennomsnittlig sikkerhet</div>
            <div className="text-2xl font-bold text-gray-900">{Math.round(avgConfidence * 100)}%</div>
          </div>
        </div>
      )}

      {/* Combined Shift Table */}
      {!processing && allShifts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Alle vakter ({allShifts.length})
          </h2>
          <ShiftTable
            initialShifts={allShifts}
            onShiftsChange={handleShiftsChange}
          />
        </div>
      )}

      {/* Generate Calendar */}
      {!processing && allShifts.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Generer kalender
          </h2>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label htmlFor="ownerName" className="block text-sm font-medium text-gray-700 mb-2">
                Ditt navn (valgfritt)
              </label>
              <input
                type="text"
                id="ownerName"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                placeholder="Ola Nordmann"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <button
              onClick={handleGenerateCalendar}
              disabled={generating}
              className="px-6 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {generating ? (
                <>
                  <svg className="animate-spin h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Genererer...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Last ned kalender (.ics)
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* No shifts found */}
      {!processing && allShifts.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-900 mb-2">
            Ingen vakter funnet
          </h3>
          <p className="text-yellow-800">
            Kunne ikke finne noen vakter i de opplastede filene. Dette kan skyldes dårlig bildekvalitet eller et format vi ikke støtter ennå.
          </p>
          <button
            onClick={() => router.push('/')}
            className="mt-4 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700"
          >
            Prøv igjen
          </button>
        </div>
      )}
    </div>
  )
}
