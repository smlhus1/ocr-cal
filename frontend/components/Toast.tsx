'use client'

import { useEffect, useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastMessage {
  id: number
  message: string
  type: ToastType
}

let toastId = 0
let addToastFn: ((message: string, type: ToastType) => void) | null = null

/**
 * Show a toast notification from anywhere in the app.
 */
export function showToast(message: string, type: ToastType = 'info') {
  if (addToastFn) {
    addToastFn(message, type)
  }
}

const TYPE_STYLES: Record<ToastType, string> = {
  success: 'bg-green-600',
  error: 'bg-red-600',
  warning: 'bg-yellow-600',
  info: 'bg-sky-600',
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])

    // Errors stay longer, other types auto-dismiss after 6s
    const timeout = type === 'error' ? 10000 : 6000
    setTimeout(() => {
      removeToast(id)
    }, timeout)
  }, [removeToast])

  useEffect(() => {
    addToastFn = addToast
    return () => { addToastFn = null }
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div
      aria-live="polite"
      role="log"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    >
      {toasts.map(toast => (
        <div
          key={toast.id}
          role="alert"
          className={`${TYPE_STYLES[toast.type]} text-white px-4 py-3 rounded-lg shadow-lg text-sm animate-slide-in flex items-center justify-between gap-2`}
        >
          <span>{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            aria-label="Lukk melding"
            className="shrink-0 p-1 rounded hover:bg-white/20 focus-visible:ring-2 focus-visible:ring-white"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  )
}
