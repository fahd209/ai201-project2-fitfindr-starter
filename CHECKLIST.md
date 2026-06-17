# FitFindr — Project Checklist

A trackable checklist of every requirement for **Show What You Know: FitFindr**.
Check items off (`[x]`) as you complete them. Time estimate: ~8–9 hours total.

---

## Setup

- [x] Forked the FitFindr starter repo and cloned the fork locally
- [x] Created and activated a virtual environment (`.venv`) — `(.venv)` visible in prompt
- [x] Installed dependencies with `pip install -r requirements.txt`
- [x] Created a `.env` file in repo root with `GROQ_API_KEY=your_key_here` (placeholder — replace with your real key)
- [x] Confirmed `.env` is listed in `.gitignore` and never committed
- [ ] Verified Groq access (`llama-3.3-70b-versatile`, free tier) — pending your real API key in `.env`

---

## Milestone 1 — Explore the Starter Repo (~30 min)

- [x] Read 5–10 listings in `data/listings.json`
- [x] Noted available listing fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`
- [x] Read the wardrobe structure in `data/wardrobe_schema.json` and noted item fields
- [x] Read `utils/data_loader.py` — understand `load_listings()`, `get_example_wardrobe()`, `get_empty_wardrobe()`
- [x] Wrote a 2–3 sentence description of what FitFindr does (triggers per tool + failure behavior) in the **A Complete Interaction** section of `planning.md`

**Checkpoint:** Can describe the listings structure from memory; understand difference between `get_example_wardrobe()` and `get_empty_wardrobe()` and when to use each.

---

## Milestone 2 — Write Your Spec Before Any Code (~1 hr)

- [x] Filled in every pre-populated section header in `planning.md` with implementation-ready content

### Tool specs (for each of the 3 required tools)
- [x] **search_listings** — what it does, exact input params (name/type/meaning), what it returns (contents described, not just "a list"), failure behavior
- [x] **suggest_outfit** — what it does, exact input params, return contents, failure behavior
- [x] **create_fit_card** — what it does, exact input params, return contents, failure behavior

### Planning loop
- [x] Described the **actual conditional logic** with specific branches (e.g. "if `results` empty → set error, return early; else `selected_item = results[0]` → proceed")
- [x] Specific enough that someone else could implement it from the words alone

### Architecture diagram
- [x] Added an agent diagram to the `## Architecture` section of `planning.md`
- [x] Diagram has labeled nodes (user, planning loop, each tool, session state)
- [x] Diagram has labeled arrows showing data flow between components
- [x] Diagram shows a visible **error branch** that terminates the flow early
- [x] Diagram is **text-based** — ASCII art or a ```mermaid``` fenced block (NOT an image/screenshot), committed in `planning.md`

### AI Tool Plan
- [x] Filled in `## AI Tool Plan` per milestone: which AI tool, what input (named planning.md sections + diagram), expected output, how you'll verify it matches your spec

### Walkthrough
- [x] Traced the complete interaction example step-by-step at the bottom of `planning.md` (tool order, exact inputs, returns, final user-facing output)

### Error handling table
- [x] Each error-handling row is specific & actionable — states what the agent *says* and what it offers instead

**Checkpoint:** All three tools specified with inputs/returns; planning loop describes conditional logic; diagram shows data/control flow + error branch; AI Tool Plan names specific spec sections; walkthrough traces a full query through all 3 tools.

---

## Milestone 3 — Build and Test Each Tool in Isolation (~2–3 hr)

- [x] Read the pre-written docstrings (Args/Returns/TODO) for all 3 stubs in `tools.py`
- [x] Implemented all tools directly in `tools.py` (no separate files per tool)

### search_listings(description, size, max_price)
- [x] Uses `load_listings()` from `utils/data_loader.py` (no re-implementing file loading)
- [x] Filters by all three parameters
- [x] Returns matching items (sorted by relevance)
- [x] Returns `[]` (empty list) when no matches — no exception

### suggest_outfit(new_item, wardrobe)
- [x] Calls Groq `llama-3.3-70b-versatile` using `GROQ_API_KEY` from `.env`
- [x] Handles empty wardrobe (`wardrobe['items']` empty) without crashing — returns useful general advice

### create_fit_card(outfit, new_item)
- [x] Takes both `outfit` and `new_item` arguments (matches stub signature)
- [x] Calls the LLM
- [x] Guards against empty `outfit` string — returns an error message string, not a crash
- [x] Produces **different output each time** for different inputs (temperature 0.9) — verify with a real key
### Tests
- [x] Created `tests/test_tools.py`
- [x] At least one test per failure mode (no results, empty wardrobe, incomplete outfit)
- [x] `test_search_returns_results` passes
- [x] `test_search_empty_results` passes (returns `[]`, no exception)
- [x] `test_search_price_filter` passes (all items `price <= max_price`)
- [x] All tests pass via `pytest tests/`

**Checkpoint:** Each tool callable directly with sensible output; each failure mode returns a specific, informative message (no exception, no silent empty return).

