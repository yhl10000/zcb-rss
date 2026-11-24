# ZCB RSS Article Excerpts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add short article leads to RSS items so Feedly can show a preview without immediately opening the source page.

**Architecture:** Extend the existing standard-library HTML parser to extract plain-text lead paragraphs from each article page and serialize them in RSS `description`. Reuse summaries already present in `zcb.rss`; fetch only missing summaries, and keep an item's title and link if its article page cannot be read.

**Tech Stack:** Python 3 standard library (`html.parser`, `urllib`, `xml.etree.ElementTree`, `unittest`), GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-22-zcb-rss-excerpts-design.md`

## Global Constraints

- Extract the first one or two substantive paragraphs, capped at about 500 characters; do not generate or paraphrase text.
- Put excerpts in RSS 2.0 `<description>`; retain title, link, GUID, and publication date.
- Reuse existing excerpts; fetch only items without a cached excerpt.
- Use bounded, rate-limited article requests; an unavailable article must not remove its headline.
- Keep full article bodies out of the public feed and leave the 30-minute schedule unchanged.

## Review Focus

- Missing or changed article body: keep the RSS item with no description (Task 2 test).
- Nested markup, entities, or whitespace in paragraph text: emit readable plain text (Task 1 test).
- XML-special characters in an excerpt: preserve valid XML and the original text (Task 1 test).
- Existing item already has an excerpt: do not refetch its article page (Task 2 test).
- Article page request fails: continue generating the feed and retain its title/link (Task 2 test).

---

### Task 1: Extract and serialize article excerpts

**Files:**
- Modify: `tools/build_feed.py`
- Modify: `tests/test_build_feed.py`

**Interfaces:**
- Produces: `parse_article_summary(html: str) -> str | None`, returning plain text from the first one or two non-empty paragraphs in the article body, truncated to 500 characters, or `None` when no body exists.
- Produces: `render_feed(articles)` writes an item's non-empty `summary` to its RSS `<description>`.

- [ ] **Step 1: Add failing parser tests** named `test_extracts_two_lead_paragraphs_as_plain_text`, `test_summary_is_capped_at_500_characters`, and `test_missing_article_body_returns_no_summary`. Import the module as `from tools import build_feed`; use `getattr(build_feed, "parse_article_summary", lambda html: None)` so a missing implementation produces assertion failures rather than collection errors. The missing-body test must first assert the parser exists, then assert its result is `None`.
- [ ] **Step 2: Run `python -m unittest discover -s tests -p test_build_feed.py -v`**; confirm the new tests fail by assertion because the parser is missing.
- [ ] **Step 3: Implement `parse_article_summary`** with the existing `PageParser` tree; use the article element's paragraph text, normalize whitespace, and cap at 500 characters.
- [ ] **Step 4: Add `test_rss_description_contains_escaped_summary`** asserting `<description>` contains the excerpt, XML special characters round-trip, and empty summaries omit the element.
- [ ] **Step 5: Run `python -m unittest discover -s tests -p test_build_feed.py -v`** and confirm the serialization assertion fails because `<description>` is absent.
- [ ] **Step 6: Update `render_feed`** to emit the non-empty plain-text summary as `<description>`.
- [ ] **Step 7: Run `python -m unittest discover -s tests -v`**; expect all tests to pass.

### Task 2: Fetch and cache summaries during updates

**Files:**
- Modify: `tools/build_feed.py`
- Modify: `tests/test_build_feed.py`

**Interfaces:**
- Consumes: `parse_article_summary(html)` and `render_feed(articles)` from Task 1.
- Produces: article items with `summary` populated from existing RSS when cached, otherwise from a bounded source-page fetch; fetch failures yield `None` without dropping the item.

- [ ] **Step 1: Add failing tests** named `test_cached_summaries_avoid_refetch`, `test_uncached_article_gets_summary`, `test_failed_article_fetch_preserves_item`, and `test_load_cached_summaries_from_feed`. Use `getattr(build_feed, "enrich_articles", None)` in the enrichment tests and assert it is callable before exercising it, so missing code fails as an assertion rather than an exception.
- [ ] **Step 2: Run `python -m unittest discover -s tests -p test_build_feed.py -v`**; confirm the four cache/failure tests fail because enrichment/cache loading is not implemented.
- [ ] **Step 3: Implement `load_cached_summaries(path=OUTPUT)` and `enrich_articles(articles, cached_summaries, fetch_summary)`** in `tools/build_feed.py`. Catch per-article fetch errors, leave the item's summary empty, and sleep 0.5 seconds between uncached article requests in `main`.
- [ ] **Step 4: Run `python -m unittest discover -s tests -v`**; expect all parser, serialization, cache, and failure tests to pass.
- [ ] **Step 5: Run the live builder in PowerShell** from `D:\YHL10000\zcb-rss`:

  ```powershell
  $env:HTTPS_PROXY = 'http://127.0.0.1:10809'
  python tools/build_feed.py
  ```

  Then parse `zcb.rss` as XML and assert every description is at most 500 characters and no `content:encoded` full-body element exists.
- [ ] **Step 6: Commit the tested changes** with `git add tools/build_feed.py tests/test_build_feed.py zcb.rss docs/superpowers/specs/2026-11-22-zcb-rss-excerpts-design.md docs/superpowers/plans/2026-11-22-zcb-rss-excerpts.md && git commit -m "feat: add article excerpts to ZCB RSS"`.
- [ ] **Step 7: Push and verify the scheduled workflow** with `git push origin master`, `gh workflow run update-feed.yml --repo yhl10000/zcb-rss --ref master`, and `gh run list --repo yhl10000/zcb-rss --workflow update-feed.yml --limit 1`; confirm the run succeeds and the public `zcb.rss` has excerpts, no full article body, and all existing item links.

## Self-review

- Spec coverage: extraction, `<description>`, cache reuse, bounded request rate, per-article failure isolation, and unchanged cadence are covered in Tasks 1–2.
- Feedly display itself is not automatable through this repository; after publishing, confirm the preview appears in the user's Feedly view.
- The repository remains public; the design limits each item to a short source excerpt but does not make excerpts private or establish redistribution permission.
- Plan scope is limited to the existing builder, its tests, and the existing scheduled workflow; no dependency or hosting changes are needed.
