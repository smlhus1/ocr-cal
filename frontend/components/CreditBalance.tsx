'use client'

import { useEffect, useState } from 'react'
import { apiClient, CreditStatusResponse } from '@/lib/api-client'

export default function CreditBalance() {
  const [status, setStatus] = useState<CreditStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.getCreditStatus()
      .then(setStatus)
      .catch(() => {/* Ignore - non-critical */})
      .finally(() => setLoading(false))
  }, [])

  if (loading || !status) return null

  const isPremium = status.free_remaining === -1

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {isPremium ? (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
            Premium
          </span>
        ) : (
          <>
            <div className="text-sm text-gray-600">
              <span className="font-medium text-gray-900">{status.free_remaining}</span>
              {' '}gratis igjen denne mnd
            </div>
            {status.credits > 0 && (
              <div className="text-sm text-gray-600 border-l border-gray-200 pl-4">
                <span className="font-medium text-purple-700">{status.credits}</span>
                {' '}kreditter
              </div>
            )}
          </>
        )}
      </div>
      {!isPremium && status.credits === 0 && status.free_remaining <= 1 && (
        <a
          href="#pricing"
          className="text-sm font-medium text-purple-600 hover:text-purple-800"
        >
          Kjop kreditter
        </a>
      )}
    </div>
  )
}
