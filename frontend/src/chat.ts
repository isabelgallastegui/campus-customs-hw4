/** Chat against the PydanticAI agent behind FastAPI. */

export interface ChatProductCard {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  description: string
  sizes_in_stock: string[]
  total_stock: number
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProductCard[]
  failed?: boolean
}

export interface ChatResponse {
  reply: string
  products: ChatProductCard[]
}

/** Where the customer is, so "do you have this in pink?" resolves to a product. */
export interface PageContext {
  path: string
  product_id: string | null
}

export interface StoredChatTurn {
  role: 'user' | 'assistant'
  content: string
  products: ChatProductCard[]
  created_at: string
}

/** Derives page context from the current route. */
export function pageContextFrom(pathname: string): PageContext {
  const match = pathname.match(/^\/products\/(.+)$/)
  return {
    path: pathname,
    product_id: match ? decodeURIComponent(match[1]) : null,
  }
}

export async function sendChatMessage(
  message: string,
  history: ChatTurn[],
  userId: number | null,
  page: PageContext,
): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      // For a signed-in customer the backend loads history from the database
      // instead; this is what carries a guest's context.
      history: history.map((turn) => ({ role: turn.role, content: turn.content })),
      user_id: userId,
      page,
    }),
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail
    throw new Error(
      typeof detail === 'string' ? detail : 'The shop assistant is not available right now.',
    )
  }

  return data as ChatResponse
}


/** Load a signed-in customer's saved conversation. */
export async function fetchChatHistory(userId: number): Promise<StoredChatTurn[]> {
  const response = await fetch(`/api/chat/history?user_id=${userId}`)
  if (!response.ok) return []
  const data = (await response.json()) as { messages?: StoredChatTurn[] }
  return data.messages ?? []
}

/** Wipe a signed-in customer's saved conversation. */
export async function clearChatHistory(userId: number): Promise<void> {
  await fetch(`/api/chat/history?user_id=${userId}`, { method: 'DELETE' })
}
