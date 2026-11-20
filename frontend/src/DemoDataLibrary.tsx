import { useId, useRef } from 'react'
import { Archive, Download, FileText, X } from 'lucide-react'
import './demo-data.css'

const root = '/demo-data/'
const bundle = 'ap-compass-demo-invoices.zip'

const samples = [
  {
    file: 'NS-26-5942.pdf',
    supplier: 'Northstar Supplies',
    scenario: 'Clean invoice',
    description: 'Match a partial shipment of chairs to its approved order.',
    current: true,
  },
  {
    file: 'KLG-2611-876.pdf',
    supplier: 'Kaveri Logistics',
    scenario: 'Unauthorized charge',
    description: 'Identify a waiting surcharge that falls outside the purchase order.',
    current: true,
  },
  {
    file: 'AS-2611-632.pdf',
    supplier: 'Aster Systems',
    scenario: 'Purchase order overrun',
    description: 'Check charges and units against the remaining authorized commitment.',
    current: false,
  },
  {
    file: 'MCL-26-4681.pdf',
    supplier: 'Meridian Cloud Pvt Ltd',
    scenario: 'Image-only scan',
    description: 'See why a degraded purchase order reference may need human review.',
    current: true,
  },
  {
    file: 'MCL-26-4573.pdf',
    supplier: 'Meridian Cloud Pvt Ltd',
    scenario: 'Unit-price variance',
    description: 'Examine a rate 3% above the approved price. Evidence checks still apply.',
    current: false,
  },
  {
    file: 'brightpath-advisory-049.pdf',
    supplier: 'Brightpath Consulting',
    scenario: 'Conflicting payable totals',
    description: 'Compare the invoice payable with a competing amount in its payment advice.',
    current: true,
  },
  {
    file: '08-northstar-supplies.pdf',
    supplier: 'Northstar Supplies',
    scenario: 'Previously billed invoice',
    description: 'Compare a reissued invoice with an existing record in the billed ledger.',
    current: true,
  },
  {
    file: 'OOP-2611-617.pdf',
    supplier: 'Orion Office Products',
    scenario: 'Clean invoice',
    description: 'Check an itemized office supplies invoice against its purchase order.',
    current: false,
  },
] as const

export default function DemoDataLibrary() {
  const title = useId()
  const notice = useId()
  const dialog = useRef<HTMLDialogElement>(null)
  const opener = useRef<HTMLButtonElement>(null)

  return (
    <>
      <button
        ref={opener}
        type="button"
        className="button quiet demo-library-trigger"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
      >
        <Archive size={16} aria-hidden="true" /> Explore demo data
      </button>
      <dialog
        ref={dialog}
        className="demo-library"
        aria-labelledby={title}
        aria-describedby={notice}
        onClose={() => opener.current?.focus({ preventScroll: true })}
      >
        <div className="demo-library-header">
          <div>
            <h2 id={title}>Explore demo data</h2>
            <p id={notice}>
              These are synthetic demonstration invoices. Results depend on the recorded policy and
              available procurement data. Repeated uploads may be flagged as duplicates.
            </p>
          </div>
          <button
            type="button"
            className="demo-library-close"
            aria-label="Close demo data"
            onClick={() => dialog.current?.close()}
          >
            <X size={21} aria-hidden="true" />
          </button>
        </div>
        <a className="button primary demo-library-download" href={root + bundle} download={bundle}>
          <Download size={16} aria-hidden="true" /> Download collection ZIP
        </a>
        <details className="demo-library-collection" open>
          <summary>
            <span>Recommended live-tested examples</span>
            <small>{samples.length} PDFs</small>
          </summary>
          <ul>
            {samples.map(({ file, supplier, scenario, description, current }) => (
              <li key={file}>
                <FileText className="demo-library-file-icon" size={18} aria-hidden="true" />
                <div className="demo-library-file">
                  <strong>{scenario}</strong>
                  <span>
                    {supplier} · {file}
                  </span>
                  <p>{description}</p>
                  <small>{current ? 'Release live-tested' : 'Earlier live test'}</small>
                </div>
                <a
                  className="button secondary demo-library-pdf"
                  href={root + file}
                  download={file}
                  aria-label={`Download PDF ${file}`}
                >
                  <Download size={15} aria-hidden="true" />
                  <span>Download PDF</span>
                </a>
              </li>
            ))}
          </ul>
        </details>
        <p className="demo-library-reference">
          <strong>What gets checked</strong>
          Approved suppliers, purchase orders, authorized line items, unit prices, quantities, and
          prior billed records. Processing an invoice leaves PO capacity and ERP records unchanged.
        </p>
      </dialog>
    </>
  )
}
