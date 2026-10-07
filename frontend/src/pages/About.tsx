import { Link } from 'react-router-dom'

const TIMELINE = [
  {
    year: '1975',
    title: 'A single storefront on Broadway',
    body: 'A father opens a small shop selling Yale memorabilia directly across from the campus. The idea is modest: sell the things students actually want to take home.',
  },
  {
    year: 'The 1980s',
    title: 'More doors on the same street',
    body: 'The shop grows into a small family of storefronts along Broadway, each one stocked for a different corner of New Haven life.',
  },
  {
    year: 'The 1990s',
    title: 'Ink comes in-house',
    body: 'Rather than ordering finished shirts from somewhere else, the family buys its own presses. Screen printing moves into the back of the store, where it still lives.',
  },
  {
    year: 'Today',
    title: 'The oldest licensed shop in town',
    body: 'Two generations in, Campus Customs is the longest-running officially licensed Yale retailer in New Haven — and still prints, embroiders, and packs orders on site.',
  },
]

const VALUES = [
  {
    num: 'No. 01',
    title: 'Make it here',
    body: 'If we can press it, stitch it, or pack it ourselves, we do. It keeps the quality honest and the turnaround short.',
  },
  {
    num: 'No. 02',
    title: 'Earn the crest',
    body: 'Licensed means reviewed. Artwork gets approved before it gets printed, every time, with no shortcuts around the university.',
  },
  {
    num: 'No. 03',
    title: 'Dress the whole family',
    body: 'A campus is more than its students. Parents, grandparents, siblings, and the dog all have a shelf in this store.',
  },
]

export default function About() {
  return (
    <>
      <section className="about-hero">
        <div className="container">
          <p className="eyebrow">About us</p>
          <h1>We have been on this block longer than most of the buildings around us.</h1>
          <p className="lede">
            Campus Customs is a family shop at 57 Broadway. We have been printing Yale apparel
            across the street from the campus since 1975 — long enough that we have outfitted
            people as first-years and then again as parents.
          </p>
        </div>
      </section>

      <section className="section">
        <div className="container prose">
          <h2>The short version</h2>
          <p>
            It started the way a lot of New Haven businesses start: one person, one lease, and a
            hunch that students would rather buy a sweatshirt from a neighbor than from a
            catalogue. That hunch held. The shop expanded down Broadway, picked up its own
            printing equipment, and eventually passed from one generation of the family to the
            next without ever leaving the street it started on.
          </p>
          <p>
            What makes the place work is not nostalgia. It is that the production floor is about
            twenty feet from the register. When a design is wrong, we see it immediately. When a
            size runs out, somebody notices on the way to lunch. That loop is short enough that we
            can keep standards high without a corporate process telling us to.
          </p>

          <h2>What officially licensed actually means</h2>
          <p>
            Anyone can print a shirt. Printing one with the university&rsquo;s marks on it requires
            approval, and we have been getting that approval since the late seventies. It shapes
            what we carry: the crest has to be right, the wordmark has to be right, and the
            garment underneath has to be good enough to put a crest on. Plenty of designs never
            make it past that gate, and that is the point.
          </p>

          <h2>How the shop is organized</h2>
          <p>
            Walk in and the room sorts itself the way campus does. There is a wall for the
            residential colleges, a wall for varsity and club teams, a section for the graduate
            and professional schools, and a rack near the front for families — the mom, dad,
            grandma, grandpa, aunt, uncle, brother, and cousin shirts that move fastest during
            move-in and reunions. This website is laid out the same way.
          </p>

          <h2>Fifty years, in four lines</h2>
          <div className="timeline">
            {TIMELINE.map((entry) => (
              <div key={entry.year} className="timeline-row">
                <div className="timeline-year">{entry.year}</div>
                <div>
                  <h3>{entry.title}</h3>
                  <p>{entry.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container">
          <div className="section-head">
            <div>
              <p className="eyebrow">How we work</p>
              <h2>Three rules we actually keep</h2>
            </div>
          </div>
          <div className="values">
            {VALUES.map((value) => (
              <article key={value.num} className="pillar">
                <div className="pillar-num">{value.num}</div>
                <h3>{value.title}</h3>
                <p>{value.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container quote">
          <p>Come by the store, or start with the shelf online.</p>
          <div className="hero-actions" style={{ justifyContent: 'center', marginTop: 20 }}>
            <Link to="/products" className="btn">
              Browse the catalogue
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
