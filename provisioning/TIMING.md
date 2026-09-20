# mkt016 Start Lab timing log

Target < 10 min to everything ready, ceiling 15. "Ready" = apply returned AND warehouse job DONE AND corpus import done AND both services Ready (`check.sh` → READY).

| Run | Date | Project | Apply duration | Warehouse job done | Corpus import done | Everything ready | Slowest | Flakes |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | 2026-09-19 | qwiklabs-gcp-01-61b6c572e170 | 2m36s, one pass, no errors | done inside the import window | **6m02s** import (start → end) | **≈7.5 min** from apply start (import starts ≈1.5 min in, behind the 60 s agent-grant settle; estimate — check.sh Timing line not recorded) | corpus import | none |
| 2 | 2026-09-19 | (fresh project, orchestrator 1.0.1) | 2m43s, one pass | | | | | |
| 3 | | | | | | | | |

## Pre-run project (qwiklabs-gcp-03-a6e4f92c632a, not timed)

Two first-apply failures, both fixed before run 1: the corpus import 403'd on `storage.buckets.create` (the Discovery Engine agent needs a storage grant and a 60 s settle before the import), and `audience-tools` failed with `Error code 7` (secret access not yet propagated; now a secret-level grant plus a 60 s settle). The warehouse job took 1 min 58 s. The services test showed re-scoring moved the policy counts, so re-scoring was dropped (decision Sep 19).
