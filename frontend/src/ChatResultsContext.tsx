import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { ChatProductCard } from './chat'

interface ChatResults {
  /** The product matches the agent returned for the most recent question. */
  products: ChatProductCard[]
  /** The customer's question that produced them, used as the panel heading. */
  query: string
  /** Bumped on every new result set so pages can react to a repeat search. */
  version: number
}

interface ChatResultsValue extends ChatResults {
  publish: (query: string, products: ChatProductCard[]) => void
  clear: () => void
}

const EMPTY: ChatResults = { products: [], query: '', version: 0 }

const ChatResultsContext = createContext<ChatResultsValue | null>(null)

/**
 * Carries the agent's structured product matches from the chat widget out to
 * the page, so a search in the chat updates the catalogue shown on the site
 * rather than living only inside the conversation.
 */
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults>(EMPTY)

  const publish = useCallback((query: string, products: ChatProductCard[]) => {
    setResults((previous) => ({ query, products, version: previous.version + 1 }))
  }, [])

  const clear = useCallback(() => setResults(EMPTY), [])

  const value = useMemo(
    () => ({ ...results, publish, clear }),
    [results, publish, clear],
  )

  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}

export function useChatResults(): ChatResultsValue {
  const context = useContext(ChatResultsContext)
  if (!context) throw new Error('useChatResults must be used inside a ChatResultsProvider')
  return context
}
