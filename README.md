# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

FitFindr is a multi-tool AI agent for secondhand shopping. You give it a natural-language request
("vintage graphic tee under $30, size M") and it runs a **planning loop** over three tools — searching
listings, suggesting an outfit against your wardrobe, and writing a shareable fit card — passing state
forward at each step and degrading gracefully when a tool fails or returns nothing.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── tools.py                   # The three tools (implemented)
├── agent.py                   # Planning loop + session state (implemented)
├── app.py                     # Gradio UI (implemented)
├── tests/
│   └── test_tools.py          # pytest isolation tests for each tool
├── planning.md                # Spec written before implementation
├── CHECKLIST.md               # Requirements checklist for the project
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```
A `.env.example` is included — copy it to `.env` and paste in your real key. `.env` is gitignored.

## Run it

```bash
# Run the tool/agent tests
pytest tests/

# Run the agent from the CLI (happy path + no-results path)
python agent.py

# Launch the web UI
python app.py
# then open the localhost URL printed in your terminal (usually http://localhost:7860)
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

---

## Tool Inventory

Your README submission must document each tool's name, inputs, and return value. **These must exactly match your actual function signatures in `tools.py`.**

### 1. `search_listings(description: str, size: str | None = None, max_price: float | None = None) -> list[dict]`

- **Inputs:**
  - `description` (str): free-text keywords (e.g. `"vintage graphic tee"`), tokenized to lowercase words.
  - `size` (str | None): size to filter by, matched case-insensitively as a substring of the listing's
    `size` field (so `"M"` matches `"S/M"` and `"M/L"`). `None` skips size filtering.
  - `max_price` (float | None): inclusive price ceiling. `None` skips price filtering.
- **Output:** `list[dict]` — full listing dicts (`id`, `title`, `description`, `category`, `style_tags`,
  `size`, `condition`, `price`, `colors`, `brand`, `platform`), sorted by descending keyword-relevance
  score (title/style-tag hits weighted highest). Returns `[]` when nothing matches.
- **Purpose:** find candidate secondhand pieces matching the user's request. No LLM — pure data filtering.

### 2. `suggest_outfit(new_item: dict, wardrobe: dict) -> str`

- **Inputs:**
  - `new_item` (dict): a listing dict (typically the top `search_listings` result).
  - `wardrobe` (dict): a wardrobe dict with an `items` key — a list of wardrobe item dicts
    (`name`, `category`, `colors`, `style_tags`, `notes`). May be empty.
- **Output:** `str` — 3–4 sentence outfit suggestion. With a populated wardrobe it names real pieces
  ("pair with your Baggy straight-leg jeans and Chunky white sneakers…"); with an empty wardrobe it
  gives general styling advice. Always non-empty.
- **Purpose:** turn a found item into a wearable look using what the user already owns. Uses Groq
  `llama-3.3-70b-versatile`.

### 3. `create_fit_card(outfit: str, new_item: dict) -> str`

- **Inputs:**
  - `outfit` (str): the outfit suggestion text from `suggest_outfit`.
  - `new_item` (dict): the same listing dict, used to mention item name, price, and platform.
- **Output:** `str` — a 2–4 sentence casual, shareable caption that mentions the item name, price, and
  platform once each and varies between runs (LLM temperature ≈ 0.9). Returns a descriptive error
  string if `outfit` is empty.
- **Purpose:** generate an OOTD-style caption for the look. Uses Groq `llama-3.3-70b-versatile`.

---

## How the Planning Loop Works

`run_agent(query, wardrobe)` in `agent.py` is a linear pipeline with a **data-driven early-exit
branch** — it does not call all three tools unconditionally.

1. **Initialize** a `session` dict (the single source of truth for the run).
2. **Guard** the empty query → set `session["error"]` and return.
3. **Parse** the query with `_parse_query()` (regex) into `description`, `size`, `max_price`
   (e.g. `"vintage graphic tee under 30 size L"` → `{"vintage graphic tee", "L", 30.0}`). Stored in
   `session["parsed"]`.
