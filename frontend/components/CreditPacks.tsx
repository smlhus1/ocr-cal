'use client'

import { useState } from 'react'
import { apiClient, CreditPack } from '@/lib/api-client'

const PACKS: CreditPack[] = [
  {
    pack_id: 'pack_5',
    credits: 5,
    price_nok: 39,
    name: '5-pack',
    price_per_credit: 7.80,
  },
  {
    pack_id: 'pack_15',
    credits: 15,
    price_nok: 89,
    name: '15-pack',
    price_per_credit: 5.93,
  },
  {
    pack_id: 'pack_50',
    credits: 50,
    price_nok: 249,
    name: '50-pack',
    price_per_credit: 4.98,
  },
]

export default function CreditPacks() {
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleBuy = async (packId: string) => {
    setLoading(packId)
    setError(null)

    try {
      const successUrl = `${window.location.origin}/?payment=success`
      const cancelUrl = `${window.location.origin}/?payment=cancelled`
      const checkoutUrl = await apiClient.createCreditCheckout(packId, successUrl, cancelUrl)
      window.location.href = checkoutUrl
    } catch {
      setError('Kunne ikke opprette betalingssesjon. Prøv igjen.')
      setLoading(null)
    }
  }

  return (
    <div id="pricing">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {PACKS.map((pack, index) => {
          const isPopular = index === 1
          return (
            <div
              key={pack.pack_id}
              className={`
                rounded-lg p-6 bg-white relative
                ${isPopular
                  ? 'border-2 border-purple-400 shadow-md'
                  : 'border border-gray-200'
                }
              `}
            >
              {isPopular && (
                <div className="absolute -top-3 left-4 bg-purple-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                  Mest populær
                </div>
              )}
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900">{pack.name}</h3>
                <div className="mt-2">
                  <span className="text-3xl font-bold text-gray-900">{pack.price_nok} kr</span>
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {pack.price_per_credit.toFixed(2)} kr per konvertering
                </p>
              </div>

              <ul className="space-y-2 text-sm text-gray-600 mb-6">
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  {pack.credits} konverteringer
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  AI OCR (GPT-4 Vision)
                </li>
                <li className="flex items-center">
                  <svg className="w-4 h-4 text-purple-500 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                  Utløper aldri
                </li>
              </ul>

              <button
                onClick={() => handleBuy(pack.pack_id)}
                disabled={loading !== null}
                className={`
                  w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-colors
                  ${isPopular
                    ? 'bg-purple-600 text-white hover:bg-purple-700 disabled:bg-purple-300'
                    : 'bg-gray-900 text-white hover:bg-gray-800 disabled:bg-gray-400'
                  }
                  disabled:cursor-not-allowed
                `}
              >
                {loading === pack.pack_id ? 'Sender til betaling...' : 'Kjøp nå'}
              </button>
            </div>
          )
        })}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700" role="alert">
          {error}
        </div>
      )}

      {/* Free tier info */}
      <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
        <p className="text-sm text-gray-600">
          <span className="font-medium text-gray-900">Alltid gratis:</span>
          {' '}2 konverteringer per måned med standard OCR. Ingen registrering nødvendig.
        </p>
      </div>
    </div>
  )
}
