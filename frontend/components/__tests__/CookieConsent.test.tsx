import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CookieConsent from '../CookieConsent'

describe('CookieConsent', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('is visible when localStorage has no cookie_consent', () => {
    render(<CookieConsent />)
    expect(screen.getByRole('region')).toBeInTheDocument()
    expect(screen.getByText(/informasjonskapsel/i)).toBeInTheDocument()
  })

  it('hides after clicking accept button', () => {
    render(<CookieConsent />)
    const button = screen.getByText('OK, forstått')
    fireEvent.click(button)
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('stores consent in localStorage', () => {
    render(<CookieConsent />)
    const spy = vi.spyOn(Storage.prototype, 'setItem')
    fireEvent.click(screen.getByText('OK, forstått'))
    expect(spy).toHaveBeenCalledWith('cookie_consent', 'accepted')
    spy.mockRestore()
  })

  it('is hidden if already accepted', () => {
    localStorage.setItem('cookie_consent', 'accepted')
    render(<CookieConsent />)
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('has accessible region role and label', () => {
    render(<CookieConsent />)
    const region = screen.getByRole('region')
    expect(region).toHaveAttribute('aria-label', 'Informasjonskapsel-samtykke')
  })
})
