import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConfidenceIndicator from '../ConfidenceIndicator'

describe('ConfidenceIndicator', () => {
  it('shows high confidence green for score >= 0.8', () => {
    render(<ConfidenceIndicator score={0.95} />)
    expect(screen.getByText('Høy')).toBeInTheDocument()
    expect(screen.getByText('95%')).toBeInTheDocument()
  })

  it('shows moderate confidence yellow for 0.6 <= score < 0.8', () => {
    render(<ConfidenceIndicator score={0.7} />)
    expect(screen.getByText('Moderat')).toBeInTheDocument()
    expect(screen.getByText('70%')).toBeInTheDocument()
  })

  it('shows low confidence red for score < 0.6', () => {
    render(<ConfidenceIndicator score={0.4} />)
    expect(screen.getByText('Lav')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
  })

  it('boundary 0.8 is high', () => {
    render(<ConfidenceIndicator score={0.8} />)
    expect(screen.getByText('Høy')).toBeInTheDocument()
  })

  it('boundary 0.6 is moderate', () => {
    render(<ConfidenceIndicator score={0.6} />)
    expect(screen.getByText('Moderat')).toBeInTheDocument()
  })

  it('displays percentage correctly', () => {
    render(<ConfidenceIndicator score={0.87} />)
    expect(screen.getByText('87%')).toBeInTheDocument()
  })

  it('has accessibility label with score and label', () => {
    render(<ConfidenceIndicator score={0.95} />)
    const container = screen.getByLabelText(/Sikkerhet:.*Høy.*95%/)
    expect(container).toBeInTheDocument()
  })

  it('rounds percentage correctly', () => {
    render(<ConfidenceIndicator score={0.556} />)
    expect(screen.getByText('56%')).toBeInTheDocument()
  })
})
