import { Link } from 'react-router-dom'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <div className="brand">
              <span className="brand-mark brand-mark-plain">
                <Logo size={42} tone="light" />
              </span>
              <span className="brand-text">
                <span className="brand-name">Campus Customs</span>
                <span className="brand-sub">New Haven, CT</span>
              </span>
            </div>
            <p className="footer-blurb">
              A family shop on Broadway, pressing ink and thread into Yale apparel for half a
              century. Every order still passes through the same back room.
            </p>
          </div>

          <div>
            <h4>Shop</h4>
            <ul>
              <li>
                <Link to="/products">The full catalogue</Link>
              </li>
              <li>
                <Link to="/products?type=hoodie">Hoodies</Link>
              </li>
              <li>
                <Link to="/products?type=crewneck">Crewnecks</Link>
              </li>
              <li>
                <Link to="/products?type=t-shirt">Tees</Link>
              </li>
            </ul>
          </div>

          <div>
            <h4>Visit &amp; Account</h4>
            <ul>
              <li>
                <Link to="/about">Our story</Link>
              </li>
              <li>
                <Link to="/login">Log in</Link>
              </li>
              <li>
                <Link to="/create-account">Create account</Link>
              </li>
              <li>57 Broadway, New Haven</li>
            </ul>
          </div>
        </div>

        <div className="footer-base">
          <span>&copy; {new Date().getFullYear()} Campus Customs. A student project build.</span>
          <span>Pressed in New Haven &middot; Boola Boola</span>
        </div>
      </div>
    </footer>
  )
}
