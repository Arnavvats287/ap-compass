import BatchUpload from './BatchUpload'

const steps = [
  ['Read the source', 'Trace extracted fields back to the invoice.'],
  ['Validate against the PO', 'Check approved prices, quantities and remaining commitment.'],
  ['Explain the next action', 'See the reason for each exception and who should act.'],
] as const

export default function LaunchPage() {
  return (
    <div className="launch-page">
      <header className="launch-intro">
        <p className="launch-eyebrow">ACCOUNTS PAYABLE / REVIEW WORKSPACE</p>
        <h1>
          <span>Understand the invoice.</span> <span>Verify the decision.</span>
        </h1>
        <p className="launch-description">
          Extract invoice details with source evidence, validate them against the purchase order,
          and see which exceptions need AP review.
        </p>
      </header>
      <BatchUpload launch />
      <section className="launch-story" aria-labelledby="launch-story-title">
        <h2 className="sr-only" id="launch-story-title">
          Review workflow
        </h2>
        <ol className="launch-steps">
          {steps.map(([title, description], index) => (
            <li key={title}>
              <span className="launch-step-number" aria-hidden="true">
                0{index + 1}
              </span>
              <div>
                <h3>{title}</h3>
                <p>{description}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
