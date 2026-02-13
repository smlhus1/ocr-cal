'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { apiClient, ApiError } from '@/lib/api-client'
import { validateFileSignature } from '@/lib/validation'

interface DragDropUploadProps {
  onUploadSuccess: (uploadIds: string[], method: 'ocr' | 'ai') => void
  onUploadError: (error: string) => void
  disabled?: boolean
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const ALLOWED_TYPES = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'application/pdf': ['.pdf']
}

interface FileUploadState {
  file: File
  uploadId?: string
  progress: number
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

export default function DragDropUpload({
  onUploadSuccess,
  onUploadError,
  disabled = false
}: DragDropUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [method, setMethod] = useState<'ocr' | 'ai'>('ocr')
  const [fileStates, setFileStates] = useState<FileUploadState[]>([])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    // Maks 10 filer
    if (acceptedFiles.length > 10) {
      onUploadError(`Du valgte ${acceptedFiles.length} filer. Maksimalt 10 filer om gangen.`)
      return
    }

    setUploading(true)

    // Initialize file states
    const initialStates: FileUploadState[] = acceptedFiles.map(file => ({
      file,
      progress: 0,
      status: 'pending'
    }))
    setFileStates(initialStates)

    // Upload alle filer parallelt
    const uploadPromises = acceptedFiles.map(async (file, index) => {
      try {
        // Update status to uploading
        setFileStates(prev => prev.map((state, i) =>
          i === index ? { ...state, status: 'uploading', progress: 10 } : state
        ))

        // Client-side validation: file signature
        const arrayBuffer = await file.arrayBuffer()
        const isValid = await validateFileSignature(arrayBuffer, file.type)

        if (!isValid) {
          throw new Error('Ugyldig filtype')
        }

        setFileStates(prev => prev.map((state, i) =>
          i === index ? { ...state, progress: 30 } : state
        ))

        // Upload to backend
        const response = await apiClient.upload(file)

        setFileStates(prev => prev.map((state, i) =>
          i === index ? {
            ...state,
            progress: 100,
            status: 'success',
            uploadId: response.upload_id
          } : state
        ))

        return { success: true, uploadId: response.upload_id }

      } catch (error) {
        console.error(`Upload error for ${file.name}:`, error)

        let errorMessage = 'Opplasting feilet'
        if (error instanceof ApiError) {
          if (error.statusCode === 413) errorMessage = 'For stor (maks 10MB)'
          else if (error.statusCode === 400) errorMessage = 'Ugyldig fil'
          else if (error.statusCode === 429) errorMessage = 'For mange forespørsler, vent litt'
          else if (error.statusCode === 402) errorMessage = 'Du har brukt opp gratiskvoten (2 per mnd). Oppgrader til Premium for ubegrenset bruk.'
          else errorMessage = error.detail || errorMessage
        } else {
          errorMessage = (error as Error).message || errorMessage
        }

        setFileStates(prev => prev.map((state, i) =>
          i === index ? { ...state, status: 'error', error: errorMessage } : state
        ))

        return { success: false, error: errorMessage }
      }
    })

    // Vent på at alle er ferdige
    const results = await Promise.all(uploadPromises)

    setUploading(false)

    // Samle alle vellykkede upload IDs
    const successfulUploads = results
      .filter(r => r.success && r.uploadId)
      .map(r => r.uploadId!)

    if (successfulUploads.length > 0) {
      setTimeout(() => {
        onUploadSuccess(successfulUploads, method)
      }, 500)
    } else {
      onUploadError('Ingen filer ble lastet opp. Se detaljer over.')
    }
  }, [onUploadSuccess, onUploadError, method])

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ALLOWED_TYPES,
    maxSize: MAX_FILE_SIZE,
    maxFiles: 10,
    disabled: disabled || uploading,
    multiple: true
  })

  return (
    <div className="w-full space-y-4">
      {/* Method Selector */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <label id="method-label" className="block text-sm font-medium text-gray-700 mb-3">
          Velg prosesseringsmetode:
        </label>
        <div role="radiogroup" aria-labelledby="method-label" className="grid grid-cols-2 gap-4">
          <button
            type="button"
            role="radio"
            aria-checked={method === 'ocr'}
            onClick={() => setMethod('ocr')}
            disabled={uploading}
            className={`
              relative flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all
              ${method === 'ocr'
                ? 'border-sky-500 bg-sky-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-gray-300'
              }
              ${uploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {method === 'ocr' && (
              <div className="absolute top-2 right-2">
                <svg className="w-5 h-5 text-sky-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            <svg className="w-8 h-8 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-medium text-gray-900">Standard OCR</span>
            <span className="text-xs text-green-600 font-medium mt-1">Gratis</span>
            <span className="text-xs text-gray-400 mt-0.5">Tesseract</span>
          </button>

          <button
            type="button"
            role="radio"
            aria-checked={method === 'ai'}
            onClick={() => setMethod('ai')}
            disabled={uploading}
            className={`
              relative flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all
              ${method === 'ai'
                ? 'border-purple-500 bg-purple-50 shadow-sm'
                : 'border-gray-200 bg-white hover:border-gray-300'
              }
              ${uploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `}
          >
            {method === 'ai' && (
              <div className="absolute top-2 right-2">
                <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            )}
            <svg className="w-8 h-8 mb-2 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span className="font-medium text-gray-900">AI-forbedret</span>
            <span className="text-xs text-purple-600 font-medium mt-1">Premium</span>
            <span className="text-xs text-gray-400 mt-0.5">GPT-4 Vision - Høyere nøyaktighet</span>
          </button>
        </div>
      </div>

      {/* Upload Area */}
      <div
        {...getRootProps({
          role: 'button' as const,
          'aria-label': uploading
            ? `Laster opp ${fileStates.length} filer`
            : 'Last opp filer. Klikk eller dra filer hit. Støtter JPG, PNG og PDF, maks 10MB per fil, opptil 10 filer.',
        })}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
          transition-colors duration-200
          ${isDragActive
            ? 'border-sky-500 bg-sky-50'
            : 'border-gray-300 bg-white hover:border-sky-400 hover:bg-gray-50'
          }
          ${(disabled || uploading) && 'opacity-50 cursor-not-allowed'}
        `}
      >
        <input {...getInputProps({ 'aria-label': 'Velg filer for opplasting' })} />

        {uploading ? (
          <div className="space-y-3" role="status" aria-live="polite">
            <div className="inline-flex items-center justify-center w-12 h-12 bg-sky-100 rounded-full mb-2">
              <svg className="animate-spin h-6 w-6 text-sky-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            <p className="text-lg font-medium text-gray-900">Laster opp {fileStates.length} fil(er)...</p>

            {/* Progress for hver fil */}
            <div className="space-y-2 max-w-2xl mx-auto text-left">
              {fileStates.map((fileState, index) => (
                <div key={index} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                      {fileState.file.name}
                    </span>
                    <span className="text-xs text-gray-500 ml-2">
                      {fileState.status === 'success' && (
                        <span className="text-green-600 flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          Ferdig
                        </span>
                      )}
                      {fileState.status === 'error' && (
                        <span className="text-red-600 text-xs">{fileState.error}</span>
                      )}
                      {fileState.status === 'uploading' && `${fileState.progress}%`}
                      {fileState.status === 'pending' && 'Venter...'}
                    </span>
                  </div>
                  {(fileState.status === 'uploading' || fileState.status === 'pending') && (
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-sky-600 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${fileState.progress}%` }}
                        role="progressbar"
                        aria-valuenow={fileState.progress}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`Opplasting av ${fileState.file.name}`}
                      ></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 bg-sky-100 rounded-full mb-4">
              <svg className="w-8 h-8 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>

            {isDragActive ? (
              <p className="text-lg font-medium text-sky-600">
                Slipp filene her...
              </p>
            ) : (
              <>
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Dra vaktplaner hit, eller klikk for å velge filer
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  Støtter JPG, PNG og PDF - Maks 10MB per fil - Opptil 10 filer samtidig
                </p>
                <span
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-sky-600 hover:bg-sky-700"
                  aria-hidden="true"
                >
                  Velg filer
                </span>
              </>
            )}
          </>
        )}
      </div>

      {/* File rejection errors */}
      {fileRejections.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg" role="alert">
          <p className="text-sm font-medium text-red-800 mb-1">Noen filer ble avvist:</p>
          <ul className="text-sm text-red-600 list-disc list-inside space-y-1">
            {fileRejections.map((rejection, idx) => (
              <li key={idx}>
                <span className="font-medium">{rejection.file.name}:</span>{' '}
                {rejection.errors.map((error) => {
                  if (error.code === 'file-too-large') return 'For stor (maks 10MB)'
                  if (error.code === 'file-invalid-type') return 'Ugyldig filtype (kun JPG, PNG, PDF)'
                  if (error.code === 'too-many-files') return 'For mange filer (maks 10)'
                  return error.message
                }).join(', ')}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
