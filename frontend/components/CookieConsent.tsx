'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'

export default function CookieConsent() {
  const [visible, setVisible] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    // Only show if user hasn't already accepted
    const accepted = localStorage.getItem('cookie_consent')
    if (!accepted) {
      setVisible(true)
    }
  }, [])

  useEffect(() => {
    if (visible && buttonRef.current) {
      buttonRef.current.focus()
    }
  }, [visible])

  const accept = () => {
    localStorage.setItem('cookie_consent', 'accepted')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      role="region"
      aria-label="Informasjonskapsel-samtykke"
      className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 shadow-lg p-4"
    >
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
        <p className="text-sm text-gray-600">
          Vi bruker en funksjonell informasjonskapsel for å holde styr på gratiskvoten din.
          Ingen sporing eller tredjepartsdeling.{' '}
          <Link href="/personvern" className="underline hover:text-gray-900 transition-colors">
            Les mer
          </Link>
        </p>
        <button
          ref={buttonRef}
          onClick={accept}
          className="shrink-0 px-4 py-2 bg-sky-600 text-white text-sm font-medium rounded hover:bg-sky-700 transition-colors focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
        >
          OK, forstått
        </button>
      </div>
    </div>
  )
}
