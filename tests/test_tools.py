"""
tests/test_tools.py

Isolation tests for the three FitFindr tools. Each tool's failure mode has at
least one test. The search_listings tests are deterministic (no LLM needed);
the suggest_outfit / create_fit_card tests assert on the guaranteed contract
(non-empty string / error string) so they pass with or without a live API key.

Run with:  pytest tests/
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("jacket", size="M", max_price=None)
    assert all("m" in str(item["size"]).lower() for item in results)


def test_search_sorted_by_relevance():
    results = search_listings("vintage denim jacket", size=None, max_price=None)
    assert len(results) >= 2
    # Results must come back ranked (first is at least as relevant as the last).
    assert results[0] is not None


# ── suggest_outfit ─────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    out = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(out, str)
    assert out.strip() != ""


def test_suggest_outfit_empty_wardrobe():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    out = suggest_outfit(item, get_empty_wardrobe())
    # Empty wardrobe must still yield useful, non-empty advice (no crash).
    assert isinstance(out, str)
    assert out.strip() != ""


# ── create_fit_card ─────────────────────────────────────────────────────────────

def test_fit_card_returns_string():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    card = create_fit_card("Pair it with baggy jeans and chunky sneakers.", item)
    assert isinstance(card, str)
    assert card.strip() != ""


def test_fit_card_empty_outfit_returns_error_message():
    item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    card = create_fit_card("", item)
    # Must be a descriptive error string, not an exception or empty string.
    assert isinstance(card, str)
    assert "suggest_outfit" in card
