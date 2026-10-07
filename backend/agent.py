"""The Campus Customs chat agent.

Configures one PydanticAI agent: the system prompt is loaded from
`prompts/prompt.md`, the model is an OpenAI model reached through the Portkey
gateway, and the tools are the catalogue and inventory lookups in `tools.py`.

The API key is read from the environment (a `.env` in this project or any folder
above it). It is never written into the source and never sent to the browser.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import time
from dataclasses import dataclass
from datetime import datetime, timezone

import audit
from database import get_product_summary, get_user_profile
from models import ChatReply, CustomerProfile, PageContext
from tools import (
    check_size_availability,
    check_stock,
    find_similar_products,
    get_product_details,
    search_products,
    suggest_alternatives,
)

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# Walk up from the project folder so the class-wide .env a few levels up is
# found without copying the key around.
PROJECT_ROOT = BACKEND_DIR.parent
for folder in [PROJECT_ROOT, *PROJECT_ROOT.parents]:
    candidate = folder / ".env"
    if candidate.exists():
        load_dotenv(candidate, override=False)

# gpt-6-luna needs the Responses API for function tools — /v1/chat/completions
# rejects tools with reasoning_effort on this gateway.
MODEL_NAME = os.getenv("CAMPUS_CUSTOMS_MODEL", "gpt-6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")

# ---------------------------------------------------------------------------
# Loop limits
#
# An agent that keeps calling tools is the main way one of these gets stuck, and
# every extra round trip costs money and keeps the customer waiting. These caps
# bound a single conversation turn:
#
#   TOOL_CALL_LIMIT   how many tool calls one reply may make. Six is generous —
#                     a hard question ("do you have this in a large, and what
#                     else is like it?") uses three.
#   REQUEST_LIMIT     how many times the model may be called in one turn. One
#                     more than the tool limit, because the final answer needs a
#                     request of its own after the last tool returns.
#   OUTPUT_TOKEN_LIMIT a ceiling on generated tokens, so a malformed run cannot
#                     produce an unbounded reply.
#   TOOL_RETRIES      retries per tool when validation fails, before giving up.
#
# Hitting a limit is not a crash: the run stops, the audit trail records
# "usage_limit_exceeded", and the customer gets a plain message.
# ---------------------------------------------------------------------------
TOOL_CALL_LIMIT = 6
REQUEST_LIMIT = 7
OUTPUT_TOKEN_LIMIT = 4000
TOOL_RETRIES = 2

# How many earlier turns are replayed into a new prompt (the stored history
# itself is capped separately by database.HISTORY_LIMIT).
HISTORY_TURNS = 8

USAGE_LIMITS = UsageLimits(
    request_limit=REQUEST_LIMIT,
    tool_calls_limit=TOOL_CALL_LIMIT,
    output_tokens_limit=OUTPUT_TOKEN_LIMIT,
)


class MissingApiKeyError(RuntimeError):
    """Raised when PORTKEY_API_KEY is not set in the environment."""


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise MissingApiKeyError(
            "PORTKEY_API_KEY is missing. Put it in a .env in this project or a parent folder."
        )
    return key


def load_system_prompt() -> str:
    """Read the system prompt from prompts/prompt.md."""
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"System prompt not found at {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def build_model() -> OpenAIResponsesModel:
    """An OpenAI model routed through Portkey."""
    client = AsyncOpenAI(
        api_key=require_api_key(),
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": "openai"},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))



@dataclass
class ChatDeps:
    """Per-conversation context handed to the agent.

    Built fresh for every request so the agent itself stays stateless and one
    customer's details can never leak into another's conversation.
    """

    customer: CustomerProfile | None = None
    page: PageContext | None = None


def build_customer(user_id: int | None) -> CustomerProfile | None:
    """Load the signed-in customer's profile, or None for a guest."""
    if user_id is None:
        return None
    profile = get_user_profile(user_id)
    if profile is None:
        return None
    return CustomerProfile(
        user_id=profile["id"],
        name=profile["name"],
        email=profile["email"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
    )


def describe_customer(customer: CustomerProfile | None) -> str:
    if customer is None:
        return (
            "The customer is browsing as a guest and is not signed in. Help them "
            "normally. Do not ask for personal details, and do not claim to "
            "remember an earlier conversation."
        )

    greeting_name = customer.first_name or customer.name.split(" ")[0]
    return (
        f"The customer is signed in. Their name is {customer.name} "
        f"(call them {greeting_name}) and their account email is {customer.email}. "
        "You may greet them by first name. Their past conversation with you is "
        "saved, so you can refer back to it naturally. Never read their email or "
        "any account details back to them unless they ask, and never mention any "
        "other customer."
    )


def describe_page(page: PageContext | None) -> str:
    if page is None or (not page.product_id and not page.path):
        return "You do not know which page the customer is on."

    if page.product_id:
        summary = get_product_summary(page.product_id)
        if summary:
            colors = ", ".join(summary["colors"]) or "not recorded"
            sizes = ", ".join(summary["sizes_in_stock"]) or "none in stock"
            return (
                "The customer is currently looking at the product page for "
                f"\"{summary['name']}\" (product_id: {summary['product_id']}, "
                f"{summary['garment_type']}, ${summary['price']:.2f}, "
                f"colors: {colors}, sizes in stock: {sizes}).\n"
                "When they say \"this\", \"it\", or \"this one\" without naming a "
                "product, they mean this one. Still call your tools for the "
                "current price and stock rather than relying on the figures here."
            )

    if page.path == "/products":
        return "The customer is browsing the full catalogue page."
    if page.path == "/":
        return "The customer is on the home page."
    return f"The customer is on the page {page.path}."


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, ChatReply]:
    """Build the agent once and reuse it across requests.

    Built lazily so that importing this module — and therefore starting the API
    — does not fail when the key is absent. The products and account routes keep
    working even if the chat cannot.
    """
    agent = Agent(
        build_model(),
        deps_type=ChatDeps,
        output_type=ChatReply,
        instructions=load_system_prompt(),
        retries=TOOL_RETRIES,
    )

    @agent.instructions
    def customer_and_page(ctx: RunContext[ChatDeps]) -> str:
        """Appended to the system prompt on every run, from live deps."""
        return (
            "## This conversation\n\n"
            f"{describe_customer(ctx.deps.customer)}\n\n"
            f"{describe_page(ctx.deps.page)}"
        )

    # Plain tools: they read the database and need no agent context.
    agent.tool_plain(search_products)
    agent.tool_plain(get_product_details)
    agent.tool_plain(check_stock)
    agent.tool_plain(check_size_availability)
    agent.tool_plain(find_similar_products)
    agent.tool_plain(suggest_alternatives)
    return agent


