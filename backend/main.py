"""Campus Customs backend.

A small FastAPI app over the existing SQLite database. It serves the product
catalogue, the product images, account signup/login, and the chat route that
forwards customer messages to the PydanticAI agent.

Run it from this folder:

    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import MODEL_NAME, MissingApiKeyError, ask_agent, build_customer
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from auth import (
    PASSWORD_RULES,
    hash_password,
    is_valid_email,
    normalize_email,
    password_problems,
    verify_password,
)
from database import (
    DATA_DIR,
    DB_PATH,
    DatabaseMissingError,
    clear_chat_history,
    get_connection as _open_connection,
    load_chat_history,
    row_to_product,
    save_chat_message,
)
from tools import similar_products
from models import (
    ChatHistoryResponse,
    ProductCard,
    ChatRequest,
    ChatResponse,
    StoredChatTurn,
)

logger = logging.getLogger("campus_customs")

app = FastAPI(
    title="Campus Customs API",
    description="Product catalogue and inventory for the Campus Customs storefront.",
    version="0.1.0",
)

# The Vite dev server runs on a different port, so the browser needs CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# `catalogue.image_file_path` is stored as e.g. "products/yale-mom-hoodie.jpg",
# so mounting the data folder at /media makes the image URL simply
# "/media/" + image_file_path.
#
# The data pack ships separately from the source, so a first run without it
# should say what is missing rather than dying inside StaticFiles.
if DATA_DIR.is_dir():
    app.mount("/media", StaticFiles(directory=DATA_DIR), name="media")
else:
    logger.warning(
        "No data folder at %s — product images and the catalogue are unavailable. "
        "Add the local data pack (data/campus_customs.db and data/products/) as "
        "described in README.md, then restart.",
        DATA_DIR,
    )


def get_connection() -> sqlite3.Connection:
    """Open a connection, turning a missing database into a clean HTTP error."""
    try:
        return _open_connection()
    except DatabaseMissingError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Quick check that the database is reachable."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    return {"status": "ok", "products": count, "chat_model": MODEL_NAME}


@app.get("/api/products")
def list_products() -> dict[str, Any]:
    """Every catalogue product, with total stock summed across sizes."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock_rows = conn.execute(
            "SELECT product_id, SUM(quantity) AS total FROM inventory GROUP BY product_id"
        ).fetchall()

    totals = {r["product_id"]: r["total"] for r in stock_rows}
    products = []
    for row in rows:
        product = row_to_product(row)
        product["total_stock"] = totals.get(row["product_id"], 0)
        products.append(product)

    return {"count": len(products), "products": products}


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict[str, Any]:
    """One product plus its per-size inventory, straight from the database."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"No product '{product_id}'")

        inventory_rows = conn.execute(
            """
            SELECT size, quantity
            FROM inventory
            WHERE product_id = ?
            ORDER BY CASE size
                WHEN 'XS' THEN 1 WHEN 'S' THEN 2 WHEN 'M' THEN 3
                WHEN 'L' THEN 4 WHEN 'XL' THEN 5 WHEN 'XXL' THEN 6
                ELSE 7 END
            """,
            (product_id,),
        ).fetchall()

    product = row_to_product(row)
    product["inventory"] = [
        {"size": r["size"], "quantity": r["quantity"]} for r in inventory_rows
    ]
    product["total_stock"] = sum(r["quantity"] for r in inventory_rows)
    return product


@app.get("/api/products/{product_id}/similar")
def get_similar_products(product_id: str, limit: int = 4) -> dict[str, Any]:
    """Real catalogue products that resemble this one, for 'You May Also Like'."""
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail=f"No product '{product_id}'")

    matches: list[ProductCard] = similar_products(product_id, limit=max(1, min(limit, 12)))
    return {"product_id": product_id, "count": len(matches), "products": matches}


@app.get("/api/garment-types")
def list_garment_types() -> dict[str, Any]:
    """Distinct garment types, for the catalogue filter bar."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT garment_type FROM catalogue ORDER BY garment_type"
        ).fetchall()
    return {"garment_types": [r["garment_type"] for r in rows]}



# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    confirm_password: str = Field(min_length=1, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PublicUser(BaseModel):
    """What the frontend is allowed to see. Never includes the hash."""

    id: int
    name: str
    email: str
    first_name: str | None
    last_name: str | None
    created_at: str


def row_to_public_user(row: sqlite3.Row) -> PublicUser:
    return PublicUser(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        created_at=row["created_at"],
    )


@app.get("/api/auth/password-rules")
def get_password_rules() -> dict[str, Any]:
    """The frontend renders these so the rules live in exactly one place."""
    return {"rules": [label for _pattern, label in PASSWORD_RULES]}


