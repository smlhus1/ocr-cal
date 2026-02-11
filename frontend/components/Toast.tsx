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

  const addToast = useCallback((message: string, type: ToastType) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])

    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }, [])

  useEffect(() => {
    addToastFn = addToast
    return () => { addToastFn = null }
  }, [addToast])

  if (toasts.length === 0) return null

  return (
    <div
      aria-live="assertive"
      className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
    >
      {toasts.map(toast => (
        <div
          key={toast.id}
          role="alert"
          className={`${TYPE_STYLES[toast.type]} text-white px-4 py-3 rounded-lg shadow-lg text-sm animate-slide-in`}
        >
          {toast.message}
        </div>
      ))}
    </div>
  )
}
