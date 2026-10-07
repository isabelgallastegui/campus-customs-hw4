import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import { swatchFor } from '../colors'
import type { ProductCardData } from '../types'

/** Trims the catalogue description to a single short line. */
function blurb(description: string): string {
  const firstSentence = description.split(/(?<=\.)\s/)[0] ?? description
  return firstSentence.length > 72 ? `${firstSentence.slice(0, 69).trimEnd()}…` : firstSentence
}

export default function ProductCard({ product }: { product: ProductCardData }) {
  const soldOut = product.total_stock === 0
  const colors = (product.colors ?? []).slice(0, 4)

  return (
    <Link to={`/products/${product.product_id}`} className="card">
      <div className="card-media">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="card-badge">Sold out</span>}
      </div>

      <div className="card-body">
        <span className="card-type">{product.garment_type}</span>
        <h3 className="card-name">{product.name}</h3>
        <span className="card-price">{formatPrice(product.price)}</span>
        <p className="card-blurb">{blurb(product.description)}</p>

        <div className="card-foot">
          {colors.length > 0 && (
            <span className="card-swatches" aria-label={`Colours: ${colors.join(', ')}`}>
              {colors.map((color) => (
                <span
                  key={color}
                  className="swatch"
                  style={{ background: swatchFor(color) }}
                  title={color}
                />
              ))}
            </span>
          )}
          <span className="card-stock">
            {soldOut ? 'Out of stock' : `${product.total_stock} in stock`}
          </span>
        </div>
      </div>
    </Link>
  )
}