def _finish(entry: dict, began: float) -> None:
    """Stamp the duration and append the run to the audit trail."""
    entry["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entry["duration_ms"] = round((time.monotonic() - began) * 1000)
    audit.record_run(entry)


async def ask_agent(
    message: str,
    history: list[dict[str, str]] | None = None,
    customer: CustomerProfile | None = None,
    page: PageContext | None = None,
) -> ChatReply:
    """Send one customer message to the agent and return its structured reply.

    `customer` and `page` travel as deps, which a dynamic instruction renders
    into the system prompt. They are rebuilt per request, so the cached agent
    stays stateless.
    """
    agent = get_agent()

    # Earlier turns are passed as a short transcript ahead of the new message.
    # For a signed-in customer these come from the chat_messages table.
    if history:
        transcript = "\n".join(
            f"{'Customer' if turn.get('role') == 'user' else 'You'}: {turn.get('content', '')}"
            for turn in history[-HISTORY_TURNS:]
        )
        prompt = f"Earlier in this conversation:\n{transcript}\n\nCustomer: {message}"
    else:
        prompt = message

    run_id = audit.new_run_id()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    began = time.monotonic()
    entry = audit.build_entry(
        run_id=run_id,
        started_at=started,
        message=message,
        model=MODEL_NAME,
        user_id=customer.user_id if customer else None,
        page_product_id=page.product_id if page else None,
        page_path=page.path if page else None,
    )

    try:
        result = await agent.run(
            prompt,
            deps=ChatDeps(customer=customer, page=page),
            usage_limits=USAGE_LIMITS,
        )
    except UsageLimitExceeded as error:
        entry["stop_reason"] = "usage_limit_exceeded"
        entry["error"] = audit.summarize(str(error))
        _finish(entry, began)
        raise
    except Exception as error:  # noqa: BLE001 - record, then let the API handle it
        entry["stop_reason"] = f"error:{type(error).__name__}"
        entry["error"] = audit.summarize(str(error))
        _finish(entry, began)
        raise

    entry["tool_calls"] = audit.extract_tool_calls(result.all_messages())
    entry["stop_reason"] = "completed"
    entry["products_returned"] = len(result.output.products)
    usage = result.usage()
    entry["usage"] = {
        "requests": getattr(usage, "requests", None),
        "tool_calls": getattr(usage, "tool_calls", None),
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }
    _finish(entry, began)

    return result.output
