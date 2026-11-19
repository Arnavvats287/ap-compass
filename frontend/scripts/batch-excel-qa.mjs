/** Real Chrome uploads against a fresh, controlled and private loopback instance. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'

const [settings, destination] = process.argv.slice(2)
assert.ok(settings && destination, 'Pass the ignored private environment file and output directory')
const env = Object.fromEntries(
  (await readFile(settings, 'utf8'))
    .split(/\r?\n/)
    .filter((line) => /^AP_COMPASS_[A-Z_]+=/.test(line.replace(/^\uFEFF/, '')))
    .map((line) =>
      line
        .replace(/^\uFEFF/, '')
        .split(/=(.*)/s)
        .slice(0, 2),
    ),
)
const base = env.AP_COMPASS_PRIVATE_ORIGIN
assert.equal(new URL(base).hostname, '127.0.0.1')
const credentials = {
  username: env.AP_COMPASS_PRIVATE_USERNAME,
  password: env.AP_COMPASS_PRIVATE_PASSWORD,
}
const authorization =
  'Basic ' + Buffer.from(credentials.username + ':' + credentials.password).toString('base64')
const output = resolve(destination)
const downloads = resolve(output, 'downloads')
await mkdir(downloads, { recursive: true })
assert.deepEqual(await readdir(downloads), [], 'Use a fresh download directory')

async function api(path) {
  const response = await fetch(base + '/api' + path, { headers: { authorization } })
  assert.equal(response.status, 200, path)
  return response
}
const health = await api('/health')
assert.equal(health.headers.get('x-ap-compass-demo'), 'TEST_ONLY-controlled-demo')
assert.deepEqual(await (await api('/runs?limit=100')).json(), [], 'Use fresh disposable storage')
assert.equal((await fetch(base + '/api/exports/invoices.xlsx')).status, 401)
const cases = [
  ['HAPPY_CLEAN', 'READY_FOR_AP', 'tests/fixtures/HAPPY_CLEAN.pdf'],
  ['OVERBILLED_PARTIAL', 'BLOCKED', 'tests/fixtures/OVERBILLED_PARTIAL.pdf'],
  ['MISSING_PO_VALID', 'REVIEW_REQUIRED', 'tests/fixtures/human_resolution/MISSING_PO_VALID.pdf'],
  ['PRICE_3PCT', 'REVIEW_REQUIRED', 'tests/fixtures/PRICE_3PCT.pdf'],
  ['HAPPY_PARTIAL', 'READY_FOR_AP', 'tests/fixtures/HAPPY_PARTIAL.pdf'],
]
const paths = cases.map(([, , path]) => resolve(path))
const hash = (content) => createHash('sha256').update(content).digest('hex')
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
try {
  const page = await browser.newPage()
  await page.authenticate(credentials)
  const connection = await page.createCDPSession()
  await connection.send('Browser.setDownloadBehavior', {
    behavior: 'allow',
    downloadPath: downloads,
  })
  const events = []
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('response', (response) => {
    const path = new URL(response.url()).pathname
    const method = response.request().method()
    if (
      (method === 'POST' && path === '/api/runs') ||
      (method === 'GET' && /^\/api\/runs\/[^/]+$/.test(path))
    ) {
      const event = { method, path, status: response.status() }
      events.push(event)
      if (response.ok())
        void response.json().then((body) => {
          event.id = body.run_id ?? body.id
          event.state = body.execution_state
        })
    }
  })

  const capture = async (name) => {
    assert.ok(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <= innerWidth + 1 &&
          document.body.scrollWidth <= innerWidth + 1,
      ),
      name,
    )
    await page.screenshot({ path: resolve(output, name + '.png'), fullPage: true })
  }
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(base + '/', { waitUntil: 'networkidle0' })
  await page.click('a.button[href="/runs/upload"]')
  await page.waitForSelector('.batch-drop button')
  await capture('desktop-batch-empty')
  await (await page.$('input[type=file][multiple]')).uploadFile(...paths)
  await page.waitForFunction(() => document.querySelectorAll('.batch-list li').length === 5)
  await capture('desktop-five-selected')
  await page.setViewport({ width: 390, height: 844 })
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  assert.equal(
    await page.$eval('.batch-drop', (el) => getComputedStyle(el).transitionDuration),
    '0s',
  )
  await page.focus('.batch-list .icon-button')
  await page.keyboard.press('Tab')
  assert.equal(await page.evaluate(() => document.activeElement.matches(':focus-visible')), true)
  await capture('mobile-five-selected')

  await page.setViewport({ width: 1440, height: 1000 })
  await page.click('.batch-actions button.primary')
  await page.waitForFunction(() =>
    [...document.querySelectorAll('.batch-state')].some((state) =>
      /Uploading|Queued|Processing/.test(state.textContent),
    ),
  )
  await capture('desktop-batch-processing')
  await page.waitForFunction(
    () =>
      document.querySelector('.batch-heading [role="status"]')?.textContent === '5 of 5 finished',
    { timeout: 60_000 },
  )
  await capture('desktop-batch-results')
  await page.setViewport({ width: 390, height: 844 })
  await capture('mobile-batch-results')
  const links = await page.$$eval('.batch-list li', (entries) =>
    entries.map((entry) => ({
      file: entry.querySelector('strong').textContent,
      path: entry.querySelector('a').pathname,
      status: entry.querySelector('.status').textContent,
    })),
  )
  const persisted = await (await api('/runs?limit=100')).json()
  assert.equal(persisted.length, 5)
  const uploads = events.filter((event) => event.method === 'POST')
  assert.equal(uploads.length, 5)
  assert.equal(new Set(uploads.map((event) => event.id)).size, 5)
  assert.ok(uploads.every((event) => event.status === 202 && event.state === 'QUEUED'))
  const evidence = []
  for (const [index, [name, outcome]] of cases.entries()) {
    const link = links[index]
    const detail = await (await api(link.path)).json()
    assert.equal(link.file, name + '.pdf')
    assert.equal(
      link.status,
      { READY_FOR_AP: 'Ready to process', REVIEW_REQUIRED: 'Needs review', BLOCKED: 'Blocked' }[
        outcome
      ],
    )
    assert.equal(detail.id, uploads[index].id)
    assert.equal(detail.execution_state, 'COMPLETED')
    assert.equal(detail.decision.outcome, outcome)
    assert.equal(detail.model_id, 'TEST_ONLY-controlled-demo')
    assert.equal(detail.extracted_invoice.invoice_number, name + '-2026')
    const stored = Buffer.from(await (await api(link.path + '/document')).arrayBuffer())
    assert.equal(hash(stored), hash(await readFile(paths[index])))
    const terminal = events.findIndex(
      (event) => event.id === detail.id && event.state === 'COMPLETED',
    )
    assert.ok(terminal > events.indexOf(uploads[index]))
    if (index < 4) assert.ok(terminal < events.indexOf(uploads[index + 1]))
    evidence.push({
      case: name,
      id: detail.id,
      documentId: detail.document_id,
      sha256: hash(stored),
      execution: detail.execution_state,
      outcome,
      findings: detail.decision.findings.length,
      snapshot: detail,
    })
  }
  await page.click('.batch-list a')
  await page.waitForSelector('.ready-brief')
  await page.goto(base + '/runs', { waitUntil: 'networkidle0' })
  await page.waitForSelector('tbody tr')
  assert.equal(await page.$$eval('tbody tr', (rows) => rows.length), 5)
  await page.setViewport({ width: 1440, height: 1000 })
  await page.click('.export-invoices button')
  await page.waitForFunction(
    () =>
      document.querySelector('.export-invoices [role="status"]')?.textContent ===
      'Excel download started.',
  )
  let workbook
  for (let step = 0; step < 60 && !workbook; step++) {
    workbook = (await readdir(downloads)).find((name) => name.endsWith('.xlsx'))
    if (!workbook) await new Promise((done) => setTimeout(done, 200))
  }
  assert.match(workbook, /^ap-compass-invoice-register-\d{4}-\d{2}-\d{2}\.xlsx$/)
  assert.equal(
    (await readFile(resolve(downloads, workbook))).subarray(0, 4).toString('hex'),
    '504b0304',
  )
  await capture('desktop-queue-excel-download')
  const dashboard = await (await api('/dashboard')).json()
  assert.deepEqual(
    [dashboard.completed, dashboard.ready, dashboard.review_required, dashboard.blocked],
    [5, 2, 2, 1],
  )

  // TEST_ONLY failure injection. No additional upload reaches the backend.
  await page.setRequestInterception(true)
  page.on('request', (request) => {
    const path = new URL(request.url()).pathname
    if (request.method() === 'POST' && path === '/api/runs')
      return request.respond({ status: 429, contentType: 'application/json', body: '{}' })
    return request.continue()
  })
  await page.click('a.button[href="/runs/upload"]')
  await page.waitForSelector('input[multiple]')
  await (await page.$('input[multiple]')).uploadFile(paths[0])
  await page.click('.batch-actions button.primary')
  await page.waitForSelector('.batch-item-error')
  assert.match(await page.$eval('.batch-item-error', (el) => el.textContent), /invoice capacity/)
  await capture('desktop-upload-429-test-only')
  assert.deepEqual(await (await api('/runs?limit=100')).json(), persisted)
  assert.deepEqual(errors, [])
  await writeFile(
    resolve(output, 'browser.json'),
    JSON.stringify({ evidence, workbook, dashboard }, null, 2),
  )
  console.log(
    'Five Chrome uploads accepted and completed serially, original PDFs verified, workbook downloaded, and authenticated TEST_ONLY 429 displayed.',
  )
} finally {
  await browser.close()
}
