/**
 * Type-safe API client for ShiftSync backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios'
import axiosRetry from 'axios-retry'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types matching backend Pydantic models
export interface Shift {
  id?: string // Client-side stable key for React lists
  date: string // DD.MM.YYYY
  start_time: string // HH:MM
  end_time: string // HH:MM
  shift_type: 'tidlig' | 'mellom' | 'kveld' | 'natt'
  confidence: number // 0.0 to 1.0
}

export interface UploadResponse {
  upload_id: string
  status: 'uploaded'
  expires_at: string
}

export interface ProcessRequest {
  upload_id: string
  method: 'ocr' | 'ai'
}

export interface ProcessResponse {
  shifts: Shift[]
  confidence: number
  warnings: string[]
  processing_time_ms: number
}

export interface GenerateCalendarRequest {
  shifts: Shift[]
  owner_name: string
}

export interface FeedbackRequest {
  upload_id: string
  error_type: 'wrong_date' | 'missing_shift' | 'wrong_time' | 'wrong_type' | 'other'
  correction_data?: Record<string, any>
}

export interface CreditPack {
  pack_id: string
  credits: number
  price_nok: number
  name: string
  price_per_credit: number
}

export interface CreditStatusResponse {
  has_quota: boolean
  free_remaining: number // -1 = unlimited (legacy premium)
  credits: number
  free_tier_limit: number
  credit_packs: CreditPack[]
}

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 120000, // 120 seconds for AI processing
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    axiosRetry(this.client, {
      retries: 3,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error) => {
        // Retry on rate limit and server errors
        const status = error.response?.status;
        return status === 429 || (status !== undefined && status >= 500);
      },
      onRetry: (retryCount, error) => {
        console.warn(`Retry attempt ${retryCount} for ${error.config?.url}`);
      },
    })

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          const detail = (error.response.data as any)?.detail || error.message
          throw new ApiError(
            'API request failed',
            error.response.status,
            detail
          )
        } else if (error.request) {
          throw new ApiError('No response from server', 0, 'Network error')
        } else {
          throw new ApiError('Request setup failed', 0, error.message)
        }
      }
    )
  }

  /**
   * Upload file to backend
   */
  async upload(file: File): Promise<UploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<UploadResponse>(
      '/api/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    return response.data
  }

  /**
   * Process uploaded file with OCR or AI Vision
   * Note: Uses extended timeout as AI processing can take 30-60 seconds
   */
  async process(uploadId: string, method: 'ocr' | 'ai' = 'ocr'): Promise<ProcessResponse> {
    const response = await this.client.post<ProcessResponse>(
      '/api/process',
      {
        upload_id: uploadId,
        method: method,
      },
      {
        timeout: 180000, // 3 minutes for AI/OCR processing
      }
    )

    return response.data
  }

  /**
   * Generate calendar file from shifts
   */
  async generateCalendar(
    shifts: Shift[],
    ownerName: string
  ): Promise<Blob> {
    const response = await this.client.post(
      '/api/generate-calendar',
      {
        shifts,
        owner_name: ownerName,
      },
      {
        responseType: 'blob',
      }
    )

    return response.data
  }

  /**
   * Submit feedback on OCR results
   */
  async submitFeedback(feedback: FeedbackRequest): Promise<void> {
    await this.client.post('/api/feedback', feedback)
  }

  /**
   * Get credit and quota status for current session
   */
  async getCreditStatus(): Promise<CreditStatusResponse> {
    const response = await this.client.get<CreditStatusResponse>(
      '/api/payment/credit-status'
    )
    return response.data
  }

  /**
   * Create Stripe checkout session for credit pack purchase
   */
  async createCreditCheckout(
    packId: string,
    successUrl: string,
    cancelUrl: string
  ): Promise<string> {
    const response = await this.client.post<{ checkout_url: string }>(
      '/api/payment/create-credit-checkout',
      {
        pack_id: packId,
        success_url: successUrl,
        cancel_url: cancelUrl,
      }
    )
    return response.data.checkout_url
  }

  /**
   * Download original uploaded file.
   * Fetches a short-lived download token first, then downloads with it.
   */
  async downloadOriginal(uploadId: string): Promise<Blob> {
    const encodedId = encodeURIComponent(uploadId)

    // Step 1: Get download token
    const tokenResponse = await this.client.post<{ token: string }>(
      `/api/download-token/${encodedId}`
    )
    const token = tokenResponse.data.token

    // Step 2: Download with token
    const response = await this.client.get(
      `/api/download/${encodedId}`,
      {
        params: { token },
        responseType: 'blob',
      }
    )

    return response.data
  }
}

// Singleton instance
export const apiClient = new ApiClient()

// Helper function to download blob as file
export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

