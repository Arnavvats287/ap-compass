import BatchUpload from './BatchUpload'
import LaunchDitherField from './LaunchDitherField'

const steps = [
  ['Read the source', 'Trace extracted fields back to the invoice.'],
  ['Validate against the PO', 'Check approved prices, quantities and remaining commitment.'],
  ['Explain the next action', 'See the reason for each exception and who should act.'],
] as const

export default function LaunchPage() {
  return (
    <div className="launch-page">
      <LaunchDitherField />
      <header className="launch-intro">
        <p className="launch-eyebrow">Accounts payable /</p>
        <h1>AP Compass</h1>
      </header>
      <div className="launch-tools">
        <BatchUpload launch />
      </div>
      <section className="launch-story" aria-labelledby="launch-story-title">
        <h2 className="sr-only" id="launch-story-title">
          Review workflow
        </h2>
        <ol className="launch-steps">
          {steps.map(([title, description], index) => (
            <li key={title}>
              {index < steps.length - 1 && <span className="launch-step-link" aria-hidden="true" />}
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
