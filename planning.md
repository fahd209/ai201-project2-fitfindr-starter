# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## What FitFindr Does (Milestone 1 summary)

FitFindr is a multi-tool agent that takes one natural-language thrifting request and runs it through
three tools in sequence, carrying state forward at each step. It **searches** the mock listings
dataset for items matching a description / size / price ceiling (`search_listings` — triggered first,
by the raw query), **suggests an outfit** that pairs the top match against the user's existing wardrobe
(`suggest_outfit` — triggered only once a real listing has been selected), and **writes a shareable
caption** for that look (`create_fit_card` — triggered only once an outfit suggestion exists). When
`search_listings` returns nothing, the agent stops immediately, records a helpful error message, and
never calls the downstream tools with empty input; when the wardrobe is empty or the outfit text is
missing, the individual tools degrade to general advice / an error string rather than crashing.

### Data notes (from reading the dataset)

- **`data/listings.json`** — 40 listings. Each is a dict with: `id` (str), `title` (str),
  `description` (str), `category` (str: tops / bottoms / outerwear / shoes / accessories),
  `style_tags` (list[str]), `size` (str, free-form e.g. `"M"`, `"S/M"`, `"W30 L30"`, `"US 8"`,
  `"One Size"`), `condition` (str: excellent / good / fair), `price` (float), `colors` (list[str]),
  `brand` (str or None), `platform` (str: depop / thredUp / poshmark).
- **`data/wardrobe_schema.json`** — each wardrobe item has: `id` (str), `name` (str), `category` (str),
  `colors` (list[str]), `style_tags` (list[str]), `notes` (str or None).
- **`get_example_wardrobe()`** returns the 10-item sample closet — use it to test the happy path
  (specific, named-piece outfit suggestions). **`get_empty_wardrobe()`** returns `{"items": []}` —
  use it to test the empty-wardrobe failure mode (general styling advice, no crash).

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the 40-item mock listings dataset for pieces matching a keyword description, optionally
filtered by size and a maximum price, and returns the matches ranked by how well they match.

**Input parameters:**
- `description` (str): Free-text keywords describing the wanted item, e.g. `"vintage graphic tee"`.
  Tokenized to lowercase words; each word is matched against a listing's title, description,
  category, and style_tags.
- `size` (str | None): Size string to filter by, e.g. `"M"`. Matched case-insensitively as a
  substring against the listing's `size` field so `"M"` matches `"S/M"` and `"M/L"`. `None` skips
  size filtering.
- `max_price` (float | None): Inclusive upper price bound. `None` skips price filtering.

**What it returns:**
A `list[dict]` of full listing dicts (every field above: id, title, description, category,
style_tags, size, condition, price, colors, brand, platform), sorted by descending relevance score
(keyword-overlap count, with light weighting for title/style_tag hits). Listings scoring 0 keyword
matches are dropped. Returns `[]` when nothing matches.

