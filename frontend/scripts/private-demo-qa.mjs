/** Loopback Chrome checks against an isolated, explicitly controlled demo store. */
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'

const [settings, destination, mode] = process.argv.slice(2)
assert.ok(settings && destination, 'Pass the ignored private environment file and QA output directory')
assert.ok(mode === undefined || mode === '--restart', 'Unknown QA mode')
const env = Object.fromEntries((await readFile(settings, 'utf8')).split(/\r?\n/)
  .filter((line) => /^AP_COMPASS_[A-Z_]+=/.test(line))
  .map((line) => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)]))
const base = env.AP_COMPASS_PRIVATE_ORIGIN
assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(base).hostname))
const credentials = { username: env.AP_COMPASS_PRIVATE_USERNAME, password: env.AP_COMPASS_PRIVATE_PASSWORD }
const authorization = 'Basic ' + Buffer.from(credentials.username + ':' + credentials.password).toString('base64')
const get = async (path) => {
  const response = await fetch(base + path, { headers: { authorization }, redirect: 'error' })
  assert.equal(response.status, 200, path)
  return response
}
const json = async (path) => (await get(path)).json()
const output = resolve(destination)
await mkdir(output, { recursive: true })
const hash = (value) => createHash('sha256').update(JSON.stringify(value)).digest('hex')
if (mode === '--restart') {
  const evidence = JSON.parse(await readFile(resolve(output, 'browser.json'), 'utf8'))
  assert.equal((await get('/api/health')).headers.get('x-ap-compass-demo'), null)
  assert.equal((await fetch(base + '/api/runs', { method: 'POST', headers: { authorization, origin: base } })).status, 403)
  for (const { id, pdfHash, snapshotHash } of Object.values(evidence.runs)) {
    assert.equal(hash(await json('/api/runs/' + id)), snapshotHash)
    const pdf = await get('/api/runs/' + id + '/document')
    assert.equal(createHash('sha256').update(Buffer.from(await pdf.arrayBuffer())).digest('hex'), pdfHash)
  }
  const history = await json('/api/runs/' + evidence.runs.MISSING_PO_VALID.id + '/review-history')
  assert.equal(hash(history), evidence.historyHash)
  console.log('Private container restart passed: uploads disabled and all four snapshots, PDFs and audit history unchanged')
  process.exit(0)
}
const rows = Object.fromEntries((await json('/api/runs')).map((row) => [row.invoice_number.split('-2026')[0], row]))
const baseline = {}
for (const [name, outcome] of Object.entries({
  HAPPY_CLEAN: 'READY_FOR_AP',
  OVERBILLED_PARTIAL: 'BLOCKED',
  MISSING_PO_VALID: 'REVIEW_REQUIRED',
  PRICE_3PCT: 'REVIEW_REQUIRED',
})) {
  const path = '/api/runs/' + rows[name].id
  assert.equal((await fetch(base + path + '/document')).status, 401)
  const run = await json(path)
  assert.equal(run.decision.outcome, outcome)
  assert.equal(run.model_id, 'TEST_ONLY-controlled-demo')
  const pdf = await get(path + '/document')
  baseline[name] = { id: run.id, outcome, run, pdfHash: createHash('sha256').update(Buffer.from(await pdf.arrayBuffer())).digest('hex') }
}
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const pathFor = (name) => '/runs/' + baseline[name].id
const textIncludes = (page, selector, expected) => page.waitForFunction(
  (element, value) => document.querySelector(element)?.textContent.includes(value), {}, selector, expected)
