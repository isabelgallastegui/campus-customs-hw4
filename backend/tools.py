"""Tools the Campus Customs agent can call.

Four tools, all reading `campus_customs.db` directly:

- `search_products`     find candidates by free text (from Problem 5)
- `get_product_details` the full catalogue record for one product
- `check_stock`         stock across every size
- `check_size_availability` stock for one specific size

They share one product resolver and the row helpers in `database.py`, so a
product name is interpreted the same way no matter which tool is called.
"""

from __future__ import annotations

import re
import sqlite3

from database import display_image_url, fetch_inventory, get_connection, parse_json_list
from models import (
    LookupFailure,
    ProductCard,
    ProductDetails,
    SizeAvailability,
    SizeStock,
    StockReport,
)

# Keeps one tool call from dragging the whole catalogue into the context window.
MAX_RESULTS = 8

# The only sizes the inventory table uses.
STORED_SIZES = ("XS", "S", "M", "L", "XL", "XXL")

# Customers type words, the database stores labels.
SIZE_ALIASES = {
    "extra small": "XS",
    "x small": "XS",
    "xsmall": "XS",
    "small": "S",
    "medium": "M",
    "med": "M",
    "large": "L",
    "extra large": "XL",
    "x large": "XL",
    "xlarge": "XL",
    "extra extra large": "XXL",
    "double extra large": "XXL",
    "2xl": "XXL",
    "2x": "XXL",
    "xxlarge": "XXL",
}


def _row_to_card(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductCard:
    inventory = fetch_inventory(conn, row["product_id"])
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        price=row["price"],
        image_url=display_image_url(row["image_file_path"]),
        description=row["description"],
        colors=parse_json_list(row["colors"]),
        sizes_in_stock=[r["size"] for r in inventory if r["quantity"] > 0],
        total_stock=sum(r["quantity"] for r in inventory),
    )


def search_products(
    query: str,
    limit: int = MAX_RESULTS,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = False,
) -> list[ProductCard]:
    """Search the Campus Customs catalogue.

    Matches the query against product names, garment types, descriptions,
    colors, and search tags, with optional price and stock filters. Returns live
    price and per-size stock for each hit.

    Args:
        query: What the customer is looking for — a garment type ("hoodie"), a
            color ("navy"), a sport ("sailing"), a residential college
            ("Saybrook"), a school ("School of Management"), or a free-text
            phrase. Pass an empty string to browse by price or stock alone.
        limit: Maximum number of products to return.
        max_price: Only products at or below this price. **Use this for any
            budget question** ("under $50", "nothing over $80") — do not put the
            price in `query`, which is a text search and will not filter by it.
        min_price: Only products at or above this price.
        in_stock_only: Drop products with no units left in any size.

    Returns:
        Matching products with their real price, description, image, the sizes
        currently in stock, and total units on hand. An empty list means nothing
        matched — say so rather than inventing a product.

    Note:
        The result is capped at `limit`, so it may not be the complete set. Do
        not claim a count unless you are sure you have seen everything.
    """
    terms = [word for word in query.lower().split() if word]
    limit = max(1, min(limit, MAX_RESULTS))

    def keep(row: sqlite3.Row) -> bool:
        if max_price is not None and row["price"] > max_price:
            return False
        if min_price is not None and row["price"] < min_price:
            return False
        return True

    with get_connection() as conn:
        rows = [
            row
            for row in conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
            if keep(row)
        ]

        if in_stock_only:
            rows = [
                row
                for row in rows
                if any(item["quantity"] > 0 for item in fetch_inventory(conn, row["product_id"]))
            ]

        if not terms:
            # Price- or stock-only browse: cheapest first is the useful order.
            rows.sort(key=lambda row: (row["price"], row["name"]))
            return [_row_to_card(conn, row) for row in rows[:limit]]

        # Simple scoring: a name hit counts for more than a description hit, so
        # "hoodie" ranks actual hoodies above items that merely mention one.
        scored: list[tuple[int, sqlite3.Row]] = []
        for row in rows:
            name = row["name"].lower()
            garment = row["garment_type"].lower()
            description = row["description"].lower()
            tags = " ".join(parse_json_list(row["search_tags"])).lower()
            colors = " ".join(parse_json_list(row["colors"])).lower()

            score = 0
            for term in terms:
                if term in name:
                    score += 5
                if term in garment:
                    score += 4
                if term in tags:
                    score += 3
                if term in colors:
                    score += 2
                if term in description:
                    score += 1

            if score:
                scored.append((score, row))

        scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
        return [_row_to_card(conn, row) for _score, row in scored[:limit]]


