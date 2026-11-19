/** Visual and interaction regression for the operations surfaces. Intercepts are TEST_ONLY. */
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'

const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:5173'
const output = resolve(process.env.AP_COMPASS_QA_DIR ?? 'tmp/premium-dashboard-qa')
await mkdir(output, { recursive: true })

const get = async (path) => {
  const response = await fetch(base + '/api' + path)
  assert.equal(response.status, 200)
  return response.json()
}

const [runs, dashboard] = await Promise.all([get('/runs?limit=100'), get('/dashboard')])
const blocked = runs.find((run) => run.outcome === 'BLOCKED')
assert.ok(blocked, 'A persisted blocked case is required for the spotlight check')
const detail = await get('/runs/' + blocked.id)
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})

const page = await browser.newPage()
const errors = []
const detailRequests = new Set()
const writes = []
page.on('pageerror', (error) => errors.push(error.message))
page.on('request', (request) => {
  const path = new URL(request.url()).pathname
  if (/^\/api\/runs\/[^/]+$/.test(path)) detailRequests.add(path)
  if (path.startsWith('/api/') && !['GET', 'HEAD'].includes(request.method())) writes.push(path)
})

async function capture(name, path, width, selector) {
  await page.setViewport({ width, height: width < 800 ? 844 : 1000 })
  await page.goto(base + path, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector(selector)
  if (name.startsWith('overview-')) {
    await page.waitForFunction(
      (action) => document.querySelector('.ops-priority dd[aria-live]')?.textContent === action,
      {},
      detail.decision.next_action,
    )
  }
  await page.evaluate(() => document.fonts.ready.then(() => true))
  const dimensions = await page.evaluate(() => ({
    viewport: innerWidth,
    root: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }))
  assert.ok(dimensions.root <= width + 1 && dimensions.body <= width + 1, name + ': page overflow')
  await page.screenshot({ path: resolve(output, name + '.png'), fullPage: true })
  if (name.startsWith('overview-')) {
    await page.screenshot({ path: resolve(output, name + '-fold.png') })
  }
}

try {
  for (const width of [1440, 1024, 768, 390]) {
    await capture('overview-' + width, '/', width, '.ops-spotlight-action')
    await page.waitForFunction(
      (action) => document.querySelector('.ops-priority dd[aria-live]')?.textContent === action,
      {},
      detail.decision.next_action,
    )
    assert.deepEqual([...detailRequests], ['/api/runs/' + blocked.id])
  }
  await capture('queue-1440', '/runs', 1440, 'tbody tr')
  await capture('queue-390', '/runs', 390, 'tbody tr')
  await capture('overview-1440', '/', 1440, '.ops-spotlight-action')
  const spotlight = await page.$('.ops-spotlight')
  await spotlight.screenshot({ path: resolve(output, 'exception-spotlight.png') })
  await page.evaluate(() => window.scrollTo(0, 0))
  const metric = '.ops-metric.blocked'
  await page.hover(metric)
  await page.waitForFunction(
    (selector) =>
      new DOMMatrix(getComputedStyle(document.querySelector(selector)).transform).m42 <= -3.9,
    {},
    metric,
  )
  await page.mouse.down()
  await page.waitForFunction(
    (selector) =>
      new DOMMatrix(getComputedStyle(document.querySelector(selector)).transform).a < 0.998,
    {},
    metric,
  )
  await page.mouse.up()
  await page.waitForFunction(() => location.search.includes('status=blocked'))
  assert.equal(await page.$$eval('tbody tr', (rows) => rows.length), dashboard.blocked)
  await page.select('.ops-sort select', 'oldest')
  await page.waitForFunction(() => location.search.includes('sort=oldest'))

  await page.goto(base, { waitUntil: 'networkidle0' })
  const selectors = []
  for (let step = 0; step < 12; step++) {
    await page.keyboard.press('Tab')
    const focused = await page.evaluate(() => ({
      label: document.activeElement.textContent.trim(),
      visible:
        document.activeElement.matches(':focus-visible') &&
        getComputedStyle(document.activeElement).outlineStyle !== 'none',
    }))
    selectors.push(focused)
    if (focused.label === 'Review invoice') break
  }
  assert.ok(selectors.some((entry) => entry.visible && entry.label === 'Review invoice'))
  await page.keyboard.press('Enter')
  await page.waitForFunction((id) => location.pathname === '/runs/' + id, {}, blocked.id)
  await page.waitForSelector('.blocked-brief')

  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  await page.goto(base, { waitUntil: 'networkidle0' })
  await page.hover(metric)
  assert.deepEqual(
    await page.$eval(metric, (el) => {
      const style = getComputedStyle(el)
      return [style.transform, style.transitionDuration]
    }),
    ['none', '0s'],
  )
  await page.click('.ops-heading a')
  await page.waitForFunction(() => location.pathname === '/runs/upload')
  await page.waitForSelector('.batch-drop button')
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }])
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true })
  await page.goto(base, { waitUntil: 'networkidle0' })
  assert.equal(await page.evaluate(() => matchMedia('(hover: none) and (pointer: coarse)').matches), true)
  await page.tap(metric)
  await page.waitForFunction(() => location.search.includes('status=blocked'))
  await page.setViewport({ width: 1440, height: 1000 })

  const zero = {
    ...dashboard,
    total_runs: 0,
    completed: 0,
    ready: 0,
    review_required: 0,
    blocked: 0,
    in_progress: 0,
    processing_failed: 0,
    interrupted: 0,
    flagged_invoice_net_by_currency: {},
  }
  const single = {
    ...blocked,
    outcome: 'READY_FOR_AP',
    primary_reason_code: 'PO_MATCH_CONFIRMED',
    owner: null,
  }
  const longSupplier =
    'Meridian Regional Infrastructure and Managed Services Consortium ' +
    'ContinentalTechnologyOperationsSpecializedProcurementDivision'
  const longSupplierCount = 9
  const varied = Array.from({ length: 100 }, (_, index) => ({
    ...blocked,
    id: index === 0 ? blocked.id : 'test-only-' + String(index).padStart(3, '0'),
    outcome: index === 99 ? null : 'REVIEW_REQUIRED',
    execution_state: index === 99 ? 'PROCESSING_FAILED' : 'COMPLETED',
    vendor_name: index < longSupplierCount ? longSupplier : 'Synthetic supplier ' + (index % 18),
    invoice_number: 'TEST-ONLY-INVOICE-' + index,
    updated_at: new Date(Date.UTC(2026, 10, 1, 0, 0, 100 - index)).toISOString(),
    currency: index % 2 ? 'INR' : 'USD',
    reviewed_outcome: index === 2 ? 'READY_FOR_AP' : null,
  }))
  let scenario = 'empty'
  await page.setRequestInterception(true)
  page.on('request', async (request) => {
    const { pathname } = new URL(request.url())
    if (
      pathname !== '/api/dashboard' &&
      pathname !== '/api/runs' &&
      pathname !== '/api/runs/' + blocked.id
    )
      return request.continue()
    if (scenario === 'loading' && pathname === '/api/dashboard') return request.abort()
    if (scenario === 'error' && pathname === '/api/dashboard') {
      return request.respond({ status: 503, contentType: 'application/json', body: '{}' })
    }
    const definitions = {
      '/api/dashboard':
        scenario === 'dense'
          ? {
              ...zero,
              total_runs: 100,
              completed: 99,
              review_required: 99,
              processing_failed: 1,
              flagged_invoice_net_by_currency: { INR: '150000', USD: '26000' },
            }
          : scenario === 'single'
            ? { ...zero, total_runs: 1, completed: 1, ready: 1 }
            : zero,
      '/api/runs': scenario === 'dense' ? varied : scenario === 'single' ? [single] : [],
      ['/api/runs/' + blocked.id]: {
        ...detail,
        decision: {
          ...detail.decision,
          outcome: 'REVIEW_REQUIRED',
          next_action: 'TEST_ONLY: Confirm the supporting records with Accounts Payable.',
        },
      },
    }
    await request.respond({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(definitions[pathname]),
    })
  })
  await capture('empty-no-attention', '/', 1024, '.ops-priority-empty h3')
  assert.equal(
    await page.$eval('.ops-priority-empty h3', (el) => el.textContent),
    'No recorded exceptions',
  )
  assert.equal(await page.$('.ops-outcome-bar'), null)
  scenario = 'single'
  await capture('single-ready', '/', 1024, '.ops-outcome-bar .ready')
  assert.equal(await page.$$eval('.ops-outcome-bar span', (segments) => segments.length), 1)
  assert.equal(await page.$$eval('tbody tr', (rows) => rows.length), 1)
  scenario = 'dense'
  await capture('dense-long-vendors', '/', 390, '.ops-vendors li')
  await page.waitForSelector('.ops-vendors li')
  assert.equal(await page.$$eval('.ops-vendors li', (rows) => rows.length), 10)
  assert.match(await page.$eval('.ops-execution', (el) => el.textContent), /Processing failed\s*1/)
  assert.equal(await page.$$eval('.ops-flagged dd', (amounts) => amounts.length), 2)
  const longVendor = await page.evaluateHandle(
    (name) =>
      Array.from(document.querySelectorAll('.ops-vendors li a')).find(
        (link) => new URL(link.href).searchParams.get('vendor') === name,
      ),
    longSupplier,
  )
  const vendorLink = longVendor.asElement()
  assert.ok(vendorLink)
  await vendorLink.click()
  await page.waitForFunction(() => new URLSearchParams(location.search).has('vendor'))
  await page.waitForSelector('tbody tr')
  assert.equal(await page.$$eval('tbody tr', (rows) => rows.length), longSupplierCount)
  assert.match(await page.$eval('tbody', (el) => el.textContent), /Current reviewed/)
  await capture('queue-long-supplier', '/runs' + new URL(page.url()).search, 390, 'tbody tr')

  scenario = 'loading'
  await capture('dashboard-loading', '/', 1024, '.ops-loading')
  assert.equal(await page.$('.ops-metrics a'), null)
  scenario = 'error'
  await capture('dashboard-error', '/', 1024, '.ops-overview [role=alert]')
  assert.ok(await page.$('#upload button'), 'Upload remains reachable on a metrics error')
  assert.deepEqual(errors, [])
  assert.deepEqual(writes, [])
  assert.deepEqual(await get('/runs?limit=100'), runs)
  assert.deepEqual(await get('/runs/' + blocked.id), detail)
  console.log(
    'Premium browser QA passed: four widths, keyboard, hover/press, motion, sorting, 100-record TEST_ONLY states, and unchanged persisted reads.',
  )
} finally {
  await browser.close()
}
