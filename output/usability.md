# Campus Customs — Usability Improvements

Four improvements to the Campus Customs site: two on the frontend, two in the
agent/backend. Each one is described below with what it does, why it matters,
and how it was tested.

---

## 1. Consistent product images

### The problem

I measured the 102 photos in `data/products/` before changing anything, and the
inconsistency was worse than it looked:

- **60 distinct pixel sizes**, from 457×457 up to 900×900.
- **73 of 102 photos had dark backgrounds**; the other 29 were on white.

Two different causes were mixed together. Most dark photos were simply
**letterboxed** — a white-background photo padded with black bars to force a
square. A smaller group was genuinely **shot on a black studio backdrop**. In the
catalogue grid this read as black boxes scattered among white ones, which makes a
real shop look like a broken one.

### What I added

CSS alone could not fix this, because the black was baked into the pixels. So
`backend/normalize_images.py` writes a cleaned display copy of every photo to
`data/products_web/`:

1. Crop away the uniform near-black letterbox padding.
2. Where a true black backdrop remains, flood it with white **from the edges
   inward**, using a cut-off of 14 — just below the darkest navy fabric, which
   measures 19. Because the fill only spreads in from the border, it cannot punch
   a hole in the middle of a garment, and if it would swallow more than 80% of
   the frame the attempt is discarded and the original kept.
3. Trim any remaining blank border so every product is bounded the same way.
4. Centre the result on a 900×900 white canvas with a fixed 6% margin.

**Nothing is distorted.** The aspect ratio is preserved at every step; the
product is scaled to fit and centred, never stretched.

On the frontend, every product image switched from `object-fit: cover` to
`object-fit: contain` on a white stage with consistent padding — so the garment
is always shown whole rather than cropped to fill the box.

The database is untouched: `catalogue.image_file_path` remains the source of
truth, and `display_image_url()` simply prefers the normalized copy when that
exact file exists, falling back to the original otherwise.

### Why it helps

A uniform grid is easier to scan, so a shopper compares garments instead of
backgrounds. For the business, consistent product photography is the cheapest
signal of a legitimate store — mismatched images read as low effort, and that
hesitation costs sales.

### Tested

- All 102 outputs are **900×900** with a **white corner pixel** (was 60 sizes, 73 dark).
- A before/after contact sheet confirmed garments are intact and undistorted.
- `/api/products` reports **102/102** images served from `products_web`.
- `image_file_path` in the API response is unchanged.
- The original `/media/products/...` path still returns `200`, so the fallback works.

---

## 2. A real Campus Customs logo

### What I added

The old mark was a navy rounded square with the letters "CC". It has been
replaced by `frontend/src/components/Logo.tsx`: a collegiate **shield** carrying
a CC monogram above an **open book**, with **1975** — the shop's founding year —
set along the bottom.

It is drawn as inline SVG rather than an image file, which means it stays sharp
at any size, costs no extra network request, and can take its colours from CSS. A
`tone="light"` variant renders a cream shield for the dark footer.

### Why it helps

The shield and book read as collegiate without copying any university mark, and
carrying "1975" in the logo puts the shop's strongest credential — fifty years on
Broadway — in front of the shopper on every single page. A flat two-letter box
said nothing; this says *old, academic, established*.

### Tested

- The brand mark renders as `<svg aria-label="Campus Customs">` in the header, with no "CC" text node.
- Verified visually at 3× zoom in the header and 2.2× in the footer; the light variant reads correctly on the dark background.

---

## 3. "You May Also Like" recommendations

### What I added

A new `similar_products()` function in `backend/tools.py` scores every other
catalogue product against the one being viewed, using only real database fields:

| Signal | Weight |
| --- | --- |
| Same `garment_type` | 6 |
| Same garment *family* (e.g. "hoodie" ≈ "pullover hoodie") | 4 |
| Each shared `search_tag` | 2 |
| Each shared colour | 2 |
| Identical price | 3 |
| Price within $15 | 1 |

Two details make the results better than a naive match. Garment types are not
standardized in this catalogue — `hoodie`, `pullover hoodie`, and `hooded
sweatshirt` all appear — so a **family** match catches relatives an exact match
would miss. And tags that sit on nearly every product (`yale`, `campus customs`)
are **excluded**, because a signal shared by everything distinguishes nothing.

