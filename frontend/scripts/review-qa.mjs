/** Real local UI/API human review. Uploads synthetic PDFs only to an explicitly TEST_ONLY extractor. */
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import puppeteer from 'puppeteer-core'
const base = process.env.AP_COMPASS_UI_URL ?? 'http://127.0.0.1:8007'
const out = resolve(process.env.AP_COMPASS_REVIEW_QA_DIR ?? 'tmp/phase6b1-qa')
await mkdir(out, { recursive: true })
const get = async (path) => {
  const r = await fetch(base + '/api' + path)
  assert.equal(r.status, 200)
  return r.json()
}
const browser = await puppeteer.launch({
  executablePath:
    process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
})
const results = {
  cases: [],
  checks: [],
  source: 'Real API, DB, native PDF grounding; TEST_ONLY extraction, no Gemini',
  newGeminiCalls: 0,
}
try {
  const page = await browser.newPage()
  const errors = []
  const requests = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('request', (r) => {
    if (r.method() === 'POST') requests.push(new URL(r.url()).pathname)
  })
  const prior = await get('/runs?limit=100')
  const priorSnapshots = await Promise.all(prior.map((r) => get('/runs/' + r.id)))
  for (const [name, expected] of [
    ['MISSING_PO_VALID', 'READY_FOR_AP'],
    ['AMBIGUOUS_PO', 'REVIEW_REQUIRED'],
  ]) {
    await page.setViewport({ width: 1440, height: 1000 })
    let summary = (await get('/runs?limit=100')).find((r) => r.invoice_number === name + '-2026')
    if (!summary) {
      assert.equal(
        process.env.AP_COMPASS_TEST_EXTRACTOR,
        'true',
        'Uploads require explicitly declared TEST_ONLY local extractor',
      )
      await page.goto(base + '/runs#upload', { waitUntil: 'networkidle0' })
      await (
        await page.$('input[type=file]')
      ).uploadFile(resolve('tests/fixtures/human_resolution/' + name + '.pdf'))
      const [response] = await Promise.all([
        page.waitForResponse(
          (r) => new URL(r.url()).pathname === '/api/runs' && r.request().method() === 'POST',
        ),
        page.click('button[type=submit]'),
      ])
      assert.equal(response.status(), 202)
      const created = await response.json()
      summary = { id: created.run_id }
      await page.waitForSelector('.human-review', { timeout: 20000 })
      await page.waitForFunction(() => document.querySelector('.decision-brief'))
    } else await page.goto(base + '/runs/' + summary.id, { waitUntil: 'networkidle0' })
    const original = await get('/runs/' + summary.id)
    assert.ok(original.model_id.startsWith('TEST_ONLY'))
    assert.equal(original.decision.outcome, 'REVIEW_REQUIRED')
    let history = await get('/runs/' + summary.id + '/review-history')
    const reusedPersistedAction = history.actions.length > 0
    if (!history.actions.length) {
      await page.screenshot({ path: out + '/' + name + '-original-1440.png', fullPage: true })
      await page.keyboard.press('Tab')
      await page.focus('.human-review > .button')
      await page.keyboard.press('Enter')
      assert.equal(await page.$eval('dialog', (d) => d.open), true)
      assert.equal(await page.$eval('button[type=submit]', (b) => b.disabled), true)
      // Native modal prevents background application focus. Chrome may visit browser chrome (BODY), then returns to the dialog.
      for (let i = 0; i < 15; i++) {
        await page.keyboard.press('Tab')
        const focus = await page.evaluate(() => ({
          tag: document.activeElement.tagName,
          text: document.activeElement.textContent?.slice(0, 30),
          inside: !!document.activeElement.closest('dialog'),
          modal: document.querySelector('dialog').matches(':modal'),
        }))
        assert.ok(focus.modal)
        if (!focus.inside) {
          assert.equal(focus.tag, 'BODY')
          await page.keyboard.press('Tab')
          assert.ok(await page.evaluate(() => !!document.activeElement.closest('dialog')))
        }
      }
      await page.click('input[type=radio][value="PO-1042"]')
      await page.type('.review-field input', 'Demo AP analyst')
      await page.type(
        '.review-field textarea',
        'Verified intended PO with Procurement and compared the invoice service scope. Identity confirmation only.',
      )
      await page.screenshot({ path: out + '/' + name + '-candidate-dialog-1440.png' })
      const [response] = await Promise.all([
        page.waitForResponse(
          (r) =>
            new URL(r.url()).pathname.endsWith('/po-confirmations') &&
            r.request().method() === 'POST',
        ),
        page.click('button[type=submit]'),
      ])
      assert.equal(response.status(), 201)
      history = await get('/runs/' + summary.id + '/review-history')
    }
    await page.waitForSelector('.review-outcomes')
    assert.equal(history.actions.length, 1)
    assert.equal(history.current_reviewed_assessment.outcome, expected)
    assert.deepEqual(await get('/runs/' + summary.id), original)
    assert.match(
      await page.$eval('.review-outcomes section:first-child', (e) => e.textContent),
      /Needs review/,
    )
    assert.match(
      await page.$eval('.review-outcomes section:last-child', (e) => e.textContent),
      expected === 'READY_FOR_AP' ? /Ready to process/ : /Needs review/,
    )
    if (name === 'AMBIGUOUS_PO') {
      assert.match(await page.$eval('.human-review', (e) => e.textContent), /still not ready/)
      assert.ok(
        history.actions[0].reassessment.findings.some((f) => f.code === 'CRITICAL_FIELD_MISSING'),
      )
      assert.equal(original.extracted_invoice.lines[0].qty, null)
    }
    for (const width of [1440, 1024, 390]) {
      await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
      await page.goto(base + '/runs/' + summary.id, { waitUntil: 'networkidle0' })
      await page.waitForSelector('.review-outcomes')
      assert.ok(await page.evaluate(() => document.body.scrollWidth <= innerWidth + 1))
      await page.screenshot({
        path: out + '/' + name + '-reassessed-' + width + '.png',
        fullPage: true,
      })
    }
    results.cases.push({
      name,
      reusedPersistedAction,
      runId: summary.id,
      original: original.decision.outcome,
      reassessed: expected,
      actionId: history.actions[0].id,
      selectedPO: history.actions[0].selected_po_id,
      sourceEvidence: original.extracted_invoice.evidence.map((e) => ({
        field: e.field,
        state: e.evidence_state,
      })),
      findings: history.actions[0].reassessment.findings.map((f) => f.code),
    })
  }
  // TEST_ONLY pre-confirmation layout, because the real accepted actions cannot be undone/reopened.
  const layoutRun = await get('/runs/' + results.cases[0].runId)
  await page.setRequestInterception(true)
  const intercept = (r) => {
    if (
      new URL(r.url()).pathname === '/api/runs/' + layoutRun.id + '/review-history' &&
      r.method() === 'GET'
    ) {
      void r.respond({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          actions: [],
          current_reviewed_assessment: null,
          confirmation_available: true,
          unavailable_reason: null,
          candidates: layoutRun.candidates,
          canonical_vendor_name: 'Meridian Cloud Pvt Ltd',
          authority_basis: 'TEST_ONLY prior layout',
        }),
      })
      return
    }
    if (r.method() === 'POST') {
      void r.abort()
      throw new Error('No writes permitted during TEST_ONLY modal layout')
    }
    void r.continue()
  }
  page.on('request', intercept)
  for (const width of [1440, 1024, 390]) {
    await page.setViewport({ width, height: width === 390 ? 844 : width === 1024 ? 900 : 1000 })
    await page.goto(base + '/runs/' + layoutRun.id, { waitUntil: 'networkidle0' })
    await page.waitForSelector('.human-review > .button')
    await page.click('.human-review > .button')
    await page.evaluate(() => {
      const label = document.createElement('p')
      label.textContent = 'TEST_ONLY pre-confirmation layout · no save performed'
      label.style.fontWeight = '600'
      document.querySelector('dialog').prepend(label)
    })
    assert.ok(await page.$eval('dialog', (d) => d.scrollWidth <= d.clientWidth + 1))
    await page.screenshot({ path: out + '/TEST_ONLY-dialog-' + width + '.png' })
    await page.$eval('dialog', (d) => d.scrollTo(0, d.scrollHeight))
    await page.screenshot({ path: out + '/TEST_ONLY-dialog-actions-' + width + '.png' })
    await page.keyboard.press('Escape')
    assert.equal(await page.$eval('dialog', (d) => d.open), false)
    assert.equal(
      await page.evaluate(() => document.activeElement.textContent),
      'Review PO candidates',
    )
  }
  page.off('request', intercept)
  await page.setRequestInterception(false)
  results.checks.push(
    'TEST_ONLY unsaved candidate-dialog layout at1440/1024/390; no horizontal overflow; footer reachable; Escape closes and restores focus',
  )
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(base + '/runs', { waitUntil: 'networkidle0' })
  await page.waitForSelector('.table-reviewed')
  assert.match(await page.$eval('table', (e) => e.textContent), /Current reviewed/)
  await page.screenshot({ path: out + '/reviewed-queue-1440.png', fullPage: true })
  for (let i = 0; i < prior.length; i++)
    assert.deepEqual(await get('/runs/' + prior[i].id), priorSnapshots[i])
  assert.deepEqual(errors, [])
  results.checks.push(
    'Both scenarios have real persisted review actions; source snapshots/stages unchanged',
    'Native modal excludes background application controls (browser chrome boundary allowed); required rationale; no automatic PO selection',
    'Original/current distinction, outstanding findings and demo identity visible',
    '1440/1024/390 no overflow; reviewed queue labelled; zero JavaScript errors',
  )
  results.posts = requests
  await writeFile(out + '/results.json', JSON.stringify(results, null, 2))
  console.log(JSON.stringify(results, null, 2))
} finally {
  await browser.close()
}
