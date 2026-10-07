import { useChatResults } from '../ChatResultsContext'
import ProductCard from './ProductCard'

/**
 * Renders the agent's product matches on the page as real product cards.
 *
 * It reuses the same ProductCard component as the catalogue grid, so a card
 * generated from a chat search looks and behaves identically to one on the
 * Products page — including opening the single-item page when clicked.
 */
export default function AgentResults({ className = '' }: { className?: string }) {
  const { products, query, clear } = useChatResults()

  if (products.length === 0) return null

  return (
    <section className={`agent-results ${className}`.trim()} aria-label="Products from your chat">
      <div className="section-head">
        <div>
          <p className="eyebrow">From your chat with Bulldog</p>
          <h2>
            {query ? `“${query}”` : 'Your search'}
          </h2>
          <p className="agent-results-count">
            {products.length} {products.length === 1 ? 'match' : 'matches'} from the catalogue
          </p>
        </div>
        <button type="button" className="btn btn-ghost agent-results-clear" onClick={clear}>
          Clear
        </button>
      </div>

      <div className="grid agent-results-grid">
        {products.map((product) => (
          <ProductCard key={product.product_id} product={product} />
        ))}
      </div>
    </section>
  )
}
