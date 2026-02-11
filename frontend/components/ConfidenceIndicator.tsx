'use client'

interface ConfidenceIndicatorProps {
  score: number // 0.0 to 1.0
}

export default function ConfidenceIndicator({ score }: ConfidenceIndicatorProps) {
  const percentage = Math.round(score * 100)
  
  let colorClass = 'text-green-600 bg-green-100'
  let label = 'Høy'
  
  if (score < 0.6) {
    colorClass = 'text-red-600 bg-red-100'
    label = 'Lav'
  } else if (score < 0.8) {
    colorClass = 'text-yellow-600 bg-yellow-100'
    label = 'Moderat'
  }

  return (
    <div className="inline-flex items-center space-x-2" aria-label={`Sikkerhet: ${label} (${percentage}%)`}>
      <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`} aria-hidden="true">
        {label}
      </span>
      <span className="text-xs text-gray-500" aria-hidden="true">
        {percentage}%
      </span>
    </div>
  )
}

