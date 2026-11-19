import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import BatchUpload, { BatchUploadProvider } from './BatchUpload'
import ExportInvoices from './ExportInvoices'
import { api, ApiError } from './api'
import { run } from './test/fixtures'
import type { Run } from './types'

const pdf = (name: string) => new File(['%PDF-test'], name, { type: 'application/pdf' })

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/runs/upload']}>
        <BatchUploadProvider>
          <Routes>
            <Route path="/runs/upload" element={<BatchUpload />} />
          </Routes>
        </BatchUploadProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { invalidate }
}

const choose = (files: File[]) => userEvent.upload(screen.getByLabelText('Invoice PDFs'), files)
const start = () => screen.getByRole('button', { name: 'Process selected invoices' })
const result = (name: string) => within(screen.getByText(name).closest('li')!)

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

it('accepts multiple files, ignores duplicate selections, supports drag and allows keyboard removal', async () => {
  setup()
  const first = pdf('first.pdf')
  await choose([first, pdf('second.pdf')])
  await choose([first])
  expect(screen.getByRole('alert')).toHaveTextContent('already selected')
  fireEvent.drop(screen.getByText('Drop invoice PDFs here').parentElement!, {
    dataTransfer: { files: [pdf('third.pdf')] },
  })
  expect(
    within(screen.getByRole('list', { name: 'Selected invoices' })).getAllByRole('listitem'),
  ).toHaveLength(3)
  const remove = screen.getByRole('button', { name: 'Remove second.pdf' })
  remove.focus()
  await userEvent.keyboard('{Enter}')
  expect(screen.queryByText('second.pdf')).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Choose PDFs' })).toHaveFocus()
  expect(start()).toBeEnabled()
})

it('rejects non-PDF, empty and oversized files without blocking valid PDFs in the same drop', () => {
  const upload = vi.spyOn(api, 'upload')
  setup()
  fireEvent.drop(screen.getByText('Drop invoice PDFs here').parentElement!, {
    dataTransfer: {
      files: [
        new File(['a'], 'wrong.txt', { type: 'text/plain' }),
        new File([], 'empty.pdf', { type: 'application/pdf' }),
        new File([new Uint8Array(8 * 1024 * 1024 + 1)], 'large.pdf', { type: 'application/pdf' }),
        pdf('okay.pdf'),
      ],
    },
  })
  expect(screen.getByRole('alert')).toHaveTextContent(/wrong.txt.*empty.pdf.*large.pdf/)
  expect(screen.getByText('okay.pdf')).toBeInTheDocument()
  expect(upload).not.toHaveBeenCalled()
})

it('waits for each persisted terminal state, skips a 429, and refreshes both data views without resubmission', async () => {
  const upload = vi
    .spyOn(api, 'upload')
    .mockResolvedValueOnce({ run_id: 'first', execution_state: 'QUEUED' })
    .mockRejectedValueOnce(new ApiError(429))
    .mockResolvedValueOnce({ run_id: 'last', execution_state: 'QUEUED' })
  let finish!: (snapshot: Run) => void
  vi.spyOn(api, 'run').mockImplementation((id) =>
    id === 'first'
      ? new Promise((resolve) => {
          finish = resolve
        })
      : Promise.resolve({
          ...run,
          execution_state: 'PROCESSING_FAILED',
          execution_error_code: 'INVALID_PDF',
          decision: null,
        }),
  )
  const { invalidate } = setup()
  await choose([pdf('first.pdf'), pdf('capacity.pdf'), pdf('last.pdf')])
  const submit = start()
  act(() => {
    submit.click()
    submit.click()
  })
  await waitFor(() => expect(result('first.pdf').getByText('Queued')).toBeInTheDocument())
  expect(upload).toHaveBeenCalledTimes(1)
  expect(result('last.pdf').getByText('Waiting')).toBeInTheDocument()
  await act(async () => finish(run))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('3 of 3 finished'))
  expect(upload.mock.calls.map(([file]) => file.name)).toEqual([
    'first.pdf',
    'capacity.pdf',
    'last.pdf',
  ])
  expect(result('first.pdf').getByText('Blocked')).toBeInTheDocument()
  expect(result('first.pdf').getByRole('link')).toHaveAttribute('href', '/runs/first')
  expect(result('capacity.pdf').getByText('Upload failed')).toBeInTheDocument()
  expect(result('capacity.pdf').getByText(/invoice capacity/)).toBeInTheDocument()
  expect(result('last.pdf').getByText('Processing failed')).toBeInTheDocument()
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['runs'] })
  expect(invalidate).toHaveBeenCalledWith({ queryKey: ['dashboard'] })
})

it('downloads the returned workbook and shows progress and failures', async () => {
  const open = vi.fn(() => 'blob:workbook')
  vi.stubGlobal(
    'URL',
    class extends URL {
      static createObjectURL = open
      static revokeObjectURL = vi.fn()
    },
  )
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    expect(this.download).toBe('register.xlsx')
  })
  let ready!: (value: Awaited<ReturnType<typeof api.exportInvoices>>) => void
  vi.spyOn(api, 'exportInvoices')
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          ready = resolve
        }),
    )
    .mockRejectedValueOnce(new ApiError(503))
  render(<ExportInvoices />)
  await userEvent.click(screen.getByRole('button', { name: 'Export Excel' }))
  expect(screen.getByRole('button', { name: 'Preparing Excel…' })).toBeDisabled()
  await act(async () => ready({ blob: new Blob(['xlsx']), filename: 'register.xlsx' }))
  expect(screen.getByRole('status')).toHaveTextContent('Excel download started.')
  expect(open).toHaveBeenCalledTimes(1)
  expect(click).toHaveBeenCalledTimes(1)
  await userEvent.click(screen.getByRole('button', { name: 'Export Excel' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be downloaded')
})