**What happens if it fails or returns nothing:**
Returns an empty list `[]` — never raises. The planning loop detects the empty list, sets a helpful
`session["error"]` ("No listings matched … try removing the size filter, raising your budget, or
using broader keywords"), and stops before calling `suggest_outfit`.

---

### Tool 2: suggest_outfit

**What it does:**
Given the selected listing and the user's wardrobe, asks the LLM to propose 1–2 complete, specific
outfits built around the new item using named pieces from the wardrobe (with styling notes like
rolling sleeves or tucking).

**Input parameters:**
- `new_item` (dict): A single listing dict (typically the top `search_listings` result). Its title,
  category, colors, and style_tags are formatted into the prompt.
- `wardrobe` (dict): A wardrobe dict with an `items` key — a list of wardrobe item dicts
  (`name`, `category`, `colors`, `style_tags`, `notes`). May be empty.

**What it returns:**
A non-empty `str` of natural-language outfit suggestions — for a populated wardrobe it names actual
pieces ("pair with your Baggy straight-leg jeans and Chunky white sneakers…"); for an empty wardrobe
it returns general styling guidance (silhouettes, colors, and item types that pair well).

**What happens if it fails or returns nothing:**
If `wardrobe["items"]` is empty it switches to the general-advice prompt instead of crashing. If the
LLM call itself fails (no/invalid key, network/rate-limit error) it returns a graceful fallback string
describing how the item could generally be styled — it never raises and never returns `""`.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion plus the item details into a short, casual, shareable caption — the kind
of thing someone posts with an OOTD photo.

**Input parameters:**
- `outfit` (str): The outfit suggestion text returned by `suggest_outfit`.
- `new_item` (dict): The same listing dict, used to mention the item name, price, and platform
  naturally.

**What it returns:**
A 2–4 sentence `str` caption that is casual/authentic (not a product description), mentions the item
name, price, and platform once each, captures the outfit vibe, and varies between runs/inputs
(LLM temperature ≈ 0.9).

**What happens if it fails or returns nothing:**
If `outfit` is empty / whitespace-only, it returns a descriptive error string
("Can't write a fit card without an outfit suggestion — run suggest_outfit first.") rather than
raising. If the LLM call fails, it returns a simple templated caption built from the item fields as a
fallback.

---

### Additional Tools (if any)

None for the required build. (Stretch candidate: `compare_price(item)` — estimate whether a listing's
price is fair against same-category comparables in the dataset. Will be specced here before starting.)

---

## Planning Loop

**How does your agent decide which tool to call next?**

The loop is a linear pipeline with a hard early-exit branch driven by tool output, implemented in
`run_agent(query, wardrobe)`:

1. Initialize `session = _new_session(query, wardrobe)`.
2. **Parse** the query into `description`, `size`, `max_price` using regex/string rules (price from
   `$NN` or `"under NN"`; size from a `size X` pattern or a standalone token like `M`/`US 8`; the
   remaining words become the description). Store in `session["parsed"]`.
3. **Call `search_listings(description, size, max_price)`**; store in `session["search_results"]`.
   - **Branch (error path):** if `search_results == []`, set `session["error"]` to a specific,
     actionable message and **`return session` immediately** — do **not** call `suggest_outfit` or
     `create_fit_card`.
   - **Branch (happy path):** otherwise set `session["selected_item"] = search_results[0]` and continue.
4. **Call `suggest_outfit(selected_item, wardrobe)`**; store in `session["outfit_suggestion"]`.
   (The tool internally branches on empty wardrobe vs. populated wardrobe.)
5. **Call `create_fit_card(outfit_suggestion, selected_item)`**; store in `session["fit_card"]`.
6. `return session`.

The agent's behavior is therefore **not** a fixed 3-call sequence: the number of tools actually
invoked depends on what `search_listings` returns (1 call on the no-results path, 3 on the happy
path). "Done" = either an error was set (early return) or `fit_card` was produced.

---

## State Management

**How does information from one tool get passed to the next?**

A single `session` dict (created by `_new_session`) is the one source of truth for the interaction and
is threaded through every step:

- `query` — the original user text.
- `parsed` — `{description, size, max_price}` extracted in step 2.
- `search_results` — list returned by `search_listings`.
- `selected_item` — `search_results[0]`; this exact dict is passed into both `suggest_outfit` and
  `create_fit_card` (the item never has to be re-entered by the user).
- `wardrobe` — the wardrobe dict passed in at the start, forwarded into `suggest_outfit`.
- `outfit_suggestion` — string from `suggest_outfit`; passed directly into `create_fit_card`.
- `fit_card` — final string from `create_fit_card`.
- `error` — set only on early termination; `None` on success.

Each tool reads its inputs from the session and writes its output back into the session before the
next tool runs, so data flows forward with no re-prompting and no hardcoded intermediate values.
`run_agent` returns the completed session, which `app.py` reads to populate the three UI panels.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Returns `[]` (no exception). Loop sets `session["error"]`: "No listings matched ‘{query}’. Try removing the size filter, raising your max price, or using broader keywords (e.g. ‘tee’ instead of ‘vintage band tee’)." and returns early — downstream tools are skipped, `fit_card` stays `None`. |
| suggest_outfit | Wardrobe is empty | Detects `wardrobe["items"] == []` and returns general styling advice for the item (what silhouettes/colors/pieces pair well) instead of naming nonexistent wardrobe pieces. Never raises, never returns `""`. (LLM-call failure → graceful generic styling fallback string.) |
| create_fit_card | Outfit input is missing or incomplete | Guards empty/whitespace `outfit`; returns the string "Can't write a fit card without an outfit suggestion — run suggest_outfit first." (LLM-call failure → a simple templated caption from the item fields.) Never raises. |

---

## Architecture

```
                          ┌─────────────────────────────┐
        User query  ─────▶│        run_agent()          │
   "vintage graphic tee   │       (planning loop)        │
    under $30, size M"    └──────────────┬──────────────┘
                                         │
                                         ▼
                              parse query → session["parsed"]
                                         │
                                         ▼
        ┌────────────────────────────────────────────────────────────┐
        │  search_listings(description, size, max_price)              │
        └───────────────┬───────────────────────────┬────────────────┘
                        │ results == []              │ results == [item, ...]
                        ▼                             ▼
            session["error"] = "No listings    session["selected_item"] = results[0]
            matched… try broader terms"                │
                        │                              ▼
                        │             ┌──────────────────────────────────────┐
              [ERROR]   │             │ suggest_outfit(selected_item,         │
              return    │             │                wardrobe)              │
              session ◀─┘             │   empty wardrobe → general advice     │
              (fit_card = None)       └───────────────┬──────────────────────┘
                                                      ▼
                                       session["outfit_suggestion"] = "..."
                                                      │
                                                      ▼
                                      ┌──────────────────────────────────────┐
                                      │ create_fit_card(outfit_suggestion,    │
                                      │                 selected_item)        │
                                      │   empty outfit → error string         │
                                      └───────────────┬──────────────────────┘
                                                      ▼
                                       session["fit_card"] = "..."
                                                      │
                                                      ▼
                                          return session  ──▶  app.py panels

   session (state, threaded through every step):
     query · parsed · search_results · selected_item · wardrobe ·
     outfit_suggestion · fit_card · error
```

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I'll use **Cursor's agent (Claude)** one tool at a time, pasting that tool's block above (what it does,
inputs, return value, failure mode) as the prompt.