# ---------------------------------------------------------------------------
# Shared lookup helpers
# ---------------------------------------------------------------------------


def normalize_size(size: str) -> str | None:
    """Map what a customer typed onto a stored size label, or None."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", size.strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    upper = cleaned.replace(" ", "").upper()
    if upper in STORED_SIZES:
        return upper
    return SIZE_ALIASES.get(cleaned)


def _find_product_row(conn: sqlite3.Connection, product: str) -> sqlite3.Row | None:
    """Resolve a product_id or a product name to one catalogue row.

    Tried in order: exact id, exact name, slugified name, then a unique
    substring match. A substring that matches several products is treated as a
    miss, so the agent is never handed the wrong item silently.
    """
    needle = product.strip()
    if not needle:
        return None

    row = conn.execute(
        "SELECT * FROM catalogue WHERE lower(product_id) = ?", (needle.lower(),)
    ).fetchone()
    if row:
        return row

    row = conn.execute(
        "SELECT * FROM catalogue WHERE lower(name) = ?", (needle.lower(),)
    ).fetchone()
    if row:
        return row

    slug = re.sub(r"[^a-z0-9]+", "-", needle.lower()).strip("-")
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (slug,)).fetchone()
    if row:
        return row

    matches = conn.execute(
        "SELECT * FROM catalogue WHERE lower(name) LIKE ? ORDER BY length(name) LIMIT 2",
        (f"%{needle.lower()}%",),
    ).fetchall()
    return matches[0] if len(matches) == 1 else None


def _suggest(conn: sqlite3.Connection, product: str, limit: int = 5) -> list[str]:
    """Candidate product names for a failed lookup.

    Terms that appear across most of the catalogue ("yale") carry no signal, so
    they are dropped. If nothing distinctive is left, return nothing rather than
    an arbitrary list the agent might present as real alternatives.
    """
    terms = [word for word in re.split(r"\W+", product.lower()) if len(word) > 2]
    if not terms:
        return []

    rows = conn.execute("SELECT name, search_tags FROM catalogue").fetchall()
    haystacks = [
        f"{row['name']} {' '.join(parse_json_list(row['search_tags']))}".lower()
        for row in rows
    ]

    # Keep only terms that narrow the catalogue down.
    common_threshold = max(1, int(len(rows) * 0.4))
    useful = [
        term
        for term in terms
        if 0 < sum(1 for hay in haystacks if term in hay) <= common_threshold
    ]
    if not useful:
        return []

    scored: list[tuple[int, str]] = []
    for row, hay in zip(rows, haystacks):
        score = sum(1 for term in useful if term in hay)
        if score:
            scored.append((score, row["name"]))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [name for _score, name in scored[:limit]]


def _split_sizes(inventory: list[SizeStock]) -> tuple[list[str], list[str]]:
    return (
        [row.size for row in inventory if row.in_stock],
        [row.size for row in inventory if not row.in_stock],
    )


def _size_stock(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    return [
        SizeStock(size=row["size"], quantity=row["quantity"], in_stock=row["quantity"] > 0)
        for row in fetch_inventory(conn, product_id)
    ]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def get_product_details(product: str) -> ProductDetails | LookupFailure:
    """Look up one product's full record: description, price, colors, and stock by size.

    Use this whenever a customer asks what a specific product is like, what it
    costs, or what it is made of. The description and price come straight from
    the catalogue table — never describe or price a product without calling this
    (or `search_products`) first.

    Args:
        product: A product_id such as 'yale-mom-hoodie', or a product name such
            as 'Yale Mom Hoodie'. A distinctive part of the name also works.

    Returns:
        The product's catalogue record plus per-size stock, or a LookupFailure
        with suggested names when nothing matched. Never guess past a failure.
    """
    with get_connection() as conn:
        row = _find_product_row(conn, product)
        if row is None:
            return LookupFailure(
                query=product,
                reason=f"No product in the Campus Customs catalogue matches '{product}'.",
                suggestions=_suggest(conn, product),
            )

        inventory = _size_stock(conn, row["product_id"])
        in_stock, sold_out = _split_sizes(inventory)

        return ProductDetails(
            product_id=row["product_id"],
            name=row["name"],
            garment_type=row["garment_type"],
            description=row["description"],
            colors=parse_json_list(row["colors"]),
            search_tags=parse_json_list(row["search_tags"]),
            price=row["price"],
            image_url=display_image_url(row["image_file_path"]),
            inventory=inventory,
            sizes_in_stock=in_stock,
            sizes_sold_out=sold_out,
            total_stock=sum(item.quantity for item in inventory),
        )


def check_stock(product: str) -> StockReport | LookupFailure:
    """Check how many units of a product are in stock, broken down by size.

    Use this for 'how many are left', 'is this still available', or any question
    about overall availability. Report the numbers exactly as returned.

    Args:
        product: A product_id or product name.

    Returns:
        Total units plus a per-size breakdown, or a LookupFailure. When
        `fully_sold_out` is true, tell the customer it is sold out rather than
        implying it can be bought.
    """
    with get_connection() as conn:
        row = _find_product_row(conn, product)
        if row is None:
            return LookupFailure(
                query=product,
                reason=f"No product in the Campus Customs catalogue matches '{product}'.",
                suggestions=_suggest(conn, product),
            )

        inventory = _size_stock(conn, row["product_id"])
        in_stock, sold_out = _split_sizes(inventory)
        total = sum(item.quantity for item in inventory)

        return StockReport(
            product_id=row["product_id"],
            product_name=row["name"],
            price=row["price"],
            total_stock=total,
            inventory=inventory,
            sizes_in_stock=in_stock,
            sizes_sold_out=sold_out,
            fully_sold_out=total == 0,
        )


def check_size_availability(product: str, size: str) -> SizeAvailability | LookupFailure:
    """Check whether one specific size of a product is in stock.

    Use this the moment a customer names a size — 'do you have this in a large?',
    'is the medium still available?'. Do not infer availability from a previous
    answer; sizes are tracked individually.

    Args:
        product: A product_id or product name.
        size: The size as the customer said it. 'L', 'large', 'XXL' and
            'extra extra large' all work.

    Returns:
        The quantity for that size, whether it is in stock, and which other
        sizes are available so a sold-out answer can offer alternatives. If
        `size_normalized` is null, the shop does not carry that size at all.
    """
    with get_connection() as conn:
        row = _find_product_row(conn, product)
        if row is None:
            return LookupFailure(
                query=product,
                reason=f"No product in the Campus Customs catalogue matches '{product}'.",
                suggestions=_suggest(conn, product),
            )

        inventory = _size_stock(conn, row["product_id"])
        in_stock, _sold_out = _split_sizes(inventory)
        normalized = normalize_size(size)
        match = next((item for item in inventory if item.size == normalized), None)

        return SizeAvailability(
            product_id=row["product_id"],
            product_name=row["name"],
            price=row["price"],
            size_requested=size,
            size_normalized=normalized if match else None,
            quantity=match.quantity if match else 0,
            in_stock=bool(match and match.in_stock),
            sizes_in_stock=in_stock,
            image_url=display_image_url(row["image_file_path"]),
        )


# ---------------------------------------------------------------------------
# Similar products and no-match alternatives (Problem 9)
# ---------------------------------------------------------------------------

# How strongly each shared attribute counts toward "similar".
SIMILARITY_WEIGHTS = {
    "garment_type_exact": 6,
    "garment_type_family": 4,
    "shared_tag": 2,
    "shared_color": 2,
    "same_price": 3,
    "near_price": 1,
}

# Loose families, because garment_type is not standardized in the catalogue
# ("hoodie", "pullover hoodie", and "hooded sweatshirt" all appear).
GARMENT_FAMILIES = (
    "hood",
    "crewneck",
    "t-shirt",
    "zip",
    "jacket",
    "fleece",
    "long-sleeve",
    "performance",
)


def _family(garment_type: str) -> str | None:
    lowered = garment_type.lower()
    return next((family for family in GARMENT_FAMILIES if family in lowered), None)


def _similarity(base: sqlite3.Row, other: sqlite3.Row) -> int:
    """Score how much `other` resembles `base`, using real catalogue fields."""
    score = 0

    base_type = base["garment_type"].lower()
    other_type = other["garment_type"].lower()
    if base_type == other_type:
        score += SIMILARITY_WEIGHTS["garment_type_exact"]
    elif _family(base_type) and _family(base_type) == _family(other_type):
        score += SIMILARITY_WEIGHTS["garment_type_family"]

    base_tags = {tag.lower() for tag in parse_json_list(base["search_tags"])}
    other_tags = {tag.lower() for tag in parse_json_list(other["search_tags"])}
    # "Yale" and "Campus Customs" are on nearly everything, so they say nothing.
    generic = {"yale", "yale university", "campus customs", "yale merch", "college merch"}
    score += SIMILARITY_WEIGHTS["shared_tag"] * len((base_tags & other_tags) - generic)

    base_colors = {c.lower() for c in parse_json_list(base["colors"])}
    other_colors = {c.lower() for c in parse_json_list(other["colors"])}
    score += SIMILARITY_WEIGHTS["shared_color"] * len(base_colors & other_colors)

    if base["price"] == other["price"]:
        score += SIMILARITY_WEIGHTS["same_price"]
    elif abs(base["price"] - other["price"]) <= 15:
        score += SIMILARITY_WEIGHTS["near_price"]

    return score


def similar_products(product_id: str, limit: int = 4) -> list[ProductCard]:
    """Products from the catalogue that resemble the given one.

    Shared by the `You May Also Like` endpoint and the agent's tool, so the
    website and the chatbot recommend the same things.
    """
    with get_connection() as conn:
        base = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if base is None:
            return []

        scored: list[tuple[int, float, sqlite3.Row]] = []
        for row in conn.execute("SELECT * FROM catalogue").fetchall():
            if row["product_id"] == base["product_id"]:
                continue
            score = _similarity(base, row)
            if score > 0:
                # Tie-break toward a similar price point.
                scored.append((score, -abs(row["price"] - base["price"]), row))

        scored.sort(key=lambda item: (-item[0], -item[1], item[2]["name"]))
        return [_row_to_card(conn, row) for _s, _p, row in scored[:limit]]


def find_similar_products(product: str, limit: int = 4) -> list[ProductCard] | LookupFailure:
    """Find products similar to one the customer already likes.

    Use this when a customer asks for "something like this", when the item they
    want is sold out, or when you want to offer a close alternative.

    Args:
        product: A product_id or product name to find relatives of.
        limit: How many to return.

    Returns:
        Similar catalogue products, or a LookupFailure if the starting product
        could not be found.
    """
    with get_connection() as conn:
        row = _find_product_row(conn, product)
        if row is None:
            return LookupFailure(
                query=product,
                reason=f"No product in the Campus Customs catalogue matches '{product}'.",
                suggestions=_suggest(conn, product),
            )
        product_id = row["product_id"]

    return similar_products(product_id, limit=max(1, min(limit, MAX_RESULTS)))


def suggest_alternatives(query: str, limit: int = MAX_RESULTS) -> dict[str, object]:
    """Find real alternatives when an exact search came back empty.

    Call this whenever `search_products` returns nothing. It retries the search
    with progressively fewer words, so "navy sailing quarter-zip" can fall back
    to "sailing" and then "quarter-zip", and reports which part of the request
    it had to drop.

    Args:
        query: The customer's original request, in their words.
        limit: Maximum number of alternatives.

    Returns:
        A dict with:
          `exact_match` — always False; this tool is only for the no-match case.
          `relaxed_to`  — the words that still matched, so you can tell the
                          customer exactly what you broadened to.
          `dropped`     — the words nothing in the catalogue matched.
          `alternatives` — real products. May be empty, in which case say so and
                          ask the customer to describe what they want differently.

    Be explicit with the customer that there was no exact match, and present
    these only as alternatives — never as what they asked for.
    """
    terms = [word for word in re.split(r"\W+", query.lower()) if len(word) > 2]
    limit = max(1, min(limit, MAX_RESULTS))

    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()

        def matches(term: str) -> list[sqlite3.Row]:
            return [
                row
                for row in rows
                if term in row["name"].lower()
                or term in row["garment_type"].lower()
                or term in row["description"].lower()
                or term in " ".join(parse_json_list(row["search_tags"])).lower()
                or term in " ".join(parse_json_list(row["colors"])).lower()
            ]

        hits = {term: matches(term) for term in terms}
        useful = [term for term in terms if hits[term]]
        dropped = [term for term in terms if not hits[term]]

        if not useful:
            return {
                "exact_match": False,
                "relaxed_to": [],
                "dropped": terms,
                "alternatives": [],
            }

        # Rank by how many of the surviving terms each product satisfies.
        counts: dict[str, int] = {}
        keep: dict[str, sqlite3.Row] = {}
        for term in useful:
            for row in hits[term]:
                counts[row["product_id"]] = counts.get(row["product_id"], 0) + 1
                keep[row["product_id"]] = row

        ranked = sorted(keep.values(), key=lambda row: (-counts[row["product_id"]], row["name"]))
        return {
            "exact_match": False,
            "relaxed_to": useful,
            "dropped": dropped,
            "alternatives": [_row_to_card(conn, row) for row in ranked[:limit]],
        }
