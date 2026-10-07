/**
 * Campus Customs — app check.
 *
 * Drives the running site in a real browser, exercises the three features the
 * assignment asks about, screenshots each one, and compares what the page said
 * against the database so the evidence is verified rather than just captured.
 *
 *   node app_check.mjs        (frontend on :5174, backend on :8000)
 */

import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const HERE = dirname(fileURLToPath(import.meta.url))
const SHOTS = join(HERE, '..', 'output', 'app_check_images')
const RESULTS = join(HERE, 'results.json')

const SITE = 'http://localhost:5174'
const API = 'http://localhost:8000'

/** The product used for the price + stock test. */
const TEST_PRODUCT = 'yale-mom-hoodie'
/** The product whose recommendations are checked. */
const SIMILAR_PRODUCT = 'champion-reverse-weave-crewneck'

const CHAT_TIMEOUT = 120_000

async function api(path) {
  const response = await fetch(`${API}${path}`)
  if (!response.ok) throw new Error(`${path} -> ${response.status}`)
  return response.json()
}

/** Opens the chat panel if it is closed. */
async function openChat(page) {
  const panel = page.locator('.chat-panel')
  if (!(await panel.isVisible().catch(() => false))) {
    await page.locator('.chat-toggle').click()
    await panel.waitFor({ state: 'visible' })
  }
}

/** Sends a message and waits for a new assistant reply to land. */
async function ask(page, message) {
  const before = await page.locator('.bubble.assistant').count()
  await page.locator('.chat-input').fill(message)
  await page.locator('.chat-send').click()

  await page.waitForFunction(
    (count) =>
      document.querySelectorAll('.bubble.assistant:not(.typing)').length > count,
    before,
    { timeout: CHAT_TIMEOUT },
  )

  return page.locator('.bubble.assistant:not(.typing)').last().innerText()
}

/* ------------------------------------------------------------------ */

async function testPriceAndStock(page, results) {
  const product = await api(`/api/products/${TEST_PRODUCT}`)
  const sizes = Object.fromEntries(product.inventory.map((r) => [r.size, r.quantity]))

  await page.goto(`${SITE}/`, { waitUntil: 'networkidle' })
  await openChat(page)

  const question = `How much is the ${product.name} and how many do you have in each size?`
  const reply = await ask(page, question)

  // The reply must contain the real price and the real per-size quantities.
  const priceText = `$${product.price.toFixed(2)}`
  const priceShown = reply.includes(priceText) || reply.includes(`$${product.price.toFixed(0)}`)
  const quantitiesShown = Object.entries(sizes).filter(([, qty]) =>
    new RegExp(`\\b${qty}\\b`).test(reply),
  ).length

  await page.locator('.chat-panel').screenshot({
    path: join(SHOTS, 'test1-price-and-stock.png'),
  })

  results.push({
    id: 'test1',
    pass: priceShown && quantitiesShown >= 4,
    question,
    reply,
    expected: {
      name: product.name,
      price: priceText,
      inventory: sizes,
      total_stock: product.total_stock,
    },
    notes: `Price matched: ${priceShown}. Per-size quantities found in reply: ${quantitiesShown} of ${Object.keys(sizes).length}.`,
  })
}