- **`search_listings`:** Give the AI the Tool 1 block and require it to (a) use `load_listings()` from
  `utils/data_loader.py` rather than re-opening the file, (b) filter by all three params, (c) score by
  keyword overlap and drop zero-score listings, (d) return `[]` on no match. **Verify before trusting:**
  read the code to confirm it filters on size *and* price *and* description and returns `[]` (not
  `None`) when empty; then run the three pytest cases (results / empty / price filter).
- **`suggest_outfit` & `create_fit_card`:** Give the AI each tool block plus the requirement to call
  Groq `llama-3.3-70b-versatile` via the existing `_get_groq_client()`. **Verify:** confirm
  `suggest_outfit` branches on empty `wardrobe["items"]`, both wrap the LLM call in try/except with a
  non-empty fallback, and `create_fit_card` guards an empty `outfit` and uses temperature ≈ 0.9. Run
  each twice on the same input to confirm `create_fit_card` output varies.

**Milestone 4 — Planning loop and state management:**

I'll paste the **Architecture diagram + the Planning Loop and State Management sections** above into the
AI and ask it to implement `run_agent()` to match exactly. **Verify before trusting:** confirm it
(a) branches on the `search_listings` result, (b) early-returns with `session["error"]` and never calls
`suggest_outfit` on `[]`, (c) stores each tool's output back into `session`, and (d) does not call all
three tools unconditionally. I'll then run `python agent.py` (happy + no-results cases) and print
`session["selected_item"]` / `session["outfit_suggestion"]` to confirm state flows without re-entry.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1 — Parse + search:**
The loop parses the query → `description="vintage graphic tee"`, `size=None`, `max_price=30.0`.
It calls `search_listings("vintage graphic tee", size=None, max_price=30.0)`. Matching tees under $30
include `lst_006` (Graphic Tee 2003 Tour Bootleg, $24), `lst_033` (Vintage Band Tee Faded Grey, $19),
and `lst_002` (Y2K Baby Tee, $18), ranked by keyword overlap. Result list is non-empty →
`session["selected_item"] = results[0]` (the top-scoring graphic tee), `session["error"]` stays `None`.

**Step 2 — Suggest outfit:**
Because a real item was selected, the loop calls
`suggest_outfit(selected_item=<graphic tee>, wardrobe=<example wardrobe>)`. The wardrobe is non-empty,
so the LLM returns a specific suggestion naming real pieces, e.g. "Pair the faded graphic tee with your
Baggy straight-leg jeans and Chunky white sneakers; layer the Vintage black denim jacket and cuff the
sleeves once." Stored in `session["outfit_suggestion"]`.

**Step 3 — Create fit card:**
The loop calls `create_fit_card(outfit=<that suggestion>, new_item=<graphic tee>)`. The LLM returns a
casual caption mentioning the item name, price, and platform once each, e.g. "thrifted this faded
graphic tee off depop for $24 and it was made for my baggy jeans 🖤 denim jacket + chunky sneakers,
full look in my stories." Stored in `session["fit_card"]`.

**Final output to user:**
The three UI panels show: (1) the selected listing details, (2) the outfit suggestion, and (3) the fit
card caption. `session["error"]` is `None`.

*Error variant:* for "designer ballgown size XXS under $5", `search_listings` returns `[]`, the loop
sets `session["error"]` to the broaden-your-search message and returns after step 1 — panels 2 and 3
stay empty and `fit_card` is `None`.
