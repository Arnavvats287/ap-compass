/** Read-only visual checks on separate loopback rehearsal and technical-failure stores. */
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'

const [rehearsalPath, technicalPath, outputPath] = process.argv.slice(2)
assert.ok(rehearsalPath && technicalPath && outputPath)
const output = resolve(outputPath)
await mkdir(output, { recursive: true })

async function settings(path) {
  const lines = (await readFile(path, 'utf8')).trim().split(/\r?\n/)
  const env = Object.fromEntries(lines.map((line) => line.split(/=(.*)/s).slice(0, 2)))
  const origin = env.AP_COMPASS_PRIVATE_ORIGIN
  assert.equal(new URL(origin).hostname, '127.0.0.1')
  const credentials = {
    username: env.AP_COMPASS_PRIVATE_USERNAME,
    password: env.AP_COMPASS_PRIVATE_PASSWORD,
  }
  const headers = {
    Authorization:
      'Basic ' + Buffer.from(credentials.username + ':' + credentials.password).toString('base64'),
  }
  const get = async (path) => {
    const response = await fetch(origin + '/api' + path, { headers })
    assert.equal(response.status, 200, path)
    return response.json()
  }
  return { origin, credentials, get }
}

const rehearsal = await settings(rehearsalPath)
const technical = await settings(technicalPath)
const runs = await rehearsal.get('/runs?limit=100')
const failed = (await technical.get('/runs?limit=100')).find(
  (item) => item.execution_state === 'PROCESSING_FAILED',
)
assert.ok(failed)
const dashboard = await rehearsal.get('/dashboard')
assert.deepEqual(
  [dashboard.total_runs, dashboard.ready, dashboard.review_required, dashboard.blocked],
  [8, 2, 4, 2],
)
const gross = Object.fromEntries(
  Object.entries(dashboard.invoice_gross).map(([key, projection]) => {
    assert.equal(projection.missing_count, 0)
    assert.deepEqual(Object.keys(projection.by_currency), ['INR'])
    return [key, Number(projection.by_currency.INR)]
  }),
)
assert.deepEqual(gross, {
  submitted: 221545,
  ready: 55460,
  review_required: 118885,
  blocked: 47200,
})
const technicalDashboard = await technical.get('/dashboard')
assert.equal(technicalDashboard.invoice_gross.submitted.missing_count, 8)
assert.ok(
  ['ready', 'review_required', 'blocked'].every(
    (key) => Object.keys(technicalDashboard.invoice_gross[key].by_currency).length === 0,
  ),
)

const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const captures = []
const errors = []
const writes = []
const details = []

async function open(config) {
  const page = await browser.newPage()
  await page.authenticate(config.credentials)
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('request', (req) => {
    if (new URL(req.url()).pathname.startsWith('/api/') && !['GET', 'HEAD'].includes(req.method()))
      writes.push(req.url())
  })
  return page
}

async function geometry(page) {
  assert.equal(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <= innerWidth + 1 &&
        document.body.scrollWidth <= innerWidth + 1,
    ),
    true,
  )
}

async function capture(page, name, selector) {
  await geometry(page)
  await page.waitForSelector(selector)
  const clip = await page.$eval(selector, (element) => {
    scrollTo(0, 0)
    const { x, y, width, height } = element.getBoundingClientRect()
    return { x: x + scrollX, y: y + scrollY, width, height }
  })
  await page.screenshot({ path: resolve(output, name + '.png'), clip, captureBeyondViewport: true })
  captures.push(name + '.png')
}