It is exposed two ways: `GET /api/products/{id}/similar` powers the "You May
Also Like" section at the bottom of every product page, and `find_similar_products`
is registered as an agent tool, so the chatbot recommends the same things the
page does.

The section reuses the existing `ProductCard` component, so each recommendation
shows a real image, name, price, short description, and stock, and clicking one
opens that product's page — identical behaviour to the catalogue grid.

### Why it helps

A shopper who lands on one product usually has not decided yet. Showing four
genuine neighbours turns a dead end into a browse. For the business it is the
cheapest lever on basket size and time-on-site, and because recommendations come
from the live catalogue, they are never stale or out of stock without saying so.

### Tested

| Viewing | Recommended | Sensible? |
| --- | --- | --- |
| Yale Mom Hoodie | Yale Dad, Yale Grandma, Yale Grandpa, Ice Hockey Left Chest Hoodie | ✅ the family set |
| Saybrook Logo T Shirt | Pierson, Grace Hopper, Morse Logo Tees, District Vintage Shield | ✅ other residential-college tees |
| Benjamin Franklin Fleece Jacket | School of Music / Divinity / Architecture / Art fleece sweaters | ✅ same garment, same price band |

- Each card carries a real image, name, price, blurb, and stock count.
- Clicking **Yale Dad Hoodie** opened its page at $68.00, and its own recommendations refreshed to Yale Mom / Grandpa / Aunt.
- An unknown product id returns `404`.

---

## 4. Honest answers when there is no exact match

### The problem

A shopper asking for something the shop does not carry is the moment an
assistant is most tempted to bluff — either inventing a product or quietly
presenting a near-match as though it were the thing asked for. Both get found out
at checkout.

### What I added

A new `suggest_alternatives(query)` tool. When an exact search returns nothing,
it retries with progressively fewer words and reports back:

- `exact_match` — always `false`, so the agent cannot mistake this for a hit
- `relaxed_to` — the words that **did** match something real
- `dropped` — the words nothing in the catalogue matched
- `alternatives` — real products, which may legitimately be empty

So "pink sailing beanie" relaxes to `sailing`, dropping `pink` and `beanie`, and
the agent can tell the customer precisely what it had to give up.

`prompts/prompt.md` gained a matching section: never invent a product or stretch
a near-match; say plainly there is no exact match and **name what is missing**;
call `suggest_alternatives` and present the results explicitly as alternatives;
put them in `products` so they appear as clickable cards; and if there are no
alternatives either, say so and ask the customer to describe it differently
rather than padding the answer.

### Why it helps

The shopper gets a straight answer and a usable next step instead of a dead end
or a wrong purchase. For the business, honesty here prevents returns and the
support cost that comes with them — and an accurate "we don't have that, but
here's what we do have" still converts, while a misleading yes destroys trust.

### Tested

| Asked | Answered | Verified against the database |
| --- | --- | --- |
| "I want a pink Yale hoodie" | "I couldn't find an exact match… the pink colour is the part we don't have." Offered 3 real hoodies in navy and gray. | **0** products mention pink ✅ |
| "Do you sell Yale beanies or winter hats?" | "I couldn't find any Yale beanies or winter hats in the catalogue," then offered real apparel. | **0** hats or beanies exist ✅ |
| "Do you have a bright red Yale rugby jersey?" | "I couldn't find a bright red Yale rugby jersey… the closest is a heather gray Game T-shirt — **not a red jersey**." | Correctly refused to call it a match ✅ |

No invented product appeared in any test, and every alternative offered exists in
the catalogue at the stated price.

One fix came out of this testing: the agent initially named an alternative in
prose but left `products` empty, so nothing clickable appeared. The prompt now
requires alternatives to go in `products`, and the retest returned the 2025 Yale
Vs Harvard T Shirt at $32.00 as a card.

---

## Regression

Everything from Problems 3–8 still works after these changes:

- Catalogue returns **102** products; detail pages, images, and garment types all respond.
- Login `200`, duplicate signup `409`, chat history `200`, unknown history `404`.
- Chat still answers, still returns structured matches, and still updates the on-page results panel.
- TypeScript build passes and the browser console is clean.
