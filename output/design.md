# Campus Customs — Design

How the storefront is styled, and why each decision should keep a shopper on the
site and moving toward a purchase.

> **Note on revisions.** My first pass was too decorative — heavy shadows, large
> serif product names, gold hairlines, a "View product" overlay on every card.
> It looked designed rather than shoppable. After reviewing two reference
> storefronts (a university merch shop and a minimal fashion retailer) the design
> was rebuilt flatter and denser. What follows describes the current design, with
> the original choices noted where they were reversed.

---

## The direction

Two references set the target: a **university merchandise storefront** — centred
logo, navy department bar, product-led hero with a single amber CTA — and a
**minimal fashion retailer** — flat product grid with no card chrome, metadata
sitting quietly beneath each photo, filters as tabs and pills.

Three rules follow from that:

1. **The photograph is the product card.** No borders, no shadows, no overlays.
   Anything drawn around a garment competes with it.
2. **Navy is structure, amber is action, white is product.** Navy carries the
   header and department bar; a single amber button is the only saturated colour
   on the page, so the eye always finds the way to shop.
3. **Text supports, never performs.** Product names, prices, and stock sit in
   plain sans at modest sizes. The serif is reserved for page headings.

---

## Navigation — two bars

- **White bar** with site links on the left, the **shield wordmark centred**, and
  account actions on the right. A centred mark reads as a store rather than an
  app.
- **Navy department bar** beneath it: ALL, HOODIES, CREWNECKS, T-SHIRTS,
  QUARTER-ZIPS, JACKETS, COLLEGES, TEAMS. Each one is a **real query against the
  catalogue**, not an invented category, and an amber underline wipes in on
  hover.

Both bars are sticky, so a shopper can jump department at any scroll depth.

**Why it helps:** the department strip puts the whole catalogue one click away
from every page. Most visitors do not use search — they browse — and this makes
browsing the default path.

---

## Home

A navy hero holds a plain, direct headline — **"Yale apparel, printed on
Broadway."** — two lines of copy, and one **amber "Shop now" button**. The
original version had a two-colour italic display headline and two competing
CTAs; one button converts better than two.

Beside it, four real products sit on flat white tiles. Beneath, three live proof
points — **102 styles · XS–XXL · $32+** — pulled from the database. Real numbers
beat adjectives, and the entry price answers the first silent objection.

The page then runs a quiet ticker of what the shop covers, **Featured products**
in a four-up grid, department shortcuts, a pull quote, and a navy closing band
that repeats the shop CTA.

**Why it helps:** a visitor sees merchandise, price range, and a single obvious
action above the fold. Most bounces happen before the first scroll.

---

## Catalogue

- **Garment tabs on the left**, search and sort as **pills on the right**, with a
  Clear control that appears only when a filter is active. Dropdowns hide their
  options; tabs show them.
- The filter row is **sticky**, so a shopper filtering 102 products never scrolls
  back up — the most common reason people abandon a long grid.
- A live `102 of 102` count gives immediate feedback.

### The product card

```
┌─────────────┐
│             │   ← white tile, photo fills the frame
│   garment   │
│             │
└─────────────┘
SHORT-SLEEVE T-SHIRT     ← type, uppercase, small
2025 Yale Vs Harvard     ← name
$32.00                   ← price
Heather gray short-s…    ← one line of description
● ○ ● ●        112 in stock
```

Flat, borderless, and sitting directly on the page. The tile is **white because
the normalized photos are white** (Problem 9) — a grey tile would frame each
photo in a visible square. On hover the photo scales ~4% and a hairline draws
itself under the image. That is the entire interaction vocabulary.

The **colour dots are real data**, read from `catalogue.colors` and mapped to
swatch values. Reference stores show star ratings there; we have no ratings in
the database and did not invent any, so the slot shows something true instead.

**Why it helps:** a grid is a comparison tool. Identical white stages mean
shoppers compare garments, not backgrounds, and colour dots answer "does it come
in navy?" without a click.

---

## Single product

Large photo on a white field, sticky while the specs scroll. Type, name, price,
description, then **sizes as a tactile grid** where in-stock boxes respond to
hover and sold-out boxes go dashed and muted. Colours, a spec table, and tags
follow as quiet sections separated by hairlines.

**"You May Also Like"** from Problem 9 uses the same flat card, so
recommendations read as part of the catalogue rather than an ad unit.

**Why it helps:** the product page is where the decision happens. Price and size
availability are the two things a shopper checks, so they are the two most
scannable elements — and recommendations turn "not quite right" into another look
instead of a back button.

---

## Chat

Navy header, Bulldog monogram, a status line naming who is signed in, and a
launcher with a pulsing availability dot. Replies are white cards; the shopper's
own messages are navy. Suggested products are miniature versions of the real
product card.

**Why it helps:** a chatbot that looks bolted on gets ignored. One that looks
like the store invites use — and the assistant is the fastest route to a product.

---

## Footer

A navy band with the light shield, the shop's story in two lines, three link
columns, and the address. Links underline from left to right on hover.

**Why it helps:** a thin footer makes a site feel unfinished. A substantial one
signals a real business and catches shoppers hunting for the store address.

---

## Details

- **One easing curve** for every transition on the site, so hovers, underlines,
  and panels all accelerate alike — the site feels like one object.
- **Entrance animations** stagger the first eight cards, then stop.
- **Focus rings** are visible and on-brand for keyboard users.
- **`prefers-reduced-motion`** disables all animation.
- Responsive from four columns down to one; the department bar scrolls
  horizontally and the sticky offsets release on small screens.

---

## Nothing was broken

Every class the components depend on was preserved, and the stack was re-tested
after the restyle:

| Check | Result |
| --- | --- |
| Catalogue | ✅ 102 products, colours present on cards |
| Product detail + inventory | ✅ Yale Mom Hoodie, $68.00, 6 sizes |
| Normalized images | ✅ `200` |
| Similar products | ✅ Yale Dad / Grandma / Grandpa / Ice Hockey Hoodie |
| Login / bad login / duplicate signup | ✅ `200` / `401` / `409` |
| Chat history | ✅ `200` |
| Chat search | ✅ 6 cards returned, colours included |
| Department links filter the catalogue | ✅ real `?type=` / `?q=` queries |
| TypeScript build | ✅ passes |
| Browser console | ✅ no errors |
