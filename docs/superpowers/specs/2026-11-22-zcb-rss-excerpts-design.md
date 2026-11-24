# ZCB RSS Article Excerpts

## Intent

Show a useful preview of each news article inside Feedly so the reader need not open the source page just to understand its lead. Keep the existing public RSS URL, 30-minute schedule, ZCB feed name, and source links.

## Approaches

- **Full article in `content:encoded`:** closest to reading without leaving Feedly, but republishes complete articles through a public GitHub feed. No permission for full redistribution was found; not selected.
- **Short source excerpt in RSS `description`:** shows the article lead in Feedly without adding a summarization service. Selected by the user; reduces, but does not eliminate, public-republication concerns.
- **Keep title and link only:** makes no new content public, but does not meet the in-Feedly reading goal.

## Design

- Fetch each item's article page and extract the first one or two substantive paragraphs from its article body, capped at about 500 characters. Do not generate or paraphrase text.
- Place the excerpt in RSS 2.0 `<description>` and retain the current `<title>`, `<link>`, `<guid>`, and `<pubDate>`.
- Reuse excerpts already present in the feed, fetching article pages only for items without a cached excerpt. On initial rollout, backfill the current feed's items with bounded, rate-limited requests; skip an unavailable article's excerpt without dropping its headline.
- Do not add full article bodies, change the public hosting model, or alter the 30-minute update schedule.

## Verification

- Unit-test paragraph extraction, truncation, XML escaping, and preservation of titles/links.
- Run the existing tests and the local feed builder against the live site; confirm excerpts appear in the XML and existing summaries are reused.
- Trigger the GitHub Actions workflow and check its result and the public RSS. Then confirm Feedly displays the excerpt inline; its UI behavior must be checked in Feedly itself.

## Remaining risk

The RSS repository is public, so even short excerpts are publicly readable. Feedly may display excerpts differently across its views, and the source page structure may change.
