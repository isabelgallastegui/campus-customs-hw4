"""Structured types shared by the agent and the API.

`ProductCard` is what the website renders beside the chat; `ProductDetails`,
`SizeAvailability` and `StockReport` are what the lookup tools hand back to the
agent; `ChatReply` is the agent's structured output; `ChatRequest` /
`ChatResponse` are the HTTP contract.

Every field here maps onto a real column in `campus_customs.db` — `catalogue`
for the product facts, `inventory` for the per-size quantities — so the agent
never has to compose a value of its own.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProductCard(BaseModel):
    """One product, shaped for display next to a chat reply.

    Every field comes from the catalogue database by way of `search_products`.
    The agent is instructed to copy these values rather than compose them.
    """

    product_id: str = Field(description="Catalogue slug, e.g. 'yale-mom-hoodie'.")
    name: str = Field(description="Display name of the product.")
    garment_type: str = Field(description="Category, e.g. 'pullover hoodie'.")
    price: float = Field(description="Price in dollars, exactly as stored.")
    image_url: str = Field(description="URL the frontend loads the photo from.")
    description: str = Field(description="The catalogue description.")
    colors: list[str] = Field(
        default_factory=list,
        description="Colors from the catalogue, shown as swatches on the card.",
    )
    sizes_in_stock: list[str] = Field(
        default_factory=list,
        description="Sizes with quantity greater than zero.",
    )
    total_stock: int = Field(default=0, description="Units on hand across all sizes.")


# ---------------------------------------------------------------------------
# Tool result types (Problem 6)
# ---------------------------------------------------------------------------


class SizeStock(BaseModel):
    """One row of the `inventory` table, made explicit for the agent.

    `quantity` is the raw number; `in_stock` is derived so the agent cannot
    misread a `0` as availability.
    """

    size: str = Field(description="Size label as stored: XS, S, M, L, XL, or XXL.")
    quantity: int = Field(description="Units on hand for this size. 0 means sold out.")
    in_stock: bool = Field(description="True when quantity is greater than zero.")


class ProductDetails(BaseModel):
    """Everything the catalogue and inventory tables know about one product."""

    product_id: str = Field(description="Catalogue slug, the primary key.")
    name: str = Field(description="Display name.")
    garment_type: str = Field(description="Category, e.g. 'quarter-zip pullover sweatshirt'.")
    description: str = Field(description="The full catalogue description, verbatim.")
    colors: list[str] = Field(default_factory=list, description="Colors from the catalogue.")
    search_tags: list[str] = Field(
        default_factory=list, description="Keywords the shop files this product under."
    )
    price: float = Field(description="Price in dollars, exactly as stored.")
    image_url: str = Field(description="URL the frontend loads the photo from.")
    inventory: list[SizeStock] = Field(
        default_factory=list, description="Every size the shop carries, XS to XXL."
    )
    sizes_in_stock: list[str] = Field(
        default_factory=list, description="Sizes a customer can actually buy right now."
    )
    sizes_sold_out: list[str] = Field(
        default_factory=list, description="Sizes currently at zero."
    )
    total_stock: int = Field(description="Units on hand across all sizes.")


class SizeAvailability(BaseModel):
    """The answer to 'do you have this in a large?'"""

    product_id: str
    product_name: str
    price: float = Field(description="Included so one call answers price and stock together.")
    size_requested: str = Field(description="The size as the customer asked for it.")
    size_normalized: str | None = Field(
        default=None,
        description="The matching stored size label, or null if the shop has no such size.",
    )
    quantity: int = Field(default=0, description="Units on hand for that size.")
    in_stock: bool = Field(default=False, description="True only when quantity > 0.")
    sizes_in_stock: list[str] = Field(
        default_factory=list,
        description="Other sizes available now, so a sold-out answer can offer alternatives.",
    )
    image_url: str = ""


class StockReport(BaseModel):
    """A stock-only view, for 'how many do you have left?'"""

    product_id: str
    product_name: str
    price: float
    total_stock: int = Field(description="Units across every size.")
    inventory: list[SizeStock] = Field(default_factory=list)
    sizes_in_stock: list[str] = Field(default_factory=list)
    sizes_sold_out: list[str] = Field(default_factory=list)
    fully_sold_out: bool = Field(
        default=False, description="True when every size is at zero."
    )


class LookupFailure(BaseModel):
    """Returned instead of a result when nothing matched.

    Giving the agent a typed failure — with candidate names — is safer than
    raising, because it gives the model something concrete to say rather than
    an empty result it might paper over.
    """

    found: bool = Field(default=False, description="Always False.")
    query: str = Field(description="What was looked up.")
    reason: str = Field(description="Plain-language explanation to relay to the customer.")
    suggestions: list[str] = Field(
        default_factory=list,
        description="Names of near matches the customer might have meant.",
    )


class ChatReply(BaseModel):
    """The agent's structured answer."""

    reply: str = Field(description="The message shown to the customer.")
    products: list[ProductCard] = Field(
        default_factory=list,
        description="Products to display alongside the reply. May be empty.",
    )


# ---------------------------------------------------------------------------
# Customer memory and page context (Problem 8)
# ---------------------------------------------------------------------------


class PageContext(BaseModel):
    """Where the customer is on the site when they send a message.

    Lets "do you have this in pink?" resolve to the product on screen instead
    of being an unanswerable question.
    """

    path: str | None = Field(default=None, description="Route the customer is on, e.g. '/products/yale-mom-hoodie'.")
    product_id: str | None = Field(
        default=None,
        description="Set when the customer is on a single-product page.",
    )


class CustomerProfile(BaseModel):
    """Who the agent is talking to. Only ever built for a signed-in customer."""

    user_id: int
    name: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class StoredChatTurn(BaseModel):
    """One saved turn, replayed into the widget when a customer returns."""

    role: str
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistoryResponse(BaseModel):
    """What GET /api/chat/history returns."""

    user_id: int
    messages: list[StoredChatTurn] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """One turn of conversation, as sent by the frontend."""

    role: str = Field(description="'user' or 'assistant'.")
    content: str


class ChatRequest(BaseModel):
    """What the website posts to /api/chat."""

    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Earlier turns, oldest first, so the agent has context.",
    )
    user_id: int | None = Field(
        default=None,
        description="Set when a customer is logged in. Drives history saving and the greeting.",
    )
    page: PageContext | None = Field(
        default=None,
        description="The page the customer is looking at while they type.",
    )


class ChatResponse(BaseModel):
    """What /api/chat returns to the website."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list)