4. **Call `search_listings(...)`** and store results in `session["search_results"]`. **This is the
   decision point:**
   - **If `results == []`** → set a specific `session["error"]` (telling the user what to adjust:
     remove size filter / raise price / broaden keywords) and **return early**. `suggest_outfit` and
     `create_fit_card` are **never** called with empty input, so `fit_card` stays `None`.
   - **Else** → set `session["selected_item"] = results[0]` and continue.
5. **Call `suggest_outfit(selected_item, wardrobe)`** → `session["outfit_suggestion"]`.
6. **Call `create_fit_card(outfit_suggestion, selected_item)`** → `session["fit_card"]`.
7. **Return** the completed `session`.

So the number of tools that actually run depends on what `search_listings` returns: **1 call** on the
no-results path, **3 calls** on the happy path. The same query type always produces the same control
flow, but a different query (impossible search) produces a visibly different path.

## State Management

A single `session` dict (created by `_new_session()`) is threaded through every step and is the only
place intermediate values live:

| Key | Set when | Used by |
|-----|----------|---------|
| `query` | start | parser |
| `parsed` | step 3 | `search_listings` |
| `search_results` | step 4 | branch decision |
| `selected_item` | step 4 (happy path) | `suggest_outfit` **and** `create_fit_card` |
| `wardrobe` | start | `suggest_outfit` |
| `outfit_suggestion` | step 5 | `create_fit_card` |
| `fit_card` | step 6 | UI panel 3 |
| `error` | any early exit | UI panel 1 |

The exact dict `search_results[0]` is stored once as `selected_item` and passed into both downstream
tools — the user never re-enters the item, and no intermediate value is hardcoded. `run_agent` returns
the final `session`, and `app.py`'s `handle_query()` reads it to populate the three UI panels (or shows
`session["error"]` in panel 1 with the other two blank).

## Error Handling Strategy

Every tool owns its failure mode; nothing fails silently and nothing crashes the agent.

| Tool | Failure mode | What the agent does | Concrete example from testing |
|------|--------------|---------------------|-------------------------------|
| `search_listings` | No listing matches | Returns `[]` (never raises). The loop sets a specific, actionable error and stops before the LLM tools. | `run_agent("designer ballgown size XXS under 5", …)` → `error = 'No listings matched "designer ballgown size XXS under 5". Try removing the size filter, or raising your max price, or using broader keywords…'`; `fit_card = None`. |
| `suggest_outfit` | Empty wardrobe | Detects `wardrobe["items"] == []` and switches to a general-styling-advice prompt instead of naming pieces the user doesn't own. (LLM-call failure → generic fallback string.) | `suggest_outfit(tee, get_empty_wardrobe())` → "I'd love to help you style this awesome graphic tee. For a casual, edgy look, pair it with high-waisted distressed denim, black combat boots…" (non-empty, no crash). |
| `create_fit_card` | Missing/empty outfit | Guards empty/whitespace `outfit` and returns a descriptive error string. (LLM-call failure → templated caption from item fields.) | `create_fit_card("", tee)` → "Can't write a fit card without an outfit suggestion — run suggest_outfit first." (string, not an exception). |

Both LLM-backed tools also wrap the Groq call in a `try/except` with a non-empty fallback, so a missing
key, network error, or rate limit degrades to a sensible message rather than an exception.

## Spec Reflection

**One way `planning.md` helped during implementation:** Writing the Planning Loop section as explicit
numbered branches ("if `results == []` → set error and return early; else `selected_item = results[0]`")
meant `run_agent()` was almost a transcription of the spec. The branch logic and the exact `session`
keys were decided on paper, so implementation was about wiring, not designing — and the no-results path
worked on the first run because I'd already defined what it should do.

