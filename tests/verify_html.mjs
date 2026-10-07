/** Opens output/app_check.html straight from disk and checks it renders. */
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { chromium } from 'playwright'

const HERE = dirname(fileURLToPath(import.meta.url))
const FILE = resolve(HERE, '..', 'output', 'app_check.html')

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1100, height: 1400 } })

const failures = []
page.on('requestfailed', (r) => failures.push(r.url()))

await page.goto(pathToFileURL(FILE).href, { waitUntil: 'networkidle' })

const images = await page.locator('img').evaluateAll((nodes) =>
  nodes.map((n) => ({ src: n.getAttribute('src'), loaded: n.naturalWidth > 0 })),
)
const badges = await page.locator('.badge').allInnerTexts()

await page.screenshot({ path: join(HERE, 'app_check_preview.png'), fullPage: true })
await browser.close()

console.log('file:', FILE)
console.log('images:')
for (const i of images) console.log(`  ${i.loaded ? 'OK  ' : 'FAIL'} ${i.src}`)
console.log('badges:', badges.join(' '))
console.log('failed requests:', failures.length ? failures : 'none')

if (images.some((i) => !i.loaded) || failures.length) process.exitCode = 1
