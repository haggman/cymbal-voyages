# Destination content spec (for the writers)

Cymbal Voyages is a fictional mid-size online travel brand (flights, hotels, curated trip packages). Its voice is warm, specific, quietly confident, never superlative. These descriptions are shown to customers on the site and are also embedded for semantic search, so each one must be distinctive and concrete about what the place feels like, what you do there, and who it suits.

Output: a JSON array. One object per destination, with exactly these keys:

- `destination_id` (string, given below)
- `name` (string, given below)
- `country` (string)
- `region` (string, given below)
- `category` (string, given below)
- `price_band` (`budget` | `mid` | `premium` | `luxury`) — use your judgement; spread them out
- `best_months` (array of integers 1–12; the months a customer would want to be there)
- `description` (120–200 words, one paragraph; evocative, varied; count words)
- `highlights` (array of exactly 5 short noun phrases, 2–6 words each, concrete: "snorkeling at the reef wall", "the Sunday market in the old town")
- `vibe` (array of exactly 3 adjectives)
- `good_for` (array of 2–4 traveler types from: couples, families, solo travelers, friends, honeymooners, multigenerational groups, first-timers, repeat visitors, active travelers, foodies)

Rules:
- Real place names are fine. Do not name real hotels, resorts, cruise lines, airlines, restaurants, or tour companies.
- No superlatives or absolutes: never "best", "#1", "cheapest", "always", "guaranteed", "risk-free", "world-class", "unforgettable", "paradise", "breathtaking", "hidden gem", "bucket list".
- No two descriptions may open with the same first three words. Vary sentence length. Avoid "Whether you're…" and "Imagine…" openings entirely.
- Do not use the "it's not X, it's Y" contrast construction.
- Cruise entries are itineraries, not places: describe the sailing, the ports, the days at sea.
- Mention the season honestly (hurricane season, monsoon, shoulder months) where it matters.
- Return only the JSON array, nothing else, and make sure it parses.
