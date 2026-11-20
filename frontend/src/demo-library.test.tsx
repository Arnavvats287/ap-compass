import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import DemoDataLibrary from './DemoDataLibrary'

it('offers only the curated PDF downloads and a single sample ZIP', async () => {
  const { container } = render(<DemoDataLibrary />)
  const opener = screen.getByRole('button', { name: 'Explore demo data' })
  const dialog = container.querySelector('dialog')!
  dialog.showModal = vi.fn(() => dialog.setAttribute('open', ''))
  dialog.close = vi.fn(() => {
    dialog.removeAttribute('open')
    fireEvent(dialog, new Event('close'))
  })

  await userEvent.click(opener)

  const library = within(screen.getByRole('dialog', { name: 'Explore demo data' }))
  expect(library.getByRole('link', { name: 'Download collection ZIP' })).toHaveAttribute(
    'href',
    '/demo-data/ap-compass-demo-invoices.zip',
  )
  const links = library.getAllByRole('link', { name: /Download PDF/ })
  expect(links.map((link) => link.getAttribute('download'))).toEqual([
    'NS-26-5942.pdf',
    'KLG-2611-876.pdf',
    'AS-2611-632.pdf',
    'MCL-26-4681.pdf',
    'MCL-26-4573.pdf',
    '08-northstar-supplies.pdf',
    'OOP-2611-617.pdf',
  ])
  for (const link of links) {
    expect(link).toHaveAttribute('href', '/demo-data/' + link.getAttribute('download'))
  }
  await userEvent.click(library.getByRole('button', { name: 'Close demo data' }))

  expect(dialog).not.toHaveAttribute('open')
  expect(opener).toHaveFocus()
})
