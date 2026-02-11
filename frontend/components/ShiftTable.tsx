'use client'

import { useState, useEffect } from 'react'
import { Shift } from '@/lib/api-client'
import ConfidenceIndicator from './ConfidenceIndicator'

interface ShiftTableProps {
  initialShifts: Shift[]
  onShiftsChange: (shifts: Shift[]) => void
}

export default function ShiftTable({ initialShifts, onShiftsChange }: ShiftTableProps) {
  const [shifts, setShifts] = useState<Shift[]>(initialShifts)
  const [editingIndex, setEditingIndex] = useState<number | null>(null)

  // Sync internal state when props change (critical for batch mode)
  useEffect(() => {
    setShifts(initialShifts)
  }, [initialShifts])

  const updateShift = (index: number, field: keyof Shift, value: string) => {
    const newShifts = [...shifts]
    newShifts[index] = { ...newShifts[index], [field]: value }
    setShifts(newShifts)
    onShiftsChange(newShifts)
  }

  const deleteShift = (index: number) => {
    const newShifts = shifts.filter((_, i) => i !== index)
    setShifts(newShifts)
    onShiftsChange(newShifts)
  }

  const addShift = () => {
    const newShift: Shift = {
      date: new Date().toLocaleDateString('no-NO', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }).replace(/\//g, '.'),
      start_time: '07:00',
      end_time: '15:00',
      shift_type: 'tidlig',
      confidence: 1.0
    }
    const newShifts = [...shifts, newShift]
    setShifts(newShifts)
    onShiftsChange(newShifts)
    setEditingIndex(newShifts.length - 1)
  }

  return (
    <div className="space-y-4">
      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Dato
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Start
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Slutt
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Sikkerhet
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Handlinger
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {shifts.map((shift, idx) => (
              <tr
                key={idx}
                className={`
                  ${shift.confidence < 0.6 ? 'bg-yellow-50' : shift.confidence < 0.8 ? 'bg-blue-50' : ''}
                  hover:bg-gray-50 transition-colors
                `}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="text"
                    value={shift.date}
                    onChange={(e) => updateShift(idx, 'date', e.target.value)}
                    className="w-28 px-2 py-1 border border-gray-300 rounded focus:ring-sky-500 focus:border-sky-500"
                    placeholder="DD.MM.YYYY"
                    aria-label={`Dato for vakt ${idx + 1}`}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="time"
                    value={shift.start_time}
                    onChange={(e) => updateShift(idx, 'start_time', e.target.value)}
                    className="w-24 px-2 py-1 border border-gray-300 rounded focus:ring-sky-500 focus:border-sky-500"
                    aria-label={`Starttid for vakt ${idx + 1}`}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="time"
                    value={shift.end_time}
                    onChange={(e) => updateShift(idx, 'end_time', e.target.value)}
                    className="w-24 px-2 py-1 border border-gray-300 rounded focus:ring-sky-500 focus:border-sky-500"
                    aria-label={`Sluttid for vakt ${idx + 1}`}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <select
                    value={shift.shift_type}
                    onChange={(e) => updateShift(idx, 'shift_type', e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded focus:ring-sky-500 focus:border-sky-500 capitalize"
                    aria-label={`Vakttype for vakt ${idx + 1}`}
                  >
                    <option value="tidlig">Tidlig</option>
                    <option value="mellom">Mellom</option>
                    <option value="kveld">Kveld</option>
                    <option value="natt">Natt</option>
                  </select>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <ConfidenceIndicator score={shift.confidence} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => deleteShift(idx)}
                    className="text-red-600 hover:text-red-900 focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 rounded"
                    aria-label={`Slett vakt ${idx + 1} (${shift.date})`}
                  >
                    Slett
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden space-y-4">
        {shifts.map((shift, idx) => (
          <div
            key={idx}
            className={`
              border rounded-lg p-4
              ${shift.confidence < 0.6 ? 'bg-yellow-50 border-yellow-200' : shift.confidence < 0.8 ? 'bg-blue-50 border-blue-200' : 'bg-white border-gray-200'}
            `}
          >
            <div className="flex justify-between items-start mb-3">
              <ConfidenceIndicator score={shift.confidence} />
              <button
                onClick={() => deleteShift(idx)}
                className="text-red-600 hover:text-red-900 text-sm focus-visible:ring-2 focus-visible:ring-red-500 rounded"
                aria-label={`Slett vakt ${idx + 1} (${shift.date})`}
              >
                Slett
              </button>
            </div>

            <div className="space-y-2">
              <div>
                <label htmlFor={`mobile-date-${idx}`} className="text-xs text-gray-500">Dato</label>
                <input
                  id={`mobile-date-${idx}`}
                  type="text"
                  value={shift.date}
                  onChange={(e) => updateShift(idx, 'date', e.target.value)}
                  className="w-full px-2 py-1 border border-gray-300 rounded"
                  placeholder="DD.MM.YYYY"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label htmlFor={`mobile-start-${idx}`} className="text-xs text-gray-500">Start</label>
                  <input
                    id={`mobile-start-${idx}`}
                    type="time"
                    value={shift.start_time}
                    onChange={(e) => updateShift(idx, 'start_time', e.target.value)}
                    className="w-full px-2 py-1 border border-gray-300 rounded"
                  />
                </div>
                <div>
                  <label htmlFor={`mobile-end-${idx}`} className="text-xs text-gray-500">Slutt</label>
                  <input
                    id={`mobile-end-${idx}`}
                    type="time"
                    value={shift.end_time}
                    onChange={(e) => updateShift(idx, 'end_time', e.target.value)}
                    className="w-full px-2 py-1 border border-gray-300 rounded"
                  />
                </div>
              </div>

              <div>
                <label htmlFor={`mobile-type-${idx}`} className="text-xs text-gray-500">Type</label>
                <select
                  id={`mobile-type-${idx}`}
                  value={shift.shift_type}
                  onChange={(e) => updateShift(idx, 'shift_type', e.target.value)}
                  className="w-full px-2 py-1 border border-gray-300 rounded capitalize"
                >
                  <option value="tidlig">Tidlig</option>
                  <option value="mellom">Mellom</option>
                  <option value="kveld">Kveld</option>
                  <option value="natt">Natt</option>
                </select>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add shift button */}
      <div className="flex justify-center pt-4">
        <button
          onClick={addShift}
          className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-sky-500"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Legg til vakt manuelt
        </button>
      </div>

      {/* Summary */}
      <div className="mt-4 text-sm text-gray-600 text-center">
        Totalt: <span className="font-semibold">{shifts.length}</span> vakt{shifts.length !== 1 ? 'er' : ''}
      </div>
    </div>
  )
}
