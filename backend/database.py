"""Shared database access for the Campus Customs backend.

Both the HTTP routes in `main.py` and the agent tools in `tools.py` read the
catalogue, so the connection helpers live here instead of in either one. That
also keeps `tools.py` from importing `main.py`, which would be circular.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

# backend/database.py -> HW 4/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "campus_customs.db"

# Display copies of the product photos: same picture, squared onto a white
# canvas at one size (see normalize_images.py). The database still stores the
# original path; this is purely a presentation layer on top of it.
WEB_IMAGE_DIR = DATA_DIR / "products_web"

SIZE_ORDER = """
    CASE size
        WHEN 'XS' THEN 1 WHEN 'S' THEN 2 WHEN 'M' THEN 3
        WHEN 'L' THEN 4 WHEN 'XL' THEN 5 WHEN 'XXL' THEN 6
        ELSE 7 END
"""


class DatabaseMissingError(RuntimeError):
    """Raised when the SQLite file is not where it should be."""


def get_connection() -> sqlite3.Connection:
    """Open a connection with dict-like rows."""
    if not DB_PATH.exists():
        raise DatabaseMissingError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_json_list(raw: str | None) -> list[str]:
    """`colors` and `search_tags` are JSON arrays stored as TEXT."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def display_image_url(image_file_path: str) -> str:
    """Prefer the normalized copy of a photo, falling back to the original.

    `catalogue.image_file_path` stays the source of truth — this only swaps the
    folder when a cleaned-up version of that exact file exists.
    """
    filename = Path(image_file_path).name
    if (WEB_IMAGE_DIR / filename).exists():
        return f"/media/products_web/{filename}"
    return f"/media/{image_file_path}"


def row_to_product(row: sqlite3.Row) -> dict[str, Any]:
    """Shape one catalogue row for the frontend. No invented fields."""
    image_file_path = row["image_file_path"]
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": parse_json_list(row["colors"]),
        "search_tags": parse_json_list(row["search_tags"]),
        "image_file_path": image_file_path,
        "image_url": display_image_url(image_file_path),
        "price": row["price"],
    }


def fetch_inventory(conn: sqlite3.Connection, product_id: str) -> list[dict[str, Any]]:
    """Per-size stock for one product, ordered XS to XXL."""
    rows = conn.execute(
        f"SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY {SIZE_ORDER}",
        (product_id,),
    ).fetchall()
    return [{"size": r["size"], "quantity": r["quantity"]} for r in rows]


# ---------------------------------------------------------------------------
# Chat history (Problem 8)
# ---------------------------------------------------------------------------

# How many stored turns to replay. Enough to feel like memory, bounded so the
# prompt does not grow without limit for a long-running customer.
HISTORY_LIMIT = 40


def save_chat_message(
    user_id: int,
    role: str,
    content: str,
    products: list[dict[str, Any]] | None = None,
) -> None:
    """Append one turn to `chat_messages` for a signed-in customer.

    `products_json` mirrors the convention already in the table: the product
    cards shown with an assistant reply are stored alongside it, so reloading a
    conversation brings its cards back. It stays NULL for customer messages.
    """
    payload = json.dumps(products) if products else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, payload),
        )
        conn.commit()


def load_chat_history(user_id: int, limit: int = HISTORY_LIMIT) -> list[dict[str, Any]]:
    """Return a customer's most recent turns, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    history = []
    for row in reversed(rows):  # DESC + LIMIT takes the newest; flip to chronological.
        products: list[dict[str, Any]] = []
        if row["products_json"]:
            try:
                parsed = json.loads(row["products_json"])
                if isinstance(parsed, list):
                    products = parsed
            except json.JSONDecodeError:
                products = []
        history.append(
            {
                "role": row["role"],
                "content": row["content"],
                "products": products,
                "created_at": row["created_at"],
            }
        )
    return history


def clear_chat_history(user_id: int) -> int:
    """Delete a customer's saved conversation. Returns how many rows went."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount


def get_user_profile(user_id: int) -> dict[str, Any] | None:
    """The identity details the agent is allowed to know about a customer."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name, email, first_name, last_name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def get_product_summary(product_id: str) -> dict[str, Any] | None:
    """A compact view of one product, for telling the agent what page the customer is on."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        inventory = fetch_inventory(conn, product_id)

    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "price": row["price"],
        "colors": parse_json_list(row["colors"]),
        "sizes_in_stock": [r["size"] for r in inventory if r["quantity"] > 0],
    }
