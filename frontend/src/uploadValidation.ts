import { ApiError } from './api'

export function validatePdf(file: File) {
  if (file.type !== 'application/pdf') return 'Choose a PDF with the application/pdf file type.'
  if (!file.size) return 'This PDF is empty. Choose a readable invoice.'
  if (file.size > 8 * 1024 * 1024) return 'This file exceeds 8 MiB. Choose a smaller PDF.'
  return null
}

export function uploadError(error: unknown) {
  if (!(error instanceof ApiError)) {
    return 'The connection ended before acceptance was confirmed. Check the invoice queue before selecting this PDF again.'
  }
  const messages: Record<number, string> = {
    400: 'The upload was rejected. Choose one readable PDF.',
    401: 'Sign in to the active AP Compass instance before uploading.',
    403: 'New invoice uploads are disabled or unavailable from this page. Existing runs are still available.',
    408: 'The upload timed out. Choose the PDF and try again.',
    413: 'This file exceeds 8 MiB. Choose a smaller PDF.',
    415: 'Choose a PDF with the application/pdf file type.',
    429: 'The demo is at invoice capacity. Wait for an active run to finish before uploading.',
  }
  return (
    messages[error.status] ??
    'The invoice could not be uploaded. Check the queue before trying again.'
  )
}
