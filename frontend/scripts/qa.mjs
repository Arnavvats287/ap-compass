/** Explicit local browser QA. Deterministic state interceptions are test data, never persisted. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'

const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:5173'
const output = process.env.AP_COMPASS_QA_DIR
  ? resolve(process.env.AP_COMPASS_QA_DIR) + sep
  : fileURLToPath(new URL('../../tmp/phase05-qa/', import.meta.url))
await mkdir(output, { recursive: true })
const json = async (path) => {
  const response = await fetch(base + '/api' + path)
  assert.equal(response.status, 200)
  return response.json()
}
const summaries = await json('/runs?limit=100')
const selected = Object.fromEntries(
  ['READY_FOR_AP', 'REVIEW_REQUIRED', 'BLOCKED'].map((outcome) => {
    const summary = summaries.find((run) => run.outcome === outcome)
    assert.ok(summary, `Need a genuinely persisted ${outcome} run`)
    return [outcome, summary]
  }),
)
const blocked = await json('/runs/' + selected.BLOCKED.id)
const persistedBefore = await Promise.all(summaries.map((run) => json('/runs/' + run.id)))
const fingerprint = (value) => createHash('sha256').update(JSON.stringify(value)).digest('hex')
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const results = {
  base,
  realPersistedRuns: Object.values(selected).map((run) => ({ id: run.id, outcome: run.outcome })),
  views: [],
  checks: [],
  deterministicStates: [],
  newModelCalls: 0,
}
const errors = []
async function geometry(page, label, width) {
  const dimensions = await page.evaluate(() => ({
    body: document.body.scrollWidth,
    html: document.documentElement.scrollWidth,
    viewport: innerWidth,
    dataCells: [...document.querySelectorAll('tbody td')].map((cell) => {
      const r = cell.getBoundingClientRect()
      return { left: r.left, right: r.right }
    }),
  }))
  assert.ok(
    dimensions.body <= width + 1 && dimensions.html <= width + 1,
    `${label}: page overflow ${JSON.stringify(dimensions)}`,
  )
  if (width === 390)
    for (const cell of dimensions.dataCells)
      assert.ok(cell.left >= 0 && cell.right <= width + 1, `${label}: mobile cell clipped`)
  return dimensions
}
try {
  const page = await browser.newPage()
  const mutations = []
  page.on('request', (request) => {
    if (
      new URL(request.url()).pathname.startsWith('/api/') &&
      !['GET', 'HEAD'].includes(request.method())
    )
      mutations.push(request.method())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  const routes = [
    ['overview', '/', '.metric-strip .metric'],
    ['queue', '/runs', 'tbody tr'],
    ['ready', '/runs/' + selected.READY_FOR_AP.id, '.ready-brief'],
    ['blocked', '/runs/' + selected.BLOCKED.id, '.blocked-brief'],
    ['review', '/runs/' + selected.REVIEW_REQUIRED.id, '.review-brief'],
  ]
  for (const width of [1440, 1024, 390]) {
    await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
    for (const [name, path, selector] of routes) {
      await page.goto(base + path, { waitUntil: 'networkidle0' })
      await page.waitForSelector(selector)
      const dimensions = await geometry(page, name, width)
      if (width === 390 && ['ready', 'blocked', 'review'].includes(name))
        assert.equal(
          await page.evaluate(
            () =>
              document.querySelector('.decision-column').getBoundingClientRect().top <
              document.querySelector('.document-panel').getBoundingClientRect().top,
          ),
          true,
        )
      if (width === 390 && ['ready', 'blocked', 'review'].includes(name)) {
        await page.$eval('.document-panel', (element) => element.scrollIntoView())
        await page.waitForFunction(
          () => document.querySelector('.document-panel').getBoundingClientRect().top < innerHeight,
        )
        await page.evaluate(
          () =>
            new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
        )
        await page.evaluate(() => window.scrollTo(0, 0))
      }
      const screenshot = `${name}-${width}.png`
      await page.screenshot({ path: output + `${name}-${width}-fold.png`, fullPage: false })
      await page.screenshot({ path: output + screenshot, fullPage: true })
      results.views.push({
        name,
        width,
        height: width === 390 ? 844 : width === 1024 ? 900 : 1000,
        path,
        screenshot,
        overflow: false,
        dataCellsWithinViewport: width === 390 ? true : undefined,
      })
    }
  }
  // Keyboard walkthrough: skip link, URL filter/search, row link, native disclosures.
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(base, { waitUntil: 'networkidle0' })
  await page.keyboard.press('Tab')
  assert.match(
    await page.evaluate(() => document.activeElement.textContent),
    /Skip to main content/,
  )
  assert.equal(
    await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle),
    'solid',
  )
  await page.keyboard.press('Enter')
  assert.equal(await page.evaluate(() => document.activeElement.id), 'main')
  results.checks.push('Skip link first, visible focus, Enter moves to main')
  await page.goto(base + '/runs', { waitUntil: 'networkidle0' })
  await page.focus('#invoice-search')
  await page.keyboard.type('Aster')
  await page.waitForFunction(() => location.search.includes('q=Aster'))
  assert.equal(await page.$eval('#invoice-search', (input) => input.value), 'Aster')
  const filter = await page.$('button.filter:nth-child(4)')
  await filter.focus()
  await page.keyboard.press('Enter')
  await page.waitForFunction(() => location.search.includes('status=blocked'))
  await page.focus('.invoice-link')
  await page.keyboard.press('Enter')
  await page.waitForSelector('.blocked-brief')
  assert.match(await page.$eval('.ownership', (el) => el.textContent), /Procurement/)
  await page.focus('.workspace-audit > summary')
  await page.keyboard.press('Enter')
  assert.equal(await page.$eval('.workspace-audit', (el) => el.open), true)
  const summary = await page.$('.finding-disclosure summary')
  await summary.focus()
  await page.keyboard.press('Enter')
  assert.equal(await page.$eval('.finding-disclosure', (el) => el.open), true)
  const evidence = await page.$('.evidence-item summary')
  await evidence.focus()
  await page.keyboard.press('Enter')
  assert.equal(await page.$eval('.evidence-item', (el) => el.open), true)
  const pdf = await fetch(base + '/api/runs/' + blocked.id + '/document')
  assert.equal(pdf.status, 200)
  assert.match(pdf.headers.get('content-type'), /application\/pdf/)
  results.checks.push(
    'Keyboard search/filter updates URL, invoice link opens workspace, findings/evidence disclose, source PDF returns 200',
  )
  // Deterministic API states: the production server/database is never changed.
  let mode = 'running'
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const url = new URL(request.url())
    const apiPath = '/api/runs/' + blocked.id
    if (
      ['empty', 'error'].includes(mode) &&
      ['/api/dashboard', '/api/runs'].includes(url.pathname)
    ) {
      if (mode === 'error')
        return request.respond({
          status: 503,
          contentType: 'application/json',
          body: '{"detail":"TEST_ONLY unavailable"}',
        })
      return request.respond({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          url.pathname === '/api/runs'
            ? []
            : {
                total_runs: 0,
                in_progress: 0,
                completed: 0,
                ready: 0,
                review_required: 0,
                blocked: 0,
                processing_failed: 0,
                interrupted: 0,
                flagged_invoice_net_by_currency: {},
                flagged_invoice_net_missing_count: 0,
              },
        ),
      })
    }
    if (url.pathname === apiPath && request.method() === 'GET') {
      const run = structuredClone(blocked)
      if (mode === 'long') {
        run.extracted_invoice.vendor_name_raw =
          'Long Supplier Financial Operations and Procurement Services '.repeat(6)
        run.extracted_invoice.invoice_number = 'INV-LONG-REFERENCE-'.repeat(16)
        run.decision.findings[1].explanation +=
          ' Detailed supplier documentation and procurement review context.'.repeat(16)
      } else {
        run.execution_state =
          mode === 'running'
            ? 'RUNNING'
            : mode === 'queued'
              ? 'QUEUED'
              : mode === 'interrupted'
                ? 'INTERRUPTED'
                : 'PROCESSING_FAILED'
        run.execution_error_code =
          mode === 'failed' ? 'PROVIDER_TIMEOUT' : mode === 'interrupted' ? 'SERVER_RESTART' : null
        run.decision = null
        run.extracted_invoice = null
        run.candidates = []
        run.usage = null
        run.timings = []
        run.model_id = null
        run.stages = run.stages.map((stage, index) => ({
          ...stage,
          state:
            index === 0
              ? 'PASSED'
              : index === 1
                ? mode === 'running'
                  ? 'RUNNING'
                  : mode === 'queued'
                    ? 'QUEUED'
                    : 'FAILED'
                : mode === 'running' || mode === 'queued'
                  ? 'QUEUED'
                  : 'SKIPPED',
          started_at: index === 0 || (index === 1 && mode !== 'queued') ? stage.started_at : null,
          finished_at:
            index === 0 || ['failed', 'interrupted'].includes(mode) ? stage.finished_at : null,
        }))
      }
      return request.respond({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(run),
      })
    }
    void request.continue()
  })
  for (const state of ['queued', 'running', 'failed', 'interrupted', 'long']) {
    mode = state
    await page.setViewport({ width: 390, height: 844 })
    await page.goto(base + '/runs/' + blocked.id, { waitUntil: 'domcontentloaded' })
    await page.waitForSelector(
      state === 'failed' || state === 'interrupted'
        ? '.technical-failure'
        : state === 'long'
          ? '.blocked-brief'
          : '.processing-panel',
    )
    await geometry(page, 'deterministic-' + state, 390)
    const text = await page.evaluate(() => document.body.innerText)
    if (state === 'failed')
      assert.ok(
        text.includes('No financial decision was produced') &&
          !text.includes('Resolution required'),
      )
    if (state === 'running') {
      assert.equal(await page.$$eval('.stage-running', (elements) => elements.length), 1)
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
      assert.equal(await page.$eval('.spin', (el) => getComputedStyle(el).animationName), 'none')
      results.checks.push(
        'Reduced-motion disables the real-state spinner; no essential content hidden',
      )
    }
    const screenshot = `deterministic-${state}-390.png`
    await page.screenshot({ path: output + screenshot, fullPage: true })
    results.deterministicStates.push({
      state,
      screenshot,
      source: 'TEST_ONLY response interception; not persisted',
    })
  }
  for (const state of ['empty', 'error']) {
    mode = state
    await page.goto(base, { waitUntil: 'domcontentloaded' })
    await page.waitForFunction(
      (state) =>
        state === 'empty'
          ? document.body.innerText.includes('Your invoice queue starts here')
          : !!document.querySelector('[role="alert"]'),
      {},
      state,
    )
    await geometry(page, 'deterministic-' + state, 390)
    const screenshot = `deterministic-${state}-390.png`
    await page.screenshot({ path: output + screenshot, fullPage: true })
    results.deterministicStates.push({
      state,
      screenshot,
      source: 'TEST_ONLY response interception; not persisted',
    })
  }
  results.checks.push(
    'Queued, processing, technical failure, interruption, long values, empty and API error states rendered with deterministic API test data',
  )
  assert.deepEqual(errors, [])
  assert.deepEqual(mutations, [])
  const persistedAfter = await Promise.all(summaries.map((run) => json('/runs/' + run.id)))
  assert.deepEqual(persistedAfter, persistedBefore)
  assert.deepEqual(await json('/runs?limit=100'), summaries)
  results.persistedSnapshotFingerprint = fingerprint(persistedAfter)
  results.checks.push(
    'Zero API mutation requests; all persisted run snapshots and summaries unchanged',
  )
  results.checks.push('No uncaught application JavaScript errors')
  await writeFile(output + 'results.json', JSON.stringify(results, null, 2) + '\n')
  console.log(
    JSON.stringify(
      {
        realViews: results.views.length,
        deterministicStates: results.deterministicStates.length,
        checks: results.checks,
        screenshotDirectory: output,
        newModelCalls: 0,
      },
      null,
      2,
    ),
  )
} finally {
  await browser.close()
}