---

## Milestone 4 — Wire Up the Planning Loop and State (~2 hr)

- [x] Read TODO steps in `agent.py`; matched them to the Planning Loop section of `planning.md`
- [x] Implemented `run_agent()` following the numbered steps
- [x] Planning loop **branches on the `search_listings` result** (does NOT call all 3 tools unconditionally)
- [x] Tool outputs stored in the `session` dict
- [x] Implemented `handle_query()` in `app.py` — calls `run_agent()` and maps session dict → 3 output panel strings

### State verification
- [x] Ran the example query end-to-end
- [x] `session["selected_item"]` is the exact same dict passed into `suggest_outfit`
- [x] `session["outfit_suggestion"]` is exactly what went into `create_fit_card`
- [x] No re-prompting / no hardcoded values between steps

### Branch path verification
- [x] Ran `python agent.py` and confirmed the no-results path sets `session["error"]` and leaves `session["fit_card"]` as `None`
- [x] Confirmed `suggest_outfit` is NOT called when `search_listings` returns `[]`

**Checkpoint:** Complete query flows through all 3 tools with visible state passing; behavior differs for no-results vs. matches; can point to the final state object and show its contents.

---

## Milestone 5 — Test Every Failure Mode Deliberately (~1 hr)

- [x] **No results:** `search_listings('designer ballgown', size='XXS', max_price=5)` returns `[]` without exception; full agent run tells user what failed + what to try
- [x] **Empty wardrobe:** `suggest_outfit(results[0], get_empty_wardrobe())` returns a useful string (general styling advice), not an exception/empty string
- [x] **Empty outfit:** `create_fit_card('', results[0])` returns a descriptive error message string, not a Python exception
- [ ] Captured a screenshot or recording of at least one triggered failure (for the demo video) — **manual: capture during your recording**

**Checkpoint:** All three failure modes trigger deliberately and produce specific, informative responses; at least one triggered failure documented.

---

## Milestone 6 — Document and Record (~1–1.5 hr)

- [x] `handle_query()` in `app.py` implemented (if not done in M4)
- [x] Ran `python app.py`; opened the URL shown in terminal (may not be `localhost:7860`) — verified HTTP 200 at http://127.0.0.1:7860
- [x] All three output panels populate correctly for a happy-path query

### README sections
- [x] **Tool inventory** — name, inputs (param names + types, e.g. `description (str)`), outputs, purpose for each tool (must match actual function signatures)
- [x] **Planning loop** explanation — describes the conditional logic, not just "it decides"
- [x] **State management** approach — what is stored, when, and how it passes between tools
- [x] **Error handling** strategy per tool, with at least one concrete example from your testing
- [x] **Spec reflection** — one way the spec helped; one way implementation diverged and why
- [x] **AI usage** — at least 2 specific instances: what you gave the AI (which spec sections/diagram), what it produced, what you changed/overrode

### Demo video (3–5 min) — **manual: record yourself**
- [ ] Complete multi-step interaction from user query → fit card using all 3 required tools
- [ ] Narration of what the agent does at each step (which tool, why)
- [ ] State visibly or verbally passing between tools
- [ ] At least one triggered failure with the agent's graceful, informative response

**Checkpoint:** Interface runs and all three panels populate; README covers all sections with substantive content; demo recorded with full interaction, state passing, and an error scenario.

---

## Required Features Summary

- [x] **3+ tools with defined interfaces** — clear function signatures (inputs + returns)
  - [x] `search_listings(description, size, max_price)` — handles no matches
  - [x] `suggest_outfit(new_item, wardrobe)` — handles empty/minimal wardrobe
  - [x] `create_fit_card(outfit, new_item)` — different output each time
- [x] **Planning loop** — selects tools based on returned data; documented in README
- [x] **State management** — info from one tool flows to the next within a session; shown in demo
- [x] **Error handling for each tool** — no fail-silently, no crashing; communicates + fallback/ask; documented in README
- [x] **Multi-step workflow** — verified one complete interaction using all 3 tools in sequence (show in demo video)

---

## Stretch Features (optional, extra credit)

> Update `planning.md` before starting each one.

- [ ] **Price comparison tool** — 4th tool estimating whether a price is fair vs. comparable listings
- [ ] **Style profile memory** — remember user style preferences across sessions
- [ ] **Trend awareness** — tool checking recent posts/tags on a public fashion platform for popular styles in user's size
- [ ] **Retry logic with fallback** — if `search_listings` returns nothing, auto-retry with loosened constraints (e.g. drop size) and tell the user what changed

---

## Submission (Course Portal)

- [ ] Link to forked GitHub repository — **manual: push your commits and submit the URL**
- [x] `planning.md` in repo root (written before implementation; updated before stretch features)
- [x] `README.md` with: tool inventory, planning loop explanation, state management, error handling per tool (+ example), spec reflection, AI usage (2+ instances)
- [ ] Demo video (3–5 min): complete interaction, per-step narration, visible state passing, one triggered failure with graceful response — **manual: record & submit**
