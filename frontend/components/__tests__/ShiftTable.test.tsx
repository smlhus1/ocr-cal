import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ShiftTable from '../ShiftTable'
import type { Shift } from '@/lib/api-client'

// Mock ConfidenceIndicator to simplify tests
vi.mock('../ConfidenceIndicator', () => ({
  default: ({ score }: { score: number }) => (
    <span data-testid="confidence">{Math.round(score * 100)}%</span>
  ),
}))

const mockShifts: Shift[] = [
  {
    date: '15.01.2024',
    start_time: '07:00',
    end_time: '15:00',
    shift_type: 'tidlig',
    confidence: 0.95,
  },
  {
    date: '16.01.2024',
    start_time: '15:00',
    end_time: '23:00',
    shift_type: 'kveld',
    confidence: 0.8,
  },
]

describe('ShiftTable', () => {
  it('renders all shifts', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    // Should show shift dates in inputs (desktop + mobile views both render in jsdom)
    const dateInputs = screen.getAllByPlaceholderText('DD.MM.YYYY')
    expect(dateInputs).toHaveLength(4) // 2 shifts x 2 views (desktop + mobile)
  })

  it('renders add button', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    expect(screen.getByText('Legg til vakt manuelt')).toBeInTheDocument()
  })

  it('calls onShiftsChange when adding a shift', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    fireEvent.click(screen.getByText('Legg til vakt manuelt'))

    expect(onChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ shift_type: 'tidlig', confidence: 1.0 }),
      ])
    )
    expect(onChange.mock.calls[0][0]).toHaveLength(3) // 2 original + 1 new
  })

  it('calls onShiftsChange when deleting a shift', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    // Click first delete button (desktop view)
    const deleteButtons = screen.getAllByText('Slett')
    fireEvent.click(deleteButtons[0])

    expect(onChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ date: '16.01.2024' }),
      ])
    )
    expect(onChange.mock.calls[0][0]).toHaveLength(1)
  })

  it('shows shift count', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    expect(screen.getByText('2')).toBeInTheDocument()
    // Multiple elements match /vakter/ (desktop summary + mobile labels)
    expect(screen.getAllByText(/vakter/).length).toBeGreaterThan(0)
  })

  it('renders empty state', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={[]} onShiftsChange={onChange} />)

    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('displays confidence indicators', () => {
    const onChange = vi.fn()
    render(<ShiftTable initialShifts={mockShifts} onShiftsChange={onChange} />)

    const confidences = screen.getAllByTestId('confidence')
    expect(confidences.length).toBeGreaterThan(0)
  })
})