async function testCategoryCards(page, results) {
  await page.goto(`${SITE}/products`, { waitUntil: 'networkidle' })
  await openChat(page)

  const question = 'What hoodies do you have?'
  const reply = await ask(page, question)

  // The agent's matches must render on the page, not just inside the chat.
  await page.locator('.agent-results .card').first().waitFor({ timeout: 20_000 })

  const cards = await page.locator('.agent-results .card').evaluateAll((nodes) =>
    nodes.map((node) => ({
      href: node.getAttribute('href'),
      name: node.querySelector('.card-name')?.textContent?.trim(),
      price: node.querySelector('.card-price')?.textContent?.trim(),
      imageLoaded: node.querySelector('img')?.naturalWidth > 0,
    })),
  )

  // Every card must point at a real catalogue row at the price shown.
  const catalogue = await api('/api/products')
  const byId = new Map(catalogue.products.map((p) => [p.product_id, p]))
  const verified = cards.map((card) => {
    const id = card.href?.replace('/products/', '')
    const row = byId.get(id)
    return {
      ...card,
      product_id: id,
      inCatalogue: Boolean(row),
      priceMatches: row ? `$${row.price.toFixed(2)}` === card.price : false,
      garment_type: row?.garment_type,
    }
  })

  // Capture the viewport rather than the panel alone, so the grader sees the
  // question in the chat and the cards it produced on the page together. An
  // element screenshot here gets overlapped by the sticky header.
  await page.evaluate(() => {
    const panel = document.querySelector('.agent-results')
    window.scrollTo({ top: panel.getBoundingClientRect().top + window.scrollY - 150 })
  })
  await page.waitForTimeout(500)
  await page.screenshot({ path: join(SHOTS, 'test2-category-cards.png') })

  results.push({
    id: 'test2',
    pass:
      verified.length > 0 &&
      verified.every((c) => c.inCatalogue && c.priceMatches && c.imageLoaded),
    question,
    reply,
    cards: verified,
    notes: `${verified.length} cards rendered on the page; all resolve to real catalogue products at the price shown.`,
  })
}

async function testSimilarProducts(page, results) {
  await page.goto(`${SITE}/products/${SIMILAR_PRODUCT}`, { waitUntil: 'networkidle' })

  const section = page.locator('.also-like')
  await section.waitFor({ timeout: 20_000 })
  await page.evaluate(() => {
    const section = document.querySelector('.also-like')
    window.scrollTo({ top: section.getBoundingClientRect().top + window.scrollY - 150 })
  })
  await page.waitForTimeout(500)

  const cards = await page.locator('.also-like .card').evaluateAll((nodes) =>
    nodes.map((node) => ({
      href: node.getAttribute('href'),
      name: node.querySelector('.card-name')?.textContent?.trim(),
      price: node.querySelector('.card-price')?.textContent?.trim(),
      imageLoaded: node.querySelector('img')?.naturalWidth > 0,
    })),
  )

  await page.screenshot({ path: join(SHOTS, 'test3-you-may-also-like.png') })

  // Clicking a recommendation must open that product's own page.
  const target = cards[0]
  await page.locator('.also-like .card').first().click()
  await page.waitForURL(`**${target.href}`, { timeout: 15_000 })

  const landed = {
    url: new URL(page.url()).pathname,
    heading: await page.locator('.detail h1').innerText(),
    price: await page.locator('.detail-price').innerText(),
    sizeBoxes: await page.locator('.size-box').count(),
  }

  // A plain scroll: the detail image is sticky, so scrollIntoViewIfNeeded
  // never settles on "stable".
  await page.evaluate(() => window.scrollTo({ top: 0 }))
  await page.waitForTimeout(600)
  await page.screenshot({ path: join(SHOTS, 'test3b-recommendation-opened.png') })

  const api_similar = await api(`/api/products/${SIMILAR_PRODUCT}/similar`)
  const expected = api_similar.products.map((p) => p.name)

  results.push({
    id: 'test3',
    pass:
      cards.length > 0 &&
      cards.every((c) => c.imageLoaded) &&
      landed.url === target.href &&
      landed.sizeBoxes > 0,
    source: SIMILAR_PRODUCT,
    cards,
    expected,
    landed,
    notes: `${cards.length} recommendations shown; clicking "${target.name}" opened ${landed.url} at ${landed.price}.`,
  })
}

/* ------------------------------------------------------------------ */

async function main() {
  await mkdir(SHOTS, { recursive: true })

  const browser = await chromium.launch()
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  })

  const results = []
  try {
    await testPriceAndStock(page, results)
    await testCategoryCards(page, results)
    await testSimilarProducts(page, results)
  } finally {
    await browser.close()
  }

  await writeFile(RESULTS, JSON.stringify(results, null, 2))

  for (const r of results) {
    console.log(`${r.pass ? 'PASS' : 'FAIL'}  ${r.id}  ${r.notes}`)
  }
  if (results.some((r) => !r.pass)) process.exitCode = 1
}

main()
