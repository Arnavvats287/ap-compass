/** One opt-in genuine UI upload. No mocked API/provider and no automatic resubmission. */
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const resume = process.argv.includes('--resume')
  ? process.argv[process.argv.indexOf('--resume') + 1]
  : null
if (!resume && !process.argv.includes('--live-upload'))
  throw new Error('Requires --live-upload or --resume RUN_ID')
if (resume && (!/^[0-9a-f]{32}$/.test(resume) || process.argv.includes('--live-upload')))
  throw new Error('Resume must name one existing run without --live-upload')
const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:5173'
const output = fileURLToPath(new URL('../../tmp/phase05-qa/', import.meta.url))
await mkdir(output, { recursive: true })
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const report = resume
  ? JSON.parse(await readFile(output + 'live-results.json', 'utf8'))
  : {
      fixture: 'OVERBILLED_PARTIAL.pdf',
      live: true,
      transport: 'actual Chrome UI -> FastAPI -> default extraction/finance workflow',
      observations: [],
    }
if (resume) assert.equal(report.runId, resume)
const observations = report.observations
if (resume)
  report.harnessRecovery =
    'Corrected popup matching to page/opener targets and resumed the existing run; no second upload or inference.'
try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1440, height: 1000 })
  if (!resume) {
    const beforeResponse = await fetch(base + '/api/dashboard')
    report.dashboardBefore = await beforeResponse.json()
  }
  page.on('response', async (response) => {
    const path = new URL(response.url()).pathname
    if (
      response.request().method() === 'GET' &&
      /^\/api\/runs\/[^/]+$/.test(path) &&
      response.status() === 200
    ) {
      const value = await response.json().catch(() => null)
      if (value)
        observations.push({
          state: value.execution_state,
          stages: value.stages.map((stage) => ({ name: stage.name, state: stage.state })),
          observedAt: new Date().toISOString(),
        })
    }
  })
  let queued
  if (!resume) {
    await page.goto(base + '/runs#upload', { waitUntil: 'networkidle0' })
    const input = await page.$('input[type="file"]')
    await input.uploadFile(
      fileURLToPath(new URL('../../tests/fixtures/OVERBILLED_PARTIAL.pdf', import.meta.url)),
    )
    await page.waitForFunction(() => document.body.innerText.includes('OVERBILLED_PARTIAL.pdf'))
    const [created] = await Promise.all([
      page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === '/api/runs' &&
          response.request().method() === 'POST',
      ),
      page.$eval('button[type="submit"]', (button) => button.click()),
    ])
    assert.equal(created.status(), 202)
    queued = await created.json()
    report.runId = queued.run_id
    report.uploadResponse = queued
    await page.waitForFunction((id) => location.pathname === '/runs/' + id, {}, queued.run_id)
    await page.waitForSelector('.processing-panel', { timeout: 15000 })
    report.visibleProcessing = await page.$eval('.processing-panel', (element) => element.innerText)
    await page.screenshot({ path: output + 'live-processing-1440.png', fullPage: true })
    await page.waitForFunction(
      () => !!document.querySelector('.decision-brief,.technical-failure'),
      { timeout: 90000 },
    )
  } else {
    queued = { run_id: resume }
    await page.goto(base + '/runs/' + resume, { waitUntil: 'networkidle0' })
  }
  const detailResponse = await fetch(base + '/api/runs/' + queued.run_id)
  const run = await detailResponse.json()
  report.executionState = run.execution_state
  report.outcome = run.decision?.outcome ?? null
  report.executionErrorCode = run.execution_error_code
  report.modelId = run.model_id
  report.sourceRoute = run.source_route
  report.usage = run.usage
  report.timings = run.timings
  report.stages = run.stages
  report.reasonCodes = run.decision?.findings.map((finding) => finding.code) ?? []
  report.primaryValues =
    run.decision?.findings.find((finding) => finding.code === run.decision.primary_reason_code)
      ?.values ?? []
  report.owner = run.decision?.owner
  report.nextAction = run.decision?.next_action
  report.criticalFields = run.extracted_invoice
    ? {
        vendor: run.extracted_invoice.vendor_name_raw,
        invoice: run.extracted_invoice.invoice_number,
        po: run.extracted_invoice.po_reference,
        net: run.extracted_invoice.net,
        tax: run.extracted_invoice.tax,
        total: run.extracted_invoice.total,
        currency: run.extracted_invoice.currency,
      }
    : null
  report.evidenceStates = [
    ...new Set(run.extracted_invoice?.evidence.map((ref) => ref.evidence_state) ?? []),
  ]
  await page.screenshot({ path: output + 'live-blocked-1440.png', fullPage: true })
  // Save observed truth before checking the oracle; never conceal provider variability/failure.
  await writeFile(output + 'live-results.json', JSON.stringify(report, null, 2) + '\n')
  assert.equal(run.execution_state, 'COMPLETED')
  assert.equal(run.decision.outcome, 'BLOCKED')
  assert.equal(run.model_id, 'gemini-3.5-flash-lite')
  assert.equal(run.usage.model_calls, 1)
  assert.ok(
    report.reasonCodes.includes('PO_BALANCE_EXCEEDED') &&
      report.reasonCodes.includes('PO_QUANTITY_EXCEEDED'),
  )
  assert.equal(run.extracted_invoice.po_reference, 'PO-3015')
  assert.match(await page.$eval('.ownership', (el) => el.innerText), /Procurement/)
  const targetPromise = browser.waitForTarget(
    (target) =>
      target.type() === 'page' &&
      target.opener() === page.target() &&
      target.url().includes('/api/runs/' + queued.run_id + '/document'),
    { timeout: 10000 },
  )
  await page.click('.document-panel .text-link')
  const target = await targetPromise
  report.sourceOpened = target.type() === 'page'
  const pdf = await fetch(base + '/api/runs/' + queued.run_id + '/document')
  assert.equal(pdf.status, 200)
  assert.match(pdf.headers.get('content-type'), /application\/pdf/)
  assert.ok(
    Buffer.from(await pdf.arrayBuffer())
      .subarray(0, 5)
      .equals(Buffer.from('%PDF-')),
  )
  const session = await browser.target().createCDPSession()
  const { targetInfos } = await session.send('Target.getTargets')
  const popup = targetInfos.find((info) => info.type === 'page' && info.url === target.url())
  if (popup) await session.send('Target.closeTarget', { targetId: popup.targetId })
  await session.detach()
  await page.click('.workspace-breadcrumb a')
  await page.waitForSelector(`a[href="/runs/${queued.run_id}"]`)
  report.queueContainsNewRun = true
  await page.click('header nav a[href="/"]')
  await page.waitForSelector('.metric-strip .metric')
  const afterResponse = await fetch(base + '/api/dashboard')
  report.dashboardAfter = await afterResponse.json()
  assert.equal(report.dashboardAfter.total_runs, report.dashboardBefore.total_runs + 1)
  assert.equal(report.dashboardAfter.blocked, report.dashboardBefore.blocked + 1)
  report.dashboardRefreshed = true
  await page.goto(base + '/runs/' + queued.run_id, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.blocked-brief')
  const reloaded = await (await fetch(base + '/api/runs/' + queued.run_id)).json()
  assert.deepEqual(reloaded, run)
  report.identicalAfterReload = true
  report.completed = true
  await writeFile(output + 'live-results.json', JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
} finally {
  await browser.close()
}