try {
  const page = await open(rehearsal)
  for (const width of [1440, 390]) {
    await page.setViewport({ width, height: width === 390 ? 844 : 1000 })
    await page.goto(rehearsal.origin, { waitUntil: 'networkidle0' })
    assert.deepEqual(
      await page.$$eval('.financial-card dd', (cells) => cells.map((cell) => cell.textContent)),
      ['₹2,21,545', '₹55,460', '₹1,18,885', '₹47,200'],
    )
    await capture(page, 'financial-' + width, '.financial-overview')
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: resolve(output, 'overview-' + width + '.png'), fullPage: true })
    captures.push('overview-' + width + '.png')
  }
  const views = [
    ['ready', 'MC-2611-207', 'READY_FOR_AP', 'journey-ink', '.journey-glyph-mark'],
    ['review', 'KL-2611-323', 'REVIEW_REQUIRED', 'journey-attention', '.journey-glyph-mark'],
    ['blocked', 'AS-2611-173', 'BLOCKED', 'journey-block', '.journey-glyph'],
    ['stopped', null, null, 'journey-stop', '.journey-glyph-mark'],
  ]
  for (const [kind, invoice, outcome, animation, selector] of views) {
    const config = kind === 'stopped' ? technical : rehearsal
    const run = invoice ? runs.find((row) => row.invoice_number === invoice) : failed
    assert.ok(run)
    const before = await config.get('/runs/' + run.id)
    assert.equal(before.decision?.outcome ?? null, outcome)
    const tab = await open(config)
    await tab.setViewport({ width: 1440, height: 1000 })
    await tab.goto(config.origin + '/runs/' + run.id, { waitUntil: 'networkidle0' })
    await tab.click('.case-nav a[href="#case-trace"]')
    await tab.waitForSelector('.journey-result.journey-' + kind)
    if (outcome) {
      await tab.waitForFunction(
        () =>
          document.querySelector('.decision-journey').getBoundingClientRect().top >=
          document.querySelector('.case-nav').getBoundingClientRect().bottom - 1,
      )
    }
    await tab.$eval('.journey-result', (element) => element.scrollIntoView({ block: 'center' }))
    await tab.waitForSelector('.journey-result-icon[data-reveal="true"]')
    assert.equal(
      await tab.$eval(selector, (element) => getComputedStyle(element).animationName),
      animation,
    )
    const first = '.journey-node summary'
    await tab.focus('.journey-heading button')
    await tab.keyboard.press('Tab')
    assert.ok(
      await tab.$eval(
        first,
        (element) =>
          element === document.activeElement &&
          element.matches(':focus-visible') &&
          getComputedStyle(element).outlineStyle === 'solid',
      ),
    )
    await tab.keyboard.press('Enter')
    assert.equal(await tab.$eval('.journey-node', (element) => element.open), true)
    await tab.$eval('.journey-glyph', (element) => {
      element.dataset.replayCheck = 'old'
    })
    await tab.focus('.journey-heading button')
    await tab.keyboard.press('Enter')
    assert.equal(
      await tab.$eval('.journey-glyph', (element) => element.dataset.replayCheck),
      undefined,
    )
    assert.ok(
      await tab.$eval('.journey-glyph', (element) =>
        element
          .getAnimations({ subtree: true })
          .some((animation) => animation.playState === 'running'),
      ),
    )
    assert.equal(await tab.$eval('.journey-node', (element) => element.open), true)
    assert.equal(
      await tab.$$eval('.journey-stage', (stages) => stages.length),
      before.stages.length,
    )
    await tab.$eval('.journey-glyph', (element) =>
      Promise.allSettled(element.getAnimations({ subtree: true }).map((item) => item.finished)),
    )
    await tab.$$eval(
      '.journey-node',
      (disclosures, index) => {
        disclosures[0].open = false
        disclosures[index].open = true
      },
      kind === 'blocked' ? 3 : 1,
    )
    await capture(tab, kind + '-journey-1440', '.decision-journey')
    if (kind === 'blocked') {
      const comparison = await tab.$eval(
        '.journey-result .exception-comparison',
        (element) => element.textContent,
      )
      for (const amount of ['₹25,000', '₹35,000', '₹10,000']) assert.ok(comparison.includes(amount))
      assert.equal(
        await tab.$eval('.journey-owner', (element) => element.textContent.includes('Procurement')),
        true,
      )
    }
    if (kind === 'stopped') {
      assert.equal(
        await tab.$eval('.journey-result', (el) =>
          el.textContent.includes('No AP decision produced'),
        ),
        true,
      )
    }
    await tab.setViewport({ width: 390, height: 844 })
    await tab.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
    await tab.click('.journey-heading button')
    assert.equal(
      await tab.$eval(
        '.decision-journey',
        (element) => element.getAnimations({ subtree: true }).length,
      ),
      0,
    )
    assert.equal(await tab.$$eval('.journey-node[open]', (opened) => opened.length), 1)
    await capture(tab, kind + '-journey-390', '.decision-journey')
    assert.deepEqual(await config.get('/runs/' + run.id), before)
    details.push({ kind, id: run.id, animation, outcome })
    await tab.close()
  }
  assert.deepEqual(writes, [])
  assert.deepEqual(errors, [])
  await writeFile(
    resolve(output, 'browser-proof.json'),
    JSON.stringify({ gross, captures, details }, null, 2),
  )
  console.log(
    'Chrome passed four recorded endings, keyboard expansion/replay, reduced motion, gross totals, and unchanged snapshots.',
  )
} finally {
  await browser.close()
}
