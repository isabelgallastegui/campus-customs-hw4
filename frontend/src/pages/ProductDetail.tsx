import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, fetchSimilarProducts, formatPrice } from '../api'
import ProductCard from '../components/ProductCard'
import type { Product, ProductDetail as ProductDetailType } from '../types'

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>()
  const [product, setProduct] = useState<ProductDetailType | null>(null)
  const [similar, setSimilar] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setLoading(true)
    setError(null)
    setSimilar([])

    fetchProduct(productId)
      .then(setProduct)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false))

    // Recommendations load separately so a slow lookup never blocks the page.
    fetchSimilarProducts(productId)
      .then(setSimilar)
      .catch(() => setSimilar([]))
  }, [productId])

  if (loading) {
    return (
      <div className="container state">
        <p>Pulling this one off the rack…</p>
      </div>
    )
  }

  if (error || !product) {
    return (
      <div className="container state">
        <h2>We could not find that style</h2>
        <p>It may have been renamed or retired.</p>
        <p style={{ marginTop: 20 }}>
          <Link to="/products" className="btn btn-ghost">
            Back to the catalogue
          </Link>
        </p>
      </div>
    )
  }

  const inStockSizes = product.inventory.filter((row) => row.quantity > 0)
  const soldOut = product.total_stock === 0

  return (
    <div className="container">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link> &nbsp;/&nbsp; <Link to="/products">Products</Link> &nbsp;/&nbsp;{' '}
        {product.name}
      </nav>

      <div className="detail">
        <div className="detail-media">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div>
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <div className="detail-price">{formatPrice(product.price)}</div>
          <p className="detail-desc">{product.description}</p>

          <section className="spec-block">
            <h2 className="spec-title">
              Sizes &amp; stock {soldOut ? '— currently sold out' : ''}
            </h2>
            {product.inventory.length > 0 ? (
              <div className="sizes">
                {product.inventory.map((row) => {
                  const out = row.quantity === 0
                  const low = !out && row.quantity <= 5
                  return (
                    <div
                      key={row.size}
                      className={`size-box${out ? ' sold-out' : ''}${low ? ' low' : ''}`}
                    >
                      <div className="size-label">{row.size}</div>
                      <div className="size-qty">
                        {out ? 'Sold out' : low ? `Only ${row.quantity} left` : `${row.quantity} left`}
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="card-blurb">No size information is recorded for this style.</p>
            )}
          </section>

          {product.colors.length > 0 && (
            <section className="spec-block">
              <h2 className="spec-title">Colors</h2>
              <div className="chips">
                {product.colors.map((color) => (
                  <span key={color} className="chip">
                    {color}
                  </span>
                ))}
              </div>
            </section>
          )}

          <section className="spec-block">
            <h2 className="spec-title">Details</h2>
            <table className="spec-table">
              <tbody>
                <tr>
                  <th scope="row">Style code</th>
                  <td>{product.product_id}</td>
                </tr>
                <tr>
                  <th scope="row">Garment</th>
                  <td>{product.garment_type}</td>
                </tr>
                <tr>
                  <th scope="row">Price</th>
                  <td>{formatPrice(product.price)}</td>
                </tr>
                <tr>
                  <th scope="row">Total units on hand</th>
                  <td>{product.total_stock}</td>
                </tr>
                <tr>
                  <th scope="row">Sizes available now</th>
                  <td>
                    {inStockSizes.length > 0
                      ? inStockSizes.map((row) => row.size).join(', ')
                      : 'None'}
                  </td>
                </tr>
              </tbody>
            </table>
          </section>

          {product.search_tags.length > 0 && (
            <section className="spec-block">
              <h2 className="spec-title">Also filed under</h2>
              <div className="chips">
                {product.search_tags.map((tag) => (
                  <span key={tag} className="chip">
                    {tag}
                  </span>
                ))}
              </div>
            </section>
          )}

          <p className="detail-note">
            Every figure on this page is read straight from the shop&rsquo;s inventory database.
            Need a size that is out? Ask Bulldog in the corner — the shop reprints regularly.
          </p>
        </div>
      </div>

      {similar.length > 0 && (
        <section className="also-like" aria-label="You may also like">
          <div className="section-head">
            <div>
              <p className="eyebrow">More from the same shelf</p>
              <h2>You May Also Like</h2>
            </div>
            <Link to="/products" className="section-link">
              Browse everything &rarr;
            </Link>
          </div>

          <div className="grid also-like-grid">
            {similar.map((item) => (
              <ProductCard key={item.product_id} product={item} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
