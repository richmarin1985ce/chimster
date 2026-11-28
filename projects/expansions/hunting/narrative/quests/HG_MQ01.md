# HG_MQ01 — The Empty Camp
Status: detailed design proposal, not native script or verified quest.

## Canon and premise
Great Forest disappearance; classic Oblivion first.

## Proposed stage plan
| Stage | Objective / transition |
|---|---|
| 10 | Discover abandoned camp and register investigation |
| 20 | Inspect tracks or question surviving witnesses |
| 30 | Reconcile evidence and locate the missing party's route |
| 100 | Unlock HG_MQ02 without mandatory transformation |

Stage numbers are proposed native bindings; validate target format before writing. Alternatives are mutually compatible where appropriate; completion occurs once. Preserve unrelated vanilla state.

## State contract
camp_found; trail_evidence; witness_account. Persistent, quest-scoped state; names are design keys, not compiled variables. Re-entry must be idempotent. Record outcome provenance and verify any references before export.

## Asset and level dependencies
Camp, trail, Maelin and Bren, original trail-marker props, TES4 quest and result-script integration.

## Recovery and acceptance
Track clues remain available even if an actor is absent; no compulsory werewolf state.
Test entry, both solution paths, save/load at every stage, missing actor/reference, repeated activation, completion and successor availability. No external authoring tools. Native compile and retail verification remain gates.
