import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="container state">
      <h2>That page is not on the shelf</h2>
      <p>The link may be old, or the style may have been retired.</p>
      <p style={{ marginTop: 20 }}>
        <Link to="/products" className="btn">
          Browse the catalogue
        </Link>
      </p>
    </div>
  )
}
