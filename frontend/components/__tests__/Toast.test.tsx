import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import ToastContainer, { showToast } from '../Toast'

describe('ToastContainer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('showToast displays message', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Test message', 'info')
    })

    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('success toast has green styling', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Success!', 'success')
    })

    const alert = screen.getByRole('alert')
    expect(alert.className).toContain('bg-green-600')
  })

  it('error toast has red styling', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Error!', 'error')
    })

    const alert = screen.getByRole('alert')
    expect(alert.className).toContain('bg-red-600')
  })

  it('warning toast has yellow styling', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Warning!', 'warning')
    })

    const alert = screen.getByRole('alert')
    expect(alert.className).toContain('bg-yellow-600')
  })

  it('auto-dismisses after 6 seconds', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Temporary', 'info')
    })

    expect(screen.getByText('Temporary')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(6000)
    })

    expect(screen.queryByText('Temporary')).not.toBeInTheDocument()
  })

  it('has aria-live polite region', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('Accessible', 'info')
    })

    const container = screen.getByText('Accessible').closest('[aria-live]')
    expect(container).toHaveAttribute('aria-live', 'polite')
  })

  it('can show multiple toasts', () => {
    render(<ToastContainer />)

    act(() => {
      showToast('First', 'info')
      showToast('Second', 'success')
    })

    expect(screen.getByText('First')).toBeInTheDocument()
    expect(screen.getByText('Second')).toBeInTheDocument()
  })
})
