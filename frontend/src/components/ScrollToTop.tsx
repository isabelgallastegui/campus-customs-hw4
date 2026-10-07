import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/** Keeps navigation feeling like page loads rather than scroll jumps. */
export default function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
