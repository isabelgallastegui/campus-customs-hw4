import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, formatPrice } from '../api'
import ProductCard from '../components/ProductCard'
import AgentResults from '../components/AgentResults'
import { useChatResults } from '../ChatResultsContext'
import type { Product } from '../types'

/** Picks a spread of real catalogue items rather than hard-coding any. */
function pickFeatured(products: Product[], count: number): Product[] {
  const seen = new Set<string>()
  const featured: Product[] = []

  for (const product of products) {
    if (product.total_stock === 0) continue
    if (seen.has(product.garment_type)) continue
    seen.add(product.garment_type)
    featured.push(product)
    if (featured.length === count) return featured
  }

  // Fall back to filling out the row if the catalogue has few distinct types.
  for (const product of products) {
    if (featured.length === count) break
    if (!featured.includes(product)) featured.push(product)
  }
  return featured
}

/** The style shown in the hero. */
const HERO_PRODUCT_ID = 'benjamin-franklin-1-4-zip'

const TICKER = [
  'Screen printed on site',
  'Officially licensed',
  'All 14 residential colleges',
  'Varsity & club teams',
  'Graduate schools',
  'Family collections',
  'XS through XXL',
]

const PILLARS = [
  {
    num: 'No. 01',
    title: 'Pressed in the back room',
    body: 'Screens, thread, and heat press all live under one roof on Broadway. Nothing gets drop-shipped from a warehouse that has never seen New Haven.',
  },
  {
    num: 'No. 02',
    title: 'Licensed, not borrowed',
    body: 'Every crest, wordmark, and bulldog on this site is approved for the real thing. We have been clearing artwork with the university for five decades.',
  },
  {
    num: 'No. 03',
    title: 'Built for a cold walk',
    body: 'Heavyweight fleece, reverse weave, and quarter-zips chosen for February on Elm Street — not for a photo shoot in a studio.',
  },
]

const SHELVES = [
  {
    icon: 'RC',
    title: 'Residential colleges',
    body: 'Branford to Timothy Dwight, on crewnecks and quarter-zips.',
    to: '/products?q=college',
  },
  {
    icon: 'VS',
    title: 'Varsity & club',
    body: 'Left-chest marks for sailing, fencing, hockey, and the rest.',
    to: '/products?q=left chest',
  },
  {
    icon: 'GS',
    title: 'Graduate schools',
    body: 'Law, Medicine, Management, Nursing, Art, Architecture, Music.',
    to: '/products?q=school of',
  },
  {
    icon: 'FM',
    title: 'The whole family',
    body: 'Mom, Dad, Grandma, Grandpa, Aunt, Uncle, Brother, Cousin.',
    to: '/products?q=yale mom',
  },
]

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])
  const { products: chatMatches } = useChatResults()

  useEffect(() => {
    fetchProducts()
      .then((data) => setProducts(data.products))
      .catch(() => setProducts([]))
  }, [])

  const featured = pickFeatured(products, 8)
  // One garment carries the hero. Falls back to the first featured product if
  // this style is ever removed from the catalogue.
  const heroProduct =
    products.find((item) => item.product_id === HERO_PRODUCT_ID) ?? featured[0] ?? null
  const priced = products.map((product) => product.price)
  const lowestPrice = priced.length ? Math.min(...priced) : null

  return (
    <>
      <section className="hero">
        <div className="container hero-grid">
          <div>
            <p className="eyebrow">New Haven &middot; Since 1975</p>
            <h1>Yale apparel, printed on Broadway.</h1>
            <p className="lede">
              Fifty years of officially licensed sweatshirts, tees and quarter-zips — pressed and
              stitched in the back of the shop, not shipped in from a warehouse.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn">
                Shop now
              </Link>
            </div>

            <div className="hero-stats">
              <div>
                <div className="hero-stat-value">{products.length || '—'}</div>
                <div className="hero-stat-label">Styles in stock</div>
              </div>
              <div>
                <div className="hero-stat-value">XS&ndash;XXL</div>
                <div className="hero-stat-label">Every size</div>
              </div>
              <div>
                <div className="hero-stat-value">
                  {lowestPrice === null ? '—' : `$${lowestPrice.toFixed(0)}+`}
                </div>
                <div className="hero-stat-label">Tees from</div>
              </div>
            </div>
          </div>

          {heroProduct && (
            <Link
              to={`/products/${heroProduct.product_id}`}
              className="hero-tile"
              aria-label={`Shop the ${heroProduct.name}`}
            >
              {/* Background-free cut-out, so the garment sits on the navy
                  instead of inside a white box. Falls back to the catalogue
                  photo if no cut-out exists for this product. */}
              <img
                src={`/media/products_hero/${heroProduct.product_id}.png`}
                alt={heroProduct.name}
                onError={(event) => {
                  event.currentTarget.src = heroProduct.image_url
                }}
              />
              <span className="hero-tile-label">
                <span className="hero-tile-name">{heroProduct.name}</span>
                <span className="hero-tile-price">{formatPrice(heroProduct.price)}</span>
              </span>
            </Link>
          )}
        </div>
      </section>

      <div className="ticker" aria-hidden="true">
        <div className="ticker-track">
          {Array.from({ length: 2 }).map((_, pass) => (
            <span key={pass} className="ticker-run">
              {TICKER.map((item) => (
                <span key={`${pass}-${item}`} className="ticker-item">
                  {item}
                </span>
              ))}
            </span>
          ))}
        </div>
      </div>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <div>
              <h2>Why shop with us</h2>
            </div>
          </div>
          <div className="pillars">
            {PILLARS.map((pillar) => (
              <article key={pillar.num} className="pillar">
                <div className="pillar-num">{pillar.num}</div>
                <h3>{pillar.title}</h3>
                <p>{pillar.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          {/* A chat search takes over this slot, so asking Bulldog visibly
              changes the page rather than only the conversation. */}
          {chatMatches.length > 0 && <AgentResults />}

          <div className="section-head">
            <div>
              <h2>Featured products</h2>
            </div>
            <Link to="/products" className="section-link">
              View all {products.length || ''} &rarr;
            </Link>
          </div>

          {featured.length > 0 ? (
            <div className="grid" style={{ padding: 0 }}>
              {featured.map((product) => (
                <ProductCard key={product.product_id} product={product} />
              ))}
            </div>
          ) : (
            <p className="lede">Loading the shelf…</p>
          )}
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="section-head">
            <div>
              <h2>Shop by department</h2>
            </div>
          </div>
          <div className="shelf">
            {SHELVES.map((shelf) => (
              <Link key={shelf.title} to={shelf.to} className="shelf-card">
                <span className="shelf-icon" aria-hidden="true">
                  {shelf.icon}
                </span>
                <div>
                  <h3>{shelf.title}</h3>
                  <p>{shelf.body}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container quote">
          <p>
            &ldquo;Buy the heavier one. You will still be wearing it at your twenty-fifth
            reunion.&rdquo;
          </p>
          <span>What we tell every first-year in October</span>
        </div>
      </section>

      <section className="closer">
        <div className="container closer-inner">
          <div>
            <p className="eyebrow">Ready when you are</p>
            <h2>
              {products.length || 'A hundred'} styles, one counter,
              <br />
              fifty years of practice.
            </h2>
          </div>
          <div className="hero-actions">
            <Link to="/products" className="btn">
              Shop the collection
            </Link>
            <Link to="/create-account" className="btn btn-ghost">
              Create an account
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
