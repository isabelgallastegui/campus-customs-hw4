import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { clearChatHistory, fetchChatHistory, pageContextFrom, sendChatMessage } from '../chat'
import type { ChatTurn } from '../chat'
import { formatPrice } from '../api'
import { useAuth } from '../AuthContext'
import { useChatResults } from '../ChatResultsContext'

const GREETING: ChatTurn = {
  role: 'assistant',
  content:
    "Hi, I'm Bulldog, the Campus Customs shop assistant. Ask me about a style, a size, or what's actually on the shelf right now.",
}

const SUGGESTIONS = [
  'What hoodies do you have?',
  'Anything for a Yale mom?',
  'Show me quarter-zips under $80',
]

/** Pages that render the agent's matches as product cards. */
const RESULT_PAGES = ['/', '/products']

export default function ChatWidget() {
  const { user } = useAuth()
  const { publish, products: shownOnPage } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState<ChatTurn[]>([GREETING])
  const [sending, setSending] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, open, sending, loadingHistory])

  // Customer memory: reload a signed-in customer's saved conversation, and drop
  // back to a fresh greeting when they sign out. Guests keep only this session.
  useEffect(() => {
    if (!user) {
      setMessages([GREETING])
      return
    }

    let cancelled = false
    setLoadingHistory(true)

    fetchChatHistory(user.id)
      .then((saved) => {
        if (cancelled) return
        setMessages(
          saved.length === 0
            ? [GREETING]
            : [
                GREETING,
                ...saved.map((turn) => ({
                  role: turn.role,
                  content: turn.content,
                  products: turn.products,
                })),
              ],
        )
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false)
      })

    return () => {
      cancelled = true
    }
  }, [user])

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || sending) return

    // The agent needs the conversation so far, not including this new message.
    const history = messages.filter((turn) => !turn.failed)

    setMessages((previous) => [...previous, { role: 'user', content: trimmed }])
    setDraft('')
    setSending(true)

    try {
      const result = await sendChatMessage(
        trimmed,
        history,
        user?.id ?? null,
        pageContextFrom(location.pathname),
      )
      setMessages((previous) => [
        ...previous,
        { role: 'assistant', content: result.reply, products: result.products },
      ])

      // Push the structured matches out to the page. This is what turns a chat
      // search into a visible catalogue update rather than just text.
      if (result.products.length > 0) {
        publish(trimmed, result.products)
      }
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { role: 'assistant', content: (error as Error).message, failed: true },
      ])
    } finally {
      setSending(false)
    }
  }

  const onResultPage = RESULT_PAGES.includes(location.pathname)

  return (
    <div className="chat-root">
      {open && (
        <section className="chat-panel" aria-label="Chat with Campus Customs">
          <header className="chat-head">
            <span className="chat-avatar" aria-hidden="true">
              B
            </span>
            <div>
              <div className="chat-title">Ask Bulldog</div>
              <div className="chat-status">
                {sending
                  ? 'Checking the shelf…'
                  : user
                    ? `Signed in as ${user.first_name ?? user.name.split(' ')[0]}`
                    : 'Shop assistant · guest'}
              </div>
            </div>
            {user && messages.length > 1 && (
              <button
                type="button"
                className="chat-wipe"
                onClick={async () => {
                  await clearChatHistory(user.id)
                  setMessages([GREETING])
                }}
                title="Forget this conversation"
              >
                Clear
              </button>
            )}
            <button
              type="button"
              className="chat-close"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
            >
              &times;
            </button>
          </header>

          <div className="chat-log" ref={logRef}>
            {loadingHistory && <p className="chat-note">Loading your conversation…</p>}

            {messages.map((message, index) => (
              <div key={index} className="chat-turn">
                <div
                  className={`bubble ${message.role}${message.failed ? ' failed' : ''}`}
                >
                  {message.content}
                </div>

                {message.products && message.products.length > 0 && (
                  <>
                    <div className="chat-products">
                      {message.products.map((product) => (
                        <Link
                          key={product.product_id}
                          to={`/products/${product.product_id}`}
                          className="chat-product"
                          onClick={() => setOpen(false)}
                        >
                          <img src={product.image_url} alt={product.name} loading="lazy" />
                          <div className="chat-product-body">
                            <span className="chat-product-name">{product.name}</span>
                            <span className="chat-product-meta">
                              {formatPrice(product.price)}
                              {product.sizes_in_stock.length > 0
                                ? ` · ${product.sizes_in_stock.join(', ')}`
                                : ' · Sold out'}
                            </span>
                          </div>
                        </Link>
                      ))}
                    </div>

                    {onResultPage ? (
                      <p className="chat-note">Showing these on the page.</p>
                    ) : (
                      <button
                        type="button"
                        className="chat-note chat-note-link"
                        onClick={() => {
                          navigate('/products')
                          setOpen(false)
                        }}
                      >
                        See {message.products.length} on the page &rarr;
                      </button>
                    )}
                  </>
                )}
              </div>
            ))}

            {sending && (
              <div className="bubble assistant typing" aria-live="polite">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
            )}
          </div>

          {messages.length <= 1 && (
            <div className="chat-suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="chat-chip"
                  onClick={() => send(suggestion)}
                  disabled={sending}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form
            className="chat-form"
            onSubmit={(event) => {
              event.preventDefault()
              send(draft)
            }}
          >
            <input
              className="chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about a style or size…"
              aria-label="Message"
              disabled={sending}
            />
            <button
              type="submit"
              className="chat-send"
              aria-label="Send message"
              disabled={sending || draft.trim() === ''}
            >
              &rarr;
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        className="chat-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        {open ? 'Hide chat' : 'Ask Bulldog'}
        {!open && shownOnPage.length > 0 && (
          <span className="chat-badge">{shownOnPage.length}</span>
        )}
      </button>
    </div>
  )
}