**One divergence from the spec, and why:** The spec left query parsing open ("regex, string splitting,
or the LLM"). I planned a simple regex parser and kept it, but I had to make it more defensive than
expected — stripping the matched price/size spans out of the description before tokenizing, plus a
stopword list — because otherwise words like "under" and "size" leaked into the search keywords and
polluted relevance scoring. The interface stayed identical to the spec; only the internal robustness
grew. I also added a UTF-8 stdout reconfigure in `agent.py`'s CLI block (not in the original plan)
because emoji in fit cards crashed the Windows cp1252 console.

## AI Usage

**Instance 1 — `search_listings` (Cursor/Claude):** I gave the AI the Tool 1 block from `planning.md`
(inputs, return contents, failure mode) and required it to use `load_listings()`, filter by all three
params, and return `[]` on no match. I reviewed and **overrode** the first cut's scoring: it treated all
keyword hits equally, so generic terms like "vintage" ranked unrelated items above on-topic ones. I
changed it to weight title/style-tag matches (×3) above description matches (×1) and to ignore
stopwords, then confirmed `search_listings("vintage graphic tee", None, 30)` ranks the graphic tee
first.

**Instance 2 — the planning loop (Cursor/Claude):** I pasted the Architecture diagram plus the Planning
Loop and State Management sections and asked for `run_agent()` matching them exactly. The generated code
was close, but I **revised** two things before trusting it: it initially built the no-results error as a
generic "no results found" string, so I replaced it with the spec's adjustment-aware message (mentions
removing size / raising price based on what was actually parsed), and I made the empty-query guard
return before parsing. I verified by running `python agent.py` (happy + no-results) and printing
`session["selected_item"]` / `session["outfit_suggestion"]` to confirm state flows without re-entry.

---

## Interaction Walkthrough

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky
sneakers. What's out there and how would I style it?" (wardrobe = example wardrobe)

**Step 1 — Tool called:**
- Tool: `search_listings`
- Input: `description="vintage graphic tee"`, `size=None`, `max_price=30.0` (parsed from the query)
- Why this tool: the agent always starts by finding real candidate items; downstream tools need a
  concrete listing.
- Output: a ranked list of tees under $30; top result `lst_006` — "Graphic Tee — 2003 Tour Bootleg
  Style", $24, depop, good condition. Stored as `session["selected_item"]`.

**Step 2 — Tool called:**
- Tool: `suggest_outfit`
- Input: `new_item=<lst_006 dict>`, `wardrobe=<example wardrobe>` (the selected item flows from state —
  not re-entered)
- Why this tool: a real item was found (results non-empty), so the agent moves to styling it against
  the user's closet.
- Output: "Pair the Graphic Tee with the Baggy straight-leg jeans and Black combat boots for a
  grunge-inspired look… layer the Vintage black denim jacket… a nostalgic 90s grunge revival." Stored
  as `session["outfit_suggestion"]`.

**Step 3 — Tool called:**
- Tool: `create_fit_card`
- Input: `outfit=<the suggestion above>`, `new_item=<lst_006 dict>` (both pulled from state)
- Why this tool: an outfit exists, so the final step is a shareable caption.
- Output: "Just scored this sick 2003 Tour Bootleg Style Graphic Tee on depop for $24 and I'm
  obsessed… paired it with my fave baggy straight-leg jeans, black combat boots, and a vintage denim
  jacket 😎." Stored as `session["fit_card"]`.

**Final output to user:** the three UI panels show the listing details, the outfit suggestion, and the
fit card. `session["error"]` is `None`.

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match the query | Returns `[]`; loop sets `session["error"]` with adjustment suggestions (remove size / raise price / broaden keywords) and returns early — downstream tools skipped, `fit_card` stays `None`. |
| `suggest_outfit` | Wardrobe is empty | Returns general styling advice (no named pieces) instead of crashing or returning `""`. |
| `create_fit_card` | Outfit input missing/incomplete | Returns the string "Can't write a fit card without an outfit suggestion — run suggest_outfit first." (no exception). |

---

## Spec Reflection

**One way planning.md helped during implementation:** see the **Spec Reflection** section above — the
numbered branch logic in the Planning Loop section translated almost directly into `run_agent()`.

**One divergence from your spec, and why:** see above — query parsing needed extra defensive stripping
of matched spans + stopwords, and a UTF-8 stdout fix was added for the Windows CLI demo; the public tool
interfaces stayed identical to the spec.

---

## Where to Start

1. **Read `planning.md`** — the full spec written before implementation.
2. Verify the data loads: `python utils/data_loader.py`.
3. Run the tests: `pytest tests/`.
4. Try it: `python agent.py` (CLI) or `python app.py` (web UI).
