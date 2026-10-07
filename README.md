# Campus Customs

A storefront for **Campus Customs**, the family-run shop at 57 Broadway in New
Haven that has printed officially licensed Yale apparel since 1975.

Customers browse the catalogue, create an account, and talk to **Bulldog**, a
PydanticAI shop assistant that answers from the shop's live database — real
prices, real stock, real products — and renders what it finds as clickable
product cards on the page.

- **Frontend** — React + Vite + TypeScript
- **Backend** — Python + FastAPI over SQLite
- **Agent** — PydanticAI, using an OpenAI model through the Portkey gateway

---

## 1. Add the local data pack

**The database and product photographs are not in this repository.** They are
supplied separately as a `data/` folder. Copy it into the project root so it
sits next to `backend/` and `frontend/`:

```
hw4/
├── backend/
├── frontend/
└── data/                       ← add this
    ├── campus_customs.db
    └── products/               ← 102 product photographs
```

Nothing else needs to move. The backend resolves the folder relative to its own
location, so it is found automatically.

Check it is in place:

```bash
ls data/campus_customs.db && ls data/products | wc -l   # expect 102
```

### Optional: tidy up the product photos

The source photographs come in 60 different sizes, and most are letterboxed or
shot on a black backdrop. Two scripts generate display copies:

```bash
cd backend
python normalize_images.py      # -> data/products_web/   square, white, uniform
python make_hero_cutouts.py     # -> data/products_hero/  transparent cut-outs
```

Both are optional. Without them the site falls back to the original photographs
in `data/products/`, and everything still works — the catalogue just looks less
consistent. Both folders are gitignored because they are derived files.

---

## 2. Add your API key

The chatbot calls an OpenAI model through Portkey. Copy the example file and
fill in your key:

```bash
cp .env.example .env
```

```ini
PORTKEY_API_KEY=your-portkey-key-here
```

`.env` is gitignored and must never be committed. A `.env` in any parent folder
also works, so a shared class key does not need copying around.

**The products and account pages work without a key** — only the chat needs it.

---

## 3. Install

**Backend** (Python 3.11+):

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Frontend** (Node 18+):

```bash
cd frontend
npm install
```

---

## 4. Run it

Two terminals.

**Backend** — from the `backend/` folder:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Frontend** — from the `frontend/` folder:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5174**.

Vite proxies `/api` and `/media` to the backend on port 8000, so the browser only
ever talks to one origin. Check the backend on its own with:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","products":102,"chat_model":"gpt-6-luna"}
```

### Signing in

The data pack ships with a test account:

```
test@campuscustoms.yale.edu  /  password
```

Or create your own — passwords need 8+ characters with an uppercase letter, a
lowercase letter, and a number. A signed-in customer's chat history is saved and
reloaded on their next visit; guests can chat normally but nothing is stored.

---

## What to try

| | |
| --- | --- |
| **Browse** | Use the navy department bar — Hoodies, Crewnecks, Colleges, Teams. |
| **Ask about a product** | "How much is the Yale Mom Hoodie and how many in each size?" The answer comes from the database. |
| **Ask for a category** | "What hoodies do you have?" The matches appear as product cards on the page, not just in the chat. |
| **Ask for something that does not exist** | "Do you have a pink Yale hoodie?" It says there is no match and offers real alternatives. |
| **Open any product** | "You May Also Like" at the bottom suggests related products from the catalogue. |
| **Ask from a product page** | "Do you have this in pink?" — the agent knows which product you are looking at. |

---

## Project layout

```
hw4/
├── AI_prompts.md              Every prompt used to build this, verbatim
├── requirements.txt           Python dependencies
├── .env.example               Environment variable template
├── .gitignore
├── README.md
├── frontend/                  Vite + React + TypeScript
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── src/
│       ├── components/        NavBar, ProductCard, ChatWidget, AgentResults, …
│       ├── pages/             Home, Products, ProductDetail, About, Login, …
│       ├── api.ts             Catalogue + similar-products client
│       ├── auth.ts            Signup and login client
│       ├── chat.ts            Chat client and page context
│       ├── colors.ts          Catalogue colour names -> swatches
│       ├── AuthContext.tsx    Signed-in customer
│       ├── ChatResultsContext.tsx  Carries agent matches out to the page
│       └── styles.css         Design system
├── backend/
│   ├── main.py                FastAPI app — uvicorn main:app --reload --port 8000
│   ├── agent.py               PydanticAI agent: prompt, model, tools, limits
│   ├── models.py              Pydantic types for tools, chat, and the API
│   ├── tools.py               The six catalogue and inventory tools
│   ├── database.py            Shared SQLite access and chat history
│   ├── auth.py                Password hashing and validation
│   ├── audit.py               Append-only agent audit log
│   ├── normalize_images.py    Product photo clean-up (optional)
│   ├── make_hero_cutouts.py   Transparent hero cut-outs (optional)
│   └── prompts/
│       └── prompt.md          The agent's system prompt and safety rules
├── tests/
│   └── app_check.mjs          Browser test that produces output/app_check.html
└── output/
    ├── harness.md             Full build write-up, problem by problem
    ├── design.md              Visual design decisions and reasoning
    ├── usability.md           The four usability improvements
    ├── app_check.html         Test evidence — open this in a browser
    ├── app_check_images/      Screenshots linked from app_check.html
    └── audit_trail.json       Append-only log of agent activity
```

`backend/` contains more modules than the four headline ones: `database.py`,
`auth.py`, and `audit.py` are imported by `main.py` and `agent.py` and are
required for the app to start.

---

## Re-running the tests

With both servers running:

```bash
cd tests
npm install
npx playwright install chromium
node app_check.mjs
```

It drives a real browser through three checks — chatbot price and stock, category
search updating the page, and the "You May Also Like" recommendations — compares
each answer against the database, and writes the screenshots that
`output/app_check.html` displays.

---

## Notes

- **Nothing about a product is invented.** Every price, size, stock figure, and
  description is read from `campus_customs.db` at request time. If the agent
  cannot find something it says so rather than guessing.
- **Passwords** are stored as salted PBKDF2-SHA256 hashes (120,000 iterations),
  matching the scheme already in the database. Plain text is never stored.
- **The audit trail** records a numeric `user_id` only — never names, emails,
  password hashes, or API keys.
- **Loop limits** cap one conversation turn at 6 tool calls and 7 model
  requests; searches return at most 8 products.

Full detail on all of the above is in [`output/harness.md`](output/harness.md).
