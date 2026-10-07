import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts } from '../api'
import ProductCard from '../components/ProductCard'
import AgentResults from '../components/AgentResults'
import type { Product } from '../types'

type SortKey = 'name' | 'price-asc' | 'price-desc'

/** Friendlier names for the loose garment families used as filters. */
const TAB_LABELS: Record<string, string> = {
  hood: 'Hoodies',
  crewneck: 'Crewnecks',
  't-shirt': 'T-Shirts',
  zip: 'Quarter-Zips',
  jacket: 'Jackets',
  fleece: 'Fleece',
  'long-sleeve': 'Long Sleeve',
}

export default function Products() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<SortKey>('name')

  const query = searchParams.get('q') ?? ''
  const typeFilter = searchParams.get('type') ?? ''

  useEffect(() => {
    fetchProducts()
      .then((data) => setProducts(data.products))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  /** Garment types are not standardized in the database, so the filter groups
   *  them loosely by substring instead of matching exact values. */
  const typeGroups = useMemo(() => {
    const groups = ['hood', 'crewneck', 't-shirt', 'zip', 'jacket', 'fleece', 'long-sleeve']
    return groups.filter((group) =>
      products.some((product) => product.garment_type.toLowerCase().includes(group)),
    )
  }, [products])

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()

    const filtered = products.filter((product) => {
      if (typeFilter && !product.garment_type.toLowerCase().includes(typeFilter.toLowerCase())) {
        return false
      }
      if (!needle) return true

      const haystack = [
        product.name,
        product.garment_type,
        product.description,
        ...product.colors,
        ...product.search_tags,
      ]
        .join(' ')
        .toLowerCase()

      return haystack.includes(needle)
    })

    const sorted = [...filtered]
    if (sort === 'price-asc') sorted.sort((a, b) => a.price - b.price)
    if (sort === 'price-desc') sorted.sort((a, b) => b.price - a.price)
    if (sort === 'name') sorted.sort((a, b) => a.name.localeCompare(b.name))
    return sorted
  }, [products, query, typeFilter, sort])

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="container">
      <header className="catalogue-head">
        <h1>Shop all</h1>
        <p className="lede">
          Pulled live from the shop&rsquo;s inventory — the price and size run you see here are the
          ones at the counter.
        </p>
      </header>

      <AgentResults className="agent-results-inline" />

      <div className="filters">
        {/* Tabs mirror the department bar: one click, no dropdown. */}
        <div className="tabs" role="tablist" aria-label="Garment type">
          <button
            type="button"
            role="tab"
            aria-selected={typeFilter === ''}
            className={typeFilter === '' ? 'tab active' : 'tab'}
            onClick={() => updateParam('type', '')}
          >
            All products
          </button>
          {typeGroups.map((group) => (
            <button
              key={group}
              type="button"
              role="tab"
              aria-selected={typeFilter === group}
              className={typeFilter === group ? 'tab active' : 'tab'}
              onClick={() => updateParam('type', typeFilter === group ? '' : group)}
            >
              {TAB_LABELS[group] ?? group}
            </button>
          ))}
        </div>

        <div className="filter-tools">
          <input
            className="search-field"
            type="search"
            value={query}
            onChange={(event) => updateParam('q', event.target.value)}
            placeholder="Search"
            aria-label="Search products"
          />

          <select
            className="select-field"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortKey)}
            aria-label="Sort products"
          >
            <option value="name">Sort by: A–Z</option>
            <option value="price-asc">Sort by: price low to high</option>
            <option value="price-desc">Sort by: price high to low</option>
          </select>

          {(query || typeFilter) && (
            <button
              type="button"
              className="pill-clear"
              onClick={() => setSearchParams(new URLSearchParams(), { replace: true })}
            >
              Clear filters
            </button>
          )}
        </div>

        <span className="result-count">
          {loading ? 'Loading…' : `${visible.length} of ${products.length}`}
        </span>
      </div>

      {loading && (
        <div className="skeleton-grid">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="skeleton" />
          ))}
        </div>
      )}

      {error && (
        <div className="state">
          <h2>The catalogue is not answering</h2>
          <p>
            Start the backend with <code>uvicorn backend.main:app --reload</code>, then refresh.
          </p>
        </div>
      )}

      {!loading && !error && visible.length === 0 && (
        <div className="state">
          <h2>Nothing matches that</h2>
          <p>Try a broader search — a color, a college, or a sport.</p>
        </div>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className="grid">
          {visible.map((product) => (
            <ProductCard key={product.product_id} product={product} />
          ))}
        </div>
      )}
    </div>
  )
}
