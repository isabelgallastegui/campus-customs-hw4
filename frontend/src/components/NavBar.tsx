import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import Logo from './Logo'

const PAGES = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Shop', end: false },
  { to: '/about', label: 'About', end: false },
]

/**
 * The navy strip of departments. Each one is a real catalogue query, so the
 * links filter the live database rather than pointing at invented categories.
 */
const DEPARTMENTS = [
  { label: 'All', to: '/products' },
  { label: 'Hoodies', to: '/products?type=hood' },
  { label: 'Crewnecks', to: '/products?type=crewneck' },
  { label: 'T-Shirts', to: '/products?type=t-shirt' },
  { label: 'Quarter-Zips', to: '/products?type=zip' },
  { label: 'Jackets', to: '/products?type=jacket' },
  { label: 'Colleges', to: '/products?q=college' },
  { label: 'Teams', to: '/products?q=left chest' },
]

export default function NavBar() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  function handleSignOut() {
    signOut()
    navigate('/')
  }

  return (
    <>
      <div className="announce">
        Printed and stitched on Broadway &middot; Officially licensed Yale apparel since 1975
      </div>

      <header className="nav">
        <div className="container nav-inner">
          <nav className="nav-links" aria-label="Main">
            {PAGES.map((page) => (
              <NavLink
                key={page.to}
                to={page.to}
                end={page.end}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              >
                {page.label}
              </NavLink>
            ))}
          </nav>

          <Link to="/" className="brand" aria-label="Campus Customs home">
            <span className="brand-mark">
              <Logo size={34} />
            </span>
            <span className="brand-text">
              <span className="brand-name">Campus Customs</span>
              <span className="brand-sub">New Haven, CT</span>
            </span>
          </Link>

          <div className="nav-actions">
            {user ? (
              <>
                <span className="nav-user">{user.first_name ?? user.name.split(' ')[0]}</span>
                <button type="button" className="nav-login" onClick={handleSignOut}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-login">
                  Log in
                </Link>
                <Link to="/create-account" className="nav-cta">
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <nav className="deptbar" aria-label="Departments">
        <div className="container deptbar-inner">
          {DEPARTMENTS.map((dept) => (
            <Link key={dept.label} to={dept.to} className="dept-link">
              {dept.label}
            </Link>
          ))}
        </div>
      </nav>
    </>
  )
}