try {
  const guest = await browser.newPage()
  // Headless Chrome may abort a main-frame HTTP authentication challenge when no credentials are supplied.
  const challenge = await guest.goto(base + '/api/health').catch((error) => error)
  assert.ok(challenge?.status?.() === 401 || /ERR_INVALID_AUTH_CREDENTIALS/.test(challenge?.message))
  assert.equal((await fetch(base + '/api/health')).status, 401)
  await guest.close()
  const page = await browser.newPage()
  await page.authenticate(credentials)
  await page.setViewport({ width: 1440, height: 1000 })
  const errors = []
  page.on('pageerror', (error) => errors.push(error.name))
  assert.equal((await page.goto(base + '/')).status(), 200)
  const blockedPath = pathFor('OVERBILLED_PARTIAL')
  const pdfLoaded = page.waitForResponse((response) => response.url().split('#')[0] === base + '/api' + blockedPath + '/document'
    && response.status() === 200)
  assert.equal((await page.goto(base + blockedPath)).status(), 200)
  await textIncludes(page, '.decision-header', 'Controlled extraction (TEST_ONLY)')
  await page.locator('iframe[title="Original invoice PDF"]').scroll()
  const pdf = await pdfLoaded
  const headers = pdf.headers()
  assert.equal(headers['content-type'], 'application/pdf')
  assert.equal(headers['x-content-type-options'], 'nosniff')
  assert.equal(headers['x-frame-options'], 'SAMEORIGIN')
  assert.equal(headers['cache-control'], 'no-store')
  assert.match(headers['content-security-policy'], /frame-ancestors 'self'/)
  const iframe = await page.waitForSelector('iframe[title="Original invoice PDF"]')
  const pdfFrame = await iframe.contentFrame()
  assert.ok(pdfFrame && pdfFrame.url().startsWith(base + '/api' + blockedPath + '/document'))
  assert.equal((await page.reload()).status(), 200)
  await textIncludes(page, '.decision-header', 'Blocked')
  await page.locator('iframe[title="Original invoice PDF"]').scroll()
  await page.screenshot({ path: resolve(output, 'blocked-authenticated.png'), fullPage: false })
  console.log('Private browser challenge, same-origin PDF request and deep link passed')

  await page.goto(base + pathFor('MISSING_PO_VALID'))
  const action = page.locator('::-p-aria(Review PO candidates)')
  await action.click()
  await page.locator('input[name="confirmed-po"][value="PO-1042"]').click()
  await page.locator('::-p-aria(Demo reviewer label)').fill('Controlled demo reviewer')
  await page.locator('textarea').fill('Confirmed the intended hosting order against the synthetic procurement record.')
  const saved = page.waitForResponse((response) => response.url().endsWith('/po-confirmations'))
  await page.locator('::-p-aria(Confirm PO & re-evaluate)').click()
  assert.equal((await saved).status(), 201)
  await textIncludes(page, '[aria-label="Current reassessment"]', 'Ready to process')
  assert.equal((await json('/api' + pathFor('MISSING_PO_VALID'))).decision.outcome, 'REVIEW_REQUIRED')
  await page.screenshot({ path: resolve(output, 'review-reassessment.png'), fullPage: false })

  await page.goto(base + pathFor('PRICE_3PCT'))
  await page.locator('details.policy-impact > summary').click()
  await page.locator('input[value="0.05"]').click()
  await textIncludes(page, '.preview-status', 'Ready to process')
  await textIncludes(page, '.decision-header', 'Needs review')
  await page.screenshot({ path: resolve(output, 'policy-preview.png'), fullPage: false })
  assert.deepEqual(errors, [])

  for (const row of Object.values(baseline)) assert.deepEqual(await json('/api/runs/' + row.id), row.run)
  const history = await json('/api' + pathFor('MISSING_PO_VALID') + '/review-history')
  // Persist only hashes of snapshots and audit records, never their raw contents.
  await writeFile(resolve(output, 'browser.json'), JSON.stringify({
    runs: Object.fromEntries(Object.entries(baseline).map(([name, { id, outcome, pdfHash, run }]) =>
      [name, { id, outcome, pdfHash, snapshotHash: hash(run) }])),
    historyHash: hash(history),
    checks: ['browser auth challenge', 'authenticated PDF embed and headers', 'deep link reload',
      'saved PO action with original unchanged', 'read-only 5% Ready preview', 'immutable snapshots'],
  }, null, 2))
  console.log('Private Chrome QA passed: access, PDF embed, deep link, human review, policy preview')
} finally {
  await browser.close()
}