@app.post("/api/auth/signup", status_code=201)
def signup(payload: SignupRequest) -> PublicUser:
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = normalize_email(payload.email)

    if not first_name or not last_name:
        raise HTTPException(status_code=422, detail="First and last name are both required.")

    if not is_valid_email(email):
        raise HTTPException(status_code=422, detail="That does not look like a valid email address.")

    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=422, detail="The two passwords do not match.")

    problems = password_problems(payload.password)
    if problems:
        raise HTTPException(
            status_code=422,
            detail="Password requirements not met: " + "; ".join(problems).lower() + ".",
        )

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="An account already exists for that email. Try logging in instead.",
            )

        # The `name` column is NOT NULL and predates first_name/last_name,
        # so it gets the combined name.
        cursor = conn.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                f"{first_name} {last_name}",
                email,
                hash_password(payload.password),
                first_name,
                last_name,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return row_to_public_user(row)


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> PublicUser:
    email = normalize_email(payload.email)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

    # Same message and same work either way, so the response does not reveal
    # whether the email is registered.
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="That email and password do not match.")

    return row_to_public_user(row)



# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def _is_content_filter(error: ModelHTTPError) -> bool:
    """True when the provider blocked the prompt under its content policy."""
    body = error.body
    if isinstance(body, dict):
        return body.get("code") == "content_filter"
    return "content_filter" in str(body)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Forward a customer message to the PydanticAI agent.

    The agent decides whether to call the catalogue search tool, and returns a
    structured reply plus any products worth displaying. The API key lives in
    the environment on this side of the wire — the browser never sees it.
    """
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Please type a message first.")

    # A signed-in customer gets their saved conversation; a guest gets only the
    # turns the browser is holding for this session.
    customer = build_customer(payload.user_id)
    if customer is not None:
        history = [
            {"role": turn["role"], "content": turn["content"]}
            for turn in load_chat_history(customer.user_id)
        ]
    else:
        history = [{"role": turn.role, "content": turn.content} for turn in payload.history]

    try:
        reply = await ask_agent(message, history, customer=customer, page=payload.page)
    except MissingApiKeyError as error:
        # Configuration problem, not a customer problem — say so plainly.
        logger.error("Chat unavailable: %s", error)
        raise HTTPException(
            status_code=503,
            detail="The shop assistant is not configured yet. PORTKEY_API_KEY is missing.",
        ) from error
    except UsageLimitExceeded as error:
        # The agent hit its per-turn tool/request ceiling. Answer plainly rather
        # than erroring — the audit trail already records why it stopped.
        logger.warning("Agent hit a usage limit: %s", error)
        return ChatResponse(
            reply=(
                "That one took more digging than I can do in a single answer. "
                "Could you narrow it down a bit — a garment type, a colour, or "
                "one product at a time?"
            ),
            products=[],
        )
    except ModelHTTPError as error:
        # The provider's own safety filter rejected the message before the agent
        # ever saw it. That is not a server fault, so answer rather than erroring.
        if _is_content_filter(error):
            logger.info("Provider content filter rejected a message")
            return ChatResponse(
                reply=(
                    "I can't help with that one. Ask me about Campus Customs apparel — "
                    "a style, a color, a size, or what's in stock — and I'll take a look."
                ),
                products=[],
            )
        logger.exception("Model call failed")
        raise HTTPException(
            status_code=502,
            detail="The shop assistant could not answer right now. Please try again.",
        ) from error
    except Exception as error:  # noqa: BLE001 - surface one clean message to the UI
        logger.exception("Agent call failed")
        raise HTTPException(
            status_code=502,
            detail="The shop assistant could not answer right now. Please try again.",
        ) from error

    # Only signed-in customers have their conversation saved. Guests are not
    # written to the database at all.
    if customer is not None:
        save_chat_message(customer.user_id, "user", message)
        save_chat_message(
            customer.user_id,
            "assistant",
            reply.reply,
            [product.model_dump() for product in reply.products] or None,
        )

    return ChatResponse(reply=reply.reply, products=reply.products)



@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def get_chat_history(user_id: int) -> ChatHistoryResponse:
    """Reload a signed-in customer's saved conversation."""
    if build_customer(user_id) is None:
        raise HTTPException(status_code=404, detail="No such account.")

    turns = [
        StoredChatTurn(
            role=turn["role"],
            content=turn["content"],
            products=turn["products"],
            created_at=turn["created_at"],
        )
        for turn in load_chat_history(user_id)
    ]
    return ChatHistoryResponse(user_id=user_id, messages=turns)


@app.delete("/api/chat/history")
def delete_chat_history(user_id: int) -> dict[str, Any]:
    """Let a customer wipe their saved conversation."""
    if build_customer(user_id) is None:
        raise HTTPException(status_code=404, detail="No such account.")
    removed = clear_chat_history(user_id)
    return {"user_id": user_id, "deleted": removed}


if __name__ == "__main__":
    # Equivalent to running `uvicorn main:app --reload --port 8000` here.
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
