/** Signature UI review capture. Read-only persisted data and policy previews; never uploads. */
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'
const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:8006'
const out = resolve(process.env.AP_COMPASS_SIGNATURE_QA_DIR ?? 'tmp/phase06a1-after/signature')
await mkdir(out, { recursive: true })
const get = async (path) => {
  const r = await fetch(base + '/api' + path)
  assert.equal(r.status, 200)
  return r.json()
}
const summaries = await get('/runs?limit=100')
const before = await Promise.all(summaries.map((r) => get('/runs/' + r.id)))
const blocked = before.find((r) => r.decision?.primary_reason_code === 'PO_BALANCE_EXCEEDED')
const price = before.find((r) => r.extracted_invoice?.invoice_number === 'PRICE_3PCT-2026')
assert.ok(blocked && price)
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const pause = (ms) => new Promise((r) => setTimeout(r, ms)) // Viewing time in a recorded demonstration only; never stage progression.
const results = {
  checks: [],
  positions: [],
  frames: 0,
  recording: 'Chrome CDP actual frames; no synthetic stages',
  newModelCalls: 0,
}
try {
  const page = await browser.newPage()
  const errors = []
  const writes = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('request', (r) => {
    if (!['GET', 'HEAD'].includes(r.method())) writes.push(new URL(r.url()).pathname)
  })
  for (const width of [1440, 1024, 390]) {
    await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
    await page.goto(base + '/runs/' + blocked.id, { waitUntil: 'networkidle0' })
    await page.waitForSelector('.blocked-brief')
    const position = await page.evaluate(() => ({
      source: document.querySelector('.document-panel').getBoundingClientRect().top,
      decision: document.querySelector('.decision-brief').getBoundingClientRect().top,
      overflow: document.body.scrollWidth > innerWidth + 1,
    }))
    assert.equal(position.overflow, false)
    if (width > 900) assert.ok(Math.abs(position.source - position.decision) < 2)
    results.positions.push({ width, ...position })
    await page.click('a[href="#evidence"]')
    await page.keyboard.press('Tab') // Enter keyboard modality before testing :focus-visible.
    const evidence = await page.$('.evidence-item summary')
    await evidence.focus()
    assert.equal(await evidence.evaluate((e) => getComputedStyle(e).outlineStyle), 'solid')
    const clear = await page.evaluate(
      () =>
        document.activeElement.getBoundingClientRect().top >=
        document.querySelector('.case-nav').getBoundingClientRect().bottom,
    )
    assert.ok(clear, 'Sticky navigation must not cover focused evidence')
    await page.keyboard.press('Enter')
    assert.equal(await page.$eval('.evidence-item', (e) => e.open), true)
    await page.click('a[href="#case-trace"]')
    await (
      await page.$('.decision-trace')
    ).screenshot({ path: out + `/completed-trace-${width}.png` })
  }
  results.checks.push(
    'Source and primary decision top-aligned on desktop/laptop; keyboard evidence expansion not covered by navigation; no overflow at all widths',
  )
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(base, { waitUntil: 'networkidle0' })
  const cdp = await page.createCDPSession()
  const frames = []
  const saves = []
  let last = 0
  cdp.on('Page.screencastFrame', (event) => {
    void cdp.send('Page.screencastFrameAck', { sessionId: event.sessionId })
    const timestamp = event.metadata.timestamp ?? Date.now() / 1000
    if (timestamp - last < 0.09) return
    last = timestamp
    const file = `frame-${String(frames.length).padStart(4, '0')}.jpg`
    frames.push({ file, timestamp })
    saves.push(writeFile(out + '/' + file, Buffer.from(event.data, 'base64')))
  })
  await cdp.send('Page.startScreencast', {
    format: 'jpeg',
    quality: 75,
    maxWidth: 1080,
    maxHeight: 750,
    everyNthFrame: 1,
  })
  await pause(1300)
  await page.hover('.attention-workload .metric')
  await pause(800)
  await page.goto(base + '/runs/' + blocked.id, { waitUntil: 'networkidle0' })
  await pause(1400)
  await page.click('a[href="#case-trace"]')
  await pause(1000)
  await page.focus('.trace-node summary')
  await page.keyboard.press('Enter')
  await pause(1200)
  await page.goto(base + '/runs/' + price.id, { waitUntil: 'networkidle0' })
  await page.click('a[href="#case-policy"]')
  await page.click('.policy-impact > summary')
  await pause(900)
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname.endsWith('/policy-preview') && r.request().method() === 'POST',
    ),
    page.click('.tolerance-options input[value="0.05"]'),
  ])
  assert.equal(response.status(), 200)
  assert.equal((await response.json()).preview_decision.outcome, 'READY_FOR_AP')
  await page.waitForSelector('.preview-status .status')
  await pause(1700)
  await cdp.send('Page.stopScreencast')
  await Promise.all(saves)
  assert.ok(frames.length > 10)
  await writeFile(out + '/frames.json', JSON.stringify(frames, null, 2))
  results.frames = frames.length
  const tree = await cdp.send('Accessibility.getFullAXTree')
  assert.ok(tree.nodes.some((n) => n.role?.value === 'heading' && !n.ignored))
  assert.ok(tree.nodes.some((n) => n.role?.value === 'radio' && !n.ignored))
  assert.deepEqual(errors, [])
  assert.ok(writes.every((path) => path.endsWith('/policy-preview')))
  assert.deepEqual(await Promise.all(summaries.map((r) => get('/runs/' + r.id))), before)
  assert.deepEqual(await get('/runs?limit=100'), summaries)
  results.checks.push(
    'Actual Chrome interaction frames recorded; real 5% preview Ready while original remains Review; accessible heading/radio exposed; zero uploads; all stored snapshots unchanged; no JS errors',
  )
  await writeFile(out + '/results.json', JSON.stringify(results, null, 2))
  console.log(JSON.stringify(results, null, 2))
} finally {
  await browser.close()
}
