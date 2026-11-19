/** Real local API/UI QA; --live-price permits one upload only when no price run exists. */
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'
const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:8006'
const out = process.env.AP_COMPASS_POLICY_QA_DIR
  ? resolve(process.env.AP_COMPASS_POLICY_QA_DIR) + sep
  : fileURLToPath(new URL('../../tmp/phase06a-qa/', import.meta.url))
await mkdir(out, { recursive: true })
const get = async (path) => {
  const r = await fetch(base + '/api' + path)
  assert.equal(r.status, 200)
  return r.json()
}
let summaries = await get('/runs?limit=100')
let price = summaries.find((r) => r.invoice_number === 'PRICE_3PCT-2026')
const blocked = summaries.find((r) => r.primary_reason_code === 'PO_BALANCE_EXCEEDED')
assert.ok(blocked)
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const results = { liveUpload: false, observations: [], views: [], checks: [], previewRequests: 0 }
try {
  const page = await browser.newPage()
  const errors = []
  const uploads = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('request', (r) => {
    const p = new URL(r.url()).pathname
    if (r.method() === 'POST' && p === '/api/runs') uploads.push(p)
    if (r.method() === 'POST' && p.endsWith('/policy-preview')) results.previewRequests++
  })
  await page.setViewport({ width: 1440, height: 1000 })
  if (!price) {
    assert.ok(
      process.argv.includes('--live-price'),
      'Need an existing price run or explicit --live-price',
    )
    page.on('response', async (r) => {
      if (
        r.request().method() === 'GET' &&
        /^\/api\/runs\/[^/]+$/.test(new URL(r.url()).pathname) &&
        r.status() === 200
      ) {
        const d = await r.json().catch(() => null)
        if (d)
          results.observations.push({
            state: d.execution_state,
            stages: d.stages.map((s) => ({ name: s.name, state: s.state })),
            observedAt: new Date().toISOString(),
          })
      }
    })
    await page.goto(base + '/runs#upload', { waitUntil: 'networkidle0' })
    await (
      await page.$('input[type=file]')
    ).uploadFile(fileURLToPath(new URL('../../tests/fixtures/PRICE_3PCT.pdf', import.meta.url)))
    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname === '/api/runs' && r.request().method() === 'POST',
      ),
      page.$eval('button[type=submit]', (e) => e.click()),
    ])
    assert.equal(response.status(), 202)
    const created = await response.json()
    price = { id: created.run_id }
    results.liveUpload = true
    await writeFile(out + 'live-run.json', JSON.stringify({ runId: price.id }) + '\n')
    await page.waitForFunction(
      () => document.querySelector('.stage-running,.decision-brief,.technical-failure'),
      { timeout: 90000 },
    )
    if (await page.$('.stage-running'))
      await page.screenshot({ path: out + 'actual-live-trace-1440.png', fullPage: true })
    await page.waitForSelector('.decision-brief,.technical-failure', { timeout: 90000 })
  }
  const originalPrice = await get('/runs/' + price.id),
    originalBlocked = await get('/runs/' + blocked.id),
    activePolicy = await get('/policy')
  const beforeSummaries = await get('/runs?limit=100')
  const beforeSnapshots = await Promise.all(beforeSummaries.map((r) => get('/runs/' + r.id)))
  results.price = {
    id: price.id,
    executionState: originalPrice.execution_state,
    outcome: originalPrice.decision?.outcome,
    error: originalPrice.execution_error_code,
    model: originalPrice.model_id,
    route: originalPrice.source_route,
    invoice: originalPrice.extracted_invoice
      ? Object.fromEntries(
          [
            'vendor_name_raw',
            'invoice_number',
            'invoice_date',
            'po_reference',
            'currency',
            'net',
            'tax',
            'total',
            'lines',
            'evidence',
          ].map((k) => [k, originalPrice.extracted_invoice[k]]),
        )
      : null,
    usage: originalPrice.usage,
    timings: originalPrice.timings,
    reasonCodes: originalPrice.decision?.findings.map((f) => f.code),
  }
  await writeFile(out + 'live-results.json', JSON.stringify(results.price, null, 2) + '\n')
  // Preserve observed model differences honestly; never upload again to force the oracle outcome.
  assert.equal(
    originalPrice.execution_state,
    'COMPLETED',
    'Live extraction did not complete; inspect live-results.json without retrying',
  )
  async function geometry(label, width) {
    const g = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }))
    assert.ok(g.body <= g.viewport + 1, label + ' overflow')
    results.checks.push(label + ' fits ' + width)
  }
  for (const width of [1440, 1024, 390]) {
    await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
    for (const [name, run] of [
      ['price', originalPrice],
      ['overbilled', originalBlocked],
    ]) {
      await page.goto(base + '/runs/' + run.id, { waitUntil: 'networkidle0' })
      await page.waitForSelector('.decision-trace')
      await geometry(name, width)
      assert.equal(
        await page.$$eval('.trace-nodes .stage-passed', (e) => e.length),
        run.stages.filter((s) => s.state === 'PASSED').length,
      )
      await page.screenshot({ path: out + `${name}-recorded-${width}.png`, fullPage: true })
      await page.click('.policy-impact > summary')
      const [response] = await Promise.all([
        page.waitForResponse(
          (r) =>
            new URL(r.url()).pathname.endsWith('/policy-preview') &&
            r.request().method() === 'POST',
        ),
        page.click('.tolerance-options input[value="0.05"]'),
      ])
      assert.equal(response.status(), 200)
      const value = await response.json()
      await page.waitForFunction(() => document.querySelector('.preview-status .status'))
      await page.evaluate(() =>
        Promise.allSettled(
          document
            .getAnimations()
            .filter((a) => a.effect?.getComputedTiming().iterations !== Infinity)
            .map((a) => a.finished),
        ),
      )
      assert.equal(
        await page.$eval('.decision-header .status', (e) => e.textContent.trim()),
        { BLOCKED: 'Blocked', REVIEW_REQUIRED: 'Needs review', READY_FOR_AP: 'Ready to process' }[
          run.decision.outcome
        ],
      )
      if (name === 'overbilled') {
        assert.equal(value.preview_decision.outcome, 'BLOCKED')
        assert.ok(value.preview_decision.findings.some((f) => f.code === 'PO_BALANCE_EXCEEDED'))
      }
      if (name === 'price')
        results.price.preview = {
          outcome: value.preview_decision.outcome,
          changed: value.changed,
          reasonCodes: value.preview_decision.findings.map((f) => f.code),
        }
      await geometry(name + ' preview', width)
      assert.equal(
        await page.$eval('.preview-outcome-label', (e) => e.textContent),
        'Preview outcome',
      )
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
      assert.equal(
        await page.$eval('.tolerance-thumb', (e) => getComputedStyle(e).transitionDuration),
        '0s',
      )
      assert.equal(
        await page.$eval('.preview-status', (e) => getComputedStyle(e).animationName),
        'none',
      )
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }])
      await page.$eval('.policy-impact', (e) => e.scrollIntoView({ block: 'start' }))
      await page.screenshot({ path: out + `${name}-preview-${width}.png`, fullPage: true })
      await page.screenshot({ path: out + `${name}-preview-${width}-fold.png` })
      results.views.push({
        name,
        width,
        recorded: run.decision.outcome,
        preview: value.preview_decision.outcome,
      })
    }
  }
  // Test-only RUNNING responses, never persisted and never model calls.
  await page.setRequestInterception(true)
  page.on('request', (r) => {
    if (new URL(r.url()).pathname === '/api/runs/' + blocked.id && r.method() === 'GET') {
      const d = structuredClone(originalBlocked)
      d.execution_state = 'RUNNING'
      d.decision = null
      d.extracted_invoice = null
      d.timings = []
      d.candidates = []
      d.stages = d.stages.map((s, i) => ({
        ...s,
        state: i === 0 ? 'PASSED' : i === 1 ? 'RUNNING' : 'QUEUED',
        started_at: i < 2 ? s.started_at : null,
        finished_at: i === 0 ? s.finished_at : null,
      }))
      void r.respond({ status: 200, contentType: 'application/json', body: JSON.stringify(d) })
      return
    }
    void r.continue()
  })
  for (const width of [1440, 1024, 390]) {
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }])
    await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
    await page.goto(base + '/runs/' + blocked.id, { waitUntil: 'domcontentloaded' })
    await page.waitForSelector('.stage-running')
    assert.equal(await page.$$eval('.stage-running', (e) => e.length), 1)
    const moving = await page.$eval(
      '.stage-running .trace-connector > span',
      (e) => getComputedStyle(e).animationName,
    )
    assert.notEqual(moving, 'none')
    const columns = await page.$eval(
      '.trace-nodes',
      (e) => getComputedStyle(e).gridTemplateColumns.split(' ').length,
    )
    assert.equal(columns, width === 390 ? 1 : 5)
    const summary = await page.$('.trace-node summary')
    await summary.focus()
    await page.keyboard.press('Enter')
    assert.equal(await page.$eval('.trace-node', (e) => e.open), true)
    assert.equal(
      await page.$eval('.trace-node summary', (e) => getComputedStyle(e).outlineStyle),
      'solid',
    )
    await geometry('running trace', width)
    await page.screenshot({ path: out + `TEST_ONLY-running-${width}.png`, fullPage: true })
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
    assert.equal(
      await page.$eval(
        '.stage-running .trace-connector > span',
        (e) => getComputedStyle(e).animationName,
      ),
      'none',
    )
    assert.equal(
      await page.$eval('.stage-running .spin', (e) => getComputedStyle(e).animationName),
      'none',
    )
  }
  assert.deepEqual(await get('/runs?limit=100'), beforeSummaries)
  assert.deepEqual(
    await Promise.all(beforeSummaries.map((r) => get('/runs/' + r.id))),
    beforeSnapshots,
  )
  assert.deepEqual(await get('/policy'), activePolicy)
  assert.equal(uploads.length, results.liveUpload ? 1 : 0)
  assert.deepEqual(errors, [])
  results.checks.push(
    'Recorded decisions/stages/all persisted snapshots and active policy unchanged by previews',
    'Actual-only connector movement, reduced-motion disables connector and spinner',
    'Native node keyboard disclosure/focus and responsive horizontal/vertical forms pass',
    'No uncaught application JavaScript errors',
  )
  await writeFile(out + 'results.json', JSON.stringify(results, null, 2) + '\n')
  console.log(
    JSON.stringify(
      {
        liveUpload: results.liveUpload,
        priceRecorded: results.price.outcome,
        pricePreview: results.price.preview,
        views: results.views,
        checks: results.checks,
        previewRequests: results.previewRequests,
      },
      null,
      2,
    ),
  )
} finally {
  await browser.close()
}
